"""
events.py — Hình dạng các sự kiện real-time đẩy qua SSE cho dashboard theo
dõi push GitHub. Tách khỏi schemas.py vì đây không phải contract
request/response (ApiResponse) mà là contract STREAM — mỗi push sinh ra N sự
kiện rời rạc theo thời gian.

Ba loại sự kiện, đúng theo vòng đời của handle_push:
    push_started    -> lúc bắt đầu, biết trước tổng số file sẽ xử lý
    file_result     -> ngay sau khi MỘT file có kết quả (thành/bại/bỏ qua/xoá)
    push_completed  -> lúc kết thúc, mirror đúng details của ApiResponse cuối

Dùng lại Issue từ schemas.py cho phần lỗi thay vì tạo shape song song.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.models.schemas import Issue

FileOutcome = Literal["ingested", "deleted", "skipped", "failed"]


class PushStartedEvent(BaseModel):
    """Bắn ngay khi handle_push biết đủ thông tin để bắt đầu — trước khi
    chạm file đầu tiên. Cho dashboard dựng thanh tiến độ 0/N ngay lập tức."""

    repository: str
    branch: str
    commit_id: str
    commit_url: str
    total_files: int = Field(description="Tổng số file added+modified+removed sẽ xử lý")


class FileResultEvent(BaseModel):
    """Bắn ngay sau khi MỘT file có kết quả cuối cùng."""

    path: str = Field(description="Đường dẫn đầy đủ trong repo")
    filename: str = Field(description="Chỉ tên file")
    outcome: FileOutcome
    issue: Issue | None = Field(
        default=None,
        description="Chi tiết lỗi/cảnh báo — None khi outcome='ingested' sạch tuyệt đối",
    )


class PushCompletedEvent(BaseModel):
    """Bắn sau khi dựng xong response tổng — mirror đúng details hiện có của
    ApiResponse cuối."""

    repository: str
    branch: str
    commit_id: str
    status: Literal["success", "warning"]
    hashed: list[str]
    ingested: list[str]
    deleted: list[str]
    skipped: list[str]
    failed: list[str]
