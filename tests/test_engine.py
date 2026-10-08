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
