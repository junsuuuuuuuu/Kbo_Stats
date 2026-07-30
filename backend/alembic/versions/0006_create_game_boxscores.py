"""Create persisted game-level box score tables.

Revision ID: 0006_game_boxscores
Revises: 0005_game_day_snapshots
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0006_game_boxscores"
down_revision: str | None = "0005_game_day_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
    ]


def upgrade() -> None:
    op.create_table(
        "game_boxscore_snapshots",
        sa.Column("game_id", sa.String(20), primary_key=True),
        sa.Column("season", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.String(500)),
        *timestamps(),
        sa.CheckConstraint("season BETWEEN 1982 AND 2200", name="boxscore_season"),
        sa.CheckConstraint("status IN ('collected', 'partial', 'failed')", name="boxscore_status"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_boxscore_snapshot_season_date", "game_boxscore_snapshots", ["season", "game_date"])

    batting_columns = [
        sa.Column("batting_line_id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.String(20), sa.ForeignKey("game_boxscore_snapshots.game_id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("team_code", sa.String(2), nullable=False),
        sa.Column("player_id", mysql.INTEGER(unsigned=True), sa.ForeignKey("players.player_id")),
        sa.Column("player_name", sa.String(100), nullable=False),
        sa.Column("line_order", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("plate_appearances", mysql.SMALLINT(unsigned=True)),
        sa.Column("at_bats", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("hits", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("doubles", mysql.SMALLINT(unsigned=True)),
        sa.Column("triples", mysql.SMALLINT(unsigned=True)),
        sa.Column("home_runs", mysql.SMALLINT(unsigned=True)),
        sa.Column("runs", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("runs_batted_in", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("walks", mysql.SMALLINT(unsigned=True)),
        sa.Column("hit_by_pitch", mysql.SMALLINT(unsigned=True)),
        sa.Column("sacrifice_flies", mysql.SMALLINT(unsigned=True)),
        sa.Column("strikeouts", mysql.SMALLINT(unsigned=True)),
        sa.Column("total_bases", mysql.SMALLINT(unsigned=True)),
        sa.Column("source_complete", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        *timestamps(),
        sa.UniqueConstraint("game_id", "team_code", "line_order", name="uq_game_batting_line"),
    ]
    op.create_table("game_batting_lines", *batting_columns, mysql_charset="utf8mb4", mysql_collate="utf8mb4_0900_ai_ci")
    op.create_index("ix_game_batting_team_date", "game_batting_lines", ["team_code", "game_date"])

    pitching_columns = [
        sa.Column("pitching_line_id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.String(20), sa.ForeignKey("game_boxscore_snapshots.game_id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("team_code", sa.String(2), nullable=False),
        sa.Column("player_id", mysql.INTEGER(unsigned=True), sa.ForeignKey("players.player_id")),
        sa.Column("player_name", sa.String(100), nullable=False),
        sa.Column("line_order", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("appearance", sa.String(30), nullable=False),
        sa.Column("is_starter", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("innings_pitched_outs", mysql.SMALLINT(unsigned=True)),
        sa.Column("hits_allowed", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("home_runs_allowed", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("walks_allowed", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("hit_batters", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("strikeouts", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("runs_allowed", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("earned_runs", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("source_complete", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        *timestamps(),
        sa.UniqueConstraint("game_id", "team_code", "line_order", name="uq_game_pitching_line"),
    ]
    op.create_table("game_pitching_lines", *pitching_columns, mysql_charset="utf8mb4", mysql_collate="utf8mb4_0900_ai_ci")
    op.create_index("ix_game_pitching_team_date", "game_pitching_lines", ["team_code", "game_date"])


def downgrade() -> None:
    op.drop_table("game_pitching_lines")
    op.drop_table("game_batting_lines")
    op.drop_index("ix_boxscore_snapshot_season_date", table_name="game_boxscore_snapshots")
    op.drop_table("game_boxscore_snapshots")
