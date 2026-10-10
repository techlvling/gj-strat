# Drawdown filters for the USDJPY green box (2010–2026)

Filters and acceptance rule in run_box_dd_filters.py (fixed before running).

| setup | share of trades kept % | design trades | design avg R | design t | design max DD % (0.5%) | check trades | check avg R | check t | check max DD % (0.5%) | holdout trades | holdout avg R | holdout t | holdout max DD % (0.5%) | all trades | all avg R | all max DD % (0.5%) | accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| box (no filter) | 100.00 | 2233 | 0.06 | 1.00 | 41.54 | 1557 | 0.16 | 2.11 | 29.52 | 766 | 0.14 | 1.26 | 26.56 | 4556 | 0.11 | 41.54 | None |
| vol filter | 42.76 | 868 | 0.16 | 1.59 | 23.61 | 737 | 0.24 | 2.09 | 26.00 | 343 | 0.22 | 1.33 | 10.62 | 1948 | 0.20 | 26.00 | True |
| equity filter | 57.57 | 1255 | 0.01 | 0.08 | 29.40 | 902 | 0.18 | 1.78 | 29.99 | 466 | -0.02 | -0.14 | 32.97 | 2623 | 0.06 | 37.44 | False |
| vol + equity | 30.25 | 581 | 0.08 | 0.68 | 21.13 | 550 | 0.25 | 1.87 | 15.14 | 247 | -0.00 | -0.02 | 20.85 | 1378 | 0.13 | 21.13 | False |

## Robustness: neighbouring vol-filter settings

|  | kept % | design avg R | design max DD % (0.5%) | check avg R | check max DD % (0.5%) | holdout avg R | holdout max DD % (0.5%) |
|---|---|---|---|---|---|---|---|
| (125, 0.9) | 62.27 | 0.20 | 20.92 | 0.21 | 25.52 | 0.11 | 25.67 |
| (125, 1.0) | 43.85 | 0.16 | 19.10 | 0.26 | 26.32 | 0.16 | 17.17 |
| (125, 1.1) | 30.36 | 0.21 | 18.81 | 0.41 | 15.74 | 0.30 | 10.94 |
| (250, 0.9) | 56.37 | 0.11 | 31.25 | 0.18 | 28.43 | 0.10 | 19.27 |
| (250, 1.0) | 42.76 | 0.16 | 23.61 | 0.24 | 26.00 | 0.22 | 10.62 |
| (250, 1.1) | 32.02 | 0.15 | 24.09 | 0.33 | 15.34 | 0.50 | 10.62 |
| (500, 0.9) | 54.15 | 0.13 | 28.22 | 0.22 | 28.48 | 0.12 | 16.44 |
| (500, 1.0) | 42.56 | 0.20 | 17.10 | 0.21 | 21.18 | 0.23 | 14.00 |
| (500, 1.1) | 33.56 | 0.11 | 20.10 | 0.21 | 24.67 | 0.34 | 11.08 |

## Prop challenge with the vol-filtered box

| mix | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | months per funded account | fees per funded account $ | max DD % | per year % |
|---|---|---|---|---|---|---|---|---|---|
| current: box 0.25% + gotobi 2% | 12.5 | 26.3 | 51.0 | 29.6 | 64.9 | 6.4 | 154.0 | 27.7 | 25.6 |
| challenge: box 0.25% + gotobi 3% | 23.0 | 35.5 | 47.8 | 48.2 | 50.1 | 5.0 | 199.6 | 37.4 | 34.8 |
| gotobi 2% alone | 4.6 | 13.6 | 41.1 | 16.1 | 67.6 | 9.3 | 148.0 | 28.0 | 18.1 |
| vol-box 0.25% + gotobi 2% | 12.1 | 25.5 | 49.6 | 18.3 | 67.8 | 8.1 | 147.5 | 28.8 | 24.6 |
| vol-box 0.5% + gotobi 2% | 16.5 | 27.5 | 46.4 | 37.3 | 54.2 | 6.8 | 184.6 | 30.2 | 30.6 |
| vol-box 1% + gotobi 2% | 16.5 | 20.6 | 27.6 | 69.2 | 28.5 | 6.4 | 351.1 | 44.8 | 40.5 |
| vol-box 0.25% + gotobi 3% | 25.5 | 39.6 | 55.4 | 35.9 | 58.7 | 4.9 | 170.4 | 40.0 | 33.8 |
| vol-box 0.5% + gotobi 3% | 25.2 | 34.4 | 47.0 | 50.2 | 48.1 | 4.7 | 208.0 | 40.8 | 40.2 |
| vol-box 1% + gotobi 3% | 17.8 | 20.9 | 24.6 | 74.7 | 24.9 | 5.1 | 402.3 | 45.2 | 50.7 |
