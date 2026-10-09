"""Fade-the-impulse rules on hand-made candles."""
import numpy as np
import pytest

from test_zone_macro import BASE, IMPULSE, SPREAD, WARM, frame, m15_from_rows, path_15m
from zonemacro import engine as E
from zonemacro.fade import fade_candidates
from zonemacro.prices import to_4h
from zonemacro.zones import find_zones


def setup(after):
    rows = path_15m(WARM + BASE + IMPULSE + after)
    b4 = to_4h(frame(rows))
    atr = np.full(len(b4), 1.0)
    z, _ = find_zones(b4, k=2.0, mode="full", atr=atr)
    return m15_from_rows(rows), b4, z, atr


AFTER = [(102.9, 103.2, 102.0, 102.2),       # bearish: confirmation candle, makes a new high first
         (102.2, 102.4, 101.0, 101.2), (101.2, 101.4, 100.2, 100.5)]


def test_fade_at_impulse_close_sells_at_bid_with_stop_beyond_extreme():
    m, b4, z, atr = setup(AFTER)
    c, _ = fade_candidates(m, b4, z, atr, "close", "2R")
    t = c.iloc[0]
    assert t["side"] == -1                                  # up impulse -> sell
    assert t["entry_idx"] == 18 * 16 - 1                    # last 15m bar of the impulse candle
    assert t["entry_price"] == pytest.approx(102.9)         # bid close
    assert t["stop"] == pytest.approx(103.0 + 0.1)          # impulse high + max(spread, 0.1 ATR)
    # the next candle trades up to 103.2 before falling: ask reaches the stop -> -1R
    assert t["reason"] == "SL" and t["r"] == pytest.approx(-1.0)


def test_fade_after_confirmation_candle_uses_new_extreme():
    m, b4, z, atr = setup(AFTER)
    c, _ = fade_candidates(m, b4, z, atr, "confirm", "1R")
    t = c.iloc[0]
    assert t["entry_idx"] == 19 * 16 - 1                    # close of the first bearish candle
    assert t["entry_price"] == pytest.approx(102.2)
    assert t["stop"] == pytest.approx(103.2 + 0.1)          # highest high up to the entry candle
    assert t["reason"] == "TP" and t["r"] == pytest.approx(1.0)


def test_fade_base_target_and_under_1R_skip():
    m, b4, z, atr = setup(AFTER)
    c, _ = fade_candidates(m, b4, z, atr, "confirm", "base")
    t = c.iloc[0]
    assert t["tp"] == pytest.approx(100.4)                  # top of the base
    assert t["reason"] == "TP" and t["r"] == pytest.approx((102.2 - 100.4) / 1.1)
    m, b4, z, atr = setup([(102.9, 103.2, 100.5, 100.6)] + AFTER[1:])
    c, _ = fade_candidates(m, b4, z, atr, "confirm", "base")
    assert c.iloc[0]["skip"] == E.SKIP_TP                   # only 0.2 left to the base, R = 2.7


def test_no_confirmation_within_six_candles_means_no_trade():
    up = [(102.9 + k * 0.2, 103.2 + k * 0.2, 102.8 + k * 0.2, 103.1 + k * 0.2) for k in range(7)]
    m, b4, z, atr = setup(up)
    c, st = fade_candidates(m, b4, z, atr, "confirm", "2R")
    assert len(c) == 0 and st["no_confirmation"] == 1
