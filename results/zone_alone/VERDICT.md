**Short answer: supply/demand zones on their own have no tradeable edge on USDJPY or EURUSD, 2010–2026.** Waiting for price to come back to the zone is better than entering at a random moment after the impulse. But that only rescues a trade that is losing to begin with, and it leaves you at roughly break-even before costs.

**Sweep, no filter (24 combos per pair, ranked on in-sample only).**
- 15 of 24 combos reach ≥ 100 in-sample trades in each pair.
- Across all 48 combo-pair runs, average expectancy with swap is:
  - in-sample: −0.05R
  - out-of-sample: −0.14R
  - full period: −0.08R
- Only 12.5% of combo-pair runs (6 of 48) are positive over the full period. The typical win rate is 30–34% at 2R; breakeven needs 33.3%.

**Top 5 in-sample** (average of both pairs):
1. K2_full_B_zone: +0.031R
2. K2_body_B_2R: +0.013R
3. K2_full_B_2R: +0.009R
4. K2_full_A_2R (the base): −0.007R
5. K2_full_A_zone: −0.015R

**Out-of-sample:**
- 4 of the 5 lose (−0.07R to −0.21R) and are flagged as overfit.
- K2_body_B_2R is slightly positive (+0.013R). But it has only 55 and 68 out-of-sample trades, it loses on USDJPY (−0.07R) and wins on EURUSD (+0.09R), and the plateau check calls it noise.
- All three positive in-sample combos are flagged as likely noise. Their neighbours are mostly negative: neighbour medians are −0.015R, −0.031R and −0.005R.

**Zones vs random entries (the fair test).** Each random entry has the same side, stop and target as the real trade and is placed at a random 15m close inside the same zone's life. So it knows everything the zone knew, and only the timing differs.
- Zone entries beat most random entries in-sample: the base combo is at the 94th percentile on USDJPY and the 100th on EURUSD.
- They hold up less well out-of-sample: 76th and 89th for the base, and only the 15th percentile for the Version B full-zone combos on EURUSD.

**What the controls show** (base combo, same stop/TP geometry):

| Average R per trade | USDJPY | EURUSD |
|---|---|---|
| Random side, random time (cost floor) | −0.02 | −0.03 |
| Zone direction, entered at the impulse close | −0.46 | −0.30 |
| Zone direction, random time in the zone's life | −0.16 | −0.18 |
| **Real zone trades** | −0.07 | +0.02 |
| Opposite direction, random time in the zone's life | +0.12 | +0.12 |

After a 4H impulse of 2×ATR or more, price tends to come back. The zone wins its comparison because it waits out that pullback, not because the bounce from the zone is reliable. Once price touches the zone, the trade is roughly a coin flip.

**Other cuts:**
- **Version B vs A:** B is less bad (−0.06R vs −0.11R full period, averaged over all combos). The difference is mostly USDJPY; on EURUSD out-of-sample they are level.
- **Zone type:** full-range zones beat body-only zones (−0.07R vs −0.10R). Body zones give tighter stops that get hit more often.
- **K:** the impulse size makes little difference. K=3 has too few trades to rank.
- **Side:** in the base combo, shorts are around 0R and longs around −0.07R.
- **Interventions:** excluding USDJPY trades open within ±3 trading days of an intervention removes up to 14 trades and changes expectancy by ≤ 0.03R.
- **Swap** costs about −0.01R per trade.
- Nothing was flagged as unrealistically good.

**Weakest point:** the edge has to come from the bounce at the zone, and there isn't one. The only robust effect in the data is the snap-back after big impulses, and these zone rules trade that in the wrong direction.

**What to test next**
1. Test the snap-back on its own merits: fade a 4H impulse of 2×ATR or more, with entry, stop and target defined from the impulse itself. It was spotted on the full sample, so it must go through the same in-sample/out-of-sample protocol (its parameters chosen on 2010–2020 only) before believing it.
2. If you want to keep zones, add a confirmation that the pullback has finished (Version B is a weak form of this). Measure it against the same zone-life random-entry benchmark.
