# Blueberry Instant Elite $2,500 — money actually withdrawn

14-day payouts, $100 minimum, 80% split; rules and models in run_instant_payouts.py.

| Drawdown · plan | got ≥1 payout % | days to first payout (median) | avg paid in first 12 months $ | median paid in 12 months $ | avg paid over 24 months $ | avg per month $ | account lost within 24 months % |
|---|---|---|---|---|---|---|---|
| static · vol-box 0.25% + gotobi 1% | 89 | 126 | 338 | 277 | 613 | 26 | 26 |
| static · vol-box 0.25% + gotobi 2% | 83 | 84 | 543 | 480 | 762 | 32 | 81 |
| static · vol-box 0.25% + gotobi 3% | 75 | 56 | 647 | 409 | 731 | 30 | 100 |
| static · gotobi 2% alone | 84 | 56 | 439 | 450 | 637 | 27 | 83 |
| trailing · vol-box 0.25% + gotobi 1% | 71 | 252 | 202 | 102 | 425 | 18 | 43 |
| trailing · vol-box 0.25% + gotobi 2% | 63 | 140 | 393 | 260 | 552 | 23 | 89 |
| trailing · vol-box 0.25% + gotobi 3% | 54 | 98 | 452 | 139 | 525 | 22 | 100 |
| trailing · gotobi 2% alone | 58 | 140 | 281 | 184 | 422 | 18 | 92 |
