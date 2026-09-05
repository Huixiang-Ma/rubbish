"""Settings 配置加载回归测试。"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings


def test_settings_loads_project_env_when_started_from_backend(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "LLM_MODE=real\n"
        "LLM_BASE_URL=https://bai.example/v1\n"
        "LLM_API_KEY=test-key\n"
        "LLM_MODEL=test-model\n",
        encoding="utf-8",
    )
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    monkeypatch.chdir(backend_dir)
    for key in ("LLM_MODE", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.llm_mode == "real"
    assert settings.llm_base_url == "https://bai.example/v1"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "test-model"
