"""Plate E16 — A27 and A28 by region: counselling, assisted referral and the two rehabilitation entries.

The stored plate was drawn by `study/pipeline/14_extra_figures_rem.py` from the REM Serie A microdata,
which this repository does not carry. Every number its six panels print survives in the plate's own
published companion, `docs/study/corpus/tables/E16_rem_a27_a28_regional.csv`: a Series x Region x
2023–2025 table whose cells are the formatted strings `753 (52)` (count and the establishments that
filed it), `<5 (1)` (cell suppressed, fewer than five events, establishments still known) and
`not reported` (the region filed no row at all). The two missing states are NOT the same thing and the
plate keeps them apart — a grey cell with an em dash for the absent row, a grey cell labelled `<5` for
the suppressed one — so this module parses them as two distinct states and never turns either into a
zero. The second tracked file is read for one number per year:

* `docs/study/corpus/tables/E73_denominator_layers_full.csv` — the INE national resident population
  (2017-census-based projection, 30 June): 19,960,889 / 20,086,377 / 20,206,953. Panel (f) is the
  national total over that population. Only the NATIONAL row of E73 is used; its regional rows are
  doubled (the defect recorded for E15) and this plate needs no regional denominator.

Estimators, unchanged from the stored plate:

* unweighted administrative counts, no survey weighting and no standardisation anywhere;
* A27 counts INTERVENTIONS and A28 counts rehabilitation ENTRIES — neither counts persons, and
  neither is ever put into a ratio with another source;
* the annual figure is a FLOW, the sum of the months of COL01;
* panels (a)–(e) are counts; only panel (f) is a rate, and it is CRUDE and ECOLOGICAL — REM locates
  the provider, not the user's residence — which is why its axis label is written in that warning's
  colour on the stored plate;
* the bracketed number above each bar of panel (e) is the count of regions that filed at least one row
  for the code that year, recovered by counting the region rows that are not `not reported`.

Case definition: the F84 family excluding Rett syndrome (`sin_rett`) — the definition of the stored
plate and of its table. The corpus is English only, so this module is English only: it takes no
language argument and has no Spanish variant.

What is a reconstruction rather than a copy: the pipeline hands its finished figure to a decongestion
engine (`common.plate_fit` / `plate_resolve`) that measures the drawn plate and settles typography by
collision. Three of its results are visible on this plate and are rebuilt here directly, each in its
own helper and each verified against the stored image — the white backing behind a dark label written
on data ink, the strip of reporting establishments dropped clear of the year labels, and the search
that places the twelve value labels of panel (f). The values themselves are read, never arranged: the
figures drawn are the figures in the table.
"""
from pathlib import Path
import re
import sys
import textwrap

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

HERE = Path(__file__).resolve().parent          # docs/study/plates
STUDY = HERE.parent                             # docs/study
ROOT = STUDY.parent.parent                      # repository root
if str(STUDY) not in sys.path:                  # import figstyle the way the figure scripts do
    sys.path.insert(0, str(STUDY))
from figstyle import *                          # noqa: E402,F401,F403

PLATE = "E16_rem_a27_a28_regional"
SOURCES = [
    "docs/study/corpus/tables/E16_rem_a27_a28_regional.csv",
    "docs/study/corpus/tables/E73_denominator_layers_full.csv",
]
NOTE = ("Redraws the six panels of plate E16 — the region x year heatmaps of A27 counselling and "
        "assisted referral and of A28 primary- and hospital-level rehabilitation entries, the "
        "reporting establishments with the regions that filed a row, and the national crude rate per "
        "100,000 residents — from the published E16 table, taking the national INE population of "
        "panel (f) from the national row of E73.")

# --------------------------------------------------------------------------------------------------
# The plate's own canvas and typography (study/pipeline/14_extra_figures_rem.py): 180 x 245 mm, three
# rows by two columns in reading order, 9 pt bold panel titles down to the 6 pt floor of the norm.
# --------------------------------------------------------------------------------------------------
PLATE_W_IN, PLATE_H_IN = 180.0 / 25.4, 245.0 / 25.4
PLATE_ROWS, PLATE_COLS = 3, 2
FS_TITLE, FS_BASE, FS_TICK, FS_ANN, FS_CELL, FS_LETTER = 9.0, 8.0, 7.0, 6.4, 6.0, 10.0
FS_FLOOR = 6.0                                  # typographic floor of the norm: nothing printed is smaller
CELL_MARGIN = 2.0 / 180.0                       # left margin of a grid cell, in figure fraction (2 mm)
LETTER_GAP_PT = 22.0                            # the letter sits this far left of its title
# The title column: the cell, less its 2 mm margin, less the 22 pt the letter takes, less the 4 mm
# gutter the plate keeps between the two columns. The pipeline reaches the same width in two steps —
# it folds at cell − margin − letter and then `common._pl_title_fit` re-folds whatever would come
# within the gutter of the next cell — and it is that second step that decides panel (e)'s two lines.
TITLE_W_PT = (PLATE_W_IN * 72.0 / PLATE_COLS) - 2.0 * 72.0 / 25.4 - LETTER_GAP_PT - 4.0 * 72.0 / 25.4
XLABEL_W_PT = 150.0                             # usable width of a note under a panel
N_STRIP_GAP_PT = 6.0                            # clearance of the 'n=' strip under the year labels
YLABEL_H_PT = 138.0                             # usable height of an axes area: a longer y label folds
DARK, DASH_GREY, SUP_GREY, N_GREY = "#333333", "#777777", "#555555", "#555555"
ECOLOGICAL_RED = "#8a3b12"                      # the panel (f) x label, written in its warning's colour
BAD_GREY = "#e8e8e8"                            # the grey cell: no row filed, or the cell suppressed
VALUE_HALO = dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.80)
# `common._pl_backing` of the pipeline gives a white backing to every dark label that falls on data
# ink. A heat map is ink edge to edge, so every dark cell label of the stored plate carries one; a
# white label written on a dark cell does not, because its background is the cell itself.
CELL_HALO = dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9)

YEARS = [2023, 2024, 2025]                      # the four codes exist only from 2023
NATIONAL_ROW = "Chile (national total)"         # verbatim in the table's Region column
NOT_REPORTED = "not reported"                   # verbatim: the region filed no row
SUPPRESSED = "<5"                               # verbatim: the cell holds fewer than five events
DASH = "\u2014"                                 # the em dash the stored plate prints in a grey cell
# Series label, sequential map of its heat panel, colour-bar unit, x-axis unit, and the Okabe–Ito
# colour that carries the series through panels (e) and (f). The four labels are verbatim in the
# table's Series column, brackets and code number included.
SERIES = [
    ("Counselling (29101566)",           "Blues",   "Interventions", BLUE),
    ("Assisted referral (29101574)",     "Oranges", "Interventions", ORANGE),
    ("Primary rehabilitation (29101629)", "Greens",  "Entries",       GREEN),
    ("Hospital rehabilitation (29101651)", "Purples", "Entries",      PINK),
]
U_INTERVENTIONS = "Interventions (annual flow; not persons)"
U_REHAB = "Rehabilitation entries (annual flow)"
N_ESTAB = "n = reporting establishments"
TITLES = ["A27 counselling (M-CHAT-R/F) by region", "A27 assisted referral by region",
          "A28 primary-level rehabilitation by region", "A28 hospital-level rehabilitation by region",
          "Reporting establishments and regions with a report", "National totals per 100,000 residents"]
PER = 100_000.0
INE_LAYER = "INE population (2017-census-based projection, 30 June)"

_MEASURE = plt.figure(figsize=(1, 1))           # auxiliary canvas: used only to measure text


# --------------------------------------------------------------------------------- reading the tables
# The presentation table stores every cell as a formatted string. Three shapes, and only three:
#   "753 (52)"      a count and the establishments that filed it
#   "<5 (1)"        the count is suppressed (fewer than five events); the establishments are known
#   "not reported"  the region filed no row for that code that year — absence of reporting, not a zero
_CELL = re.compile(r"^\s*(<5|[\d.,]+)\s*(?:\(\s*([\d.,]+)\s*\))?\s*$")


def _num(s):
    """One formatted number -> float; blanks -> nan."""
    s = str(s).strip()
    return float(s.replace(",", "")) if s else float("nan")


def _cell(s):
    """'753 (52)' -> (753.0, 52.0, False); '<5 (1)' -> (nan, 1.0, True); 'not reported' -> (nan, nan, False)."""
    s = str(s).strip()
    if s == NOT_REPORTED:
        return float("nan"), float("nan"), False
    m = _CELL.match(s)
    if not m:
        raise ValueError(f"E16 cell in none of the three published shapes: {s!r}")
    n_est = _num(m.group(2)) if m.group(2) else float("nan")
    if m.group(1) == SUPPRESSED:
        return float("nan"), n_est, True
    return _num(m.group(1)), n_est, False


def _table(rel):
    """A tracked presentation table, read as text (they are written with a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str)


def read_e16():
    """The published E16 table -> regions, and one record per series.

    Each record carries the 16 x 3 matrices the plate needs: `total` (nan where the cell is missing for
    either reason), `suppressed` (True only for the '<5' cells), the national totals and reporting
    establishments, and `n_regions` — the regions that filed at least one row, which is the bracketed
    number above each bar of panel (e) and is recovered by counting the rows that are not
    'not reported'. A suppressed cell IS a filed row and counts towards it; an absent row is not."""
    t = _table(SOURCES[0])
    regions, out = None, {}
    for label, _cmap, _unit, _colour in SERIES:
        block = t[t["Series"] == label]
        if block.empty:
            raise KeyError(f"no rows for series {label!r} in the E16 table")
        rows = block[block["Region"] != NATIONAL_ROW]
        names = list(rows["Region"])
        if regions is None:
            regions = names
        elif names != regions:
            raise ValueError("the four series of the E16 table do not share one region order")
        parsed = [[_cell(v) for v in rows[str(y)]] for y in YEARS]     # year-major, then region
        total = np.array([[p[0] for p in col] for col in parsed]).T
        sup = np.array([[p[2] for p in col] for col in parsed]).T
        filed = np.array([[np.isfinite(p[0]) or p[2] for p in col] for col in parsed]).T
        nat = block[block["Region"] == NATIONAL_ROW]
        if len(nat) != 1:
            raise ValueError(f"series {label!r} has no single national row")
        pairs = [_cell(nat.iloc[0][str(y)]) for y in YEARS]
        out[label] = dict(total=total, suppressed=sup,
                          national=np.array([p[0] for p in pairs]),
                          n_est=np.array([p[1] for p in pairs]),
                          n_regions=filed.sum(axis=0))
    if len(regions) != 16:
        raise ValueError(f"the E16 table carries {len(regions)} regions, not the 16 of the plate")
    return regions, out


def national_population():
    """The INE national resident population of 2023–2025, from the national row of E73.

    Only the NATIONAL row is read. The regional rows of that file are doubled — the defect recorded
    against E15 — and this plate needs no regional denominator: its rates are national."""
    t = _table(SOURCES[1])
    hit = t[(t["Denominator layer"] == INE_LAYER) & (t["Dimension"] == "National total")
            & (t["Category"] == "Chile")]
    if len(hit) != 1:
        raise KeyError("no single national INE population row in E73")
    pop = np.array([_num(hit.iloc[0][str(y)]) for y in YEARS])
    if not (pop > 19e6).all():
        raise ValueError(f"the national INE population read from E73 is implausible: {pop}")
    return pop


# --------------------------------------------------------------------------------- typography helpers
def _width_pt(s, fontsize, weight="normal"):
    """Real typographic width of a string in points, measured with the font it will be drawn in."""
    r = _MEASURE.canvas.get_renderer()
    w, _h, _d = r.get_text_width_height_descent(str(s), FontProperties(size=fontsize, weight=weight), False)
    return w * 72.0 / _MEASURE.dpi


def wrap_measured(text, max_pt, fontsize, weight="normal"):
    """Line breaking by MEASURED width, not by character count — the rule of the stored plate.

    It is what decides that 'Reporting establishments and regions with a report' takes two lines and
    'National totals per 100,000 residents' takes one, and where each x-axis note breaks."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and _width_pt(trial, fontsize, weight) > max_pt:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return "\n".join(lines) if lines else str(text)


def long_xlabel(ax, text, fontsize=FS_ANN):
    """X-axis label carrying a methodological note, wrapped by measured width to the panel's cell."""
    ax.set_xlabel(wrap_measured(text, XLABEL_W_PT, fontsize), fontsize=fontsize)


def legend_wrapped(ax, loc="upper left", fontsize=FS_ANN, width=24):
    """The plate's legend: long labels fold into lines, and the axis is stretched to make room.

    `legend_wrapped` of the pipeline never shrinks the type; it folds each label at `width` characters
    and then calls `headroom`, which lifts the top of the axis by a fraction that grows with the number
    of legend LINES. With four labels of which three fold in two, that is seven lines, so the fraction
    is 0.030 + 0.062 x 7 = 0.464 — which is exactly what puts the top of panel (e) near 970 reporting
    establishments and the top of panel (f) at 140 per 100,000, as the stored plate's ticks show."""
    handles, labels = ax.get_legend_handles_labels()
    labels = [textwrap.fill(str(t), width) for t in labels]
    lines = max(len(labels), sum(str(t).count("\n") + 1 for t in labels))
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + (hi - lo) * min(0.62, 0.030 + 0.062 * lines))
    leg = ax.legend(handles, labels, loc=loc, fontsize=fontsize, borderpad=0.28, labelspacing=0.3)
    leg.set_in_layout(False)       # a legend wider than its axes would make the layout shrink the column
    return leg


# --------------------------------------------------------------------------------- the heat map panels
def heat(ax, total, suppressed, regions, cmap, cbar_label):
    """Region x year heat map with the plate's two distinct missing states.

    A cell with no row and a suppressed cell are both grey — neither has a value to place on the
    colour scale — but they are not the same fact and the plate says which is which: the absent row
    prints a grey em dash, the suppressed cell prints '<5'. The colour scale therefore runs over the
    cells that DO carry a count, and nothing is imputed into the others."""
    data = np.asarray(total, dtype=float)
    sup = np.asarray(suppressed, dtype=bool)
    mask = (~np.isfinite(data)) | sup
    cm = mpl.colormaps[cmap].resampled(256).copy()
    cm.set_bad(BAD_GREY)
    im = ax.imshow(np.ma.masked_array(data, mask), aspect="auto", cmap=cm)
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels([str(y) for y in YEARS], fontsize=FS_TICK)
    ax.set_yticks(range(len(regions)))
    ax.set_yticklabels(regions, fontsize=FS_ANN)
    ax.grid(False)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if sup[i, j]:
                txt, col = SUPPRESSED, SUP_GREY
            elif not np.isfinite(v):
                txt, col = DASH, DASH_GREY
            else:
                txt = num(v, "en")
                # The colour of the label is decided by the REAL luminance of its cell, not by a
                # threshold on the value: a threshold on the value drops white text onto pale cells.
                rr, gg, bb, _aa = im.cmap(im.norm(v))
                col = "white" if (0.2126 * rr + 0.7152 * gg + 0.0722 * bb) < 0.55 else DARK
            t = ax.text(j, i, txt, ha="center", va="center", fontsize=FS_CELL, color=col)
            if col != "white":
                t.set_bbox(dict(CELL_HALO))
    cb = ax.figure.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.ax.tick_params(labelsize=FS_ANN)
    cb.ax.yaxis.set_major_formatter(thousands("en"))    # '1,000', as every axis of the plate writes it
    cb.set_label(cbar_label, fontsize=FS_ANN, labelpad=2.0)
    return im


# --------------------------------------------------------------------------------- the value labels
# Panel (f) draws four series whose rates almost coincide in 2023 (19.8, 11.9, 3.7 and 3.4 per
# 100,000): a label written straight above its own marker lands on a neighbouring one. The pipeline
# defers every such label to `common.plate_value_label`, which is run on the FROZEN layout and tries
# growing offsets — up, down, right, left, then the diagonals — keeping the one that covers least
# marker, least of the panel's own edge and least of the labels already placed. The reduced version
# below is that search, with the same directions, the same step and the same weights; it is what puts
# the pink 3.7 of 2023 clear above the rest instead of inside the orange 3.4.
STEP_PT = 3.0
MAX_STEPS = 4
DIRS = ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1))
MARKER_COVER = 1.0 / 16.0                       # fraction of a marker disc a label may cover unnoticed


def _disc_samples(n_rings=4, n_ang=16):
    """Equal-area sampling of the unit disc, to estimate how much of a marker a text box covers."""
    pts = []
    for k in range(n_rings):
        rr = float(np.sqrt((k + 0.5) / n_rings))
        for j in range(n_ang):
            a = 2.0 * np.pi * (j + 0.5 * (k % 2)) / n_ang
            pts.append((rr * np.cos(a), rr * np.sin(a)))
    return np.asarray(pts, dtype=float)


_DISC = _disc_samples()


def _markers(ax):
    """Every marker of the panel as (x, y, radius) in screen pixels; markersize is a DIAMETER."""
    px = ax.figure.dpi / 72.0
    out = []
    for ln in ax.lines:
        if not ln.get_visible() or ln.get_marker() in (None, "", " ", "None"):
            continue
        pts = np.asarray(ln.get_transform().transform(ln.get_xydata()), dtype=float)
        pts = pts[np.isfinite(pts).all(axis=1)]
        rad = np.full((len(pts), 1), 0.5 * float(ln.get_markersize()) * px)
        if len(pts):
            out.append(np.hstack([pts[:, :2], rad]))
    return np.vstack(out) if out else np.zeros((0, 3))


def _cover(box, marks):
    """Fraction of each marker's disc covered by `box`, for the markers that touch it."""
    if not len(marks):
        return np.zeros(0)
    rad = marks[:, 2]
    near = ((marks[:, 0] >= box.x0 - rad) & (marks[:, 0] <= box.x1 + rad)
            & (marks[:, 1] >= box.y0 - rad) & (marks[:, 1] <= box.y1 + rad))
    idx = np.flatnonzero(near)
    fr = np.empty(len(idx))
    for i, j in enumerate(idx):
        pts = _DISC * rad[j] + marks[j, :2]
        fr[i] = float(((pts[:, 0] >= box.x0) & (pts[:, 0] <= box.x1)
                       & (pts[:, 1] >= box.y0) & (pts[:, 1] <= box.y1)).mean())
    return fr


def _overlap(a, b):
    return (max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0)) * max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0)))


def _outside(box, bound):
    return (max(0.0, bound.x0 - box.x0) + max(0.0, box.x1 - bound.x1)
            + max(0.0, bound.y0 - box.y0) + max(0.0, box.y1 - bound.y1))


def value_label(ax, x, y, text, colour, placed, fontsize=FS_ANN):
    """Write one value label of panel (f) clear of every marker, of the axis edge and of its peers."""
    fig = ax.figure
    ann = ax.annotate(text, xy=(x, y), xycoords="data", textcoords="offset points",
                      xytext=(0.0, STEP_PT), fontsize=max(FS_FLOOR, fontsize), color=colour,
                      ha="center", va="bottom", zorder=6, bbox=dict(VALUE_HALO), annotation_clip=False)
    ann.set_in_layout(False)
    r = fig.canvas.get_renderer()
    marks = _markers(ax)
    axb = ax.get_window_extent(r)
    b = ann.get_window_extent(r)
    w_pt, h_pt = b.width * 72.0 / fig.dpi, b.height * 72.0 / fig.dpi
    rad_pt = (float(np.max(marks[:, 2])) * 72.0 / fig.dpi) if len(marks) else 0.0
    best, best_cost = (0.0, STEP_PT + rad_pt), np.inf
    for k in range(1, MAX_STEPS + 1):
        for ux, uy in DIRS:
            ann.xyann = (ux * (w_pt * 0.55 + STEP_PT + rad_pt) * k,
                         uy * (h_pt * 0.75 + STEP_PT + rad_pt) * k)
            nb = ann.get_window_extent(r)
            cover = _cover(nb, marks)
            cost = 40.0 * float(np.sum(cover[cover > MARKER_COVER])) + 4.0 * float(np.sum(cover))
            cost += sum(_overlap(nb, q) for q in placed) / 100.0
            cost += 0.02 * (abs(ann.xyann[0]) + abs(ann.xyann[1]))
            cost += 5.0 * _outside(nb, axb)
            if cost < best_cost - 1e-9:
                best, best_cost = ann.xyann, cost
            if best_cost <= 1e-9:
                break
        if best_cost <= 1e-9:
            break
    ann.xyann = best
    placed.append(ann.get_window_extent(r))
    return ann


# --------------------------------------------------------------------------------- titles and letters
def _cell_x0(ax):
    """Left edge of the panel's GRID CELL in figure fraction — the column every letter is written in."""
    return ax.get_subplotspec().colspan.start / PLATE_COLS


def facet_title(ax, text):
    """Panel title: folded by measured width and left-aligned, so the layout reserves its real height."""
    return ax.set_title(wrap_measured(text, TITLE_W_PT, FS_TITLE, "bold"), loc="left",
                        fontsize=FS_TITLE, fontweight="bold")


def place_titles_and_letters(fig, axes):
    """Anchor each title to the left edge of its cell and its letter one gap to the left of the title.

    In a narrow cell a centred title travels with the axes: the region names of the left column push
    the axes far to the right, and a title that moved with them would collide with the panel beside it.
    The stored plate anchors the title to the CELL, which is why its six titles form one column and
    every letter sits beside the first line of its own title."""
    r = fig.canvas.get_renderer()
    gap = LETTER_GAP_PT / 72.0 / fig.get_figwidth()          # the letter-to-title gap, in figure fraction
    for ax, ch in zip(axes, "abcdef"):
        pos = ax.get_position()
        t = ax.title if ax.title.get_text() else ax._left_title
        t.set_x((_cell_x0(ax) + CELL_MARGIN + gap - pos.x0) / pos.width)
        fig.canvas.draw()
        bb = t.get_window_extent(r).transformed(fig.transFigure.inverted())
        lines = t.get_text().count("\n") + 1
        # The letter is part of the title: it sits beside the title's FIRST line, in the cell's margin.
        fig.text(_cell_x0(ax) + CELL_MARGIN, bb.y1 - bb.height / lines, f"({ch})",
                 fontsize=FS_LETTER, fontweight="bold", ha="left", va="bottom")


def place_n_strip(fig, strips):
    """Drop the strip of reporting establishments clear of the year labels it sits under.

    The pipeline writes it at a fixed −0.055 of the axes height, which on this plate lands on the year
    labels themselves; `common.plate_resolve` then measures the drawn panel and pushes it down, and
    the stored plate prints it a clear line below them. That second step is what is done here, on the
    frozen layout: the strip is hung from the BOTTOM of the year labels, so it keeps its own line
    whatever the panel's height turns out to be."""
    r = fig.canvas.get_renderer()
    gap = N_STRIP_GAP_PT * fig.dpi / 72.0
    for ax, texts in strips:
        axb = ax.get_window_extent(r)
        bottom = min(t.get_window_extent(r).y0 for t in ax.get_xticklabels() if t.get_text())
        y = (bottom - gap - axb.y0) / axb.height
        for t in texts:
            t.set_position((t.get_position()[0], y))


def wrap_ylabel(ax):
    """Fold a rotated y label taller than the usable height of a panel, so it cannot cross the letter.

    The rule of the stored plate (`wrap_axis_labels`) is a fixed column of 138 pt, measured on the
    string itself: 'Reporting establishments (n)' stays on one line and 'per 100,000 residents (INE
    base 2017)' does not."""
    lbl = ax.yaxis.label
    txt = lbl.get_text()
    if txt and "\n" not in txt and _width_pt(txt, lbl.get_fontsize()) > YLABEL_H_PT:
        lbl.set_text(wrap_measured(txt, YLABEL_H_PT, lbl.get_fontsize()))
        lbl.set_linespacing(1.0)


# --------------------------------------------------------------------------------- the plate
def draw():
    style()
    plt.rcParams.update({
        # The plate norm of the pipeline (`PLATE_RC`), over the study style: the tick marks are
        # suppressed and only the left and bottom spines are drawn, as the stored plate shows.
        "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold",
        "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
        "legend.fontsize": FS_ANN, "legend.frameon": True, "legend.framealpha": 0.82,
        "legend.facecolor": "white", "legend.edgecolor": "none", "legend.borderpad": 0.25,
        "legend.handlelength": 1.4, "legend.handletextpad": 0.5, "legend.columnspacing": 1.0,
        "legend.labelspacing": 0.35, "legend.borderaxespad": 0.3,
        "axes.edgecolor": DARK, "axes.linewidth": 0.7, "axes.labelcolor": "#262626",
        "text.color": "#262626", "xtick.color": "#262626", "ytick.color": "#262626",
        "grid.color": "#b0b0b0", "grid.linewidth": 0.5, "grid.alpha": 0.32,
        # No tick marks are drawn, but their length still spaces the labels off the axis, as it does
        # on the stored plate.
        "xtick.bottom": False, "ytick.left": False, "xtick.major.size": 2.2, "ytick.major.size": 2.2,
        "xtick.major.pad": 1.6, "ytick.major.pad": 1.6, "axes.titlepad": 4.0, "axes.labelpad": 2.0,
        "lines.linewidth": 1.1, "lines.markersize": 3.2,
    })
    regions, E = read_e16()
    pop = national_population()

    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055)
    gs = fig.add_gridspec(PLATE_ROWS, PLATE_COLS)
    axes, strips = [], []

    # (a)–(d) the four codes, one region x year heat map each -----------------------------------------
    for k, (label, cmap, cb_unit, _colour) in enumerate(SERIES):
        ax = fig.add_subplot(gs[k // 2, k % 2])
        axes.append(ax)
        s = E[label]
        heat(ax, s["total"], s["suppressed"], regions, cmap, cb_unit)
        facet_title(ax, TITLES[k])
        unit = U_INTERVENTIONS if cb_unit == "Interventions" else U_REHAB
        long_xlabel(ax, f"Year — {unit} — {N_ESTAB}", fontsize=FS_TICK)
        ax.xaxis.labelpad = 16          # room for the strip of reporting establishments under the axis
        row = []
        for j in range(len(YEARS)):
            # The national number of establishments that filed the code, under its own column.
            t = ax.text(j, -0.055, f"n={num(s['n_est'][j], 'en')}", transform=ax.get_xaxis_transform(),
                        ha="center", va="top", fontsize=FS_ANN, color=N_GREY)
            t.set_in_layout(False)
            row.append(t)
        strips.append((ax, row))

    # (e) reporting establishments, with the regions that filed a row above each bar -------------------
    ax = fig.add_subplot(gs[2, 0])
    axes.append(ax)
    w = 0.2
    for k, (label, _cmap, _unit, colour) in enumerate(SERIES):
        s = E[label]
        xx = np.asarray(YEARS, dtype=float) + (k - 1.5) * w
        ax.bar(xx, s["n_est"], width=w * 0.9, color=colour, label=label)
        for xi, v, nr in zip(xx, s["n_est"], s["n_regions"]):
            # Twelve 3 mm bars in a 90 mm cell: a two-line label above each one does not fit, and
            # moving it aside puts it over its neighbour. One rotated line fits over its own bar, and
            # the x-axis label says what the two numbers are.
            t = ax.annotate(f"{num(v, 'en')} ({num(nr, 'en')})", (xi, v), xytext=(0, 2),
                            textcoords="offset points", ha="center", va="bottom", rotation=90,
                            fontsize=FS_CELL, color=DARK, zorder=6, bbox=dict(VALUE_HALO))
            t.set_in_layout(False)
    ax.set_xticks(YEARS)
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.set_ylabel("Reporting establishments (n)", fontsize=FS_BASE)
    ax.yaxis.set_major_formatter(thousands("en"))
    long_xlabel(ax, "Year — above each bar: reporting establishments "
                    "(regions with a row for the code)")
    ax.set_ylim(0, float(max(E[s]["n_est"].max() for s in E)) * 1.85)
    legend_wrapped(ax, loc="upper left", fontsize=FS_ANN)
    facet_title(ax, TITLES[4])
    clean(ax, "y")

    # (f) national totals per 100,000 residents — a crude, ecological rate ----------------------------
    ax = fig.add_subplot(gs[2, 1])
    axes.append(ax)
    marks, top = [], 0.0
    for label, _cmap, _unit, colour in SERIES:
        rate = PER * E[label]["national"] / pop
        top = max(top, float(rate.max()))
        ax.plot(YEARS, rate, marker="o", ms=6, lw=2.0, color=colour, label=label)
        marks += [(y, v, num(v, "en", 1), colour) for y, v in zip(YEARS, rate)]
    ax.set_ylim(0, top * 1.24)
    ax.set_xticks(YEARS)
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.set_ylabel("per 100,000 residents (INE base 2017)", fontsize=FS_BASE)
    long_xlabel(ax, "Year — ecological rate: REM locates the provider, not residence")
    ax.xaxis.label.set_color(ECOLOGICAL_RED)
    legend_wrapped(ax, loc="upper left", fontsize=FS_ANN)
    facet_title(ax, TITLES[5])
    clean(ax, "y")

    # The layout is resolved and frozen before anything is measured: the value labels of panel (f) and
    # the letters are placed in POINTS, so a later redistribution of the cells would undo them.
    for a in axes:
        wrap_ylabel(a)
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    fig.canvas.draw()
    place_n_strip(fig, strips)
    place_titles_and_letters(fig, axes)
    placed = []
    for mx, my, mtxt, mcol in marks:
        value_label(axes[5], mx, my, mtxt, mcol, placed)
    return fig
