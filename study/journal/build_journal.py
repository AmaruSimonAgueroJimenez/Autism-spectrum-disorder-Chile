#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_journal.py — the journal-format builder of the sin_rett submission.

Builds, from the journal modules of this folder and the existing corpus builders, into manuscript/04_submission_study/:

  article_sin_rett_en.docx|pdf      the submission: title page, Summary, Research in context (boxed panel), main
                                    text, declarations, References (Vancouver, superscript numbers after the
                                    punctuation), then Table 1 and Table 2 (10 pt bold heading, 8 pt body, 8 pt
                                    bold internal headings), then Figures 1–4 ONE PER PAGE with their 10 pt bold
                                    heading at the start of a 10 pt single-spaced legend
  supplement_sin_rett_en.docx|pdf   ONE document: front matter, table of contents WITH PAGE NUMBERS (two-pass
                                    build verified on the PDF), numbered pages, 12 pt bold main heading, 10 pt
                                    bold headings, 10 pt Times New Roman text
  article_sin_rett_es.docx|pdf      the team's working translation (identical numbers; Spanish conventions)
  analysis_plan_v1.0_es.md          the pre-specified analysis plan copied verbatim (Spanish original)
  build_report_journal.json         word counts, budgets, citation keys, plates, page audits, TOC verification
  review/                           page thumbnails and contact sheets

Contract (journal/plan.md, section 7). The article blocks come from `prose_journal_<lang>.article(V)`, the
supplement from `supplement_journal.blocks("en", V)` and the configuration from `journal_config`. Until those
modules land, this builder develops against STUB block lists that follow the same contract (`_Stub*` below,
derived from the corpus article, the extended methodology and the plan's item lists); every stub use is
recorded in the report under "stubs" and the build is flagged "provisional".

The English text passes through the journal number pass (`journal_config.journal_text_blocks`, or the
fallback of the same contract here): mid-height decimal point (U+00B7), four-digit numbers without a
thousands separator, five or more digits with a narrow no-break space; protected tokens (ICD codes, REM
codes, the law, versions, DOIs, URLs, dates, file names, model ids) are never touched; and the numeric value
of every token is verified unchanged before anything is written.

Usage:
    python3 journal/build_journal.py --lang en --skip-pdf
    python3 journal/build_journal.py --lang all
    python3 journal/build_journal.py --lang en --render-plates       # needs common.py's journal plate mode
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent            # study/journal
LA = HERE.parent                                  # study
REPO = LA.parent
for p in (str(HERE), str(LA)):   # references.py y authors.py viven en study/ (LA); paper/ ya no existe
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd  # noqa: E402

import config as CFG  # noqa: E402
import prose_en  # noqa: E402
import prose_es  # noqa: E402
import docx_builder as DB  # noqa: E402
import supplementary_material as SM  # noqa: E402
import prose_methods_extended as PME  # noqa: E402

_spec = importlib.util.spec_from_file_location("m10", LA / "pipeline" / "10_manuscript.py")
m10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m10)


def _optional(name: str):
    """Import a journal module of this folder if it exists; None otherwise (the stub is used)."""
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        if exc.name == name:
            return None
        raise


JC = _optional("journal_config")
PJ = {"en": _optional("prose_journal_en"), "es": _optional("prose_journal_es")}
SJ = _optional("supplement_journal")

PROSE = {"en": prose_en, "es": prose_es}
VARIANT = getattr(JC, "VARIANT", "sin_rett")
LANGS = tuple(getattr(JC, "LANGS", ("en", "es")))
SUBMISSION_LANG = getattr(JC, "SUBMISSION_LANG", "en")
OUT_DIR = Path(getattr(JC, "OUT_DIR", CFG.SUBMISSION))
PLATE_DIR = getattr(JC, "PLATE_DIR", {lang: CFG.OUT / VARIANT / lang / "journal" / "figures" for lang in LANGS})
BODY_FIGURES = list(getattr(JC, "BODY_FIGURES", ["fig1_dataflow", "fig2_grd_core", "fig3_rem_pathway", "fig4_triangulation"]))
BODY_TABLES = list(getattr(JC, "BODY_TABLES", ["T2_grd_core", "T7_models"]))
PLAN = HERE / "plan.md"
EMBED_CACHE = OUT_DIR / ".embed_cache"
REVIEW = OUT_DIR / "review"
REPORT_PATH = OUT_DIR / "build_report_journal.json"
PLATE_PX = (4251, 5787)          # 180 × 245 mm at 600 dpi, as the corpus plates are drawn
SUPP_DPI_DEFAULT = 300
PDFTOTEXT = shutil.which("pdftotext")

#: Journal typography, one dict per document (docx_builder.build_document(journal=...)). The article keeps a
#: 12 pt body at 1,5 spacing with 12 pt headings (the journal fixes no body size for the manuscript text);
#: the supplement is what the journal prescribes for web extra material: 12 pt bold main heading, 10 pt bold
#: headings, 10 pt single-spaced text. Both: tables 10/8/8 pt, legends 10 pt with the bold heading,
#: superscript citations after the punctuation, one figure per page.
#: Round 1 of the readers (journal/decisions.md, CLOSE ROUND 1): table legends (notes) at 10 pt like the figure
#: legends; no table below 8 pt (`table_min_pt`; a table that does not fit A4 landscape at 8 pt wraps its long
#: tokens instead of shrinking); the supplement text single-spaced; a plate may shrink to `plate_min_w_cm` (140 mm,
#: above the journal's 107 mm; 4251 px at 140 mm is 770 dpi) so that its whole legend — or at least
#: `plate_min_lines` lines of it — sits under the image, which is what puts the legend heading on the plate's
#: page; equations never split across pages.
#: Round 2 of the readers: a plate shrunk below 180 mm prints its 6 pt artwork text at 5,0–5,9 pt, so the plate
#: keeps its natural 180 mm (`plate_min_w_cm` = 18: the plate never shrinks; `common.PLATE_FS_FLOOR` = 6 pt holds at
#: print size) and a legend that does not fit under it continues on the next page labelled «(continued)»; every
#: table row is unsplittable and the last two rows travel with the note (`table_rows_cant_split`); the supplement's
#: front matter, presentation paragraphs and appendix references are single-spaced like its text
#: (`aux_line_spacing` = 1,0).
JOURNAL_DOC_FLAGS = dict(table_pt=8, table_heading_pt=10, table_internal_heading_pt=8, table_note_pt=10,
                         table_min_pt=8, table_rows_cant_split=True, legend_pt=10,
                         legend_heading_bold=True, heading_pt=12, main_heading_pt=14, title_pt=14, body_pt=12,
                         line_spacing=1.5, aux_line_spacing=1.15, superscript_citations=True,
                         one_figure_per_page=True, plate_min_w_cm=18.0, plate_min_lines=3,
                         page_numbers=True, toc=False, refs_pt=10, panel_pt=10.5)
SUPPLEMENT_DOC_FLAGS = dict(JOURNAL_DOC_FLAGS, heading_pt=10, main_heading_pt=12, title_pt=12, body_pt=10,
                            line_spacing=1.0, aux_line_spacing=1.0, toc=True, panel_pt=10,
                            one_figure_per_page=False,
                            lead_max_cm=6.0)     # the presentation paragraph (≤ 14 lines at 10 pt) rides with its plate

WORD_BUDGET_DEFAULT = dict(summary=250, panel=430, introduction=400, methods=1350, results=1650, discussion=1000,
                           conclusion=80, core_body_max=4800, core_body_min=3500, legend_max=300,
                           legend_fig1_max=160)
WORD_BUDGET = dict(WORD_BUDGET_DEFAULT, **getattr(JC, "WORD_BUDGET", {}))
N_REFERENCES = 30

W = {   # bilingual labels of this module (title page and supplement front matter)
    "counts": {"en": ("Word counts: Summary {summary}; Research in context {panel}; manuscript text "
                      "(Introduction–Conclusion) {core}; {refs} references; {tables} tables; {figures} figures."),
               "es": ("Recuentos de palabras: Resumen {summary}; Investigación en contexto {panel}; texto del "
                      "manuscrito (Introducción–Conclusión) {core}; {refs} referencias; {tables} tablas; "
                      "{figures} figuras.")},
    "supp_line": {"en": "Supplementary appendix: one PDF with the applied methodology, the STROBE/RECORD checklist, "
                        "the pre-specified analysis plan and the supplementary results ({sfig} figures, {stab} tables).",
                  "es": "Apéndice suplementario: un solo PDF con la metodología aplicada, la lista STROBE/RECORD, "
                        "el plan de análisis preespecificado y los resultados suplementarios ({sfig} figuras, "
                        "{stab} tablas)."},
    "translation": {"es": ("Traducción de trabajo del equipo: el envío es la versión en inglés, que es la que "
                           "observa los límites de la revista; este archivo conserva las mismas cifras.")},
    "built": {"en": "Built on {date} by study/journal/build_journal.py from outputs/values_{variant}.json.",
              "es": "Construido el {date} por study/journal/build_journal.py a partir de "
                    "outputs/values_{variant}.json."},
    "supp_title": {"en": "Supplementary appendix"},
    "contents": {"en": "Contents"},
    "appendix_refs": {"en": "Appendix references"},
    "part_a": {"en": "Part A — Applied methodology"},
    "part_b": {"en": "Part B — Supplementary results"},
}


def log(msg: str) -> None:
    print(f"[build_journal] {msg}", flush=True)


# ---------------------------------------------------------------------------
# The journal number pass (fallback of the journal_config contract) and its verification
# ---------------------------------------------------------------------------
PROTECTED_TOKENS_DEFAULT = [
    r"\bF84(?:\.\d)?\b", r"\b[A-Z]\d{2}\.\d\b", r"\b\d{8}\b", r"\bP6\d{6}\b", r"(?:Law|Ley) 21\.545",
    r"\b\d+\.\d+\.\d+\b", r"doi:\S+", r"https?://\S+", r"\b\d{4}-\d{2}-\d{2}\b",
    r"\S+\.(?:csv|json|py|png|pdf|md|docx|parquet|shp|xlsx?|rar|zip|txt|bib)\b",
    r"\b[a-z_]+:[a-z_]+(?::[A-Za-z0-9_-]+)+\b", r"\bSHA-256\b", r"\bv?\d+\.\d+\b(?= of the plan)",
    r"\b(?:Python|pandas|numpy|NumPy|SciPy|scipy|statsmodels|matplotlib|Matplotlib|geopandas|GeoPandas|"
    r"libpysal|esda|PySAL|pyproj|shapely|Shapely|python-docx|Pillow|PIL|R)\s+v?\d+\.\d+(?:\.\d+)*\b",
    r"\b(?:version|versión|v\.?)\s*\d+\.\d+(?:\.\d+)*\b", r"\bEPSG:\d+\b",
]
PROTECTED_TOKENS = list(getattr(JC, "PROTECTED_TOKENS", PROTECTED_TOKENS_DEFAULT))
_PROTECTED_RE = re.compile("|".join(f"(?:{p})" for p in PROTECTED_TOKENS))
_THOUSANDS_RE = re.compile(r"\d{1,3}(?:,\d{3})+\b")
_DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")
_NARROW = " "
_MASK_OPEN, _MASK_CLOSE = "", ""


def _mask_id(n: int) -> str:
    return _MASK_OPEN + "".join(chr(0xE200 + int(c)) for c in str(n)) + _MASK_CLOSE


def fallback_journal_text(s: str, lang: str) -> str:
    """The number pass of the contract (identity for lang != 'en'): protected tokens masked, thousands
    separators removed (four digits) or replaced by a narrow no-break space (five or more), decimal point at
    mid height, mask restored."""
    if lang != "en" or not isinstance(s, str) or not s:
        return s
    kept: list[str] = []

    def mask(m):
        kept.append(m.group(0))
        return _mask_id(len(kept) - 1)

    text = _PROTECTED_RE.sub(mask, s)

    def thousands(m):
        digits = m.group(0).replace(",", "")
        return digits if len(digits) == 4 else _NARROW.join(m.group(0).split(","))

    text = _THOUSANDS_RE.sub(thousands, text)
    text = _DECIMAL_RE.sub("·", text)
    for i, tok in enumerate(kept):
        text = text.replace(_mask_id(i), tok)
    return text


def journal_text(s: str, lang: str) -> str:
    fn = getattr(JC, "journal_text", None)
    return fn(s, lang) if callable(fn) else fallback_journal_text(s, lang)


def remap_refs(s: str, lang: str) -> str:
    fn = getattr(JC, "remap_refs", None)
    return fn(s, lang) if callable(fn) else s


def walk_strings(value, fn):
    """A transformed copy of any block payload: every str through `fn`, DataFrames cell by cell."""
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, pd.DataFrame):
        df = value.copy()
        df.columns = [fn(str(c)) for c in df.columns]
        for j in range(df.shape[1]):
            if df.dtypes.iloc[j] == object:
                df.isetitem(j, [fn(v) if isinstance(v, str) else v for v in df.iloc[:, j]])
        return df
    if isinstance(value, dict):
        return {k: walk_strings(v, fn) for k, v in value.items()}
    if isinstance(value, list):
        return [walk_strings(v, fn) for v in value]
    if isinstance(value, tuple):
        return tuple(walk_strings(v, fn) for v in value)
    return value


def strings_of(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, pd.DataFrame):
        out = [str(c) for c in value.columns]
        for j in range(value.shape[1]):
            if value.dtypes.iloc[j] == object:
                out += [v for v in value.iloc[:, j] if isinstance(v, str)]
        return out
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings_of(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in strings_of(v)]
    return []


def journal_text_blocks(blocks: list, lang: str) -> list:
    """Every string of every block through the number pass and the cross-reference remap (contract 7.1)."""
    fn = getattr(JC, "journal_text_blocks", None)
    if callable(fn):
        return fn(blocks, lang)
    return [(kind, walk_strings(payload, lambda s: remap_refs(journal_text(s, lang), lang))) for kind, payload in blocks]


_NUM_TOKEN_RE = re.compile(r"\d(?:[\d,. ·]*\d)?")
#: cross-references ("Table S27", "Figures S3–S5", "Figure 2c") are renumbered by the remap of contract 7.7,
#: not numbers: they are removed before the numeric tokens of a string are compared
_XREF_RE = re.compile(r"\b(?:Figures?|Tables?|Figuras?|Tablas?|Fig\.)\s+S?\d+[a-z]?"
                      r"(?:\s*(?:[–\-]|to|and|y|a|,)\s*S?\d+[a-z]?)*")


def _numeric_tokens(s: str) -> list[str]:
    s = _XREF_RE.sub(" ", s)
    return [t.replace(",", "").replace(_NARROW, "").replace("·", ".") for t in _NUM_TOKEN_RE.findall(s)]


def numbers_unchanged(before: list, after: list) -> dict:
    """The check the task requires: the numeric VALUE of every token is the same before and after the pass.

    Compares, block by block, the normalised numeric tokens of every string (separators removed, the mid-height
    point read as a decimal point). Returns dict(ok, checked, mismatches=[...])."""
    mismatches, checked = [], 0
    if len(before) != len(after):
        return dict(ok=False, checked=0, mismatches=[f"block count {len(before)} != {len(after)}"])
    for i, ((kb, pb), (ka, pa)) in enumerate(zip(before, after)):
        sb, sa = strings_of(pb), strings_of(pa)
        if len(sb) != len(sa):
            mismatches.append(f"{kb}#{i}: {len(sb)} strings before, {len(sa)} after")
            continue
        for x, y in zip(sb, sa):
            checked += 1
            tx, ty = _numeric_tokens(x), _numeric_tokens(y)
            if tx != ty:
                mismatches.append(f"{kb}#{i}: {tx[:6]} -> {ty[:6]} | {x[:80]!r}")
    return dict(ok=not mismatches, checked=checked, mismatches=mismatches[:20])


def ascii_decimals_left(blocks: list) -> list[str]:
    """Strings of the passed blocks that still carry an ASCII decimal outside the protected tokens."""
    out = []
    for kind, payload in blocks:
        for s in strings_of(payload):
            masked = _PROTECTED_RE.sub(" ", s)
            if _DECIMAL_RE.search(masked):
                out.append(f"{kind}: {s[:100]!r}")
    return out


def format_p(p: float) -> str:
    fn = getattr(JC, "format_p", None)
    if callable(fn):
        return fn(p)
    if p < 1e-4:
        return "<0·0001"
    return f"{p:.2g}".replace(".", "·")


# ---------------------------------------------------------------------------
# Stubs (development until journal_config / prose_journal_* / supplement_journal land)
# ---------------------------------------------------------------------------
def plan_lists() -> dict:
    """The item lists of journal/plan.md (section 4 Part B and section 6), read from the plan itself."""
    text = PLAN.read_text(encoding="utf-8")
    figs = sorted(((int(n), key) for n, key, _ in re.findall(r"^\| S(\d+) \| (\S+) \((f|xf)\) \|", text, flags=re.M)))
    tabs = sorted(((int(n), key) for n, key, _ in re.findall(r"^\| S(\d+) \| (\S+) \((t|x)\)", text, flags=re.M)))
    refs = [k for _, k in sorted((int(n), k) for n, k in re.findall(r"^\| (\d+) \| (\w+) \| ", text, flags=re.M))]
    m = re.search(r"\*\*Table 2 whitelist\*\*.*?\n((?:`[^`]+`(?:, |\.)\s*)+)", text, flags=re.S)
    t7_ids = re.findall(r"`([^`]+)`", m.group(1)) if m else []
    supp_tables = list(SM.METHODS_TABLES) + ["S_reporting_checklist"] + [k for _, k in tabs]
    return dict(supp_figures=[k for _, k in figs], supp_tables=supp_tables, reference_keys=refs, t7_model_ids=t7_ids)


SUPP_FIGURES = list(getattr(JC, "SUPP_FIGURES", []) or plan_lists()["supp_figures"])
SUPP_TABLES = list(getattr(JC, "SUPP_TABLES", []) or plan_lists()["supp_tables"])
REFERENCE_KEYS = list(getattr(JC, "REFERENCE_KEYS", []) or plan_lists()["reference_keys"])


def stub_registry(P, lang: str):
    """A registry with the journal numbering (contract 7.1 surface) over the corpus assets."""
    plan = plan_lists()

    class _StubRegistry(P._Registry):
        def __init__(self):
            super().__init__(VARIANT)
            self.SF, self.ST, self.BF, self.BT = SUPP_FIGURES, SUPP_TABLES, BODY_FIGURES, BODY_TABLES
            self.first_cited: list[str] = []

        def _first(self, key):
            if key not in self.first_cited:
                self.first_cited.append(key)

        def fig(self, key):
            if key not in self.SF:
                raise KeyError(f"'{key}' is not a supplementary figure of the journal plan")
            self._first(key)
            return f"{self.FIG_WORD} S{self.SF.index(key) + 1}"

        def tab(self, key):
            if key not in self.ST:
                raise KeyError(f"'{key}' is not a supplementary table of the journal plan")
            self._first(key)
            return f"{self.TAB_WORD} S{self.ST.index(key) + 1}"

        def mfig(self, key):
            self._first(key)
            return f"{self.FIG_WORD} {self.BF.index(key) + 1}"

        def mtab(self, key):
            self._first(key)
            return f"{self.TAB_WORD} {self.BT.index(key) + 1}"

        def figp(self, key, panels):
            return f"{self.fig(key)}{self._panels(key, panels)}"

        def mfigp(self, key, panels):
            return f"{self.mfig(key)}{self._panels(key, panels)}"

        def fig_path(self, key):
            journal_png = Path(PLATE_DIR[lang]) / f"{key}.png"
            if key in self.BF and journal_png.is_file():
                return journal_png
            return super().fig_path(key)

        def heading_of(self, key):
            return P._strip_prefix(self.captions[key].get("title", ""))

        def figure_block(self, key, label, body=False):
            meta = self.captions[key]
            heading = self.heading_of(key)
            caption = f"{heading}. {meta.get('caption', '')}".strip()
            return ("figure", dict(path=self.fig_path(key), caption=caption, label=label, heading=heading,
                                   embed_dpi=None))

        def table_block(self, key, label, rows=None, columns=None):
            meta = self.titles[key]
            df = pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False)
            if key == "T2_grd_core" and key in self.BT and label.split()[-1].isdigit():
                df = _stub_cut_t2(df)
            elif key == "T7_models" and key in self.BT and label.split()[-1].isdigit():
                df = _stub_cut_t7(df, self.tab_path(key).with_name("T7_models_numeric.csv"), plan["t7_model_ids"])
            return ("table", dict(df=df, title=P._strip_prefix(meta.get("title", "")),
                                  note=P.table_note(key, meta.get("note", ""), df, lang), label=label))

        def first_citation_order(self):
            return list(self.first_cited)

    return _StubRegistry()


def _heading_rows(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Rows grouped under an internal heading row (first cell = group, the rest empty), group column dropped."""
    cols = [c for c in df.columns if c != group_col]
    out = []
    for group in df[group_col].drop_duplicates():
        out.append({c: "" for c in cols} | {cols[0]: group})
        for _, row in df[df[group_col] == group].iterrows():
            out.append({c: row[c] for c in cols})
    return pd.DataFrame(out, columns=cols)


def _stub_cut_t2(df: pd.DataFrame) -> pd.DataFrame:
    """Columns by position (Block/Bloque, Indicator/Indicador): the stub serves both languages."""
    block, indicator = df.columns[0], df.columns[1]
    keep = ~df[indicator].str.contains(r"mean \(median\)|media \(mediana\)", regex=True)
    return _heading_rows(df[keep].reset_index(drop=True), block)


def _stub_cut_t7(df: pd.DataFrame, numeric_path: Path, ids: list) -> pd.DataFrame:
    num = pd.read_csv(numeric_path, dtype=str, keep_default_na=False)
    if len(num) != len(df):
        raise RuntimeError(f"T7_models ({len(df)} rows) and T7_models_numeric ({len(num)} rows) are not row-aligned")
    idx = [i for i, mid in enumerate(num["model_id"]) if mid in set(ids)] if ids else list(range(len(df)))
    cut = df.iloc[idx].copy()
    pcol = next((c for c in cut.columns if c.lower().startswith(("p value", "valor p"))), None)
    if pcol:
        cut[pcol] = [format_p(float(num.iloc[i]["p_value"])) for i in idx]
    cut = cut.drop(columns=[c for c in cut.columns if str(c).lower().startswith(("notes", "notas"))])
    return _heading_rows(cut.reset_index(drop=True), cut.columns[0])


def stub_article(lang: str, V: dict) -> tuple[list, object]:
    """The corpus article (optional paragraphs dropped) with the journal display items after the References."""
    P = PROSE[lang]
    R = stub_registry(P, lang)
    src = P.strip_opt(P.article(VARIANT, V))
    out = [b for b in src if b[0] not in ("figure", "table")]
    for i, key in enumerate(BODY_TABLES, 1):
        out.append(R.table_block(key, R.mtab(key)))
    for i, key in enumerate(BODY_FIGURES, 1):
        out.append(R.figure_block(key, R.mfig(key), body=True))
    return out, R


def stub_supplement(V: dict, limit: int | None = None) -> tuple[list, object]:
    """Part A (extended methodology verbatim, journal table numbers) and Part B (the plan's items) in English."""
    R = stub_registry(prose_en, "en")
    blocks: list = [("title", f"{W['supp_title']['en']}: {prose_en.TITLE}"),
                    ("p", ("This appendix accompanies the article. It presents the F84 family excluding Rett "
                           "syndrome (F84.2); the full-family variant is not submitted separately and is compared "
                           "series by series in the supplementary results. [Stub front matter: the journal "
                           "supplement module has not landed; the standing rules paragraph is supplied by it.]")),
                    ("h1", W["part_a"]["en"])]
    methods = PME.methods_blocks(VARIANT, V, "en", R=R, first_table=1)
    if methods and methods[0][0] == "h1":
        methods = methods[1:]
    blocks += methods
    blocks.append(("h1", W["part_b"]["en"]))
    figs = [k for k in SUPP_FIGURES if k in R.captions][:limit]
    tabs = [k for k in SUPP_TABLES if k in R.titles and k not in SM.METHODS_TABLES][:limit]
    blocks.append(("h2", "Supplementary figures"))
    for key in figs:
        label = R.fig(key)
        try:
            intro = SM.figure_intro(key, label, "en")
        except KeyError:
            intro = f"{label} shows {R.heading_of(key)}."
        blocks.append(("p", intro))
        blocks.append(R.figure_block(key, label))
    blocks.append(("h2", "Supplementary tables"))
    for key in tabs:
        blocks.append(R.table_block(key, R.tab(key)))
    blocks.append(("refs", {"title": W["appendix_refs"]["en"]}))
    return blocks, R


# ---------------------------------------------------------------------------
# Block preparation shared by the article and the supplement
# ---------------------------------------------------------------------------
_TITLE_SENTENCE_RE = re.compile(r"^(.+?[^.\d]\.)\s+(.*)$", flags=re.S)


def normalise_figure_headings(blocks: list) -> list:
    """Every figure payload carries `heading` (the figure title printed in bold at the start of the legend).

    The journal registry supplies it; for a block that only carries the corpus caption 'Title. Body' the title
    is the first sentence (a period followed by a space, never the decimal point of a number)."""
    out = []
    for kind, payload in blocks:
        if kind == "figure" and not payload.get("heading"):
            m = _TITLE_SENTENCE_RE.match(str(payload.get("caption", "")))
            if m:
                payload = dict(payload, heading=m.group(1)[:-1])
        out.append((kind, payload))
    return out


def strip_front_matter(blocks: list) -> tuple[dict, list]:
    """Split the leading title/subtitle/authors blocks (any subset) from the rest."""
    front, i = {}, 0
    while i < len(blocks) and blocks[i][0] in ("title", "subtitle", "authors") and blocks[i][0] not in front:
        front[blocks[i][0]] = blocks[i][1]
        i += 1
    return front, blocks[i:]


def title_page(blocks: list, lang: str, P, authors: list, affiliations: list, counts: dict,
               supplement: bool = False) -> list:
    """Journal title page: title, authors with affiliation, correspondence, article type, running title, counts."""
    front, rest = strip_front_matter(blocks)
    title = front.get("title") or getattr(P, "TITLE", prose_en.TITLE)
    supplied = front.get("authors") if isinstance(front.get("authors"), dict) else None
    stamp = W["built"][lang].format(date=dt.date.today().isoformat(), variant=VARIANT)
    if supplied and supplied.get("lines"):
        # the prose/supplement module words its own title page (contract 7.2): keep it. The build stamp goes
        # only on the team's working translation: a submission title page carries no build metadata.
        lines = [l for l in supplied["lines"] if not str(l).startswith(("Built on", "Construido el"))]
        if lang != SUBMISSION_LANG and not supplement:
            lines += [W["translation"][lang], stamp]
        payload = dict(supplied, lines=lines)
    else:
        email_author = next(((n, e) for n, _, e in authors if e), (authors[0][0], ""))
        lines = [f"{m10.W['corr'][lang]}: {email_author[0]}" + (f" ({email_author[1]})" if email_author[1] else "")]
        if not supplement:
            lines.append(m10.W["article"][lang])
            lines.append(f"{m10.W['running'][lang]}: {getattr(P, 'RUNNING_TITLE', prose_en.RUNNING_TITLE)}")
            lines.append(W["counts"][lang].format(**counts))
            lines.append(W["supp_line"][lang].format(**counts))
            if lang != SUBMISSION_LANG:
                lines += [W["translation"][lang], stamp]
        payload = m10.authors_payload(lang, P if hasattr(P, "AFFILIATION") else prose_en, authors, affiliations, lines)
    out = [("title", title)]
    if front.get("subtitle"):
        out.append(("subtitle", front["subtitle"]))
    return out + [("authors", payload)] + rest


def section_word_counts(blocks: list) -> dict:
    """Words per h1 section of the manuscript text (same counter as prose_en.word_counts)."""
    counts, section = {}, None
    for kind, payload in blocks:
        if kind == "h1":
            section = payload
        elif kind in ("p", "bullets") and section:
            texts = payload if kind == "bullets" else [payload]
            counts[section] = counts.get(section, 0) + sum(prose_en._wc(str(t).replace("**", "")) for t in texts)
    return counts


_SECTION_BUDGET = {"Introduction": "introduction", "Methods": "methods", "Results": "results",
                   "Discussion": "discussion", "Conclusion": "conclusion"}


def check_budgets(blocks: list, lang: str, wc: dict, keys: list) -> list[str]:
    """Every budget of WORD_BUDGET, the Summary, the legends and the reference count (English only)."""
    problems = []
    if lang != SUBMISSION_LANG:
        return problems
    if wc["summary"] > WORD_BUDGET["summary"]:
        problems.append(f"Summary {wc['summary']} > {WORD_BUDGET['summary']}")
    if wc["panel"] > WORD_BUDGET["panel"]:
        problems.append(f"Research in context {wc['panel']} > {WORD_BUDGET['panel']}")
    if not WORD_BUDGET["core_body_min"] <= wc["core_body"] <= WORD_BUDGET["core_body_max"]:
        problems.append(f"manuscript text {wc['core_body']} outside {WORD_BUDGET['core_body_min']}–{WORD_BUDGET['core_body_max']}")
    for section, n in section_word_counts(blocks).items():
        b = _SECTION_BUDGET.get(section)
        if b and n > WORD_BUDGET[b]:
            problems.append(f"{section} {n} > {WORD_BUDGET[b]}")
    n_fig = 0
    for kind, payload in blocks:
        if kind == "figure":
            n_fig += 1
            n = prose_en._wc(str(payload.get("caption", "")))
            cap = WORD_BUDGET["legend_fig1_max"] if n_fig == 1 else WORD_BUDGET["legend_max"]
            if n > cap:
                problems.append(f"{payload.get('label', f'Figure {n_fig}')} legend {n} > {cap}")
    if len(keys) != N_REFERENCES:
        problems.append(f"{len(keys)} references cited, {N_REFERENCES} required")
    if REFERENCE_KEYS and keys != REFERENCE_KEYS:
        problems.append("citation keys differ from REFERENCE_KEYS (order or content)")
    if any(kind == "p" and str(payload).startswith(prose_en.OPT) for kind, payload in blocks):
        problems.append("an [OPT] paragraph survives")
    return problems


def _hash_tree(paths: list[Path]) -> dict:
    out = {}
    for base in paths:
        if base.is_file():
            out[str(base)] = hashlib.sha256(base.read_bytes()).hexdigest()
            continue
        for f in sorted(base.rglob("*")) if base.is_dir() else []:
            if f.is_file():
                out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def corpus_paths() -> list[Path]:
    out = [CFG.OUT / VARIANT / lang / sub for lang in LANGS for sub in ("figures", "extra", "tables")]
    out += sorted(CFG.OUT.glob("values_*.json")) + [CFG.TIDY]
    return out


# ---------------------------------------------------------------------------
# PDF, review, table of contents
# ---------------------------------------------------------------------------
#: LibreOffice's PDF export downsamples every image to 300 dpi by default ("Reduce image resolution"); the
#: journal build switches that off so the plates reach the PDF at the resolution they are embedded with (the
#: body plates at 600 dpi, 180 mm wide; the supplement plates at --supp-dpi). JPEG quality 95 keeps the PDF
#: within a few megabytes; the default corpus export (m10.to_pdf) is untouched.
PDF_EXPORT_FILTER = ('pdf:writer_pdf_Export:{"ReduceImageResolution":{"type":"boolean","value":"false"},'
                     '"UseLosslessCompression":{"type":"boolean","value":"false"},'
                     '"Quality":{"type":"long","value":"95"}}')


def to_pdf(docx: Path, profile: Path, timeout: int = 1200) -> Path:
    """PDF beside the DOCX through LibreOffice, without image downsampling (see PDF_EXPORT_FILTER)."""
    profile.mkdir(parents=True, exist_ok=True)
    pdf = OUT_DIR / (docx.stem + ".pdf")
    if pdf.exists():
        pdf.unlink()
    cmd = [m10.SOFFICE, "--headless", "--norestore", f"-env:UserInstallation={profile.as_uri()}",
           "--convert-to", PDF_EXPORT_FILTER, "--outdir", str(OUT_DIR), str(docx)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"LibreOffice did not convert {docx.name}: rc={res.returncode}\n{res.stdout}\n{res.stderr}")
    return pdf


def pdf_image_resolutions(pdf: Path) -> list[dict]:
    """Every raster image of the PDF (page, pixels, ppi) from `pdfimages -list`; [] when the tool is absent."""
    tool = shutil.which("pdfimages")
    if not tool:
        return []
    res = subprocess.run([tool, "-list", str(pdf)], capture_output=True, text=True, timeout=600)
    out = []
    for line in res.stdout.splitlines()[2:]:
        f = line.split()
        if len(f) >= 14 and f[2] == "image":
            out.append(dict(page=int(f[0]), width_px=int(f[3]), height_px=int(f[4]), x_ppi=int(f[12]), y_ppi=int(f[13])))
    return out


def review(docx: Path, pdf: Path, lang: str, plates: list | None, do_thumbs: bool,
           skip_pages: set | None = None) -> dict:
    """PDF facts, the corpus layout audit and the thumbnails. `skip_pages` (1-based) are the pages of the
    table of contents: their lines «Figure Sn. …» are entries, not legends, and the corpus audit — written
    for documents without a TOC — would count each of them as a legend without its plate."""
    info = dict(pdf=str(pdf), pdf_size_mb=round(pdf.stat().st_size / 1e6, 1), pages=m10.pdf_pages(pdf))
    images = pdf_image_resolutions(pdf)
    if images:
        info["images"] = dict(n=len(images), ppi_min=min(i["x_ppi"] for i in images),
                              ppi_max=max(i["x_ppi"] for i in images), first=images[:6])
    audit = m10.page_layout_audit(pdf, lang, plates)
    if audit and skip_pages:
        for key, hits, count in (("caption_spill", "unmarked_at", "unmarked_spills"),
                                 ("lead_in", "lead_off_at", "lead_off_plate_page")):
            part = audit.get(key) or {}
            if hits in part:
                kept = [h for h in part[hits] if h.get("page") not in skip_pages]
                part[hits], part[count] = kept, len(kept)
                part["toc_pages_skipped"] = sorted(skip_pages)
    if audit:
        info["layout"] = audit
    if do_thumbs:
        rdir = REVIEW / docx.stem
        pages = m10.thumbnails(pdf, rdir)
        sheet = m10.contact_sheet(pages, REVIEW / f"{docx.stem}_contact_sheet.png")
        info.update(thumbnails=str(rdir), n_thumbnails=len(pages), contact_sheet=str(sheet))
    return info


def pdf_page_texts(pdf: Path) -> list[str]:
    if not PDFTOTEXT:
        raise RuntimeError("pdftotext is not available: the supplement table of contents cannot be verified")
    res = subprocess.run([PDFTOTEXT, "-layout", str(pdf), "-"], capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"pdftotext failed on {pdf.name}: {res.stderr}")
    pages = res.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


_PART_RE = re.compile(r"\s*\(part \d+ of \d+\)$")


def toc_entries(blocks: list) -> list[dict]:
    """One entry per h1/h2 heading, table, figure and reference list after the TOC position."""
    entries = []
    for kind, payload in blocks:
        if kind == "h1":
            entries.append(dict(level=0, kind="heading", text=str(payload), page=None))
        elif kind == "h2":
            entries.append(dict(level=1, kind="heading", text=str(payload), page=None))
        elif kind == "table":
            if payload.get("continuation"):          # part 2… of a restructured table: one TOC entry per table
                continue
            label = _PART_RE.sub("", payload["label"])
            entries.append(dict(level=2, kind="table", label=label, text=_short(f"{label}. {payload['title']}"), page=None))
        elif kind == "figure":
            label = payload["label"]
            entries.append(dict(level=2, kind="figure", label=label,
                                text=_short(f"{label}. {payload.get('heading') or ''}".rstrip(". ") + "."), page=None))
        elif kind == "refs":
            title = (payload or {}).get("title") if isinstance(payload, dict) else None
            entries.append(dict(level=0, kind="heading", text=title or DB.WORDS["references"]["en"], page=None))
    return entries


_ASCII_WS_RE = re.compile(r"[ \t\r\n\f\v]+")


def _short(text: str, n: int = 88) -> str:
    text = _ASCII_WS_RE.sub(" ", str(text)).strip()      # not str.split(): it would turn «100 000» into «100 000»
    if len(text) <= n:
        return text
    cut = text[:n - 1]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:–-") + "…"


def _norm(s: str) -> str:
    return " ".join(str(s).split())        # comparison only (pdftotext output), never written to the document


def locate_entries(pages: list[str], entries: list[dict], toc_title: str) -> list[int | None]:
    """The PDF page (1-based) where each TOC entry starts, read from `pdftotext -layout`.

    The TOC pages are skipped: they run from the page carrying the '<toc_title>' line to the page before the
    first page whose first line is the first level-0 entry (a page break separates the TOC from Part A)."""
    lines = [[_norm(l) for l in p.splitlines() if l.strip()] for p in pages]
    toc_start = next((i for i, ls in enumerate(lines) if any(l == toc_title for l in ls)), None)
    first = _norm(entries[0]["text"])[:50] if entries else ""
    start = 0
    if toc_start is not None:
        start = next((i for i in range(toc_start + 1, len(lines)) if lines[i] and lines[i][0].startswith(first)),
                     toc_start + 1)
    found, cursor = [], start
    for e in entries:
        kind = e["kind"]
        if kind == "table":
            pat = re.compile(r"^" + re.escape(e["label"]) + r"(?: \(part 1 of \d+\))?$")
        elif kind == "figure":
            pat = re.compile(r"^" + re.escape(e["label"]) + r"\.(\s|$)")
        else:
            head = _norm(e["text"])[:50]
            pat = re.compile(r"^" + re.escape(head))
        page = next((i for i in range(cursor, len(lines)) if any(pat.match(l) for l in lines[i])), None)
        found.append(None if page is None else page + 1)
        if page is not None:
            cursor = page
    return found


def toc_position(blocks: list) -> tuple[int, int]:
    """(start, end) of the slice the TOC replaces: the module's own "Contents" heading and the placeholder
    lines under it when it carries one; otherwise the empty slice before the first "Part A" h1 (or the
    first h1)."""
    contents = getattr(SJ, "CONTENTS_H1", None) or W["contents"]["en"]
    for i, (k, p) in enumerate(blocks):
        if k == "h1" and _norm(str(p)) == _norm(contents):
            j = i + 1
            while j < len(blocks) and blocks[j][0] in ("p", "bullets", "small", "pagebreak"):
                j += 1
            return i, j
    part_a = next((i for i, (k, p) in enumerate(blocks) if k == "h1" and str(p).startswith("Part A")), None)
    if part_a is None:
        part_a = next((i for i, (k, _) in enumerate(blocks) if k == "h1"), len(blocks))
    return part_a, part_a


def toc_page_numbers(pages: list[str], entries: list[dict], toc_title: str) -> set:
    """The 1-based pages of the table of contents (same rule as `locate_entries`)."""
    lines = [[_norm(l) for l in p.splitlines() if l.strip()] for p in pages]
    toc_start = next((i for i, ls in enumerate(lines) if any(l == toc_title for l in ls)), None)
    if toc_start is None or not entries:
        return set()
    first = _norm(entries[0]["text"])[:50]
    start = next((i for i in range(toc_start + 1, len(lines)) if lines[i] and lines[i][0].startswith(first)),
                 toc_start + 1)
    return set(range(toc_start + 1, start + 1))


def with_toc(blocks: list, entries: list[dict], placeholder: str = "000") -> list:
    """The blocks with the TOC in its place (see `toc_position`) and a page break after it."""
    a, b = toc_position(blocks)
    toc = ("toc", dict(title=W["contents"]["en"], entries=[dict(e, placeholder=placeholder) for e in entries]))
    return blocks[:a] + [toc, ("pagebreak", None)] + blocks[b:]


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
def article_blocks(lang: str, V: dict, stubs: list) -> tuple[list, object]:
    mod = PJ.get(lang)
    if mod is not None and hasattr(mod, "article"):
        return mod.article(V), getattr(mod, "REGISTRY", None)
    stubs.append(f"prose_journal_{lang}.article (corpus article with the journal display items)")
    return stub_article(lang, V)


def supplement_blocks(V: dict, stubs: list, limit: int | None) -> tuple[list, object]:
    if SJ is not None and hasattr(SJ, "blocks"):
        return SJ.blocks("en", V), getattr(SJ, "REGISTRY", None)
    stubs.append("supplement_journal.blocks (extended methodology + the plan's Part B items)")
    return stub_supplement(V, limit)


def body_plate_check(blocks: list, lang: str) -> list[str]:
    """Body plates must come from PLATE_DIR at the plate size; otherwise the build is provisional."""
    warnings = []
    plate_dir = Path(PLATE_DIR[lang])
    for kind, payload in blocks:
        if kind != "figure":
            continue
        path = Path(payload["path"])
        if payload.get("label", "").split()[-1].isdigit():
            if path.parent != plate_dir:
                warnings.append(f"{payload['label']}: read from {path.parent.relative_to(CFG.OUT) if path.is_relative_to(CFG.OUT) else path.parent}, not from the journal plate folder (PLATE_JOURNAL plates not rendered yet)")
        from PIL import Image
        with Image.open(path) as im:
            if abs(im.size[0] - PLATE_PX[0]) > 2 or abs(im.size[1] - PLATE_PX[1]) > 2:
                warnings.append(f"{payload['label']}: {im.size} px, expected {PLATE_PX}")
    return warnings


def build_article(lang: str, args, authors: list, affiliations: list, profile: Path) -> dict:
    P = PROSE[lang]
    V = prose_en.load_values(VARIANT)
    stubs: list[str] = []
    blocks, R = article_blocks(lang, V, stubs)
    blocks = m10.printed_blocks(blocks, lang, f"article_{VARIANT}_{lang}")      # the print glossary funnel
    blocks = normalise_figure_headings(blocks)
    wc = P.word_counts(blocks)
    keys = P.citation_keys(blocks)
    problems = check_budgets(blocks, lang, wc, keys)
    jc_budget = None
    if callable(getattr(JC, "budget_report", None)):
        try:
            jc_budget = JC.budget_report(blocks, lang)
        except Exception as exc:                               # the module's own report is informative only
            jc_budget = dict(error=f"{type(exc).__name__}: {exc}")
    counts = dict(summary=wc["summary"], panel=wc["panel"], core=wc["core_body"], refs=len(keys),
                  tables=wc["tables"], figures=wc["figures"], sfig=len(SUPP_FIGURES), stab=len(SUPP_TABLES))
    blocks = title_page(blocks, lang, P, authors, affiliations, counts)
    warnings = body_plate_check(blocks, lang)
    blocks, abbr_report = JC.expand_abbreviations(blocks, lang)
    before = blocks
    blocks = journal_text_blocks(blocks, lang)
    numbers = numbers_unchanged(before, blocks)
    if not numbers["ok"]:
        raise RuntimeError(f"the number pass changed a numeric value in article_{lang}: {numbers['mismatches'][:3]}")
    leftovers = ascii_decimals_left(blocks) if lang == SUBMISSION_LANG else []
    if problems:
        msg = f"article_{lang}: " + "; ".join(problems)
        if stubs or args.no_strict:
            warnings.append(msg)
            log("WARNING " + msg)
        else:
            raise RuntimeError(msg)
    out = OUT_DIR / f"article_{VARIANT}_{lang}.docx"
    with m10.localised_references(lang, journal=True):
        r = DB.build_document(blocks, lang, out, bib_path=P.BIB, journal=JOURNAL_DOC_FLAGS, embed_cache=EMBED_CACHE)
    # the body tables are printed landscape (plan, section 2) even when their longest words fit the column
    post = m10.postprocess_docx(out, lang, landscape_labels=tuple(p["label"] for k, p in blocks if k == "table"),
                                min_table_pt=JOURNAL_DOC_FLAGS.get("table_min_pt"))
    info = dict(path=str(out), size_mb=round(out.stat().st_size / 1e6, 1), builder=r, word_counts=wc,
                abbreviations_expanded=abbr_report,
                section_words=section_word_counts(before), citation_keys=keys, budgets_ok=not problems,
                budget_problems=problems, budget_report_journal_config=jc_budget,
                number_pass=dict(numbers, ascii_decimals_left=leftovers[:20]),
                postprocess=post, plates=m10.plate_summary(r), stubs=stubs, warnings=warnings,
                first_citation_order=(R.first_citation_order() if R is not None and hasattr(R, "first_citation_order") else None))
    if not args.skip_pdf:
        t0 = time.time()
        pdf = to_pdf(out, profile)
        info["review"] = review(out, pdf, lang, r.get("full_page_plates"), not args.skip_thumbs)
        info["review"]["pdf_seconds"] = round(time.time() - t0)
    return info


def build_supplement(args, authors: list, affiliations: list, profile: Path) -> dict:
    V = prose_en.load_values(VARIANT)
    stubs: list[str] = []
    blocks, R = supplement_blocks(V, stubs, args.limit_items)
    blocks = m10.printed_blocks(blocks, "en", f"supplement_{VARIANT}_en")
    # readers, round 2: tables wider than the landscape page at 8 pt are presented in parts (key columns
    # repeated), with internal heading rows and lettered footnotes; cells unchanged (journal_config.TABLE_LAYOUT)
    n_before = sum(1 for k, _ in blocks if k == "table")
    if callable(getattr(JC, "restructure_blocks", None)):
        blocks = JC.restructure_blocks(blocks, "en")
    parts = [(p["label"], p["df"].shape) for k, p in blocks if k == "table" and p.get("part", (1, 1))[1] > 1]
    blocks = normalise_figure_headings(blocks)
    counts = dict(sfig=sum(1 for k, _ in blocks if k == "figure"), stab=sum(1 for k, _ in blocks if k == "table"))
    blocks = title_page(blocks, "en", prose_en, authors, affiliations, counts, supplement=True)
    blocks = m10.mark_embed_dpi(blocks, 0, args.supp_dpi or None)
    # The appendix is read on its own, so it expands its abbreviations on its own.
    blocks, supp_abbr_report = JC.expand_abbreviations(blocks, "en")
    before = blocks
    blocks = journal_text_blocks(blocks, "en")
    numbers = numbers_unchanged(before, blocks)
    if not numbers["ok"]:
        raise RuntimeError(f"the number pass changed a numeric value in the supplement: {numbers['mismatches'][:3]}")
    leftovers = ascii_decimals_left(blocks)
    n_eq = sum(1 for k, _ in blocks if k == "eq")
    eq_numbers = [p[1] for k, p in blocks if k == "eq"]
    entries = toc_entries(blocks[toc_position(blocks)[1]:])          # only what follows the TOC
    out = OUT_DIR / f"supplement_{VARIANT}_en.docx"
    shutil.copyfile(LA / "analysis_plan.md", OUT_DIR / "analysis_plan_v1.0_es.md")
    toc_info: dict = dict(entries=len(entries), verified=False, passes=0)
    r = post = None
    toc_pages: set = set()
    if args.skip_pdf:
        doc_blocks = with_toc(blocks, entries, placeholder="—")
        with m10.localised_references("en", journal=True):
            r = DB.build_document(doc_blocks, "en", out, bib_path=prose_en.BIB, journal=SUPPLEMENT_DOC_FLAGS,
                                  embed_cache=EMBED_CACHE, supplementary_prefix=True)
        post = m10.postprocess_docx(out, "en", min_table_pt=SUPPLEMENT_DOC_FLAGS.get("table_min_pt"))
        toc_info["note"] = "--skip-pdf: table of contents written with placeholders, not verified"
    else:
        pdf = None
        for attempt in range(1, 4):
            doc_blocks = with_toc(blocks, entries)
            with m10.localised_references("en", journal=True):
                r = DB.build_document(doc_blocks, "en", out, bib_path=prose_en.BIB, journal=SUPPLEMENT_DOC_FLAGS,
                                      embed_cache=EMBED_CACHE, supplementary_prefix=True)
            post = m10.postprocess_docx(out, "en", min_table_pt=SUPPLEMENT_DOC_FLAGS.get("table_min_pt"))
            t0 = time.time()
            pdf = to_pdf(out, profile)
            texts = pdf_page_texts(pdf)
            found = locate_entries(texts, entries, W["contents"]["en"])
            toc_pages = toc_page_numbers(texts, entries, W["contents"]["en"])
            missing = [e["text"] for e, f in zip(entries, found) if f is None]
            toc_info.update(passes=attempt, pdf_seconds=round(time.time() - t0), missing=missing[:20])
            log(f"supplement pass {attempt}: {m10.pdf_pages(pdf)} pages, {len(missing)} TOC entries not located")
            if missing:
                raise RuntimeError(f"TOC entries not located in the PDF: {missing[:5]}")
            if all(e["page"] == f for e, f in zip(entries, found)):
                toc_info["verified"] = True
                break
            for e, f in zip(entries, found):
                e["page"] = f
        if not toc_info["verified"]:
            raise RuntimeError("the supplement table of contents did not stabilise in three passes")
        toc_info["pages"] = [(e["text"][:40], e["page"]) for e in entries]
    info = dict(path=str(out), size_mb=round(out.stat().st_size / 1e6, 1), builder=r, equations=n_eq,
                abbreviations_expanded=supp_abbr_report,
                equation_numbers=eq_numbers, equations_in_order=(eq_numbers == sorted(eq_numbers)),
                number_pass=dict(numbers, ascii_decimals_left=leftovers[:20]), postprocess=post,
                plates=m10.plate_summary(r), toc=toc_info, stubs=stubs, supp_dpi=args.supp_dpi,
                figures=counts["sfig"], tables=counts["stab"],
                table_parts=dict(tables=n_before, blocks=sum(1 for k, _ in blocks if k == "table"), parts=parts))
    if not args.skip_pdf:
        info["review"] = review(out, pdf, "en", r.get("full_page_plates"), not args.skip_thumbs, skip_pages=toc_pages)
    return info


# ---------------------------------------------------------------------------
# Journal plates (builder P's flag in common.py)
# ---------------------------------------------------------------------------
PLATE_SCRIPTS = (("08d_figure_dataflow.py", []), ("08a_figures_grd.py", []), ("08b_figures_rem.py", []),
                 ("08c_figures_triangulation.py", ["--variants", VARIANT]))


def render_plates() -> dict:
    import common
    if not hasattr(common, "plate_journal_mode"):
        raise SystemExit("common.py has no journal plate mode yet (PLATE_JOURNAL); cannot render the journal plates")
    before = _hash_tree(corpus_paths())
    env = dict(os.environ, PLATE_JOURNAL="1", PLATE_CHECK="strict")
    runs = []
    for script, extra in PLATE_SCRIPTS:
        t0 = time.time()
        res = subprocess.run([sys.executable, str(LA / "pipeline" / script), *extra], env=env, capture_output=True,
                             text=True, timeout=3600)
        runs.append(dict(script=script, rc=res.returncode, seconds=round(time.time() - t0),
                         tail=res.stdout[-800:] + res.stderr[-800:]))
        if res.returncode != 0:
            raise RuntimeError(f"{script} failed in journal plate mode:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
    after = _hash_tree(corpus_paths())
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed:
        raise RuntimeError(f"journal plate rendering changed {len(changed)} corpus file(s): {changed[:5]}")
    from PIL import Image
    plates = {}
    for lang in LANGS:
        for key in BODY_FIGURES:
            png = Path(PLATE_DIR[lang]) / f"{key}.png"
            if not png.is_file():
                raise RuntimeError(f"journal plate missing: {png}")
            with Image.open(png) as im:
                if abs(im.size[0] - PLATE_PX[0]) > 2 or abs(im.size[1] - PLATE_PX[1]) > 2:
                    raise RuntimeError(f"{png.name}: {im.size} px, expected {PLATE_PX}")
                plates[f"{lang}/{key}"] = list(im.size)
    controls_dir = CFG.OUT / "controls" / "journal"        # CFG.CONTROLS is the expected-values dictionary
    checks = controls_dir / "plate_check_journal.json"
    checks.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for f in sorted(controls_dir.glob("*_runlog.json")):
        try:
            records.append(dict(file=f.name, content=json.loads(f.read_text(encoding="utf-8"))))
        except ValueError:
            records.append(dict(file=f.name, content=None))
    checks.write_text(json.dumps(dict(date=dt.datetime.now().isoformat(timespec="seconds"), runs=runs, plates=plates,
                                      runlogs=records), indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return dict(runs=runs, plates=plates, corpus_unchanged=True, check_file=str(checks))


# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="en", choices=[*LANGS, "all"])
    ap.add_argument("--skip-pdf", action="store_true", help="no PDF, no thumbnails, TOC unverified")
    ap.add_argument("--skip-thumbs", action="store_true", help="PDF without thumbnails")
    ap.add_argument("--skip-supplement", action="store_true", help="article only")
    ap.add_argument("--skip-article", action="store_true", help="supplement only")
    ap.add_argument("--render-plates", action="store_true", help="re-render the four body plates in journal mode first")
    ap.add_argument("--no-strict", action="store_true", help="budget violations become warnings")
    ap.add_argument("--supp-dpi", type=int, default=SUPP_DPI_DEFAULT, help="embedding resolution of supplementary plates (0 = native)")
    ap.add_argument("--limit-items", type=int, default=None, help="STUB ONLY: first N figures/tables of Part B")
    args = ap.parse_args(argv)
    t0 = time.time()
    # the number-width guard of the tables measures the pieces LibreOffice cannot break (UAX #14: tied ranges,
    # signed numbers, «n/N» fractions with thin thousands spaces) for every document this build writes; the flag is
    # set here, not at import, so that a test importing this module keeps the corpus rule
    DB.set_journal_atoms(True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    langs = list(LANGS) if args.lang == "all" else [args.lang]
    corpus_before = _hash_tree(corpus_paths())
    authors, affiliations = m10.load_paper_authors()
    report = dict(date=dt.datetime.now().isoformat(timespec="seconds"), variant=VARIANT, langs=langs,
                  modules=dict(journal_config=JC is not None, prose_journal_en=PJ["en"] is not None,
                               prose_journal_es=PJ["es"] is not None, supplement_journal=SJ is not None),
                  doc_flags=dict(article=JOURNAL_DOC_FLAGS, supplement=SUPPLEMENT_DOC_FLAGS),
                  word_budget=WORD_BUDGET, protected_tokens=PROTECTED_TOKENS, documents={})
    if args.render_plates:
        report["plates_rendered"] = render_plates()
    profile = Path(tempfile.gettempdir()) / "study_lo_profile_journal"
    for lang in langs:
        if not args.skip_article:
            t1 = time.time()
            info = build_article(lang, args, authors, affiliations, profile)
            report["documents"][f"article_{lang}"] = info
            log(f"article_{lang}: {info['size_mb']} MB, {info['word_counts']['core_body']} words, "
                f"{len(info['citation_keys'])} refs, {info['builder']['tables']} tables, {info['builder']['figures']} "
                f"figures ({time.time() - t1:.0f} s); budgets {'ok' if info['budgets_ok'] else 'NOT ok'}; "
                f"pages {info.get('review', {}).get('pages', '—')}")
        if lang == SUBMISSION_LANG and not args.skip_supplement:
            t1 = time.time()
            info = build_supplement(args, authors, affiliations, profile)
            report["documents"]["supplement_en"] = info
            log(f"supplement_en: {info['size_mb']} MB, {info['figures']} figures, {info['tables']} tables, "
                f"{info['equations']} equations ({time.time() - t1:.0f} s); TOC verified: {info['toc']['verified']}; "
                f"pages {info.get('review', {}).get('pages', '—')}")
    changed = sorted(k for k, v in _hash_tree(corpus_paths()).items() if corpus_before.get(k) != v)
    report["corpus_unchanged"] = not changed
    if changed:
        log(f"WARNING: {len(changed)} corpus file(s) changed during the build: {changed[:5]}")
    stubs = sorted({s for d in report["documents"].values() for s in d.get("stubs", [])})
    report["provisional"] = bool(stubs) or any(d.get("warnings") for d in report["documents"].values())
    report["stubs"] = stubs
    report["seconds"] = round(time.time() - t0)
    # one report for the package: a partial run (one language, article only, supplement only) updates the
    # entries of the documents it built and keeps the others' entries from the previous run
    if REPORT_PATH.is_file():
        try:
            previous = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            kept = {k: v for k, v in (previous.get("documents") or {}).items() if k not in report["documents"]}
            if kept:
                report["documents"] = {**kept, **report["documents"]}
                report["documents_kept_from"] = previous.get("date")
        except ValueError:
            pass
    REPORT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    log(f"report: {REPORT_PATH}" + (f" (PROVISIONAL: stubs {stubs})" if stubs else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
