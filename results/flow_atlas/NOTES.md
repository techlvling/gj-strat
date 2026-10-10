# What the flow atlas found

## Scan result
- 600,912 pre-declared tests. 161 flows passed design, check and holdout on mid prices.
- Most are known effects or quote mechanics, and most move only 1–3 bp, which is less than the spread:
  - **Rollover jump at 17:00 New York, triple on Wednesday.** High-yield currencies (AUD, NZD) drop at the
    rollover by about the interest differential, and by about 3× on Wednesday. This is the forward-point
    adjustment for the later value date; the swap pays it back, so there is nothing to trade.
  - **Home-hours effect.** A currency weakens during its own session (AUD in the Sydney morning, EUR around
    European midday, JPY in early Tokyo). Known: Ranaldo 2009; Breedon & Ranaldo 2013.
  - **Gotobi.** JPY weakens before the 09:55 Tokyo fix on gotobi days, in every JPY cross. Known: Ito & Yamada.
  - **Month-end London 4pm fix (EURGBP).** Known category (Melvin & Prins 2015), and it is fading.
  - **Gold up on Friday afternoon (New York).** Known as a daily effect (Friday gold returns). Fails after costs.

## After real costs (bid/ask, $7/lot, slippage, swap)
3 of 161 pass our bar (design t ≥ 2, check > 0, holdout > 0):

| Flow | Trade | avg R design / check / holdout | Status |
|---|---|---|---|
| Month-end London fix | sell EURGBP 15:00–16:00 London, last weekday | +0.45 / +0.18 / +0.04 | known, fading |
| Day after a US holiday | buy USDJPY around the Tokyo fix | +0.12 / +0.05 / +0.07 | small sample (153), weak |
| 3rd-last weekday of the month | buy USD 11:00–12:00 UTC | +0.10 / +0.21 / +0.02 (USDJPY) | probably undocumented |

## The 3rd-last-weekday USD bid (run_monthend_t2.py)
- In the 2024–26 holdout, USD-buy is positive after costs in all 7 USD pairs.
- The six-pair basket does best on the 3rd-last weekday; the days around it lose roughly the cost of trading:
  +0.064R overall, t 2.5.
- P2 failed: USDCAD settles T+1, so it should shift to the 2nd-last weekday, but it does not. The
  "spot T+2 for month-end value" explanation is therefore not supported, and the cause is unknown.
- It is stronger outside quarter-end months, so it is not quarter-end window dressing.
- On those days USD also rises at the London open (06:30–07:00 UTC) and into the 4pm fix in summer
  (14:30–15:00 UTC), then reverses after the fix. This matches the pre-fix USD appreciation that
  Krohn, Mueller & Whelan document, but it is stronger on this one day of the month.
- Size: about +0.06–0.13R per trade, 12 days a year. It is real-looking but too small to be a strategy on
  its own.

## Literature checked
- Krohn, Mueller & Whelan, "Foreign Exchange Fixings and Returns Around the Clock": USD rises before the
  Tokyo, Frankfurt and London fixes on all days, then reverses.
- Ito & Yamada, Tokyo fix / gotobi.
- Melvin & Prins (2015), month-end London fix and equity-hedge rebalancing.
- Turn-of-month and day-of-week FX studies (e.g. "Revisiting calendar anomalies", Journal of Economics and
  Business 2016).
- None of these reports a specific USD bid on the 3rd-last business day, or after US holidays at the
  Tokyo fix.
