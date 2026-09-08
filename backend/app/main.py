from pathlib import Path
import gzip

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.admin import router as admin_router
from app.api.auth import require_admin, router as auth_router
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
app.include_router(rag_router)
app.include_router(auth_router)

# toB 管理类路由：AUTH_ENABLED=true 时强制 Bearer 校验。
# 注意：此处只能注册一次——FastAPI 按注册顺序匹配，若先注册一份无守卫的同名路由，
# 请求会命中无守卫的那份，导致鉴权被绕过。
_auth_deps = [Depends(require_admin)] if get_settings().auth_enabled else []
app.include_router(admin_router, dependencies=_auth_deps)
app.include_router(services_router)

# 本地开发：WL项目/frontend；容器内：/app/frontend。取第一个存在的目录。
_frontend_candidates = [
    Path(__file__).resolve().parents[2] / "frontend",
    Path(__file__).resolve().parents[1] / "frontend",
]
FRONTEND_DIR = next((p for p in _frontend_candidates if p.exists()), _frontend_candidates[0])


# 页面内存缓存（按 mtime 失效）：文件没变时直接命中内存，免去每请求磁盘读取；
# 同时预生成 GZip 字节（gzip 是 CPU 大头，压一次反复用）；
# 前端是 bind-mount，改文件 mtime 变化 → 自动重新读取，不影响"改了即生效"
_page_cache: dict[str, tuple[float, Response, Response]] = {}  # (mtime, 原文版, gzip版)


def _page_variants(filename: str) -> tuple[Response, Response]:
    path = FRONTEND_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="前端页面未打包进当前部署，请直接打开 frontend 目录下的文件。")
    mtime = path.stat().st_mtime
    cached = _page_cache.get(filename)
    if not cached or cached[0] != mtime:
        content = path.read_text(encoding="utf-8")
        base_headers = {"Cache-Control": "no-cache"}
        raw = Response(content=content, media_type="text/html", headers=dict(base_headers))
        gz = Response(
            content=gzip.compress(content.encode("utf-8"), compresslevel=6),
            media_type="text/html",
            headers={**base_headers, "Content-Encoding": "gzip"},
        )
        _page_cache[filename] = (mtime, raw, gz)
    return _page_cache[filename][1], _page_cache[filename][2]


def _read_page(filename: str, request: Request) -> Response:
    raw, gz = _page_variants(filename)
    accepts_gzip = "gzip" in request.headers.get("accept-encoding", "")
    return gz if accepts_gzip else raw


@app.get("/", response_class=HTMLResponse)
def toc_page(request: Request) -> Response:
    """toC 游客端入口。"""
    return _read_page("index.html", request)


@app.get("/b", response_class=HTMLResponse)
def tob_page(request: Request) -> Response:
    """toB 企业端工作台入口。"""
    return _read_page("admin.html", request)


@app.get("/s/{job_id}", response_class=HTMLResponse)
def share_page(job_id: str, request: Request) -> Response:
    """P1.6 行程书只读分享页（免登录；job_id 为 12 位 hash，不可枚举；页面带 noindex）。"""
    return _read_page("share.html", request)


_vendor_dir = FRONTEND_DIR / "vendor"
if _vendor_dir.exists():
    app.mount("/vendor", StaticFiles(directory=str(_vendor_dir)), name="vendor")

_media_dir = FRONTEND_DIR / "media"
if _media_dir.exists():
    app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")


# ----------------------------------------------------------------------------
# 前端 v2（Vue3 + Vite 全新工程，hash 路由，构建产物 frontend-v2/dist）
# 挂载在 /v2 前缀下，与旧版单文件前端并存，互不影响。
# 访问入口：/v2/index.html#/ （toC）、/v2/index.html#/b （toB 工作台）
# ----------------------------------------------------------------------------
_frontend_v2_candidates = [
    Path(__file__).resolve().parents[2] / "frontend-v2" / "dist",
    Path(__file__).resolve().parents[1] / "frontend-v2" / "dist",
]
_frontend_v2_dir = next((p for p in _frontend_v2_candidates if p.exists()), None)
if _frontend_v2_dir:
    app.mount("/v2", StaticFiles(directory=str(_frontend_v2_dir), html=True), name="frontend_v2")


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics_endpoint() -> Response:
    """Prometheus 抓取端点（METRICS_ENABLED=true 时开启）。"""
    if not get_settings().metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
