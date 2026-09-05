import os
import socket
import time
from collections import deque
from threading import Lock
from typing import Protocol

from app.config import get_settings


class QueueClient(Protocol):
    def enqueue(self, job_id: str) -> None:
        ...

    def consume(self) -> str | None:
        ...

    def ack(self, job_id: str) -> None:
        ...

    def reclaim(self) -> list[str]:
        ...


class InMemoryQueueClient:
    """本地演示队列；ack/reclaim 为 no-op（进程内无 PEL 概念）。"""

    def __init__(self) -> None:
        self._items: deque[str] = deque()
        self._lock = Lock()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            self._items.append(job_id)

    def consume(self) -> str | None:
        with self._lock:
            if not self._items:
                return None
            return self._items.popleft()

    def ack(self, job_id: str) -> None:
        return None

    def reclaim(self) -> list[str]:
        return []


class RedisStreamQueueClient:
    """Redis Streams 生产队列：at-least-once 语义。

    consume 读取后不立即 ack；Worker 处理完成调用 ack(job_id) 才确认。
    进程硬崩溃时消息留在 PEL，由 reclaim()（XAUTOCLAIM，按空闲时长）重新认领，
    配合 plan_processor 的幂等（COMPLETED 短路 + 任务锁）实现安全的重复投递。
    """

    def __init__(self) -> None:
        from redis import Redis

        settings = get_settings()
        self.stream_name = settings.redis_stream
        self.group_name = settings.redis_group
        # 消费者名默认按 主机+进程 唯一：--scale 多副本时避免同名消费者互抢 PEL
        self.consumer_name = settings.redis_consumer or f"worker-{socket.gethostname()}-{os.getpid()}"
        self.block_ms = settings.redis_block_ms
        self.claim_min_idle_ms = settings.redis_claim_min_idle_ms
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._pending: dict[str, str] = {}
        self._lock = Lock()
        # 建组惰性化：导入时 Redis 不可用不再让 uvicorn 崩溃循环，
        # 首次真正使用队列时按退避重试（见 _ensure_group_ready）
        self._group_ready = False

    def _ensure_group_ready(self) -> None:
        if self._group_ready:
            return
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self.redis.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
                self._group_ready = True
                return
            except Exception as exc:
                if "BUSYGROUP" in str(exc):
                    self._group_ready = True
                    return
                last_error = exc
                time.sleep(0.5 * (attempt + 1))
        raise last_error if last_error else RuntimeError("ensure_group failed")

    def enqueue(self, job_id: str) -> None:
        self._ensure_group_ready()
        self.redis.xadd(self.stream_name, {"job_id": job_id})

    def consume(self) -> str | None:
        self._ensure_group_ready()
        response = self.redis.xreadgroup(
            self.group_name,
            self.consumer_name,
            {self.stream_name: ">"},
            count=1,
            block=self.block_ms,
        )
        if not response:
            return None
        _, messages = response[0]
        message_id, fields = messages[0]
        job_id = fields.get("job_id")
        with self._lock:
            self._pending[job_id] = message_id
        return job_id

    def ack(self, job_id: str) -> None:
        with self._lock:
            message_id = self._pending.pop(job_id, None)
        if message_id:
            try:
                self.redis.xack(self.stream_name, self.group_name, message_id)
            except Exception:
                pass

    def reclaim(self) -> list[str]:
        """XAUTOCLAIM 认领空闲超时的 PEL 消息（其他 Worker 崩溃遗留），交回本消费者处理。"""
        try:
            cursor, messages, _ = self.redis.xautoclaim(
                self.stream_name,
                self.group_name,
                self.consumer_name,
                min_idle_time=self.claim_min_idle_ms,
                count=10,
            )
        except Exception:
            return []
        job_ids = []
        for message_id, fields in messages:
            job_id = fields.get("job_id")
            if job_id:
                with self._lock:
                    self._pending[job_id] = message_id
                job_ids.append(job_id)
        return job_ids

def build_queue_client() -> QueueClient:
    settings = get_settings()
    if settings.queue_backend == "redis":
        return RedisStreamQueueClient()
    if settings.queue_backend == "memory":
        return InMemoryQueueClient()
    raise ValueError(f"Unsupported QUEUE_BACKEND: {settings.queue_backend}")


queue_client = build_queue_client()
