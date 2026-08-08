from fastapi import APIRouter, HTTPException
import hmac
import hashlib
import os
import httpx # Dùng httpx thay cho requests vì FastAPI ưu tiên bất đồng bộ (async)

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse

from fastapi import FastAPI, Request, Header, HTTPException
router = APIRouter()


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




# Mật khẩu này bạn tự bịa ra, sau đó copy dán vào phần "Secret" khi tạo Webhook trên GitHub
# Trong thực tế, KHÔNG hardcode ở đây mà nên để trong file biến môi trường (.env)
WEBHOOK_SECRET = "12345678" 


WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mat_khau_bi_mat_cua_thien_123")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "ghp_your_personal_access_token_here")


# --- HÀM PHỤ: LẤY NỘI DUNG RAW CỦA FILE TỪ GITHUB ---
async def fetch_file_content_from_github(repo_full_name: str, commit_id: str, file_path: str) -> str:
    """Gọi API GitHub để lấy nội dung thô (raw) của một file tại một commit cụ thể."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}?ref={commit_id}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw" # Yêu cầu trả về nội dung raw thay vì JSON base64
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
    if response.status_code == 200:
        return response.text
    else:
        print(f"Lỗi lấy file {file_path}: {response.status_code} - {response.text}")
        return None


# --- ROUTER CHÍNH ---
@app.post("/webhook/github")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    # ==========================================
    # 1. BẢO MẬT & LỌC SỰ KIỆN (Giữ nguyên như cũ)
    # ==========================================
    body = await request.body()
    
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

    # ==========================================
    # 2. TRÍCH XUẤT METADATA TỪ WEBHOOK
    # ==========================================
    payload = await request.json()
    commits = payload.get("commits", [])
    
    if not commits:
        return {"status": "ignored", "message": "Không có commit nào."}

    latest_commit = commits[-1]
    commit_id = latest_commit["id"]
    repo_name = payload["repository"]["full_name"]
    committer_name = latest_commit["author"]["name"] # Lấy tên tác giả commit
    timestamp = latest_commit["timestamp"] # Lấy thời gian thực của commit

    # ==========================================
    # 3. TÌM FILE YAML BỊ THAY ĐỔI
    # ==========================================
    # Gộp danh sách các file được thêm mới (added) và sửa đổi (modified)
    changed_files = latest_commit.get("added", []) + latest_commit.get("modified", [])
    
    # Lọc ra chỉ lấy các file có đuôi .yaml hoặc .yml
    yaml_files = [f for f in changed_files if f.endswith('.yaml') or f.endswith('.yml')]

    # ==========================================
    # 4. FETCH NỘI DUNG CODE & ĐÓNG GÓI DỮ LIỆU
    # ==========================================
    files_content_data = [] # Mảng chứa thông tin từng file YAML

    for file_path in yaml_files:
        # Gọi hàm phụ để lấy nội dung code
        raw_content = await fetch_file_content_from_github(repo_name, commit_id, file_path)
        
        if raw_content:
            files_content_data.append({
                "file_path": file_path,
                "content": raw_content
            })

    # Cấu trúc JSON cuối cùng chuẩn bị cho Web App
    response_data = {
        "status": "Success",
        "metadata": {
            "committer_name": committer_name,
            "timestamp": timestamp,
            "commit_id": commit_id,
            "repo_name": repo_name,
            "commit_message": latest_commit["message"]
        },
        "yaml_changes": files_content_data # Chứa mảng các file và ruột code bên trong
    }

    # Tại đây, bạn có thể lưu `response_data` vào Database 
    # HOẶC bắn sự kiện qua Pusher/Supabase để đẩy ra Frontend cho ứng dụng web

    print("--- DỮ LIỆU SẼ GỬI CHO WEB APP ---")
    print(response_data)

    # Trả về cho GitHub
    return {"status": "success", "data": response_data}