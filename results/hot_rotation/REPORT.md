# Short-term alpha: recent winners next month (walk-forward)

Rules in run_hot_rotation.py (fixed before running). 488 trade streams.

## Variants (first row = trade every stream)

|  | trades | trades / month | 2011-07..2017 avg R | 2011-07..2017 t | 2018-23 avg R | 2018-23 t | 2024-26 avg R | 2024-26 t | accepted |
|---|---|---|---|---|---|---|---|---|---|
| ('all', 'all') | 1138993 | 6190.179 | -0.158 | -68.050 | -0.159 | -66.097 | -0.184 | -51.136 | None |
| (1, 3) | 6507 | 35.364 | -0.043 | -2.090 | -0.102 | -4.914 | -0.078 | -2.060 | False |
| (1, 5) | 11234 | 61.054 | -0.046 | -2.795 | -0.099 | -5.853 | -0.085 | -3.000 | False |
| (1, 10) | 24167 | 131.342 | -0.069 | -5.256 | -0.078 | -5.608 | -0.048 | -2.039 | False |
| (3, 3) | 5181 | 28.158 | -0.003 | -0.109 | -0.142 | -4.650 | -0.051 | -1.102 | False |
| (3, 5) | 9154 | 49.750 | -0.005 | -0.203 | -0.084 | -3.260 | -0.064 | -1.925 | False |
| (3, 10) | 20100 | 109.239 | -0.026 | -1.533 | -0.059 | -3.149 | 0.018 | 0.583 | False |
| (6, 3) | 2540 | 13.804 | -0.069 | -2.312 | 0.010 | 0.188 | 0.052 | 0.600 | False |
| (6, 5) | 4936 | 26.826 | -0.008 | -0.318 | 0.019 | 0.481 | 0.037 | 0.579 | False |
| (6, 10) | 12106 | 65.793 | 0.006 | 0.268 | 0.048 | 1.670 | 0.102 | 2.349 | True |

## Most-picked streams (months picked, all variants)

|  | months |
|---|---|
| USDJPY · GOTOBI | 168 |
| EURJPY · GOTOBI | 164 |
| GBPUSD · F2 ldn-fix fade | 141 |
| USDJPY · I3 inside-bo | 117 |
| USDJPY · BOX-C fade | 112 |
| USDJPY · GOTOBI vol | 101 |
| GBPJPY · I3 inside-bo | 97 |
| EURAUD · F2 ldn-fix fade | 97 |
| USDJPY · I2 prevday-bo | 96 |
| EURUSD · F2 ldn-fix fade | 92 |
| EURJPY · I1 ldn-breakout | 92 |
| CADJPY · F1 month-end | 87 |
| CHFJPY · GOTOBI | 87 |
| EURJPY · I2 prevday-bo | 86 |
| XAUUSD · I1 ldn-breakout | 86 |

## Alpha Swing prop simulation

| mix | window | pass ≤1 month % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | months per funded account |
|---|---|---|---|---|---|---|---|
| current basket | starts 2011-2025 | 7.8 | 28.1 | 44.4 | 31.1 | 59.1 | 7.3 |
| rotation L6 K10 0.5% | starts 2011-2025 | 2.6 | 8.2 | 14.4 | 60.7 | 23.5 | 18.8 |
| rotation L6 K10 1% | starts 2011-2025 | 5.0 | 12.9 | 16.2 | 81.3 | 16.6 | 9.0 |
| basket + rotation 0.5% | starts 2011-2025 | 8.0 | 18.4 | 22.6 | 68.6 | 25.9 | 8.6 |
| current basket | starts 2018-2025 | 6.9 | 33.0 | 58.1 | 19.4 | 74.0 | 5.8 |
| rotation L6 K10 0.5% | starts 2018-2025 | 2.9 | 6.7 | 10.2 | 67.8 | 13.1 | 32.0 |
| rotation L6 K10 1% | starts 2018-2025 | 5.5 | 11.2 | 11.5 | 84.5 | 11.5 | 12.3 |
| basket + rotation 0.5% | starts 2018-2025 | 6.6 | 17.5 | 21.4 | 71.3 | 25.1 | 8.2 |
