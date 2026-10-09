"""Hand-built scenarios that pin down each strategy rule. Run: python -m pytest -q"""
import numpy as np
import pandas as pd
import pytest

from gjstrat.accounting import account, stats
from gjstrat.data import Market
from gjstrat.engine import IST, Params, run

DAY = pd.Timestamp("2024-01-03")      # Wednesday (IST)
SPREAD = 0.02                         # 2 pips


def flat_market(price=190.0):
    t0 = pd.Timestamp("2024-01-01")
    n = 4 * 1440
    a = np.full(n, price)
    return Market(t0=t0, bo=a.copy(), bh=a.copy(), bl=a.copy(), bc=a.copy(),
                  ao=a + SPREAD, ah=a + SPREAD, al=a + SPREAD, ac=a + SPREAD,
                  vol=np.ones(n), quote_per_usd=np.full(n, 150.0))


def i_of(m, hhmm, day=DAY):
    h, mi = map(int, hhmm.split(":"))
    return m.idx(day + pd.Timedelta(hours=h, minutes=mi) - IST)


def bar(m, hhmm, o, h, l, c, day=DAY):
    i = i_of(m, hhmm, day)
    m.bo[i], m.bh[i], m.bl[i], m.bc[i] = o, h, l, c
    m.ao[i], m.ah[i], m.al[i], m.ac[i] = o + SPREAD, h + SPREAD, l + SPREAD, c + SPREAD


def with_range(m):
    bar(m, "05:10", 190.0, 190.20, 190.0, 190.0)    # range high 190.20
    bar(m, "05:40", 190.0, 190.0, 189.80, 190.0)    # range low 189.80
    return m


def go(m, **kw):
    p = Params(**{**dict(rr=4, sl_pips=30, be_trigger=3, be_plus=5, version="A"), **kw})
    return run(m, p, days=[DAY])


def test_range_window_crosses_utc_midnight_and_ignores_outside_bars():
    m = with_range(flat_market())
    assert i_of(m, "05:00") == m.idx(pd.Timestamp("2024-01-02 23:30"))
    bar(m, "04:59", 190.0, 195.0, 185.0, 190.0)     # before window: must be ignored
    bar(m, "06:00", 190.0, 190.10, 189.90, 190.0)   # after window: must be ignored
    trades, c = go(m)
    assert c.traded_days == 1 and trades == [] and c.initial_expired == 1


def test_buy_breakout_to_tp():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)   # ask high 190.21 >= 190.20
    bar(m, "07:00", 190.0, 191.50, 190.0, 191.4)    # TP = 190.20 + 4*0.32 = 191.48
    (t,), c = go(m)
    assert (t.side, t.entry, t.reason) == ("BUY", 190.20, "TP")
    assert t.risk == pytest.approx(0.32) and t.r == pytest.approx(4.0)
    assert t.exit_i == i_of(m, "07:00")


def test_gap_through_buy_stop_fills_at_open():
    m = with_range(flat_market())
    bar(m, "06:10", 190.30, 190.35, 190.25, 190.30)   # ask open 190.32 > 190.20
    (t,), _ = go(m, be_trigger=None)
    assert t.entry == pytest.approx(190.32) and t.gap_fill


def test_level_already_crossed_at_0600_fills_at_market():
    m = with_range(flat_market())
    bar(m, "06:00", 190.19, 190.19, 190.19, 190.19)   # ask open 190.21 >= 190.20
    (t,), c = go(m, be_trigger=None)
    assert t.entry_i == i_of(m, "06:00") and t.entry == pytest.approx(190.21)
    assert c.open_fill_0600 == 1


def test_sl_first_when_sl_and_tp_in_same_bar():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "06:30", 190.0, 192.0, 189.50, 190.0)
    (t,), c = go(m)
    assert t.reason == "SL" and t.r == pytest.approx(-1.0)
    assert c.reentry_expired == 1       # A: sell stop parked at the 6-bar low 189.50, never hit


def test_gap_through_sl_fills_at_open():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "06:30", 189.60, 189.70, 189.55, 189.6)    # opens below SL 189.88
    t = go(m)[0][0]
    assert t.exit == pytest.approx(189.60) and t.r < -1


def test_sell_uses_ask_for_exits():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.0, 189.79, 189.85)     # bid low through 189.80 -> sell @189.80
    # SL = 189.80 + 0.32 = 190.12 on ASK -> bid high 190.10 is enough
    bar(m, "06:20", 190.0, 190.10, 190.0, 190.0)
    t = go(m)[0][0]
    assert (t.side, t.reason, t.exit) == ("SELL", "SL", pytest.approx(190.12))


def test_entry_bar_can_stop_out_but_not_take_profit():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 191.60, 189.80, 190.0)     # spans entry, SL and TP
    t = go(m)[0][0]
    assert t.reason == "SL" and t.exit_i == i_of(m, "06:10")


def test_break_even_moves_stop_from_next_bar():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "07:00", 190.0, 191.20, 190.0, 191.1)      # >= 3R (191.16): BE armed; low ignored this bar
    for i in range(i_of(m, "07:01"), i_of(m, "07:30")):
        m.bo[i] = m.bh[i] = m.bl[i] = m.bc[i] = 191.0
    bar(m, "07:30", 191.0, 191.0, 190.24, 190.3)      # BE stop 190.25 on bid
    t, *_ = go(m)[0]
    assert t.reason == "BE" and t.exit == pytest.approx(190.25)
    assert t.r == pytest.approx(0.05 / 0.32)


def test_reentry_version_a_uses_six_bar_extreme():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)     # buy @190.20, SL 189.88
    bar(m, "07:00", 189.95, 189.95, 189.85, 189.86)   # SL hit at 07:00
    bar(m, "07:03", 189.86, 189.86, 189.70, 189.75)   # window low 189.70 < range low 189.80
    bar(m, "07:06", 189.75, 189.75, 189.75, 189.75)   # 07:06 bar is outside the window
    for i in range(i_of(m, "07:07"), i_of(m, "08:00")):
        m.bo[i] = m.bh[i] = m.bl[i] = m.bc[i] = 189.75
        m.ao[i] = m.ah[i] = m.al[i] = m.ac[i] = 189.77
    bar(m, "08:00", 189.75, 189.75, 189.65, 189.66)   # sell stop at 189.70 triggers
    trades, c = go(m)
    assert [t.side for t in trades] == ["BUY", "SELL"]
    assert trades[1].entry == pytest.approx(189.70) and trades[1].num == 2
    assert trades[1].entry_i == i_of(m, "08:00")


def test_reentry_version_b_invalid_when_price_already_through():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "07:00", 189.95, 189.95, 189.85, 189.86)
    for i in range(i_of(m, "07:01"), i_of(m, "08:00")):   # parked below range low 189.80
        m.bo[i] = m.bh[i] = m.bl[i] = m.bc[i] = 189.75
        m.ao[i] = m.ah[i] = m.al[i] = m.ac[i] = 189.77
    trades, c = go(m, version="B")
    assert len(trades) == 1 and c.reentry_skipped_invalid == 1
    trades, c = go(m, version="A")                    # A: level = window low 189.75 -> still valid?
    # bid open at 07:06 is 189.75 == window low -> already at the level -> invalid too
    assert c.reentry_skipped_invalid == 1


def test_reentry_skipped_when_wait_runs_past_11():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "10:54", 189.95, 189.95, 189.85, 189.86)   # SL at 10:54 -> place at 11:00 -> skip
    trades, c = go(m)
    assert len(trades) == 1 and c.reentry_skipped_time == 1


def test_reentry_window_ending_before_11_is_allowed():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "10:53", 189.95, 189.95, 189.85, 189.86)   # place at 10:59: one bar to fill
    trades, c = go(m)
    assert c.reentry_skipped_time == 0 and c.reentry_expired == 1


def test_no_reentry_after_11_and_trade_survives_past_11():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "13:00", 189.95, 189.95, 189.85, 189.86)
    trades, c = go(m)
    assert len(trades) == 1 and trades[0].reason == "SL" and c.exit_after_11_no_reentry == 1


def test_orders_expire_at_11():
    m = with_range(flat_market())
    bar(m, "11:00", 190.0, 190.50, 190.0, 190.4)
    trades, c = go(m)
    assert trades == [] and c.initial_expired == 1


def test_no_reentry_after_tp_and_max_two_trades():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "06:30", 190.0, 191.50, 190.0, 191.4)
    assert len(go(m)[0]) == 1
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)     # buy, SL
    bar(m, "06:20", 189.9, 189.9, 189.80, 189.85)     # SL; window low == range low -> level 189.80
    bar(m, "06:40", 189.85, 189.85, 189.70, 189.75)   # sell @189.80 (risk .32 -> SL 190.12 ask)
    bar(m, "07:00", 190.0, 190.15, 190.0, 190.1)      # second trade SL
    trades, c = go(m)
    assert len(trades) == 2 and [t.reason for t in trades] == ["SL", "SL"]


def test_incomplete_range_is_skipped():
    m = with_range(flat_market())
    m.vol[i_of(m, "05:30")] = 0
    trades, c = go(m)
    assert c.skipped_incomplete == 1 and c.traded_days == 0


def test_accounting_risks_one_percent_and_rounds_lots():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)
    bar(m, "07:00", 190.0, 191.50, 190.0, 191.4)
    trades, _ = go(m)
    log = account(trades, m)
    # $100 risk / (32 pips * 1000/150 $) = 0.468 -> 0.46 lots; win 128 pips
    assert log.lots[0] == pytest.approx(0.46)
    assert log.pnl_usd[0] == pytest.approx(0.46 * 128 * 1000 / 150, abs=0.01)
    assert stats(log)["trades"] == 1


def test_accounting_handles_stop_on_entry_bar():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.30, 189.80, 190.0)     # entry and SL inside one bar
    trades, _ = go(m)
    log = account(trades, m)
    assert log.R[0] == pytest.approx(-1.0) and log.lots[0] > 0 and log.pnl_usd[0] < 0


# ----------------------------------------------------------------- Version C (fade the break)
def park(m, start, end, bid):
    for i in range(i_of(m, start), i_of(m, end)):
        m.bo[i] = m.bh[i] = m.bl[i] = m.bc[i] = bid
        m.ao[i] = m.ah[i] = m.al[i] = m.ac[i] = bid + SPREAD


def test_fade_buys_at_the_virtual_sell_stop_loss():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.0, 189.79, 189.85)     # low breaks: virtual sell @189.80, SL 190.12 (ask)
    bar(m, "07:00", 190.0, 190.10, 190.0, 190.05)     # ask high 190.12 -> virtual SL -> real BUY @190.12
    trades, c = go(m, version="C", be_trigger=None)
    (t,) = trades
    assert (t.side, t.num, t.entry, t.entry_i) == ("BUY", 1, pytest.approx(190.12), i_of(m, "07:00"))
    assert t.risk == pytest.approx(0.32) and c.fade_filled == 1


def test_fade_cancelled_when_virtual_trade_wins():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.0, 189.79, 189.85)
    bar(m, "07:00", 189.0, 189.0, 188.50, 188.6)      # virtual sell TP 189.80-1.28=188.52 (ask)
    bar(m, "08:00", 190.0, 190.20, 190.0, 190.1)      # later rally must not trigger anything
    trades, c = go(m, version="C", be_trigger=None)
    assert trades == [] and c.fade_cancel_tp == 1


def test_fade_stop_expires_at_11_unless_noexpiry():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.0, 189.79, 189.85)
    bar(m, "12:00", 190.0, 190.10, 190.0, 190.05)     # virtual SL only after 11:00
    trades, c = go(m, version="C", be_trigger=None)
    assert trades == [] and c.fade_expired == 1
    trades, c = go(m, version="C", be_trigger=None, fade_expiry_11=False)
    assert len(trades) == 1 and trades[0].side == "BUY" and trades[0].entry_i == i_of(m, "12:00")


def test_fade_reversal_stopped_before_11_gets_reentry():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.0, 189.79, 189.85)
    bar(m, "07:00", 190.0, 190.10, 190.0, 190.05)     # real BUY @190.12, SL 190.12-0.32=189.80 (bid)
    bar(m, "07:30", 189.9, 189.9, 189.75, 189.78)     # BUY stopped; 6-bar low 189.75 < range low
    park(m, "07:31", "08:00", 189.85)
    bar(m, "08:00", 189.85, 189.85, 189.70, 189.72)   # A-style sell stop @189.75 fills
    trades, c = go(m, version="C", be_trigger=None)
    assert [(t.side, t.num, t.reason) for t in trades][:2] == [("BUY", 1, "SL"), ("SELL", 2, trades[1].reason)]
    assert trades[1].entry == pytest.approx(189.75)


# ----------------------------------------------------------------- Version W (weekly bias)
from gjstrat.bias import weekly_bias


def weeks_market():
    """Flat 190.00 market, Mon 2024-01-01 .. Sat 2024-01-20, every minute live."""
    t0 = pd.Timestamp("2024-01-01")
    n = 20 * 1440
    a = np.full(n, 190.0)
    return Market(t0=t0, bo=a.copy(), bh=a.copy(), bl=a.copy(), bc=a.copy(), ao=a + SPREAD,
                  ah=a + SPREAD, al=a + SPREAD, ac=a + SPREAD, vol=np.ones(n),
                  quote_per_usd=np.full(n, 150.0))


def daily_close(m, ny_date, price):
    """Set the last minute before 17:00 New York (22:00 UTC in January) of a day."""
    i = m.idx(pd.Timestamp(ny_date) + pd.Timedelta(hours=21, minutes=59))
    m.bc[i] = price
    m.bh[i], m.bl[i] = max(m.bo[i], price), min(m.bo[i], price)


def test_weekly_bias_rules():
    m = weeks_market()
    i = m.idx(pd.Timestamp("2024-01-03 10:00"))
    m.bh[i] = 191.0                                   # week 1 high 191
    i = m.idx(pd.Timestamp("2024-01-04 10:00"))
    m.bl[i] = 189.0                                   # week 1 low 189
    daily_close(m, "2024-01-09", 191.5)               # Tue close above last week's high
    daily_close(m, "2024-01-11", 188.5)               # Thu close below last week's low
    days = [pd.Timestamp(f"2024-01-{d:02d}") for d in (3, 8, 9, 10, 11, 12)]
    b = weekly_bias(m, days)
    assert b[pd.Timestamp("2024-01-03")] is None      # no previous week
    assert b[pd.Timestamp("2024-01-08")] is None      # Monday: no daily close of this week yet
    assert b[pd.Timestamp("2024-01-09")] is None      # Mon close 190 is inside 189-191
    assert b[pd.Timestamp("2024-01-10")] == "BUY"     # Tue close 191.5 > 191
    assert b[pd.Timestamp("2024-01-11")] is None      # Wed close back inside -> bias off
    assert b[pd.Timestamp("2024-01-12")] == "SELL"    # Thu close 188.5 < 189: latest close wins


def test_version_w_trades_one_side_once():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.0, 189.79, 189.85)     # low breaks -> ignored on a BUY day
    bar(m, "06:30", 190.0, 190.19, 190.0, 190.15)     # buy stop 190.20 fills (ask high 190.21)
    bar(m, "07:00", 189.95, 189.95, 189.80, 189.86)   # buy SL 189.88 -> no re-entry in W
    bar(m, "07:30", 189.85, 189.85, 189.60, 189.65)
    trades, c = run(m, Params(version="W"), [DAY], bias={DAY: "BUY"})
    assert [(t.side, t.reason) for t in trades] == [("BUY", "SL")] and c.w_buy_days == 1
    trades, c = run(m, Params(version="W"), [DAY], bias={DAY: None})
    assert trades == [] and c.w_no_bias == 1
    trades, c = run(m, Params(version="W"), [DAY], bias={DAY: "SELL"})
    assert [t.side for t in trades] == ["SELL"] and trades[0].entry_i == i_of(m, "06:10")


# ----------------------------------------------------------------- SL scaled to the box
def test_box_scaled_stop_loss_and_break_even():
    m = with_range(flat_market())                     # box 189.80-190.20 = 40 pips
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)     # buy @190.20, risk = 0.40 + 0.02 = 0.42
    bar(m, "07:00", 190.0, 191.50, 190.0, 191.4)      # 3R = 191.46 -> BE armed (TP 191.88 not hit)
    park(m, "07:01", "07:30", 191.0)
    bar(m, "07:30", 191.0, 191.0, 190.20, 190.3)      # BE stop = 190.20 + 0.40*5/30 = 190.2667
    t, *_ = run(m, Params(sl_box_mult=1.0), [DAY])[0]
    assert t.risk == pytest.approx(0.42) and t.reason == "BE"
    assert t.exit == pytest.approx(190.20 + 0.40 * 5 / 30)
    assert Params(sl_box_mult=1.0).label == "RR4_SLbox1_BE3R+5_A"


# ----------------------------------------------------------------- swap
from gjstrat.swap import SwapModel


def flat_rates(usd, jpy, markup=0.0):
    idx = pd.date_range("2023-01-01", "2025-01-01", freq="D")
    return SwapModel({"USD": pd.Series(usd, idx), "JPY": pd.Series(jpy, idx)}, markup)


def test_rollover_count_and_wednesday_triple():
    # January: 17:00 New York = 22:00 UTC. Tue 10:00 -> Thu 10:00 crosses Tue (1) + Wed (3)
    r = SwapModel.rollovers(pd.Timestamp("2024-01-09 10:00"), pd.Timestamp("2024-01-11 10:00"))
    assert list(r["days"]) == [1, 3]
    assert r["utc"].iloc[0] == pd.Timestamp("2024-01-09 22:00")
    # July (EDT): rollover at 21:00 UTC; an intraday trade has none
    assert SwapModel.rollovers(pd.Timestamp("2024-07-09 20:59"), pd.Timestamp("2024-07-09 21:00")).shape[0] == 1
    assert SwapModel.rollovers(pd.Timestamp("2024-07-09 01:00"), pd.Timestamp("2024-07-09 20:00")).empty


def test_swap_sign_and_markup():
    a, b = pd.Timestamp("2024-01-09 10:00"), pd.Timestamp("2024-01-10 10:00")   # one Tue rollover
    long_, n = flat_rates(5.0, 0.0).swap_usd("USDJPY", "BUY", 1.0, a, b, 150.0)
    short, _ = flat_rates(5.0, 0.0).swap_usd("USDJPY", "SELL", 1.0, a, b, 150.0)
    assert n == 1 and long_ == pytest.approx(100_000 * 0.05 / 365) and short == pytest.approx(-long_)
    marked, _ = flat_rates(5.0, 0.0, markup=1.0).swap_usd("USDJPY", "BUY", 1.0, a, b, 150.0)
    assert marked == pytest.approx(100_000 * 0.04 / 365)


def test_account_books_swap_into_pnl_and_r():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)     # buy Wed 2024-01-03, exits Thu 07:00 IST
    i = i_of(m, "07:00", day=pd.Timestamp("2024-01-04"))
    m.bo[i], m.bh[i], m.bl[i], m.bc[i] = 190.0, 191.50, 190.0, 191.4
    m.ao[i], m.ah[i], m.al[i], m.ac[i] = 190.02, 191.52, 190.02, 191.42
    trades, _ = go(m)
    plain = account(trades, m)
    sw = account(trades, m, swap=flat_rates(5.0, 0.0), sym="USDJPY")
    assert sw.swap_nights[0] == 1                      # Wed 22:00 UTC rollover -> 3 days
    assert sw.swap_usd[0] == pytest.approx(0.46 * 100_000 * 0.05 * 3 / 365, abs=0.01)
    assert sw.pnl_usd[0] == pytest.approx(plain.pnl_usd[0] + sw.swap_usd[0], abs=0.02)
    assert sw.R[0] > plain.R[0]


# ----------------------------------------------------------------- relative small-box filter
def test_small_box_filter_uses_only_previous_days():
    m = weeks_market()
    days = [pd.Timestamp(f"2024-01-{d:02d}") for d in (2, 3, 4, 5)]
    for d, half in zip(days, (0.20, 0.20, 0.05, 0.20)):           # boxes 40, 40, 10, 40 pips
        bar(m, "05:10", 190.0, 190.0 + half, 190.0, 190.0, day=d)
        bar(m, "05:40", 190.0, 190.0, 190.0 - half, 190.0, day=d)
    p = Params(sl_box_mult=1.0, min_box_rel=0.5, box_lookback=2)
    _, c = run(m, p, days)
    assert c.skipped_small_box == 1                    # Jan 4: 10 < 0.5 x median(40, 40)
    # lookback 3: Jan 4 has no full window yet; Jan 5 window (40, 40, 10) -> median 40, 40 is fine
    _, c = run(m, Params(sl_box_mult=1.0, min_box_rel=0.5, box_lookback=3), days)
    assert c.skipped_small_box == 0


# ----------------------------------------------------------------- configurable box timing
def test_box_timing_is_configurable():
    m = flat_market()
    # box 09:00-09:59 IST, orders 10:00-12:00 (2 h)
    bar(m, "09:20", 190.0, 190.30, 190.0, 190.0)
    bar(m, "09:40", 190.0, 190.0, 189.70, 190.0)
    bar(m, "05:30", 190.0, 195.0, 185.0, 190.0)       # inside the default box, outside this one
    p = Params(box_start_min=9 * 60, order_hours=2, sl_box_mult=1.0)
    bar(m, "12:00", 190.0, 190.40, 190.0, 190.3)      # 12:00 = expiry bar: must NOT fill
    trades, c = run(m, p, [DAY])
    assert trades == [] and c.initial_expired == 1
    bar(m, "11:59", 190.0, 190.29, 190.0, 190.2)      # ask high 190.31 >= 190.30 -> buy
    trades, _ = run(m, p, [DAY])
    assert trades[0].side == "BUY" and trades[0].entry == pytest.approx(190.30)
    assert trades[0].range_pips == pytest.approx(60)  # 190.30 - 189.70


# ----------------------------------------------------------------- follow-through measure
from gjstrat.analysis import levels_before_stop


def test_levels_before_stop():
    m = with_range(flat_market())
    bar(m, "06:10", 190.0, 190.19, 190.0, 190.15)     # buy @190.20, 1R = 0.32 (SL 189.88)
    bar(m, "07:00", 190.0, 190.55, 190.0, 190.5)      # +1R = 190.52
    bar(m, "08:00", 190.0, 190.90, 190.0, 190.8)      # +2R = 190.84
    bar(m, "09:00", 190.0, 190.0, 189.80, 189.85)     # stop before +3R (191.16)
    t = run(m, Params(be_trigger=None), [DAY])[0][0]
    assert levels_before_stop(m, t) == 2


def test_swap_for_a_cross_uses_usd_notional():
    idx = pd.date_range("2023-01-01", "2025-01-01", freq="D")
    sw = SwapModel({"EUR": pd.Series(4.0, idx), "GBP": pd.Series(5.0, idx)}, 0.0)
    a, b = pd.Timestamp("2024-01-09 10:00"), pd.Timestamp("2024-01-10 10:00")
    # EURGBP 0.86, GBPUSD 1.27 -> quote_per_usd = 1/1.27; notional = 100k EUR = 100k*0.86*1.27 USD
    usd, n = sw.swap_usd("EURGBP", "BUY", 1.0, a, b, 0.86, 1 / 1.27)
    assert n == 1 and usd == pytest.approx(100_000 * 0.86 * 1.27 * (4.0 - 5.0) / 100 / 365)


# ----------------------------------------------------------------- general pattern simulator
from gjstrat.patterns import Signal, is_gotobi, simulate


def sig(m, side, start, kind="market", level=None, sl=0.20, tp=0.40, exit_hhmm="10:00"):
    return Signal(DAY, side, i_of(m, start), kind, level, i_of(m, "09:00"), sl, tp,
                  i_of(m, exit_hhmm))


def test_pattern_market_buy_hits_tp():
    m = flat_market()
    bar(m, "07:30", 190.0, 190.45, 190.0, 190.4)       # buy @ ask open 190.02 -> TP 190.42 (bid)
    t = simulate(m, sig(m, "BUY", "07:00"))
    assert (t.entry, t.reason, t.exit) == (pytest.approx(190.02), "TP", pytest.approx(190.42))


def test_pattern_sl_first_and_time_exit():
    m = flat_market()
    bar(m, "07:30", 190.0, 190.50, 189.80, 190.0)      # TP and SL both inside -> SL
    assert simulate(m, sig(m, "BUY", "07:00")).reason == "SL"
    m = flat_market()
    t = simulate(m, sig(m, "SELL", "07:00"))            # nothing happens -> exit 10:00 at ask
    assert t.reason == "TIME" and t.exit_i == i_of(m, "10:00") and t.exit == pytest.approx(190.02)


def test_pattern_limit_fills_at_level():
    m = flat_market()
    bar(m, "07:30", 190.0, 190.0, 189.85, 189.9)       # ask low 189.87 <= limit 189.90
    t = simulate(m, sig(m, "BUY", "07:00", kind="limit", level=189.90))
    assert t.entry == pytest.approx(189.90) and t.entry_i == i_of(m, "07:30")
    assert simulate(m, sig(m, "BUY", "07:00", kind="limit", level=189.80)) is None


def test_gotobi_days():
    assert is_gotobi(pd.Timestamp("2024-01-05"))       # Friday the 5th
    assert is_gotobi(pd.Timestamp("2024-02-09"))       # Sat 10th -> Fri 9th
    assert is_gotobi(pd.Timestamp("2024-01-31"))       # month end
    assert not is_gotobi(pd.Timestamp("2024-01-08"))


from gjstrat.data import synthetic_market
from gjstrat.patterns import daily_table, local_idx, london_fix_fade, month_end_days, ny_open_momentum


def test_local_idx_follows_daylight_saving():
    m = synthetic_market(days=200)
    winter, summer = pd.Timestamp("2024-01-15"), pd.Timestamp("2024-07-15")
    assert m.ts(local_idx(m, winter, 16, 0, "Europe/London")) == winter + pd.Timedelta(hours=16)
    assert m.ts(local_idx(m, summer, 16, 0, "Europe/London")) == summer + pd.Timedelta(hours=15)
    assert m.ts(local_idx(m, summer, 10, 0, "America/New_York")) == summer + pd.Timedelta(hours=14)


def test_month_end_days_and_flow_signals_have_no_lookahead():
    m = synthetic_market(days=200)
    d = daily_table(m)
    ends = month_end_days(d)
    assert pd.Timestamp("2024-05-31") in ends and pd.Timestamp("2024-06-28") in ends   # Jun 30 = Sun
    for s in london_fix_fade(m, d, (17, 0), 0.25):
        move = m.bo[s.start_i] - m.bo[s.start_i - 60]                     # the 15:00-16:00 move
        assert (s.side == "SELL") == (move > 0)
        assert s.exit_by_i - s.start_i == 60
    for s in ny_open_momentum(m, d, (16, 0), 0.5):
        assert (s.side == "BUY") == (m.bo[s.start_i] > m.bo[s.start_i - 30])
