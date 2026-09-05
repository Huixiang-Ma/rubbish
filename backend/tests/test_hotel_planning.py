"""酒店分类 / 折叠渲染 / 以酒店为行程起点的回归测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.itinerary import ItineraryAgent
from app.services import amap_client
from app.services.markdown_reporter import MarkdownReporter
from app.services.travel_context_service import TravelContextService

HOTEL_POIS = [
    {"name": "南昌香格里拉大酒店", "lng": 115.85, "lat": 28.69, "address": "翠林路669号", "type": "住宿服务;五星级酒店"},
    {"name": "泰耐克国际大酒店(秋水广场店)", "lng": 115.853, "lat": 28.691, "address": "新府路28号", "type": "住宿服务;宾馆"},
    {"name": "拾居公寓", "lng": 115.851, "lat": 28.688, "address": "世贸路", "type": "住宿服务;公寓"},
    {"name": "豪华阁贵宾廊", "lng": 115.854, "lat": 28.692, "address": "世贸路", "type": "住宿服务;会所"},
]


@pytest.fixture(autouse=True)
def _reset_cache():
    amap_client._cache.clear()
    yield
    amap_client._cache.clear()


def _enable_amap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(
        amap_client, "geocode",
        lambda address: {"lng": 115.857, "lat": 28.682, "adcode": "360100", "city": "南昌市"},
    )
    monkeypatch.setattr(
        amap_client, "around_pois",
        lambda lng, lat, types="", keywords="", radius=5000, size=8: list(HOTEL_POIS) if types == "100000" else [],
    )
    monkeypatch.setattr(
        amap_client, "route_between",
        lambda origin, dest, city="北京": {"transit_minutes": 30, "driving_minutes": 20, "distance_km": 8.0},
    )


def test_hotels_are_categorized_with_coords(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_amap(monkeypatch)
    data = TravelContextService().hotels("南昌市", nights=2)
    categories = {h["category"] for h in data["hotels"]}
    assert categories, "酒店应被分类"
    for hotel in data["hotels"]:
        assert hotel.get("lat") and hotel.get("lng"), "酒店应带坐标以支撑地理位置排程"
    # 香格里拉 → 高档酒店；公寓 → 民宿公寓
    by_name = {h["name"]: h for h in data["hotels"]}
    assert by_name["南昌香格里拉大酒店"]["category"] == "高档酒店"
    assert by_name["拾居公寓"]["category"] == "民宿公寓"


def test_itinerary_starts_from_recommended_hotel(monkeypatch: pytest.MonkeyPatch) -> None:
    """每日首站通勤以推荐酒店为起点，而非市中心。"""
    _enable_amap(monkeypatch)
    context = {
        "user_input": {"destination": "南昌市", "days": 1, "budget": 8000, "travelers": 2},
        "outputs": {
            "Planner": {"payload": {"days": [{"day": 1, "theme": "豫章古韵", "spot_names": ["滕王阁"]}]}},
            "Researcher": {
                "payload": {
                    "spots": [
                        {"name": "滕王阁", "lat": 28.672, "lng": 115.89, "tags": ["地标"], "ticket_price": 50, "visit_minutes": 120}
                    ]
                }
            },
        },
    }
    payload = ItineraryAgent().run(context)["payload"]
    assert payload["legs"][0]["from"] == "南昌香格里拉大酒店", payload["legs"][0]["from"]


def test_recommend_hotel_matches_budget_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """住宿推荐按预算分档匹配：品质型预算 → 高档酒店，经济型预算 → 民宿公寓。"""
    _enable_amap(monkeypatch)
    service = TravelContextService()
    pick = service.recommend_hotel_poi("南昌市", budget=8000, days=1, origin=None)
    assert pick["name"] == "南昌香格里拉大酒店", pick["name"]
    assert pick["matched_tier"] == "品质型"
    economy = service.recommend_hotel_poi("南昌市", budget=800, days=2)
    assert economy["name"] == "拾居公寓", economy["name"]
    assert economy["matched_tier"] == "经济型"


def test_reporter_renders_collapsible_hotel_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    """住宿推荐按预算推荐酒店（默认展开），每日行程直接嵌在其下，无重复通勤摘要。"""
    _enable_amap(monkeypatch)
    context = {
        "user_input": {"destination": "南昌市", "days": 1, "budget": 8000, "travelers": 2},
        "outputs": {
            "Planner": {"payload": {"days": [{"day": 1, "theme": "x", "spot_names": ["滕王阁"]}]}},
            "Researcher": {"payload": {"spots": [
                {"name": "滕王阁", "lat": 28.672, "lng": 115.89, "tags": ["地标"], "ticket_price": 50, "visit_minutes": 120}
            ]}},
            "Itinerary": {"payload": {"itinerary": [
                {"day": 1, "theme": "x", "items": [{"time": "09:00-11:00", "title": "游览滕王阁", "spot": {"name": "滕王阁", "lat": 28.672, "lng": 115.89}, "transport": "地铁 30 分钟", "reason": "x"}]}
            ], "legs": []}},
            "Validator": {"payload": {"estimated_budget": 3000, "travel_advice": {}, "what_if": [], "budget_breakdown": {}}},
            "Debate": {"payload": {"debates": []}},
        },
    }
    md = MarkdownReporter().render(context)
    assert "<details open>" in md
    assert "🏆 推荐入住：南昌香格里拉大酒店" in md
    # 每日行程直接嵌在推荐酒店条目下，无冗余的首站通勤摘要与引导行
    assert "### Day 1" in md
    assert md.index("推荐入住") < md.index("### Day 1") < md.index("·备选（")
    assert "若入住本酒店" not in md, "逐日首站通勤摘要应删除（交通建议已含从酒店出发的信息）"
    assert "入住本酒店的每日行程" not in md, "引导行应删除"
    assert "匹配预算" not in md, "预算匹配说明与分档建议重复，应删除"
    assert "泰耐克国际大酒店(秋水广场店)" in md, "其余酒店应作为备选保留"


def test_itinerary_adds_daily_weather_and_tips(monkeypatch: pytest.MonkeyPatch) -> None:
    """每天标注和风实时天气并给出今日建议；LLM 不可用时建议回退到天气驱动模板。"""
    from app.services import qweather_client
    from app.services.markdown_reporter import MarkdownReporter as Reporter

    _enable_amap(monkeypatch)
    monkeypatch.setenv("QWEATHER_API_KEY", "k")
    monkeypatch.setattr(
        qweather_client, "weather_3d",
        lambda location: [
            {"date": "2026-09-05", "text_day": "阵雨", "temp_min": "23", "temp_max": "26"},
            {"date": "2026-09-06", "text_day": "晴", "temp_min": "24", "temp_max": "31"},
        ],
    )
    context = {
        "user_input": {"destination": "南昌市", "days": 2, "budget": 8000, "travelers": 2},
        "outputs": {
            "Planner": {"payload": {"days": [
                {"day": 1, "theme": "豫章古韵", "spot_names": ["滕王阁"]},
                {"day": 2, "theme": "红色记忆", "spot_names": ["八一起义纪念馆"]},
            ]}},
            "Researcher": {"payload": {"spots": [
                {"name": "滕王阁", "lat": 28.672, "lng": 115.89, "tags": ["地标"], "ticket_price": 50, "visit_minutes": 120},
                {"name": "八一起义纪念馆", "lat": 28.682, "lng": 115.878, "tags": ["博物馆"], "ticket_price": 0, "visit_minutes": 90},
            ]}},
        },
    }
    payload = ItineraryAgent().run(context)["payload"]
    days = payload["itinerary"]
    assert days[0]["weather"].startswith("2026-09-05"), days[0].get("weather")
    assert "阵雨" in days[0]["weather"]
    assert days[1]["weather"].startswith("2026-09-06")
    assert days[0]["fun_tip"], "雨天建议应存在"
    assert "雨" in days[0]["fun_tip"], "雨天建议应提示携带雨具/室内备选"

    context["outputs"]["Itinerary"] = {"payload": payload}
    context["outputs"]["Validator"] = {"payload": {"estimated_budget": 3000, "travel_advice": {}, "what_if": [], "budget_breakdown": {}}}
    context["outputs"]["Debate"] = {"payload": {"debates": []}}
    md = Reporter().render(context)
    assert "当日天气：2026-09-05 阵雨 23~26℃（和风实时预报）" in md
    assert md.count("今日建议：") == 2


def test_itinerary_enriched_with_fliggy_rank(monkeypatch: pytest.MonkeyPatch) -> None:
    """飞猪AI 数据源启用时，Itinerary 阶段按景点名补充榜单与预订链接，并渲染进行程书。"""
    from app.services import fliggy_client

    _enable_amap(monkeypatch)
    monkeypatch.setenv("FLIGGY_AI_API_KEY", "test-key")
    monkeypatch.setattr(
        fliggy_client, "search_pois",
        lambda city, keyword="景点": [
            {"name": "滕王阁", "category": "历史古迹", "list_rank": "江西历史古迹景点榜第1名", "booking_url": "https://router.feizhu.com/x", "ticket_info": "", "main_pic": "https://img.alicdn.com/tengwangge.jpg", "source": "飞猪AI"}
        ],
    )
    spot = {"name": "滕王阁", "lat": 28.672, "lng": 115.881, "tags": ["地标"], "ticket_price": 50, "visit_minutes": 120, "open_time": "08:00-18:30", "open_time_realtime": True, "rating": "4.8"}
    context = {
        "user_input": {"destination": "南昌市", "days": 1, "budget": 8000, "travelers": 2},
        "outputs": {
            "Planner": {"payload": {"days": [{"day": 1, "theme": "豫章古韵", "spot_names": ["滕王阁"]}]}},
            "Researcher": {"payload": {"spots": [spot]}},
        },
    }
    payload = ItineraryAgent().run(context)["payload"]
    enriched_spot = payload["itinerary"][0]["items"][0]["spot"]
    assert enriched_spot["list_rank"] == "江西历史古迹景点榜第1名"
    assert enriched_spot["booking_url"] == "https://router.feizhu.com/x"
    assert enriched_spot["main_pic"] == "https://img.alicdn.com/tengwangge.jpg"
    # 行程书渲染榜单与预订链接
    context["outputs"]["Itinerary"] = {"payload": payload}
    context["outputs"]["Validator"] = {"payload": {"estimated_budget": 3000, "travel_advice": {}, "what_if": [], "budget_breakdown": {}}}
    context["outputs"]["Debate"] = {"payload": {"debates": []}}
    md = MarkdownReporter().render(context)
    assert "榜单：江西历史古迹景点榜第1名（飞猪AI）" in md
    assert "门票预订：[飞猪预订](https://router.feizhu.com/x)" in md
    assert "![ 滕王阁实拍](https://img.alicdn.com/tengwangge.jpg)" in md, "行程书应渲染飞猪实拍图"


def test_hotel_tier_accounts_for_rooms(monkeypatch: pytest.MonkeyPatch) -> None:
    """住宿分档按房间数计算：4 人 2 间房时预算不够高档则强制降为经济型。"""
    service = TravelContextService()
    # 15000 - 4000 大交通 - 3600 餐饮 = 7400 ÷ 5 晚 ÷ 2 间 = 740 元/间 → 舒适型（600）
    hotel = service.recommend_hotel(15000, 6, 4000, travelers=4)
    assert hotel["tier"] == "舒适型"
    assert hotel["rooms"] == 2
    # 5000 - 1000 - 900 = 3100 ÷ 3 晚 ÷ 2 间 ≈ 516 元/间 → 经济型（不足舒适型 600）且标注强制降档
    hotel2 = service.recommend_hotel(5000, 4, 1000, travelers=4)
    assert hotel2["tier"] == "经济型"
    assert hotel2["adjusted"] is True
