"""Shared style and helpers for the manuscript plates (version 10) in docs/lancet.

Adapted copy of `technical/sources/v10_figstyle.py` of revision 10: it reads the public data of
`docs/lancet/data/` and writes the plates to `docs/lancet/figures/<language>/` (PNG at 300 dpi, SVG and PDF)
with a preview and a QA record in `docs/lancet/qa/`.

Rules applied from the August 2026 Information for Authors of The Lancet Regional
Health – Americas: lowercase panel letters, no titles inside the artwork, no box
outlines, one consistent font, >=300 dpi at >=107 mm width. Plates are 175 mm wide,
exported as PNG (600 dpi), SVG and PDF, plus a 150 dpi preview in technical/qa.
"""
from pathlib import Path
import json, math
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

BASE = Path(__file__).resolve().parent          # docs/lancet
assert BASE.name == 'lancet' and BASE.parent.name == 'docs', BASE
DATA = BASE/'data'              # public copies of outputs/tidy and technical/data of revision 10
TIDY = DATA
QA = BASE/'qa'
PNG_DPI = 300
OKABE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442", "#000000"]
BLUE, ORANGE, GREEN, PINK, GOLD, SKY, YELLOW, BLACK = OKABE
GREY = '#7f7f7f'; LIGHT = '#bdbdbd'; BAND = '#e6e6e6'
LAW_YEAR = 2023 + (10 - 1) / 12 + 9 / 365   # Ley 21.545 published 10 March 2023
QA_LOG = []

def text(en, es, lang):
    return en if lang == 'en' else es

def style():
    plt.rcdefaults()
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.titlesize': 8, 'axes.labelsize': 8,
        'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5, 'legend.fontsize': 7.3, 'legend.title_fontsize': 7.3,
        'axes.linewidth': 0.7, 'grid.linewidth': 0.35, 'grid.color': '#d9d9d9', 'lines.linewidth': 1.3,
        'lines.markersize': 3.4, 'axes.labelpad': 3, 'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'axes.spines.top': False, 'axes.spines.right': False,
        'legend.frameon': False, 'axes.grid': True, 'axes.axisbelow': True, 'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.major.width': 0.7, 'ytick.major.width': 0.7, 'xtick.major.size': 3, 'ytick.major.size': 3,
        'mathtext.default': 'regular'})

def clean(ax, grid='y'):
    ax.grid(False)
    if grid in ('y', 'both'): ax.grid(True, axis='y')
    if grid in ('x', 'both'): ax.grid(True, axis='x')
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    return ax

def letter(fig, ax, ch, dx=-0.055, dy=0.012):
    """Bold lowercase letter outside the top-left corner of the axes (figure coordinates)."""
    pos = ax.get_position()
    fig.text(max(pos.x0 + dx, 0.006), pos.y1 + dy, ch, fontweight='bold', fontsize=11, ha='left', va='bottom')

def num(x, lang, dec=0):
    if x is None or (isinstance(x, float) and math.isnan(x)): return ''
    s = f'{x:,.{dec}f}'
    if lang == 'es': s = s.replace(',', ' ').replace('.', ',').replace(' ', '.')
    return s

def thousands(lang):
    return FuncFormatter(lambda v, p: num(v, lang, 0))

def shade_pandemic(ax, x0=2019.5, x1=2021.5, label=None, lang='en'):
    ax.axvspan(x0, x1, color=BAND, alpha=0.6, lw=0, zorder=0).set_gid('shade')

def law_line(ax, lang, y=0.97, label=True, x=LAW_YEAR, ha='left', color='#444444'):
    ax.axvline(x, color=color, ls=(0, (2, 2)), lw=0.8, zorder=1)
    if label:
        ax.text(x + 0.04 if ha == 'left' else x - 0.04, y,
                text('Law 21.545\n(context)', 'Ley 21.545\n(contexto)', lang), transform=ax.get_xaxis_transform(),
                fontsize=6.6, color=color, ha=ha, va='top', linespacing=1.05)

def end_label(ax, x, y, s, color, dx=4, dy=0, ha='left', size=7):
    ax.annotate(s, (x, y), xytext=(dx, dy), textcoords='offset points', ha=ha, va='center', fontsize=size,
                color=color, fontweight='bold', clip_on=False)

def year_ticks(ax, years, short=False):
    ax.set_xticks(list(years))
    ax.set_xticklabels([("’" + str(y)[2:]) if short else str(y) for y in years])

def log_axis(ax, axis='y', lang='en'):
    a = ax.yaxis if axis == 'y' else ax.xaxis
    (ax.set_yscale if axis == 'y' else ax.set_xscale)('log')
    a.set_major_formatter(FuncFormatter(lambda v, p: num(v, lang, 0) if v >= 1 else (num(v, lang, 1) if v >= 0.1 else num(v, lang, 2))))
    a.set_minor_formatter(NullFormatter())

def fisher_ci(rho, n, alpha=0.05):
    from scipy import stats
    z = np.arctanh(rho); se = 1 / math.sqrt(n - 3); q = stats.norm.ppf(1 - alpha / 2)
    return math.tanh(z - q * se), math.tanh(z + q * se)

def out_of_canvas(fig):
    """Text artists whose bounding box leaves the figure canvas (a simple QA check).
    Tick labels of ticks lying outside the axis limits are never drawn and are ignored."""
    fig.canvas.draw(); r = fig.canvas.get_renderer(); W, H = fig.bbox.width, fig.bbox.height; bad = []
    hidden = set()
    for ax in fig.axes:
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = min(lim), max(lim)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                loc = tick.get_loc()
                if loc < lo or loc > hi: hidden.update([id(tick.label1), id(tick.label2)])
    for t in fig.findobj(matplotlib.text.Text):
        if id(t) in hidden or not t.get_visible() or not t.get_text().strip(): continue
        try: bb = t.get_window_extent(r)
        except Exception: continue
        if bb.x0 < -1 or bb.y0 < -1 or bb.x1 > W + 1 or bb.y1 > H + 1: bad.append(t.get_text()[:40])
    return bad

def save(fig, name, lang):
    out = BASE/'figures'/lang; out.mkdir(parents=True, exist_ok=True); QA.mkdir(exist_ok=True)
    bad = out_of_canvas(fig)
    from overlap_qa import overlaps
    ov = overlaps(fig)
    for o in ov: print('    overlap:', o)
    sizes = sorted({round(t.get_fontsize(), 1) for t in fig.findobj(matplotlib.text.Text) if t.get_text().strip()})
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(out/f'{name}.{ext}', dpi=PNG_DPI, bbox_inches=None, facecolor='white')
    fig.savefig(QA/f'{name}_{lang}_preview.png', dpi=150, bbox_inches=None, facecolor='white')
    QA_LOG.append({'figure': name, 'language': lang, 'width_mm': round(fig.get_figwidth()*25.4, 1),
                   'height_mm': round(fig.get_figheight()*25.4, 1), 'font_sizes_pt': sizes, 'out_of_canvas': bad, 'overlaps': ov,
                   'internal_titles': False, 'panel_letters': 'lowercase'})
    plt.close(fig)
    print(f'  {name} [{lang}] {round(fig.get_figwidth()*25.4)}x{round(fig.get_figheight()*25.4)} mm; fonts {sizes[0]}–{sizes[-1]} pt; off-canvas: {len(bad)}; overlaps: {len(ov)}')

def write_qa(name):
    (QA/name).write_text(json.dumps(QA_LOG, ensure_ascii=False, indent=1))
