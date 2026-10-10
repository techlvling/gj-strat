# Alpha Swing: adding the fade to vol-box + gotobi

Rules in run_swing_basket.py.

## Fade, with and without the vol filter

| setup | design trades | design avg R | design t | check trades | check avg R | check t | holdout trades | holdout avg R | holdout t |
|---|---|---|---|---|---|---|---|---|---|
| fade | 823.000 | 0.140 | 1.649 | 565.000 | 0.144 | 1.404 | 284.000 | 0.150 | 1.016 |
| vol-filtered fade | 307.000 | 0.281 | 1.938 | 253.000 | -0.086 | -0.611 | 117.000 | 0.323 | 1.366 |

Vol-filtered fade accepted: **False**

## Alpha Swing challenge

| mix | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | median months to pass | months per funded account | max DD % |
|---|---|---|---|---|---|---|---|---|
| vol-box 0.25% + gotobi 3% (current pick) | 23.1 | 35.9 | 51.6 | 39.4 | 54.7 | 2.3 | 5.5 | 40.0 |
| vol-box 0.25% + gotobi 4% | 30.4 | 41.7 | 50.5 | 47.3 | 50.9 | 1.7 | 4.1 | 49.7 |
| vol-box 0.25% + gotobi 2% + fade 0.25% | 13.6 | 26.0 | 48.1 | 22.5 | 63.1 | 3.6 | 8.0 | 26.8 |
| vol-box 0.25% + gotobi 3% + fade 0.25% | 22.8 | 33.5 | 48.3 | 42.5 | 53.0 | 2.3 | 5.8 | 37.6 |
| vol-box 0.25% + gotobi 2% + fade 0.5% | 18.0 | 30.2 | 50.1 | 35.4 | 60.5 | 3.1 | 5.9 | 28.9 |
| vol-box 0.25% + gotobi 3% + fade 0.5% | 25.4 | 37.2 | 51.7 | 43.6 | 55.7 | 2.2 | 4.5 | 36.3 |
| vol-box 0.5% + gotobi 3% + fade 0.5% | 24.9 | 34.0 | 44.3 | 53.1 | 45.7 | 1.8 | 4.7 | 38.0 |
