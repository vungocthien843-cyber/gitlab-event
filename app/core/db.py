"""
db.py — Kết nối Postgres và tự tạo bảng bằng ORM.

Không có SQL thuần nào trong dự án: bảng được mô tả bằng model SQLAlchemy
(`app/models/tables.py`), còn `init_db()` dịch mô tả đó thành DDL và chạy.
Muốn thêm cột thì sửa model, không phải mở console gõ ALTER TABLE.

Vì sao engine tạo LƯỜI (lazy) chứ không tạo ngay lúc import: import module không
được phép mở kết nối mạng. Nếu tạo ngay, chỉ cần `import app.main` lúc DB đang
sập là cả tiến trình chết trước khi kịp log ra một dòng tử tế — và test cũng
không đổi được URL trước khi engine kịp ra đời.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import parse_qs, unquote, urlparse

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.schema import CreateSchema

from app.core.config import (
    DATABASE_URL,
    DB_CONNECT_TIMEOUT_SECONDS,
    DB_ECHO,
    DB_POOL_RECYCLE_SECONDS,
    DB_SCHEMA,
    DB_SCHEMA_FALLBACK,
)
from app.core.errors import CriticalError, ErrorCode, Stage

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Gốc khai báo của mọi bảng. `Base.metadata` là bản mô tả schema mà
    `init_db()` đem đi tạo."""


# Engine dùng chung toàn tiến trình. `None` = chưa ai cần tới DB.
_engine: Engine | None = None
_active_schema: str | None = None


def _schema_from_url(url: str) -> str | None:
    """Rút schema ra khỏi `?options=-csearch_path%3Dai20k_db` nếu URL có khai.

    URL Neon dán từ console thường đã kèm sẵn tham số này; đọc lại nó để cấu
    hình không mâu thuẫn với chuỗi kết nối.
    """
    options = parse_qs(urlparse(url).query).get("options", [""])[0]
    marker = "-csearch_path="
    if marker not in options:
        return None
    # `-csearch_path=a,b` -> lấy schema đầu tiên, đó là nơi CREATE TABLE rơi vào.
    return unquote(options.split(marker, 1)[1]).split(",")[0].strip() or None


def _make_engine(url: str, schema: str) -> Engine:
    engine = create_engine(
        url,
        echo=DB_ECHO,
        pool_pre_ping=True,
        pool_recycle=DB_POOL_RECYCLE_SECONDS,
        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
    )

    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection, _record) -> None:
        """Ép search_path ở MỌI connection.

        URL có thể quên `options=-csearch_path=...` (dán thiếu, copy nhầm), và
        khi đó bảng lặng lẽ rơi vào `public` — dữ liệu vẫn ghi được nên không ai
        nhận ra cho tới lúc đi tìm bảng ở đúng schema mà không thấy. Đặt lại ở
        đây thì URL thiếu hay đủ đều cho cùng một kết quả.
        """
        with dbapi_connection.cursor() as cur:
            cur.execute(f'SET search_path TO "{schema}"')

    return engine


def get_engine() -> Engine:
    global _engine, _active_schema
    if _engine is None:
        if not DATABASE_URL:
            raise CriticalError(
                ErrorCode.STORAGE_FAILURE,
                "Hệ thống chưa được cấu hình kho lưu trữ. Vui lòng liên hệ hỗ trợ.",
                stage=Stage.PERSIST,
                log_message="Thiếu biến môi trường DATABASE_URL — không có DB để ghi.",
            )
        # Ưu tiên: biến DB_SCHEMA > search_path trong URL > mặc định.
        _active_schema = (
            DB_SCHEMA or _schema_from_url(DATABASE_URL) or DB_SCHEMA_FALLBACK
        )
        _engine = _make_engine(DATABASE_URL, _active_schema)
    return _engine


def configure(url: str, schema: str) -> None:
    """Trỏ toàn hệ thống sang một database khác. Dùng cho test.

    Test chạy trên schema riêng (`ai20k_db_test`) để không đụng vào dữ liệu thật
    trong `ai20k_db`, nhưng vẫn là Postgres thật — JSONB, BIGSERIAL và kiểu so
    sánh JSON đều là thứ chỉ Postgres mới có, giả lập bằng DB khác là test đúng
    một hệ thống không tồn tại.
    """
    global _engine, _active_schema
    dispose()
    _active_schema = schema
    _engine = _make_engine(url, schema)


def dispose() -> None:
    """Đóng toàn bộ connection pool."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def active_schema() -> str:
    """Schema đang dùng thật sự. Gọi `get_engine()` trước vì tên schema chỉ được
    chốt lại lúc engine ra đời."""
    get_engine()
    assert _active_schema is not None
    return _active_schema


@contextmanager
def session_scope() -> Iterator[Session]:
    """Một session cho một đơn vị công việc: xong thì commit, hỏng thì rollback.

    Rollback là phần quan trọng: không có nó, một câu INSERT lỗi sẽ để lại
    transaction ở trạng thái aborted, và mọi câu lệnh sau trên cùng connection
    đều hỏng theo với thông báo chẳng liên quan gì tới nguyên nhân thật.
    """
    session = Session(bind=get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Tạo schema + bảng nếu chưa có, rồi KIỂM CHỨNG là bảng nằm đúng chỗ.

    `create_all` im lặng khi bảng đã tồn tại, nên bản thân nó không chứng minh
    được điều gì. Câu inspect ở cuối mới là thứ trả lời được "bảng có thật, ở
    đúng schema mình nghĩ không" — và log lại để lúc chạy Docker còn nhìn thấy.
    """
    # import ở đây, không ở đầu file: model phải được nạp thì mới có mặt trong
    # Base.metadata, nhưng model lại import Base từ chính module này.
    from app.models import tables  # noqa: F401

    engine = get_engine()
    schema = active_schema()

    with engine.begin() as conn:
        conn.execute(CreateSchema(schema, if_not_exists=True))

    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    tables_found = inspector.get_table_names(schema=schema)
    with engine.connect() as conn:
        current = conn.execute(text("select current_schema()")).scalar()

    logger.info(
        "DB sẵn sàng: schema=%s (current_schema=%s), bảng=%s",
        schema, current, sorted(tables_found),
    )

    if "input_json" not in tables_found:
        raise CriticalError(
            ErrorCode.STORAGE_FAILURE,
            "Không khởi tạo được kho lưu trữ.",
            stage=Stage.PERSIST,
            log_message=(
                f"Đã chạy create_all nhưng không thấy bảng 'input_json' trong "
                f"schema '{schema}'. Bảng có thể đã rơi vào schema khác."
            ),
        )
