"""
catalogs.py — Controller. Mỏng có chủ đích.

Controller chỉ làm 3 việc: lấy dữ liệu ra khỏi HTTP request, gọi service, gắn
HTTP status code. Không validate, không ghi đĩa, không dựng message.

Bạn sẽ không thấy `try/except` bọc quanh lời gọi service ở đây, và đó là cố ý:
mọi `AppError` đã có handler toàn cục ở `main.py` biến thành đúng response
contract. Lặp lại cùng một khối try/except ở 3 endpoint là 3 chỗ để quên cập
nhật khi contract đổi. Bắt lỗi ở đây chỉ khi có việc RIÊNG của endpoint cần làm
— ví dụ đóng file tạm (xem `finally` bên dưới).
"""

from __future__ import annotations

import logging
from typing import Literal
from urllib.parse import unquote

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.core.logging import get_request_id
from app.models.schemas import ApiResponse
from app.services import ingest
from app.services.validation import read_upload_within_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalogs", tags=["Catalogs"])


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên 1 file catalog-info.yaml",
    responses={
        201: {"description": "Hợp lệ (status=success) hoặc hợp lệ kèm cảnh báo (status=warning)"},
        400: {"description": "Từ chối vì lý do an toàn (severity=critical)"},
        409: {"description": "Tranh chấp quyền sở hữu, cần người duyệt (next_action=human_review)"},
        422: {"description": "Input không hợp lệ (severity=validation)"},
        500: {"description": "Lỗi hệ thống (severity=critical)"},
    },
)
async def upload_catalog(file: UploadFile = File(...)) -> ApiResponse:
    """Nhận file, chạy 5 tầng validate, sinh graph JSON và ghi vào output_json/.

    Chỉ file qua được TOÀN BỘ validate mới được lưu. Bản cũ ghi file JSON ngay
    cả khi parse còn lỗi — nghĩa là thư mục output tích luỹ dữ liệu hỏng mà
    không ai biết. Giờ thì lỗi ở tầng nào cũng dừng trước khi chạm vào đĩa.
    """
    try:
        content = await read_upload_within_limit(file)
    finally:
        # UploadFile lớn được đệm ra file tạm; không đóng thì rác nằm lại trên đĩa.
        # `finally` chạy cả khi read raise FILE_TOO_LARGE.
        await file.close()

    return ingest.ingest_catalog(
        filename=file.filename,
        content=content,
        content_type=file.content_type,
        request_id=get_request_id(),
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="Danh sách catalog đã nạp, có tìm kiếm",
)
def list_catalogs(
    q: str | None = Query(
        default=None,
        description="Tìm theo tên file (khớp chuỗi con, không phân biệt hoa thường). "
        "Bỏ trống để lấy toàn bộ danh sách.",
        examples=["order"],
    ),
    include: Literal["diagnostics"] | None = Query(
        default=None, description="Truyền 'diagnostics' để lấy kèm chi tiết cảnh báo."
    ),
) -> ApiResponse:
    """Phục vụ cả hai cách chọn file ở màn hình xoá:

    - `GET /catalogs`            -> toàn bộ danh sách, đổ vào dropdown "Chọn file"
    - `GET /catalogs?q=order`    -> kết quả tìm kiếm theo tên

    Dữ liệu nằm ở `details.items`, kèm `details.total` để hiện "x/y file".
    """
    return ingest.list_catalogs(
        query=q,
        include_diagnostics=include == "diagnostics",
        request_id=get_request_id(),
    )


@router.delete(
    "/{filename}",
    response_model=ApiResponse,
    summary="Xoá 1 catalog đã nạp",
    responses={422: {"description": "Không tìm thấy file; details.suggestions gợi ý tên gần đúng"}},
)
def delete_catalog(filename: str, response: Response) -> ApiResponse:
    """Xoá cả bản ghi trong chỉ mục lẫn file JSON đã sinh.

    Trả 200 kèm body thay vì 204 rỗng: contract chung yêu cầu mọi response đều
    đọc được `status`/`message`/`can_continue`. 204 theo đúng chuẩn REST hơn
    nhưng buộc frontend phải xử lý riêng một trường hợp không có body — đổi lấy
    sự nhất quán thì không đáng.
    """
    response.status_code = status.HTTP_200_OK
    return ingest.delete_catalog(unquote(filename), request_id=get_request_id())
