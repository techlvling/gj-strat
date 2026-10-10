# Alpha Swing with the Nasdaq calendar trades

Rules in run_index_prop.py (fixed before running). Added: E1b turn of month (from last day).

| mix | risk rule | window | pass ≤1 month % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | median months to pass | months per funded account | accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| basket | normal risk | starts 2011-2025 | 7.8 | 28.1 | 44.4 | 31.1 | 59.1 | 3.3 | 7.3 | None |
| basket + E1b 1% | normal risk | starts 2011-2025 | 7.9 | 26.7 | 45.5 | 29.8 | 60.1 | 3.5 | 7.2 | True |
| basket + E1b 2% | normal risk | starts 2011-2025 | 7.9 | 29.2 | 47.4 | 31.8 | 60.2 | 3.2 | 6.6 | False |
| basket | normal risk | starts 2018-2025 | 6.9 | 33.0 | 58.1 | 19.4 | 74.0 | 3.6 | 5.8 | None |
| basket + E1b 1% | normal risk | starts 2018-2025 | 6.9 | 30.0 | 58.7 | 17.8 | 75.7 | 3.9 | 5.8 | True |
| basket + E1b 2% | normal risk | starts 2018-2025 | 6.8 | 31.0 | 58.7 | 22.8 | 71.1 | 3.5 | 5.5 | False |
| basket | boost x1.5 | starts 2011-2025 | 12.2 | 31.3 | 43.4 | 50.9 | 46.2 | 2.0 | 4.9 | None |
| basket + E1b 1% | boost x1.5 | starts 2011-2025 | 12.2 | 30.7 | 45.3 | 50.1 | 47.6 | 2.1 | 4.7 | True |
| basket + E1b 2% | boost x1.5 | starts 2011-2025 | 12.2 | 32.1 | 44.7 | 51.9 | 46.4 | 2.0 | 4.5 | True |
| basket | boost x1.5 | starts 2018-2025 | 11.9 | 34.5 | 51.9 | 42.7 | 55.2 | 2.3 | 4.3 | None |
| basket + E1b 1% | boost x1.5 | starts 2018-2025 | 11.5 | 32.5 | 55.3 | 41.0 | 57.6 | 2.7 | 4.1 | True |
| basket + E1b 2% | boost x1.5 | starts 2018-2025 | 11.5 | 34.3 | 53.8 | 43.3 | 56.0 | 2.5 | 4.0 | True |
