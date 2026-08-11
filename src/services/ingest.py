"""
ingest.py — Điều phối luồng nạp một catalog, sau khi input đã sạch.

    validate (5 tầng)  ->  kiểm tra xung đột xuyên file  ->  lưu DB  ->  cập nhật cache
                                                                     ->  dá»±ng response

Đây là tầng DUY NHẤT biết thứ tự các bước. Controller không biết, validator
không biết. Muốn chèn thêm một bước (gọi LLM, bắn event) thì thêm đúng ở đây,
và nó tự nằm trong đúng nhánh xử lý lỗi.

Vì sao KHÔNG bọc cả luồng trong một try/except khổng lồ: một `except Exception`
duy nhất ôm cả validate lẫn ghi DB thì không còn phân biệt được "người dùng gửi
file sai" (422, tự sửa được) với "database không tới được" (500, gọi support).
Mỗi bước bắt đúng loại lỗi mình hiểu, phần còn lại để rơi lên handler toàn cục
thành critical.
"""

from __future__ import annotations

import difflib
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from src.core.errors import (
    CriticalError,
    ErrorCode,
    HumanReviewRequiredError,
    Stage,
    ValidationError,
)
from src.models import schemas
from src.models.schemas import ApiResponse, Issue
from src.repositories import catalog_repository
from src.services.catalog_merge import merge_documents
from src.services.catalog_to_graph import ParsedFile
from src.core.store import StoredCatalog, output_name, store
from src.services.validation import run_validation_pipeline

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
    force: bool = False,
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
    if not force:
        _check_cross_file_conflicts(parsed, validated.filename)

    # ── Bước 3: lưu JSON vào database ────────────────────────────────────────
    record_id, replaced = _save_graph_document(parsed)
    output_file = output_name(parsed.filename)

    # ── Bước 4: cập nhật cache ───────────────────────────────────────────────
    # Sau DB, không phải trước: DB hỏng thì cache phải giữ nguyên trạng thái cũ,
    # nếu không hệ thống sẽ báo "đã nạp" một file chưa hề được lưu ở đâu cả.
    store.put(
        StoredCatalog(
            parsed=parsed,
            size_bytes=validated.size_bytes,
            fingerprint=validated.fingerprint,
            output_file=output_file,
            record_id=record_id,
        )
    )

    # ── Bước 5: dựng response ────────────────────────────────────────────────
    return _build_ingest_response(validated, output_file, record_id, replaced, request_id)


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


def _build_graph_document(parsed: ParsedFile) -> dict[str, Any]:
    """Dựng đúng nội dung JSON sẽ nằm trong cột `content`.

    Giống hệt thứ trước đây ghi ra `output_json/*.json`, cộng thêm `generatedAt`
    — trường mà `build_document` của CLI vẫn sinh ra cho file JSON. Nó không phải
    metadata gắn thêm cho database: đó là một phần của định dạng tài liệu, và
    nhờ nó mà lúc nạp lại từ DB vẫn biết được catalog này nạp lúc nào.
    """
    document = merge_documents([parsed])
    document["generatedAt"] = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    return document


def _save_graph_document(parsed: ParsedFile) -> tuple[int, bool]:
    """Sinh graph JSON và lưu vào bảng `input_json`. Trả `(id, đã_ghi_đè)`.

    Không còn file tạm và `os.replace` như bản ghi đĩa: một câu UPDATE/INSERT của
    Postgres đã là nguyên tử sẵn, hoặc dòng cũ còn nguyên hoặc dòng mới đã đủ.
    Không bao giờ có tài liệu JSON cụt trong bảng.
    """
    try:
        document = _build_graph_document(parsed)
    except OSError as exc:
        # Hiếm, nhưng `merge_documents` có thể chạm tài nguyên hệ thống. Giữ
        # nhánh này để lỗi hạ tầng không bị gán nhầm thành lỗi logic.
        raise CriticalError(
            ErrorCode.STORAGE_FAILURE,
            "Không lưu được kết quả xử lý. Vui lòng thử lại sau.",
            stage=Stage.PERSIST,
            log_message=f"Dựng tài liệu cho '{parsed.filename}' thất bại: "
            f"{type(exc).__name__}",
        ) from exc
    except Exception as exc:
        # Lỗi lạ khi merge/serialize. Không đoán, không đi tiếp.
        raise CriticalError(
            ErrorCode.INTERNAL_ERROR,
            "Không lưu được kết quả xử lý.",
            stage=Stage.PERSIST,
            log_message=f"Lỗi ngoài dự kiến khi dựng JSON cho "
            f"'{parsed.filename}': {type(exc).__name__}",
        ) from exc

    # `save` tự bọc lỗi SQLAlchemy thành CriticalError/STORAGE_FAILURE.
    record_id, replaced = catalog_repository.save(document)

    logger.info(
        "Đã lưu '%s' vào input_json: id=%d, ghi_đè=%s",
        parsed.filename, record_id, replaced,
    )
    return record_id, replaced


def _build_ingest_response(
    validated: Any,
    output_file: str,
    record_id: int,
    replaced: bool,
    request_id: str,
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
        "record_id": record_id,
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
    """Xoá 1 catalog: xoá dòng trong DB trước, xoá cache sau.

    Thứ tự này là cố ý. Nếu xoá cache trước rồi xoá DB thất bại, ta còn lại một
    dòng mồ côi trong bảng mà không API nào nhìn thấy — cho tới lần restart sau,
    lúc nó bất ngờ sống lại. Làm ngược lại: DB xoá hỏng thì dừng luôn, cache còn
    nguyên, hệ thống vẫn nhất quán và người dùng thử lại được.
    """
    item = store.get(filename)
    if item is None:
        raise ValidationError(
            ErrorCode.CATALOG_NOT_FOUND,
            f"Không tìm thấy file '{filename}' trong hệ thống.",
            stage=Stage.STORE,
            details={"suggestions": _suggest_filenames(filename)},
        )

    # Lỗi SQLAlchemy đã được repository bọc thành STORAGE_FAILURE, và nó bay lên
    # trước khi cache bị đụng tới — đúng thứ tự an toàn nói ở trên.
    catalog_repository.delete(filename)

    store.delete(filename)
    logger.info("Đã xoá catalog '%s'", filename)

    return schemas.success(
        f"Đã xoá '{filename}'.",
        request_id=request_id,
        stage=Stage.DONE,
        details={"file": filename, "remaining": len(store)},
    )

