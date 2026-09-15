"""EF8 — GRD panel hospitals, redrawn from the tracked hospital-year panel.

The stored plate came from `study/pipeline/12_grd_hospital_panel.py`, which reads discharge microdata
this repository does not hold. The whole plate, however, rests on a single published aggregate: the
hospital × year panel of `docs/study/corpus/tables/ST1_grd_hospital_panel.csv`, whose cells are
`GRD episodes (episodes with documented F84)` for each of the 72 hospitals that ever reported, plus
the summary rows for the observed and the fixed panels. Six panels are redrawn from it:

  (a) rate of the twelve hospitals with most F84 episodes, the other sixty pooled
  (b) Spearman rank correlation of hospital rates between years
  (c) share of episodes with F84 held by the ten largest hospitals
  (d) fixed panel of 65 against the hospitals added in 2023–2024
  (e) distribution of hospital rates within each year
  (f) Lorenz curve and Gini index of episodes with F84 across hospitals

The estimator is the same in all six: numerator = episodes with documented F84 (F84 family excluding
Rett syndrome, in any of the 35 diagnostic positions), denominator = GRD episodes of the *same
hospital and year*. It is a rate per episode — never per resident — and it is never age-standardised,
so nothing here is a quality ranking; it reflects case mix, coding depth and service portfolio.

Three points where the arithmetic has to be done the way the plate does it, not the obvious way:

  * the pooled row of (a) is a group rate — the sixty remaining hospitals' F84 counts over their GRD
    episodes — and not the mean of their sixty rates;
  * the rate lines of (d) are group rates for the same reason (202.7 → 808.6 for the fixed panel of
    65, 357.2 → 676.4 for the hospitals added in 2023–2024);
  * (b), (c) and (f) are recomputed here because no tracked table stores them. The rank correlation
    runs over the hospitals present in *both* years of a pair (n is printed on each bar), the share
    of (c) is over F84 episodes, and the Gini of (f) runs over the hospitals that reported that year,
    the 'not reported' rows dropped — keeping them as zeros would give 0.59 in 2019 instead of 0.55.

`_check_published()` re-reads the two other published hospital tables before anything is drawn and
compares every count, denominator and rate against them: `E61_grd_hospital_year_full.csv` prints the
same 72 × 6 cells as `count; rate (exact 95% CI)`, and `S_hospital_rates_2024.csv` prints the 2024
denominators and rates again. Nothing on this plate is entered by hand.

The jitter of the strip in (e) is the one thing that cannot be recovered from a published table; it
is drawn from a fixed seed, so the points sit where the box statistics put them but not on the very
pixels of the stored plate.

The corpus is English only, so this plate is English only.
"""
import sys
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: F401,F403  (house style)

PLATE = "EF8_hospitals"
SOURCES = [
    "docs/study/corpus/tables/ST1_grd_hospital_panel.csv",
    "docs/study/corpus/tables/E61_grd_hospital_year_full.csv",
    "docs/study/corpus/tables/S_hospital_rates_2024.csv",
]
PANEL, FULL, RATES_2024 = SOURCES
NOTE = ("Redraws the six panels of EF8 — the hospital heat map, the Spearman rank stability, the "
        "share of the ten largest hospitals, the fixed panel of 65 against the hospitals added in "
        "2023–2024, the within-year distribution of hospital rates and the Lorenz curve with its "
        "Gini index — from the published hospital × year panel ST1, every cell checked against the "
        "published E61 and 2024 hospital tables.")

ROOT = BASE.parent.parent          # docs/study -> docs -> repository root
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
NAMED = 12                         # named rows of the heat map; the rest are pooled into one row
LABEL_CHARS = 17                   # the stored plate clips the abbreviated name at 17 characters
RNG_SEED = 8                       # the strip of (e) needs a jitter; keep it reproducible
MISSING = '—'                      # ST1 writes an em dash where a hospital did not report that year
# Law 21.545 was published on 10 March 2023 (day 69); the stored plate marks it against the middle
# of each plotted year, which is what this expression reproduces. Context only — no estimate uses it.
LAW_X = 2023 + 69 / 365 - 0.5
BOX_FILL = '#e0eef6'               # the pale fill of the boxes in (e)
BOX_EDGE = '#26485c'
COUNT = FuncFormatter(lambda v, p: num(v, 'en', 0))
# the stored plate sets the heat map and the explanatory notes in smaller type than the axes
CELL_PT, ROW_PT, YEAR_PT, NOTE_PT, KEY_PT = 6.5, 6.2, 8.4, 6.6, 6.9
TITLE_PT, LETTER_PT = 9.2, 10.5

# the stored plate is a full page of six panels on a fixed two-column grid
FIGSIZE = (185 / 25.4, 252 / 25.4)
COLUMN = [(0.150, 0.300), (0.628, 0.300)]                 # x0, width
ROW = [(0.6943, 0.2542), (0.3769, 0.2542), (0.0338, 0.2542)]   # y0, height
LETTER_X = [0.013, 0.513]
TITLE_X = [0.0555, 0.5555]
TITLES = [
    '(a)', 'Rate per 100,000 hospital episodes (12\nhospitals with most F84 episodes and the\nrest pooled)',
    '(b)', 'Rank stability across years (Spearman ρ)',
    '(c)', 'Contribution of the 10 largest hospitals',
    '(d)', 'Fixed panel of 65 versus hospitals added',
    '(e)', 'Distribution of hospital rates by year',
    '(f)', 'Concentration of episodes with F84\n(Lorenz curve)',
]
# 'Hospital Clínico Regional Dr. X (Santiago, Y)' -> 'H.C.R. Dr. X' + '(Y)', longest prefix first
ABBREVIATIONS = [
    ('Hospital Clínico Regional ', 'H.C.R. '), ('Hospital Clínico de Niños ', 'H. Niños '),
    ('Hospital de Niños ', 'H. Niños '), ('Hospital Clínico ', 'H.C. '),
    ('Complejo Hospitalario ', 'C.H. '), ('Complejo Asistencial ', 'C.A. '), ('Hospital ', 'H. '),
]


# ---------------------------------------------------------------- tracked tables and their parsing
def _read(rel):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT/rel, encoding='utf-8-sig', dtype=str)


def _int(s):
    """'1,151,475' -> 1151475 ; the presentation tables store counts as formatted strings."""
    return int(str(s).replace(',', '').replace(' ', '').strip())


def _cell(s):
    """'19,727 (38)' -> (19727, 38) ; an em dash means the hospital did not report that year."""
    s = str(s).strip()
    if s == MISSING:
        return np.nan, np.nan
    episodes, f84 = s.split('(')
    return _int(episodes), _int(f84.rstrip(')'))


def _panel_table():
    """The hospital × year panel: F84 counts, GRD denominators and the fixed-panel flag.

    Returns the 72 hospital rows only; the five summary rows at the foot of the table (they carry no
    code) are handed back separately because `_check_published` totals the panel against them.
    """
    t = _read(PANEL)
    hospitals, summary = t[t.Code.notna()], t[t.Code.isna()]
    counts, denominators = {}, {}
    for year in YEARS:
        parsed = hospitals[str(year)].map(_cell)
        denominators[year] = parsed.map(lambda c: c[0]).to_numpy(float)
        counts[year] = parsed.map(lambda c: c[1]).to_numpy(float)
    index = pd.Index(hospitals.Hospital.to_numpy(), name='hospital')
    return (pd.DataFrame(counts, index=index), pd.DataFrame(denominators, index=index),
            (hospitals['Fixed panel of 65'] == 'Yes').to_numpy(),
            hospitals.Code.to_numpy(), summary.set_index('Hospital'))


def _rate(counts, denominators):
    """Rate per 100,000 episodes of the same hospital and year — the estimator of every panel."""
    return 100_000 * counts / denominators


def _check_published(counts, denominators, fixed, codes, summary):
    """Compare the parsed panel against the other two published hospital tables before drawing.

    E61 prints the same 72 × 6 cells as 'count; rate (exact 95% CI)' and S_hospital_rates_2024 prints
    the 2024 denominators and rates again, so between them every number this plate draws is checked
    against a second published table, and the annual totals against the summary rows of ST1 itself.
    """
    bad = []
    rate = _rate(counts, denominators)

    full = _read(FULL)
    full['code'] = full[full.columns[0]].str.split(' — ').str[0].str.strip()
    full = full.set_index('code')
    for code, hospital in zip(codes, counts.index):
        row = full.loc[code]
        for year in YEARS:
            cell = str(row[str(year)]).strip()
            if cell == 'not reported':
                if np.isfinite(denominators.loc[hospital, year]):
                    bad.append(f'{code} {year}: ST1 reports but E61 does not')
                continue
            published_count, published_rate = cell.split(';')
            if _int(published_count) != counts.loc[hospital, year]:
                bad.append(f'{code} {year}: F84 {counts.loc[hospital, year]:.0f} vs E61 '
                           f'{published_count.strip()}')
            value = float(published_rate.split('(')[0].replace(',', ''))
            if round(rate.loc[hospital, year], 1) != value:
                bad.append(f'{code} {year}: rate {rate.loc[hospital, year]:.1f} vs E61 {value}')

    latest = _read(RATES_2024).set_index('Code')
    for code, hospital in zip(codes, counts.index):
        row = latest.loc[code]
        for got, published, what in (
                (denominators.loc[hospital, 2024], _int(row['GRD episodes 2024']), 'episodes'),
                (counts.loc[hospital, 2024], _int(row['Episodes with F84 2024']), 'F84')):
            if got != published:
                bad.append(f'{code} 2024 {what}: {got:.0f} vs S table {published}')
        value = float(row['Rate per 100,000 episodes (exact 95% CI)'].split('(')[0].replace(',', ''))
        if round(rate.loc[hospital, 2024], 1) != value:
            bad.append(f'{code} 2024 rate: {rate.loc[hospital, 2024]:.1f} vs S table {value}')

    for label, keep in (('Total, observed annual panel', np.ones(len(counts), bool)),
                        ('Total, fixed panel of 65 hospitals', fixed)):
        for year in YEARS:
            episodes, f84 = _cell(summary.loc[label, str(year)])
            got = (counts[keep][year].sum(), denominators[keep][year].sum())
            if got != (f84, episodes):
                bad.append(f'{label} {year}: {got[0]:.0f}/{got[1]:.0f} '
                           f'vs published {f84}/{episodes}')
    for year in YEARS:
        if denominators[year].notna().sum() != _int(summary.loc['Observed hospitals (n)', str(year)]):
            bad.append(f'hospitals reporting in {year}: {denominators[year].notna().sum()} vs '
                       f'published {summary.loc["Observed hospitals (n)", str(year)]}')

    if bad:
        raise AssertionError('redraw disagrees with the published tables:\n  ' + '\n  '.join(bad))


def _abbreviate(name):
    """'Hospital Clínico de Niños Dr. Roberto del Río (Santiago, Independencia)' -> two label lines.

    The stored plate writes the abbreviated hospital on one line and its locality, the last part of
    the parenthesis, on the next, clipping the name at LABEL_CHARS characters with an ellipsis.
    """
    body, _, locality = name.partition(' (')
    locality = locality.rstrip(')').split(', ')[-1]
    for long, short in ABBREVIATIONS:
        if body.startswith(long):
            body = short + body[len(long):]
            break
    if len(body) > LABEL_CHARS:
        body = body[:LABEL_CHARS] + '…'
    return f'{body}\n({locality})'


# ------------------------------------------------------------------------ what each panel is made of
def _heatmap(counts, denominators):
    """(a): the NAMED hospitals with most F84 episodes over 2019–2024, the remaining ones pooled.

    The pooled row is a group rate — the other hospitals' F84 episodes over their GRD episodes — so
    it is built from the summed counts and denominators, never from the mean of their rates.
    """
    order = counts.sum(axis=1).sort_values(ascending=False, kind='mergesort').index
    named, rest = order[:NAMED], order[NAMED:]
    rows = _rate(counts.loc[named], denominators.loc[named]).to_numpy()
    pooled = _rate(counts.loc[rest].sum(), denominators.loc[rest].sum()).to_numpy()
    labels = [_abbreviate(h) for h in named] + [f'All other hospitals ({len(rest)})']
    return np.vstack([rows, pooled]), labels


def _rank_stability(counts, denominators):
    """(b): Spearman ρ of hospital rates, over the hospitals present in both years of each pair."""
    rate = _rate(counts, denominators)
    pairs = list(zip(YEARS, YEARS[1:])) + [(YEARS[0], YEARS[-1])]
    out = []
    for a, b in pairs:
        both = rate[a].notna() & rate[b].notna()
        out.append((f'{a}–\n{b}', stats.spearmanr(rate.loc[both, a], rate.loc[both, b]).statistic,
                    int(both.sum())))
    return out


def _concentration(counts):
    """(c): share of episodes with F84 held by the ten largest hospitals of the year, and by the
    ten largest of 2024 held fixed. 'Largest' is by episodes with F84, which is what the plate plots.
    """
    fixed_ten = counts[YEARS[-1]].sort_values(ascending=False, kind='mergesort').index[:10]
    same, held = [], []
    for year in YEARS:
        column = counts[year]
        same.append(100 * column.sort_values(ascending=False, kind='mergesort').head(10).sum()
                    / column.sum())
        held.append(100 * column.loc[fixed_ten].sum() / column.sum())
    return np.array(same), np.array(held)


def _groups(counts, denominators, fixed):
    """(d): the fixed panel of 65 hospitals against the hospitals that joined in 2023–2024.

    Both rate lines are group rates: the group's F84 episodes over the group's GRD episodes. Years in
    which the added group does not exist have no denominator and are left out of its line.
    """
    out = {}
    for name, mask in (('fixed', fixed), ('added', ~fixed)):
        episodes = counts[mask].sum().to_numpy()
        denominator = denominators[mask].sum().to_numpy()
        with np.errstate(invalid='ignore', divide='ignore'):
            rate = np.where(denominator > 0, 100_000 * episodes / denominator, np.nan)
        out[name] = (episodes, rate)
    return out


def _distribution(counts, denominators):
    """(e): the rates of the hospitals that reported in the year and have at least one F84 episode.

    Hospitals that reported but coded no F84 episode have a rate of exactly zero and cannot be placed
    on a logarithmic axis; the plate says so in a note and leaves them out of the boxes as well.
    """
    rate = _rate(counts, denominators)
    values, zeros = [], 0
    for year in YEARS:
        column = rate[year]
        zeros += int(((column == 0) & column.notna()).sum())
        values.append(column[column > 0].to_numpy())
    return values, zeros


def _lorenz(column):
    """Cumulative share of hospitals against cumulative share of episodes with F84, and the Gini.

    Runs over the hospitals that reported that year — hospitals with no F84 episode are part of the
    inequality and stay in; hospitals that did not report at all are not in the panel of that year.
    """
    value = np.sort(column[column.notna()].to_numpy())
    n = len(value)
    share = np.concatenate([[0], np.cumsum(value) / value.sum()]) * 100
    hospitals = np.arange(n + 1) / n * 100
    gini = 2 * np.sum(np.arange(1, n + 1) * value) / (n * value.sum()) - (n + 1) / n
    return hospitals, share, gini


# ------------------------------------------------------------------------------------------ panels
def _panel_title(fig, ax, side, letter_text, title):
    """Bold panel letter and title above the axes, at the fixed column positions of the plate.

    The title grows upwards from the axes, so a panel whose title needs three lines pushes its first
    line higher; the letter rides on that first line rather than on the last.
    """
    pos = ax.get_position()
    line = TITLE_PT * 1.2 / 72 / fig.get_figheight()          # one line of the title, in figure units
    fig.text(LETTER_X[side], pos.y1 + 0.003 + line * title.count('\n'), letter_text,
             fontweight='bold', fontsize=LETTER_PT, ha='left', va='bottom')
    fig.text(TITLE_X[side], pos.y1 + 0.003, title, fontweight='bold', fontsize=TITLE_PT, ha='left',
             va='bottom', linespacing=1.2)


def _panel_heatmap(fig, ax, values, labels):
    """(a): hospital × year rates, the value printed in every cell."""
    image = ax.imshow(values, cmap='YlGnBu', aspect='auto', vmin=0, vmax=values.max())
    ax.set_xticks(range(len(YEARS))); ax.set_xticklabels(YEARS)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, linespacing=1.15)
    ax.set_xlabel('Year')
    ax.grid(False)
    ax.tick_params(length=0)            # the cells are the grid; the plate draws no tick marks here
    ax.tick_params(axis='x', labelsize=YEAR_PT)
    ax.tick_params(axis='y', labelsize=ROW_PT)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            red, green, blue, _ = image.cmap(image.norm(values[i, j]))
            dark = 0.2126 * red + 0.7152 * green + 0.0722 * blue < 0.5   # is the cell too dark?
            ax.text(j, i, num(values[i, j], 'en', 0), ha='center', va='center', fontsize=CELL_PT,
                    color='white' if dark else BLACK, zorder=3, bbox=None if dark else
                    dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='square,pad=0.25'))
    bar = fig.colorbar(image, cax=ax.inset_axes([1.027, 0.196, 0.037, 0.607]))
    bar.set_label('Hospital rate per 100,000\nepisodes', fontsize=CELL_PT, linespacing=1.15)
    bar.set_ticks(np.arange(1000, values.max(), 1000))
    bar.ax.yaxis.set_major_formatter(COUNT)
    bar.ax.tick_params(labelsize=CELL_PT)
    bar.outline.set_visible(False)


def _panel_rank(fig, ax, pairs):
    """(b): rank correlation between consecutive years, and between the two ends of the series."""
    labels = [p[0] for p in pairs]
    rho = np.array([p[1] for p in pairs])
    colours = [BLUE] * (len(pairs) - 1) + [ORANGE]     # the 2019–2024 pair is set apart
    ax.bar(range(len(pairs)), rho, 0.8, color=colours, zorder=3)
    for i, (_, value, n) in enumerate(pairs):
        ax.annotate(f'n={n}', (i, value), xytext=(0, 4), textcoords='offset points', ha='center',
                    va='bottom', fontsize=7.5)
    ax.set_xticks(range(len(pairs))); ax.set_xticklabels(labels, linespacing=1.15)
    ax.set_ylim(0, 1.13); ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_ylabel('Spearman ρ between years')
    clean(ax, 'x')


def _panel_concentration(fig, ax, same, held):
    """(c): the two shares of the ten largest hospitals, with the reporting band and the law marker."""
    ax.plot(YEARS, same, 'o-', color=BLUE, ms=4.4, lw=1.6, zorder=4,
            label='10 largest of the same\nyear')
    ax.plot(YEARS, held, 's--', color=ORANGE, ms=4.4, lw=1.6, zorder=4,
            label='10 largest of 2024\n(fixed)')
    shade_pandemic(ax)
    ax.text(2020.5, 0.125, 'Reporting\ndisruption 2020–21', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=7.3, color=GREY, linespacing=1.15)
    ax.axvline(LAW_X, color='#444444', ls=(0, (1.4, 1.8)), lw=0.9, zorder=1)
    ax.text(LAW_X + 0.07, 0.135, 'Law 21.545\n(2023)', transform=ax.get_xaxis_transform(),
            fontsize=7.3, color='#444444', ha='left', va='top', linespacing=1.15)
    low = np.floor(min(same.min(), held.min())) - 1
    ax.set_ylim(low, low + (max(same.max(), held.max()) - low) * 1.285)
    ax.set_yticks(np.arange(low, low + 9, 2))
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year'); ax.set_ylabel('% of episodes with F84')
    ax.legend(loc='upper right', labelspacing=0.45, handletextpad=0.6, borderaxespad=0.3,
              fontsize=KEY_PT, frameon=True, facecolor='white', edgecolor='none', framealpha=0.9)
    clean(ax, 'both')


def _panel_groups(fig, ax, groups):
    """(d): episodes of each group (bars) and the rate of each group (lines, right axis)."""
    years = np.array(YEARS, float)
    bars = [('fixed', -0.2, BLUE, 'Fixed panel of 65\nhospitals'),
            ('added', 0.2, ORANGE, 'Hospitals added in\n2023–2024')]
    for key, offset, colour, label in bars:
        ax.bar(years + offset, groups[key][0], 0.35, color=colour, label=label, zorder=3)
    ax.set_ylim(0, groups['fixed'][0].max() * 1.341)
    ax.yaxis.set_major_locator(MultipleLocator(2000)); ax.yaxis.set_major_formatter(COUNT)
    year_ticks(ax, YEARS)
    ax.set_ylabel('Episodes with documented F84')
    ax.set_xlabel('Year — lines (right axis): rate per 100,000\nepisodes of each group',
                  fontsize=NOTE_PT, linespacing=1.2)
    ax.legend(loc='upper left', labelspacing=0.55, handletextpad=0.6, borderaxespad=0.3,
              fontsize=KEY_PT)
    clean(ax, 'y')

    right = ax.twinx()
    for key, style_, colour, marker in (('fixed', '-', BLACK, 'o'), ('added', '--', GREY, 's')):
        rate = groups[key][1]
        keep = np.isfinite(rate)
        right.plot(years[keep], rate[keep], marker + style_, color=colour, ms=4.4, lw=1.6, zorder=4)
    rates = np.concatenate([groups[k][1][np.isfinite(groups[k][1])] for k in ('fixed', 'added')])
    span = rates.max() - rates.min()
    right.set_ylim(rates.min() - 0.05 * span, rates.max() + 0.322 * span)
    right.yaxis.set_major_locator(MultipleLocator(100))
    right.yaxis.set_major_formatter(COUNT)
    right.set_ylabel('Per 100,000 GRD episodes')
    right.grid(False)
    for spine in ('top', 'right'):
        right.spines[spine].set_visible(False)


def _panel_distribution(fig, ax, values, zeros):
    """(e): every hospital of the year as a point, with the median and quartiles behind them."""
    box = ax.boxplot(values, positions=range(len(YEARS)), widths=0.6, patch_artist=True,
                     showfliers=False, medianprops=dict(color=ORANGE, lw=1.3),
                     boxprops=dict(facecolor=BOX_FILL, edgecolor=BOX_EDGE, lw=0.9),
                     whiskerprops=dict(color=BLACK, lw=1.0), capprops=dict(color=BLACK, lw=1.0),
                     zorder=2)
    for patch in box['boxes']:
        patch.set_zorder(2)
    rng = np.random.default_rng(RNG_SEED)
    for i, column in enumerate(values):
        ax.scatter(i + rng.uniform(-0.23, 0.23, len(column)), column, s=8, color=SKY, alpha=0.6,
                   linewidths=0.35, edgecolors=BLUE, zorder=4)
    ax.set_yscale('log')                # decade labels as powers of ten, as the stored plate has them
    low = min(c.min() for c in values) * 10 ** -0.15
    ax.set_ylim(low, max(c.max() for c in values) * 10 ** 0.52)
    ax.set_xticks(range(len(YEARS))); ax.set_xticklabels(YEARS)
    ax.set_xlim(-0.5, len(YEARS) - 0.5)
    ax.set_xlabel('Year'); ax.set_ylabel('Hospital rate per 100,000\nepisodes', linespacing=1.2)
    ax.text(0.015, 0.985, 'Boxes: median and quartiles of hospitals with\nepisodes; hospitals with '
            'no F84 episodes are\noutside the log scale', transform=ax.transAxes, ha='left',
            va='top', fontsize=NOTE_PT, color=GREY, linespacing=1.25)
    assert zeros, 'the note only makes sense if some hospital-year really did code no F84 episode'
    clean(ax, 'both')


def _panel_lorenz(fig, ax, curves):
    """(f): how unequally the episodes with F84 sit across hospitals, at the two ends of the series."""
    ax.plot([0, 100], [0, 100], ls=(0, (1.5, 2)), lw=0.9, color=GREY, zorder=2)
    for (year, colour), (hospitals, share, gini) in zip(((YEARS[0], SKY), (YEARS[-1], ORANGE)),
                                                        curves):
        ax.plot(hospitals, share, color=colour, lw=2.0, zorder=3,
                label=f'{year} · Gini {gini:.2f}')
    ax.set_xlim(-5, 105); ax.set_ylim(-5, 122)
    ax.set_xticks(np.arange(0, 101, 20)); ax.set_yticks(np.arange(0, 121, 20))
    ax.set_xlabel('Cumulative % of hospitals (ascending)')
    ax.set_ylabel('Cumulative % of episodes with\nF84', linespacing=1.2)
    ax.legend(loc='upper right', borderaxespad=0.3, handletextpad=0.6, fontsize=KEY_PT)
    clean(ax, 'both')


# -------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of EF8 and hand back the figure."""
    counts, denominators, fixed, codes, summary = _panel_table()
    _check_published(counts, denominators, fixed, codes, summary)
    style()
    fig = plt.figure(figsize=FIGSIZE)
    axes = [fig.add_axes([COLUMN[i % 2][0], ROW[i // 2][0], COLUMN[i % 2][1], ROW[i // 2][1]])
            for i in range(6)]

    values, labels = _heatmap(counts, denominators)
    _panel_heatmap(fig, axes[0], values, labels)
    _panel_rank(fig, axes[1], _rank_stability(counts, denominators))
    _panel_concentration(fig, axes[2], *_concentration(counts))
    _panel_groups(fig, axes[3], _groups(counts, denominators, fixed))
    _panel_distribution(fig, axes[4], *_distribution(counts, denominators))
    _panel_lorenz(fig, axes[5], [_lorenz(counts[YEARS[0]]), _lorenz(counts[YEARS[-1]])])

    for i, ax in enumerate(axes):
        _panel_title(fig, ax, i % 2, TITLES[2 * i], TITLES[2 * i + 1])
    return fig


if __name__ == '__main__':
    fig = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'qa'/f'{PLATE}_redraw.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor='white')
    print('wrote', out)
