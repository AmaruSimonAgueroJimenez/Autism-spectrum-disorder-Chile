"""E18 — monthly REM series: A05 entries, A03 screening, A28 rehabilitation, seasonality, 2020.

The stored plate was drawn by `study/pipeline/14_extra_figures_rem.py` from `outputs/tidy/
rem_pathway_tidy.csv`, which this repository does not carry. All six panels survive in two tracked
files and are redrawn here from them:

  * `docs/study/corpus/tables/E18_rem_monthly_series.csv` — the plate's own published table. It is
    Series x Year x Jan..Dec x Year total, and every month cell is the formatted string
    ``"1,104 (411)"``: the month's count and the establishments that had a row in that month. Panels
    (a), (b), (c), (d) and (e) are parsed straight off it, count and bracketed n alike.
  * `output_files/consolidacion/rem_monthly_region_raw_columns.csv` — the REM month x region x code
    file that panel (f) needs. The panel compares each 2020 month with the same 2019 month for FIVE
    codes and the E18 table carries only three of them; 03500404 and 03500405 have no monthly row
    there. This file supplies all five, and `_check()` confirms it reproduces the three the E18 table
    does publish, month for month, which is what ties the two lineages together.
  * `docs/study/corpus/tables/E11_rem_a03_codes_by_era.csv` — for the four A03 legend strings of
    panel (f), which that table prints verbatim in its `Indicator` column.

Estimator, unchanged from the original: unweighted administrative counts, never rates and never
standardised. The unit is the MONTHLY FLOW — COL01 for the A05 codes, COL01+COL02 for the A03 codes
(Col01 alone gives 34 for 03500406 in January 2019 and would not reproduce the table's 50). Panel (d)
is an index to the year's own twelve-month mean, averaged within the definition era; panel (f) is a
same-month year-over-year ratio. Both are within-source and neither crosses a definition break: the
A05 broad PDD category of 2019-2020 is a different case definition from strict autism and is drawn
with its own dashed line, never joined to the 2021-2025 series.

A month with no row is "not reported" and stays a gap — never a zero and never interpolated.

The corpus is English only, so this module is English only and takes no language argument.
"""
import re
import sys
import textwrap
from pathlib import Path

_STUDY = Path(__file__).resolve().parents[1]          # docs/study, where figstyle lives
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D

from figstyle import *   # noqa: F401,F403 — style, clean, num, thousands, OKABE, GREY, …

PLATE = "E18_rem_monthly_series"
SOURCES = [
    "docs/study/corpus/tables/E18_rem_monthly_series.csv",
    "output_files/consolidacion/rem_monthly_region_raw_columns.csv",
    "docs/study/corpus/tables/E11_rem_a03_codes_by_era.csv",
]
NOTE = ("Redraws the six panels of plate E18 — the A05 monthly entries of both definition eras, the "
        "legacy A03 M-CHAT series with its February 2019 outlier, the A28 rehabilitation series, the "
        "mean seasonal index within each era, the establishments reporting in each month and the "
        "2020-to-2019 same-month ratio of five codes — from the published E18 table and, for the two "
        "panel-(f) codes it does not carry by month, from the REM monthly region-by-code file.")

ROOT = Path(__file__).resolve().parents[3]            # repository root
TABLE = ROOT / SOURCES[0]
MONTHLY = ROOT / SOURCES[1]
E11_TABLE = ROOT / SOURCES[2]

# --------------------------------------------------------------------------------------------------
# The plate's own geometry and typography (study/pipeline/14_extra_figures_rem.py): 180 x 245 mm,
# three rows by two columns in reading order, 9 pt bold panel titles down to a 6 pt floor.
# --------------------------------------------------------------------------------------------------
PLATE_W_IN, PLATE_H_IN = 180.0 / 25.4, 245.0 / 25.4
PLATE_LETTERS = "abcdef"
FS_TITLE, FS_BASE, FS_TICK, FS_LEG, FS_ANN, FS_CELL, FS_LETTER = 9.0, 8.0, 7.0, 7.0, 6.4, 6.0, 10.0
TITLE_W_PT = (PLATE_W_IN * 72.0 / 2) - 2.0 * 72.0 / 25.4 - 31.0     # cell - margin - letter
XLABEL_W_PT = 150.0            # useful width of a note under a panel
YLABEL_H_PT = 138.0            # useful height of the axes area: a longer y label breaks into lines
CELL_MARGIN = 2.0 / 180.0      # 2 mm left margin of the grid cell, as a figure fraction
LETTER_GAP_PT = 22.0           # gap between the panel letter and its title
NOTE_BROWN = "#8a3b12"         # the two coloured notes of the stored plate
GREY_TEXT = "#555555"
PLATE_RC = {
    "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold",
    "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "legend.fontsize": FS_LEG, "legend.title_fontsize": FS_LEG,
    "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
    "legend.edgecolor": "none", "legend.borderpad": 0.25, "legend.handlelength": 1.4,
    "legend.handletextpad": 0.5, "legend.columnspacing": 1.0, "legend.labelspacing": 0.35,
    "legend.borderaxespad": 0.3,
    "axes.linewidth": 0.7, "axes.edgecolor": "#333333",
    "grid.linewidth": 0.5, "grid.alpha": 0.32, "grid.color": "#b0b0b0",
    "lines.linewidth": 1.1, "lines.markersize": 3.2,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.2,
    "ytick.major.size": 2.2, "xtick.bottom": False, "ytick.left": False,
    "xtick.major.pad": 1.6, "ytick.major.pad": 1.6, "axes.titlepad": 4.0, "axes.labelpad": 2.0,
}

# Year colours of the REM plates: 2019 grey and 2020 black mark the years whose definition and whose
# reporting are both different, the Okabe-Ito wheel carries the rest.
YEARCOL = {2019: "#9e9e9e", 2020: "#000000", 2021: SKY, 2022: BLUE, 2023: GREEN, 2024: GOLD,
           2025: ORANGE}
MONTHS_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS = np.arange(1, 13)

# Series of the E18 table, by the exact wording of its `Series` column.
S_STRICT = "A05 Strict autism"
S_BROAD = "A05 Broad PDD (pre-2021)"
S_DONE = "M-CHAT performed (children with an alteration)"
S_ALTERED = "M-CHAT altered (children with an alteration)"
S_PRIMARY = "Primary rehabilitation (29101629)"
S_HOSPITAL = "Hospital rehabilitation (29101651)"

# Short legend forms the plate prints; the long forms above are the table's own.
L_STRICT, L_BROAD = "Strict autism", "Broad PDD (pre-2021)"
L_PRIMARY_SHORT, L_HOSPITAL_SHORT = "Primary rehabilitation", "Hospital rehabilitation"

A05_YEARS = [2021, 2022, 2023, 2024, 2025]
A03_YEARS = [2019, 2020, 2021, 2022]
A28_YEARS = [2023, 2024, 2025]

# Panel (f): the five codes present in both 2019 and 2020, in the order the plate draws them, with
# the REM columns that make the monthly flow of each family.
RATIO_CODES = [("03500404", ("Col01", "Col02")), ("03500405", ("Col01", "Col02")),
               ("03500406", ("Col01", "Col02")), ("03500407", ("Col01", "Col02")),
               ("06902600", ("Col01",))]
RATIO_COLOURS = [BLUE, ORANGE, GREEN, PINK, GOLD]           # OKABE[0..4], as the pipeline takes them

TITLES = {
    "a": "A05 strict-autism entries by month",
    "b": "A03 M-CHAT performed by month (legacy era)",
    "c": "A28 primary-level rehabilitation by month",
    "d": "Mean seasonal index by indicator and era",
    "e": "Establishments with a row in the month",
    "f": "2020 disruption: 2020 month against the same 2019 month",
}
U_ENTRIES = "Entries (annual flow)"
U_SCREEN = "Screening records (annual flow) (log scale)"
U_REHAB = "Rehabilitation entries (annual flow)"
U_INDEX = "Monthly index (annual mean = 100)"
U_ESTAB = "Reporting establishments (n)"
U_RATIO = "2020 / 2019 ratio of the same month (%)"
NO_CONTINUITY = "separate eras: the totals do not form a continuous series"
NO_ROW_MONTH = "month with no row = not reported (never zero)"


# --------------------------------------------------------------------------------------------------
# Reading the tracked tables
# --------------------------------------------------------------------------------------------------
_CELL = re.compile(r"^\s*([\d,]+)\s*(?:\(\s*([\d,]+)\s*\))?\s*$")


def _int(s):
    return int(str(s).replace(",", ""))


def _cell(s):
    """'1,104 (411)' -> (1104.0, 411.0); '2,085' -> (2085.0, nan); anything else -> (nan, nan)."""
    m = _CELL.match(str(s))
    if not m:
        return np.nan, np.nan
    return float(_int(m.group(1))), (float(_int(m.group(2))) if m.group(2) else np.nan)


def read_table():
    """The published E18 table as two month-by-year frames per series: counts and establishments.

    Returns {series: {"total": DataFrame(year x month), "n_est": DataFrame(year x month)}}. A month
    with no row would arrive as an unparsable cell and stays NaN — never a zero.
    """
    raw = pd.read_csv(TABLE, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    out = {}
    for series, block in raw.groupby("Series", sort=False):
        total, n_est = {}, {}
        for _, row in block.iterrows():
            year = _int(row["Year"])
            pairs = [_cell(row[m]) for m in MONTHS_ABBR]
            total[year] = [p[0] for p in pairs]
            n_est[year] = [p[1] for p in pairs]
            # the plate's own arithmetic: the twelve months are the year, checked before anything is drawn
            published = _int(row["Year total"])
            assert np.isclose(np.nansum(total[year]), published), \
                f"{series} {year}: months sum to {np.nansum(total[year])}, table says {published}"
        out[series] = {
            "total": pd.DataFrame(total, index=MONTHS).T.sort_index(),
            "n_est": pd.DataFrame(n_est, index=MONTHS).T.sort_index(),
        }
    return out


def read_monthly_ratio():
    """2019 and 2020 month totals of the five panel-(f) codes, summed over the sixteen regions.

    COL01+COL02 for the A03 codes and COL01 for the A05 broad category: the same monthly flow the E18
    table publishes for the three codes it carries, which `_check` verifies.
    """
    cols = ["year", "Mes", "IdRegion", "CodigoPrestacion", "Col01", "Col02"]
    raw = pd.read_csv(MONTHLY, usecols=cols, dtype={"CodigoPrestacion": str})
    raw = raw[raw.year.isin((2019, 2020))]
    out = {}
    for code, use in RATIO_CODES:
        s = raw[raw.CodigoPrestacion == code].copy()
        s["flow"] = sum(s[c].fillna(0) for c in use)
        wide = (s.groupby(["year", "Mes"])["flow"].sum(min_count=1)
                 .unstack("Mes").reindex(index=[2019, 2020], columns=MONTHS))
        out[code] = wide
    return out


def read_a03_labels():
    """The four A03 indicator strings of panel (f), verbatim from the E11 table's own column."""
    raw = pd.read_csv(E11_TABLE, dtype=str, encoding="utf-8-sig")
    raw.columns = [c.strip() for c in raw.columns]
    return dict(zip(raw["Code"].str.strip(), raw["Indicator"].str.strip()))


def _check(table, ratio):
    """The two lineages must be the same series before either is drawn.

    The E18 table and the monthly region file both carry 03500406, 03500407 and the A05 broad
    category by month for 2019 and 2020. If they disagree anywhere, panel (f) would be mixing two
    different countings and nothing below should run.
    """
    for code, series in (("03500406", S_DONE), ("03500407", S_ALTERED), ("06902600", S_BROAD)):
        published = table[series]["total"].loc[[2019, 2020]].to_numpy(dtype=float)
        recomputed = ratio[code].to_numpy(dtype=float)
        assert np.allclose(published, recomputed, equal_nan=True), \
            f"{code}: the monthly file does not reproduce the E18 table row for {series}"


def seasonal_index(total):
    """Month index (the year's own twelve-month mean = 100), then mean, min and max across years.

    `total` is a year x month frame. A month with no row is left out of the year's mean rather than
    counted as a zero, which is what the pipeline's `s.mean()` does.
    """
    index = 100.0 * total.div(total.mean(axis=1), axis=0)
    return index.mean(axis=0), index.min(axis=0), index.max(axis=0)


# --------------------------------------------------------------------------------------------------
# The plate's typographic helpers (measured wrapping, not character counting)
# --------------------------------------------------------------------------------------------------
_MEASURE = None


def _text_width_pt(s, fontsize=FS_TITLE, weight="bold"):
    """The real typographic width of a string in points, measured in the font it will be drawn in."""
    global _MEASURE
    if _MEASURE is None:
        # deliberately not a pyplot figure: an open pyplot figure would become the current one and a
        # notebook or Quarto chunk would render the blank measuring square
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        _MEASURE = Figure(figsize=(1, 1))
        FigureCanvasAgg(_MEASURE)
    r = _MEASURE.canvas.get_renderer()
    w, _h, _d = r.get_text_width_height_descent(
        s, FontProperties(family="DejaVu Sans", size=fontsize, weight=weight), False)
    return w * 72.0 / _MEASURE.dpi


def wrap_measured(text, max_pt=TITLE_W_PT, fontsize=FS_TITLE, weight="bold"):
    """Line wrapping by measured width. Counting characters leaves a title out of its own cell."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and _text_width_pt(trial, fontsize, weight) > max_pt:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return "\n".join(lines) if lines else str(text)


def _headroom(ax, frac):
    """Stretch the top of the axis so the legend has its own white space instead of covering a line."""
    lo, hi = ax.get_ylim()
    if ax.get_yscale() == "log":
        if lo > 0 and hi > lo:
            ax.set_ylim(lo, hi * (hi / lo) ** frac)
    elif hi > lo:
        ax.set_ylim(lo, hi + (hi - lo) * frac)


def _legend(ax, *args, width=24, expand=None, **kw):
    """The plate's legend: long labels break into lines, the body size never shrinks.

    A legend in the upper half stretches its axis first, so it sits in white space rather than over
    the series it explains — the same rule, and the same arithmetic, as the pipeline's helper.
    """
    if len(args) >= 2:
        handles, labels, args = args[0], args[1], args[2:]
    else:
        handles, labels, args = (*ax.get_legend_handles_labels(), ())
    labels = [textwrap.fill(str(t), width) for t in labels]
    kw.setdefault("fontsize", FS_LEG)
    kw.setdefault("borderpad", 0.28)
    kw.setdefault("labelspacing", 0.3)
    loc = kw.get("loc", "best")
    if expand is None:
        expand = isinstance(loc, str) and (loc.startswith("upper") or loc == "best")
    if expand:
        ncol = int(kw.get("ncol", 1)) or 1
        rows = -(-len(labels) // ncol)
        lines = max(rows, sum(str(t).count("\n") + 1 for t in labels) // ncol)
        _headroom(ax, min(0.62, 0.030 + 0.062 * lines))
    leg = ax.legend(handles, labels, *args, **kw)
    # A legend wider than its axes makes the layout engine reserve room outside and shrink the whole
    # column; kept out of the layout it stays inside the panel where it was put.
    leg.set_in_layout(False)
    return leg


def _month_axis(ax):
    ax.set_xticks(MONTHS)
    ax.set_xticklabels(MONTHS_ABBR, fontsize=FS_TICK, rotation=45, ha="right")


def _long_xlabel(ax, text, colour):
    ax.set_xlabel(wrap_measured(text, XLABEL_W_PT, FS_ANN, "normal"), fontsize=FS_ANN, color=colour)


def _ylabel(ax, text):
    """The y label of a 90 mm cell: wrapped when it is taller than the axes area, as on the plate."""
    if _text_width_pt(text, FS_BASE, "normal") > YLABEL_H_PT:
        text = wrap_measured(text, YLABEL_H_PT, FS_BASE, "normal")
        ax.set_ylabel(text, fontsize=FS_BASE, linespacing=1.0)
    else:
        ax.set_ylabel(text, fontsize=FS_BASE)


# --------------------------------------------------------------------------------------------------
# The six panels
# --------------------------------------------------------------------------------------------------
def _panel_a(ax, table):
    """A05 entries by month. Two definition eras, two line styles, never one series."""
    strict, broad = table[S_STRICT]["total"], table[S_BROAD]["total"]
    for y in A05_YEARS:
        ax.plot(MONTHS, strict.loc[y], marker="o", ms=4, lw=1.8, color=YEARCOL[y],
                label=f"{y} — {L_STRICT}")
    for y in (2019, 2020):
        ax.plot(MONTHS, broad.loc[y], marker="^", ms=4, lw=1.4, ls="--", color=YEARCOL[y],
                alpha=0.85, label=f"{y} — {L_BROAD}")
    _month_axis(ax)
    _ylabel(ax, U_ENTRIES)
    ax.yaxis.set_major_formatter(thousands("en"))
    _legend(ax, loc="upper left", fontsize=FS_CELL, ncol=2)
    _long_xlabel(ax, NO_CONTINUITY, NOTE_BROWN)
    clean(ax, grid="both")


def _panel_b(ax, table):
    """Legacy-era M-CHAT performed, log scale, with the February 2019 file outlier marked."""
    done = table[S_DONE]["total"]
    for y in A03_YEARS:
        ax.plot(MONTHS, done.loc[y], marker="o", ms=4, lw=1.8, color=YEARCOL[y], label=str(y))
    ax.set_yscale("log")
    # The note used to sit on the very points it marks; it goes up into the sky of the panel with the
    # arrow pointing at the datum, and the axis is stretched just enough to hold it.
    performed = float(done.loc[2019, 2])
    altered = float(table[S_ALTERED]["total"].loc[2019, 2])
    _headroom(ax, 0.55)
    # Both numbers in the note are read off the table, not transcribed from the stored image.
    note = (f"Feb 2019: {num(performed, 'en')} performed and {num(altered, 'en')} altered in a "
            f"single month (outlying file value; reported, never corrected)")
    t = ax.annotate(wrap_measured(note, 104.0, FS_ANN, "normal"), xy=(2, performed),
                    xytext=(4.2, performed * 2.6), fontsize=FS_ANN, color=NOTE_BROWN, ha="left",
                    va="bottom", arrowprops=dict(arrowstyle="->", color=NOTE_BROWN, lw=1.0))
    t.set_in_layout(False)          # a note inside a panel does not shrink the column it sits in
    _month_axis(ax)
    _ylabel(ax, U_SCREEN)
    _legend(ax, loc="lower right", fontsize=FS_ANN, ncol=2)
    clean(ax, grid="both")


def _panel_c(ax, table):
    """A28 rehabilitation entries by month: colour is the year, the stroke is the level of care."""
    primary, hospital = table[S_PRIMARY]["total"], table[S_HOSPITAL]["total"]
    for y in A28_YEARS:
        ax.plot(MONTHS, primary.loc[y], marker="o", ms=4.5, lw=1.9, color=YEARCOL[y])
        ax.plot(MONTHS, hospital.loc[y], marker="s", ms=3.6, lw=1.2, ls=":", color=YEARCOL[y],
                alpha=0.85)
    _month_axis(ax)
    _ylabel(ax, U_REHAB)
    ax.yaxis.set_major_formatter(thousands("en"))
    # Five keys instead of six long labels, and every entry one line high so the marker sits on its
    # own label and the rows read across.
    handles = ([Line2D([], [], color=YEARCOL[y], marker="o", ms=4.5, lw=1.9) for y in A28_YEARS] +
               [Line2D([], [], color=GREY, marker="o", ms=4.5, lw=1.9),
                Line2D([], [], color=GREY, marker="s", ms=3.6, lw=1.2, ls=":")])
    labels = [str(y) for y in A28_YEARS] + [L_PRIMARY_SHORT, L_HOSPITAL_SHORT]
    _legend(ax, handles, labels, loc="upper left", ncol=2, width=28, columnspacing=0.7,
            fontsize=FS_CELL)
    clean(ax, grid="both")


def _panel_d(ax, table):
    """Mean seasonal index within each definition era, with the min-to-max band across its years."""
    eras = ((S_STRICT, BLUE, f"A05 {L_STRICT} 2021–2025"),
            (S_DONE, GREEN, "A03 M-CHAT 2019–2022"),
            (S_PRIMARY, ORANGE, f"A28 {S_PRIMARY} 2023–2025"))
    for series, colour, label in eras:
        mean, lo, hi = seasonal_index(table[series]["total"])
        ax.plot(MONTHS, mean, marker="o", ms=5, lw=2.0, color=colour, label=label)
        ax.fill_between(MONTHS, lo, hi, color=colour, alpha=0.12)
    ax.axhline(100, color=GREY, ls=":", lw=1.2)
    _month_axis(ax)
    _ylabel(ax, U_INDEX)
    ax.yaxis.set_major_formatter(thousands("en"))
    _legend(ax, loc="upper right", fontsize=FS_ANN)
    clean(ax, grid="both")


def _panel_e(ax, table):
    """Establishments with at least one row in the month — the numerator follows the reporting."""
    for series, ls in ((S_STRICT, "-"), (S_PRIMARY, "--")):
        n_est = table[series]["n_est"]
        for y in n_est.index:
            ax.plot(MONTHS, n_est.loc[y], marker="o", ms=3.2, lw=1.4, ls=ls, color=YEARCOL[y])
    _month_axis(ax)
    _ylabel(ax, U_ESTAB)
    ax.yaxis.set_major_formatter(thousands("en"))
    _long_xlabel(ax, NO_ROW_MONTH, GREY_TEXT)
    years = sorted(set(table[S_STRICT]["n_est"].index) | set(table[S_PRIMARY]["n_est"].index))
    handles = ([Line2D([], [], color=YEARCOL[y], marker="o", ms=3.2, lw=1.4) for y in years] +
               [Line2D([], [], color=GREY, marker="o", ms=3.2, lw=1.4),
                Line2D([], [], color=GREY, marker="o", ms=3.2, lw=1.4, ls="--")])
    labels = [str(y) for y in years] + [f"A05 {L_STRICT}", f"A28 {L_PRIMARY_SHORT}"]
    _headroom(ax, 0.34)
    _legend(ax, handles, labels, loc="upper left", expand=False, ncol=2, width=28,
            columnspacing=0.7, fontsize=FS_CELL)
    clean(ax, grid="both")


def _panel_f(ax, ratio, labels):
    """Each 2020 month against the same 2019 month, for the five codes present in both years."""
    for (code, _use), colour in zip(RATIO_CODES, RATIO_COLOURS):
        wide = ratio[code]
        a = wide.loc[2019].to_numpy(dtype=float)
        b = wide.loc[2020].to_numpy(dtype=float)
        pct = np.where(a > 0, 100.0 * b / a, np.nan)        # a zero denominator is not a ratio
        ax.plot(MONTHS, pct, marker="o", ms=4, lw=1.7, color=colour, label=labels[code])
    ax.axhline(100, color=GREY, ls=":", lw=1.2)
    _month_axis(ax)
    _ylabel(ax, U_RATIO)
    ax.yaxis.set_major_formatter(thousands("en"))
    _legend(ax, loc="upper right", width=20, fontsize=FS_CELL, frameon=True, framealpha=0.92,
            edgecolor="none")
    clean(ax, grid="both")


# --------------------------------------------------------------------------------------------------
def _headings(fig, axes):
    """Panel letter and title anchored to the grid CELL, the letter's top level with the title's.

    A title anchored to its own axes starts wherever the y tick labels end, which in a 90 mm cell is
    well inside it; anchored to the cell the three rows of titles line up and none of them runs into
    the neighbouring cell or off the canvas.
    """
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    gap = LETTER_GAP_PT / (PLATE_W_IN * 72.0)
    for i, (ax, ch) in enumerate(zip(axes, PLATE_LETTERS)):
        artist = ax._left_title
        cell = CELL_MARGIN + (i % 2) * 0.5
        top = artist.get_window_extent(r).transformed(inv).y1
        pos = ax.get_position()
        artist.set_x((cell + gap - pos.x0) / pos.width)
        fig.text(cell, top, f"({ch})", fontsize=FS_LETTER, fontweight="bold", ha="left", va="top")


def draw():
    table = read_table()
    ratio = read_monthly_ratio()
    _check(table, ratio)
    labels = read_a03_labels()
    labels["06902600"] = f"A05 {L_BROAD}"       # the one string only E18 carries

    style()
    plt.rcParams.update(PLATE_RC)
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055)
    gs = fig.add_gridspec(3, 2)
    axes = [fig.add_subplot(gs[r, c]) for r in range(3) for c in range(2)]

    _panel_a(axes[0], table)
    _panel_b(axes[1], table)
    _panel_c(axes[2], table)
    _panel_d(axes[3], table)
    _panel_e(axes[4], table)
    _panel_f(axes[5], ratio, labels)

    for ax, ch in zip(axes, PLATE_LETTERS):
        ax.set_title(wrap_measured(TITLES[ch], TITLE_W_PT, FS_TITLE, "bold"), fontsize=FS_TITLE,
                     fontweight="bold", loc="left")
    _headings(fig, axes)
    return fig


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(f"{PLATE}_redraw.png")
    draw().savefig(out, dpi=141, facecolor="white")
    print("wrote", out)
