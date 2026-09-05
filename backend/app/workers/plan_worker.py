import threading
import time

from app.config import get_settings
from app.services import metrics
from app.services.distributed import distributed_lock
from app.services.jsonlog import log_event
from app.services.plan_processor import plan_processor
from app.services.queue_client import queue_client


class PlanWorker:
    """后台消费循环：支持多 Worker（WORKER_COUNT），Redis 模式下任务级分布式锁互斥。

    at-least-once 语义：consume 读取（进 PEL）→ 处理 → ack；
    进程崩溃遗留的 PEL 消息由周期性 reclaim（XAUTOCLAIM）认领重投，
    重复投递由 plan_processor 幂等（COMPLETED 短路 + 任务锁）兜底。
    """

    def __init__(self) -> None:
        self._threads: list[threading.Thread] = []
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        settings = get_settings()
        count = max(1, settings.worker_count)
        for index in range(count):
            thread = threading.Thread(target=self._loop, name=f"plan-worker-{index}", args=(index,), daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._running = False

    def _loop(self, index: int) -> None:
        settings = get_settings()
        reclaim_interval = max(5, settings.reclaim_interval_seconds)
        last_reclaim = time.monotonic()
        use_locks = settings.queue_backend == "redis"
        redis_client = getattr(queue_client, "redis", None)
        while self._running:
            try:
                job_id = queue_client.consume()
                if job_id is None:
                    if time.monotonic() - last_reclaim >= reclaim_interval:
                        last_reclaim = time.monotonic()
                        for claimed in queue_client.reclaim():
                            log_event("pel_reclaimed", job_id=claimed, worker=index)
                            self._handle(claimed, index, use_locks, redis_client)
                    time.sleep(0.2)
                    continue
                self._handle(job_id, index, use_locks, redis_client)
            except Exception as exc:  # noqa: BLE001 - Worker 主循环兜底
                log_event("worker_loop_error", worker=index, error=str(exc))
                time.sleep(0.5)

    def _handle(self, job_id: str, index: int, use_locks: bool, redis_client) -> None:
        with distributed_lock(redis_client if use_locks else None, f"lock:job:{job_id}") as acquired:
            if not acquired:
                log_event("job_skipped_locked", job_id=job_id, worker=index)
                return
            started = time.monotonic()
            log_event("job_start", job_id=job_id, worker=index)
            try:
                plan_processor.process(job_id)
            finally:
                metrics.JOB_PROCESS_SECONDS.observe(time.monotonic() - started)
                try:
                    state = plan_processor.store.load(job_id)
                    if state.get("status") == "COMPLETED":
                        metrics.JOB_COMPLETED.inc()
                    elif state.get("status") == "FAILED":
                        metrics.JOB_FAILED.inc()
                except Exception:
                    pass
                queue_client.ack(job_id)
                log_event("job_ack", job_id=job_id, worker=index)


plan_worker = PlanWorker()
