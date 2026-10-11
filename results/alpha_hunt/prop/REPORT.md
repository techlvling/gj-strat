# Alpha hunt -> prop: verified edges added to the Alpha Swing and Blueberry baskets

Rules, risk levels and acceptance are in the docstring of `run_alpha_prop.py` (fixed before running). All results after costs.

## Edges added

- `index_meanrev`: Nasdaq 100 MR6: RSI2 < 5 & C > SMA200, exit first close > SMA5 (cap 10), SL 2 x ATR20

Only one edge was verified, so "all edges together" is the same mix as the edge alone.

## Summary (written by hand after the run)

- **Edge:** the only verified edge is Nasdaq 100 MR6. It has 61 trades (2014-10 to 2026-08), 0.35 a month, 70% wins and avg R +0.235 after costs.
  - Its trades from 2014-17 are in the period the edge was found in.
  - About half its trades (31 of 61) are open at the same time as a 3% vol-gotobi or M-3 trade.
- **Alpha Swing: no change to the basket under the pre-declared rule.**
  - Normal risk: MR6 is accepted at 1% and at 2%.
    - At 2%, months per funded account fall from 7.29 to 6.68 (starts 2011-25) and from 5.79 to 5.56 (starts 2018-25).
    - At 2%, pass eventually % rises from 59.1 to 63.5 and from 74.0 to 75.9.
    - At 1%, the gain is small: 7.29 to 7.07 and 5.79 to 5.76.
    - At 0.5% it is not accepted: 5.83 vs 5.79 months for starts 2018-25.
  - Boost x1.5 (the speed-up actually in use): no level is accepted.
    - The best level is 2%. Months per funded account fall from 4.86 to 4.74 and from 4.34 to 4.20.
    - But pass eventually % slips from 46.24 to 46.18 for starts 2011-25.
    - At 0.5% and 1%, both measures get worse.
    - With the boost, fails by the daily limit rise from 19.7% to 22.0% (2011-25) and from 12.3% to 14.7% (2018-25). The cause is MR6 losses landing on the same day as boosted 3% legs, which are capped at 4%.
  - The decision rule needs a level accepted under both risk rules, so MR6 is not added.
- **Blueberry Instant Elite: accepted at every level (0.5%, 1%, 1.5%). Decision: add at 1.5%.**
  - Starts 2018-24 (outside the period the edge was found in):
    - Avg paid in 24 months goes from $729 to $754 (0.5%), $776 (1%) and $798 (1.5%).
    - Accounts lost within 24 months go from 2.3% to 1.8-1.9%.
  - Starts 2011-24 show a much bigger change: lost falls from 9.0% to 1.4-2.4%. This is not evidence for the edge.
    - Almost all of it comes from accounts started in 2013-14, which survive their 2014-15 drawdown thanks to MR6 trades from its design period (by-year table at the end).
    - The path effect also cuts the other way: accounts started in 2017 lose 31.7% at 1.5% vs 0% for the basket.
  - By start year, 2018-24 is mixed. MR6 lowers the payout for 2018-19 starts and raises it for 2020-24 starts.
  - The honest gain is about +$47 to +$69 per account over 24 months (+6% to +9%). It rests on about 4 MR6 trades a year.
- **Caveat:** both simulators book the daily loss when trades close. A multi-day Nasdaq position's open loss is not marked to market, so the daily-limit risk of MR6 is somewhat understated.

## Decision (pre-declared rule)

| addition | Alpha accepted (normal risk) | Alpha accepted (boost x1.5) | Alpha decision | Blueberry accepted | Blueberry decision |
|---|---|---|---|---|---|
| Nasdaq MR6 | 1%, 2% | none | no change | 0.5%, 1%, 1.5% | add at 1.5% |


## The edge on its own (on the USDJPY minute grid)

trades/month from the edge report (per month with Nasdaq data). Overlap columns: trades open at the same time as a vol-gotobi or M-3 USDJPY trade, and trades exiting on the same NY day as one of them.

| edge | trades | trades/month | win % | avg win / avg loss | avg R | t | design n | design avg R | design t | check n | check avg R | check t | holdout n | holdout avg R | holdout t | last3y n | last3y avg R | open with a 3% basket trade | exit on a 3% basket trade's exit day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq MR6 | 61.000 | 0.345 | 70.492 | 0.883 | 0.235 | 2.457 | 20.000 | 0.433 | 2.279 | 29.000 | 0.073 | 0.527 | 12.000 | 0.298 | 2.060 | 13.000 | 0.302 | 31.000 | 14.000 |


## A. Alpha Swing $10k (P1 +10%, P2 +5%, 10% static, 5% daily, >= 3 days)

Basket = vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3% (run_m3_addon.build_legs). New edge at 0.5%, 1%, 2%. Accepted if months per funded account is lower AND pass eventually % is not lower than the basket, in both windows (per risk rule). Δ = mix minus basket in the same rule and window.

| mix | risk rule | window | challenges | pass ≤1 month % | pass ≤3 months % | pass ≤6 months % | fail ≤6 months % | fails by daily limit % | pass eventually % | median months to pass | months per funded account | Δ months per funded | Δ pass eventually | max DD % | accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| basket (vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%) | normal risk | starts 2011-2025 | 2537 | 7.80 | 28.03 | 44.38 | 31.06 | 2.68 | 59.12 | 3.26 | 7.29 | 0.00 | 0.00 | 26.44 | None |
| + Nasdaq MR6 0.5% | normal risk | starts 2011-2025 | 2553 | 7.79 | 28.24 | 44.97 | 31.18 | 2.66 | 59.89 | 3.29 | 7.18 | -0.11 | 0.77 | 26.11 | False |
| + Nasdaq MR6 1% | normal risk | starts 2011-2025 | 2553 | 7.83 | 28.79 | 45.59 | 30.63 | 2.66 | 60.52 | 3.26 | 7.07 | -0.22 | 1.39 | 25.98 | True |
| + Nasdaq MR6 2% | normal risk | starts 2011-2025 | 2553 | 7.95 | 29.73 | 47.67 | 28.59 | 2.66 | 63.49 | 3.29 | 6.68 | -0.61 | 4.37 | 25.74 | True |
| basket (vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%) | normal risk | starts 2018-2025 | 1291 | 6.89 | 32.92 | 58.09 | 19.36 | 0.00 | 73.97 | 3.59 | 5.79 | 0.00 | 0.00 | 24.84 | None |
| + Nasdaq MR6 0.5% | normal risk | starts 2018-2025 | 1303 | 6.91 | 32.85 | 57.94 | 19.42 | 0.00 | 73.91 | 3.59 | 5.83 | 0.04 | -0.07 | 24.54 | False |
| + Nasdaq MR6 1% | normal risk | starts 2018-2025 | 1303 | 6.98 | 33.31 | 58.10 | 19.19 | 0.00 | 74.44 | 3.52 | 5.76 | -0.03 | 0.47 | 24.24 | True |
| + Nasdaq MR6 2% | normal risk | starts 2018-2025 | 1303 | 7.21 | 33.77 | 58.79 | 18.42 | 0.00 | 75.90 | 3.59 | 5.56 | -0.23 | 1.93 | 23.65 | True |
| basket (vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%) | boost x1.5 | starts 2011-2025 | 2537 | 12.22 | 31.30 | 43.40 | 50.93 | 19.71 | 46.24 | 1.97 | 4.86 | 0.00 | 0.00 | 26.44 | None |
| + Nasdaq MR6 0.5% | boost x1.5 | starts 2011-2025 | 2553 | 12.14 | 31.22 | 43.05 | 51.27 | 20.37 | 45.52 | 1.94 | 4.88 | 0.02 | -0.72 | 26.11 | False |
| + Nasdaq MR6 1% | boost x1.5 | starts 2011-2025 | 2553 | 12.30 | 31.45 | 42.62 | 51.43 | 21.50 | 44.81 | 1.88 | 5.00 | 0.14 | -1.43 | 25.98 | False |
| + Nasdaq MR6 2% | boost x1.5 | starts 2011-2025 | 2553 | 12.30 | 31.81 | 43.75 | 51.51 | 22.01 | 46.18 | 1.84 | 4.74 | -0.11 | -0.05 | 25.74 | False |
| basket (vol-box 0.25% + vol-gotobi 3% + fade 0.5% + M-3 3%) | boost x1.5 | starts 2018-2025 | 1291 | 11.85 | 34.55 | 51.90 | 42.68 | 12.32 | 55.23 | 2.30 | 4.34 | 0.00 | 0.00 | 24.84 | None |
| + Nasdaq MR6 0.5% | boost x1.5 | starts 2018-2025 | 1303 | 11.82 | 34.46 | 51.88 | 42.59 | 12.82 | 54.49 | 2.17 | 4.35 | 0.00 | -0.74 | 24.54 | False |
| + Nasdaq MR6 1% | boost x1.5 | starts 2018-2025 | 1303 | 12.05 | 34.38 | 50.42 | 43.44 | 14.43 | 52.65 | 2.11 | 4.56 | 0.22 | -2.58 | 24.24 | False |
| + Nasdaq MR6 2% | boost x1.5 | starts 2018-2025 | 1303 | 12.05 | 34.61 | 52.57 | 43.28 | 14.66 | 55.56 | 2.11 | 4.20 | -0.14 | 0.34 | 23.65 | False |


## B. Blueberry Instant Elite $2.5k (10% cushion kept, 24-month horizon)

Basket = vol-box 0.25% + vol-gotobi 1.5% + M-3 1%. New edge at 0.5%, 1%, 1.5%. Accepted if avg paid in 24 months is higher AND account lost within 24 months % is not higher, in both windows.

| mix | window | got ≥1 payout % | days to first payout (median) | avg paid in 12 months $ | avg paid in 24 months $ | avg per month $ | account lost within 24 months % | Δ avg paid 24m $ | Δ lost % | accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| basket (vol-box 0.25% + vol-gotobi 1.5% + M-3 1%) | starts 2011-2024 | 77.3 | 224.0 | 279.2 | 571.3 | 23.8 | 9.0 | 0.0 | 0.0 | None |
| + Nasdaq MR6 0.5% | starts 2011-2024 | 78.6 | 224.0 | 279.8 | 589.2 | 24.5 | 7.7 | 17.8 | -1.4 | True |
| + Nasdaq MR6 1% | starts 2011-2024 | 83.2 | 238.0 | 283.1 | 631.8 | 26.3 | 1.4 | 60.5 | -7.6 | True |
| + Nasdaq MR6 1.5% | starts 2011-2024 | 85.3 | 238.0 | 288.3 | 651.2 | 27.1 | 2.4 | 79.9 | -6.7 | True |
| basket (vol-box 0.25% + vol-gotobi 1.5% + M-3 1%) | starts 2018-2024 | 89.3 | 224.0 | 344.0 | 729.2 | 30.4 | 2.3 | 0.0 | 0.0 | None |
| + Nasdaq MR6 0.5% | starts 2018-2024 | 90.8 | 231.0 | 347.2 | 754.0 | 31.4 | 1.8 | 24.8 | -0.5 | True |
| + Nasdaq MR6 1% | starts 2018-2024 | 92.3 | 238.0 | 354.1 | 775.7 | 32.3 | 1.9 | 46.5 | -0.4 | True |
| + Nasdaq MR6 1.5% | starts 2018-2024 | 93.0 | 238.0 | 361.3 | 797.9 | 33.2 | 1.9 | 68.7 | -0.4 | True |


## Post-hoc diagnostic: Blueberry by account start year

Added after the main run to see where the Blueberry gain comes from; not used for any decision. Accounts started in each calendar year (2024: up to 2024-10-07), 24-month horizon, 10% cushion. paid $ = avg paid in 24 months; lost % = account lost within 24 months.

| start year | paid $: basket | paid $: Nasdaq MR6 1% | paid $: Nasdaq MR6 1.5% | lost %: basket | lost %: Nasdaq MR6 1% | lost %: Nasdaq MR6 1.5% |
|---|---|---|---|---|---|---|
| 2011 | 109.6 | 109.6 | 109.6 | 0.0 | 0.0 | 0.0 |
| 2012 | 576.3 | 577.2 | 578.6 | 3.6 | 3.6 | 3.6 |
| 2013 | 395.6 | 411.0 | 439.9 | 35.9 | 1.8 | 0.0 |
| 2014 | 127.3 | 765.7 | 815.7 | 84.4 | 1.3 | 0.0 |
| 2015 | 807.1 | 831.7 | 840.9 | 0.7 | 0.0 | 0.0 |
| 2016 | 396.4 | 422.0 | 439.7 | 0.0 | 0.0 | 0.0 |
| 2017 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 31.7 |
| 2018 | 200.5 | 174.0 | 158.8 | 0.0 | 0.0 | 0.0 |
| 2019 | 539.0 | 489.2 | 474.6 | 0.0 | 0.0 | 0.0 |
| 2020 | 318.2 | 440.1 | 503.2 | 0.0 | 0.7 | 0.7 |
| 2021 | 1390.7 | 1461.9 | 1501.2 | 0.0 | 0.0 | 0.0 |
| 2022 | 848.6 | 890.5 | 909.1 | 6.4 | 6.4 | 6.4 |
| 2023 | 745.8 | 809.4 | 838.8 | 0.0 | 0.0 | 0.0 |
| 2024 | 759.5 | 767.4 | 769.0 | 3.5 | 0.0 | 0.0 |
