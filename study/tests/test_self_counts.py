"""Pruebas de los recuentos que los documentos declaran SOBRE SÍ MISMOS.

Cubren los defectos 1, 9, 10 y 15 de la revisión página a página y, desde el rediseño de la Figura 1, la
separación entre lo que dice la lámina y lo que dicen los documentos:

* toda cifra suplementaria (láminas, tablas y ecuaciones numeradas) sale del registro compartido
  `supplementary_material` y de `equations`, no de un recuento de archivos en disco;
* todo total de control sale de `controls_registry` y va acompañado del ÁMBITO escrito en palabras, de modo
  que dos totales distintos del mismo documento no puedan leerse como versiones contradictorias de la misma
  cifra;
* la Figura 1 responde tres preguntas sobre cada FUENTE —qué es una fila, cuántas hay y qué se cuenta al
  final— y ya NO cuenta figuras, tablas, ecuaciones, controles ni artefactos: ni en la lámina, ni en su
  leyenda, ni en su tabla de recuentos (Tabla S2). Esas cifras siguen viviendo en el texto, en los métodos
  extendidos y en `values_<variante>.json`, y allí se comprueban;
* las dos cifras de fechas inválidas (episodios F84 y episodios GRD de cualquier diagnóstico) son
  distintas, llevan su unidad y se reproducen desde `grd_length_of_stay.csv`. Ninguna se dibuja en el
  esquema, así que desde la fase 4e viven en la Tabla S2 y allí se comprueban, no en la leyenda;
* la leyenda de la Figura 1 no arrastra rutas de archivo largas, que estiraban las líneas justificadas, y
  cabe entera bajo la lámina en una sola página.
"""
from pathlib import Path
import json
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
import controls_registry as CR  # noqa: E402
import equations as EQ  # noqa: E402
import supplementary_material as SM  # noqa: E402

CONTROLS_DIR = CFG.OUT / "controls"
SUMMARY = CONTROLS_DIR / "controls_summary.csv"
DATAFLOW = CFG.TIDY / "dataflow_counts.csv"
VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")

HAS_OUTPUTS = (SUMMARY.is_file() and DATAFLOW.is_file()
               and all((CFG.OUT / f"values_{v}.json").is_file() for v in VARIANTS))
# palabras que marcan un párrafo que habla de los controles de reproducción
CONTROL_WORDS = ("control", "controles", "reproduction", "reproducción", "comprobacion", "checks")


def _dataflow():
    import pandas as pd
    return pd.read_csv(DATAFLOW)


def _value(df, variant, key):
    row = df[(df.variant == variant) & (df.key == key)]
    if row.empty:
        raise AssertionError(f"dataflow_counts.csv no trae la clave {key} para {variant}")
    return float(row.value.iloc[0])


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/controls/controls_summary.csv, tidy/dataflow_counts.csv y values_*.json")
class RegistryCountsTest(unittest.TestCase):
    """Defecto 1: la lámina, su leyenda y la Tabla S2 dicen lo que dice el registro compartido."""

    def test_registry_is_internally_consistent(self):
        c = SM.counts()
        self.assertEqual(c["figures"], len(SM.FIGURE_ORDER))
        self.assertEqual(c["tables"], len(SM.TABLE_ORDER))
        self.assertEqual(c["equations"], len(EQ.NUMBER))
        self.assertEqual(len(EQ.NUMBER), len(EQ.EQUATIONS),
                         "la numeración de ecuaciones y la lista de ecuaciones deben tener el mismo tamaño")
        inv = SM.inventory()
        self.assertEqual(sum(1 for r in inv if r["kind"] == "figure"), c["figures"])
        self.assertEqual(sum(1 for r in inv if r["kind"] == "table"), c["tables"])
        self.assertEqual(len(set(SM.FIGURE_ORDER)), len(SM.FIGURE_ORDER), "clave de lámina repetida")
        self.assertEqual(len(set(SM.TABLE_ORDER)), len(SM.TABLE_ORDER), "clave de tabla repetida")

    def test_the_plate_does_not_count_the_documents_it_belongs_to(self):
        """La Figura 1 describe las FUENTES; los recuentos del suplemento no son asunto suyo."""
        df = _dataflow()
        forbidden = {"e_fig_supp", "e_tab_supp", "d_equations", "e_fig_article", "e_tab_article",
                     "e_prov_artefacts", "e_prov_sources"}
        for variant in VARIANTS:
            keys = set(df[df.variant == variant].key)
            self.assertEqual(keys & forbidden, set(),
                             f"{variant}: la lámina de flujo volvió a contar figuras, tablas, ecuaciones o "
                             f"artefactos: {sorted(keys & forbidden)}")

    def test_the_plate_answers_the_three_questions_about_every_source(self):
        """Cada fuente trae su unidad de análisis, su n de entrada, su n tras la selección y su exclusión."""
        df = _dataflow()
        for variant in VARIANTS:
            sub = df[df.variant == variant]
            kinds = set(sub.unit_kind.unique())
            self.assertLessEqual({"record", "person"}, kinds,
                                 f"{variant}: la lámina debe distinguir registros de personas")
            # El carril de territorio añadió una tercera unidad —la comuna— porque su fila no es ni un
            # registro ni una persona; la lámina la marca con un hexágono y la palabra «comuna».
            self.assertLessEqual(kinds, {"record", "person", "place"},
                                 f"{variant}: unidad de análisis desconocida en la lámina: {kinds}")
            for question in ("1_unit", "2_entry", "2_selection", "2_exclusion", "3_counted"):
                self.assertGreater(int((sub.question == question).sum()), 0,
                                   f"{variant}: la lámina no responde la pregunta {question}")
            for key in ("grd_in", "grd_sel", "deis_in", "deis_sel", "rema_in", "a05_last", "remp_in",
                        "p2_last", "endide_adults", "encavi_n", "pie_base_last", "pie_last"):
                self.assertIn(key, set(sub.key), f"{variant}: falta la cifra {key}")
            self.assertTrue(sub.source_file.notna().all(), f"{variant}: una cifra sin tabla de origen")
            self.assertTrue(sub.source_column_or_key.notna().all(), f"{variant}: una cifra sin columna de origen")

    def test_supplementary_note_and_index_use_the_registry(self):
        class _R:
            def fig(self, key):
                return f"Figure S{SM.FIGURE_ORDER.index(key) + 1}"

            def tab(self, key):
                return f"Table S{SM.TABLE_ORDER.index(key) + 1}"

        c = SM.counts()
        for lang in LANGS:
            note, index = SM.part_texts(lang, _R())
            for n in (c["figures"], c["tables"]):
                self.assertIn(str(n), note + index, f"{lang}: la nota/índice no declara {n}")
            self.assertIn(str(c["equations"]), index, f"{lang}: el índice no declara las ecuaciones")


@unittest.skipUnless(HAS_OUTPUTS, "requiere las salidas del pipeline")
class ControlScopeTest(unittest.TestCase):
    """Defecto 9: un solo origen para cada total de control y el ámbito siempre escrito."""

    def test_summary_has_a_scope_column_with_known_scopes(self):
        import pandas as pd
        df = pd.read_csv(SUMMARY, dtype=str, keep_default_na=False)
        self.assertIn("scope", df.columns)
        self.assertEqual(set(df.scope.unique()), set(CR.scopes()))

    def test_pipeline_scope_consolidates_every_module_control_file(self):
        import pandas as pd
        df = pd.read_csv(SUMMARY, dtype=str, keep_default_na=False)
        pipe = df[df.scope == CR.PIPELINE]
        files = sorted(CONTROLS_DIR.glob("*_controls.csv"))
        self.assertEqual(sorted(pipe.module.unique()), sorted(p.name[: -len("_controls.csv")] for p in files),
                         "el consolidado debe traer TODOS los módulos, del 00 al 17")
        for path in files:
            module = path.name[: -len("_controls.csv")]
            self.assertEqual(int((pipe.module == module).sum()), len(pd.read_csv(path, dtype=str, keep_default_na=False)),
                             f"{module}: el consolidado no coincide con su archivo de controles (¿corrida vieja?)")
        self.assertEqual(CR.totals(CR.PIPELINE, refresh=True)["checks"], len(pipe))
        self.assertEqual(CR.totals(CR.PIPELINE)["files"], len(files))

    def test_analysis_plan_scope_matches_the_control_table(self):
        import pandas as pd
        t8 = CFG.OUT / "con_rett" / "en" / "tables" / "T8_controls_numeric.csv"
        if not t8.is_file():
            self.skipTest("falta T8_controls_numeric.csv")
        plan = CR.totals(CR.ANALYSIS_PLAN, refresh=True)
        self.assertEqual(plan["checks"], len(pd.read_csv(t8)))

    def test_e79_total_reconciles_with_the_pipeline_scope(self):
        """La Tabla E79 cuenta un archivo menos (el suyo, que se escribe después) y lo declara en su nota."""
        import pandas as pd
        pipe = CR.totals(CR.PIPELINE)
        for variant in VARIANTS:
            path = CFG.OUT / variant / "en" / "extra" / "tables" / "E79_reproduction_controls_by_family.csv"
            if not path.is_file():
                self.skipTest("falta E79_reproduction_controls_by_family.csv")
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
            total = int(df[df.iloc[:, 0] == "TOTAL"]["Checks"].iloc[0].replace(",", "").replace(".", ""))
            own = len(pd.read_csv(CONTROLS_DIR / "16_extra_tables_controls.csv", dtype=str, keep_default_na=False))
            self.assertEqual(total + own, pipe["checks"],
                             f"{variant}: E79 ({total}) + los controles del módulo 16 ({own}) deben dar el total del pipeline")

    def test_m10_module_names_match_the_consolidated_summary(self):
        """El nombre del módulo es una CLAVE: la M10 y el consolidado tienen que escribirlo igual.

        `module=path.stem.replace("_controls", "")` quitaba TODAS las apariciones, de modo que el tallo
        `07_controls_controls` se quedaba en «07» —el único módulo del pipeline cuyo nombre contiene
        «_controls»—. La Tabla S12 imprimía «07» donde la S10 escribe `pipeline/07_controls.py` y la S123
        escribe `07_controls`: el mismo módulo con dos nombres dentro de un documento, y las dos tablas sin
        poder unirse por esa columna. Los cuatro CSV numéricos de M10 se publican en «Data sharing»."""
        import pandas as pd
        df = pd.read_csv(SUMMARY, dtype=str, keep_default_na=False)
        expected = sorted(df[df.scope == CR.PIPELINE].module.unique())
        seen = 0
        for variant in VARIANTS:
            for lang in LANGS:
                path = CFG.OUT / variant / lang / "extra" / "tables" / "M10_reproduction_controls_numeric.csv"
                if not path.is_file():
                    continue
                seen += 1
                m10 = pd.read_csv(path, dtype=str, keep_default_na=False)
                self.assertEqual(sorted(m10.module.unique()), expected,
                                 f"{variant}/{lang}: los nombres de módulo de M10 no son los del consolidado")
                for _, r in m10.iterrows():
                    self.assertEqual(r["file"], f"{r['module']}_controls.csv",
                                     f"{variant}/{lang}: la fila {r['module']} no casa con su propio archivo")
        if not seen:
            self.skipTest("faltan los M10_reproduction_controls_numeric.csv")

    def test_the_two_scopes_are_different_totals_and_never_added(self):
        pipe, plan = CR.totals(CR.PIPELINE), CR.totals(CR.ANALYSIS_PLAN)
        self.assertNotEqual(pipe["checks"], plan["checks"],
                            "si los dos ámbitos coincidieran, el rótulo dejaría de distinguirlos y habría que revisar la prueba")
        for lang in LANGS:
            self.assertNotEqual(CR.phrase(CR.PIPELINE, lang), CR.phrase(CR.ANALYSIS_PLAN, lang))
            self.assertIn(str(pipe["files"]), CR.phrase(CR.PIPELINE, lang))

    def test_the_plate_does_not_print_control_totals(self):
        """Los totales de control se informan en el texto y en los métodos extendidos, no en la Figura 1."""
        df = _dataflow()
        forbidden = {"e_controls_n", "e_controls_ok", "e_controls_info", "e_controls_diff",
                     "e_controls_modules", "e_controls_plan_n"}
        for variant in VARIANTS:
            keys = set(df[df.variant == variant].key)
            self.assertEqual(keys & forbidden, set(),
                             f"{variant}: la lámina de flujo volvió a imprimir totales de control: "
                             f"{sorted(keys & forbidden)}")

    def test_values_json_carries_the_pipeline_scope_only(self):
        for variant in VARIANTS:
            V = json.loads((CFG.OUT / f"values_{variant}.json").read_text(encoding="utf-8"))
            self.assertEqual(V["controls_csv_rows"], CR.totals(CR.PIPELINE)["checks"], variant)
            self.assertEqual(V["controls_csv_ok"], CR.totals(CR.PIPELINE)["ok"], variant)
            self.assertEqual(V["controls_csv_differs"], CR.totals(CR.PIPELINE)["differs"], variant)
            self.assertEqual(V["controls_csv_modules_n"], CR.totals(CR.PIPELINE)["files"], variant)
            self.assertEqual(V["t8_rows"], CR.totals(CR.ANALYSIS_PLAN)["checks"], variant)

    def test_figure1_caption_names_the_units_and_the_no_linkage_rule(self):
        """La leyenda de la Figura 1 es autocontenida: unidades y regla de no enlace, sin recuentos de salidas."""
        wanted = {"en": ("RECORDS", "PEOPLE", "no record is linked across systems", "only within a year"),
                  "es": ("REGISTROS", "PERSONAS", "ningún registro se enlaza entre sistemas",
                         "solo dentro de un año")}
        for variant in VARIANTS:
            for lang in LANGS:
                caps = json.loads((CFG.OUT / variant / lang / "figures" / "captions.json").read_text(encoding="utf-8"))
                cap = caps["fig1_dataflow"]["caption"]
                low = cap.lower()
                for phrase in wanted[lang]:
                    self.assertIn(phrase.lower(), low,
                                  f"{variant}/{lang}: la leyenda no dice «{phrase}»")
                for scope in CR.scopes():
                    self.assertNotIn(CR.phrase(scope, lang), cap,
                                     f"{variant}/{lang}: la leyenda de la Figura 1 volvió a contar controles")
                    total = C.fmt_number(CR.totals(scope)["checks"], 0, lang)
                    self.assertNotRegex(cap, rf"(?<![\d.,]){re.escape(total)}(?![\d.,])",
                                        f"{variant}/{lang}: la leyenda imprime el total de control {total}")


@unittest.skipUnless(HAS_OUTPUTS, "requiere las salidas del pipeline")
class InvalidDateUnitsTest(unittest.TestCase):
    """Defecto 10: la lámina distingue episodios F84 de episodios GRD de cualquier diagnóstico."""

    def test_two_counts_with_their_own_unit(self):
        import pandas as pd
        los = pd.read_csv(CFG.TIDY / "grd_length_of_stay.csv")
        df = _dataflow()
        for variant in VARIANTS:
            all_ep = los[(los.variant == "all_episodes") & (los.panel == "observed") & (los.activity == "all")]
            f84 = los[(los.variant == variant) & (los.position == "any") & (los.panel == "observed")
                      & (los.activity == "all")]
            self.assertEqual(_value(df, variant, "b_grd_bad_dates"), float(all_ep.n_invalid_dates.sum()))
            self.assertEqual(_value(df, variant, "b_grd_bad_dates_f84"), float(f84.n_invalid_dates.sum()))
            self.assertLess(_value(df, variant, "b_grd_bad_dates_f84"), _value(df, variant, "b_grd_bad_dates"),
                            "el subconjunto F84 no puede igualar el total de episodios GRD")
            # la fila de la Tabla S2 nombra la unidad de cada cifra
            rows = df[(df.variant == variant) & (df.key.isin(["b_grd_bad_dates", "b_grd_bad_dates_f84"]))]
            self.assertTrue((rows.unit_en == "episodes").all())
            self.assertIn("any diagnosis", rows[rows.key == "b_grd_bad_dates"].label_en.iloc[0])
            self.assertIn("F84", rows[rows.key == "b_grd_bad_dates_f84"].label_en.iloc[0])

    def test_the_counts_table_states_both_counts_with_their_unit(self):
        """Las dos cifras viven en la TABLA de recuentos, que es donde el lector las encuentra.

        Ninguna de las dos se dibuja en el esquema (`on_plate` es falso para las dos), de modo que desde
        que la leyenda dejó de recitar cifras —fase 4e, tarea Y1: la leyenda ocupaba 37 líneas en inglés y
        39 en español y se partía en una página de continuación— la Tabla S2 es su único sitio. Se
        comprueba ahí, en los dos idiomas y con el formato de número de cada uno, y se comprueba además
        que la leyenda manda al lector a esa tabla.
        """
        import pandas as pd
        df = _dataflow()
        for variant in VARIANTS:
            for lang in LANGS:
                num = pd.read_csv(CFG.OUT / variant / lang / "extra" / "tables" / "T_dataflow_counts_numeric.csv")
                fmtd = pd.read_csv(CFG.OUT / variant / lang / "extra" / "tables" / "T_dataflow_counts.csv",
                                   dtype=str, keep_default_na=False)
                for key, big in (("b_grd_bad_dates", True), ("b_grd_bad_dates_f84", False)):
                    row = num[num.key == key]
                    self.assertFalse(row.empty, f"{variant}/{lang}: la Tabla S2 no trae la fila {key}")
                    self.assertFalse(bool(row.on_plate.iloc[0]),
                                     f"{variant}/{lang}: {key} no se dibuja en el esquema y la tabla dice que sí")
                    value = C.fmt_number(_value(df, variant, key), 0, lang)
                    label = row[f"label_{lang}"].iloc[0]
                    hit = fmtd[(fmtd.iloc[:, 3] == label) & (fmtd.iloc[:, 5] == value)]
                    self.assertFalse(hit.empty,
                                     f"{variant}/{lang}: la Tabla S2 no imprime «{label}» con el valor {value}")
                    unit = row[f"unit_{lang}"].iloc[0]
                    self.assertEqual(hit.iloc[0, 4], unit,
                                     f"{variant}/{lang}: la fila {key} no lleva su unidad")
                    if big:
                        self.assertRegex(label, r"(any diagnosis|cualquier diagnóstico)",
                                         f"{variant}/{lang}: la fila mayor no dice de qué episodios habla")
                    else:
                        self.assertIn("F84", label, f"{variant}/{lang}: la fila menor no dice que es F84")
                caps = json.loads((CFG.OUT / variant / lang / "figures" / "captions.json").read_text(encoding="utf-8"))
                cap = caps["fig1_dataflow"]["caption"]
                self.assertRegex(cap, r"(companion table|tabla de recuentos)",
                                 f"{variant}/{lang}: la leyenda no manda al lector a la tabla de recuentos")


@unittest.skipUnless(HAS_OUTPUTS, "requiere las salidas del pipeline")
class CaptionTypographyTest(unittest.TestCase):
    """Defecto 15: la leyenda de la Figura 1 ya no arrastra rutas largas que estiran la justificación."""

    def test_caption_has_no_long_file_paths(self):
        for variant in VARIANTS:
            for lang in LANGS:
                caps = json.loads((CFG.OUT / variant / lang / "figures" / "captions.json").read_text(encoding="utf-8"))
                cap = caps["fig1_dataflow"]["caption"]
                offenders = [t for t in re.findall(r"\S+", cap) if "/" in t and len(t) > 14]
                self.assertEqual(offenders, [], f"{variant}/{lang}: rutas largas en la leyenda: {offenders}")


@unittest.skipUnless(HAS_OUTPUTS and (CFG.OUT / "con_rett" / "en" / "figures" / "captions.json").is_file(),
                     "requiere las láminas y tablas por variante e idioma")
class ProseScopeTest(unittest.TestCase):
    """Ningún párrafo de los documentos imprime un total de control sin decir de qué ámbito habla."""

    @classmethod
    def setUpClass(cls):
        import prose_en as E
        import prose_es as S
        cls.P = {"en": E, "es": S}
        cls.docs, cls.notes = {}, {}
        for variant in VARIANTS:
            V = E.load_values(variant)
            for lang, mod in cls.P.items():
                art, main, supp, _R = mod._assemble(variant, V)
                cls.docs[(variant, lang)] = [str(p) for k, p in main + supp if k == "p"]
                notes = []
                for kind, payload in main + supp:
                    if kind == "table":
                        notes.append((payload.get("label", "?"), f"{payload.get('title', '')} {payload.get('note', '')}"))
                    elif kind == "figure":
                        notes.append((payload.get("label", "?"), f"{payload.get('title', '')} {payload.get('caption', '')}"))
                cls.notes[(variant, lang)] = notes

    def test_every_control_total_carries_its_scope(self):
        for (variant, lang), paragraphs in self.docs.items():
            for scope in CR.scopes():
                total = C.fmt_number(CR.totals(scope)["checks"], 0, lang)
                phrase, label = CR.phrase(scope, lang), CR.label(scope, lang)
                for text in paragraphs:
                    low = text.lower()
                    if not re.search(rf"(?<![\d.,]){re.escape(total)}(?![\d.,])", text):
                        continue
                    if not any(w in low for w in CONTROL_WORDS):
                        continue
                    self.assertTrue(phrase in text or label in text,
                                    f"{variant}/{lang}: total de control {total} sin ámbito en: {text[:160]}")

    def test_every_caption_and_table_note_carries_its_scope(self):
        """Una leyenda o una nota de tabla que imprime un total de control también nombra su ámbito."""
        for (variant, lang), notes in self.notes.items():
            for scope in CR.scopes():
                total = C.fmt_number(CR.totals(scope)["checks"], 0, lang)
                phrase, label = CR.phrase(scope, lang), CR.label(scope, lang)
                for lab, text in notes:
                    if not re.search(rf"(?<![\d.,]){re.escape(total)}(?![\d.,])", text):
                        continue
                    self.assertTrue(phrase in text or label in text,
                                    f"{variant}/{lang} {lab}: total de control {total} sin ámbito")

    def test_the_supplement_states_both_scopes_side_by_side(self):
        for (variant, lang), paragraphs in self.docs.items():
            joined = " ".join(paragraphs)
            for scope in CR.scopes():
                self.assertIn(CR.phrase(scope, lang), joined,
                              f"{variant}/{lang}: el documento nunca nombra el ámbito {scope}")
                self.assertIn(C.fmt_number(CR.totals(scope)["checks"], 0, lang), joined,
                              f"{variant}/{lang}: el documento no imprime el total del ámbito {scope}")


if __name__ == "__main__":
    unittest.main()
