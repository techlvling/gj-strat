# Pattern search — EURUSD 2010–2026 (beyond the box breakout)

36 pre-declared setups in 4 families (see run_patterns.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) is shown only for survivors.

**Survivors: 0 of 36.** With 36 tries, about 1 setup would reach t ≥ 2 by luck.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|---|
| P4 pullback k0.25 SL0.5ATR RR2 | 979 | 47.293 | -0.014 | -0.449 | 783 | 43.295 | -0.095 | -2.853 | False |
| P4 pullback k0.25 SL1ATR RR1 | 979 | 49.949 | -0.008 | -0.466 | 783 | 46.488 | -0.055 | -2.883 | False |
| P4 pullback k0.5 SL1ATR RR2 | 564 | 47.695 | -0.011 | -0.501 | 460 | 43.696 | -0.063 | -2.673 | False |
| P3 asian-fade 60m TP opposite | 1400 | 43.929 | -0.019 | -0.515 | 1143 | 41.645 | -0.138 | -3.616 | False |
| P4 pullback k0.25 SL1ATR RR2 | 979 | 49.438 | -0.010 | -0.584 | 783 | 45.977 | -0.062 | -3.216 | False |
| P4 pullback k0.25 SL0.5ATR RR1 | 979 | 50.153 | -0.020 | -0.777 | 783 | 47.765 | -0.066 | -2.251 | False |
| P4 pullback k0.5 SL1ATR RR1 | 564 | 48.050 | -0.016 | -0.783 | 460 | 44.348 | -0.059 | -2.545 | False |
| P3 asian-fade 15m TP opposite | 1682 | 33.413 | -0.036 | -0.878 | 1388 | 30.908 | -0.171 | -4.053 | False |
| P4 pullback k0.5 SL0.5ATR RR1 | 564 | 48.582 | -0.037 | -1.121 | 460 | 46.522 | -0.073 | -1.980 | False |
| P4 pullback k0.5 SL0.5ATR RR2 | 564 | 45.390 | -0.043 | -1.150 | 460 | 42.174 | -0.106 | -2.602 | False |
| P2 sweep 60m TP mid | 1352 | 40.607 | -0.071 | -1.960 | 1079 | 37.720 | -0.142 | -3.594 | False |
| P2 sweep 60m TP 2R | 1352 | 37.130 | -0.073 | -2.165 | 1079 | 36.237 | -0.097 | -2.545 | False |
| P1 fix-short to 06:00UTC gotobi | 561 | 40.820 | -0.092 | -2.557 | 432 | 43.287 | -0.110 | -3.366 | False |
| P2 sweep 15m TP mid | 1471 | 29.980 | -0.120 | -2.739 | 1194 | 28.392 | -0.200 | -4.253 | False |
| P2 sweep 60m TP 1R | 1352 | 48.447 | -0.072 | -2.821 | 1079 | 47.359 | -0.111 | -3.849 | False |
| P1 fix-short to 03:00UTC gotobi | 561 | 36.542 | -0.107 | -3.590 | 432 | 42.361 | -0.113 | -4.563 | False |
| P3 asian-fade 60m TP mid | 1400 | 58.643 | -0.088 | -3.739 | 1140 | 57.018 | -0.108 | -4.183 | False |
| P2 sweep 15m TP 2R | 1471 | 33.447 | -0.134 | -3.822 | 1194 | 34.171 | -0.128 | -3.231 | False |
| P3 asian-fade 15m TP mid | 1681 | 48.424 | -0.108 | -4.078 | 1385 | 48.881 | -0.138 | -4.808 | False |
| P2 sweep 15m TP 1R | 1471 | 47.859 | -0.120 | -4.632 | 1194 | 47.906 | -0.149 | -5.155 | False |
| P1 fix-long 23:30UTC gotobi | 561 | 36.542 | -0.103 | -5.735 | 432 | 46.759 | -0.043 | -2.250 | False |
| P1 fix-short to 02:00UTC gotobi | 561 | 36.542 | -0.100 | -5.911 | 432 | 39.815 | -0.094 | -4.987 | False |
| P1 fix-long 23:00UTC gotobi | 561 | 37.433 | -0.119 | -5.994 | 432 | 47.222 | -0.037 | -1.774 | False |
| P1 fix-long 00:00UTC gotobi | 561 | 38.146 | -0.099 | -6.369 | 432 | 46.065 | -0.045 | -2.503 | False |
| P1 fix-short to 02:00UTC other | 1470 | 39.660 | -0.087 | -8.439 | 1130 | 37.699 | -0.100 | -8.626 | False |
| P1 fix-long 23:30UTC other | 1470 | 39.660 | -0.096 | -8.465 | 1130 | 37.965 | -0.104 | -8.182 | False |
| P1 fix-short to 06:00UTC all | 2031 | 41.211 | -0.133 | -8.537 | 1562 | 41.677 | -0.115 | -6.898 | False |
| P1 fix-short to 06:00UTC other | 1470 | 41.361 | -0.149 | -8.951 | 1130 | 41.062 | -0.117 | -6.034 | False |
| P1 fix-long 23:00UTC other | 1470 | 38.776 | -0.113 | -9.101 | 1130 | 40.000 | -0.094 | -6.844 | False |
| P1 fix-long 00:00UTC other | 1470 | 38.776 | -0.096 | -9.473 | 1130 | 36.018 | -0.111 | -9.426 | False |
| P1 fix-short to 03:00UTC all | 2031 | 37.666 | -0.126 | -10.109 | 1562 | 40.653 | -0.116 | -8.965 | False |
| P1 fix-long 23:30UTC all | 2031 | 38.799 | -0.098 | -10.213 | 1562 | 40.397 | -0.087 | -8.205 | False |
| P1 fix-short to 02:00UTC all | 2031 | 38.799 | -0.090 | -10.291 | 1562 | 38.284 | -0.098 | -9.961 | False |
| P1 fix-short to 03:00UTC other | 1470 | 38.095 | -0.133 | -10.316 | 1130 | 40.000 | -0.118 | -7.716 | False |
| P1 fix-long 23:00UTC all | 2031 | 38.405 | -0.115 | -10.893 | 1562 | 41.997 | -0.078 | -6.807 | False |
| P1 fix-long 00:00UTC all | 2031 | 38.602 | -0.097 | -11.394 | 1562 | 38.796 | -0.093 | -9.371 | False |
