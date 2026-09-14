"""Dos reglas que una lectura independiente encontró rotas en el papel, y su guarda.

1. Un nombre compuesto con raya («Gauss–Newton», «Getis–Ord», «Benjamini–Hochberg») no puede partirse entre
   dos renglones. La raya es «break after» de Unicode: sin ayuda el corte cae detrás de ella y con un
   unificador sólo detrás se muda delante, que es peor, porque el renglón siguiente abre con la raya.
2. Una tabla cuyo numerador está todo por comuna de residencia declara su denominador COMPATIBLE; pegarle
   además la advertencia de lugar de atención hace que la nota se contradiga a sí misma.
"""
import json
import re
import sys
import unittest
from pathlib import Path

LA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LA))

import docx_builder as D  # noqa: E402

WJ = "\ufeff"
EN = "–"


class CompoundDashTest(unittest.TestCase):
    def test_a_compound_name_is_bound_on_both_sides(self):
        for name in ("Gauss–Newton", "Getis–Ord", "Benjamini–Hochberg", "Durbin–Watson", "Fay–Feuer"):
            with self.subTest(name=name):
                out = D.compound_indivisible(name)
                self.assertIn(WJ + EN + WJ, out, "la raya tiene que quedar atada por los dos lados")
                self.assertEqual(out.replace(WJ, ""), name, "no se puede cambiar ningún otro carácter")

    def test_a_numeric_range_is_left_free_to_break(self):
        for rng in ("2019–2024", "31–59", "0,21–0,00", "65–72"):
            with self.subTest(rng=rng):
                self.assertEqual(D.compound_indivisible(rng), rng)

    def test_the_percent_rule_still_applies_through_the_same_funnel(self):
        self.assertEqual(D.texto_indivisible("12,3 % del total"), "12,3 % del total")
        self.assertEqual(D.texto_indivisible("Gauss–Newton"), f"Gauss{WJ}{EN}{WJ}Newton")

    def test_no_source_file_writes_the_joiner_into_the_data(self):
        """La atadura la pone el impresor, no el dato: si vive en el `.bib` o en un rótulo, se duplica."""
        offenders = []
        for f in list(LA.glob("*.py")) + list((LA / "pipeline").glob("*.py")) + [LA / "references_lancet.bib"]:
            if f.name == "docx_builder.py" or f.parent.name == "tests":
                continue
            if WJ in f.read_text(errors="ignore"):
                offenders.append(f.name)
        self.assertEqual(offenders, [], f"unificador de palabra escrito en el dato: {offenders}")


class CareWarningTest(unittest.TestCase):
    """La advertencia de lugar de atención sólo donde el numerador se localiza por atención."""

    def _notes(self):
        for f in LA.glob("outputs/*/*/extra/tables/titles.json"):
            for key, meta in json.loads(f.read_text()).items():
                yield f.parts[-5], f.parts[-4], key, (meta.get("note") or "")

    def test_no_note_declares_a_compatible_denominator_and_then_warns_about_place_of_care(self):
        bad = []
        for variant, lang, key, note in self._notes():
            says_compatible = re.search(r"(?<!NO )(?<!NOT )COMPATIBLE (con el numerador|with the)", note)
            warns = "ADVERTENCIA de compatibilidad" in note or "Compatibility WARNING" in note
            if says_compatible and warns:
                bad.append(f"{variant}/{lang}:{key}")
        self.assertEqual(bad, [], f"notas que se contradicen: {bad}")

    def test_the_place_of_care_tables_keep_their_warning(self):
        seen = 0
        for variant, lang, key, note in self._notes():
            if key.startswith("E41_rem_comuna_place_of_care"):
                seen += 1
                self.assertTrue("ADVERTENCIA de compatibilidad" in note or "Compatibility WARNING" in note,
                                f"{variant}/{lang}: la tabla por lugar de atención perdió su advertencia")
        self.assertTrue(seen >= 1, "no se encontró la tabla por lugar de atención")


class BuiltDocumentCompoundTest(unittest.TestCase):
    """La prueba que faltaba: el compuesto no puede partirse en el PAPEL, no sólo en la cadena de entrada.

    La primera versión de la regla ató la prosa y las tablas y dejó fuera la lista de referencias, los
    encabezados y los títulos de panel, que escriben su run directamente; el corte de «Gauss–Newton»
    sobrevivió en los doce documentos hasta que se leyó el PDF."""

    COMPOUNDS = ("Gauss–Newton", "Getis–Ord", "Benjamini–Hochberg", "Durbin–Watson", "Fay–Feuer",
                 "Clopper–Pearson")

    def test_no_compound_name_is_broken_across_two_lines(self):
        import subprocess
        pdfs = sorted(p for d in ("04_submission_lancet_americas", "02_others")
                      for sub in ("", "documents")   # raíz de la versión y su carpeta documents/
                      for p in (LA / "manuscript" / d / sub).glob("*.pdf"))
        if not pdfs:
            self.skipTest("todavía no hay documentos construidos")
        bad = []
        for f in pdfs:
            txt = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True).stdout
            lines = txt.split("\n")
            for i in range(len(lines) - 1):
                a, b = lines[i].rstrip(), lines[i + 1].lstrip()
                for c in self.COMPOUNDS:
                    left, right = c.split("–")
                    if a.endswith(left + "–") or (a.endswith(left) and b.startswith("–" + right)):
                        bad.append(f"{f.name}: {a[-40:]!r} / {b[:40]!r}")
        self.assertEqual(bad, [], f"nombre compuesto partido en el papel: {bad[:6]}")


if __name__ == "__main__":
    unittest.main()
