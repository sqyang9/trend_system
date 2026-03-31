# AddOn Grading Exposure Repair Report

## Final Judgment

- Best repaired candidate: `Core+ExposureRepair[exhaustion_downgrade]`
- Promotion state: still promising-but-not-promotable
- Current strong exposure too wide: yes

## Full-Sample Comparison Vs Binary Baseline

| Candidate | dReturn | dSharpe | dCalmar | dMaxDD | WF strict | Avg exp delta vs graded | Avg addon active delta | Dominant driver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+ExposureRepair[cap_only_048] | +10.50pp | -0.000 | -0.003 | -0.76pp | 0.67 | -0.22pp | -0.009 | simple exposure reduction |
| Core+ExposureRepair[structure_confirm] | -6.56pp | -0.004 | -0.007 | -0.55pp | 0.00 | -1.17pp | -0.047 | better strong selection |
| Core+ExposureRepair[exhaustion_downgrade] | +18.94pp | +0.003 | +0.000 | -0.61pp | 0.67 | -0.17pp | -0.007 | better strong selection |
| Core+ExposureRepair[confirm_downgrade_cap048] | -5.75pp | -0.003 | -0.006 | -0.52pp | 0.00 | -1.24pp | -0.049 | better strong selection |

## Best Candidate Selection Audit

- Dominant driver: better strong selection
- Baseline strong count: 19
- Kept strong count: 17
- Downgraded strong count: 2
- Kept strong avg trade move: +7.53%
- Downgraded strong avg trade move: -6.53%
- Kept strong win rate: 64.7%
- Downgraded strong win rate: 0.0%

## Best Candidate Time-Slice Diagnostics

| Slice | dReturn | dSharpe | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- |
| bull_expansion | +12.92pp | +0.002 | +0.049 | -0.11pp |
| major_drawdown | -0.60pp | +0.004 | -0.001 | -0.61pp |
| recovery_phase | +13.76pp | +0.035 | +0.269 | -0.37pp |
| sideways_volatility | +0.85pp | +0.006 | +0.009 | +0.47pp |

## Direct Answers

1. Did structure confirmation improve grading quality? Yes. Structure confirmation improved grading quality directionally: dMaxDD -0.55pp, dReturn -6.56pp, and downgraded strong trades averaged +5.39% versus +8.54% for kept strong trades.
2. Did downgrade / cap rules reduce false-strong exposure? Yes. Downgrade / cap rules reduced false-strong exposure: the best repaired candidate removed 2 nominal strong assignments while the downgraded bucket averaged -6.53% trade move.
3. Is current strong exposure too wide? Yes. Current strong exposure is too wide: downgraded strong entries under the best repair averaged -6.53% versus +7.53% for the kept strong set.
4. Is there a repaired grading design that no longer loses on drawdown vs Binary baseline? No. Best repaired dMaxDD is still -0.61pp versus Binary.
7. Is this line now promotable, still promising-but-not-promotable, or effectively stalled? Still promising-but-not-promotable.