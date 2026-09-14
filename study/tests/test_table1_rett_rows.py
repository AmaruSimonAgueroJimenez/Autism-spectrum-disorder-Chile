# -*- coding: utf-8 -*-
"""Las dos filas de Rett de la Tabla 1 del artículo (T2_grd_core) cuentan cosas distintas y lo dicen.

La tabla imprimía una sola fila, «F84.2 síndrome de Rett, cualquier posición (n; diferencia entre variantes)»,
con 55 / 27 / 36 / 57 / 58 / 94. Esas son las cifras de la PRIMERA mitad del rótulo —episodios en que aparece
el código F84.2— pero no las de la segunda: la diferencia entre las dos variantes es 51 / 24 / 32 / 53 / 50 /
87, porque un episodio con F84.2 y además otro código F84 lo cuentan las dos variantes y no las separa. El
texto del artículo imprime 87 dos párrafos antes, de modo que la tabla contradecía al texto.

Ahora la tabla lleva las dos filas, cada una con su rótulo exacto, y estas pruebas fijan lo que las distingue:

  1. las dos filas existen en las cuatro tablas (dos variantes × dos idiomas) y sus rótulos no se confunden;
  2. la fila «diferencia entre variantes» ES la diferencia entre variantes, calculada de las propias tablas;
  3. esa diferencia cabe dentro de los episodios con F84.2 y nunca los supera;
  4. las dos filas imprimen los mismos números en las dos variantes y en los dos idiomas;
  5. la cifra que el texto del artículo llama «diferencia» es la de la fila «diferencia», no la del código.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

LA = Path(__file__).resolve().parents[1]
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import config as CFG  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("es", "en")
YEARS = [str(y) for y in CFG.YEARS_GRD]
RETT_ROW, DIFF_ROW = "t2_rett_n", "t2_rett_only_n"

HAS_OUTPUTS = all((CFG.OUT / v / lang / "tables" / "T2_grd_core_numeric.csv").is_file()
                  for v in VARIANTS for lang in LANGS)


def _numeric(variant: str, lang: str):
    import pandas as pd
    df = pd.read_csv(CFG.OUT / variant / lang / "tables" / "T2_grd_core_numeric.csv")
    return df.set_index("row_key")


def _label(variant: str, lang: str, row_key: str) -> str:
    """Rótulo impreso de una fila: la fila del CSV formateado en la misma posición que la del CSV numérico."""
    import pandas as pd
    num = pd.read_csv(CFG.OUT / variant / lang / "tables" / "T2_grd_core_numeric.csv")
    txt = pd.read_csv(CFG.OUT / variant / lang / "tables" / "T2_grd_core.csv", dtype=str, keep_default_na=False)
    return str(txt.iloc[int(num.index[num.row_key == row_key][0])][txt.columns[1]])


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/<variante>/<idioma>/tables/T2_grd_core*.csv")
class Table1RettRowsTest(unittest.TestCase):

    def test_both_rows_are_printed_with_labels_that_cannot_be_confused(self):
        for variant in VARIANTS:
            for lang in LANGS:
                num = _numeric(variant, lang)
                for key in (RETT_ROW, DIFF_ROW):
                    self.assertIn(key, num.index, f"{variant}/{lang}: falta la fila {key}")
                code_label = _label(variant, lang, RETT_ROW)
                diff_label = _label(variant, lang, DIFF_ROW)
                difference = "diferencia" if lang == "es" else "difference"
                self.assertNotIn(difference, code_label.lower(),
                                 f"{variant}/{lang}: la fila del código F84.2 vuelve a prometer la diferencia entre variantes")
                self.assertIn(difference, diff_label.lower(), f"{variant}/{lang}: {diff_label}")
                self.assertIn("F84.2", code_label)
                self.assertIn("F84.2", diff_label)

    def test_the_difference_row_is_the_difference_between_the_variants(self):
        """Se recalcula de las dos tablas: F84 en cualquier posición del F84 completo menos el del F84 sin Rett."""
        for lang in LANGS:
            con = _numeric("con_rett", lang)
            sin = _numeric("sin_rett", lang)
            for year in YEARS:
                expected = int(con.loc["t2_any_obs_n", year] - sin.loc["t2_any_obs_n", year])
                for variant, num in (("con_rett", con), ("sin_rett", sin)):
                    self.assertEqual(int(num.loc[DIFF_ROW, year]), expected,
                                     f"{variant}/{lang}/{year}: la fila «diferencia» no es con_rett − sin_rett")

    def test_the_difference_never_exceeds_the_episodes_that_carry_the_code(self):
        """Un episodio con F84.2 y además otro código F84 lo cuentan las dos variantes: entra en el código, no en la diferencia."""
        for variant in VARIANTS:
            for lang in LANGS:
                num = _numeric(variant, lang)
                for year in YEARS:
                    code, diff = int(num.loc[RETT_ROW, year]), int(num.loc[DIFF_ROW, year])
                    self.assertTrue(0 <= diff <= code, f"{variant}/{lang}/{year}: {diff} fuera de [0, {code}]")

    def test_the_two_rows_print_the_same_values_everywhere(self):
        base = {key: [int(_numeric("con_rett", "en").loc[key, y]) for y in YEARS] for key in (RETT_ROW, DIFF_ROW)}
        for variant in VARIANTS:
            for lang in LANGS:
                num = _numeric(variant, lang)
                for key, values in base.items():
                    self.assertEqual([int(num.loc[key, y]) for y in YEARS], values, f"{variant}/{lang}: {key}")

    def test_the_note_tells_the_two_rows_apart(self):
        for variant in VARIANTS:
            for lang in LANGS:
                with open(CFG.OUT / variant / lang / "tables" / "titles.json", encoding="utf-8") as fh:
                    note = json.load(fh)["T2_grd_core"]["note"]
                needle = "único código F84 es F84.2" if lang == "es" else "only F84 code is F84.2"
                self.assertIn(needle, note, f"{variant}/{lang}: la nota no define la fila «diferencia»")

    def test_the_article_text_quotes_the_difference_row_and_not_the_code_row(self):
        for variant in VARIANTS:
            with open(CFG.OUT / f"values_{variant}.json", encoding="utf-8") as fh:
                V = json.load(fh)
            num = _numeric(variant, "en")
            for year in YEARS:
                self.assertEqual(int(V[f"grd_f84_any_n_rett_only_difference_{year}"]), int(num.loc[DIFF_ROW, year]),
                                 f"{variant}/{year}: el texto y la fila «diferencia» no coinciden")
                self.assertEqual(int(V[f"grd_f842_any_n_{year}"]), int(num.loc[RETT_ROW, year]),
                                 f"{variant}/{year}: el texto y la fila del código F84.2 no coinciden")


if __name__ == "__main__":
    unittest.main()
