from fastapi import APIRouter, HTTPException

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse
import hmac
import hashlib
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

@router.post("/webhook/github")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(None), # Bắt header xem loại sự kiện là gì
    x_hub_signature_256: str = Header(None) # Bắt header chứa chữ ký bảo mật
):
    # ==========================================
    # BƯỚC 1 & 2: NHẬN DỮ LIỆU & XÁC THỰC BẢO MẬT
    # ==========================================
    body = await request.body() # Đọc dữ liệu thô
    
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Bị từ chối: Thiếu chữ ký bảo mật")

    # Tự tính toán lại chữ ký dựa trên Secret Key của mình
    expected_signature = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    # So sánh an toàn 2 chữ ký
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Bị từ chối: Chữ ký giả mạo!")

    # ==========================================
    # BƯỚC 3: LỌC SỰ KIỆN
    # ==========================================
    if x_github_event == "ping":
        return {"status": "success", "message": "Pong! Webhook đã kết nối thành công với GitHub."}
        
    if x_github_event != "push":
        return {"status": "ignored", "message": f"Bỏ qua sự kiện {x_github_event}, chỉ xử lý push."}

    # ==========================================
    # BƯỚC 4: TRÍCH XUẤT THÔNG TIN & XỬ LÝ
    # ==========================================
    payload = await request.json() # Chuyển dữ liệu thô thành dạng Dictionary
    
    commits = payload.get("commits", [])
    if not commits:
        return {"status": "ignored", "message": "Không có commit nào trong lần push này."}

    # Lấy commit cuối cùng trong mảng
    latest_commit = commits[-1]
    commit_id = latest_commit["id"]
    repo_name = payload["repository"]["full_name"]
    pusher_name = payload["pusher"]["name"]

    print(f"🚀 {pusher_name} vừa push code lên {repo_name}!")
    print(f"Commit ID: {commit_id}")
    
    # Tại đây, bạn gọi hàm lấy diff API mà chúng ta đã làm ở ví dụ trước
    # diff_code = get_commit_diff_from_github(repo_name, commit_id)
    # print(diff_code)

    # ==========================================
    # BƯỚC 5: PHẢN HỒI CHO GITHUB
    # ==========================================
    return {"status": "success", "message": "Đã nhận và xử lý commit thành công!"}