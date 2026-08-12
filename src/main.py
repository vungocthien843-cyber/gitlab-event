from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import LOG_LEVEL
from src.core.db import dispose, init_db
from src.core.errors import (
    AppError,
    CriticalError,
    ErrorCode,
    NextAction,
    Severity,
    Stage,
    Status,
    ValidationError,
)
from src.core.logging import configure_logging, get_request_id, new_request_id, set_request_id
from src.models.schemas import ApiResponse, Issue, from_error
from src.core.store import store

from src.api.routes import router
from src.core.config import get_settings

configure_logging(LOG_LEVEL)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    try:
        init_db()
        store.load_from_db()
    except Exception:
        logger.critical(
            "Không khởi tạo được database lúc khởi động. API vẫn chạy nhưng mọi "
            "thao tác đọc/ghi catalog sẽ trả STORAGE_FAILURE cho tới khi DB trở lại.",
            exc_info=True,
        )
    yield
    dispose()
    print("Shutting down...")

app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph (Integrated with IDP Catalog Graph API)",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 1. Xử lý đường dẫn gốc (Bỏ lỗi GET /)
@app.get("/", tags=["Trang chủ"])
async def root():
    return {
        "status": "success",
        "message": "Hệ thống Webhook API đang hoạt động bình thường!"
    }

# 2. Xử lý trình duyệt xin logo (Bỏ lỗi GET /favicon.ico và /favicon.png)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return Response(status_code=204)

@app.get("/favicon.png", include_in_schema=False)
async def favicon_png():
    return Response(status_code=204)

# Nhúng toàn bộ route từ src/api/routes.py vào tiền tố /api/v1
app.include_router(router, prefix="/api/v1")

# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    set_request_id(request_id)
    started = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response

# ─────────────────────────────────────────────────────────────────────────────
# Exception handlers
# ─────────────────────────────────────────────────────────────────────────────
def _json(payload: ApiResponse, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": payload.request_id},
    )

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.log(
        exc.log_level,
        "stage=%s code=%s path=%s | %s",
        exc.stage.value, exc.code.value, request.url.path, exc.log_message,
        exc_info=exc.log_traceback,
    )
    return _json(from_error(exc, request_id=get_request_id()), exc.http_status)

@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    missing_file = any(
        e.get("type") == "missing" and "files" in [str(x) for x in e.get("loc", ())]
        for e in exc.errors()
    )
    code = ErrorCode.NO_FILE if missing_file else ErrorCode.INVALID_STRUCTURE
    message = (
        "Chưa chọn file để tải lên."
        if missing_file
        else "Dữ liệu gửi lên không đúng định dạng yêu cầu."
    )

    wrapped = ValidationError(
        code,
        message,
        stage=Stage.RECEIVE,
        issues=[
            Issue(
                severity="error",
                code=str(e.get("type", "invalid")),
                message=str(e.get("msg", "")),
                location=".".join(str(x) for x in e.get("loc", ())),
            )
            for e in exc.errors()
        ],
    )
    logger.warning("Request sai hình dạng ở %s: %s", request.url.path, code.value)
    return _json(from_error(wrapped, request_id=get_request_id()), wrapped.http_status)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    severity = Severity.VALIDATION if exc.status_code < 500 else Severity.CRITICAL
    payload = ApiResponse(
        status=Status.of(severity),
        severity=severity,
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        can_continue=False,
        next_action=(
            NextAction.FIX_AND_REUPLOAD if exc.status_code < 500 else NextAction.CONTACT_SUPPORT
        ),
        stage=Stage.RECEIVE,
        request_id=get_request_id(),
    )
    return _json(payload, exc.status_code)

@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.critical(
        "Exception ngoài dự kiến ở %s %s: %s",
        request.method, request.url.path, type(exc).__name__,
        exc_info=True,
    )
    wrapped = CriticalError(
        ErrorCode.INTERNAL_ERROR,
        "Không thể xử lý yêu cầu. Vui lòng thử lại hoặc liên hệ hỗ trợ kèm mã request.",
        stage=Stage.RECEIVE,
    )
    return _json(from_error(wrapped, request_id=get_request_id()), wrapped.http_status)

# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Kiểm tra sức khoẻ dịch vụ")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
