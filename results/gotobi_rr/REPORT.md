# Gotobi short: RR exit vs time exit (USDJPY 2010–2026)

Rules and pass test in run_gotobi_rr.py.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | holdout trades | holdout win % | holdout avg R | holdout t | holdout max DD % (0.5%) | replaces current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| current: time exit 15:00 JST | 561 | 54.724 | 0.144 | 3.163 | 432 | 52.546 | 0.112 | 2.206 | 199 | 47.236 | 0.107 | 1.458 | 6.583 | False |
| RR exit TP 1R (no time exit) | 561 | 54.724 | 0.044 | 1.035 | 432 | 56.481 | 0.067 | 1.385 | 197 | 55.838 | 0.065 | 0.907 | 6.080 | False |
| RR exit TP 1.5R (no time exit) | 561 | 45.455 | 0.083 | 1.569 | 432 | 44.676 | 0.049 | 0.820 | 197 | 43.147 | 0.004 | 0.048 | 13.739 | False |
| RR exit TP 2R (no time exit) | 561 | 38.859 | 0.110 | 1.777 | 432 | 38.426 | 0.081 | 1.151 | 197 | 37.563 | 0.048 | 0.451 | 13.905 | False |
| RR exit TP 3R (no time exit) | 561 | 29.768 | 0.130 | 1.673 | 432 | 29.398 | 0.095 | 1.078 | 197 | 26.904 | -0.014 | -0.110 | 14.800 | False |
