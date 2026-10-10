# USDJPY edges on unseen JPY markets — gotobi short and green box, 2010–2026

Frozen rules, costs and pass rule in run_jpy_edges_oos.py. EURJPY / GBPJPY / USDJPY rows are reference only (not clean).

- gotobi: pooled over 5 clean markets 5769 trades, win 44.9%, avg +0.006R, t 0.41 -> FAIL
- box: pooled over 5 clean markets 20531 trades, win 20.4%, avg -0.123R, t -6.61 -> FAIL

| market | clean | gotobi trades | gotobi win % | gotobi avg R | gotobi t | gotobi years + | box trades | box win % | box avg R | box t | box years + |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AUDJPY | True | 1192 | 43.205 | -0.004 | -0.120 | 8/17 | 4891 | 22.306 | 0.029 | 0.706 | 9/17 |
| CADJPY | True | 1192 | 45.805 | 0.022 | 0.760 | 8/17 | 4712 | 19.949 | -0.124 | -3.177 | 6/17 |
| CHFJPY | True | 1191 | 50.798 | 0.062 | 2.083 | 10/17 | 4714 | 18.244 | -0.221 | -5.983 | 2/17 |
| NZDJPY | True | 1192 | 44.211 | 0.002 | 0.063 | 9/17 | 4755 | 19.243 | -0.194 | -5.239 | 2/17 |
| JPNIDXJPY | True | 1002 | 39.521 | -0.060 | -1.239 | 5/15 | 1459 | 25.565 | -0.079 | -1.169 | 3/12 |
| EURJPY | False | 1192 | 50.923 | 0.095 | 2.958 | 12/17 | 4830 | 22.940 | 0.019 | 0.453 | 9/17 |
| GBPJPY | False | 1192 | 48.574 | 0.057 | 1.719 | 11/17 | 4806 | 21.993 | -0.037 | -0.930 | 7/17 |
| USDJPY | False | 1192 | 52.685 | 0.126 | 4.103 | 14/17 | 4556 | 23.200 | 0.109 | 2.477 | 11/17 |
