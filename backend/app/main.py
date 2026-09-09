from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.admin import router as admin_router
from app.api.assist import router as assist_router
from app.api.auth import require_admin, router as auth_router
from app.api.catalog import router as catalog_router
from app.api.commerce import router as commerce_router
from app.api.composer import router as composer_router
from app.api.material import router as material_router
from app.api.experience import router as experience_router
from app.api.integrations import router as integrations_router
from app.api.plans import router as plans_router
from app.api.rag import router as rag_router
from app.api.routes import router as routes_router
from app.api.safety import router as safety_router
from app.api.services import router as services_router
from app.services.jsonlog import log_event
from app.services.queue_client import queue_client
from app.config import get_settings
from app.services.recovery import recover_pending_jobs
from app.workers.plan_worker import plan_worker

app = FastAPI(title="Multi-Agent Travel Planner MVP")

# HTML/JSON 响应压缩：首页 165KB → ~35KB，显著降低传输与序列化耗时
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    # 认证走 Bearer 头而非 Cookie，无需凭据模式；通配源 + allow_credentials=True
    # 是 CORS 规范中的无效组合（浏览器会拒绝带凭据请求），这里显式关闭凭据。
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans_router)
app.include_router(safety_router)
app.include_router(experience_router)
app.include_router(integrations_router)
app.include_router(routes_router)
app.include_router(catalog_router)
app.include_router(composer_router)
app.include_router(commerce_router)
app.include_router(material_router)
app.include_router(rag_router)
app.include_router(assist_router)
app.include_router(auth_router)

# toB 管理类路由：AUTH_ENABLED=true 时强制 Bearer 校验。
# 注意：此处只能注册一次——FastAPI 按注册顺序匹配，若先注册一份无守卫的同名路由，
# 请求会命中无守卫的那份，导致鉴权被绕过。
_auth_deps = [Depends(require_admin)] if get_settings().auth_enabled else []
app.include_router(admin_router, dependencies=_auth_deps)
app.include_router(services_router)


@app.get("/b")
def tob_redirect() -> Response:
    """toB 企业端入口：旧路径重定向到 hash 路由。"""
    return RedirectResponse(url="/#/b", status_code=307)


@app.get("/s/{job_id}")
def share_redirect(job_id: str) -> Response:
    """行程书只读分享页：旧 /s/{job_id} 重定向到 hash 路由。"""
    return RedirectResponse(url=f"/#/s/{job_id}", status_code=307)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics_endpoint() -> Response:
    """Prometheus 抓取端点（METRICS_ENABLED=true 时开启）。"""
    if not get_settings().metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/internal/alerts/feishu")
async def alerts_feishu_bridge(request: Request) -> dict:
    """P3.2 告警桥接：接收 Alertmanager webhook，转译为飞书群消息。

    仅供 compose 内网 Alertmanager 调用；Bearer token 校验防公网滥用。
    始终返回 200，避免 Alertmanager 对失败告警疯狂重试。
    """
    auth = request.headers.get("authorization", "")
    import os as _os
    expected = "Bearer " + _os.environ.get("ALERT_BRIDGE_TOKEN", "alert-bridge-change-me")
    if auth != expected:
        return {"status": "forbidden"}
    try:
        body = await request.json()
    except Exception:
        return {"status": "bad_request"}
    from app.services.notify import send_feishu_text
    lines = []
    for alert in body.get("alerts", [])[:10]:
        labels = alert.get("labels", {})
        anno = alert.get("annotations", {})
        raw_status = alert.get("status")
        status = raw_status.get("state") if isinstance(raw_status, dict) else (raw_status or "firing")
        lines.append(f"【{labels.get('severity', 'info').upper()}】{labels.get('alertname', 'Alert')} {status} | {anno.get('summary', '')}")
    if lines:
        text = "[文旅系统告警]\n" + "\n\n".join(lines)
        delivered = send_feishu_text(text)
        log_event("alert_bridge", alerts=len(lines), delivered=delivered)
    return {"status": "ok"}


@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    # 口径说明：pg_mirror 为懒初始化，enabled 要到首次写库才翻转；启动时如实报告"是否已配置"
    log_event("app_startup", queue_backend=settings.queue_backend, worker_count=settings.worker_count, pg_mirror_configured=bool(settings.database_url))
    # 后台预热任务索引：任务量大（数百+）时冷扫描要几十秒，不能让首个列表请求扛
    try:
        from app.services import job_index
        job_index.warmup()
    except Exception:
        log_event("job_index_warmup_failed")
    summary = recover_pending_jobs(queue_client)
    if summary["recovered"] or summary["corrupted"]:
        log_event("recovery", recovered=summary["recovered"], corrupted=summary["corrupted"], requeued=summary.get("requeued"))
    plan_worker.start()


@app.on_event("shutdown")
def shutdown() -> None:
    plan_worker.stop()


# ----------------------------------------------------------------------------
# 前端（Vue3 + Vite 构建产物，hash 路由，构建目录 frontend-v2/dist）：
#   本地开发 → WL项目/frontend-v2/dist；容器内 → /app/web（compose bind-mount）。
#   toC 游客端入口 /、toB 工作台 /#/b、行程分享页 /#/s/{job_id}。
#   旧版单文件前端已整体移除；/b、/s/{job_id} 旧书签保留为 307 重定向。
#   挂载必须放在所有 API 路由之后：mount("/") 是通配兜底，先注册会把
#   其后声明的 /health、/metrics 等一并吞掉（曾导致健康检查 404）。
# ----------------------------------------------------------------------------
_web_candidates = [
    Path(__file__).resolve().parents[2] / "frontend-v2" / "dist",
    Path(__file__).resolve().parents[1] / "web",
]
WEB_DIR = next((p for p in _web_candidates if p.exists()), None)

if WEB_DIR:
    # /v2 别名保留给存量书签与截图脚本（同一份产物，base='/' 绝对路径可复用）。
    app.mount("/v2", StaticFiles(directory=str(WEB_DIR), html=True), name="web_v2_alias")
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
else:
    log_event("web_dir_missing", hint="frontend-v2 未构建，仅 API 可用：先执行 cd frontend-v2 && npm run build")
