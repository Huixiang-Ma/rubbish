"""Prometheus 指标（生产演进）：提交/完成/失败/安全拦截计数 + 处理时长直方图 + 队列深度。"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

PLAN_SUBMITS = Counter("plan_submits_total", "提交的规划任务总数")
JOB_COMPLETED = Counter("job_completed_total", "完成的任务数")
JOB_FAILED = Counter("job_failed_total", "失败的任务数")
SAFETY_BLOCKED = Counter("safety_blocked_total", "高风险拦截次数")
APPROVALS = Counter("approval_total", "人工审批次数", ["decision"])
JOB_PROCESS_SECONDS = Histogram("job_process_seconds", "单个任务处理耗时（秒）")
QUEUE_DEPTH = Gauge("queue_depth", "当前队列积压深度")
