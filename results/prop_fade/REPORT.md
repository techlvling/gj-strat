# Prop challenge — USDJPY box vs fade vs both, with gotobi

Trades: box 4556, fade 1672, gotobi 1192. Correlation of daily box and fade results: 0.12. Mixes fixed before running; rules and costs in run_prop_fade.py.

| mix | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | median months to pass | fails by daily 4% % | max DD % 2010–26 | per year % |
|---|---|---|---|---|---|---|---|---|
| box 0.25% + gotobi 2% (current best) | 12.5 | 26.3 | 51.0 | 29.6 | 3.7 | 0.0 | 27.7 | 25.6 |
| fade 0.25% + gotobi 2% | 8.4 | 19.5 | 45.2 | 24.8 | 4.3 | 0.0 | 25.5 | 21.8 |
| fade 0.5% + gotobi 2% | 15.0 | 27.0 | 50.1 | 35.3 | 3.3 | 2.0 | 31.1 | 25.4 |
| box 0.25% + fade 0.25% + gotobi 2% | 17.6 | 29.7 | 50.4 | 34.2 | 3.1 | 1.4 | 28.4 | 29.7 |
| box 0.25% + fade 0.25% + gotobi 1.5% | 12.6 | 24.9 | 46.3 | 27.7 | 3.7 | 0.0 | 24.8 | 24.9 |
| fade 0.5% alone | 1.6 | 4.2 | 15.4 | 15.0 | 9.4 | 0.0 | 22.1 | 6.6 |
