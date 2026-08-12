"""
broadcaster.py — Pub/sub trong RAM để đẩy sự kiện real-time cho dashboard SSE.

Một singleton duy nhất trong tiến trình (KHÔNG dùng Redis/broker ngoài — hệ
thống chạy 1 instance). Mỗi client SSE đang kết nối giữ một `asyncio.Queue`
riêng; `publish()` bơm event vào TẤT CẢ các hàng đợi đang mở, không chờ ai
đọc — client chậm không được phép làm chậm client khác, và tuyệt đối không
được làm chậm request webhook đang publish.

Ba luật:
  1. Queue có giới hạn kích thước (bounded). Đầy thì DROP EVENT CŨ NHẤT của
     đúng client đó, không chặn publish() và không rớt kết nối.
  2. publish() không bao giờ await một thao tác có thể bị client làm chậm.
     Queue.put_nowait() là đồng bộ, không có cách nào 1 client treo được
     publish() của N-1 client còn lại.
  3. unsubscribe() phải chạy được trong finally của generator SSE — client
     ngắt kết nối không được để lại queue mồ côi.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class BroadcastEvent:
    """Một sự kiện chuẩn bị gửi qua SSE. `event` là tên loại sự kiện (map sang
    field `event:` của SSE); `data` là payload JSON-serializable; `id` dùng để
    debug / làm cơ sở cho Last-Event-ID nếu sau này thêm replay."""

    event: str
    data: dict[str, Any]
    id: str = field(default_factory=lambda: uuid4().hex[:12])


class EventBroadcaster:
    """Đăng ký/huỷ đăng ký client, và phát broadcast toàn cục (không lọc theo
    user/session — hệ thống không có bảng user)."""

    def __init__(self, *, queue_size: int = 100) -> None:
        self._queue_size = queue_size
        self._subscribers: set[asyncio.Queue[BroadcastEvent]] = set()
        # Lock chỉ bảo vệ thao tác thêm/bớt khỏi set — publish() KHÔNG giữ
        # lock trong lúc bơm event (xem lý do ở publish()).
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[BroadcastEvent]:
        queue: asyncio.Queue[BroadcastEvent] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        logger.info("SSE client kết nối. Tổng số đang xem: %d", len(self._subscribers))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[BroadcastEvent]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)
        logger.info("SSE client ngắt kết nối. Còn lại: %d", len(self._subscribers))

    async def publish(self, event: str, data: dict[str, Any]) -> None:
        """Bơm event vào MỌI client đang mở. Không raise, không bao giờ chặn
        lâu: hàm này được gọi từ giữa vòng lặp xử lý push, tuyệt đối không
        được làm chậm việc ingest catalog thật.
        """
        message = BroadcastEvent(event=event, data=data)
        async with self._lock:
            targets = list(self._subscribers)

        for queue in targets:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Client chậm: bỏ event CŨ NHẤT của riêng nó để nhường chỗ
                # cho event mới — dashboard thà nhảy cóc còn hơn đứng hình.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning(
                        "Không bơm được event '%s' cho 1 client SSE dù đã rớt bớt.", event
                    )


# Singleton toàn tiến trình — cùng idiom với `store = CatalogStore()` trong
# src/core/store.py. Đọc queue_size từ Settings ở lúc import module (config đã
# nạp xong .env từ trước, get_settings() được lru_cache).
def _make_broadcaster() -> EventBroadcaster:
    from src.core.config import get_settings

    return EventBroadcaster(queue_size=get_settings().sse_client_queue_size)


broadcaster = _make_broadcaster()
