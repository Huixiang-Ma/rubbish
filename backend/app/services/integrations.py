"""外部能力扩展点（明确不接清单的正式接口层）。

地图/搜索/OCR 目前只有本地 Mock 实现（可用），支付仅保留接口（禁止纳入 MVP）。
未来接入真实供应商时：实现对应 Adapter 并在 registry 注册，业务代码零改动。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings
from app.services.travel_context_service import TravelContextService

_travel = TravelContextService()


class MapAdapter(ABC):
    name = "map"

    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def route(self, origin: str, destination: str) -> dict[str, Any]:
        ...


class LocalMapAdapter(MapAdapter):
    name = "local-haversine"

    def available(self) -> bool:
        return True

    def route(self, origin: str, destination: str) -> dict[str, Any]:
        info = _travel.intercity_advice(origin)
        return {"mode": "local估算", "origin": origin, "destination": destination, "intercity": info}


class RemoteMapAdapter(MapAdapter):
    name = "remote"

    def available(self) -> bool:
        return False  # 明确不接：配置供应商 key 并实现 HTTP 调用后才为 True

    def route(self, origin: str, destination: str) -> dict[str, Any]:
        raise NotImplementedError("地图 API 属明确不接清单，仅保留扩展点。")


class SearchAdapter(ABC):
    name = "search"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]: ...


class MockSearchAdapter(SearchAdapter):
    name = "mock"

    def available(self) -> bool:
        return True

    def search(self, query: str) -> list[dict[str, Any]]:
        return [{"title": f"「{query}」相关演示攻略", "source": "本地静态库", "note": "演示数据，非真实搜索"}]


class OcrAdapter(ABC):
    name = "ocr"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def recognize(self, image_ref: str) -> dict[str, Any]: ...


class MockOcrAdapter(OcrAdapter):
    name = "mock"

    def available(self) -> bool:
        return True

    def recognize(self, image_ref: str) -> dict[str, Any]:
        tags = ["古建筑", "自然风光", "美食街市"]
        picked = tags[len(image_ref) % len(tags)]
        return {"text_hint": picked, "note": "演示 mock，未调用真实视觉模型"}


class PaymentAdapter(ABC):
    name = "payment"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def create_order(self, amount: int, subject: str) -> dict[str, Any]: ...


class DisabledPaymentAdapter(PaymentAdapter):
    name = "disabled"

    def available(self) -> bool:
        return False  # 支付/订单 API 禁止纳入 MVP，仅保留扩展点

    def create_order(self, amount: int, subject: str) -> dict[str, Any]:
        raise NotImplementedError("支付/订单 API 禁止纳入 MVP，仅保留扩展点。")


def build_registry() -> dict[str, Any]:
    settings = get_settings()
    map_adapter: MapAdapter = LocalMapAdapter() if settings.external_map_provider == "local" else RemoteMapAdapter()
    return {
        "map": map_adapter,
        "search": MockSearchAdapter(),
        "ocr": MockOcrAdapter(),
        "payment": DisabledPaymentAdapter(),
    }


def status() -> dict[str, Any]:
    registry = build_registry()
    return {
        name: {
            "implementation": adapter.name,
            "available": adapter.available(),
        }
        for name, adapter in registry.items()
    }
