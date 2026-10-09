# Nas100 15-minute opening-range breakout — Sep 2011 to Oct 2026

Rules exactly as given; see `gjstrat/nas_orb.py` for fill conventions. Data: Dukascopy USATECHIDXUSD 1-minute bid/ask (Nasdaq-100 CFD). Costs: real spread + 1 pt slippage per market/stop fill. **R = P/L ÷ planned loss** (stop distance + 1 pt estimated slippage), per contract.

Days: 3796 NYSE trading days, 201 skipped for missing data, 181 without a signal, 58 skipped because the entry open was back inside the range, **3356 trades**.

## Verdict

* **No edge after costs.** All 3356 trades: avg -0.080 R (t -5.9), win rate 44%. Design years -0.166 R, check -0.022 R, holdout +0.018 R (t +0.5): recent years are about break-even, not a reliable profit. Every nearby variant (1R/1.5R/3R target, hold to 16:00, no back-inside skip) is negative overall too, so it is not one unlucky setting.

* **The 2R target is rarely reached before 11:30**: 124 targets, 862 stops, 2370 time exits. Most trades are small time-exit results that spread and slippage eat.

* **Costs decide the sign.** With zero slippage the whole sample is about flat; each point of slippage per fill takes roughly 0.06 R per trade.

* **Rule 8 sizing makes a challenge impossible to pass on any useful time scale.** With a $2,000 cushion the $50 budget is below one MNQ at the stop on every signal since 2020; on a CFD account a 2R win adds 5% of the cushion, so an 8% target needs a long run of net wins that this strategy does not produce. It also almost never fails, because the risk shrinks with the cushion.

* Data caveat: before mid-2013 Dukascopy has no separate ask (spread 0) and 2013 misses 86 days, so the early years flatter the cost side — and still lose.

## Result by period

| Period | trades | win % | avg R | t | profit factor | total R | max DD (R) | worst losing streak |
|---|---|---|---|---|---|---|---|---|
| design 2011-18 | 1517.000 | 38.431 | -0.166 | -8.713 | 0.583 | -252.481 | 253.083 | 13.000 |
| check 2019-23 | 1182.000 | 47.800 | -0.022 | -0.959 | 0.934 | -26.326 | 39.467 | 13.000 |
| holdout 2024-26 | 657.000 | 50.381 | 0.018 | 0.529 | 1.052 | 11.533 | 21.206 | 9.000 |
| all | 3356.000 | 44.070 | -0.080 | -5.850 | 0.782 | -267.275 | 286.636 | 13.000 |

## By year

| Year | trades | win % | avg R | t | profit factor | total R | max DD (R) | worst losing streak |
|---|---|---|---|---|---|---|---|---|
| 2011 | 4.000 | 50.000 | -0.343 | -0.894 | 0.315 | -1.370 | 1.370 | 1.000 |
| 2012 | 215.000 | 41.860 | -0.135 | -2.609 | 0.655 | -29.122 | 32.654 | 13.000 |
| 2013 | 147.000 | 33.333 | -0.251 | -4.373 | 0.401 | -36.902 | 40.654 | 8.000 |
| 2014 | 227.000 | 34.361 | -0.269 | -5.819 | 0.408 | -60.991 | 64.946 | 11.000 |
| 2015 | 225.000 | 36.889 | -0.158 | -3.397 | 0.577 | -35.604 | 39.203 | 12.000 |
| 2016 | 234.000 | 42.308 | -0.151 | -2.985 | 0.626 | -35.423 | 36.347 | 7.000 |
| 2017 | 231.000 | 36.364 | -0.169 | -3.564 | 0.558 | -39.036 | 39.834 | 10.000 |
| 2018 | 234.000 | 41.880 | -0.060 | -1.115 | 0.838 | -14.033 | 17.001 | 11.000 |
| 2019 | 232.000 | 46.121 | -0.029 | -0.553 | 0.914 | -6.785 | 12.878 | 5.000 |
| 2020 | 235.000 | 46.383 | -0.056 | -1.122 | 0.839 | -13.077 | 18.532 | 10.000 |
| 2021 | 238.000 | 49.160 | 0.016 | 0.316 | 1.052 | 3.764 | 17.825 | 7.000 |
| 2022 | 241.000 | 51.037 | -0.000 | -0.006 | 0.999 | -0.080 | 15.247 | 8.000 |
| 2023 | 236.000 | 46.186 | -0.043 | -0.781 | 0.884 | -10.148 | 14.175 | 13.000 |
| 2024 | 241.000 | 49.378 | 0.036 | 0.623 | 1.103 | 8.754 | 7.420 | 5.000 |
| 2025 | 232.000 | 49.569 | 0.035 | 0.635 | 1.110 | 8.204 | 8.600 | 7.000 |
| 2026 | 184.000 | 52.717 | -0.029 | -0.515 | 0.913 | -5.426 | 21.206 | 9.000 |

## By side

| Side | trades | win % | avg R | t | profit factor | total R | max DD (R) | worst losing streak |
|---|---|---|---|---|---|---|---|---|
| BUY | 1737.000 | 47.438 | -0.059 | -3.373 | 0.821 | -102.985 | 119.350 | 9.000 |
| SELL | 1619.000 | 40.457 | -0.101 | -4.836 | 0.748 | -164.290 | 173.248 | 12.000 |

## Exits

| Exit | count | avg R |
|---|---|---|
| SL | 862.000 | -1.000 |
| TIME | 2370.000 | 0.150 |
| TP | 124.000 | 1.938 |

## Costs and nearby variants (context only — not a parameter search)

| Variant | design 2011-18 trades | design 2011-18 avg R | design 2011-18 t | check 2019-23 trades | check 2019-23 avg R | check 2019-23 t | holdout 2024-26 trades | holdout 2024-26 avg R | holdout 2024-26 t | all trades | all avg R | all t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| as written, slip 0 | 1517.000 | -0.062 | -3.116 | 1182.000 | 0.010 | 0.421 | 657.000 | 0.035 | 1.061 | 3356.000 | -0.018 | -1.275 |
| as written, slip 1 | 1517.000 | -0.166 | -8.713 | 1182.000 | -0.022 | -0.959 | 657.000 | 0.018 | 0.529 | 3356.000 | -0.080 | -5.850 |
| as written, slip 2 | 1517.000 | -0.262 | -14.378 | 1182.000 | -0.052 | -2.282 | 657.000 | -0.001 | -0.020 | 3356.000 | -0.137 | -10.241 |
| hold to 16:00 | 1517.000 | -0.159 | -5.955 | 1182.000 | 0.026 | 0.808 | 657.000 | 0.033 | 0.760 | 3356.000 | -0.056 | -2.981 |
| no back-inside skip | 1552.000 | -0.167 | -8.832 | 1197.000 | -0.025 | -1.069 | 665.000 | 0.021 | 0.630 | 3414.000 | -0.081 | -5.959 |
| target 1.5R | 1517.000 | -0.165 | -8.754 | 1182.000 | -0.024 | -1.058 | 657.000 | 0.020 | 0.621 | 3356.000 | -0.079 | -5.945 |
| target 1R | 1517.000 | -0.172 | -9.643 | 1182.000 | -0.033 | -1.546 | 657.000 | 0.022 | 0.742 | 3356.000 | -0.085 | -6.802 |
| target 3R | 1517.000 | -0.172 | -9.035 | 1182.000 | -0.019 | -0.805 | 657.000 | 0.006 | 0.167 | 3356.000 | -0.083 | -6.075 |

## Rule 8 sizing in practice

With a $2,000 cushion the budget is $50. One MNQ ($2/pt, $1.50 fees) at the stop:

| Year | median stop distance (pts) | median range (pts) | median spread (pts) | 1 MNQ at stop, median $ | % signals 1 MNQ <= $50 | CFD lots for $50, median |
|---|---|---|---|---|---|---|
| 2011 | 16.49 | 14.28 | 0.00 | 36.47 | 100.00 | 2.88 |
| 2012 | 11.75 | 9.15 | 0.00 | 27.00 | 95.81 | 3.92 |
| 2013 | 13.19 | 9.22 | 2.13 | 29.88 | 97.96 | 3.52 |
| 2014 | 17.18 | 12.84 | 2.15 | 37.87 | 81.06 | 2.75 |
| 2015 | 22.26 | 17.50 | 1.08 | 48.01 | 55.56 | 2.15 |
| 2016 | 19.05 | 14.73 | 1.02 | 41.59 | 65.81 | 2.49 |
| 2017 | 18.34 | 13.90 | 1.06 | 40.17 | 74.03 | 2.59 |
| 2018 | 39.71 | 31.85 | 1.07 | 82.92 | 10.26 | 1.23 |
| 2019 | 32.18 | 26.25 | 0.98 | 67.87 | 19.40 | 1.51 |
| 2020 | 70.75 | 56.59 | 1.40 | 145.00 | 0.85 | 0.70 |
| 2021 | 77.13 | 61.13 | 1.30 | 157.76 | 0.00 | 0.64 |
| 2022 | 116.64 | 97.72 | 1.30 | 236.78 | 0.00 | 0.43 |
| 2023 | 74.30 | 61.34 | 1.39 | 152.10 | 0.00 | 0.66 |
| 2024 | 83.05 | 67.32 | 1.44 | 169.60 | 0.00 | 0.59 |
| 2025 | 110.00 | 90.59 | 1.39 | 223.49 | 0.00 | 0.45 |
| 2026 | 159.56 | 133.27 | 1.10 | 322.61 | 0.00 | 0.31 |

## Prop challenge simulation (rule 8 sizing)

A challenge is started on every signal day and played forward on the trades above (closed P/L only, no time limit). Only start days with at least N days of data after them count towards the N-day columns.

| Account | challenges | pass <= 30d % | fail <= 30d % | pass <= 90d % | fail <= 90d % | pass <= 365d % | fail <= 365d % | median days to pass (when passed) | signals skipped: 1 contract > budget % |
|---|---|---|---|---|---|---|---|---|---|
| Futures 50K (MNQ) | 3356.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 97.3 |
| CFD 100K | 3356.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1689.0 | 8.4 |
