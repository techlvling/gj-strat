"""Download Dukascopy 1-minute BID + ASK candles for the majors and minors into data/raw.

    python fetch_pairs.py [--start 2023-12-31] [--end 2026-10-07]

Already-downloaded files are skipped, so it is safe to stop and restart.
"""
import argparse
from datetime import date

from gjstrat.data import MAJORS, MINORS, download

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2023-12-31")
ap.add_argument("--end", default="2026-10-07")
ap.add_argument("--workers", type=int, default=12)
args = ap.parse_args()
pairs = MAJORS + [p for p in MINORS if p not in MAJORS]
for k, sym in enumerate(pairs, 1):
    download(sym, date.fromisoformat(args.start), date.fromisoformat(args.end), "data/raw",
             workers=args.workers)
    print(f"[{k}/{len(pairs)}] {sym} done", flush=True)
print("ALL PAIRS DONE", flush=True)
