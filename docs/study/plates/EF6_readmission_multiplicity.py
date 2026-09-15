"""EF6 — readmission and multiplicity of GRD episodes with F84, redrawn from the tracked tables.

The stored plate came from `study/pipeline/11_grd_episode_detail.py`, which reads discharge microdata
this repository does not hold. Every series it draws survives in published aggregates, so the six
panels are redrawn here from those:

  (a) all-cause readmission at 30, 90 and 365 days        `docs/study/data/grd_readmission.csv`
  (b) readmission with documented F84, same horizons      `docs/study/data/grd_readmission.csv`
  (c) episodes per identifier within each identifier era  `docs/study/corpus/tables/E10_grd_multiplicity.csv`
  (d) persons within year and episodes per person         `docs/study/data/grd_year_summary.csv`
  (e) 30-day readmission by the position of F84           `docs/study/data/grd_readmission.csv`
  (f) index discharges, eligible discharges and overlaps  `docs/study/data/grd_readmission.csv`

The unit is the index discharge with documented F84 and valid dates inside its identifier era, case
definition `sin_rett` (F84 family without F84.2) on the observed hospital panel. The denominator of
every percentage is `n_eligible` — discharges whose whole horizon falls inside the era — and never
`n_discharges`; that is why the 365-day series breaks at the 2019–2020 | 2021–2024 cut. Percentages
with fewer than `MIN_ELIGIBLE` eligible discharges are not estimable and are not plotted: the
published table prints them as 'n/e' and the plate leaves a note in their place. Intervals are the
Wilson intervals already stored in the table; nothing is recomputed. Persons are counted within a
year or an era only, and are never deduplicated across the identifier-format change between 2020 and
2021, so the bars of (d) are not a person-level time series.

`_check_published()` reads the presentation table of the plate,
`docs/study/corpus/tables/EF6_readmission_multiplicity.csv`, and compares every drawn percentage,
count, person count and multiplicity share against the published cell before the figure is built.

The corpus is English only, so this plate is English only.
"""
import sys
import textwrap
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "EF6_readmission_multiplicity"
SOURCES = [
    "docs/study/data/grd_readmission.csv",
    "docs/study/data/grd_year_summary.csv",
    "docs/study/corpus/tables/E10_grd_multiplicity.csv",
    "docs/study/corpus/tables/EF6_readmission_multiplicity.csv",
]
READMISSION, YEAR_SUMMARY, MULTIPLICITY, PUBLISHED = SOURCES
NOTE = ("Redraws the six panels of EF6 — readmission at 30, 90 and 365 days with Wilson intervals, "
        "readmission by the position of F84, episodes per identifier, persons within year and the "
        "eligibility states — from the published GRD readmission, multiplicity and annual-summary "
        "tables, keeping n_eligible as the denominator and suppressing years with fewer than 30 "
        "eligible discharges.")

ROOT = BASE.parent.parent          # docs/study -> docs -> repository root
VARIANT, PANEL = 'sin_rett', 'observed'
MIN_ELIGIBLE = 30                  # below this the percentage is not estimable ('n/e' in the table)
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
ERAS = ['2019-2020', '2021-2024']
HORIZONS = [(30, BLUE, '30 days'), (90, GREEN, '90 days'), (365, ORANGE, '365 days')]
POSITIONS = [('any', BLUE, 'Any position'), ('principal', ORANGE, 'Principal F84'),
             ('secondary_only', GOLD, 'Secondary only')]
# Law 21.545 was published on 10 March 2023 (day 69). The stored plate marks it a little before the
# 2023 position, i.e. against the middle of each plotted year; LAW_X reproduces that placement. The
# marker is context only — no estimate depends on it.
LAW_X = 2023 + 69 / 365 - 0.5
ERA_NOTE = ("Year — series split by identifier era (2019–2020 | 2021–2024); 'n/e': fewer than "
            f"{MIN_ELIGIBLE} eligible discharges, percentage not estimable and therefore not plotted")
PERSON_NOTE = ("Year (shading: 2020–2021 reporting disruption) — persons only within year: the "
               "identifier format changes between 2020 and 2021")
STATE_NOTE = "Year — 365-day horizon: eligibility falls at the end of each identifier era"
COUNT = FuncFormatter(lambda v, p: num(v, 'en', 0))


# ---------------------------------------------------------------- tracked tables and their parsing
def _read(rel, **kw):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, **kw)


def _int(s):
    """'8,221' -> 8221 ; the presentation tables store counts as formatted strings."""
    return int(str(s).replace(',', '').replace(' ', '').strip())


def _readmission():
    """The readmission table restricted to the case definition and hospital panel of the plate."""
    d = _read(READMISSION)
    return d[(d.variant == VARIANT) & (d.panel == PANEL)].copy()


def _series(d, position, horizon, value='any_cause'):
    """Year, percentage and Wilson bounds for one position and horizon, era by era.

    Years with fewer than MIN_ELIGIBLE eligible discharges are dropped, so the lines break where the
    era ends rather than running through a percentage that the table itself refuses to print.
    """
    s = d[(d.position == position) & (d.horizon_days == horizon) & (d.n_eligible >= MIN_ELIGIBLE)]
    for era in ERAS:
        e = s[s.era == era].sort_values('year')
        if len(e):
            yield e.year.to_numpy(), e[f'pct_{value}'].to_numpy(), \
                  e[f'pct_{value}_lo'].to_numpy(), e[f'pct_{value}_hi'].to_numpy()


def _multiplicity():
    """Episodes per identifier within each era, as counts and as a share of the era's identifiers."""
    m = _read(MULTIPLICITY, encoding='utf-8-sig')
    eras = list(m.columns[1:3])                      # '2019–2020', '2021–2024' (en dash in the file)
    groups = m[m.columns[0]].astype(str).tolist()
    total = {e: _int(m[e].iloc[groups.index('Total identifiers')]) for e in eras}
    rows = [g for g in groups if g != 'Total identifiers']
    out = {}
    for e in eras:
        counts = [_int(m[e].iloc[groups.index(g)].split('(')[0]) for g in rows]
        out[e] = np.array([100 * c / total[e] for c in counts])
    return rows, eras, out


def _persons():
    """Persons within year and episodes per person, on the same case definition as the plate."""
    y = _read(YEAR_SUMMARY)
    y = y[(y.variant == VARIANT) & (y.panel == PANEL) & (y.activity == 'all') & (y.position == 'any')]
    y = y.sort_values('year')
    return y.year.to_numpy(), y.persons_within_year.to_numpy(), \
        (y.n_episodes_f84 / y.persons_within_year).to_numpy()


def _check_published(d):
    """Compare what will be drawn against the published presentation table of the plate.

    The table prints '<numerator>/<denominator>; <pct> (<lo>–<hi>)' or 'n/e' where the percentage is
    not estimable, so it checks the counts, the percentages, the Wilson bounds and the suppression
    rule at once. It also carries the multiplicity shares and the persons of (c) and (d).
    """
    t = _read(PUBLISHED, encoding='utf-8-sig')
    t = t.set_index(t.columns[0])
    bad = []

    def cell(row, year):
        return str(t.loc[row, str(year)]).strip()

    for horizon, _c, _l in HORIZONS:
        for value, label in (('any_cause', 'any cause'), ('f84', 'with F84')):
            row = f'{horizon} days — {label}'
            for year in YEARS:
                r = d[(d.position == 'any') & (d.horizon_days == horizon) & (d.year == year)].iloc[0]
                counts, pct = cell(row, year).split(';')
                n, den = (_int(x) for x in counts.split('/'))
                got = (r[f'n_readmitted_{value}'], r.n_eligible)
                if (n, den) != got:
                    bad.append(f'{row} {year}: counts {got} vs published {(n, den)}')
                if 'n/e' in pct:
                    if r.n_eligible >= MIN_ELIGIBLE:
                        bad.append(f'{row} {year}: published n/e but n_eligible={r.n_eligible}')
                    continue
                v, lo, hi = (float(x) for x in pct.replace('(', ' ').replace(')', '')
                             .replace('–', ' ').split())
                for a, b, what in ((r[f'pct_{value}'], v, 'pct'), (r[f'pct_{value}_lo'], lo, 'lo'),
                                   (r[f'pct_{value}_hi'], hi, 'hi')):
                    if round(float(a), 1) != b:
                        bad.append(f'{row} {year} {what}: {a} vs published {b}')

    rows, eras, shares = _multiplicity()
    for era, col in zip(eras, ['2019–2020', '2021–2024']):
        published = dict(p.split(': ') for p in cell(f'Episodes per identifier within the era — {col}',
                                                     YEARS[0]).split('; '))
        for g, share in zip(rows, shares[era]):
            want = float(published[g].split('(')[1].rstrip('%)'))
            if round(share, 1) != want:
                bad.append(f'multiplicity {era} {g}: {share:.2f}% vs published {want}%')

    years, persons, per_person = _persons()
    for year, p, r in zip(years, persons, per_person):
        if p != _int(cell('Persons within year', year)):
            bad.append(f'persons {year}: {p} vs published {cell("Persons within year", year)}')
        if round(float(r), 2) != float(cell('Episodes per person', year)):
            bad.append(f'episodes per person {year}: {r:.4f} vs published {cell("Episodes per person", year)}')

    if bad:
        raise AssertionError('redraw disagrees with the published table:\n  ' + '\n  '.join(bad))


# ------------------------------------------------------------------------------------------ panels
def _panel_title(fig, ax, ch, title, gap=0.008):
    """Bold panel letter and title above the axes, the way the stored plate sets them.

    `gap` leaves room for the panels that name their unit in a line of their own above the axes.
    """
    lines = title.count('\n')
    letter(fig, ax, ch, dx=-0.048, dy=gap + 0.0165 * lines)
    pos = ax.get_position()
    fig.text(pos.x0, pos.y1 + gap, title, fontweight='bold', fontsize=10.5, ha='left', va='bottom',
             linespacing=1.25)


def _disruption(ax, y=0.80):
    """The shaded 2020–2021 reporting disruption and its note, as the stored plate labels it."""
    shade_pandemic(ax)
    ax.text(2020.5, y, 'Reporting\ndisruption 2020–21', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=7.3, color=GREY, linespacing=1.15,
            bbox=dict(facecolor='white', edgecolor='none', pad=1.2))


def _context(ax, note_x):
    """Reporting-disruption band, the law marker and the 'n/e' notes of panels (a) and (b)."""
    _disruption(ax)
    ax.axvline(LAW_X, color='#444444', ls=(0, (1.6, 1.8)), lw=0.8, zorder=1)
    ax.text(LAW_X + 0.06, 0.97, 'Law 21.545\n(2023)', transform=ax.get_xaxis_transform(),
            fontsize=6.6, color='#444444', ha='left', va='top', linespacing=1.1)
    for x in note_x:
        ax.text(x, 0.10, 'n/e\n365 days', transform=ax.get_xaxis_transform(), ha='center', va='top',
                fontsize=7, color=ORANGE, linespacing=1.15,
                bbox=dict(facecolor='white', edgecolor='none', pad=1.2))


def _panel_readmission(fig, ax, d, value, ticks):
    """(a) and (b): readmission percentage by horizon, one line per identifier era."""
    for horizon, colour, label in HORIZONS:
        first = True
        for years, pct, lo, hi in _series(d, 'any', horizon, value):
            ax.errorbar(years, pct, yerr=[pct - lo, hi - pct], fmt='o-', color=colour, ecolor=colour,
                        ms=3.4, lw=1.3, elinewidth=0.9, capsize=1.8, capthick=0.9,
                        label=label if first else None, zorder=3)
            first = False
    # the years the 365-day horizon cannot reach: its eligibility window leaves the era
    cut = sorted(d[(d.position == 'any') & (d.horizon_days == 365)
                   & (d.n_eligible < MIN_ELIGIBLE)].year.unique())
    _context(ax, cut)
    s = d[(d.position == 'any') & (d.n_eligible >= MIN_ELIGIBLE)]
    # the stored plate keeps the data in the lower third and fills the rest with the legend and notes
    ax.set_ylim(s[f'pct_{value}_lo'].min() * 0.15, s[f'pct_{value}_hi'].max() * 2.4)
    ax.set_yticks(ticks)                      # tick step as in the stored plate: 6 pp in (a), 5 in (b)
    year_ticks(ax, YEARS)
    ax.set_xlabel(textwrap.fill(ERA_NOTE, 45), fontsize=7.3, linespacing=1.2)
    ax.legend(title='Horizon', loc='upper center', bbox_to_anchor=(0.5, 0.62), ncol=3,
              handletextpad=0.5, columnspacing=1.4, frameon=True, facecolor='white',
              edgecolor='none', framealpha=0.85)
    clean(ax, 'both')


def _panel_multiplicity(fig, ax):
    """(c): how many episodes with F84 each identifier accumulates inside its era."""
    rows, eras, shares = _multiplicity()
    x = np.arange(len(rows))
    for i, (era, colour) in enumerate(zip(eras, (BLUE, ORANGE))):
        ax.bar(x + (i - 0.5) * 0.4, shares[era], 0.38, color=colour, label=era, zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(rows)
    ax.set_ylim(0, 110); ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel('Episodes with F84 per identifier')
    ax.set_ylabel('% of identifiers')
    ax.legend(title='Identifier era', loc='upper right')
    clean(ax, 'both')


def _panel_persons(fig, ax):
    """(d): persons within year (bars) and episodes per person (line, right axis)."""
    years, persons, per_person = _persons()
    ax.bar(years, persons, 0.62, color=BLUE, label='Persons within year', zorder=3)
    shade_pandemic(ax)
    ax.set_ylim(0, persons.max() * 1.41)
    ax.yaxis.set_major_locator(MultipleLocator(2000)); ax.yaxis.set_major_formatter(COUNT)
    year_ticks(ax, YEARS)
    ax.text(0, 1.015, 'Persons within year', transform=ax.transAxes, ha='left', va='bottom')
    ax.set_xlabel(textwrap.fill(PERSON_NOTE, 43), fontsize=7.3, linespacing=1.2)
    clean(ax, 'both')

    r = ax.twinx()
    r.plot(years, per_person, 'o-', color=ORANGE, ms=4, lw=1.6, zorder=4, label='Episodes per person')
    span = per_person.max() - per_person.min()
    r.set_ylim(per_person.min() - 0.08 * span, per_person.max() + 0.20 * span)
    r.yaxis.set_major_locator(MultipleLocator(0.005))
    r.yaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, 'en', 3)))
    r.set_ylabel('Episodes per person')
    r.grid(False); r.spines['top'].set_visible(False); r.spines['right'].set_visible(False)

    handles, labels = ax.get_legend_handles_labels()          # the bars live on the left axis
    h2, l2 = r.get_legend_handles_labels()                     # the line on the right one
    r.legend(handles + h2, labels + l2, loc='upper right', borderaxespad=0.2, labelspacing=0.3,
             handletextpad=0.5, frameon=True, facecolor='white', edgecolor='none', framealpha=0.85)


def _panel_position(fig, ax, d):
    """(e): the same 30-day readmission, split by where F84 sits in the discharge record."""
    s = d[(d.horizon_days == 30) & (d.n_eligible >= MIN_ELIGIBLE)]
    for i, (position, colour, label) in enumerate(POSITIONS):
        p = s[s.position == position].sort_values('year')
        ax.bar(p.year + (i - 1) * 0.27, p.pct_any_cause, 0.25, color=colour, label=label, zorder=3,
               yerr=[p.pct_any_cause - p.pct_any_cause_lo, p.pct_any_cause_hi - p.pct_any_cause],
               ecolor=BLACK, capsize=2, error_kw=dict(elinewidth=0.8, capthick=0.8, zorder=4))
    _disruption(ax, 0.98)
    ax.set_ylim(0, s.pct_any_cause_hi.max() * 1.3); ax.set_yticks(np.arange(0, 41, 5))
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year'); ax.set_ylabel('% of eligible discharges')
    ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='none', framealpha=0.85)
    clean(ax, 'both')


def _panel_states(fig, ax, d):
    """(f): index discharges, those with a full 365-day horizon, and overlapping next admissions."""
    s = d[(d.position == 'any') & (d.horizon_days == 365)].sort_values('year')
    bars = [('n_discharges', GREY, 'Index discharges'),
            ('n_eligible', BLUE, 'Eligible with full\nhorizon'),
            ('n_with_overlapping_next_admission', PINK, 'With overlapping next\nadmission')]
    for i, (column, colour, label) in enumerate(bars):
        ax.bar(s.year + (i - 1) * 0.27, s[column], 0.25, color=colour, label=label, zorder=3)
    ax.set_ylim(0, s.n_discharges.max() * 1.48)
    ax.yaxis.set_major_locator(MultipleLocator(2000)); ax.yaxis.set_major_formatter(COUNT)
    year_ticks(ax, YEARS)
    ax.text(0, 1.015, 'Episodes', transform=ax.transAxes, ha='left', va='bottom')
    ax.set_xlabel(textwrap.fill(STATE_NOTE, 48), fontsize=7.3, linespacing=1.2)
    ax.legend(loc='upper left', labelspacing=0.5, handletextpad=0.5)
    clean(ax, 'both')


# -------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of EF6 and hand back the figure."""
    d = _readmission()
    _check_published(d)
    style()
    fig = plt.figure(figsize=(210/25.4, 286/25.4))   # the stored plate is a full page, six panels
    # axes placed as in the stored plate: two columns, three rows, room under each for its note.
    # (d) is the narrower one of the right column: it carries a second axis on its right edge.
    col = [(0.059, 0.396), (0.527, 0.403)]
    row = [(0.731, 0.215), (0.386, 0.214), (0.045, 0.211)]
    box = [list(col[i % 2]) for i in range(6)]
    box[3] = [0.535, 0.382]
    axes = [fig.add_axes([box[i][0], row[i // 2][0], box[i][1], row[i // 2][1]]) for i in range(6)]
    a, b, c, e, f = axes[0], axes[1], axes[2], axes[4], axes[5]

    _panel_readmission(fig, a, d, 'any_cause', np.arange(6, 43, 6))
    a.set_ylabel('% of eligible discharges')
    _panel_readmission(fig, b, d, 'f84', np.arange(5, 36, 5))
    b.text(0, 1.015, '% of eligible discharges', transform=b.transAxes, ha='left', va='bottom')
    _panel_multiplicity(fig, c)
    _panel_persons(fig, axes[3])
    _panel_position(fig, e, d)
    _panel_states(fig, f, d)

    titles = [('(a)', 'All-cause readmission (Wilson 95% CI)', 0.008),
              ('(b)', 'Readmission with documented F84\n(Wilson 95% CI)', 0.018),
              ('(c)', 'Episodes per identifier within the era', 0.008),
              ('(d)', 'Persons within year and episodes per\nperson', 0.018),
              ('(e)', '30-day readmission by F84 position', 0.008),
              ('(f)', 'Data states: discharges, eligible and\noverlaps', 0.018)]
    for ax, (ch, title, gap) in zip(axes, titles):
        _panel_title(fig, ax, ch, title, gap)
    return fig


if __name__ == '__main__':
    fig = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor='white')
    print('wrote', out)
