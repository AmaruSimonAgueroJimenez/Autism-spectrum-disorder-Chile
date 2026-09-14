# -*- coding: utf-8 -*-
"""La nota de la tabla BREVE de controles no puede contradecirse a sí misma en el mismo párrafo.

Defecto IC-3 de la fase 4e. La tabla de controles se imprime en dos tamaños —la larga, una fila por control
indicador-año, y la breve, una fila por familia de control O por fila rotulada— y las dos comparten una sola
nota. La cabecera de la nota abría diciendo «una fila por familia de control» / «one row per control family»
y la cláusula del final contaba, sobre la MISMA tabla de 48 filas, 42 familias, 2 filas de comprobación y 4
controles del módulo: seis filas no son familias y la nota se desmentía dos oraciones más abajo.

La ronda 1 arregló la cláusula del final al IMPRIMIR (`prose_*.table_note`) y dejó intacta la cabecera
guardada, de modo que el defecto sobrevivió en los ocho documentos que imprimen la tabla breve. Esta prueba
vigila las TRES puntas a la vez:

  1. la nota GUARDADA en titles.json (la que escribe `pipeline/07_controls.py` y la que lee cualquier
     consumidor externo del archivo publicado),
  2. la nota IMPRESA (`prose_en.table_note`, la misma para los dos idiomas),
  3. y que las cifras de las dos se cuenten sobre la tabla breve, no sobre la larga.
"""
from pathlib import Path
import json
import sys
import unittest

LA = Path(__file__).resolve().parents[1]
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import config as CFG  # noqa: E402
import prose_en as PEN  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")
KEY = "T8_controls_compact"


def _paths(variant: str, lang: str) -> tuple[Path, Path]:
    tdir = CFG.OUT / variant / lang / "tables"
    return tdir / "titles.json", tdir / f"{KEY}.csv"


HAS_OUTPUTS = all(p.is_file() for v in VARIANTS for l in LANGS for p in _paths(v, l))


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/<variante>/<idioma>/tables/T8_controls_compact.*")
class CompactControlsNoteTest(unittest.TestCase):

    def _cases(self):
        for variant in VARIANTS:
            for lang in LANGS:
                titles_path, csv_path = _paths(variant, lang)
                with open(titles_path, encoding="utf-8") as fh:
                    entry = json.load(fh)[KEY]
                df = pd.read_csv(csv_path, dtype=str).fillna("")
                yield variant, lang, entry["note"], df

    def test_lead_makes_no_absolute_one_per_family_claim(self):
        """Con filas que no son familias de control, la cabecera no puede afirmar que todas lo son."""
        for variant, lang, note, df in self._cases():
            with self.subTest(variant=variant, lang=lang):
                counts = C.controls_compact_counts(df)
                self.assertGreater(counts["check"] + counts["module"], 0,
                                   "la tabla ya no lleva filas rotuladas: revisar esta guarda")
                lead = note.split(". ")[0]
                for forbidden in C.CONTROLS_LEAD_FORBIDDEN[lang]:
                    self.assertNotIn(forbidden.lower(), lead.lower(),
                                     f"la cabecera afirma «{forbidden}» y {counts['check'] + counts['module']} "
                                     f"de las {counts['rows']} filas no son familias de control")

    def test_stored_clause_counts_the_compact_table(self):
        """La cláusula guardada cuenta las filas de la tabla BREVE, no las de la larga."""
        for variant, lang, note, df in self._cases():
            with self.subTest(variant=variant, lang=lang):
                m = C.CONTROLS_ROWS_CLAUSE_RE[lang].search(note)
                self.assertIsNotNone(m, "la nota guardada ya no lleva la cláusula de filas")
                written = int("".join(ch for ch in m.group(1) if ch.isdigit()))
                self.assertEqual(written, len(df))
                self.assertEqual(note[m.start():m.end()], C.controls_compact_clause(df, lang))

    def test_printed_note_equals_the_stored_note(self):
        """Las tres puntas dicen lo mismo: al imprimir no queda nada que corregir."""
        for variant, lang, note, df in self._cases():
            with self.subTest(variant=variant, lang=lang):
                printed = PEN.table_note(KEY, note, df, lang)
                self.assertEqual(printed, note)
                for forbidden in C.CONTROLS_LEAD_FORBIDDEN[lang]:
                    self.assertNotIn(forbidden.lower(), printed.split(". ")[0].lower())

    def test_both_languages_print_the_same_numbers(self):
        """Regla del estudio: los dos idiomas imprimen las MISMAS cifras, sólo cambia el separador."""
        import re
        bare = lambda s: [m.group(0).replace(".", "").replace(",", "")
                          for m in re.finditer(r"\d[\d.,]*", s)]
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                notes = {}
                for lang in LANGS:
                    titles_path, _ = _paths(variant, lang)
                    with open(titles_path, encoding="utf-8") as fh:
                        notes[lang] = json.load(fh)[KEY]["note"]
                self.assertEqual(bare(notes["en"]), bare(notes["es"]))

    def test_rewrite_still_works_on_a_stale_note(self):
        """La red de `table_note` sigue puesta: una nota vieja se corrige al imprimir."""
        for variant, lang, note, df in self._cases():
            with self.subTest(variant=variant, lang=lang):
                m = C.CONTROLS_ROWS_CLAUSE_RE[lang].search(note)
                stale = note[:m.start()] + ("Filas: 205 (191 coinciden, 14 difieren, todas explicadas)."
                                            if lang == "es" else
                                            "Rows: 205 (191 match, 14 differ, all explained).") + note[m.end():]
                self.assertEqual(PEN.table_note(KEY, stale, df, lang), note)
                break


if __name__ == "__main__":
    unittest.main()
