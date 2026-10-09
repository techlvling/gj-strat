# Intraday pattern search — XAUUSD, 2010–2026

20 pre-declared setups per market, 20 tests (see run_patterns_intraday.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.

**Survivors: 0 of 20, robust (≥ 2 markets): 0.** About 0 would pass by luck.

| Setup · pair | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | survives | robust |
|---|---|---|---|---|---|---|---|---|---|---|
| I3 inside-breakout TP2R · XAUUSD | 191 | 45.026 | -0.009 | -0.148 | 137 | 47.445 | 0.034 | 0.506 | False | False |
| I3 nr7-breakout TP1R · XAUUSD | 167 | 46.707 | -0.016 | -0.251 | 134 | 48.507 | 0.006 | 0.098 | False | False |
| I3 inside-breakout TP1R · XAUUSD | 191 | 46.597 | -0.016 | -0.312 | 137 | 48.175 | 0.006 | 0.110 | False | False |
| I3 nr7-breakout TP2R · XAUUSD | 167 | 42.515 | -0.033 | -0.474 | 134 | 46.269 | 0.061 | 0.765 | False | False |
| I1 ldn-breakout SL1range TP1R · XAUUSD | 1725 | 49.449 | -0.015 | -0.680 | 1355 | 46.494 | -0.050 | -2.004 | False | False |
| I2 prevday-breakout SL0.25ATR TP1R · XAUUSD | 1023 | 49.169 | -0.025 | -0.832 | 831 | 46.089 | -0.091 | -2.700 | False | False |
| I1 ldn-breakout SL1range TP2R · XAUUSD | 1725 | 40.870 | -0.025 | -0.879 | 1355 | 39.041 | -0.040 | -1.295 | False | False |
| I2 prevday-breakout SL0.5ATR TP2R · XAUUSD | 1023 | 42.229 | -0.033 | -1.152 | 831 | 44.886 | -0.031 | -0.977 | False | False |
| I2 prevday-breakout SL0.5ATR TP1R · XAUUSD | 1023 | 45.357 | -0.039 | -1.553 | 831 | 47.653 | -0.036 | -1.301 | False | False |
| I4 ny-orb 30m TP2R · XAUUSD | 1899 | 39.021 | -0.043 | -1.620 | 1452 | 41.804 | -0.023 | -0.817 | False | False |
| I2 prevday-breakout SL0.25ATR TP2R · XAUUSD | 1023 | 35.386 | -0.065 | -1.634 | 831 | 35.620 | -0.085 | -1.960 | False | False |
| I4 ny-orb 60m TP2R · XAUUSD | 1563 | 40.691 | -0.049 | -2.113 | 1206 | 44.776 | -0.019 | -0.774 | False | False |
| I4 ny-orb 60m TP1R · XAUUSD | 1563 | 45.361 | -0.044 | -2.220 | 1206 | 47.098 | -0.027 | -1.275 | False | False |
| I1 ldn-breakout SL0.5range TP1R · XAUUSD | 1725 | 48.232 | -0.062 | -2.579 | 1355 | 44.649 | -0.128 | -4.755 | False | False |
| I1 ldn-breakout SL0.5range TP2R · XAUUSD | 1725 | 32.522 | -0.102 | -3.158 | 1355 | 31.144 | -0.127 | -3.506 | False | False |
| I4 ny-orb 30m TP1R · XAUUSD | 1899 | 46.340 | -0.071 | -3.408 | 1452 | 48.829 | -0.025 | -1.057 | False | False |
| I5 night-scalp BB2.5 SL0.3ATR · XAUUSD | 1173 | 53.879 | -0.073 | -4.521 | 968 | 58.161 | -0.057 | -3.249 | False | False |
| I5 night-scalp BB2.5 SL0.15ATR · XAUUSD | 1173 | 47.656 | -0.119 | -4.692 | 968 | 49.793 | -0.140 | -5.005 | False | False |
| I5 night-scalp BB2 SL0.3ATR · XAUUSD | 1917 | 57.955 | -0.058 | -4.865 | 1561 | 60.026 | -0.068 | -5.233 | False | False |
| I5 night-scalp BB2 SL0.15ATR · XAUUSD | 1917 | 51.956 | -0.099 | -5.318 | 1561 | 51.762 | -0.141 | -6.886 | False | False |
