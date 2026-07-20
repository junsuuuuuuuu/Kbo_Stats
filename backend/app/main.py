"""FastAPI application factory와 공통 middleware/exception handler."""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import ApplicationError
from app.schemas.common import ErrorBody, ErrorResponse

logger = logging.getLogger("kbo_api")


def error_response(
    *, code: str, message: str, status_code: int, details: object | None = None
) -> JSONResponse:
    """모든 handler가 동일한 JSON 오류 계약을 사용하도록 응답을 생성한다."""

    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


def create_app() -> FastAPI:
    """테스트에서 새 app을 만들 수 있도록 전역 초기화를 factory로 캡슐화한다."""

    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="1982~2025 KBO 선수 기록 검색 및 AI 분석 API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        """요청 ID와 처리 시간을 응답/로그에 남긴다."""

        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if (
            request.method == "GET"
            and "/analytics/" in request.url.path
            and response.status_code < 400
        ):
            # 분석 결과는 모델/데이터 버전이 바뀌기 전까지 결정적이므로 edge cache가 가능하다.
            response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        logger.info(
            "request_completed method=%s path=%s status=%s latency_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response

    @application.exception_handler(ApplicationError)
    async def application_error_handler(
        _request: Request, exception: ApplicationError
    ) -> JSONResponse:
        """도메인 예외를 안전한 공개 오류 형식으로 변환한다."""

        return error_response(
            code=exception.code,
            message=exception.message,
            details=exception.details,
            status_code=exception.status_code,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        """FastAPI 입력 검증 오류도 공통 envelope로 반환한다."""

        return error_response(
            code="VALIDATION_ERROR",
            message="요청 값이 올바르지 않습니다.",
            details=exception.errors(),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exception: Exception) -> JSONResponse:
        """예상하지 못한 내부 정보를 노출하지 않고 서버 로그에만 남긴다."""

        logger.exception("unhandled_error path=%s", request.url.path, exc_info=exception)
        return error_response(
            code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
