"""EF5 — co-diagnoses of the episodes with documented F84, F84 family excluding Rett syndrome.

Redraw of the stored plate `docs/study/corpus/figures/EF5_codiagnoses.jpg`. The original was drawn by
`study/pipeline/13_extra_figures_hospital.py` from the GRD microdata, which this repository does not
carry; all six panels survive in published aggregates and are rebuilt here from three tracked tables
and one tracked tidy file:

  (a) ten most frequent three-character ICD-10 categories, pooled  `corpus/tables/EF5_codiagnoses.csv`
  (b) six ICD-10 chapters by year, as a heat map                   `corpus/tables/E7_grd_codiagnosis_chapters.csv`
  (c) the thirteen mental-health blocks, 2019 against 2024         `corpus/tables/E7_grd_codiagnosis_chapters.csv`
  (d) principal diagnosis when F84 is secondary only               `corpus/tables/E8_grd_principal_when_secondary.csv`
  (e) change between 2019 and 2024 of the ten categories of (a)    `corpus/tables/EF5_codiagnoses.csv`
  (f) categories per episode and mean coding depth                 `corpus/tables/EF5_codiagnoses.csv`
      with the two coding depths of the annual summary             `data/grd_year_summary.csv`

None of those tables prints the denominators the percentages are taken over; they come from
`data/grd_year_summary.csv`, whose `n_episodes_f84` for the same variant, panel and activity gives the
episodes with F84 in any position and, separately, those in which F84 is secondary only.

Estimator, unchanged from the original: case definition `sin_rett` (the F84 family without Rett
syndrome), observed hospital panel, F84 in any diagnostic position, all activities. Every co-diagnosis
figure counts EPISODES WITH AT LEAST ONE MENTION — once per episode per category, chapter or block —
so the columns do not add to 100% and mentions are never summed across categories; the F84 family
itself is excluded from the count. Three denominators live in this plate and must not be exchanged:
panels (a), (b), (c) and (e) divide by the episodes with F84 of the same year (2,334 / 1,609 / 2,367 /
3,859 / 6,423 / 8,731, pooled 25,323), panel (d) divides by the episodes in which F84 is SECONDARY
ONLY (2,106 / 1,452 / 2,181 / 3,564 / 6,062 / 8,341, pooled 23,706), and panel (f) keeps distinct
categories per episode apart from coded diagnoses per episode — two different rows of the EF5 table.

The E66 length-of-stay table prints an annual n for the same position-by-activity cells, but it counts
the episodes whose stay could be measured: 8,728 and 8,340 in 2024, three and one episodes short of the
annual denominator. That shortfall is visible in the published cells — 3,549 of the chapter 'Mental and
behavioural disorders' in 2024 is 40.6% of 8,731 and 40.7% of 8,728, and the table prints 40.6% — so
the denominators are read from the annual summary and not from E66.

Panel (c) is drawn from the thirteen `Mental-health block (F)` rows of E7 and never by aggregating the
three-character categories of EF5: a block row counts episodes with at least one code of the block, and
one episode carrying two codes of the same block would be counted twice by any such aggregation.

The percentages are recomputed from the counts rather than read off the rounded cells, exactly as the
original did; `_check_published()` verifies every one of them against its published cell — 541 in all —
before the figure is drawn, so no value here is invented.

The corpus is English only, so this plate is English only.
"""
import re
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: E402,F401,F403  (house style)

PLATE = "EF5_codiagnoses"
SOURCES = [
    "docs/study/corpus/tables/EF5_codiagnoses.csv",
    "docs/study/corpus/tables/E7_grd_codiagnosis_chapters.csv",
    "docs/study/corpus/tables/E8_grd_principal_when_secondary.csv",
    "docs/study/data/grd_year_summary.csv",
]
NOTE = ("Redraws the six panels of EF5 — the top ten co-diagnosis categories pooled, the six ICD-10 "
        "chapters by year, the thirteen mental-health blocks in 2019 against 2024, the principal "
        "diagnosis when F84 is secondary only, the 2019-to-2024 change of the top ten and the coding "
        "depth — from the published EF5, E7 and E8 tables and the annual GRD summary, keeping "
        "'episodes with at least one mention' as the unit and each panel's own denominator.")

TABLES = BASE/"corpus"/"tables"
EF5_TABLE = TABLES/"EF5_codiagnoses.csv"
CHAPTER_TABLE = TABLES/"E7_grd_codiagnosis_chapters.csv"
SECONDARY_TABLE = TABLES/"E8_grd_principal_when_secondary.csv"
YEAR_SUMMARY = DATA/"grd_year_summary.csv"

VARIANT, PANEL_SET, ACTIVITY = "sin_rett", "observed", "all"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
TOP = 10                 # categories kept in the ranking panels; the table keeps twenty-five
CHAPTERS = 6             # rows of the heat map
POOLED_COL = "2019–2024"

#: rows of the EF5 table that are not co-diagnosis categories but the two coding-depth series of (f)
CATS_PER_EPISODE = "Distinct ICD-10 categories per episode"
DEPTH_F84 = "Coded diagnoses per episode · Episodes with documented F84"

#: colours of the stored plate (Okabe–Ito, as in `figstyle`)
C_F84, C_SECONDARY, C_2019, C_2024, C_ALL = BLUE, GOLD, SKY, ORANGE, "#7f8c8d"
CONNECT = "#bbbbbb"      # the dumbbell connector of (c) and (e)
CTX = "#444444"          # the Law 21.545 marker
CTX_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.4)
CELL_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9)

#: Law 21.545 on a year axis of centred years, as the original placed it: the year of publication plus
#: March (2.5/12) minus the half year that centres the tick, i.e. 2022.708, between 2022 and 2023.
LAW_X = 2023 + 2.5/12 - 0.5

FS_TITLE, FS_LETTER, FS_BASE, FS_TICK, FS_ANN, FS_CELL = 9.0, 10.0, 8.0, 7.0, 6.4, 6.0

PCT_F84 = "% of episodes with F84"
PCT_SECONDARY = "% of episodes with F84 secondary only"
DEPTH_LABEL = "Coded diagnoses per episode"
CBAR_LABEL = "Episodes with ≥ 1 mention per\n100\nepisodes with F84"
CONTEXT_XLABEL = ("Year — shading: Reporting disruption\n2020–21; dotted line: Law 21.545 (March\n"
                  "2023, context)")

TITLES = [("(a)", "10 most frequent three-character ICD-10\ncategories, 2019–2024"),
          ("(b)", "ICD-10 chapters: episodes with a mention\nper 100 episodes with F84"),
          ("(c)", "Mental-health blocks (F00–F99, excluding\nF84)"),
          ("(d)", "Principal diagnosis when F84 is secondary\nonly"),
          ("(e)", "Change between 2019 and 2024 (top 10\ncategories)"),
          ("(f)", "Categories per episode and coding depth")]

# axes of the stored plate, measured on it: two columns of 300 px and three rows of 341 px on the
# 1000 x 1361 px canvas, with the colour bar of (b) outside its axes on the right margin.
AX_X, AX_Y = (0.147, 0.616), (0.713446, 0.363703, 0.033799)
AX_W, AX_H = 0.300, 0.250551
CBAR_BOX = (0.923, 0.761205, 0.013, 0.155768)


# ---------------------------------------------------------------------------------------------
# reading the tracked tables
# ---------------------------------------------------------------------------------------------
def _n_pct(cell):
    """'1,045 (44.8%)' -> (1045, 44.8); anything else -> None."""
    m = re.fullmatch(r"([\d,]+)\s*\(([\d.]+)%\)", str(cell).strip())
    if not m:
        return None
    return int(m.group(1).replace(",", "")), float(m.group(2))


def _read_counts(path, key, keep=None):
    """A published table of `n (percentage)` cells, as {label: {year: (n, published %)}}.

    `keep` filters the rows on the table's own grouping column; rows whose cells are not counts (the
    two coding-depth rows of the EF5 table) are left out and read separately.
    """
    raw = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    out = {}
    for _, row in raw.iterrows():
        if keep is not None and row[keep[0]].strip() != keep[1]:
            continue
        cells = {y: _n_pct(row[str(y)]) for y in YEARS}
        if any(v is None for v in cells.values()):
            continue
        out[row[key].strip()] = cells
    return out


def _read_ef5():
    """The EF5 companion table: the twenty-five categories and the distinct-categories series of (f)."""
    raw = pd.read_csv(EF5_TABLE, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    key = raw.columns[0]
    cats = _read_counts(EF5_TABLE, key)
    pooled = {}
    for _, row in raw.iterrows():
        parsed = _n_pct(row[POOLED_COL])
        if parsed is not None:
            pooled[row[key].strip()] = parsed
    depth = raw.set_index(key)
    cats_per_episode = {y: float(depth.loc[CATS_PER_EPISODE, str(y)]) for y in YEARS}
    depth_f84_published = {y: float(depth.loc[DEPTH_F84, str(y)]) for y in YEARS}
    return cats, pooled, cats_per_episode, depth_f84_published


def _read_year_summary():
    """The annual summary of the same cell: the two denominators and the two coding depths of (f).

    'any' is the number of episodes with F84 in any diagnostic position, which panels (a), (b), (c)
    and (e) divide by; 'secondary_only' is the different denominator of panel (d). Neither is printed
    by any of the presentation tables.
    """
    d = pd.read_csv(YEAR_SUMMARY)
    d = d[(d.variant == VARIANT) & (d.panel == PANEL_SET) & (d.activity == ACTIVITY)]
    any_pos = d[d.position == "any"].set_index("year").sort_index()
    secondary = d[d.position == "secondary_only"].set_index("year").sort_index()
    den_any = {y: int(any_pos.n_episodes_f84[y]) for y in YEARS}
    den_sec = {y: int(secondary.n_episodes_f84[y]) for y in YEARS}
    depth_f84 = {y: float(any_pos.coding_depth_mean_f84[y]) for y in YEARS}
    depth_all = {y: float(any_pos.coding_depth_mean_all[y]) for y in YEARS}
    return den_any, den_sec, depth_f84, depth_all


def _pooled_rank(counts, top=None):
    """Labels ordered by the pooled 2019–2024 count, with that count: the plate's own ranking."""
    order = sorted(counts, key=lambda k: -sum(n for n, _ in counts[k].values()))
    order = order if top is None else order[:top]
    return [(k, sum(n for n, _ in counts[k].values())) for k in order]


def _share(counts, label, year, denominator):
    """Episodes with at least one mention of `label` in `year`, per 100 episodes of the denominator."""
    return 100 * counts[label][year][0] / denominator[year]


# ---------------------------------------------------------------------------------------------
# the published values every drawn number is checked against
# ---------------------------------------------------------------------------------------------
def _check_published(cats, pooled, cats_per_episode, depth_f84_published, chapters, blocks,
                     secondary, den_any, den_sec, depth_f84):
    """Every percentage drawn here is recomputed from counts; each must round to its published cell."""
    bad = []
    for name, counts, denominator in (("EF5", cats, den_any), ("E7 chapter", chapters, den_any),
                                      ("E7 block", blocks, den_any), ("E8", secondary, den_sec)):
        for label, cells in counts.items():
            for year, (n, published) in cells.items():
                got = round(100 * n / denominator[year], 1)
                if abs(got - published) > 0.051:
                    bad.append(f"{name} {label} {year}: {got} vs published {published}")
    total = sum(den_any.values())
    for label, (n, published) in pooled.items():
        got = round(100 * n / total, 1)
        if abs(got - published) > 0.051:
            bad.append(f"EF5 pooled {label}: {got} vs published {published}")
    for year in YEARS:                      # the orange series of (f), against its published rounding
        if abs(round(float(depth_f84[year]), 2) - depth_f84_published[year]) > 0.005:
            bad.append(f"coding depth {year}: {depth_f84[year]} vs published {depth_f84_published[year]}")
    if not 3.0 < min(cats_per_episode.values()) <= max(cats_per_episode.values()) < 6.0:
        bad.append(f"categories per episode out of range: {cats_per_episode}")
    if bad:
        raise AssertionError("EF5 redraw does not match the published tables:\n  " + "\n  ".join(bad))


# ---------------------------------------------------------------------------------------------
# small drawing helpers, the plate's own
# ---------------------------------------------------------------------------------------------
def _clip(text, width):
    """A label too long for its line, cut with an ellipsis and never left mid-word without one."""
    s = str(text)
    return s if len(s) <= width else s[:max(1, width - 1)].rstrip() + "…"


def _tick(text, width=18, lines=2):
    """A categorical tick label for a narrow cell: at most `lines` lines before it is clipped."""
    parts = textwrap.wrap(str(text), width) or [str(text)]
    if len(parts) <= lines:
        return "\n".join(parts)
    keep = parts[:lines]
    keep[-1] = _clip(keep[-1] + " " + parts[lines], width)
    return "\n".join(keep)


def _icd_label(text):
    """E8 writes 'G40 — Epilepsy'; the plate, like EF5 and E7, writes 'G40 · Epilepsy'."""
    return re.sub(r"\s+—\s+", " · ", str(text))


def _grid(ax):
    ax.set_axisbelow(True)
    ax.grid(True, color="#b0b0b0", alpha=0.32, lw=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _heading(fig, letter_x, top, letter, title):
    fig.text(letter_x, top, letter, fontsize=FS_LETTER, fontweight="bold", ha="left", va="top")
    fig.text(letter_x + 0.0425, top, title, fontsize=FS_TITLE, fontweight="bold", ha="left", va="top",
             linespacing=1.13)


def _rank_bars(ax, rows, colour, xlabel):
    """A ranking panel: horizontal bars, the longest on top, with the glossed label in two lines."""
    y = np.arange(len(rows))
    ax.barh(y, [v for _, v in rows], color=colour)
    ax.set_yticks(y)
    ax.set_yticklabels([_tick(label) for label, _ in rows], fontsize=FS_ANN)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=FS_BASE)
    _grid(ax)


def _dumbbell(ax, rows):
    """A 2019-against-2024 panel: the two years joined by a grey connector, one row per category."""
    y = np.arange(len(rows))
    for i, (_, first, last) in enumerate(rows):
        ax.plot([first, last], [i, i], color=CONNECT, lw=1.6, zorder=1)
    ax.scatter([r[1] for r in rows], y, s=26, color=C_2019, zorder=2, label="2019")
    ax.scatter([r[2] for r in rows], y, s=26, color=C_2024, zorder=2, label="2024")
    ax.set_yticks(y)
    ax.set_yticklabels([_tick(r[0]) for r in rows], fontsize=FS_ANN)
    ax.invert_yaxis()
    ax.set_xlabel(PCT_F84, fontsize=FS_BASE)
    _grid(ax)
    ax.legend(loc="lower right", fontsize=FS_TICK, frameon=True, framealpha=0.92, facecolor="white",
              edgecolor="none", borderpad=0.28, labelspacing=0.3, handlelength=1.4,
              handletextpad=0.5, borderaxespad=0.3)


# ---------------------------------------------------------------------------------------------
# the six panels
# ---------------------------------------------------------------------------------------------
def _panel_a(ax, cats, den_any):
    """(a) The ten most frequent three-character categories, pooled over 2019–2024."""
    total = sum(den_any.values())
    rows = [(label, 100 * n / total) for label, n in _pooled_rank(cats, TOP)]
    _rank_bars(ax, rows, C_F84, PCT_F84)


def _panel_b(fig, ax, chapters, den_any):
    """(b) The six chapters with the most affected episodes, per 100 episodes with F84 of the year."""
    rows = [label for label, _ in _pooled_rank(chapters, CHAPTERS)]
    data = np.array([[_share(chapters, label, y, den_any) for y in YEARS] for label in rows])
    im = ax.imshow(data, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels([str(y) for y in YEARS], fontsize=FS_BASE)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([_tick(label, 20) for label in rows], fontsize=FS_CELL)
    ax.grid(False)
    lo, hi = float(data.min()), float(data.max())
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            pale = (data[i, j] - lo) / (hi - lo) <= 0.62      # the text lightens only on dark cells
            ax.text(j, i, num(data[i, j], "en", 1), ha="center", va="center", fontsize=FS_CELL,
                    color="#1a1a1a" if pale else "white", bbox=CELL_BBOX if pale else None)
    # context over a column axis: the disruption covers the 2020 and 2021 columns, the law falls
    # between 2022 and 2023; the gloss goes under the axis, not over the cells.
    ax.axvspan(0.5, 2.5, color="grey", alpha=0.16, zorder=3)
    ax.axvline(3.5, color="#222222", ls=":", lw=1.2, zorder=4)
    ax.set_xlabel(CONTEXT_XLABEL, fontsize=FS_ANN)
    cax = fig.add_axes(CBAR_BOX)
    bar = fig.colorbar(im, cax=cax)
    bar.ax.tick_params(labelsize=FS_TICK)
    # the stored plate breaks the colour-bar label into three lines and sets them solid, at the
    # smallest body of the plate: that is what keeps the block inside the right margin of the canvas.
    bar.set_label(CBAR_LABEL, fontsize=FS_CELL, labelpad=0.0)
    bar.ax.yaxis.label.set_linespacing(1.0)


def _panel_c(ax, blocks, den_any):
    """(c) The thirteen mental-health blocks (F00–F99 without F84), 2019 against 2024."""
    rows = [(label, _share(blocks, label, 2019, den_any), _share(blocks, label, 2024, den_any))
            for label, _ in _pooled_rank(blocks)]
    _dumbbell(ax, rows)


def _panel_d(ax, secondary, den_sec):
    """(d) Principal diagnosis of the episodes in which F84 appears only as a secondary diagnosis."""
    total = sum(den_sec.values())
    rows = [(_icd_label(label), 100 * n / total) for label, n in _pooled_rank(secondary, TOP)]
    _rank_bars(ax, rows, C_SECONDARY, PCT_SECONDARY)


def _panel_e(ax, cats, den_any):
    """(e) The ten categories of (a), 2019 against 2024, in the same order."""
    rows = [(label, _share(cats, label, 2019, den_any), _share(cats, label, 2024, den_any))
            for label, _ in _pooled_rank(cats, TOP)]
    _dumbbell(ax, rows)


def _panel_f(ax, cats_per_episode, depth_f84, depth_all):
    """(f) Distinct categories per episode against the coding depth of F84 and of all GRD episodes."""
    ax.plot(YEARS, [cats_per_episode[y] for y in YEARS], marker="o", ms=4.2, lw=1.7, color=C_F84,
            label=CATS_PER_EPISODE)
    ax.plot(YEARS, [depth_f84[y] for y in YEARS], marker="^", ms=4.0, lw=1.5, color=C_2024,
            label="Episodes with documented F84")
    ax.plot(YEARS, [depth_all[y] for y in YEARS], marker="s", ms=3.8, lw=1.4, ls="--", color=C_ALL,
            label="All GRD episodes")
    for year in (2020, 2021):                       # the reporting disruption, one span per year
        ax.axvspan(year - 0.5, year + 0.5, color="grey", alpha=0.12, zorder=0)
    ax.text(2020.5, 0.97, "Reporting\ndisruption 2020–21", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=FS_TICK, color="#555555", bbox=CTX_BBOX, zorder=6)
    ax.axvline(LAW_X, color=CTX, ls=":", lw=1.2, zorder=1)
    ax.text(LAW_X + 0.06, 0.5, "Law 21.545\n(2023)", transform=ax.get_xaxis_transform(), ha="left",
            va="top", fontsize=FS_TICK, color=CTX, bbox=CTX_BBOX, zorder=6)
    ax.set_xticks(YEARS)
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.set_xlabel("Year", fontsize=FS_BASE)
    ax.set_ylabel(DEPTH_LABEL, fontsize=FS_BASE)
    _grid(ax)
    lo, hi = ax.get_ylim()                          # room under the series for the legend box
    ax.set_ylim(lo - (hi - lo) * 0.46, hi)
    lo, hi = ax.get_ylim()                          # and the headroom the stored plate keeps above
    ax.set_ylim(top=hi + (hi - lo) * 0.024)         # the 2020 peak, under the disruption label
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, [textwrap.fill(t, 24) for t in labels], loc="lower right", fontsize=FS_ANN,
              title=DEPTH_LABEL, title_fontsize=FS_TICK, frameon=True, framealpha=0.9,
              facecolor="white", edgecolor="none", borderpad=0.28, labelspacing=0.3,
              handlelength=1.4, handletextpad=0.5, borderaxespad=0.3)


# ---------------------------------------------------------------------------------------------
def draw():
    """Draw the six panels of EF5 and hand back the figure."""
    cats, pooled, cats_per_episode, depth_f84_published = _read_ef5()
    chapters = _read_counts(CHAPTER_TABLE, "Group", keep=("Grouping", "ICD-10 chapter"))
    blocks = _read_counts(CHAPTER_TABLE, "Group", keep=("Grouping", "Mental-health block (F)"))
    secondary = _read_counts(SECONDARY_TABLE, "Principal diagnosis (ICD-10, 3 characters)")
    den_any, den_sec, depth_f84, depth_all = _read_year_summary()
    _check_published(cats, pooled, cats_per_episode, depth_f84_published, chapters, blocks,
                     secondary, den_any, den_sec, depth_f84)

    style()
    plt.rcParams.update({
        "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
        "axes.edgecolor": "#333333", "axes.linewidth": 0.7, "axes.labelpad": 2.0,
        # the stored plate draws no tick marks — the grid carries the scale — but keeps their length
        # in the gap between the spine and the tick label, which is where the labels of (a) to (e) sit
        "xtick.bottom": False, "ytick.left": False, "xtick.major.size": 2.2, "ytick.major.size": 2.2,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.pad": 1.6, "ytick.major.pad": 1.6,
        "lines.linewidth": 1.1, "lines.markersize": 3.2})
    fig = plt.figure(figsize=(180/25.4, 245/25.4))     # the plate norm: 180 x 245 mm, three by two
    ax = [fig.add_axes([AX_X[i % 2], AX_Y[i // 2], AX_W, AX_H]) for i in range(6)]

    _panel_a(ax[0], cats, den_any)
    _panel_b(fig, ax[1], chapters, den_any)
    _panel_c(ax[2], blocks, den_any)
    _panel_d(ax[3], secondary, den_sec)
    _panel_e(ax[4], cats, den_any)
    _panel_f(ax[5], cats_per_episode, depth_f84, depth_all)

    for i, (letter_, title) in enumerate(TITLES):
        top = AX_Y[i // 2] + AX_H + (41 if title.count("\n") else 21)/1361
        _heading(fig, 0.013 + 0.500 * (i % 2), top, letter_, title)
    return fig


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/"qa"/f"{PLATE}_redraw.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    draw().savefig(out, dpi=141.1, facecolor="white")   # 1000 px wide, as the stored plate
    print("wrote", out)
