"""
Tools Layer — Notification Tools
Simulates email/SMS notification dispatch to maintenance teams and management.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Notification log (in-memory for simulation)
_NOTIFICATION_LOG: list[dict] = []


def notification_sender(
    recipients: list[str],
    message: str,
    urgency_level: str,
    subject: str = "",
    channels: Optional[list[str]] = None,
    work_order_id: Optional[str] = None,
) -> dict:
    """
    Simulate sending email/SMS notifications to maintenance personnel and management.

    Args:
        recipients: List of email/phone targets
        message: Notification body
        urgency_level: CRITICAL | HIGH | MEDIUM | LOW
        subject: Notification subject line
        channels: ["email", "sms"] - defaults based on urgency
        work_order_id: Associated work order ID for traceability

    Returns:
        Notification dispatch result with timestamp and delivery status
    """
    if channels is None:
        if urgency_level == "CRITICAL":
            channels = ["email", "sms"]
        elif urgency_level in ("HIGH", "MEDIUM"):
            channels = ["email"]
        else:
            channels = []

    if not subject:
        subject = f"[{urgency_level}] Maintenance Alert - Agentic AI System"

    entries = []
    for recipient in recipients:
        for channel in channels:
            entry = {
                "recipient": recipient,
                "channel": channel,
                "subject": subject,
                "message": message[:500],  # Truncate for log
                "urgency_level": urgency_level,
                "work_order_id": work_order_id,
                "sent_at": datetime.now().isoformat(),
                "status": "DELIVERED",  # Simulated delivery
            }
            _NOTIFICATION_LOG.append(entry)
            logger.info(
                "NOTIFY: [%s] via %s → %s | WO=%s",
                urgency_level, channel.upper(), recipient, work_order_id or "N/A"
            )
            entries.append(entry)

    return {
        "dispatched": len(entries),
        "recipients_count": len(recipients),
        "channels": channels,
        "urgency_level": urgency_level,
        "sent_at": datetime.now().isoformat(),
        "entries": entries,
    }


def get_notification_log(
    work_order_id: Optional[str] = None,
    urgency_filter: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Retrieve notification history, optionally filtered."""
    log = list(_NOTIFICATION_LOG)
    if work_order_id:
        log = [e for e in log if e.get("work_order_id") == work_order_id]
    if urgency_filter:
        log = [e for e in log if e.get("urgency_level") == urgency_filter]
    return log[-limit:]
