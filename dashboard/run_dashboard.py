#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot dashboard runner for the adopted BTC mainline."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from decision_layer import build_decision
from output_layer import write_all
from push_layer import push_telegram
from signal_layer import build_signal_snapshot


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "dashboard_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and optionally open the current signal PNG.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to dashboard config json.")
    parser.add_argument("--open", action="store_true", help="Open the generated PNG after rendering.")
    return parser.parse_args()


def load_config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    snapshot = build_signal_snapshot()
    decision = build_decision(snapshot, config)
    files = write_all(snapshot, decision)
    push_result = push_telegram(files, snapshot, decision, config)

    if args.open or config.get("open_png_after_render", False):
        subprocess.run(["open", str(files["png_latest"])], check=False)

    print(
        json.dumps(
            {
                "png": str(files["png"]),
                "png_latest": str(files["png_latest"]),
                "json": str(files["json"]),
                "md": str(files["md"]),
                "state": snapshot["state"],
                "action": decision["action"],
                "order_text": decision["order_text"],
                "telegram": push_result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
