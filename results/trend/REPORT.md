# Daily trend following — 28 FX pairs, 2010–2026

7 pre-declared portfolio tests (see run_trend.py). Equal-risk portfolio, 10% a year volatility target if pairs were uncorrelated. Costs: half spread + $7/lot + 0.2 pip per unit traded; carry at policy / interbank rates with a 1% a year markup. Survival rule fixed before running: design (2010–2017) t ≥ 2 AND check (2018–2023) return > 0. Holdout (2024–2026) only for survivors.

**Survivors: 0 of 7.**

| setup | design ann ret % | design sharpe | design t | design ann vol % | check ann ret % | check sharpe | check t | survives |
|---|---|---|---|---|---|---|---|---|
| T1 tsmom 63d monthly | -4.28 | -0.17 | -0.49 | 25.27 | -18.19 | -0.75 | -1.87 | False |
| T1 tsmom 126d monthly | -3.94 | -0.16 | -0.46 | 24.47 | -18.19 | -0.79 | -1.98 | False |
| T1 tsmom 252d monthly | -6.06 | -0.26 | -0.75 | 23.35 | -10.50 | -0.44 | -1.10 | False |
| T2 ma-cross 50/200 | -7.64 | -0.30 | -0.86 | 25.55 | -17.79 | -0.74 | -1.85 | False |
| T2 ma-cross 20/100 | -6.28 | -0.25 | -0.72 | 25.07 | -23.51 | -0.96 | -2.39 | False |
| T3 donchian 20/10 | -7.36 | -0.35 | -1.02 | 20.76 | -10.84 | -0.49 | -1.22 | False |
| T3 donchian 55/20 | -6.40 | -0.32 | -0.91 | 20.27 | -13.10 | -0.63 | -1.58 | False |

## Where the return comes from (% a year): price move, trading costs, interest carry, broker swap markup; and the result with no markup (futures / forwards-like financing)

| setup | design gross %/yr | design cost %/yr | design carry %/yr | design markup %/yr | design no-markup ann ret % | design no-markup t | check gross %/yr | check cost %/yr | check carry %/yr | check markup %/yr | check no-markup ann ret % | check no-markup t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 tsmom 63d monthly | 1.70 | 0.77 | 0.84 | 6.05 | 1.76 | 0.20 | -10.16 | 0.81 | -0.16 | 7.06 | -11.13 | -1.15 |
| T1 tsmom 126d monthly | 1.77 | 0.61 | 0.94 | 6.05 | 2.11 | 0.25 | -10.09 | 0.63 | -0.42 | 7.06 | -11.13 | -1.21 |
| T1 tsmom 252d monthly | -0.80 | 0.51 | 1.28 | 6.05 | -0.02 | -0.00 | -2.70 | 0.48 | -0.26 | 7.06 | -3.44 | -0.36 |
| T2 ma-cross 50/200 | -1.42 | 0.35 | 0.26 | 6.13 | -1.51 | -0.17 | -10.30 | 0.36 | -0.30 | 6.83 | -10.96 | -1.14 |
| T2 ma-cross 20/100 | 0.64 | 0.70 | -0.23 | 5.99 | -0.29 | -0.03 | -15.82 | 0.79 | -0.00 | 6.90 | -16.61 | -1.69 |
| T3 donchian 20/10 | -0.62 | 2.34 | -0.03 | 4.36 | -2.99 | -0.41 | -3.17 | 2.35 | -0.18 | 5.14 | -5.70 | -0.64 |
| T3 donchian 55/20 | -1.67 | 1.00 | -0.07 | 3.66 | -2.74 | -0.39 | -7.52 | 1.04 | -0.32 | 4.22 | -8.88 | -1.07 |

## Breadth: per-pair Sharpe of the best design-period setup (T1 tsmom 126d monthly)

| pair | design sharpe | check sharpe |
|---|---|---|
| EURGBP | 0.44 | -0.56 |
| GBPJPY | 0.36 | -0.40 |
| EURCHF | 0.31 | 0.06 |
| EURCAD | 0.24 | 0.23 |
| EURUSD | 0.18 | 0.23 |
| GBPUSD | 0.15 | -0.11 |
| USDJPY | 0.14 | 0.35 |
| CHFJPY | 0.12 | 0.24 |
| GBPCHF | 0.10 | -0.32 |
| EURAUD | 0.08 | -0.62 |
| EURJPY | -0.00 | -0.24 |
| USDCAD | -0.03 | -0.19 |
| GBPAUD | -0.06 | -0.25 |
| AUDJPY | -0.11 | -0.56 |
| GBPCAD | -0.15 | -0.22 |
| USDCHF | -0.18 | -1.04 |
| NZDCHF | -0.20 | -0.21 |
| EURNZD | -0.20 | -0.58 |
| AUDUSD | -0.22 | -0.44 |
| AUDCHF | -0.25 | -0.06 |
| GBPNZD | -0.34 | -1.06 |
| AUDCAD | -0.38 | -0.30 |
| CADCHF | -0.44 | -0.07 |
| AUDNZD | -0.46 | -0.93 |
| CADJPY | -0.47 | -0.02 |
| NZDUSD | -0.54 | -0.65 |
| NZDCAD | -0.64 | -0.49 |
| NZDJPY | -0.72 | -0.91 |

## Data coverage (Dukascopy daily candles)

Dukascopy publishes a year's daily-candle file only after the year ends, so the data stop at 2025-12-31 and the holdout is 2024–2025.

|  | first | last | days |
|---|---|---|---|
| EURUSD | 2008-01-01 | 2025-12-31 | 4695 |
| GBPUSD | 2008-01-01 | 2025-12-31 | 4695 |
| USDJPY | 2008-01-01 | 2025-12-31 | 4695 |
| USDCHF | 2008-01-01 | 2025-12-31 | 4695 |
| AUDUSD | 2008-01-02 | 2025-12-31 | 4693 |
| USDCAD | 2008-01-01 | 2025-12-31 | 4695 |
| NZDUSD | 2008-01-01 | 2025-12-31 | 4695 |
| EURGBP | 2008-01-01 | 2025-12-31 | 4693 |
| EURJPY | 2008-01-01 | 2025-12-31 | 4695 |
| GBPJPY | 2008-01-01 | 2025-12-31 | 4695 |
| EURCHF | 2008-01-01 | 2025-12-31 | 4693 |
| EURAUD | 2008-01-01 | 2025-12-31 | 4693 |
| EURCAD | 2008-01-01 | 2025-12-31 | 4693 |
| EURNZD | 2008-01-01 | 2025-12-31 | 4693 |
| GBPCHF | 2008-01-01 | 2025-12-31 | 4693 |
| GBPAUD | 2008-01-01 | 2025-12-31 | 4693 |
| GBPCAD | 2008-01-01 | 2025-12-31 | 4693 |
| GBPNZD | 2008-01-01 | 2025-12-31 | 4693 |
| AUDJPY | 2008-01-01 | 2025-12-31 | 4695 |
| AUDNZD | 2008-01-01 | 2025-12-31 | 4689 |
| AUDCAD | 2008-01-01 | 2025-12-31 | 4693 |
| AUDCHF | 2008-01-01 | 2025-12-31 | 4693 |
| CADJPY | 2008-01-01 | 2025-12-31 | 4693 |
| CHFJPY | 2008-01-01 | 2025-12-31 | 4693 |
| NZDJPY | 2008-01-01 | 2025-12-31 | 4693 |
| NZDCAD | 2008-01-01 | 2025-12-31 | 4693 |
| NZDCHF | 2008-01-01 | 2025-12-31 | 4693 |
| CADCHF | 2008-01-01 | 2025-12-31 | 4693 |
