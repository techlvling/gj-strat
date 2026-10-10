# Alpha Swing: risk rules on the current basket

Rules in run_prop_risk_rules.py (fixed before running).

| rule | window | pass ≤1 month % | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | fails by daily limit % | pass eventually % | median months to pass | months per funded account | accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | starts 2011-2025 | 7.8 | 19.9 | 28.0 | 44.4 | 31.1 | 2.7 | 59.1 | 3.3 | 7.3 | None |
| boost 1.5 | starts 2011-2025 | 12.2 | 23.6 | 31.3 | 43.4 | 50.9 | 19.7 | 46.2 | 2.0 | 4.9 | True |
| boost 2 | starts 2011-2025 | 14.9 | 25.3 | 30.8 | 39.2 | 58.2 | 20.2 | 39.9 | 1.4 | 4.3 | False |
| protect | starts 2011-2025 | 7.6 | 19.7 | 26.9 | 42.5 | 17.8 | 4.8 | 62.6 | 3.8 | 9.9 | False |
| finish | starts 2011-2025 | 7.4 | 19.4 | 27.9 | 44.4 | 30.9 | 1.8 | 59.2 | 3.3 | 7.4 | False |
| P2 half | starts 2011-2025 | 3.4 | 15.0 | 21.9 | 35.9 | 25.0 | 1.3 | 68.1 | 5.4 | 8.8 | False |
| boost 2 + protect | starts 2011-2025 | 13.4 | 23.7 | 29.3 | 38.0 | 46.4 | 27.8 | 44.0 | 1.8 | 7.2 | False |
| boost 2 + protect + finish | starts 2011-2025 | 13.2 | 24.4 | 30.5 | 39.3 | 45.5 | 26.8 | 44.6 | 1.8 | 7.1 | False |
| boost 2 + protect + P2 half | starts 2011-2025 | 10.6 | 21.3 | 27.7 | 41.5 | 34.3 | 16.9 | 56.0 | 3.1 | 8.2 | False |
| base | starts 2018-2025 | 6.9 | 22.2 | 32.9 | 58.1 | 19.4 | 0.0 | 74.0 | 3.6 | 5.8 | None |
| boost 1.5 | starts 2018-2025 | 11.9 | 25.1 | 34.5 | 51.9 | 42.7 | 12.3 | 55.2 | 2.3 | 4.3 | True |
| boost 2 | starts 2018-2025 | 15.2 | 26.6 | 32.9 | 45.0 | 52.7 | 16.0 | 45.1 | 1.6 | 3.9 | False |
| protect | starts 2018-2025 | 6.5 | 21.5 | 30.7 | 53.9 | 9.5 | 0.0 | 80.5 | 4.3 | 7.1 | False |
| finish | starts 2018-2025 | 6.5 | 21.7 | 32.6 | 57.2 | 19.8 | 0.0 | 72.9 | 3.6 | 5.9 | False |
| P2 half | starts 2018-2025 | 2.2 | 16.0 | 24.6 | 44.5 | 15.9 | 0.0 | 80.6 | 5.1 | 7.3 | False |
| boost 2 + protect | starts 2018-2025 | 13.0 | 24.2 | 29.9 | 43.5 | 36.9 | 28.0 | 52.0 | 2.3 | 6.9 | False |
| boost 2 + protect + finish | starts 2018-2025 | 13.2 | 25.6 | 32.1 | 45.5 | 34.9 | 26.3 | 52.9 | 2.1 | 6.7 | False |
| boost 2 + protect + P2 half | starts 2018-2025 | 10.0 | 23.5 | 30.7 | 49.0 | 27.1 | 17.6 | 65.5 | 3.3 | 7.0 | False |
