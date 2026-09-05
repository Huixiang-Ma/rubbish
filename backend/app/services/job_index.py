"""toB 聚合接口的进程内索引缓存。

背景：方案列表/审核台/经营看板/客户之声/安全看板此前每次请求都全量扫描
DATA_ROOT 并逐个 json 解析 state.json / audit.log，任务数增长后接口明显变慢
（Docker 卷挂载场景下文件 I/O 放大数倍，尤为明显）。

两级缓存策略：
1. 以 (mtime_ns, size) 为失效依据缓存解析结果——文件未变直接复用；
2. TTL（默认 2 秒）内的请求直接返回内存快照，连 stat 目录都不碰；
   TTL 过期后的下一次请求才重新扫描目录。Worker 跨进程写入后最迟
   TTL + 轮询间隔内可见，演示口径足够。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Iterator

from app.services import paths as paths_mod

TTL_SECONDS = 20.0

# key: (data_root_str, job_id) -> ((mtime_ns, size), 解析结果)
_states_by_root: dict[str, dict[str, tuple[tuple[int, int], dict[str, Any]]]] = {}
_audit_by_root: dict[str, dict[str, tuple[tuple[int, int], list[dict[str, Any]]]]] = {}
_scanned_at: dict[str, float] = {}
_lock = threading.RLock()  # 可重入：_maybe_scan 持锁时会调 _refresh_sync（内部再拿锁）


def _root_str(data_root: Path | None) -> tuple[str, Path]:
    root = Path(data_root) if data_root is not None else Path(paths_mod.DATA_ROOT)
    return str(root), root


def _scan_states(root_str: str, root: Path) -> None:
    cache = _states_by_root.setdefault(root_str, {})
    seen: set[str] = set()
    for job_path in sorted(root.iterdir()):
        state_path = job_path / "state.json"
        if not job_path.is_dir() or not state_path.exists():
            continue
        name = job_path.name
        seen.add(name)
        try:
            stat = state_path.stat()
            sig = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            continue
        cached = cache.get(name)
        if cached is not None and cached[0] == sig:
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cache[name] = (sig, state)
    for gone in cache.keys() - seen:
        del cache[gone]


def _scan_audit(root_str: str, root: Path) -> None:
    cache = _audit_by_root.setdefault(root_str, {})
    seen: set[str] = set()
    for job_path in sorted(root.iterdir()):
        audit_path = job_path / "audit.log"
        if not job_path.is_dir() or not audit_path.exists():
            continue
        name = job_path.name
        seen.add(name)
        try:
            stat = audit_path.stat()
            sig = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            continue
        cached = cache.get(name)
        if cached is not None and cached[0] == sig:
            continue
        parsed: list[dict[str, Any]] = []
        try:
            for line in audit_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            continue
        cache[name] = (sig, parsed)
    for gone in cache.keys() - seen:
        del cache[gone]


_refresh_inflight: set[str] = set()


def _refresh_sync(root_str: str, root: Path, which: str) -> None:
    with _lock:
        if which == "states":
            _scan_states(root_str, root)
        else:
            _scan_audit(root_str, root)
        _scanned_at[f"{root_str}|{which}"] = time.monotonic()


def _refresh_async(root_str: str, root: Path, which: str) -> None:
    """后台重扫：过期请求立即返回旧快照，绝不让接口阻塞在一次全量扫描上。"""

    def bg() -> None:
        try:
            _refresh_sync(root_str, root, which)
        finally:
            with _lock:
                _refresh_inflight.discard(f"{root_str}|{which}")

    threading.Thread(target=bg, daemon=True, name=f"job-index-refresh-{which}").start()


def _maybe_scan(root_str: str, root: Path, which: str) -> None:
    stamp_key = f"{root_str}|{which}"
    now = time.monotonic()
    if now - _scanned_at.get(stamp_key, 0.0) < TTL_SECONDS:
        return
    with _lock:
        # 已有刷新在跑（含启动预热）：直接用当前快照返回，绝不让请求排队等全量扫描
        if stamp_key in _refresh_inflight:
            return
        if _scanned_at.get(stamp_key) is None:
            # 首次访问：同步扫描，保证首请求就能看到数据
            _refresh_sync(root_str, root, which)
            return
        _refresh_inflight.add(stamp_key)
    _refresh_async(root_str, root, which)


def warmup(data_root: Path | None = None) -> None:
    """启动预热：后台线程全量扫描一次，避免重启后首个列表请求阻塞在冷扫描上。"""
    root_str, root = _root_str(data_root)
    for which in ("states", "audit"):
        stamp_key = f"{root_str}|{which}"
        with _lock:
            if stamp_key in _refresh_inflight:
                continue
            _refresh_inflight.add(stamp_key)
        _refresh_async(root_str, root, which)


def invalidate(job_id: str, data_root: Path | None = None) -> None:
    """写入后按任务精确失效：只重读该任务的 state/audit 并 upsert 进快照（毫秒级）。

    容器内 Worker 与 API 同进程，保存/审批/反馈后调用本函数即可立即一致；
    跨进程写入由 TTL + 后台刷新兜底。
    """
    root_str, root = _root_str(data_root)
    state_path = root / job_id / "state.json"
    states = _states_by_root.setdefault(root_str, {})
    if state_path.exists():
        try:
            stat = state_path.stat()
            state = json.loads(state_path.read_text(encoding="utf-8"))
            states[job_id] = ((stat.st_mtime_ns, stat.st_size), state)
        except (OSError, json.JSONDecodeError):
            states.pop(job_id, None)
    else:
        states.pop(job_id, None)
    audit_path = root / job_id / "audit.log"
    audits = _audit_by_root.setdefault(root_str, {})
    if audit_path.exists():
        try:
            stat = audit_path.stat()
            parsed = []
            for line in audit_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            audits[job_id] = ((stat.st_mtime_ns, stat.st_size), parsed)
        except OSError:
            audits.pop(job_id, None)
    else:
        audits.pop(job_id, None)


def iter_states(data_root: Path | None = None) -> Iterator[dict[str, Any]]:
    """按目录顺序产出全部任务 state（TTL 内直接复用内存快照）。"""
    root_str, root = _root_str(data_root)
    if not root.exists():
        return
    _maybe_scan(root_str, root, "states")
    for entry in _states_by_root.get(root_str, {}).values():
        yield entry[1]


def states_snapshot(data_root: Path | None = None) -> list[dict[str, Any]]:
    return list(iter_states(data_root))


def audit_events(data_root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """返回 {job_id: [审计事件]}（TTL 内直接复用内存快照）。"""
    root_str, root = _root_str(data_root)
    if not root.exists():
        return {}
    _maybe_scan(root_str, root, "audit")
    return {name: entry[1] for name, entry in _audit_by_root.get(root_str, {}).items()}
