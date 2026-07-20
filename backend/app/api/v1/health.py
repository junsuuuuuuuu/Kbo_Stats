"""배포 플랫폼에서 사용하는 health endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="프로세스 상태 확인")
def health_check() -> HealthResponse:
    """DB 접근 없이 API 프로세스가 요청을 처리할 수 있는지 확인한다."""

    settings = get_settings()
    return HealthResponse(status="ok", environment=settings.app_env)
