"""Rule-by-rule tests for the Nasdaq overnight volume-profile strategy (nqvp). Hand-built bars.

Run: python -m pytest -q tests/test_nqvp.py
Times are "tod" = minutes after midnight ET of the trading day (09:30 = 570, prior 18:00 = -360).
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from nqvp.core import (Bias, atr15_at_close, bars15, drive_in, drive_out, find_bias,
                       obvious_level, swing_highs, swing_lows, value_area, volume_profile)
from nqvp.data import et_wall_clock, to_et
from nqvp.engine import Day, DayLimits, Variant, day_bias, prepare_day, run_day, simulate_exit

D = date(2024, 1, 10)            # a Wednesday
SPREAD = 1.0
TODS = range(-360, 975)          # 18:00 prior day .. 16:14 (the CFD closes 16:15)


# --------------------------------------------------------------------------- builders
def frame(bars: dict, d=D, spread=SPREAD, vol=None) -> pd.DataFrame:
    """bars: tod -> (o, h, l, c) MID prices. bid = mid - spread/2, ask = mid + spread/2."""
    tods = np.array(sorted(bars))
    o, h, l, c = (np.array([bars[t][k] for t in tods], float) for k in range(4))
    sp = np.broadcast_to(np.asarray(spread, float), o.shape)
    v = np.ones(len(tods)) if vol is None else np.array([vol.get(t, 1.0) for t in tods])
    idx = pd.Timestamp(d) + pd.to_timedelta(tods, unit="min")
    return pd.DataFrame({"bo": o - sp / 2, "bh": h - sp / 2, "bl": l - sp / 2, "bc": c - sp / 2,
                         "ao": o + sp / 2, "ah": h + sp / 2, "al": l + sp / 2, "ac": c + sp / 2,
                         "v": v}, index=idx)


def flat(price=1000.0, tods=TODS) -> dict:
    return {t: (price, price + 0.25, price - 0.25, price) for t in tods}


def day_of(bars, **kw) -> Day:
    day, info = prepare_day(frame(bars, **kw), D)
    assert day is not None, info
    day.atr15_at[:] = 1e9            # stop-width filter off unless a test sets it
    return day


def put_long_setup(bars, T, B, exit_kind):
    """Swing low at T (B-5); sweep T+11; deeper low T+12 (sweep extreme, gap vs T+10);
    drive-out T+13 closes B+0.2 -> long at ask B+0.7, stop B-24, 1R = 24.7.
    exit_kind: SL (T+14), BE (+1R at T+14, back to entry T+15), TP (2R at T+14), none."""
    bars[T] = (B, B + 0.25, B - 5, B)
    bars[T + 10] = (B, B + 0.25, B - 2, B - 1.8)
    bars[T + 11] = (B - 1.8, B - 1.7, B - 22, B - 21.5)           # big bearish, sweeps B-5
    bars[T + 12] = (B - 21.5, B - 21.4, B - 23, B - 22.5)         # high < low[T+10]: bearish gap
    bars[T + 13] = (B - 22.5, B + 0.5, B - 22.6, B + 0.2)         # big bullish drive-out
    if exit_kind == "SL":
        bars[T + 14] = (B, B + 0.25, B - 26, B - 25)
        return T + 15
    if exit_kind == "BE":
        bars[T + 14] = (B, B + 26, B - 1, B + 20)                 # bid high B+25.5 >= B+25.4
        bars[T + 15] = (B + 20, B + 20.5, B - 1, B)               # bid low <= entry B+0.7
        return T + 16
    if exit_kind == "TP":
        bars[T + 14] = (B, B + 51, B - 1, B + 50)                 # bid high >= B+50.1 (2R)
        return T + 15
    return T + 14


def staircase(kinds, T0=575, B0=1000.0, step=18, drop=40.0):
    bars, B = flat(B0), B0
    for k, kind in enumerate(kinds):
        end = put_long_setup(bars, T0 + k * step, B, kind)
        B -= drop
        for t in range(end, 975):
            bars[t] = (B, B + 0.25, B - 0.25, B)
    return bars


def mirror(bars, K=3000.0):
    return {t: (K - o, K - l, K - h, K - c) for t, (o, h, l, c) in bars.items()}


B2_LONG = Bias(1, "B2", 570)


# --------------------------------------------------------------------------- 1. profile
def test_volume_profile_spreads_volume_uniformly_over_bins():
    k0, prof = volume_profile(np.array([100.5]), np.array([102.2]), np.array([3.0]))
    assert k0 == 100 and prof.tolist() == [1.0, 1.0, 1.0]


def test_value_area_expands_one_bin_toward_heavier_pair_until_70pct():
    prof = np.array([1, 2, 3, 10, 4, 2, 1], float)         # bins 100..106
    lv = value_area(100, prof)
    # POC 103 (10). up2 = 4+2 = 6 > dn2 = 3+2 = 5 -> add 104 (14). up2 = 3 < dn2 = 5 -> add 102 (17)
    assert (lv.poc, lv.val, lv.vah) == (103.5, 102.0, 105.0)
    assert lv.coverage == pytest.approx(17 / 23) and lv.coverage >= 0.70
    assert (17 - 3) / 23 < 0.70                             # one bin fewer would not reach 70%


def test_profile_uses_only_overnight_bars_before_0930():
    rng = np.random.default_rng(1)
    bars = {t: (1000.3 + x, 1000.6 + x, 1000.1 + x, 1000.3 + x)
            for t, x in zip(TODS, rng.uniform(0, 8, len(TODS)))}
    bars[-361] = (1500.3, 1500.6, 1500.1, 1500.3)           # 17:59 prior day: outside the window
    bars[570] = (1100.3, 1100.6, 1100.1, 1100.3)            # 09:30 bar: outside the window
    vol = {-361: 1e6, 570: 1e6}
    base, _ = prepare_day(frame(bars, vol=vol), D)
    assert 1000 <= base.poc <= 1009
    bars[569] = (1200.3, 1200.6, 1200.1, 1200.3)            # 09:29 bar (closes 09:30): inside
    vol[569] = 1e6
    inc, _ = prepare_day(frame(bars, vol=vol), D)
    assert inc.poc == 1200.5
    on = (base.tod >= -360) & (base.tod < 570)
    k0, prof = volume_profile(base.l[on], base.h[on], base.v[on])
    inside = prof[int(base.val) - k0:int(base.vah) - k0].sum()
    assert inside / prof.sum() >= 0.70 and base.va_coverage == pytest.approx(inside / prof.sum())


# --------------------------------------------------------------------------- 2. 15m usability
def test_15m_bar_closed_only_at_its_end_and_built_from_its_own_minutes():
    tod = np.arange(540, 620)
    o = c = np.full(len(tod), 100.0)
    h, l = np.full(len(tod), 100.5), np.full(len(tod), 99.5)
    h[tod == 585] = 130.0                                   # 09:45 1m bar belongs to the 09:45 bar
    s15, o15, h15, l15, c15 = bars15(tod, o, h, l, c)
    assert h15[s15 == 570][0] == 100.5 and h15[s15 == 585][0] == 130.0
    atr = np.arange(len(s15), dtype=float)                 # ATR value = index of the 15m bar
    a = atr15_at_close(tod, s15, atr)
    k570 = int(np.flatnonzero(s15 == 570)[0])
    assert a[tod == 583][0] == k570 - 1                     # 09:43 bar closes 09:44: 09:30 bar open
    assert a[tod == 584][0] == k570                         # 09:44 bar closes 09:45: now usable


def test_bias_ignores_15m_bars_before_eligible_start():
    s = np.arange(540, 700, 15)
    h, l, c = np.full(len(s), 105.0), np.full(len(s), 101.0), np.full(len(s), 103.0)
    k = int(np.flatnonzero(s == 570)[0])
    l[k], c[k] = 99.0, 101.0                                # 09:30 bar sweeps VAL=100, closes back
    l[k - 1] = 98.0                                         # 09:15 bar (pre-open) sweeps too
    assert find_bias(s, h, l, c, 110, 100, 570, True) == Bias(1, "B1", 585)
    assert find_bias(s, h, l, c, 110, 100, 585, True) == Bias(0, "none", -1)


def test_no_entry_before_the_bias_bar_has_closed():
    bars = staircase(["TP"], T0=560)                        # drive-out 09:33, before 09:45
    assert run_day(day_of(bars), Variant(target="2R"), Bias(1, "B2", 585))[0] == []
    (tr,), _ = run_day(day_of(bars), Variant(target="2R"), Bias(1, "B2", 570))
    assert tr["entry_time"] == pd.Timestamp("2024-01-10 09:34")


# --------------------------------------------------------------------------- 3. bias rules
S = np.arange(570, 660, 15)                                 # 09:30 .. 10:45 starts
VAH, VAL = 110.0, 100.0


def fb(h, l, c, start=570, acc=True):
    return find_bias(S, np.asarray(h, float), np.asarray(l, float), np.asarray(c, float), VAH, VAL,
                     start, acc)


def test_b1_rejection_same_bar():
    assert fb([105] * 6, [99, 101, 101, 101, 101, 101], [101, 103, 103, 103, 103, 103]) == Bias(1, "B1", 585)


def test_b1_rejection_within_next_four_bars_and_not_after():
    lows, closes = [99, 99.2, 100.2, 101, 101, 101], [99.5, 99.8, 100.5, 103, 103, 103]
    assert fb([105] * 6, lows, closes, acc=False) == Bias(1, "B1", 615)
    # with acceptance on, the two closes below VAL (09:30, 09:45) confirm B2 short first
    assert fb([105] * 6, lows, closes) == Bias(-1, "B2", 600)
    # sweep at 09:30, closes stay at VAL (not above) without new lows, close above on bar 6 -> none
    assert fb([105] * 6, [99, 100, 100, 100, 100, 100], [99.5, 100, 100, 100, 100, 101]).kind == "none"


def test_b1_short_mirror_and_conflict():
    assert fb([111, 105, 105, 105, 105, 105], [101] * 6, [109, 103, 103, 103, 103, 103]) == Bias(-1, "B1", 585)
    assert fb([111, 105, 105, 105, 105, 105], [99, 101, 101, 101, 101, 101], [105] * 6).kind == "conflict"


def test_b2_acceptance_two_consecutive_closes():
    assert fb([115] * 6, [111] * 6, [112, 113, 113, 113, 113, 113]) == Bias(1, "B2", 600)
    assert fb([115] * 6, [111] * 6, [112, 113, 113, 113, 113, 113], start=585) == Bias(1, "B2", 615)
    assert fb([115] * 6, [111] * 6, [112, 113, 113, 113, 113, 113], acc=False).kind == "none"
    assert fb([99] * 6, [95] * 6, [98, 97, 97, 97, 97, 97]) == Bias(-1, "B2", 600)
    # not consecutive: the close back below VAH is a B1 short (rejection), never a B2 long
    assert fb([115, 109, 115, 109, 115, 109], [111, 105, 111, 105, 111, 105],
              [112, 108, 112, 108, 112, 108]) == Bias(-1, "B1", 600)


def test_bias_cannot_be_set_after_1100():
    s = np.arange(570, 720, 15)
    h, l, c = np.full(len(s), 105.0), np.full(len(s), 101.0), np.full(len(s), 103.0)
    l[s == 660], c[s == 660] = 99.0, 101.0                 # 11:00 bar: too late
    assert find_bias(s, h, l, c, VAH, VAL, 570, True).kind == "none"
    l[s == 645], c[s == 645] = 99.0, 101.0                 # 10:45 bar closes 11:00: allowed
    assert find_bias(s, h, l, c, VAH, VAL, 570, True) == Bias(1, "B1", 660)


# --------------------------------------------------------------------------- 4. swings
def test_swing_low_usable_only_after_five_more_bars_closed():
    low = np.full(40, 100.0)
    low[10] = 95.0
    sw = swing_lows(low)
    assert sw[10] and sw.sum() == 1
    assert np.isnan(obvious_level(low, sw, 15, 1)[0])      # bar 15 opens: bar 15 confirms, not closed
    assert obvious_level(low, sw, 16, 1) == (95.0, 10)     # bars 11..15 closed -> usable for bar 16
    low[17] = 94.0                                          # bar 17 traded below -> not intact
    assert np.isnan(obvious_level(low, swing_lows(low), 18, 1)[0])
    old = np.r_[low[:17], np.full(60, 100.0)]
    assert obvious_level(old, swing_lows(old), 70, 1) == (95.0, 10)        # bar 10 = t-60: in
    assert np.isnan(obvious_level(old, swing_lows(old), 71, 1)[0])          # bar 10 = t-61: out


def test_swing_needs_strictly_lower_than_five_each_side_and_takes_lowest():
    low = np.full(40, 100.0)
    low[8], low[14] = 95.0, 96.0
    low[20], low[24] = 97.0, 97.0                           # 24 is within 5 of 20 and equal: neither
    sw = swing_lows(low)
    assert sw[8] and sw[14] and not sw[20] and not sw[24]
    assert obvious_level(low, sw, 35, 1) == (95.0, 8)
    high = 200 - low
    assert obvious_level(high, swing_highs(high), 35, -1) == (105.0, 8)


# --------------------------------------------------------------------------- 5. drive in / out
def test_drive_in_gap_closest_to_sweep_and_body_threshold():
    n = 12
    o, c = np.full(n, 100.0), np.full(n, 100.0)
    h, l = np.full(n, 100.5), np.full(n, 99.5)
    atr = np.full(n, 2.0)
    h[4], l[2] = 99.0, 99.6                                 # gap A: bar 4 high < bar 2 low
    l[7], h[9] = 98.0, 97.0                                 # gap B: bar 9 high < bar 7 low (closer)
    o[8], c[8] = 100.0, 97.0                                # bearish body 3.0 = 1.5 x ATR exactly
    ok, gap = drive_in(o, h, l, c, atr, 11, 1)
    assert ok and gap == 98.0
    c[8] = 97.01                                            # body 2.99 < 3.0
    assert drive_in(o, h, l, c, atr, 11, 1) == (False, 98.0)
    c[8], h[9], h[4] = 97.0, 98.5, 100.5                    # no gap at all
    assert drive_in(o, h, l, c, atr, 11, 1)[0] is False


def test_drive_in_window_is_ten_bars_ending_at_sweep_extreme():
    n = 20
    o, c, h, l = np.full(n, 100.0), np.full(n, 100.0), np.full(n, 100.5), np.full(n, 99.5)
    atr = np.full(n, 2.0)
    h[7], l[5] = 99.0, 99.6                                 # gap with bar1 = 5
    o[9], c[9] = 100.0, 96.0
    assert drive_in(o, h, l, c, atr, 14, 1)[0]              # window 5..14
    assert not drive_in(o, h, l, c, atr, 15, 1)[0]          # window 6..15: bar 5 gone


def test_drive_out_body_and_close_above_gap_top():
    o, c, atr = np.array([90.0]), np.array([93.0]), np.array([2.0])
    assert drive_out(o, c, atr, 0, 1, 92.9)
    assert not drive_out(o, c, atr, 0, 1, 93.0)             # must close ABOVE the gap top
    assert not drive_out(o, np.array([92.99]), atr, 0, 1, 92.0)   # body 2.99 < 3.0


def test_full_long_setup_enters_at_ask_with_stop_below_sweep_minus_spread():
    (tr,), cnt = run_day(day_of(staircase(["TP"])), Variant(target="2R"), B2_LONG)
    assert tr["side"] == "LONG" and tr["entry_time"] == pd.Timestamp("2024-01-10 09:49")
    assert tr["entry_price"] == pytest.approx(1000.7) and tr["stop_price"] == pytest.approx(976.0)
    assert tr["stop_dist"] == pytest.approx(24.7) and tr["exit_reason"] == "TP"
    assert tr["R"] == pytest.approx(2.0) and cnt["sweep_extreme_updated"] == 1


# --------------------------------------------------------------------------- 6. 5-bar clock
def clock_bars(drive_out_at):
    bars, B, T = flat(), 1000.0, 575
    put_long_setup(bars, T, B, "none")                      # extreme at T+12 (low B-23)
    bars[T + 13] = (B - 22.5, B - 22.3, B - 22.8, B - 22.6)  # small, no new low
    bars[T + 14] = (B - 22.6, B - 22.5, B - 25, B - 24.5)    # lower low: extreme moves, clock restarts
    for t in range(T + 15, T + drive_out_at):
        bars[t] = (B - 24.5, B - 24, B - 24.9, B - 24.2)
    bars[T + drive_out_at] = (B - 24, B + 0.5, B - 24.3, B + 0.2)
    return bars


def test_lower_sweep_low_restarts_the_five_bar_clock():
    (tr,), cnt = run_day(day_of(clock_bars(18)), Variant(target="2R"), B2_LONG)
    # T+18 is 6 bars after the first extreme (T+12) but 4 after the new one (T+14)
    assert tr["entry_time"] == pd.Timestamp("2024-01-10 09:54") and cnt["sweep_extreme_updated"] == 2
    assert tr["sweep_extreme"] == pytest.approx(975.0)


def test_setup_dies_six_bars_after_the_latest_extreme():
    trades, cnt = run_day(day_of(clock_bars(20)), Variant(target="2R"), B2_LONG)
    assert trades == [] and cnt["died_no_drive_out_5bars"] == 1


# --------------------------------------------------------------------------- 7. fills
def exit_day(rows):
    tod = np.arange(len(rows))
    o, h, l, c = (np.array([r[k] for r in rows], float) for k in range(4))
    s = SPREAD / 2
    return Day(date=D, tod=tod, o=o, h=h, l=l, c=c, bo=o - s, bh=h - s, bl=l - s, bc=c - s,
               ao=o + s, ah=h + s, al=l + s, ac=c + s, v=np.ones(len(rows)), e_end=len(rows))


def test_gap_through_stop_fills_at_open():
    d = exit_day([(1000, 1000, 1000, 1000), (985.5, 986, 980, 984)])     # bid open 985 < stop 990
    assert simulate_exit(d, 1, 1, 1000.0, 990.0, 1020.0, 10.0, False) == (1, 985.0, "SL")
    d = exit_day([(1000, 1000, 1000, 1000), (1014.5, 1016, 1013, 1015)])  # ask open 1015 > stop 1010
    assert simulate_exit(d, -1, 1, 1000.0, 1010.0, 980.0, 10.0, False) == (1, 1015.0, "SL")


def test_same_bar_sl_and_tp_resolves_to_sl():
    d = exit_day([(1000, 1000, 1000, 1000), (1000.5, 1021.5, 988.5, 1000)])
    assert simulate_exit(d, 1, 1, 1000.0, 990.0, 1020.0, 10.0, False) == (1, 990.0, "SL")
    assert simulate_exit(d, -1, 1, 1000.0, 1010.0, 980.0, 10.0, False) == (1, 1010.0, "SL")


def test_same_bar_sl_and_be_trigger_resolves_to_sl_and_be_stop_live_next_bar():
    d = exit_day([(1000, 1000, 1000, 1000), (1000.5, 1011.5, 988.5, 1000)])
    assert simulate_exit(d, 1, 1, 1000.0, 990.0, 1020.0, 10.0, True) == (1, 990.0, "SL")
    # trigger and a touch of entry in the same bar: BE stop not live yet; next bar hits it
    d = exit_day([(1000, 1000, 1000, 1000), (1000.5, 1011.5, 999, 1005), (1005, 1006, 999.5, 1000)])
    assert simulate_exit(d, 1, 1, 1000.0, 990.0, 1020.0, 10.0, True) == (2, 1000.0, "BE")


def test_tp_limit_and_eod_exit():
    d = exit_day([(1000, 1000, 1000, 1000), (1030.5, 1031, 1029, 1030)])  # gaps over TP: fill at TP
    assert simulate_exit(d, 1, 1, 1000.0, 990.0, 1020.0, 10.0, False) == (1, 1020.0, "TP")
    d = exit_day([(1000, 1000, 1000, 1000)] * 3 + [(1004, 1005, 1003, 1004.5)])
    assert simulate_exit(d, 1, 1, 1000.0, 990.0, 1020.0, 10.0, False) == (3, 1004.0, "EOD")


# --------------------------------------------------------------------------- 8. daily limits
def test_day_limits_class():
    lim = DayLimits()
    for r in ("SL", "BE", "BE"):
        lim.record(r)
    assert not lim.done and lim.consec_sl == 1
    lim.record("SL")
    assert lim.done == "2SL"
    lim = DayLimits()
    lim.record("TP")
    assert lim.done == "TP"


def test_two_stop_losses_end_the_day_and_be_counts_as_neither():
    v = Variant(target="2R", be=True)
    trades, cnt = run_day(day_of(staircase(["SL", "BE", "SL", "TP"])), v, B2_LONG)
    assert [t["exit_reason"] for t in trades] == ["SL", "BE", "SL"] and cnt["day_done_2SL"] == 1
    assert [round(t["R"], 9) for t in trades] == [-1.0, 0.0, -1.0]
    trades, cnt = run_day(day_of(staircase(["BE", "BE", "SL", "TP"])), v, B2_LONG)
    assert [t["exit_reason"] for t in trades] == ["BE", "BE", "SL", "TP"] and cnt["day_done_TP"] == 1


def test_tp_ends_the_day():
    trades, cnt = run_day(day_of(staircase(["TP", "TP"])), Variant(target="2R"), B2_LONG)
    assert len(trades) == 1 and cnt["day_done_TP"] == 1


# --------------------------------------------------------------------------- 9. mirrors
def assert_mirrored(a, b, K=3000.0):
    assert len(a) == len(b)
    for x, y in zip(a, b):
        assert {x["side"], y["side"]} == {"LONG", "SHORT"}
        for k in ("entry_time", "exit_time", "exit_reason", "bias_type"):
            assert x[k] == y[k]
        for k in ("R", "stop_dist", "reward_R", "r_opp"):
            assert x[k] == pytest.approx(y[k], abs=1e-9)
        for k in ("entry_price", "exit_price", "stop_price", "tp_price"):
            assert x[k] == pytest.approx(K - y[k], abs=1e-9)


def test_short_setups_mirror_long_setups_exactly():
    bars = staircase(["BE", "BE", "SL", "TP"])
    v = Variant(target="2R", be=True)
    a, _ = run_day(day_of(bars), v, B2_LONG)
    b, _ = run_day(day_of(mirror(bars)), v, Bias(-1, "B2", 570))
    assert len(a) == 4 and all(t["side"] == "SHORT" for t in b)
    assert_mirrored(a, b)


def random_walk_bars(seed):
    rng = np.random.default_rng(seed)
    n = len(TODS)
    c = 20000.37 + np.cumsum(rng.standard_t(3, n) * rng.choice([1.0, 4.0], n, p=[0.8, 0.2]))
    o = np.r_[20000.37, c[:-1]]
    w = np.abs(rng.normal(0, 1.2, (2, n)))
    h, l = np.maximum(o, c) + w[0], np.minimum(o, c) - w[1]
    bars = {t: (o[i], h[i], l[i], c[i]) for i, t in enumerate(TODS)}
    return bars, rng.uniform(0.5, 2.0, n), dict(zip(TODS, rng.uniform(0.2, 3.0, n)))


def test_random_days_mirror_exactly_in_every_mode():
    K, sides, kinds = 40000.0, set(), set()
    variants = [Variant(mode="nofilter"), Variant(mode="nofilter", be=True),
                Variant(), Variant(start=585, target="2R", acceptance=False, be=True)]
    for seed in range(150):
        bars, sp, vol = random_walk_bars(seed)
        a_day, _ = prepare_day(frame(bars, spread=sp, vol=vol), D)
        b_day, _ = prepare_day(frame(mirror(bars, K), spread=sp, vol=vol), D)
        assert b_day.poc == pytest.approx(K - a_day.poc)
        assert (b_day.vah, b_day.val) == pytest.approx((K - a_day.val, K - a_day.vah))
        for v in variants:
            ba, bb = day_bias(a_day, v), day_bias(b_day, v)
            assert (bb.side, bb.kind, bb.active) == (-ba.side, ba.kind, ba.active)
            a, _ = run_day(a_day, v, ba)
            b, _ = run_day(b_day, v, bb)
            assert_mirrored(a, b, K)
            sides |= {t["side"] for t in a}
            kinds |= {t["exit_reason"] for t in a}
    assert sides == {"LONG", "SHORT"} and {"SL", "TP", "BE"} <= kinds   # 38 trades, not vacuous


# --------------------------------------------------------------------------- 10. time zone
def test_utc_to_new_york_around_dst_changes():
    utc = pd.DatetimeIndex(["2024-03-08 14:30", "2024-03-11 13:30",      # spring forward 3/10
                            "2024-11-01 13:30", "2024-11-04 14:30"], tz="UTC")   # fall back 11/3
    et = to_et(utc)
    assert [t.strftime("%H:%M") for t in et] == ["09:30"] * 4
    assert [t.utcoffset().total_seconds() / 3600 for t in et] == [-5, -4, -4, -5]


@pytest.mark.parametrize("monday,first_utc", [("2024-03-11", "2024-03-10 22:00"),   # EDT from 3/10
                                              ("2024-11-04", "2024-11-03 23:00"),   # EST from 11/3
                                              ("2024-03-08", "2024-03-07 23:00")])  # Friday, EST
def test_overnight_window_starts_1800_new_york_across_dst(monday, first_utc):
    utc = pd.date_range(pd.Timestamp(first_utc, tz="UTC") - pd.Timedelta(hours=2), periods=24 * 60, freq="1min")
    df = pd.DataFrame({k: 20000.3 + np.arange(len(utc)) % 7 for k in
                       ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")}, index=et_wall_clock(utc))
    df["v"] = 1.0
    day, info = prepare_day(df, pd.Timestamp(monday).date())
    assert info["on_bars"] == 930                          # 18:00 .. 09:29 = 15.5 h of minutes
    first = df.index[day.tod >= -360][0]
    assert first == pd.Timestamp(monday) - pd.Timedelta(hours=6)
    assert to_et(pd.DatetimeIndex([pd.Timestamp(first_utc, tz="UTC")]))[0].hour == 18


# --------------------------------------------------------------------------- day skips
def test_skip_days_with_thin_overnight_or_premarket_gap():
    bars = {t: v for t, v in flat().items() if t >= 220}    # overnight only from 03:40 (350 bars)
    assert prepare_day(frame(bars), D)[1]["skip"] == "overnight_lt_6h"
    bars = {t: v for t, v in flat().items() if not 480 <= t < 511}   # 31-minute hole 08:00-08:30
    assert prepare_day(frame(bars), D)[1]["skip"] == "gap_gt_30m_0700_0930"
    bars = {t: v for t, v in flat().items() if not 480 <= t < 510}   # 30 minutes: allowed
    assert prepare_day(frame(bars), D)[1]["skip"] == ""
