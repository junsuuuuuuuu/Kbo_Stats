"""구단 목록과 최신 1군 로스터 조회 유스케이스."""

from datetime import date

from app.core.exceptions import GameDayNotFoundError, TeamRosterNotFoundError
from app.models.game_day import GameDaySnapshot
from app.models.standing import TeamStanding
from app.repositories.team import TeamRepository, TeamRosterSnapshot, TeamRosterSummary


class TeamService:
    def __init__(self, repository: TeamRepository) -> None:
        self._repository = repository

    def list_teams(self, season: int) -> list[TeamRosterSummary]:
        """해당 시즌에 수집된 최신 구단 로스터 요약을 반환한다."""

        return self._repository.list_latest_rosters(season)

    def get_roster(self, team_code: str, season: int) -> TeamRosterSnapshot:
        """구단 코드를 정규화하고 로스터가 없으면 도메인 오류를 발생시킨다."""

        normalized_code = team_code.strip().upper()
        snapshot = self._repository.get_latest_roster(normalized_code, season)
        if snapshot is None:
            raise TeamRosterNotFoundError(normalized_code, season)
        return snapshot

    def get_standing(self, team_code: str, season: int) -> TeamStanding | None:
        """구단의 최신 전적을 반환한다. 시즌 개막 전에는 None일 수 있다."""

        return self._repository.get_latest_standing(team_code.strip().upper(), season)

    def get_latest_game_day(self, season: int) -> GameDaySnapshot:
        snapshot = self._repository.get_latest_game_day(season)
        if snapshot is None:
            raise GameDayNotFoundError(season)
        return snapshot

    def get_game_day(self, game_date: date, season: int) -> GameDaySnapshot:
        snapshot = self._repository.get_game_day(season, game_date)
        if snapshot is None:
            raise GameDayNotFoundError(season, game_date.isoformat())
        return snapshot
