# Prop challenge: dynamic risk — USDJPY Version B

Same rules as `results/prop_sim` (P1 +8%, P2 +6%, static 10%, daily 4%, ≥3 days, costs + 0.2 pip slippage). Schemes fixed before any result (see run_prop_dynamic.py).

## Fair comparison: passed within 3 / 6 / 12 months

Every challenge started at least 12 months before the data ends. Use this table: the 'room' schemes shrink risk toward zero instead of failing, so most of their challenges get stuck for years, and the plain pass % below (which drops unfinished challenges) flatters them.

| Scheme | challenges | pass ≤90d % | pass ≤180d % | pass ≤365d % | failed ≤365d % | stuck >365d % |
|---|---|---|---|---|---|---|
| fixed 0.5% | 3791.0 | 16.6 | 31.2 | 38.0 | 62.0 | 0.0 |
| fixed 1% | 3791.0 | 18.9 | 19.2 | 19.2 | 80.8 | 0.0 |
| step-down 1 / 0.5 / 0.25% | 3791.0 | 21.8 | 24.5 | 25.3 | 74.7 | 0.0 |
| room ÷ 10 (starts 1%) | 3791.0 | 16.1 | 23.9 | 29.9 | 7.6 | 62.5 |
| room ÷ 15 (starts 0.67%) | 3791.0 | 14.0 | 24.8 | 34.2 | 0.7 | 65.2 |
| room ÷ 20 (starts 0.5%) | 3791.0 | 10.1 | 21.8 | 35.5 | 0.0 | 64.5 |

## Raw table (unfinished challenges excluded — misleading for 'room' schemes)

| Starts · scheme | challenges | PASS % | median days to pass | median days to fail | attempts per pass | expected days to funded |
|---|---|---|---|---|---|---|
| all · fixed 0.5% | 3951.0 | 36.8 | 103.0 | 72.5 | 2.7 | 265.0 |
| 2018–2026 · fixed 0.5% | 1980.0 | 39.3 | 100.0 | 74.0 | 2.5 | 248.9 |
| all · fixed 1% | 3990.0 | 18.5 | 28.0 | 23.0 | 5.4 | 157.2 |
| 2018–2026 · fixed 1% | 2019.0 | 18.1 | 26.0 | 24.0 | 5.5 | 158.7 |
| all · step-down 1 / 0.5 / 0.25% | 3952.0 | 24.5 | 42.0 | 55.0 | 4.1 | 265.7 |
| 2018–2026 · step-down 1 / 0.5 / 0.25% | 1981.0 | 23.1 | 37.0 | 58.0 | 4.3 | 280.7 |
| all · room ÷ 10 (starts 1%) | 1596.0 | 73.0 | 83.0 | 261.0 | 1.4 | 212.8 |
| 2018–2026 · room ÷ 10 (starts 1%) | 858.0 | 86.7 | 92.5 | 91.5 | 1.2 | 148.8 |
| all · room ÷ 15 (starts 0.67%) | 1468.0 | 97.9 | 123.0 | 306.0 | 1.0 | 171.0 |
| 2018–2026 · room ÷ 15 (starts 0.67%) | 940.0 | 96.7 | 138.0 | 306.0 | 1.0 | 181.2 |
| all · room ÷ 20 (starts 0.5%) | 1673.0 | 99.7 | 183.0 | 438.0 | 1.0 | 233.1 |
| 2018–2026 · room ÷ 20 (starts 0.5%) | 1004.0 | 99.5 | 187.0 | 438.0 | 1.0 | 236.0 |
