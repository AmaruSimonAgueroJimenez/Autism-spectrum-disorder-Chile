# -*- coding: utf-8 -*-
"""journal_config.py — shared configuration of the journal submission (sin_rett, the target journal).

This module is the contract of section 7.1 of journal/plan.md. It is imported by prose_journal_en.py,
prose_journal_es.py, supplement_journal.py and build_journal.py, and it REUSES the corpus (prose_en, config,
supplementary_material) without modifying it. Nothing here writes a file.

Exports
-------
VARIANT, LANGS, SUBMISSION_LANG, OUT_DIR, PLATE_DIR
BODY_FIGURES, BODY_TABLES, TABLE_ROWS, TABLE_COLUMNS
SUPP_FIGURES (36), SUPP_TABLES (85), SUPP_PART_A
REFERENCE_KEYS (30, order of first citation), DROPPED_REFERENCE_KEYS
WORD_BUDGET, PROTECTED_TOKENS
journal_text(s, lang)            number pass for the English submission (identity for other languages)
journal_text_blocks(blocks, lang) number pass on every string of every block (after word counting)
format_p(p)                      "<0·0001" or two significant figures with the mid-height point
tidy_value(file, filters, column) one float from outputs/tidy/<file>; exactly one row must match
tidy_count(file, filters)        number of rows of outputs/tidy/<file> matching the filters
asset_path(key, kind, lang, body=False)
remap_refs(text, lang)           corpus "Figure Sn"/"Table Sn"/"Figure n"/"Table n" tokens -> journal numbering
section_word_counts(blocks, lang) words per h1 section of the article (before the number pass)
class JournalRegistry            same surface as prose_en._Registry, numbered by the journal lists above
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import config as CFG  # noqa: E402
import prose_en as PE  # noqa: E402
import supplementary_material as SM  # noqa: E402

# ---------------------------------------------------------------------------
# Identity of the submission
# ---------------------------------------------------------------------------
VARIANT = "sin_rett"
LANGS = ("en", "es")
SUBMISSION_LANG = "en"
OUT_DIR = CFG.SUBMISSION           # manuscript/04_submission_study
PLATE_DIR = {lang: CFG.OUT / VARIANT / lang / "journal" / "figures" for lang in LANGS}

# ---------------------------------------------------------------------------
# Body display items (plan section 2)
# ---------------------------------------------------------------------------
BODY_FIGURES = ["fig1_dataflow", "fig2_grd_core", "fig3_rem_pathway", "fig4_triangulation"]
BODY_TABLES = ["T2_grd_core", "T7_models"]

#: Table 1: (Block, Indicator) pairs of T2_grd_core.csv, in file order (25 of 45 rows).
TABLE_ROWS = {
    "T2_grd_core": [
        ("Panel and episodes", "Hospitals observed (n)"),
        ("Panel and episodes", "Fixed-panel hospitals (n)"),
        ("Panel and episodes", "GRD episodes, observed panel, all activity (n)"),
        ("Panel and episodes", "GRD episodes, fixed panel of 65, all activity (n)"),
        ("Panel and episodes", "GRD episodes, strict hospitalisation (n)"),
        ("Episodes with documented F84", "F84 in any position, observed panel (n)"),
        ("Episodes with documented F84", "F84 in any position, observed panel, per 100,000 episodes (95% CI)"),
        ("Episodes with documented F84", "F84 in any position, fixed panel of 65 (n)"),
        ("Episodes with documented F84", "F84 in any position, fixed panel of 65, per 100,000 episodes (95% CI)"),
        ("Episodes with documented F84", "F84 principal, observed panel (n)"),
        ("Episodes with documented F84", "F84 principal, observed panel, per 100,000 episodes (95% CI)"),
        ("Episodes with documented F84", "F84 as secondary diagnosis only, n (% of episodes with F84)"),
        ("Activity type (observed panel)", "Strict hospitalisation: F84 any position (n)"),
        ("Activity type (observed panel)", "Strict hospitalisation: F84 any position, per 100,000 episodes (95% CI)"),
        ("Activity type (observed panel)", "Major ambulatory surgery: F84 any position (n)"),
        ("Activity type (observed panel)", "Major ambulatory surgery: F84 any position, per 100,000 episodes (95% CI)"),
        ("Unique persons (within each year only)", "Persons with F84 any position (n, within year)"),
        ("Unique persons (within each year only)", "F84 episodes per person (ratio)"),
        ("Per 100,000 population (INE base 2017, residence)", "Crude rate, both sexes, F84 any position (95% CI)"),
        ("Per 100,000 population (INE base 2017, residence)", "WHO age-standardised rate, both sexes, F84 any position (95% CI)"),
        ("Per 100,000 population (INE base 2017, residence)", "Crude rate, males, F84 any position (95% CI)"),
        ("Per 100,000 population (INE base 2017, residence)", "Crude rate, females, F84 any position (95% CI)"),
        # The «Definition sensitivity» block (alternative full-family variant, F84.0 only, and the difference
        # between variants) was removed from the body: this submission carries one case definition, stated once
        # in Methods. The comparison itself is not lost — it is Figure S2 and Table S24 of the appendix, which
        # the Methods sentence cites.
    ],
    #: Table 2: model_id of T7_models_numeric.csv (row-aligned with T7_models.csv), in file order (29 of 54 rows).
    "T7_models": [
        "grd_rate:sin_rett:observed:all:any:none:2019-2024",
        "grd_rate:sin_rett:observed:all:any:depth:2019-2024",
        "grd_rate:sin_rett:observed:all:any:disruption:2019-2024",
        "grd_rate:sin_rett:observed:all:any:none:2021-2024",
        "grd_rate:sin_rett:fixed65:all:any:none:2019-2024",
        "grd_rate:sin_rett:observed:hospitalisation:any:none:2019-2024",
        "grd_rate:sin_rett:observed:all:principal:none:2019-2024",
        "grd_rate:sin_rett:fixed65:all:principal:none:2019-2024",
        "grd_rate:strict_autism_f840:observed:all:any:none:2019-2024",
        "grd_hospital:sin_rett:observed:any:none:2019-2024:model",
        "grd_hospital:sin_rett:observed:any:none:2019-2024:cluster",
        "grd_hospital:sin_rett:observed:any:depth:2019-2024:model",
        "grd_hospital:sin_rett:observed:any:ri_none:2019-2024:random_intercept",
        "grd_pop:sin_rett:any:TOTAL:crude:2019-2024",
        "grd_pop:sin_rett:any:TOTAL:age_adjusted:2019-2024",
        "grd_pop:sin_rett:any:HOMBRE:age_adjusted:2019-2024",
        "grd_pop:sin_rett:any:MUJER:age_adjusted:2019-2024",
        "a05_entry:strict_autism:pop:none:2021-2025",
        "a05_entry:strict_autism:estab:none:2021-2025",
        "a05_entry:strict_autism:stable_pop:none:2021-2025",
        "a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025",
        "p2_dec:none:2019-2025",
        "p2_dec:estab:2019-2025",
        "p2_dec:stable:2019-2025",
        "p2_dec:naneas:2023-2025",
        "p6_primary:strict_autism:none:2021-2025",
        "p6_primary:strict_autism:estab:2021-2025",
        "pie_harmonised:none:2019-2025",
        "deis_principal:sin_rett:none:2019-2024",
    ],
}

#: Columns printed for Table 2 (exact header strings of the English T7_models.csv; the Notes column is dropped).
#: The Spanish CSV has the same columns in the same positions, so the Spanish cut selects by position.
TABLE_COLUMNS = {
    "T7_models": ["Estimand", "Series / variant",
                  "Specification (panel; activity; position; denominator/offset; covariates; family)",
                  "Years", "n (obs.)", "APC % (95% CI)", "p value (Wald)", "Dispersion (Pearson χ²/df)"],
}
#: The corpus column «Series / variant» packs the series and the case-definition variant in one cell («F84 any
#: position — F84 without Rett — males»). With one variant in the paper the second half is noise on every row, so
#: it is dropped and the column is titled «Series»; qualifiers that are NOT the variant (sex, stable panel, F84.0
#: only, strict REM autism) are part of the series and survive.
#: Presentation-only header rename of a body table (never moves or reorders a column).
TABLE_COLUMN_RENAME = {"T7_models": {"en": {"Series / variant": "Series"},
                                     "es": {"Serie / variante": "Serie"}}}

#: The exact strings the corpus writes in that cell, in each language (read from the CSVs, not guessed).
_VARIANT_CELL_RULES_EN = [(" — F84 without Rett", ""), (" — independent of Rett (identical)", ""),
                          (" (identical in both variants)", "")]
#: A whole column of an appendix table can BE the case-definition stamp ("Variant: F84 without Rett" on all 111
#: rows of the converged-model table; "Series: F84 family excluding Rett syndrome" on all 32 rows of the annual
#: GRD table). With one variant in the submission such a column carries no information, so it is dropped whole.
#: Only a column whose EVERY non-empty cell is one of these exact strings qualifies: "Rett syndrome" as a data
#: CATEGORY of the REM age-sex table, the "sensitivity, Rett inseparable" caveat and the asset inventory's stored
#: titles are data or method, and none of them is touched.
_VARIANT_ONLY_CELLS = {
    "f84 without rett", "f84 family excluding rett syndrome", "independent of rett (identical)",
    "f84 sin rett", "familia f84 sin síndrome de rett", "no depende de rett (idéntico)",
    "f84 excluding rett", "f84 sin síndrome de rett",
}
#: Appendix tables whose subject IS the comparison of the two case definitions: they keep every mention.
VARIANT_TABLES = ("E28_variant_sensitivity", "M2_case_definitions", "ST10_grd_f84_subcodes", "E81_project_asset_inventory")


#: The appendix names the case definition inside its cells, because the corpus prints both variants side by
#: side. Here the distinction each cell really carries is kept and only the comparative frame is dropped: a row
#: of the main series says so, a row that does not depend on the definition says THAT, and a parenthesis whose
#: only content was "identical in both variants" goes. Every rule is a whole-cell match, so a data category
#: ("Rett syndrome" as a category of the REM age-sex table) can never be caught by it.
_APPENDIX_CELL_MAP = {
    "en": {"F84 without Rett": "Main case definition",
           "F84 family excluding Rett syndrome": "Main case definition",
           "Independent of Rett (identical)": "Not affected by the case definition",
           "F84.0 only (identical in both variants)": "F84.0 only",
           "Strict REM autism (identical in both variants)": "Strict REM autism"},
    "es": {"F84 sin Rett": "Definición de caso principal",
           "familia F84 sin síndrome de Rett": "Definición de caso principal",
           "No depende de Rett (idéntico)": "No depende de la definición de caso",
           "Solo F84.0 (idéntico en ambas variantes)": "Solo F84.0",
           "Autismo estricto REM (idéntico en ambas variantes)": "Autismo estricto REM"},
}


def rewrite_appendix_variant_cells(key: str, df, lang: str):
    """Whole-cell rewrite of the case-definition frame in an appendix table. Returns (frame, n cells changed)."""
    table = _APPENDIX_CELL_MAP.get(lang, {})
    if df is None or key in VARIANT_TABLES or not table:
        return df, 0
    changed, out = 0, df
    for col in list(df.columns):
        vals, touched = [], False
        for v in df[col].astype(str):
            new = table.get(v.strip())
            if new is not None:
                vals.append(new)
                changed += 1
                touched = True
            else:
                vals.append(v)
        if touched:
            if out is df:
                out = df.copy()
            out[col] = vals
    return out, changed


def drop_variant_only_columns(key: str, df):
    """Drop any column of an appendix table whose every non-empty cell is the case-definition stamp.

    Returns (frame, dropped names). A table about the variants keeps them."""
    if df is None or key in VARIANT_TABLES:
        return df, []
    dropped = []
    for col in list(df.columns):
        vals = [str(v).strip() for v in df[col] if str(v).strip()]
        if vals and all(v.lower() in _VARIANT_ONLY_CELLS for v in vals):
            dropped.append(str(col))
    return (df.drop(columns=dropped) if dropped else df), dropped

_VARIANT_CELL_RULES_ES = [(" — F84 sin Rett", ""), (" — no depende de Rett (idéntico)", ""),
                          (" — depende de Rett (idéntico)", ""), (" (idéntico en ambas variantes)", "")]

TABLE_CELL_REWRITE = {
    # keyed by the ENGLISH column name (the frame is located through the English header) with one rule list
    # per language, because the cell text itself is written in the language of the table.
    "T7_models": {"Series / variant": {"en": _VARIANT_CELL_RULES_EN, "es": _VARIANT_CELL_RULES_ES}},
}

#: Column of each body table whose values are printed as 8 pt bold internal headings (journal document mode).
TABLE_HEADING_COLUMN = {"T2_grd_core": "Block", "T7_models": "Estimand"}
#: Column of T7_models rebuilt from the raw p_value of T7_models_numeric.csv (never from the "< 0.001" string).
P_VALUE_COLUMN = {"T7_models": "p value (Wald)"}
#: The same rule for every appendix table whose printed p column comes from a "< 0.001" string while a row-aligned
#: numeric companion carries the raw value: key -> (numeric companion beside the CSV, printed p column, raw column).
P_VALUE_NUMERIC = {"T7_models": ("T7_models_numeric.csv", [("p value (Wald)", "p_value")]),
                   "T7_models_cpa_full": ("T7_models_cpa_full_numeric.csv", [("p value (Wald)", "p_value")]),
                   "E43_moran_sensitivity_main": ("E43_moran_sensitivity_main_numeric.csv",
                                                  [("p (999 permutations)", "p_sim"), ("Analytic p", "p_norm")]),
                   "E50_moran_gistar_all": ("E50_moran_gistar_all_numeric.csv",
                                            [("p (999 perm.)", "p_sim"), ("Analytic p", "p_norm")]),
                   # readers, round 2: the rank-stability table still printed «< 0.001»; its numeric companion is
                   # row-aligned (61 rows) and carries the raw p_value
                   "E48_rank_stability": ("E48_rank_stability_numeric.csv", [("p", "p_value")])}

# ---------------------------------------------------------------------------
# Supplement (plan section 4), in order of first citation from the article
# ---------------------------------------------------------------------------
SUPP_FIGURES = [
    "fig1_sources_coverage", "figE28_variant_sensitivity", "figS10_denominators", "figS11_coverage_age_sex",
    "figE27_model_diagnostics", "figS15_controls", "figS2_grd_subcodes", "EF6_readmission_multiplicity",
    "figS3_grd_hospital_effects", "EF8_hospitals", "EF5_codiagnoses", "figS14_deis_sex_age", "EF10_deis_detail",
    "E12_rem_a03_risk_referral", "E11_rem_a03_codes_by_era", "figS6_rem_stable_panel",
    "E17_rem_establishment_distribution", "figS7_rem_education_models", "figS8_a05_age_sex",
    "E19_rem_definition_era_sensitivity", "E15_rem_p2_p6_detail", "figS5_rem_june_december",
    "figS13_rem_seasonality", "figE22_rem20_capacity", "figE23_surveys_detail", "figE24_education_detail",
    "figS12_junaeb_sex_level", "figS9_regional_maps", "E40_maps_grd_smoothed_ratio", "E42_lisa_gistar_maps",
    "E47_lorenz_theil", "E49_regional_summary", "E46_sae_deprivation", "figE26_cross_source", "figS4_models_cpa",
    "figE26b_sex_ratio_multisource",
]
SUPP_TABLES = [
    "M1_sources_units", "M2_case_definitions", "M3_rem_code_sets", "M4_denominator_layers", "M5_estimator_map",
    "M6_sensitivity_grid", "M7_data_states", "M8_pipeline_map", "M9_software_seeds", "M10_reproduction_controls",
    "S_reporting_checklist",
    "T1_sources", "T_dataflow_counts", "ST1_grd_hospital_panel", "ST8_grd_identifier_audit",
    "ST2_rem_code_dictionary", "S_definition_breaks", "ST3_rem_reporting_establishments", "ST5_survey_items",
    "ST6_junaeb_items", "ST7_provenance", "ST7b_manifest_checks", "ST10_grd_f84_subcodes",
    "E28_variant_sensitivity", "T4_denominators_coverage", "S10_denominator_sensitivity", "ST12a_fonasa_schema",
    "ST12b_isapre_rules", "ST12c_aps_panel", "ST4a_comuna_crosswalk_summary", "ST4b_comuna_unmatched",
    "S11_coverage_age_sex", "E27_model_diagnostics", "T8_controls_compact", "E79_reproduction_controls_by_family",
    "E60_grd_annual_full", "T2_grd_core", "EF6_readmission_multiplicity", "ST9_grd_age_sex",
    "S_grd_population_rates", "S_hospital_rates_2024", "EF8_hospitals", "EF5_codiagnoses",
    "E8_grd_principal_when_secondary", "EF4_severity_weight", "ST11a_deis_annual", "ST11b_deis_vs_grd",
    "S14_deis_sex_age",
    "EF10_deis_detail", "T3_rem_pathway", "E69_rem_code_year_full", "E12_rem_a03_risk_referral",
    "E11_rem_a03_codes_by_era", "S6_stable_panel", "E17_rem_establishment_distribution",
    "S_a05_standardised_rates", "ST13_a05_age_sex", "E14_rem_a05_age_sex", "E19_rem_definition_era_sensitivity",
    "E15_rem_p2_p6_detail", "ST14_p2_p6_june_december", "S13_rem_seasonality", "E1_grd_seasonality",
    "E22_rem20_capacity",
    "T5_survey_benchmarks", "E23_surveys_detail", "T6_education", "E24_education_detail", "S12_junaeb_sex_level",
    "S9_regional_rates", "E62_grd_region_population_rates", "E13_rem_a05_regional",
    "E40_grd_smoothed_ratio_comuna", "E42_local_class_counts",
    "E51_lisa_significant_comunas", "E43_moran_sensitivity_main", "E50_moran_gistar_all",
    "E47_inequality_gini_theil", "E49_regional_summary", "E44_correlation_matrix_comuna",
    "E45_bivariate_moran_pairs", "E48_rank_stability",
    "E46_sae_association", "E41_rem_comuna_place_of_care", "S_convergence_index", "F4_triangulation_series",
    "E26_cross_source", "T7_models", "T7_models_cpa_full", "E26b_sex_ratio_multisource",
    "E80_tidy_data_dictionary",
]
SUPP_PART_A = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "A8_checklist", "A9_analysis_plan", "A10_references"]
#: Supplementary tables with no CSV on disk (built by supplement_journal.checklist_table()).
SYNTHETIC_TABLES = {"S_reporting_checklist"}
assert len(SUPP_FIGURES) == 36 and len(set(SUPP_FIGURES)) == 36
assert len(SUPP_TABLES) == 91 and len(set(SUPP_TABLES)) == 91
#: Tables restored after the first reading round (journal/decisions.md, CLOSE ROUND 1): the outputs of equations
#: 7, 18 and 19 and of the bivariate Moran's I that the methodology describes, plus the two region × year tables.
RESTORED_TABLES = ["EF4_severity_weight", "E14_rem_a05_age_sex", "E1_grd_seasonality",
                   "E62_grd_region_population_rates", "E13_rem_a05_regional", "E45_bivariate_moran_pairs"]
assert all(k in SUPP_TABLES for k in RESTORED_TABLES)

# ---------------------------------------------------------------------------
# References (plan section 6): exactly 30, in order of first citation
# ---------------------------------------------------------------------------
REFERENCE_KEYS = [
    "zeidan2022", "russell2022", "hansen2015", "lundstrom2015", "shaw2025", "lord2022",
    "montielnava2024", "yanez2021", "romanurrestarazu2025", "ley21545",
    "vonelm2007", "benchimol2015",
    "fonasa_grd", "deis_egresos", "minsal_rem", "ine2019", "fonasa_beneficiarios", "endide2022", "encavi2023",
    "mineduc_apuntes60", "mineduc_sinaces2026", "junaeb_eve",
    "ahmad2001", "fay1997", "wedderburn1974",
    "iezzoni1992", "song2010", "loomes2017", "fyfe2026", "garcia2022",
]
#: Round 2 of the readers: the slot of heidari2016 (SAGER, whose statement stands without a citation) goes to
#: fyfe2026, the population-based comparator of the falling male:female ratio that the Summary, Results and
#: Discussion headline (journal/reference_cut.md).
assert len(REFERENCE_KEYS) == 30 and len(set(REFERENCE_KEYS)) == 30
DROPPED_REFERENCE_KEYS = {
    "santomauro2025": "the 'about 1%' sentence rests on zeidan2022",
    "paula2011": "the Brazil/Mexico prevalence sentence is deleted; the six-country study covers Latin America",
    "fombonne2016": "the Brazil/Mexico prevalence sentence is deleted; the six-country study covers Latin America",
    "becerril2011": "segmentation rests on the study's own coverage data (share_fonasa_ine_pct_2025, share_isapre_ine_pct_2025)",
    "minsal2011": "the guideline clause is stated without citation, dated",
    "irarrazaval2023": "ley21545 suffices",
    "cid2024": "payment-mechanism clause deleted",
    "wolter2007": "Taylor linearisation cited in the appendix at estimator 23",
    "ine_base2024": "sensitivity-layer dataset; cited in the appendix",
    "ine_censo2024": "sensitivity-layer dataset; cited in the appendix",
    "fonasa_aps": "sensitivity-layer dataset; cited in the appendix",
    "supersalud_isapre": "sensitivity-layer dataset; cited in the appendix",
    "deis_rem20": "sensitivity-layer dataset; cited in the appendix",
    "heidari2016": "the SAGER statement of Methods stands without a citation; its slot goes to fyfe2026 (round 2)",
    "lai2020": "dropped with the optional sex-ratio paragraph",
    "hull2020": "dropped with the optional sex-ratio paragraph",
    "romanurrestarazu2018": "dropped with the optional Chilean-context paragraph",
    "cid2016": "dropped with the optional Chilean-context paragraph",
    "breinbauer2022": "dropped with the optional Chilean-context paragraph",
    "acevedo2025": "dropped with the optional Chilean-context paragraph",
}

# ---------------------------------------------------------------------------
# Budgets and the number pass (plan sections 3 and 7.5)
# ---------------------------------------------------------------------------
#: Section targets. The plan's paragraph map (section 3) mandates more Methods and Results content than its own
#: section totals of 1350 and 1650 words allow (its paragraph estimates sum to about 1650 and 1950); the targets
#: below are the tightest the mandated content, the appendix pointers and the territory paragraph fit into. The
#: plan's hard ceiling (4800) and floor (3500) of the manuscript text are unchanged (journal/decisions.md, B2).
#: Round-1 readers asked for n beside every %, medians instead of unqualified means, the SAGER limitation, the
#: quality of the evidence in the panel and the restored appendix tables cited from the text: the sections grew
#: by about 100 words. The journal's own window is 3500–5000 words; the ceiling below stays under it.
#: Round 2: the numerator beside every percentage of Results (journal rule «numbers … should always be provided if
#: % is shown») costs about 60 words after compressing six passages; Results moves to 1920, the ceiling stays 4980.
#: `core_body_max` was 4980, chosen so that the rendered count stayed under 5000 even when section headings are
#: counted. The author then asked for every abbreviation to be expanded at its first use "independently of the
#: words", and for the case definition to be stated once with its reason; both are content the journal itself
#: requires (its style rules ask for the expansion, its Methods for the definition). The ceiling is raised to the
#: journal's own figure — "around 3500–5000 words" — and the build reports the measured count, so the trade is
#: visible rather than silently enforced. Trimming back below 4980 is a decision for the author team.
WORD_BUDGET = dict(summary=250, panel=500, introduction=400, methods=1700, results=1920, discussion=1120,
                   conclusion=80, core_body_max=5100, core_body_min=3500, legend_max=300, legend_fig1_max=160)
#: h1 heading of each budgeted section, per language (the article's block grammar uses these exact strings).
SECTION_HEADINGS = {
    "en": dict(summary="Summary", introduction="Introduction", methods="Methods", results="Results",
               discussion="Discussion", conclusion="Conclusion"),
    "es": dict(summary="Resumen", introduction="Introducción", methods="Métodos", results="Resultados",
               discussion="Discusión", conclusion="Conclusión"),
}

PROTECTED_TOKENS = [
    r"\bF84(?:\.\d)?\b",                      # ICD-10 family and subcodes
    r"\b\d{8}\b",                             # REM codes (8 digits)
    r"\bP\d{7}\b",                            # Serie P codes (P6241010, P2500500)
    r"(?:Law|Ley) 21\.545",                   # the law
    r"\b\d+\.\d+\.\d+\b",                     # semantic versions
    r"\bv\d+\.\d+\b",                         # v1.0
    r"(?<=Python )\d+\.\d+",                  # Python 3.14
    r"(?<=version )\d+\.\d+",                 # version 1.0
    r"doi:\S+", r"https?://\S+",
    r"\b\d{4}-\d{2}-\d{2}\b",                 # ISO dates
    r"\S+\.(?:csv|json|py|png|pdf|md|docx|xlsx?|xlsm|zip|rar|txt|parquet|shp|gpkg|geojson|bib|dta|sav|tsv)\b",  # file names
    r"\bFable \d+\.\d+\b",                      # the model version named in the AI declaration
    r"\bclaude-fable-\d+-\d+\b",
    r"\b[a-z_0-9]+:[a-z_0-9]+(?::[A-Za-z0-9_-]+)+\b",  # model ids
    r"\bSHA-256\b",
    r"\b\d+\.º\b",                            # Spanish ordinals (identity for es anyway)
]
_PROTECTED_RE = re.compile("|".join(f"(?:{p})" for p in PROTECTED_TOKENS))
_THOUSANDS_RE = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?!\d)")
_DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")
NNBSP = " "   # narrow no-break space (thousands separator of five-digit and longer numbers)
MIDDOT = "·"  # mid-height decimal point


def _mask(s: str):
    """Replace every protected token by a private placeholder; return (masked, restore)."""
    saved = []

    def keep(m):
        saved.append(m.group(0))
        return f"{len(saved) - 1}"

    masked = _PROTECTED_RE.sub(keep, s)

    def restore(t: str) -> str:
        return re.sub("(\\d+)", lambda m: saved[int(m.group(1))], t)

    return masked, restore


def _thousands(m) -> str:
    digits = m.group(0).replace(",", "")
    if len(digits) == 4:
        return digits
    groups = []
    while digits:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    return NNBSP.join(groups)


WJ = "\ufeff"   # ZERO WIDTH NO-BREAK SPACE before a range dash: no break opens a line with «–2024», and,
#                unlike U+2060 WORD JOINER, LibreOffice does not treat it as a justification stretch point.
#                Measured on a justified sweep of 16 line positions: U+2060 gives 3 same-line gaps up to
#                1·21 pt («2019 –2024», visible at 400 dpi on article p 26); U+FEFF gives none, with the
#                same break behaviour. The name is kept so the call sites read unchanged.
_RANGE_DASH_RE = re.compile(r"(?<=\d)[\u2013](?=\d)")
#: House-style rewrites of the English text (journal_guidelines.md: "eg," and "ie," without stops; Times New
#: Roman has no U+26A0, so the corpus's warning glyph becomes a dagger, which the notes explain).
_HOUSE_STYLE = [(re.compile(r"\be\.g\.,?\s"), "eg, "), (re.compile(r"\bi\.e\.,?\s"), "ie, "),
                (re.compile("⚠"), "†"), (re.compile(r"(?<=\S) +\.(?=\s|$)"), "."),
                # a list of numbers written by the corpus formatter («65, 65, 68 and 72») takes the journal's
                # comma before the final «and»; a two-item «2019 and 2024» has no comma before it and is untouched
                (re.compile(r"(\d[\d·%]*(?:, \d[\d·%]*)+) and (?=\d)"), r"\1, and ")]


def tie_ranges(s: str) -> str:
    """A numeric range («2019–2024», «30·0–42·1») may break AFTER its dash, never before it.

    Both extremes were built and measured, and both failed. With a WORD JOINER on BOTH sides (round 2) the
    dash never opened a line, but each joiner is a word boundary that justification stretches: the character
    geometry of article p 26 showed «2019 –2024» with a real 1·49 pt hole (pdftotext -bbox-layout). With the
    dash BARE, the hole disappeared but LibreOffice broke before the dash anyway — Unicode's «break after»
    class does not settle it — and three lines opened with a dash (EN p 12 «the 2021» / «–2024 window», ES
    p 14 and p 33). One ZERO WIDTH NO-BREAK SPACE before the dash is what survives all three measurements: it removes the break
    opportunity that opens a line with a dash, keeps the one after it, which is correct typography, and halves
    the exposure to the gap, which only shows on a stretched line. Table cells are excluded by the caller,
    whose number-width guard measures the atoms on either side of the dash. The compound-name rule in
    docx_builder keeps both joiners: there, a break inside a proper name is worse than a gap."""
    if not isinstance(s, str) or "–" not in s:
        return s
    return _RANGE_DASH_RE.sub(WJ + "–", s)


ZWSP = "\u200b"   # ZERO WIDTH SPACE: a break opportunity inside a very long machine token (path, URL, code list)
_LONG_TOKEN_RE = re.compile(r"\S{25,}")
_SOFT_AFTER_RE = re.compile(r"([/_\\=&?+]|\.(?=[A-Za-z]))")


def soft_breaks(s: str) -> str:
    """Break opportunities (U+200B) inside machine tokens of 25 characters or more that contain a letter — file
    paths, URLs, code lists — after «/», «_», «\\», «=», «&», «?», «+» and a stop followed by a letter. Never inside
    a number (a token without a letter is untouched). Round 2 of the readers: without them a provenance column had
    to measure 34 cm for one URL, and the whole table fell to 7 pt with its words broken letter by letter."""
    if not isinstance(s, str) or len(s) < 25:
        return s

    def fix(m):
        tok = m.group(0)
        if not re.search(r"[A-Za-z]", tok):
            return tok
        return _SOFT_AFTER_RE.sub(lambda mm: mm.group(1) + ZWSP, tok)

    return _LONG_TOKEN_RE.sub(fix, s)


def journal_text(s: str, lang: str, cells: bool = False) -> str:
    """The journal number pass for English: mid-height decimal point, four-digit numbers without separator,
    longer numbers with a narrow no-break space; protected tokens (codes, versions, DOIs, files) untouched;
    then the house-style rewrites and the range-dash tie. In English table cells the tie is applied too (the
    document builder's number-width guard measures the tied range as one piece in journal mode,
    docx_builder.set_journal_atoms) and very long machine tokens receive soft break opportunities (soft_breaks).
    For every other language only the tie is applied outside cells (the Spanish file keeps the corpus number
    conventions and its cells are untouched)."""
    if not isinstance(s, str) or not s:
        return s
    if lang != "en":
        return s if cells else tie_ranges(s)
    masked, restore = _mask(s)
    masked = _THOUSANDS_RE.sub(_thousands, masked)
    masked = _DECIMAL_RE.sub(MIDDOT, masked)
    for rx, new in _HOUSE_STYLE:
        masked = rx.sub(new, masked)
    out = tie_ranges(restore(masked))
    return soft_breaks(out) if cells else out


def _apply_strings(payload, fn):
    """Apply fn to every string of a block payload (str, list, tuple, dict, DataFrame)."""
    if isinstance(payload, str):
        return fn(payload)
    if isinstance(payload, list):
        return [_apply_strings(x, fn) for x in payload]
    if isinstance(payload, tuple):
        return tuple(_apply_strings(x, fn) for x in payload)
    if isinstance(payload, dict):
        return {k: (v if k in ("path", "df", "embed_dpi", "font_pt", "key", "heading_column", "label") else _apply_strings(v, fn))
                for k, v in payload.items()}
    if isinstance(payload, pd.DataFrame):
        out = payload.copy()
        out.columns = [fn(str(c)) for c in out.columns]
        return out.map(lambda c: fn(c) if isinstance(c, str) else c)
    return payload


def journal_text_blocks(blocks: list, lang: str) -> list:
    """Every string that reaches the document passes through journal_text (paragraphs, headings, panel items,
    captions, table titles, notes and cells). Cross-references stored with the corpus numbering (captions.json,
    titles.json) are remapped ONLY in table/figure payloads not already remapped by JournalRegistry (flag
    refs_remapped); prose written against JournalRegistry already carries the journal numbering."""
    out = []
    for kind, payload in blocks:
        if kind in ("table", "figure") and isinstance(payload, dict) and not payload.get("refs_remapped"):
            payload = dict(payload)
            for field in ("caption", "title", "note"):
                if isinstance(payload.get(field), str):
                    payload[field] = remap_refs(payload[field], lang)
            payload["refs_remapped"] = True
        if kind == "table" and isinstance(payload, dict) and isinstance(payload.get("df"), pd.DataFrame):
            payload = dict(payload)
            payload["df"] = _apply_strings(payload["df"], lambda s: journal_text(s, lang, cells=True))
        out.append((kind, _apply_strings(payload, lambda s: journal_text(s, lang))))
    return out


def format_p(p: float, lang: str = "en") -> str:
    """p to two significant figures ("0·016", "0·50"), "<0·0001" below 0·0001 (comma for Spanish)."""
    p = float(p)
    if math.isnan(p):
        raise ValueError("p value is NaN")
    sep = MIDDOT if lang == "en" else ","
    if p < 1e-4:
        return f"<0{sep}0001"
    if p >= 1:
        return f"1{sep}0"
    exponent = math.floor(math.log10(p))
    decimals = max(0, 1 - exponent)
    s = f"{p:.{decimals}f}"
    if len(s.replace("0.", "").lstrip("0")) > 2:          # rounding carried a digit ("0.0995" -> "0.100")
        s = f"{p:.{decimals - 1}f}"
    return s.replace(".", sep)


# ---------------------------------------------------------------------------
# Tidy tables (numbers the values file does not carry: the territory paragraph)
# ---------------------------------------------------------------------------
def _tidy_rows(file: str, filters: dict) -> pd.DataFrame:
    path = CFG.TIDY / file
    df = pd.read_csv(path)
    m = df
    for col, val in filters.items():
        if col not in m.columns:
            raise KeyError(f"{file}: no column '{col}'")
        m = m[m[col].astype(str) == str(val)]
    return m


def tidy_value(file: str, filters: dict, column: str) -> float:
    """One value of outputs/tidy/<file>: exactly one row must match `filters` (string equality), else raise."""
    m = _tidy_rows(file, filters)
    if len(m) != 1:
        raise ValueError(f"{file}: {len(m)} rows match {filters} (exactly one required)")
    if column not in m.columns:
        raise KeyError(f"{file}: no column '{column}'")
    return float(m.iloc[0][column])


def tidy_count(file: str, filters: dict) -> int:
    """Number of rows of outputs/tidy/<file> matching `filters` (string equality)."""
    return int(len(_tidy_rows(file, filters)))


def tidy_sum(file: str, filters: dict, column: str, rows: dict | None = None) -> float:
    """Sum of `column` over the rows of outputs/tidy/<file> matching `filters`, restricted to the rows whose
    `rows` columns take one of the listed values ({column: [values]}). At least one row must match. This is the
    third documented derivation of the journal text (journal/decisions.md, CLOSE ROUND 2): the numerator of an
    age-band share printed as a percentage (the values file carries the share only), verified against the share
    key at build time by prose_journal_en.age_band_count."""
    m = _tidy_rows(file, filters)
    for col, values in (rows or {}).items():
        if col not in m.columns:
            raise KeyError(f"{file}: no column '{col}'")
        m = m[m[col].astype(str).isin([str(v) for v in values])]
    if m.empty:
        raise ValueError(f"{file}: no row matches {filters} / {rows}")
    if column not in m.columns:
        raise KeyError(f"{file}: no column '{column}'")
    return float(pd.to_numeric(m[column]).sum())


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def _meta(lang: str):
    base = CFG.OUT / VARIANT / lang
    with open(base / "figures" / "captions.json", encoding="utf-8") as fh:
        cap_base = json.load(fh)
    with open(base / "extra" / "figures" / "captions.json", encoding="utf-8") as fh:
        cap_extra = json.load(fh)
    with open(base / "tables" / "titles.json", encoding="utf-8") as fh:
        tit_base = json.load(fh)
    with open(base / "extra" / "tables" / "titles.json", encoding="utf-8") as fh:
        tit_extra = json.load(fh)
    clash = (set(cap_base) & set(cap_extra)) | (set(tit_base) & set(tit_extra))
    if clash:
        raise RuntimeError(f"file stems used by both the main and the extra output folders: {sorted(clash)}")
    fig_dir = {k: base / "extra" / "figures" for k in cap_extra} | {k: base / "figures" for k in cap_base}
    tab_dir = {k: base / "extra" / "tables" for k in tit_extra} | {k: base / "tables" for k in tit_base}
    return {**cap_extra, **cap_base}, {**tit_extra, **tit_base}, fig_dir, tab_dir


def journal_plate(key: str, lang: str, corpus_png: Path) -> Path:
    """The journal-mode render of a supplementary plate (no in-graph titles, journal number style), which the
    supplement embeds in place of the corpus plate. It must exist: falling back to the corpus PNG would put the
    in-graph titles back without anyone noticing."""
    png = PLATE_DIR[lang] / f"{key}.png"
    if not png.is_file():
        raise FileNotFoundError(f"journal plate missing for {key} ({lang}): {png} (render with PLATE_JOURNAL=1); "
                                f"corpus plate at {corpus_png}")
    return png


def journal_captions(lang: str) -> dict:
    """captions.json written beside the journal plates: the corpus caption with each removed panel title
    re-inserted at the start of its (a)… segment (common.journal_caption_entry). Empty if not rendered yet."""
    path = PLATE_DIR[lang] / "captions.json"
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


#: Variant code names that a reader of the journal must not meet in a legend (common._JOURNAL_LABEL_SUBS is
#: the same rule for the artwork).
_LABEL_SUBS = (("con_rett − sin_rett", "full F84 − F84 without Rett"), ("con_rett", "full F84 (with Rett)"),
               ("sin_rett", "F84 without Rett"))


def legend_label_text(text: str, lang: str) -> str:
    if lang != "en" or not isinstance(text, str):
        return text
    for old, new in _LABEL_SUBS:
        text = text.replace(old, new)
    return text


def asset_path(key: str, kind: str, lang: str, body: bool = False) -> Path:
    """Path of a figure PNG or table CSV of the journal package. Only keys of the journal lists are accepted;
    body figures come from PLATE_DIR (journal plate mode), never from figures/."""
    if lang not in LANGS:
        raise ValueError(f"unknown language {lang!r}")
    captions, titles, fig_dir, tab_dir = _meta(lang)
    if kind == "figure":
        if body:
            if key not in BODY_FIGURES:
                raise KeyError(f"'{key}' is not a body figure")
            return PLATE_DIR[lang] / f"{key}.png"
        if key not in SUPP_FIGURES:
            raise KeyError(f"'{key}' is not in SUPP_FIGURES")
        return journal_plate(key, lang, fig_dir[key] / f"{key}.png")
    if kind == "table":
        if key in SYNTHETIC_TABLES:
            raise KeyError(f"'{key}' is synthetic (built by supplement_journal.checklist_table)")
        if key not in SUPP_TABLES and key not in BODY_TABLES:
            raise KeyError(f"'{key}' is not in SUPP_TABLES or BODY_TABLES")
        return tab_dir[key] / f"{key}.csv"
    raise ValueError(f"kind must be 'figure' or 'table', not {kind!r}")


# ---------------------------------------------------------------------------
# Cross-reference remap (plan section 7.7)
# ---------------------------------------------------------------------------
_ITEM_WORDS = {"en": ("Figure", "Table"), "es": ("Figura", "Tabla")}
_DEPOSITED = {"en": "the deposited data", "es": "los datos depositados"}
REMAP_LOG: list[dict] = []
_REF_TOKEN_RE = re.compile(r"((?:\b(?:la|las|el|los|the)\s+)?)\b((?i:figures?|tables?|figuras?|tablas?))\s+(S?)(\d+)"
                           r"([a-f](?:[–-][a-f])?)?(?:\s*[–-]\s*(S?)(\d+))?")
#: Dropped corpus items that duplicate a kept item: a corpus token naming them is remapped to the kept twin
#: instead of "the deposited data" (kind of the twin in the value: "figure" or "table").
DROPPED_ALIASES = {
    ("figure", "figS1_grd_variants"): ("figure", "figE28_variant_sensitivity"),
    ("figure", "E14_rem_a05_age_sex"): ("figure", "figS8_a05_age_sex"),
    ("figure", "E18_rem_monthly_series"): ("figure", "figS13_rem_seasonality"),
    ("figure", "E41_maps_rem_place_of_care"): ("figure", "figS9_regional_maps"),
    ("figure", "E43_moran_scatter_weights"): ("table", "E43_moran_sensitivity_main"),
    ("figure", "E44_correlation_matrix"): ("table", "E44_correlation_matrix_comuna"),
    ("figure", "E45_bivariate_moran"): ("table", "E45_bivariate_moran_pairs"),
    ("figure", "E48_rank_stability"): ("table", "E48_rank_stability"),
    ("figure", "figE25_junaeb_detail"): ("figure", "figS12_junaeb_sex_level"),
    ("figure", "figE21_insurance_coverage"): ("figure", "figS11_coverage_age_sex"),
    ("figure", "figE20_population_structure"): ("figure", "figS11_coverage_age_sex"),
    ("table", "S8_a05_age_sex"): ("table", "ST13_a05_age_sex"),
    ("table", "S5_june_december"): ("table", "ST14_p2_p6_june_december"),
    ("table", "F3_rem_pathway_data"): ("table", "T3_rem_pathway"),
    ("table", "T8_controls"): ("table", "T8_controls_compact"),
    ("table", "S15_controls_scatter"): ("table", "T8_controls_compact"),
}
#: Legacy cross-references inside corpus texts that no registry number resolves (internal numbers of the
#: table module, code keys of the extra modules): exact substitutions per (key, field), with the journal
#: labels filled in by JournalRegistry (T = table labels by key).
LEGACY_REFS = {
    ("ST9_grd_age_sex", "note"): [("in table S4.", "in {T[S_grd_population_rates]}.")],
    ("figS8_a05_age_sex", "caption"): [("(numeric table S7)", "({T[ST13_a05_age_sex]})")],
    ("E42_local_class_counts", "note"): [("in E40 and E41.", "in {T[E40_grd_smoothed_ratio_comuna]} and {T[E41_rem_comuna_place_of_care]}.")],
}
_COMPANION_RE = re.compile(r"^Companion table of plate (E\d+|EF\d+)\. ")
#: Contexts in which a "Table n" token names a table of an EXTERNAL document, never of this study.
_EXTERNAL_CONTEXT_RE = re.compile(r"Apuntes \d+, (?:Table|Tabla) \d+|\((?:Tables|Tablas) 1–2, pp\. 8–9\)")


def _journal_label(key: str, word_fig: str, word_tab: str, is_fig: bool):
    if is_fig:
        if key in BODY_FIGURES:
            return f"{word_fig} {BODY_FIGURES.index(key) + 1}"
        if key in SUPP_FIGURES:
            return f"{word_fig} S{SUPP_FIGURES.index(key) + 1}"
    else:
        if key in BODY_TABLES:
            return f"{word_tab} {BODY_TABLES.index(key) + 1}"
        if key in SUPP_TABLES:
            return f"{word_tab} S{SUPP_TABLES.index(key) + 1}"
    return None


def _corpus_key(is_fig: bool, supp: bool, n: int):
    order = (SM.FIGURE_ORDER if supp else PE.MAIN_FIGURES) if is_fig else (SM.TABLE_ORDER if supp else PE.MAIN_TABLES)
    return order[n - 1] if 1 <= n <= len(order) else None


def remap_refs(text: str, lang: str) -> str:
    """Rewrite corpus-numbered tokens ("Figure S9", "Table 6", "Tables S3–S12", "Figure 3c") to the journal
    numbering; a token whose target is a dropped item becomes "the deposited data" and is logged."""
    if not isinstance(text, str) or not text:
        return text
    word_fig, word_tab = _ITEM_WORDS.get(lang, _ITEM_WORDS["en"])
    masked, restore = _mask_re(text, _EXTERNAL_CONTEXT_RE)

    def one(is_fig, supp, n):
        key = _corpus_key(is_fig, supp, n)
        if key is None:
            return None
        label = _journal_label(key, word_fig, word_tab, is_fig)
        if label is None:
            alias = DROPPED_ALIASES.get(("figure" if is_fig else "table", key))
            if alias is not None:
                label = _journal_label(alias[1], word_fig, word_tab, alias[0] == "figure")
        return key, label

    def repl(m):
        article, word, s1, n1, panels, s2, n2 = m.groups()
        is_fig = word.startswith("Fig")
        plural = word.endswith("s")
        supp = bool(s1)
        if n2 is not None:
            a, b = int(n1), int(n2)
            if b < a:
                return m.group(0)
            items = [one(is_fig, supp, n) for n in range(a, b + 1)]
        else:
            items = [one(is_fig, supp, int(n1))]
        if any(it is None for it in items):
            return m.group(0)
        article = article or ""
        labels = []
        for key, label in items:
            if label is None:
                REMAP_LOG.append(dict(token=m.group(0), key=key, lang=lang))
                continue
            labels.append(label)
        if not labels:
            return _DEPOSITED[lang]          # the leading article is dropped with the token
        if n2 is None:
            return article + labels[0] + (panels or "")
        nums = [lab.split()[-1] for lab in labels]
        heads = {lab.split()[0] for lab in labels}
        head = labels[0].split()[0]
        if len(heads) == 1 and len(labels) > 1:
            digits = [int(x.lstrip("S")) for x in nums]
            contiguous = all(b == a + 1 for a, b in zip(digits, digits[1:])) and len({x.startswith("S") for x in nums}) == 1
            pl = {"Figure": "Figures", "Table": "Tables", "Figura": "Figuras", "Tabla": "Tablas"}[head]
            if contiguous:
                return f"{article}{pl} {nums[0]}–{nums[-1]}"
            return f"{article}{pl} " + ", ".join(nums)
        if len(labels) == 1:
            return article + labels[0]
        return article + ", ".join(labels)

    return restore(_REF_TOKEN_RE.sub(repl, masked))


def _mask_re(s: str, rx):
    saved = []

    def keep(m):
        saved.append(m.group(0))
        return f"{len(saved) - 1}"

    masked = rx.sub(keep, s)

    def restore(t):
        return re.sub("(\\d+)", lambda m: saved[int(m.group(1))], t)

    return masked, restore


# ---------------------------------------------------------------------------
# Word counts per section (before the number pass)
# ---------------------------------------------------------------------------
def section_word_counts(blocks: list, lang: str = "en") -> dict:
    """Words of every h1 section of the article (paragraphs and bullets; [@key] markers and the Summary labels
    removed; the Spanish narrow space before % does not split a word). Keys are the h1 strings."""
    counts: dict[str, int] = {}
    section = None
    for kind, payload in blocks:
        if kind == "h1":
            section = payload
            counts.setdefault(section, 0)
        elif kind in ("p", "bullets") and section is not None:
            texts = payload if kind == "bullets" else [payload]
            for t in texts:
                t = re.sub(r"\[@[^\]]+\]", "", str(t)).replace("**", "").replace(" ", "")
                counts[section] += len(t.split())
    return counts


def budget_report(blocks: list, lang: str = "en") -> dict:
    """Section counts against WORD_BUDGET (keys of WORD_BUDGET; None where a section is absent)."""
    heads = SECTION_HEADINGS[lang]
    sec = section_word_counts(blocks, lang)
    rep = {name: sec.get(h1) for name, h1 in heads.items()}
    rep["core_body"] = sum(sec.get(heads[n], 0) for n in ("introduction", "methods", "results", "discussion", "conclusion"))
    rep["over_budget"] = [n for n in ("summary", "introduction", "methods", "results", "discussion", "conclusion")
                          if rep[n] is not None and rep[n] > WORD_BUDGET[n]]
    return rep


# ---------------------------------------------------------------------------
# Numbering registry of the journal package
# ---------------------------------------------------------------------------
#: The corpus stamps the case-definition variant on the end of every stored title, because its documents carry
#: both variants side by side. This submission carries ONE variant, stated once in Methods, so the stamp is
#: dropped from every title and legend instead of being turned into a parenthesis: it was printing 32 times in
#: the article and 686 times in the appendix, where it says nothing a reader of this paper does not already know.
_TITLE_VARIANT_SUFFIX = {
    "en": [" — F84 without Rett variant",
           " — F84 family excluding Rett syndrome variant",
           " — F84 family excluding Rett syndrome",
           " — Full F84 family (including Rett syndrome)"],
    "es": [" — variante F84 sin Rett",
           " — variante F84 sin síndrome de Rett",
           " — familia F84 sin síndrome de Rett",
           " — familia F84 completa (incluye síndrome de Rett)"],
}
#: A stored title may close with a qualifier of its own ("… — F84 without Rett variant (all specifications)");
#: the qualifier is part of the title and survives the removal of the stamp.
_TRAILING_QUALIFIER_RE = re.compile(r"\s*(\([^()]*\))\s*$")


def journal_title(title: str, lang: str) -> str:
    """Stored title without its provisional number and without the case-definition stamp of the corpus."""
    t = PE._strip_prefix(title)
    m = _TRAILING_QUALIFIER_RE.search(t)
    qualifier, stem = ("", t)
    if m:
        stem, qualifier = t[: m.start()], " " + m.group(1)
    for suffix in _TITLE_VARIANT_SUFFIX[lang]:
        if stem.endswith(suffix):
            return (stem[: -len(suffix)] + qualifier).strip()
    return t


_BODY_LABEL_RE = re.compile(r"^(?:Table|Tabla)\s+\d+$")


def _is_body_label(label: str) -> bool:
    """True for a body label ("Table 1", "Tabla 2"); False for an appendix label ("Table S37")."""
    return bool(_BODY_LABEL_RE.match(str(label).strip()))


class JournalRegistry:
    """Numbering registry of the journal package: supplementary items by their position in SUPP_FIGURES /
    SUPP_TABLES (= order of first citation from the article, frozen by the plan), body items by BODY_FIGURES /
    BODY_TABLES. Same surface as prose_en._Registry plus first_citation_order() and assert_monotone()."""

    def __init__(self, lang: str = "en", variant: str = VARIANT, plate_dir: Path | None = None):
        if lang not in LANGS:
            raise ValueError(f"unknown language {lang!r}")
        if variant != VARIANT:
            raise ValueError(f"the journal package is built for {VARIANT!r} only")
        self.lang, self.variant = lang, variant
        self.FIG_WORD, self.TAB_WORD = _ITEM_WORDS[lang]
        self.plate_dir = Path(plate_dir) if plate_dir else PLATE_DIR[lang]
        self.captions, self.titles, self._fig_dir, self._tab_dir = _meta(lang)
        self.journal_captions = journal_captions(lang)
        self.figs: list[str] = []
        self.tabs: list[str] = []
        self.main_figs: list[str] = []
        self.main_tabs: list[str] = []
        self.main_citations: list[str] = []
        self.article_citations = 0
        #: {table key: [columns dropped]} — the case-definition stamp printed as a whole column of an appendix
        #: table; reported by the build so the removal is visible and auditable.
        self.variant_columns_dropped: dict[str, list] = {}
        #: {table key: cells rewritten} — the comparative frame of the case definition inside a cell.
        self.variant_cells_rewritten: dict[str, int] = {}

    # -- supplementary items -------------------------------------------------
    def fig(self, key: str) -> str:
        if key not in SUPP_FIGURES:
            raise KeyError(f"'{key}' is not in journal_config.SUPP_FIGURES")
        if key not in self.figs:
            self.figs.append(key)
        return f"{self.FIG_WORD} S{SUPP_FIGURES.index(key) + 1}"

    def tab(self, key: str) -> str:
        if key not in SUPP_TABLES:
            raise KeyError(f"'{key}' is not in journal_config.SUPP_TABLES")
        if key not in self.tabs:
            self.tabs.append(key)
        return f"{self.TAB_WORD} S{SUPP_TABLES.index(key) + 1}"

    def figs_range(self, keys: list[str]) -> str:
        """'Figures S3–S5' (contiguous keys) or 'Figures S3, S7'; every key is registered as cited."""
        return SM._range([self.fig(k) for k in keys]) if self._contiguous(keys, SUPP_FIGURES) else \
            self._listed([self.fig(k) for k in keys])

    def tabs_range(self, keys: list[str]) -> str:
        return SM._range([self.tab(k) for k in keys]) if self._contiguous(keys, SUPP_TABLES) else \
            self._listed([self.tab(k) for k in keys])

    @staticmethod
    def _contiguous(keys, order) -> bool:
        idx = [order.index(k) for k in keys]
        return all(b == a + 1 for a, b in zip(idx, idx[1:]))

    @staticmethod
    def _listed(labels) -> str:
        if len(labels) == 1:
            return labels[0]
        word = labels[0].split()[0]
        pl = {"Figure": "Figures", "Table": "Tables", "Figura": "Figuras", "Tabla": "Tablas"}[word]
        return f"{pl} " + ", ".join(lab.split()[-1] for lab in labels)

    # -- body items ----------------------------------------------------------
    def mfig(self, key: str) -> str:
        if key not in BODY_FIGURES:
            raise KeyError(f"'{key}' is not in journal_config.BODY_FIGURES")
        if key not in self.main_figs:
            self.main_figs.append(key)
        label = f"{self.FIG_WORD} {BODY_FIGURES.index(key) + 1}"
        self.main_citations.append(label)
        return label

    def mtab(self, key: str) -> str:
        if key not in BODY_TABLES:
            raise KeyError(f"'{key}' is not in journal_config.BODY_TABLES")
        if key not in self.main_tabs:
            self.main_tabs.append(key)
        label = f"{self.TAB_WORD} {BODY_TABLES.index(key) + 1}"
        self.main_citations.append(label)
        return label

    # -- panel citations (resolved against the plate's own caption) ------------
    def _panels(self, key: str, panels: str) -> str:
        return PE.panel_suffix(self.captions[key].get("caption", ""), panels, key)

    def figp(self, key: str, panels: str) -> str:
        return f"{self.fig(key)}{self._panels(key, panels)}"

    def mfigp(self, key: str, panels: str) -> str:
        return f"{self.mfig(key)}{self._panels(key, panels)}"

    # -- paths ---------------------------------------------------------------
    def fig_path(self, key: str, body: bool = False) -> Path:
        if body:
            if key not in BODY_FIGURES:
                raise KeyError(f"'{key}' is not a body figure")
            return self.plate_dir / f"{key}.png"
        corpus = self._fig_dir[key] / f"{key}.png"
        if key in SUPP_FIGURES:
            png = self.plate_dir / f"{key}.png"
            if png.is_file():
                return png
            if self.plate_dir == PLATE_DIR[self.lang]:
                raise FileNotFoundError(f"journal plate missing for {key} ({self.lang}): {png}; corpus plate at {corpus}")
        return corpus

    def _remap(self, key: str, field: str, text: str) -> str:
        """A corpus text (caption, title, note) with its cross-references rewritten to the journal numbering:
        the registry tokens through remap_refs, and the legacy references that no registry number resolves
        (LEGACY_REFS; the 'Companion table of plate X.' titles of the extra module) through exact substitutions
        whose journal labels are masked while remap_refs runs, so they are never remapped a second time."""
        if not isinstance(text, str) or not text:
            return text
        labels = {k: f"{self.TAB_WORD} S{SUPP_TABLES.index(k) + 1}" for k in SUPP_TABLES}
        kept: list[str] = []

        def hold(label: str) -> str:
            kept.append(label)
            return f"\ue030{len(kept) - 1}\ue031"

        for old, new in LEGACY_REFS.get((key, field), []):
            if old in text:
                text = text.replace(old, hold(new.format(T=labels)))
        if field == "title":
            m = _COMPANION_RE.match(text)
            if m:
                fig = next((k for k in SUPP_FIGURES if k.startswith(m.group(1) + "_")), None)
                if fig is not None:
                    text = hold(f"Companion table of {self.FIG_WORD} S{SUPP_FIGURES.index(fig) + 1}. ") + text[m.end():]
                else:                      # the plate is not printed: the title stands on its own
                    text = text[m.end():]
        text = remap_refs(text, self.lang)
        return re.sub("\ue030(\\d+)\ue031", lambda m: kept[int(m.group(1))], text)

    def tab_path(self, key: str) -> Path:
        return self._tab_dir[key] / f"{key}.csv"

    def caption_text(self, key: str) -> str:
        return self.captions[key].get("caption", "")

    def title_text(self, key: str, kind: str = "figure") -> str:
        meta = self.captions[key] if kind == "figure" else self.titles[key]
        return journal_title(meta.get("title", ""), self.lang)

    def note_text(self, key: str) -> str:
        return self.titles[key].get("note", "")

    def heading_of(self, key: str) -> str:
        """The legend heading of a figure (stored title without its provisional number; variant as a parenthesis)."""
        return self.title_text(key, "figure")

    # -- blocks --------------------------------------------------------------
    def figure_block(self, key: str, label: str, body: bool = False, caption: str | None = None):
        """('figure', {...}). The caption is 'heading. legend' with the corpus numbering remapped; a body plate
        is read from the journal plate folder and embedded at 600 dpi."""
        meta = self.captions[key]
        # Corpus captions carry the corpus numbering and are remapped; a caller-supplied legend already carries
        # the journal numbering (it was written against this registry) and is never remapped. A supplementary
        # plate takes the caption written beside its journal render, which re-inserts the panel titles that the
        # journal mode removed from the artwork (titles belong in the legend).
        if caption is None:
            stored = (self.journal_captions.get(key) or meta).get("caption", "") if not body else meta.get("caption", "")
            legend = legend_label_text(self._remap(key, "caption", stored), self.lang)
        else:
            legend = caption
        text = f"{self.title_text(key)}. {legend}".strip()
        payload = dict(path=self.fig_path(key, body=body), caption=text, label=label, refs_remapped=True)
        if body:
            payload["embed_dpi"] = 600
        return ("figure", payload)

    def table_block(self, key: str, label: str, rows=None, columns=None, df: pd.DataFrame | None = None,
                    title: str | None = None, note: str | None = None):
        """('table', {...}). For a body table the presentation filter TABLE_ROWS/TABLE_COLUMNS is applied (cells
        byte-identical to the CSV; the p column of T7_models rebuilt from the raw p_value). A synthetic table
        passes its own df/title/note."""
        # The presentation cut belongs to the BODY item only: the same key printed in the appendix under its
        # S-label ("Table S37", "Table S82") is the unmodified full table of which the body table is the cut.
        body = key in BODY_TABLES and (rows is not None or _is_body_label(label))
        heading_column = None
        if df is None:
            if key in SYNTHETIC_TABLES:
                raise KeyError(f"'{key}' is synthetic: pass df, title and note")
            df = pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False)
            # the Block/Estimand column is named in the language of the CSV (Bloque/Estimando in Spanish): it is
            # located by its position in the English file BEFORE the cut, so the document builder finds it in
            # both languages (the cut keeps the column names of the language)
            heading_column = self._heading_column(key, df)
            if body:
                df = self._cut(key, df, rows, columns)
        meta = self.titles.get(key, {})
        if df is not None and not body:
            df, dropped_variant_cols = drop_variant_only_columns(key, df)
            if dropped_variant_cols:
                self.variant_columns_dropped[key] = dropped_variant_cols
            df, n_cells = rewrite_appendix_variant_cells(key, df, self.lang)
            if n_cells:
                self.variant_cells_rewritten[key] = n_cells
        if df is not None and not body and key in P_VALUE_NUMERIC:
            df = self._rebuild_p(key, df)          # journal rule: p to two significant figures, never "< 0.001"
        if title is None:      # corpus title: remapped; a caller-supplied title is journal-numbered already
            title = self._remap(key, "title", self.title_text(key, "table")) if key in self.titles else ""
        if note is None:
            note = self._remap(key, "note", PE.table_note(key, meta.get("note", ""), df, self.lang)) if key in self.titles else ""
        payload = dict(df=df, title=title, note=note, label=label, refs_remapped=True, key=key)
        if key in BODY_TABLES:
            payload["font_pt"] = 8
            payload["heading_column"] = heading_column if heading_column in list(df.columns) else None
        return ("table", payload)

    def _rebuild_p(self, key: str, df: pd.DataFrame) -> pd.DataFrame:
        """The p column of a full model table rebuilt from the raw p_value of its row-aligned numeric companion
        (format_p: two significant figures, "<0·0001"); every other cell untouched."""
        num_name, columns = P_VALUE_NUMERIC[key]
        en_dir = _meta("en")[3][key]
        num = pd.read_csv(en_dir / num_name, dtype=str, keep_default_na=False)
        en = pd.read_csv(en_dir / f"{key}.csv", dtype=str, keep_default_na=False, nrows=0)
        if len(num) != len(df) or len(en.columns) != len(df.columns):
            raise RuntimeError(f"{num_name} is not row-aligned with {key}, or the {self.lang} table is not column-aligned")
        out = df.copy()
        for pcol, raw in columns:
            if raw not in num.columns or pcol not in en.columns:
                raise RuntimeError(f"{key}: printed column {pcol!r} or raw column {raw!r} not found")
            out.iloc[:, list(en.columns).index(pcol)] = [format_p(float(v), self.lang) for v in num[raw]]
        return out

    def _heading_column(self, key: str, df: pd.DataFrame) -> str | None:
        """Name, in the CSV of the registry's language, of the internal-heading column of a body table."""
        name = TABLE_HEADING_COLUMN.get(key)
        if name is None:
            return None
        if name in df.columns:
            return name
        en = pd.read_csv(CFG.OUT / VARIANT / "en" / "tables" / f"{key}.csv", dtype=str, keep_default_na=False, nrows=0)
        if name in en.columns and len(en.columns) == len(df.columns):
            return str(df.columns[list(en.columns).index(name)])
        return None

    def _cut(self, key: str, df: pd.DataFrame, rows, columns) -> pd.DataFrame:
        """Row and column whitelist. Rows are located in the ENGLISH CSV (labels of TABLE_ROWS) and the same
        positions are taken from the CSV of the registry's language (row-aligned outputs)."""
        rows = TABLE_ROWS[key] if rows is None else rows
        columns = TABLE_COLUMNS.get(key) if columns is None else columns
        en = df if self.lang == "en" else pd.read_csv(CFG.OUT / VARIANT / "en" / "tables" / f"{key}.csv",
                                                      dtype=str, keep_default_na=False)
        if en.shape != df.shape:
            raise RuntimeError(f"{key}: the {self.lang} table ({df.shape}) is not row-aligned with the English one ({en.shape})")
        if key == "T7_models":
            num = pd.read_csv(CFG.OUT / VARIANT / "en" / "tables" / "T7_models_numeric.csv", dtype=str, keep_default_na=False)
            if len(num) != len(en):
                raise RuntimeError("T7_models_numeric.csv is not row-aligned with T7_models.csv")
            ids = list(num["model_id"])
            missing = [r for r in rows if r not in ids]
            if missing:
                raise KeyError(f"T7_models: model ids not found: {missing}")
            pos = [ids.index(r) for r in rows]
            if pos != sorted(pos):
                raise ValueError("T7_models: the whitelist must follow the file order")
            out = df.iloc[pos].copy()
            pcol = P_VALUE_COLUMN[key]
            pidx = list(en.columns).index(pcol)
            out.iloc[:, pidx] = [format_p(float(num.iloc[i]["p_value"]), self.lang) for i in pos]
        else:
            pairs = list(zip(en["Block"], en["Indicator"]))
            missing = [r for r in rows if r not in pairs]
            if missing:
                raise KeyError(f"{key}: rows not found: {missing}")
            pos = [pairs.index(r) for r in rows]
            if pos != sorted(pos):
                raise ValueError(f"{key}: the whitelist must follow the file order")
            out = df.iloc[pos].copy()
        # The case-definition stamp inside a cell goes before the column whitelist, because the whitelist may
        # rename the column it lives in ("Series / variant" -> "Series").
        for col_en, by_lang in TABLE_CELL_REWRITE.get(key, {}).items():
            if col_en not in list(en.columns):
                raise KeyError(f"{key}: cell-rewrite column {col_en!r} not found")
            rules = by_lang[self.lang] if isinstance(by_lang, dict) else by_lang
            j = list(en.columns).index(col_en)
            vals = []
            for v in out.iloc[:, j].astype(str):
                for old, new in rules:
                    v = v.replace(old, new)
                vals.append(v.strip())
            out.iloc[:, j] = vals
        if columns:
            cidx = [list(en.columns).index(c) for c in columns]
            out = out.iloc[:, cidx]
            # A header of the corpus may name something the submission no longer distinguishes
            # ("Series / variant" -> "Series"); the rename is presentation only and never moves a column.
            rename = TABLE_COLUMN_RENAME.get(key, {}).get(self.lang, {})
            if rename:
                out.columns = [rename.get(c, c) for c in out.columns]
        return out.reset_index(drop=True)

    def nrows(self, key: str) -> int:
        return len(pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False))

    # -- order of first citation ---------------------------------------------
    def first_citation_order(self) -> dict:
        return dict(figures=list(self.figs), tables=list(self.tabs), body_figures=list(self.main_figs),
                    body_tables=list(self.main_tabs))

    def assert_monotone(self, complete: bool = True) -> None:
        """Raise unless every list of first citations is ascending in the journal numbering (and, when
        `complete`, cites every item of SUPP_FIGURES / SUPP_TABLES / BODY_* exactly in order)."""
        for name, cited, order in (("figures", self.figs, SUPP_FIGURES), ("tables", self.tabs, SUPP_TABLES),
                                   ("body figures", self.main_figs, BODY_FIGURES),
                                   ("body tables", self.main_tabs, BODY_TABLES)):
            idx = [order.index(k) for k in cited]
            if idx != sorted(idx):
                bad = [(order[i], i + 1) for i in idx]
                raise AssertionError(f"{name}: first citations are not ascending: {bad}")
            if complete and cited != list(order):
                missing = [k for k in order if k not in cited]
                raise AssertionError(f"{name}: not every item is cited by the article; missing {missing}")


def with_internal_headings(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Presentation helper for the document builder: the values of `column` become heading rows (the value in the
    first cell, every other cell empty) inserted before each group, and the column itself is dropped."""
    if column not in df.columns:
        return df
    rest = [c for c in df.columns if c != column]
    rows = []
    last = None
    for _, r in df.iterrows():
        if r[column] != last:
            rows.append({rest[0]: r[column], **{c: "" for c in rest[1:]}, "_heading": True})
            last = r[column]
        rows.append({**{c: r[c] for c in rest}, "_heading": False})
    return pd.DataFrame(rows, columns=rest + ["_heading"])


# ---------------------------------------------------------------------------
# Table presentation for the journal (readers, round 2): heading rows, lettered footnotes, column parts
# ---------------------------------------------------------------------------
# Nine appendix tables were set at 7 pt and a dozen more printed words broken inside their cells because their
# columns, at the journal's 8 pt, need more than the 24,7 cm of an A4 landscape page. The cells are never altered:
# a table that does not fit is PRESENTED differently — (a) a column whose value repeats over runs of rows becomes
# the 8 pt bold internal heading the journal provides for («Headings within tables»); (b) a free-text notes column
# whose sentences repeat across rows becomes lettered footnotes under the table (a sentence present in every row
# is stated once in the note); (c) a running «#» column identifies the row across parts; (d) the remaining
# columns are split into consecutive PARTS, each of which fits the landscape page at 8 pt with no column narrower
# than its longest unbreakable piece, the key columns repeated in every part and the parts labelled
# «Table Sn (part i of m)». The measurement is the document builder's own (docx_builder._ancho_texto,
# _ancho_numero, numeros_de in journal mode) on the cells as they will be printed (journal_text with cells=True).
LANDSCAPE_TEXT_CM = 24.7          # pipeline/10_manuscript.LANDSCAPE_TEXT_WIDTH_CM
PART_MARGIN_CM = 0.4              # kept free in every part for the builder's own rounding
TABLE_PT = 8.0
INDEX_COLUMN = "#"
#: key = which columns repeat in every part (file order otherwise); heading_column = internal heading rows;
#: footnotes = the free-text column turned into lettered footnotes; index = prepend the running «#» column.
TABLE_LAYOUT = {
    "T7_models_cpa_full": dict(heading_column="Estimand", footnotes="Note", index=True,
                               keys=["Source", "Outcome (numerator)"]),
    "T7_models": dict(heading_column="Estimand", footnotes="Notes", footnote_split="semicolon", index=True,
                      keys=["Series / variant"]),
    "T1_sources": dict(keys=["Source"]),
    "T_dataflow_counts": dict(keys=["Question", "Source"]),
    "ST8_grd_identifier_audit": dict(keys=["Year", "Series"]),
    "ST2_rem_code_dictionary": dict(keys=["REM module", "Code"]),
    "ST5_survey_items": dict(keys=["Survey", "Variable"]),
    "ST6_junaeb_items": dict(keys=["Year", "Level"]),
    "ST7_provenance": dict(keys=["Source", "File"]),
    "ST7b_manifest_checks": dict(keys=["Source", "File"]),
    "ST12a_fonasa_schema": dict(keys=["Year"]),
    "ST12b_isapre_rules": dict(keys=["Year"]),
    "ST11a_deis_annual": dict(keys=["Year"]),
    "ST11b_deis_vs_grd": dict(keys=["Year", "Series"]),
    "ST14_p2_p6_june_december": dict(keys=["Series", "Year"]),
    "T5_survey_benchmarks": dict(keys=["Survey", "Year", "Subgroup"]),
    "E44_correlation_matrix_comuna": dict(keys=["Scale", "Indicator"]),
}
_SENTENCE_SPLIT_RE = re.compile(r"(?<=\.)\s+(?=[A-Z0-9(«\"'])")


def _letters(i: int) -> str:
    """a … z, aa, ab …"""
    out = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        out = chr(97 + r) + out
    return out


_SEMICOLON_SPLIT_RE = re.compile(r";\s+")


def footnote_column(df: pd.DataFrame, col: str, split: str = "sentence") -> tuple[pd.DataFrame, str]:
    """The free-text column `col` as lettered footnotes: each distinct sentence (or, with split="semicolon",
    each «;»-separated clause) gets a letter in order of first appearance, a sentence present in every row is
    stated once, the column keeps its name and prints the letters of its row. Returns (df, the text to append
    to the table note)."""
    rx = _SEMICOLON_SPLIT_RE if split == "semicolon" else _SENTENCE_SPLIT_RE
    rows = []
    for cell in df[col]:
        text = " ".join(str(cell).split())
        sents = [x.strip().rstrip(";") for x in rx.split(text) if x.strip() and re.search(r"[A-Za-z]", x)]
        rows.append(sents)
    n = len(rows)
    counts: dict = {}
    for sents in rows:
        for x in dict.fromkeys(sents):
            counts[x] = counts.get(x, 0) + 1
    common = [x for x in counts if n > 1 and counts[x] == n]
    letters: dict = {}
    for sents in rows:
        for x in sents:
            if x not in common and x not in letters:
                letters[x] = _letters(len(letters))
    out = df.copy()
    out[col] = [", ".join(letters[x] for x in dict.fromkeys(sents) if x in letters) or "—" for sents in rows]
    parts = []
    if common:
        parts.append("In every row: " + " ".join(common))
    if letters:
        parts.append("Notes: " + "; ".join(f"{L}, {x.rstrip('.')}" for x, L in letters.items()) + ".")
    return out, " ".join(parts)


class _journal_atoms:
    def __enter__(self):
        import docx_builder as DB
        self.DB, self.prev = DB, DB.JOURNAL_ATOMS
        DB.set_journal_atoms(True)

    def __exit__(self, *exc):
        self.DB.set_journal_atoms(self.prev)


def column_min_cm(header: str, cells: list, pt: float = TABLE_PT) -> float:
    """Narrowest width at which the column prints no broken word and no broken number (the builder's rule)."""
    import docx_builder as DB
    pad, seg = 0.40, 1.08
    printed = [DB.texto_indivisible(c) for c in cells]
    tok = max([DB._ancho_texto(w, pt) for t in printed for w in DB._palabras(t)] or [0.0])
    cab = max([DB._ancho_texto(w, pt, bold=True) for w in str(header).split()] or [0.0])
    with _journal_atoms():
        num = max([DB._ancho_numero(x, pt) for t in printed for x in DB.numeros_de(t)] or [0.0])
        numh = max([DB._ancho_numero(x, pt, bold=True) for x in DB.numeros_de(header)] or [0.0])
    return max(tok, cab, num, numh) * seg + pad


def column_parts(df: pd.DataFrame, keys: list, heading_column: str | None, lang: str = "en") -> list[list]:
    """Consecutive groups of columns (keys repeated) each of which fits the landscape page at 8 pt; one group
    when the whole table fits."""
    cols = [c for c in df.columns if c != heading_column]
    width = {c: column_min_cm(journal_text(str(c), lang), [journal_text(str(v), lang, cells=True) for v in df[c]])
             for c in cols}
    if sum(width.values()) <= LANDSCAPE_TEXT_CM:
        return [cols]
    keys = [k for k in keys if k in cols]
    budget = LANDSCAPE_TEXT_CM - PART_MARGIN_CM - sum(width[k] for k in keys)
    parts, cur, cur_w = [], [], 0.0
    for c in cols:
        if c in keys:
            continue
        if cur and cur_w + width[c] > budget:
            parts.append(keys + cur)
            cur, cur_w = [], 0.0
        cur.append(c)
        cur_w += width[c]
    if cur:
        parts.append(keys + cur)
    return parts


def restructure_table_block(block, lang: str = "en") -> list:
    """One ('table', payload) block -> the list of blocks that present it within the journal's table rules
    (see above). Blocks without a `key`, non-table blocks and tables that already fit are returned unchanged."""
    kind, payload = block
    if kind != "table" or not isinstance(payload, dict) or not isinstance(payload.get("df"), pd.DataFrame):
        return [block]
    key = payload.get("key")
    lay = TABLE_LAYOUT.get(key, {})
    df = payload["df"].copy()
    note = str(payload.get("note") or "")
    if lay.get("footnotes") and lay["footnotes"] in df.columns:
        df, extra = footnote_column(df, lay["footnotes"], lay.get("footnote_split", "sentence"))
        note = (note.rstrip() + " " + extra).strip()
    heading_column = payload.get("heading_column") or lay.get("heading_column")
    if heading_column not in list(df.columns):
        heading_column = None
    if lay.get("index"):
        df.insert(0, INDEX_COLUMN, [str(i) for i in range(1, len(df) + 1)])
    first = next((c for c in df.columns if c not in (INDEX_COLUMN, heading_column)), None)
    keys = ([INDEX_COLUMN] if lay.get("index") else []) + list(lay.get("keys") or ([first] if first else []))
    parts = column_parts(df, keys, heading_column, lang)
    out = []
    for i, cols in enumerate(parts, 1):
        keep = [c for c in cols] + ([heading_column] if heading_column else [])
        sub = df[[c for c in keep if c in df.columns]]
        if heading_column:                      # the heading column stays first for the document builder
            sub = sub[[heading_column] + [c for c in sub.columns if c != heading_column]]
        pl = dict(payload, df=sub.reset_index(drop=True), note=(note if i == len(parts) else ""),
                  heading_column=heading_column, restructured=True, part=(i, len(parts)))
        if len(parts) > 1:
            pl["label"] = f"{payload['label']} (part {i} of {len(parts)})"
            pl["continuation"] = i > 1
        out.append((kind, pl))
    return out


def restructure_blocks(blocks: list, lang: str = "en") -> list:
    """Every table block of a document through restructure_table_block (the supplement, in build_journal)."""
    out = []
    for block in blocks:
        out.extend(restructure_table_block(block, lang))
    return out


# ---------------------------------------------------------------------------
# Abbreviations: expanded once, at first use, in each document
# ---------------------------------------------------------------------------
#: The corpus writes for a reader who already knows the Chilean administrative vocabulary; a journal reader does
#: not. Every abbreviation this submission prints is expanded at its FIRST use in each document — the article and
#: the appendix are read separately, so each expands on its own — and left bare afterwards. Wording is authored
#: here, not generated: the expansion is the official English name of the source WITHOUT its article, so the
#: surrounding prose supplies it («the INE projections» -> «the National Statistics Institute (INE)
#: projections», «del INE» -> «del Instituto Nacional de Estadísticas (INE)»), with the Spanish name kept
#: where the institution has no English name of its own. Entries whose expansion the corpus prose already writes
#: (GRD, APS, PIE, CMA, APC, ASD, PDD) are absent on purpose.
ABBREVIATIONS = {
    "en": {
        "DEIS": "Department of Health Statistics and Information",
        "REM": "Monthly Statistical Records",
        "REM-20": "REM-20, the hospital activity and capacity module",
        "FONASA": "National Health Fund",
        "ISAPRE": "private health insurance institutions",
        "SNSS": "National System of Health Services",
        "INE": "National Statistics Institute",
        "JUNAEB": "National Board of School Aid and Scholarships",
        "ENDIDE": "National Disability and Dependence Survey",
        "ENCAVI": "National Quality of Life and Health Survey",
        "CASEN": "National Socioeconomic Characterisation Survey",
        "NANEAS": "children and adolescents with special health-care needs",
        "MINEDUC": "Ministry of Education",
        "ICD-10": "International Classification of Diseases, 10th revision",
        "M-CHAT-R/F": "Modified Checklist for Autism in Toddlers, Revised, with Follow-Up",
        "WHO": "World Health Organization",
        "CI": "confidence interval",
        "IQR": "interquartile range",
        "SD": "standard deviation",
        "SAGER": "Sex and Gender Equity in Research",
        "ICMJE": "International Committee of Medical Journal Editors",
        "DOI": "digital object identifier",
        "SAE": "small-area estimation",
        "LISA": "local indicators of spatial association",
        "SIR": "standardised incidence ratio",
    },
    "es": {
        "DEIS": "Departamento de Estadísticas e Información de Salud",
        "REM": "Registros Estadísticos Mensuales",
        "REM-20": "REM-20, el módulo de actividad y capacidad hospitalaria",
        "FONASA": "Fondo Nacional de Salud",
        "ISAPRE": "instituciones de salud previsional",
        "SNSS": "Sistema Nacional de Servicios de Salud",
        "INE": "Instituto Nacional de Estadísticas",
        "JUNAEB": "Junta Nacional de Auxilio Escolar y Becas",
        "ENDIDE": "Encuesta Nacional de Discapacidad y Dependencia",
        "ENCAVI": "Encuesta Nacional de Calidad de Vida y Salud",
        "CASEN": "Encuesta de Caracterización Socioeconómica Nacional",
        "NANEAS": "niños, niñas y adolescentes con necesidades especiales de atención en salud",
        "MINEDUC": "Ministerio de Educación",
        "ICD-10": "Clasificación Internacional de Enfermedades, 10.ª revisión",
        "CIE-10": "Clasificación Internacional de Enfermedades, 10.ª revisión",
        "M-CHAT-R/F": "lista de verificación modificada para autismo en niños pequeños, revisada, con seguimiento",
        "WHO": "Organización Mundial de la Salud",
        "OMS": "Organización Mundial de la Salud",
        "IC": "intervalo de confianza",
        "RIC": "rango intercuartílico",
        "DE": "desviación estándar",
        "SAGER": "Sex and Gender Equity in Research",
        "ICMJE": "International Committee of Medical Journal Editors",
        "DOI": "identificador de objeto digital",
        "SAE": "estimación en áreas pequeñas",
        "LISA": "indicadores locales de asociación espacial",
        "SIR": "razón estandarizada de incidencia",
    },
}
#: Kinds of block whose text is prose the reader reads in order. A table cell, a reference and an equation are
#: never the place to introduce an abbreviation, and a heading would break its own typography.
_ABBR_BLOCK_KINDS = ("p", "panel", "figure", "table")
_ABBR_FIELDS = {"figure": ("caption",), "table": ("title", "note")}


def _abbr_pattern(abbr: str) -> re.Pattern:
    """The abbreviation as a standalone token: not inside a longer word, a code or a file name."""
    return re.compile(r"(?<![\w./-])" + re.escape(abbr) + r"(?![\w/-]|\.\w)")


def expand_abbreviations(blocks: list, lang: str) -> tuple[list, dict]:
    """Expand every abbreviation of ABBREVIATIONS at its FIRST use in this document, and leave the rest bare.

    Returns the blocks and a report {abbr: where} for the checklist. An abbreviation the prose already defines
    (the expansion is written immediately before it, or it is introduced in parentheses) is left untouched, so
    the corpus wording always wins over the table."""
    table = ABBREVIATIONS.get(lang, {})
    done, report = set(), {}
    out = []
    for idx, (kind, payload) in enumerate(blocks):
        if kind not in _ABBR_BLOCK_KINDS or not table:
            out.append((kind, payload))
            continue

        def expand(text: str, _idx=idx) -> str:
            if not isinstance(text, str) or not text:
                return text
            for abbr, full in table.items():
                if abbr in done:
                    continue
                m = _abbr_pattern(abbr).search(text)
                if not m:
                    continue
                before = text[max(0, m.start() - len(full) - 4):m.start()]
                if full.lower() in before.lower() or text[m.end():m.end() + 1] == ")":
                    done.add(abbr)          # the prose defines it already
                    report[abbr] = "prose"
                    continue
                text = text[:m.start()] + f"{full} ({abbr})" + text[m.end():]
                done.add(abbr)
                report[abbr] = f"block {_idx} ({kind})"
            return text

        if kind == "p":
            payload = expand(payload)
        elif kind == "panel" and isinstance(payload, dict):
            payload = dict(payload)
            payload["items"] = [(h, expand(t)) for h, t in payload.get("items", [])]
        elif isinstance(payload, dict):
            payload = dict(payload)
            for field in _ABBR_FIELDS.get(kind, ()):
                if isinstance(payload.get(field), str):
                    payload[field] = expand(payload[field])
        out.append((kind, payload))
    return out, report
