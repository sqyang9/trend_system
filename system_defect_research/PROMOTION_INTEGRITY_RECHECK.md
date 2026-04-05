# Promotion Integrity Recheck

## Purpose

- Recheck whether the recently promoted combo mainline contains any additional "pseudo-promotion" layers after the ATR alignment bug was found.
- Separate:
  - genuinely active promoted layers
  - stale promotion headlines

## Confirmed Findings

### 1. Old ATRVT promotion headline was stale

- The previously promoted ATRVT layer was wired through a broken ATR alignment path.
- `atr_scale` had collapsed to `1.0x` across the whole series.
- Therefore the old combo headline that assumed live ATRVT effect should no longer be treated as canonical.

### 2. ATRVT is now truly active after the fix

- After fixing ATR alignment:
  - `atr_scale` unique values: `11930`
  - range: `0.35 -> 1.50`
  - mean: `1.0177`
- Active bars with non-`1.0x` ATR scaling:
  - `S1`: `3380`
  - `S2`: `1562`

### 3. HV85 force is genuinely active

- `HV85`-forced high-churn bars: `2405`
- flip-defined high-churn bars: `6797`
- overlap bars: `950`
- bars where instability state changes vs no-HV version: `1455`

### 4. High-churn qualification path is genuinely active

- strict-and-breakout rows with HV force:
  - `161`
- strict-and-breakout rows without HV force:
  - `152`
- target-weight bars changed by HV force:
  - `26`

## Integrity Verdict

- No second fully-empty promoted layer has been found so far.
- Current understanding:
  - `ATRVT` was the only confirmed pseudo-promotion layer in the recent combo promotion path.
  - `HV85` is active.
  - high-churn qualification is active.
  - live/dashboard reporting fields for these layers are real, not placeholders.

## Corrected Promotion Baseline

- After the ATR fix and corrected rerun:
  - repaired current formal mainline headline:
    - `Return 2956.62% / Calmar 2.601 / MaxDD -28.15%`

## ATRVT Parameterization Progress

- `180d med / 0.35-1.50 both`
  - repaired combo base replay:
    - `2946.79% / 2.574 / -28.41%`
- `90d med / 0.35-1.50 both`
  - first strong challenger:
    - `3114.74% / 2.762 / -27.02%`
- `60d med / 0.35-1.50 both`
  - current strongest screened challenger:
    - `3327.75% / 2.988 / -25.59%`

## Current Read

- Promotion integrity is now materially cleaner than before.
- The remaining task is no longer to debug whether ATRVT exists.
- The remaining task is to decide whether the corrected ATRVT contract should be promoted from:
  - `180d`
  - to `90d`
  - or already to `60d`
