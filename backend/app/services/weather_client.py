"""双源天气服务：和风（主）+ Open-Meteo（备）。

weather_3d(location) 先走和风，未配置/失败/超限自动切换 Open-Meteo；
is_ready() 双源任一可用即 True，供行程/出行上下文链路做前置判断。
输出结构与 qweather_client.weather_3d 完全一致；last_source_label()
返回本次实际生效的数据源名称（和风天气 / Open-Meteo），供展示层标注口径。
"""
from __future__ import annotations

from typing import Any

from app.services import open_meteo_client, qweather_client

_SOURCE_LABELS = {"qweather": "和风天气", "open_meteo": "Open-Meteo"}
_last_source = "qweather"


def is_ready() -> bool:
    return qweather_client.is_ready() or open_meteo_client.is_ready()


def last_source_label() -> str:
    return _SOURCE_LABELS.get(_last_source, _last_source)


def weather_3d(location: str) -> list[dict[str, Any]] | None:
    global _last_source
    daily = qweather_client.weather_3d(location)
    if daily:
        _last_source = "qweather"
        return daily
    daily = open_meteo_client.weather_3d(location)
    if daily:
        _last_source = "open_meteo"
    return daily
