"""v1 하위 router 조립."""

from fastapi import APIRouter

from app.api.v1 import analytics, health, players, teams

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(players.router)
api_router.include_router(teams.router)
api_router.include_router(analytics.router)
