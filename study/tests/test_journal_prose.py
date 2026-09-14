"""Pruebas del paquete journal/ (tarea B2): journal_config, prose_journal_en y prose_journal_es.

Comprueban, sobre los bloques del artículo enviado (sin_rett): recuento de palabras por sección y total; el Resumen
(cinco párrafos rotulados, ≤ 250 palabras, sin referencias); el panel «Research in context» sin referencias; el tope de
30 referencias en el orden del plan; la numeración del apéndice por orden de primera cita; la paridad numérica entre el
inglés y el español, párrafo por párrafo; los cortes de las Tablas 1 y 2 (celdas idénticas al CSV, p recalculada); las
leyendas del cuerpo compuestas solo con fragmentos de las leyendas del corpus; el pase de número de la revista; y la
construcción de ambos DOCX con docx_builder.
"""
from collections import Counter
from pathlib import Path
import re
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "journal"))
import config as CFG  # noqa: E402
import supplementary_material as SM  # noqa: E402

HAS_OUTPUTS = (CFG.OUT / "values_sin_rett.json").is_file() and \
    (CFG.OUT / "sin_rett" / "en" / "figures" / "captions.json").is_file() and \
    (CFG.OUT / "sin_rett" / "es" / "extra" / "figures" / "captions.json").is_file() and \
    (CFG.TIDY / "spatial_moran.csv").is_file()

SUMMARY_LABELS = {"en": ["Background", "Methods", "Findings", "Interpretation", "Funding"],
                  "es": ["Antecedentes", "Métodos", "Resultados", "Interpretación", "Financiamiento"]}


def _numbers(text):
    """Multiset of number tokens (≥ 2 digits or with a separator) with separators removed; the mid-height point of
    the English text and the Spanish ordinal markers are normalised away."""
    t = re.sub(r"\[@[^\]]+\]", "", str(text)).replace("·", ".")
    t = re.sub(r"\d+\.º", "", t)
    out = []
    for m in re.findall(r"\d[\d.,]*", t):
        m = m.rstrip(".,")
        d = re.sub(r"[^\d]", "", m)
        if len(d) >= 2 or ("." in m or "," in m):
            out.append(d)
    return Counter(out)


def _paragraphs(blocks):
    return [str(p) for k, p in blocks if k == "p"]


def _section_paragraphs(blocks, h1):
    out, on = [], False
    for k, p in blocks:
        if k == "h1":
            on = p == h1
        elif on and k == "p":
            out.append(str(p))
    return out


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_sin_rett.json, las láminas/tablas por idioma y outputs/tidy")
class JournalProseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import journal_config as JC
        import prose_en as PE
        import prose_es as PS
        import prose_journal_en as JE
        import prose_journal_es as JS
        cls.JC, cls.PE, cls.PS, cls.JE, cls.JS = JC, PE, PS, JE, JS
        cls.V = PE.load_values("sin_rett")
        # the corpus plate folder stands in for the journal plates (rendered by the plate task) in these tests
        cls.plates = {lang: CFG.OUT / "sin_rett" / lang / "figures" for lang in ("en", "es")}
        cls.en = JE.article(cls.V, plate_dir=cls.plates["en"])
        cls.es = JS.article(cls.V, plate_dir=cls.plates["es"])

    # ---------------- lengths ----------------
    def test_word_budgets(self):
        JC, PE = self.JC, self.PE
        wc = PE.word_counts(self.en)
        self.assertGreaterEqual(wc["core_body"], JC.WORD_BUDGET["core_body_min"], wc)
        self.assertLessEqual(wc["core_body"], JC.WORD_BUDGET["core_body_max"], wc)
        self.assertTrue(3500 <= wc["core_body"] <= 5000, wc)          # the journal's own limits
        self.assertLessEqual(wc["summary"], JC.WORD_BUDGET["summary"], wc)
        self.assertLessEqual(wc["panel"], JC.WORD_BUDGET["panel"], wc)
        self.assertEqual(wc["opt_paragraphs"], 0, "no [OPT] paragraph may remain")
        rep = JC.budget_report(self.en, "en")
        self.assertEqual(rep["over_budget"], [], rep)
        legends = self.JE.legend_word_counts(self.en)
        self.assertEqual(sorted(legends), ["Figure 1", "Figure 2", "Figure 3", "Figure 4"])
        self.assertLessEqual(legends["Figure 1"], JC.WORD_BUDGET["legend_fig1_max"], legends)
        for label, n in legends.items():
            self.assertLessEqual(n, JC.WORD_BUDGET["legend_max"], legends)
        # the Spanish twin is the same text expanded: within the corpus ratio of 0.9–1.3 for every count
        wc_es = self.PS.word_counts(self.es)
        for key in ("summary", "panel", "core_body", "declarations"):
            ratio = wc_es[key] / wc[key]
            self.assertTrue(0.9 <= ratio <= 1.3, f"{key}: es={wc_es[key]} en={wc[key]} ratio={ratio:.2f}")

    def test_summary_structure_and_no_references(self):
        for lang, blocks, h1 in (("en", self.en, "Summary"), ("es", self.es, "Resumen")):
            summary = _section_paragraphs(blocks, h1)
            self.assertEqual(len(summary), 5, lang)
            self.assertEqual([p.split("**")[1] for p in summary], SUMMARY_LABELS[lang], lang)
            for p in summary:
                self.assertNotIn("[@", p, f"{lang}: the Summary carries no reference")
                self.assertIsNone(re.search(r"\(\d{1,2}(?:[,–-]\d{1,2})*\)", p), f"{lang}: citation-like token in the Summary")
            # bold only for the five labels
            for p in summary:
                self.assertEqual(p.count("**"), 2, p[:40])
        for blocks in (self.en, self.es):
            for kind, p in blocks:
                if kind == "p" and not p.startswith("**"):
                    self.assertNotIn("**", p, "no bold for emphasis outside the Summary labels")

    def test_panel_has_sources_dates_and_no_references(self):
        for lang, blocks, title, first in (("en", self.en, "Research in context", "Evidence before this study"),
                                           ("es", self.es, "Investigación en contexto", "Evidencia previa a este estudio")):
            panels = [p for k, p in blocks if k == "panel"]
            self.assertEqual(len(panels), 1, lang)
            panel = panels[0]
            self.assertEqual(panel["title"], title)
            self.assertEqual(len(panel["items"]), 3)
            self.assertEqual(panel["items"][0][0], first)
            evidence = panel["items"][0][1]
            for needle in ("PubMed", "Crossref", "2026", "\"autism\"", "\"Chile\""):
                self.assertIn(needle, evidence, lang)
            for _, text in panel["items"]:
                self.assertNotIn("[@", text, f"{lang}: the panel carries no reference")
                self.assertIsNone(re.search(r"\(\d{1,2}(?:[,–-]\d{1,2})*\)", text), lang)
        self.assertIn("rehabilitation", dict(self.en[[i for i, (k, _) in enumerate(self.en) if k == "panel"][0]][1]["items"])["Added value of this study"])

    # ---------------- references ----------------
    def test_references_are_the_plan_list_in_order(self):
        JC, PE = self.JC, self.PE
        keys_en = PE.citation_keys(self.en)
        keys_es = PE.citation_keys(self.es)
        self.assertEqual(keys_en, JC.REFERENCE_KEYS)
        self.assertEqual(keys_es, JC.REFERENCE_KEYS)
        self.assertEqual(len(keys_en), 30)
        self.assertFalse(set(keys_en) & set(JC.DROPPED_REFERENCE_KEYS))
        sys.path.insert(0, str(ROOT.parent / "paper"))
        from references import parse_bib
        entries = parse_bib(PE.BIB)
        for key in keys_en:
            self.assertIn(key, entries)
        # the dataset citations appear only in the "Official sources" paragraph
        datasets = [k for k in keys_en if k in ("fonasa_grd", "deis_egresos", "minsal_rem", "ine2019", "fonasa_beneficiarios",
                                                 "endide2022", "encavi2023", "mineduc_apuntes60", "mineduc_sinaces2026", "junaeb_eve")]
        self.assertEqual(len(datasets), 10)
        carrying = [p for p in _paragraphs(self.en) if "[@fonasa_grd" in p]
        self.assertEqual(len(carrying), 1)
        for key in datasets:
            self.assertEqual(sum(f"@{key}" in p for p in _paragraphs(self.en)), 1, key)

    # ---------------- appendix numbering ----------------
    def _first_citations(self, blocks, fig_word, tab_word):
        texts = []
        for kind, payload in blocks:
            if kind == "p":
                texts.append(str(payload))
            elif kind == "panel":
                texts += [t for _, t in payload["items"]]
            elif kind == "table":
                texts += [payload.get("title", ""), payload.get("note", "")]
            elif kind == "figure":
                texts.append(payload.get("caption", ""))
        text = " ".join(texts)
        order = {}
        rx = re.compile(rf"\b({fig_word}|{tab_word})s?\s+(S?)(\d+)(?:\s*[–-]\s*(S?)(\d+))?")
        for m in rx.finditer(text):
            word, s1, n1, s2, n2 = m.groups()
            nums = [int(n1)] if n2 is None else list(range(int(n1), int(n2) + 1))
            for n in nums:
                order.setdefault((word, bool(s1)), []).append(n)
        first = {}
        for key, seq in order.items():
            seen, out = set(), []
            for n in seq:
                if n not in seen:
                    seen.add(n)
                    out.append(n)
            first[key] = out
        return first

    def test_supplement_items_are_cited_in_ascending_order_and_completely(self):
        JC = self.JC
        for blocks, fw, tw in ((self.en, "Figure", "Table"), (self.es, "Figura", "Tabla")):
            first = self._first_citations(blocks, fw, tw)
            self.assertEqual(first[(fw, True)], list(range(1, len(JC.SUPP_FIGURES) + 1)), fw)
            self.assertEqual(first[(tw, True)], list(range(1, len(JC.SUPP_TABLES) + 1)), tw)
            self.assertEqual(first[(fw, False)], list(range(1, len(JC.BODY_FIGURES) + 1)), fw)
            self.assertEqual(first[(tw, False)], list(range(1, len(JC.BODY_TABLES) + 1)), tw)
        # the plan's frozen anchors
        self.assertEqual(JC.SUPP_TABLES.index("T1_sources") + 1, 12)
        self.assertEqual(JC.SUPP_TABLES.index("S_reporting_checklist") + 1, 11)
        self.assertEqual(JC.SUPP_TABLES.index("E80_tidy_data_dictionary") + 1, 91)
        self.assertEqual(JC.SUPP_FIGURES.index("fig1_sources_coverage") + 1, 1)
        self.assertEqual(JC.SUPP_FIGURES.index("figE26b_sex_ratio_multisource") + 1, 36)

    def test_supplement_assets_exist(self):
        JC = self.JC
        for lang in ("en", "es"):
            for key in JC.SUPP_FIGURES:
                self.assertTrue(JC.asset_path(key, "figure", lang).is_file(), (lang, key))
            for key in JC.SUPP_TABLES:
                if key in JC.SYNTHETIC_TABLES:
                    continue
                self.assertTrue(JC.asset_path(key, "table", lang).is_file(), (lang, key))
        with self.assertRaises(KeyError):
            JC.asset_path("figS4_grd_model_sensitivities", "figure", "en")   # legacy, unregistered plate
        with self.assertRaises(KeyError):
            JC.asset_path("EF1_seasonality_monthly", "figure", "en")          # dropped item

    # ---------------- parity ----------------
    def test_numeric_parity_en_es(self):
        pe, ps = _paragraphs(self.en), _paragraphs(self.es)
        self.assertEqual(len(pe), len(ps))
        self.assertEqual([k for k, _ in self.en], [k for k, _ in self.es])
        for i, (a, b) in enumerate(zip(pe, ps)):
            self.assertEqual(_numbers(a), _numbers(b), f"¶{i}: {a[:70]!r} / {b[:70]!r}")
        items_en = [p for k, p in self.en if k in ("figure", "table")]
        items_es = [p for k, p in self.es if k in ("figure", "table")]
        self.assertEqual([p["label"] for p in items_en], ["Table 1", "Table 2", "Figure 1", "Figure 2", "Figure 3", "Figure 4"])
        self.assertEqual([p["label"] for p in items_es], ["Tabla 1", "Tabla 2", "Figura 1", "Figura 2", "Figura 3", "Figura 4"])
        for a, b in zip(items_en, items_es):
            ta = a.get("caption") or a.get("note")
            tb = b.get("caption") or b.get("note")
            self.assertEqual(_numbers(ta), _numbers(tb), a["label"])
            if "df" in a:
                self.assertEqual(a["df"].shape, b["df"].shape, a["label"])

    # ---------------- display items ----------------
    def test_table_cuts_match_the_csv(self):
        JC = self.JC
        t1, t2 = [p for k, p in self.en if k == "table"]
        # 22, not 25: the three-row «Definition sensitivity» block left the body when the submission stopped
        # carrying two case definitions; the comparison is Figure S2 and Table S24 of the appendix.
        self.assertEqual(len(t1["df"]), 22)
        self.assertEqual(len(t2["df"]), 29)
        full = pd.read_csv(CFG.OUT / "sin_rett" / "en" / "tables" / "T2_grd_core.csv", dtype=str, keep_default_na=False)
        rows = {(r["Block"], r["Indicator"]): r for _, r in full.iterrows()}
        for _, r in t1["df"].iterrows():
            src = rows[(r["Block"], r["Indicator"])]
            for col in t1["df"].columns:
                self.assertEqual(r[col], src[col], (r["Indicator"], col))
        # Table 2 keeps every cell of the CSV except the case-definition stamp, which is presentation only.
        full2 = pd.read_csv(CFG.OUT / "sin_rett" / "en" / "tables" / "T7_models.csv", dtype=str, keep_default_na=False)
        stamped = [v for v in full2["Series / variant"] if "Rett" in v]
        self.assertTrue(stamped, "the corpus column should carry the stamp this cut removes")
        self.assertEqual([v for v in t2["df"]["Series"] if "Rett" in v], [])
        self.assertNotIn("mean (median)", " ".join(t1["df"]["Indicator"]))
        self.assertIn("n (% of episodes with F84)", " ".join(t1["df"]["Indicator"]))
        full7 = pd.read_csv(CFG.OUT / "sin_rett" / "en" / "tables" / "T7_models.csv", dtype=str, keep_default_na=False)
        num = pd.read_csv(CFG.OUT / "sin_rett" / "en" / "tables" / "T7_models_numeric.csv", dtype=str, keep_default_na=False)
        ids = list(num["model_id"])
        rename = JC.TABLE_COLUMN_RENAME.get("T7_models", {}).get("en", {})
        self.assertEqual(list(t2["df"].columns), [rename.get(c, c) for c in JC.TABLE_COLUMNS["T7_models"]])
        self.assertNotIn("Notes", t2["df"].columns)
        for j, model_id in enumerate(JC.TABLE_ROWS["T7_models"]):
            i = ids.index(model_id)
            back = {v: k for k, v in rename.items()}
            for col in t2["df"].columns:
                src_col = back.get(col, col)
                if col == "p value (Wald)":
                    self.assertEqual(t2["df"].iloc[j][col], JC.format_p(float(num.iloc[i]["p_value"])))
                elif src_col in JC.TABLE_CELL_REWRITE.get("T7_models", {}):
                    # the stamp is removed; everything else in the cell is byte-identical to the CSV
                    expected = full7.iloc[i][src_col]
                    for old_s, new_s in JC.TABLE_CELL_REWRITE["T7_models"][src_col]["en"]:
                        expected = expected.replace(old_s, new_s)
                    self.assertEqual(t2["df"].iloc[j][col], expected.strip(), (model_id, col))
                else:
                    self.assertEqual(t2["df"].iloc[j][col], full7.iloc[i][src_col], (model_id, col))
        self.assertFalse(any("< 0.001" in v for v in t2["df"]["p value (Wald)"]))
        self.assertTrue(all(re.fullmatch(r"<0·0001|0·\d+|1·0", v) for v in t2["df"]["p value (Wald)"]), list(t2["df"]["p value (Wald)"]))
        self.assertEqual(t1["heading_column"], "Block")
        self.assertEqual(t2["heading_column"], "Estimand")
        for tbl in (t1, t2):
            self.assertEqual(tbl["font_pt"], 8)
            self.assertIn("administrative recognition, not prevalence or incidence", tbl["note"])

    def test_body_figures_and_legends(self):
        JC = self.JC
        figs = [p for k, p in self.en if k == "figure"]
        self.assertEqual([p["label"] for p in figs], ["Figure 1", "Figure 2", "Figure 3", "Figure 4"])
        R = JC.JournalRegistry("en")
        for p, key in zip(figs, JC.BODY_FIGURES):
            self.assertEqual(Path(p["path"]).name, f"{key}.png")
            self.assertEqual(p["embed_dpi"], 600)
            self.assertTrue(p["caption"].startswith(p["heading"] + ". "))
            self.assertEqual(p["heading"], R.heading_of(key))
            self.assertNotIn("Figure 3.", p["heading"])           # provisional numbers stripped
            # The case definition is stated once in Methods, not stamped on every heading and legend.
            self.assertNotIn("Rett", p["heading"])
            self.assertNotIn("the deposited data", p["caption"])
            legend = p["caption"][len(p["heading"]) + 2:]
            source = R.caption_text(key)
            for tok in re.findall(r"\d[\d.,]*", re.sub(r"\b(?:Figure|Table)s?\s+S?\d+", "", legend)):
                self.assertIn(tok.rstrip(".,"), source, f"{key}: number {tok!r} not in the corpus caption")
        # standing-rule sentences of the legends
        by = {p["label"]: p["caption"] for p in figs}
        self.assertIn("No record is linked across systems", by["Figure 1"])
        self.assertIn("place of care", by["Figure 2"])
        self.assertIn("never share an axis", by["Figure 3"])
        self.assertIn("indices, not comparable levels", by["Figure 4"])
        self.assertIn("not a probability", by["Figure 4"])
        # journal plates are read from the journal plate folder in the real build
        real = self.JE.article(self.V)
        for p, key in zip([p for k, p in real if k == "figure"], JC.BODY_FIGURES):
            self.assertEqual(Path(p["path"]), JC.PLATE_DIR["en"] / f"{key}.png")

    # ---------------- language rules ----------------
    def test_standing_rules_and_house_style(self):
        text = " ".join(_paragraphs(self.en)).lower()
        for banned in ("hospitalisations for autism", "hospitalizations for", "care cascade", "prevalence of autism increased",
                       "caused by law 21.545", "attributable to law 21.545", "effect of law 21.545 was", "real increase in autism",
                       "trough in 2020", "quantifies the contribution", "conversion probability", "[opt]"):
            self.assertNotIn(banned, text, banned)
        for p in _paragraphs(self.en) + _paragraphs(self.es):
            if p.strip() in ("None.", "Ninguno.") or p.startswith(("**Funding**", "**Financiamiento**")):
                continue
            self.assertIsNone(re.search(r"\bNone\b|\bnan\b", p), p[:80])
        self.assertIn("iqr", text)
        self.assertNotIn("interquartile range", text)
        self.assertIn("no disability was inferred from a diagnosis", text)
        self.assertIn("sager", text)
        self.assertIn("coverage comparison between two unlinked registries of the same event and not a probability", text)
        # numbers one to ten in words: the frequent counts of small hospitals/students
        self.assertIn("three hospitals having joined in 2023 and four more in 2024", text)
        self.assertIn("difference of five students", text)
        for h in ("Summary", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "Contributors",
                  "Declaration of interests", "Data sharing statement", "Funding", "Acknowledgements",
                  "Declaration of the use of artificial intelligence"):
            self.assertIn(h, [p for k, p in self.en if k == "h1"])
        self.assertEqual([k for k, _ in self.en if k in ("refs", "table", "figure")],
                         ["refs", "table", "table", "figure", "figure", "figure", "figure"])
        # author-supplied placeholders stay bracketed, never invented
        decl = " ".join(_section_paragraphs(self.en, "Contributors") + _section_paragraphs(self.en, "Data sharing statement"))
        self.assertIn("[Second author, to be named before submission]", decl)
        self.assertIn("[URL and DOI to be inserted at acceptance]", decl)
        self.assertNotIn("undecided", decl.lower())

    # ---------------- the number pass and the remap ----------------
    def test_journal_text_number_pass(self):
        JC = self.JC
        S = JC.NNBSP
        self.assertEqual(JC.journal_text("202.7 per 100,000; 13,155; 2,334; F84.2; 05990022; Law 21.545; Python 3.14; 1,012,345", "en"),
                         f"202·7 per 100{S}000; 13{S}155; 2334; F84.2; 05990022; Law 21.545; Python 3.14; 1{S}012{S}345")
        self.assertEqual(JC.journal_text("grd_rate:sin_rett:observed:all:any:none:2019-2024 T7_models.csv v1.0", "en"),
                         "grd_rate:sin_rett:observed:all:any:none:2019-2024 T7_models.csv v1.0")
        # Spanish keeps the corpus number conventions, and the range dash stays BARE. Round 2 tied it with a
        # WORD JOINER on both sides so no line could open with "–42,1"; measured on the built page that costs a
        # real 1·49 pt gap ("30,0 –42,1"), because the joiner is a word boundary and justification stretches at
        # it (char geometry of article p 26, pdftotext -bbox-layout). The en dash is already "break after" in
        # Unicode, so a bare range breaks as "30,0–" / "42,1", which is what the journal's type wants.
        self.assertEqual(JC.journal_text("35,9 % (IC 95 % 30,0–42,1)", "es"), "35,9 % (IC 95 % 30,0\ufeff–42,1)")
        self.assertEqual(JC.journal_text("2019–2024 and 30·0–42·1", "en"), "2019\ufeff–2024 and 30·0\ufeff–42·1")
        # one joiner, and only before the dash: a line may still break after it
        self.assertNotIn("–\ufeff", JC.journal_text("2019–2024", "en"))
        self.assertEqual(JC.journal_text("30,0–42,1", "es", cells=True), "30,0–42,1")
        self.assertEqual(JC.format_p(2.7e-41), "<0·0001")
        self.assertEqual(JC.format_p(0.0157), "0·016")
        self.assertEqual(JC.format_p(0.5), "0·50")
        self.assertEqual(JC.format_p(0.0157, "es"), "0,016")
        passed = JC.journal_text_blocks(self.en, "en")
        protected = re.compile("|".join(f"(?:{p})" for p in JC.PROTECTED_TOKENS))
        for kind, payload in passed:
            if kind == "p":
                masked = protected.sub("", str(payload))
                self.assertIsNone(re.search(r"(?<=\d)\.(?=\d)", masked), payload[:80])
                self.assertIsNone(re.search(r"\d,\d{3}\b", masked), payload[:80])
        tables = [p for k, p in passed if k == "table"]
        self.assertIn(f"100{S}000", tables[0]["df"]["Indicator"].iloc[6])
        self.assertTrue(all("·" in v for v in tables[1]["df"]["APC % (95% CI)"]))

    def test_remap_refs(self):
        JC = self.JC
        # corpus numbering: Table 5 = T6_education, Table 6 = T7_models, Table 7 = T8_controls_compact; Figure 2 = fig1_sources_coverage;
        # corpus Table S27 = F3_rem_pathway_data, a dropped duplicate whose token is remapped to its kept twin T3_rem_pathway
        # (journal_config.DROPPED_ALIASES); a dropped item without a twin becomes "the deposited data"
        self.assertEqual(JC.remap_refs("Figure S9 and Table S27 and Table 5 and Figure 2 and Figure 3c", "en"),
                         f"Figure S28 and {JC.remap_refs('Table S27', 'en')} and Table S{JC.SUPP_TABLES.index('T6_education') + 1} and Figure S1 and Figure 2c")
        self.assertEqual(JC.remap_refs("Table S27", "en"), f"Table S{JC.SUPP_TABLES.index('T3_rem_pathway') + 1}")
        dropped_no_twin = SM.TABLE_ORDER.index("E2_grd_length_of_stay") + 1
        self.assertEqual(JC.remap_refs(f"Table S{dropped_no_twin}", "en"), "the deposited data")
        self.assertEqual(JC.remap_refs("Table 6 and Table 7", "en"), "Table 2 and Table S34")
        self.assertEqual(JC.remap_refs("Tables S3–S12", "en"), "Tables S1–S10")
        self.assertEqual(JC.remap_refs("(Apuntes 60, Table 6)", "en"), "(Apuntes 60, Table 6)")
        self.assertEqual(JC.remap_refs("la Figura S9 y la Tabla 5", "es"),
                         f"la Figura S28 y la Tabla S{JC.SUPP_TABLES.index('T6_education') + 1}")
        self.assertEqual(JC.remap_refs("Table 1", "en"), "Table 1")      # T2_grd_core stays Table 1

    # ---------------- the documents ----------------
    def test_docx_builds_in_both_languages(self):
        from docx_builder import build_document
        with tempfile.TemporaryDirectory() as tmp:
            for lang, blocks in (("en", self.JC.journal_text_blocks(self.en, "en")), ("es", self.es)):
                rep = build_document(blocks, lang, Path(tmp) / f"article_{lang}.docx", bib_path=self.PE.BIB)
                self.assertEqual((rep["tables"], rep["figures"], rep["references"]), (2, 4, 30), lang)
                self.assertGreater((Path(tmp) / f"article_{lang}.docx").stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
