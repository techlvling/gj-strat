"""Hand-built scenarios for the NY-open candle vs 12 EMA rule (gjstrat.candle)."""
import numpy as np
import pandas as pd
import pytest

from gjstrat.candle import CandleParams, atr5, direction_moves, ema5, run_candle
from gjstrat.data import Market

DAY = pd.Timestamp("2024-01-03")      # Wednesday, NY winter time: 09:30 NY = 14:30 UTC
SPREAD = 0.0001                       # 1 pip


def flat_market(price=1.1000):
    t0 = pd.Timestamp("2024-01-01")
    n = 4 * 1440
    a = np.full(n, price)
    return Market(t0=t0, bo=a.copy(), bh=a.copy(), bl=a.copy(), bc=a.copy(),
                  ao=a + SPREAD, ah=a + SPREAD, al=a + SPREAD, ac=a + SPREAD,
                  vol=np.ones(n), quote_per_usd=np.ones(n), pip=0.0001)


def i_of(m, hhmm, day=DAY):
    h, mi = map(int, hhmm.split(":"))
    return m.idx((day + pd.Timedelta(hours=h, minutes=mi)).tz_localize("America/New_York")
                 .tz_convert("UTC").tz_localize(None))


def bar(m, hhmm, o, h, l, c, day=DAY):
    i = i_of(m, hhmm, day)
    m.bo[i], m.bh[i], m.bl[i], m.bc[i] = o, h, l, c
    m.ao[i], m.ah[i], m.al[i], m.ac[i] = o + SPREAD, h + SPREAD, l + SPREAD, c + SPREAD


def up_candle(m):
    """09:30-09:34 candle: low 1.0990, close 1.1010 above a flat 1.1000 EMA; then 1.1010 flat."""
    bar(m, "09:30", 1.1000, 1.1000, 1.0990, 1.1000)
    bar(m, "09:34", 1.1000, 1.1012, 1.1000, 1.1010)
    a, b = i_of(m, "09:35"), i_of(m, "16:01")
    for arr in (m.bo, m.bh, m.bl, m.bc):
        arr[a:b] = 1.1010
    for arr in (m.ao, m.ah, m.al, m.ac):
        arr[a:b] = 1.1011
    return m


def go(m, **kw):
    return run_candle(m, CandleParams(**kw), [DAY])


def test_ny_open_maps_to_utc_with_dst():
    m = flat_market()
    assert i_of(m, "09:30") == m.idx(pd.Timestamp("2024-01-03 14:30"))
    assert i_of(m, "09:30", pd.Timestamp("2024-07-03")) == m.idx(pd.Timestamp("2024-07-03 13:30"))


def test_close_above_ema_buys_at_next_open_ask_with_candle_low_stop_and_tp():
    m = up_candle(flat_market())
    bar(m, "10:00", 1.1010, 1.1060, 1.1010, 1.1030)  # TP = 1.1011 + 2 * (1.1011 - 1.0990)
    (t,), c = go(m, rr=2)
    assert (t.side, t.entry, t.reason) == ("BUY", pytest.approx(1.1011), "TP")
    assert t.risk == pytest.approx(0.0021) and t.r == pytest.approx(2.0)
    assert t.entry_i == i_of(m, "09:35")


def test_close_below_ema_sells_with_stop_above_candle_high_plus_spread():
    m = flat_market()
    bar(m, "09:30", 1.1000, 1.1010, 1.1000, 1.1000)
    bar(m, "09:34", 1.1000, 1.1000, 1.0988, 1.0990)
    bar(m, "09:35", 1.0990, 1.0990, 1.0990, 1.0990)
    bar(m, "11:00", 1.0990, 1.1012, 1.0990, 1.1000)  # ask high 1.1013 > stop 1.1011
    (t,), _ = go(m, rr=2)
    assert (t.side, t.entry, t.reason) == ("SELL", pytest.approx(1.0990), "SL")
    assert t.exit == pytest.approx(1.1011) and t.r == pytest.approx(-1.0)


def test_stop_before_target_in_one_bar_and_entry_bar_cannot_take_profit():
    m = up_candle(flat_market())
    bar(m, "09:35", 1.1010, 1.1100, 1.1010, 1.1010)  # target inside the entry bar: ignored
    bar(m, "10:00", 1.1010, 1.1100, 1.0980, 1.1000)  # both on one bar -> stop
    (t,), _ = go(m, rr=2)
    assert (t.reason, t.exit_i) == ("SL", i_of(m, "10:00"))


def test_no_target_closes_at_16_00_open():
    m = up_candle(flat_market())
    bar(m, "16:00", 1.1020, 1.1020, 1.1020, 1.1020)
    (t,), _ = go(m, rr=None)
    assert (t.reason, t.exit_i, t.exit) == ("EOD", i_of(m, "16:00"), pytest.approx(1.1020))


def test_ema_trail_exits_at_next_open_after_a_5m_close_below_the_ema():
    m = up_candle(flat_market())
    bar(m, "09:44", 1.1010, 1.1010, 1.0995, 1.0995)  # 09:40-09:44 closes under the EMA
    bar(m, "09:45", 1.0996, 1.0996, 1.0996, 1.0996)
    (t,), _ = go(m, rr=None, ema_trail=True)
    assert (t.reason, t.exit_i, t.exit) == ("EMA", i_of(m, "09:45"), pytest.approx(1.0996))


def test_signal_candle_with_an_empty_minute_is_skipped():
    m = up_candle(flat_market())
    m.vol[i_of(m, "09:32")] = 0
    trades, c = go(m)
    assert trades == [] and c["no_data"] == 1


def test_ema_ignores_buckets_without_ticks():
    m = flat_market()
    m.vol[:] = 0
    m.vol[:10] = 1
    m.bc[4], m.bc[9] = 1.0, 2.0
    e = ema5(m, 12)
    assert e[1] == pytest.approx(1.0 + (2.0 - 1.0) * 2 / 13) and e[-1] == e[1]


def test_atr_floor_widens_a_stop_that_is_too_tight():
    m = up_candle(flat_market())
    atr = np.full(m.n // 5, 0.0010)
    (t,), _ = run_candle(m, CandleParams(rr=None, stop_atr=3), [DAY], atr=atr)
    assert t.risk == pytest.approx(0.0030)           # candle stop was 0.0021 away
    (t,), _ = run_candle(m, CandleParams(rr=None, stop_atr=1), [DAY], atr=atr)
    assert t.risk == pytest.approx(0.0021)           # candle stop already wider


def test_atr5_true_range_uses_previous_close():
    m = flat_market()
    m.bh[5:10], m.bl[5:10] = 1.1010, 1.0995
    m.bc[4] = 1.0980
    a = atr5(m, 1)
    assert a[1] == pytest.approx(1.1010 - 1.0980)


def test_direction_move_is_signed_mid_to_mid_in_pips():
    m = up_candle(flat_market())
    bar(m, "16:00", 1.1030, 1.1030, 1.1030, 1.1030)
    mv = direction_moves(m, [DAY], ema5(m))
    assert mv == pytest.approx([20.0])                # mid 1.10105 -> 1.10305
