**Short answer: it fails. The USDJPY K=3 fade does not carry over to the other yen pairs, so treat the USDJPY result as a one-pair fluke.**

**Primary rule, K3_close_2R, unchanged from USDJPY, 2010–2026, with swap.** It fails all three criteria fixed before the run:

| Pair | Trades | Expectancy | vs random direction (percentile) |
|---|---|---|---|
| EURJPY | 231 | −0.057R | 52nd |
| GBPJPY | 253 | −0.039R | 76th |
| AUDJPY | 190 | −0.049R | 39th |
| CADJPY | 214 | −0.093R | 87th |
| CHFJPY | 165 | +0.047R | 88th |
| **Pooled, 5 fresh pairs** | 1053 | **−0.042R** | 89th |
| USDJPY (reference, where the rules were found) | 257 | +0.171R | 99th |

1. Pooled expectancy −0.042R → **FAIL**
2. Pooled percentile 89, below the 95 needed → **FAIL**
3. Positive on 1 of 5 pairs → **FAIL**

CHFJPY, the only positive pair, is negative in 2020–2026 (−0.005R) and gives back most of its 2022–2023 gain by 2026.

**Secondary rule, K3_close_1R** (for information only):
- Pooled −0.032R, positive on 1 of 5 pairs.
- It does beat the random direction at the 98th percentile pooled.

**What the "beats random" numbers mean.** Fading is somewhat better than picking a random direction at the same moment. On the 1R rule it's clearly better: the pooled random-direction median is −0.09R against −0.03R for the fade. But the random-direction median is essentially the cost of trading: spread, plus the stop and target being slightly asymmetric after spread on these short stops. So there is a small real snap-back after 3×ATR yen impulses, worth roughly 0.05R per trade. The cost of trading it with stops this tight is about 0.09R per trade, which is bigger, so it doesn't pay.

**Caveats:**
- These crosses aren't fully independent of USDJPY: many big impulses are the same yen move showing up on every pair. That makes the failure more telling, not less. The same yen events that paid on USDJPY didn't pay on its crosses.
- MoF intervention windows change results by ≤ 0.03R.
- NZDJPY was not tested: the datastore has data only to 2012.

**Bottom line across all four studies:** no tested version of 4H supply/demand trading has a robust edge on these pairs after costs. That covers zones with the macro filter, zones alone, the fade on USDJPY and EURUSD, and the frozen USDJPY fade on 5 yen crosses. The one real effect, a partial snap-back after big impulses, is smaller than the cost of trading it with these stops.
