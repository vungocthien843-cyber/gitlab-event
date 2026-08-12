"""
Test cho src/core/broadcaster.py — pub/sub trong RAM cho SSE.

Không dùng singleton `broadcaster` toàn cục ở đây: mỗi test tự tạo một
`EventBroadcaster()` riêng để không rò rỉ subscriber giữa các test (singleton
toàn cục sẽ tích luỹ queue chết qua các lần chạy nếu test không unsubscribe).
"""

from __future__ import annotations

import asyncio

import pytest

from src.core.broadcaster import EventBroadcaster


@pytest.mark.asyncio
async def test_client_dang_ky_nhan_duoc_event_da_publish():
    broadcaster = EventBroadcaster()
    queue = await broadcaster.subscribe()

    await broadcaster.publish("file_result", {"path": "a.yaml", "outcome": "ingested"})

    message = queue.get_nowait()
    assert message.event == "file_result"
    assert message.data == {"path": "a.yaml", "outcome": "ingested"}


@pytest.mark.asyncio
async def test_nhieu_client_deu_nhan_cung_mot_event():
    broadcaster = EventBroadcaster()
    queue_a = await broadcaster.subscribe()
    queue_b = await broadcaster.subscribe()

    await broadcaster.publish("push_started", {"total_files": 3})

    assert queue_a.get_nowait().data == {"total_files": 3}
    assert queue_b.get_nowait().data == {"total_files": 3}


@pytest.mark.asyncio
async def test_unsubscribe_thi_khong_con_nhan_event_nua():
    broadcaster = EventBroadcaster()
    queue = await broadcaster.subscribe()
    await broadcaster.unsubscribe(queue)

    await broadcaster.publish("push_completed", {"status": "success"})

    assert queue.empty()


@pytest.mark.asyncio
async def test_client_cham_bi_rot_event_cu_khong_bi_ngat_ket_noi():
    broadcaster = EventBroadcaster(queue_size=2)
    queue = await broadcaster.subscribe()

    await broadcaster.publish("file_result", {"n": 1})
    await broadcaster.publish("file_result", {"n": 2})
    await broadcaster.publish("file_result", {"n": 3})

    # Queue chỉ giữ 2 chỗ: event 1 (cũ nhất) bị rớt, còn lại 2 và 3.
    assert queue.qsize() == 2
    assert queue.get_nowait().data == {"n": 2}
    assert queue.get_nowait().data == {"n": 3}


@pytest.mark.asyncio
async def test_publish_khong_loi_du_khong_co_ai_dang_ky():
    broadcaster = EventBroadcaster()

    await broadcaster.publish("push_started", {"total_files": 0})  # không raise


@pytest.mark.asyncio
async def test_publish_khong_bi_chan_boi_mot_client_cham():
    """Bảo đảm N-1 client vẫn nhận event dù 1 client đầy hàng đợi."""
    broadcaster = EventBroadcaster(queue_size=1)
    slow = await broadcaster.subscribe()
    fast = await broadcaster.subscribe()

    await broadcaster.publish("file_result", {"n": 1})
    await asyncio.wait_for(
        broadcaster.publish("file_result", {"n": 2}), timeout=1
    )

    assert fast.qsize() == 1
    assert slow.qsize() == 1  # rớt event cũ, không chặn, không đầy vô hạn
