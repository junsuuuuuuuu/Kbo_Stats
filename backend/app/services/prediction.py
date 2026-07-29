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
    PredictionForm,
    PredictionRecord,
    PredictionScore,
    PredictionTeam,
    PredictionTeamMetrics,
    StartingPitcherAnalysis,
)
from app.services.kbo_team_schedule import LatestGameSummary, TeamGameResult
from app.services.recent_boxscore import RecentBoxscoreMetrics, aggregate_boxscores


class PredictionScheduleClient(Protocol):
    def game_day(self, target_date: str, season: int): ...

    def results(self, team_code: str, season: int) -> list[TeamGameResult]: ...

    def game_detail(self, game_id: str, season: int): ...


class PredictionRepository(Protocol):
    def get_latest_standing(self, team_code: str, season: int) -> TeamStanding | None: ...


@dataclass(frozen=True)
class _TeamInputs:
    standing: TeamStanding | None
    results: list[TeamGameResult]
    recent_results: list[TeamGameResult]
    recent_boxscores: RecentBoxscoreMetrics = RecentBoxscoreMetrics()


_RECORD_PATTERN = re.compile(r"^(\d+)[-:](\d+)[-:](\d+)$")
logger = logging.getLogger("prediction")


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
            season_win_percentage=float(standing.winning_percentage) if standing else None,
            ranking=standing.ranking if standing else None,
            recent_batting_average=boxscores.batting_average if boxscores else None,
            recent_ops=boxscores.ops if boxscores else None,
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
        recent_games_count=len(recent),
        recent_games_status="complete" if len(recent) == 10 else "partial",
        recent_win_percentage=recent_record.winning_percentage,
        season_win_percentage=float(standing.winning_percentage) if standing else None,
        ranking=standing.ranking if standing else None,
        recent_runs_for_per_game=round(runs_for, 2),
        recent_runs_against_per_game=round(runs_against, 2),
        recent_run_differential=round(runs_for - runs_against, 2),
        recent_batting_average=boxscores.batting_average if boxscores else None,
        recent_ops=boxscores.ops if boxscores else None,
        recent_era=boxscores.era if boxscores else None,
        recent_whip=boxscores.whip if boxscores else None,
        recent_strikeouts_per_game=boxscores.strikeouts_per_game if boxscores else None,
        batting_status=boxscores.batting_status if boxscores else "unavailable",
        pitching_status=boxscores.pitching_status if boxscores else "unavailable",
        status="complete" if standing else "partial",
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


def _probability(away: _TeamInputs, home: _TeamInputs, head_to_head: PredictionRecord):
    signals: list[tuple[float, float, str]] = []
    away_metrics = _metrics(away.standing, away.recent_results)
    home_metrics = _metrics(home.standing, home.recent_results)
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
    away_home = _parse_record(away.standing.home_record if away.standing else None)
    home_away = _parse_record(home.standing.away_record if home.standing else None)
    if away_home.winning_percentage is not None and home_away.winning_percentage is not None:
        signals.append(
            (0.05, away_home.winning_percentage - home_away.winning_percentage, "홈·원정 성적")
        )
    if head_to_head.winning_percentage is not None:
        signals.append((0.05, head_to_head.winning_percentage - 0.5, "상대전적"))
    if not signals:
        return 0.5, ["사용 가능한 최근 경기 데이터가 부족합니다."], 0.15
    total_weight = sum(item[0] for item in signals)
    score = sum(weight * difference for weight, difference, _ in signals) / total_weight
    probability = max(0.05, min(0.95, 0.5 + score / 2))
    confidence_score = min(0.9, 0.20 + 0.65 * len(signals) / 7)
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
    def __init__(self, repository: PredictionRepository, client: PredictionScheduleClient) -> None:
        self._repository = repository
        self._client = client

    def _recent_boxscores(
        self, results: list[TeamGameResult], team_code: str, season: int
    ) -> RecentBoxscoreMetrics:
        game_ids = [result.game_id for result in results if result.game_id]
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
        return aggregate_boxscores(details, team_code)

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
        away_probability, reasons, confidence_score = _probability(away_inputs, home_inputs, h2h)
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
            away_starting_pitcher=StartingPitcherAnalysis(
                name=game.away_starting_pitcher,
                status="available" if game.away_starting_pitcher else "unavailable",
                note=None if game.away_starting_pitcher else "선발투수 미정",
            ),
            home_starting_pitcher=StartingPitcherAnalysis(
                name=game.home_starting_pitcher,
                status="available" if game.home_starting_pitcher else "unavailable",
                note=None if game.home_starting_pitcher else "선발투수 미정",
            ),
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
