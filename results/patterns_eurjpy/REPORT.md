# Pattern search — EURJPY 2010–2026 (beyond the box breakout)

36 pre-declared setups in 4 families (see run_patterns.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) is shown only for survivors.

**Survivors: 0 of 36.** With 36 tries, about 1 setup would reach t ≥ 2 by luck.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|---|
| P1 fix-short to 06:00UTC gotobi | 561 | 50.267 | 0.088 | 1.775 | 432 | 51.389 | 0.068 | 1.366 | False |
| P1 fix-short to 03:00UTC gotobi | 561 | 48.841 | 0.028 | 0.636 | 432 | 48.843 | 0.000 | 0.003 | False |
| P1 fix-short to 02:00UTC gotobi | 561 | 46.702 | -0.013 | -0.576 | 432 | 54.167 | 0.028 | 1.106 | False |
| P1 fix-long 23:30UTC gotobi | 561 | 47.059 | -0.024 | -0.856 | 432 | 55.556 | 0.030 | 0.981 | False |
| P1 fix-short to 06:00UTC all | 2029 | 45.983 | -0.022 | -1.005 | 1561 | 44.331 | -0.047 | -2.051 | False |
| P1 fix-long 23:00UTC gotobi | 561 | 46.524 | -0.048 | -1.701 | 432 | 53.704 | 0.029 | 0.903 | False |
| P1 fix-long 00:00UTC gotobi | 561 | 48.841 | -0.039 | -1.805 | 432 | 55.556 | 0.002 | 0.078 | False |
| P1 fix-short to 03:00UTC all | 2029 | 45.934 | -0.036 | -2.117 | 1561 | 45.740 | -0.050 | -2.935 | False |
| P4 pullback k0.5 SL1ATR RR1 | 528 | 46.970 | -0.045 | -2.164 | 442 | 45.023 | -0.075 | -3.181 | False |
| P4 pullback k0.5 SL1ATR RR2 | 528 | 46.780 | -0.050 | -2.397 | 442 | 44.570 | -0.085 | -3.618 | False |
| P4 pullback k0.25 SL1ATR RR1 | 873 | 46.735 | -0.041 | -2.506 | 719 | 43.394 | -0.072 | -3.891 | False |
| P4 pullback k0.25 SL1ATR RR2 | 873 | 46.506 | -0.044 | -2.646 | 719 | 43.115 | -0.081 | -4.354 | False |
| P3 asian-fade 15m TP opposite | 1427 | 27.260 | -0.124 | -2.710 | 1149 | 26.806 | -0.164 | -3.191 | False |
| P4 pullback k0.25 SL0.5ATR RR1 | 873 | 45.934 | -0.075 | -2.780 | 719 | 43.950 | -0.102 | -3.455 | False |
| P1 fix-short to 06:00UTC other | 1468 | 44.346 | -0.063 | -2.787 | 1129 | 41.630 | -0.091 | -3.616 | False |
| P3 asian-fade 60m TP opposite | 1166 | 37.307 | -0.116 | -2.826 | 971 | 35.118 | -0.185 | -4.102 | False |
| P4 pullback k0.5 SL0.5ATR RR1 | 528 | 45.644 | -0.098 | -2.907 | 442 | 45.928 | -0.094 | -2.485 | False |
| P4 pullback k0.25 SL0.5ATR RR2 | 873 | 43.528 | -0.090 | -3.087 | 719 | 40.751 | -0.118 | -3.690 | False |
| P4 pullback k0.5 SL0.5ATR RR2 | 528 | 43.371 | -0.119 | -3.295 | 442 | 42.986 | -0.115 | -2.852 | False |
| P2 sweep 60m TP 2R | 1206 | 35.323 | -0.126 | -3.598 | 1008 | 32.143 | -0.214 | -5.762 | False |
| P2 sweep 60m TP 1R | 1206 | 46.517 | -0.101 | -3.724 | 1008 | 44.246 | -0.147 | -4.964 | False |
| P1 fix-short to 03:00UTC other | 1468 | 44.823 | -0.061 | -3.735 | 1129 | 44.553 | -0.069 | -3.426 | False |
| P3 asian-fade 60m TP mid | 1166 | 51.458 | -0.122 | -4.157 | 971 | 47.683 | -0.176 | -5.556 | False |
| P3 asian-fade 15m TP mid | 1427 | 40.294 | -0.140 | -4.258 | 1149 | 41.950 | -0.174 | -4.868 | False |
| P1 fix-short to 02:00UTC all | 2029 | 45.441 | -0.050 | -4.356 | 1561 | 46.765 | -0.026 | -1.876 | False |
| P1 fix-short to 02:00UTC other | 1468 | 44.959 | -0.064 | -4.814 | 1129 | 43.933 | -0.047 | -2.841 | False |
| P2 sweep 60m TP mid | 1206 | 36.401 | -0.174 | -4.909 | 1008 | 33.234 | -0.246 | -6.355 | False |
| P2 sweep 15m TP mid | 1355 | 26.716 | -0.218 | -5.155 | 1106 | 26.040 | -0.246 | -5.121 | False |
| P2 sweep 15m TP 2R | 1355 | 31.365 | -0.190 | -5.310 | 1106 | 30.922 | -0.214 | -5.372 | False |
| P2 sweep 15m TP 1R | 1355 | 45.683 | -0.156 | -5.815 | 1106 | 46.835 | -0.153 | -5.114 | False |
| P1 fix-long 00:00UTC other | 1468 | 42.779 | -0.080 | -5.941 | 1129 | 44.641 | -0.084 | -4.968 | False |
| P1 fix-long 23:30UTC all | 2029 | 44.899 | -0.077 | -5.952 | 1561 | 48.046 | -0.065 | -4.196 | False |
| P1 fix-long 00:00UTC all | 2029 | 44.455 | -0.068 | -6.011 | 1561 | 47.662 | -0.060 | -4.167 | False |
| P1 fix-long 23:30UTC other | 1468 | 44.074 | -0.097 | -6.764 | 1129 | 45.173 | -0.101 | -5.678 | False |
| P1 fix-long 23:00UTC all | 2029 | 44.012 | -0.096 | -6.955 | 1561 | 45.932 | -0.086 | -5.288 | False |
| P1 fix-long 23:00UTC other | 1468 | 43.052 | -0.114 | -7.293 | 1129 | 42.958 | -0.129 | -6.977 | False |
