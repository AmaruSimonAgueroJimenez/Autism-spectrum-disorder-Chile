# -*- coding: utf-8 -*-
"""Citas de panel: minúsculas y resueltas contra la leyenda de la propia lámina.

Todas las láminas del estudio letran sus paneles en MINÚSCULA —en el dibujo y en la leyenda, que abre cada
panel con «(a)», «(b)», …— pero el texto los citaba en MAYÚSCULA: «Figure 3C», «Figure 5A», «Figure 5C»,
«Figure 5D–E», «Figure 5F» y sus gemelas españolas. La letra se escribía como un literal pegado al rótulo que
devuelve el registro, así que nada impedía que la cita nombrara un panel que la lámina no dibuja, ni que las
dos convenciones se separaran todavía más.

Ahora la letra la construyen `R.mfigp(clave, paneles)` y `R.figp(clave, paneles)`, que la resuelven con
`prose_en.panel_suffix` contra la leyenda de ESA lámina y EN ESE idioma. Estas pruebas fijan las tres cosas
que eso garantiza:

  1. `panel_suffix` acepta solo minúsculas, solo paneles que la leyenda rotula y solo rangos ascendentes;
  2. ninguno de los cuatro documentos (dos variantes × dos idiomas) imprime una cita de panel en mayúscula;
  3. toda letra citada existe como panel «(x)» en la leyenda de la lámina citada, en el mismo idioma, de modo
     que la cita y la lámina no pueden divergir.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

LA = Path(__file__).resolve().parents[1]
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import config as CFG  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")

HAS_OUTPUTS = (all((CFG.OUT / f"values_{v}.json").is_file() for v in VARIANTS)
               and all((CFG.OUT / v / lang / sub / "captions.json").is_file()
                       for v in VARIANTS for lang in ("en", "es") for sub in ("figures", "extra/figures")))

#: Una cita de panel: el rótulo de la lámina seguido de una o dos letras. La clase de caracteres incluye las
#: MAYÚSCULAS a propósito: la prueba tiene que poder ver la cita mal escrita para poder denunciarla.
CITATION_RE = re.compile(r"\b(?:Figure|Figura)\s+(S?\d+)([A-Za-z](?:\s*[–-]\s*[A-Za-z])?)(?![A-Za-z0-9])")


def _texts(blocks) -> str:
    out = []
    for kind, payload in blocks:
        if kind in ("p", "h1", "h2", "h3"):
            out.append(str(payload))
        elif kind == "bullets":
            out += [str(t) for t in payload]
        elif kind == "panel":
            out += [f"{t} {b}" for t, b in payload["items"]]
        elif kind == "figure":
            out.append(str(payload.get("caption", "")))
        elif kind == "table":
            out += [str(payload.get("title", "")), str(payload.get("note", ""))]
    return "\n".join(out)


class PanelSuffixTest(unittest.TestCase):
    """La función que resuelve la letra, sin tocar los documentos."""

    CAPTION = "(a) uno. (b) dos. (c) tres. (d) cuatro. (e) cinco. (f) seis."

    def setUp(self):
        import prose_en as E
        self.E = E

    def test_accepts_a_letter_and_an_ascending_range(self):
        self.assertEqual(self.E.panel_suffix(self.CAPTION, "c"), "c")
        self.assertEqual(self.E.panel_suffix(self.CAPTION, "d-e"), "d–e")
        self.assertEqual(self.E.panel_suffix(self.CAPTION, "d–e"), "d–e")

    def test_rejects_uppercase_unknown_panels_and_inverted_ranges(self):
        for bad in ("C", "D-E", "g", "e-d", "a-a", "ab", "", "1", "a,b"):
            with self.assertRaises(ValueError, msg=bad):
                self.E.panel_suffix(self.CAPTION, bad)

    def test_rejects_a_panel_the_caption_does_not_label(self):
        with self.assertRaises(ValueError):
            self.E.panel_suffix("(a) uno. (b) dos.", "c")

    def test_rejects_every_panel_of_a_plate_that_has_none(self):
        """La Figura 1 es un diagrama de lienzo único: no tiene paneles y ninguna letra puede citarse."""
        for letter in self.E.PANEL_LETTERS:
            with self.assertRaises(ValueError):
                self.E.panel_suffix("", letter, "fig1_dataflow")


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las leyendas por variante e idioma")
class BuiltDocumentPanelCitationTest(unittest.TestCase):
    """El barrido real sobre los cuatro documentos armados."""

    @classmethod
    def setUpClass(cls):
        import prose_en as E
        import prose_es as S
        cls.mods = {"en": E, "es": S}
        cls.docs = {}
        for lang, P in cls.mods.items():
            for variant in VARIANTS:
                V = P.load_values(variant)
                art, main, supp, R = P._assemble(variant, V)
                cls.docs[(lang, variant)] = (art, main, supp, R)

    def _citations(self, blocks):
        for number, letters in CITATION_RE.findall(_texts(blocks)):
            yield number, letters.replace(" ", "")

    def test_no_panel_citation_is_uppercase(self):
        for (lang, variant), (art, main, supp, _R) in self.docs.items():
            for number, letters in self._citations(main + supp):
                self.assertEqual(letters, letters.lower(),
                                 f"{lang}/{variant}: cita de panel en mayúscula «Figura {number}{letters}»")

    def test_every_cited_panel_is_labelled_by_the_caption_of_that_plate(self):
        for (lang, variant), (art, main, supp, R) in self.docs.items():
            P = self.mods[lang]
            for number, letters in self._citations(main + supp):
                if number.startswith("S"):
                    keys = P.SUPP_FIGURES
                    index = int(number[1:]) - 1
                else:
                    keys = P.MAIN_FIGURES
                    index = int(number) - 1
                self.assertTrue(0 <= index < len(keys), f"{lang}/{variant}: Figura {number} no existe")
                key = keys[index]
                caption = R.captions[key].get("caption", "")
                for letter in [c for c in letters if c.isalpha()]:
                    self.assertIn(f"({letter})", caption,
                                  f"{lang}/{variant}: se cita el panel ({letter}) de {key}, que su leyenda no rotula")

    def test_both_languages_cite_the_same_panels(self):
        """Los dos documentos son el mismo artículo: citan las mismas láminas con las mismas letras."""
        for variant in VARIANTS:
            en = sorted(self._citations(self.docs[("en", variant)][1]))
            es = sorted(self._citations(self.docs[("es", variant)][1]))
            self.assertEqual(en, es, f"{variant}: las citas de panel difieren entre idiomas")

    def test_the_article_actually_cites_panels(self):
        """Guarda contra un falso silencio: si el texto dejara de citar paneles, estas pruebas pasarían vacías."""
        for (lang, variant), (art, _main, _supp, _R) in self.docs.items():
            cited = list(self._citations(art))
            self.assertGreaterEqual(len(cited), 5, f"{lang}/{variant}: {cited}")


if __name__ == "__main__":
    unittest.main()
