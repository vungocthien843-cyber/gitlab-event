"""
github_events.py — Xử lý sự kiện push từ GitHub.

    xác thực chữ ký  ->  bóc tách payload  ->  ghi nhật ký DB
                                            ->  xoá catalog của file bị removed
                                            ->  nạp catalog của file added/modified
                                            ->  dá»±ng response

Đây là tầng DUY NHẤT biết thứ tự các bước, đúng vai trò `app/services/ingest.py`
giữ cho luồng upload thủ công. Controller (`src/api/routes.py`) không biết gì về
hình dạng payload của GitHub, và `ingest` không biết là nó đang được gọi từ một
webhook hay từ một form upload.

Hai nguyên tắc chi phối toàn bộ file này:

1. **Một file hỏng không được làm hỏng cả lần push.** Lỗi thuộc về nội dung file
   (YAML sai schema, tranh chấp quyền sở hữu, không tải được từ GitHub) được gom
   thành `Issue` và vẫn trả HTTP 200. Trả 4xx/5xx sẽ khiến GitHub đánh dấu
   delivery thất bại rồi RETRY — mà retry thì file vẫn sai y như cũ.

2. **Sự cố hệ thống thì ngược lại: phải để nổ.** `CriticalError` (database sập,
   chẳng hạn) được re-raise để thành 500 và GitHub retry — lần sau DB sống lại
   thì push được xử lý thật. Nuốt nó thành `Issue` là báo "đã xử lý xong" cho
   một việc chưa hề xảy ra.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import posixpath
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from starlette.concurrency import run_in_threadpool

from src.core.config import ALLOWED_EXTENSIONS
from src.core.errors import (
    AppError,
    CriticalError,
    ErrorCode,
    SecurityError,
    Stage,
)
from src.models import schemas
from src.models.schemas import ApiResponse, Issue
from src.services import github_event_repository, ingest
from src.config import get_settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

# GitHub gửi tên nhánh dưới dạng `refs/heads/main`. Tag là `refs/tags/v1.0`.
_BRANCH_PREFIX = "refs/heads/"

# Content-Type khai với `ingest`: layer 2 chỉ dùng nó để CẢNH BÁO khi lệch, không
# để chặn, nên khai đúng loại thật là đủ.
_YAML_CONTENT_TYPE = "application/x-yaml"


# ─────────────────────────────────────────────────────────────────────────────
# Dữ liệu đã bóc tách khỏi payload
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PushEvent:
    """Một lần push, đã lọc sạch còn đúng thứ hệ thống quan tâm.

    Ba danh sách file mang ĐƯỜNG DẪN ĐẦY ĐỦ trong repo
    ('services/order/catalog-info.yaml') và chỉ chứa file `.yaml`/`.yml`.
    """

    repo_full_name: str
    commit_id: str
    commit_url: str
    email: str
    branch: str
    timestamp: str
    added_files: list[str]
    modified_files: list[str]
    removed_files: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# Bước 1 — xác thực
# ─────────────────────────────────────────────────────────────────────────────


def verify_signature(body: bytes, signature_header: str | None) -> None:
    """Kiểm tra HMAC-SHA256 của GitHub. Không hợp lệ thì raise, hợp lệ thì im lặng.

    Chạy trên body THÔ, trước khi parse JSON: chữ ký ký trên đúng chuỗi byte
    GitHub gửi đi. Parse rồi serialize lại sẽ ra chuỗi khác (thứ tự key, khoảng
    trắng) và không còn khớp chữ ký nào cả.
    """
    secret = get_settings().webhook_secret

    if not secret:
        # Lỗi cấu hình phía ta, không phải của người gửi. Tuyệt đối không được
        # "vì chưa cấu hình nên bỏ qua bước xác thực" — như vậy là mở toang
        # endpoint cho bất kỳ ai gửi payload giả.
        raise CriticalError(
            ErrorCode.WEBHOOK_NOT_CONFIGURED,
            "Hệ thống chưa được cấu hình để nhận webhook. Vui lòng liên hệ hỗ trợ.",
            stage=Stage.RECEIVE,
            log_message="Thiếu WEBHOOK_SECRET — không có cách nào xác thực webhook GitHub.",
        )

    if not signature_header:
        raise SecurityError(
            ErrorCode.INVALID_SIGNATURE,
            "Yêu cầu không hợp lệ.",
            stage=Stage.RECEIVE,
            log_message="Webhook không kèm header X-Hub-Signature-256.",
        )

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    # So sánh trên bytes: `compare_digest` với chuỗi str sẽ nổ TypeError nếu
    # header chứa ký tự ngoài ASCII — và header thì do người gửi đặt.
    if not hmac.compare_digest(
        expected.encode("utf-8"), signature_header.encode("utf-8")
    ):
        # `message` cố ý mơ hồ: nói rõ "chữ ký sai" là chỉ cho kẻ đang dò biết
        # nó sai ở đâu. Lý do thật chỉ nằm trong log.
        raise SecurityError(
            ErrorCode.INVALID_SIGNATURE,
            "Yêu cầu không hợp lệ.",
            stage=Stage.RECEIVE,
            log_message="Chữ ký HMAC không khớp — request không đến từ GitHub, "
            "hoặc WEBHOOK_SECRET hai bên khác nhau.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Bước 2 — bóc tách payload
# ─────────────────────────────────────────────────────────────────────────────


def _classify_files(
    commits: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Gộp thay đổi của MỌI commit trong push thành 3 danh sách, hành-động-cuối-thắng.

    Một lần push mang nhiều commit và cùng một file có thể xuất hiện ở nhiều
    commit với hành động khác nhau. Chỉ trạng thái CUỐI CÙNG là có thật: file
    thêm ở commit 1 rồi xoá ở commit 3 thì trên nhánh nó không còn tồn tại — nạp
    nó vào hệ thống là nạp một file đã chết.

    Riêng 'added' thắng 'modified' đến sau: trong cùng một lần push thì nó vẫn là
    file mới toanh, gọi là "sửa" thì sai bản chất.
    """
    state: dict[str, str] = {}
    for commit in commits:
        for path in commit.get("added") or []:
            state[path] = "added"
        for path in commit.get("modified") or []:
            if state.get(path) != "added":
                state[path] = "modified"
        for path in commit.get("removed") or []:
            state[path] = "removed"

    buckets: dict[str, list[str]] = {"added": [], "modified": [], "removed": []}
    for path, action in state.items():
        if path.lower().endswith(ALLOWED_EXTENSIONS):
            buckets[action].append(path)

    # sorted() để thứ tự xử lý và nội dung ghi vào bảng log là tất định, không
    # phụ thuộc thứ tự key của dict hay thứ tự GitHub liệt kê file.
    return (
        sorted(buckets["added"]),
        sorted(buckets["modified"]),
        sorted(buckets["removed"]),
    )


def parse_push_payload(payload: dict[str, Any]) -> PushEvent | None:
    """Bóc `PushEvent` khỏi payload. Trả None khi không có gì để xử lý.

    Trả None thay vì raise cho mọi trường hợp "push hợp lệ nhưng không liên
    quan" (push tag, xoá nhánh, push toàn file .py). Đó không phải lỗi của ai
    cả — GitHub bắn webhook cho mọi push là đúng việc của nó.
    """
    ref = payload.get("ref") or ""
    if not ref.startswith(_BRANCH_PREFIX):
        logger.info("Bỏ qua push không nhắm vào nhánh: ref=%s", ref)
        return None

    # `head_commit` là null khi push xoá nhánh, hoặc khi push không mang commit
    # mới nào. Bản prototype cũ đọc thẳng payload["head_commit"]["url"] và nổ
    # TypeError ở đúng chỗ này.
    head = payload.get("head_commit")
    if not head:
        logger.info("Push lên '%s' không có head_commit — không có gì để xử lý.", ref)
        return None

    repo_full_name = (payload.get("repository") or {}).get("full_name")
    commit_id = head.get("id")
    commit_url = head.get("url")
    if not (repo_full_name and commit_id and commit_url):
        logger.warning(
            "Payload push thiếu repository.full_name / head_commit.id / head_commit.url "
            "— không đủ dữ liệu để tải file hay để ghi nhật ký."
        )
        return None

    added, modified, removed = _classify_files(payload.get("commits") or [])
    if not (added or modified or removed):
        logger.info("Push lên '%s' không chạm file YAML nào.", ref)
        return None

    author = head.get("author") or {}
    pusher = payload.get("pusher") or {}

    return PushEvent(
        repo_full_name=repo_full_name,
        commit_id=commit_id,
        commit_url=commit_url,
        # Tác giả commit là người viết thay đổi; `pusher` chỉ là người bấm push.
        # Ưu tiên tác giả, lùi về pusher khi commit không khai email.
        email=author.get("email") or pusher.get("email") or "",
        branch=ref[len(_BRANCH_PREFIX) :],
        timestamp=head.get("timestamp") or "",
        added_files=added,
        modified_files=modified,
        removed_files=removed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bước 3 — tải nội dung file từ GitHub
# ─────────────────────────────────────────────────────────────────────────────


async def _fetch_file(repo_full_name: str, ref: str, path: str) -> bytes | None:
    """Tải nội dung thô của 1 file tại đúng commit. None nếu không lấy được.

    Lấy theo `ref` là commit id chứ không theo tên nhánh: giữa lúc GitHub bắn
    webhook và lúc ta gọi API có thể đã có push khác chen vào, và khi đó đọc
    theo nhánh sẽ ra một nội dung khác với nội dung của chính commit này.
    """
    settings = get_settings()

    # `quote` với safe='/' mặc định — giữ nguyên dấu / ngăn cách thư mục, nhưng
    # mã hoá khoảng trắng và ký tự tiếng Việt trong tên file.
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{quote(path)}"
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # CHỈ gắn Authorization khi thật sự có token. Gắn một header rỗng hay chuỗi
    # "Bearer None" thì GitHub trả 401 ngay cả với repo public — thứ vốn đọc
    # được mà không cần xác thực gì.
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    try:
        async with httpx.AsyncClient(
            timeout=settings.github_api_timeout_seconds
        ) as client:
            response = await client.get(url, headers=headers, params={"ref": ref})
    except httpx.HTTPError as exc:
        logger.warning(
            "Không gọi được GitHub API cho '%s': %s", path, type(exc).__name__
        )
        return None

    if response.status_code != 200:
        # Log metadata thôi. `response.text` có thể mang nội dung file hoặc thông
        # điệp lỗi kèm thông tin repo private — không thuộc về log.
        logger.warning(
            "GitHub trả %d khi lấy '%s' tại ref=%s", response.status_code, path, ref
        )
        return None

    # Trả BYTES chứ không phải text đã decode: `ingest_catalog` nhận bytes, và
    # layer 2 của validation soi CHÍNH BYTE THÔ (magic bytes, ký tự NUL) trước
    # khi có ai parse. Decode ở đây rồi encode lại là vứt đi đúng thứ tầng đó cần.
    return response.content


# ─────────────────────────────────────────────────────────────────────────────
# Bước 4 — điều phối
# ─────────────────────────────────────────────────────────────────────────────


def _issue_from(exc: AppError, path: str) -> Issue:
    """Biến một lỗi cấp file thành `Issue` để nhét vào response chung."""
    return Issue(
        severity="error",
        code=exc.code.value,
        message=exc.message,
        source=path,
    )


async def handle_push(event: PushEvent, request_id: str) -> ApiResponse:
    """Chạy trọn một lần push. Trả về `ApiResponse` đúng contract chung.

    Mọi lời gọi xuống `ingest` và database đều đi qua `run_in_threadpool`: hàm
    này là `async` nhưng `ingest_catalog`, `delete_catalog` và psycopg2 đều đồng
    bộ và chặn. Gọi thẳng thì suốt N file, toàn bộ event loop đứng im — mọi
    request khác của API cũng phải chờ theo.
    """
    settings = get_settings()

    # ── Bước 1: ghi nhật ký TRƯỚC khi xử lý ──────────────────────────────────
    # Lần push này ĐÃ XẢY RA, bất kể ingest phía sau có thành công hay không.
    # Ghi sau sẽ mất bản ghi của đúng những lần push hỏng — thứ cần điều tra nhất.
    log_id = await run_in_threadpool(
        github_event_repository.save_commit_event,
        email=event.email,
        branch=event.branch,
        commit_url=event.commit_url,
        timestamp=event.timestamp,
        added_files=event.added_files,
        modified_files=event.modified_files,
        removed_files=event.removed_files,
    )

    issues: list[Issue] = []
    ingested: list[str] = []
    deleted: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    # ── Bước 2: xoá catalog của các file đã bị removed ───────────────────────
    # Xoá trước khi nạp: nếu một push vừa xoá 'a.yaml' vừa thêm 'b.yaml' khai
    # cùng một node, làm ngược thứ tự sẽ dựng ra tranh chấp quyền sở hữu giả.
    for path in event.removed_files:
        name = posixpath.basename(path)
        try:
            await run_in_threadpool(ingest.delete_catalog, name, request_id)
        except CriticalError:
            raise
        except AppError as exc:
            if exc.code == ErrorCode.CATALOG_NOT_FOUND:
                # Bình thường: GitHub báo xoá một YAML chưa từng được nạp vào hệ
                # thống (file thuộc repo nhưng không phải catalog, hoặc đã xoá từ
                # trước). Không có gì để làm, và cũng không có gì sai.
                skipped.append(name)
                logger.info("Bỏ qua xoá '%s': chưa từng được nạp.", name)
                continue
            failed.append(path)
            issues.append(_issue_from(exc, path))
        else:
            deleted.append(name)

    # ── Bước 3: nạp catalog của các file added + modified ────────────────────
    targets = [*event.added_files, *event.modified_files]
    if len(targets) > settings.github_max_files_per_push:
        skipped_count = len(targets) - settings.github_max_files_per_push
        issues.append(
            Issue(
                severity="warning",
                code=ErrorCode.HAS_WARNINGS.value,
                message=f"Push chạm {len(targets)} file YAML, vượt giới hạn "
                f"{settings.github_max_files_per_push} file mỗi lần. "
                f"{skipped_count} file chưa được xử lý — hãy tải lên thủ công.",
            )
        )
        targets = targets[: settings.github_max_files_per_push]

    for path in targets:
        name = posixpath.basename(path)

        content = await _fetch_file(event.repo_full_name, event.commit_id, path)
        if content is None:
            failed.append(path)
            issues.append(
                Issue(
                    severity="error",
                    code=ErrorCode.GITHUB_FETCH_FAILED.value,
                    message=f"Không tải được nội dung '{path}' từ GitHub.",
                    source=path,
                )
            )
            continue

        try:
            result = await run_in_threadpool(
                ingest.ingest_catalog, name, content, _YAML_CONTENT_TYPE, request_id
            )
        except CriticalError:
            raise
        except AppError as exc:
            failed.append(path)
            issues.append(_issue_from(exc, path))
        else:
            ingested.append(name)
            # Cảnh báo của chính file (thiếu owner, ref lạ...) đã được `ingest`
            # dựng sẵn thành Issue — chuyển tiếp nguyên vẹn thay vì nuốt mất.
            issues.extend(result.issues)

    # ── Bước 4: dựng response ────────────────────────────────────────────────
    details: dict[str, Any] = {
        "log_id": log_id,
        "repository": event.repo_full_name,
        "branch": event.branch,
        "email": event.email,
        "commit_id": event.commit_id,
        "commit_url": event.commit_url,
        "ingested": ingested,
        "deleted": deleted,
        "skipped": skipped,
        "failed": failed,
    }

    summary = (
        f"Push lên nhánh '{event.branch}': nạp {len(ingested)} file, "
        f"xoá {len(deleted)} file"
    )
    if failed:
        summary += f", {len(failed)} file lá»—i"
    summary += "."

    if not issues:
        logger.info(
            "Webhook xử lý xong push '%s' (log_id=%d): nạp %d, xoá %d",
            event.commit_id, log_id, len(ingested), len(deleted),
        )
        return schemas.success(summary, request_id=request_id, details=details)

    logger.warning(
        "Webhook xử lý push '%s' (log_id=%d) kèm %d vấn đề: %s",
        event.commit_id, log_id, len(issues), [i.code for i in issues],
    )
    return schemas.warning(
        summary, request_id=request_id, issues=issues, details=details
    )

