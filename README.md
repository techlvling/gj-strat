# GBPJPY 05:00–06:00 IST range breakout backtest

Plain pandas + numpy, own event-driven loop, no strategy libraries.

```
pip install pandas numpy matplotlib requests pytest
python -m pytest -q                 # rule-by-rule engine tests (hand-built candles)
python run_backtest.py --synthetic  # random-walk sanity run (should show no edge)
python run_backtest.py              # downloads Dukascopy data into data/ (cached), full run
python compare_versions.py          # base settings: A vs B vs C (fade) -> results/version_comparison/
python run_majors.py                # A and B on the 7 majors (+ GBPJPY) -> results/majors/
python run_majors.py --sl-box 1 --out results/majors_box_sl   # SL = that day's box + spread
```

Version C ("fade"): the first break of the box is not traded. It is followed virtually with
the normal SL/TP/BE, and an opposite stop sits at its SL price. That stop fills only if the
virtual trade is stopped out, and is cancelled if the virtual trade reaches TP or BE first.
By default the stop expires at 11:00 IST like every other order
(`Params(fade_expiry_11=False)` keeps it alive as long as the virtual trade). The real trade
then follows the normal rules, including the Version A re-entry.

Version W ("weekly bias", `gjstrat/bias.py`): daily candles close at 17:00 New York. The latest
daily close of the current week above last week's high means buy stop only; below last week's
low means sell stop only; inside last week's range (and every Monday) means no trade. One trade
a day, no re-entry.

`python fetch_pairs.py` downloads the 7 majors and 21 minors (bid + ask) into `data/raw`.
`--save` packs each finished pair into `datastore/<PAIR>.tar` (committed) and unpacks those on
start, so a new container only downloads what is missing. Pip size is 0.01 for JPY pairs and
0.0001 otherwise; pip value is converted to USD per pair (XXXUSD: 1, USDXXX: its own price,
JPY crosses: USDJPY).

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

## Zone + macro-bias backtest (USDJPY, EURUSD) — `zonemacro/`

```
python -m pytest tests/test_zone_macro.py -q   # rule-by-rule tests on hand-made candles
python run_zone_macro.py                       # sweep + benchmarks -> results/zone_macro/REPORT.md
python -m zonemacro.report                     # rebuild REPORT.md from the CSVs
```

4H supply/demand zones (base of 1–3 small-body candles, impulse >= K x ATR(14) within 3 candles,
active only after the impulse candle closes, fresh only: dies at first touch or after 50 4H bars),
traded only in the direction of a 3-input US macro bias (DGS2−DFF, DGS10 − JGB10/Bund10, US CPI YoY
from ALFRED first releases; each scored on its 63-trading-day change). Version A = limit at the
near edge; Version B = 15m break of the last confirmed swing after price enters the zone. Exits:
fixed 2R or the nearest fresh opposite zone. 24 combos per pair, ranked in-sample only, top 5
tested out-of-sample, benchmarked against no filter, 1000 random filters and a 200-day trend filter.

| File | What |
|---|---|
| `zonemacro/sources.py` | FRED, ALFRED CPI vintages, MoF JGB 10y, Bundesbank Bund 10y, BoJ call rate, ECB DFR, MoF interventions → `zonemacro_data/*.parquet` (committed) |
| `zonemacro/prices.py` | Dukascopy 1m bid+ask (datastore) → 15m bars by year → `data/cache/*.parquet`; 4H bars; daily closes; data gaps |
| `zonemacro/macro.py` | release-timed macro values, bias, day filters (macro / none / trend / random) |
| `zonemacro/zones.py` | ATR, base/impulse/zone detection |
| `zonemacro/engine.py` | 15m execution (A/B entries, SL/TP, gaps), swap, one-position portfolio pass, stats |
| `zonemacro/report.py`, `zonemacro/charts.py` | REPORT.md and equity charts |
