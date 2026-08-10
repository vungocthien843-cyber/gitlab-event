"""
errors.py — Cây exception + bảng mã lỗi dùng chung cho toàn backend.

Ba nhóm lỗi, phân loại theo CÁCH XỬ LÝ chứ không theo nguyên nhân kỹ thuật:

    ValidationError  Lỗi của INPUT. Người dùng sửa file rồi upload lại là xong.
                     -> HTTP 422, severity "validation", can_continue = False.
                     -> Log WARNING, KHÔNG log stack trace (không phải bug của ta).

    SecurityError    Input có dấu hiệu nguy hiểm (spoof, path traversal, YAML bomb).
                     -> HTTP 400, severity "critical", can_continue = False.
                     -> Message trả client cố tình chung chung; chi tiết chỉ nằm
                        trong log — không dạy kẻ tấn công cách né bộ lọc.

    CriticalError    Hệ thống không đảm bảo được trạng thái an toàn để đi tiếp
                     (không ghi được đĩa, config thiếu, invariant vỡ, exception lạ).
                     -> HTTP 500, severity "critical". LUÔN log stack trace.

Vì sao dùng custom exception thay vì exception có sẵn của Python:
  - Cần mang METADATA mà built-in không có: code, stage, can_continue, next_action,
    danh sách issues -> đủ để dựng thẳng response contract, không cần map lại.
  - `ValueError` từ int() và `ValueError` từ business rule cần 2 cách xử lý khác
    nhau; phân loại theo built-in type là phân loại sai trục.
  - Built-in VẪN được dùng ở tầng thấp (OSError, UnicodeDecodeError, yaml.YAMLError),
    rồi bọc lại khi đi lên tầng service: `raise ValidationError(...) from exc`.
    `from exc` giữ nguyên chuỗi nguyên nhân trong log.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    """Mức độ nghiêm trọng — frontend dựa vào đây để chọn màu/hành vi UI."""

    NONE = "none"              # không có vấn đề gì
    LOW = "low"                # warning, đi tiếp được
    VALIDATION = "validation"  # input sai, người dùng tự sửa được
    CRITICAL = "critical"      # dừng, không tự sửa được ở phía người dùng


class Status(StrEnum):
    """Kết quả tổng của request. Suy ra được từ Severity — xem `Status.of()`."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    @classmethod
    def of(cls, severity: Severity) -> Status:
        """Nguồn sự thật duy nhất cho cặp (status, severity).

        Contract của bạn có cả 2 field, mà `status` luôn suy được từ `severity`.
        Không xoá `status` (frontend đọc nó tiện hơn), nhưng KHÔNG BAO GIỜ set tay
        — đi qua hàm này để hai field không thể lệch nhau.
        """
        if severity is Severity.NONE:
            return cls.SUCCESS
        if severity is Severity.LOW:
            return cls.WARNING
        return cls.ERROR


class NextAction(StrEnum):
    """Người dùng cần làm gì tiếp theo. Frontend map thẳng sang nút bấm."""

    PROCEED = "proceed"                    # xong, đi tiếp
    REVIEW_WARNINGS = "review_warnings"    # xem cảnh báo rồi tự quyết định
    FIX_AND_REUPLOAD = "fix_and_reupload"  # sửa file, upload lại
    HUMAN_REVIEW = "human_review"          # vượt thẩm quyền tự động, cần người duyệt
    CONTACT_SUPPORT = "contact_support"    # lỗi phía hệ thống, người dùng bó tay


class Stage(StrEnum):
    """Chặng xử lý — trả về cho frontend và ghi vào log để biết chết ở đâu."""

    RECEIVE = "receive"
    L1_BASIC_INPUT = "layer1_basic_input"
    L2_SECURITY = "layer2_security"
    L3_FILE_INTEGRITY = "layer3_file_integrity"
    L4_SCHEMA = "layer4_schema"
    L5_DATA = "layer5_data"
    PERSIST = "persist"
    STORE = "store"
    DONE = "done"


class ErrorCode(StrEnum):
    """Mã lỗi ổn định. Frontend switch trên MÃ, không parse `message`.

    Thêm mã mới = thêm dòng ở đây. Không đổi/xoá mã cũ khi frontend còn dùng.
    """

    # ── Layer 1: basic input ─────────────────────────────────────────────────
    NO_FILE = "NO_FILE"
    EMPTY_FILE = "EMPTY_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILENAME_TOO_LONG = "FILENAME_TOO_LONG"
    UNSAFE_FILENAME = "UNSAFE_FILENAME"

    # ── Layer 2: security ────────────────────────────────────────────────────
    BINARY_CONTENT = "BINARY_CONTENT"
    CONTENT_TYPE_MISMATCH = "CONTENT_TYPE_MISMATCH"
    UNSAFE_YAML_TAG = "UNSAFE_YAML_TAG"
    YAML_EXPANSION_BOMB = "YAML_EXPANSION_BOMB"
    YAML_TOO_DEEP = "YAML_TOO_DEEP"
    YAML_TOO_MANY_LINES = "YAML_TOO_MANY_LINES"

    # ── Layer 3: file integrity ──────────────────────────────────────────────
    INVALID_ENCODING = "INVALID_ENCODING"
    YAML_SYNTAX = "YAML_SYNTAX"
    DUPLICATE_KEY = "DUPLICATE_KEY"

    # ── Layer 4: schema ──────────────────────────────────────────────────────
    INVALID_STRUCTURE = "INVALID_STRUCTURE"
    MISSING_REQUIRED_SECTION = "MISSING_REQUIRED_SECTION"

    # ── Layer 5: data / business rules ───────────────────────────────────────
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"

    # ── Warning (không chặn) ─────────────────────────────────────────────────
    HAS_WARNINGS = "HAS_WARNINGS"
    FILE_REPLACED = "FILE_REPLACED"

    # ── Tra cứu / xoá ────────────────────────────────────────────────────────
    CATALOG_NOT_FOUND = "CATALOG_NOT_FOUND"

    # ── GitHub webhook ───────────────────────────────────────────────────────
    # Chữ ký HMAC sai/thiếu -> SecurityError (400). Không phải "input sai định
    # dạng" mà là "request này không chứng minh được nó đến từ GitHub".
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    # Server chưa cấu hình WEBHOOK_SECRET -> CriticalError (500). Lỗi của ta,
    # không phải của người gửi; tuyệt đối không được bỏ qua bước xác thực.
    WEBHOOK_NOT_CONFIGURED = "WEBHOOK_NOT_CONFIGURED"
    # Không tải được nội dung file từ GitHub. Dùng làm `Issue.code` trong response
    # chứ không raise: một file hỏng không được làm hỏng cả lần push.
    GITHUB_FETCH_FAILED = "GITHUB_FETCH_FAILED"

    # ── Critical ─────────────────────────────────────────────────────────────
    STORAGE_FAILURE = "STORAGE_FAILURE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INCONSISTENT_STATE = "INCONSISTENT_STATE"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class AppError(Exception):
    """Gốc của mọi lỗi có contract. Mang đủ dữ liệu để dựng response.

    Không raise trực tiếp class này — dùng một trong các lớp con bên dưới.
    """

    severity: Severity = Severity.CRITICAL
    http_status: int = 500
    can_continue: bool = False
    next_action: NextAction = NextAction.CONTACT_SUPPORT
    log_level: int = logging.CRITICAL
    # True = ghi kèm stack trace. Lỗi do input người dùng thì stack trace vô nghĩa,
    # chỉ làm ngập log và che mất lỗi thật.
    log_traceback: bool = True

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        stage: Stage = Stage.RECEIVE,
        details: dict[str, Any] | None = None,
        issues: list[Any] | None = None,
        log_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage
        self.details = details or {}
        self.issues = issues or []
        # Thông tin cho log — được phép chi tiết hơn `message` trả cho client.
        self.log_message = log_message or message

    @property
    def status(self) -> Status:
        return Status.of(self.severity)


class ValidationError(AppError):
    """Input sai. Không phải bug của hệ thống, không cần crash gì cả.

    Người dùng sửa file rồi upload lại. Server vẫn khoẻ mạnh, request khác
    vẫn chạy bình thường.
    """

    severity = Severity.VALIDATION
    http_status = 422
    can_continue = False
    next_action = NextAction.FIX_AND_REUPLOAD
    log_level = logging.WARNING
    log_traceback = False


class SecurityError(AppError):
    """Input có dấu hiệu tấn công hoặc vượt giới hạn an toàn.

    HTTP 400 chứ không 422: đây không phải "file sai định dạng" mà là
    "request này bị từ chối". `message` cố tình mơ hồ — chi tiết ở `log_message`.
    """

    severity = Severity.CRITICAL
    http_status = 400
    can_continue = False
    next_action = NextAction.FIX_AND_REUPLOAD
    log_level = logging.ERROR
    log_traceback = False


class CriticalError(AppError):
    """Hệ thống không đảm bảo được là đi tiếp thì an toàn.

    Đây là nhánh mặc định cho MỌI thứ không rõ ràng: exception lạ, invariant vỡ,
    đĩa không ghi được. Nguyên tắc "Unknown error = Fail safely".
    """

    severity = Severity.CRITICAL
    http_status = 500
    can_continue = False
    next_action = NextAction.CONTACT_SUPPORT
    log_level = logging.CRITICAL
    log_traceback = True


class HumanReviewRequiredError(AppError):
    """Hệ thống ĐỌC ĐƯỢC input nhưng không đủ thẩm quyền tự quyết.

    Khác CriticalError ở chỗ: không có gì hỏng cả, chỉ là bài toán cần con người.
    Ví dụ trong domain này: 2 file cùng nhận là chủ sở hữu một node
    (AMBIGUOUS_OWNER / DUPLICATE_DECLARATION) — chọn bừa file nào thắng là
    âm thầm làm hỏng catalog của người khác.

    HTTP 409 Conflict: trạng thái hiện tại của hệ thống mâu thuẫn với request.
    """

    severity = Severity.CRITICAL
    http_status = 409
    can_continue = False
    next_action = NextAction.HUMAN_REVIEW
    log_level = logging.ERROR
    log_traceback = False
