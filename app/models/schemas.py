"""
schemas.py — Response contract giữa backend và frontend.

MỘT hình dạng response duy nhất cho mọi endpoint, mọi kết quả (thành công,
cảnh báo, lỗi input, lỗi hệ thống). Frontend viết một hàm xử lý dùng chung,
không phải đoán mỗi endpoint trả kiểu gì.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import ErrorCode, NextAction, Severity, Stage, Status


class Issue(BaseModel):
    """Một vấn đề cụ thể trong file. Đây là thứ frontend render thành danh sách
    lỗi có thể bấm vào để nhảy tới đúng dòng YAML."""

    severity: str = Field(description="'error' (chặn) hoặc 'warning' (không chặn)")
    code: str = Field(description="Mã ổn định, vd 'REQUIRED', 'INVALID_REF'")
    message: str = Field(description="Mô tả cho người đọc")
    location: str | None = Field(
        default=None,
        description="Đường dẫn trong YAML, vd 'spec.owners.members[0].role'",
    )
    subject: str | None = Field(
        default=None, description="Node liên quan, vd 'api:order/order-service'"
    )
    source: str | None = Field(default=None, description="File phát sinh vấn đề")


class ApiResponse(BaseModel):
    """Response contract dùng chung.

    | field       | ý nghĩa                                                      |
    |-------------|--------------------------------------------------------------|
    | status      | success / warning / error — suy từ `severity`, không set tay  |
    | severity    | none / low / validation / critical — mức nghiêm trọng         |
    | code        | mã lỗi ổn định; null khi thành công. Frontend switch trên đây |
    | message     | câu tiếng Việt hiển thị thẳng cho người dùng                  |
    | can_continue| frontend có được phép cho đi bước tiếp theo không             |
    | next_action | người dùng cần LÀM GÌ tiếp theo -> map thẳng ra nút bấm       |
    | stage       | chết ở chặng nào — để hiện tiến độ và để hỗ trợ tra log       |
    | request_id  | nối response với log phía server                              |
    | issues      | danh sách vấn đề chi tiết                                     |
    | details     | dữ liệu riêng của từng endpoint (số node, danh sách file...)  |

    Hai bổ sung so với contract ban đầu bạn đưa, và lý do:

    - `next_action`: yêu cầu số 4 của bạn có "người dùng cần làm gì tiếp theo"
      nhưng contract lại thiếu field cho nó. `can_continue=false` mới chỉ nói
      "dừng", chưa nói "sửa file rồi thử lại" hay "gọi support". Không có field
      này, frontend buộc phải suy đoán từ `code` — tức là nhét business logic
      vào chỗ sai.

    - `issues`: nhét danh sách lỗi vào `details` (dict tự do) thì frontend phải
      đoán key và không có type. Đây là payload chính của một API validate,
      xứng đáng có chỗ riêng, có schema.
    """

    status: Status
    severity: Severity
    code: str | None = None
    message: str
    can_continue: bool
    next_action: NextAction
    stage: Stage
    request_id: str
    issues: list[Issue] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class CatalogSummary(BaseModel):
    """Tóm tắt 1 catalog đã nạp — phần tử của `details.items` ở GET /catalogs.

    Dựng để frontend render bảng mà không cần gọi thêm API nào: đã có sẵn tình
    trạng, số liệu đồ thị, thời điểm nạp và đường dẫn file JSON sinh ra.
    """

    file: str
    root: str | None = Field(description="Node gốc, vd 'component:order/order-service'")
    state: str = Field(description="'valid' hoặc 'valid_with_warnings'")
    error_count: int
    warning_count: int
    node_count: int
    edge_count: int
    size_bytes: int
    uploaded_at: datetime
    output_file: str | None = Field(description="Tên file JSON đã sinh trong output_json/")
    diagnostics: dict[str, Any] | None = Field(
        default=None, description="Chi tiết đầy đủ; chỉ có khi ?include=diagnostics"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Response builders — cách DUY NHẤT được phép dựng ApiResponse.
# Không new ApiResponse(...) rải rác trong service: `status` và `severity` phải
# luôn khớp nhau, chỉ ép được điều đó nếu mọi lối đi chụm về đây.
# ─────────────────────────────────────────────────────────────────────────────


def success(
    message: str,
    *,
    request_id: str,
    stage: Stage = Stage.DONE,
    details: dict[str, Any] | None = None,
) -> ApiResponse:
    return ApiResponse(
        status=Status.of(Severity.NONE),
        severity=Severity.NONE,
        code=None,
        message=message,
        can_continue=True,
        next_action=NextAction.PROCEED,
        stage=stage,
        request_id=request_id,
        issues=[],
        details=details or {},
    )


def warning(
    message: str,
    *,
    request_id: str,
    code: ErrorCode = ErrorCode.HAS_WARNINGS,
    issues: list[Issue] | None = None,
    stage: Stage = Stage.DONE,
    details: dict[str, Any] | None = None,
) -> ApiResponse:
    """can_continue = True: dữ liệu đã đủ điều kiện tối thiểu, người dùng xem
    cảnh báo rồi tự quyết định."""
    return ApiResponse(
        status=Status.of(Severity.LOW),
        severity=Severity.LOW,
        code=code.value,
        message=message,
        can_continue=True,
        next_action=NextAction.REVIEW_WARNINGS,
        stage=stage,
        request_id=request_id,
        issues=issues or [],
        details=details or {},
    )


def from_error(exc: Any, *, request_id: str) -> ApiResponse:
    """Dựng response từ AppError. Mọi thuộc tính contract đã nằm sẵn trên
    exception nên ở đây không có logic nào để lỡ tay làm sai."""
    return ApiResponse(
        status=exc.status,
        severity=exc.severity,
        code=exc.code.value if isinstance(exc.code, ErrorCode) else str(exc.code),
        message=exc.message,
        can_continue=exc.can_continue,
        next_action=exc.next_action,
        stage=exc.stage,
        request_id=request_id,
        issues=exc.issues,
        details=exc.details,
    )
