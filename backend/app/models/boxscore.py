"""Persisted game-level box score source data."""

from datetime import date

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import TimestampMixin


class GameBoxscoreSnapshot(TimestampMixin, Base):
    __tablename__ = "game_boxscore_snapshots"
    __table_args__ = (
        CheckConstraint("season BETWEEN 1982 AND 2200", name="boxscore_season"),
        CheckConstraint("status IN ('collected', 'partial', 'failed')", name="boxscore_status"),
        Index("ix_boxscore_snapshot_season_date", "season", "game_date"),
    )

    game_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500))


class GameBattingLine(TimestampMixin, Base):
    __tablename__ = "game_batting_lines"
    __table_args__ = (
        UniqueConstraint("game_id", "team_code", "line_order", name="uq_game_batting_line"),
        Index("ix_game_batting_team_date", "team_code", "game_date"),
    )

    batting_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("game_boxscore_snapshots.game_id", ondelete="CASCADE"),
        nullable=False,
    )
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    team_code: Mapped[str] = mapped_column(String(2), nullable=False)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.player_id"))
    player_name: Mapped[str] = mapped_column(String(100), nullable=False)
    line_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    plate_appearances: Mapped[int | None] = mapped_column(SmallInteger)
    at_bats: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hits: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    doubles: Mapped[int | None] = mapped_column(SmallInteger)
    triples: Mapped[int | None] = mapped_column(SmallInteger)
    home_runs: Mapped[int | None] = mapped_column(SmallInteger)
    runs: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    runs_batted_in: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    walks: Mapped[int | None] = mapped_column(SmallInteger)
    hit_by_pitch: Mapped[int | None] = mapped_column(SmallInteger)
    sacrifice_flies: Mapped[int | None] = mapped_column(SmallInteger)
    strikeouts: Mapped[int | None] = mapped_column(SmallInteger)
    total_bases: Mapped[int | None] = mapped_column(SmallInteger)
    source_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class GamePitchingLine(TimestampMixin, Base):
    __tablename__ = "game_pitching_lines"
    __table_args__ = (
        UniqueConstraint("game_id", "team_code", "line_order", name="uq_game_pitching_line"),
        Index("ix_game_pitching_team_date", "team_code", "game_date"),
    )

    pitching_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("game_boxscore_snapshots.game_id", ondelete="CASCADE"),
        nullable=False,
    )
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    team_code: Mapped[str] = mapped_column(String(2), nullable=False)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.player_id"))
    player_name: Mapped[str] = mapped_column(String(100), nullable=False)
    line_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    appearance: Mapped[str] = mapped_column(String(30), nullable=False)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    innings_pitched_outs: Mapped[int | None] = mapped_column(SmallInteger)
    hits_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    home_runs_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    walks_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hit_batters: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strikeouts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    runs_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    earned_runs: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
