# Pattern search — GBPUSD 2010–2026 (beyond the box breakout)

36 pre-declared setups in 4 families (see run_patterns.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) is shown only for survivors.

**Survivors: 0 of 36.** With 36 tries, about 1 setup would reach t ≥ 2 by luck.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|---|
| P1 fix-short to 03:00UTC gotobi | 561 | 36.542 | -0.100 | -2.148 | 432 | 38.194 | -0.110 | -4.888 | False |
| P1 fix-short to 06:00UTC gotobi | 561 | 39.216 | -0.114 | -2.471 | 432 | 40.972 | -0.123 | -4.286 | False |
| P4 pullback k0.25 SL0.5ATR RR2 | 947 | 41.922 | -0.075 | -2.548 | 767 | 44.850 | -0.050 | -1.473 | False |
| P4 pullback k0.25 SL0.5ATR RR1 | 947 | 44.667 | -0.074 | -2.791 | 767 | 47.458 | -0.053 | -1.750 | False |
| P4 pullback k0.5 SL1ATR RR2 | 545 | 44.404 | -0.061 | -2.798 | 456 | 45.614 | -0.033 | -1.360 | False |
| P4 pullback k0.25 SL1ATR RR2 | 947 | 43.611 | -0.052 | -2.995 | 767 | 47.066 | -0.036 | -1.811 | False |
| P4 pullback k0.5 SL1ATR RR1 | 545 | 44.587 | -0.063 | -3.015 | 456 | 45.833 | -0.025 | -1.022 | False |
| P4 pullback k0.25 SL1ATR RR1 | 947 | 43.823 | -0.051 | -3.020 | 767 | 47.327 | -0.035 | -1.851 | False |
| P4 pullback k0.5 SL0.5ATR RR1 | 545 | 44.037 | -0.102 | -3.050 | 456 | 46.272 | -0.072 | -1.915 | False |
| P4 pullback k0.5 SL0.5ATR RR2 | 545 | 42.202 | -0.112 | -3.053 | 456 | 44.298 | -0.032 | -0.716 | False |
| P3 asian-fade 15m TP opposite | 1922 | 32.830 | -0.112 | -3.214 | 1396 | 31.089 | -0.165 | -4.129 | False |
| P2 sweep 60m TP mid | 1382 | 38.712 | -0.127 | -3.774 | 1070 | 37.196 | -0.149 | -3.765 | False |
| P2 sweep 60m TP 2R | 1382 | 34.370 | -0.131 | -4.018 | 1070 | 34.486 | -0.150 | -4.011 | False |
| P2 sweep 15m TP mid | 1530 | 27.647 | -0.167 | -4.029 | 1187 | 27.043 | -0.194 | -4.172 | False |
| P3 asian-fade 15m TP mid | 1921 | 50.651 | -0.104 | -4.401 | 1395 | 48.100 | -0.157 | -5.671 | False |
| P3 asian-fade 60m TP opposite | 1626 | 42.558 | -0.146 | -4.932 | 1149 | 44.038 | -0.118 | -3.241 | False |
| P2 sweep 15m TP 2R | 1530 | 31.438 | -0.171 | -5.036 | 1187 | 32.350 | -0.146 | -3.735 | False |
| P2 sweep 60m TP 1R | 1382 | 43.849 | -0.148 | -5.890 | 1070 | 46.075 | -0.123 | -4.219 | False |
| P1 fix-long 23:00UTC gotobi | 561 | 34.581 | -0.114 | -6.033 | 432 | 39.352 | -0.082 | -4.156 | False |
| P3 asian-fade 60m TP mid | 1629 | 58.809 | -0.127 | -6.361 | 1146 | 58.202 | -0.107 | -4.285 | False |
| P1 fix-long 23:30UTC gotobi | 561 | 35.829 | -0.110 | -6.364 | 432 | 42.361 | -0.067 | -3.727 | False |
| P2 sweep 15m TP 1R | 1530 | 44.379 | -0.180 | -7.149 | 1187 | 46.167 | -0.148 | -5.150 | False |
| P1 fix-long 00:00UTC gotobi | 561 | 36.185 | -0.113 | -7.157 | 432 | 40.741 | -0.072 | -4.391 | False |
| P1 fix-short to 02:00UTC gotobi | 561 | 34.225 | -0.124 | -7.303 | 432 | 38.889 | -0.110 | -6.025 | False |
| P1 fix-short to 06:00UTC all | 2031 | 38.552 | -0.142 | -8.223 | 1561 | 42.281 | -0.108 | -6.846 | False |
| P1 fix-short to 03:00UTC all | 2031 | 35.746 | -0.130 | -8.411 | 1561 | 38.693 | -0.107 | -8.728 | False |
| P1 fix-short to 06:00UTC other | 1470 | 38.299 | -0.153 | -9.464 | 1129 | 42.781 | -0.102 | -5.424 | False |
| P1 fix-long 23:30UTC other | 1470 | 37.891 | -0.123 | -11.875 | 1129 | 37.644 | -0.110 | -9.308 | False |
| P1 fix-short to 03:00UTC other | 1470 | 35.442 | -0.142 | -11.955 | 1129 | 38.884 | -0.105 | -7.246 | False |
| P1 fix-short to 02:00UTC other | 1470 | 36.122 | -0.116 | -12.205 | 1129 | 36.935 | -0.089 | -7.822 | False |
| P1 fix-long 23:00UTC other | 1470 | 36.122 | -0.142 | -12.593 | 1129 | 37.821 | -0.116 | -8.645 | False |
| P1 fix-long 23:30UTC all | 2031 | 37.322 | -0.119 | -13.435 | 1561 | 38.949 | -0.098 | -9.910 | False |
| P1 fix-long 00:00UTC other | 1470 | 34.490 | -0.125 | -13.550 | 1129 | 35.075 | -0.108 | -10.124 | False |
| P1 fix-long 23:00UTC all | 2031 | 35.697 | -0.135 | -13.859 | 1561 | 38.245 | -0.106 | -9.569 | False |
| P1 fix-short to 02:00UTC all | 2031 | 35.598 | -0.118 | -14.202 | 1561 | 37.476 | -0.095 | -9.819 | False |
| P1 fix-long 00:00UTC all | 2031 | 34.958 | -0.122 | -15.264 | 1561 | 36.643 | -0.098 | -10.941 | False |
