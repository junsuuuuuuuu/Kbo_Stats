"""날짜별 KBO 팀 전적 스냅샷 테이블을 생성한다.

Revision ID: 0004_team_standings
Revises: 0003_team_rosters
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0004_team_standings"
down_revision: str | None = "0003_team_rosters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "team_standings",
        sa.Column("standing_id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column("season", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("team_id", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column("team_code", sa.String(2), nullable=False),
        sa.Column("ranking", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column("games", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("wins", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("losses", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("draws", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("winning_percentage", sa.Numeric(4, 3), nullable=False),
        sa.Column("games_behind", sa.Numeric(4, 1), nullable=False),
        sa.Column("recent_ten", sa.String(20), nullable=False),
        sa.Column("streak", sa.String(10), nullable=False),
        sa.Column("home_record", sa.String(20), nullable=False),
        sa.Column("away_record", sa.String(20), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("season", "as_of_date", "team_id", name="uq_standing_season_date_team"),
        sa.CheckConstraint("season BETWEEN 1982 AND 2200", name="ck_standing_season"),
        sa.CheckConstraint("ranking BETWEEN 1 AND 20", name="ck_standing_ranking"),
        sa.CheckConstraint("games >= wins + losses + draws", name="ck_standing_game_counts"),
        sa.CheckConstraint("winning_percentage BETWEEN 0 AND 1", name="ck_standing_win_pct"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_standing_season_date_rank",
        "team_standings",
        ["season", "as_of_date", "ranking"],
    )


def downgrade() -> None:
    op.drop_index("ix_standing_season_date_rank", table_name="team_standings")
    op.drop_table("team_standings")
