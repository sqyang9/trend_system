# Mainline Risk Notes

## Locked Mainline

- Current canonical package:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - `S1 = ATRVT_90D_med_035_150`
  - `S2 = ATRVT_60D_med_035_150`
  - current `S1 gate contract = S1_VP_LB60_EA050_VR120`

## Known Structural Costs

- `W04`-style V rebounds can be under-captured.
  - This is an intentional cost of the high-churn qualification regime.
  - Do not loosen the gate impulsively in live trading because of a single missed rebound.
- `HV85` is a governance / defect-repair layer.
  - It helps bring forward the strict high-churn gate.
  - It is not the primary return engine.
- `ATRVT` is a volatility adaptation layer, not a signal source.
  - Large scaling changes should be read as environment shifts, not as discretionary trade prompts.

## Promotion Note

- The former `S1 volume-profile proxy gate` reserve line is now promoted into the locked mainline.
- Future `S1 gate` changes should be treated as mainline changes, not reserve tweaks.

## Governance Rule

- Locked mainline first.
- Runtime verification second.
- Monitoring and risk reporting always on.
- Promotion only after the candidate clears:
  - promotion audit
  - landing audit
  - implementation parity
  - documentation sync
