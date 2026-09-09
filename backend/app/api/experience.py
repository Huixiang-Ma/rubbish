import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.checkpoint_store import CheckpointStore
from app.services.safety_service import SafetyService
from app.services.experience_service import ExperienceService
from app.services.travel_context_service import TravelContextService

router = APIRouter(prefix="/api/plans", tags=["experience"])
store = CheckpointStore()
experience = ExperienceService()
travel = TravelContextService()


class DialogueRequest(BaseModel):
    guide_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class VoteRequest(BaseModel):
    side: str = Field(..., pattern="^(规划方|游客方)$")


def _load_job(job_id: str) -> dict[str, Any]:
    try:
        return store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


@router.get("/{job_id}/map")
def get_map(job_id: str) -> dict[str, Any]:
    """地图模式数据源：每日景点坐标（高德实时 POI 或静态库）。"""
    state = _load_job(job_id)
    outputs = experience.load_outputs(job_id, state)
    days = []
    for day in outputs.get("Itinerary", {}).get("payload", {}).get("itinerary", []):
        spots = [
            {
                "name": item["spot"].get("name", item["title"]),
                "lat": item["spot"].get("lat"),
                "lng": item["spot"].get("lng"),
                "time": item.get("time"),
            }
            for item in day.get("items", [])
            if item.get("spot", {}).get("lat")
        ]
        if spots:
            days.append({"day": day["day"], "theme": day.get("theme", ""), "spots": spots})
    return {"job_id": job_id, "destination": state.get("user_input", {}).get("destination"), "origin": state.get("user_input", {}).get("origin"), "days": days}


@router.get("/{job_id}/nearby")
def get_nearby(job_id: str, kind: str = "food") -> dict[str, Any]:
    """周边服务演示：美食/车位/厕所 POI（静态演示数据 + 距离计算）。"""
    if kind not in {"food", "parking", "toilet"}:
        raise HTTPException(status_code=400, detail="kind must be food|parking|toilet")
    state = _load_job(job_id)
    outputs = experience.load_outputs(job_id, state)
    selected = experience._selected_spots(outputs)[:3]
    pois = []
    for spot in selected:
        pois.extend(travel.nearby_pois(spot, kind))
    pois.sort(key=lambda poi: poi["distance_m"])
    return {"job_id": job_id, "kind": kind, "pois": pois}


@router.get("/geo/ip")
def geo_ip() -> dict[str, Any]:
    """P2 定位兜底：高德 IP 定位（城市级，精度约数公里），供前端三层定位的第二层使用。"""
    from app.services import amap_client
    result = amap_client.ip_location()
    if not result:
        raise HTTPException(status_code=503, detail="IP 定位不可用")
    return result


@router.get("/{job_id}/agent-outputs")
def get_agent_outputs(job_id: str) -> dict[str, Any]:
    """P1.5 流水线角色卡数据源：返回各节点真实产出（名称 → {status, payload}）。"""
    state = _load_job(job_id)
    outputs = experience.load_outputs(job_id, state)
    return {
        "job_id": job_id,
        "outputs": {
            name: {"agent": name, "status": out.get("status"), "payload": out.get("payload")}
            for name, out in outputs.items()
        },
    }


@router.get("/{job_id}/debates")
def get_debates(job_id: str) -> dict[str, Any]:
    """C2 双栏渲染数据源：决策辩论结构化内容。"""
    state = _load_job(job_id)
    outputs = experience.load_outputs(job_id, state)
    debates = outputs.get("Debate", {}).get("payload", {}).get("debates", [])
    return {"job_id": job_id, "debates": debates}


@router.get("/{job_id}/counterfactual")
def get_counterfactual(job_id: str) -> dict[str, Any]:
    """C4 反事实后悔药对照卡。"""
    state = _load_job(job_id)
    return experience.counterfactual(job_id, state)


@router.get("/{job_id}/swarm")
def get_swarm(job_id: str) -> dict[str, Any]:
    """C3 虚拟游客踩点 swarm 反馈。"""
    state = _load_job(job_id)
    return experience.swarm(job_id, state)


@router.get("/{job_id}/guides")
def get_guides(job_id: str) -> dict[str, Any]:
    """C5 角色名导团点评。"""
    state = _load_job(job_id)
    return experience.guides(job_id, state)


@router.post("/{job_id}/dialogue")
def post_dialogue(job_id: str, payload: DialogueRequest) -> dict[str, Any]:
    """P2.5 合规：UGC 输入先过 Prompt 注入/风险扫描，拦截直接 400。"""
    scan = SafetyService().scan_user_input(payload.message)
    if scan.action == "block":
        raise HTTPException(status_code=400, detail="输入包含高风险内容，已被安全策略拦截")
    """C5 名人对话：多轮追问。"""
    state = _load_job(job_id)
    return experience.dialogue(job_id, state, payload.guide_id, payload.message, payload.history)


@router.post("/{job_id}/debate/vote")
def post_vote(job_id: str, payload: VoteRequest) -> dict[str, Any]:
    """C6 直播辩论投票：计票落状态与审计，并写入 travel_plan.md。"""
    state = _load_job(job_id)
    return experience.cast_vote(job_id, state, store, payload.side)


@router.get("/{job_id}/debate/live")
async def debate_live(job_id: str) -> StreamingResponse:
    """C6 直播辩论 SSE 流式：规划方 vs 游客方交替发言。"""
    state = _load_job(job_id)
    messages = experience.live_rounds(job_id, state)

    async def event_stream():
        for message in messages:
            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.15)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
