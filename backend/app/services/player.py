"""선수 검색과 상세 조회 유스케이스."""

from dataclasses import dataclass
from statistics import fmean

from app.analytics.batting_metrics import BattingMetricValues, calculate_batting_metrics
from app.core.exceptions import PlayerNotFoundError
from app.models.player import Player
from app.models.stats import BattingSeasonStat, PitchingSeasonStat
from app.repositories.player import PlayerRepository, PlayerSearchCriteria
from app.schemas.player import PlayerRole


@dataclass(frozen=True, slots=True)
class PlayerPage:
    """Service의 HTTP 비종속 페이지 결과."""

    items: list[Player]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class PlayerSeasons:
    """선수 신원과 역할별 시즌 기록 묶음."""

    player: Player
    batting: list[BattingSeasonStat]
    pitching: list[PitchingSeasonStat]
    defensive_efficiencies: dict[tuple[int, int], float]
    batting_metrics: dict[int, BattingMetricValues]


@dataclass(frozen=True, slots=True)
class LeagueBenchmark:
    metric: str
    player_value: float
    league_average: float
    percentile: float
    sample_size: int
    higher_is_better: bool


BENCHMARK_METRICS = {
    PlayerRole.BATTING: (
        "batting_average",
        "on_base_plus_slugging",
        "home_runs",
        "runs_batted_in",
    ),
    PlayerRole.PITCHING: (
        "earned_run_average",
        "strikeouts",
        "wins",
        "saves",
    ),
}
LOWER_IS_BETTER = {"earned_run_average"}


class PlayerService:
    """검색 입력 정규화와 선수 존재 규칙을 담당한다."""

    def __init__(self, repository: PlayerRepository) -> None:
        self._repository = repository

    @staticmethod
    def normalize_search_name(value: str | None) -> str | None:
        """DB의 search_name 생성 규칙과 동일하게 공백을 제거하고 소문자화한다."""

        if value is None:
            return None
        normalized = "".join(value.split()).lower()
        return normalized or None

    def search_players(
        self,
        *,
        query: str | None,
        role: PlayerRole | None,
        season: int | None,
        team: str | None,
        page: int,
        page_size: int,
    ) -> PlayerPage:
        """검색 조건을 Repository 기준으로 변환해 페이지 결과를 만든다."""

        criteria = PlayerSearchCriteria(
            query=self.normalize_search_name(query),
            role=role,
            season=season,
            team=team.strip() if team else None,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        players, total = self._repository.search(criteria)
        return PlayerPage(players, page, page_size, total)

    def get_player(self, player_id: int) -> Player:
        """선수가 없으면 Repository 결과 대신 명시적 도메인 예외를 발생시킨다."""

        player = self._repository.get_by_id(player_id)
        if player is None:
            raise PlayerNotFoundError(player_id)
        return player

    def get_player_seasons(self, player_id: int, role: PlayerRole | None) -> PlayerSeasons:
        """요청 역할만 조회해 불필요한 DB 접근을 피한다."""

        player = self.get_player(player_id)
        batting = (
            self._repository.list_batting_seasons(player_id)
            if role in (None, PlayerRole.BATTING)
            else []
        )
        pitching = (
            self._repository.list_pitching_seasons(player_id)
            if role in (None, PlayerRole.PITCHING)
            else []
        )
        defensive_efficiencies = self._repository.team_defensive_efficiencies(
            {(row.season, row.team_id) for row in batting}
        )
        league_by_season = {
            season: self._repository.list_league_batting_seasons(season)
            for season in {row.season for row in batting}
        }
        batting_metrics = {
            id(row): calculate_batting_metrics(row, league_by_season[row.season])
            for row in batting
            if hasattr(row, "plate_appearances")
        }
        return PlayerSeasons(player, batting, pitching, defensive_efficiencies, batting_metrics)

    def get_league_benchmarks(
        self, player_id: int, role: PlayerRole, season: int
    ) -> list[LeagueBenchmark]:
        """선수 기록을 같은 시즌의 일정 표본 이상 선수군과 비교한다."""

        self.get_player(player_id)
        rows = (
            self._repository.list_batting_seasons(player_id)
            if role is PlayerRole.BATTING
            else self._repository.list_pitching_seasons(player_id)
        )
        player_row = next((row for row in reversed(rows) if row.season == season), None)
        if player_row is None:
            return []

        results: list[LeagueBenchmark] = []
        for metric in BENCHMARK_METRICS[role]:
            raw_value = getattr(player_row, metric)
            if raw_value is None:
                continue
            value = float(raw_value)
            distribution = self._repository.league_metric_values(role, season, metric)
            if not distribution:
                continue
            lower_is_better = metric in LOWER_IS_BETTER
            better = sum(
                candidate > value if lower_is_better else candidate < value
                for candidate in distribution
            )
            equal = sum(candidate == value for candidate in distribution)
            percentile = (better + equal * 0.5) / len(distribution) * 100
            results.append(
                LeagueBenchmark(
                    metric=metric,
                    player_value=value,
                    league_average=fmean(distribution),
                    percentile=round(percentile, 1),
                    sample_size=len(distribution),
                    higher_is_better=not lower_is_better,
                )
            )
        return results
