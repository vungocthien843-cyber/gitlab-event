"""
main.py — Khởi tạo FastAPI, middleware và các handler lỗi toàn cục.

Chỗ này là hiện thân của nguyên tắc "Unknown error = Fail safely": bất kỳ
exception nào lọt qua được mọi tầng đều rơi vào `unexpected_error_handler` và
được xử lý như CRITICAL — dừng, ghi log đầy đủ, trả response an toàn. Không có
đường nào để một lỗi lạ âm thầm biến thành 200 OK.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.catalogs import router as catalogs_router
from app.core.config import LOG_LEVEL
from app.core.db import dispose, init_db
from app.core.errors import (
    AppError,
    CriticalError,
    ErrorCode,
    NextAction,
    Severity,
    Stage,
    Status,
    ValidationError,
)
from app.core.logging import configure_logging, get_request_id, new_request_id, set_request_id
from app.models.schemas import ApiResponse, Issue, from_error
from app.services.store import store

configure_logging(LOG_LEVEL)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Tạo bảng nếu chưa có, rồi nạp lại chỉ mục từ database.

    Vì sao KHÔNG cho chết hẳn khi database không tới được: process chết lúc khởi
    động thì Docker healthcheck restart, chết tiếp, restart tiếp — một vòng lặp
    không ai đọc được log. Khởi động được rồi thì mỗi request tự trả
    STORAGE_FAILURE đúng contract, và dòng CRITICAL dưới đây nói rõ lý do.

    Không nuốt lỗi: nó được log ở mức CRITICAL kèm stack trace.
    """
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


app = FastAPI(
    title="IDP Catalog Graph API",
    version="2.0",
    lifespan=lifespan,
    description=(
        "Nạp catalog-info.yaml, validate 5 tầng và sinh graph JSON.\n\n"
        "Mọi endpoint trả về cùng một hình dạng response: "
        "`status` / `severity` / `code` / `message` / `can_continue` / "
        "`next_action` / `stage` / `request_id` / `issues` / `details`."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.include_router(catalogs_router)


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Gắn request_id cho mọi dòng log của request và trả nó về header.

    Người dùng báo lỗi kèm `request_id` là tra ra đúng chuỗi log — không phải
    mò theo timestamp giữa hàng nghìn dòng.
    """
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
# Exception handlers — nơi try/except "thật sự" của hệ thống nằm.
#
# Gom về một chỗ thay vì rải try/except ở từng endpoint: contract chỉ được dựng
# ở một nơi duy nhất, nên không thể có endpoint nào trả sai hình dạng.
# ─────────────────────────────────────────────────────────────────────────────


def _json(payload: ApiResponse, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": payload.request_id},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Lỗi ĐÃ ĐƯỢC PHÂN LOẠI. Mức log lấy từ chính exception:

        ValidationError      -> WARNING, không stack trace (lỗi của input, không phải bug)
        SecurityError        -> ERROR,   không stack trace (biết chính xác vì sao chặn)
        HumanReviewRequired  -> ERROR,   không stack trace
        CriticalError        -> CRITICAL + stack trace đầy đủ
    """
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
    """FastAPI tự chặn request sai hình dạng TRƯỚC khi vào code của ta (thiếu
    field `file`, sai kiểu query param...). Mặc định nó trả `{"detail": [...]}`
    — một hình dạng khác hẳn contract.

    Không dịch lại ở đây thì frontend phải viết 2 nhánh xử lý lỗi. Handler này
    kéo nhánh đó về đúng contract chung.
    """
    missing_file = any(
        e.get("type") == "missing" and "file" in [str(x) for x in e.get("loc", ())]
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
    """404 route lạ, 405 sai method... Cũng phải nói cùng một thứ tiếng."""
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
    """Lưới cuối cùng. Đến được đây nghĩa là có một lỗi ta CHƯA TỪNG LƯỜNG TRƯỚC.

    Vì không biết nó là gì, không có cách nào khẳng định hệ thống còn ở trạng
    thái an toàn -> mặc định coi là CRITICAL. Không đoán, không cho đi tiếp.

    `exc_info=True` là bắt buộc: đây là loại lỗi duy nhất mà stack trace thực sự
    cần thiết, vì nó luôn là bug của ta.

    Message trả về cố ý không kèm chi tiết kỹ thuật — thông điệp exception thô
    hay lộ đường dẫn nội bộ, tên biến, đôi khi cả chuỗi kết nối. `request_id`
    là cầu nối để tra ra chi tiết trong log.
    """
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
    """Dùng cho Docker HEALTHCHECK / uptime probe.

    Cố tình KHÔNG theo ApiResponse: probe chỉ đọc HTTP status, thêm 10 field vào
    đây chỉ làm nặng thứ được gọi vài giây một lần.
    """
    return {"status": "ok"}
