"""Figure 4 (`fig4_triangulation`) — educational triangulation and population benchmarks, redrawn
from the published aggregates.

The stored plate `docs/study/corpus/figures/fig4_triangulation.jpg` was drawn by
`study/pipeline/08c_figures_triangulation.py` from the JUNAEB, ENDIDE, ENCAVI, REM, GRD and DEIS
microdata, which this repository does not carry. All six panels survive in tracked tables and are
rebuilt from them, one panel per table group:

  (a) PIE and special schools — `education_summary_year.csv` (which is `fig3a_pie.csv` plus the
      `special_schools_autism_n` column the pink line needs): strict ASD 11,877 -> 47,551,
      ASD-Asperger 9,135 -> 16,091, the harmonised ASD + Asperger stock 21,012 / 23,590 / 30,882 /
      42,940 / 63,642 / 86,475 / 106,786 (the seven value labels of the plate), the four figures
      SINACES prints for the same harmonised series (42,945 / 63,642 / 86,475 / 106,786, the black
      crosses) and special-school autism 2,074 / 2,298 / 2,505 / 2,626.
  (b) JUNAEB — the `junaeb_*` block of the same table, plus `E77_education_junaeb_full.csv` for the
      ceiling of the axis (see below) and `S12_junaeb_sex_level.csv` to check the 2023 Wilson limits.
  (c) surveys — `survey_estimates.csv` for the design-based estimate and its limits at full
      precision, checked cell by cell against `E75_survey_estimates_full.csv`, which prints the same
      twelve rows as "0.29 (0.22-0.38)".
  (d) indices — `models_convergence_index.csv`, the published convergence index itself, filtered to
      `variant == "sin_rett"` and `index_base_year == 2021`. Its five series reproduce the plate's
      five end labels exactly (277.51 -> 278, 199.52 -> 200, 630.94 -> 631, 777.94 -> 778,
      345.79 -> 346) and each index is re-derived here from its own component table as a check.
  (e) per 100,000 population — `F4_triangulation_series.csv`, the figure's own companion table, whose
      `Value` and `Denominator` cells are formatted strings ("29,974", "20,206,953") and are parsed.
  (f) principal F84 — `expanded_deis_principal_comparison.csv` and `grd_year_summary.csv`, checked
      against the published presentation table `ST11b_deis_vs_grd.csv`.

THE ESTIMATORS, UNCHANGED. This is the plate where the six panels deliberately do NOT share an
estimator, and the tracked tables distinguish them:

  * (b) mixes three states on purpose. 2024 (weight EXP_REG) and 2025 (weight EXP) are WEIGHTED
    percentages with the published weighted limits; 2023 has no published weight, so it is an
    UNWEIGHTED percentage with a Wilson interval and is drawn with hollow markers and no connecting
    line; 2019-2022 (no ASD item) and Grade 9 in 2024 (the variable is empty in the published file)
    are NOT ESTIMABLE and go in the lower strip as hatched squares. None of them is ever plotted as
    zero. The Wilson limits are recomputed from `n_students` and `tea_n` and checked against
    `S12_junaeb_sex_level.csv`, which prints them to two decimals.
  * (c) is the DESIGN-BASED weighted proportion with its logit-t interval (weight `fexp`, stratum
    `estrato`, cluster `cod_upm`), never cases/n: the ENDIDE adult total is 0.29% weighted, where
    72/30,010 unweighted would be 0.240%. The row label carries `cases / unweighted domain n`
    precisely because the plotted number is not that ratio. The rows flagged
    `precision_flag == "imprecise"` are drawn grey.
  * (d) indexes RATES for GRD and DEIS (F84 in any position per 100,000 GRD episodes; principal F84
    per 100,000 DEIS discharges) and COUNTS for A05 entries, the P2 December stock and PIE. Mixing
    the two would move every end label: the GRD population rate would give 363, not 278. The first
    common year is 2021 (the A05 autism code starts there) and 2019-2020 are therefore drawn dotted,
    before the base year, never as part of the solid line.
  * (e) gives each of the five strips its own axis, labels that strip's own maximum on it, and never
    compares heights across strips. Hatched bars are stocks (P2, PIE), solid bars flows (GRD
    episodes, GRD persons/year, A05 entries).
  * (f) is the PRINCIPAL position only, with exact Poisson limits, and keeps the plate's own note
    that DEIS has no secondary-diagnosis equivalent (DIAG2 is the external cause). The exact Poisson
    formula used for the SNSS subset, whose limits are not tabulated, is the one this repository
    uses everywhere else: it reproduces the tabulated DEIS and GRD limits to six decimals, which
    `_check()` verifies before anything is drawn.
  * Every GRD and DEIS input is the `sin_rett` variant — F84 without Rett, the definition the plate's
    title names.

TWO NUMBERS THAT ARE NOT IN A TRACKED TABLE AND ARE RECOMPUTED HERE. The 2023 JUNAEB Wilson limits
(above), and the ceiling of panel (b): the original set it at 1.22 x the highest weighted upper limit
of the WHOLE JUNAEB table, sexes included, which is 12.47 (2025 Grade 1, males). That value is
tracked in `E77_education_junaeb_full.csv`; measured against the stored plate the implied ceiling is
12.46, so the axis, its six ticks up to 12.5 and the position of the zero rule all come out where the
plate prints them.

WHERE THE LEGENDS SIT. The stored plate was finished by a de-congestion pass that measures the drawn
composition and moves legends and value labels out of whatever they cover. That pass is not rebuilt
here; each legend is placed where the stored plate actually prints it — upper right in (a) and (d),
upper left in (b) and (f) — and panel (f)'s legend is built from explicit handles in the order the
plate prints them, which is not the order the series are drawn in.

The corpus is English only, so this module is English only: it takes no language argument. The one
Spanish string it reads is the `domain` key of `survey_estimates.csv`, a source-database field value,
and it is never printed.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy import stats

_STUDY = Path(__file__).resolve().parents[1]          # docs/study, where figstyle lives
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))

from figstyle import *   # noqa: F401,F403 — style, clean, num, BLUE, ORANGE, GREEN, PINK, GOLD, SKY…

PLATE = "fig4_triangulation"
SOURCES = [
    "docs/study/data/education_summary_year.csv",
    "docs/study/data/survey_estimates.csv",
    "docs/study/data/models_convergence_index.csv",
    "docs/study/data/expanded_deis_principal_comparison.csv",
    "docs/study/data/grd_year_summary.csv",
    "docs/study/data/rem_pathway_annual.csv",
    "docs/study/data/fig3a_pie.csv",
    "docs/study/corpus/tables/F4_triangulation_series.csv",
    "docs/study/corpus/tables/E75_survey_estimates_full.csv",
    "docs/study/corpus/tables/E77_education_junaeb_full.csv",
    "docs/study/corpus/tables/S12_junaeb_sex_level.csv",
    "docs/study/corpus/tables/ST11b_deis_vs_grd.csv",
]
NOTE = ("Redraws the six triangulation panels — PIE and special-school stocks, the JUNAEB weighted / "
        "unweighted / not-estimable percentages by school level, the design-based survey proportions "
        "with logit-t limits, the 2021 = 100 convergence indices, the five per-100,000-population "
        "strips and the principal-F84 DEIS-versus-GRD comparison with exact Poisson limits — from the "
        "tracked education, survey, REM, GRD and DEIS aggregates in docs/study/data/ and the "
        "published companion tables in docs/study/corpus/tables/, all GRD and DEIS inputs sin_rett.")

ROOT = Path(__file__).resolve().parents[3]            # repository root
(EDU_FILE, SURVEY_FILE, INDEX_FILE, DEIS_FILE, GRD_FILE, REM_FILE, PIE_FILE,
 F4_FILE, E75_FILE, E77_FILE, S12_FILE, ST11B_FILE) = SOURCES

VARIANT = "sin_rett"                                  # F84 without Rett: the plate's own definition
YEARS = list(range(2019, 2026))                       # the plate's full span
YEARS_GRD = list(range(2019, 2025))                   # GRD and DEIS stop in 2024
BASE_YEAR = 2021                                      # first year common to all five index series
PER = 100_000.0
Z = stats.norm.ppf(0.975)

# --------------------------------------------------------------------------------------------------
# The plate's geometry and typography (study/pipeline/08c_figures_triangulation.py): 180 x 245 mm
# drawn 1:1, three rows by two columns, 9 pt bold panel heads over a 6 pt floor, seaborn 'whitegrid'
# (grid on both axes, no tick marks), 2020-21 shaded and Law 21.545 marked only as context.
# --------------------------------------------------------------------------------------------------
PLATE_W_IN, PLATE_H_IN = 180.0 / 25.4, 245.0 / 25.4
CELL_MARGIN = 2.0 / 180.0                             # left margin of a grid cell, figure fraction
FS_BASE, FS_TITLE, FS_MIN = 8.0, 9.0, 6.0
DARK, GREY_TEXT, MUTED = "#333333", "#555555", "#666666"
GREY_ROW = "#999999"                                  # an imprecise survey row in (c)
LAW_X = 2023 - 0.35                                   # `CFG.LAW_YEAR - 0.35`: March 2023 on a
#                                                       year-centred axis, marked as context only
PANDEMIC = [2020, 2021]
STRIP_FILL = "#eeeeee"                                # the 'not estimable' strip of (b)
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)
PLATE_RC = {
    "font.family": "DejaVu Sans", "font.size": FS_BASE,
    "axes.titlesize": FS_TITLE, "axes.titleweight": "bold", "axes.labelsize": FS_BASE,
    "xtick.labelsize": FS_MIN + 1.0, "ytick.labelsize": FS_MIN + 1.0,
    "legend.fontsize": FS_MIN + 0.2, "legend.title_fontsize": FS_MIN + 0.2,
    "legend.handlelength": 1.5, "legend.handletextpad": 0.5, "legend.labelspacing": 0.30,
    "legend.columnspacing": 0.9, "legend.borderpad": 0.3, "legend.frameon": False,
    "axes.facecolor": "white", "axes.edgecolor": DARK, "axes.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True,
    "grid.color": "#b0b0b0", "grid.alpha": 0.35, "grid.linewidth": 0.45,
    "lines.linewidth": 1.3, "lines.markersize": 3.4, "patch.linewidth": 0.6,
    # seaborn 'whitegrid': the grid is drawn, the tick marks are not.
    "xtick.bottom": False, "ytick.left": False, "ytick.right": False,
    "xtick.major.size": 0, "ytick.major.size": 0,
    "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    "axes.labelpad": 2.0, "axes.titlepad": 3.0,
    "figure.facecolor": "white", "savefig.facecolor": "white",
}

# --------------------------------------------------------------------------------------------------
# Every string the plate prints, in the plate's own words (LBL of the pipeline module, English side).
# --------------------------------------------------------------------------------------------------
T = ["PIE: autistic students", "JUNAEB: reported ASD (%)", "Surveys: weighted %",
     "Indices (2021 = 100)", "Per 100,000 population", "Principal F84: DEIS and GRD"]
L_YEAR = "Year"
N_PANDEMIC = "Reporting\ndisruption 2020–21"
N_LAW = "Law 21.545\n(context)"

A_YLABEL = "Students (annual school stock)"
A_SERIES = ["PIE strict ASD (Apuntes 60)", "PIE ASD-Asperger (Apuntes 60)",
            "Harmonised PIE ASD + Asperger", "Harmonised PIE as printed by SINACES",
            "Special schools, autism (SINACES)"]
A_SOURCE_CHANGE = "source: SINACES\n(2024–2025)"

B_YLABEL = "% of students with reported ASD (95% CI)"
B_LEVELS = [("parvularia", "Pre-school (NT1–NT2)", 0, -0.24),
            ("basico1", "Grade 1 (1º básico)", 1, -0.08),
            ("basico5", "Grade 5 (5º básico)", 2, 0.08),
            ("medio1", "Grade 9 (1º medio)", 3, 0.24)]
B_UNWEIGHTED = "2023: unweighted (Wilson CI)"
B_NOT_ESTIMABLE = "not estimable (see caption)"
B_STRIP = "not estimable"

C_XLABEL = "Weighted % (95% CI, log scale)\nrow label: cases / unweighted domain n"
C_IMPRECISE = "imprecise (< 30 cases or RSE > 30%): greyed"
#: (heading the plate prints, `domain` key of survey_estimates.csv, colour). The domain strings are
#: source-database values, exactly like the REM code names elsewhere in the corpus; the plate prints
#: only the English headings above.
C_GROUPS = [("ENDIDE 2022 · adults 18+", "ENDIDE adultos 18+: autismo reportado", 0),
            ("ENDIDE 2022 · 2–17 reported", "ENDIDE NNA 2-17: autismo reportado", 2),
            ("ENDIDE 2022 · 2–17 confirmed",
             "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico", 3),
            ("ENCAVI 2023–24 · persons 15+",
             "ENCAVI 15+: diagnóstico de trastorno del espectro autista", 1)]
C_ROWS = [("total", "Total"), ("Hombre", "Males"), ("Mujer", "Females")]

D_YLABEL = "Index (first common year 2021 = 100; log scale)"
D_NOTE = ("units, denominators and coverage differ;\nlevels are not comparable; dotted 2019–2020\n"
          "= before the first common year")
#: (series key of models_convergence_index.csv, legend label, Okabe index, marker).
D_SERIES = [("grd_any_rate", "GRD: F84 any position (rate)", 0, "o"),
            ("deis_principal_rate", "DEIS: principal F84 (rate)", 1, "^"),
            ("a05_strict_entries", "REM A05: entries, flow (n {n})", 2, "s"),
            ("p2_december_stock", "REM P2: Dec., stock (n {n})", 3, "D"),
            ("pie_harmonised", "Harmonised PIE (school stock)", 4, "P")]

E_XLABEL = "Year · per 100,000 pop. (INE 2017); one axis per strip"
#: (series key of F4_triangulation_series.csv, strip label, Okabe index, is a stock).
E_STRIPS = [("GRD: episodes with documented F84 (any position)", "GRD F84 episodes (flow)", 0, False),
            ("GRD: unique persons within the year with F84", "GRD persons/year F84 (flow)", 5, False),
            ("REM A05: strict-autism entries (05990022)", "A05 autism entries (flow)", 2, False),
            ("REM P2: ASD under control, December (P2500500)", "P2 ASD December (stock)", 3, True),
            ("Harmonised PIE ASD + Asperger (school stock)", "Harmonised PIE (school stock)", 4, True)]

F_YLABEL = "Principal F84 per 100,000\ndischarges / episodes (95% CI)"
F_DEIS_ALL = "DEIS: all establishments"
F_DEIS_SNSS = "DEIS: SNSS subset (public hospitals)"
F_GRD_ALL = "GRD: principal F84, observed panel, all activity"
F_GRD_HOSP = "GRD: principal F84, strict hospitalisation"
F_NOTE = ("DEIS DIAG2 = external cause (never F84):\nDEIS 'any position' = principal. Secondary\n"
          "F84 in GRD has no DEIS equivalent.")


# --------------------------------------------------------------------------------------------------
# Reading the tracked tables
# --------------------------------------------------------------------------------------------------
def _read(name):
    return pd.read_csv(ROOT / name, encoding="utf-8-sig")


def _count(cell):
    """A presentation count out of a formatted cell: '20,206,953' -> 20206953, '—' -> nan."""
    s = str(cell).replace(",", "").replace(" ", "").strip()
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else np.nan


def _triplet(cell):
    """Point estimate and the two limits of a printed interval, '18.2 (16.2 to 20.4)' or
    '6.60 (6.48–6.73)' -> (18.2, 16.2, 20.4). A cell without an interval gives three nan."""
    nums = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?", str(cell))
    if len(nums) < 3:
        return (np.nan, np.nan, np.nan)
    return tuple(float(n.replace(",", "")) for n in nums[:3])


def _dash(lo, hi, dec=2):
    """The study's printed interval: an en dash between two positive limits."""
    return f"{num(lo, 'en', dec)}–{num(hi, 'en', dec)}"


def poisson_ci(k, denom, per=PER):
    """Exact (Garwood) Poisson limits of a rate per `per`, the interval this repository publishes.

    Verified in `_check()` against the limits `expanded_deis_principal_comparison.csv` and
    `grd_year_summary.csv` already store, which it reproduces to six decimals; it is used to supply
    the one interval of panel (f) that is not tabulated, the DEIS SNSS subset.
    """
    k = float(k)
    lo = stats.chi2.ppf(0.025, 2 * k) / 2 if k > 0 else 0.0
    hi = stats.chi2.ppf(0.975, 2 * (k + 1)) / 2
    return per * lo / denom, per * hi / denom


def wilson_ci(k, n):
    """Wilson limits of a percentage — the interval the plate draws for the unweighted 2023 JUNAEB
    percentages, which have no published weight. Checked against `S12_junaeb_sex_level.csv`."""
    p = k / n
    denom = 1 + Z * Z / n
    centre = p + Z * Z / (2 * n)
    half = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return 100 * (centre - half) / denom, 100 * (centre + half) / denom


def education():
    """`education_summary_year.csv` indexed on the school year, all seven years present."""
    return _read(EDU_FILE).set_index("year").reindex(YEARS)


def junaeb_rows(edu):
    """One row per level and year of panel (b): the state, the percentage and its two limits.

    The state is the table's own `estimable` flag and decides both the estimator and the mark:
    'yes' is the weighted percentage with the published weighted limits, 'unweighted_only' is the
    unweighted percentage with a Wilson interval, 'no' goes to the not-estimable strip.
    """
    out = []
    for key, label, colour, offset in B_LEVELS:
        for year in YEARS:
            state = edu.loc[year, f"junaeb_{key}_estimable"]
            if state == "yes":
                pct = edu.loc[year, f"junaeb_{key}_pct_weighted"]
                lo = edu.loc[year, f"junaeb_{key}_pct_weighted_lo"]
                hi = edu.loc[year, f"junaeb_{key}_pct_weighted_hi"]
            elif state == "unweighted_only":
                pct = edu.loc[year, f"junaeb_{key}_pct_unweighted"]
                lo, hi = wilson_ci(edu.loc[year, f"junaeb_{key}_tea_n"],
                                   edu.loc[year, f"junaeb_{key}_n_students"])
            else:
                pct = lo = hi = np.nan
            out.append(dict(key=key, label=label, colour=OKABE[colour], offset=offset,
                            year=year, state=state, pct=pct, lo=lo, hi=hi))
    return pd.DataFrame(out)


def junaeb_ceiling():
    """1.22 x the highest weighted upper limit of the WHOLE JUNAEB table, sexes included.

    The plate's ceiling is not the ceiling of the four series it draws: the original measured the
    full year x level x sex table, whose highest upper limit is 12.47 (2025, Grade 1, males).
    """
    t = _read(E77_FILE)
    hi = t["Weighted % (95% CI)"].map(lambda c: _triplet(c)[2])
    return float(hi.max())


def surveys():
    """The twelve rows of panel (c): four domains x total / males / females, in the plate's order.

    The estimate is the design-based weighted proportion of `survey_estimates.csv` and its logit-t
    limits, never cases/n; `cases` and `n` go to the row label, which says so.
    """
    t = _read(SURVEY_FILE)
    t = t[(t.estimate_type == "primary") & (t.subgroup_type.isin(["total", "sex"]))]
    rows = []
    for heading, domain, colour in C_GROUPS:
        rows.append(dict(kind="header", label=heading, colour=OKABE[colour]))
        for key, label in C_ROWS:
            r = t[(t.domain == domain) & (t.subgroup == key)]
            if r.empty:
                continue
            r = r.iloc[0]
            grey = (r.precision_flag == "imprecise") or (pd.notna(r.rse) and r.rse > 0.30)
            rows.append(dict(kind="row", label=label, colour=GREY_ROW if grey else OKABE[colour],
                             pct=100 * r.proportion, lo=100 * r.lo, hi=100 * r.hi,
                             cases=int(r.cases), n=int(r.n), grey=grey))
    return rows


def index_series():
    """The published convergence index, `sin_rett` on base 2021, one frame per plotted series."""
    t = _read(INDEX_FILE)
    t = t[(t.variant == VARIANT) & (t.index_base_year == BASE_YEAR)]
    return {key: t[t.series == key].sort_values("year").set_index("year") for key, *_ in D_SERIES}


def rem_reporting():
    """The REM reporting-establishment range printed in the legend of (d) and the strips of (e)."""
    t = _read(REM_FILE)
    out = {}
    for name, code, measure in (("a05", "05990022", "annual_sum"), ("p2", "P2500500", "december_stock")):
        z = t[(t.code.astype(str) == code) & (t.measure == measure) & (t.variant == "single_code")]
        out[name] = (int(z.n_reporting_establishments.min()), int(z.n_reporting_establishments.max()))
    return out


def per_population():
    """The five strips of (e) out of the figure's own companion table.

    `Value` and `Denominator` are formatted strings; the rate is recomputed from them at full
    precision and checked against the `Per 100,000 pop.` cell the table prints.
    """
    t = _read(F4_FILE)
    t = t.assign(value=t["Value"].map(_count), denom=t["Denominator"].map(_count),
                 reporting=t["Reporting N"].map(_count))
    t["rate"] = PER * t.value / t.denom
    t["printed"] = t["Per 100,000 pop. (95% CI)"].map(lambda c: _triplet(c)[0])
    return t


def deis_grd():
    """Panel (f): the four principal-F84 series with their exact Poisson limits.

    DEIS (all establishments) and the two GRD series carry their limits in the tracked tables; the
    DEIS SNSS subset does not, and its limits are computed from `deis_f84_principal_snss` over
    `deis_discharges_snss` with the same exact formula `_check()` validates on the other three.
    """
    d = _read(DEIS_FILE)
    d = d[d.variant == VARIANT].sort_values("year").set_index("year")
    g = _read(GRD_FILE)
    g = g[(g.variant == VARIANT) & (g.panel == "observed") & (g.position == "principal")]
    g_all = g[g.activity == "all"].sort_values("year").set_index("year")
    g_hosp = g[g.activity == "hospitalisation"].sort_values("year").set_index("year")
    snss = pd.DataFrame(
        [dict(year=y,
              rate=PER * d.loc[y, "deis_f84_principal_snss"] / d.loc[y, "deis_discharges_snss"],
              lo=poisson_ci(d.loc[y, "deis_f84_principal_snss"], d.loc[y, "deis_discharges_snss"])[0],
              hi=poisson_ci(d.loc[y, "deis_f84_principal_snss"], d.loc[y, "deis_discharges_snss"])[1])
         for y in YEARS_GRD]).set_index("year")
    return d, snss, g_all, g_hosp


# --------------------------------------------------------------------------------------------------
# Nothing is drawn until every number this module computes has met the number the corpus prints.
# --------------------------------------------------------------------------------------------------
def _close(a, b, tol):
    return bool(np.isfinite(a) and np.isfinite(b) and abs(a - b) <= tol)


def _check(edu, jun, surv, idx, pp, deis, snss, g_all, g_hosp):
    """Measure this module's numbers against the published presentation tables."""
    bad = []

    # (a) the seven harmonised value labels and the four SINACES crosses.
    pie = _read(PIE_FILE).set_index("year")
    for year in YEARS:
        if edu.loc[year, "pie_harmonised_n"] != pie.loc[year, "pie_harmonised_n"]:
            bad.append(f"(a) harmonised PIE {year} differs from fig3a_pie.csv")

    # (b) the 2024-2025 weighted percentages and their limits, against E77's own printed cells.
    e77 = _read(E77_FILE)
    e77 = e77[(e77.Sex == "Both sexes") & (e77.Year.isin([2024, 2025]))]
    levels = {"Pre-school": "parvularia", "Grade 1": "basico1", "Grade 5": "basico5",
              "Year 9": "medio1"}
    for year, level, cell in zip(e77.Year, e77.Level, e77["Weighted % (95% CI)"]):
        pct, lo, hi = _triplet(cell)
        mine = jun[(jun.key == levels[level]) & (jun.year == year)].iloc[0]
        if not np.isfinite(pct):                     # Grade 9 in 2024: not estimable in both
            if mine.state != "no":
                bad.append(f"(b) {year} {level} is printed as not estimable but drawn as a point")
            continue
        if not (mine.state == "yes" and _close(mine.pct, pct, 0.006)
                and _close(mine.lo, lo, 0.006) and _close(mine.hi, hi, 0.006)):
            bad.append(f"(b) weighted {year} {level}: {mine.pct:.3f} ({mine.lo:.3f}–{mine.hi:.3f}) "
                       f"against the printed {pct} ({lo}–{hi})")

    # (b) the 2023 Wilson limits, against the ones S12 prints to two decimals.
    s12 = _read(S12_FILE)
    s12 = s12[(s12.Sex == "All") & (s12.Year == 2023)]
    printed = {"Pre-school (NT1–NT2)": "parvularia", "Grade 1 (1º básico)": "basico1",
               "Grade 5 (5º básico)": "basico5", "Grade 9 (1º medio)": "medio1"}
    for level, cell in zip(s12.Level, s12["Unweighted % (Wilson 95% CI)"]):
        key = printed[level]
        pct, lo, hi = _triplet(cell)
        mine = jun[(jun.key == key) & (jun.year == 2023)].iloc[0]
        if not (_close(mine.pct, pct, 0.006) and _close(mine.lo, lo, 0.006)
                and _close(mine.hi, hi, 0.006)):
            bad.append(f"(b) 2023 Wilson {key}: {mine.pct:.3f} ({mine.lo:.3f}–{mine.hi:.3f}) "
                       f"against the printed {pct} ({lo}–{hi})")

    # (c) all twelve rows against the twelve printed cells of E75.
    e75 = _read(E75_FILE)
    e75 = e75[(e75["Estimate type"] == "primary")
              & (e75.Subgroup.isin(["total: total", "sex: Male", "sex: Female"]))]
    printed_c = [_triplet(c) for c in e75["Weighted % (95% CI)"]]
    drawn = [(r["pct"], r["lo"], r["hi"]) for r in surv if r["kind"] == "row"]
    for pct, lo, hi in drawn:
        if not any(_close(pct, p, 0.006) and _close(lo, l, 0.006) and _close(hi, h, 0.006)
                   for p, l, h in printed_c):
            bad.append(f"(c) {pct:.2f} ({lo:.2f}–{hi:.2f}) is not a printed E75 row")

    # (d) each index re-derived from its own component table.
    comp = {
        "grd_any_rate": _read(GRD_FILE).pipe(
            lambda t: t[(t.variant == VARIANT) & (t.panel == "observed") & (t.activity == "all")
                        & (t.position == "any")].set_index("year").rate_per_100k_episodes),
        "deis_principal_rate": _read(DEIS_FILE).pipe(
            lambda t: t[t.variant == VARIANT].set_index("year")
            .deis_rate_f84_principal_per_100k_discharges),
        "a05_strict_entries": pp[pp["Series"] == E_STRIPS[2][0]].set_index("Year").value,
        "p2_december_stock": pp[pp["Series"] == E_STRIPS[3][0]].set_index("Year").value,
        "pie_harmonised": pp[pp["Series"] == E_STRIPS[4][0]].set_index("Year").value,
    }
    for key, series in comp.items():
        z = idx[key]
        for year in z.index:
            mine = 100 * series.loc[year] / series.loc[BASE_YEAR]
            if not _close(mine, z.loc[year, "index"], 0.02):
                bad.append(f"(d) {key} {year}: recomputed {mine:.2f} against the published "
                           f"{z.loc[year, 'index']:.2f}")

    # (e) each rate against the `Per 100,000 pop.` cell the same table prints.
    for row in pp.itertuples():
        if not _close(row.rate, row.printed, 0.051):
            bad.append(f"(e) {row.Series} {row.Year}: {row.rate:.2f} against the printed {row.printed}")

    # (f) the exact Poisson limits against the two tables that already store them, and the four
    #     series against the presentation table ST11b.
    for year in YEARS_GRD:
        lo, hi = poisson_ci(deis.loc[year, "deis_f84_principal"], deis.loc[year, "deis_discharges_total"])
        if not (_close(lo, deis.loc[year, "deis_rate_lo95"], 1e-6)
                and _close(hi, deis.loc[year, "deis_rate_hi95"], 1e-6)):
            bad.append(f"(f) exact Poisson does not reproduce the DEIS limits of {year}")
        lo, hi = poisson_ci(g_all.loc[year, "n_episodes_f84"],
                            g_all.loc[year, "n_episodes_total_same_panel_activity"])
        if not (_close(lo, g_all.loc[year, "rate_lo"], 1e-6)
                and _close(hi, g_all.loc[year, "rate_hi"], 1e-6)):
            bad.append(f"(f) exact Poisson does not reproduce the GRD limits of {year}")
    st11b = _read(ST11B_FILE)
    st11b = st11b[st11b.Series.str.startswith("F84 family")].set_index("Year")
    for year in YEARS_GRD:
        pct, lo, hi = _triplet(st11b.loc[year, "Principal F84 per 100,000 discharges (exact 95% CI)"])
        if not _close(deis.loc[year, "deis_rate_f84_principal_per_100k_discharges"], pct, 0.051):
            bad.append(f"(f) DEIS {year} against ST11b")
        if not _close(g_all.loc[year, "rate_per_100k_episodes"],
                      float(st11b.loc[year, "GRD principal F84 per 100,000 episodes"]), 0.051):
            bad.append(f"(f) GRD {year} against ST11b")
        mine = PER * float(_count(st11b.loc[year, "DEIS principal F84 SNSS"])) / \
            float(_count(st11b.loc[year, "SNSS discharges"]))
        if not _close(snss.loc[year, "rate"], mine, 1e-9):
            bad.append(f"(f) DEIS SNSS {year} against ST11b")
    if bad:
        raise AssertionError("fig4_triangulation: " + "; ".join(bad))


# --------------------------------------------------------------------------------------------------
# Shared context furniture: the 2020-21 shading and the Law 21.545 rule, drawn on every year panel
# and labelled once, in (a), exactly as the plate does it.
# --------------------------------------------------------------------------------------------------
def _context(ax, pandemic_label=False, law_label=False):
    for year in PANDEMIC:
        ax.axvspan(year - 0.5, year + 0.5, color="grey", alpha=0.12, lw=0, zorder=0)
    if pandemic_label:
        ax.text(np.mean(PANDEMIC), 0.55, N_PANDEMIC, transform=ax.get_xaxis_transform(),
                ha="center", va="center", fontsize=FS_MIN, color=GREY_TEXT, linespacing=1.15)
    ax.axvline(LAW_X, color="#444444", ls=":", lw=1.2, zorder=1)
    if law_label:
        ax.text(LAW_X + 0.06, 0.55, N_LAW, transform=ax.get_xaxis_transform(), ha="left",
                va="center", fontsize=FS_MIN, color="#444444", linespacing=1.15)


def _year_axis(ax, years=YEARS, labels=True):
    ax.set_xticks(years)
    ax.set_xticklabels([f"’{y % 100:02d}" for y in years] if labels else [],
                       fontsize=FS_MIN + 0.5)


# --------------------------------------------------------------------------------------------------
# (a) PIE: autistic students
# --------------------------------------------------------------------------------------------------
def _panel_a(ax, edu):
    years = np.array(YEARS, dtype=float)
    ax.plot(years, edu.pie_tea_strict_n, "s--", color=BLUE, lw=1.1, ms=3.2, label=A_SERIES[0])
    ax.plot(years, edu.pie_tea_asperger_n, "^--", color=ORANGE, lw=1.1, ms=3.2, label=A_SERIES[1])
    harm = edu.pie_harmonised_n
    apuntes = [y for y in YEARS if y <= 2023]
    sinaces = [y for y in YEARS if y >= 2023]
    ax.plot(apuntes, harm.loc[apuntes], "o-", color=SKY, lw=1.6, ms=3.8, label=A_SERIES[2])
    ax.plot(sinaces, harm.loc[sinaces], "D--", color=SKY, lw=1.3, ms=3.2, mfc="white")
    ax.plot(years, edu.pie_harmonised_sinaces_n, "x", color=DARK, ms=4, mew=1.0, label=A_SERIES[3])
    ax.plot(years, edu.special_schools_autism_n, "v-", color=PINK, lw=1.0, ms=3.0, label=A_SERIES[4])

    # the source of the harmonised series changes after 2023; the rule and its note say where
    ax.axvline(2023.5, color="#888888", ls="-.", lw=0.9)
    ax.text(2023.55, 0.62, A_SOURCE_CHANGE, transform=ax.get_xaxis_transform(), fontsize=FS_MIN,
            color=MUTED, va="bottom", linespacing=1.15)
    _context(ax, pandemic_label=True, law_label=True)

    clean(ax, grid="both")
    ax.set_ylim(0, float(harm.max()) * 2.3)
    _year_axis(ax)
    ax.set_xlabel(L_YEAR, fontsize=FS_MIN + 1)
    ax.set_ylabel(A_YLABEL, fontsize=FS_MIN + 1)
    ax.yaxis.set_major_formatter(thousands("en"))

    # The seven value labels of the harmonised series. The original placed them with a measuring
    # placer that steps a label away until it clears its neighbours; the offsets below are the
    # positions that placer settled on, measured off the stored plate in points.
    place = {2019: (12.8, 5.2, False), 2020: (0.0, 13.0, True), 2021: (0.0, 12.9, True),
             2022: (0.0, 12.8, False), 2023: (2.8, 12.6, False),
             2024: (2.0, 5.0, False), 2025: (-14.8, 3.8, False)}
    for year, (dx, dy, boxed) in place.items():
        ax.annotate(num(harm.loc[year], "en", 0), (year, harm.loc[year]), xytext=(dx, dy),
                    textcoords="offset points", ha="center", va="center", fontsize=FS_MIN,
                    color=SKY, bbox=NOTE_BBOX if boxed else None, zorder=5)
    ax.legend(loc="upper right", fontsize=FS_MIN + 0.2, handlelength=1.4, frameon=True,
              framealpha=1.0, edgecolor="#cccccc", facecolor="white", borderpad=0.25).set_zorder(6)


# --------------------------------------------------------------------------------------------------
# (b) JUNAEB: reported ASD (%)
# --------------------------------------------------------------------------------------------------
def _panel_b(ax, jun, ceiling):
    strip_y = -0.13 * ceiling
    ax.axhspan(strip_y * 1.9, strip_y * 0.25, color=STRIP_FILL, zorder=0)
    _context(ax)

    for key, label, colour_ix, offset in B_LEVELS:
        d = jun[jun.key == key]
        colour = OKABE[colour_ix]
        for sel, kw in (("yes", dict(fmt="o-", lw=1.2, label=label)),
                        ("unweighted_only", dict(fmt="o", lw=0.9, mfc="white"))):
            z = d[d.state == sel]
            pct, lo, hi = z.pct.to_numpy(), z.lo.to_numpy(), z.hi.to_numpy()
            ax.errorbar(z.year.to_numpy() + offset, pct, yerr=[pct - lo, hi - pct], color=colour,
                        ms=3.4, capsize=1.4, elinewidth=0.6, **kw)
        ne = d[d.state == "no"]
        ax.scatter(ne.year + offset, np.full(len(ne), strip_y), marker="s", s=13,
                   facecolor="white", edgecolor=colour, hatch="///", linewidth=0.6, zorder=3)
    ax.axhline(0, color=DARK, lw=0.8, zorder=2)

    clean(ax, grid="both")
    ax.set_ylim(strip_y * 1.9, ceiling * 1.22)
    ax.set_xlim(2018.4, 2025.95)
    _year_axis(ax)
    ticks = [t for t in ax.get_yticks() if 0 <= t <= ceiling * 1.20]
    dec = 0 if all(abs(t - round(t)) < 1e-9 for t in ticks) else 1
    ax.set_yticks(list(ticks) + [strip_y])
    ax.set_yticklabels([num(t, "en", dec) for t in ticks] + [B_STRIP])
    ax.get_yticklabels()[-1].set_fontsize(FS_MIN)
    ax.get_yticklabels()[-1].set_color(GREY_TEXT)
    ax.set_xlabel(L_YEAR, fontsize=FS_MIN + 1)
    ax.set_ylabel(B_YLABEL, fontsize=FS_MIN + 1)

    # one value label per weighted point, in its own level's colour, as the plate prints them
    place = {("parvularia", 2024): (-4, 9, "right"), ("basico1", 2024): (-2, -9, "right"),
             ("basico5", 2024): (2, 9, "left"), ("parvularia", 2025): (4, -7, "left"),
             ("basico1", 2025): (1, 9, "center"), ("basico5", 2025): (5, 5, "left"),
             ("medio1", 2025): (3, -8, "left")}
    for key, label, colour_ix, offset in B_LEVELS:
        for row in jun[(jun.key == key) & (jun.state == "yes")].itertuples():
            dx, dy, ha = place[(key, row.year)]
            ax.annotate(num(row.pct, "en", 1), (row.year + offset, row.pct), xytext=(dx, dy),
                        textcoords="offset points", ha=ha, va="center", fontsize=FS_MIN,
                        color=OKABE[colour_ix], zorder=5)

    # The stored plate prints this legend with plain rules for the four levels — the marker keys
    # below them are what distinguishes the three states — and over an opaque white card with no
    # visible border, so the shaded band does not print through the labels.
    handles = [Line2D([0], [0], color=OKABE[c], lw=1.2, label=label)
               for _, label, c, _ in B_LEVELS]
    handles += [Line2D([0], [0], marker="o", color=GREY_TEXT, mfc="white", lw=0, ms=3.4,
                       label=B_UNWEIGHTED),
                Line2D([0], [0], marker="s", color=GREY_TEXT, mfc="white", lw=0, ms=3.8,
                       label=B_NOT_ESTIMABLE)]
    ax.legend(handles=handles, loc="upper left", fontsize=FS_MIN + 0.2, handlelength=1.3,
              frameon=True, framealpha=1.0, edgecolor="none", facecolor="white",
              borderpad=0.25).set_zorder(6)


# --------------------------------------------------------------------------------------------------
# (c) Surveys: weighted %
# --------------------------------------------------------------------------------------------------
def _panel_c(ax, surv):
    n = len(surv)
    ticks, ticklabels = [], []
    for i, row in enumerate(surv):
        y = n - 1 - i
        if row["kind"] == "header":
            ax.text(0.0, y, row["label"], fontsize=FS_MIN, fontweight="bold", color=row["colour"],
                    va="center", ha="left", transform=ax.get_yaxis_transform())
            continue
        ax.plot([row["lo"], row["hi"]], [y, y], color=row["colour"], lw=1.2, zorder=2)
        ax.scatter(row["pct"], y, s=11, color=row["colour"], zorder=3, edgecolor="white",
                   linewidth=0.5)
        # one line per row: with sixteen rows in an 82 mm cell a two-line label invades its neighbour
        ax.text(11.0, y, f"{num(row['pct'], 'en', 2)} ({_dash(row['lo'], row['hi'])})",
                va="center", ha="left", fontsize=FS_MIN, color=DARK)
        ticks.append(y)
        ticklabels.append(f"{row['label']} · {row['cases']}/{num(row['n'], 'en', 0)}")

    ax.set_xscale("log")
    ax.set_xlim(0.05, 420)
    ax.set_xticks([0.1, 0.3, 1, 3, 10])
    ax.set_xticklabels([num(v, "en", 1) for v in (0.1, 0.3, 1, 3, 10)], fontsize=FS_MIN + 0.5)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_yticks(ticks)
    ax.set_yticklabels(ticklabels, fontsize=FS_MIN)
    ax.set_ylim(-1.6, n - 0.3)
    ax.set_xlabel(C_XLABEL, fontsize=FS_MIN + 0.5)
    ax.text(0.0, -1.15, C_IMPRECISE, transform=ax.get_yaxis_transform(), fontsize=FS_MIN,
            ha="left", va="center", color="#777777")
    clean(ax, grid="both")


# --------------------------------------------------------------------------------------------------
# (d) Indices (2021 = 100)
# --------------------------------------------------------------------------------------------------
def _panel_d(ax, idx, reporting):
    _context(ax)
    top = 0.0
    for key, label, colour_ix, marker in D_SERIES:
        z = idx[key]
        colour = OKABE[colour_ix]
        if "{n}" in label:
            lo, hi = reporting["a05" if key.startswith("a05") else "p2"]
            label = label.format(n=f"{num(lo, 'en', 0)}–{num(hi, 'en', 0)}")
        post = z[z.index >= BASE_YEAR]
        pre = z[z.index <= BASE_YEAR]
        if key == "pie_harmonised":       # the Apuntes 60 -> SINACES change of source, as in (a)
            first = post[post.index <= 2023]
            later = post[post.index >= 2023]
            ax.plot(first.index, first["index"], marker=marker, ls="-", color=colour, lw=1.3,
                    ms=3.4, label=label)
            ax.plot(later.index, later["index"], marker=marker, ls="--", color=colour, lw=1.1,
                    ms=3.4, mfc="white")
        else:
            ax.plot(post.index, post["index"], marker=marker, ls="-", color=colour, lw=1.3,
                    ms=3.4, label=label)
        if len(pre) > 1:                  # the years before the first common year are never solid
            ax.plot(pre.index, pre["index"], marker=marker, ls=":", color=colour, lw=0.9, ms=2.6,
                    alpha=0.6)
        end = post["index"].iloc[-1]
        ax.annotate(num(end, "en", 0), (post.index[-1], end), xytext=(3, 0),
                    textcoords="offset points", fontsize=FS_MIN, color=colour, va="center")
        top = max(top, float(z["index"].max()))

    ax.set_yscale("log")
    ax.axhline(100, color=GREY_ROW, ls="--", lw=0.8)
    ax.set_ylim(35, top * 9)
    clean(ax, grid="both")
    _year_axis(ax)
    ax.margins(x=0.14)
    ax.set_xlabel(f"{L_YEAR}\n{D_NOTE}", fontsize=FS_MIN + 0.5)
    ax.set_ylabel(D_YLABEL, fontsize=FS_MIN + 1)
    ax.legend(loc="upper right", fontsize=FS_MIN, handlelength=1.4)


# --------------------------------------------------------------------------------------------------
# (e) Per 100,000 population — five strips, five axes, never one scale
# --------------------------------------------------------------------------------------------------
def _panel_e(axes, pp, reporting):
    for k, (ax, (series, label, colour_ix, stock)) in enumerate(zip(axes, E_STRIPS)):
        z = pp[pp["Series"] == series].sort_values("Year")
        colour = OKABE[colour_ix]
        if stock:
            ax.bar(z.Year, z.rate, color="white", edgecolor=colour, hatch="///", linewidth=0.8,
                   width=0.72)
        else:
            ax.bar(z.Year, z.rate, color=colour, width=0.72)
        for year in PANDEMIC:
            ax.axvspan(year - 0.5, year + 0.5, color="grey", alpha=0.1, lw=0, zorder=0)
        top = float(z.rate.max())
        ax.set_xlim(2018.4, 2025.9)
        ax.set_ylim(0, top * 1.55)        # head-room for the strip label, which sits inside the axes
        ax.set_yticks([0, round(top, 1 if top < 100 else 0)])
        ax.tick_params(axis="y", labelsize=FS_MIN, pad=1.0)
        text = label
        if series.startswith("REM"):
            lo, hi = reporting["a05" if "A05" in series else "p2"]
            text += f" · n {num(lo, 'en', 0)}–{num(hi, 'en', 0)}"
        ax.text(0.012, 0.97, text, transform=ax.transAxes, ha="left", va="top", fontsize=FS_MIN,
                fontweight="bold", color=DARK)
        clean(ax, grid="both")
        last = k == len(E_STRIPS) - 1
        _year_axis(ax, labels=last)
        if last:
            ax.set_xlabel(E_XLABEL, fontsize=FS_MIN + 0.5)


# --------------------------------------------------------------------------------------------------
# (f) Principal F84: DEIS and GRD
# --------------------------------------------------------------------------------------------------
def _panel_f(ax, deis, snss, g_all, g_hosp):
    years = np.array(YEARS_GRD, dtype=float)
    rate = deis.deis_rate_f84_principal_per_100k_discharges.to_numpy()
    h_deis = ax.errorbar(years - 0.1, rate,
                         yerr=[rate - deis.deis_rate_lo95.to_numpy(),
                               deis.deis_rate_hi95.to_numpy() - rate],
                         fmt="^-", color=GREEN, lw=1.2, ms=3.4, capsize=1.4, elinewidth=0.6,
                         label=F_DEIS_ALL)
    s_rate, s_lo, s_hi = snss.rate.to_numpy(), snss.lo.to_numpy(), snss.hi.to_numpy()
    h_snss = ax.errorbar(years + 0.1, s_rate, yerr=[s_rate - s_lo, s_hi - s_rate],
                         fmt="v--", color=YELLOW, lw=1.1, ms=3.4, capsize=1.4, elinewidth=0.6,
                         label=F_DEIS_SNSS)
    g = g_all.rate_per_100k_episodes.to_numpy()
    h_grd = ax.errorbar(years, g,
                        yerr=[g - g_all.rate_lo.to_numpy(), g_all.rate_hi.to_numpy() - g],
                        fmt="o-", color=BLUE, lw=1.2, ms=3.4, capsize=1.4, elinewidth=0.6,
                        label=F_GRD_ALL)
    h_hosp, = ax.plot(years, g_hosp.rate_per_100k_episodes.to_numpy(), "s:", color=ORANGE, lw=1.0,
                      ms=3.0, label=F_GRD_HOSP)
    # the observed panel is not a fixed panel: the hospitals behind each year are printed on it
    for year in YEARS_GRD:
        ax.text(year, 1.0, f"n={int(g_all.loc[year, 'hospitals_n'])}", ha="center", va="bottom",
                fontsize=FS_MIN, color=BLUE, rotation=90, bbox=NOTE_BBOX, zorder=4)
    _context(ax)

    clean(ax, grid="both")
    ax.set_ylim(0, float(max(snss.hi.max(), g_hosp.rate_per_100k_episodes.max())) * 2.6)
    _year_axis(ax, YEARS_GRD)
    ax.set_xlabel(L_YEAR, fontsize=FS_MIN + 1)
    ax.set_ylabel(F_YLABEL, fontsize=FS_MIN + 1)
    # the de-congestion pass of the original reordered this legend; the plate prints it like this
    ax.legend(handles=[h_hosp, h_deis, h_snss, h_grd], loc="upper left", fontsize=FS_MIN,
              handlelength=1.4)
    ax.text(0.03, 0.56, F_NOTE, transform=ax.transAxes, fontsize=FS_MIN, ha="left", va="top",
            color="#444444", linespacing=1.25)


# --------------------------------------------------------------------------------------------------
def _head(ax, k):
    """The head of one panel, set before the layout pass so room is reserved for it."""
    return ax.set_title(f"({'abcdef'[k]}) {T[k]}", loc="left", fontsize=FS_TITLE,
                        fontweight="bold", pad=3.0)


def _align_heads(fig, titles, axes):
    """Re-anchor the heads to the left edge of their GRID CELL, not of their axes.

    The original does this once the layout is settled (`C.plate_align_titles`), so the two columns
    of heads line up whatever the width of the y-tick labels. Here the layout is drawn once and then
    frozen, so the measured positions are the ones the returned figure keeps.
    """
    fig.canvas.draw()
    fig.set_layout_engine("none")
    for k, (title, ax) in enumerate(zip(titles, axes)):
        cell_left = CELL_MARGIN + 0.5 * (k % 2)
        pos = ax.get_position()
        title.set_position(((cell_left - pos.x0) / pos.width, 1.0))


def draw():
    edu = education()
    jun = junaeb_rows(edu)
    ceiling = junaeb_ceiling()
    surv = surveys()
    idx = index_series()
    reporting = rem_reporting()
    pp = per_population()
    deis, snss, g_all, g_hosp = deis_grd()
    _check(edu, jun, surv, idx, pp, deis, snss, g_all, g_hosp)

    style()
    plt.rcParams.update(PLATE_RC)
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), layout="constrained")
    try:
        fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    except AttributeError:                               # pragma: no cover — older matplotlib
        pass
    gs = fig.add_gridspec(3, 2)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    strips = [fig.add_subplot(cell) for cell in gs[2, 0].subgridspec(5, 1, hspace=0.16)]
    ax_f = fig.add_subplot(gs[2, 1])

    heads = [ax_a, ax_b, ax_c, ax_d, strips[0], ax_f]
    titles = [_head(ax, k) for k, ax in enumerate(heads)]

    _panel_a(ax_a, edu)
    _panel_b(ax_b, jun, ceiling)
    _panel_c(ax_c, surv)
    _panel_d(ax_d, idx, reporting)
    _panel_e(strips, pp, reporting)
    _panel_f(ax_f, deis, snss, g_all, g_hosp)

    _align_heads(fig, titles, heads)
    return fig


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name(f"{PLATE}_redraw.png")
    draw().savefig(out, dpi=141, facecolor="white")
    print("wrote", out)
