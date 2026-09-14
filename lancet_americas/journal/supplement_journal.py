# -*- coding: utf-8 -*-
"""supplement_journal.py — the ONE English supplementary appendix of the `sin_rett` journal submission.

Builder S of `journal/plan.md` (section 4 and contract 7.2). Produces the block list, in the grammar of
`docx_builder.build_document`, of a single supplementary document for *The Lancet Regional Health – Americas*:

  front matter   title, authors, the statement that the F84-without-Rett variant is the one submitted and where the
                 full-family variant is compared, and the standing rules stated once in prose — with no heading, so
                 that the table of contents that `build_journal.py` inserts before the first h1 (its own ("toc", …)
                 block, pages filled and verified in its two-pass build, plan 7.6) follows them; `blocks(...,
                 toc=True, pages=…)` prints instead the module's own TOC (one 10 pt line per Part, M-section,
                 A8/A9, B-group, Figure S and Table S) for standalone builds;
  Part A         the APPLIED METHODOLOGY in full, verbatim from `prose_methods_extended.methods_blocks` so that the
                 33 equations of `equations_lancet` print once each, in numeric order, under the estimator that
                 first uses them and cited from its heading; the estimator map (M5_estimator_map) and the grid of
                 pre-specified sensitivities (M6_sensitivity_grid) print as Tables S5 and S6 where they are
                 discussed; then A8 = the STROBE + RECORD checklist as Table S11 with the "Where reported" column
                 mapped to the journal sections and S-numbers; A9 = the pre-specified analysis plan (v1.0,
                 4 September 2026) rendered in English; A10 = the appendix references, numbered separately;
  Part B         every figure and table the plan assigns to the supplement, numbered S1, S2, … in the order in
                 which the ARTICLE first cites them, each introduced by a paragraph that says what it shows (unit
                 and denominator, reused from `supplementary_material.figure_intro` where it fits), why it matters
                 and what it adds beyond the body.

Numbering is the position in SUPP_FIGURES / SUPP_TABLES (index + 1), which is the first-citation order of the
plan; `FIRST_CITED` names the article paragraph that first cites each item and `_check_registry_order()` asserts
at import that the S-numbers ascend with that order. `cross_reference_problems(article_blocks)` checks both
directions against an assembled article (every S-item cited in the article exists here; every item here is
cited at least once; first citations ascend) — `tests/test_supplement_journal.py` runs it against
`prose_journal_en.article()` when that module exists.

Reuse and fallbacks. The registry of `journal_config.JournalRegistry` is used when `journal_config` is importable
(contract 7.1); otherwise `_LocalRegistry`, with the same surface, reads the corpus `captions.json` /
`titles.json` of `outputs/sin_rett/en/{figures,extra/figures,tables,extra/tables}` exactly as
`prose_en._Registry` does. Captions and notes of the corpus carry CORPUS numbering ("Table S27", "Figure 5"):
by default they are returned untouched because `build_journal` remaps them once through
`journal_config.remap_refs` (contract 7.7); `blocks(..., remap=True)` remaps them here instead (for standalone
verification), with `_local_remap` as the fallback. The prose written in this module already carries JOURNAL
labels produced by the registry and must never be remapped.

Numbers. Every number printed in the prose of this module comes from `outputs/values_sin_rett.json` (key named
in `_fields`), from the row count of the table being printed (`R.nrows`) or from the size of a code registry
(`equations_lancet`, `prose_methods_extended.SENSITIVITY_GRID`); nothing is typed by hand. The journal number
pass (mid-height decimals, thin-space thousands) is applied by `build_journal` after word counting, so the text
here uses the corpus English conventions of `prose_en` (n0, n1, n2, pct, ppct, nw).

Standing rules of the study hold in every sentence here: counts are administrative recognition, never
prevalence or incidence; the hospital outcome is episodes with documented F84 and principal F84 is a separate
series; no person-level linkage, no stage-to-stage ratios between unlinked sources; stocks and flows never on one
axis; place of care and residence never mixed without the warning; December primary and June sensitivity, never
summed; cells below five suppressed; Law 21.545 is context only.

Public API (contract 7.2, plus the keyword extensions documented in journal/decisions.md):
  blocks(lang, V, *, pages=None, toc=True, remap=False, R=None) -> list[tuple]
  build(lang, V, **kw) -> dict(blocks, toc, figures, tables)
  checklist_table(R=None) -> pandas.DataFrame   (Item, Recommendation, Where reported, Status)
  analysis_plan_blocks() -> list[tuple]
  toc_entries(blocks) -> list[dict]             (id, level, text) for every TOC line the document needs
  cited_items(article_blocks) -> dict(figures=[...], tables=[...])   keys in order of first citation
  cross_reference_problems(article_blocks) -> list[str]
  equation_problems(blocks) -> list[str]
  SUPP_FIGURES, SUPP_TABLES, PART_A_TABLES, FIRST_CITED, SECTIONS, BODY_FIGURES, BODY_TABLES
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
LA = HERE.parent
for _p in (str(LA), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as CFG  # noqa: E402
import equations_lancet as EQ  # noqa: E402
import prose_en as PE  # noqa: E402
import prose_methods_extended as PME  # noqa: E402
import supplementary_material as SM  # noqa: E402

VARIANT = "sin_rett"
LANG = "en"
SUBMISSION_LANGS = ("en",)

ANALYSIS_PLAN_MD = LA / "analysis_plan.md"
ANALYSIS_PLAN_VERSION = "1.0"
ANALYSIS_PLAN_DATE_EN = "4 September 2026"
ANALYSIS_PLAN_DATE_ES = "4 de septiembre de 2026"   # the stamp of the Spanish original, asserted at render time

CHECKLIST_KEY = "S_reporting_checklist"           # synthetic table key of A8 (plan 4, Part A)
TOC_PLACEHOLDER = "—"                        # fixed-width page placeholder of the first pass (plan 7.6)

# Journal body items (plan section 2). Read from journal_config when it exists; these are the plan's values.
BODY_FIGURES = ["fig1_dataflow", "fig2_grd_core", "fig3_rem_pathway", "fig4_triangulation"]
BODY_TABLES = ["T2_grd_core", "T7_models"]


def _journal_config():
    """`journal_config` of builder B when it is importable, else None (every use has a local fallback)."""
    try:
        import journal_config as JC  # noqa: WPS433
    except Exception:  # noqa: BLE001  (missing module, or a module that fails while builder B is still writing it)
        return None
    return JC


_JC = _journal_config()
if _JC is not None:
    BODY_FIGURES = list(getattr(_JC, "BODY_FIGURES", BODY_FIGURES))
    BODY_TABLES = list(getattr(_JC, "BODY_TABLES", BODY_TABLES))

# ---------------------------------------------------------------------------
# Article paragraphs that first cite an appendix item, in the order of the article (plan section 3)
# ---------------------------------------------------------------------------
SECTIONS: list[tuple[str, str]] = [
    ("study_design", "Methods › Study design and setting"),
    ("sources_1", "Methods › Data sources and units of observation (hospital registers)"),
    ("sources_2", "Methods › Data sources and units of observation (REM)"),
    ("sources_3", "Methods › Data sources and units of observation (surveys and education)"),
    ("official_sources", "Methods › Official sources"),
    ("case_definitions", "Methods › Case definitions and definition variants"),
    ("denominators", "Methods › Denominators and coverage layers"),
    ("statistics", "Methods › Statistical analysis"),
    ("controls", "Methods › Reproducibility controls"),
    ("hospital_1", "Results › Hospital core (annual series)"),
    ("hospital_2", "Results › Hospital core (coding depth and persons)"),
    ("hospital_3", "Results › Hospital core (age, sex and population)"),
    ("hospital_4", "Results › Hospital core (hospitals, co-diagnoses and DEIS)"),
    ("pathway_1", "Results › Aggregate administrative pathway (screening and referral)"),
    ("pathway_2", "Results › Aggregate administrative pathway (A05 entries)"),
    ("pathway_3", "Results › Aggregate administrative pathway (stocks and rehabilitation)"),
    ("benchmarks", "Results › Population benchmarks"),
    ("education", "Results › Educational triangulation"),
    ("territory", "Results › Territory"),
    ("convergence_1", "Results › Convergence across systems (indices)"),
    ("convergence_2", "Results › Convergence across systems (pre-specified models)"),
    ("discussion_3", "Discussion (sex ratio)"),
    ("data_sharing", "Data sharing statement"),
]
SECTION_INDEX = {sid: i for i, (sid, _) in enumerate(SECTIONS)}
SECTION_NAME = dict(SECTIONS)

# ---------------------------------------------------------------------------
# Registry of the appendix: (key, first-citing section), in print order = first-citation order (plan section 4)
# ---------------------------------------------------------------------------
FIGURES: list[tuple[str, str]] = [
    ("fig1_sources_coverage", "sources_2"),            # S1
    ("figE28_variant_sensitivity", "case_definitions"),  # S2
    ("figS10_denominators", "denominators"),           # S3
    ("figS11_coverage_age_sex", "denominators"),       # S4
    ("figE27_model_diagnostics", "statistics"),        # S5
    ("figS15_controls", "controls"),                   # S6
    ("figS2_grd_subcodes", "hospital_1"),              # S7
    ("EF6_readmission_multiplicity", "hospital_2"),    # S8
    ("figS3_grd_hospital_effects", "hospital_4"),      # S9
    ("EF8_hospitals", "hospital_4"),                   # S10
    ("EF5_codiagnoses", "hospital_4"),                 # S11
    ("figS14_deis_sex_age", "hospital_4"),             # S12
    ("EF10_deis_detail", "hospital_4"),                # S13
    ("E12_rem_a03_risk_referral", "pathway_1"),        # S14
    ("E11_rem_a03_codes_by_era", "pathway_1"),         # S15
    ("figS6_rem_stable_panel", "pathway_2"),           # S16
    ("E17_rem_establishment_distribution", "pathway_2"),  # S17
    ("figS7_rem_education_models", "pathway_2"),       # S18
    ("figS8_a05_age_sex", "pathway_2"),                # S19
    ("E19_rem_definition_era_sensitivity", "pathway_2"),  # S20
    ("E15_rem_p2_p6_detail", "pathway_3"),             # S21
    ("figS5_rem_june_december", "pathway_3"),          # S22
    ("figS13_rem_seasonality", "pathway_3"),           # S23
    ("figE22_rem20_capacity", "pathway_3"),            # S24
    ("figE23_surveys_detail", "benchmarks"),           # S25
    ("figE24_education_detail", "education"),          # S26
    ("figS12_junaeb_sex_level", "education"),          # S27
    ("figS9_regional_maps", "territory"),              # S28
    ("E40_maps_grd_smoothed_ratio", "territory"),      # S29
    ("E42_lisa_gistar_maps", "territory"),             # S30
    ("E47_lorenz_theil", "territory"),                 # S31
    ("E49_regional_summary", "territory"),             # S32
    ("E46_sae_deprivation", "territory"),              # S33
    ("figE26_cross_source", "convergence_1"),          # S34
    ("figS4_models_cpa", "convergence_2"),             # S35
    ("figE26b_sex_ratio_multisource", "discussion_3"),  # S36
]

TABLES: list[tuple[str, str]] = (
    [(key, "study_design") for key in PME.TABLE_KEYS]   # S1–S10: the methodological tables inside Part A
    + [(CHECKLIST_KEY, "study_design")]                  # S11: STROBE + RECORD checklist (A8)
    + [
        ("T1_sources", "sources_1"),                     # S12
        ("T_dataflow_counts", "sources_1"),              # S13
        ("ST1_grd_hospital_panel", "sources_1"),         # S14
        ("ST8_grd_identifier_audit", "sources_1"),       # S15
        ("ST2_rem_code_dictionary", "sources_2"),        # S16
        ("S_definition_breaks", "sources_2"),            # S17
        ("ST3_rem_reporting_establishments", "sources_2"),  # S18
        ("ST5_survey_items", "sources_3"),               # S19
        ("ST6_junaeb_items", "sources_3"),               # S20
        ("ST7_provenance", "official_sources"),          # S21
        ("ST7b_manifest_checks", "official_sources"),    # S22
        ("ST10_grd_f84_subcodes", "case_definitions"),   # S23
        ("E28_variant_sensitivity", "case_definitions"),  # S24
        ("T4_denominators_coverage", "denominators"),    # S25
        ("S10_denominator_sensitivity", "denominators"),  # S26
        ("ST12a_fonasa_schema", "denominators"),         # S27
        ("ST12b_isapre_rules", "denominators"),          # S28
        ("ST12c_aps_panel", "denominators"),             # S29
        ("ST4a_comuna_crosswalk_summary", "denominators"),  # S30
        ("ST4b_comuna_unmatched", "denominators"),       # S31
        ("S11_coverage_age_sex", "denominators"),        # S32
        ("E27_model_diagnostics", "statistics"),         # S33
        ("T8_controls_compact", "controls"),             # S34
        ("E79_reproduction_controls_by_family", "controls"),  # S35
        ("E60_grd_annual_full", "hospital_1"),           # S36
        ("T2_grd_core", "hospital_1"),                   # S37
        ("EF6_readmission_multiplicity", "hospital_2"),  # S38
        ("ST9_grd_age_sex", "hospital_3"),               # S39
        ("S_grd_population_rates", "hospital_3"),        # S40
        ("S_hospital_rates_2024", "hospital_4"),         # S41
        ("EF8_hospitals", "hospital_4"),                 # S42
        ("EF5_codiagnoses", "hospital_4"),               # S43
        ("E8_grd_principal_when_secondary", "hospital_4"),  # S44
        ("EF4_severity_weight", "hospital_4"),           # S45 (restored: output of equation 18)
        ("ST11a_deis_annual", "hospital_4"),             # S46
        ("ST11b_deis_vs_grd", "hospital_4"),             # S46
        ("S14_deis_sex_age", "hospital_4"),              # S47
        ("EF10_deis_detail", "hospital_4"),              # S48
        ("T3_rem_pathway", "pathway_1"),                 # S49
        ("E69_rem_code_year_full", "pathway_1"),         # S50
        ("E12_rem_a03_risk_referral", "pathway_1"),      # S51
        ("E11_rem_a03_codes_by_era", "pathway_1"),       # S52
        ("S6_stable_panel", "pathway_2"),                # S53
        ("E17_rem_establishment_distribution", "pathway_2"),  # S54
        ("S_a05_standardised_rates", "pathway_2"),       # S55
        ("ST13_a05_age_sex", "pathway_2"),               # S57
        ("E14_rem_a05_age_sex", "pathway_2"),            # S58 (restored: output of equation 7)
        ("E19_rem_definition_era_sensitivity", "pathway_2"),  # S59
        ("E15_rem_p2_p6_detail", "pathway_3"),           # S58
        ("ST14_p2_p6_june_december", "pathway_3"),       # S59
        ("S13_rem_seasonality", "pathway_3"),            # S62
        ("E1_grd_seasonality", "pathway_3"),             # S63 (restored: output of equation 19 for the GRD)
        ("E22_rem20_capacity", "pathway_3"),             # S64
        ("T5_survey_benchmarks", "benchmarks"),          # S62
        ("E23_surveys_detail", "benchmarks"),            # S63
        ("T6_education", "education"),                   # S64
        ("E24_education_detail", "education"),           # S65
        ("S12_junaeb_sex_level", "education"),           # S66
        ("S9_regional_rates", "territory"),              # S70
        ("E62_grd_region_population_rates", "territory"),  # S71 (restored: region × year, residence)
        ("E13_rem_a05_regional", "territory"),           # S72 (restored: region × year, place of care)
        ("E40_grd_smoothed_ratio_comuna", "territory"),  # S73
        ("E42_local_class_counts", "territory"),         # S69
        ("E51_lisa_significant_comunas", "territory"),   # S70
        ("E43_moran_sensitivity_main", "territory"),     # S71
        ("E50_moran_gistar_all", "territory"),           # S72
        ("E47_inequality_gini_theil", "territory"),      # S73
        ("E49_regional_summary", "territory"),           # S74
        ("E44_correlation_matrix_comuna", "territory"),  # S80
        ("E45_bivariate_moran_pairs", "territory"),      # S81 (restored: output of equation 26)
        ("E48_rank_stability", "territory"),             # S82
        ("E46_sae_association", "territory"),            # S77
        ("E41_rem_comuna_place_of_care", "territory"),   # S78
        ("S_convergence_index", "convergence_1"),        # S79
        ("F4_triangulation_series", "convergence_1"),    # S80
        ("E26_cross_source", "convergence_1"),           # S81
        ("T7_models", "convergence_2"),                  # S82
        ("T7_models_cpa_full", "convergence_2"),         # S83
        ("E26b_sex_ratio_multisource", "discussion_3"),  # S84
        ("E80_tidy_data_dictionary", "data_sharing"),    # S85
    ]
)

SUPP_FIGURES: list[str] = [key for key, _ in FIGURES]
SUPP_TABLES: list[str] = [key for key, _ in TABLES]
PART_A_TABLES: list[str] = list(PME.TABLE_KEYS) + [CHECKLIST_KEY]
FIRST_CITED: dict[str, str] = {**{f"figure:{k}": s for k, s in FIGURES}, **{f"table:{k}": s for k, s in TABLES}}


def _check_registry_order() -> None:
    """S-numbers must ascend with the order in which the article first cites the items (plan section 4)."""
    for kind, items in (("figure", FIGURES), ("table", TABLES)):
        keys = [k for k, _ in items]
        dup = sorted({k for k in keys if keys.count(k) > 1})
        if dup:
            raise RuntimeError(f"duplicate {kind} keys in the appendix registry: {dup}")
        last = -1
        for key, section in items:
            idx = SECTION_INDEX[section]
            if idx < last:
                raise RuntimeError(f"{kind} {key!r} is first cited in {section!r}, earlier than the item before it")
            last = idx


_check_registry_order()


def fig_label(key: str) -> str:
    """'Figure Sn' of an appendix figure (position in SUPP_FIGURES + 1; no registry side effect)."""
    return f"Figure S{SUPP_FIGURES.index(key) + 1}"


def tab_label(key: str) -> str:
    """'Table Sn' of an appendix table (position in SUPP_TABLES + 1)."""
    return f"Table S{SUPP_TABLES.index(key) + 1}"


def mfig_label(key: str) -> str:
    return f"Figure {BODY_FIGURES.index(key) + 1}"


def mtab_label(key: str) -> str:
    return f"Table {BODY_TABLES.index(key) + 1}"


def dropped_items() -> dict:
    """Corpus figures and tables that neither the article nor this appendix prints (keys with corpus titles)."""
    figs = [k for k in SM.FIGURE_ORDER if k not in SUPP_FIGURES and k not in BODY_FIGURES]
    tabs = [k for k in SM.TABLE_ORDER if k not in SUPP_TABLES and k not in BODY_TABLES]
    return dict(figures=figs, tables=tabs)


def _labels() -> tuple[dict, dict, dict]:
    F = {key: fig_label(key) for key in SUPP_FIGURES}
    T = {key: tab_label(key) for key in SUPP_TABLES}
    M = {key: mfig_label(key) for key in BODY_FIGURES} | {key: mtab_label(key) for key in BODY_TABLES}
    return F, T, M


# Groups of Part B (print order). Each group names the first-citing sections it collects; within a group the
# items keep first-citation order, figures before tables, so both S-sequences ascend on the page.
PART_B_GROUPS: list[tuple[str, list[str]]] = [
    ("B1. Data sources, reporting completeness, identifiers and provenance",
     ["sources_1", "sources_2", "sources_3", "official_sources"]),
    ("B2. Case definitions and the full-family variant", ["case_definitions"]),
    ("B3. Denominators and coverage layers", ["denominators"]),
    ("B4. Model diagnostics and reproduction controls", ["statistics", "controls"]),
    ("B5. Hospital episodes with documented F84", ["hospital_1", "hospital_2", "hospital_3", "hospital_4"]),
    ("B6. Aggregate administrative pathway in primary and specialty care (REM)",
     ["pathway_1", "pathway_2", "pathway_3"]),
    ("B7. Population benchmarks and educational triangulation", ["benchmarks", "education"]),
    ("B8. Territory", ["territory"]),
    ("B9. Convergence across systems and the pre-specified models", ["convergence_1", "convergence_2"]),
    ("B10. Sex ratio across sources", ["discussion_3"]),
    ("B11. Data dictionary of the deposited tidy tables", ["data_sharing"]),
]

# ---------------------------------------------------------------------------
# Registry (journal numbering) — journal_config.JournalRegistry when present, else a local twin
# ---------------------------------------------------------------------------
class _LocalRegistry:
    """Same surface as `prose_en._Registry`, numbered by SUPP_FIGURES / SUPP_TABLES of this module."""

    FIG_WORD, TAB_WORD = "Figure", "Table"

    def __init__(self, variant: str = VARIANT, lang: str = LANG):
        self.variant, self.lang = variant, lang
        self.figs: list[str] = []
        self.tabs: list[str] = []
        base = CFG.OUT / variant / lang
        self.fdir, self.tdir = base / "figures", base / "tables"
        self.xfdir, self.xtdir = base / "extra" / "figures", base / "extra" / "tables"
        with open(self.fdir / "captions.json", encoding="utf-8") as fh:
            base_captions = json.load(fh)
        with open(self.xfdir / "captions.json", encoding="utf-8") as fh:
            extra_captions = json.load(fh)
        with open(self.tdir / "titles.json", encoding="utf-8") as fh:
            base_titles = json.load(fh)
        with open(self.xtdir / "titles.json", encoding="utf-8") as fh:
            extra_titles = json.load(fh)
        self.captions = {**extra_captions, **base_captions}
        self.titles = {**extra_titles, **base_titles}
        self._fig_dir = {k: self.xfdir for k in extra_captions} | {k: self.fdir for k in base_captions}
        self._tab_dir = {k: self.xtdir for k in extra_titles} | {k: self.tdir for k in base_titles}

    # -- supplementary items --
    def fig(self, key: str) -> str:
        if key not in SUPP_FIGURES:
            raise KeyError(f"'{key}' is not in the appendix figures (SUPP_FIGURES)")
        if key not in self.figs:
            self.figs.append(key)
        return f"{self.FIG_WORD} S{SUPP_FIGURES.index(key) + 1}"

    def tab(self, key: str) -> str:
        if key not in SUPP_TABLES:
            raise KeyError(f"'{key}' is not in the appendix tables (SUPP_TABLES)")
        if key not in self.tabs:
            self.tabs.append(key)
        return f"{self.TAB_WORD} S{SUPP_TABLES.index(key) + 1}"

    def figp(self, key: str, panels: str) -> str:
        return f"{self.fig(key)}{PE.panel_suffix(self.captions[key].get('caption', ''), panels, key)}"

    # -- body items of the article --
    def mfig(self, key: str) -> str:
        if key not in BODY_FIGURES:
            raise KeyError(f"'{key}' is not a body figure of the journal article")
        return f"{self.FIG_WORD} {BODY_FIGURES.index(key) + 1}"

    def mtab(self, key: str) -> str:
        if key not in BODY_TABLES:
            raise KeyError(f"'{key}' is not a body table of the journal article")
        return f"{self.TAB_WORD} {BODY_TABLES.index(key) + 1}"

    def mfigp(self, key: str, panels: str) -> str:
        return f"{self.mfig(key)}{PE.panel_suffix(self.captions[key].get('caption', ''), panels, key)}"

    # -- blocks --
    def fig_path(self, key: str) -> Path:
        return self._fig_dir[key] / f"{key}.png"

    def tab_path(self, key: str) -> Path:
        return self._tab_dir[key] / f"{key}.csv"

    def figure_block(self, key: str, label: str, body: bool = False):
        meta = self.captions[key]
        caption = f"{PE._strip_prefix(meta.get('title', ''))}. {meta.get('caption', '')}".strip()
        return ("figure", dict(path=self.fig_path(key), caption=caption, label=label))

    def table_block(self, key: str, label: str, rows=None, columns=None):
        if key == CHECKLIST_KEY:
            return checklist_block(self, label)
        meta = self.titles[key]
        df = pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False)
        return ("table", dict(df=df, title=PE._strip_prefix(meta.get("title", "")),
                              note=PE.table_note(key, meta.get("note", ""), df, self.lang), label=label))

    def nrows(self, key: str) -> int:
        if key == CHECKLIST_KEY:
            return len(checklist_table(self))
        return len(pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False))

    def first_citation_order(self) -> list[str]:
        return [f"figure:{k}" for k in self.figs] + [f"table:{k}" for k in self.tabs]


def registry(prefer_journal_config: bool = True):
    """The numbering registry: `journal_config.JournalRegistry` when builder B's module is importable."""
    if prefer_journal_config and _JC is not None and hasattr(_JC, "JournalRegistry"):
        for args in ((), (LANG,), (VARIANT, LANG)):
            try:
                return _JC.JournalRegistry(*args)
            except TypeError:
                continue
    return _LocalRegistry()


# ---------------------------------------------------------------------------
# Cross-reference remap of the corpus captions / notes (fallback of journal_config.remap_refs, plan 7.7)
# ---------------------------------------------------------------------------
REMAP_LOG: list[str] = []
DROPPED_TEXT = "the deposited data"
_XREF_RE = re.compile(r"\b(Figures?|Tables?)\s+(S?)(\d+)([a-z](?:[–-][a-z])?)?\b")


def _journal_label(kind: str, corpus_key: str) -> str | None:
    if kind == "Figure":
        if corpus_key in BODY_FIGURES:
            return f"Figure {BODY_FIGURES.index(corpus_key) + 1}"
        if corpus_key in SUPP_FIGURES:
            return f"Figure S{SUPP_FIGURES.index(corpus_key) + 1}"
    else:
        if corpus_key in BODY_TABLES:
            return f"Table {BODY_TABLES.index(corpus_key) + 1}"
        if corpus_key in SUPP_TABLES:
            return f"Table S{SUPP_TABLES.index(corpus_key) + 1}"
    return None


def _local_remap(text: str) -> str:
    """Rewrite corpus-numbered tokens to the journal numbering; a dropped target becomes `DROPPED_TEXT`."""
    if not text:
        return text

    def sub(m: re.Match) -> str:
        word, supp, num, suffix = m.group(1), m.group(2), int(m.group(3)), m.group(4) or ""
        kind = "Figure" if word.startswith("Figure") else "Table"
        if supp:
            order = SM.FIGURE_ORDER if kind == "Figure" else SM.TABLE_ORDER
        else:
            order = PE.MAIN_FIGURES if kind == "Figure" else PE.MAIN_TABLES
        if not 1 <= num <= len(order):
            REMAP_LOG.append(f"unmapped token {m.group(0)!r}")
            return m.group(0)
        corpus_key = order[num - 1]
        label = _journal_label(kind, corpus_key)
        if label is None:
            REMAP_LOG.append(f"{m.group(0)!r} -> dropped item {corpus_key} -> {DROPPED_TEXT!r}")
            return DROPPED_TEXT
        if word.endswith("s"):
            label = label.replace(kind, kind + "s", 1)
        return label + suffix

    return _XREF_RE.sub(sub, text)


def remap_refs(text: str, lang: str = LANG) -> str:
    """`journal_config.remap_refs` when it exists, else the local remap (identity for lang != 'en')."""
    if lang != LANG:
        return text
    if _JC is not None and hasattr(_JC, "remap_refs"):
        return _JC.remap_refs(text, lang)
    return _local_remap(text)


def _remap_block(block):
    """Remap the corpus cross-references of a figure/table payload ONCE: a payload already flagged
    `refs_remapped` (journal_config.JournalRegistry sets it) is returned untouched."""
    kind, payload = block
    if not isinstance(payload, dict) or payload.get("refs_remapped"):
        return block
    if kind == "figure":
        payload = dict(payload, caption=remap_refs(payload.get("caption", "")), refs_remapped=True)
    elif kind == "table":
        payload = dict(payload, title=remap_refs(payload.get("title", "")), note=remap_refs(payload.get("note", "")),
                       refs_remapped=True)
    return (kind, payload)


# ---------------------------------------------------------------------------
# Values and labels available to the presentation texts
# ---------------------------------------------------------------------------
def _v(V: dict, key: str):
    if key not in V:
        raise KeyError(f"values_{VARIANT}.json lacks the key '{key}' used by supplement_journal.py")
    return V[key]


def _fields(V: dict, R) -> dict:
    """Every number and label the presentation texts may print, each traced to a key or a registry."""
    n0, n1, n2, pct, ppct, nw = PE.n0, PE.n1, PE.n2, PE.pct, PE.ppct, PE.nw
    years_grd = list(range(2019, 2025))
    junaeb_2025 = [_v(V, f"junaeb_{lvl}_mf_ratio_2025") for lvl in ("parvularia", "basico1", "basico5", "medio1")]
    N = dict(
        rett_diff_2024=n0(_v(V, "grd_f84_any_n_rett_only_difference_2024")),
        census_ratio=n2(_v(V, "ine_ratio_censo2024_base2017_2024")),
        fonasa_0_9=ppct(_v(V, "coverage_2025_share_fonasa_ine_age_0_9")),
        disp_grd=n1(_v(V, "apc_grd_any_obs_disp")),
        sec_only=pct(_v(V, "grd_f84_secondary_only_share_2024_pct")),
        epp_2024=n2(_v(V, "grd_episodes_per_person_any_2024")),
        persons_2024=n0(_v(V, "grd_f84_any_persons_2024")),
        n_2024=n0(_v(V, "grd_f84_any_n_2024")),
        fe_above=nw(_v(V, "grd_hosp_rr_fixed_effects_none_n_above1")),
        fe_below=nw(_v(V, "grd_hosp_rr_fixed_effects_none_n_below1")),
        ri_sd=n2(_v(V, "apc_grd_hospital_ri_re_sd")),
        fixed_share_2024=ppct(_v(V, "grd_records_fixed65_share_2024")),
        fixed_panel=n0(_v(V, "grd_fixed_panel_n")),
        hosp_ever=n0(_v(V, "grd_hospitals_ever_observed_n")),
        hosp_series=PE.lst(n0(_v(V, f"grd_hospitals_observed_{y}")) for y in years_grd),
        deis_grd_ratio=n2(_v(V, "deis_vs_grd_ratio_f84_principal_2024")),
        a05_stable_2021=n0(_v(V, "a05_autism_entries_stable_total_2021")),
        a05_stable_2025=n0(_v(V, "a05_autism_entries_stable_total_2025")),
        a05_stable_panel=n0(_v(V, "a05_autism_entries_stable_panel_n")),
        a05_asr_2021=n1(_v(V, "a05_autism_pop_total_asr_2021")),
        a05_asr_2025=n1(_v(V, "a05_autism_pop_total_asr_2025")),
        a05_age09_2025=ppct(_v(V, "a05_autism_entries_share_age_0_9_2025")),
        naneas_2023=pct(_v(V, "p2_tea_share_of_naneas_dec_pct_2023")),
        naneas_2025=pct(_v(V, "p2_tea_share_of_naneas_dec_pct_2025")),
        jun_dec_2020=n2(_v(V, "p2_jun_dec_ratio_2020")),
        pie_strict_2023=pct(_v(V, "pie_tea_strict_share_of_pie_pct_2023")),
        junaeb_mf_min=n1(min(junaeb_2025)),
        junaeb_mf_max=n1(max(junaeb_2025)),
        apc_min=n1(_v(V, "apc_grd_any_sensitivity_min")),
        apc_max=n1(_v(V, "apc_grd_any_sensitivity_max")),
        n_specs=n0(_v(V, "apc_grd_any_sensitivity_n_specs")),
        models_n=n0(_v(V, "models_n_variant")),
        mf_2019=n2(_v(V, "grd_f84_any_mf_ratio_n_2019")),
        mf_2024=n2(_v(V, "grd_f84_any_mf_ratio_n_2024")),
        a05_mf_asr_2025=n2(_v(V, "a05_autism_pop_asr_mf_ratio_2025")),
        t8_rows=n0(_v(V, "t8_rows")), t8_ok=n0(_v(V, "t8_ok")), t8_differs=n0(_v(V, "t8_differs")),
        prov_n=n0(_v(V, "prov_artefacts_n")),
        rem_codes=n0(_v(V, "rem_pathway_codes_n")),
        n_estimators=nw(len(EQ.ESTIMATORS)),
        n_equations=n0(len(EQ.NUMBER)),
        n_sens=n0(len(PME.SENSITIVITY_GRID)),
        rows_T2=n0(R.nrows("T2_grd_core")),
        rows_T3=n0(R.nrows("T3_rem_pathway")),
        rows_T7=n0(R.nrows("T7_models")),
        rows_T7full=n0(R.nrows("T7_models_cpa_full")),
        n_supp_figs=n0(len(SUPP_FIGURES)),
        n_supp_tabs=n0(len(SUPP_TABLES)),
        n_dropped_figs=n0(len(dropped_items()["figures"])),
        n_dropped_tabs=n0(len(dropped_items()["tables"])),
    )
    F, T, M = _labels()
    return dict(N=N, F=F, T=T, M=M)


# ---------------------------------------------------------------------------
# Presentation texts of Part B: what it shows (unit, denominator), why it matters, what it adds beyond the body
# ---------------------------------------------------------------------------
#: The one appendix figure without a corpus presentation sentence (it was a body figure of the working article).
FIGURE_SHOWS_EXTRA: dict[str, str] = {
    "fig1_sources_coverage": (
        "{L} shows, for every REM module and year, the completeness of reporting — reported value, explicit zero "
        "and not reported as three distinct states — together with the denominator and coverage layers, the "
        "establishments reporting each module, the observed and fixed GRD panels, the retention of the REM-20 "
        "panel and the definition breaks. The unit is the establishment × period × code cell for completeness and "
        "the layer or panel for coverage."),
}

FIGURE_ADDS: dict[str, str] = {
    "fig1_sources_coverage": (
        "It matters because the article's rule that zero, missing and not reported are different states can only "
        "be verified when every module-year is seen at once; it adds to the body the complete reporting grid that "
        "{M[fig3_rem_pathway]} summarises with a single count of reporting establishments beside each series."),
    "figE28_variant_sensitivity": (
        "It matters because the article presents only the F84 family excluding Rett syndrome (F84.2): this plate is "
        "where a reader sees that the full-family variant, which is not submitted separately, changes no series "
        "materially — the two variants differ by {N[rett_diff_2024]} GRD episodes in 2024 and the F84.0-only series "
        "is identical in both — and it adds the relative difference of every series, which the body states once in "
        "Methods."),
    "figS10_denominators": (
        "It matters because every population rate of the article rests on the INE base-2017 projections: the plate "
        "shows how the base-2024 projections and the Census 2024 count (ratio of the Census 2024 count to the "
        "base-2017 projection in 2024: {N[census_ratio]}) would move the 2024 rates nationally, by region and by "
        "age, which the body reports as a single sensitivity sentence."),
    "figS11_coverage_age_sex": (
        "It matters because the public network whose registers are analysed covers a selected population: FONASA "
        "covered {N[fonasa_0_9]} of children aged 0–9 years in 2025, and the age structures of FONASA, APS "
        "enrolment and ISAPRE differ. The plate documents the selection that the Discussion names and that no body "
        "figure draws; these are coverage layers, never case denominators."),
    "figE27_model_diagnostics": (
        "It matters because {M[T7_models]} reports quasi-Poisson models: the plate shows the fitted against the "
        "observed values, the residuals, the Pearson dispersion of every specification (the main GRD model has a "
        "dispersion of {N[disp_grd]}) and the Durbin–Watson statistics, which justify the quasi-Poisson family and "
        "the width of the intervals printed in the body."),
    "figS15_controls": (
        "It matters because the Methods state that no reproduction control was completed by plausibility: the plate "
        "is the visual proof, with every difference listed, which the body summarises in one sentence."),
    "figS2_grd_subcodes": (
        "It matters because {N[sec_only]} of the 2024 episodes carried F84 only as a secondary diagnosis: the plate "
        "shows the shift towards F84.0 and towards secondary-only coding behind that figure, the principal share by "
        "subcode and F84.2 by position, none of which {M[fig2_grd_core]} can show at its scale."),
    "EF6_readmission_multiplicity": (
        "It matters because the article counts persons only within each year: the plate shows readmission at 30, 90 "
        "and 365 days by identifier era and the episodes per identifier within the year ({N[epp_2024]} in 2024: "
        "{N[persons_2024]} persons for {N[n_2024]} episodes), so a reader can see that the multiplicity is not an "
        "accumulation across years."),
    "figS3_grd_hospital_effects": (
        "It matters because the Discussion interprets the heterogeneity between hospitals: the plate shows the "
        "hospital fixed effects as rate ratios ({N[fe_above]} hospitals above one and {N[fe_below]} below), the "
        "shrinkage of the random intercepts (standard deviation {N[ri_sd]} on the log scale), the rate against "
        "coding depth and each hospital in 2019 against 2024, which panel (e) of {M[fig2_grd_core]} summarises as "
        "a single ranked chart."),
    "EF8_hospitals": (
        "It matters because hospitals joined the observed panel in 2023 and 2024: the plate ranks the hospitals, "
        "measures the stability of their ranks, the share of the ten largest, the fixed panel against the added "
        "hospitals and the Lorenz curve and Gini coefficient across hospitals; the fixed panel of {N[fixed_panel]} "
        "hospitals still produced {N[fixed_share_2024]} of the 2024 episodes, which is why the added hospitals "
        "contribute little to the trend."),
    "EF5_codiagnoses": (
        "It matters because the body states that most hospital recognition is documentation in episodes admitted "
        "for other reasons: the plate lists the diagnoses recorded together with F84 by ICD-10 chapter and "
        "mental-health block and the principal diagnosis when F84 is secondary, which substantiates that reading."),
    "figS14_deis_sex_age": (
        "It matters as an independent check of the hospital series in all establishments, public and private — by "
        "sex, age and ownership, with masked cells kept as a state — which the body cites in one sentence; the two "
        "registries are not linked by person."),
    "EF10_deis_detail": (
        "It matters because the body compares principal F84 in DEIS with principal F84 in GRD as a coverage "
        "comparison between two unlinked registries of the same event (ratio {N[deis_grd_ratio]} in 2024), never "
        "as a probability; the plate gives the counts and rates, the SNSS, non-SNSS and masked strata and the "
        "subcodes behind that comparison."),
    "E12_rem_a03_risk_referral": (
        "It matters because the screening eras are drawn in separate facets in {M[fig3_rem_pathway]}: the plate "
        "shows the risk composition of M-CHAT-R/F and the referral of high-risk results with Wilson intervals "
        "within each code and year, and the 2024 and 2025 code families, which is why the eras are never joined as "
        "one series."),
    "E11_rem_a03_codes_by_era": (
        "It matters for transparency about the legacy era: every A03 code is shown by era, including the February "
        "2019 outlier, which is kept and flagged rather than removed."),
    "figS6_rem_stable_panel": (
        "It matters because reporting expansion is one of the coincident processes the article names: in the "
        "stable panel of {N[a05_stable_panel]} establishments that reported the code every year, A05 autism "
        "entries rose from {N[a05_stable_2021]} in 2021 to {N[a05_stable_2025]} in 2025, and the plate repeats P2 "
        "and P6 in their stable panels, which the body reports only through the per-establishment models of "
        "{M[T7_models]}."),
    "E17_rem_establishment_distribution": (
        "It matters because a rise in entries can come from many establishments reporting or from a few reporting "
        "more: the plate gives the Lorenz curve, the Gini coefficient and the top-decile share of REM activity "
        "across establishments by year."),
    "figS7_rem_education_models": (
        "It matters because the WHO age-standardised A05 rate rose from {N[a05_asr_2021]} to {N[a05_asr_2025]} per "
        "100,000 residents between 2021 and 2025: the plate shows the crude and standardised rates by sex, the "
        "age-specific rates and the fitted trends of P2, P6 and PIE behind {M[T7_models]}; place-of-care numerators "
        "over residence denominators carry their warning."),
    "figS8_a05_age_sex": (
        "It matters for the sex and age reporting required by SAGER in the outpatient series: entries by age group "
        "and sex and the male:female ratio by age; {N[a05_age09_2025]} of the 2025 entries were in children aged "
        "0–9 years."),
    "E19_rem_definition_era_sensitivity": (
        "It matters because the body attributes part of the change to definition changes: here the reader can see "
        "which part of each series depends on the definition era, which no body figure separates."),
    "E15_rem_p2_p6_detail": (
        "It matters because the stocks are the fastest-growing series: the plate opens P2 by region, December "
        "against June, the stock per reporting establishment, autism as a share of the NANEAS total under control "
        "({N[naneas_2023]} in December 2023 and {N[naneas_2025]} in December 2025) and P6 by era."),
    "figS5_rem_june_december": (
        "It matters because December is the primary cut and June the sensitivity: the plate shows how far the two "
        "cuts agree and the June 2020 collapse of reporting (June stock {N[jun_dec_2020]} of the December stock in "
        "2020), which the body mentions in one sentence."),
    "figS13_rem_seasonality": (
        "It matters because the 2020 fall in the flows is a fall in reporting establishments rather than "
        "necessarily in persons: the monthly index of A05 and A03 shows the reporting profile within each year."),
    "figE22_rem20_capacity": (
        "It matters as context that the body does not draw: REM-20 discharges and bed-days, the retention of the "
        "REM-20 panel and the ecological association, by establishment, with the hospital series."),
    "figE23_surveys_detail": (
        "It matters because the survey benchmarks of the body are printed only for reliable domains: the plate "
        "gives every domain with its design effect, relative standard error and case threshold and greys the "
        "unreliable ones, which explains why most sex and age domains are not reported as point estimates."),
    "figE24_education_detail": (
        "It matters because the educational register is the external system closest to a person-level count: the "
        "plate opens PIE by definition and source, declares the 2022 discrepancy, gives the shares (strict autism "
        "was {N[pie_strict_2023]} of PIE registrations in 2023), the special schools, the 2023 sex split and the "
        "exceptional-entry rule that {M[fig4_triangulation]} summarises in one panel."),
    "figS12_junaeb_sex_level": (
        "It matters for SAGER in the school cohorts: caregiver-reported autism by sex and level, with a "
        "male:female ratio between {N[junaeb_mf_min]} and {N[junaeb_mf_max]} across the levels of 2025, weighted "
        "and unweighted where a weight is published."),
    "figS9_regional_maps": (
        "It matters because the journal asks for equal-area projections and the article prints no map: the Albers "
        "equal-area regional maps show GRD 2024 by region of residence and A05 by region of the reporting "
        "establishment, with the warning that these are not the same geography."),
    "E40_maps_grd_smoothed_ratio": (
        "It matters because the Territory paragraph reports a global Moran's I: the comuna maps of the "
        "standardised ratio, its empirical-Bayes smoothed version and the suppressed cells show the territorial "
        "pattern behind that statistic."),
    "E42_lisa_gistar_maps": (
        "It matters because the Territory paragraph counts the local clusters: the plate locates the LISA classes "
        "and the Gi* hot and cold spots after Benjamini–Hochberg control."),
    "E47_lorenz_theil": (
        "It matters because the Territory paragraph states that inequality across comunas fell as recognition "
        "spread: the plate gives the Lorenz curves, the Gini coefficient and the Theil decomposition by year."),
    "E49_regional_summary": (
        "It matters because the Territory paragraph is written at comuna level: the plate gives the regional "
        "reading of the same statistics — rates, standardised ratios and ranks."),
    "E46_sae_deprivation": (
        "It matters as context of supply and deprivation, which the article does not analyse: the plate is the only "
        "place where recognition is set against a deprivation measure."),
    "figE26_cross_source": (
        "It matters because the convergence claim of the body is drawn as indices in {M[fig4_triangulation]}: here "
        "the same series are also read as raw values, as population rates and per reporting unit, so the "
        "per-reporting-unit reading is visible."),
    "figS4_models_cpa": (
        "It matters because {M[T7_models]} prints numbers: the plate is their visual form — observed and fitted "
        "series, forests of the annual percent change across the {N[n_specs]} GRD specifications (range "
        "{N[apc_min]}–{N[apc_max]}%), standardised rates and indices — with every interval."),
    "figE26b_sex_ratio_multisource": (
        "It matters as the SAGER synthesis of the Discussion: the male:female ratio in every source that reports "
        "sex, as a trend, by age, as counts against standardised rates and as a forest in both variants (GRD "
        "episodes fell from {N[mf_2019]} in 2019 to {N[mf_2024]} in 2024; WHO-standardised A05 rates "
        "{N[a05_mf_asr_2025]} in 2025)."),
}

TABLE_INTROS: dict[str, str] = {
    "T1_sources": (
        "{L} is the inventory of the sources: provider, unit of observation, period, coverage, geography, stock or "
        "flow, denominator, definition breaks, linkage and files. It adds to the Methods the row-by-row statement "
        "that no source is linked at the person level."),
    "T_dataflow_counts": (
        "{L} lists every count printed on {M[fig1_dataflow]} with its unit, source, column and whether it is drawn, "
        "together with the exclusions; its note carries the description of how the figure is drawn and the files "
        "it reads. It is the audit of the figure."),
    "ST1_grd_hospital_panel": (
        "{L} lists the {N[hosp_ever]} hospitals ever observed, year by year, and their membership of the fixed "
        "panel of {N[fixed_panel]}; the observed panel is {N[hosp_series]} hospitals in 2019 to 2024."),
    "ST8_grd_identifier_audit": (
        "{L} audits the person identifier of the GRD files: validity, uniqueness, the format change between 2020 "
        "and 2021 and the absence of shared identifiers across it, which is why persons are counted only within "
        "each year."),
    "ST2_rem_code_dictionary": (
        "{L} lists the {N[rem_codes]} REM codes of the pathway, each verified against the dictionary of every "
        "year: the complete code list that RECORD asks for."),
    "S_definition_breaks": (
        "{L} gives one row per definition break of every source with its date and consequence, which is why eras "
        "are drawn in separate facets and never joined by a line."),
    "ST3_rem_reporting_establishments": (
        "{L} gives the establishments reporting each code in each year and the stable panel: the denominator that "
        "accompanies every REM count in the article."),
    "ST5_survey_items": (
        "{L} reproduces verbatim the ENDIDE 2022 and ENCAVI 2023–24 questions from which autism was identified, "
        "with the design variables; autism is taken as reported by the respondent or caregiver and no disability "
        "is inferred from a diagnosis."),
    "ST6_junaeb_items": (
        "{L} gives the JUNAEB item, filter, weight and estimability by cohort and year, including the level and "
        "year that are not estimable."),
    "ST7_provenance": (
        "{L} lists the {N[prov_n]} artefacts read by the pipeline with their SHA-256 hash, date and use: the frozen "
        "provenance behind every count."),
    "ST7b_manifest_checks": "{L} records the agreement between the downloaded files and their manifests.",
    "ST10_grd_f84_subcodes": (
        "{L} gives the F84 subcodes by year and diagnostic position, with F84.2 flagged, so that both "
        "case-definition variants can be reconstructed from it."),
    "E28_variant_sensitivity": (
        "{L} carries the values drawn in {F[figE28_variant_sensitivity]}: every series in both variants with the "
        "absolute difference in cases and the relative difference; it adds the exact counts that the plate can only "
        "show as bars."),
    "T4_denominators_coverage": (
        "{L} gives the denominator and coverage layers by year with their retention; it was a body table of the "
        "working manuscript and is the source of the coverage figures quoted in Results."),
    "S10_denominator_sensitivity": (
        "{L} carries the values drawn in {F[figS10_denominators]}: the INE base-2017, base-2024 (30 June and 1 "
        "January) and Census 2024 populations by year with their ratios to the primary denominator; it adds the "
        "ratios themselves, which the body quotes once."),
    "ST12a_fonasa_schema": (
        "{L} documents the schema breaks of the FONASA beneficiary files and the harmonisation rules applied."),
    "ST12b_isapre_rules": "{L} documents the rules applied to the ISAPRE files.",
    "ST12c_aps_panel": "{L} documents the panel of APS enrolment files by year.",
    "ST4a_comuna_crosswalk_summary": "{L} summarises the audit of the comuna crosswalk between sources and years.",
    "ST4b_comuna_unmatched": "{L} lists the comuna codes left unmatched by the crosswalk and how they were treated.",
    "S11_coverage_age_sex": (
        "{L} carries the values drawn in {F[figS11_coverage_age_sex]}: FONASA, APS and ISAPRE beneficiaries by age "
        "band and sex in 2025 with their shares of the INE population; it adds the cells from which the coverage "
        "percentages of the Discussion are read."),
    "E27_model_diagnostics": (
        "{L} gives the main specification of each estimand with its diagnostics (dispersion, residual "
        "autocorrelation and influence); it accompanies {F[figE27_model_diagnostics]}."),
    "T8_controls_compact": (
        "{L} is the compact table of the pre-specified reproduction controls of the analysis plan: {N[t8_rows]} "
        "indicator-year controls, of which {N[t8_ok]} matched and {N[t8_differs]} carry a documented difference; "
        "it was a body table of the working manuscript."),
    "E79_reproduction_controls_by_family": (
        "{L} lists the control files of the whole pipeline by family with the table's own totals row; this scope "
        "is the numeric module control and is never added to the indicator-year controls of "
        "{T[T8_controls_compact]}."),
    "E60_grd_annual_full": (
        "{L} is the complete annual GRD series by panel, activity and diagnostic position, from which "
        "{M[T2_grd_core]} and {M[fig2_grd_core]} are drawn."),
    "T2_grd_core": (
        "{L} is the unmodified full hospital core table ({N[rows_T2]} rows) of which {M[T2_grd_core]} prints a "
        "selection; the two coding-depth rows reported as mean (median) are here."),
    "EF6_readmission_multiplicity": (
        "{L} carries the values drawn in {F[EF6_readmission_multiplicity]}: all-cause and F84 readmission at 30, 90 "
        "and 365 days by year with Wilson intervals, and the multiplicity of episodes per identifier by era; it adds "
        "the 'n/e' cells of the years whose horizon leaves too few eligible discharges."),
    "ST9_grd_age_sex": "{L} gives the age–sex cells of the GRD series (SAGER).",
    "S_grd_population_rates": (
        "{L} gives the crude and WHO age-standardised rates per 100,000 residents by sex with Fay–Feuer limits: "
        "the population reading of the hospital series, with place-of-care numerators over residence "
        "denominators and the warning that goes with them."),
    "S_hospital_rates_2024": (
        "{L} lists the {N[hosp_ever]} hospitals with their 2024 rate, exact interval and fixed-effect rate ratio: "
        "the values ranked in panel (e) of {M[fig2_grd_core]}."),
    "EF8_hospitals": (
        "{L} carries the values drawn in {F[EF8_hospitals]}: the 25 hospitals with most episodes with F84 by year, "
        "the rank correlations, the concentration measures and the fixed against the added panel; it adds the "
        "abbreviated hospital names and the counts behind each rate."),
    "EF5_codiagnoses": (
        "{L} carries the values drawn in {F[EF5_codiagnoses]}: the three-character ICD-10 categories recorded with "
        "F84 by year, as episodes and as percentages of the episodes with F84; it adds the pooled 2019–2024 column."),
    "E8_grd_principal_when_secondary": (
        "{L} gives the principal diagnosis of the episodes in which F84 is secondary: the direct answer to the "
        "{N[sec_only]} of 2024 episodes that carried F84 only as a secondary diagnosis."),
    "EF4_severity_weight": (
        "{L} gives, by year, the severity and mortality-risk classes of the episodes with documented F84, the "
        "IR-29301 relative weight as median (P25–P75) and mean (SD), and in-hospital lethality as deaths per "
        "episodes with the Jeffreys interval of equation 18. It is printed because the methodology describes that "
        "estimator; it adds the clinical profile of episodes that the body describes only as admitted for other "
        "reasons, and lethality is a property of the episode, never of autism."),
    "ST11a_deis_annual": "{L} gives the DEIS totals by year, the SNSS share, the masked cells and F84 by position.",
    "ST11b_deis_vs_grd": (
        "{L} compares principal F84 in DEIS with principal F84 in GRD year by year as a coverage comparison "
        "between two unlinked registries of the same event, with its non-probability note; the any-position to "
        "principal ratio is not printed."),
    "S14_deis_sex_age": (
        "{L} carries the values drawn in {F[figS14_deis_sex_age]}: DEIS discharges and principal-F84 discharges by "
        "year, sex and age band with rates per 100,000 discharges and their limits; it adds the exact counts of "
        "every cell."),
    "EF10_deis_detail": (
        "{L} carries the values drawn in {F[EF10_deis_detail]}: principal-F84 discharges in all establishments, in "
        "the SNSS, outside it and masked by DEIS, and by sex, year by year; it adds the masked stratum as a state "
        "of its own."),
    "T3_rem_pathway": (
        "{L} is the REM pathway table ({N[rows_T3]} rows) by module, code, era and reporting establishments: the "
        "values drawn in {M[fig3_rem_pathway]}; it was a body table of the working manuscript."),
    "E69_rem_code_year_full": (
        "{L} is the complete code × year table with reporting establishments and stable-panel totals."),
    "E12_rem_a03_risk_referral": (
        "{L} carries the values drawn in {F[E12_rem_a03_risk_referral]}: every M-CHAT-R/F risk and referral code "
        "with its definition era and its 2023–2025 counts; it adds the code-level counts that the plate draws as "
        "proportions."),
    "E11_rem_a03_codes_by_era": (
        "{L} carries the values drawn in {F[E11_rem_a03_codes_by_era]}: every A03 code by definition era and year "
        "2019–2024, including the February 2019 outlier kept and flagged; it adds the code-level series behind the "
        "eras."),
    "S6_stable_panel": (
        "{L} carries the values drawn in {F[figS6_rem_stable_panel]}: A05, P2 and P6 by year in all reporting "
        "establishments and in the stable panel, with both panel sizes; it adds the establishment counts behind "
        "the per-establishment models of {M[T7_models]}."),
    "E17_rem_establishment_distribution": (
        "{L} carries the values drawn in {F[E17_rem_establishment_distribution]}: the concentration measures of REM "
        "activity across establishments by series and year; it adds the values the plate draws as curves."),
    "S_a05_standardised_rates": (
        "{L} gives the crude and WHO age-standardised A05 rates by sex and year with their limits."),
    "ST13_a05_age_sex": "{L} gives the A05 entries by age, sex, category and year with reporting establishments.",
    "E14_rem_a05_age_sex": (
        "{L} gives the A05 strict-autism entries by five-year age group and sex, 2021–2025, with the standardised "
        "rates and the male-to-female ratio whose interval is the exact binomial count ratio of equation 7: the "
        "numeric companion of {F[figS8_a05_age_sex]}, which {T[ST13_a05_age_sex]} summarises by broad age band."),
    "E19_rem_definition_era_sensitivity": (
        "{L} carries the values drawn in {F[E19_rem_definition_era_sensitivity]}: every REM series by code and "
        "definition era, 2019–2024; it adds the counts under each definition, which the body attributes to "
        "definition changes in one clause."),
    "E15_rem_p2_p6_detail": (
        "{L} carries the values drawn in {F[E15_rem_p2_p6_detail]}: P2 and P6 by code, measure and year, including "
        "the broad pre-2021 codes as a labelled sensitivity; it adds the December and June values as separate rows, "
        "never summed."),
    "ST14_p2_p6_june_december": (
        "{L} gives the December and June stocks of P2 and P6 with reporting establishments and the stable panel; "
        "the two cuts are never summed."),
    "S13_rem_seasonality": (
        "{L} carries the values drawn in {F[figS13_rem_seasonality]}: the monthly totals of A05 and A03 by year with "
        "the establishments reporting in the month and in the year and the index (annual mean = 100), with 'not "
        "reported' and 'not estimable' kept as distinct states; it adds the monthly establishment counts, which are "
        "what shows the 2020 fall to be one of reporting."),
    "E1_grd_seasonality": (
        "{L} gives the GRD episodes with documented F84 by month of admission and year with the within-year "
        "seasonal index of equation 19 (annual mean = 1), the hospital counterpart of the REM index of "
        "{F[figS13_rem_seasonality]}; it adds the monthly profile of the hospital counts, which no body figure "
        "draws."),
    "E22_rem20_capacity": (
        "{L} carries the values drawn in {F[figE22_rem20_capacity]}: REM-20 discharges, bed-days, occupancy and "
        "discharges per establishment by year; it adds the panel of 188 establishments as a separate column. These "
        "are context and never a denominator."),
    "T5_survey_benchmarks": (
        "{L} gives the survey estimates by domain with the design, the design effect, the relative standard error "
        "and the precision flags; it was a body table of the working manuscript and is the source of the "
        "benchmarks quoted in Results."),
    "E23_surveys_detail": (
        "{L} carries the values drawn in {F[figE23_surveys_detail]}: every survey domain with n, cases, weighted "
        "percentage and interval, weighted total, design effect and relative standard error; it adds the case "
        "counts behind the domains greyed on the plate."),
    "T6_education": (
        "{L} gives the PIE series by definition and source, SINACES, the special schools and JUNAEB; it was a body "
        "table of the working manuscript."),
    "E24_education_detail": (
        "{L} carries the values drawn in {F[figE24_education_detail]}: PIE registrations by definition and source, "
        "special schools, regular and exceptional entry and the share of PIE enrolment by year; it adds the "
        "exceptional-entry counts that the plate does not print."),
    "S12_junaeb_sex_level": (
        "{L} carries the values drawn in {F[figS12_junaeb_sex_level]}: students with a response and reported ASD "
        "by year, level and sex, unweighted and weighted percentages with intervals, the estimator and whether the "
        "cell is estimable; it adds the case counts behind every percentage."),
    "S9_regional_rates": (
        "{L} gives the regional rates of 2024 by residence (GRD) and by place of care (A05), which are not the "
        "same geography."),
    "E62_grd_region_population_rates": (
        "{L} gives the GRD episodes with documented F84 by declared region of residence and year with rates per "
        "100,000 regional residents and exact Poisson intervals; numerator and denominator share the residence "
        "definition, so it is the regional table read without the place-of-care warning. It adds the region × year "
        "reading, which {T[S9_regional_rates]} gives for 2024 only."),
    "E13_rem_a05_regional": (
        "{L} gives the A05 strict-autism entries by region of the reporting establishment and year, 2021–2025, "
        "with the establishments reporting in each region and year in brackets and the share contributed by the "
        "stable panel: the place-of-care companion of {T[E62_grd_region_population_rates]}, never divided by it."),
    "E40_grd_smoothed_ratio_comuna": (
        "{L} gives the comuna standardised ratios and their empirical-Bayes smoothed values."),
    "E42_local_class_counts": (
        "{L} counts the LISA and Gi* classes after Benjamini–Hochberg control: the source of the cluster counts "
        "of the Territory paragraph."),
    "E51_lisa_significant_comunas": "{L} names the comunas with a significant local statistic.",
    "E43_moran_sensitivity_main": (
        "{L} gives Moran's I across the weight matrices and value types: the sensitivity behind the range quoted "
        "in the Territory paragraph."),
    "E50_moran_gistar_all": "{L} gives the global and local statistics for every territorial indicator.",
    "E47_inequality_gini_theil": (
        "{L} gives the Gini and Theil indices by year: the source of the fall in territorial inequality reported "
        "in the Territory paragraph."),
    "E49_regional_summary": (
        "{L} carries the values drawn in {F[E49_regional_summary]}: observed and expected counts, rates and crude "
        "and smoothed standardised ratios by region and indicator; it adds the expected counts of the indirect "
        "standardisation."),
    "E44_correlation_matrix_comuna": (
        "{L} gives the rank correlations between the territorial indicators of the different systems by comuna, "
        "with the warning that they are ecological associations between sources that are not person-linked."),
    "E45_bivariate_moran_pairs": (
        "{L} gives the bivariate Moran's I of every pair of territorial indicators (the value of one indicator "
        "against the spatial lag of the other, queen contiguity, 999 permutations) with its z value, permutation p "
        "and Spearman's rho, the output of equation 26. It describes the spatial co-location of two unlinked "
        "systems and implies neither a direction nor a linkage; it is printed because the methodology describes the "
        "estimator, not because any pair is interpreted in the article."),
    "E48_rank_stability": "{L} gives the stability of the comuna ranks across years.",
    "E46_sae_association": (
        "{L} carries the values drawn in {F[E46_sae_deprivation]}: the association of each territorial indicator "
        "with comuna multidimensional poverty, income poverty and urban population; it adds the coefficients the "
        "plate draws, with the warning glyph (†) on the place-of-care indicators."),
    "E41_rem_comuna_place_of_care": (
        "{L} gives the REM comuna values by place of care: the companion of the residence versus place-of-care "
        "warning."),
    "S_convergence_index": (
        "{L} gives the indices of every system with 2021 = 100 and 2019 = 100, declared as indices and not as "
        "rates."),
    "F4_triangulation_series": (
        "{L} carries the values drawn in panel (e) of {M[fig4_triangulation]}: each series by year with its value, "
        "unit, reporting N, denominator and rate per 100,000 residents with its interval; it adds the exact rates "
        "behind the strips."),
    "E26_cross_source": (
        "{L} carries the values drawn in {F[figE26_cross_source]}: the five systems side by side by year in their "
        "own units; it adds the raw values that the plate reads as indices."),
    "T7_models": (
        "{L} is the full table of the pre-specified models ({N[rows_T7]} rows) of which "
        "{M[T7_models]} prints a selection; every cell is the output file's except the p value, which is printed to "
        "two significant figures from the raw model output as in {M[T7_models]}; the estimand is the internal "
        "heading of each group of rows and the notes of the output file are the lettered footnotes under the table."),
    "T7_models_cpa_full": (
        "{L} lists every model specification fitted for this variant, {N[models_n]} in all, with its estimand "
        "(the internal heading of each group of rows), offset, covariates, years, APC, interval, p value (two "
        "significant figures from the raw output) and dispersion; the notes of the output file are the lettered "
        "footnotes under the table, and the running number identifies the row across the parts of the table."),
    "E26b_sex_ratio_multisource": (
        "{L} gives the male:female ratios with their intervals for every source: the values of "
        "{F[figE26b_sex_ratio_multisource]}."),
    "E80_tidy_data_dictionary": (
        "{L} is the data dictionary of the tidy tables deposited under the data sharing statement."),
}


def figure_intro(key: str, label: str, fields: dict) -> str:
    """Presentation paragraph of an appendix figure: what it shows (corpus sentence), why it matters, what it adds."""
    if key in FIGURE_SHOWS_EXTRA:
        shows = FIGURE_SHOWS_EXTRA[key].format(L=label)
    else:
        shows = SM.figure_intro(key, label, LANG)
    adds = FIGURE_ADDS[key].format(**fields)
    return f"{shows} {adds}"


def table_intro(key: str, label: str, fields: dict) -> str:
    return TABLE_INTROS[key].format(L=label, **fields)


# ---------------------------------------------------------------------------
# A8 — STROBE + RECORD checklist (Table S11)
# ---------------------------------------------------------------------------
_STATUS_REPORTED = "Reported"
_STATUS_LIMITATION = "Reported as a limitation"
_STATUS_NA = "Not applicable"
_STATUS_AUTHOR = "Reported in structure; content author-supplied"

_STROBE: list[tuple[str, str, str, str]] = [
    ("STROBE 1", "Title and abstract: indicate the study's design; provide an informative summary",
     "Title ('national multisource surveillance study'; 'administrative recognition' names the type of data); "
     "Summary (Background, Methods, Findings, Interpretation, Funding)", _STATUS_REPORTED),
    ("STROBE 2", "Background/rationale: scientific background and rationale", "Introduction", _STATUS_REPORTED),
    ("STROBE 3", "Objectives: specific objectives, including any pre-specified hypotheses",
     "Introduction (final paragraph); Methods › Study design and setting; appendix Part A, M1; appendix A9 "
     "(pre-specified analysis plan)", _STATUS_REPORTED),
    ("STROBE 4", "Study design: key elements of the design",
     "Methods › Study design and setting; appendix Part A, M1", _STATUS_REPORTED),
    ("STROBE 5", "Setting: locations, dates and periods of data collection",
     "Methods › Study design and setting; Methods › Data sources and units of observation (Chile, public network, "
     "2019–2024 for GRD and DEIS, 2019–2025 for REM and education); {T[T1_sources]}", _STATUS_REPORTED),
    ("STROBE 6", "Participants: eligibility criteria, sources and methods of selection",
     "Methods › Data sources and units of observation; Methods › Case definitions and definition variants; "
     "{M[fig1_dataflow]} (lane by lane: the unit of the row, n at entry, n after the autism selection and the "
     "exclusions with their reason); {T[T1_sources]} (unit of observation by source; census of records, no "
     "individual recruitment); {T[T_dataflow_counts]}", _STATUS_REPORTED),
    ("STROBE 7", "Variables: outcomes, exposures, covariates and diagnostic criteria",
     "Methods › Case definitions and definition variants; Methods › Denominators and coverage layers; appendix "
     "Part A, M2–M3 and {N[range_M2_M4]}; {T[E80_tidy_data_dictionary]}",
     _STATUS_REPORTED),
    ("STROBE 8", "Data sources and measurement: source and method of assessment for each variable; comparability",
     "Methods › Data sources and units of observation; {T[T1_sources]}; {T[ST7_provenance]} and "
     "{T[ST7b_manifest_checks]} (provenance with SHA-256 and manifest checks); {T[S_definition_breaks]}; "
     "{T[ST2_rem_code_dictionary]}", _STATUS_REPORTED),
    ("STROBE 9", "Bias: efforts to address potential sources of bias",
     "Methods › Statistical analysis (fixed versus observed panel, coding depth, definition eras, stable REM "
     "panel, June versus December); appendix Part A, M5 and {T[M6_sensitivity_grid]}; Discussion (limitations)",
     _STATUS_REPORTED),
    ("STROBE 10", "Study size: how the study size was arrived at",
     "Methods › Study design and setting (census of every public record; no sampling); Results › Sources and "
     "coverage; {M[fig1_dataflow]} and {T[T_dataflow_counts]} (records read per source)", _STATUS_REPORTED),
    ("STROBE 11", "Quantitative variables: handling and groupings",
     "Methods › Statistical analysis (age groups, coding-depth strata, eras); appendix Part A, M3–M4",
     _STATUS_REPORTED),
    ("STROBE 12", "Statistical methods: all methods, subgroups, missing data and sensitivity analyses",
     "Methods › Statistical analysis; Methods › Reproducibility controls; appendix Part A, M4 (the "
     "{N[n_estimators]} estimators with equations 1–{N[n_equations]}, assumptions, implementation, script and "
     "output file; {T[M5_estimator_map]}); {M[T7_models]}; {T[T7_models_cpa_full]}", _STATUS_REPORTED),
    ("STROBE 13", "Participants: numbers at each stage; flow diagram",
     "{M[fig1_dataflow]}: per lane, the unit of the row (record, person or comuna), n at entry, n after the "
     "autism selection and the exclusions with their n; there is no flow of individuals because there is no "
     "recruitment and no person-level linkage, which the dashed band of the figure states once. "
     "{T[T_dataflow_counts]} carries the counts; Results › Sources and coverage; {T[T1_sources]}",
     _STATUS_REPORTED),
    ("STROBE 14", "Descriptive data: characteristics and missing data by variable",
     "Results (every subsection); {M[T2_grd_core]}; {F[fig1_sources_coverage]} (explicit zero, missing and not "
     "reported as distinct states); {T[M7_data_states]}; {T[T3_rem_pathway]} (reporting establishments beside "
     "every REM count)", _STATUS_REPORTED),
    ("STROBE 15", "Outcome data: numbers of events or summary measures",
     "Results › Hospital core; Results › Aggregate administrative pathway; Results › Educational triangulation; "
     "{M[T2_grd_core]}; {T[E60_grd_annual_full]}; {T[T3_rem_pathway]}; {T[T6_education]}", _STATUS_REPORTED),
    ("STROBE 16", "Main results: unadjusted and adjusted estimates with precision; category boundaries",
     "Results › Hospital core (rates with exact limits; APC with 95% CI); Results › Convergence across systems "
     "and sensitivity of the trends; {M[T7_models]}; {T[T7_models]}; {T[T7_models_cpa_full]}", _STATUS_REPORTED),
    ("STROBE 17", "Other analyses: subgroups, interactions and sensitivity analyses",
     "Results › Convergence across systems and sensitivity of the trends; appendix Part B ({N[range_figs]} and "
     "{N[range_tabs_B]}: hospital episodes in detail, REM pathway by era, denominators, surveys and education, sex "
     "ratio across sources, model diagnostics, spatial analysis)", _STATUS_REPORTED),
    ("STROBE 18", "Key results with reference to the objectives", "Discussion (first paragraph)", _STATUS_REPORTED),
    ("STROBE 19", "Limitations: sources of bias or imprecision, direction and magnitude",
     "Discussion (limitations paragraph: pandemic, taxonomy, coverage, geography, coding depth, absence of "
     "linkage, access bias); appendix Part A, M7", _STATUS_REPORTED),
    ("STROBE 20", "Interpretation: cautious overall interpretation considering multiplicity and similar studies",
     "Discussion (recognition, demand and epidemiology kept apart; comparison with international registers; "
     "non-separability of the coincident processes); Conclusion", _STATUS_REPORTED),
    ("STROBE 21", "Generalisability: external validity",
     "Discussion (universal and segmented systems of Latin America; public network, not ISAPRE)",
     _STATUS_REPORTED),
    ("STROBE 22", "Funding: source of funding and role of the funders",
     "Funding; Methods › Role of the funding source", _STATUS_AUTHOR),
]

_RECORD: list[tuple[str, str, str, str]] = [
    ("RECORD 1.1", "Type of data used should be specified in the title or abstract",
     "Title ('administrative recognition', 'multisource'); Summary › Methods ('unlinked routine data')",
     _STATUS_REPORTED),
    ("RECORD 1.2", "Names of the databases used should be included in the title or abstract",
     "Summary › Methods (GRD, DEIS, REM, surveys, school registers); Methods › Data sources and units of "
     "observation; {T[T1_sources]}", _STATUS_REPORTED),
    ("RECORD 1.3", "Linkage between databases should be stated in the title or abstract",
     "Summary › Methods ('unlinked'); Methods › Data sources and units of observation (no person-level linkage); "
     "{M[fig1_dataflow]}", _STATUS_REPORTED),
    ("RECORD 6.1", "Methods of study population selection (codes or algorithms) should be listed in detail",
     "Methods › Case definitions and definition variants; appendix Part A, M2, {T[M2_case_definitions]} and "
     "{T[M3_rem_code_sets]}; {T[ST2_rem_code_dictionary]} (dictionary verified by year); "
     "{T[ST10_grd_f84_subcodes]}", _STATUS_REPORTED),
    ("RECORD 6.2", "Any validation studies of the codes or algorithms should be referenced",
     "Discussion (no clinical validation; ENDIDE and ENCAVI are benchmarks of reported autism, not a validation); "
     "Results › Population benchmarks", _STATUS_LIMITATION),
    ("RECORD 6.3", "If linkage was used, the linkage process and its quality should be described, with a diagram",
     "Methods › Data sources and units of observation (no person-level linkage); {M[fig1_dataflow]} (the dashed "
     "band states once that no record is linked across systems); {T[ST8_grd_identifier_audit]} (identifier "
     "format change between 2020 and 2021, no shared identifiers across it); {T[T1_sources]}; "
     "{T[M1_sources_units]}", _STATUS_REPORTED),
    ("RECORD 7.1", "A complete list of codes and algorithms used to classify exposures, outcomes and covariates",
     "appendix Part A, M2, {T[M2_case_definitions]} and {T[M3_rem_code_sets]}; {T[ST2_rem_code_dictionary]}; "
     "{T[S_definition_breaks]}", _STATUS_REPORTED),
    ("RECORD 12.1", "Data cleaning methods should be described",
     "Methods › Reproducibility controls; {T[T8_controls_compact]}; {T[E79_reproduction_controls_by_family]}; "
     "{T[M10_reproduction_controls]}; {T[ST8_grd_identifier_audit]}; {F[figS15_controls]}", _STATUS_REPORTED),
    ("RECORD 12.2", "Linkage: quality evaluation of the linkage process",
     "No person-level linkage was performed (Methods › Data sources and units of observation; {M[fig1_dataflow]}; "
     "{T[T1_sources]})", _STATUS_NA),
    ("RECORD 12.3", "Handling of missing data",
     "Methods › Data sources and units of observation (missing, explicit zero and not reported are distinct "
     "states; 2020 as a reporting disruption, no interpolation); {F[fig1_sources_coverage]}; "
     "{T[M7_data_states]}; {T[T3_rem_pathway]} (reporting establishments)", _STATUS_REPORTED),
    ("RECORD 13.1", "Selection of included persons: detailed diagram",
     "{M[fig1_dataflow]}; {T[T_dataflow_counts]}; {T[T1_sources]}; {T[ST1_grd_hospital_panel]}; "
     "{T[ST3_rem_reporting_establishments]}", _STATUS_REPORTED),
    ("RECORD 19.1", "Limitations of using data that were created or collected for other purposes",
     "Discussion; appendix Part A, M7", _STATUS_REPORTED),
    ("RECORD 22.1", "Access to the data, code and protocol",
     "Data sharing statement; {T[ST7_provenance]}; appendix A9 (the analysis plan as protocol); appendix Part A, "
     "M6 ({T[M8_pipeline_map]} and {T[M9_software_seeds]})", _STATUS_AUTHOR),
]

CHECKLIST_TITLE = ("STROBE and RECORD checklist of the article, with the section, figure or table where each item "
                   "is reported")
CHECKLIST_NOTE = ("STROBE: Strengthening the Reporting of Observational Studies in Epidemiology (22 items); RECORD: "
                  "REporting of studies Conducted using Observational Routinely-collected health Data (13 items). "
                  "'Where reported' names the sections of the journal article and the figures and tables of the "
                  "article and of this appendix. 'Reported in structure; content author-supplied' marks the two "
                  "items whose wording (funding source; repository URL and DOI) the author team completes at "
                  "submission. No person-level linkage was performed, so the linkage items are reported as not "
                  "applicable.")


def _range_label(first: str, last: str) -> str:
    """'Table S2' + 'Table S4' -> 'Tables S2–S4' (the plural form of a contiguous range of labels)."""
    word, a = first.split()
    b = last.split()[-1]
    return f"{SM._PLURAL.get(word, word)} {a}–{b}"


def checklist_table(R=None) -> pd.DataFrame:
    """STROBE (22) + RECORD (13) checklist in English, 'Where reported' mapped to the journal numbering.

    `R` is accepted for the contract's surface (labels are positions in the registry lists, so no registry call
    is needed and a shared registry is never marked as having cited every item)."""
    F, T, M = _labels()
    N = dict(n_estimators=PE.nw(len(EQ.ESTIMATORS)), n_equations=PE.n0(len(EQ.NUMBER)),
             range_M2_M4=_range_label(T["M2_case_definitions"], T["M4_denominator_layers"]),
             range_figs=_range_label(F[SUPP_FIGURES[0]], F[SUPP_FIGURES[-1]]),
             range_tabs_B=_range_label(T[SUPP_TABLES[len(PART_A_TABLES)]], T[SUPP_TABLES[-1]]))
    rows = [dict(Item=item, Recommendation=rec, **{"Where reported": where.format(F=F, T=T, M=M, N=N)},
                 Status=status) for item, rec, where, status in _STROBE + _RECORD]
    return pd.DataFrame(rows, columns=["Item", "Recommendation", "Where reported", "Status"])


def checklist_block(R, label: str):
    """('table', {...}) of the checklist. Its text already carries the journal numbering (refs_remapped=True).
    Through journal_config.JournalRegistry the payload is built by its table_block (df/title/note passed, as the
    contract requires for a synthetic table); the local registry builds the same payload directly."""
    df = checklist_table(R)
    if _JC is not None and isinstance(R, getattr(_JC, "JournalRegistry", ())):
        kind, payload = R.table_block(CHECKLIST_KEY, label, df=df, title=CHECKLIST_TITLE, note=CHECKLIST_NOTE)
        return (kind, dict(payload, refs_remapped=True))
    return ("table", dict(df=df, title=CHECKLIST_TITLE, note=CHECKLIST_NOTE, label=label, refs_remapped=True))


# ---------------------------------------------------------------------------
# A9 — the pre-specified analysis plan, rendered in English from analysis_plan.md v1.0
# ---------------------------------------------------------------------------
def _assert_plan_stamp() -> None:
    text = ANALYSIS_PLAN_MD.read_text(encoding="utf-8")
    stamp = f"**Versión:** {ANALYSIS_PLAN_VERSION}, {ANALYSIS_PLAN_DATE_ES}"
    if stamp not in text:
        raise RuntimeError(f"{ANALYSIS_PLAN_MD.name} no longer carries the stamp {stamp!r}: re-render A9 from it")


def analysis_plan_blocks() -> list:
    """English rendering of `analysis_plan.md`, version 1.0 of 4 September 2026 (the study protocol)."""
    _assert_plan_stamp()
    b: list = []
    b.append(("h2", f"A9. Pre-specified analysis plan (version {ANALYSIS_PLAN_VERSION}, {ANALYSIS_PLAN_DATE_EN})"))
    b.append(("p", f"This section is an English rendering of the study's pre-specified analysis plan "
                   f"(analysis_plan.md, version {ANALYSIS_PLAN_VERSION}, dated {ANALYSIS_PLAN_DATE_EN}), written "
                   f"before any association was explored; later changes are recorded in the decision log named in "
                   f"the data sharing statement. The Spanish original is supplied verbatim with the submission "
                   f"files (analysis_plan_v1.0_es.md). Its headings and rules are rendered one by one; nothing is "
                   f"added."))
    b.append(("h3", "Principal question"))
    b.append(("p", "How did the administrative recognition of autism and the recorded demand for services change "
                   "between 2019 and 2025 in Chile's public health and education systems, and how much of the "
                   "change is robust to variations in coverage, coding intensity and definitions?"))
    b.append(("p", "The contribution is not to estimate prevalence or incidence. It is to show the descriptive "
                   "convergence between independent administrative systems, to quantify the threats to "
                   "comparability and to translate the findings into surveillance and capacity needs. Law 21.545 "
                   "(March 2023) is policy context, not an intervention with an identifiable causal effect."))
    b.append(("h3", "Conceptual DAG (simple)"))
    b.append(("p", "Underlying occurrence, social awareness and the law, supply and capacity, and the pandemic "
                   "(2020–2021) all feed care seeking, which leads to contact with the system and then to "
                   "administrative recognition (a code or a register entry). System coverage and the reporting "
                   "panel act on the contact; coding depth and taxonomy act on the recognition. No data allow the "
                   "contributions of occurrence, care seeking, coverage and coding to be separated; the study "
                   "describes them and subjects them to sensitivity analyses."))
    b.append(("h3", "Sources, units and linkage"))
    b.append(("bullets", [
        "Public GRD 2019–2024: unit = episode (hospitalisation or major ambulatory surgery); flow; geography = "
        "hospital and reported comuna of residence; individual linkage = identifier within the year, none across "
        "2020/2021.",
        "REM A03, A27, A05, A28 2019–2025: unit = establishment × month × code row; flow (activity); geography = "
        "establishment; no individual linkage.",
        "REM P2, P6 2019–2025: unit = semester stock per establishment; stock (June, December); geography = "
        "establishment; no individual linkage.",
        "DEIS discharges 2019–2024: unit = discharge; flow; geography = establishment and residence; no individual "
        "linkage.",
        "FONASA aggregates 2018–2025, APS 2019–2025, ISAPRE 2019–2025: unit = aggregated December cell; stock; "
        "geography = enrolment or domicile, APS centre, administrative comuna; no individual linkage.",
        "INE base 2017 (Census 2024 and base 2024 as sensitivity): unit = population; stock; geography = residence; "
        "linkage not applicable.",
        "REM-20 2019–2025: unit = establishment × area × month; activity and capacity; geography = establishment; "
        "no individual linkage.",
        "ENDIDE 2022, ENCAVI 2023–24: unit = surveyed person; cross-sectional; geography = national and regional; "
        "no individual linkage.",
        "PIE/SINACES 2019–2025, JUNAEB EVE 2019–2025: unit = aggregated school register, student; school stock; "
        "geography = national, establishment; no individual linkage.",
    ]))
    b.append(("p", "The sources are not linked by person. Every indicator that combines stages is an aggregate "
                   "administrative pathway, not a sequence followed at the individual level."))
    b.append(("h3", "Definition variants (two complete analyses)"))
    b.append(("bullets", [
        "con_rett: GRD any F84.x including F84.2; REM A05 and P6 all pervasive-developmental-disorder categories "
        "including the Rett rows.",
        "sin_rett: GRD F84.x except F84.2; the same REM categories without Rett.",
        "Identical series in both variants: strict REM autism (05990022, P6241010, P6241060), principal F84, A03, "
        "A27, A28 and P2, education, surveys.",
        "The broad pervasive-developmental-disorder category of REM 2019–2020 (06902600, 05225000, P6223000, "
        "P6223380) contains Rett inseparably: it is presented only as a flagged sensitivity in both variants.",
    ]))
    b.append(("h3", "Estimands and hierarchy"))
    b.append(("bullets", [
        "Primary hospital estimand (GRD): episodes with documented F84 in any position per 100,000 GRD episodes of "
        "the same year and panel. Mandatory sensitivities: principal F84; strict hospitalisation against all "
        "activity (major ambulatory surgery apart); annual observed panel against a fixed panel of 65 hospitals; "
        "stratification and adjustment by diagnostic depth (number of coded diagnoses); unique persons only within "
        "each year; rates per INE population by age and sex (per 100,000 residents) as a complementary population "
        "reading; hospital effects (random) if the model is stable.",
        "Primary outpatient estimand (REM A05): autism entries from 2021: count, rate per 100,000 INE residents "
        "with age standardisation where the age and sex breakdown allows it, number of reporting establishments "
        "and stable panel. The broad 2019–2020 category only as a separate sensitivity.",
        "Follow-up (REM P2, P6): December stocks for autism (P2 NANEAS; P6 primary care and specialty), with June "
        "as sensitivity and without summing semesters; reporting establishments; the NANEAS total as denominator "
        "only from 2023.",
        "Detection and referral (REM A03, A27): components by definition era (2019–2022, 2023–2024, 2024 for 31–59 "
        "months, 2025) and A27 from 2023, presented in separate facets; no ratio between stages of sources that "
        "cannot be linked.",
        "Rehabilitation (REM A28): entries for autism to primary and hospital rehabilitation from 2023.",
        "Denominators and coverage: INE (population), FONASA and ISAPRE (insurance), APS enrolment (operational "
        "coverage), REM-20 (activity and capacity; panel of 188). Each answers a different question and none is "
        "chosen for convenience.",
        "Population benchmarks: ENDIDE 2022 and ENCAVI 2023–24 with complex design: proportion, weighted total, "
        "standard error and 95% CI; no comuna-level disaggregation.",
        "Educational triangulation: PIE strict autism, autism–Asperger, harmonised (explicit rule for the 2022 "
        "discrepancy) and SINACES 2024–2025; JUNAEB EVE 2019–2025 with the annual wording and the EXP weight; "
        "first year of secondary school 2024 'not estimable'.",
    ]))
    b.append(("h3", "Pre-specified modelling and sensitivity"))
    b.append(("bullets", [
        "Family: log-linear quasi-Poisson with an offset for the denominator (GRD episodes, INE population or "
        "reporting establishments according to the estimand); annual percent change with 95% CI; checks of "
        "overdispersion and residual autocorrelation.",
        "Unit: year (national) and establishment-year or hospital-year for models with random effects of the "
        "establishment.",
        "Minimum covariates: mean diagnostic depth of the panel (GRD), an indicator of 2020–2021 as a reporting "
        "disruption (not as a causal effect), definition era (REM).",
        "Complete panel against observed panel; missing against zero (the absence of a REM row is not zero).",
        "No causal interrupted time series: the coincidence of the pandemic, code changes, reporting expansion and "
        "the law means that no change can be identified with Law 21.545.",
        "Multiplicity: the analyses are descriptive; the local comparisons of the spatial analysis (if included in "
        "the supplement) use the false discovery rate.",
        "Suppression: cells with fewer than five events are shown as '<5' in territorial tables.",
    ]))
    b.append(("h3", "Exclusions and rules"))
    b.append(("bullets", [
        "Administrative counts are never called prevalence, incidence or a real increase of autism.",
        "Episodes with F84 as a secondary diagnosis are never described as admissions for autism.",
        "June and December of Series P are never summed; 2020 is never interpolated.",
        "GRD persons are never deduplicated across 2020/2021.",
        "Repeated FONASA rows of 2018–2020 are not removed (they are additive).",
        "Place of care is never mixed with residence without a compatibility analysis.",
        "The 72 hospitals are never used as a fixed panel.",
        "Every number must be traceable to a file, version, filter and script; a number that does not reproduce "
        "is removed or marked as pending.",
    ]))
    return b


# ---------------------------------------------------------------------------
# Front matter, Part A, Part B
# ---------------------------------------------------------------------------
SUPP_TITLE = "Supplementary appendix"
PART_A_H1 = "Part A. Applied methodology"
PART_B_H1 = "Part B. Supplementary results not shown in the article"
APPENDIX_REFS_H1 = "A10. Appendix references"
CONTENTS_H1 = "Contents"
ABOUT_H1 = "About this appendix"
VARIANT_SENTENCE = ("It presents the F84 family excluding Rett syndrome (F84.2), the variant analysed in the article; "
                    "the full-family variant (including F84.2) is not submitted separately and is compared series by "
                    "series in {F[figE28_variant_sensitivity]} and {T[E28_variant_sensitivity]}.")


def _front_matter(fields: dict) -> list:
    N, F, T = fields["N"], fields["F"], fields["T"]
    about = (f"This appendix accompanies the article “{PE.TITLE}”. "
             + VARIANT_SENTENCE.format(F=F, T=T)
             + f" The pre-specified analysis plan (A9) and the sensitivity grid ({T['M6_sensitivity_grid']}) name "
               f"the full F84 family as the primary case definition of the study; the author team chose the variant "
               f"excluding Rett syndrome for the submission (recorded in the decision log named in the data sharing "
               f"statement), and the two variants differ by {N['rett_diff_2024']} GRD episodes in 2024."
               f" It is one document: Part A carries the methodology applied in the study, generated by the same "
               f"code that produced every number of the article, with its {N['n_equations']} numbered equations, the "
               f"estimator map, the sensitivity grid, the STROBE and RECORD checklist and the pre-specified analysis "
               f"plan; Part B carries the results that the article cites but does not print — "
               f"{N['n_supp_figs']} figures and {N['n_supp_tabs']} tables in all, numbered by the order in which the "
               f"article first cites them — each figure introduced by what it shows, why it matters and what it adds "
               f"beyond the body, and each table by a sentence that states what it holds and what it adds. The "
               f"remaining {N['n_dropped_figs']} plates and {N['n_dropped_tabs']} tables of the full corpus, which "
               f"duplicate a printed item or describe detail without bearing on the article's message, are listed by "
               f"name in section B12 and deposited with the data. The table of contents gives the page of every item; "
               f"the appendix references are numbered separately from those of the article.")
    rules = (f"Rules of reading that hold throughout. Every count is administrative recognition of autism — the "
             f"recording of an autism code in a contact with a service — and never prevalence or incidence. The "
             f"hospital outcome is episodes with documented F84 in any diagnostic position; F84 as principal "
             f"diagnosis is a separate series. The sources are not linked at the person level: no figure or table "
             f"follows individuals across systems and no ratio between two sources is a probability; the comparison "
             f"of principal F84 in DEIS and in GRD is a coverage comparison between two registries of the same event. "
             f"Stocks (persons under control at a cut date; insured, enrolled or registered persons) and flows "
             f"(episodes, discharges, entries, interventions) never share an axis. Place of care (hospital, reporting "
             f"establishment) and place of residence (INE, DEIS, GRD comuna) are never mixed without an explicit "
             f"warning. The hospital panel is {N['fixed_panel']} fixed hospitals against {N['hosp_series']} observed in "
             f"2019 to 2024; persons are counted only within each year. Survey estimates carry their weights and "
             f"complex design. In REM, an explicit zero, a missing cell and a module not reported are three distinct "
             f"states; the December cut of Series P is primary, June the sensitivity, and the two are never summed. "
             f"Cells below five events are suppressed. Definition eras are never joined by a line. Law 21.545, in "
             f"force from March 2023, appears only as policy context and no causal effect is attributed to it.")
    lines = [f"Correspondence: {PE.AUTHOR}, {PE.AUTHOR_EMAIL}",
             "Analysis variant: F84 family excluding Rett syndrome (F84.2)"]
    # No heading before the table of contents: build_journal inserts its TOC block before the FIRST h1 of the
    # document (Part A), so the about-paragraph and the rules stay on the title pages, as the plan orders them.
    return [("title", SUPP_TITLE),
            ("subtitle", PE.TITLE),
            ("authors", dict(authors=[(PE.AUTHOR, "1")], affiliations=[("1", PE.AFFILIATION)], lines=lines)),
            ("p", about),
            ("p", rules)]


def _part_a(V: dict, R, fields: dict, remap: bool = False) -> tuple[list, list]:
    """Part A blocks and their TOC entries (`remap`: flag the methodological tables as remapped, see `_remap_block`)."""
    N, T = fields["N"], fields["T"]
    entries: list[dict] = []
    methods = PME.methods_blocks(VARIANT, V, LANG, R=R, first_table=1)
    if not methods or methods[0][0] != "h1":
        raise RuntimeError("prose_methods_extended.methods_blocks must start with an h1 heading")
    blocks: list = [("h1", PART_A_H1)]
    entries.append(dict(id="Part A", level=1, text=PART_A_H1))
    blocks.append(("p", (
        f"Part A reproduces in full the methodology applied in the study, as generated by the same code that "
        f"produced every number of the article: the design, sources, units and the impossibility of linkage (M1); "
        f"the case definitions and code sets (M2); the denominators, coverage layers and compatibility rules (M3); "
        f"the {N['n_estimators']} estimators with their {N['n_equations']} equations, printed once each in numeric "
        f"order under the estimator that first uses them and cited from its heading, with the estimator map "
        f"({T['M5_estimator_map']}) that names the equation, script and output file of each (M4); the reproduction "
        f"controls, the data states and the grid of {N['n_sens']} pre-specified sensitivity analyses "
        f"({T['M6_sensitivity_grid']}) (M5); the software, seeds and pipeline map (M6); and the limitations of the "
        f"methods (M7). The ten methodological tables are printed where they are discussed: "
        f"{T['M1_sources_units']} (sources, units and linkage), {T['M2_case_definitions']} (case definitions), "
        f"{T['M3_rem_code_sets']} (REM code sets), {T['M4_denominator_layers']} (denominator layers), "
        f"{T['M5_estimator_map']} (estimator map), {T['M6_sensitivity_grid']} (sensitivity grid), "
        f"{T['M7_data_states']} (data states), {T['M8_pipeline_map']} (pipeline map), "
        f"{T['M9_software_seeds']} (software and seeds) and {T['M10_reproduction_controls']} (reproduction "
        f"controls). Section A8 is the STROBE and RECORD checklist ({T['S_reporting_checklist']}), A9 the "
        f"pre-specified analysis plan and A10 the appendix references, numbered separately from those of the "
        f"article.")))
    for kind, payload in methods[1:]:
        if kind == "table" and remap:
            kind, payload = _remap_block((kind, payload))
        blocks.append((kind, payload))
        if kind == "h2":
            m = re.match(r"^(M\d)\.", str(payload))
            entries.append(dict(id=m.group(1) if m else str(payload), level=2, text=str(payload)))
        elif kind == "table":
            entries.append(dict(id=payload["label"], level=3, text=f"{payload['label']} — {payload['title']}"))
    # A8 — checklist
    label = tab_label(CHECKLIST_KEY)
    h = "A8. STROBE and RECORD checklist"
    blocks.append(("h2", h))
    entries.append(dict(id="A8", level=2, text=h))
    blocks.append(("p", (
        f"{label} maps every item of STROBE and of its RECORD extension for routinely collected data to the "
        f"section of the article, or the figure or table of the article or of this appendix, where it is "
        f"reported. The study has no recruitment and performs no person-level linkage, so the linkage items are "
        f"reported as not applicable; the two items whose content the author team supplies at submission (funding "
        f"source; repository URL and DOI) are marked.")))
    cb = checklist_block(R, label)
    blocks.append(cb)
    entries.append(dict(id=label, level=3, text=f"{label} — {cb[1]['title']}"))
    # A9 — analysis plan
    plan = analysis_plan_blocks()
    blocks += plan
    entries.append(dict(id="A9", level=2, text=str(plan[0][1])))
    return blocks, entries


def _part_b(R, fields: dict, remap: bool) -> tuple[list, list]:
    N = fields["N"]
    entries: list[dict] = []
    blocks: list = [("h1", PART_B_H1)]
    entries.append(dict(id="Part B", level=1, text=PART_B_H1))
    blocks.append(("p", (
        f"Part B collects the results that the article cites but does not print, in the order in which the article "
        f"first cites them, so that figure and table numbers ascend with the text. Each figure is preceded by a "
        f"paragraph that states what it shows, its unit and its denominator, why it matters and what it adds beyond "
        f"the body; each table by a sentence that states what it holds and what it adds. The items of the full corpus "
        f"that are not printed here are listed by name in section B12. Captions and notes "
        f"are the self-contained texts of the output files and state coverage, definition era, the number of "
        f"reporting establishments or hospitals and the source file. Cells with fewer than five events are "
        f"suppressed in the territorial tables, and survey domains with fewer than 30 cases or a relative standard "
        f"error above 30% are flagged and are not presented as reliable. The {N['n_supp_figs']} figures and the "
        f"{N['n_supp_tabs']} tables of this appendix are numbered S1 onwards in a single sequence per kind; the "
        f"first {PE.nw(len(PART_A_TABLES))} tables are printed in Part A. A table whose columns do not fit a "
        f"landscape page at 8 point is printed in consecutive parts, labelled 'part i of m', with its key "
        f"columns repeated in every part and its note under the last part; no cell is altered, and where a "
        f"column repeats one value over a run of rows that value is printed once as the bold heading of the "
        f"run.")))
    fig_of = {s: [k for k, sec in FIGURES if sec == s] for s, _ in SECTIONS}
    tab_of = {s: [k for k, sec in TABLES if sec == s and k not in PART_A_TABLES] for s, _ in SECTIONS}
    for heading, sections in PART_B_GROUPS:
        blocks.append(("h2", heading))
        entries.append(dict(id=heading.split(".")[0], level=2, text=heading))
        for section in sections:
            for key in fig_of[section]:
                label = fig_label(key)
                blocks.append(("p", figure_intro(key, label, fields)))
                fb = R.figure_block(key, label)
                if remap:
                    fb = _remap_block(fb)
                title = str(fb[1].get("caption", "")).split(". ")[0]
                if not fb[1].get("heading"):
                    fb = (fb[0], dict(fb[1], heading=title))   # the legend heading, used by the builder's TOC
                blocks.append(fb)
                entries.append(dict(id=label, level=3, text=f"{label} — {title}"))
            for key in tab_of[section]:
                label = tab_label(key)
                blocks.append(("p", table_intro(key, label, fields)))
                tb = R.table_block(key, label)
                if remap:
                    tb = _remap_block(tb)
                blocks.append(tb)
                entries.append(dict(id=label, level=3, text=f"{label} — {tb[1]['title']}"))
    # B12 — the items of the full corpus that neither the article nor this appendix prints, by name
    heading = "B12. Items of the full corpus not printed in this appendix"
    blocks.append(("h2", heading))
    entries.append(dict(id="B12", level=2, text=heading))
    dropped = dropped_items()
    blocks.append(("p", (
        f"The full bilingual corpus of the study carries {N['n_dropped_figs']} further plates and "
        f"{N['n_dropped_tabs']} further tables that this appendix does not print because they duplicate a printed "
        f"item (the same series in another arrangement, or a complete-data table that the printed tables and the "
        f"deposited tidy files already carry) or describe hospital, REM or population detail with no bearing on the "
        f"article's message. They are deposited with the data named in the article's data sharing statement, under "
        f"the file names below (corpus titles, without their provisional numbers).")))
    blocks.append(("small", "Plates: " + "; ".join(
        f"{k} ({PE._strip_prefix(R.captions[k].get('title', '')) if k in R.captions else 'no caption'})"
        for k in dropped["figures"]) + "."))
    blocks.append(("small", "Tables: " + "; ".join(
        f"{k} ({PE._strip_prefix(R.titles[k].get('title', '')) if k in R.titles else 'no title'})"
        for k in dropped["tables"]) + "."))
    return blocks, entries


def _toc_blocks(entries: list[dict], pages: dict | None) -> list:
    pages = pages or {}
    out: list = [("h1", CONTENTS_H1),
                 ("small", "Page numbers refer to this appendix; every page carries its number in the footer.")]
    for e in entries:
        page = pages.get(e["id"], TOC_PLACEHOLDER)
        indent = " " * (e["level"] - 1)
        out.append(("small", f"{indent}{e['text']}\t{page}"))
    return out


def toc_entries(blocks: list) -> list[dict]:
    """TOC lines a document built from `blocks` needs: Parts, M-sections, A8/A9, groups, every figure and table."""
    entries: list[dict] = []
    for kind, payload in blocks:
        if kind == "h1" and str(payload) in (PART_A_H1, PART_B_H1):
            entries.append(dict(id="Part A" if payload == PART_A_H1 else "Part B", level=1, text=str(payload)))
        elif kind == "h2":
            m = re.match(r"^(M\d|A\d+|B\d+)\.", str(payload))
            if m:
                entries.append(dict(id=m.group(1), level=2, text=str(payload)))
        elif kind == "table":
            entries.append(dict(id=payload["label"], level=3, text=f"{payload['label']} — {payload['title']}"))
        elif kind == "figure":
            title = str(payload.get("caption", "")).split(". ")[0]
            entries.append(dict(id=payload["label"], level=3, text=f"{payload['label']} — {title}"))
        elif kind == "refs":
            title = (payload or {}).get("title") if isinstance(payload, dict) else None
            entries.append(dict(id=APPENDIX_REFS_H1, level=1, text=title or APPENDIX_REFS_H1))
    return entries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build(lang: str, V: dict | None, *, pages: dict | None = None, toc: bool = False, remap: bool = False,
          R=None) -> dict:
    """Assemble the appendix. Returns dict(blocks, toc, figures, tables); see `blocks()` for the arguments."""
    if lang not in SUBMISSION_LANGS:
        raise NotImplementedError("bilingual corpus supplement exists")
    if V is None:
        V = PE.load_values(VARIANT)
    R = R or registry()
    fields = _fields(V, R)
    front = _front_matter(fields)
    a_blocks, a_entries = _part_a(V, R, fields, remap)
    b_blocks, b_entries = _part_b(R, fields, remap)
    refs = ("refs", dict(title=APPENDIX_REFS_H1))
    entries = a_entries + b_entries + [dict(id=APPENDIX_REFS_H1, level=1, text=APPENDIX_REFS_H1)]
    body = a_blocks + b_blocks + [refs]
    blocks = front + (_toc_blocks(entries, pages) + [("pagebreak", None)] if toc else []) + body
    problems = equation_problems(blocks)
    if problems:
        raise RuntimeError("the appendix does not print the equations as required: " + "; ".join(problems))
    return dict(blocks=blocks, toc=entries, figures=list(SUPP_FIGURES), tables=list(SUPP_TABLES))


def blocks(lang: str, V: dict | None = None, *, pages: dict | None = None, toc: bool = False, remap: bool = False,
           R=None) -> list:
    """Block list of the ONE English supplementary document (contract 7.2).

    lang    must be "en"; "es" raises NotImplementedError("bilingual corpus supplement exists").
    V       `outputs/values_sin_rett.json` as a dict (loaded when None).
    pages   {toc id: page number} for the module's own TOC (ids = `toc_entries()`); the first pass leaves
            TOC_PLACEHOLDER in the page column.
    toc     emit the module's own table of contents as 10 pt lines after the title pages (standalone use). The
            default False leaves it to build_journal, which inserts its ("toc", …) block before the first h1
            (Part A), fills the pages in its two-pass build and verifies them on the PDF (plan 7.6).
    remap   rewrite the corpus-numbered cross-references of captions and notes here (standalone use); the journal
            build leaves False and remaps once through journal_config.remap_refs.
    R       a registry with the surface of journal_config.JournalRegistry (defaults to `registry()`).
    """
    return build(lang, V, pages=pages, toc=toc, remap=remap, R=R)["blocks"]


# ---------------------------------------------------------------------------
# Checks: equations, cross-references with the article
# ---------------------------------------------------------------------------
def equation_problems(blocks: list) -> list[str]:
    """Every equation of `equations_lancet` printed exactly once, in numeric order, under a heading that cites it."""
    numbers = [int(payload[1]) for kind, payload in blocks if kind == "eq"]
    expected = list(range(1, len(EQ.NUMBER) + 1))
    problems: list[str] = []
    if numbers != expected:
        problems.append(f"equation numbers printed {numbers} differ from {expected}")
    problems += PME.heading_equation_problems([b for b in blocks if b[0] in ("h1", "h2", "h3", "eq")])
    return problems


_SUPP_CITE_RE = re.compile(r"\b(Figure|Table)s?\s+S(\d+)")
#: continuation of a citation list after the first token: "–S29" / "–29" (range), ", S28" / " and S30" (list)
_SUPP_CITE_MORE_RE = re.compile(r"\s*(?:(?P<dash>[–-])\s*S?(?P<to>\d+)|(?:,|;|\band)\s*S(?P<next>\d+))")


def _supp_citations(text: str):
    """(kind, number) pairs cited by `text`, with ranges ('Tables S27–S29') and lists ('Tables S45 and S46')
    expanded; the order is the order of first mention."""
    pos = 0
    while True:
        m = _SUPP_CITE_RE.search(text, pos)
        if not m:
            return
        kind, n = m.group(1), int(m.group(2))
        yield kind, n
        pos = m.end()
        while True:
            c = _SUPP_CITE_MORE_RE.match(text, pos)
            if not c:
                break
            if c.group("dash"):
                to = int(c.group("to"))
                if to < n or to - n > 200:      # not a range of appendix items (e.g. a year after a hyphen)
                    break
                for k in range(n + 1, to + 1):
                    yield kind, k
                n = to
            else:
                n = int(c.group("next"))
                yield kind, n
            pos = c.end()


def _article_texts(article_blocks: list) -> list[str]:
    out: list[str] = []
    for kind, payload in article_blocks:
        if kind in ("p", "small", "h1", "h2", "h3", "title", "subtitle"):
            out.append(str(payload))
        elif kind == "bullets":
            out += [str(i) for i in payload]
        elif kind == "panel":
            out += [str(t) for _, t in payload.get("items", [])]
        elif kind == "figure":
            out.append(str(payload.get("caption", "")))
        elif kind == "table":
            out += [str(payload.get("title", "")), str(payload.get("note", ""))]
    return out


def cited_items(article_blocks: list) -> dict:
    """Appendix figures and tables cited by an assembled article, as keys, in order of first citation."""
    figs: list[int] = []
    tabs: list[int] = []
    for text in _article_texts(article_blocks):
        for kind, n in _supp_citations(text):
            target = figs if kind == "Figure" else tabs
            if n not in target:
                target.append(n)
    return dict(figures=[SUPP_FIGURES[n - 1] if 1 <= n <= len(SUPP_FIGURES) else f"S{n}" for n in figs],
                tables=[SUPP_TABLES[n - 1] if 1 <= n <= len(SUPP_TABLES) else f"S{n}" for n in tabs],
                figure_numbers=figs, table_numbers=tabs)


def cross_reference_problems(article_blocks: list) -> list[str]:
    """Both directions: every S-item the article cites exists here; every item here is cited; first citations ascend."""
    cited = cited_items(article_blocks)
    problems: list[str] = []
    for kind, numbers, order in (("Figure", cited["figure_numbers"], SUPP_FIGURES),
                                 ("Table", cited["table_numbers"], SUPP_TABLES)):
        for n in numbers:
            if not 1 <= n <= len(order):
                problems.append(f"the article cites {kind} S{n}, which does not exist in the appendix")
        missing = [f"{kind} S{i + 1} ({key})" for i, key in enumerate(order) if (i + 1) not in numbers]
        if missing:
            problems.append(f"appendix items never cited by the article: {', '.join(missing)}")
        if numbers != sorted(numbers):
            problems.append(f"{kind} S-numbers are not first cited in ascending order: {numbers}")
    return problems


if __name__ == "__main__":
    out = build(LANG, None, remap=True, toc=True)
    kinds: dict[str, int] = {}
    for k, _ in out["blocks"]:
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{len(out['blocks'])} blocks: {kinds}")
    print(f"{len(SUPP_FIGURES)} figures, {len(SUPP_TABLES)} tables, {len(out['toc'])} TOC entries; "
          f"equations OK: {not equation_problems(out['blocks'])}; remap log: {len(REMAP_LOG)} entries")
