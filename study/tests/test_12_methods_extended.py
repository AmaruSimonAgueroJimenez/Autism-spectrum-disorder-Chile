# -*- coding: utf-8 -*-
"""Pruebas del módulo 12 (ecuaciones y metodología extendida).

Verifican que la numeración de `equations.py` es correlativa, que cada estimador tiene ecuación y
párrafo, que `prose_methods_extended.methods_blocks` produce los mismos bloques en los dos idiomas y las dos
variantes, que `docx_builder.build_document` los acepta y que toda clave de citación existe en el .bib.
No escriben nada en las salidas del estudio: el DOCX de prueba va a un directorio temporal.
"""
from pathlib import Path
import sys
import tempfile
import unittest

import matplotlib
matplotlib.use("Agg")

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parent
for _p in (str(STUDY), str(REPO / "paper")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as CFG  # noqa: E402
import equations as EQ  # noqa: E402
import prose_methods_extended as PME  # noqa: E402
import docx_builder as DB  # noqa: E402
from references import parse_bib  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("es", "en")


class EquationsTest(unittest.TestCase):
    def test_numbering_is_sequential_and_unique(self):
        self.assertEqual(len(EQ.KEYS), len(set(EQ.KEYS)))
        self.assertEqual([EQ.NUMBER[k] for k in EQ.KEYS], list(range(1, len(EQ.KEYS) + 1)))

    def test_every_equation_has_a_label_in_both_languages(self):
        for key in EQ.KEYS:
            self.assertIn(key, EQ.LABEL, key)
            for lang in LANGS:
                self.assertTrue(EQ.LABEL[key][lang].strip(), f"{key}/{lang}")

    def test_no_orphan_equations_or_estimators(self):
        self.assertEqual(EQ.orphan_equations(), [])
        self.assertEqual(PME.estimators_without_equation(), [])

    def test_paths_match_the_line_count(self):
        for key, tex in EQ.EQUATIONS:
            parts = tex if isinstance(tex, list) else [tex]
            paths = EQ.paths_for(key)
            self.assertEqual(len(paths), len(parts), key)
            self.assertTrue(paths[0].name.startswith(f"eq_{EQ.NUMBER[key]:02d}_{key}"), paths[0].name)

    def test_render_only_missing_creates_every_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            rendered = EQ.render_all(dpi=100, eq_dir=Path(tmp))
            self.assertEqual(set(rendered), set(EQ.KEYS))
            for paths in rendered.values():
                for path in paths:
                    self.assertTrue(path.is_file(), path)


class BlocksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks = {(v, lang): PME.methods_blocks(v, None, lang) for v in VARIANTS for lang in LANGS}
        cls.bib = set(parse_bib(STUDY / "references.bib"))

    def test_every_equation_is_cited_exactly_once(self):
        for key, blocks in self.blocks.items():
            numbers = [payload[1] for kind, payload in blocks if kind == "eq"]
            self.assertEqual(sorted(numbers), list(range(1, len(EQ.KEYS) + 1)), key)

    def test_every_estimator_has_a_heading_and_a_paragraph(self):
        for (variant, lang), blocks in self.blocks.items():
            headings = [payload for kind, payload in blocks if kind == "h3"]
            self.assertEqual(len(headings), len(EQ.ESTIMATORS), (variant, lang))
            for estimator in EQ.ESTIMATORS:
                self.assertIn(estimator["key"], PME.EST_TEXT)
                self.assertTrue(PME.EST_TEXT[estimator["key"]][lang].strip())

    def test_each_heading_cites_the_equations_printed_under_it(self):
        # Un encabezado de estimador promete, entre paréntesis, los números de las ecuaciones que el lector
        # va a encontrar DEBAJO. La metodología imprime cada ecuación la primera vez que un estimador la
        # cita, de modo que un estimador que reutiliza una ecuación anterior (Gi* reutiliza el umbral de
        # Benjamini–Hochberg de los indicadores locales) NO debe citarla en su encabezado.
        for key, blocks in self.blocks.items():
            self.assertEqual(PME.heading_equation_problems(blocks), [], key)

    def test_heading_equation_check_catches_a_broken_reference(self):
        # Control positivo: la comprobación no es muda. Al encabezado de un estimador se le añade un número
        # que no se imprime debajo y la comprobación tiene que verlo.
        blocks = list(self.blocks[("con_rett", "en")])
        for i, (kind, payload) in enumerate(blocks):
            if kind == "h3" and str(payload).endswith(")"):
                blocks[i] = (kind, str(payload)[:-1] + ", 99)")
                break
        else:                                                       # pragma: no cover - no debería ocurrir
            self.fail("no hay ningún encabezado de estimador que citar")
        problems = PME.heading_equation_problems(blocks)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("99", problems[0])

    def test_shared_equation_is_printed_once_under_the_first_estimator(self):
        # El caso concreto que motivó la comprobación: la ecuación del umbral de Benjamini–Hochberg la
        # declaran dos estimadores (LISA y Gi*) y se imprime una sola vez, bajo el primero.
        shared = [e["key"] for e in EQ.ESTIMATORS if "bh" in e["eq"]]
        self.assertEqual(shared, ["lisa", "getis_ord"])
        for (variant, lang), blocks in self.blocks.items():
            heads = [str(payload) for kind, payload in blocks if kind == "h3"]
            gistar = [h for h in heads if "Gi*" in h]
            self.assertEqual(len(gistar), 1, (variant, lang))
            cited = PME._heading_equation_numbers(gistar[0])
            self.assertEqual(cited, [EQ.NUMBER["gistar"]], (variant, lang))
            self.assertNotIn(EQ.NUMBER["bh"], cited, (variant, lang))

    def test_structure_is_identical_across_languages_and_variants(self):
        reference = [kind for kind, _ in self.blocks[("con_rett", "es")]]
        for key, blocks in self.blocks.items():
            self.assertEqual([kind for kind, _ in blocks], reference, key)

    def test_citation_keys_exist_in_the_bibliography(self):
        for key, blocks in self.blocks.items():
            missing = [k for k in PME.citation_keys(blocks) if k not in self.bib]
            self.assertEqual(missing, [], key)

    def test_word_count_is_substantial(self):
        for key, blocks in self.blocks.items():
            self.assertGreater(PME.word_count(blocks), 3000, key)

    def test_build_document_accepts_the_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            for (variant, lang), blocks in self.blocks.items():
                out = Path(tmp) / f"{variant}_{lang}.docx"
                report = DB.build_document(list(blocks) + [("refs", None)], lang, out,
                                           bib_path=STUDY / "references.bib", supplementary_prefix=True)
                self.assertTrue(out.is_file())
                self.assertEqual(report["tables"], len(PME.TABLE_KEYS))
                self.assertGreater(report["references"], 0)


class TablesTest(unittest.TestCase):
    def test_ten_tables_with_notes_and_numeric_companions(self):
        for variant in VARIANTS:
            for lang in LANGS:
                specs = PME.table_specs(variant, lang)
                self.assertEqual(list(specs), PME.TABLE_KEYS, (variant, lang))
                for name, spec in specs.items():
                    self.assertGreater(len(spec["df"]), 0, name)
                    self.assertEqual(len(spec["numeric"]), len(spec["df"]), name)
                    marker = "Archivo fuente" if lang == "es" else "Source file"
                    self.assertIn(marker, spec["note"], name)
                    self.assertTrue(spec["title"].strip(), name)

    def test_case_definition_table_follows_the_variant(self):
        for lang in LANGS:
            con = PME.table_specs("con_rett", lang)["M2_case_definitions"]["numeric"].set_index("code")
            sin = PME.table_specs("sin_rett", lang)["M2_case_definitions"]["numeric"].set_index("code")
            self.assertEqual(int(con.loc["F842", "in_variant"]), 1)
            self.assertEqual(int(sin.loc["F842", "in_variant"]), 0)
            self.assertEqual(int(con.loc["F840", "strict_f840"]), 1)

    def test_rem_code_table_matches_config(self):
        codes = [c for _, c, _, _ in PME.REM_CODE_SPEC]
        expected = (list(CFG.A03_LEGACY.values()) + list(CFG.A03_2023_2024.values())
                    + list(CFG.A03_2024_31_59.values()) + list(CFG.A03_2025.values())
                    + list(CFG.A05_ENTRY.values()) + list(CFG.A05_EXIT.values())
                    + list(CFG.A05_BROAD_PRE2021.values()) + list(CFG.A27.values()) + list(CFG.A28.values())
                    + [CFG.P2_TEA, CFG.P2_NANEAS_TOTAL] + list(CFG.P6_PRIMARY.values())
                    + list(CFG.P6_SPECIALTY.values()) + list(CFG.P6_BROAD_PRE2021.values()))
        self.assertEqual(sorted(codes), sorted(expected))
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
