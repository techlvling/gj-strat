# Month-end hedge rebalancing on USDJPY (Nasdaq vs JPN225 signal), 2011–2026

Rules, variants and selection in run_monthend_hedge.py (fixed before running).

**Design-best: Tokyo morning last day, gap>=2%** — design t >= 2: yes, check avg R > 0: NO, holdout avg R > 0: NO → **FAIL**

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | holdout trades | holdout win % | holdout avg R | holdout t | all avg R | all t | quarter-end trades | quarter-end avg R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tokyo morning last day, gap>=2% | 46.000 | 80.435 | 0.541 | 3.996 | 50.000 | 44.000 | -0.240 | -2.046 | 19.000 | 36.842 | -0.123 | -0.513 | 0.092 | 1.018 | 38.000 | 0.051 |
| Tokyo morning last day, all | 75.000 | 69.333 | 0.494 | 3.159 | 72.000 | 45.833 | -0.081 | -0.678 | 33.000 | 33.333 | -0.280 | -1.766 | 0.122 | 1.375 | 60.000 | 0.039 |
| 14:00 LDN last day, gap>=2% | 53.000 | 69.811 | 0.213 | 2.551 | 51.000 | 45.098 | -0.098 | -1.014 | 18.000 | 16.667 | -0.187 | -1.061 | 0.024 | 0.391 | 40.000 | 0.090 |
| 14:00 LDN last day, all | 75.000 | 61.333 | 0.118 | 1.673 | 72.000 | 50.000 | -0.069 | -0.862 | 33.000 | 21.212 | -0.171 | -1.681 | -0.010 | -0.205 | 60.000 | -0.024 |
| 16:05 LDN day before, all | 75.000 | 56.000 | 0.218 | 1.329 | 72.000 | 40.278 | -0.105 | -0.865 | 33.000 | 27.273 | -0.299 | -1.814 | -0.006 | -0.065 | 60.000 | -0.091 |
| 16:05 LDN day before, gap>=2% | 48.000 | 58.333 | 0.164 | 1.128 | 50.000 | 36.000 | -0.188 | -1.369 | 19.000 | 31.579 | -0.166 | -0.640 | -0.040 | -0.424 | 38.000 | -0.150 |
