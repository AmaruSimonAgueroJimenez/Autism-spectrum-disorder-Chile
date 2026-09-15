"""E40 — territorial distribution of hospital recognition of autism by comuna of residence.

Redraw of the stored plate `docs/study/corpus/figures/E40_maps_grd_smoothed_ratio.jpg`. The original
was drawn by `study/pipeline/` from the GRD microdata, which this repository does not carry; all six
panels are rebuilt here from the plate's own companion table plus the comuna cartography.

What the plate shows, unchanged. Every series is the F84 family EXCLUDING Rett syndrome (`sin_rett`),
pooled 2019–2024, by comuna of RESIDENCE, and the outcome is 'GRD episodes with documented F84 in any
position' — F84-principal is a separate series and is not this plate. Panels (a), (b) and (f) are
INTERNALLY INDIRECTLY STANDARDISED ratios, so the national reference is 1 by construction, with
Marshall's empirical-Bayes smoother on top; they are not crude rates and not directly standardised.
Panel (c) alone is the CRUDE rate per 100,000 person-years on the compatible INE base-2017 comuna
denominator. Panel (a) counts EPISODES and panel (b) unique PERSONS within year: the table keeps them
in separate columns and they must not be interchanged.

  (a) empirical-Bayes smoothed standardised ratio of GRD F84 episodes, diverging scale centred on 1;
  (b) the same smoother over unique persons within year;
  (c) crude rate per 100,000 person-years, sequential scale;
  (d) the smoother's shrinkage weight against the expected counts it depends on, x on a log scale;
  (e) the distribution of the crude and the smoothed ratio over the comunas, one shared bin grid;
  (f) the eighteen comunas with the highest smoothed ratio, each with its crude ratio and exact
      Poisson 95% CI and its observed episodes in brackets.

Sources.

* `E40_grd_smoothed_ratio_comuna.csv` is the plate's own companion table: 346 comuna rows carrying the
  observed episodes, the expected counts, the person-years, the crude rate with its interval, the
  crude standardised ratio with its exact Poisson interval, the empirical-Bayes smoothed ratio, the
  shrinkage weight and the persons smoothed ratio. Only 'Observed episodes' is censored (37 rows read
  '<5'); every quantity this plate draws is present for all 346 comunas, and none of the eighteen rows
  of panel (f) is suppressed. Sorting by the smoothed ratio descending reproduces panel (f) in the
  plate's order, San Carlos to Coquimbo.
* `catalogo_comunas.csv` supplies the `continental` flag. It is what reduces the 346 comunas to the
  342 the maps cover, and the colour limits are taken over those 342 so that the four oceanic comunas
  — above all Antártica, whose rate of 117.4 per 100,000 rests on fewer than five episodes — cannot
  stretch a scale for territory that is never drawn.

Do NOT substitute `output_files/consolidacion/grd_rates_comunal.csv`: it holds the same quantities in
a different variant (San Carlos smoothed 2.746 against this table's 2.78, expected 69.47 against 69.2)
and would produce maps that look right and are not.

Cartography. Panels (a)–(c) are choropleths and cannot be drawn from a table: they need the comuna
polygons, and this module reads `data/comunas.shp`, the same file the hospital chapter of the report
already draws its commune maps from. That file is NOT tracked in this repository, so those three
panels only render where it is present; panels (d), (e) and (f) run from a clone. The map recipe is
the pipeline's own: clip to the continental box, project to the equal-area conic of the study, simplify
to 500 m and draw the country in three latitude bands at one common vertical scale. The shapefile
carries one polygon with no comuna code — the 'Zona sin demarcar' of the southern ice field — and that
is the single thing the plate's 'No data' key refers to; it is assigned to the band its latitude falls
in and drawn in the plate's no-value grey.

Two conventions were read off the stored plate rather than derived, because the published table cannot
supply them: the shared histogram grid of panel (e) (thirty edges from 0 to 3, hence 29 bins, which is
what the plate's bar boundaries measure out at) and the 1.4 headroom that panels (e) and (f) leave
beyond their data.

Where this redraw cannot be identical. The three latitude bands render 8-11% narrower than the
stored plate (north band 56 px against 63 in panel (a), 86 against 91 in panel (c)) while their
vertical spans match to a pixel or two. The comuna colours agree, so this is the geometry, not
the data: the shapefile is not tracked and its vintage and the 500 m simplification are not
recoverable from the stored image. The table rounds the ratios to two decimals and panel (e)'s bins
are 0.1034 wide, so about one comuna in ten sits within half a rounding step of a bin edge and a few of
those cross it: the tail is exactly the plate's, but two of the crude bars near the mode land one
comuna away (the stored plate shows 18 and 22 where the published table gives 19 and 21), and the
four crowded bars around
the mode move by up to four comunas (the plate's 45-44-48-35 against this module's 49-41-45-37). The
same rounding floors panel (d)'s smallest expected counts at the printed 0.1, where the pipeline had
0.079, which shifts that panel's left-hand limit; every drawn point still sits at its own value and the
right-hand end, 918.5 expected at weight 1.00, lands on the stored plate's own pixel.

The corpus is English only and so is this module: no language parameter, no Spanish variant.
"""
import textwrap

import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from figstyle import *

PLATE = "E40_maps_grd_smoothed_ratio"
SOURCES = [
    "docs/study/corpus/tables/E40_grd_smoothed_ratio_comuna.csv",
    "output_files/consolidacion/catalogo_comunas.csv",
    "data/comunas.shp",
]
NOTE = ("Redraws the six panels of plate E40 — the comuna maps of the empirical-Bayes smoothed "
        "standardised ratio of GRD F84 episodes and of unique persons within year, the map of the crude "
        "rate per 100,000 person-years, the shrinkage weight against the expected counts, the "
        "distribution of the crude and smoothed ratios and the eighteen comunas with the highest "
        "smoothed ratio — from the plate's companion table E40_grd_smoothed_ratio_comuna.csv (346 "
        "comunas, sin_rett, pooled 2019–2024) with the continental flag of catalogo_comunas.csv; the "
        "three choropleths additionally read the comuna polygons of data/comunas.shp, which is not "
        "tracked in this repository and is the same cartography the hospital chapter uses.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIGSIZE = (180 / 25.4, 245 / 25.4)              # the plate canvas of the pipeline: 180 x 245 mm

TABLE = BASE / "corpus" / "tables" / "E40_grd_smoothed_ratio_comuna.csv"
CATALOGUE = ROOT / "output_files" / "consolidacion" / "catalogo_comunas.csv"
SHAPEFILE = ROOT / "data" / "comunas.shp"

#: Equal-area conic of the study; the pipeline measures every distance and area in it, never in
#: Web Mercator, and the maps are drawn in it so that a metre is a metre in both axes.
ALBERS = "+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 +datum=WGS84 +units=m +no_defs"
CONTINENTAL_BOX = (-76.5, -56.6, -66.0, -17.3)  # the clip that drops the oceanic islands
SIMPLIFY = 500.0                                # metres; the plotting geometry of the pipeline
#: The three latitude bands of the plate, by region code: north, centre, south.
BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]
SPAN_PAD, WIDTH_PAD = 1.04, 1.06                # air around the tallest band and around each band
GAP = 9.5 / 1000                                # gap between two bands, as a fraction of the canvas

DIVERGING, SEQUENTIAL = "RdBu_r", "YlGnBu"
ROBUST_Q = 0.98                                 # the tail the colour limits are cut at
REFERENCE = 1.0                                 # the national reference of an internal standardisation
NO_VALUE = "#e9e9e9"                            # a polygon with no comuna code: the plate's 'No data'
MAP_EDGE, KEY_EDGE = "#666666", "#666666"
HIST_HI, HIST_EDGES = 3.0, 30                   # the shared bin grid of panel (e): 30 edges, 29 bins
HIST_ALPHA = 0.75                               # the smoothed bars are laid over the crude ones
HEADROOM = 1.4                                  # free band beyond the data in panels (e) and (f)
TOP_N = 18                                      # comunas in panel (f)
WEIGHT_TOP = 1.05                               # panel (d) keeps the weight-1 ceiling inside the frame

#: Panel (f)'s x window: the reference edge on the left, the widest upper limit with headroom on the right.
F_LEFT = 0.85

TITLE_PT, LABEL_PT, TICK_PT = 9.0, 8.0, 7.0
CBAR_TICK_PT = 7.5                              # the keys carry slightly larger numbers than the axes
NOTE_PT, KEY_PT = 7.0, 7.0
HIST_KEY_PT, TOP_KEY_PT = 6.9, 6.4              # the two panel keys, as the plate sets them
WRAP_NOTE = 58                                  # the plate's line break inside panel (d)'s note

#: Boxes as fractions of the canvas, measured off the stored plate. A map cell is
#: (left, right, bottom, height) — the three bands are laid inside it — a colourbar and a chart panel
#: are the usual (left, bottom, width, height).
MAP_CELL = {"a": (0.0435, 0.4585, 0.7862, 0.1521),
            "b": (0.5345, 0.9495, 0.7862, 0.1521),
            "c": (0.0435, 0.4585, 0.4328, 0.2315)}
CBAR = {"a": (0.0435, 0.774064, 0.4150, 0.009552),
        "b": (0.5345, 0.774064, 0.4150, 0.009552),
        "c": (0.0435, 0.421382, 0.4150, 0.009552)}
BOX = {"d": (0.5895, 0.392726, 0.3900, 0.277002),
       "e": (0.0535, 0.070904, 0.3900, 0.241734),
       "f": (0.5895, 0.067965, 0.3900, 0.243571)}

#: Panel headings, with the line breaks the stored plate prints; the letter joins the first line.
TITLE = {"a": "GRD F84 episodes 2019–2024 —\nSmoothed ratio (EB) (without Rett)",
         "b": "GRD persons/year 2019–2024 — Smoothed ratio\n(EB) (without Rett)",
         "c": "GRD F84 episodes — Rate per 100,000\n2019–2024",
         "d": "Shrinkage weight of the smoother: prior mean\n= {mean:.2f}, prior variance = {var:.3f}",
         "e": "Distribution of the comuna ratios",
         "f": "{n} comunas with the highest smoothed ratio\n(observed in brackets)"}
TITLE_X = {"a": 0.010, "c": 0.010, "e": 0.010, "b": 0.466, "d": 0.466, "f": 0.466}
TITLE_TOP = {"a": 0.98237, "b": 0.98237, "c": 0.70581, "d": 0.70066, "e": 0.33917, "f": 0.34358}

RATIO_LABEL = "Smoothed ratio (EB); national reference = 1"
RATE_LABEL = "Rate per 100,000"
NO_DATA_LABEL = "No data"
CRUDE_LABEL = "Crude standardised ratio"
SMOOTH_LABEL = "Empirical-Bayes smoothed standardised ratio"
CI_LABEL = "Crude standardised ratio (95% CI)"
RATIO_AXIS = "Crude ratio / Smoothed ratio (EB)"
WEIGHT_NOTE = ["Weight 0 = the ratio is shrunk entirely to the national reference;",
               "weight 1 = the crude ratio is preserved"]


def table():
    """The plate's companion table, with the bracketed point estimates parsed out.

    Nothing is recomputed: the rate, the crude ratio and its exact Poisson limits are read from the
    published strings, the smoothed ratio and the shrinkage weight from their own columns. Only
    'Observed episodes' is censored, and it is kept as printed ('<5') because panel (f) prints it.
    """
    t = pd.read_csv(TABLE, encoding="utf-8-sig")
    t["cut_comuna"] = t.CUT.astype(int)
    t["observed"] = t["Observed episodes"].astype(str).str.strip()
    t["expected"] = t["Expected"].astype(float)
    t["weight"] = t["Shrinkage weight of the smoother"].astype(float)
    t["sir_eb"] = t["Empirical-Bayes smoothed standardised ratio"].astype(float)
    t["persons_eb"] = t["GRD persons (smoothed ratio)"].astype(float)
    t["rate"] = _point(t["Rate per 100,000 population"])
    t["sir"] = _point(t["Crude standardised ratio"])
    t["sir_lo"], t["sir_hi"] = _limits(t["Crude standardised ratio"])
    catalogue = pd.read_csv(CATALOGUE, encoding="utf-8-sig")
    t["continental"] = t.cut_comuna.map(dict(zip(catalogue.cut_comuna, catalogue.continental)))
    return t


def _point(column):
    """The point estimate of a '58.9 (51.1–67.7)' cell."""
    return column.astype(str).str.split(" ").str[0].astype(float)


def _limits(column):
    """The two limits of a '2.89 (2.50–3.32)' cell."""
    inside = column.astype(str).str.extract(r"\(([\d.]+)[–-]([\d.]+)\)")
    return inside[0].astype(float), inside[1].astype(float)


def diverging_norm(values):
    """Colour limits for a standardised ratio: symmetric about the national reference.

    The half-width is the robust tail of the distance from 1, so that the scale is readable and the
    reference sits exactly at the middle of the bar. Measured against the stored plate, panel (a)'s
    bar runs 0.043 to 1.957 and panel (b)'s 0.105 to 1.895, which is this rule over the 342 comunas
    the maps draw.
    """
    half = float(np.quantile(np.abs(values - REFERENCE), ROBUST_Q))
    return Normalize(vmin=REFERENCE - half, vmax=REFERENCE + half)


def sequential_norm(values):
    """Colour limits for a rate: the robust body of the distribution, both tails cut alike."""
    lo, hi = np.quantile(values, [1 - ROBUST_Q, ROBUST_Q])
    return Normalize(vmin=float(lo), vmax=float(hi))


def prior_variance(t):
    """The smoother's prior, recovered from the published weights, for panel (d)'s heading.

    Marshall's weight is w = s² / (s² + m / E) with the prior mean m = 1 by construction, so each row
    gives back s² = w / (E (1 − w)); the plate prints the median of those, and the 345 rows whose
    weight is below 1 return 0.2439 against the stored heading's 'prior variance = 0.244'.
    """
    keep = t.weight < 1                          # a weight of exactly 1 carries no information on s²
    return float(np.median(t.weight[keep] / (t.expected[keep] * (1 - t.weight[keep]))))


def comunas():
    """The comuna polygons of the plate, in the pipeline's own plotting geometry.

    `data/comunas.shp` is not tracked in this repository; it is the cartography the hospital chapter
    of the report already uses. Clipped to the continental box, projected to the equal-area conic and
    simplified to 500 m. The polygon with no comuna code — the 'Zona sin demarcar' of the southern
    ice field — is KEPT, because it is the one thing the plate's 'No data' key stands for.
    """
    import geopandas as gpd
    from shapely.geometry import box
    if not SHAPEFILE.exists():
        raise FileNotFoundError(
            f"{SHAPEFILE} is missing: panels (a)-(c) of {PLATE} are choropleths and need the comuna "
            "cartography, which this repository does not track.")
    g = gpd.read_file(SHAPEFILE)[["cod_comuna", "geometry"]].rename(columns={"cod_comuna": "cut_comuna"})
    g["cut_comuna"] = g.cut_comuna.astype(int)
    g = g.to_crs(4326)
    g["geometry"] = g.geometry.make_valid()
    g["geometry"] = g.geometry.intersection(box(*CONTINENTAL_BOX))
    g = g[~g.geometry.is_empty].copy().to_crs(ALBERS)
    g["geometry"] = g.geometry.simplify(SIMPLIFY)
    catalogue = pd.read_csv(CATALOGUE, encoding="utf-8-sig")
    g["cut_region"] = g.cut_comuna.map(dict(zip(catalogue.cut_comuna, catalogue.cut_region)))
    g["band"] = _band(g)
    return g


def _band(g):
    """Which of the three latitude strips each polygon is drawn in.

    A comuna goes by its region code. A polygon with no comuna code has no region either, so it goes
    by where it lies: the band whose own polygons span its centroid, which puts the ice field in the
    south strip where the plate draws it.
    """
    band = pd.Series(np.nan, index=g.index)
    for i, regions in enumerate(BANDS):
        band[g.cut_region.isin(regions)] = i
    edges = [g.geometry[band == i].total_bounds[[1, 3]] for i in range(len(BANDS))]
    for row in np.where(band.isna())[0]:
        y = g.geometry.iloc[row].centroid.y
        band.iloc[row] = int(np.argmin([max(0.0, lo - y, y - hi) for lo, hi in edges]))
    return band.astype(int)


def _map(fig, cell, shapes, values, cmap, norm):
    """One choropleth of the plate: the country in three bands at one common vertical scale.

    Every band is drawn at the same metres-per-inch, so the three strips are comparable; each band is
    then given the width its own geography needs rather than a fixed third of the cell, which is what
    keeps the narrow north and centre from floating in an empty rectangle. If the three together do
    not fit across the cell, the whole map — bands and height alike — is scaled down.
    """
    x0, x1, bottom, height = cell
    bands = [shapes[shapes.band == i] for i in range(len(BANDS))]
    bounds = [b.total_bounds for b in bands]
    span = max(b[3] - b[1] for b in bounds) * SPAN_PAD
    widths_m = [(b[2] - b[0]) * WIDTH_PAD for b in bounds]
    w_in, h_in = fig.get_size_inches()
    scale = (height * h_in) / span                       # inches per metre, shared by the three bands
    widths = [w * scale for w in widths_m]
    available = (x1 - x0 - (len(bands) - 1) * GAP) * w_in
    if sum(widths) > available:
        shrink = available / sum(widths)
        widths = [w * shrink for w in widths]
        height = height * shrink
    widths = [w / w_in for w in widths]
    x = x0 + max(0.0, (x1 - x0 - sum(widths) - (len(bands) - 1) * GAP)) / 2
    palette = plt.get_cmap(cmap)
    blank = to_rgba(NO_VALUE)
    for band, bound, width in zip(bands, bounds, widths):
        ax = fig.add_axes([x, bottom, width, height])
        seen = values.reindex(band.cut_comuna).to_numpy(float)
        colours = [blank if np.isnan(v) else palette(norm(v)) for v in seen]
        band.plot(color=colours, edgecolor=MAP_EDGE, linewidth=0.18, ax=ax)
        ax.set_aspect("auto")
        ax.set_axis_off()
        cy, cx = (bound[1] + bound[3]) / 2, (bound[0] + bound[2]) / 2
        ax.set_ylim(cy - span / 2, cy + span / 2)
        window = span * (width * w_in) / (height * h_in)  # a metre is a metre in both axes
        ax.set_xlim(cx - window / 2, cx + window / 2)
        x += width + GAP


def _colourbar(fig, box, cmap, norm, label, no_data=False):
    """The horizontal key under a map, and — under panel (a) only — the 'No data' swatch."""
    cax = fig.add_axes(box)
    bar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
    bar.outline.set_linewidth(0.7)
    cax.tick_params(labelsize=CBAR_TICK_PT, length=2.4, pad=1.8)
    cax.set_xlabel(label, fontsize=LABEL_PT, labelpad=1.0)
    if no_data:
        cax.legend(handles=[Patch(facecolor=NO_VALUE, edgecolor=KEY_EDGE, label=NO_DATA_LABEL)],
                   loc="upper center", bbox_to_anchor=(0.5, -2.82), fontsize=KEY_PT, frameon=False,
                   handlelength=1.45, handleheight=1.3, borderpad=0.0, handletextpad=0.6)


def _panel_d(fig, t):
    """The shrinkage weight against the expected counts, on a log x axis."""
    ax = fig.add_axes(BOX["d"])
    ax.set_xscale("log")
    ax.scatter(t.expected, t.weight, s=21, color=BLUE, edgecolor="white", linewidth=0.3, zorder=3)
    ax.axhline(1.0, color="black", ls=(0, (1, 1.6)), lw=0.9, zorder=2)
    ax.set_ylim(0, WEIGHT_TOP)
    ax.set_xlabel("Expected counts (indirect standardisation)", fontsize=LABEL_PT)
    ax.set_ylabel("Shrinkage weight of the smoother", fontsize=LABEL_PT)
    log_axis(ax, "x")
    ax.tick_params(labelsize=TICK_PT)
    clean(ax, grid="both")
    ax.text(0.02, 0.16, "\n".join(_wrap(line) for line in WEIGHT_NOTE), transform=ax.transAxes,
            fontsize=NOTE_PT, va="top", ha="left", linespacing=1.3, color="#333333", zorder=4)


def _panel_e(fig, t):
    """The two ratio distributions over one shared bin grid, crude behind, smoothed in front."""
    ax = fig.add_axes(BOX["e"])
    edges = np.linspace(0, HIST_HI, HIST_EDGES)
    crude, _ = np.histogram(t.sir, bins=edges)
    smooth, _ = np.histogram(t.sir_eb, bins=edges)
    ax.hist(t.sir, bins=edges, color=LIGHT, edgecolor="white", linewidth=0.5, label=CRUDE_LABEL,
            zorder=2)
    ax.hist(t.sir_eb, bins=edges, color=BLUE, alpha=HIST_ALPHA, edgecolor="white", linewidth=0.5,
            label=SMOOTH_LABEL, zorder=3)
    ax.axvline(REFERENCE, color="black", ls=(0, (4, 3)), lw=1.1, zorder=4)
    ax.set_ylim(0, max(crude.max(), smooth.max()) * HEADROOM)
    ax.set_xlabel(RATIO_AXIS, fontsize=LABEL_PT)
    ax.set_ylabel("Comunas", fontsize=LABEL_PT)
    ax.tick_params(labelsize=TICK_PT)
    clean(ax, grid="both")
    ax.legend(fontsize=HIST_KEY_PT, loc="upper center", bbox_to_anchor=(0.5, -0.135), frameon=False,
              handlelength=1.25, handleheight=0.95, borderpad=0.0, labelspacing=0.3)


def _panel_f(fig, t):
    """The eighteen comunas with the highest smoothed ratio, crude interval behind each one."""
    ax = fig.add_axes(BOX["f"])
    top = t.nlargest(TOP_N, "sir_eb")
    y = np.arange(len(top))
    ax.axvline(REFERENCE, color="black", ls=(0, (4, 3)), lw=1.1, zorder=2)
    ax.errorbar(top.sir, y, xerr=[top.sir - top.sir_lo, top.sir_hi - top.sir], fmt="o", color=GREY,
                ecolor=GREY, elinewidth=1.0, markersize=4.6, capsize=0, zorder=3)
    ax.plot(top.sir_eb, y, "o", color=ORANGE, markersize=6.6, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{c} ({o})" for c, o in zip(top.Comuna, top.observed)], fontsize=TICK_PT)
    ax.set_xlim(F_LEFT, float(top.sir_hi.max()) * HEADROOM)
    ax.invert_yaxis()
    ax.set_xlabel(RATIO_AXIS, fontsize=LABEL_PT)
    ax.tick_params(axis="x", labelsize=TICK_PT)
    ax.tick_params(axis="y", length=0)
    clean(ax, grid="x")
    ax.spines["left"].set_visible(True)
    # The key names the two series, not the two artists: a dot for the smoothed point estimate and a
    # plain rule for the crude interval, which is how the stored plate draws it.
    keys = [Line2D([], [], color=ORANGE, marker="o", markersize=6.6, ls="none", label=SMOOTH_LABEL),
            Line2D([], [], color=GREY, lw=1.0, label=CI_LABEL)]
    ax.legend(handles=keys, fontsize=TOP_KEY_PT, loc="upper center", bbox_to_anchor=(0.5, -0.135),
              frameon=False, numpoints=1, handlelength=1.35, borderpad=0.0, labelspacing=0.3)


def _wrap(text, width=WRAP_NOTE):
    """The plate's line breaking: plain character wrapping, one paragraph at a time."""
    return "\n".join(textwrap.wrap(str(text), width))


def draw():
    style()
    plt.rcParams.update({"axes.edgecolor": "#333333", "axes.linewidth": 0.7,
                         "xtick.major.size": 2.4, "ytick.major.size": 2.4,
                         "xtick.major.pad": 1.8, "ytick.major.pad": 1.8, "axes.labelpad": 2.4})
    t = table()
    mapped = t[t.continental]                    # the 342 comunas the maps cover set the colour limits
    series = {"a": ("sir_eb", DIVERGING, diverging_norm(mapped.sir_eb), RATIO_LABEL, True),
              "b": ("persons_eb", DIVERGING, diverging_norm(mapped.persons_eb), RATIO_LABEL, False),
              "c": ("rate", SEQUENTIAL, sequential_norm(mapped.rate), RATE_LABEL, False)}

    fig = plt.figure(figsize=FIGSIZE)
    shapes = comunas()
    for letter, (column, cmap, norm, label, no_data) in series.items():
        _map(fig, MAP_CELL[letter], shapes, t.set_index("cut_comuna")[column], cmap, norm)
        _colourbar(fig, CBAR[letter], cmap, norm, label, no_data=no_data)
    _panel_d(fig, t)
    _panel_e(fig, t)
    _panel_f(fig, t)

    headings = dict(TITLE)
    headings["d"] = TITLE["d"].format(mean=REFERENCE, var=prior_variance(t))
    headings["f"] = TITLE["f"].format(n=TOP_N)
    for letter in "abcdef":
        rows = headings[letter].split("\n")
        rows[0] = f"({letter}) {rows[0]}"
        fig.text(TITLE_X[letter], TITLE_TOP[letter], "\n".join(rows), fontsize=TITLE_PT,
                 fontweight="bold", ha="left", va="top", linespacing=1.15)
    return fig
