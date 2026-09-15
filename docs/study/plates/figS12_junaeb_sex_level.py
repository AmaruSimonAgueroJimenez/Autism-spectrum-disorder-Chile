"""figS12 — JUNAEB EVE: caregiver-reported ASD by sex and school level, 2019–2025.

Redraw of the stored plate `docs/study/corpus/figures/figS12_junaeb_sex_level.jpg`. The original was
drawn by `study/pipeline/` from the 28 de-identified JUNAEB Student Vulnerability Survey files, which
this repository does not carry. Every number the plate prints survives in one tracked presentation
table, `docs/study/corpus/tables/S12_junaeb_sex_level.csv` (52 rows: year × level × {All, Males,
Females}), so the six panels are rebuilt from it alone.

The estimator is the whole point of this plate and the table states it row by row in its `Estimator`
and `Estimable` columns; this module never mixes the two:

  2019–2022  the questionnaire has no ASD category at all. `Estimable` is 'not estimable' and the
             ASD column is an em dash. These years appear only as response counts in panel (e).
  2023       there is an ASD item but no published weight. `Estimable` is 'unweighted %', the weighted
             column is an em dash, and panel (a) reads the UNWEIGHTED percentage with its Wilson 95%
             interval — drawn as hollow hatched bars and labelled UNWEIGHTED, as the stored plate does.
  2024       weighted with the EXP_REG weight; panel (b) reads the WEIGHTED column. Grade 9 is
             'not estimable' because the ASD variable of that file is entirely empty: it is drawn as
             three hatched markers at the foot of the axis, never as a zero bar.
  2025       weighted with the EXP weight; panel (c) reads the WEIGHTED column.

Panel (d) is the male-to-female ratio of the same percentages — unweighted for 2023, weighted for
2024 and 2025, exactly as the original — with an approximate 95% interval by the delta method on the
log scale. The table publishes intervals rather than standard errors, so the design SE of each
sex-specific percentage is recovered as (upper − lower) / (2 × 1.96) from the printed interval; the
published intervals are near-symmetric, so this returns the SE to three significant figures. The
ratios themselves reproduce the labels of the stored plate to ±0.01, because the table stores the
percentages rounded to two decimals while the original divided the unrounded estimates (2023 Grade 5:
4.34 / 1.36 = 3.19 here against 3.18 printed).

Panel (e) is the response count by level and year with the reported ASD count written above each bar,
and panel (f) is the weighted against the unweighted percentage for the rows the table marks
estimable, with the identity diagonal.

These are caregiver-reported proportions in selected school cohorts (pre-school NT1–NT2, Grade 1,
Grade 5 and Grade 9), not national prevalence, and the case definition is the F84 family without the
Rett variant — identical in both variants, as the table's own note records.

The corpus is English only, so this plate is English only: there is no `lang` parameter and no Spanish
variant. The Spanish strings that do appear (`1º básico`, `5º básico`, `1º medio`, `NT1–NT2`) are the
official Chilean names of the school levels, quoted inside English labels, and they are the table's
own row keys.

Panel geometry, the shared 0–16 % scale of (a)–(c) and the positions of the value labels that the
stored plate nudges clear of a neighbouring marker are read off the stored plate and kept as named
layout constants; every plotted value comes from the table.
"""
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "figS12_junaeb_sex_level"
SOURCES = ["docs/study/corpus/tables/S12_junaeb_sex_level.csv"]
NOTE = ("Redraws the six panels of Figure S12 — the 2023 unweighted percentage with its Wilson "
        "interval, the 2024 (EXP_REG) and 2025 (EXP) weighted percentages, the male:female ratio "
        "with a log-delta interval, the response and ASD counts 2019–2025 and the weighted against "
        "unweighted scatter — from the published JUNAEB table S12, keeping each year on the "
        "estimator that table declares and drawing the not-estimable cells as hatched markers.")

ROOT = BASE.parent.parent                       # docs/study -> docs -> repository root
TABLE = SOURCES[0]

LEVELS = ['Pre-school (NT1–NT2)', 'Grade 1 (1º básico)', 'Grade 5 (5º básico)', 'Grade 9 (1º medio)']
LEVEL_COLOUR = dict(zip(LEVELS, [BLUE, ORANGE, GREEN, PINK]))
ALL_GREY = '#333333'                            # the 'All' series of the stored plate
SEXES = [('Males', BLUE), ('Females', ORANGE), ('All', ALL_GREY)]
YEARS = list(range(2019, 2026))
RATIO_YEARS = [(2023, BLUE, 'o', '2023 (unweighted %)'), (2024, ORANGE, 's', '2024'),
               (2025, GREEN, 'D', '2025')]
DARK_RED = '#8b0000'                            # the 'not estimable' notes of the stored plate
EM_DASH = '—'
Z = 1.959963985                                 # 95% normal quantile: SE = (hi - lo) / (2 Z)

# ---- layout constants read off the stored plate (they carry no estimate) -------------------------
PCT_TOP = 16.35        # the shared percentage scale of panels (a), (b) and (c)
BAR_W, BAR_DODGE = 0.25, 0.27          # bar width and sex offset within a level
NE_W, NE_H = 0.16, 0.70                # the hatched 'not estimable' bars of panel (b)
NE_D = (0.17, 0.06, 0.38)              # width, foot and height of the same marker in panel (d)
LEVEL_W = 12           # characters per line of a wrapped level tick label
COUNT_W, COUNT_DODGE = 0.164, 0.20     # bar width and level offset within a year in panel (e)
COUNT_TOP = 521.0      # thousands: the y limit of panel (e), which has to hold two rows of labels
COUNT_LOW, COUNT_HIGH = 6, 36          # points above the tallest bar of the year: the two label rows
LABEL_UP, LABEL_DOWN = 9, -2           # points above the interval / below it, for a value label
VALUE_FS = 7.5         # the value labels, the not-estimable notes and the point labels of (f)
AXIS_FS, AXIS_PAD = 9.3, 3.0           # the stored plate sets its axis labels larger than figstyle
RATIO_X = (-0.61, 3.752)               # the x limits panel (d) uses, a little wider than (a)-(c)
RATIO_DODGE = 0.22                     # year offset within a level in panel (d)
RATIO_MS, SCATTER_MS = 5.5, 7.7        # marker size of panels (d) and (f) in the stored plate
SCATTER_PAD = 1.25     # panel (f) axis limit as a multiple of the largest percentage drawn
# panel (d): the two labels the stored plate moves under their marker to clear the 2024 point
RATIO_BELOW = {(2025, 'Pre-school (NT1–NT2)'), (2025, 'Grade 5 (5º básico)')}
# panel (f): one label per estimable level x year, anchored on that cell's Males point. The stored
# plate dodges them away from the crowded middle of the diagonal; the offsets are in axis units.
SCATTER_LABEL = {(2024, 'Pre-school (NT1–NT2)'): (-0.40, -0.79),
                 (2024, 'Grade 1 (1º básico)'): (-0.39, 0.03),
                 (2024, 'Grade 5 (5º básico)'): (0.84, 1.14),
                 (2025, 'Pre-school (NT1–NT2)'): (-0.46, 0.02),
                 (2025, 'Grade 1 (1º básico)'): (-0.53, -0.61),
                 (2025, 'Grade 5 (5º básico)'): (-0.07, -6.23),
                 (2025, 'Grade 9 (1º medio)'): (1.54, 1.73)}
# axes boxes of the stored plate (figure fractions), two columns by three rows
COL = [(0.055, 0.4365), (0.559, 0.4370)]
ROW = [(0.70610, 0.26157), (0.36885, 0.26231), (0.03233, 0.26157)]
TITLES = ['JUNAEB 2023: ASD by sex and level\n(UNWEIGHTED)',
          'JUNAEB 2024: weighted ASD (EXP_REG)',
          'JUNAEB 2025: weighted ASD (EXP)',
          'Male:female ratio of ASD % by level and\nyear',
          'Surveyed students (unweighted n) by level\nand year',
          'Weighted vs unweighted, 2024–2025']
GRADE9_NOTE = 'Grade 9 2024: ASD variable\nentirely empty → not\nestimable'
NOT_ESTIMABLE = 'not estimable'


# --------------------------------------------------------- the tracked table and its presentation
def _blank(cell):
    """True for the em dash the table writes where a quantity does not exist."""
    return str(cell).strip() in ('', EM_DASH, '-', 'nan', 'None')


def _count(cell):
    """'217,506' -> 217506 ; the em dash of a year without an ASD item -> None.

    Thousands are grouped with a comma in this table; the narrow no-break space is stripped too,
    because it is what the Spanish-language exports of the same pipeline use.
    """
    if _blank(cell):
        return None
    return int(str(cell).replace(',', '').replace(' ', '').replace(' ', '').strip())


def _pct(cell):
    """'4.17 (4.07 to 4.26)' -> (4.17, 4.07, 4.26) ; the em dash -> (nan, nan, nan)."""
    if _blank(cell):
        return (np.nan, np.nan, np.nan)
    point, interval = str(cell).split('(')
    lo, hi = interval.rstrip(') ').split(' to ')
    return (float(point), float(lo), float(hi))


def load():
    """The published JUNAEB table with every presentation cell parsed into numbers.

    One row per year x level x sex, carrying the response count, the reported ASD count, the
    unweighted percentage with its Wilson interval, the weighted percentage with its interval, the
    name of the weight and the estimability state that the table itself declares.
    """
    t = pd.read_csv(ROOT/TABLE, encoding='utf-8-sig')
    u = t['Unweighted % (Wilson 95% CI)'].map(_pct)
    w = t['Weighted % (95% CI)'].map(_pct)
    return pd.DataFrame({
        'year': t.Year.astype(int),
        'level': t.Level.astype(str),
        'sex': t.Sex.astype(str),
        'n': t['Students with a response (n)'].map(_count),
        'asd': t['Reported ASD (n)'].map(_count),
        'u': [v[0] for v in u], 'u_lo': [v[1] for v in u], 'u_hi': [v[2] for v in u],
        'w': [v[0] for v in w], 'w_lo': [v[1] for v in w], 'w_hi': [v[2] for v in w],
        'estimator': t.Estimator.astype(str).str.strip(),
        'estimable': t.Estimable.astype(str).str.strip()})


def cell(d, year, level, sex):
    """The single row of the table for one year, level and sex, or None where the table has none."""
    m = d[(d.year == year) & (d.level == level) & (d.sex == sex)]
    return m.iloc[0] if len(m) else None


def _estimable(row):
    """True where the table says the percentage of that cell exists at all."""
    return row is not None and row.estimable != 'not estimable'


def _se(lo, hi):
    """The design SE behind a published 95% interval, (hi - lo) / (2 x 1.96).

    The table prints intervals, not standard errors; its weighted intervals are near-symmetric, so
    this recovers the SE the original used for the delta-method ratio to three significant figures.
    """
    return (hi - lo) / (2 * Z)


def ratio(male, female, column):
    """Male:female ratio of two percentages with an approximate 95% CI, delta method on log scale.

    `column` is 'u' for the unweighted percentage (2023, the year with no published weight) or 'w'
    for the weighted one (2024 and 2025) — the estimator never changes inside a year.
    """
    pm, pf = male[column], female[column]
    sm = _se(male[column + '_lo'], male[column + '_hi'])
    sf = _se(female[column + '_lo'], female[column + '_hi'])
    r = pm / pf
    se_log = float(np.sqrt((sm / pm) ** 2 + (sf / pf) ** 2))
    return r, r * np.exp(-Z * se_log), r * np.exp(Z * se_log)


def _column(year):
    """'u' where the table declares the year unweighted, 'w' where it names a weight."""
    return 'u' if year == 2023 else 'w'


# --------------------------------------------------------------------------- shared panel drawing
def _level_ticks(ax):
    """Level names on the x axis, wrapped over two lines as the stored plate wraps them."""
    ax.set_xticks(range(len(LEVELS)))
    ax.set_xticklabels([textwrap.fill(s, LEVEL_W) for s in LEVELS], linespacing=1.15)


def _value(ax, x, hi, lo, s, colour, below=False):
    """A value label above the interval, or under it where the stored plate moves it down."""
    if below:
        ax.annotate(s, (x, lo), xytext=(0, LABEL_DOWN), textcoords='offset points', ha='center',
                    va='top', fontsize=VALUE_FS, color=colour)
    else:
        ax.annotate(s, (x, hi), xytext=(0, LABEL_UP), textcoords='offset points', ha='center',
                    va='bottom', fontsize=VALUE_FS, color=colour)


def _percent_panel(ax, d, year, column, hollow):
    """(a), (b), (c): the percentage by sex and level for one year, on that year's own estimator.

    `hollow` draws the bars as the stored plate draws 2023 — white with a hatched coloured outline,
    the visual mark that the year carries no published weight.
    """
    for i, (sex, colour) in enumerate(SEXES):
        pos, val, err, missing = [], [], [[], []], []
        for k, level in enumerate(LEVELS):
            row = cell(d, year, level, sex)
            if not _estimable(row) or pd.isna(row[column]):
                missing.append(k + (i - 1) * BAR_DODGE)
                continue
            p, lo, hi = row[column], row[column + '_lo'], row[column + '_hi']
            pos.append(k + (i - 1) * BAR_DODGE)
            val.append(p)
            err[0].append(p - lo); err[1].append(hi - p)
            _value(ax, pos[-1], hi, lo, num(p, 'en', 1), colour)
        style_kw = (dict(facecolor='white', edgecolor=colour, hatch='//', linewidth=1.1)
                    if hollow else dict(color=colour))
        ax.bar(pos, val, BAR_W, label=sex, yerr=err, ecolor=ALL_GREY, capsize=2,
               error_kw=dict(elinewidth=1.0, capthick=1.0, zorder=4), zorder=3, **style_kw)
        # a cell the table calls not estimable: a hatched marker at the foot of the axis, not a zero
        ax.bar(missing, [NE_H] * len(missing), NE_W, facecolor='white', edgecolor=colour,
               hatch='//', linewidth=1.0, zorder=3)
    for k, level in enumerate(LEVELS):
        if not _estimable(cell(d, year, level, 'All')):
            ax.annotate(NOT_ESTIMABLE, (k, NE_H), xytext=(0, 4), textcoords='offset points',
                        ha='center', va='bottom', fontsize=VALUE_FS, color=DARK_RED)
    ax.set_ylim(0, PCT_TOP)
    ax.set_yticks(range(0, 17, 2))
    _level_ticks(ax)
    ax.legend(loc='upper right', frameon=True, facecolor='white', framealpha=1,
              handlelength=1.6, handletextpad=0.6, labelspacing=0.25, borderaxespad=0.5)
    clean(ax, 'y')


def _ratio_panel(ax, d):
    """(d): the male:female ratio of the percentage of each year, with a log-delta interval."""
    for j, (year, colour, marker, label) in enumerate(RATIO_YEARS):
        column = _column(year)
        first, missing = True, []
        for k, level in enumerate(LEVELS):
            male, female = cell(d, year, level, 'Males'), cell(d, year, level, 'Females')
            if not (_estimable(male) and _estimable(female)):
                missing.append(k)
                continue
            r, lo, hi = ratio(male, female, column)
            x = k + (j - 1) * RATIO_DODGE
            ax.errorbar([x], [r], yerr=[[r - lo], [hi - r]], fmt=marker, color=colour, ecolor=colour,
                        ms=RATIO_MS, elinewidth=1.1, capsize=2.4, capthick=1.1, zorder=4,
                        markerfacecolor='white' if year == 2023 else colour,
                        markeredgewidth=1.6 if year == 2023 else 0.8,
                        label=label if first else None)
            first = False
            _value(ax, x, hi, lo, num(r, 'en', 2), colour,
                   below=(year, level) in RATIO_BELOW)
        for k in missing:                       # 2024 Grade 9: no ASD variable, so no ratio
            w, foot, height = NE_D
            ax.bar([k], [height], w, bottom=foot, facecolor='white', edgecolor=colour, hatch='//',
                   linewidth=1.0, zorder=3)
            ax.annotate(NOT_ESTIMABLE, (k, foot + height), xytext=(0, 4),
                        textcoords='offset points', ha='center', va='bottom', fontsize=VALUE_FS,
                        color=DARK_RED)
    ax.axhline(1, color=GREY, ls=(0, (5, 3)), lw=1.1, zorder=1)
    ax.set_xlim(*RATIO_X)
    ax.set_ylim(0, 7.21)
    ax.set_yticks(range(0, 5))
    _level_ticks(ax)
    ax.set_ylabel('M:F ratio (approximate 95% CI, log-delta)')
    ax.legend(loc='upper right', frameon=True, facecolor='white', framealpha=1,
              handletextpad=0.6, labelspacing=0.25, borderaxespad=0.5)
    clean(ax, 'y')


def _counts_panel(ax, d):
    """(e): students with a response by level and year, with the reported ASD count above the bar."""
    tallest = {}
    for i, level in enumerate(LEVELS):
        pos, val = [], []
        for year in YEARS:
            row = cell(d, year, level, 'All')
            if row is None or pd.isna(row.n):
                continue
            pos.append(YEARS.index(year) + (i - 1.5) * COUNT_DODGE)
            val.append(row.n / 1000)
            tallest[year] = max(tallest.get(year, 0), row.n / 1000)
        ax.bar(pos, val, COUNT_W, color=LEVEL_COLOUR[level], label=level, zorder=3)
    for i, level in enumerate(LEVELS):
        for year in YEARS:
            row = cell(d, year, level, 'All')
            if row is None or pd.isna(row.asd):
                continue                        # 2019–2022 and 2024 Grade 9: no ASD count to write
            x = YEARS.index(year) + (i - 1.5) * COUNT_DODGE
            ax.annotate(num(row.asd, 'en', 0), (x, tallest[year]),
                        xytext=(0, COUNT_LOW if i % 2 == 0 else COUNT_HIGH),
                        textcoords='offset points', rotation=90, ha='center', va='bottom',
                        fontsize=VALUE_FS, color=LEVEL_COLOUR[level])
    ax.text(0.0114, 0.826, 'reported ASD (n)  ↑', transform=ax.transAxes, ha='left', va='center',
            fontsize=8.2, color=GREY)
    ax.set_ylim(0, COUNT_TOP)
    ax.yaxis.set_major_locator(MultipleLocator(100))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, 'en', 0)))
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.set_xlabel('Year')
    ax.set_ylabel('Students with a response (thousands)')
    ax.legend(loc='upper right', ncol=2, frameon=True, facecolor='white', framealpha=1,
              handlelength=1.3, handletextpad=0.6, columnspacing=1.2, labelspacing=0.2,
              borderaxespad=0.4)
    clean(ax, 'y')


def _scatter_panel(ax, d):
    """(f): the weighted against the unweighted percentage of every estimable 2024–2025 cell."""
    top = 0.0
    for sex, colour in SEXES:
        xs, ys = [], []
        for year in (2024, 2025):
            for level in LEVELS:
                row = cell(d, year, level, sex)
                if not _estimable(row) or pd.isna(row.w) or pd.isna(row.u):
                    continue
                xs.append(row.u); ys.append(row.w)
                top = max(top, row.u, row.w)
        ax.plot(xs, ys, 'o', color=colour, ms=SCATTER_MS, mew=0, label=sex, zorder=3)
    lim = SCATTER_PAD * top
    ax.plot([0, lim], [0, lim], ls=(0, (5, 3)), color=GREY, lw=1.1, label='identity', zorder=2)
    for (year, level), (dx, dy) in SCATTER_LABEL.items():
        row = cell(d, year, level, 'Males')      # one label per estimable level x year
        ax.annotate(f'{level} {year}', (row.u + dx, row.w + dy), ha='right', va='center',
                    fontsize=VALUE_FS)
    ax.set_xlim(-0.05, lim)
    ax.set_ylim(0, lim)
    ax.set_xticks(range(0, 15, 2)); ax.set_yticks(range(0, 15, 2))
    ax.set_xlabel('Unweighted %')
    ax.set_ylabel('Weighted %')
    ax.legend(loc='upper left', frameon=True, facecolor='white', framealpha=1, handletextpad=0.6,
              labelspacing=0.25, borderaxespad=0.5)
    clean(ax, 'both')


# ------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of Figure S12 and hand back the figure."""
    d = load()
    style()
    plt.rcParams.update({'axes.labelsize': AXIS_FS, 'axes.labelpad': AXIS_PAD})
    fig = plt.figure(figsize=(210/25.4, 286/25.4))       # the stored plate is a full page
    axes = [fig.add_axes([COL[i % 2][0], ROW[i // 2][0], COL[i % 2][1], ROW[i // 2][1]])
            for i in range(6)]

    _percent_panel(axes[0], d, 2023, 'u', hollow=True)
    axes[0].set_ylabel('Unweighted % (Wilson 95% CI)')
    _percent_panel(axes[1], d, 2024, 'w', hollow=False)
    axes[1].set_ylabel('Weighted % (95% CI)')
    axes[1].text(0.407, 0.978, GRADE9_NOTE, transform=axes[1].transAxes, ha='right', va='top',
                 ma='right', fontsize=VALUE_FS, color=DARK_RED, linespacing=1.15)
    _percent_panel(axes[2], d, 2025, 'w', hollow=False)
    axes[2].set_ylabel('Weighted % (95% CI)')
    _ratio_panel(axes[3], d)
    _counts_panel(axes[4], d)
    _scatter_panel(axes[5], d)

    for i, (ax, title) in enumerate(zip(axes, TITLES)):
        pos = ax.get_position()
        fig.text(COL[i % 2][0] - 0.045, pos.y1 + 0.0022, f'({"abcdef"[i]}) {title}',
                 fontweight='bold', fontsize=10.5, ha='left', va='bottom', linespacing=1.05)
    return fig


if __name__ == '__main__':
    figure = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=121, facecolor='white')
    print('wrote', out)
