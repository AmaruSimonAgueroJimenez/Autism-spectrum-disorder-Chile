"""E49 — the regional summary: smoothed ratios, crude rates with intervals, Moran's I and the
ecological comparison of the two sources.

Redraw of the stored plate `docs/study/corpus/figures/E49_regional_summary.jpg`. The original was
drawn by `study/pipeline/` from the GRD and REM microdata aggregated to the sixteen regions, which
this repository does not carry; all six panels are rebuilt here from tracked tables plus the regional
cartography.

What the plate shows, unchanged. Three different estimators sit side by side and the plate labels
each one where it is used, so they are kept apart here too:

  (a) EMPIRICAL-BAYES SMOOTHED standardised ratio of GRD episodes with documented F84, by region of
      residence — internal indirect standardisation, so the national ratio is 1 by construction;
  (b) the same smoothed ratio for REM A05 entries, which is place of CARE over a RESIDENCE
      denominator and therefore carries the compatibility mark ⚠;
  (c) CRUDE rate per 100,000 person-years of the GRD series, 2019–2024, with its exact Poisson 95%
      interval and the observed count in brackets after the region's name;
  (d) the same for REM A05 entries, 2021–2025, again marked ⚠;
  (e) global Moran's I at the REGIONAL scale — sixteen units, which is the scale the caption itself
      warns has little power; the bars print the permutation p, never a verdict;
  (f) the two sources against each other on log axes with Spearman's rho and its interval. No ratio
      between the two sources is computed, here or anywhere on the plate.

Nothing is weighted, nothing is re-standardised, and the counts are administrative recognition, never
prevalence or incidence.

Sources.

* `E49_regional_summary.csv` is the plate's own companion table: 64 rows, one for each of the sixteen
  regions and each of four indicators (GRD F84 episodes, GRD persons/year, REM A05 entries ⚠, REM P2
  December ⚠), carrying the observed count, the expected count of the indirect standardisation, the
  crude rate with its Poisson limits, the crude standardised ratio with limits, and the
  empirical-Bayes smoothed ratio, each in its own named column. Two of those four indicators are
  drawn: panels (a) and (c) are GRD F84 episodes, panels (b) and (d) REM A05 entries. Every cell is a
  formatted string — `"1,456"`, `"25.5 (23.5–27.6)"` — and is parsed, never retyped.
* `E50_moran_gistar_all.csv` holds the global Moran's I of every indicator at every scale. Panel (e)
  is the `Scale == "Region"` block: fourteen indicators, each taking its EMPIRICAL-BAYES row where the
  indicator has one and its `Observed value` row where it does not (the four context layers — SAE
  multidimensional, SAE income, Urban %, FONASA/INE % — are levels, not counts, so they have no
  standardised ratio), sorted from the largest I down. The p printed on each bar is the permutation p,
  not the analytic one.
* `output_files/consolidacion/population_regional.csv` is the INE base-2017 projection by region, sex
  and five-year age group. Summed over sex and age across 2019–2024 it is the person-year denominator
  of the GRD series, and dividing the observed counts of E49 by it reproduces all sixteen published
  GRD rates to the decimal the table prints — the check this module runs before it uses them. It is
  needed for one reason: the published rate is rounded to ONE DECIMAL and Metropolitana and Los Ríos
  both print 16.4, a tie that panel (f) has to break. At full precision Metropolitana is 16.378 and
  Los Ríos 16.445, and the stored plate draws them in exactly that order — its Los Ríos marker sits
  1.1 px above its Metropolitana one. Broken that way, Spearman's rho is 0.6324 and its interval
  0.18–0.86, which is what the plate prints; left tied it is 0.6269 with an interval of 0.17–0.86 and
  the printed title would be wrong. The A05 rates have no tie, and their 2021–2025 denominator has no
  tracked 2025 projection, so panel (f) takes the published A05 rate for its x coordinate.

The interval on rho is the Fisher z transform with the SPEARMAN correction to the variance,
se² = 1.06/(n − 3) — the same form the E44 plate needed. The plain 1/√(n − 3) form misses the printed
lower bound (0.20 against the plate's 0.18).

Cartography. Panels (a) and (b) are choropleths and cannot be drawn from a table: they need the
regional polygons, and this module reads `data/Regional.shp`, the same file the hospital chapter of
the report already draws its maps from. That file is NOT tracked in this repository, so these two
panels only render where it is present; the four chart panels do not depend on it. The map recipe is
the pipeline's own: clip to the continental box (-76.5, -56.6, -66.0, -17.3) so that the oceanic
islands do not set the frame, project to the equal-area conic of the study (Albers, standard
parallels 20 S and 52 S, central meridian 71 W), simplify at 800 m, and draw the country in the three
latitude bands the plate uses (north 15-1-2-3-4, centre 5-13-6-7-16-8-9-14-10, south 11-12) at one
common scale, each band as wide as its own geography needs.

The colour scale of both maps was read off the stored plate: a diverging RdBu_r centred on the
national ratio of 1, running up to the 98th percentile of the sixteen values and down to its mirror
image below 1, floored at zero. That is 0.128–1.872 for the GRD map, whose colour bar the plate ticks
from 0.2 to 1.8, and 0–2.637 for the A05 map, ticked 0.0 to 2.5; Ñuble tops both and is drawn at the
end of the bar in each.

The corpus is English only and so is this module: no language parameter, no Spanish variant.
"""
import math

import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import LogFormatter
from scipy import stats
from figstyle import *

PLATE = "E49_regional_summary"
SOURCES = [
    "docs/study/corpus/tables/E49_regional_summary.csv",
    "docs/study/corpus/tables/E50_moran_gistar_all.csv",
    "output_files/consolidacion/population_regional.csv",
    "data/Regional.shp",
]
NOTE = ("Redraws the six panels of plate E49 — the two empirical-Bayes smoothed-ratio maps of the "
        "sixteen regions, the two crude regional rates per 100,000 person-years with their exact "
        "Poisson intervals and observed counts, the fourteen-indicator Moran's I bar chart at the "
        "regional scale and the log-log comparison of GRD against REM A05 with Spearman's rho — from "
        "the E49 companion table and the Region block of E50, with the INE regional person-years of "
        "output_files/consolidacion/population_regional.csv used to recover the GRD rates at full "
        "precision so that the Metropolitana/Los Ríos tie at 16.4 breaks the way panel (f) needs; the "
        "two choropleths additionally read the regional polygons of data/Regional.shp, which is not "
        "tracked in this repository and is the same cartography the hospital chapter uses.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repo root
FIGSIZE = (180 / 25.4, 245 / 25.4)              # the plate canvas of the pipeline: 180 x 245 mm

E49 = BASE / "corpus" / "tables" / "E49_regional_summary.csv"
E50 = BASE / "corpus" / "tables" / "E50_moran_gistar_all.csv"
POPULATION = ROOT / "output_files" / "consolidacion" / "population_regional.csv"
SHAPEFILE = ROOT / "data" / "Regional.shp"

#: The two indicators of E49 the plate draws, exactly as its Indicator column spells them. The mark
#: is part of the stored name of the A05 series and travels with it into the panel titles.
WARN = " ⚠"
GRD = "GRD F84 episodes"
A05 = "REM A05 entries" + WARN

#: CUT code -> region name as E49 spells it, and the north -> south order of panels (c), (d) and (f).
REGION_NAMES = {15: "Arica y Parinacota", 1: "Tarapacá", 2: "Antofagasta", 3: "Atacama",
                4: "Coquimbo", 5: "Valparaíso", 13: "Metropolitana", 6: "O'Higgins", 7: "Maule",
                16: "Ñuble", 8: "Biobío", 9: "La Araucanía", 14: "Los Ríos", 10: "Los Lagos",
                11: "Aysén", 12: "Magallanes"}
REGION_ORDER = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]
GRD_YEARS = range(2019, 2025)                   # the GRD coverage of the plate, 2019-2024

#: Equal-area conic of the study; the pipeline measures every distance in it, never in Web Mercator.
ALBERS = "+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 +datum=WGS84 +units=m +no_defs"
CONTINENTAL_BOX = (-76.5, -56.6, -66.0, -17.3)  # the clip that drops the oceanic islands
SIMPLIFY = 800.0                                # metres; the plotting geometry of the pipeline
BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]
SPAN_PAD = 1.04                                 # air above and below the tallest band
BAND_GAP = 0.010                                # gap between two bands, as a fraction of the canvas
UPPER_Q = 0.98                                  # where the colour scale of a map stops, see module doc
MAP_CMAP = "RdBu_r"
MAP_EDGE, MAP_EDGE_LW = "#666666", 0.25
NO_VALUE = "#f2f2f2"

#: Boxes measured off the stored plate, as fractions of the canvas. A map cell is
#: (left, right, bottom, height) with the three bands laid inside it, its colour bar is
#: (left, bottom, width, height), and a chart panel is the usual (left, bottom, width, height).
MAP_CELL = {"a": (0.0440, 0.4580, 0.7716, 0.1673),
            "b": (0.5350, 0.9490, 0.7720, 0.1826)}
CBAR = {"a": (0.0440, 0.7605, 0.4140, 0.0074),
        "b": (0.5350, 0.7605, 0.4140, 0.0074)}
BOX = {"c": (0.1920, 0.3960, 0.2860, 0.2748),
       "d": (0.6980, 0.3960, 0.2860, 0.2748),
       "e": (0.1920, 0.0404, 0.2860, 0.2748),
       "f": (0.6980, 0.0404, 0.2860, 0.2748)}
TITLE_X = {"a": 0.0110, "c": 0.0110, "e": 0.0110, "b": 0.5045, "d": 0.5045, "f": 0.5045}
TITLE_TOP = {"a": 0.9827, "b": 0.9835, "c": 0.7021, "d": 0.7021, "e": 0.3317, "f": 0.3464}

TITLE_PT, LABEL_PT, TICK_PT = 9.0, 8.0, 7.0
P_PT, POINT_PT, WARN_PT = 6.3, 6.7, 6.0         # p labels, the region labels of (f), the red note
TITLE_W_PT = (180 / 25.4 * 72.0) / 2 - (4.0 / 25.4 * 72.0)      # half the canvas less a 4 mm margin
TITLE_LINESPACING = 1.12
MARKER_PT = 5.1                                 # the dot of (c) and (d), in points of diameter
SCATTER_PT = 5.2                                # the dot of (f)
BAR_HEIGHT = 0.72                               # the bar of (e), in category units
MORAN_HEADROOM = 1.311                          # the room panel (e) leaves on the right for its p
P_GAP = 0.020                                   # the air between a bar and its p, in units of I
WARN_COLOUR = "#8b0000"
LEADER_COLOUR = "#999999"

#: The panel headings, as the stored plate prints them. The two map titles are not built from one
#: template: (a) names the scale and (b) ends on the compatibility mark instead, and that asymmetry
#: is the plate's own. The (f) heading is composed in `draw` from the numbers it reports.
TITLE = {"a": f"{GRD} — Smoothed ratio (EB) (Region)",
         "b": f"REM A05 entries — Smoothed ratio (EB){WARN}",
         "c": "Regional rate of GRD episodes with F84, 2019–2024 (observed)",
         "d": f"Regional rate of A05 entries, 2021–2025{WARN} place of care",
         "e": "Moran's I at the regional scale"}
CBAR_LABEL = "Smoothed ratio (EB)"
RATE_LABEL = "Rate per 100,000 population (95% CI)"
WARNING_TEXT = "⚠ Place of CARE over a RESIDENCE denominator"

#: Panel (e) takes the empirical-Bayes row of every indicator that has one and the observed-value row
#: of the four context layers that do not; nothing else in the Region block is drawn.
MORAN_VALUE_TYPES = ["Empirical-Bayes smoothed standardised ratio", "Observed value"]


# --------------------------------------------------------------------------- reading the tables
def _num(s):
    """One formatted number -> float; an empty or not-estimable cell -> nan."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-", "< 5"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-").replace("<", "").strip())


def _point(s):
    """'25.5 (23.5–27.6)' -> 25.5 — the estimate, without its interval."""
    return _num(str(s).split("(")[0])


def _limits(s):
    """'25.5 (23.5–27.6)' -> (23.5, 27.6) — the two limits the table publishes."""
    inside = str(s).split("(")[1].rstrip(")")
    lo, hi = inside.replace("–", "|").replace("—", "|").replace(" to ", "|").split("|")
    return _num(lo), _num(hi)


def regional_summary():
    """E49 by (indicator, region): observed, expected, the crude rate with limits and the EB ratio."""
    t = pd.read_csv(E49, encoding="utf-8-sig", dtype=str)
    t.columns = [c.strip() for c in t.columns]
    rate = t["Rate per 100,000 population"]
    out = pd.DataFrame({
        "indicator": t.Indicator.str.strip(),
        "region": t.Region.str.strip(),
        "observed": t.Observed.map(_num),
        "expected": t["Expected counts (indirect standardisation)"].map(_num),
        "rate": rate.map(_point),
        "rate_lo": [_limits(v)[0] for v in rate],
        "rate_hi": [_limits(v)[1] for v in rate],
        "ratio": t["Crude standardised ratio"].map(_point),
        "eb": t["Empirical-Bayes smoothed standardised ratio"].map(_num),
    }).set_index(["indicator", "region"])
    assert len(out) == 64, f"E49 should carry 16 regions x 4 indicators, not {len(out)} rows"
    return out


def indicator_frame(summary, indicator):
    """One indicator of E49, in the north -> south order the plate prints."""
    frame = summary.loc[indicator].reindex([REGION_NAMES[c] for c in REGION_ORDER])
    assert frame.notna().all().all(), f"{indicator}: a region of the plate is missing from E49"
    return frame


def person_years():
    """The INE base-2017 person-years of each region over 2019-2024, summed over sex and age."""
    pop = pd.read_csv(POPULATION)
    by_year = pop.groupby(["year", "cut_region"]).population.sum().unstack()
    missing = [y for y in GRD_YEARS if y not in by_year.index]
    assert not missing, f"population_regional.csv has no projection for {missing}"
    return by_year.loc[list(GRD_YEARS)].sum()


def grd_rate_full_precision(grd):
    """The GRD rate of each region without the table's rounding, and the check that it is the same one.

    E49 publishes the rate to one decimal, which makes Metropolitana and Los Ríos both 16.4. Panel (f)
    ranks the regions, so that tie has to be broken, and the only tracked thing that breaks it is the
    denominator: the observed count of E49 over the INE person-years of the region. The recomputed
    value must round to the published one for all sixteen regions, or these are not the same rates and
    nothing here may be drawn."""
    py = person_years()
    rate = pd.Series({REGION_NAMES[c]: grd.observed[REGION_NAMES[c]] / py[c] * 1e5
                      for c in REGION_ORDER}).reindex(grd.index)
    assert np.allclose(rate.round(1), grd.rate), \
        "the E49 counts over the INE person-years do not reproduce the published GRD rates"
    assert rate["Metropolitana"] < rate["Los Ríos"], \
        "the 16.4 tie must break with Metropolitana below Los Ríos, as the stored plate draws it"
    return rate


def moran_regional():
    """The fourteen bars of panel (e): Moran's I at the regional scale, largest first."""
    t = pd.read_csv(E50, encoding="utf-8-sig", dtype=str)
    t.columns = [c.strip() for c in t.columns]
    t = t[(t.Scale.str.strip() == "Region") & t["Value type"].str.strip().isin(MORAN_VALUE_TYPES)]
    t = t.assign(indicator=t.Indicator.str.strip(), moran=t["Moran's I"].map(_num),
                 p=t["p (999 perm.)"].map(_num), n=t.n.map(_num))
    assert t.indicator.is_unique, "an indicator has both an EB and an observed-value row at Region"
    assert len(t) == 14, f"panel (e) has fourteen bars, not {len(t)}"
    assert (t.n == 16).all(), "the regional scale has sixteen units"
    return t.sort_values("moran", ascending=False)[["indicator", "moran", "p"]].reset_index(drop=True)


def regions_shapefile():
    """The regional polygons of the plate, in the pipeline's own plotting geometry.

    `data/Regional.shp` is not tracked in this repository; it is the cartography the hospital chapter
    of the report already uses. Clipped to the continental box, projected to the equal-area conic and
    simplified, exactly as `load_regions_equal_area` prepares it in the pipeline."""
    import warnings
    import geopandas as gpd
    from shapely.geometry import box
    if not SHAPEFILE.exists():
        raise FileNotFoundError(
            f"{SHAPEFILE} is missing: panels (a) and (b) of {PLATE} are choropleths and need the "
            "regional cartography, which this repository does not track.")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = gpd.read_file(SHAPEFILE)
    g = g.loc[g.codregion.astype(int) > 0, ["codregion", "geometry"]].rename(
        columns={"codregion": "cut_region"})
    g["cut_region"] = g.cut_region.astype(int)
    g = g.to_crs(4326)
    try:
        g["geometry"] = g.geometry.make_valid()
    except AttributeError:                                  # older shapely
        g["geometry"] = g.geometry.buffer(0)
    g["geometry"] = g.geometry.intersection(box(*CONTINENTAL_BOX))
    g = g[~g.geometry.is_empty].copy().to_crs(ALBERS)
    g["geometry"] = g.geometry.simplify(SIMPLIFY)
    assert set(g.cut_region) == set(REGION_ORDER), "the shapefile does not carry the sixteen regions"
    return g


# --------------------------------------------------------------------------- panel furniture
def _wrap(text, width_pt=TITLE_W_PT, size=TITLE_PT, weight="bold"):
    """Fold a heading at a MEASURED width, as the plate engine does — not at a character count."""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    prop = FontProperties(family=plt.rcParams["font.family"], size=size, weight=weight)
    lines, line = [], ""
    for word in str(text).split():
        trial = f"{line} {word}".strip()
        if line and TextPath((0, 0), trial, prop=prop, usetex=False).get_extents().width > width_pt:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    return "\n".join(lines)


def _map(fig, cell, cbar_box, shapes, values, label=CBAR_LABEL):
    """One choropleth of the plate: the country in three bands at one common scale, under one bar.

    Every band is drawn at the same metres-per-inch, so the three strips are comparable; each band is
    then given the width its own geography needs rather than a fixed third of the cell, which is what
    keeps the narrow north and centre from floating in an empty rectangle. The scale is diverging
    around the national ratio of 1 and stops at the 98th percentile of the sixteen values, mirrored
    below 1 and floored at zero — the limits measured off the stored plate."""
    x0, x1, bottom, height = cell
    series = pd.Series({c: float(values[REGION_NAMES[c]]) for c in REGION_ORDER})
    upper = float(np.quantile(series.to_numpy(), UPPER_Q))
    norm = TwoSlopeNorm(vmin=max(0.0, 2.0 - upper), vcenter=1.0, vmax=upper)
    mapper = ScalarMappable(norm=norm, cmap=MAP_CMAP)

    bands = [shapes[shapes.cut_region.isin(b)] for b in BANDS]
    bounds = [b.total_bounds for b in bands]
    span = max(b[3] - b[1] for b in bounds) * SPAN_PAD
    w_in, h_in = fig.get_size_inches()
    scale = (height * h_in) / span                          # inches per metre, shared by the bands
    widths = [(b[2] - b[0]) * scale / w_in for b in bounds]
    x = x0 + max(0.0, (x1 - x0 - sum(widths) - (len(bands) - 1) * BAND_GAP)) / 2
    for band, bound, width in zip(bands, bounds, widths):
        ax = fig.add_axes([x, bottom, width, height])
        colours = [mapper.to_rgba(v) if np.isfinite(v) else NO_VALUE
                   for v in series.reindex(band.cut_region.to_numpy())]
        band.plot(color=colours, edgecolor=MAP_EDGE, linewidth=MAP_EDGE_LW, ax=ax)
        ax.set_aspect("auto")
        ax.set_axis_off()
        cy, cx = (bound[1] + bound[3]) / 2, (bound[0] + bound[2]) / 2
        ax.set_ylim(cy - span / 2, cy + span / 2)
        window = span * (width * w_in) / (height * h_in)    # a metre is a metre in both axes
        ax.set_xlim(cx - window / 2, cx + window / 2)
        x += width + BAND_GAP

    cax = fig.add_axes(cbar_box)
    bar = fig.colorbar(mapper, cax=cax, orientation="horizontal")
    bar.set_label(label, fontsize=TICK_PT)
    bar.ax.tick_params(labelsize=TICK_PT, length=2.4, pad=1.8)
    bar.outline.set_linewidth(0.0)
    return norm


def _rate_panel(fig, box, frame, colour):
    """Panel (c) or (d): the crude regional rate with its exact Poisson interval, north to south.

    The region's observed count goes in its own axis label, in brackets after the name, which is where
    the stored plate puts it; the interval is the one E49 publishes, never a recomputed one."""
    ax = fig.add_axes(box)
    y = np.arange(len(frame))
    rate = frame.rate.to_numpy(float)
    error = np.vstack([rate - frame.rate_lo.to_numpy(float), frame.rate_hi.to_numpy(float) - rate])
    ax.errorbar(rate, y, xerr=error, fmt="o", color=colour, markersize=MARKER_PT, elinewidth=1.1,
                capsize=0.0, linestyle="none", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r} ({num(c, 'en')})" for r, c in zip(frame.index, frame.observed)],
                       fontsize=TICK_PT)
    ax.invert_yaxis()
    ax.set_xlabel(RATE_LABEL, fontsize=LABEL_PT)
    ax.tick_params(axis="x", labelsize=TICK_PT)
    clean(ax, grid="both")
    return ax


def _moran_panel(fig, box, table):
    """Panel (e): global Moran's I of fourteen indicators at the regional scale, largest first."""
    ax = fig.add_axes(box)
    y = np.arange(len(table))
    moran = table.moran.to_numpy(float)
    ax.barh(y, moran, height=BAR_HEIGHT, color=BLUE, linewidth=0.0, zorder=3)
    for yi, value, p in zip(y, moran, table.p.to_numpy(float)):
        ax.text(value + P_GAP, yi, f"p = {p:.3f}", va="center", ha="left", fontsize=P_PT, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(table.indicator, fontsize=TICK_PT)
    ax.invert_yaxis()
    ax.set_xlim(0.0, float(moran.max()) * MORAN_HEADROOM)
    ax.set_xlabel("Moran's I (Region, n = 16)", fontsize=LABEL_PT)
    ax.tick_params(axis="x", labelsize=TICK_PT)
    clean(ax, grid="x")
    return ax


def _scatter_panel(fig, box, a05, grd, labels):
    """Panel (f): the two sources against each other on log axes, one marker per region.

    The axes carry matplotlib's own log ticking, so only the ticks it chooses to label are labelled —
    40, 60 and 100 across, 20, 30 and 40 up — and the single major tick at 100 is the only grid line
    the panel draws, which is what the stored plate shows."""
    ax = fig.add_axes(box)
    ax.scatter(a05, grd, s=SCATTER_PT ** 2, color=GREEN, linewidth=0.0, zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(LogFormatter())
        axis.set_minor_formatter(LogFormatter())
    ax.margins(0.16)                                # the air the stored plate leaves for its labels
    ax.set_xlabel("REM A05 entries — Rate per 100,000", fontsize=LABEL_PT)
    # The vertical label is folded where the stored plate folds it: upright it is as long as the panel
    # is tall, and the plate breaks it after 'per' rather than let it run past the axes.
    ax.set_ylabel("GRD F84 episodes — Rate per\n100,000", fontsize=LABEL_PT, linespacing=1.3)
    ax.tick_params(labelsize=TICK_PT)
    ax.tick_params(axis="both", which="minor", labelsize=TICK_PT)
    clean(ax, grid="both")
    # The note is anchored to the bottom RIGHT of the panel, where the stored plate puts it, and its
    # two lines are left-aligned inside that block; the bottom left corner is left free for the region
    # name that lands there.
    warning = ax.text(0.965, 0.022, _wrap(WARNING_TEXT, width_pt=0.78 * box[2] * FIGSIZE[0] * 72.0,
                                          size=WARN_PT, weight="normal"),
                      transform=ax.transAxes, fontsize=WARN_PT, ha="right", va="bottom",
                      multialignment="left", color=WARN_COLOUR, linespacing=1.3, zorder=6)
    return ax, warning


def _overlap(a, b):
    """Area shared by two pixel boxes — zero when they do not touch."""
    return (max(min(a[2], b[2]) - max(a[0], b[0]), 0.0)
            * max(min(a[3], b[3]) - max(a[1], b[1]), 0.0))


def _outside(box, frame):
    """How far a label sticks out of its axes, in pixels; zero when it is wholly inside."""
    return (max(frame.x0 - box[0], 0.0) + max(box[2] - frame.x1, 0.0)
            + max(frame.y0 - box[1], 0.0) + max(box[3] - frame.y1, 0.0))


def place_point_labels(fig, ax, xs, ys, labels, obstacles=(), fontsize=POINT_PT):
    """Sixteen region names around sixteen markers, placed by MEASUREMENT, with a leader when far.

    The stored plate places them at save time, with the composition already frozen: it tries a ring of
    directions and distances around each marker and rejects any placement that covers a marker, another
    label or the note. The same rule is applied here, from the topmost point down, so that the most
    crowded corner is settled last against what is already on the page."""
    renderer = fig.canvas.get_renderer()
    marker_boxes = [(px - 4.0, py - 4.0, px + 4.0, py + 4.0)
                    for px, py in (ax.transData.transform((x, y)) for x, y in zip(xs, ys))]
    placed = list(obstacles)
    frame = ax.get_window_extent(renderer)
    angles = np.deg2rad(np.arange(0, 360, 15))
    for i in np.argsort(-np.asarray(ys)):
        text = ax.annotate(labels[i], (xs[i], ys[i]), textcoords="offset points", xytext=(0, 0),
                           ha="center", va="center", fontsize=fontsize, color="#222222", zorder=6)
        best, best_cost = (0.0, 0.0), np.inf
        for distance in (8.0, 11.0, 14.0, 18.0, 23.0, 29.0):
            for angle in angles:
                text.xyann = (distance * np.cos(angle), distance * np.sin(angle))
                b = text.get_window_extent(renderer)
                candidate = (b.x0 - 1.0, b.y0 - 1.0, b.x1 + 1.0, b.y1 + 1.0)
                cost = sum(_overlap(candidate, other) for other in placed + marker_boxes)
                cost += 400.0 * _outside(candidate, frame)
                cost += 0.30 * distance                     # near its own marker, all else being equal
                if cost < best_cost:
                    best, best_cost = text.xyann, cost
                if best_cost <= 0.30 * distance + 1e-9:
                    break
            if best_cost <= 0.30 * distance + 1e-9:
                break
        text.xyann = best
        b = text.get_window_extent(renderer)
        placed.append((b.x0 - 1.0, b.y0 - 1.0, b.x1 + 1.0, b.y1 + 1.0))
        if np.hypot(*best) > 15.0:                          # far from its marker: draw the leader
            # Anchored in the same offset POINTS the label itself uses, so that the line still starts
            # under the label whatever resolution the plate is finally written at.
            ax.annotate("", xy=(xs[i], ys[i]), xycoords="data",
                        xytext=(best[0] * 0.55, best[1] * 0.55), textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", lw=0.4, color=LEADER_COLOUR, shrinkA=0.0,
                                        shrinkB=3.0), zorder=2)


def spearman(a05, grd):
    """Spearman's rho of the sixteen regions and its Fisher-z interval, the plate's own form.

    The variance carries the Spearman correction, se² = 1.06/(n − 3): the plain 1/√(n − 3) form gives
    0.20–0.86 where the stored plate prints 0.18–0.86."""
    rho = float(stats.spearmanr(a05, grd).statistic)
    n = len(grd)
    z, se = math.atanh(rho), math.sqrt(1.06 / (n - 3))
    q = stats.norm.ppf(0.975)
    return rho, math.tanh(z - q * se), math.tanh(z + q * se), n


# --------------------------------------------------------------------------- the plate
def draw():
    style()
    plt.rcParams.update({
        "font.size": LABEL_PT, "axes.titlesize": TITLE_PT, "axes.labelsize": LABEL_PT,
        "xtick.labelsize": TICK_PT, "ytick.labelsize": TICK_PT, "axes.edgecolor": "#333333",
        "axes.linewidth": 0.7, "xtick.major.size": 2.4, "ytick.major.size": 2.4,
        "xtick.major.pad": 1.8, "ytick.major.pad": 1.8, "axes.labelpad": 2.4,
    })
    summary = regional_summary()
    grd = indicator_frame(summary, GRD)
    a05 = indicator_frame(summary, A05)
    moran = moran_regional()
    shapes = regions_shapefile()
    # Panel (f) ranks the regions, so it needs the GRD rate without the table's one-decimal rounding.
    grd_exact = grd_rate_full_precision(grd)
    rho, lo, hi, n = spearman(a05.rate.to_numpy(float), grd_exact.to_numpy(float))

    fig = plt.figure(figsize=FIGSIZE)
    _map(fig, MAP_CELL["a"], CBAR["a"], shapes, grd.eb)
    _map(fig, MAP_CELL["b"], CBAR["b"], shapes, a05.eb)
    _rate_panel(fig, BOX["c"], grd, BLUE)
    _rate_panel(fig, BOX["d"], a05, ORANGE)
    _moran_panel(fig, BOX["e"], moran)
    scatter, warning = _scatter_panel(fig, BOX["f"], a05.rate.to_numpy(float),
                                      grd_exact.to_numpy(float), list(grd.index))

    headings = dict(TITLE)
    headings["f"] = (f"Spearman's rho = {num(rho, 'en', 2)} (95% CI {num(lo, 'en', 2)}–"
                     f"{num(hi, 'en', 2)}; n = {n})")
    for letter in "abcdef":
        rows = _wrap(f"({letter}) {headings[letter]}").split("\n")
        fig.text(TITLE_X[letter], TITLE_TOP[letter], "\n".join(rows), fontsize=TITLE_PT,
                 fontweight="bold", ha="left", va="top", linespacing=TITLE_LINESPACING)

    # The composition is frozen first, then the region names are placed against what is already on the
    # page — the order the stored plate resolves them in.
    fig.canvas.draw()
    note = warning.get_window_extent(fig.canvas.get_renderer())
    # The red note is the one thing on the panel a region name may never touch, so it is offered to
    # the placer with a margin around it rather than as its bare box.
    place_point_labels(fig, scatter, a05.rate.to_numpy(float), grd_exact.to_numpy(float),
                       list(grd.index),
                       obstacles=[(note.x0 - 3.0, note.y0 - 3.0, note.x1 + 3.0, note.y1 + 3.0)])
    return fig


if __name__ == "__main__":
    draw().savefig("E49_regional_summary_redraw.png", dpi=141.1)
