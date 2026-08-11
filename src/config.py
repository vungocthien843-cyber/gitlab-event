from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    # GitHub webhook
    # Rỗng = chưa cấu hình. Không có giá trị mặc định nào khác được: một secret
    # mặc định nghĩa là ai cũng ký được request giả.
    webhook_secret: str = ""
    # Rỗng thì gọi GitHub API ẩn danh — repo public vẫn đọc được, chỉ bị giới hạn
    # rate thấp hơn. Repo private thì bắt buộc phải có.
    github_token: str = ""
    github_api_timeout_seconds: int = 10
    # Một lần đổi tên thư mục có thể chạm hàng trăm file YAML. Không chặn thì
    # một request webhook sẽ bắn hàng trăm lệnh gọi API GitHub và treo tới timeout.
    github_max_files_per_push: int = 50

@lru_cache
def get_settings() -> Settings:
    return Settings()
