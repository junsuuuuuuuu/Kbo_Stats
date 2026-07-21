"""날짜별 KBO 1군 선수 등록 로스터 모델."""

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import TimestampMixin


class TeamRoster(TimestampMixin, Base):
    """특정 날짜와 구단의 1군 등록 선수 snapshot 행."""

    __tablename__ = "team_rosters"
    __table_args__ = (
        UniqueConstraint(
            "season",
            "as_of_date",
            "team_id",
            "player_id",
            name="roster_season_date_team_player",
        ),
        CheckConstraint("season BETWEEN 1982 AND 2200", name="roster_season"),
        CheckConstraint("position_code IN ('P', 'C', 'IF', 'OF')", name="roster_position"),
        CheckConstraint("bat_side IN ('L', 'R', 'S')", name="roster_bat_side"),
        CheckConstraint("throw_side IN ('L', 'R')", name="roster_throw_side"),
        CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 140 AND 230", name="roster_height"
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg BETWEEN 40 AND 180", name="roster_weight"
        ),
        Index("ix_roster_season_team_date", "season", "team_id", "as_of_date"),
    )

    roster_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id", ondelete="RESTRICT"), nullable=False
    )
    team_code: Mapped[str] = mapped_column(String(2), nullable=False)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id", ondelete="RESTRICT"), nullable=False
    )
    position_code: Mapped[str] = mapped_column(String(2), nullable=False)
    uniform_number: Mapped[str] = mapped_column(String(3), nullable=False)
    bat_side: Mapped[str] = mapped_column(String(1), nullable=False)
    throw_side: Mapped[str] = mapped_column(String(1), nullable=False)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[int | None] = mapped_column(SmallInteger)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    team = relationship("Team", back_populates="rosters", lazy="joined")
    player = relationship("Player", back_populates="rosters", lazy="joined")
