"""段落感知切块器（rag_lab 验证后回填）：段落整块聚合，超长滑窗，overlap 衔接。"""
from __future__ import annotations

import re


def chunk_text(text: str, size: int = 350, overlap: int = 70, min_chars: int = 30) -> list[str]:
    """除"过短末块并入前块（允许轻微超出 size）"外，所有块 ≤ size。"""
    if not (0 <= overlap < size):
        raise ValueError("overlap 须在 [0, size) 内")
    normalized = re.sub(r"[ \t\r\f\v]+", " ", text.strip())
    if not normalized:
        return []

    units: list[str] = []
    for block in (b.strip() for b in normalized.split("\n")):
        if not block:
            continue
        if len(block) <= size:
            units.append(block)
            continue
        step = max(size - overlap, 1)
        for i in range(0, len(block), step):
            units.append(block[i : i + size])

    chunks: list[str] = []
    buf = ""
    for unit in units:
        candidate = (buf + "\n" + unit) if buf else unit
        if len(candidate) <= size:
            buf = candidate
            continue
        chunks.append(buf)
        tail = chunks[-1][-overlap:] if overlap and len(chunks[-1]) > overlap else ""
        buf = (tail + "\n" + unit) if tail and len(tail) + 1 + len(unit) <= size else unit
    if buf:
        chunks.append(buf)
    if len(chunks) >= 2 and len(chunks[-1]) < min_chars:
        chunks[-2] = chunks[-2] + "\n" + chunks.pop()
    return chunks
