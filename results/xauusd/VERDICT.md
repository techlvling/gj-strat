**Short answer: no. Neither supply/demand zones nor fading the impulse has an edge on gold (XAUUSD), 2010–2026. Gold is, if anything, worse than the currency pairs.**

**Zones alone (24 combos; 18 have ≥ 100 in-sample trades).**
- **Overall:** averages −0.12R per trade in-sample and −0.09R out-of-sample. Only 1 of the 18 eligible combos is positive in-sample.
- **That one** (K2_full_B_zone, +0.004R) loses out-of-sample (−0.07R), and the plateau check calls it noise.
- **The other top-5 picks** are negative even in-sample (−0.03R to −0.06R). Two of them turn slightly positive out-of-sample:
  - K1.5_full_B_zone: +0.02R, 234 trades, t-stat 0.2.
  - K1.5_body_B_2R: +0.06R, 124 trades, t-stat 0.5.
  
  Neither can be told apart from zero.
- **The base** (K2_full_A_2R) is −0.14R per trade: −59% over the period, with a 62% drawdown.
- **Versions:** every Version A (limit order) combo is clearly negative, −0.12R to −0.50R. Version B is around −0.03R.
- **Long vs short:** the only positive slices are Version B longs, +0.02R to +0.06R, while shorts lose. That is gold's 4× bull market, not the zones: any rule that leans long earns the drift.
- **Vs random entries in the same zone's life:** Version B zone entries beat them (90th–98th percentile). As on the currency pairs, that comes from waiting out the post-impulse retrace, and it still doesn't make the trade profitable.

**Fade the impulse (18 combos, all eligible).**
- **Every one of the 18 combos loses in-sample.** The best is K1.5_close_2R at −0.05R, and it loses out-of-sample (−0.08R).
- **Overall:** averages −0.17R in-sample, −0.11R out-of-sample and −0.14R over the full period. No combo is positive over the full period.
- **Vs random direction:** the fade sits between the 1st and 94th percentile, mostly around the 55th–75th, so the fade direction carries almost no information on gold.
- **Costs:** trading at random times costs −0.11R per trade with these stops (gold's spread is about $0.35).
- **Snap-back:** after big gold impulses it is weaker than on the currency pairs. Fading at random times in the zone's life makes +0.07R, against +0.12R on USDJPY and EURUSD.

**Other:**
- Swap costs longs about fed funds + 0.5% a year, assuming a 0% gold lease rate. It moves results by ≤ 0.01R per trade.
- Nothing was flagged as unrealistically good.

**Bottom line.** Across USDJPY, EURUSD, five yen crosses and gold, 4H supply/demand zones show no edge, and nor does fading their impulses: with or without the macro filter, under every setting tested, after realistic costs. The one consistent pattern is a partial retrace after big 4H impulses, and it is too small to pay for the spread with stops this tight. I would stop testing variants of this idea on historical data. A different concept, or a different holding horizon (daily rather than 4H, so costs are a smaller share of each trade), would be a better use of the next test.
