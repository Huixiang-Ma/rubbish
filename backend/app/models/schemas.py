from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    days: int = Field(default=3, ge=1, le=14)
    budget: int = Field(..., ge=0)
    travelers: int = Field(default=2, ge=1, le=20, description="出行人数；预算分项按人数换算（住宿每 2 人一间、打车每 3 人一车）")
    origin: str | None = Field(default=None, description="出发地，用于大交通建议与分项预算；不填则不计大交通")
    departure_date: str | None = Field(default=None, description="出发日期（前端联动传入，供展示和兼容）")
    return_date: str | None = Field(default=None, description="返回日期（前端联动传入，供展示和兼容）")
    customer: str | None = Field(default=None, description="客户归属（toB 顾问工作台用）")
    tenant: str | None = Field(default=None, description="租户标识（B7 多租户演示）")
    mood: str | None = Field(default=None, description="心情词（C7 人生剧本），填写后生成情绪弧线章节")
    preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    user_id: str | None = Field(default=None, description="服务端从 Bearer token 注入，客户端传值会被覆盖")


class PlanListItem(BaseModel):
    job_id: str
    status: str
    current_node: str | None = None
    progress: int = 0
    destination: str | None = None
    origin: str | None = None
    days: int | None = None
    budget: int | None = None
    customer: str | None = None
    error: str | None = None
    version: int = 1
    created_at: str | None = None
    updated_at: str | None = None
    pipeline: str | None = Field(default=None, description="toc / tob，区分游客端与企业端来源")
    travelers: int | None = Field(default=None, description="出行人数")
    user_id: str | None = Field(default=None, description="归属账号（toC 登录用户）")


class PlanListResponse(BaseModel):
    total: int
    items: list[PlanListItem]


class BrandExportRequest(BaseModel):
    brand: str = Field(..., min_length=1, description="企业品牌名（白标交付）")
    consultant: str = Field(..., min_length=1, description="顾问署名")


class FeedbackRequest(BaseModel):
    kind: Literal["praise", "complaint"]
    operator: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class PlanCreateResponse(BaseModel):
    job_id: str
    status: str


class PlanStatusResponse(BaseModel):
    job_id: str
    status: str
    current_agent: str | None = None
    progress: int = 0
    resume_from: str | None = None
    version: int = 1
    error: str | None = None
    parent_job_id: str | None = None
    completed_nodes: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PlanResultResponse(BaseModel):
    job_id: str
    version: int
    travel_plan_md: str
    sha256: str
    itinerary: list[dict] | None = Field(default=None, description="结构化行程（toC 前端携程式视图）：每天 items/meals/legs/weather/fun_tip")
    hotels: list[dict] | None = Field(default=None, description="高德实时酒店列表（含分类/坐标/距市中心），供视图渲染备选住宿")
    economy_tips: list[str] | None = Field(default=None, description="经济实惠建议（超预算压缩口径/默认经济导向说明）")
    user_input: dict | None = Field(default=None, description="原始规划入参（目的地/天数/人数/预算/心情词），供历史行程回看渲染封面口径")


class ApprovalRequest(BaseModel):
    decision: Literal["approve", "reject"]
    operator: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    base_version: int = Field(..., ge=1)


class ApprovalResponse(BaseModel):
    status: str
    next_node: str | None = None


class ReplanRequest(BaseModel):
    change_request: str = Field(..., min_length=1)
    base_version: int = Field(..., ge=1)


class ReplanResponse(BaseModel):
    job_id: str
    parent_job_id: str
    status: str
    replan_mode: str
    diff_summary: dict[str, Any] | None = None


class AgentResult(BaseModel):
    agent: str
    status: str = "ok"
    payload: dict[str, Any] = Field(default_factory=dict)
