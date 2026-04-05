# Research History

## S1 Volume-Profile Proxy Promotion

After the asymmetric ATRVT package was locked, an independent `future_direction_research/` branch tested whether `Sleeve #1` breakouts could be filtered by a lightweight volume-profile proxy without changing the rest of the mainline.

Promoted winner:

- `S1_VP_LB60_EA050_VR120`
- `lookback = 60`
- `HVN escape = 0.50 ATR`
- `volume ratio20 = 1.20`

Result:

- current latest official mainline:
  - `Formal + ATRVT_S1H90_S2H60 + S1_VP_LB60_EA050_VR120 + EMA250_CLOSE3_HC23_STRICT_BREAKOUT4_HV85FORCE`
  - `Return 3321.25%`
  - `Sharpe 1.386`
  - `Calmar 3.209`
  - `MaxDD -23.81%`

Interpretation:

- the latest promoted gain did not come from changing `Core`
- it came from making `S1` more selective in low-quality breakout zones
- the winner later passed promotion audit, landing audit, implementation parity, and final promotion replay

## Volatility Proxy System Upgrade

An independent `system_defect_research/` branch was extended to test whether the `W06` and `W11` defects could be addressed at the system level without changing the locked official baseline directly.

The branch explicitly treated those windows as defect revealers, not as optimization targets.

Two proxy layers were introduced:

- `ATR`-based sleeve vol-targeting
- `HV percentile` as a realized-volatility proxy for missing `DVOL / IV` style context

### P0: ATR Vol-Targeting

Objective:

- reduce system-level volatility mismatch under extreme expansion rather than only tightening local sleeve stops

Implementation:

- `ATR14` on `4h`
- convert to `ATR% = ATR / close`
- compare current `ATR%` to trailing `180d` median `ATR%`
- scale sleeve weights with clipping inside `0.35x ~ 1.50x`

Tested variants:

- `S2-only ATR VT`
- `S1 + S2 ATR VT`

Result:

- both improve on the official mainline
- strongest variant is `S1 + S2 ATR VT`
- current readout:
  - `Return 3072.90%`
  - `Calmar 3.073`
  - `MaxDD -24.17%`

Interpretation:

- this is the current highest-ROI independent answer to the `W06` defect family
- it behaves like a system-level shock absorber instead of a stop-parameter tweak

### P1: HV Percentile Core-Gate Forcing

Objective:

- detect choppy or overheated environments earlier than the current `core flips`-only high-churn detector

Implementation:

- `HV14` from rolling `14d` log-return volatility on `4h`
- annualized
- ranked inside trailing `180d`
- when `HV percentile` is high enough, force `Core` into the stricter `high-churn` qualification path earlier

Tested variants:

- `HV >= 85 percentile`
- `HV >= 90 percentile`

Result:

- this branch reduces `W11` false re-entry counts
- best first-pass variant is `HV >= 90`
- current readout:
  - `W11 entries 4 -> 3`
  - `W11 quick14 50.0% -> 33.3%`
  - `W11 quick30 75.0% -> 66.7%`
- however, it is weaker than the official mainline on full-sample headline metrics if used alone

Interpretation:

- `HV percentile` is a useful background detector
- by itself it is not yet a promoted standalone upgrade

### Current Combined Readout

Best combined independent probe:

- `S1 + S2 ATR vol-targeting`
- plus `HV percentile >= 85 -> force high-churn core qualification`

Result:

- `Return 2995.89%`
- `Calmar 3.044`
- `MaxDD -24.17%`

Status:

- strongest result from the system-defect branch
- later passed combo audition, landing audit, and implementation pass
- later exposed a real ATR alignment bug in the first promotion implementation
- corrected ATRVT replay was rebuilt and re-audited
- sleeve-level ATRVT refinement then found:
  - symmetric `H60/H90` are strong economics challengers
  - but the best promotion-grade contract is asymmetric
  - adopted current official contract: `S1 90d / S2 60d`
- current official mainline after the asymmetric ATRVT promotion:
  - `Return 3179.90%`
  - `Calmar 2.872`
  - `MaxDD -26.19%`
  - this later became the immediate predecessor to the current `S1 volume-profile proxy` promoted mainline

## Regime Detector Reserve Branch

- Independent folder created: `regime_detector_research/`
- Objective:
  - test whether a separate multi-dimensional regime layer can improve on the adopted mainline without reopening the baseline itself
- Progression:
  - sparse prototype: too weak / too rare
  - looser `vol_soft_off`: real positive effect
  - refined `distribution` definition: able to remove part of weak `S1B`
  - mainline-like isolated audit: credible challenger
  - event-level `S2 tightened stop` replay: advantage shrinks materially
- Final current readout:
  - `SoftOffOnly` and `SoftOff + S1 lock` both beat the adopted baseline on headline metrics
  - both also worsen `Worst3m`, `Worst6m`, and `RecoveryDays`
  - adding `S2 tightened stop` gives back most of the earlier edge
- Current status:
  - preserve as lightweight reserve research
  - not promoted into the adopted mainline

## Module Refinement First Pass

An isolated `module_refinement_research/` folder was opened to test whether small local improvements could clearly beat the adopted mainline before any deeper audit.

The first-pass shortlist was:

- `core_slope_significance_filter`
- `s1_momentum_gate_tightening`
- `s2_divergence_confirmation`

Result:

- all three were screened directly against the adopted baseline
- none showed a clear advantage
- all three were first-pass rejected

Interpretation:

- the adopted mainline is not obviously under-optimized at the local module level
- small “clean-up” refinements are currently more likely to damage participation than to produce meaningful portfolio improvement

## S2 Time / Progress Stop Recheck

An independent `s2_time_stop_research/` branch was reopened after the initial timeout idea failed to trigger.

Important correction:

- the original “exit if `range_mid_20` is not touched within `N` bars” idea was structurally incompatible with native adopted `S2`
- native `S2B` already enters after reclaim conditions that include `close >= range_mid_20`

The corrected branch therefore tested:

- if `S2` fails to reach `entry + 1.4 ATR` within `N` 4h bars
- force exit at the deadline close

Result:

- replay now aligned closely with native adopted `S2`
- `TS8 / TS12 / TS16` all still failed to beat the adopted mainline
- best candidate `ProgressTS16` remained slightly worse on return, Calmar, and MaxDD

Current status:

- corrected branch completed
- rejected

## Stage 1: Core Trend Strategy

The current BTC system started from the long-only mother line built on `squeeze_release_20`.

- Strategy role: low-frequency BTC trend-following system
- Current `research_optimal`: `lb20_stop3.2_trail5.0_beoff`
- Signal idea: wait for compression, then enter a breakout release inside a bullish higher-timeframe trend regime
- Trend logic: price above long EMA, positive EMA slope, mild ADX confirmation, acceptable breakout bar quality
- Trade template: a small number of trend entries, few trades, large winners, exits driven mainly by ATR trailing rather than fixed profit taking
- Execution design: signal observed on completed 4h bar, position change modeled under the locked execution tuple rather than idealized same-bar assumptions

This line replaced the old `v85` long+short line as the primary research object because it behaved more like a real BTC trend mother and less like a fragile multi-leg backtest artifact.

## Stage 2: Execution Alignment

The repository then separated default research from stress validation.

Default execution tuple:

- `next_bar_open`
- `legacy_bar_extrema`
- `midpoint`
- `full_model`

Stress / gate tuple:

- `live_runner_next_5m_close`
- `segment_path_same_bar`
- `pessimistic`
- `full_model`

Execution alignment was validated by:

- keeping bar-level causality explicit
- modeling entry and exit timing on the next execution event rather than current-bar hindsight
- rerunning key modules under the stress tuple
- keeping stress/gate conclusions separate from default-tuple research conclusions

This alignment step is the main reason later portfolio-layer conclusions were split into `exploratory`, `aligned but preliminary`, and promotable states instead of being treated as equal by default.

## Stage 3: AddOn Overlay

After the mother line stabilized, the system was reframed as an overlay on top of BTC buy-and-hold.

Structure:

- Core BTC holding
- Binary AddOn trend sleeve

Binary AddOn overlay means:

- hold the BTC core continuously
- add an extra trend sleeve when the validated long-only signal is active

Relative to pure BTC buy-and-hold, the committed overlay integration result showed:

- Return `960.72%` vs `856.16%`
- CAGR `46.14%` vs `43.73%`
- Sharpe `0.791` vs `0.750`
- Calmar `0.636` vs `0.568`
- MaxDD `-72.61%` vs `-77.04%`

This is why `Core BTC holding + Binary AddOn overlay` first became the locked baseline structure.

## Stage 4: Risk-Off Research Line

Risk-Off was explored as a portfolio module, then aligned, then repeatedly tested for promotion.

Key structures tested:

- EMA200 / EMA210 / EMA220 regime triggers
- flat core exits
- two-stage exits
- re-entry timing repairs

The line progressed through:

- exploratory allocation study
- execution-aligned validation
- core-off-weight study
- promotion v1
- promotion v2
- narrow re-entry checks
- authorized core re-entry deep dive

Final result:

- directionally valid
- execution-aligned
- promotion frozen

Why promotion failed:

- the line helped on downside control
- the EMA200-220 family behaved like a stable plateau, not a single lucky point
- but bull / recovery opportunity cost remained too large
- even the best late repair candidate, `RO_EMA220_REENTRY_CLOSE_HOLD_3`, still failed to remove promotion blockers
- the later deep dive confirmed staged restoration should be closed, and full-restoration variants improved internal understanding but still did not beat the archived best repair
- after the deep dive, the line was re-frozen rather than kept exploratory

Risk-Off therefore became an archived direction, not an active baseline module.

## Stage 5: AddOn Grading

Once Risk-Off was frozen, active extension research shifted to smarter AddOn sizing.

Current grading line:

- `Core + GradedAddOn[compression_breakout]`

Features:

- `compression_quality`
- `squeeze_count`
- `breakout_distance_atr`

Base tier weights:

- `weak = 0.25`
- `base = 0.35`
- `strong = 0.50`

Key result:

- full sample vs binary AddOn: `+14.41pp Return`, `+0.001 Sharpe`, `-0.002 Calmar`, `-0.72pp MaxDD improvement`
- OOS: `strict win ratio = 1.00`, `avg delta Return = +4.52pp`, `avg delta Sharpe = +0.035`, `avg delta Calmar = +0.202`

Status:

- promising
- not promotable yet

The main blocker is still slight MaxDD degradation versus the binary AddOn baseline.

## Stage 6: Exposure Engine

After the repair line stalled, research moved up one layer from AddOn grading to portfolio-level exposure design.

### E1: Constant Exposure Mapping

Result:

- best constant AddOn baseline: `Core+ConstAddOn[1.00x]`
- this beat `Core+BinaryAddOn` on both return and drawdown
- interpretation: the old Binary AddOn baseline was materially under-deployed

### E2: Minimal Dynamic Exposure

Result:

- no tested minimal dynamic schedule beat `Core+ConstAddOn[1.00x]`
- constant full deployment remained the efficient frontier
- `E3` promotion audit therefore did not open

### Deployment Audit

Result:

- `Core+ConstAddOn[1.00x]` cleared the deployment-grade robustness audit
- promotion to new default baseline was recommended

## Stage 7: Second Sleeve Discovery

The next research stage moved away from repairing the current AddOn sleeve and toward discovering a genuinely different second sleeve that could improve portfolio path quality on top of `Core+ConstAddOn[1.00x]`.

### S1: Candidate Family Generation

Initial candidate families:

- `washout_reversal_reclaim`
- `pullback_reclaim_continuation`
- `range_rotation_mean_reversion`
- `failed_break_retest_reclaim`

Immediate rejections as too similar to the current sleeve:

- `compression_breakout` variants
- `squeeze_release` variants
- `quality_breakout` variants
- `donchian breakout` lookback variants
- `structure-confirm breakout` variants
- breakout grading / cap / downgrade wrappers

### S2: Candidate Audit Results So Far

#### `washout_reversal_reclaim`

Result:

- orthogonal in timing
- not usefully complementary
- rejected

Why it failed:

- active overlap was low and entries mostly arrived while the current sleeve was flat
- but standalone return quality was poor
- portfolio layering on top of `Const1x` worsened return and drawdown instead of helping recovery path

#### `pullback_reclaim_continuation`

Result:

- narrative fit was plausible
- portfolio value was not
- rejected

Why it failed:

- standalone behavior was weak: `-1.71%` total return, `-71.21%` MaxDD
- layered portfolio effect vs `Const1x` was negative: `dReturn -1.71pp`, `dMaxDD -0.24pp`
- early recovery contribution was actively harmful: `dReturn -9.83pp`, `dMaxDD -1.88pp`
- overlap with the current sleeve was too high to claim useful orthogonality:
  - active overlap `15.55%`
  - active return correlation `0.667`

### Current Discovery State

- `washout_reversal_reclaim`: rejected
- `pullback_reclaim_continuation`: rejected
- next priority candidate: `range_rotation_mean_reversion`
- reserve candidate after that: `failed_break_retest_reclaim`

## Stage 8: Official Two-Sleeve Baseline

`range_rotation_mean_reversion` then advanced through S3 promotion audit and was approved as official `Sleeve #2`.

Role definition:

- not a recovery helper
- not a breakout clone
- a drawdown / sideways-volatility / chop diversification sleeve

Portfolio conclusion:

- official default combination became `Core BTC holding + ConstAddOn[1.00x] + RangeRotation`
- `Core+BinaryAddOn` was reduced to legacy reference only
- second-sleeve discovery was completed for this round

## Stage 9: Total Exposure Cap Governance Audit

The final two-sleeve portfolio was then audited under true hard total-exposure caps.

Required grid:

- `1.0x`
- `1.5x`
- `2.0x`
- `2.5x`
- `3.0x`

Final conclusion:

- the cap curve was effectively monotone improving up to `3.0x`
- `3.0x` was the best overall tradeoff and the approved governance cap
- `2.5x` remains fallback only if governance ever tightens later
- lower caps were mainly mechanical suppression of an already validated portfolio edge

## Stage 10: Full-Stack Risk-Off Re-Entry Reopening

After the old core-only Risk-Off line was re-frozen, a new authorized branch reopened one narrower question:

- can Risk-Off be reintroduced as a full-stack cash-like portfolio overlay on top of the formal portfolio
- using low-value / oversold core re-entry rather than late EMA-only restoration

Important scope distinction:

- the old core-only promotion line remained archived
- the new branch used a different architecture:
  - normal state: `Core + Sleeve #1 + Sleeve #2`
  - Risk-Off state: all three flatten to cash-like
  - re-entry: core restores first, sleeves participate again only through fresh native trade activity

### 10A: Low-Value Re-Entry Candidate Discovery

The earlier deep dive showed:

- staged restoration should be closed
- trend-rebuild full restoration was the best branch result
- but it still did not beat `RO_EMA220_REENTRY_CLOSE_HOLD_3`

Research then shifted to a clearly different ecology:

- oversold / low-value core restoration

Candidate screening found two serious successors:

- `RO_LOWVALUE_WEEKLY_RSI30_HOLD`
- `RO_LOWVALUE_4H_RSI10_HOLD`

### 10B: Optimistic Pre-Adoption Simulation

An initial full-stack gate simulation showed extremely strong results, but it was later superseded.

Why it was superseded:

- core was truly rerun
- but sleeves were still handled through optimistic post-hoc freezing / resumption of already-generated sleeve paths
- this was useful for direction finding, but not strict enough for adoption

This stage should therefore be treated as:

- exploratory
- directionally important
- not final evidence

### 10C: Strict Event-Level Adoption Audit

The stricter audit reran:

- core
- `Sleeve #1`
- `Sleeve #2`

under full-stack cash-like Risk-Off semantics with `default + stress`.

Formal baseline:

- `Return 1591.16%`
- `Calmar 1.008`
- `MaxDD -57.08%`

Primary candidate:

- `Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD`
- `Return 2722.96%`
- `Calmar 1.747`
- `MaxDD -40.66%`

Secondary candidate:

- `Formal + RO_LOWVALUE_4H_RSI10_HOLD`
- `Return 2799.57%`
- `Calmar 1.487`
- `MaxDD -48.26%`

Stress audit also remained clearly positive relative to the formal baseline.

Current interpretation:

- full-stack Risk-Off / re-entry has advanced from archived curiosity to highest-priority adoption candidate architecture
- `RO_LOWVALUE_WEEKLY_RSI30_HOLD` is the more balanced main candidate
- `RO_LOWVALUE_4H_RSI10_HOLD` is the more aggressive secondary candidate
- harsher-friction finalization is still pending before final adoption closure

## Stage 11: Risk-Off Structure Closure And Final Adoption

The later branch then split into two architecture interpretations:

- core-only Risk-Off overlay
- full-stack cash-like Risk-Off overlay

### 11A: Structure Screen

Result:

- core-only Risk-Off clearly beat full-stack under shared `default + stress`
- the main value came from managing core carry
- forcing `Sleeve #1 / #2` flat was unnecessary suppression rather than added protection

This closed the structure question:

- keep `core-only`
- reject `full-stack`

### 11B: Core-Only Final Adoption Audit

Core-only Risk-Off then completed:

- `default`
- `stress`
- `harsher friction`

on top of the formal portfolio.

This confirmed:

- `RO_LOWVALUE_WEEKLY_RSI30_HOLD` and `RO_LOWVALUE_4H_RSI10_HOLD` both remained strong
- the branch was promotable

### 11C: Sell-Side EMA Replacement Audit

With re-entry mostly locked, the remaining first-layer question was whether the incumbent sell-side EMA should survive.

Weekly branch:

- `WRSI14_30_EMA220`
- `WRSI14_30_EMA250`

4h branch:

- `H4RSI14_10_EMA220`
- `H4RSI14_10_EMA200`

Final result:

- adopted primary version:
  - `Formal + WRSI14_30_EMA250`
- 4h branch winner:
  - `Formal + H4RSI14_10_EMA200`

Why `WRSI14_30_EMA250` won:

- it gave the best overall balance of return, drawdown, Calmar, cluster loss, and recovery burden
- it beat `EMA220` in the weekly branch on path efficiency
- it held up under `default`, `stress`, and `harsher friction`

Portfolio conclusion:

- the formal default portfolio was upgraded from
  - `Core + ConstAddOn[1.00x] + RangeRotation`
- to
  - `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- with:
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`

## Current Official State

The repository is now in this state:

- official default combination: `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted Risk-Off parameters:
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`
- launch status: `LAUNCH_GO`
- approved hard total exposure cap: `3.0x`
- legacy reference: `Core BTC holding + Binary AddOn overlay`
- archived direction: old core-only Risk-Off promotion line
- rejected direction: full-stack cash-like Risk-Off / re-entry overlay
- archived repair line: `compression_breakout -> exhaustion / compound repair`
- closed line: single-sleeve Exposure Engine `E2 / E3`
- completed line: `SECOND_SLEEVE_DISCOVERY`
- second-layer composition readout:
  - adopted default posture: `Core 0.75 / Sleeve1 1.25 / Sleeve2 1.00`
  - superseded prior default posture: `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- current-time entry readout:
  - latest live state is `core_full_s1_0_s2_0`
  - current practical onboarding recommendation is `immediate_full`
- startup warmup readout:
  - `6m-12m` warmup is operationally acceptable
  - `3m` warmup is too short and unstable
- live operating layer:
  - current state panel implemented
  - live decision memo implemented
  - startup / onboarding playbook implemented
- closed line:
  - `SLEEVE3_DISCOVERY_RESET`
  - screened and rejected:
    - `post_dislocation_repricing_climb`
    - `failed_breakdown_reversal_acceptance`
    - `reset_base_reacceptance_v2`
  - `slow_drift_trend_persistence` was not promoted and the line was closed
- ETH transfer study:
  - adopted BTC mainline was transferred to ETH under `1h exec / 4h signal`
  - ETH standalone transfer was directionally valid but materially weaker than BTC
  - `BTC flat -> ETH switch` failed to improve same-window BTC mainline performance
  - ETH switch line was closed
- eligible next directions:
  - deployment / implementation packaging
  - live monitoring / reporting / dashboard layer
  - higher-layer multi-sleeve portfolio architecture
