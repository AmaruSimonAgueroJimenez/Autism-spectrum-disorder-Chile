"""figE28 — how every series moves when Rett syndrome is kept in or taken out of the case definition.

Redraw of the stored plate `docs/study/corpus/figures/figE28_variant_sensitivity.jpg`. The original
was drawn by `study/pipeline/` from the GRD, REM, DEIS and education microdata, which this repository
does not carry. All six panels are a view of one published table,
`docs/study/corpus/tables/E28_variant_sensitivity.csv`, which stores, for each of the seven series
and each year, the count under the two case-definition variants and the difference between them:

    Series, Year, 'with Rett (full F84)', 'without Rett (F84 except F84.2)',
    'Absolute difference (cases)', 'Relative difference (%)'

Estimator, unchanged from the original: plain counts in the unit of each series — GRD episodes, DEIS
discharges, REM A05 entries, REM P6 people under control in December, PIE students. No rates, no
standardisation, no weighting anywhere on this plate, so nothing here is a prevalence. The two bars
of every pair are the two case definitions: `con_rett` is the full F84 family including F84.2 Rett
syndrome, `sin_rett` is F84 except F84.2. The number printed over each pair is the count contributed
by Rett syndrome, written as the negative that removing it produces (`sin_rett − con_rett`); panel
(e) prints the same quantity with the sign of the published column (`con_rett − sin_rett`), and panel
(f) is the published relative difference, which takes the without-Rett value as the denominator
(DEIS 2019: 32/304 = 10.53 %).

Every number drawn is parsed from that one table: the counts are thousands-separated strings
('15,685') and the relative difference is a percent string ('7.15%'). The caption's remark that the
education, survey, A03/A27/A28, P2 and strict-autism series are identical under both variants is kept
as the footnote the plate prints; the plate itself draws only the education series as the zero line,
and no invented zero series are added.

The corpus is English only, so this module is English only.
"""
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from figstyle import *

PLATE = "figE28_variant_sensitivity"
SOURCES = ["docs/study/corpus/tables/E28_variant_sensitivity.csv"]
NOTE = ("Redraws the six panels of figE28 — the GRD, REM A05, REM P6 and DEIS counts under the two "
        "case-definition variants with the Rett contribution printed over each pair, and the "
        "absolute and relative difference of all seven series — from the published E28 variant "
        "table, in each series' own unit and with no rate, weighting or standardisation.")

TABLE = BASE / "corpus" / "tables" / "E28_variant_sensitivity.csv"

# --- the seven series of the table, in the order of the plate's legend ----------------------------
GRD_ANY = "GRD · documented F84 (any position)"
GRD_PRI = "GRD · principal F84"
A05 = "REM A05 · PDD-family entries"
P6_PRIMARY = "REM P6 · primary care, December"
P6_SPECIALTY = "REM P6 · specialty care, December"
DEIS = "DEIS · principal F84"
EDUCATION = "Education · harmonised PIE (identical)"
SERIES = [GRD_ANY, GRD_PRI, A05, P6_PRIMARY, P6_SPECIALTY, DEIS, EDUCATION]
COLOUR = dict(zip(SERIES, [BLUE, ORANGE, GREEN, PINK, GOLD, SKY, YELLOW]))

# --- the two case-definition variants, wording verbatim from the plate's legend --------------------
CON_RETT = "with Rett (full F84)"            # column 'with Rett (full F84)'      — full F84
SIN_RETT = "without Rett (F84 except F84.2)"  # column 'without Rett (F84 except F84.2)'

#: (a)-(d): the series drawn as bar pairs, the short name the plate puts under each group, and the
#: panel heading. Panels (a) and (c) carry two series side by side in one panel.
BAR_PANELS = {
    "a": ("GRD: episodes with documented F84",
          [(GRD_ANY, "GRD F84 any"), (GRD_PRI, "GRD F84 principal")]),
    "b": ("REM A05: PDD-family entries", [(A05, None)]),
    "c": ("REM P6: December population under\ncontrol",
          [(P6_PRIMARY, "P6 primary"), (P6_SPECIALTY, "P6 specialty")]),
    "d": ("DEIS: discharges with principal F84", [(DEIS, None)]),
}
LINE_PANELS = {"e": "Absolute difference con_rett − sin_rett",
               "f": "Relative difference (%)"}
Y_LABEL = {"a": "Cases (annual count)", "b": "Cases (annual count)",
           "c": "Cases (annual count)", "d": "Cases (annual count)",
           "e": "Absolute difference (cases)", "f": "Relative difference (%)"}
FOOTNOTE = ("(f) Series identical in both variants: education, surveys, A03/A27/A28, P2 and strict "
            "autism.")

# --- geometry and marks measured off the stored plate (figure fractions of its 1000x1361 canvas) ---
FIG_W_IN, FIG_H_IN = 8.27, 11.25             # 210 x 286 mm, the stored plate's proportions
AXES_X = {"a": 0.084, "c": 0.084, "e": 0.084, "b": 0.584, "d": 0.584, "f": 0.584}
AXES_BOX = {"a": (0.7414, 0.2351), "b": (0.7414, 0.2351),     # (bottom, height) per row
            "c": (0.3857, 0.2355), "d": (0.3857, 0.2355),
            "e": (0.1543, 0.1374), "f": (0.1543, 0.1374)}
AXES_W = 0.3995
TITLE_Y = {"a": 0.9780, "b": 0.9780, "c": 0.6223, "d": 0.6223, "e": 0.2939, "f": 0.2939}
TITLE_X = {"a": 0.010, "c": 0.010, "e": 0.010, "b": 0.510, "d": 0.510, "f": 0.510}

WIDTH, OFFSET = 0.32, 0.19    # bar width and the offset of each variant from the group centre
HEADROOM = 1.220              # top of (a)-(d): the tallest bar leaves room for the legend
LABEL_PAD = 0                 # points between the taller bar and its Rett label
BOX = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.5)   # behind the Rett label
# type sizes, each measured off the stored plate: the bar panels label their axis larger than they
# tick it, the rotated group labels of (a) and (c) are set smaller than the plain year labels of
# (b) and (d), and (e) and (f) tick larger but label their y axis smaller than the bar panels
TITLE_SIZE, RETT_SIZE, LEGEND_SIZE = 10.5, 7.5, 8
AXIS_LABEL_SIZE = 9.3         # 'Cases (annual count)' and 'Year'
BAR_TICK_SIZE, ROTATED_TICK_SIZE = 7.5, 7.0
LINE_TICK_SIZE, LINE_YLABEL_SIZE, LINE_LEGEND_SIZE = 8.5, 7.5, 7.0
Y_TICK_PAD = 5.5              # the stored plate sets the y labels further off the axis than the x
MARKER = 6.6                  # (e) and (f): marker diameter in points, measured off the plate
FOOT_GREY = "#555555"


# ------------------------------------------------------------------ the tracked table and parsing
def _count(cell):
    """'15,685' -> 15685; the presentation table stores every count as a separated string."""
    return int(str(cell).replace(",", "").strip())


def _percent(cell):
    """'7.15%' -> 7.15, the published relative difference, without recomputing it."""
    return float(str(cell).strip().rstrip("%"))


def load():
    """The E28 table with its four numeric columns parsed, indexed by series and year."""
    t = pd.read_csv(TABLE, encoding="utf-8-sig")
    t.columns = [c.strip() for c in t.columns]
    con = next(c for c in t.columns if c.startswith("with Rett"))
    sin = next(c for c in t.columns if c.startswith("without Rett"))
    absolute = next(c for c in t.columns if c.startswith("Absolute difference"))
    relative = next(c for c in t.columns if c.startswith("Relative difference"))
    out = t.assign(series=t["Series"].str.strip(), year=t["Year"].astype(int),
                   con=t[con].map(_count), sin=t[sin].map(_count),
                   absolute=t[absolute].map(_count), relative=t[relative].map(_percent))
    missing = set(SERIES) - set(out.series)
    assert not missing, f"{TABLE.name} is missing {sorted(missing)}"
    # the difference the table publishes is the one the plate prints; check it against the counts
    assert (out.absolute == out.con - out.sin).all(), "absolute difference != con_rett - sin_rett"
    return out.sort_values(["series", "year"], kind="stable")


def _rows(t, series):
    """The years of one series, in order, as (year, con_rett, sin_rett, difference) tuples."""
    d = t[t.series == series]
    return list(zip(d.year, d.con, d.sin, d.absolute))


# ------------------------------------------------------------------------------ drawing the panels
def _bar_panel(ax, t, key):
    """(a)-(d): the two case definitions side by side, one pair per year of each series."""
    heading, members = BAR_PANELS[key]
    ticks, con, sin, diff = [], [], [], []
    for series, short in members:
        for year, c, s, d in _rows(t, series):
            ticks.append(f"{short}\n{year}" if short else str(year))
            con.append(c); sin.append(s); diff.append(d)

    rotated = any(short for _, short in members)
    x = np.arange(len(ticks))
    ax.bar(x - OFFSET, con, width=WIDTH, color=BLUE, label=CON_RETT, zorder=3)
    ax.bar(x + OFFSET, sin, width=WIDTH, color=ORANGE, label=SIN_RETT, zorder=3)

    top = HEADROOM * max(max(con), max(sin))
    ax.set_ylim(0, top)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_xticks(x)
    ax.set_xticklabels(ticks, rotation=90 if rotated else 0)
    ax.set_ylabel(Y_LABEL[key], fontsize=AXIS_LABEL_SIZE)
    clean(ax, "both")
    ax.tick_params(axis="x", length=0, pad=3.5,
                   labelsize=ROTATED_TICK_SIZE if rotated else BAR_TICK_SIZE)
    ax.tick_params(axis="y", length=0, pad=Y_TICK_PAD, labelsize=BAR_TICK_SIZE)
    ax.legend(loc="upper left", fontsize=LEGEND_SIZE, handlelength=2.0, labelspacing=0.5)

    # the count Rett syndrome contributes, over the taller bar of each pair and written as the loss
    # that removing it produces; the box is translucent, as the stored plate draws it
    labels = []
    for xi, c, s, d in zip(x, con, sin, diff):
        labels.append(ax.annotate(f"−{num(d, 'en')}", (xi, max(c, s)), xytext=(0, LABEL_PAD),
                                  textcoords="offset points", ha="center", va="bottom",
                                  fontsize=RETT_SIZE, bbox=BOX, zorder=5))
    return labels


def _clear_legend(fig, ax, labels):
    """Drop a Rett label onto the top of its bar where it would otherwise run into the legend.

    Two labels of the stored plate sit inside the bar instead of above it — the 2024 pair of panel
    (a) and the 2025 pair of panel (c), the tallest pair of each panel, both under the legend. The
    rule is the plate's own: a label that collides with the legend is pinned to the bar top instead.
    """
    renderer = fig.canvas.get_renderer()
    box = ax.get_legend().get_window_extent(renderer)
    for text in labels:
        if text.get_window_extent(renderer).overlaps(box):
            text.set_va("top")
            text.xyann = (0, -LABEL_PAD)


def _line_panel(ax, t, key):
    """(e) and (f): the difference of all seven series, in cases and as a percentage."""
    field = "absolute" if key == "e" else "relative"
    for series in SERIES:
        d = t[t.series == series]
        ax.plot(d.year, d[field], marker="o", markersize=MARKER, lw=2.2, color=COLOUR[series],
                label=series, zorder=3)
    ax.axhline(0, color=BLACK, lw=1.0, zorder=4)     # the education series sits on it

    ax.set_xlabel("Year", fontsize=AXIS_LABEL_SIZE)
    ax.set_ylabel(Y_LABEL[key], fontsize=LINE_YLABEL_SIZE)
    year_ticks(ax, range(int(t.year.min()), int(t.year.max()) + 1))
    if key == "e":
        ax.yaxis.set_major_formatter(thousands("en"))
    else:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:.1f}"))
    clean(ax, "both")
    ax.tick_params(axis="x", length=0, pad=3.5, labelsize=LINE_TICK_SIZE)
    ax.tick_params(axis="y", length=0, pad=Y_TICK_PAD, labelsize=LINE_TICK_SIZE)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.194), fontsize=LINE_LEGEND_SIZE,
              labelspacing=0.19, handlelength=1.6, handletextpad=0.5, borderpad=0.2)


# ---------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of figE28 and hand back the figure."""
    t = load()

    style()
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    axes = {k: fig.add_axes([AXES_X[k], AXES_BOX[k][0], AXES_W, AXES_BOX[k][1]])
            for k in "abcdef"}

    bar_labels = {k: _bar_panel(axes[k], t, k) for k in "abcd"}
    for k in "ef":
        _line_panel(axes[k], t, k)

    for k in "abcdef":
        heading = BAR_PANELS[k][0] if k in BAR_PANELS else LINE_PANELS[k]
        fig.text(TITLE_X[k], TITLE_Y[k], f"({k}) {heading}", fontweight="bold",
                 fontsize=TITLE_SIZE, ha="left", va="bottom", linespacing=1.16)
    fig.text(0.009, 0.0037, FOOTNOTE, fontsize=7.5, color=FOOT_GREY, ha="left", va="bottom")

    fig.draw_without_rendering()                    # so the legend boxes can be measured
    for k in "abcd":
        _clear_legend(fig, axes[k], bar_labels[k])
    return fig


if __name__ == "__main__":
    import sys
    from pathlib import Path

    figure = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/"qa"/f"{PLATE}_redraw.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=1000/FIG_W_IN, facecolor="white")
    print("wrote", out)
