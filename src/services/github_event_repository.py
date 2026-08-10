"""
github_event_repository.py — Ghi bảng `github_commits_log`.

Cùng vai trò với `catalog_repository.py`: tầng duy nhất chạm SQLAlchemy cho bảng
này. Tầng trên chỉ đưa vào các giá trị Python thuần và nhận về một `int` id, nên
đổi Postgres sang thứ khác chỉ phải viết lại file này.

Chỉ có INSERT, không có UPDATE và không có DELETE. Bảng là nhật ký của những
việc ĐÃ XẢY RA — sửa hay xoá một dòng nghĩa là làm hỏng chính thứ mà nhật ký sinh
ra để bảo vệ. Muốn biết trạng thái hiện tại của catalog thì đọc `input_json`.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from src.core.db import session_scope
from src.core.errors import CriticalError, ErrorCode, Stage
from src.models.tables import GithubCommitLog

logger = logging.getLogger(__name__)


def save_commit_event(
    *,
    email: str,
    branch: str,
    commit_url: str,
    timestamp: str,
    added_files: list[str],
    modified_files: list[str],
    removed_files: list[str],
) -> int:
    """Ghi 1 dòng nhật ký cho một lần push. Trả về id vừa được cấp.

    Tham số bắt buộc truyền theo tên (`*`): bảy giá trị thì bốn cái đầu đều là
    chuỗi và ba cái cuối đều là list chuỗi — truyền theo vị trí thì hoán nhầm
    `email` với `branch` vẫn chạy êm và chỉ lộ ra khi có người đọc bảng.
    """
    try:
        with session_scope() as session:
            row = GithubCommitLog(
                email=email,
                branch=branch,
                commit_url=commit_url,
                timestamp=timestamp,
                added_files=added_files,
                modified_files=modified_files,
                removed_files=removed_files,
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
            "Không lưu được nhật ký commit. Vui lòng thử lại sau.",
            stage=Stage.PERSIST,
            log_message=f"Ghi bảng github_commits_log thất bại: {type(exc).__name__}",
        ) from exc

    logger.info(
        "Đã ghi nhật ký push: id=%d branch=%s added=%d modified=%d removed=%d",
        record_id, branch, len(added_files), len(modified_files), len(removed_files),
    )
    return record_id

