# Month-end USD bid (M-3) as a 4th prop leg

Rules and acceptance in run_m3_addon.py (fixed before running).

## The new legs alone (avg R after costs)

| leg | trades | win % | avg R | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M-3 USDJPY | 189.000 | 58.730 | 0.124 | 84.000 | 0.091 | 2.107 | 72.000 | 0.210 | 3.463 | 33.000 | 0.022 | 0.356 |
| M-3 other five pairs | 945.000 | 53.757 | 0.053 | 420.000 | 0.075 | 3.086 | 360.000 | 0.012 | 0.399 | 165.000 | 0.084 | 2.234 |

## A. Alpha Swing $10k

| mix | window | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | median months to pass | months per funded account | max DD % | accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| base: vol-box 0.25% + vol-gotobi 3% + fade 0.5% | starts 2011-2025 | 19.8 | 26.5 | 37.7 | 30.9 | 52.2 | 3.0 | 9.4 | 28.1 | None |
| + M-3 USDJPY 1% | starts 2011-2025 | 19.2 | 26.2 | 38.0 | 30.9 | 53.4 | 3.2 | 9.0 | 27.6 | True |
| + M-3 USDJPY 2% | starts 2011-2025 | 19.6 | 26.6 | 40.7 | 31.3 | 55.5 | 3.2 | 8.2 | 27.0 | True |
| + M-3 USDJPY 3% | starts 2011-2025 | 19.9 | 28.0 | 44.4 | 31.1 | 59.1 | 3.3 | 7.3 | 26.4 | True |
| + M-3 six pairs 0.25% each (1.5%) | starts 2011-2025 | 19.7 | 26.2 | 37.4 | 34.6 | 50.2 | 2.8 | 9.5 | 28.2 | False |
| + M-3 six pairs 0.5% each (3%) | starts 2011-2025 | 19.6 | 26.5 | 37.5 | 35.3 | 53.0 | 3.1 | 8.7 | 28.2 | False |
| base: vol-box 0.25% + vol-gotobi 3% + fade 0.5% | starts 2018-2025 | 22.1 | 30.2 | 46.6 | 22.2 | 64.2 | 3.2 | 7.5 | 24.5 | None |
| + M-3 USDJPY 1% | starts 2018-2025 | 21.3 | 30.2 | 47.8 | 21.8 | 66.9 | 3.6 | 7.0 | 23.5 | True |
| + M-3 USDJPY 2% | starts 2018-2025 | 21.8 | 30.8 | 53.1 | 20.8 | 71.4 | 3.8 | 6.2 | 24.2 | True |
| + M-3 USDJPY 3% | starts 2018-2025 | 22.2 | 32.9 | 58.1 | 19.4 | 74.0 | 3.6 | 5.8 | 24.8 | True |
| + M-3 six pairs 0.25% each (1.5%) | starts 2018-2025 | 22.2 | 30.4 | 47.5 | 29.0 | 60.4 | 3.0 | 7.2 | 24.1 | False |
| + M-3 six pairs 0.5% each (3%) | starts 2018-2025 | 21.8 | 30.8 | 48.1 | 30.1 | 60.8 | 3.0 | 6.8 | 23.6 | False |

## B. Blueberry Instant Elite $2.5k (10% cushion)

| mix | window | got ≥1 payout % | avg paid in 12 months $ | avg paid in 24 months $ | avg per month $ | account lost within 24 months % | accepted |
|---|---|---|---|---|---|---|---|
| base: vol-box 0.25% + vol-gotobi 1.5% | starts 2011-2024 | 71 | 269 | 494 | 21 | 23 | None |
| + M-3 USDJPY 0.5% | starts 2011-2024 | 77 | 270 | 548 | 23 | 9 | True |
| + M-3 USDJPY 1% | starts 2011-2024 | 77 | 279 | 571 | 24 | 9 | True |
| + M-3 USDJPY 1.5% | starts 2011-2024 | 78 | 288 | 591 | 25 | 9 | True |
| + M-3 six pairs 0.25% each (1.5%) | starts 2011-2024 | 76 | 276 | 555 | 23 | 14 | True |
| base: vol-box 0.25% + vol-gotobi 1.5% | starts 2018-2024 | 84 | 324 | 638 | 27 | 19 | None |
| + M-3 USDJPY 0.5% | starts 2018-2024 | 88 | 331 | 700 | 29 | 4 | True |
| + M-3 USDJPY 1% | starts 2018-2024 | 89 | 344 | 729 | 30 | 2 | True |
| + M-3 USDJPY 1.5% | starts 2018-2024 | 90 | 358 | 758 | 32 | 2 | True |
| + M-3 six pairs 0.25% each (1.5%) | starts 2018-2024 | 85 | 335 | 697 | 29 | 14 | True |

## Robustness: neighbouring risk settings (run_m3_neighbours.py)

### Alpha Swing, starts 2011–2025

| mix | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | months per funded account |
|---|---|---|---|---|---|
| box 0.2% · gotobi 3% · fade 0.5% | 26.2 | 37.3 | 31.2 | 53.1 | 9.4 |
| box 0.2% · gotobi 3% · fade 0.5% + M-3 3% | 27.4 | 44.3 | 29.8 | 60.3 | 7.4 |
| box 0.3% · gotobi 3% · fade 0.5% | 26.6 | 37.2 | 33.3 | 52.2 | 9.1 |
| box 0.3% · gotobi 3% · fade 0.5% + M-3 3% | 27.7 | 43.1 | 34.4 | 55.7 | 7.4 |
| box 0.25% · gotobi 2.5% · fade 0.5% | 25.9 | 37.5 | 28.0 | 56.8 | 9.7 |
| box 0.25% · gotobi 2.5% · fade 0.5% + M-3 3% | 26.1 | 43.4 | 28.1 | 62.3 | 7.6 |
| box 0.25% · gotobi 3.5% · fade 0.5% | 25.3 | 35.0 | 41.6 | 45.9 | 9.0 |
| box 0.25% · gotobi 3.5% · fade 0.5% + M-3 3% | 27.9 | 40.4 | 40.2 | 49.6 | 7.4 |

### Blueberry Elite, starts 2011–2024

| mix | got ≥1 payout % | avg paid in 24 months $ | account lost within 24 months % |
|---|---|---|---|
| box 0.25% · gotobi 1.4% | 73.2 | 475.6 | 17.9 |
| box 0.25% · gotobi 1.4% + M-3 0.5% | 76.7 | 518.2 | 9.3 |
| box 0.25% · gotobi 1.6% | 70.7 | 520.7 | 26.9 |
| box 0.25% · gotobi 1.6% + M-3 0.5% | 74.4 | 564.3 | 12.7 |
| box 0.2% · gotobi 1.5% | 74.0 | 463.3 | 17.2 |
| box 0.2% · gotobi 1.5% + M-3 0.5% | 77.6 | 507.0 | 5.9 |
| box 0.3% · gotobi 1.5% | 63.3 | 477.4 | 37.5 |
| box 0.3% · gotobi 1.5% + M-3 0.5% | 65.0 | 516.1 | 36.2 |
