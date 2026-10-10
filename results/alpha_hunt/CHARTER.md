# Alpha hunt charter (every agent reads this first)

Repo: /home/user/gj-strat (Python, pandas + numpy, own backtester). Goal: find **any** real, tradeable edge
(any style: carry, momentum, reversal, mean reversion, seasonality, event/flow, regime, relative value,
volatility, cross-asset) that a retail prop trader can execute, ideally one that helps pass the Alpha Capital
"Alpha Swing" $10k challenge faster (P1 +10%, P2 +5%, 10% static max loss, 5% daily loss, >= 3 trading days,
no time limit; 1:30 FX leverage, indices/metals allowed). Honest negatives are valuable: never force a result.

## Data (1-minute bid/ask, Dukascopy, continuous UTC minute grid; vol == 0 means no ticks that minute)
- 28 FX pairs (gjstrat.data MAJORS + MINORS) and XAUUSD: `data/<sym lower>_2010-01-01_2026-10-07.npz`, t0 2009-12-31.
- JPNIDXJPY, USATECHIDXUSD: `data/<sym lower>_2011-01-02_2026-10-07.npz`, t0 2011-09-18. Coverage is patchy
  before 2014 and Asian hours are missing 2015-2017 (check `vol > 0` before trusting a time).
- S&P 500 hourly bid candles: `data/hourly/USA500IDXUSD/<YYYY>_<MM>.bi5` (2012-2026, decode like run_index_replication.spx()).
- Rates: `rates/*.csv` (FRED; USD daily DFF, others monthly). gjstrat.swap.SwapModel.from_fred("rates", 1.0).
- Web works (FRED csv `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`, federalreserve.gov,
  ecb.europa.eu, boj.or.jp, rba.gov.au). Save anything downloaded under `data/extra/` and record the source URL.
- Load markets ONE AT A TIME (each ~650 MB in RAM) and `del` them; max `multiprocessing.Pool(2)` per script —
  4 CPUs are shared with another agent.

## Building blocks (read the code before use)
- `gjstrat.data.build_market(sym, start, end, "data/raw", cache)` / `load_market(cache)`; Market has bo/bh/bl/bc,
  ao/ah/al/ac, vol, pip, idx(ts), ts(i).
- `gjstrat.patterns`: `Signal(day, side, start_i, kind, level, expiry_i, sl_dist, tp_dist, exit_by_i, tag)` +
  `simulate(m, sig)` (market/limit/stop entry, SL/TP/time exit on real bid/ask); `daily_table(m)` (NY-close
  daily bars; atr20/sma50 are shifted = known before the day); `local_idx(m, day, hh, mm, tz)`, `utc_idx`;
  `is_gotobi`, `kth_last_weekday`, `month_end_usd_bid`, `gotobi_short`.
- Costs: FX `gjstrat.accounting.account(trades_sorted_by_(exit_i,entry_i), m, 10_000, commission=7,
  swap=SwapModel, sym=sym, slippage_pips=0.2)["R"]`; gold/indices `run_all_matrix.net_r(m, sym, trades, swap)`.
  Costs are mandatory in every result.
- Stats: `run_edge_hunt.PER` (design 2010-17, check 2018-23, holdout 2024-26), `per_stats(r, day)`,
  `run_usdjpy_sl.tstat`, `run_backtest.fmt_table`.
- Prop: `gjstrat.prop.prop_table(m, legs, mixes, **rules)`, `gjstrat.prop.instant_table` (Blueberry),
  `run_m3_addon.build_legs()` (current basket legs: vol-box, vol-gotobi, fade, M-3 USDJPY, M-3 others),
  `run_m3_addon.ALPHA` rules, `run_m3_addon.since(legs, day)`, `run_prop_risk_rules.make_rule(boost=1.5)`.
  Trades from another market can join a USDJPY-grid prop sim as namedtuples (day, entry_i, exit_i) shifted by
  `(m_other.t0 - m_usdjpy.t0)` minutes (see run_index_prop.py).

## Protocol (non-negotiable)
1. Write `run_alpha_<slug>.py` whose docstring states every rule and variant **before** running it
   (<= 12 variants per family; pick parameters from theory/literature, not from the data).
2. No look-ahead: signals may only use data available before the entry minute. Daily features come from
   `daily_table` shifted values or from closes strictly before the entry.
3. Survival bar per test: design (2010-17; indices from their start) t >= 2 AND avg R > 0 in 2018-23 AND in
   2024-26. For families applied to many markets, also report pooled results and the count of markets
   positive; say how many survivors luck alone would give (~0.6% of tests pass by chance).
4. Report for every test: trades, trades/month, win %, avg win / avg loss, avg R per period with t, last 3 years.
5. Outputs: `results/alpha_hunt/<slug>/REPORT.md` (+ csv). Do NOT git commit, do NOT edit existing files in
   gjstrat/ or existing run_*.py (new helper code goes in your own script).

## Already tested (do not repeat; build on them only if clearly different)
Box breakouts at many times on all 31 markets (05:00 IST green box works only on USDJPY, best with vol filter);
fade of failed box breaks (Version C, USDJPY +0.14R); London/Asian-range/prev-day/inside-bar/NR7/NY-ORB
breakouts; Frankfurt box; prev-day sweep reversal; Asian-range fade; trend pullback limit; quiet-hours
Bollinger fade; London 4pm fix fade/follow; month-end fix follow; ECB/NY-cut/gold-fix fades; Tokyo fix and
gotobi (works on USDJPY, vol filter helps); month-start Tokyo fix; CNY fix; Monday gap fill; NFP; Nikkei/Nasdaq
lead-lag vs USDJPY; flow atlas (600,912 clock x calendar x currency-strength mean tests; only 3 tradeable:
EURGBP month-end fix, USDJPY after US holiday, USD bid 11:00-12:00 UTC on the 3rd-last weekday = M-3);
round-number fade/breakout; Nasdaq turn-of-month / overnight / pre-holiday / intraday momentum (TOM weakly
positive everywhere); walk-forward "recent winners" rotation over ~500 streams (fails); logistic filter on the
box; prop risk rules (boost x1.5 until +4% is the only accepted speed-up).
Lesson so far: tight-stop intraday ideas die on costs (1-1.5 pip + spread); real edges are flows tied to
calendar/clock on USDJPY.
