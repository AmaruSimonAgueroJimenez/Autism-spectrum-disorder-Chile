# -*- coding: utf-8 -*-
"""Lo que una leyenda AFIRMA sobre el TAMAÑO de su tabla acompañante tiene que ser cierto.

Nada vigilaba esta clase de afirmación. La leyenda de la Figura S49 (E44) decía «la matriz completa de los
TRECE indicadores … está en la tabla acompañante» y esa tabla —E44_correlation_matrix_comuna— imprime una
matriz de CATORCE por catorce (14 columnas de indicador y 14 filas por escala, 28 filas sobre comuna y
región). El 13 era en realidad el recuento del panel (c) —los catorce indicadores menos los episodios GRD,
que son la referencia—, trasplantado a la matriz. El defecto viajaba en los ocho documentos que llevan la
parte suplementaria, en los dos idiomas, y ninguna prueba lo veía: `test_stored_title_numbers` vigila el
NÚMERO de lámina que cita un título, `test_self_counts` los totales de control y los recuentos del registro.

Aquí la cifra se DERIVA del ancho de la matriz acompañante y se compara con la que la leyenda escribe en
letra, en los dos idiomas y en las dos variantes. Si mañana entra o sale un indicador y el productor no
reescribe la leyenda, falla aquí y no en la lectura de la página impresa.
"""
from pathlib import Path
import json
import re
import sys
import unittest

LA = Path(__file__).resolve().parents[1]
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import config as CFG  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")

#: Cardinales en letra que puede escribir una leyenda del estudio, en los dos idiomas.
WORDS = {
    "es": {"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
           "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
           "quince": 15, "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
           "veinte": 20},
    "en": {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
           "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
           "twenty": 20},
}

#: La frase que promete la matriz completa, y el grupo que lleva la cifra.
CLAIM = {
    "es": re.compile(r"matriz completa\s+de\s+los\s+([A-Za-zÁÉÍÓÚáéíóú]+|\d+)\s+indicadores", re.I),
    "en": re.compile(r"complete\s+matrix\s+of\s+the\s+([A-Za-z]+|\d+)\s+indicators", re.I),
}
#: La frase que dice con cuántos indicadores se DIBUJA la matriz de la lámina.
DRAWN = {
    "es": re.compile(r"regiones,\s+con\s+([A-Za-zÁÉÍÓÚáéíóú]+|\d+)\s+indicadores", re.I),
    "en": re.compile(r"regions,\s+with\s+([A-Za-z]+|\d+)\s+indicators", re.I),
}

FIG_KEY = "E44_correlation_matrix"
TABLE = "E44_correlation_matrix_comuna.csv"
#: Columnas de encabezado de la tabla acompañante que NO son un indicador: la escala y el nombre de fila.
LEAD_COLUMNS = 2


def _spelled(token: str, lang: str) -> int:
    t = str(token).strip().lower()
    if t.isdigit():
        return int(t)
    if t not in WORDS[lang]:
        raise AssertionError(f"la leyenda escribe «{token}», que no es un cardinal reconocido en {lang}")
    return WORDS[lang][t]


def _cases():
    for variant in VARIANTS:
        for lang in LANGS:
            caps = CFG.OUT / variant / lang / "extra" / "figures" / "captions.json"
            table = CFG.OUT / variant / lang / "extra" / "tables" / TABLE
            if caps.is_file() and table.is_file():
                yield variant, lang, caps, table


HAS_OUTPUTS = any(True for _ in _cases())


@unittest.skipUnless(HAS_OUTPUTS, "requiere captions.json y E44_correlation_matrix_comuna.csv")
class CaptionCompanionSizeTest(unittest.TestCase):

    def test_e44_caption_states_the_real_width_of_its_companion_matrix(self):
        import pandas as pd
        for variant, lang, caps_path, table_path in _cases():
            with self.subTest(variant=variant, lang=lang):
                caption = json.loads(caps_path.read_text(encoding="utf-8"))[FIG_KEY]["caption"]
                df = pd.read_csv(table_path, dtype=str, keep_default_na=False)
                width = len(df.columns) - LEAD_COLUMNS
                scales = df[df.columns[0]].nunique()
                self.assertEqual(len(df), width * scales,
                                 f"{variant}/{lang}: la matriz acompañante no es cuadrada por escala")
                m = CLAIM[lang].search(caption)
                self.assertIsNotNone(m, f"{variant}/{lang}: la leyenda ya no promete la matriz completa")
                self.assertEqual(_spelled(m.group(1), lang), width,
                                 f"{variant}/{lang}: la leyenda dice «{m.group(1)}» indicadores y la tabla "
                                 f"acompañante imprime {width}")

    def test_e44_caption_states_how_many_indicators_the_plate_draws(self):
        """La otra cifra de la misma frase: los indicadores DIBUJADOS son los del panel, no los de la tabla."""
        import importlib.util
        root = LA / "pipeline"
        spec = importlib.util.spec_from_file_location("m15b_caption", root / "15b_spatial_correlation.py")
        sys.path.insert(0, str(root))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        drawn, full = len(m.MATRIX_INDICATORS), len(m.ALL_INDICATORS)
        self.assertLess(drawn, full, "la lámina dibuja un subconjunto de la matriz completa")
        for variant, lang, caps_path, _table in _cases():
            with self.subTest(variant=variant, lang=lang):
                caption = json.loads(caps_path.read_text(encoding="utf-8"))[FIG_KEY]["caption"]
                m2 = DRAWN[lang].search(caption)
                self.assertIsNotNone(m2, f"{variant}/{lang}: la leyenda ya no dice con cuántos se dibuja")
                self.assertEqual(_spelled(m2.group(1), lang), drawn,
                                 f"{variant}/{lang}: la leyenda dice «{m2.group(1)}» indicadores dibujados "
                                 f"y la lámina dibuja {drawn}")


if __name__ == "__main__":
    unittest.main()
