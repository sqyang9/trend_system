# Four-Direction Light Screen

- Scope: lightweight independent screen only; current mainline stays unchanged.
- Baseline mainline: asymmetric ATRVT (`S1 90d`, `S2 60d`) + current hybrid core qualification.
- Direction (3) note: the current mainline already contains sleeve-level ATRVT. This probe tests a narrower `entry-fixed ATR budget` replacement on `S1`, not a brand-new volatility-targeting layer.

## default

| Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Current Official Mainline | 3179.90 | 1.337 | 2.872 | -26.19 | +0.00pp | +0.000 | +0.000 | +0.00pp |
| Core KAMA250 Divider | 1676.88 | 1.220 | 1.989 | -29.55 | -1503.02pp | -0.117 | -0.883 | -3.37pp |
| S1 Volume-Profile Proxy Gate | 3321.25 | 1.386 | 3.209 | -23.81 | +141.34pp | +0.049 | +0.337 | +2.38pp |
| S1 Entry-Fixed ATR Budget | 3170.99 | 1.322 | 2.746 | -27.36 | -8.92pp | -0.015 | -0.126 | -1.17pp |
| S1 Time-Decay Exit (6 bars) | 3179.90 | 1.337 | 2.872 | -26.19 | -0.00pp | +0.000 | +0.000 | +0.00pp |

## stress

| Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Current Official Mainline | 3298.74 | 1.348 | 2.931 | -26.00 | +0.00pp | +0.000 | +0.000 | +0.00pp |
| Core KAMA250 Divider | 1783.82 | 1.239 | 2.056 | -29.32 | -1514.92pp | -0.108 | -0.875 | -3.32pp |
| S1 Volume-Profile Proxy Gate | 3440.08 | 1.396 | 3.267 | -23.68 | +141.34pp | +0.048 | +0.336 | +2.32pp |
| S1 Entry-Fixed ATR Budget | 3298.20 | 1.335 | 2.833 | -26.89 | -0.54pp | -0.013 | -0.098 | -0.89pp |
| S1 Time-Decay Exit (6 bars) | 3298.74 | 1.348 | 2.931 | -26.00 | +0.00pp | +0.000 | +0.000 | +0.00pp |

## harsh_friction

| Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Current Official Mainline | 2966.62 | 1.302 | 2.679 | -27.37 | +0.00pp | +0.000 | +0.000 | +0.00pp |
| Core KAMA250 Divider | 1457.67 | 1.159 | 1.764 | -31.42 | -1508.95pp | -0.143 | -0.914 | -4.05pp |
| S1 Volume-Profile Proxy Gate | 3120.69 | 1.353 | 3.035 | -24.61 | +154.07pp | +0.051 | +0.357 | +2.76pp |
| S1 Entry-Fixed ATR Budget | 2915.84 | 1.281 | 2.558 | -28.48 | -50.78pp | -0.021 | -0.120 | -1.11pp |
| S1 Time-Decay Exit (6 bars) | 2966.62 | 1.302 | 2.679 | -27.37 | -0.00pp | -0.000 | -0.000 | -0.00pp |

## Readout

- `s1_volume_profile_proxy`: frontier-positive; default `dReturn +141.34pp / dSharpe +0.049 / dCalmar +0.337 / dMaxDD improve +2.38pp`.
- `s1_time_decay_6bar`: reserve-only; default `dReturn -0.00pp / dSharpe +0.000 / dCalmar +0.000 / dMaxDD improve +0.00pp`.
- `s1_entry_fixed_atr_budget`: no-go; default `dReturn -8.92pp / dSharpe -0.015 / dCalmar -0.126 / dMaxDD improve -1.17pp`.
- `core_kama250`: no-go; default `dReturn -1503.02pp / dSharpe -0.117 / dCalmar -0.883 / dMaxDD improve -3.37pp`.

## Candidate Definitions

- `Core KAMA250 Divider`: swap the core trend divider from `EMA250` to `KAMA250`; keep the same high-churn logic and sleeves.
- `S1 Volume-Profile Proxy Gate`: require `4h volume > 1.2x rolling20 mean` and breakout close to sit at least `0.5 ATR` above a `60-bar` rolling HVN proxy before allowing the S1 trade.
- `S1 Entry-Fixed ATR Budget`: replace dynamic S1 ATRVT with an entry-fixed ATR budget weight using the current adopted `S1 90d` ATRVT scale sampled at entry.
- `S1 Time-Decay Exit (6 bars)`: if a breakout trade fails to reach `+2.5 ATR` expansion inside `6` bars, force-close at the `6th` bar close.