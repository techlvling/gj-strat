# ✅ USDJPY Tokyo-open box breakout — Version B (approved)

## Rules (IST)
1. Box = high/low of the 05:00–05:59 candles.
2. 06:00: buy stop at box high, sell stop at box low. One fills → cancel the other.
3. SL = box size + spread, from entry. TP = 9 × SL.
4. Price reaches 3 × SL in profit → move SL to entry + 1/6 of the SL distance.
5. Stopped out (SL or BE) before 11:00 → wait 6 minutes → one stop on the opposite side at the
   original box level (skip if price is already beyond it).
6. Unfilled orders expire 11:00. Done after a TP or 2 trades. Trades run until SL/TP/BE, overnight OK.
7. Risk 0.5% of balance per trade.

## Backtest (Dukascopy bid/ask, $7/lot, swap +1% markup, 0.2 pip slippage)
| | 2010–2017 | 2018–2026 |
|---|---|---|
| Trades | 2,233 | 2,323 |
| Win rate | 26% | 24% |
| Avg R | +0.06 | +0.15 |
| Return at 0.5% risk | +58% | +333% |
| Max drawdown at 0.5% | 39% | 29% |
| Longest losing streak | 35 | 24 |

- Edge is ~1–2 pips/trade after commission → **slippage above ~0.3 pip kills it.**
- Rules were found on 2024–2026, held on 2010–2023 (never seen) before costs; RR picked on
  2010–2017 and checked on 2018–2026.
- Tested and rejected: wider SL (1.5×/2× box), small-box filter, other majors.

## Prop challenge (P1 8%, P2 6%, 10% static, 4% daily)
- Fixed 0.5%: 31% pass within 6 months, 38% within 12.
- Step-down 1%→0.5%→0.25%: 22% pass within 3 months.

## Rerun
```
python run_usdjpy_grid.py        # RR / version grid (pick RR9_SLbox1_BE3R+5_B)
python run_prop_sim.py           # prop pass rate
python run_prop_dynamic.py       # dynamic risk
```
Full reports: `results/usdjpy_history_comm7/`, `results/usdjpy_grid/`, `results/prop_sim/`,
`results/prop_dynamic/`.

## Still unknown
Your real slippage at 06:00 IST. Log stop price vs fill price on demo for ~20 trades.
