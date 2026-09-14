# -*- coding: utf-8 -*-
"""Tests of `journal/supplement_journal.py` — the ONE English supplementary appendix of the journal submission.

Without outputs (registry only):
  * sizes (36 figures, 91 tables, the 10 methodological tables + the checklist first), no duplicates, S-numbers
    ascending with the article paragraph that first cites each item, every key traceable to the corpus registry
    (or a relocated body item, or the synthetic checklist), a presentation text for every item;
  * agreement with `journal_config.SUPP_FIGURES` / `SUPP_TABLES` when that module is importable;
  * the STROBE + RECORD checklist (35 rows, English, every S-number within range, statuses from the closed set);
  * the analysis-plan rendering (version 1.0, 4 September 2026, the seven headings);
  * the local cross-reference remap and the citation parser (ranges and lists);
  * "es" refused; the study's forbidden phrases absent from the module's own English text.

With outputs (values, captions, titles, plates and tables of sin_rett/en):
  * the assembled appendix prints the 33 equations once each, in numeric order, under a heading that cites them;
  * Tables S1–S91 and Figures S1–S36 in order, each preceded by its presentation paragraph; Part A before Part B;
    the appendix references last, with their own title;
  * no corpus-numbered cross-reference survives in a caption, title or note (remap applied once);
  * every asset exists on disk;
  * BOTH directions of the cross-reference with the journal article (`prose_journal_en.article`): every S-item
    the article cites exists, every item of the appendix is cited at least once, first citations ascend — skipped
    with a reason while that module is not importable.
"""
from pathlib import Path
import re
import sys
import unittest

LA = Path(__file__).resolve().parents[1]
for _p in (str(LA), str(LA / "journal")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as CFG  # noqa: E402
import equations_lancet as EQ  # noqa: E402
import prose_en as PE  # noqa: E402
import prose_methods_extended as PME  # noqa: E402
import supplementary_material as SM  # noqa: E402
import supplement_journal as SJ  # noqa: E402

BASE = CFG.OUT / "sin_rett" / "en"
HAS_OUTPUTS = (CFG.OUT / "values_sin_rett.json").is_file() and all(
    (BASE / sub / name).is_file() for sub, name in (("figures", "captions.json"), ("extra/figures", "captions.json"),
                                                    ("tables", "titles.json"), ("extra/tables", "titles.json")))

#: Phrases the standing rules forbid (plan section 8, R6), checked on the text THIS module writes.
FORBIDDEN = ["prevalence of autism", "incidence of autism", "hospitalisations for autism", "hospitalizations for",
             "cascade", "conversion", "effect of Law", "caused by", "attributable to the law", "trough in 2020",
             "quantifies the contribution of reporting"]


def _own_texts() -> list[str]:
    """Every English string this module writes itself (templates, checklist, plan, headings)."""
    texts = list(SJ.FIGURE_SHOWS_EXTRA.values()) + list(SJ.FIGURE_ADDS.values()) + list(SJ.TABLE_INTROS.values())
    texts += [SJ.CHECKLIST_TITLE, SJ.CHECKLIST_NOTE, SJ.VARIANT_SENTENCE, SJ.PART_A_H1, SJ.PART_B_H1]
    texts += [rec + " " + where for _, rec, where, _ in SJ._STROBE + SJ._RECORD]
    for kind, payload in SJ.analysis_plan_blocks():
        texts += [str(x) for x in payload] if kind == "bullets" else [str(payload)]
    return texts


class RegistryTest(unittest.TestCase):
    def test_sizes_and_uniqueness(self):
        self.assertEqual(len(SJ.SUPP_FIGURES), 36)
        self.assertEqual(len(SJ.SUPP_TABLES), 91)
        self.assertEqual(len(set(SJ.SUPP_FIGURES)), 36)
        self.assertEqual(len(set(SJ.SUPP_TABLES)), 91)
        self.assertEqual(SJ.SUPP_TABLES[:11], list(PME.TABLE_KEYS) + [SJ.CHECKLIST_KEY])
        self.assertEqual(SJ.PART_A_TABLES, SJ.SUPP_TABLES[:11])

    def test_numbers_ascend_with_first_citation(self):
        for items in (SJ.FIGURES, SJ.TABLES):
            idx = [SJ.SECTION_INDEX[s] for _, s in items]
            self.assertEqual(idx, sorted(idx))
        SJ._check_registry_order()   # raises on a violation

    def test_every_key_is_traceable(self):
        for key in SJ.SUPP_FIGURES:
            self.assertTrue(key in SM.FIGURE_ORDER or key in PE.MAIN_FIGURES, key)
        for key in SJ.SUPP_TABLES:
            self.assertTrue(key in SM.TABLE_ORDER or key in PE.MAIN_TABLES or key == SJ.CHECKLIST_KEY, key)
        # the four body figures and the two body tables of the journal never appear in the appendix
        self.assertFalse(set(SJ.BODY_FIGURES) & set(SJ.SUPP_FIGURES))
        # T2 and T7 ARE reprinted in full (Tables S37 and S82): the body prints a cut of them
        self.assertIn("T2_grd_core", SJ.SUPP_TABLES)
        self.assertIn("T7_models", SJ.SUPP_TABLES)

    def test_presentation_text_for_every_item(self):
        for key in SJ.SUPP_FIGURES:
            self.assertIn(key, SJ.FIGURE_ADDS)
            self.assertTrue(key in SM.FIGURE_INTRO or key in SJ.FIGURE_SHOWS_EXTRA, key)
        for key in SJ.SUPP_TABLES[len(SJ.PART_A_TABLES):]:
            self.assertIn(key, SJ.TABLE_INTROS)
            self.assertIn("{L}", SJ.TABLE_INTROS[key])
        self.assertEqual(set(SJ.FIGURE_ADDS), set(SJ.SUPP_FIGURES))
        self.assertEqual(set(SJ.TABLE_INTROS), set(SJ.SUPP_TABLES[len(SJ.PART_A_TABLES):]))

    def test_agrees_with_journal_config_when_present(self):
        try:
            import journal_config as JC
        except Exception:  # noqa: BLE001
            self.skipTest("journal_config not importable yet")
        self.assertEqual(list(JC.SUPP_FIGURES), SJ.SUPP_FIGURES)
        self.assertEqual(list(JC.SUPP_TABLES), SJ.SUPP_TABLES)
        self.assertEqual(list(JC.BODY_FIGURES), SJ.BODY_FIGURES)
        self.assertEqual(list(JC.BODY_TABLES), SJ.BODY_TABLES)

    def test_spanish_is_refused(self):
        with self.assertRaises(NotImplementedError):
            SJ.blocks("es", {})

    def test_forbidden_phrases_absent_from_own_text(self):
        joined = "\n".join(_own_texts()).lower()
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase.lower(), joined, phrase)
        self.assertNotIn("[@", joined)
        self.assertNotIn("[opt]", joined)


class ChecklistTest(unittest.TestCase):
    def test_shape_and_content(self):
        df = SJ.checklist_table()
        self.assertEqual(list(df.columns), ["Item", "Recommendation", "Where reported", "Status"])
        self.assertEqual(len(df), 35)
        self.assertEqual(sum(df["Item"].str.startswith("STROBE")), 22)
        self.assertEqual(sum(df["Item"].str.startswith("RECORD")), 13)
        self.assertTrue((df["Where reported"].str.len() > 0).all())
        self.assertTrue(set(df["Status"]) <= {SJ._STATUS_REPORTED, SJ._STATUS_LIMITATION, SJ._STATUS_NA,
                                              SJ._STATUS_AUTHOR})
        self.assertEqual(df.loc[df["Item"] == "RECORD 12.2", "Status"].item(), SJ._STATUS_NA)

    def test_every_cited_number_is_within_the_journal_registry(self):
        df = SJ.checklist_table()
        for where in df["Where reported"]:
            for kind, n in SJ._supp_citations(where):
                limit = len(SJ.SUPP_FIGURES) if kind == "Figure" else len(SJ.SUPP_TABLES)
                self.assertTrue(1 <= n <= limit, f"{kind} S{n}: {where}")
            for m in re.finditer(r"\b(Figure|Table) (\d+)\b", where):
                limit = len(SJ.BODY_FIGURES) if m.group(1) == "Figure" else len(SJ.BODY_TABLES)
                self.assertTrue(1 <= int(m.group(2)) <= limit, m.group(0))
        # no unformatted placeholder survives
        self.assertFalse(df["Where reported"].str.contains(r"\{", regex=True).any())


class AnalysisPlanTest(unittest.TestCase):
    def test_rendering(self):
        blocks = SJ.analysis_plan_blocks()
        self.assertEqual(blocks[0][0], "h2")
        self.assertIn("version 1.0", blocks[0][1])
        self.assertIn("4 September 2026", blocks[0][1])
        h3 = [p for k, p in blocks if k == "h3"]
        self.assertEqual(h3, ["Principal question", "Conceptual DAG (simple)", "Sources, units and linkage",
                              "Definition variants (two complete analyses)", "Estimands and hierarchy",
                              "Pre-specified modelling and sensitivity", "Exclusions and rules"])
        estimands = next(p for k, p in blocks if k == "bullets" and str(p[0]).startswith("Primary hospital"))
        self.assertEqual(len(estimands), 8)

    def test_source_stamp_is_asserted(self):
        self.assertIn(f"**Versión:** {SJ.ANALYSIS_PLAN_VERSION}, {SJ.ANALYSIS_PLAN_DATE_ES}",
                      SJ.ANALYSIS_PLAN_MD.read_text(encoding="utf-8"))


class RemapAndParserTest(unittest.TestCase):
    def test_local_remap(self):
        # corpus main Table 6 = MAIN_TABLES[5] = T7_models -> journal Table 2; corpus Table 2 = T3 -> Table S49
        t7 = PE.MAIN_TABLES.index("T7_models") + 1
        self.assertEqual(SJ._local_remap(f"see Table {t7} here"), "see Table 2 here")
        t3 = PE.MAIN_TABLES.index("T3_rem_pathway") + 1
        self.assertEqual(SJ._local_remap(f"(Table {t3})"), f"(Table S{SJ.SUPP_TABLES.index('T3_rem_pathway') + 1})")
        # corpus supplementary figure -> journal number; a dropped plate -> the deposited data
        kept = SM.FIGURE_ORDER.index("figS2_grd_subcodes") + 1
        self.assertEqual(SJ._local_remap(f"Figure S{kept}"), f"Figure S{SJ.SUPP_FIGURES.index('figS2_grd_subcodes') + 1}")
        dropped = SM.FIGURE_ORDER.index("EF1_seasonality_monthly") + 1
        self.assertEqual(SJ._local_remap(f"Figure S{dropped}b"), SJ.DROPPED_TEXT)
        # main figure with a panel letter keeps the letter; an out-of-range number is left alone
        f4 = PE.MAIN_FIGURES.index("fig4_triangulation") + 1
        self.assertEqual(SJ._local_remap(f"Figure {f4}c"), "Figure 4c")
        self.assertEqual(SJ._local_remap("Table 99"), "Table 99")

    def test_citation_parser_expands_ranges_and_lists(self):
        text = "Tables S27–S29, Figures S12–S13 and Tables S45 and S46; Table S13 and 2021–2024 (Table S6)."
        self.assertEqual(list(SJ._supp_citations(text)),
                         [("Table", 27), ("Table", 28), ("Table", 29), ("Figure", 12), ("Figure", 13),
                          ("Table", 45), ("Table", 46), ("Table", 13), ("Table", 6)])
        self.assertEqual(SJ.cited_items([("p", "Figure S3 then Tables S1–S3.")])["table_numbers"], [1, 2, 3])


@unittest.skipUnless(HAS_OUTPUTS, "requires outputs/values_sin_rett.json and the sin_rett/en captions and titles")
class AssembledAppendixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.V = PE.load_values("sin_rett")
        cls.out = SJ.build("en", cls.V, remap=True, toc=True)
        cls.blocks = cls.out["blocks"]

    def test_equations_once_each_in_order_and_cited(self):
        numbers = [p[1] for k, p in self.blocks if k == "eq"]
        self.assertEqual(numbers, list(range(1, len(EQ.NUMBER) + 1)))
        self.assertEqual(len(EQ.NUMBER), 33)
        self.assertEqual(SJ.equation_problems(self.blocks), [])
        # the estimator map and the sensitivity grid print inside Part A with their own labels
        labels = {p["label"]: p["title"] for k, p in self.blocks if k == "table"}
        self.assertIn("Estimator map", labels[SJ.tab_label("M5_estimator_map")])
        self.assertIn("sensitivity", labels[SJ.tab_label("M6_sensitivity_grid")].lower())

    def test_tables_and_figures_in_order_with_their_introductions(self):
        tables = [p["label"] for k, p in self.blocks if k == "table"]
        figures = [p["label"] for k, p in self.blocks if k == "figure"]
        self.assertEqual(tables, [f"Table S{i}" for i in range(1, 92)])
        self.assertEqual(figures, [f"Figure S{i}" for i in range(1, 37)])
        part_a = next(i for i, (k, p) in enumerate(self.blocks) if k == "h1" and p == SJ.PART_A_H1)
        part_b = next(i for i, (k, p) in enumerate(self.blocks) if k == "h1" and p == SJ.PART_B_H1)
        self.assertLess(part_a, part_b)
        for i, (kind, payload) in enumerate(self.blocks):
            if kind == "figure" or (kind == "table" and i > part_b):
                prev = self.blocks[i - 1]
                self.assertEqual(prev[0], "p", payload["label"])
                self.assertTrue(str(prev[1]).startswith(payload["label"] + " "), payload["label"])
            if kind == "table" and i < part_b:
                self.assertIn(payload["label"], [SJ.tab_label(k) for k in SJ.PART_A_TABLES])
        self.assertEqual(self.blocks[-1][0], "refs")
        self.assertEqual(self.blocks[-1][1]["title"], SJ.APPENDIX_REFS_H1)
        self.assertEqual([k for k, _ in self.blocks[:3]], ["title", "subtitle", "authors"])

    def test_no_corpus_numbering_survives_in_captions_and_notes(self):
        for kind, payload in self.blocks:
            if kind not in ("figure", "table"):
                continue
            texts = [payload.get("caption", "")] if kind == "figure" else [payload.get("title", ""), payload.get("note", "")]
            for text in texts:
                for k, n in SJ._supp_citations(text):
                    limit = len(SJ.SUPP_FIGURES) if k == "Figure" else len(SJ.SUPP_TABLES)
                    self.assertTrue(1 <= n <= limit, f"{payload['label']}: {k} S{n}")
                for m in re.finditer(r"\b(Figure|Table) (\d+)\b", text):
                    limit = len(SJ.BODY_FIGURES) if m.group(1) == "Figure" else len(SJ.BODY_TABLES)
                    self.assertTrue(1 <= int(m.group(2)) <= limit, f"{payload['label']}: {m.group(0)}")
            self.assertTrue(payload.get("refs_remapped"), payload["label"])

    def test_assets_exist(self):
        for kind, payload in self.blocks:
            if kind == "figure":
                self.assertTrue(Path(payload["path"]).is_file(), payload["label"])
            elif kind == "table":
                self.assertGreater(len(payload["df"]), 0, payload["label"])

    def test_toc_covers_every_item(self):
        ids = {e["id"] for e in self.out["toc"]}
        for i in range(1, 92):
            self.assertIn(f"Table S{i}", ids)
        for i in range(1, 37):
            self.assertIn(f"Figure S{i}", ids)
        for sid in ("Part A", "M1", "M4", "M7", "A8", "A9", "Part B", "B1", "B11", SJ.APPENDIX_REFS_H1):
            self.assertIn(sid, ids)
        self.assertEqual(ids, {e["id"] for e in SJ.toc_entries(self.blocks)} | {"Part A", "Part B"} - set())

    def test_front_matter_states_the_variant(self):
        about = next(p for k, p in self.blocks if k == "p")
        self.assertIn("excluding Rett syndrome (F84.2)", about)
        self.assertIn(SJ.fig_label("figE28_variant_sensitivity"), about)
        self.assertIn(SJ.tab_label("E28_variant_sensitivity"), about)

    def test_forbidden_phrases_absent_from_assembled_prose(self):
        corpus = {str(p) for k, p in PME.methods_blocks("sin_rett", self.V, "en") if k in ("p", "h1", "h2", "h3")}
        own = []
        for kind, payload in self.blocks:
            if kind in ("p", "small", "h1", "h2", "h3") and str(payload) not in corpus:
                own.append(str(payload))
            elif kind == "bullets":
                own += [str(x) for x in payload]
        joined = "\n".join(own).lower()
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase.lower(), joined, phrase)

    def test_cross_references_with_the_journal_article(self):
        try:
            import prose_journal_en as PJ
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"prose_journal_en not importable yet: {exc}")
        if not hasattr(PJ, "article"):
            self.skipTest("prose_journal_en.article not available yet")
        art = PJ.article(self.V)
        problems = SJ.cross_reference_problems(art)
        self.assertEqual(problems, [], "\n".join(problems))
        cited = SJ.cited_items(art)
        self.assertEqual(cited["figure_numbers"], list(range(1, 37)))
        self.assertEqual(cited["table_numbers"], list(range(1, 92)))


if __name__ == "__main__":
    unittest.main()
