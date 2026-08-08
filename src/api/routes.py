import os
import hmac
import hashlib
import httpx # Dùng httpx thay cho requests vì FastAPI ưu tiên bất đồng bộ (async)
from dotenv import load_dotenv # Quan trọng: Để đọc biến từ file .env khi test local

from fastapi import APIRouter, Request, Header, HTTPException

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse

# Tải các biến môi trường từ file .env vào hệ thống
load_dotenv()

router = APIRouter()

# ==========================================
# CÁC ROUTER CŨ CỦA BẠN (GIỮ NGUYÊN)
# ==========================================
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
        print(f"🔥 LỖI LẤY FILE: {file_path}")
        print(f"🔥 TRẠNG THÁI: {response.status_code}")
        print(f"🔥 CHI TIẾT LỖI TỪ GITHUB: {response.text}")
        print(f"🔥 URL ĐÃ GỌI: {url}")
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
            files_content_data.append({
                "file_path": file_path,
                "content": raw_content
            })
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


    sql.save(re)

    return {"status": "success", "data": response_data}