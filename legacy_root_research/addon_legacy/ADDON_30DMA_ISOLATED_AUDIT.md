# AddOn 30DMA Isolated Audit

## Final Judgment

- Best isolated 30DMA candidate: `Grading30DMA[close_above_30dma|gate]`
- Best use mode: strong eligibility gate

## Candidate Table

| Candidate | dReturn | dSharpe | dCalmar | dMaxDD | WF strict | Activation delta vs graded | Avg addon active delta | Driver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Grading30DMA[close_above_30dma|gate] | +19.07pp | +0.003 | +0.000 | -0.61pp | 0.67 | -0.44pp | -0.002 | better strong selection |
| Grading30DMA[close_above_30dma|downgrade] | +15.80pp | +0.002 | -0.001 | -0.69pp | 0.67 | +0.00pp | -0.003 | better strong selection |
| Grading30DMA[close_above_30dma|cap] | +15.15pp | +0.001 | -0.002 | -0.70pp | 0.67 | +0.00pp | -0.001 | simple exposure reduction |
| Grading30DMA[dma30_slope_up|gate] | -50.52pp | -0.016 | -0.022 | -0.72pp | 0.00 | -2.62pp | -0.014 | simple exposure reduction |
| Grading30DMA[dma30_slope_up|downgrade] | -6.26pp | -0.005 | -0.008 | -0.72pp | 0.00 | +0.00pp | -0.016 | simple exposure reduction |
| Grading30DMA[dma30_slope_up|cap] | +3.26pp | -0.002 | -0.005 | -0.72pp | 0.33 | +0.00pp | -0.008 | simple exposure reduction |
| Grading30DMA[close_and_slope|gate] | -47.23pp | -0.015 | -0.020 | -0.61pp | 0.00 | -2.83pp | -0.015 | simple exposure reduction |
| Grading30DMA[close_and_slope|downgrade] | -4.99pp | -0.004 | -0.007 | -0.69pp | 0.00 | +0.00pp | -0.017 | simple exposure reduction |
| Grading30DMA[close_and_slope|cap] | +3.97pp | -0.002 | -0.005 | -0.70pp | 0.33 | +0.00pp | -0.009 | simple exposure reduction |

## Best Candidate Detail

- Definition: A. close > 30DMA
- Action: strong eligibility gate
- Affected strong count: 3
- Kept strong avg trade move: +7.43%
- Downgraded/gated strong avg trade move: -1.28%

## Direct Answers

5. In isolated testing, does the 30DMA filter add real value? No. In isolated testing the 30DMA layer mostly behaves like background suppression rather than a true quality repair.
6. Is 30DMA best used as gate, downgrade, or cap? strong eligibility gate is best in this isolated audit, using A. close > 30DMA.