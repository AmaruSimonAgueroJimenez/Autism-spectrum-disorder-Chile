"""Plate figS1 — does Rett syndrome (F84.2) move the GRD series? Redrawn from the tracked tables.

The stored plate was drawn by `study/pipeline/08a_figures_grd.py` from the GRD discharge microdata,
which this repository does not carry. Every series it shows survives in published aggregates, so the
six panels are redrawn here from those:

  (a) any position, all activity, both variants        `docs/study/data/grd_year_summary.csv`
  (b) principal F84, all activity, both variants       `docs/study/data/grd_year_summary.csv`
  (c) strict hospitalisation and CMA, both variants    `docs/study/data/grd_year_summary.csv`
  (d) F84.2 episodes, any position and principal       `docs/study/corpus/tables/ST10_grd_f84_subcodes.csv`
  (e) relative difference of five series               `docs/study/data/grd_year_summary.csv`
  (f) fixed panel of 65 hospitals and persons          `docs/study/data/grd_year_summary.csv`

THE ESTIMATOR, unchanged from the original. Unweighted administrative event counts. The rate is
100,000 x episodes with documented F84 / GRD episodes of the SAME panel and activity — the offset
sits in the file as `n_episodes_total_same_panel_activity` and is never swapped for a population
denominator, so these are episodes per 100,000 episodes and not a population rate. The intervals are
the exact Poisson limits already stored as `rate_lo`/`rate_hi`; nothing is recomputed here.
`persons_within_year` counts unique persons inside one year only and is never a person-level series
across years, because the identifier format changes between 2020 and 2021.

THE CASE DEFINITION IS THE SUBJECT OF THIS PLATE, so unlike every other GRD plate it keeps BOTH
variants side by side and filters to neither: `con_rett` is the full F84 family and `sin_rett` is
F84 without F84.2. The third variant in the file, `strict_autism_f840`, is a different case
definition altogether and does not belong here — the caption says the strict series do not change
between variants, and the stored plate does not draw them.

Two details of the original that are easy to get wrong and are kept here. Panel (d) cannot be taken
as `con_rett` minus `sin_rett`: that difference is 51 episodes in 2019, while F84.2 appears in 55,
because an episode carrying F84.2 alongside another F84 code stays inside `sin_rett` as well. The
F84.2 counts therefore come from the subcode table, and their percentage labels are F84.2 in any
position over the whole `con_rett` family of the same year. And the bars of panel (f) are the
persons of the OBSERVED panel, not of the fixed panel of 65 hospitals whose rates the same panel
draws on its log axis.

`_check_published()` runs before the figure is built and compares what will be drawn against three
independently published tables: the variant rates of `case_definition_variant_rates.csv` (panel a),
the counts and relative differences of `E28_variant_sensitivity.csv` (panels a, b and e) and the
F84.2 counts of `ST10_grd_f84_subcodes.csv` (panel d).

The corpus is English only, so this plate is English only.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, MultipleLocator, NullLocator

HERE = Path(__file__).resolve().parent          # docs/study/plates
STUDY = HERE.parent                             # docs/study
ROOT = STUDY.parent.parent                      # repository root
if str(STUDY) not in sys.path:                  # import figstyle the way the figure scripts do
    sys.path.insert(0, str(STUDY))
from figstyle import *                          # noqa: E402,F401,F403  (house style)

PLATE = "figS1_grd_variants"
SOURCES = [
    "docs/study/data/grd_year_summary.csv",
    "docs/study/corpus/tables/ST10_grd_f84_subcodes.csv",
    "docs/study/data/case_definition_variant_rates.csv",
    "docs/study/corpus/tables/E28_variant_sensitivity.csv",
]
YEAR_SUMMARY, SUBCODES, VARIANT_RATES, SENSITIVITY = SOURCES
NOTE = ("Redraws the six panels of figS1 — the GRD episode rate with and without Rett syndrome in "
        "any position, as principal diagnosis and by activity, the F84.2 episodes themselves, the "
        "relative difference of five series and the fixed panel of 65 hospitals with persons "
        "within year — from the tracked GRD annual summary and the published F84 subcode table, "
        "keeping both case-definition variants and the episode denominator of the original.")

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
WITH, WITHOUT = "con_rett", "sin_rett"          # full F84 family / F84 without F84.2
VARIANTS = [(WITH, BLUE, "with Rett"), (WITHOUT, ORANGE, "without Rett")]
CI_ALPHA = 0.15                                 # the exact-Poisson band of the stored plate
BAR_ALPHA = 0.25                                # the person bars of panel (f)
LINE_W, MS = 2.3, 6.5
# Law 21.545 was published on 10 March 2023. The stored plate marks it a little before the 2023
# position — the series are annual and sit on their year tick — and the marker is context only:
# no estimate on this plate depends on it.
LAW_X = 2023 - 0.3
LAW_COLOUR = "#333333"
RATE_LABEL = "Episodes with F84 per 100,000 GRD episodes"
# x limits as the stored plate has them: the line panels leave matplotlib's 5% margin around
# 2019-2024, the two bar panels (d and f) the same margin around the outer edge of their bars
LINE_XLIM = (2018.75, 2024.25)
BAR_XLIM = (2018.332, 2024.668)
# axes rectangles read off the stored plate (1000 x 1361 px), in figure fractions
BOXES = {
    "a": [0.0550, 0.71345, 0.3920, 0.26819], "b": [0.5450, 0.71345, 0.3850, 0.26819],
    "c": [0.0660, 0.38060, 0.3810, 0.26819], "d": [0.5530, 0.38060, 0.3760, 0.26819],
    "e": [0.0550, 0.03233, 0.3920, 0.26819], "f": [0.6360, 0.03233, 0.2930, 0.26819],
}
TITLES = [
    ("a", 0.013, 0.98457, "(a) Any position, all activity (observed panel)"),
    ("b", 0.513, 0.98457, "(b) Principal F84, all activity (observed panel)"),
    ("c", 0.012, 0.64952, "(c) Strict hospitalisation and CMA (any\nposition)"),
    ("d", 0.513, 0.64952, "(d) Episodes with F84.2 (Rett) by position"),
    ("e", 0.012, 0.30450, "(e) Relative difference with − without Rett by\nseries"),
    ("f", 0.512, 0.30450, "(f) Fixed panel of 65 and persons within year"),
]


# ------------------------------------------------------------- tracked tables and their parsing
def _read(rel, **kw):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT.joinpath(*rel.split("/")), **kw)


def _int(s):
    """'8,221' -> 8221 ; the presentation tables store counts as formatted strings."""
    return int(str(s).replace(",", "").replace(" ", "").replace(" ", "").strip())


def _summary():
    """The GRD annual summary, the grid of year x variant x panel x activity x position."""
    return _read(YEAR_SUMMARY)


def _ys(d, variant, panel, activity, position):
    """One cell series of that grid, ordered by year — the original's own selector."""
    s = d[(d.variant == variant) & (d.panel == panel) & (d.activity == activity)
          & (d.position == position)].sort_values("year")
    assert list(s.year) == YEARS, f"{variant}/{panel}/{activity}/{position}: {list(s.year)}"
    return s


def _subcodes():
    """F84.2 episodes by year, any position and principal, from the published subcode table."""
    t = _read(SUBCODES, encoding="utf-8-sig")
    t = t[t[t.columns[0]].str.startswith("F84.2")]
    out = {}
    for row_name, key in (("Any position", "any"), ("Principal diagnosis", "principal")):
        r = t[t["F84 code position"] == row_name]
        assert len(r) == 1, f"{row_name}: {len(r)} rows"
        out[key] = np.array([_int(r.iloc[0][str(y)]) for y in YEARS])
    return out


def _rel_difference(d):
    """(with - without) / without, in %, for the five series of panel (e).

    The denominator of a rate is identical in the two variants, so the relative difference of the
    rates is the relative difference of the counts; the original takes the counts, and the persons
    series takes `persons_within_year` on the same observed panel.
    """
    series = [
        ("Any position · all activity", BLUE, "o", ("observed", "all", "any"), "n_episodes_f84"),
        ("Principal · all activity", ORANGE, "s", ("observed", "all", "principal"),
         "n_episodes_f84"),
        ("Any position · hospitalisation", GREEN, "^", ("observed", "hospitalisation", "any"),
         "n_episodes_f84"),
        ("Any position · CMA", PINK, "D", ("observed", "cma", "any"), "n_episodes_f84"),
        ("Persons within year", GOLD, "v", ("observed", "all", "any"), "persons_within_year"),
    ]
    out = []
    for label, colour, marker, cell, column in series:
        with_, without = (_ys(d, v, *cell)[column].to_numpy(float) for v in (WITH, WITHOUT))
        out.append((label, colour, marker, 100 * (with_ - without) / without))
    return out


def _check_published(d, f842):
    """Compare every drawn value against the published tables before the figure is built."""
    bad = []

    rates = _read(VARIANT_RATES).set_index("year")           # panel (a), both variants
    for variant in (WITH, WITHOUT):
        drawn = _ys(d, variant, "observed", "all", "any")
        for year, rate in zip(drawn.year, drawn.rate_per_100k_episodes):
            want = float(rates.loc[year, variant])
            if round(float(rate), 2) != want:
                bad.append(f"rate {variant} {year}: {rate:.4f} vs published {want}")

    s = _read(SENSITIVITY, encoding="utf-8-sig")             # panels (a), (b) and (e)
    s = s.set_index([s.columns[0], "Year"])
    for row, cell in (("GRD · documented F84 (any position)", ("observed", "all", "any")),
                      ("GRD · principal F84", ("observed", "all", "principal"))):
        with_, without = (_ys(d, v, *cell).n_episodes_f84.to_numpy(float) for v in (WITH, WITHOUT))
        for i, year in enumerate(YEARS):
            r = s.loc[(row, year)]
            got = (with_[i], without[i], with_[i] - without[i])
            want = (_int(r["with Rett (full F84)"]), _int(r["without Rett (F84 except F84.2)"]),
                    _int(r["Absolute difference (cases)"]))
            if got != want:
                bad.append(f"{row} {year}: counts {got} vs published {want}")
            rel = 100 * (with_[i] - without[i]) / without[i]
            want_rel = float(str(r["Relative difference (%)"]).rstrip("%"))
            if round(rel, 2) != want_rel:
                bad.append(f"{row} {year}: relative difference {rel:.4f}% vs published {want_rel}%")

    t = _read(SUBCODES, encoding="utf-8-sig")                # panel (d)
    t = t[t[t.columns[0]].str.startswith("F84.2")]
    for row_name, key in (("Any position", "any"), ("Principal diagnosis", "principal")):
        r = t[t["F84 code position"] == row_name].iloc[0]
        for i, year in enumerate(YEARS):
            if _int(r[str(year)]) != f842[key][i]:
                bad.append(f"F84.2 {row_name} {year}: {f842[key][i]} vs published {r[str(year)]}")
        if not str(r["In the variant's code set"]).startswith("No"):
            bad.append("F84.2 is not marked as the excluded subcode in the published table")

    if bad:
        raise AssertionError("redraw disagrees with the published tables:\n  "
                             + "\n  ".join(bad))


# ------------------------------------------------------------------------- shared panel furniture
def _context(ax):
    """The 2020–2021 reporting-disruption band and the Law 21.545 marker, as context only."""
    shade_pandemic(ax)
    ax.axvline(LAW_X, color=LAW_COLOUR, ls=(0, (1.0, 1.9)), lw=1.2, zorder=1)


def _year_axis(ax, xlim=LINE_XLIM, label="Year"):
    year_ticks(ax, YEARS)
    ax.set_xlim(*xlim)
    ax.set_xlabel(label)


def _variant_lines(ax, d, panel, activity, position, markers=("o", "s"), dashed=False,
                   labels=None, band="both"):
    """One pair of variant series with their exact-Poisson bands: with Rett, then without.

    `band` follows the stored plate: "both" shades each variant's own limits (a and b), "with"
    shades only the with-Rett band (c, where the two lie within a pixel of each other), and "none"
    shades nothing (f, where the log axis makes the band thinner than the line).
    """
    for (variant, colour, tail), marker in zip(VARIANTS, markers):
        s = _ys(d, variant, panel, activity, position)
        if band == "both" or (band == "with" and variant == WITH):
            ax.fill_between(s.year, s.rate_lo, s.rate_hi, color=colour, alpha=CI_ALPHA, lw=0,
                            zorder=2)
        # the stored plate draws the without-Rett series dashed and open on top of the with-Rett
        # one, so both stay legible where the two variants lie on each other
        open_marker = dashed and variant == WITHOUT
        style_kw = dict(dashes=(3.7, 2.8), mfc="white", mew=1.6) if open_marker \
            else dict(mfc=colour, mew=0.9)
        ax.plot(s.year, s.rate_per_100k_episodes, marker=marker, color=colour, lw=LINE_W, ms=MS,
                label=(labels or {}).get(variant, tail), zorder=3, **style_kw)
    return ax


# ------------------------------------------------------------------------------------------ panels
def _panel_a(ax, d):
    """(a) Episodes with F84 in any position per 100,000 GRD episodes, both variants."""
    _context(ax)
    _variant_lines(ax, d, "observed", "all", "any",
                   labels={WITH: "Full F84 (with Rett)", WITHOUT: "F84 without Rett"})
    # the headroom factors of (a), (b), (c), (d) and (e) are read off the stored plate's gridlines
    hi = max(_ys(d, v, "observed", "all", "any").rate_hi.max() for v, _c, _t in VARIANTS)
    ax.set_ylim(0, hi * 1.033)
    ax.yaxis.set_major_locator(MultipleLocator(100))
    _year_axis(ax)
    ax.set_ylabel(RATE_LABEL)
    # both notes sit where the stored plate puts them, in axes fractions of the y axis
    ax.text(2020.5, 0.625, "Reporting\ndisruption\n2020–21", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=7, color=GREY, linespacing=1.15)
    ax.text(LAW_X + 0.07, 0.303, "Law 21.545\n(March 2023,\ncontext)",
            transform=ax.get_xaxis_transform(), ha="left", va="top", fontsize=7,
            color=LAW_COLOUR, linespacing=1.2)
    ax.legend(loc="lower right", borderaxespad=0.6, handletextpad=0.6, labelspacing=0.15,
              borderpad=0.3, frameon=True, facecolor="white", edgecolor="0.8", framealpha=0.9)
    clean(ax, "both")


def _panel_b(ax, d):
    """(b) The same rate restricted to F84 as the principal diagnosis."""
    _context(ax)
    _variant_lines(ax, d, "observed", "all", "principal",
                   labels={WITH: "Full F84 (with Rett)", WITHOUT: "F84 without Rett"})
    hi = max(_ys(d, v, "observed", "all", "principal").rate_hi.max() for v, _c, _t in VARIANTS)
    ax.set_ylim(0, hi * 1.031)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    _year_axis(ax)
    ax.set_ylabel(RATE_LABEL)
    ax.legend(loc="lower right", borderaxespad=0.6, handletextpad=0.6, labelspacing=0.15,
              borderpad=0.3, frameon=True, facecolor="white", edgecolor="0.8", framealpha=0.9)
    clean(ax, "both")


def _panel_c(ax, d):
    """(c) The same any-position rate inside strict hospitalisation and inside CMA."""
    _context(ax)
    hi = 0
    for activity, marker, name in (("hospitalisation", "s", "Strict hospitalisation"),
                                   ("cma", "^", "Major ambulatory surgery (CMA)")):
        _variant_lines(ax, d, "observed", activity, "any", markers=(marker, marker), dashed=True,
                       band="with",
                       labels={v: f"{name} · {tail}" for v, _c, tail in VARIANTS})
        hi = max(hi, max(_ys(d, v, "observed", activity, "any").rate_hi.max()
                         for v, _c, _t in VARIANTS))
    ax.set_ylim(0, hi * 1.041)
    ax.yaxis.set_major_locator(MultipleLocator(200))
    _year_axis(ax)
    ax.set_ylabel(RATE_LABEL)
    # hospitalisation with/without then CMA with/without, the order the series were drawn in
    ax.legend(loc="upper left", borderaxespad=0.5, handletextpad=0.6, labelspacing=0.15,
              borderpad=0.3, frameon=True, facecolor="white", edgecolor="0.8", framealpha=0.9)
    clean(ax, "both")


def _panel_d(ax, d, f842):
    """(d) The F84.2 episodes themselves, with their share of the whole F84 family."""
    _context(ax)
    family = _ys(d, WITH, "observed", "all", "any").n_episodes_f84.to_numpy(float)
    x = np.array(YEARS, dtype=float)
    ax.bar(x - 0.2, f842["any"], 0.35, color=GOLD, label="F84.2 in any position", zorder=3)
    ax.bar(x + 0.2, f842["principal"], 0.35, color=ORANGE, label="F84.2 principal", zorder=3)
    ax.set_ylim(0, f842["any"].max() * 1.345)
    ax.yaxis.set_major_locator(MultipleLocator(20))
    for xi, n, total in zip(x, f842["any"], family):
        # the label sits on a white patch: over the shaded years the stored plate clears the band
        ax.text(xi - 0.2, n + 2.2, f"{100 * n / total:.1f}%", ha="center", va="bottom",
                fontsize=8, zorder=4,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    _year_axis(ax, BAR_XLIM)
    ax.set_ylabel("Episodes")
    ax.legend(title="% of the F84 family ↑", loc="upper right", borderaxespad=0.5,
              handletextpad=0.6, labelspacing=0.15, borderpad=0.3, frameon=True, facecolor="white",
              edgecolor="0.8", framealpha=0.9)
    clean(ax, "both")


def _panel_e(ax, d):
    """(e) How much each series moves when F84.2 is put back into the case definition."""
    _context(ax)
    series = _rel_difference(d)
    for label, colour, marker, values in series:
        ax.plot(YEARS, values, marker=marker, color=colour, lw=2.4, ms=7.0, label=label, zorder=3)
    top = max(v.max() for _l, _c, _m, v in series)
    ax.set_ylim(0, top * 1.045)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, "en", 1)))
    _year_axis(ax)
    ax.set_ylabel("(with − without) / without, %")
    ax.legend(loc="upper right", borderaxespad=0.5, handletextpad=0.6, labelspacing=0.15,
              borderpad=0.3, frameon=True, facecolor="white", edgecolor="0.8", framealpha=0.9)
    clean(ax, "both")


def _panel_f(ax, d):
    """(f) The fixed panel of 65 hospitals on a log axis, with persons within year as bars.

    The bars are the persons of the OBSERVED panel — the original reads
    `_ys(D, 'con_rett', 'observed', 'all', 'any').persons_within_year` — while the lines are the
    rates of the fixed panel of 65 hospitals, so the two axes answer different questions.
    """
    bars = ax.twinx()                       # persons, linear, behind the rates
    _context(bars)
    x = np.array(YEARS, dtype=float)
    for (variant, colour, tail), offset in zip(VARIANTS, (-0.2, 0.2)):
        persons = _ys(d, variant, "observed", "all", "any").persons_within_year.to_numpy(float)
        bars.bar(x + offset, persons, 0.35, color=colour, alpha=BAR_ALPHA, lw=0,
                 label=f"Persons · {tail}", zorder=3)
    tallest = _ys(d, WITH, "observed", "all", "any").persons_within_year.max()
    bars.set_ylim(0, tallest * 3.985)       # the stored plate keeps the bars in the lower quarter
    bars.yaxis.set_major_locator(MultipleLocator(5000))
    bars.yaxis.set_major_formatter(thousands("en"))
    # labelpad 1.5 keeps the right-hand label inside the canvas, where the stored plate has it
    bars.set_ylabel("Unique persons within year", labelpad=1.5)
    bars.grid(False)
    for spine in ("top", "right"):
        bars.spines[spine].set_visible(False)

    for position, marker, name in (("any", "o", "Any position, fixed panel"),
                                   ("principal", "s", "Principal, fixed panel")):
        _variant_lines(ax, d, "fixed65", "all", position, markers=(marker, marker), dashed=True,
                       band="none", labels={v: f"{name} · {tail}" for v, _c, tail in VARIANTS})
    ax.set_yscale("log")
    ax.set_ylim(8, 20000)
    ax.yaxis.set_major_locator(FixedLocator([10, 20, 50, 100, 200, 500, 1000, 2000, 5000,
                                             10000, 20000]))
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.yaxis.set_minor_locator(NullLocator())
    _year_axis(ax, BAR_XLIM)
    ax.set_ylabel(f"{RATE_LABEL} (log)")
    clean(ax, "both")
    ax.set_zorder(bars.get_zorder() + 1)    # rates over the bars, as in the stored plate
    ax.patch.set_visible(False)

    handles, labels = ax.get_legend_handles_labels()
    order = [0, 2, 1, 3]                    # with Rett first, then without, as the plate lists them
    h2, l2 = bars.get_legend_handles_labels()
    # (f) is the one legend of the plate the stored figure draws without a frame line
    ax.legend([handles[i] for i in order] + h2, [labels[i] for i in order] + l2, loc="upper left",
              borderaxespad=0.4, handletextpad=0.6, labelspacing=0.15, borderpad=0.3, frameon=True,
              facecolor="white", edgecolor="none", framealpha=1.0)


# --------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of figS1 and hand back the figure."""
    d = _summary()
    f842 = _subcodes()
    _check_published(d, f842)

    style()
    # text sizes read off the stored plate: axis labels 9 pt, legends 7 pt, panel titles 10 pt,
    # in-panel notes 7 pt, and no tick marks at all — only their labels
    plt.rcParams.update({"axes.labelsize": 9, "legend.fontsize": 7, "legend.title_fontsize": 7,
                         "xtick.major.size": 0, "ytick.major.size": 0})
    fig = plt.figure(figsize=(8.0, 10.888))        # the stored plate's proportions, 1000 x 1361 px
    ax = {k: fig.add_axes(box) for k, box in BOXES.items()}
    _panel_a(ax["a"], d)
    _panel_b(ax["b"], d)
    _panel_c(ax["c"], d)
    _panel_d(ax["d"], d, f842)
    _panel_e(ax["e"], d)
    _panel_f(ax["f"], d)
    for _key, x, y, title in TITLES:
        fig.text(x, y, title, fontweight="bold", fontsize=10, ha="left", va="bottom",
                 linespacing=1.3)
    return fig


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE/f"{PLATE}_redraw.png"
    draw().savefig(out, dpi=125, facecolor="white")     # 1000 x 1361 px, the stored plate's size
    print("wrote", out)
