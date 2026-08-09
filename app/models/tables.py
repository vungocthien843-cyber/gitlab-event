"""
tables.py — Mô tả bảng trong database bằng ORM.

Đây là nguồn sự thật DUY NHẤT về hình dạng bảng. `init_db()` đọc file này để
sinh DDL, nên không có kịch bản "code nghĩ một đằng, bảng thật một nẻo" do ai đó
sửa bảng bằng tay mà quên sửa code.

Tách khỏi `schemas.py`: hai file này mô tả hai thứ khác nhau và đổi vì hai lý do
khác nhau. `schemas.py` là hợp đồng với frontend (Pydantic), file này là hợp đồng
với Postgres (SQLAlchemy). Gộp chung thì một thay đổi ở tầng lưu trữ trông như
một thay đổi ở API.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class InputJson(Base):
    """Bảng `input_json` — mỗi dòng là graph JSON sinh ra từ một catalog.

    Chỉ 2 cột theo đúng thiết kế:

        id       BIGSERIAL  khoá chính tự tăng
        content  JSONB      nội dung JSON, y hệt thứ trước đây ghi ra file

    Dùng JSONB chứ không TEXT: Postgres parse sẵn nên truy vấn được vào bên
    trong tài liệu. Chính nhờ vậy mới tra được "dòng nào ứng với file nào" qua
    `content->'scope'->'sources'->0->>'file'` mà không cần thêm cột.

    JSONB không giữ thứ tự key và bỏ khoảng trắng — không sao, vì mọi thứ tự có
    ý nghĩa (node theo id, edge theo topology) đều nằm trong mảng hoặc do tầng
    sinh JSON quyết định, không phụ thuộc thứ tự key của object.
    """

    __tablename__ = "input_json"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - chỉ để debug
        return f"<InputJson id={self.id}>"
