"""QA/压测任务归档：把带 qa: 标记（及历史压测标记）的任务移出 data/jobs。

用法：
    python backend/scripts/archive_qa_jobs.py            # 预演：只打印将归档的任务
    python backend/scripts/archive_qa_jobs.py --apply    # 实际移动到 data/jobs_archive/

归档依据（state.json → user_input.constraints 任一命中）：
    ^qa:                    当前统一压测/探针标记（load_test.py 已统一为此前缀）
    ^load-test-             历史压测标记（旧版 load_test.py）
    ^rbac-notoken401-       历史 RBAC 探针标记
    ^bench-parent-          重规划基准测试（scripts/bench_replan.py）
    ^减少打车$               旧版压测脚本固定约束（57+ 条同指纹任务）
    忽略之前所有指令          Prompt 注入安全测试用例

归档不删除任何数据（审计口径不变），data/jobs_archive/ 仍可人工查阅。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

QA_MARKERS = re.compile(r"^(qa:|load-test-|rbac-notoken401-|bench-parent-|减少打车$)")
QA_SUBSTRINGS = ("忽略之前所有指令",)  # Prompt 注入安全测试固定句

ROOT = Path(__file__).resolve().parents[2]
JOBS = ROOT / "data" / "jobs"
ARCHIVE = ROOT / "data" / "jobs_archive"


def is_qa_job(state_path: Path) -> tuple[bool, str]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ""
    constraints = (state.get("user_input") or {}).get("constraints") or []
    for c in constraints:
        c = str(c)
        if QA_MARKERS.match(c) or any(s in c for s in QA_SUBSTRINGS):
            return True, c
    return False, ""


def main() -> int:
    apply = "--apply" in sys.argv
    fingerprint = "--fingerprint" in sys.argv
    if not JOBS.exists():
        print(f"not found: {JOBS}")
        return 1
    # 指纹模式：入参完全一致且份数 >= FINGERPRINT_MIN 的整组视为压测残留（真实用户不会提交 10 份完全相同的规划）
    FINGERPRINT_MIN = 10
    groups: dict[tuple, list[Path]] = {}
    jobs: list[tuple[Path, bool, str]] = []
    for job_dir in sorted(JOBS.iterdir()):
        state_path = job_dir / "state.json"
        if not job_dir.is_dir() or not state_path.exists():
            continue
        hit, marker = is_qa_job(state_path)
        if fingerprint and not hit:
            try:
                ui = dict(json.loads(state_path.read_text(encoding="utf-8")).get("user_input") or {})
            except (OSError, json.JSONDecodeError):
                ui = {}
            # 指纹排除 constraints：压测约束常带唯一时间戳，排除后才能聚成同组
            ui.pop("constraints", None)
            key = json.dumps(ui, sort_keys=True, ensure_ascii=False, default=str)
            groups.setdefault(key, []).append(job_dir)
        jobs.append((job_dir, hit, marker))
    if fingerprint:
        for key, dirs in groups.items():
            if len(dirs) >= FINGERPRINT_MIN:
                for d in dirs:
                    jobs.append((d, True, f"指纹组×{len(dirs)}"))
    moved = kept = 0
    for job_dir, hit, marker in jobs:
        if not hit:
            kept += 1
            continue
        print(f"[{'MOVE' if apply else 'PLAN'}] {job_dir.name}  marker={marker}")
        if apply:
            ARCHIVE.mkdir(parents=True, exist_ok=True)
            job_dir.rename(ARCHIVE / job_dir.name)
        moved += 1
    print(f"\n total: {moved} qa jobs {'archived' if apply else 'planned'}, {kept} real jobs kept")
    if not apply:
        print(" dry-run only; re-run with --apply to move")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
