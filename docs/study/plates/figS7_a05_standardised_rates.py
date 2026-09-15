"""Plate S7 — REM A05 entries per 100,000 population: crude and WHO age-standardised rates.

The stored plate was drawn by `study/pipeline/08b_figures_rem.py` from `outputs/tidy/
rem_a05_age_sex_annual.csv` and the INE projection grid, neither of which is in this repository. Both
survive in published tables, so the whole plate is rebuilt here from the numerator and the denominator
rather than from the finished rates:

* `ST13_a05_age_sex.csv` — THE NUMERATOR. The 17 five-year WHO age groups x Males/Females x 2019–2025
  for the three blocks the plate draws: broad PDD 2019–2020 (06902600), the variant's PDD family
  2021–2025 (05990022+05990023+05990025+05990026) and strict autism 2021–2025 (05990022). A year
  outside a block's era is stored 'n/e' and is an ABSENT row, never a zero;
* `output_files/consolidacion/population_regional.csv` — THE DENOMINATOR for 2019–2024: the INE
  base-2017 projection by region, sex and age group, summed over the sixteen regions to the national
  grid (its national totals are the 'INE population' column of S7 to the unit);
* `E20_population_structure.csv` — the denominator for 2025, which the regional file does not reach:
  its 17 age rows carry Males and Females for 2019 and 2025, and its 2019 half reproduces the regional
  file cell for cell, which is what licenses using its 2025 half for the same grid;
* `S7_a05_standardised_rates.csv` — the plate's own numeric companion, read for the reporting
  establishments printed under every year (449 / 658 / 920 / 1,070 / 952 for strict autism, 710 / 869 /
  1,040 / 1,153 / 995 for the family, 651 / 492 for broad PDD) and used by `_check_published()` as the
  test of the reconstruction: all 36 of its rows — entries, population, crude rate with limits and
  standardised rate with limits — must come back out of the rebuild as the strings it prints.

Do NOT take the denominator from the regional INE rows of `E73_denominator_layers_full.csv`: they are
exactly twice the correct value and would halve every rate on this plate.

THE ESTIMATORS, all four of them, and they must not be mixed:

* CRUDE rate = 100,000 x entries / INE residents, with exact (chi-square) Poisson limits. Drawn dotted
  with a round marker in (a), (b) and (f);
* WHO-STANDARDISED rate = direct standardisation to the WHO world standard population (Ahmad et al.
  2001, collapsed at 80+, weights renormalised over the groups that have a denominator), with the
  gamma limits of Fay and Feuer (1997). Drawn solid with a square marker in (a), (b) and (f);
* panel (c) is the male:female ratio of the two STANDARDISED rates with the log-normal interval,
  ratio x exp(+/- z sqrt(var_m/asr_m^2 + var_f/asr_f^2)). Its variance is the one quantity of the plate
  that the S7 table does not publish, which is why the rebuild goes through the age grid: the ASR and
  its variance come back at 21.957552 / 0.2984090 for strict-autism 2021 males, identical to the stored
  `rem_rates_national.csv` to the last digit it keeps, and that file stops at 2024 while the plate does
  not. It is a ratio of RATES and is never the ratio of entries of plate S8 panel (d);
* panels (d) and (e) are AGE-SPECIFIC CRUDE rates with exact Poisson limits — not standardised.

The numerator is A05 mental-health programme entries summed over the age x sex cells COL04–COL37: an
annual flow located by place of care in the public network, against a denominator of all INE residents
by residence, insured or not. The ratio is administrative recognition per population, never incidence
and never prevalence. Broad PDD 2019–2020 is a DIFFERENT case definition: it keeps its own panel (f)
and stays behind the break marker in (c).

Two features of the stored plate that no table records and that were measured off the image itself.
The y-axis of every rate panel is a fixed multiple of the tallest upper limit that panel draws — 3.4x
in (a) and (b), 2.6x in (f), 1.9x in (d) and 9x in (e) — which reserves the band above the ink for the
key and is why the ink of (a) sits in the bottom quarter of a 0–418 axis. And the six-entry keys are
one column, not two: those of (a) and (b) sit at the middle right, (f) keeps its own at the upper
left, while the four- and five-entry keys of (d) and (e) do run in two columns at the upper right.
The stored plate is the authority on both, so both are drawn as it prints them.

The corpus is English only, so this module is too.
"""
import re

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from figstyle import *

PLATE = "figS7_a05_standardised_rates"
SOURCES = [
    "docs/study/corpus/tables/ST13_a05_age_sex.csv",
    "output_files/consolidacion/population_regional.csv",
    "docs/study/corpus/tables/E20_population_structure.csv",
    "docs/study/corpus/tables/S7_a05_standardised_rates.csv",
]
COUNTS, POP_REGIONAL, POP_2025, PUBLISHED = SOURCES
NOTE = ("Redraws the six panels of plate S7 — crude and WHO-standardised A05 entry rates by sex for "
        "strict autism and for the variant's PDD family, the male:female ratio of the standardised "
        "rates with its log-normal interval, the age- and sex-specific rates of 2021 and 2025, the "
        "age curves of every year on a log axis and the broad PDD 2019–2020 sensitivity — by "
        "rebuilding them from the published age x sex entry counts of ST13 over the INE population "
        "grid, and checking every rate against the plate's own S7 companion table.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
CELL_MARGIN = 2.0 / 180.0                       # panel titles hang 2 mm inside their grid cell

# WHO World Standard Population (Ahmad et al. 2001, GPE Discussion Paper 31), collapsed to an open 80+
# group. The published weights add to 100,030 per 100,000 because of rounding and are renormalised.
WHO_STANDARD = {
    "0–4": 8860, "5–9": 8690, "10–14": 8600, "15–19": 8470, "20–24": 8220, "25–29": 7930,
    "30–34": 7610, "35–39": 7150, "40–44": 6590, "45–49": 6040, "50–54": 5370, "55–59": 4550,
    "60–64": 3720, "65–69": 2960, "70–74": 2210, "75–79": 1520, "80+": 1545,
}
AGES = list(WHO_STANDARD)                       # the 17 groups, verbatim as ST13 prints them
YOUNG = AGES[:8]                                # 0–4 to 35–39: the age axis of panels (d) and (e)
SEXES = ["Males", "Females", "Both sexes"]      # verbatim in the tables' Sex column
# The three blocks of ST13, matched on their opening words, with the Series label S7 gives each one.
BLOCKS = {"strict autism": "Strict autism", "PDD family": "PDD family", "broad PDD": "Broad PDD"}
ERA = {"strict autism": [2021, 2022, 2023, 2024, 2025],     # the years each definition is in era for
       "PDD family": [2021, 2022, 2023, 2024, 2025], "broad PDD": [2019, 2020]}
YEARS = [2021, 2022, 2023, 2024, 2025]

PER = 100_000.0
Z = 1.959964                                    # the two-sided 95 % normal quantile of the pipeline
ALPHA = 0.05
DARK = "#333333"
GREY = "#8c8c8c"
SEX_COLOR = {"Males": BLUE, "Females": ORANGE, "Both sexes": DARK}
# Okabe-Ito, in the order the pipeline gives the five years (sky, blue, green, gold, orange).
YEAR_COLOR = {2021: SKY, 2022: BLUE, 2023: GREEN, 2024: GOLD, 2025: ORANGE}
DISRUPTION = (2020, 2021)                       # the reporting-disruption years the plate shades
# Law 21.545 was published on 10 March 2023; the plate marks it a little before the 2023 tick and it is
# CONTEXT, never an intervention: no estimate on this plate depends on it.
LAW_X = 2023 - 0.35

RATE_AXIS = "Entries per 100,000 population (INE base 2017)"
RATE_AXIS_LOG = "Entries per 100,000 pop. (INE 2017; log scale)"
RATIO_AXIS = "M:F ratio of standardised rates (95% CI)"
AGE_AXIS = "Age group (years)"
YEAR_AXIS = "Year · n = reporting establishments"
ESTAB_LEGEND = "n = reporting establishments"
CRUDE, ASR = "crude", "standardised (WHO)"
# The stored plate wraps its panel titles by measured width; the break below is the one it prints.
TITLES = {
    "a": "Strict autism (05990022): rates by sex",
    "b": "Variant PDD family: rates by sex",
    "c": "Male:female ratio of standardised rates",
    "d": "Strict autism by age and sex, 2021 and\n2025",
    "e": "Strict autism by age, both sexes, by year",
    "f": "Broad PDD 2019–2020 (different definition)",
}


# --------------------------------------------------------------------------- reading the tables
def _num(s):
    """The leading number of a formatted cell -> float; 'n/e' and a blank -> nan.

    'n/e' is not estimable: the block has no row for that year because the year is outside its
    definition era. It is an ABSENT cell and must never be read as a zero."""
    s = str(s).strip()
    if not s or s.lower() in {"n/e", "nan", "—", "-"}:
        return float("nan")
    m = re.match(r"^\(?\s*(-?[\d.,]+)", s)
    if not m:
        return float("nan")
    return float(m.group(1).replace(",", "").replace("−", "-"))


def _table(rel):
    """A tracked presentation table, read as text (they are written with a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", dtype=str)


def population():
    """The national INE denominator grid: {(year, sex): the 17 age groups}, Males and Females.

    2019–2024 come from the regional projection summed over the sixteen regions; 2025 from the
    population-structure table, whose 2019 half is asserted against the regional file first — that
    identity is the only warrant for splicing the two files into one grid."""
    reg = pd.read_csv(ROOT / POP_REGIONAL)
    reg = reg.groupby(["year", "sex", "age_group"], as_index=False).population.sum()
    reg["sex"] = reg.sex.map({"HOMBRE": "Males", "MUJER": "Females"})
    reg["age_group"] = reg.age_group.str.replace("-", "–", regex=False)
    grid = {(int(y), s): np.array([float(g.set_index("age_group").population.get(a, np.nan)) for a in AGES])
            for (y, s), g in reg.groupby(["year", "sex"])}

    t = _table(POP_2025).set_index("Age group")
    for year in (2019, 2025):
        for sex in ("Males", "Females"):
            col = np.array([_num(t.loc[a, f"{year} · {sex}"]) for a in AGES])
            if year == 2019:
                assert np.allclose(col, grid[(2019, sex)]), \
                    f"E20 and the regional projection disagree on the {year} {sex} age grid"
            else:
                grid[(year, sex)] = col
    for key, col in grid.items():
        assert np.isfinite(col).all(), f"the INE grid has a hole in {key}"
    return grid


def counts():
    """The A05 numerator: {(series, sex, year): the 17 age groups} of entries, in-era years only."""
    t = _table(COUNTS)
    label = t.columns[2]                        # 'Age group (years)' — it also labels the summary rows
    out = {}
    for series, opening in BLOCKS.items():
        block = t[t["Block"].str.startswith(opening)]
        assert not block.empty, f"ST13 carries no {opening} block"
        for sex in ("Males", "Females"):
            rows = block[block.Sex == sex].set_index(label)
            for year in ERA[series]:
                col = np.array([_num(rows.loc[a, str(year)]) for a in AGES])
                assert np.isfinite(col).all(), f"ST13 leaves {series} {sex} {year} partly 'n/e'"
                out[(series, sex, year)] = col
    return out


def establishments():
    """{(series, year): reporting establishments} from the plate's own companion table."""
    t = _table(PUBLISHED)
    col = [c for c in t.columns if c.startswith("Reporting establishments")][0]
    return {(row["Series"], int(row["Year"])): _num(row[col]) for _i, row in t.iterrows()}


# --------------------------------------------------------------------------- the four estimators
def poisson_limits(count):
    """Exact (chi-square) limits of a Poisson count; vectorised, and 0 has a lower limit of 0."""
    count = np.asarray(count, dtype=float)
    lo = np.where(count > 0, stats.chi2.ppf(ALPHA / 2, 2 * np.maximum(count, 1e-12)) / 2, 0.0)
    hi = stats.chi2.ppf(1 - ALPHA / 2, 2 * count + 2) / 2
    return lo, hi


def crude_rate(count, pop):
    """Crude rate per 100,000 with its exact Poisson limits."""
    count, pop = np.asarray(count, dtype=float), np.asarray(pop, dtype=float)
    lo, hi = poisson_limits(count)
    return PER * count / pop, PER * lo / pop, PER * hi / pop


def standardise(count, pop):
    """Direct standardisation to the WHO world standard with the gamma limits of Fay and Feuer (1997).

    Groups with no denominator are dropped and the remaining standard weights renormalised, so the
    weights always add to one over the groups that actually contribute."""
    count, pop = np.asarray(count, dtype=float), np.asarray(pop, dtype=float)
    keep = pop > 0
    w = np.array([WHO_STANDARD[a] for a in AGES], dtype=float)[keep]
    w = w / w.sum()
    rates = count[keep] / pop[keep]
    asr = float(np.sum(w * rates))
    var = float(np.sum(w ** 2 * count[keep] / pop[keep] ** 2))
    w_max = float(np.max(w / pop[keep]))
    if asr > 0 and var > 0:
        lo = stats.gamma.ppf(ALPHA / 2, a=asr ** 2 / var, scale=var / asr)
        shape = (asr + w_max) ** 2 / (var + w_max ** 2)
        hi = stats.gamma.ppf(1 - ALPHA / 2, a=shape, scale=(var + w_max ** 2) / (asr + w_max))
    else:
        lo, hi = 0.0, (stats.gamma.ppf(1 - ALPHA / 2, a=1.0, scale=w_max) if w_max > 0 else np.nan)
    return PER * asr, PER * lo, PER * hi, PER ** 2 * var


def rates(cells, grid, estab):
    """One row per series x year x sex: entries, population, crude and standardised rates, variance."""
    rows = []
    for series, years in ERA.items():
        for year in years:
            for sex in SEXES:
                if sex == "Both sexes":
                    count = cells[(series, "Males", year)] + cells[(series, "Females", year)]
                    pop = grid[(year, "Males")] + grid[(year, "Females")]
                else:
                    count, pop = cells[(series, sex, year)], grid[(year, sex)]
                crude, crude_lo, crude_hi = crude_rate(count.sum(), pop.sum())
                asr, asr_lo, asr_hi, asr_var = standardise(count, pop)
                rows.append(dict(series=series, year=year, sex=sex, entries=count.sum(),
                                 population=pop.sum(), crude=crude, crude_lo=crude_lo,
                                 crude_hi=crude_hi, asr=asr, asr_lo=asr_lo, asr_hi=asr_hi,
                                 asr_var=asr_var, establishments=estab[(series, year)]))
    return pd.DataFrame(rows)


def age_rates(cells, grid, series, year, sex, groups=YOUNG):
    """Age-specific CRUDE rates with exact Poisson limits — panels (d) and (e), never standardised."""
    if sex == "Both sexes":
        count = cells[(series, "Males", year)] + cells[(series, "Females", year)]
        pop = grid[(year, "Males")] + grid[(year, "Females")]
    else:
        count, pop = cells[(series, sex, year)], grid[(year, sex)]
    take = [AGES.index(a) for a in groups]
    rate, lo, hi = crude_rate(count[take], pop[take])
    return pd.DataFrame({"age_group": groups, "count": count[take], "rate": rate,
                         "rate_lo": lo, "rate_hi": hi})


def mf_ratio(r):
    """Panel (c): male:female ratio of the standardised rates with its log-normal 95 % interval."""
    m = r[r.sex == "Males"].set_index("year").sort_index()
    f = r[r.sex == "Females"].set_index("year").sort_index()
    ratio = m.asr / f.asr
    se = np.sqrt(m.asr_var / m.asr ** 2 + f.asr_var / f.asr ** 2)
    return ratio.index.to_numpy(), ratio.to_numpy(), (ratio * np.exp(-Z * se)).to_numpy(), \
        (ratio * np.exp(Z * se)).to_numpy()


def _check_published(r):
    """Every rate of the rebuild against the plate's own companion table, as the strings it prints."""
    t = _table(PUBLISHED)
    crude_col = [c for c in t.columns if c.startswith("Crude rate")][0]
    asr_col = [c for c in t.columns if c.startswith("WHO-standardised")][0]
    entry_col = [c for c in t.columns if c.startswith("Entries")][0]
    seen = 0
    for _i, row in t.iterrows():
        mine = r[(r.series == row["Series"]) & (r.year == int(row["Year"])) & (r.sex == row["Sex"])]
        assert len(mine) == 1, f"the rebuild has {len(mine)} rows for {row['Series']} {row['Year']}"
        mine = mine.iloc[0]
        got = {entry_col: f"{mine.entries:,.0f}", "INE population": f"{mine.population:,.0f}",
               crude_col: f"{mine.crude:.1f} ({mine.crude_lo:.1f} to {mine.crude_hi:.1f})",
               asr_col: f"{mine.asr:.1f} ({mine.asr_lo:.1f} to {mine.asr_hi:.1f})"}
        for col, value in got.items():
            assert value == row[col].strip(), \
                f"S7 {row['Series']} {row['Year']} {row['Sex']} {col}: {value} vs {row[col]}"
        seen += 1
    assert seen == 36, f"S7 should hold 36 rows, not {seen}"


# --------------------------------------------------------------------------- panel furniture
def _context(ax, law=True, shade=DISRUPTION, pandemic_pos=0.97, law_pos=0.97, pandemic_text=True,
             law_text=True, fs=7.0):
    """Shade the disruption years that are visible and mark Law 21.545 — context, not intervention."""
    lo, hi = ax.get_xlim()
    yrs = [y for y in shade if lo < y < hi]
    for y in yrs:
        ax.axvspan(y - 0.5, y + 0.5, color="grey", alpha=0.12, zorder=0)
    if yrs and pandemic_text:
        txt = "Reporting\ndisruption 2020–21" if len(yrs) == 2 else f"Reporting\ndisruption {yrs[0]}"
        ax.text(float(np.mean(yrs)), pandemic_pos, txt, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=fs, color="#555555", linespacing=1.15)
    if law and lo < LAW_X < hi:
        ax.axvline(LAW_X, color="#444444", ls=":", lw=1.2, zorder=1)
        if law_text:
            ax.text(LAW_X + 0.06, law_pos, "Law 21.545\n(context)", transform=ax.get_xaxis_transform(),
                    ha="left", va="top", fontsize=fs, color="#444444", linespacing=1.15)


def _legend(ax, loc, **kw):
    """The plate's key: 6 pt body in an OPAQUE white box, so no context line prints through its text."""
    lg = ax.legend(loc=loc, fontsize=6.0, frameon=True, framealpha=1.0, edgecolor="#cccccc",
                   facecolor="white", borderpad=0.25, **kw)
    lg.set_zorder(6)
    lg.set_in_layout(False)         # a wide key must not be allowed to squeeze its own panel
    return lg


def _head(ax, letter_):
    return ax.set_title(f"({letter_}) {TITLES[letter_]}", loc="left", fontsize=9.0,
                        fontweight="bold", pad=3.0, linespacing=1.15)


def _rates_panel(ax, r, letter_, law=True, headroom=3.4):
    """(a), (b): the crude and the standardised rate of each sex, with the standardised band."""
    for sex in SEXES:
        s = r[r.sex == sex].sort_values("year")
        ax.plot(s.year, s.crude, "o:", color=SEX_COLOR[sex], lw=1.1, ms=3.0, label=f"{sex} · {CRUDE}")
        ax.plot(s.year, s.asr, "s-", color=SEX_COLOR[sex], lw=1.5, ms=3.4, label=f"{sex} · {ASR}")
        ax.fill_between(s.year, s.asr_lo, s.asr_hi, color=SEX_COLOR[sex], alpha=0.13)
    tot = r[r.sex == "Both sexes"].sort_values("year")
    yrs = tot.year.tolist()
    ax.set_xticks(yrs)
    ax.set_xticklabels([f"{y}\n{num(n, 'en')}" for y, n in zip(yrs, tot.establishments)], fontsize=6.2)
    # The band above the ink is reserved for the six-entry key, as in the stored plate.
    ax.set_xlim(min(yrs) - 0.5, max(yrs) + 0.5)
    ax.set_ylim(0, r.asr_hi.max() * headroom)
    ax.yaxis.set_major_formatter(thousands("en"))
    _context(ax, law=law, pandemic_pos=0.985, law_pos=0.90, fs=6.0)
    ax.set_xlabel(YEAR_AXIS)
    ax.set_ylabel(RATE_AXIS, fontsize=6.0)
    _legend(ax, loc="center right", ncol=1, columnspacing=0.7, handlelength=1.2)
    return _head(ax, letter_)


def draw():
    """Draw the six panels of plate S7 and hand back the figure."""
    cells, grid = counts(), population()
    r = rates(cells, grid, establishments())
    _check_published(r)

    style()
    plt.rcParams.update({
        # seaborn's white grid, as the pipeline's shared `style()` sets it: grid on both axes, no tick
        # marks at all, only their labels, and no top or right spine.
        "axes.facecolor": "white", "axes.edgecolor": DARK, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": "#cccccc", "grid.alpha": 0.35, "grid.linewidth": 0.45, "grid.linestyle": "-",
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.bottom": False, "ytick.left": False,
        # the plate's own body: 8 pt base, 9 pt bold panel head, 7 pt ticks, 6 pt floor
        "font.size": 8.0, "axes.titlesize": 9.0, "axes.titleweight": "bold", "axes.labelsize": 8.0,
        "xtick.labelsize": 7.0, "ytick.labelsize": 7.0, "legend.fontsize": 7.0,
        "legend.title_fontsize": 7.0, "axes.linewidth": 0.7, "lines.linewidth": 1.3,
        "lines.markersize": 3.4, "patch.linewidth": 0.6, "axes.labelpad": 2.0, "axes.titlepad": 3.0,
        "xtick.major.pad": 1.5, "ytick.major.pad": 1.5, "legend.handlelength": 1.5,
        "legend.handletextpad": 0.5, "legend.labelspacing": 0.30, "legend.columnspacing": 0.9,
        "legend.borderpad": 0.3,
    })

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    titles = {}

    # (a), (b) the two in-era definitions, each with its own three sexes -----------------------------
    titles[axes[0, 0]] = _rates_panel(axes[0, 0], r[r.series == "strict autism"], "a")
    titles[axes[0, 1]] = _rates_panel(axes[0, 1], r[r.series == "PDD family"], "b")

    # (c) male:female ratio of the standardised rates ------------------------------------------------
    c = axes[1, 0]
    for series, colour, marker, label in (("strict autism", BLUE, "o", "Strict autism"),
                                          ("PDD family", GREEN, "s", "PDD family"),
                                          ("broad PDD", GREY, "^", "Broad PDD 2019–20")):
        broad = series == "broad PDD"
        year, ratio, lo, hi = mf_ratio(r[r.series == series])
        c.errorbar(year, ratio, yerr=[ratio - lo, hi - ratio], fmt=marker + (":" if broad else "-"),
                   color=colour, capsize=1.6, ms=3.4, lw=1.0 if broad else 1.4, label=label)
    c.axhline(3, color="#999999", ls=":", lw=1.0)
    c.text(2025.75, 3.05, "3:1", fontsize=6.0, color="#777777", va="bottom", ha="right")
    c.axhline(4, color="#bbbbbb", ls=":", lw=1.0)
    c.text(2025.75, 4.05, "4:1", fontsize=6.0, color="#999999", va="bottom", ha="right")
    c.set_xticks(list(range(2019, 2026)))
    c.set_xlim(2018.4, 2025.9)
    c.set_ylim(0, 8.4)
    # The break marker says what the shading cannot: 2019–20 is a different case definition, and no
    # line of this panel crosses it.
    c.axvline(2020.5, color="#999999", ls="-.", lw=1.0, zorder=1)
    c.text(2020.5, 0.86, "definition\nbreak", transform=c.get_xaxis_transform(), ha="center",
           va="center", fontsize=6.5, color="#777777",
           bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    _context(c, pandemic_text=False, law_text=False, fs=6.0)
    c.set_xlabel("Year")
    c.set_ylabel(RATIO_AXIS, fontsize=7.0)
    _legend(c, loc="lower right")
    titles[c] = _head(c, "c")

    # (d) age- and sex-specific rates, first year against last ---------------------------------------
    d = axes[1, 1]
    x = np.arange(len(YOUNG))
    d_hi = 0.0
    for year, ls, marker, off in ((2021, ":", "o", -0.1), (2025, "-", "s", 0.1)):
        for sex in ("Males", "Females"):
            s = age_rates(cells, grid, "strict autism", year, sex)
            d.errorbar(x + off, s.rate, yerr=[s.rate - s.rate_lo, s.rate_hi - s.rate], fmt=marker,
                       ls=ls, color=SEX_COLOR[sex], capsize=1.6, ms=3.2, lw=1.3,
                       label=f"{sex} {year}")
            d_hi = max(d_hi, float(s.rate_hi.max()))
    d.set_xticks(x)
    d.set_xticklabels(YOUNG, rotation=45, ha="right", fontsize=6.2)
    d.set_ylim(0, d_hi * 1.9)                   # the upper band is reserved for the key
    d.yaxis.set_major_formatter(thousands("en"))
    d.set_xlabel(AGE_AXIS)
    d.set_ylabel(RATE_AXIS, fontsize=7.0)
    _legend(d, loc="upper right", ncol=2, columnspacing=0.7)
    titles[d] = _head(d, "d")

    # (e) the age curve of every year, both sexes, on a log axis --------------------------------------
    e = axes[2, 0]
    e_hi = 0.0
    for year in YEARS:
        s = age_rates(cells, grid, "strict autism", year, "Both sexes")
        n = r[(r.series == "strict autism") & (r.year == year) & (r.sex == "Both sexes")]
        e.plot(x, s.rate.replace(0, np.nan), "o-", color=YEAR_COLOR[year], lw=1.4, ms=3.2,
               label=f"{year} (n={num(n.establishments.iloc[0], 'en')})")
        e.fill_between(x, s.rate_lo.replace(0, np.nan), s.rate_hi, color=YEAR_COLOR[year], alpha=0.10)
        e_hi = max(e_hi, float(s.rate_hi.max()))
    e.set_yscale("log")
    e.set_xticks(x)
    e.set_xticklabels(YOUNG, rotation=45, ha="right", fontsize=6.2)
    e.set_ylim(top=e_hi * 9.0)                  # only the top is set: the floor stays where the data put it
    e.set_xlabel(AGE_AXIS)
    e.set_ylabel(RATE_AXIS_LOG, fontsize=7.0)
    _legend(e, loc="upper right", title=ESTAB_LEGEND, title_fontsize=6.0, ncol=2, columnspacing=0.7)
    titles[e] = _head(e, "e")

    # (f) the broad PDD sensitivity: a different definition, in its own panel -------------------------
    f = axes[2, 1]
    rb = r[r.series == "broad PDD"]
    for sex in SEXES:
        s = rb[rb.sex == sex].sort_values("year")
        f.errorbar(s.year - 0.05, s.crude, yerr=[s.crude - s.crude_lo, s.crude_hi - s.crude], fmt="o",
                   ls=":", color=SEX_COLOR[sex], capsize=1.6, ms=3.2, lw=1.1, label=f"{sex} · {CRUDE}")
        f.errorbar(s.year + 0.05, s.asr, yerr=[s.asr - s.asr_lo, s.asr_hi - s.asr], fmt="s", ls="-",
                   color=SEX_COLOR[sex], capsize=1.6, ms=3.2, lw=1.5, label=f"{sex} · {ASR}")
    tot = rb[rb.sex == "Both sexes"].sort_values("year")
    f.set_xticks(tot.year.tolist())
    f.set_xticklabels([f"{y}\n{num(n, 'en')}" for y, n in zip(tot.year, tot.establishments)],
                      fontsize=6.2)
    f.set_xlim(2018.5, 2020.5)
    f.set_ylim(0, rb.asr_hi.max() * 2.6)
    f.yaxis.set_major_formatter(thousands("en"))
    # Only 2020 is shaded here: 2021 is outside this definition's era and outside the panel.
    _context(f, shade=(2020,), law=False, pandemic_pos=0.985, fs=6.0)
    f.set_xlabel(YEAR_AXIS)
    f.set_ylabel(RATE_AXIS, fontsize=7.0)
    _legend(f, loc="upper left", ncol=1, columnspacing=0.7, handlelength=1.2)
    titles[f] = _head(f, "f")

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
