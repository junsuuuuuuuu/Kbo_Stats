"""Explainable, replaceable MVP game prediction service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Protocol

from app.core.exceptions import PredictionGameNotFoundError
from app.models.standing import TeamStanding
from app.schemas.prediction import (
    GamePredictionResponse,
    PredictionRecord,
    PredictionScore,
    PredictionTeam,
    PredictionTeamMetrics,
    StartingPitcherAnalysis,
)
from app.services.kbo_team_schedule import LatestGameSummary, TeamGameResult


class PredictionScheduleClient(Protocol):
    def game_day(self, target_date: str, season: int): ...

    def results(self, team_code: str, season: int) -> list[TeamGameResult]: ...


class PredictionRepository(Protocol):
    def get_latest_standing(self, team_code: str, season: int) -> TeamStanding | None: ...


@dataclass(frozen=True)
class _TeamInputs:
    standing: TeamStanding | None
    results: list[TeamGameResult]


_RECORD_PATTERN = re.compile(r"^(\d+)[-:](\d+)[-:](\d+)$")


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
        return _record(0, 0, 0, "unavailable")
    match = _RECORD_PATTERN.match(value.strip())
    if match is None:
        return _record(0, 0, 0, "unavailable")
    wins, draws, losses = (int(part) for part in match.groups())
    return _record(wins, losses, draws)


def _standing_record(standing: TeamStanding | None) -> PredictionRecord:
    if standing is None:
        return _record(0, 0, 0)
    return _record(standing.wins, standing.losses, standing.draws)


def _recent_results(results: list[TeamGameResult]) -> list[TeamGameResult]:
    return sorted(results, key=lambda item: item.game_date, reverse=True)[:10]


def _record_from_results(results: list[TeamGameResult]) -> PredictionRecord:
    wins = sum(result.result == "W" for result in results)
    losses = sum(result.result == "L" for result in results)
    draws = sum(result.result == "D" for result in results)
    return _record(wins, losses, draws)


def _metrics(standing: TeamStanding | None, results: list[TeamGameResult]) -> PredictionTeamMetrics:
    recent = _recent_results(results)
    runs_for = [result.team_score for result in recent]
    runs_against = [result.opponent_score for result in recent]
    if not recent:
        return PredictionTeamMetrics(
            season_win_percentage=(float(standing.winning_percentage) if standing else None),
            ranking=standing.ranking if standing else None,
            status="unavailable" if standing is None else "partial",
        )
    for_avg, against_avg = mean(runs_for), mean(runs_against)
    return PredictionTeamMetrics(
        season_win_percentage=(float(standing.winning_percentage) if standing else None),
        ranking=standing.ranking if standing else None,
        recent_runs_for_per_game=round(for_avg, 2),
        recent_runs_against_per_game=round(against_avg, 2),
        recent_run_differential=round(for_avg - against_avg, 2),
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
        metrics=_metrics(standing, inputs.results),
    )


def _probability(
    away: _TeamInputs,
    home: _TeamInputs,
    head_to_head: PredictionRecord,
) -> tuple[float, list[str], float]:
    signals: list[tuple[float, float, str]] = []
    away_season = away.standing.winning_percentage if away.standing else None
    home_season = home.standing.winning_percentage if home.standing else None
    if away_season is not None and home_season is not None:
        signals.append((0.45, float(away_season) - float(home_season), "시즌 승률 비교"))

    away_recent = _record_from_results(_recent_results(away.results))
    home_recent = _record_from_results(_recent_results(home.results))
    if away_recent.winning_percentage is not None and home_recent.winning_percentage is not None:
        signals.append(
            (
                0.25,
                away_recent.winning_percentage - home_recent.winning_percentage,
                "최근 10경기 성적",
            )
        )

    away_home = _parse_record(away.standing.home_record if away.standing else None)
    home_away = _parse_record(home.standing.away_record if home.standing else None)
    if away_home.winning_percentage is not None and home_away.winning_percentage is not None:
        signals.append(
            (
                0.15,
                away_home.winning_percentage - home_away.winning_percentage,
                "홈·원정 성적",
            )
        )

    if head_to_head.winning_percentage is not None:
        signals.append((0.10, head_to_head.winning_percentage - 0.5, "상대전적"))

    away_diff, home_diff = away.results, home.results
    away_metric = _metrics(away.standing, away_diff).recent_run_differential
    home_metric = _metrics(home.standing, home_diff).recent_run_differential
    if away_metric is not None and home_metric is not None:
        signals.append((0.05, max(-1.0, min(1.0, (away_metric - home_metric) / 10)), "최근 득실점"))

    if not signals:
        return 0.5, ["사용 가능한 전적 데이터가 부족해 균등 확률을 사용했습니다."], 0.15
    weight = sum(item[0] for item in signals)
    score = sum(item[0] * item[1] for item in signals) / weight
    probability = max(0.05, min(0.95, 0.5 + score / 2))
    confidence_score = min(0.9, 0.25 + 0.65 * (len(signals) / 5))
    reasons = [item[2] for item in sorted(signals, reverse=True)]
    return probability, reasons, confidence_score


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

    def predict(self, game_id: str, season: int) -> GamePredictionResponse:
        game = _find_game(self._client, game_id.upper(), season)
        away_code, home_code = game.away.team_code, game.home.team_code
        away_inputs = _TeamInputs(
            self._repository.get_latest_standing(away_code, season),
            self._client.results(away_code, season),
        )
        home_inputs = _TeamInputs(
            self._repository.get_latest_standing(home_code, season),
            self._client.results(home_code, season),
        )
        h2h_results = [
            result for result in away_inputs.results if result.opponent == game.home.team_name
        ]
        h2h = _record_from_results(h2h_results)
        away_team = _team_prediction(away_code, game.away.team_name, away_inputs)
        home_team = _team_prediction(home_code, game.home.team_name, home_inputs)
        away_probability, reasons, confidence_score = _probability(away_inputs, home_inputs, h2h)
        home_probability = round(1 - away_probability, 4)
        away_recent = _recent_results(away_inputs.results)
        home_recent = _recent_results(home_inputs.results)
        expected = PredictionScore(
            away=round(mean([item.team_score for item in away_recent])) if away_recent else None,
            home=round(mean([item.team_score for item in home_recent])) if home_recent else None,
        )
        favored = away_team if away_probability > home_probability else home_team
        confidence = (
            "low"
            if confidence_score < 0.5
            else "medium"
            if confidence_score < 0.75
            else "high"
        )
        return GamePredictionResponse(
            game_id=game.game_id,
            season=season,
            game_date=date.fromisoformat(game.game_id[:8]),
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
                "현재 확보된 시즌 전적, 최근 경기, 홈·원정 성적, 상대전적을 조합한 "
                "MVP 예측입니다. "
                f"사용 가능한 신호 {len(reasons)}개를 반영했으며 선발투수 상세 지표는 "
                "별도 저장 데이터가 없어 확률에 직접 반영하지 않았습니다."
            ),
        )
