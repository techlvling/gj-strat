**Short answer: fading the 4H impulse, with these rules, has no tradeable edge on the two pairs together.** There is one lead, USDJPY at K=3, but it fails on EURUSD with the same rules, and it is too small and too data-mined to trust yet.

**Sweep (18 combos per pair, all eligible; ranked on 2010–2020 only).**
- Average expectancy with swap is −0.10R in-sample and −0.07R out-of-sample.
- Only 22% of combo-pair runs are positive over the full period.

**Top 5 in-sample** (average of both pairs):
1. K3_close_2R: +0.046R
2. K3_close_1R: +0.015R
3. K1.5_close_2R: −0.009R
4. K2_close_1R: −0.031R
5. K2_close_2R (the base): −0.041R

**All 5 lose out-of-sample** (−0.03R to −0.14R) and are flagged as overfit. The plateau check calls the two positive ones likely noise: their neighbours have medians of −0.09R and −0.08R.

**Fade direction vs a coin-flip direction** (same moment, same stop and target):

| Combo | Pair | In-sample percentile | Out-of-sample percentile | Expectancy, IS → OOS |
|---|---|---|---|---|
| Base (K2_close_2R) | USDJPY | 97th | 23rd | |
| Base (K2_close_2R) | EURUSD | 57th | 28th | |
| K3_close_2R | USDJPY | 99th | 75th | +0.27R → +0.05R |
| K3_close_2R | EURUSD | 10th | 36th | −0.17R → −0.10R |

On EURUSD, fading big impulses is worse than a coin flip: those impulses tend to continue.

**Why the earlier hint didn't turn into a strategy.** The +0.12R in the zone study's controls came from fading at a random time later in the zone's life, with a stop sized from the zone, about 36 pips. Fading right at the impulse close with the stop just beyond the impulse extreme gives a median stop of about 17 pips (a quarter are under 10). At that size, spread and noise dominate: the cost floor alone is −0.06R per trade. Waiting for a confirmation candle didn't help either; it was worse in-sample in every pairing.

**USDJPY K=3, the only lead.**
- 2R target: +0.17R over the full period (257 trades, 98th–99th percentile in-sample, 75th out-of-sample).
- 1R target: +0.07R.
- The equity curve grows mostly in 2010–2014 and 2020–2022, then goes flat to down.
- Out-of-sample it has only about 110 trades and +0.02R to +0.05R, which is not distinguishable from zero.
- Trading it means dropping your "identical rules on both pairs" principle and picking USDJPY after seeing the result. That is exactly the kind of choice the protocol exists to prevent.

**Multiple testing.** This is the third strategy family tested on the same 2010–2026 data, and the 2020–2026 "out-of-sample" has now been looked at three times. Each new idea derived from these results is less protected by that split. Anything that looks good from here needs fresh data before real money: other pairs, or forward/paper trading.

**Other:**
- Swap and the intervention exclusion change results by ≤ 0.03R.
- No result was flagged as unrealistically good.

**What I would do next**
1. Stop iterating on these two pairs' history. Across three families, the only consistent pattern is that big 4H impulses partially retrace. These rules haven't turned that into money after costs.
2. If you want one more test, take the USDJPY K=3 fade exactly as it is now (no re-tuning) and check it on fresh data: other JPY pairs (EURJPY, GBPJPY, AUDJPY are already in `datastore/`) and from now on as paper trades. If it doesn't hold there, drop it.
