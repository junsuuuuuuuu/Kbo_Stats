"""Create collected KBO game-day snapshots.

Revision ID: 0005_game_day_snapshots
Revises: 0004_team_standings
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0005_game_day_snapshots"
down_revision: str | None = "0004_team_standings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_day_snapshots",
        sa.Column("snapshot_id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column("season", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("season", "game_date", name="uq_game_day_season_date"),
        sa.CheckConstraint("season BETWEEN 1982 AND 2200", name="ck_game_day_season"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_game_day_season_date",
        "game_day_snapshots",
        ["season", "game_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_game_day_season_date", table_name="game_day_snapshots")
    op.drop_table("game_day_snapshots")
