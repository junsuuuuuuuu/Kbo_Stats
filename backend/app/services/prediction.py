"""Explainable recent-form MVP game prediction service."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Protocol

from app.core.exceptions import PredictionGameNotFoundError
from app.models.standing import TeamStanding
from app.schemas.prediction import (
    GamePredictionResponse,
    PitcherOpponentAnalysis,
    PitcherSeasonAnalysis,
    PredictionForm,
    PredictionRecord,
    PredictionScore,
    PredictionTeam,
    PredictionTeamMetrics,
    StartingPitcherAnalysis,
)
from app.services.kbo_game_log import PitchingAppearance, kbo_game_log_client
from app.services.kbo_team_schedule import TEAM_NAMES, LatestGameSummary, TeamGameResult
from app.services.recent_boxscore import (
    RecentBoxscoreMetrics,
    aggregate_boxscores,
    innings_to_outs,
)


class PredictionScheduleClient(Protocol):
    def game_day(self, target_date: str, season: int): ...

    def results(self, team_code: str, season: int) -> list[TeamGameResult]: ...

    def game_detail(self, game_id: str, season: int): ...


class PredictionRepository(Protocol):
    def get_latest_standing(self, team_code: str, season: int) -> TeamStanding | None: ...

    def find_pitcher(self, player_name: str, team_code: str, season: int): ...

    def list_pitching_seasons(self, player_id: int): ...


class PredictionBoxscoreRepository(Protocol):
    def recent_metrics(
        self, game_ids: list[str], team_code: str, expected_games: int
    ) -> RecentBoxscoreMetrics: ...


@dataclass(frozen=True)
class _TeamInputs:
    standing: TeamStanding | None
    results: list[TeamGameResult]
    recent_results: list[TeamGameResult]
    recent_boxscores: RecentBoxscoreMetrics = RecentBoxscoreMetrics()


_RECORD_PATTERN = re.compile(r"^(\d+)[-:](\d+)[-:](\d+)$")
logger = logging.getLogger("prediction")


def outs_to_display(outs: int) -> float:
    return (outs // 3) + (outs % 3) / 10


def _record(wins: int, losses: int, draws: int, status: str = "available") -> PredictionRecord:
    games = wins + losses + draws
    return PredictionRecord(
        games=games,
        wins=wins,
        losses=losses,
        draws=draws,
        winning_percentage=(wins + draws * 0.5) / games if games else None,
        status=status if games else "unavailable",
    )


def _parse_record(value: str | None) -> PredictionRecord:
    if not value:
        return _record(0, 0, 0)
    match = _RECORD_PATTERN.match(value.strip())
    if match is None:
        return _record(0, 0, 0)
    wins, draws, losses = (int(part) for part in match.groups())
    return _record(wins, losses, draws)


def _standing_record(standing: TeamStanding | None) -> PredictionRecord:
    return _record(standing.wins, standing.losses, standing.draws) if standing else _record(0, 0, 0)


def _recent_results(results: list[TeamGameResult], before: date) -> list[TeamGameResult]:
    eligible: list[TeamGameResult] = []
    for result in results:
        try:
            result_date = date.fromisoformat(result.game_date)
        except ValueError:
            continue
        if result_date >= before or result.result not in {"W", "L", "D"}:
            continue
        if result.team_score < 0 or result.opponent_score < 0:
            continue
        eligible.append(result)
    return sorted(eligible, key=lambda item: item.game_date, reverse=True)[:10]


def _record_from_results(results: list[TeamGameResult]) -> PredictionRecord:
    return _record(
        sum(result.result == "W" for result in results),
        sum(result.result == "L" for result in results),
        sum(result.result == "D" for result in results),
    )


def _metrics(
    standing: TeamStanding | None,
    recent: list[TeamGameResult],
    boxscores: RecentBoxscoreMetrics | None = None,
) -> PredictionTeamMetrics:
    recent_record = _record_from_results(recent)
    if not recent:
        return PredictionTeamMetrics(
            boxscore_games=boxscores.boxscore_games if boxscores else 0,
            expected_boxscore_games=boxscores.expected_games if boxscores else 0,
            season_win_percentage=float(standing.winning_percentage) if standing else None,
            ranking=standing.ranking if standing else None,
            recent_batting_average=boxscores.batting_average if boxscores else None,
            recent_batting_average_status=boxscores.batting_average_status
            if boxscores
            else "unavailable",
            recent_on_base_percentage_status=boxscores.on_base_percentage_status
            if boxscores
            else "unavailable",
            recent_slugging_percentage_status=boxscores.slugging_percentage_status
            if boxscores
            else "unavailable",
            recent_ops_status=boxscores.ops_status if boxscores else "unavailable",
            recent_on_base_percentage=boxscores.on_base_percentage if boxscores else None,
            recent_slugging_percentage=boxscores.slugging_percentage if boxscores else None,
            recent_ops=boxscores.ops if boxscores else None,
            recent_hits_per_game=boxscores.hits_per_game if boxscores else None,
            recent_home_runs=boxscores.home_runs if boxscores else None,
            recent_walks=boxscores.walks if boxscores else None,
            recent_era=boxscores.era if boxscores else None,
            recent_whip=boxscores.whip if boxscores else None,
            recent_strikeouts_per_game=boxscores.strikeouts_per_game if boxscores else None,
            batting_status=boxscores.batting_status if boxscores else "unavailable",
            pitching_status=boxscores.pitching_status if boxscores else "unavailable",
            status="unavailable" if standing is None else "partial",
        )
    runs_for = mean(result.team_score for result in recent)
    runs_against = mean(result.opponent_score for result in recent)
    return PredictionTeamMetrics(
        boxscore_games=boxscores.boxscore_games if boxscores else 0,
        expected_boxscore_games=boxscores.expected_games if boxscores else 0,
        recent_games_count=len(recent),
        recent_games_status="complete" if len(recent) == 10 else "partial",
        recent_win_percentage=recent_record.winning_percentage,
        season_win_percentage=float(standing.winning_percentage) if standing else None,
        ranking=standing.ranking if standing else None,
        recent_runs_for_per_game=round(runs_for, 2),
        recent_runs_against_per_game=round(runs_against, 2),
        recent_run_differential=round(runs_for - runs_against, 2),
        recent_batting_average=boxscores.batting_average if boxscores else None,
        recent_batting_average_status=boxscores.batting_average_status
        if boxscores
        else "unavailable",
        recent_on_base_percentage_status=boxscores.on_base_percentage_status
        if boxscores
        else "unavailable",
        recent_slugging_percentage_status=boxscores.slugging_percentage_status
        if boxscores
        else "unavailable",
        recent_ops_status=boxscores.ops_status if boxscores else "unavailable",
        recent_on_base_percentage=boxscores.on_base_percentage if boxscores else None,
        recent_slugging_percentage=boxscores.slugging_percentage if boxscores else None,
        recent_ops=boxscores.ops if boxscores else None,
        recent_hits_per_game=boxscores.hits_per_game if boxscores else None,
        recent_home_runs=boxscores.home_runs if boxscores else None,
        recent_walks=boxscores.walks if boxscores else None,
        recent_era=boxscores.era if boxscores else None,
        recent_whip=boxscores.whip if boxscores else None,
        recent_strikeouts_per_game=boxscores.strikeouts_per_game if boxscores else None,
        batting_status=boxscores.batting_status if boxscores else "unavailable",
        pitching_status=boxscores.pitching_status if boxscores else "unavailable",
        status="complete" if standing else "partial",
    )


def _opponent_matches(value: str, team_code: str) -> bool:
    normalized = "".join(value.split()).lower()
    team_name = "".join(TEAM_NAMES.get(team_code, "").split()).lower()
    return normalized in {team_code.lower(), team_name}


def _pitcher_innings_outs(appearances: list[PitchingAppearance]) -> int:
    return sum(innings_to_outs(appearance.innings_pitched) or 0 for appearance in appearances)


def _pitcher_season_analysis(
    stats: list[object],
    appearances: list[PitchingAppearance],
    season: int,
    target_date: date,
) -> PitcherSeasonAnalysis:
    season_stats = [stat for stat in stats if getattr(stat, "season", None) == season]
    outs = sum(int(getattr(stat, "innings_pitched_outs", 0)) for stat in season_stats)
    earned_runs = sum(int(getattr(stat, "earned_runs", 0)) for stat in season_stats)
    hits = sum(int(getattr(stat, "hits_allowed", 0)) for stat in season_stats)
    walks = sum(int(getattr(stat, "walks_allowed", 0)) for stat in season_stats)
    strikeouts = sum(int(getattr(stat, "strikeouts", 0)) for stat in season_stats)
    wins = sum(int(getattr(stat, "wins", 0)) for stat in season_stats)
    losses = sum(int(getattr(stat, "losses", 0)) for stat in season_stats)
    games = sum(int(getattr(stat, "games", 0)) for stat in season_stats)
    prior_appearances = [
        appearance
        for appearance in appearances
        if date.fromisoformat(appearance.game_date) < target_date
    ]
    last_date = max(
        (date.fromisoformat(appearance.game_date) for appearance in prior_appearances),
        default=None,
    )
    if not season_stats and not prior_appearances:
        return PitcherSeasonAnalysis(status="unavailable")
    return PitcherSeasonAnalysis(
        era=earned_runs * 27 / outs if outs else None,
        whip=(hits + walks) * 3 / outs if outs else None,
        innings=outs_to_display(outs) if outs else None,
        strikeouts=strikeouts
        if season_stats
        else sum(item.strikeouts for item in prior_appearances),
        walks=walks if season_stats else sum(item.walks_allowed for item in prior_appearances),
        hits=hits if season_stats else sum(item.hits_allowed for item in prior_appearances),
        wins=wins if season_stats else None,
        losses=losses if season_stats else None,
        games=games if season_stats else len(prior_appearances),
        last_appearance_date=last_date,
        status="available" if outs else "partial",
    )


def _pitcher_opponent_analysis(
    appearances: list[PitchingAppearance], opponent_code: str, target_date: date
) -> PitcherOpponentAnalysis:
    matching = [
        appearance
        for appearance in appearances
        if date.fromisoformat(appearance.game_date) < target_date
        and _opponent_matches(appearance.opponent, opponent_code)
    ]
    if not matching:
        return PitcherOpponentAnalysis(status="unavailable")
    outs = _pitcher_innings_outs(matching)
    earned_runs = sum(item.earned_runs for item in matching)
    hits = sum(item.hits_allowed for item in matching)
    walks = sum(item.walks_allowed + item.hit_batters for item in matching)
    starts = sum(
        "선발" in item.appearance_type or "start" in item.appearance_type.lower()
        for item in matching
    )
    return PitcherOpponentAnalysis(
        games=len(matching),
        starts=starts,
        innings=outs_to_display(outs) if outs else None,
        era=earned_runs * 27 / outs if outs else None,
        whip=(hits + walks) * 3 / outs if outs else None,
        hits=hits,
        strikeouts=sum(item.strikeouts for item in matching),
        wins=sum(item.result in {"승", "W"} for item in matching),
        losses=sum(item.result in {"패", "L"} for item in matching),
        status="available" if outs else "partial",
    )


def _team_prediction(code: str, name: str, inputs: _TeamInputs) -> PredictionTeam:
    standing = inputs.standing
    return PredictionTeam(
        team_code=code,
        team_name=name,
        season_record=_standing_record(standing),
        home_record=_parse_record(standing.home_record if standing else None),
        away_record=_parse_record(standing.away_record if standing else None),
        recent_form=PredictionForm(
            results=[result.result for result in inputs.recent_results],
            record=_record_from_results(inputs.recent_results),
        ),
        metrics=_metrics(standing, inputs.recent_results, inputs.recent_boxscores),
    )


def _probability(
    away: _TeamInputs,
    home: _TeamInputs,
    head_to_head: PredictionRecord,
    away_pitcher: StartingPitcherAnalysis | None = None,
    home_pitcher: StartingPitcherAnalysis | None = None,
):
    signals: list[tuple[float, float, str]] = []
    away_metrics = _metrics(away.standing, away.recent_results, away.recent_boxscores)
    home_metrics = _metrics(home.standing, home.recent_results, home.recent_boxscores)
    if away.standing and home.standing:
        signals.append(
            (
                0.20,
                float(away.standing.winning_percentage) - float(home.standing.winning_percentage),
                "시즌 승률",
            )
        )
    away_recent = _record_from_results(away.recent_results)
    home_recent = _record_from_results(home.recent_results)
    if away_recent.winning_percentage is not None and home_recent.winning_percentage is not None:
        signals.append(
            (
                0.30,
                away_recent.winning_percentage - home_recent.winning_percentage,
                "최근 10경기 승률",
            )
        )
    if (
        away_metrics.recent_runs_for_per_game is not None
        and home_metrics.recent_runs_for_per_game is not None
    ):
        signals.append(
            (
                0.15,
                max(
                    -1,
                    min(
                        1,
                        (
                            away_metrics.recent_runs_for_per_game
                            - home_metrics.recent_runs_for_per_game
                        )
                        / 5,
                    ),
                ),
                "최근 10경기 평균 득점",
            )
        )
    if (
        away_metrics.recent_runs_against_per_game is not None
        and home_metrics.recent_runs_against_per_game is not None
    ):
        signals.append(
            (
                0.15,
                max(
                    -1,
                    min(
                        1,
                        (
                            home_metrics.recent_runs_against_per_game
                            - away_metrics.recent_runs_against_per_game
                        )
                        / 5,
                    ),
                ),
                "최근 10경기 평균 실점",
            )
        )
    if (
        away_metrics.recent_run_differential is not None
        and home_metrics.recent_run_differential is not None
    ):
        signals.append(
            (
                0.10,
                max(
                    -1,
                    min(
                        1,
                        (
                            away_metrics.recent_run_differential
                            - home_metrics.recent_run_differential
                        )
                        / 10,
                    ),
                ),
                "최근 10경기 득실차",
            )
        )
    if away_metrics.recent_ops is not None and home_metrics.recent_ops is not None:
        signals.append((0.10, away_metrics.recent_ops - home_metrics.recent_ops, "최근 10경기 OPS"))
    away_home = _parse_record(away.standing.home_record if away.standing else None)
    home_away = _parse_record(home.standing.away_record if home.standing else None)
    if away_home.winning_percentage is not None and home_away.winning_percentage is not None:
        signals.append(
            (0.05, away_home.winning_percentage - home_away.winning_percentage, "홈·원정 성적")
        )
    if head_to_head.winning_percentage is not None:
        signals.append((0.05, head_to_head.winning_percentage - 0.5, "상대전적"))
    if away_pitcher and home_pitcher and away_pitcher.season and home_pitcher.season:
        if away_pitcher.season.era is not None and home_pitcher.season.era is not None:
            signals.append(
                (
                    0.10,
                    max(-1, min(1, (home_pitcher.season.era - away_pitcher.season.era) / 5)),
                    "선발투수 시즌 ERA",
                )
            )
        if away_pitcher.season.whip is not None and home_pitcher.season.whip is not None:
            signals.append(
                (
                    0.05,
                    max(-1, min(1, (home_pitcher.season.whip - away_pitcher.season.whip) / 2)),
                    "선발투수 시즌 WHIP",
                )
            )
    if (
        away_pitcher
        and home_pitcher
        and away_pitcher.vs_opponent
        and home_pitcher.vs_opponent
        and away_pitcher.vs_opponent.status == "available"
        and home_pitcher.vs_opponent.status == "available"
        and away_pitcher.vs_opponent.games >= 2
        and home_pitcher.vs_opponent.games >= 2
        and away_pitcher.vs_opponent.era is not None
        and home_pitcher.vs_opponent.era is not None
    ):
        signals.append(
            (
                0.05,
                max(-1, min(1, (home_pitcher.vs_opponent.era - away_pitcher.vs_opponent.era) / 5)),
                "상대 구단 상대 ERA",
            )
        )
    if not signals:
        return 0.5, ["사용 가능한 최근 경기 데이터가 부족합니다."], 0.15
    total_weight = sum(item[0] for item in signals)
    score = sum(weight * difference for weight, difference, _ in signals) / total_weight
    probability = max(0.05, min(0.95, 0.5 + score / 2))
    confidence_score = min(0.9, 0.20 + 0.65 * len(signals) / 10)
    if (
        away_pitcher
        and home_pitcher
        and (away_pitcher.status != "available" or home_pitcher.status != "available")
    ):
        confidence_score *= 0.8
    return probability, [label for _, _, label in sorted(signals, reverse=True)], confidence_score


def _find_game(client: PredictionScheduleClient, game_id: str, season: int) -> LatestGameSummary:
    try:
        target_date = date.fromisoformat(game_id[:8])
    except ValueError as exception:
        raise PredictionGameNotFoundError(game_id, season) from exception
    if target_date.year != season:
        raise PredictionGameNotFoundError(game_id, season)
    day = client.game_day(target_date.isoformat(), season)
    for game in day.games:
        if game.game_id == game_id:
            return game
    raise PredictionGameNotFoundError(game_id, season)


class GamePredictionService:
    def __init__(
        self,
        repository: PredictionRepository,
        client: PredictionScheduleClient,
        player_repository: PredictionRepository | None = None,
        boxscore_repository: PredictionBoxscoreRepository | None = None,
    ) -> None:
        self._repository = repository
        self._client = client
        self._player_repository = player_repository
        self._boxscore_repository = boxscore_repository

    def _recent_boxscores(
        self, results: list[TeamGameResult], team_code: str, season: int
    ) -> RecentBoxscoreMetrics:
        game_ids = [result.game_id for result in results if result.game_id]
        if self._boxscore_repository is not None and game_ids:
            stored = self._boxscore_repository.recent_metrics(
                game_ids, team_code, len(results)
            )
            if stored.boxscore_games:
                return stored
        details = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._client.game_detail, game_id, season): game_id
                for game_id in game_ids
            }
            for future in as_completed(futures):
                game_id = futures[future]
                try:
                    details.append(future.result())
                except Exception as exception:  # noqa: BLE001 - one failed detail must not fail prediction
                    logger.warning(
                        "prediction_boxscore_failed game_id=%s team=%s error=%r",
                        game_id,
                        team_code,
                        exception,
                    )
        return aggregate_boxscores(details, team_code, expected_games=len(results))

    def _starting_pitcher(
        self,
        name: str | None,
        team_code: str,
        opponent_code: str,
        season: int,
        target_date: date,
    ) -> StartingPitcherAnalysis:
        if not name:
            return StartingPitcherAnalysis(status="unavailable", note="선발투수 미정")
        player_repository = self._player_repository or self._repository
        finder = getattr(player_repository, "find_pitcher", None)
        if finder is None:
            return StartingPitcherAnalysis(name=name, status="available")
        player = finder(name, team_code, season)
        if player is None:
            return StartingPitcherAnalysis(
                name=name,
                status="unverified",
                note="일정의 선발투수 이름과 선수 기록을 매칭하지 못했습니다.",
            )
        try:
            appearances = kbo_game_log_client.pitching_appearances(player.player_id, season)
        except Exception as exception:  # noqa: BLE001 - pitcher detail is optional
            logger.warning(
                "prediction_pitcher_log_failed player_id=%s error=%r",
                player.player_id,
                exception,
            )
            appearances = []
        return StartingPitcherAnalysis(
            name=player.player_name,
            status="available",
            season=_pitcher_season_analysis(
                player_repository.list_pitching_seasons(player.player_id),
                appearances,
                season,
                target_date,
            ),
            vs_opponent=_pitcher_opponent_analysis(appearances, opponent_code, target_date),
        )

    def predict(self, game_id: str, season: int) -> GamePredictionResponse:
        game = _find_game(self._client, game_id.upper(), season)
        target_date = date.fromisoformat(game.game_id[:8])
        away_code, home_code = game.away.team_code, game.home.team_code
        away_results = self._client.results(away_code, season)
        home_results = self._client.results(home_code, season)
        away_inputs = _TeamInputs(
            self._repository.get_latest_standing(away_code, season),
            away_results,
            _recent_results(away_results, target_date),
            RecentBoxscoreMetrics(),
        )
        home_inputs = _TeamInputs(
            self._repository.get_latest_standing(home_code, season),
            home_results,
            _recent_results(home_results, target_date),
            RecentBoxscoreMetrics(),
        )
        away_inputs = _TeamInputs(
            away_inputs.standing,
            away_inputs.results,
            away_inputs.recent_results,
            self._recent_boxscores(away_inputs.recent_results, away_code, season),
        )
        home_inputs = _TeamInputs(
            home_inputs.standing,
            home_inputs.results,
            home_inputs.recent_results,
            self._recent_boxscores(home_inputs.recent_results, home_code, season),
        )
        h2h = _record_from_results(
            [
                result
                for result in away_inputs.recent_results
                if result.opponent == game.home.team_name
            ]
        )
        away_team = _team_prediction(away_code, game.away.team_name, away_inputs)
        home_team = _team_prediction(home_code, game.home.team_name, home_inputs)
        away_pitcher = self._starting_pitcher(
            game.away_starting_pitcher, away_code, home_code, season, target_date
        )
        home_pitcher = self._starting_pitcher(
            game.home_starting_pitcher, home_code, away_code, season, target_date
        )
        away_probability, reasons, confidence_score = _probability(
            away_inputs, home_inputs, h2h, away_pitcher, home_pitcher
        )
        home_probability = round(1 - away_probability, 4)
        expected = PredictionScore(
            away=round(mean(result.team_score for result in away_inputs.recent_results))
            if away_inputs.recent_results
            else None,
            home=round(mean(result.team_score for result in home_inputs.recent_results))
            if home_inputs.recent_results
            else None,
        )
        favored = away_team if away_probability > home_probability else home_team
        confidence = (
            "low" if confidence_score < 0.5 else "medium" if confidence_score < 0.75 else "high"
        )
        return GamePredictionResponse(
            game_id=game.game_id,
            season=season,
            game_date=target_date,
            start_time=game.start_time,
            stadium=game.stadium,
            away=away_team,
            home=home_team,
            away_starting_pitcher=away_pitcher,
            home_starting_pitcher=home_pitcher,
            head_to_head=h2h,
            away_win_probability=round(away_probability, 4),
            home_win_probability=home_probability,
            favored_team_code=favored.team_code if confidence_score >= 0.35 else None,
            favored_team_name=favored.team_name if confidence_score >= 0.35 else None,
            expected_score=expected,
            confidence=confidence,
            confidence_score=round(confidence_score, 4),
            key_reasons=reasons,
            explanation=(
                "예측 대상 경기일 이전 종료 경기 중 "
                f"최근 {len(away_inputs.recent_results)}경기를 기준으로 "
                "승률·득점·실점·득실차를 계산했습니다. "
                "타율·OPS·ERA·WHIP은 박스스코어 데이터가 없어 "
                "임의로 계산하지 않았습니다."
            ),
        )
