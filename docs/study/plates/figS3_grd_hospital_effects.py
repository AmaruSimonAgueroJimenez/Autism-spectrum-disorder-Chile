"""figS3 — heterogeneity across GRD hospitals, redrawn from the tracked tables.

The stored plate was drawn by `figS3()` in `study/pipeline/08a_figures_grd.py`, which reads two files
this repository does not carry: `study/outputs/tidy/hospital_effects.csv` (panels a and b) and
`study/outputs/tidy/grd_hospital_year.csv` (panels c, d, e and f). Both are ignored by `.gitignore`.
Every series they feed survives in published tables, so the six panels are redrawn here from those:

  (a) hospital fixed-effect RR, ranked, with 95% CI and depth-adjusted crosses
      `docs/study/corpus/tables/S_hospital_rates_2024.csv`
  (b) random-intercept posterior mean against the centred fixed effect, with the intercept SD
      the same table, plus `docs/study/data/models_summary.csv` for the SD and its interval
  (c) 2024 rate against the hospital's mean coding depth, with Spearman's rho
      `ST1_grd_hospital_panel.csv` (rate) and `S_hospital_rates_2024.csv` (coding depth)
  (d) distribution of hospital rates by year, with the fixed-panel median
      `docs/study/corpus/tables/ST1_grd_hospital_panel.csv`
  (e) the 33 fixed-panel hospitals above the 2024 median: 2019 against 2024
      the same table
  (f) the 32 fixed-panel hospitals at or below it                     the same table

Case definition `sin_rett` — the F84 family excluding Rett syndrome — in any diagnosis position, on
the observed annual panel of 65/65/65/65/68/72 hospitals. The unit is the GRD episode and nothing is
weighted or standardised: the rate is episodes with documented F84 per 100,000 GRD episodes OF THE
SAME HOSPITAL AND YEAR, so its denominator is hospital activity, never residents. The two hospital
effects are different estimators and are never substituted for one another: the RR of (a) is a
quasi-Poisson hospital fixed effect 2019–2024 (hospital indicators, common trend, log(episodes)
offset) expressed against the geometric mean of hospitals, and the RR of (b) is the posterior mean
of a Poisson random intercept fitted by Laplace/MAP.

Three fidelity caveats, none of them a missing series:

* Panels (a) and (b) read the RRs as the table prints them, rounded to two decimals, where the
  pipeline held the unrounded log effects. On an axis spanning about 4.4 log units the displacement
  is under 0.05 log units and invisible, but the redraw is not bit-identical; where two hospitals tie
  at two decimals their order in the ranking of (a) may differ from the original by one place.
* Panel (c) prints the Spearman statistic recomputed here from the published columns: rho = -0.062,
  which rounds to the -0.06 the stored plate prints, and p = 0.602, where the stored plate prints
  p = 0.596. Rounding the rate does not move the rank correlation at all (the rate and its published
  one-decimal string give the same rho to six figures), but the coding-depth column is published to
  two decimals and ten of the 72 hospitals then fall into five tied pairs, which is enough to move
  the p-value in the third decimal. The redrawn panel prints what this code computes, not the stored
  number.
* Panel (d) jitters its points with the pipeline's own seed, but the jitter is drawn in the row order
  of the table being read, and that order is not the order of the untracked file. The cloud has the
  same points and the same shape; individual dots sit at different horizontal offsets.

`_check_published()` runs before anything is drawn. It re-derives every hospital-year from ST1 and
compares the counts and the rate against E61, the hospital-by-year presentation table, checks the
2024 counts against S_hospital_rates_2024, checks the panel sizes and the annual totals against ST1's
own summary rows, and checks that the intercept SD of (b) is the row of models_summary.csv for the
random-intercept model on this case definition and panel.

The corpus is English only, so this plate is English only.
"""
import re
import sys
import textwrap
from pathlib import Path

_STUDY = Path(__file__).resolve().parents[1]          # docs/study, where figstyle lives
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
from scipy import stats

from figstyle import *   # noqa: F401,F403  — style, clean, num, BLUE, ORANGE, SKY, BAND, BASE, …

PLATE = "figS3_grd_hospital_effects"
SOURCES = [
    "docs/study/corpus/tables/S_hospital_rates_2024.csv",
    "docs/study/corpus/tables/ST1_grd_hospital_panel.csv",
    "docs/study/corpus/tables/E61_grd_hospital_year_full.csv",
    "docs/study/data/models_summary.csv",
]
RATES_2024, PANEL_TABLE, HOSPITAL_YEAR, MODELS = SOURCES
NOTE = ("Redraws the six panels of figure S3 — the ranked quasi-Poisson hospital fixed-effect RR with "
        "its depth-adjusted crosses, the Laplace/MAP random intercept against the centred fixed "
        "effect, the 2024 rate against hospital coding depth, the distribution of hospital rates by "
        "year and the 2019-versus-2024 dumbbells of the 65 fixed-panel hospitals — from the published "
        "hospital tables S3 and ST1, with the intercept SD read from models_summary.csv; case "
        "definition sin_rett, unweighted GRD episodes per 100,000 episodes of the same hospital-year.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
PER = 100_000.0
FIXED, NEW = BLUE, ORANGE                       # 2019-2024 fixed panel / hospitals added in 2023-2024
LINK, CROSS, RULE, IDENT = "#bbbbbb", "#555555", "#333333", "#888888"
BOX_FACE = "#dbe9f6"
MINUS = "−"                                # the corpus writes the typographic minus, not a hyphen
# Law 21.545 was published on 10 March 2023. The pipeline marks it at LAW_YEAR - 0.30 on an axis whose
# years are category centres, which is where the stored plate puts the dotted line. Context only.
LAW_X = 2023 - 0.30
PANDEMIC = [2020, 2021]                         # the shaded reporting disruption
SD_MODEL = "grd_hospital:sin_rett:observed:any:ri_none:2019-2024:random_intercept"
TITLES = {
    "a": "Hospital fixed effects (RR)",
    "b": "Random-intercept shrinkage",
    "c": "2024 rate versus hospital coding depth",
    "d": "Distribution of hospital rates by year",
    "e": "Rate by hospital, 2019 versus 2024: half with the higher 2024 rate",
    "f": "Rate by hospital, 2019 versus 2024: half with the lower 2024 rate",
}
RATE_AXIS = "F84 per 100,000 hospital episodes (log)"
RATE_AXIS_WRAPPED = "F84 per 100,000 hospital\nepisodes (log)"
DEPTH_AXIS = "Mean hospital coding depth,\n2024"
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)
LEGEND_KW = dict(frameon=True, framealpha=1.0, edgecolor="#cccccc", facecolor="white",
                 borderpad=0.25, fontsize=6.2)


# --------------------------------------------------------------- reading and parsing tracked tables
def _read(rel, **kw):
    """One tracked table, by its repository-relative path (the paths listed in SOURCES)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", **kw)


def _f(s):
    """'1,042.3' -> 1042.3 ; the presentation tables group thousands with commas."""
    return float(str(s).replace(",", "").replace(MINUS, "-").strip())


_CI = re.compile(r"^\s*([\d,.]+)\s*\(\s*([\d,.]+)\s*(?:to|[-–])\s*([\d,.]+)\s*\)\s*$")


def _ci(s):
    """'8.63 (7.71 to 9.66)' and '5,210.7 (4,771.6 to 5,679.4)' -> (value, lo, hi)."""
    m = _CI.match(str(s))
    if not m:
        raise ValueError(f"not a value with an interval: {s!r}")
    return tuple(_f(x) for x in m.groups())


_PAIR = re.compile(r"^\s*([\d,]+)\s*\(\s*([\d,]+)\s*\)\s*$")


def _pair(s):
    """ST1's cell '19,727 (38)' -> (GRD episodes, episodes with F84); '—' -> None."""
    s = str(s).strip()
    if s in {"—", "-", "", "nan"}:
        return None
    m = _PAIR.match(s)
    if not m:
        raise ValueError(f"not a hospital-year cell: {s!r}")
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


def _effects():
    """Table S3: the 72 hospitals observed in 2024, their 2024 rate, coding depth and three RRs.

    The fixed-effect RR and the random-intercept RR are different estimators of the same quantity and
    are kept in separate columns exactly as the table prints them; neither is substituted for the
    other anywhere in this module.
    """
    t = _read(RATES_2024)
    fe = [_ci(v) for v in t["Fixed-effect RR 2019–2024 vs hospital mean (95% CI)"]]
    dp = [_ci(v) for v in t["Depth-adjusted fixed-effect RR (95% CI)"]]
    ri = [_ci(v) for v in t["Random-intercept RR (95% posterior interval)"]]
    return pd.DataFrame({
        "code": t.Code.astype(int),
        "name": t.Hospital.astype(str),
        "fixed": t["Fixed panel of 65"].eq("Yes").to_numpy(),
        "episodes_2024": [_f(v) for v in t["GRD episodes 2024"]],
        "f84_2024": [_f(v) for v in t["Episodes with F84 2024"]],
        "rate_2024_published": [_ci(v)[0] for v in t["Rate per 100,000 episodes (exact 95% CI)"]],
        "depth": t["Mean coding depth 2024"].astype(float),
        "rr": [v[0] for v in fe], "rr_lo": [v[1] for v in fe], "rr_hi": [v[2] for v in fe],
        "rr_depth": [v[0] for v in dp],
        "ri": [v[0] for v in ri],
    })


def _hospital_years():
    """ST1 parsed into one row per hospital-year present: raw counts and the unrounded rate.

    ST1 stores the counts, not the rate, so the rate is computed here at full precision rather than
    read back from E61's one-decimal strings. The 32 absent hospital-years ('—') are dropped: absence
    from a year's GRD file is a state distinct from a zero count, and the stored plate plots neither.
    """
    t = _read(PANEL_TABLE)
    t = t[t.Code.notna()]                       # the five summary rows at the foot carry no code
    rows = []
    for _, r in t.iterrows():
        for year in YEARS:
            cell = _pair(r[str(year)])
            if cell is None:
                continue
            rows.append(dict(code=int(r.Code), name=str(r.Hospital),
                             fixed=r["Fixed panel of 65"] == "Yes", year=year,
                             episodes=cell[0], f84=cell[1]))
    h = pd.DataFrame(rows)
    h["rate"] = PER * h.f84 / h.episodes
    return h


def _summary_rows():
    """ST1's five foot rows, keyed by their label: totals and panel sizes by year."""
    t = _read(PANEL_TABLE)
    t = t[t.Code.isna()]
    return {str(r.Hospital): {str(y): str(r[str(y)]) for y in YEARS} for _, r in t.iterrows()}


def _intercept_sd():
    """Intercept SD of (b): the random-intercept row of models_summary for this variant and panel."""
    m = _read(MODELS)
    row = m[m.model_id == SD_MODEL]
    if len(row) != 1:
        raise AssertionError(f"{SD_MODEL}: expected one row in models_summary.csv, found {len(row)}")
    r = row.iloc[0]
    return float(r.re_sd), float(r.re_sd_lo), float(r.re_sd_hi)


# ---------------------------------------------------------------------- checking against the corpus
def _check_published(eff, h):
    """Compare everything this module will draw against the published tables, before drawing it.

    E61 prints '<episodes with F84>; <rate> (<lo>–<hi>)' per hospital-year and 'not reported' where
    the hospital is absent, so it checks the count, the rate and the observed panel at once; table S3
    checks the 2024 counts and the 2024 rate; ST1's own foot rows check the annual totals and the
    size of the observed and fixed panels.
    """
    bad = []

    # 1 — every hospital-year of ST1 against E61, both the count and the rate to its printed decimal
    e61 = _read(HOSPITAL_YEAR)
    codes = [int(str(s).split("—")[0].strip()) for s in e61["Hospital (GRD code — name)"]]
    e61 = e61.assign(code=codes).set_index("code")
    seen = 0
    for _, r in h.iterrows():
        cell = str(e61.loc[r.code, str(r.year)]).strip()
        if cell == "not reported":
            bad.append(f"{r.code} {r.year}: ST1 has {r.episodes} episodes, E61 says not reported")
            continue
        seen += 1
        count, rate = cell.split(";")
        if int(count.replace(",", "")) != r.f84:
            bad.append(f"{r.code} {r.year}: F84 {r.f84} vs E61 {count.strip()}")
        published = _ci(rate)[0]
        if round(r.rate, 1) != published:
            bad.append(f"{r.code} {r.year}: rate {r.rate:.3f} vs E61 {published}")
    absent = sum(str(e61.loc[c, str(y)]).strip() == "not reported"
                 for c in e61.index for y in YEARS)
    if seen + absent != len(e61) * len(YEARS):
        bad.append(f"E61 cells: {seen} reported + {absent} not reported != {len(e61) * len(YEARS)}")

    # 2 — the 2024 column of table S3 against the same hospital-years, counts and rate
    h24 = h[h.year == 2024].set_index("code")
    for _, r in eff.iterrows():
        if r.code not in h24.index:
            bad.append(f"{r.code}: in table S3 for 2024 but not in ST1")
            continue
        s = h24.loc[r.code]
        if (s.episodes, s.f84) != (r.episodes_2024, r.f84_2024):
            bad.append(f"{r.code} 2024: ST1 {(s.episodes, s.f84)} vs table S3 "
                       f"{(r.episodes_2024, r.f84_2024)}")
        if round(s.rate, 1) != r.rate_2024_published:
            bad.append(f"{r.code} 2024: rate {s.rate:.3f} vs table S3 {r.rate_2024_published}")
    if set(eff.code) != set(h24.index):
        bad.append("table S3 and ST1 disagree on which hospitals are observed in 2024")
    if not eff.set_index("code").fixed.reindex(h24.index).equals(h24.fixed):
        bad.append("table S3 and ST1 disagree on fixed-panel membership")

    # 3 — ST1's foot rows: annual totals, the observed panel and the fixed panel present each year
    foot = _summary_rows()
    for year in YEARS:
        y = h[h.year == year]
        total = _pair(foot["Total, observed annual panel"][str(year)])
        if (int(y.episodes.sum()), int(y.f84.sum())) != total:
            bad.append(f"{year}: observed totals {(int(y.episodes.sum()), int(y.f84.sum()))} "
                       f"vs ST1 {total}")
        fixed = y[y.fixed]
        total65 = _pair(foot["Total, fixed panel of 65 hospitals"][str(year)])
        if (int(fixed.episodes.sum()), int(fixed.f84.sum())) != total65:
            bad.append(f"{year}: fixed-panel totals "
                       f"{(int(fixed.episodes.sum()), int(fixed.f84.sum()))} vs ST1 {total65}")
        if len(y) != int(_f(foot["Observed hospitals (n)"][str(year)])):
            bad.append(f"{year}: {len(y)} hospitals observed vs ST1 "
                       f"{foot['Observed hospitals (n)'][str(year)]}")
        if len(fixed) != int(_f(foot["Fixed-panel hospitals present (n)"][str(year)])):
            bad.append(f"{year}: {len(fixed)} fixed-panel hospitals vs ST1 "
                       f"{foot['Fixed-panel hospitals present (n)'][str(year)]}")

    # 4 — the intercept SD annotated on (b) is the row of models_summary for this model
    sd, lo, hi = _intercept_sd()
    if not lo < sd < hi:
        bad.append(f"intercept SD {sd} outside its interval ({lo}; {hi})")

    if bad:
        raise AssertionError("redraw disagrees with the published tables:\n  " + "\n  ".join(bad))


# ---------------------------------------------------------------------------- style of the panels
PLATE_RC = {
    "font.size": 8.0, "axes.titlesize": 9.0, "axes.titleweight": "bold", "axes.labelsize": 8.0,
    "xtick.labelsize": 7.0, "ytick.labelsize": 7.0, "legend.fontsize": 7.0,
    "legend.title_fontsize": 7.0, "axes.linewidth": 0.7, "grid.linewidth": 0.45,
    "lines.linewidth": 1.3, "lines.markersize": 3.4, "patch.linewidth": 0.6,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7, "xtick.major.size": 2.2,
    "ytick.major.size": 2.2, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    "axes.labelpad": 2.0, "axes.titlepad": 3.0, "axes.titlelocation": "left",
    "legend.handlelength": 1.5, "legend.handletextpad": 0.5, "legend.labelspacing": 0.30,
    "legend.columnspacing": 0.9, "legend.borderpad": 0.3,
}


def _signed(v, dec):
    """A tick or a statistic in the corpus's convention: typographic minus, not a hyphen."""
    s = num(v, "en", dec)
    return MINUS + s[1:] if s.startswith("-") else s


def _log_axis(ax, which="y"):
    """Decade ticks with the 2 and 5 subdivisions, as the stored plate labels its log axes."""
    axis = ax.yaxis if which == "y" else ax.xaxis
    (ax.set_yscale if which == "y" else ax.set_xscale)("log")
    axis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0), numticks=12))
    axis.set_major_formatter(FuncFormatter(
        lambda v, p: num(v, "en", 0 if v >= 1 else (1 if v >= 0.1 else 2))))
    axis.set_minor_formatter(NullFormatter())


def _legend(ax, loc, handles=None, **kw):
    """The plate's legend: white box, thin grey edge, 6.2 pt, drawn over the series."""
    lg = ax.legend(handles=handles, loc=loc, **dict(LEGEND_KW, **kw)) if handles is not None \
        else ax.legend(loc=loc, **dict(LEGEND_KW, **kw))
    lg.set_zorder(8)
    lg.set_in_layout(False)
    return lg


def _dot(colour, label, ms=4.5):
    return Line2D([0], [0], marker="o", color="w", markerfacecolor=colour, markersize=ms, label=label)


_ABBR = [("Complejo Hospitalario ", "C.H. "), ("Complejo Asistencial ", "C.A. "),
         ("Hospital Clínico Metropolitano ", "H.C.M. "), ("Hospital Clínico Regional ", "H.C.R. "),
         ("Hospital Clínico de Niños ", "H. Niños "), ("Hospital de Niños ", "H. Niños "),
         ("Hospital Clínico ", "H.C. "), ("Hospital Provincial ", "H. Prov. "),
         ("Hospital Regional ", "H. Reg. "), ("Hospital Base ", "H. Base "),
         ("Hospital de Urgencia Asistencia Pública ", "H.U.A.P. "),
         ("Hospital Intercultural ", "H. Interc. "), ("Hospital ", "H. "),
         ("Instituto Nacional de Enfermedades Respiratorias y Cirugía Torácica",
          "Inst. Nac. Enf. Respiratorias"),
         ("Instituto ", "Inst. "), ("Doctor ", "Dr. "), ("Doctora ", "Dra. "),
         ("Monseñor ", "Mons. "), ("Presidente ", "Pdte. ")]


def _abbreviate(name, max_core=24):
    """The pipeline's hospital abbreviation: the establishment, elided, then its commune.

    The commune is the last element of the parenthesis, so 'Hospital Dr. Exequiel González Cortés
    (Santiago, San Miguel)' becomes 'H. Dr. Exequiel Gonzále… (San Miguel)' — the row labels of the
    stored plate's (e) and (f), which is the only place 24 characters fit.
    """
    name = str(name)
    m = re.search(r"\(([^)]*)\)", name)
    city = m.group(1).split(",")[-1].strip() if m else ""
    core = re.sub(r"\s*\([^)]*\)", "", name).strip()
    for a, b in _ABBR:
        core = core.replace(a, b)
    if len(core) > max_core:
        core = core[:max_core - 1].rstrip() + "…"
    return f"{core} ({city})" if city and city not in core else core


# ------------------------------------------------------------------------------------------ panels
def _panel_a(ax, eff):
    """(a) the quasi-Poisson hospital fixed effect, ranked, with its CI and the depth-adjusted cross.

    Ranked by the RR itself, as the pipeline ranks it; the x axis carries no ticks because the rank
    has no unit. The crosses are the same model with hospital-year coding depth added, never a
    different case definition or a different panel of hospitals.
    """
    fe = eff.sort_values(["rr", "rr_depth", "ri", "code"]).reset_index(drop=True)
    x = np.arange(len(fe))
    ax.errorbar(x, fe.rr, yerr=[fe.rr - fe.rr_lo, fe.rr_hi - fe.rr], fmt="none", ecolor="#999999",
                elinewidth=0.6, zorder=1)
    ax.scatter(x, fe.rr, c=[FIXED if v else NEW for v in fe.fixed], s=12, zorder=3,
               edgecolor="white", linewidth=0.35)
    ax.scatter(x, fe.rr_depth, marker="x", s=10, color=CROSS, zorder=4, linewidth=0.7)
    ax.axhline(1, color=RULE, ls="--", lw=0.9)
    _log_axis(ax, "y")
    ax.set_ylim(max(1e-3, fe.rr_lo.min() * 0.75), fe.rr_hi.max() * 12.0)
    ax.set_xticks([])
    ax.set_xlabel("Hospitals ranked")
    ax.set_ylabel("Rate ratio (log, 95% CI)")
    _legend(ax, "upper left", handles=[
        _dot(FIXED, f"Fixed panel 2019–2024 ({int(fe.fixed.sum())})"),
        _dot(NEW, f"Added in 2023–2024 ({int((~fe.fixed).sum())})"),
        Line2D([0], [0], marker="x", color=CROSS, lw=0, markersize=4.5,
               label="Adjusted for hospital-year\ncoding depth")])
    clean(ax, "both")


def _panel_b(ax, eff, sd):
    """(b) the random intercept against the centred fixed effect, both on the log scale.

    The published RRs are already expressed against the geometric mean of hospitals, so their logs
    are the centred effects the pipeline plots; shrinkage towards zero is what separates the points
    from the identity line, and it is largest for the smallest hospitals.
    """
    fixed_log, random_log = np.log(eff.rr.to_numpy()), np.log(eff.ri.to_numpy())
    ax.scatter(fixed_log, random_log, c=[FIXED if v else NEW for v in eff.fixed], s=13,
               edgecolor="white", linewidth=0.35, zorder=3)
    lim = [min(fixed_log.min(), random_log.min()) - 0.1, max(fixed_log.max(), random_log.max()) + 0.1]
    ax.plot(lim, lim, ls="--", color=IDENT, lw=0.9, label="Identity")
    ax.set_xlim(lim[0], lim[1])
    ax.set_ylim(lim[0], lim[1] + 0.45 * (lim[1] - lim[0]))   # a free band for the SD annotation
    ax.text(0.03, 0.97, f"Intercept SD = {num(sd[0], 'en', 2)}\n"
                        f"({num(sd[1], 'en', 2)}; {num(sd[2], 'en', 2)})",
            transform=ax.transAxes, fontsize=6.3, va="top", bbox=NOTE_BBOX, zorder=6)
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(FuncFormatter(lambda v, p: _signed(v, 1)))
    ax.set_xlabel("Centred fixed effect (log)")
    ax.set_ylabel("Random intercept, posterior mean (log)")
    _legend(ax, "lower right")
    clean(ax, "both")


def _panel_c(ax, eff, h):
    """(c) the 2024 rate against the hospital's mean coding depth, with Spearman's rho.

    The rate is recomputed from ST1's raw counts rather than read from a rounded string; the depth is
    the published two-decimal column, the only place it survives. An ecological association between
    two hospital-level summaries: it is neither causal nor a measure of quality.
    """
    h24 = h[h.year == 2024].merge(eff[["code", "depth"]], on="code", how="left")
    ok = h24[(h24.rate > 0) & h24.depth.notna()].merge(eff[["code", "fixed"]], on="code",
                                                       suffixes=("", "_e"))
    rho, p = stats.spearmanr(ok.depth, ok.rate)
    ax.scatter(ok.depth, ok.rate, c=[FIXED if v else NEW for v in ok.fixed], s=13,
               edgecolor="white", linewidth=0.35, zorder=3)
    _log_axis(ax, "y")
    ax.set_ylim(top=ok.rate.max() * 12.0)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p_: num(v, "en", 1)))
    ax.set_xlabel(DEPTH_AXIS)
    ax.set_ylabel(RATE_AXIS)
    ax.text(0.02, 0.985, textwrap.fill(f"Spearman ρ = {_signed(rho, 2)} "
                                       f"(p = {num(p, 'en', 3)}; n = {len(ok)})", 33),
            transform=ax.transAxes, fontsize=6.3, ha="left", va="top", color=RULE,
            bbox=NOTE_BBOX, linespacing=1.25, zorder=6)
    clean(ax, "both")
    return rho, p, len(ok)


def _panel_d(ax, h):
    """(d) the distribution of hospital rates within each year, with the fixed-panel median.

    Every observed hospital of the year is a point; the box is its median and quartiles over all
    hospitals observed that year, and the black line is the median of the 65 fixed-panel hospitals
    only, which is why it runs above the 2024 box median. Hospital-years with no episode with F84 —
    four of them, in 2021 and 2022 — cannot be placed on a log axis and are not drawn.
    """
    hh = h[h.rate > 0]
    data = [hh[hh.year == y].rate.to_numpy() for y in YEARS]
    ax.boxplot(data, positions=YEARS, widths=0.55, showfliers=False, patch_artist=True,
               boxprops=dict(facecolor=BOX_FACE, color=RULE, linewidth=0.6),
               medianprops=dict(color=ORANGE, lw=1.2), whiskerprops=dict(linewidth=0.6),
               capprops=dict(linewidth=0.6))
    rng = np.random.default_rng(20260904)                 # the pipeline's own seed for the jitter
    for year, vals in zip(YEARS, data):
        fixed = hh[hh.year == year].fixed.to_numpy()
        ax.scatter(year + rng.uniform(-0.18, 0.18, len(vals)), vals, s=4,
                   c=[FIXED if v else NEW for v in fixed], alpha=0.7, zorder=3, linewidths=0)
    median = [float(np.median(hh[(hh.year == y) & hh.fixed].rate)) for y in YEARS]
    ax.plot(YEARS, median, "-", color=RULE, lw=1.1, zorder=4)
    _log_axis(ax, "y")
    ax.set_ylim(max(0.5, hh.rate.min() * 0.3), hh.rate.max() * 12.0)
    ax.set_xticks(YEARS)
    ax.set_xticklabels([str(y) for y in YEARS])
    ax.tick_params(axis="x", labelrotation=45)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    ax.set_xlabel("Year")
    ax.set_ylabel(RATE_AXIS)
    for year in PANDEMIC:                                  # the 2020-2021 reporting disruption
        ax.axvspan(year - 0.5, year + 0.5, color="grey", alpha=0.12, zorder=0)
    ax.axvline(LAW_X, color="#444444", ls=":", lw=1.0, zorder=1)
    clean(ax, "both")
    return median


def _fixed_panel_pairs(h):
    """The 65 fixed-panel hospitals with their 2019 and 2024 rates, ascending by the 2024 rate."""
    p = h[h.fixed & h.year.isin([YEARS[0], YEARS[-1]])].pivot_table(
        index=["code", "name"], columns="year", values=["f84", "episodes"])
    full = pd.DataFrame({
        "name": [i[1] for i in p.index],
        "r0": (PER * p[("f84", YEARS[0])] / p[("episodes", YEARS[0])]).to_numpy(),
        "r1": (PER * p[("f84", YEARS[-1])] / p[("episodes", YEARS[-1])]).to_numpy(),
    }).sort_values(["r1", "r0", "name"]).reset_index(drop=True)
    return full


def _panel_ef(ax, full, half, show_xlabel=True):
    """(e) and (f) — one row per fixed-panel hospital, its 2019 rate joined to its 2024 rate.

    Sixty-five rows do not fit in one 62 mm cell, so the pipeline splits the list at the median of
    the 2024 rate and gives each half its own panel: 'top' is the 33 hospitals at or above the median
    and 'bottom' the 32 below it, so no hospital is dropped and every name stays legible. Both halves
    share the x limits of the whole list, so the two panels can be read against each other.
    """
    floor = max(1.0, float(np.nanmin(full.r0[full.r0 > 0])) * 0.6)
    cut = len(full) // 2
    df = (full.iloc[cut:] if half == "top" else full.iloc[:cut]).reset_index(drop=True)
    for i, row in df.iterrows():
        x0 = row.r0 if row.r0 > 0 else floor     # a hospital with no F84 in 2019 sits on the floor
        ax.plot([x0, row.r1], [i, i], color=LINK, lw=1.6, zorder=1)
        ax.scatter(x0, i, s=13, color=SKY if row.r0 > 0 else "white", edgecolor=SKY, zorder=3,
                   marker="o" if row.r0 > 0 else "x", linewidth=0.9)
        ax.scatter(row.r1, i, s=13, color=ORANGE, zorder=4, edgecolor="white", linewidth=0.4)
    handles = [_dot(SKY, str(YEARS[0])), _dot(ORANGE, str(YEARS[-1]))]
    if (df.r0 <= 0).any():                       # never true on this data: no fixed-panel zero in 2019
        handles.append(Line2D([0], [0], marker="x", color=SKY, lw=0, markersize=4.5,
                              label="0 in 2019 (no F84 episodes)"))
    _legend(ax, "lower right", handles=handles)
    ax.set_yticks(np.arange(len(df)))
    ax.set_yticklabels([_abbreviate(n) for n in df.name], fontsize=6.2)
    _log_axis(ax, "x")
    # decades only: with the 2 and 5 subdivisions the six numbers printed on top of one another
    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=8))
    ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(2.0, 5.0), numticks=16))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlim(floor * 0.8, full.r1.max() * 6.0)
    ax.set_ylim(-1, len(df))
    if show_xlabel:
        ax.set_xlabel(RATE_AXIS_WRAPPED)
    clean(ax, "x")
    ax.tick_params(axis="y", length=0)
    return df


# -------------------------------------------------------------------------------------------- draw
def draw():
    """Draw the six panels of figure S3 and hand back the figure."""
    eff = _effects()
    h = _hospital_years()
    _check_published(eff, h)
    sd = _intercept_sd()

    style()
    plt.rcParams.update(PLATE_RC)
    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    ax = axes.ravel()

    _panel_a(ax[0], eff)
    _panel_b(ax[1], eff, sd)
    _panel_c(ax[2], eff, h)
    _panel_d(ax[3], h)
    full = _fixed_panel_pairs(h)
    _panel_ef(ax[4], full, "top")
    _panel_ef(ax[5], full, "bottom")

    # Titles last, and moved to the left edge of their own cell once the layout is frozen: the plate
    # anchors them to the cell, not to the axes, which in this plate start far to the right because
    # the hospital names of (e) and (f) set the left margin of both columns.
    titles = []
    for a, key in zip(ax, "abcdef"):
        wrapped = textwrap.fill(f"({key}) {TITLES[key]}", 44)
        titles.append(a.set_title(wrapped, loc="left", fontsize=9, fontweight="bold", pad=3.0,
                                  linespacing=1.15))
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    margin = 2.0 / 180.0                      # 2 mm left margin of the cell
    for i, (a, title) in enumerate(zip(ax, titles)):
        pos = a.get_position()
        title.set_x((margin + (i % 2) * 0.5 - pos.x0) / pos.width)
    return fig


if __name__ == "__main__":
    _eff, _h = _effects(), _hospital_years()
    _check_published(_eff, _h)
    print(f"ok  {len(_eff)} hospitals in 2024, {len(_h)} hospital-years, "
          f"{int(_h.fixed.sum() / len(YEARS))} in the fixed panel")
    fig = draw()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "qa" / f"{PLATE}_redraw.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor="white")
    print("wrote", out)
