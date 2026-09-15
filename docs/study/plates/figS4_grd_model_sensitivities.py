"""figS4 — sensitivity of the GRD annual percent change, redrawn from the tracked model table.

The stored plate was drawn by `figS4()` in `study/pipeline/08a_figures_grd.py`, which reads
`study/outputs/tidy/models_summary.csv`; `.gitignore` keeps that copy out of the repository. The same
table is published as `docs/study/data/models_summary.csv` (331 rows, the same model identifiers), so
the six cells are redrawn here from it, one forest per cell:

  (a) national rate models, F84 in any position     24 specifications
  (b) national rate models, principal F84           24 specifications
  (c) hospital-year models, F84 in any position     17 specifications
  (d) hospital-year models, principal F84           none — the cell says so in words
  (e) population rates, F84 in any position          4 specifications (both sexes)
  (f) population rates, principal F84                4 specifications (both sexes)

Panel (d) is not a panel that went missing. `models_summary.csv` holds no hospital-year specification
for principal F84, so the faithful redraw is the same empty cell carrying the same sentence, and the
letters are not renumbered: six cells, six letters.

Case definition `sin_rett` throughout — the F84 family without Rett syndrome — never `con_rett` and
never `autismo_F840`. Every point is the annual percent change, 100 × (exp(β) − 1), of a quasi-Poisson
log-linear model with its Wald 95% interval, read from the `apc`, `apc_lo` and `apc_hi` columns:
nothing is refitted here and no survey weight enters anywhere. The three estimands are different
estimators and are never mixed — (a) and (b) are rates per 100,000 GRD EPISODES of the model's own
panel and activity, (c) is a hospital-year model with a log(hospital episodes) offset, and (e) and (f)
are rates per 100,000 INE RESIDENTS, crude and age-standardised, for both sexes (`sex == TOTAL`).
Markers: circle for the 2019–2024 window, triangle for 2021–2024. The axis is clipped at −40 and 130
and a clipped interval is starred; on this variant no interval reaches either bound. The blue dotted
line is the base model of its own column — observed panel, all activity, no covariates, 2019–2024.

`_check_published()` parses every estimate out of the published presentation table
`docs/study/corpus/tables/E78_models_all_specifications.csv`, whose `APC % (95% CI)` column stores the
values as formatted strings such as '35.9 (30.0 to 42.1)' and '−2.4 (−20.1 to 19.2)' with a
typographic minus, and refuses to draw if any of the 73 plotted rows disagrees with the figure it
publishes.

The corpus is English only, so this plate is English only.
"""
import re
import sys
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "figS4_grd_model_sensitivities"
SOURCES = [
    "docs/study/data/models_summary.csv",
    "docs/study/corpus/tables/E78_models_all_specifications.csv",
]
MODELS, PUBLISHED = SOURCES
NOTE = ("Redraws the six cells of figS4 — the annual percent change and Wald 95% interval of the 24 "
        "national rate specifications, the 17 hospital-year specifications, the empty principal "
        "hospital-year cell and the 4 crude and age-adjusted population rates, in both code "
        "positions — from the published quasi-Poisson model table for the sin_rett case definition, "
        "checked row by row against the published specification table.")

ROOT = BASE.parent.parent          # docs/study -> docs -> repository root
VARIANT = 'sin_rett'

# Plate norm of the supplementary series: 180 x 245 mm, three rows by two columns, nothing under 6 pt.
PLATE_W_MM, PLATE_H_MM = 180.0, 245.0
FS_BASE, FS_TITLE, FS_MIN = 8.0, 9.0, 6.0
CELL_MARGIN = 2.0 / PLATE_W_MM                 # titles hang on the cell's left edge, not the axes'
TITLE_W_PT = (PLATE_W_MM / 25.4 * 72.0) / 2 - (4.0 / 25.4 * 72.0)   # half the plate, less 4 mm
XLIM = (-40.0, 130.0)
XTICKS = [-25, 0, 25, 50, 75, 100, 125]
LEGEND_ROOM = 5.5              # rows of empty space kept at the top of (a) for the plate's only key

AXIS = 'Annual percent change (%) and 95% CI'
NONE_NOTE = 'No specifications estimated for this series'
POS_TITLE = {'any': 'F84 in any position', 'principal': 'Principal F84'}
GRP_TITLE = {'rate': 'Per 100,000 GRD episodes (national)',
             'hosp': 'Hospital-year (log hospital-episodes offset)',
             'pop': 'Per 100,000 INE population (both sexes)'}
LETTER = {('rate', 'any'): 'a', ('rate', 'principal'): 'b', ('hosp', 'any'): 'c',
          ('hosp', 'principal'): 'd', ('pop', 'any'): 'e', ('pop', 'principal'): 'f'}
COLOUR = {'rate': BLUE, 'hosp': GREEN, 'pop': ORANGE}
EXPECTED = {('rate', 'any'): 24, ('hosp', 'any'): 17, ('pop', 'any'): 4,
            ('rate', 'principal'): 24, ('hosp', 'principal'): 0, ('pop', 'principal'): 4}

# Row labels, abbreviated to the width of the cell exactly as the stored plate abbreviates them.
SHORT = {'panel_observed': 'obs.', 'panel_fixed65': 'fixed 65',
         'act_all': 'all', 'act_hospitalisation': 'hosp.',
         'cov_none': 'no cov.', 'cov_depth': '+depth', 'cov_disruption': '+2020–21',
         'cov_depth_disruption': '+depth+2020–21', 'cov_hospital_fe': 'hosp. FE',
         'cov_hospital_fe_depth': 'hosp. FE+depth', 'cov_hospital_fe_disruption': 'hosp. FE+2020–21',
         'cov_hospital_ri': 'random int.', 'cov_hospital_ri_depth': 'random int.+depth',
         'cov_age': 'age-adjusted', 'crude': 'crude',
         'fam_qp_fe_cluster': 'robust SE', 'fam_ri_map': 'Laplace'}
WINDOW = {'2019-2024': '19–24', '2021-2024': '21–24'}
# the coded order of the stored plate: panel, then activity, then window, then covariates
COV_ORDER = {'cov_none': 0, 'cov_depth': 1, 'cov_disruption': 2, 'cov_depth_disruption': 3}
PANEL_ORDER = {'panel_observed': 0, 'panel_fixed65': 1}
ACT_ORDER = {'act_all': 0, 'act_hospitalisation': 1}
YEAR_ORDER = {'2019-2024': 0, '2021-2024': 1}
# the two families that earn a name of their own in the row label; the plain fixed effect does not
NAMED_FAMILY = ('fam_qp_fe_cluster', 'fam_ri_map')


# ---------------------------------------------------------------- tracked tables and their parsing
def _read(rel, **kw):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, **kw)


def _models():
    """The published model table, restricted to the case definition of the plate."""
    m = _read(MODELS)
    m = m[m.variant == VARIANT].copy()
    m['sex'] = m.sex.fillna('')
    m['years'] = m.years.astype(str)
    return m


def _rows(m, position):
    """The rows of one column of the plate, in the coded order the stored plate sorts them by.

    Three blocks, never mixed: the national rate specifications, the hospital-year specifications and
    the population rates of both sexes together. The sort keys are the coded ones (panel, activity,
    window, covariates for the rate block; panel, window, covariates, family for the hospital block;
    window then covariates for the population block), so the order does not depend on how the table
    happens to be stored.
    """
    base = m[m.position == f'pos_{position}']
    out = []

    rate = base[base.estimand == 'est_grd_rate'].copy()
    rate['_k'] = list(zip(rate.panel.map(PANEL_ORDER), rate.activity.map(ACT_ORDER),
                          rate.years.map(YEAR_ORDER), rate.covariates.map(COV_ORDER)))
    out += [('rate', r) for _, r in rate.sort_values('_k', kind='stable').iterrows()]

    hosp = base[base.estimand == 'est_grd_hospital'].copy()
    hosp['_k'] = list(zip(hosp.panel.map(PANEL_ORDER), hosp.years.map(YEAR_ORDER),
                          hosp.covariates, hosp.model_family))
    out += [('hosp', r) for _, r in hosp.sort_values('_k', kind='stable').iterrows()]

    # both sexes only: the per-sex population models of the same table belong to figS7, not here
    pop = base[(base.estimand == 'est_grd_pop') & (base.sex == 'TOTAL')].copy()
    pop['_k'] = list(zip(pop.years, pop.covariates))
    out += [('pop', r) for _, r in pop.sort_values('_k', kind='stable').iterrows()]
    return out


def _label(kind, r):
    """The abbreviated row label of the stored plate, assembled from the coded columns."""
    yrs = WINDOW[r.years]
    if kind == 'rate':
        return f'{SHORT[r.panel]} · {SHORT[r.activity]} · {SHORT[r.covariates]} · {yrs}'
    if kind == 'hosp':
        fam = f' · {SHORT[r.model_family]}' if r.model_family in NAMED_FAMILY else ''
        return f'{SHORT[r.panel]} · {SHORT[r.covariates]}{fam} · {yrs}'
    return f'{SHORT["crude"] if r.covariates == "cov_none" else SHORT[r.covariates]} · {yrs}'


def _base_apc(rows):
    """The base model of a column: observed panel, all activity, no covariates, 2019–2024."""
    for kind, r in rows:
        if (kind == 'rate' and r.panel == 'panel_observed' and r.activity == 'act_all'
                and r.covariates == 'cov_none' and r.years == '2019-2024'):
            return float(r.apc)
    raise AssertionError('no base model in this column')


def _published_apc():
    """`model_id -> (apc, lo, hi)` parsed out of the published specification table.

    The column stores the estimate as '35.9 (30.0 to 42.1)' and a negative one as
    '−2.4 (−20.1 to 19.2)' with U+2212, so the typographic minus is normalised before parsing.
    """
    t = _read(PUBLISHED, encoding='utf-8-sig')
    out = {}
    for mid, cell in zip(t['Model (identifier)'], t['APC % (95% CI)']):
        s = str(cell).replace('−', '-').replace('–', '-')
        got = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', s)]
        if len(got) == 3:
            out[str(mid)] = tuple(got)
    return out


def _check_published(columns):
    """Compare every value about to be drawn with the published presentation table of the models.

    It also checks the shape of the plate itself: 24 / 17 / 4 rows in the 'any position' column and
    24 / 0 / 4 in the principal one, the empty hospital-year cell included.
    """
    pub, bad = _published_apc(), []
    for position, rows in columns.items():
        for kind in ('rate', 'hosp', 'pop'):
            n = sum(1 for k, _ in rows if k == kind)
            if n != EXPECTED[(kind, position)]:
                bad.append(f'{kind}/{position}: {n} rows, expected {EXPECTED[(kind, position)]}')
        for kind, r in rows:
            if r.model_id not in pub:
                bad.append(f'{r.model_id}: not in the published specification table')
                continue
            want = pub[r.model_id]
            got = tuple(round(float(v), 1) for v in (r.apc, r.apc_lo, r.apc_hi))
            if got != want:
                bad.append(f'{r.model_id}: {got} vs published {want}')
    if bad:
        raise AssertionError('redraw disagrees with the published table:\n  ' + '\n  '.join(bad))


# --------------------------------------------------------------------------------- measured wrapping
_MEASURE = FigureCanvasAgg(Figure(figsize=(1, 1)))


def _width_pt(s, fs, weight='normal'):
    """Typographic width of a string in points, measured with the font it will be drawn with."""
    w, _h, _d = _MEASURE.get_renderer().get_text_width_height_descent(
        str(s), FontProperties(size=fs, weight=weight), False)
    return w * 72.0 / _MEASURE.figure.dpi


def _wrap(text, max_pt, fs, weight='normal'):
    """Fold a line by measured width, not by a character count: a title must fit ITS cell."""
    lines, cur = [], ''
    for w in str(text).split():
        trial = f'{cur} {w}'.strip()
        if cur and _width_pt(trial, fs, weight) > max_pt:
            lines.append(cur); cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return '\n'.join(lines) if lines else str(text)


# ------------------------------------------------------------------------------------------ panels
def _plate_style():
    """The house style of the supplementary plates: base 8 pt, panel title 9 pt bold, ticks 6 pt."""
    style()
    plt.rcParams.update({
        'font.size': FS_BASE, 'axes.titlesize': FS_TITLE, 'axes.titleweight': 'bold',
        'axes.labelsize': FS_BASE, 'xtick.labelsize': FS_MIN, 'ytick.labelsize': FS_MIN,
        'legend.fontsize': FS_MIN, 'lines.linewidth': 1.3, 'grid.linewidth': 0.45,
        'xtick.major.size': 2.2, 'ytick.major.size': 2.2, 'xtick.major.pad': 1.5,
        'ytick.major.pad': 1.5, 'axes.labelpad': 2.0, 'axes.titlepad': 3.0})


def _head(ax, kind, position):
    """Panel letter and title, folded to the width of the cell the panel sits in.

    Set as the axes title so the layout engine reserves the room for it; `_align_titles` then moves
    it onto the left edge of the cell, where the stored plate hangs it.
    """
    title = _wrap(f'({LETTER[(kind, position)]}) {POS_TITLE[position]} — {GRP_TITLE[kind]}',
                  TITLE_W_PT, FS_TITLE, 'bold')
    ax.set_title(title, loc='left', fontsize=FS_TITLE, fontweight='bold', pad=3.0, linespacing=1.15)
    return title


def _forest(ax, rows, kind, base, legend_room=False):
    """One forest: a point per specification, its 95% interval, and the base model of the column."""
    colour = COLOUR[kind]
    yy = np.arange(len(rows))[::-1]                    # the first specification sits at the top
    for y, (_k, r) in zip(yy, rows):
        lo, hi = float(r.apc_lo), float(r.apc_hi)
        ax.plot([max(lo, XLIM[0]), min(hi, XLIM[1])], [y, y], color=colour, lw=1.2, zorder=2)
        ax.scatter(float(r.apc), y, s=11, color=colour, zorder=3, edgecolor='white', linewidth=0.4,
                   marker='o' if r.years == '2019-2024' else '^')
        if lo < XLIM[0] or hi > XLIM[1]:               # an interval the axis cannot show is starred
            ax.text(XLIM[1] - 2, y, '*', fontsize=FS_MIN, color=colour, va='center', ha='right')
    ax.axvline(0, color='#888888', ls='--', lw=0.9, zorder=0)
    ax.axvline(base, color=BLUE, ls=':', lw=0.9, zorder=0)
    ax.set_yticks(yy)
    ax.set_yticklabels([_label(k, r) for k, r in rows], fontsize=FS_MIN)
    # a forest has no gap between its rows, so the key needs a band reserved for it on purpose
    ax.set_ylim(-0.8, len(rows) - 0.2 + (LEGEND_ROOM if legend_room else 0.0))
    ax.set_xlim(*XLIM)
    ax.set_xticks(XTICKS)
    ax.xaxis.set_major_formatter(thousands('en'))
    ax.set_xlabel(AXIS)
    clean(ax, 'x')                                     # vertical guides only: rows are not a scale


def _empty(ax):
    """The cell with no specifications: it says so in words rather than drawing a zero."""
    ax.text(0.5, 0.985, _wrap(NONE_NOTE, 120.0, FS_MIN + 0.5), transform=ax.transAxes,
            ha='center', va='top', fontsize=FS_MIN + 0.5, color='#555555', linespacing=1.25)
    ax.set_xticks([]); ax.set_yticks([])
    ax.grid(False)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


def _key(ax):
    """The plate's only key, inside (a): the two windows, the base model and the clipping mark."""
    handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor='#333333', markersize=3.6,
                      label='Window 2019–2024'),
               Line2D([0], [0], marker='^', color='w', markerfacecolor='#333333', markersize=3.6,
                      label='Window 2021–2024'),
               Line2D([0], [0], color=BLUE, ls=':', lw=0.9, label='Base model'),
               Line2D([0], [0], color='w', label='* CI clipped at axis')]
    leg = ax.legend(handles=handles, loc='upper right', fontsize=FS_MIN, ncol=2, frameon=True,
                    framealpha=1.0, edgecolor='#cccccc', facecolor='white', borderpad=0.25,
                    handlelength=1.5, handletextpad=0.5, labelspacing=0.30, columnspacing=0.9)
    leg.set_zorder(6)
    leg.set_in_layout(False)      # a key this wide would otherwise squeeze the cell that holds it
    return leg


def _fit_axis_labels(fig, axes):
    """Fold each axis label so that, centred on its axes, it stays inside its own cell.

    An axis label is centred on the AXES, not on the cell, and in this plate the row labels push the
    axes well to the right of the cell; the room the label really has is twice the smaller distance
    from the centre of the axes to the edges of the cell, not the width of the cell. Two passes: the
    fold changes the height the label asks for, which moves the axes, which the second pass measures.
    """
    for _ in range(2):
        fig.canvas.draw()
        for i, ax in enumerate(axes):
            if not ax.get_xlabel():
                continue
            cell_x0 = 0.5 * (i % 2) * fig.bbox.width
            cell_x1 = cell_x0 + 0.5 * fig.bbox.width
            box = ax.get_window_extent()
            centre = 0.5 * (box.x0 + box.x1)
            room_px = max(60.0, 2.0 * min(centre - cell_x0, cell_x1 - centre) - 6.0)
            ax.set_xlabel(_wrap(AXIS, room_px * 72.0 / fig.dpi, FS_BASE))


def _align_titles(fig, axes, heads):
    """Hang every title on the left edge of its cell, once the composition is frozen.

    Anchored to the axes, a title starts wherever the row labels let the axes start — a third of the
    way into the cell here — so the six titles would not line up and the long ones would run into the
    neighbouring cell or off the canvas. The title is set on the axes first so that the layout engine
    reserves its height, and moved onto the cell afterwards, when nothing will shift again.
    """
    pad = 3.0 / 72.0 / fig.get_figheight()
    for i, (ax, head) in enumerate(zip(axes, heads)):
        ax.set_title('', loc='left')
        fig.text(CELL_MARGIN + 0.5 * (i % 2), ax.get_position().y1 + pad, head, fontsize=FS_TITLE,
                 fontweight='bold', ha='left', va='bottom', linespacing=1.15)


# -------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six cells of figS4 and hand back the figure."""
    m = _models()
    columns = {pos: _rows(m, pos) for pos in ('any', 'principal')}
    _check_published(columns)
    base = {pos: _base_apc(rows) for pos, rows in columns.items()}

    _plate_style()
    fig, ax = plt.subplots(3, 2, figsize=(PLATE_W_MM/25.4, PLATE_H_MM/25.4), layout='constrained')
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)

    heads = []
    for i, kind in enumerate(('rate', 'hosp', 'pop')):
        for j, position in enumerate(('any', 'principal')):
            cell = ax[i, j]
            rows = [(k, r) for k, r in columns[position] if k == kind]
            if rows:
                _forest(cell, rows, kind, base[position],
                        legend_room=(kind, position) == ('rate', 'any'))
            else:
                _empty(cell)
            heads.append(_head(cell, kind, position))
    _key(ax[0, 0])

    axes = list(ax.flat)              # row-major, so the cells run a, b, c, d, e, f
    _fit_axis_labels(fig, axes)
    fig.canvas.draw()
    fig.set_layout_engine('none')     # freeze the composition, then move the titles onto their cells
    _align_titles(fig, axes, heads)
    return fig


if __name__ == '__main__':
    fig = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor='white')
    print('wrote', out)
