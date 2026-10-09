# Home-hours drift test — 5 pairs, 2010–2026

40 pre-declared tests (see run_patterns_hours.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.

**Survivors: 0 of 40.** Opposite directions of one window are near mirror images, so about 1 would pass by luck.

## Raw drift before costs (+ = home currency weakened), pips per day

| window · pair | design days | design mean pips | design t | check days | check mean pips | check t |
|---|---|---|---|---|---|---|
| H1 tokyo · USDJPY | 2030.00 | -2.01 | -2.91 | 1561.00 | -0.03 | -0.03 |
| H3 us · USDJPY | 2030.00 | -1.23 | -2.39 | 1561.00 | -1.52 | -2.90 |
| H1 tokyo · EURJPY | 2029.00 | -1.09 | -1.21 | 1561.00 | 0.46 | 0.56 |
| H2 europe · EURJPY | 2029.00 | 2.18 | 2.22 | 1561.00 | 1.45 | 1.39 |
| H1 tokyo · GBPJPY | 2030.00 | -2.17 | -1.79 | 1561.00 | -0.09 | -0.09 |
| H2 europe · GBPJPY | 2030.00 | -0.09 | -0.07 | 1561.00 | 1.11 | 0.79 |
| H2 europe · EURUSD | 2031.00 | 3.09 | 3.67 | 1562.00 | 1.38 | 1.97 |
| H3 us · EURUSD | 2031.00 | 1.06 | 1.68 | 1562.00 | 0.31 | 0.64 |
| H2 europe · GBPUSD | 2031.00 | 1.01 | 0.98 | 1561.00 | 1.08 | 1.00 |
| H3 us · GBPUSD | 2031.00 | 1.61 | 2.61 | 1561.00 | -0.36 | -0.54 |

## Tradeable version (after costs)

| Setup · pair | design trades | design win % | design avg R | design t | check trades | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|
| H2 europe home-weak SELL SL1ATR · EURUSD | 2031 | 50.271 | 0.017 | 2.179 | 1562 | -0.002 | -0.186 | False |
| H2 europe home-weak SELL SL0.5ATR · EURUSD | 2031 | 49.828 | 0.030 | 1.994 | 1562 | -0.008 | -0.479 | False |
| H1 tokyo home-strong SELL SL1ATR · USDJPY | 2030 | 50.985 | 0.005 | 0.763 | 1561 | -0.017 | -2.212 | False |
| H2 europe home-weak SELL SL0.5ATR · EURJPY | 2029 | 48.743 | 0.007 | 0.492 | 1561 | -0.019 | -1.000 | False |
| H2 europe home-weak SELL SL1ATR · EURJPY | 2029 | 49.039 | 0.002 | 0.313 | 1561 | -0.004 | -0.456 | False |
| H3 us home-weak BUY SL0.5ATR · EURUSD | 2031 | 48.449 | 0.003 | 0.261 | 1562 | -0.027 | -2.303 | False |
| H1 tokyo home-strong SELL SL0.5ATR · USDJPY | 2030 | 50.394 | 0.001 | 0.107 | 1561 | -0.031 | -2.084 | False |
| H3 us home-weak BUY SL1ATR · EURUSD | 2031 | 48.498 | -0.001 | -0.220 | 1562 | -0.014 | -2.193 | False |
| H2 europe home-weak SELL SL0.5ATR · GBPUSD | 2031 | 48.941 | -0.005 | -0.295 | 1561 | -0.012 | -0.648 | False |
| H3 us home-strong BUY SL1ATR · USDJPY | 2030 | 49.655 | -0.002 | -0.362 | 1561 | -0.001 | -0.097 | False |
| H2 europe home-weak SELL SL1ATR · GBPUSD | 2031 | 49.483 | -0.006 | -0.646 | 1561 | -0.009 | -0.880 | False |
| H3 us home-strong BUY SL0.5ATR · USDJPY | 2030 | 49.360 | -0.007 | -0.699 | 1561 | -0.005 | -0.459 | False |
| H3 us home-weak BUY SL1ATR · GBPUSD | 2031 | 48.154 | -0.004 | -0.712 | 1561 | -0.023 | -3.791 | False |
| H1 tokyo home-strong SELL SL0.5ATR · EURJPY | 2029 | 46.969 | -0.010 | -0.811 | 1561 | -0.038 | -2.725 | False |
| H1 tokyo home-strong SELL SL1ATR · EURJPY | 2029 | 47.215 | -0.006 | -0.854 | 1561 | -0.021 | -2.938 | False |
| H3 us home-weak BUY SL0.5ATR · GBPUSD | 2031 | 48.006 | -0.009 | -0.879 | 1561 | -0.046 | -4.086 | False |
| H1 tokyo home-strong SELL SL1ATR · GBPJPY | 2030 | 46.749 | -0.006 | -0.962 | 1561 | -0.020 | -3.034 | False |
| H1 tokyo home-strong SELL SL0.5ATR · GBPJPY | 2030 | 46.256 | -0.019 | -1.654 | 1561 | -0.038 | -2.893 | False |
| H2 europe home-weak SELL SL0.5ATR · GBPJPY | 2030 | 46.897 | -0.026 | -1.706 | 1561 | -0.020 | -1.077 | False |
| H2 europe home-weak SELL SL1ATR · GBPJPY | 2030 | 47.340 | -0.017 | -2.076 | 1561 | -0.014 | -1.389 | False |
| H2 europe home-strong BUY SL0.5ATR · GBPJPY | 2030 | 46.453 | -0.035 | -2.303 | 1561 | -0.039 | -2.174 | False |
| H2 europe home-strong BUY SL1ATR · GBPJPY | 2030 | 47.143 | -0.019 | -2.378 | 1561 | -0.027 | -2.802 | False |
| H2 europe home-strong BUY SL1ATR · GBPUSD | 2031 | 45.741 | -0.030 | -3.482 | 1561 | -0.026 | -2.654 | False |
| H1 tokyo home-weak BUY SL1ATR · EURJPY | 2029 | 45.786 | -0.025 | -3.869 | 1561 | -0.018 | -2.587 | False |
| H2 europe home-strong BUY SL0.5ATR · GBPUSD | 2031 | 44.904 | -0.065 | -4.023 | 1561 | -0.049 | -2.719 | False |
| H1 tokyo home-weak BUY SL0.5ATR · EURJPY | 2029 | 45.589 | -0.050 | -4.060 | 1561 | -0.040 | -2.893 | False |
| H2 europe home-strong BUY SL0.5ATR · EURJPY | 2029 | 46.131 | -0.063 | -4.411 | 1561 | -0.050 | -2.960 | False |
| H3 us home-strong SELL SL1ATR · EURUSD | 2031 | 43.427 | -0.026 | -4.680 | 1562 | -0.021 | -3.313 | False |
| H2 europe home-strong BUY SL1ATR · EURJPY | 2029 | 46.476 | -0.036 | -4.685 | 1561 | -0.030 | -3.281 | False |
| H3 us home-strong SELL SL0.5ATR · EURUSD | 2031 | 43.131 | -0.050 | -4.833 | 1562 | -0.041 | -3.410 | False |
| H1 tokyo home-weak BUY SL1ATR · GBPJPY | 2030 | 45.468 | -0.031 | -4.886 | 1561 | -0.024 | -3.684 | False |
| H1 tokyo home-weak BUY SL0.5ATR · GBPJPY | 2030 | 45.172 | -0.061 | -4.998 | 1561 | -0.048 | -3.890 | False |
| H1 tokyo home-weak BUY SL0.5ATR · USDJPY | 2030 | 42.315 | -0.078 | -5.188 | 1561 | -0.040 | -2.661 | False |
| H1 tokyo home-weak BUY SL1ATR · USDJPY | 2030 | 42.660 | -0.041 | -5.193 | 1561 | -0.022 | -2.742 | False |
| H2 europe home-strong BUY SL0.5ATR · EURUSD | 2031 | 44.412 | -0.080 | -5.690 | 1562 | -0.058 | -3.525 | False |
| H2 europe home-strong BUY SL1ATR · EURUSD | 2031 | 44.707 | -0.044 | -5.915 | 1562 | -0.033 | -3.768 | False |
| H3 us home-weak SELL SL1ATR · USDJPY | 2030 | 40.000 | -0.038 | -6.731 | 1561 | -0.039 | -6.764 | False |
| H3 us home-weak SELL SL0.5ATR · USDJPY | 2030 | 39.852 | -0.073 | -6.951 | 1561 | -0.077 | -6.999 | False |
| H3 us home-strong SELL SL1ATR · GBPUSD | 2031 | 42.196 | -0.034 | -6.959 | 1561 | -0.017 | -2.789 | False |
| H3 us home-strong SELL SL0.5ATR · GBPUSD | 2031 | 42.048 | -0.071 | -7.520 | 1561 | -0.036 | -3.067 | False |
