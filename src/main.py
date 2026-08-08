from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import get_settings

# 1. Định nghĩa lifespan trước
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    print("Shutting down...")

# 2. KHỞI TẠO APP MỘT LẦN DUY NHẤT
app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

# 3. Thêm Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. NHÚNG ROUTER VÀO ĐÚNG CÁI APP VỪA TẠO
# Lưu ý: Vì bạn thêm prefix="/api/v1" ở đây, mọi API trong router sẽ bị nối thêm tiền tố này
app.include_router(router, prefix="/api/v1")

# 5. Khai báo các API trực tiếp (nếu có)
@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}