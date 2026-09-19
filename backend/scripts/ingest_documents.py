"""文档摄取 CLI：PDF/DOCX/HTML/TXT/MD → 切块 → 向量化 → pgvector 入库。

输入（可组合）：
  --file a.pdf b.docx ...          本地文档，按扩展名分发解析
  --dir ./docs [--ext pdf,docx,txt]  目录批量摄取（递归）
  --url https://... [--url ...]    网页抓取（HTML 正文提取）
通用选项：
  --api-base http://localhost:8000  后端地址（入库走 /api/semantic/add）
  --job-id-prefix doc               chunk 的 job_id 前缀（实际为 {prefix}:{文档名}，按文档分组便于清理）
  --chunk-size 400 --overlap 80     切块参数（文旅语料规范：300-500 字带 overlap）
  --no-prefix-title                 关闭"块前缀文档标题"（默认开，检索结果可直接溯源）
  --dry-run / --verify "查询语句"    试运行 / 入库后抽样检索验证
清洗：内容 MD5 去重；过滤 <30 字噪声块（页码/分隔符）；UTF-8/GBK 自动识别。

用法（backend 目录下）：
  python -m scripts.ingest_documents --file /path/景区公告.pdf
  python -m scripts.ingest_documents --dir ../docs --ext pdf,docx,md
  python -m scripts.ingest_documents --url https://www.szzzy.cn/visit --verify "拙政园 开放时间"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import document_ingest  # noqa: E402

_INGESTIBLE_EXT = {".pdf", ".docx", ".html", ".htm", ".txt", ".md", ".markdown"}


def collect_documents(args: argparse.Namespace) -> list[tuple[str, str, str]]:
    """汇总所有输入 → [(title, text, doc_label)]；doc_label 用于 job_id 分组。"""
    docs: list[tuple[str, str, str]] = []
    for file_path in args.file or []:
        title, text = document_ingest.extract_document(file_path)
        docs.append((title or Path(file_path).stem, text, Path(file_path).stem))
    for dir_path in args.dir or []:
        root = Path(dir_path)
        if not root.is_dir():
            raise SystemExit(f"目录不存在：{root}")
        allowed = (
            {f".{e.strip().lower().lstrip('.')}" for e in args.ext.split(",") if e.strip()}
            if args.ext
            else _INGESTIBLE_EXT
        )
        for child in sorted(root.rglob("*")):
            if child.is_file() and child.suffix.lower() in allowed:
                try:
                    title, text = document_ingest.extract_document(child)
                except Exception as exc:  # 批量模式单文件失败不阻断
                    print(f"  ✗ 跳过 {child.name}：{exc}")
                    continue
                docs.append((title or child.stem, text, child.stem))
    for url in args.url or []:
        title, text = document_ingest.fetch_document(url, timeout=args.timeout)
        label = urllib.parse.urlparse(url).netloc or url[:40]
        docs.append((title, text, label))
    return docs


def build_chunks(docs: list[tuple[str, str, str]], args: argparse.Namespace) -> list[tuple[str, str]]:
    """所有文档 → [(job_id, chunk_text)]，块前缀标题、MD5 去重。"""
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    skipped_dup = skipped_noise = 0
    for title, text, label in docs:
        if not text.strip():
            print(f"  ✗ 空文档跳过：{label}")
            continue
        chunks = document_ingest.chunk_text(text, size=args.chunk_size, overlap=args.overlap)
        chunks = [c for c in chunks if len(c) >= document_ingest.MIN_CHUNK_CHARS]
        if not chunks:
            print(f"  ✗ 有效内容不足（噪声块过滤后为空）：{label}")
            continue
        if args.prefix_title and title:
            chunks = [f"【{title}】{c}" for c in chunks]
        job_id = f"{args.job_id_prefix}:{label}"
        for chunk in chunks:
            digest = hashlib.md5(chunk.encode("utf-8")).hexdigest()
            if digest in seen:
                skipped_dup += 1
                continue
            seen.add(digest)
            result.append((job_id, chunk))
    if skipped_dup:
        print(f"去重跳过 {skipped_dup} 条重复块")
    if skipped_noise:
        print(f"噪声块过滤 {skipped_noise} 条")
    return result


def insert_chunks(api_base: str, items: list[tuple[str, str]], dry_run: bool) -> tuple[int, str, int]:
    """批量入库（单条失败重试 3 次），返回 (写入数, 存储模式, 失败数)。"""
    mode = ""
    inserted = failed = 0
    endpoint = api_base.rstrip("/") + "/api/semantic/add"
    for index, (job_id, text) in enumerate(items, start=1):
        if dry_run:
            print(f"  [dry-run {index}/{len(items)}] ({job_id}) {text[:60]}")
            inserted += 1
            continue
        url = endpoint + "?" + urllib.parse.urlencode({"job_id": job_id, "content": text})
        for attempt in range(1, 4):
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
                    print(f"  ✗ 第{index}块入库失败（已重试3次）：{exc}")
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
        print(f"  Top{i} d={hit.get('distance', 0):.4f} {hit.get('content', '')[:70]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="文档摄取：PDF/DOCX/HTML/TXT/MD → RAG 向量库")
    parser.add_argument("--file", action="append", help="本地文档路径，可重复")
    parser.add_argument("--dir", action="append", help="目录批量摄取（递归），可重复")
    parser.add_argument("--ext", default="", help="目录模式的扩展名过滤，逗号分隔（如 pdf,docx,md）")
    parser.add_argument("--url", action="append", help="网页地址，可重复")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--job-id-prefix", default="doc")
    parser.add_argument("--chunk-size", type=int, default=document_ingest.CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=document_ingest.CHUNK_OVERLAP)
    parser.add_argument("--timeout", type=float, default=30.0, help="网页抓取超时（秒）")
    parser.add_argument("--no-prefix-title", dest="prefix_title", action="store_false")
    parser.add_argument("--verify", default="", help="入库后抽样检索验证的 query")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not (args.file or args.dir or args.url):
        parser.error("至少提供 --file / --dir / --url 之一")

    docs = collect_documents(args)
    print(f"收集 {len(docs)} 个文档：", "、".join(label for _, _, label in docs[:8]) + ("..." if len(docs) > 8 else ""))
    items = build_chunks(docs, args)
    print(f"切块去重后共 {len(items)} 块待入库（size={args.chunk_size}, overlap={args.overlap}）")
    if not items:
        print("无可入库内容")
        return

    inserted, mode, failed = insert_chunks(args.api_base, items, args.dry_run)
    store = f"写入 {inserted} 块（存储模式：{mode or 'dry-run'}，失败 {failed} 块）"
    if mode == "memory":
        store += " ⚠️ 后端未配置 DATABASE_URL，内存模式重启即失"
    print(store)

    if args.verify:
        search_check(args.api_base, args.verify)


if __name__ == "__main__":
    main()
