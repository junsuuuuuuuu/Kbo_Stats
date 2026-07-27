"""Schemas for explainable MVP game predictions."""

from datetime import date

from pydantic import BaseModel, Field


class PredictionRecord(BaseModel):
    games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    winning_percentage: float | None = None
    status: str = "unavailable"


class PredictionForm(BaseModel):
    results: list[str] = Field(default_factory=list)
    record: PredictionRecord


class PredictionTeamMetrics(BaseModel):
    season_win_percentage: float | None = None
    ranking: int | None = None
    recent_runs_for_per_game: float | None = None
    recent_runs_against_per_game: float | None = None
    recent_run_differential: float | None = None
    status: str = "partial"


class PredictionTeam(BaseModel):
    team_code: str
    team_name: str
    season_record: PredictionRecord
    home_record: PredictionRecord
    away_record: PredictionRecord
    metrics: PredictionTeamMetrics


class StartingPitcherAnalysis(BaseModel):
    name: str | None = None
    status: str = "unavailable"
    note: str | None = None


class PredictionScore(BaseModel):
    away: int | None = None
    home: int | None = None


class GamePredictionResponse(BaseModel):
    game_id: str
    season: int
    game_date: date
    start_time: str
    stadium: str
    away: PredictionTeam
    home: PredictionTeam
    away_starting_pitcher: StartingPitcherAnalysis
    home_starting_pitcher: StartingPitcherAnalysis
    head_to_head: PredictionRecord
    away_win_probability: float = Field(ge=0, le=1)
    home_win_probability: float = Field(ge=0, le=1)
    favored_team_code: str | None = None
    favored_team_name: str | None = None
    expected_score: PredictionScore
    confidence: str
    confidence_score: float = Field(ge=0, le=1)
    key_reasons: list[str]
    explanation: str
