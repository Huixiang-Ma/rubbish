"""Embedding 客户端：真实模型（本机 Ollama 的 BGE-M3）与演示 mock 向量的统一入口。

mock-first 风格与 LLMClient 一致：EMBEDDING_PROVIDER=mock（默认）零依赖，返回
确定性 8 维演示向量（历史行为不变）；配置 ollama 后经 /api/embed 调用本机 Ollama
的 BGE-M3（1024 维）。与 LLMClient 不同，ollama 模式调用失败不静默降级 mock——
两套向量维度不同，混写入同一列会污染检索空间，失败直接抛错由 API 层转 503。
"""
from __future__ import annotations

import logging

import httpx

from app.config import Settings

logger = logging.getLogger("wl.embedding")

MOCK_DIM = 8


def mock_embed(text: str) -> list[float]:
    """确定性 8 维向量：按字符 hash 分布到各维，归一化。仅用于演示检索链路。"""
    vec = [0.0] * MOCK_DIM
    for index, char in enumerate(text):
        vec[(index + ord(char)) % MOCK_DIM] += 1 + (ord(char) % 7) / 10
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [round(v / norm, 6) for v in vec]


def active_dim(settings: Settings) -> int:
    """当前 embedder 的输出维度：mock 恒为 8 维；真实模型取 EMBEDDING_DIM。

    pg_mirror 建表以它为准，保证默认零配置（mock）与 ollama 模式各自自洽。
    """
    return MOCK_DIM if settings.embedding_provider != "ollama" else settings.embedding_dim


class EmbeddingClient:
    """BGE-M3（Ollama /api/embed）+ mock 双模式封装。"""

    def __init__(self) -> None:
        settings = Settings()
        self.provider = settings.embedding_provider.lower()
        self.ollama_url = settings.embedding_ollama_url.rstrip("/")
        self.model = settings.embedding_model
        self.dim = active_dim(settings)
        self.timeout_seconds = settings.embedding_timeout_seconds

    def embed(self, text: str) -> list[float]:
        if self.provider != "ollama":
            return mock_embed(text)
        try:
            vector = self._embed_ollama(text)
        except Exception as exc:
            logger.warning("ollama embedding 调用失败: %s", exc)
            raise RuntimeError(
                f"EMBEDDING_PROVIDER=ollama 调用失败：确认宿主机 Ollama 已运行且模型 "
                f"{self.model} 可用（{self.ollama_url}）。"
            ) from exc
        if len(vector) != self.dim:
            raise RuntimeError(
                f"embedding 维度不符：模型返回 {len(vector)} 维，EMBEDDING_DIM={self.dim}。"
                "请核对 .env 配置与 Ollama 模型。"
            )
        return vector

    def _embed_ollama(self, text: str) -> list[float]:
        resp = httpx.post(
            f"{self.ollama_url}/api/embed",
            json={"model": self.model, "input": text},
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        embeddings = resp.json().get("embeddings") or []
        if not embeddings:
            raise RuntimeError("ollama /api/embed 返回为空")
        return embeddings[0]
