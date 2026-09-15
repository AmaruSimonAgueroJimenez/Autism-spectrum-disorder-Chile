"""Plate EF1 — seasonality and monthly series of GRD episodes with documented F84.

The stored plate was drawn by `study/pipeline/13_extra_figures_hospital.py` from `outputs/tidy/
grd_monthly.csv`, which is not in this repository. Its six panels are redrawn here from the three
published tables that carry the same series: the EF1 companion table (monthly count and rate per
100,000 GRD episodes of the same month, index of dispersion, annual REM A05 total), E1 (the
within-year seasonal index printed to two decimals) and E18 (the REM A05 monthly series, which runs
one year further than the EF1 table).

Two things the tables do not store directly, and how they are recovered here:

* the monthly **all-GRD denominator** of panels (b) and (d). The EF1 cell is `count (rate per 100,000
  GRD episodes of the same month)`, so the denominator is back-derived as `count / rate x 100,000`.
  The rate is published to one decimal, so the denominator carries about 0.02 % of rounding error —
  it does not move the Poisson interval in the third significant figure, but the denominator is
  derived, not read.
* the **exact Poisson 95 % band** of panel (b), recomputed from the monthly count on that derived
  denominator.

Case definition: the F84 family excluding Rett syndrome (`sin_rett`), the definition of the stored
plate — its 2019 total is 2,334 episodes. `output_files/consolidacion/grd_epi_monthly.csv` is a
different case definition (`F84_historico`, 2,385 in 2019) and is deliberately not used here.
"""
import re
import textwrap

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2
from figstyle import *

PLATE = "EF1_seasonality_monthly"
SOURCES = [
    "docs/study/corpus/tables/EF1_seasonality_monthly.csv",
    "docs/study/corpus/tables/E1_grd_seasonality.csv",
    "docs/study/corpus/tables/E18_rem_monthly_series.csv",
]
NOTE = ("Redraws the six panels of plate EF1 — monthly GRD episodes with documented F84 (F84 family "
        "excluding Rett), their rate per 100,000 GRD episodes of the same month, the within-year "
        "seasonal index, the 2020–2021 ratios to 2019, the REM A05 monthly series and the index of "
        "dispersion — from the EF1 companion table, E1 and E18, with the monthly all-GRD denominator "
        "back-derived as count / rate x 100,000 because it is not published on its own.")

ROOT = BASE.parents[1]                      # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]    # GRD years of the stored plate
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_INITIALS = list("JFMAMJJASOND")
# Okabe-Ito, in the order the pipeline gives the six years (sky, blue, green, yellow, gold, orange).
YEAR_COLORS = [SKY, BLUE, GREEN, YELLOW, GOLD, ORANGE]
F84_COLOR, ALL_COLOR = BLUE, GREY
PER = 100_000.0
LAW_X = 2023 + 2.5 / 12     # Law 21.545, March 2023, on the decimal-year axis of a monthly series
CTX = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.4)
TITLES = {
    "a": "Episodes with F84 by month of admission and year",
    "b": "Monthly rate per 100,000 GRD episodes of the same month",
    "c": "Within-year seasonal index (year mean = 1)",
    "d": "2020–2021 disruption: month versus same month of 2019",
    "e": "REM A05 comparison: monthly autism programme entries (2021–2025)",
    "f": "Index of dispersion of the monthly counts",
}

# --------------------------------------------------------------------------- reading the tables
# The presentation tables store every value as a formatted string: "210 (211.3)" is a count and its
# rate, "1,104 (411)" a count and the establishments reporting it, "2,334" a plain total.
_CELL = re.compile(r"^\s*(-?[\d.,]+)\s*(?:\(\s*(-?[\d.,]+)\s*\))?")


def _num(s):
    """One formatted number -> float; 'n/e' (not estimable) and blanks -> nan."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-"))


def _cell(s):
    """'210 (211.3)' -> (210.0, 211.3); '2,334' -> (2334.0, nan); 'n/e' -> (nan, nan)."""
    m = _CELL.match(str(s))
    if not m:
        return float("nan"), float("nan")
    return _num(m.group(1)), (_num(m.group(2)) if m.group(2) else float("nan"))


def _table(rel):
    """A tracked presentation table, keyed by its first column (they are written with a BOM)."""
    t = pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str)
    return t.set_index(t.columns[0])


def _row(t, prefix, suffix=""):
    """The row whose label starts with `prefix` and ends with `suffix` (labels carry a ' · ' tail)."""
    hit = [k for k in t.index if str(k).startswith(prefix) and str(k).endswith(suffix)]
    if not hit:
        raise KeyError(f"no row starting with {prefix!r} and ending with {suffix!r}")
    return t.loc[hit[0]]


def grd_monthly():
    """Monthly counts, published rates and the derived all-GRD denominator, months x years."""
    t = _table(SOURCES[0])
    counts = np.full((12, len(YEARS)), np.nan)
    rates = np.full((12, len(YEARS)), np.nan)
    for i, month in enumerate(MONTHS):
        for j, year in enumerate(YEARS):
            counts[i, j], rates[i, j] = _cell(t.loc[month, str(year)])
    # The denominator of the rate is not published: it is recovered from the pair it was printed with.
    denom = counts / rates * PER
    totals = np.array([_num(t.loc["Total", str(y)]) for y in YEARS])
    unparsable = np.array([_num(_row(t, "Unparsable admission date")[str(y)]) for y in YEARS])
    disp_f84 = np.array([_num(_row(t, "Variance / mean", "Episodes with documented F84")[str(y)])
                         for y in YEARS])
    disp_all = np.array([_num(_row(t, "Variance / mean", "All GRD episodes")[str(y)]) for y in YEARS])
    # The plate's own arithmetic, checked against the table it is drawn from.
    assert np.allclose(counts.sum(axis=0) + unparsable, totals), "monthly counts do not add to the total"
    return counts, rates, denom, disp_f84, disp_all


def seasonal_index():
    """The within-year seasonal index (mean of the year's 12 months = 1) as E1 publishes it."""
    t = _table(SOURCES[1])
    idx = np.full((12, len(YEARS)), np.nan)
    counts = np.full((12, len(YEARS)), np.nan)
    for i, month in enumerate(MONTHS):
        for j, year in enumerate(YEARS):
            counts[i, j], idx[i, j] = _cell(t.loc[month, str(year)])
    # E1 and the EF1 companion table must be the same series before either is drawn.
    assert np.allclose(np.round(counts / counts.mean(axis=0), 2), idx), "E1 index is not count / year mean"
    return idx


def rem_a05():
    """REM A05 strict-autism entries by month, and the establishments reporting the code."""
    t = pd.read_csv(ROOT / SOURCES[2], encoding="utf-8-sig", dtype=str)
    s = t[t["Series"] == "A05 Strict autism"]
    years = sorted(int(_num(y)) for y in s["Year"])
    entries, establishments = {}, {}
    for y in years:
        row = s[s["Year"] == str(y)].iloc[0]
        pairs = [_cell(row[m]) for m in MONTH_ABBR]
        entries[y] = np.array([p[0] for p in pairs])
        establishments[y] = np.array([p[1] for p in pairs])
        assert np.isclose(entries[y].sum(), _num(row["Year total"])), f"REM A05 {y} does not add up"
    return years, entries, establishments


# --------------------------------------------------------------------------- panel furniture
def _month_axis(ax):
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_INITIALS)
    ax.set_xlabel("Month of admission")


def _title(ax, key):
    """Panel title, wrapped where the pipeline's measured wrap breaks it.

    Returns the title artist (a left title is its own Text, not `ax.title`) and its line count."""
    lines = textwrap.fill(TITLES[key], 41)
    t = ax.set_title(lines, loc="left", fontsize=9, fontweight="bold", linespacing=1.15)
    return t, lines.count("\n") + 1


def draw():
    style()
    plt.rcParams.update({
        "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlepad": 4.0, "axes.titlelocation": "left",
        "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
        "legend.edgecolor": "none", "legend.borderpad": 0.25, "legend.handlelength": 1.4,
        "legend.handletextpad": 0.5, "legend.columnspacing": 1.0, "legend.labelspacing": 0.35,
        "legend.borderaxespad": 0.3, "legend.fontsize": 7, "legend.title_fontsize": 7,
        "grid.alpha": 0.32, "grid.linewidth": 0.5,
    })
    counts, rates, denom, disp_f84, disp_all = grd_monthly()
    index = seasonal_index()
    rem_years, rem_entries, rem_estab = rem_a05()
    months = np.arange(1, 13)

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    # The top strip the rect leaves free is for the panel letters: they stand on the first line of a
    # two-line title, which the layout engine does not know about and would push off the canvas.
    fig.get_layout_engine().set(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055,
                                rect=(0, 0, 1, 0.986))
    ax = axes.ravel()

    # (a) episodes by month of admission and year -------------------------------------------------
    for j, year in enumerate(YEARS):
        ax[0].plot(months, counts[:, j], marker="o", ms=3.4, lw=1.6, color=YEAR_COLORS[j], label=str(year))
    _month_axis(ax[0])
    ax[0].set_ylabel("Episodes with documented F84")
    ax[0].set_ylim(top=np.nanmax(counts) * 1.20)
    ax[0].legend(ncol=3, title="Year", loc="upper left")
    ax[0].yaxis.set_major_formatter(thousands("en"))
    clean(ax[0], "both")

    # (b) rate per 100,000 GRD episodes of the same month, exact Poisson band ----------------------
    x = np.array([y + (m - 0.5) / 12 for y in YEARS for m in months])
    k = counts.T.ravel()                      # month within year, in calendar order
    rate = rates.T.ravel()
    d = denom.T.ravel()
    lo = chi2.ppf(0.025, 2 * k) / 2 / d * PER          # exact Poisson 95 % limits on the monthly count
    hi = chi2.ppf(0.975, 2 * (k + 1)) / 2 / d * PER
    smooth = pd.Series(rate).rolling(12, center=True, min_periods=12).mean()
    ax[1].fill_between(x, lo, hi, color=F84_COLOR, alpha=0.18, lw=0)
    ax[1].plot(x, rate, lw=1.5, color=F84_COLOR)
    ax[1].plot(x, smooth, lw=2.2, color=ORANGE, ls="--")
    shade_pandemic(ax[1], 2020.0, 2022.0)
    ax[1].text(2021.0, 0.97, "Reporting\ndisruption 2020–21", transform=ax[1].get_xaxis_transform(),
               ha="center", va="top", fontsize=7, color="#555555", bbox=CTX, zorder=6)
    ax[1].axvline(LAW_X, color="#444444", ls=":", lw=1.2, zorder=1)
    ax[1].text(LAW_X + 0.06, 0.97, "Law 21.545\n(2023)", transform=ax[1].get_xaxis_transform(),
               ha="left", va="top", fontsize=7, color="#444444", bbox=CTX, zorder=6)
    year_ticks(ax[1], YEARS + [2025])
    ax[1].set_xlim(2019, 2025)
    ax[1].set_ylim(top=float(np.nanmax(hi)) * 1.12)
    ax[1].set_xlabel("Year")
    ax[1].set_ylabel("Per 100,000 GRD episodes")
    ax[1].yaxis.set_major_formatter(thousands("en"))
    clean(ax[1], "both")

    # (c) within-year seasonal index --------------------------------------------------------------
    im = ax[2].imshow(index, cmap="RdYlBu_r", aspect="auto")
    lo_i, hi_i = float(np.nanmin(index)), float(np.nanmax(index))
    for i in range(12):
        for j in range(len(YEARS)):
            shade = (index[i, j] - lo_i) / (hi_i - lo_i)
            ax[2].text(j, i, num(index[i, j], "en", 2), ha="center", va="center", fontsize=6.4,
                       color="white" if shade > 0.62 else "#1a1a1a")
    ax[2].set_xticks(range(len(YEARS))); ax[2].set_xticklabels([str(y) for y in YEARS], fontsize=8)
    ax[2].set_yticks(range(12)); ax[2].set_yticklabels(MONTH_INITIALS)
    ax[2].set_xlabel("Year")
    ax[2].grid(False)
    cb = fig.colorbar(im, ax=ax[2], fraction=0.035, pad=0.015)
    cb.ax.tick_params(labelsize=7)
    cb.set_label(textwrap.fill(TITLES["c"], 32), fontsize=7)

    # (d) 2020 and 2021 against the same month of 2019 --------------------------------------------
    for j, year in enumerate([2020, 2021], start=1):
        colour = YEAR_COLORS[j]
        ax[3].plot(months, counts[:, j] / counts[:, 0], marker="o", ms=3.4, lw=1.7, color=colour,
                   label=f"{year} · Episodes with\ndocumented F84")
        ax[3].plot(months, denom[:, j] / denom[:, 0], marker="s", ms=3.0, lw=1.4, ls="--", color=colour,
                   alpha=0.75, label=f"{year} · All GRD episodes")
    ax[3].axhline(1.0, color="#444444", lw=1.0, ls=":")
    _month_axis(ax[3])
    ax[3].set_ylabel("Ratio to 2019 (same month)")
    ratios = np.concatenate([counts[:, 1:3] / counts[:, [0]], denom[:, 1:3] / denom[:, [0]]], axis=1)
    ax[3].set_ylim(float(np.nanmin(ratios)) * 0.94, float(np.nanmax(ratios)) * 1.34)
    ax[3].legend(ncol=1, loc="upper left", fontsize=6.4)
    clean(ax[3], "both")

    # (e) the REM pathway: a different source on its own axis --------------------------------------
    for i, year in enumerate(rem_years):
        ax[4].plot(months, rem_entries[year], marker="o", ms=3.2, lw=1.5,
                   color=YEAR_COLORS[i % len(YEAR_COLORS)], label=str(year))
    _month_axis(ax[4])
    ax[4].set_ylabel("REM A05 entries (month)")
    top = max(v.max() for v in rem_entries.values()) * 1.27
    ax[4].set_ylim(-0.11 * top, top)        # room for the legend above and for the note below
    ax[4].legend(ncol=3, title="A05 autism entries (05990022)", loc="upper center")
    ax[4].text(0.02, 0.02, textwrap.fill("Different source, own axis: REM is not GRD", 38),
               transform=ax[4].transAxes, fontsize=7, color="#555555", ha="left", va="bottom")
    # Every REM panel states how many establishments report the code: the numerator follows the reporting.
    estab = "; ".join(
        f"{y}: {num(np.median(rem_estab[y]), 'en')} ({num(rem_estab[y].min(), 'en')}–{num(rem_estab[y].max(), 'en')})"
        for y in rem_years)
    ax[4].set_xlabel(textwrap.fill("Month of admission — REM establishments reporting the code, "
                                   f"monthly median (min.–max.): {estab}", 41), fontsize=6.4)
    ax[4].yaxis.set_major_formatter(thousands("en"))
    clean(ax[4], "both")

    # (f) index of dispersion of the 12 monthly counts ---------------------------------------------
    w = 0.38
    years = np.array(YEARS, dtype=float)
    ax[5].bar(years - w / 2, disp_f84, width=w, color=F84_COLOR, label="Episodes with documented\nF84")
    ax[5].bar(years + w / 2, disp_all, width=w, color=ALL_COLOR, label="All GRD episodes")
    ax[5].axhline(1.0, color="#444444", ls=":", lw=1.1)
    log_axis(ax[5], "y", "en")
    ax[5].set_ylim(0.75, float(np.nanmax(disp_all)) * 15)
    ax[5].text(0.015, 0.02, "Poisson (= 1)", transform=ax[5].transAxes, fontsize=7, color="#444444",
               va="bottom", ha="left", bbox=CTX, zorder=6)
    year_ticks(ax[5], YEARS)
    ax[5].set_xlabel("Year")
    ax[5].set_ylabel("Variance / mean of the 12 months")
    ax[5].legend(loc="upper left")
    clean(ax[5], "y")

    # Letters and titles last. The titles are set first so the layout reserves their height, the
    # layout is then resolved and frozen, and only then are letter and title moved to the left edge
    # of their own cell — where the pipeline puts them, and where a two-column title still fits on
    # the canvas. The letter sits on the title's FIRST line, so it rises with a wrapped title.
    titles = {key: _title(a, key) for a, key in zip(ax, "abcdef")}
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    margin = 2.0 / 180.0                    # 2 mm left margin of the cell
    gap = 22.0 / (FIG_W_IN * 72)            # gap between the panel letter and its title
    line_h = 10.8 / (FIG_H_IN * 72)         # one title line at 9 pt
    for i, (a, key) in enumerate(zip(ax, "abcdef")):
        cell = margin + (i % 2) * 0.5
        pos = a.get_position()
        artist, nlines = titles[key]
        artist.set_x((cell + gap - pos.x0) / pos.width)
        letter(fig, a, f"({key})", dx=cell - pos.x0, dy=0.012 + (nlines - 1) * line_h)
    return fig
