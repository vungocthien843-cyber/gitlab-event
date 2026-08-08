"""
store.py — Kho lưu các catalog đã nạp thành công (in-memory).

Tách khỏi tầng API vì hai lý do:
  - Controller không nên biết dữ liệu nằm ở dict hay Postgres. Đổi sang DB thật
    sau này chỉ cần viết lại file này, các tầng khác không đổi một dòng.
  - Trạng thái nằm sau một class thì mọi đường ghi/xoá đi qua đúng vài phương
    thức, kiểm soát được. `_store` là dict global thì bất cứ đâu cũng sửa được.

GIỚI HẠN CẦN BIẾT: dữ liệu nằm trong RAM, restart server là mất sạch, và nhiều
worker uvicorn thì mỗi worker có kho riêng. Chấp nhận được ở giai đoạn này vì
file JSON đã ghi ra đĩa mới là nguồn sự thật; kho này chỉ là chỉ mục.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models.schemas import CatalogSummary
from app.services.catalog_to_graph import ParsedFile


@dataclass
class StoredCatalog:
    """Một catalog đã qua đủ 5 tầng validate và đã ghi JSON ra đĩa."""

    parsed: ParsedFile
    size_bytes: int
    fingerprint: str
    output_file: str | None
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def filename(self) -> str:
        return self.parsed.filename

    @property
    def warning_count(self) -> int:
        return len(self.parsed.diagnostics.warnings)

    @property
    def state(self) -> str:
        return "valid_with_warnings" if self.warning_count else "valid"

    def summary_dict(self, include_diagnostics: bool = False) -> dict[str, Any]:
        """Đi qua model `CatalogSummary` chứ không tự dựng dict.

        Model vừa là tài liệu OpenAPI, vừa là chốt kiểm: thêm/bớt field ở đây mà
        quên cập nhật model là vỡ ngay lúc chạy test, không lặng lẽ trôi ra
        frontend. `mode="json"` lo luôn việc đổi datetime sang chuỗi ISO.
        """
        return CatalogSummary(
            file=self.filename,
            root=self.parsed.root_id,
            state=self.state,
            error_count=len(self.parsed.diagnostics.errors),
            warning_count=self.warning_count,
            node_count=len(self.parsed.nodes),
            edge_count=len(self.parsed.edges),
            size_bytes=self.size_bytes,
            uploaded_at=self.uploaded_at,
            output_file=self.output_file,
            diagnostics=self.parsed.diagnostics.as_dict() if include_diagnostics else None,
        ).model_dump(mode="json")


class CatalogStore:
    """Kho catalog, an toàn với truy cập đồng thời.

    `Lock` là cần thiết dù FastAPI chạy async: endpoint đồng bộ được uvicorn đẩy
    ra threadpool, nên hai request có thể sửa dict cùng lúc thật.
    """

    def __init__(self) -> None:
        self._items: dict[str, StoredCatalog] = {}
        self._lock = threading.Lock()

    def put(self, item: StoredCatalog) -> bool:
        """Lưu (hoặc thay thế). Trả True nếu đã GHI ĐÈ một bản cũ.

        Trả về cờ này để tầng trên biết mà báo warning FILE_REPLACED — ghi đè
        âm thầm là cách dễ nhất để người dùng mất dữ liệu mà không hay biết.
        """
        with self._lock:
            replaced = item.filename in self._items
            self._items[item.filename] = item
            return replaced

    def get(self, filename: str) -> StoredCatalog | None:
        with self._lock:
            return self._items.get(filename)

    def delete(self, filename: str) -> StoredCatalog | None:
        """Xoá và trả về bản ghi vừa xoá (None nếu không có)."""
        with self._lock:
            return self._items.pop(filename, None)

    def list(self, query: str | None = None) -> list[StoredCatalog]:
        """Liệt kê, sắp theo tên. `query` là tìm kiếm chuỗi con, không phân biệt hoa thường.

        Một endpoint phục vụ cả hai cách chọn file ở màn hình xoá: không truyền
        `query` -> danh sách đầy đủ cho dropdown; có `query` -> kết quả tìm kiếm.
        Hai endpoint riêng cho cùng một phép lọc chỉ tạo thêm chỗ để lệch nhau.
        """
        with self._lock:
            items = list(self._items.values())
        if query:
            needle = query.strip().lower()
            items = [i for i in items if needle in i.filename.lower()]
        return sorted(items, key=lambda i: i.filename)

    def all_parsed(self, exclude: str | None = None) -> list[ParsedFile]:
        """Toàn bộ ParsedFile — dùng để kiểm tra xung đột xuyên file.

        `exclude` bỏ qua chính file đang được upload lại, nếu không nó sẽ tự
        xung đột với phiên bản cũ của chính mình.
        """
        with self._lock:
            return [i.parsed for name, i in self._items.items() if name != exclude]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


store = CatalogStore()
