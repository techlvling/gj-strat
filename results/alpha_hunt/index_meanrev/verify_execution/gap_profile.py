"""Live-minute (vol > 0) coverage of USATECHIDXUSD by NY hour and year (diagnostic for stop-miss bias)."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/gj-strat"); os.chdir("/home/user/gj-strat")
from gjstrat.data import load_market
from gjstrat.patterns import NY
m = load_market("data/usatechidxusd_2011-01-02_2026-10-07.npz")
ts = m.t0 + pd.to_timedelta(np.arange(m.n), unit="min")
loc = ts.tz_localize("UTC").tz_convert(NY).tz_localize(None)
wk = (loc.dayofweek <= 3) & (loc.dayofweek >= 0)            # Mon-Thu (all 24 h should trade except 17-18)
df = pd.DataFrame({"y": loc.year[wk], "h": loc.hour[wk], "live": (m.vol[wk] > 0)})
tab = df.groupby(["y", "h"]).live.mean().unstack().round(2)
pd.set_option("display.width", 250)
print(tab.to_string())
