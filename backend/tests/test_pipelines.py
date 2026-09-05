"""toC/toB 双管线分叉（app/services/pipelines.py）的单测。"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pipelines import TOB_PIPELINE, TOC_PIPELINE, resolve_pipeline


def test_toc_by_default() -> None:
    key, nodes = resolve_pipeline({"destination": "北京市", "days": 3})
    assert key == "toc"
    assert nodes == TOC_PIPELINE
    assert "Debate" in nodes and "Mood" in nodes
    assert "Consultant" not in nodes


def test_tob_with_customer() -> None:
    key, nodes = resolve_pipeline({"destination": "北京市", "customer": "示例客户"})
    assert key == "tob"
    assert nodes == TOB_PIPELINE
    assert "Consultant" in nodes and "Compliance" in nodes
    assert "Debate" not in nodes and "Mood" not in nodes


def test_tob_with_tenant_only() -> None:
    key, _ = resolve_pipeline({"destination": "北京市", "tenant": "demo"})
    assert key == "tob"
