"""
config.py — Đường dẫn và NGƯỠNG AN TOÀN của hệ thống.

Mọi con số giới hạn (size, độ sâu, số dòng...) nằm hết ở đây, không rải rác
trong code validate. Muốn siết/nới một luật thì sửa đúng một chỗ.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Gốc dự án (thư mục chứa app/, data/, requirements.txt, ...), suy ra từ vị trí
# file này thay vì dùng đường dẫn tương đối "./..." — tránh phụ thuộc vào cwd
# lúc chạy uvicorn (chạy từ đâu cũng ra đúng thư mục).
BASE_DIR = Path(__file__).resolve().parents[2]

# Nạp .env ở gốc dự án. `override=False` để biến môi trường thật (docker-compose
# env_file, CI secret) luôn thắng file .env trên máy lập trình viên.
load_dotenv(BASE_DIR / ".env", override=False)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─────────────────────────────────────────────────────────────────────────────
# Database — nơi lưu graph JSON (thay cho thư mục output_json/ trước đây)
# ─────────────────────────────────────────────────────────────────────────────

# Không có giá trị mặc định trỏ vào một DB nào đó: thiếu biến này thì phải hỏng
# ngay lúc khởi động với thông báo rõ ràng, chứ không phải âm thầm ghi vào chỗ
# không ai ngờ tới rồi vài ngày sau mới phát hiện dữ liệu nằm sai nơi.
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Schema chứa bảng `input_json`. Để trống thì suy từ `options=-csearch_path%3D...`
# trong DATABASE_URL (xem core/db.py); đặt biến này chỉ khi muốn ghi đè URL.
DB_SCHEMA = os.getenv("DB_SCHEMA", "")
DB_SCHEMA_FALLBACK = "ai20k_db"

# Bật để in mọi câu SQL ra log — chỉ dùng khi debug, rất ồn.
DB_ECHO = os.getenv("DB_ECHO", "").lower() in ("1", "true", "yes")

# Neon đóng connection nhàn rỗi. `pool_pre_ping` cho SQLAlchemy ping trước khi
# giao connection cho request, nếu chết thì lặng lẽ mở lại — không có nó thì
# request đầu tiên sau một lúc rảnh sẽ ăn OperationalError.
DB_POOL_RECYCLE_SECONDS = 300
DB_CONNECT_TIMEOUT_SECONDS = 10

# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — giới hạn cơ bản của file upload
# ─────────────────────────────────────────────────────────────────────────────

# 1 MiB. catalog-info.yaml thật cỡ vài KB; ngưỡng này đã rộng gấp trăm lần.
# Đặt thấp là một biện pháp an toàn, không phải sự bất tiện: nó chặn cả DoS
# bằng file khổng lồ lẫn tai nạn upload nhầm file dump.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 1024 * 1024))

# Đọc theo từng chunk để không nuốt trọn file vào RAM trước khi kịp kiểm tra size.
UPLOAD_CHUNK_BYTES = 64 * 1024

ALLOWED_EXTENSIONS = (".yaml", ".yml")
MAX_FILENAME_LENGTH = 128

# Content-Type do client khai — CHỈ dùng để cảnh báo, không dùng để chặn.
# Lý do: header này do client tự đặt, kẻ tấn công khai gì cũng được, còn trình
# duyệt thật thì hay gửi sai (Windows trả "application/octet-stream" cho .yaml).
# Chặn theo nó vừa không an toàn vừa chặn nhầm người dùng thật.
EXPECTED_CONTENT_TYPES = (
    "application/x-yaml",
    "application/yaml",
    "text/yaml",
    "text/x-yaml",
    "text/plain",
    "application/octet-stream",
)

# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — ngưỡng chống YAML bomb / nội dung bất thường
# ─────────────────────────────────────────────────────────────────────────────

# "Billion laughs": file 1KB dùng anchor/alias lồng nhau nở ra hàng GB lúc parse.
# SafeLoader KHÔNG chặn cái này — nó chỉ chặn tạo object Python tuỳ ý.
MAX_YAML_ANCHORS = 64
MAX_YAML_ALIASES = 256
MAX_YAML_DEPTH = 32          # theo mức thụt đầu dòng
MAX_YAML_LINES = 5_000
MAX_YAML_LINE_LENGTH = 8_192

# Tag khiến loader dựng object tuỳ ý. SafeLoader đã từ chối, ta chặn sớm hơn
# để trả về thông điệp rõ ràng thay vì một YAMLError khó hiểu.
FORBIDDEN_YAML_TAGS = ("!!python/", "!!java", "!!ruby", "!<tag:yaml.org,2002:python")

# Magic bytes của các định dạng nhị phân hay bị đội lốt .yaml
BINARY_MAGIC_SIGNATURES: dict[bytes, str] = {
    b"PK\x03\x04": "ZIP/XLSX/DOCX",
    b"\x89PNG": "PNG",
    b"\xff\xd8\xff": "JPEG",
    b"GIF8": "GIF",
    b"%PDF": "PDF",
    b"\x1f\x8b": "GZIP",
    b"BM": "BMP",
    b"\x7fELF": "ELF",
    b"MZ": "Windows PE",
    b"Rar!": "RAR",
    b"SQLite format 3": "SQLite",
}
