"""
hub_notifier.py — jackdeng-hub callback integration
Pushes status updates to the jackdeng-hub backend at key events.

Required env vars:
  HUB_URL         = https://jackdeng.cc          (no trailing slash)
  HUB_TOOL_SLUG   = visa-checker
  CRON_SECRET     = <your CRON_SECRET value>

All calls are fire-and-forget: failures are logged but never raise.
"""

import os
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_HUB_URL       = os.getenv("HUB_URL", "https://jackdeng.cc").rstrip("/")
_TOOL_SLUG     = os.getenv("HUB_TOOL_SLUG", "visa-checker")
_CRON_SECRET   = os.getenv("CRON_SECRET", "")
_ENABLED       = bool(_CRON_SECRET)

if not _ENABLED:
    logger.warning("[hub_notifier] CRON_SECRET not set — hub notifications disabled")


def notify(
    status: str,
    summary: str,
    detail: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Push a status update to jackdeng-hub.

    status  : 'running' | 'found' | 'booked' | 'heartbeat' | 'error' | 'exited'
    summary : one-line human-readable description
    detail  : longer text (optional)
    metadata: arbitrary dict (e.g. available_date, consulate, current_appointment)
    """
    if not _ENABLED:
        return

    url = f"{_HUB_URL}/api/tools/{_TOOL_SLUG}/callback"
    payload = {
        "status":   status,
        "summary":  summary,
        "detail":   detail,
        "metadata": metadata or {},
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"x-cron-secret": _CRON_SECRET},
            timeout=8,
        )
        if resp.status_code == 200:
            logger.debug(f"[hub_notifier] OK — {status}: {summary}")
        else:
            logger.warning(f"[hub_notifier] Non-200 ({resp.status_code}): {resp.text[:120]}")
    except Exception as e:
        logger.warning(f"[hub_notifier] Failed to notify hub: {e}")
