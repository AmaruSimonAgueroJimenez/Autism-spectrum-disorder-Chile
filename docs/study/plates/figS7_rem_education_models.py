"""Plate S7 — A05 standardised rates, P2/P6 December stocks and the PIE school series, with their fits.

The stored plate was drawn by `study/pipeline/06_models.py` from the REM microdata and from
`outputs/tidy/models_fitted.csv`, neither of which is in this repository. Its six panels are redrawn
here from the published aggregates that carry the same series:

* `S7_a05_standardised_rates.csv` — panels (a) and (b): the crude and WHO age-standardised A05 entry
  rates per 100,000 INE residents, by sex and year, for the strict-autism code and for the variant's
  PDD family, each cell stored as `rate (lower to upper)`, with the establishments reporting the
  code each year;
* `a05_age_{hombre,mujer}_{2021,2025}.csv` — panel (c): the age- and sex-specific rate of strict
  autism entries with its exact Poisson limits, already published per age group;
* `ST14_p2_p6_june_december.csv` — panel (d): the P2 (NANEAS, ASD) December stock, the December
  reporting establishments, the December stable panel (n = 193) and its stock, and the June stock
  that the plate prints as a sensitivity marker;
* `S6_stable_panel.csv` — panel (e): the P6 December stocks of primary care (P6241010) and specialty
  (P6241060) with their reporting establishments; it is also used to re-check the P2 column of (d);
* `education_summary_year.csv` — panel (f): the harmonised PIE count, the strict-ASD and
  ASD-Asperger counts of 2019–2023, and `pie_harmonised_source`, which marks the year the source
  changes from Apuntes 60 to SINACES;
* `models_summary.csv` — not drawn, read only to CHECK the five refitted models (see below).

The estimators are the stored plate's own:

* panels (a) and (b) keep the two rate estimators visually distinct and never mix them — the dotted
  line with a round marker is the CRUDE rate (exact Poisson), the solid line with a square marker the
  rate age-STANDARDISED to the WHO standard population, whose Fay–Feuer limits are the shaded band.
  Panel (a) is the strict autism code 05990022 alone; panel (b) is the variant's PDD family
  (05990022+05990023+05990025+05990026, i.e. without the Rett code). The broad-PDD rows of 2019–2020
  are a different case definition and are excluded from both, as the stored plate excludes them;
* panel (c) is the age-specific crude rate with the exact Poisson limits of the published table, for
  the eight age groups below 40 that the stored plate prints;
* panels (d) and (e) are DECEMBER STOCKS — people under control — and panel (f) is a school-year
  stock of PIE students. None of them is a flow and none may be added to the A05 entries of (a) and
  (b). June is a sensitivity marker and is never summed with December;
* the fits are quasi-Poisson (Poisson GLM with the Pearson scale) log-linear in year, `t` counted
  from the first year of each window, with a 95 % band from the delta method on the log scale. The
  P2 offset model carries log(reporting establishments) and is therefore drawn on the FITTED-COUNT
  scale (dashed): it is change per establishment, a different quantity from the fitted stock.

REFITTED CURVES. `models_fitted.csv` — the stored fitted series and their bands — is not tracked, so
the five curves of panels (d), (e) and (f) are refitted here from the observed points of the tracked
tables. That is safe only because the specification is fully pinned and the refit reproduces the
published `models_summary.csv` exactly: `_check_fit` asserts beta, its standard error and the
dispersion of each model to nine decimal places on every run, and the module fails rather than draw a
curve that does not belong to the published model.

Deviations from the stored artwork: the panel titles are anchored to the left margin of their grid
cell rather than to the measured left edge of each panel's tick column, so the titles of the right
column start a few millimetres further left than in the stored plate; the `n=` labels of panel (e)
are placed by a short collision search rather than by the pipeline's measured decongestion engine, so
individual labels may sit on a different side of their marker. The corpus is English only, so this
module is too.
"""
import re

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from figstyle import *

PLATE = "figS7_rem_education_models"
SOURCES = [
    "docs/study/corpus/tables/S7_a05_standardised_rates.csv",
    "docs/study/data/a05_age_hombre_2021.csv",
    "docs/study/data/a05_age_mujer_2021.csv",
    "docs/study/data/a05_age_hombre_2025.csv",
    "docs/study/data/a05_age_mujer_2025.csv",
    "docs/study/corpus/tables/ST14_p2_p6_june_december.csv",
    "docs/study/corpus/tables/S6_stable_panel.csv",
    "docs/study/data/education_summary_year.csv",
    "docs/study/data/models_summary.csv",
]
NOTE = ("Redraws the six panels of plate S7 — the crude and WHO-standardised A05 entry rates by sex "
        "for strict autism and for the PDD family, the age- and sex-specific rates of 2021 and 2025, "
        "the P2 and P6 December stocks under control and the harmonised PIE series, each with its "
        "quasi-Poisson log-linear fit and 95 % band — from the published rate, stock and education "
        "tables; the five fitted curves are refitted from the tracked observed points and checked "
        "against the published models_summary.csv before they are drawn.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIG_W_IN, FIG_H_IN = 180 / 25.4, 245 / 25.4     # the plate canvas of the pipeline: 180 x 245 mm
Z = float(stats.norm.ppf(0.975))                # the pipeline's own 95 % multiplier

YEARS_A05 = [2021, 2022, 2023, 2024, 2025]      # the years of the 2021–2025 A05 definition era
YEARS_REM = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
LAW_X = 2023 - 0.35                             # the stored plate draws the law mark 0.35 y before 2023
DISRUPTION = (2020, 2021)                       # the shaded reporting-disruption years
SEXES = ["Males", "Females", "Both sexes"]      # verbatim in the Sex column of the rate table
SEXCOL = {"Males": BLUE, "Females": ORANGE, "Both sexes": "#333333"}
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39"]   # ages 0–39, as (c) prints
STRICT, FAMILY = "strict autism", "PDD family"  # the two Series the plate draws; "broad PDD" is excluded
GREY_MARK = "#777777"                           # the June sensitivity triangle
BAR_GREY = "#d9d9d9"                            # the establishment bars on the right axis of (d)
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)
FS_MIN, FS_TICK, FS_LEG = 6.0, 7.0, 6.2         # the type sizes of the pipeline's plate style
# The stored plate wraps its panel titles by measured width; the breaks below are the ones it prints.
TITLES = {
    "a": "A05 strict autism: rates per 100,000 pop.\nby sex",
    "b": "A05 PDD family (variant): rates per\n100,000 pop.",
    "c": "A05 strict: rates by age and sex, 2021 and\n2025",
    "d": "P2 ASD under control in December:\nobserved and fitted",
    "e": "P6 strict autism under control in December",
    "f": "Harmonised PIE: observed and fitted",
}

# --------------------------------------------------------------------------- reading the tables
# The presentation tables store every value as a formatted string: "1,854" is a count and
# "35.6 (34.4 to 36.8)" a rate with its confidence limits.
_RATE = re.compile(r"^\s*(-?[\d.,]+)\s*\(\s*(-?[\d.,]+)\s*to\s*(-?[\d.,]+)\s*\)")


def _num(s):
    """One formatted number -> float; blanks and the table's dashes -> nan."""
    s = str(s).strip()
    if not s or s.lower() in {"nan", "n/e", "—", "-", "not reported (no rows)"}:
        return float("nan")
    return float(s.replace(",", "").replace("−", "-"))


def _rate(s):
    """'35.6 (34.4 to 36.8)' -> (35.6, 34.4, 36.8)."""
    m = _RATE.match(str(s))
    if not m:
        raise ValueError(f"not a rate with limits: {s!r}")
    return _num(m.group(1)), _num(m.group(2)), _num(m.group(3))


def _table(rel, **kw):
    """A tracked table, read from the repository root (the corpus tables may carry a BOM)."""
    return pd.read_csv(ROOT / rel, encoding="utf-8-sig", **kw)


def a05_rates(series):
    """The published rates of one A05 series: {sex: {kind: (value, lo, hi) x 5 years}} and the n."""
    t = _table(SOURCES[0], dtype=str)
    s = t[t["Series"] == series]
    if s.empty:
        raise KeyError(f"no {series!r} rows in the standardised-rate table")
    out, estab = {}, None
    for sex in SEXES:
        rows = s[s["Sex"] == sex].set_index("Year")
        out[sex] = {
            "crude": np.array([_rate(rows.loc[str(y), "Crude rate per 100,000 (95% CI)"])
                               for y in YEARS_A05]).T,
            "asr": np.array([_rate(rows.loc[str(y), "WHO-standardised rate per 100,000 (95% CI)"])
                             for y in YEARS_A05]).T,
        }
        n = np.array([_num(rows.loc[str(y), "Reporting establishments"]) for y in YEARS_A05])
        if estab is None:
            estab = n
        assert np.array_equal(estab, n), f"the {series} rows disagree on the establishments of a year"
    return out, estab


def age_rates():
    """Panel (c): {(sex, year): (rate, lo, hi) x 8 age groups} for strict-autism entries."""
    files = {("Males", 2021): SOURCES[1], ("Females", 2021): SOURCES[2],
             ("Males", 2025): SOURCES[3], ("Females", 2025): SOURCES[4]}
    out = {}
    for key, rel in files.items():
        t = _table(rel).set_index("age_group")
        out[key] = np.array([[float(t.loc[a, c]) for c in ("rate", "lo", "hi")] for a in AGES]).T
    return out


def p2_december():
    """Panel (d): the P2 ASD December stock, June stock, stable panel and establishments, 2019–2025."""
    t = _table(SOURCES[5], dtype=str)
    s = t[(t["Code(s)"] == "P2500500") & (t["Definition era"] == "2019–2025")].set_index("Year")
    take = lambda col: np.array([_num(s.loc[str(y), col]) for y in YEARS_REM])
    out = dict(december=take("December stock"), june=take("June stock (sensitivity)"),
               estab=take("Establishments reporting in December"),
               stable=take("December stable panel: stock"),
               stable_n=take("December stable panel: establishments (n)"))
    # The stable panel is one fixed set of establishments across the window, so its n is a constant.
    assert len(set(out["stable_n"])) == 1, "the P2 stable panel changes size across the window"
    # S6 publishes the same December column: the two tables must agree before either is drawn.
    s6 = _table(SOURCES[6], dtype=str)
    c = s6[(s6["Panel"] == "c") & (s6["Code"] == "P2500500")].set_index("Year")
    assert np.array_equal(out["december"], np.array([_num(c.loc[str(y), "Value"]) for y in YEARS_REM])), \
        "ST14 and S6 disagree on the P2 December stock"
    return out


def p6_december():
    """Panel (e): the P6 December stock and establishments of the 2021–2025 era, by setting."""
    t = _table(SOURCES[6], dtype=str)
    out = {}
    for setting, code in (("primary", "P6241010"), ("specialty", "P6241060")):
        s = t[t["Code"] == code].set_index("Year")
        # Broad PDD 2019–2020 (P6223000 / P6223380) is a different definition era and never joins these.
        assert set(s["Definition era"]) == {"2021–2025"}, f"{code} carries more than one definition era"
        out[setting] = dict(stock=np.array([_num(s.loc[str(y), "Value"]) for y in YEARS_A05]),
                            estab=np.array([_num(s.loc[str(y), "Reporting establishments"])
                                            for y in YEARS_A05]))
    return out


def pie_series():
    """Panel (f): the harmonised PIE count, its two component series and the source-change year."""
    e = _table(SOURCES[7]).sort_values("year")
    e = e[e.year.isin(YEARS_REM)]
    src = e.set_index("year")["pie_harmonised_source"]
    last_apuntes = max(y for y in src.index if "APUNTES" in str(src[y]).upper())
    return dict(year=e.year.to_numpy(float), harmonised=e.pie_harmonised_n.to_numpy(float),
                strict=e.pie_tea_strict_n.to_numpy(float), asperger=e.pie_tea_asperger_n.to_numpy(float),
                source_change=last_apuntes + 0.5)


# --------------------------------------------------------------------------- the log-linear fits
def qp_fit(years, counts, offsets=None):
    """Quasi-Poisson log-linear fit in year, with the delta-method 95 % band of the pipeline.

    `X = [1, t]` with `t` counted from the first year of the window; the Pearson scale is estimated
    (`scale='X2'`), which is what makes the fit quasi-Poisson. With `offsets` the linear predictor
    carries `log(offset)`, so `fitted_count = exp(lp + log(offset))` is the fitted COUNT and the
    trend it reports is change per unit of the offset — a different quantity from the fitted stock."""
    years = np.asarray(years, dtype=float)
    y = np.asarray(counts, dtype=float)
    X = pd.DataFrame({"const": 1.0, "t": years - years.min()})
    off = None if offsets is None else np.log(np.asarray(offsets, dtype=float))
    fit = sm.GLM(y, X, family=sm.families.Poisson(), offset=off).fit(scale="X2")
    Xv, V = np.asarray(X, dtype=float), np.asarray(fit.cov_params(), dtype=float)
    lp = Xv @ np.asarray(fit.params, dtype=float)
    se = np.sqrt(np.einsum("ij,jk,ik->i", Xv, V, Xv))
    return dict(year=years, beta=float(fit.params["t"]), se=float(fit.bse["t"]),
                dispersion=float(fit.pearson_chi2 / (len(y) - X.shape[1])),
                rate=np.exp(lp), lo=np.exp(lp - Z * se), hi=np.exp(lp + Z * se),
                count=np.exp(lp + (0.0 if off is None else off)))


def _check_fit(model_id, fit):
    """The refit must reproduce the published model. A curve that does not is never drawn."""
    m = _table(SOURCES[8])
    row = m[m.model_id == model_id]
    assert len(row) == 1, f"{model_id} is not a single row of models_summary.csv"
    row = row.iloc[0]
    for key, stored in (("beta", row.beta), ("se", row.se), ("dispersion", row.dispersion)):
        assert abs(fit[key] - float(stored)) < 5e-10 * max(1.0, abs(float(stored))), \
            f"{model_id}: refitted {key} {fit[key]!r} is not the published {stored!r}"
    return fit


# --------------------------------------------------------------------------- panel furniture
def _shade(ax, years):
    """The reporting-disruption shading of the stored plate: one grey year-wide span per year."""
    for y in years:
        ax.axvspan(y - 0.5, y + 0.5, color="grey", alpha=0.12, zorder=0)


def _law(ax, y=0.55, fontsize=FS_MIN, ha="left"):
    """Law 21.545 as CONTEXT — a dotted mark, never an intervention in any model drawn here."""
    ax.axvline(LAW_X, color="#444444", ls=":", lw=1.2, zorder=1)
    ax.text(LAW_X + (0.06 if ha == "left" else -0.06), y, "Law 21.545\n(context)",
            transform=ax.get_xaxis_transform(), ha=ha, va="center", fontsize=fontsize, color="#444444")


def _disruption_text(ax, y=0.55):
    ax.text(2020.5, y, "Reporting\ndisruption 2020–21", transform=ax.get_xaxis_transform(),
            ha="center", va="center", fontsize=7.5, color="#555555")


def _legend(ax, *args, loc="upper right", ncol=1, **kw):
    lg = ax.legend(*args, loc=loc, ncol=ncol, fontsize=FS_LEG, frameon=True, framealpha=0.82,
                   edgecolor="none", facecolor="white", borderpad=0.25, **kw)
    lg.set_zorder(6)
    lg.set_in_layout(False)
    return lg


def _value_label(ax, x, y, text, colour, prefer, placed, marks, step=3.0):
    """A short `n=` label set beside its marker, clear of the other markers and of the labels already
    placed — a compact stand-in for the pipeline's measured decongestion engine, with the same
    preference order: the two settings of panel (e) push their labels to opposite sides."""
    fig = ax.figure
    ann = ax.annotate(text, xy=(x, y), xycoords="data", textcoords="offset points", xytext=(0, step),
                      fontsize=FS_MIN, color=colour, ha="center", va="center", zorder=6)
    r = fig.canvas.get_renderer()
    bb = ann.get_window_extent(r)
    w = bb.width / fig.dpi * 72.0
    h = bb.height / fig.dpi * 72.0
    best, best_cost = (0.0, step), np.inf
    for k in (1, 2):
        for ux, uy in prefer:
            ann.xyann = (ux * (w * 0.55 + step + 4.0) * k, uy * (h * 0.75 + step + 4.0) * k)
            nb = ann.get_window_extent(r)
            cost = sum(60.0 for px, py in marks if nb.x0 - 4 <= px <= nb.x1 + 4 and nb.y0 - 4 <= py <= nb.y1 + 4)
            cost += sum(20.0 for q in placed if nb.overlaps(q))
            axb = ax.get_window_extent(r)
            cost += 5.0 * (max(0.0, axb.x0 - nb.x0) + max(0.0, nb.x1 - axb.x1)
                           + max(0.0, axb.y0 - nb.y0) + max(0.0, nb.y1 - axb.y1))
            cost += 0.02 * (abs(ann.xyann[0]) + abs(ann.xyann[1]))
            if cost < best_cost - 1e-9:
                best, best_cost = ann.xyann, cost
        if best_cost <= 1e-9:
            break
    ann.xyann = best
    placed.append(ann.get_window_extent(r))
    return ann


def draw():
    style()
    plt.rcParams.update({
        "font.size": 8.0, "axes.titlesize": 9.0, "axes.titleweight": "bold", "axes.labelsize": 8.0,
        "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK, "axes.titlelocation": "left",
        "grid.linewidth": 0.45, "lines.linewidth": 1.3, "axes.labelpad": 2.0, "axes.titlepad": 3.0,
        "xtick.major.size": 2.2, "ytick.major.size": 2.2, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    })
    strict_rates, strict_n = a05_rates(STRICT)
    family_rates, family_n = a05_rates(FAMILY)
    ages = age_rates()
    p2 = p2_december()
    p6 = p6_december()
    pie = pie_series()

    fig, axes = plt.subplots(3, 2, figsize=(FIG_W_IN, FIG_H_IN), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    ax = axes.ravel()

    # (a), (b) crude and WHO-standardised A05 rates, one panel per case definition ------------------
    for a, (rates, estab) in zip(ax[:2], [(strict_rates, strict_n), (family_rates, family_n)]):
        for sex in SEXES:
            colour = SEXCOL[sex]
            crude, asr = rates[sex]["crude"], rates[sex]["asr"]
            a.plot(YEARS_A05, crude[0], "o:", color=colour, lw=1.4, markersize=5, label=f"{sex} · crude")
            a.plot(YEARS_A05, asr[0], "s-", color=colour, lw=2.0, markersize=5,
                   label=f"{sex} · WHO-standardised")
            a.fill_between(YEARS_A05, asr[1], asr[2], color=colour, alpha=0.12)
        _shade(a, [2021])
        _law(a)
        a.set_xticks(YEARS_A05)
        # The stored plate writes the establishment count of the tick plainly, without a thousands
        # separator ("n=1070"), unlike the axis ticks of (d)-(f); it is kept as it prints it.
        a.set_xticklabels([f"{y}\nn={n:.0f}" for y, n in zip(YEARS_A05, estab)],
                          fontsize=FS_MIN + 0.2)
        a.set_xlabel("Year (n = A05 reporting establishments)")
        a.set_ylabel("A05 entries per 100,000 population")
        a.set_ylim(0, max(rates[s]["asr"][2].max() for s in SEXES) * 1.7)
        _legend(a)
        clean(a, "both")

    # (c) age- and sex-specific rates of the first and the last year -------------------------------
    x = np.arange(len(AGES))
    for year, ls, mk, off in [(2021, ":", "o", -0.1), (2025, "-", "s", 0.1)]:
        for sex in ("Males", "Females"):
            rate, lo, hi = ages[(sex, year)]
            ax[2].errorbar(x + off, rate, yerr=[rate - lo, hi - rate], fmt=mk, ls=ls,
                           color=SEXCOL[sex], capsize=2, markersize=5, lw=1.6, label=f"{sex} {year}")
    ax[2].set_xticks(x)
    ax[2].set_xticklabels(AGES, rotation=45, ha="right")
    ax[2].set_xlabel("Age group (years)")
    ax[2].set_ylabel("A05 entries per 100,000 population")
    _legend(ax[2])
    clean(ax[2], "both")

    # (d) P2 December stock: observed, both fits, June, the stable panel and the establishments ------
    d2 = ax[3].twinx()
    d2.spines["right"].set_visible(True)
    d2.grid(False)
    d2.bar(YEARS_REM, p2["estab"], width=0.6, color=BAR_GREY, alpha=0.7, zorder=0,
           label="reporting establishments")
    d2.set_ylim(0, p2["estab"].max() * 3.2)
    d2.set_ylabel("Reporting establishments (December)")
    d2.yaxis.set_major_formatter(thousands("en"))
    f1 = _check_fit("p2_dec:none:2019-2025", qp_fit(YEARS_REM, p2["december"]))
    ax[3].plot(f1["year"], f1["rate"], "-", color=PINK, lw=2.0, zorder=3,
               label="log-linear fit, no offset")
    ax[3].fill_between(f1["year"], f1["lo"], f1["hi"], color=PINK, alpha=0.13, zorder=2)
    f2 = _check_fit("p2_dec:estab:2019-2025", qp_fit(YEARS_REM, p2["december"], p2["estab"]))
    # The offset model is drawn on the fitted-COUNT scale: it is change per establishment, and its
    # fitted rate (people per establishment) does not belong on this axis.
    ax[3].plot(f2["year"], f2["count"], "--", color=YELLOW, lw=1.8, zorder=3,
               label="fit with log(establishments) offset")
    ax[3].plot(YEARS_REM, p2["december"], "o", color=PINK, markersize=7, zorder=4,
               label="People under control (December)")
    ax[3].plot(YEARS_REM, p2["june"], "^", color=GREY_MARK, markersize=6, zorder=4,
               label="June (sensitivity)")
    ax[3].plot(YEARS_REM, p2["stable"], "d:", color=GREEN, lw=1.2, markersize=5, zorder=4,
               label=f"stable panel (n={num(p2['stable_n'][0], 'en')})")
    _shade(ax[3], DISRUPTION)
    _disruption_text(ax[3])
    _law(ax[3], fontsize=7.5)
    ax[3].set_xticks(YEARS_REM)
    ax[3].set_xlabel("Year")
    ax[3].set_ylim(0, f1["hi"].max() * 1.45)
    ax[3].set_ylabel("People under control (December)")
    ax[3].yaxis.set_major_formatter(thousands("en"))
    ax[3].set_zorder(d2.get_zorder() + 1)
    ax[3].patch.set_visible(False)
    h1, l1 = ax[3].get_legend_handles_labels()
    h2, l2 = d2.get_legend_handles_labels()
    _legend(ax[3], h1 + h2, l1 + l2)
    clean(ax[3], "both")
    d2.grid(False)

    # (e) P6 December stock by setting, strict autism only, 2021–2025 -------------------------------
    fits_e = {}
    for setting, colour, label, prefer in (
            ("primary", GOLD, "Primary care (P6241010)", ((0, 1), (0, -1), (1, 0), (-1, 0))),
            ("specialty", SKY, "Specialty (P6241060)", ((0, -1), (0, 1), (1, 0), (-1, 0)))):
        s = p6[setting]
        f = _check_fit(f"p6_{setting}:strict_autism:none:2021-2025", qp_fit(YEARS_A05, s["stock"]))
        fits_e[setting] = (f, colour, prefer)
        ax[4].plot(f["year"], f["rate"], "-", color=colour, lw=2.0, zorder=2)
        ax[4].fill_between(f["year"], f["lo"], f["hi"], color=colour, alpha=0.13)
        ax[4].plot(YEARS_A05, s["stock"], "o", color=colour, markersize=7, zorder=4, label=label)
    ax[4].text(0.99, 0.02, "Broad PDD 2019–2020 excluded (different era)", transform=ax[4].transAxes,
               ha="right", va="bottom", fontsize=FS_MIN, color="#555555", bbox=NOTE_BBOX, zorder=6)
    _shade(ax[4], [2021])
    _law(ax[4])
    ax[4].set_xticks(YEARS_A05)
    ax[4].set_xlabel("Year")
    ax[4].set_ylim(0, fits_e["primary"][0]["hi"].max() * 1.4)
    ax[4].set_ylabel("People under control (December)")
    ax[4].yaxis.set_major_formatter(thousands("en"))
    _legend(ax[4], loc="upper center")
    clean(ax[4], "both")

    # (f) the harmonised PIE series, its fit and the two component series ---------------------------
    fp = _check_fit("pie_harmonised:none:2019-2025", qp_fit(pie["year"], pie["harmonised"]))
    ax[5].plot(fp["year"], fp["rate"], "-", color=SKY, lw=2.0, zorder=2)
    ax[5].fill_between(fp["year"], fp["lo"], fp["hi"], color=SKY, alpha=0.13)
    ax[5].plot(pie["year"], pie["harmonised"], "o", color=SKY, markersize=7, zorder=4,
               label="PIE ASD + ASD-Asperger (harmonised)")
    ax[5].plot(pie["year"], pie["strict"], "s--", color=BLUE, lw=1.5, markersize=5, label="PIE strict ASD")
    ax[5].plot(pie["year"], pie["asperger"], "^--", color=ORANGE, lw=1.5, markersize=5,
               label="PIE ASD-Asperger")
    ax[5].axvline(pie["source_change"], color="#999999", ls="-.", lw=1.0)
    _shade(ax[5], DISRUPTION)
    _disruption_text(ax[5])
    # The series climbs just after the law mark, so the stored plate writes that label to its LEFT.
    _law(ax[5], y=0.67, fontsize=7.5, ha="right")
    ax[5].set_xticks(YEARS_REM)
    ax[5].set_xlabel("Year")
    ax[5].set_ylim(0, fp["hi"].max() * 1.4)
    ax[5].set_ylabel("PIE students with ASD")
    ax[5].yaxis.set_major_formatter(thousands("en"))
    from matplotlib.lines import Line2D
    h, l = ax[5].get_legend_handles_labels()
    h.append(Line2D([], [], color="#999999", ls="-.", lw=1.0))
    l.append("source change: Apuntes 60 → SINACES")
    _legend(ax[5], h, l)
    clean(ax[5], "both")

    # The panel letter is part of the title in this plate, anchored to the left margin of its grid
    # cell — which is what lets the long titles of the right column start left of their tick column.
    for a, key in zip(ax, "abcdef"):
        a.set_title(f"({key}) {TITLES[key]}", loc="left", fontsize=9, fontweight="bold",
                    linespacing=1.15)
    fig.draw_without_rendering()
    fig.set_layout_engine("none")
    fig.canvas.draw()
    margin = 2.0 / 180.0                        # the pipeline's 2 mm cell margin, in figure fractions
    for a, key in zip(ax, "abcdef"):
        pos = a.get_position()
        cell_x0 = a.get_subplotspec().colspan.start / axes.shape[1]
        a.title.set_x((cell_x0 + margin - pos.x0) / pos.width)

    # The `n=` labels of panel (e) are placed last, against the frozen composition.
    marks = [tuple(ax[4].transData.transform((yr, v)))
             for setting in ("primary", "specialty") for yr, v in zip(YEARS_A05, p6[setting]["stock"])]
    for setting in ("primary", "specialty"):                # keep the labels off the fitted curves too
        f = fits_e[setting][0]
        t = np.linspace(0, len(YEARS_A05) - 1, 61)
        marks += [tuple(ax[4].transData.transform(
            (np.interp(u, np.arange(len(YEARS_A05)), f["year"]),
             np.interp(u, np.arange(len(YEARS_A05)), f["rate"])))) for u in t]
    placed = [ax[4].texts[0].get_window_extent(fig.canvas.get_renderer())]   # the era note of the panel
    for setting in ("primary", "specialty"):
        _f, colour, prefer = fits_e[setting]
        for yr, v, n in zip(YEARS_A05, p6[setting]["stock"], p6[setting]["estab"]):
            _value_label(ax[4], yr, v, f"n={n:.0f}", colour, prefer, placed, marks)
    return fig
