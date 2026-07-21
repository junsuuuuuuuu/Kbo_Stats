"""날짜별 KBO 정규시즌 팀 순위 스냅샷."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import TimestampMixin


class TeamStanding(TimestampMixin, Base):
    """특정 기준일의 정규시즌 구단 전적과 순위."""

    __tablename__ = "team_standings"
    __table_args__ = (
        UniqueConstraint("season", "as_of_date", "team_id", name="standing_season_date_team"),
        CheckConstraint("season BETWEEN 1982 AND 2200", name="standing_season"),
        CheckConstraint("ranking BETWEEN 1 AND 20", name="standing_ranking"),
        CheckConstraint("games >= wins + losses + draws", name="standing_game_counts"),
        CheckConstraint("winning_percentage BETWEEN 0 AND 1", name="standing_win_pct"),
        Index("ix_standing_season_date_rank", "season", "as_of_date", "ranking"),
    )

    standing_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id", ondelete="RESTRICT"), nullable=False
    )
    team_code: Mapped[str] = mapped_column(String(2), nullable=False)
    ranking: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    games: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    wins: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    losses: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    draws: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    winning_percentage: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    games_behind: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    recent_ten: Mapped[str] = mapped_column(String(20), nullable=False)
    streak: Mapped[str] = mapped_column(String(10), nullable=False)
    home_record: Mapped[str] = mapped_column(String(20), nullable=False)
    away_record: Mapped[str] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)

    team = relationship("Team", back_populates="standings", lazy="joined")
