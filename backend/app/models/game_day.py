"""Persisted home-page KBO game-day snapshots."""

from datetime import date
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import TimestampMixin


class GameDaySnapshot(TimestampMixin, Base):
    """One collected schedule/result payload for a KBO game date."""

    __tablename__ = "game_day_snapshots"
    __table_args__ = (
        UniqueConstraint("season", "game_date", name="uq_game_day_season_date"),
        CheckConstraint("season BETWEEN 1982 AND 2200", name="game_day_season"),
        Index("ix_game_day_season_date", "season", "game_date"),
    )

    snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
