"""날짜별 KBO 1군 구단 로스터 테이블을 생성한다.

Revision ID: 0003_team_rosters
Revises: 0002_partial_season
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0003_team_rosters"
down_revision: str | None = "0002_partial_season"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """로스터 snapshot 행과 조회 인덱스를 생성한다."""

    op.create_table(
        "team_rosters",
        sa.Column("roster_id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column("season", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("team_id", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column("team_code", sa.String(2), nullable=False),
        sa.Column("player_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("position_code", sa.String(2), nullable=False),
        sa.Column("uniform_number", sa.String(3), nullable=False),
        sa.Column("bat_side", sa.String(1), nullable=False),
        sa.Column("throw_side", sa.String(1), nullable=False),
        sa.Column("height_cm", mysql.SMALLINT(unsigned=True)),
        sa.Column("weight_kg", mysql.SMALLINT(unsigned=True)),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["player_id"], ["players.player_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "season",
            "as_of_date",
            "team_id",
            "player_id",
            name="uq_roster_season_date_team_player",
        ),
        sa.CheckConstraint("season BETWEEN 1982 AND 2200", name="ck_roster_season"),
        sa.CheckConstraint(
            "position_code IN ('P', 'C', 'IF', 'OF')", name="ck_roster_position"
        ),
        sa.CheckConstraint("bat_side IN ('L', 'R', 'S')", name="ck_roster_bat_side"),
        sa.CheckConstraint("throw_side IN ('L', 'R')", name="ck_roster_throw_side"),
        sa.CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 140 AND 230", name="ck_roster_height"
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg BETWEEN 40 AND 180", name="ck_roster_weight"
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_roster_season_team_date",
        "team_rosters",
        ["season", "team_id", "as_of_date"],
    )


def downgrade() -> None:
    """로스터 테이블을 제거한다."""

    op.drop_index("ix_roster_season_team_date", table_name="team_rosters")
    op.drop_table("team_rosters")
