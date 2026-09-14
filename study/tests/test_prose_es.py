"""Pruebas de prose_es.py: ambas variantes construyen manuscrito y suplemento en español, reglas de lenguaje,
numeración suplementaria y fidelidad al texto en inglés (mismas cifras de V, mismas citas, mismos párrafos [OPT])."""
from collections import Counter
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402

HAS_OUTPUTS = all((CFG.OUT / f"values_{v}.json").is_file() for v in ("con_rett", "sin_rett")) and \
    (CFG.OUT / "con_rett" / "es" / "figures" / "captions.json").is_file() and \
    (CFG.OUT / "con_rett" / "es" / "extra" / "figures" / "captions.json").is_file()


def _numbers(blocks):
    """Multiconjunto de cifras (≥ 2 dígitos o con separador decimal) de los párrafos, sin separadores de miles/decimal.
    Se ignoran los marcadores ordinales del español («1.º básico», «5.º básico», «1.º medio»)."""
    out = []
    for kind, p in blocks:
        if kind != "p":
            continue
        t = re.sub(r"\[@[^\]]+\]", "", str(p))
        t = re.sub(r"\d+\.º", "", t)
        for m in re.findall(r"\d[\d.,]*", t):
            m = m.rstrip(".,")  # puntuación final («grade 1,», «Tabla 1.») no forma parte de la cifra
            d = re.sub(r"[^\d]", "", m)
            if len(d) >= 2 or ("." in m or "," in m):
                out.append(d)
    return Counter(out)


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante e idioma")
class ProseEsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prose_en as E
        import prose_es as S
        cls.E, cls.S = E, S
        cls.docs = {}
        cls.docs_en = {}
        for variant in ("con_rett", "sin_rett"):
            V = S.load_values(variant)
            cls.docs[variant] = S._assemble(variant, V)      # (artículo, manuscrito, apéndice, registro)
            cls.docs_en[variant] = E._assemble(variant, V)

    def test_builds_docx_for_both_variants(self):
        from docx_builder import build_document
        n_sfig, n_stab = len(self.S.SUPP_FIGURES), len(self.S.SUPP_TABLES)
        with tempfile.TemporaryDirectory() as tmp:
            for variant, (art, main, supp, _) in self.docs.items():
                r0 = build_document(art, "es", Path(tmp) / f"a_{variant}.docx", bib_path=self.S.BIB)
                r1 = build_document(main, "es", Path(tmp) / f"m_{variant}.docx", bib_path=self.S.BIB)
                r2 = build_document(supp, "es", Path(tmp) / f"s_{variant}.docx", bib_path=self.S.BIB)
                self.assertEqual((r0["tables"], r0["figures"]), (7, 5), variant)
                self.assertEqual((r1["tables"], r1["figures"]), (7 + n_stab, 5 + n_sfig), variant)
                self.assertEqual((r2["tables"], r2["figures"]), (n_stab, n_sfig), variant)
                self.assertTrue((Path(tmp) / f"m_{variant}.docx").stat().st_size > 10_000)

    def test_word_counts_and_citations(self):
        """El español se expande frente al inglés; se exige que cada recuento quede entre 0,9 y 1,3 veces el inglés y
        que el texto núcleo cite como máximo 30 claves (mismo límite que la revista impone al inglés)."""
        for variant, (art, _, _, _) in self.docs.items():
            wc, wc_en = self.S.word_counts(art), self.E.word_counts(self.docs_en[variant][0])
            for key in ("summary", "panel", "core_body", "opt_body", "declarations"):
                ratio = wc[key] / wc_en[key]
                self.assertTrue(0.9 <= ratio <= 1.3, f"{variant}: {key} es={wc[key]} en={wc_en[key]} ratio={ratio:.2f}")
            self.assertEqual(wc["opt_paragraphs"], wc_en["opt_paragraphs"])
            self.assertLessEqual(len(self.S.citation_keys(art)), 30, variant)

    def test_structure_and_language_rules(self):
        for variant, (art, main, supp, _) in self.docs.items():
            h1 = [p for k, p in art if k == "h1"]
            for h in ("Resumen", "Introducción", "Métodos", "Resultados", "Discusión", "Conclusión", "Contribuciones",
                      "Declaración de intereses", "Declaración de disponibilidad de datos", "Financiamiento"):
                self.assertIn(h, h1)
            self.assertEqual(art[-1][0], "refs")
            self.assertEqual(main[-1][0], "refs")
            self.assertEqual(supp[-1][0], "refs")
            self.assertIn(self.S.SUPP_PART_H1, [p for k, p in main if k == "h1"])
            panel = [p for k, p in art if k == "panel"]
            self.assertEqual(len(panel), 1)
            self.assertEqual(panel[0]["title"], "Investigación en contexto")
            self.assertFalse(any("[@" in t for _, t in panel[0]["items"]), "el panel no lleva referencias")
            summary = [p for k, p in art[:art.index(("panel", panel[0]))] if k == "p"]
            self.assertEqual([p.split("**")[1] for p in summary],
                             ["Antecedentes", "Métodos", "Resultados", "Interpretación", "Financiamiento"])
            paragraphs = [str(p) for k, p in art if k == "p"]
            text = " ".join(paragraphs).lower()
            for banned in ("hospitalizaciones por autismo", "hospitalización por autismo", "cascada de atención",
                           "cascada asistencial", "trayectoria individual", "aumento real del autismo",
                           "prevalencia del autismo aumentó", "causado por la ley 21.545", "causada por la ley 21.545",
                           "atribuible a la ley 21.545", "efecto de la ley 21.545 fue", "care cascade",
                           "hospitalisations for autism"):
                self.assertNotIn(banned, text, f"{variant}: '{banned}'")
            # toda cifra debe haberse resuelto: nunca 'None'/'nan' desde V
            for p in paragraphs:
                self.assertIsNone(re.search(r"\bNone\b|\bnan\b", p), f"{variant}: valor sin resolver en: {p[:80]}")
            # formato español: coma decimal en al menos una cifra del resumen y espacio duro antes de «%»
            self.assertRegex(" ".join(summary), r"\d,\d")
            self.assertNotRegex(" ".join(paragraphs), r"\d\.\d%")
            self.assertIn("IC 95 %", " ".join(paragraphs))

    def test_supplementary_numbering_is_sequential_and_identical_to_english(self):
        for variant, (art, main, supp, _) in self.docs.items():
            smap = self.S.supplementary_map(variant, None)
            figs = [p["label"] for k, p in supp if k == "figure"]
            tabs = [p["label"] for k, p in supp if k == "table"]
            self.assertEqual(figs, [f"Figura S{i}" for i in range(1, len(self.S.SUPP_FIGURES) + 1)])
            self.assertEqual(sorted(tabs, key=lambda s: int(s.split("S")[1])),
                             [f"Tabla S{i}" for i in range(1, len(self.S.SUPP_TABLES) + 1)])
            self.assertEqual(len(set(tabs)), len(tabs), f"{variant}: número de tabla repetido")
            self.assertEqual(set(smap["figures"].values()), set(figs))
            self.assertEqual(set(smap["tables"].values()), set(tabs))
            self.assertEqual(smap["tables"]["T1_sources"], "Tabla S1", variant)
            self.assertEqual(smap["tables"]["T_dataflow_counts"], "Tabla S2", variant)
            cited = set(re.findall(r"(?:Figura|Tabla) S\d+", " ".join(str(p) for k, p in art if k == "p")))
            self.assertTrue(cited <= set(figs) | set(tabs))
            smap_en = self.E.supplementary_map(variant, None)
            self.assertEqual(list(smap["figures"]), list(smap_en["figures"]))
            self.assertEqual(list(smap["tables"]), list(smap_en["tables"]))
            # rótulos del artículo (insertados tras el párrafo de primera mención) y títulos sin prefijo provisional
            self.assertEqual(sorted(p["label"] for k, p in art if k == "figure"), [f"Figura {i}" for i in range(1, 6)])
            self.assertEqual(sorted((p["label"] for k, p in art if k == "table"), key=lambda s: int(s.split()[1])),
                             [f"Tabla {i}" for i in range(1, 8)])
            self.assertEqual([p["label"] for k, p in art if k == "table"],
                             [p["label"].replace("Table", "Tabla") for k, p in self.docs_en[variant][0] if k == "table"])
            # ningún prefijo de numeración provisional sobrevive («Tabla ST7.», «Lámina EF1.», «Figura E20.»);
            # un título que empieza por «Tabla acompañante de…» sí es legítimo, porque no lleva número
            for k, p in main + supp:
                if k == "table":
                    self.assertNotRegex(p["title"], r"^(Tabla|Table|Cuadro)\s+[A-Za-z]{0,3}\d", p["label"])
                elif k == "figure":
                    self.assertNotRegex(p["caption"], r"^(Figura|Figure|Lámina|Plate)\s+[A-Za-z]{0,3}\d", p["label"])
                    self.assertTrue(Path(p["path"]).is_file() and "/es/" in str(p["path"]), p["label"])

    def test_faithful_to_english(self):
        """Mismos párrafos, mismas posiciones [OPT], mismas claves de cita en el mismo orden y mismas cifras de V."""
        for variant, (_art, main, supp, _R) in self.docs.items():
            _art_en, main_en, supp_en, _R_en = self.docs_en[variant]
            pe = [str(p) for k, p in main_en if k == "p"]
            ps = [str(p) for k, p in main if k == "p"]
            self.assertEqual(len(pe), len(ps), variant)
            self.assertEqual([p.startswith(self.E.OPT) for p in pe], [p.startswith(self.S.OPT) for p in ps], variant)
            self.assertEqual(self.E.citation_keys(main_en, True), self.S.citation_keys(main, True), variant)
            self.assertEqual(self.E.citation_keys(main_en), self.S.citation_keys(main), variant)
            self.assertEqual(self.E.citation_keys(supp_en, True), self.S.citation_keys(supp, True), variant)
            self.assertEqual(_numbers(main_en), _numbers(main), f"{variant}: cifras distintas entre inglés y español")
            self.assertEqual(_numbers(supp_en), _numbers(supp), f"{variant}: cifras del suplemento distintas")

    def test_variants_differ_only_where_expected(self):
        main_con = [p for k, p in self.docs["con_rett"][1] if k == "p"]
        main_sin = [p for k, p in self.docs["sin_rett"][1] if k == "p"]
        self.assertEqual(len(main_con), len(main_sin))
        self.assertIn("incluido el síndrome de Rett", " ".join(main_con))
        self.assertIn("F84.2 excluido", " ".join(main_sin))

    def test_citation_keys_exist_in_bib(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paper"))
        from references import parse_bib
        entries = parse_bib(self.S.BIB)
        for variant, (_art, main, supp, _R) in self.docs.items():
            for key in self.S.citation_keys(main, include_opt=True) + self.S.citation_keys(supp, include_opt=True):
                self.assertIn(key, entries, f"{variant}: {key}")


if __name__ == "__main__":
    unittest.main()
