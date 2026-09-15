"""Figure 2 — reporting completeness, coverage layers, panels and definition breaks of the sources.

Redraw of the stored plate `docs/study/corpus/figures/fig1_sources_coverage.jpg`. The original was
drawn by `study/pipeline/` from the REM, GRD, FONASA/ISAPRE/APS and INE files, which this repository
does not carry; all six panels are rebuilt here from tracked tables only — the public REM pathway
file `docs/study/data/rem_pathway_annual.csv` and the published companion tables E72, T, E21, ST1,
E22 and S of `docs/study/corpus/tables/`.

The estimators are the plate's own, and each panel keeps the unit the caption gives it.

(a) The unit is the establishment x period x code CELL, not the row. A module-year's potential grid
    is the establishments that filed at least one row of that module in that year (E72,
    'Establishments with at least one row'), times the year's reporting periods — twelve months in
    Series A, June and December in Series P — times the codes the module actually carries that year.
    That last factor is the trap: it is the distinct single codes present in rem_pathway_annual (the
    `variant == 'single_code'` rows), not E72's 'Codes in force in the year', which counts fourteen
    for A05 and P6 from 2021 where the file holds ten and would turn 4.1% into 2.9%. The three cell
    states are mutually exclusive: a reported value, an explicit zero, and not reported at all (no
    row for the combination, or a row with the cell left blank). Series P sums both the
    `december_stock` and the `june_stock` rows of each code. Explicit zeros never reach 1.4% of
    cells, so their orange segment is drawn at a minimum visible width and is NOT proportional when
    very small; a blank cell is never read as a zero. Modules whose codes were not in force are
    hatched, not shown as zero.

(b) December stocks (FONASA, ISAPRE, APS enrolled) against a 30-June projection (INE). The right
    axis is (FONASA + ISAPRE)/INE as the table prints it, and it is not an insurance rate: it mixes
    those two reference dates and omits the other regimes.

(c) Establishments reporting each module, by definition era, as the maximum across the era's codes —
    a count of establishments, never of people. No line crosses a definition break; the dashed
    verticals are the era boundaries of the plotted series themselves (each era's last year + 0.5).

(d) GRD hospitals and total GRD EPISODES of each panel — the panel-and-activity denominator of the
    register, not a count of F84 cases.

(e) REM-20 discharges and 188-panel retention: activity and capacity, never a population
    denominator.

(f) One column per source, coloured by what one row of it is, with every break of the
    definition-breaks table placed on its year.

The source-database field names that appear in the corpus (REGION, TIPO_INGRESO, ...) play no part
here; the plate, the tables and this module are English only.
"""
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, MultipleLocator
from figstyle import *

PLATE = "fig1_sources_coverage"
SOURCES = ["docs/study/data/rem_pathway_annual.csv",
           "docs/study/corpus/tables/E72_rem_establishments_by_module.csv",
           "docs/study/corpus/tables/T_dataflow_counts.csv",
           "docs/study/corpus/tables/E21_insurance_coverage.csv",
           "docs/study/corpus/tables/ST1_grd_hospital_panel.csv",
           "docs/study/corpus/tables/E22_rem20_capacity.csv",
           "docs/study/corpus/tables/S_definition_breaks.csv"]
NOTE = ("Redraws the six panels of the sources-and-coverage plate from tracked tables only: REM "
        "cell states per establishment x period x code from rem_pathway_annual and E72, coverage "
        "layers from E21, establishments by definition era from rem_pathway_annual, the GRD hospital "
        "panel from ST1, REM-20 capacity from E22 and the source breaks from S_definition_breaks.")

TABLES = BASE / "corpus" / "tables"
PATHWAY = BASE / "data" / "rem_pathway_annual.csv"

YEARS = list(range(2019, 2026))
#: 10 March 2023 on an axis whose year tick is the 30 June reference date of the INE projection.
LAW_X = 2023 - 112 / 365
BAND_X = (2019.5, 2021.5)      # the 2020–21 reporting disruption, shaded in every panel
GREY_DARK = '#555555'


# ---------------------------------------------------------------------------- parsing helpers
def count(cell):
    """Leading count of a presentation cell such as '1,151,475 (2,334)' or '8,221 (731)'."""
    return int(str(cell).split('(')[0].replace(',', '').replace(' ', '').strip())


def pct(cell):
    """Percentage inside a presentation cell: '1,062,539 (99.8%)' -> 99.8, '95.6%' -> 95.6."""
    s = str(cell)
    s = s.split('(')[1] if '(' in s else s
    return float(s.replace('%', '').replace(')', '').strip())


def is_year(v):
    return str(v).strip().isdigit() and len(str(v).strip()) == 4


# ---------------------------------------------------------------------------- panel (a)
#: module, the plate's row order, and the reporting periods of its REM series (A monthly, P biannual)
REM_MODULES = [('A03', 12), ('A05', 12), ('A27', 12), ('A28', 12), ('P2', 2), ('P6', 2)]
ZERO_FLOOR = 3.0        # minimum drawn width of the explicit-zero segment, in % of the cell grid


def pathway():
    """rem_pathway_annual restricted to the module's own single codes.

    The file also carries pooled family rows (con_rett / sin_rett / strict_autism / broad_pre2021)
    that repeat the same establishment x period x code cells; counting them would double the grid.
    """
    d = pd.read_csv(PATHWAY)
    return d[d.variant == 'single_code']


def establishments():
    """E72's 'Establishments with at least one row', by module and year; 'not reported' -> None."""
    t = pd.read_csv(TABLES / "E72_rem_establishments_by_module.csv", encoding='utf-8-sig')
    t = t[t.Indicator == 'Establishments with at least one row'].set_index('REM module')
    out = {}
    for module in t.index:
        for y in YEARS:
            v = str(t.loc[module, str(y)])
            out[(module, y)] = count(v) if v.replace(',', '').strip().isdigit() else None
    return out


def cell_states():
    """Per module and year: % of grid cells with a value, % explicit zero, and the zero count."""
    d, est, out = pathway(), establishments(), {}
    for module, periods in REM_MODULES:
        for y in YEARS:
            s = d[(d.module == module) & (d.year == y)]
            n_est = est.get((module, y))
            if s.empty or not n_est:            # codes not in force: hatched, never zero
                out[(module, y)] = None
                continue
            grid = n_est * periods * s.code.nunique()
            out[(module, y)] = (100 * s.n_rows_value.sum() / grid,
                                100 * s.n_rows_zero.sum() / grid,
                                int(s.n_rows_zero.sum()))
    return out


def masked_deis():
    """The DEIS discharges kept in the national totals and out of the territorial tables."""
    t = pd.read_csv(TABLES / "T_dataflow_counts.csv", encoding='utf-8-sig')
    row = t[t['Count'].astype(str).str.contains('provider-masked', na=False)].iloc[0]
    return count(row['Value'])


def panel_a(ax):
    states, d = cell_states(), pathway()
    rows_k = d.groupby('year').n_rows.sum() / 1000
    ax.set_axis_off()
    ax.set_xlim(-1.55, 7.05)
    ax.set_ylim(-8.95, 1.15)
    for j, y in enumerate(YEARS):                                   # year header
        ax.text(j + 0.45, 0.72, str(y), ha='center', va='bottom', fontsize=7.2, color=BLACK)
    for i, (module, _) in enumerate(REM_MODULES):
        ax.text(-0.12, -i, module, ha='right', va='center', fontsize=8, fontweight='bold')
        for j, y in enumerate(YEARS):
            s = states[(module, y)]
            if s is None:
                ax.add_patch(Rectangle((j, -i - 0.12), 0.9, 0.24, facecolor='white',
                                       edgecolor=LIGHT, lw=0.6, hatch='///'))
                continue
            value, zero, n_zero = s
            zero_w = max(zero, ZERO_FLOOR) if n_zero else 0.0
            left = 0.0
            for width, colour in ((value, BLUE), (zero_w, ORANGE), (100 - value - zero_w, '#d9d9d9')):
                ax.add_patch(Rectangle((j + 0.9 * left / 100, -i - 0.12), 0.9 * width / 100, 0.24,
                                       facecolor=colour, lw=0))
                left += width
            ax.text(j + 0.45, -i + 0.20, num(value, 'en', 1), ha='center', va='bottom',
                    fontsize=7.2, fontweight='bold', color=BLACK)
    ax.plot([0, 6.9], [-5.72, -5.72], color=GREY, lw=0.7)            # rule above the rows line
    ax.text(-0.12, -6.03, 'Rows\n(thousands)', ha='right', va='center', fontsize=7,
            color=BLACK, linespacing=1.15)
    for j, y in enumerate(YEARS):
        ax.text(j + 0.45, -6.03, num(rows_k[y], 'en', 1), ha='center', va='center',
                fontsize=7.2, color=GREY_DARK)
    for (x, colour, label) in ((0.15, BLUE, 'reported value'), (3.85, ORANGE, 'explicit zero'),
                               (0.15, '#d9d9d9', 'not reported')):
        yy = -6.72 if label != 'not reported' else -7.34
        ax.add_patch(Rectangle((x, yy - 0.12), 0.42, 0.24, facecolor=colour, lw=0))
        ax.text(x + 0.58, yy, label, ha='left', va='center', fontsize=7.2, color=BLACK)
    ax.text(0.15, -7.95,
            'Blank cells {} · duplicate rows {}. A blank is not a zero. DEIS\nmasks {} '
            'discharges.'.format(num(d.n_rows_empty.sum(), 'en'),
                                 num(d.n_rows_exact_duplicate.sum(), 'en'),
                                 num(masked_deis(), 'en')),
            ha='left', va='top', fontsize=7, color=BLACK, linespacing=1.3)


# ---------------------------------------------------------------------------- panel (b)
#: legend label, column of E21, colour, marker, and the nudge (points) the plate gives the end
#: label — FONASA and APS end 1.3 million apart, too close for two labels centred on the markers
COVERAGE = [('INE (30 June)', 'INE (30 Jun)', BLACK, 'o', 0.0),
            ('FONASA (Dec)', 'FONASA', BLUE, 's', 1.7),
            ('APS enrolled (Dec)', 'APS enrolled', GREEN, '^', -0.9),
            ('ISAPRE (Dec)', 'ISAPRE', ORANGE, 'D', 0.0)]


def panel_b(ax):
    t = pd.read_csv(TABLES / "E21_insurance_coverage.csv", encoding='utf-8-sig')
    t = t[t.Year.map(is_year)].assign(Year=lambda d: d.Year.astype(int))
    x = t.Year.to_numpy()
    for label, column, colour, marker, dy in COVERAGE:
        y = t[column].map(count).to_numpy() / 1e6
        ax.plot(x, y, color=colour, marker=marker, label=label, clip_on=False)
        end_label(ax, x[-1], y[-1], num(y[-1], 'en', 1), colour, dx=7, dy=dy, size=7.2)
    ax2 = ax.twinx()
    ratio = t['(FONASA+ISAPRE)/INE'].map(pct).to_numpy()
    ax2.plot(x, ratio, color=GREY, marker='x', ls='--', label='Ratio (right axis)')
    ax.plot([], [], color=GREY, marker='x', ls='--', label='Ratio (right axis)')

    shade_pandemic(ax)
    law_line(ax, 'en', label=False, x=LAW_X)
    ax.set_xlim(2018.7, 2026.8)
    ax.set_ylim(0, 32.06)
    ax.set_yticks(range(0, 26, 5))
    ax2.set_ylim(79.8, 122.0)
    ax2.set_yticks([80, 85, 90, 95, 100])
    ax2.set_ylabel('(FONASA + ISAPRE) / INE (%)', fontsize=8, labelpad=1)
    ax2.grid(False)
    ax2.spines['top'].set_visible(False)
    ax2.tick_params(labelsize=7)
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year', fontsize=8)
    ax.set_ylabel('Millions of people', fontsize=8)
    clean(ax)
    ax.text(np.mean(BAND_X), 9.6, 'Reporting\ndisruption\n2020–21', ha='center', va='top',
            fontsize=6.6, color=GREY_DARK, linespacing=1.15,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.65, pad=1.2))
    ax.text(LAW_X + 0.08, 9.6, 'Law 21.545\n(March 2023,\ncontext)', ha='left', va='top',
            fontsize=6.6, color=GREY_DARK, linespacing=1.15)
    leg = ax.legend(loc='upper right', fontsize=6.8, handlelength=1.8, handletextpad=0.5,
                    labelspacing=0.28, borderpad=0.4, frameon=True, framealpha=1,
                    edgecolor=LIGHT, facecolor='white')
    leg.get_frame().set_linewidth(0.6)
    leg.set_zorder(5)


# ---------------------------------------------------------------------------- panel (c)
#: label, module, the era's codes (prefix or explicit tuple), measure, colour, marker, line style
ERA_SERIES = [
    ('A03 M-CHAT 2019–22', 'A03', ('03500406', '03500407'), 'annual_sum', BLUE, 'o', '-'),
    ('A03 M-CHAT-R/F 2023–24', 'A03', '096002', 'annual_sum', BLUE, 's', '-'),
    ('A03 31–59 months 2024', 'A03', '037001', 'annual_sum', BLUE, '^', '-'),
    ('A03 redesign 2025', 'A03', '037100', 'annual_sum', BLUE, 'D', '-'),
    ('A05 broad PDD 2019–20', 'A05', ('05225000', '06902600'), 'annual_sum', ORANGE, 'D', '--'),
    ('A05 autism 2021–25', 'A05', '059900', 'annual_sum', ORANGE, 'o', '-'),
    ('A27 counselling 2023–25', 'A27', '291015', 'annual_sum', GREEN, 'o', '-'),
    ('A28 rehabilitation 2023–25', 'A28', '291016', 'annual_sum', PINK, 'o', '-'),
    ('P2 ASD NANEAS, Dec', 'P2', ('P2500500',), 'december_stock', BLACK, 'o', '-'),
    ('P6 broad PDD, Dec 2019–20', 'P6', ('P6223000', 'P6223380'), 'december_stock', SKY, 'o', '--'),
    ('P6 autism, Dec 2021–25', 'P6', 'P6241', 'december_stock', SKY, 'o', '-')]

C_XLIM = (2018.6, 2025.4)


def era_rows(d, module, codes, measure):
    s = d[(d.module == module) & (d.measure == measure)]
    return s[s.code.isin(codes)] if isinstance(codes, tuple) else s[s.code.str.startswith(codes)]


def panel_c(ax):
    d, breaks = pathway(), set()
    for label, module, codes, measure, colour, marker, ls in ERA_SERIES:
        s = era_rows(d, module, codes, measure)
        e = s.groupby('year').n_reporting_establishments.max()
        ax.plot(e.index, e.to_numpy(), color=colour, marker=marker, ls=ls, label=label,
                markersize=3.6, clip_on=False)
        breaks.add(s.era_end.max() + 0.5)       # a line stops where its era's last year ends
    shade_pandemic(ax)
    for b in sorted(breaks):
        if C_XLIM[0] < b < C_XLIM[1]:
            ax.axvline(b, color=GREY, ls=(0, (4, 3)), lw=0.7, zorder=1)
    law_line(ax, 'en', label=False, x=LAW_X)
    ax.set_xlim(*C_XLIM)
    log_axis(ax, 'y')
    ax.set_ylim(50, 3070)
    ax.yaxis.set_major_locator(FixedLocator([50, 100, 200, 500, 1000, 2000]))
    year_ticks(ax, YEARS)
    ax.set_xlabel('Year', fontsize=8)
    ax.set_ylabel('Reporting establishments (log)', fontsize=8, labelpad=1)
    clean(ax)
    ax.legend(loc='upper center', bbox_to_anchor=(0.52, -0.16), ncol=2, fontsize=6.3,
              handlelength=1.6, handletextpad=0.5, labelspacing=0.3, columnspacing=1.2)


# ---------------------------------------------------------------------------- panel (d)
def grd_panel():
    """The four summary rows of ST1: totals of each panel and the hospital counts, by year."""
    t = pd.read_csv(TABLES / "ST1_grd_hospital_panel.csv", encoding='utf-8-sig')
    years = [c for c in t.columns if is_year(c)]
    t = t.set_index('Hospital')
    take = lambda row: [count(t.loc[row, y]) for y in years]
    return ([int(y) for y in years],
            take('Total, observed annual panel'), take('Total, fixed panel of 65 hospitals'),
            take('Observed hospitals (n)'), take('Fixed-panel hospitals present (n)'))


def panel_d(ax):
    years, obs_ep, fix_ep, obs_h, fix_h = grd_panel()
    x = np.array(years, dtype=float)
    shade_pandemic(ax)
    for off, vals, colour, label in ((-0.21, obs_h, BLUE, 'Hospitals observed'),
                                     (0.21, fix_h, '#b0b0b0', 'Fixed panel (65)')):
        ax.bar(x + off, vals, width=0.4, color=colour, label=label, zorder=2)
        for xi, v in zip(x + off, vals):
            ax.text(xi, 30, str(v), ha='center', va='center', rotation=90, fontsize=6.8,
                    fontweight='bold', color='white', zorder=3)
    ax2 = ax.twinx()
    ax2.plot(x, np.array(obs_ep) / 1e6, color=BLACK, marker='o',
             label='GRD episodes, observed panel (millions)', zorder=4)
    ax2.plot(x, np.array(fix_ep) / 1e6, color=GREY_DARK, marker='s', ls='--',
             label='GRD episodes, fixed panel (millions)', zorder=4)
    proxies = [Line2D([], [], color=BLACK, marker='o',
                      label='GRD episodes, observed panel (millions)'),
               Line2D([], [], color=GREY_DARK, marker='s', ls='--',
                      label='GRD episodes, fixed panel (millions)')]

    law_line(ax, 'en', label=False, x=LAW_X)
    ax.set_xlim(2018.3, 2024.75)
    ax.set_ylim(0, 165.3)
    ax.set_yticks(range(0, 161, 20))
    ax2.set_ylim(0, 1.853)
    ax2.yaxis.set_major_locator(MultipleLocator(0.25))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: num(v, 'en', 1)))
    ax2.set_ylabel('GRD episodes (millions)', fontsize=8, labelpad=1)
    ax2.grid(False)
    ax2.spines['top'].set_visible(False)
    ax2.tick_params(labelsize=7)
    year_ticks(ax, years)
    ax.set_xlabel('Year', fontsize=8)
    ax.set_ylabel('GRD hospitals', fontsize=8)
    clean(ax)
    leg = ax.legend(handles=ax.get_legend_handles_labels()[0] + proxies,
                    loc='upper left', fontsize=6.6, handlelength=1.8, handletextpad=0.5,
                    labelspacing=0.28, borderpad=0.4, frameon=True, framealpha=1,
                    edgecolor=LIGHT, facecolor='white')
    leg.get_frame().set_linewidth(0.6)
    leg.set_zorder(5)


# ---------------------------------------------------------------------------- panel (e)
def panel_e(ax):
    t = pd.read_csv(TABLES / "E22_rem20_capacity.csv", encoding='utf-8-sig')
    t = t[t.Year.map(is_year)].assign(Year=lambda d: d.Year.astype(int))
    x = t.Year.to_numpy().astype(float)
    allest = t['Discharges (all)'].map(count).to_numpy() / 1000
    panel = t['Discharges (188-panel)'].map(count).to_numpy() / 1000
    retention = t['Discharges (188-panel)'].map(pct).to_numpy()
    reporting = t['Reporting establishments'].map(count).to_numpy()

    shade_pandemic(ax)
    ax.bar(x - 0.21, allest, width=0.4, color='#a8cfe8', label='All establishments', zorder=2)
    ax.bar(x + 0.21, panel, width=0.4, color=BLUE, label='188-panel', zorder=2)
    ax2 = ax.twinx()
    ax2.plot(x, retention, color=ORANGE, marker='o', zorder=4)
    retention_proxy = Line2D([], [], color=ORANGE, marker='o', label='Panel retention (%)')
    for xi, r in zip(x, retention):
        ax2.annotate(num(r, 'en', 1), (xi, r), xytext=(0, 6), textcoords='offset points',
                     ha='center', va='bottom', fontsize=7, fontweight='bold', color=ORANGE)

    law_line(ax, 'en', label=False, x=LAW_X)
    ax.set_xlim(2018.45, 2025.55)
    ax.set_ylim(0, 2110)
    ax.set_yticks([0, 500, 1000, 1500, 2000])
    ax.yaxis.set_major_formatter(thousands('en'))
    ax2.set_ylim(95, 102.53)
    ax2.set_yticks([96, 97, 98, 99, 100])
    ax2.set_ylabel('Panel retention (%)', fontsize=8, labelpad=1)
    ax2.grid(False)
    ax2.spines['top'].set_visible(False)
    ax2.tick_params(labelsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{int(y)}\n{n}' for y, n in zip(x, reporting)], linespacing=1.3)
    ax.set_xlabel('Year · n reporting', fontsize=8)
    ax.set_ylabel('Discharges (thousands)', fontsize=8, labelpad=1)
    clean(ax)
    leg = ax.legend(handles=ax.get_legend_handles_labels()[0] + [retention_proxy],
                    loc='upper right', fontsize=6.8, handlelength=1.5, handletextpad=0.5,
                    labelspacing=0.3, borderpad=0.4, frameon=True, framealpha=1,
                    edgecolor=LIGHT, facecolor='white',
                    title='Hospital activity/capacity;\nnot a population denominator')
    leg.get_frame().set_linewidth(0.6)
    leg.get_title().set_fontsize(6.6)
    leg.get_title().set_color(GREY_DARK)
    leg.get_title().set_linespacing(1.15)
    leg.set_zorder(5)


# ---------------------------------------------------------------------------- panel (f)
#: colour of a source column by what one row of it is
NATURE = {'Flow': BLUE, 'Stock': ORANGE, 'Activity/capacity': GREY,
          'Cross-sectional survey': GREEN, 'School stock': PINK}
#: marker of a break by its kind, with the plate's sizes
KIND = {'Definition/code change': ('D', 2.9, BLACK),
        'Panel/coverage/schema change': ('s', 2.7, GREY_DARK),
        'Series start': ('^', 2.5, BLACK)}
BAR_HALF = 0.42     # a source bar spans its first year - 0.42 to its last year + 0.42


def panel_f(ax):
    t = pd.read_csv(TABLES / "S_definition_breaks.csv", encoding='utf-8-sig')
    order = list(dict.fromkeys(t.Source))            # the plate's column order: first appearance
    ax.axhspan(*BAND_X, color=BAND, alpha=0.6, lw=0, zorder=0)
    ax.axhline(LAW_X, color='#444444', ls=(0, (1, 2)), lw=0.9, zorder=1)
    for i, src in enumerate(order):
        s = t[t.Source == src]
        span = s.Years.iloc[0].split('–')          # '2019–2024', or '2022' for a single year
        lo, hi = int(span[0]), int(span[-1])
        ax.add_patch(Rectangle((i - 0.3, lo - BAR_HALF), 0.6, hi - lo + 2 * BAR_HALF,
                               facecolor=NATURE[s['Stock/flow'].iloc[0]], alpha=0.45, lw=0,
                               zorder=2))
        for _, b in s.iterrows():
            marker, size, colour = KIND[b.Kind]
            ax.plot([i], [int(b['Break year'])], marker=marker, markersize=size, color=colour,
                    markeredgecolor=BLACK, markeredgewidth=0.5, ls='none', zorder=4)
    ax.set_xlim(-0.75, len(order) - 0.25)
    ax.set_ylim(2018.45, 2025.5)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=90, fontsize=6.8)
    ax.set_yticks(YEARS)
    ax.set_yticklabels([str(y) for y in YEARS])
    ax.set_ylabel('Reporting year', fontsize=8)
    clean(ax)
    ax.tick_params(axis='x', length=0)
    handles = [Line2D([], [], marker=m, markersize=s, color=c, markeredgecolor=BLACK,
                      markeredgewidth=0.5, ls='none', label=k) for k, (m, s, c) in KIND.items()]
    leg = ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.285),
                    fontsize=6.5, handletextpad=0.6, labelspacing=0.3, borderpad=0.2,
                    title='Each break, in the definition-breaks table')
    leg.get_title().set_fontsize(6.5)
    leg.get_title().set_color(GREY_DARK)


# ---------------------------------------------------------------------------- the plate
#: (a) is a drawn table, so every panel is placed by hand, as the stored plate places them
BOXES = {'a': (0.0276, 0.7625, 0.4129, 0.2105), 'b': (0.5735, 0.7630, 0.3710, 0.2194),
         'c': (0.0845, 0.4813, 0.3515, 0.2193), 'd': (0.5735, 0.4813, 0.3710, 0.2193),
         'e': (0.0780, 0.1179, 0.3580, 0.2197), 'f': (0.5735, 0.1179, 0.3710, 0.2134)}
HEADINGS = {'a': 'States of a REM cell', 'b': 'Coverage layers, 2019–2025',
            'c': 'REM establishments by era', 'd': 'GRD hospitals and episodes',
            'e': 'REM-20: 188-panel and retention', 'f': 'Breaks by source, 2019–2025'}
#: where the stored plate puts each panel heading (figure coordinates, baseline of the text)
HEAD_XY = {'a': (0.013, 0.9853), 'b': (0.5115, 0.9853), 'c': (0.010, 0.7032),
           'd': (0.5115, 0.7032), 'e': (0.010, 0.3410), 'f': (0.5115, 0.3410)}


def draw():
    style()
    plt.rcParams.update({'xtick.labelsize': 7, 'ytick.labelsize': 7})
    fig = plt.figure(figsize=(6.89, 9.38))
    axes = {k: fig.add_axes(BOXES[k]) for k in 'abcdef'}
    for key, panel in zip('abcdef', (panel_a, panel_b, panel_c, panel_d, panel_e, panel_f)):
        panel(axes[key])
    for key in 'abcdef':
        x, y = HEAD_XY[key]
        fig.text(x, y, f'({key}) {HEADINGS[key]}', fontweight='bold', fontsize=9,
                 ha='left', va='baseline')
    return fig
