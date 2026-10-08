# GBPJPY 05:00–06:00 IST range breakout backtest

Plain pandas + numpy, own event-driven loop, no strategy libraries.

```
pip install pandas numpy matplotlib requests pytest
python -m pytest -q                 # rule-by-rule engine tests (hand-built candles)
python run_backtest.py --synthetic  # random-walk sanity run (should show no edge)
python run_backtest.py              # downloads Dukascopy data into data/ (cached), full run
```

Options: `--end YYYY-MM-DD` (last UTC day to download), `--commission 7` (USD per lot round
turn), `--max-missing N` (tick-less minutes tolerated in the range window, default 0),
`--out DIR`.

Results go to `results/`: `REPORT.md` (all tables + verdict), `charts/`, `trade_logs/*.csv`,
`sweep_version_A.csv` (every combo, in-sample / out-of-sample / full), `summary.json`.

## Layout

| File | What |
|---|---|
| `gjstrat/data.py` | Dukascopy BID/ASK 1-min download + decode, continuous UTC minute grid, synthetic market |
| `gjstrat/engine.py` | Per-day state machine: range → OCO stops → trade → 6-bar wait → re-entry |
| `gjstrat/accounting.py` | 1% compounding, 0.01-lot rounding, USDJPY pip value, stats, breakdowns |
| `run_backtest.py` | Base A vs B, Version A sweep, IS/OOS ranking, plateau check, charts, report |
| `tests/test_engine.py` | One test per rule (UTC-midnight range, gaps, SL-first, BE, re-entry A/B, expiry, skips) |

## Modelling decisions

Times: strategy in IST (UTC+5:30, no DST). Range = bars 23:30–00:29 UTC (previous UTC date),
orders placed 00:30 UTC, expire 05:30 UTC. Only Mon–Fri IST dates are trading days.

* Range and re-entry extremes use **BID** candles. Buy stops trigger when **ask** high reaches
  the level and fill at ask; longs exit on bid. Sell stops trigger on **bid**, shorts exit on ask.
* 1R = SL pips + entry spread (ask − bid at the open of the entry bar), measured from the fill.
  TP = entry ± RR × 1R. BE moves the stop to entry ± BE_plus pips once price reaches
  BE_trigger × 1R (on the exit side).
* Gaps through a stop (entry stop, SL or BE stop) fill at the bar's open. TP is a limit order and
  fills at the TP price (no positive slippage).
* At 06:00, a level already crossed at the open fills at market at the 06:00 open (user choice).
  A re-entry stop already crossed when placed is skipped and counted.
* Same bar touches SL and TP / BE trigger → SL first. On the entry bar only the SL can be hit.
  A BE stop becomes live on the bar after the trigger bar.
* Both 06:00 stops inside one bar → the side beyond the level at the open, else the level nearer
  the open, is treated as first; the other is cancelled.
* Re-entry window = the SL/BE exit bar plus the next 5 bars; the order is placed at the open of
  the 7th bar, which must be before 11:00 IST. Version A: level = the window's extreme if it went
  beyond the range level, else the range level. Version B: always the range level.
* Days are independent: overlapping positions from different days are allowed. Risk = 1% of the
  closed balance at entry; lots rounded down to 0.01 (minimum 0.01). No swap modelled.
* Days with any tick-less minute in the 05:00–05:59 IST range window are skipped and listed.
* In-sample / out-of-sample split: first 60% / last 40% of tradable days. Combos are ranked by
  in-sample t-stat of mean R only.
