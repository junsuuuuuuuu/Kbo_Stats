"""단위/API 테스트에서 재사용하는 Repository 대역."""

from datetime import date

from app.models.player import Player, PlayerSourceProfile
from app.models.roster import TeamRoster
from app.models.stats import BattingSeasonStat, PitchingSeasonStat
from app.models.team import Team
from app.repositories.player import PlayerSearchCriteria
from app.repositories.team import TeamRosterSnapshot, TeamRosterSummary


def sample_player() -> Player:
    """동명이인 구분 정보와 타자 역할을 가진 최소 선수 객체를 만든다."""

    player = Player(
        player_id=68050,
        player_name="김도영",
        search_name="김도영",
        birth_date=date(2003, 10, 2),
    )
    player.profiles = [
        PlayerSourceProfile(
            player_id=68050,
            profile_role="BATTING",
            source_url="https://example.test/player/68050",
            bat_side="R",
            throw_side="R",
            height_cm=183,
            weight_kg=85,
            career="테스트 경력",
            draft="테스트 지명",
        )
    ]
    return player


class FakePlayerRepository:
    """전달된 조건과 호출 횟수를 기록하는 in-memory Repository."""

    def __init__(self) -> None:
        self.player: Player | None = sample_player()
        self.last_criteria: PlayerSearchCriteria | None = None
        self.batting_calls = 0
        self.pitching_calls = 0
        self.batting_stats: list[BattingSeasonStat] = []
        self.pitching_stats: list[PitchingSeasonStat] = []

    def search(self, criteria: PlayerSearchCriteria) -> tuple[list[Player], int]:
        self.last_criteria = criteria
        items = [self.player] if self.player is not None else []
        return items, len(items)

    def get_by_id(self, player_id: int) -> Player | None:
        if self.player is not None and self.player.player_id == player_id:
            return self.player
        return None

    def list_batting_seasons(self, _player_id: int) -> list[BattingSeasonStat]:
        self.batting_calls += 1
        return self.batting_stats

    def list_pitching_seasons(self, _player_id: int) -> list[PitchingSeasonStat]:
        self.pitching_calls += 1
        return self.pitching_stats


class FakeTeamRepository:
    """구단 API 테스트용 최신 로스터 대역."""

    def __init__(self) -> None:
        summary = TeamRosterSummary(
            team_id=1,
            team_code="SS",
            team_name="삼성",
            season=2026,
            as_of_date=date(2026, 7, 20),
            roster_count=1,
            pitcher_count=1,
            hitter_count=0,
        )
        member = TeamRoster(
            roster_id=1,
            season=2026,
            as_of_date=date(2026, 7, 20),
            team_id=1,
            team_code="SS",
            player_id=68050,
            position_code="P",
            uniform_number="18",
            bat_side="R",
            throw_side="R",
            height_cm=183,
            weight_kg=92,
            source_url="https://example.test/player/68050",
            is_active=True,
        )
        member.player = sample_player()
        member.team = Team(team_id=1, team_name="삼성")
        self.snapshot: TeamRosterSnapshot | None = TeamRosterSnapshot(summary, [member])

    def list_latest_rosters(self, _season: int) -> list[TeamRosterSummary]:
        return [self.snapshot.summary] if self.snapshot is not None else []

    def get_latest_roster(
        self, _team_code: str, _season: int
    ) -> TeamRosterSnapshot | None:
        return self.snapshot
