# -*- coding: utf-8 -*-
"""UNA SOLA REGLA DE RAYA PARA TODO EL CORPUS (fase 4j, tarea J2).

La compilación del 2026-09-08 imprimía el MISMO tipo de intervalo con dos trazos: «0-4» y «0–4» en la
misma página, en la misma lámina y hasta en la misma fila de la misma tabla (Tabla S110: «Documented
F84 · 0-4» junto a «2 (0–6)»). La causa era que la regla estaba escrita cinco veces y por tanto faltaba
en cuatro módulos de lámina y en TODA la ruta de tablas.

Esta prueba fija la regla y la puerta:

  1. LA REGLA, categoría por categoría, sobre `common.range_dash` — incluidas las que CONSERVAN el guion.
  2. LOS DOS SITIOS por los que se aplica: la tabla impresa (`atomic_write_csv`), el JSON de títulos y
     leyendas (`atomic_write_json`) y la lámina (`plate_range_dash`), y los sitios de MÁQUINA que NO deben
     tocarse (el hermano `_numeric`, `outputs/tidy/`, `outputs/controls/`, un runlog).
  3. LA PUERTA DE REGRESIÓN: ni una sola tabla impresa del corpus, ni un solo título o leyenda, escribe un
     intervalo de lectura con guion. Si mañana alguien añade una banda de edad con guion, esto falla.
  4. NINGÚN MÓDULO VUELVE A ESCRIBIR SU PROPIA COPIA de la regla (la sexta copia es la que la rompe).

Cada bloque lleva su CONTROL POSITIVO: una cadena, un marco o una figura con el defecto plantado, para
que un fallo del instrumento no se lea como un aprobado.
"""
from pathlib import Path
import csv
import json
import sys
import tempfile
import unittest

import pandas as pd

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import common as C  # noqa: E402
import config as CFG  # noqa: E402

EN_DASH = "–"


# ---------------------------------------------------------------------------
# 1. La regla, categoría por categoría
# ---------------------------------------------------------------------------
class RangeDashRuleTest(unittest.TestCase):
    #: (entrada, salida esperada) — INTERVALOS QUE UN LECTOR LEE: pasan a raya corta.
    CONVERT = [
        ("0-4", "0" + EN_DASH + "4"),
        ("6-7", "6" + EN_DASH + "7"),
        ("31-59 meses", "31" + EN_DASH + "59 meses"),
        ("2019-2024", "2019" + EN_DASH + "2024"),
        ("A03 31-59 meses 2024", "A03 31" + EN_DASH + "59 meses 2024"),
        ("1,5-2,5", "1,5" + EN_DASH + "2,5"),
        ("31-59-month", "31" + EN_DASH + "59-month"),
        ("2-5/6-11/12-17", "2" + EN_DASH + "5/6" + EN_DASH + "11/12" + EN_DASH + "17"),
        ("5-year bands as published (0-4 … 95-99)",
         "5-year bands as published (0" + EN_DASH + "4 … 95" + EN_DASH + "99)"),
        ("Documented F84 · 0-4", "Documented F84 · 0" + EN_DASH + "4"),
        # La PUNTUACIÓN DE LA FRASE que envuelve la palabra no decide la tipografía del número: los dos
        # puntos de una entradilla de leyenda («2020-2021: disrupción») no la convierten en clave de
        # máquina. Era el defecto que dejaba «2020-2021:» con guion a dos centímetros de «2020–2021».
        ("2020-2021: disrupción del reporte", "2020" + EN_DASH + "2021: disrupción del reporte"),
        ("(2019-2020)", "(2019" + EN_DASH + "2020)"),
        ("«0-4»", "«0" + EN_DASH + "4»"),
        ("2019-2020;", "2019" + EN_DASH + "2020;"),
        ("[0-4]", "[0" + EN_DASH + "4]"),
    ]
    #: CONSERVAN EL GUION, y por qué. Cada una es una categoría declarada de la regla.
    KEEP = [
        ("2026-09-04", "fecha ISO completa"),
        ("2014-07/2026", "año-mes: el guion es de la fecha, no del intervalo"),
        ("65-65-65-65-68-72", "cadena de seis números: enumeración, no intervalo"),
        ("F84-2019", "código con prefijo alfabético pegado"),
        ("grd_rate:con_rett:observed:all:any:none:2019-2024", "identificador de modelo"),
        ("EF6_readmission_le_episodes[con_rett|2019-2020]", "clave de familia de control"),
        ("ine_estimaciones-y-proyecciones-2002-2035_base-2017.csv", "nombre de archivo"),
        ("source_url=https://x/dataset/1992-2070_base.xlsx", "URL"),
        ("REM-20", "el guion no separa dos cifras"),
        ("M-CHAT-R/F", "identificador de instrumento"),
        ("COVID-19", "el guion no separa dos cifras"),
        ("IR-29301", "identificador"),
        ("REM-20:", "identificador con dos puntos de frase: sigue sin separar dos cifras"),
        ("F84-2019.", "código con punto final de frase"),
        ("GRD/metadata/SOURCES_MANIFEST.md", "ruta"),
    ]

    def test_reader_intervals_take_the_en_dash(self):
        for raw, want in self.CONVERT:
            with self.subTest(raw=raw):
                self.assertEqual(C.range_dash(raw), want)
                self.assertGreater(C.count_hyphen_ranges(raw), 0)
                self.assertEqual(C.count_hyphen_ranges(C.range_dash(raw)), 0)

    def test_machine_and_non_interval_keep_their_hyphen(self):
        for raw, why in self.KEEP:
            with self.subTest(raw=raw, why=why):
                self.assertEqual(C.range_dash(raw), raw)
                self.assertEqual(C.count_hyphen_ranges(raw), 0)

    def test_rule_is_idempotent(self):
        for raw, _ in self.CONVERT:
            once = C.range_dash(raw)
            self.assertEqual(C.range_dash(once), once)

    def test_negative_number_keeps_the_typographic_minus(self):
        # El menos lo pone `fmt_number`; la regla de la raya no lo toca y no lo confunde con un guion.
        self.assertEqual(C.fmt_number(-3, 0, "en"), C.MINUS_SIGN + "3")
        self.assertEqual(C.range_dash(C.fmt_number(-3, 0, "en")), C.MINUS_SIGN + "3")
        self.assertEqual(C.range_dash(C.MINUS_SIGN + "3-5"), C.MINUS_SIGN + "3" + EN_DASH + "5")

    def test_year_window_rule_is_a_special_case_of_the_interval_rule(self):
        self.assertEqual(C.range_dash("2019-2021"), C.yspan("2019-2021"))

    def test_positive_control_the_instrument_is_not_mute(self):
        # Si `count_hyphen_ranges` dejara de ver el defecto, este bloque fallaría y no al revés.
        self.assertEqual(C.count_hyphen_ranges("0-4 y 5-9"), 2)
        self.assertEqual(C.count_dash_ranges("0" + EN_DASH + "4"), 1)
        self.assertEqual(C.count_kept_hyphens("2026-09-04"), 2)


# ---------------------------------------------------------------------------
# 2. Los dos sitios donde se aplica, y los de máquina donde no
# ---------------------------------------------------------------------------
class RangeDashApplicationTest(unittest.TestCase):
    VARIANT = tuple(CFG.VARIANTS)[0]
    LANG = tuple(CFG.LANGUAGES)[0]

    def frame(self):
        return pd.DataFrame({"Grupo etario": ["0-4", "5-9"], "2019-2024": ["2 (0-6)", "3 (1-7)"],
                             "Clave": ["grd_rate:x:2019-2024", "EF6_x[con_rett|2019-2020]"]})

    def test_printed_table_is_converted_and_the_numeric_sibling_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / self.VARIANT / self.LANG / "tables"
            printed = C.atomic_write_csv(self.frame(), base / "T9_ages.csv")
            numeric = C.atomic_write_csv(self.frame(), base / "T9_ages_numeric.csv")
            tidy = C.atomic_write_csv(self.frame(), Path(d) / "tidy" / "T9_ages.csv")
            controls = C.atomic_write_csv(self.frame(), Path(d) / "controls" / "T9_controls.csv")
            self.assertEqual(self.hyphens(printed), 0)
            self.assertGreater(self.dashes(printed), 0)
            for machine in (numeric, tidy, controls):
                with self.subTest(path=machine.name):
                    self.assertGreater(self.hyphens(machine), 0)  # control positivo: el defecto está ahí
                    self.assertEqual(self.dashes(machine), 0)

    def test_extra_tables_directory_is_a_printed_table_too(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / self.VARIANT / self.LANG / "extra" / "tables"
            printed = C.atomic_write_csv(self.frame(), base / "E70_ages.csv")
            self.assertEqual(self.hyphens(printed), 0)

    def test_machine_keys_survive_inside_a_printed_table(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / self.VARIANT / self.LANG / "tables"
            p = C.atomic_write_csv(self.frame(), base / "T9_ages.csv")
            text = p.read_text(encoding="utf-8")
            self.assertIn("grd_rate:x:2019-2024", text)
            self.assertIn("EF6_x[con_rett|2019-2020]", text)

    def test_verbatim_columns_are_left_alone(self):
        df = pd.DataFrame({"Etiquetas de valor (textual)": ["edad5 1 15-19, 2 20-29"],
                           "Grupo etario": ["15-19"]})
        out, conv, kept = C.range_dash_frame(df)
        self.assertEqual(out.iloc[0, 0], "edad5 1 15-19, 2 20-29")
        self.assertEqual(out.iloc[0, 1], "15" + EN_DASH + "19")
        self.assertEqual(conv, 1)
        self.assertGreaterEqual(kept, 2)

    def test_a_frame_can_declare_its_own_exempt_columns(self):
        df = pd.DataFrame({"Transcripción": ["0-4"], "Banda": ["0-4"]})
        df.attrs[C.RANGE_DASH_EXEMPT] = ("Transcripción",)
        out, conv, _ = C.range_dash_frame(df)
        self.assertEqual(out.iloc[0, 0], "0-4")
        self.assertEqual(out.iloc[0, 1], "0" + EN_DASH + "4")
        self.assertEqual(conv, 1)

    def test_titles_and_captions_json_are_printed_text_and_a_runlog_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / self.VARIANT / self.LANG / "tables"
            obj = {"T9_ages": {"title": "Table S9. Ages 0-4 to 75-79", "note": "Key: grd_rate:x:2019-2024"}}
            p = C.atomic_write_json(obj, base / "titles.json")
            back = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(back["T9_ages"]["title"], "Table S9. Ages 0" + EN_DASH + "4 to 75" + EN_DASH + "79")
            self.assertEqual(back["T9_ages"]["note"], "Key: grd_rate:x:2019-2024")
            run = C.atomic_write_json(obj, Path(d) / "controls" / "16_run_log.json")
            self.assertIn("0-4", run.read_text(encoding="utf-8"))  # control positivo

    def test_the_module_frame_is_never_mutated_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            df = self.frame()
            C.atomic_write_csv(df, Path(d) / self.VARIANT / self.LANG / "tables" / "T9.csv")
            self.assertEqual(df.iloc[0, 0], "0-4")

    @staticmethod
    def hyphens(path):
        with Path(path).open(encoding="utf-8-sig", newline="") as fh:
            return sum(C.count_hyphen_ranges(c) for row in csv.reader(fh) for c in row)

    @staticmethod
    def dashes(path):
        with Path(path).open(encoding="utf-8-sig", newline="") as fh:
            return sum(C.count_dash_ranges(c) for row in csv.reader(fh) for c in row)


class PlateRangeDashTest(unittest.TestCase):
    def figure(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.bar(["0-4", "5-9", "10-14"], [1, 2, 3], label="2019-2024")
        ax.set_title("Median and 6-7 by band")
        ax.set_xlabel("Age band 0-4 to 10-14")
        ax.set_ylabel("Episodes 2019-2024")
        ax.legend(title="Series 2019-2024")
        ax.text(0.5, 0.5, "note: 31-59 months; key grd_rate:x:2019-2024", transform=ax.transAxes)
        fig.text(0.01, 0.01, "footer 2021-2025")
        return fig

    def texts(self, fig):
        from matplotlib.text import Text
        fig.canvas.draw()
        return [t.get_text() for t in fig.findobj(Text) if t.get_visible() and t.get_text()]

    def test_every_drawn_text_takes_the_en_dash(self):
        fig = self.figure()
        before = sum(C.count_hyphen_ranges(s) for s in self.texts(fig))
        self.assertGreaterEqual(before, 8)  # control positivo: la figura nace con el defecto
        C.plate_range_dash(fig)
        after = sum(C.count_hyphen_ranges(s) for s in self.texts(fig))
        self.assertEqual(after, 0)
        joined = " ".join(self.texts(fig))
        self.assertIn("grd_rate:x:2019-2024", joined)  # la clave de máquina sobrevive
        self.assertIn("0" + EN_DASH + "4", joined)

    def test_the_rule_is_idempotent_over_a_figure(self):
        fig = self.figure()
        C.plate_range_dash(fig)
        self.assertEqual(C.plate_range_dash(fig), 0)

    def test_the_layout_engine_applies_it_without_the_module_asking(self):
        # `plate_fit` es la primera mitad del motor: todas las láminas del estudio pasan por él o por
        # `plate_resolve`, y por eso ningún módulo tiene que acordarse de llamar a la regla.
        fig = self.figure()
        C.plate_fit(fig)
        self.assertEqual(sum(C.count_hyphen_ranges(s) for s in self.texts(fig)), 0)


# ---------------------------------------------------------------------------
# 3. La puerta de regresión sobre el corpus ya escrito
# ---------------------------------------------------------------------------
def printed_tables():
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            base = CFG.OUT / variant / lang
            for tdir in (base / "tables", base / "extra" / "tables"):
                if tdir.is_dir():
                    for p in sorted(tdir.glob("*.csv")):
                        if not p.stem.endswith("_numeric"):
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


def verbatim_headers():
    """Los encabezados de TRANSCRIPCIÓN LITERAL, leídos del módulo que los imprime (09b), no copiados.

    Son las columnas que citan un diccionario o un cuestionario chileno: retocar su tipografía rompería
    la cita, y por eso conservan el guion que publica la fuente. Que la puerta los lea del propio módulo
    es lo que impide que la exención del escritor y la de la prueba se separen con el tiempo."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_j2_09b", PKG / "pipeline" / "09b_tables_supplementary.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return frozenset().union(*(mod.verbatim_headers(lang) for lang in CFG.LANGUAGES))


class CorpusHasOneDashTest(unittest.TestCase):
    """Puerta: un intervalo de lectura nuevo escrito con guion hace fallar esta prueba."""

    @classmethod
    def setUpClass(cls):
        cls.verbatim = verbatim_headers()

    def reader_hyphens(self, path):
        bad = []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            return bad
        keep = [i for i, h in enumerate(rows[0])
                if not C.range_dash_verbatim_header(h) and h not in self.verbatim]
        for row in rows:
            for i in keep:
                if i < len(row) and C.count_hyphen_ranges(row[i]):
                    bad.append(row[i][:80])
        return bad

    def test_the_verbatim_exemption_is_declared_in_one_place(self):
        self.assertIn("Response codes", self.verbatim)
        self.assertIn("Códigos de respuesta", self.verbatim)
        self.assertNotIn("Grupo etario", self.verbatim)

    def test_no_printed_table_writes_a_reader_interval_with_a_hyphen(self):
        tables = list(printed_tables())
        if not tables:
            self.skipTest("no hay tablas construidas en outputs/")
        offenders = {}
        for p in tables:
            bad = self.reader_hyphens(p)
            if bad:
                offenders[f"{p.parent.parent.name}/{p.parent.name}/{p.name}"] = bad[:4]
        self.assertEqual(offenders, {}, f"{len(offenders)} tabla(s) impresas con guion: {offenders}")

    def test_no_title_or_caption_writes_a_reader_interval_with_a_hyphen(self):
        labels = list(printed_labels())
        if not labels:
            self.skipTest("no hay títulos ni leyendas construidos en outputs/")
        offenders = {}
        for p in labels:
            obj = json.loads(p.read_text(encoding="utf-8"))
            bad = [s[:80] for s in _strings(obj) if C.count_hyphen_ranges(s)]
            if bad:
                offenders[f"{p.parent.parent.name}/{p.parent.name}/{p.name}"] = bad[:4]
        self.assertEqual(offenders, {}, f"{len(offenders)} archivo(s) de rótulos con guion: {offenders}")

    def test_positive_control_the_gate_would_see_the_defect(self):
        # Sin esto, «cero infractores» podría significar «el instrumento no mira».
        planted = "Documented F84 · 0-4"
        self.assertEqual(C.count_hyphen_ranges(planted), 1)
        self.assertTrue(C.range_dash_verbatim_header("Etiquetas de valor (textual)"))
        self.assertTrue(C.range_dash_verbatim_header("Value labels (verbatim)"))
        self.assertFalse(C.range_dash_verbatim_header("Grupo etario"))


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


# ---------------------------------------------------------------------------
# 4. Ningún módulo vuelve a escribir su propia copia de la regla
# ---------------------------------------------------------------------------
class OnlyOneCopyOfTheRuleTest(unittest.TestCase):
    #: La sexta copia es la que rompe la regla: hasta la fase 4j había cinco, idénticas palabra por
    #: palabra, y los cuatro módulos de lámina que no la tenían imprimían el guion.
    FORBIDDEN = ('re.compile(r"(?<=\\d)-(?=\\d)")', "_IV_HYPHEN")

    def test_no_pipeline_module_declares_its_own_interval_regex(self):
        offenders = {}
        for p in sorted((PKG / "pipeline").glob("*.py")):
            src = p.read_text(encoding="utf-8")
            hits = [f for f in self.FORBIDDEN if f in src]
            if hits:
                offenders[p.name] = hits
        self.assertEqual(offenders, {},
                         "la regla del intervalo vive en common.py; estos módulos la vuelven a escribir: "
                         f"{offenders}")

    def test_common_is_the_one_place_that_declares_it(self):
        src = (PKG / "common.py").read_text(encoding="utf-8")
        self.assertIn("_RANGE_HYPHEN_RE", src)
        self.assertEqual(src.count("def range_dash("), 1)
        self.assertEqual(src.count("def plate_range_dash("), 1)


if __name__ == "__main__":
    unittest.main()
