"""Plate S8 — REM A05 entries by age group and sex per year: strict autism and the variant's PDD family.

The stored plate was drawn by `study/pipeline/08b_figures_rem.py` from `outputs/tidy/rem_a05_age_sex.csv`,
which is not in this repository. Its six panels are redrawn here from the two published tables that
carry the same series:

* `S8_a05_age_sex.csv` — the plate's own numeric companion: Series (strict autism / PDD family) x Sex
  (Males / Females) x the eleven heat-map age groups (five-year up to 45–49, with 50+ pooling 50–54 to
  80+) by year 2021–2025. These twelve series of five columns ARE the four heat maps, and panels (c)
  and (d) are derived from the strict-autism half of them;
* `ST13_a05_age_sex.csv` — for the `n` printed under every year: its 'Reporting establishments (n)'
  row, one per block, gives 449 / 658 / 920 / 1,070 / 952 for strict autism and 710 / 869 / 1,040 /
  1,153 / 995 for the PDD family.

The estimators are the stored plate's own:

* the four heat maps are RAW ADMINISTRATIVE COUNTS of A05 entries — an annual flow, summed over
  establishment and month and located by place of care. They are not rates and not standardised: the
  colour scale is 'Entries reported', each panel scaled from 0 to its own maximum;
* panel (c) is the percentage distribution of the year's strict-autism entries over six age bands,
  both sexes pooled — 20–29 pools 20–24 with 25–29, and 30+ pools everything from 30–34 up;
* panel (d) is the male-to-female ratio of ENTRIES (a ratio of counts) with the Poisson log-normal
  interval, ratio x exp(+/-1.96 sqrt(1/m + 1/f)). It is not the M:F ratio of standardised rates of
  figS7 panel (c), and the two must never be swapped.

Case definition: strict autism 05990022 for panels (a)–(d); the variant's PDD family
(05990022+05990023+05990025+05990026, the without-Rett variant) for panels (e)–(f).

The caption's 'n/e' convention is kept: an age x sex cell that appears in no row of the code that year
is an ABSENT row, not a measured zero, and is printed 'n/e' rather than filled with 0. S8 stores such
cells blank; in the tracked table as published every one of the 220 cells is present, so no 'n/e' is
drawn — the branch is here because the convention, not the current table, is what the plate asserts.

The corpus is English only, so this module is too.
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from figstyle import *

PLATE = "figS8_a05_age_sex"
SOURCES = [
    "docs/study/corpus/tables/S8_a05_age_sex.csv",
    "docs/study/corpus/tables/ST13_a05_age_sex.csv",
]
NOTE = ("Redraws the six panels of plate S8 — the four age x sex heat maps of A05 entries (strict "
        "autism and the variant's PDD family, males and females, 2021–2025), the age-band composition "
        "of strict-autism entries and their male-to-female ratio by age with a Poisson log-normal "
        "interval — from the published S8 table, with the reporting establishments printed under each "
        "year read from the numeric companion ST13.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
CELL_MARGIN = 2.0 / 180.0                       # panel titles hang 2 mm inside their grid cell

YEARS = [2021, 2022, 2023, 2024, 2025]          # the A05 years of the stored plate
# The eleven rows of every heat map, verbatim from the table: five-year groups to 45–49, then 50+.
AGES = ["0–4", "5–9", "10–14", "15–19", "20–24", "25–29", "30–34", "35–39", "40–44", "45–49", "50+"]
RATIO_AGES = AGES[:7]                           # panel (d) stops at 30–34, as the caption says
SEXES = ["Males", "Females"]                    # verbatim in the table's Sex column
SERIES = {"strict": "strict autism", "family": "PDD family"}     # verbatim in the table's Series column
# The blocks of ST13 that carry the establishments of each series (matched on their opening words).
ESTAB_BLOCK = {"strict": "Strict autism", "family": "PDD family"}

# Okabe-Ito, in the order the pipeline gives the five years (sky, blue, green, gold, orange).
YEAR_COLORS = dict(zip(YEARS, [SKY, BLUE, GREEN, GOLD, ORANGE]))
DARK = "#333333"                                # the ink of a cell label on a pale cell
WHITE_CUT = 0.55                                # above this share of the panel maximum the label is white
# The corpus's own backing rule: a dark label that falls on the data's ink gets a translucent white box.
BACKING = dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9)
Z = 1.959964                                    # the two-sided 95 % normal quantile of the pipeline
LABEL_MIN = 5.0                                 # panel (c) labels the bands that reach 5 %
# The six age bands of panel (c): the label, then the rows of the table it pools.
BANDS = [("0–4", ["0–4"]), ("5–9", ["5–9"]), ("10–14", ["10–14"]), ("15–19", ["15–19"]),
         ("20–29", ["20–24", "25–29"]), ("30+", ["30–34", "35–39", "40–44", "45–49", "50+"])]

AGE_AXIS = "Age group (years)"
YEAR_AXIS = "Year (n = reporting establishments)"
ESTAB_LEGEND = "n = reporting establishments"
TITLES = {
    "a": "(a) Strict autism: entries, males",
    "b": "(b) Strict autism: entries, females",
    "c": "(c) Strict autism: age distribution (%)",
    "d": "(d) Strict autism: M:F ratio of entries by age",
    "e": "(e) PDD family: entries, males",
    "f": "(f) PDD family: entries, females",
}


# --------------------------------------------------------------------------- reading the tables
def _num(s):
    """One formatted cell -> float; 'n/e' (not estimable) and a blank cell -> nan.

    A blank or 'n/e' is the caption's absent row: the age x sex cell appears in no row of the code that
    year. It is NOT a zero and must never be read as one."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-"))


def _table(rel):
    """A tracked presentation table, read as text (they are written with a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str)


def counts():
    """{(series key, sex): 11 age groups x 5 years} of A05 entries, absent cells left as nan."""
    t = _table(SOURCES[0])
    out = {}
    for key, name in SERIES.items():
        for sex in SEXES:
            rows = t[(t["Series"] == name) & (t["Sex"] == sex)].set_index("Age group")
            missing = [a for a in AGES if a not in rows.index]
            assert not missing, f"S8 has no {name} {sex} row for {missing}"
            out[(key, sex)] = np.array([[_num(rows.loc[a, str(y)]) for y in YEARS] for a in AGES])
    return out


def establishments():
    """{series key: the 5 reporting-establishment counts} from the ST13 block of each series."""
    t = _table(SOURCES[1])
    label = t.columns[2]                        # 'Age group (years)' — it also labels the summary rows
    out = {}
    for key, opening in ESTAB_BLOCK.items():
        hit = t[t["Block"].str.startswith(opening) & (t[label] == "Reporting establishments (n)")]
        assert len(hit) == 1, f"ST13 has {len(hit)} establishment rows for {opening}"
        out[key] = np.array([_num(hit.iloc[0][str(y)]) for y in YEARS])
        assert np.isfinite(out[key]).all(), f"ST13 leaves an A05 year of {opening} without a count"
    return out


def composition(strict_m, strict_f):
    """Panel (c): the six age bands as percentages of each year's strict-autism entries, both sexes.

    An absent cell contributes nothing to the band — it is not a zero, but it is not a count either."""
    both = np.nan_to_num(strict_m) + np.nan_to_num(strict_f)
    banded = np.array([both[[AGES.index(a) for a in rows], :].sum(axis=0) for _lab, rows in BANDS])
    share = 100.0 * banded / banded.sum(axis=0)
    assert np.allclose(share.sum(axis=0), 100.0), "the age composition does not add to 100"
    return share


def mf_ratio(male, female):
    """Panel (d): male/female ratio of entries with the Poisson log-normal 95 % interval.

    se = sqrt(1/m + 1/f) on the log scale, so the limits are ratio x exp(-/+ z se). A group with no
    entry of either sex has no ratio and is left blank."""
    m = np.nan_to_num(male)
    f = np.nan_to_num(female)
    ok = (m > 0) & (f > 0)
    ratio = np.where(ok, m / np.where(f > 0, f, 1.0), np.nan)
    se = np.where(ok, np.sqrt(1.0 / np.where(m > 0, m, 1.0) + 1.0 / np.where(f > 0, f, 1.0)), np.nan)
    return ratio, ratio * np.exp(-Z * se), ratio * np.exp(Z * se)


# --------------------------------------------------------------------------- panel furniture
def _heat(fig, ax, matrix, estab, title):
    """One heat map: the eleven age groups by the five years, scaled 0 to the panel's own maximum."""
    top = float(np.nanmax(matrix))
    # imshow cannot paint a nan, so an absent cell is drawn at the floor of the scale and then said
    # in words ('n/e'); it is never given the colour of a measured value.
    ax.imshow(np.where(np.isnan(matrix), 0.0, matrix), cmap=sns.color_palette("crest", as_cmap=True),
              aspect="auto", vmin=0, vmax=top)
    ax.grid(False)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            pale = np.isnan(v) or v <= WHITE_CUT * top
            ax.text(j, i, "n/e" if np.isnan(v) else num(v, "en"), ha="center", va="center",
                    fontsize=6.3, color=DARK if pale else "white", zorder=5,
                    bbox=dict(BACKING) if pale else None)
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels([f"{y}\nn={num(n, 'en')}" for y, n in zip(YEARS, estab)], fontsize=6.2)
    ax.set_yticks(range(len(AGES)))
    ax.set_yticklabels(AGES, fontsize=6.5)
    ax.set_xlabel(YEAR_AXIS)
    ax.set_ylabel(AGE_AXIS)
    cb = fig.colorbar(ax.images[0], ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("Entries reported", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    cb.ax.yaxis.set_major_formatter(thousands("en"))
    return ax.set_title(title, loc="left", fontsize=9, fontweight="bold", pad=3.0)


def draw():
    style()
    plt.rcParams.update({
        # The plate's own body: 8 pt base, 9 pt bold panel head, 7 pt ticks and legend, 6 pt floor.
        "font.size": 8.0, "axes.titlesize": 9.0, "axes.titleweight": "bold", "axes.labelsize": 8.0,
        "xtick.labelsize": 7.0, "ytick.labelsize": 7.0, "legend.fontsize": 7.0,
        "legend.title_fontsize": 7.0, "axes.linewidth": 0.7, "lines.linewidth": 1.3,
        "lines.markersize": 3.4, "patch.linewidth": 0.6, "axes.labelpad": 2.0, "axes.titlepad": 3.0,
        "legend.handlelength": 1.5, "legend.handletextpad": 0.5, "legend.labelspacing": 0.30,
        "legend.columnspacing": 0.9, "legend.borderpad": 0.3,
        # seaborn's white grid, as the pipeline's `style()` sets it: grid on both axes, no tick marks.
        "axes.edgecolor": DARK, "axes.grid": True, "grid.color": "#b0b0b0", "grid.alpha": 0.35,
        "grid.linewidth": 0.45, "xtick.bottom": False, "ytick.left": False,
        "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    })
    cell = counts()
    estab = establishments()

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    titles = {}

    # (a), (b), (e), (f) the four heat maps ----------------------------------------------------------
    for (row, col), key, sex, letter_ in (((0, 0), "strict", "Males", "a"), ((0, 1), "strict", "Females", "b"),
                                          ((2, 0), "family", "Males", "e"), ((2, 1), "family", "Females", "f")):
        titles[axes[row, col]] = _heat(fig, axes[row, col], cell[(key, sex)], estab[key], TITLES[letter_])

    # (c) age composition of the year's strict-autism entries, both sexes ----------------------------
    c = axes[1, 0]
    share = composition(cell[("strict", "Males")], cell[("strict", "Females")])
    palette = sns.color_palette("crest", len(BANDS))
    bottom = np.zeros(len(YEARS))
    for (label, _rows), colour, band in zip(BANDS, palette, share):
        c.bar(YEARS, band, bottom=bottom, color=colour, width=0.7, label=label, edgecolor="white")
        for year, base, value in zip(YEARS, bottom, band):
            if value >= LABEL_MIN:              # a shorter band has no room for its own label
                c.text(year, base + value / 2, f"{value:.0f}%", ha="center", va="center", fontsize=6.2,
                       color="white" if colour[2] < 0.6 else DARK, zorder=5)
        bottom = bottom + band
    c.set_xticks(YEARS)
    c.set_xticklabels([f"{y}\nn={num(n, 'en')}" for y, n in zip(YEARS, estab["strict"])], fontsize=6.2)
    c.set_ylim(0, 100)
    c.set_xlabel(YEAR_AXIS)
    c.set_ylabel("% of the year's entries")
    # The key sits under the panel in three columns; matplotlib fills a column at a time, so the
    # reading order down each column is 0–4 / 5–9, then 10–14 / 15–19, then 20–29 / 30+.
    c.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=6.2, frameon=False,
             columnspacing=0.8, handlelength=1.1, title=AGE_AXIS, title_fontsize=6.2)
    titles[c] = c.set_title(TITLES["c"], loc="left", fontsize=9, fontweight="bold", pad=3.0)

    # (d) male-to-female ratio of entries by age and year --------------------------------------------
    d = axes[1, 1]
    x = np.arange(len(RATIO_AGES))
    for k, year in enumerate(YEARS):
        j = YEARS.index(year)
        ratio, lo, hi = mf_ratio(cell[("strict", "Males")][:len(RATIO_AGES), j],
                                 cell[("strict", "Females")][:len(RATIO_AGES), j])
        off = (k - (len(YEARS) - 1) / 2) * 0.12     # the five years are dodged inside their age group
        d.errorbar(x + off, ratio, yerr=[ratio - lo, hi - ratio], fmt="o-", color=YEAR_COLORS[year],
                   capsize=2, ms=4.5, lw=1.4, label=f"{year} (n={num(estab['strict'][j], 'en')})")
    d.axhline(3, color="#999999", ls=":", lw=1.1)
    d.text(len(RATIO_AGES) - 0.55, 3.05, "3:1", fontsize=6.3, color="#777777")
    d.axhline(1, color="#bbbbbb", ls="--", lw=1.0)
    d.set_xticks(x)
    d.set_xticklabels(RATIO_AGES, rotation=45, ha="right")
    # The band above 8 is kept clear on purpose: the key of five years would otherwise be printed over
    # the 2021 series and the tall interval of its last age group.
    d.set_ylim(0, 14)
    d.set_yticks([0, 2, 4, 6, 8])
    d.set_xlabel(AGE_AXIS)
    d.set_ylabel("M:F ratio of entries (95% CI)")
    lg = d.legend(loc="upper left", fontsize=6.2, title=ESTAB_LEGEND, title_fontsize=6.2, frameon=True,
                  framealpha=1.0, edgecolor="#cccccc", facecolor="white", borderpad=0.25)
    lg.set_zorder(6)
    lg.set_in_layout(False)         # a wide key must not be allowed to squeeze its own panel
    titles[d] = d.set_title(TITLES["d"], loc="left", fontsize=9, fontweight="bold", pad=3.0)

    # Panel heads last: the stored plate anchors each title to the left edge of ITS grid cell, not to
    # its axes, so the two columns of titles line up however wide the y-axis labels of a panel are.
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    fig.canvas.draw()
    for ax, title in titles.items():
        pos = ax.get_position()
        title.set_ha("left")
        # `set_title(loc="left")` hands back its own Text artist; the cell of a 2-column grid starts at
        # half the canvas, so the head of a right-hand panel is anchored 2 mm inside the midline.
        title.set_x((ax.get_subplotspec().colspan.start / 2 + CELL_MARGIN - pos.x0) / pos.width)
    return fig
