"""
ingest.py — Điều phối luồng nạp một catalog, sau khi input đã sạch.

    validate (5 tầng)  ->  kiểm tra xung đột xuyên file  ->  ghi JSON  ->  lưu chỉ mục
                                                                       ->  dựng response

Đây là tầng DUY NHẤT biết thứ tự các bước. Controller không biết, validator
không biết. Muốn chèn thêm một bước (lưu DB, gọi LLM, bắn event) thì thêm đúng
ở đây, và nó tự nằm trong đúng nhánh xử lý lỗi.

Vì sao KHÔNG bọc cả luồng trong một try/except khổng lồ: một `except Exception`
duy nhất ôm cả validate lẫn ghi đĩa thì không còn phân biệt được "người dùng gửi
file sai" (422, tự sửa được) với "đĩa đầy" (500, gọi support). Mỗi bước bắt đúng
loại lỗi mình hiểu, phần còn lại để rơi lên handler toàn cục thành critical.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
from pathlib import Path
from typing import Any

from app.core.config import OUTPUT_DIR
from app.core.errors import (
    CriticalError,
    ErrorCode,
    HumanReviewRequiredError,
    SecurityError,
    Stage,
    ValidationError,
)
from app.models import schemas
from app.models.schemas import ApiResponse, Issue
from app.services.catalog_merge import merge_documents
from app.services.catalog_to_graph import ParsedFile
from app.services.store import StoredCatalog, store
from app.services.validation import run_validation_pipeline

logger = logging.getLogger(__name__)

# Hai mã lỗi này nghĩa là hai file cùng nhận là chủ sở hữu một node. Hệ thống
# ĐỌC ĐƯỢC cả hai file, không có gì hỏng — nó chỉ không có cơ sở nào để chọn bên
# nào đúng. Chọn bừa = âm thầm ghi đè catalog của đội khác. Đây đúng là chỗ cần
# con người, xem `HumanReviewRequired`.
_HITL_CONFLICT_CODES = {"DUPLICATE_DECLARATION", "AMBIGUOUS_OWNER"}


def ingest_catalog(
    filename: str | None,
    content: bytes,
    content_type: str | None,
    request_id: str,
) -> ApiResponse:
    """Nạp 1 catalog. Raise AppError nếu không thể hoàn tất."""

    # ── Bước 1: 5 tầng validate. Lỗi bay thẳng lên handler, không bắt ở đây. ──
    validated = run_validation_pipeline(filename, content, content_type)
    parsed = validated.parsed

    logger.info(
        "Input hợp lệ: file=%s size=%dB sha=%s nodes=%d edges=%d warnings=%d",
        validated.filename, validated.size_bytes, validated.fingerprint,
        len(parsed.nodes), len(parsed.edges), len(validated.warnings),
    )

    # ── Bước 2: xung đột với các file đã nạp trước đó ────────────────────────
    _check_cross_file_conflicts(parsed, validated.filename)

    # ── Bước 3: ghi JSON ra đĩa ──────────────────────────────────────────────
    output_file = _write_graph_json(parsed)

    # ── Bước 4: cập nhật chỉ mục ─────────────────────────────────────────────
    replaced = store.put(
        StoredCatalog(
            parsed=parsed,
            size_bytes=validated.size_bytes,
            fingerprint=validated.fingerprint,
            output_file=output_file,
        )
    )

    # ── Bước 5: dựng response ────────────────────────────────────────────────
    return _build_ingest_response(validated, output_file, replaced, request_id)


# ─────────────────────────────────────────────────────────────────────────────
# Các bước
# ─────────────────────────────────────────────────────────────────────────────


def _check_cross_file_conflicts(parsed: ParsedFile, filename: str) -> None:
    """Gộp thử file mới với các file đã có, xem có tranh chấp quyền sở hữu không.

    Chỉ nhìn một file thì không phát hiện được — phải nhìn toàn cục.
    """
    others = store.all_parsed(exclude=filename)
    if not others:
        return

    merged = merge_documents([*others, parsed])
    conflicts = [
        e for e in merged["diagnostics"]["errors"] if e["code"] in _HITL_CONFLICT_CODES
    ]
    if not conflicts:
        return

    logger.error(
        "Xung đột quyền sở hữu khi nạp '%s': %d tranh chấp -> chuyển human review",
        filename, len(conflicts),
    )
    raise HumanReviewRequiredError(
        ErrorCode.NEEDS_HUMAN_REVIEW,
        f"File này tranh chấp quyền sở hữu {len(conflicts)} thành phần với catalog "
        "đã có trên hệ thống. Cần người phụ trách xác nhận trước khi ghi đè.",
        stage=Stage.STORE,
        details={"conflict_count": len(conflicts)},
        issues=[
            Issue(
                severity="error",
                code=c["code"],
                message=c["message"],
                subject=c.get("subject"),
                source=c.get("source"),
            )
            for c in conflicts
        ],
    )


def _output_name(filename: str) -> str:
    """'order-service.catalog.yaml' -> 'order-service.json'"""
    stem = os.path.splitext(filename)[0]
    if stem.endswith(".catalog"):
        stem = stem[: -len(".catalog")]
    return f"{stem}.json"


def _resolve_output_path(filename: str) -> Path:
    """Dựng đường dẫn output và KHẲNG ĐỊNH nó nằm trong OUTPUT_DIR.

    Layer 2 đã chặn path traversal ở tên file. Chốt chặn thứ hai này tồn tại vì
    hàm `_write_graph_json` có thể bị gọi từ chỗ khác trong tương lai — an toàn
    không nên phụ thuộc vào việc người gọi có nhớ validate hay không.
    """
    base = Path(OUTPUT_DIR).resolve()
    target = (base / _output_name(filename)).resolve()
    if not target.is_relative_to(base):
        raise SecurityError(
            ErrorCode.UNSAFE_FILENAME,
            "Tên file không hợp lệ.",
            stage=Stage.PERSIST,
            log_message=f"Đường dẫn output thoát khỏi OUTPUT_DIR: {target}",
        )
    return target


def _write_graph_json(parsed: ParsedFile) -> str:
    """Ghi file JSON theo kiểu 'ghi tạm rồi đổi tên'.

    `os.replace` là thao tác nguyên tử trên cùng một filesystem: hoặc file cũ
    còn nguyên, hoặc file mới đã đủ. Không bao giờ có trạng thái giữa chừng —
    tiến trình chết lúc đang ghi cũng không để lại file JSON cụt.
    """
    target = _resolve_output_path(parsed.filename)
    tmp = target.with_name(target.name + ".tmp")

    try:
        graph = merge_documents([parsed])
        target.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, target)
    except OSError as exc:
        _cleanup(tmp)
        raise CriticalError(
            ErrorCode.STORAGE_FAILURE,
            "Không lưu được kết quả xử lý. Vui lòng thử lại sau.",
            stage=Stage.PERSIST,
            log_message=f"Ghi '{target}' thất bại: {type(exc).__name__}: {exc}",
        ) from exc
    except Exception as exc:
        # Lỗi lạ khi serialize (kiểu dữ liệu không JSON hoá được...). Không đoán,
        # không đi tiếp — dọn file tạm rồi báo critical.
        _cleanup(tmp)
        raise CriticalError(
            ErrorCode.INTERNAL_ERROR,
            "Không lưu được kết quả xử lý.",
            stage=Stage.PERSIST,
            log_message=f"Lỗi ngoài dự kiến khi ghi '{target}': {type(exc).__name__}",
        ) from exc

    logger.info("Đã ghi %s", target.name)
    return target.name


def _cleanup(path: Path) -> None:
    """Xoá file tạm. Thất bại ở đây không được che lỗi gốc nên chỉ ghi log."""
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Không xoá được file tạm %s: %s", path, exc)


def _build_ingest_response(
    validated: Any, output_file: str, replaced: bool, request_id: str
) -> ApiResponse:
    """Sạch hoàn toàn -> success. Có cảnh báo hoặc có ghi đè -> warning."""
    parsed = validated.parsed
    details: dict[str, Any] = {
        "file": validated.filename,
        "root": parsed.root_id,
        "node_count": len(parsed.nodes),
        "edge_count": len(parsed.edges),
        "size_bytes": validated.size_bytes,
        "output_file": output_file,
        "warning_count": len(validated.warnings),
        "replaced_existing": replaced,
    }

    issues = list(validated.warnings)
    if replaced:
        issues.insert(
            0,
            Issue(
                severity="warning",
                code=ErrorCode.FILE_REPLACED.value,
                message=f"'{validated.filename}' đã tồn tại và vừa bị ghi đè bằng bản mới.",
                source=validated.filename,
            ),
        )

    if not issues:
        logger.info("Nạp thành công '%s' (không cảnh báo)", validated.filename)
        return schemas.success(
            f"Đã xử lý '{validated.filename}': {len(parsed.nodes)} node, "
            f"{len(parsed.edges)} quan hệ.",
            request_id=request_id,
            details=details,
        )

    logger.warning(
        "Nạp '%s' kèm %d cảnh báo: %s",
        validated.filename, len(issues), [i.code for i in issues],
    )
    return schemas.warning(
        f"Đã xử lý '{validated.filename}' nhưng có {len(issues)} cảnh báo cần xem lại.",
        request_id=request_id,
        issues=issues,
        details=details,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Liệt kê / tìm kiếm / xoá
# ─────────────────────────────────────────────────────────────────────────────


def list_catalogs(
    query: str | None, include_diagnostics: bool, request_id: str
) -> ApiResponse:
    items = store.list(query)
    total = len(store)

    if query and not items:
        message = f"Không tìm thấy file nào khớp '{query}'."
    elif query:
        message = f"Tìm thấy {len(items)}/{total} file khớp '{query}'."
    elif total:
        message = f"Có {total} file đã nạp."
    else:
        message = "Chưa có file nào được nạp."

    return schemas.success(
        message,
        request_id=request_id,
        details={
            "total": total,
            "returned": len(items),
            "query": query,
            "items": [i.summary_dict(include_diagnostics) for i in items],
        },
    )


def _suggest_filenames(wanted: str, limit: int = 5) -> list[str]:
    """Gợi ý tên gần đúng khi không tìm thấy file.

    Khớp chuỗi con thôi thì gõ sai một ký tự ('order-servic') là không gợi ý được
    gì — đúng lúc người dùng cần gợi ý nhất. Nên: ưu tiên khớp chuỗi con (người
    dùng gõ tắt), sau đó bù bằng khớp mờ của `difflib` (người dùng gõ sai).
    """
    names = [i.filename for i in store.list()]
    substring = [i.filename for i in store.list(wanted)]
    fuzzy = difflib.get_close_matches(wanted, names, n=limit, cutoff=0.6)

    seen: list[str] = []
    for name in [*substring, *fuzzy]:
        if name not in seen:
            seen.append(name)
    return seen[:limit]


def delete_catalog(filename: str, request_id: str) -> ApiResponse:
    """Xoá 1 catalog: xoá file JSON trước, xoá chỉ mục sau.

    Thứ tự này là cố ý. Nếu xoá chỉ mục trước rồi xoá file thất bại, ta còn lại
    một file JSON mồ côi trên đĩa mà không API nào nhìn thấy. Làm ngược lại:
    xoá file hỏng thì dừng luôn, chỉ mục còn nguyên, hệ thống vẫn nhất quán và
    người dùng thử lại được.
    """
    item = store.get(filename)
    if item is None:
        raise ValidationError(
            ErrorCode.CATALOG_NOT_FOUND,
            f"Không tìm thấy file '{filename}' trong hệ thống.",
            stage=Stage.STORE,
            details={"suggestions": _suggest_filenames(filename)},
        )

    if item.output_file:
        try:
            _resolve_output_path(filename).unlink(missing_ok=True)
        except OSError as exc:
            raise CriticalError(
                ErrorCode.STORAGE_FAILURE,
                "Không xoá được file kết quả. Chưa xoá gì cả, vui lòng thử lại.",
                stage=Stage.PERSIST,
                log_message=f"Xoá output của '{filename}' thất bại: {exc}",
            ) from exc

    store.delete(filename)
    logger.info("Đã xoá catalog '%s'", filename)

    return schemas.success(
        f"Đã xoá '{filename}'.",
        request_id=request_id,
        stage=Stage.DONE,
        details={"file": filename, "remaining": len(store)},
    )
