"""
logging.py — Cấu hình log + request-id để nối các dòng log của cùng 1 request.

Nguyên tắc:
  - Mỗi request có 1 `request_id`. Nó nằm trong MỌI dòng log của request đó và
    cũng nằm trong response trả cho frontend. Người dùng báo lỗi kèm request_id
    là tra được đúng chuỗi log, không phải mò theo timestamp.
  - KHÔNG log nội dung file, không log token/password/API key/email người dùng.
    Chỉ log metadata: tên file (đã làm sạch), kích thước, sha256 rút gọn,
    mã lỗi, chặng xử lý.
  - Stack trace chỉ ghi cho lỗi PHÍA HỆ THỐNG. Lỗi do input người dùng ghi ở mức
    WARNING không kèm trace — nếu không, log sẽ ngập lỗi vô hại và che mất bug thật.
"""

from __future__ import annotations

import hashlib
import logging
import logging.config
import sys
import uuid
from contextvars import ContextVar

# ContextVar chứ không phải biến global: mỗi request/coroutine có giá trị riêng,
# chạy song song vẫn không lẫn.
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    """Bơm request_id vào mọi LogRecord để format string dùng được `%(request_id)s`."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | req=%(request_id)s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Gọi 1 lần lúc app khởi động. `disable_existing_loggers=False` để không
    bịt miệng logger của uvicorn."""
    # Message log viết bằng tiếng Việt. Khi stdout bị redirect (file log, Docker,
    # CI), Python lấy encoding theo locale — trên Windows là cp1252, không biểu
    # diễn được tiếng Việt và log ra thành ký tự rác. Ép UTF-8 ngay tại đây.
    # `errors="replace"` để một ký tự lạ không bao giờ giết được tiến trình.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # stream đã bị thay bằng object khác (pytest capture chẳng hạn)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIdFilter}},
            "formatters": {
                "standard": {"format": LOG_FORMAT, "datefmt": "%Y-%m-%dT%H:%M:%S%z"}
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
            },
        }
    )


def content_fingerprint(data: bytes) -> str:
    """Vân tay nội dung để log/đối chiếu mà KHÔNG lộ nội dung.

    12 hex đầu của sha256 — đủ để nhận ra "vẫn là file cũ upload lại lần 3",
    không đủ để dựng ngược nội dung.
    """
    return hashlib.sha256(data).hexdigest()[:12]
