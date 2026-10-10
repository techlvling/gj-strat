"""Execution-realism verification of the index_meanrev Nasdaq survivors MR4 and MR6 (adversarial).

Rebuilds the Nasdaq close series and the MR4 / MR6 trades exactly as run_alpha_index_meanrev.run_minute
(imports its functions; the original script is not edited), keeps the minute Market in memory and checks:
  1. fills: vol > 0 and spread (ao - bo) at the entry minute, the time-exit minute and the stop-fill minute
  2. stop distance vs spread; stop fills by NY hour (17:00-18:00 rollover / Sunday 18:00 weekend open), gap fills
  3. in-session data gaps (vol == 0 minutes while the CFD normally trades) during each hold
  4. cost stress (per period avg R and t):
       base       = net_r: slip 0.25 pt (x2 on SL), commission 0, financing 3%/yr per rollover day
       2x slip    = slip 0.50 pt (x2 on SL = 1.0), commission x1.5 (0 -> 0), financing 3%/yr
       real fin   = base slip, financing (Fed funds DFF + 2.5%)/yr per rollover day (typical CFD long)
       stress     = 2x slip + real fin + 1 extra point of spread on entry and on exit
       harsh      = 2x slip + financing (DFF + 3.5%)/yr + 2 pt extra spread + entry 1 live minute later
  5. trades whose hold has > 60 min of in-session missing data: dropped / counted as stop-outs
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/gj-strat")
os.chdir("/home/user/gj-strat")
import run_alpha_index_meanrev as A  # noqa: E402
from gjstrat.data import load_market  # noqa: E402
from gjstrat.patterns import NY, Signal, daily_table, local_idx, simulate  # noqa: E402
from gjstrat.swap import SwapModel  # noqa: E402
from run_all_matrix import net_r, FIN  # noqa: E402
from run_edge_hunt import PER  # noqa: E402
from run_index_anomalies import live_at  # noqa: E402
from run_usdjpy_sl import tstat  # noqa: E402

OUT = "results/alpha_hunt/index_meanrev/verify_execution"
SYM = "USATECHIDXUSD"
L3 = A.L3


def build():
    vix, vmed = A.load_vix()
    cfg = A.MINUTE[SYM]
    m = load_market(cfg["path"])
    d = daily_table(m)
    atr_med = d["atr20"].rolling(250, min_periods=250).median()
    hot_flag = (d["atr20"] >= atr_med).astype(float).where(atr_med.notna())
    cal = A.calendar(cfg["cal"], m.t0 + pd.Timedelta(days=1), m.ts(m.n - 1))
    rows = []
    for day in cal:
        i = local_idx(m, day, 15, 54, NY)
        if i < 0 or i >= m.n - 1 or not m.vol[i] > 0:
            continue
        a = max(local_idx(m, day, 9, 30, NY), 0)
        rows.append((day, i, m.bc[i], m.bh[a:i + 1].max(), m.bl[a:i + 1].min()))
    cs = pd.DataFrame(rows, columns=["day", "i", "C", "H", "L"]).set_index("day")
    cs["atr20"] = d["atr20"].reindex(cs.index).to_numpy()
    cs["hot"] = hot_flag.reindex(cs.index).to_numpy()
    cs["ts"] = [m.ts(i + 1) for i in cs.i]
    cs = A.add_features(cs, cal, atr_med, vix, vmed)
    return m, cs, cal


def main():
    t0 = time.time()
    m, cs, cal = build()
    print("built", len(cs), "closes", f"{time.time() - t0:.0f}s", "has_ask", m.has_ask, flush=True)
    I = cs.I = cs.i.to_numpy()
    meta = {}

    def execute(v, j, jx, side, slm, delay=0):
        s = live_at(m, int(I[j]) + 1)
        if delay and s >= 0:                                   # entry one live minute later
            w = np.flatnonzero(m.vol[s + 1: s + 30] > 0)
            s = s + 1 + w[0] if len(w) else -1
        x = int(I[jx]) + 1
        sl = slm * cs.atr20.iat[j]
        if s < 0 or x <= s + 1 or x >= m.n or not sl > 0:
            return None
        t = simulate(m, Signal(cs.index[j], side, s, "market", None, s + 1, sl, None, x, v))
        if t is not None:
            meta[(v, delay, t.entry_i)] = (j, jx, x)
        return t

    raw = A.plan(cs, execute)
    raw_delay = A.plan(cs, lambda v, j, jx, side, slm: execute(v, j, jx, side, slm, delay=1))
    saved = pd.read_pickle("results/alpha_hunt/index_meanrev/trades.pkl")

    # expected-live minutes: minute-of-week (NY local) live in >= 80% of 2019-2023 weeks
    ts_all = m.t0 + pd.to_timedelta(np.arange(m.n), unit="min")
    loc = ts_all.tz_localize("UTC").tz_convert(NY).tz_localize(None)
    mow = (loc.dayofweek * 1440 + loc.hour * 60 + loc.minute).to_numpy()
    yr = loc.year.to_numpy()
    sel = (yr >= 2019) & (yr <= 2023)
    live_rate = np.bincount(mow[sel], weights=(m.vol[sel] > 0).astype(float), minlength=7 * 1440) / \
        np.maximum(np.bincount(mow[sel], minlength=7 * 1440), 1)
    expected = live_rate[mow] >= 0.8
    hol = set(cal.normalize())
    locday = loc.normalize()
    del ts_all

    dff = pd.read_csv("rates/DFF.csv", parse_dates=["observation_date"]).set_index("observation_date")["DFF"]
    dff = dff.reindex(pd.date_range("2010-01-01", "2026-10-10")).ffill()

    all_rows, scen_rows, sl_rows = [], [], []
    for v in ("MR4", "MR6"):
        tr = sorted(raw[v], key=lambda t: (t.exit_i, t.entry_i))
        R0 = net_r(m, SYM, tr, None)
        sv = saved[(saved.market == SYM) & (saved.variant == v)].sort_values(["exit_ts", "entry_ts"])
        assert len(sv) == len(tr) and np.allclose(sv.R.to_numpy(), R0), "rebuild mismatch"
        rec = []
        for t, r0 in zip(tr, R0):
            ei, xi = t.entry_i, t.exit_i
            rl = SwapModel.rollovers(m.ts(ei), m.ts(xi))
            ndays = rl["days"].to_numpy()
            # Friday-triple convention (index CFDs): weekend charged on Friday; same total, so keep weights
            rates = dff.reindex(pd.DatetimeIndex(rl["ny_date"])).to_numpy()
            fin_real = float((t.entry * (rates + 2.5) / 100 / 365 * ndays).sum())
            fin_harsh = float((t.entry * (rates + 3.5) / 100 / 365 * ndays).sum())
            fin_base = FIN * ndays.sum() * t.entry
            seg = slice(ei, xi)
            gap_in_session = int(((m.vol[seg] == 0) & expected[seg]).sum())
            # longest contiguous in-session zero-vol run
            z = ((m.vol[seg] == 0) & expected[seg]).astype(np.int8)
            if z.any():
                dz = np.diff(np.r_[0, z, 0])
                st, en = np.flatnonzero(dz == 1), np.flatnonzero(dz == -1)
                longest = int((en - st).max())
            else:
                longest = 0
            xl = loc[xi]
            hold_days = int(((cal > locday[ei]) & (cal <= locday[xi])).sum())
            j, jx, x = meta[(v, 0, ei)]
            rec.append(dict(variant=v, day=t.day, entry_ts=m.ts(ei), exit_ts=m.ts(xi), reason=t.reason,
                            entry=t.entry, exit=t.exit, risk=t.risk, R_gross=t.r, R_base=r0,
                            entry_vol=m.vol[ei], entry_spread=m.ao[ei] - m.bo[ei],
                            exit_vol=m.vol[xi], exit_spread=m.ao[xi] - m.bo[xi],
                            exit_bo_minus_prev_bc=m.bo[xi] - m.bc[xi - 1],
                            risk_over_spread=t.risk / max(m.ao[ei] - m.bo[ei], 1e-9),
                            exit_ny_hour=xl.hour + xl.minute / 60, exit_dow=xl.dayofweek,
                            gapped=(t.reason == "SL" and t.exit < t.entry - t.risk - 1e-6),
                            sl_fill_minus_level=(t.exit - (t.entry - t.risk)) if t.reason == "SL" else np.nan,
                            sl_mid_low=(0.5 * (m.bl[xi] + m.al[xi])) if t.reason == "SL" else np.nan,
                            sl_ask_low=m.al[xi] if t.reason == "SL" else np.nan,
                            sl_spread_at_fill=(m.ao[xi] - m.bo[xi]) if t.reason == "SL" else np.nan,
                            rollovers=len(rl), fin_days=int(ndays.sum()),
                            fin_base_R=fin_base / t.risk, fin_real_R=fin_real / t.risk, fin_harsh_R=fin_harsh / t.risk,
                            weekend_held=bool((loc[ei:xi:60].dayofweek >= 5).any()),
                            gap_min_in_session=gap_in_session, longest_gap_min=longest,
                            nyse_days_held=hold_days, close_steps=jx - j))
        df = pd.DataFrame(rec)
        # delayed-entry version (1 live minute later)
        trd = sorted(raw_delay[v], key=lambda t: (t.exit_i, t.entry_i))
        Rd = net_r(m, SYM, trd, None)
        dmap = {meta[(v, 1, t.entry_i)][0]: r for t, r in zip(trd, Rd)}
        base_j = [meta[(v, 0, t.entry_i)][0] for t in tr]
        df["R_delay_base"] = [dmap.get(jj, np.nan) for jj in base_j]
        dgross = {meta[(v, 1, t.entry_i)][0]: (t, ) for t in trd}

        slip = 0.25
        isSL = (df.reason == "SL").to_numpy()
        risk = df.risk.to_numpy()
        gross = df.R_gross.to_numpy()
        slip_base = slip * (1 + isSL) / risk
        slip2 = 2 * slip * (1 + isSL) / risk
        sc = {
            "base (as reported)": df.R_base.to_numpy(),
            "2x slip, comm x1.5": gross - slip2 - df.fin_base_R.to_numpy(),
            "real financing DFF+2.5%": gross - slip_base - df.fin_real_R.to_numpy(),
            "2x slip + real fin + 1pt spread each side": gross - slip2 - df.fin_real_R.to_numpy() - 2.0 / risk,
        }
        # harsh: delayed entry gross where available
        gd = np.array([dgross[jj][0].r if jj in dgross else np.nan for jj in base_j])
        sld = np.array([(dgross[jj][0].reason == "SL") if jj in dgross else False for jj in base_j])
        sc["harsh: 2x slip + DFF+3.5% + 2pt spread + entry 1 min later"] = \
            gd - 2 * slip * (1 + sld) / risk - df.fin_harsh_R.to_numpy() - 4.0 / risk
        bad = (df.longest_gap_min > 60).to_numpy()
        x = sc["2x slip, comm x1.5"].copy()
        sc["2x slip, drop trades with >60 min in-session data gap"] = np.where(bad, np.nan, x)
        sc["2x slip, trades with >60 min gap forced to -1R"] = np.where(bad & (x > -1), -1.0 - slip2, x)
        for name, r in sc.items():
            df[f"R[{name}]"] = r
            day = pd.DatetimeIndex(df.day)
            row = {"variant": v, "scenario": name}
            rr = r[~np.isnan(r)]
            row.update({"n": len(rr), "avg R": rr.mean(), "t": tstat(rr)})
            ok = True
            for p, (a, b) in PER.items():
                msk = np.asarray((day >= pd.Timestamp(a)) & (day <= pd.Timestamp(b))) & ~np.isnan(r)
                row.update({f"{p} n": int(msk.sum()), f"{p} avg R": r[msk].mean(), f"{p} t": tstat(r[msk])})
                ok &= r[msk].mean() > 0
            msk = np.asarray((day >= L3[0]) & (day <= L3[1])) & ~np.isnan(r)
            row.update({"last3y avg R": r[msk].mean(), "all 3 periods > 0": bool(ok)})
            scen_rows.append(row)
        all_rows.append(df)
    D = pd.concat(all_rows, ignore_index=True)
    S = pd.DataFrame(scen_rows)
    D.to_csv(f"{OUT}/trades_exec.csv", index=False)
    S.to_csv(f"{OUT}/scenarios.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(S.round(3).to_string())
    for v, g in D.groupby("variant"):
        print(f"\n===== {v}  n={len(g)}")
        print("entry vol>0:", (g.entry_vol > 0).mean(), " exit vol>0 (TIME):", (g[g.reason == 'TIME'].exit_vol > 0).mean(),
              " SL fill vol>0:", (g[g.reason == 'SL'].exit_vol > 0).mean())
        print("entry spread pts quantiles:", g.entry_spread.quantile([0, .5, .9, .99, 1]).round(2).to_dict())
        print("entry spread by year median/max:\n", g.groupby(pd.DatetimeIndex(g.day).year).entry_spread.agg(['median', 'max']).round(2).T.to_string())
        print("exit spread (TIME) quantiles:", g[g.reason == 'TIME'].exit_spread.quantile([0, .5, .9, 1]).round(2).to_dict())
        print("risk/entry spread min, median:", g.risk_over_spread.min().round(1), g.risk_over_spread.median().round(1))
        print("exit open - prev close (TIME) abs max:", g[g.reason == 'TIME'].exit_bo_minus_prev_bc.abs().max().round(2))
        s = g[g.reason == "SL"]
        print("SL n", len(s), "gapped", int(s.gapped.sum()), "fill-level (pts) quantiles", s.sl_fill_minus_level.quantile([0, .5, 1]).round(1).to_dict())
        print("SL fills NY hour/dow:", list(zip(s.exit_ny_hour.round(2), s.exit_dow)))
        print("SL spread at fill:", s.sl_spread_at_fill.round(2).tolist())
        print("SL mid-low <= stop level? (would mid trigger):", ((s.sl_mid_low <= s.entry - s.risk + 1e-6)).mean())
        print("SL R values:", s.R_base.round(2).tolist())
        print("fin days mean", g.fin_days.mean().round(2), "fin_base_R mean", g.fin_base_R.mean().round(4),
              "fin_real_R mean", g.fin_real_R.mean().round(4), "by period real-base:",
              g.assign(dd=g.fin_real_R - g.fin_base_R).groupby(pd.cut(pd.DatetimeIndex(g.day).year, [2010, 2017, 2023, 2026])).dd.mean().round(4).to_dict())
        print("weekend held frac", g.weekend_held.mean().round(3))
        print("in-session gap minutes: trades with any", int((g.gap_min_in_session > 0).sum()), " >60 longest", int((g.longest_gap_min > 60).sum()),
              " years of >60:", pd.DatetimeIndex(g[g.longest_gap_min > 60].day).year.value_counts().sort_index().to_dict())
        print("R of >60 gap trades:", g[g.longest_gap_min > 60].R_base.round(2).tolist())
        print("NYSE days held distribution:", g.nyse_days_held.value_counts().sort_index().to_dict())
        print("delayed-entry missing:", int(g.R_delay_base.isna().sum()), "base vs delay mean R:", g.R_base.mean().round(4), g.R_delay_base.mean().round(4))
    print(f"DONE {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
