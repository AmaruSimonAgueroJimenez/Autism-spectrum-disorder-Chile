"""E12 — A03 2023–2025: risk and referral structure of M-CHAT-R/F screening, redrawn from its table.

The stored plate was produced by `study/pipeline/14_extra_figures_rem.py` from the REM Serie A
microdata, which this repository does not carry. Every number the six panels print, however, survives
in the plate's own published table, `docs/study/corpus/tables/E12_rem_a03_risk_referral.csv`: the 23
code rows give each code's annual total and its reporting establishments as the formatted cell
``"14,083 (880)"``, and the three derived rows at the foot give the risk composition and the two
referral percentages already rounded. This module parses those cells and redraws the plate.

What is recomputed rather than parsed: the within-code-year percentages and their Wilson 95% limits,
rebuilt from the parsed counts exactly as the pipeline built them (`wilson_pct` over the same
numerator and denominator). `_check()` confirms every one of them reproduces the derived row of the
table to the printed decimal, so nothing here is invented and nothing drifts from what was published.

Estimator, unchanged from the original: unweighted administrative counts, an annual flow that is the
sum of the months, with no survey weighting and no standardisation. The percentages are proportions
*within one code and one year* — they are not person-level probabilities, not conversion rates along
a cascade, and the three bars of panel (f) describe three different instruments, so they never form a
continuous series.

The corpus is English only and so is this module: it takes no language argument.
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
from matplotlib.font_manager import FontProperties
from scipy import stats

from figstyle import *   # noqa: F401,F403  — style, clean, letter, num, BLUE, ORANGE, BLACK, …

PLATE = "E12_rem_a03_risk_referral"
SOURCES = ["docs/study/corpus/tables/E12_rem_a03_risk_referral.csv"]
NOTE = ("Redraws the six panels of E12 — the composition of the M-CHAT-R/F part-1 result, the referral "
        "of high risk, the part-2 outcomes, the 2024-era 31–59-month codes, the 2025 redesign and the "
        "risk composition by era — from the annual totals and reporting establishments published in "
        "docs/study/corpus/tables/E12_rem_a03_risk_referral.csv.")

ROOT = Path(__file__).resolve().parents[3]            # repository root
TABLE = ROOT / SOURCES[0]

# --------------------------------------------------------------------------------------------------
# The plate's own geometry and typography (study/pipeline/14_extra_figures_rem.py): 180 × 245 mm,
# three rows by two columns in reading order, 9 pt bold panel titles down to a 6 pt floor.
# --------------------------------------------------------------------------------------------------
PLATE_W_IN, PLATE_H_IN = 180.0 / 25.4, 245.0 / 25.4
PLATE_LETTERS = "abcdef"
FS_TITLE, FS_BASE, FS_TICK, FS_LEG, FS_ANN, FS_CELL = 9.0, 8.0, 7.0, 7.0, 6.4, 6.0
TITLE_W_PT = (PLATE_W_IN * 72.0 / 2) - 2.0 * 72.0 / 25.4 - 31.0      # cell − margin − letter
LETTER_DX_PT = -30.0
DARK, DASH_GREY, BREAK_GREY, GLOSS_GREY = "#333333", "#8c8c8c", "#999999", "#555555"
VALUE_HALO = dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.80)
NOTE_HALO = dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85)
PLATE_RC = {
    "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold", "axes.labelsize": FS_BASE,
    "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "legend.fontsize": FS_LEG, "legend.title_fontsize": FS_LEG,
    "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
    "legend.edgecolor": "none", "legend.borderpad": 0.25, "legend.handlelength": 1.4,
    "legend.handletextpad": 0.5, "legend.columnspacing": 1.0, "legend.labelspacing": 0.35,
    "legend.borderaxespad": 0.3,
    "axes.linewidth": 0.7, "grid.linewidth": 0.5, "grid.alpha": 0.32, "grid.color": "#b0b0b0",
    "lines.linewidth": 1.1, "lines.markersize": 3.2,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    "xtick.major.pad": 1.6, "ytick.major.pad": 1.6, "axes.titlepad": 4.0, "axes.labelpad": 2.0,
}

# Panel titles, legend keys and axis units, in the words the stored plate prints.
T_A = "Composition of the part-1 result, 2023–2024"
T_B = "Referral of high risk, 2023–2024"
T_C = "Part-2 outcomes, 2023–2024"
T_D = "31–59-month codes, 2024 era"
T_E = "2025 redesign: motives and results — 2025 era"
T_F = "Risk composition by era (never a continuous series)"
U_SCREEN = "Screening records (annual flow)"
U_CHILDREN = "Children or records (annual flow)"
U_SHARE = "% of the year total"
L_LOW, L_MED, L_HIGH = "Low risk", "Medium risk", "High risk"
L_HIGH_REF = "High risk with specialist referral"
SHARE_REFERRED = "% of high risk with referral (Wilson 95% CI)"
DEF_BREAK = "definition\nbreak"
NO_CONTINUITY = "separate eras: the totals do not form a continuous series"
MOTIVES, RESULTS_2025 = "Screening motives (16–30 months)", "Results and referral"

#: SHORT FORMS OF THE TABLE'S LONG `Indicator` STRINGS. The table names each code in full
#: ("M-CHAT-R/F part 2: no referral required"); a 90 mm cell has room for two short lines, so the
#: drawing code supplies the abbreviation, exactly as the pipeline's own `A03_SHORT` did.
SHORT = {
    "09600212": "Suspected elsewhere", "09600213": L_LOW, "09600214": L_MED, "09600215": L_HIGH,
    "09600216": "High with referral", "09600217": "Part 2: medium in part 1",
    "09600218": "Part 2: no referral", "09600219": "Part 2: referral",
    "03700104": "Evaluated", "03700105": "Suspected elsewhere", "03700106": "Alert: yes",
    "03700107": "Alert: no", "03700108": "Referral: yes", "03700109": "Referral: no",
    "03710013": "Motive: EEDP", "03710014": "Motive: risk/alert", "03710015": "Motive: both",
    "03710016": L_LOW, "03710017": "Medium no referral", "03710018": "Medium referral",
    "03710019": "High referral", "03710020": "30–59 mo no referral", "03710021": "30–59 mo referral",
}
ERA_2024 = ["03700104", "03700105", "03700106", "03700107", "03700108", "03700109"]
ERA_2025 = ["03710013", "03710014", "03710015", "03710016", "03710017", "03710018",
            "03710019", "03710020", "03710021"]
# OKABE index in the original ≡ the figstyle names: OK[0] BLUE, OK[1] ORANGE, OK[2] GREEN,
# OK[3] PINK, OK[4] GOLD, OK[5] SKY.
COL_D = [BLUE, SKY, ORANGE, GREEN, PINK, GOLD]
COL_E = [BLUE] * 3 + [SKY, GOLD, GOLD, ORANGE, GREEN, GREEN]


# --------------------------------------------------------------------------------------------------
# Reading the table: every cell of the 23 code rows is "<total> (<establishments>)"
# --------------------------------------------------------------------------------------------------
_CELL = re.compile(r"^\s*(\d[\d,]*)\s*\(\s*(\d[\d,]*)\s*\)\s*$")
_PCT_CI = re.compile(r"([\d.]+)%\s*\(\s*([\d.]+)\s*[–-]\s*([\d.]+)\s*\)")
_PCT_ONLY = re.compile(r"([\d.]+)%")


def _cell(s):
    """'14,083 (880)' -> (14083.0, 880.0); 'outside the era' -> (nan, nan)."""
    m = _CELL.match(str(s))
    if not m:
        return float("nan"), float("nan")
    return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))


def read_table():
    """The published table, indexed by code, with the derived rows kept apart."""
    df = pd.read_csv(TABLE, dtype=str, encoding="utf-8-sig").fillna("")
    df.columns = [c.strip() for c in df.columns]
    codes = df[df["Code"].str.fullmatch(r"\d{8}")].set_index("Code")
    derived = df[~df["Code"].str.fullmatch(r"\d{8}")].set_index("Code")
    return codes, derived


def _wilson(k, n):
    """Wilson 95% limits on a within-code-year proportion, as percentages (the pipeline's `wilson_pct`)."""
    if not n or n <= 0 or pd.isna(k) or pd.isna(n):
        return float("nan"), float("nan"), float("nan")
    z = float(stats.norm.ppf(0.975))
    p = k / n
    den = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return 100 * p, 100 * max(0.0, centre - half), 100 * min(1.0, centre + half)


def prepare():
    """The three small frames the six panels need, all parsed from the one table."""
    codes, derived = read_table()

    def g(code, year):
        return _cell(codes.loc[code, str(year)]) if code in codes.index else (np.nan, np.nan)

    def total(code, year):
        return g(code, year)[0]

    def n_est(code, year):
        return g(code, year)[1]

    # (a)/(f) composition of the part-1 result. In 2025 medium risk is already split by referral
    # need, so its two codes are added together; that is the definition break panel (f) marks.
    comp = []
    for y in (2023, 2024):
        low, med, high = total("09600213", y), total("09600214", y), total("09600215", y)
        tot = float(np.nansum([low, med, high]))
        comp.append(dict(era="2023–2024", year=y, low=low, medium=med, high=high, part1_total=tot,
                         low_pct=100 * low / tot, medium_pct=100 * med / tot, high_pct=100 * high / tot,
                         n_est=n_est("09600213", y)))
    low, med_nr, med_r, high = (total("03710016", 2025), total("03710017", 2025),
                                total("03710018", 2025), total("03710019", 2025))
    tot = float(np.nansum([low, med_nr, med_r, high]))
    comp.append(dict(era="2025", year=2025, low=low, medium=med_nr + med_r, high=high, part1_total=tot,
                     low_pct=100 * low / tot, medium_pct=100 * (med_nr + med_r) / tot,
                     high_pct=100 * high / tot, n_est=n_est("03710016", 2025)))
    comp = pd.DataFrame(comp)

    # (b) high risk referred to a specialist, within the same code-year.
    ref = []
    for y in (2023, 2024):
        den, numr = total("09600215", y), total("09600216", y)
        p, lo, hi = _wilson(numr, den)
        ref.append(dict(year=y, denominator=den, numerator=numr, pct=p, lo=lo, hi=hi,
                        n_est=n_est("09600216", y), n_est_denominator=n_est("09600215", y)))
    ref = pd.DataFrame(ref)

    # (c) part-2 outcomes; 09600217 exists in 2023 only, so 2024 keeps its empty slot.
    second = []
    for y in (2023, 2024):
        no_ref, with_ref = total("09600218", y), total("09600219", y)
        tot2 = float(np.nansum([no_ref, with_ref]))
        p, lo, hi = _wilson(with_ref, tot2)
        second.append(dict(year=y, medium_in_part1=total("09600217", y), no_referral=no_ref,
                           referral=with_ref, second_total=tot2, referral_pct=p, referral_lo=lo,
                           referral_hi=hi, n_est=n_est("09600219", y),
                           n_est_medium=n_est("09600217", y), n_est_no_referral=n_est("09600218", y)))
    second = pd.DataFrame(second)

    # (d)/(e) one row per code of the 2024 and 2025 eras.
    era = {y: pd.DataFrame([dict(code=c, total=total(c, y), n=n_est(c, y)) for c in cs]).set_index("code")
           for y, cs in ((2024, ERA_2024), (2025, ERA_2025))}
    return comp, ref, second, era, derived


# --------------------------------------------------------------------------------------------------
# Formatting and layout helpers (the plate's own conventions, English only)
# --------------------------------------------------------------------------------------------------
def _n(x, dec=0):
    return num(x, "en", dec)


def _pct(x, dec=1):
    return "—" if x is None or pd.isna(x) else _n(x, dec) + "%"


def _ci(lo, hi, dec=1):
    return f"{_n(lo, dec)}–{_n(hi, dec)}"


#: Scratch canvas used only to MEASURE text. It is deliberately not a pyplot figure: an open pyplot
#: figure would become the current one and a notebook or Quarto chunk would render the blank square.
_MEASURE = None


def _width_pt(s, fontsize, weight):
    global _MEASURE
    if _MEASURE is None:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        _MEASURE = Figure(figsize=(1, 1))
        FigureCanvasAgg(_MEASURE)
    r = _MEASURE.canvas.get_renderer()
    w, _h, _d = r.get_text_width_height_descent(
        s, FontProperties(family="DejaVu Sans", size=fontsize, weight=weight), False)
    return w * 72.0 / _MEASURE.dpi


def _wrap_measured(s, max_pt=TITLE_W_PT, fontsize=FS_TITLE, weight="bold"):
    """Line breaks by measured width, not by character count."""
    lines, cur = [], ""
    for w in str(s).split():
        trial = f"{cur} {w}".strip()
        if cur and _width_pt(trial, fontsize, weight) > max_pt:
            lines.append(cur); cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return "\n".join(lines) if lines else str(s)


def _tick_label(s, width=15, lines=2):
    parts = textwrap.wrap(str(s), width) or [str(s)]
    if len(parts) <= lines:
        return "\n".join(parts)
    keep = parts[:lines]
    tail = (keep[-1] + " " + parts[lines])
    keep[-1] = tail if len(tail) <= width else tail[:max(1, width - 1)].rstrip() + "…"
    return "\n".join(keep)


def _title(ax, s):
    """Panel title wrapped to the measured width of its cell, anchored to the cell's left edge."""
    return ax.set_title(_wrap_measured(s), fontsize=FS_TITLE, fontweight="bold", loc="left")


def _ann(ax, x, y, s, fs=FS_ANN, dy=3, color=DARK, halo=VALUE_HALO):
    return ax.annotate(s, (x, y), xytext=(0, dy), textcoords="offset points", ha="center",
                       va="bottom" if dy >= 0 else "top", fontsize=fs, color=color, zorder=6,
                       bbox=dict(halo))


def _headroom(ax, frac):
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + (hi - lo) * frac)


def _legend(ax, loc, fontsize=FS_LEG, ncol=1, width=24):
    """Legend inside the panel, labels wrapped rather than shrunk, with room made above the series."""
    handles, labels = ax.get_legend_handles_labels()
    labels = [textwrap.fill(str(t), width) for t in labels]
    rows = -(-len(labels) // ncol)
    lines = max(rows, sum(t.count("\n") + 1 for t in labels) // ncol)
    _headroom(ax, min(0.62, 0.030 + 0.062 * lines))
    leg = ax.legend(handles, labels, loc=loc, fontsize=fontsize, ncol=ncol, borderpad=0.28,
                    labelspacing=0.3)
    leg.set_in_layout(False)
    return leg


def _spread(ax, anns, pad_pt=1.0, step_pt=2.0, limit=40):
    """Raise an n label that runs into the n label of the neighbouring bar.

    Panel (c) sets three bars 0.21 units wide 0.22 apart: over the 2023 group the n of the gold bar
    and the n of the blue bar are wider than the gap between their bar centres and touch. The
    published plate lifts the left one clear; this is the same move, measured rather than hand-placed.
    Only the one-line n labels take part — the three-line percentage block keeps the place the plate
    gives it, beside its neighbour rather than above it.
    """
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    placed = []
    for a in sorted(anns, key=lambda t: t.xy[0], reverse=True):
        for _ in range(limit):
            bb = a.get_window_extent(r).padded(pad_pt)
            if not any(bb.overlaps(q) for q in placed):
                break
            dx, dy = a.get_position()
            a.set_position((dx, dy + step_pt))
        placed.append(a.get_window_extent(r).padded(pad_pt))


def _letters(fig, axes, titles):
    """figstyle's panel letter, its top set level with the top of the panel's own title."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    w_pt = fig.get_figwidth() * 72.0
    for ax, ttl, ch in zip(axes, titles, PLATE_LETTERS):
        top = ttl.get_window_extent(r).transformed(inv).y1
        letter(fig, ax, f"({ch})", dx=LETTER_DX_PT / w_pt, dy=0.0)
        t = fig.texts[-1]
        t.set_y(t.get_position()[1] + top - t.get_window_extent(r).transformed(inv).y1)


# --------------------------------------------------------------------------------------------------
# The plate
# --------------------------------------------------------------------------------------------------
def draw():
    comp, ref, second, era, _derived = prepare()
    style()
    plt.rcParams.update(PLATE_RC)
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), layout="constrained")
    try:
        fig.get_layout_engine().set(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055)
    except AttributeError:                                   # pragma: no cover — older matplotlib
        pass
    gs = fig.add_gridspec(3, 2)
    axes, titles = [], []

    # (a) composition of the part-1 result, 2023–2024 ------------------------------------------
    ax = fig.add_subplot(gs[0, 0]); axes.append(clean(ax, grid="both"))
    s = comp[comp.era == "2023–2024"]
    x = s.year.to_numpy(dtype=float)
    bottom = np.zeros(len(s))
    for key, col, lab in (("low", SKY, L_LOW), ("medium", GOLD, L_MED), ("high", ORANGE, L_HIGH)):
        v = s[key].to_numpy(dtype=float)
        ax.bar(x, v, bottom=bottom, width=0.5, color=col, label=lab, zorder=2)
        for xi, vi, bi, pc in zip(x, v, bottom, s[f"{key}_pct"]):
            ax.text(xi, bi + vi / 2, f"{_n(vi)}\n{_pct(pc)}", ha="center", va="center",
                    fontsize=FS_ANN, zorder=6,
                    color="white" if key != "low" else DARK,
                    bbox=None if key != "low" else dict(VALUE_HALO))
        bottom = bottom + np.nan_to_num(v)
    for xi, r in zip(x, s.itertuples()):
        _ann(ax, xi, r.part1_total, f"n={_n(r.n_est)}")
    ax.set_xticks(x); ax.set_xlim(2022.5, 2024.5)
    ax.set_ylim(0, float(s.part1_total.max()) * 1.20)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_ylabel(U_SCREEN, fontsize=FS_BASE); ax.set_xlabel("Year", fontsize=FS_BASE)
    _legend(ax, "upper left", fontsize=FS_TICK)
    titles.append(_title(ax, T_A))

    # (b) referral of high risk ------------------------------------------------------------------
    ax = fig.add_subplot(gs[0, 1]); axes.append(clean(ax, grid="both"))
    x = ref.year.to_numpy(dtype=float)
    ax.bar(x - 0.16, ref.denominator, width=0.32, color=ORANGE, label=L_HIGH, zorder=2)
    ax.bar(x + 0.16, ref.numerator, width=0.32, color=PINK, label=L_HIGH_REF, zorder=2)
    for r in ref.itertuples():
        # each n labels the bar it belongs to: 09600215 (denominator) and 09600216 (numerator)
        _ann(ax, r.year - 0.16, r.denominator, f"n={_n(r.n_est_denominator)}")
        _ann(ax, r.year + 0.16, r.numerator, f"n={_n(r.n_est)}")
    ax.set_xticks(x); ax.set_xlim(2022.5, 2024.5)
    ax.set_ylim(0, float(ref.denominator.max()) * 1.45)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_ylabel(U_SCREEN, fontsize=FS_BASE); ax.set_xlabel("Year", fontsize=FS_BASE)
    _legend(ax, "upper left", fontsize=FS_TICK)
    ax2 = ax.twinx()
    ax2.errorbar(x, ref.pct, yerr=[ref.pct - ref.lo, ref.hi - ref.pct], fmt="D", ms=6,
                 color=DARK, ecolor=DARK, elinewidth=1.3, capsize=3, zorder=5)
    for r in ref.itertuples():
        _ann(ax2, r.year, r.hi, _pct(r.pct), dy=4)
    ax2.set_ylim(0, 100); ax2.grid(False)
    ax2.set_ylabel(SHARE_REFERRED, fontsize=FS_TICK)
    titles.append(_title(ax, T_B))

    # (c) part-2 outcomes ------------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 0]); axes.append(clean(ax, grid="both"))
    x = second.year.to_numpy(dtype=float)
    ax.bar(x - 0.22, second.medium_in_part1, width=0.21, color=GOLD, label=SHORT["09600217"], zorder=2)
    ax.bar(x, second.no_referral, width=0.21, color=BLUE, label=SHORT["09600218"], zorder=2)
    ax.bar(x + 0.22, second.referral, width=0.21, color=GREEN, label=SHORT["09600219"], zorder=2)
    crowded = []
    for r in second.itertuples():
        # each n labels its own bar; the percentage referred sits over the referral bar
        _ann(ax, r.year + 0.22, r.referral,
             f"{_pct(r.referral_pct)}\n({_ci(r.referral_lo, r.referral_hi)})\nn={_n(r.n_est)}", fs=FS_CELL)
        crowded.append(_ann(ax, r.year, r.no_referral, f"n={_n(r.n_est_no_referral)}"))
        if pd.notna(r.medium_in_part1):
            crowded.append(_ann(ax, r.year - 0.22, r.medium_in_part1, f"n={_n(r.n_est_medium)}"))
    ax.set_xticks(x); ax.set_xlim(2022.5, 2024.5)
    ax.set_ylim(0, float(np.nanmax([second.medium_in_part1.max(), second.no_referral.max(),
                                    second.referral.max()])) * 1.62)
    ax.yaxis.set_major_formatter(thousands("en"))
    ax.set_ylabel(U_SCREEN, fontsize=FS_BASE); ax.set_xlabel("Year", fontsize=FS_BASE)
    _legend(ax, "upper left", fontsize=FS_ANN)
    _spread(ax, crowded)
    titles.append(_title(ax, T_C))

    # (d) the six 31–59-month codes of the 2024 era ----------------------------------------------
    ax = fig.add_subplot(gs[1, 1]); axes.append(clean(ax, grid="both"))
    s = era[2024]
    # Transposed axis: six code labels do not fit under a 90 mm x-axis without overlapping or
    # dropping below the 6 pt floor; horizontal bars give each label its own line.
    yb = np.arange(len(s))
    ax.barh(yb, s.total.to_numpy(dtype=float), color=COL_D, height=0.68, zorder=2)
    for i, r in enumerate(s.itertuples()):
        ax.text(r.total, i, f" {_n(r.total)} (n={_n(r.n)})", va="center", ha="left",
                fontsize=FS_ANN, color=DARK, zorder=6)
    ax.set_yticks(yb); ax.set_yticklabels([_tick_label(SHORT[c]) for c in s.index], fontsize=FS_ANN)
    ax.invert_yaxis()
    ax.set_xlim(0, float(np.nanmax(s.total.to_numpy(dtype=float))) * 1.42)
    ax.xaxis.set_major_formatter(thousands("en"))
    ax.set_xlabel(U_CHILDREN, fontsize=FS_BASE)
    titles.append(_title(ax, T_D))

    # (e) the 2025 redesign ----------------------------------------------------------------------
    ax = fig.add_subplot(gs[2, 0]); axes.append(clean(ax, grid="both"))
    s = era[2025]
    yb = np.arange(len(s))
    ax.barh(yb, s.total.to_numpy(dtype=float), color=COL_E, height=0.72, zorder=2)
    for i, r in enumerate(s.itertuples()):
        ax.text(r.total, i, f" {_n(r.total)} (n={_n(r.n)})", va="center", ha="left",
                fontsize=FS_CELL, color=DARK, zorder=6)
    ax.axhline(2.5, color=DASH_GREY, ls="--", lw=1.0, zorder=3)
    for yy, gloss in ((2.0, MOTIVES), (6.0, RESULTS_2025)):
        ax.text(0.985, yy, _wrap_measured(gloss, 74.0, FS_ANN, "normal"),
                transform=ax.get_yaxis_transform(), ha="right", va="center", linespacing=1.05,
                fontsize=FS_ANN, color=GLOSS_GREY, zorder=6, bbox=dict(NOTE_HALO))
    ax.set_yticks(yb); ax.set_yticklabels([_tick_label(SHORT[c]) for c in s.index], fontsize=FS_CELL)
    ax.invert_yaxis()
    ax.set_xlim(0, float(np.nanmax(s.total.to_numpy(dtype=float))) * 1.45)
    ax.xaxis.set_major_formatter(thousands("en"))
    ax.set_xlabel(U_SCREEN, fontsize=FS_BASE)
    titles.append(_title(ax, T_E))

    # (f) risk composition by era, the break marked ----------------------------------------------
    ax = fig.add_subplot(gs[2, 1]); axes.append(clean(ax, grid="both"))
    pos = [0, 1, 3]
    bottom = np.zeros(3)
    for key, col, lab in (("low_pct", SKY, L_LOW), ("medium_pct", GOLD, L_MED), ("high_pct", ORANGE, L_HIGH)):
        v = comp[key].to_numpy(dtype=float)
        ax.bar(pos, v, bottom=bottom, width=0.62, color=col, label=lab, zorder=2)
        for p_, vi, bi in zip(pos, v, bottom):
            ax.text(p_, bi + vi / 2, _pct(vi), ha="center", va="center", fontsize=FS_ANN, zorder=6,
                    color="white" if key != "low_pct" else DARK,
                    bbox=None if key != "low_pct" else dict(VALUE_HALO))
        bottom = bottom + np.nan_to_num(v)
    ax.axvline(2.0, color=BREAK_GREY, ls="-.", lw=1.1, zorder=1)
    ax.text(2.0, 0.5, DEF_BREAK, transform=ax.get_xaxis_transform(), ha="center", va="center",
            fontsize=FS_ANN, color="#777777", zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))
    for p_, r in zip(pos, comp.itertuples()):
        _ann(ax, p_, 100, f"N={_n(r.part1_total)}\nn={_n(r.n_est)}", fs=FS_CELL)
    ax.set_xticks(pos); ax.set_xticklabels(["2023", "2024", "2025"], fontsize=FS_BASE)
    ax.set_xlim(-0.7, 3.7); ax.set_ylim(0, 138); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel(U_SHARE, fontsize=FS_BASE)
    ax.set_xlabel(NO_CONTINUITY, fontsize=FS_TICK, color="#8a3b12")
    _legend(ax, "upper center", fontsize=FS_ANN, ncol=3)
    titles.append(_title(ax, T_F))

    _letters(fig, axes, titles)
    return fig


# --------------------------------------------------------------------------------------------------
# Verification: every recomputed percentage against the derived rows the table already prints
# --------------------------------------------------------------------------------------------------
def _check():
    comp, ref, second, era, derived = prepare()
    out = []

    row = derived.loc["09600213+09600214+09600215 / 03710016–03710019"]
    for r in comp.itertuples():
        printed = [float(v) for v in _PCT_ONLY.findall(row[str(r.year)])]
        drawn = [round(r.low_pct, 1), round(r.medium_pct, 1), round(r.high_pct, 1)]
        out.append((f"(a)/(f) composition {r.year}", drawn, printed, drawn == printed))

    row = derived.loc["09600216/09600215"]
    for r in ref.itertuples():
        p, lo, hi = _PCT_CI.search(row[str(r.year)]).groups()
        drawn = [round(r.pct, 1), round(r.lo, 1), round(r.hi, 1)]
        printed = [float(p), float(lo), float(hi)]
        out.append((f"(b) high risk referred {r.year}", drawn, printed, drawn == printed))

    row = derived.loc["09600219 / (09600218+09600219)"]
    for r in second.itertuples():
        p, lo, hi = _PCT_CI.search(row[str(r.year)]).groups()
        drawn = [round(r.referral_pct, 1), round(r.referral_lo, 1), round(r.referral_hi, 1)]
        printed = [float(p), float(lo), float(hi)]
        out.append((f"(c) part-2 referred {r.year}", drawn, printed, drawn == printed))

    totals = [("(a) 2023 part-1 total", comp.part1_total.iloc[0], 19632.0),
              ("(a) 2024 part-1 total", comp.part1_total.iloc[1], 25074.0),
              ("(f) 2025 part-1 total", comp.part1_total.iloc[2], 19289.0),
              ("(d) 2024 codes drawn", float(len(era[2024])), 6.0),
              ("(e) 2025 codes drawn", float(len(era[2025])), 9.0)]
    for name, a, b in totals:
        out.append((name, a, b, a == b))
    return out


if __name__ == "__main__":
    for name, drawn, printed, ok in _check():
        print(f"{'ok ' if ok else 'BAD'} {name}: redrawn {drawn} vs table {printed}")
    fig = draw()
    if len(sys.argv) > 1:                      # python3 <this file> <preview.png>
        fig.savefig(sys.argv[1], dpi=150, facecolor="white")
        print("wrote", sys.argv[1])
