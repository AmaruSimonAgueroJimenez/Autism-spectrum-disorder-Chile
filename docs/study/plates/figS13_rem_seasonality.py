"""Plate S13 — monthly seasonality of REM reporting: A05 entries and A03 screening, by year and era.

The stored plate was drawn by `study/pipeline/` from the REM Serie A microdata, which this repository
does not carry. All six of its panels survive in one published table and are redrawn from it:

  * `docs/study/corpus/tables/S13_rem_seasonality.csv` — 312 rows, one per series x year x month,
    holding `Month total`, `Establishments with a row in the month`, `Reporting establishments in the
    year` and `Index (annual mean = 100)`. Seven series live in it: the five indexed ones behind
    panels (a)–(e) and, as their own explicit rows, the two establishment-count series behind panel
    (f) — whose index cell is `n/e`, because they are drawn on a count axis and not on an index one.
  * `docs/study/corpus/tables/E18_rem_monthly_series.csv` — the same REM months published as
    `total (establishments)` for A05 strict autism, A05 broad PDD and the legacy M-CHAT. It is not
    needed to draw anything; it is read to check the S13 figures against a second published table
    before the plate is drawn (`_cross_check`).

The estimator is the stored plate's own and is not replaced:

  * panels (a)–(e) plot the published INDEX — the national monthly total (the sum of the
    establishment x month rows present) divided by that year's 12-month mean, x 100. The stored
    `Index (annual mean = 100)` column is what is drawn, never a value recomputed from rounded
    totals; the module only asserts that the two agree to the published decimal.
  * panel (f) plots RAW establishment counts on its own axis — how many establishments have a row in
    the month — and carries no index reference line.
  * definition eras are separate lines per year and are never joined: the 2021 A05 break (broad PDD
    06902600 before it, strict autism 05990022 from 2021) and the 2025 M-CHAT-R/F redesign
    (09600213–09600215 in 2023–24, 03710016–03710019 in 2025) each keep their own lines, the later
    or other code family dashed, as the `Code` and `Definition era` columns require.
  * a month with no row would be left blank, never drawn as a zero (the table happens to carry all
    twelve months of every year, but the reindex that would open the gap is kept).
  * n in every legend is `Reporting establishments in the year` — establishments with at least one
    row for that code in the year.

These are administrative counts, never prevalence or incidence. The corpus is English only, so this
module is English only.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent          # docs/study/plates
STUDY = HERE.parent                             # docs/study
ROOT = STUDY.parent.parent                      # repository root
if str(STUDY) not in sys.path:                  # import figstyle the way the figure scripts do
    sys.path.insert(0, str(STUDY))
from figstyle import *                          # noqa: E402,F401,F403

PLATE = "figS13_rem_seasonality"
SOURCES = [
    "docs/study/corpus/tables/S13_rem_seasonality.csv",
    "docs/study/corpus/tables/E18_rem_monthly_series.csv",
]
NOTE = ("Redraws the six panels of plate S13 — the published within-year monthly index of A05 "
        "strict-autism entries, the variant PDD family, broad PDD 2019–2020, the legacy A03 M-CHAT "
        "and the M-CHAT-R/F part-1 results by era, plus the establishments with a row in each month "
        "— from the S13 presentation table, with E18 read only to check the same months against a "
        "second published table.")

TABLE = ROOT/"docs"/"study"/"corpus"/"tables"/"S13_rem_seasonality.csv"
E18 = ROOT/"docs"/"study"/"corpus"/"tables"/"E18_rem_monthly_series.csv"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_X = np.arange(1, 13)

# One colour per year, used in every panel the year appears in: the two pre-2021 years are the
# neutral pair (grey, black) of the stored plate, the A05 years its Okabe-Ito run.
YEAR_COLOUR = {2019: "#9e9e9e", 2020: BLACK, 2021: SKY, 2022: BLUE, 2023: GREEN, 2024: GOLD, 2025: ORANGE}

# The `Series` labels of the table, verbatim — the five indexed series and the two count series.
S_A05_STRICT = "A05 strict-autism entries"
S_A05_FAMILY = "A05 PDD-family entries (variant)"
S_A05_BROAD = "A05 broad-PDD entries"
S_A03_LEGACY = "A03 legacy M-CHAT done"
S_A03_MCHAT_RF = "A03 M-CHAT-R/F part-1 results"
S_EST_BROAD = "A05 broad PDD: establishments with a row"
S_EST_STRICT = "A05 strict autism: establishments with a row"

# The stored plate's headings, with the break panel (f) prints.
TITLES = {
    "a": "(a) A05 strict-autism entries",
    "b": "(b) A05 PDD-family entries (variant)",
    "c": "(c) A05 broad PDD entries 2019–2020",
    "d": "(d) A03 legacy M-CHAT done 2019–2022",
    "e": "(e) A03 M-CHAT-R/F results (part 1) by era",
    "f": "(f) A05 entries: establishments with a row by\nmonth",
}
# The stored plate's y limits, measured off its axes: the three panels whose index stays near 100
# share one scale, and the three with a spike, a legacy era or a count axis have their own headroom
# for the legend that sits over the data.
YTOP = {"a": 180.0, "b": 180.0, "c": 238.0, "d": 626.0, "e": 180.0, "f": 655.0}

INDEX_LABEL = "Monthly index (annual mean = 100)"
COUNT_LABEL = "Establishments with a row in the month (n)"
LEGEND_TITLE = "n = reporting establishments"
ANNOTATION = "#555555"
ANNOTATION_SIZE = 8.8

# The canvas and the panel rectangles of the stored plate, 1000 x 1361 px at 100 dpi.
FIG_W_IN, FIG_H_IN = 10.0, 13.61
COL_X = (0.055, 0.564)          # left edge of the left-hand and the right-hand column
PANEL_W = 0.432
ROW_Y = (0.713079, 0.380235, 0.032329)          # bottom edge of each row of panels
ROW_H = (0.268920, 0.268552, 0.268920)
HEAD_X = (0.013, 0.513)         # the heading starts left of its axes, as the stored plate sets it
HEAD_GAP = 0.0022               # and its last line sits just above the top of the axes


# --------------------------------------------------------------------------- reading the table
def _num(s):
    """One formatted number -> float; 'n/e' (not estimable) and blanks -> nan."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-"))


def _pair(s):
    """E18 prints `total (establishments)`: '56 (38)' -> (56.0, 38.0); '2,085' -> (2085.0, nan)."""
    text = str(s).strip()
    if "(" not in text:
        return _num(text), float("nan")
    head, tail = text.split("(", 1)
    return _num(head), _num(tail.rstrip(")"))


def _table():
    """The S13 table with its four numeric columns parsed and its months in calendar order."""
    t = pd.read_csv(TABLE, encoding="utf-8-sig", dtype=str)
    t["year"] = t["Year"].map(_num).astype(int)
    t["total"] = t["Month total"].map(_num)
    t["establishments"] = t["Establishments with a row in the month"].map(_num)
    t["reporting"] = t["Reporting establishments in the year"].map(_num)
    t["index"] = t["Index (annual mean = 100)"].map(_num)      # 'n/e' on the two count series
    t["Month"] = pd.Categorical(t["Month"], categories=MONTHS, ordered=True)
    return t


def _year_rows(t, series, year):
    """One series-year as twelve rows in calendar order; a month with no row stays blank."""
    rows = t[(t["Series"] == series) & (t["year"] == year)].set_index("Month")
    return rows.reindex(MONTHS)


def _years(t, series):
    return sorted(t.loc[t["Series"] == series, "year"].unique())


def _check_index(t):
    """The published index is month total / the year's 12-month mean x 100, to its own decimal."""
    for (series, year), g in t[t["index"].notna()].groupby(["Series", "year"]):
        rows = _year_rows(t, series, year)
        recomputed = np.round(rows["total"] / rows["total"].mean() * 100, 1)
        gap = float((recomputed - rows["index"]).abs().max())
        assert gap <= 0.05, f"{series} {year}: index is not total / annual mean ({gap:.2f})"
        assert len(g) == 12, f"{series} {year}: {len(g)} months, not 12"


def _cross_check(t):
    """The S13 months against E18, the second table that publishes the same REM series."""
    e18 = pd.read_csv(E18, encoding="utf-8-sig", dtype=str)
    same = {"A05 Strict autism": S_A05_STRICT,
            "A05 Broad PDD (pre-2021)": S_A05_BROAD,
            "M-CHAT performed (children with an alteration)": S_A03_LEGACY}
    for e18_series, s13_series in same.items():
        for _, row in e18[e18["Series"] == e18_series].iterrows():
            rows = _year_rows(t, s13_series, int(_num(row["Year"])))
            pairs = [_pair(row[m]) for m in MONTHS]
            assert np.allclose([p[0] for p in pairs], rows["total"].values), \
                f"{e18_series} {row['Year']}: E18 month totals differ from S13"
            assert np.allclose([p[1] for p in pairs], rows["establishments"].values), \
                f"{e18_series} {row['Year']}: E18 establishment counts differ from S13"
            assert np.isclose(_num(row["Year total"]), rows["total"].sum()), \
                f"{e18_series} {row['Year']}: the months do not add to the published year total"


# --------------------------------------------------------------------------- panel furniture
def _month_axis(ax):
    ax.set_xticks(MONTH_X)
    ax.set_xticklabels(MONTHS)
    ax.set_xlabel("Month")


def _line(ax, values, year, label, dashed=False):
    """One year of one series; nan months are left blank, which is what a missing row must be."""
    ax.plot(MONTH_X, np.asarray(values, dtype=float), marker="o", color=YEAR_COLOUR[year],
            ls="--" if dashed else "-", label=label)


def _index_panel(ax, t, series, key, legend_kw, eras=None):
    """One of the five index panels: a line per year, the annual mean drawn at 100."""
    for year in _years(t, series):
        rows = _year_rows(t, series, year)
        era = str(rows["Definition era"].dropna().iloc[0])
        n = num(rows["reporting"].dropna().iloc[0], "en")
        label = f"{year} (n={n})" if eras is None else f"{year} (n={n}) · {era}"
        _line(ax, rows["index"], year, label, dashed=eras is not None and era == eras)
    ax.axhline(100, color="#888888", ls="--", lw=1.0, zorder=1)
    _month_axis(ax)
    ax.set_ylim(0, YTOP[key])
    ax.set_ylabel(INDEX_LABEL)
    ax.legend(title=LEGEND_TITLE, **legend_kw)
    clean(ax, "both")


def _heading(fig, ax, key):
    """The stored plate heads every panel with its parenthesised letter and title in one bold line,
    starting left of the axes and sitting on the top of the axes however many lines it wraps to."""
    x = HEAD_X[0] if ax.get_position().x0 < 0.5 else HEAD_X[1]
    fig.text(x, ax.get_position().y1 + HEAD_GAP, TITLES[key], fontweight="bold", fontsize=12.5,
             ha="left", va="bottom", linespacing=1.1)


# --------------------------------------------------------------------------- the plate
def draw():
    t = _table()
    _check_index(t)
    _cross_check(t)

    style()
    plt.rcParams.update({
        "xtick.labelsize": 9.5, "ytick.labelsize": 8.3, "axes.labelsize": 11,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 4, "ytick.major.pad": 5.5,
        "lines.linewidth": 2.2, "lines.markersize": 7.0,
        "legend.fontsize": 8.8, "legend.title_fontsize": 8.8, "legend.frameon": True,
        "legend.framealpha": 0.95, "legend.facecolor": "white", "legend.edgecolor": "0.8",
        "legend.borderpad": 0.25, "legend.labelspacing": 0.2, "legend.columnspacing": 0.8,
        "legend.handlelength": 1.6, "legend.handletextpad": 0.5,
    })

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    ax = {}
    for i, key in enumerate("abcdef"):
        row, col = divmod(i, 2)
        ax[key] = fig.add_axes([COL_X[col], ROW_Y[row], PANEL_W, ROW_H[row]])

    # (a) A05 strict autism, 2021–2025 --------------------------------------------------------------
    _index_panel(ax["a"], t, S_A05_STRICT, "a", dict(loc="lower right", ncol=2))

    # (b) the variant's PDD family on the same five years -------------------------------------------
    _index_panel(ax["b"], t, S_A05_FAMILY, "b", dict(loc="upper left", ncol=2))

    # (c) the pre-2021 era: broad PDD 06902600, never joined to (a) ----------------------------------
    _index_panel(ax["c"], t, S_A05_BROAD, "c", dict(loc="upper left", ncol=2))
    ax["c"].text(0.98, 0.985, "Reporting disruption 2020", transform=ax["c"].transAxes,
                 ha="right", va="top", fontsize=ANNOTATION_SIZE, color=ANNOTATION)

    # (d) the legacy A03 M-CHAT, with the February 2019 file value left uncorrected -------------------
    _index_panel(ax["d"], t, S_A03_LEGACY, "d", dict(loc="upper left", ncol=2))
    feb_2019 = _year_rows(t, S_A03_LEGACY, 2019).loc["Feb", "total"]
    ax["d"].text(0.98, 0.50, f"Feb 2019: {num(feb_2019, 'en')} records (outlying file value)",
                 transform=ax["d"].transAxes, ha="right", va="center", fontsize=ANNOTATION_SIZE,
                 color=ANNOTATION)

    # (e) M-CHAT-R/F part 1: the 2023–24 codes and the 2025 redesign, as two code families ------------
    _index_panel(ax["e"], t, S_A03_MCHAT_RF, "e", dict(loc="upper left", ncol=1), eras="2025 era")

    # (f) the reporting itself: establishments with a row in the month, on a count axis ---------------
    for series, dashed in ((S_EST_BROAD, True), (S_EST_STRICT, False)):
        # 'A05 broad PDD: establishments with a row' -> 'broad PDD', the plate's own legend wording.
        what = series.split("A05 ", 1)[1].split(":", 1)[0]
        for year in _years(t, series):
            rows = _year_rows(t, series, year)
            _line(ax["f"], rows["establishments"], year, f"{year} · {what}", dashed=dashed)
    _month_axis(ax["f"])
    ax["f"].set_ylim(0, YTOP["f"])
    ax["f"].set_ylabel(COUNT_LABEL)
    ax["f"].legend(loc="upper left", ncol=2, frameon=True, framealpha=1.0, facecolor="white",
                   edgecolor="none")   # the original covers the gridlines behind its legend
    clean(ax["f"], "both")

    for key in "abcdef":
        _heading(fig, ax[key], key)
    return fig


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE/f"{PLATE}_redraw.png"
    draw().savefig(out, dpi=100, facecolor="white")
    print("wrote", out)
