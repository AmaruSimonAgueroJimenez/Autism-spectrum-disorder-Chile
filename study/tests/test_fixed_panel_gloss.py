# -*- coding: utf-8 -*-
"""UNA SOLA DEFINICIÓN DEL PANEL FIJO DE 65 HOSPITALES (fase 4k, tarea K1).

La compilación del 2026-09-08 definía el MISMO panel de dos maneras, y las dos convivían a una página de
distancia: apéndice inglés p. 361 (Tabla S62) «fixed panel of 65 = hospitals present in 2019–2022» contra
p. 362 (Tabla S64) «fixed panel of 65 (present in every year 2019–2024)»; y otra vez dentro del artículo,
p. 18 (nota de la Tabla 1) contra p. 49 (tabla de controles). Medido sobre las tablas impresas y los
títulos de los cuatro árboles variante-idioma: 138 enunciados con la ventana 2019–2022 contra 56 con la
ventana 2019–2024.

EL HECHO ESTÁ ESTABLECIDO y esta prueba lo vuelve a comprobar sobre el dato, no sobre el texto: los dos
enunciados designan EXACTAMENTE los mismos 65 hospitales. Lo que se decidió no es el fondo sino la
redacción, porque «presentes en 2019–2022» deja al lector preguntándose si esos hospitales reportaron
también en 2023 y en 2024.

Esta prueba fija la glosa y su puerta:

  1. LA GLOSA, forma por forma, sobre `common.fixed_panel_gloss` — escrita UNA vez y en un solo sitio.
  2. EL HECHO, releído de `outputs/tidy/grd_hospital_year.csv`: 65/65/65/65/68/72 hospitales por año, la
     intersección de los seis años y la de 2019–2022 tienen 65 miembros y son el MISMO conjunto.
  3. EL DETECTOR con su control positivo: las cadenas que el corpus imprimía antes deben leerse como
     2019–2022, o «cero infractores» significaría «el instrumento no mira».
  4. LA PUERTA DE REGRESIÓN: ninguna tabla impresa ni ningún título o leyenda de los cuatro árboles dice
     quiénes forman el panel fijo con una ventana que no sea 2019–2024, y TODOS lo dicen con la misma:
     dos glosas no pueden volver a convivir.
  5. NINGÚN MÓDULO VUELVE A ESCRIBIR SU PROPIA COPIA: los que imprimen la glosa la piden a `common`.

ALCANCE Y EXENCIONES, declaradas aquí y en ningún otro sitio:

  * `01_grd_core.py` es el módulo que CALCULA el panel. Su nota de control («panel fijo = hospitales
    presentes en 2019–2022») es texto de máquina: viaja por `outputs/controls/01_grd_core_controls.csv`
    hasta los hermanos `_numeric` —en español incluso en el árbol inglés, que es la prueba de que nadie
    la lee como prosa del corpus— y NO llega a ninguno de los doce documentos. Ahí, además, «2019–2022»
    describe la REGLA DE CONSTRUCCIÓN, que es exacta.
  * `10_manuscript.py` es el informe de decisiones: CITA las dos glosas para contar por qué se eligió
    una. Un informe que no pudiera nombrar el defecto no serviría de informe.
"""
from pathlib import Path
import ast
import json
import sys
import unittest

import pandas as pd

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import common as C  # noqa: E402
import config as CFG  # noqa: E402

#: La ventana que el estudio usa para decir QUIÉNES forman el panel fijo. Cualquier otra es el defecto.
CANONICAL_WINDOW = "2019–2024"

#: Los módulos que imprimen la glosa y que, por tanto, tienen que pedírsela a `common`.
PRINTING_MODULES = ("06_models.py", "07_controls.py", "09a_tables_main.py", "09b_tables_supplementary.py",
                    "11_grd_episode_detail.py", "13_extra_figures_hospital.py", "16_extra_tables.py")

#: Las dos exenciones del barrido de fuentes, con su razón en el docstring del módulo.
SOURCE_EXEMPT = ("01_grd_core.py", "10_manuscript.py")


# ---------------------------------------------------------------------------
# 1. La glosa, forma por forma
# ---------------------------------------------------------------------------
class GlossTest(unittest.TestCase):
    """La redacción adoptada. Cambiarla en silencio hace fallar esta prueba."""

    def test_the_membership_gloss_is_the_adopted_wording(self):
        self.assertEqual(C.fixed_panel_gloss("en", "membership"),
                         "hospitals reporting in every year 2019–2024")
        self.assertEqual(C.fixed_panel_gloss("es", "membership"),
                         "hospitales que reportan en todos los años 2019–2024")

    def test_every_form_says_the_same_thing(self):
        for lang in ("es", "en"):
            clause = C.fixed_panel_gloss(lang, "clause")
            for form in ("clause", "membership", "paren", "named", "definition", "full"):
                self.assertIn(clause, C.fixed_panel_gloss(lang, form), f"{lang}/{form}")
                self.assertIn(CANONICAL_WINDOW, C.fixed_panel_gloss(lang, form), f"{lang}/{form}")

    def test_the_shapes_the_corpus_needs(self):
        self.assertEqual(C.fixed_panel_gloss("es", "paren"), "(que reportan en todos los años 2019–2024)")
        self.assertEqual(C.fixed_panel_gloss("en", "paren"), "(reporting in every year 2019–2024)")
        self.assertEqual(C.fixed_panel_gloss("es", "definition"),
                         "panel fijo de 65 = hospitales que reportan en todos los años 2019–2024")
        self.assertEqual(C.fixed_panel_gloss("en", "definition"),
                         "fixed panel of 65 = hospitals reporting in every year 2019–2024")
        self.assertEqual(C.fixed_panel_gloss("en", "named", n=65),
                         "fixed panel of 65 hospitals reporting in every year 2019–2024")

    def test_the_construction_rule_is_a_different_sentence_and_keeps_its_years(self):
        # «2019–2022» es exacto cuando describe CÓMO se obtuvo el conjunto, no QUIÉNES lo forman: la
        # forma `construction` nombra los cuatro años uno a uno y la ventana 2019–2022 no aparece.
        for lang in ("es", "en"):
            build = C.fixed_panel_gloss(lang, "construction")
            self.assertIn("2019", build)
            self.assertIn("2022", build)
            self.assertNotIn("2019–2022", build)
            self.assertTrue(C.fixed_panel_gloss(lang, "full").startswith(
                C.fixed_panel_gloss(lang, "membership")))
            self.assertTrue(C.fixed_panel_gloss(lang, "full").endswith(build))

    def test_an_unknown_form_or_language_is_an_error_not_a_silent_string(self):
        with self.assertRaises(KeyError):
            C.fixed_panel_gloss("es", "inventada")
        with self.assertRaises(KeyError):
            C.fixed_panel_gloss("fr", "membership")


# ---------------------------------------------------------------------------
# 2. El hecho, releído del dato
# ---------------------------------------------------------------------------
class TheFactTest(unittest.TestCase):
    """Los dos enunciados designan el MISMO conjunto: si un día dejaran de hacerlo, la glosa mentiría."""

    def setUp(self):
        p = CFG.OUT / "tidy" / "grd_hospital_year.csv"
        if not p.is_file():
            self.skipTest("no hay outputs/tidy/grd_hospital_year.csv")
        self.d = pd.read_csv(p)

    def test_the_two_sets_are_the_same_65_hospitals(self):
        for variant, g in self.d.groupby("variant"):
            years = {int(y): set(gg.COD_HOSPITAL) for y, gg in g.groupby("year")}
            self.assertEqual([len(years[y]) for y in sorted(years)], [65, 65, 65, 65, 68, 72], variant)
            every_year = set.intersection(*(years[y] for y in sorted(years)))
            first_four = set.intersection(*(years[y] for y in (2019, 2020, 2021, 2022)))
            self.assertEqual(len(every_year), 65, variant)
            self.assertEqual(len(first_four), 65, variant)
            self.assertEqual(every_year, first_four,
                             f"{variant}: los dos enunciados dejarían de designar el mismo conjunto")

    def test_the_stored_membership_flag_agrees_with_both(self):
        for variant, g in self.d.groupby("variant"):
            flagged = set(g[g.in_fixed_panel.astype(str) == "True"].COD_HOSPITAL)
            years = {int(y): set(gg.COD_HOSPITAL) for y, gg in g.groupby("year")}
            self.assertEqual(flagged, set.intersection(*(years[y] for y in sorted(years))), variant)


# ---------------------------------------------------------------------------
# 3. El detector, con su control positivo
# ---------------------------------------------------------------------------
class DetectorTest(unittest.TestCase):
    """Las cadenas que el corpus imprimía antes de la fase 4k, una por módulo que las escribía."""

    OLD = [
        # 11_grd_episode_detail.py — nota común de E1–E12
        "Observed panel: 65, 65, 65, 65, 68 and 72 hospitals in 2019–2024; fixed panel of 65 = "
        "hospitals present in 2019–2022. 2020–2021: pandemic reporting disruption",
        "panel fijo de 65 = hospitales presentes en 2019–2022. 2020–2021: disrupción del reporte",
        # 16_extra_tables.py — nota común de E60–E68 y nota propia de E61
        "observed panel of 65, 65, 65, 65, 68 and 72 hospitals in 2019–2024 and fixed panel of 65 "
        "(present in 2019–2022). Persons are counted only within each year",
        "El panel observado crece de 65 a 72 hospitales; la columna de panel fijo identifica los 65 "
        "presentes en 2019–2022. El hospital es el LUGAR DE ATENCIÓN",
        # 09b_tables_supplementary.py — nota de la Tabla ST1
        "Fixed panel = 65 hospitals present in 2019, 2020, 2021 and 2022 (a subset of 2023 and 2024); "
        "observed panel = 65/65/65/65/68/72 hospitals",
        # 07_controls.py — tabla de controles (la del artículo, p. 49)
        "Distinct hospitals (COD_HOSPITAL) with at least one episode in the year; the fixed panel is "
        "the 65 present in 2019–2022, never the 72 of 2024",
        "el panel fijo son los 65 presentes en 2019–2022, nunca los 72 de 2024",
        # 06_models.py — nota de la Tabla S3
        "72 hospitals observed in 2024 (65 in the 2019–2022 fixed panel and 7 added in 2023–2024)",
        "72 hospitales observados en 2024 (65 del panel fijo 2019–2022 y 7 incorporados en 2023–2024)",
    ]

    NOT_A_GLOSS = [
        "A03 detección, era legado 2019–2022 (subgrupo con alteración de lenguaje/área social)",
        "2019–2022: el cuestionario no incluye categoría TEA (no estimable)",
        # El panel OBSERVADO enumera cuántos hospitales reporta cada año: es exacto tal cual.
        "Hospitales públicos que reportan al GRD: 65 (2019–2022), 68 (2023) y 72 (2024)",
        "Episodes of public hospitals reporting to the FONASA GRD dataset; observed panel of 65 "
        "hospitals in 2019-2022, 68 in 2023 and 72 in 2024",
    ]

    def test_positive_control_the_old_gloss_is_seen(self):
        for s in self.OLD:
            self.assertEqual(C.fixed_panel_membership_windows(s), ["2019–2022"], s[:70])

    def test_the_new_gloss_is_seen_and_reads_2019_2024(self):
        for lang in ("es", "en"):
            for form in ("paren", "named", "definition", "full"):
                text = ("panel fijo " if lang == "es" else "fixed panel ") + C.fixed_panel_gloss(lang, form)
                self.assertIn(CANONICAL_WINDOW, C.fixed_panel_membership_windows(text), f"{lang}/{form}")

    def test_what_is_not_a_membership_gloss_is_left_alone(self):
        for s in self.NOT_A_GLOSS:
            self.assertEqual(C.fixed_panel_membership_windows(s), [], s[:70])


# ---------------------------------------------------------------------------
# 4. La puerta de regresión sobre el corpus ya escrito
# ---------------------------------------------------------------------------
def printed_tables():
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            base = CFG.OUT / variant / lang
            for tdir in (base / "tables", base / "extra" / "tables"):
                if tdir.is_dir():
                    for p in sorted(tdir.glob("*.csv")):
                        if C.is_printed_table(p):
                            yield p


def printed_labels():
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            base = CFG.OUT / variant / lang
            for sub in ("tables", "figures", "extra/tables", "extra/figures"):
                for nom in ("titles.json", "captions.json"):
                    p = base / sub / nom
                    if p.is_file():
                        yield p


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


class CorpusHasOneDefinitionTest(unittest.TestCase):
    """Puerta: una segunda glosa del panel fijo escrita mañana hace fallar esta prueba."""

    @classmethod
    def setUpClass(cls):
        cls.found = []          # (archivo, ventana, fragmento)
        for p in printed_tables():
            for w in C.fixed_panel_membership_windows(p.read_text(encoding="utf-8", errors="replace")):
                cls.found.append((p, w))
        for p in printed_labels():
            for s in _strings(json.loads(p.read_text(encoding="utf-8"))):
                for w in C.fixed_panel_membership_windows(s):
                    cls.found.append((p, w))

    def _label(self, p):
        return f"{p.parent.parent.name}/{p.parent.name}/{p.name}"

    def test_the_instrument_is_not_mute(self):
        if not list(printed_tables()):
            self.skipTest("no hay tablas construidas en outputs/")
        self.assertGreater(len(self.found), 100,
                           "el corpus construido debería decir quiénes forman el panel fijo muchas veces")

    def test_no_printed_text_defines_the_panel_with_another_window(self):
        if not self.found:
            self.skipTest("no hay tablas construidas en outputs/")
        offenders = {}
        for p, w in self.found:
            if w != CANONICAL_WINDOW:
                offenders.setdefault(self._label(p), set()).add(w)
        self.assertEqual({k: sorted(v) for k, v in offenders.items()}, {},
                         f"{len(offenders)} archivo(s) definen el panel fijo con otra ventana")

    def test_two_glosses_cannot_coexist(self):
        if not self.found:
            self.skipTest("no hay tablas construidas en outputs/")
        windows = sorted({w for _, w in self.found})
        self.assertEqual(windows, [CANONICAL_WINDOW],
                         f"el corpus define el panel fijo de {len(windows)} maneras: {windows}")


# ---------------------------------------------------------------------------
# 5. Ningún módulo vuelve a escribir su propia copia de la glosa
# ---------------------------------------------------------------------------
def literal_windows(path: Path):
    """Las ventanas de pertenencia escritas COMO LITERAL en un módulo, con su línea."""
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for w in C.fixed_panel_membership_windows(node.value):
                out.append((node.lineno, w))
    return out


class OnlyOneCopyOfTheGlossTest(unittest.TestCase):

    def test_no_module_writes_the_rejected_definition_as_a_literal(self):
        offenders = {}
        for p in sorted((PKG / "pipeline").glob("*.py")):
            if p.name in SOURCE_EXEMPT:
                continue
            bad = [(ln, w) for ln, w in literal_windows(p) if w != CANONICAL_WINDOW]
            if bad:
                offenders[p.name] = bad
        self.assertEqual(offenders, {},
                         "la glosa del panel fijo vive en common.fixed_panel_gloss; estos módulos "
                         f"vuelven a escribirla con otra ventana: {offenders}")

    def test_the_exemptions_are_real_and_still_needed(self):
        # Si un día dejaran de contener la glosa vieja, la exención sobra y hay que borrarla de aquí.
        for name in SOURCE_EXEMPT:
            p = PKG / "pipeline" / name
            self.assertTrue(p.is_file(), name)
            self.assertTrue(any(w != CANONICAL_WINDOW for _, w in literal_windows(p)),
                            f"{name} ya no escribe la glosa vieja: sobra su exención")

    def test_every_printing_module_asks_common_for_it(self):
        missing = [n for n in PRINTING_MODULES
                   if "fixed_panel_gloss(" not in (PKG / "pipeline" / n).read_text(encoding="utf-8")]
        self.assertEqual(missing, [],
                         f"estos módulos imprimen la glosa sin pedirla a common: {missing}")

    def test_common_is_the_one_place_that_declares_it(self):
        src = (PKG / "common.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("def fixed_panel_gloss("), 1)
        self.assertEqual(src.count("def fixed_panel_membership_windows("), 1)
        self.assertEqual(src.count('"que reportan en todos los años 2019–2024"'), 1)
        self.assertEqual(src.count('"reporting in every year 2019–2024"'), 1)

    def test_no_other_file_of_the_package_copies_the_canonical_clause(self):
        here = Path(__file__).resolve()
        offenders = []
        for p in sorted(PKG.rglob("*.py")):
            if p == here or p.resolve() == (PKG / "common.py").resolve():
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            if C.fixed_panel_gloss("es", "clause") in src or C.fixed_panel_gloss("en", "clause") in src:
                offenders.append(str(p.relative_to(PKG)))
        self.assertEqual(offenders, [],
                         f"la glosa está copiada fuera de common.py: {offenders}")


if __name__ == "__main__":
    unittest.main()
