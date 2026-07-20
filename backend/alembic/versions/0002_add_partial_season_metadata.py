"""진행 중 시즌 snapshot 메타데이터를 시즌 기록에 추가한다.

Revision ID: 0002_partial_season
Revises: 0001_core
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_partial_season"
down_revision: str | None = "0001_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """타자·투수 기록에 진행 여부와 기준일을 추가한다."""

    for table_name in ("batting_season_stats", "pitching_season_stats"):
        op.add_column(
            table_name,
            sa.Column(
                "is_partial",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        op.add_column(table_name, sa.Column("as_of_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """진행 시즌 메타데이터 컬럼을 제거한다."""

    for table_name in ("pitching_season_stats", "batting_season_stats"):
        op.drop_column(table_name, "as_of_date")
        op.drop_column(table_name, "is_partial")
