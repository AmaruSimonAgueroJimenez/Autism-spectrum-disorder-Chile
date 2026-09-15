"""Figure 3 — the aggregated REM administrative pathway for autism, redrawn from tracked tables.

The stored plate was drawn by `study/pipeline/02_rem_pathway.py` from the REM Serie A, A05, A27,
A28, P2 and P6 establishment x month files, which this repository does not carry. Every series it
draws survives in two tracked aggregates, and the six panels are rebuilt from them:

  * `docs/study/data/rem_pathway_annual.csv` — the tidy annual file, 346 rows keyed
    year x module x code x variant x measure, carrying `total`, `n_reporting_establishments` and
    the definition `era` of every code. This is what the figure is drawn from.
  * `docs/study/corpus/tables/F3_rem_pathway_data.csv` — the published data table of the figure.
    Its `Value` and `Reporting establishments` cells are formatted strings ("8,221", "1,082"); they
    are parsed and every single number this module plots is checked against them before the figure
    is built (`_check_published`), so nothing drawn here is invented or interpolated.

Estimator, unchanged from the original. Every value is an unweighted annual administrative count
summed over the establishment x month rows present in the REM files — no rate, no denominator, no
survey weight and no standardisation. The consequences are structural, not cosmetic:

  * Definition eras never join. A03 splits into four non-comparable blocks (2019–2022 M-CHAT
    03500406/07; 2023–2024 M-CHAT-R/F 09600212–19; the 2024 31–59-month codes 03700104–09; the 2025
    redesign 03710013–21), so panels (a) and (b) are four separate dot blocks and not one series.
    A05 and P6 break between 2020 and 2021 when broad PDD became strict autism, so panels (d) and
    (f) draw two segments with the break marked and never a line across it.
  * The case definition is `sin_rett`: the lighter "PDD family" lines are the four-code sums
    05990022+05990023+05990025+05990026 (entries), 05990027+05990028+05990030+05990031 (discharges)
    and P6241010+P6241020+P6241040+P6241050 / P6241060+P6241070+P6241090+P6241100 (under control).
    The five-code `con_rett` rows of the tidy file, which add 05990024 / P6241030 / P6241080, are a
    different quantity and are never read here.
  * Stocks and flows never share an axis. Panels (a)–(d) are annual flows; panels (e) and (f) are
    the December stock (`measure == 'december_stock'`). June is a sensitivity shown as unconnected
    hollow markers in (e) and is never summed with December.
  * n is `n_reporting_establishments` and is printed on every label, bar or auxiliary axis, because
    these counts are interventions, entries and records — not persons.

The corpus is English only, so this module is English only.
"""
from pathlib import Path
import re
import sys
import textwrap

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullFormatter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: E402,F401,F403  (house style)

PLATE = "fig3_rem_pathway"
SOURCES = [
    "docs/study/data/rem_pathway_annual.csv",
    "docs/study/corpus/tables/F3_rem_pathway_data.csv",
]
TIDY_FILE, PUBLISHED_FILE = SOURCES
NOTE = ("Redraws the six panels of Figure 3 — A03 detection by definition era, A27/A28 counselling, "
        "referral and rehabilitation, A05 entries and clinical discharges across the 2021 definition "
        "break, and the P2 and P6 December stocks — from the tidy REM pathway file "
        "docs/study/data/rem_pathway_annual.csv, with every plotted number checked against the "
        "published table docs/study/corpus/tables/F3_rem_pathway_data.csv.")

ROOT = BASE.parent.parent                       # docs/study -> docs -> repository root

# --------------------------------------------------------------------------------------------
# palette
# --------------------------------------------------------------------------------------------
# One sequential blue per calendar year for the dot rows of (a) and (b): ColorBrewer Blues, the
# seven darkest of nine steps, 2019 lightest to 2025 darkest.
_BLUES = matplotlib.colormaps['Blues'].resampled(9)
YEAR_BLUE = {year: _BLUES(i) for i, year in enumerate(range(2019, 2026), start=2)}
DOT_EDGE = _BLUES(8)

BROAD_A = '#888888'        # broad-PDD entries / primary care, the pre-2021 definition
BROAD_B = '#505050'        # broad-PDD discharges / specialty, the pre-2021 definition
N_LINE = GREY              # the reporting-establishments line on the right-hand axis
BREAK_GREY = '#8a8a8a'     # definition-break rule and its label
NOTE_GREY = '#5a5a5a'      # in-panel notes

# The stored plate sets the dot panels (a) and (b) in a smaller face than the time-series panels:
# their row labels carry the code name and its n range and would not otherwise fit the gutter.
DOT_TICK, DOT_LABEL, HEAD_PT, ANNOT_PT, NOTE_PT = 8.4, 9.0, 8.4, 9.0, 9.4


def _light(colour, amount=0.35):
    """The PDD-family variant of a series colour: the same hue lifted towards white."""
    r, g, b = matplotlib.colors.to_rgb(colour)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


# Law 21.545 was published on 10 March 2023 (day 69). The stored plate marks it against the middle
# of each plotted year, so the rule sits a little before the 2023 tick. Context only; no estimate
# depends on it.
LAW_X = 2023 + 69 / 365 - 0.5
BREAK_X = 2020.5           # broad PDD (to 2020) | strict autism (from 2021)
YEARS_FULL = list(range(2019, 2026))


# --------------------------------------------------------------------------------------------
# the tracked tables
# --------------------------------------------------------------------------------------------
def _read_tidy():
    """`rem_pathway_annual.csv` as {(code, measure, year): (total, n, era)}.

    A handful of codes appear twice, once as `single_code` and once under the case-definition
    variant that contains them (`strict_autism`, `broad_pre2021`); those duplicates carry identical
    totals and establishment counts, so one row per (code, measure, year) is kept. The combined
    family rows are the `sin_rett` ones and are addressed by their explicit code strings, so the
    five-code `con_rett` rows are never selected.
    """
    raw = pd.read_csv(ROOT/TIDY_FILE, dtype={'code': str})
    raw = raw.drop_duplicates(subset=['code', 'measure', 'year'])
    out = {}
    for row in raw.itertuples():
        out[(row.code, row.measure, int(row.year))] = (
            float(row.total), int(row.n_reporting_establishments), str(row.era))
    return out


_MEASURE = {'annual sum of months (flow)': 'annual_sum',
            'December stock': 'december_stock',
            'June stock (sensitivity)': 'june_stock'}


def _read_published():
    """`F3_rem_pathway_data.csv` as {(code, measure, year): (value, n, panel, series)}.

    The presentation cells are formatted strings — "8,221", "1,082" — and are parsed back to
    integers here; that parsed table is the reference every drawn number is checked against.
    """
    raw = pd.read_csv(ROOT/PUBLISHED_FILE, dtype=str).fillna('')
    out = {}
    for row in raw.itertuples():
        key = (row.Code.strip(), _MEASURE[row.Measure.strip()], int(row.Year))
        out[key] = (_int(row.Value), _int(getattr(row, '_9')),   # 'Reporting establishments'
                    row.Panel.strip(), row.Series.strip())
    return out


def _int(cell):
    """'15,859' -> 15859."""
    m = re.fullmatch(r'[\d,]+', str(cell).strip())
    if not m:
        raise ValueError(f'not a count cell: {cell!r}')
    return int(str(cell).replace(',', ''))


def _label(published, code, measure, year):
    """The series name the published table gives a code, without its module prefix.

    The plate's legends and row labels drop the module tag the table carries ('A05 Entries: strict
    autism' is drawn as 'Entries: strict autism'); the wording itself is the table's, not ours.
    """
    name = published[(code, measure, year)][3]
    return re.sub(r'^(A05|A27|A28|P2|P6)\s+', '', name)


# --------------------------------------------------------------------------------------------
# what each panel draws, in the plate's order
# --------------------------------------------------------------------------------------------
# (title, years, the era every code in the block must start in, codes). The era string is checked
# against the tidy file so a code from a neighbouring era can never slip into a block.
A03_BLOCKS = [                                   # panel (a)
    ('2019–2022 · M-CHAT (03500406/07)', [2019, 2020, 2021, 2022], '2019',
     ['03500406', '03500407']),
    ('2023–2024 · M-CHAT-R/F\n(09600212–19)', [2023, 2024], '2023',
     ['09600212', '09600213', '09600214', '09600215', '09600216',
      '09600217', '09600218', '09600219']),
]
A03_LATER_BLOCKS = [                             # panel (b)
    ('2024 · 31–59 months (03700104–09)', [2024], '2024',
     ['03700104', '03700105', '03700106', '03700107', '03700108', '03700109']),
    ('2025 · redesign (03710013–21)', [2025], '2025',
     ['03710013', '03710014', '03710015', '03710016', '03710017',
      '03710018', '03710019', '03710020', '03710021']),
]
A27_A28 = [('29101566', BLUE), ('29101574', ORANGE),      # panel (c)
           ('29101629', GREEN), ('29101651', PINK)]

# panel (d): (code, measure, years, colour, marker, linestyle, linewidth, markersize)
BROAD_YEARS, STRICT_YEARS = [2019, 2020], [2021, 2022, 2023, 2024, 2025]
A05_SERIES = [
    ('06902600', BROAD_YEARS, BROAD_A, 'o', '-', 2.0, 6.5),
    ('05225000', BROAD_YEARS, BROAD_B, 's', '--', 2.0, 5.6),
    ('05990022+05990023+05990025+05990026', STRICT_YEARS, _light(BLUE), 'o', '-', 1.3, 4.6),
    ('05990027+05990028+05990030+05990031', STRICT_YEARS, _light(ORANGE), 's', '--', 1.3, 4.2),
    ('05990022', STRICT_YEARS, BLUE, 'o', '-', 2.2, 6.5),
    ('05990027', STRICT_YEARS, ORANGE, 's', '--', 2.2, 5.6),
]
# the establishment line of (d): the entries code of each era, so the line breaks where the
# definition does
A05_N_LINE = [('06902600', BROAD_YEARS), ('05990022', STRICT_YEARS)]

P6_SERIES = [                                            # panel (f)
    ('P6223000', BROAD_YEARS, BROAD_A, 'o', '-', 2.0, 6.5),
    ('P6223380', BROAD_YEARS, BROAD_B, 's', '--', 2.0, 5.6),
    ('P6241010+P6241020+P6241040+P6241050', STRICT_YEARS, _light(GOLD), 'o', '-', 1.3, 4.6),
    ('P6241060+P6241070+P6241090+P6241100', STRICT_YEARS, _light(SKY), 's', '--', 1.3, 4.2),
    ('P6241010', STRICT_YEARS, GOLD, 'o', '-', 2.2, 6.5),
    ('P6241060', STRICT_YEARS, SKY, 's', '--', 2.2, 5.6),
]

# every (code, measure, year) this module reads, for the check against the published table
def _used_keys():
    keys = []
    for _, years, _, codes in A03_BLOCKS + A03_LATER_BLOCKS:
        keys += [(c, 'annual_sum', y) for c in codes for y in years]
    keys += [(c, 'annual_sum', y) for c, _ in A27_A28 for y in (2023, 2024, 2025)]
    for code, years, *_ in A05_SERIES + P6_SERIES:
        measure = 'december_stock' if code.startswith('P6') else 'annual_sum'
        keys += [(code, measure, y) for y in years]
    keys += [('P2500500', 'december_stock', y) for y in YEARS_FULL]
    keys += [('P2500500', 'june_stock', y) for y in YEARS_FULL]
    keys += [('P2501878', 'december_stock', y) for y in (2023, 2024, 2025)]
    return [k for k in keys if k != ('09600217', 'annual_sum', 2024)]   # code existed in 2023 only


def _check_published(tidy, published):
    """Every number this module draws, against the published table cell for it."""
    bad = []
    for key in _used_keys():
        total, n, _ = tidy[key]
        value, n_pub, _, _ = published[key]
        if round(total) != value or n != n_pub:
            bad.append(f'{key}: tidy {round(total)} (n={n}) vs published {value} (n={n_pub})')
    if bad:
        raise AssertionError('drawn values disagree with F3_rem_pathway_data.csv:\n  '
                             + '\n  '.join(bad))


# --------------------------------------------------------------------------------------------
# small drawing helpers
# --------------------------------------------------------------------------------------------
def _n_range(ns):
    """'198–399', or '247' when a code was reported in a single year."""
    lo, hi = min(ns), max(ns)
    return num(lo, 'en') if lo == hi else f"{num(lo, 'en')}–{num(hi, 'en')}"


def _break_rule(ax, y_text, label=True):
    """The dash-dot rule at the broad-PDD | strict-autism definition break."""
    ax.axvline(BREAK_X, color=BREAK_GREY, ls=(0, (6, 2, 1, 2)), lw=1.1, zorder=2)
    if label:
        ax.text(BREAK_X - 0.09, y_text, 'definition break', transform=ax.get_xaxis_transform(),
                rotation=90, ha='right', va='bottom', fontsize=NOTE_PT, color=BREAK_GREY)


def _law_rule(ax, label=None, y=0.478):
    """Law 21.545 (March 2023) as context, dotted; labelled once, in (d)."""
    ax.axvline(LAW_X, color='#1a1a1a', ls=(0, (1, 2.2)), lw=1.4, zorder=2)
    if label:
        ax.text(LAW_X + 0.05, y, label, transform=ax.get_xaxis_transform(), ha='left', va='top',
                fontsize=NOTE_PT, color=NOTE_GREY, linespacing=1.15)


def _log_x(ax):
    """The shared log axis of (a) and (b): decade ticks only, as on the stored plate."""
    ax.set_xscale('log')
    ax.xaxis.set_major_locator(FixedLocator([1_000, 10_000]))
    ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.xaxis.set_major_formatter(thousands('en'))
    ax.xaxis.set_minor_formatter(NullFormatter())


def _block_head(ax, text):
    ax.text(0.0, 1.012, text, transform=ax.transAxes, ha='left', va='bottom', fontsize=HEAD_PT,
            fontweight='bold', linespacing=1.3)


def _right_axis(ax, top, ticks):
    """The reporting-establishments axis: counts of establishments, never of people."""
    ax2 = ax.twinx()
    ax2.set_ylim(0, top)
    ax2.set_yticks(ticks)
    ax2.yaxis.set_major_formatter(thousands('en'))
    ax2.set_ylabel('Reporting establishments (n)')
    ax2.grid(False)
    for side in ('top', 'left'):
        ax2.spines[side].set_visible(False)
    ax2.spines['right'].set_visible(True)
    return ax2


def _heading(fig, x, y, text):
    fig.text(x, y, text, fontweight='bold', fontsize=12.5, ha='left', va='top')


# --------------------------------------------------------------------------------------------
# (a) and (b): A03 by definition era, one dot row per code
# --------------------------------------------------------------------------------------------
def _dot_block(ax, tidy, published, block, markersize):
    head, years, era, codes = block
    labels = []
    for i, code in enumerate(codes):
        points = [(y, tidy[(code, 'annual_sum', y)]) for y in years
                  if (code, 'annual_sum', y) in tidy]
        values = [t for _, (t, _, _) in points]
        assert all(e.startswith(era) for _, (_, _, e) in points), (code, era)
        if len(values) > 1:                       # the era's lowest and highest value, joined
            ax.plot([min(values), max(values)], [i, i], color=LIGHT, lw=1.7, zorder=2,
                    solid_capstyle='round')
        for year, (total, _, _) in points:
            ax.plot([total], [i], marker='o', ms=markersize, color=YEAR_BLUE[year],
                    mec=DOT_EDGE, mew=0.55, ls='none', zorder=3 + year - 2019)
        series = _label(published, code, 'annual_sum', points[0][0])
        labels.append(f"{series} · n {_n_range([n for _, (_, n, _) in points])}")
    clean(ax, grid='x')
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(labels)
    ax.set_ylim(len(codes) - 0.5, -0.5)
    ax.tick_params(axis='both', length=0, labelsize=DOT_TICK)
    _block_head(ax, head)


def _panel_ab(ax_top, ax_bottom, tidy, published, blocks, xlabel, markersize, footnote=None):
    for ax, block in ((ax_top, blocks[0]), (ax_bottom, blocks[1])):
        _dot_block(ax, tidy, published, block, markersize)
    lo = min(tidy[(c, 'annual_sum', y)][0]
             for _, years, _, codes in blocks for c in codes for y in years
             if (c, 'annual_sum', y) in tidy)
    hi = max(tidy[(c, 'annual_sum', y)][0]
             for _, years, _, codes in blocks for c in codes for y in years
             if (c, 'annual_sum', y) in tidy)
    span = np.log10(hi) - np.log10(lo)           # the two blocks share one log scale
    xlim = (10 ** (np.log10(lo) - 0.22 * span), 10 ** (np.log10(hi) + 0.22 * span))
    for ax in (ax_top, ax_bottom):
        _log_x(ax)
        ax.set_xlim(*xlim)
    ax_top.tick_params(axis='x', labelbottom=False)
    ax_top.spines['bottom'].set_visible(False)
    ax_bottom.set_xlabel(xlabel, fontsize=DOT_LABEL)
    if footnote:
        ax_bottom.text(0.5, -0.163, footnote, transform=ax_bottom.transAxes, ha='center', va='top',
                       fontsize=9.1)


# --------------------------------------------------------------------------------------------
# (c) A27 and A28, 2023-2025
# --------------------------------------------------------------------------------------------
def _panel_c(ax, tidy, published):
    years = [2023, 2024, 2025]
    offsets = (-0.3, -0.1, 0.1, 0.3)
    for (code, colour), off in zip(A27_A28, offsets):
        totals = [tidy[(code, 'annual_sum', y)][0] for y in years]
        ns = [tidy[(code, 'annual_sum', y)][1] for y in years]
        label = _label(published, code, 'annual_sum', 2023)
        ax.bar([y + off for y in years], totals, width=0.17, color=colour, label=label, zorder=3)
        for y, total, n in zip(years, totals, ns):
            ax.text(y + off, total + 550, f"{num(total, 'en')} · n={num(n, 'en')}", rotation=90,
                    ha='center', va='bottom', fontsize=9.0, color=colour, zorder=4)
    clean(ax)
    ax.set_xlim(2022.5, 2025.5)
    ax.set_ylim(0, 40_000)
    ax.set_yticks(range(0, 40_001, 5_000))
    ax.yaxis.set_major_formatter(thousands('en'))
    year_ticks(ax, years)
    ax.set_xlabel('Year (codes from 2023)')
    ax.set_ylabel('Interventions (annual flow; not persons)')
    ax.legend(loc='upper left', bbox_to_anchor=(0.03, 1.0), title='n = reporting establishments',
              frameon=False, alignment='left', handlelength=1.1, handleheight=1.0,
              labelspacing=0.32, borderpad=0.2)


# --------------------------------------------------------------------------------------------
# (d) A05 entries and clinical discharges, and (f) P6 under control in December
# --------------------------------------------------------------------------------------------
def _era_lines(ax, tidy, published, series, measure_of):
    handles = []
    for code, years, colour, marker, ls, lw, ms in series:
        measure = measure_of(code)
        totals = [tidy[(code, measure, y)][0] for y in years]
        label = textwrap.fill(_label(published, code, measure, years[0]), 27)
        line, = ax.plot(years, totals, marker=marker, ls=ls, lw=lw, ms=ms, color=colour,
                        mec=colour, label=label, zorder=3, clip_on=False)
        handles.append(line)
    return handles


def _panel_d(ax, tidy, published):
    shade_pandemic(ax)
    _break_rule(ax, 0.04)
    _law_rule(ax, 'Law 21.545\n(context)')
    ax.text(2021.1, 0.547, 'Reporting\ndisruption 2020–21', transform=ax.get_xaxis_transform(),
            ha='center', va='center', fontsize=NOTE_PT, color=NOTE_GREY, linespacing=1.15, zorder=4)

    handles = _era_lines(ax, tidy, published, A05_SERIES, lambda c: 'annual_sum')
    clean(ax)
    ax.set_xlim(2018.5, 2025.5)
    ax.set_ylim(0, 50_000)
    ax.set_yticks(range(0, 50_001, 10_000))
    ax.yaxis.set_major_formatter(thousands('en'))
    year_ticks(ax, YEARS_FULL, short=True)
    ax.set_xlabel('Year')
    ax.set_ylabel('Entries / clinical discharges (annual flow)')

    ax2 = _right_axis(ax, 3_800, range(0, 3_501, 500))
    for code, years in A05_N_LINE:               # one segment per definition era
        ax2.plot(years, [tidy[(code, 'annual_sum', y)][1] for y in years], color=N_LINE, lw=1.3,
                 zorder=2)
    n_line, = ax.plot([], [], color=N_LINE, lw=1.3, label='n reporting establishments')


    # the strict-autism entries, labelled year by year as on the stored plate
    for year in STRICT_YEARS:
        total = tidy[('05990022', 'annual_sum', year)][0]
        dx, ha = (6.5, 'left') if year <= 2023 else (-6.0, 'right')
        ax.annotate(num(total, 'en'), (year, total), xytext=(dx, 8.3),
                    textcoords='offset points', ha=ha, va='center', fontsize=ANNOT_PT,
                    color=BLUE, zorder=5)

    ax.legend(handles=handles + [n_line], loc='upper left', bbox_to_anchor=(0.01, 1.005),
              frameon=False, handlelength=1.6, labelspacing=0.30, borderpad=0.15, fontsize=9.4)


def _panel_f(ax, tidy, published):
    shade_pandemic(ax)
    _break_rule(ax, 0.40)
    _law_rule(ax)
    handles = _era_lines(ax, tidy, published, P6_SERIES, lambda c: 'december_stock')
    clean(ax)
    ax.set_xlim(2018.19, 2025.81)
    ax.set_ylim(0, 55_440)
    ax.set_yticks(range(0, 50_001, 10_000))
    ax.yaxis.set_major_formatter(thousands('en'))
    year_ticks(ax, YEARS_FULL, short=True)
    ax.set_xlabel('Year')
    ax.set_ylabel('People under control in December (stock)')

    for code, colour, dx in (('P6241010', GOLD, -3.5), ('P6241060', SKY, -5.0)):
        total = tidy[(code, 'december_stock', 2025)][0]
        ax.annotate(num(total, 'en'), (2025, total), xytext=(dx, 10.0),
                    textcoords='offset points', ha='right', va='center', fontsize=ANNOT_PT,
                    color=colour, zorder=5)
    primary = [tidy[('P6241010', 'december_stock', y)][1] for y in STRICT_YEARS]
    specialty = [tidy[('P6241060', 'december_stock', y)][1] for y in STRICT_YEARS]
    ax.text(0.965, 0.012, f"n primary care\n{_n_range(primary)} ·\nspecialty {_n_range(specialty)}",
            transform=ax.transAxes, ha='right', va='bottom', fontsize=NOTE_PT, color=NOTE_GREY,
            linespacing=1.2)
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.01, 1.005), frameon=False,
              handlelength=1.6, labelspacing=0.30, borderpad=0.15)


# --------------------------------------------------------------------------------------------
# (e) P2 NANEAS with ASD, December stock with the June sensitivity
# --------------------------------------------------------------------------------------------
def _panel_e(ax, tidy, published):
    shade_pandemic(ax)
    _law_rule(ax)
    december = [tidy[('P2500500', 'december_stock', y)][0] for y in YEARS_FULL]
    june = [tidy[('P2500500', 'june_stock', y)][0] for y in YEARS_FULL]
    dec_line, = ax.plot(YEARS_FULL, december, marker='o', ms=7.0, lw=2.4, color=PINK, mec=PINK,
                        label=_label(published, 'P2500500', 'december_stock', 2019), zorder=3)
    # the June markers sit above the December series: in 2019 the two stocks almost coincide and
    # the stored plate shows the hollow June ring over the filled December point
    jun_line, = ax.plot(YEARS_FULL, june, marker='o', ms=7.0, ls='none', color=PINK, mec=PINK,
                        mfc='white', mew=1.6,
                        label=_label(published, 'P2500500', 'june_stock', 2019), zorder=4)
    clean(ax)
    ax.set_xlim(2018.19, 2025.81)
    ax.set_ylim(0, 44_070)
    ax.set_yticks(range(0, 40_001, 5_000))
    ax.yaxis.set_major_formatter(thousands('en'))
    year_ticks(ax, YEARS_FULL, short=True)
    ax.set_xlabel('Year')
    ax.set_ylabel('People under control in December (stock)')

    ax2 = _right_axis(ax, 5_203, range(0, 5_001, 1_000))
    n_dec = [tidy[('P2500500', 'december_stock', y)][1] for y in YEARS_FULL]
    n_jun = [tidy[('P2500500', 'june_stock', y)][1] for y in YEARS_FULL]
    ax2.plot(YEARS_FULL, n_dec, color=N_LINE, lw=1.3, zorder=2)
    ax2.plot(YEARS_FULL, n_jun, color=N_LINE, lw=1.0, ls=(0, (1, 1.7)), zorder=2)
    h_dec, = ax.plot([], [], color=N_LINE, lw=1.3, label='n establishments, Dec.')
    h_jun, = ax.plot([], [], color=N_LINE, lw=1.0, ls=(0, (1, 1.7)),
                     label='n establishments, Jun.')

    for year, offset, ha in ((2019, (7, 8.6), 'left'), (2025, (1, -17), 'right')):
        total = tidy[('P2500500', 'december_stock', year)][0]
        ax.annotate(num(total, 'en'), (year, total), xytext=offset, textcoords='offset points',
                    ha=ha, va='center', fontsize=ANNOT_PT, color=PINK, zorder=5)

    # ASD per 100 NANEAS under control: the same December stock over the total NANEAS code
    ratio = '; '.join(
        f"{y}: {100 * tidy[('P2500500', 'december_stock', y)][0] / tidy[('P2501878', 'december_stock', y)][0]:.1f}"
        for y in (2023, 2024, 2025))
    ax.text(0.032, 0.478, 'ASD per 100 NANEAS\n' + textwrap.fill(f'(Dec.) {ratio}', 24),
            transform=ax.transAxes, ha='left', va='top', fontsize=NOTE_PT, color=NOTE_GREY,
            linespacing=1.2, zorder=4)

    ax.legend(handles=[dec_line, jun_line, h_dec, h_jun], loc='upper left',
              bbox_to_anchor=(0.01, 1.005), frameon=True, facecolor='white', edgecolor='#cccccc',
              framealpha=0.95, handlelength=1.6, labelspacing=0.30, borderpad=0.35)


# --------------------------------------------------------------------------------------------
def draw():
    tidy = _read_tidy()
    published = _read_published()
    _check_published(tidy, published)

    style()
    plt.rcParams.update({'xtick.labelsize': 9.5, 'ytick.labelsize': 9.5, 'axes.labelsize': 11.0,
                         'legend.fontsize': 8.6, 'legend.title_fontsize': 8.6,
                         'xtick.major.size': 0, 'ytick.major.size': 0,
                         'xtick.major.pad': 4, 'ytick.major.pad': 5})
    fig = plt.figure(figsize=(10.0, 13.61))      # the stored plate's proportions, 1000 x 1361 px

    def rect(x0, y0, x1, y1):                    # pixel box of the stored plate -> figure fraction
        return [x0/1000, 1 - y1/1361, (x1 - x0)/1000, (y1 - y0)/1361]

    ax_a_top = fig.add_axes(rect(212, 52, 437, 112))
    ax_a_bot = fig.add_axes(rect(212, 143, 437, 370))
    ax_b_top = fig.add_axes(rect(706, 47, 931, 169))
    ax_b_bot = fig.add_axes(rect(706, 187, 931, 370))
    ax_c = fig.add_axes(rect(212, 541, 437, 887))
    ax_d = fig.add_axes(rect(706, 541, 931, 887))
    ax_e = fig.add_axes(rect(212, 972, 428, 1319))
    ax_f = fig.add_axes(rect(706, 972, 931, 1319))

    _panel_ab(ax_a_top, ax_a_bot, tidy, published, A03_BLOCKS,
              'Screening records (annual flow)', markersize=5.6,
              footnote='*among children with language/social alteration')
    handles, labels = [], []
    for year in YEARS_FULL[:-1]:                 # panel (a) spans 2019-2024
        handles.append(plt.Line2D([], [], marker='o', ls='none', ms=5.6, color=YEAR_BLUE[year],
                                  mec=DOT_EDGE, mew=0.55))
        labels.append(str(year))
    ax_a_bot.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.437), ncol=6,
                    frameon=False, handlelength=1.0, columnspacing=1.1, handletextpad=0.35,
                    fontsize=8.0)

    _panel_ab(ax_b_top, ax_b_bot, tidy, published, A03_LATER_BLOCKS,
              'Children or records (annual flow)', markersize=6.0)
    ax_b_bot.legend([plt.Line2D([], [], marker='o', ls='none', ms=6.0, color=YEAR_BLUE[y],
                                mec=DOT_EDGE, mew=0.55) for y in (2024, 2025)],
                    ['2024', '2025'], loc='upper center', bbox_to_anchor=(0.5, -0.189), ncol=2,
                    frameon=False, handlelength=1.0, columnspacing=1.1, handletextpad=0.35,
                    fontsize=8.0)

    _panel_c(ax_c, tidy, published)
    _panel_d(ax_d, tidy, published)
    _panel_e(ax_e, tidy, published)
    _panel_f(ax_f, tidy, published)

    for x, y, text in ((0.012, 5, '(a) A03: M-CHAT and M-CHAT-R/F'),
                       (0.512, 5, '(b) A03: 2024 and 2025 redesign'),
                       (0.012, 523, '(c) A27 and A28, 2023–2025'),
                       (0.512, 523, '(d) A05 entries and discharges'),
                       (0.012, 954, '(e) P2 NANEAS with ASD (Dec.)'),
                       (0.512, 954, '(f) P6 under control in December')):
        _heading(fig, x, 1 - y/1361, text)
    return fig


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name(f'{PLATE}_redraw.png')
    draw().savefig(out, dpi=100, facecolor='white')
    print('wrote', out)
