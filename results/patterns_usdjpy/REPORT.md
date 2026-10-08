# Pattern search — USDJPY 2010–2026 (beyond the box breakout)

36 pre-declared setups in 4 families (see run_patterns.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage per stop fill. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) is shown only for survivors.

**Survivors: 2 of 36.** With 36 tries, about 1 setup would reach t ≥ 2 by luck.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|---|
| P1 fix-short to 06:00UTC gotobi | 561 | 54.724 | 0.144 | 3.163 | 432 | 52.546 | 0.112 | 2.206 | True |
| P1 fix-short to 06:00UTC all | 2030 | 50.542 | 0.056 | 2.533 | 1561 | 47.021 | -0.004 | -0.158 | False |
| P1 fix-short to 03:00UTC gotobi | 561 | 54.011 | 0.088 | 2.339 | 432 | 49.537 | 0.049 | 1.400 | True |
| P1 fix-short to 03:00UTC all | 2030 | 50.197 | 0.031 | 1.811 | 1561 | 46.573 | 0.004 | 0.194 | False |
| P1 fix-short to 02:00UTC gotobi | 561 | 52.763 | 0.034 | 1.432 | 432 | 56.481 | 0.067 | 2.262 | False |
| P1 fix-short to 06:00UTC other | 1469 | 48.945 | 0.022 | 0.886 | 1129 | 44.907 | -0.048 | -1.772 | False |
| P1 fix-short to 03:00UTC other | 1469 | 48.741 | 0.009 | 0.487 | 1129 | 45.438 | -0.014 | -0.608 | False |
| P1 fix-long 23:00UTC gotobi | 561 | 49.376 | 0.013 | 0.419 | 432 | 50.463 | -0.008 | -0.229 | False |
| P1 fix-long 23:30UTC gotobi | 561 | 50.980 | 0.007 | 0.240 | 432 | 51.620 | 0.010 | 0.291 | False |
| P1 fix-long 00:00UTC gotobi | 561 | 48.663 | -0.016 | -0.682 | 432 | 51.157 | -0.016 | -0.507 | False |
| P4 pullback k0.5 SL0.5ATR RR1 | 519 | 50.096 | -0.045 | -1.274 | 398 | 42.211 | -0.177 | -4.483 | False |
| P1 fix-short to 02:00UTC all | 2030 | 47.635 | -0.022 | -1.709 | 1561 | 50.545 | 0.009 | 0.564 | False |
| P4 pullback k0.25 SL0.5ATR RR1 | 857 | 48.658 | -0.051 | -1.937 | 679 | 44.624 | -0.118 | -3.907 | False |
| P4 pullback k0.5 SL1ATR RR1 | 519 | 47.592 | -0.049 | -2.327 | 398 | 42.211 | -0.113 | -4.306 | False |
| P4 pullback k0.5 SL1ATR RR2 | 519 | 47.399 | -0.051 | -2.435 | 398 | 41.960 | -0.121 | -4.628 | False |
| P4 pullback k0.5 SL0.5ATR RR2 | 519 | 45.665 | -0.095 | -2.529 | 398 | 39.950 | -0.179 | -4.113 | False |
| P1 fix-short to 02:00UTC other | 1469 | 45.677 | -0.043 | -2.883 | 1129 | 48.273 | -0.013 | -0.694 | False |
| P2 sweep 60m TP 2R | 1109 | 36.700 | -0.106 | -2.898 | 899 | 32.925 | -0.223 | -5.586 | False |
| P4 pullback k0.25 SL0.5ATR RR2 | 857 | 45.158 | -0.093 | -3.322 | 679 | 41.532 | -0.136 | -4.146 | False |
| P4 pullback k0.25 SL1ATR RR1 | 857 | 47.491 | -0.063 | -3.882 | 679 | 44.624 | -0.083 | -4.299 | False |
| P4 pullback k0.25 SL1ATR RR2 | 857 | 47.375 | -0.064 | -3.903 | 679 | 44.477 | -0.083 | -4.187 | False |
| P1 fix-long 23:30UTC all | 2030 | 46.749 | -0.058 | -3.968 | 1561 | 48.559 | -0.042 | -2.489 | False |
| P1 fix-long 23:00UTC all | 2030 | 45.862 | -0.063 | -4.067 | 1561 | 46.252 | -0.073 | -4.092 | False |
| P1 fix-long 00:00UTC all | 2030 | 46.010 | -0.052 | -4.132 | 1561 | 48.559 | -0.033 | -2.082 | False |
| P3 asian-fade 60m TP opposite | 893 | 32.139 | -0.205 | -4.258 | 750 | 34.133 | -0.149 | -2.639 | False |
| P1 fix-long 00:00UTC other | 1469 | 44.997 | -0.066 | -4.426 | 1129 | 47.564 | -0.039 | -2.151 | False |
| P3 asian-fade 60m TP mid | 893 | 46.920 | -0.165 | -4.581 | 750 | 50.000 | -0.104 | -2.628 | False |
| P2 sweep 60m TP 1R | 1109 | 46.078 | -0.132 | -4.687 | 899 | 43.382 | -0.203 | -6.538 | False |
| P2 sweep 60m TP mid | 1109 | 37.511 | -0.176 | -4.755 | 899 | 34.372 | -0.213 | -4.732 | False |
| P3 asian-fade 15m TP opposite | 1090 | 24.404 | -0.246 | -4.861 | 912 | 25.658 | -0.204 | -3.398 | False |
| P1 fix-long 23:30UTC other | 1469 | 45.133 | -0.082 | -5.015 | 1129 | 47.387 | -0.061 | -3.201 | False |
| P1 fix-long 23:00UTC other | 1469 | 44.520 | -0.092 | -5.178 | 1129 | 44.641 | -0.097 | -4.803 | False |
| P3 asian-fade 15m TP mid | 1090 | 36.881 | -0.215 | -5.537 | 912 | 40.899 | -0.134 | -3.058 | False |
| P2 sweep 15m TP 2R | 1221 | 32.924 | -0.211 | -5.641 | 991 | 32.795 | -0.209 | -4.962 | False |
| P2 sweep 15m TP mid | 1221 | 29.730 | -0.258 | -6.075 | 991 | 28.052 | -0.276 | -5.488 | False |
| P2 sweep 15m TP 1R | 1221 | 45.618 | -0.205 | -7.251 | 991 | 47.326 | -0.175 | -5.536 | False |

## Survivors: full numbers incl. holdout

|  | P1 fix-short to 03:00UTC gotobi | P1 fix-short to 06:00UTC gotobi |
|---|---|---|
| design trades | 561.000 | 561.000 |
| design win % | 54.011 | 54.724 |
| design avg R | 0.088 | 0.144 |
| design t | 2.339 | 3.163 |
| design max DD % (0.5%) | 4.342 | 5.846 |
| design return % (0.5%) | 27.321 | 49.129 |
| check trades | 432.000 | 432.000 |
| check win % | 49.537 | 52.546 |
| check avg R | 0.049 | 0.112 |
| check t | 1.400 | 2.206 |
| check max DD % (0.5%) | 4.109 | 7.549 |
| check return % (0.5%) | 10.861 | 26.495 |
| holdout trades | 199.000 | 199.000 |
| holdout win % | 48.744 | 47.236 |
| holdout avg R | 0.076 | 0.107 |
| holdout t | 1.312 | 1.458 |
| holdout max DD % (0.5%) | 3.295 | 6.583 |
| holdout return % (0.5%) | 7.664 | 10.996 |
