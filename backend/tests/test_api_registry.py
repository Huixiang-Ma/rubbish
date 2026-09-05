"""统一 API 配置中心（app/api_registry.py）的离线单测：不发起任何网络请求。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import api_registry

_API_ENV_KEYS = (
    "AMAP_API_KEY",
    "QWEATHER_API_KEY",
    "TAOBAO_APP_KEY",
    "TAOBAO_APP_SECRET",
    "ALIYUN_ACCESS_KEY_ID",
    "ALIYUN_ACCESS_KEY_SECRET",
    "LLM_API_KEY",
    "LLM_MODE",
    "FLIGGY_AI_API_KEY",
    "FLIGGY_AI_MCP_URL",
)


@pytest.fixture(autouse=True)
def _isolated_api_env():
    """隔离 API 密钥环境变量：测试开始清空（避免导入时加载的真实 .env 泄漏），结束后恢复。"""
    saved = {key: os.environ.get(key) for key in _API_ENV_KEYS}
    for key in _API_ENV_KEYS:
        os.environ.pop(key, None)
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_core_providers_declared() -> None:
    names = set(api_registry.API_PROVIDERS)
    assert {"llm", "amap", "qweather", "fliggy", "fliggy_ai", "aliyun_content_safety"} <= names


def test_no_redundant_category_duplicates() -> None:
    """同一能力只保留一个 API：地图类/天气类不允许出现重复 provider。"""
    seen: dict[str, str] = {}
    for name, config in api_registry.API_PROVIDERS.items():
        if config.category in {"map", "weather"}:
            assert config.category not in seen, (
                f"{config.category} 能力重复：{seen[config.category]} 与 {name}"
            )
            seen[config.category] = name
    assert seen["map"] == "amap"
    assert seen["weather"] == "qweather"


def test_all_providers_have_mock_fallback_and_docs() -> None:
    for name, config in api_registry.API_PROVIDERS.items():
        assert config.fallback == "mock", name
        assert config.base_url.startswith("https://"), name
        assert config.key_envs, name
        assert config.description, name


def test_disabled_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for env in ("AMAP_API_KEY", "QWEATHER_API_KEY", "LLM_MODE", "LLM_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    configs = api_registry.load_api_configs()
    assert configs["amap"].enabled is False
    assert configs["qweather"].enabled is False
    assert configs["llm"].enabled is False


def test_env_key_enables_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "test-amap-key")
    monkeypatch.setenv("QWEATHER_API_KEY", "test-qweather-key")
    configs = api_registry.load_api_configs()
    assert configs["amap"].enabled is True
    assert configs["amap"].api_key == "test-amap-key"
    assert configs["qweather"].enabled is True


def test_llm_enabled_only_in_real_mode_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODE", "real")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    configs = api_registry.load_api_configs()
    assert configs["llm"].enabled is True

    monkeypatch.setenv("LLM_MODE", "mock")
    configs = api_registry.load_api_configs()
    assert configs["llm"].enabled is False


def test_get_api_config_unknown_name_has_hint() -> None:
    with pytest.raises(KeyError) as excinfo:
        api_registry.get_api_config("not_exist")
    assert "可用" in str(excinfo.value)


def test_env_file_enables_usable_apis(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """项目根 .env 填了密钥后，本地裸跑（cwd=backend）也应能读到并启用对应 API。"""
    (tmp_path / ".env").write_text("AMAP_API_KEY=env-file-amap\nQWEATHER_API_KEY=env-file-qweather\n", encoding="utf-8")
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    monkeypatch.chdir(backend_dir)  # 模拟在 backend/ 目录启动 uvicorn，.env 在上级项目根
    assert api_registry.load_env_file() is True
    configs = api_registry.load_api_configs()
    assert configs["amap"].enabled is True
    assert configs["amap"].api_key == "env-file-amap"
    assert configs["qweather"].enabled is True


def test_env_file_missing_returns_false(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    monkeypatch.setenv("AMAP_API_KEY", "")  # 清掉进程环境，避免误判
    assert api_registry.load_env_file() is False


def test_base_url_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """和风等平台要求项目专属 API Host：设置 QWEATHER_API_HOST 时覆盖声明里的默认域名。"""
    monkeypatch.setenv("QWEATHER_API_KEY", "kq")
    monkeypatch.setenv("QWEATHER_API_HOST", "https://abc123.re.qweatherapi.com/v7")
    configs = api_registry.load_api_configs()
    assert configs["qweather"].base_url == "https://abc123.re.qweatherapi.com/v7"


def test_list_apis_summary_ready_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    rows = api_registry.list_apis()
    by_name = {row["name"]: row for row in rows}
    assert by_name["amap"]["ready"] is True
    assert by_name["qweather"]["ready"] is False
    assert {"name", "category", "description", "enabled", "ready", "base_url", "key_envs"} <= set(
        by_name["amap"]
    )


def test_fliggy_ai_ready_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """fliggy_ai：未配置 key 时禁用，配置后启用（MCP 端点默认值）。"""
    monkeypatch.delenv("FLIGGY_AI_API_KEY", raising=False)
    config = api_registry.get_api_config("fliggy_ai")
    assert not config.enabled
    assert config.base_url == "https://flyai.open.fliggy.com/mcp"
    monkeypatch.setenv("FLIGGY_AI_API_KEY", "test-key")
    config = api_registry.get_api_config("fliggy_ai")
    assert config.enabled
    assert config.api_key == "test-key"
