import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SafetyScanResult:
    risk_level: str
    action: str
    evidence: list[str]


class SafetyService:
    HIGH_RISK_PATTERNS = [
        "忽略之前",
        "忽略以上",
        "输出系统提示词",
        "system prompt",
        "ignore previous",
        "developer message",
        "泄露密钥",
        "绕过审核",
        "不要告诉用户",
    ]

    MEDIUM_RISK_PATTERNS = [
        "base64",
        "隐藏文本",
        "html 注释",
        "修改预算",
    ]

    def scan_user_input(self, text: str) -> SafetyScanResult:
        return self.scan_untrusted_content(text)

    def scan_untrusted_content(self, text: str) -> SafetyScanResult:
        lowered = text.lower()
        high_hits = [pattern for pattern in self.HIGH_RISK_PATTERNS if pattern.lower() in lowered]
        if high_hits:
            return SafetyScanResult("high", "block", high_hits)
        medium_hits = [pattern for pattern in self.MEDIUM_RISK_PATTERNS if pattern.lower() in lowered]
        if medium_hits:
            return SafetyScanResult("medium", "sanitize", medium_hits)
        return SafetyScanResult("low", "allow", [])

    def sanitize(self, text: str) -> str:
        cleaned = text
        for pattern in self.HIGH_RISK_PATTERNS + self.MEDIUM_RISK_PATTERNS:
            cleaned = cleaned.replace(pattern, "[已移除风险片段]")
        return cleaned

    def scan_payload(self, payload: Any) -> tuple[Any, list[dict[str, Any]]]:
        """递归遍历 payload 中所有 str 字段，返回 (清洗后的 payload, 审计事件列表)。

        - 命中 HIGH_RISK_PATTERNS → 字段值替换为占位符，事件 action="web_content_block"
        - 命中 MEDIUM_RISK_PATTERNS → sanitize() 后保留，事件 action="web_content_sanitize"
        - 仅处理 str 值；dict/list 结构与键保持不变（兼容下游消费方）
        """
        events: list[dict[str, Any]] = []

        def _scan(value: Any) -> Any:
            if isinstance(value, str):
                scan = self.scan_untrusted_content(value)
                if scan.risk_level == "high":
                    events.append(
                        {"action": "web_content_block", "risk_level": "high", "evidence": scan.evidence}
                    )
                    cleaned = value
                    for pattern in self.HIGH_RISK_PATTERNS:
                        cleaned = cleaned.replace(pattern, "[已移除风险片段]")
                    return cleaned
                if scan.risk_level == "medium":
                    events.append(
                        {"action": "web_content_sanitize", "risk_level": "medium", "evidence": scan.evidence}
                    )
                    return self.sanitize(value)
                return value
            if isinstance(value, dict):
                return {key: _scan(item) for key, item in value.items()}
            if isinstance(value, list):
                return [_scan(item) for item in value]
            return value

        return _scan(payload), events


SAFETY_COUNTER_KEYS = ["safety_block", "safety_scan", "budget_approval_required", "approval", "web_content_block", "web_content_sanitize"]


def aggregate_safety_events(data_root: Path, events_by_job: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    """扫描本地审计日志，聚合安全看板计数、拦截率、攻击分布与按天曲线。

    events_by_job 可传入 job_index.audit_events() 的缓存结果，避免每次全量读盘。
    """
    counters: dict[str, int] = {}
    recent_blocks: list[dict[str, Any]] = []
    pattern_counter: dict[str, int] = {}
    daily_counter: dict[str, int] = {}
    jobs_scanned = 0
    if events_by_job is None:
        events_by_job = {}
        if data_root.exists():
            for job_path in sorted(data_root.iterdir()):
                audit_path = job_path / "audit.log"
                if not job_path.is_dir() or not audit_path.exists():
                    continue
                parsed: list[dict[str, Any]] = []
                for line in audit_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    parsed.append(event)
                events_by_job[job_path.name] = parsed
    for job_id, events in events_by_job.items():
        jobs_scanned += 1
        for event in events:
            action = event.get("action")
            if not isinstance(action, str):
                continue
            counters[action] = counters.get(action, 0) + 1
            if action == "safety_block":
                evidence = event.get("evidence") or []
                for pattern in evidence:
                    if isinstance(pattern, str):
                        pattern_counter[pattern] = pattern_counter.get(pattern, 0) + 1
                day = str(event.get("created_at", ""))[:10]
                if day:
                    daily_counter[day] = daily_counter.get(day, 0) + 1
                recent_blocks.append(
                    {
                        "job_id": job_id,
                        "risk_level": event.get("risk_level"),
                        "evidence": event.get("evidence"),
                        "created_at": event.get("created_at"),
                    }
                )
    known = {key: counters.get(key, 0) for key in SAFETY_COUNTER_KEYS}
    known["other"] = sum(value for key, value in counters.items() if key not in SAFETY_COUNTER_KEYS)
    scan_count = known["safety_scan"]
    block_count = known["safety_block"]
    return {
        "jobs_scanned": jobs_scanned,
        "counters": known,
        "scan_count": scan_count,
        "interception_rate": round(block_count / scan_count, 4) if scan_count else None,
        "attack_distribution": sorted(pattern_counter.items(), key=lambda pair: pair[1], reverse=True)[:6],
        "daily_blocks": [
            {"date": day, "count": count} for day, count in sorted(daily_counter.items())
        ][-14:],
        "recent_safety_blocks": recent_blocks[-10:],
    }
