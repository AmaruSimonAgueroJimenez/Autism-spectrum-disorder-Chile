"""E42 — local clusters of administrative recognition: LISA and Getis–Ord Gi*, Chile.

Redraw of the stored plate `docs/study/corpus/figures/E42_lisa_gistar_maps.jpg`. The original was
drawn by `study/pipeline/` from the GRD and REM microdata, which this repository does not carry; all
six panels are rebuilt here from tracked tables plus the comuna cartography.

What the plate shows, unchanged. Every panel is about LOCAL indicators of the empirical-Bayes
SMOOTHED standardised ratio (`sir_eb`) of the F84 family EXCLUDING Rett syndrome (`sin_rett`), over
row-standardised QUEEN contiguity of the 342 continental comunas, with significance set by the
Benjamini–Hochberg threshold at q = 0.05 (critical p 0.0020 for GRD episodes and for A05, 0.0040 for GRD persons/year).
Panels (a)–(c) are categorical maps of that classification; panels (d)–(f) are COUNTS OF COMUNAS per
class, never rates and never events. Nothing here is weighted and nothing is re-standardised.

  (a) LISA quadrant of GRD episodes with documented F84, comuna of residence;
  (b) Getis–Ord Gi* of the same series — hot and cold spots;
  (c) LISA of REM A05 entries, which is place of CARE over a RESIDENCE denominator and so carries the
      compatibility warning ⚠;
  (d) comunas per significant class for the four local indicators, LISA and Gi* side by side, linear
      scale, with 'not significant' deliberately left out (it is in panel f);
  (e) region of the LISA-significant comunas of the main indicator, stacked by class;
  (f) the class key, the per-map counts including 'not significant', the ⚠ warning and the threshold.

Sources.

* `S3_grd_lisa_full2019_2024.csv` is the per-comuna result of the main indicator: one row for each of
  the 342 continental comunas, with `lisa_class`, `gi_class`, `region_name` and the metadata columns
  that pin the series down (indicator = grd_episodes, variant = sin_rett, value_type = sir_eb,
  weights = queen). It draws the maps of (a) and (b), the whole of (e), and the GRD F84 lines of (f);
  its class counts are HH 12, LL 6, LH 1, ns 323 and hot 13, cold 6, ns 323.
* `E42_local_class_counts.csv` is the plate's own companion table and holds the four indicator rows
  that panel (d) plots, with the 'not significant' column and the BH critical p that panel (f) cites.
* `E51_lisa_significant_comunas.csv` lists, with its CUT, every comuna that passes the threshold for
  each indicator. Panel (c) needs the A05 classification of all 342 comunas, and the caption states
  that every comuna not in the list is drawn 'not significant', never missing data: E51's fourteen
  A05 rows (10 High–High, 1 Low–Low, 3 Low–High) plus that rule reconstruct the map exactly, and the
  10/1/0/3/328 it yields is the A05 row of E42.
* `catalogo_comunas.csv` supplies the region of each comuna. Its `continental` flag is NOT read:
  the 342 comunas come from S3's own row set, and the islands drop out of the maps through the
  continental-box clip below.
  out of the graph and kept in the tables).

Cartography. Panels (a)–(c) are choropleths and cannot be drawn from a table: they need the comuna
polygons, and this module reads `data/comunas.shp`, the same file the hospital chapter of the report
already draws its commune maps from. That file is NOT tracked in this repository, so these three
panels only render where it is present; the three chart panels do not depend on it. The map recipe is
the pipeline's own: clip to the continental box (-76.5, -56.6, -66.0, -17.3), project to the
equal-area conic of the study (Albers, standard parallels 20 S and 52 S, central meridian 71 W),
simplify to 500 m, and draw the country in the three latitude bands the plate uses (north 15-1-2-3-4,
centre 5-13-6-7-16-8-9-14-10, south 11-12) at one common vertical scale, each band as wide as its own
geography needs. Comunas with no class — Cabo de Hornos, which survives the box but is not one of the
342 — are drawn in the plate's 'no value' grey, distinct from the 'not significant' grey.

The corpus is English only and so is this module: no language parameter, no Spanish variant.
"""
import textwrap

import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from figstyle import *

PLATE = "E42_lisa_gistar_maps"
SOURCES = [
    "docs/study/data/S3_grd_lisa_full2019_2024.csv",
    "docs/study/corpus/tables/E42_local_class_counts.csv",
    "docs/study/corpus/tables/E51_lisa_significant_comunas.csv",
    "output_files/consolidacion/catalogo_comunas.csv",
    "data/comunas.shp",
]
NOTE = ("Redraws the six panels of plate E42 — the LISA and Getis–Ord Gi* maps of the smoothed "
        "standardised ratio of GRD F84 episodes, the LISA map of REM A05 entries, the comunas per "
        "significant class of the four local indicators, the region of the LISA-significant comunas and "
        "the class key with the per-map counts — from the per-comuna S3 LISA file (sin_rett, sir_eb, "
        "queen, 342 continental comunas), the E42 class-count table and the E51 list of significant "
        "comunas, with the region taken from catalogo_comunas.csv; the three "
        "choropleths additionally read the comuna polygons of data/comunas.shp, which is not tracked in "
        "this repository and is the same cartography the hospital chapter uses.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIGSIZE = (180 / 25.4, 245 / 25.4)              # the plate canvas of the pipeline: 180 x 245 mm

S3 = BASE / "data" / "S3_grd_lisa_full2019_2024.csv"
COUNTS = BASE / "corpus" / "tables" / "E42_local_class_counts.csv"
E51 = BASE / "corpus" / "tables" / "E51_lisa_significant_comunas.csv"
CATALOGUE = ROOT / "output_files" / "consolidacion" / "catalogo_comunas.csv"
SHAPEFILE = ROOT / "data" / "comunas.shp"

#: Equal-area conic of the study; the pipeline measures every distance and area in it, never in
#: Web Mercator, and the maps are drawn in it so that a metre is a metre in both axes.
ALBERS = ("+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 +datum=WGS84 +units=m +no_defs")
CONTINENTAL_BOX = (-76.5, -56.6, -66.0, -17.3)  # the clip that drops the oceanic islands
SIMPLIFY = 500.0                                # metres; the plotting geometry of the pipeline
#: The three latitude bands of the plate, by region code: north, centre, south.
BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]
SPAN_PAD, WIDTH_PAD = 1.04, 1.06                # air around the tallest band and around each band
GAP = 1.2 / 180                                 # gap between two bands, as a fraction of the canvas

#: The plate's class palette. High-High and a Gi* hot spot share the red, Low-Low and a cold spot the
#: blue; the two off-diagonal LISA quadrants are the washed-out versions of the same two hues.
CLASS_COLOURS = {"HH": "#c0392b", "LL": "#2471a3", "LH": "#8bb8d8", "HL": "#e59a8f",
                 "hot": "#c0392b", "cold": "#2471a3", "ns": "#f2f2f2"}
CLASS_LABEL = {"HH": "High–High", "LL": "Low–Low", "LH": "Low–High", "HL": "High–Low",
               "hot": "Hot spot", "cold": "Cold spot", "ns": "Not significant"}
KEY_ORDER = ["HH", "LL", "HL", "LH", "hot", "cold", "ns"]        # the reading order of panel (f)
NO_VALUE = "#e9e9e9"                            # a comuna outside the 342: grey, but not the ns grey
MAP_EDGE, KEY_EDGE, BAR_EDGE = "#666666", "#666666", "#555555"

#: (class column, class code) in the bar order of panel (d): the four LISA quadrants, then Gi*.
SIG_CLASSES = [("lisa_class", "HH"), ("lisa_class", "LL"), ("lisa_class", "HL"), ("lisa_class", "LH"),
               ("gi_class", "hot"), ("gi_class", "cold")]
#: Column of E42_local_class_counts.csv that holds each of those six counts.
COUNT_COLUMN = {("lisa_class", "HH"): "LISA HH", ("lisa_class", "LL"): "LISA LL",
                ("lisa_class", "HL"): "LISA HL", ("lisa_class", "LH"): "LISA LH",
                ("gi_class", "hot"): "Gi* hot", ("gi_class", "cold"): "Gi* cold"}
PREFIX = {"lisa_class": "LISA", "gi_class": "Getis–Ord Gi*"}     # what panel (d)'s legend writes
LISA_ORDER = ["HH", "LL", "HL", "LH"]           # the stacking order of panel (e)
E51_CLASS = {"High–High": "HH", "Low–Low": "LL", "High–Low": "HL", "Low–High": "LH"}
WARN = " ⚠"                                     # the place-of-care mark of the A05 series
FDR_Q = 0.05                                    # the Benjamini–Hochberg level of every local test

#: Panel letter -> (indicator of the map, class column, heading). The heading is printed with the mark
#: in the panel title and without it in the key block of panel (f), exactly as the stored plate does.
MAPS = [("a", "GRD F84 episodes", "lisa_class", "LISA — GRD F84 episodes"),
        ("b", "GRD F84 episodes", "gi_class", "Getis–Ord Gi* — GRD F84 episodes"),
        ("c", "REM A05 entries" + WARN, "lisa_class", "LISA — REM A05 entries" + WARN)]

#: Boxes as fractions of the canvas, measured off the stored plate. A map cell is
#: (left, right, bottom, height) — the three bands are laid inside it — and a chart panel is the usual
#: (left, bottom, width, height).
MAP_CELL = {"a": (0.0171, 0.4859, 0.7100, 0.2459),
            "b": (0.5081, 0.9769, 0.7100, 0.2459),
            "c": (0.0171, 0.4859, 0.3543, 0.3229)}
BOX = {"d": (0.5790, 0.3909, 0.4050, 0.2777),
       "e": (0.1050, 0.0367, 0.4050, 0.2770),
       "f": (0.5780, 0.0367, 0.4050, 0.2748)}
#: Panel headings, with the line breaks the stored plate prints; the letter joins the first line.
TITLE = {"a": "LISA — GRD F84 episodes",
         "b": "Getis–Ord Gi* — GRD F84 episodes",
         "c": "LISA — REM A05 entries" + WARN,
         "d": "Comunas per significant class (BH q <\n0.05); 'not significant' is not drawn",
         "e": "Region of the LISA-significant comunas\n(GRD)",
         "f": "Class key and counts"}
TITLE_X = {"a": 0.011, "c": 0.011, "e": 0.011, "b": 0.5365, "d": 0.5365, "f": 0.5365}
TITLE_TOP = {"a": 0.9824, "b": 0.9824, "c": 0.7047, "d": 0.6988, "e": 0.3446, "f": 0.3306}

TITLE_PT, LABEL_PT, TICK_PT, SMALL_PT = 9.0, 8.0, 7.0, 6.0
KEY_PT, KEY_TITLE_PT, BLOCK_PT, AXIS_TICK_PT = 6.6, 6.8, 6.4, 6.4
KEY_GAP, BLOCK_GAP = 0.045, 0.035               # air under the key legend and between text blocks
WRAP_KEY, WRAP_TICK, ABBREV = 52, 12, 18        # the plate's wrap columns and its y-label cut
WARNING_TEXT = "⚠ Place of CARE over a RESIDENCE denominator"
THRESHOLD_TEXT = ("Only comunas passing the Benjamini–Hochberg threshold "
                  f"(q = {FDR_Q}) are coloured; the rest are 'not significant', never missing data.")
BODY_COLOUR, WARN_COLOUR, FOOT_COLOUR = "#333333", "#8b0000", "#555555"


def _wrap(text, width=WRAP_KEY):
    """The plate's line breaking: plain character wrapping, one paragraph at a time."""
    return "\n".join(textwrap.wrap(str(text), width))


def _abbrev(text, n=ABBREV):
    """A y-axis label cut to the width of the half-page panel, with the cut marked."""
    t = str(text)
    return t if len(t) <= n else t[: n - 1] + "…"


def local_classes():
    """The per-comuna LISA and Gi* classes of the main indicator, indexed by CUT.

    S3 is the analysis file itself: 342 rows, one per continental comuna, of the series the plate
    draws (grd_episodes, sin_rett, sir_eb, queen). Nothing is recomputed here.
    """
    t = pd.read_csv(S3)
    t["cut_comuna"] = t.cut_comuna.astype(int)
    return t.set_index("cut_comuna")


def a05_classes(continental):
    """The A05 LISA class of every one of the 342 comunas, for panel (c).

    E51 lists only the comunas that pass the Benjamini–Hochberg threshold; the caption says the rest
    are 'not significant', never missing data, so the full map is that list over a background of ns.
    """
    t = pd.read_csv(E51, encoding="utf-8-sig")
    sig = t[t.Indicator.str.startswith("REM A05")]
    out = pd.Series("ns", index=pd.Index(sorted(continental), name="cut_comuna"))
    out.loc[sig.CUT.astype(int).to_numpy()] = [E51_CLASS[c] for c in sig.LISA]
    return out


def class_counts():
    """The four indicator rows of the E42 companion table, parsed to integers."""
    t = pd.read_csv(COUNTS, encoding="utf-8-sig")
    cols = [c for c in t.columns if c != "Indicator" and "critical" not in c]
    return t.assign(**{c: t[c].astype(int) for c in cols}).set_index("Indicator")


def comunas():
    """The comuna polygons of the plate, in the pipeline's own plotting geometry.

    `data/comunas.shp` is not tracked in this repository; it is the cartography the hospital chapter
    of the report already uses. Clipped to the continental box, projected to the equal-area conic and
    simplified to 500 m, exactly as `15b_spatial_correlation.load_geography` prepares its `plot` frame.
    """
    import geopandas as gpd
    from shapely.geometry import box
    if not SHAPEFILE.exists():
        raise FileNotFoundError(
            f"{SHAPEFILE} is missing: panels (a)-(c) of {PLATE} are choropleths and need the comuna "
            "cartography, which this repository does not track.")
    g = gpd.read_file(SHAPEFILE)
    g = g.loc[g.cod_comuna > 0, ["cod_comuna", "geometry"]].rename(columns={"cod_comuna": "cut_comuna"})
    g["cut_comuna"] = g.cut_comuna.astype(int)
    g = g.to_crs(4326)
    g["geometry"] = g.geometry.make_valid()
    g["geometry"] = g.geometry.intersection(box(*CONTINENTAL_BOX))
    g = g[~g.geometry.is_empty].copy().to_crs(ALBERS)
    g["geometry"] = g.geometry.simplify(SIMPLIFY)
    catalogue = pd.read_csv(CATALOGUE, encoding="utf-8-sig")
    g["cut_region"] = g.cut_comuna.map(dict(zip(catalogue.cut_comuna, catalogue.cut_region)))
    return g


def _map(fig, cell, shapes, classes):
    """One categorical map of the plate: the country in three bands at one common vertical scale.

    Every band is drawn at the same metres-per-inch, so the three strips are comparable; each band is
    then given the width its own geography needs rather than a fixed third of the cell, which is what
    keeps the narrow north and centre from floating in an empty rectangle. If the three together do
    not fit across the cell, the whole map — bands and height alike — is scaled down.
    """
    x0, x1, bottom, height = cell
    bands = [shapes[shapes.cut_region.isin(b)] for b in BANDS]
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
    for band, bound, width in zip(bands, bounds, widths):
        ax = fig.add_axes([x, bottom, width, height])
        colours = [CLASS_COLOURS.get(c, NO_VALUE) for c in classes.reindex(band.cut_comuna)]
        band.plot(color=colours, edgecolor=MAP_EDGE, linewidth=0.18, ax=ax)
        ax.set_aspect("auto")
        ax.set_axis_off()
        cy = (bound[1] + bound[3]) / 2
        cx = (bound[0] + bound[2]) / 2
        ax.set_ylim(cy - span / 2, cy + span / 2)
        window = span * (width * w_in) / (height * h_in)  # a metre is a metre in both axes
        ax.set_xlim(cx - window / 2, cx + window / 2)
        x += width + GAP


def _panel_d(fig, counts):
    """Comunas per significant class, four indicators, LISA and Gi* side by side, linear scale."""
    ax = fig.add_axes(BOX["d"])
    indicators = list(counts.index)
    width = 0.82 / len(SIG_CLASSES)
    x = np.arange(len(indicators))
    for k, key in enumerate(SIG_CLASSES):
        values = counts[COUNT_COLUMN[key]].to_numpy(int)
        ax.bar(x + k * width, values, width=width, color=CLASS_COLOURS[key[1]], edgecolor=BAR_EDGE,
               linewidth=0.3, label=f"{PREFIX[key[0]]} {CLASS_LABEL[key[1]]}")
        for xi, v in zip(x + k * width, values):
            if v:
                ax.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=SMALL_PT)
    ax.set_xticks(x + 0.41 - width / 2)
    ax.set_xticklabels([_wrap(i.replace(WARN, ""), WRAP_TICK) for i in indicators],
                       fontsize=AXIS_TICK_PT)
    ax.set_ylabel("Comunas", fontsize=LABEL_PT)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.42)              # a free band for the six-class legend
    ax.tick_params(labelsize=TICK_PT)
    ax.tick_params(axis="x", labelsize=AXIS_TICK_PT)
    clean(ax, grid="both")
    ax.legend(fontsize=SMALL_PT, ncol=2, loc="upper right", frameon=True, framealpha=0.95,
              facecolor="white", edgecolor="none", borderpad=0.25)


def _panel_e(fig, local):
    """Region of the LISA-significant comunas of the main indicator, stacked by class."""
    ax = fig.add_axes(BOX["e"])
    significant = local[local.lisa_class != "ns"]
    table = significant.groupby(["region_name", "lisa_class"]).size().unstack(fill_value=0)
    y = np.arange(len(table))
    left = np.zeros(len(table))
    for cl in [c for c in LISA_ORDER if c in table.columns]:
        ax.barh(y, table[cl].to_numpy(), left=left, color=CLASS_COLOURS[cl], label=CLASS_LABEL[cl],
                edgecolor=BAR_EDGE, linewidth=0.3)
        left = left + table[cl].to_numpy()
    ax.set_yticks(y)
    ax.set_yticklabels([_abbrev(i) for i in table.index], fontsize=AXIS_TICK_PT)
    ax.set_xlim(0, float(left.max()) * 1.55)             # a free band on the right for the legend
    ax.set_xlabel("Comunas", fontsize=LABEL_PT)
    ax.tick_params(axis="x", labelsize=TICK_PT)
    clean(ax, grid="both")
    ax.legend(fontsize=SMALL_PT, loc="lower right", frameon=True, framealpha=0.95,
              facecolor="white", edgecolor="none", borderpad=0.25)


def _panel_f(fig, drawn, counts):
    """The class key, the counts of each map including 'not significant', the ⚠ and the threshold.

    The text blocks are placed under the key legend as the plate places them: the legend is measured
    once it is drawn and each block is measured in turn, so a longer block simply pushes the next one
    down instead of landing on top of it.
    """
    ax = fig.add_axes(BOX["f"])
    ax.set_axis_off()
    handles = [Patch(facecolor=CLASS_COLOURS[k], edgecolor=KEY_EDGE, label=CLASS_LABEL[k])
               for k in KEY_ORDER]
    key = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=2,
                    fontsize=KEY_PT, frameon=False, title="Local class", title_fontsize=KEY_TITLE_PT,
                    alignment="left")
    rows = []
    for letter, indicator, column, heading in MAPS:
        present = drawn[(letter, column)].value_counts()
        parts = ", ".join(f"{CLASS_LABEL[k]} {present[k]:,}" for k in KEY_ORDER if k in present.index)
        rows.append(f"({letter}) {heading.replace(WARN, '')}: {parts}")
        # The counts printed in the key are the ones the maps actually draw. For the LISA panel they
        # are also a published column of E42, so they can be checked; the Gi* panel has no matching
        # "not significant" column in that table, so there is nothing to check it against.
        if column == "lisa_class":
            published_ns = int(counts.loc[indicator, "LISA not significant"])
            drawn_ns = int(present.get("ns", 0))
            if drawn_ns != published_ns:
                raise AssertionError(
                    f"{indicator}: the map draws {drawn_ns} communes as not significant but E42 "
                    f"publishes {published_ns}")
    blocks = [("\n".join(_wrap(r) for r in rows), BODY_COLOUR, BLOCK_PT),
              (_wrap(WARNING_TEXT), WARN_COLOUR, BLOCK_PT),
              (_wrap(THRESHOLD_TEXT), FOOT_COLOUR, BLOCK_PT)]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = ax.get_window_extent()
    y = (key.get_window_extent(renderer).y0 - box.y0) / box.height - KEY_GAP
    for text, colour, size in blocks:
        t = ax.text(0.0, y, text, transform=ax.transAxes, fontsize=size, va="top", ha="left",
                    linespacing=1.35, color=colour)
        fig.canvas.draw()
        y -= t.get_window_extent(fig.canvas.get_renderer()).height / box.height + BLOCK_GAP


def draw():
    style()
    plt.rcParams.update({"axes.edgecolor": "#333333", "axes.linewidth": 0.7,
                         "xtick.major.size": 2.4, "ytick.major.size": 2.4,
                         "xtick.major.pad": 1.8, "ytick.major.pad": 1.8, "axes.labelpad": 2.2})
    local = local_classes()
    counts = class_counts()
    shapes = comunas()
    a05 = a05_classes(local.index)

    # The class series each map draws, keyed by (panel letter, class column).
    drawn = {("a", "lisa_class"): local.lisa_class,
             ("b", "gi_class"): local.gi_class,
             ("c", "lisa_class"): a05}

    fig = plt.figure(figsize=FIGSIZE)
    for letter, indicator, column, heading in MAPS:
        _map(fig, MAP_CELL[letter], shapes, drawn[(letter, column)])
    _panel_d(fig, counts)
    _panel_e(fig, local)
    _panel_f(fig, drawn, counts)

    for letter in "abcdef":
        rows = TITLE[letter].split("\n")
        rows[0] = f"({letter}) {rows[0]}"
        fig.text(TITLE_X[letter], TITLE_TOP[letter], "\n".join(rows), fontsize=TITLE_PT,
                 fontweight="bold", ha="left", va="top", linespacing=1.2)
    return fig
