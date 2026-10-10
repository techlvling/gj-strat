# Costs and gotobi refinements (USDJPY 2010–2026)

Rules in run_costs_gotobi_vol.py.

## A. Avg R per trade 2010–2026 by commission (rows) and slippage per stop fill (columns)

|  | slip 0 | slip 0.2 | slip 0.5 | slip 1 |
|---|---|---|---|---|
| ('fade', 0.0) | 0.231 | 0.203 | 0.161 | 0.091 |
| ('fade', 3.5) | 0.201 | 0.173 | 0.131 | 0.061 |
| ('fade', 7.0) | 0.171 | 0.143 | 0.101 | 0.031 |
| ('fade', 10.0) | 0.145 | 0.117 | 0.075 | 0.005 |
| ('gotobi', 0.0) | 0.177 | 0.165 | 0.146 | 0.115 |
| ('gotobi', 3.5) | 0.158 | 0.146 | 0.127 | 0.096 |
| ('gotobi', 7.0) | 0.139 | 0.126 | 0.108 | 0.077 |
| ('gotobi', 10.0) | 0.122 | 0.110 | 0.091 | 0.060 |
| ('vol-box', 0.0) | 0.266 | 0.245 | 0.214 | 0.162 |
| ('vol-box', 3.5) | 0.244 | 0.223 | 0.192 | 0.139 |
| ('vol-box', 7.0) | 0.222 | 0.201 | 0.170 | 0.117 |
| ('vol-box', 10.0) | 0.203 | 0.182 | 0.151 | 0.098 |

## B–C. Gotobi limit entry and vol filter

| variant | trades | win % | design avg R | check avg R | holdout avg R | beats current in every period |
|---|---|---|---|---|---|---|
| gotobi market entry (current) | 1192 | 52.685 | 0.144 | 0.112 | 0.107 | None |
| limit +1 pip, valid 5 min | 712 | 49.719 | 0.021 | 0.076 | 0.119 | False |
| limit +1 pip, valid 15 min | 852 | 49.296 | 0.060 | 0.094 | 0.048 | False |
| limit +2 pip, valid 5 min | 483 | 48.240 | -0.024 | -0.002 | 0.082 | False |
| limit +2 pip, valid 15 min | 667 | 48.576 | 0.057 | 0.060 | 0.022 | False |
| vol filter: ATR20 >= 250-day median | 499 | 52.505 | 0.173 | 0.167 | 0.214 | True |
| vol filter: ATR20 < 250-day median | 624 | 52.724 | 0.125 | 0.066 | 0.024 | False |

## Gotobi vol filter: neighbouring settings

|  | kept % | design avg R | check avg R | holdout avg R |
|---|---|---|---|---|
| (125, 0.9) | 64.670 | 0.158 | 0.112 | 0.085 |
| (125, 1.0) | 46.079 | 0.176 | 0.046 | 0.049 |
| (125, 1.1) | 31.454 | 0.047 | 0.177 | 0.177 |
| (250, 0.9) | 59.824 | 0.176 | 0.100 | 0.158 |
| (250, 1.0) | 43.965 | 0.173 | 0.167 | 0.214 |
| (250, 1.1) | 33.216 | 0.176 | 0.221 | 0.283 |
| (500, 0.9) | 57.004 | 0.168 | 0.144 | 0.247 |
| (500, 1.0) | 44.493 | 0.182 | 0.121 | 0.253 |
| (500, 1.1) | 34.537 | 0.243 | 0.178 | 0.395 |

## Alpha Swing challenge with vol-filtered gotobi

| mix | pass ≤2 months % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | pass eventually % | median months to pass | months per funded account | max DD % |
|---|---|---|---|---|---|---|---|---|
| current: vol-box 0.25% + gotobi 3% + fade 0.5% | 25.4 | 37.2 | 51.7 | 43.6 | 55.7 | 2.2 | 4.5 | 36.3 |
| vol-box 0.25% + vol-gotobi 3% + fade 0.5% | 19.8 | 26.5 | 37.7 | 30.9 | 52.2 | 3.0 | 9.4 | 28.1 |
| vol-box 0.25% + vol-gotobi 4% + fade 0.5% | 20.0 | 24.9 | 33.7 | 49.5 | 40.3 | 2.0 | 8.1 | 32.2 |
| vol-box 0.25% + gotobi 2% + vol-gotobi +2% (4% on hot days) + fade 0.5% | 22.1 | 31.5 | 43.9 | 50.8 | 47.4 | 2.1 | 5.0 | 32.4 |
| vol-box 0.25% + vol-gotobi 3% | 20.5 | 31.6 | 43.4 | 14.1 | 58.4 | 2.7 | 12.2 | 20.4 |
