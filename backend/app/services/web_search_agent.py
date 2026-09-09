"""Agent 联网搜索：RAG 知识库未命中时的网络兜底。

- 检索源：Bing 网页版（无需 API key），结果与查询词面不相关时逐词裁剪重试；
- 安全：只读 GET、固定 UA、超时 8s、最多 8 条、只取摘要不深抓网页、1.2s 限速；
- 任何失败返回空列表 + note，由调用方如实告知「联网检索不可用」，绝不编造。
"""
from __future__ import annotations

import html
import re
import time
import urllib.parse
import urllib.request

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_LAST_TS = [0.0]
_MIN_INTERVAL = 1.2  # 简单限速，避免高频触发反爬


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).replace("\u200b", "").strip()


def _fetch(url: str, timeout: float = 8.0) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _bing_raw(query: str) -> list[dict[str, str]]:
    q = urllib.parse.quote(query)
    body = _fetch(f"https://www.bing.com/search?q={q}&count=8")
    items = re.findall(
        r'<li class="b_algo".*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>.*?<p[^>]*>(.*?)</p>',
        body, re.S)
    return [{"title": _clean(t)[:60], "url": u, "snippet": _clean(s)[:220]}
            for u, t, s in items[:8] if _clean(t)]


def _relevant(rows: list[dict[str, str]], words: list[str]) -> bool:
    """结果与查询词面是否相关（Bing 对长中文串偶发分词异常，仅凭这条判定重试）。

    判定：实体词（首个 ≥2 字词，通常是「拙政园」这类专名）必须出现在结果里；
    纯功能词查询（无实体词）时退化为「返回了中文结果即认为相关」。
    """
    if not rows:
        return False
    blob = " ".join(r["title"] + r["snippet"] for r in rows)
    entity = next((w for w in words if len(w) >= 2), "")
    if entity:
        return entity in blob
    return bool(re.search(r"[\u4e00-\u9fff]", blob))


def _entity_of(query: str) -> str:
    """从整句中文提取实体词：优先标品/知识库目录名前缀匹配，否则取停用词裁剪后的首词块。"""
    try:
        from app.services.catalog_rag import documents

        names = [str(d.get("name") or "") for d in documents() if d.get("name")]
        names.sort(key=len, reverse=True)
        for n in names:
            if n and n in query:
                return n
    except Exception:
        pass
    stop = {"什么", "怎么", "如何", "多少", "哪里", "哪些", "请问", "一下", "可以", "有没有",
            "有什么", "值得去吗", "怎么样", "几点", "时候", "建议", "推荐", "门票", "开放时间",
            "预约", "攻略", "优惠", "政策", "价格", "值得", "适合", "需要", "提前", "今年",
            "最新", "年", "月", "日"}
    core = query
    for w in sorted(stop, key=len, reverse=True):
        core = core.replace(w, " ")
    blocks = [w for w in core.split() if len(w) >= 2]
    return blocks[0] if blocks else query


def web_search(query: str, max_results: int = 6) -> dict:
    """对外入口：返回 {provider, results:[{title, url, snippet}], note}。

    重试链：完整 query → 实体词+功能词逐个裁剪 → 仅实体词；首个词面相关的结果集即用。
    中文整句（无空格）先做停用词裁剪提取实体，避免整句搜索被分词打碎。
    """
    query = str(query or "").strip().rstrip("？?。！")
    if not query:
        return {"provider": "none", "results": [], "note": "查询为空"}
    words = [w for w in re.split(r"[\s,，、]+", query) if w]
    if len(words) == 1 and len(words[0]) > 4:
        entity = _entity_of(query)
        if entity and entity != query:
            words = [entity, query.replace(entity, "").strip()]

    elapsed = time.monotonic() - _LAST_TS[0]
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_TS[0] = time.monotonic()

    errors: list[str] = []
    entity = next((w for w in words if len(w) >= 2), "")
    attempts: list[str] = [query]
    if len(words) > 2:
        attempts.append(" ".join(words[:-1]))
    if len(words) > 1:
        attempts.append(" ".join(words[:2]))
    if entity and entity != query.strip():
        attempts.append(entity)  # 最终兜底：只搜实体名本身

    seen_urls: set[str] = set()
    for q in attempts:
        try:
            rows = _bing_raw(q)
        except Exception as e:
            errors.append(f"{type(e).__name__}")
            continue
        if _relevant(rows, words):
            # 把与查询词面最相关的结果排前（Bing 偶发混入分词异常的无关条目）
            def _score(r: dict[str, str]) -> int:
                blob = r["title"] + r["snippet"]
                return -sum(1 for w in words if len(w) >= 2 and w in blob)
            rows = sorted(rows, key=_score)
            merged = []
            for r in rows:
                if r["url"] in seen_urls:
                    continue
                seen_urls.add(r["url"])
                merged.append(r)
                if len(merged) >= max_results:
                    break
            return {"provider": "bing", "results": merged, "note": ""}
    return {"provider": "none", "results": [],
            "note": "联网检索暂不可用（" + ("; ".join(errors) if errors else "无相关结果") + "）"}
