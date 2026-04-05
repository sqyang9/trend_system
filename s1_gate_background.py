#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared S1 gate contract and lightweight volume-profile proxy helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from v85_research_suite_v2 import ensure_datetime
from volatility_background import build_volatility_background


DEFAULT_S1_GATE_CONTRACT = {
    "s1_gate_enabled": False,
    "s1_gate_family": "none",
}


def normalize_s1_gate_contract(contract: dict | None = None) -> Dict:
    raw = {} if contract is None else dict(contract)
    if "s1_gate_contract" in raw and isinstance(raw["s1_gate_contract"], dict):
        raw = dict(raw["s1_gate_contract"])
    enabled = bool(raw.get("s1_gate_enabled", False))
    family = str(raw.get("s1_gate_family", "none"))
    if not enabled or family in {"none", "", "disabled"}:
        return {
            "s1_gate_enabled": False,
            "s1_gate_family": "none",
            "s1_gate_label": "S1_GATE_NONE",
        }
    if family != "volume_profile_proxy":
        raise ValueError(f"Unsupported S1 gate family: {family}")
    lookback = int(raw.get("s1_vp_lookback", 60))
    escape_atr = float(raw.get("s1_vp_escape_atr", 0.50))
    volume_ratio = float(raw.get("s1_vp_volume_ratio", 1.20))
    return {
        "s1_gate_enabled": True,
        "s1_gate_family": "volume_profile_proxy",
        "s1_vp_lookback": lookback,
        "s1_vp_escape_atr": escape_atr,
        "s1_vp_volume_ratio": volume_ratio,
        "s1_gate_label": f"S1_VP_LB{lookback}_EA{int(round(escape_atr*100)):03d}_VR{int(round(volume_ratio*100)):03d}",
    }


def build_s1_gate_features(df_4h: pd.DataFrame, contract: Dict, bins: int = 24) -> pd.DataFrame:
    cfg = normalize_s1_gate_contract(contract)
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    out = pd.DataFrame(index=d4.index)
    out["signal_bar"] = d4.index
    out["s1_gate_enabled"] = bool(cfg["s1_gate_enabled"])
    out["s1_gate_family"] = str(cfg["s1_gate_family"])
    out["s1_gate_label"] = str(cfg["s1_gate_label"])
    if not cfg["s1_gate_enabled"]:
        out["s1_vp_hvn_escape_atr"] = np.nan
        out["s1_vp_volume_ratio20"] = np.nan
        out["s1_gate_pass"] = False
        out["s1_gate_reason"] = "disabled"
        return out.reset_index(drop=True)

    lookback = int(cfg["s1_vp_lookback"])
    hlc3 = ((d4["high"] + d4["low"] + d4["close"]) / 3.0).astype(float)
    volume = d4["volume"].astype(float)
    atr = build_volatility_background(d4.reset_index())["atr14"].reindex(d4.index).ffill().bfill()
    rows = []
    for pos, ts in enumerate(d4.index):
        if pos < lookback:
            rows.append(
                {
                    "signal_bar": ts,
                    "s1_vp_hvn_escape_atr": np.nan,
                    "s1_vp_volume_ratio20": np.nan,
                    "s1_gate_pass": False,
                    "s1_gate_reason": "not_applicable",
                }
            )
            continue
        window = slice(pos - lookback, pos)
        price = hlc3.iloc[window].to_numpy()
        weight = volume.iloc[window].to_numpy()
        low = float(np.nanmin(price))
        high = float(np.nanmax(price))
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            hvn_price = np.nan
        else:
            hist, edges = np.histogram(price, bins=bins, range=(low, high), weights=weight)
            hvn_idx = int(np.argmax(hist))
            hvn_price = float((edges[hvn_idx] + edges[hvn_idx + 1]) / 2.0)
        current_close = float(d4.iloc[pos]["close"])
        current_atr = float(atr.iloc[pos]) if np.isfinite(atr.iloc[pos]) else np.nan
        vol20 = float(volume.iloc[max(0, pos - 20):pos].mean())
        current_vol = float(volume.iloc[pos])
        escape = (
            (current_close - hvn_price) / current_atr
            if np.isfinite(hvn_price) and np.isfinite(current_atr) and current_atr > 0.0
            else np.nan
        )
        vol_ratio = current_vol / vol20 if np.isfinite(vol20) and vol20 > 0.0 else np.nan
        pass_escape = bool(np.isfinite(escape) and escape >= float(cfg["s1_vp_escape_atr"]))
        pass_vol = bool(np.isfinite(vol_ratio) and vol_ratio >= float(cfg["s1_vp_volume_ratio"]))
        if pass_escape and pass_vol:
            reason = "pass"
        elif pass_escape:
            reason = "fail_volume_ratio"
        elif pass_vol:
            reason = "fail_hvn_escape"
        else:
            reason = "fail_both"
        rows.append(
            {
                "signal_bar": ts,
                "s1_vp_hvn_escape_atr": escape,
                "s1_vp_volume_ratio20": vol_ratio,
                "s1_gate_pass": pass_escape and pass_vol,
                "s1_gate_reason": reason,
            }
        )
    feat = pd.DataFrame(rows).set_index("signal_bar")
    out = out.join(feat, how="left")
    out["s1_gate_pass"] = out["s1_gate_pass"].fillna(False)
    out["s1_gate_reason"] = out["s1_gate_reason"].fillna("not_applicable")
    return out.reset_index(drop=True)
