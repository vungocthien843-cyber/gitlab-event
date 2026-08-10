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


class GithubCommitLog(Base):
    """Bảng `github_commits_log` — mỗi dòng là MỘT lần push lên GitHub.

    Đây là NHẬT KÝ AUDIT, không phải nguồn sự thật của catalog. Nguồn sự thật
    vẫn là `input_json`; bảng này trả lời câu hỏi mà `input_json` không giữ:
    "catalog đó vào hệ thống từ commit nào, ai đẩy lên, lúc nào".

        id              BIGSERIAL  khoá chính tự tăng
        email           VARCHAR    email tác giả của head_commit
        branch          VARCHAR    'main' (đã bỏ tiền tố refs/heads/)
        commit_url      VARCHAR    link bấm thẳng sang trang diff của GitHub
        timestamp       VARCHAR    ISO8601 nguyên văn GitHub gửi sang
        added_files     JSONB      danh sách đường dẫn file .yaml/.yml
        modified_files  JSONB
        removed_files   JSONB

    LUÔN INSERT, không bao giờ UPDATE — ngược hẳn với `InputJson`. Một lần push
    là một sự kiện ĐÃ XẢY RA, ghi đè lên nó là xoá mất lịch sử. Còn `input_json`
    mô tả trạng thái HIỆN TẠI nên upload lại cùng tên file thì phải ghi đè.

    Ba cột JSONB lưu ĐƯỜNG DẪN ĐẦY ĐỦ trong repo
    ('services/order/catalog-info.yaml') chứ không phải tên file rút gọn: mục
    đích của bảng là truy ngược về đúng chỗ trong repo. Tên rút gọn chỉ dùng khi
    gọi sang `ingest`, và việc quy đổi đó nằm ở tầng service.

    Lưu `timestamp` dạng chuỗi chứ không TIMESTAMPTZ: đây là chuỗi GitHub gửi
    sang, giữ nguyên văn thì log luôn khớp với thứ nhìn thấy trên GitHub, không
    phụ thuộc vào việc ta parse timezone có đúng hay không.
    """

    __tablename__ = "github_commits_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    branch: Mapped[str] = mapped_column(String, nullable=False)
    commit_url: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)

    # `default=list` là default phía Python, KHÔNG phải server default: INSERT
    # bằng SQL tay mà bỏ trống ba cột này sẽ vi phạm NOT NULL. Luôn ghi qua
    # `github_event_repository`.
    added_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    modified_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    removed_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    def __repr__(self) -> str:  # pragma: no cover - chỉ để debug
        return f"<GithubCommitLog id={self.id} branch={self.branch}>"

