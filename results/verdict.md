**Short answer: no edge has been shown yet.** It isn't clearly losing either. Measured honestly, the result can't be told apart from zero.

**Is there an edge?**
- Base Version A made +0.079R per trade over 847 trades (+63%). The t-stat is 1.16, which would happen about 1 time in 4 with no edge at all. Almost all of that profit came after the in-sample period. In-sample the same rules made **+0.018R** (−1% net, with a 48% drawdown).
- The sweep tested **170 combos**. Luck alone would be expected to produce a best in-sample t-stat of about 2.5–3.2. The actual best was **0.99**. No parameter set stands out from noise.
- The in-sample top 5 are all SL 40 with BE at 1R–1.5R. Out-of-sample they fell to between −0.01R and +0.04R per trade. Three are flagged degraded, one overfit, and two sit on weak neighbours. The "best SL" also reversed between the halves: 40 pips won in-sample, 20–30 pips won out-of-sample. Noise behaves like that.
- **Version A vs B:** A is slightly better (+0.079R vs +0.068R; +63% vs +43%). The whole difference is in re-entries. A filled 142 second trades and B filled only 65, because B's stop was already crossed 120 times. A's second trades averaged +0.09R and B's −0.02R. That direction makes sense, but at n=142 it isn't statistically meaningful.
- **Break-even:** BE at 1.5R helped in-sample on 75% of RR×SL cells, by about +0.015R. Out-of-sample it hurt on average. BE mostly changes the shape of returns (win rate up, average win down), not the edge.
- **RR / SL:** no RR is reliably better. **SL 15 is consistently bad**: the 2.1-pip spread is about 12% of a 17-pip risk, and noise stops you out. SL 30–40 is the least bad range.

**Weakest point:** the edge is tiny compared with the risks around it.
1. The base case had a **51% max drawdown and a 22-loss streak at 1% risk**. One month, April 2025 (the tariff shock), lost **−28R**, with 1 win out of 29.
2. At about 0.05–0.08R per trade, **one extra pip of slippage per side (~0.06R) wipes it out**. Commission at a typical $7 per lot round turn costs about 0.03R more.
3. **Buys carry the result** (+0.16R vs −0.01R for sells). GBPJPY rose about 16% over the test (179.5 → 208.9). Long swap on GBPJPY is positive and short swap negative, and about 21% of trades are held overnight with **swap not modelled**. Part of the "edge" may just be being long a rising pair.
4. This is under three years of data, in one regime.

**What to test next, in order:**
1. **Older data as a true out-of-sample test.** Dukascopy has GBPJPY back to 2003. Run these exact rules, untouched, on 2010–2023 (`--end`; extend `START`). That is the cleanest check available, because nothing was fitted on that period.
2. **Costs:** rerun with `--commission 7` and 0.5–1 pip of extra slippage on stop fills, and add the swap. If the base case goes negative, stop here.
3. **A range-size filter** (skip days with a range above 30 or 40 pips). It is the only pattern positive in **both** halves (ranges under 20 pips: +0.35R in-sample, +0.15R out-of-sample). Fix the threshold first and test it on the older data, not on this sample. Ignore Monday, Friday and large-range patterns: they reverse between halves.
4. **Direction:** compare buy-only with a simple trend filter (for example, trade only with the daily 50-day MA) to separate a breakout edge from GBPJPY drift.
5. **Walk-forward** (fit on 12 months, trade the next 3, roll) instead of a single 60/40 split, if steps 1–3 leave anything worth fitting.

Data notes: 16 of 723 weekdays were skipped. Three were holidays with no data. Thirteen had tick-less minutes in the range window, mostly a single minute, under your strict "any missing minute" rule; `--max-missing 2` would keep most of them. Every fill is conservative where 1-minute bars are ambiguous (SL first, no TP on the entry bar, no positive slippage), so on these mechanics results are more likely understated than overstated.
