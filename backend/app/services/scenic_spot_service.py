import json
from functools import lru_cache
from urllib.parse import quote

from app.services import amap_client
from app.services.paths import STATIC_DATA_ROOT


class ScenicSpotService:
    @lru_cache(maxsize=8)
    def load_spots(self, destination: str) -> list[dict]:
        # 前端选择带行政区划后缀（如"北京市"），匹配时归一化为城市短名
        if destination.removesuffix("市") != "北京":
            return []
        path = STATIC_DATA_ROOT / "scenic_spots_beijing.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def recommend(self, destination: str, preferences: list[str], limit: int = 12) -> list[dict]:
        # 真实模式：高德 key 就绪时走 POI 检索；失败或未配置回退静态演示库
        if amap_client.is_ready():
            real_spots = self._recommend_from_amap(destination, limit)
            if real_spots:
                return real_spots[:limit]
        spots = self.load_spots(destination)
        if not preferences:
            return spots[:limit]
        scored = []
        for spot in spots:
            tags = set(spot.get("tags", []))
            score = sum(1 for preference in preferences if preference in tags or preference in spot.get("name", ""))
            scored.append((score, spot))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [spot for _, spot in scored[:limit]]

    def _recommend_from_amap(self, destination: str, limit: int) -> list[dict]:
        real_pois = amap_client.search_pois(destination.removesuffix("市"), "景点", size=limit * 2)
        if not real_pois:
            return []
        static_spots = self.load_spots(destination)
        chosen: list[str] = []
        spots: list[dict] = []
        for poi in real_pois:
            name = poi["name"]
            # 去除嵌套重复（如"天安门"是"天安门广场"的子串，二者只留更完整的一个）
            if any(name in seen or seen in name for seen in chosen):
                continue
            chosen.append(name)
            static = next((s for s in static_spots if s["name"] in name or name in s["name"]), None)
            # 开放时间优先高德实时字段，无则回退静态库口径；是否实时由 open_time_realtime 标注
            poi_open_time = poi.get("open_time") or ""
            spots.append(
                {
                    "name": name,
                    "tags": list(dict.fromkeys(tag for tag in poi["type"].split(";") if tag))[:3] or ["景点"],
                    "lat": poi["lat"],
                    "lng": poi["lng"],
                    "ticket_price": static["ticket_price"] if static else 0,
                    "visit_minutes": static["visit_minutes"] if static else 120,
                    "open_time": poi_open_time or (static["open_time"] if static else "以景区公告为准"),
                    "open_time_realtime": bool(poi_open_time),
                    "rating": poi.get("rating") or (static.get("rating") if static else ""),
                    "list_rank": "",
                    "booking_url": "",
                    # 来源溯源：高德搜索页链接（可点击核对 POI 信息）
                    "source_urls": [f"https://www.amap.com/search?query={quote(name)}"],
                    "source": "高德POI",
                }
            )
            if len(spots) >= limit:
                break
        return spots

    def get_spot(self, destination: str, name: str) -> dict | None:
        for spot in self.load_spots(destination):
            if spot.get("name") == name:
                return spot
        return None
