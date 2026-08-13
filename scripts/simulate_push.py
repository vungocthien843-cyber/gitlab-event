"""
simulate_push.py — Giả một push GitHub gửi tới webhook local để test thủ công.

Dùng khi server đang chạy ở localhost:8000 và bạn muốn xem sự kiện SSE hiện
ra ở terminal đang `curl -N .../webhook/events`.

Usage:
    python scripts/simulate_push.py
    python scripts/simulate_push.py --added a.yaml b.yaml --removed c.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
DEFAULT_URL = "http://localhost:8000/api/v1/catalogs/webhook/github"


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def make_payload(
    added: list[str],
    modified: list[str],
    removed: list[str],
    repo_full_name: str,
    commit_id: str,
) -> dict:
    return {
        "ref": "refs/heads/main",
        "before": "0" * 40,
        "repository": {"full_name": repo_full_name},
        "pusher": {"email": "pusher@example.com"},
        "head_commit": {
            "id": commit_id,
            "url": f"https://github.com/{repo_full_name}/commit/{commit_id}",
            "timestamp": "2026-08-12T00:00:00+07:00",
            "author": {"email": "author@example.com"},
        },
        "commits": [{"added": added, "modified": modified, "removed": removed}],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Giả push GitHub gửi tới webhook local")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--repo", default="vungocthien843-cyber/gitlab-event")
    ap.add_argument(
        "--commit",
        required=True,
        help="SHA commit THẬT đang tồn tại trên repo (vd: HEAD của main) — "
        "_fetch_file tải nội dung theo đúng SHA này, không theo tên nhánh.",
    )
    ap.add_argument("--added", nargs="*", default=["data/file1.catalog.yaml"])
    ap.add_argument("--modified", nargs="*", default=[])
    ap.add_argument("--removed", nargs="*", default=[])
    args = ap.parse_args()

    if not WEBHOOK_SECRET:
        print("Thiếu WEBHOOK_SECRET trong .env — không ký được request.", file=sys.stderr)
        return 1

    payload = make_payload(args.added, args.modified, args.removed, args.repo, args.commit)
    body = json.dumps(payload).encode("utf-8")

    response = httpx.post(
        args.url,
        content=body,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": sign(body, WEBHOOK_SECRET),
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    print(f"HTTP {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
