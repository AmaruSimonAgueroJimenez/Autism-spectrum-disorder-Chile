"""Plate E11 — A03 in detail: every primary-care autism screening code by definition era.

The stored plate was drawn by `study/pipeline/` from the REM Serie A microdata, which this
repository does not carry. This module redraws its six panels from two tracked files:

  * `docs/study/corpus/tables/E11_rem_a03_codes_by_era.csv` — the published table behind the plate.
    Every cell is the formatted string `count (n establishments)`, or `outside the era` when the
    code did not exist that year; the last two rows are the altered-to-performed ratio as
    `62.8% (60.9-64.6)`. Panels a, b, d, e and f are parsed straight off it.
  * `output_files/consolidacion/rem_monthly_region_raw_columns.csv` — the monthly region-by-code
    file that panel c needs. Summing Col01+Col02 over regions reproduces the annual totals of the
    table exactly for 2019 (37,952 / 5,160 / 2,613 / 1,640), which is what ties the two together.

Estimator, unchanged from the original: unweighted administrative counts, never rates and never
standardised. The Serie A annual figure is a FLOW, the sum of the months of COL01+COL02 — Col01
alone gives 19,279 for 03500404 in 2019 and would not match the table's 37,952. Panel d is a
within-code-year proportion (03500407 / 03500406) with Wilson limits, taken as published.

The corpus is English only, so this module is English only.
"""
from pathlib import Path
import re
import sys
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent          # docs/study/plates
STUDY = HERE.parent                             # docs/study
ROOT = STUDY.parent.parent                      # repository root
if str(STUDY) not in sys.path:                  # import figstyle the way the figure scripts do
    sys.path.insert(0, str(STUDY))
from figstyle import *                          # noqa: E402,F401,F403

PLATE = "E11_rem_a03_codes_by_era"
SOURCES = [
    "docs/study/corpus/tables/E11_rem_a03_codes_by_era.csv",
    "output_files/consolidacion/rem_monthly_region_raw_columns.csv",
]
NOTE = ("Redraws the six panels of plate E11 — the annual flow of every A03 screening code by "
        "definition era, the 2019 monthly series, and the altered-to-performed ratio — from the "
        "published E11 table and, for the monthly panel, from the REM monthly region-by-code file.")

TABLE = ROOT/"docs"/"study"/"corpus"/"tables"/"E11_rem_a03_codes_by_era.csv"
MONTHLY = ROOT/"output_files"/"consolidacion"/"rem_monthly_region_raw_columns.csv"

# --- the four legacy codes of panels a to d, in code order -------------------------------------
LEGACY = ["03500404", "03500405", "03500406", "03500407"]
LEGACY_COLOUR = {"03500404": BLUE, "03500405": ORANGE, "03500406": GREEN, "03500407": PINK}

# --- short y-axis forms for panels e and f -----------------------------------------------------
# The stored plate labels these bars with short forms that no tracked file spells out; the table's
# own `Indicator` wording (kept in the legends of panels a to c, where the plate prints it verbatim)
# is too long for a bar label. The map below is the drawing code's, not data.
SHORT = {
    "09600212": "Suspected elsewhere",
    "09600213": "Low risk",
    "09600214": "Medium risk",
    "09600215": "High risk",
    "09600216": "High with referral",
    "09600217": "Part 2: medium in part 1",
    "09600218": "Part 2: no referral",
    "09600219": "Part 2: referral",
    "03700104": "Evaluated",
    "03700105": "Suspected elsewhere",
    "03700106": "Alert: yes",
    "03700107": "Alert: no",
    "03700108": "Referral: yes",
    "03700109": "Referral: no",
    "03710013": "Motive: EEDP",
    "03710014": "Motive: risk/alert",
    "03710015": "Motive: both",
    "03710016": "Low risk",
    "03710017": "Medium no referral",
    "03710018": "Medium referral",
    "03710019": "High referral",
    "03710020": "30–59 mo no referral",
    "03710021": "30–59 mo referral",
}

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
YEARS = [str(y) for y in range(2019, 2026)]
NOTE_BROWN = "#8b4513"        # the two in-panel notes of the stored plate
GREY_TEXT = "#555555"         # facet titles and the reporting-disruption label


# ---------------------------------------------------------------------------------------------
# reading the tracked tables
# ---------------------------------------------------------------------------------------------
def _read_table():
    """The published E11 table, with the count cells parsed into numbers.

    Returns (counts, establishments, indicator, ratios): the first three keyed by (code, year),
    the last a list with the two ratio rows.
    """
    raw = pd.read_csv(TABLE, dtype=str, encoding="utf-8-sig").fillna("")
    raw.columns = [c.strip() for c in raw.columns]
    counts, estab, indicator = {}, {}, {}
    ratios = []
    for _, row in raw.iterrows():
        code = row["Code"].strip()
        if "/" in code:                                   # the two altered-to-performed rows
            entry = {"label": row["Indicator"].split("—")[-1].strip()}
            for year in YEARS:
                parsed = _ratio_cell(row[year])
                if parsed is not None:
                    entry[int(year)] = parsed
            ratios.append(entry)
            continue
        indicator[code] = row["Indicator"].strip()
        for year in YEARS:
            parsed = _count_cell(row[year])
            if parsed is not None:
                counts[(code, int(year))], estab[(code, int(year))] = parsed
    return counts, estab, indicator, ratios


def _count_cell(cell):
    """'8,221 (731)' -> (8221, 731); 'outside the era' -> None."""
    m = re.fullmatch(r"([\d,]+)\s*\(([\d,]+)\)", cell.strip())
    if not m:
        return None
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


def _ratio_cell(cell):
    """'62.8% (60.9-64.6)' -> (62.8, 60.9, 64.6); 'outside the era' -> None."""
    m = re.fullmatch(r"([\d.]+)%\s*\(([\d.]+)[-–]([\d.]+)\)", cell.strip())
    if not m:
        return None
    return tuple(float(g) for g in m.groups())


def _monthly_2019():
    """Month totals of the four legacy codes in 2019: COL01+COL02 summed over regions.

    The same annual flow the E11 table publishes, kept by month instead of by year.
    """
    cols = ["year", "Mes", "IdRegion", "CodigoPrestacion", "Col01", "Col02"]
    raw = pd.read_csv(MONTHLY, usecols=cols, dtype={"CodigoPrestacion": str})
    raw = raw[(raw.year == 2019) & raw.CodigoPrestacion.isin(LEGACY)]
    raw["flow"] = raw.Col01.fillna(0) + raw.Col02.fillna(0)
    wide = (raw.groupby(["CodigoPrestacion", "Mes"])["flow"].sum()
               .unstack("Mes").reindex(index=LEGACY, columns=range(1, 13)).fillna(0))
    return wide


# ---------------------------------------------------------------------------------------------
# small drawing helpers
# ---------------------------------------------------------------------------------------------
def _heading(fig, x_letter, x_title, top, ch, title):
    """The stored plate heads every panel with a parenthesised letter and a wrapped title."""
    fig.text(x_letter, top, ch, fontweight="bold", fontsize=13.5, ha="left", va="top")
    fig.text(x_title, top, title, fontweight="bold", fontsize=12.5, ha="left", va="top",
             linespacing=1.15)


def _n_rows(ax, years, series, offsets, colours, counts_n):
    """Year tick labels carry one row of n per series, in the series' own colour."""
    for row, (code, off, colour) in enumerate(zip(series, offsets, colours)):
        for year in years:
            n = counts_n.get((code, year))
            if n is None:
                continue
            ax.text(year + off, -0.108 - 0.060*row, num(n, "en"), transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=8.6, color=colour, clip_on=False)


def _bar_labels(ax, ys, values, ns, colour="#1a1a1a", size=8.0, pad=0.008, xmax=None):
    """'8,221 (n=731)' just past the end of a horizontal bar."""
    for y, v, n in zip(ys, values, ns):
        if v is None or np.isnan(v):
            continue
        ax.text(v + pad*xmax, y, f"{num(v, 'en')} (n={num(n, 'en')})", ha="left", va="center",
                fontsize=size, color=colour, clip_on=False)


# ---------------------------------------------------------------------------------------------
# the six panels
# ---------------------------------------------------------------------------------------------
def _panel_a(ax, counts, estab, indicator):
    years = list(range(2019, 2025))
    codes = ["03500404", "03500405"]
    offs = (-0.19, 0.19)
    shade_pandemic(ax)
    for code, off in zip(codes, offs):
        ax.bar([y + off for y in years], [counts[(code, y)] for y in years], width=0.35,
               color=LEGACY_COLOUR[code], label=textwrap.fill(indicator[code], 18), zorder=3)
    law_line(ax, "en", y=0.985)
    clean(ax)
    ax.set_ylim(0, 175_000)                    # headroom for the legend, as in the stored plate
    ax.set_yticks(range(0, 180_000, 20_000))
    ax.yaxis.set_major_formatter(thousands("en"))
    year_ticks(ax, years)
    _n_rows(ax, years, codes, offs, [LEGACY_COLOUR[c] for c in codes], estab)
    ax.set_ylabel("Children or records (annual flow)")
    ax.set_xlabel("Year — below the axis, n = reporting\nestablishments, one row per series in its\ncolour",
                  labelpad=48, fontsize=9.0)
    ax.legend(loc="upper left", title="n = reporting\nestablishments", frameon=True,
              facecolor="white", edgecolor="none", framealpha=0.7, borderaxespad=0.3,
              labelspacing=0.35, handlelength=1.2, alignment="left", fontsize=8.8,
              title_fontsize=8.8)


def _panel_b(ax, counts, estab, indicator):
    years = list(range(2019, 2023))
    codes = ["03500406", "03500407"]
    offs = (-0.19, 0.19)
    shade_pandemic(ax)
    for code, off in zip(codes, offs):
        ax.bar([y + off for y in years], [counts[(code, y)] for y in years], width=0.35,
               color=LEGACY_COLOUR[code], label=textwrap.fill(indicator[code], 18), zorder=3)
    clean(ax)
    ax.set_ylim(0, 7_630)                      # headroom for the legend, as in the stored plate
    ax.set_yticks(range(0, 8_000, 1_000))
    ax.yaxis.set_major_formatter(thousands("en"))
    year_ticks(ax, years)
    _n_rows(ax, years, codes, offs, [LEGACY_COLOUR[c] for c in codes], estab)
    ax.set_ylabel("Screening records (annual flow)")
    ax.set_xlabel("Year — below the axis, n = reporting\nestablishments, one row per series in its\ncolour",
                  labelpad=48, fontsize=9.0)
    ax.legend(loc="upper left", title="n = reporting\nestablishments", frameon=True,
              facecolor="white", edgecolor="none", framealpha=0.7, borderaxespad=0.3,
              labelspacing=0.35, handlelength=1.2, alignment="left", fontsize=8.8,
              title_fontsize=8.8)


def _panel_c(ax, monthly, indicator):
    months = list(range(1, 13))
    ax.axvspan(1.5, 2.5, color=ORANGE, alpha=0.12, lw=0, zorder=0)
    for code in LEGACY:
        ax.plot(months, monthly.loc[code].values, marker="o", markersize=4.4,
                color=LEGACY_COLOUR[code], label=textwrap.fill(indicator[code], 20), zorder=3)
    clean(ax)
    ax.set_yscale("log")                       # the stored plate keeps the 10^k tick labels
    ax.set_ylim(20, 230_000)
    ax.set_xticks(months)
    ax.set_xticklabels(MONTH_ABBR, rotation=40, ha="right")
    ax.set_ylabel("Month total (log scale)")
    performed = monthly.loc["03500406", 2]
    altered = monthly.loc["03500407", 2]
    ax.text(0.19, 0.99,
            f"Feb 2019: {num(performed, 'en')} performed and\n{num(altered, 'en')} altered in a "
            f"single month\n(outlying file value; reported,\nnever corrected)",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.6, color=NOTE_BROWN,
            linespacing=1.05)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.151), ncol=2, frameon=False,
              handlelength=1.4, columnspacing=1.6, labelspacing=0.75)


def _panel_d(ax, counts, monthly, ratios):
    years = list(range(2019, 2023))
    shade_pandemic(ax)
    ax.text(2020.5, 0.711, "Reporting\ndisruption 2020–21", transform=ax.get_xaxis_transform(),
            ha="center", va="center", fontsize=9.4, color=GREY_TEXT, linespacing=1.15,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=2.5), zorder=4)
    # numerator / denominator of every point, from the same table (panel b's two codes) and,
    # for the February-free series, from the monthly file
    feb_alt, feb_perf = monthly.loc["03500407", 2], monthly.loc["03500406", 2]
    fractions = {
        "All months": {y: (counts[("03500407", y)], counts[("03500406", y)]) for y in years},
        "Excluding February 2019": {y: ((counts[("03500407", y)] - feb_alt,
                                         counts[("03500406", y)] - feb_perf) if y == 2019 else
                                        (counts[("03500407", y)], counts[("03500406", y)]))
                                    for y in years},
    }
    for entry, off, colour in zip(ratios, (-0.12, 0.12), (BLUE, GOLD)):
        xs = [y + off for y in years]
        point = [entry[y][0] for y in years]
        lo = [entry[y][0] - entry[y][1] for y in years]
        hi = [entry[y][2] - entry[y][0] for y in years]
        ax.errorbar(xs, point, yerr=[lo, hi], fmt="o", color=colour, ecolor=colour, elinewidth=1.8,
                    capsize=3.2, capthick=1.8, markersize=6.5, label=entry["label"], zorder=3)
        for x, y, p in zip(xs, years, point):
            n, d = fractions[entry["label"]][y]
            if entry["label"] != "All months" and fractions["All months"][y] == (n, d):
                continue                        # the stored plate prints the fraction only once
            dx = 0.28 if (entry["label"] == "All months" and y == 2019) else 0.0
            ax.text(x + dx, p + 4.0, f"{num(n, 'en')}/{num(d, 'en')}", ha="center", va="bottom",
                    fontsize=8.4, color=colour, zorder=4)
    clean(ax)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    year_ticks(ax, years)
    ax.set_xlabel("Year")
    ax.set_ylabel("Altered / performed (%, Wilson\n95% CI)", linespacing=1.1)
    ax.text(0.02, 0.99, "not population M-CHAT positivity: the\ndenominator is children with an already"
                        "\ndetected language or social-area alteration",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.6, color=NOTE_BROWN,
            linespacing=1.05)
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="none", framealpha=0.7,
              borderaxespad=0.4, handletextpad=0.5, labelspacing=0.45)


def _panel_e(ax, counts, estab):
    codes = [f"096002{i}" for i in range(12, 20)]
    ys = np.arange(len(codes))
    xmax = 29_650                               # room for the end labels, as in the stored plate
    for year, off, colour in ((2023, -0.19, GREEN), (2024, 0.19, GOLD)):
        vals = [counts.get((c, year)) for c in codes]
        keep = [(y + off, v, estab.get((c, year))) for y, v, c in zip(ys, vals, codes) if v is not None]
        ax.barh([k[0] for k in keep], [k[1] for k in keep], height=0.35, color=colour,
                label=str(year), zorder=3)
        _bar_labels(ax, [k[0] for k in keep], [k[1] for k in keep], [k[2] for k in keep], xmax=xmax)
    clean(ax, grid="x")
    ax.set_yticks(ys)
    ax.set_yticklabels([SHORT[c] for c in codes])
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.set_xticks(range(0, 30_000, 5_000))
    ax.xaxis.set_major_formatter(thousands("en"))
    ax.set_xlabel("Screening records (annual flow)")
    ax.legend(loc="lower right", title="n = reporting establishments", frameon=True,
              facecolor="white", edgecolor="none", framealpha=0.7, borderaxespad=0.4,
              handlelength=1.2, labelspacing=0.4, alignment="left")


def _panel_f(ax_top, ax_bottom, counts, estab):
    for ax, codes, year, colour, xmax, ticks, title in (
            (ax_top, [f"037001{i:02d}" for i in range(4, 10)], 2024, SKY, 61_500,
             range(0, 60_001, 20_000), "2024 era: 31–59 months"),
            (ax_bottom, [f"037100{i:02d}" for i in range(13, 22)], 2025, GREEN, 22_800,
             range(0, 20_001, 5_000), "2025 era: redesign")):
        ys = np.arange(len(codes))
        vals = [counts[(c, year)] for c in codes]
        ns = [estab[(c, year)] for c in codes]
        ax.barh(ys, vals, height=0.62, color=colour, zorder=3)
        _bar_labels(ax, ys, vals, ns, size=7.4, xmax=xmax)
        clean(ax, grid="x")
        ax.set_yticks(ys)
        ax.set_yticklabels([SHORT[c] for c in codes], fontsize=7.6)
        ax.invert_yaxis()
        ax.set_xlim(0, xmax)
        ax.set_xticks(list(ticks))
        ax.xaxis.set_major_formatter(thousands("en"))
        ax.text(0.0, 1.05, title, transform=ax.transAxes, ha="left", va="bottom", fontsize=10,
                color=GREY_TEXT)
    ax_bottom.set_xlabel("Screening records (annual flow)", fontsize=9.0)


# ---------------------------------------------------------------------------------------------
def draw():
    counts, estab, indicator, ratios = _read_table()
    monthly = _monthly_2019()

    style()
    plt.rcParams.update({"xtick.labelsize": 9.5, "ytick.labelsize": 8.3, "axes.labelsize": 11,
                         "legend.fontsize": 8.0, "legend.title_fontsize": 8.0,
                         "xtick.major.size": 0, "ytick.major.size": 0,
                         "xtick.major.pad": 4, "ytick.major.pad": 5.5})
    fig = plt.figure(figsize=(10.0, 13.61))     # the stored plate's proportions, 1000 x 1361 px

    ax_a = fig.add_axes([0.168, 0.75533, 0.360, 0.20867])
    ax_b = fig.add_axes([0.622, 0.75533, 0.360, 0.20867])
    ax_c = fig.add_axes([0.168, 0.40338, 0.360, 0.20867])
    ax_d = fig.add_axes([0.622, 0.40338, 0.360, 0.20867])
    ax_e = fig.add_axes([0.168, 0.03380, 0.360, 0.20867])
    ax_f1 = fig.add_axes([0.744, 0.15062, 0.231, 0.07127])
    ax_f2 = fig.add_axes([0.744, 0.04629, 0.231, 0.07127])

    _panel_a(ax_a, counts, estab, indicator)
    _panel_b(ax_b, counts, estab, indicator)
    _panel_c(ax_c, monthly, indicator)
    _panel_d(ax_d, counts, monthly, ratios)
    _panel_e(ax_e, counts, estab)
    _panel_f(ax_f1, ax_f2, counts, estab)

    _heading(fig, 0.013, 0.055, 0.99376, "(a)",
             "A03 legacy era 2019–2024: 18-month\ncontrol and detected alteration")
    _heading(fig, 0.513, 0.555, 0.99376, "(b)",
             "A03 legacy era 2019–2022: M-CHAT\nperformed and altered")
    _heading(fig, 0.013, 0.055, 0.64106, "(c)",
             "Legacy era by month, 2019: the February\noutlier")
    _heading(fig, 0.513, 0.555, 0.64106, "(d)",
             "Altered-to-performed ratio within the\nlegacy era")
    _heading(fig, 0.013, 0.055, 0.27226, "(e)",
             "A03 2023–2024 era (M-CHAT-R/F): every\ncode")
    _heading(fig, 0.513, 0.555, 0.27226, "(f)",
             "A03 2024 and 2025 eras: 31–59-month\ncodes and the redesign")
    return fig


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE/f"{PLATE}_redraw.png"
    draw().savefig(out, dpi=100, facecolor="white")
    print("wrote", out)
