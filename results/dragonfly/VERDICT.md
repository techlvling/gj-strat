# Dragonfly Intercept - Phase 1 verdict

**Short answer: the intercept is not useful. It doesn't reliably beat chasing, it doesn't beat random
entries in a significant way, and it loses money on both pairs, in-sample and out-of-sample.
Phase 2 (2010-2019) is not worth running.**

Full tables are in `REPORT.md`. Charts are in `charts/`. Unit tests (37 passed, run before the
backtest) are in `unit_tests.txt`.

## What was tested

- GBPJPY and EURUSD, 2020-01-01 -> 2026-10-07. Dukascopy bid+ask (1m aggregated to 15m / 1H UTC).
- **6 combos** (R 0.382 / 0.5 / 0.618 x T1 / T2), identical on both pairs. Nothing else was tuned.
- In-sample is 2020-01-01 -> 2024-01-23 (60%). Out-of-sample is 2024-01-23 -> 2026-10-07 (40%).
- Combos were ranked on in-sample only. The top 3 were then run out-of-sample once.

## The numbers that matter (avg R per trade = expectancy)

| | GBPJPY IS | EURUSD IS | GBPJPY OOS | EURUSD OOS |
|---|---|---|---|---|
| #1 R0.382_T2 dragonfly | -0.060 | -0.025 | -0.149 | -0.033 |
| chase, same target (T2) | -0.048 | -0.033 | -0.146 | -0.045 |
| random median (1000 seeds) | -0.093 | -0.033 | -0.167 | -0.069 |
| dragonfly percentile vs random | 94.6 | 66.4 | 74.1 | 91.5 |
| dragonfly return, $10k start, 1% risk | -79% | -52% | -92% | -47% |

- **All 6 combos are negative in-sample on both pairs**, from -0.025R to -0.19R per trade. Every one
  of the top 3 is negative out-of-sample on both pairs. All three are flagged as failing OOS.
- **Every combo has 2,000-3,500 in-sample trades per pair.** Small samples aren't the issue, and
  nothing looks unrealistically good.
- **Plateau check:** the neighbours are just as negative as the picks. The surface is flat and below
  zero, so there is no isolated lucky peak, but no edge either.

## Does the intercept beat chasing?

Not consistently.

- Against chase with the same target, the #1 combo loses on GBPJPY in-sample (-0.060 vs -0.048).
  It wins on EURUSD (-0.025 vs -0.033), and both are negative.
- Out-of-sample it's a tie on GBPJPY (-0.149 vs -0.146) and slightly better on EURUSD.
- At deeper retracements (0.5, 0.618), waiting for the pullback is clearly **worse** than chasing on
  GBPJPY.

## Does it beat random?

Slightly better than random, but not significantly.

- The real result sits at the 27th-95th percentile of random entries. The best was GBPJPY R0.382_T2
  in-sample at 94.6, just under the 95th-percentile bar. The same combo fell to the 74th percentile
  out-of-sample.
- No combo clears the 95th percentile on both pairs in either segment.

## Does it work on both pairs?

No. GBPJPY loses on every combo, about -0.06 to -0.19R in-sample and -0.15 to -0.19R out-of-sample.
EURUSD loses less (-0.02 to -0.08R) but is still negative everywhere.

## Weakest point

**The entry has no edge to pay its costs.**

- With the real spread removed (ask = bid, a diagnostic only, not a variant), the #1 combo is about
  zero: GBPJPY +0.03R in-sample, -0.03R out-of-sample; EURUSD +0.01R / 0.00R.
- The trades then pay the spread. The median stop is about 28 pips on GBPJPY and 14 on EURUSD, and
  a 2-pip GBPJPY spread on a 28-pip stop already costs about 0.07R per trade.
- Because the stop sits behind L, a deeper retracement doesn't help much. Entry gets closer to the
  stop, so 1R shrinks, but the fill rate drops (78% -> 67% -> 56%). The fills it keeps are the legs
  that really reversed.
- The 1H trend filter doesn't rescue it. The OOS sell side was especially poor (-0.14R).
- Losing streaks run 7-14 trades, and drawdowns at 1% risk reach 50-99%.

Sensitivity to my conservative modelling choices is small. "No TP on the fill candle" decided the
outcome of only 0.1-0.6% of trades.

## Phase 2?

**Not worth running.** The rule says the strategy only counts if it beats both benchmarks. Here it
beats neither in a significant way, and it is negative after costs on both pairs. Running the same
frozen settings on 2010-2019 would only confirm a loser or produce a lucky decade. I have **not**
touched 2010-2019 data.

## Modelling decisions (agreed before running, or forced by the data)

- **Data:** 15m bars built from Dukascopy 1m bid+ask, since Dukascopy has no native 15m feed. A
  minute is used only if it traded (bid volume > 0). 1H bars are built from the 15m bars. No 2019
  warm-up data was used: the indicators warm up in the first days of January 2020, and the first
  trade is on 2020-01-06.
- **Signals:** leg and trend use bid prices (the chart price). A leg completes at candle i only if
  candle i-1 made the window's high (i-1 made the low for sells). That gives one signal per leg. The
  window is the 8 closed candles ending with the completion candle.
- **Spread:** the stop buffer and the 3x-spread skip use the fixed nominal spread (GBPJPY 2.5,
  EURUSD 0.8 pips). Fills and exits use the real bid/ask.
- **Order timing:** the order is placed at the completion close and can fill from the next candle.
  If the completion candle itself already closed beyond 78.6%, the order is cancelled at once and
  counted as `cancel_786_at_signal`. If price is already past the limit at placement, it fills at
  the next open.
- **Exits:**
  - On the fill candle, only the stop can be hit.
  - A gap through a stop fills at the open; a gap through TP fills at the open (it's a limit).
  - SL is assumed first when it shares a candle with TP or the BE trigger.
  - The BE stop is live from the next candle.
- **Sizing and accounting:**
  - Size is set at order placement as 1% of current equity over the planned stop distance.
  - R = net USD P&L / planned risk, with JPY P&L converted at USDJPY at exit.
  - Each segment's equity starts at $10,000.
- **Random benchmark:**
  - Trades are independent market entries at the close of random bars where the 1H filter points
    the same way, matching the real buy/sell counts.
  - Stop = the median real stop distance; target = the median planned target multiple; same BE rule.
  - 1000 seeds per pair, combo and segment.
- **Sessions** use the entry hour in UTC: Asia 21-07, London 07-13, New York 13-21.
- **Costs:** commission $0 and swap 0 (both parameters). About 7-19% of trades are held over the
  17:00 NY rollover.
