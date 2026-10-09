"""Download Dukascopy 1-minute BID + ASK candles for the majors and minors into data/raw.

    python fetch_pairs.py [--majors-only] [--save] [--start 2023-12-31] [--end 2026-10-07]
    python fetch_pairs.py --pairs USDJPY --by-year --save --start 2009-12-31 --end 2023-12-31

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


def _commit_push(path: str, msg: str) -> None:
    git("add", path)
    git("commit", "-q", "-m", msg + TRAILER)
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True,
                            capture_output=True, text=True).stdout.strip()
    for wait in (0, 2, 4, 8, 16):
        time.sleep(wait)
        if subprocess.run(["git", "push", "-q", "-u", "origin", branch]).returncode == 0:
            print(f"saved {path} (pushed)", flush=True)
            return
    print(f"saved {path} (committed, PUSH FAILED)", flush=True)


def _write_tar(path: str, files: list[str]) -> None:
    os.makedirs(STORE, exist_ok=True)
    with tarfile.open(path + ".part", "w") as tar:
        for f in files:
            tar.add(f, arcname=os.path.basename(f))
    os.replace(path + ".part", path)


def save(sym: str) -> None:
    """datastore/<SYM>.tar with the files not already in a per-year <SYM>_<YEAR>.tar."""
    path = f"{STORE}/{sym}.tar"
    stored = set()
    for t in glob.glob(f"{STORE}/{sym}_*.tar"):
        with tarfile.open(t) as tar:
            stored.update(tar.getnames())
    files = [f for f in sorted(glob.glob(f"{RAW}/{sym}_*.bi5")) if os.path.basename(f) not in stored]
    if not files:
        return
    if os.path.exists(path):
        with tarfile.open(path) as tar:
            if len(tar.getnames()) == len(files):
                return                                    # already saved, nothing new
    _write_tar(path, files)
    _commit_push(path, f"Save Dukascopy 1-minute data: {sym} ({len(files)} files)")


def save_year(sym: str, year: int) -> None:
    """datastore/<SYM>_<YEAR>.tar with that year's files not already in another <SYM> tar.
    One file per year keeps every tar far below GitHub's 100 MB limit."""
    path = f"{STORE}/{sym}_{year}.tar"
    stored = set()
    for t in glob.glob(f"{STORE}/{sym}.tar") + glob.glob(f"{STORE}/{sym}_*.tar"):
        if t != path:
            with tarfile.open(t) as tar:
                stored.update(tar.getnames())
    files = [f for f in sorted(glob.glob(f"{RAW}/{sym}_{year}*.bi5"))
             if os.path.basename(f) not in stored]
    if not files:
        return
    if os.path.exists(path):
        with tarfile.open(path) as tar:
            if len(tar.getnames()) == len(files):
                return
    _write_tar(path, files)
    _commit_push(path, f"Save Dukascopy 1-minute data: {sym} {year} ({len(files)} files)")


ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2023-12-31")
ap.add_argument("--end", default="2026-10-07")
ap.add_argument("--workers", type=int, default=12)
ap.add_argument("--majors-only", action="store_true")
ap.add_argument("--pairs", nargs="*", help="explicit list of pairs (overrides --majors-only)")
ap.add_argument("--by-year", action="store_true",
                help="download and save one calendar year at a time (long histories)")
ap.add_argument("--save", action="store_true")
ap.add_argument("--extra", nargs="*", default=[], help="pairs to save first if already complete")
args = ap.parse_args()
pairs = args.pairs or (MAJORS if args.majors_only else MAJORS + [p for p in MINORS if p not in MAJORS])
start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
if args.save:
    restore()
    for sym in args.extra:
        save(sym)
for k, sym in enumerate(pairs, 1):
    if args.by_year:
        for year in range(start.year, end.year + 1):
            download(sym, max(start, date(year, 1, 1)), min(end, date(year, 12, 31)), RAW,
                     workers=args.workers)
            if args.save:
                save_year(sym, year)
            print(f"{sym} {year} done", flush=True)
    else:
        download(sym, start, end, RAW, workers=args.workers)
        if args.save:
            save(sym)
    print(f"[{k}/{len(pairs)}] {sym} done", flush=True)
print("ALL PAIRS DONE", flush=True)
