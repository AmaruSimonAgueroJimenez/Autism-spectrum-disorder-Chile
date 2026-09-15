"""Figure 1 — what was done with each database: the six data families of the multisource study.

Redraw of the stored plate `docs/study/corpus/figures/fig1_dataflow.jpg`. The original was composed by
`study/pipeline/08d_figure_dataflow.py`, which reads every figure at run time out of the pipeline's
`outputs/tidy/*.csv`; this repository does not carry those, so the schematic is rebuilt here from the
companion table the plate was published with, `T_dataflow_counts.csv`, which stores each figure with
its unit, its source column and a column saying whether it is drawn on the schematic.

This plate carries no plotted series: it is a hand-composed diagram of six lanes, one per data family,
each read from left to right as `database -> steps -> what the lane yields`. Nothing here is a
trajectory or a cascade — the lanes share no identifier, which is what the dashed red band states once.

Six lanes, six bands, in the order of the original:

  1 Hospital care                                     two rows, GRD and DEIS
  2 Care pathway · REM Series A (A03, A05, A27, A28)  one row
  3 People under control · REM Series P                one row
  4 Denominators and coverage                          one row
  5 Surveys and education                              two rows, the surveys and the school registers
  6 Territory                                          one row

The visual grammar is the original's and is reproduced exactly: a cylinder is a database and carries a
badge saying what one row is — square RECORD, circle PERSON, hexagon COMUNA; a rounded box is a step
really applied to that database; a pointed block is what the lane yields. Arrows carry only figures.
Red, and only red, marks what is excluded or never added, with its minus sign. Two strokes across an
arrow mark a definition break, with its three or four words underneath. The lane palette is the
schematic's own (one ink per lane, `#B02A1A` reserved for exclusions and for the barrier), not the
Okabe–Ito series of `figstyle`, because the plate uses colour to name lanes and not to encode a scale.

WHAT THE FIGURES ARE. Every number is a count or a rate already computed elsewhere and published in
`T_dataflow_counts.csv`; nothing is recomputed here and nothing is estimated. The two arrow pairs of
lane 1 are rates per 100,000 of the lane's own denominator — GRD 202.7 -> 804.1 per 100,000 episodes,
DEIS 18.2 -> 40.7 per 100,000 discharges — and the plate prints them rounded to whole numbers, so this
module prints `203 -> 804` and `18 -> 41` as the original does. `84.8%` is the FONASA share of the
projected resident population, `22.4%` a share of the education programme's published base and `7.7%`
the design-weighted JUNAEB percentage; the labels that say so are the yield blocks and are unchanged.
The case definition is the one the plate declares in its top-right corner, `without Rett`: the F84
family excluding Rett syndrome, which is the variant `T_dataflow_counts.csv` was published for.

ONE OBSERVATION ABOUT THE COMPANION TABLE. Forty-one of its 62 rows are flagged `On the schematic =
yes` and this module draws thirty-eight of them. The three it does not draw are the design-weighted
survey percentages (ENDIDE adults 0.29, ENDIDE children 2.87, ENCAVI 0.71): the survey row has a
single step and therefore only two arrows, so the original's own layout has nowhere to put a third
stack of figures and the stored plate does not show them either — the flag records that the figure was
registered for the row, not that it was printed. The yield block `design-weighted percentage` is what
the lane shows in their place, exactly as in the stored plate.

The periods printed inside the cylinders (2019–2024 for the hospital lane, 2019–2025 for REM) are read
from the `Period` column of the supplementary source table `M1_sources_units.csv` rather than typed in,
and `Figure_S1_dataflow_count_provenance.csv` is read to re-check twelve of the drawn figures against
an independently derived copy before the figure is built.

The corpus is English only, so this plate is English only.
"""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from matplotlib.patches import (Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon,
                                Rectangle, RegularPolygon)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "fig1_dataflow"
SOURCES = [
    "docs/study/corpus/tables/T_dataflow_counts.csv",
    "docs/study/corpus/tables/M1_sources_units.csv",
    "docs/study/data/Figure_S1_dataflow_count_provenance.csv",
]
COUNTS, UNITS, PROVENANCE = SOURCES
NOTE = ("Redraws the six-lane data-flow schematic of Figure 1 — cylinder, steps and yield block for "
        "each data family, with the n at entry, the n after the autism selection and the ends of the "
        "series on the arrows — from the published companion table of counts, the supplementary "
        "source table that carries each lane's period, and the count-provenance table used to "
        "re-check the drawn figures.")

TABLE_COUNTS = BASE / 'corpus' / 'tables' / 'T_dataflow_counts.csv'
TABLE_UNITS = BASE / 'corpus' / 'tables' / 'M1_sources_units.csv'
TABLE_PROV = BASE / 'data' / 'Figure_S1_dataflow_count_provenance.csv'

VARIANT_TAG = 'without Rett'       # the case definition the companion table was published for

# ---------------------------------------------------------------------------
# Geometry of the schematic, in millimetres: one data unit is one millimetre and the plate is drawn 1:1
# ---------------------------------------------------------------------------
W_MM, H_MM = 180.0, 245.0
MM_PER_IN = 25.4
PT_MM = 0.3528

X0, X1 = 3.5, 176.5                # margins of the content
LANES_TOP, LANES_BOT = 241.6, 3.2  # the band the six lanes occupy
SEP_MIN, SEP_MAX = 4.4, 9.0        # gap between lanes: the no-linkage barrier sits in one of them

DB_W = 33.0                        # width of the database cylinder
YIELD_W = 34.0                     # width of the yield block
YIELD_TIP = 4.4                    # its point
STEP_W_MAX, STEP_W_MIN = 40.0, 15.0
ARROW_MIN = 8.5                    # shortest arrow between two elements
BREAK_ROOM = 6.2                   # room the definition-break mark needs on its arrow
DRUM_E = 3.0                       # height of the cylinder's ellipses
PAD = 1.30                         # inner padding of the boxes
LINE_FACTOR = 1.18
CHIP_R = 1.25                      # half-side / radius of the unit badge
CHIP_GAP = 0.95                    # badge to its word
TITLE_GAP = 1.6                    # lane title to its first row
ROW_GAP = 2.0                      # between two rows of the same lane
TOL_MM = 0.12

# Type sizes in points. Nothing on the plate goes below 6 pt.
FS_VARIANT, FS_LANE, FS_DB, FS_DB_SUB = 8.0, 8.8, 8.4, 7.2
FS_CHIP, FS_STEP, FS_YIELD, FS_NUM, FS_NOTE, FS_BARRIER = 6.9, 7.6, 7.8, 8.2, 7.1, 7.9
FS_FLOOR = 6.6

# One ink per lane; red is always an exclusion or the barrier.
LANE_INK = ["#0B5FA5", "#0E7C7B", "#1F7A3C", "#8A6100", "#6A4C93", "#44586B"]
LANE_FILL = ["#e9f1fa", "#e5f4f3", "#e9f4ed", "#f8f0dd", "#efeaf7", "#eceff3"]
EXCL_COL = "#B02A1A"
INK, MUTED, CHIP_EDGE = "#1a1a1a", "#4d4d4d", "#2f2f2f"

RECORD, PERSON, PLACE = "record", "person", "comuna"
BARRIER = "no person-level linkage between systems"

WARNINGS = []                      # composition problems seen while measuring, never silently kept


# ===========================================================================
# The figures: every one of them read out of the published companion table
# ===========================================================================
#: plate key -> the exact label the companion table gives that figure in its `Count` column.
KEYS = {
    'grd_in': 'GRD episodes at entry',
    'grd_sel': 'GRD episodes with documented F84',
    'grd_rate_first': 'Episodes with documented F84 per 100,000 GRD episodes, 2019',
    'grd_rate_last': 'Episodes with documented F84 per 100,000 GRD episodes, 2024',
    'grd_hosp_fixed': 'Hospitals in the fixed panel',
    'grd_hosp_min': 'Hospitals in the observed panel, first year',
    'grd_hosp_max': 'Hospitals in the observed panel, last year',
    'deis_in': 'DEIS discharges at entry',
    'deis_sel': 'DEIS discharges with F84 as the principal diagnosis',
    'deis_rate_first': 'Discharges with principal F84 per 100,000 discharges, 2019',
    'deis_rate_last': 'Discharges with principal F84 per 100,000 discharges, 2024',
    'deis_masked': ('DEIS discharges in provider-masked rows, kept in the national totals and out of '
                    'the territorial tables'),
    'rema_in': 'REM Series A establishment-month rows at entry',
    'a05_first': 'Autism entries into ambulatory care, 2021',
    'a05_last': 'Autism entries into ambulatory care, 2025',
    'a05_era_year': 'First year of the code era of the autism entry indicator',
    'rem_empty': 'REM establishment-month cells reported empty, kept as empty and never read as zero',
    'remp_in': 'REM Series P establishment-month rows at entry',
    'p2_first': 'People with autism under control in December 2019',
    'p2_last': 'People with autism under control in December 2025',
    'p6_era_year': 'First year of the code era of the specialty autism indicator',
    'p2_june_last': 'June 2025 stock, a sensitivity never added to December',
    'cov_ine': 'Residents projected at 30 June 2025',
    'cov_share_fonasa': ('FONASA beneficiaries as a percentage of the projected resident population, '
                         '2025'),
    'endide_adults': 'ENDIDE respondents aged 18 or more',
    'endide_children': 'ENDIDE children aged 2–17 answered for by a caregiver',
    'encavi_n': 'ENCAVI respondents aged 15 or more',
    'endide_adult_cases': 'ENDIDE adults reporting autism',
    'endide_child_cases': 'ENDIDE children reported as autistic',
    'encavi_cases': 'ENCAVI respondents reporting an autism diagnosis',
    'pie_base_last': 'Students in the published base of the school integration programme, 2025',
    'junaeb_in_last': 'Pre-school students who answered the JUNAEB survey, 2025',
    'pie_last': 'Autistic students in the harmonised programme series, 2025',
    'junaeb_sel_last': 'Pre-school students reported as autistic, 2025',
    'pie_share_last': "Autistic students as a percentage of the programme's published base, 2025",
    'junaeb_pct_last': 'Design-weighted percentage of pre-school students reported as autistic, 2025',
    'edu_source_year': 'First year published by the second source of the programme series',
    'geo_comunas': 'Comunas in the national cartography',
}

#: plate key -> key of `Figure_S1_dataflow_count_provenance.csv`, which re-derives the figure from its
#: own source file and column. Only the figures the provenance table also carries are listed.
CROSSCHECK = {'grd_in': 'all_episodes', 'grd_sel': 'eligible_any', 'a05_first': 'a05_2021_total',
              'a05_last': 'a05_2025_total', 'p2_first': 'p2_2019_total', 'p2_last': 'p2_2025_total',
              'grd_hosp_fixed': 'hospitals_fixed', 'grd_hosp_min': 'hospitals_min',
              'grd_hosp_max': 'hospitals_max', 'endide_adults': 'adult',
              'endide_children': 'child', 'encavi_n': 'encavi_valid', 'pie_last': 'pie2025'}


def _value(cell):
    """A figure out of the companion table's presentation cell: '5,808,535' or '202.7' or '2,024'."""
    return float(str(cell).replace(',', '').strip())


def values():
    """Every figure the schematic prints, read out of `T_dataflow_counts.csv` by its published label.

    Only the rows the table flags `On the schematic = yes` are eligible: the other 21 rows are
    deliberately off-plate and support the figure without appearing on it.
    """
    t = pd.read_csv(TABLE_COUNTS, encoding='utf-8-sig')
    on = t[t['On the schematic'].str.strip().eq('yes')]
    by_label = dict(zip(on['Count'].str.strip(), on['Value']))
    missing = [k for k, lab in KEYS.items() if lab not in by_label]
    if missing:
        raise KeyError(f'not flagged on the schematic in {TABLE_COUNTS.name}: {missing}')
    return {k: _value(by_label[lab]) for k, lab in KEYS.items()}


def periods():
    """The two periods printed inside the cylinders, from the `Period` column of the source table."""
    t = pd.read_csv(TABLE_UNITS, encoding='utf-8-sig')
    src = t.set_index(t['Source'].str.strip())['Period']
    grd = next(v for k, v in src.items() if k.startswith('GRD'))
    rem = next(v for k, v in src.items() if k.startswith('REM Serie A'))
    return str(grd).strip(), str(rem).strip()


def check(vals):
    """Re-check the drawn figures against the independently derived count-provenance table."""
    prov = pd.read_csv(TABLE_PROV, encoding='utf-8-sig')
    prov = dict(zip(prov['key'].str.strip(), prov['value'].astype(float)))
    bad = [f'{k}: {vals[k]:,.0f} on the plate, {prov[p]:,.0f} in the provenance table'
           for k, p in CROSSCHECK.items() if p in prov and abs(vals[k] - prov[p]) > 1e-6]
    if bad:
        raise ValueError('the schematic disagrees with ' + TABLE_PROV.name + ': ' + '; '.join(bad))
    return len(CROSSCHECK)


def _n(v, dec=0):
    """A figure as the English plate writes it: thousands separated, `dec` decimals."""
    return num(v, 'en', dec)


def _subst(txt, vals):
    """Resolve `{key}`, `{key:1}` and `{key:y}` in a break or note template; `:y` is a bare year."""
    def one(m):
        key, _, spec = m.group(1).partition(':')
        return str(int(vals[key])) if spec == 'y' else _n(vals[key], int(spec) if spec else 0)
    return re.sub(r'\{([^}]+)\}', one, txt)


# ===========================================================================
# Canvas: every string is measured on the real renderer before anything is drawn
# ===========================================================================
class Canvas:
    def __init__(self, fig, ax):
        self.fig, self.ax = fig, ax
        self.renderer = fig.canvas.get_renderer()
        self.rects = []
        self._cache = {}

    def width_mm(self, s, fs, weight='normal'):
        key = (s, round(fs, 2), weight)
        if key not in self._cache:
            t = self.ax.text(0, 0, s, fontsize=fs, fontweight=weight)
            bb = t.get_window_extent(renderer=self.renderer)
            t.remove()
            self._cache[key] = bb.width / self.fig.dpi * MM_PER_IN
        return self._cache[key]

    def register(self, x, y, w, h, name):
        for (x2, y2, w2, h2, n2) in self.rects:
            if x < x2 + w2 - 0.05 and x2 < x + w - 0.05 and y < y2 + h2 - 0.05 and y2 < y + h - 0.05:
                WARNINGS.append(f'box overlap: {name} overlaps {n2}')
        self.rects.append((x, y, w, h, name))


def wrap_fit(cv, s, fs, weight, max_w, floor=FS_FLOOR):
    """Break `s` into lines that fit `max_w`, shrinking the body to the floor before giving up."""
    s = str(s)
    while True:
        lines, cur = [], ''
        for w in s.split():
            trial = f'{cur} {w}'.strip()
            if cur and cv.width_mm(trial, fs, weight) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        lines = lines or ['']
        widest = max(cv.width_mm(ln, fs, weight) for ln in lines)
        if widest <= max_w + 0.05:
            return lines, fs
        if fs <= floor + 1e-9:
            WARNINGS.append(f"'{s}' needs {widest:.1f} mm in {max_w:.1f} mm at the floor")
            return lines, fs
        fs = max(floor, fs - 0.1)


def fit_fs(cv, s, fs, weight, max_w, floor=FS_FLOOR):
    """Shrink a line that must not wrap until it fits `max_w`."""
    while cv.width_mm(s, fs, weight) > max_w and fs > floor + 1e-9:
        fs = max(floor, fs - 0.1)
    if cv.width_mm(s, fs, weight) > max_w + 0.05:
        WARNINGS.append(f"'{s}' does not fit {max_w:.1f} mm at the floor")
    return fs


# ===========================================================================
# The visual vocabulary: three shapes, one ink per lane, red only for exclusions
# ===========================================================================
def put(cv, x, y, s, fs, *, weight='normal', colour=INK, ha='left', va='baseline', zorder=6,
        bbox=None):
    return cv.ax.text(x, y, s, fontsize=fs, fontweight=weight, color=colour, ha=ha, va=va,
                      zorder=zorder, bbox=bbox)


def put_block(cv, xc, yc, lines, fs, *, weight='normal', colour=INK, ha='center', zorder=6,
              bbox=None):
    """A block of lines centred vertically on `yc`."""
    lh = fs * PT_MM * LINE_FACTOR
    top = yc + len(lines) * lh / 2.0
    for i, ln in enumerate(lines):
        put(cv, xc, top - (i + 1) * lh + fs * PT_MM * 0.30, ln, fs, weight=weight, colour=colour,
            ha=ha, va='baseline', zorder=zorder, bbox=bbox)


def put_down(cv, x, y_top, lines, fs, *, weight='normal', colour=INK, ha='left', zorder=6):
    """A block of lines hanging from `y_top`; returns the y it ends at."""
    lh = fs * PT_MM * LINE_FACTOR
    yy = y_top
    for ln in lines:
        yy -= lh
        put(cv, x, yy + fs * PT_MM * 0.30, ln, fs, weight=weight, colour=colour, ha=ha,
            va='baseline', zorder=zorder)
    return yy


def drum(cv, x, y, w, h, edge, name=None):
    """Cylinder: a DATABASE. The only shape with elliptical caps."""
    if name:
        cv.register(x, y, w, h, name)
    e = min(DRUM_E, h * 0.34)
    cv.ax.add_patch(Ellipse((x + w / 2, y + e / 2), w, e, fc='white', ec=edge, lw=1.15, zorder=2))
    cv.ax.add_patch(Rectangle((x, y + e / 2), w, h - e, fc='white', ec='none', zorder=2))
    cv.ax.plot([x, x], [y + e / 2, y + h - e / 2], color=edge, lw=1.15, zorder=3)
    cv.ax.plot([x + w, x + w], [y + e / 2, y + h - e / 2], color=edge, lw=1.15, zorder=3)
    cv.ax.add_patch(Ellipse((x + w / 2, y + h - e / 2), w, e, fc='white', ec=edge, lw=1.15, zorder=3))


def step_box(cv, x, y, w, h, edge, name=None):
    """Rounded box: a STEP really applied to that database."""
    if name:
        cv.register(x, y, w, h, name)
    cv.ax.add_patch(FancyBboxPatch((x + 0.5, y + 0.5), w - 1.0, h - 1.0,
                                   boxstyle='round,pad=0.5,rounding_size=1.2',
                                   fc='white', ec=edge, lw=0.85, zorder=2))


def yield_block(cv, x, y, w, h, colour, name=None):
    """Pointed block: what the lane YIELDS."""
    if name:
        cv.register(x, y, w, h, name)
    pts = [(x, y), (x + w - YIELD_TIP, y), (x + w, y + h / 2), (x + w - YIELD_TIP, y + h), (x, y + h)]
    cv.ax.add_patch(Polygon(pts, closed=True, fc=colour, ec=colour, lw=0.8, zorder=2))


def flow_arrow(cv, x0, x1, y, colour, broken_x=None):
    """The flow arrow. `broken_x` cuts it exactly where the definition of the series changes."""
    cv.ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle='-|>', mutation_scale=7.5, lw=1.15,
                                    color=colour, shrinkA=0, shrinkB=0, zorder=3))
    if broken_x is not None:
        for dx in (-0.85, 0.85):
            cv.ax.plot([broken_x + dx - 0.7, broken_x + dx + 0.7], [y - 1.55, y + 1.55],
                       color=colour, lw=1.25, solid_capstyle='round', zorder=5)


def unit_chip(cv, x, yc, kind, fs, colour=CHIP_EDGE):
    """The badge of the unit of analysis: square RECORD, circle PERSON, hexagon COMUNA.

    The word is always beside the shape, so the shape never needs a legend.
    """
    if kind == RECORD:
        cv.ax.add_patch(Rectangle((x, yc - CHIP_R), 2 * CHIP_R, 2 * CHIP_R, fc='white', ec=colour,
                                  lw=1.0, zorder=5))
    elif kind == PERSON:
        cv.ax.add_patch(Circle((x + CHIP_R, yc), CHIP_R, fc='white', ec=colour, lw=1.0, zorder=5))
    else:
        cv.ax.add_patch(RegularPolygon((x + CHIP_R, yc), 6, radius=CHIP_R * 1.18, orientation=0.0,
                                       fc='white', ec=colour, lw=1.0, zorder=5))
    put(cv, x + 2 * CHIP_R + CHIP_GAP, yc - fs * PT_MM * 0.34, kind, fs, colour=colour, ha='left',
        va='baseline')


def chip_width(cv, word, fs):
    return 2 * CHIP_R + CHIP_GAP + cv.width_mm(word, fs)


# ===========================================================================
# The content: six lanes, each one `database -> steps -> what it yields`
# ---------------------------------------------------------------------------
# `nums` names keys of the companion table and draws them over the arrow given (0 = database to first
# step, n = last step to the yield block); `brk` is a template resolved the same way and marks, on that
# same arrow, where the definition of the series changes; `note` hangs under the step given, in red
# when it is an exclusion.
# ===========================================================================
def lanes(grd_span, rem_span):
    return [
        dict(key='hospital', title='Hospital care', rows=[
            dict(name='GRD', sub=[grd_span], unit=RECORD,
                 steps=['select F84 codes', 'position and activity'],
                 nums={0: [[('grd_in', 0, '')]], 1: [[('grd_sel', 0, '')]],
                       2: [[('grd_rate_first', 0, ''), ('grd_rate_last', 0, '')]]},
                 brk={1: '{grd_hosp_fixed} fixed · {grd_hosp_min}–{grd_hosp_max} observed'},
                 out='F84 per 100,000 episodes'),
            dict(name='DEIS', sub=[grd_span], unit=RECORD,
                 steps=['principal F84', 'by residence'],
                 nums={0: [[('deis_in', 0, '')]], 1: [[('deis_sel', 0, '')]],
                       2: [[('deis_rate_first', 0, ''), ('deis_rate_last', 0, '')]]},
                 note=dict(at=1, kind='excl', n=('deis_masked', 0), text='masked discharges'),
                 out='F84 per 100,000 discharges'),
        ]),
        dict(key='rem_pathway', title='Care pathway · REM Series A (A03, A05, A27, A28)', rows=[
            dict(name=None, sub=['screening · entries', 'counselling · rehabilitation', rem_span],
                 unit=RECORD,
                 steps=['harmonise codes', 'count establishments'],
                 nums={0: [[('rema_in', 0, '')]],
                       2: [[('a05_first', 0, ''), ('a05_last', 0, '')]]},
                 brk={1: 'code changes, {a05_era_year:y}'},
                 note=dict(at=0, kind='excl', n=('rem_empty', 0), text='empty cells, never zero'),
                 out='entries per year'),
        ]),
        dict(key='under_control', title='People under control · REM Series P', rows=[
            dict(name=None, sub=['P2 · P6', rem_span], unit=PERSON,
                 steps=['harmonise codes', 'take December'],
                 nums={0: [[('remp_in', 0, '')]],
                       2: [[('p2_first', 0, ''), ('p2_last', 0, '')]]},
                 brk={1: 'code changes, {p6_era_year:y}'},
                 note=dict(at=1, kind='excl', n=('p2_june_last', 0), text='June, never added'),
                 out='December stock'),
        ]),
        dict(key='denominators', title='Denominators and coverage', rows=[
            dict(name=None, sub=['INE · FONASA', 'APS · ISAPRE · REM-20'], unit=PERSON,
                 steps=['take December', 'age and sex'],
                 nums={0: [[('cov_ine', 0, '')]], 2: [[('cov_share_fonasa', 1, '%')]]},
                 note=dict(at=0, kind='plain', n=None, text='no autism code'),
                 out='residents as denominator'),
        ]),
        dict(key='surveys_education', title='Surveys and education', rows=[
            dict(name=None, sub=['ENDIDE 18+', 'ENDIDE 2–17', 'ENCAVI 15+'], unit=PERSON,
                 steps=['apply survey design'],
                 nums={0: [[('endide_adults', 0, '')], [('endide_children', 0, '')],
                           [('encavi_n', 0, '')]],
                       1: [[('endide_adult_cases', 0, '')], [('endide_child_cases', 0, '')],
                           [('encavi_cases', 0, '')]]},
                 out='design-weighted percentage'),
            dict(name=None, sub=['MINEDUC · PIE', 'JUNAEB'], unit=PERSON,
                 steps=['harmonise the series', 'weight the survey'],
                 nums={0: [[('pie_base_last', 0, '')], [('junaeb_in_last', 0, '')]],
                       1: [[('pie_last', 0, '')], [('junaeb_sel_last', 0, '')]],
                       2: [[('pie_share_last', 1, '%')], [('junaeb_pct_last', 1, '%')]]},
                 brk={0: 'source changes, {edu_source_year:y}'},
                 out='students per year'),
        ]),
        dict(key='territory', title='Territory', rows=[
            dict(name=None, sub=['SAE · deprivation', 'cartography'], unit=PLACE,
                 steps=['standardise by age and sex', 'smooth by comuna'],
                 nums={0: [[('geo_comunas', 0, '')]]},
                 out='smoothed comuna ratio'),
        ]),
    ]


# ===========================================================================
# Measuring one row: everything is measured on the renderer before anything is drawn
# ===========================================================================
def plan_row(cv, row, vals, xa, xb, scale):
    fs = SimpleNamespace(db=FS_DB * scale, sub=FS_DB_SUB * scale, chip=FS_CHIP * scale,
                         step=FS_STEP * scale, out=FS_YIELD * scale, num=FS_NUM * scale,
                         note=FS_NOTE * scale)
    P = dict(fs=fs)

    # --- the figures over the arrows -----------------------------------------------------------
    n_steps = len(row['steps'])
    n_arrows = n_steps + 1
    nums = {}
    for a, spec_lines in row.get('nums', {}).items():
        nums[a] = [' → '.join(_n(vals[key], dec) + suffix for key, dec, suffix in spec)
                   for spec in spec_lines]
    P['nums'] = nums

    # --- width of each arrow: the figure decides ------------------------------------------------
    gaps = []
    for a in range(n_arrows):
        w = max([cv.width_mm(ln, fs.num, 'bold') for ln in nums.get(a, [])], default=0.0)
        room = BREAK_ROOM if a in row.get('brk', {}) else 0.0
        gaps.append(max(ARROW_MIN + room, w + 4.6 + room) if w else max(ARROW_MIN, room + 4.0))
    span = (xb - xa) - DB_W - YIELD_W
    step_w = (span - sum(gaps)) / n_steps
    if step_w > STEP_W_MAX:
        gaps = [g + (step_w - STEP_W_MAX) * n_steps / n_arrows for g in gaps]
        step_w = STEP_W_MAX
    if step_w < STEP_W_MIN:
        WARNINGS.append(f"step boxes only {step_w:.1f} mm wide in the row yielding '{row['out']}'")
    P['gaps'], P['step_w'], P['n_steps'], P['n_arrows'] = gaps, step_w, n_steps, n_arrows

    # --- the cylinder ---------------------------------------------------------------------------
    inner = DB_W - 2 * PAD
    name = row.get('name')
    lh_chip = fs.chip * PT_MM * LINE_FACTOR + 0.6
    fs_name = fit_fs(cv, name, fs.db, 'bold', inner) if name is not None else fs.db
    lh_db = fs_name * PT_MM * LINE_FACTOR
    sub_fit = []
    for k, s in enumerate(row['sub']):
        head = name is None and k == 0          # with no name, the first line is the lane's head
        lines, f = wrap_fit(cv, s, fs.sub, 'bold' if head else 'normal', inner)
        sub_fit.append((lines, f, head))
    inline = (name is not None
              and cv.width_mm(name, fs_name, 'bold') + 1.7 + chip_width(cv, row['unit'],
                                                                       fs.chip) <= inner)
    drum_h = ((lh_db if name is not None else 0.0)
              + sum(len(ls) * f * PT_MM * LINE_FACTOR for ls, f, _ in sub_fit)
              + (0.0 if inline else lh_chip) + 2 * PAD + DRUM_E)
    P['drum'] = dict(name=name, fs_name=fs_name, sub=sub_fit, inline=inline, h=drum_h,
                     lh_db=lh_db, lh_chip=lh_chip)

    # --- the steps ------------------------------------------------------------------------------
    steps = [wrap_fit(cv, s, fs.step, 'normal', step_w - 2 * PAD) for s in row['steps']]
    step_h = max(max(len(ln) * f * PT_MM * LINE_FACTOR for ln, f in steps) + 2 * PAD, 8.6)
    P['steps'], P['step_h'] = steps, step_h

    # --- what the lane yields --------------------------------------------------------------------
    out_lines, fs_out = wrap_fit(cv, row['out'], fs.out, 'bold', YIELD_W - YIELD_TIP - 2 * PAD)
    out_h = max(len(out_lines) * fs_out * PT_MM * LINE_FACTOR + 2 * PAD, 9.8)
    P['out'], P['fs_out'], P['out_h'] = out_lines, fs_out, out_h

    # --- height of the core: the tallest box and the longest stack of figures ---------------------
    num_h = max([len(v) for v in nums.values()], default=0) * fs.num * PT_MM * LINE_FACTOR
    P['core_h'] = max(drum_h, step_h, out_h, num_h + 1.8)

    # --- definition breaks, at the foot of their arrow --------------------------------------------
    lh_note = fs.note * PT_MM * LINE_FACTOR
    brk = {a: wrap_fit(cv, _subst(t, vals), fs.note, 'normal', 46.0)[0]
           for a, t in row.get('brk', {}).items()}
    P['brk'] = brk
    P['brk_h'] = (max([len(v) for v in brk.values()], default=0) * lh_note + 1.5) if brk else 0.0

    # --- the note: an exclusion in red, or a plain remark in grey ----------------------------------
    note = row.get('note')
    P['note'], P['note_h'] = None, 0.0
    if note:
        head = '' if note['n'] is None else '−' + _n(vals[note['n'][0]], note['n'][1]) + '  '
        P['note'] = dict(at=note['at'], kind=note['kind'],
                         lines=wrap_fit(cv, head + note['text'], fs.note, 'normal', 64.0)[0])
        P['note_h'] = len(P['note']['lines']) * lh_note + 2.4

    P['h'] = P['core_h'] + P['brk_h'] + P['note_h']
    return P


def draw_row(cv, P, row, xa, xb, ytop, ink, tag):
    fs = P['fs']
    core_h, step_w, gaps = P['core_h'], P['step_w'], P['gaps']
    yc = ytop - core_h / 2.0

    # --- the cylinder ---------------------------------------------------------------------------
    d = P['drum']
    drum(cv, xa, yc - d['h'] / 2, DB_W, d['h'], ink, f'{tag}-db')
    xc = xa + DB_W / 2
    yy = yc + d['h'] / 2 - DRUM_E / 2 - PAD
    if d['name'] is not None:
        fn = d['fs_name']
        if d['inline']:
            w_name = cv.width_mm(d['name'], fn, 'bold')
            x_start = xc - (w_name + 1.7 + chip_width(cv, row['unit'], fs.chip)) / 2
            put(cv, x_start, yy - d['lh_db'] + fn * PT_MM * 0.30, d['name'], fn, weight='bold',
                colour=ink, ha='left', va='baseline')
            unit_chip(cv, x_start + w_name + 1.7, yy - d['lh_db'] * 0.52, row['unit'], fs.chip)
        else:
            put(cv, xc, yy - d['lh_db'] + fn * PT_MM * 0.30, d['name'], fn, weight='bold',
                colour=ink, ha='center', va='baseline')
        yy -= d['lh_db']
    for lines, f, head in d['sub']:
        for s in lines:
            yy -= f * PT_MM * LINE_FACTOR
            put(cv, xc, yy + f * PT_MM * 0.30, s, f, weight='bold' if head else 'normal',
                colour=ink if head else MUTED, ha='center', va='baseline')
    if not d['inline']:
        w_chip = chip_width(cv, row['unit'], fs.chip)
        unit_chip(cv, xc - w_chip / 2, yy - d['lh_chip'] * 0.5, row['unit'], fs.chip)

    # --- geometry of the steps and the arrows -----------------------------------------------------
    xs, x = [], xa + DB_W
    for i in range(P['n_steps']):
        x += gaps[i]
        xs.append(x)
        x += step_w
    x_out = xb - YIELD_W
    spans, prev = [], xa + DB_W
    for i in range(P['n_steps']):
        spans.append((prev, xs[i]))
        prev = xs[i] + step_w
    spans.append((prev, x_out))

    for i, (lines, f) in enumerate(P['steps']):
        step_box(cv, xs[i], yc - P['step_h'] / 2, step_w, P['step_h'], ink, f'{tag}-step{i}')
        put_block(cv, xs[i] + step_w / 2, yc, lines, f, colour=INK)

    yield_block(cv, x_out, yc - P['out_h'] / 2, YIELD_W, P['out_h'], ink, f'{tag}-out')
    put_block(cv, x_out + (YIELD_W - YIELD_TIP) / 2, yc, P['out'], P['fs_out'], weight='bold',
              colour='white')

    for a, (x_left, x_right) in enumerate(spans):
        has_num = a in P['nums']
        # with a figure on it, the break mark goes in the room reserved to the left of the white
        # label; without one, in the middle of the arrow.
        broken = (x_left + BREAK_ROOM * 0.48 if has_num else (x_left + x_right) / 2) \
            if a in P['brk'] else None
        flow_arrow(cv, x_left, x_right, yc, ink, broken_x=broken)
        if has_num:
            xn = ((x_left + BREAK_ROOM) + x_right) / 2 if a in P['brk'] else (x_left + x_right) / 2
            put_block(cv, xn, yc, P['nums'][a], fs.num, weight='bold', colour=INK, zorder=7,
                      bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none'))

    # --- the definition break, at the foot of its arrow --------------------------------------------
    y_brk = yc - core_h / 2 - 1.0
    for a, lines in P['brk'].items():
        x_left, x_right = spans[a]
        half = max(cv.width_mm(ln, fs.note) for ln in lines) / 2 + 0.5
        xm = min(max((x_left + x_right) / 2, xa + half), xb - half)
        put_down(cv, xm, y_brk, lines, fs.note, colour=ink, ha='center')

    # --- the note: an exclusion in red, with its own arrow, or a plain remark in grey ---------------
    nt = P['note']
    if nt:
        y_top = yc - core_h / 2 - P['brk_h'] - 0.7
        xm = xs[nt['at']] + step_w / 2
        if nt['kind'] == 'excl':
            cv.ax.add_patch(FancyArrowPatch((xm, y_top + 0.5), (xm, y_top - 2.3), arrowstyle='-|>',
                                            mutation_scale=6.0, lw=1.0, color=EXCL_COL, shrinkA=0,
                                            shrinkB=0, zorder=4))
            wmax = max(cv.width_mm(ln, fs.note) for ln in nt['lines'])
            put_down(cv, min(xm + 1.9, xb - wmax - 0.4), y_top - 0.7, nt['lines'], fs.note,
                     colour=EXCL_COL, ha='left')
        else:
            put_down(cv, xm, y_top - 0.5, nt['lines'], fs.note, colour=MUTED, ha='center')


# ===========================================================================
# The plate
# ===========================================================================
def draw():
    style()
    del WARNINGS[:]
    vals = values()
    check(vals)
    LN = lanes(*periods())

    fig = plt.figure(figsize=(W_MM / MM_PER_IN, H_MM / MM_PER_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.set_facecolor('white')
    ax.axis('off')
    ax.grid(False)
    fig.canvas.draw()
    cv = Canvas(fig, ax)

    # --- measure: the whole plate is planned before anything is drawn, and the body shrinks if the
    #     six lanes do not fit the 245 mm of the sheet ------------------------------------------
    xa, xb = X0 + 1.4, X1 - 1.4
    avail = LANES_TOP - LANES_BOT
    scale = 1.0
    while True:
        plans, lane_h = [], []
        for L_ in LN:
            rows = [plan_row(cv, r, vals, xa, xb, scale) for r in L_['rows']]
            plans.append(rows)
            lane_h.append(FS_LANE * scale * PT_MM * LINE_FACTOR + TITLE_GAP
                          + sum(p['h'] for p in rows) + ROW_GAP * (len(rows) - 1) + 1.6)
        need = sum(lane_h) + SEP_MIN * (len(LN) - 1)
        if need <= avail + TOL_MM or FS_NOTE * scale <= 6.4:
            break
        scale -= 0.01
    if need > avail + TOL_MM:
        WARNINGS.append(f'the six lanes need {need:.1f} mm in {avail:.1f} mm (body scale {scale:.2f})')

    slack = max(avail - sum(lane_h) - SEP_MIN * (len(LN) - 1), 0.0)
    sep = min(SEP_MAX, SEP_MIN + slack * 0.55 / (len(LN) - 1))
    rest = max(avail - sum(lane_h) - sep * (len(LN) - 1), 0.0)
    pad = [rest * h / sum(lane_h) for h in lane_h]

    # --- the case definition, top right ----------------------------------------------------------
    put(cv, X1, H_MM - 1.2, VARIANT_TAG, FS_VARIANT * scale, weight='bold', colour=MUTED,
        ha='right', va='top')

    # --- the six lanes, and the barrier that separates the record lanes from the rest --------------
    y = LANES_TOP
    for i, (L_, rows, h, pad_extra) in enumerate(zip(LN, plans, lane_h, pad)):
        hh = h + pad_extra
        ink, fill = LANE_INK[i], LANE_FILL[i]
        ax.add_patch(FancyBboxPatch((X0 + 0.6, y - hh + 0.6), X1 - X0 - 1.2, hh - 1.2,
                                    boxstyle='round,pad=0.6,rounding_size=1.8', fc=fill, ec=fill,
                                    lw=0.0, zorder=1))
        lh_lane = FS_LANE * scale * PT_MM * LINE_FACTOR
        put(cv, X0 + 2.4, y - 1.0 - lh_lane + FS_LANE * scale * PT_MM * 0.30, L_['title'],
            FS_LANE * scale, weight='bold', colour=ink, ha='left', va='baseline')
        yr = y - 1.0 - lh_lane - TITLE_GAP - pad_extra * 0.5
        for j, (P, row) in enumerate(zip(rows, L_['rows'])):
            draw_row(cv, P, row, xa, xb, yr, ink, f"{L_['key']}{j}")
            yr -= P['h'] + ROW_GAP
        y -= hh
        if i < len(LN) - 1:
            yb = y - sep / 2
            ax.plot([X0, X1], [yb, yb], color=EXCL_COL, lw=1.0, ls=(0, (3.0, 2.2)), zorder=4)
            if i == 2:                      # said once, between the care lanes and the denominators
                put(cv, (X0 + X1) / 2, yb, BARRIER, FS_BARRIER * scale, weight='bold',
                    colour=EXCL_COL, ha='center', va='center', zorder=7,
                    bbox=dict(boxstyle='round,pad=0.30', fc='white', ec=EXCL_COL, lw=0.7))
            y -= sep
    return fig
