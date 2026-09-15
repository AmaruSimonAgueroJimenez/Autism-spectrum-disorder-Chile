"""E44 — territorial correlation between the administrative systems, comunas and regions.

Redraw of the stored plate `docs/study/corpus/figures/E44_correlation_matrix.jpg`. The original was
drawn by `study/pipeline/` from the microdata, which this repository does not carry; all six panels
are rebuilt here from tracked tables.

What the plate shows, unchanged: Spearman rank correlations between the empirical-Bayes SMOOTHED
standardised ratios of fourteen territorial indicators, computed over the 342 continental comunas and
over the 16 regions, unweighted, on the F84 family excluding Rett syndrome (sin_rett). No count is
plotted anywhere on the plate — every quantity is a rank correlation between smoothed ratios, or, in
panel (e), the two smoothed ratios themselves.

  (a) 8 x 8 matrix of the comuna-scale coefficients, (b) the same eight indicators at region scale —
  the caption's "one per system and layer", so that the printed coefficient stays legible;
  (c) every indicator against GRD F84 episodes, comuna scale, with Fisher-z 95% CI;
  (d) the 91 = C(14,2) off-diagonal pairs of the full matrix, comuna coefficient against region
      coefficient — the modifiable areal unit problem;
  (e) the strongest pair between different systems, REM A05 against REM P6 primary, drawn as the
      smoothed ratios of the 342 continental comunas;
  (f) the ten strongest cross-system pairs, comuna scale, with Fisher-z 95% CI.

Sources. `E44_correlation_matrix_comuna.csv` is the plate's own companion table: it stores the two
complete 14 x 14 matrices (Scale = Comuna, Scale = Region) to two decimals, which is what panels
(a)-(d) and (f) plot. Panel (e) needs the underlying comuna series, not a coefficient, and those are
`E41_rem_comuna_place_of_care.csv`'s 'A05 smoothed ratio' and 'P6 smoothed ratio'; the plate's n = 342
is the continental comunas, so the 346 rows of E41 are restricted with the `continental` flag of
`output_files/consolidacion/catalogo_comunas.csv`. Recomputing the two coefficients the plate prints
in its own headings from those series reproduces them: panel (d) 0.6937 -> "0.69", panel (e) 0.6171
-> "0.62", and 0.62 is also what the stored matrix holds for REM A05 x REM P6 primary.

Three things the tables do not store and that this module therefore recomputes or restates.

1. The confidence intervals. They are Fisher-z intervals on the rank coefficient, and the plate's
   printed endpoints are only reproduced with the Spearman variance correction, se^2 = 1.06 / (n - 3)
   (Fieller; Bonett & Wright), not with the Pearson se^2 = 1 / (n - 3): panel (d) comes out
   0.5649-0.7895 -> "0.56-0.79" against the plain form's 0.5691 -> "0.57", and panel (e) comes out
   0.5446-0.6804 -> "0.54-0.68" against the plain form's 0.5468 -> "0.55". Both printed lower bounds
   pick the corrected form, so that is what `_ci` uses. This is arithmetic on the stored coefficients,
   not new data.
2. Panel (f)'s selection rule, which lives in the caption rather than in the table: the ten strongest
   pairs by |rho| among pairs that cross two systems and involve at least one outcome indicator. The
   three GRD columns are three views of one register and count as one system; every other indicator is
   its own series, and only the strongest pair of any two systems is kept (which is what drops
   GRD persons/year x REM-20, tied at 0.28 with GRD F84 episodes x REM-20). Ties at the two decimals
   the table publishes cannot be resolved from it — the original ranked unrounded coefficients — so
   they are broken by a fixed rule, later column first, which returns the stored plate's ten pairs in
   the stored plate's order.
3. The abbreviations and the place-of-care marks. The table carries only full indicator names; the
   plate abbreviates them ('GRD F84', 'P2 Dec.', 'P6 prim.', 'SAE mult.') and marks with a warning
   sign, in panel (c), the indicators whose comuna is the reporting or enrolling establishment rather
   than the resident's — the five REM series and the three FONASA/APS enrolment denominators, which is
   how M1_sources_units.csv and T4_denominators_coverage.csv classify those sources ("establishment
   (place of care)", "APS centre", "mixes APS enrolment and address") against the GRD's "declared
   comuna of residence" and INE's "residence". The maps are supplied below because no tracked table
   holds them.

The corpus is English only and so is this module: no language parameter, no Spanish variant.
"""
import math
import textwrap

import numpy as np
import pandas as pd
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator
from scipy import stats
from figstyle import *

PLATE = "E44_correlation_matrix"
SOURCES = [
    "docs/study/corpus/tables/E44_correlation_matrix_comuna.csv",
    "docs/study/corpus/tables/E41_rem_comuna_place_of_care.csv",
    "output_files/consolidacion/catalogo_comunas.csv",
]
NOTE = ("Redraws the six panels of plate E44 — the comuna and region Spearman matrices of eight "
        "indicators, every indicator against GRD F84 episodes, the 91 pairs at the two scales, the "
        "strongest cross-system pair and the ten strongest cross-system pairs — from the stored 14 x 14 "
        "matrices of the E44 companion table, with panel (e)'s scatter taken from the A05 and P6 "
        "smoothed ratios of E41 restricted to the 342 continental comunas of catalogo_comunas.csv; the "
        "Fisher-z intervals are recomputed on those coefficients with the Spearman correction "
        "1.06/(n-3), which is what the plate's printed endpoints match.")

ROOT = BASE.parents[1]                          # figstyle.BASE is docs/study; ROOT is the repository root
FIGSIZE = (6.89, 9.377)                         # 175 x 238 mm, the plate canvas of the sibling modules

N_COMUNA, N_REGION = 342, 16                    # the plate's own n, printed in the headings of (a) and (b)
SPEARMAN_VAR = 1.06                             # se^2 = 1.06/(n-3): the Spearman correction, see the docstring
Z975 = 1.959963984540054                        # the normal quantile the plate's 95% intervals use

#: The indicator order of the stored table, which is also the matrix order of panels (a), (b) and (d).
INDICATORS = ["GRD F84 episodes", "GRD persons/year", "GRD F84 principal", "REM A05 entries",
              "REM P2 December", "REM P6 primary", "REM P6 specialty", "APS enrolment",
              "FONASA beneficiaries", "REM-20 discharges", "SAE multidimensional", "SAE income",
              "Urban %", "FONASA/INE %"]

#: The caption's eight, "one per system and layer", in the order the stored heatmaps print them.
EIGHT = ["GRD F84 episodes", "GRD F84 principal", "REM A05 entries", "REM P2 December",
         "REM P6 primary", "REM-20 discharges", "SAE multidimensional", "Urban %"]

#: The plate abbreviates every indicator; the table carries only the full names.
SHORT = {"GRD F84 episodes": "GRD F84", "GRD persons/year": "GRD pers.",
         "GRD F84 principal": "GRD princ.", "REM A05 entries": "A05", "REM P2 December": "P2 Dec.",
         "REM P6 primary": "P6 prim.", "REM P6 specialty": "P6 spec.", "APS enrolment": "APS",
         "FONASA beneficiaries": "FONASA", "REM-20 discharges": "REM-20",
         "SAE multidimensional": "SAE mult.", "SAE income": "SAE inc.", "Urban %": "Urban %",
         "FONASA/INE %": "FONASA %"}

#: Indicator -> system. The three GRD columns are three views of one register, so they share a system;
#: every other indicator is a series of its own. Only pairs that cross two systems enter panel (f).
SYSTEM = {"GRD F84 episodes": "GRD", "GRD persons/year": "GRD", "GRD F84 principal": "GRD",
          "REM A05 entries": "REM A05", "REM P2 December": "REM P2", "REM P6 primary": "REM P6 primary",
          "REM P6 specialty": "REM P6 specialty", "REM-20 discharges": "REM-20",
          "APS enrolment": "APS", "FONASA beneficiaries": "FONASA", "FONASA/INE %": "FONASA/INE",
          "SAE multidimensional": "SAE multidimensional", "SAE income": "SAE income",
          "Urban %": "INE urban"}

#: The ASD-count indicators. Panel (f) keeps only pairs with at least one of them; the rest are context.
OUTCOMES = {"GRD F84 episodes", "GRD persons/year", "GRD F84 principal", "REM A05 entries",
            "REM P2 December", "REM P6 primary", "REM P6 specialty", "REM-20 discharges"}

#: Panel (c) marks these with a warning sign: the comuna is the reporting or enrolling establishment's,
#: not the resident's (REM is "establishment (place of care)", APS "APS centre", FONASA "mixes APS
#: enrolment and address"), so the ratio is not a population rate of the comuna.
PLACE_OF_CARE = {"REM A05 entries", "REM P2 December", "REM P6 primary", "REM P6 specialty",
                 "REM-20 discharges", "APS enrolment", "FONASA beneficiaries", "FONASA/INE %"}
WARN = " ⚠"                                # the mark the plate appends to those labels

N_TOP = 10                                      # panel (f) draws the ten strongest pairs
CMAP = "RdBu_r"                                 # the diverging map of the stored heatmaps, -1 to 1
DASH = "#333333"                                # the reference lines of (c), (d) and (f)

#: Axes boxes as fractions of the canvas, measured off the stored plate: (left, bottom, width, height).
BOX = {"a": (0.0930, 0.7561, 0.3120, 0.2292), "b": (0.5840, 0.7561, 0.3120, 0.2292),
       "c": (0.1690, 0.3968, 0.2400, 0.2528), "d": (0.6560, 0.3968, 0.2400, 0.2528),
       "e": (0.1690, 0.0485, 0.2400, 0.2528), "f": (0.6560, 0.0485, 0.2400, 0.2528)}
CBAR = {"a": (0.4120, 0.7840, 0.0110, 0.1704), "b": (0.9030, 0.7840, 0.0110, 0.1704)}
TITLE_X = {"a": 0.010, "c": 0.010, "e": 0.010, "b": 0.510, "d": 0.510, "f": 0.510}
TITLE_Y = {"a": 0.9853, "b": 0.9853, "c": 0.6510, "d": 0.6510, "e": 0.3020, "f": 0.3020}
WRAP = 46                                       # the column the stored plate breaks its headings at

TICK_PT, LABEL_PT, TITLE_PT, CELL_PT, CBAR_PT = 6.2, 7.7, 8.7, 5.2, 6.4

TABLE = BASE / "corpus" / "tables" / "E44_correlation_matrix_comuna.csv"
E41 = BASE / "corpus" / "tables" / "E41_rem_comuna_place_of_care.csv"
CATALOGUE = ROOT / "output_files" / "consolidacion" / "catalogo_comunas.csv"


def _f(cell):
    """A stored coefficient such as '0.48' or '−0.10' (U+2212 minus) as a float."""
    return float(str(cell).replace("−", "-").strip())


def _mark(x, dec=1):
    """A number written the way the plate writes it, with a true minus sign."""
    return f"{x:.{dec}f}".replace("-", "−")


def _ci(rho, n):
    """Fisher-z 95% interval for a Spearman coefficient, with the 1.06/(n-3) variance correction."""
    z, se = math.atanh(rho), math.sqrt(SPEARMAN_VAR / (n - 3))
    return math.tanh(z - Z975 * se), math.tanh(z + Z975 * se)


def matrices():
    """The two stored 14 x 14 matrices, indicator order preserved, as float frames."""
    t = pd.read_csv(TABLE, encoding="utf-8-sig")
    out = {}
    for scale in ("Comuna", "Region"):
        d = t[t.Scale == scale].set_index("Indicator").loc[INDICATORS, INDICATORS]
        out[scale] = d.map(_f)
    return out["Comuna"], out["Region"]


def smoothed_ratios():
    """E41's A05 and P6 primary smoothed ratios over the 342 continental comunas of the catalogue."""
    t = pd.read_csv(E41, encoding="utf-8-sig")
    keep = pd.read_csv(CATALOGUE, encoding="utf-8-sig")[["cut_comuna", "continental"]]
    d = t.merge(keep, left_on="CUT", right_on="cut_comuna", how="inner")
    d = d[d.continental]
    return d["A05 smoothed ratio"].to_numpy(float), d["P6 smoothed ratio"].to_numpy(float)


def pairs(comuna, region):
    """The 91 off-diagonal pairs of the matrix: names, comuna rho and region rho."""
    rows = []
    for i in range(len(INDICATORS)):
        for j in range(i + 1, len(INDICATORS)):
            a, b = INDICATORS[i], INDICATORS[j]
            rows.append((a, b, i, j, comuna.iat[i, j], region.iat[i, j]))
    return pd.DataFrame(rows, columns=["a", "b", "i", "j", "comuna", "region"])


def cross_system(comuna, region):
    """Panel (f)'s ten: the strongest cross-system pairs holding at least one outcome indicator.

    Ranked by |rho| at comuna scale. Ties at the two decimals the table publishes are broken by a
    fixed rule — the pair whose indicators sit further down the matrix comes first — because the
    original ranked unrounded coefficients that the published table cannot restore. Of two pairs
    joining the same two systems only the stronger is drawn, which is what separates GRD F84
    episodes x REM-20 from GRD persons/year x REM-20, tied at 0.28.
    """
    p = pairs(comuna, region)
    p = p[[SYSTEM[a] != SYSTEM[b] and bool({a, b} & OUTCOMES) for a, b in zip(p.a, p.b)]]
    p = p.assign(strength=p.comuna.abs()).sort_values(
        ["strength", "j", "i"], ascending=[False, False, True], kind="stable")
    seen, keep = set(), []
    for row in p.itertuples():
        key = frozenset((SYSTEM[row.a], SYSTEM[row.b]))
        if key in seen:
            continue
        seen.add(key)
        keep.append(row)
        if len(keep) == N_TOP:
            break
    return keep


def _heatmap(fig, key, m):
    """One of the two matrices of the plate, eight indicators, printed to one decimal."""
    ax = fig.add_axes(BOX[key])
    d = m.loc[EIGHT, EIGHT].to_numpy(float)
    img = ax.imshow(d, cmap=CMAP, vmin=-1, vmax=1, aspect="auto")
    labels = [SHORT[i] for i in EIGHT]
    ax.set_xticks(range(len(EIGHT)), labels, rotation=90, fontsize=TICK_PT)
    ax.set_yticks(range(len(EIGHT)), labels, fontsize=TICK_PT)
    ax.tick_params(length=0, pad=5)
    ax.grid(False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for r in range(len(EIGHT)):
        for c in range(len(EIGHT)):
            if r == c:                          # the diagonal is 1.00 by construction and stays blank
                continue
            ax.text(c, r, _mark(d[r, c]), ha="center", va="center", fontsize=CELL_PT, color=BLACK,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.85))
    cax = fig.add_axes(CBAR[key])
    cb = fig.colorbar(img, cax=cax)
    cb.set_ticks(FixedLocator(np.arange(-1, 1.001, 0.25)))
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: _mark(v, 2)))
    cb.ax.tick_params(labelsize=TICK_PT, length=2, width=0.7, pad=2)
    cb.outline.set_linewidth(0.7)
    cb.set_label("Spearman's rho", fontsize=CBAR_PT, labelpad=3)
    return ax


def _forest(ax, rho, labels, color, n, ms, lw):
    """The shared body of panels (c) and (f): a point per row with its Fisher-z interval."""
    lo, hi = zip(*(_ci(r, n) for r in rho))
    y = np.arange(len(rho))
    ax.axvline(0, color=DASH, ls="--", lw=1.0, zorder=1)
    ax.errorbar(rho, y, xerr=[np.array(rho) - np.array(lo), np.array(hi) - np.array(rho)],
                fmt="o", color=color, ms=ms, lw=lw, mew=0, capsize=0, zorder=3)
    ax.set_yticks(y, labels, fontsize=TICK_PT)
    ax.invert_yaxis()
    clean(ax, grid="x")
    ax.tick_params(axis="y", length=0, pad=4.5)
    ax.tick_params(axis="x", labelsize=TICK_PT, pad=2)


def draw():
    style()
    comuna, region = matrices()
    fig = plt.figure(figsize=FIGSIZE)
    titles = {}

    # (a) and (b) — the two matrices of eight indicators.
    _heatmap(fig, "a", comuna)
    _heatmap(fig, "b", region)
    titles["a"] = f"(a) Comunas (n = {N_COMUNA})"
    titles["b"] = f"(b) Regions (n = {N_REGION})"

    # (c) — every other indicator against GRD F84 episodes, comuna scale, strongest first.
    row = comuna.loc["GRD F84 episodes"].drop("GRD F84 episodes").sort_values(
        ascending=False, kind="stable")
    ax = fig.add_axes(BOX["c"])
    _forest(ax, list(row.to_numpy(float)),
            [i + (WARN if i in PLACE_OF_CARE else "") for i in row.index], BLUE, N_COMUNA, 4.0, 1.3)
    ax.set_xlabel("Spearman's rho (95% CI Fisher-z)", fontsize=LABEL_PT, labelpad=1.5)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=3, steps=[1, 2, 2.5, 5, 10]))
    titles["c"] = "(c) Correlation with GRD episodes (smoothed ratio)"

    # (d) — the 91 off-diagonal pairs at the two scales, against the identity.
    p = pairs(comuna, region)
    rho_d = stats.spearmanr(p.comuna, p.region).statistic
    lo, hi = _ci(rho_d, len(p))
    ax = fig.add_axes(BOX["d"])
    ax.plot([-1, 1], [-1, 1], ls="--", lw=1.0, color=DASH, zorder=1)
    ax.scatter(p.comuna, p.region, s=12, color=GREEN, lw=0, alpha=0.9, zorder=3)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_xlabel("Spearman's rho — Comuna", fontsize=LABEL_PT, labelpad=1.5)
    ax.set_ylabel("Spearman's rho — Region", fontsize=LABEL_PT, labelpad=1.5)
    ax.tick_params(labelsize=TICK_PT, pad=2)
    clean(ax, grid="both")
    titles["d"] = (f"(d) Comuna scale versus region scale; Spearman's rho = {rho_d:.2f} "
                   f"(95% CI {lo:.2f}–{hi:.2f}; n = {len(p)})")

    # (e) — the strongest pair between different systems, drawn as the two smoothed ratios.
    a05, p6 = smoothed_ratios()
    rho_e = stats.spearmanr(a05, p6).statistic
    lo, hi = _ci(rho_e, len(a05))
    ax = fig.add_axes(BOX["e"])
    ax.scatter(a05, p6, s=11, color=ORANGE, lw=0, alpha=0.85)
    ax.set_xlabel("REM A05 entries — Smoothed ratio\n(EB)", fontsize=LABEL_PT, labelpad=1.5, linespacing=1.15)
    ax.set_ylabel("REM P6 primary — Smoothed\nratio (EB)", fontsize=LABEL_PT, labelpad=1.5, linespacing=1.15)
    ax.tick_params(labelsize=TICK_PT, pad=2)
    clean(ax, grid="both")
    titles["e"] = (f"(e) Strongest pair between different systems: Spearman's rho = {rho_e:.2f} "
                   f"(95% CI {lo:.2f}–{hi:.2f}; n = {len(a05)})")

    # (f) — the ten strongest cross-system pairs, comuna scale.
    top = cross_system(comuna, region)
    ax = fig.add_axes(BOX["f"])
    _forest(ax, [r.comuna for r in top],
            [f"{SHORT[r.a]} – {SHORT[r.b]}" for r in top], PINK, N_COMUNA, 4.2, 1.3)
    ax.set_xlabel("Spearman's rho (95% CI)", fontsize=LABEL_PT, labelpad=1.5)
    titles["f"] = "(f) The 10 strongest cross-system pairs (at least one outcome indicator)"

    for key, heading in titles.items():
        fig.text(TITLE_X[key], TITLE_Y[key], "\n".join(textwrap.wrap(heading, WRAP)),
                 fontsize=TITLE_PT, fontweight="bold", ha="left", va="bottom", linespacing=1.2)
    return fig
