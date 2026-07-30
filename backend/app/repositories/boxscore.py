"""Database access for normalized game box scores."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.boxscore import GameBattingLine, GamePitchingLine
from app.services.recent_boxscore import RecentBoxscoreMetrics, aggregate_boxscore_rows


class SqlAlchemyBoxscoreRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def recent_metrics(
        self, game_ids: Sequence[str], team_code: str, expected_games: int
    ) -> RecentBoxscoreMetrics:
        batting = list(
            self._session.scalars(
                select(GameBattingLine).where(
                    GameBattingLine.game_id.in_(game_ids),
                    GameBattingLine.team_code == team_code,
                )
            )
        )
        pitching = list(
            self._session.scalars(
                select(GamePitchingLine).where(
                    GamePitchingLine.game_id.in_(game_ids),
                    GamePitchingLine.team_code == team_code,
                )
            )
        )
        return aggregate_boxscore_rows(batting, pitching, expected_games)
