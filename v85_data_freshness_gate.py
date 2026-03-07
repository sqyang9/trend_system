#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_data_freshness_gate.py
Checks data recency and OKX network readiness before live rollout.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


def tail_timestamp(csv_file: Path) -> pd.Timestamp:
    df = pd.read_csv(csv_file, usecols=["timestamp"])
    return pd.to_datetime(df["timestamp"].iloc[-1], utc=True)


def check_okx_network() -> dict:
    out = {
        "public_time_api_ok": False,
        "error": "",
    }
    try:
        r = requests.get("https://www.okx.com/api/v5/public/time", timeout=12)
        out["public_time_api_ok"] = r.status_code == 200 and '"code":"0"' in r.text
    except Exception as e:
        out["error"] = str(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="V85 data freshness gate")
    ap.add_argument("--data_dir", default="./data")
    ap.add_argument("--max_staleness_hours", type=float, default=48.0)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    files = {
        "5m": data_dir / "btc_usdt_swap_5m.csv",
        "4h": data_dir / "btc_usdt_swap_4h_from_5m.csv",
    }

    now = pd.Timestamp.now(tz="UTC")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "max_staleness_hours": args.max_staleness_hours,
        "files": {},
    }

    data_ok = True
    for name, fp in files.items():
        if not fp.exists():
            report["files"][name] = {"exists": False}
            data_ok = False
            continue

        ts = tail_timestamp(fp)
        stale_h = float((now - ts).total_seconds() / 3600.0)
        pass_flag = stale_h <= args.max_staleness_hours
        report["files"][name] = {
            "exists": True,
            "last_bar_utc": str(ts),
            "staleness_hours": stale_h,
            "pass": pass_flag,
        }
        data_ok = data_ok and pass_flag

    net = check_okx_network()
    report["okx_network"] = net
    report["data_gate_pass"] = data_ok
    report["network_gate_pass"] = bool(net["public_time_api_ok"])
    report["overall_pass"] = report["data_gate_pass"] and report["network_gate_pass"]

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
