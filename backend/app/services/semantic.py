"""语义检索（pgvector）：chunk 入库 + 余弦相似检索。

未配置 DATABASE_URL 时使用进程内存索引兜底；embedding 由 app.services.embedding
提供——默认确定性 mock 演示向量（8 维），配置 EMBEDDING_PROVIDER=ollama 后走本机
Ollama 的 BGE-M3（1024 维），函数接口不变。
"""
from __future__ import annotations

from app.services.embedding import EmbeddingClient, mock_embed  # noqa: F401  mock_embed 保留旧导出
from app.services.pg_mirror import pg_mirror

embedding_client = EmbeddingClient()
_memory_chunks: list[dict] = []


def add_chunk(job_id: str, content: str) -> dict:
    embedding = embedding_client.embed(content)
    chunk_id = pg_mirror.add_chunk(job_id, content, embedding)
    if chunk_id is None:
        _memory_chunks.append({"job_id": job_id, "content": content, "embedding": embedding})
        chunk_id = len(_memory_chunks)
    return {
        "id": chunk_id,
        "mode": "pg" if pg_mirror.enabled else "memory",
        "embedder": embedding_client.provider,
    }


def search_similar(query: str, k: int = 3) -> dict:
    embedding = embedding_client.embed(query)
    if pg_mirror.enabled:
        return {
            "mode": "pg",
            "embedder": embedding_client.provider,
            "results": pg_mirror.search_chunks(embedding, k),
        }
    scored = sorted(
        _memory_chunks,
        key=lambda c: -sum(a * b for a, b in zip(c["embedding"], embedding)),
    )[:k]
    return {"mode": "memory", "embedder": embedding_client.provider, "results": scored}
