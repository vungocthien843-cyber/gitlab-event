"""
config.py — Đường dẫn và NGƯỠNG AN TOÀN của hệ thống.

Mọi con số giới hạn (size, độ sâu, số dòng...) nằm hết ở đây, không rải rác
trong code validate. Muốn siết/nới một luật thì sửa đúng một chỗ.
"""

import os
from pathlib import Path

# Gốc dự án (thư mục chứa app/, data/, requirements.txt, ...), suy ra từ vị trí
# file này thay vì dùng đường dẫn tương đối "./..." — tránh phụ thuộc vào cwd
# lúc chạy uvicorn (chạy từ đâu cũng ra đúng thư mục).
BASE_DIR = Path(__file__).resolve().parents[2]

# Thư mục output: nơi ghi các file JSON đã convert, tự tạo nếu chưa tồn tại
OUTPUT_DIR = str(BASE_DIR / "output_json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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
