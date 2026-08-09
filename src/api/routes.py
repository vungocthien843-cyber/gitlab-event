
from __future__ import annotations

import os
import hmac
import hashlib
import logging
import httpx # Dùng httpx thay cho requests vì FastAPI ưu tiên bất đồng bộ (async)
from typing import Literal
from urllib.parse import unquote
from dotenv import load_dotenv # Quan trọng: Để đọc biến từ file .env khi test local

from fastapi import APIRouter, File, Query, Response, UploadFile, status, Request, Header, HTTPException

from app.core.logging import get_request_id
from app.models.schemas import ApiResponse
from app.services import ingest
from app.services.validation import read_upload_within_limit

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse

# Tải các biến môi trường từ file .env vào hệ thống
load_dotenv()

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
    """Chat với AI agent."""
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
# CẤU HÌNH WEBHOOK (Lấy từ biến môi trường)
# ==========================================
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# --- HÀM PHỤ: LẤY NỘI DUNG RAW CỦA FILE TỪ GITHUB ---
async def fetch_file_content_from_github(repo_full_name: str, commit_id: str, file_path: str) -> str:
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}?ref={commit_id}"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}", # Dùng 'token' hoặc 'Bearer'
        "Accept": "application/vnd.github.v3.raw",
        "X-GitHub-Api-Version": "2022-11-28" 
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
    if response.status_code == 200:
        return response.text
    else:
        # IN ĐẬM LỖI RA VERCEL ĐỂ BẮT BỆNH
        print(f"=====================================")
        print(f" LỖI LẤY FILE: {file_path}")
        print(f" TRẠNG THÁI: {response.status_code}")
        print(f" CHI TIẾT LỖI TỪ GITHUB: {response.text}")
        print(f" URL ĐÃ GỌI: {url}")
        print(f"=====================================")
        return None

# ==========================================
# ROUTER CHÍNH: XỬ LÝ SỰ KIỆN GITHUB WEBHOOK
# ==========================================
@router.post("/webhook/github")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    # ------------------------------------------
    # 1. BẢO MẬT & LỌC SỰ KIỆN
    # ------------------------------------------
    body = await request.body()
    
    # Kiểm tra xem có cấu hình Secret chưa (để tránh lỗi 'NoneType' has no attribute 'encode')
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Lỗi Server: Chưa cấu hình WEBHOOK_SECRET")

    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Thiếu chữ ký bảo mật")

    expected_signature = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Chữ ký giả mạo!")

    if x_github_event == "ping":
        return {"status": "success", "message": "Pong! Webhook OK."}
        
    if x_github_event != "push":
        return {"status": "ignored", "message": "Chỉ xử lý sự kiện push."}

    # ------------------------------------------
    # 2. TRÍCH XUẤT METADATA TỪ WEBHOOK
    # ------------------------------------------
    payload = await request.json()
    commits = payload.get("commits", [])
    
    if not commits:
        return {"status": "ignored", "message": "Không có commit nào."}

    # Lấy thông tin từ commit cuối cùng (đại diện cho lần push này)
    latest_commit = commits[-1]
    commit_id = latest_commit["id"]
    repo_name = payload["repository"]["full_name"]
    committer_name = latest_commit["author"]["name"] 
    timestamp = latest_commit["timestamp"] 

    # ------------------------------------------
    # 3. TÌM FILE YAML BỊ THAY ĐỔI (ĐÃ SỬA LỖI MẢNG RỖNG)
    # ------------------------------------------
    changed_files = set() # Dùng tập hợp (set) để tránh trùng lặp file
    
    # Quét TẤT CẢ các commit trong lần push này để gom file, không chỉ quét 1 commit cuối nữa
    for commit in commits:
        for file in commit.get("added", []):
            changed_files.add(file)
        for file in commit.get("modified", []):
            changed_files.add(file)
    
    # Lọc ra chỉ lấy các file có đuôi .yaml hoặc .yml
    yaml_files = [f for f in changed_files if f.endswith('.yaml') or f.endswith('.yml')]

    # ------------------------------------------
    # 4. FETCH NỘI DUNG CODE & ĐÓNG GÓI DỮ LIỆU
    # ------------------------------------------
    files_content_data = [] 
    errors = [] # Tạo một mảng lưu lỗi

    for file_path in yaml_files:
        raw_content = await fetch_file_content_from_github(repo_name, commit_id, file_path)
        
        if raw_content:
            try:
                # GỌI HÀM INGEST THẬT CỦA HỆ THỐNG
                ingest.ingest_catalog(
                    filename=file_path.split("/")[-1], # Chỉ lấy tên file thay vì cả đường dẫn dài
                    content=raw_content.encode("utf-8"), # Chuyển text thô thành bytes
                    content_type="application/x-yaml",
                    request_id=get_request_id()
                )
                
                files_content_data.append({
                    "file_path": file_path,
                    "status": "Đã lưu vào DB thành công"
                })
            except Exception as e:
                # Nếu file YAML sai cấu trúc, bắt lỗi lại để không làm sập toàn bộ Webhook
                errors.append(f"Lỗi kiểm duyệt file {file_path}: {str(e)}")
        else:
            # Nếu không lấy được file, ghi lại lý do để xem
            errors.append(f"Không lấy được nội dung cho file: {file_path}")

    response_data = {
        "status": "Success",
        "metadata": {
            "committer_name": committer_name,
            "timestamp": timestamp,
            "commit_id": commit_id,
            "repo_name": repo_name,
            "commit_message": latest_commit["message"]
        },
        "yaml_changes": files_content_data,
        "debug_errors": errors # Xuất mảng lỗi này ra kết quả trả về
    }

    return {"status": "success", "data": response_data}