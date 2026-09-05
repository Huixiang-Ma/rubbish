"""Sentiment 舆情 Agent：对行程候选资源做负面舆情/风险过滤。

输出避坑提示与风险告警，供 Reporter 渲染"舆情与避坑提示"章节。
分类口径（需求文档 §11.2）：BENIGN / NEGATIVE_REVIEW / SERVICE_RISK / SAFETY_RISK / SCAM_RISK / UNKNOWN。
数据来源：本地舆情库（演示口径）；LLM real 模式可对未收录景点增强分类，失败静默回退。
"""
from __future__ import annotations

import json
from typing import Any

from app.agents.base import AgentBase
from app.services.llm_client import LLMClient
from app.services.paths import STATIC_DATA_ROOT

RISK_ORDER = {"SAFETY_RISK": 0, "SCAM_RISK": 1, "SERVICE_RISK": 2, "NEGATIVE_REVIEW": 3, "UNKNOWN": 4, "BENIGN": 5}
_CONSERVATIVE_NOTE = "暂未获取到该景点舆情信息，建议出行前自行确认。"


class SentimentAgent(AgentBase):
    name = "Sentiment"

    def __init__(self) -> None:
        self.llm = LLMClient()

    @staticmethod
    def _load_reviews() -> dict[str, dict[str, Any]]:
        path = STATIC_DATA_ROOT / "sentiment_reviews.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _collect_names(self, context: dict[str, Any]) -> list[str]:
        """收集待分析资源：Researcher spots + Itinerary 每日 items 的景点名（保持出现顺序去重）。"""
        outputs = context.get("outputs", {})
        names: list[str] = []
        seen: set[str] = set()

        def push(name: str) -> None:
            if name and name not in seen:
                seen.add(name)
                names.append(name)

        for spot in outputs.get("Researcher", {}).get("payload", {}).get("spots", []):
            push(spot.get("name", ""))
        for day in outputs.get("Itinerary", {}).get("payload", {}).get("itinerary", []):
            for item in day.get("items", []):
                push(item.get("spot", {}).get("name", ""))
        return names

    def _llm_classify(self, names: list[str], destination: str) -> dict[str, dict[str, Any]] | None:
        """LLM real 模式增强：对未收录景点做舆情分类；任何失败返回 None（回退本地口径）。"""
        if self.llm.mode != "real" or not names:
            return None
        schema = {
            "type": "object",
            "properties": {
                "reviews": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "risk_level": {"type": "string"},
                            "highlights": {"type": "array", "items": {"type": "string"}},
                            "warnings": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "risk_level"],
                    },
                }
            },
        }
        prompt = (
            f"你是旅游舆情分析器。目的地：{destination}。"
            f"对以下景点逐个做舆情分类，risk_level 只能取：BENIGN / NEGATIVE_REVIEW / SERVICE_RISK / "
            f"SAFETY_RISK / SCAM_RISK。不确定时用 UNKNOWN。只输出 JSON："
            f'{{"reviews": [{{"name": "...", "risk_level": "...", "highlights": ["..."], "warnings": ["..."]}}]}}。'
            f"景点列表：{json.dumps(names, ensure_ascii=False)}"
        )
        result = self.llm.try_generate_json(prompt, schema)
        if not result:
            return None
        reviews: dict[str, dict[str, Any]] = {}
        for item in result.get("reviews", []):
            name = item.get("name")
            if name and item.get("risk_level") in RISK_ORDER:
                reviews[name] = item
        return reviews or None

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        destination = context["user_input"].get("destination", "")
        names = self._collect_names(context)
        local_db = self._load_reviews()
        # LLM 增强仅覆盖本地库未收录的景点；失败（含 mock 模式）静默回退
        unknown_names = [n for n in names if n not in local_db]
        llm_reviews = self._llm_classify(unknown_names, destination) if unknown_names else None

        reviews: list[dict[str, Any]] = []
        risk_alerts: list[dict[str, Any]] = []
        for name in names:
            entry = local_db.get(name)
            source = "本地舆情库（演示口径）"
            if entry is None:
                entry = (llm_reviews or {}).get(name)
                if entry is not None:
                    source = "LLM 舆情增强（演示口径）"
            if entry is None:
                # 诚实口径：无本地数据且 LLM 不可用 → UNKNOWN，保守降权处理
                reviews.append({"name": name, "risk_level": "UNKNOWN", "highlights": [], "warnings": [_CONSERVATIVE_NOTE], "source": source})
                continue
            review = {
                "name": name,
                "risk_level": entry.get("risk_level", "UNKNOWN"),
                "highlights": list(entry.get("highlights", [])),
                "warnings": list(entry.get("warnings", [])),
                "notes": entry.get("notes", ""),
                "source": source,
            }
            reviews.append(review)
            # 告警口径：SAFETY_RISK / SCAM_RISK / SERVICE_RISK 与带 warnings 的 NEGATIVE_REVIEW；BENIGN 不告警
            level = review["risk_level"]
            if level in ("SAFETY_RISK", "SCAM_RISK", "SERVICE_RISK"):
                suggestion = (
                    "出行前再次确认官方渠道信息，避开非正规渠道。"
                    if level in ("SAFETY_RISK", "SCAM_RISK")
                    else "预留排队与备选方案，避开高峰时段。"
                )
                risk_alerts.append(
                    {
                        "name": name,
                        "risk_level": level,
                        "message": "；".join(review["warnings"]) or review.get("notes", ""),
                        "suggestion": suggestion,
                    }
                )
            elif level == "NEGATIVE_REVIEW" and review["warnings"]:
                risk_alerts.append(
                    {
                        "name": name,
                        "risk_level": level,
                        "message": "；".join(review["warnings"]),
                        "suggestion": "按提示规避排队与消费陷阱，行程不受影响。",
                    }
                )
        risk_alerts.sort(key=lambda alert: RISK_ORDER.get(alert["risk_level"], 9))
        risk_count = sum(1 for review in reviews if review["risk_level"] not in ("BENIGN",))
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "reviews": reviews,
                "risk_alerts": risk_alerts,
                "summary": f"共分析 {len(reviews)} 个资源，其中 {risk_count} 条存在风险提示或信息待确认。",
            },
        }
