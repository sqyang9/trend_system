# BTC Core Risk-Off Level Report

## Final Judgment

- This round answers one question only: how far the BTC core should be reduced once Risk-Off is active, and whether a with-core framework still beats a no-core framework.
- Recommended core_off_weight: 0.00
- Preferred aligned structure: Core+AddOnOverlay+EMA220_OFF_0.00
- With-core vs no-core: WITH-CORE FRAMEWORK IS MORE REASONABLE
- Promotion status: NO. This raises confidence in full-flat Risk-Off, but it is still not enough to rewrite the locked working baseline.

## Method

- Overlay sleeve remains the locked AddOnOverlay artifact under the default tuple.
- The only new validation dimension is the Risk-Off core-off level.
- Core timing stays causal: signal at 4h close t, execution at t+1.

## Core-Off Grid

| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | dRet vs AddOn | dSharpe | dCalmar | dMaxDD improve | Avg Core Exposure% | Risk-Off Active% | State Changes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+AddOnOverlay+EMA200_OFF_0.00 | 1319.64 | 53.15 | 1.007 | 1.048 | -50.73 | 1.055 | +358.92 | +0.216 | +0.412 | +21.88 | 58.9 | 41.1 | 224 |
| Core+AddOnOverlay+EMA200_OFF_0.25 | 1334.18 | 53.40 | 0.994 | 0.949 | -56.30 | 1.046 | +373.46 | +0.203 | +0.313 | +16.31 | 69.2 | 41.1 | 5715 |
| Core+AddOnOverlay+EMA200_OFF_0.35 | 1317.88 | 53.12 | 0.977 | 0.907 | -58.54 | 1.042 | +357.16 | +0.185 | +0.272 | +14.07 | 73.3 | 41.1 | 5715 |
| Core+AddOnOverlay+EMA200_OFF_0.50 | 1270.73 | 52.29 | 0.941 | 0.846 | -61.82 | 1.038 | +310.01 | +0.150 | +0.210 | +10.79 | 79.5 | 41.1 | 5715 |
| Core+AddOnOverlay+EMA220_OFF_0.00 | 1626.59 | 58.04 | 1.068 | 1.097 | -52.90 | 1.064 | +665.87 | +0.277 | +0.462 | +19.71 | 58.9 | 41.1 | 204 |
| Core+AddOnOverlay+EMA220_OFF_0.25 | 1561.07 | 57.06 | 1.038 | 0.992 | -57.51 | 1.051 | +600.35 | +0.247 | +0.357 | +15.09 | 69.2 | 41.1 | 5704 |
| Core+AddOnOverlay+EMA220_OFF_0.35 | 1510.14 | 56.28 | 1.014 | 0.946 | -59.47 | 1.047 | +549.42 | +0.223 | +0.311 | +13.14 | 73.3 | 41.1 | 5704 |
| Core+AddOnOverlay+EMA220_OFF_0.50 | 1411.16 | 54.69 | 0.968 | 0.875 | -62.49 | 1.041 | +450.44 | +0.177 | +0.240 | +10.12 | 79.5 | 41.1 | 5704 |

## Structural Comparison

- AddOn-only baseline: Return 960.72%, Sharpe 0.791, MaxDD -72.61%
- No-core baseline (`SwitchingOverlay`): Return 470.51%, Sharpe 0.933, MaxDD -34.49%
- Preferred with-core structure: Return 1626.59%, Sharpe 1.068, MaxDD -52.90%

## Minimal Stress Check

- Preferred structure stress delta vs default: Return +80.03pp, Sharpe +0.014, MaxDD improve -0.11pp
- AddOn-only stress delta vs default: Return +0.00pp, Sharpe +0.000, MaxDD improve +0.00pp

## Risk Windows

| Window | B&H | AddOn-only | No-core | Preferred with-core |
| --- | --- | --- | --- | --- |
| covid_crash_2020 | -14.67 | -10.24 | 15.25 | -3.16 |
| china_deleveraging_2021 | -28.76 | -26.97 | 0.27 | -2.39 |
| bear_2022 | -64.65 | -59.22 | -2.48 | -43.76 |
| ftx_shock | -13.03 | -10.75 | 0.00 | -10.54 |

## Final Answer

- Risk-Off trigger should reduce the BTC core to 0.00 under the current aligned evidence set.
- Full flat still beats keeping 25%/35%/50% residual core. The best partial structure is Core+AddOnOverlay+EMA220_OFF_0.25, but it still trails Core+AddOnOverlay+EMA220_OFF_0.00.
- The with-core framework remains more reasonable than the no-core framework. Pure no-core `SwitchingOverlay` is more defensive, but it gives up too much absolute return and participation.
- This round raises confidence in the full-flat Risk-Off setting, but it is still not enough to promote a new working baseline.
