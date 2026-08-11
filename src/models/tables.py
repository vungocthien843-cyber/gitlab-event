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

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base


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


class GithubFileEventMixin:
    """Cột dùng chung cho 3 bảng `github_files_{added,modified,removed}`.

    Không kế thừa `Base` — đây chỉ là mixin, mỗi bảng con tự khai `__tablename__`
    riêng để ra 3 bảng vật lý khác nhau thay vì 1 bảng chung.

    LUÔN INSERT, không bao giờ UPDATE/DELETE: mỗi dòng là một lần file đó xuất
    hiện trong một push, không phải trạng thái hiện tại của file (trạng thái
    hiện tại của catalog vẫn nằm ở `InputJson`). Sửa cùng một file nhiều lần thì
    ra nhiều dòng — nhờ vậy giữ được lịch sử mã băm qua thời gian, không chỉ bản
    mới nhất.
    """

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Mã băm SHA-256 (64 ký tự hex) của nội dung file tại đúng commit liên quan.
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str] = mapped_column(String, nullable=False)
    commit_url: Mapped[str] = mapped_column(String, nullable=False)
    # Chuỗi ISO8601 GitHub gửi sang, giữ nguyên văn — cùng lý do với
    # `GithubCommitLog.timestamp` trước đây: không phụ thuộc việc ta parse
    # timezone có đúng hay không.
    event_time: Mapped[str] = mapped_column(String, nullable=False)
    # Đường dẫn đầy đủ trong repo ('services/order/catalog-info.yaml'), không
    # phải tên rút gọn — mục đích của bảng là truy ngược về đúng chỗ trong repo.
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    # Link bấm thẳng sang file trên GitHub tại đúng commit (blob permalink).
    url: Mapped[str] = mapped_column(String, nullable=False)


class GithubFileAdded(GithubFileEventMixin, Base):
    """Bảng `github_files_added` — mỗi dòng là MỘT file `.yaml`/`.yml` mới xuất
    hiện trong một lần push."""

    __tablename__ = "github_files_added"

    def __repr__(self) -> str:  # pragma: no cover - chỉ để debug
        return f"<GithubFileAdded id={self.id} file={self.file_name}>"


class GithubFileModified(GithubFileEventMixin, Base):
    """Bảng `github_files_modified` — mỗi dòng là MỘT file `.yaml`/`.yml` bị
    sửa nội dung trong một lần push."""

    __tablename__ = "github_files_modified"

    def __repr__(self) -> str:  # pragma: no cover - chỉ để debug
        return f"<GithubFileModified id={self.id} file={self.file_name}>"


class GithubFileRemoved(GithubFileEventMixin, Base):
    """Bảng `github_files_removed` — mỗi dòng là MỘT file `.yaml`/`.yml` bị xoá
    khỏi repo trong một lần push.

    `file_hash` ở đây là mã băm của nội dung file NGAY TRƯỚC KHI bị xoá (lấy tại
    commit `before` của push), không phải nội dung hiện tại — file đã không còn
    tồn tại ở commit mới nhất nên không có gì để băm ở đó.
    """

    __tablename__ = "github_files_removed"

    def __repr__(self) -> str:  # pragma: no cover - chỉ để debug
        return f"<GithubFileRemoved id={self.id} file={self.file_name}>"

