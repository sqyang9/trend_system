# Background Indicators

## Purpose

This document records repository-level background indicators that can be reused as system context, gating data, or reserve research inputs.

Some indicators in this document are now part of the adopted mainline. Their formulas still matter as shared background data because the same series may be reused in future research and live reporting.

## Active Background Proxies

### ATR Vol-Targeting Proxy

Current implementation path:

- shared background layer in [volatility_background.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/volatility_background.py)
- script: [v171_volatility_proxy_system_upgrade.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/v171_volatility_proxy_system_upgrade.py)
- background data export: [volatility_proxy_background_data.csv](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/volatility_proxy_background_data.csv)

Definition:

- timeframe: `4h`
- `ATR14`
- `ATR% = ATR14 / close`
- trailing reference: `180d` rolling median of `ATR%`
- scaler:
  - `atr_scale = trailing_180d_median_atr_pct / current_atr_pct`
- clipping band:
  - `0.35x ~ 1.50x`

Interpretation:

- when current volatility is above recent history, `atr_scale < 1.0`
- when current volatility is below recent history, `atr_scale > 1.0`
- this is a sleeve-level volatility target proxy, not a signal-quality score

Current tested use:

- `S2-only` sleeve scaling
- `S1 + S2` sleeve scaling

Research meaning:

- this is the current best system-level answer to the `W06` defect family
- it addresses position-size mismatch under volatility expansion rather than trying to rescue the path only through local stop tweaks

Current readout:

- best ATR-only probe in independent research:
  - `P0: ATR vol-targeting on S1+S2`
  - `Return 3072.90%`
  - `Calmar 3.073`
  - `MaxDD -24.17%`
- current adopted mainline package using this indicator in the full combo:
  - `Return 3179.90%`
  - `Calmar 2.872`
  - `MaxDD -26.19%`
  - adopted asymmetric contract:
    - `S1 = ATRVT_90D_med_035_150`
    - `S2 = ATRVT_60D_med_035_150`

Status:

- promoted into the current official mainline as `S1 + S2 ATR vol-targeting`
- still reusable as shared background data for future system research

### HV Percentile Proxy

Current implementation path:

- shared background layer in [volatility_background.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/volatility_background.py)
- script: [v171_volatility_proxy_system_upgrade.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/v171_volatility_proxy_system_upgrade.py)
- background data export: [volatility_proxy_background_data.csv](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/volatility_proxy_background_data.csv)

Definition:

- timeframe: `4h`
- return base: log returns on `close`
- short realized volatility:
  - rolling `14d` standard deviation
- annualization:
  - `HV14_ann = std(log_returns, 14d) * sqrt(6 * 365)`
- historical rank:
  - current `HV14_ann` percentile rank inside trailing `180d` history

Current thresholds tested:

- `HV >= 85 percentile`
- `HV >= 90 percentile`

Interpretation:

- this is a realized-volatility environment thermometer
- it is the current repository proxy for missing `DVOL / IV` style context
- it should be treated as background regime information, not as an alpha signal by itself

Current tested use:

- if `HV percentile` is above threshold, force `Core` re-entry into the `high-churn` qualification path earlier
- it does not create a new re-entry gate
- it only changes when the stricter gate is invoked

Research meaning:

- this is the current best first-pass answer to the `W11` defect family
- it helps reduce false re-entries in choppy-downtrend windows, but by itself has weaker economic value than the ATR sizing layer

Current readout:

- best HV-only probe in independent research:
  - `P1: HV pct >= 90 -> force HC gate`
  - `W11 entries 3`
  - `W11 quick re-FLAT 14d 33.3%`
  - `W11 quick re-FLAT 30d 66.7%`
- current adopted mainline package uses:
  - `HV percentile >= 85 -> force high-churn core qualification`

Status:

- promoted into the current official mainline as background forcing data
- still not a standalone alpha or standalone promotable rule family by itself

## Current Best Combined Independent Probe

- promoted package:
  - `S1 + S2 ATR vol-targeting`
  - plus `HV percentile >= 85 -> force high-churn core qualification`
- pre-promotion combo audition:
  - `Return 2995.89%`
  - `Calmar 3.044`
  - `MaxDD -24.17%`
- current official mainline after promotion packaging:
  - `Return 3179.90%`
  - `Calmar 2.872`
  - `MaxDD -26.19%`
- window readout:
  - `W06 DD/Exp -47.4%` vs baseline `-49.5%`
  - `W11 entries 3` vs baseline `4`
  - `W11 quick14 33.3%` vs baseline `50.0%`

Status:

- strongest result from the system-defect branch
- audited and promoted into the current official mainline

## Governance

- do describe `ATR vol-targeting` and `HV percentile forcing` as adopted mainline behavior when you refer to the current combo mainline
- do preserve both as reusable background indicators for future system-level research
