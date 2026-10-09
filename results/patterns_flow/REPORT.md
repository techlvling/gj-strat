# Flow / session pattern search — 5 pairs, 2010–2026

12 pre-declared setups per pair, 60 tests (see run_patterns_flow.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.

**Survivors: 2 of 60.** With 60 tries, 1–2 would pass by luck.

| Setup · pair | design trades | design win % | design avg R | design t | check trades | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|
| F2 ldn-fix fade exit 18:00LDN SL0.5ATR · GBPUSD | 601 | 56.739 | 0.042 | 2.536 | 490 | -0.034 | -1.624 | False |
| F1 month-end follow exit 16:05LDN · GBPJPY | 93 | 60.215 | 0.183 | 2.377 | 72 | 0.212 | 2.524 | True |
| F1 month-end follow exit 17:00LDN · GBPJPY | 93 | 60.215 | 0.180 | 2.230 | 72 | 0.182 | 2.175 | True |
| F2 ldn-fix fade exit 18:00LDN SL0.5ATR · EURUSD | 550 | 58.909 | 0.033 | 1.912 | 489 | -0.042 | -1.935 | False |
| F1 month-end follow exit 16:05LDN · GBPUSD | 93 | 52.688 | 0.121 | 1.522 | 72 | -0.056 | -0.600 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.25ATR · GBPUSD | 601 | 54.243 | 0.045 | 1.441 | 490 | -0.059 | -1.552 | False |
| F1 month-end follow exit 17:00LDN · GBPUSD | 93 | 48.387 | 0.112 | 1.333 | 72 | -0.087 | -0.962 | False |
| F1 month-end follow exit 16:05LDN · USDJPY | 93 | 61.290 | 0.087 | 1.322 | 72 | -0.058 | -0.753 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.25ATR · EURUSD | 550 | 56.909 | 0.042 | 1.314 | 489 | -0.096 | -2.461 | False |
| F1 month-end follow exit 16:05LDN · EURJPY | 93 | 55.914 | 0.073 | 1.180 | 72 | 0.240 | 3.259 | False |
| F1 month-end follow exit 17:00LDN · EURJPY | 93 | 58.065 | 0.078 | 1.163 | 72 | 0.207 | 2.746 | False |
| F1 month-end follow exit 16:05LDN · EURUSD | 93 | 50.538 | 0.068 | 0.980 | 72 | -0.135 | -1.559 | False |
| F1 month-end follow exit 17:00LDN · USDJPY | 93 | 56.989 | 0.066 | 0.969 | 72 | -0.063 | -0.703 | False |
| F1 month-end follow exit 17:00LDN · EURUSD | 93 | 49.462 | 0.041 | 0.546 | 72 | -0.084 | -0.871 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.5ATR · GBPJPY | 500 | 53.600 | 0.009 | 0.462 | 437 | -0.029 | -1.405 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.5ATR · EURJPY | 490 | 52.857 | 0.007 | 0.389 | 425 | -0.030 | -1.425 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.25ATR · GBPJPY | 500 | 52.200 | 0.013 | 0.362 | 437 | -0.042 | -1.144 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.5ATR · GBPUSD | 601 | 52.246 | 0.001 | 0.080 | 490 | -0.020 | -1.170 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.5ATR · USDJPY | 493 | 53.955 | 0.001 | 0.041 | 402 | -0.015 | -0.874 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.25ATR · EURJPY | 490 | 51.633 | 0.001 | 0.025 | 425 | -0.051 | -1.320 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.5ATR · EURUSD | 550 | 53.818 | -0.002 | -0.160 | 489 | -0.034 | -2.131 | False |
| F3 ny-open mom exit 16:00NY SL0.5ATR · EURUSD | 2020 | 48.663 | -0.004 | -0.239 | 1546 | -0.036 | -1.962 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.25ATR · GBPUSD | 601 | 51.581 | -0.007 | -0.268 | 490 | -0.045 | -1.424 | False |
| F3 ny-open mom exit 15:00NY SL0.5ATR · EURUSD | 2020 | 48.168 | -0.004 | -0.268 | 1546 | -0.029 | -1.656 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.25ATR · EURUSD | 550 | 53.273 | -0.007 | -0.269 | 489 | -0.087 | -2.923 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.5ATR · USDJPY | 493 | 52.535 | -0.007 | -0.370 | 402 | -0.049 | -2.275 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.25ATR · USDJPY | 493 | 53.144 | -0.012 | -0.419 | 402 | -0.025 | -0.777 | False |
| F3 ny-open mom exit 16:00NY SL0.5ATR · EURJPY | 2014 | 48.908 | -0.010 | -0.725 | 1548 | -0.028 | -1.752 | False |
| F2 ldn-fix fade exit 18:00LDN SL0.25ATR · USDJPY | 493 | 50.913 | -0.030 | -0.859 | 402 | -0.090 | -2.279 | False |
| F3 ny-open mom exit 15:00NY SL0.5ATR · EURJPY | 2014 | 46.971 | -0.012 | -0.969 | 1548 | -0.019 | -1.233 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.5ATR · GBPJPY | 500 | 48.600 | -0.015 | -1.015 | 437 | -0.022 | -1.269 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.25ATR · EURJPY | 490 | 53.265 | -0.028 | -1.052 | 425 | -0.020 | -0.629 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.5ATR · EURJPY | 490 | 53.469 | -0.015 | -1.065 | 425 | -0.009 | -0.528 | False |
| F2 ldn-fix fade exit 17:00LDN SL0.25ATR · GBPJPY | 500 | 48.200 | -0.031 | -1.100 | 437 | -0.025 | -0.801 | False |
| F1 month-end fade exit 17:00LDN · EURUSD | 93 | 43.011 | -0.091 | -1.266 | 72 | 0.021 | 0.212 | False |
| F1 month-end fade exit 17:00LDN · GBPUSD | 93 | 49.462 | -0.109 | -1.432 | 72 | 0.031 | 0.384 | False |
| F3 ny-open mom exit 15:00NY SL0.25ATR · EURUSD | 2020 | 42.525 | -0.037 | -1.452 | 1546 | -0.035 | -1.135 | False |
| F1 month-end fade exit 16:05LDN · GBPUSD | 93 | 46.237 | -0.108 | -1.481 | 72 | 0.014 | 0.186 | False |
| F3 ny-open mom exit 16:00NY SL0.25ATR · EURUSD | 2020 | 42.475 | -0.039 | -1.498 | 1546 | -0.043 | -1.381 | False |
| F1 month-end fade exit 17:00LDN · EURJPY | 93 | 37.634 | -0.125 | -1.809 | 72 | -0.311 | -3.448 | False |
| F1 month-end fade exit 16:05LDN · EURUSD | 93 | 44.086 | -0.116 | -1.819 | 72 | 0.069 | 0.841 | False |
| F1 month-end fade exit 16:05LDN · EURJPY | 93 | 37.634 | -0.118 | -1.895 | 72 | -0.316 | -3.912 | False |
| F3 ny-open mom exit 16:00NY SL0.25ATR · EURJPY | 2014 | 44.290 | -0.053 | -2.203 | 1548 | -0.045 | -1.629 | False |
| F1 month-end fade exit 16:05LDN · USDJPY | 93 | 37.634 | -0.146 | -2.390 | 72 | 0.004 | 0.043 | False |
| F1 month-end fade exit 17:00LDN · USDJPY | 93 | 37.634 | -0.160 | -2.476 | 72 | -0.007 | -0.076 | False |
| F3 ny-open mom exit 15:00NY SL0.25ATR · EURJPY | 2014 | 42.651 | -0.061 | -2.699 | 1548 | -0.029 | -1.048 | False |
| F1 month-end fade exit 16:05LDN · GBPJPY | 93 | 34.409 | -0.198 | -2.984 | 72 | -0.269 | -3.324 | False |
| F3 ny-open mom exit 15:00NY SL0.5ATR · GBPUSD | 2012 | 45.626 | -0.042 | -3.065 | 1553 | -0.038 | -2.331 | False |
| F1 month-end fade exit 17:00LDN · GBPJPY | 93 | 33.333 | -0.220 | -3.084 | 72 | -0.261 | -3.095 | False |
| F3 ny-open mom exit 16:00NY SL0.5ATR · GBPUSD | 2012 | 45.328 | -0.046 | -3.221 | 1553 | -0.038 | -2.278 | False |
| F3 ny-open mom exit 15:00NY SL0.25ATR · GBPUSD | 2012 | 41.004 | -0.099 | -4.030 | 1553 | -0.089 | -3.147 | False |
| F3 ny-open mom exit 16:00NY SL0.5ATR · GBPJPY | 2014 | 45.283 | -0.055 | -4.187 | 1552 | -0.042 | -2.650 | False |
| F3 ny-open mom exit 16:00NY SL0.5ATR · USDJPY | 2011 | 45.102 | -0.059 | -4.204 | 1549 | -0.043 | -2.500 | False |
| F3 ny-open mom exit 15:00NY SL0.5ATR · USDJPY | 2011 | 44.704 | -0.058 | -4.281 | 1549 | -0.024 | -1.423 | False |
| F3 ny-open mom exit 16:00NY SL0.25ATR · GBPUSD | 2012 | 39.960 | -0.108 | -4.323 | 1553 | -0.093 | -3.219 | False |
| F3 ny-open mom exit 15:00NY SL0.5ATR · GBPJPY | 2014 | 44.340 | -0.055 | -4.340 | 1552 | -0.030 | -1.956 | False |
| F3 ny-open mom exit 16:00NY SL0.25ATR · USDJPY | 2011 | 40.129 | -0.114 | -4.750 | 1549 | -0.083 | -2.908 | False |
| F3 ny-open mom exit 15:00NY SL0.25ATR · USDJPY | 2011 | 39.334 | -0.112 | -4.834 | 1549 | -0.057 | -1.976 | False |
| F3 ny-open mom exit 16:00NY SL0.25ATR · GBPJPY | 2014 | 40.318 | -0.119 | -5.280 | 1552 | -0.089 | -3.171 | False |
| F3 ny-open mom exit 15:00NY SL0.25ATR · GBPJPY | 2014 | 39.921 | -0.120 | -5.500 | 1552 | -0.074 | -2.702 | False |

## Survivors incl. holdout

|  | F1 month-end follow exit 16:05LDN · GBPJPY | F1 month-end follow exit 17:00LDN · GBPJPY |
|---|---|---|
| design trades | 93.000 | 93.000 |
| design win % | 60.215 | 60.215 |
| design avg R | 0.183 | 0.180 |
| design t | 2.377 | 2.230 |
| design max DD % (0.5%) | 0.958 | 1.318 |
| design return % (0.5%) | 8.009 | 7.871 |
| check trades | 72.000 | 72.000 |
| check win % | 63.889 | 61.111 |
| check avg R | 0.212 | 0.182 |
| check t | 2.524 | 2.175 |
| check max DD % (0.5%) | 1.486 | 1.569 |
| check return % (0.5%) | 7.387 | 6.536 |
| holdout trades | 33.000 | 33.000 |
| holdout win % | 42.424 | 39.394 |
| holdout avg R | -0.060 | -0.074 |
| holdout t | -0.523 | -0.650 |
| holdout max DD % (0.5%) | 2.575 | 2.744 |
| holdout return % (0.5%) | -0.978 | -1.189 |
