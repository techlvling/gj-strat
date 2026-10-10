"""Rule-by-rule tests for the zone + macro backtest, on small hand-made candles."""
import numpy as np
import pandas as pd
import pytest

from zonemacro import engine as E
from zonemacro import macro as MC
from zonemacro.prices import to_4h
from zonemacro.sources import first_releases
from zonemacro.zones import DEMAND, SUPPLY, find_zones

SPREAD = 0.02
T0 = pd.Timestamp("2024-06-03 00:00")          # a Monday


# --------------------------------------------------------------------------- helpers
def m15_from_rows(rows, start=T0, spread=SPREAD, atr=1.0) -> E.M15:
    """rows: list of bid (o, h, l, c). Ask = bid + spread."""
    a = np.array(rows, float)
    n = len(a)
    t = (pd.date_range(start, periods=n, freq="15min").to_numpy()
         .astype("datetime64[ns]").astype(np.int64))
    sh, sl = E.confirmed_swings(a[:, 1], a[:, 2])
    return E.M15(t=t, bo=a[:, 0], bh=a[:, 1], bl=a[:, 2], bc=a[:, 3], ao=a[:, 0] + spread,
                 ah=a[:, 1] + spread, al=a[:, 2] + spread, ac=a[:, 3] + spread,
                 spread=np.full(n, spread), atr=np.full(n, atr), sh=sh, sl=sl)


def path_15m(bars4h):
    """Expand 4H bid candles (o, h, l, c) into 16 15m candles each: o -> low -> high -> c for
    up candles, o -> high -> low -> c for down candles."""
    rows = []
    for o, h, l, c in bars4h:
        way = [o, l, h, c] if c >= o else [o, h, l, c]
        p = np.interp(np.arange(17), [0, 5, 10, 16], way)
        for i in range(16):
            rows.append((p[i], max(p[i], p[i + 1]), min(p[i], p[i + 1]), p[i + 1]))
    return rows


def frame(rows, start=T0, spread=SPREAD):
    a = np.array(rows, float)
    idx = pd.date_range(start, periods=len(a), freq="15min")
    df = pd.DataFrame(a, columns=["bo", "bh", "bl", "bc"], index=idx)
    for s in ("o", "h", "l", "c"):
        df["a" + s] = df["b" + s] + spread
    return df


def book(m, zones):
    """zones: list of (kind, top, bottom, active_idx, expiry_idx)."""
    k = np.array([z[0] for z in zones]); top = np.array([z[1] for z in zones], float)
    bot = np.array([z[2] for z in zones], float)
    a = np.array([z[3] for z in zones]); e = np.array([z[4] for z in zones])
    touch = np.full(len(zones), -1)
    for i in range(len(zones)):
        hit = m.al[a[i]:e[i]] <= top[i] if k[i] == DEMAND else m.bh[a[i]:e[i]] >= bot[i]
        if hit.any():
            touch[i] = a[i] + int(np.argmax(hit))
    return E.ZoneBook(k, top, bot, np.full(len(zones), 1.0), a, e, touch)


WARM = [(100.0, 101.0, 99.9, 100.8), (100.8, 100.9, 99.8, 100.0)] * 8      # big bodies
BASE = [(100.0, 100.4, 99.8, 100.1)]                                        # body 0.1 / range 0.6
IMPULSE = [(100.1, 103.0, 100.0, 102.9)]       # dips to 100.0 (inside the zone) before rallying
AFTER = [(102.9, 103.2, 102.0, 102.2), (102.2, 102.4, 101.0, 101.2), (101.2, 101.4, 100.2, 100.5)]


# --------------------------------------------------------------------------- zones
def test_zone_detection_full_and_body():
    b4 = to_4h(frame(path_15m(WARM + BASE + IMPULSE + AFTER)))
    atr = np.full(len(b4), 1.0)
    z, _ = find_zones(b4, k=2.0, mode="full", atr=atr)
    assert len(z) == 1
    r = z.iloc[0]
    assert r["kind"] == DEMAND and r["top"] == pytest.approx(100.4) and r["bottom"] == pytest.approx(99.8)
    imp_start = T0 + pd.Timedelta(hours=4 * 17)
    assert r["impulse"] == imp_start
    assert r["active_from"] == imp_start + pd.Timedelta(hours=4)        # after the impulse CLOSES
    zb, _ = find_zones(b4, k=2.0, mode="body", atr=atr)
    assert zb.iloc[0]["top"] == pytest.approx(100.1) and zb.iloc[0]["bottom"] == pytest.approx(100.0)
    # K=3: the move 103.0 - 100.4 = 2.6 ATR is not enough within 3 candles -> no zone
    z3, _ = find_zones(b4, k=3.0, mode="full", atr=atr)
    assert len(z3) == 0


def test_supply_zone_and_long_base_ignored():
    down = [(100.0, 100.1, 97.0, 97.1)]
    b4 = to_4h(frame(path_15m(WARM + BASE + down + AFTER)))
    z, _ = find_zones(b4, k=2.0, atr=np.full(len(b4), 1.0))
    assert len(z) == 1 and z.iloc[0]["kind"] == SUPPLY
    b4 = to_4h(frame(path_15m(WARM + BASE * 4 + IMPULSE + AFTER)))     # 4 small candles
    z, st = find_zones(b4, k=2.0, atr=np.full(len(b4), 1.0))
    assert len(z) == 0 and st["long_runs_ignored"] == 1


def test_zone_not_touchable_before_impulse_closes():
    rows = path_15m(WARM + BASE + IMPULSE + AFTER)
    df = frame(rows)
    b4 = to_4h(df)
    z, _ = find_zones(b4, k=2.0, atr=np.full(len(b4), 1.0))
    m = m15_from_rows(rows)
    zb = E.make_book(z, m)
    imp_first = 17 * 16                                   # first 15m bar of the impulse candle
    dip = imp_first + int(np.argmin(m.bl[imp_first:imp_first + 16]))
    assert m.al[dip] <= z.iloc[0]["top"]                  # price was inside the zone ...
    assert zb.a_idx[0] == imp_first + 16                  # ... but the zone was not active yet
    assert zb.touch[0] >= zb.a_idx[0]
    # the real first touch is in the last AFTER candle (low 100.2 + spread <= 100.4)
    assert zb.touch[0] >= (17 + 1 + 2) * 16


# --------------------------------------------------------------------------- macro timing
def test_daily_value_not_usable_before_next_day():
    df = pd.DataFrame({"date": pd.to_datetime(["2024-06-03", "2024-06-04"]), "value": [1.0, 2.0]})
    days = pd.to_datetime(["2024-06-03", "2024-06-04", "2024-06-05"])
    v = MC.daily_usable(df, days)
    assert np.isnan(v[0]) and v[1] == 1.0 and v[2] == 2.0


def test_cpi_first_release_only_and_release_timing():
    v1 = pd.DataFrame({"month": pd.to_datetime(["2024-01-01", "2024-02-01"]), "value": [300.0, 301.0]})
    v2 = pd.DataFrame({"month": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
                       "value": [300.5, 309.9, 302.0]})              # Feb revised in v2
    fr = first_releases([(pd.Timestamp("2024-03-12"), v1), (pd.Timestamp("2024-04-10"), v2)])
    feb = fr[fr["month"] == "2024-02-01"].iloc[0]
    assert feb["value"] == 301.0 and feb["release_date"] == pd.Timestamp("2024-03-12")
    mar = fr[fr["month"] == "2024-03-01"].iloc[0]
    assert mar["value"] == 302.0 and mar["release_date"] == pd.Timestamp("2024-04-10")
    # CPI released on 2024-04-10 is usable only from 2024-04-11
    days = pd.to_datetime(["2024-04-10", "2024-04-11"])
    u = MC.usable_values(fr["value"], fr["release_date"] + pd.Timedelta(days=1), days)
    assert u[0] == 301.0 and u[1] == 302.0
    # YoY uses first-release values for both legs
    base = pd.DataFrame({"month": pd.to_datetime(["2023-03-01"]), "value": [290.0],
                         "release_date": pd.to_datetime(["2023-04-12"])})
    yoy = MC.cpi_yoy_first_release(pd.concat([base, fr], ignore_index=True))
    assert yoy.iloc[-1]["yoy"] == pytest.approx((302.0 / 290.0 - 1) * 100)


def _synthetic_sources(jump_date):
    d = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    d = d[d.dayofweek < 5]
    step = (d >= jump_date).astype(float)
    flat = lambda v: pd.DataFrame({"date": d, "value": np.full(len(d), v)})
    cpi = pd.DataFrame({"month": pd.date_range("2022-01-01", "2024-12-01", freq="MS")})
    cpi["value"] = 300.0
    cpi["release_date"] = cpi["month"] + pd.DateOffset(months=1, days=11)
    return {"DGS2": pd.DataFrame({"date": d, "value": 4.0 + step}), "DFF": flat(5.0),
            "DGS10": pd.DataFrame({"date": d, "value": 4.0 + step}), "JGB10": flat(1.0),
            "BUND10": flat(2.0), "CPI_FIRST": cpi}


def test_bias_timing_and_usd_strong_maps_to_pair_side():
    jump = pd.Timestamp("2024-06-05")                     # Wednesday: DGS2 and DGS10 rise
    src = _synthetic_sources(jump)
    out = {}
    for pair in ("USDJPY", "EURUSD"):
        b = MC.macro_bias(src, pair, "2023-01-01", "2024-12-31")
        assert b.loc["2024-06-05", "usd_bias"] == 0        # obs dated 06-05 not usable on 06-05
        assert b.loc["2024-06-06", "usd_bias"] == 1        # decided at the close of 06-06
        assert b.loc["2024-06-06", "n_agree"] == 2
        f = MC.macro_filter(b, pair, "2024-01-01", "2024-12-31")
        idx = lambda s: int(f.day_index(np.array([pd.Timestamp(s).value]))[0])
        assert f.code[idx("2024-06-06")] == 0              # not yet
        out[pair] = f.code[idx("2024-06-07")]              # applies from the next day (T = obs + 2)
    assert out["USDJPY"] == 1                              # USD strong -> buy USDJPY (demand zones)
    assert out["EURUSD"] == -1                             # USD strong -> sell EURUSD (supply zones)


def test_friday_decision_covers_weekend_and_monday():
    dec = pd.Series([1, -1], index=pd.to_datetime(["2024-06-06", "2024-06-07"]))   # Thu, Fri
    code = MC.apply_next_day(dec, "2024-06-07", "2024-06-11")
    assert list(code) == [1, -1, -1, -1, -1]                # Fri(Thu dec), Sat, Sun, Mon, Tue(Mon none->Fri)


def test_63_day_change_score():
    x = np.concatenate([np.full(63, 1.0), [2.0, 0.5, 1.0]])
    s = MC.change_score(x)
    assert list(s[:63]) == [0] * 63 and list(s[63:]) == [1, -1, 0]


# --------------------------------------------------------------------------- 15m swings
def test_swing_high_not_usable_until_three_candles_after():
    h = np.array([1, 2, 3, 10, 3, 2, 1, 1, 1], float)
    l = h - 0.5
    sh, _ = E.confirmed_swings(h, l)
    assert np.isnan(sh[:6]).all()                          # swing at k=3, bars 4, 5 not enough
    assert sh[6] == 10                                     # known after bar k+3 = 6 closes


def test_version_B_cannot_trigger_on_unconfirmed_swing():
    # down into a demand zone [99.0, 99.5]; swing high 100.0 at bar 3 is confirmed at bar 6.
    rows = [(99.8, 99.85, 99.7, 99.75), (99.75, 99.8, 99.6, 99.65), (99.65, 99.7, 99.2, 99.3),
            (99.3, 100.0, 99.3, 99.9),                     # swing high candidate (k = 3)
            (99.9, 99.9, 99.4, 99.5), (99.5, 99.6, 99.3, 99.4), (99.4, 99.8, 99.4, 99.7),
            (99.7, 100.3, 99.7, 100.2),                    # first close above 100.0 after k+3
            ] + [(100.2, 100.3, 100.1, 100.2)] * 5
    m = m15_from_rows(rows, atr=1.0)
    assert np.isnan(m.sh[5]) and m.sh[6] == 100.0          # unusable until bar 6 has closed
    zb = book(m, [(DEMAND, 99.5, 99.0, 1, 50)])
    assert zb.touch[0] == 2
    c, _ = E.candidates(m, zb, "B", "2R")
    assert c.iloc[0]["entry_idx"] == 7
    assert c.iloc[0]["entry_price"] == pytest.approx(100.2 + SPREAD)       # buy at ask close
    # stop = lowest low since entering (99.2) - buffer (max(spread, 0.1 ATR) = 0.1)
    assert c.iloc[0]["stop"] == pytest.approx(99.2 - 0.1)


# --------------------------------------------------------------------------- exits
def test_same_candle_sl_and_tp_resolves_to_sl():
    rows = [(100, 100.1, 99.9, 100), (100, 103, 97, 100)]
    m = m15_from_rows(rows)
    j, px, reason = E.simulate_exit(m, +1, stop=99.0, tp=102.0, i=0, check_entry_bar=False)
    assert (j, reason, px) == (1, "SL", 99.0)
    j, px, reason = E.simulate_exit(m, -1, stop=101.0, tp=98.0, i=0, check_entry_bar=False)
    assert (j, reason, px) == (1, "SL", 101.0)


def test_gap_through_stop_fills_at_open():
    rows = [(100, 100.1, 99.9, 100), (98.5, 98.6, 98.0, 98.2)]
    m = m15_from_rows(rows)
    j, px, reason = E.simulate_exit(m, +1, stop=99.0, tp=102.0, i=0, check_entry_bar=False)
    assert reason == "SL" and px == 98.5                   # bid open, worse than the stop
    rows = [(100, 100.1, 99.9, 100), (101.5, 101.8, 101.4, 101.6)]
    m = m15_from_rows(rows)
    j, px, reason = E.simulate_exit(m, -1, stop=101.0, tp=98.0, i=0, check_entry_bar=False)
    assert reason == "SL" and px == pytest.approx(101.5 + SPREAD)          # ask open


def test_gap_through_limit_fills_at_open_and_normal_limit_at_price():
    # demand zone top 100.0, bottom 99.5. Bar 2 gaps down: ask opens at 99.8 (< limit 100.0)
    rows = [(100.5, 100.6, 100.4, 100.5), (100.5, 100.6, 100.4, 100.5),
            (99.78, 99.9, 99.7, 99.85)] + [(99.85, 101.5, 99.8, 101.4)] * 3
    m = m15_from_rows(rows, atr=1.0)
    c, _ = E.candidates(m, book(m, [(DEMAND, 100.0, 99.5, 1, 50)]), "A", "2R")
    t = c.iloc[0]
    assert t["entry_idx"] == 2 and t["entry_price"] == pytest.approx(99.78 + SPREAD)
    assert t["stop"] == pytest.approx(99.5 - 0.1)
    # no gap: ask low touches the limit mid-candle -> filled at the limit price
    rows[2] = (100.3, 100.35, 99.9, 100.2)
    m = m15_from_rows(rows, atr=1.0)
    c, _ = E.candidates(m, book(m, [(DEMAND, 100.0, 99.5, 1, 50)]), "A", "2R")
    assert c.iloc[0]["entry_price"] == pytest.approx(100.0)
    assert c.iloc[0]["reason"] == "TP"


def test_stop_under_two_spreads_is_skipped():
    rows = [(100.5, 100.6, 100.4, 100.5), (100.5, 100.6, 100.4, 100.5), (100.1, 100.2, 99.7, 100.0)]
    m = m15_from_rows(rows, spread=0.2, atr=0.1)
    m.spread[:] = 0.2                     # buffer = max(0.2, 0.01) -> stop 0.2 + 0.01 zone below
    c, _ = E.candidates(m, book(m, [(DEMAND, 100.0, 99.99, 1, 50)]), "A", "2R")
    assert c.iloc[0]["skip"] == E.SKIP_STOP


def test_opposite_zone_tp_and_fallback_and_under_1R():
    rows = [(100.3, 100.35, 100.25, 100.3)] * 2 + [(100.1, 100.2, 99.9, 100.0)] + [(100, 100.1, 99.95, 100)] * 4
    m = m15_from_rows(rows, atr=1.0)
    # demand 100.0/99.5 (R = 0.6). Supply zone near edge 101.5 -> TP 101.5 (2.5R)
    zb = book(m, [(DEMAND, 100.0, 99.5, 1, 50), (SUPPLY, 102.0, 101.5, 0, 50)])
    c, _ = E.candidates(m, zb, "A", "zone")
    assert c.iloc[0]["tp"] == pytest.approx(101.5) and not c.iloc[0]["tp_fallback"]
    zb = book(m, [(DEMAND, 100.0, 99.5, 1, 50), (SUPPLY, 100.5, 100.4, 0, 50)])
    c, _ = E.candidates(m, zb, "A", "zone")                 # 0.4 away < 1R -> skipped
    assert c.iloc[0]["skip"] == E.SKIP_TP
    zb = book(m, [(DEMAND, 100.0, 99.5, 1, 50), (SUPPLY, 102.0, 101.5, 5, 50)])  # not active yet
    c, _ = E.candidates(m, zb, "A", "zone")
    assert c.iloc[0]["tp_fallback"] and c.iloc[0]["tp"] == pytest.approx(100.0 + 2 * 0.6)


# --------------------------------------------------------------------------- swap
def test_wednesday_rollover_counts_three_days():
    r = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "value": [5.0]})
    q = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "value": [0.0]})
    sw = E.build_swap(r, q, "2024-06-01", "2024-06-30")
    ns = lambda s: np.array([pd.Timestamp(s).value])
    # Wed 2024-06-05 12:00 UTC -> Wed 23:00 UTC crosses the Wed 17:00 NY (21:00 UTC) rollover
    one = E.SwapTable.swap_r(sw, 1, ns("2024-06-05 12:00"), ns("2024-06-05 23:00"), 100.0, 1.0, markup=0.0)
    assert one[0] == pytest.approx(3 * 5.0 / 100 / 365 * 100.0)
    # Tue 12:00 -> Thu 12:00: Tue (1) + Wed (3) = 4 days; short pays the differential + markup
    two = sw.swap_r(-1, ns("2024-06-04 12:00"), ns("2024-06-06 12:00"), 100.0, 1.0, markup=0.5)
    assert two[0] == pytest.approx(4 * (-5.0 - 0.5) / 100 / 365 * 100.0)
    none = sw.swap_r(1, ns("2024-06-04 12:00"), ns("2024-06-04 20:00"), 100.0, 1.0, markup=0.0)
    assert none[0] == 0


# --------------------------------------------------------------------------- portfolio
def test_one_open_position_at_a_time_and_bias_filter():
    entry = [10, 20, 40, 50]
    exit_ = [30, 25, 45, 60]
    side = [1, 1, -1, 1]
    skip = [0, 0, 0, 0]
    taken, cnt = E.run_portfolio(entry, exit_, side, skip, [2, 2, 2, 2])
    assert taken == [0, 2, 3] and cnt["skipped_position_open"] == 1
    taken, cnt = E.run_portfolio(entry, exit_, side, skip, [1, 1, 1, 1])     # buys only
    assert taken == [0, 3] and cnt["filtered_by_bias"] == 1 and cnt["skipped_position_open"] == 1
    taken, cnt = E.run_portfolio(entry, exit_, side, skip, [0, 0, 0, 0])
    assert taken == [] and cnt["filtered_by_bias"] == 4


def test_stats_basic():
    s = E.stats(np.array([2.0, -1.0, -1.0, 2.0]))
    assert s["win_rate"] == 50 and s["profit_factor"] == 2 and s["expectancy_R"] == 0.5
    assert s["longest_losing_streak"] == 2
