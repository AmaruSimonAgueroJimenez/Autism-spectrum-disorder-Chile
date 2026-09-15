"""Plate E14 — REM A05 entries by age and sex: counts, rates, sex ratio and the variant PDD family.

The stored plate was drawn by `study/pipeline/17_extended_material.py` from `outputs/tidy/
rem_a05_age_sex_annual.csv`, which is not in this repository. Its six panels are redrawn here from the
two published tables that carry the same series:

* `E14_rem_a05_age_sex.csv` — the 17 five-year WHO age groups x Males/Females x 2021–2025 as plain
  counts of the strict autism code (05990022), the four rate rows (crude and WHO-standardised, per
  sex, each as `rate (lower–upper)`) and the establishments reporting the code each year;
* `E70_rem_a05_age_sex_full.csv` — the same A05 flow by category, used for panel (f) only: the
  variant PDD family (05990022+05990023+05990025+05990026) by age in 2025, which E14 does not carry.

The estimators are the stored plate's own and are not recomputed from a denominator:

* panel (c) prints **both** rates as the table publishes them — the dashed line is the CRUDE rate per
  100,000 INE residents, the square marker the rate age-STANDARDISED to the WHO standard population,
  with the Fay–Feuer limits of the table as its error bar. Neither a population file nor a standard
  population is needed here, and the two estimators are never mixed;
* panel (d) is a ratio of RECORDS, not of rates: male count / female count, with the exact
  (Clopper–Pearson) limits of the male share of the age group's records carried over to the ratio —
  408/114 = 3.58 (2.90–4.44), the first point of the stored plate;
* panel (f) is counts, not rates, and the labelled difference is family minus strict.

Case definition: strict autism 05990022 for panels (a)–(e); panel (f) adds the variant PDD family of
E70. The corpus is English only, so this module is too.
"""
import re

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from scipy.stats import beta
from figstyle import *

PLATE = "E14_rem_a05_age_sex"
SOURCES = [
    "docs/study/corpus/tables/E14_rem_a05_age_sex.csv",
    "docs/study/corpus/tables/E70_rem_a05_age_sex_full.csv",
]
NOTE = ("Redraws the six panels of plate E14 — A05 autism entries by the 17 WHO age groups and sex on a "
        "log axis, the published crude and WHO-standardised rates per 100,000 residents, the exact "
        "male-to-female ratio of records, the age composition of 2021 and 2025, and the variant PDD "
        "family against strict autism by age in 2025 — from the E14 presentation table, with the PDD "
        "family counts of panel (f) read from its extended companion E70.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
YEARS = [2021, 2022, 2023, 2024, 2025]          # the A05 years of the stored plate
AGES = ["0–4", "5–9", "10–14", "15–19", "20–24", "25–29", "30–34", "35–39", "40–44", "45–49",
        "50–54", "55–59", "60–64", "65–69", "70–74", "75–79", "80+"]     # verbatim, WHO five-year groups
SEXES = ["Males", "Females"]                    # verbatim in the table's Series column
# Okabe-Ito, in the order the pipeline gives the five years (sky, blue, green, gold, orange).
YEAR_COLORS = [SKY, BLUE, GREEN, GOLD, ORANGE]
SEX_COLORS = {"Males": BLUE, "Females": ORANGE}
FIRST_LAST = {2021: SKY, 2025: ORANGE}          # panels (d) and (e) show the first and the last year
STRICT_COLOR, FAMILY_COLOR = BLUE, GREEN
COMPOSITION_MIN = 5.0                           # the stored plate labels the groups that reach 5 %
CTX = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.0)    # a label that crosses a bar
# The stored plate wraps its panel titles by measured width; the breaks below are the ones it prints.
TITLES = {
    "a": "Entries by age and year, males (strict\nautism)",
    "b": "Entries by age and year, females (strict\nautism)",
    "c": "Crude and WHO-standardised rates by sex",
    "d": "Male-to-female ratio of entries by age",
    "e": "Age composition of entries, 2021 and\n2025",
    "f": "Variant PDD family versus strict autism by\nage (2025)",
}

# --------------------------------------------------------------------------- reading the tables
# The presentation tables store every value as a formatted string: "3,538" is a count, "1,140 (995)" a
# count and the establishments reporting it, "202.7 (194.6–211.1)" a rate and its confidence limits.
_RATE = re.compile(r"^\s*(-?[\d.,]+)\s*\(\s*(-?[\d.,]+)\s*[–-]\s*(-?[\d.,]+)\s*\)")
_CELL = re.compile(r"^\s*(-?[\d.,]+)\s*(?:\(\s*(-?[\d.,]+)\s*\))?")


def _num(s):
    """One formatted number -> float; 'n/e' (not estimable) and blanks -> nan."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-"))


def _cell(s):
    """'1,140 (995)' -> (1140.0, 995.0); '3,538' -> (3538.0, nan); 'n/e' -> (nan, nan)."""
    m = _CELL.match(str(s))
    if not m:
        return float("nan"), float("nan")
    return _num(m.group(1)), (_num(m.group(2)) if m.group(2) else float("nan"))


def _rate(s):
    """'22.0 (20.9–23.1)' -> (22.0, 20.9, 23.1)."""
    m = _RATE.match(str(s))
    if not m:
        raise ValueError(f"not a rate with limits: {s!r}")
    return _num(m.group(1)), _num(m.group(2)), _num(m.group(3))


def _table(rel):
    """A tracked presentation table, read as text (they are written with a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str)


def counts_by_age_sex():
    """Strict-autism entries, {sex: 17 age groups x 5 years}, and the establishments of each year."""
    t = _table(SOURCES[0])
    label = t.columns[0]                        # 'Age group (years)' — it also labels the rate rows
    counts = {}
    for sex in SEXES:
        rows = t[(t["Series"] == sex)].set_index(label)
        counts[sex] = np.array([[_num(rows.loc[a, str(y)]) for y in YEARS] for a in AGES])
    estab = np.array([_num(v) for v in
                      t[t[label] == "Reporting establishments"].iloc[0][[str(y) for y in YEARS]]])
    return counts, estab


def published_rates():
    """The two rate rows of each sex: {(sex, kind): (value, lower, upper) x 5 years}."""
    t = _table(SOURCES[0])
    label = t.columns[0]
    out = {}
    for sex in SEXES:
        for kind in ("crude", "WHO-standardised"):
            hit = t[(t["Series"] == sex) & (t[label].str.endswith(kind))]
            if hit.empty:
                raise KeyError(f"no {kind} rate row for {sex}")
            out[(sex, kind)] = np.array([_rate(hit.iloc[0][str(y)]) for y in YEARS]).T
    return out


def family_2025(counts):
    """The variant PDD family by age in 2025 (both sexes), and the establishments reporting it."""
    t = _table(SOURCES[1])
    entries = t[t["Flow"] == "Entries"]
    fam = entries[entries["Category"] == "Variant PDD family (sum of codes)"]
    strict = entries[entries["Category"] == "Autism (single code)"]
    total, estab = np.zeros(len(AGES)), []
    for sex in SEXES:
        rows = fam[fam["Sex"] == sex].set_index("Age group")
        pairs = [_cell(rows.loc[a, "2025"]) for a in AGES]
        total += np.array([p[0] for p in pairs])
        estab += [p[1] for p in pairs]
        # E70 is the plate's own extended companion: its strict rows must be the E14 counts it redraws.
        srows = strict[strict["Sex"] == sex].set_index("Age group")
        same = np.array([[_cell(srows.loc[a, str(y)])[0] for y in YEARS] for a in AGES])
        assert np.allclose(same, counts[sex]), f"E70 and E14 disagree on the strict {sex.lower()} counts"
    assert len(set(estab)) == 1, "the PDD family rows of 2025 do not share one establishment count"
    return total, estab[0]


def exact_ratio(male, female):
    """Male-to-female ratio of records with exact 95 % limits (Clopper–Pearson on the male share).

    The limits are of the male share p of the age group's records; p/(1-p) carries them to the ratio.
    An age group with no record of either sex has no ratio, and the logarithmic axis cannot hold a
    ratio of zero, so those groups are left blank — as the stored plate and its caption say."""
    ratio = np.full(len(AGES), np.nan)
    lo = np.full(len(AGES), np.nan)
    hi = np.full(len(AGES), np.nan)
    for i, (m, f) in enumerate(zip(male, female)):
        n = m + f
        if m <= 0 or f <= 0:
            continue
        p_lo = beta.ppf(0.025, m, n - m + 1)
        p_hi = beta.ppf(0.975, m + 1, n - m)
        ratio[i], lo[i], hi[i] = m / f, p_lo / (1 - p_lo), p_hi / (1 - p_hi)
    return ratio, lo, hi


# --------------------------------------------------------------------------- panel furniture
def _age_axis(ax):
    ax.set_xticks(range(len(AGES)))
    ax.set_xticklabels(AGES, rotation=90)
    ax.set_xlim(-0.65, len(AGES) - 0.35)
    ax.set_xlabel("Age group (years)")


def _open_marker(colour):
    """The crude series of panel (c): a dashed line with a ringed marker, as the stored plate draws it."""
    return dict(color=colour, mec=colour, mfc=(*to_rgb(colour), 0.45), mew=1.1)


def draw():
    style()
    plt.rcParams.update({
        "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlepad": 4.0, "axes.titlelocation": "left",
        "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
        "legend.edgecolor": "none", "legend.borderpad": 0.25, "legend.handlelength": 1.4,
        "legend.handletextpad": 0.5, "legend.columnspacing": 1.0, "legend.labelspacing": 0.35,
        "legend.borderaxespad": 0.3, "legend.fontsize": 7, "legend.title_fontsize": 7,
        "grid.alpha": 0.32, "grid.linewidth": 0.5,
    })
    counts, estab = counts_by_age_sex()
    rates = published_rates()
    family, family_n = family_2025(counts)
    both = counts["Males"] + counts["Females"]
    x = np.arange(len(AGES))

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055)
    ax = axes.ravel()

    # (a), (b) entries by age and year, one panel per sex --------------------------------------------
    for a, sex in zip(ax[:2], SEXES):
        series = counts[sex]
        for j, year in enumerate(YEARS):
            v = series[:, j].astype(float)
            v[v <= 0] = np.nan          # the log axis cannot hold a zero: the group is left blank
            a.plot(x, v, marker="o", ms=4.5, lw=1.7, color=YEAR_COLORS[j],
                   label=f"{year} (n={num(estab[j], 'en')})")
        a.set_yscale("log")             # powers of ten, as the stored plate labels them
        a.set_ylim(0.7, float(np.nanmax(series)) * 40)
        _age_axis(a)
        a.set_ylabel("Entries (annual flow) (log scale)")
        a.legend(loc="upper right", title="n = reporting establishments")
        clean(a, "both")

    # (c) crude and WHO-standardised rates, both estimators on one axis ------------------------------
    ymax = max(rates[(s, "WHO-standardised")][0].max() for s in SEXES) * 1.20
    for sex in SEXES:
        colour = SEX_COLORS[sex]
        crude = rates[(sex, "crude")]
        ax[2].plot(YEARS, crude[0], ls="--", lw=1.8, marker="o", ms=4.5, label=f"{sex} — crude",
                   **_open_marker(colour))
    for sex in SEXES:
        colour = SEX_COLORS[sex]
        std = rates[(sex, "WHO-standardised")]
        # The Fay–Feuer limits of the table; they are narrower than the marker in most years.
        label = "Females — WHO-\nstandardised" if sex == "Females" else f"{sex} — WHO-standardised"
        ax[2].errorbar(YEARS, std[0], yerr=[std[0] - std[1], std[2] - std[0]], fmt="s", ms=7.5,
                       color=colour, ls="none", elinewidth=0.9, capsize=0, zorder=4, label=label)
        others = [rates[(s, k)][0] for s in SEXES for k in ("crude", "WHO-standardised")
                  if not (s == sex and k == "WHO-standardised")]
        for i, year in enumerate(YEARS):
            v = std[0][i]
            # A label sits above its square unless another series of the year sits just above it —
            # the 2021 female square, whose place is taken by the male crude marker at 16.7.
            clash = any(0 < o[i] - v < 0.08 * ymax for o in others)
            ax[2].annotate(num(v, "en", 1), (year, v), textcoords="offset points",
                           xytext=(6, 9) if clash else (0, 7), ha="left" if clash else "center",
                           va="bottom", fontsize=7.5, color=colour, zorder=6)
    year_ticks(ax[2], YEARS)
    ax[2].set_xlim(2020.72, 2025.38)
    ax[2].set_ylim(0, ymax)
    ax[2].set_xlabel("Year")
    ax[2].set_ylabel("Entries per 100,000 residents")
    # Four entries in two columns, as the stored plate arranges them, kept compact enough to clear the
    # last square: matplotlib fills a column at a time, so the crude pair is the first column.
    ax[2].legend(loc="upper left", ncol=2, fontsize=6.6, labelspacing=0.28, columnspacing=0.8,
                 handlelength=1.2, handletextpad=0.4, borderpad=0.2)
    clean(ax[2], "both")

    # (d) male-to-female ratio of records, exact limits ----------------------------------------------
    for year, colour in FIRST_LAST.items():
        j = YEARS.index(year)
        ratio, lo, hi = exact_ratio(counts["Males"][:, j], counts["Females"][:, j])
        off = -0.16 if year == YEARS[0] else 0.16
        ax[3].errorbar(x + off, ratio, yerr=[ratio - lo, hi - ratio], fmt="o", ms=5.0, color=colour,
                       ls="none", elinewidth=1.1, capsize=1.8, label=str(year))
    ax[3].axhline(1.0, color=GREY, ls=":", lw=1.1, zorder=1)
    ax[3].set_yscale("log")
    _age_axis(ax[3])
    ax[3].set_ylabel("M:F ratio (exact 95% CI) (log\nscale)")
    ax[3].legend(loc="upper left")
    clean(ax[3], "both")

    # (e) age composition of the first and the last year ---------------------------------------------
    w, off = 0.32, 0.215
    shares = {}
    for year, colour in FIRST_LAST.items():
        j = YEARS.index(year)
        share = both[:, j] / both[:, j].sum() * 100
        shares[year] = share
        ax[4].bar(x + (-off if year == YEARS[0] else off), share, width=w, color=colour, label=str(year))
    ymax_e = max(s.max() for s in shares.values()) * 1.22
    for year in FIRST_LAST:
        share = shares[year]
        for i, v in enumerate(share):
            if v < COMPOSITION_MIN:     # the tail is left to the numeric companion: the boxes do not fit
                continue
            ax[4].annotate(num(v, "en", 1), (x[i] + (-off if year == YEARS[0] else off), v),
                           textcoords="offset points", xytext=(0, 3), ha="center", va="bottom",
                           rotation=90, fontsize=6.8)
    assert all(abs(s.sum() - 100) < 1e-9 for s in shares.values()), "the composition does not add to 100"
    _age_axis(ax[4])
    ax[4].set_ylim(0, ymax_e)
    ax[4].set_ylabel("% of the year's entries")
    ax[4].legend(loc="upper right")
    clean(ax[4], "y")

    # (f) the variant PDD family against strict autism, last year ------------------------------------
    strict = both[:, YEARS.index(2025)]
    ymax_f = float(np.ceil(family.max() * 1.25 / 1000) * 1000)
    ax[5].bar(x - off, strict, width=w, color=STRICT_COLOR,
              label=f"Strict autism (n={num(estab[-1], 'en')})")
    ax[5].bar(x + off, family, width=w, color=FAMILY_COLOR,
              label=f"PDD family (variant)\n(n={num(family_n, 'en')})")
    # The difference is the contribution of the remaining categories of the group. It is written just
    # above the family bar; in the tail, where the bars are short, two long labels of neighbouring
    # groups would sit on one another — a label as wide as the group spacing (three characters or
    # more) is lifted clear of its left neighbour, which is how the stored plate staggers +29, +19
    # and +11 above +55, +17 and +13 and leaves the two-character labels of the last groups in line.
    prev_y, prev_wide = None, False
    for i, (s, f) in enumerate(zip(strict, family)):
        text = f"+{num(f - s, 'en')}"
        wide = len(text) >= 3
        y = f + 0.015 * ymax_f
        if wide and prev_wide and abs(y - prev_y) < 0.012 * ymax_f:
            y = prev_y + 0.055 * ymax_f
        ax[5].annotate(text, (x[i] + off, y), textcoords="offset points", xytext=(0, 1), ha="center",
                       va="bottom", fontsize=7.4, color=FAMILY_COLOR, bbox=CTX, zorder=5)
        prev_y, prev_wide = y, wide
    _age_axis(ax[5])
    ax[5].set_ylim(0, ymax_f)
    ax[5].set_ylabel("Entries (annual flow)")
    ax[5].yaxis.set_major_formatter(thousands("en"))
    ax[5].legend(loc="upper right")
    clean(ax[5], "y")

    # Panel letters last: the layout is resolved and frozen first, so each letter keeps its corner.
    # `set_title(loc='left')` writes its own Text artist, which it hands back: the letters are placed
    # against that artist, not against the (empty) centred title of the axes.
    titles = {key: a.set_title(TITLES[key], loc="left", fontsize=9, fontweight="bold",
                               linespacing=1.15) for a, key in zip(ax, "abcdef")}
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    r = fig.canvas.get_renderer()
    for a, key in zip(ax, "abcdef"):
        t = titles[key]
        # The stored plate starts the title of a right-hand panel a little left of its axes, which is
        # what lets the longest one (panel f) end inside the canvas; the same nudge is applied here,
        # and only where the title would otherwise run off the page.
        over = t.get_window_extent(r).x1 - (fig.bbox.width - 2)
        if over > 0:
            t.set_x(t.get_position()[0] - over / a.get_window_extent().width)
        # The letter sits beside the first line of the title, as it does in the stored plate.
        bb = t.get_window_extent(r).transformed(fig.transFigure.inverted())
        lines = TITLES[key].count("\n") + 1
        letter(fig, a, f"({key})", dy=bb.y1 - bb.height / lines - a.get_position().y1)
    return fig
