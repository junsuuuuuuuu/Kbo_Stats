"""선수 조회 Repository."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Select, func, or_, select, tuple_
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


def calculate_defensive_efficiency(
    *,
    batters_faced: int,
    hits_allowed: int,
    home_runs_allowed: int,
    walks_allowed: int,
    hit_batters: int,
    strikeouts: int,
    errors: int,
) -> float | None:
    """공식 DER 식으로 인플레이 타구의 아웃 처리 비율을 계산한다."""

    balls_in_play = (
        batters_faced - home_runs_allowed - strikeouts - walks_allowed - hit_batters
    )
    if balls_in_play <= 0:
        return None
    outs_on_balls_in_play = (
        batters_faced
        - hits_allowed
        - strikeouts
        - walks_allowed
        - hit_batters
        - errors
    )
    return outs_on_balls_in_play / balls_in_play


class PlayerRepository(Protocol):
    """Service가 구체적인 SQLAlchemy 구현에 의존하지 않도록 하는 계약."""

    def search(self, criteria: PlayerSearchCriteria) -> tuple[list[Player], int]: ...

    def get_by_id(self, player_id: int) -> Player | None: ...

    def list_batting_seasons(self, player_id: int) -> list[BattingSeasonStat]: ...

    def list_league_batting_seasons(self, season: int) -> list[BattingSeasonStat]: ...

    def list_pitching_seasons(self, player_id: int) -> list[PitchingSeasonStat]: ...

    def team_defensive_efficiencies(
        self, team_seasons: set[tuple[int, int]]
    ) -> dict[tuple[int, int], float]: ...

    def league_metric_values(self, role: PlayerRole, season: int, metric: str) -> list[float]: ...


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

    def list_league_batting_seasons(self, season: int) -> list[BattingSeasonStat]:
        """파생 타격 지표의 시즌 리그 기준값 계산용 원시 기록을 반환한다."""

        statement = select(BattingSeasonStat).where(BattingSeasonStat.season == season)
        return list(self._session.scalars(statement).all())

    def list_pitching_seasons(self, player_id: int) -> list[PitchingSeasonStat]:
        """투구 기록을 시즌, 팀 순서로 반환한다."""

        statement = (
            select(PitchingSeasonStat)
            .options(joinedload(PitchingSeasonStat.team))
            .where(PitchingSeasonStat.player_id == player_id)
            .order_by(PitchingSeasonStat.season, PitchingSeasonStat.team_id)
        )
        return list(self._session.scalars(statement).unique().all())

    def team_defensive_efficiencies(
        self, team_seasons: set[tuple[int, int]]
    ) -> dict[tuple[int, int], float]:
        """팀-시즌별 인플레이 타구 아웃 비율(DER)을 계산한다."""

        if not team_seasons:
            return {}
        key_filter = tuple_(PitchingSeasonStat.season, PitchingSeasonStat.team_id).in_(
            team_seasons
        )
        pitching_statement = (
            select(
                PitchingSeasonStat.season,
                PitchingSeasonStat.team_id,
                func.sum(PitchingSeasonStat.batters_faced),
                func.sum(PitchingSeasonStat.hits_allowed),
                func.sum(PitchingSeasonStat.home_runs_allowed),
                func.sum(PitchingSeasonStat.walks_allowed),
                func.sum(PitchingSeasonStat.hit_batters),
                func.sum(PitchingSeasonStat.strikeouts),
            )
            .where(key_filter)
            .group_by(PitchingSeasonStat.season, PitchingSeasonStat.team_id)
        )
        error_statement = (
            select(
                BattingSeasonStat.season,
                BattingSeasonStat.team_id,
                func.sum(BattingSeasonStat.errors),
            )
            .where(tuple_(BattingSeasonStat.season, BattingSeasonStat.team_id).in_(team_seasons))
            .group_by(BattingSeasonStat.season, BattingSeasonStat.team_id)
        )
        errors = {
            (season, team_id): int(error_count or 0)
            for season, team_id, error_count in self._session.execute(error_statement)
        }
        results: dict[tuple[int, int], float] = {}
        for season, team_id, faced, hits, home_runs, walks, hit_batters, strikeouts in (
            self._session.execute(pitching_statement)
        ):
            efficiency = calculate_defensive_efficiency(
                batters_faced=int(faced),
                hits_allowed=int(hits),
                home_runs_allowed=int(home_runs),
                walks_allowed=int(walks),
                hit_batters=int(hit_batters),
                strikeouts=int(strikeouts),
                errors=errors.get((season, team_id), 0),
            )
            if efficiency is not None:
                results[(season, team_id)] = efficiency
        return results

    def league_metric_values(self, role: PlayerRole, season: int, metric: str) -> list[float]:
        """동일 시즌의 최소 표본 충족 선수군에서 지표 값을 조회한다."""

        model = BattingSeasonStat if role is PlayerRole.BATTING else PitchingSeasonStat
        opportunity = (
            BattingSeasonStat.plate_appearances >= 100
            if role is PlayerRole.BATTING
            else PitchingSeasonStat.innings_pitched_outs >= 90
        )
        column = getattr(model, metric)
        statement = select(column).where(
            model.season == season,
            opportunity,
            column.is_not(None),
        )
        return [float(value) for value in self._session.scalars(statement).all()]
