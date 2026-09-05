"""结构化 JSON 日志（生产演进）：job_id 贯穿所有关键事件，便于采集与检索。"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("wl.structured")
if not _logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)


def log_event(event: str, **fields: Any) -> None:
    """输出一条 JSON 结构化日志（信息采集友好：Loki/ELK 可直接解析）。"""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    _logger.info(json.dumps(record, ensure_ascii=False, default=str))
