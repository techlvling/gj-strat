"""Spread-floor check: 2012 Nasdaq ask == bid (zero spread) -> those trades paid no spread. Re-cost every trade
with a spread floor (entry and exit spread raised to >= floor) on top of the stress costs; per-period avg R / t."""
import numpy as np, pandas as pd
from run_edge_hunt import PER
from run_usdjpy_sl import tstat
D = pd.read_csv("results/alpha_hunt/index_meanrev/verify_execution/trades_exec.csv", parse_dates=["day"])
print(D.groupby([D.variant, D.day.dt.year]).entry_spread.apply(lambda s: (s < 0.3).sum()).unstack(0).fillna(0).astype(int).T.to_string())
rows = []
for v, g in D.groupby("variant"):
    isSL = (g.reason == "SL").to_numpy(); risk = g.risk.to_numpy(); gross = g.R_gross.to_numpy()
    ex_sp = np.where(isSL, g.sl_spread_at_fill.fillna(0), g.exit_spread).astype(float)
    for floor in (0.0, 1.0, 1.5):
        add = (np.maximum(floor - g.entry_spread.to_numpy(), 0) + np.maximum(floor - ex_sp, 0) * 0) / risk
        # entry pays ask (spread floor shortfall added); long exits at bid so exit spread does not enter P&L
        for nm, slipm, fin in (("base slip, 3% fin", 1, g.fin_base_R), ("2x slip, 3% fin", 2, g.fin_base_R),
                               ("2x slip, DFF+2.5% fin", 2, g.fin_real_R)):
            r = gross - slipm * 0.25 * (1 + isSL) / risk - fin.to_numpy() - add
            row = {"variant": v, "spread floor pts": floor, "costs": nm}
            ok = True
            for p, (a, b) in PER.items():
                k = ((g.day >= a) & (g.day <= b)).to_numpy()
                row[f"{p} avg R"], row[f"{p} t"] = r[k].mean(), tstat(r[k]); ok &= r[k].mean() > 0
            row["all 3 > 0"] = ok; row["bar (design t>=2 & check,holdout>0)"] = ok and row["design t"] >= 2
            rows.append(row)
S = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(S.round(3).to_string())
S.to_csv("results/alpha_hunt/index_meanrev/verify_execution/spread_floor.csv", index=False)
