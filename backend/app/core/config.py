"""환경변수 기반 애플리케이션 설정."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """실행 환경별로 달라지는 값만 관리한다.

    로컬 기본 URL은 개발 편의를 위한 값이며 배포 환경에서는 DATABASE_URL을 반드시
    secret 환경변수로 덮어쓴다.
    """

    app_name: str = "KBO AI Player Analytics API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "mysql+pymysql://kbo_user:change_me@localhost:3306/kbo_stats?charset=utf8mb4"
    )
    cors_origins: list[str] = ["http://localhost:3000"]
    sql_echo: bool = False
    db_pool_recycle_seconds: int = 1800
    db_pool_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """설정 파일을 요청마다 다시 읽지 않도록 한 번만 생성한다."""

    return Settings()
