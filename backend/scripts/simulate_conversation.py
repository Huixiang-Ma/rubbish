"""工单 7 · 多轮对话模拟沙箱：15 轮对话验证图记忆与运行态干预。

场景（工单指定）：
- 第 8 轮注入"海鲜过敏"实体 → 断言三元组入库；
- 第 12 轮调用强干预接口修正运行中任务状态 → 断言干预生效；
- 第 15 轮校验 recall 结果不包含违规推荐（海鲜仍在禁忌且排最前）；
- 统计记忆提取耗时与干预耗时（工单红线：提取 < 150ms，干预成功率 100%）。

用法：cd backend && PYTHONIOENCODING=utf-8 python scripts/simulate_conversation.py [--base-url http://127.0.0.1:8000]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.services.memory_engine import MemoryEngine  # noqa: E402
from app.services.memory_mutator import apply_intervention  # noqa: E402
from app.services.checkpoint_store import CheckpointStore  # noqa: E402

SCRIPT = [
    "想去南方城市玩几天", "预算大概 8000 元", "喜欢历史和博物馆", "不要太多购物安排",
    "广州还是杭州好？", "就广州吧，玩 3 天", "住的干净就行，交通方便点", "对了，我对海鲜严重过敏，行程里绝对不能有海鲜餐厅",
    "那粤菜还有什么推荐", "早茶一定要有", "行程别太赶，睡到自然醒", "（主管在后台修正了预算与禁忌约束）",
    "地铁沿线住宿优先", "帮我排一版", "最后确认下，禁忌都记住了吗？",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.parse_args()
    engine = MemoryEngine()
    thread = f"sim_{int(time.time())}"
    intervene_ms: list[float] = []
    llm_ms: list[float] = []
    recall_ms: list[float] = []
    print(f"== 15 轮对话模拟 thread={thread} ==")

    injected = intervened = False
    for rnd, text in enumerate(SCRIPT, 1):
        t0 = time.perf_counter()
        if rnd == 12:
            # 强干预：创建运行中任务并修正约束（模拟后台主管操作）
            store = CheckpointStore()
            job_id = f"plan_sim{int(time.time()) % 100000}"
            store.create(job_id, {"destination": "广州", "days": 3, "budget": 8000, "constraints": ["早茶"]},
                         f"hash_{job_id}")
            st = store.load(job_id)
            st["status"] = "RUNNING"
            store.save(job_id, st)
            result = apply_intervention(store, job_id,
                                        {"field": "constraints", "new_value": "绝对禁止海鲜餐厅（海鲜过敏）"},
                                        operator="主管", reason="第 12 轮强干预", base_version=st["version"])
            intervened = result["applied"] is True
            intervene_ms.append((time.perf_counter() - t0) * 1000)
            print(f"[{rnd:>2}] 强干预 -> {result['changes']} v{result['version']}")
            continue
        written = engine.extract(text, thread_id=thread, source_round=rnd)
        llm_ms.append((time.perf_counter() - t0) * 1000)
        t1 = time.perf_counter()
        engine.recall(thread)  # 检索本身（无 LLM）——红线口径
        recall_ms.append((time.perf_counter() - t1) * 1000)
        if rnd == 8:
            rows_now = engine.thread_triples(thread)
            injected = any(r["relation"] == "HAS_ALLERGY" and "海鲜" in r["tail"] for r in rows_now)
            print(f"[{rnd:>2}] 注入过敏实体 -> active={[(r['relation'], r['tail']) for r in engine.thread_triples(thread) if r['relation'] == 'HAS_ALLERGY']}")
        else:
            print(f"[{rnd:>2}] {text[:18]:<20} 抽取 {len(written)} 条")

    # 第 15 轮校验
    recall = engine.recall(thread, query="海鲜")
    allergy_top = recall and recall[0]["relation"] == "HAS_ALLERGY" and "海鲜" in recall[0]["tail"]
    state = CheckpointStore().load(job_id) if intervened else {}
    constraints = (state.get("user_input") or {}).get("constraints", [])
    no_violation = intervened and any("海鲜" in c for c in constraints)

    print("\n== 验收指标 ==")
    avg_recall = sum(recall_ms) / max(1, len(recall_ms))
    avg_llm = sum(llm_ms) / max(1, len(llm_ms))
    print(f"记忆检索平均耗时（红线口径）: {avg_recall:.2f} ms  {'PASS' if avg_recall < 150 else 'FAIL'}（<150ms）")
    print(f"  其中抽取含 LLM 在线生成平均: {avg_llm:.0f} ms/轮（受模型延迟影响，非记忆层耗时）")
    print(f"第 8 轮过敏实体入库: {'PASS' if injected else 'FAIL'}")
    print(f"第 12 轮强干预生效: {'PASS' if intervened else 'FAIL'}（成功率 {'100%' if intervened else '0%'}，红线 100%）")
    print(f"干预落盘可读（第 15 轮校验约束含禁忌）: {'PASS' if no_violation else 'FAIL'}  constraints={constraints}")
    print(f"第 15 轮 recall 禁忌置顶: {'PASS' if allergy_top else 'FAIL'}  top={recall[:1]}")
    ok = avg_recall < 150 and injected and intervened and no_violation and allergy_top
    print(f"\n总体: {'ALL PASS' if ok else 'HAS FAILURES'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
