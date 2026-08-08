"""
validation.py — Pipeline validate input, 5 tầng, fail-fast.

    Layer 1  Basic input     có file? rỗng? quá lớn? đúng đuôi?
    Layer 2  Security        tên file độc, nhị phân đội lốt, YAML bomb, tag nguy hiểm
    Layer 3  File integrity   giải mã UTF-8, cú pháp YAML, key trùng
    Layer 4  Schema           đúng hình dạng? có đủ section bắt buộc? độ sâu?
    Layer 5  Data             business rules, ref, quan hệ, chu trình phụ thuộc

Mỗi tầng là một hàm độc lập, tự raise khi phát hiện lỗi. Tầng sau chỉ chạy khi
tầng trước đã sạch — thoả yêu cầu "một layer phát hiện critical thì dừng ngay".

── Một điểm tôi làm KHÁC thứ tự bạn đưa, và lý do ──────────────────────────────
Bạn xếp Security ở layer 5 (sau cùng). Đặt vậy thì hai loại tấn công quan trọng
nhất lọt lưới, vì cả hai đều nổ NGAY LÚC PARSE:

  - YAML bomb ("billion laughs"): file 1KB dùng anchor/alias lồng nhau, parse
    xong nở ra hàng GB và giết process. Kiểm tra sau khi parse là kiểm tra khi
    server đã chết.
  - Tag `!!python/object/apply`: dựng object Python tuỳ ý ngay trong lúc parse.

Nên security phải chia đôi: phần soi BYTES THÔ chạy TRƯỚC khi parse (đây là
layer 2), phần soi NỘI DUNG ĐÃ HIỂU chạy sau (nằm ở layer 4 — độ sâu, và layer 5
— dữ liệu). Nguyên tắc chung: không bao giờ đưa dữ liệu chưa soi vào một parser.

`yaml.SafeLoader` chặn được tag nguy hiểm, nhưng KHÔNG chặn anchor/alias bomb —
đó là YAML hợp lệ. Nó không thay thế được layer 2.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from fastapi import UploadFile

from app.core import config
from app.core.errors import (
    CriticalError,
    ErrorCode,
    SecurityError,
    Stage,
    ValidationError,
)
from app.core.logging import content_fingerprint
from app.models.schemas import Issue
from app.services.catalog_to_graph import (
    Diagnostics,
    FatalError,
    ParsedFile,
    assert_invariants,
    build_nx_graph,
    check_cycles,
    load_yaml,
    parse_document,
)

logger = logging.getLogger(__name__)

# Tên file bị Windows cấm — nếu lọt xuống, thao tác ghi đĩa sẽ hỏng theo cách khó hiểu.
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

_ANCHOR_RE = re.compile(r"(?:^|[\s\[\{,])&[A-Za-z0-9_-]+")
_ALIAS_RE = re.compile(r"(?:^|[\s\[\{,])\*[A-Za-z0-9_-]+")
_MERGE_KEY_RE = re.compile(r"(?m)^\s*<<\s*:")


@dataclass
class ValidatedUpload:
    """Kết quả của cả pipeline khi input đã sạch."""

    filename: str
    size_bytes: int
    fingerprint: str
    parsed: ParsedFile
    warnings: list[Issue] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Basic input validation
# ─────────────────────────────────────────────────────────────────────────────


async def read_upload_within_limit(file: UploadFile) -> bytes:
    """Đọc file theo từng chunk và CHẶN NGAY khi vượt ngưỡng.

    Không dùng `await file.read()` một phát: nó nạp trọn file vào RAM rồi mới
    đo được kích thước — tức là kiểm tra giới hạn sau khi thiệt hại đã xảy ra.
    Cũng không tin `Content-Length` do client khai.
    """
    buffer = bytearray()
    limit = config.MAX_UPLOAD_BYTES
    try:
        while chunk := await file.read(config.UPLOAD_CHUNK_BYTES):
            buffer.extend(chunk)
            if len(buffer) > limit:
                raise ValidationError(
                    ErrorCode.FILE_TOO_LARGE,
                    f"File vượt quá giới hạn {limit // 1024} KB. "
                    "catalog-info.yaml hợp lệ chỉ nặng vài KB.",
                    stage=Stage.L1_BASIC_INPUT,
                    details={"limit_bytes": limit},
                )
    except ValidationError:
        raise
    except Exception as exc:  # đọc hỏng giữa chừng: mạng đứt, temp file lỗi
        raise CriticalError(
            ErrorCode.INTERNAL_ERROR,
            "Không đọc được dữ liệu upload. Vui lòng thử lại.",
            stage=Stage.L1_BASIC_INPUT,
            log_message=f"Đọc UploadFile thất bại: {type(exc).__name__}",
        ) from exc
    return bytes(buffer)


def layer1_basic_input(filename: str | None, content: bytes, content_type: str | None) -> str:
    """Kiểm tra ở mức 'có phải một file dùng được không'. Trả về tên file đã strip.

    Kiểm tra an toàn TÊN FILE nằm ở đây chứ không ở layer 2, dù nó là kiểm tra
    bảo mật. Lý do: tên file là dữ liệu người dùng nguy hiểm nhất trong request
    (nó sẽ đi vào một đường dẫn ghi đĩa), và nếu để sau bước kiểm tra đuôi file
    thì `../../etc/passwd.txt` sẽ bị báo là "sai đuôi file" — người dùng thật vẫn
    bị chặn, nhưng ta mất tín hiệu là có người đang dò path traversal. Phân loại
    lỗi nằm ở KIỂU EXCEPTION (`SecurityError`), không ở số hiệu tầng.
    """
    if not filename or not filename.strip():
        raise ValidationError(
            ErrorCode.NO_FILE,
            "Chưa chọn file để tải lên.",
            stage=Stage.L1_BASIC_INPUT,
        )

    name = _check_filename(filename.strip())

    if len(name) > config.MAX_FILENAME_LENGTH:
        raise ValidationError(
            ErrorCode.FILENAME_TOO_LONG,
            f"Tên file quá dài (tối đa {config.MAX_FILENAME_LENGTH} ký tự).",
            stage=Stage.L1_BASIC_INPUT,
        )

    if not name.lower().endswith(config.ALLOWED_EXTENSIONS):
        raise ValidationError(
            ErrorCode.INVALID_FILE_TYPE,
            f"Chỉ nhận file {' hoặc '.join(config.ALLOWED_EXTENSIONS)}.",
            stage=Stage.L1_BASIC_INPUT,
            details={"allowed_extensions": list(config.ALLOWED_EXTENSIONS)},
        )

    if not content:
        raise ValidationError(
            ErrorCode.EMPTY_FILE,
            "File rỗng, không có nội dung để xử lý.",
            stage=Stage.L1_BASIC_INPUT,
        )

    # Content-Type chỉ ghi log, KHÔNG chặn — xem chú thích ở config.EXPECTED_CONTENT_TYPES.
    if content_type and content_type.lower().split(";")[0] not in config.EXPECTED_CONTENT_TYPES:
        logger.info(
            "Content-Type lạ '%s' cho file '%s' — bỏ qua, sẽ soi nội dung thật ở layer 2",
            content_type, name,
        )

    return name


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Security (chạy trên BYTES THÔ, trước khi parse)
# ─────────────────────────────────────────────────────────────────────────────


def layer2_security(filename: str, content: bytes) -> None:
    """Soi BYTES THÔ trước khi đưa cho parser. Tên file đã được layer 1 duyệt."""
    _check_not_binary(filename, content)
    _check_yaml_bomb(filename, content)


def _check_filename(filename: str) -> str:
    """Chặn path traversal. Gọi từ layer 1 — xem chú thích ở đó.

    Nguyên tắc: TỪ CHỐI chứ không âm thầm sửa. Nếu tự ý cắt `../../etc/passwd.yaml`
    thành `passwd.yaml` thì người dùng tưởng đã lưu tên này, hệ thống lưu tên kia
    — và ta mất luôn tín hiệu là có người đang dò đường.
    """
    lowered = filename.lower()

    reasons: list[str] = []
    if "/" in filename or "\\" in filename:
        reasons.append("chứa dấu phân cách thư mục")
    if ".." in filename:
        reasons.append("chứa '..'")
    if "\x00" in filename:
        reasons.append("chứa NUL byte")
    if ":" in filename:  # 'C:' hoặc NTFS alternate data stream 'file.yaml:evil'
        reasons.append("chứa dấu ':'")
    if filename.startswith((".", "-", "~")):
        reasons.append("bắt đầu bằng ký tự đặc biệt")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in filename):
        reasons.append("chứa control character")
    if lowered.split(".")[0] in _WINDOWS_RESERVED:
        reasons.append("trùng tên thiết bị hệ thống")

    if reasons:
        raise SecurityError(
            ErrorCode.UNSAFE_FILENAME,
            "Tên file không hợp lệ. Chỉ dùng chữ, số, dấu '-', '_', '.' "
            "và không kèm đường dẫn thư mục.",
            stage=Stage.L1_BASIC_INPUT,
            log_message=f"Từ chối tên file {filename!r}: {', '.join(reasons)}",
        )
    return filename


def _check_not_binary(filename: str, content: bytes) -> None:
    """Bắt 'file type spoofing': đổi đuôi ảnh/zip thành .yaml.

    Soi magic bytes và NUL byte — hai thứ không bao giờ có trong file text hợp lệ.
    Đây là kiểm tra dựa trên NỘI DUNG THẬT, khác hẳn việc tin vào phần mở rộng
    hay Content-Type do client khai.
    """
    head = content[:64]
    for magic, label in config.BINARY_MAGIC_SIGNATURES.items():
        if head.startswith(magic):
            raise SecurityError(
                ErrorCode.CONTENT_TYPE_MISMATCH,
                "Nội dung file không phải văn bản YAML dù phần mở rộng là .yaml/.yml.",
                stage=Stage.L2_SECURITY,
                details={"detected_format": label},
                log_message=f"'{filename}' mang đuôi YAML nhưng magic bytes là {label}",
            )

    if b"\x00" in content:
        raise SecurityError(
            ErrorCode.BINARY_CONTENT,
            "File chứa dữ liệu nhị phân, không phải văn bản YAML.",
            stage=Stage.L2_SECURITY,
            log_message=f"'{filename}' chứa NUL byte",
        )


def _check_yaml_bomb(filename: str, content: bytes) -> None:
    """Chặn tấn công làm cạn tài nguyên lúc parse.

    Đếm trên text thô bằng regex — cố tình thô sơ, vì mục đích là chặn TRƯỚC khi
    parser chạm vào dữ liệu. Ngưỡng đặt cao hơn nhiều lần file thật nên không
    có nguy cơ chặn nhầm.
    """
    # errors="replace": ở đây chỉ cần đếm ký tự, chuyện encoding để layer 3 phán.
    text = content.decode("utf-8", errors="replace")

    for tag in config.FORBIDDEN_YAML_TAGS:
        if tag in text:
            raise SecurityError(
                ErrorCode.UNSAFE_YAML_TAG,
                "File chứa cấu trúc YAML không được phép.",
                stage=Stage.L2_SECURITY,
                log_message=f"'{filename}' chứa tag nguy hiểm {tag!r}",
            )

    lines = text.splitlines()
    if len(lines) > config.MAX_YAML_LINES:
        raise SecurityError(
            ErrorCode.YAML_TOO_MANY_LINES,
            f"File quá dài (tối đa {config.MAX_YAML_LINES} dòng).",
            stage=Stage.L2_SECURITY,
            details={"lines": len(lines)},
        )

    longest = max((len(ln) for ln in lines), default=0)
    if longest > config.MAX_YAML_LINE_LENGTH:
        raise SecurityError(
            ErrorCode.YAML_TOO_MANY_LINES,
            f"File có dòng quá dài (tối đa {config.MAX_YAML_LINE_LENGTH} ký tự).",
            stage=Stage.L2_SECURITY,
            details={"longest_line": longest},
        )

    anchors = len(_ANCHOR_RE.findall(text))
    aliases = len(_ALIAS_RE.findall(text)) + len(_MERGE_KEY_RE.findall(text))
    if anchors > config.MAX_YAML_ANCHORS or aliases > config.MAX_YAML_ALIASES:
        raise SecurityError(
            ErrorCode.YAML_EXPANSION_BOMB,
            "File dùng quá nhiều anchor/alias YAML và bị từ chối vì lý do an toàn.",
            stage=Stage.L2_SECURITY,
            details={"anchors": anchors, "aliases": aliases},
            log_message=(
                f"Nghi ngờ YAML expansion bomb ở '{filename}': "
                f"{anchors} anchor, {aliases} alias"
            ),
        )

    # Thụt đầu dòng quá sâu -> đệ quy sâu trong parser. Ước lượng 2 space = 1 cấp.
    max_indent = max((len(ln) - len(ln.lstrip(" ")) for ln in lines), default=0)
    if max_indent > config.MAX_YAML_DEPTH * 2:
        raise SecurityError(
            ErrorCode.YAML_TOO_DEEP,
            f"Cấu trúc file lồng nhau quá sâu (tối đa {config.MAX_YAML_DEPTH} cấp).",
            stage=Stage.L2_SECURITY,
            details={"max_indent_spaces": max_indent},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — File integrity
# ─────────────────────────────────────────────────────────────────────────────


def layer3_file_integrity(filename: str, content: bytes) -> dict[str, Any]:
    """File có ĐỌC ĐƯỢC không: giải mã UTF-8, cú pháp YAML, key trùng."""
    try:
        text = content.decode("utf-8-sig")  # -sig để nuốt luôn BOM của Notepad
    except UnicodeDecodeError as exc:
        raise ValidationError(
            ErrorCode.INVALID_ENCODING,
            "File phải được lưu ở dạng UTF-8. Hãy lưu lại với encoding UTF-8 rồi tải lên.",
            stage=Stage.L3_FILE_INTEGRITY,
            details={"position": exc.start},
        ) from exc

    try:
        document = load_yaml(text)
    except FatalError as exc:
        # load_yaml gói cả lỗi cú pháp lẫn "root không phải mapping" vào FatalError.
        code = (
            ErrorCode.DUPLICATE_KEY
            if "duplicate key" in exc.issue.message
            else ErrorCode.YAML_SYNTAX
            if exc.issue.code == "YAML_SYNTAX"
            else ErrorCode.INVALID_STRUCTURE
        )
        raise ValidationError(
            code,
            _readable_yaml_error(exc.issue.message),
            stage=Stage.L3_FILE_INTEGRITY,
            issues=[
                Issue(
                    severity="error",
                    code=exc.issue.code,
                    message=exc.issue.message,
                    location=exc.issue.yaml_path,
                    source=filename,
                )
            ],
        ) from exc

    return document


def _readable_yaml_error(raw: str) -> str:
    """PyYAML in ra nhiều dòng có toạ độ; giữ dòng đầu cho gọn màn hình."""
    first = raw.strip().splitlines()[0] if raw.strip() else "không rõ"
    return f"File YAML sai cú pháp: {first}"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Schema (hình dạng tài liệu)
# ─────────────────────────────────────────────────────────────────────────────

_REQUIRED_SECTIONS = ("specVersion", "metadata", "spec")


def layer4_schema(filename: str, document: dict[str, Any]) -> None:
    """Kiểm tra HÌNH DẠNG, chưa xét giá trị.

    Tách khỏi layer 5 vì hai lý do khác nhau về bản chất: thiếu hẳn section `spec`
    thì không có gì để mà kiểm tra giá trị — báo "thiếu spec" một câu rõ ràng
    hữu ích hơn là 20 lỗi "field bắt buộc" dội ra từ tầng dưới.
    """
    missing = [s for s in _REQUIRED_SECTIONS if s not in document]
    if missing:
        raise ValidationError(
            ErrorCode.MISSING_REQUIRED_SECTION,
            f"File thiếu section bắt buộc: {', '.join(missing)}.",
            stage=Stage.L4_SCHEMA,
            details={"missing_sections": missing},
            issues=[
                Issue(
                    severity="error",
                    code="REQUIRED",
                    message=f"Thiếu section '{s}' ở cấp cao nhất",
                    location=s,
                    source=filename,
                )
                for s in missing
            ],
        )

    wrong_type = [s for s in ("metadata", "spec") if not isinstance(document[s], dict)]
    if wrong_type:
        raise ValidationError(
            ErrorCode.INVALID_STRUCTURE,
            f"Section {', '.join(wrong_type)} phải là một mapping (khối key: value).",
            stage=Stage.L4_SCHEMA,
            issues=[
                Issue(
                    severity="error",
                    code="TYPE_MISMATCH",
                    message=f"'{s}' phải là mapping, đang là "
                    f"{type(document[s]).__name__}",
                    location=s,
                    source=filename,
                )
                for s in wrong_type
            ],
        )

    depth = _document_depth(document)
    if depth > config.MAX_YAML_DEPTH:
        raise ValidationError(
            ErrorCode.INVALID_STRUCTURE,
            f"Cấu trúc lồng nhau quá sâu ({depth} cấp, tối đa {config.MAX_YAML_DEPTH}).",
            stage=Stage.L4_SCHEMA,
        )


def _document_depth(value: Any, current: int = 0, limit: int = 64) -> int:
    """Đo độ sâu thật sau khi parse. `limit` chặn chính hàm này khỏi đệ quy vô hạn
    khi gặp cấu trúc tự tham chiếu do alias tạo ra."""
    if current >= limit:
        return current
    if isinstance(value, dict):
        return max((_document_depth(v, current + 1, limit) for v in value.values()),
                   default=current)
    if isinstance(value, list):
        return max((_document_depth(v, current + 1, limit) for v in value), default=current)
    return current


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — Data / business rules
# ─────────────────────────────────────────────────────────────────────────────


def layer5_data(filename: str, document: dict[str, Any]) -> tuple[ParsedFile, list[Issue]]:
    """Chạy toàn bộ luật nghiệp vụ. Trả về (ParsedFile, danh sách warning).

    Khác 4 tầng trên ở một điểm quan trọng: tầng này GOM HẾT lỗi rồi mới báo,
    không dừng ở lỗi đầu tiên. Người dùng sửa YAML cần thấy cả 12 lỗi trong một
    lần, không phải upload lại 12 lần.
    """
    d = Diagnostics()
    try:
        nodes, edges, root_id = parse_document(document, filename, d)
    except FatalError as exc:
        raise ValidationError(
            ErrorCode.INVALID_STRUCTURE,
            exc.issue.message,
            stage=Stage.L5_DATA,
            issues=[_to_issue(exc.issue, "error", filename)],
        ) from exc

    if nodes and not d.errors:
        check_cycles(build_nx_graph(nodes, edges), d)
        try:
            assert_invariants(nodes, edges)
        except AssertionError as exc:
            # Bất biến vỡ = bug ở phía sinh dữ liệu, KHÔNG phải lỗi của input.
            # Không được nuốt: đồ thị đang ở trạng thái không nhất quán.
            raise CriticalError(
                ErrorCode.INCONSISTENT_STATE,
                "Hệ thống tạo ra dữ liệu không nhất quán và đã dừng để tránh lưu sai.",
                stage=Stage.L5_DATA,
                log_message=f"Vỡ bất biến khi xử lý '{filename}': {exc}",
            ) from exc

    if d.errors:
        raise ValidationError(
            ErrorCode.SCHEMA_VALIDATION_FAILED,
            f"File có {len(d.errors)} lỗi cần sửa trước khi sử dụng được.",
            stage=Stage.L5_DATA,
            details={"error_count": len(d.errors), "warning_count": len(d.warnings)},
            issues=(
                [_to_issue(i, "error", filename) for i in d.errors]
                + [_to_issue(i, "warning", filename) for i in d.warnings]
            ),
        )

    warnings = [_to_issue(i, "warning", filename) for i in d.warnings]
    return ParsedFile(filename, nodes, edges, root_id, d), warnings


def _to_issue(issue: Any, severity: str, filename: str) -> Issue:
    """Đổi `catalog_to_graph.Issue` (nội bộ) thành `schemas.Issue` (contract).

    Giữ hai kiểu riêng biệt là cố ý: đổi cấu trúc nội bộ không được phép âm thầm
    làm vỡ contract của frontend.
    """
    return Issue(
        severity=severity,
        code=issue.code,
        message=issue.message,
        location=issue.yaml_path,
        subject=issue.subject,
        source=issue.source or filename,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────


def run_validation_pipeline(
    filename: str | None, content: bytes, content_type: str | None = None
) -> ValidatedUpload:
    """Chạy lần lượt 5 tầng. Tầng nào raise thì các tầng sau không chạy.

    Hàm này KHÔNG bắt exception. Nó để lỗi bay lên cho tầng gọi (service) quyết
    định — đúng vai trò: validator phán đúng/sai, không phán xử lý thế nào.
    """
    name = layer1_basic_input(filename, content, content_type)
    layer2_security(name, content)
    document = layer3_file_integrity(name, content)
    layer4_schema(name, document)
    parsed, warnings = layer5_data(name, document)

    return ValidatedUpload(
        filename=name,
        size_bytes=len(content),
        fingerprint=content_fingerprint(content),
        parsed=parsed,
        warnings=warnings,
    )
