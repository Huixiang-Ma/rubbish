"""RAG 语料同步管道：真实数据源 → 清洗去重 → 批量入库语义检索库。

源模式（--source）：
  amap  --city 苏州 [--keywords 风景名胜] [--size 25]
        实时调用项目已配置的高德 POI（需 AMAP_API_KEY，合规商用数据，含营业时间/评分）
  file  --file path.(csv|json) [--encoding gbk]
        政务开放平台导出的数据集文件（北京/深圳/杭州等开放平台可下载景区名录）；
        推荐列：name/city/address/level/open_time/ticket/description（中英文列名均可，缺失列自动跳过）
  url   --url https://... [--param k=v ...]
        政务平台开放 JSON 接口（GET，自动带浏览器 UA；部分平台需注册 token，走 file 模式更稳）

通用选项：
  --api-base http://localhost:8000   后端地址（入库走 /api/semantic/add，容器内 pgvector 自动生效）
  --job-id corpus:amap:suzhou        chunk 的 job_id 分组标识
  --verify "拙政园 门票"              入库后抽样语义检索验证
  --dry-run                          只打印将入库的文本，不实际写入

清洗规则：name 必填；字段拼接为知识文本（≤500 字）；全角空白归一；按内容 MD5 去重。

用法（backend 目录下）：
  python -m scripts.sync_rag_corpus --source amap --city 苏州 --keywords 风景名胜
  python -m scripts.sync_rag_corpus --source file --file /tmp/5a_spots.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api_registry import load_api_configs  # noqa: E402
from app.services import amap_client  # noqa: E402

MAX_CHARS = 500
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def _pick(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def build_text(row: dict[str, Any], default_city: str = "") -> str | None:
    """数据行 → 知识文本；name 缺失返回 None。"""
    name = _pick(row, "name", "名称", "景区名称", "景点名称")
    if not name:
        return None
    city = _pick(row, "city", "城市", "所在城市") or default_city
    address = _pick(row, "address", "地址")
    level = _pick(row, "level", "等级", "景区等级", "A级")
    open_time = _pick(row, "open_time", "开放时间", "营业时间")
    ticket = _pick(row, "ticket", "门票", "门票价格", "票价")
    description = _pick(row, "description", "简介", "介绍")

    fragments = [name]
    if city or address:
        fragments.append("位于" + " ".join(x for x in (city, address) if x))
    if level:
        fragments.append(f"景区等级：{level}")
    if open_time:
        fragments.append(f"开放时间：{open_time}")
    if ticket:
        fragments.append(f"门票信息：{ticket}")
    if description:
        fragments.append(description)
    text = "。".join(f.strip().rstrip("。") for f in fragments if f.strip()) + "。"
    text = "".join(text.split())  # 去除所有空白（含全角空格）
    return text[:MAX_CHARS] if text else None


def rows_from_file(path: str, encoding: str) -> list[dict[str, Any]]:
    raw = Path(path).read_text(encoding=encoding)
    if path.lower().endswith(".json"):
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("data") or data.get("rows") or data.get("list") or []
        return [r for r in data if isinstance(r, dict)]
    reader = csv.DictReader(io.StringIO(raw))
    return [dict(r) for r in reader]


def rows_from_url(url: str, params: list[str]) -> list[dict[str, Any]]:
    query = "&".join(p for p in params if p)
    full = f"{url}?{query}" if query else url
    req = urllib.request.Request(full, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        reader = csv.DictReader(io.StringIO(raw))
        return [dict(r) for r in reader]
    if isinstance(data, dict):
        data = data.get("data") or data.get("rows") or data.get("list") or data.get("result") or []
    return [r for r in data if isinstance(r, dict)]


def rows_from_amap(city: str, keywords: str, size: int) -> list[dict[str, Any]]:
    if not load_api_configs()["amap"].enabled:
        raise SystemExit("AMAP_API_KEY 未配置：.env 里填好后重试，或改用 file/url 源")
    pois = amap_client.search_pois(city, keywords, size=size)
    rows = []
    for poi in pois:
        ptype = poi.get("type", "")
        # level 仅对景区类 POI 有意义；餐饮/商店等类型硬填会产出"景区等级：中餐厅"这类病句
        is_scenic = any(k in ptype for k in ("风景名胜", "景点", "博物馆", "公园", "寺庙", "文物"))
        rows.append(
            {
                "name": poi.get("name", ""),
                "city": city,
                "address": poi.get("address", ""),
                "level": ptype.split(";")[-1] if (ptype and is_scenic) else "",
                "open_time": poi.get("open_time", ""),
                "description": f"类型：{ptype}" + (f"；评分：{poi['rating']}" if poi.get("rating") else ""),
            }
        )
    return rows


def insert_texts(api_base: str, job_id: str, texts: list[str], dry_run: bool) -> tuple[int, str, int]:
    """批量入库（单条失败重试 3 次），返回 (写入数, 模式, 失败数)。"""
    mode = ""
    inserted = 0
    failed = 0
    endpoint = api_base.rstrip("/") + "/api/semantic/add"
    for index, text in enumerate(texts, start=1):
        if dry_run:
            print(f"  [dry-run {index}/{len(texts)}] {text[:60]}")
            inserted += 1
            continue
        url = endpoint + "?" + urllib.parse.urlencode({"job_id": job_id, "content": text})
        for attempt in range(1, 4):  # embedding 偶发超时（模型冷启动/批量高峰），重试兜底
            try:
                req = urllib.request.Request(url, method="POST")
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                mode = str(data.get("mode", ""))
                inserted += 1
                break
            except Exception as exc:
                if attempt == 3:
                    failed += 1
                    print(f"  ✗ 第{index}条入库失败（已重试3次）：{exc}")
                else:
                    time.sleep(attempt)
        time.sleep(0.05)
    return inserted, mode, failed


def search_check(api_base: str, query: str, k: int = 3) -> None:
    url = api_base.rstrip("/") + "/api/semantic/search?" + urllib.parse.urlencode({"q": query, "k": k})
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    print(f"检索验证（q={query}，embedder={data.get('embedder')}，mode={data.get('mode')}）：")
    for i, hit in enumerate(data.get("results") or [], start=1):
        print(f"  Top{i} d={hit.get('distance', 0):.4f} {hit.get('content', '')[:60]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 语料同步：真实数据源 → 清洗去重 → 批量入库")
    parser.add_argument("--source", required=True, choices=["amap", "file", "url"])
    parser.add_argument("--city", default="", help="amap 模式：城市名；file/url 模式：缺失 city 列时的默认值")
    parser.add_argument("--keywords", default="风景名胜", help="amap 模式：POI 关键字")
    parser.add_argument("--size", type=int, default=25, help="amap 模式：拉取条数")
    parser.add_argument("--file", dest="file_path", help="file 模式：CSV/JSON 文件路径")
    parser.add_argument("--encoding", default="utf-8-sig", help="file 模式：文件编码（Excel 导出常用 gbk）")
    parser.add_argument("--url", help="url 模式：接口地址")
    parser.add_argument("--param", action="append", default=[], help="url 模式：查询参数 k=v，可重复")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--job-id", default="", help="缺省按 source 自动生成")
    parser.add_argument("--verify", default="", help="入库后抽样检索验证的 query")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.source == "amap":
        rows = rows_from_amap(args.city, args.keywords, args.size)
        job_id = args.job_id or f"corpus:amap:{args.city or 'default'}"
    elif args.source == "file":
        if not args.file_path:
            parser.error("file 模式需要 --file 路径")
        rows = rows_from_file(args.file_path, args.encoding)
        job_id = args.job_id or f"corpus:file:{Path(args.file_path).stem}"
    else:
        if not args.url:
            parser.error("url 模式需要 --url 地址")
        rows = rows_from_url(args.url, args.param)
        job_id = args.job_id or "corpus:url"

    texts: list[str] = []
    seen: set[str] = set()
    for row in rows:
        text = build_text(row, default_city=args.city)
        if not text:
            continue
        digest = hashlib.md5(text.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        texts.append(text)

    print(f"拉取 {len(rows)} 行 → 清洗去重后 {len(texts)} 条入库文本（job_id={job_id}）")
    if not texts:
        print("无可入库内容：检查数据列名（name 必填）与编码")
        return

    inserted, mode, failed = insert_texts(args.api_base, job_id, texts, args.dry_run)
    store = f"写入 {inserted} 条（存储模式：{mode or 'dry-run'}，失败 {failed} 条）"
    if mode == "memory":
        store += " ⚠️ 后端未配置 DATABASE_URL，内存模式重启即失"
    print(store)

    if args.verify:
        search_check(args.api_base, args.verify)


if __name__ == "__main__":
    main()
