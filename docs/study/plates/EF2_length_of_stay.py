"""EF2 — length of stay of the GRD episodes with documented F84, redrawn from the tracked tables.

The stored plate `docs/study/corpus/figures/EF2_length_of_stay.jpg` came from
`study/pipeline/11_grd_episode_detail.py`, which reads discharge microdata this repository does not
hold. Every series it draws survives in published aggregates, so the six panels are redrawn here from
those:

  (a) median and P25–P75 by year and code position   `docs/study/data/grd_length_of_stay.csv`
  (b) pooled 2019–2024 mean and 2024 median by age   `docs/study/corpus/tables/E66_grd_length_of_stay_full.csv`
  (c) 90th percentile of stay by year                `docs/study/data/grd_length_of_stay.csv`
  (d) episodes with a zero-day stay (%)              `docs/study/data/grd_length_of_stay.csv`
  (e) distribution by stay band in 2024              `docs/study/corpus/tables/E4_grd_episode_features.csv`
  (f) episodes and median days by activity           `docs/study/data/grd_length_of_stay.csv`

The unit is the GRD episode and the case definition is `sin_rett` (the F84 family without F84.2,
Rett syndrome) on the `observed` hospital panel — not `fixed65`, and not `con_rett`,
`TEA_operacional`, `F84_historico` or `autismo_F840`, which are different definitions and give
different counts (2024: 7,616 episodes against 7,421 on the fixed panel and 7,702 with Rett).
`output_files/consolidacion/grd_epi_los.csv` is deliberately not read: it carries no all-GRD
comparison series and its definitions are not this plate's.

The denominator of every statistic is `n_valid_dates`, episodes with two parsable dates and a
discharge on or after the admission. Episodes with unparsable dates are counted in `n_invalid_dates`,
reported in the companion table as the '(+3)' of '7,616 (+3)', excluded from every statistic and
never imputed. Panels (a), (b) and (c) are hospitalisation only; (d) shows all activities and
hospitalisation only side by side, because major ambulatory surgery is a zero-day stay by definition
and would otherwise swamp the comparison; (f) separates the activities outright.

Two things the tables do not store as such and that this module recomputes, exactly as the plate did:

  * the pooled bars of (b). E66 prints, per age group and per year, 'n; median (IQR); mean' — six
    per-year means rounded to one decimal, not a pooled one. The bar is their n-weighted average, so
    the weighting has to be done here: for documented F84 at 80+ that is
    (1×37.0 + 1×2.0 + 3×7.3 + 3×11.7 + 7×31.9)/15 = 21.3 days, the longest blue bar of the panel.
    Averaging the six printed means unweighted would give 18.0 and a visibly shorter bar. Years the
    table prints as 'n/e' carry no episodes and drop out of both sums; documented F84 has no episode
    of unreported age in any year, which is why that row of (b) carries only the grey bar.
  * the percentages and the difference labels of (e), which are recomputed from the counts and their
    column totals rather than taken from the rounded percentages the table prints: the 15–30 band is
    687/8,731 against 67,641/1,085,813, that is 7.87% against 6.23% and the printed '+1.6'.

Panel (e) compares 2024 against all GRD episodes of 2024 because that is the only year the source
carries an all-GRD column; the panel plots that single year and is complete as it stands.

`_check_published()` reads the presentation table of the plate,
`docs/study/corpus/tables/EF2_length_of_stay.csv`, and compares every median, quartile, P90,
zero-day count, zero-day percentage and episode count that (a), (c), (d) and (f) will draw against
the published cell before the figure is built; the age blocks of (b) and the bands of (e) are
checked against their own tables' totals.

The corpus is English only, so this plate is English only.
"""
import sys
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "EF2_length_of_stay"
SOURCES = [
    "docs/study/data/grd_length_of_stay.csv",
    "docs/study/corpus/tables/E66_grd_length_of_stay_full.csv",
    "docs/study/corpus/tables/E4_grd_episode_features.csv",
    "docs/study/corpus/tables/EF2_length_of_stay.csv",
]
LOS, AGE, FEATURES, PUBLISHED = SOURCES
NOTE = ("Redraws the six panels of EF2 — median and P25–P75 by code position, pooled mean and 2024 "
        "median by WHO age group, the 90th percentile, the zero-day share across all activities and "
        "for hospitalisation only, the 2024 stay bands against all GRD episodes, and episodes and "
        "median days by activity — from the published GRD length-of-stay, age and episode-feature "
        "tables, on the sin_rett definition and the observed hospital panel, with n_valid_dates as "
        "the denominator of every statistic.")

ROOT = BASE.parent.parent          # docs/study -> docs -> repository root
VARIANT, PANEL = 'sin_rett', 'observed'
ALL_GRD = 'all_episodes'           # every GRD episode of the same year, panel and activity
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
BAND_YEAR = 2024                   # the only year (e) can compare: E4 carries one all-GRD column

BAR_GREY = '0.6'                   # the comparison bars of (b) and (e)
DARK = '#555555'                   # all GRD, hospitalisation only: the darker of the two grey lines
# Law 21.545 was published on 10 March 2023 (day 69). Years are plotted as integers, so the marker
# sits at the day's place inside 2023 measured from the middle of each plotted year, as in EF6.
# It is context only: no estimate in this plate depends on it.
LAW_X = 2023 + 69 / 365 - 0.5
DISRUPTION = 'Reporting\ndisruption 2020–21'
LAW_LABEL = 'Law 21.545\n(2023)'
COUNT = FuncFormatter(lambda v, p: num(v, 'en', 0))

#: (a) — the three F84 position series are dodged by 0.09 of a year around the tick; the all-GRD
#: comparison sits two dodge steps further right, clear of the F84 whiskers, as in the stored plate.
POSITIONS = [(VARIANT, 'any', BLUE, 'o', '-', 'Any position', -0.09),
             (VARIANT, 'principal', ORANGE, 'o', '-', 'Principal F84', 0.00),
             (VARIANT, 'secondary_only', GOLD, 'o', '-', 'Secondary only', +0.09),
             (ALL_GRD, 'all', GREY, 's', '--', 'All GRD episodes', +0.27)]

#: (c) — the same comparison without the secondary-only series, principal F84 marked by a triangle.
P90_SERIES = [(VARIANT, 'any', BLUE, 'o', '-', 'Any position'),
              (VARIANT, 'principal', ORANGE, '^', '-', 'Principal F84'),
              (ALL_GRD, 'all', GREY, 's', '--', 'All GRD episodes')]

#: (d) — F84 and all GRD, each across all activities and restricted to hospitalisation.
ZERO_SERIES = [(VARIANT, 'any', 'all', BLUE, '-',
                'Episodes with documented F84 · all\nactivities'),
               (VARIANT, 'any', 'hospitalisation', GREEN, '-',
                'Episodes with documented F84 ·\nhospitalisation'),
               (ALL_GRD, 'all', 'all', GREY, '--', 'All GRD episodes · all activities'),
               (ALL_GRD, 'all', 'hospitalisation', DARK, '--',
                'All GRD episodes · hospitalisation')]

#: (f) — the two activities the plate separates, bars on the left axis, median days on the right.
ACTIVITIES = [('hospitalisation', GREEN, BLACK, 'o', '-', 'Hospitalisation'),
              ('cma', PINK, GREY, 's', '--', 'Major ambulatory surgery')]
DAYS_PER_EPISODE = 2000            # (f): the two axes of the stored plate, 2,000 episodes per day

#: (b) — the WHO five-year groups of E66, in the plate's order, with the label the plate prints.
AGE_GROUPS = [('0–4', '0–4'), ('5–9', '5–9'), ('10–14', '10–14'), ('15–19', '15–19'),
              ('20–24', '20–24'), ('25–29', '25–29'), ('30–34', '30–34'), ('35–39', '35–39'),
              ('40–44', '40–44'), ('45–49', '45–49'), ('50–54', '50–54'), ('55–59', '55–59'),
              ('60–64', '60–64'), ('65–69', '65–69'), ('70–74', '70–74'), ('75–79', '75–79'),
              ('80+', '80+'), ('Age not reported', 'not reported')]
AGE_BLOCK = 'WHO age group (hospitalisation, any position)'
F84_ROW, ALL_ROW = 'Documented F84 · {}', 'All GRD episodes · {}'

#: (e) — the stay bands of E4, in the plate's order (by band, not by frequency).
STAY_BANDS = ['0', '1', '2', '3–4', '5–7', '8–14', '15–30', '31–90', '91+', 'not reported']


# ---------------------------------------------------------------- tracked tables and their parsing
def _read(rel, **kw):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, **kw)


def _int(s):
    """'8,221' -> 8221 ; the presentation tables store counts as formatted strings."""
    return int(str(s).replace(',', '').replace(' ', '').strip())


def _count(cell):
    """Count out of a presentation cell such as '1,751 (20.1%)' or '7,616 (+3)'."""
    return _int(str(cell).split('(')[0])


def _los():
    """The tidy length-of-stay grid restricted to the hospital panel of the plate."""
    return _read(LOS).query('panel == @PANEL').copy()


def _cell(d, variant, position, activity):
    """One (variant, position, activity) series of the grid, indexed by year, in year order."""
    s = d[(d.variant == variant) & (d.position == position) & (d.activity == activity)]
    return s.sort_values('year').set_index('year')


def _age_table():
    """The WHO age block of E66, one row per 'Documented F84 · <band>' / 'All GRD episodes · <band>'."""
    t = _read(AGE, encoding='utf-8-sig')
    return t[t.Block == AGE_BLOCK].set_index('Indicator')


def _age_cell(text):
    """'1,319; 3 (1–5); 5.4' -> (1319, 3.0, 5.4) ; 'n/e' -> (0, nan, nan).

    The cell is 'n; median (IQR); mean'. Only the count, the median and the mean are plotted, so the
    interquartile range is parsed and dropped.
    """
    text = str(text).strip()
    if text in ('n/e', 'nan', ''):
        return 0, np.nan, np.nan
    n, median_iqr, mean = text.split(';')
    return _int(n), float(median_iqr.split('(')[0].strip()), float(mean)


def _age_series(t, template):
    """Pooled 2019–2024 mean and 2024 median for one of the two series of (b).

    The pooled mean is the n-weighted average of the six per-year means the table prints, which is
    what the stored plate's bars are; the unweighted average of the six would be a different number.
    Age groups with no episode in any year (documented F84 never reports 'age not reported') come
    back as nan and are not drawn.
    """
    pooled, median_2024 = [], []
    for key, _label in AGE_GROUPS:
        row = t.loc[template.format(key)]
        cells = [_age_cell(row[str(y)]) for y in YEARS]
        n = np.array([c[0] for c in cells], float)
        mean = np.array([c[2] for c in cells], float)
        keep = n > 0
        pooled.append(float((n[keep] * mean[keep]).sum() / n[keep].sum()) if keep.any() else np.nan)
        median_2024.append(_age_cell(row[str(BAND_YEAR)])[1])
    return np.array(pooled), np.array(median_2024)


def _bands():
    """(e): the 2024 stay bands, as a share of episodes with F84 and of all GRD episodes.

    E4 prints each cell as '<count> (<pct>%)' with the percentage already rounded to one decimal.
    The shares are recomputed from the counts and the column totals, because only then do the
    plate's difference labels come out right ('−0.7' for the 3–4 band, '+0.0' for 'not reported').
    """
    t = _read(FEATURES, encoding='utf-8-sig')
    t = t[t.Variable == 'los_bin'].set_index('Category')
    whole = next(c for c in t.columns if c.startswith('All GRD'))
    f84 = np.array([_count(t.loc[b, str(BAND_YEAR)]) for b in STAY_BANDS], float)
    grd = np.array([_count(t.loc[b, whole]) for b in STAY_BANDS], float)
    return 100 * f84 / f84.sum(), 100 * grd / grd.sum(), f84.sum(), grd.sum()


def _diff(pp):
    """The plate's difference label: an explicit sign, one decimal, a true minus sign."""
    return ('+' if pp >= 0 else '−') + num(abs(pp), 'en', 1)


# --------------------------------------------------------------------- agreement with the corpus
def _check_published(d):
    """Compare what will be drawn against the published presentation table of the plate.

    EF2 prints, for four of the plotted series, 'median (P25–P75)', the P90, the zero-day count and
    share and the episode count with its excluded invalid dates, so this checks the estimator, the
    denominator and the case definition at once. The quartiles and the P90 of the tidy grid are not
    whole days (the 2021 principal P75 is 24.75), so they are compared rounded, the way the table
    prints them. The age and stay-band tables are checked against their own year totals.
    """
    t = _read(PUBLISHED, encoding='utf-8-sig')
    t = t.set_index(t.columns[0])
    bad = []
    rows = [('Episodes with documented F84 · hospitalisation', VARIANT, 'any', 'hospitalisation'),
            ('Principal F84 · hospitalisation', VARIANT, 'principal', 'hospitalisation'),
            ('Episodes with documented F84 · major ambulatory surgery', VARIANT, 'any', 'cma'),
            ('All GRD episodes · hospitalisation', ALL_GRD, 'all', 'hospitalisation')]
    for label, variant, position, activity in rows:
        s = _cell(d, variant, position, activity)
        for year in YEARS:
            r = s.loc[year]
            got = {
                'Median (P25–P75)': (round(r.median_days), round(r.q25_days), round(r.q75_days)),
                'P90 of stay (days)': round(r.p90_days),
                '% of episodes with zero-day stay': (int(r.n_los_zero),
                                                     round(100 * r.n_los_zero / r.n_valid_dates, 1)),
                'n': (int(r.n_valid_dates), int(r.n_invalid_dates)),
            }
            for stat, value in got.items():
                cell = str(t.loc[f'{label} — {stat}', str(year)]).strip()
                if stat == 'Median (P25–P75)':
                    median, iqr = cell.split(' (')
                    want = (_int(median), *(_int(x) for x in iqr.rstrip(')').split('–')))
                elif stat == 'P90 of stay (days)':
                    want = _int(cell)
                elif stat == 'n':
                    n, invalid = cell.split(' (+')
                    want = (_int(n), _int(invalid.rstrip(')')))
                else:
                    n, pct = cell.split(' (')
                    want = (_int(n), float(pct.rstrip('%)')))
                if value != want:
                    bad.append(f'{label} — {stat} {year}: {value} vs published {want}')

    age = _age_table()
    for template, variant, position in ((F84_ROW, VARIANT, 'any'), (ALL_ROW, ALL_GRD, 'all')):
        s = _cell(d, variant, position, 'hospitalisation')
        for year in YEARS:
            total = sum(_age_cell(age.loc[template.format(k)][str(year)])[0] for k, _ in AGE_GROUPS)
            if total != int(s.loc[year].n_valid_dates):
                bad.append(f'{template.format("<age>")} {year}: age groups sum to {total} but the '
                           f'grid holds {int(s.loc[year].n_valid_dates)} episodes')

    _f84, _grd, n_f84, n_grd = _bands()
    s = _cell(d, VARIANT, 'any', 'all').loc[BAND_YEAR]
    if n_f84 != int(s.n_episodes_cell):
        bad.append(f'stay bands {BAND_YEAR}: sum to {int(n_f84)}, grid holds {int(s.n_episodes_cell)}')
    g = _cell(d, ALL_GRD, 'all', 'all').loc[BAND_YEAR]
    if n_grd != int(g.n_episodes_cell):
        bad.append(f'all-GRD stay bands {BAND_YEAR}: sum to {int(n_grd)}, grid holds '
                   f'{int(g.n_episodes_cell)}')

    if bad:
        raise AssertionError('redraw disagrees with the published tables:\n  ' + '\n  '.join(bad))


# ------------------------------------------------------------------------------------------ panels
#: title block of a panel, as the stored plate sets it: the letter sits at the sheet margin, the
#: title beside it, the block anchored on its bottom just above the axes, and the letter level with
#: the title's first line — so one line of title height, in figure fractions, is needed to raise it.
TITLE_SIZE, TITLE_LEADING = 10.5, 1.25
LINE = TITLE_SIZE * TITLE_LEADING / 72 / (286 / 25.4)


def _panel_title(fig, ax, ch, title, gap=0.004):
    """Bold panel letter and title above the axes; `gap` makes room for a panel that also writes the
    name of its vertical scale in a line of its own above the axes, as (b) does."""
    pos = ax.get_position()
    x = 0.013 + 0.5 * (pos.x0 > 0.3)
    top = pos.y1 + gap
    fig.text(x, top + title.count('\n') * LINE, ch, fontweight='bold', fontsize=11, ha='left',
             va='bottom')
    fig.text(x + 0.0425, top, title, fontweight='bold', fontsize=TITLE_SIZE, ha='left', va='bottom',
             linespacing=TITLE_LEADING)


def _disruption(ax, y):
    """The shaded 2020–2021 reporting disruption and the note the stored plate writes inside it."""
    shade_pandemic(ax)
    ax.text(2020.5, y, DISRUPTION, transform=ax.get_xaxis_transform(), ha='center', va='top',
            fontsize=7.3, color=GREY, linespacing=1.15,
            bbox=dict(facecolor='white', edgecolor='none', pad=1.2))


def _law(ax, y=0.105):
    """The Law 21.545 marker: dotted, labelled, and context only.

    `y` is where the label hangs from, in axis fractions: the stored plate tucks it under the lowest
    series of each panel, so (d) — whose all-GRD hospitalisation line runs flat along the bottom —
    sets it lower than the others.
    """
    ax.axvline(LAW_X, color='#444444', ls=(0, (1.6, 1.8)), lw=0.8, zorder=1)
    ax.text(LAW_X + 0.06, y, LAW_LABEL, transform=ax.get_xaxis_transform(), fontsize=6.6,
            color='#444444', ha='left', va='top', linespacing=1.1)


def _panel_quartiles(fig, ax, d):
    """(a): median with the interquartile range, by year and by where F84 sits in the record."""
    hi = 0
    for variant, position, colour, marker, ls, label, dx in POSITIONS:
        s = _cell(d, variant, position, 'hospitalisation')
        y = s.median_days.to_numpy()
        lo, up = s.q25_days.to_numpy(), s.q75_days.to_numpy()
        hi = max(hi, up.max())
        ax.errorbar(s.index.to_numpy() + dx, y, yerr=[y - lo, up - y], color=colour, ecolor=colour,
                    marker=marker, ls=ls, ms=3.6, lw=1.3, elinewidth=1.0, capsize=2.0, capthick=1.0,
                    label=label, zorder=3)
    # the stored plate keeps the whiskers in the lower three-quarters: the legend takes the top of
    # the axes and the disruption and law notes the strip under zero.
    ax.set_ylim(-0.14 * hi, 1.41 * hi)
    ax.set_yticks(np.arange(0, 31, 5))
    _disruption(ax, 0.108)
    _law(ax)
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year')
    ax.set_ylabel('Median (P25–P75) · days')
    ax.legend(loc='upper left', ncol=2, columnspacing=1.2, handletextpad=0.5, borderaxespad=0.2,
              labelspacing=0.35)
    clean(ax, 'both')


def _panel_age(fig, ax):
    """(b): pooled 2019–2024 mean (bars) and 2024 median (points) by five-year WHO age group."""
    t = _age_table()
    f84_mean, f84_median = _age_series(t, F84_ROW)
    grd_mean, grd_median = _age_series(t, ALL_ROW)
    y = np.arange(len(AGE_GROUPS))
    f84_bar = ax.barh(y - 0.2, np.nan_to_num(f84_mean), height=0.38, color=BLUE, zorder=3,
                      label='Episodes with\ndocumented F84 · x̄')
    grd_bar = ax.barh(y + 0.2, np.nan_to_num(grd_mean), height=0.38, color=BAR_GREY, zorder=2,
                      label='All GRD episodes · x̄')
    f84_pt, = ax.plot(f84_median, y - 0.2, 'o', color=BLACK, ms=4.2, ls='none', zorder=5,
                      label='Episodes with\ndocumented F84 · 2024\nmed.')
    grd_pt, = ax.plot(grd_median, y + 0.2, 's', color=DARK, ms=3.8, ls='none', zorder=4,
                      label='All GRD episodes ·\n2024 med.')
    ax.set_xlim(0, 1.9 * np.nanmax(np.concatenate([f84_mean, grd_mean])))
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.set_yticks(y)
    ax.set_yticklabels([label for _key, label in AGE_GROUPS])
    ax.set_ylim(len(AGE_GROUPS) - 0.5, -0.5)          # first group at the top, as in the plate
    ax.set_xlabel('Days')
    ax.text(0, 1.015, 'Age group', transform=ax.transAxes, ha='left', va='bottom')
    handles = [f84_pt, grd_pt, f84_bar, grd_bar]       # points first, then the bars, as in the plate
    leg = ax.legend(handles, [h.get_label() for h in handles], loc='upper right',
                    handletextpad=0.6, labelspacing=0.55, borderaxespad=0.2)
    for txt in leg.get_texts():
        txt.set_linespacing(1.15)
    clean(ax, 'x')
    ax.tick_params(axis='y', length=0)


def _panel_p90(fig, ax, d):
    """(c): the 90th percentile of stay, the tail the median and the quartiles cannot show."""
    lo, hi = np.inf, 0
    for variant, position, colour, marker, ls, label in P90_SERIES:
        s = _cell(d, variant, position, 'hospitalisation')
        v = s.p90_days.to_numpy()
        lo, hi = min(lo, v.min()), max(hi, v.max())
        ax.plot(s.index.to_numpy(), v, marker=marker, ls=ls, color=colour, ms=4, lw=1.5,
                label=label, zorder=3)
    ax.set_ylim(0.62 * lo, 1.21 * hi)                  # room for the legend and the two notes
    ax.yaxis.set_major_locator(MultipleLocator(10))
    _disruption(ax, 0.108)
    _law(ax)
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year')
    ax.set_ylabel('P90 of stay (days)')
    ax.legend(loc='upper right', borderaxespad=0.2, labelspacing=0.35, handletextpad=0.6)
    clean(ax, 'both')


def _panel_zero(fig, ax, d):
    """(d): the share of episodes discharged on the day of admission.

    All activities and hospitalisation only are drawn side by side on purpose: major ambulatory
    surgery is a zero-day stay by definition, so the all-activity series is a mix of case mix and
    modality mix and the two must not be read as one.
    """
    hi, lo = 0, np.inf
    for variant, position, activity, colour, ls, label in ZERO_SERIES:
        s = _cell(d, variant, position, activity)
        v = (100 * s.n_los_zero / s.n_valid_dates).to_numpy()
        hi, lo = max(hi, v.max()), min(lo, v.min())
        ax.plot(s.index.to_numpy(), v, marker='o', ls=ls, color=colour, ms=3.6, lw=1.4,
                label=label, zorder=3)
    ax.set_ylim(0.08 * lo, 1.52 * hi)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    _disruption(ax, 0.58)
    _law(ax, 0.096)
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year')
    ax.set_ylabel('% of episodes with zero-day stay')
    leg = ax.legend(loc='upper right', borderaxespad=0.2, labelspacing=0.45, handletextpad=0.6,
                    fontsize=6.6)
    for txt in leg.get_texts():
        txt.set_linespacing(1.15)
    clean(ax, 'both')


def _panel_bands(fig, ax):
    """(e): the 2024 distribution across stay bands, F84 against all GRD episodes of the same year."""
    f84, grd, _n_f84, _n_grd = _bands()
    y = np.arange(len(STAY_BANDS))
    ax.barh(y - 0.2, f84, height=0.38, color=BLUE, zorder=3,
            label='Episodes with\ndocumented F84')
    ax.barh(y + 0.2, grd, height=0.38, color=BAR_GREY, zorder=3, label='All GRD episodes')
    for yi, a, b in zip(y, f84, grd):
        ax.annotate(_diff(a - b), (max(a, b), yi), xytext=(4, 0), textcoords='offset points',
                    ha='left', va='center', fontsize=7.5, color=BLACK)
    ax.set_xlim(0, 1.25 * max(f84.max(), grd.max()))
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.set_yticks(y)
    ax.set_yticklabels(STAY_BANDS)
    ax.set_ylim(len(STAY_BANDS) - 0.5, -0.5)
    ax.set_xlabel('% of episodes')
    ax.set_ylabel('Stay band (days)')
    ax.legend(loc='lower right', borderaxespad=0.2, labelspacing=0.5, handletextpad=0.6)
    clean(ax, 'x')
    ax.tick_params(axis='y', length=0)


def _panel_activity(fig, ax, d):
    """(f): episodes with F84 by activity (bars) and the median days of each activity (lines).

    The two axes are locked together at 2,000 episodes per day, the way the stored plate sets them,
    so the median-day line reads against the right axis without a second grid.
    """
    hi = 0
    for i, (activity, colour, _lc, _m, _ls, label) in enumerate(ACTIVITIES):
        s = _cell(d, VARIANT, 'any', activity)
        n = s.n_valid_dates.to_numpy()
        hi = max(hi, n.max())
        ax.bar(s.index.to_numpy() + (i - 0.5) * 0.36, n, 0.34, color=colour, label=label, zorder=3)
    shade_pandemic(ax)
    top = 2.04 * hi                                   # the stored plate's headroom for its legend
    ax.set_ylim(0, top)
    ax.yaxis.set_major_locator(MultipleLocator(DAYS_PER_EPISODE))
    ax.yaxis.set_major_formatter(COUNT)
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year')
    ax.set_ylabel('Episodes with documented F84')
    ax.text(2020.5, 0.62, DISRUPTION, transform=ax.get_xaxis_transform(), ha='center', va='top',
            fontsize=7.3, color=GREY, linespacing=1.15)
    clean(ax, 'both')

    r = ax.twinx()
    for activity, _bar, colour, marker, ls, label in ACTIVITIES:
        s = _cell(d, VARIANT, 'any', activity)
        r.plot(s.index.to_numpy(), s.median_days.to_numpy(), marker=marker, ls=ls, color=colour,
               ms=4.2, lw=1.6, zorder=4, label=f'Median days (line) ·\n{label.lower()}')
    r.set_ylim(0, top / DAYS_PER_EPISODE)
    r.yaxis.set_major_locator(MultipleLocator(1))
    r.set_ylabel('Median days (line)')
    r.grid(False)
    for spine in ('top', 'right'):
        r.spines[spine].set_visible(False)

    handles, labels = ax.get_legend_handles_labels()   # the bars live on the left axis
    h2, l2 = r.get_legend_handles_labels()             # the lines on the right one
    leg = r.legend(handles + h2, labels + l2, loc='upper right', borderaxespad=0.2,
                   labelspacing=0.45, handletextpad=0.6, fontsize=7)
    for txt in leg.get_texts():
        txt.set_linespacing(1.15)


# -------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of EF2 and hand back the figure."""
    d = _los()
    _check_published(d)
    style()
    fig = plt.figure(figsize=(210/25.4, 286/25.4))    # the stored plate is a full page, six panels
    # axes placed as in the stored plate: two columns, three rows, room above each for its title.
    col, width, height = (0.118, 0.596), 0.362, 0.2565
    row = (0.6899, 0.3696, 0.0338)
    axes = [fig.add_axes([col[i % 2], row[i // 2], width, height]) for i in range(6)]
    a, b, c, e, f = axes[0], axes[1], axes[2], axes[4], axes[5]

    _panel_quartiles(fig, a, d)
    _panel_age(fig, b)
    _panel_p90(fig, c, d)
    _panel_zero(fig, axes[3], d)
    _panel_bands(fig, e)
    _panel_activity(fig, f, d)

    # (b) writes 'Age group' above its axes, so its title is set a line higher than the others
    titles = [('(a)', 'Median and P25–P75 by year and position\n(hospitalisation)', 0.004),
              ('(b)', 'Stay by age group: pooled 2019–2024\nmean and 2024 median', 0.0213),
              ('(c)', '90th percentile of stay by year', 0.004),
              ('(d)', 'Episodes with zero-day stay (%)', 0.004),
              ('(e)', 'Distribution by stay bands, 2024', 0.004),
              ('(f)', 'Hospitalisation versus major ambulatory\nsurgery', 0.004)]
    for ax, (ch, title, gap) in zip(axes, titles):
        _panel_title(fig, ax, ch, title, gap)
    return fig


if __name__ == '__main__':
    fig = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor='white')
    print('wrote', out)
