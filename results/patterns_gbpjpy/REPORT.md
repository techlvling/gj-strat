# Pattern search — GBPJPY 2010–2026 (beyond the box breakout)

36 pre-declared setups in 4 families (see run_patterns.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) is shown only for survivors.

**Survivors: 0 of 36.** With 36 tries, about 1 setup would reach t ≥ 2 by luck.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|---|
| P1 fix-short to 06:00UTC gotobi | 561 | 50.446 | 0.083 | 1.570 | 432 | 47.685 | 0.016 | 0.328 | False |
| P1 fix-short to 03:00UTC gotobi | 561 | 47.059 | 0.041 | 0.815 | 432 | 47.222 | -0.023 | -0.786 | False |
| P1 fix-long 23:30UTC gotobi | 561 | 48.485 | -0.023 | -0.877 | 432 | 51.620 | -0.011 | -0.431 | False |
| P1 fix-short to 06:00UTC all | 2030 | 46.010 | -0.023 | -1.079 | 1561 | 43.370 | -0.057 | -2.605 | False |
| P1 fix-short to 02:00UTC gotobi | 561 | 47.237 | -0.025 | -1.111 | 432 | 51.620 | -0.012 | -0.499 | False |
| P1 fix-long 23:00UTC gotobi | 561 | 45.633 | -0.039 | -1.455 | 432 | 47.454 | -0.046 | -1.590 | False |
| P1 fix-short to 03:00UTC all | 2030 | 46.256 | -0.034 | -1.863 | 1561 | 43.882 | -0.052 | -3.245 | False |
| P1 fix-long 00:00UTC gotobi | 561 | 46.168 | -0.044 | -2.100 | 432 | 50.231 | -0.041 | -1.755 | False |
| P1 fix-short to 06:00UTC other | 1469 | 44.316 | -0.064 | -2.944 | 1129 | 41.718 | -0.085 | -3.555 | False |
| P3 asian-fade 15m TP opposite | 1580 | 28.228 | -0.137 | -3.324 | 1210 | 28.430 | -0.115 | -2.348 | False |
| P4 pullback k0.25 SL0.5ATR RR1 | 882 | 45.011 | -0.096 | -3.608 | 702 | 47.151 | -0.085 | -2.799 | False |
| P2 sweep 60m TP mid | 1302 | 37.020 | -0.134 | -3.758 | 965 | 37.409 | -0.113 | -2.666 | False |
| P1 fix-short to 03:00UTC other | 1469 | 45.950 | -0.062 | -3.896 | 1129 | 42.604 | -0.063 | -3.289 | False |
| P4 pullback k0.25 SL0.5ATR RR2 | 882 | 42.404 | -0.112 | -3.903 | 702 | 44.017 | -0.129 | -4.056 | False |
| P4 pullback k0.25 SL1ATR RR1 | 882 | 44.444 | -0.064 | -3.927 | 702 | 46.154 | -0.084 | -4.424 | False |
| P4 pullback k0.25 SL1ATR RR2 | 882 | 44.444 | -0.065 | -3.984 | 702 | 45.869 | -0.092 | -4.927 | False |
| P3 asian-fade 60m TP opposite | 1319 | 38.741 | -0.144 | -4.057 | 1000 | 39.900 | -0.110 | -2.599 | False |
| P4 pullback k0.5 SL1ATR RR1 | 520 | 43.077 | -0.085 | -4.125 | 448 | 47.991 | -0.052 | -2.072 | False |
| P4 pullback k0.5 SL1ATR RR2 | 520 | 43.077 | -0.085 | -4.135 | 448 | 47.545 | -0.066 | -2.737 | False |
| P2 sweep 60m TP 2R | 1302 | 34.562 | -0.140 | -4.198 | 965 | 35.337 | -0.096 | -2.430 | False |
| P2 sweep 15m TP mid | 1410 | 27.234 | -0.182 | -4.285 | 1068 | 28.558 | -0.135 | -2.645 | False |
| P4 pullback k0.5 SL0.5ATR RR1 | 520 | 41.538 | -0.141 | -4.301 | 448 | 45.536 | -0.102 | -2.651 | False |
| P4 pullback k0.5 SL0.5ATR RR2 | 520 | 40.000 | -0.160 | -4.615 | 448 | 44.866 | -0.087 | -2.043 | False |
| P3 asian-fade 15m TP mid | 1579 | 43.319 | -0.142 | -4.921 | 1210 | 43.636 | -0.162 | -4.858 | False |
| P3 asian-fade 60m TP mid | 1318 | 53.111 | -0.128 | -4.978 | 1000 | 55.000 | -0.138 | -4.735 | False |
| P2 sweep 60m TP 1R | 1302 | 44.624 | -0.132 | -5.087 | 965 | 45.596 | -0.111 | -3.679 | False |
| P2 sweep 15m TP 2R | 1410 | 31.206 | -0.178 | -5.101 | 1068 | 32.678 | -0.143 | -3.506 | False |
| P1 fix-short to 02:00UTC all | 2030 | 44.384 | -0.064 | -5.643 | 1561 | 44.971 | -0.037 | -2.751 | False |
| P1 fix-short to 02:00UTC other | 1469 | 43.295 | -0.078 | -6.006 | 1129 | 42.427 | -0.047 | -2.870 | False |
| P1 fix-long 23:30UTC all | 2030 | 43.300 | -0.085 | -6.763 | 1561 | 45.291 | -0.077 | -5.790 | False |
| P2 sweep 15m TP 1R | 1410 | 43.688 | -0.184 | -7.032 | 1068 | 45.412 | -0.158 | -5.231 | False |
| P1 fix-long 00:00UTC other | 1469 | 40.504 | -0.093 | -7.274 | 1129 | 42.958 | -0.086 | -6.004 | False |
| P1 fix-long 00:00UTC all | 2030 | 42.069 | -0.080 | -7.284 | 1561 | 44.971 | -0.074 | -6.025 | False |
| P1 fix-long 23:00UTC all | 2030 | 42.512 | -0.102 | -7.567 | 1561 | 43.434 | -0.108 | -7.514 | False |
| P1 fix-long 23:30UTC other | 1469 | 41.321 | -0.109 | -7.687 | 1129 | 42.870 | -0.102 | -6.652 | False |
| P1 fix-long 23:00UTC other | 1469 | 41.321 | -0.126 | -8.135 | 1129 | 41.895 | -0.132 | -8.010 | False |
