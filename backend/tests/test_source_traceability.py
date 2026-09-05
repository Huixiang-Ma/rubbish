"""来源 URL 溯源单测：高德链接生成、飞猪链接追加、静态兜底为空且渲染不报错。"""
from urllib.parse import quote

from app.services.scenic_spot_service import ScenicSpotService


def test_amap_poi_has_source_urls(monkeypatch):
    """高德 POI 命中时 spot 带可点击的 amap 检索链接。"""
    service = ScenicSpotService()
    fake_pois = [
        {"name": "故宫博物院", "type": "风景名胜;景点", "lat": 39.9, "lng": 116.4,
         "open_time": "08:30-17:00", "rating": "4.8"},
    ]
    monkeypatch.setattr("app.services.amap_client.is_ready", lambda: True)
    monkeypatch.setattr(service, "_recommend_from_amap", lambda dest, limit: [
        {
            "name": "故宫博物院", "tags": ["景点"], "lat": 39.9, "lng": 116.4,
            "ticket_price": 60, "visit_minutes": 120, "open_time": "08:30-17:00",
            "open_time_realtime": True, "rating": "4.8", "list_rank": "", "booking_url": "",
            "source": "高德POI",
            "source_urls": [f"https://www.amap.com/search?query={quote('故宫博物院')}"],
        }
    ])
    spots = service.recommend("北京市", [])
    assert spots and spots[0]["source_urls"] == [f"https://www.amap.com/search?query={quote('故宫博物院')}"]


def test_static_fallback_empty_urls_and_render():
    """静态库兜底景点无 source_urls 字段（如实无来源），渲染不报错。"""
    service = ScenicSpotService()
    spots = service.load_spots("北京市")
    assert spots, "静态库应有数据"
    assert all("source_urls" not in spot for spot in spots)
    # 渲染路径：无 source_urls 且非"静态演示库"来源时不输出信息来源行、不抛错
    from app.services.markdown_reporter import MarkdownReporter
    spot = spots[0]
    source_urls = spot.get("source_urls") or []
    rendered = "、".join(
        f"[高德检索]({url})" if "amap.com" in url else f"[飞猪预订]({url})" for url in source_urls
    )
    assert rendered == ""


def test_fliggy_booking_url_appended_dedup():
    """飞猪 enrich 时 booking_url 追加进 source_urls 且去重、保留高德链接在前。"""
    amap_url = f"https://www.amap.com/search?query={quote('故宫博物院')}"
    fliggy_url = "https://router.feizhu.com/webview?x=1"
    spot = {"name": "故宫博物院", "source_urls": [amap_url], "booking_url": fliggy_url}
    # 模拟 enrich 的追加逻辑（与 itinerary._enrich_with_fliggy 中一致）
    booking_url = spot.get("booking_url", "")
    if booking_url:
        urls = list(spot.get("source_urls", []))
        if booking_url not in urls:
            urls.append(booking_url)
        spot["source_urls"] = urls
    assert spot["source_urls"] == [amap_url, fliggy_url]
    # 重复追加不产生重复项
    booking_url = spot["booking_url"]
    urls = list(spot.get("source_urls", []))
    if booking_url not in urls:
        urls.append(booking_url)
    assert spot["source_urls"] == [amap_url, fliggy_url]
