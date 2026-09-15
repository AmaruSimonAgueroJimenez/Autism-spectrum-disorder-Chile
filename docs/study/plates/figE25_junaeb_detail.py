"""E25 — JUNAEB EVE: caregiver-reported autism in selected school cohorts, 2019–2025.

Redraw of the stored plate `docs/study/corpus/figures/figE25_junaeb_detail.jpg`. The original was
drawn by `study/pipeline/15_extra_figures_context.py` from the JUNAEB EVE microdata, which this
repository does not carry. Every number the six panels plot survives in three tracked tables, so all
six are rebuilt from those:

  (a) weighted % by level and year, with 95% CI and the not-estimable years    E25
  (b) % by sex, level and year (weighted where a weight exists)                E77
  (c) students in the estimation domain and unweighted autism cases            E25
  (d) weighted against unweighted percentage, with the identity diagonal       E25
  (e) male-to-female ratio by level and year, with the 3:1 and 4:1 references  E25
  (f) availability of the autism item and of the weight, year by level         ST6

The estimator is the one the tables already resolve, and it is the whole point of this plate:

* Panel (a) plots ONLY the published weighted percentage, and it exists for three levels in 2024 and
  four in 2025. Every other level-year is marked with a grey cross on the floor of the panel, never
  with a value: 2019–2022 the questionnaire has no autism category at all, 2023 has the item but no
  published weight, and in 2024 the grade-9 variable (D15_11) is completely empty even though the
  filter was answered, so it is 'not estimable' — never zero. Six years therefore carry a cross.
* Panel (b) mixes the two bases on purpose, exactly as the original does: for 2023 it shows the
  UNWEIGHTED percentage by sex, asterisked in the tick label, because no weight was published that
  year; for 2024 and 2025 it shows the weighted percentage. Grade 9 2024 keeps its asterisked tick
  label and no bars. The 2023 intervals are Wilson intervals computed from E77's own
  'Students; ASD cases' counts — the table's 'Weight and design' column says so in as many words —
  while 2024 and 2025 use the design-based interval published beside each weighted percentage.
* Panel (e)'s 2023 points are ratios of unweighted percentages and carry the same asterisk. The
  ratios and their intervals are read from E25; nothing is recomputed from counts.
* The published weight changes name between years (EXP_REG in 2024, EXP in 2025); panel (f) prints
  that, and prints '×' for grade 9 2024.

Nothing outside the three tables is used, and no percentage, count, ratio or interval is recomputed
from microdata: `_check_published()` re-reads the tables and asserts that every value about to be
drawn is the published one before the figure is built.

The corpus is English only, so this plate is English only.
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

PLATE = "figE25_junaeb_detail"
SOURCES = [
    "docs/study/corpus/tables/E25_junaeb_detail.csv",
    "docs/study/corpus/tables/E77_education_junaeb_full.csv",
    "docs/study/corpus/tables/ST6_junaeb_items.csv",
]
E25, E77, ST6 = SOURCES
NOTE = ("Redraws the six panels of E25 — weighted percentage by level and year with its not-estimable "
        "years, percentage by sex, students and unweighted cases, weighted against unweighted, the "
        "male-to-female ratio and the item/weight availability grid — from the published JUNAEB EVE "
        "tables E25, E77 and ST6, keeping the weighted/unweighted distinction of the original.")

ROOT = BASE.parent.parent          # docs/study -> docs -> repository root

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
#: Levels in the plate's own order, with the colour each one carries in every panel.
LEVELS = [("Pre-school", BLUE, "Pre"), ("Grade 1", ORANGE, "G1"),
          ("Grade 5", GREEN, "G5"), ("Grade 9", PINK, "G9")]
LEVEL_COLOUR = {name: colour for name, colour, _ in LEVELS}
LEVEL_SHORT = {name: short for name, _, short in LEVELS}
ORDER = [name for name, _, _ in LEVELS]

RED = '#c0392b'                    # the clinical-literature reference lines of panel (e)
LAW_X = 2023 - 0.30                # Law 21.545, published 10 March 2023, on an axis of whole years
PANDEMIC = (2020, 2021)
PCT_AXIS = 'Weighted percentage (%)'
NE = 'n/e'                         # how the tables spell a cell that is not estimable

#: Foot of the plate: one note per panel, printed under the six panels as the original prints them.
FOOT = [
    ('a', "the last year of each level is labelled; the full series is in the companion table. "
          "× = not estimable as a weighted percentage (no autism item 2019–2022; no published "
          "weight in 2023; grade 9 in 2024 has a completely empty variable: 'not estimable', never "
          "zero)."),
    ('b', "* unweighted percentage (2023 has no published weight); grade 9 in 2024 is not estimable."),
    ('c', "unweighted autism cases: 2023–2025 only, and no grade 9 in 2024."),
    ('d', "JUNAEB is not national prevalence: selected school cohorts with caregiver report."),
    ('e', "* ratio of unweighted percentages (2023 has no published weight)."),
    ('f', "the autism item appears in 2023; the published weight changes from EXP_REG (2024) to EXP "
          "(2025). In 2024 the grade-9 autism variable is completely empty: 'not estimable', never "
          "zero."),
]
FOOT_FS, FOOT_W_PT, FOOT_LINE = 6.4, 493.2, 1.28   # 6.4 pt over 180 mm less a 3 mm margin each side
FOOT_X, FOOT_Y = 0.0087, 0.06878                   # where the stored plate starts its foot block

#: Panel (f): the three availability states, their symbol and their cell fill.
STATUS = {'yes': ('✓', '#d9ead3'), 'unweighted_only': ('~', '#fce5cd'), 'no': ('×', '#f4cccc')}
KEY = ("✓ = weighted % · ~ = unweighted only · × = not estimable. Levels: "
       + " · ".join(f'{short} = {name}' for name, _, short in LEVELS) + '.')


# ------------------------------------------------------------------ tracked tables and their parsing
def _read(rel):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, encoding='utf-8-sig')


def _int(s):
    """'217,506' -> 217506 ; the presentation tables store counts as formatted strings."""
    s = str(s).strip()
    return np.nan if s.startswith(NE) else float(s.replace(',', '').replace('%', ''))


def _value_ci(s):
    """'6.60 (6.48–6.73)' -> (6.60, 6.48, 6.73) ; 'n/e' -> three NaN."""
    s = str(s).strip()
    if s.startswith(NE):
        return np.nan, np.nan, np.nan
    head, _, tail = s.partition('(')
    lo, _, hi = tail.rstrip(')').partition('–')
    return float(head.strip()), float(lo), float(hi)


def _pct(s):
    """'4.17%' -> 4.17 ; 'n/e' -> NaN. Panel (b) and (d) read the unweighted column this way."""
    s = str(s).strip()
    return np.nan if s.startswith(NE) else float(s.rstrip('%'))


def _wilson(x, n, z=1.959963984540054):
    """The 95% Wilson interval for x successes out of n, as a percentage.

    E77 publishes no interval for the 2023 columns because no weight was published that year; its
    'Weight and design' column states the rule the original followed — 'unweighted proportions with
    Wilson CI' — and this is that interval, computed from the two counts the table does print.
    """
    if not np.isfinite(x) or not np.isfinite(n) or n <= 0:
        return np.nan, np.nan
    p, d = x/n, 1 + z*z/n
    centre = (p + z*z/(2*n))/d
    half = z*np.sqrt(p*(1 - p)/n + z*z/(4*n*n))/d
    return 100*(centre - half), 100*(centre + half)


def junaeb():
    """E25, one row per level and year: students, cases, the two percentages, the ratio, the state."""
    t = _read(E25)
    v = t['% Weighted (95% CI)'].map(_value_ci)
    r = t['Male-to-female ratio (95% CI)'].map(_value_ci)
    return pd.DataFrame({
        'year': t.Year.astype(int),
        'level': t.Level.astype(str),
        'students': t['Students in domain'].map(_int),
        'cases': t['Autism cases (unweighted)'].map(_int),
        'weighted': [a for a, _, _ in v], 'lo': [b for _, b, _ in v], 'hi': [c for _, _, c in v],
        'unweighted': t['% unweighted'].map(_pct),
        'ratio': [a for a, _, _ in r], 'ratio_lo': [b for _, b, _ in r],
        'ratio_hi': [c for _, _, c in r],
        'estimable': t.Estimable.astype(str),
    })


def by_sex():
    """E77 restricted to the two sex rows, with the interval each cell is entitled to.

    Where a weighted percentage is published the value and its design-based interval are used; where
    it is not — 2023, and grade 9 in 2024 — the unweighted percentage is used with a Wilson interval
    from the same row's counts, which is what the original plots behind the asterisk.
    """
    t = _read(E77)
    t = t[t.Sex.isin(['Males', 'Females'])].copy()
    t['level'] = t.Level.replace({'Year 9': 'Grade 9'})       # E77 spells grade 9 'Year 9'
    counts = t['Students; ASD cases'].str.split(';', expand=True)
    t['students'], t['cases'] = counts[0].map(_int), counts[1].map(_int)
    w = t['Weighted % (95% CI)'].map(_value_ci)
    t['weighted'] = [a for a, _, _ in w]
    t['w_lo'] = [b for _, b, _ in w]
    t['w_hi'] = [c for _, _, c in w]
    t['unweighted'] = t['Unweighted %'].map(_pct)
    t['value'] = t.weighted.fillna(t.unweighted)
    wilson = [_wilson(x, n) for x, n in zip(t.cases, t.students)]
    t['lo'] = [w_ if np.isfinite(w_) else u for w_, (u, _) in zip(t.w_lo, wilson)]
    t['hi'] = [w_ if np.isfinite(w_) else u for w_, (_, u) in zip(t.w_hi, wilson)]
    return t[['Year', 'level', 'Sex', 'students', 'cases', 'weighted', 'value', 'lo', 'hi']] \
        .rename(columns={'Year': 'year', 'Sex': 'sex'})


def availability():
    """ST6, one row per year: the state of each level, the autism item and the published weight."""
    t = _read(ST6)
    t = t.assign(level=t.Level.str.split(' (', regex=False).str[0],
                 state=t.Estimability.map(lambda s: 'yes' if str(s).startswith('estimable')
                                          else ('unweighted_only' if str(s).startswith('unweighted')
                                                else 'no')),
                 weight=t['Auxiliary variables (weight · sex · grade)']
                 .str.split(' · ').str[0]
                 .map(lambda s: 'absent' if s.strip() == 'not published' else s.strip()))
    rows = []
    for year in YEARS:
        s = t[t.Year == year].set_index('level')
        rows.append({'year': year,
                     'states': {name: s.at[name, 'state'] for name in ORDER},
                     # the plate names the item of the first level, which is the pre-school variable
                     'item': str(s.at['Pre-school', 'ASD variable']),
                     'weight': ', '.join(sorted(set(s.weight)))})
    return pd.DataFrame(rows)


def _check_published(j, s, av):
    """Assert that every value about to be drawn is the one the tracked tables print.

    It re-reads the three tables as text and compares the parsed series cell by cell, so a change of
    parsing, of level naming or of the case the plate selects fails here rather than on the page.
    """
    bad = []
    e25 = _read(E25)
    e25 = e25.set_index([e25.Year.astype(int), e25.Level.astype(str)])
    for r in j.itertuples():
        cell = e25.loc[(r.year, r.level)]
        want = str(cell['% Weighted (95% CI)']).strip()
        got = NE if not np.isfinite(r.weighted) else f'{r.weighted:.2f} ({r.lo:.2f}–{r.hi:.2f})'
        if want != got:
            bad.append(f'(a) {r.level} {r.year}: weighted {got!r} vs published {want!r}')
        want = str(cell['Male-to-female ratio (95% CI)']).strip()
        got = NE if not np.isfinite(r.ratio) else \
            f'{r.ratio:.2f} ({r.ratio_lo:.2f}–{r.ratio_hi:.2f})'
        if want != got:
            bad.append(f'(e) {r.level} {r.year}: ratio {got!r} vs published {want!r}')
        want = str(cell['Students in domain']).strip()
        if f'{int(r.students):,}' != want:
            bad.append(f'(c) {r.level} {r.year}: students {r.students} vs published {want!r}')
        want = str(cell['Autism cases (unweighted)']).strip()
        got = NE if not np.isfinite(r.cases) else f'{int(r.cases):,}'
        if want != got:
            bad.append(f'(c) {r.level} {r.year}: cases {got!r} vs published {want!r}')

    # grade 9 in 2024 must reach the panels as absent, never as a zero
    g9 = j[(j.year == 2024) & (j.level == 'Grade 9')].iloc[0]
    if np.isfinite(g9.weighted) or np.isfinite(g9.cases) or np.isfinite(g9.ratio):
        bad.append('grade 9 2024 must be not estimable in (a), (c) and (e)')

    e77 = _read(E77)
    e77 = e77.assign(level=e77.Level.replace({'Year 9': 'Grade 9'})).set_index(['Year', 'level', 'Sex'])
    for r in s.itertuples():
        cell = e77.loc[(r.year, r.level, r.sex)]
        want = str(cell['Weighted % (95% CI)']).strip()
        if want.startswith(NE):
            if str(cell['Unweighted %']).strip().startswith(NE):
                if np.isfinite(r.value):
                    bad.append(f'(b) {r.level} {r.year} {r.sex}: drawn {r.value} but published n/e')
            elif f'{r.value:.2f}' != f'{float(cell["Unweighted %"]):.2f}':
                bad.append(f'(b) {r.level} {r.year} {r.sex}: {r.value} vs unweighted {cell["Unweighted %"]}')
        elif want != f'{r.value:.2f} ({r.lo:.2f}–{r.hi:.2f})':
            bad.append(f'(b) {r.level} {r.year} {r.sex}: weighted vs published {want!r}')

    st6 = _read(ST6)
    for _, r in av.iterrows():
        for name in ORDER:
            rows = st6[(st6.Year == r['year']) & (st6.Level.str.startswith(name))]
            want = str(rows.Estimability.iloc[0])
            got = r['states'][name]
            if (got == 'yes') != want.startswith('estimable'):
                bad.append(f'(f) {name} {r["year"]}: state {got!r} vs published {want!r}')
        want_item = str(st6[(st6.Year == r['year'])
                            & (st6.Level.str.startswith('Pre-school'))]['ASD variable'].iloc[0])
        if r['item'] != want_item:
            bad.append(f'(f) {r["year"]}: item {r["item"]!r} vs published {want_item!r}')

    if bad:
        raise AssertionError('redraw disagrees with the published tables:\n  ' + '\n  '.join(bad))


# ---------------------------------------------------------------------------------- shared drawing
def _fmt(ax, which='y', dec=0):
    """Tick labels in the house number format, as the stored plate writes them."""
    axis = ax.yaxis if which == 'y' else ax.xaxis
    axis.set_major_formatter(FuncFormatter(lambda v, p: num(v, 'en', dec)))


def _panel_title(fig, x, y, ch, title):
    """Bold '(x) Title' anchored to the left margin of the grid cell, not to the axes."""
    fig.text(x, y, f'({ch}) {title}', fontweight='bold', fontsize=9, ha='left', va='bottom')


def _halo(alpha=0.75):
    return dict(facecolor='white', edgecolor='none', alpha=alpha, pad=0.8)


# ------------------------------------------------------------------------------------------ panels
def _panel_a(ax, j):
    """(a) weighted percentage by level and year, with the not-estimable years marked on the floor."""
    for level, colour, _ in LEVELS:
        d = j[(j.level == level) & j.weighted.notna()].sort_values('year')
        ax.errorbar(d.year.to_numpy(), d.weighted.to_numpy(),
                    yerr=[(d.weighted - d.lo).to_numpy(), (d.hi - d.weighted).to_numpy()],
                    fmt='o-', color=colour, lw=2, markersize=6, capsize=3, label=level, zorder=3)
    # one cross per year that has no weighted percentage at all; the levels of a year sit on top of
    # one another exactly as in the stored plate, so 2019-2024 show six crosses between them
    for _, r in j[j.estimable != 'yes (weighted)'].iterrows():
        ax.plot([r.year], [0.25], marker='x', color=GREY, markersize=6, zorder=3)

    for x in PANDEMIC:
        ax.axvspan(x - 0.5, x + 0.5, color='grey', alpha=0.12, lw=0, zorder=0)
    ax.text(np.mean(PANDEMIC), 0.988, '2020–2021 (pandemic)', transform=ax.get_xaxis_transform(),
            fontsize=6.2, color='#555555', ha='center', va='top', zorder=6, bbox=_halo(0.85))
    ax.axvline(LAW_X, color='#333333', ls=':', lw=1.1, zorder=1)
    ax.text(LAW_X, 0.932, 'Law 21.545 (2023) ', transform=ax.get_xaxis_transform(), fontsize=6.2,
            color='#333333', ha='right', va='top', zorder=6, bbox=_halo(0.85))

    ax.set_xticks(YEARS)
    ax.set_xlim(min(YEARS) - 0.45, max(YEARS) + 1.15)
    ax.set_ylim(0, 13 * 1.16)          # the plate reserves the top sixth of the panel for its marks
    ax.set_yticks(np.arange(0, 15, 2))
    ax.set_xlabel('Year')
    ax.set_ylabel(PCT_AXIS)
    _fmt(ax)
    # the last year of each level, labelled where the stored plate puts it
    place = {'Grade 1': (3.8, 3.0, 'left', 'bottom'), 'Pre-school': (0, -5, 'center', 'top'),
             'Grade 5': (7, 3, 'left', 'center'), 'Grade 9': (0, -5, 'center', 'top')}
    for level, colour, _ in LEVELS:
        d = j[(j.level == level) & j.weighted.notna()].sort_values('year')
        last = d.iloc[-1]
        dx, dy, ha, va = place[level]
        ax.annotate(num(last.weighted, 'en', 2), (last.year, last.weighted), xytext=(dx, dy),
                    textcoords='offset points', ha=ha, va=va, fontsize=6.4, color=colour, zorder=6)
    ax.legend(loc='upper right', fontsize=7.5, frameon=True, facecolor='white', edgecolor='none',
              framealpha=0.82, borderpad=0.25)
    clean(ax, 'both')


def _panel_b(ax, s):
    """(b) percentage by sex, level and year; 2023 and grade 9 2024 carry the asterisk."""
    keys = [(y, l) for y in (2023, 2024, 2025) for l in ORDER]
    x = np.arange(len(keys))
    for off, sex, colour in ((-0.2, 'Males', BLUE), (0.2, 'Females', ORANGE)):
        v, lo, hi = [], [], []
        for year, level in keys:
            r = s[(s.year == year) & (s.level == level) & (s.sex == sex)]
            value = float(r.value.iloc[0]) if len(r) else np.nan
            v.append(value)
            lo.append(max(value - float(r.lo.iloc[0]), 0) if len(r) and np.isfinite(value) else 0)
            hi.append(max(float(r.hi.iloc[0]) - value, 0) if len(r) and np.isfinite(value) else 0)
        ax.bar(x + off, [0 if not np.isfinite(q) else q for q in v], width=0.38, color=colour,
               label=sex, zorder=3)
        ax.errorbar(x + off, v, yerr=[lo, hi], fmt='none', ecolor='#333333', elinewidth=0.8,
                    capsize=2, zorder=4)
    # a cell is asterisked when no weighted percentage is published for either sex
    star = {(y, l) for y, l in keys
            if not s[(s.year == y) & (s.level == l)].weighted.notna().any()}
    ax.set_xticks(x)
    ax.set_xticklabels([f'{l} {y}' + (' *' if (y, l) in star else '') for y, l in keys],
                       fontsize=6.2, rotation=45, ha='right')
    ax.set_ylim(0, float(np.nanmax(s.value)) * 1.25)
    ax.set_yticks(np.arange(0, 15, 2))
    ax.set_ylabel(PCT_AXIS)
    _fmt(ax)
    ax.legend(loc='upper left', fontsize=7.5, frameon=True, facecolor='white', edgecolor='none',
              framealpha=0.82, borderpad=0.25)
    clean(ax, 'both')


def _panel_c(ax, j):
    """(c) students in the estimation domain (bars) and unweighted autism cases (dots, right axis)."""
    x = np.arange(len(YEARS))
    for i, (level, colour, _) in enumerate(LEVELS):
        d = j[j.level == level].set_index('year').reindex(YEARS)
        ax.bar(x + (i - 1.5) * 0.2, d.students/1e3, width=0.19, color=colour, label=level, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.set_xlabel('Year')
    ax.set_ylabel('Students (thousands)')
    ax.set_ylim(0, float(j.students.max())/1e3 * 1.40)
    ax.yaxis.set_major_locator(MultipleLocator(100))
    _fmt(ax)
    ax.legend(loc='upper center', fontsize=6.2, frameon=True, facecolor='white', edgecolor='none',
              framealpha=0.95, borderpad=0.25)
    clean(ax, 'both')

    right = ax.twinx()
    for level, colour, _ in LEVELS:
        d = j[j.level == level].set_index('year').reindex(YEARS)
        # grade 9 2024 is NaN, so its dotted line breaks there instead of dropping to zero
        right.plot(x, d.cases/1e3, 'o:', color=colour, lw=1.4, markersize=4, zorder=4)
    right.set_ylabel('Unweighted autism cases (thousands)')
    right.yaxis.set_major_locator(MultipleLocator(2))
    _fmt(right, dec=1)
    right.grid(False)
    right.spines['top'].set_visible(False)
    right.spines['right'].set_visible(True)


def _panel_d(ax, j):
    """(d) weighted against unweighted percentage, with the identity diagonal."""
    d = j[j.weighted.notna()]
    ax.scatter(d.unweighted, d.weighted, c=[LEVEL_COLOUR[l] for l in d.level], s=60,
               edgecolor='white', linewidth=0.6, zorder=3)
    lim = float(max(d.unweighted.max(), d.weighted.max())) * 1.18
    ax.plot([0, lim], [0, lim], '--', color=GREY, lw=1.0, zorder=2)
    # the stored plate puts every label up and to the right of its point, and flips only G1 2024,
    # which would otherwise sit on top of Pre 2024
    for r in d.itertuples():
        left = (r.level, r.year) == ('Grade 1', 2024)
        ax.annotate(f'{LEVEL_SHORT[r.level]} {r.year}', (r.unweighted, r.weighted),
                    xytext=(-4.1 if left else 4.0, 5.9), textcoords='offset points',
                    ha='right' if left else 'left', va='center', fontsize=6.2, zorder=6,
                    bbox=_halo())
    ax.set_xlim(0, lim * 1.30)
    ax.set_ylim(0, lim)
    ax.set_xlabel('Unweighted percentage (%)')
    ax.set_ylabel(PCT_AXIS)
    _fmt(ax, 'x')
    _fmt(ax, 'y')
    clean(ax, 'both')


def _panel_e(ax, j):
    """(e) male-to-female ratio by level and year, against the 3:1 and 4:1 clinical references."""
    # the plate orders the eleven points by level NAME and then year, which is why grade 9 comes
    # before pre-school on the axis; grade 9 2024 has no ratio and simply is not there
    d = j[j.ratio.notna()].sort_values(['level', 'year'])
    x = np.arange(len(d))
    ax.errorbar(x, d.ratio.to_numpy(),
                yerr=[(d.ratio - d.ratio_lo).clip(lower=0).to_numpy(),
                      (d.ratio_hi - d.ratio).clip(lower=0).to_numpy()],
                fmt='o', color=BLUE, markersize=6, capsize=3, lw=1.6, zorder=3)
    ax.scatter(x, d.ratio, c=[LEVEL_COLOUR[l] for l in d.level], s=55, edgecolor='white',
               linewidth=0.6, zorder=4)
    ax.axhline(3, color=RED, ls='--', lw=1.0, zorder=2)
    ax.axhline(4, color=RED, ls=':', lw=1.0, zorder=2)
    # '3:1' sits on its own line; the stored plate drops '4:1' clear of the 4.0 rule instead of
    # writing it against the top of the panel, and it is placed here where the plate places it
    for y, label in ((3.00, ' 3:1'), (3.39, ' 4:1')):
        ax.text(len(d) - 0.5, y, label, fontsize=7, color=RED, va='bottom', ha='right', zorder=6,
                bbox=_halo(0.8))
    ax.set_xticks(x)
    ax.set_xticklabels([f'{r.level} {r.year}' + ('' if r.estimable == 'yes (weighted)' else ' *')
                        for r in d.itertuples()], fontsize=6.4, rotation=45, ha='right')
    ax.set_xlim(-0.5, len(d) - 0.5)
    ax.set_ylim(0, max(4.6, float(d.ratio_hi.max()) * 1.12))
    ax.set_ylabel('Male-to-female ratio')
    ax.yaxis.set_major_locator(MultipleLocator(1))
    _fmt(ax, dec=1)
    clean(ax, 'both')


def _panel_f(ax, av):
    """(f) availability of the autism item and of the published weight, year by level."""
    ax.axis('off')
    header = ['Year'] + [short for _, _, short in LEVELS] + ['Autism item', 'Weight']
    cells, colours = [], []
    for _, r in av.iterrows():
        row, fill = [str(r['year'])], ['white']
        for name in ORDER:
            symbol, colour = STATUS[r['states'][name]]
            row.append(symbol)
            fill.append(colour)
        cells.append(row + [r['item'], r['weight']])   # r.item is a Series method, not the column
        colours.append(fill + ['white', 'white'])
    table = ax.table(cellText=cells, colLabels=header, cellColours=colours, cellLoc='center',
                     colWidths=[0.11, 0.095, 0.095, 0.095, 0.095, 0.26, 0.25],
                     bbox=[0.0, 0.40, 1.0, 0.56])
    table.auto_set_font_size(False)
    table.set_fontsize(6.4)
    for (row, _col), cell in table.get_celld().items():
        cell.set_linewidth(0.4)
        if row == 0:
            cell.set_text_props(fontweight='bold')
            cell.set_facecolor('#e8e8e8')
    ax.text(0.0, 0.34, '\n'.join(textwrap.wrap(KEY, 62)), transform=ax.transAxes, fontsize=6.2,
            color='#333333', va='top', linespacing=1.3)


def _foot(fig):
    """The plate's own foot: the six panel notes, wrapped to the width of the canvas."""
    renderer = fig.canvas.get_renderer()
    probe = fig.text(0, 0, '', fontsize=FOOT_FS)

    def width(s):
        probe.set_text(s)
        return probe.get_window_extent(renderer).width/fig.dpi*72

    text, line = [], ''
    for word in ' '.join(f'({ch}) {note}' for ch, note in FOOT).split():
        trial = f'{line} {word}'.strip()
        if line and width(trial) > FOOT_W_PT:
            text.append(line)
            line = word
        else:
            line = trial
    text.append(line)
    probe.remove()
    fig.text(FOOT_X, FOOT_Y, '\n'.join(text), fontsize=FOOT_FS, color='#555555', ha='left',
             va='top', linespacing=FOOT_LINE)


# -------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of E25 and hand back the figure."""
    j, s, av = junaeb(), by_sex(), availability()
    _check_published(j, s, av)

    style()
    plt.rcParams.update({'xtick.labelsize': 7.0, 'ytick.labelsize': 7.0, 'legend.fontsize': 7.0,
                         'axes.labelsize': 8.0})
    fig = plt.figure(figsize=(180/25.4, 245/25.4))     # the plate is a 180 x 245 mm page, 3 x 2
    # the axes rectangles of the stored plate, measured from it: two columns, three rows of equal size
    cols = [(0.0616, 0.3997), (0.5857, 0.3994)]
    rows = [(0.7681, 0.2088), (0.4417, 0.2089), (0.1686, 0.2090)]
    axes = [fig.add_axes([cols[i % 2][0], rows[i//2][0], cols[i % 2][1], rows[i//2][1]])
            for i in range(6)]

    _panel_a(axes[0], j)
    _panel_b(axes[1], s)
    _panel_c(axes[2], j)
    _panel_d(axes[3], j)
    _panel_e(axes[4], j)
    _panel_f(axes[5], av)

    titles = ['Weighted percentage by level and year', 'Percentage by sex, level and year',
              'Students in the domain and autism cases', 'Weighted versus unweighted',
              'Male-to-female ratio by level and year', 'Item and weight availability by year']
    # the titles hang from the left margin of the grid CELL, not from the axes, which is why the
    # three of the left column line up although their y-tick labels are of very different widths
    title_x = [0.0111, 0.5436]
    title_y = [0.97944, 0.65288, 0.37982]
    for i, title in enumerate(titles):
        _panel_title(fig, title_x[i % 2], title_y[i//2], 'abcdef'[i], title)
    _foot(fig)
    return fig


if __name__ == '__main__':
    figure = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=150, facecolor='white')
    print('wrote', out)
