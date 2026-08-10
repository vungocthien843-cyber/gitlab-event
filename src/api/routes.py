
from __future__ import annotations

import json
import logging
from typing import Literal
from urllib.parse import unquote

from fastapi import (
    APIRouter,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from src.core.logging import get_request_id
from src.models import schemas
from src.models.schemas import ApiResponse
from src.services import ingest
from src.services.validation import read_upload_within_limit
from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse
from src.services import github_events

# Không gọi load_dotenv() ở đây: app/core/config.py đã nạp .env lúc import (và
# nạp theo đường dẫn tuyệt đối, nên chạy uvicorn từ thư mục nào cũng đúng).

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
async def upload_catalog(
    file: UploadFile = File(...),
    force: bool = Query(default=False, description="Ép ghi đè nếu có tranh chấp quyền sở hữu")
) -> ApiResponse:
    """Nhận file, chạy 5 tầng validate, sinh graph JSON và lưu vào bảng `input_json`.

    Chỉ file qua được TOÀN BỘ validate mới được lưu. Bản cũ ghi file JSON ngay
    cả khi parse còn lỗi — nghĩa là kho output tích luỹ dữ liệu hỏng mà không ai
    biết. Giờ thì lỗi ở tầng nào cũng dừng trước khi chạm vào database.
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
        force=force,
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="Danh sách catalog đã nạp, có tìm kiếm",
)
def list_catalogs(
    q: str | None = Query(
        default=None,
        description="Tìm theo tên file. "
        "Bỏ trống để lấy toàn bộ danh sách.",
        examples=["order"],
    ),
    include: Literal["diagnostics"] | None = Query(
        default=None, description="Truyền 'diagnostics' để lấy kèm chi tiết cảnh báo."
    ),
) -> ApiResponse:
    """Phục vụ cả hai cách chọn file ở màn hình xoá:
    Bỏ trống để lấy toàn bộ list file
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
    """Xoá cả data trong bảng `input_json` lẫn bản ghi trong cache.

    Trả 200 kèm body thay vì 204 rỗng: contract chung yêu cầu mọi response đều
    đọc được `status`/`message`/`can_continue`. 204 theo đúng chuẩn REST hơn
    nhưng buộc frontend phải xử lý riêng một trường hợp không có body — đổi lấy
    sự nhất quán thì không đáng.
    """
    response.status_code = status.HTTP_200_OK
    return ingest.delete_catalog(unquote(filename), request_id=get_request_id())


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat vá»›i AI agent."""
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}


# ==========================================
# WEBHOOK GITHUB — nạp/xoá catalog tự động khi có push
# ==========================================
@router.post(
    "/webhook/github",
    response_model=ApiResponse,
    summary="Nhận sự kiện push từ GitHub",
    responses={
        200: {"description": "Đã xử lý (status=success) hoặc có file lỗi (status=warning)"},
        400: {"description": "Chữ ký HMAC sai hoặc thiếu (INVALID_SIGNATURE)"},
        500: {"description": "Server chưa cấu hình WEBHOOK_SECRET"},
    },
)
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
) -> ApiResponse:
    """Push lên GitHub -> ghi nhật ký + tự nạp/xoá catalog tương ứng.

    File `added`/`modified` được tải về và đẩy qua đúng pipeline validate 5 tầng
    của `POST /catalogs`; file `removed` thì gọi `delete_catalog`. Toàn bộ thứ tự
    các bước nằm ở `src/services/github_events.py`, controller chỉ bóc header ra
    và gọi service.

    Một file YAML sai vẫn trả HTTP 200 kèm `status=warning`: trả 4xx/5xx sẽ khiến
    GitHub đánh dấu delivery thất bại rồi retry, mà retry thì file vẫn sai y cũ.
    """
    body = await request.body()
    # Xác thực trên body THÔ, trước khi parse — chữ ký ký trên đúng chuỗi byte
    # GitHub gửi đi. Raise SecurityError/CriticalError, handler toàn cục ở
    # src/main.py lo phần dựng response.
    github_events.verify_signature(body, x_hub_signature_256)

    if x_github_event == "ping":
        return schemas.success("Webhook đã kết nối.", request_id=get_request_id())

    if x_github_event != "push":
        return schemas.success(
            f"Bỏ qua sự kiện '{x_github_event}' — chỉ xử lý push.",
            request_id=get_request_id(),
        )

    event = github_events.parse_push_payload(json.loads(body))
    if event is None:
        # Push tag, push xoá nhánh, hoặc push không chạm file YAML nào. Không
        # phải lỗi của ai — GitHub bắn webhook cho mọi push là đúng việc của nó.
        return schemas.success(
            "Push không có file YAML nào cần xử lý.", request_id=get_request_id()
        )

    return await github_events.handle_push(event, request_id=get_request_id())

