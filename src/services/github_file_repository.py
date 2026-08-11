"""
github_file_repository.py — Ghi 3 bảng `github_files_{added,modified,removed}`.

Cùng vai trò với `catalog_repository.py`: tầng duy nhất chạm SQLAlchemy cho 3
bảng này. Tầng trên (`github_events.py`) chỉ đưa vào giá trị Python thuần và
nhận về một `int` id, nên đổi Postgres sang thứ khác chỉ phải viết lại file này.

Chỉ có INSERT, không có UPDATE và không có DELETE — xem docstring của
`GithubFileEventMixin` trong `src/models/tables.py`.
"""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError

from src.core.db import session_scope
from src.core.errors import CriticalError, ErrorCode, Stage
from src.models.tables import GithubFileAdded, GithubFileModified, GithubFileRemoved

logger = logging.getLogger(__name__)

FileStatus = Literal["added", "modified", "removed"]

_MODEL_BY_STATUS = {
    "added": GithubFileAdded,
    "modified": GithubFileModified,
    "removed": GithubFileRemoved,
}


def record_file_event(
    *,
    status: FileStatus,
    file_hash: str,
    email: str,
    branch: str,
    commit_url: str,
    event_time: str,
    file_name: str,
    url: str,
) -> int:
    """Ghi 1 dòng vào đúng bảng theo `status`. Trả về id vừa được cấp.

    Tham số bắt buộc truyền theo tên (`*`): nhiều cột đều là chuỗi, truyền theo
    vị trí thì hoán nhầm `branch` với `file_name` vẫn chạy êm và chỉ lộ ra khi
    có người đọc bảng.
    """
    model = _MODEL_BY_STATUS[status]
    try:
        with session_scope() as session:
            row = model(
                file_hash=file_hash,
                email=email,
                branch=branch,
                commit_url=commit_url,
                event_time=event_time,
                file_name=file_name,
                url=url,
            )
            session.add(row)
            # flush để Postgres cấp id ngay, đọc được trước khi commit.
            session.flush()
            record_id = row.id
    except SQLAlchemyError as exc:
        # Không để `SQLAlchemyError` lọt lên: handler toàn cục sẽ bắt nó như một
        # exception lạ và trả INTERNAL_ERROR, trong khi đây là tình huống ta HIỂU
        # RÕ — kho lưu trữ không dùng được.
        #
        # `log_message` cố ý chỉ mang tên lớp exception: thông điệp lỗi kết nối
        # của psycopg2 có thể kèm nguyên chuỗi DSN, tức là kèm cả mật khẩu.
        raise CriticalError(
            ErrorCode.STORAGE_FAILURE,
            "Không lưu được nhật ký thay đổi file. Vui lòng thử lại sau.",
            stage=Stage.PERSIST,
            log_message=f"Ghi bảng github_files_{status} thất bại: {type(exc).__name__}",
        ) from exc

    logger.info(
        "Đã ghi nhật ký file %s: id=%d branch=%s file=%s hash=%s",
        status, record_id, branch, file_name, file_hash[:12],
    )
    return record_id
