"""선수 검색과 시즌 기록을 위한 핵심 테이블 생성.

Revision ID: 0001_core
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0001_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    """migration 내부의 반복 timestamp 정의를 한 곳에서 유지한다."""

    return [
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
    ]


def upgrade() -> None:
    """FK 의존 순서에 맞게 core 6개 테이블과 조회 인덱스를 생성한다."""

    op.create_table(
        "data_import_batches",
        sa.Column("import_batch_id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column("dataset_type", sa.String(20), nullable=False),
        sa.Column("source_file_name", sa.String(255), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("source_row_count", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("imported_row_count", mysql.INTEGER(unsigned=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("quality_report", sa.JSON()),
        sa.Column(
            "started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("finished_at", sa.DateTime()),
        sa.UniqueConstraint("dataset_type", "source_sha256", name="uq_import_dataset_hash"),
        sa.CheckConstraint(
            "dataset_type IN ('BATTING', 'PITCHING')", name="ck_import_dataset_type"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_import_status",
        ),
        sa.CheckConstraint(
            "imported_row_count IS NULL OR imported_row_count <= source_row_count",
            name="ck_imported_row_count",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )

    op.create_table(
        "players",
        sa.Column("player_id", mysql.INTEGER(unsigned=True), primary_key=True, autoincrement=False),
        sa.Column("player_name", sa.String(100), nullable=False),
        sa.Column("search_name", sa.String(100), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("CHAR_LENGTH(TRIM(player_name)) > 0", name="ck_players_name_not_blank"),
        sa.CheckConstraint("CHAR_LENGTH(search_name) > 0", name="ck_players_search_name_not_blank"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_players_player_name", "players", ["player_name"])
    op.create_index("ix_players_search_name", "players", ["search_name"])

    op.create_table(
        "teams",
        sa.Column("team_id", mysql.TINYINT(unsigned=True), primary_key=True, autoincrement=False),
        sa.Column("team_name", sa.String(30), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("team_name", name="uq_teams_name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    teams_table = sa.table(
        "teams",
        sa.column("team_id", sa.SmallInteger()),
        sa.column("team_name", sa.String()),
    )
    op.bulk_insert(
        teams_table,
        [
            {"team_id": team_id, "team_name": team_name}
            for team_id, team_name in enumerate(
                [
                    "KIA",
                    "KT",
                    "LG",
                    "MBC",
                    "NC",
                    "OB",
                    "SK",
                    "SSG",
                    "넥센",
                    "두산",
                    "롯데",
                    "빙그레",
                    "삼미",
                    "삼성",
                    "쌍방울",
                    "우리",
                    "청보",
                    "키움",
                    "태평양",
                    "한화",
                    "해태",
                    "현대",
                    "히어로즈",
                ],
                start=1,
            )
        ],
    )

    op.create_table(
        "player_source_profiles",
        sa.Column(
            "player_id",
            mysql.INTEGER(unsigned=True),
            sa.ForeignKey("players.player_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("profile_role", sa.String(20), primary_key=True),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("bat_side", sa.String(1), nullable=False),
        sa.Column("throw_side", sa.String(1), nullable=False),
        sa.Column("height_cm", mysql.SMALLINT(unsigned=True)),
        sa.Column("weight_kg", mysql.SMALLINT(unsigned=True)),
        sa.Column("career", sa.Text()),
        sa.Column("draft", sa.String(255)),
        *timestamp_columns(),
        sa.CheckConstraint("profile_role IN ('BATTING', 'PITCHING')", name="ck_profile_role"),
        sa.CheckConstraint("bat_side IN ('L', 'R', 'S')", name="ck_profile_bat_side"),
        sa.CheckConstraint("throw_side IN ('L', 'R')", name="ck_profile_throw_side"),
        sa.CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 140 AND 230",
            name="ck_profile_height",
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg BETWEEN 40 AND 180",
            name="ck_profile_weight",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )

    _create_batting_table()
    _create_pitching_table()


def _create_batting_table() -> None:
    """타격 컬럼과 자연키/도메인 제약을 생성한다."""

    integer_columns = [
        "games",
        "plate_appearances",
        "at_bats",
        "runs",
        "hits",
        "doubles",
        "triples",
        "home_runs",
        "total_bases",
        "runs_batted_in",
        "stolen_bases",
        "caught_stealing",
        "walks",
        "hit_by_pitch",
        "strikeouts",
        "grounded_into_double_play",
        "sacrifice_flies",
        "sacrifice_hits",
        "errors",
    ]
    op.create_table(
        "batting_season_stats",
        sa.Column("batting_stat_id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column(
            "player_id",
            mysql.INTEGER(unsigned=True),
            sa.ForeignKey("players.player_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            mysql.TINYINT(unsigned=True),
            sa.ForeignKey("teams.team_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "import_batch_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("data_import_batches.import_batch_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("season", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("position_code", sa.String(5), nullable=False),
        *(
            sa.Column(name, mysql.SMALLINT(unsigned=True), nullable=False)
            for name in integer_columns
        ),
        sa.Column("batting_average", sa.Numeric(5, 3)),
        sa.Column("slugging_percentage", sa.Numeric(5, 3)),
        sa.Column("on_base_percentage", sa.Numeric(5, 3)),
        sa.Column("on_base_plus_slugging", sa.Numeric(5, 3)),
        *timestamp_columns(),
        sa.UniqueConstraint("player_id", "season", "team_id", name="uq_batting_player_season_team"),
        sa.CheckConstraint("season BETWEEN 1982 AND 2200", name="ck_batting_season"),
        sa.CheckConstraint(
            "hits <= at_bats AND plate_appearances >= at_bats "
            "AND home_runs <= hits AND doubles + triples + home_runs <= hits",
            name="ck_batting_counts",
        ),
        sa.CheckConstraint(
            "batting_average IS NULL OR batting_average BETWEEN 0 AND 1",
            name="ck_batting_average_range",
        ),
        sa.CheckConstraint(
            "slugging_percentage IS NULL OR slugging_percentage BETWEEN 0 AND 4",
            name="ck_batting_slg_range",
        ),
        sa.CheckConstraint(
            "on_base_percentage IS NULL OR on_base_percentage BETWEEN 0 AND 1",
            name="ck_batting_obp_range",
        ),
        sa.CheckConstraint(
            "on_base_plus_slugging IS NULL OR on_base_plus_slugging BETWEEN 0 AND 5",
            name="ck_batting_ops_range",
        ),
        sa.CheckConstraint(
            "at_bats <> 0 OR (batting_average IS NULL AND slugging_percentage IS NULL "
            "AND on_base_percentage IS NULL AND on_base_plus_slugging IS NULL)",
            name="ck_batting_zero_at_bats_rates",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_batting_season_team", "batting_season_stats", ["season", "team_id"])
    op.create_index(
        "ix_batting_season_ops",
        "batting_season_stats",
        ["season", "on_base_plus_slugging"],
    )


def _create_pitching_table() -> None:
    """투구 컬럼과 자연키/도메인 제약을 생성한다."""

    integer_columns = [
        "games",
        "complete_games",
        "shutouts",
        "wins",
        "losses",
        "saves",
        "holds",
        "batters_faced",
        "innings_pitched_outs",
        "hits_allowed",
        "home_runs_allowed",
        "walks_allowed",
        "hit_batters",
        "strikeouts",
        "runs_allowed",
        "earned_runs",
    ]
    op.create_table(
        "pitching_season_stats",
        sa.Column("pitching_stat_id", mysql.BIGINT(unsigned=True), primary_key=True),
        sa.Column(
            "player_id",
            mysql.INTEGER(unsigned=True),
            sa.ForeignKey("players.player_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            mysql.TINYINT(unsigned=True),
            sa.ForeignKey("teams.team_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "import_batch_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("data_import_batches.import_batch_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("season", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("earned_run_average", sa.Numeric(7, 3)),
        *(
            sa.Column(name, mysql.SMALLINT(unsigned=True), nullable=False)
            for name in integer_columns
        ),
        sa.Column("winning_percentage", sa.Numeric(4, 3)),
        *timestamp_columns(),
        sa.UniqueConstraint(
            "player_id", "season", "team_id", name="uq_pitching_player_season_team"
        ),
        sa.CheckConstraint("season BETWEEN 1982 AND 2200", name="ck_pitching_season"),
        sa.CheckConstraint(
            "earned_runs <= runs_allowed AND complete_games <= games "
            "AND shutouts <= complete_games",
            name="ck_pitching_counts",
        ),
        sa.CheckConstraint(
            "earned_run_average IS NULL OR earned_run_average >= 0",
            name="ck_pitching_era_nonnegative",
        ),
        sa.CheckConstraint(
            "winning_percentage IS NULL OR winning_percentage BETWEEN 0 AND 1",
            name="ck_pitching_wpct_range",
        ),
        sa.CheckConstraint(
            "innings_pitched_outs <> 0 OR earned_run_average IS NULL",
            name="ck_pitching_zero_outs_era",
        ),
        sa.CheckConstraint(
            "wins + losses <> 0 OR winning_percentage IS NULL",
            name="ck_pitching_no_decision_wpct",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_pitching_season_team", "pitching_season_stats", ["season", "team_id"])
    op.create_index(
        "ix_pitching_season_era",
        "pitching_season_stats",
        ["season", "earned_run_average"],
    )


def downgrade() -> None:
    """FK 자식부터 역순으로 핵심 테이블을 제거한다."""

    op.drop_table("pitching_season_stats")
    op.drop_table("batting_season_stats")
    op.drop_table("player_source_profiles")
    op.drop_table("teams")
    op.drop_table("players")
    op.drop_table("data_import_batches")
