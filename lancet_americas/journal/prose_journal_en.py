# -*- coding: utf-8 -*-
"""prose_journal_en.py — the submission article (English, sin_rett) for The Lancet Regional Health – Americas.

Public API
----------
    article(V, plate_dir=None) -> list of docx_builder blocks: title page, Summary (five paragraphs), Research in
        context panel, Introduction … Conclusion, the declarations, ("refs", None), Table 1, Table 2, Figures 1–4.
    legend_word_counts(blocks) -> {label: words of the legend body}
    body_legend(R, key), body_note(R, key) -> the body legends / notes assembled from corpus fragments.

Conventions (journal/plan.md, sections 1, 3 and 7.2)
------------------------------------------------------
* Every number comes from values_sin_rett.json through prose_en's helpers (n0, n1, n2, pct, ppct, nw, millions,
  _V.series) or from a tidy row through journal_config.tidy_value/tidy_count; the two documented derivations are
  the Census effect (ine_ratio_censo2024_base2017_2024) and the ENDIDE male:female ratio (two sex keys). Nothing
  is typed by hand. Confidence intervals are printed "a–b" (en rule) with the corpus number formatter.
* The body legends and the two body-table notes are assembled from VERBATIM fragments of the corpus captions.json
  / titles.json (asserted to be substrings) joined by digit-free connectives, so every number a legend prints is a
  number the corpus caption prints.
* Cross-references use journal_config.JournalRegistry only (R.fig/R.tab/R.mfig/R.mtab/R.mfigp); the registry
  records first citations and assert_monotone() guards the numbering of the supplement.
* House style in the prose: numbers one to ten in words except with units; no bold except the Summary labels;
  medians with IQR; p values through journal_config.format_p. The mid-height decimal point and the thousands rule
  are applied by journal_config.journal_text at build time, after word counting.
* Standing rules of the study are restated in the docstring of prose_en.py and honoured here verbatim.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(HERE), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
import common as C  # noqa: E402  (the single source of the fixed-panel gloss)
import controls_registry as CR  # noqa: E402
import equations_lancet as EQ  # noqa: E402
import journal_config as JC  # noqa: E402
import prose_en as PE  # noqa: E402
import supplementary_material as SM  # noqa: E402  (sizes of the corpus registries, named in the data sharing statement)
from prose_en import (AFFILIATION, AUTHOR, AUTHOR_EMAIL, RUNNING_TITLE, TITLE, YEARS_A05, YEARS_A27,  # noqa: E402
                      YEARS_GRD, YEARS_REM, millions, n0, n1, n2, nw, pct, ppct)

LANG = "en"
VARIANT = JC.VARIANT
VLABEL = "F84 family excluding Rett syndrome (F84.2)"
PLAN_DATE = "4 September 2026"      # analysis plan v1.0 (appendix Part A, section A9)

# ---------------------------------------------------------------------------
# Compact interval helpers (numbers through the corpus formatter; en rule between limits)
# ---------------------------------------------------------------------------
def cir(lo, hi, dec=1) -> str:
    return f"{PE.fmt_number(lo, dec, LANG)}–{PE.fmt_number(hi, dec, LANG)}"


class _K:
    """Strict accessor plus the compact estimate formats of the journal text."""

    def __init__(self, V: dict):
        self.k = PE._V(V, VARIANT)

    def __call__(self, key):
        return self.k(key)

    def series(self, tmpl, years, dec=0):
        return self.k.series(tmpl, years, dec)

    def apc(self, alias, dec=1):
        return f"{PE.fmt_number(self(alias), dec, LANG)}% (95% CI {cir(self(alias + '_lo'), self(alias + '_hi'), dec)})"

    def rate(self, prefix, year, dec=1):
        return (f"{PE.fmt_number(self(f'{prefix}_rate_{year}'), dec, LANG)} (95% CI "
                f"{cir(self(f'{prefix}_rate_lo_{year}'), self(f'{prefix}_rate_hi_{year}'), dec)})")

    def est_y(self, prefix, year, dec=1):
        return (f"{PE.fmt_number(self(f'{prefix}_{year}'), dec, LANG)} (95% CI "
                f"{cir(self(f'{prefix}_lo_{year}'), self(f'{prefix}_hi_{year}'), dec)})")

    def svy(self, base, dec=2):
        return f"{pct(self(base + '_pct'), dec)} (95% CI {cir(self(base + '_lo_pct'), self(base + '_hi_pct'), dec)})"


# ---------------------------------------------------------------------------
# Legends and notes from caption / note fragments
# ---------------------------------------------------------------------------
_LABEL_TOKEN_RE = re.compile(r"\b(?:Figures?|Tables?|Figuras?|Tablas?)\s+S?\d+(?:[–-]S?\d+)?[a-f]?(?:[–-][a-f])?\b"
                             r"|\bF84(?:\.\d)?\b|\b[AP]\d{1,2}\b|\bREM-20\b|\bICD-10\b")


def _join(parts: list[str]) -> str:
    text = " ".join(p for p in parts if p)
    text = re.sub(r"\s+([.,;:)])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def assemble_fragments(source: str, parts: list[str], what: str) -> str:
    """Join caption/note fragments. A part starting with '~' is a connective and must carry no digit (except
    inside a registry label such as 'Table S41' or an identifier such as F84 or A05); a part starting with '=' is
    computed text whose numbers come from the registry or the values file; every other part must be a verbatim
    substring of `source`."""
    out = []
    for part in parts:
        if part.startswith("="):
            out.append(part[1:])
        elif part.startswith("~"):
            conn = part[1:]
            if re.search(r"\d", _LABEL_TOKEN_RE.sub("", conn)):
                raise ValueError(f"{what}: connective carries a digit: {conn!r}")
            out.append(conn)
        else:
            if part not in source:
                raise ValueError(f"{what}: fragment is not in the corpus text: {part[:70]!r}")
            out.append(part)
    return _join(out)


def _legend_parts(R: JC.JournalRegistry) -> dict:
    """Body legends (Figures 1–4): fragments of the corpus captions, in reading order, with the appendix pointers
    of the plan; the legend heading (10 pt bold) is the stored title and is added by the registry."""
    return {
        "fig1_dataflow": [
            "No record is linked across systems: the six lanes share no identifier; nothing here is a trajectory or "
            "a cascade, and one person may be counted in more than one lane.",
            "Persons are counted only within a year: the GRD identifier changes format between 2020 and 2021.",
            "Counts are administrative recognition, not prevalence or incidence; in GRD they are 'episodes with "
            "documented F84', principal F84 being a separate series; stocks and flows never share an axis; zero, "
            "missing", "~,", "and 'not reported' are distinct; place of care and residence are never mixed without a warning;",
            "~territorial cells with fewer than five events are suppressed;",
            "and no effect of Law 21.545 (March 2023) is estimated.",
            f"~Every count printed, with its unit, source, and column, and the drawing conventions are in appendix "
            f"{R.tab('T_dataflow_counts')}.",
        ],
        "fig2_grd_core": [
            "(a) Episodes with F84 in any position and with principal F84 per 100,000 GRD episodes of the same panel "
            "and year", "~,", "observed annual panel (65, 65, 65, 65, 68 and 72 hospitals in 2019–2024", "~)",
            "and fixed panel of 65 hospitals.",
            "(b) Observed panel by activity: all activity, strict hospitalisation", "~,",
            "and major ambulatory surgery (CMA), any position; the 'other' category is absent from the 2020–2024 files "
            "(absence, not zero).",
            "(c) F84 rate per 100,000 episodes within each coding-depth stratum (coded diagnoses per episode) in 2019 "
            "and 2024 with exact CIs; inset: mean depth of all episodes and of episodes with F84 by year",
            "~(means only; no dispersion is drawn).",
            "(d) Episodes with F84 (any position) per 100,000 INE population (base 2017, national) by age group",
            "and sex, 2019 versus 2024", "~:",
            "the numerator is located by place of care (public GRD hospitals) and the denominator by residence, so "
            "this is a complementary reading and not a use rate for a defined population.",
            "(e) F84 rate per 100,000 episodes of each hospital in 2024", "~,",
            "with exact CIs and the national rate (804); the five hospitals with the highest rate are numbered 1–5 "
            "and the three lowest x, y", "~,", "and z",
            f"~(every hospital in appendix {R.tab('S_hospital_rates_2024')}).",
            "(f) Episodes with F84 and unique persons within each year, in thousands (no deduplication across years: "
            "the identifier changes format between 2020 and 2021), episodes per person", "~,",
            "and the male:female ratio of episodes with 95% CIs (right axis).",
            "Grey band: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context", "~.",
            "Counts are administrative recognition", "~(episodes with documented F84)", ", not prevalence or incidence.",
        ],
        "fig3_rem_pathway": [
            "All values are annual administrative counts from the public network", "~;",
            "sources are not person-linked and no ratio between panels represents an individual probability.",
            "~No series crosses a break.",
            "(a) A03 detection in primary care, log scale, one dot per year", "~per era:",
            "2019–2022 M-CHAT done", "and altered",
            "only among children with a language or social-area alteration at the 18-month control (neither "
            "population coverage nor positivity); 2023–2024 M-CHAT-R/F", "~risk categories and referral.",
            "(b) A03 in the following eras, read the same way: 2024 codes", "~for", "ages 31–59 months",
            "and the 2025 redesign", "~; not mutually comparable.",
            "(c) A27 counselling", "and assisted referral", "~, and", "A28 rehabilitation entries for ASD at primary",
            "and hospital level", ", 2023–2025: interventions and entries, not persons", "~.",
            "(d) A05 mental-health programme entries and clinical discharges on a single axis with the definition "
            "break marked: broad PDD 2019–2020", "and strict autism 2021–2025",
            "with the variant's PDD family", "as lighter lines; grey line and right axis: reporting establishments.",
            "(e) P2 NANEAS population with ASD under control",
            ": December stock (filled points) and June stock (hollow markers, sensitivity; semesters are never "
            "summed); grey lines and right axis: establishments with a December and a June row; text: ASD per 100 "
            "total NANEAS", "~.",
            "(f) P6 population under control in December on a single axis with the break marked: broad PDD 2019–2020",
            "and strict autism 2021–2025", "~.",
            "Grey shading: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context, not as an "
            "intervention", "~.",
            "Counts are administrative recognition, not prevalence or incidence; stocks (e, f) and flows (a, b, c, d) "
            "never share an axis.",
        ],
        "fig4_triangulation": [
            "(a) Autistic students in the School Integration Programme (PIE; annual school stock, national enrolment): "
            "strict ASD and ASD-Asperger 2019–2023", ", the harmonised ASD + Asperger series 2019–2025", "~, and",
            "autism in special schools 2022–2025.",
            "(b) JUNAEB (Student Vulnerability Survey): % of students with caregiver-reported ASD by level; 2024",
            "and 2025", "with 95% CIs; 2023 has no published weight", "~;",
            "2019–2022 have no ASD item and Grade 9 in 2024 has an empty variable, both marked 'not estimable'",
            "and never as zero.",
            "(c) Design-based weighted proportions",
            ": ENDIDE 2022 adults 18+, children 2–17 with caregiver-reported autism and with physician-confirmed "
            "report, and ENCAVI 2023–2024 persons 15+ with an ASD diagnosis", "~; imprecise estimates in grey.",
            "(d) Indices (first common year 2021 = 100; log scale)", "~:",
            "GRD F84 in any position per 100,000 episodes (observed panel), DEIS principal F84 per 100,000 "
            "discharges, A05 autism entries", ", P2 December stock", "~,", "and harmonised PIE", "~;",
            "these are indices, not comparable levels.",
            "(e) Five stacked strips, each with its own vertical axis, per 100,000 INE population", "~(residence)",
            ": GRD episodes with F84 (variant), unique persons within the year, A05 entries", "~,", "and the P2 December "
            "stock (numerators by place of care, public network; n = reporting establishments)", "~,", "and harmonised PIE.",
            "Hatched bars are stocks and solid bars flows, and they never share an axis", "~.",
            "(f) F84 in the principal position: DEIS discharges (all establishments and the SNSS subset) per 100,000 "
            "discharges against GRD episodes", "~(n = hospitals)", "per 100,000 episodes, exact 95% Poisson CIs;",
            "~a coverage comparison between two registries of the same event, not a probability.",
            "Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context, not as an "
            "intervention", "~.",
            "Sources are not person-linked; counts are administrative recognition, not prevalence or incidence.",
        ],
    }


def _table_note_parts(R: JC.JournalRegistry) -> dict:
    """Body-table notes: source, unit, panel and the standing-rule sentences, from the corpus notes."""
    n_t2, n_t7, n_cpa = R.nrows("T2_grd_core"), R.nrows("T7_models"), R.nrows("T7_models_cpa_full")
    return {
        "T2_grd_core": [
            "Source: public GRD (FONASA) 2019–2024, module 01_grd_core (grd_year_summary.csv, grd_subcode_year.csv) "
            "and module 06_models (models_population_rates.csv).",
            "Unit: GRD episode (hospitalisation or major ambulatory surgery); 'F84 in any position' = episodes with "
            "documented F84", "~;", "F84 principal as a separate series.",
            "Rate denominator: GRD episodes of the same year, panel", "~,", "and activity, per 100,000, with exact Poisson 95% CIs.",
            "Coverage: observed panel of 65/65/65/65/68/72 hospitals (2019–2024);",
            C.fixed_panel_gloss("en", "named") + ".",
            "Unique persons within each year only (the identifier changes format between 2020 and 2021; "
            "CIP_ENCRIPTADO 2019–2023, ID_BENEFICIARIO 2024); never deduplicated across years.",
            "Rates per 100,000 population: numerator by place of care (public network) and INE base-2017 "
            "denominator at 30 June (residence), complementary reading; WHO age-standardised rate with Fay–Feuer CI.",
            "The 'F84.0 only' row is identical in both variants.",
            "All counts are administrative recognition, not prevalence or incidence.",
            "Law 21.545 (March 2023) is policy context, not an intervention with an identifiable causal effect.",
            f"=The complete table ({n0(n_t2)} rows, including the full-family rates, coding-depth summaries, and "
            f"principal-F84 population rates) is appendix {R.tab('T2_grd_core')}.",
        ],
        "T7_models": [
            f"=Twenty-nine of the {n0(n_t7)} pre-specified specifications of appendix {R.tab('T7_models')}; every "
            f"one of the {n0(n_cpa)} converged specifications is in appendix {R.tab('T7_models_cpa_full')}.",
            "Quasi-Poisson log-linear models (Pearson scale) with the stated offset; APC = 100·(exp(β) − 1) with "
            "Wald 95% CI; dispersion = Pearson χ² / df.",
            "~p values are Wald tests to two significant figures.",
            "GRD: episodes with documented F84 per 100,000 GRD episodes of the same panel and activity (observed "
            "panel 65/65/65/65/68/72 hospitals; fixed panel 65); hospital-year with hospital fixed effects and "
            "log(episodes) offset, hospital-clustered SE", "~,", "and a Poisson random intercept as sensitivity; per 100,000 "
            "population with a place-of-care numerator and INE base-2017 denominator (residence).",
            "REM A05 2021–2025 (autism-code era; broad PDD 2019–2020 not modelled; fewer establishments report in "
            "2025); P2 and P6 are December stocks (June sensitivity only; never summed); harmonised PIE = Apuntes 60 "
            "(2019–2023) and SINACES (2024–2025); DEIS F84 in DIAG1 only, comparable solely with GRD principal.",
            "The 2020–2021 indicator describes reporting disruption and no specification estimates a causal effect "
            "of Law 21.545 (March 2023).",
            "All counts are administrative recognition, not prevalence or incidence.",
        ],
    }


def body_legend(R: JC.JournalRegistry, key: str) -> str:
    return assemble_fragments(R.caption_text(key), _legend_parts(R)[key], f"legend of {key}")


def body_note(R: JC.JournalRegistry, key: str) -> str:
    return assemble_fragments(R.note_text(key), _table_note_parts(R)[key], f"note of {key}")


def legend_word_counts(blocks: list) -> dict:
    """Words of each figure legend as printed (heading included), the count build_journal holds to the caps."""
    return {payload["label"]: len(str(payload["caption"]).split()) for kind, payload in blocks if kind == "figure"}


# ---------------------------------------------------------------------------
# The article
# ---------------------------------------------------------------------------
def _eq(name: str) -> str:
    return str(EQ.NUMBER[name])


def _eqs(a: str, b: str) -> str:
    return f"{_eq(a)}–{_eq(b)}"


M_TABLES = ["M1_sources_units", "M2_case_definitions", "M3_rem_code_sets", "M4_denominator_layers",
            "M5_estimator_map", "M6_sensitivity_grid", "M7_data_states", "M8_pipeline_map", "M9_software_seeds",
            "M10_reproduction_controls"]


def territory_numbers() -> dict:
    """Every number of the Territory paragraph, read from the tidy tables (file, filters and column named)."""
    spatial = dict(variant=VARIANT, scope="comuna", indicator="grd_episodes", value_type="sir_eb",
                   years="full period", subset="all comunas")
    lisa = dict(variant=VARIANT, indicator="grd_episodes", value_type="sir_eb", weights="queen")
    ineq = dict(variant=VARIANT, indicator="grd_episodes")
    corr = dict(variant=VARIANT, scope="comuna", indicator_x="grd_episodes", indicator_y="a05_entries",
                value_type_x="sir_eb")
    return dict(
        moran={w: JC.tidy_value("spatial_moran.csv", {**spatial, "weights": w}, "morans_i")
               for w in ("queen", "knn4", "knn8", "idw")},
        moran_p=JC.tidy_value("spatial_moran.csv", {**spatial, "weights": "queen"}, "p_sim"),
        moran_perm=JC.tidy_value("spatial_moran.csv", {**spatial, "weights": "queen"}, "permutations"),
        n_lisa=JC.tidy_count("spatial_lisa.csv", lisa),
        hh=JC.tidy_count("spatial_lisa.csv", {**lisa, "lisa_bh_reject": True, "lisa_class": "HH"}),
        ll=JC.tidy_count("spatial_lisa.csv", {**lisa, "lisa_bh_reject": True, "lisa_class": "LL"}),
        lh=JC.tidy_count("spatial_lisa.csv", {**lisa, "lisa_bh_reject": True, "lisa_class": "LH"}),
        hot=JC.tidy_count("spatial_lisa.csv", {**lisa, "gi_bh_reject": True, "gi_class": "hot"}),
        cold=JC.tidy_count("spatial_lisa.csv", {**lisa, "gi_bh_reject": True, "gi_class": "cold"}),
        gini={y: JC.tidy_value("spatial_inequality.csv", {**ineq, "years": y}, "gini") for y in (2019, 2024)},
        with_events={y: JC.tidy_value("spatial_inequality.csv", {**ineq, "years": y}, "n_comunas_with_events")
                     for y in (2019, 2024)},
        n_comunas=JC.tidy_value("spatial_inequality.csv", {**ineq, "years": 2024}, "n_comunas"),
        top_decile={y: JC.tidy_value("spatial_inequality.csv", {**ineq, "years": y}, "top_decile_event_share")
                    for y in (2019, 2024)},
        total_count={y: JC.tidy_value("spatial_inequality.csv", {**ineq, "years": y}, "total_count")
                     for y in (2019, 2024)},
        rho=JC.tidy_value("spatial_correlations.csv", corr, "rho"),
        rho_lo=JC.tidy_value("spatial_correlations.csv", corr, "rho_lo"),
        rho_hi=JC.tidy_value("spatial_correlations.csv", corr, "rho_hi"),
    )


GRD_AGE_FILTERS = dict(year=2024, variant=VARIANT, panel="observed", position="any", activity="all")
GRD_AGE_BANDS_0_9 = ["0-4", "5-9"]
GRD_AGE_BANDS_20PLUS = ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69",
                        "70-74", "75-79", "80+"]
GRD_AGE_BANDS_KNOWN = ["0-4", "5-9", "10-14", "15-19"] + GRD_AGE_BANDS_20PLUS


def grd_age_count(bands: list, share_key: str, V: dict) -> tuple[float, float]:
    """Documented derivation 3 (readers, round 2: n beside every %): the numerator and the base of an age-band share
    of GRD episodes with F84 (observed panel, any position, all activity, 2024), summed over both sexes and the
    five-year cells of outputs/tidy/grd_age_sex_year.csv; the base is the episodes with a known age, which is the
    base of the share key, and the quotient is asserted equal to that key (four decimals) before anything prints."""
    n = JC.tidy_sum("grd_age_sex_year.csv", GRD_AGE_FILTERS, "n_f84", rows=dict(age_group=bands))
    base = JC.tidy_sum("grd_age_sex_year.csv", GRD_AGE_FILTERS, "n_f84", rows=dict(age_group=GRD_AGE_BANDS_KNOWN))
    share = float(V[share_key])
    if abs(n / base - share) > 5e-5:
        raise ValueError(f"{share_key}: tidy sum {n}/{base} = {n / base:.5f} does not reproduce the share {share:.5f}")
    return n, base


def a05_age_0_9_count(V: dict) -> float:
    """Documented derivation 4: A05 strict-autism entries aged 0–9 in 2025 = the two five-year cells of the values
    file (a05_autism_entries_both_0_4_2025 + a05_autism_entries_both_5_9_2025), asserted against the share key."""
    n = float(V["a05_autism_entries_both_0_4_2025"]) + float(V["a05_autism_entries_both_5_9_2025"])
    if abs(n / float(V["a05_autism_entries_2025"]) - float(V["a05_autism_entries_share_age_0_9_2025"])) > 5e-5:
        raise ValueError("a05_autism_entries_share_age_0_9_2025 is not reproduced by the two five-year cells")
    return n


def article(V: dict, plate_dir: Path | None = None) -> list:
    """Blocks of the submission article (see the module docstring). `plate_dir` overrides the journal plate
    folder of the body figures (previews and tests only; the build reads journal_config.PLATE_DIR)."""
    k = _K(V)
    jn = lambda lvl, y: f"{n0(k(f'junaeb_{lvl}_all_tea_n_{y}'))}/{n0(k(f'junaeb_{lvl}_all_n_answered_{y}'))}"  # noqa: E731
    mill = lambda key: PE.fmt_number(k(key) / 1e6, 1, LANG)  # noqa: E731  («17·1 of 20·2 million»)
    grd_0_9, grd_age_base = grd_age_count(GRD_AGE_BANDS_0_9, "grd_f84_any_share_age_0_9_2024", V)
    grd_20plus, _ = grd_age_count(GRD_AGE_BANDS_20PLUS, "grd_f84_any_share_age_20plus_2024", V)
    a05_0_9 = a05_age_0_9_count(V)
    R = JC.JournalRegistry(LANG, plate_dir=plate_dir)
    doc = PE._Doc()
    T = lambda key: R.tab(key)  # noqa: E731
    F = lambda key: R.fig(key)  # noqa: E731
    TR = lambda keys: R.tabs_range(keys)  # noqa: E731
    FR = lambda keys: R.figs_range(keys)  # noqa: E731

    # ---------------- Title page ----------------
    doc.add("title", TITLE)
    # Journal title-page rule: name, preferred degree (one only), affiliation with full address, and the
    # corresponding author's name, address, email and telephone. Degree, addresses and telephone are
    # author-supplied and stay bracketed (never invented). No word counts or build metadata on the submission.
    doc.add("authors", dict(authors=[(f"{AUTHOR} [preferred degree, one only: to be completed by the author]", "1")],
                            affiliations=[("1", f"{AFFILIATION} [full postal address of the affiliation: to be "
                                                f"completed by the author]")],
                            lines=[f"Corresponding author: {AUTHOR}; [postal address: to be completed by the author]; "
                                   f"{AUTHOR_EMAIL}; telephone [to be completed by the author].",
                                   f"Running title: {RUNNING_TITLE}.",
                                   "Article type: Article (original research). Reporting guidelines: STROBE "
                                   "(Strengthening the Reporting of Observational Studies in Epidemiology) and RECORD "
                                   "(REporting of studies Conducted using Observational Routinely-collected health Data)."]))

    # ---------------- Summary (five paragraphs, ≤ 250 words, no references) ----------------
    doc.h1("Summary")
    doc.p("**Background** Recorded autism diagnoses have risen steeply in high-income countries; Latin American "
          "evidence is scarce. We describe how administrative recognition of autism changed across Chile's public "
          "health and education systems in 2019–2025 and its robustness to coverage, coding, and definitions.")
    doc.p("**Methods** National study of unlinked routine data: public-hospital diagnosis-related-group (GRD) episodes "
          "and DEIS discharges (2019–2024), six REM modules (2019–2025), population denominators, two "
          "complex-design surveys, and school registers. We estimated rates per 100,000 GRD episodes and per resident, "
          "WHO-standardised rates, and quasi-Poisson annual percent changes (APC) with pre-specified sensitivities.")
    doc.p(f"**Findings** GRD episodes with documented F84 rose from {n0(k('grd_f84_any_n_2019'))} "
          f"({n1(k('grd_f84_any_rate_2019'))} per 100,000 episodes) in 2019 to {n0(k('grd_f84_any_n_2024'))} "
          f"({n1(k('grd_f84_any_rate_2024'))}) in 2024 (APC {n1(k('apc_grd_any_obs'))}%, 95% CI "
          f"{cir(k('apc_grd_any_obs_lo'), k('apc_grd_any_obs_hi'))}; {n1(k('apc_grd_any_sensitivity_min'))}–"
          f"{n1(k('apc_grd_any_sensitivity_max'))}% across specifications); "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} ({n0(k('grd_f84_secondary_only_n_2024'))} episodes) "
          f"carried F84 only as a secondary diagnosis. "
          f"Strict-autism mental-health entries rose from {n0(k('a05_autism_entries_2021'))} (2021) to "
          f"{n0(k('a05_autism_entries_2025'))} (2025), children with autism under control from "
          f"{n0(k('p2_tea_dec_2019'))} to {n0(k('p2_tea_dec_2025'))} and autistic students in school integration "
          f"from {n0(k('pie_harmonised_2019'))} to {n0(k('pie_harmonised_2025'))}. The male:female ratio of "
          f"hospital episodes fell from {n2(k('grd_f84_any_mf_ratio_n_2019'))} to "
          f"{n2(k('grd_f84_any_mf_ratio_n_2024'))}. ENDIDE 2022 reported autism in "
          f"{pct(k('svy_endide_children_reported_total_pct'), 2)} of children aged 2–17 years "
          f"({n0(k('svy_endide_children_reported_total_cases'))}/{n0(k('svy_endide_children_reported_total_n'))}) and "
          f"{pct(k('svy_endide_adults_reported_total_pct'), 2)} of adults "
          f"({n0(k('svy_endide_adults_reported_total_cases'))}/{n0(k('svy_endide_adults_reported_total_n'))}); "
          f"ENCAVI 2023–24 in {pct(k('svy_encavi_15plus_diagnosed_total_pct'), 2)} of people aged 15 or older "
          f"({n0(k('svy_encavi_15plus_diagnosed_total_cases'))}/{n0(k('svy_encavi_15plus_diagnosed_total_n'))}).")
    doc.p("**Interpretation** Independent health and education systems recorded a several-fold expansion of "
          "administrative recognition, alongside pandemic recovery, reporting expansion, code changes and, from "
          "2023, Law 21.545. Reporting and coding explain part of it; epidemiological change cannot be separated. "
          "Services and surveillance must keep pace.")
    doc.p("**Funding** None.")

    # ---------------- Research in context (no references) ----------------
    doc.add("panel", dict(title="Research in context", items=[
        ("Evidence before this study",
         "We searched PubMed and Crossref on Sept 4, 2026, without language or date restrictions, combining the terms "
         "\"autism\", \"autism spectrum disorder\" or \"pervasive developmental disorder\" with \"administrative data\", "
         "\"register\", \"hospital discharge\", \"surveillance\", \"time trends\", \"prevalence\", \"Chile\" and \"Latin "
         "America\", and we searched on the same date the official portals of the Chilean Ministry of Health (DEIS), FONASA, "
         "the Superintendencia de Salud, the National Statistics Institute, the Ministry of Education, JUNAEB, the Ministry "
         "of Social Development, and the Library of the National Congress for data documentation, methodological reports, and "
         "the text of Law 21.545; every retained record was verified against its PubMed or Crossref metadata or the official "
         "page. Register-based studies from the UK, Denmark, Sweden, and the USA show large increases in recorded autism "
         "diagnoses, attributable largely to diagnostic criteria, service contact, and awareness rather than to changes in the "
         "underlying phenotype. Latin American evidence is limited to a few local prevalence surveys, caregiver surveys "
         "documenting diagnostic delay and access barriers, and, for Chile, one urban screening-based prevalence estimate and "
         "one school-register-based estimate. The quality of that evidence is uneven: the register studies are national "
         "cohorts at low risk of selection bias whose outcome, like ours, is an unvalidated administrative code; the Latin "
         "American estimates come from single-city screening or convenience samples at moderate to high risk of selection "
         "and information bias; and the official documentation is descriptive, with no risk-of-bias appraisal possible. "
         "No study has examined how several unlinked administrative systems of a Latin "
         "American country recorded autism over the same period, nor quantified how much of the recorded change survives "
         "adjustment for reporting coverage, coding depth, and definition breaks."),
        ("Added value of this study",
         "Using every public routine source in Chile that carries an autism code or item (hospital GRD episodes, DEIS "
         "discharges, six REM modules, insurance, primary-care, and population denominators, two national surveys, and school "
         "registers), with frozen provenance and pre-specified reproduction controls, we show that administrative recognition "
         "of autism rose several-fold between 2019 and 2025 in the hospital, outpatient, rehabilitation, and educational "
         "systems; that the increases converge in timing and direction despite different units, coverage, and definitions; "
         "and that coding depth, reporting expansion, and definition changes explain part, but not all, of the recorded "
         "change. We separate stocks from flows, place of care from residence, and definition eras from one another, and we "
         "report the number of reporting establishments next to every count."),
        ("Implications of all the available evidence",
         "Administrative recognition is an actionable measure of demand for diagnosis, care, and educational support even "
         "when it cannot be read as prevalence. In Chile, and in other segmented Latin American systems, the observed "
         "expansion implies growing needs for diagnostic capacity, primary-care follow-up, rehabilitation, and school "
         "integration, and for surveillance that records coverage and coding rules explicitly. Whether the change reflects "
         "unmet need becoming visible or a rising occurrence of autism cannot be resolved with unlinked records; "
         "person-level linkage, validation of codes, and repeated population surveys are needed."),
    ]))

    # ---------------- Introduction ----------------
    doc.h1("Introduction")
    doc.p("Autism is estimated to affect about 1% of the world's population [@zeidan2022], and recorded diagnoses have "
          "risen steeply wherever population registers exist. Register-based studies in the "
          "UK, Denmark, and Sweden attribute most of that rise to changes in diagnostic criteria, the inclusion of "
          "outpatient contacts, awareness, and service capacity rather than to a change in the underlying phenotype "
          "[@russell2022; @hansen2015; @lundstrom2015], and the multisource surveillance network of the USA continues "
          "to document increasing identified prevalence with linked health and education records [@shaw2025]. The "
          "Lancet Commission on autism called for national data systems able to monitor identification, needs, and "
          "services [@lord2022].")
    doc.p(f"Latin America contributes little to this evidence: population-based prevalence estimates exist for few "
          f"countries [@zeidan2022], caregiver surveys document long diagnostic delays and access barriers "
          f"[@montielnava2024], and "
          f"routinely collected records have rarely been analysed. Chile has a segmented health system in which the "
          f"public insurer FONASA covered {pct(k('share_fonasa_ine_pct_2025'))} of residents in 2025 "
          f"({mill('fonasa_beneficiaries_2025')} of {mill('ine_pop_total_2025')} million) and private "
          f"ISAPRE insurers a shrinking minority ({pct(k('share_isapre_ine_pct_2025'))}; "
          f"{millions(k('isapre_beneficiaries_2025'))}); it has one urban prevalence "
          f"estimate [@yanez2021] and one school-register estimate [@romanurrestarazu2025]. Law 21.545, in force "
          f"since March 2023, established rights to inclusion, care, "
          f"and protection for autistic people and created reporting duties for the health and education sectors "
          f"[@ley21545].")
    doc.p("Chile's public health and education systems produce several routine datasets that record autism: hospital "
          "diagnosis-related-group (GRD) episodes, hospital discharges (DEIS), monthly statistical reports (REM), the "
          "registers of the School Integration Programme (PIE) and a caregiver survey of whole school cohorts. They "
          "differ in unit of observation, coverage, definitions, and reporting rules, are not linked by person, and were "
          "designed for payment and management rather than surveillance. Counts derived from them measure "
          "administrative recognition, the recording of an autism code in a contact with a service, not the "
          "prevalence or incidence of autism.")
    doc.p("We asked how administrative recognition of autism and the registered demand for services changed between "
          "2019 and 2025 across Chile's public health and education systems, and how much of the change is robust to "
          "variations in coverage, coding intensity, and definitions. The contribution is descriptive: to show whether "
          "independent systems converge, to quantify the threats to comparability, and to translate the findings into "
          "surveillance and service-capacity needs. Law 21.545 is treated as policy context that coincides with "
          "pandemic recovery, expansion of reporting, code changes, and deeper coding; no effect of the law is "
          "estimated.")

    # ---------------- Methods ----------------
    doc.h1("Methods")
    doc.h2("Study design and setting")
    doc.p(f"This is a national multisource descriptive study of routinely collected data. The applied methodology is "
          f"in the appendix (Part A, {TR(M_TABLES)}); the study follows the "
          f"STROBE statement and its RECORD extension [@vonelm2007; @benchimol2015] (appendix "
          f"{T('S_reporting_checklist')}) and reports results by sex following the SAGER guidelines: sex is the sex "
          f"recorded by each register or declared to each survey, no source records sex assigned at birth or gender, "
          f"and no gender variable was analysed; the "
          f"pre-specified analysis plan (version 1.0, {PLAN_DATE}) is reproduced in the appendix "
          f"(Part A, section A9), with every deviation in the decision log. The setting is Chile (projected resident "
          f"population {millions(k('ine_pop_total_2019'))} in 2019 and {millions(k('ine_pop_total_2025'))} in 2025), "
          f"whose public network comprises the SNSS hospitals and mainly municipal primary care (APS); the hospital "
          f"sources end in 2024.")
    doc.h2("Data sources and units of observation")
    doc.p(f"Appendix {T('T1_sources')} and {R.mfig('fig1_dataflow')} describe the sources, units, coverage, and "
          f"definition breaks (counts of {R.mfig('fig1_dataflow')}: appendix {T('T_dataflow_counts')}). Hospital "
          f"care was measured with the public GRD files, in which the unit is one episode (hospitalisation or major "
          f"ambulatory surgery, CMA) with up to "
          f"{n0(k('grd_diagnosis_positions'))} coded diagnoses, from SNSS hospitals. The observed panel comprised "
          f"{k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitals in 2019–2024; the "
          f"{n0(k('grd_fixed_panel_n'))} hospitals present in every year form the fixed panel used as a sensitivity, "
          f"and the {n0(k('grd_hospitals_ever_observed_n'))} ever observed are not a panel (appendix "
          f"{T('ST1_grd_hospital_panel')}). The person identifier changes format between 2020 and 2021, so unique "
          f"persons are counted only within each year (appendix {T('ST8_grd_identifier_audit')}). DEIS discharges "
          f"from all establishments, which carry the principal diagnosis only, were an external check homologous "
          f"only with principal F84.")
    doc.p(f"Ambulatory activity was measured with the REM monthly reports, whose unit is one establishment × month × "
          f"code row; reporting completeness by module and year (zero, missing, and not reported as distinct states) is "
          f"in appendix {F('fig1_sources_coverage')}. Series A modules are flows: A03 (developmental screening), A27 "
          f"(counselling and assisted referral, from 2023; interventions, not persons), A05 (entries to and "
          f"discharges from mental-health programmes), and A28 (entries to rehabilitation, from 2023). Series P "
          f"modules are semi-annual stocks of people under control: P2 (NANEAS with autism) and P6 (mental-health "
          f"programmes); December is the "
          f"primary cut and June a sensitivity, never summed. The {n0(k('rem_pathway_codes_n'))} pathway codes were "
          f"verified against each year's official dictionary (appendix {T('ST2_rem_code_dictionary')}); no "
          f"series crosses a definition break (appendix {T('S_definition_breaks')}), and the establishments reporting "
          f"each code and year (appendix {T('ST3_rem_reporting_establishments')}) accompany every count.")
    doc.p(f"Population benchmarks came from two complex-design surveys: the 2022 National Disability and Dependence "
          f"Survey (ENDIDE; autism reported by adults aged 18 years or older and by caregivers of children aged 2–17 "
          f"years, with a physician-confirmation item) and the 2023–24 National Quality of Life and "
          f"Health Survey (ENCAVI; declared diagnosis at 15 years or older). Autism was identified from the survey "
          f"items as reported by the respondent or caregiver; no disability was inferred from a diagnosis (item "
          f"wording: appendix {T('ST5_survey_items')}). Educational recognition came from the Ministry of Education "
          f"reports on the PIE (annual stock of registered autistic students, 2019–2025), the Law 21.545 monitoring "
          f"report, and the JUNAEB Student Vulnerability Survey microdata (caregiver-reported physician diagnosis of "
          f"autism spectrum disorder in pre-school, grade 1, grade 5, and grade 9 cohorts; item from 2023, weights "
          f"from 2024; appendix {T('ST6_junaeb_items')}).")
    doc.p(f"Official sources: GRD files [@fonasa_grd], DEIS discharges [@deis_egresos], REM [@minsal_rem], INE "
          f"projections [@ine2019], FONASA beneficiaries [@fonasa_beneficiarios], ENDIDE 2022 [@endide2022], ENCAVI "
          f"2023–24 [@encavi2023], PIE registers [@mineduc_apuntes60; @mineduc_sinaces2026] and JUNAEB "
          f"[@junaeb_eve]; the sensitivity layers (INE base 2024 and Census 2024, APS enrolment, ISAPRE beneficiaries, "
          f"and REM-20 hospital activity) are cited in the appendix. Provenance was frozen before analysis: "
          f"{n0(k('prov_artefacts_n'))} source artefacts ({n1(k('prov_gb_total'))} GB) were hashed (SHA-256) and "
          f"documented (appendix {TR(['ST7_provenance', 'ST7b_manifest_checks'])}); source data were never copied "
          f"or overwritten.")
    doc.h2("Case definitions and definition variants")
    doc.p(f"In the GRD, an episode with documented F84 carries any ICD-10 code of the F84 family in any of the "
          f"{n0(k('grd_diagnosis_positions'))} diagnosis positions; principal F84 is a separate, more specific series, "
          f"and secondary-only F84 is also reported (subcodes by position: appendix {T('ST10_grd_f84_subcodes')}). "
          f"Throughout this article the case definition is the F84 family excluding Rett syndrome (F84.2), because "
          f"F84.2 is a distinct genetic disorder no longer classified with autism; the full F84 family is analysed "
          f"in parallel and compared series by series in appendix {F('figE28_variant_sensitivity')} and "
          f"{T('E28_variant_sensitivity')} (a difference of {n0(k('grd_f84_any_n_rett_only_difference_2024'))} "
          f"episodes in 2024), and F84.0 alone is a strict series that both definitions share. In REM, strict autism "
          f"is {k('strict_autism_code_a05_entry')}/{k('strict_autism_code_a05_exit')} in A05 (entries/discharges) and "
          f"{k('strict_autism_code_p6_primary')}/{k('strict_autism_code_p6_specialty')} in P6 (primary "
          f"care/specialty), all from 2021; the variant's "
          f"pervasive-developmental-disorder (PDD) family adds the other PDD categories, and the broad PDD codes of "
          f"2019–2020, from which F84.2 cannot be separated, are a labelled sensitivity only. P2 (code "
          f"{k('p2_tea_code')}), A03, A27, and A28 do not depend on the variant; A03 has four non-comparable eras. In "
          f"education, strict autism spectrum disorder (ASD), ASD-Asperger, and their harmonised "
          f"sum are separate PIE series; the JUNAEB estimand is the weighted proportion of surveyed students with a "
          f"caregiver-reported physician diagnosis of ASD, and a level or year without an item or a weight is not "
          f"estimable, never zero.")
    doc.h2("Denominators and coverage layers")
    doc.p(f"Four denominator layers answer different questions and were never interchanged (appendix "
          f"{T('T4_denominators_coverage')}): INE projections based on the 2017 Census at 30 June (resident "
          f"population; the 2024 base and the enumerated 2024 Census only as sensitivities, appendix "
          f"{F('figS10_denominators')} and {T('S10_denominator_sensitivity')}); FONASA and ISAPRE December "
          f"beneficiary stocks and validated APS enrolment (insurance and operational coverage; schemas, harmonisation "
          f"rules, exact-name comuna crosswalk, and coverage by age and sex in appendix "
          f"{TR(['ST12a_fonasa_schema', 'ST12b_isapre_rules', 'ST12c_aps_panel', 'ST4a_comuna_crosswalk_summary', 'ST4b_comuna_unmatched'])}, "
          f"{F('figS11_coverage_age_sex')}, {T('S11_coverage_age_sex')}); "
          f"and REM-20 hospital discharges and bed-days (never a covered population). The primary GRD "
          f"estimand is the rate per 100,000 GRD episodes of the same year, panel, and activity; rates per 100,000 INE "
          f"residents are a complementary reading with the numerator located by place of care and the denominator "
          f"by residence. REM counts carry their reporting establishments, rates per reporting establishment, and a "
          f"stable panel of establishments that report the code in every year of its era.")
    doc.h2("Statistical analysis")
    doc.p(f"Estimators are defined in appendix Part A (equation numbers below). Rates per 100,000 "
          f"episodes, discharges, or residents carry exact Poisson 95% limits (equation {_eq('crude')}); rates per "
          f"population were directly standardised to the WHO world standard [@ahmad2001] with Fay–Feuer gamma "
          f"intervals [@fay1997] (equations {_eqs('age_specific', 'ff')}). Annual trends were summarised with "
          f"quasi-Poisson log-linear models [@wedderburn1974] with the logarithm of the estimand's denominator as "
          f"offset (none for stocks), from which the annual percent change (APC) is 100·(exp(β) − 1) with Wald 95% CI "
          f"(equations {_eqs('qpois', 'apc')}); the Pearson dispersion is reported for every model and residual "
          f"autocorrelation was checked with the Durbin–Watson statistic (equation {_eq('dw')}), weak with three to "
          f"seven points. GRD hospital-year models added hospital fixed effects with a common trend "
          f"(clustered standard errors as sensitivity; equation {_eq('fe')}) and, separately, a Poisson "
          f"random intercept per hospital (equation {_eq('ri')}). Covariates were the mean coding depth (coded "
          f"diagnoses per episode) and an indicator of the 2020–2021 reporting disruption, which has no causal "
          f"meaning. Age-adjusted APCs came from age-group × year cells with age fixed effects and a population "
          f"offset, by sex (diagnostics: appendix {F('figE27_model_diagnostics')}, "
          f"{T('E27_model_diagnostics')}).")
    doc.p(f"Survey proportions were estimated with the published weights, strata, and primary sampling units as domain "
          f"ratio estimators with Taylor-linearised standard errors, logit 95% CIs on t, design effects, and relative "
          f"standard errors (equations {_eqs('taylor', 'deff')}); domains with fewer than 30 cases or a relative "
          f"standard error above 30% are flagged. JUNAEB proportions used the annual expansion weight without school "
          f"clustering. Convergence is described with indices (2021 = 100; equation {_eq('index_number')}) never read "
          f"as comparable levels. Comuna rates by residence were indirectly standardised, smoothed (empirical Bayes), "
          f"and described with Moran's I, local indicators, and Getis–Ord Gi* under Benjamini–Hochberg control and "
          f"with Lorenz, Gini, and Theil measures, with cells below five events suppressed (equations "
          f"{_eqs('expected', 'eb_prior')} and {_eqs('moran', 'suppression')}). Pre-specified sensitivities (appendix "
          f"{T('M6_sensitivity_grid')}) were: fixed versus observed hospital panel, strict hospitalisation versus all "
          f"activity, principal versus any position, F84.0 only, coding-depth adjustment and stratification, the "
          f"2020–2021 disruption indicator, the 2021–2024 window, hospital fixed and random effects, stable REM "
          f"panels, per-establishment offsets, June versus December stocks, and the Census 2024 and base-2024 "
          f"denominators. A missing REM row is \"not reported\", distinct from zero, and is never imputed; 2020 was "
          f"never interpolated; no causal model of Law 21.545 was fitted. Analyses used Python 3.14; the "
          f"{n0(k('models_n_variant'))} converged specifications are shared (Data sharing statement).")
    doc.h2("Reproducibility controls")
    doc.p(f"Before modelling, {n0(k('controls_families_prespecified_n'))} pre-specified control families were "
          f"reproduced from the source files, requiring exact equality for counts and 0.5% or less relative "
          f"difference for means and proportions; every difference was explained. The "
          f"{n0(k('t8_rows'))} resulting indicator-year "
          f"rows {CR.label(CR.ANALYSIS_PLAN, LANG)} are summarised by family in appendix "
          f"{TR(['T8_controls_compact', 'E79_reproduction_controls_by_family'])} and plotted in appendix "
          f"{F('figS15_controls')}; no control was completed by plausibility.")
    doc.h2("Role of the funding source")
    doc.p("There was no funding source for this study. The corresponding author had full access to all the data in the "
          "study and had final responsibility for the decision to submit for publication.")
    doc.h2("Ethics")
    doc.p("The study used only public, de-identified aggregated or pseudonymised administrative data and public survey "
          "microdata; no individual was contacted and no linkage was attempted. Under Chilean regulations such "
          "secondary analyses do not require ethics approval [to be confirmed by the author team before submission].")
    doc.h2("Use of artificial intelligence in the research process")
    doc.p("Large-language-model assistants (Claude Code, Anthropic, model Claude Fable 5.1; OpenAI Codex) were used "
          "under the author's direction to write and debug the pipeline and drafts of this text; the author "
          "specified every analysis, ran and reviewed all code, and verified every number against the output files "
          "(AI declaration).")

    # ---------------- Results ----------------
    doc.h1("Results")
    doc.h2("Sources and coverage")
    doc.p(f"{R.mfig('fig1_dataflow')} shows, for each source, what one row is, how many rows survive the autism "
          f"selection and the denominator, without person-level linkage. The GRD "
          f"files held {n0(k('grd_records_total_2019'))} episodes in 2019 and {n0(k('grd_records_total_2024'))} in "
          f"2024 from {k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitals; the fixed panel of "
          f"{n0(k('grd_fixed_panel_n'))} hospitals accounted for {n0(k('grd_records_fixed65_2024'))} of the "
          f"{n0(k('grd_records_total_2024'))} episodes of 2024 ({ppct(k('grd_records_fixed65_share_2024'))}), "
          f"{nw(k('grd_hospitals_added_2023_n'))} hospitals having joined in 2023 and "
          f"{nw(k('grd_hospitals_added_2024_only_n'))} more in 2024 (appendix {T('ST1_grd_hospital_panel')}). "
          f"Establishments reporting strict-autism A05 entries numbered "
          f"{k.series('a05_autism_entries_estab_{y}', YEARS_A05)} in 2021–2025 ("
          f"{n0(abs(k('a05_autism_entries_estab_change_2025_2024')))} fewer in 2025; file possibly incomplete) "
          f"and those reporting the P2 December stock {k.series('p2_tea_dec_estab_{y}', YEARS_REM)} in 2019–2025. "
          f"FONASA covered {pct(k('share_fonasa_ine_pct_2019'))} of residents in 2019 "
          f"({mill('fonasa_beneficiaries_2019')} of {mill('ine_pop_total_2019')} million) and "
          f"{pct(k('share_fonasa_ine_pct_2025'))} in 2025 ({mill('fonasa_beneficiaries_2025')} of "
          f"{mill('ine_pop_total_2025')} million); the enumerated 2024 Census population was "
          f"{ppct(k('ine_ratio_censo2024_base2017_2024'))} of the base-2017 projection "
          f"({n0(k('censo2024_enumerated'))} of {n0(k('ine_pop_total_2024'))}).")

    doc.h2("Hospital core: GRD episodes with documented F84")
    doc.p(f"Episodes with documented F84 in any position numbered {k.series('grd_f84_any_n_{y}', YEARS_GRD)} in "
          f"2019–2024, that is {k.rate('grd_f84_any', 2019)} per 100,000 GRD episodes in 2019 and "
          f"{k.rate('grd_f84_any', 2024)} in 2024, a ratio of {n2(k('grd_f84_any_rate_ratio_2024_2019'))} "
          f"({R.mtab('T2_grd_core')}, {R.mfig('fig2_grd_core')}; appendix {F('figS2_grd_subcodes')}, "
          f"{TR(['E60_grd_annual_full', 'T2_grd_core'])}). The count fell with hospital activity in 2020 "
          f"({n0(k('grd_f84_any_n_2020'))} episodes) while the rate did not ({n1(k('grd_f84_any_rate_2020'))}). In "
          f"the fixed panel of {n0(k('grd_fixed_panel_n'))} hospitals the 2024 count was "
          f"{n0(k('grd_f84_any_fixed65_n_2024'))} ({n1(k('grd_f84_any_fixed65_rate_2024'))} per 100,000), so added "
          f"hospitals contributed little. Principal F84 was rarer and grew more slowly: "
          f"{k.series('grd_f84_principal_n_{y}', YEARS_GRD)}, from {k.rate('grd_f84_principal', 2019)} to "
          f"{k.rate('grd_f84_principal', 2024)} per 100,000 episodes; in 2024, "
          f"{n0(k('grd_f84_secondary_only_n_2024'))} of the {n0(k('grd_f84_any_n_2024'))} episodes with F84 "
          f"({pct(k('grd_f84_secondary_only_share_2024_pct'))}) carried it only as a secondary diagnosis. The F84.0-only series reached {n0(k('grd_f840_strict_any_n_2024'))} episodes in 2024 "
          f"(appendix {F('figE28_variant_sensitivity')}, {T('E28_variant_sensitivity')}).")
    doc.p(f"The increase was not only deeper coding (mean depth by year: inset of {R.mfigp('fig2_grd_core', 'c')}; "
          f"no dispersion is computed): within each stratum of three or more diagnoses the F84 rate rose between "
          f"2019 and 2024 by a "
          f"factor of {n1(k('grd_depth_bin_3_rate_ratio_2024_2019'))} (three diagnoses), "
          f"{n1(k('grd_depth_bin_4_rate_ratio_2024_2019'))} (four), {n1(k('grd_depth_bin_5_rate_ratio_2024_2019'))} "
          f"(five), {n1(k('grd_depth_bin_6_7_rate_ratio_2024_2019'))} (six to seven), "
          f"{n1(k('grd_depth_bin_8_10_rate_ratio_2024_2019'))} (eight to ten), and "
          f"{n1(k('grd_depth_bin_11plus_rate_ratio_2024_2019'))} (11 or more), and in the strata of one and two "
          f"diagnoses from {n1(k('grd_depth_bin_1_rate_2019'))} to {n1(k('grd_depth_bin_1_rate_2024'))} and from "
          f"{n1(k('grd_depth_bin_2_rate_2019'))} to {n1(k('grd_depth_bin_2_rate_2024'))} per 100,000 "
          f"({R.mfigp('fig2_grd_core', 'c')}). Unique persons within each year numbered "
          f"{k.series('grd_f84_any_persons_{y}', YEARS_GRD)}, with {n2(k('grd_episodes_per_person_any_2024'))} "
          f"episodes per person in 2024 (appendix {F('EF6_readmission_multiplicity')}, "
          f"{T('EF6_readmission_multiplicity')}).")
    doc.p(f"In 2024 the highest rate per 100,000 episodes was in the "
          f"{str(k('grd_f84_any_peak_age_group_2024')).replace('-', '–')}-year age group, "
          f"{n0(grd_0_9)} of the {n0(grd_age_base)} episodes with F84 and a known age "
          f"({ppct(k('grd_f84_any_share_age_0_9_2024'))}) were in children aged 0–9 years and {n0(grd_20plus)} "
          f"({ppct(k('grd_f84_any_share_age_20plus_2024'))}) in people aged 20 or older; the male:female ratio of "
          f"episodes fell from {n2(k('grd_f84_any_mf_ratio_n_2019'))} in 2019 to "
          f"{n2(k('grd_f84_any_mf_ratio_n_2024'))} in 2024 (appendix {T('ST9_grd_age_sex')}). Per 100,000 INE "
          f"residents, the WHO-standardised rate of episodes with F84 rose from "
          f"{k.est_y('grd_pop_any_total_asr', 2019)} in 2019 to {k.est_y('grd_pop_any_total_asr', 2024)} in 2024, "
          f"{n1(k('grd_pop_any_male_asr_2024'))} in males and "
          f"{n1(k('grd_pop_any_female_asr_2024'))} in females (ratio {n2(k('grd_pop_any_asr_mf_ratio_2024'))}; "
          f"appendix {T('S_grd_population_rates')}; {R.mfigp('fig2_grd_core', 'd')}).")
    doc.p(f"Hospitals were heterogeneous: in 2024 the rate ranged from {n1(k('grd_hosp2024_rate_min'))} to "
          f"{n0(k('grd_hosp2024_rate_max'))} per 100,000 episodes (ratio {n1(k('grd_hosp2024_rate_ratio_max_min'))}; "
          f"median {n1(k('grd_hosp2024_rate_median'))}, IQR {n1(k('grd_hosp2024_rate_q1'))}–"
          f"{n1(k('grd_hosp2024_rate_q3'))}), highest in paediatric hospitals ({R.mfigp('fig2_grd_core', 'e')}; "
          f"appendix {FR(['figS3_grd_hospital_effects', 'EF8_hospitals'])}, "
          f"{TR(['S_hospital_rates_2024', 'EF8_hospitals'])}); {n0(k('grd_hosp_rr_fixed_effects_none_n_above1'))} "
          f"hospitals had a fixed-effect rate ratio above one and "
          f"{n0(k('grd_hosp_rr_fixed_effects_none_n_below1'))} below one, and the random-intercept SD was "
          f"{n2(k('apc_grd_hospital_ri_re_sd'))} (principal diagnoses of secondary-F84 episodes: appendix "
          f"{F('EF5_codiagnoses')}, {TR(['EF5_codiagnoses', 'E8_grd_principal_when_secondary'])}; severity and "
          f"lethality: {T('EF4_severity_weight')}). "
          f"DEIS discharges with principal F84 rose from {n0(k('deis_f84_principal_n_2019'))} "
          f"({k.rate('deis_f84_principal', 2019)} per 100,000 discharges) in 2019 to "
          f"{n0(k('deis_f84_principal_n_2024'))} ({k.rate('deis_f84_principal', 2024)}) in 2024, "
          f"{n0(k('deis_f84_principal_snss_2024'))} of them ({ppct(k('deis_f84_principal_snss_share_2024'))}) in SNSS "
          f"establishments; the ratio of DEIS to GRD "
          f"principal-F84 counts was "
          f"{n2(k('deis_vs_grd_ratio_f84_principal_2024'))} in 2024, a coverage comparison between two unlinked "
          f"registries of the same event and not a probability (appendix "
          f"{TR(['ST11a_deis_annual', 'ST11b_deis_vs_grd'])}, {FR(['figS14_deis_sex_age', 'EF10_deis_detail'])}, "
          f"{TR(['S14_deis_sex_age', 'EF10_deis_detail'])}).")

    doc.h2("Aggregate administrative pathway in primary and specialty care")
    doc.p(f"{R.mfig('fig3_rem_pathway')} presents the REM modules by era with their reporting establishments (appendix "
          f"{TR(['T3_rem_pathway', 'E69_rem_code_year_full'])}); the panels are aggregate indicators of unlinked "
          f"systems, so no ratio between them represents an individual probability. Detection and referral codes "
          f"were redefined in 2023, 2024, and 2025, so A03 and A27 are shown by era without a continuous series: the "
          f"M-CHAT-R/F classification of 2023–2024 recorded {n0(k('a03_2023_high_2023'))} and "
          f"{n0(k('a03_2023_high_2024'))} children at high risk, and assisted referrals (A27) numbered "
          f"{k.series('a27_assisted_referral_{y}', YEARS_A27)} interventions in 2023–2025 (risk and referral by era: "
          f"appendix {FR(['E12_rem_a03_risk_referral', 'E11_rem_a03_codes_by_era'])}, "
          f"{TR(['E12_rem_a03_risk_referral', 'E11_rem_a03_codes_by_era'])}).")
    doc.p(f"Strict-autism entries to mental-health programmes (A05) rose from {n0(k('a05_autism_entries_2021'))} in "
          f"2021 to {n0(k('a05_autism_entries_2025'))} in 2025 ({k.series('a05_autism_entries_{y}', YEARS_A05)}), "
          f"programme discharges from {n0(k('a05_autism_exits_2021'))} to {n0(k('a05_autism_exits_2025'))} and the "
          f"variant's PDD-family entries from {n0(k('a05_family_entries_2021'))} to "
          f"{n0(k('a05_family_entries_2025'))}. In the stable panel of {n0(k('a05_autism_entries_stable_panel_n'))} "
          f"establishments, entries rose from "
          f"{n0(k('a05_autism_entries_stable_total_2021'))} to {n0(k('a05_autism_entries_stable_total_2025'))} "
          f"(appendix {FR(['figS6_rem_stable_panel', 'E17_rem_establishment_distribution'])}, "
          f"{TR(['S6_stable_panel', 'E17_rem_establishment_distribution'])}). Per 100,000 residents, the "
          f"WHO-standardised rate of entries rose from {k.est_y('a05_autism_pop_total_asr', 2021)} in 2021 to "
          f"{k.est_y('a05_autism_pop_total_asr', 2025)} in 2025 (appendix {F('figS7_rem_education_models')}, "
          f"{T('S_a05_standardised_rates')}), with a male:female ratio "
          f"of standardised rates of {n2(k('a05_autism_pop_asr_mf_ratio_2025'))} in 2025 and "
          f"{n0(a05_0_9)} of the {n0(k('a05_autism_entries_2025'))} entries "
          f"({ppct(k('a05_autism_entries_share_age_0_9_2025'))}) in children aged 0–9 years (appendix "
          f"{F('figS8_a05_age_sex')}, {TR(['ST13_a05_age_sex', 'E14_rem_a05_age_sex'])}; definitions compared in appendix "
          f"{F('E19_rem_definition_era_sensitivity')}, {T('E19_rem_definition_era_sensitivity')}).")
    doc.p(f"The December stock of children with autism under control in the NANEAS programme (P2) rose from "
          f"{n0(k('p2_tea_dec_2019'))} in 2019 to {n0(k('p2_tea_dec_2025'))} in 2025 "
          f"({k.series('p2_tea_dec_{y}', YEARS_REM)}; ratio {n1(k('p2_tea_dec_ratio_2025_2019'))}), while reporting "
          f"establishments rose from {n0(k('p2_tea_dec_estab_2019'))} to {n0(k('p2_tea_dec_estab_2025'))}; autism "
          f"accounted for {pct(k('p2_tea_share_of_naneas_dec_pct_2023'))} of the total NANEAS stock in 2023 "
          f"({n0(k('p2_tea_dec_2023'))} of {n0(k('p2_naneas_dec_2023'))}) and "
          f"{pct(k('p2_tea_share_of_naneas_dec_pct_2025'))} in 2025 ({n0(k('p2_tea_dec_2025'))} of "
          f"{n0(k('p2_naneas_dec_2025'))}; appendix {F('E15_rem_p2_p6_detail')}, "
          f"{T('E15_rem_p2_p6_detail')}). The June 2020 cut fell to {ppct(k('p2_jun_dec_ratio_2020'))} of the "
          f"December stock ({n0(k('p2_tea_jun_2020'))} against {n0(k('p2_tea_dec_2020'))}) as few establishments "
          f"reported: monthly series show that the April–September 2020 fall was in reporting establishments, not "
          f"in persons (appendix {FR(['figS5_rem_june_december', 'figS13_rem_seasonality'])}, "
          f"{TR(['ST14_p2_p6_june_december', 'S13_rem_seasonality'])}; GRD monthly index: "
          f"{T('E1_grd_seasonality')}). In P6, the December stock under control for "
          f"strict autism rose from {n0(k('p6_primary_autism_dec_2021'))} to {n0(k('p6_primary_autism_dec_2025'))} "
          f"in primary care and from {n0(k('p6_specialty_autism_dec_2021'))} to "
          f"{n0(k('p6_specialty_autism_dec_2025'))} in specialty care (2021–2025). Entries to rehabilitation for autism "
          f"(A28), reported from 2023, numbered {k.series('a28_primary_{y}', YEARS_A27)} at primary level and "
          f"{k.series('a28_hospital_{y}', YEARS_A27)} at hospital level (REM-20 capacity, never a denominator: "
          f"appendix {F('figE22_rem20_capacity')}, {T('E22_rem20_capacity')}).")

    doc.h2("Population benchmarks")
    doc.p(f"ENDIDE 2022 estimated reported autism in {k.svy('svy_endide_adults_reported_total')} "
          f"of adults aged 18 years or older ({n0(k('svy_endide_adults_reported_total_cases'))} cases) and in "
          f"{k.svy('svy_endide_children_reported_total')} of children aged 2–17 years "
          f"({n0(k('svy_endide_children_reported_total_cases'))} cases), of whom "
          f"{k.svy('svy_endide_children_confirmed_among_reported_total', 1)} had a physician-confirmed diagnosis "
          f"({n0(k('svy_endide_children_confirmed_among_reported_total_cases'))} of "
          f"{n0(k('svy_endide_children_confirmed_among_reported_total_n'))}; "
          f"{k.svy('svy_endide_children_reported_confirmed_total')} of all children); reported autism was "
          f"{pct(k('svy_endide_children_reported_male_pct'), 2)} in boys ({n0(k('svy_endide_children_reported_male_cases'))} "
          f"cases among {n0(k('svy_endide_children_reported_male_n'))} surveyed) and "
          f"{pct(k('svy_endide_children_reported_female_pct'), 2)} in girls "
          f"({n0(k('svy_endide_children_reported_female_cases'))} of {n0(k('svy_endide_children_reported_female_n'))}). "
          f"ENCAVI 2023–24 estimated a declared "
          f"diagnosis of autism spectrum disorder in {k.svy('svy_encavi_15plus_diagnosed_total')} at 15 years or older "
          f"({n0(k('svy_encavi_15plus_diagnosed_total_cases'))} cases; design effect "
          f"{n2(k('svy_encavi_15plus_diagnosed_total_deff'))}). Most sex and age domains are imprecise "
          f"({R.mfigp('fig4_triangulation', 'c')}; appendix "
          f"{T('T5_survey_benchmarks')}, {F('figE23_surveys_detail')}, {T('E23_surveys_detail')}); these benchmarks "
          f"are self- or caregiver-reported, not a validation of codes.")

    doc.h2("Educational triangulation")
    doc.p(f"Autistic students registered in the PIE rose from {n0(k('pie_tea_strict_2019'))} (strict ASD) and "
          f"{n0(k('pie_tea_asperger_2019'))} (ASD-Asperger) in 2019 to {n0(k('pie_tea_strict_2023'))} and "
          f"{n0(k('pie_tea_asperger_2023'))} in 2023, when strict ASD represented "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2023'))} of all PIE students ({n0(k('pie_tea_strict_2023'))} of "
          f"{n0(k('pie_total_enrolment_2023'))}) against {pct(k('pie_tea_strict_share_of_pie_pct_2019'))} in 2019 "
          f"({n0(k('pie_tea_strict_2019'))} of {n0(k('pie_total_enrolment_2019'))}); the harmonised ASD + Asperger "
          f"series was "
          f"{k.series('pie_harmonised_{y}', YEARS_REM)} in 2019–2025 (ratio {n2(k('pie_harmonised_ratio_2025_2019'))}), "
          f"with 2024–2025 from the Law 21.545 monitoring report ({R.mfigp('fig4_triangulation', 'a')}; appendix "
          f"{T('T6_education')}). For 2022 that report prints {n0(k('pie_2022_sinaces_printed'))} whereas its own total "
          f"minus special schools gives {n0(k('pie_2022_sinaces_total_minus_special'))}, the ministerial figure; the "
          f"difference of {nw(k('pie_2022_discrepancy_cases'))} students was resolved in favour of the disaggregated "
          f"source. Including special schools, registered autistic students numbered "
          f"{n0(k('sinaces_total_autistic_students_2022'))} in 2022 and "
          f"{n0(k('sinaces_total_autistic_students_2025'))} in 2025 (appendix {F('figE24_education_detail')}, "
          f"{T('E24_education_detail')}).")
    doc.p(f"In JUNAEB's whole-cohort caregiver survey, the weighted share of students with a reported physician "
          f"diagnosis of ASD was {pct(k('junaeb_parvularia_all_pct_weighted_2024'), 2)} in pre-school "
          f"({jn('parvularia', 2024)} unweighted cases/respondents), "
          f"{pct(k('junaeb_basico1_all_pct_weighted_2024'), 2)} in grade 1 ({jn('basico1', 2024)}), and "
          f"{pct(k('junaeb_basico5_all_pct_weighted_2024'), 2)} in grade 5 ({jn('basico5', 2024)}) in 2024 (grade 9 "
          f"not estimable: empty item), and {pct(k('junaeb_parvularia_all_pct_weighted_2025'), 2)} "
          f"({jn('parvularia', 2025)}), {pct(k('junaeb_basico1_all_pct_weighted_2025'), 2)} ({jn('basico1', 2025)}), "
          f"{pct(k('junaeb_basico5_all_pct_weighted_2025'), 2)} ({jn('basico5', 2025)}), and "
          f"{pct(k('junaeb_medio1_all_pct_weighted_2025'), 2)} ({jn('medio1', 2025)}) in 2025, with male:female "
          f"ratios between "
          f"{n1(k('junaeb_medio1_mf_ratio_2025'))} (grade 9) and {n1(k('junaeb_basico1_mf_ratio_2025'))} (grade 1) "
          f"({R.mfigp('fig4_triangulation', 'b')}; appendix {F('figS12_junaeb_sex_level')}, "
          f"{T('S12_junaeb_sex_level')}); no trend before 2024 can be estimated, and these are caregiver reports in "
          f"selected cohorts, not national prevalence.")

    doc.h2("Territory")
    t = territory_numbers()
    doc.p(f"Comuna-level rates of GRD episodes by residence (empirical-Bayes smoothed standardised ratios) were "
          f"spatially clustered: global Moran's I was {n2(t['moran']['queen'])} (queen contiguity; p = "
          f"{JC.format_p(t['moran_p'], LANG)} with {n0(t['moran_perm'])} permutations; "
          f"{n2(min(t['moran'].values()))}–{n2(max(t['moran'].values()))} across four weight matrices). After "
          f"Benjamini–Hochberg control, {nw(t['hh'])} comunas were high–high, {nw(t['ll'])} low–low, and "
          f"{nw(t['lh'])} low–high, and Gi* identified {nw(t['hot'])} hot and {nw(t['cold'])} cold spots among "
          f"{n0(t['n_lisa'])} continental comunas. Inequality fell as recognition spread: the Gini "
          f"coefficient across comunas was {n2(t['gini'][2019])} in 2019 and {n2(t['gini'][2024])} in 2024, comunas "
          f"with at least one episode rose from {n0(t['with_events'][2019])} to {n0(t['with_events'][2024])} of "
          f"{n0(t['n_comunas'])}, and the top decile's share of episodes fell from "
          f"{ppct(t['top_decile'][2019])} (of {n0(t['total_count'][2019])} with a comuna of residence) to "
          f"{ppct(t['top_decile'][2024])} (of {n0(t['total_count'][2024])}). Comuna ranks of GRD episodes (residence) and A05 entries (place of care) "
          f"were weakly correlated (Spearman ρ {n2(t['rho'])}, 95% CI {cir(t['rho_lo'], t['rho_hi'], 2)}), a "
          f"territorial comparison of two unlinked systems with different geographies, not a linkage (appendix "
          f"{FR(['figS9_regional_maps', 'E40_maps_grd_smoothed_ratio', 'E42_lisa_gistar_maps', 'E47_lorenz_theil', 'E49_regional_summary', 'E46_sae_deprivation'])}, "
          f"{TR(['S9_regional_rates', 'E62_grd_region_population_rates', 'E13_rem_a05_regional', 'E40_grd_smoothed_ratio_comuna', 'E42_local_class_counts', 'E51_lisa_significant_comunas', 'E43_moran_sensitivity_main', 'E50_moran_gistar_all', 'E47_inequality_gini_theil', 'E49_regional_summary', 'E44_correlation_matrix_comuna', 'E45_bivariate_moran_pairs', 'E48_rank_stability', 'E46_sae_association', 'E41_rem_comuna_place_of_care'])}). "
          f"Region × year series (residence for GRD, reporting establishment for A05) are never divided one by the "
          f"other, and the bivariate Moran's I of each pair of indicators is a spatial co-location of unlinked "
          f"systems, not a direction or a linkage.")

    doc.h2("Convergence across systems and sensitivity of the trends")
    doc.p(f"Indexed to 2021 = 100, the GRD rate of episodes with F84 stood at {n0(k('conv_grd_any_rate_index2021_2024'))} "
          f"in 2024, the DEIS principal-F84 rate at {n0(k('conv_deis_principal_rate_index2021_2024'))}, strict-autism "
          f"A05 entries at {n0(k('conv_a05_strict_entries_index2021_2025'))} in 2025, the P2 December stock at "
          f"{n0(k('conv_p2_december_stock_index2021_2025'))}, the P6 primary-care stock at "
          f"{n0(k('conv_p6_primary_strict_stock_index2021_2025'))}, and the harmonised PIE at "
          f"{n0(k('conv_pie_harmonised_index2021_2025'))} ({R.mfigp('fig4_triangulation', 'd-e')}; appendix "
          f"{TR(['S_convergence_index', 'F4_triangulation_series'])}, {F('figE26_cross_source')}, "
          f"{T('E26_cross_source')}); the indices share direction and timing (steepest in 2022–2024) but not units, "
          f"denominators, or definitions.")
    doc.p(f"{R.mtab('T7_models')} gives the pre-specified models. The APC of GRD episodes with F84 per 100,000 "
          f"episodes was {k.apc('apc_grd_any_obs')} in the observed panel and {k.apc('apc_grd_any_fixed65')} in the "
          f"fixed panel; adjustment for "
          f"mean coding depth raised it to {k.apc('apc_grd_any_obs_depth')}, the 2020–2021 disruption indicator "
          f"lowered it to {k.apc('apc_grd_any_obs_disruption')}, the 2021–2024 window gave "
          f"{k.apc('apc_grd_any_obs_2021_2024')} and strict hospitalisation {k.apc('apc_grd_any_hosp')} "
          f"({n1(k('apc_grd_any_sensitivity_min'))}–{n1(k('apc_grd_any_sensitivity_max'))}% across the "
          f"{n0(k('apc_grd_any_sensitivity_n_specs'))} specifications). Principal F84 grew at "
          f"{k.apc('apc_grd_principal_obs')} ({n1(k('apc_grd_principal_sensitivity_min'))}–"
          f"{n1(k('apc_grd_principal_sensitivity_max'))}% across specifications). Hospital fixed-effects models gave "
          f"{n1(k('apc_grd_hospital_fe'))}% (hospital-clustered 95% CI "
          f"{cir(k('apc_grd_hospital_fe_cluster_lo'), k('apc_grd_hospital_fe_cluster_hi'))}) and the random-intercept "
          f"model {n1(k('apc_grd_hospital_ri'))}%; each additional coded diagnosis carried a rate ratio "
          f"of {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} within hospitals. Per 100,000 residents "
          f"the age-adjusted APC was {k.apc('apc_grd_pop_any_total_ageadj')}, higher in females "
          f"({n1(k('apc_grd_pop_any_female_ageadj'))}%) than in males ({n1(k('apc_grd_pop_any_male_ageadj'))}%). DEIS "
          f"principal-F84 discharges grew at {k.apc('apc_deis_principal')} ({R.mfigp('fig4_triangulation', 'f')}; "
          f"every specification with its fit in appendix {F('figS4_models_cpa')} and "
          f"{TR(['T7_models', 'T7_models_cpa_full'])}).")
    doc.p(f"Strict-autism A05 entries grew at {k.apc('apc_a05_autism_pop')} per 100,000 residents, "
          f"{k.apc('apc_a05_autism_estab')} per reporting establishment, {k.apc('apc_a05_autism_stable_pop')} in the "
          f"stable panel and {k.apc('apc_a05_autism_ageadj_total')} after age adjustment "
          f"({n1(k('apc_a05_autism_ageadj_female'))}% in females, {n1(k('apc_a05_autism_ageadj_male'))}% in males); "
          f"the P2 December stock at {k.apc('apc_p2_dec')} as a count, {k.apc('apc_p2_dec_estab')} per reporting "
          f"establishment, {k.apc('apc_p2_dec_stable')} in the stable panel of {n0(k('p2_tea_dec_stable_panel_n'))} "
          f"establishments and {k.apc('apc_p2_dec_naneas_offset')} per 100 NANEAS under control (2023–2025); the P6 "
          f"primary-care stock at {k.apc('apc_p6_primary_autism')} ({n1(k('apc_p6_primary_autism_estab'))}% per "
          f"establishment) and the harmonised PIE at {k.apc('apc_pie_harmonised')}. Dispersion was large in the flow "
          f"and stock models, and no specification estimates an effect of Law 21.545.")
    doc.p(f"The {n0(k('t8_rows'))} reproduction controls {CR.label(CR.ANALYSIS_PLAN, LANG)} ({n0(k('t8_ok'))} matched, "
          f"{n0(k('t8_differs'))} differed, all documented) are listed by family in appendix "
          f"{TR(['T8_controls_compact', 'E79_reproduction_controls_by_family'])}.")

    # ---------------- Discussion ----------------
    junaeb_levels = ("parvularia", "basico1", "basico5", "medio1")
    junaeb_2025 = [k(f"junaeb_{lvl}_all_pct_weighted_2025") for lvl in junaeb_levels]
    junaeb_min, junaeb_max = min(junaeb_2025), max(junaeb_2025)
    junaeb_mf = [k(f"junaeb_{lvl}_mf_ratio_2025") for lvl in junaeb_levels]
    junaeb_mf_min, junaeb_mf_max = min(junaeb_mf), max(junaeb_mf)
    endide_mf = k('svy_endide_children_reported_male_pct') / k('svy_endide_children_reported_female_pct')
    doc.h1("Discussion")
    doc.p(f"Across Chile's public hospital, primary-care, specialty, and education systems, administrative recognition of "
          f"autism expanded several-fold between 2019 and 2025: {n1(k('grd_f84_any_rate_ratio_2024_2019'))}-fold in the "
          f"rate of GRD episodes with documented F84, {n1(k('a05_autism_entries_ratio_2025_2021'))}-fold in strict-autism "
          f"programme entries in four years, {n1(k('p2_tea_dec_ratio_2025_2019'))}-fold in the December stock of children "
          f"with autism under control and {n1(k('pie_harmonised_ratio_2025_2019'))}-fold in registered autistic students; "
          f"hospital counts fell with activity in 2020 while the stocks did not, and the steepest increases came in "
          f"2022–2024. The increases survive every pre-specified sensitivity, although their magnitude changes: the GRD "
          f"APC spans {n1(k('apc_grd_any_sensitivity_min'))}–{n1(k('apc_grd_any_sensitivity_max'))}% across "
          f"specifications, A05 entries grow at {n1(k('apc_a05_autism_estab'))}% per reporting establishment against "
          f"{n1(k('apc_a05_autism_pop'))}% per resident, and the P2 stock at {n1(k('apc_p2_dec_estab'))}% per "
          f"establishment against {n1(k('apc_p2_dec'))}% as a count, a gap that bounds the contribution of reporting "
          f"expansion.")
    doc.p(f"Three constructs must be separated: administrative recognition is the recording of a code; registered demand "
          f"is the volume of contacts that carry it; underlying epidemiology is the occurrence of autism in the "
          f"population; our data measure the first two. In the GRD, {pct(k('grd_f84_secondary_only_share_2024_pct'))} of "
          f"episodes with F84 in 2024 carried it as a secondary diagnosis and principal F84 grew at "
          f"{n1(k('apc_grd_principal_obs'))}% against {n1(k('apc_grd_any_obs'))}% for any position, so most of the "
          f"hospital signal is the documentation of autism in episodes admitted for other reasons, and coding depth "
          f"changes what administrative data capture [@iezzoni1992]. Yet the rate rose "
          f"within every coding-depth stratum of three or more diagnoses and each additional diagnosis explained only a "
          f"rate ratio of {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} within hospitals, so deeper "
          f"coding accounts for part of the change and not for the whole of it. In the REM, the gap between growth per "
          f"establishment and growth per resident bounds the contribution of reporting expansion, and stocks under "
          f"control accumulate people by construction. Coding and reporting practices are themselves determinants of "
          f"recorded rates [@song2010]; the "
          f"{n0(k('grd_hosp2024_rate_ratio_max_min'))}-fold range across hospitals in 2024 reflects paediatric case-mix "
          f"as much as practice.")
    doc.p(f"The convergence across independent systems is informative although they measure different things: they "
          f"share timing and direction, a concentration in early childhood "
          f"({ppct(k('grd_f84_any_share_age_0_9_2024'))} of GRD episodes and "
          f"{ppct(k('a05_autism_entries_share_age_0_9_2025'))} of A05 entries in children aged 0–9 years) and a falling "
          f"male:female ratio (from {n1(k('grd_f84_any_mf_ratio_n_2019'))} to {n1(k('grd_f84_any_mf_ratio_n_2024'))} in "
          f"GRD episodes; {n1(k('a05_autism_pop_asr_mf_ratio_2025'))} in standardised A05 entries; "
          f"{n1(junaeb_mf_min)}–{n1(junaeb_mf_max)} in JUNAEB cohorts), with faster growth in females in the "
          f"age-adjusted models (appendix {F('figE26b_sex_ratio_multisource')}, {T('E26b_sex_ratio_multisource')}). A "
          f"ratio approaching 2:1 is below the 3:1 of active ascertainment and "
          f"the 4:1 of passive samples [@loomes2017], and a falling ratio has been documented in a population-based "
          f"birth cohort [@fyfe2026]; it is consistent with expanding recognition of autism in girls "
          f"and women, although unlinked records cannot show whether it reflects earlier under-recognition or a changing "
          f"population; the ENDIDE benchmark in Chilean children ({n1(endide_mf)}:1) is nearer the "
          f"passive-ascertainment values than the administrative flows of 2024–2025.")
    doc.p(f"Registers elsewhere showed the same pattern earlier. In UK primary care, recorded autism "
          f"diagnoses rose 787% between 1998 and 2018 [@russell2022]; in Denmark, 60% of the increase in prevalence was "
          f"attributable to changes in diagnostic criteria and to the inclusion of outpatient contacts [@hansen2015]; in "
          f"Sweden, registered diagnoses rose steeply over ten years while the population phenotype remained stable "
          f"[@lundstrom2015]; and in the USA, the multisource surveillance of eight-year-olds reached one in 31 children "
          f"in 2022 [@shaw2025]. The Chilean "
          f"annual changes of {n0(k('apc_grd_any_sensitivity_min'))}–{n0(k('apc_grd_any_sensitivity_max'))}% in "
          f"hospital episodes and {n0(k('apc_a05_autism_estab'))}–{n0(k('apc_a05_autism_pop'))}% in programme entries "
          f"are far above the long-run rates of those countries; the survey benchmarks of {pct(k('svy_endide_children_reported_confirmed_total_pct'), 1)}–"
          f"{pct(k('svy_endide_children_reported_total_pct'), 1)} in children are of the order of the identified "
          f"prevalence in high-income countries, whereas the administrative flows and stocks, which are not prevalence, "
          f"remain far below the number of people those benchmarks imply.")
    doc.p(f"In Latin America, a six-country study that included Chile documented late diagnosis and the role of public "
          f"coverage [@montielnava2024]. The public network we observed serves the residents insured by FONASA "
          f"({pct(k('share_fonasa_ine_pct_2025'), 0)} of the population in 2025); privately purchased care, ISAPRE "
          f"networks, and the armed forces are invisible to GRD and REM, and Chilean caregivers report that access to "
          f"diagnosis and services differs by insurance and by region [@garcia2022]. Recognition therefore depends on "
          f"supply, and the geography of place of care differs from that of residence.")
    doc.p(f"The implications are practical. Every stage of the public pathway is under pressure: strict-autism programme "
          f"entries reached {n0(k('a05_autism_entries_2025'))} in 2025, primary-care stocks under control multiplied by "
          f"{n1(k('p6_primary_autism_dec_ratio_2025_2021'))} in four years, entries to primary-level rehabilitation rose "
          f"{n1(k('a28_primary_ratio_2025_2023'))}-fold in two years, and autistic students represent "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2023'))} of PIE registrations (2023) and {pct(junaeb_min)}–"
          f"{pct(junaeb_max)} of the school cohorts surveyed in 2025. Diagnostic, follow-up, rehabilitation, and school "
          f"services must be planned for a demand that is still rising, and the "
          f"monitoring required by Law 21.545 should report the number of reporting establishments, the definition era, "
          f"and the coding rule next to every count and move towards person-level linkage with proper safeguards, so "
          f"that recognition can be distinguished from re-contacts and from accumulation of stocks.")
    doc.p(f"Its strengths (national coverage of every public source, frozen provenance, pre-specified controls, and "
          f"sensitivities) do not remove its limitations. The COVID-19 pandemic depressed activity and reporting in "
          f"2020–2021 and its recovery overlaps with every later change; the disruption indicator describes rather "
          f"than corrects it. Taxonomic breaks (PDD categories in 2021, four A03 eras, and the JUNAEB item from 2023) "
          f"truncate series, and the REM 2025 file may be incomplete "
          f"({n0(k('a05_autism_entries_estab_2025'))} establishments against {n0(k('a05_autism_entries_estab_2024'))} "
          f"in 2024). Panels changed, and stable panels are conservative sensitivities rather than representative "
          f"series. Numerators are located by place of care and "
          f"denominators by residence, so population rates are complementary readings and regional and comuna "
          f"comparisons are ecological (residence for GRD, place of care for REM). Sex is the sex recorded "
          f"administratively or declared to the survey, not sex assigned at birth or gender identity, so the falling "
          f"male:female ratio describes recording and no result by gender can be given. Sources are not linked by person, so "
          f"no trajectory, cascade, or conversion ratio can be estimated and persons are unique only within a year. No "
          f"code was validated clinically; the surveys, with few cases and different wording, are benchmarks, not "
          f"validation. The series are short (three to seven points), so trend models are descriptive and the "
          f"dispersion is large.")
    doc.p("We cannot separate a genuine change in the occurrence of autism from awareness, care-seeking, service "
          "supply, coverage, coding depth, and definitions. The observed convergence establishes that recognition and "
          "registered demand rose in every system; it does not establish that autism became more frequent, and the "
          "coincidence of Law 21.545 with the other changes precludes any attribution to the law.")
    doc.h1("Conclusion")
    doc.p("Between 2019 and 2025, Chile's public health and education systems recorded a several-fold expansion of "
          "administrative recognition of autism that converges in timing and direction across unlinked hospital, "
          "primary-care, specialty, rehabilitation, and school registers, and that is partly, but not wholly, explained by "
          "reporting expansion, coding depth, and definition changes. For Chile and for other segmented Latin American "
          "systems, these counts are a measure of demand that services and surveillance must plan for, not a measure of "
          "prevalence.")

    # ---------------- Declarations ----------------
    doc.h1("Contributors")
    doc.p(f"{AUTHOR} conceived the study, wrote the analysis plan, obtained and curated the data, wrote the analysis "
          f"pipeline, verified the reproduction controls, produced the figures and tables, interpreted the results, and "
          f"wrote the manuscript. [Second author, to be named before submission] independently accessed the source "
          f"files listed in appendix {T('ST7_provenance')}, re-ran the pipeline, and verified the values reported in "
          f"the text, in {R.mtab('T2_grd_core')} and {R.mtab('T7_models')} and in the appendix. {AUTHOR} and [second "
          f"author] directly accessed and verified the underlying data reported in the manuscript. All authors had "
          f"full access to all the data and accept responsibility for the decision to submit for publication.")
    doc.h1("Declaration of interests")
    doc.p("The authors declare no competing interests. [Each author will complete the ICMJE disclosure form at "
          "submission.]")
    doc.h1("Data sharing statement")
    doc.p(f"All source data are public and are listed, with providers, files, versions, and SHA-256 hashes, in appendix "
          f"{T('T1_sources')} and {T('ST7_provenance')}. The derived tidy tables (data dictionary: appendix "
          f"{T('E80_tidy_data_dictionary')}; {n0(k('n_tables_supp_files_en'))} supplementary and "
          f"{n0(k('n_tables_main_en'))} main table files per variant and language), the complete extended material of the "
          f"full bilingual corpus ({n0(len(PE.MAIN_FIGURES) + len(SM.FIGURE_ORDER))} figures and "
          f"{n0(len(PE.MAIN_TABLES) + len(SM.TABLE_ORDER))} tables, of which this article and its appendix print "
          f"{n0(len(JC.BODY_FIGURES) + len(JC.SUPP_FIGURES))} and "
          f"{n0(len(set(JC.BODY_TABLES) | set(JC.SUPP_TABLES) - JC.SYNTHETIC_TABLES))}; the rest are named in appendix "
          f"Part B), the flat table of every quantity cited in the text, the model outputs, the analysis plan, the decision log, the reporting checklist, and the "
          f"complete Python pipeline that reproduces every figure and table from the source files will be deposited in "
          f"a public repository with a persistent identifier [URL and DOI to be inserted at acceptance] and are "
          f"available from the corresponding author now; access is open under a permissive licence, without "
          f"restriction and without application, from the date of publication. No person-level data are "
          f"redistributed: the GRD, REM, DEIS, survey, and JUNAEB microdata must be obtained from the official portals "
          f"cited.")
    doc.h1("Funding")
    doc.p("None.")
    doc.h1("Acknowledgements")
    doc.p("We thank the Department of Health Statistics and Information (DEIS) of the Ministry of Health, FONASA, the "
          "Superintendencia de Salud, the National Statistics Institute, the Ministry of Education, JUNAEB, and the Ministry "
          "of Social Development and Family for publishing the data used in this study.")
    doc.h1("Declaration of the use of artificial intelligence")
    doc.p("In accordance with the journal's policy, the author declares that large-language-model assistants were used in "
          "this work: Claude Code (Anthropic; model Claude Fable 5.1, claude-fable-5-1) and OpenAI Codex (Visual Studio Code "
          "extension; [version to be confirmed by the author]). Purpose and scope: writing and debugging the Python "
          "analysis pipeline, the figure and table scripts, and the document builder; drafting and editing this "
          "manuscript, its summary, the Research in context panel, and the supplementary appendix from the computed "
          "outputs; and verifying bibliographic metadata against PubMed, Crossref, and official pages. Supervision: the "
          "author specified every analysis and rule, reviewed and executed all code, verified every reported number "
          "against the output files and the reproduction controls, checked every reference against its source, and edited "
          "the final text; the tools did not generate or alter data, images, or references, and they are not authors. "
          "Prompts are available on request.")
    doc.add("refs", None)

    # ---------------- Display items: tables, then figures one per page ----------------
    for key in JC.BODY_TABLES:
        kind, payload = R.table_block(key, f"Table {JC.BODY_TABLES.index(key) + 1}", note=body_note(R, key))
        doc.add(kind, payload)
    for key in JC.BODY_FIGURES:
        heading = R.title_text(key)
        kind, payload = R.figure_block(key, f"Figure {JC.BODY_FIGURES.index(key) + 1}", body=True,
                                       caption=body_legend(R, key))
        payload["heading"] = heading
        doc.add(kind, payload)

    blocks = doc.blocks
    R.article_citations = len(R.main_citations)
    R.assert_monotone(complete=True)

    # Title-page counts (computed, never typed): manuscript text, Summary, references, display items.
    wc = PE.word_counts(blocks)
    n_refs = len(PE.citation_keys(blocks))
    counts = (f"Manuscript text {n0(wc['core_body'])} words; Summary {n0(wc['summary'])} words; "
              f"{n0(n_refs)} references; {nw(len(JC.BODY_TABLES))} tables; {nw(len(JC.BODY_FIGURES))} figures; "
              f"appendix with {n0(len(JC.SUPP_FIGURES))} figures and {n0(len(JC.SUPP_TABLES))} tables.")
    for kind, payload in blocks:
        if kind == "authors":
            payload["lines"] = [counts if line == "__COUNTS__" else line for line in payload["lines"]]
    return blocks


if __name__ == "__main__":
    import json

    V = PE.load_values(VARIANT)
    blocks = article(V)
    print(json.dumps(dict(word_counts=PE.word_counts(blocks), sections=JC.budget_report(blocks, LANG),
                          legends=legend_word_counts(blocks), citations=PE.citation_keys(blocks)),
                     indent=1, ensure_ascii=False))
