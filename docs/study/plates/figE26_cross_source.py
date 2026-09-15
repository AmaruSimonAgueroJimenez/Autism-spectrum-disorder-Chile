"""Plate E26 — the five administrative systems side by side: index, raw value, population rate and
value per reporting unit, with the denominators of the last two, 2019–2025.

The stored plate `docs/study/corpus/figures/figE26_cross_source.jpg` was drawn by `study/pipeline/`
from the GRD, DEIS, REM and education files, which this repository does not carry. Every number it
plots survives in published aggregates, so the six panels are redrawn here from tracked tables only:

  (a) index of each system to the 2021 base   `E26_cross_source.csv` + `E60_grd_annual_full.csv`
  (b) raw annual value in the source's unit   `E26_cross_source.csv`
  (c) value per 100,000 residents             `E26_cross_source.csv`
  (d) the INE denominator of panel (c)        `T4_denominators_coverage.csv`
  (e) value per reporting unit                `E26_cross_source.csv`
  (f) the denominators of panel (e)           `E60`, `ST11a_deis_annual.csv`, `E17`, `E76`

Every cell of E26 is a formatted triple — `2,334 episodes; 12.2 /100,000; 35.9 per reporting GRD
hospital` — and the three numbers are three different estimators that are not interchangeable: the
raw value feeds panel (b), the per-100,000-resident rate feeds panel (c) and the per-reporting-unit
value feeds panel (e). `_cell()` parses all three out of the string; nothing is recomputed from the
others.

The one panel that E26 cannot supply on its own is (a), and it is also the one that is easy to get
wrong. The index is NOT the same quantity for the five series. REM A05, REM P2 and the harmonised
PIE are indices of their RAW counts, but GRD and DEIS are indices of their ACTIVITY rates: GRD of
its episodes per 100,000 panel episodes (202.7 → 804.1, which lives in E60 and nowhere in E26) and
DEIS of its discharges per 100,000 DEIS discharges (18.2 → 40.7, the third sub-value of E26's own
DEIS cell). Indexing those two on raw counts instead gives 369 and 227 where the plate prints 278
and 200 — a plate that looks right and is not. The base year is 2021, the first year common to all
five series, because the REM strict-autism codes only begin in 2021.

The GRD series is one row of E60 and must be selected on all four of its keys — F84 family excluding
Rett syndrome, the observed annual panel, all activities, any diagnostic position — because E60 also
carries the fixed-panel-of-65, F84-principal, strict-hospitalisation and strict-F84.0 variants, whose
numbers differ substantially. DEIS is principal F84 only (304 in 2019), never F84 in any position.

`_check_published()` rebuilds every per-reporting-unit value of panel (e) from the panel (f)
denominators and compares it with the published E26 cell, and checks panel (c) against panel (d), so
the two halves of the plate are verified against each other before anything is drawn.

UNITS DIFFER: episodes, discharges, entries, persons under control and students are not
interchangeable, the sources are not person-linked, and the panels keep separate axes for that
reason. The corpus is English only, so this module is English only.
"""
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

HERE = Path(__file__).resolve().parent          # docs/study/plates
STUDY = HERE.parent                             # docs/study
ROOT = STUDY.parent.parent                      # repository root
if str(STUDY) not in sys.path:                  # import figstyle the way the figure scripts do
    sys.path.insert(0, str(STUDY))
from figstyle import *                          # noqa: E402,F401,F403  (house style)

PLATE = "figE26_cross_source"
SOURCES = [
    "docs/study/corpus/tables/E26_cross_source.csv",
    "docs/study/corpus/tables/E60_grd_annual_full.csv",
    "docs/study/corpus/tables/ST11a_deis_annual.csv",
    "docs/study/corpus/tables/E17_rem_establishment_distribution.csv",
    "docs/study/corpus/tables/E76_education_pie_full.csv",
    "docs/study/corpus/tables/T4_denominators_coverage.csv",
]
CROSS, GRD_ANNUAL, DEIS_ANNUAL, REM_ESTABLISHMENTS, PIE_FULL, DENOMINATORS = SOURCES
NOTE = ("Redraws the six panels of E26 — index to the 2021 base, raw value, value per 100,000 "
        "residents and its INE denominator, value per reporting unit and its denominators — from "
        "the published E26 triples, the GRD annual table (whose activity rate is what the index of "
        "the GRD series is built on), the DEIS annual table, the REM establishment table and the "
        "PIE applicant table.")

YEARS = list(range(2019, 2026))
BASE_YEAR = 2021                # first year common to all five series: the REM codes start in 2021
GRD_ROW = ('F84 family excluding Rett syndrome',   # the four keys that select the GRD series in E60
           'Observed annual panel', 'All activities', 'Any position')
# Law 21.545 was published on 10 March 2023 (day 69). Each year is plotted at its own midpoint, so
# the marker sits a little before the 2023 position. Context only: no estimate depends on it.
LAW_X = 2023 + 69 / 365 - 0.5
PANDEMIC = (2019.5, 2021.5)
XLIM = (2018.4, 2025.6)

#: One row per source: the E26 column, the colour, and the short label panels (b) and (c) use.
SERIES = [
    ('GRD: episodes with documented F84', BLUE, 'GRD (episodes)'),
    ('DEIS: discharges with principal F84', SKY, 'DEIS (discharges)'),
    ('REM A05: strict-autism entries', ORANGE, 'REM A05 (entries)'),
    ('REM P2: December population under control', GREEN, 'REM P2 (persons under control)'),
    ('Education: harmonised PIE', PINK, 'PIE (students)'),
]
#: Panel (f): the denominator of each series and the label of its line.
DENOMINATOR_LABELS = ['GRD — reporting GRD hospitals', 'DEIS — total DEIS discharges',
                      'REM A05 — reporting REM establishments',
                      'REM P2 — reporting REM establishments', 'PIE — PIE applicants']

BAR = '#9ecae1'                 # panel (d): the light blue of the population bars
LAW_GREY = '#444444'            # the law marker and its label
BAND_GREY = '#666666'           # the pandemic band label
FOOT_GREY = '#595959'           # the first footnote
FOOT_RED = '#b22222'            # the units-differ footnote
ANNOTATION = 6.2                # in-axes annotations and the footnotes
LEGEND = 6.2                    # the five-entry legend under each panel
TITLE = 8.7                     # the bold heading above each panel

# The stored plate is 1000 x 1361 px for a 6.89 x 9.38 in figure (145.1 dpi). The axes rectangles,
# read off the spines of that image, are kept in those pixels and converted once: panel (d) is
# taller than panel (c) because it is the only panel without a legend underneath it.
PX_W, PX_H = 1000, 1361
AXES_PX = {'a': (83.5, 437.5, 53, 280), 'b': (630.5, 984.5, 53, 280),
           'c': (83.5, 437.5, 487, 714.5), 'd': (630.5, 984.5, 487, 811.5),
           'e': (83.5, 437.5, 921.5, 1149), 'f': (630.5, 984.5, 921.5, 1149)}
#: Log limits read off the stored plate, so the decade ticks land where the original put them.
YLIM = {'a': (29.6, 13800.0), 'b': (190.0, 414000.0), 'c': (1.0, 10600.0),
        'e': (2.01, 9720.0), 'f': (40.3, 1.668e7)}
TITLES = {'a': '(a) Annual value indexed to the stated base\nyear',
          'b': '(b) Raw annual value of each source',
          'c': '(c) Value per 100,000 residents (INE, 2017\nbase)',
          'd': '(d) Denominator of panel (c): INE population\n(2017 base, 30 Jun)',
          'e': '(e) Value per reporting unit',
          'f': '(f) Denominator of panel (e): reporting units\nby year'}
YLABELS = {'a': 'Index (base year = 100) — 2021 = 100', 'b': 'Annual value (log scale)',
           'c': 'Per 100,000 residents', 'd': 'Population (millions)',
           'e': 'Value per reporting unit', 'f': 'Units or base (log scale)'}
FOOTNOTES = [
    (FOOT_GREY, '(e) The number of schools is not published in the sources used; the education '
                'denominator is PIE applicants.'),
    (FOOT_RED, 'UNITS DIFFER: episodes, entries, persons under control and students are not '
               'interchangeable; axes are separate and there is no person-level linkage\n'
               'across sources.'),
]


# ---------------------------------------------------------------- tracked tables and their parsing
def _read(rel):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, encoding='utf-8-sig')


def _n(cell):
    """A presentation number such as '1,667,180', '19.11' or '—' as a float, or NaN when absent."""
    s = str(cell).strip().replace(',', '')
    try:
        return float(s)
    except ValueError:
        return float('nan')


#: A cell of E26: raw value and its unit, the rate per 100,000 residents, and the value per
#: reporting unit with the name of that unit. Any of the three numbers may be 'n/e'.
CELL = re.compile(r'^(?P<raw>[\d,]+|n/e)\s+(?P<unit>[^;]+);\s*'
                  r'(?P<rate>[\d.]+|n/e)\s*/100,000;\s*'
                  r'(?P<per>[\d.]+|n/e)\s+(?P<per_unit>per .+)$')


def _cell(text):
    """The three estimators packed into one E26 cell, as a dict; None when the year is not reported.

    They are three different quantities — a count, a rate per 100,000 residents and a value per
    reporting unit — and each panel of the plate uses a different one, so they are kept apart here
    rather than derived from one another.
    """
    s = str(text).strip()
    if s in ('n/e', 'nan', ''):
        return None
    m = CELL.match(s)
    if not m:
        raise ValueError(f'E26 cell not in the expected format: {text!r}')
    return {'raw': _n(m['raw']), 'unit': m['unit'].strip(), 'rate': _n(m['rate']),
            'per': _n(m['per']), 'per_unit': m['per_unit'].strip()}


def cross_source():
    """E26 parsed into {column: {year: cell}}, one entry per source and year actually reported."""
    t = _read(CROSS).set_index('Year')
    out = {}
    for c, _, _ in SERIES:
        parsed = {y: _cell(t.loc[y, c]) for y in YEARS}
        out[c] = {y: cell for y, cell in parsed.items() if cell is not None}
    return out


def grd_activity_rate():
    """The GRD row of E60: episodes per 100,000 panel episodes, by year, and the hospital panel.

    The row is selected on all four keys of the table. E60 also holds the fixed-panel-of-65,
    F84-principal, strict-hospitalisation and strict-F84.0 variants; their numbers differ
    substantially, so selecting by file name or by position would silently change the estimator.
    """
    t = _read(GRD_ANNUAL)
    series, panel, activity, position = GRD_ROW
    row = t[(t.Series == series) & (t.Panel.str.startswith(panel))
            & (t.Activity == activity) & (t['Code position'] == position)]
    if len(row) != 1:
        raise ValueError(f'E60 does not hold exactly one {GRD_ROW} row (found {len(row)})')
    row = row.iloc[0]
    years = [y for y in YEARS if str(y) in t.columns]
    # each cell is 'count; rate (low–high)' — the rate is the second field
    rate = {y: _n(str(row[str(y)]).split(';')[1].split('(')[0]) for y in years}
    # the panel label states the hospitals that reported each year: '(65, 65, 65, 65, 68 and 72)'
    hospitals = [int(v) for v in re.findall(r'\d+', row.Panel.split('(')[1])]
    if len(hospitals) != len(years):
        raise ValueError(f'E60 panel label {row.Panel!r} does not name one count per year')
    return rate, dict(zip(years, hospitals))


def deis_discharges():
    """Total DEIS discharges of the canonical file layout, by year (the denominator of panel f)."""
    t = _read(DEIS_ANNUAL)
    t = t[t['File layout'] == 'canonical']
    return {int(y): _n(v) for y, v in zip(t.Year, t['DEIS discharges (all establishments)'])}


def rem_establishments(series):
    """Reporting REM establishments of one module ('A05 strict autism (entries)' or 'P2 ASD ...')."""
    t = _read(REM_ESTABLISHMENTS)
    row = t[(t.Series == series) & (t.Value == 'Reporting establishments')].iloc[0]
    out = {}
    for y in YEARS:
        v = _n(row[str(y)])                      # 'outside the era' before the module existed
        if not np.isnan(v):
            out[y] = v
    return out


def pie_applicants():
    """Total PIE applicants (all special educational needs), the education denominator of panel (f)."""
    t = _read(PIE_FULL)
    row = t[t.Series == 'pie_total_applicants_sinaces'].iloc[0]
    return {y: _n(row[str(y)]) for y in YEARS if not np.isnan(_n(row[str(y)]))}


def ine_population():
    """The INE Censo 2017-base projection at 30 June, the denominator of panel (c)."""
    t = _read(DENOMINATORS)
    row = t[t.Indicator == 'INE projection, Census 2017 base (primary denominator)'].iloc[0]
    return {y: _n(row[str(y)]) for y in YEARS}


# ------------------------------------------------------------------------------ the plotted series
def denominators(rate_panel, pie):
    """Panel (f): the denominator of every series, in the order of SERIES."""
    return [rate_panel,                                         # reporting GRD hospitals
            deis_discharges(),                                  # total DEIS discharges
            rem_establishments('A05 strict autism (entries)'),
            rem_establishments('P2 ASD (December)'),
            pie]                                                # PIE applicants


def indexed(cells, grd_rate, deis_rate):
    """Panel (a): each series indexed to BASE_YEAR = 100, each on its own published estimator.

    GRD and DEIS are indexed on their activity rates (per 100,000 panel episodes and per 100,000
    DEIS discharges); REM A05, REM P2 and PIE on their raw counts. The two are different series and
    indexing all five the same way is the trap this panel sets.
    """
    out = []
    for i, (col, _, _) in enumerate(SERIES):
        if i == 0:
            values = dict(grd_rate)
        elif i == 1:
            values = dict(deis_rate)
        else:
            values = {y: c['raw'] for y, c in cells[col].items()}
        base = values[BASE_YEAR]
        out.append({y: 100 * v / base for y, v in values.items()})
    return out


# --------------------------------------------------------------------------------- self-validation
def _check_published(cells, grd_hospitals, pop):
    """Rebuild the published values from the denominators before drawing a single point.

    Panel (e) against panel (f): value per reporting unit = raw value / denominator, with the DEIS
    and PIE series scaled as their own labels state (per 100,000 discharges, per 1,000 applicants).
    Panel (c) against panel (d): rate per 100,000 residents = raw value / INE population.
    Both are compared with the cell E26 publishes, at the one decimal the table prints.
    """
    scale = [1, 1e5, 1, 1, 1e3]
    dens = denominators(grd_hospitals, pie_applicants())
    bad = []
    for (col, _, _), den, k in zip(SERIES, dens, scale):
        for y, c in cells[col].items():
            if not np.isnan(c['per']) and y in den:
                got = k * c['raw'] / den[y]
                if abs(got - c['per']) > 0.051:       # the table prints one decimal
                    bad.append(f'(e) {col} {y}: rebuilt {got:.3f} vs published {c["per"]}')
            got = 1e5 * c['raw'] / pop[y]
            if abs(got - c['rate']) > 0.051:
                bad.append(f'(c) {col} {y}: rebuilt {got:.3f} vs published {c["rate"]}')
    if bad:
        raise ValueError('E26 does not reproduce from its denominators:\n  ' + '\n  '.join(bad))


# ------------------------------------------------------------------------------------- the drawing
def _rect(key):
    """One axes rectangle of the stored plate, in figure coordinates."""
    x0, x1, y0, y1 = AXES_PX[key]
    return [x0/PX_W, 1 - y1/PX_H, (x1 - x0)/PX_W, (y1 - y0)/PX_H]


def _frame(ax, key, law=True):
    """The furniture every panel shares: years, pandemic band, law marker, grid and labels."""
    ax.set_xlim(*XLIM)
    year_ticks(ax, YEARS)
    shade_pandemic(ax, *PANDEMIC)      # the house band, tagged so the overlap QA ignores it
    ax.text(sum(PANDEMIC)/2, 0.985, '2020–2021 (pandemic)', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=ANNOTATION, color=BAND_GREY)
    if law:
        ax.axvline(LAW_X, color=LAW_GREY, ls=(0, (1, 1.8)), lw=1.0, zorder=1)
        ax.text(LAW_X + 0.11, 0.985, 'Law 21.545 (2023)', transform=ax.get_xaxis_transform(),
                ha='left', va='top', fontsize=ANNOTATION, color=LAW_GREY)
    clean(ax, grid='both')
    ax.tick_params(axis='both', which='both', length=0)
    ax.set_xlabel('Year')
    # (a) carries the longest label of the plate and the original sets it smaller and tighter
    # against the tick labels so that it still spans only the height of its own panel.
    ax.set_ylabel(YLABELS[key], fontsize=5.85 if key == 'a' else 8, labelpad=0 if key == 'a' else 3)


def _line(ax, values, colour, label):
    """One source as the plate draws it: a marked line over the years it actually reports."""
    years = sorted(values)
    ax.plot(years, [values[y] for y in years], '-o', color=colour, label=label,
            lw=1.6, ms=5.4, mew=0, zorder=3)


def _legend(ax):
    """The five-entry legend the plate centres under each panel."""
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.207), fontsize=LEGEND, handlelength=1.2,
              handletextpad=0.5, labelspacing=0.25, borderpad=0.0, borderaxespad=0.0)


def _heading(fig, key):
    """The bold heading the plate prints above each panel, wrapped where the original wraps it."""
    x0, _, y0, _ = AXES_PX[key]
    fig.text(0.010 if x0 < PX_W/2 else 0.528, 1 - (y0 - 2)/PX_H, TITLES[key],
             fontweight='bold', fontsize=TITLE, ha='left', va='bottom', linespacing=1.2)


def draw():
    style()
    cells = cross_source()
    grd_rate, grd_hospitals = grd_activity_rate()
    pop = ine_population()
    _check_published(cells, grd_hospitals, pop)

    deis_col = SERIES[1][0]
    deis_rate = {y: c['per'] for y, c in cells[deis_col].items()}     # per 100,000 DEIS discharges
    index = indexed(cells, grd_rate, deis_rate)
    dens = denominators(grd_hospitals, pie_applicants())

    fig = plt.figure(figsize=(PX_W/145.14, PX_H/145.14))
    ax = {k: fig.add_axes(_rect(k)) for k in 'abcdef'}

    # (a) index to the 2021 base — GRD and DEIS on their activity rates, the rest on raw counts
    for (col, colour, _), values in zip(SERIES, index):
        last = max(values)
        _line(ax['a'], values, colour, f'{col} — {num(values[last], "en", 0)} ({last})')
    ax['a'].axhline(100, color=BLACK, ls='--', lw=0.9, zorder=2)

    # (b) raw annual value, (c) value per 100,000 residents
    for col, colour, short in SERIES:
        _line(ax['b'], {y: c['raw'] for y, c in cells[col].items()}, colour, short)
        _line(ax['c'], {y: c['rate'] for y, c in cells[col].items()}, colour, short)

    # (d) the INE denominator of panel (c), in millions, with the printed bar labels
    millions = [pop[y]/1e6 for y in YEARS]
    ax['d'].bar(YEARS, millions, width=0.55, color=BAR, zorder=2)
    for y, v in zip(YEARS, millions):
        ax['d'].annotate(num(v, 'en', 2), (y, v), xytext=(0, 1), textcoords='offset points',
                         ha='center', va='bottom', fontsize=7.0, color=BLACK)

    # (e) value per reporting unit, labelled with the unit E26 names in the cell itself
    for col, colour, _ in SERIES:
        reported = {y: c['per'] for y, c in cells[col].items() if not np.isnan(c['per'])}
        unit = next(c['per_unit'] for c in cells[col].values())
        _line(ax['e'], reported, colour, f'{col.split(":")[0].replace("Education", "PIE")} — {unit}')

    # (f) the denominators of panel (e)
    for (_, colour, _), values, label in zip(SERIES, dens, DENOMINATOR_LABELS):
        _line(ax['f'], values, colour, label)

    for key in 'abcdef':
        _frame(ax[key], key, law=key not in ('d', 'f'))
        _heading(fig, key)
    for key in ('a', 'b', 'c', 'e', 'f'):
        log_axis(ax[key], 'y', 'en')
        ax[key].set_ylim(*YLIM[key])
        _legend(ax[key])
    ax['d'].set_ylim(0, 1.31 * max(millions))   # the headroom the stored plate leaves for the labels
    ax['d'].yaxis.set_major_locator(MultipleLocator(5))
    ax['d'].yaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, 'en', 1)))

    for y_px, (colour, text) in zip((1303, 1327), FOOTNOTES):
        fig.text(0.009, 1 - y_px/PX_H, text, fontsize=ANNOTATION, color=colour, ha='left', va='top',
                 linespacing=1.25)
    return fig
