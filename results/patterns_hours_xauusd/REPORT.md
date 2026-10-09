# Home-hours drift test — XAUUSD, 2010–2026

4 pre-declared tests (see run_patterns_hours.py). Costs: $7/lot, swap (+1% markup), 0.2 pip slippage. Survival rule fixed before running: design (2010–2017) avg R > 0 with t ≥ 2 AND check (2018–2023) avg R > 0. Holdout (2024–2026) only for survivors.

**Survivors: 0 of 4.** Opposite directions of one window are near mirror images, so about 1 would pass by luck.

## Raw drift before costs (+ = home currency weakened), pips per day

| window · pair | design days | design mean pips | design t | check days | check mean pips | check t |
|---|---|---|---|---|---|---|
| H3 us · XAUUSD | 2020.00 | 1.04 | 0.08 | 1548.00 | -10.83 | -0.79 |

## Tradeable version (after costs)

| Setup · pair | design trades | design win % | design avg R | design t | check trades | check avg R | check t | survives |
|---|---|---|---|---|---|---|---|---|
| H3 us home-strong SELL SL0.5ATR · XAUUSD | 2020 | 43.366 | -0.036 | -3.098 | 1548 | -0.035 | -2.979 | False |
| H3 us home-weak BUY SL1ATR · XAUUSD | 2020 | 43.663 | -0.024 | -3.648 | 1548 | -0.028 | -4.354 | False |
| H3 us home-weak BUY SL0.5ATR · XAUUSD | 2020 | 43.267 | -0.045 | -3.740 | 1548 | -0.053 | -4.424 | False |
| H3 us home-strong SELL SL1ATR · XAUUSD | 2020 | 43.465 | -0.024 | -3.802 | 1548 | -0.018 | -2.935 | False |
