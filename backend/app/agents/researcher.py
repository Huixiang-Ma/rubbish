import time
from typing import Any

from app.agents.base import AgentBase
from app.services import web_research
from app.services.scenic_spot_service import ScenicSpotService

# 白名单景点官网页（演示口径）：仅这几个域名会被抓取，且能力默认关闭
SPOT_OFFICIAL_PAGES = {
    "故宫博物院": "https://www.dpm.org.cn/home.html",
    "八达岭长城": "https://www.badaling.gov.cn/",
}


class ResearcherAgent(AgentBase):
    name = "Researcher"

    def __init__(self) -> None:
        self.scenic_spots = ScenicSpotService()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        spots: list[dict[str, Any]] = []
        # 高德 TLS 偶发抖动会返回空结果（无静态库的城市无法兜底），空时退避重试两次
        for attempt in range(3):
            spots = self.scenic_spots.recommend(
                user_input["destination"],
                user_input.get("preferences", []),
                limit=max(user_input["days"] * 4, 8),
            )
            if spots or attempt == 2:
                break
            time.sleep(0.8 * (attempt + 1))
        # 白名单网页调研（默认关闭）：命中官网页时用实时文本覆盖开放时间并补充预约规则
        if web_research.is_enabled():
            for spot in spots:
                url = SPOT_OFFICIAL_PAGES.get(spot.get("name", ""))
                if not url:
                    continue
                rules = web_research.research_spot(spot["name"], url)
                if rules:
                    if rules.get("open_time"):
                        spot["open_time"] = rules["open_time"]
                        spot["open_time_realtime"] = True
                    if rules.get("booking_rule"):
                        spot["booking_rule"] = rules["booking_rule"]
                    spot["fetched_at"] = rules["fetched_at"]
                    spot["source_url"] = url
        # RAG 知识增强（标品接入）：逐景点检索知识库，命中即挂 knowledge 卡片与来源
        # ——行程书内容有据化：markdown_reporter 会按 source 字段渲染溯源行
        for spot in spots:
            try:
                from app.services.semantic import search_similar

                hit = search_similar(spot.get("name", ""), k=1)
                results = hit.get("results") or []
                if results:
                    top = results[0]
                    spot["knowledge"] = top["content"]
                    spot["knowledge_source"] = top["job_id"]  # 语料来源组，可溯源
                    spot["knowledge_distance"] = top["distance"]
            except Exception:
                continue  # RAG 失败不阻断行程主链路
        result = {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "destination": user_input["destination"],
                "spots": spots,
                "notes": "MVP 使用演示城市静态景点库，不承诺实时路网。",
            },
        }
        # 数据生产闭环：Researcher 搜集的 POI 自动同步到素材库（去重，新建自动挂语料）
        try:
            from app.services.material_sync import sync_pois

            pois = [
                {
                    "name": s.get("name", ""), "city": user_input["destination"],
                    "lat": s.get("lat"), "lng": s.get("lng"),
                    "ticket_price": s.get("ticket_price", 0),
                    "visit_minutes": s.get("visit_minutes", 120),
                    "open_time": s.get("open_time", ""),
                    "tags": s.get("tags", []), "rating": s.get("rating", ""),
                    "description": (s.get("knowledge") or "")[:120],
                }
                for s in spots if s.get("name")
            ]
            result["payload"]["material_sync"] = sync_pois(pois, user_input["destination"], source="agent")
        except Exception:
            pass  # 同步失败不阻断规划主链路
        return result
