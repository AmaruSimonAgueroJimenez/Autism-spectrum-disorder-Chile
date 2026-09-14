# -*- coding: utf-8 -*-
"""Pruebas del REGISTRO COMPARTIDO de la parte suplementaria (`supplementary_material.py`).

`test_17_extended_material.py` comprueba el registro DESDE los documentos ya ensamblados (que cada cita
resuelva, que el manuscrito y el apéndice separado tengan la misma secuencia). Esta prueba lo comprueba
desde el otro lado, que es donde se rompe una fusión de manifiestos: contra los ARCHIVOS del disco y
contra los manifiestos `outputs/phase4c_manifest_*.json` que las tareas de diseño dejan escritos cuando
añaden, dividen o renombran una lámina.

Cubre:

  * los tamaños publicados del registro (54 láminas, 125 tablas, 10 metodológicas, 33 ecuaciones) y el
    orden temático de los grupos, que es el que fija la numeración impresa;
  * la biyección clave ↔ archivo en las CUATRO combinaciones de variante e idioma: toda lámina registrada
    tiene su PNG y todo PNG que no sea del artículo tiene su clave, salvo los archivos heredados que
    `LEGACY_UNREGISTERED_PLATES` nombra uno a uno;
  * que ninguna clave quede huérfana por una división: todo `new_keys` de todo manifiesto está registrado
    y todo `old_key` sustituido ha desaparecido del registro;
  * la norma de lámina de la fase 4c medida sobre el PNG (4251 × 5787 px = 180 × 245 mm a 600 dpi) y las
    letras de panel en minúscula en la leyenda, con las dos listas de pendientes del registro;
  * que cada lámina traiga su frase de presentación bilingüe, con su unidad y su denominador, y que esa
    frase respete las reglas del estudio (nunca «prevalencia», nunca «hospitalizaciones por autismo»).

Las dos listas de pendientes (`PLATES_PENDING_STANDARD`, `CAPTIONS_PENDING_LOWERCASE`) se comprueban por
INCLUSIÓN: quien reconstruya una de esas láminas puede quitarla de la lista, o dejarla, sin que nada falle;
lo que falla es una lámina NUEVA fuera de norma. Así la guarda se aprieta sola y nunca castiga el arreglo.
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
import supplementary_material as SM  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")

#: Tamaños publicados en la nota y en el índice de la parte suplementaria. Son un fusible: si una fusión de
#: manifiestos añade, divide o pierde un ítem, esta prueba falla y obliga a releer la nota, el índice y el
#: recuento de grupos antes de reconstruir los documentos.
PUBLISHED = dict(figures=54, tables=125, methods_tables=10, figure_groups=7, table_groups=9, equations=33)

#: Secuencia temática de los grupos de láminas, en el orden en que se imprimen y por tanto se numeran.
FIGURE_GROUP_SEQUENCE = [
    "Core supplementary figures of the article",
    "Hospital episodes in detail",
    "Aggregate REM administrative pathway in detail",
    "Denominators, surveys and education",
    "Sex ratio across sources",
    "Model diagnostics and case-definition sensitivity",
    "Spatial analysis and territorial correlation",
]

#: Marcador de panel en MAYÚSCULA al principio de la leyenda o de una frase: «(A)», «(A, B)», «(A–D)».
#: El ancla evita los falsos positivos de un paréntesis que no es un panel (los tramos FONASA «(A–D)»).
UPPERCASE_PANEL = re.compile(r"(?:^|(?<=\.\s))\(([A-F](?:\s*(?:,|–|-|y|and)\s*[A-F])*)\)")

HAS_OUTPUTS = all((CFG.OUT / v / lang / sub / "captions.json").is_file()
                  for v in VARIANTS for lang in LANGS for sub in ("figures", "extra/figures"))


def _plate_files(variant: str, lang: str) -> dict[str, list[Path]]:
    """Todos los PNG de lámina de una combinación, por clave (el nombre del archivo es la clave)."""
    found: dict[str, list[Path]] = {}
    base = CFG.OUT / variant / lang
    for sub in ("figures", "extra/figures"):
        for path in sorted((base / sub).glob("*.png")):
            found.setdefault(path.stem, []).append(path)
    return found


def _captions(variant: str, lang: str) -> dict:
    merged: dict = {}
    for sub in ("figures", "extra/figures"):
        path = CFG.OUT / variant / lang / sub / "captions.json"
        if path.is_file():
            merged.update(json.loads(path.read_text(encoding="utf-8")))
    return merged


def _manifests() -> list[tuple[str, dict]]:
    """(nombre del manifiesto, entrada) de cada lámina o tabla anunciada por una tarea de diseño.

    Los manifiestos vienen en dos formas: una lista de entradas, o un objeto con la lista en `plates`."""
    entries: list[tuple[str, dict]] = []
    for path in sorted(CFG.OUT.glob("phase4c_manifest_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("plates", [])
        for item in items:
            if isinstance(item, dict) and item.get("old_key"):
                entries.append((path.name, item))
    return entries


class RegistryShapeTest(unittest.TestCase):
    """El registro, sin tocar el disco: tamaños, orden temático y frases de presentación."""

    def test_published_sizes(self):
        counts = SM.counts()
        for key, expected in PUBLISHED.items():
            self.assertEqual(counts[key], expected,
                             f"el registro declara {counts[key]} en «{key}» y la nota suplementaria publica "
                             f"{expected}: al fusionar un manifiesto hay que releer W['note'], W['index'] y "
                             f"PUBLISHED antes de reconstruir los documentos")

    def test_thematic_sequence_of_the_groups_fixes_the_numbering(self):
        self.assertEqual([title["en"] for title, _ in SM.FIGURE_GROUPS], FIGURE_GROUP_SEQUENCE)
        self.assertEqual(SM.FIGURE_ORDER, [key for _, keys in SM.FIGURE_GROUPS for key in keys],
                         "FIGURE_ORDER debe ser la concatenación de los grupos, en su orden")
        # las tablas metodológicas se numeran tras las dos de fuentes porque se imprimen ahí
        self.assertEqual(SM.TABLE_ORDER[:len(SM.TABLE_GROUPS[0][1])], SM.TABLE_GROUPS[0][1])
        start = len(SM.TABLE_GROUPS[0][1])
        self.assertEqual(SM.TABLE_ORDER[start:start + len(SM.METHODS_TABLES)], SM.METHODS_TABLES)
        self.assertEqual(len(set(SM.FIGURE_ORDER)), len(SM.FIGURE_ORDER), "clave de lámina repetida")
        self.assertEqual(len(set(SM.TABLE_ORDER)), len(SM.TABLE_ORDER), "clave de tabla repetida")

    def test_every_plate_has_its_bilingual_sentence_with_unit_and_denominator(self):
        self.assertEqual(sorted(SM.FIGURE_INTRO), sorted(SM.FIGURE_ORDER),
                         "toda lámina registrada necesita su frase de presentación, y sólo ella")
        unit = {"en": ("the unit is", "unit is the", "unit varies", "keeps its own unit"),
                "es": ("la unidad es", "unidad varía", "conserva su unidad")}
        denominator = {"en": "denominator", "es": "denominador"}
        for key in SM.FIGURE_ORDER:
            entry = SM.FIGURE_INTRO[key]
            for lang in LANGS:
                text = entry[lang]
                self.assertIn("{L}", text, f"{key}/{lang}: la frase no deja sitio al rótulo del registro")
                low = text.lower()
                self.assertTrue(any(w in low for w in unit[lang]),
                                f"{key}/{lang}: la frase no dice cuál es la unidad de análisis")
                self.assertIn(denominator[lang], low,
                              f"{key}/{lang}: la frase no dice cuál es el denominador")
            label = SM.figure_intro(key, "Figure S99", "en")
            self.assertIn("Figure S99", label)
            self.assertNotIn("{L}", label)

    def test_the_sentences_respect_the_standing_rules(self):
        forbidden = {"en": ("prevalence", "incidence", "hospitalisations for autism",
                            "hospitalizations for autism"),
                     "es": ("prevalencia", "incidencia", "hospitalizaciones por autismo")}
        for key in SM.FIGURE_ORDER:
            for lang in LANGS:
                low = SM.FIGURE_INTRO[key][lang].lower()
                for word in forbidden[lang]:
                    self.assertNotIn(word, low, f"{key}/{lang}: la frase dice «{word}»")

    def test_the_prose_modules_take_the_sequence_from_the_registry(self):
        import prose_en as E
        self.assertEqual(E.SUPP_FIGURES, SM.FIGURE_ORDER)
        self.assertEqual(E.SUPP_TABLES, SM.TABLE_ORDER)
        self.assertEqual(set(E.MAIN_FIGURES) & set(SM.FIGURE_ORDER), set(),
                         "una lámina del artículo no puede estar además en la serie suplementaria")

    def test_the_pending_lists_only_name_registered_plates(self):
        for name, keys in (("PLATES_PENDING_STANDARD", SM.PLATES_PENDING_STANDARD),
                           ("CAPTIONS_PENDING_LOWERCASE", SM.CAPTIONS_PENDING_LOWERCASE)):
            self.assertEqual(sorted(set(keys)), sorted(keys), f"{name}: clave repetida")
            for key in keys:
                self.assertIn(key, SM.FIGURE_ORDER, f"{name}: «{key}» ya no está en el registro; quítala")


class ManifestMergeTest(unittest.TestCase):
    """Ninguna clave anunciada por una tarea de diseño queda huérfana."""

    def test_every_manifest_is_merged_into_the_registry(self):
        entries = _manifests()
        self.assertGreater(len(entries), 0, "no hay ningún manifiesto de la fase 4c que fusionar")
        known = set(SM.FIGURE_ORDER) | set(SM.TABLE_ORDER)
        import prose_en as E
        known |= set(E.MAIN_FIGURES) | set(E.MAIN_TABLES)
        for name, item in entries:
            old, new = item["old_key"], list(item.get("new_keys") or [])
            self.assertTrue(new, f"{name}: la entrada «{old}» no dice en qué claves quedó")
            for key in new:
                self.assertIn(key, known, f"{name}: «{key}» ({old}) no está registrado en ninguna serie")
            if old not in new:
                self.assertNotIn(old, known,
                                 f"{name}: «{old}» se sustituyó por {new} pero sigue en el registro")

    def test_a_split_never_leaves_a_hole_in_the_printed_order(self):
        """Las claves de una división se imprimen juntas y en el orden del manifiesto."""
        for name, item in _manifests():
            new = [k for k in (item.get("new_keys") or []) if k in SM.FIGURE_ORDER]
            if len(new) < 2:
                continue
            positions = [SM.FIGURE_ORDER.index(k) for k in new]
            self.assertEqual(positions, sorted(positions),
                             f"{name}: {item['old_key']} se dividió y sus láminas no siguen el orden anunciado")
            self.assertEqual(positions[-1] - positions[0], len(positions) - 1,
                             f"{name}: {item['old_key']} se dividió y sus láminas no quedaron consecutivas")


@unittest.skipUnless(HAS_OUTPUTS, "requiere las láminas por variante e idioma")
class PlateFilesTest(unittest.TestCase):
    """El registro contra el disco, en las cuatro combinaciones de variante e idioma."""

    def test_every_registered_plate_has_exactly_one_file(self):
        for variant in VARIANTS:
            for lang in LANGS:
                files = _plate_files(variant, lang)
                for key in SM.FIGURE_ORDER:
                    self.assertIn(key, files, f"{variant}/{lang}: lámina registrada sin archivo: {key}")
                    self.assertEqual(len(files[key]), 1,
                                     f"{variant}/{lang}: {key} aparece en {len(files[key])} carpetas")

    def test_no_plate_file_is_left_unregistered(self):
        import prose_en as E
        allowed = set(SM.FIGURE_ORDER) | set(E.MAIN_FIGURES) | set(SM.LEGACY_UNREGISTERED_PLATES)
        for variant in VARIANTS:
            for lang in LANGS:
                extra = sorted(set(_plate_files(variant, lang)) - allowed)
                self.assertEqual(extra, [],
                                 f"{variant}/{lang}: archivos de lámina sin clave en el registro: {extra}. "
                                 f"O se registran, o se borran, o se nombran en LEGACY_UNREGISTERED_PLATES")

    def test_every_registered_table_has_an_output_file(self):
        for variant in VARIANTS:
            for lang in LANGS:
                base = CFG.OUT / variant / lang
                for key in SM.TABLE_ORDER:
                    hits = list((base / "tables").glob(f"{key}.*")) + list((base / "extra/tables").glob(f"{key}.*"))
                    self.assertTrue(hits, f"{variant}/{lang}: tabla registrada sin archivo: {key}")

    def test_the_plates_obey_the_plate_standard(self):
        """4251 × 5787 px = 180 × 245 mm a 600 dpi, medido en el PNG y no en el parámetro del dibujo."""
        from PIL import Image
        import prose_en as E
        pending = set(SM.PLATES_PENDING_STANDARD)
        offenders: dict[str, set] = {}
        checked = 0
        for variant in VARIANTS:
            for lang in LANGS:
                files = _plate_files(variant, lang)
                for key in list(E.MAIN_FIGURES) + SM.FIGURE_ORDER:
                    if key in pending or key not in files:
                        continue
                    checked += 1
                    size = Image.open(files[key][0]).size
                    if size != SM.PLATE_PX:
                        offenders.setdefault(key, set()).add(size)
        self.assertGreater(checked, 100, "no se midió ninguna lámina")
        self.assertEqual(offenders, {},
                         f"láminas fuera de la norma de {SM.PLATE_W_MM:.0f} × {SM.PLATE_H_MM:.0f} mm a "
                         f"{SM.PLATE_DPI} dpi: {sorted(offenders)}")

    def test_the_captions_letter_their_panels_in_lowercase(self):
        """La revista pide letras en minúscula: la leyenda no puede abrir con «(A)» ni con «(A–C)»."""
        exempt = set(SM.PLATES_PENDING_STANDARD) | set(SM.CAPTIONS_PENDING_LOWERCASE)
        offenders: dict[str, set] = {}
        for variant in VARIANTS:
            for lang in LANGS:
                captions = _captions(variant, lang)
                for key in SM.FIGURE_ORDER:
                    if key in exempt:
                        continue
                    text = str((captions.get(key) or {}).get("caption", ""))
                    for match in UPPERCASE_PANEL.findall(text):
                        offenders.setdefault(key, set()).add(match)
        self.assertEqual(offenders, {},
                         f"leyendas que nombran sus paneles en mayúscula: "
                         f"{ {k: sorted(v) for k, v in offenders.items()} }")


if __name__ == "__main__":
    unittest.main()
