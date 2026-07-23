"""단위/API 테스트에서 재사용하는 Repository 대역."""

from datetime import date

from app.models.game_day import GameDaySnapshot
from app.models.player import Player, PlayerSourceProfile
from app.models.roster import TeamRoster
from app.models.standing import TeamStanding
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
        self.metric_values: list[float] = []
        self.defensive_efficiencies: dict[tuple[int, int], float] = {}
        self.team_rankings: dict[tuple[int, int], int] = {}
        self.last_league_seasons: set[int] | None = None

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

    def list_league_batting_seasons(self, seasons: set[int]) -> list[BattingSeasonStat]:
        self.last_league_seasons = seasons
        return self.batting_stats

    def list_pitching_seasons(self, _player_id: int) -> list[PitchingSeasonStat]:
        self.pitching_calls += 1
        return self.pitching_stats

    def team_defensive_efficiencies(
        self, _team_seasons: set[tuple[int, int]]
    ) -> dict[tuple[int, int], float]:
        return self.defensive_efficiencies

    def team_standing_rankings(
        self, _team_seasons: set[tuple[int, int]]
    ) -> dict[tuple[int, int], int]:
        return self.team_rankings

    def league_metric_values(self, _role: object, _season: int, _metric: str) -> list[float]:
        return self.metric_values


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
        self.standing = TeamStanding(
            standing_id=1,
            season=2026,
            as_of_date=date(2026, 7, 20),
            team_id=1,
            team_code="SS",
            ranking=1,
            games=86,
            wins=52,
            losses=32,
            draws=2,
            winning_percentage=0.619,
            games_behind=0,
            recent_ten="8승0무2패",
            streak="2승",
            home_record="27-1-15",
            away_record="25-1-17",
            source_url="https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx",
        )
        self.standing.team = member.team
        payload = {
            "game_date": "2026-07-20",
            "games": [],
            "source_url": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
        }
        self.game_day: GameDaySnapshot | None = GameDaySnapshot(
            snapshot_id=1,
            season=2026,
            game_date=date(2026, 7, 20),
            source_url=payload["source_url"],
            payload=payload,
        )

    def list_latest_rosters(self, _season: int) -> list[TeamRosterSummary]:
        return [self.snapshot.summary] if self.snapshot is not None else []

    def get_latest_roster(self, _team_code: str, _season: int) -> TeamRosterSnapshot | None:
        return self.snapshot

    def get_latest_standing(self, _team_code: str, _season: int) -> TeamStanding | None:
        return self.standing

    def get_latest_game_day(self, _season: int) -> GameDaySnapshot | None:
        return self.game_day

    def get_game_day(self, _season: int, _game_date: date) -> GameDaySnapshot | None:
        return self.game_day
