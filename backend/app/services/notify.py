"""审批通知（生产演进）：任务进入人工挂起时推送飞书群机器人。

未配置 FEISHU_WEBHOOK_URL 时静默跳过；发送失败只记日志不阻断流程。
邮件通道属同一扩展点，预留 send_email 接口。
"""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("wl.notify")


def notify_hold(job_id: str, status: str, reason: str) -> bool:
    settings = get_settings()
    if not settings.feishu_webhook_url:
        return False
    try:
        response = httpx.post(
            settings.feishu_webhook_url,
            json={
                "msg_type": "text",
                "content": {"text": f"[文旅审批提醒] 任务 {job_id} 进入 {status}：{reason}，请在审核台处理。"},
            },
            timeout=5,
        )
        return response.status_code == 200
    except Exception as exc:
        logger.warning("feishu notify failed: %s", exc)
        return False


def send_feishu_text(text: str) -> bool:
    """P3.2 告警桥接：向飞书群机器人发送任意文本；未配置 webhook 时静默跳过。"""
    settings = get_settings()
    if not settings.feishu_webhook_url:
        logger.info("feishu webhook 未配置，告警文本仅记日志：%s", text[:200])
        return False
    try:
        response = httpx.post(
            settings.feishu_webhook_url,
            json={"msg_type": "text", "content": {"text": text}},
            timeout=5,
        )
        return response.status_code == 200
    except Exception as exc:
        logger.warning("feishu notify failed: %s", exc)
        return False


def send_email(to: str, subject: str, body: str) -> bool:
    """邮件通道扩展点：接入 SMTP 前占位（明确不接清单之外，按触发条件启用）。"""
    raise NotImplementedError("邮件通知未启用：配置 SMTP 后在本扩展点实现。")
