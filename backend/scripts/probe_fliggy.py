"""P1.0 飞猪 MCP 接口探测 spike（实现方案 1.0，半天任务）。

目的：确认五类服务窗口（车票/机票/酒店/景点/演出）在飞猪AI MCP 上的
真实工具名、入参形态与返回字段，为 ticketing.py 的映射精确化提供依据。

用法：
    FLIGGY_AI_API_KEY=xxx python backend/scripts/probe_fliggy.py [目的地]

输出：每个探测调用的原始返回（截断 JSON），直接粘到 docs/飞猪MCP探测.md 即可。
任何一项返回 None/空，说明该工具名或入参需按官方 flyai-cli 文档修正。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import fliggy_client  # noqa: E402

PROBES: list[tuple[str, str, dict]] = [
    ("train", "search_train", {"origin": "杭州", "destination": "北京"}),
    ("train-alt", "ai_search", {"query": "杭州到北京的高铁车次和二等座价格"}),
    ("flight", "search_flight", {"origin": "杭州", "destination": "北京"}),
    ("hotel", "search_hotel", {"destName": "北京"}),
    ("attraction", "search_poi", {"cityName": "北京", "keyword": "景点"}),
    ("entertainment", "keyword_search", {"query": "北京 演出 展览"}),
]


def truncated(obj, limit: int = 1200) -> str:
    text = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    return text if len(text) <= limit else text[:limit] + f"\n...（截断，总长 {len(text)}）"


def main() -> int:
    if not fliggy_client.is_ready():
        print("FLIGGY_AI_API_KEY 未配置：请在 .env 配置后重跑本探测。")
        return 1
    destination = sys.argv[1] if len(sys.argv) > 1 else "北京"
    print(f"探测目的地：{destination}\n")
    findings: dict[str, dict] = {}
    for label, tool, args in PROBES:
        args = json.loads(json.dumps(args).replace("北京", destination) if label != "train-alt" else json.dumps(args))
        print(f"===== {label}  tool={tool}  args={args} =====")
        result = fliggy_client.call_tool(tool, args)
        print(truncated(result) if result else "None（无数据/工具名或入参不匹配）")
        print()
        if result:
            findings[label] = {"tool": tool, "args": args, "sample": result}
    out = Path(__file__).resolve().parents[2] / "docs" / "飞猪MCP探测.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write("# 飞猪 MCP 探测结果\n\n")
        f.write(f"- 探测时间：{__import__('datetime').datetime.now().isoformat(timespec='seconds')}\n\n")
        for label, data in findings.items():
            f.write(f"## {label}\n\n```json\n{json.dumps(data['sample'], ensure_ascii=False, indent=2, default=str)[:4000]}\n```\n\n")
    print(f"有效命中 {len(findings)}/{len(PROBES)} 项，已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
