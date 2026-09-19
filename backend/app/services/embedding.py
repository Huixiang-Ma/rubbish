"""Embedding 客户端：真实模型（本机 Ollama 的 BGE-M3）与演示 mock 向量的统一入口。

mock-first 风格与 LLMClient 一致：EMBEDDING_PROVIDER=mock（默认）零依赖，返回
确定性 8 维演示向量（历史行为不变）；配置 ollama 后经 /api/embed 调用本机 Ollama
的 BGE-M3（1024 维）。与 LLMClient 不同，ollama 模式调用失败不静默降级 mock——
两套向量维度不同，混写入同一列会污染检索空间，失败直接抛错由 API 层转 503。
"""
from __future__ import annotations

import hashlib
import json
import logging

import httpx

from app.config import Settings
from app.services.paths import DATA_ROOT

logger = logging.getLogger("wl.embedding")

MOCK_DIM = 8
_BATCH_SIZE = 32
_EMBED_CACHE_PATH = DATA_ROOT / "embed_cache.json"
_embed_cache: dict[str, list[float]] | None = None


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

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化（缓存命中直接返回；未命中按批调 ollama）。mock 模式本地计算。"""
        if self.provider != "ollama":
            return [mock_embed(t) for t in texts]
        cache = self._load_cache()
        results: list[list[float] | None] = [None] * len(texts)
        pending: list[int] = []
        new_keys = 0
        for i, text in enumerate(texts):
            key = self._cache_key(text)
            if key in cache:
                results[i] = cache[key]
            else:
                pending.append(i)
        for start in range(0, len(pending), _BATCH_SIZE):
            batch = pending[start : start + _BATCH_SIZE]
            vectors = self._embed_ollama_batch([texts[i] for i in batch])
            for i, vector in zip(batch, vectors):
                results[i] = vector
                cache[self._cache_key(texts[i])] = vector
                new_keys += 1
        if new_keys:
            self._save_cache(cache)
        return [v for v in results if v is not None]

    def _cache_key(self, text: str) -> str:
        return hashlib.sha1(f"{self.provider}|{self.model}|{text}".encode("utf-8")).hexdigest()

    @staticmethod
    def _load_cache() -> dict[str, list[float]]:
        global _embed_cache
        if _embed_cache is None:
            if _EMBED_CACHE_PATH.is_file():
                try:
                    _embed_cache = json.loads(_EMBED_CACHE_PATH.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    _embed_cache = {}
            else:
                _embed_cache = {}
        return _embed_cache

    @staticmethod
    def _save_cache(cache: dict[str, list[float]]) -> None:
        _EMBED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _EMBED_CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")

    def _embed_ollama_batch(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{self.ollama_url}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        embeddings = resp.json().get("embeddings") or []
        if len(embeddings) != len(texts):
            raise RuntimeError(f"ollama 批量返回数不符：请求 {len(texts)} 得 {len(embeddings)}")
        for vector in embeddings:
            if len(vector) != self.dim:
                raise RuntimeError(
                    f"embedding 维度不符：模型返回 {len(vector)} 维，EMBEDDING_DIM={self.dim}"
                )
        return embeddings


def embed_batch(texts: list[str], settings: Settings) -> list[list[float]]:
    """模块级便捷入口：用当前配置批量向量化。"""
    return EmbeddingClient().embed_batch(texts)
