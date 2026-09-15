"""figE24 — educational recognition of autism: PIE, SINACES and special schools, 2019–2025.

The stored plate `docs/study/corpus/figures/figE24_education_detail.jpg` was drawn by
`study/pipeline/15_extra_figures_context.py` from `outputs/tidy/pie_series.csv` and
`education_summary_year.csv`, neither of which travels with this repository. Every number its six
panels print survives in two tracked tables, so the whole plate is redrawn here from them:

  * `docs/study/corpus/tables/E76_education_pie_full.csv` — the 29 named PIE/SINACES series with
    page-level provenance. It carries the counts of panels (a), (b), (d) and (f), the 2023 sex
    counts of panel (e), and — the reason it is the primary source rather than E24 — the three
    share series of panel (c) to two decimals (5.44 … 13.46, 3.08 … 10.05, 9.79 … 22.45). E24
    rounds those to one decimal ("5.4%"), which cannot reproduce the plate's own end labels.
  * `docs/study/corpus/tables/E24_education_detail.csv` — the plate's presentation table. Its three
    trailing rows give the 2023 male-to-female ratios with the intervals the plate prints under
    panel (e) ("4.03 (3.94–4.12)"), and the 2022 discrepancy row gives the documented five-case gap
    quoted in the red foot note. Those strings are parsed, never recomputed.

Unit and estimator, unchanged from the original: an annual school stock, a plain count of students.
Nothing here is a rate, a weighted estimate or a standardised figure, so no estimator can drift. The
three definition rules of the original are kept exactly:

  1. The two harmonised series stay SEPARATE. `pie_harmonised_apuntes60` (2019–2023, Apuntes 60) is
     the green line and `pie_harmonised_sinaces` (2022–2025, SINACES) the pink dashed one; they
     disagree by five cases in 2022 (42,940 against 42,945) and panel (b) exists to show that gap.
     E76's `pie_harmonised` row, which splices the two into one 2019–2025 series, is deliberately
     NOT read: splicing it would erase the panel. The five cases are shown, never corrected.
  2. Special schools are not added to PIE. Panel (d) draws the SINACES total — which already
     contains them — and overlays the special-school count at the foot of the same bar.
  3. Panel (e) is the only published sex year, and the interval under each of its categories is
     the published exact binomial. It is parsed from E24, never recomputed for the drawing;
     `_check()` confirms that Clopper–Pearson limits on the male share, turned back into a
     ratio, reproduce all three printed pairs (4.03 3.94–4.12, 4.60 4.42–4.79, 1.50 1.49–1.51).

These series are identical in both case-definition variants (`sin_rett` and `con_rett`), as E24
itself records, so this plate takes no variant argument. The corpus is English only and so is this
module: it takes no language argument and draws no Spanish variant.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

_STUDY = Path(__file__).resolve().parents[1]          # docs/study, where figstyle lives
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))

from figstyle import *   # noqa: F401,F403 — style, clean, num, thousands, log_axis, BLUE, ORANGE, …

PLATE = "figE24_education_detail"
SOURCES = [
    "docs/study/corpus/tables/E76_education_pie_full.csv",
    "docs/study/corpus/tables/E24_education_detail.csv",
]
NOTE = ("Redraws the six panels of figE24 — the four PIE series by definition and source, the "
        "documented five-case discrepancy of 2022, the three share series, the SINACES total with "
        "the special schools it contains, the 2023 sex split on a log axis and the regular against "
        "exceptional entry — from the published PIE/SINACES series table E76 and, for the 2023 "
        "male-to-female ratios with their exact binomial intervals, from the plate's own table E24.")

TABLE_E76 = BASE / "corpus" / "tables" / "E76_education_pie_full.csv"
TABLE_E24 = BASE / "corpus" / "tables" / "E24_education_detail.csv"

# --------------------------------------------------------------------------------------------------
# The plate norm of study/pipeline: 180 × 245 mm, three rows by two columns, 9 pt bold panel titles
# over a 6 pt floor, DejaVu Sans throughout, seaborn's white grid with the ticks themselves hidden.
# --------------------------------------------------------------------------------------------------
PLATE_W_IN, PLATE_H_IN = 180.0 / 25.4, 245.0 / 25.4
FS_TITLE, FS_BASE, FS_TICK, FS_LEG = 9.0, 8.0, 7.0, 7.0
FS_MARK, FS_CELL = 6.2, 6.4          # context markers; the wrapped category labels of (b) and (e)
FOOT_FS, FOOT_LINE = 6.4, 1.30
DARK, GLOSS, RED = "#333333", "#555555", "#c0392b"
#: The two white haloes the original's engine adds just before saving: a firm one under a context
#: note written in axis coordinates, a lighter one under a value label that falls on its own bar.
NOTE_HALO = dict(facecolor="white", edgecolor="none", alpha=0.92, pad=1.4)
VALUE_HALO = dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9)
LIGHT_BLUE = "#9ecae1"               # the SINACES total of panel (d), as in the original
LAW_X = 2023 - 0.30                  # March 2023 on an axis of centred years (study/config LAW_YEAR)
PANDEMIC = [2020, 2021]

PLATE_RC = {
    "font.family": "DejaVu Sans", "font.size": FS_BASE,
    "axes.titlesize": FS_TITLE, "axes.titleweight": "bold", "axes.labelsize": FS_BASE,
    "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "legend.fontsize": FS_LEG, "legend.title_fontsize": FS_LEG,
    # The plate's own legend settings: a translucent white box with no edge, and matplotlib's own
    # spacing for everything the plate style does not override (only the inner pad is tightened).
    "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
    "legend.edgecolor": "none", "legend.borderpad": 0.25,
    "axes.facecolor": "white", "axes.edgecolor": DARK, "axes.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True,
    "grid.color": "#cccccc", "grid.alpha": 0.35, "grid.linewidth": 0.8,
    "xtick.bottom": False, "ytick.left": False,           # seaborn's white grid: no tick marks
    "xtick.major.pad": 2.6, "ytick.major.pad": 2.6,
    "lines.linewidth": 1.3, "lines.markersize": 4.0,
    "axes.labelpad": 2.2, "axes.titlepad": 3.5,
    "figure.facecolor": "white", "savefig.facecolor": "white",
}

# Panel geometry, read off the stored plate (1000 × 1361 px) and kept as fractions of the canvas.
_W, _H = 1000.0, 1361.0


def _rect(left, top, right, bottom):
    return [left / _W, (_H - bottom) / _H, (right - left) / _W, (bottom - top) / _H]


BOXES = {
    "a": _rect(75, 32, 492, 272),
    "b": _rect(568, 31, 985, 359),
    "c": _rect(75, 493, 492, 754),
    "d": _rect(568, 493, 985, 820),
    "e": _rect(75, 909, 492, 1236),
    "f": _rect(568, 909, 985, 1236),
}
#: Left edge of each column of panel titles, in figure fractions: the stored plate anchors the title
#: to the visible left edge of the column (the rotated y-axis label), not to the axes box.
TITLE_X = {"a": 0.0105, "c": 0.0105, "e": 0.0105, "b": 0.5180, "d": 0.5180, "f": 0.5180}

TITLES = {
    "a": "PIE series by definition and source",
    "b": "The 2022 discrepancy in harmonised PIE",
    "c": "PIE autism as a share of PIE enrolment and\nof applicants",
    "d": "Special schools and SINACES total",
    "e": "Sex split, 2023 (the only published year)",
    "f": "Regular and exceptional entry to PIE",
}

Y_STUDENTS = "Students (thousands)"
Y_SHARE = "Share (%)"
X_YEAR = "Year"
LAW_MARK = "Law 21.545 (2023)"
PANDEMIC_MARK = "2020–2021 (pandemic)"

FOOT_GREY = ("(a) Harmonisation rule: strict autism + autism-Asperger (Apuntes 60, 2019–2023); "
             "SINACES publishes the harmonised total for 2022–2025. (e) the figure\n"
             "under each category is the male-to-female ratio with its 95% CI.")
FOOT_RED = ("(b) Documented discrepancy: {gap} cases between the published total and the "
            "subtraction.")

#: Where the bold end label of a series goes, relative to its last point. The plate writes every one
#: of them five points right and two up; the two series that run to 2025 would then hang over the
#: neighbouring cell, and the original's de-overlap pass pulls them back inside before saving — the
#: 2025 count to the left of its diamond, the 2025 share squarely above its triangle, clear of the
#: line that climbs into it. Those two placements are measured off the stored plate.
END_LABEL = dict(xytext=(5, 2), ha="left")
END_LABEL_PULLED_LEFT = dict(xytext=(0, 2), ha="right")
END_LABEL_LIFTED = dict(xytext=(0, 10), ha="center")

#: (a) the four series of the first panel: E76 row, colour, marker, line style, label, end label.
SERIES_A = [
    ("pie_tea_strict", BLUE, "o", "-", "PIE strict autism (Apuntes 60)", END_LABEL),
    ("pie_tea_asperger", ORANGE, "s", "-", "PIE autism-Asperger (Apuntes 60)", END_LABEL),
    ("pie_harmonised_apuntes60", GREEN, "^", "-", "Harmonised PIE (Apuntes 60, 2019–2023)",
     END_LABEL),
    ("pie_harmonised_sinaces", PINK, "D", "--", "Harmonised PIE (SINACES, 2022–2025)",
     END_LABEL_PULLED_LEFT),
]
#: (c) the three share series: E76 row, colour, marker, legend label, end label.
SERIES_C = [
    ("pie_harmonised_share_of_pie_pct", BLUE, "o", "Harmonised PIE / PIE enrolment", END_LABEL),
    ("pie_tea_strict_share_of_pie_pct", ORANGE, "s", "Strict autism / PIE enrolment", END_LABEL),
    ("pie_tea_share_of_applicants_pct", GREEN, "^", "Harmonised PIE / SINACES applicants",
     END_LABEL_LIFTED),
]
#: (b) the five bars of the discrepancy panel: E76 row, wrapped label, colour.
BARS_B = [
    ("sinaces_total_autistic_students", "SINACES\ntotal 2022", GOLD),
    ("special_schools_autism", "Special\nschools", ORANGE),
    ("sinaces_total_minus_special", "Total −\nspecial\nschools", BLUE),
    ("pie_harmonised_sinaces", "Published\nharmonised\nPIE\n(SINACES)", PINK),
    ("pie_harmonised_apuntes60", "Harmonised\nPIE\n(Apuntes\n60)", GREEN),
]
#: (e) the three categories of the sex panel: E76 male row, E76 female row, E24 ratio row, label.
SEX_E = [
    ("pie_tea_strict_male", "pie_tea_strict_female", "Strict autism 2023 by sex", "Strict\nautism"),
    ("pie_tea_asperger_male", "pie_tea_asperger_female", "Autism-Asperger 2023 by sex",
     "Autism-\nAsperger"),
    ("pie_total_enrolment_male", "pie_total_enrolment_female", "PIE enrolment 2023 by sex",
     "Total PIE\nenrolment"),
]

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
DISCREPANCY_YEAR = 2022


# --------------------------------------------------------------------------------------------------
# Reading the two tracked tables
# --------------------------------------------------------------------------------------------------
def _value(cell):
    """A year cell of E76: '106,786' or '13.46' to a float, 'not reported' to NaN."""
    s = str(cell).strip()
    if not s or s.lower() in {"not reported", "n/e", "nan", "-", "—"}:
        return np.nan
    return float(s.replace(",", ""))


def read_series():
    """Every E76 row as {year: value}, keyed by the row's own `Series` name."""
    raw = pd.read_csv(TABLE_E76, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    out = {}
    for _, row in raw.iterrows():
        out[row["Series"].strip()] = {y: _value(row[str(y)]) for y in YEARS}
    return out


_RATIO = re.compile(r"ratio:\s*([\d.]+)\s*\(\s*([\d.]+)\s*[–-]\s*([\d.]+)\s*\)")
_GAP = re.compile(r"gap\s+(\d+)")


def read_published():
    """The presentation table E24, keyed by its first column.

    Returns (ratios, gap): the three 2023 male-to-female ratio strings already split into
    (point, low, high), and the documented number of cases of the 2022 discrepancy.
    """
    raw = pd.read_csv(TABLE_E24, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    key = raw.columns[0]
    rows = {str(r[key]).strip(): r for _, r in raw.iterrows()}

    ratios = {}
    for label, row in rows.items():
        if not label.endswith("by sex"):
            continue
        m = _RATIO.search(" ".join(str(v) for v in row.values))
        if m:
            ratios[label] = tuple(float(g) for g in m.groups())

    gap_row = " ".join(str(v) for v in rows["2022 discrepancy"].values)
    gap = int(_GAP.search(gap_row).group(1))
    return ratios, gap


def _points(series, key):
    """The (years, values) actually reported for one E76 row, NaN years dropped."""
    pairs = [(y, v) for y, v in sorted(series[key].items()) if np.isfinite(v)]
    return np.array([p[0] for p in pairs], dtype=float), np.array([p[1] for p in pairs], dtype=float)


# --------------------------------------------------------------------------------------------------
# Small drawing helpers, in the plate's own conventions
# --------------------------------------------------------------------------------------------------
def _n(x, dec=0):
    return num(x, "en", dec)


def _pct(x, dec=1):
    return _n(x, dec) + "%"


def _context_markers(ax):
    """The pandemic band and the Law 21.545 marker, both labels in a reserved band at the top.

    The plate reserves 16% of the panel height above the series, shades each pandemic year and
    writes the two labels inside that band — never over the data. The law label is right-aligned
    against its dotted line and sits one line lower than the pandemic label, which is where the
    original's de-overlap pass leaves it: centred over 2020–2021, the two labels would touch.
    """
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, lo + (hi - lo) * 1.16)
    for year in PANDEMIC:
        ax.axvspan(year - 0.5, year + 0.5, color="grey", alpha=0.12, lw=0, zorder=0)
    ax.annotate(PANDEMIC_MARK, (float(np.mean(PANDEMIC)), 0.988),
                xycoords=ax.get_xaxis_transform(), xytext=(0, 0), textcoords="offset points",
                fontsize=FS_MARK, color=GLOSS, ha="center", va="top", zorder=6,
                bbox=dict(NOTE_HALO))
    ax.axvline(LAW_X, color=DARK, ls=":", lw=1.1, zorder=0)
    ax.annotate(LAW_MARK + " ", (LAW_X, 0.988), xycoords=ax.get_xaxis_transform(),
                xytext=(0, -8), textcoords="offset points", fontsize=FS_MARK, color=DARK,
                ha="right", va="top", zorder=6, bbox=dict(NOTE_HALO))


def _below_legend(ax, y):
    """The legend of a time panel, centred under its x-axis label as the stored plate places it."""
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, y), fontsize=FS_LEG,
                    labelspacing=0.27)
    leg.set_in_layout(False)
    return leg


def _title(ax, ch):
    """Panel title: the parenthesised lowercase letter, then the title, both bold and left-aligned
    on the visible left edge of the column rather than on the axes box."""
    pos = ax.get_position()
    x = (TITLE_X[ch] - pos.x0) / pos.width
    ax.set_title(f"({ch}) {TITLES[ch]}", loc="left", x=x, fontsize=FS_TITLE, fontweight="bold",
                 pad=3.5, linespacing=1.15)


def _foot(fig, gap):
    """The plate's foot: the grey panel notes of (a) and (e), and the red note of (b) under them."""
    lh = FOOT_FS * FOOT_LINE / (PLATE_H_IN * 72.0)
    space = 0.35 * lh
    y = 0.004
    for block, colour in ((FOOT_RED.format(gap=_n(gap)), RED), (FOOT_GREY, GLOSS)):
        fig.text(0.008, y, block, fontsize=FOOT_FS, color=colour, va="bottom", ha="left",
                 linespacing=FOOT_LINE)
        y += (block.count("\n") + 1) * lh + space


# --------------------------------------------------------------------------------------------------
# The six panels
# --------------------------------------------------------------------------------------------------
def _panel_a(ax, series):
    """(a) the four PIE series, in thousands of students, with the last value of each labelled."""
    top = 0.0
    for key, colour, marker, ls, label, place in SERIES_A:
        x, v = _points(series, key)
        ax.plot(x, v / 1e3, marker + ls, color=colour, lw=2, markersize=6, label=label, zorder=3)
        ax.annotate(_n(v[-1]), (x[-1], v[-1] / 1e3), textcoords="offset points", fontsize=7,
                    color=colour, fontweight="bold", zorder=5, **place)
        top = max(top, float(v.max()))
    ax.set_xticks(YEARS)
    ax.set_xlabel(X_YEAR)
    ax.set_ylabel(Y_STUDENTS)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_ylim(0, top / 1e3 * 1.35)
    _context_markers(ax)
    clean(ax, grid="both")
    _below_legend(ax, -0.156)


def _panel_b(ax, series, year=DISCREPANCY_YEAR):
    """(b) the five figures of the 2022 discrepancy, each printed over its bar."""
    values = [series[key][year] for key, _, _ in BARS_B]
    x = np.arange(len(BARS_B))
    ax.bar(x, [v / 1e3 for v in values], width=0.62, color=[c for _, _, c in BARS_B], zorder=3)
    for xi, v in zip(x, values):
        ax.text(xi, v / 1e3 + 0.6, _n(v), ha="center", va="bottom", fontsize=7.5, color=DARK,
                fontweight="bold", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab, _ in BARS_B], fontsize=FS_MARK, linespacing=1.15)
    ax.set_ylabel(Y_STUDENTS)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_ylim(0, max(values) / 1e3 * 1.28)
    clean(ax, grid="both")


def _panel_c(ax, series):
    """(c) the two shares of PIE enrolment and the share of SINACES applicants."""
    for key, colour, marker, label, place in SERIES_C:
        x, v = _points(series, key)
        ax.plot(x, v, marker + "-", color=colour, lw=2, markersize=6, label=label, zorder=3)
        ax.annotate(_pct(v[-1]), (x[-1], v[-1]), textcoords="offset points", fontsize=7,
                    color=colour, fontweight="bold", zorder=5, **place)
    ax.set_xticks(YEARS)
    ax.set_xlabel(X_YEAR)
    ax.set_ylabel(Y_SHARE)
    ax.set_ylim(0, ax.get_ylim()[1])
    _context_markers(ax)
    clean(ax, grid="both")
    _below_legend(ax, -0.141)


def _panel_d(ax, series):
    """(d) the SINACES total with, at the foot of the same bar, the special schools it contains.

    The special-school count is drawn INSIDE the total, never stacked on top of it: SINACES
    publishes 'total = special autism school + PIE', so adding the two would double-count.
    """
    xt, total = _points(series, "sinaces_total_autistic_students")
    xs, special = _points(series, "special_schools_autism")
    ax.bar(xt, total / 1e3, width=0.6, color=LIGHT_BLUE, label="SINACES total autistic students",
           zorder=3)
    ax.bar(xs, special / 1e3, width=0.6, color=ORANGE, label="Special schools (autism)", zorder=4)
    for xi, v in zip(xs, special):
        ax.text(xi, v / 1e3 + 1.5, _n(v), ha="center", va="bottom", fontsize=7, color=ORANGE,
                zorder=5, bbox=dict(VALUE_HALO))   # the label falls on its own bar, so it is haloed
    ax.set_xticks(sorted(set(xt) | set(xs)))
    ax.set_xlabel(X_YEAR)
    ax.set_ylabel(Y_STUDENTS)
    ax.yaxis.set_major_formatter(thousands("en"))
    clean(ax, grid="both")
    leg = ax.legend(loc="upper left", fontsize=7.5)
    leg.set_in_layout(False)


def _panel_e(ax, series, ratios):
    """(e) the 2023 sex split on a log axis, the ratio and its interval under each category."""
    x = np.arange(len(SEX_E))
    male = np.array([series[m][2023] for m, _, _, _ in SEX_E])
    female = np.array([series[f][2023] for _, f, _, _ in SEX_E])
    ax.bar(x - 0.2, male / 1e3, width=0.38, color=BLUE, label="Males", zorder=3)
    ax.bar(x + 0.2, female / 1e3, width=0.38, color=ORANGE, label="Females", zorder=3)
    log_axis(ax, "y", "en")
    both = np.concatenate([male, female]) / 1e3
    ax.set_ylim(max(0.5, float(both.min()) * 0.35), float(both.max()) * 8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{lab}\n{_n(ratios[row][0], 2)} "
                        f"({_n(ratios[row][1], 2)}–{_n(ratios[row][2], 2)})"
                        for _, _, row, lab in SEX_E], fontsize=FS_CELL, linespacing=1.15)
    ax.set_ylabel(Y_STUDENTS)
    clean(ax, grid="both")
    leg = ax.legend(loc="upper left", fontsize=7.5)
    leg.set_in_layout(False)


def _panel_f(ax, series):
    """(f) regular against exceptional entry, with the exceptional share over its own bar."""
    xr, regular = _points(series, "pie_tea_regular_entry")
    xe, exceptional = _points(series, "pie_tea_exceptional_entry")
    ax.bar(xr - 0.19, regular / 1e3, width=0.36, color=BLUE, label="Regular entry", zorder=3)
    ax.bar(xe + 0.19, exceptional / 1e3, width=0.36, color=ORANGE, label="Exceptional entry",
           zorder=3)
    share = {y: 100 * e / (r + e) for y, r, e in zip(xe, regular, exceptional)}
    for xi, v in zip(xe, exceptional):
        ax.text(xi + 0.19, v / 1e3 + 1.2, _pct(share[xi], 0), ha="center", va="bottom",
                fontsize=6.8, color=DARK, zorder=5)
    ax.set_xticks(sorted(set(xr) | set(xe)))
    ax.set_xlabel(X_YEAR)
    ax.set_ylabel(Y_STUDENTS)
    ax.yaxis.set_major_formatter(thousands("en"))
    clean(ax, grid="both")
    leg = ax.legend(loc="upper left", fontsize=7.5)
    leg.set_in_layout(False)


# --------------------------------------------------------------------------------------------------
def draw():
    series = read_series()
    ratios, gap = read_published()

    style()
    plt.rcParams.update(PLATE_RC)
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN))
    ax = {ch: fig.add_axes(BOXES[ch]) for ch in "abcdef"}

    _panel_a(ax["a"], series)
    _panel_b(ax["b"], series)
    _panel_c(ax["c"], series)
    _panel_d(ax["d"], series)
    _panel_e(ax["e"], series, ratios)
    _panel_f(ax["f"], series)
    for ch in "abcdef":
        _title(ax[ch], ch)
    _foot(fig, gap)
    return fig


# --------------------------------------------------------------------------------------------------
# Verification: every drawn figure against the plate's own presentation table, E24
# --------------------------------------------------------------------------------------------------
def _check():
    """Compare what the panels draw, read from E76, with what E24 prints for the same cell."""
    series = read_series()
    raw = pd.read_csv(TABLE_E24, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    by_year = {int(r[raw.columns[0]]): r for _, r in raw.iterrows()
               if str(r[raw.columns[0]]).strip().isdigit()}
    out = []

    columns = [("Strict autism", "pie_tea_strict"),
               ("Autism-Asperger", "pie_tea_asperger"),
               ("Harmonised (Apuntes 60)", "pie_harmonised_apuntes60"),
               ("Harmonised (SINACES)", "pie_harmonised_sinaces"),
               ("Special schools", "special_schools_autism"),
               ("Regular entry", "pie_tea_regular_entry"),
               ("Exceptional entry", "pie_tea_exceptional_entry")]
    for column, key in columns:
        for year, row in by_year.items():
            printed, drawn = _value(row[column]), series[key][year]
            if np.isnan(printed) and np.isnan(drawn):
                continue
            out.append((f"{column} {year}", drawn, printed,
                        bool(np.isfinite(drawn) and np.isfinite(printed) and drawn == printed)))

    # (c): the one-decimal shares E24 prints must be the two-decimal E76 shares this module draws
    for column, key in (("% of PIE enrolment", "pie_harmonised_share_of_pie_pct"),
                        ("% of SINACES applicants", "pie_tea_share_of_applicants_pct")):
        for year, row in by_year.items():
            cell = str(row[column]).strip()
            if not cell.endswith("%"):
                continue
            drawn, printed = series[key][year], float(cell.rstrip("%"))
            out.append((f"{column} {year}", round(drawn, 1), printed, round(drawn, 1) == printed))

    # (b): the SINACES total, the subtraction and the published harmonised figure of 2022
    total = series["sinaces_total_autistic_students"][DISCREPANCY_YEAR]
    special = series["special_schools_autism"][DISCREPANCY_YEAR]
    derived = series["sinaces_total_minus_special"][DISCREPANCY_YEAR]
    published = series["pie_harmonised_sinaces"][DISCREPANCY_YEAR]
    _ratios, gap = read_published()
    out += [("(b) total − special = derived", total - special, derived, total - special == derived),
            ("(b) documented gap", published - derived, float(gap), published - derived == gap),
            ("(b) Apuntes 60 equals the subtraction",
             series["pie_harmonised_apuntes60"][DISCREPANCY_YEAR], derived,
             series["pie_harmonised_apuntes60"][DISCREPANCY_YEAR] == derived)]

    # (e): the parsed ratios and their intervals against male / female of the same year. The
    # interval E24 publishes is an exact binomial on the male share, so Clopper–Pearson limits
    # turned back into a ratio must reproduce the printed pair; they are checked, never substituted.
    from scipy import stats
    ratios, _gap = read_published()
    for male, female, row, label in SEX_E:
        m, f = series[male][2023], series[female][2023]
        n = m + f
        lo = stats.beta.ppf(0.025, m, n - m + 1)
        hi = stats.beta.ppf(0.975, m + 1, n - m)
        drawn = [round(m / f, 2), round(float(lo / (1 - lo)), 2), round(float(hi / (1 - hi)), 2)]
        printed = [round(v, 2) for v in ratios[row]]
        out.append((f"(e) {label.replace(chr(10), ' ')} ratio (95% CI)", drawn, printed,
                    drawn == printed))

    # (f): the annotated share of exceptional entries
    for year in (2022, 2023, 2024, 2025):
        regular = series["pie_tea_regular_entry"][year]
        exceptional = series["pie_tea_exceptional_entry"][year]
        total_entry = series["pie_harmonised_sinaces"][year]
        out.append((f"(f) entries sum to the harmonised total {year}", regular + exceptional,
                    total_entry, regular + exceptional == total_entry))
    return out


if __name__ == "__main__":
    for name, drawn, printed, ok in _check():
        print(f"{'ok ' if ok else 'BAD'} {name}: redrawn {drawn} vs table {printed}")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(f"{PLATE}_redraw.png")
    draw().savefig(out, dpi=1000 / PLATE_W_IN, facecolor="white")
    print("wrote", out)
