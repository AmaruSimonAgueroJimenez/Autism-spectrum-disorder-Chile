"""E19 — definition-era sensitivity of every REM indicator, redrawn from the tracked tables.

The stored plate was drawn by `study/pipeline/` from the REM Serie A and Serie P microdata, which
this repository does not carry. All six panels survive in published aggregates and are redrawn from
two tracked tables:

  (a–d) `docs/study/corpus/tables/E19_rem_definition_era_sensitivity.csv` — the presentation table
        of the plate. Every count cell is the formatted string `count (n establishments)`, or
        `outside the era` when the code did not exist that year; the `Family / strict` rows are a
        bare ratio. Panels a–d are the Broad PDD, Strict autism and PDD family rows of the four
        Series, with their n labels, parsed straight off it.
  (e)   `docs/study/corpus/tables/E69_rem_code_year_full.csv` — E19 carries the family only as a
        total, so the composition panel needs the code-level table. The four member codes of each
        family (05990022/23/25/26 for entries, 05990027/28/30/31 for clinical discharges,
        P6241010/20/40/50 for primary care, P6241060/70/90/100 for specialty) are summed to the
        E19 family total of the same year, which is asserted in `_composition()` before drawing.
  (f)   the `Family / strict` rows of the E19 table, taken as published and never recomputed.

Estimator, unchanged from the original: unweighted administrative counts, no survey weighting, no
standardisation and no rates. The units differ by panel and the plate keeps them apart — A05 entries
and A05 clinical discharges are an annual FLOW (`Flow: annual sum` in E69), while P6 is the December
STOCK (`Stock: December`, never the June sensitivity). The case definition is the F84 family
EXCLUDING Rett syndrome: 05990024, 05990029, P6241030 and P6241080 are listed separately in E69 and
are not in any family sum here. The pre-2021 broad category and the 2021+ strict and family
definitions measure different objects, so the bars either side of the break are neither joined by a
line nor differenced, and the definition-break marker at 2020.5 is kept. The family/strict ratio is
always within the same year and the same source.

The corpus is English only, so this module is English only.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # docs/study, so `figstyle` resolves
from figstyle import *                                          # noqa: E402,F401,F403  (house style)

PLATE = "E19_rem_definition_era_sensitivity"
SOURCES = [
    "docs/study/corpus/tables/E19_rem_definition_era_sensitivity.csv",
    "docs/study/corpus/tables/E69_rem_code_year_full.csv",
]
ERA_TABLE, CODE_TABLE = SOURCES
NOTE = ("Redraws the six panels of E19 — the four REM indicators under the broad pre-2021 category, "
        "strict autism and the variant PDD family, the composition of that family by category in "
        "2021 and 2025, and the family/strict ratio — from the published definition-era table and "
        "the code-level REM table, keeping A05 as an annual flow and P6 as the December stock and "
        "the family as F84 excluding Rett syndrome.")

ROOT = BASE.parent.parent                      # docs/study -> docs -> repository root
YEARS = list(range(2019, 2026))

# --- the four Series of the table, one per panel of (a)-(d); wording verbatim from its Series column
SERIES = ["A05 entries", "A05 clinical discharges", "P6 primary care", "P6 specialty"]

# --- the three definition eras, wording verbatim from the table's 'Definition era' column ---------
BROAD, STRICT, FAMILY, RATIO = ("Broad PDD (pre-2021)", "Strict autism",
                                "PDD family (variant)", "Family / strict")
BROAD_GREY = "#d9d9d9"                          # the pre-2021 bars of the stored plate
ERA_COLOUR = {BROAD: BROAD_GREY, STRICT: BLUE, FAMILY: GREEN}

# --- panel (e): the four member codes of each family, and the measure each Series is counted on ---
# E69 lists every code separately; the summary rows ('A05 ...', 'P6 population ...') repeat the same
# numbers and are skipped so that each (code, measure) resolves to exactly one row. Rett syndrome
# (05990024, 05990029, P6241030, P6241080) is not a member of any of these families.
CATEGORIES = ["Autism", "Asperger", "Disintegrative disorder", "PDD unspecified"]
CATEGORY_COLOUR = dict(zip(CATEGORIES, [BLUE, ORANGE, GREEN, PINK]))
# short forms of the E69 Indicator wording ('Entry: childhood disintegrative disorder', ...); the
# longest of the four is wrapped in the legend, as in the stored plate
CATEGORY_LEGEND = {"Disintegrative disorder": "Disintegrative\ndisorder"}
COMPOSITION = {
    "A05 entries": ("Flow: annual sum", ["05990022", "05990023", "05990025", "05990026"]),
    "A05 clinical discharges": ("Flow: annual sum", ["05990027", "05990028", "05990030", "05990031"]),
    "P6 primary care": ("Stock: December", ["P6241010", "P6241020", "P6241040", "P6241050"]),
    "P6 specialty": ("Stock: December", ["P6241060", "P6241070", "P6241090", "P6241100"]),
}
COMPOSITION_YEARS = [2021, 2025]                # the first and last year of each indicator
LABEL_FLOOR = 4.0                               # below this share the segment is too thin to label

# --- geometry and marks measured off the stored plate ---------------------------------------------
BREAK_X = 2020.5                # the definition break sits between the 2020 and 2021 bars
# Law 21.545 was published on 10 March 2023. The stored plate puts the marker immediately to the
# left of the 2023 bar group so that it does not cross the bars; it is policy context only.
LAW_X = 2023 - 0.35
HEADROOM = 1.64                 # top of (a)-(d), leaving the stored plate's room for the legend
BREAK_GREY = "#555555"          # the 'definition break' and panel (e) group captions
LABEL_DARK = "#333333"          # the count and n labels above the bars
NOTE_BROWN = "#8b4513"          # the x-axis note of panel (f)
ERA_NOTE = "Year — separate eras: the totals do not form a\ncontinuous series"

PANEL_TITLE = {
    "a": "A05 entries by era and definition",
    "b": "A05 clinical discharges by era and\ndefinition",
    "c": "P6 primary care (December) by era and\ndefinition",
    "d": "P6 specialty (December) by era and\ndefinition",
    "e": "Composition of the PDD family by\ncategory — F84 family excluding Rett\nsyndrome",
    "f": "PDD family / strict autism ratio",
}
Y_LABEL = {
    "A05 entries": "Entries (annual flow)",
    "A05 clinical discharges": "Clinical discharges (annual flow)",
    "P6 primary care": "People under control in December\n(stock)",
    "P6 specialty": "People under control in December\n(stock)",
}
# Panel (f) prints every point; the offsets below are the drawing code's own placement, chosen as in
# the stored plate so that four series crossing between 2022 and 2023 stay readable.
RATIO_LABEL = {
    ("A05 entries", 2021): (1, -4, "center", "top"),
    ("A05 entries", 2022): (0, -4, "center", "top"),
    ("A05 entries", 2023): (0, -4, "center", "top"),
    ("A05 entries", 2024): (0, -4, "center", "top"),
    ("A05 entries", 2025): (1, 11, "center", "bottom"),
    ("A05 clinical discharges", 2021): (0, 11, "center", "bottom"),
    ("A05 clinical discharges", 2022): (1, 11, "center", "bottom"),
    ("A05 clinical discharges", 2023): (0, 11, "center", "bottom"),
    ("A05 clinical discharges", 2024): (9, 4, "left", "center"),
    ("A05 clinical discharges", 2025): (-9, 3, "right", "center"),
    ("P6 primary care", 2021): (8, 4, "left", "center"),
    ("P6 primary care", 2022): (2, -4, "center", "top"),
    ("P6 primary care", 2023): (8, 3, "left", "center"),
    ("P6 primary care", 2024): (0, 11, "center", "bottom"),
    ("P6 primary care", 2025): (2, 24, "center", "bottom"),
    ("P6 specialty", 2021): (8, 4, "left", "center"),
    ("P6 specialty", 2022): (9, 4, "left", "center"),
    ("P6 specialty", 2023): (7, 4, "left", "center"),
    ("P6 specialty", 2024): (0, 11, "center", "bottom"),
    ("P6 specialty", 2025): (-7, 4, "right", "center"),
}
RATIO_COLOUR = dict(zip(SERIES, [BLUE, ORANGE, GREEN, PINK]))


# ------------------------------------------------------------------ the tracked tables and parsing
def _read(rel):
    """Read one tracked table by its repository-relative path (the paths listed in SOURCES)."""
    table = pd.read_csv(ROOT/rel, dtype=str, encoding="utf-8-sig").fillna("")
    table.columns = [c.strip() for c in table.columns]
    return table


def _count_cell(cell):
    """'4,417 (651)' -> (4417, 651); 'outside the era' -> None."""
    m = re.fullmatch(r"([\d,]+)\s*\(([\d,]+)\)", cell.strip())
    return None if m is None else (int(m.group(1).replace(",", "")),
                                   int(m.group(2).replace(",", "")))


def _ratio_cell(cell):
    """'2.37' -> 2.37; 'outside the era' -> None."""
    m = re.fullmatch(r"\d+\.\d+", cell.strip())
    return None if m is None else float(cell.strip())


def _first_field(cell):
    """E69 stores '2,085; 449; 1,522'; the count is the first field, else None."""
    head = cell.split(";")[0].strip()
    m = re.fullmatch(r"[\d,]+", head)
    return None if m is None else int(head.replace(",", ""))


def _eras():
    """The E19 table as {Series: {era: {year: (count, n)}}} plus the published ratios."""
    table = _read(ERA_TABLE)
    counts = {s: {BROAD: {}, STRICT: {}, FAMILY: {}} for s in SERIES}
    ratios = {s: {} for s in SERIES}
    for _, row in table.iterrows():
        series, era = row["Series"].strip(), row["Definition era"].strip()
        if series not in counts:
            continue
        for year in YEARS:
            cell = row[str(year)]
            if era == RATIO:
                value = _ratio_cell(cell)
                if value is not None:
                    ratios[series][year] = value
            elif era in counts[series]:
                value = _count_cell(cell)
                if value is not None:
                    counts[series][era][year] = value
    return counts, ratios


def _composition(family_totals):
    """Panel (e): the four category counts of every Series and year, from the code-level table.

    `family_totals` is {Series: {year: family count}} out of E19; each set of four codes must sum
    to it, which is what ties the two tracked tables together.
    """
    table = _read(CODE_TABLE)
    # the summary rows repeat the per-code numbers under a different Indicator; drop them so that
    # (code, measure) is unique
    per_code = table[~table["Indicator"].str.startswith(("A05 ", "P6 "))]
    out = {}
    for series, (measure, codes) in COMPOSITION.items():
        out[series] = {}
        for year in COMPOSITION_YEARS:
            shares = {}
            for category, code in zip(CATEGORIES, codes):
                rows = per_code[(per_code["Code"] == code) & (per_code["Measure"] == measure)]
                assert len(rows) == 1, f"{code} {measure}: {len(rows)} rows in {CODE_TABLE}"
                value = _first_field(rows.iloc[0][str(year)])
                assert value is not None, f"{code} has no {year} count"
                shares[category] = value
            total = sum(shares.values())
            published = family_totals[series][year][0]
            assert total == published, f"{series} {year}: {total} != published {published}"
            out[series][year] = {c: 100 * v / total for c, v in shares.items()}
    return out


# ------------------------------------------------------------------------------ drawing the panels
LINE_PITCH = 0.0147             # one title line, in figure fractions of the stored plate


def _panel_letter(fig, ch, x_letter, x_title, y):
    """The stored plate heads each panel with a bold letter and a bold, hand-wrapped title.

    The title block sits on the top of the axes, so a two- or three-line title grows upwards; the
    letter stays beside the FIRST line, which is why it is offset by the extra lines.
    """
    lines = PANEL_TITLE[ch].count("\n")
    fig.text(x_letter, y + lines*LINE_PITCH, f"({ch})", fontweight="bold", fontsize=12, ha="left",
             va="bottom")
    fig.text(x_title, y, PANEL_TITLE[ch], fontweight="bold", fontsize=10.5, ha="left", va="bottom",
             linespacing=1.13)


def _era_panel(ax, series, counts, ytick_step):
    """(a)-(d): the three definition eras of one Series, side by side, never joined across the break."""
    broad, strict, family = (counts[series][e] for e in (BROAD, STRICT, FAMILY))
    top = HEADROOM * max(v for v, _ in family.values())

    shade_pandemic(ax)
    ax.axvline(BREAK_X, color=GREY, ls=(0, (6, 2, 1, 2)), lw=1.3, zorder=2)
    ax.text(BREAK_X, 0.553, "definition\nbreak", transform=ax.get_xaxis_transform(), ha="center",
            va="center", fontsize=7.5, color=BREAK_GREY, linespacing=1.11,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=2.4), zorder=3)
    law_line(ax, "en", x=LAW_X, label=False, color="#222222")
    ax.text(LAW_X + 0.08, 0.803, "Law 21.545\n(context)", transform=ax.get_xaxis_transform(),
            ha="left", va="top", fontsize=8, color="#222222", linespacing=1.05)

    ax.bar(list(broad), [v for v, _ in broad.values()], width=0.50, color=BROAD_GREY,
           edgecolor=LABEL_DARK, lw=0.7, zorder=3)
    ax.bar([y - 0.185 for y in strict], [v for v, _ in strict.values()], width=0.32, color=BLUE,
           zorder=3)
    ax.bar([y + 0.185 for y in family], [v for v, _ in family.values()], width=0.32, color=GREEN,
           zorder=3)

    pad = 0.012 * top
    for year, (value, n) in broad.items():        # the pre-2021 bars carry the count and the n
        ax.text(year, value + pad, f"{num(value, 'en')}\nn={num(n, 'en')}", ha="center",
                va="bottom", fontsize=7.5, color=LABEL_DARK, linespacing=1.2, zorder=4)
    for year, (value, n) in strict.items():       # the strict bar carries its reporting n only
        ax.text(year - 0.185, value + pad, f"n={num(n, 'en')}", ha="center", va="bottom",
                rotation=90, fontsize=7.5, color=LABEL_DARK, zorder=4)
    for year, (value, _) in family.items():       # the family bar carries its total
        ax.text(year + 0.185, value + pad, num(value, "en"), ha="center", va="bottom", rotation=90,
                fontsize=7.5, color=GREEN, zorder=4)

    clean(ax, "both")
    ax.set_xlim(2018.4, 2025.7)
    ax.set_ylim(0, top)
    ax.yaxis.set_major_locator(MultipleLocator(ytick_step))
    ax.yaxis.set_major_formatter(thousands("en"))
    year_ticks(ax, YEARS)
    ax.set_xlabel("Year")
    ax.set_ylabel(Y_LABEL[series], linespacing=1.2)
    ax.legend(handles=[Patch(facecolor=BROAD_GREY, edgecolor=LABEL_DARK, lw=0.7, label=BROAD),
                       Patch(facecolor=BLUE, label=STRICT), Patch(facecolor=GREEN, label=FAMILY)],
              loc="upper right", frameon=False, handlelength=1.5, handleheight=0.9,
              labelspacing=0.4, borderaxespad=0.2)


def _panel_composition(ax, composition):
    """(e): the PDD family split by category, as a percentage of the year total."""
    spots = np.arange(len(SERIES))
    offsets = dict(zip(COMPOSITION_YEARS, (-0.185, 0.185)))
    ticks, labels = [], []
    for spot, series in zip(spots, SERIES):
        for year in COMPOSITION_YEARS:
            x = spot + offsets[year]
            ticks.append(x)
            labels.append(str(year))
            bottom = 0.0
            for category in CATEGORIES:
                share = composition[series][year][category]
                legend = CATEGORY_LEGEND.get(category, category)
                ax.bar(x, share, bottom=bottom, width=0.235, color=CATEGORY_COLOUR[category],
                       zorder=3, label=legend if (spot == 0 and year == 2021) else None)
                if share >= LABEL_FLOOR:
                    ax.text(x, bottom + share/2, f"{share:.1f}", ha="center", va="center",
                            fontsize=7.5, color=LABEL_DARK, zorder=4,
                            bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.2))
                bottom += share
        ax.text(spot, -0.085, series.replace("A05 clinical ", "A05 clinical\n")
                                    .replace("P6 primary ", "P6 primary\n"),
                transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=7.5,
                color=BREAK_GREY, linespacing=1.25)

    clean(ax, "both")
    ax.set_xlim(-0.5, len(SERIES) - 0.5)
    ax.set_ylim(0, 132.3)                       # the stored plate's room for the legend above
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_yticks(range(0, 101, 20))            # the bars stop at 100; the headroom carries no ticks
    ax.set_ylabel("% of the year total")
    ax.legend(loc="upper center", ncol=3, frameon=False, handlelength=1.1, columnspacing=0.5,
              labelspacing=0.25, borderaxespad=0.1)


def _panel_ratio(ax, ratios):
    """(f): the family total over the strict-autism total, within the same year and the same source."""
    years = sorted(ratios[SERIES[0]])
    ax.axhline(1.0, color=GREY, ls=":", lw=1.6, zorder=1)
    for series in SERIES:
        colour = RATIO_COLOUR[series]
        values = [ratios[series][y] for y in years]
        ax.plot(years, values, marker="o", markersize=6, lw=2.0, color=colour, label=series,
                zorder=3)
        for year, value in zip(years, values):
            dx, dy, ha, va = RATIO_LABEL[(series, year)]
            ax.annotate(f"{value:.2f}", (year, value), xytext=(dx, dy), textcoords="offset points",
                        ha=ha, va=va, fontsize=7.5, color=colour, zorder=4)

    clean(ax, "both")
    ax.set_xlim(2020.8, 2025.2)
    ax.set_ylim(0.908, 4.668)                   # the stored plate's room for the four-entry legend
    ax.set_yticks(np.arange(1.0, 4.75, 0.5))
    ax.set_yticklabels([f"{v:.1f}" for v in np.arange(1.0, 4.75, 0.5)])
    year_ticks(ax, years)
    ax.set_ylabel("Family / strict")
    ax.set_xlabel(ERA_NOTE, color=NOTE_BROWN, linespacing=1.25)
    ax.legend(loc="upper right", frameon=False, handlelength=1.6, labelspacing=0.45,
              borderaxespad=0.2)


# ---------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of E19 and hand back the figure."""
    counts, ratios = _eras()
    composition = _composition({s: counts[s][FAMILY] for s in SERIES})

    style()
    # the stored plate draws no tick marks, only the labels
    plt.rcParams.update({"xtick.major.size": 0, "ytick.major.size": 0,
                         "xtick.major.pad": 3, "ytick.major.pad": 3.5})
    fig = plt.figure(figsize=(210/25.4, 286/25.4))     # a full page, as the stored plate
    # axes placed as in the stored plate: two columns of three, every panel the same box
    left, right, width, height = 0.095, 0.598, 0.393, 0.2542
    bottoms = [0.7098, 0.3769, 0.0441]
    boxes = {ch: fig.add_axes([left if i % 2 == 0 else right, bottoms[i // 2], width, height])
             for i, ch in enumerate("abcdef")}

    for ch, series, step in zip("abcd", SERIES, (5_000, 1_000, 5_000, 5_000)):
        _era_panel(boxes[ch], series, counts, step)
    _panel_composition(boxes["e"], composition)
    _panel_ratio(boxes["f"], ratios)

    for ch, y in zip("abcdef", (0.9662, 0.9662, 0.6348, 0.6348, 0.2998, 0.2998)):
        _panel_letter(fig, ch, 0.011 if ch in "ace" else 0.511, 0.055 if ch in "ace" else 0.553, y)
    return fig


if __name__ == "__main__":
    figure = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/"qa"/f"{PLATE}_redraw.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=121, facecolor="white")
    print("wrote", out)
