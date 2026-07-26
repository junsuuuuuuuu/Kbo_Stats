"""구단별 최신 1군 등록 로스터 조회 Repository."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.game_day import GameDaySnapshot
from app.models.roster import TeamRoster
from app.models.standing import TeamStanding
from app.models.team import Team


@dataclass(frozen=True, slots=True)
class TeamRosterSummary:
    team_id: int
    team_code: str
    team_name: str
    season: int
    as_of_date: date
    roster_count: int
    pitcher_count: int
    hitter_count: int


@dataclass(frozen=True, slots=True)
class TeamRosterSnapshot:
    summary: TeamRosterSummary
    members: list[TeamRoster]


@dataclass(frozen=True, slots=True)
class TeamRosterChanges:
    season: int
    team_code: str
    as_of_date: date
    previous_as_of_date: date | None
    registered: list[TeamRoster]
    removed: list[TeamRoster]


class TeamRepository(Protocol):
    def list_latest_rosters(self, season: int) -> list[TeamRosterSummary]: ...

    def get_latest_roster(self, team_code: str, season: int) -> TeamRosterSnapshot | None: ...

    def get_roster_changes(self, team_code: str, season: int) -> TeamRosterChanges | None: ...

    def get_latest_standing(self, team_code: str, season: int) -> TeamStanding | None: ...

    def get_latest_game_day(self, season: int) -> GameDaySnapshot | None: ...

    def get_game_day(self, season: int, game_date: date) -> GameDaySnapshot | None: ...


class SqlAlchemyTeamRepository:
    """최신 기준일 선택과 로스터 SQL 조회를 담당한다."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _summary_from_row(row: object) -> TeamRosterSummary:
        return TeamRosterSummary(
            team_id=row.team_id,  # type: ignore[attr-defined]
            team_code=row.team_code,  # type: ignore[attr-defined]
            team_name=row.team_name,  # type: ignore[attr-defined]
            season=row.season,  # type: ignore[attr-defined]
            as_of_date=row.as_of_date,  # type: ignore[attr-defined]
            roster_count=row.roster_count,  # type: ignore[attr-defined]
            pitcher_count=row.pitcher_count,  # type: ignore[attr-defined]
            hitter_count=row.hitter_count,  # type: ignore[attr-defined]
        )

    def _summary_statement(self, season: int, team_code: str | None = None):
        latest_dates = (
            select(
                TeamRoster.team_id,
                func.max(TeamRoster.as_of_date).label("as_of_date"),
            )
            .where(TeamRoster.season == season, TeamRoster.is_active.is_(True))
            .group_by(TeamRoster.team_id)
            .subquery()
        )
        statement = (
            select(
                Team.team_id.label("team_id"),
                TeamRoster.team_code.label("team_code"),
                Team.team_name.label("team_name"),
                TeamRoster.season.label("season"),
                TeamRoster.as_of_date.label("as_of_date"),
                func.count(TeamRoster.roster_id).label("roster_count"),
                func.sum(case((TeamRoster.position_code == "P", 1), else_=0)).label(
                    "pitcher_count"
                ),
                func.sum(case((TeamRoster.position_code != "P", 1), else_=0)).label("hitter_count"),
            )
            .join(Team, Team.team_id == TeamRoster.team_id)
            .join(
                latest_dates,
                (latest_dates.c.team_id == TeamRoster.team_id)
                & (latest_dates.c.as_of_date == TeamRoster.as_of_date),
            )
            .where(TeamRoster.season == season, TeamRoster.is_active.is_(True))
            .group_by(
                Team.team_id,
                TeamRoster.team_code,
                Team.team_name,
                TeamRoster.season,
                TeamRoster.as_of_date,
            )
        )
        if team_code is not None:
            statement = statement.where(TeamRoster.team_code == team_code)
        return statement

    def list_latest_rosters(self, season: int) -> list[TeamRosterSummary]:
        rows = self._session.execute(self._summary_statement(season).order_by(Team.team_name)).all()
        return [self._summary_from_row(row) for row in rows]

    def get_latest_roster(self, team_code: str, season: int) -> TeamRosterSnapshot | None:
        summary_row = self._session.execute(
            self._summary_statement(season, team_code)
        ).one_or_none()
        if summary_row is None:
            return None
        summary = self._summary_from_row(summary_row)
        position_order = case(
            (TeamRoster.position_code == "P", 1),
            (TeamRoster.position_code == "C", 2),
            (TeamRoster.position_code == "IF", 3),
            else_=4,
        )
        statement = (
            select(TeamRoster)
            .options(joinedload(TeamRoster.player), joinedload(TeamRoster.team))
            .where(
                TeamRoster.season == season,
                TeamRoster.as_of_date == summary.as_of_date,
                TeamRoster.team_code == team_code,
                TeamRoster.is_active.is_(True),
            )
            .order_by(position_order, TeamRoster.uniform_number, TeamRoster.player_id)
        )
        members = list(self._session.scalars(statement).unique().all())
        return TeamRosterSnapshot(summary=summary, members=members)

    def _roster_members_for_date(
        self,
        team_code: str,
        season: int,
        as_of_date: date,
    ) -> list[TeamRoster]:
        statement = (
            select(TeamRoster)
            .options(joinedload(TeamRoster.player), joinedload(TeamRoster.team))
            .where(
                TeamRoster.season == season,
                TeamRoster.as_of_date == as_of_date,
                TeamRoster.team_code == team_code,
                TeamRoster.is_active.is_(True),
            )
            .order_by(TeamRoster.player_id)
        )
        return list(self._session.scalars(statement).unique().all())

    def get_roster_changes(self, team_code: str, season: int) -> TeamRosterChanges | None:
        latest_date = self._session.scalar(
            select(func.max(TeamRoster.as_of_date)).where(
                TeamRoster.season == season,
                TeamRoster.team_code == team_code,
                TeamRoster.is_active.is_(True),
            )
        )
        if latest_date is None:
            return None

        previous_date = self._session.scalar(
            select(func.max(TeamRoster.as_of_date)).where(
                TeamRoster.season == season,
                TeamRoster.team_code == team_code,
                TeamRoster.as_of_date < latest_date,
                TeamRoster.is_active.is_(True),
            )
        )
        if previous_date is None:
            return TeamRosterChanges(
                season=season,
                team_code=team_code,
                as_of_date=latest_date,
                previous_as_of_date=None,
                registered=[],
                removed=[],
            )

        latest_members = self._roster_members_for_date(team_code, season, latest_date)
        previous_members = self._roster_members_for_date(team_code, season, previous_date)
        latest_by_player = {member.player_id: member for member in latest_members}
        previous_by_player = {member.player_id: member for member in previous_members}
        registered = [
            latest_by_player[player_id]
            for player_id in sorted(latest_by_player.keys() - previous_by_player.keys())
        ]
        removed = [
            previous_by_player[player_id]
            for player_id in sorted(previous_by_player.keys() - latest_by_player.keys())
        ]
        return TeamRosterChanges(
            season=season,
            team_code=team_code,
            as_of_date=latest_date,
            previous_as_of_date=previous_date,
            registered=registered,
            removed=removed,
        )

    def get_latest_standing(self, team_code: str, season: int) -> TeamStanding | None:
        """해당 시즌 구단의 가장 최근 전적 스냅샷을 반환한다."""

        latest_date = select(func.max(TeamStanding.as_of_date)).where(
            TeamStanding.season == season,
            TeamStanding.team_code == team_code,
        )
        statement = select(TeamStanding).where(
            TeamStanding.season == season,
            TeamStanding.team_code == team_code,
            TeamStanding.as_of_date == latest_date.scalar_subquery(),
        )
        return self._session.scalar(statement)

    def get_latest_game_day(self, season: int) -> GameDaySnapshot | None:
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        statement = (
            select(GameDaySnapshot)
            .where(
                GameDaySnapshot.season == season,
                GameDaySnapshot.game_date <= today,
            )
            .order_by(GameDaySnapshot.game_date.desc())
            .limit(1)
        )
        return self._session.scalar(statement)

    def get_game_day(self, season: int, game_date: date) -> GameDaySnapshot | None:
        statement = select(GameDaySnapshot).where(
            GameDaySnapshot.season == season,
            GameDaySnapshot.game_date == game_date,
        )
        return self._session.scalar(statement)
