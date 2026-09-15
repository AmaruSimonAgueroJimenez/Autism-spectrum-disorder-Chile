"""figE23 — ENDIDE 2022 and ENCAVI 2023–2024 read with their own complex sampling design.

Redraw of the stored plate `docs/study/corpus/figures/figE23_surveys_detail.jpg`. The original was
drawn by `study/pipeline/` from the two survey microdata files, which this repository does not carry;
the six panels are rebuilt here from the published companion table `E23_surveys_detail.csv`, which
prints every domain and every subgroup of the plate with its estimate, its interval, its unweighted
cases, its domain size, its DEFF, its relative standard error and its precision verdict.

Nothing is recomputed. These are survey-weighted estimates — a ratio estimator with Taylor
linearisation and a logit-scale 95% CI on t with df = PSU − strata (8,445 for ENDIDE, 254 for
ENCAVI) — so the only honest thing to do with them is to read them off the table and plot them.
The cell `% (95% CI)` is parsed for the point and the two limits and is ALSO printed verbatim as the
row label, which is why the printed labels cannot drift from the plotted points. Dividing cases by n
would be a different estimator and a different number: 72/30,010 = 0.24% against the published
weighted 0.29% for the ENDIDE adult total.

Two columns of the table carry the plate's editorial decisions and are obeyed rather than re-derived:

* `Precision` drives the grey/blue coding of panels a–c and supplies the second line printed under a
  flagged row. It is not a rule this module reapplies: ENCAVI 30–49 years has 30 cases and an RSE of
  30.8% and the table still calls it an adequate domain, and the plate accordingly draws it blue,
  while ENCAVI 20–29 years with 28 cases is grey.
* `RSE` is the relative standard error of E23, the one panel (e) plots. The companion table E75
  carries a field of the same name inside its packed `DEFF; RSE; df; PSU; strata` cell which is on a
  different scale (it reads 0.1% where E23 reads 14.0% for the same ENDIDE adult domain); E75 is not
  read here.

Panels d–f summarise the DOMAIN — the ten `Domain total` rows — exactly as the original did; the sex
and age subgroups live in panels a–c and complete in the companion table. Their bars are sorted
ascending and drawn from the bottom up, which is what puts `rep.+conf.` above `reported` where both
have DEFF 1.54 and `treat.|rep.` above `medic.|rep.` where both have RSE 9.2%.

The plate, like the table and the caption, is English only.

Deviations from the stored image, all of them cosmetic and all of them checked pixel by pixel:
the three forest axes end 0.3-0.9% short of the original's right-hand limit, because the label-fit
loop starts from a slightly different estimate of the panel width (markers and whisker ends land
within two pixels of the original at the plate's own size); and the (e) threshold label, which the
original's de-collision pass pushes a further 33 px clear of the 30% rule, is written here one
space to the left of that rule. Everything plotted — every point, interval, bar, order, colour and
printed figure — matches the stored plate.
"""
import re

import numpy as np
from matplotlib.ticker import FuncFormatter

from figstyle import *

PLATE = "figE23_surveys_detail"
SOURCES = ["docs/study/corpus/tables/E23_surveys_detail.csv"]
NOTE = ("Redraws the six panels of E23 from the published E23 companion table: the survey-weighted "
        "proportion, logit 95% CI and unweighted cases of the three estimation domains by sex and age, "
        "and the DEFF, relative standard error and case count of the ten domain totals.")

TABLE = BASE / "corpus" / "tables" / "E23_surveys_detail.csv"

# --- the plate's own measurements ------------------------------------------------------------------
#: The stored plate is 180 x 245 mm; every fraction below was measured on it at 1000 x 1361 px.
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4
REF_H = 1361.0                   # height of that reference render
AX_X = (0.1840, 0.6820)          # left edge of the two panel columns, figure fraction
AX_W = 0.2980                    # panel width, figure fraction
AX_TOP = (53.0, 500.0, 925.0)    # top of the three panel rows, in reference pixels
AX_H_PX = 336.5                  # panel height, in reference pixels
TITLE_X = (0.0110, 0.5085)       # the panel headings sit at the left edge of their cell
TITLE_DY = 3.0 / REF_H           # and just above the top of their panel
#: Useful width of a panel heading: half the plate, less a 5 mm margin and the room for the letter.
TITLE_W_PT = FIG_W_IN * 72.0 / 2 - 5.0 / 25.4 * 72.0 - 12.0

FS_TITLE, FS_BASE, FS_TICK, FS_LEGEND = 9.0, 8.0, 7.0, 7.0
FS_ROW = 6.2                     # the estimate/interval/cases label of a forest row
FS_TINY = 6.4                    # the domain labels of panels d–f, and the plate foot
FOOT_LINE = 1.30

RED = '#c0392b'                  # threshold lines and the regional-domains note
INK = '#333333'                  # a reliable row's label, and the DEFF = 1 reference
MUTED = '#555555'                # the 'n=' labels of panel f and the plate foot
DIM = '#7f8c8d'                  # a flagged row: marker, interval and label
DIM_ALPHA = 0.55

ADEQUATE = 'Adequate domain'     # the value of `Precision` that the plate draws in blue

#: Compact, unique label of each domain for the y axis of panels d–f (the table's own `Domain`
#: strings are too long for a half-plate panel, and truncating them collided two ENDIDE domains).
TINY = {
    'ENDIDE adults: reported': 'ENDIDE 18+: reported',
    'ENDIDE children: reported': 'ENDIDE 2–17: reported',
    'ENDIDE children: reported & confirmed': 'ENDIDE 2–17: rep.+conf.',
    'ENDIDE children: confirmed | reported': 'ENDIDE 2–17: conf.|rep.',
    'ENDIDE children: confirmed (sens.)': 'ENDIDE 2–17: conf. (sens.)',
    'ENDIDE children: medication | reported': 'ENDIDE 2–17: medic.|rep.',
    'ENDIDE children: other treatment | reported': 'ENDIDE 2–17: treat.|rep.',
    'ENCAVI 15+: diagnosed': 'ENCAVI 15+: diagnosed',
    'ENCAVI 15+: diagnosed (sens.)': 'ENCAVI 15+: diag. (sens.)',
    'ENCAVI: in treatment | diagnosed': 'ENCAVI 15+: treat.|diag.',
}

#: Panel a–c: (heading, the `Domain` whose rows the forest draws, foot note and its colour).
FOREST = [
    ('ENDIDE 2022, adults aged 18 and over', 'ENDIDE adults: reported', None, None),
    ('ENDIDE 2022, children and adolescents aged 2–17', 'ENDIDE children: reported',
     'Additional series: professional confirmation of the report (companion table).', MUTED),
    ('ENCAVI 2023–2024, persons aged 15 and over', 'ENCAVI 15+: diagnosed',
     'Regional domains: not estimated (effective sample does not support them); '
     'no comuna disaggregation.', RED),
]

RSE_THRESHOLD = 30.0             # the reliability thresholds the plate draws
CASE_THRESHOLD = 30


def _int(cell):
    """A count out of a presentation cell such as '30,010' or '5,526'."""
    return int(str(cell).replace(',', '').strip())


def _pct(cell):
    """Point estimate and the two interval limits out of a cell such as '0.29 (0.22–0.38)'."""
    a, lo, hi = re.match(r'\s*([\d.]+)\s*\(\s*([\d.]+)\s*[–-]\s*([\d.]+)\s*\)\s*$', str(cell)).groups()
    return float(a), float(lo), float(hi)


def load():
    """The E23 companion table with every plotted number parsed out of its presentation cell."""
    t = pd.read_csv(TABLE, encoding='utf-8-sig')
    pct = t['% (95% CI)'].map(_pct)
    return t.assign(ci_text=t['% (95% CI)'],
                    n_dom=t['n'].map(_int),
                    cases=t['Cases'].map(_int),
                    pct=[p[0] for p in pct],
                    lo=[p[1] for p in pct],
                    hi=[p[2] for p in pct],
                    deff=t['DEFF'].astype(float),
                    rse=t['RSE'].str.rstrip('%').astype(float),
                    reliable=t['Precision'].eq(ADEQUATE))


def _dec(ax, dec):
    """The plate's x axis: a fixed number of decimals, thousands separated."""
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: num(v, 'en', dec)))


def _panel(fig, row, col):
    """One panel of the 3 x 2 plate, at the position measured on the stored image."""
    return fig.add_axes([AX_X[col], 1 - (AX_TOP[row] + AX_H_PX) / REF_H, AX_W, AX_H_PX / REF_H])


def _heading(fig, ax, letter, text):
    """The bold heading above a panel: '(a)' and the title, folded to the width of the cell."""
    words, lines, line = text.split(), [], ''
    for w in words:
        trial = (line + ' ' + w).strip()
        if line and _width_pt(fig, trial + ' ', FS_TITLE, 'bold') > TITLE_W_PT:
            lines.append(line); line = w
        else:
            line = trial
    lines.append(line)
    lines[0] = f'({letter}) ' + lines[0]
    pos = ax.get_position()
    fig.text(TITLE_X[0] if pos.x0 < 0.5 else TITLE_X[1], pos.y1 + TITLE_DY, '\n'.join(lines),
             fontsize=FS_TITLE, fontweight='bold', ha='left', va='bottom', linespacing=1.2)


def _width_pt(fig, s, size, weight='normal'):
    """Width of one line of text in points, measured on the figure that will carry it."""
    t = fig.text(0, 0, s, fontsize=size, fontweight=weight)
    w = t.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi * 72.0
    t.remove()
    return w


def forest(fig, ax, rows, heading, letter):
    """Panel a, b or c: one estimation domain, its total and its sex and age subgroups.

    The row label is anchored to the upper end of its own interval and the axis is then widened
    until the widest of them fits inside the panel — the plate's own rule, and the reason panel (b)
    reaches 12% for an estimate of 4.6% and panel (a) reaches 1.9% for one of 0.6%.
    """
    y = np.arange(len(rows))[::-1]
    labels = [r.ci_text + f'; n={r.cases}' + ('' if r.reliable else '\n' + r.Precision)
              for r in rows.itertuples()]

    # Starting width: the widest label gets its share of the panel, the interval keeps the rest.
    axis_pt = FIG_W_IN * 72.0 / 2.0 - 78.0
    w_pt = max(max(_width_pt(fig, line, FS_ROW) for line in s.split('\n')) for s in labels)
    share = min(0.62, w_pt / axis_pt)
    pad = 5.0 / axis_pt                      # the whisker cap (3 pt) plus 2 pt of white
    top = float(rows.hi.max())
    ax.set_xlim(0, max(top * 1.30, top / max(0.2, 1.0 - share - pad)))
    ax.set_ylim(-0.75, float(len(rows)) - 0.25)

    placed = []
    for i, r in enumerate(rows.itertuples()):
        colour = BLUE if r.reliable else DIM
        ax.errorbar(r.pct, y[i], xerr=[[max(r.pct - r.lo, 0.0)], [max(r.hi - r.pct, 0.0)]], fmt='o',
                    color=colour, markersize=6, capsize=3, lw=1.6,
                    alpha=1.0 if r.reliable else DIM_ALPHA)
        placed.append((ax.text(r.hi + pad * ax.get_xlim()[1], y[i], labels[i], fontsize=FS_ROW,
                               va='center', ha='left', linespacing=1.15,
                               color=INK if r.reliable else DIM), r.hi))

    ax.set_yticks(y)
    ax.set_yticklabels(list(rows.Subgroup), fontsize=7.5)
    ax.set_xlabel('Weighted proportion (%)', fontsize=FS_BASE)
    _dec(ax, 1)
    clean(ax, grid='both')
    _heading(fig, ax, letter, heading)
    return placed, pad


def fit_labels(fig, panels):
    """Widen each forest until its label column sits inside its panel.

    With the composition frozen the labels are measured as drawn and the axis is stretched — which
    pulls every label back towards the centre — until none of them crosses the right-hand edge.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax, (placed, pad) in panels:
        for _ in range(6):
            edge = ax.get_window_extent(r)
            over = max(t.get_window_extent(r).x1 - (edge.x1 - 1.0) for t, _h in placed)
            if over <= 0.5:
                break
            x1 = ax.get_xlim()[1] * (1.0 + over / max(edge.width, 1.0) * 1.12)
            ax.set_xlim(0, x1)
            for t, hi in placed:
                t.set_x(hi + pad * x1)
            fig.canvas.draw()
            r = fig.canvas.get_renderer()


def threshold(fig, ax, x, text):
    """The reliability threshold of panels e and f: a red rule and its label, kept inside the panel.

    Written to the right of the rule; where that would run past the edge of the panel — panel (e),
    whose axis stops barely past the 30% mark — it is pulled back to the left of the rule instead,
    which is where the stored plate prints it.
    """
    ax.axvline(x, color=RED, ls='--', lw=1.2)
    t = ax.text(x, 0.99, ' ' + text, transform=ax.get_xaxis_transform(), fontsize=FS_LEGEND,
                color=RED, va='top', ha='left')
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    if t.get_window_extent(r).x1 > ax.get_window_extent(r).x1:
        t.set_text(text + ' ')
        t.set_ha('right')


def domains(t):
    """The ten `Domain total` rows — the domain level that panels d–f summarise."""
    d = t[t.Subgroup == 'Domain total'].copy()
    d['short'] = d.Domain.map(TINY)
    assert d.short.notna().all() and len(d) == 10, 'unexpected domain totals in E23'
    return d


def bars(ax, d, values):
    """A ranked horizontal bar of one domain statistic: ascending, drawn from the bottom up."""
    y = np.arange(len(d))
    ax.barh(y, values, height=0.7, color=[BLUE if v else DIM for v in d.reliable])
    ax.set_yticks(y)
    ax.set_yticklabels(list(d.short), fontsize=FS_TINY)
    return y


def draw():
    style()
    plt.rcParams.update({'axes.labelsize': FS_BASE, 'xtick.labelsize': FS_TICK,
                         'ytick.labelsize': FS_TICK, 'lines.linewidth': 1.3, 'axes.linewidth': 0.7,
                         'xtick.major.size': 2.4, 'ytick.major.size': 2.4,
                         'xtick.major.pad': 1.8, 'ytick.major.pad': 1.8, 'axes.labelpad': 2.2})
    t = load()
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))

    # --- a, b, c: the three estimation domains, by sex and age group -------------------------------
    forests, notes = [], []
    for k, (heading, domain, note, colour) in enumerate(FOREST):
        ax = _panel(fig, k // 2, k % 2)
        rows = t[t.Domain == domain].reset_index(drop=True)
        placed = forest(fig, ax, rows, heading, 'abcdef'[k])
        forests.append((ax, placed))
        if note:
            notes.append((f'({"abcdef"[k]}) ' + note, colour))
    fit_labels(fig, forests)

    d = domains(t)

    # --- d: design effect by domain, against the DEFF = 1 reference ---------------------------------
    ax = _panel(fig, 1, 1)
    # Two ENDIDE child domains tie at DEFF 1.54 and, as in the stored plate, keep the table's order.
    dd = d.sort_values('deff', kind='stable')
    bars(ax, dd, dd.deff)
    ax.axvline(1.0, color=INK, ls='--', lw=0.9)
    ax.set_xlabel('DEFF', fontsize=FS_BASE)
    _dec(ax, 1)
    clean(ax, grid='both')
    _heading(fig, ax, 'd', 'Design effect (DEFF) by domain')

    # --- e: relative standard error by domain, against the 30% threshold ---------------------------
    ax = _panel(fig, 2, 0)
    # `RSE` is printed to one decimal and the two ENCAVI domains tie at 17.9%, as do the two ENDIDE
    # treatment domains at 9.2%. DEFF breaks the tie the way the unrounded error would: at the same
    # cases and the same domain size the relative error rises with the design effect.
    de = d.sort_values(['rse', 'deff'], kind='stable')
    bars(ax, de, de.rse)
    ax.set_xlim(0, RSE_THRESHOLD * 1.05)
    ax.set_xlabel('Relative standard error (%)', fontsize=FS_BASE)
    _dec(ax, 0)
    clean(ax, grid='both')
    threshold(fig, ax, RSE_THRESHOLD, '30% threshold')
    _heading(fig, ax, 'e', 'Relative standard error by domain')

    # --- f: unweighted cases and domain size, against the 30-case threshold ------------------------
    ax = _panel(fig, 2, 1)
    # Cases are exact integers: the three domains at 139 and the two at 80 keep the table's order.
    df = d.sort_values('cases', kind='stable')
    y = bars(ax, df, df.cases)
    for yi, r in zip(y, df.itertuples()):
        ax.text(r.cases * 1.10, yi, f'n={num(r.n_dom, "en", 0)}', fontsize=FS_ROW, va='center',
                color=MUTED)
    log_axis(ax, axis='x')
    ax.set_xlim(0.8, float(df.cases.max()) * 9)
    ax.set_ylim(-0.8, float(y.max()) + 2.4)     # a free band at the top for the threshold label
    ax.set_xlabel('Unweighted cases', fontsize=FS_BASE)
    clean(ax, grid='both')
    threshold(fig, ax, CASE_THRESHOLD, '30-case threshold')
    _heading(fig, ax, 'f', 'Unweighted cases and domain size')

    # --- the plate foot: the panel notes, greys first, the red note last ----------------------------
    line = FS_TINY * FOOT_LINE / (FIG_H_IN * 72.0)
    y0 = 0.004
    for text, colour in reversed(notes):
        fig.text(0.008, y0, text, fontsize=FS_TINY, color=colour, ha='left', va='bottom',
                 linespacing=FOOT_LINE)
        y0 += line + 0.35 * line
    return fig
