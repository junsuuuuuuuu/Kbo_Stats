"""API 전체에서 공유하는 응답 schema."""

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    """클라이언트가 code로 분기하고 message를 표시할 수 있는 오류 본문."""

    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """모든 예상 오류의 최상위 envelope."""

    error: ErrorBody


class HealthResponse(BaseModel):
    """프로세스 생존 여부 응답."""

    status: str
    environment: str
