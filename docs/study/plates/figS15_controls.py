"""figS15 — reproduction controls: the pre-specified expected value against the value the pipeline observed.

Redraw of the stored plate `docs/study/corpus/figures/figS15_controls.jpg`. The original was drawn by
`study/pipeline/` from the control files of every module (`outputs/controls/*_controls.csv`), which this
repository does not carry; the six panels are rebuilt here from two published companion tables that do
carry the plotted material:

  * `S15_controls_scatter.csv` — the plotted set itself, 650 numeric controls of the phase-1 and phase-2
    modules with their module, control, key, expected value, observed value, relative difference, status
    and curated explanation. Panels a, b, d, e and f are this table and nothing else.
  * `M10_reproduction_controls.csv` — the count of checks, matches, informative controls and documented
    differences per module. Panel c needs it because its bars are 823 checks, not 650: the informative
    controls (counts and runtimes, no expected value) have no point to plot and are therefore absent from
    S15, so the per-module row counts of S15 (79, 84, 183, 81, 66, 24, 71, 56, 6) would print the wrong
    totals. M10 also lists modules 08b–17; the plate deliberately shows only the nine phase-1/phase-2
    modules 00–07 and so does this module.

There is no estimator anywhere on this plate: every panel compares a value fixed in advance (the study
brief, DATA_REVIEW.md, a manifest or config.CONTROLS) with the value the pipeline reproduced, so the only
requirement is to parse the two tables faithfully. The presentation cells carry thousands separators and a
typographic minus; panel b plots the table's own 'Relative difference (%)', which is '—' for the 82
controls whose expected value is zero, so the panel keeps the 568 controls whose parsed expected value is
not zero rather than filtering on that string. The eleven controls whose status is 'differs (explained)'
are the ones ringed and numbered in panels a, b, d and e and listed in panel f, in table order, which is
the order the plate prints them.

Two things the tables do not store and that this module fixes from the stored plate: the axis limits of
the symlog panels (the plate shows the zero row at the bottom of the linear segment and leaves about 1.6
decades of headroom above the largest value, i.e. limits of −0.5 to 40 × the largest value, the same on
both axes, so the identity runs corner to corner) and the offsets of the eleven numbered labels, which the
original placed with a repulsion pass whose result is not recorded anywhere; they are placed here by a
documented no-overlap rule, so the numbering and the points are the plate's but the exact offsets are not.

The plate, like the corpus, is English only.
"""
import numpy as np
import pandas as pd
from matplotlib.ticker import LogLocator, SymmetricalLogLocator
from figstyle import *

PLATE = "figS15_controls"
SOURCES = ["docs/study/corpus/tables/S15_controls_scatter.csv",
           "docs/study/corpus/tables/M10_reproduction_controls.csv"]
NOTE = ("Redraws the six panels of figure S15 from the two published control tables: the 650 numeric "
        "reproduction controls of modules 00–07 (expected against observed, their relative difference and "
        "the eleven documented differences) and the per-module count of matches, differences and "
        "informative controls.")

SCATTER = BASE / "corpus" / "tables" / "S15_controls_scatter.csv"
STATUS = BASE / "corpus" / "tables" / "M10_reproduction_controls.csv"

BROWN = '#8c564b'       # the ninth module colour of the plate, outside the eight Okabe-Ito hues
DARKRED = '#8B0000'     # the ring and the 'differs' bar of the plate

#: module label of the plate, its colour, and the row key of M10, in the plate's legend order.
MODULES = [('00 provenance', BLUE, '00_provenance'),
           ('01 GRD', ORANGE, '01_grd_core'),
           ('01b DEIS', GREEN, '01b_deis_egresos'),
           ('02 REM', PINK, '02_rem_pathway'),
           ('03 denominators', GOLD, '03_denominators'),
           ('04 surveys', SKY, '04_surveys'),
           ('05 education', YELLOW, '05_education'),
           ('06 models', BLACK, '06_models'),
           ('07 controls', BROWN, '07_controls')]

DETAIL_D = ['01 GRD', '01b DEIS']                                   # panel d
DETAIL_E = ['02 REM', '03 denominators', '04 surveys',              # panel e
            '05 education', '06 models']

HEADINGS = [('a', '(a) Reproduction controls: observed vs\nexpected'),
            ('b', '(b) Relative difference by expected magnitude'),
            ('c', '(c) Control status by module'),
            ('d', '(d) GRD and DEIS (modules 01, 01b)'),
            ('e', '(e) REM, denominators, surveys, education\nand models (02–06)'),
            ('f', '(f) Controls that differ and their explanation')]

#: axes rectangles measured on the stored plate (figure fractions), three rows of two.
COL_X, ROW_Y, AX_W, AX_H = (0.128, 0.598), (0.7054, 0.3777, 0.0345), 0.3985, 0.2623
RECT = {k: (COL_X[i % 2], ROW_Y[i // 2], AX_W, AX_H) for i, (k, _) in enumerate(HEADINGS)}

TOLERANCE = 0.5         # the +/- band of panel b, in per cent
HEADROOM = 40           # upper symlog limit, as a multiple of the largest value of the panel
FLOOR = -0.5            # lower symlog limit, inside the linear segment so the zero row is visible
DOT, RING, EDGE = 25, 70, 0.4   # marker area, ring area (points squared) and the markers' white edge
WRAP = 62               # characters per line of panel f
CLOSING = ('The explanation of each difference is printed in full in the reproduction-controls table of '
           'the supplementary material.')

FS_HEAD, FS_LABEL, FS_TICK, FS_TICK_C = 8.8, 7.8, 5.8, 6.85
FS_LEG, FS_SMALL, FS_LIST, FS_TAG, FS_BAND = 6.0, 6.2, 6.0, 6.5, 6.8


def _number(cell):
    """A presentation cell such as '8,221', '0.0029' or '20,844,484,687' as a float."""
    return float(str(cell).replace(',', '').replace('−', '-').strip())


def load_controls():
    """The 650 numeric reproduction controls, with expected, observed and their difference parsed out.

    'Relative difference (%)' is the figure the pipeline itself recorded and the figure panel b plots; it
    is not recoverable from the two rounded presentation cells beside it (the four weighted survey
    controls of module 04, expected 0.0029 to 0.0286, print the same rounded expected and observed value
    and would collapse onto zero if the panel recomputed them). It is '—' for the 82 controls whose
    expected value is zero, and those never reach panel b.
    """
    t = pd.read_csv(SCATTER, encoding='utf-8-sig', dtype=str)
    rel = t['Relative difference (%)'].map(lambda c: np.nan if str(c).strip() == '—' else _number(c))
    return t.assign(expected=t.Expected.map(_number), observed=t.Observed.map(_number), rel=rel)


def load_status():
    """Checks, matches, differences and informative controls per module, modules 00-07 only."""
    t = pd.read_csv(STATUS, encoding='utf-8-sig', dtype=str)
    keys = {key: label for label, _, key in MODULES}
    t = t[t.Module.isin(keys)].copy()
    for c in ('Checks', 'Match', 'Informative', 'Differ'):
        t[c] = t[c].map(_number).astype(int)
    t['label'] = t.Module.map(keys)
    return t.set_index('label').loc[[label for label, _, _ in MODULES]]


# --------------------------------------------------------------------------- numbered labels

def _boxes_overlap(a, b, pad=1.0):
    return (a[0] - pad < b[2] and b[0] - pad < a[2] and a[1] - pad < b[3] and b[1] - pad < a[3])


def _place_tags(ax, xy, tags, others=None, fontsize=FS_TAG):
    """Write the index of each differing control beside its ringed marker.

    The stored plate placed these eleven labels with a repulsion pass that no published file records, so
    they are placed here by a rule instead: try a fixed sequence of offsets around the point and take the
    first that clears every label already written, every ringed marker and every plotted point. Points
    that coincide (controls 3 and 10 share (0, 1); 1 and 8, and 2 and 9, share their coordinates exactly)
    therefore get stacked labels, as they do on the plate.
    """
    px = ax.transData.transform(np.asarray(xy, float))
    rest = ax.transData.transform(np.asarray(others, float)) if others is not None else np.empty((0, 2))
    dpi = ax.figure.dpi
    ring = 0.5 * np.sqrt(RING) * dpi / 72 + 1.5            # keep clear of the ring itself
    dot = 0.5 * np.sqrt(DOT) * dpi / 72                    # and of the plotted markers
    frame = ax.get_window_extent()
    placed = []
    for (cx, cy), tag in zip(px, tags):
        w = 0.66 * fontsize * len(tag) * dpi / 72
        h = 0.80 * fontsize * dpi / 72
        for radius in (10, 14, 19, 25, 32, 40):
            for angle in (25, 90, 155, 0, 180, 60, 120, 335, 205, 300, 240, 270):
                r = radius * dpi / 72
                ox, oy = r * np.cos(np.radians(angle)), r * np.sin(np.radians(angle))
                box = (cx + ox - w / 2, cy + oy - h / 2, cx + ox + w / 2, cy + oy + h / 2)
                if not (frame.x0 < box[0] and box[2] < frame.x1
                        and frame.y0 < box[1] and box[3] < frame.y1):
                    continue                                   # a label never leaves the panel
                if any(_boxes_overlap(box, b) for b in placed):
                    continue
                if any(abs(qx - (cx + ox)) < ring + w / 2 and abs(qy - (cy + oy)) < ring + h / 2
                       for qx, qy in px):
                    continue
                if len(rest) and np.any((np.abs(rest[:, 0] - (cx + ox)) < dot + w / 2)
                                        & (np.abs(rest[:, 1] - (cy + oy)) < dot + h / 2)):
                    continue
                placed.append(box)
                break
            else:
                continue
            break
        else:
            box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            placed.append(box)
        x, y = ax.transData.inverted().transform(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
        ax.annotate(tag, (x, y), ha='center', va='center', fontsize=fontsize, fontweight='bold',
                    color=DARKRED, zorder=6, annotation_clip=False)


# --------------------------------------------------------------------------- panels

def _symlog_panel(ax, t, labels, rotate_x=False):
    """One observed-against-expected panel: symlog on both axes, the identity, the modules, the rings."""
    sub = t[t.Module.isin(labels)]
    top = HEADROOM * max(sub.expected.max(), sub.observed.max())
    ax.set_xscale('symlog', linthresh=1)
    ax.set_yscale('symlog', linthresh=1)
    ax.plot([FLOOR, top], [FLOOR, top], ls='--', lw=1.1, color=GREY, zorder=1, label='identity')
    for label, colour, _ in MODULES:
        if label not in labels:
            continue
        d = sub[sub.Module == label]
        ax.scatter(d.expected, d.observed, s=DOT, color=colour, alpha=0.8,
                   edgecolors='white', linewidths=EDGE,
                   label=label, zorder=2 + labels.index(label) / 100)
    differs = sub[sub.Status != 'matches']
    ax.scatter(differs.expected, differs.observed, s=RING, facecolors='none', edgecolors=DARKRED,
               linewidths=1.3, zorder=5)
    ax.set_xlim(FLOOR, top)
    ax.set_ylim(FLOOR, top)
    ax.xaxis.set_major_locator(SymmetricalLogLocator(linthresh=1, base=10))
    ax.yaxis.set_major_locator(SymmetricalLogLocator(linthresh=1, base=10))
    ax.set_xlabel('Expected (symlog scale)', fontsize=FS_LABEL, labelpad=2)
    ax.set_ylabel('Observed (symlog scale)', fontsize=FS_LABEL, labelpad=2)
    clean(ax, grid='both')
    ax.tick_params(axis='both', length=0, labelsize=FS_TICK)
    if rotate_x:
        plt.setp(ax.get_xticklabels(), rotation=90, ha='center', va='top')
    handles, names = ax.get_legend_handles_labels()
    order = list(range(1, len(names))) + [0]                 # the identity is written last
    leg = ax.legend([handles[i] for i in order], [names[i] for i in order], loc='upper left',
                    fontsize=FS_LEG, handlelength=1.4, handletextpad=0.5,
                    labelspacing=0.35, borderpad=0.3, borderaxespad=0.4, frameon=True,
                    framealpha=1, edgecolor='none')
    leg.set_zorder(7)
    return differs


def numbering(t):
    """The plate numbers the controls that differ 1 to 11, in table order, everywhere they appear."""
    return {k: str(i) for i, k in enumerate(t.index[t.Status != 'matches'], start=1)}


def panel_a(ax, t, tag_of):
    differs = _symlog_panel(ax, t, [label for label, _, _ in MODULES], rotate_x=True)
    _place_tags(ax, list(zip(differs.expected, differs.observed)), [tag_of[k] for k in differs.index],
                list(zip(t.expected, t.observed)))


def panel_b(ax, t, tag_of):
    """Relative difference against expected magnitude, expected != 0, with the +/-0.5% tolerance band."""
    sub = t[t.expected != 0]
    lo, hi = np.log10(sub.expected.min() / 5), np.log10(sub.expected.max() * 5)
    pad = 0.05 * (hi - lo)
    ax.set_xscale('log')
    ax.axhspan(-TOLERANCE, TOLERANCE, color=GREEN, alpha=0.12, lw=0, zorder=0)
    ax.axhline(0, color=GREY, lw=0.9, zorder=1)
    for label, colour, _ in MODULES:
        d = sub[sub.Module == label]
        ax.scatter(d.expected, d.rel, s=DOT, color=colour, alpha=0.8, edgecolors='white',
                   linewidths=EDGE, zorder=2)
    differs = sub[sub.Status != 'matches']
    ax.scatter(differs.expected, differs.rel, s=RING, facecolors='none', edgecolors=DARKRED,
               linewidths=1.3, zorder=5)
    ax.set_xlim(10 ** (lo - pad), 10 ** (hi + pad))
    ax.set_ylim(-1.4 * sub.rel.abs().max(), 1.4 * sub.rel.abs().max())
    ax.xaxis.set_major_locator(LogLocator(base=10, numticks=8))
    ax.set_xlabel('Expected (log scale; expected ≠ 0)', fontsize=FS_LABEL, labelpad=2)
    ax.set_ylabel('100 × (observed − expected) / expected', fontsize=FS_LABEL, labelpad=2)
    ax.text(0.995, 0.979, f'±{num(TOLERANCE, "en", 1)}% tolerance', transform=ax.transAxes,
            ha='right', va='top', fontsize=FS_BAND, color=GREEN)
    clean(ax, grid='both')
    ax.tick_params(axis='both', length=0, labelsize=FS_TICK)
    _place_tags(ax, list(zip(differs.expected, differs.rel)), [tag_of[k] for k in differs.index],
                list(zip(sub.expected, sub.rel)))


def panel_c(ax, status):
    """Controls per module and status: matches, documented differences, informative (no expected value)."""
    y = np.arange(len(status))
    segments = [('matches', status.Match.values, GREEN, 'w'),
                ('differs (explained)', status.Differ.values, DARKRED, 'w'),
                ('informative (no expected value)', status.Informative.values, LIGHT, BLACK)]
    left = np.zeros(len(status))
    top = status.Checks.max() * 1.16
    for name, width, colour, textcolour in segments:
        ax.barh(y, width, left=left, color=colour, label=name)
        for yi, w, l in zip(y, width, left):
            if w >= 0.05 * top:
                bbox = dict(facecolor='white', edgecolor='none', pad=0.9) if textcolour == BLACK else None
                ax.text(l + w / 2, yi, num(w, 'en'), ha='center', va='center', color=textcolour,
                        fontsize=FS_SMALL, bbox=bbox)
        left = left + width
    for yi, total in zip(y, status.Checks.values):
        ax.annotate(num(total, 'en'), (total, yi), xytext=(2.5, 0), textcoords='offset points',
                    ha='left', va='center', fontsize=FS_SMALL, color=BLACK)
    ax.set_yticks(y)
    ax.set_yticklabels(status.index)
    ax.invert_yaxis()
    ax.set_xlim(0, top)
    ax.set_xlabel('Number of controls', fontsize=FS_LABEL, labelpad=2)
    clean(ax, grid='x')
    ax.tick_params(axis='both', length=0, labelsize=FS_TICK_C)
    ax.legend(loc='lower right', fontsize=FS_LEG, handlelength=1.4, handletextpad=0.5, labelspacing=0.35,
              borderpad=0.4, frameon=True, framealpha=1, edgecolor='0.8')


def _detail(ax, t, labels, tag_of):
    differs = _symlog_panel(ax, t, labels)
    sub = t[t.Module.isin(labels)]
    _place_tags(ax, list(zip(differs.expected, differs.observed)), [tag_of[k] for k in differs.index],
                list(zip(sub.expected, sub.observed)))


def _chunks(s):
    """The pieces panel f may break a line at: after every space and after every underscore."""
    out, cur = [], ''
    for ch in s:
        cur += ch
        if ch in ' _':
            out.append(cur)
            cur = ''
    if cur:
        out.append(cur)
    return out


def _wrap(s, indent='    ', width=WRAP):
    """Fold one entry of panel f, hanging the continuation, exactly where the stored plate folds it."""
    lines, cur, prefix = [], '', ''
    for chunk in _chunks(s):
        if cur and len((prefix + cur + chunk).rstrip()) > width:
            lines.append((prefix + cur).rstrip())
            prefix, cur = indent, chunk
        else:
            cur += chunk
    lines.append((prefix + cur).rstrip())
    return lines


def panel_f(ax, t):
    """The numbered list of the controls that differ, with the value each one moved from and to."""
    ax.axis('off')
    differs = t[t.Status != 'matches']
    body = []
    for i, (_, r) in enumerate(differs.iterrows(), start=1):
        body += _wrap(f'{i}. {r.Module} · {r.Control}: {r.Expected} → {r.Observed}')
    body += [''] + _wrap(CLOSING, indent='')
    ax.text(0.005, 1.0, '\n'.join(body), transform=ax.transAxes, ha='left', va='top',
            fontsize=FS_LIST, color=BLACK, linespacing=1.25)


# --------------------------------------------------------------------------- plate

def draw():
    style()
    t = load_controls()
    status = load_status()
    fig = plt.figure(figsize=(6.89, 9.38))
    ax = {k: fig.add_axes(RECT[k]) for k, _ in HEADINGS}
    tag_of = numbering(t)
    panel_a(ax['a'], t, tag_of)
    panel_b(ax['b'], t, tag_of)
    panel_c(ax['c'], status)
    _detail(ax['d'], t, DETAIL_D, tag_of)
    _detail(ax['e'], t, DETAIL_E, tag_of)
    panel_f(ax['f'], t)
    for key, heading in HEADINGS:
        x0, y0, _, h = RECT[key]
        fig.text(0.0125 if x0 < 0.5 else 0.513, y0 + h + 0.0021, heading, fontweight='bold',
                 fontsize=FS_HEAD, ha='left', va='bottom', linespacing=1.05)
    return fig
