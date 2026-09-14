# -*- coding: utf-8 -*-
"""prose_en.py — English manuscript and supplementary appendix for The Lancet Regional Health – Americas.

Public API
----------
    manuscript(variant, V) -> list of docx_builder blocks (main document, English)
    supplement(variant, V) -> list of docx_builder blocks (supplementary appendix, English)
    load_values(variant)   -> dict V read from outputs/values_<variant>.json
    word_counts(blocks)    -> dict with word counts (summary, panel, core body without '[OPT] ', optional body, ...)
    citation_keys(blocks, include_opt=False) -> ordered list of distinct [@key] citations

Conventions
-----------
* Every number in the text comes from V (outputs/values_<variant>.json); nothing is hard-coded. Numbers are
  formatted with common.fmt_number(x, dec, 'en') and confidence intervals with common.fmt_ci(lo, hi, dec, 'en').
* Counts are administrative recognition (episodes, entries, interventions, stocks, enrolments), never prevalence or
  incidence; GRD counts are "episodes with documented F84", never "hospitalisations for autism"; sources are not
  person-linked (aggregate administrative pathway, no cascade, no conversion ratios); stocks and flows are kept
  apart; place of care and residence are kept apart; Law 21.545 (March 2023) is context, never an intervention.
* Optional paragraphs (to be dropped for the 3500–5000-word journal version) start with the tag '[OPT] ', which the
  final builder strips; word_counts() reports the core text without them.
* Supplementary figures and tables are numbered by PRINT ORDER: the thematic order in which the supplementary part
  prints them (supplementary_material.FIGURE_ORDER / TABLE_ORDER, the registry shared by the manuscript and the
  supplement), which is the rule the supplementary note itself states. It is NOT the order of first mention: a
  cross-reference in the text never fixes a number, and R.fig()/R.tab() only resolve the number the registry gives.
  Figure captions come from outputs/<variant>/en/figures/captions.json and table titles/notes from
  outputs/<variant>/en/tables/titles.json (keys = file stems; provisional numbers in the stored titles are
  stripped and replaced by the registry's label).
* Numbering clashes between modules are resolved here by choosing one file per slot: figS3_grd_hospital_effects
  (08a) instead of figS3_hospital_effects (06); figS4_models_cpa (06) instead of figS4_grd_model_sensitivities
  (08a); figS7_rem_education_models (06) instead of figS7_a05_standardised_rates (08b); T7_models (curated) as
  Table 7 with T7_models_cpa_full in the supplement; T8_controls_compact as Table 8 with the full T8_controls in
  the supplement; S_a05_standardised_rates (06) instead of S7_a05_standardised_rates (08b).
* Citations use [@key] markers whose keys must exist in references_lancet.bib; the core text targets <= 30 keys and
  official data-source keys are cited in optional paragraphs and in the supplement.

Usage: `python prose_en.py [--out DIR]` builds both variants (manuscript + supplement) into a temporary directory
(or DIR) and prints the word counts and the number of distinct citation keys.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import fmt_ci, fmt_number  # noqa: E402
import common as C_CONTROLS  # noqa: E402  (single source of the compact controls-note clause)
import controls_registry as CR  # noqa: E402  (named scopes of the reproduction controls: one source for every total)
import supplementary_material as SM  # noqa: E402  (shared inventory and builder of the supplementary part)

LANG = "en"
OUT = HERE / "outputs"
BIB = HERE / "references_lancet.bib"
OPT = "[OPT] "

TITLE = ("Administrative recognition of autism across health and education systems in Chile, 2019–2025: "
         "a national multisource surveillance study")
RUNNING_TITLE = "Administrative recognition of autism in Chile, 2019–2025"
SUPP_PART_H1 = "Supplementary material"        # heading of the supplementary part inside the manuscript file
SUPP_REFS_H1 = "Supplementary references"
AUTHOR = "Amaru Simón Agüero Jiménez"
AUTHOR_EMAIL = "amaruaguero2004@ug.uchile.cl"
AFFILIATION = "[Institutional affiliation to be completed by the author before submission]"

VARIANT_LABEL = {
    "con_rett": "full F84 family (F84.0–F84.9, including Rett syndrome F84.2)",
    "sin_rett": "F84 family without Rett syndrome (F84.2 excluded)",
}
VARIANT_SHORT = {"con_rett": "with Rett", "sin_rett": "without Rett"}
YEARS_GRD = [2019, 2020, 2021, 2022, 2023, 2024]
YEARS_REM = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
YEARS_A05 = [2021, 2022, 2023, 2024, 2025]
YEARS_A27 = [2023, 2024, 2025]

# Main figures and tables (file stems) in the order they are numbered. The data-workflow plate of module 08d is
# Figure 1 of the article and the source inventory (T1_sources) is Table S1 of the supplementary material, so the
# article carries Figures 1–5 and Tables 1–7. Never cite a main item with a literal string: use R.mfig()/R.mtab().
MAIN_FIGURES = ["fig1_dataflow", "fig1_sources_coverage", "fig2_grd_core", "fig3_rem_pathway", "fig4_triangulation"]
MAIN_TABLES = ["T2_grd_core", "T3_rem_pathway", "T4_denominators_coverage", "T5_survey_benchmarks",
               "T6_education", "T7_models", "T8_controls_compact"]

#: Words used to name an article item in each language.
_ITEM_WORD = {"figure": {"en": "Figure", "es": "Figura"}, "table": {"en": "Table", "es": "Tabla"}}


def main_figure_label(key: str, lang: str) -> str:
    """'Figure 4' / 'Figura 4': the article label of `key`, resolved from MAIN_FIGURES.

    The pipeline modules that STORE a table title whose body names an article figure (08b for
    F3_rem_pathway_data, 08c for F4_triangulation_series) call this instead of writing the number as a
    literal, so a renumbering of MAIN_FIGURES can never leave a stored title pointing at the wrong plate."""
    if key not in MAIN_FIGURES:
        raise KeyError(f"'{key}' is not in MAIN_FIGURES")
    if lang not in _ITEM_WORD["figure"]:
        raise ValueError(f"unknown language: {lang!r}")
    return f"{_ITEM_WORD['figure'][lang]} {MAIN_FIGURES.index(key) + 1}"


def main_table_label(key: str, lang: str) -> str:
    """'Table 2' / 'Tabla 2': the article label of `key`, resolved from MAIN_TABLES (same rule as above)."""
    if key not in MAIN_TABLES:
        raise KeyError(f"'{key}' is not in MAIN_TABLES")
    if lang not in _ITEM_WORD["table"]:
        raise ValueError(f"unknown language: {lang!r}")
    return f"{_ITEM_WORD['table'][lang]} {MAIN_TABLES.index(key) + 1}"

#: Panel letters. Every multipanel plate of the study letters its panels in LOWERCASE, on the plate and in the
#: caption ('(a) …', '(b) …'), so an in-text panel citation must use the same letters. It is never written as a
#: literal: R.mfigp()/R.figp() build it and resolve it against the plate's OWN caption, which is what makes a
#: divergence between the citation and the plate impossible instead of merely unlikely.
PANEL_LETTERS = "abcdef"
_PANEL_SPEC_RE = re.compile(r"^[a-z](?:[\u2013-][a-z])?$")


def panel_suffix(caption: str, panels: str, key: str = "") -> str:
    """'c' -> 'c'; 'd-e' -> 'd\u2013e'. Raises unless the caption itself labels every panel cited.

    `panels` is a single letter or a two-letter range, always lowercase. The caption of a multipanel plate opens
    each panel with '(a)', '(b)', ..., so membership is read from the caption: an uppercase letter, a panel the
    plate does not draw, an inverted range or a plate with no panels at all (the data-workflow diagram) fails
    here, at build time, and never reaches the page.
    """
    spec = str(panels).strip()
    if not _PANEL_SPEC_RE.match(spec):
        raise ValueError(f"panel citation {panels!r} for {key!r}: expected a lowercase letter or range such as 'c' or 'd-e'")
    letters = [c for c in spec if c.isalpha()]
    for letter in letters:
        if letter not in PANEL_LETTERS:
            raise ValueError(f"panel citation {panels!r} for {key!r}: a plate carries at most {len(PANEL_LETTERS)} panels")
        if f"({letter})" not in (caption or ""):
            raise ValueError(f"panel citation {panels!r}: the caption of {key!r} does not label a panel ({letter})")
    if len(letters) == 2:
        if letters[0] >= letters[1]:
            raise ValueError(f"panel citation {panels!r} for {key!r}: the range is not ascending")
        return f"{letters[0]}\u2013{letters[1]}"
    return letters[0]


# Supplementary figures and tables (file stems) in the order of the shared registry: the position in these lists IS
# the number (index + 1), so the article, the supplementary part of the manuscript and the standalone appendix always
# agree. The order comes from supplementary_material.py, which also holds the thematic grouping and the presentation
# sentence of every plate. Slot clashes of the earlier modules are resolved there: figS3_grd_hospital_effects (08a)
# instead of figS3_hospital_effects (06), figS4_models_cpa (06) instead of figS4_grd_model_sensitivities (08a),
# figS7_rem_education_models (06) instead of figS7_a05_standardised_rates (08b) and S_a05_standardised_rates (06)
# instead of S7_a05_standardised_rates (08b); the alternative files are deliberately left out.
SUPP_FIGURES = list(SM.FIGURE_ORDER)
SUPP_TABLES = list(SM.TABLE_ORDER)

# ---------------------------------------------------------------------------
# Formatting helpers (English)
# ---------------------------------------------------------------------------
def n0(x):
    return fmt_number(x, 0, LANG)

def n1(x):
    return fmt_number(x, 1, LANG)

def n2(x):
    return fmt_number(x, 2, LANG)

def ci(lo, hi, dec=1):
    return fmt_ci(lo, hi, dec, LANG)

def pct(x, dec=1):
    return f"{fmt_number(x, dec, LANG)}%"

def ppct(x, dec=1):
    """Proportion in [0, 1] formatted as a percentage."""
    return pct(100.0 * x, dec) if x is not None else "—"

def lst(items):
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]

def millions(x, dec=1):
    return f"{fmt_number(x / 1e6, dec, LANG)} million"

def codes(s) -> str:
    """Code lists from values_*.json rendered as prose: '+'-joined families get spaces around '+' (so that the line
    can break) and 'label=code, label=code' pairs become 'label code and label code'."""
    s = str(s)
    if "=" in s:
        parts = []
        for pair in s.split(","):
            label, _, code = pair.strip().partition("=")
            parts.append(f"{label.strip().replace('_', ' ')} {code.strip()}")
        return lst(parts)
    return s.replace("+", " + ")

_SMALL = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}

def nw(x):
    """Numbers one to ten in words (Lancet style), larger numbers as digits."""
    try:
        xi = int(x)
    except (TypeError, ValueError):
        return n0(x)
    return _SMALL[xi] if xi == x and xi in _SMALL else n0(x)

def load_values(variant: str) -> dict:
    path = OUT / f"values_{variant}.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

class _V:
    """Strict accessor over the flat values dictionary: a missing key raises a clear error (never a silent blank)."""

    def __init__(self, V: dict, variant: str):
        self.V = V
        self.variant = variant

    def __call__(self, key: str):
        if key not in self.V:
            raise KeyError(f"values_{self.variant}.json lacks the key '{key}' cited by prose_en.py")
        return self.V[key]

    def series(self, tmpl: str, years, dec=0):
        return lst(fmt_number(self(tmpl.format(y=y)), dec, LANG) for y in years)

    def apc(self, alias: str, dec=1):
        return f"{fmt_number(self(alias), dec, LANG)}% (95% CI {ci(self(alias + '_lo'), self(alias + '_hi'), dec)})"

    def apc_disp(self, alias: str, dec=1):
        return f"{self.apc(alias, dec)}; dispersion {n1(self(alias + '_disp'))}"

    def rate(self, prefix: str, year, dec=1):
        return (f"{fmt_number(self(f'{prefix}_rate_{year}'), dec, LANG)} (95% CI "
                f"{ci(self(f'{prefix}_rate_lo_{year}'), self(f'{prefix}_rate_hi_{year}'), dec)})")

    def est_ci(self, base: str, dec=1, suffix_lo="_lo", suffix_hi="_hi"):
        return f"{fmt_number(self(base), dec, LANG)} (95% CI {ci(self(base + suffix_lo), self(base + suffix_hi), dec)})"

    def est_ci_y(self, prefix: str, year, dec=1):
        """Estimate with CI whose keys carry the year last: <prefix>_<y>, <prefix>_lo_<y>, <prefix>_hi_<y>."""
        return (f"{fmt_number(self(f'{prefix}_{year}'), dec, LANG)} (95% CI "
                f"{ci(self(f'{prefix}_lo_{year}'), self(f'{prefix}_hi_{year}'), dec)})")

    def svy(self, base: str, dec=2):
        return (f"{pct(self(base + '_pct'), dec)} (95% CI {ci(self(base + '_lo_pct'), self(base + '_hi_pct'), dec)})")

# ---------------------------------------------------------------------------
# Supplementary numbering registry and document assembler
# ---------------------------------------------------------------------------
_PREFIX_RE = re.compile(r"^(Figure|Figura|Table|Tabla|Plate|L\u00e1mina)\s+[A-Za-z]{0,3}\d+[a-zA-Z]?\s*"
                       r"(\([^)]*\)\s*)?[.:]?\s*")

def _strip_prefix(title: str) -> str:
    return _PREFIX_RE.sub("", title or "").strip()

#: A note that counts "the rows of the table" but is written ONCE for TWO tables of different sizes.
#: Module 07_controls gives the full controls table (one row per indicator-year) and the compact one (one row per
#: control family or labelled check row) the same note. The clause that counts the rows is rebuilt FROM THE FILE
#: BEING PRINTED, so a note always counts its own table. Module 07 now writes the compact note with this same
#: clause, so this pass is normally a no-op: the two are the SAME function (common.controls_compact_clause), which
#: is what keeps a fix in one of them from leaving the other behind.
_ROWS_CLAUSE_RE = C_CONTROLS.CONTROLS_ROWS_CLAUSE_RE
_controls_compact_counts = C_CONTROLS.controls_compact_counts
_controls_compact_clause = C_CONTROLS.controls_compact_clause


def table_note(key: str, note: str, df, lang: str) -> str:
    """The note a table PRINTS: the stored note, with a shared row-count clause rebuilt for THIS table."""
    if key != "T8_controls_compact":
        return note
    rx = _ROWS_CLAUSE_RE[lang]
    m = rx.search(note or "")
    if not m or int(re.sub(r"[^\d]", "", m.group(1))) == len(df):
        return note
    return note[:m.start()] + _controls_compact_clause(df, lang) + note[m.end():]


class _Registry:
    """Shared numbering registry of the study.

    Supplementary items are numbered by their position in SUPP_FIGURES / SUPP_TABLES, which is the order in which
    the supplementary part prints them, so the manuscript and the standalone appendix always agree. Main items are
    numbered by their position in MAIN_FIGURES / MAIN_TABLES and must be cited with mfig()/mtab(): no main-figure or
    main-table citation may be written as a literal string anywhere in prose_en.py or prose_es.py.
    """

    FIG_WORD, TAB_WORD = "Figure", "Table"

    def __init__(self, variant: str):
        self.variant = variant
        self.figs: list[str] = []     # supplementary figures actually cited (order of first citation)
        self.tabs: list[str] = []     # supplementary tables actually cited
        self.main_figs: list[str] = []  # main figures cited, in order of first citation
        self.main_tabs: list[str] = []
        self.main_citations: list[str] = []  # every main-item citation string produced here, in order
        self.article_citations = 0   # citations produced before the article was closed
        fdir = OUT / variant / LANG / "figures"
        tdir = OUT / variant / LANG / "tables"
        xfdir = OUT / variant / LANG / "extra" / "figures"
        xtdir = OUT / variant / LANG / "extra" / "tables"
        self.fdir, self.tdir, self.xfdir, self.xtdir = fdir, tdir, xfdir, xtdir
        with open(fdir / "captions.json", encoding="utf-8") as fh:
            base_captions = json.load(fh)
        with open(xfdir / "captions.json", encoding="utf-8") as fh:
            extra_captions = json.load(fh)
        with open(tdir / "titles.json", encoding="utf-8") as fh:
            base_titles = json.load(fh)
        with open(xtdir / "titles.json", encoding="utf-8") as fh:
            extra_titles = json.load(fh)
        clash = (set(base_captions) & set(extra_captions)) | (set(base_titles) & set(extra_titles))
        if clash:
            raise RuntimeError(f"file stems used by both the main and the extra output folders: {sorted(clash)}")
        self.captions = {**extra_captions, **base_captions}
        self.titles = {**extra_titles, **base_titles}
        self._fig_dir = {k: xfdir for k in extra_captions} | {k: fdir for k in base_captions}
        self._tab_dir = {k: xtdir for k in extra_titles} | {k: tdir for k in base_titles}

    # -- supplementary items -------------------------------------------------
    def fig(self, key: str) -> str:
        if key not in SUPP_FIGURES:
            raise KeyError(f"'{key}' is not in SUPP_FIGURES")
        if key not in self.figs:
            self.figs.append(key)
        return f"{self.FIG_WORD} S{SUPP_FIGURES.index(key) + 1}"

    def tab(self, key: str) -> str:
        if key not in SUPP_TABLES:
            raise KeyError(f"'{key}' is not in SUPP_TABLES")
        if key not in self.tabs:
            self.tabs.append(key)
        return f"{self.TAB_WORD} S{SUPP_TABLES.index(key) + 1}"

    # -- main items (the only allowed way to cite a figure or table of the article) ------------
    def mfig(self, key: str) -> str:
        if key not in MAIN_FIGURES:
            raise KeyError(f"'{key}' is not in MAIN_FIGURES")
        if key not in self.main_figs:
            self.main_figs.append(key)
        label = f"{self.FIG_WORD} {MAIN_FIGURES.index(key) + 1}"
        self.main_citations.append(label)
        return label

    def mtab(self, key: str) -> str:
        if key not in MAIN_TABLES:
            raise KeyError(f"'{key}' is not in MAIN_TABLES")
        if key not in self.main_tabs:
            self.main_tabs.append(key)
        label = f"{self.TAB_WORD} {MAIN_TABLES.index(key) + 1}"
        self.main_citations.append(label)
        return label

    # -- panel citations (lowercase, resolved against the plate's own caption) -----------------
    def _panels(self, key: str, panels: str) -> str:
        return panel_suffix(self.captions[key].get("caption", ""), panels, key)

    def figp(self, key: str, panels: str) -> str:
        """'Figure S12c': a supplementary-figure citation with its panel letters."""
        return f"{self.fig(key)}{self._panels(key, panels)}"

    def mfigp(self, key: str, panels: str) -> str:
        """'Figure 3c', 'Figure 5d\u2013e': a main-figure citation with its panel letters."""
        return f"{self.mfig(key)}{self._panels(key, panels)}"

    # -- blocks --------------------------------------------------------------
    def fig_path(self, key: str) -> Path:
        return self._fig_dir[key] / f"{key}.png"

    def tab_path(self, key: str) -> Path:
        return self._tab_dir[key] / f"{key}.csv"

    def figure_block(self, key: str, label: str):
        meta = self.captions[key]
        caption = f"{_strip_prefix(meta.get('title', ''))}. {meta.get('caption', '')}".strip()
        return ("figure", dict(path=self.fig_path(key), caption=caption, label=label))

    def table_block(self, key: str, label: str):
        meta = self.titles[key]
        df = pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False)
        return ("table", dict(df=df, title=_strip_prefix(meta.get("title", "")),
                              note=table_note(key, meta.get("note", ""), df, LANG), label=label))

    def nrows(self, key: str) -> int:
        """Number of data rows of a supplementary table file (a number traceable to that output file)."""
        return len(pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False))

class _Doc:
    def __init__(self):
        self.blocks: list = []

    def add(self, kind, payload):
        self.blocks.append((kind, payload))

    def h1(self, t):
        self.add("h1", t)

    def h2(self, t):
        self.add("h2", t)

    def h3(self, t):
        self.add("h3", t)

    def p(self, t, opt=False):
        self.add("p", (OPT + t) if opt else t)

    def bullets(self, items):
        self.add("bullets", list(items))

# ---------------------------------------------------------------------------
# Manuscript
# ---------------------------------------------------------------------------
def _assemble(variant: str, V: dict):
    if variant not in VARIANT_LABEL:
        raise ValueError(f"unknown variant '{variant}'")
    k = _V(V, variant)
    R = _Registry(variant)
    other = "sin_rett" if variant == "con_rett" else "con_rett"
    vlabel, olabel = VARIANT_LABEL[variant], VARIANT_LABEL[other]
    doc = _Doc()
    y0, y1 = 2019, 2024

    # ---------------- Title page ----------------
    doc.add("title", TITLE)
    doc.add("subtitle", f"Analysis variant: {vlabel}. Running title: {RUNNING_TITLE}.")
    doc.add("authors", dict(authors=[(AUTHOR, "1")], affiliations=[("1", AFFILIATION)],
                            lines=[f"Correspondence: {AUTHOR}, {AUTHOR_EMAIL}",
                                   "Article type: Article (original research). Reporting guidelines: STROBE and RECORD.",
                                   "Word counts, citation keys and figure/table numbering are reported by prose_en.word_counts()."]))

    # ---------------- Summary ----------------
    doc.h1("Summary")
    doc.p("**Background** Recorded autism diagnoses have risen steeply in high-income countries, but Latin American "
          "multisource evidence is scarce. We describe how administrative recognition of autism changed across Chile's "
          "public health and education systems in 2019–2025 and how robust the change is to coverage, coding and "
          "definitions.")
    doc.p("**Methods** National study of unlinked routine data: public-hospital diagnosis-related-group (GRD) episodes and "
          "DEIS discharges (2019–2024), six REM primary and specialty care modules (2019–2025), insurance, primary-care and "
          "population denominators, two complex-design surveys and school registers. We estimated rates per 100,000 GRD "
          "episodes and per population, WHO-standardised rates and quasi-Poisson annual percent changes (APC) with "
          "pre-specified sensitivities.")
    doc.p(f"**Findings** GRD episodes with documented F84 rose from {n0(k('grd_f84_any_n_2019'))} "
          f"({n1(k('grd_f84_any_rate_2019'))} per 100,000 episodes) in 2019 to {n0(k('grd_f84_any_n_2024'))} "
          f"({n1(k('grd_f84_any_rate_2024'))}) in 2024 (APC {n1(k('apc_grd_any_obs'))}%, 95% CI "
          f"{ci(k('apc_grd_any_obs_lo'), k('apc_grd_any_obs_hi'))}; {n1(k('apc_grd_any_sensitivity_min'))}–"
          f"{n1(k('apc_grd_any_sensitivity_max'))}% across specifications); "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} carried F84 only as a secondary diagnosis and mean coding depth "
          f"rose from {n2(k('grd_coding_depth_all_mean_2019'))} to {n2(k('grd_coding_depth_all_mean_2024'))}. Strict-autism "
          f"mental-health entries rose from {n0(k('a05_autism_entries_2021'))} (2021) to {n0(k('a05_autism_entries_2025'))} "
          f"(2025), children with autism under control from {n0(k('p2_tea_dec_2019'))} to {n0(k('p2_tea_dec_2025'))} and "
          f"autistic students in school integration programmes from {n0(k('pie_harmonised_2019'))} to "
          f"{n0(k('pie_harmonised_2025'))}. Surveys reported autism in {pct(k('svy_endide_children_reported_total_pct'), 2)} "
          f"of children aged 2–17 and {pct(k('svy_endide_adults_reported_total_pct'), 2)}–"
          f"{pct(k('svy_encavi_15plus_diagnosed_total_pct'), 2)} of adults and older adolescents.")
    doc.p("**Interpretation** Independent health and education systems recorded a several-fold expansion of administrative "
          "recognition of autism, coinciding with pandemic recovery, reporting expansion, code changes, "
          "deeper coding and, from 2023, Law 21.545. Reporting and coding explain part of the change; the contribution of "
          "underlying epidemiological change cannot be separated. Service capacity and surveillance must keep pace.")
    doc.p("**Funding** None.")

    # ---------------- Research in context ----------------
    doc.add("panel", dict(title="Research in context", items=[
        ("Evidence before this study",
         "We searched PubMed and Crossref on Sept 4, 2026, without language or date restrictions, combining the terms "
         "\"autism\", \"autism spectrum disorder\" or \"pervasive developmental disorder\" with \"administrative data\", "
         "\"register\", \"hospital discharge\", \"surveillance\", \"time trends\", \"prevalence\", \"Chile\" and \"Latin "
         "America\", and we searched on the same date the official portals of the Chilean Ministry of Health (DEIS), FONASA, "
         "the Superintendencia de Salud, the National Statistics Institute, the Ministry of Education, JUNAEB, the Ministry "
         "of Social Development and the Library of the National Congress for data documentation, methodological reports and "
         "the text of Law 21.545; every retained record was verified against its PubMed or Crossref metadata or the official "
         "page. Register-based studies from the UK, Denmark, Sweden and the USA show large increases in recorded autism "
         "diagnoses, attributable largely to diagnostic criteria, service contact and awareness rather than to changes in the "
         "underlying phenotype. Latin American evidence is limited to a few local prevalence surveys, caregiver surveys "
         "documenting diagnostic delay and access barriers and, for Chile, one urban screening-based prevalence estimate and "
         "one school-register-based estimate. No study has examined how several unlinked administrative systems of a Latin "
         "American country recorded autism over the same period, nor quantified how much of the recorded change survives "
         "adjustment for reporting coverage, coding depth and definition breaks."),
        ("Added value of this study",
         "Using every public routine source in Chile that carries an autism code or item (hospital GRD episodes, DEIS "
         "discharges, six REM modules, insurance, primary-care and population denominators, two national surveys and school "
         "registers), with frozen provenance and pre-specified reproduction controls, we show that administrative recognition "
         "of autism rose several-fold between 2019 and 2025 in the hospital, outpatient and educational systems; that the "
         "increases converge in timing and direction despite different units, coverage and definitions; and that coding "
         "depth, reporting expansion and definition changes explain part, but not all, of the recorded change. We separate "
         "stocks from flows, place of care from residence and definition eras from one another, and we report the number of "
         "reporting establishments next to every count."),
        ("Implications of all the available evidence",
         "Administrative recognition is an actionable measure of demand for diagnosis, care and educational support even "
         "when it cannot be read as prevalence. In Chile, and in other segmented Latin American systems, the observed "
         "expansion implies growing needs for diagnostic capacity, primary-care follow-up, rehabilitation and school "
         "integration, and for surveillance that records coverage and coding rules explicitly. Whether the change reflects "
         "unmet need becoming visible or a rising occurrence of autism cannot be resolved with unlinked records; "
         "person-level linkage, validation of codes and repeated population surveys are needed."),
    ]))

    # ---------------- Introduction ----------------
    doc.h1("Introduction")
    doc.p("Autism is estimated to affect about 1% of the world's population [@zeidan2022; @santomauro2025], and recorded "
          "diagnoses have risen steeply over the past two decades in every country with population registers. Register-based "
          "studies in the UK, Denmark and Sweden attribute most of that rise to changes in diagnostic criteria, the inclusion "
          "of outpatient contacts, awareness and service capacity rather than to a change in the underlying phenotype "
          "[@russell2022; @hansen2015; @lundstrom2015], and the multisource surveillance network of the USA continues to "
          "document increasing identified prevalence with linked health and education records [@shaw2025]. The Lancet "
          "Commission on autism called for national data systems able to monitor identification, needs and services "
          "[@lord2022].")
    doc.p("Latin America contributes little to this evidence. Population-based prevalence estimates exist for few countries "
          "[@paula2011; @fombonne2016], caregiver surveys document long diagnostic delays and access barriers "
          "[@montielnava2024], and routinely collected records have rarely been analysed. Chile has a segmented health "
          "system in which the public insurer FONASA covers most of the population and private ISAPRE insurers a shrinking "
          "minority [@becerril2011]; it has one urban prevalence estimate based on screening and clinical confirmation "
          "[@yanez2021], one school-register estimate of autism and unmet special-education needs [@romanurrestarazu2025] "
          "and clinical guidelines for early detection in primary care since 2011 [@minsal2011]. Law 21.545, in force since "
          "March 2023, established rights to inclusion, comprehensive care and protection for autistic people and created "
          "reporting duties for the health and education sectors [@ley21545; @irarrazaval2023].")
    doc.p("Chile's public health and education systems produce several routine datasets that record autism: hospital "
          "diagnosis-related-group (GRD) episodes, hospital discharges (DEIS), monthly statistical reports (REM) covering "
          "detection, counselling, programme entries, populations under control and rehabilitation, the registers of the "
          "School Integration Programme (PIE) and a caregiver survey of whole school cohorts. They differ in unit of "
          "observation, coverage, definitions and reporting rules, are not linked by person and were designed for payment "
          "and management rather than surveillance. Counts derived from them measure administrative recognition, that is, "
          "the recording of an autism code in a contact with a service, not the prevalence or incidence of autism.")
    doc.p("We asked how administrative recognition of autism and the registered demand for services changed between 2019 "
          "and 2025 across Chile's public health and education systems, and how much of the change is robust to variations "
          "in coverage, coding intensity and definitions. The contribution is descriptive: to show whether independent "
          "systems converge, to quantify the threats to comparability and to translate the findings into surveillance and "
          "service-capacity needs for Chile and the region. Law 21.545 is treated as policy context that coincides with "
          "pandemic recovery, expansion of reporting, changes of codes and deeper coding; no effect of the law is estimated.")

    # ---------------- Methods ----------------
    doc.h1("Methods")
    doc.h2("Study design and setting")
    doc.p(f"This is a national multisource descriptive study of routinely collected data, reported according to the STROBE "
          f"statement and its RECORD extension [@vonelm2007; @benchimol2015], with "
          f"sex-disaggregated results following the SAGER guidelines [@heidari2016]. The setting is Chile (projected "
          f"resident population {millions(k('ine_pop_total_2019'))} in 2019 and {millions(k('ine_pop_total_2025'))} in "
          f"2025), whose public network comprises the hospitals of the National Health Services System (SNSS) and mainly "
          f"municipal primary care (APS). The study period is 2019–2025; the hospital sources end in 2024. Two complete "
          f"definition variants were analysed and delivered as separate documents; this document presents the "
          f"{vlabel}. The analysis plan (appendix) was pre-specified before any association was explored, and every "
          f"deviation, assumption and discrepancy is recorded in a decision log.")
    doc.h2("Data sources and units of observation")
    doc.p(f"{R.tab('T1_sources')} and {R.mfig('fig1_dataflow')} describe the sources, their units of observation, "
          f"coverage and definition breaks. Hospital care was measured with the public GRD files published by FONASA, in "
          f"which the unit is one episode (hospitalisation or major ambulatory surgery, CMA; other modalities exist only in "
          f"2019) with up to {n0(k('grd_diagnosis_positions'))} coded diagnoses, from the SNSS hospitals that operate the "
          f"IR-GRD system used since 2020 as a payment mechanism [@cid2024]. The observed panel comprised "
          f"{k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitals in 2019–2024; the {n0(k('grd_fixed_panel_n'))} "
          f"hospitals present in every year form the fixed panel used as a sensitivity, and the "
          f"{n0(k('grd_hospitals_ever_observed_n'))} hospitals ever observed are never treated as a fixed panel. The person identifier changes format between 2020 and 2021, so unique persons "
          f"are counted only within each year. DEIS hospital discharges from all establishments (public and private) were "
          f"used as an external check; DEIS publishes only the principal diagnosis (its second field is the external cause), "
          f"so the only homologous comparison is F84 as principal diagnosis in both sources.")
    doc.p(f"Ambulatory activity was measured with the REM monthly reports, whose unit is one establishment × month × code "
          f"row. Series A modules are flows: A03 (developmental screening in primary care), A27 (counselling and assisted "
          f"referral in the M-CHAT-R/F context, from 2023, counting interventions rather than persons), A05 (entries to and "
          f"discharges from mental-health programmes) and A28 (entries to rehabilitation, from 2023). Series P modules are "
          f"semi-annual stocks of people under control: P2 (children and adolescents with special health-care needs, NANEAS, "
          f"with autism) and P6 (mental-health programmes in primary care and specialty). December is the primary cut and "
          f"June a sensitivity; semesters are never summed. The {n0(k('rem_pathway_codes_n'))} pathway codes were "
          f"verified against the official dictionary of every year ({R.tab('ST2_rem_code_dictionary')}); definition eras "
          f"({R.tab('S_definition_breaks')}) are presented in separate facets and no series crosses a break. Establishments "
          f"reporting each code and year ({R.tab('ST3_rem_reporting_establishments')}) accompany every count.")
    doc.p("Population benchmarks came from two surveys with complex sampling designs: the 2022 National Disability and "
          "Dependence Survey (ENDIDE; autism reported for adults aged 18 years and older and, by the main caregiver, for "
          "children aged 2–17 years, with a physician-confirmation item for children) and the 2023–24 National Quality of "
          "Life and Health Survey (ENCAVI; declared diagnosis of autism spectrum disorder at age 15 years and older). "
          "Educational recognition came from the Ministry of Education reports on the PIE (annual school stock of registered "
          "autistic students, 2019–2025) and the Law 21.545 monitoring report, and from the JUNAEB Student Vulnerability "
          "Survey microdata (caregiver report of a physician-diagnosed autism spectrum disorder in pre-school, grade 1, "
          "grade 5 and grade 9 cohorts; the item exists from 2023 and expansion weights from 2024).")
    doc.p(f"Official sources: GRD files [@fonasa_grd], DEIS discharges [@deis_egresos], REM series A and P [@minsal_rem], "
          f"REM-20 hospital activity [@deis_rem20], INE projections and the 2024 Census [@ine2019; @ine_base2024; "
          f"@ine_censo2024], FONASA beneficiaries and APS enrolment [@fonasa_beneficiarios; @fonasa_aps], ISAPRE "
          f"beneficiaries [@supersalud_isapre], ENDIDE [@endide2022], ENCAVI [@encavi2023], MINEDUC reports "
          f"[@mineduc_apuntes60; @mineduc_sinaces2026] and JUNAEB microdata [@junaeb_eve] are public. Provenance was frozen "
          f"before analysis: {n0(k('prov_artefacts_n'))} source artefacts ({n1(k('prov_gb_total'))} GB) were hashed with "
          f"SHA-256 and documented with unit, period, coverage, geography, columns, stock or flow nature, definition breaks "
          f"and linkage restrictions ({R.tab('ST7_provenance')}); manifests agreed with the files on disk "
          f"({R.tab('ST7b_manifest_checks')}). Source data were never copied into the repository or overwritten.", opt=True)
    doc.h2("Case definitions and definition variants")
    doc.p(f"In the GRD, an episode with documented F84 carries any ICD-10 code of the F84 family in any of "
          f"the {n0(k('grd_diagnosis_positions'))} diagnosis positions; principal F84 (first position) is a separate, more "
          f"specific series, and episodes carrying F84 only in a secondary position are also reported. The two variants "
          f"differ only in Rett syndrome: the {vlabel} versus the {olabel}; F84.0 (childhood autism) alone is reported as a "
          f"strict series identical in both variants ({R.fig('figS1_grd_variants')}, {R.fig('figS2_grd_subcodes')}, "
          f"{R.tab('ST10_grd_f84_subcodes')}). In REM, strict autism is the code {k('strict_autism_code_a05_entry')} "
          f"(entries) and {k('strict_autism_code_a05_exit')} (discharges) in A05 and the codes "
          f"{k('strict_autism_code_p6_primary')} (primary care) and {k('strict_autism_code_p6_specialty')} (specialty) in P6, "
          f"all available from 2021 and identical in both variants; the variant's pervasive-developmental-disorder (PDD) "
          f"family adds Asperger syndrome, childhood disintegrative disorder, unspecified PDD and, in the with-Rett variant "
          f"only, Rett syndrome. The broad PDD codes of 2019–2020, in which Rett syndrome is inseparable, are shown only as "
          f"a labelled sensitivity. P2 (code {k('p2_tea_code')}), A03, A27 and A28 do not depend on the variant. A03 has "
          f"four non-comparable eras: 2019–2022 (M-CHAT performed and altered only among children with a language or social "
          f"alteration at the 18-month check, which is neither coverage nor positivity), 2023–2024 (M-CHAT-R/F risk "
          f"categories and referral), 2024 (children aged 31–59 months) and the 2025 redesign.")
    doc.p("In education, strict autism spectrum disorder (ASD), ASD-Asperger and their harmonised sum are kept as separate "
          "PIE series; the 2022 discrepancy between the two ministerial reports is resolved by an explicit rule (Results). "
          "In JUNAEB, the estimand is the weighted proportion of surveyed students whose caregiver reports a physician-"
          "diagnosed ASD requiring prolonged treatment; levels and years without an item or without a weight are reported "
          "as not estimable, never as zero. In the surveys, the items are reported autism (ENDIDE) and a declared diagnosis "
          "(ENCAVI); neither is equivalent to an administrative code nor to clinical prevalence.", opt=True)
    doc.h2("Denominators and coverage layers")
    doc.p("Four denominator layers answer different questions and were never interchanged: INE projections based on the "
          "2017 Census at 30 June (territorial resident population; the 2024 base and the enumerated 2024 Census only as "
          "sensitivities, never merged within a series); FONASA and ISAPRE December beneficiary stocks (insurance coverage); "
          "validated APS enrolment at December (operational coverage by centre, place of care); and REM-20 hospital "
          "discharges and bed-days (activity and capacity, never a covered population). The primary GRD estimand is the rate "
          "per 100,000 GRD episodes of the same year, panel and activity, which describes the composition of hospital "
          "activity; rates per 100,000 INE residents are a complementary reading in which the numerator is located by place "
          "of care in the public network and the denominator by residence. REM counts are accompanied by the number of "
          "reporting establishments, by rates per reporting establishment and by a stable panel of establishments that "
          "report the code in every year of its era. A comuna crosswalk between INE and DEIS codes used exact normalised "
          "names and explicit aliases only, without fuzzy matching.")
    doc.h2("Statistical analysis")
    doc.p("Rates per 100,000 episodes, discharges or residents carry exact Poisson 95% limits with the denominator treated "
          "as fixed (for a subset of its own denominator these are marginally conservative relative to binomial limits). "
          "Rates per population were directly standardised to the WHO world standard population [@ahmad2001] with "
          "Fay–Feuer gamma intervals [@fay1997]. Annual trends were summarised with quasi-Poisson log-linear models "
          "[@wedderburn1974] with the logarithm of the denominator as offset (GRD episodes, DEIS discharges, INE population, "
          "reporting establishments or total NANEAS according to the estimand; no offset for stocks), from which the annual "
          "percent change (APC) is 100·(exp(β) − 1) with Wald 95% CI; the Pearson dispersion is reported for every model and "
          "residual autocorrelation was checked with the Durbin–Watson statistic, a weak test with three to seven annual "
          "points. GRD hospital-year models added hospital fixed effects with a common trend (hospital-clustered standard "
          "errors as sensitivity) and, separately, a Poisson random intercept per hospital (Laplace approximation); hospital "
          "effects are expressed as rate ratios against the geometric mean of hospitals. Pre-specified covariates were the "
          "mean coding depth (number of coded diagnoses per episode) and an indicator of the 2020–2021 reporting disruption, "
          "which describes the pandemic period and has no causal meaning. Age-adjusted APCs came from age-group × year cells "
          "with age fixed effects and a population offset, overall and by sex.")
    doc.p(f"Survey proportions were estimated with the published weights, strata and primary sampling units of each survey "
          f"as domain ratio estimators keeping all design units, with Taylor-linearised standard errors [@wolter2007], logit "
          f"95% CIs on t with degrees of freedom equal to primary sampling units minus strata, design effects and relative "
          f"standard errors; domains with fewer than 30 unweighted cases are flagged as imprecise and those with a relative "
          f"standard error above 30% are suppressed. JUNAEB proportions used the annual expansion weight; because the "
          f"de-identified files carry no school identifier, their standard errors ignore school clustering and are likely "
          f"too narrow. Convergence across systems is described with indices (first common year 2021 = 100) that are never "
          f"read as comparable levels. Analyses were run in Python 3.14 with pandas, NumPy, SciPy and statsmodels; the "
          f"pipeline, tidy tables and a flat table of every cited quantity ({n0(k('models_n_variant'))} converged model "
          f"specifications per variant) are shared (Data sharing statement). Zero, empty and absent REM rows are distinct "
          f"states (a missing row is \"not reported\" and is never imputed), 2020 was never interpolated, cells with fewer "
          f"than five events are suppressed in territorial tables, and no causal model of Law 21.545 was fitted.")
    doc.p(f"Pre-specified sensitivities were: fixed versus observed hospital panel; all activity versus strict "
          f"hospitalisation with CMA reported separately; any position versus principal F84; adjustment for coding depth and "
          f"stratification by coding-depth band; the 2020–2021 disruption indicator and a 2021–2024 window; unit of "
          f"analysis (national, hospital-year, age × year); the two F84 variants and the F84.0-only series; December versus "
          f"June stocks; all reporting establishments versus the stable panel and rates per reporting establishment; INE "
          f"base 2017 versus base 2024 and Census 2024; and the three PIE series. Zero, empty and absent REM rows are "
          f"distinct states: an establishment with a row counts as reporting even if the value is zero or empty, and a "
          f"missing row is \"not reported\" and is never imputed; 2020 was never interpolated. Cells with fewer than five "
          f"events are suppressed in territorial tables, and survey domains with fewer than 30 cases are flagged. No "
          f"interrupted-time-series or other causal model of Law 21.545 was fitted, because the law coincides with the "
          f"pandemic recovery, the expansion of reporting, code changes and deeper coding and no specification can identify "
          f"its effect.", opt=True)
    doc.h2("Reproducibility controls")
    # Todo total de control lleva su ámbito: en el texto núcleo, la forma breve CR.label(); en el suplemento y en
    # los párrafos opcionales, la frase completa CR.phrase(). Sin el rótulo, este total (plan de análisis) y el del
    # pipeline completo se leían como dos versiones contradictorias de la misma cifra (defecto 9).
    doc.p(f"Before modelling, {n0(k('controls_families_prespecified_n'))} pre-specified control families (hospital and "
          f"REM totals, denominators, survey case counts and educational stocks in the protocol) were reproduced from "
          f"the source files; matches required exact equality for counts and 0.5% or less relative difference for means "
          f"and proportions, and every difference was explained before use; the {n0(k('t8_rows'))} resulting "
          f"indicator-year rows {CR.label(CR.ANALYSIS_PLAN, LANG)} are summarised by family in the Results, "
          f"labelled check rows included "
          # La cita tiene que resolver al ÁMBITO del plan de análisis: la tabla de las 205 filas
          # indicador-año. La Figura S15 y su Tabla S50 cuentan los controles numéricos POR MÓDULO (ámbito
          # pipeline), que la nota del propio estudio prohíbe sumar con estas filas; citarlas aquí era
          # exactamente esa confusión. El resumen por familia se nombra CON PALABRAS («in the Results») y no
          # con una cita: la tabla principal que lo contiene se cita por primera vez en los Resultados, y el
          # orden de primera cita de las tablas principales tiene que ser 1, 2, 3, …
          f"({R.tab('T8_controls')}).")
    doc.h2("Role of the funding source")
    doc.p("There was no funding source for this study. The author had full access to all the data and had final "
          "responsibility for the decision to submit for publication.")
    doc.h2("Ethics")
    doc.p("The study used only public, de-identified aggregated or pseudonymised administrative data and public survey "
          "microdata; no individual was contacted and no person-level linkage was attempted. Under Chilean regulations "
          "such secondary analyses of public data do not require ethics committee approval; the author team should confirm "
          "this statement, or obtain a waiver, before submission.")
    doc.h2("Use of artificial intelligence in the research process")
    doc.p("Large-language-model coding assistants (Claude Code, Anthropic, model Claude Fable 5.1; OpenAI Codex in Visual "
          "Studio Code) were used under the author's direction to write and debug the analysis pipeline and drafts of this "
          "text; the author specified every analysis, ran and reviewed all code and verified every reported number against "
          "the output files (see the AI declaration).")

    # ---------------- Results ----------------
    doc.h1("Results")
    doc.h2("Sources and coverage")
    doc.p(f"{R.mfig('fig1_sources_coverage')} and {R.tab('T1_sources')} summarise the sources, and "
          f"{R.mfig('fig1_dataflow')} answers, source by source, what one row is (a record, which may repeat a "
          f"person, or a person), how many rows enter and survive the autism selection, and what is counted "
          f"against which denominator, with no person-level linkage between systems. The GRD files held "
          f"{n0(k('grd_records_total_2019'))} episodes in "
          f"2019 and {n0(k('grd_records_total_2024'))} in 2024 from {k.series('grd_hospitals_observed_{y}', YEARS_GRD)} "
          f"hospitals; the fixed panel of {n0(k('grd_fixed_panel_n'))} hospitals accounted for "
          f"{ppct(k('grd_records_fixed65_share_2024'))} of the 2024 episodes, {nw(k('grd_hospitals_added_2023_n'))} "
          f"hospitals having joined in 2023 and {nw(k('grd_hospitals_added_2024_only_n'))} more in 2024 "
          f"({R.tab('ST1_grd_hospital_panel')}). Mean coding depth of all episodes rose from "
          f"{n2(k('grd_coding_depth_all_mean_2019'))} to {n2(k('grd_coding_depth_all_mean_2024'))} diagnoses per episode "
          f"and, among episodes with F84, from {n2(k('grd_coding_depth_f84_mean_2019'))} to "
          f"{n2(k('grd_coding_depth_f84_mean_2024'))}. In REM, the establishments reporting strict-autism entries numbered "
          f"{k.series('a05_autism_entries_estab_{y}', YEARS_A05)} in 2021–2025 (a fall of "
          f"{n0(abs(k('a05_autism_entries_estab_change_2025_2024')))} in 2025, when the file may still be incomplete) and "
          f"those reporting the P2 autism stock in December numbered {k.series('p2_tea_dec_estab_{y}', YEARS_REM)} in "
          f"2019–2025. The June 2020 P2 cut fell to {ppct(k('p2_jun_dec_ratio_2020'))} of the December stock because few "
          f"establishments reported during the pandemic ({R.fig('figS5_rem_june_december')}). The enumerated 2024 Census "
          f"population was {ppct(k('ine_ratio_censo2024_base2017_2024'))} of the base-2017 projection used as denominator; "
          f"FONASA covered {pct(k('share_fonasa_ine_pct_2019'))} of residents in 2019 and "
          f"{pct(k('share_fonasa_ine_pct_2025'))} in 2025 while ISAPRE fell from {pct(k('share_isapre_ine_pct_2019'))} to "
          f"{pct(k('share_isapre_ine_pct_2025'))}, and the continuous APS and REM-20 panels retained at least "
          f"{pct(min(k('aps_panel_retention_pct_2025'), k('rem20_panel_retention_pct_2025')))} of their 2025 totals.")

    doc.add("_figure", "fig1_dataflow")
    doc.add("_figure", "fig1_sources_coverage")

    doc.h2("Hospital core: GRD episodes with documented F84")
    doc.p(f"Episodes with documented F84 in any position numbered {k.series('grd_f84_any_n_{y}', YEARS_GRD)} in "
          f"2019–2024, that is {k.rate('grd_f84_any', 2019)} per 100,000 GRD episodes in 2019 and "
          f"{k.rate('grd_f84_any', 2024)} in 2024, a ratio of {n2(k('grd_f84_any_rate_ratio_2024_2019'))} "
          f"({R.mtab('T2_grd_core')}, {R.mfig('fig2_grd_core')}). In the fixed panel of {n0(k('grd_fixed_panel_n'))} hospitals the 2024 count was "
          f"{n0(k('grd_f84_any_fixed65_n_2024'))} "
          f"({n1(k('grd_f84_any_fixed65_rate_2024'))} per 100,000), so the hospitals added in 2023–2024 contributed little "
          f"to the rate. Strict hospitalisation episodes with F84 numbered {n0(k('grd_f84_any_hosp_n_2024'))} in 2024 "
          f"({n0(k('grd_f84_any_hosp_fixed65_n_2024'))} in the fixed "
          f"panel), and CMA episodes with F84 rose from {n0(k('grd_f84_any_cma_n_2019'))} to "
          f"{n0(k('grd_f84_any_cma_n_2024'))}. Episodes with principal F84 were fewer and grew more "
          f"slowly: {k.series('grd_f84_principal_n_{y}', YEARS_GRD)}, from {k.rate('grd_f84_principal', 2019)} to "
          f"{k.rate('grd_f84_principal', 2024)} per 100,000 episodes; in 2024, "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} of the episodes with F84 carried it only as a secondary "
          f"diagnosis. The F84.0-only series, identical in both variants, reached {n0(k('grd_f840_strict_any_n_2024'))} "
          f"episodes in 2024; the alternative variant, the {olabel}, counted {n0(k('grd_f84_any_n_other_variant_2024'))} "
          f"episodes with F84 in any position in 2024, a difference of {n0(k('grd_f84_any_n_rett_only_difference_2024'))} "
          f"episodes carrying F84.2 and no other F84 code.")
    doc.p(f"The increase was not only a by-product of deeper coding: within each coding-depth band the F84 rate rose "
          f"between 2019 and 2024 by a factor of {n1(k('grd_depth_bin_3_rate_ratio_2024_2019'))} (three diagnoses), "
          f"{n1(k('grd_depth_bin_4_rate_ratio_2024_2019'))} (four), {n1(k('grd_depth_bin_5_rate_ratio_2024_2019'))} "
          f"(five), {n1(k('grd_depth_bin_6_7_rate_ratio_2024_2019'))} (six to seven), "
          f"{n1(k('grd_depth_bin_8_10_rate_ratio_2024_2019'))} (eight to ten) and "
          f"{n1(k('grd_depth_bin_11plus_rate_ratio_2024_2019'))} (11 or more), while the share of episodes with eight or "
          f"more diagnoses rose from {ppct(k('grd_depth_share_records_8plus_2019'))} to "
          f"{ppct(k('grd_depth_share_records_8plus_2024'))} ({R.mfigp('fig2_grd_core', 'c')}). Unique persons within each year (identifiers valid "
          f"within the year only) numbered {k.series('grd_f84_any_persons_{y}', YEARS_GRD)}, with "
          f"{n2(k('grd_episodes_per_person_any_2024'))} episodes per person in 2024 ({R.tab('ST8_grd_identifier_audit')}).")
    doc.p(f"In 2024 the highest rate per 100,000 episodes was in the "
          f"{str(k('grd_f84_any_peak_age_group_2024')).replace('-', '–')}-year age group, "
          f"{ppct(k('grd_f84_any_share_age_0_9_2024'))} of episodes with F84 were in children aged 0–9 years and "
          f"{ppct(k('grd_f84_any_share_age_20plus_2024'))} in people aged 20 years or older; the male:female ratio of "
          f"episodes fell from {n2(k('grd_f84_any_mf_ratio_n_2019'))} in 2019 to {n2(k('grd_f84_any_mf_ratio_n_2024'))} in "
          f"2024 ({R.tab('ST9_grd_age_sex')}). Per 100,000 INE residents, episodes with F84 rose from "
          f"{n1(k('grd_pop_any_total_crude_2019'))} (crude) and {k.est_ci_y('grd_pop_any_total_asr', 2019)} (WHO-standardised) "
          f"in 2019 to {n1(k('grd_pop_any_total_crude_2024'))} and {k.est_ci_y('grd_pop_any_total_asr', 2024)} in 2024; "
          f"standardised rates in 2024 were {n1(k('grd_pop_any_male_asr_2024'))} in males and "
          f"{n1(k('grd_pop_any_female_asr_2024'))} in females (ratio {n2(k('grd_pop_any_asr_mf_ratio_2024'))}; "
          f"{R.tab('S_grd_population_rates')}).")
    doc.p(f"Hospitals were heterogeneous: in 2024 the rate ranged from "
          f"{n1(k('grd_hosp2024_rate_min'))} to {n0(k('grd_hosp2024_rate_max'))} per 100,000 episodes (ratio "
          f"{n1(k('grd_hosp2024_rate_ratio_max_min'))}; median {n1(k('grd_hosp2024_rate_median'))}, interquartile range "
          f"{n1(k('grd_hosp2024_rate_q1'))}–{n1(k('grd_hosp2024_rate_q3'))}), with the highest values in paediatric "
          f"hospitals such as {k('grd_hosp2024_top1_name')} ({n0(k('grd_hosp2024_top1_n_f84'))} of "
          f"{n0(k('grd_hosp2024_top1_episodes'))} episodes). In the hospital fixed-effects model "
          f"{n0(k('grd_hosp_rr_fixed_effects_none_n_above1'))} hospitals had a rate ratio above one and "
          f"{n0(k('grd_hosp_rr_fixed_effects_none_n_below1'))} below one, and the random-intercept standard deviation was "
          f"{n2(k('apc_grd_hospital_ri_re_sd'))} on the log scale ({R.fig('figS3_grd_hospital_effects')}, "
          f"{R.tab('S_hospital_rates_2024')}); regional maps by residence and by place of care are ecological and "
          f"uncorrected for inter-regional referrals ({R.fig('figS9_regional_maps')}, {R.tab('S9_regional_rates')}).",
          opt=True)
    doc.p(f"DEIS discharges with F84 as principal diagnosis in all establishments rose from "
          f"{n0(k('deis_f84_principal_n_2019'))} ({k.rate('deis_f84_principal', 2019)} per 100,000 discharges) in 2019 to "
          f"{n0(k('deis_f84_principal_n_2024'))} ({k.rate('deis_f84_principal', 2024)}) in 2024, "
          f"{ppct(k('deis_f84_principal_snss_share_2024'))} of them in SNSS establishments; the ratio of DEIS to GRD "
          f"principal-F84 counts was {n2(k('deis_vs_grd_ratio_f84_principal_2024'))} in 2024, a coverage comparison between "
          f"unlinked registries and not a probability ({R.tab('ST11a_deis_annual')}, "
          f"{R.tab('ST11b_deis_vs_grd')}, {R.fig('figS14_deis_sex_age')}, {R.tab('S14_deis_sex_age')}).", opt=True)
    doc.add("_table", "T2_grd_core")
    doc.add("_figure", "fig2_grd_core")

    doc.h2("Aggregate administrative pathway in primary and specialty care")
    doc.p(f"{R.mtab('T3_rem_pathway')} and {R.mfig('fig3_rem_pathway')} present the REM modules by era with their "
          f"reporting establishments; the panels are "
          f"aggregate indicators of unlinked systems, so no ratio between them represents an individual probability. "
          f"Detection and referral codes in primary care were redefined in 2023, 2024 and 2025, so A03 and A27 are shown by "
          f"era without a continuous series: the M-CHAT-R/F classification of 2023–2024 recorded "
          f"{n0(k('a03_2023_high_2023'))} and {n0(k('a03_2023_high_2024'))} children at high risk, and assisted referrals "
          f"(A27) numbered {k.series('a27_assisted_referral_{y}', YEARS_A27)} interventions in 2023–2025.")
    doc.p(f"In the legacy A03 era, M-CHAT screening among children with a language or social alteration was recorded "
          f"{k.series('a03_legacy_mchat_done_{y}', [2019, 2020, 2021, 2022])} times in 2019–2022 and was altered in "
          f"{k.series('a03_legacy_mchat_altered_{y}', [2019, 2020, 2021, 2022])} of them; in the 2023–2024 era, the "
          f"M-CHAT-R/F risk classification recorded {n0(k('a03_2023_risk_total_2023'))} and "
          f"{n0(k('a03_2023_risk_total_2024'))} results ({n0(k('a03_2023_high_2023'))} and "
          f"{n0(k('a03_2023_high_2024'))} at high risk), {n0(k('a03_2024_31_59_evaluated_2024'))} children aged 31–59 "
          f"months were evaluated in 2024, and the 2025 redesign recorded {n0(k('a03_2025_risk_total_2025'))} risk "
          f"results. A27 counselling interventions numbered {k.series('a27_counselling_{y}', YEARS_A27)} and assisted "
          f"referrals {k.series('a27_assisted_referral_{y}', YEARS_A27)} in 2023–2025.", opt=True)
    doc.p(f"Strict-autism entries to mental-health programmes (A05) rose from {n0(k('a05_autism_entries_2021'))} in 2021 to "
          f"{n0(k('a05_autism_entries_2025'))} in 2025 ({n0(k('a05_autism_entries_total_2021_2025'))} entries over five "
          f"years; {k.series('a05_autism_entries_{y}', YEARS_A05)}), programme discharges from "
          f"{n0(k('a05_autism_exits_2021'))} to {n0(k('a05_autism_exits_2025'))}, and the variant's PDD-family entries "
          f"from {n0(k('a05_family_entries_2021'))} to {n0(k('a05_family_entries_2025'))}. In the stable panel of "
          f"{n0(k('a05_autism_entries_stable_panel_n'))} establishments that reported the code every year, strict-autism "
          f"entries rose from {n0(k('a05_autism_entries_stable_total_2021'))} to "
          f"{n0(k('a05_autism_entries_stable_total_2025'))} ({R.fig('figS6_rem_stable_panel')}, "
          f"{R.tab('S6_stable_panel')}). Per 100,000 residents, strict-autism entries rose from "
          f"{n1(k('a05_autism_pop_total_crude_2021'))} (crude) and {k.est_ci_y('a05_autism_pop_total_asr', 2021)} "
          f"(WHO-standardised) in 2021 to {n1(k('a05_autism_pop_total_crude_2025'))} and "
          f"{k.est_ci_y('a05_autism_pop_total_asr', 2025)} in 2025, with a male:female ratio of standardised rates of "
          f"{n2(k('a05_autism_pop_asr_mf_ratio_2025'))} in 2025 and {ppct(k('a05_autism_entries_share_age_0_9_2025'))} "
          f"of entries in children aged 0–9 years ({R.fig('figS7_rem_education_models')}, "
          f"{R.fig('figS8_a05_age_sex')}, {R.tab('S_a05_standardised_rates')}, {R.tab('ST13_a05_age_sex')}).")
    doc.p(f"The December stock of children and adolescents with autism under control in the NANEAS programme (P2) rose "
          f"from {n0(k('p2_tea_dec_2019'))} in 2019 to {n0(k('p2_tea_dec_2025'))} in 2025 "
          f"({k.series('p2_tea_dec_{y}', YEARS_REM)}; ratio {n1(k('p2_tea_dec_ratio_2025_2019'))}), while reporting "
          f"establishments rose from {n0(k('p2_tea_dec_estab_2019'))} to {n0(k('p2_tea_dec_estab_2025'))}; the June 2025 "
          f"stock was {n0(k('p2_tea_jun_2025'))}. The total NANEAS population, reported from December 2023, was "
          f"{k.series('p2_naneas_dec_{y}', [2023, 2024, 2025])}, so autism accounted for "
          f"{pct(k('p2_tea_share_of_naneas_dec_pct_2023'))} of NANEAS under control in 2023 and "
          f"{pct(k('p2_tea_share_of_naneas_dec_pct_2025'))} in 2025 ({R.tab('ST14_p2_p6_june_december')}, "
          f"{R.tab('S5_june_december')}). In P6, the December stock under control for strict autism rose from "
          f"{n0(k('p6_primary_autism_dec_2021'))} to {n0(k('p6_primary_autism_dec_2025'))} in primary care and from "
          f"{n0(k('p6_specialty_autism_dec_2021'))} to {n0(k('p6_specialty_autism_dec_2025'))} in specialty care "
          f"(2021–2025); the broad PDD stocks of 2019–2020 ({n0(k('p6_primary_broad_dec_2019'))} and "
          f"{n0(k('p6_primary_broad_dec_2020'))} in primary care; {n0(k('p6_specialty_broad_dec_2019'))} and "
          f"{n0(k('p6_specialty_broad_dec_2020'))} in specialty) belong to a different definition and are not joined to "
          f"them. Entries to rehabilitation for autism (A28), reported from 2023, numbered "
          f"{k.series('a28_primary_{y}', YEARS_A27)} at primary level (a {n1(k('a28_primary_ratio_2025_2023'))}-fold rise "
          f"in two years) and {k.series('a28_hospital_{y}', YEARS_A27)} at hospital level. Monthly reporting shows the "
          f"April–September 2020 fall in reporting establishments rather than in persons "
          f"({R.fig('figS13_rem_seasonality')}, {R.tab('S13_rem_seasonality')}); the values plotted in "
          f"{R.mfig('fig3_rem_pathway')} are listed "
          f"in {R.tab('F3_rem_pathway_data')}.")
    doc.add("_table", "T3_rem_pathway")
    doc.add("_figure", "fig3_rem_pathway")

    doc.h2("Coverage and denominator layers")
    doc.p(f"The INE resident population grew from {millions(k('ine_pop_total_2019'), 2)} to "
          f"{millions(k('ine_pop_total_2025'), 2)}; the enumerated 2024 Census population ({n0(k('censo2024_enumerated'))}) "
          f"was {ppct(k('ine_ratio_censo2024_base2017_2024'))} of the base-2017 projection for 2024, so any population rate "
          f"would be about {pct(100 * (1 / k('ine_ratio_censo2024_base2017_2024') - 1), 1)} higher under the Census "
          f"denominator ({R.fig('figS10_denominators')}, {R.tab('S10_denominator_sensitivity')}). FONASA beneficiaries rose "
          f"from {millions(k('fonasa_beneficiaries_2019'), 2)} ({pct(k('share_fonasa_ine_pct_2019'))} of the INE "
          f"population) to {millions(k('fonasa_beneficiaries_2025'), 2)} ({pct(k('share_fonasa_ine_pct_2025'))}) while "
          f"ISAPRE beneficiaries fell from {millions(k('isapre_beneficiaries_2019'), 2)} "
          f"({pct(k('share_isapre_ine_pct_2019'))}) to {millions(k('isapre_beneficiaries_2025'), 2)} "
          f"({pct(k('share_isapre_ine_pct_2025'))}); their sum reached {pct(k('share_fonasa_plus_isapre_ine_pct_2025'))} "
          f"of the projection in 2025, a figure that is not an insurance rate because it mixes December stocks with a June "
          f"projection and omits other regimes ({R.mtab('T4_denominators_coverage')}, {R.fig('figS11_coverage_age_sex')}). APS enrolment grew from "
          f"{millions(k('aps_enrolled_2019'), 2)} in {n0(k('aps_centres_2019'))} centres to "
          f"{millions(k('aps_enrolled_2025'), 2)} in {n0(k('aps_centres_2025'))} centres, and the continuous panel of "
          f"{n0(k('aps_panel_n'))} centres retained {pct(k('aps_panel_retention_pct_2019'))} to "
          f"{pct(k('aps_panel_retention_pct_2025'))} of enrolment; the REM-20 panel of {n0(k('rem20_panel_n'))} "
          f"establishments with 12 reported months every year retained {pct(k('rem20_panel_retention_pct_2019'))} to "
          f"{pct(k('rem20_panel_retention_pct_2025'))} of discharges. The {n0(k('t8_differs'))} differing reproduction "
          f"controls concern the panel definition of strict hospitalisation, placeholder person identifiers and repeated "
          f"source rows, and are listed with the reproduction controls below.", opt=True)
    doc.add("_table", "T4_denominators_coverage")

    doc.h2("Population benchmarks")
    doc.p(f"With the complex design, ENDIDE 2022 estimated reported autism in {k.svy('svy_endide_adults_reported_total')} "
          f"of adults aged 18 years or older (n = {n0(k('svy_endide_adults_reported_total_n'))}; "
          f"{n0(k('svy_endide_adults_reported_total_cases'))} cases; about "
          f"{n0(k('svy_endide_adults_reported_total_weighted_total'))} persons) and in "
          f"{k.svy('svy_endide_children_reported_total')} of children and adolescents aged 2–17 years (n = "
          f"{n0(k('svy_endide_children_reported_total_n'))}; {n0(k('svy_endide_children_reported_total_cases'))} cases; "
          f"about {n0(k('svy_endide_children_reported_total_weighted_total'))} persons), of whom "
          f"{k.svy('svy_endide_children_confirmed_among_reported_total', 1)} had a physician-confirmed diagnosis, giving "
          f"{k.svy('svy_endide_children_reported_confirmed_total')} of all children with reported and confirmed autism. "
          f"Reported autism in children was {pct(k('svy_endide_children_reported_male_pct'), 2)} in boys and "
          f"{pct(k('svy_endide_children_reported_female_pct'), 2)} in girls. ENCAVI 2023–24 estimated a declared diagnosis "
          f"of autism spectrum disorder in {k.svy('svy_encavi_15plus_diagnosed_total')} of persons aged 15 years or older "
          f"(n = {n0(k('svy_encavi_15plus_diagnosed_total_n'))}; {n0(k('svy_encavi_15plus_diagnosed_total_cases'))} cases; "
          f"design effect {n2(k('svy_encavi_15plus_diagnosed_total_deff'))}). Most sex and age domains are imprecise and are "
          f"reported only as orders of magnitude ({R.mtab('T5_survey_benchmarks')}, {R.mfigp('fig4_triangulation', 'c')}, "
          f"{R.tab('ST5_survey_items')}). These benchmarks are "
          f"self- or caregiver-reported and are not a validation of administrative codes.")
    doc.add("_table", "T5_survey_benchmarks")

    doc.h2("Educational triangulation")
    doc.p(f"Autistic students registered in the PIE rose from {n0(k('pie_tea_strict_2019'))} (strict ASD) and "
          f"{n0(k('pie_tea_asperger_2019'))} (ASD-Asperger) in 2019 to {n0(k('pie_tea_strict_2023'))} and "
          f"{n0(k('pie_tea_asperger_2023'))} in 2023, when strict ASD represented "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2023'))} of all PIE students against "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2019'))} in 2019; the harmonised ASD + Asperger series was "
          f"{k.series('pie_harmonised_{y}', YEARS_REM)} in 2019–2025 (ratio {n2(k('pie_harmonised_ratio_2025_2019'))}), "
          f"with 2024–2025 from the Law 21.545 monitoring report. For 2022 that report prints "
          f"{n0(k('pie_2022_sinaces_printed'))}, whereas its total of autistic students minus special schools "
          f"({n0(k('sinaces_total_autistic_students_2022'))} − {n0(k('special_schools_autism_2022'))} = "
          f"{n0(k('pie_2022_sinaces_total_minus_special'))}) coincides with the ministerial series; the difference of "
          f"{nw(k('pie_2022_discrepancy_cases'))} students was resolved in favour of the disaggregated source. Autistic "
          f"students in special schools numbered {k.series('special_schools_autism_{y}', [2022, 2023, 2024, 2025])} and the "
          f"total registered autistic students {n0(k('sinaces_total_autistic_students_2022'))} in 2022 and "
          f"{n0(k('sinaces_total_autistic_students_2025'))} in 2025 ({R.mtab('T6_education')}, "
          f"{R.mfigp('fig4_triangulation', 'a')}).")
    doc.p(f"In JUNAEB's whole-cohort caregiver survey, the weighted percentage of students with a reported physician "
          f"diagnosis of ASD was {pct(k('junaeb_parvularia_all_pct_weighted_2024'), 2)} in pre-school, "
          f"{pct(k('junaeb_basico1_all_pct_weighted_2024'), 2)} in grade 1 and "
          f"{pct(k('junaeb_basico5_all_pct_weighted_2024'), 2)} in grade 5 in 2024 (grade 9 not estimable because the "
          f"item is empty in the published file), and {pct(k('junaeb_parvularia_all_pct_weighted_2025'), 2)}, "
          f"{pct(k('junaeb_basico1_all_pct_weighted_2025'), 2)}, {pct(k('junaeb_basico5_all_pct_weighted_2025'), 2)} and "
          f"{pct(k('junaeb_medio1_all_pct_weighted_2025'), 2)} in 2025, with male:female ratios between "
          f"{n1(k('junaeb_medio1_mf_ratio_2025'))} (grade 9) and {n1(k('junaeb_basico1_mf_ratio_2025'))} (grade 1) "
          f"({R.fig('figS12_junaeb_sex_level')}, {R.tab('S12_junaeb_sex_level')}, {R.tab('ST6_junaeb_items')}). The "
          f"2019–2022 questionnaires had no ASD item and 2023 has no published weight, so no JUNAEB trend before 2024 can "
          f"be estimated; these proportions describe selected school cohorts and caregiver report, not national prevalence.")
    doc.add("_table", "T6_education")
    doc.add("_figure", "fig4_triangulation")

    doc.h2("Convergence across systems and sensitivity of the trends")
    doc.p(f"Indexed to 2021 = 100, the GRD rate of episodes with F84 stood at {n0(k('conv_grd_any_rate_index2021_2024'))} "
          f"in 2024, the DEIS principal-F84 rate at {n0(k('conv_deis_principal_rate_index2021_2024'))}, strict-autism A05 "
          f"entries at {n0(k('conv_a05_strict_entries_index2021_2025'))} in 2025, the P2 December stock at "
          f"{n0(k('conv_p2_december_stock_index2021_2025'))}, the P6 primary-care stock at "
          f"{n0(k('conv_p6_primary_strict_stock_index2021_2025'))} and the harmonised PIE at "
          f"{n0(k('conv_pie_harmonised_index2021_2025'))} ({R.mfigp('fig4_triangulation', 'd-e')}, {R.tab('S_convergence_index')}, "
          f"{R.tab('F4_triangulation_series')}); the indices share direction and timing, with the steepest increases in "
          f"2022–2024, but not units, denominators or definitions.")
    doc.p(f"{R.mtab('T7_models')} gives the pre-specified models. The APC of GRD episodes with F84 per 100,000 episodes was "
          f"{k.apc('apc_grd_any_obs')} in the observed panel (Pearson dispersion {n1(k('apc_grd_any_obs_disp'))}) and "
          f"{k.apc('apc_grd_any_fixed65')} in the fixed panel; "
          f"adjustment for mean coding depth raised it to {k.apc('apc_grd_any_obs_depth')}, the 2020–2021 disruption "
          f"indicator lowered it to {k.apc('apc_grd_any_obs_disruption')}, the 2021–2024 window gave "
          f"{k.apc('apc_grd_any_obs_2021_2024')} and strict hospitalisation {k.apc('apc_grd_any_hosp')}; across the "
          f"{n0(k('apc_grd_any_sensitivity_n_specs'))} specifications the APC ranged from "
          f"{n1(k('apc_grd_any_sensitivity_min'))}% to {n1(k('apc_grd_any_sensitivity_max'))}%. Principal F84 grew at "
          f"{n1(k('apc_grd_principal_obs'))}% (95% CI {ci(k('apc_grd_principal_obs_lo'), k('apc_grd_principal_obs_hi'))}; "
          f"{n1(k('apc_grd_principal_sensitivity_min'))}–{n1(k('apc_grd_principal_sensitivity_max'))}% across "
          f"specifications). Hospital-year models with hospital fixed "
          f"effects gave {n1(k('apc_grd_hospital_fe'))}% (hospital-clustered 95% CI {ci(k('apc_grd_hospital_fe_cluster_lo'), k('apc_grd_hospital_fe_cluster_hi'))}) "
          f"and the random-intercept model {n1(k('apc_grd_hospital_ri'))}%; each additional coded diagnosis per episode was "
          f"associated with a rate ratio of {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} within hospitals. "
          f"Per 100,000 residents the age-adjusted APC was {k.apc('apc_grd_pop_any_total_ageadj')}, higher in females "
          f"({n1(k('apc_grd_pop_any_female_ageadj'))}%) than in males ({n1(k('apc_grd_pop_any_male_ageadj'))}%). DEIS "
          f"principal-F84 discharges grew at {n1(k('apc_deis_principal'))}% (95% CI "
          f"{ci(k('apc_deis_principal_lo'), k('apc_deis_principal_hi'))}; {R.mfigp('fig4_triangulation', 'f')}, "
          f"{R.fig('figS4_models_cpa')}, "
          f"{R.tab('T7_models_cpa_full')}). In REM and education, the APC was {n1(k('apc_a05_autism_estab'))}% per "
          f"reporting establishment for strict-autism entries ({n1(k('apc_a05_autism_pop'))}% per resident), "
          f"{n1(k('apc_p2_dec_estab'))}% per establishment for the P2 December stock ({n1(k('apc_p2_dec'))}% as a count), "
          f"{n1(k('apc_p6_primary_autism_estab'))}% per establishment for the P6 primary-care stock and "
          f"{k.apc('apc_pie_harmonised')} for the harmonised PIE stock.")
    doc.p(f"Strict-autism A05 entries grew at {k.apc('apc_a05_autism_pop')} per 100,000 residents (dispersion "
          f"{n1(k('apc_a05_autism_pop_disp'))}), "
          f"{k.apc('apc_a05_autism_estab')} per reporting establishment, {k.apc('apc_a05_autism_stable_pop')} in the "
          f"stable panel and {k.apc('apc_a05_autism_ageadj_total')} after age adjustment ({n1(k('apc_a05_autism_ageadj_female'))}% "
          f"in females, {n1(k('apc_a05_autism_ageadj_male'))}% in males). The P2 December stock grew at "
          f"{k.apc('apc_p2_dec')} as a count, {k.apc('apc_p2_dec_estab')} per reporting establishment, "
          f"{k.apc('apc_p2_dec_stable')} in the stable panel of {n0(k('p2_tea_dec_stable_panel_n'))} establishments and "
          f"{k.apc('apc_p2_dec_naneas_offset')} per 100 NANEAS under control (2023–2025). The P6 strict-autism stocks grew "
          f"at {k.apc('apc_p6_primary_autism')} in primary care ({n1(k('apc_p6_primary_autism_estab'))}% per "
          f"establishment) and {k.apc('apc_p6_specialty_autism')} in specialty care "
          f"({n1(k('apc_p6_specialty_autism_estab'))}% per establishment). The harmonised PIE stock grew at "
          f"{n1(k('apc_pie_harmonised'))}% (95% CI {ci(k('apc_pie_harmonised_lo'), k('apc_pie_harmonised_hi'))}; "
          f"2019–2025; {n1(k('apc_pie_harmonised_2019_2023'))}% for the ministerial series alone), with strict ASD at "
          f"{n1(k('apc_pie_tea_strict'))}% and ASD-Asperger at "
          f"{n1(k('apc_pie_tea_asperger'))}% in 2019–2023. Dispersion was large in the count models of flows and stocks, "
          f"and no specification estimates an effect of Law 21.545.", opt=True)
    doc.p(f"The {n0(k('t8_rows'))} reproduction controls {CR.label(CR.ANALYSIS_PLAN, LANG)} ({n0(k('t8_ok'))} matched, "
          f"{n0(k('t8_differs'))} differed, all documented) are listed by family in {R.mtab('T8_controls_compact')} "
          f"({R.tab('T8_controls')}).")
    doc.add("_table", "T7_models")
    doc.add("_table", "T8_controls_compact")

    # ---------------- Discussion ----------------
    junaeb_levels = ("parvularia", "basico1", "basico5", "medio1")
    junaeb_2025 = [k(f"junaeb_{lvl}_all_pct_weighted_2025") for lvl in junaeb_levels]
    junaeb_min, junaeb_max = min(junaeb_2025), max(junaeb_2025)
    junaeb_mf = [k(f"junaeb_{lvl}_mf_ratio_2025") for lvl in junaeb_levels]
    junaeb_mf_min, junaeb_mf_max = min(junaeb_mf), max(junaeb_mf)
    doc.h1("Discussion")
    doc.p(f"Across Chile's public hospital, primary-care, specialty and education systems, administrative recognition of "
          f"autism expanded several-fold between 2019 and 2025: {n1(k('grd_f84_any_rate_ratio_2024_2019'))}-fold in the "
          f"rate of GRD episodes with documented F84, {n1(k('a05_autism_entries_ratio_2025_2021'))}-fold in strict-autism "
          f"programme entries in four years, {n1(k('p2_tea_dec_ratio_2025_2019'))}-fold in the December stock of children "
          f"with autism under control and {n1(k('pie_harmonised_ratio_2025_2019'))}-fold in registered autistic students, "
          f"with a trough or plateau in 2020 and the steepest increases in 2022–2024. The increases survive restriction to a "
          f"fixed hospital panel and to stable establishment panels, stratification by coding depth and adjustment for the "
          f"pandemic disruption, although their magnitude changes: the GRD APC spans "
          f"{n1(k('apc_grd_any_sensitivity_min'))}–{n1(k('apc_grd_any_sensitivity_max'))}% across specifications, A05 "
          f"entries grow at {n1(k('apc_a05_autism_estab'))}% per reporting establishment against "
          f"{n1(k('apc_a05_autism_pop'))}% per resident, and the P2 stock at {n1(k('apc_p2_dec_estab'))}% per "
          f"establishment against {n1(k('apc_p2_dec'))}% as a count.")
    doc.p(f"Three constructs must be separated. Administrative recognition is the recording of a code; registered demand "
          f"is the volume of contacts that carry it; underlying epidemiology is the occurrence of autism in the population. "
          f"Our data measure the first two. In the GRD, {pct(k('grd_f84_secondary_only_share_2024_pct'))} of episodes with "
          f"F84 in 2024 carried it as a secondary diagnosis and principal F84 grew at {n1(k('apc_grd_principal_obs'))}% "
          f"against {n1(k('apc_grd_any_obs'))}% for any position, so most of the hospital signal is the documentation of "
          f"autism in episodes admitted for other reasons; the number of coded diagnoses per episode is known to change what "
          f"administrative data capture [@iezzoni1992], and mean depth rose by "
          f"{pct(100 * (k('grd_coding_depth_all_mean_ratio_2024_2019') - 1), 0)} over the period. Yet the rate rose within "
          f"every coding-depth band and each additional diagnosis explained only a rate ratio of "
          f"{n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} within hospitals, so deeper coding accounts for "
          f"part of the change and not for the whole of it. In the REM, the gap between the growth per establishment and the "
          f"growth per resident quantifies the contribution of reporting expansion, and stocks under control accumulate "
          f"people over time by construction. Coding depth, reporting expansion, definition changes and diagnostic intensity "
          f"vary across places and are themselves determinants of recorded rates [@song2010]; the {n0(k('grd_hosp2024_rate_ratio_max_min'))}-fold "
          f"range across hospitals in 2024 reflects case-mix (paediatric hospitals lead) as much as practice.")
    doc.p(f"The convergence across independent systems is informative even though the systems do not measure the same "
          f"thing. Hospital episodes, programme entries, stocks under control and school registers share timing and "
          f"direction, a concentration in early childhood ({ppct(k('grd_f84_any_share_age_0_9_2024'))} of GRD episodes and "
          f"{ppct(k('a05_autism_entries_share_age_0_9_2025'))} of A05 entries in children aged 0–9 years) and a falling "
          f"male:female ratio (from {n1(k('grd_f84_any_mf_ratio_n_2019'))} to {n1(k('grd_f84_any_mf_ratio_n_2024'))} in "
          f"GRD episodes; {n1(k('a05_autism_pop_asr_mf_ratio_2025'))} in standardised A05 entries; "
          f"{n1(junaeb_mf_min)}–{n1(junaeb_mf_max)} in JUNAEB cohorts), with "
          f"faster growth in females in the age-adjusted models. A ratio approaching 2:1 is below the 3:1 of active "
          f"ascertainment and the 4:1 of passive samples [@loomes2017] and is consistent with expanding recognition of "
          f"autism in girls and women, although administrative data cannot show whether it reflects earlier under-recognition "
          f"or a changing population.")
    doc.p(f"The falling sex ratio is also documented in prospective birth cohorts, in which the male-to-female ratio of "
          f"autism incidence has declined over time, and has been linked to the female autism phenotype and camouflaging "
          f"[@fyfe2026; @lai2020; @hull2020]; the survey benchmark in Chilean children "
          f"({n1(k('svy_endide_children_reported_male_pct') / k('svy_endide_children_reported_female_pct'))}:1 in ENDIDE) "
          f"is nearer the passive-ascertainment values than the administrative flows of 2024–2025.", opt=True)
    doc.p(f"Internationally, the pattern resembles what registers showed in earlier decades elsewhere. In UK primary care, "
          f"recorded autism diagnoses rose 787% between 1998 and 2018, most steeply in adults and females [@russell2022]; in "
          f"Denmark, 60% of the increase in prevalence was attributable to changes in diagnostic criteria and to the "
          f"inclusion of outpatient contacts [@hansen2015]; in Sweden, registered diagnoses rose steeply over ten years while "
          f"the population phenotype remained stable [@lundstrom2015]; and in the USA, the multisource surveillance of "
          f"eight-year-olds reached one in 31 children in 2022 with persistent differences between sites in identification "
          f"rather than in occurrence [@shaw2025]. The Chilean annual changes of "
          f"{n0(k('apc_grd_any_sensitivity_min'))}–{n0(k('apc_grd_any_sensitivity_max'))}% in hospital episodes and "
          f"{n0(k('apc_a05_autism_estab'))}–{n0(k('apc_a05_autism_pop'))}% in programme entries are far above the long-run "
          f"rates of those countries, as expected of a system catching up from a low level of recognition; the "
          f"survey benchmarks of {pct(k('svy_endide_children_reported_confirmed_total_pct'), 1)}–"
          f"{pct(k('svy_endide_children_reported_total_pct'), 1)} in children are of the order of the identified prevalence "
          f"in high-income countries, whereas the administrative flows and stocks remain far below what those benchmarks "
          f"imply.")
    doc.p(f"In Latin America, population surveys in Brazil and Mexico estimated prevalences of roughly 0.3% and 0.9% "
          f"[@paula2011; @fombonne2016], and a six-country study that included Chile documented late diagnosis and the role "
          f"of public coverage [@montielnava2024]. Chile's system is segmented by insurer and by provider: the public network "
          f"we observed serves the residents insured by FONASA ({pct(k('share_fonasa_ine_pct_2025'), 0)} of the population "
          f"in 2025), but care purchased privately, care in ISAPRE networks and the armed forces are invisible to GRD and "
          f"REM, and Chilean "
          f"caregivers report that access to diagnosis and services differs by insurance and by region [@garcia2022]. "
          f"Administrative recognition therefore depends on supply: it grows where paediatric hospitals, mental-health teams "
          f"and screening programmes exist, and the geography of place of care differs from the geography of residence.")
    doc.p("The segmentation of Chilean health insurance between FONASA and ISAPRE, and its consequences for access and "
          "hospital performance, have been analysed elsewhere [@romanurrestarazu2018; @cid2016]; early childhood "
          "development policy has expanded developmental screening in primary care but with gaps in follow-up for children "
          "with developmental disabilities [@breinbauer2022], and REM data have already been used to describe the fall and "
          "recovery of well-child visits around the pandemic [@acevedo2025].", opt=True)
    doc.p(f"The implications are practical. Every stage of the public pathway is under pressure: screening and referral "
          f"codes have been redesigned three times since 2023, strict-autism programme entries reached "
          f"{n0(k('a05_autism_entries_2025'))} in 2025, primary-care stocks under control multiplied by "
          f"{n1(k('p6_primary_autism_dec_ratio_2025_2021'))} in four years, entries to primary-level rehabilitation rose "
          f"{n1(k('a28_primary_ratio_2025_2023'))}-fold in two years, and autistic students represent "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2023'))} of PIE registrations (2023) and {pct(junaeb_min)}–"
          f"{pct(junaeb_max)} of the school cohorts surveyed in 2025. Diagnostic capacity, primary-care follow-up, "
          f"rehabilitation and school integration need "
          f"to be planned for a demand that is still rising, and the monitoring required by Law 21.545 should be built on "
          f"indicators that report the number of reporting establishments, the definition era and the coding rule next to "
          f"every count, and should move towards person-level linkage with proper safeguards so that recognition can be "
          f"distinguished from re-contacts and from accumulation of stocks.")
    doc.p(f"This study has limitations. The COVID-19 pandemic depressed activity and reporting in 2020–2021 and its recovery "
          f"overlaps with every later change, so the disruption indicator describes rather than corrects it. Taxonomic "
          f"breaks (broad PDD to categories in 2021; four A03 eras; the JUNAEB item from 2023) truncate series, and the REM "
          f"2025 file may be incomplete ({n0(k('a05_autism_entries_estab_2025'))} establishments against "
          f"{n0(k('a05_autism_entries_estab_2024'))} in 2024). Coverage and panels changed: the GRD gained seven hospitals, "
          f"REM reporting establishments multiplied, and stable panels are conservative sensitivities rather than "
          f"representative series. Numerators are located by place of care and denominators by residence, so population "
          f"rates are complementary readings and regional comparisons are ecological. Coding depth rose and cannot be fully "
          f"adjusted for. Sources are not linked by person, so no trajectory, cascade or conversion ratio can be estimated "
          f"and persons are unique only within a year. Recognition depends on access to the public network, which introduces "
          f"selection by insurance, region and age. No code was validated against clinical assessment, and the surveys, with "
          f"few cases and different wording, are benchmarks rather than validation. The series are short (three to seven "
          f"points), so trend models are descriptive and the dispersion is large; survey variances are approximate (ENDIDE "
          f"pseudo-strata; JUNAEB without clustering).")
    doc.p(f"Its strengths are national coverage of every public source with an autism code or item, frozen provenance with "
          f"SHA-256 hashes, {n0(k('t8_rows'))} pre-specified reproduction controls {CR.phrase(CR.ANALYSIS_PLAN, LANG)} "
          f"with every difference explained, a "
          f"pre-specified analysis plan with two complete definition variants and a comprehensive set of sensitivities, "
          f"exact and design-based intervals throughout, and a strict separation of stocks from flows, of place of care from "
          f"residence, of definition eras and of the four denominator layers, without any claim of individual linkage.",
          opt=True)
    doc.p("We cannot separate the contribution of a genuine change in the occurrence of autism from the contributions of "
          "awareness, care-seeking, service supply, coverage, coding depth and definitions. The observed convergence "
          "establishes that recognition and registered demand rose in every system; it does not establish that autism "
          "became more frequent, and the coincidence of Law 21.545 with the other changes precludes any attribution to the "
          "law.")
    doc.h1("Conclusion")
    doc.p("Between 2019 and 2025, Chile's public health and education systems recorded a several-fold expansion of "
          "administrative recognition of autism that converges in timing and direction across unlinked hospital, "
          "primary-care, specialty, rehabilitation and school registers, and that is partly, but not wholly, explained by "
          "reporting expansion, coding depth and definition changes. For Chile and for other segmented Latin American "
          "systems, these counts are a measure of demand that services and surveillance must plan for, not a measure of "
          "prevalence.")

    # ---------------- Declarations ----------------
    doc.h1("Contributors")
    doc.p(f"{AUTHOR} conceived the study, wrote the analysis plan, obtained and curated the data, wrote the analysis "
          f"pipeline, verified the reproduction controls, produced the figures and tables, interpreted the results and wrote "
          f"the manuscript. The journal requires that more than one author directly accessed and verified the underlying "
          f"data: before submission a second author must be added who independently accesses the source files listed in the "
          f"provenance table, re-runs the pipeline and verifies the values reported in the text and in "
          f"{R.mtab('T8_controls_compact')}. All authors "
          f"will have full access to all the data and accept responsibility for the decision to submit for publication.")
    doc.h1("Declaration of interests")
    doc.p("The author declares no competing interests. [Each author will complete the ICMJE disclosure form at submission.]")
    doc.h1("Data sharing statement")
    doc.p(f"All source data are public ({R.tab('T1_sources')}, together with the provenance table, lists the providers, "
          f"files, versions and SHA-256 "
          f"hashes). The derived tidy tables ({n0(k('n_tables_supp_files_en'))} supplementary and "
          f"{n0(k('n_tables_main_en'))} main table files per variant and language), the flat table of every quantity cited "
          f"in the text, the model outputs, the analysis plan, the decision log, the reporting checklist and the complete "
          f"Python pipeline that reproduces every figure and table from the source files will be deposited in a public "
          f"repository with a persistent identifier (URL and DOI to be inserted at acceptance) and are available from the "
          f"corresponding author now; access is open under a permissive licence, without restriction, from the date of "
          f"publication. No person-level data are redistributed: the GRD, REM, DEIS, survey and JUNAEB microdata must be "
          f"obtained from the official portals cited.")
    doc.h1("Funding")
    doc.p("None.")
    doc.h1("Acknowledgements")
    doc.p("We thank the Department of Health Statistics and Information (DEIS) of the Ministry of Health, FONASA, the "
          "Superintendencia de Salud, the National Statistics Institute, the Ministry of Education, JUNAEB and the Ministry "
          "of Social Development and Family for publishing the data used in this study.")
    doc.h1("Declaration of the use of artificial intelligence")
    doc.p("In accordance with the journal's policy, the author declares that large-language-model assistants were used in "
          "this work: Claude Code (Anthropic; model Claude Fable 5.1, claude-fable-5-1) and OpenAI Codex (Visual Studio Code "
          "extension; version to be confirmed by the author). Purpose and scope: writing and debugging the Python analysis "
          "pipeline, the figure and table scripts and the document builder; drafting and editing this manuscript, its "
          "summary, the Research in context panel and the supplementary appendix from the computed outputs; and verifying "
          "bibliographic metadata against PubMed, Crossref and official pages. Supervision: the author specified every "
          "analysis and rule, reviewed and executed all code, verified every reported number against the output files and "
          "the reproduction controls, checked every reference against its source and edited the final text; the tools did "
          "not generate or alter data, images or references, and they are not authors. Prompts are available on request.")
    doc.add("refs", None)

    article_blocks = _expand(doc.blocks, R)
    R.article_citations = len(R.main_citations)

    # ---------------- Supplementary part (shared by the manuscript and the standalone appendix) ----------------
    supp = _Doc()
    supp.h1("Supplementary methods")
    supp.h2("S1. Sources, codes and definition eras")
    supp.p(f"The study uses the {vlabel}; the alternative document uses the {olabel}. GRD subcodes in this variant: "
           f"{k('variant_grd_subcodes')}. REM strict-autism codes: {k('strict_autism_code_a05_entry')} (A05 entries), "
           f"{k('strict_autism_code_a05_exit')} (A05 discharges), {k('strict_autism_code_p6_primary')} (P6 primary care) "
           f"and {k('strict_autism_code_p6_specialty')} (P6 specialty); variant PDD family: A05 entries "
           f"{codes(k('a05_family_codes_entry'))}, A05 discharges {codes(k('a05_family_codes_exit'))}, P6 primary care "
           f"{codes(k('p6_family_codes_primary'))}, P6 specialty {codes(k('p6_family_codes_specialty'))}; P2 autism "
           f"{k('p2_tea_code')} and total NANEAS {k('p2_naneas_total_code')} (from December 2023); A27 "
           f"{codes(k('a27_codes'))}; A28 {codes(k('a28_codes'))}. The {n0(k('rem_pathway_codes_n'))} codes were checked against the "
           f"official dictionary of each year ({R.tab('ST2_rem_code_dictionary')}); definition, panel and schema breaks by "
           f"source are listed in {R.tab('S_definition_breaks')}; reporting establishments by code and year in "
           f"{R.tab('ST3_rem_reporting_establishments')}; the hospital panel in {R.tab('ST1_grd_hospital_panel')}; the GRD "
           f"identifier audit in {R.tab('ST8_grd_identifier_audit')}; F84 subcodes by position in "
           f"{R.tab('ST10_grd_f84_subcodes')}; and the full provenance in {R.tab('ST7_provenance')} and "
           f"{R.tab('ST7b_manifest_checks')} [@fonasa_grd; @deis_egresos; @minsal_rem; @deis_rem20; @ine2019; "
           f"@ine_base2024; @ine_censo2024; @fonasa_beneficiarios; @fonasa_aps; @supersalud_isapre; @endide2022; "
           f"@encavi2023; @mineduc_apuntes59; @mineduc_apuntes60; @mineduc_sinaces2026; @junaeb_eve; @who_icd10; "
           f"@deis_establecimientos].")
    supp.p("A03 eras (never joined): 2019–2022 legacy codes 03500406 (M-CHAT performed) and 03500407 (M-CHAT altered), "
           "restricted to children with a language or social alteration at the 18-month control; 2023–2024 family "
           "09600212–09600219 (M-CHAT-R/F part 1 by low, medium and high risk; high risk referred; part 2 with and "
           "without referral); 2024 codes 03700104–03700109 (children aged 31–59 months: evaluated, suspected elsewhere, "
           "alert signs, referral); 2025 redesign 03710013–03710021 (motives at 16–30 months, risk result and referral "
           "need, suspicion at 30–59 months). A05 2019–2020 broad PDD (06902600 entries, 05225000 discharges) and P6 "
           "2019–2020 broad PDD (P6223000 primary care, P6223380 specialty) contain Rett syndrome inseparably and are "
           "shown only as labelled sensitivities. A27 counts interventions, not persons. Stocks (P2, P6) are December "
           "values with June as sensitivity and are never summed; total NANEAS is not reported in June 2023 (no rows, not "
           "zero).")
    supp.h2("S2. Estimands, denominators and models")
    supp.p(f"Primary hospital estimand: episodes with documented F84 (any of the {n0(k('grd_diagnosis_positions'))} "
           f"diagnosis positions) per 100,000 GRD "
           f"episodes of the same year, panel and activity, with exact Poisson limits; principal F84, strict hospitalisation, "
           f"CMA, fixed panel of {n0(k('grd_fixed_panel_n'))} hospitals, coding-depth strata, persons within year and INE "
           f"population rates by age and "
           "sex (WHO world standard, Fay–Feuer intervals [@ahmad2001; @fay1997]) as sensitivities. Trend family: "
           "quasi-Poisson log-linear regression [@wedderburn1974; @mccullagh1989] of the count on calendar year with the "
           "logarithm of the denominator as offset; APC = 100·(exp(β) − 1) with Wald 95% CI [@clegg2009]; Pearson "
           "dispersion; Durbin–Watson on deviance residuals. Hospital-year models: hospital fixed effects with a common "
           "trend and log(hospital-year episodes) offset (hospital-clustered standard errors as sensitivity), hospital "
           "effects expressed as rate ratios against the geometric mean; Poisson random intercept per hospital fitted by "
           "Laplace approximation with the offset added to the linear predictor (variational Bayes as fallback), reported "
           "as a sensitivity because it ignores overdispersion. Covariates: mean coding depth (hospital-year or national) and "
           "the 2020–2021 reporting-disruption indicator; windows 2019–2024 and 2021–2024. Age-adjusted APCs: age-group × "
           "year cells with age fixed effects and log(population) offset. Comuna-level maps were computed: the comuna "
           "ratio is internally indirectly standardised by age and sex and smoothed with Marshall's global "
           "empirical-Bayes estimator [@breslow1987; @marshall1991], and the territorial analysis adds global and "
           "bivariate Moran's I, LISA and Getis–Ord Gi* under a Benjamini–Hochberg threshold, Lorenz/Gini and Theil "
           "decompositions, rank stability and the association with small-area deprivation "
           f"({SM._range([R.fig('E40_maps_grd_smoothed_ratio'), R.fig('E49_regional_summary')])}, "
           f"{SM._range([R.tab('E40_grd_smoothed_ratio_comuna'), R.tab('E51_lisa_significant_comunas')])}), with every "
           f"territorial cell below five suppressed; the regional maps of {R.fig('figS9_regional_maps')} are crude "
           "rates by residence (GRD) and by place of care (A05). "
           f"The full set of {n0(k('models_n_variant'))} converged specifications per variant is in "
           f"{R.tab('T7_models_cpa_full')} and summarised in {R.fig('figS4_models_cpa')}; hospital effects in "
           f"{R.fig('figS3_grd_hospital_effects')} and {R.tab('S_hospital_rates_2024')}; population rates in "
           f"{R.tab('S_grd_population_rates')} and {R.tab('S_a05_standardised_rates')}; indices in "
           f"{R.tab('S_convergence_index')}.")
    supp.p("Denominator layers: INE base-2017 projections at 30 June by comuna, sex and single age (primary); INE base "
           "2024 (30 June and 1 January) and the 2024 Census enumerated population as sensitivities "
           f"({R.fig('figS10_denominators')}, {R.tab('S10_denominator_sensitivity')}); FONASA and ISAPRE December stocks "
           f"and APS enrolment with their schema changes and harmonisation rules ({R.tab('ST12a_fonasa_schema')}, "
           f"{R.tab('ST12b_isapre_rules')}, {R.tab('ST12c_aps_panel')}, {R.fig('figS11_coverage_age_sex')}, "
           f"{R.tab('S11_coverage_age_sex')}); comuna crosswalk by exact normalised name and explicit aliases "
           f"({R.tab('ST4a_comuna_crosswalk_summary')}, {R.tab('ST4b_comuna_unmatched')}). Regional rates "
           f"({R.fig('figS9_regional_maps')}, {R.tab('S9_regional_rates')}) are ecological and uncorrected for "
           f"inter-regional flows. REM semester sensitivity and stable panels: {R.fig('figS5_rem_june_december')}, "
           f"{R.tab('S5_june_december')}, {R.tab('ST14_p2_p6_june_december')}, {R.fig('figS6_rem_stable_panel')}, "
           f"{R.tab('S6_stable_panel')}; monthly seasonality: {R.fig('figS13_rem_seasonality')}, "
           f"{R.tab('S13_rem_seasonality')}; A05 age and sex: {R.fig('figS8_a05_age_sex')}, {R.tab('S8_a05_age_sex')}, "
           f"{R.tab('ST13_a05_age_sex')}; DEIS: {R.tab('ST11a_deis_annual')}, {R.tab('ST11b_deis_vs_grd')}, "
           f"{R.fig('figS14_deis_sex_age')}, {R.tab('S14_deis_sex_age')}; GRD variants, subcodes and age–sex tables: "
           f"{R.fig('figS1_grd_variants')}, {R.fig('figS2_grd_subcodes')}, {R.tab('ST9_grd_age_sex')}.")
    supp.h2("S3. Surveys")
    supp.p(f"ENDIDE 2022: weight fexp, {n0(k('svy_endide_adults_reported_total_n_strata'))} published pseudo-strata "
           f"(region × zone) and {n0(k('svy_endide_adults_reported_total_n_psu'))} first-stage clusters (cod_upm); the 96 "
           f"second-phase strata of the design are not released, so the with-replacement ultimate-cluster approximation is "
           f"used and is probably slightly conservative; adults: item c26_33 (n = {n0(k('svy_endide_adults_reported_total_n'))}); "
           f"children and adolescents 2–17: item n29_19 answered by the main caregiver "
           f"(n = {n0(k('svy_endide_children_reported_total_n'))}), physician confirmation n29a_19 among those with reported "
           f"autism and a valid answer (n = {n0(k('svy_endide_children_confirmed_among_reported_total_n'))}). ENCAVI "
           f"2023–24: weight w_personas_cal, strata varstrat, clusters varunit, item p4_6_1_h (declared diagnosis) among "
           f"persons aged 15 or older with a valid answer (n = {n0(k('svy_encavi_15plus_diagnosed_total_n'))}; a sensitivity "
           f"treats 'don't know/no answer' as not diagnosed, n = {n0(k('svy_encavi_15plus_diagnosed_sens_total_n'))}). "
           f"Domain ratio estimators with Taylor linearisation [@wolter2007; @lumley2004], logit intervals on t, design "
           f"effects and relative standard errors; items and wording in {R.tab('ST5_survey_items')}. The surveys differ in "
           f"year, ages, respondent and wording and are benchmarks of reported autism, not prevalence and not a validation "
           f"of codes; no region or comuna disaggregation is made.")
    supp.h2("S4. Education")
    supp.p(f"PIE series: strict ASD and ASD-Asperger 2019–2023 from MINEDUC Apuntes 60 (Table 6, p. 11) and Apuntes 59 "
           f"(sex split); harmonised ASD + Asperger 2019–2023 from Apuntes 60 and 2024–2025 from the Law 21.545 monitoring "
           f"report (Tables 1–2, pp. 8–9), which also gives autistic students in special schools and the total registered "
           f"autistic students; the 2022 rule adopts {n0(k('pie_2022_apuntes60_sum'))} (Apuntes 60 sum, equal to the "
           f"report's total minus special schools) over the printed {n0(k('pie_2022_sinaces_printed'))}. JUNAEB Student "
           f"Vulnerability Survey microdata 2019–2025 (28 de-identified files by year and level): the ASD item exists from "
           f"2023, weights EXP_REG (2024) and EXP (2025); 2023 unweighted only; grade 9 in 2024 has an entirely empty ASD "
           f"variable (not estimable, not zero); wording, filter and weight by year and level in "
           f"{R.tab('ST6_junaeb_items')}, sex and level estimates in {R.fig('figS12_junaeb_sex_level')} and "
           f"{R.tab('S12_junaeb_sex_level')}; the series plotted in {R.mfig('fig4_triangulation')} are listed in "
           f"{R.tab('F4_triangulation_series')} and the values of {R.mfig('fig3_rem_pathway')} in "
           f"{R.tab('F3_rem_pathway_data')}.")
    supp.h2("S5. Reproduction controls")
    supp.p(f"Reproduction controls are counted in two named scopes that measure different things and are never added "
           f"together. First, {CR.phrase(CR.ANALYSIS_PLAN, LANG)}: the {n0(k('controls_families_prespecified_n'))} "
           f"pre-specified control families, plus labelled check rows, give {n0(k('t8_rows'))} indicator-year controls "
           f"({n0(R.nrows('T8_controls_compact'))} rows in {R.mtab('T8_controls_compact')}: one per control family, "
           f"per labelled check row and per labelled module control) reproduced from the source "
           f"files, of which {n0(k('t8_ok'))} match and {n0(k('t8_differs'))} differ, every difference being a documented "
           f"panel, identifier or duplicate-row convention (full table in {R.tab('T8_controls')}; scatter of the "
           f"{n0(R.nrows('S15_controls_scatter'))} numeric module controls, matches and explained differences, in "
           f"{R.fig('figS15_controls')} and {R.tab('S15_controls_scatter')}). Second, {CR.phrase(CR.PIPELINE, LANG)}: "
           f"{n0(k('controls_csv_rows'))} checks, of which {n0(k('controls_csv_ok'))} reproduce, "
           f"{n0(k('controls_csv_info'))} are informative (a figure with no external expected value) and "
           f"{n0(k('controls_csv_differs'))} carry a documented difference. That total is written by the pipeline to "
           f"controls_summary.csv and is reported here and in the extended methodology; it is not printed on the "
           f"data-workflow plate ({R.mfig('fig1_dataflow')}), whose table of counts ({R.tab('T_dataflow_counts')}) "
           f"lists the counts of the plate itself and not the reproduction controls. No control was completed by "
           f"plausibility; values that do not reproduce are marked and not cited.")

    # Extended methodology (module 12, every formula), supplementary figures grouped by theme and supplementary tables.
    supp.blocks += SM.material_blocks(LANG, variant, V, R)
    supp.add("refs", dict(title=SUPP_REFS_H1, **{"continue": True}))
    note, index = SM.part_texts(LANG, R)
    note_standalone, _ = SM.part_texts(LANG, R, standalone=True)

    # The manuscript carries the same supplementary part after its References, in the same file.
    manuscript_blocks = (article_blocks + [("pagebreak", None), ("h1", SUPP_PART_H1), ("p", note), ("p", index)]
                         + supp.blocks)

    # The standalone appendix repeats it with its own title page, so both documents share the numbering registry.
    appendix = _Doc()
    appendix.add("title", "Supplementary appendix")
    appendix.add("subtitle", f"{TITLE}. Analysis variant: {vlabel}.")
    appendix.add("authors", dict(authors=[(AUTHOR, "1")], affiliations=[("1", AFFILIATION)],
                                 lines=[f"Correspondence: {AUTHOR}, {AUTHOR_EMAIL}"]))
    appendix.h1("Contents")
    appendix.p(note_standalone)
    appendix.p(index)
    appendix.blocks += supp.blocks
    return article_blocks, manuscript_blocks, appendix.blocks, R

def _expand(blocks, R: _Registry):
    """Replace the '_figure'/'_table' placeholders of the main document by real figure/table blocks."""
    out = []
    for kind, payload in blocks:
        if kind == "_figure":
            n = MAIN_FIGURES.index(payload) + 1
            out.append(_main_figure(R, payload, n))
        elif kind == "_table":
            n = MAIN_TABLES.index(payload) + 1
            out.append(_main_table(R, payload, n))
        else:
            out.append((kind, payload))
    return out

def _main_figure(R: _Registry, key: str, n: int):
    meta = R.captions[key]
    caption = f"{_strip_prefix(meta.get('title', ''))}. {meta.get('caption', '')}".strip()
    return ("figure", dict(path=R.fig_path(key), caption=caption, label=f"Figure {n}"))

def _main_table(R: _Registry, key: str, n: int):
    meta = R.titles[key]
    df = pd.read_csv(R.tab_path(key), dtype=str, keep_default_na=False)
    return ("table", dict(df=df, title=_strip_prefix(meta.get("title", "")),
                          note=table_note(key, meta.get("note", ""), df, LANG), label=f"Table {n}"))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def article(variant: str, V: dict) -> list:
    """Blocks of the article alone (title page to References), without the supplementary part."""
    art, _, _, _ = _assemble(variant, V)
    return art

def manuscript(variant: str, V: dict) -> list:
    """Blocks of the manuscript file (English): the article followed by the supplementary part in the same file."""
    _, main, _, _ = _assemble(variant, V)
    return main

def supplement(variant: str, V: dict) -> list:
    """Blocks of the standalone supplementary appendix (English), numbered consistently with manuscript()."""
    _, _, supp, _ = _assemble(variant, V)
    return supp

def supplementary_map(variant: str, V: dict) -> dict:
    """Mapping of file stems to the final supplementary labels ({'figures': {stem: 'Figure Sn'}, 'tables': {...}})."""
    return dict(figures={key: f"Figure S{i}" for i, key in enumerate(SUPP_FIGURES, 1)},
                tables={key: f"Table S{i}" for i, key in enumerate(SUPP_TABLES, 1)})

def main_map(variant: str, V: dict) -> dict:
    """Mapping of file stems to the article's labels ({'figures': {stem: 'Figure n'}, 'tables': {...}})."""
    return dict(figures={key: f"Figure {i}" for i, key in enumerate(MAIN_FIGURES, 1)},
                tables={key: f"Table {i}" for i, key in enumerate(MAIN_TABLES, 1)})

def supplementary_part(variant: str, V: dict) -> list:
    """Blocks of the supplementary part alone (heading, note, index, extended methodology, figures and tables).

    These are exactly the blocks that manuscript() appends after the References, so a caller can inspect or rebuild
    the supplementary part without reassembling the article."""
    art, main, _, _ = _assemble(variant, V)
    return main[len(art):]

def main_citations(variant: str, V: dict) -> list:
    """Every main-figure/main-table citation string produced by the registry, in the order it was produced."""
    _, _, _, R = _assemble(variant, V)
    return list(R.main_citations)

def strip_opt(blocks: list) -> list:
    """Drop the optional paragraphs (journal-length version)."""
    return [(kind, payload) for kind, payload in blocks if not (kind == "p" and str(payload).startswith(OPT))]

_CIT_RE = re.compile(r"\[(@[^\]]+)\]")

def citation_keys(blocks: list, include_opt: bool = False) -> list:
    keys = []

    def scan(text):
        for m in _CIT_RE.finditer(str(text)):
            for part in m.group(1).split(";"):
                key = part.strip().lstrip("@")
                if key and key not in keys:
                    keys.append(key)

    for kind, payload in blocks:
        if kind in ("p", "small"):
            if not include_opt and str(payload).startswith(OPT):
                continue
            scan(payload)
        elif kind == "bullets":
            for item in payload:
                scan(item)
        elif kind == "panel":
            for _, text in payload["items"]:
                scan(text)
        elif kind in ("table", "figure"):
            scan(payload.get("note", "") if kind == "table" else payload.get("caption", ""))
    return keys

_BODY_SECTIONS = ("Introduction", "Methods", "Results", "Discussion", "Conclusion")
_DECL_SECTIONS = ("Contributors", "Declaration of interests", "Data sharing statement", "Funding", "Acknowledgements",
                  "Declaration of the use of artificial intelligence")

def _wc(text: str) -> int:
    return len(re.sub(r"\[@[^\]]+\]", "", str(text)).split())

def word_counts(blocks: list) -> dict:
    """Word counts: summary, panel, core body (Introduction–Conclusion without '[OPT] '), optional body, declarations."""
    counts = dict(summary=0, panel=0, core_body=0, opt_body=0, declarations=0, opt_paragraphs=0, tables=0, figures=0)
    section = None
    for kind, payload in blocks:
        if kind == "h1":
            section = payload
        elif kind == "panel":
            counts["panel"] += sum(_wc(t) for _, t in payload["items"])
        elif kind == "table":
            counts["tables"] += 1
        elif kind == "figure":
            counts["figures"] += 1
        elif kind in ("p", "bullets"):
            texts = payload if kind == "bullets" else [payload]
            for t in texts:
                w = _wc(t.replace("**", ""))
                if section == "Summary":
                    counts["summary"] += w
                elif section in _BODY_SECTIONS:
                    if str(t).startswith(OPT):
                        counts["opt_body"] += _wc(t[len(OPT):])
                        counts["opt_paragraphs"] += 1
                    else:
                        counts["core_body"] += w
                elif section in _DECL_SECTIONS:
                    counts["declarations"] += w
    return counts

def build_all(out_dir: Path, variants=("con_rett", "sin_rett")) -> dict:
    """Build manuscript and supplement DOCX files for each variant; return counts per variant."""
    from docx_builder import build_document
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for variant in variants:
        V = load_values(variant)
        art, main, supp, R = _assemble(variant, V)
        r_main = build_document(main, LANG, out_dir / f"manuscript_en_{variant}.docx", bib_path=BIB)
        r_supp = build_document(supp, LANG, out_dir / f"supplement_en_{variant}.docx", bib_path=BIB)
        report[variant] = dict(manuscript=r_main, supplement=r_supp, word_counts=word_counts(art),
                               core_citation_keys=len(citation_keys(art)), all_citation_keys=len(citation_keys(art, True)),
                               supp_figures=len(SUPP_FIGURES), supp_tables=len(SUPP_TABLES))
    return report

if __name__ == "__main__":
    import argparse
    import tempfile

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="output directory (default: temporary)")
    args = ap.parse_args()
    if args.out:
        rep = build_all(Path(args.out))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            rep = build_all(Path(tmp))
    print(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
