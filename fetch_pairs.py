"""Download Dukascopy 1-minute BID + ASK candles for the majors and minors into data/raw.

    python fetch_pairs.py [--majors-only] [--save] [--start 2023-12-31] [--end 2026-10-07]

Already-downloaded files are skipped, so it is safe to stop and restart.

--save: progress survives a new container. On start, every datastore/<PAIR>.tar is unpacked into
data/raw. Each pair that finishes is packed into datastore/<PAIR>.tar (one file, the .bi5 files
are already LZMA-compressed), then committed and pushed on the current branch.
"""
import argparse
import glob
import os
import subprocess
import tarfile
import time
from datetime import date

from gjstrat.data import MAJORS, MINORS, download

RAW, STORE = "data/raw", "datastore"
TRAILER = ("\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_015fRBG3ZHT6FjBYVaAMsXcD")


def restore() -> None:
    os.makedirs(RAW, exist_ok=True)
    for path in sorted(glob.glob(f"{STORE}/*.tar")):
        with tarfile.open(path) as tar:
            members = [m for m in tar.getmembers()
                       if m.isfile() and "/" not in m.name and not os.path.exists(f"{RAW}/{m.name}")]
            tar.extractall(RAW, members=members, filter="data")
        print(f"restored {path}: {len(members)} files", flush=True)


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True)


def save(sym: str) -> None:
    files = sorted(glob.glob(f"{RAW}/{sym}_*.bi5"))
    path = f"{STORE}/{sym}.tar"
    if os.path.exists(path):
        with tarfile.open(path) as tar:
            if len(tar.getnames()) == len(files):
                return                                    # already saved, nothing new
    os.makedirs(STORE, exist_ok=True)
    with tarfile.open(path + ".part", "w") as tar:
        for f in files:
            tar.add(f, arcname=os.path.basename(f))
    os.replace(path + ".part", path)
    git("add", path)
    git("commit", "-q", "-m", f"Save Dukascopy 1-minute data: {sym} ({len(files)} files){TRAILER}")
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True,
                            capture_output=True, text=True).stdout.strip()
    for wait in (0, 2, 4, 8, 16):
        time.sleep(wait)
        if subprocess.run(["git", "push", "-q", "-u", "origin", branch]).returncode == 0:
            print(f"saved {sym} -> {path} (pushed)", flush=True)
            return
    print(f"saved {sym} -> {path} (committed, PUSH FAILED)", flush=True)


ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2023-12-31")
ap.add_argument("--end", default="2026-10-07")
ap.add_argument("--workers", type=int, default=12)
ap.add_argument("--majors-only", action="store_true")
ap.add_argument("--save", action="store_true")
ap.add_argument("--extra", nargs="*", default=[], help="pairs to save first if already complete")
args = ap.parse_args()
pairs = MAJORS if args.majors_only else MAJORS + [p for p in MINORS if p not in MAJORS]
if args.save:
    restore()
    for sym in args.extra:
        save(sym)
for k, sym in enumerate(pairs, 1):
    download(sym, date.fromisoformat(args.start), date.fromisoformat(args.end), RAW,
             workers=args.workers)
    if args.save:
        save(sym)
    print(f"[{k}/{len(pairs)}] {sym} done", flush=True)
print("ALL PAIRS DONE", flush=True)
