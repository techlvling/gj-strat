"""Equity-curve charts (compounded % return, 1% risk per trade), one PNG per combo,
one panel per pair: macro vs no filter vs 200-day trend, random-filter 5-95% band behind."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = {"macro": ("#2a78d6", "Macro filter"), "none": ("#eb6834", "No filter"),
          "trend": ("#1baf7a", "200-day trend")}
BAND = "#c9c8c2"


def equity_on_grid(exit_ns: np.ndarray, r: np.ndarray, grid_ns: np.ndarray) -> np.ndarray:
    """Compounded % return realised by each grid time."""
    order = np.argsort(exit_ns, kind="stable")
    eq = np.concatenate([[1.0], np.cumprod(1 + 0.01 * r[order])])
    k = np.searchsorted(exit_ns[order], grid_ns, side="right")
    return (eq[k] - 1) * 100


def plot_combo(path: str, title: str, curves: dict, bands: dict, grid: pd.DatetimeIndex,
               split: pd.Timestamp, series: dict | None = None, band_label: str = "Random filter") -> None:
    """curves[pair][filter] = array on grid; bands[pair] = (p5, p50, p95) arrays."""
    pairs = list(curves)
    fig, axes = plt.subplots(1, len(pairs), figsize=(6.2 * len(pairs), 4.2), sharey=False,
                             facecolor=SURFACE)
    for ax, pair in zip(np.atleast_1d(axes), pairs):
        ax.set_facecolor(SURFACE)
        if pair in bands:
            lo, med, hi = bands[pair]
            ax.fill_between(grid, lo, hi, color=BAND, alpha=0.55, lw=0, label=f"{band_label} 5-95%")
            ax.plot(grid, med, color=INK2, lw=1, ls=(0, (3, 2)), label=f"{band_label} median")
        for f, (col, lab) in (series or SERIES).items():
            y = curves[pair].get(f)
            if y is None:
                continue
            ax.plot(grid, y, color=col, lw=2, label=lab)
            ax.annotate(f"{y[-1]:+.0f}%", (grid[-1], y[-1]), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=8, color=INK)
        ax.axvline(split, color=INK2, lw=0.8, ls=":")
        ax.text(split, 1.0, " out-of-sample →", transform=ax.get_xaxis_transform(), va="top",
                fontsize=8, color=INK2)
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_title(pair, fontsize=11, color=INK, loc="left")
        ax.set_ylabel("Net return, % (1% risk/trade, compounding)", fontsize=8, color=INK2)
        ax.grid(axis="y", color=GRID, lw=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    np.atleast_1d(axes)[0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle(title, fontsize=12, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
