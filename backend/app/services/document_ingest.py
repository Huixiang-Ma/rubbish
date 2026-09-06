"""文档摄取服务：PDF/DOCX/HTML/TXT/MD → 纯文本 → 段落感知切块（RAG 入库前置）。

- 解析按扩展名分发；重依赖（pypdf / python-docx）延迟导入，未安装时给出可操作的安装提示；
- HTML 用标准库 HTMLParser 剥离 script/style，块级标签转换行，零额外依赖；
- 切块遵循文旅语料规范：段落优先整块聚合、默认 400 字上限、80 字 overlap 保持语义连续。
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
import urllib.request

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
MIN_CHUNK_CHARS = 30

_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "table", "ul", "ol", "blockquote", "pre",
}
_SKIP_TAGS = {"script", "style", "noscript", "template", "head", "svg"}


class _TextExtractor(HTMLParser):
    """块级标签转换行、跳过 script/style 的极简正文提取器。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title = ""
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data.strip()
        if not self._skip_depth and data.strip():
            self._parts.append(data)


def parse_html(html: str) -> tuple[str, str]:
    """HTML → (title, 正文纯文本)。畸形 HTML 尽力提取不抛错。"""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    lines = [line.strip() for line in "".join(parser._parts).split("\n")]
    return parser.title.strip(), "\n".join(line for line in lines if line)


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_pdf(path: Path) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("解析 PDF 需要 pypdf：pip install pypdf") from exc
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    meta_title = ""
    try:
        meta_title = str((reader.metadata or {}).get("/Title") or "").strip()
    except Exception:
        pass
    return meta_title or path.stem, "\n".join(p for p in pages if p)


def extract_docx(path: Path) -> tuple[str, str]:
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("解析 DOCX 需要 python-docx：pip install python-docx") from exc
    document = docx.Document(str(path))
    parts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:  # 表格按行拼接，保留"列：值"语义
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append("；".join(cells))
    return path.stem, "\n".join(parts)


def extract_document(path: str | Path) -> tuple[str, str]:
    """按扩展名分发解析，返回 (title, text)。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在：{p}")
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(p)
    if suffix == ".docx":
        return extract_docx(p)
    if suffix in {".html", ".htm"}:
        return parse_html(_read_text_file(p))
    if suffix in {".txt", ".md", ".markdown"}:
        return p.stem, _read_text_file(p)
    raise ValueError(f"不支持的文档类型：{suffix}（支持 pdf/docx/html/htm/txt/md）")


def _fetch_bytes(url: str, timeout: float = 30.0) -> bytes:
    # 完整 UA：部分站点（如百度百科）拦截简化 UA，返回 403
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_document(url: str, timeout: float = 30.0) -> tuple[str, str]:
    """抓取网页并解析为 (title, 正文)。编码依次尝试 utf-8 / gb18030。"""
    raw = _fetch_bytes(url, timeout)
    html = None
    for encoding in ("utf-8", "gb18030"):
        try:
            html = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if html is None:
        html = raw.decode("utf-8", errors="replace")
    title, text = parse_html(html)
    if not title:
        title = urllib.parse.urlparse(url).netloc
    return title, text


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """段落感知切块：段落整块聚合；超长段落按滑动窗口硬切（窗口间自然带 overlap）；
    相邻块之间再衔接上一块尾部 overlap 字符；过短末块并入前块（允许轻微超出 size）。
    除末块合并外，所有块 ≤ size。"""
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
        step = max(size - overlap, 1)  # 超长段落：滑动窗口，窗口间自然带 overlap
        for i in range(0, len(block), step):
            units.append(block[i : i + size])

    chunks: list[str] = []
    buf = ""
    for unit in units:  # unit 恒 ≤ size
        candidate = (buf + "\n" + unit) if buf else unit
        if len(candidate) <= size:
            buf = candidate
            continue
        chunks.append(buf)
        tail = chunks[-1][-overlap:] if overlap and len(chunks[-1]) > overlap else ""
        buf = (tail + "\n" + unit) if tail and len(tail) + 1 + len(unit) <= size else unit
    if buf:
        chunks.append(buf)
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_CHUNK_CHARS:
        chunks[-2] = chunks[-2] + "\n" + chunks.pop()
    return chunks
