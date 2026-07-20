"""타자와 투수의 시즌 기록 모델."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class BattingSeasonStat(TimestampMixin, Base):
    """선수-시즌-팀 단위 타격 기록."""

    __tablename__ = "batting_season_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "team_id", name="batting_player_season_team"),
        CheckConstraint("season BETWEEN 1982 AND 2200", name="batting_season"),
        CheckConstraint(
            "hits <= at_bats AND plate_appearances >= at_bats "
            "AND home_runs <= hits AND doubles + triples + home_runs <= hits",
            name="batting_counts",
        ),
        CheckConstraint(
            "batting_average IS NULL OR batting_average BETWEEN 0 AND 1",
            name="batting_average_range",
        ),
        CheckConstraint(
            "slugging_percentage IS NULL OR slugging_percentage BETWEEN 0 AND 4",
            name="batting_slg_range",
        ),
        CheckConstraint(
            "on_base_percentage IS NULL OR on_base_percentage BETWEEN 0 AND 1",
            name="batting_obp_range",
        ),
        CheckConstraint(
            "on_base_plus_slugging IS NULL OR on_base_plus_slugging BETWEEN 0 AND 5",
            name="batting_ops_range",
        ),
        CheckConstraint(
            "at_bats <> 0 OR (batting_average IS NULL AND slugging_percentage IS NULL "
            "AND on_base_percentage IS NULL AND on_base_plus_slugging IS NULL)",
            name="batting_zero_at_bats_rates",
        ),
        Index("ix_batting_season_team", "season", "team_id"),
        Index("ix_batting_season_ops", "season", "on_base_plus_slugging"),
    )

    batting_stat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id", ondelete="RESTRICT"), nullable=False
    )
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("data_import_batches.import_batch_id", ondelete="RESTRICT"), nullable=False
    )
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    as_of_date: Mapped[date | None] = mapped_column(Date)
    position_code: Mapped[str] = mapped_column(String(5), nullable=False)
    games: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    plate_appearances: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    at_bats: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    runs: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hits: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    doubles: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    triples: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    home_runs: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_bases: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    runs_batted_in: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    stolen_bases: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    caught_stealing: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    walks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hit_by_pitch: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strikeouts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    grounded_into_double_play: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sacrifice_flies: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sacrifice_hits: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    errors: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    batting_average: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    slugging_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    on_base_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    on_base_plus_slugging: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))

    player = relationship("Player", back_populates="batting_stats")
    team = relationship("Team", back_populates="batting_stats", lazy="joined")


class PitchingSeasonStat(TimestampMixin, Base):
    """선수-시즌-팀 단위 투구 기록. 이닝은 정수 아웃 수로 저장한다."""

    __tablename__ = "pitching_season_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "team_id", name="pitching_player_season_team"),
        CheckConstraint("season BETWEEN 1982 AND 2200", name="pitching_season"),
        CheckConstraint(
            "earned_runs <= runs_allowed AND complete_games <= games "
            "AND shutouts <= complete_games",
            name="pitching_counts",
        ),
        CheckConstraint(
            "earned_run_average IS NULL OR earned_run_average >= 0",
            name="pitching_era_nonnegative",
        ),
        CheckConstraint(
            "winning_percentage IS NULL OR winning_percentage BETWEEN 0 AND 1",
            name="pitching_wpct_range",
        ),
        CheckConstraint(
            "innings_pitched_outs <> 0 OR earned_run_average IS NULL",
            name="pitching_zero_outs_era",
        ),
        CheckConstraint(
            "wins + losses <> 0 OR winning_percentage IS NULL",
            name="pitching_no_decision_wpct",
        ),
        Index("ix_pitching_season_team", "season", "team_id"),
        Index("ix_pitching_season_era", "season", "earned_run_average"),
    )

    pitching_stat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id", ondelete="RESTRICT"), nullable=False
    )
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("data_import_batches.import_batch_id", ondelete="RESTRICT"), nullable=False
    )
    season: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    as_of_date: Mapped[date | None] = mapped_column(Date)
    earned_run_average: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    games: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    complete_games: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    shutouts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    wins: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    losses: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    saves: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    holds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    winning_percentage: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    batters_faced: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    innings_pitched_outs: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hits_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    home_runs_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    walks_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hit_batters: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strikeouts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    runs_allowed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    earned_runs: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    player = relationship("Player", back_populates="pitching_stats")
    team = relationship("Team", back_populates="pitching_stats", lazy="joined")
