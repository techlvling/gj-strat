"""Download Dukascopy hourly BID candles (one file per month) for an instrument, politely.

    python fetch_hourly.py USA500IDXUSD 2012 2026

Files: data/hourly/<SYM>/<YYYY>_<MM>.bi5 (MM 1-12). Saved copy for the S&P 500:
    mkdir -p data/hourly && tar -xf datastore/USA500IDXUSD_hourly.tar -C data/hourly HTTP 429 or a dropped connection -> wait and retry.
"""
import os
import sys
import time

import requests

sym, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
out = f"data/hourly/{sym}"
os.makedirs(out, exist_ok=True)
s = requests.Session()
for y in range(y0, y1 + 1):
    for mth in range(1, 13):
        path = f"{out}/{y}_{mth:02d}.bi5"
        if os.path.exists(path):
            continue
        url = f"https://datafeed.dukascopy.com/datafeed/{sym}/{y}/{mth - 1:02d}/BID_candles_hour_1.bi5"
        for attempt in range(12):
            try:
                r = s.get(url, timeout=60)
            except requests.RequestException:
                time.sleep(min(15 * 2 ** attempt, 300))
                continue
            if r.status_code == 200:
                open(path, "wb").write(r.content)
                break
            if r.status_code == 404:
                open(path, "wb").write(b"")
                break
            time.sleep(min(15 * 2 ** attempt, 300))
        else:
            sys.exit(f"gave up on {url}")
        print(y, mth, len(r.content), flush=True)
        time.sleep(1.0)
print("ALL DONE", flush=True)
