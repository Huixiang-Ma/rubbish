"""白名单网页调研（演示口径，默认关闭）。

安全边界（必须遵守）：
- 仅允许抓取硬编码白名单域名的公开页面（故宫官网、八达岭官网）；
- 只读 GET、超时 5s、单任务页数与间隔限速；不提交表单、不采集个人信息、不绕过访问控制；
- 任何失败静默返回 None，不影响主链路；
- 能力默认关闭（WEB_RESEARCH_ENABLED=true 才启用），零配置行为与历史版本一致。
"""
from __future__ import annotations

import html.parser
import json
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

ALLOWLIST = {"www.dpm.org.cn", "www.badaling.gov.cn"}
FETCH_TIMEOUT_SECONDS = 5
_LAST_FETCH_TS = 0.0
_MIN_INTERVAL_SECONDS = 1.0


def is_enabled() -> bool:
    import os

    return os.environ.get("WEB_RESEARCH_ENABLED", "").strip().lower() == "true"


def is_allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in ALLOWLIST and urlparse(url).scheme in ("http", "https")


class _TextExtractor(html.parser.HTMLParser):
    """极简正文提取：取 <title> 与 <body> 内的文本行（忽略 script/style）。"""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._in_body = False
        self._depth_skip = 0
        self.lines: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
        elif tag == "body":
            self._in_body = True
        elif tag in ("script", "style"):
            self._depth_skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" or tag == "style":
            self._depth_skip = max(0, self._depth_skip - 1)

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = text
        elif self._in_body and self._depth_skip == 0:
            self.lines.append(text)


def _strip_tags(html_fragment: str) -> str:
    """剥离行内标签，返回纯文本（用于单行 HTML 的兜底解析）。"""
    parser = _TextExtractor()
    try:
        parser.feed(html_fragment)
    except Exception:
        return ""
    return " ".join(part for part in (fragment.strip() for fragment in parser.lines) if part)


def fetch_page_text(url: str) -> str | None:
    """仅白名单 URL；超时/失败/非白名单一律返回 None。请求间限速 ≥1s。"""
    global _LAST_FETCH_TS
    if not is_allowed(url):
        return None
    elapsed = time.monotonic() - _LAST_FETCH_TS
    if elapsed < _MIN_INTERVAL_SECONDS:
        time.sleep(_MIN_INTERVAL_SECONDS - elapsed)
    _LAST_FETCH_TS = time.monotonic()
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (travel-planner-demo; whitelist research)"}
        )
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html_text = resp.read(512_000).decode(charset, errors="ignore")
    except Exception:
        return None
    parser = _TextExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        return None
    body = "\n".join(parser.lines)
    return f"{parser.title}\n{body}" if parser.title else body


def extract_rules(html_text: str, spot_name: str) -> dict | None:
    """从页面文本中提取开放时间与预约规则。

    页面常见形态是「标题行 + 数据行」（如 "开放时间" 下一行是 "旺季 8:30-17:00…"），
    因此用状态机：命中标题关键词后捕获其后的第一条数据行；行内自带关键信息的直接采集。
    """
    if not html_text:
        return None

    parser = _TextExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    candidate_lines = list(parser.lines)
    for raw_line in html_text.splitlines():
        stripped = raw_line.strip()
        if "<" in stripped and ">" in stripped:
            bare = _strip_tags(stripped)
            if bare:
                candidate_lines.append(bare)

    keywords_open = ("开放时间", "开馆时间", "闭馆时间")
    keywords_booking = ("预约", "购票", "实名")
    header_markers = ("开放时间", "开馆时间", "闭馆时间", "预约须知", "预约", "购票须知")

    def is_data_line(line: str) -> bool:
        return any(ch.isdigit() for ch in line)

    open_lines: list[str] = []
    booking_lines: list[str] = []
    pending_open = False
    pending_booking = False
    for line in candidate_lines:
        if len(line) < 3 or len(line) > 120:
            continue
        if pending_open and is_data_line(line):
            if len(open_lines) < 2:
                open_lines.append(line)
            pending_open = False
            continue
        if pending_booking and (is_data_line(line) or any(k in line for k in ("提前", "实名"))):
            if len(booking_lines) < 2:
                booking_lines.append(line)
            pending_booking = False
            continue
        if any(k in line for k in keywords_open):
            if is_data_line(line) and len(open_lines) < 2:
                open_lines.append(line)
            else:
                pending_open = True
            continue
        if any(k in line for k in keywords_booking):
            if len(booking_lines) < 2:
                booking_lines.append(line)
            pending_booking = True

    if not open_lines and not booking_lines:
        return None
    return {
        "open_time": "；".join(open_lines) or "",
        "booking_rule": "；".join(booking_lines) or "",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def research_spot(spot_name: str, url: str) -> dict | None:
    """一步式调研：抓取 + 提取；返回带 fetched_at/source_url 的规则字典，失败返回 None。"""
    html_text = fetch_page_text(url)
    if not html_text:
        return None
    rules = extract_rules(html_text, spot_name)
    if not rules:
        return None
    return rules
