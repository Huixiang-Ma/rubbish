import difflib
import json
import shutil
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from pydantic import BaseModel

from app.api.auth import bearer_token, require_role, require_traveler
from app.services import auth_service

from app.config import get_settings

from app.models.schemas import (
    ApprovalRequest,
    ApprovalResponse,
    BrandExportRequest,
    FeedbackRequest,
    PlanCreateResponse,
    PlanListResponse,
    PlanRequest,
    PlanResultResponse,
    PlanStatusResponse,
    ReplanRequest,
    ReplanResponse,
)
from app.models.states import JobStatus
from app.services import job_index
from app.services.atomic_writer import AtomicWriter
from app.services.checkpoint_store import CheckpointStore
from app.services.hash_utils import request_hash
from app.services.jsonlog import log_event
from app.services.metrics import APPROVALS, PLAN_SUBMITS
from app.services.markdown_reporter import MarkdownReporter
from app.services.paths import DATA_ROOT, job_dir
from app.services.queue_client import queue_client
from app.services.safety_service import SafetyService
from app.services.travel_context_service import TravelContextService

router = APIRouter(prefix="/api/plans", tags=["plans"])
store = CheckpointStore()
reporter = MarkdownReporter()
request_index: dict[str, str] = {}

APPROVABLE_STATUSES = {
    JobStatus.WAITING_BUDGET_APPROVAL.value,
    JobStatus.WAITING_SAFETY_REVIEW.value,
}
PLAN_GENERATION_VERSION = "geo_cluster_v19"


# ---------- P2.2 任务归属 / P2.4b 配额 ----------

def _optional_traveler(request: Request) -> str | None:
    """从 Bearer token 解析 toC 用户名；未登录/无效 token 一律 None（游客单）。"""
    try:
        payload = auth_service.verify_token(bearer_token(request))
        if payload and payload.get("r") == "traveler":
            return payload.get("u")
    except Exception:
        pass
    return None


def _quota_checker():
    """Redis 每日免费额度：INCR + 当日过期；Redis 不可用时放行（不阻断主链路）。"""
    settings = get_settings()
    limit = max(1, settings.free_plan_per_day)
    redis = None
    try:
        from redis import Redis
        redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    except Exception:
        redis = None
    day = datetime.now().strftime("%Y%m%d")

    def check(scope: str, ident: str) -> None:
        if redis is None:
            return
        key = f"quota:{scope}:{ident}:{day}"
        try:
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, 90000)
            if count > limit:
                raise HTTPException(status_code=429, detail=f"今日免费规划额度已用完（{limit} 单/天），明天再来或联系客服升级")
        except HTTPException:
            raise
        except Exception:
            return

    return check


_check_quota = _quota_checker()


def _list_item(state: dict) -> dict:
    user_input = state.get("user_input", {})
    return {
        "job_id": state.get("job_id"),
        "status": state.get("status", "UNKNOWN"),
        "current_node": state.get("current_node"),
        "progress": state.get("progress", 0),
        "destination": user_input.get("destination"),
        "origin": user_input.get("origin"),
        "days": user_input.get("days"),
        "departure_date": user_input.get("departure_date"),
        "return_date": user_input.get("return_date"),
        "budget": user_input.get("budget"),
        "customer": state.get("customer"),
        "error": state.get("error"),
        "version": state.get("version", 1),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
        "pipeline": state.get("pipeline"),
        "travelers": user_input.get("travelers"),
        "user_id": state.get("user_id"),
    }


@router.post("", response_model=PlanCreateResponse)
def create_plan(payload: PlanRequest, request: Request) -> PlanCreateResponse:
    # P2.2 归属：服务端从 token 注入 user_id（客户端传值一律覆盖）；P2.4b：登录按账号、游客按 IP 计免费额度
    user_id = _optional_traveler(request)
    payload.user_id = user_id
    client_ip = request.client.host if request.client else "unknown"
    _check_quota("user" if user_id else "ip", user_id or client_ip)
    data = payload.model_dump()
    hash_data = {**data, "_generation_version": PLAN_GENERATION_VERSION}
    digest = request_hash(hash_data)
    job_id = f"plan_{digest[:12]}"
    request_index[digest] = job_id
    if store.exists(job_id):
        state = store.load(job_id)
        return PlanCreateResponse(job_id=job_id, status=state.get("status", JobStatus.QUEUED.value))
    store.create(job_id, data, digest)
    state = store.load(job_id)
    if payload.customer or payload.tenant or user_id:
        if payload.customer:
            state["customer"] = payload.customer
        if payload.tenant:
            state["tenant"] = payload.tenant
        if user_id:
            state["user_id"] = user_id
        store.save(job_id, state)
    queue_client.enqueue(job_id)
    PLAN_SUBMITS.inc()
    log_event(
        "job_created",
        job_id=job_id,
        destination=payload.destination,
        days=payload.days,
        budget=payload.budget,
        departure_date=payload.departure_date,
        return_date=payload.return_date,
    )
    return PlanCreateResponse(job_id=job_id, status=JobStatus.QUEUED.value)


@router.get("/mine", response_model=PlanListResponse)
def list_my_plans(user: dict = Depends(require_traveler)) -> PlanListResponse:
    """P2.2 toC 历史云端化：当前登录用户的任务列表（按更新时间倒序）。"""
    username = user.get("u")
    items = [_list_item(state) for state in job_index.iter_states(DATA_ROOT) if state.get("user_id") == username]
    items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return PlanListResponse(total=len(items), items=items)


class PlanClaimRequest(BaseModel):
    job_ids: list[str]


@router.post("/claim")
def claim_plans(payload: PlanClaimRequest, user: dict = Depends(require_traveler)) -> dict:
    """P2.2 游客单认领：把近 72 小时内、尚无归属的任务绑定到当前登录账号。"""
    from datetime import datetime as _dt

    username = user.get("u")
    claimed, skipped = [], []
    cutoff = _dt.now(timezone.utc) - timedelta(hours=72)
    for job_id in payload.job_ids[:50]:
        try:
            state = store.load(job_id)
        except Exception:
            skipped.append({"job_id": job_id, "reason": "not_found"})
            continue
        if state.get("user_id"):
            skipped.append({"job_id": job_id, "reason": "already_owned"})
            continue
        created = state.get("created_at")
        try:
            created_dt = _dt.fromisoformat(created.replace("Z", "+00:00")) if created else None
        except ValueError:
            created_dt = None
        if created_dt and created_dt < cutoff:
            skipped.append({"job_id": job_id, "reason": "expired"})
            continue
        state["user_id"] = username
        store.save(job_id, state)
        claimed.append(job_id)
    log_event("plans_claimed", user=username, claimed=claimed, skipped=len(skipped))
    return {"claimed": claimed, "skipped": skipped}


@router.get("", response_model=PlanListResponse)
def list_plans(
    request: Request,
    status: str | None = None,
    customer: str | None = None,
    tenant: str | None = None,
    limit: int = 100,
) -> PlanListResponse:
    """B1 顾问工作台：本地任务索引列表（状态/客户/租户筛选，按更新时间倒序）。
    P2.3 多租户隔离：AUTH_ENABLED=true 时，携带主管/顾问 token 的请求被强制限定在本租户，仅管理员可见全部。"""
    settings = get_settings()
    if settings.auth_enabled:
        import app.services.auth_service as _auth
        payload = _auth.verify_token(bearer_token(request))
        if payload and payload.get("r") in ("supervisor", "consultant") and payload.get("t"):
            tenant = payload["t"]  # 数据隔离：覆盖查询参数，防止越权查看其他租户
    items: list[dict] = []
    for state in job_index.iter_states(DATA_ROOT):
        if status and state.get("status") != status:
            continue
        if customer and state.get("customer") != customer:
            continue
        if tenant and state.get("tenant") != tenant:
            continue
        items.append(_list_item(state))
    items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    items = items[: max(1, min(limit, 500))]
    return PlanListResponse(total=len(items), items=items)


@router.get("/{job_id}/audit")
def get_plan_audit(job_id: str) -> dict:
    try:
        store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    audit_path = job_dir(job_id) / "audit.log"
    events: list[dict] = []
    if audit_path.exists():
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"job_id": job_id, "events": events}


@router.post("/{job_id}/feedback")
def submit_feedback(job_id: str, payload: FeedbackRequest, _role: dict = Depends(require_role("consultant", "supervisor", "admin"))) -> dict:
    scan = SafetyService().scan_user_input(payload.content)
    if scan.action == "block":
        raise HTTPException(status_code=400, detail="反馈内容包含高风险内容，已被安全策略拦截")
    """B4 反馈通道（吸收原型"填写好评/填写投诉"），落审计日志。"""
    try:
        store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    store.append_audit(
        job_id,
        {
            "action": "feedback",
            "kind": payload.kind,
            "operator": payload.operator,
            "content": payload.content,
        },
    )
    return {"job_id": job_id, "recorded": True}


@router.post("/{job_id}/export")
def export_branded_plan(job_id: str, payload: BrandExportRequest) -> dict:
    """B5 白标交付：注入企业品牌/顾问署名后另存，交付记录落审计。"""
    try:
        state = store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    source = job_dir(job_id) / "travel_plan.md"
    if not source.exists():
        raise HTTPException(status_code=404, detail="result not found")
    markdown = source.read_text(encoding="utf-8")
    digest_line = state.get("file_hash", "")
    now = datetime.now(timezone.utc).isoformat()
    branded = "\n".join(
        [
            "---",
            f"企业品牌：{payload.brand}",
            "> 中立声明：本方案由中立规划引擎生成，不绑定任何供应链、不参与返佣分成，推荐结果不受库存利益影响。",
            "（Logo 占位：替换为企业标识）",
            f"顾问署名：{payload.consultant}",
            f"导出时间：{now}",
            f"原稿校验（sha256）：{digest_line}",
            "交付留痕：本文件由多 Agent 文旅系统导出，交付记录已写入审计日志。",
            "---",
            "",
            markdown,
        ]
    )
    writer = AtomicWriter()
    branded_digest = writer.write_text(job_dir(job_id) / "travel_plan_branded.md", branded)
    store.append_audit(
        job_id,
        {
            "action": "export",
            "brand": payload.brand,
            "consultant": payload.consultant,
            "file": "travel_plan_branded.md",
            "sha256": branded_digest,
        },
    )
    return {"file": "travel_plan_branded.md", "sha256": branded_digest, "markdown": branded}


@router.get("/{job_id}/diff")
def get_plan_diff(job_id: str, base: str | None = None) -> dict:
    """Return a bounded line-level comparison of a replanned job and its parent."""
    try:
        state = store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    parent_job_id = base or state.get("parent_job_id")
    if not parent_job_id:
        raise HTTPException(status_code=400, detail="NOT_A_REPLAN：该任务无父版本，无法对比")

    parent_path = job_dir(parent_job_id) / "travel_plan.md"
    child_path = job_dir(job_id) / "travel_plan.md"
    if not parent_path.exists() or not child_path.exists():
        raise HTTPException(status_code=404, detail="travel_plan.md 尚未生成，无法对比")

    parent_lines = parent_path.read_text(encoding="utf-8").splitlines()
    child_lines = child_path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, str]] = []
    added = removed = unchanged = 0
    matcher = difflib.SequenceMatcher(a=parent_lines, b=child_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            for line in parent_lines[i1:i2]:
                rows.append({"type": "del", "text": line})
                removed += 1
        if tag in ("insert", "replace"):
            for line in child_lines[j1:j2]:
                rows.append({"type": "add", "text": line})
                added += 1
        if tag == "equal":
            for line in parent_lines[i1:i2]:
                rows.append({"type": "same", "text": line})
                unchanged += 1

    return {
        "job_id": job_id,
        "parent_job_id": parent_job_id,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "truncated": len(rows) > 2000,
        "lines": rows[:2000],
    }


@router.get("/{job_id}", response_model=PlanStatusResponse)
def get_plan_status(job_id: str) -> PlanStatusResponse:
    try:
        state = store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    return PlanStatusResponse(
        job_id=job_id,
        status=state["status"],
        current_agent=state.get("current_node"),
        progress=state.get("progress", 0),
        resume_from=state.get("resume_from"),
        version=state.get("version", 1),
        error=state.get("error"),
        parent_job_id=state.get("parent_job_id"),
        completed_nodes=state.get("completed_nodes"),
        created_at=state.get("created_at"),
        updated_at=state.get("updated_at"),
    )


@router.get("/{job_id}/result", response_model=PlanResultResponse)
def get_plan_result(job_id: str) -> PlanResultResponse:
    try:
        state = store.load(job_id)
        markdown, digest = reporter.read_result(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="result not found") from exc
    # 结构化行程 + 实时酒店：供 toC 前端渲染携程式行程详情视图（旧 job / toB 口径无此字段）
    itinerary = None
    itinerary_relative = state.get("agent_outputs", {}).get("Itinerary")
    if itinerary_relative:
        try:
            output = json.loads((job_dir(job_id) / itinerary_relative).read_text(encoding="utf-8"))
            itinerary = output.get("payload", {}).get("itinerary")
        except (OSError, ValueError):
            itinerary = None
    hotels = None
    try:
        hotels = TravelContextService().hotels(state.get("user_input", {}).get("destination", "北京")).get("hotels") or None
    except Exception:
        hotels = None
    economy_tips = None
    # 经济贴士：新管线由 Budget 节点产出；旧任务兜底读 Validator 历史字段
    budget_relative = state.get("agent_outputs", {}).get("Budget")
    if budget_relative:
        try:
            budget_output = json.loads((job_dir(job_id) / budget_relative).read_text(encoding="utf-8"))
            economy_tips = budget_output.get("payload", {}).get("economy_tips")
        except (OSError, ValueError):
            economy_tips = None
    if economy_tips is None:
        validator_relative = state.get("agent_outputs", {}).get("Validator")
        if validator_relative:
            try:
                validator_output = json.loads((job_dir(job_id) / validator_relative).read_text(encoding="utf-8"))
                economy_tips = validator_output.get("payload", {}).get("economy_tips")
            except (OSError, ValueError):
                economy_tips = None
    return PlanResultResponse(
        job_id=job_id,
        version=state.get("version", 1),
        travel_plan_md=markdown,
        sha256=digest,
        itinerary=itinerary,
        hotels=hotels,
        economy_tips=economy_tips,
        user_input=state.get("user_input"),
    )


@router.post("/{job_id}/approval", response_model=ApprovalResponse)
def approve_plan(job_id: str, payload: ApprovalRequest, _role: dict = Depends(require_role("supervisor", "admin"))) -> ApprovalResponse:
    try:
        state = store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    if payload.base_version != state.get("version", 1):
        raise HTTPException(status_code=409, detail="VERSION_CONFLICT")
    if state.get("status") not in APPROVABLE_STATUSES:
        raise HTTPException(status_code=409, detail="INVALID_STATE")
    was_safety_hold = state["status"] == JobStatus.WAITING_SAFETY_REVIEW.value
    store.append_audit(
        job_id,
        {
            "action": "approval",
            "decision": payload.decision,
            "operator": payload.operator,
            "reason": payload.reason,
            "base_version": payload.base_version,
        },
    )
    if payload.decision == "reject":
        state["status"] = JobStatus.REPLAN_REQUIRED.value
    else:
        state["status"] = JobStatus.RUNNING.value
        state["error"] = None
        if was_safety_hold:
            state["safety_reviewed"] = True
    state["version"] = state.get("version", 1) + 1
    store.save(job_id, state)
    APPROVALS.labels(decision=payload.decision).inc()
    log_event("approval", job_id=job_id, decision=payload.decision, operator=payload.operator)
    if payload.decision == "reject":
        return ApprovalResponse(status=JobStatus.REPLAN_REQUIRED.value, next_node=None)
    queue_client.enqueue(job_id)
    return ApprovalResponse(status="APPROVED", next_node=state.get("resume_from"))


@router.post("/{job_id}/replan", response_model=ReplanResponse)
def replan(job_id: str, payload: ReplanRequest, request: Request) -> ReplanResponse:
    try:
        state = store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    # P2 精准修改权限：toB 角色，或该行程书的 toC 归属用户（无归属的老任务允许任意登录游客）
    token = bearer_token(request)
    actor = auth_service.verify_token(token) if token else None
    if not actor:
        raise HTTPException(status_code=401, detail="需要登录")
    role_ok = actor.get("r") in ("consultant", "supervisor", "admin")
    owner_ok = actor.get("r") == "traveler" and (not state.get("user_id") or state.get("user_id") == actor.get("u"))
    if not (role_ok or owner_ok):
        raise HTTPException(status_code=403, detail="FORBIDDEN_ROLE")
    if payload.base_version != state.get("version", 1):
        raise HTTPException(status_code=409, detail="VERSION_CONFLICT")
    new_input = dict(state["user_input"])
    new_input["constraints"] = list(new_input.get("constraints", [])) + [payload.change_request]
    digest = request_hash({"parent_job_id": job_id, **new_input})
    new_job_id = f"plan_{digest[:12]}"
    diff_summary = {
        "mode": "constraints_append",
        "changed_fields": ["constraints"],
        "added_constraints": [payload.change_request],
        "parent_job_id": job_id,
        "parent_version": state.get("version", 1),
    }
    if store.exists(new_job_id):
        existing = store.load(new_job_id)
        return ReplanResponse(
            job_id=new_job_id,
            parent_job_id=job_id,
            status=existing.get("status", JobStatus.QUEUED.value),
            replan_mode="incremental_by_request",
            diff_summary=diff_summary,
        )
    store.create(new_job_id, new_input, digest)
    child_state = store.load(new_job_id)
    child_state["parent_job_id"] = job_id
    store.save(new_job_id, child_state)
    # S4 节点级增量：目的地/天数/偏好未变时，Researcher/Planner/Itinerary 均不读 constraints，
    # 可安全复用父任务输出，只重算 Validator/Debate/Reporter 受影响链。
    parent_input = state["user_input"]
    if (
        parent_input.get("destination") == new_input.get("destination")
        and parent_input.get("days") == new_input.get("days")
        and parent_input.get("preferences") == new_input.get("preferences")
    ):
        reusable = [name for name in ("Researcher", "Planner", "Itinerary") if name in state.get("agent_outputs", {})]
        reused_relative: dict[str, str] = {}
        for name in reusable:
            source_output = job_dir(job_id) / state["agent_outputs"][name]
            if not source_output.exists():
                continue
            target_output = job_dir(new_job_id) / "agent_outputs" / source_output.name
            target_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_output, target_output)
            reused_relative[name] = f"agent_outputs/{source_output.name}"
        if reused_relative:
            new_state = store.load(new_job_id)
            new_state["completed_nodes"] = list(reused_relative.keys())
            new_state["agent_outputs"] = reused_relative
            new_state["resume_from"] = "Validator"
            new_state["progress"] = 64
            store.save(new_job_id, new_state)
            store.append_audit(
                job_id,
                {"action": "incremental_reuse", "reused_nodes": list(reused_relative.keys()), "child_job_id": new_job_id},
            )
    queue_client.enqueue(new_job_id)
    return ReplanResponse(
        job_id=new_job_id,
        parent_job_id=job_id,
        status=JobStatus.QUEUED.value,
        replan_mode="incremental_by_request",
        diff_summary=diff_summary,
    )
