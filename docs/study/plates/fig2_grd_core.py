"""Figure 3 (`fig2_grd_core`) — the GRD hospital core, redrawn from the published aggregates.

The stored plate `docs/study/corpus/figures/fig2_grd_core.jpg` was drawn by
`study/pipeline/08a_figures_grd.py` from the GRD microdata, which this repository does not carry.
Every series of its six panels, however, survives in tables that are tracked here, so the six panels
are rebuilt from those tables rather than from the register:

  (a) F84 per 100,000 GRD episodes — `grd_year_summary.csv`, the four rows `any`/`principal` ×
      `observed`/`fixed65` of activity `all`, with the exact Poisson limits the table already stores
      and the `hospitals_n` foot row (65 65 65 65 68 72).
  (b) the same rate by activity — the `all`, `hospitalisation` and `cma` rows of the observed panel.
  (c) the rate inside each coding-depth stratum in 2019 and 2024 — `grd_coding_depth_year.csv` — with
      the mean-depth inset taken from `coding_depth_mean_all` / `coding_depth_mean_f84`.
  (d) episodes per 100,000 INE population by age and sex — the four `grd_age_<sex>_<year>.csv` files,
      which already publish the rate and its exact limits with 45+ pooled.
  (e) the 2024 rate of each of the 72 hospitals — `S_hospital_rates_2024.csv`, whose rate cell is the
      formatted string `"5,210.7 (4,771.6 to 5,679.4)"` and is parsed here.
  (f) episodes and unique persons within each year — `grd_year_summary.csv` again — with the male:
      female ratio of episodes from `grd_age_sex_year.csv`.

THE ESTIMATOR, UNCHANGED. Every GRD table is filtered to `variant == "sin_rett"` (F84 without Rett),
which is the definition the plate's title names and which differs from `con_rett`: 2,334 against 2,385
episodes in 2019, 202.7 against 207.1 per 100,000. Panels (a), (b), (c) and (e) are rates per 100,000
GRD EPISODES of the same panel, activity and year, with exact Poisson limits; only panel (d) is per
100,000 INE population, it is crude age-specific (not standardised), and it keeps the plate's own
warning that the numerator is located by place of care and the denominator by residence. The 'other'
activity is not drawn in (b): its denominator is 0 from 2020 on, which is an absent category and not a
zero, and the published plate leaves it out and says so in the caption. Persons in (f) are unique
WITHIN a year only — the identifier changes format between 2020 and 2021 — so nothing is joined
across years and the printed figure is episodes per person within the year.

THE ONE NUMBER THIS MODULE RECOMPUTES is the male:female ratio of panel (f) and its 95% interval:
the counts are read from `grd_age_sex_year.csv` (the plate's own age-sex table, `sin_rett`, observed
panel, any position, all activity) and the interval is the pipeline's `ratio_ci` — Wilson on
p = males / (males + females), mapped back to the ratio. `_check()` measures the result against the
stored plate: the 2019 ratio comes out at 3.265 (2.967–3.593) against 3.261 (2.955–3.604) read off
the image, and the 2021 ratio at 3.2250 against 3.2252 read off the image.

  A NOTE ON THE ASSESSMENT. `docs/study/plate_assessment.json` directs this panel to
  `output_files/consolidacion/grd_sex_ratio.csv` (definition `TEA_operacional`, unit `records`, role
  `cualquiera`), which gives 3.270 (2.969–3.606) for 2019 and 3.241 (2.946–3.572) for 2021. Those are
  NOT the plotted values: the plate's 2019 upper cap falls at 3.604 and its 2021 upper cap at 3.550,
  i.e. BELOW 3.606 and 3.572, which an outer-edge reading of a drawn cap cannot be. The age-sex
  counts reproduce both caps to within the width of the cap itself, and they are also the counts
  panel (d) is drawn from, so the two panels stay consistent. The plate is drawn from the age-sex
  counts; `_check()` prints the comparison.

WHERE THE LEGENDS SIT. The stored plate was finished by a de-congestion pass that measures the drawn
composition and moves a legend or a value label out of whatever it covers. That pass is not rebuilt
here; instead each legend is placed where the stored plate actually prints it — upper right in (a),
(b), (d) and (f), upper left in (c), lower right in (e) — and the two small collisions the pass had
to resolve (a rotated axis label reaching into its own panel head, and the '872' end label of (b)
reaching into the legend card) are resolved by the two measured helpers below.

The corpus is English only and so is this module: it takes no language argument.
"""
import re
import sys
from pathlib import Path

_STUDY = Path(__file__).resolve().parents[1]          # docs/study, where figstyle lives
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
from scipy import stats

from figstyle import *   # noqa: F401,F403  — style, clean, num, BLUE, ORANGE, GREEN, PINK, BLACK, …

PLATE = "fig2_grd_core"
SOURCES = [
    "docs/study/data/grd_year_summary.csv",
    "docs/study/data/grd_selected_definition.csv",
    "docs/study/data/grd_coding_depth_year.csv",
    "docs/study/data/grd_age_hombre_2019.csv",
    "docs/study/data/grd_age_hombre_2024.csv",
    "docs/study/data/grd_age_mujer_2019.csv",
    "docs/study/data/grd_age_mujer_2024.csv",
    "docs/study/data/grd_age_sex_year.csv",
    "docs/study/corpus/tables/S_hospital_rates_2024.csv",
    "docs/study/corpus/tables/T2_grd_core.csv",
]
NOTE = ("Redraws the six panels of the GRD core plate — the F84 rate per 100,000 GRD episodes by "
        "position and panel, by activity, by coding-depth stratum, the population rate by age and "
        "sex, the 2024 rate of each of the 72 hospitals and the episodes/persons pair with the male:"
        "female ratio — from the published GRD aggregates in docs/study/data/ and the hospital and "
        "core tables in docs/study/corpus/tables/, all filtered to the sin_rett definition.")

ROOT = Path(__file__).resolve().parents[3]            # repository root
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
FIRST, LAST = YEARS[0], YEARS[-1]
VARIANT = "sin_rett"                                  # F84 without Rett: the plate's own definition
PER = 100_000.0

# --------------------------------------------------------------------------------------------------
# The plate's geometry and typography (study/pipeline/08a_figures_grd.py): 180 × 245 mm drawn 1:1,
# three rows by two columns, 9 pt bold panel heads down to a 6 pt floor, ticks drawn without marks.
# --------------------------------------------------------------------------------------------------
PLATE_W_IN, PLATE_H_IN = 180.0 / 25.4, 245.0 / 25.4
CELL_MARGIN = 2.0 / 180.0                             # left margin of a grid cell, figure fraction
FS_BASE, FS_TITLE, FS_TICK, FS_MIN = 8.0, 9.0, 7.0, 6.0
DARK, GREY_TEXT, LEADER = "#333333", "#555555", "#999999"
LIGHT_BLUE, LIGHT_ORANGE = "#9ecae1", "#f4b183"       # the plate's two 2019 tints
LAW_X = 2023 - 0.30                                   # `CFG.LAW_YEAR - 0.30`: March 2023 on a
#                                                       year-centred axis, marked as context
PANDEMIC = [2020, 2021]
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)
PLATE_RC = {
    "font.family": "DejaVu Sans", "font.size": FS_BASE,
    "axes.titlesize": FS_TITLE, "axes.titleweight": "bold", "axes.labelsize": FS_BASE,
    "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "legend.fontsize": FS_TICK, "legend.title_fontsize": FS_TICK, "legend.frameon": False,
    "legend.handlelength": 1.5, "legend.handletextpad": 0.5, "legend.labelspacing": 0.30,
    "legend.columnspacing": 0.9, "legend.borderpad": 0.3,
    "axes.facecolor": "white", "axes.edgecolor": DARK, "axes.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True,
    "grid.color": "#cccccc", "grid.alpha": 0.35, "grid.linewidth": 0.45,
    "lines.linewidth": 1.3, "lines.markersize": 3.4, "patch.linewidth": 0.6,
    # the stored plate draws the grid but no tick marks (seaborn's `whitegrid`); the right-hand axis
    # of panel (f) is a twin and brings its own marks back.
    "xtick.bottom": False, "ytick.left": False, "ytick.right": False,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    "axes.labelpad": 2.0, "axes.titlepad": 3.0,
    "figure.facecolor": "white", "savefig.facecolor": "white",
}

# Panel heads, axis units and legend keys, in the words the stored plate prints.
T = ["F84 per 100,000 GRD episodes", "Hospitalisation and CMA", "Coding depth and rate",
     "Population: age and sex", "Rate by hospital, 2024", "Persons and episodes"]
U_RATE_LOG = "Episodes with F84 per 100,000 GRD episodes (log)"
U_RATE = "Episodes with F84 per 100,000 GRD episodes"
U_DEPTH = "F84 per 100,000 episodes in stratum"
U_DEPTH_X = "Coded diagnoses per episode (stratum)"
U_POP = "Episodes with F84 per 100,000 population (log)"
U_AGE_X = "Age group (years)"
U_RANK = "Hospitals ranked by rate (n = {})"
U_HOSP_X = "F84 per 100,000 hospital episodes (log, exact 95% CI)"
U_COUNT = "Episodes / persons (thousands)"
U_MF = "Male:female ratio"
L_ANY_OBS, L_ANY_FIX = "Any position, observed panel", "Any position, fixed panel of 65"
L_PRI_OBS, L_PRI_FIX = "Principal, observed panel", "Principal, fixed panel of 65"
L_ACT = ["All activity", "Strict hospitalisation", "Major ambulatory surgery (CMA)"]
L_DEPTH_ALL, L_DEPTH_F84, L_DEPTH_INSET = "All episodes", "Episodes with F84", "Mean depth"
L_MALES, L_FEMALES = "Males", "Females"
L_FIXED, L_NEW = "Fixed panel 2019–2024 ({})", "Added in 2023–2024 ({})"
L_EPISODES, L_PERSONS = "Episodes with F84 (any position)", "Unique persons within year"
L_MF = "M:F ratio of episodes (95% CI)"
L_HOSP_N, L_NATIONAL, L_YEAR = "Hospitals:", "National", "Year"
N_PANDEMIC = "Reporting\ndisruption\n2020–21"
N_LAW = "Law 21.545\n(March 2023,\ncontext)"
N_POP = ("Numerator: place of care (public GRD\nhospitals); denominator: residence\n"
         "(INE base 2017). Complementary reading.")

DEPTH_BINS = ["1", "2", "3", "4", "5", "6-7", "8-10", "11+"]
AGE_GROUPS = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45+"]


# --------------------------------------------------------------------------------------------------
# Reading the tracked tables
# --------------------------------------------------------------------------------------------------
def _read(name):
    return pd.read_csv(ROOT / name, encoding="utf-8-sig")


def _dash(s):
    """The study's interval rule: an interval a reader reads takes an en dash. '6-7' -> '6–7'."""
    return re.sub(r"(?<=\d)-(?=\d)", "–", str(s))


def year_summary():
    """`grd_year_summary.csv` restricted to the plate's definition, F84 without Rett."""
    t = _read(SOURCES[0])
    return t[t.variant == VARIANT]


def ys(t, panel, activity, position):
    """One annual series of the year summary, reindexed on the six GRD years."""
    d = t[(t.panel == panel) & (t.activity == activity) & (t.position == position)]
    d = d.set_index("year").reindex(YEARS)
    return d.rename(columns={"rate_per_100k_episodes": "rate", "rate_lo": "lo", "rate_hi": "hi"})


def depth_year(year):
    """The eight coding-depth strata of one year, in the plate's order (the empty `0` bin dropped)."""
    t = _read(SOURCES[2])
    d = t[(t.variant == VARIANT) & (t.panel == "observed") & (t.activity == "all") & (t.year == year)]
    return d.set_index("depth_bin").reindex(DEPTH_BINS)


def depth_ceiling():
    """The plate's own ceiling for (c): 2.35 × the highest upper limit over all years and strata."""
    t = _read(SOURCES[2])
    d = t[(t.variant == VARIANT) & (t.panel == "observed") & (t.activity == "all")
          & (t.depth_bin.isin(DEPTH_BINS))]
    return float(d.rate_hi.max()) * 2.35


def pop_rates(sex, year):
    """One age curve of panel (d): rate per 100,000 INE population with its exact limits, 45+ pooled."""
    name = {"HOMBRE": "hombre", "MUJER": "mujer"}[sex]
    t = _read(f"docs/study/data/grd_age_{name}_{year}.csv")
    return t.set_index("age_group").reindex(AGE_GROUPS).reset_index()


_RATE_CELL = re.compile(r"^\s*([\d,]+\.?\d*)\s*\(\s*([\d,]+\.?\d*)\s+to\s+([\d,]+\.?\d*)\s*\)\s*$")


def _cell(s):
    """'5,210.7 (4,771.6 to 5,679.4)' -> (5210.7, 4771.6, 5679.4)."""
    m = _RATE_CELL.match(str(s))
    if not m:
        raise ValueError(f"unparsed rate cell: {s!r}")
    return tuple(float(g.replace(",", "")) for g in m.groups())


def _count(s):
    """'9,941' -> 9941."""
    return int(str(s).replace(",", "").strip())


def hospitals():
    """The 72 hospitals of 2024, ranked from lowest to highest rate, with their exact limits."""
    t = _read(SOURCES[8])
    t.columns = [c.strip() for c in t.columns]
    rate = t["Rate per 100,000 episodes (exact 95% CI)"].map(_cell)
    h = pd.DataFrame({
        "rate": [v[0] for v in rate], "lo": [v[1] for v in rate], "hi": [v[2] for v in rate],
        "episodes": t["GRD episodes 2024"].map(_count),
        "f84": t["Episodes with F84 2024"].map(_count),
        "fixed": t["Fixed panel of 65"].str.strip().str.lower().eq("yes"),
    })
    return h.sort_values("rate").reset_index(drop=True)


def _wilson(k, n, alpha=0.05):
    """Wilson limits on a proportion (the pipeline's `common.wilson`)."""
    z = float(stats.norm.ppf(1 - alpha / 2))
    p = k / n
    den = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def mf_ratio():
    """Male:female ratio of episodes with F84, by year, with the pipeline's `ratio_ci` interval.

    The counts are the plate's own age-sex table summed over every age group (the 'unknown' age
    included, as the pipeline's `_mf_ratio` sums it); the interval is Wilson on males / (males +
    females) mapped back to the ratio.
    """
    t = _read(SOURCES[7])
    t = t[t.variant == VARIANT]
    g = t.groupby(["year", "sex"]).n_f84.sum().unstack().reindex(YEARS)
    rows = []
    for y in YEARS:
        m, w = float(g.loc[y, "HOMBRE"]), float(g.loc[y, "MUJER"])
        _p, lo, hi = _wilson(m, m + w)
        rows.append(dict(year=y, males=m, females=w, ratio=m / w,
                         lo=lo / (1 - lo), hi=hi / (1 - hi)))
    return pd.DataFrame(rows).set_index("year")


# --------------------------------------------------------------------------------------------------
# Drawing helpers, as the plate draws them
# --------------------------------------------------------------------------------------------------
def _log_axis(ax, axis="y"):
    """The plate's log axis: major ticks at 1, 2 and 5 of each decade, written out in full."""
    a = ax.yaxis if axis == "y" else ax.xaxis
    (ax.set_yscale if axis == "y" else ax.set_xscale)("log")
    a.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0), numticks=12))
    a.set_major_formatter(FuncFormatter(
        lambda v, p: num(v, "en", 0 if v >= 1 else (1 if v >= 0.1 else 2))))
    a.set_minor_formatter(NullFormatter())


def _fmt(ax, axis="y", dec=0):
    f = FuncFormatter(lambda v, p: num(v, "en", dec))
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(f)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(f)


def _rate(ax, d, color, label, ls="-", mk="o", band=True, lw=2.2):
    """One rate series: line, marker (open when the series is dashed) and its exact-CI ribbon."""
    ax.plot(d.index, d.rate, ls=ls, marker=mk, color=color, lw=lw, markersize=5.5, label=label,
            markerfacecolor=color if ls == "-" else "white")
    if band:
        ax.fill_between(d.index, d.lo, d.hi, color=color, alpha=0.13, lw=0)


def _end_label(ax, y, s, color):
    return ax.annotate(s, (LAST, y), xytext=(3, 0), textcoords="offset points",
                       fontsize=FS_MIN + 0.5, color=color, va="center", fontweight="bold")


def _shade_years(ax, years=PANDEMIC):
    for y in years:
        ax.axvspan(y - 0.5, y + 0.5, color="grey", alpha=0.12, zorder=0)


def _context(ax, law_y=0.97, pandemic_label=True, pandemic_y=0.97, law_label=True):
    """The two context marks: the 2020–21 reporting disruption and the Law 21.545 line.

    Both are labelled once per plate — in (a) — because the caption says they mean the same in every
    panel; the labels carry the plate's translucent white frame so a series stays visible under them.
    """
    _shade_years(ax)
    if pandemic_label:
        ax.text(2020.5, pandemic_y, N_PANDEMIC, transform=ax.get_xaxis_transform(), ha="center",
                va="top", fontsize=FS_MIN, color=GREY_TEXT, linespacing=1.15, bbox=dict(NOTE_BBOX))
    ax.axvline(LAW_X, color="#444444", ls=":", lw=1.0, zorder=1)
    if law_label:
        ax.text(LAW_X + 0.06, law_y, N_LAW, transform=ax.get_xaxis_transform(), ha="left", va="top",
                fontsize=FS_MIN, color="#444444", linespacing=1.15, bbox=dict(NOTE_BBOX))


def _framed_legend(ax, *args, loc="upper right", fontsize=FS_MIN, **kw):
    """A legend on the plate's opaque white card, so no series reads through its text."""
    lg = ax.legend(*args, loc=loc, fontsize=fontsize, frameon=True, framealpha=1.0,
                   edgecolor="#cccccc", facecolor="white", borderpad=0.25, **kw)
    lg.set_zorder(6)
    lg.set_in_layout(False)
    return lg


def _plain_legend(ax, *args, loc="upper right", fontsize=FS_MIN, **kw):
    lg = ax.legend(*args, loc=loc, fontsize=fontsize, **kw)
    lg.set_in_layout(False)
    return lg


def _drop_clear(ax, anns, pad_pt=1.5, limit=60):
    """Slide an end label down until it clears the opaque legend and the label above it.

    Panel (b) ends its three series a few points apart and prints each one's 2024 value beside its
    marker; the topmost of them, 872, reaches into the legend card, which is opaque on purpose. The
    stored plate drops the labels that collide, one step at a time, keeping their order; this is the
    same move, measured rather than hand-placed. It does nothing when nothing collides.
    """
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    blocking = []
    lg = ax.get_legend()
    if lg is not None and lg.get_visible() and lg.get_frame_on():
        blocking.append(lg.get_window_extent(r).padded(pad_pt))
    for a in sorted(anns, key=lambda t: -t.xy[1]):        # highest series first
        for _ in range(limit):
            if not any(a.get_window_extent(r).padded(pad_pt).overlaps(q) for q in blocking):
                break
            dx, dy = a.get_position()                     # the offset, in points
            a.set_position((dx, dy - 1.0))
        blocking.append(a.get_window_extent(r).padded(pad_pt))


def _align_titles(fig, axes, titles):
    """Anchor every panel head to the left edge of ITS grid cell, not to its axes.

    In a narrow cell the axes start well to the right of the cell — the y label and its tick column
    take 15–20 mm — so a title anchored to the axes drifts inward and the six heads no longer line
    up. The stored plate anchors them to the cell, 2 mm in; this is that move.
    """
    fig.canvas.draw()
    ncols = 2
    for ax, t in zip(axes, titles):
        try:
            col = ax.get_subplotspec().colspan.start
        except Exception:                                # pragma: no cover — defensive
            col = 0 if ax.get_position().x0 < 0.5 else 1
        target = col / ncols + CELL_MARGIN               # left edge of the cell, 2 mm in
        pos = ax.get_position()
        t.set_x((target - pos.x0) / pos.width)


def _tuck_ylabels(fig, axes, titles, pad_px=2.0):
    """Slide a rotated y label down until it clears the panel head above it.

    'Episodes with F84 per 100,000 GRD episodes (log)' is taller at 8 pt than the 62 mm cell it
    labels, so matplotlib, which centres it on the axes, pushes its last words up into the head of
    the panel. The stored plate drops the label by the overlap — it then runs a little past the foot
    of the axes, over blank canvas beside the year ticks, where nothing else is drawn. This is that
    move, measured rather than hand-placed.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax, t in zip(axes, titles):
        lab = ax.yaxis.label
        if not str(lab.get_text()).strip():
            continue
        top = min(t.get_window_extent(r).y0 - pad_px, fig.bbox.y1 - pad_px)
        over = lab.get_window_extent(r).y1 - top
        if over > 0.5:
            lab.set_y(lab.get_position()[1] - over / ax.bbox.height)


# --------------------------------------------------------------------------------------------------
# The plate
# --------------------------------------------------------------------------------------------------
def draw():
    t = year_summary()
    ao, af = ys(t, "observed", "all", "any"), ys(t, "fixed65", "all", "any")
    po, pf = ys(t, "observed", "all", "principal"), ys(t, "fixed65", "all", "principal")

    style()
    plt.rcParams.update(PLATE_RC)
    fig, ax = plt.subplots(3, 2, figsize=(PLATE_W_IN, PLATE_H_IN), layout="constrained")
    try:
        fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    except AttributeError:                               # pragma: no cover — older matplotlib
        pass
    axes, titles = [], []

    def head(a, k):
        axes.append(a)
        titles.append(a.set_title(f"({'abcdef'[k]}) {T[k]}", loc="left",
                                  fontsize=FS_TITLE, fontweight="bold"))

    # (a) any position and principal, observed panel and fixed panel of 65 ---------------------
    a = ax[0, 0]
    _rate(a, ao, BLUE, L_ANY_OBS)
    _rate(a, af, BLUE, L_ANY_FIX, ls="--", mk="o", band=False, lw=1.0)
    _rate(a, po, ORANGE, L_PRI_OBS, mk="s")
    _rate(a, pf, ORANGE, L_PRI_FIX, ls="--", mk="s", band=False, lw=1.0)
    ends_a = [_end_label(a, d_.rate.iloc[-1], num(d_.rate.iloc[-1], "en", 0), colr)
              for d_, colr in ((ao, BLUE), (po, ORANGE))]
    _log_axis(a)
    a.set_ylim(8, 4000)
    a.set_xticks(YEARS); a.set_xticklabels([str(y) for y in YEARS], fontsize=FS_MIN + 0.5)
    a.set_xlabel(L_YEAR); a.set_ylabel(U_RATE_LOG); a.margins(x=0.13)
    # the panel counts are a foot row of their own: the rate is a ratio, and the number of hospitals
    # behind it belongs beside the year, not on the rate axis.
    a.text(0.01, 0.085, L_HOSP_N, transform=a.transAxes, fontsize=FS_MIN, color=DARK,
           ha="left", va="center")
    for y in YEARS:
        a.text(y, 10.0, num(ao.loc[y, "hospitals_n"], "en", 0), fontsize=FS_MIN, ha="center",
               va="center", color=DARK)
    _context(a, law_y=0.40, pandemic_y=0.40)
    _plain_legend(a, loc="upper right", handlelength=1.5)
    head(a, 0)

    # (b) strict hospitalisation against major ambulatory surgery, observed panel ----------------
    b = ax[0, 1]
    ends_b = []
    for act, lab, colr, mk in (("all", L_ACT[0], BLUE, "o"),
                               ("hospitalisation", L_ACT[1], GREEN, "s"),
                               ("cma", L_ACT[2], PINK, "^")):
        d_ = ys(t, "observed", act, "any")
        _rate(b, d_, colr, lab, mk=mk)
        ends_b.append(_end_label(b, d_.rate.iloc[-1], num(d_.rate.iloc[-1], "en", 0), colr))
    # 'other' is deliberately absent: its denominator is 0 from 2020 on, which is a category that
    # stopped being reported, not a zero, and a line through it would read as a collapse.
    b.set_xticks(YEARS); b.set_xticklabels([str(y) for y in YEARS], fontsize=FS_MIN + 0.5)
    b.set_xlabel(L_YEAR); b.margins(x=0.13)
    b.set_ylim(0, 1050); b.set_yticks([0, 200, 400, 600, 800])
    b.set_ylabel(U_RATE); _fmt(b, "y", 0)
    _context(b, pandemic_label=False, law_label=False)
    _framed_legend(b, loc="upper right", handlelength=1.5)
    head(b, 1)

    # (c) the rate inside each coding-depth stratum, 2019 against 2024 ---------------------------
    c = ax[1, 0]
    xb = np.arange(len(DEPTH_BINS))
    for off, year, colr in ((-0.2, FIRST, LIGHT_BLUE), (0.2, LAST, BLUE)):
        r = depth_year(year)
        c.bar(xb + off, r.rate_per_100k_episodes, width=0.38, color=colr, label=str(year))
        c.errorbar(xb + off, r.rate_per_100k_episodes,
                   yerr=[r.rate_per_100k_episodes - r.rate_lo, r.rate_hi - r.rate_per_100k_episodes],
                   fmt="none", ecolor=DARK, elinewidth=0.6, capsize=1.2)
    c.set_xticks(xb); c.set_xticklabels([_dash(s) for s in DEPTH_BINS], fontsize=FS_MIN + 0.5)
    c.set_xlabel(U_DEPTH_X); c.set_ylabel(U_DEPTH)
    _fmt(c, "y", 0); c.set_ylim(0, depth_ceiling())
    _plain_legend(c, loc="upper left", handlelength=1.2, title=L_YEAR, title_fontsize=FS_MIN)
    ci = c.inset_axes([0.36, 0.60, 0.60, 0.36])
    ci.plot(ao.index, ao.coding_depth_mean_all, "o-", color=GREY_TEXT, lw=1.0, markersize=2.6,
            label=L_DEPTH_ALL)
    ci.plot(ao.index, ao.coding_depth_mean_f84, "s-", color=ORANGE, lw=1.0, markersize=2.6,
            label=L_DEPTH_F84)
    _shade_years(ci)
    ci.set_xticks(YEARS); ci.set_xticklabels([f"'{y % 100:02d}" for y in YEARS], fontsize=FS_MIN)
    ci.tick_params(labelsize=FS_MIN, length=1.6, pad=1.0)
    ci.set_title(L_DEPTH_INSET, fontsize=FS_MIN + 0.8, fontweight="bold", pad=1.6)
    lg = ci.legend(fontsize=FS_MIN, loc="lower right", handlelength=1.0, borderpad=0.2,
                   labelspacing=0.15)
    lg.set_in_layout(False)
    ci.set_ylim(3.5, 7.6); _fmt(ci, "y", 1); ci.grid(alpha=0.3)
    head(c, 2)

    # (d) population rate by age and sex, first year against last --------------------------------
    d = ax[1, 1]
    series = [(FIRST, "HOMBRE", LIGHT_BLUE, "o", "--"), (LAST, "HOMBRE", BLUE, "o", "-"),
              (FIRST, "MUJER", LIGHT_ORANGE, "s", "--"), (LAST, "MUJER", ORANGE, "s", "-")]
    xd = np.arange(len(AGE_GROUPS))
    for year, sex, colr, mk, ls in series:
        r = pop_rates(sex, year)
        off = -0.1 if sex == "HOMBRE" else 0.1
        d.errorbar(xd + off, r.rate.replace(0, np.nan),
                   yerr=[(r.rate - r.lo).clip(lower=0), r.hi - r.rate], fmt=mk + ls, color=colr,
                   lw=1.1, capsize=1.2, markersize=2.8, elinewidth=0.6,
                   label=f"{L_MALES if sex == 'HOMBRE' else L_FEMALES} {year}")
    d.set_xticks(xd)
    d.set_xticklabels([_dash(g) for g in AGE_GROUPS], rotation=60, ha="right", fontsize=FS_MIN)
    _log_axis(d); d.set_ylim(0.06, 700)
    d.tick_params(axis="y", labelsize=FS_MIN)
    d.set_xlabel(U_AGE_X); d.set_ylabel(U_POP, fontsize=FS_MIN + 0.5)
    # the numerator is located by place of care and the denominator by residence: the panel is a
    # complementary reading, never a use rate for a defined population.
    d.text(0.02, 0.03, N_POP, transform=d.transAxes, fontsize=FS_MIN, color=GREY_TEXT,
           va="bottom", linespacing=1.25)
    _plain_legend(d, loc="upper right", ncol=2, handlelength=1.4, columnspacing=0.7)
    head(d, 3)

    # (e) the 72 hospitals of 2024, ranked ------------------------------------------------------
    e = ax[2, 0]
    h = hospitals()
    yr = np.arange(len(h))
    colours = [BLUE if v else ORANGE for v in h.fixed]
    floor = max(1.0, float(h.rate[h.rate > 0].min()) * 0.5)
    e.errorbar(h.rate.clip(lower=floor), yr,
               xerr=[(h.rate - h.lo).clip(lower=0), h.hi - h.rate], fmt="none",
               ecolor="#a5a5a5", elinewidth=0.5, zorder=1)
    e.scatter(h.rate.clip(lower=floor), yr, c=colours, s=7, zorder=3, edgecolor="white",
              linewidth=0.3)
    national = PER * h.f84.sum() / h.episodes.sum()
    e.axvline(national, color=DARK, ls="--", lw=0.9)
    # the left ~9% and right ~20% of the panel are kept clear of data: the eight extreme hospitals
    # are labelled there, and their label positions are computed from these limits.
    x_lo, x_hi = floor * 0.42, float(h.hi.max()) * 6.5
    y_lo, y_hi = -2.5, len(h) + 0.5
    _log_axis(e, axis="x"); e.set_xlim(x_lo, x_hi)
    e.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=8))
    e.set_ylim(y_lo, y_hi); e.set_yticks([])

    def fx(frac):                                        # panel-width fraction -> log data coord
        return x_lo * (x_hi / x_lo) ** frac

    def fy(frac):
        return y_lo + frac * (y_hi - y_lo)

    e.text(national, 0.985, f"{L_NATIONAL} = {num(national, 'en', 0)}",
           transform=e.get_xaxis_transform(), fontsize=FS_MIN, color=DARK, va="top", ha="center")
    # the extremes are numbered here and named in the caption: eight hospital names do not fit
    # legibly in a 62 mm cell. Each label sits in the margin on a fixed step, joined to its point by
    # a leader drawn as a line rather than as an arrow.
    for k, i in enumerate(range(len(h) - 1, len(h) - 6, -1)):
        y_lab = fy(0.975 - 0.075 * k)
        e.plot([h.hi.iloc[i], fx(0.885)], [yr[i], y_lab], color=LEADER, lw=0.4, zorder=1,
               solid_capstyle="butt")
        e.text(fx(0.905), y_lab, str(k + 1), fontsize=FS_MIN, ha="left", va="center", color=DARK,
               fontweight="bold")
    for k in range(3):
        y_lab = fy(0.170 - 0.075 * k)
        e.plot([max(h.lo.iloc[k], floor), fx(0.092)], [yr[k], y_lab], color=LEADER, lw=0.4,
               zorder=1, solid_capstyle="butt")
        e.text(fx(0.072), y_lab, "xyz"[k], fontsize=FS_MIN, ha="right", va="center", color=DARK,
               fontweight="bold")
    n_fixed, n_new = int(h.fixed.sum()), int((~h.fixed).sum())
    _framed_legend(e, handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE, markersize=3.6,
               label=L_FIXED.format(num(n_fixed, "en", 0))),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE, markersize=3.6,
               label=L_NEW.format(num(n_new, "en", 0)))], loc="lower right", handlelength=1.0)
    e.set_ylabel(U_RANK.format(num(len(h), "en", 0)))
    e.set_xlabel(U_HOSP_X)
    e.tick_params(axis="x", labelsize=FS_MIN + 0.5)
    e.grid(axis="y", visible=False)
    head(e, 4)

    # (f) episodes, unique persons within the year and the male:female ratio ---------------------
    f = ax[2, 1]
    x = np.array(YEARS, dtype=float)
    # counts in THOUSANDS: the exact figures are in the plate's table and its caption, and six-figure
    # tick labels leave no room for the rotated axis label in a 90 mm cell.
    f.bar(x - 0.2, ao.n_episodes_f84 / 1e3, width=0.38, color=LIGHT_BLUE, label=L_EPISODES)
    f.bar(x + 0.2, ao.persons_within_year / 1e3, width=0.38, color=BLUE, label=L_PERSONS)
    for xi, ne, npers in zip(x, ao.n_episodes_f84, ao.persons_within_year):
        f.text(xi, max(ne, npers) / 1e3 * 1.03, num(ne / npers, "en", 2), ha="center",
               fontsize=FS_MIN, color=DARK)
    f.set_ylim(0, float(ao.n_episodes_f84.max()) / 1e3 * 2.5)
    f.set_xticks(YEARS); f.set_xticklabels([str(y) for y in YEARS], fontsize=FS_MIN + 0.5)
    f.set_xlabel(L_YEAR); _fmt(f, "y", 0); f.set_ylabel(U_COUNT)
    f2 = f.twinx(); f2.spines["right"].set_visible(True); f2.grid(False)
    mf = mf_ratio()
    f2.errorbar(x, mf.ratio, yerr=[mf.ratio - mf.lo, mf.hi - mf.ratio], fmt="o-", color=ORANGE,
                lw=1.2, capsize=1.6, markersize=3.0, elinewidth=0.6, label=L_MF)
    f2.set_ylim(0, 6.6); f2.set_yticks([0, 1, 2, 3, 4, 5, 6]); f2.set_ylabel(U_MF)
    _fmt(f2, "y", 1); f2.tick_params(labelsize=FS_TICK, right=True)
    _context(f, pandemic_label=False, law_label=False)
    h1, l1 = f.get_legend_handles_labels()
    h2, l2 = f2.get_legend_handles_labels()
    _framed_legend(f, h1 + h2, l1 + l2, loc="upper right", handlelength=1.4)
    head(f, 5)

    for a_ in axes:
        for txt in a_.texts:
            txt.set_in_layout(False)
    _align_titles(fig, axes, titles)
    _tuck_ylabels(fig, axes, titles)
    _drop_clear(a, ends_a)
    _drop_clear(b, ends_b)
    return fig


# --------------------------------------------------------------------------------------------------
# Verification: the drawn values against the tables and against the stored plate
# --------------------------------------------------------------------------------------------------
#: Values read off `docs/study/corpus/figures/fig2_grd_core.jpg` (pixel positions of markers, caps
#: and printed labels), used to confirm the redraw plots the same series as the stored plate.
PLATE_READ = {
    "(a) any position 2024 end label": "804",
    "(a) principal 2024 end label": "36",
    "(a) hospitals foot row": "65 65 65 65 68 72",
    "(b) end labels (all / hospitalisation / CMA)": "804 / 872 / 524",
    "(c) 2024 bar heights": [16.5, 662.7, 1068.0, 1051.4, 1038.0, 1041.6, 898.0, 646.5],
    "(d) males 2024 at 0-4 and 5-9": [177.2, 347.6],
    "(e) five highest / three lowest": [5210.7, 3610.4, 3513.1, 2068.8, 1662.6, 67.9, 69.2, 79.0],
    "(e) national line": 804.0,
    "(f) multiplicity labels": ["1.20", "1.22", "1.21", "1.19", "1.23", "1.22"],
    "(f) M:F point and caps, 2019": [3.2613, 2.9550, 3.6036],
    "(f) M:F point, 2021": 3.2252,
}


def _check():
    """Compare what `draw()` plots with the tables it parses and with the stored plate."""
    out = []
    t = year_summary()

    # the definition: `grd_selected_definition.csv` is the sin_rett slice of the year summary
    sel = _read(SOURCES[1])
    out.append(("definition of the selected series", sorted(sel.variant.unique()), [VARIANT],
                sorted(sel.variant.unique()) == [VARIANT]))
    con = _read(SOURCES[0])
    con = con[(con.variant == "con_rett") & (con.panel == "observed") & (con.activity == "all")
              & (con.position == "any") & (con.year == FIRST)]
    sin = ys(t, "observed", "all", "any")
    out.append(("sin_rett 2019 episodes, not con_rett", int(sin.loc[FIRST, "n_episodes_f84"]),
                int(con.n_episodes_f84.iloc[0]), int(sin.loc[FIRST, "n_episodes_f84"]) == 2334
                and int(con.n_episodes_f84.iloc[0]) == 2385))

    # (a) the two end labels and the foot row
    ao = sin
    po = ys(t, "observed", "all", "principal")
    for name, v in (("(a) any position 2024 end label", ao.rate.iloc[-1]),
                    ("(a) principal 2024 end label", po.rate.iloc[-1])):
        drawn = num(v, "en", 0)
        out.append((name, drawn, PLATE_READ[name], drawn == PLATE_READ[name]))
    foot = " ".join(str(int(v)) for v in ao.hospitals_n)
    out.append(("(a) hospitals foot row", foot, PLATE_READ["(a) hospitals foot row"],
                foot == PLATE_READ["(a) hospitals foot row"]))

    # (b) the three end labels, and 'other' left out because its denominator is 0
    ends = " / ".join(num(ys(t, "observed", a, "any").rate.iloc[-1], "en", 0)
                      for a in ("all", "hospitalisation", "cma"))
    key = "(b) end labels (all / hospitalisation / CMA)"
    out.append((key, ends, PLATE_READ[key], ends == PLATE_READ[key]))
    other = ys(t, "observed", "other", "any")
    out.append(("(b) 'other' denominator 2020-2024 is 0 (absent, not zero)",
                list(other.n_episodes_total_same_panel_activity.iloc[1:].fillna(0).astype(int)),
                [0, 0, 0, 0, 0],
                list(other.n_episodes_total_same_panel_activity.iloc[1:].fillna(0).astype(int))
                == [0, 0, 0, 0, 0]))

    # (c) the eight 2024 bars and the two inset points of 2019
    bars = [round(v, 1) for v in depth_year(LAST).rate_per_100k_episodes]
    out.append(("(c) 2024 bar heights", bars, PLATE_READ["(c) 2024 bar heights"],
                bars == PLATE_READ["(c) 2024 bar heights"]))
    inset = [round(float(ao.loc[FIRST, "coding_depth_mean_all"]), 3),
             round(float(ao.loc[FIRST, "coding_depth_mean_f84"]), 3)]
    out.append(("(c) mean depth 2019, all and F84", inset, [4.386, 4.966], inset == [4.386, 4.966]))

    # (d) the male 2024 curve at its peak and at 0-4
    m24 = pop_rates("HOMBRE", LAST).set_index("age_group").rate
    got = [round(float(m24["0-4"]), 1), round(float(m24["5-9"]), 1)]
    out.append(("(d) males 2024 at 0-4 and 5-9", got, PLATE_READ["(d) males 2024 at 0-4 and 5-9"],
                got == PLATE_READ["(d) males 2024 at 0-4 and 5-9"]))
    out.append(("(d) ten age groups with 45+ pooled", len(m24), 10, len(m24) == 10))

    # (e) the eight extremes, the panel size and the national line
    h = hospitals()
    ext = [round(v, 1) for v in list(h.rate.iloc[::-1][:5]) + list(h.rate.iloc[:3])]
    out.append(("(e) five highest / three lowest", ext, PLATE_READ["(e) five highest / three lowest"],
                ext == PLATE_READ["(e) five highest / three lowest"]))
    nat = PER * h.f84.sum() / h.episodes.sum()
    out.append(("(e) national line", round(nat), PLATE_READ["(e) national line"],
                round(nat) == PLATE_READ["(e) national line"]))
    out.append(("(e) hospitals drawn (fixed + added)", [int(h.fixed.sum()), int((~h.fixed).sum())],
                [65, 7], [int(h.fixed.sum()), int((~h.fixed).sum())] == [65, 7]))
    out.append(("(e) national line equals the observed-panel 2024 rate", round(nat, 1),
                round(float(ao.rate.iloc[-1]), 1), round(nat, 1) == round(float(ao.rate.iloc[-1]), 1)))

    # (f) the six multiplicity labels and the M:F line against the image
    mult = [num(n / p, "en", 2) for n, p in zip(ao.n_episodes_f84, ao.persons_within_year)]
    out.append(("(f) multiplicity labels", mult, PLATE_READ["(f) multiplicity labels"],
                mult == PLATE_READ["(f) multiplicity labels"]))
    mf = mf_ratio()
    got = [round(float(mf.loc[2019, c]), 4) for c in ("ratio", "lo", "hi")]
    read = PLATE_READ["(f) M:F point and caps, 2019"]
    # the image is read at the OUTER edge of a drawn cap, so the caps read wide by about 0.012;
    # the test is that the drawn interval sits inside what the image shows, and within 0.02 of it.
    ok = (got[1] >= read[1] - 0.02 and got[2] <= read[2] + 0.001 and abs(got[0] - read[0]) < 0.02)
    out.append(("(f) M:F point and caps, 2019", got, read, ok))
    got21 = round(float(mf.loc[2021, "ratio"]), 4)
    out.append(("(f) M:F point, 2021", got21, PLATE_READ["(f) M:F point, 2021"],
                abs(got21 - PLATE_READ["(f) M:F point, 2021"]) < 0.005))

    # the plate's own companion table, T2, prints the panel and the episode denominators
    t2 = _read(SOURCES[9])
    t2.columns = [c.strip() for c in t2.columns]
    row = t2[t2.Indicator.str.startswith("Hospitals observed")].iloc[0]
    got = [int(str(row[str(y)]).replace(",", "")) for y in YEARS]
    out.append(("T2: hospitals observed", got, [65, 65, 65, 65, 68, 72],
                got == [65, 65, 65, 65, 68, 72]))
    row = t2[t2.Indicator.str.startswith("GRD episodes, observed panel")].iloc[0]
    got = [int(str(row[str(y)]).replace(",", "")) for y in YEARS]
    want = [int(v) for v in ao.n_episodes_total_same_panel_activity]
    out.append(("T2: observed-panel episode denominators", got, want, got == want))
    return out


if __name__ == "__main__":
    for name, drawn, expected, ok in _check():
        print(f"{'ok ' if ok else 'BAD'} {name}: redrawn {drawn} vs {expected}")
    fig = draw()
    if len(sys.argv) > 1:                      # python3 <this file> <preview.png>
        fig.savefig(sys.argv[1], dpi=141, facecolor="white")
        print("wrote", sys.argv[1])
