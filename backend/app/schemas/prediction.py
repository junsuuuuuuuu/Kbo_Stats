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
    recent_games_count: int = 0
    recent_games_status: str = "unavailable"
    recent_win_percentage: float | None = None
    season_win_percentage: float | None = None
    ranking: int | None = None
    recent_runs_for_per_game: float | None = None
    recent_runs_against_per_game: float | None = None
    recent_run_differential: float | None = None
    recent_batting_average: float | None = None
    recent_on_base_percentage: float | None = None
    recent_slugging_percentage: float | None = None
    recent_ops: float | None = None
    recent_hits_per_game: float | None = None
    recent_home_runs: int | None = None
    recent_walks: int | None = None
    recent_era: float | None = None
    recent_whip: float | None = None
    recent_strikeouts_per_game: float | None = None
    batting_status: str = "unavailable"
    pitching_status: str = "unavailable"
    status: str = "partial"


class PredictionTeam(BaseModel):
    team_code: str
    team_name: str
    season_record: PredictionRecord
    home_record: PredictionRecord
    away_record: PredictionRecord
    recent_form: PredictionForm
    metrics: PredictionTeamMetrics


class PitcherSeasonAnalysis(BaseModel):
    era: float | None = None
    whip: float | None = None
    innings: float | None = None
    strikeouts: int | None = None
    walks: int | None = None
    hits: int | None = None
    wins: int | None = None
    losses: int | None = None
    games: int | None = None
    last_appearance_date: date | None = None
    status: str = "unavailable"


class PitcherOpponentAnalysis(BaseModel):
    games: int = 0
    starts: int = 0
    innings: float | None = None
    era: float | None = None
    whip: float | None = None
    hits: int | None = None
    strikeouts: int | None = None
    wins: int | None = None
    losses: int | None = None
    status: str = "unavailable"


class StartingPitcherAnalysis(BaseModel):
    name: str | None = None
    status: str = "unavailable"
    note: str | None = None
    season: PitcherSeasonAnalysis | None = None
    vs_opponent: PitcherOpponentAnalysis | None = None


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
