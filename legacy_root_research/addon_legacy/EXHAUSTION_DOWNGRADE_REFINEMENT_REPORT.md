# Exhaustion Downgrade Refinement Report

## Final Judgment

- Best refinement candidate: `Core+ExhaustionRefine[sq25_base_all]`
- Line status: still promising-but-not-promotable

## Reference

- Current exhaustion baseline dReturn vs Binary: +18.94pp
- Current exhaustion baseline dMaxDD vs Binary: -0.61pp
- Current exhaustion baseline WF strict: 0.67

## Candidate Table

| Candidate | dRet vs Binary | dMaxDD vs Binary | dRet vs CurrentEx | dMaxDD vs CurrentEx | WF strict | Exp delta vs CurrentEx | Affected strong count | Affected avg move | Driver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+ExhaustionRefine[sq25_cap044] | +19.51pp | -0.58pp | +0.57pp | +0.03pp | 0.67 | -0.09pp | 5 | -0.71% | better strong selection |
| Core+ExhaustionRefine[sq25_cap042] | +19.70pp | -0.57pp | +0.76pp | +0.04pp | 0.67 | -0.12pp | 5 | -0.71% | better strong selection |
| Core+ExhaustionRefine[sq25_base_all] | +20.36pp | -0.53pp | +1.42pp | +0.08pp | 0.67 | -0.22pp | 5 | -0.71% | better strong selection |
| Core+ExhaustionRefine[sq35_highwidth_cap044] | +19.15pp | -0.60pp | +0.21pp | +0.01pp | 0.67 | -0.06pp | 3 | -0.38% | better strong selection |

## Best Candidate Bad-Strong Pattern

- Affected strong count: 5
- Affected strong avg trade move: -0.71%
- Affected strong win rate: 60.0%
- Unaffected strong avg trade move: +10.97%
- Current exhaustion thresholds: {'high_range_cut': 3.033501663231525, 'high_width_cut': 0.6108376196089205, 'low_efficiency_cut': 0.44459205136721414, 'high_stretch_cut': 0.9783005365135933, 'downgraded_strong_count': 2}
- Refinement thresholds: {'squeeze_cut': 32.0, 'width_cut': None, 'affected_count': 5, 'mode': 'base', 'cap_weight': None}

## Direct Answers

1. Did refinement improve on the current exhaustion_downgrade baseline? Yes. Core+ExhaustionRefine[sq25_base_all] improves the current exhaustion baseline by dReturn +1.42pp and dMaxDD +0.08pp.
2. What specific bad-strong pattern is being isolated? The bad-strong pattern is a short-squeeze breakout bucket: relatively low squeeze persistence, then oversized post-breakout expansion. The worst subset is the extreme blow-off case with both high bar-range and high stretch-vs-box; the best refinement then downgrades the remaining short-squeeze strong bucket to base.
3. Is the improvement still driven by better strong selection? Yes.
4. Does any refined candidate fully repair drawdown underperformance vs Binary baseline? No. Best refined dMaxDD vs Binary is still -0.53pp.
5. Is the line now promotable, still promising-but-not-promotable, or exhausted? Still promising-but-not-promotable.