# Adaptive rules on the USDJPY basket, 2010–2026

Rules in run_adaptive.py (fixed before running).

## Fade in high vs low volatility

| fade on | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t |
|---|---|---|---|---|---|---|---|---|---|
| high-vol days | 307.000 | 0.281 | 1.938 | 253.000 | -0.086 | -0.611 | 117.000 | 0.323 | 1.366 |
| low-vol days | 383.000 | 0.047 | 0.390 | 312.000 | 0.331 | 2.270 | 167.000 | 0.029 | 0.153 |

## Baskets (simple-sum % at vol-box 0.25%, vol-gotobi 1.5%, fade 0.5%)

| basket | design return % | design max DD % | design return/DD | check return % | check max DD % | check return/DD | holdout return % | holdout max DD % | holdout return/DD | accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| base: vol-box + vol-gotobi + fade (all days) | 148.52 | 26.54 | 5.60 | 134.27 | 20.90 | 6.42 | 67.95 | 21.31 | 3.19 | None |
| 1. regime switch: fade only on low-vol days | 99.92 | 17.36 | 5.75 | 145.17 | 19.24 | 7.55 | 49.06 | 21.39 | 2.29 | False |
| 2. strategy momentum (6-month R > 0) | 75.16 | 23.82 | 3.16 | 103.56 | 17.59 | 5.89 | 46.08 | 12.99 | 3.55 | False |
