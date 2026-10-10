# Alpha Capital — Alpha Swing challenge with vol-box + gotobi (USDJPY)

Rules (as reported; verify): P1 +10%, P2 +5%, 10% static max loss, 5% daily, ≥3 days per phase. Details in run_prop_alpha_swing.py.

| mix | rules | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | fails by daily limit % | median months to pass | months per funded account | fees per funded account $ |
|---|---|---|---|---|---|---|---|---|---|---|
| vol-box 0.25% + gotobi 2% | no consistency rule | 10.4 | 22.6 | 48.8 | 17.6 | 66.5 | 0.0 | 4.1 | 8.5 | 150.3 |
| vol-box 0.25% + gotobi 3% | no consistency rule | 22.5 | 35.6 | 51.5 | 39.3 | 54.7 | 0.0 | 2.3 | 5.6 | 182.7 |
| vol-box 0.25% + gotobi 4% | no consistency rule | 29.5 | 41.4 | 50.5 | 47.4 | 50.8 | 0.4 | 1.8 | 4.1 | 196.7 |
| vol-box 0.5% + gotobi 2% | no consistency rule | 16.2 | 28.2 | 50.3 | 32.5 | 59.1 | 0.0 | 3.2 | 6.4 | 169.1 |
| vol-box 0.5% + gotobi 3% | no consistency rule | 23.9 | 35.0 | 49.2 | 42.8 | 51.7 | 0.4 | 2.2 | 5.3 | 193.3 |
| vol-box 0.5% + gotobi 4% | no consistency rule | 28.4 | 36.7 | 43.4 | 55.5 | 43.5 | 12.4 | 1.5 | 4.1 | 230.1 |
| vol-box 0.25% + gotobi 2% | 40% consistency rule | 0.4 | 4.7 | 17.3 | 14.4 | 59.6 | 0.0 | 8.9 | 24.3 | 167.8 |
| vol-box 0.25% + gotobi 3% | 40% consistency rule | 1.0 | 4.8 | 17.0 | 31.1 | 50.2 | 0.0 | 8.8 | 21.8 | 199.3 |
| vol-box 0.25% + gotobi 4% | 40% consistency rule | 1.2 | 5.0 | 16.7 | 41.8 | 43.1 | 4.2 | 8.1 | 21.7 | 232.0 |
| vol-box 0.5% + gotobi 2% | 40% consistency rule | 0.9 | 4.2 | 12.9 | 28.8 | 45.6 | 0.0 | 9.1 | 23.2 | 219.2 |
| vol-box 0.5% + gotobi 3% | 40% consistency rule | 1.5 | 5.8 | 14.1 | 42.1 | 38.9 | 4.6 | 8.2 | 23.0 | 257.0 |
| vol-box 0.5% + gotobi 4% | 40% consistency rule | 1.9 | 5.5 | 10.4 | 70.0 | 15.5 | 30.2 | 4.0 | 25.0 | 645.0 |
