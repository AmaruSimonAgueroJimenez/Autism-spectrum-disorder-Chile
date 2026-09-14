# -*- coding: utf-8 -*-
"""El CUERPO de un título guardado no puede citar una lámina del artículo con un número obsoleto.

Los módulos productores guardan el título de cada tabla en `outputs/<variante>/<idioma>/tables/titles.json`.
El constructor del documento borra el PREFIJO provisional («Tabla F3 (datos).», «Tabla S9.») y lo sustituye
por el rótulo del registro, pero NO toca el cuerpo: dos títulos citaban ahí una lámina del artículo por su
número anterior a la renumeración —F3_rem_pathway_data decía «Figura 3» cuando corresponde a la Figura 4, y
F4_triangulation_series decía «Figura 4» cuando corresponde a la Figura 5—.

Los módulos 08b y 08c resuelven ahora ese número con `prose_en.main_figure_label`, de modo que el título
guardado sigue al registro. Esta prueba vigila el archivo escrito: si alguien vuelve a escribir el número a
mano, o si el artículo se renumera y los módulos productores no se han vuelto a ejecutar, falla aquí y no en
la lectura del documento impreso.
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
import prose_en as PEN  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")

#: Título guardado -> lámina del artículo que su cuerpo nombra. `T_dataflow_counts` (módulo 08d) nombra la
#: lámina del flujo de datos, que hoy es la Figura 1: se vigila igual, aunque su número sea el correcto.
TITLE_CITES_MAIN_FIGURE = {
    "F3_rem_pathway_data": "fig3_rem_pathway",
    "F4_triangulation_series": "fig4_triangulation",
    "T_dataflow_counts": "fig1_dataflow",
}

_FIG_IN_BODY = re.compile(r"\b(?:Figure|Figura)\s+(\d+)\b")
#: prefijo provisional del propio título («Tabla F3 (datos).», «Table S9.»), que el constructor borra
_PREFIX = re.compile(r"^\s*(?:Table|Tabla)\s+[A-Z]*\d+[a-z]*(?:\s*\([^)]*\))?\.\s*")


#: Los títulos viven en dos carpetas: `tables/` (módulos 08–09) y `extra/tables/` (módulos 11–16).
TITLE_FILES = (("tables",), ("extra", "tables"))


def _titles(variant: str, lang: str) -> dict:
    merged: dict = {}
    for parts in TITLE_FILES:
        path = CFG.OUT.joinpath(variant, lang, *parts, "titles.json")
        if path.is_file():
            with open(path, encoding="utf-8") as fh:
                merged.update(json.load(fh))
    return merged


HAS_OUTPUTS = all(CFG.OUT.joinpath(v, l, *parts, "titles.json").is_file()
                  for v in VARIANTS for l in LANGS for parts in TITLE_FILES)


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/<variante>/<idioma>/tables/titles.json")
class StoredTitleFigureNumberTest(unittest.TestCase):

    def test_helper_resolves_through_the_registry(self):
        for key in TITLE_CITES_MAIN_FIGURE.values():
            self.assertIn(key, PEN.MAIN_FIGURES, key)
        self.assertEqual(PEN.main_figure_label("fig3_rem_pathway", "en"),
                         f"Figure {PEN.MAIN_FIGURES.index('fig3_rem_pathway') + 1}")
        self.assertEqual(PEN.main_figure_label("fig4_triangulation", "es"),
                         f"Figura {PEN.MAIN_FIGURES.index('fig4_triangulation') + 1}")
        with self.assertRaises(KeyError):
            PEN.main_figure_label("no_existe", "en")
        with self.assertRaises(ValueError):
            PEN.main_figure_label("fig2_grd_core", "pt")

    def test_stored_titles_cite_the_current_figure_number(self):
        checked = 0
        for variant in VARIANTS:
            for lang in LANGS:
                titles = _titles(variant, lang)
                for key, fig_key in TITLE_CITES_MAIN_FIGURE.items():
                    with self.subTest(variant=variant, lang=lang, table=key):
                        self.assertIn(key, titles, f"{variant}/{lang}: falta el título de {key}")
                        body = _PREFIX.sub("", str(titles[key]["title"]))
                        found = _FIG_IN_BODY.findall(body)
                        self.assertEqual(len(found), 1, f"{variant}/{lang} {key}: {body[:120]}")
                        expected = str(PEN.MAIN_FIGURES.index(fig_key) + 1)
                        self.assertEqual(found[0], expected,
                                         f"{variant}/{lang} {key}: el título dice «Figura {found[0]}» pero "
                                         f"{fig_key} es la lámina {expected} del artículo; vuelva a ejecutar el "
                                         f"módulo productor (08b / 08c)")
                        checked += 1
        self.assertEqual(checked, len(TITLE_CITES_MAIN_FIGURE) * len(VARIANTS) * len(LANGS))

    def test_no_other_stored_title_cites_a_main_figure_by_number(self):
        """Cualquier otro título cuyo cuerpo nombre una lámina del artículo tiene que declararse arriba."""
        strays = []
        for variant in VARIANTS:
            for lang in LANGS:
                for key, entry in _titles(variant, lang).items():
                    if key in TITLE_CITES_MAIN_FIGURE:
                        continue
                    body = _PREFIX.sub("", str(entry.get("title", "")))
                    if _FIG_IN_BODY.search(body):
                        strays.append((variant, lang, key, body[:110]))
        self.assertEqual(strays, [], f"títulos que citan una lámina del artículo sin resolverla: {strays[:6]}")


if __name__ == "__main__":
    unittest.main()
