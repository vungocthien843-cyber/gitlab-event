"""
Test tích hợp: POST /webhook/github có bắn đúng chuỗi sự kiện SSE qua
broadcaster hay không (push_started -> N file_result -> push_completed), và
POST /catalogs (upload thủ công) thì KHÔNG bắn sự kiện nào.

Dùng cùng schema Postgres riêng như `test_catalog_api.py` (bảng
`github_files_{added,modified,removed}` + `input_json` đều cần tồn tại thật,
vì `handle_push` ghi cả hai). `_fetch_file` được monkeypatch để không gọi
mạng thật tới GitHub — test chỉ cần đúng luồng nội bộ, không cần GitHub thật.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

import pytest
import pytest_asyncio
from sqlalchemy import text

from src.core import config
from src.core import db as core_db
from src.core.broadcaster import EventBroadcaster
from src.core.config import get_settings
from src.core.store import store
from src.services import github_events

WEBHOOK_SECRET = "test-webhook-secret"


def make_push_payload(
    *,
    added: tuple[str, ...] = (),
    modified: tuple[str, ...] = (),
    removed: tuple[str, ...] = (),
    before: str = "0" * 40,
    repo_full_name: str = "acme/catalogs",
    branch: str = "main",
) -> dict:
    """Hình dạng tối thiểu của payload push GitHub mà `parse_push_payload`
    cần: ref, before, head_commit.{id,url,timestamp,author.email},
    pusher.email, repository.full_name, commits[].{added,modified,removed}.
    """
    return {
        "ref": f"refs/heads/{branch}",
        "before": before,
        "repository": {"full_name": repo_full_name},
        "pusher": {"email": "pusher@example.com"},
        "head_commit": {
            "id": "c" * 40,
            "url": f"https://github.com/{repo_full_name}/commit/{'c' * 40}",
            "timestamp": "2026-08-12T00:00:00+07:00",
            "author": {"email": "author@example.com"},
        },
        "commits": [
            {
                "added": list(added),
                "modified": list(modified),
                "removed": list(removed),
            }
        ],
    }


def sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def post_webhook(client, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    return await client.post(
        "/api/v1/catalogs/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": sign(body),
            "Content-Type": "application/json",
        },
    )


VALID_YAML = b"""specVersion: vsf-idp.io/v2
metadata:
  domain: commerce
  system: order-system
  namespace: order
spec:
  type: worker
  id: order-worker
  name: Order Worker
  owners:
    members:
      - user: alice@example.com
        role: techlead
  review:
    branch: main
  topology:
    - ref: system:order/order-system
"""


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Bản sao rút gọn của fixture cùng tên trong test_catalog_api.py — mỗi
    module test tự có phiên bản riêng vì pytest fixture không chia sẻ qua
    module theo mặc định. Dùng chung schema test để không tạo thêm schema mới."""
    if not config.DATABASE_URL:
        pytest.fail(
            "Thiếu DATABASE_URL. Bộ test chạy trên Postgres thật (schema riêng), "
            "không có bản giả lập — hãy đặt biến này trong .env."
        )

    schema = os.getenv("TEST_DB_SCHEMA", "ai20k_db_test")
    if schema == (config.DB_SCHEMA or config.DB_SCHEMA_FALLBACK):
        pytest.fail(
            f"TEST_DB_SCHEMA trùng schema production ('{schema}'). "
            "Test sẽ TRUNCATE bảng nên phải nằm ở schema khác."
        )

    core_db.configure(config.DATABASE_URL, schema)
    core_db.init_db()

    yield

    with core_db.get_engine().begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    core_db.dispose()


@pytest.fixture(autouse=True)
def isolate():
    """Mỗi test bắt đầu với bảng rỗng và cache rỗng."""
    with core_db.get_engine().begin() as conn:
        conn.execute(text("TRUNCATE TABLE input_json RESTART IDENTITY"))
        conn.execute(text("TRUNCATE TABLE github_files_added RESTART IDENTITY"))
        conn.execute(text("TRUNCATE TABLE github_files_modified RESTART IDENTITY"))
        conn.execute(text("TRUNCATE TABLE github_files_removed RESTART IDENTITY"))
    store.clear()
    yield
    store.clear()


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    """`verify_signature` đọc secret qua `get_settings()` — ép giá trị test và
    xoá cache `lru_cache` để mọi lời gọi trong test đều thấy secret này."""
    monkeypatch.setenv("WEBHOOK_SECRET", WEBHOOK_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_fetch(monkeypatch):
    """Thay `_fetch_file` (gọi mạng thật tới GitHub) bằng nội dung giả cố định
    — test chỉ quan tâm luồng nội bộ (publish sự kiện + ghi DB), không cần
    GitHub thật trả lời."""

    async def _fetch(repo_full_name: str, ref: str, path: str) -> bytes | None:
        return VALID_YAML

    monkeypatch.setattr(github_events, "_fetch_file", _fetch)
    return _fetch


@pytest_asyncio.fixture
async def broadcaster_probe(monkeypatch):
    """Cắm một EventBroadcaster mới tinh vào github_events, độc lập với
    singleton toàn cục, để test không lẫn event giữa các lần chạy."""
    probe = EventBroadcaster()
    monkeypatch.setattr(github_events, "broadcaster", probe)
    return probe


class TestPushEventsSSE:
    @pytest.mark.asyncio
    async def test_push_them_file_thanh_cong_ban_du_3_loai_su_kien(
        self, client, fake_fetch, broadcaster_probe
    ):
        queue = await broadcaster_probe.subscribe()
        payload = make_push_payload(added=("services/order/catalog-info.yaml",))

        response = await post_webhook(client, payload)
        assert response.status_code == 200

        started = queue.get_nowait()
        assert started.event == "push_started"
        assert started.data["total_files"] == 1

        file_result = queue.get_nowait()
        assert file_result.event == "file_result"
        assert file_result.data["outcome"] == "ingested"
        assert file_result.data["filename"] == "catalog-info.yaml"

        completed = queue.get_nowait()
        assert completed.event == "push_completed"
        assert completed.data["status"] == "success"
        assert completed.data["ingested"] == ["catalog-info.yaml"]

        assert queue.empty()

    @pytest.mark.asyncio
    async def test_file_that_bai_ban_su_kien_kem_issue(
        self, client, monkeypatch, broadcaster_probe
    ):
        """Nội dung YAML hỏng -> ingest raise ValidationError -> file_result
        phải mang outcome='failed' kèm Issue mô tả đúng lỗi, không phải
        outcome='ingested'."""

        async def fetch_broken(repo_full_name, ref, path):
            return b"khong phai yaml hop le: [[["

        monkeypatch.setattr(github_events, "_fetch_file", fetch_broken)

        queue = await broadcaster_probe.subscribe()
        payload = make_push_payload(added=("services/order/broken.yaml",))

        response = await post_webhook(client, payload)
        assert response.status_code == 200

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        file_results = [e for e in events if e.event == "file_result"]
        assert len(file_results) == 1
        assert file_results[0].data["outcome"] == "failed"
        assert file_results[0].data["issue"] is not None
        assert file_results[0].data["issue"]["severity"] == "error"

        completed = [e for e in events if e.event == "push_completed"][0]
        assert completed.data["status"] == "warning"
        assert completed.data["failed"] == ["services/order/broken.yaml"]

    @pytest.mark.asyncio
    async def test_upload_thu_cong_khong_ban_su_kien_nao(self, client, broadcaster_probe):
        """Đúng quyết định thiết kế: chỉ webhook GitHub mới bắn SSE, upload
        thủ công qua POST /catalogs vẫn hoàn toàn đồng bộ, không đụng
        broadcaster (vì route đó không import/gọi github_events)."""
        queue = await broadcaster_probe.subscribe()

        response = await client.post(
            "/api/v1/catalogs",
            files=[("files", ("order-worker.yaml", VALID_YAML, "application/x-yaml"))],
        )
        assert response.status_code == 201
        assert queue.empty()
