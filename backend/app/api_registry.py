"""统一外部 API 配置中心：所有真实化要接的 API 端点、密钥环境变量、启停与降级策略集中在这一个文件。

使用方式：
- 业务代码统一通过 ``get_api_config("amap")`` 读取，不要散落 os.getenv；
- 未启用的 API（无密钥或显式关闭）业务侧回退现有 mock 演示口径（fallback="mock"）；
- 新增真实 API：在本文件 API_PROVIDERS 加一个条目，并在 .env.example 增加对应密钥变量即可。

密钥只放环境变量（.env / compose），不入库不进前端。本地零配置时全部 provider 自动降级 mock。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv


def load_env_file(path: str | None = None) -> bool:
    """加载 .env 密钥文件，让本地裸跑与 docker compose 共用同一份配置。

    默认从当前目录向上查找 .env（覆盖在 backend/ 目录启动的场景）；
    override=False：进程已有环境变量（compose 注入/手工 export）优先于 .env 文件。
    """
    if path is None:
        candidates = [Path.cwd(), *Path.cwd().parents]
        found = next((c / ".env" for c in candidates if (c / ".env").is_file()), None)
        if found is None:
            return False
        path = str(found)
    return load_dotenv(path, override=False)


# 导入即加载一次：业务代码只管 get_api_config / is_ready，无需关心加载时机
load_env_file()


@dataclass(frozen=True)
class ApiConfig:
    """单个外部 API 的统一配置条目。"""

    name: str
    category: str  # llm | map | weather | ticket | hotel | dining | safety | payment
    description: str
    base_url: str
    key_envs: tuple[str, ...]  # 就绪所需全部环境变量名（密钥/凭证）
    enabled_env: str | None = None  # 可选：显式启停开关的环境变量名（值 true/false）
    base_url_env: str | None = None  # 可选：专属 API Host 环境变量名（如和风天气按项目分配域名）
    timeout_seconds: float = 10.0
    max_retries: int = 2
    fallback: str = "mock"  # 未启用或调用失败时的回退口径
    docs_url: str = ""
    api_key: str = ""  # 由 load_api_configs() 从环境注入，勿手工填写
    enabled: bool = False  # 由 load_api_configs() 按密钥与开关计算


# ---------- 全部外部 API 声明（真实化改造按需启用，密钥走环境变量） ----------

_API_DECLARATIONS: tuple[dict, ...] = (
    # LLM 生成（现有 LLM_MODE=real 链路，已在 llm_client.py 落地）
    {
        "name": "llm",
        "category": "llm",
        "description": "OpenAI 兼容大模型（通义千问/DeepSeek/GPT），驱动 6 Agent 真实生成",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "key_envs": ("LLM_API_KEY",),
        "enabled_env": "LLM_MODE",  # 仅 real 模式启用
        "timeout_seconds": 30.0,
        "max_retries": 2,
        "docs_url": "https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope",
    },
    # 高德开放平台：POI 检索（景点/餐饮）/ 路径规划 / 地理编码，一个 key 覆盖地图与餐饮推荐
    {
        "name": "amap",
        "category": "map",
        "description": "高德开放平台：景点与餐饮 POI 检索、驾车公交路径规划、地理编码（地图+餐饮同一 API）",
        "base_url": "https://restapi.amap.com",
        "key_envs": ("AMAP_API_KEY",),
        "timeout_seconds": 15.0,  # TLS 握手在部分网络环境下偏慢，放宽以降低瞬时抖动失败
        "docs_url": "https://lbs.amap.com/api/webservice/summary",
    },
    # 和风天气：实时天气 + 逐日预报（替换四季演示样例）
    # 注意：新版和风为每个项目分配专属 API Host（控制台-设置 查看），通过 QWEATHER_API_HOST 覆盖默认域名
    {
        "name": "qweather",
        "category": "weather",
        "description": "和风天气：实时天气与逐日预报，供行程与翻车预演使用",
        "base_url": "https://devapi.qweather.com/v7",
        "key_envs": ("QWEATHER_API_KEY",),
        "base_url_env": "QWEATHER_API_HOST",
        "docs_url": "https://dev.qweather.com/docs/",
    },
    # Open-Meteo：全球天气灾备双源（和风主源未配置/失败/超限时自动切换）。
    # 非商用免密钥（1 万次/天，CC BY 4.0）；商用需订阅付费 endpoint。
    {
        "name": "open_meteo",
        "category": "weather_backup",
        "description": "Open-Meteo：免密钥全球天气灾备源，和风失败时自动切换（非商用免费，商用需订阅）",
        "base_url": "https://api.open-meteo.com",
        "key_envs": (),  # 免密钥公开服务，无凭证要求
        "timeout_seconds": 10.0,
        "docs_url": "https://open-meteo.com/en/docs",
    },
    # 飞猪开放平台（淘宝开放平台 alitrip）：酒店查询/房价 + 门票商品（同一 appkey 覆盖）
    # 关键 API：taobao.xhotel.get（酒店查询）、taobao.xhotel.baseinfo.room.get（房型房价）、
    #          taobao.xhotel.rate.get / multiplerate.get（房价报价）、alitrip.ticket.scenic.query / product.query（门票商品）
    # 注意：火车票/机票在该平台仅代理商履约接口（出票/退票/改签），无搜索报价 API；行程书中的车次/航班展示保留演示口径或引导官方渠道
    {
        "name": "fliggy",
        "category": "ticket",
        "description": "飞猪开放平台：酒店查询与房价报价（taobao.xhotel.*）、门票商品查询（alitrip.ticket.*），同一 appkey 覆盖住宿+门票",
        "base_url": "https://open.alitrip.com",
        "key_envs": ("TAOBAO_APP_KEY", "TAOBAO_APP_SECRET"),
        "docs_url": "https://open.alitrip.com/docs/api_list.htm?cid=20540",
    },
    # 飞猪AI开放平台：MCP 协议（Streamable HTTP）搜索服务，正式 API Key 鉴权
    # 能力：search_poi（景点/榜单/门票/预订链接）、ai_search（语义搜索，含细分开放时间）等 8 个工具
    {
        "name": "fliggy_ai",
        "category": "ticket",
        "description": "飞猪AI开放平台（MCP）：景点榜单/门票信息/飞猪预订链接/语义搜索，补充高德没有的榜单与预订数据",
        "base_url": "https://flyai.open.fliggy.com/mcp",
        "key_envs": ("FLIGGY_AI_API_KEY",),
        "base_url_env": "FLIGGY_AI_MCP_URL",
        "docs_url": "https://flyai.open.fliggy.com/",
    },
    # 携程问道：携程旅游大模型，OpenAI 兼容接口（chat/completions）
    # 用途：生成备选 LLM（多供应商互备）、行程问答/名导团对话等旅游语义场景
    # 注意：接入点与模型名以携程问道开放平台控制台为准（每个租户分配专属网关域名，同和风模式）
    {
        "name": "ctrip_wendao",
        "category": "llm",
        "description": "携程问道旅游大模型（OpenAI 兼容）：行程语义问答与生成备选 LLM，旅游垂直语料口径",
        "base_url": "https://wendao.ctrip.com/openai/v1",  # 占位：以控制台分配的网关地址为准，用 CTRIP_WENDAO_BASE_URL 覆盖
        "key_envs": ("CTRIP_WENDAO_API_KEY",),
        "base_url_env": "CTRIP_WENDAO_BASE_URL",
        "timeout_seconds": 30.0,
        "docs_url": "https://pages.ctrip.com/commerce-promote/202208/other/wendao/",
    },

    # 阿里云内容安全：替换正则注入检测（可选增强）
    {
        "name": "aliyun_content_safety",
        "category": "safety",
        "description": "阿里云内容安全：文本审核，增强现有 Prompt 注入正则检测",
        "base_url": "https://green.cn-shanghai.aliyuncs.com",
        "key_envs": ("ALIYUN_ACCESS_KEY_ID", "ALIYUN_ACCESS_KEY_SECRET"),
        "docs_url": "https://help.aliyun.com/zh/content-safety/",
    },
)

API_PROVIDERS: dict[str, ApiConfig] = {
    item["name"]: ApiConfig(**item) for item in _API_DECLARATIONS
}


def _truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_api_configs() -> dict[str, ApiConfig]:
    """读取当前环境变量，计算每个 API 的密钥与启用状态（每次调用都刷新，便于测试与热更新）。"""
    configs: dict[str, ApiConfig] = {}
    for name, base in API_PROVIDERS.items():
        keys = [os.environ.get(env, "").strip() for env in base.key_envs]
        keys_ready = all(keys)
        base_url = base.base_url
        if base.base_url_env:
            host_override = os.environ.get(base.base_url_env, "").strip()
            if host_override:
                base_url = host_override
        if base.enabled_env:
            switch = os.environ.get(base.enabled_env)
            if base.name == "llm":
                # LLM 特例：LLM_MODE=real 才启用
                enabled = keys_ready and str(switch or "").strip().lower() == "real"
            else:
                enabled = keys_ready if switch is None else (keys_ready and _truthy(switch))
        else:
            enabled = keys_ready
        configs[name] = replace(
            base,
            api_key=keys[0] if keys else "",
            enabled=enabled,
            base_url=base_url,
        )
    return configs


def get_api_config(name: str) -> ApiConfig:
    """取单个 API 的当前配置；未声明时抛 KeyError 并给出可用清单提示。"""
    configs = load_api_configs()
    if name not in configs:
        raise KeyError(f"未声明的 API：{name}；可用：{', '.join(sorted(configs))}")
    return configs[name]


def is_ready(name: str) -> bool:
    """该 API 是否已配置密钥可真实调用；False 时业务侧应走 mock 演示口径。"""
    return get_api_config(name).enabled


def list_apis() -> list[dict]:
    """汇总清单（toB 治理看板/运维巡检可直接展示）。"""
    return [
        {
            "name": config.name,
            "category": config.category,
            "description": config.description,
            "base_url": config.base_url,
            "key_envs": list(config.key_envs),
            "enabled": config.enabled,
            "ready": config.enabled,
            "fallback": config.fallback,
            "docs_url": config.docs_url,
        }
        for config in load_api_configs().values()
    ]
