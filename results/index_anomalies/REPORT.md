# Equity-index calendar anomalies (Nasdaq 100, S&P 500 replication)

Rules in run_index_anomalies.py (fixed before running).

**Survivors: 0 of 7**

## Nasdaq 100

| test | trades | win % | avg win / avg loss | avg R | design n | design avg R | design t | check avg R | check t | holdout avg R | holdout t | survives |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1a turn of month | 168 | 44.643 | 1.309 | 0.029 | 64 | 0.097 | 0.604 | 0.021 | 0.146 | -0.087 | -0.407 | False |
| E1b turn of month (from last day) | 163 | 49.080 | 1.329 | 0.128 | 61 | 0.097 | 0.669 | 0.193 | 1.317 | 0.043 | 0.191 | False |
| E2a overnight | 3535 | 51.485 | 0.922 | -0.007 | 1352 | -0.032 | -1.266 | -0.006 | -0.300 | 0.039 | 1.157 | False |
| E2b overnight, weeknights | 2792 | 51.468 | 0.920 | -0.008 | 1070 | -0.045 | -1.640 | 0.008 | 0.361 | 0.032 | 0.880 | False |
| E3 pre-holiday | 135 | 56.296 | 1.111 | 0.142 | 52 | 0.107 | 0.819 | 0.141 | 1.025 | 0.215 | 1.065 | False |
| E4a intraday momentum | 3517 | 43.901 | 0.948 | -0.065 | 1335 | -0.123 | -7.705 | -0.031 | -2.058 | -0.028 | -1.316 | False |
| E4b intraday momentum, strong first half-hour | 1770 | 43.503 | 0.958 | -0.072 | 678 | -0.121 | -5.122 | -0.045 | -1.961 | -0.033 | -1.054 | False |

## Replication (run_index_replication.py)

### S&P 500, hourly closes

| test | trades | win % | avg net % | t | design avg | check avg | holdout avg | replicates |
|---|---|---|---|---|---|---|---|---|
| E1a turn of month | 176 | 54.545 | 0.149 | 1.056 | 0.075 | 0.189 | 0.229 | True |
| E1b turn of month (from last day) | 176 | 57.386 | 0.178 | 1.332 | 0.086 | 0.301 | 0.108 | True |
| E3 pre-holiday | 138 | 60.870 | 0.088 | 1.430 | 0.034 | 0.124 | 0.124 | True |

### Nikkei 225, minute data

| test | trades | win % | avg R | t | design avg | check avg | holdout avg | replicates |
|---|---|---|---|---|---|---|---|---|
| E1a turn of month | 163 | 43.558 | 0.033 | 0.313 | 0.193 | -0.137 | 0.121 | True |
| E1b turn of month (from last day) | 159 | 44.025 | 0.068 | 0.638 | 0.093 | 0.100 | -0.052 | True |
| E3 pre-holiday | 166 | 45.783 | -0.013 | -0.139 | -0.021 | -0.047 | 0.068 | False |
