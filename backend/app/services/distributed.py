"""Redis 分布式锁：多 Worker / 多进程部署时的任务互斥。

SET NX PX + 随机 token + Lua 比较删除（只删自己的锁）。
内存队列模式无需跨进程锁，提供 no-op 回退。
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any

_UNLOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisLock:
    def __init__(self, client: Any, name: str, token: str | None = None, ttl_ms: int = 30_000) -> None:
        self.client = client
        self.name = name
        self.token = token or uuid.uuid4().hex
        self.ttl_ms = ttl_ms

    def acquire(self) -> bool:
        try:
            return bool(self.client.set(self.name, self.token, nx=True, px=self.ttl_ms))
        except Exception:
            return False

    def release(self) -> None:
        try:
            self.client.eval(_UNLOCK_LUA, 1, self.name, self.token)
        except Exception:
            pass


@contextmanager
def distributed_lock(client: Any | None, name: str, ttl_ms: int = 30_000):
    """client 为 None 时退化为直接执行（内存队列单进程无竞争）。"""
    if client is None:
        yield True
        return
    lock = RedisLock(client, name, ttl_ms=ttl_ms)
    if not lock.acquire():
        yield False
        return
    try:
        yield True
    finally:
        lock.release()
