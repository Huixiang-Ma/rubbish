"""集中配置（pydantic-settings）：全部环境变量一个入口，替代散落的 os.getenv。

环境变量名与字段名大小写不敏感对应（如 llm_mode ← LLM_MODE），
与 .env.example / docker-compose.yml 一一对应。本地开发零配置即可运行。
"""
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_env_file() -> None:
    """Load the nearest project .env while preserving process env precedence."""
    candidates = [Path.cwd(), *Path.cwd().parents]
    env_file = next((path / ".env" for path in candidates if (path / ".env").is_file()), None)
    if env_file is not None:
        load_dotenv(env_file, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    def __init__(self, **values):
        _load_env_file()
        super().__init__(**values)

    # 队列
    queue_backend: str = "memory"  # memory | redis
    redis_url: str = "redis://localhost:6379/0"
    redis_stream: str = "travel_plan_jobs"
    redis_group: str = "plan_workers"
    redis_consumer: str = ""  # 留空则按 主机+进程 自动生成唯一名（多副本扩容安全）
    redis_block_ms: int = 1000
    redis_claim_min_idle_ms: int = 60_000  # PEL 消息空闲多久后可被 XAUTOCLAIM 认领
    reclaim_interval_seconds: int = 30

    # 存储 / 运行
    data_root: str | None = None
    worker_count: int = 1

    # LLM
    llm_mode: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.2

    # Embedding（语义检索）：mock=确定性演示向量；ollama=宿主机 Ollama 服务（BGE-M3）
    embedding_provider: str = "mock"  # mock | ollama
    embedding_ollama_url: str = "http://host.docker.internal:11434"  # 容器内访问宿主机 Ollama
    embedding_model: str = "dengcao/bge-m3:567m"
    embedding_dim: int = 1024  # BGE-M3 输出 1024 维；换模型需同步此值
    embedding_timeout_seconds: float = 10.0

    # 生产演进：数据库 / 可观测 / 通知
    database_url: str | None = None  # 例 postgresql+psycopg://wl:wl@localhost:5432/wl_travel
    metrics_enabled: bool = True
    feishu_webhook_url: str | None = None

    # 认证（演示级门禁）：生产部署必须在 .env 轮换以下全部口令
    auth_enabled: bool = False  # true 时 toB 管理类 API 强制 Bearer token
    auth_secret: str = "wl-dev-secret-change-me"
    admin_username: str = "admin"
    admin_password: str = "wl2026"
    toc_demo_username: str = "旅者"
    toc_demo_password: str = "123456"
    tob_supervisor_password: str = "sv2026"
    tob_consultant_password: str = "ct2026"
    free_plan_per_day: int = 3  # 每账号/每 IP 每日免费规划单数（P2 成本治理）

    # 外部适配器（明确不接第三方，只留扩展点）
    external_map_provider: str = "local"
    external_map_api_key: str = ""
    external_search_provider: str = "local"
    external_search_api_key: str = ""
    external_ocr_provider: str = "local"
    external_ocr_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
