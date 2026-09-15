"""Plate S2 — F84 subcode composition and code position in GRD episodes, 2019–2024.

Redraw of the stored plate `docs/study/corpus/figures/figS2_grd_subcodes.jpg`. The original was
drawn by `study/pipeline/08a_figures_grd.py` (`figS2`) from two microdata-derived frames that this
repository does not carry: `grd_subcode_year` (one row per subcode × code position × year) and
`grd_year_summary`. The second of those two *is* tracked, in `docs/study/data/`, and the first
survives in full in the published supplementary table ST10, which prints every one of the eight F84
subcodes in each of the three positions the plate uses (any, principal, secondary) for all six
years. All six panels are therefore redrawn here from tracked tables alone.

Case definition, unchanged from the original: the variant is `sin_rett` — the F84 family excluding
Rett syndrome, i.e. the seven subcodes F84.0, F84.1, F84.3, F84.4, F84.5, F84.8 and F84.9 that ST10
marks `Yes` in its column "In the variant's code set". F84.2 is *not* part of the variant and
appears in panel (f) only, as the excluded series the plate shows for reference. Panel (e)'s second
line is the separate `strict_autism_f840` variant (F84.0 alone), which is identical in both Rett
variants.

Estimator, unchanged from the original:

* Panels (a), (b), (c) and (f) count **mentions**, not episodes. An episode may carry more than one
  F84 subcode in its 35 diagnostic fields, so the seven subcode counts of a year add to more than
  the year's episode count — 2,372 mentions against 2,334 episodes in 2019. The plate says so in
  panel (b) and ST10 is a mention count; building these panels from episode counts would be a
  different quantity. The dashed "F84 family (variant)" line of panel (c) is likewise a mention
  ratio, the year's principal mentions over the year's any-position mentions across the seven
  subcodes (228/2,372 = 9.6 % in 2019), which is what `figS2` computes as
  `100 * prin.sum(axis=1) / anyp.sum(axis=1)`.
* Panels (d) and (e) count **episodes**, from `grd_year_summary` on the observed hospital panel and
  all activity types, and (e) carries the exact Poisson 95 % interval that table publishes.
* Everything is an unweighted count; no standardisation anywhere on this plate.

Panel (d) reproduces one quirk of the original worth naming, because it is a drawing decision and
not a data decision: the plate stacks `principal`, `principal_and_secondary` and `secondary_only`
while labelling the first segment "Principal only". `principal` in `grd_year_summary` already
includes the handful of episodes that carry F84 in both positions (6 of 2,334 in 2019), so the stack
exceeds the `any` total by that handful. This module stacks the same three series as the stored
plate does rather than netting the overlap out, so the redrawn bars match the ones in the JPG; the
difference is 3–15 episodes a year and is invisible at this scale either way.

`case_definition_subcodes.csv` and `case_definition_variant_rates.csv` are read as cross-checks and
are asserted against the two drawing sources before anything is plotted: the first must reproduce
panel (a)'s composition (its `Other` column is F84.3 + F84.4 pooled), the second panel (e)'s two
rate series to the two decimals it publishes.
"""
import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from figstyle import *

PLATE = "figS2_grd_subcodes"
SOURCES = [
    "docs/study/corpus/tables/ST10_grd_f84_subcodes.csv",
    "docs/study/data/grd_year_summary.csv",
    "docs/study/data/case_definition_subcodes.csv",
    "docs/study/data/case_definition_variant_rates.csv",
]
NOTE = ("Redraws all six panels of plate S2 — F84 subcode composition and code position in GRD "
        "episodes, 2019–2024, for the F84-without-Rett variant — from supplementary table ST10 "
        "(mentions of each subcode in any, principal and secondary position, panels a, b, c and f) "
        "and the tracked grd_year_summary (episodes by code position and the exact-Poisson rates of "
        "panels d and e), cross-checked against case_definition_subcodes and "
        "case_definition_variant_rates.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repo root
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]    # GRD years of the stored plate
PLATE_W_MM, PLATE_H_MM = 180.0, 245.0           # the pipeline's plate canvas, drawn 1:1
FIG_W_IN, FIG_H_IN = PLATE_W_MM / 25.4, PLATE_H_MM / 25.4
# March 2023 on an axis whose ticks are year centres: the pipeline draws the law at YEAR - 0.30.
LAW_X = 2023 - 0.30
VARIANT = "sin_rett"                            # F84 family excluding Rett — the plate's variant
RETT = "F84.2"                                  # excluded from the variant; panel (f) only
STRICT = "strict_autism_f840"                   # F84.0 alone — the second line of panel (e)

FS_BASE, FS_TITLE, FS_TICK, FS_LEG, FS_MIN = 8.0, 9.0, 7.0, 7.0, 6.0
# Useful width of a panel title: half the plate less a 4 mm margin, in points.
TITLE_W_PT = (PLATE_W_MM / 25.4 * 72.0) / 2 - (4.0 / 25.4 * 72.0)
NOTE_W_PT = 150.0                               # useful width of a note drawn inside a cell
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)
CELL_MARGIN = 2.0 / PLATE_W_MM                  # 2 mm: where a panel title starts in its own cell

TITLES = {
    "a": "Subcode composition (mentions, any position)",
    "b": "Mentions by subcode",
    "c": "% of mentions in principal position",
    "d": "Code position within the episode",
    "e": "F84.0 only versus F84 family per 100,000 episodes",
    "f": "F84.2 (Rett syndrome) by position",
}
FAMILY = "F84 family (variant)"
VARIANT_LABEL = "F84 without Rett"
STRICT_LABEL = "F84.0 only (identical in both variants)"
POS_LABEL = {"principal": "Principal only", "principal_and_secondary": "Principal and secondary",
             "secondary_only": "Secondary only", "secondary": "Secondary only"}
PCT_SEC = "% secondary only"
MENTIONS_NOTE = "An episode may carry more than one F84 subcode: mentions ≠ episodes"
RETT_NOTE = "Excluded from this variant (shown for reference)"
LAW_NOTE = "Law 21.545\n(March 2023,\ncontext)"
PANDEMIC_NOTE = "Reporting\ndisruption\n2020–21"
MIN_MENTIONS = 20       # panel (c) keeps the subcodes with at least this many mentions every year


# --------------------------------------------------------------------------- reading the tables
def _int(cell):
    """A presentation count -> int: '1,400', and the thin and non-breaking spaces a grouped
    number can carry instead of the comma."""
    return int(str(cell).replace(",", "").replace(" ", "").replace(" ", "").strip())


def subcode_mentions():
    """ST10 as a long frame: subcode x position x year, with the variant flag it publishes.

    ST10 prints three positions per subcode — "Any position", "Principal diagnosis" and "Secondary
    position (2–35)" — which are the three the plate uses; they are keyed here on the first word so
    the en dash of the third label cannot break the match.
    """
    t = pd.read_csv(ROOT / SOURCES[0], encoding="utf-8-sig", dtype=str)
    long = pd.DataFrame({
        "subcode": t[t.columns[0]].str.slice(0, 5),                 # 'F84.0 Childhood autism' -> 'F84.0'
        "position": t["F84 code position"].str.split().str[0].str.lower(),
        "in_variant": t["In the variant's code set"].str.startswith("Yes"),
    })
    for y in YEARS:
        long[y] = t[str(y)].map(_int)
    wide = {p: g.set_index("subcode")[YEARS].T for p, g in long.groupby("position")}
    # Every subcode's mentions must split exactly into principal and secondary in every year.
    assert (wide["any"] == wide["principal"] + wide["secondary"]).all().all(), \
        "ST10: principal + secondary does not equal any position"
    subs = sorted(long.subcode[long.in_variant].unique())
    assert RETT not in subs and len(subs) == 7, f"unexpected variant code set: {subs}"
    return wide, subs


def year_summary():
    """Episodes with F84 by code position and year, on the panel the plate draws.

    `observed` is every hospital reporting in the year and `all` every activity type: the stored
    plate's panels (d) and (e) are both drawn on that cell of `grd_year_summary`.
    """
    d = pd.read_csv(ROOT / SOURCES[1])
    return d[(d.panel == "observed") & (d.activity == "all")]


def check_composition(wide, subs):
    """Panel (a) against `case_definition_subcodes.csv`, which publishes the same composition."""
    c = pd.read_csv(ROOT / SOURCES[2]).set_index("year").reindex(YEARS)
    anyp = wide["any"][subs]
    named = {"F840": "F84.0", "F841": "F84.1", "F845": "F84.5", "F848": "F84.8", "F849": "F84.9"}
    for col, code in named.items():
        assert (c[col].values == anyp[code].values).all(), f"{code} mentions differ from {SOURCES[2]}"
    pooled = [s for s in subs if s not in named.values()]            # F84.3 and F84.4
    assert (c["Other"].values == anyp[pooled].sum(axis=1).values).all(), "pooled 'Other' differs"
    share = 100 * anyp.div(anyp.sum(axis=1), axis=0)
    for col, code in named.items():
        assert np.allclose(c["pct_" + col].values, share[code].round(2).values), \
            f"{code} share differs from {SOURCES[2]}: the denominator is not the mention total"
    return share


def check_rates(ys):
    """Panel (e) against `case_definition_variant_rates.csv`, published to two decimals."""
    r = pd.read_csv(ROOT / SOURCES[3]).set_index("year").reindex(YEARS)
    for variant, col in ((VARIANT, "sin_rett"), (STRICT, "strict_autism_f840")):
        drawn = rate_series(ys, variant).rate_per_100k_episodes.round(2).values
        assert np.allclose(r[col].values, drawn), f"{variant} rates differ from {SOURCES[3]}"


def rate_series(ys, variant):
    """The any-position rate per 100,000 GRD episodes of one variant, with its exact Poisson band."""
    d = ys[(ys.variant == variant) & (ys.position == "any")]
    return d.set_index("year").reindex(YEARS)


# --------------------------------------------------------------------------- panel furniture
# One off-screen canvas, reused: wrapping measures every word of every title. It is built outside
# pyplot so that it never joins the figure registry the caller manages.
_MEASURE = FigureCanvasAgg(Figure(figsize=(1, 1)))


def _width_pt(s, fontsize, weight):
    """Typographic width of a string in points, measured with the font it will be drawn in."""
    w, _h, _d = _MEASURE.get_renderer().get_text_width_height_descent(
        str(s), FontProperties(size=fontsize, weight=weight), False)
    return w * 72.0 / _MEASURE.figure.dpi


def wrap(s, max_pt, fontsize, weight="bold"):
    """Line wrap by MEASURED width, as the pipeline wraps its panel titles and notes.

    Counting characters puts a long title one word over the edge of its cell and leaves a short one
    needlessly folded; the register's own words are long enough for that to matter here.
    """
    lines, cur = [], ""
    for word in str(s).split():
        trial = f"{cur} {word}".strip()
        if cur and _width_pt(trial, fontsize, weight) > max_pt:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def panel_head(ax, key):
    """The plate's panel header: '(a) Title', bold, left of its own cell, wrapped to the cell."""
    return ax.set_title(wrap(f"({key}) {TITLES[key]}", TITLE_W_PT, FS_TITLE),
                        loc="left", fontsize=FS_TITLE, fontweight="bold", pad=3.0, linespacing=1.15)


def panel_legend(ax, *args, loc="upper left", ncol=1, **kw):
    """Legend of a narrow cell: 6.2 pt on a solid white box, so the series stays readable under it."""
    lg = ax.legend(*args, loc=loc, ncol=ncol, fontsize=FS_MIN + 0.2, frameon=True, framealpha=1.0,
                   edgecolor="#cccccc", facecolor="white", borderpad=0.25, **kw)
    lg.set_zorder(6)
    lg.set_in_layout(False)         # a wide in-panel legend would otherwise collapse its own axes
    return lg


def below_legend(ax, ncol=4):
    """The seven-subcode legend of panels (a) and (b): under the axes, four columns, unframed."""
    lg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=ncol, fontsize=FS_MIN + 0.3,
                   frameon=False, columnspacing=0.8, handlelength=1.1)
    return lg


def context(ax, pandemic_label=False, law_label=False, y=0.97):
    """Common context of every panel: the 2020–21 shading and the Law 21.545 line.

    Both are labelled once per plate, not once per panel: repeated in six 90 mm cells the two notes
    are unreadable, and the caption says they mean the same thing everywhere.
    """
    shade_pandemic(ax)                                      # 2019.5–2021.5, the two pandemic years
    if pandemic_label:
        ax.text(2020.5, y, PANDEMIC_NOTE, transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=FS_MIN + 0.3, color="#555555", linespacing=1.15, zorder=6)
    ax.axvline(LAW_X, color="#444444", ls=":", lw=1.0, zorder=1)
    if law_label:
        ax.text(LAW_X + 0.06, y, LAW_NOTE, transform=ax.get_xaxis_transform(), ha="left", va="top",
                fontsize=FS_MIN + 0.3, color="#444444", linespacing=1.15, zorder=6)


def rate_line(ax, d, color, label, mk="o"):
    """One rate series of panel (e): the point estimate over its exact Poisson 95 % band."""
    ax.plot(d.index, d.rate_per_100k_episodes, "-", marker=mk, color=color, lw=2.2, markersize=5.5,
            label=label)
    ax.fill_between(d.index, d.rate_lo, d.rate_hi, color=color, alpha=0.13, lw=0)


def pct(x, dec=0):
    """A percentage as the English plates write it: no space before the sign."""
    return num(x, "en", dec) + "%"


# --------------------------------------------------------------------------- the plate
def draw():
    style()
    plt.rcParams.update({
        "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold",
        "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
        "legend.fontsize": FS_LEG, "legend.title_fontsize": FS_LEG, "grid.linewidth": 0.45,
        "lines.linewidth": 1.3, "lines.markersize": 3.4, "patch.linewidth": 0.6,
        "xtick.major.size": 2.2, "ytick.major.size": 2.2, "xtick.major.pad": 1.5,
        "ytick.major.pad": 1.5, "axes.labelpad": 2.0, "axes.titlepad": 3.0,
        "legend.handlelength": 1.5, "legend.handletextpad": 0.5, "legend.labelspacing": 0.30,
        "legend.columnspacing": 0.9, "legend.borderpad": 0.3,
    })
    wide, subs = subcode_mentions()
    ys = year_summary()
    share = check_composition(wide, subs)
    check_rates(ys)
    anyp, prin = wide["any"][subs], wide["principal"][subs]
    x = np.array(YEARS, dtype=float)
    palette = dict(zip(subs, OKABE[:len(subs)]))

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    ax = axes.ravel()

    # (a) composition of the year's mentions, one stacked bar per year -----------------------------
    a = ax[0]
    bottom = np.zeros(len(x))
    for s in subs:
        a.bar(x, share[s], bottom=bottom, color=palette[s], width=0.7, label=s)
        bottom += share[s].values
    for xi, v in zip(x, share["F84.0"]):
        a.text(xi, v / 2, pct(v), ha="center", va="center", fontsize=8, color="white",
               fontweight="bold")
    a.set_ylim(0, 100)
    year_ticks(a, YEARS)
    a.set_xlabel("Year")
    a.set_ylabel("% of F84 mentions")
    clean(a, "y")
    below_legend(a)

    # (b) the same mentions as counts, on a log scale ----------------------------------------------
    b = ax[1]
    for s in subs:
        b.plot(x, anyp[s].replace(0, np.nan), "o-", color=palette[s], lw=1.8, markersize=4.5, label=s)
    log_axis(b, "y", "en")
    b.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0), numticks=12))
    b.set_ylim(0.5, 50000)
    year_ticks(b, YEARS)
    b.set_xlabel("Year")
    b.set_ylabel("Mentions (log scale)")
    context(b, pandemic_label=True, law_label=True, y=0.99)
    # The pipeline asks for this note at x = 0.02 and its label-decongestion pass, which cannot run
    # here, slid it clear of the F84.3 series; it is placed where the stored plate carries it.
    b.text(0.24, 0.05, wrap(MENTIONS_NOTE, NOTE_W_PT, FS_MIN + 0.3, "normal"), transform=b.transAxes,
           fontsize=FS_MIN + 0.3, ha="left", va="bottom", color="#555555", bbox=NOTE_BBOX,
           linespacing=1.25, zorder=6)
    clean(b, "y")
    below_legend(b)

    # (c) how often each subcode is the principal diagnosis ----------------------------------------
    c = ax[2]
    big = [s for s in subs if (anyp[s] >= MIN_MENTIONS).all()]
    for s in big:
        c.plot(x, 100 * prin[s] / anyp[s], "o-", color=palette[s], lw=1.8, markersize=4.5, label=s)
    # The family line is the ratio of the two mention totals, not the mean of the five ratios above.
    c.plot(x, 100 * prin.sum(axis=1) / anyp.sum(axis=1), "k--", lw=2, label=FAMILY)
    # The headroom above 40 % is the legend's: with the axis closed at 42 it sat on the F84.1 series.
    c.set_ylim(0, 62)
    c.set_yticks([0, 10, 20, 30, 40])
    c.yaxis.set_major_formatter(thousands("en"))
    year_ticks(c, YEARS)
    c.set_xlabel("Year")
    c.set_ylabel("% principal within subcode")
    context(c)
    clean(c, "y")
    panel_legend(c, loc="upper right")

    # (d) episodes by code position, with the secondary-only share on its own axis -----------------
    d = ax[3]
    pos = ys[ys.variant == VARIANT].pivot_table(index="year", columns="position",
                                                values="n_episodes_f84").reindex(YEARS)
    bottom = np.zeros(len(x))
    for key, colour in (("principal", ORANGE), ("principal_and_secondary", GOLD),
                        ("secondary_only", BLUE)):
        d.bar(x, pos[key], bottom=bottom, color=colour, width=0.7, label=POS_LABEL[key])
        bottom += pos[key].values
    year_ticks(d, YEARS)
    d.set_xlabel("Year")
    d.set_ylabel("Episodes")
    d.set_ylim(0, pos["any"].max() * 1.3)
    d.yaxis.set_major_formatter(thousands("en"))
    clean(d, "y")
    d2 = d.twinx()
    d2.spines["right"].set_visible(True)
    d2.grid(False)
    secondary = 100 * pos["secondary_only"] / pos["any"]
    d2.plot(x, secondary, "o-", color="#333333", lw=1.8, markersize=5, label=PCT_SEC)
    # Each share is written above its marker, except the last: the legend holds the top-right corner,
    # so the stored plate carries 2024's label under its marker, against the top of the bar.
    for i, (xi, v) in enumerate(zip(x, secondary)):
        under = i == len(x) - 1
        d2.text(xi, v - 0.5 if under else v + 0.6, pct(v, 1), ha="center",
                va="top" if under else "baseline", fontsize=7.5, zorder=6)
    d2.set_ylim(80, 100)
    d2.set_ylabel(PCT_SEC)
    d2.yaxis.set_major_formatter(thousands("en"))
    context(d)
    h1, l1 = d.get_legend_handles_labels()
    h2, l2 = d2.get_legend_handles_labels()
    panel_legend(d, h1 + h2, l1 + l2, loc="upper right")

    # (e) the narrow and the wide case definition, per 100,000 GRD episodes -------------------------
    e = ax[4]
    rate_line(e, rate_series(ys, VARIANT), BLUE, f"{FAMILY}: {VARIANT_LABEL}")
    rate_line(e, rate_series(ys, STRICT), GREEN, STRICT_LABEL, mk="s")
    year_ticks(e, YEARS)
    e.set_xlabel("Year")
    e.set_ylabel("Episodes with F84 per 100,000 GRD episodes")
    e.set_ylim(0, None)
    e.yaxis.set_major_formatter(thousands("en"))
    context(e)
    clean(e, "y")
    panel_legend(e, loc="lower right")

    # (f) the subcode this variant excludes, kept in view --------------------------------------------
    f = ax[5]
    rett = {p: wide[p][RETT] for p in ("secondary", "principal")}
    f.bar(x - 0.2, rett["secondary"], width=0.38, color=BLUE, label=POS_LABEL["secondary"])
    f.bar(x + 0.2, rett["principal"], width=0.38, color=ORANGE, label=POS_LABEL["principal"])
    year_ticks(f, YEARS)
    f.set_xlabel("Year")
    f.set_ylabel("Episodes")
    f.set_ylim(0, rett["secondary"].max() * 1.4)
    f.yaxis.set_major_formatter(thousands("en"))
    context(f)
    clean(f, "y")
    panel_legend(f, loc="upper left", title=RETT_NOTE)

    # Titles last: the layout is resolved with them where matplotlib puts a left title — at the left
    # edge of the AXES — so their height is reserved, then frozen, and only then is each title slid
    # out to the left edge of its own CELL, where the stored plate carries it.
    heads = {key: panel_head(cell, key) for cell, key in zip(ax, "abcdef")}
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    for i, key in enumerate("abcdef"):
        p = ax[i].get_position()
        heads[key].set_x((CELL_MARGIN + 0.5 * (i % 2) - p.x0) / p.width)
    return fig
