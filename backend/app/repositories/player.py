"""선수 조회 Repository."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.player import Player
from app.models.stats import BattingSeasonStat, PitchingSeasonStat
from app.models.team import Team
from app.schemas.player import PlayerRole


@dataclass(frozen=True, slots=True)
class PlayerSearchCriteria:
    """HTTP와 무관한 선수 검색 조건."""

    query: str | None = None
    role: PlayerRole | None = None
    season: int | None = None
    team: str | None = None
    offset: int = 0
    limit: int = 20


class PlayerRepository(Protocol):
    """Service가 구체적인 SQLAlchemy 구현에 의존하지 않도록 하는 계약."""

    def search(self, criteria: PlayerSearchCriteria) -> tuple[list[Player], int]: ...

    def get_by_id(self, player_id: int) -> Player | None: ...

    def list_batting_seasons(self, player_id: int) -> list[BattingSeasonStat]: ...

    def list_pitching_seasons(self, player_id: int) -> list[PitchingSeasonStat]: ...


class SqlAlchemyPlayerRepository:
    """SQL 작성과 ORM loading 전략만 담당하는 선수 Repository 구현."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _escape_like(value: str) -> str:
        """사용자 입력의 LIKE wildcard를 일반 문자로 처리한다."""

        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _stat_exists(
        model: type[BattingSeasonStat] | type[PitchingSeasonStat],
        criteria: PlayerSearchCriteria,
    ):
        """역할/시즌/팀 조건에 맞는 시즌 기록 EXISTS 절을 생성한다."""

        statement = (
            select(model.player_id)
            .join(Team, Team.team_id == model.team_id)
            .where(model.player_id == Player.player_id)
        )
        if criteria.season is not None:
            statement = statement.where(model.season == criteria.season)
        if criteria.team is not None:
            statement = statement.where(Team.team_name == criteria.team)
        return statement.exists()

    def _apply_filters(
        self, statement: Select[tuple[Player]], criteria: PlayerSearchCriteria
    ) -> Select[tuple[Player]]:
        """목록과 count 쿼리가 동일한 필터를 사용하도록 한 곳에서 적용한다."""

        if criteria.query:
            escaped_query = self._escape_like(criteria.query)
            statement = statement.where(Player.search_name.like(f"{escaped_query}%", escape="\\"))

        batting_exists = self._stat_exists(BattingSeasonStat, criteria)
        pitching_exists = self._stat_exists(PitchingSeasonStat, criteria)
        if criteria.role is PlayerRole.BATTING:
            statement = statement.where(batting_exists)
        elif criteria.role is PlayerRole.PITCHING:
            statement = statement.where(pitching_exists)
        elif criteria.season is not None or criteria.team is not None:
            statement = statement.where(or_(batting_exists, pitching_exists))
        return statement

    def search(self, criteria: PlayerSearchCriteria) -> tuple[list[Player], int]:
        """필터링된 선수 페이지와 전체 개수를 반환한다."""

        filtered = self._apply_filters(select(Player), criteria)
        count_statement = select(func.count()).select_from(filtered.subquery())
        total = self._session.scalar(count_statement) or 0

        page_statement = (
            filtered.options(selectinload(Player.profiles))
            .order_by(Player.player_name, Player.player_id)
            .offset(criteria.offset)
            .limit(criteria.limit)
        )
        players = list(self._session.scalars(page_statement).all())
        return players, total

    def get_by_id(self, player_id: int) -> Player | None:
        """역할별 프로필을 포함해 한 선수를 조회한다."""

        statement = (
            select(Player)
            .options(selectinload(Player.profiles))
            .where(Player.player_id == player_id)
        )
        return self._session.scalar(statement)

    def list_batting_seasons(self, player_id: int) -> list[BattingSeasonStat]:
        """타격 기록을 시즌, 팀 순서로 반환한다."""

        statement = (
            select(BattingSeasonStat)
            .options(joinedload(BattingSeasonStat.team))
            .where(BattingSeasonStat.player_id == player_id)
            .order_by(BattingSeasonStat.season, BattingSeasonStat.team_id)
        )
        return list(self._session.scalars(statement).unique().all())

    def list_pitching_seasons(self, player_id: int) -> list[PitchingSeasonStat]:
        """투구 기록을 시즌, 팀 순서로 반환한다."""

        statement = (
            select(PitchingSeasonStat)
            .options(joinedload(PitchingSeasonStat.team))
            .where(PitchingSeasonStat.player_id == player_id)
            .order_by(PitchingSeasonStat.season, PitchingSeasonStat.team_id)
        )
        return list(self._session.scalars(statement).unique().all())
