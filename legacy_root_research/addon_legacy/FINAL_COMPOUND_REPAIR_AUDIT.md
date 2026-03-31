# Final Compound Repair Audit

## Final Judgment

- Best compound repair candidate: `Core+CompoundRepair[close30_gate_to_base]`
- Branch status: promising-but-not-promotable archive
- Freeze recommendation: freeze as promising-but-not-promotable archive

## References

- Current exhaustion baseline dReturn vs Binary: +18.94pp
- Current exhaustion baseline dMaxDD vs Binary: -0.61pp
- Current best refinement (`sq25_base_all`) dReturn vs Binary: +20.36pp
- Current best refinement (`sq25_base_all`) dMaxDD vs Binary: -0.53pp
- Current best refinement WF strict: 0.67

## Candidate Table

| Candidate | dRet vs Binary | dMaxDD vs Binary | dRet vs sq25 | dMaxDD vs sq25 | WF strict | Exp delta vs sq25 | Affected remaining strong | Driver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+CompoundRepair[close30_gate_to_base] | +21.79pp | -0.50pp | +1.43pp | +0.03pp | 0.67 | -0.07pp | 3 | better strong selection |
| Core+CompoundRepair[close30_cap044] | +20.93pp | -0.52pp | +0.57pp | +0.01pp | 0.67 | -0.03pp | 3 | better strong selection |
| Core+CompoundRepair[shortsq_light_structure_gate] | +22.58pp | -0.53pp | +2.22pp | +0.00pp | 0.67 | -0.14pp | 1 | better strong selection |

## Best Candidate Audit

- Dominant driver: better strong selection
- Remaining strongs affected: 3
- Affected avg trade move: -1.28%
- Affected win rate: 33.3%
- Unaffected remaining strong avg trade move: +15.05%
- Avg exposure delta vs sq25_base_all: -0.07pp
- Avg addon weight when active vs sq25_base_all: -0.003
- Stress delta vs same scheme: Return +0.52pp, MaxDD +0.05pp
- Secondary veto thresholds: {'type': 'close30_gate_to_base', 'affected_count': 3, 'trend_friendly_share_pct': 75.0}

## Direct Answers

1. Did any compound repair fully close the remaining drawdown gap? No. Best compound repair still leaves dMaxDD vs Binary at -0.50pp.
2. Was the gain real selection repair or simple suppression? Real selection repair. The affected remaining strong subset averages -1.28% while average exposure only changes -0.07pp versus sq25_base_all.
3. Is the line finally promotable? No.
4. If not, should this branch now be frozen as promising-but-not-promotable archive? Yes. This final compound repair audit did not clear the remaining drawdown bar, so the branch should now be frozen as a promising-but-not-promotable archive.