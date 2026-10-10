**Short answer: no. The macro filter does not add anything you can rely on, on either pair.**

**What was tested.** 24 combos per pair (K 1.5/2/3 × full/body zone × Version A/B × 2R/opposite-zone exit). Each combo was run under the macro filter, no filter and the 200-day trend filter, and the base and top-5 combos also under 1000 random filters. Only 13 of the 24 combos reach ≥ 100 in-sample trades in *each* pair. Every K=3 combo and most body-zone Version B combos fall short, so they could not be ranked.

**In-sample ranking (macro, with swap, average of both pairs).** Only 2 of the top 5 are positive in-sample:
1. K2_full_A_2R (the base): +0.054R
2. K1.5_full_A_2R: +0.023R
3. K2_full_A_zone: 0.000R
4. K1.5_full_A_zone: −0.016R
5. K1.5_body_B_2R: −0.017R

**All 5 lose out-of-sample**, by −0.03R to −0.15R per trade, so they are flagged as overfit. The plateau check flags the two positive combos as likely noise. Their body-zone and Version B neighbours are clearly negative (−0.23R and −0.05R for the base).

**Macro vs the three benchmarks (base combo, with swap).**

| | Macro | No filter | Trend | Random median | Macro percentile vs random |
|---|---|---|---|---|---|
| USDJPY, full period | −0.033R (282 trades) | −0.081R | −0.161R | −0.079R | 76th |
| USDJPY, out-of-sample | −0.146R | −0.093R | −0.142R | −0.090R | 27th |
| EURUSD, full period | +0.028R (299 trades) | +0.016R | −0.031R | +0.022R | 54th |
| EURUSD, out-of-sample | −0.041R | −0.054R | −0.062R | −0.059R | 58th |

On the full period, macro is ahead of all three on paper. But in USDJPY that lead comes entirely from 2016–2019, in-sample, and reverses out-of-sample. In EURUSD it is a coin-flip result.

Across all 24 combos × 2 pairs, macro beats no filter in only 44% of cases in-sample and 29% out-of-sample. Its average expectancy is worse than no filter: −0.075 vs −0.046R in-sample, −0.175 vs −0.139R out-of-sample. It does beat the trend filter about 70% of the time. That is only because the trend filter hurts: these zone entries trade pullbacks, and a 200-day trend side mostly picks the wrong pullbacks.

**Does the signal behave like a signal?** No. With 3 agreeing inputs it does no better than with 2: −0.015R vs +0.007R for the base, and worse in every top combo. A real bias should get stronger when all inputs agree.

**Pairs.** It works on neither pair. USDJPY looks best in-sample and worst out-of-sample. EURUSD is indistinguishable from random.

**Weakest point.** The underlying zone trade has no edge. Unfiltered, the 48 combo-pair runs average −0.08R with a ~30% win rate at 2R, and no day filter can turn that positive.

On top of that, the 3-input vote almost never says "no trade" (about 1% of days), so in practice it just picks long or short. It also cuts trades roughly in half: about 170 in-sample per pair for the base. The standard error of expectancy at that size is about 0.11R, larger than every difference above.

**Minor effects** (none change the conclusion):
- Swap costs about −0.01R per trade.
- Excluding trades within ±3 trading days of MoF intervention days removes at most 12 USDJPY trades.
- The opposite-zone exit falls back to 2R on 78% of trades, because a fresh opposite zone rarely exists in the trade direction. In practice it is mostly the 2R exit.
- Nothing was flagged as unrealistically good.

**What to test next**
1. Test the macro bias on its own, without zones. For example, does the bias side predict the next 5–20 day return of each pair? If it doesn't, no zone overlay will.
2. Test the zone entry against random entries at the same times and with the same stops and targets, to see whether the zones themselves beat chance.
3. Give each input a dead-band, so that small 63-day changes score 0 and "no trade" actually happens. This is a new parameter, so it has to be chosen in-sample only.
4. If 1 or 2 shows anything, add pairs with their own foreign yields (GBPUSD, AUDUSD, USDCAD) to get past roughly 170 trades per pair.
