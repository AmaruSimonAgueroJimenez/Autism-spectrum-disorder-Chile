"""EF7 — age detail of the GRD episodes with documented F84, redrawn from the tracked tables.

The stored plate `docs/study/corpus/figures/EF7_age_detail.jpg` was drawn by `study/pipeline/` from
`outputs/tidy/grd_age_single_year.csv`, `grd_age_sex_year.csv` and the INE population file, none of
which this repository carries at episode level. Every series of its six panels survives in published
aggregates, so they are redrawn here from those:

  (a) single-year age 0–40 by sex, 2019 and 2024      `E63_grd_age_single_sex_full.csv`
  (b) rate per 100,000 by age group and year          `EF7_age_detail.csv`
  (c) male-to-female ratio pooled 2019–2024           `EF7_age_detail.csv` (M:F column)
  (d) cumulative age in 2019 and 2024, median marked  `E63_grd_age_single_sex_full.csv` + the
                                                      published 'Median age (years)' row
  (e) rate per 100,000: age group x year              `EF7_age_detail.csv`
  (f) rate by age group and sex in 2024               `grd_age_sex_year.csv` counts over the national
                                                      sum of `population_regional.csv`

Case definition and panel, unchanged from the original: `sin_rett` (F84 family without Rett
syndrome), observed hospital panel, F84 in any of the 35 diagnostic positions, all activities. The
unit is the GRD episode, not the person.

The rates of (b), (e) and (f) are **crude** rates per 100,000 population, with the numerator/
denominator mismatch the caption declares — the numerator is located by place of care (public
hospitals with GRD), the denominator by residence (INE projections, 2017 base, 30 June). The WHO
age-standardised figures of `S_grd_population_rates.csv` are a different estimator and are
deliberately not used here. Intervals are exact Poisson in (b), (e) and (f), and the delta method on
the log scale in (c).

Two things are not read off a single cell and are stated here because they are the only places where
this module computes rather than parses:

* **Panel (f)** needs sex-specific rates for all seventeen age groups, and the published
  `grd_age_hombre_2024.csv` / `grd_age_mujer_2024.csv` collapse everything above 44 into one '45+'
  row. The eight bands 45–49 … 80+ are therefore recomputed from the `grd_age_sex_year.csv` counts
  over the national sum of `population_regional.csv`, with exact Poisson intervals. `_check_sources()`
  proves the recipe by reproducing every band those two files *do* store, and their pooled 45+ row,
  to within 1e-9 per 100,000.
* **Panel (d)** needs the cumulative curve, which no table prints. It is the cumulative share of the
  episodes of known age in E63, and `_check_sources()` proves it by recovering the published 'Median
  age (years)' row — 7.9, 9.2, 9.1, 8.2, 8.6, 9.5 — as the linear interpolation of that curve at 50%,
  for all six years.

Denominators follow the original exactly and differ by panel: (a) is a within-year, within-sex
percentage, so its denominator is the sex total of the year (1,786 and 547 in 2019; 5,849 and 2,878
in 2024, the 3 male episodes of unknown age included in the total but not on the curve); (d) is over
the episodes of known age of the year (2,334 and 8,728); (b), (e) and (f) are over population.
Episodes of unknown age — 3 in 2024, 0 elsewhere — are excluded from every rate and never imputed,
and male 80+ in 2024 is a true zero, which is why the male line of (f) runs off the bottom of the log
axis at the right edge, exactly as it does in the stored plate.

`population_regional.csv` lives in `output_files/consolidacion/`; it is regional, so the national
denominator is a sum over the sixteen regions. `_check_sources()` reproduces every published rate and
interval of the companion table from that sum before anything is drawn.

The corpus is English only, so this plate is English only.
"""
import re
import sys
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, NullFormatter
from scipy.stats import chi2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "EF7_age_detail"
SOURCES = [
    "docs/study/corpus/tables/EF7_age_detail.csv",
    "docs/study/corpus/tables/E63_grd_age_single_sex_full.csv",
    "docs/study/data/grd_age_sex_year.csv",
    "docs/study/data/grd_age_hombre_2024.csv",
    "docs/study/data/grd_age_mujer_2024.csv",
    "output_files/consolidacion/population_regional.csv",
]
COMPANION, SINGLE_YEAR, AGE_SEX_YEAR, HOMBRE_2024, MUJER_2024, POPULATION = SOURCES
NOTE = ("Redraws the six panels of EF7 — single-year age by sex, the crude rate per 100,000 "
        "population by age group and year, the pooled male-to-female ratio, the cumulative age "
        "distribution with its median, the age-by-year rate heat map and the 2024 rate by age and "
        "sex — from the EF7 and E63 companion tables and from the tracked GRD age-by-sex counts over "
        "the national sum of the regional INE population, case definition sin_rett, observed panel.")

ROOT = BASE.parents[1]                  # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 210 / 25.4, 286 / 25.4     # the plate canvas of the pipeline: a full page

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
#: year colours of the stored plate, pale to dark across 2019–2024
YEAR_COLOURS = [SKY, BLUE, GREEN, YELLOW, GOLD, ORANGE]
SEXES = [('HOMBRE', 'Males', BLUE), ('MUJER', 'Females', ORANGE)]
DETAIL_YEARS = [(2019, '-.', SKY), (2024, '-', ORANGE)]   # the two years detailed in (a) and (d)
MAX_SINGLE_AGE = 40                     # panel (a) stops at 40 completed years, as the plate does
MAX_CUM_AGE = 60                        # panel (d) runs to 60
UNKNOWN_ROW = 'Unknown age (episodes)'
MEDIAN_ROW = 'Median age (years)'
RATE_LABEL = 'Per 100,000 population'
MISMATCH = 'Numerator: place of care · Denominator:\nresidence'
#: the stored plate writes the numerator/denominator note in a dark grey, not in figstyle's GREY
MISMATCH_COLOUR = '#444444'
A_YLABEL = "% of the year's and sex's\nepisodes"
AGE_LABEL = 'Age (completed years)'
HEAT_CMAP = 'YlOrRd'
HEAT_WHITE = 0.60                       # above this share of the maximum the cell label turns white
TITLES = [('(a)', 'Single-year age by sex, 2019 and 2024'),
          ('(b)', 'Rate per 100,000 population by age group\nand year'),
          ('(c)', 'Male-to-female ratio by age group'),
          ('(d)', 'Shift of the age distribution, 2019 versus\n2024'),
          ('(e)', 'Rate per 100,000 population: age group ×\nyear'),
          ('(f)', 'Rate by age and sex, 2024 (exact 95% CI)')]

#: presentation cell of the companion table: 'episodes; rate (exact Poisson 95% CI)'
CELL = re.compile(r'^([\d,]+)\s*;\s*([\d.]+)\s*\(([\d.]+)[–-]([\d.]+)\)$')
#: the M:F column: 'ratio (delta-method 95% CI)'
RATIO = re.compile(r'^([\d.]+)\s*\(([\d.]+)[–-]([\d.]+)\)$')


# ---------------------------------------------------------------- tracked tables and their parsing
def _read(rel, **kw):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, **kw)


def _int(s):
    """'1,418' -> 1418 ; the presentation tables store counts as formatted strings."""
    return int(str(s).replace(',', '').replace(' ', '').strip())


def _key(label):
    """'0–4' (the table's en dash) -> '0-4', the spelling of the tidy files and of the population."""
    return str(label).strip().replace('–', '-')


def _poisson(k, pop):
    """Rate per 100,000 and its exact Poisson 95% interval, the estimator of (b), (e) and (f).

    A zero count keeps a zero rate and a zero lower bound: it is a true zero, not a missing value,
    and it is drawn as such (on a log axis matplotlib clips it to the bottom of the panel).
    """
    k, pop = np.asarray(k, float), np.asarray(pop, float)
    lo = np.where(k > 0, chi2.ppf(0.025, 2*np.maximum(k, 1))/2, 0.0)
    hi = chi2.ppf(0.975, 2*(k + 1))/2
    return k/pop*1e5, lo/pop*1e5, hi/pop*1e5


def _companion():
    """The EF7 companion table, parsed: counts, rates, exact Poisson bounds, ratios, median age."""
    t = _read(COMPANION, encoding='utf-8-sig')
    t.columns = [c.strip() for c in t.columns]
    first, ratio_col = t.columns[0], t.columns[-1]
    rows = t[first].astype(str).str.strip().tolist()
    groups = [g for g in rows if g not in (UNKNOWN_ROW, MEDIAN_ROW)]
    t = t.set_index(first)

    n = np.zeros((len(groups), len(YEARS)), int)
    rate, lo, hi = (np.zeros((len(groups), len(YEARS))) for _ in range(3))
    for i, g in enumerate(groups):
        for j, y in enumerate(YEARS):
            m = CELL.match(str(t.loc[g, str(y)]).strip())
            n[i, j] = _int(m.group(1))
            rate[i, j], lo[i, j], hi[i, j] = (float(m.group(k)) for k in (2, 3, 4))
    ratio = np.array([[float(x) for x in RATIO.match(str(t.loc[g, ratio_col]).strip()).groups()]
                      for g in groups])
    unknown = np.array([_int(t.loc[UNKNOWN_ROW, str(y)]) for y in YEARS])
    median = np.array([float(t.loc[MEDIAN_ROW, str(y)]) for y in YEARS])
    return dict(groups=groups, n=n, rate=rate, lo=lo, hi=hi, ratio=ratio.T,
                unknown=unknown, median=median)


def _single_year():
    """E63: episodes by completed age and sex, one column per year, counts parsed out.

    Returns the ages actually reported (0–91), the per-sex counts indexed by age, and the sex totals
    of each year — the totals include the 'Age not reported' row, because panel (a) is a share of all
    the episodes of that year and sex.
    """
    e = _read(SINGLE_YEAR, encoding='utf-8-sig')
    age_col, sex_col = e.columns[0], e.columns[1]
    for c in e.columns[2:]:
        e[c] = e[c].map(_int)
    e[age_col] = e[age_col].astype(str).str.strip()
    known = e[e[age_col].str.fullmatch(r'\d+')].copy()
    known['age'] = known[age_col].astype(int)
    by_sex = {s: known[known[sex_col] == s].set_index('age') for s in e[sex_col].unique()}
    totals = {s: e[e[sex_col] == s][[str(y) for y in YEARS]].sum() for s in e[sex_col].unique()}
    return known, by_sex, totals


def _share(by_sex, totals, sex, year, ages):
    """Panel (a): episodes of one sex and year at each completed age, as a % of that sex's year."""
    counts = by_sex[sex][str(year)].reindex(ages, fill_value=0).to_numpy(float)
    return 100 * counts / totals[sex][str(year)]


def _cumulative(known, year):
    """Panel (d): ages and the cumulative % of the episodes of known age of that year, both sexes."""
    s = known.groupby('age')[str(year)].sum().sort_index()
    return s.index.to_numpy(float), 100 * s.cumsum().to_numpy(float) / s.sum()


def _median_from_cumulative(ages, cum):
    """The age at which the cumulative curve of (d) crosses 50%, linearly between two whole ages.

    This is the recipe that reproduces the published 'Median age (years)' row; `_check_sources()`
    asserts it for all six years before the plate is drawn.
    """
    i = int(np.searchsorted(cum, 50.0))
    below = cum[i-1] if i else 0.0
    return ages[i] - 1 + (50.0 - below) / (cum[i] - below)


def _population(year):
    """National population of `year` by sex and age group: the sum of the sixteen regions."""
    p = _read(POPULATION)
    return p[p.year == year].groupby(['sex', 'age_group'])['population'].sum()


def _sex_rates_2024(groups):
    """Panel (f): 2024 episodes, population, rate and exact Poisson bounds by sex and age group."""
    g = _read(AGE_SEX_YEAR)
    g = g[(g.variant == 'sin_rett') & (g.panel == 'observed') & (g.position == 'any')
          & (g.activity == 'all') & (g.year == 2024)].set_index(['sex', 'age_group'])['n_f84']
    pop = _population(2024)
    keys = [_key(x) for x in groups]
    out = {}
    for sex, _label, _colour in SEXES:
        k = np.array([int(g.loc[(sex, a)]) for a in keys], float)
        d = np.array([float(pop.loc[(sex, a)]) for a in keys])
        rate, lo, hi = _poisson(k, d)
        out[sex] = dict(n=k, population=d, rate=rate, lo=lo, hi=hi)
    return out


# ------------------------------------------------------------------------------------ verification
def _check_sources(tab, known, totals, sex_2024):
    """Prove every drawn value against a second tracked table before the figure is built.

    Five checks: the companion counts against the tidy age-by-sex counts; the companion rates and
    exact Poisson bounds against those counts over the national population sum; the M:F column
    against the pooled counts with a delta-method interval; the 2024 sex-specific rates against the
    two published `grd_age_*_2024.csv` files, the eight bands above 44 through their pooled 45+ row;
    and the E63 year totals and cumulative medians against the companion table.
    """
    bad = []
    keys = [_key(g) for g in tab['groups']]
    g = _read(AGE_SEX_YEAR)
    g = g[(g.variant == 'sin_rett') & (g.panel == 'observed') & (g.position == 'any')
          & (g.activity == 'all')]
    pooled = g.groupby(['sex', 'age_group'])['n_f84'].sum()

    for j, year in enumerate(YEARS):
        pop = _population(year)
        counts = g[g.year == year].groupby('age_group')['n_f84'].sum()
        for i, a in enumerate(keys):
            if int(counts.get(a, 0)) != tab['n'][i, j]:
                bad.append(f'{a} {year}: {counts.get(a, 0)} episodes vs published {tab["n"][i, j]}')
            d = sum(float(pop.loc[(s, a)]) for s, _l, _c in SEXES)
            rate, lo, hi = _poisson(tab['n'][i, j], d)
            for got, want, what in ((rate, tab['rate'][i, j], 'rate'), (lo, tab['lo'][i, j], 'lo'),
                                    (hi, tab['hi'][i, j], 'hi')):
                if round(float(got), 1) != want:
                    bad.append(f'{a} {year} {what}: {float(got):.3f} vs published {want}')
        if int(counts.get('unknown', 0)) != tab['unknown'][j]:
            bad.append(f'unknown age {year}: {counts.get("unknown", 0)} vs published '
                       f'{tab["unknown"][j]}')

    for i, a in enumerate(keys):
        m, f = float(pooled.loc[('HOMBRE', a)]), float(pooled.loc[('MUJER', a)])
        se = np.sqrt(1/m + 1/f)
        for got, want, what in ((m/f, tab['ratio'][0, i], 'ratio'),
                                (m/f*np.exp(-1.959964*se), tab['ratio'][1, i], 'lo'),
                                (m/f*np.exp(+1.959964*se), tab['ratio'][2, i], 'hi')):
            if round(float(got), 2) != want:
                bad.append(f'M:F {a} {what}: {float(got):.4f} vs published {want}')

    for (sex, _label, _colour), path in ((SEXES[0], HOMBRE_2024), (SEXES[1], MUJER_2024)):
        ref = _read(path).set_index('age_group')
        s = sex_2024[sex]
        for i, a in enumerate(keys):
            if a not in ref.index:
                continue
            for got, want, what in ((s['n'][i], ref.loc[a, 'count'], 'count'),
                                    (s['population'][i], ref.loc[a, 'population'], 'population'),
                                    (s['rate'][i], ref.loc[a, 'rate'], 'rate'),
                                    (s['lo'][i], ref.loc[a, 'lo'], 'lo'),
                                    (s['hi'][i], ref.loc[a, 'hi'], 'hi')):
                if abs(float(got) - float(want)) > 1e-9:
                    bad.append(f'2024 {sex} {a} {what}: {float(got)} vs published {float(want)}')
        above = [i for i, a in enumerate(keys) if a not in ref.index]     # 45–49 … 80+
        rate, lo, hi = _poisson(s['n'][above].sum(), s['population'][above].sum())
        for got, want, what in ((s['n'][above].sum(), ref.loc['45+', 'count'], 'count'),
                                (s['population'][above].sum(), ref.loc['45+', 'population'], 'pop'),
                                (rate, ref.loc['45+', 'rate'], 'rate'), (lo, ref.loc['45+', 'lo'], 'lo'),
                                (hi, ref.loc['45+', 'hi'], 'hi')):
            if abs(float(got) - float(want)) > 1e-9:
                bad.append(f'2024 {sex} 45+ {what}: {float(got)} vs published {float(want)}')

    for j, year in enumerate(YEARS):
        ages, cum = _cumulative(known, year)
        if round(_median_from_cumulative(ages, cum), 1) != tab['median'][j]:
            bad.append(f'median {year}: {_median_from_cumulative(ages, cum):.3f} vs published '
                       f'{tab["median"][j]}')
        total = sum(int(t[str(year)]) for t in totals.values())
        if total != int(tab['n'][:, j].sum() + tab['unknown'][j]):
            bad.append(f'E63 total {year}: {total} vs companion '
                       f'{int(tab["n"][:, j].sum() + tab["unknown"][j])}')

    if bad:
        raise AssertionError('redraw disagrees with the tracked tables:\n  ' + '\n  '.join(bad))


# ------------------------------------------------------------------------------------------ panels
def _log_y(ax):
    """A log y axis labelled 10^k, the powers-of-ten labels the stored plate carries in (b), (c), (f).

    `figstyle.log_axis` writes the decades out as plain numbers; this plate does not, so the default
    scientific formatter is kept and only the minor labels are silenced. Non-positive values — the
    zero rates of (b), (e) and the male 80+ of (f) — are clipped to the bottom by matplotlib's own
    log scale, which is what draws them running off the panel in the stored plate.
    """
    ax.set_yscale('log')
    ax.yaxis.set_minor_formatter(NullFormatter())


def _categorical(ax, labels):
    """The seventeen WHO age groups on the x axis, written the way the companion table writes them."""
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=90)


def _panel_single_year(ax, by_sex, totals):
    """(a) single-year age by sex, 2019 dash-dotted and 2024 solid, each within its own sex-year."""
    ages = np.arange(0, MAX_SINGLE_AGE + 1)
    for year, style_, _colour in DETAIL_YEARS:
        for sex, label, colour in SEXES:
            ax.plot(ages, _share(by_sex, totals, label, year, ages), ls=style_, color=colour,
                    lw=1.3, label=f'{year} · {label}', zorder=3)
    ax.set_xticks(np.arange(0, MAX_SINGLE_AGE + 1, 5))
    ax.set_ylim(-0.41, 12.53)          # the stored plate's headroom: the four-entry legend sits in it
    ax.set_yticks(np.arange(0, 13, 2))
    ax.set_xlabel(AGE_LABEL)
    ax.set_ylabel(A_YLABEL)
    ax.legend(loc='upper right', handlelength=2.2)
    clean(ax, 'both')


def _panel_rate_by_year(ax, tab):
    """(b) the crude rate per 100,000 by age group, one line per year, on a log axis."""
    for j, (year, colour) in enumerate(zip(YEARS, YEAR_COLOURS)):
        ax.plot(np.arange(len(tab['groups'])), tab['rate'][:, j], 'o-', color=colour, ms=3.4,
                lw=1.3, label=str(year), zorder=3)
    _log_y(ax)
    positive = tab['rate'][tab['rate'] > 0]
    ax.set_ylim(positive.min() * 0.2, tab['rate'].max() * 10)   # a decade of room for the legend
    _categorical(ax, tab['groups'])
    ax.set_xlabel('Age group')
    ax.set_ylabel(RATE_LABEL)
    ax.text(0.022, 0.016, MISMATCH, transform=ax.transAxes, fontsize=7.3, color=MISMATCH_COLOUR,
            ha='left', va='bottom', linespacing=1.2)
    ax.legend(title='Year', loc='upper left', ncol=3, columnspacing=0.75, handletextpad=0.5)
    clean(ax, 'both')


def _panel_ratio(ax, tab):
    """(c) the male-to-female ratio of episodes pooled over 2019–2024, delta-method 95% CI."""
    ratio, lo, hi = tab['ratio']
    x = np.arange(len(tab['groups']))
    ax.errorbar(x, ratio, yerr=[ratio - lo, hi - ratio], fmt='o', color=BLUE, ecolor=BLUE,
                ms=5, elinewidth=1.3, capsize=2.6, capthick=1.1, zorder=3)
    ax.axhline(1, color=BLACK, ls=':', lw=1.0, zorder=2)
    _log_y(ax)
    _categorical(ax, tab['groups'])
    ax.set_ylabel('Male:female ratio (95% CI)')
    clean(ax, 'both')


def _panel_cumulative(ax, known, median):
    """(d) the cumulative age distribution of 2019 against 2024, with the published medians marked."""
    marked = [median[YEARS.index(year)] for year, _style, _colour in DETAIL_YEARS]
    for (year, _style, colour), m in zip(DETAIL_YEARS, marked):
        ages, cum = _cumulative(known, year)
        ax.plot(ages, cum, '-', color=colour, lw=2.0, label=str(year), zorder=3)
        ax.axvline(m, color=colour, ls=':', lw=1.3, zorder=2)      # the published median of the year
    ax.axhline(50, color=GREY, ls=':', lw=1.0, zorder=2)
    ax.set_xlim(0, MAX_CUM_AGE)
    ax.set_ylim(-5, 128)               # the stored plate's headroom for the median note and legend
    ax.set_yticks(np.arange(0, 121, 20))
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.set_xlabel(AGE_LABEL)
    ax.set_ylabel('Cumulative % of episodes')
    ax.text(0.985, 0.972, f'Median: {marked[0]:.1f} → {marked[-1]:.1f} years', transform=ax.transAxes,
            ha='right', va='top', fontsize=8)
    ax.legend(loc='upper right', bbox_to_anchor=(1.0, 0.938), handlelength=1.6)
    clean(ax, 'both')


def _panel_heatmap(fig, ax, tab):
    """(e) the same rates as a heat map, age group by year, every cell labelled as the plate does."""
    rate = tab['rate']
    im = ax.imshow(rate, cmap=HEAT_CMAP, aspect='auto', vmin=0, vmax=rate.max())
    for i in range(rate.shape[0]):
        for j in range(rate.shape[1]):
            white = rate[i, j] >= HEAT_WHITE * rate.max()
            ax.text(j, i, f'{rate[i, j]:.1f}', ha='center', va='center', fontsize=7,
                    color='white' if white else BLACK,
                    bbox=None if white else dict(facecolor='white', edgecolor='none',
                                                 alpha=0.65, pad=1.1))
    ax.set_xticks(np.arange(len(YEARS)))
    ax.set_xticklabels([str(y) for y in YEARS], fontsize=8.5)
    ax.set_yticks(np.arange(len(tab['groups'])))
    ax.set_yticklabels(tab['groups'])
    ax.set_xlabel('Year')
    ax.grid(False)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    cax = fig.add_axes([0.4530, 0.0639, 0.0140, 0.1984])    # the colour bar of the stored plate
    cb = fig.colorbar(im, cax=cax, ticks=MultipleLocator(50))
    cb.set_label(RATE_LABEL)
    cb.outline.set_visible(False)
    cax.tick_params(length=0)


def _panel_sex_2024(ax, tab, sex_2024):
    """(f) the 2024 rate by age group and sex, exact Poisson 95% CI, on a log axis.

    Male 80+ is a true zero: the point is clipped to the bottom of the log axis and only its upper
    bound is visible, which is why the blue line runs off the panel at the right edge.
    """
    x = np.arange(len(tab['groups']))
    for sex, label, colour in SEXES:
        s = sex_2024[sex]
        ax.errorbar(x, s['rate'], yerr=[s['rate'] - s['lo'], s['hi'] - s['rate']], fmt='o-',
                    color=colour, ecolor=colour, ms=3.4, lw=1.3, elinewidth=1.0, capsize=2.2,
                    capthick=0.9, label=label, zorder=3)
    _log_y(ax)
    ax.set_ylim(4.5e-3, 4.0e3)         # the stored plate's limits: the legend and the note sit above
    _categorical(ax, tab['groups'])
    ax.set_ylabel(RATE_LABEL)
    ax.text(0.020, 0.986, MISMATCH, transform=ax.transAxes, fontsize=7.3, color=MISMATCH_COLOUR,
            ha='left', va='top', linespacing=1.2)
    ax.legend(loc='upper right')
    clean(ax, 'both')


# -------------------------------------------------------------------------------------------- draw
def _panel_title(fig, ax, ch, title, col):
    """Bold panel letter and title above the axes, placed as the stored plate places them."""
    line = 10.5 * 1.15 / 72 / FIG_H_IN                       # one title line, in figure fractions
    y = ax.get_position().y1
    fig.text(0.012 + 0.5*col, y + line * title.count('\n'), ch, fontweight='bold', fontsize=11,
             ha='left', va='bottom')
    fig.text(0.054 + 0.5*col, y, title, fontweight='bold', fontsize=10.5, ha='left', va='bottom',
             linespacing=1.15)


def draw():
    """Draw the six panels of EF7 and hand back the figure."""
    tab = _companion()
    known, by_sex, totals = _single_year()
    sex_2024 = _sex_rates_2024(tab['groups'])
    _check_sources(tab, known, totals, sex_2024)

    style()
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
    # axes placed as in the stored plate: two columns of three, measured off the stored image
    col_x, col_w = (0.0645, 0.6005), (0.3850, 0.3840)
    row_y, row_h = (0.71693, 0.37160, 0.03950), 0.24725
    axes = [fig.add_axes([col_x[i % 2], row_y[i // 2], col_w[i % 2], row_h]) for i in range(6)]
    for ax in axes:
        ax.tick_params(length=0)                             # the stored plate draws no tick marks

    _panel_single_year(axes[0], by_sex, totals)
    _panel_rate_by_year(axes[1], tab)
    _panel_ratio(axes[2], tab)
    _panel_cumulative(axes[3], known, tab['median'])
    _panel_heatmap(fig, axes[4], tab)
    _panel_sex_2024(axes[5], tab, sex_2024)

    for i, (ax, (ch, title)) in enumerate(zip(axes, TITLES)):
        _panel_title(fig, ax, ch, title, i % 2)
    return fig


if __name__ == '__main__':
    fig = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor='white')
    print('wrote', out)
