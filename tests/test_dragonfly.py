"""Hand-built candle scenarios for the Dragonfly Intercept rules. Run: python -m pytest -q tests/test_dragonfly.py"""
import numpy as np
import pandas as pd
import pytest

from dragonfly.benchmarks import resolve
from dragonfly.data import aggregate_15m, to_hourly
from dragonfly.engine import Bars, Params, Position, manage_bar, run
from dragonfly.indicators import ema, hourly_to_15m, legs, trend_1h

SPREAD = 0.02
ATR = 0.10
T0 = pd.Timestamp("2024-01-03 08:00")        # Wednesday


def mk(candles, n=60, trend=1, spread=SPREAD, atr=ATR):
    """Bars from bid (o, h, l, c) tuples, padded with flat candles at the last close.
    Ask = bid + spread. ATR(15m) is fixed; trend is a constant or an array."""
    last = candles[-1][3]
    rows = list(candles) + [(last, last, last, last)] * (n - len(candles))
    o, h, l, c = (np.array(x, float) for x in zip(*rows))
    tr = np.full(n, trend, np.int8) if np.isscalar(trend) else np.asarray(trend, np.int8)
    a = np.full(n, atr)
    b = Bars(t=pd.date_range(T0, periods=n, freq="15min"), bo=o, bh=h, bl=l, bc=c,
             ao=o + spread, ah=h + spread, al=l + spread, ac=c + spread,
             usd_per_quote=np.full(n, 1 / 150), atr15=a, trend=tr)
    b.legs = legs(h, l, a)
    return b


# Canonical BUY leg: L = 99.90 (candle 1), H = 100.50 (candle 7), completion candle 8.
# Leg 0.60 = 6 x ATR. R=0.5 -> limit 100.20; stop 99.90 - max(0.02, 0.01) = 99.88; 78.6% = 100.0284
BUY_LEG = [
    (100.00, 100.02, 99.98, 100.00),   # 0 (outside the 8-candle window)
    (100.00, 100.05, 99.90, 100.00),   # 1  L
    (100.00, 100.10, 99.95, 100.08),   # 2
    (100.08, 100.18, 100.05, 100.15),  # 3
    (100.15, 100.25, 100.10, 100.22),  # 4
    (100.22, 100.32, 100.18, 100.30),  # 5
    (100.30, 100.40, 100.26, 100.38),  # 6
    (100.38, 100.50, 100.35, 100.45),  # 7  H
    (100.45, 100.45, 100.30, 100.35),  # 8  fails to make a higher high -> leg complete
]
FLAT = (100.35, 100.35, 100.35, 100.35)


def p_(**kw):
    return Params(**{"retrace": 0.5, "target": "T1", "spread": SPREAD, **kw})


# ------------------------------------------------------------------ leg detection
def test_leg_detected_on_completion_candle_with_frozen_values():
    b = mk(BUY_LEG)
    assert np.flatnonzero(b.legs["buy"]).tolist() == [8]
    assert b.legs["buy_H"][8] == pytest.approx(100.50)
    assert b.legs["buy_L"][8] == pytest.approx(99.90)


def test_leg_not_usable_before_completion_candle_closes():
    b = mk(BUY_LEG)
    # with data only up to candle 7 (the H candle) there is no leg yet
    h, l = b.bh[:8], b.bl[:8]
    assert not legs(h, l, np.full(8, ATR))["buy"].any()
    # the leg at 8 does not depend on anything after 8
    b2 = mk(BUY_LEG + [(100.35, 101.0, 99.0, 99.5)] * 5)
    for k in ("buy", "buy_H", "buy_L"):
        assert np.array_equal(b.legs[k][:9], b2.legs[k][:9], equal_nan=True)
    # an order placed at the completion close cannot fill on the completion candle itself,
    # even if that candle traded through the limit
    c = list(BUY_LEG)
    c[8] = (100.45, 100.45, 100.10, 100.30)      # dips through 100.20 intrabar, closes above 78.6%
    out = run(mk(c + [FLAT] * 3), p_())
    assert out["trades"].empty
    assert out["orders"].iloc[0]["outcome"] == "cancel_expired"


def test_leg_too_small_is_not_a_signal():
    b = mk(BUY_LEG, atr=0.31)                    # leg 0.60 < 2 x 0.31
    assert not b.legs["buy"].any()


def test_leg_requires_H_on_candle_before_completion():
    c = list(BUY_LEG) + [(100.35, 100.40, 100.30, 100.32)]   # 9: lower high again, H now 2 back
    b = mk(c)
    assert np.flatnonzero(b.legs["buy"]).tolist() == [8]


# ------------------------------------------------------------------ 1H trend filter
def _bars15(closes, start="2024-01-01 00:00"):
    idx = pd.date_range(start, periods=len(closes), freq="15min")
    c = np.asarray(closes, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"bo": o, "bh": np.maximum(o, c) + 0.01, "bl": np.minimum(o, c) - 0.01,
                         "bc": c}, index=idx)


def test_ema_matches_definition():
    x = np.arange(1.0, 61.0)
    e = ema(x, 50)
    assert np.isnan(e[48]) and e[49] == pytest.approx(x[:50].mean())
    assert e[50] == pytest.approx(e[49] + 2 / 51 * (x[50] - e[49]))


def test_15m_bar_sees_only_closed_1h_bars():
    t15 = pd.date_range("2024-01-01 10:00", periods=4, freq="15min")   # 10:00 10:15 10:30 10:45
    hours = pd.DatetimeIndex(["2024-01-01 09:00", "2024-01-01 10:00"])
    got = hourly_to_15m(t15, hours, np.array([1, 2]))
    # 10:00/10:15/10:30 bars close before 11:00 -> still the 09:00 bar; 10:45 closes at 11:00
    assert got.tolist() == [1, 1, 1, 2]


def test_trend_uses_only_closed_1h_bars():
    rng = np.random.default_rng(1)
    closes = 100 + np.cumsum(rng.normal(0.02, 0.05, 4 * 120))     # 120 hours, drifting up
    df = _bars15(closes)

    def trend15(d):
        h = to_hourly(d)
        return hourly_to_15m(d.index, h.index, trend_1h(h))

    base = trend15(df)
    assert (base == 1).any()
    # rewrite everything after bar i (inside the still-forming hour and beyond)
    for i in (300, 301, 302, 403):
        d2 = df.copy()
        d2.iloc[i + 1:, :] = d2.iloc[i + 1:, :] * 0.9
        assert np.array_equal(trend15(d2)[: i + 1], base[: i + 1])


def test_trend_flat_when_ema_slope_too_small():
    def hb(c):
        return pd.DataFrame({"o": c, "h": c + 0.5, "l": c - 0.5, "c": c})
    # close > EMA but the EMA rises far less than 0.1 x ATR (~1.0) over 5 bars -> flat
    assert (trend_1h(hb(np.linspace(100, 100.05, 80)))[60:] == 0).all()
    assert (trend_1h(hb(np.linspace(100, 120, 80)))[60:] == 1).all()
    assert (trend_1h(hb(np.linspace(120, 100, 80)))[60:] == -1).all()
    assert (trend_1h(hb(np.linspace(100, 120, 80)))[:54] == 0).all()     # EMA50 + 5 warm-up


def test_15m_aggregation_drops_zero_volume_minutes():
    idx = pd.date_range("2024-01-01 10:00", periods=30, freq="1min")
    bid = pd.DataFrame({"o": 1.0, "h": 1.1, "l": 0.9, "c": 1.0, "v": 1.0}, index=idx)
    bid.iloc[20:, :] = [5.0, 5.0, 5.0, 5.0, 0.0]          # 10:20-10:29: no ticks (flat filler)
    bid.iloc[16] = [1.0, 2.0, 0.5, 1.5, 1.0]
    ask = bid.assign(o=bid.o + 0.01, h=bid.h + 0.01, l=bid.l + 0.01, c=bid.c + 0.01)
    out = aggregate_15m(bid, ask)
    assert out.index.tolist() == [pd.Timestamp("2024-01-01 10:00"), pd.Timestamp("2024-01-01 10:15")]
    assert out.loc["2024-01-01 10:15", ["bh", "bl", "bc"]].tolist() == [2.0, 0.5, 1.0]


# ------------------------------------------------------------------ fills
def test_limit_fills_at_limit_intrabar():
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30)]           # ask low 100.17 <= 100.20
    tr = run(mk(c), p_())["trades"]
    assert tr.iloc[0]["entry_price"] == pytest.approx(100.20)
    assert not tr.iloc[0]["fill_gap"]


def test_limit_gap_fill_at_open():
    c = BUY_LEG + [(100.10, 100.15, 100.05, 100.12)]           # ask opens 100.12 < limit 100.20
    tr = run(mk(c), p_())["trades"]
    assert tr.iloc[0]["entry_price"] == pytest.approx(100.12)
    assert tr.iloc[0]["fill_gap"]
    assert tr.iloc[0]["entry_time"] == T0 + pd.Timedelta(minutes=15 * 9)


def test_stop_gap_fills_at_open():
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30), FLAT, (99.70, 99.80, 99.60, 99.75)]
    tr = run(mk(c), p_())["trades"].iloc[0]
    assert tr["exit_reason"] == "SL" and tr["exit_gap"]
    assert tr["exit_price"] == pytest.approx(99.70)          # bid open, below the 99.88 stop
    assert tr["R"] < -1


# ------------------------------------------------------------------ cancels
def test_cancel_after_12_candles():
    c = BUY_LEG + [FLAT] * 12 + [(100.35, 100.36, 100.10, 100.30)]   # touch on the 13th candle
    out = run(mk(c), p_())
    assert out["trades"].empty
    o = out["orders"].iloc[0]
    assert o["outcome"] == "cancel_expired"
    assert o["end_time"] == T0 + pd.Timedelta(minutes=15 * (8 + 12 + 1))


def test_touch_on_12th_candle_still_fills():
    c = BUY_LEG + [FLAT] * 11 + [(100.35, 100.36, 100.10, 100.30)]
    assert len(run(mk(c), p_())["trades"]) == 1


def test_cancel_on_close_beyond_786():
    # R=0.382 -> limit 100.2708 sits ABOVE the 78.6% level 100.0284. The completion candle closes
    # below 78.6% after dipping: the order is never placed live.
    c = list(BUY_LEG)
    c[8] = (100.45, 100.45, 100.00, 100.02)
    out = run(mk(c + [FLAT]), p_(retrace=0.382))
    assert out["orders"].iloc[0]["outcome"] == "cancel_786_at_signal"
    assert out["trades"].empty
    # a later candle closing below 78.6% cancels a live order; with bid/ask that candle has also
    # fired the limit, so the test uses a sell-side ask that never reached it: push the limit
    # out of reach with R=0.618 -> limit 100.1292, ask low must stay above it while bid closes
    # below 100.0284 -> needs a wide spread on that candle.
    b = mk(BUY_LEG + [FLAT] * 3)
    b.bo[9], b.bh[9], b.bl[9], b.bc[9] = 100.30, 100.30, 100.00, 100.01
    b.ao[9], b.ah[9], b.al[9], b.ac[9] = 100.40, 100.40, 100.15, 100.20   # ask low 100.15 > 100.1292
    out = run(b, p_(retrace=0.618))
    assert out["orders"].iloc[0]["outcome"] == "cancel_786"
    assert out["trades"].empty


def test_cancel_when_trend_turns_off():
    tr = np.ones(60, np.int8)
    tr[10] = 0                                       # 1H filter off at the close of candle 10
    c = BUY_LEG + [FLAT, FLAT, (100.35, 100.36, 100.10, 100.30)]  # touch on candle 11
    out = run(mk(c, trend=tr), p_())
    o = out["orders"].iloc[0]
    assert o["outcome"] == "cancel_trend"
    assert o["end_time"] == T0 + pd.Timedelta(minutes=15 * 11)
    assert out["trades"].empty


# ------------------------------------------------------------------ exits
def test_same_candle_sl_and_tp_resolves_to_sl():
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30), (100.30, 100.60, 99.80, 100.30)]
    tr = run(mk(c), p_())["trades"].iloc[0]
    assert tr["exit_reason"] == "SL"
    assert tr["exit_price"] == pytest.approx(99.88)
    assert tr["R"] == pytest.approx(-1.0)


def test_same_candle_sl_and_be_trigger_resolves_to_sl():
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30), (100.30, 100.55, 99.80, 100.30)]
    tr = run(mk(c), p_(target="T2"))["trades"].iloc[0]
    assert tr["exit_reason"] == "SL" and not tr["be_moved"]


def test_no_tp_on_fill_candle_but_sl_counts():
    c = BUY_LEG + [(100.35, 100.60, 100.15, 100.30), (100.30, 100.55, 100.25, 100.50)]
    tr = run(mk(c), p_())["trades"].iloc[0]
    assert tr["exit_time"] == T0 + pd.Timedelta(minutes=15 * 10)       # TP on the NEXT candle
    c = BUY_LEG + [(100.35, 100.60, 99.80, 100.30)]
    tr = run(mk(c), p_())["trades"].iloc[0]
    assert tr["exit_reason"] == "SL" and tr["exit_time"] == T0 + pd.Timedelta(minutes=15 * 9)


def test_tp_t1_and_t2_levels():
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30), (100.30, 100.51, 100.25, 100.50)]
    tr = run(mk(c), p_())["trades"].iloc[0]
    assert tr["exit_reason"] == "TP" and tr["exit_price"] == pytest.approx(100.50)
    assert tr["R"] == pytest.approx(0.30 / 0.32)
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30), (100.30, 100.81, 100.25, 100.80)]
    tr = run(mk(c), p_(target="T2"))["trades"].iloc[0]
    assert tr["exit_reason"] == "TP" and tr["exit_price"] == pytest.approx(100.80)


def test_break_even_skipped_when_target_under_1R():
    # R=0.382: entry 100.2708, stop 99.88 (1R = 0.3908), T1 = 100.50 is 0.2292 away < 1R
    c = BUY_LEG + [(100.35, 100.36, 100.25, 100.30), (100.30, 100.49, 100.28, 100.30),
                   (100.30, 100.30, 99.80, 99.90)]
    tr = run(mk(c), p_(retrace=0.382))["trades"].iloc[0]
    assert not tr["be_rule_on"] and not tr["be_moved"]
    assert tr["exit_reason"] == "SL" and tr["R"] == pytest.approx(-1.0)


def test_break_even_applied_when_target_beyond_1R():
    # R=0.5, T2: entry 100.20, stop 99.88, 1R = 0.32 -> trigger at 100.52; T2 = 100.80
    c = BUY_LEG + [(100.35, 100.36, 100.15, 100.30), (100.30, 100.53, 100.28, 100.40),
                   (100.40, 100.40, 100.10, 100.15)]
    tr = run(mk(c), p_(target="T2"))["trades"].iloc[0]
    assert tr["be_rule_on"] and tr["be_moved"]
    assert tr["exit_reason"] == "BE" and tr["exit_price"] == pytest.approx(100.20)
    assert tr["R"] == pytest.approx(0.0)


def test_small_stop_is_skipped_and_counted():
    out = run(mk(BUY_LEG + [FLAT]), p_(spread=0.11))     # dist 100.20-(99.90-0.11)=0.41 >= 0.33
    assert len(out["orders"]) == 1
    out = run(mk(BUY_LEG + [FLAT]), p_(spread=0.16))     # 100.20-99.74=0.46 < 3 x 0.16
    assert out["signals"]["outcome"].tolist() == ["skip_small_stop"]
    assert out["orders"].empty


# ------------------------------------------------------------------ mirror
def _mirror(b: Bars, C=200.0) -> Bars:
    """Price -> C - price, zero spread so bid/ask roles mirror exactly."""
    m = Bars(t=b.t, bo=C - b.bo, bh=C - b.bl, bl=C - b.bh, bc=C - b.bc,
             ao=C - b.bo, ah=C - b.bl, al=C - b.bh, ac=C - b.bc,
             usd_per_quote=b.usd_per_quote, atr15=b.atr15, trend=-b.trend)
    m.legs = legs(m.bh, m.bl, m.atr15)
    return m


def _random_bars(n=4000, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.standard_t(4, n) * 0.04)
    o = np.r_[100.0, c[:-1]]
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.03, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.03, n))
    tr = np.repeat(rng.choice([1, 0, -1], n // 40 + 1), 40)[:n].astype(np.int8)
    a = np.full(n, 0.08)
    b = Bars(t=pd.date_range(T0, periods=n, freq="15min"), bo=o, bh=h, bl=l, bc=c,
             ao=o.copy(), ah=h.copy(), al=l.copy(), ac=c.copy(), usd_per_quote=np.ones(n),
             atr15=a, trend=tr)
    b.legs = legs(h, l, a)
    return b


@pytest.mark.parametrize("retrace,target", [(0.382, "T1"), (0.5, "T2"), (0.618, "T2")])
@pytest.mark.parametrize("mode", ["limit", "chase"])
def test_sell_logic_mirrors_buy_logic(retrace, target, mode):
    b = _random_bars()
    m = _mirror(b)
    for k in ("buy", "sell"):
        other = "sell" if k == "buy" else "buy"
        assert np.array_equal(b.legs[k], m.legs[other])
    p = p_(retrace=retrace, target=target, mode=mode)
    x, y = run(b, p), run(m, p)
    tx, ty = x["trades"], y["trades"]
    assert len(tx) > 20 and (tx["side"] == "buy").any() and (tx["side"] == "sell").any()
    assert (tx["side"].map({"buy": "sell", "sell": "buy"}).to_numpy() == ty["side"].to_numpy()).all()
    for col in ("entry_time", "exit_time", "exit_reason", "be_moved"):
        assert (tx[col].to_numpy() == ty[col].to_numpy()).all(), col
    assert np.allclose(tx["R"], ty["R"])
    assert np.allclose(tx["entry_price"], 200 - ty["entry_price"])
    assert (x["orders"]["outcome"].to_numpy() == y["orders"]["outcome"].to_numpy()).all()
    assert (x["signals"]["outcome"].to_numpy() == y["signals"]["outcome"].to_numpy()).all()


def test_trend_filter_mirrors():
    rng = np.random.default_rng(5)
    c = 100 + np.cumsum(rng.normal(0, 0.3, 500))
    h = pd.DataFrame({"o": c, "h": c + 0.2, "l": c - 0.2, "c": c})
    hm = pd.DataFrame({"o": 200 - c, "h": 200 - c + 0.2, "l": 200 - c - 0.2, "c": 200 - c})
    assert np.array_equal(trend_1h(h), -trend_1h(hm))


# ------------------------------------------------------------------ one at a time
def test_one_pending_order_at_a_time():
    second = [(100.35, 100.36, 100.30, 100.33), (100.33, 100.60, 100.32, 100.55),
              (100.55, 100.70, 100.50, 100.65), (100.65, 100.65, 100.55, 100.60)]
    # candle 12 makes a new high 100.70 above the window's prior highs, 13 fails -> second leg
    b = mk(BUY_LEG + [FLAT, FLAT, FLAT] + second, atr=0.05)
    assert b.legs["buy"].sum() == 2
    out = run(b, p_())
    assert out["signals"]["outcome"].tolist() == ["placed", "skip_pending"]
    assert len(out["orders"]) == 1


def test_one_position_at_a_time():
    f30 = (100.30, 100.30, 100.30, 100.30)
    second = [(100.30, 100.38, 100.28, 100.36), (100.36, 100.45, 100.34, 100.44),
              (100.44, 100.44, 100.38, 100.40)]       # leg completes at 16 while the trade is open
    b = mk(BUY_LEG + [(100.35, 100.36, 100.15, 100.30)] + [f30] * 4 + second, atr=0.02)
    assert b.legs["buy"].sum() == 2
    out = run(b, p_())
    assert out["signals"]["outcome"].tolist() == ["placed", "skip_position"]
    assert len(out["trades"]) == 1


def test_new_signal_allowed_after_order_cancelled():
    c = BUY_LEG + [FLAT] * 12
    second = [(100.35, 100.36, 100.30, 100.33), (100.33, 100.60, 100.32, 100.55),
              (100.55, 100.70, 100.50, 100.65), (100.65, 100.65, 100.55, 100.60)]
    out = run(mk(c + second, atr=0.05), p_())
    assert out["signals"]["outcome"].tolist() == ["placed", "placed"]
    assert out["orders"]["outcome"].tolist()[0] == "cancel_expired"


# ------------------------------------------------------------------ benchmark consistency
@pytest.mark.parametrize("side", [1, -1])
@pytest.mark.parametrize("m", [0.6, 1.8])
def test_random_resolver_matches_engine_exit_logic(side, m):
    rng = np.random.default_rng(11)
    n = 3000
    c = 100 + np.cumsum(rng.normal(0, 0.05, n))
    o = np.r_[100.0, c[:-1]] + rng.normal(0, 0.02, n)        # some gaps
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.03, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.03, n))
    b = Bars(t=pd.date_range(T0, periods=n, freq="15min"), bo=o, bh=h, bl=l, bc=c,
             ao=o + 0.02, ah=h + 0.02, al=l + 0.02, ac=c + 0.02, usd_per_quote=np.ones(n),
             atr15=np.full(n, 0.1), trend=np.zeros(n, np.int8))
    d = 0.3
    entries = np.arange(0, 2000, 7)
    fast = resolve(b, entries, side, d, m)
    for e, r in zip(entries, fast):
        entry = b.ac[e] if side == 1 else b.bc[e]
        pos = Position(side, e, entry, entry - side * d, entry + side * m * d, d, m >= 1)
        for k in range(e + 1, n):
            ex = manage_bar(pos, b, k)
            if ex:
                assert r == pytest.approx(side * (ex[0] - entry) / d)
                break
