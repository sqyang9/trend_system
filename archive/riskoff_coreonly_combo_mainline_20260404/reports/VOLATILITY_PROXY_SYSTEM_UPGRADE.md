# Volatility Proxy System Upgrade

- Scope: independent system-level research for the two defects surfaced by `W06` and `W11`.
- Mainline not changed.
- P0 route: ATR-based vol-targeting for sleeves.
- P1 route: HV percentile as a background detector that can force high-churn core qualification earlier.

## Background Data

- `ATR14` proxy built on 4h bars; position scaler uses trailing `180d` ATR%% median / current ATR%%, clipped to `0.35x ~ 1.50x`.
- `HV14` uses 14-day rolling log-return volatility on 4h bars, annualized with `sqrt(6*365)`.
- `HV percentile` is current HV's rolling rank inside trailing `180d`.
- `W06` background: median ATR scale `1.00x`, HV>=85 share `13.6%`, HV>=90 share `9.1%`.
- `W11` background: median ATR scale `1.00x`, HV>=85 share `17.3%`, HV>=90 share `11.3%`.

## Full-Sample Summary

| Candidate | Default Return% | Default Calmar | Default MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 Entries | W11 Quick14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0: ATR vol-targeting on S1+S2 | 3072.90 | 3.073 | -24.17 | 3.150 | 2.941 | -47.4% | 4 | 50.0% |
| Combo: S1+S2 ATR VT + HV85 core gate | 2995.89 | 3.044 | -24.17 | 3.123 | 2.916 | -47.4% | 3 | 33.3% |
| P0: ATR vol-targeting on S2 | 2979.07 | 2.964 | -24.77 | 3.068 | 2.773 | -47.7% | 4 | 50.0% |
| Combo: S2 ATR VT + HV85 core gate | 2902.07 | 2.936 | -24.77 | 3.040 | 2.748 | -47.7% | 3 | 33.3% |
| Current mainline | 2893.89 | 2.854 | -25.46 | 2.968 | 2.643 | -49.5% | 4 | 50.0% |
| P1: HV pct >= 90 -> force HC gate | 2857.92 | 2.841 | -25.46 | 2.954 | 2.632 | -49.5% | 3 | 33.3% |
| P1: HV pct >= 85 -> force HC gate | 2816.89 | 2.825 | -25.46 | 2.940 | 2.618 | -49.5% | 3 | 33.3% |

## Readout

- Baseline mainline: default `Return 2893.89% / Calmar 2.854 / MaxDD -25.46%`; W06 `DD/Exp -49.5%`; W11 `entries 4, quick14 50.0%`.
- Best P0-only candidate: `P0: ATR vol-targeting on S1+S2` with default `Return 3072.90% / Calmar 3.073 / MaxDD -24.17%`; W06 `DD/Exp -47.4%`.
- Best P1-only candidate: `P1: HV pct >= 90 -> force HC gate` with default `Return 2857.92% / Calmar 2.841 / MaxDD -25.46%`; W11 `entries 3, quick14 33.3%`.
- Best combined candidate: `Combo: S1+S2 ATR VT + HV85 core gate` with default `Return 2995.89% / Calmar 3.044 / MaxDD -24.17%`; W06 `DD/Exp -47.4%`; W11 `entries 3, quick14 33.3%`.