"""
catalog_repository.py — Đọc/ghi bảng `input_json`.

Đây là tầng DUY NHẤT biết tới SQLAlchemy. Tầng trên (`ingest`, `store`) chỉ nhận
và trả về dict JSON thuần, nên đổi Postgres sang thứ khác chỉ phải viết lại file
này — đúng như lời hứa trong docstring của `store.py` từ đầu.

Tra cứu theo TÊN FILE trong khi khoá chính là `id` tự tăng: tên file gốc đã nằm
sẵn trong cột `information` ở `information.scope.sources[0].file` (do
`merge_documents` ghi vào), nên không cần thêm cột phụ.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from src.core.db import session_scope
from src.core.errors import CriticalError, ErrorCode, Stage
from src.models.tables import InputJson

logger = logging.getLogger(__name__)


def information_filename(information: dict[str, Any]) -> str | None:
    """Tên file gốc đã sinh ra tài liệu này ('order-service.yaml').

    Một tài liệu lưu trong bảng luôn được merge từ đúng MỘT file, nên
    `sources` luôn có đúng một phần tử. Vẫn viết phòng thủ vì hàm này còn được
    gọi trên dữ liệu đọc từ DB — thứ có thể do bản cũ hoặc do người khác ghi.
    """
    sources = (information.get("scope") or {}).get("sources") or []
    if not sources:
        return None
    return sources[0].get("file")


# Biểu thức SQL trỏ tới đúng chỗ chứa tên file trong cột `information`.
# `.astext` là toán tử `#>>` của Postgres: lấy ra chuỗi thay vì một giá trị JSON,
# nhờ vậy so sánh trực tiếp được với tham số Python.
_FILENAME_COLUMN = InputJson.information["scope"]["sources"][0]["file"].astext


@contextmanager
def _storage_guard(action: str) -> Iterator[None]:
    """Biến mọi lỗi SQLAlchemy thành CriticalError/STORAGE_FAILURE.

    Không để `SQLAlchemyError` lọt lên tầng trên: handler toàn cục sẽ bắt nó như
    một exception lạ và trả INTERNAL_ERROR, trong khi đây là tình huống ta HIỂU
    RÕ — kho lưu trữ không dùng được. Hai mã lỗi khác nhau dẫn tới hai cách xử lý
    khác nhau ở phía vận hành.

    `log_message` cố ý chỉ mang tên lớp exception: thông điệp lỗi kết nối của
    psycopg2 có thể kèm nguyên chuỗi DSN, tức là kèm cả mật khẩu database.
    """
    try:
        yield
    except SQLAlchemyError as exc:
        raise CriticalError(
            ErrorCode.STORAGE_FAILURE,
            "Không lưu được kết quả xử lý. Vui lòng thử lại sau.",
            stage=Stage.PERSIST,
            log_message=f"Thao tác '{action}' trên bảng input_json thất bại: "
            f"{type(exc).__name__}",
        ) from exc


def _row_to_dict(row: InputJson) -> dict[str, Any]:
    return {
        "nodes": row.nodes,
        "edges": row.edges,
        "information": row.information,
        "diagnostics": row.diagnostics,
        "file_json": row.file_json,
    }


def save(
    *,
    nodes: dict[str, Any],
    edges: list[dict[str, Any]],
    information: dict[str, Any],
    diagnostics: dict[str, Any],
) -> tuple[int, bool]:
    """Lưu tài liệu. Trả `(id, đã_ghi_đè)`.

    Cùng một file upload lại thì GHI ĐÈ đúng dòng cũ chứ không sinh dòng mới:
    bảng phản ánh "các catalog đang có", không phải nhật ký upload. Nếu cứ chèn
    thêm, `GET /catalogs` sẽ phải tự đoán dòng nào là bản mới nhất — một câu hỏi
    không nên tồn tại.

    `file_json` không nhận từ caller — tự dựng lại từ `nodes`+`edges` ở đây, để
    bất biến "file_json luôn nhất quán với nodes+edges" chỉ cần giữ ở một chỗ.
    """
    filename = information_filename(information)
    if filename is None:
        raise CriticalError(
            ErrorCode.INCONSISTENT_STATE,
            "Không lưu được kết quả xử lý.",
            stage=Stage.PERSIST,
            log_message="Tài liệu chuẩn bị lưu không có information.scope.sources[0].file — "
            "lỗi ở tầng sinh JSON, không phải ở input.",
        )

    file_json = {"nodes": nodes, "edges": edges}

    with _storage_guard("save"), session_scope() as session:
        row = session.scalars(
            select(InputJson).where(_FILENAME_COLUMN == filename)
        ).first()

        if row is not None:
            row.nodes = nodes
            row.edges = edges
            row.information = information
            row.diagnostics = diagnostics
            row.file_json = file_json
            session.flush()
            return row.id, True

        row = InputJson(
            nodes=nodes, edges=edges, information=information,
            diagnostics=diagnostics, file_json=file_json,
        )
        session.add(row)
        session.flush()  # để Postgres cấp id ngay, đọc được trước khi commit
        return row.id, False


def find(filename: str) -> dict[str, Any] | None:
    """Trả dict gộp {nodes, edges, information, diagnostics, file_json}."""
    with _storage_guard("find"), session_scope() as session:
        row = session.scalars(
            select(InputJson).where(_FILENAME_COLUMN == filename)
        ).first()
        return _row_to_dict(row) if row is not None else None


def delete(filename: str) -> bool:
    """Xoá dòng của 1 file. Trả True nếu thật sự có dòng bị xoá."""
    with _storage_guard("delete"), session_scope() as session:
        row = session.scalars(
            select(InputJson).where(_FILENAME_COLUMN == filename)
        ).first()
        if row is None:
            return False
        session.delete(row)
        return True


def all_documents() -> list[tuple[int, dict[str, Any]]]:
    """Toàn bộ `(id, dict gộp)`, sắp theo id — dùng để dựng lại cache lúc khởi động.

    Trả kèm `id` chứ không chỉ nội dung: bản ghi nạp lại sau restart vẫn phải
    biết mình là dòng nào trong bảng, nếu không `record_id` sẽ là null cho tới
    lần upload kế tiếp.
    """
    with _storage_guard("all_documents"), session_scope() as session:
        rows = session.scalars(select(InputJson).order_by(InputJson.id)).all()
        return [(row.id, _row_to_dict(row)) for row in rows]


def count() -> int:
    with _storage_guard("count"), session_scope() as session:
        return session.scalar(select(func.count()).select_from(InputJson)) or 0
