"""Hand-built scenarios for the Nas100 opening-range breakout. Run: python -m pytest -q"""
import numpy as np
import pandas as pd
import pytest

from gjstrat.data import Market
from gjstrat.nas_orb import (Account, OrbParams, challenge, net_r, nyse_holidays, planned_loss,
                             run_day,
                             size, trading_days)

DAY = pd.Timestamp("2024-01-03")      # Wednesday, New York is UTC-5
SPREAD = 1.0
P = OrbParams(slip=0.0)


def flat_market(price=17000.0):
    t0 = pd.Timestamp("2024-01-02")
    n = 3 * 1440
    a = np.full(n, price)
    return Market(t0=t0, bo=a.copy(), bh=a.copy(), bl=a.copy(), bc=a.copy(),
                  ao=a + SPREAD, ah=a + SPREAD, al=a + SPREAD, ac=a + SPREAD,
                  vol=np.ones(n), quote_per_usd=np.ones(n), pip=1.0)


def i_of(m, hhmm):
    h, mi = map(int, hhmm.split(":"))
    return m.idx(DAY + pd.Timedelta(hours=h + 5, minutes=mi))


def bar(m, hhmm, o, h, l, c):
    i = i_of(m, hhmm)
    m.bo[i], m.bh[i], m.bl[i], m.bc[i] = o, h, l, c
    m.ao[i], m.ah[i], m.al[i], m.ac[i] = o + SPREAD, h + SPREAD, l + SPREAD, c + SPREAD


def with_range(m):
    bar(m, "09:31", 17000, 17050, 17000, 17000)    # range high 17050
    bar(m, "09:44", 17000, 17000, 16950, 17000)    # range low 16950
    return m


def set_price(m, hhmm, price):
    """Every bar from hhmm on flat at `price`."""
    i = i_of(m, hhmm)
    for a in (m.bo, m.bh, m.bl, m.bc):
        a[i:] = price
    for a in (m.ao, m.ah, m.al, m.ac):
        a[i:] = price + SPREAD


def test_range_is_0930_to_0944_only():
    m = with_range(flat_market())
    bar(m, "09:29", 17000, 17200, 16800, 17000)    # before the range: ignored
    bar(m, "09:45", 17000, 17040, 16960, 17000)    # first signal candle, inside
    what, t = run_day(m, DAY, P)
    assert what == "no_signal" and t is None


def test_wick_outside_is_not_a_signal_only_a_close():
    m = with_range(flat_market())
    bar(m, "09:47", 17000, 17100, 17000, 17000)    # wick above, candle closes inside
    assert run_day(m, DAY, P)[0] == "no_signal"


def test_buy_close_above_enters_next_open_and_hits_2r():
    m = with_range(flat_market())
    set_price(m, "09:49", 17060)                   # 09:45 candle closes 17060 > 17050
    (what, t) = run_day(m, DAY, P)
    assert what == "traded" and t.side == "BUY"
    assert t.signal_i == i_of(m, "09:45") and t.entry_i == i_of(m, "09:50")
    assert t.entry == 17061                        # ask open
    assert t.stop == 16950 and t.risk_pts == 111 and t.target == 17061 + 222
    bar(m, "10:20", 17060, 17290, 17060, 17200)
    _, t = run_day(m, DAY, P)
    assert (t.reason, t.exit) == ("TP", 17283) and t.exit_i == i_of(m, "10:20")


def test_sell_stop_triggers_on_ask_at_range_high():
    m = with_range(flat_market())
    set_price(m, "09:54", 16940)                   # 09:50 candle closes below 16950
    _, t = run_day(m, DAY, P)
    assert t.side == "SELL" and t.entry == 16940 and t.stop == 17050
    bar(m, "10:30", 16940, 17049.5, 16940, 16940)  # ask high 17050.5 >= 17050
    _, t = run_day(m, DAY, P)
    assert (t.reason, t.exit, t.exit_i) == ("SL", 17050, i_of(m, "10:30"))


def test_skip_when_next_open_is_back_inside():
    m = with_range(flat_market())
    bar(m, "09:49", 17000, 17060, 17000, 17060)    # closes above
    set_price(m, "09:50", 17040)                   # next open back inside
    assert run_day(m, DAY, P)[0] == "back_inside"


def test_only_first_signal_counts_and_last_candle_is_1055():
    m = with_range(flat_market())
    bar(m, "10:59", 17000, 17070, 17000, 17070)    # 10:55 candle closes above at 11:00
    set_price(m, "11:00", 17070)
    _, t = run_day(m, DAY, P)
    assert t.entry_i == i_of(m, "11:00")
    m = with_range(flat_market())
    bar(m, "11:04", 17000, 17070, 17000, 17070)    # 11:00 candle: too late
    assert run_day(m, DAY, P)[0] == "no_signal"


def test_time_exit_at_1130_open_and_same_bar_stop_first():
    m = with_range(flat_market())
    set_price(m, "09:49", 17060)
    set_price(m, "11:30", 17100)
    _, t = run_day(m, DAY, P)
    assert (t.reason, t.exit, t.exit_i) == ("TIME", 17100, i_of(m, "11:30"))
    m = with_range(flat_market())
    set_price(m, "09:49", 17060)
    bar(m, "10:00", 17060, 17400, 16900, 17000)    # target and stop in one minute
    _, t = run_day(m, DAY, P)
    assert t.reason == "SL"


def test_gap_through_stop_fills_at_open_with_slippage():
    m = with_range(flat_market())
    set_price(m, "09:49", 17060)
    set_price(m, "10:10", 16900)
    _, t = run_day(m, DAY, OrbParams(slip=1.0))
    assert t.entry == 17062 and t.reason == "SL" and t.exit == 16899 and t.gap


def test_missing_range_minute_skips_the_day():
    m = with_range(flat_market())
    m.vol[i_of(m, "09:40")] = 0
    assert run_day(m, DAY, P)[0] == "no_data"


def test_holidays():
    h = nyse_holidays(2021, 2024)
    for d in ["2021-07-05", "2022-06-20", "2022-12-26", "2023-04-07", "2024-11-28", "2021-12-24"]:
        assert pd.Timestamp(d) in h
    assert pd.Timestamp("2021-12-31") not in h     # Saturday New Year: no Friday closure
    assert pd.Timestamp("2024-01-03") in trading_days(pd.Timestamp("2024-01-01").date(),
                                                      pd.Timestamp("2024-01-05").date())


ACC = Account("t", 50_000, 2_000, True, 1_000, 3_000, 2.0, 1, 1.5)


def test_rule8_sizing_example():
    m = flat_market()
    bar(m, "09:31", 17000, 17005, 17000, 17000)
    bar(m, "09:44", 17000, 17000, 16995, 17000)
    set_price(m, "09:49", 17006)
    _, t = run_day(m, DAY, P)                      # ask entry 17007, stop 16995 -> 12 pts
    assert t.risk_pts == 12 and planned_loss(t, ACC) == (12 + 1) * 2 + 1.5
    assert size(t, ACC, 2_000, 1_000) == 1         # $50 budget, 1 MNQ = $27.5 at the stop
    assert size(t, ACC, 1_000, 1_000) == 0         # $25 budget < $27.5 -> skip
    assert size(t, ACC, 2_000, 27) == 0            # daily allowance left is the other cap
    assert t.reason == "TIME" and net_r(t, ACC) == pytest.approx((-1 * 2 - 1.5) / 27.5)


def test_challenge_trailing_floor_and_pass():
    class T:                                       # minimal stand-in for OrbTrade
        def __init__(self, pnl):
            self.pnl_pts, self.risk_pts = pnl, 9.0
    acc = Account("t", 1_000, 100, True, 1_000, 30, 1.0, 1, 0.0, risk_frac=0.5, est_slip=1.0)
    # budget 50 -> 5 contracts at $10 planned loss each
    assert challenge([T(2.0), T(2.0), T(2.0)], acc, 0)["result"] == "pass"
    r = challenge([T(-10.0)] * 30, acc, 0)
    assert r["result"] == "unfinished" and r["skipped"] > 0  # shrinking cushion -> no contract fits


def test_two_phase_challenge_min_days_and_daily_limit():
    class T:
        def __init__(self, pnl):
            self.pnl_pts, self.risk_pts = pnl, 9.0
    acc = Account("t", 1_000, 100, False, 0, 30, 1.0, 1, 0.0, risk_frac=0.5, est_slip=1.0,
                  target2=20, daily_frac=0.04, min_days=3)
    # budget min(50% cushion, 4% daily) -> 4 contracts; phase 1: +40 on day 1 is not enough
    # (3 days needed), passes on day 3; phase 2 restarts at 1,000 and needs 3 days of +12
    r = challenge([T(10.0)] + [T(3.0)] * 5, acc, 0)
    assert (r["result"], r["phase"], r["taken"]) == ("pass", 2, 6)
    assert challenge([T(10.0)] + [T(3.0)] * 4, acc, 0)["phase"] == 2
    assert challenge([T(10.0)], acc, 0)["result"] == "unfinished"     # target hit but 1 day < 3
    assert challenge([T(-10.0)], acc, 0)["result"] == "fail: daily"  # -40 = 4% of 1,000
    r = challenge([T(1.0)], acc, 0, fixed_risk=0.01)                   # $10 budget -> 1 contract
    assert r["taken"] == 1
