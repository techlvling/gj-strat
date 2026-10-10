# Gotobi short: Japanese calendar and entry time (USDJPY 2010–2026)

Rules and pass test in run_gotobi_calendar.py.

| setup | design trades | design win % | design avg R | design t | check trades | check win % | check avg R | check t | holdout trades | holdout win % | holdout avg R | holdout t | replaces current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| current (weekend calendar, 09:55) | 561 | 54.724 | 0.144 | 3.163 | 432 | 52.546 | 0.112 | 2.206 | 199 | 47.236 | 0.107 | 1.458 | False |
| JP calendar, entry 09:50 | 560 | 50.357 | 0.047 | 1.136 | 430 | 51.628 | 0.083 | 1.604 | 199 | 43.719 | 0.038 | 0.500 | False |
| JP calendar, entry 09:55 | 560 | 53.929 | 0.143 | 2.896 | 430 | 52.558 | 0.099 | 1.960 | 199 | 47.739 | 0.107 | 1.442 | False |
| JP calendar, entry 10:00 | 560 | 51.250 | 0.095 | 2.018 | 430 | 50.233 | 0.046 | 0.959 | 199 | 41.709 | -0.000 | -0.007 | False |
