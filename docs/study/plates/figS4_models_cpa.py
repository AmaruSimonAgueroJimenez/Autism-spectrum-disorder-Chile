"""Figure S4 — quasi-Poisson models of administrative recognition of autism (F84 without Rett).

Redraw of the stored plate `docs/study/corpus/figures/figS4_models_cpa.jpg`. The original was drawn
by `study/pipeline/06_models.py` from `study/outputs/tidy/models_fitted.csv`, which is not in this
repository (`study/outputs/` is ignored); everything else it plotted is tracked. The six panels are
rebuilt here from five tracked tables:

* `docs/study/data/grd_year_summary.csv` — the annual GRD counts, their denominators and their exact
  Poisson limits, by variant, panel, activity and diagnostic position;
* `docs/study/corpus/tables/ST11a_deis_annual.csv` — the DEIS annual discharges, the F84 principal
  count and its published rate with exact 95% CI;
* `docs/study/data/models_summary.csv` — the APC and Wald 95% CI of every fitted model, by model id;
* `docs/study/data/models_population_rates.csv` — crude (exact Poisson) and WHO-standardised
  (Fay–Feuer) rates per 100,000 INE population, by sex and year;
* `docs/study/data/models_convergence_index.csv` — the 2021 = 100 indices of the six series.

The one thing that is not read but recomputed: the FITTED lines and their 95% bands in panels (a)
and (b). `models_fitted.csv` is not tracked, so the four GRD fits and the DEIS fit are **refitted
here from the tracked annual counts and offsets**, with the specification the pipeline used — a
Poisson GLM with a log(denominator) offset, the year centred on the first year of the window, and
the Pearson scale (`scale='X2'`, i.e. quasi-Poisson) — and the band taken from the delta-method
standard error of the linear predictor. The refit is not an approximation of the published fit: it
reproduces `models_summary.csv` to every digit it stores (checked in `_check()` below, and again in
the QA numbers reported with this module), so the lines and bands drawn here are the stored ones.

Estimators kept exactly as the original drew them. Panels (a) and (b) are rates per 100,000 GRD
EPISODES (and, for DEIS, per 100,000 DISCHARGES), never per resident. Panel (d) plots both the crude
rate and the WHO-standardised rate per 100,000 INE residents, read from the table, never recomputed.
Panel (e) is an INDEX with 2021 = 100 on a log axis — the six series have different units and
denominators and are not comparable levels. Panels (c) and (f) take `apc`, `apc_lo` and `apc_hi`
straight from `models_summary.csv` by exact model id, in the order the original listed them, and the
colour encodes the estimand. No panel uses survey weights.

Case definition: the F84 family excluding Rett syndrome (`sin_rett`), the variant of the stored
plate — 2,334 GRD episodes with F84 in any position in 2019, not the 2,385 of `con_rett`. The panel
(f) rows for REM A05 and P6 keep the pipeline's `strict_autism` code definition where the pipeline
used it (those model ids are literals of the original figure), and the one `sin_rett` A05 row is the
row the plate labels "A05 family /INE pop.".
"""
import re
import textwrap

import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.lines import Line2D
from scipy import stats

from figstyle import *

PLATE = "figS4_models_cpa"
SOURCES = [
    "docs/study/data/grd_year_summary.csv",
    "docs/study/corpus/tables/ST11a_deis_annual.csv",
    "docs/study/data/models_summary.csv",
    "docs/study/data/models_population_rates.csv",
    "docs/study/data/models_convergence_index.csv",
]
NOTE = ("Redraws the six panels of Figure S4 — the GRD episode rate observed and fitted, principal "
        "F84 in GRD and DEIS, the fifteen-model GRD APC forest, crude and WHO-standardised "
        "population rates by sex, the 2021 = 100 convergence indices and the sixteen-model "
        "REM/education/DEIS APC forest — from the tracked annual tables and models_summary, with the "
        "quasi-Poisson fits of panels (a) and (b) refitted from the same annual counts and offsets "
        "because models_fitted.csv is not in the repository.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repo root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
VARIANT = "sin_rett"                            # F84 family excluding Rett, the stored plate's variant
FAMILY_VARIANTS = ("con_rett", "sin_rett")      # the two "family" variants of the pipeline
YEARS_GRD = list(range(2019, 2025))
DISRUPTION_YEARS = (2020, 2021)
LAW_X = 2023 - 0.35             # the pipeline draws Law 21.545 at LAW_YEAR (= 2023) - 0.35
PER = 100_000.0
Z = float(stats.norm.ppf(0.975))

# Type sizes of the plate norm (180 x 245 mm, one plate per page, nothing under 6 pt).
FS_BASE, FS_TITLE, FS_TICK, FS_MIN = 8.0, 9.0, 7.0, 6.0
SEXCOL = {"HOMBRE": BLUE, "MUJER": ORANGE, "TOTAL": "#333333"}
SEXLAB = {"HOMBRE": "Males", "MUJER": "Females", "TOTAL": "Both sexes"}

TITLES = {
    "a": "GRD: episode rate (observed and fitted)",
    "b": "Principal F84: GRD and DEIS",
    "c": "GRD: APC across sensitivities (quasi-Poisson)",
    "d": "GRD per 100,000 pop.: crude and standardised",
    "e": "Convergence indices (2021 = 100)",
    "f": "REM, education and DEIS: APC (quasi-Poisson)",
}
APC_AXIS = "Annual percent change (%) and 95% CI"
PANDEMIC = "Reporting\ndisruption 2020–21"
LAW = "Law 21.545\n(context)"
CTX_GREY, LAW_GREY = "#555555", "#444444"

# --------------------------------------------------------------------------- model id lists
# The two forests list their models as literals, in the order the original printed them
# (06_models.py MAIN_IDS["grd"][:11] plus four hospital-year / population models for panel c).
IDS_C = [f"grd_rate:{VARIANT}:observed:all:any:none:2019-2024",
         f"grd_rate:{VARIANT}:observed:all:any:depth:2019-2024",
         f"grd_rate:{VARIANT}:observed:all:any:disruption:2019-2024",
         f"grd_rate:{VARIANT}:observed:all:any:depth_disruption:2019-2024",
         f"grd_rate:{VARIANT}:observed:all:any:none:2021-2024",
         f"grd_rate:{VARIANT}:fixed65:all:any:none:2019-2024",
         f"grd_rate:{VARIANT}:fixed65:all:any:depth:2019-2024",
         f"grd_rate:{VARIANT}:observed:hospitalisation:any:none:2019-2024",
         f"grd_rate:{VARIANT}:observed:all:principal:none:2019-2024",
         f"grd_rate:{VARIANT}:fixed65:all:principal:none:2019-2024",
         f"grd_rate:{VARIANT}:observed:all:principal:none:2021-2024",
         f"grd_hospital:{VARIANT}:observed:any:none:2019-2024:model",
         f"grd_hospital:{VARIANT}:observed:any:depth:2019-2024:model",
         f"grd_hospital:{VARIANT}:observed:any:ri_none:2019-2024:random_intercept",
         f"grd_pop:{VARIANT}:any:TOTAL:age_adjusted:2019-2024"]

IDS_F = ["a05_entry:strict_autism:pop:none:2021-2025",
         "a05_entry:strict_autism:estab:none:2021-2025",
         "a05_entry:strict_autism:stable_pop:none:2021-2025",
         "a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025",
         f"a05_entry:{VARIANT}:pop:none:2021-2025",
         "p2_dec:none:2019-2025",
         "p2_dec:estab:2019-2025",
         "p2_dec:none_disruption:2019-2025",
         "p2_dec:none:2021-2025",
         "p2_dec:naneas:2023-2025",
         "p6_primary:strict_autism:none:2021-2025",
         "p6_primary:strict_autism:estab:2021-2025",
         "p6_specialty:strict_autism:none:2021-2025",
         "pie_harmonised:none:2019-2025",
         "pie_harmonised:none:2019-2023",
         f"deis_principal:{VARIANT}:none:2019-2024"]

# The label of a model row, built from its own summary columns (06_models.py `_short`).
PANEL_LBL = {"panel_observed": "obs.", "panel_fixed65": "fixed 65", "panel_stable": "stable panel",
             "panel_all_estab": "", "panel_national": ""}
ACT_LBL = {"act_all": "all", "act_hospitalisation": "hosp.", "act_na": ""}
POS_LBL = {"pos_any": "any", "pos_principal": "princ.", "pos_na": ""}
COV_LBL = {"cov_none": "", "cov_depth": "+depth", "cov_disruption": "+disruption",
           "cov_depth_disruption": "+depth+disr.", "cov_age": "age-adj.", "cov_disruption_2021": "+disr. 2021",
           "cov_hospital_fe": "hospital FE", "cov_hospital_fe_depth": "hospital FE +depth",
           "cov_hospital_fe_disruption": "hospital FE +disr.", "cov_hospital_ri": "hospital RI",
           "cov_hospital_ri_depth": "hospital RI +depth"}
OFF_LBL = {"off_episodes": "", "off_hosp_episodes": "", "off_pop": "/INE pop.", "off_estab": "/estab.",
           "off_none": "count", "off_naneas": "/100 NANEAS", "off_discharges": ""}
PREFIX_F = {"est_a05": "A05 ", "est_a05_pop": "A05 ", "est_p2": "P2 ", "est_p2_naneas": "P2 ",
            "est_p6_primary": "P6 APS ", "est_p6_specialty": "P6 spec. ", "est_pie": "PIE ", "est_deis": "DEIS "}
COLOUR_F = {"est_a05": GREEN, "est_a05_pop": GREEN, "est_p2": PINK, "est_p2_naneas": PINK,
            "est_p6_primary": GOLD, "est_p6_specialty": GOLD, "est_pie": SKY, "est_deis": YELLOW}

# Panel (e): the six series of the convergence index, in the order of the plate's legend.
CONV = [("grd_any_rate", "GRD F84 any position (rate/episodes)", "o", OKABE[0]),
        ("deis_principal_rate", "DEIS F84 principal (rate/discharges)", "^", OKABE[1]),
        ("a05_strict_entries", "A05 autism entries (flow)", "s", OKABE[2]),
        ("p2_december_stock", "P2 ASD December (stock)", "D", OKABE[3]),
        ("p6_primary_strict_stock", "P6 primary autism December (stock)", "v", OKABE[4]),
        ("pie_harmonised", "Harmonised PIE (school stock)", "P", OKABE[5])]


# --------------------------------------------------------------------------- reading the tables
def _table(rel, **kw):
    """A tracked table, read from the repository root (the presentation CSVs carry a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", **kw)


def _int(s):
    """'1,667,180' -> 1667180."""
    return int(str(s).replace(",", "").replace(" ", "").strip())


_CI = re.compile(r"^\s*([\d.]+)\s*\(\s*([\d.]+)\s*to\s*([\d.]+)\s*\)")


def _rate_ci(cell):
    """'18.2 (16.2 to 20.4)' -> (18.2, 16.2, 20.4)."""
    m = _CI.match(str(cell))
    if not m:
        raise ValueError(f"not a rate with CI: {cell!r}")
    return tuple(float(g) for g in m.groups())


def grd_annual(panel, position, activity="all", variant=VARIANT):
    """One annual GRD series: count, denominator, observed rate with exact Poisson limits, hospitals."""
    g = _table(SOURCES[0])
    d = g[(g.variant == variant) & (g.panel == panel) & (g.activity == activity)
          & (g.position == position)].sort_values("year")
    if len(d) != len(YEARS_GRD):
        raise ValueError(f"{panel}/{activity}/{position}: {len(d)} years, expected {len(YEARS_GRD)}")
    return pd.DataFrame({"year": d.year.to_numpy(float),
                         "count": d.n_episodes_f84.to_numpy(float),
                         "denominator": d.n_episodes_total_same_panel_activity.to_numpy(float),
                         "observed_rate": d.rate_per_100k_episodes.to_numpy(float),
                         "observed_lo": d.rate_lo.to_numpy(float),
                         "observed_hi": d.rate_hi.to_numpy(float),
                         "reporting_n": d.hospitals_n.to_numpy(float)})


def deis_annual():
    """The DEIS annual series: F84 in DIAG1 over all discharges, with the published rate and CI.

    ST11a prints one canonical row per year plus a 15-column layout check for 2021; only the
    canonical rows are the series (the check row repeats 2021 and would double it)."""
    t = _table(SOURCES[1], dtype=str)
    t = t[t["File layout"] == "canonical"].copy()
    t["year"] = t["Year"].map(int)
    t = t.sort_values("year")
    den = t["DEIS discharges (all establishments)"].map(_int).to_numpy(float)
    cnt = t["F84 in DIAG1 (principal)"].map(_int).to_numpy(float)
    ci = np.array([_rate_ci(c) for c in t["Principal F84 per 100,000 discharges (exact 95% CI)"]])
    if not np.allclose(np.round(PER * cnt / den, 1), ci[:, 0]):
        raise ValueError("ST11a rate does not equal count / discharges")
    return pd.DataFrame({"year": t.year.to_numpy(float), "count": cnt, "denominator": den,
                         "observed_rate": ci[:, 0], "observed_lo": ci[:, 1], "observed_hi": ci[:, 2],
                         "reporting_n": np.nan})


def summary():
    """models_summary.csv keyed by model id."""
    return _table(SOURCES[2]).set_index("model_id")


def population_rates():
    """Crude and WHO-standardised rates per 100,000 INE residents, variant `sin_rett`, any position."""
    p = _table(SOURCES[3])
    return p[(p.variant == VARIANT) & (p.position == "any")].sort_values(["sex", "year"])


def convergence():
    """The 2021 = 100 indices of the plate's variant."""
    c = _table(SOURCES[4])
    return c[(c.variant == VARIANT) & (c.index_base_year == 2021)]


# --------------------------------------------------------------------------- the refitted models
def quasi_poisson(years, counts, denominator):
    """The pipeline's trend model: Poisson GLM, log(denominator) offset, year centred on the first.

    `scale='X2'` is the quasi-Poisson step — the Pearson scale multiplies the covariance, so the
    Wald interval of the trend and the band of the fitted rate both widen with the overdispersion.
    Returns the APC with its 95% CI and the fitted rate per `PER` with its 95% band.
    """
    years = np.asarray(years, dtype=float)
    X = pd.DataFrame({"const": 1.0, "t": years - years.min()})
    off = np.log(np.asarray(denominator, dtype=float))
    fit = sm.GLM(np.asarray(counts, dtype=float), X, family=sm.families.Poisson(), offset=off).fit(scale="X2")
    beta, se = float(fit.params["t"]), float(fit.bse["t"])
    Xv = X.to_numpy(float)
    lp = Xv @ np.asarray(fit.params, dtype=float)
    se_lp = np.sqrt(np.einsum("ij,jk,ik->i", Xv, np.asarray(fit.cov_params(), dtype=float), Xv))
    return dict(apc=100 * (np.exp(beta) - 1),
                apc_lo=100 * (np.exp(beta - Z * se) - 1),
                apc_hi=100 * (np.exp(beta + Z * se) - 1),
                fitted_rate=PER * np.exp(lp),
                fitted_lo=PER * np.exp(lp - Z * se_lp),
                fitted_hi=PER * np.exp(lp + Z * se_lp))


def fitted(series):
    """`series` (from `grd_annual` or `deis_annual`) with the refitted rate and band attached."""
    f = quasi_poisson(series.year, series["count"], series.denominator)
    return series.assign(fitted_rate=f["fitted_rate"], fitted_lo=f["fitted_lo"], fitted_hi=f["fitted_hi"]), f


def _check(sm_, fits):
    """The refit has to be the published fit: its APC and CI must equal models_summary to 1e-9."""
    for mid, f in fits.items():
        r = sm_.loc[mid]
        for k in ("apc", "apc_lo", "apc_hi"):
            if abs(f[k] - float(r[k])) > 1e-9:
                raise ValueError(f"{mid}: refitted {k} {f[k]!r} != stored {float(r[k])!r}")


# --------------------------------------------------------------------------- panel furniture
def _shade(ax, years=DISRUPTION_YEARS):
    for y in years:
        ax.axvspan(y - 0.5, y + 0.5, color="grey", alpha=0.12, lw=0, zorder=0)


def _pandemic(ax, y, va="center", x=2020.5, size=7.5):
    ax.text(x, y, PANDEMIC, transform=ax.get_xaxis_transform(), ha="center", va=va,
            fontsize=size, color=CTX_GREY, linespacing=1.05)


def _law(ax, y, va="center", ha="left", size=7.5):
    ax.axvline(LAW_X, color=LAW_GREY, ls=":", lw=1.2, zorder=1)
    ax.text(LAW_X + (0.06 if ha == "left" else -0.06), y, LAW, transform=ax.get_xaxis_transform(),
            ha=ha, va=va, fontsize=size, color=LAW_GREY, linespacing=1.05)


def _plot_fit(ax, d, color, label, marker="o", ls="-", offset=0.0):
    """One series of panels (a) and (b): observed with its exact CI, the fit, and the fitted band.

    One legend entry per series, as the original: the marker is the observation and the line the
    fit, and the caption says so. `errorbar` is given both a marker and a linestyle, so the observed
    points are joined by the series' own line under the heavier fitted line.
    """
    x = d.year.to_numpy(float) + offset
    ax.errorbar(x, d.observed_rate,
                yerr=[d.observed_rate - d.observed_lo, d.observed_hi - d.observed_rate],
                fmt=marker, color=color, capsize=2.5, markersize=5.5, lw=1.4, ls=ls,
                label=label, zorder=3)
    ax.plot(x, d.fitted_rate, ls=ls, color=color, lw=2.0, zorder=2)
    ax.fill_between(x, d.fitted_lo, d.fitted_hi, color=color, alpha=0.13, lw=0, zorder=1)


def _legend(ax, loc="upper left", **kw):
    lg = ax.legend(loc=loc, fontsize=FS_MIN + 0.2, frameon=True, framealpha=0.82, edgecolor="none",
                   facecolor="white", borderpad=0.25, handlelength=1.5, handletextpad=0.5,
                   labelspacing=0.30, **kw)
    lg.set_zorder(6)
    lg.set_in_layout(False)
    return lg


# --------------------------------------------------------------------------- the two forests
def short_label(r):
    """The one-line label of a model row, from its own summary columns."""
    parts = [PANEL_LBL[r.panel], ACT_LBL[r.activity], POS_LBL[r.position], COV_LBL[r.covariates],
             OFF_LBL[r.denominator_offset]]
    if r.model_family == "fam_qp_fe_cluster":
        parts.append("robust SE")
    y0, y1 = str(r.years).split("-")
    return " · ".join([p for p in parts if p]) + f" · {y0}–{y1[2:]}"


def strip_period(rows):
    """Take the period shared by most rows out of the labels and return it for the axis label.

    Fifteen rows leave about 10 pt between them and a two-line label measures 15, so the label has
    to stay on one line; the period most rows share is declared once, on the x axis.
    """
    tails = [str(r[0]).rsplit(" · ", 1)[-1] for r in rows]
    common = [t for t in dict.fromkeys(tails) if tails.count(t) > 1 and any(c.isdigit() for c in t)]
    if not common:
        return rows, ""
    modal = max(common, key=tails.count)
    if tails.count(modal) < max(2, len(rows) // 2):
        return rows, ""
    out = []
    for r, tail in zip(rows, tails):
        lab = str(r[0])
        if tail == modal and " · " in lab:
            lab = lab.rsplit(" · ", 1)[0]
        out.append((lab,) + tuple(r[1:]))
    return out, f"unless stated, {modal}"


def forest(ax, rows, key=None, ref=0.0):
    """A forest of specifications: label on the y axis, value in a reserved column on the right."""
    rows, period = strip_period(rows)
    n = len(rows)
    values = []
    for i, (lab, e, lo, hi, col) in enumerate(rows):
        y = n - 1 - i
        ax.plot([lo, hi], [y, y], color=col, lw=2.0, zorder=2)
        ax.scatter(e, y, s=40, color=col, zorder=3, edgecolor="white", linewidth=1)
        values.append(ax.text(max(hi, ref) + 1.5, y, f"{e:.1f} ({lo:.1f}; {hi:.1f})",
                              va="center", ha="left", fontsize=FS_MIN, color="#333333"))
    ax.axvline(ref, color="#888888", ls="--", lw=1.0, zorder=0)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=FS_MIN)
    label = APC_AXIS if not period else f"{APC_AXIS} · {period}"
    ax.set_xlabel(textwrap.fill(label, 31), fontsize=FS_BASE, linespacing=1.15)
    finite = [v for r in rows for v in (r[2], r[3])] + [ref]
    lo_, hi_ = min(finite), max(finite)
    ax.set_xlim(lo_ - 0.05 * (hi_ - lo_ + 1), hi_ + 0.55 * (hi_ - lo_ + 1))
    ax._value_column = dict(texts=values, lo=float(lo_), hi=float(hi_))
    ax.margins(y=0.05)
    if key:
        # The colour key goes in a band reserved under the last row, never floating over the rows:
        # a floating legend covered the last three intervals and pushed their values off their row.
        ax.set_ylim(-0.6 - 1.25 * len(key), n - 1 + 0.6)
        lg = ax.legend([Line2D([], [], color=c, lw=2.4) for c, _ in key], [t for _, t in key],
                       loc="lower left", fontsize=FS_MIN, ncol=1, frameon=True, framealpha=0.85,
                       edgecolor="none", facecolor="white", borderpad=0.25, handlelength=1.4,
                       handletextpad=0.5, labelspacing=0.25)
        lg.set_zorder(6)
        lg.set_in_layout(False)


def value_column(fig):
    """Reserve, to the right of each forest, the measured column its values occupy.

    Each row used to write its value 1.5 units from the top of ITS OWN interval; on a wide interval
    that start falls so far right that the label leaves the panel and lands back on top of its own
    bar. Here the widest label is measured with the layout already resolved, the axis is widened by
    exactly that column, and every label is aligned in it.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax in fig.axes:
        info = getattr(ax, "_value_column", None)
        if not info:
            continue
        width = max(t.get_window_extent(r).width for t in info["texts"])
        axw = float(ax.bbox.width)
        frac = min(0.60, (width + 0.05 * axw) / axw)        # the value column, plus a breath
        lo_, hi_ = info["lo"], info["hi"]
        left = lo_ - 0.05 * (hi_ - lo_ + 1.0)
        right = left + (hi_ - left) / max(1e-6, 1.0 - frac)
        ax.set_xlim(left, right)
        x_lab = left + (1.0 - frac + 0.012) * (right - left)
        for t in info["texts"]:
            t.set_x(x_lab)


# --------------------------------------------------------------------------- the plate
def draw():
    style()
    plt.rcParams.update({
        "font.size": FS_BASE, "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK,
        "ytick.labelsize": FS_TICK, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlepad": 4.0, "axes.linewidth": 0.7,
        "grid.linewidth": 0.45, "lines.linewidth": 1.3, "xtick.major.size": 2.2,
        "ytick.major.size": 2.2, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5, "axes.labelpad": 2.0,
    })
    sm_ = summary()

    obs_any, f_obs_any = fitted(grd_annual("observed", "any"))
    fix_any, f_fix_any = fitted(grd_annual("fixed65", "any"))
    obs_pri, f_obs_pri = fitted(grd_annual("observed", "principal"))
    fix_pri, f_fix_pri = fitted(grd_annual("fixed65", "principal"))
    deis, f_deis = fitted(deis_annual())
    _check(sm_, {f"grd_rate:{VARIANT}:observed:all:any:none:2019-2024": f_obs_any,
                 f"grd_rate:{VARIANT}:fixed65:all:any:none:2019-2024": f_fix_any,
                 f"grd_rate:{VARIANT}:observed:all:principal:none:2019-2024": f_obs_pri,
                 f"grd_rate:{VARIANT}:fixed65:all:principal:none:2019-2024": f_fix_pri,
                 f"deis_principal:{VARIANT}:none:2019-2024": f_deis})

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.05, h_pad=0.04, wspace=0.05, hspace=0.06, rect=(0, 0, 1, 0.988))
    ax = axes.ravel()
    a, b, c, d, e, f = ax

    # (a) GRD any position: observed and fitted, observed annual panel and fixed panel of 65 --------
    _plot_fit(a, obs_any, BLUE, "Observed panel", "o", "-")
    _plot_fit(a, fix_any, ORANGE, "Fixed panel 65", "s", "--", offset=0.08)
    _shade(a)
    _pandemic(a, 0.55)
    _law(a, 0.03, va="bottom")
    # The n of hospitals goes UNDER ITS YEAR, not floating over the series: the observed panel has
    # 65 hospitals in 2019 and in 2020 and the two labels printed on top of each other.
    a.set_xticks(YEARS_GRD)
    a.set_xticklabels([f"{y}\nn={int(n)}" for y, n in zip(YEARS_GRD, obs_any.reporting_n)],
                      fontsize=FS_MIN + 0.2)
    a.set_xlabel("Year (n = reporting GRD hospitals)")
    a.set_ylabel("Episodes with F84 per 100,000 GRD episodes")
    a.set_ylim(0, float(obs_any.observed_hi.max()) * 1.45)
    a.yaxis.set_major_formatter(thousands("en"))
    _legend(a, loc="upper right")
    clean(a, "both")

    # (b) principal F84 in GRD (observed and fixed) and DEIS principal ------------------------------
    _plot_fit(b, obs_pri, BLUE, "GRD, observed panel", "o", "-")
    _plot_fit(b, fix_pri, ORANGE, "GRD, fixed panel 65", "s", "--", offset=0.08)
    _plot_fit(b, deis, GREEN, "DEIS principal", "^", "-.", offset=-0.08)
    _shade(b)
    _pandemic(b, 0.03, va="bottom")
    # Both notes sit at the foot of this panel; the stored plate carries the Law note the height of
    # one line higher, which is where the pipeline's decongestion engine left it.
    _law(b, 0.115, va="bottom")
    b.set_xticks(YEARS_GRD)
    b.set_xlabel("Year")
    b.set_ylabel("Principal F84 per 100,000 episodes / discharges")
    b.set_ylim(0, float(obs_pri.observed_hi.max()) * 1.55)
    _legend(b, loc="upper right")
    clean(b, "both")

    # (c) forest of the GRD specifications ---------------------------------------------------------
    rows = []
    for mid in IDS_C:
        r = sm_.loc[mid]
        if r.estimand == "est_grd_rate" and r.position == "pos_any":
            col = BLUE
        elif r.position == "pos_principal":
            col = ORANGE
        elif r.estimand == "est_grd_hospital":
            col = GREEN
        else:
            col = PINK
        rows.append((short_label(r), float(r.apc), float(r.apc_lo), float(r.apc_hi), col))
    # The estimand used to be spelled out in front of EVERY label and took 40 pt of the 90 mm cell:
    # here the colour says it and the key translates it once, in a band of its own under the rows.
    forest(c, rows, key=[(BLUE, "rate per episodes · any position"),
                         (ORANGE, "rate per episodes · principal"),
                         (GREEN, "hospital-year"),
                         (PINK, "per 100,000 population")])
    clean(c, "x")

    # (d) per 100,000 INE population: crude and WHO-standardised, by sex ----------------------------
    pv = population_rates()
    for sex in ("HOMBRE", "MUJER", "TOTAL"):
        s = pv[pv.sex == sex].sort_values("year")
        d.plot(s.year, s.crude, "o:", color=SEXCOL[sex], lw=1.4, markersize=5,
               label=f"{SEXLAB[sex]} · crude")
        d.plot(s.year, s.asr, "s-", color=SEXCOL[sex], lw=2.0, markersize=5,
               label=f"{SEXLAB[sex]} · WHO-standardised")
        d.fill_between(s.year, s.asr_lo, s.asr_hi, color=SEXCOL[sex], alpha=0.12, lw=0)
    _shade(d)
    _pandemic(d, 0.55)
    # The six-entry legend takes the top band of this panel, so the Law mark goes to mid height and
    # is written to the LEFT of its line: after 2023 every series is climbing through that corner.
    _law(d, 0.465, ha="right")
    d.set_xticks(YEARS_GRD)
    d.set_xlabel("Year")
    d.set_ylabel("Episodes with F84 per 100,000 population")
    d.set_ylim(0, float(pv.asr_hi.max()) * 1.5)
    _legend(d, loc="upper left", ncol=1)
    clean(d, "both")

    # (e) convergence indices, 2021 = 100, log scale ------------------------------------------------
    cv = convergence()
    e.set_yscale("log")
    e.set_xlim(2020.6, 2025.9)              # a column reserved on the right for each series' end value
    ends = []
    for series, label, marker, col in CONV:
        z = cv[(cv.series == series) & (cv.year >= 2021)].sort_values("year")
        e.plot(z.year, z["index"], marker=marker, ls="-", color=col, lw=2.0, markersize=6, label=label)
        ends.append((float(z["index"].iloc[-1]), float(z.year.iloc[-1]), col))
    e.axhline(100, color="#999999", ls="--", lw=1)
    # A free band is reserved above for the six-entry legend.
    e.set_ylim(70, float(cv["index"].max()) * 6.0)
    for value, year, col in sorted(ends, key=lambda q: -q[0]):
        e.annotate(f"{value:,.0f}", (year, value), xytext=(5, 0), textcoords="offset points",
                   ha="left", va="center", fontsize=FS_MIN, color=col, fontweight="bold",
                   annotation_clip=False, zorder=5)
    _shade(e, [2021])
    _law(e, 0.03, va="bottom", size=FS_MIN)
    e.set_xticks(range(2021, 2026))
    e.set_xlabel("Year\n" + textwrap.fill(
        "(Indices, not levels: each series has its own unit and denominator)", 38),
        fontsize=FS_MIN + 0.5, linespacing=1.20)
    # The longest y label of the plate in the shortest cell: 7 pt keeps it inside its own axes,
    # which is what the pipeline's measured y label does here.
    e.set_ylabel("Index (first common year 2021 = 100; log scale)", fontsize=7.0)
    _legend(e, loc="upper left")
    clean(e, "both")

    # (f) forest of the REM, education and DEIS specifications --------------------------------------
    rows = []
    for mid in IDS_F:
        r = sm_.loc[mid]
        family = "family " if (r.variant in FAMILY_VARIANTS and str(r.estimand).startswith("est_a05")) else ""
        rows.append((PREFIX_F[r.estimand] + family + short_label(r),
                     float(r.apc), float(r.apc_lo), float(r.apc_hi), COLOUR_F[r.estimand]))
    forest(f, rows)
    clean(f, "x")

    # Panel letters and titles last: the titles are set while the layout is still live so their
    # height is reserved, the layout is then frozen, and only then is each title moved to the left
    # edge of ITS OWN cell — where the pipeline puts it, and where a two-line title still fits.
    titles = {}
    for axis, key in zip(ax, "abcdef"):
        # `break_on_hyphens=False`: the plate breaks '(quasi-Poisson)' between words, never inside
        # the hyphenated word, which is where the pipeline's measured wrap breaks it too.
        titles[key] = axis.set_title(textwrap.fill(f"({key}) {TITLES[key]}", 44, break_on_hyphens=False),
                                     loc="left", fontsize=FS_TITLE, fontweight="bold", linespacing=1.15)
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    value_column(fig)
    margin = 2.0 / 180.0                        # 2 mm left margin of the cell
    for i, (axis, key) in enumerate(zip(ax, "abcdef")):
        pos = axis.get_position()
        cell = margin + (i % 2) * 0.5
        titles[key].set_x((cell - pos.x0) / pos.width)
    return fig
