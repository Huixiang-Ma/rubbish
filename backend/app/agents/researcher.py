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
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "destination": user_input["destination"],
                "spots": spots,
                "notes": "MVP 使用演示城市静态景点库，不承诺实时路网。",
            },
        }
