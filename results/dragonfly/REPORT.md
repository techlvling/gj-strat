# Dragonfly Intercept - Phase 1 report

Plain-English verdict: `VERDICT.md` (written after reviewing these tables). Unit tests: `unit_tests.txt`.

Data: Dukascopy BID+ASK (1m aggregated to 15m and 1H, UTC), 2020-01-01 22:00 -> 2026-10-08 00:00. In-sample 2020-01-01 -> 2024-01-23 13:30 (60%), out-of-sample 2024-01-23 13:30 -> 2026-10-08 (40%). Trades belong to the segment of their signal time. Each segment starts at $10,000 per pair, 1% risk compounding. Commission $0.0/lot, swap long/short 0.0/0.0 USD/lot/night. Nominal spread (buffer + 3x rule): GBPJPY 2.5 pips, EURUSD 0.8 pips; fills use real bid/ask. Random benchmark: 1000 seeds. Code commit f614f49.

**Combos tested: 6** (R 0.382/0.5/0.618 x T1/T2), identical parameters on both pairs. No other parameter was varied.

## 1. In-sample ranking (the only basis for selection)

Ranked by the average of the two pairs' in-sample expectancy (avg R per trade); a combo needs >= 100 in-sample trades on BOTH pairs to be eligible.

| combo | rank | avg_expectancy_R | gbpjpy_R | eurusd_R | min_trades | eligible |
|---|---|---|---|---|---|---|
| R0.382_T2 | 1 | -0.042 | -0.060 | -0.025 | 2390 | True |
| R0.5_T2 | 2 | -0.071 | -0.111 | -0.032 | 2279 | True |
| R0.382_T1 | 3 | -0.072 | -0.100 | -0.044 | 3370 | True |
| R0.5_T1 | 4 | -0.086 | -0.124 | -0.048 | 2761 | True |
| R0.618_T2 | 5 | -0.102 | -0.165 | -0.039 | 2057 | True |
| R0.618_T1 | 6 | -0.132 | -0.188 | -0.077 | 2258 | True |

Top 3 taken to out-of-sample: **R0.382_T2, R0.5_T2, R0.382_T1**

## 2. In-sample, all 6 combos

avg R = expectancy per trade in R (win% x avg win + loss% x avg loss). Max DD is on closed-trade equity. Losing streak counts consecutive R < 0 trades (a break-even exit ends a streak).

| combo / pair | trades | fill_rate_pct | win_rate | avg_R | avg_win_R | avg_loss_R | profit_factor | max_dd_pct | longest_losing_streak | net_return_pct | pct_held_over_rollover |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R0.382_T1 GBPJPY | 3370.00 | 77.94 | 53.65 | -0.10 | 0.61 | -0.95 | 0.76 | 96.98 | 8.00 | -96.95 | 9.85 |
| R0.382_T1 EURUSD | 3474.00 | 78.58 | 54.58 | -0.04 | 0.64 | -0.90 | 0.89 | 84.19 | 7.00 | -80.35 | 10.39 |
| R0.382_T2 GBPJPY | 2390.00 | 76.75 | 34.52 | -0.06 | 1.33 | -0.95 | 0.88 | 81.58 | 12.00 | -79.00 | 18.70 |
| R0.382_T2 EURUSD | 2466.00 | 77.13 | 32.52 | -0.02 | 1.38 | -0.91 | 0.95 | 68.73 | 9.00 | -52.42 | 18.45 |
| R0.5_T1 GBPJPY | 2761.00 | 67.24 | 45.02 | -0.12 | 0.91 | -0.99 | 0.77 | 97.13 | 13.00 | -97.11 | 9.67 |
| R0.5_T1 EURUSD | 2856.00 | 68.54 | 46.22 | -0.05 | 0.96 | -0.95 | 0.90 | 82.81 | 8.00 | -77.76 | 9.84 |
| R0.5_T2 GBPJPY | 2279.00 | 65.66 | 25.36 | -0.11 | 1.78 | -0.98 | 0.80 | 93.35 | 12.00 | -93.19 | 14.26 |
| R0.5_T2 EURUSD | 2356.00 | 67.33 | 25.17 | -0.03 | 1.87 | -0.95 | 0.94 | 75.47 | 8.00 | -59.87 | 13.92 |
| R0.618_T1 GBPJPY | 2258.00 | 55.81 | 29.58 | -0.19 | 1.37 | -1.00 | 0.68 | 98.78 | 14.00 | -98.76 | 7.04 |
| R0.618_T1 EURUSD | 2383.00 | 57.74 | 31.22 | -0.08 | 1.47 | -0.97 | 0.86 | 90.88 | 14.00 | -86.06 | 7.51 |
| R0.618_T2 GBPJPY | 2057.00 | 55.31 | 17.31 | -0.16 | 2.47 | -1.00 | 0.72 | 97.26 | 13.00 | -97.15 | 9.53 |
| R0.618_T2 EURUSD | 2116.00 | 56.71 | 18.53 | -0.04 | 2.63 | -0.96 | 0.93 | 82.69 | 13.00 | -64.01 | 10.35 |

### Benchmarks, in-sample

Chase = market entry at the completion close, same stop/target/BE/risk. Random = same trade count and buy/sell mix, random entry bars while the 1H filter points that way, stop = the strategy's median stop distance, target = its median planned target multiple. 'real pct' = percentile of the real result in the random distribution.

| combo / pair | dragonfly trades | dragonfly avg R | dragonfly return % | chase trades | chase avg R | chase win % | chase PF | chase maxDD % | chase return % | random avg R p5/p50/p95 | real pct (avg R) | random return % p5/p50/p95 | real pct (return) | rand stop pips / tgt x |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0.382_T1 GBPJPY | 3370 | -0.100 | -96.947 | 5402 | -0.094 | 67.456 | 0.705 | 99.448 | -99.448 | -0.126 / -0.105 / -0.081 | 62.300 | -98.7 / -97.4 / -94.2 | 62.400 | 26.9 / 0.56 |
| R0.382_T1 EURUSD | 3474 | -0.044 | -80.346 | 5522 | -0.046 | 66.932 | 0.849 | 95.133 | -93.045 | -0.058 / -0.036 / -0.015 | 27.700 | -87.9 / -73.8 / -46.0 | 27.900 | 13.8 / 0.58 |
| R0.382_T2 GBPJPY | 2390 | -0.060 | -79.002 | 2550 | -0.048 | 47.255 | 0.901 | 76.478 | -74.082 | -0.127 / -0.093 / -0.059 | 94.600 | -95.8 / -90.6 / -78.9 | 94.800 | 28.2 / 1.30 |
| R0.382_T2 EURUSD | 2466 | -0.025 | -52.418 | 2457 | -0.033 | 43.915 | 0.930 | 73.620 | -60.956 | -0.071 / -0.033 / +0.001 | 66.400 | -84.9 / -61.6 / -12.6 | 67.200 | 14.6 / 1.34 |
| R0.5_T1 GBPJPY | 2761 | -0.124 | -97.106 | 5402 | -0.094 | 67.456 | 0.705 | 99.448 | -99.448 | -0.168 / -0.140 / -0.111 | 81.000 | -99.2 / -98.1 / -95.9 | 81.200 | 21.7 / 0.88 |
| R0.5_T1 EURUSD | 2856 | -0.048 | -77.761 | 5522 | -0.046 | 66.932 | 0.849 | 95.133 | -93.045 | -0.078 / -0.047 / -0.017 | 48.000 | -90.5 / -77.3 / -47.0 | 48.400 | 10.9 / 0.92 |
| R0.5_T2 GBPJPY | 2279 | -0.111 | -93.188 | 2550 | -0.048 | 47.255 | 0.901 | 76.478 | -74.082 | -0.168 / -0.129 / -0.086 | 74.700 | -98.2 / -95.4 / -87.9 | 75.400 | 22.2 / 1.78 |
| R0.5_T2 EURUSD | 2356 | -0.032 | -59.869 | 2457 | -0.033 | 43.915 | 0.930 | 73.620 | -60.956 | -0.086 / -0.046 / -0.003 | 68.300 | -88.8 / -71.1 / -20.9 | 69.000 | 11.1 / 1.85 |
| R0.618_T1 GBPJPY | 2258 | -0.188 | -98.756 | 5402 | -0.094 | 67.456 | 0.705 | 99.448 | -99.448 | -0.227 / -0.191 / -0.153 | 56.200 | -99.5 / -98.8 / -97.3 | 56.600 | 16.8 / 1.38 |
| R0.618_T1 EURUSD | 2383 | -0.077 | -86.057 | 5522 | -0.046 | 66.932 | 0.849 | 95.133 | -93.045 | -0.115 / -0.078 / -0.040 | 51.600 | -94.5 / -86.5 / -67.1 | 52.100 | 8.1 / 1.45 |
| R0.618_T2 GBPJPY | 2057 | -0.165 | -97.148 | 2550 | -0.048 | 47.255 | 0.901 | 76.478 | -74.082 | -0.219 / -0.171 / -0.123 | 58.200 | -99.1 / -97.5 / -93.3 | 59.000 | 16.9 / 2.49 |
| R0.618_T2 EURUSD | 2116 | -0.039 | -64.007 | 2457 | -0.033 | 43.915 | 0.930 | 73.620 | -60.956 | -0.124 / -0.080 / -0.030 | 90.700 | -94.1 / -84.7 / -57.0 | 91.000 | 8.2 / 2.62 |

### Signal flow, in-sample

| combo / pair | signals | skip_pending | skip_position | skip_small_stop | orders_placed | filled | fill_rate_pct | cancel_786_at_signal | cancel_786 | cancel_trend | cancel_expired | open_at_end | unfilled_orders |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0.382_T1 GBPJPY | 6904.0 | 1555.0 | 1025.0 | 0.0 | 4324.0 | 3370.0 | 77.9 | 171.0 | 9.0 | 16.0 | 758.0 | 0.0 | 954.0 |
| R0.382_T1 EURUSD | 6922.0 | 1379.0 | 1122.0 | 0.0 | 4421.0 | 3474.0 | 78.6 | 263.0 | 1.0 | 15.0 | 668.0 | 0.0 | 947.0 |
| R0.382_T2 GBPJPY | 6904.0 | 1146.0 | 2644.0 | 0.0 | 3114.0 | 2390.0 | 76.8 | 131.0 | 4.0 | 13.0 | 576.0 | 0.0 | 724.0 |
| R0.382_T2 EURUSD | 6922.0 | 1037.0 | 2688.0 | 0.0 | 3197.0 | 2466.0 | 77.1 | 201.0 | 1.0 | 15.0 | 514.0 | 0.0 | 731.0 |
| R0.5_T1 GBPJPY | 6904.0 | 1990.0 | 805.0 | 3.0 | 4106.0 | 2761.0 | 67.2 | 169.0 | 16.0 | 30.0 | 1130.0 | 0.0 | 1345.0 |
| R0.5_T1 EURUSD | 6922.0 | 1839.0 | 916.0 | 0.0 | 4167.0 | 2856.0 | 68.5 | 251.0 | 1.0 | 26.0 | 1033.0 | 0.0 | 1311.0 |
| R0.5_T2 GBPJPY | 6904.0 | 1684.0 | 1746.0 | 3.0 | 3471.0 | 2279.0 | 65.7 | 153.0 | 13.0 | 30.0 | 996.0 | 0.0 | 1192.0 |
| R0.5_T2 EURUSD | 6922.0 | 1524.0 | 1899.0 | 0.0 | 3499.0 | 2356.0 | 67.3 | 239.0 | 1.0 | 25.0 | 878.0 | 0.0 | 1143.0 |
| R0.618_T1 GBPJPY | 6904.0 | 2339.0 | 486.0 | 33.0 | 4046.0 | 2258.0 | 55.8 | 168.0 | 26.0 | 52.0 | 1542.0 | 0.0 | 1788.0 |
| R0.618_T1 EURUSD | 6922.0 | 2257.0 | 538.0 | 0.0 | 4127.0 | 2383.0 | 57.7 | 263.0 | 3.0 | 42.0 | 1436.0 | 0.0 | 1744.0 |
| R0.618_T2 GBPJPY | 6904.0 | 2152.0 | 1001.0 | 32.0 | 3719.0 | 2057.0 | 55.3 | 164.0 | 25.0 | 50.0 | 1423.0 | 0.0 | 1662.0 |
| R0.618_T2 EURUSD | 6922.0 | 2041.0 | 1150.0 | 0.0 | 3731.0 | 2116.0 | 56.7 | 251.0 | 3.0 | 41.0 | 1320.0 | 0.0 | 1615.0 |

## 3. Plateau check (in-sample)

Neighbours = adjacent retracement with the same target, and the same retracement with the other target. 'likely noise' = the pick is positive but its neighbours average <= 0 or less than half of it.

| pick | pick_R | neighbours | neighbour_mean_R | likely_noise |
|---|---|---|---|---|
| R0.382_T2 | -0.042 | R0.5_T2 -0.071, R0.382_T1 -0.072 | -0.072 | False |
| R0.5_T2 | -0.071 | R0.382_T2 -0.042, R0.618_T2 -0.102, R0.5_T1 -0.086 | -0.077 | False |
| R0.382_T1 | -0.072 | R0.5_T1 -0.086, R0.382_T2 -0.042 | -0.064 | False |

## 4. Out-of-sample, top 3 only

| combo / pair | trades | fill_rate_pct | win_rate | avg_R | avg_win_R | avg_loss_R | profit_factor | max_dd_pct | longest_losing_streak | net_return_pct | pct_held_over_rollover |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R0.382_T2 GBPJPY | 1617.00 | 77.04 | 30.12 | -0.15 | 1.35 | -0.95 | 0.73 | 91.78 | 11.00 | -91.78 | 17.87 |
| R0.382_T2 EURUSD | 1635.00 | 78.45 | 32.91 | -0.03 | 1.38 | -0.92 | 0.93 | 52.50 | 9.00 | -47.02 | 18.96 |
| R0.5_T2 GBPJPY | 1537.00 | 66.68 | 22.12 | -0.19 | 1.84 | -0.98 | 0.68 | 95.35 | 12.00 | -95.21 | 13.27 |
| R0.5_T2 EURUSD | 1580.00 | 67.78 | 24.24 | -0.08 | 1.86 | -0.95 | 0.85 | 76.81 | 9.00 | -74.69 | 14.05 |
| R0.382_T1 GBPJPY | 2244.00 | 79.04 | 50.62 | -0.15 | 0.62 | -0.95 | 0.68 | 96.63 | 11.00 | -96.61 | 9.85 |
| R0.382_T1 EURUSD | 2290.00 | 79.60 | 54.02 | -0.05 | 0.64 | -0.91 | 0.86 | 74.18 | 9.00 | -73.33 | 10.70 |

### Benchmarks, out-of-sample

| combo / pair | dragonfly trades | dragonfly avg R | dragonfly return % | chase trades | chase avg R | chase win % | chase PF | chase maxDD % | chase return % | random avg R p5/p50/p95 | real pct (avg R) | random return % p5/p50/p95 | real pct (return) | rand stop pips / tgt x |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0.382_T2 GBPJPY | 1617 | -0.149 | -91.784 | 1748 | -0.146 | 41.819 | 0.722 | 92.940 | -92.940 | -0.209 / -0.167 / -0.122 | 74.100 | -96.9 / -93.9 / -87.4 | 74.400 | 29.4 / 1.31 |
| R0.382_T2 EURUSD | 1635 | -0.033 | -47.022 | 1615 | -0.045 | 43.467 | 0.907 | 60.550 | -55.785 | -0.113 / -0.069 / -0.025 | 91.500 | -85.7 / -70.6 / -39.3 | 91.800 | 12.3 / 1.33 |
| R0.5_T2 GBPJPY | 1537 | -0.191 | -95.211 | 1748 | -0.146 | 41.819 | 0.722 | 92.940 | -92.940 | -0.267 / -0.219 / -0.172 | 83.200 | -98.5 / -96.9 / -93.6 | 83.400 | 23.5 / 1.79 |
| R0.5_T2 EURUSD | 1580 | -0.080 | -74.685 | 1615 | -0.045 | 43.467 | 0.907 | 60.550 | -55.785 | -0.134 / -0.086 / -0.037 | 58.100 | -89.3 / -76.9 / -50.7 | 58.800 | 9.3 / 1.83 |
| R0.382_T1 GBPJPY | 2244 | -0.147 | -96.606 | 3591 | -0.121 | 65.330 | 0.645 | 98.840 | -98.833 | -0.190 / -0.163 / -0.137 | 82.700 | -98.7 / -97.6 / -95.7 | 82.600 | 28.1 / 0.56 |
| R0.382_T1 EURUSD | 2290 | -0.055 | -73.329 | 3682 | -0.052 | 65.752 | 0.833 | 86.676 | -86.579 | -0.090 / -0.063 / -0.037 | 70.700 | -88.2 / -78.2 / -60.2 | 70.800 | 11.6 / 0.57 |

### Signal flow, out-of-sample

| combo / pair | signals | skip_pending | skip_position | skip_small_stop | orders_placed | filled | fill_rate_pct | cancel_786_at_signal | cancel_786 | cancel_trend | cancel_expired | open_at_end | unfilled_orders |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0.382_T2 GBPJPY | 4628.0 | 750.0 | 1779.0 | 0.0 | 2099.0 | 1617.0 | 77.0 | 93.0 | 9.0 | 9.0 | 371.0 | 0.0 | 482.0 |
| R0.382_T2 EURUSD | 4637.0 | 698.0 | 1855.0 | 0.0 | 2084.0 | 1635.0 | 78.5 | 121.0 | 0.0 | 7.0 | 321.0 | 0.0 | 449.0 |
| R0.5_T2 GBPJPY | 4628.0 | 1077.0 | 1246.0 | 0.0 | 2305.0 | 1537.0 | 66.7 | 110.0 | 25.0 | 19.0 | 614.0 | 0.0 | 768.0 |
| R0.5_T2 EURUSD | 4637.0 | 1074.0 | 1232.0 | 0.0 | 2331.0 | 1580.0 | 67.8 | 140.0 | 0.0 | 14.0 | 597.0 | 0.0 | 751.0 |
| R0.382_T1 GBPJPY | 4628.0 | 973.0 | 816.0 | 0.0 | 2839.0 | 2244.0 | 79.0 | 118.0 | 11.0 | 9.0 | 457.0 | 0.0 | 595.0 |
| R0.382_T1 EURUSD | 4637.0 | 946.0 | 814.0 | 0.0 | 2877.0 | 2290.0 | 79.6 | 149.0 | 0.0 | 8.0 | 430.0 | 0.0 | 587.0 |

## 5. Does it beat both benchmarks?

'useful' = avg R > 0 on both pairs AND avg R above chase on both pairs AND at or above the 95th percentile of the random benchmark on both pairs.

| In-sample | avg_R_both_pairs | positive_both_pairs | beats_chase_both_pairs | beats_random_95pct_both_pairs | useful |
|---|---|---|---|---|---|
| R0.382_T1 | -0.072 | False | False | False | False |
| R0.382_T2 | -0.042 | False | False | False | False |
| R0.5_T1 | -0.086 | False | False | False | False |
| R0.5_T2 | -0.071 | False | False | False | False |
| R0.618_T1 | -0.132 | False | False | False | False |
| R0.618_T2 | -0.102 | False | False | False | False |

| Out-of-sample | avg_R_both_pairs | positive_both_pairs | beats_chase_both_pairs | beats_random_95pct_both_pairs | useful |
|---|---|---|---|---|---|
| R0.382_T2 | -0.091 | False | False | False | False |
| R0.5_T2 | -0.135 | False | False | False | False |
| R0.382_T1 | -0.101 | False | False | False | False |

## 6. Flags

- In-sample pick R0.382_T2 FAILS out-of-sample (avg R <= 0 on at least one pair)
- In-sample pick R0.5_T2 FAILS out-of-sample (avg R <= 0 on at least one pair)
- In-sample pick R0.382_T1 FAILS out-of-sample (avg R <= 0 on at least one pair)

## 7. Breakdowns for the in-sample #1 (R0.382_T2), both pairs

Session by entry hour (UTC): Asia 21:00-07:00, London 07:00-13:00, New York 13:00-21:00. CSV breakdowns for all top-3 combos are in `breakdowns/`.

**IS by pair**

| pair | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| EURUSD | 2466.00 | 32.52 | -0.02 | -61.13 |
| GBPJPY | 2390.00 | 34.52 | -0.06 | -142.75 |

**IS by side**

| side | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| buy | 2525.00 | 34.73 | -0.03 | -82.48 |
| sell | 2331.00 | 32.18 | -0.05 | -121.40 |

**IS by session**

| session | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| Asia | 1661.00 | 33.96 | -0.06 | -107.11 |
| London | 1652.00 | 33.05 | -0.03 | -51.22 |
| New York | 1543.00 | 33.51 | -0.03 | -45.55 |

**IS by year**

| year | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 2020 | 1186.00 | 35.41 | 0.01 | 6.82 |
| 2021 | 1181.00 | 33.36 | -0.05 | -58.61 |
| 2022 | 1205.00 | 33.78 | -0.04 | -42.86 |
| 2023 | 1217.00 | 31.64 | -0.08 | -99.83 |
| 2024 | 67.00 | 31.34 | -0.14 | -9.40 |

**IS by month**

| month | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 1 | 444.00 | 32.66 | -0.06 | -27.38 |
| 2 | 370.00 | 38.65 | 0.07 | 26.05 |
| 3 | 457.00 | 36.11 | 0.02 | 8.68 |
| 4 | 397.00 | 32.49 | -0.07 | -26.65 |
| 5 | 388.00 | 31.96 | -0.10 | -37.86 |
| 6 | 407.00 | 33.42 | -0.06 | -24.17 |
| 7 | 412.00 | 29.37 | -0.12 | -49.98 |
| 8 | 390.00 | 31.54 | -0.07 | -28.47 |
| 9 | 403.00 | 33.75 | -0.04 | -16.34 |
| 10 | 375.00 | 34.13 | -0.02 | -7.40 |
| 11 | 412.00 | 35.68 | 0.01 | 5.42 |
| 12 | 401.00 | 32.42 | -0.06 | -25.76 |

**IS GBPJPY by side**

| side | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| buy | 1312.00 | 36.74 | -0.03 | -39.79 |
| sell | 1078.00 | 31.82 | -0.10 | -102.96 |

**IS GBPJPY by session**

| session | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| Asia | 889.00 | 33.75 | -0.10 | -88.74 |
| London | 762.00 | 34.91 | -0.03 | -21.16 |
| New York | 739.00 | 35.05 | -0.04 | -32.84 |

**IS GBPJPY by year**

| year | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 2020 | 564.00 | 35.64 | -0.05 | -26.96 |
| 2021 | 572.00 | 36.36 | -0.04 | -20.98 |
| 2022 | 607.00 | 33.77 | -0.05 | -29.41 |
| 2023 | 614.00 | 32.25 | -0.11 | -64.95 |
| 2024 | 33.00 | 39.39 | -0.01 | -0.46 |

**IS EURUSD by side**

| side | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| buy | 1213.00 | 32.56 | -0.04 | -42.69 |
| sell | 1253.00 | 32.48 | -0.01 | -18.44 |

**IS EURUSD by session**

| session | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| Asia | 772.00 | 34.20 | -0.02 | -18.36 |
| London | 890.00 | 31.46 | -0.03 | -30.05 |
| New York | 804.00 | 32.09 | -0.02 | -12.71 |

**IS EURUSD by year**

| year | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 2020 | 622.00 | 35.21 | 0.05 | 33.78 |
| 2021 | 609.00 | 30.54 | -0.06 | -37.63 |
| 2022 | 598.00 | 33.78 | -0.02 | -13.45 |
| 2023 | 603.00 | 31.01 | -0.06 | -34.88 |
| 2024 | 34.00 | 23.53 | -0.26 | -8.94 |

**OOS by pair**

| pair | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| EURUSD | 1635.00 | 32.91 | -0.03 | -54.51 |
| GBPJPY | 1617.00 | 30.12 | -0.15 | -240.67 |

**OOS by side**

| side | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| buy | 1697.00 | 34.47 | -0.05 | -78.08 |
| sell | 1555.00 | 28.30 | -0.14 | -217.09 |

**OOS by session**

| session | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| Asia | 1173.00 | 31.71 | -0.11 | -125.22 |
| London | 997.00 | 31.70 | -0.07 | -74.30 |
| New York | 1082.00 | 31.15 | -0.09 | -95.65 |

**OOS by year**

| year | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 2024 | 1138.00 | 30.76 | -0.12 | -140.13 |
| 2025 | 1208.00 | 32.04 | -0.06 | -69.56 |
| 2026 | 906.00 | 31.79 | -0.09 | -85.49 |

**OOS by month**

| month | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 1 | 210.00 | 33.33 | -0.04 | -8.99 |
| 2 | 298.00 | 32.55 | -0.08 | -24.68 |
| 3 | 331.00 | 32.02 | -0.06 | -20.13 |
| 4 | 306.00 | 34.64 | -0.04 | -12.27 |
| 5 | 255.00 | 33.73 | -0.03 | -8.66 |
| 6 | 304.00 | 25.66 | -0.23 | -68.48 |
| 7 | 309.00 | 29.77 | -0.17 | -53.23 |
| 8 | 268.00 | 27.99 | -0.15 | -40.91 |
| 9 | 319.00 | 35.11 | 0.03 | 9.00 |
| 10 | 264.00 | 32.95 | -0.04 | -9.54 |
| 11 | 196.00 | 30.61 | -0.09 | -17.14 |
| 12 | 192.00 | 29.17 | -0.21 | -40.15 |

**OOS GBPJPY by side**

| side | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| buy | 924.00 | 34.20 | -0.08 | -77.15 |
| sell | 693.00 | 24.68 | -0.24 | -163.52 |

**OOS GBPJPY by session**

| session | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| Asia | 639.00 | 30.99 | -0.14 | -90.15 |
| London | 480.00 | 31.25 | -0.10 | -48.06 |
| New York | 498.00 | 27.91 | -0.21 | -102.46 |

**OOS GBPJPY by year**

| year | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 2024 | 579.00 | 30.22 | -0.16 | -93.62 |
| 2025 | 614.00 | 29.48 | -0.14 | -84.26 |
| 2026 | 424.00 | 30.90 | -0.15 | -62.79 |

**OOS EURUSD by side**

| side | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| buy | 773.00 | 34.80 | -0.00 | -0.94 |
| sell | 862.00 | 31.21 | -0.06 | -53.57 |

**OOS EURUSD by session**

| session | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| Asia | 534.00 | 32.58 | -0.07 | -35.07 |
| London | 517.00 | 32.11 | -0.05 | -26.24 |
| New York | 584.00 | 33.90 | 0.01 | 6.80 |

**OOS EURUSD by year**

| year | trades | win_rate | avg_R | total_R |
|---|---|---|---|---|
| 2024 | 559.00 | 31.31 | -0.08 | -46.51 |
| 2025 | 594.00 | 34.68 | 0.02 | 14.70 |
| 2026 | 482.00 | 32.57 | -0.05 | -22.70 |

## 8. Counts

### Legs and trend filter

| pair / segment | valid_legs_buy | valid_legs_sell | legs_blocked_by_trend_filter | pct_bars_trend_up | pct_bars_trend_down |
|---|---|---|---|---|---|
| GBPJPY IS | 8176.0 | 7724.0 | 8988.0 | 45.3 | 34.1 |
| GBPJPY OOS | 5607.0 | 5181.0 | 6152.0 | 46.6 | 32.5 |
| EURUSD IS | 8046.0 | 8026.0 | 9142.0 | 38.5 | 40.8 |
| EURUSD OOS | 5498.0 | 5441.0 | 6296.0 | 39.3 | 40.6 |

### Chase signal flow

| run | signals | skip_position | skip_small_stop | skip_target_reached | filled |
|---|---|---|---|---|---|
| chase T1 GBPJPY IS | 6904 | 1231 | 103 | 168 | 5402 |
| chase T1 GBPJPY OOS | 4628 | 859 | 73 | 105 | 3591 |
| chase T2 GBPJPY IS | 6904 | 4298 | 56 | 0 | 2550 |
| chase T2 GBPJPY OOS | 4628 | 2841 | 39 | 0 | 1748 |
| chase T1 EURUSD IS | 6922 | 1231 | 134 | 35 | 5522 |
| chase T1 EURUSD OOS | 4637 | 868 | 67 | 20 | 3682 |
| chase T2 EURUSD IS | 6922 | 4412 | 53 | 0 | 2457 |
| chase T2 EURUSD OOS | 4637 | 2990 | 32 | 0 | 1615 |

### Data gaps (missing 15m bars outside the weekend close)

- GBPJPY: 646 missing bars in 30 episodes (10 longer than 1h). Largest: 2023-12-31 22:00:00 (96 bars), 2024-12-31 22:00:00 (96 bars), 2025-12-31 22:00:00 (96 bars), 2020-12-31 22:00:00 (92 bars), 2024-12-25 08:00:00 (56 bars), 2025-12-25 08:00:00 (56 bars), 2023-12-25 08:00:00 (56 bars), 2020-12-25 07:30:00 (54 bars)
- EURUSD: 616 missing bars in 19 episodes (8 longer than 1h). Largest: 2023-12-31 22:00:00 (96 bars), 2024-12-31 22:00:00 (96 bars), 2025-12-31 22:00:00 (96 bars), 2020-12-31 22:00:00 (92 bars), 2024-12-25 08:00:00 (56 bars), 2023-12-25 08:00:00 (56 bars), 2025-12-25 08:00:00 (56 bars), 2020-12-25 08:00:00 (52 bars)

All gaps longer than 1h are the Christmas and New Year closures.

## 9. Files

- `trade_logs/<PAIR>_<combo>.csv`, `trade_logs/<PAIR>_chase_<T1|T2>.csv`, `trade_logs/orders.csv`
- `in_sample_all6.csv`, `in_sample_ranking.csv`, `out_of_sample_top3.csv`
- `charts/equity_IS.png`, `charts/equity_OOS.png`, `charts/random_benchmark.png`
- `breakdowns/<combo>_<segment>_<year|pair|side|session|month>.csv`
