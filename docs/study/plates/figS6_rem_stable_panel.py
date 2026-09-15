"""figS6 — the stable establishment panel against all reporting establishments, redrawn.

The stored plate was drawn by `study/pipeline/` from the REM Serie A and Serie P microdata, which
this repository does not carry. All six panels survive in published aggregates and are redrawn from
two tracked tables:

  (a–e) `docs/study/corpus/tables/S6_stable_panel.csv` — the plate's own backing table, one row per
        panel, series and year. Every mark on those five panels is a column of it: the filled bar is
        `Value` (all establishments with a row for the code that year), the hatched bar is
        `Stable-panel total`, the n under each year is `Reporting establishments`, the legend's panel
        size is `Stable-panel establishments`, and the black line is the share of the volume the
        stable panel holds.
  (f)   the same table's `% volume retained` and `% establishments retained`, for the five series of
        the 2021–2025 era (2019–2025 for P2); the broad pre-2021 era is not in panel (f).
  cross-check
        `docs/study/corpus/tables/ST14_p2_p6_june_december.csv` — an independent publication of the
        same December stocks, reporting establishments, panel sizes and panel stocks for P2 and for
        both P6 series. `_crosscheck()` asserts the two tables agree cell for cell before anything is
        drawn; ST14's June sensitivity is not on this plate and is not read.

Estimator, unchanged from the original: unweighted administrative counts, never rates and never
standardised, and the case definition is the F84 family EXCLUDING Rett syndrome. The units differ by
panel and must not be mixed on one axis — (a) and (b) are ENTRIES, an annual flow summed over the
months; (c), (d) and (e) are PEOPLE UNDER CONTROL IN DECEMBER, a stock. The stable panel is the set
of establishments with a row for the code (or family) in EVERY year of that code's definition era, so
the broad-PDD era 2019–2020 has its own panel (395 for A05 entries, 594 for P6 primary care, 104 for
P6 specialty) and the 2021–2025 era another (258, 432, 353, 68). The two eras measure different
objects: their bars stand apart at the definition break, their percentage lines are never joined
across it, and the pre-2021 line is drawn dotted to say so. The percentages are the share of the
VOLUME the panel holds, not coverage of the population.

The percentages are recomputed from the counts rather than taken from the table's rounded column,
because the plate's one-decimal labels are printed from the exact ratio: P6 specialty 2020 is
6,250/6,905 = 90.51 %, which prints as 91, while the published 90.5 would print as 90. `_check()`
asserts the recomputed values agree with the published column to 0.05 pp everywhere.

The corpus is English only, so this module is English only and takes no language argument.
"""
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

_STUDY = Path(__file__).resolve().parents[1]          # docs/study, so `figstyle` resolves
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))

from figstyle import *   # noqa: E402,F401,F403 — style, clean, num, thousands, OKABE, GREY, …

PLATE = "figS6_rem_stable_panel"
SOURCES = [
    "docs/study/corpus/tables/S6_stable_panel.csv",
    "docs/study/corpus/tables/ST14_p2_p6_june_december.csv",
]
NOTE = ("Redraws the six panels of figure S6 — the national total against the stable establishment "
        "panel for A05 entries (strict autism and the variant's PDD family), P2 ASD in December and "
        "P6 primary care and specialty in December, with the share of the volume the panel retains — "
        "from the published stable-panel table, cross-checked against the P2/P6 June–December table.")

ROOT = BASE.parent.parent                      # docs/study -> docs -> repository root
TABLE, CROSS = (ROOT/rel for rel in SOURCES)

# --- the table's own vocabulary -------------------------------------------------------------------
BROAD_ERA = "2019–2020"                        # the broad-PDD era; every other era is the variant's
BROAD_TAG = " · Broad PDD 2019–20"             # the suffix the table puts on the broad-era Series
FLOW, STOCK = "annual sum of months (flow)", "December stock"

# --- the five bar panels, in the plate's reading order ---------------------------------------------
# colour: the bars and the hatch of the 2021-2025 era; the broad era is always grey.
BAR_PANELS = ["a", "b", "c", "d", "e"]
BAR_COLOUR = {"a": BLUE, "b": BLUE, "c": PINK, "d": GOLD, "e": SKY}
BROAD_GREY = "#999999"                         # the pre-2021 bars and their hatch
Y_LABEL = {FLOW: "Entries (annual flow)", STOCK: "People under control in December (stock)"}
PCT_LABEL = "% retained by the stable panel"

# --- panel (f): the five series it draws, with the panel and era each one comes from ---------------
# The broad pre-2021 era is deliberately absent: the caption's "eras 2021-2025 (2019-2025 for P2)".
RETENTION = [("A05 strict autism", "a", BLUE), ("A05 PDD family", "b", GREEN),
             ("P2 ASD", "c", PINK), ("P6 primary", "d", GOLD), ("P6 specialty", "e", SKY)]
ESTAB_ALPHA = 0.7                              # the establishments series, drawn lighter and dashed
PANEL_F_NOTE = ("stable panel = establishments with a row for\nthe code in every year of its era")

# --- geometry and marks measured off the stored plate ----------------------------------------------
YEARS = list(range(2019, 2026))
BAR_W = 0.40                                   # each bar 0.40 of a year, the pair centred on it
BAR_DX = 0.20
HEADROOM = 2.2                                 # left axis top = 2.2 x the tallest bar, as stored
PCT_TOP = 172.8                                # the right axis is the same in all five bar panels
PANEL_F_TOP = 150.0                            # (f) leaves room for its seven-entry legend
X_PAD = 0.6                                    # half a bar pair plus air, both ends
BREAK_X = 2020.5                               # the definition break sits between the two eras
LAW_X = 2023 - 0.35                            # Law 21.545, drawn clear of the 2023 bar group
BREAK_Y = 0.6388                               # height of the 'definition break' caption
BAND_TEXT_Y = 0.623                            # height of the two captions of panel (b)
BREAK_GREY = "#666666"                         # the 'definition break' caption
BREAK_LINE = "#909090"                         # the dash-dot rule that marks it
LAW_DARK = "#444444"                           # the law marker and its caption
LABEL_DARK = "#333333"                         # the percentage labels on the black line

# The plate is 180 x 245 mm, the REM plate size of `study/pipeline/` (the same geometry as E18), and
# its typography is that pipeline's: a 9 pt bold panel head, 8 pt axis labels, 7 pt y ticks, 6.4 pt
# two-line x ticks and a 6.2 pt floor for the legend and the labels on the line. Every size below was
# measured off the stored plate and is in points at that plate size.
PLATE_W_IN, PLATE_H_IN = 180.0/25.4, 245.0/25.4
FS_TITLE, FS_LABEL, FS_YTICK, FS_XTICK, FS_ANN, FS_NOTE, FS_LEG = 9.0, 8.0, 7.0, 6.4, 6.2, 6.4, 6.2
FS_BAND = 7.2                                  # the two captions panel (b) carries for the plate
TITLE_X = {"left": 0.013, "right": 0.512}      # the bold panel heads, measured off the stored plate
LEGEND = dict(fontsize=FS_LEG, labelspacing=0.2, borderpad=0.25, handlelength=1.5)
LW_LINE, MS_LINE = 1.7, 5.3                    # the black percentage line and its markers
PLATE_RC = {
    "axes.labelsize": FS_LABEL, "xtick.labelsize": FS_XTICK, "ytick.labelsize": FS_YTICK,
    "legend.fontsize": FS_LEG,
    # the stored plate marks the y axes only: a short rule beside each y tick, none under the x ticks
    "xtick.major.size": 0, "ytick.major.size": 2.0, "ytick.major.width": 0.7,
    "xtick.major.pad": 3.0, "ytick.major.pad": 1.5,
}

# (a)-(e) are headed with the table's own Series wording; (f) has no row of its own.
PANEL_F_TITLE = "Stable-panel retention: volume and\nestablishments"

# The stored plate prints every percentage. The default is up and to the right of its marker; the
# last year of each panel is centred over it instead, so that the label does not run past the axes.
LABEL_OFFSET = (5.2, 2.6, "left", "bottom")
LAST_OFFSET = {"a": (1.7, 9.4, "center", "bottom"), "b": (3.4, 2.6, "center", "bottom"),
               "c": (1.7, 9.4, "center", "bottom"), "d": (1.7, 9.4, "center", "bottom"),
               "e": (1.7, 11.2, "center", "bottom")}


# ------------------------------------------------------------------ the tracked tables and parsing
def _int(cell):
    """'13,155' -> 13155."""
    return int(str(cell).replace(",", "").strip())


def _read(path):
    table = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    table.columns = [c.strip() for c in table.columns]
    return table


def _series():
    """The S6 table as {panel: {era: {'series','code','measure','rows': {year: row}}}}.

    One row is a dict of the five counts the plate draws plus the two published percentages.
    """
    table = _read(TABLE)
    out = {}
    for _, row in table.iterrows():
        panel = row["Panel"].strip()
        era = row["Definition era"].strip()
        block = out.setdefault(panel, {}).setdefault(era, {
            "series": row["Series"].strip(), "code": row["Code"].strip(),
            "measure": row["Measure"].strip(), "rows": {}})
        block["rows"][int(row["Year"])] = {
            "value": _int(row["Value"]),
            "reporting": _int(row["Reporting establishments"]),
            "panel_n": _int(row["Stable-panel establishments"]),
            "stable": _int(row["Stable-panel total"]),
            "pub_volume": float(row["% volume retained"]),
            "pub_estab": float(row["% establishments retained"]),
        }
    return out


def _check(series):
    """The two percentages are recomputed from the counts and must match the published column."""
    for panel, eras in series.items():
        for era, block in eras.items():
            for year, row in block["rows"].items():
                volume = 100 * row["stable"] / row["value"]
                estab = 100 * row["panel_n"] / row["reporting"]
                assert abs(volume - row["pub_volume"]) < 0.05, (panel, era, year, volume)
                assert abs(estab - row["pub_estab"]) < 0.05, (panel, era, year, estab)
                assert row["stable"] <= row["value"], (panel, year)
                assert row["panel_n"] <= row["reporting"], (panel, year)


def _crosscheck(series):
    """ST14 publishes the same December cells for P2 and both P6 series; they must agree."""
    table = _read(CROSS)
    wanted = {"P2500500": "c", "P6223000": "d", "P6241010": "d",
              "P6223380": "e", "P6241060": "e"}
    seen = 0
    for _, row in table.iterrows():
        code = row["Code(s)"].strip()
        if code not in wanted:
            continue
        block = series[wanted[code]][row["Definition era"].strip()]
        assert block["code"] == code, (code, block["code"])
        mine = block["rows"][int(row["Year"])]
        assert mine["value"] == _int(row["December stock"]), (code, row["Year"])
        assert mine["reporting"] == _int(row["Establishments reporting in December"])
        assert mine["panel_n"] == _int(row["December stable panel: establishments (n)"])
        assert mine["stable"] == _int(row["December stable panel: stock"])
        seen += 1
    assert seen == 21, seen           # 7 P2 years + 2 + 5 P6 primary + 2 + 5 P6 specialty


def _eras_in_order(panel_blocks):
    """The panel's definition eras, earliest first; the broad era, where present, comes first."""
    return sorted(panel_blocks, key=lambda era: min(panel_blocks[era]["rows"]))


# ------------------------------------------------------------------------------ drawing the panels
def _title(fig, ax, ch, text):
    """The stored plate heads each panel with one bold line, '(x) Title', on the axes top left."""
    pos = ax.get_position()
    x = TITLE_X["left" if pos.x0 < 0.5 else "right"]
    fig.text(x, pos.y1 + 0.0004, f"({ch}) {text}", fontweight="bold",
             fontsize=FS_TITLE, ha="left", va="bottom", linespacing=1.2)


def _bar_panel(ax, ch, blocks):
    """(a)-(e): all establishments against the stable panel, with the retained share on the right."""
    eras = _eras_in_order(blocks)
    main = blocks[eras[-1]]                       # the 2021-2025 era (2019-2025 for P2)
    years = sorted(y for era in eras for y in blocks[era]["rows"])
    colour = BAR_COLOUR[ch]
    top = HEADROOM * max(r["value"] for era in eras for r in blocks[era]["rows"].values())

    shade_pandemic(ax)
    if len(eras) > 1:                             # only the panels that carry both definition eras
        ax.axvline(BREAK_X, color=BREAK_LINE, ls=(0, (6, 2, 1, 2)), lw=1.2, zorder=2)
        ax.text(BREAK_X, BREAK_Y, "definition\nbreak", transform=ax.get_xaxis_transform(),
                ha="center", va="center", fontsize=FS_ANN, color=BREAK_GREY, linespacing=1.12,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.9), zorder=3)
    ax.axvline(LAW_X, color=LAW_DARK, ls=(0, (1, 1.4)), lw=1.2, zorder=2)

    for era in eras:
        face = BROAD_GREY if era == BROAD_ERA else colour
        rows = blocks[era]["rows"]
        ys = sorted(rows)
        ax.bar([y - BAR_DX for y in ys], [rows[y]["value"] for y in ys], width=BAR_W,
               color=face, zorder=3)
        ax.bar([y + BAR_DX for y in ys], [rows[y]["stable"] for y in ys], width=BAR_W,
               facecolor="white", edgecolor=face, hatch="//", lw=0.8, zorder=3)

    clean(ax, "both")
    ax.set_xlim(years[0] - X_PAD, years[-1] + X_PAD)
    ax.set_ylim(0, top)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_xticks(years)
    ax.set_xticklabels([f"{y}\n{num(_reporting(blocks, y), 'en')}" for y in years],
                       linespacing=1.05)
    ax.set_xlabel("Year · n = reporting establishments")
    ax.set_ylabel(Y_LABEL[main["measure"]])

    pct = ax.twinx()
    pct.set_zorder(4)
    pct.patch.set_visible(False)
    pct.grid(False)
    for era in eras:
        rows = blocks[era]["rows"]
        ys = sorted(rows)
        shares = [100 * rows[y]["stable"] / rows[y]["value"] for y in ys]
        pct.plot(ys, shares, color=BLACK, lw=LW_LINE, ls="-" if era != BROAD_ERA else ":",
                 marker="o", markersize=MS_LINE, zorder=4)
        for year, share in zip(ys, shares):
            dx, dy, ha, va = LAST_OFFSET[ch] if year == years[-1] else LABEL_OFFSET
            pct.annotate(f"{share:.0f}%", (year, share), xytext=(dx, dy),
                         textcoords="offset points", ha=ha, va=va, fontsize=FS_ANN,
                         color=LABEL_DARK, zorder=5,
                         bbox=dict(facecolor="white", edgecolor="none", alpha=0.72, pad=0.9))
    pct.set_ylim(0, PCT_TOP)
    pct.yaxis.set_major_locator(MultipleLocator(20))
    pct.set_ylabel(PCT_LABEL)
    pct.spines["top"].set_visible(False)
    pct.spines["right"].set_visible(True)      # the stored plate keeps the right axis rule

    handles = []
    for era in eras:
        tag = BROAD_TAG if era == BROAD_ERA else ""
        face = BROAD_GREY if era == BROAD_ERA else colour
        size = next(iter(blocks[era]["rows"].values()))["panel_n"]
        handles += [Patch(facecolor=face, label=f"All establishments{tag}"),
                    Patch(facecolor="white", edgecolor=face, hatch="//", lw=0.8,
                          label=f"Stable panel (n={size}){tag}")]
    handles.append(Line2D([], [], color=BLACK, lw=LW_LINE, marker="o", markersize=MS_LINE,
                          label="% of volume retained"))
    pct.legend(handles=handles, loc="upper left" if ch in "ade" else "upper right", frameon=True,
               facecolor="white", edgecolor="#cccccc", framealpha=1.0, **LEGEND).set_zorder(6)


def _reporting(blocks, year):
    """The establishments that reported the code that year, whichever era the year belongs to."""
    for block in blocks.values():
        if year in block["rows"]:
            return block["rows"][year]["reporting"]
    raise KeyError(year)


def _panel_retention(ax, series):
    """(f): the share of the volume (circles) and of the establishments (squares) the panel holds."""
    shade_pandemic(ax)
    ax.axvline(LAW_X, color=LAW_DARK, ls=(0, (1, 1.4)), lw=1.2, zorder=2)
    for label, panel, colour in RETENTION:
        blocks = series[panel]
        era = _eras_in_order(blocks)[-1]           # never the broad pre-2021 era
        rows = blocks[era]["rows"]
        ys = sorted(rows)
        ax.plot(ys, [100 * rows[y]["stable"] / rows[y]["value"] for y in ys], color=colour,
                lw=LW_LINE, marker="o", markersize=MS_LINE, label=label, zorder=4)
        ax.plot(ys, [100 * rows[y]["panel_n"] / rows[y]["reporting"] for y in ys], color=colour,
                lw=1.55, ls=(0, (5, 2.4)), marker="s", markersize=5.1, alpha=ESTAB_ALPHA, zorder=3)

    clean(ax, "both")
    ax.set_xlim(YEARS[0] - X_PAD, YEARS[-1] + X_PAD)
    ax.set_ylim(0, PANEL_F_TOP)
    ax.yaxis.set_major_locator(MultipleLocator(20))
    year_ticks(ax, YEARS)
    ax.set_xlabel("Year")
    ax.set_ylabel("%")
    ax.text(0.013, 0.023, PANEL_F_NOTE, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=FS_NOTE, color=GREY, linespacing=1.2, zorder=5)

    handles = [Line2D([], [], color=c, lw=LW_LINE, marker="o", markersize=MS_LINE, label=name)
               for name, _, c in RETENTION]
    handles += [Line2D([], [], color=BLACK, lw=LW_LINE, marker="o", markersize=MS_LINE,
                       label="% of volume retained"),
                Line2D([], [], color=GREY, lw=1.55, ls=(0, (5, 2.4)), marker="s", markersize=5.1,
                       label="% of establishments in the panel")]
    ax.legend(handles=handles, loc="upper right", frameon=False, **LEGEND)


# ---------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of figure S6 and hand back the figure."""
    series = _series()
    _check(series)
    _crosscheck(series)

    style()
    plt.rcParams.update(PLATE_RC)
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN))     # 180 x 245 mm, as the stored plate
    # axes placed as in the stored plate: two columns of three, every panel the same box
    left, right, width, height = 0.077, 0.585, 0.359, 0.2594
    bottoms = [0.7230, 0.3902, 0.0419]
    boxes = {ch: fig.add_axes([left if i % 2 == 0 else right, bottoms[i // 2], width, height])
             for i, ch in enumerate("abcdef")}

    for ch in BAR_PANELS:
        _bar_panel(boxes[ch], ch, series[ch])
        _title(fig, boxes[ch], ch, series[ch][_eras_in_order(series[ch])[-1]]["series"])
    _panel_retention(boxes["f"], series)
    _title(fig, boxes["f"], "f", PANEL_F_TITLE)

    # panel (b) is the only one without a definition break, so the stored plate labels the pandemic
    # shading and the law marker there, once for the plate
    band = boxes["b"]
    band.text(2021.5, BAND_TEXT_Y, "Reporting\ndisruption 2021", transform=band.get_xaxis_transform(),
              ha="center", va="top", fontsize=FS_BAND, color=GREY, linespacing=1.15, zorder=3,
              bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.9))
    band.text(LAW_X + 0.02, BAND_TEXT_Y, "Law 21.545\n(context)",
              transform=band.get_xaxis_transform(), ha="left", va="top", fontsize=FS_BAND,
              color=LAW_DARK, linespacing=1.15, zorder=3)
    return fig


if __name__ == "__main__":
    figure = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/"qa"/f"{PLATE}_redraw.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=141, facecolor="white")
    print("wrote", out)
