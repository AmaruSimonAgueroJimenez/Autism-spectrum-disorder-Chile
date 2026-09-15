"""EF3 — administrative features of the hospital episodes, F84 against all GRD episodes.

Redraw of the stored plate `docs/study/corpus/figures/EF3_episode_features.jpg`. The original was
drawn by `study/pipeline/` from the GRD microdata, which this repository does not carry; the six
panels are rebuilt here from the published companion table `EF3_episode_features.csv`, which prints
every category of every plotted variable with its two counts.

What the panels show, unchanged from the original: for each register field, the share of episodes
falling in each category, for episodes with a documented F84 in any diagnostic position (2019–2024
pooled, observed panel, sin_rett) and for all GRD episodes of the same panel and period. Percentages
are within-cell, so the categories of a panel add to 100%; 'Not reported' and 'Not identified' are
categories of their own and are drawn as such. The number printed beside each pair is the difference
in percentage points, F84 minus all GRD.

Two things the table does not store and that this module recomputes, exactly as the plate did them:
the percentages themselves (the printed cells are rounded to one decimal, and the plate's labels only
come out right — '−0.0' for 'Not identified' in panel a, '−32.8' for the pooled specialties in panel
f — when the shares are recomputed from the counts and their cell denominator), and the pooled
'Other categories' bar, which the plate adds when a variable has more than eight categories by
keeping the seven most frequent F84 categories and summing the counts of the rest.

The field names of the source register (TIPO_INGRESO, TIPO_ACTIVIDAD, TIPO_PROCEDENCIA, TIPOALTA,
PREVISION_grouped, ESPECIALIDAD_MEDICA) are the table's own row keys; the plate, like the table,
prints only English category labels, and so does this module.
"""
import re

import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator
from figstyle import *

PLATE = "EF3_episode_features"
SOURCES = ["docs/study/corpus/tables/EF3_episode_features.csv"]
NOTE = ("Redraws the six episode-feature panels of EF3 from the published EF3 companion table: the "
        "within-cell share of each register category among documented F84 episodes and among all GRD "
        "episodes, 2019–2024 pooled, with the percentage-point difference beside each pair.")

TABLE = BASE / "corpus" / "tables" / "EF3_episode_features.csv"

#: (row key of the table, panel heading of the plate), in the plate's panel order a–f.
PANELS = [("TIPO_INGRESO", "Type of admission"),
          ("TIPO_ACTIVIDAD", "Type of activity"),
          ("TIPO_PROCEDENCIA", "Provenance"),
          ("TIPOALTA", "Type of discharge"),
          ("PREVISION_grouped", "Insurance (tramo)"),
          ("ESPECIALIDAD_MEDICA", "Medical specialty")]

KEEP = 7            # named categories kept per panel before the rest are pooled
POOLED = 'Other categories (pooled) ({})'
WRAP = 24           # characters per line of a category label
GREY_BAR = '0.6'    # the comparison series of the plate: a mid grey, lighter than figstyle's GREY
F84_LABEL = 'Episodes with\ndocumented F84'
ALL_LABEL = 'All GRD episodes'


def _count(cell):
    """Count out of a presentation cell such as '8,221 (731)' or '16,705 (66.0%)'."""
    return int(str(cell).split('(')[0].replace(',', '').replace(' ', '').strip())


def _wrap(s, width=WRAP):
    """A register category label as the plate writes it: at most two lines, the overflow of the
    second cut off with an ellipsis. The pooled row is not a register category and is left alone."""
    if s.startswith(POOLED.split('(')[0]):
        return s
    words, line, i = s.split(), '', 0
    while i < len(words) and len((line + ' ' + words[i]).strip()) <= width:
        line = (line + ' ' + words[i]).strip(); i += 1
    if not line:                              # a first word longer than the line
        line, i = words[0], 1
    rest = ' '.join(words[i:])
    if not rest:
        return line
    return line + '\n' + (rest if len(rest) <= width else rest[:width - 1] + '…')


def load():
    """The EF3 companion table with the two counts of every category parsed out."""
    t = pd.read_csv(TABLE, encoding='utf-8-sig')
    f84 = next(c for c in t.columns if c.startswith('Documented F84'))
    whole = next(c for c in t.columns if c.startswith('All GRD'))
    return t.assign(n_f84=t[f84].map(_count), n_all=t[whole].map(_count))


def panel_rows(t, var):
    """Label, % of F84 episodes and % of all GRD episodes, for one panel of the plate.

    The categories are ranked by their F84 count; past the eighth the plate pools them, and the
    pooled bar is the sum of the counts, not the sum of the rounded percentages.
    """
    d = t[t.Variable == var].sort_values('n_f84', ascending=False, kind='stable')
    n_f84, n_all = d.n_f84.sum(), d.n_all.sum()
    rows = [(c, f, a) for c, f, a in zip(d.Category, d.n_f84, d.n_all)]
    if len(rows) > KEEP + 1:
        rest = d.iloc[KEEP:]
        rows = rows[:KEEP] + [(POOLED.format(len(rest)), rest.n_f84.sum(), rest.n_all.sum())]
    return [(c, 100 * f / n_f84, 100 * a / n_all) for c, f, a in rows]


def _diff(pp):
    """The plate's difference label: an explicit sign, one decimal, a true minus sign."""
    return ('+' if pp >= 0 else '−') + num(abs(pp), 'en', 1)


def draw():
    style()
    t = load()
    fig, axes = plt.subplots(3, 2, figsize=(6.89, 9.38))
    fig.subplots_adjust(left=0.2245, right=0.992, top=0.9794, bottom=0.0338, wspace=0.924, hspace=0.232)
    for k, ((var, heading), ax) in enumerate(zip(PANELS, axes.ravel())):
        rows = panel_rows(t, var)
        y = np.arange(len(rows))
        f84 = np.array([r[1] for r in rows])
        whole = np.array([r[2] for r in rows])
        ax.barh(y - 0.2, f84, height=0.4, color=BLUE, label=F84_LABEL)
        ax.barh(y + 0.2, whole, height=0.4, color=GREY_BAR, label=ALL_LABEL)
        for yi, f, a in zip(y, f84, whole):
            ax.annotate(_diff(f - a), (max(f, a), yi), xytext=(2, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=6.3, color=BLACK)
        ax.set_xlim(0, 1.24 * max(f84.max(), whole.max()))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 2.5, 5, 10]))
        ax.set_yticks(y)
        ax.set_yticklabels([_wrap(r[0]) for r in rows], fontsize=6.9)
        ax.invert_yaxis()
        ax.set_xlabel('% of episodes', fontsize=7.8, labelpad=1)
        clean(ax, grid='x')
        ax.tick_params(axis='both', length=0)
        pos = ax.get_position()
        x0 = 0.011 + 0.5 * (k % 2)
        top = pos.y1 + 1.5 / 72 / fig.get_figheight()
        fig.text(x0, top, f'({"abcdef"[k]})', fontweight='bold', fontsize=9, ha='left', va='bottom')
        fig.text(x0 + 0.041, top, heading, fontweight='bold', fontsize=9, ha='left', va='bottom')
    leg = axes[0, 0].legend(loc='lower right', fontsize=6.8, handlelength=1.2, handletextpad=0.55,
                            labelspacing=0.35, borderpad=0.2, borderaxespad=0.4)
    for txt in leg.get_texts():
        txt.set_linespacing(1.1)
    return fig
