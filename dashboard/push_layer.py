#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional push layer for Telegram delivery."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import requests


def push_telegram(files: Dict[str, Path], snapshot: Dict, decision: Dict, config: Dict) -> Dict:
    if not config.get("telegram_enabled", False):
        return {"sent": False, "reason": "telegram_disabled"}

    token_env = config.get("telegram_bot_token_env", "TELEGRAM_BOT_TOKEN")
    chat_env = config.get("telegram_chat_id_env", "TELEGRAM_CHAT_ID")
    token = os.getenv(token_env)
    chat_id = os.getenv(chat_env)
    if not token or not chat_id:
        return {"sent": False, "reason": "missing_credentials"}

    caption = (
        f"{snapshot['timestamp']}\n"
        f"State: {snapshot['state']}\n"
        f"Action: {decision['action']}\n"
        f"Order: {decision['order_text']}\n"
        f"Total exposure: {snapshot['total_exposure']:.2f}\n"
        f"Cap headroom: {snapshot['cap_headroom']:.2f}x"
    )
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(files["png"], "rb") as fh:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": fh},
            timeout=20,
        )
    return {
        "sent": bool(resp.ok),
        "status_code": resp.status_code,
        "reason": "ok" if resp.ok else resp.text[:500],
    }
