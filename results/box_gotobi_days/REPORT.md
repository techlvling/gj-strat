# USDJPY green box on gotobi days only, 2010–2026

Variants and pass rule in run_box_gotobi_days.py.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | holdout trades | holdout win % | holdout avg R | holdout t | all avg R | all t | beats all-days in every period |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B all days (green) | 2233 | 23.556 | 0.061 | 1.005 | 1557 | 22.286 | 0.163 | 2.111 | 766 | 24.021 | 0.136 | 1.256 | 0.109 | 2.477 | None |
| B gotobi days | 630 | 20.000 | -0.186 | -1.812 | 439 | 23.007 | 0.167 | 1.139 | 210 | 28.095 | 0.438 | 1.944 | 0.037 | 0.465 | False |
| B non-gotobi days | 1603 | 24.953 | 0.159 | 2.120 | 1118 | 22.004 | 0.162 | 1.777 | 556 | 22.482 | 0.021 | 0.175 | 0.137 | 2.611 | None |
| SELL only, gotobi days | 391 | 24.552 | 0.027 | 0.188 | 250 | 20.400 | 0.058 | 0.313 | 130 | 25.385 | 0.379 | 1.367 | 0.096 | 0.919 | False |
| SELL only, all days | 1363 | 25.165 | 0.152 | 1.891 | 901 | 20.089 | 0.085 | 0.871 | 453 | 20.088 | 0.048 | 0.355 | 0.113 | 1.993 | None |
| BUY only, gotobi days | 389 | 18.509 | -0.150 | -1.098 | 270 | 23.333 | 0.049 | 0.275 | 129 | 32.558 | 0.700 | 2.223 | 0.058 | 0.549 | False |
| BUY only, all days | 1339 | 21.583 | -0.007 | -0.088 | 978 | 24.642 | 0.249 | 2.464 | 475 | 27.789 | 0.363 | 2.422 | 0.146 | 2.542 | None |
