"""
broadcaster.py — Gửi sự kiện real-time qua Pusher.

Phù hợp cho kiến trúc Serverless (Vercel) vì không yêu cầu duy trì state (RAM)
giữa các request. Thay vì giữ kết nối SSE, Backend chỉ việc ném sự kiện cho Pusher,
Pusher sẽ lo việc phân phối qua WebSockets tới hàng ngàn client đang mở.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pusher import Pusher
from src.core.config import get_settings

logger = logging.getLogger(__name__)

class EventBroadcaster:
    """Giao tiếp với Pusher Channels để gửi Broadcast."""

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = bool(settings.pusher_app_id and settings.pusher_key and settings.pusher_secret)
        
        if self.enabled:
            self.pusher_client = Pusher(
                app_id=settings.pusher_app_id,
                key=settings.pusher_key,
                secret=settings.pusher_secret,
                cluster=settings.pusher_cluster,
                ssl=True
            )
            logger.info("Đã khởi tạo Pusher Client thành công.")
        else:
            logger.warning("Chưa cấu hình Pusher. Tính năng Real-time sẽ bị vô hiệu hoá.")

    async def publish(self, event: str, data: dict[str, Any]) -> None:
        """Đẩy event sang Pusher. Hàm async nên không làm chậm luồng gọi."""
        if not self.enabled:
            return

        def _trigger():
            try:
                # Bắn vào channel 'webhook-events', tên sự kiện là biến `event`
                self.pusher_client.trigger('webhook-events', event, data)
            except Exception as e:
                logger.error("Lỗi khi gửi sự kiện sang Pusher: %s", e)

        # Chạy Pusher (đồng bộ) trên một Thread khác để không block asyncio loop.
        asyncio.create_task(asyncio.to_thread(_trigger))

broadcaster = EventBroadcaster()
