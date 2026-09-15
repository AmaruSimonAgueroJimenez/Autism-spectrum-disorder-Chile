"""Plate S9 — the regional picture: three choropleths, the ecological scatter and two region x year heat maps.

The stored plate was drawn by `figS9()` of `study/pipeline/08c_figures_triangulation.py` from the GRD
and REM A05 microdata, which this repository does not carry. Its six panels are redrawn here from the
tracked tables that publish the same series:

* `docs/study/corpus/tables/S9_regional_rates.csv` — the plate's own companion table: the sixteen
  regions with the INE base-2017 population at 30 June 2024, the 2024 GRD F84 episode count and rate
  for BOTH case-definition variants (full F84 with Rett, and F84 without Rett), and the 2024 REM A05
  strict-autism entries with the number of reporting establishments and their own rate. Every cell is
  a formatted string — `"261,779"`, `"8,420,729"`, `"70.3 (60.5 to 81.2)"` — and is parsed, never
  retyped. This one table carries panels (a), (b), (c) and (d) whole.
* `docs/study/corpus/tables/E62_grd_region_population_rates.csv` — the region x year GRD panel
  2019–2024, stored as `"162; 31.2 (26.6–36.4)"`. Only the COUNT before the semicolon is read: the
  rate it publishes is computed on a doubled denominator (Arica 2024 prints 35.1 where the plate shows
  70) and would halve every cell of panel (e).
* `output_files/consolidacion/population_regional.csv` — the INE base-2017 projection by region, sex
  and five-year age group, summed over sex and age to the regional denominator of each year. Its 2024
  column reproduces the population column of S9 exactly (Arica 261,779), which is the check this
  module runs before it divides. The regional rows of `E73_denominator_layers_full.csv` are NOT used:
  they are exactly twice the true value.
* `docs/study/corpus/tables/E13_rem_a05_regional.csv` — the region x year A05 panel 2021–2025, stored
  as `"181 / 69.1 (12)"`: count, published rate, reporting establishments. Panel (f) puts the
  establishments in the year label, as the stored plate does, and paints the count over the same INE
  denominator: E13 publishes its rate to ONE DECIMAL, and two of its cells sit exactly on a rounding
  boundary there, so a heat map built on the printed 4.5 and 37.5 of Metropolitana 2021 and 2024 would
  print 5 and 38 where the plate prints 4 and 37. The full-precision values are 4.49 and 37.48. The
  recomputed rate agrees with every published one to the decimal E13 prints. 2025 is the exception:
  its INE denominator is in no tracked file, so the published rate is used for that column — no 2025
  value lies near a boundary, so the printed integers are the same either way.

GEOMETRY. Panels (a)–(c) are maps and need polygons. Chile's regional boundaries live in
`data/Regional.shp`, which is present on the machine that built the report but is NOT git-tracked —
exactly the dependency the hospital chapter already declares through `scripts/report_helpers.load_regions()`.
Only the polygons are untracked; every value painted on them comes from S9. The three maps are built
here the way `load_regions_equal_area()` builds them in the pipeline: read, clip to the continental
box (-76.5, -56.6, -66.0, -17.3) so the oceanic islands do not stretch the frame, reproject to the
Albers equal-area conic for Chile, simplify at 800 m, and draw in the three north/centre/south bands
that let a 4,300 km country fit a 90 mm cell. Where the shapefile is absent the three map panels say so
in place of the map and the other three panels are unaffected — nothing is drawn from invented geometry.

Estimators, carried over unchanged from the stored plate:

* the two sources are located DIFFERENTLY and the plate says so in red inside panel (d): GRD is by
  region of RESIDENCE (the comuna recorded in the discharge, linked by normalised name), REM A05 by
  the region of the reporting ESTABLISHMENT, i.e. the place of care. Inter-regional referrals are not
  corrected, so panel (d) is an ecological comparison and the warning is reproduced verbatim;
* every rate is a CRUDE count per 100,000 INE residents — not age-standardised, not smoothed, not
  empirical-Bayes shrunk;
* the GRD numerator counts EPISODES with F84 in any position, not persons; the A05 numerator counts
  ENTRIES, not persons;
* panels (a) and (b) differ only by the Rett variant and share one colour scale, so that the pair can
  be read as the sensitivity check it is;
* panels (b), (d) and (e) are the WITHOUT-RETT variant, which is the plate's own default: Spearman's
  rho on the sixteen regions is 0.379 for that pairing (the 0.38 the panel title prints) against 0.365
  for the full-F84 one.

The corpus is English only, so this module is too.
"""
import re
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter
from scipy import stats
from figstyle import *

PLATE = "figS9_regional_maps"
SOURCES = [
    "docs/study/corpus/tables/S9_regional_rates.csv",
    "docs/study/corpus/tables/E62_grd_region_population_rates.csv",
    "docs/study/corpus/tables/E13_rem_a05_regional.csv",
    "output_files/consolidacion/population_regional.csv",
    "data/Regional.shp",            # regional polygons: present locally, NOT git-tracked (see NOTE)
]
NOTE = ("Redraws the six panels of plate S9 — the 2024 choropleth of GRD F84 episodes per 100,000 "
        "residents under both case-definition variants, the 2024 REM A05 choropleth by region of the "
        "reporting establishment, the log-log ecological scatter of the two with Spearman's rho, and "
        "the two region x year heat maps — from S9_regional_rates.csv, E62 counts divided by the "
        "regional INE denominators of output_files/consolidacion/population_regional.csv, and the "
        "published rates of E13_rem_a05_regional.csv; the three maps additionally need the regional "
        "polygons of data/Regional.shp, which is present on the build machine but is not git-tracked "
        "(the same untracked geometry the hospital chapter already depends on), and they say so in "
        "place of the map when it is missing.")

ROOT = Path(__file__).resolve().parents[3]      # docs/study/plates/<this file> -> the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
TITLE_W_PT = (180 / 25.4 * 72.0) / 2 - (4.0 / 25.4 * 72.0)      # half the canvas less a 4 mm margin
NOTE_W_PT = 150.0                               # the width a panel note is folded to, in the plate norm
CELL_MARGIN = 2.0 / 180.0                       # 2 mm: where a panel title starts inside its own cell
FS_TITLE, FS_MIN = 9.0, 6.0                     # the plate norm of 08c: titles 9 pt, floor 6 pt

# CUT region codes, their names as S9 and E13 spell them, and the north -> south order of the plate.
REGION_NAMES = {
    15: "Arica y Parinacota", 1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 13: "Metropolitana", 6: "O'Higgins", 7: "Maule", 16: "Ñuble", 8: "Biobío",
    9: "La Araucanía", 14: "Los Ríos", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
}
REGION_ORDER = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]
# The plate abbreviates the four longest names on its axes and inside its maps; the full name is always
# in the accompanying table. This is the study's own label glossary, restricted to the regions.
SHORT = {"Arica y Parinacota": "Arica y P.", "Antofagasta": "Antofag.", "Metropolitana": "Metropol.",
         "La Araucanía": "Araucanía"}
# North, centre and south: a 4,300 km country does not fit one 90 mm cell at a legible scale.
BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]
GRD_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]        # the GRD panel of E62
A05_YEARS = [2021, 2022, 2023, 2024, 2025]              # the A05 panel of E13
LAST = 2024                                             # the year both sources share on the maps
SHAPEFILE = ROOT / "data" / "Regional.shp"
# Continental box, in degrees: Easter Island and the Antarctic claim would otherwise set the frame.
CONTINENTAL_BOX = (-76.5, -56.6, -66.0, -17.3)
ALBERS = ("+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 "
          "+datum=WGS84 +units=m +no_defs")          # equal-area conic for Chile, as the pipeline uses
SIMPLIFY_M = 800
WARNING = ("WARNING: REM locates the establishment (place of care) and GRD the comuna of residence; "
           "inter-regional patient flows are not corrected. Ecological comparison.")
WARNING_RED = "#8b0000"
RATE_LABEL = "per 100,000 population"
MISSING_GREY = "#f2f2f2"
# The stored plate writes a dark cell label over a translucent white patch so that it survives the
# colour under it, and switches to white ink on the darkest cells (`_pl_backing` of the plate engine).
BACKING = dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9)
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)
WHITE_INK_FRAC = 0.6        # the heat map writes in white above 0.6 x the panel maximum

# --------------------------------------------------------------------------- reading the tables
# Every presentation table stores its values as formatted strings. Three shapes appear here:
#   "8,420,729"                 a count with thousands separators
#   "70.3 (60.5 to 81.2)"       a rate with its exact Poisson limits           (S9)
#   "162; 31.2 (26.6–36.4)"     a count, then a rate on a denominator we reject (E62)
#   "1,329 / 65.6 (126)"        a count, a rate and the establishments that filed it  (E13)
_E62 = re.compile(r"^\s*([\d.,]+)\s*;")
_E13 = re.compile(r"^\s*([\d.,]+)\s*/\s*([\d.,]+)\s*\(\s*([\d.,]+)\s*\)\s*$")


def _num(s):
    """One formatted number -> float; an empty or not-estimable cell -> nan."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-", "< 5"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-"))


def _rate(s):
    """'70.3 (60.5 to 81.2)' -> 70.3 — the point estimate; S9's limits are not drawn on this plate."""
    return _num(str(s).split("(")[0])


def _half_up(v):
    """Round half AWAY FROM ZERO, as the plate prints it: 44.5 -> 45, 96.5 -> 97, 37.5 -> 38.

    Python rounds half to even, which would print 44 and 96 and disagree with the stored plate in
    three of the eighty cells below."""
    return int(Decimal(repr(float(v))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _table(rel):
    """A tracked table, read as text (the corpus tables are written with a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str)


def regional_2024():
    """S9 by CUT region: population, both GRD variants (count and rate), A05 entries, rate and n."""
    t = _table(SOURCES[0]).set_index("Region")
    col = {c.split("·")[-1].strip(): c for c in t.columns if "·" in c}
    rows = {}
    for code in REGION_ORDER:
        r = t.loc[REGION_NAMES[code]]
        rows[code] = dict(
            population=_num(r["INE population 2024 (base 2017)"]),
            grd_con_rett=_num(r[col["Full F84 (with Rett)"]]),
            rate_con_rett=_rate(r[col["GRD Full F84 (with Rett)"]]),
            grd_sin_rett=_num(r[col["F84 without Rett"]]),
            rate_sin_rett=_rate(r[col["GRD F84 without Rett"]]),
            a05=_num(r["A05 autism entries 2024"]),
            establishments=_num(r["Reporting establishments"]),
            rate_a05=_rate(r[col["A05"]]),
        )
    out = pd.DataFrame(rows).T.reindex(REGION_ORDER)
    # The published rate is the published count over the published population: the check costs nothing
    # and it is what tells us the three columns belong to one another.
    for count, rate in (("grd_con_rett", "rate_con_rett"), ("grd_sin_rett", "rate_sin_rett"),
                        ("a05", "rate_a05")):
        recomputed = (out[count] / out["population"] * 1e5).round(1)
        assert np.allclose(recomputed, out[rate]), f"S9: {rate} is not {count} over the population"
    return out


def regional_population():
    """The INE denominator of each region and year, summed over sex and five-year age group."""
    pop = pd.read_csv(ROOT / SOURCES[3])
    return pop.groupby(["year", "cut_region"]).population.sum()


def grd_heatmap(population, s9):
    """Panel (e): GRD F84 without Rett per 100,000 residents, 16 regions x 2019-2024.

    E62 publishes the counts of this exact variant (its 2024 column is 228 for Tarapacá, the
    without-Rett figure of S9, not the 230 of the full-F84 one) and a rate we do not use."""
    t = _table(SOURCES[1])
    t = t.set_index(t.columns[0])
    grid = np.full((len(REGION_ORDER), len(GRD_YEARS)), np.nan)
    for i, code in enumerate(REGION_ORDER):
        for j, year in enumerate(GRD_YEARS):
            cell = t.loc[REGION_NAMES[code], str(year)]
            m = _E62.match(str(cell))
            assert m, f"E62 cell is not 'count; rate (limits)': {cell!r}"
            grid[i, j] = _num(m.group(1)) / population[(year, code)] * 1e5
    # The last column of E62 is 2024, which S9 publishes as a finished rate: the two must agree.
    assert np.allclose(grid[:, -1].round(1), s9["rate_sin_rett"].to_numpy()), \
        "E62 2024 over population_regional does not reproduce the without-Rett rates of S9"
    return grid


def a05_heatmap(population, s9):
    """Panel (f): A05 entries per 100,000 residents, 16 regions x 2021-2025, and the establishments.

    The rate is recomputed from the count wherever the year has a tracked denominator, because E13
    stores it rounded to one decimal and the plate rounds the unrounded value. 2025 has no tracked
    denominator and keeps the published rate."""
    t = _table(SOURCES[2])
    t = t.set_index(t.columns[0])
    grid = np.full((len(REGION_ORDER), len(A05_YEARS)), np.nan)
    estab = np.zeros((len(REGION_ORDER), len(A05_YEARS)))
    for i, code in enumerate(REGION_ORDER):
        for j, year in enumerate(A05_YEARS):
            m = _E13.match(str(t.loc[REGION_NAMES[code], str(year)]))
            assert m, f"E13 cell is not 'count / rate (n)': {t.loc[REGION_NAMES[code], str(year)]!r}"
            published = _num(m.group(2))
            if (year, code) in population.index:
                grid[i, j] = _num(m.group(1)) / population[(year, code)] * 1e5
                assert round(grid[i, j], 1) == published, \
                    f"E13 {REGION_NAMES[code]} {year}: {grid[i, j]:.2f} is not the published {published}"
            else:                       # 2025: the INE projection for that year is in no tracked file
                grid[i, j] = published
            estab[i, j] = _num(m.group(3))
    national = np.array([_num(_E13.match(str(t.loc["Chile (national total)", str(y)])).group(3))
                         for y in A05_YEARS])
    assert np.allclose(estab.sum(axis=0), national), "E13: the regional establishments do not add up"
    assert np.allclose(grid[:, A05_YEARS.index(LAST)].round(1), s9["rate_a05"].to_numpy()), \
        "E13 and S9 disagree on the 2024 A05 rates"
    return grid, estab.sum(axis=0)


def regions_shapefile():
    """Continental regional polygons in the Albers equal-area conic, or None when the file is absent.

    `data/Regional.shp` is not git-tracked. The steps are those of `load_regions_equal_area()` in
    `study/pipeline/08c_figures_triangulation.py`: drop the undemarcated zone, repair the geometry,
    clip to the continental box, reproject and simplify."""
    if not SHAPEFILE.is_file():
        return None
    import warnings
    import geopandas as gpd
    from shapely.geometry import box
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        shp = gpd.read_file(SHAPEFILE)
    shp = shp.loc[shp.codregion.astype(int) > 0, ["codregion", "geometry"]].rename(
        columns={"codregion": "cut_region"})
    shp["cut_region"] = shp.cut_region.astype(int)
    shp = shp.to_crs(4326)
    try:
        shp["geometry"] = shp.geometry.make_valid()
    except AttributeError:                      # older shapely
        shp["geometry"] = shp.geometry.buffer(0)
    shp["geometry"] = shp.geometry.intersection(box(*CONTINENTAL_BOX))
    shp = shp[~shp.geometry.is_empty].copy()
    shp = shp.to_crs(ALBERS)
    shp["geometry"] = shp.geometry.simplify(SIMPLIFY_M)
    assert set(shp.cut_region) == set(REGION_ORDER), "the shapefile does not carry the sixteen regions"
    return shp


# --------------------------------------------------------------------------- panel furniture
def _wrap(text, width_pt=TITLE_W_PT, size=FS_TITLE, weight="bold"):
    """Fold a title at a MEASURED width, as the plate engine does — not at a character count."""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    prop = FontProperties(family=plt.rcParams["font.family"], size=size, weight=weight)
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and TextPath((0, 0), trial, prop=prop, usetex=False).get_extents().width > width_pt:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    return "\n".join(lines)


def panel_head(ax, ch, title, fig=None):
    """`(a) Title`, bold, folded to the cell and anchored to its left edge — the plate's own header."""
    ax.set_title("", loc="center")
    ax.set_title(_wrap(f"({ch}) {title}"), loc="left", fontsize=FS_TITLE, fontweight="bold", pad=3.0,
                 linespacing=1.15)


def _cell_left(spec):
    """Left edge of a panel's own grid cell, as a fraction of the figure, through any nested grid."""
    grid = spec.get_gridspec()
    parent = getattr(grid, "_subplot_spec", None)
    x0, x1 = _cell_left_right(parent) if parent is not None else (0.0, 1.0)
    return x0 + (x1 - x0) * spec.colspan.start / grid.ncols


def _cell_left_right(spec):
    grid = spec.get_gridspec()
    parent = getattr(grid, "_subplot_spec", None)
    x0, x1 = _cell_left_right(parent) if parent is not None else (0.0, 1.0)
    return (x0 + (x1 - x0) * spec.colspan.start / grid.ncols,
            x0 + (x1 - x0) * spec.colspan.stop / grid.ncols)


def align_titles(fig, margin=CELL_MARGIN):
    """Anchor every panel title to the left edge of ITS cell, 2 mm in — the plate's own rule.

    Left as it comes, a title starts at the axes, which the y-axis label has already pushed inward, and
    the long titles of the right-hand column then run off the canvas. Measured in the stored plate, all
    six start at 0.013 and 0.513 of the width: the cell edge plus that margin."""
    for ax in fig.axes:
        spec = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
        title = ax.title if ax.title.get_text() else getattr(ax, "_left_title", None)
        pos = ax.get_position()
        if spec is None or title is None or not title.get_text() or pos.width <= 0:
            continue
        title.set_ha("left")
        title.set_x((_cell_left(spec) + margin - pos.x0) / pos.width)


def heatmap(ax, grid, cmap, fontsize=FS_MIN + 0.2):
    """A region x year matrix with its value written in each cell.

    White ink above 0.6 x the panel maximum, dark ink over a translucent white patch below it. The
    threshold is applied to the RATE, not to the printed integer: Los Lagos 2024 is 42.5 and stays
    dark, Aysen 2023 is 43.4 and turns white, and both print `43`."""
    im = ax.imshow(grid, cmap=cmap, aspect="auto")
    vmax = np.nanmax(grid)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid[i, j]
            if not np.isfinite(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=fontsize, color="#777777")
                continue
            white = v > WHITE_INK_FRAC * vmax
            ax.text(j, i, num(_half_up(v), "en"), ha="center", va="center", fontsize=fontsize,
                    color="white" if white else "#222222", zorder=5,
                    bbox=None if white else dict(BACKING))
    ax.set_yticks(range(grid.shape[0]))
    ax.set_yticklabels([SHORT.get(REGION_NAMES[c], REGION_NAMES[c]) for c in REGION_ORDER],
                       fontsize=FS_MIN + 0.2)
    ax.grid(False)
    return im


def chile_map(fig, slot, shapes, values, title, ch, cmap="YlGnBu", vmin=None, vmax=None):
    """Three bands (north, centre, south) at one metric scale, one colour scale and a shared bar.

    The band is drawn at a fixed aspect ratio, so the title cannot hang from the map's own axes: with
    the aspect pinned, reserving room for it collapses them. It goes on its own near-zero-height row of
    the sub-grid, exactly as the stored plate arranges it."""
    sub = slot.subgridspec(3, 3, height_ratios=[0.001, 1, 0.05], wspace=0.04, hspace=0.05)
    tax = fig.add_subplot(sub[0, :])
    tax.set_axis_off()
    panel_head(tax, ch, title)
    if shapes is None:
        gap = fig.add_subplot(sub[1, :])
        gap.set_axis_off()
        gap.text(0.5, 0.5, "Map not drawn: the regional polygons of\n`data/Regional.shp` are not in "
                           "this repository.\nThe values are in S9_regional_rates.csv and in\n"
                           "panels (d)-(f).", ha="center", va="center", fontsize=FS_MIN + 1.4,
                 color="#555555", linespacing=1.45)
        return [gap]
    series = pd.Series(values).reindex(shapes.cut_region.to_numpy()).to_numpy(dtype=float)
    finite = series[np.isfinite(series)]
    norm = Normalize(vmin=float(finite.min()) if vmin is None else vmin,
                     vmax=float(finite.max()) if vmax is None else vmax)
    mapper = ScalarMappable(norm=norm, cmap=cmap)
    bounds = [shapes[shapes.cut_region.isin(band)].total_bounds for band in BANDS]
    span = max(b[3] - b[1] for b in bounds) * 1.04
    # One x window COMMON to the three bands: the metric scale has to be the same in all three, and no
    # region label may fall outside its axes (matplotlib does not clip the text for us).
    width = max(span * 0.36, max(b[2] - b[0] for b in bounds) * 1.30)
    axes = []
    for k, band in enumerate(BANDS):
        ax = fig.add_subplot(sub[1, k])
        g = shapes[shapes.cut_region.isin(band)].copy()
        v = pd.Series(values).reindex(g.cut_region.to_numpy()).to_numpy(dtype=float)
        g.plot(color=[mapper.to_rgba(x) if np.isfinite(x) else MISSING_GREY for x in v],
               edgecolor="#555555", linewidth=0.3, ax=ax)
        b = g.total_bounds
        cy, cx = (b[1] + b[3]) / 2, (b[0] + b[2]) / 2
        ax.set_ylim(cy - span / 2, cy + span / 2)
        ax.set_xlim(cx - width / 2, cx + width / 2)
        ax.set_aspect("equal")
        ax.set_axis_off()
        # The region's name sits ON its polygon and may not be moved: moved, it stops naming the region
        # it names. The plate accepts the crowding of the central band for that reason.
        for row in g.itertuples():
            point = row.geometry.representative_point()
            name = REGION_NAMES[row.cut_region]
            ax.text(point.x, point.y, SHORT.get(name, name), fontsize=FS_MIN, ha="center", va="center",
                    color="#222222", clip_on=True,
                    bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.70))
        axes.append(ax)
    cax = fig.add_subplot(sub[2, :])
    bar = fig.colorbar(mapper, cax=cax, orientation="horizontal")
    bar.set_label(RATE_LABEL, fontsize=FS_MIN + 0.5)
    bar.ax.tick_params(labelsize=FS_MIN + 0.2)
    return axes


def place_point_labels(fig, ax, xs, ys, labels, obstacles=(), fontsize=FS_MIN):
    """Sixteen region labels around sixteen markers, placed by MEASUREMENT, with a leader when far.

    The stored plate places them at save time, with the composition already frozen: it tries a ring of
    directions and distances around each marker and rejects any placement that covers a marker, another
    label or a note. The same rule is applied here, from the farthest point inward, so that the most
    crowded corner is settled last against what is already on the page."""
    renderer = fig.canvas.get_renderer()
    marker_boxes = []
    for x, y in zip(xs, ys):
        px, py = ax.transData.transform((x, y))
        marker_boxes.append((px - 4.0, py - 4.0, px + 4.0, py + 4.0))
    placed = list(obstacles)
    frame = ax.get_window_extent(renderer)
    angles = np.deg2rad(np.arange(0, 360, 15))
    order = np.argsort(-np.asarray(ys))                 # the pipeline labels from the top down
    for i in order:
        px, py = ax.transData.transform((xs[i], ys[i]))
        text = ax.annotate(labels[i], (xs[i], ys[i]), textcoords="offset points", xytext=(0, 0),
                           ha="center", va="center", fontsize=fontsize, color="#222222", zorder=6)
        best, best_cost = None, np.inf
        for distance in (8.0, 11.0, 14.0, 18.0, 23.0, 29.0):
            for angle in angles:
                dx, dy = distance * np.cos(angle), distance * np.sin(angle)
                text.set_position((xs[i], ys[i]))
                text.xyann = (dx, dy)
                box = text.get_window_extent(renderer)
                candidate = (box.x0 - 1.0, box.y0 - 1.0, box.x1 + 1.0, box.y1 + 1.0)
                cost = sum(_overlap(candidate, other) for other in placed + marker_boxes)
                cost += 400.0 * _outside(candidate, frame)
                cost += 0.30 * distance                 # near its own marker, all else being equal
                if cost < best_cost:
                    best, best_cost = (dx, dy), cost
                if best_cost <= 0.30 * distance + 1e-9:
                    break
            if best_cost <= 0.30 * distance + 1e-9:
                break
        text.xyann = best
        box = text.get_window_extent(renderer)
        placed.append((box.x0 - 1.0, box.y0 - 1.0, box.x1 + 1.0, box.y1 + 1.0))
        if np.hypot(*best) > 15.0:                      # far from its marker: draw the leader line
            text.set_arrowprops(None)
            ax.annotate("", xy=(xs[i], ys[i]), xycoords="data",
                        xytext=(px + best[0] * 0.55, py + best[1] * 0.55), textcoords="figure pixels",
                        arrowprops=dict(arrowstyle="-", lw=0.4, color="#999999", shrinkA=0, shrinkB=3),
                        zorder=2, annotation_clip=False)


def _overlap(a, b):
    """Area shared by two pixel boxes, in square points — zero when they do not touch."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0.0) * max(h, 0.0)


def _outside(box, frame):
    """How far a label sticks out of its axes, in pixels; zero when it is wholly inside."""
    return (max(frame.x0 - box[0], 0.0) + max(box[2] - frame.x1, 0.0)
            + max(frame.y0 - box[1], 0.0) + max(box[3] - frame.y1, 0.0))


def draw():
    style()
    plt.rcParams.update({
        "font.size": 8.0, "axes.titlesize": FS_TITLE, "axes.labelsize": 7.5,
        "xtick.labelsize": 7.0, "ytick.labelsize": 7.0, "grid.alpha": 0.32, "grid.linewidth": 0.5,
    })
    s9 = regional_2024()
    population = regional_population()
    # The denominator of the heat map has to be the denominator of the table it is checked against.
    assert np.allclose([population[(LAST, c)] for c in REGION_ORDER], s9["population"].to_numpy()), \
        "population_regional and S9 disagree on the 2024 regional populations"
    grd_grid = grd_heatmap(population, s9)
    a05_grid, a05_estab = a05_heatmap(population, s9)
    shapes = regions_shapefile()

    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN), constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    gs = fig.add_gridspec(3, 2)

    # (a), (b) the two GRD variants on ONE shared colour scale --------------------------------------
    # The scale is shared so that the pair reads as the sensitivity check it is: its top is the larger
    # of the two 2024 maxima, which is the full-F84 one (72.1 against 71.9).
    vmax_grd = float(max(s9["rate_con_rett"].max(), s9["rate_sin_rett"].max()))
    for ch, column, variant in (("a", "rate_con_rett", "Full F84 (with Rett)"),
                                ("b", "rate_sin_rett", "F84 without Rett")):
        chile_map(fig, gs[0, "ab".index(ch)], shapes, s9[column],
                  f"GRD {variant}: F84 per 100,000 pop., residence, {LAST}", ch, vmin=0, vmax=vmax_grd)

    # (c) the A05 map, on its own scale and its own colour ------------------------------------------
    n_estab = int(s9["establishments"].sum())
    assert n_estab == int(a05_estab[A05_YEARS.index(LAST)]), "S9 and E13 disagree on the 2024 n"
    chile_map(fig, gs[1, 0], shapes, s9["rate_a05"],
              f"REM A05: entries per 100,000 pop., establishment, {LAST} (n = {num(n_estab, 'en')})",
              "c", cmap="YlOrRd", vmin=0)

    # (d) the ecological scatter: residence against place of care ------------------------------------
    d = fig.add_subplot(gs[1, 1])
    a05 = s9["rate_a05"].to_numpy(dtype=float)
    grd = s9["rate_sin_rett"].to_numpy(dtype=float)      # the plate's default variant, not full F84
    rho = float(stats.spearmanr(a05, grd).statistic)
    d.scatter(a05, grd, s=16, color=BLUE, edgecolor="white", linewidth=0.4, zorder=3)
    d.set_xscale("log")
    d.set_yscale("log")
    for axis, values in ((d.xaxis, a05), (d.yaxis, grd)):
        lo, hi = float(values.min()), float(values.max())
        ticks = [t for t in (10, 15, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300)
                 if lo * 0.85 <= t <= hi * 1.15]
        axis.set_major_locator(FixedLocator(ticks))
        axis.set_major_formatter(FuncFormatter(lambda v, _p: num(v, "en")))
        axis.set_minor_formatter(NullFormatter())
    d.set_xlim(float(a05.min()) * 0.80, float(a05.max()) * 1.28)
    d.set_ylim(float(grd.min()) * 0.80, float(grd.max()) * 2.6)      # air for the labels and the note
    d.set_xlabel("A05 entries per 100,000 pop. (log)")
    d.set_ylabel("GRD F84 episodes per 100,000 pop. (log)")
    clean(d, "both")
    # The warning is the plate's own, verbatim and in its own red: the two sources are not comparable
    # region by region without correcting the inter-regional flows.
    warning = d.text(0.02, 0.985, _wrap(WARNING, width_pt=NOTE_W_PT, size=FS_MIN + 0.3,
                                        weight="normal"),
                     transform=d.transAxes, fontsize=FS_MIN + 0.3, ha="left", va="top",
                     color=WARNING_RED, bbox=dict(NOTE_BBOX), linespacing=1.25, zorder=6)
    panel_head(d, "d", f"Regions {LAST}: GRD (residence) vs A05 (place of care); "
                       f"Spearman ρ = {num(rho, 'en', 2)} (n = {len(grd)})")

    # (e) GRD without Rett, region x year -----------------------------------------------------------
    e = fig.add_subplot(gs[2, 0])
    heatmap(e, grd_grid, "YlGnBu")
    e.set_xticks(range(len(GRD_YEARS)))
    e.set_xticklabels([str(y) for y in GRD_YEARS], fontsize=FS_MIN + 0.5)
    e.set_xlabel("Year")
    e.set_ylabel("Region (north → south)")
    panel_head(e, "e", "GRD F84 without Rett: F84 episodes per 100,000 pop. by region of residence "
                       "and year")

    # (f) A05, region x year; the establishments go in the year label --------------------------------
    f = fig.add_subplot(gs[2, 1])
    heatmap(f, a05_grid, "YlOrRd")
    f.set_xticks(range(len(A05_YEARS)))
    f.set_xticklabels([f"{y}\nn={num(n, 'en')}" for y, n in zip(A05_YEARS, a05_estab)],
                      fontsize=FS_MIN)
    f.set_xlabel("Year (n = reporting establishments)")
    f.set_ylabel("")
    panel_head(f, "f", "REM A05 autism: entries per 100,000 pop. by region of establishment")

    # The composition is frozen first, then the titles are anchored to their cells and the scatter
    # labels placed against what is already on the page — the order the stored plate resolves them in.
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    fig.canvas.draw()
    align_titles(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    note_box = warning.get_window_extent(renderer)
    title = d.title if d.title.get_text() else d._left_title
    obstacles = [(note_box.x0, note_box.y0, note_box.x1, note_box.y1)]
    place_point_labels(fig, d, a05, grd,
                       [SHORT.get(REGION_NAMES[c], REGION_NAMES[c]) for c in REGION_ORDER], obstacles)
    return fig


if __name__ == "__main__":
    draw().savefig("figS9_regional_maps_redraw.png", dpi=200)
