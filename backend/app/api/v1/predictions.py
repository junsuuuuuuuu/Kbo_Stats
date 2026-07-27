"""Game prediction endpoints."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import PredictionServiceDependency
from app.core.constants import CURRENT_SEASON
from app.schemas.prediction import GamePredictionResponse

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get(
    "/games/{game_id}",
    response_model=GamePredictionResponse,
    summary="경기 승리 확률 및 예측 근거 조회",
)
def predict_game(
    service: PredictionServiceDependency,
    game_id: Annotated[str, Path(min_length=13, max_length=18)],
    season: Annotated[int, Query(ge=CURRENT_SEASON, le=2200)] = CURRENT_SEASON,
) -> GamePredictionResponse:
    return service.predict(game_id, season)
