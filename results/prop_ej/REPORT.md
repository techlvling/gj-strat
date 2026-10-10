# Prop challenge — adding EURJPY gotobi to USDJPY box + gotobi

Correlation of USDJPY and EURJPY gotobi results on the same days: 0.79. Mixes fixed before running; rules and costs in run_prop_ej.py.

| mix | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | median months to pass | fails by daily 4% % | max DD % 2010–26 | per year % |
|---|---|---|---|---|---|---|---|---|
| box 0.25% + UJ gotobi 2% (current best) | 12.6 | 26.4 | 51.1 | 29.5 | 3.7 | 0.0 | 27.7 | 25.6 |
| box 0.25% + UJ 1% + EJ 1% (same total) | 9.0 | 20.9 | 45.2 | 26.5 | 3.9 | 0.0 | 26.8 | 23.1 |
| box 0.25% + UJ 1.5% + EJ 1% | 13.8 | 28.7 | 49.4 | 34.3 | 3.1 | 0.0 | 31.1 | 27.7 |
| box 0.25% + UJ 2% + EJ 1% (added on top) | 18.2 | 33.4 | 52.8 | 41.0 | 2.7 | 0.0 | 35.8 | 32.2 |
| box 0.25% + UJ 2% + EJ 2% | 15.6 | 18.0 | 19.1 | 80.9 | 1.2 | 79.1 | 48.8 | 38.2 |
