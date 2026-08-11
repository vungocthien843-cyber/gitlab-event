"""
store.py — Cache trong RAM của bảng `input_json`.

Nguồn sự thật là DATABASE, không phải kho này. Kho chỉ giữ sẵn kết quả đã parse
để `GET /catalogs` và bước kiểm tra xung đột xuyên file không phải đọc lại rồi
dựng lại đồ thị từ JSON ở mọi request.

Ba luật giữ cho cache không lệch khỏi DB:
  - Ghi/xoá LUÔN đi qua DB trước, cập nhật cache sau. DB hỏng thì cache không đổi.
  - `replaced` lấy từ kết quả DB trả về, không suy từ việc key có trong dict.
  - Lúc khởi động, `load_from_db()` nạp lại toàn bộ — restart không mất danh sách.

Vẫn còn một giới hạn: chạy nhiều worker uvicorn thì mỗi worker có cache riêng,
nên worker A upload xong worker B chưa thấy ngay cho tới lần khởi động sau. Dữ
liệu không sai (DB vẫn đúng), chỉ là danh sách có thể cũ. Chấp nhận được ở quy
mô hiện tại; muốn bỏ hẳn thì cho `list()`/`all_parsed()` đọc thẳng DB.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from src.models.schemas import CatalogSummary
from src.repositories import catalog_repository
from src.services.catalog_to_graph import Diagnostics, Issue, ParsedFile

logger = logging.getLogger(__name__)


def output_name(filename: str) -> str:
    """'order-service.catalog.yaml' -> 'order-service.json'

    Tên logic của tài liệu JSON. Không còn file nào trên đĩa mang tên này, nhưng
    nó vẫn là nhãn frontend đang hiển thị và là tên gợi ý khi người dùng tải về.

    Đặt ở đây chứ không ở `ingest` vì cả hai chiều đều cần: `ingest` dựng nó lúc
    lưu, `StoredCatalog.from_document` dựng lại nó lúc nạp từ DB.
    """
    stem = os.path.splitext(filename)[0]
    if stem.endswith(".catalog"):
        stem = stem[: -len(".catalog")]
    return f"{stem}.json"


def _parse_generated_at(value: Any) -> datetime | None:
    """'2026-08-09T10:20:30Z' -> datetime. Hỏng thì trả None chứ không nổ.

    Trường này chỉ để hiển thị. Một tài liệu cũ có timestamp lạ không đáng để
    chặn cả việc nạp lại chỉ mục lúc khởi động.
    """
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class StoredCatalog:
    """Một catalog đã qua đủ 5 tầng validate và đã nằm trong bảng `input_json`."""

    parsed: ParsedFile
    fingerprint: str
    output_file: str | None
    record_id: int | None = None
    # None với bản nạp lại từ DB: kích thước file YAML gốc không phải nội dung
    # của JSON nên không lưu trong `content`, và bịa ra một con số còn tệ hơn.
    size_bytes: int | None = None
    uploaded_at: datetime | None = field(default_factory=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")))

    @property
    def filename(self) -> str:
        return self.parsed.filename

    @property
    def warning_count(self) -> int:
        return len(self.parsed.diagnostics.warnings)

    @property
    def state(self) -> str:
        return "valid_with_warnings" if self.warning_count else "valid"

    @classmethod
    def from_document(
        cls, document: dict[str, Any], record_id: int | None = None
    ) -> StoredCatalog | None:
        """Dựng lại từ JSON đã lưu. None nếu tài liệu không đủ để dựng.

        Đây là chiều ngược của `_save_graph_document`: mọi thứ `CatalogSummary`
        cần đều rút được từ chính nội dung JSON, trừ `size_bytes`.

        Trả None thay vì raise: một dòng lạ trong bảng (bản cũ, ai đó chèn tay)
        không được phép làm sập cả tiến trình lúc khởi động. Bỏ qua dòng đó và
        ghi log là đủ.
        """
        filename = catalog_repository.document_filename(document)
        if filename is None:
            return None

        sources = document.get("scope", {}).get("sources") or [{}]
        diagnostics = document.get("diagnostics") or {}

        parsed = ParsedFile(
            filename=filename,
            nodes=document.get("nodes") or {},
            edges=document.get("edges") or [],
            root_id=sources[0].get("root"),
            diagnostics=Diagnostics(
                errors=[Issue(**i) for i in diagnostics.get("errors", [])],
                warnings=[Issue(**i) for i in diagnostics.get("warnings", [])],
            ),
        )
        return cls(
            parsed=parsed,
            fingerprint="",
            output_file=output_name(filename),
            record_id=record_id,
            size_bytes=None,
            uploaded_at=_parse_generated_at(document.get("generatedAt")),
        )

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
            record_id=self.record_id,
            diagnostics=self.parsed.diagnostics.as_dict() if include_diagnostics else None,
        ).model_dump(mode="json")


class CatalogStore:
    """Cache catalog, an toàn với truy cập đồng thời.

    `Lock` là cần thiết dù FastAPI chạy async: endpoint đồng bộ được uvicorn đẩy
    ra threadpool, nên hai request có thể sửa dict cùng lúc thật.
    """

    def __init__(self) -> None:
        self._items: dict[str, StoredCatalog] = {}
        self._lock = threading.Lock()

    def put(self, item: StoredCatalog) -> None:
        """Cập nhật cache sau khi DB đã ghi xong.

        Không trả cờ `replaced` như bản cũ: chuyện "có ghi đè hay không" giờ do
        DB trả lời (`catalog_repository.save`). Cache mà tự trả lời câu đó thì
        sau một lần restart giữa chừng nó sẽ nói sai.
        """
        with self._lock:
            self._items[item.filename] = item

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

    def load_from_db(self) -> int:
        """Nạp lại toàn bộ chỉ mục từ bảng `input_json`. Trả số bản ghi đã nạp.

        Gọi lúc khởi động: dữ liệu đã vào DB thì restart xong phải nhìn thấy lại,
        nếu không người dùng sẽ tưởng mất dữ liệu và upload đè lên chính nó.
        """
        documents = catalog_repository.all_documents()

        loaded: dict[str, StoredCatalog] = {}
        skipped = 0
        for record_id, doc in documents:
            item = StoredCatalog.from_document(doc, record_id)
            if item is None:
                skipped += 1
                continue
            loaded[item.filename] = item

        with self._lock:
            self._items = loaded

        if skipped:
            logger.warning("Bỏ qua %d dòng không dựng lại được từ input_json", skipped)
        logger.info("Đã nạp %d catalog từ database vào chỉ mục", len(loaded))
        return len(loaded)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


store = CatalogStore()

