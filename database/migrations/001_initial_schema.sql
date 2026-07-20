-- KBO AI Player Analytics - MySQL 8.0 초기 스키마
-- 이 파일은 3단계의 실행 가능한 DB 계약이다. 4단계에서 동일 구조의
-- SQLAlchemy 모델과 Alembic revision을 작성하고 schema diff로 대조한다.

SET NAMES utf8mb4;

CREATE TABLE data_import_batches (
    import_batch_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    dataset_type VARCHAR(20) NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_sha256 CHAR(64) NOT NULL,
    source_row_count INT UNSIGNED NOT NULL,
    imported_row_count INT UNSIGNED NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    quality_report JSON NULL,
    started_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    finished_at DATETIME(6) NULL,
    PRIMARY KEY (import_batch_id),
    UNIQUE KEY uq_import_dataset_hash (dataset_type, source_sha256),
    CONSTRAINT ck_import_dataset_type
        CHECK (dataset_type IN ('BATTING', 'PITCHING')),
    CONSTRAINT ck_import_status
        CHECK (status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    CONSTRAINT ck_imported_row_count
        CHECK (imported_row_count IS NULL OR imported_row_count <= source_row_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE players (
    player_id INT UNSIGNED NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    search_name VARCHAR(100) NOT NULL COMMENT '공백 제거 및 소문자화한 검색용 이름',
    birth_date DATE NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (player_id),
    KEY ix_players_name (player_name),
    KEY ix_players_search_name (search_name),
    CONSTRAINT ck_players_name_not_blank CHECK (CHAR_LENGTH(TRIM(player_name)) > 0),
    CONSTRAINT ck_players_search_name_not_blank CHECK (CHAR_LENGTH(search_name) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE teams (
    team_id TINYINT UNSIGNED NOT NULL,
    team_name VARCHAR(30) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (team_id),
    UNIQUE KEY uq_teams_name (team_name),
    CONSTRAINT ck_teams_name_not_blank CHECK (CHAR_LENGTH(TRIM(team_name)) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 동일 선수라도 타자/투수 원본의 투타 정보와 신체 정보가 다를 수 있으므로
-- 공통 players 테이블에 임의 통합하지 않고 데이터 출처 역할별로 보존한다.
CREATE TABLE player_source_profiles (
    player_id INT UNSIGNED NOT NULL,
    profile_role VARCHAR(20) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    bat_side CHAR(1) NOT NULL,
    throw_side CHAR(1) NOT NULL,
    height_cm SMALLINT UNSIGNED NULL,
    weight_kg SMALLINT UNSIGNED NULL,
    career TEXT NULL,
    draft VARCHAR(255) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (player_id, profile_role),
    CONSTRAINT fk_player_profiles_player
        FOREIGN KEY (player_id) REFERENCES players (player_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT ck_player_profile_role
        CHECK (profile_role IN ('BATTING', 'PITCHING')),
    CONSTRAINT ck_player_profile_bat_side CHECK (bat_side IN ('L', 'R', 'S')),
    CONSTRAINT ck_player_profile_throw_side CHECK (throw_side IN ('L', 'R')),
    CONSTRAINT ck_player_profile_height
        CHECK (height_cm IS NULL OR height_cm BETWEEN 140 AND 230),
    CONSTRAINT ck_player_profile_weight
        CHECK (weight_kg IS NULL OR weight_kg BETWEEN 40 AND 180)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE batting_season_stats (
    batting_stat_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    player_id INT UNSIGNED NOT NULL,
    team_id TINYINT UNSIGNED NOT NULL,
    import_batch_id BIGINT UNSIGNED NOT NULL,
    season SMALLINT UNSIGNED NOT NULL,
    position_code VARCHAR(5) NOT NULL,
    games SMALLINT UNSIGNED NOT NULL,
    plate_appearances SMALLINT UNSIGNED NOT NULL,
    at_bats SMALLINT UNSIGNED NOT NULL,
    runs SMALLINT UNSIGNED NOT NULL,
    hits SMALLINT UNSIGNED NOT NULL,
    doubles SMALLINT UNSIGNED NOT NULL,
    triples SMALLINT UNSIGNED NOT NULL,
    home_runs SMALLINT UNSIGNED NOT NULL,
    total_bases SMALLINT UNSIGNED NOT NULL,
    runs_batted_in SMALLINT UNSIGNED NOT NULL,
    stolen_bases SMALLINT UNSIGNED NOT NULL,
    caught_stealing SMALLINT UNSIGNED NOT NULL,
    walks SMALLINT UNSIGNED NOT NULL,
    hit_by_pitch SMALLINT UNSIGNED NOT NULL,
    strikeouts SMALLINT UNSIGNED NOT NULL,
    grounded_into_double_play SMALLINT UNSIGNED NOT NULL,
    sacrifice_flies SMALLINT UNSIGNED NOT NULL,
    sacrifice_hits SMALLINT UNSIGNED NOT NULL,
    errors SMALLINT UNSIGNED NOT NULL,
    batting_average DECIMAL(5,3) NULL,
    slugging_percentage DECIMAL(5,3) NULL,
    on_base_percentage DECIMAL(5,3) NULL,
    on_base_plus_slugging DECIMAL(5,3) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (batting_stat_id),
    UNIQUE KEY uq_batting_player_season_team (player_id, season, team_id),
    KEY ix_batting_season_team (season, team_id),
    KEY ix_batting_season_ops (season, on_base_plus_slugging DESC),
    KEY ix_batting_import_batch (import_batch_id),
    CONSTRAINT fk_batting_player
        FOREIGN KEY (player_id) REFERENCES players (player_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_batting_team
        FOREIGN KEY (team_id) REFERENCES teams (team_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_batting_import_batch
        FOREIGN KEY (import_batch_id) REFERENCES data_import_batches (import_batch_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_batting_season CHECK (season BETWEEN 1982 AND 2200),
    CONSTRAINT ck_batting_position_not_blank
        CHECK (CHAR_LENGTH(TRIM(position_code)) > 0),
    CONSTRAINT ck_batting_counts CHECK (
        hits <= at_bats AND plate_appearances >= at_bats
        AND home_runs <= hits AND doubles + triples + home_runs <= hits
    ),
    CONSTRAINT ck_batting_average_range
        CHECK (batting_average IS NULL OR batting_average BETWEEN 0 AND 1),
    CONSTRAINT ck_batting_slg_range
        CHECK (slugging_percentage IS NULL OR slugging_percentage BETWEEN 0 AND 4),
    CONSTRAINT ck_batting_obp_range
        CHECK (on_base_percentage IS NULL OR on_base_percentage BETWEEN 0 AND 1),
    CONSTRAINT ck_batting_ops_range
        CHECK (on_base_plus_slugging IS NULL OR on_base_plus_slugging BETWEEN 0 AND 5),
    CONSTRAINT ck_batting_zero_at_bats_rates CHECK (
        at_bats <> 0 OR (
            batting_average IS NULL
            AND slugging_percentage IS NULL
            AND on_base_percentage IS NULL
            AND on_base_plus_slugging IS NULL
        )
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE pitching_season_stats (
    pitching_stat_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    player_id INT UNSIGNED NOT NULL,
    team_id TINYINT UNSIGNED NOT NULL,
    import_batch_id BIGINT UNSIGNED NOT NULL,
    season SMALLINT UNSIGNED NOT NULL,
    earned_run_average DECIMAL(7,3) NULL,
    games SMALLINT UNSIGNED NOT NULL,
    complete_games SMALLINT UNSIGNED NOT NULL,
    shutouts SMALLINT UNSIGNED NOT NULL,
    wins SMALLINT UNSIGNED NOT NULL,
    losses SMALLINT UNSIGNED NOT NULL,
    saves SMALLINT UNSIGNED NOT NULL,
    holds SMALLINT UNSIGNED NOT NULL,
    winning_percentage DECIMAL(4,3) NULL,
    batters_faced SMALLINT UNSIGNED NOT NULL,
    innings_pitched_outs SMALLINT UNSIGNED NOT NULL,
    hits_allowed SMALLINT UNSIGNED NOT NULL,
    home_runs_allowed SMALLINT UNSIGNED NOT NULL,
    walks_allowed SMALLINT UNSIGNED NOT NULL,
    hit_batters SMALLINT UNSIGNED NOT NULL,
    strikeouts SMALLINT UNSIGNED NOT NULL,
    runs_allowed SMALLINT UNSIGNED NOT NULL,
    earned_runs SMALLINT UNSIGNED NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (pitching_stat_id),
    UNIQUE KEY uq_pitching_player_season_team (player_id, season, team_id),
    KEY ix_pitching_season_team (season, team_id),
    KEY ix_pitching_season_era (season, earned_run_average),
    KEY ix_pitching_import_batch (import_batch_id),
    CONSTRAINT fk_pitching_player
        FOREIGN KEY (player_id) REFERENCES players (player_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_pitching_team
        FOREIGN KEY (team_id) REFERENCES teams (team_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_pitching_import_batch
        FOREIGN KEY (import_batch_id) REFERENCES data_import_batches (import_batch_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_pitching_season CHECK (season BETWEEN 1982 AND 2200),
    CONSTRAINT ck_pitching_counts CHECK (
        earned_runs <= runs_allowed AND complete_games <= games AND shutouts <= complete_games
    ),
    CONSTRAINT ck_pitching_era_nonnegative
        CHECK (earned_run_average IS NULL OR earned_run_average >= 0),
    CONSTRAINT ck_pitching_wpct_range
        CHECK (winning_percentage IS NULL OR winning_percentage BETWEEN 0 AND 1),
    CONSTRAINT ck_pitching_zero_outs_era
        CHECK (innings_pitched_outs <> 0 OR earned_run_average IS NULL),
    CONSTRAINT ck_pitching_no_decision_wpct
        CHECK (wins + losses <> 0 OR winning_percentage IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE model_versions (
    model_version_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    model_key VARCHAR(120) NOT NULL,
    task_type VARCHAR(40) NOT NULL,
    target_metric VARCHAR(64) NOT NULL,
    algorithm VARCHAR(40) NOT NULL,
    version_label VARCHAR(30) NOT NULL,
    artifact_uri VARCHAR(500) NOT NULL,
    feature_schema JSON NOT NULL,
    evaluation_metrics JSON NOT NULL,
    training_start_season SMALLINT UNSIGNED NOT NULL,
    training_end_season SMALLINT UNSIGNED NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    active_target_key VARCHAR(110)
        GENERATED ALWAYS AS (
            CASE
                WHEN is_active THEN CONCAT(task_type, ':', target_metric)
                ELSE NULL
            END
        ) STORED,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (model_version_id),
    UNIQUE KEY uq_model_key (model_key),
    UNIQUE KEY uq_model_version (
        task_type, target_metric, algorithm, version_label
    ),
    UNIQUE KEY uq_model_active_target (active_target_key),
    KEY ix_model_active_lookup (task_type, target_metric, is_active),
    CONSTRAINT ck_model_task_type CHECK (
        task_type IN ('NEXT_SEASON', 'PEAK', 'SIMILARITY', 'RANKING')
    ),
    CONSTRAINT ck_model_training_range
        CHECK (training_start_season BETWEEN 1982 AND training_end_season)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 같은 입력 컨텍스트의 예측을 재사용하기 위한 선택적 캐시다.
-- context_hash는 player/model 외 요청 feature의 정규화된 JSON SHA-256이다.
CREATE TABLE prediction_results (
    prediction_result_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    player_id INT UNSIGNED NOT NULL,
    model_version_id BIGINT UNSIGNED NOT NULL,
    context_hash CHAR(64) NOT NULL,
    base_season SMALLINT UNSIGNED NOT NULL,
    target_season SMALLINT UNSIGNED NULL,
    predicted_value DECIMAL(14,5) NOT NULL,
    lower_bound DECIMAL(14,5) NULL,
    upper_bound DECIMAL(14,5) NULL,
    explanation JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (prediction_result_id),
    UNIQUE KEY uq_prediction_context (player_id, model_version_id, context_hash),
    KEY ix_prediction_player_created (player_id, created_at DESC),
    CONSTRAINT fk_prediction_player
        FOREIGN KEY (player_id) REFERENCES players (player_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT fk_prediction_model
        FOREIGN KEY (model_version_id) REFERENCES model_versions (model_version_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_prediction_seasons CHECK (
        base_season BETWEEN 1982 AND 2200
        AND (target_season IS NULL OR target_season >= base_season)
    ),
    CONSTRAINT ck_prediction_bounds CHECK (
        (lower_bound IS NULL AND upper_bound IS NULL)
        OR (lower_bound IS NOT NULL AND upper_bound IS NOT NULL
            AND lower_bound <= predicted_value AND predicted_value <= upper_bound)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 랭킹 화면에서 반복되는 무거운 점수 계산을 피하기 위한 버전별 materialized 결과다.
CREATE TABLE player_ranking_scores (
    ranking_score_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    player_id INT UNSIGNED NOT NULL,
    team_id TINYINT UNSIGNED NOT NULL,
    season SMALLINT UNSIGNED NOT NULL,
    player_role VARCHAR(20) NOT NULL,
    score_version VARCHAR(30) NOT NULL,
    ai_score DECIMAL(8,4) NOT NULL,
    score_components JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (ranking_score_id),
    UNIQUE KEY uq_ranking_score (
        player_id, team_id, season, player_role, score_version
    ),
    KEY ix_ranking_board (
        season, player_role, score_version, ai_score DESC
    ),
    KEY ix_ranking_team_board (
        season, team_id, player_role, score_version, ai_score DESC
    ),
    CONSTRAINT fk_ranking_player
        FOREIGN KEY (player_id) REFERENCES players (player_id)
        ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT fk_ranking_team
        FOREIGN KEY (team_id) REFERENCES teams (team_id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_ranking_role CHECK (player_role IN ('BATTING', 'PITCHING')),
    CONSTRAINT ck_ranking_score CHECK (ai_score BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
