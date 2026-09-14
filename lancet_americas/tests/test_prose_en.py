"""Pruebas de prose_en.py: ambos variantes construyen artículo, manuscrito (artículo + parte suplementaria) y
apéndice separado; límites de la revista sobre el ARTÍCULO y trazabilidad de la numeración compartida."""
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402

HAS_OUTPUTS = all((CFG.OUT / f"values_{v}.json").is_file() for v in ("con_rett", "sin_rett")) and \
    (CFG.OUT / "con_rett" / "en" / "figures" / "captions.json").is_file() and \
    (CFG.OUT / "con_rett" / "en" / "extra" / "figures" / "captions.json").is_file()


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante")
class ProseEnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prose_en as P
        cls.P = P
        cls.docs = {}
        for variant in ("con_rett", "sin_rett"):
            V = P.load_values(variant)
            cls.docs[variant] = P._assemble(variant, V)   # (article, manuscript, appendix, registry)

    def test_builds_docx_for_both_variants(self):
        """El manuscrito lleva el artículo (7 tablas, 5 láminas) más toda la parte suplementaria; el apéndice, solo esta."""
        from docx_builder import build_document
        n_sfig, n_stab = len(self.P.SUPP_FIGURES), len(self.P.SUPP_TABLES)
        with tempfile.TemporaryDirectory() as tmp:
            for variant, (art, main, supp, _) in self.docs.items():
                r0 = build_document(art, "en", Path(tmp) / f"a_{variant}.docx", bib_path=self.P.BIB)
                r1 = build_document(main, "en", Path(tmp) / f"m_{variant}.docx", bib_path=self.P.BIB)
                r2 = build_document(supp, "en", Path(tmp) / f"s_{variant}.docx", bib_path=self.P.BIB)
                self.assertEqual((r0["tables"], r0["figures"]), (7, 5), variant)
                self.assertEqual((r1["tables"], r1["figures"]), (7 + n_stab, 5 + n_sfig), variant)
                self.assertEqual((r2["tables"], r2["figures"]), (n_stab, n_sfig), variant)
                self.assertGreater((Path(tmp) / f"m_{variant}.docx").stat().st_size, 10_000)

    def test_journal_limits(self):
        """Los límites de la revista se aplican al artículo, no al archivo con la parte suplementaria."""
        for variant, (art, _, _, _) in self.docs.items():
            wc = self.P.word_counts(art)
            self.assertLessEqual(wc["summary"], 250, variant)
            self.assertTrue(3500 <= wc["core_body"] <= 5000, f"{variant}: {wc}")
            self.assertLessEqual(len(self.P.citation_keys(art)), 30, variant)
            self.assertEqual((wc["tables"], wc["figures"]), (7, 5), variant)

    def test_structure_and_language_rules(self):
        for variant, (art, main, supp, _) in self.docs.items():
            h1 = [p for k, p in art if k == "h1"]
            for h in ("Summary", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "Contributors",
                      "Declaration of interests", "Data sharing statement", "Funding"):
                self.assertIn(h, h1)
            self.assertEqual(art[-1][0], "refs")
            self.assertEqual(main[-1][0], "refs")
            self.assertEqual(supp[-1][0], "refs")
            self.assertIn(self.P.SUPP_PART_H1, [p for k, p in main if k == "h1"])
            paragraphs = [str(p) for k, p in art if k == "p"]
            text = " ".join(paragraphs).lower()
            for banned in ("hospitalisations for autism", "hospitalizations for autism", "care cascade",
                           "prevalence of autism increased", "caused by law 21.545", "attributable to law 21.545",
                           "effect of law 21.545 was", "real increase in autism"):
                self.assertNotIn(banned, text, f"{variant}: '{banned}'")
            # every number must have been resolved: no 'None'/'nan' rendered from V (the Funding lines legitimately say 'None')
            for p in paragraphs:
                if p.startswith("**Funding**") or p.strip() == "None.":
                    continue
                self.assertIsNone(re.search(r"\bNone\b|\bnan\b", p), f"{variant}: unresolved value in: {p[:80]}")

    def test_supplementary_numbering_is_sequential_and_unique(self):
        """La numeración suplementaria es la posición en SUPP_FIGURES/SUPP_TABLES y ningún número se repite."""
        for variant, (art, main, supp, R) in self.docs.items():
            smap = self.P.supplementary_map(variant, None)
            figs = [p["label"] for k, p in supp if k == "figure"]
            tabs = [p["label"] for k, p in supp if k == "table"]
            self.assertEqual(figs, [f"Figure S{i}" for i in range(1, len(self.P.SUPP_FIGURES) + 1)], variant)
            self.assertEqual(sorted(tabs, key=lambda s: int(s.split("S")[1])),
                             [f"Table S{i}" for i in range(1, len(self.P.SUPP_TABLES) + 1)], variant)
            self.assertEqual(len(set(tabs)), len(tabs), f"{variant}: repeated supplementary table number")
            self.assertEqual(set(smap["figures"].values()), set(figs))
            self.assertEqual(set(smap["tables"].values()), set(tabs))
            # T1_sources es la Tabla S1 y T_dataflow_counts la Tabla S2 del registro compartido
            self.assertEqual(smap["tables"]["T1_sources"], "Table S1", variant)
            self.assertEqual(smap["tables"]["T_dataflow_counts"], "Table S2", variant)
            # todo ítem suplementario citado en el artículo existe en el suplemento
            cited = set(re.findall(r"(?:Figure|Table) S\d+", " ".join(str(p) for k, p in art if k == "p")))
            self.assertTrue(cited <= set(figs) | set(tabs), f"{variant}: {cited - set(figs) - set(tabs)}")

    def test_variants_differ_only_where_expected(self):
        main_con = [p for k, p in self.docs["con_rett"][1] if k == "p"]
        main_sin = [p for k, p in self.docs["sin_rett"][1] if k == "p"]
        self.assertEqual(len(main_con), len(main_sin))
        self.assertIn("including Rett syndrome", " ".join(main_con))
        self.assertIn("F84.2 excluded", " ".join(main_sin))

    def test_citation_keys_exist_in_bib(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paper"))
        from references import parse_bib
        entries = parse_bib(self.P.BIB)
        for variant, (_, main, supp, _) in self.docs.items():
            for key in self.P.citation_keys(main, include_opt=True) + self.P.citation_keys(supp, include_opt=True):
                self.assertIn(key, entries, f"{variant}: {key}")


if __name__ == "__main__":
    unittest.main()
