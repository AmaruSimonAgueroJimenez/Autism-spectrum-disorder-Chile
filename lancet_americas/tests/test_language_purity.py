# -*- coding: utf-8 -*-
"""Pruebas de pureza de idioma (defecto 7 de la revisión página a página).

El estudio publica CUATRO documentos —dos variantes de definición de caso × dos idiomas— y cada uno
debe estar escrito íntegramente en su idioma. Antes de esta tarea el texto libre se filtraba en las dos
direcciones: la Tabla S121 (JUNAEB) traía sus columnas «Ponderador y diseño» y «Estimable» en español
dentro del documento en inglés, la Tabla S108 imprimía las categorías CIE-10 solo con su glosa española,
la Tabla S123 mostraba la anotación en español de cada módulo, y al revés, las Tablas S118, S122 y S124
mostraban texto en inglés dentro del documento en español.

Qué comprueban estas pruebas:

  1. `LanguageMarkerTest` — que el detector `labels.language_leak` sigue siendo capaz de ver una fuga
     (si alguien lo vacía, esta prueba falla antes que las demás).
  2. `BuiltDocumentLanguageTest` — el barrido real: arma los BLOQUES de los cuatro documentos con
     `prose_en.manuscript()` y `prose_es.manuscript()` —no los archivos tidy— y revisa título, subtítulo,
     encabezados, párrafos, viñetas, paneles, títulos, notas, encabezados de columna y CELDAS de todas
     las tablas, y las leyendas de todas las láminas.
  3. `TidyTextTest` — que la glosa bilingüe de `labels.tidy_text` cubre el texto libre de los archivos
     tidy que los módulos 11 y 16 imprimen, de modo que la fuga no pueda volver por la puerta del dato.
  4. `Icd10DictionaryTest` — que el diccionario CIE-10 del repositorio es único y bilingüe, que cubre
     todas las glosas españolas que usa el pipeline y que incluye J30, el código que se imprimía sin
     glosa.
  5. `FigureLiteralTest` — que ningún rótulo, leyenda o anotación de una lámina se escribe con un
     literal suelto: todo texto que se dibuja en una figura tiene que venir de un rótulo declarado en
     los dos idiomas.
  6. `ProvenanceTextTest` — que los campos descriptivos de los 182 artefactos fuente (unidad, período,
     stock/flujo, quiebres, enlace, regla de uso) y las notas de concordancia de manifiesto se leen en
     español, con los miles escritos con punto.
  7. `GrdEpisodeCategoryTest` — que toda categoría administrativa del episodio GRD fuera de la exención
     que la tabla declara tiene glosa inglesa, que el español conserva la forma de la fuente y que los
     estados del dato se leen incluso dentro de las variables exentas.
  8. `NumberFormatTest` — que el mismo número no se imprime con la misma cadena en los dos idiomas
     (25.618 en español, 25,618 en inglés), alineando los cuatro documentos celda a celda.

Lo que la tarea LG endureció, y por qué la revisión había pasado con 0 fugas mientras el verificador
contaba 596 marcadores ingleses en el suplemento español:

  * una NOTA de tabla ya no exime a nada. Antes bastaba con que la nota dijera «se transcriben en inglés
    tal como constan» para silenciar las quince columnas y las 2.730 celdas de la Tabla S14. Ahora un
    encabezado solo se exime si él mismo declara la transcripción, y una celda solo por SU columna.
  * un marcador de estado («ABSENT», «MISSING», «n/a», «Outcome», «no reportado») es fuga por sí solo:
    son demasiado cortos para llegar al umbral de tres palabras funcionales, y ninguna declaración de
    transcripción los exime, porque no son cita de nada (`labels.PLACEHOLDER_MARKERS`).

Excepciones legítimas, y por qué no son fugas:

  * una columna o una nota que DECLARA que transcribe la fuente sin traducir («verbatim Spanish»,
    «Original Spanish wording», «se transcriben en inglés tal como constan») — el lector sabe lo que
    está leyendo, y traducir la redacción literal de un cuestionario destruiría la trazabilidad;
  * los valores codificados por el registro (países, servicios de salud, especialidades, tramos
    previsionales), que van en mayúsculas y son el valor del dato, no prosa;
  * los nombres propios («Magallanes y de la Antártica Chilena», «Junta Nacional de Auxilio Escolar y
    Becas»), iguales en los dos idiomas.

`KNOWN_OPEN` lista las fugas que quedan en módulos que NO pertenecen a esta tarea; cada entrada nombra
el módulo productor. Una fuga nueva en cualquier otro sitio hace fallar la prueba.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

LA = Path(__file__).resolve().parents[1]
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import config as CFG  # noqa: E402
import labels as LB  # noqa: E402

VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")

HAS_OUTPUTS = (all((CFG.OUT / f"values_{v}.json").is_file() for v in VARIANTS)
               and all((CFG.OUT / v / lang / sub / "captions.json").is_file()
                       for v in VARIANTS for lang in LANGS for sub in ("figures", "extra/figures")))

# ---------------------------------------------------------------------------
# Fugas conocidas cuyo módulo productor NO pertenece a esta tarea
# ---------------------------------------------------------------------------
# Cada entrada es (idioma del documento, rótulo del ítem, columna, prefijo del texto, módulo productor).
# El prefijo es la parte estable de la celda: así una fuga NUEVA en la misma columna sigue fallando.
#: Vacía desde la tarea L5: las tres fugas que quedaban (la nota de módulo en español de la Tabla 7 y de la
#: Tabla S49, y el indicador del diccionario REM de la Tabla S5) se cerraron en su módulo productor
#: —`pipeline/07_controls.py` (NOTE_GLOSS/note_text) y `prose_methods_extended.py` (glosa
#: `labels.rem_indicator`)—, de modo que el barrido las vigila como a cualquier otra celda.
KNOWN_OPEN: tuple[tuple[str, str, str, str, str], ...] = ()


# Marcadores de ruta que se escriben en un solo idioma («outputs/<variante>/<idioma>/…»). En el documento
# en inglés el marcador tiene que ser <variant>/<language>, y al revés en el español.
SPANISH_PLACEHOLDERS = ("<variante", "<idioma", "<clave>", "<indicador>", "<módulo")
ENGLISH_PLACEHOLDERS = ("<variant>", "<language>", "<key>", "<indicator>", "<module>")
#: (idioma del documento, rótulo del ítem, módulo productor) de los marcadores que siguen en el idioma
#: equivocado en módulos que NO pertenecen a esta tarea.
#: Las Tablas S7 y S10 salieron de esta lista en la tarea L5: `prose_methods_extended._paths` traduce ahora los
#: marcadores comodín al idioma del documento (la forma canónica sigue siendo la española, la que esperan
#: `output_exists` y los comodines de disco). La Tabla S2 salió en la tarea L1: la Figura 1 rediseñada y su tabla
#: de recuentos ya no imprimen ninguna ruta de archivo, así que no queda marcador que traducir.
KNOWN_OPEN_PLACEHOLDERS: tuple[tuple[str, str, str], ...] = ()


def _is_known(lang: str, label: str, where: str, text: str) -> bool:
    return any(lang == l and label == lb and where == w and text.startswith(pref)
               for l, lb, w, pref, _ in KNOWN_OPEN)


# ---------------------------------------------------------------------------
# Barrido de los bloques de un documento construido
# ---------------------------------------------------------------------------
def scan_blocks(blocks, lang: str) -> list[tuple[str, str, str, dict]]:
    """Todas las fugas de idioma de los bloques de `docx_builder` de un documento.

    Devuelve (rótulo del ítem, dónde, texto, marcadores). No mira los bloques de referencias: la
    bibliografía cita títulos en su idioma original y eso no es una fuga."""
    found: list[tuple[str, str, str, dict]] = []
    n_tab = n_fig = 0

    def check(label, where, value, context=""):
        leak = LB.language_leak(value, lang, context=context)
        if leak and not _is_known(lang, label, where, str(value).strip()):
            found.append((label, where, str(value), leak))

    for kind, payload in blocks:
        if kind in ("p", "small", "title", "subtitle", "h1", "h2", "h3"):
            check(kind, "text", payload)
        elif kind == "bullets":
            for item in payload:
                check(kind, "text", item)
        elif kind == "panel":
            check(kind, "title", payload.get("title", ""))
            for head, text in payload["items"]:
                check(kind, "item", head)
                check(kind, "item", text)
        elif kind == "table":
            n_tab += 1
            label = payload.get("label") or f"table {n_tab}"
            note = str(payload.get("note", ""))
            check(label, "title", payload.get("title", ""))
            check(label, "note", note)
            df = payload["df"]
            for column in df.columns:
                # Un encabezado no es cita de nada: solo se exime si él mismo declara la transcripción.
                # Y una celda se exime por SU columna, no por la nota de la tabla: hasta la tarea LG la
                # nota de la Tabla S14 decía «se transcriben en inglés» y con eso silenciaba las 15
                # columnas y las 2.730 celdas de la tabla, incluidas las 544 frases inglesas del
                # suplemento español que la revisión encontró.
                check(label, "header", str(column), context=str(column))
                for value in df[column].astype(str).unique():
                    check(label, f"cell[{column}]", value, context=str(column))
        elif kind == "figure":
            n_fig += 1
            label = payload.get("label") or f"figure {n_fig}"
            check(label, "caption", payload.get("caption", ""))
    return found


def _report(found, lang, variant) -> str:
    lines = [f"{len(found)} fuga(s) de idioma en el documento {lang}/{variant}:"]
    for label, where, text, leak in found[:25]:
        lines.append(f"  · {label} {where}: marcadores {leak['wrong'][:8]} → {text[:180]}")
    if len(found) > 25:
        lines.append(f"  … y {len(found) - 25} más")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1. El propio detector
# ---------------------------------------------------------------------------
class LanguageMarkerTest(unittest.TestCase):
    LEAKY_IN_ENGLISH = [
        "No — No estimable: el cuestionario 2019 no incluye categoría TEA. Se informa el filtro.",
        "EXP_REG; EE por linealización de Taylor con estudiantes como unidades independientes",
        "Z63 — Problemas relacionados con el grupo de apoyo primario",
        "otra especialidad (fuera de las 20 principales)",
        "alta anterior al ingreso: se excluye de la estadía y se informa en n_invalid_dates",
    ]
    LEAKY_IN_SPANISH = [
        "No specification estimates an effect of Law 21.545. Durbin–Watson with fewer than 8 points.",
        "rows are additive within a year (exact duplicates kept); geography mixes the enrolment comuna",
        "persons with valid benefits (December stock); sum only within year and sex",
    ]
    CLEAN_ENGLISH = [
        "Unit: GRD episode (not person). Counts are administrative recognition, never prevalence.",
        "Magallanes y de la Antártica Chilena",
        "Junta Nacional de Auxilio Escolar y Becas",
        "Unlinked non-geographic placeholders: Sin Código de Comuna, Sin dato Comuna",
        "E03 — Other hypothyroidism",
    ]
    CLEAN_SPANISH = [
        "Unidad: episodio GRD (no persona). Los recuentos son reconocimiento administrativo.",
        "Serie A del REM; archivo GRD_PUBLICO_2019.csv; columna n_students del acompañante numérico",
        "E03 — Otro hipotiroidismo",
    ]

    def test_detects_spanish_inside_english(self):
        for text in self.LEAKY_IN_ENGLISH:
            self.assertIsNotNone(LB.language_leak(text, "en"), f"no detectada: {text[:70]}")

    def test_detects_english_inside_spanish(self):
        for text in self.LEAKY_IN_SPANISH:
            self.assertIsNotNone(LB.language_leak(text, "es"), f"no detectada: {text[:70]}")

    def test_does_not_flag_clean_text(self):
        for text in self.CLEAN_ENGLISH:
            self.assertIsNone(LB.language_leak(text, "en"), f"falso positivo: {text[:70]}")
        for text in self.CLEAN_SPANISH:
            self.assertIsNone(LB.language_leak(text, "es"), f"falso positivo: {text[:70]}")

    #: Marcadores de estado: la revisión los contó 596 veces en el suplemento español.
    PLACEHOLDER_IN_SPANISH = ["ABSENT", "MISSING", "n/a", "Outcome (numerador)",
                              "not listed in any manifest", "no date in manifest"]
    PLACEHOLDER_IN_ENGLISH = ["ausente", "no reportado", "sin dato", "no estimable"]
    #: …y lo que NO es marcador: un identificador que lo contiene, o el valor que trae la fuente.
    NOT_A_PLACEHOLDER_IN_SPANISH = ["enrolled_tramo_missing", "n_missing_rows",
                                    "year|source_file|cotizantes|cargas|nonatos_sin_clasificar"]
    NOT_A_PLACEHOLDER_IN_ENGLISH = ["Sin dato Comuna", "Sin Código de Comuna", "NO APLICA"]

    def test_a_state_marker_of_the_other_language_is_a_leak_on_its_own(self):
        for text in self.PLACEHOLDER_IN_SPANISH:
            self.assertIsNotNone(LB.language_leak(text, "es"), f"no detectada: {text}")
        for text in self.PLACEHOLDER_IN_ENGLISH:
            self.assertIsNotNone(LB.language_leak(text, "en"), f"no detectada: {text}")

    def test_a_state_marker_is_not_seen_inside_an_identifier_or_a_source_value(self):
        for text in self.NOT_A_PLACEHOLDER_IN_SPANISH:
            self.assertIsNone(LB.language_leak(text, "es"), f"falso positivo: {text}")
        for text in self.NOT_A_PLACEHOLDER_IN_ENGLISH:
            self.assertIsNone(LB.language_leak(text, "en"), f"falso positivo: {text}")

    def test_a_verbatim_declaration_never_excuses_a_state_marker(self):
        """«ABSENT» no es una transcripción del cuestionario: lo escribió el módulo 05."""
        self.assertIsNotNone(LB.language_leak("ABSENT", "es", context="Redacción del ítem TEA (textual)"))

    def test_declared_verbatim_columns_are_exempt(self):
        wording = "¿Le ha dicho un médico que tiene…? Autismo (Trastorno del espectro Autista)"
        self.assertIsNotNone(LB.language_leak(wording, "en"))
        self.assertIsNone(LB.language_leak(wording, "en", context="Question wording (verbatim Spanish)"))

    def test_unknown_language_is_rejected(self):
        with self.assertRaises(ValueError):
            LB.language_leak("texto", "pt")


# ---------------------------------------------------------------------------
# 2. Los cuatro documentos construidos
# ---------------------------------------------------------------------------
@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante e idioma")
class BuiltDocumentLanguageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prose_en as E
        import prose_es as S
        cls.blocks = {}
        for lang, module in (("en", E), ("es", S)):
            for variant in VARIANTS:
                values = module.load_values(variant)
                cls.blocks[(lang, variant)] = module.manuscript(variant, values)

    def test_no_language_leak_in_any_document(self):
        for (lang, variant), blocks in self.blocks.items():
            with self.subTest(lang=lang, variant=variant):
                found = scan_blocks(blocks, lang)
                self.assertEqual(found, [], _report(found, lang, variant))

    def test_icd10_cells_carry_the_gloss_of_the_document_language(self):
        """Toda celda «CÓDIGO — glosa» de una tabla CIE-10 usa el diccionario único del repositorio."""
        pattern = re.compile(r"^([A-Z]\d\d)(?: — (.+))?$")
        headers = ("ICD-10 category", "Categoría CIE-10", "Principal diagnosis (ICD-10",
                   "Diagnóstico principal (CIE-10")
        checked = 0
        for (lang, variant), blocks in self.blocks.items():
            for kind, payload in blocks:
                if kind != "table":
                    continue
                for column in payload["df"].columns:
                    if not str(column).startswith(headers):
                        continue
                    for value in payload["df"][column].astype(str):
                        m = pattern.match(value.strip())
                        if not m:
                            continue
                        checked += 1
                        self.assertEqual(value.strip(), LB.icd_code_label(m.group(1), lang),
                                         f"{lang}/{variant} {payload.get('label')}: glosa CIE-10 fuera del "
                                         f"diccionario único de labels.py → {value}")
        self.assertGreater(checked, 200, "no se revisó ninguna celda CIE-10")

    def test_path_placeholders_are_written_in_the_document_language(self):
        """«outputs/<variante>/<idioma>/…» dentro del documento en inglés es texto en español."""
        known = {(lang, label) for lang, label, _ in KNOWN_OPEN_PLACEHOLDERS}
        found = []
        for (lang, variant), blocks in self.blocks.items():
            wrong = SPANISH_PLACEHOLDERS if lang == "en" else ENGLISH_PLACEHOLDERS
            n_tab = 0
            for kind, payload in blocks:
                if kind == "table":
                    n_tab += 1
                    label = payload.get("label") or f"table {n_tab}"
                    cells = [str(payload.get("title", "")), str(payload.get("note", ""))]
                    cells += [str(c) for c in payload["df"].columns]
                    cells += [v for c in payload["df"].columns for v in payload["df"][c].astype(str)]
                elif kind in ("p", "small", "h1", "h2", "h3"):
                    label, cells = kind, [str(payload)]
                elif kind == "bullets":
                    label, cells = kind, [str(i) for i in payload]
                else:
                    continue
                if (lang, label) in known:
                    continue
                for cell in cells:
                    for token in wrong:
                        if token in cell:
                            found.append((lang, variant, label, token, cell[:140]))
        self.assertEqual(found, [], f"marcadores de ruta en el idioma equivocado: {found[:8]}")

    def test_every_document_has_tables_and_figures_to_scan(self):
        """Una prueba que no mira nada pasa siempre: aquí se exige que haya algo que mirar."""
        for (lang, variant), blocks in self.blocks.items():
            kinds = [k for k, _ in blocks]
            self.assertGreater(kinds.count("table"), 100, f"{lang}/{variant}: faltan tablas")
            self.assertGreater(kinds.count("figure"), 50, f"{lang}/{variant}: faltan láminas")


# ---------------------------------------------------------------------------
# 3. El texto libre de los archivos tidy
# ---------------------------------------------------------------------------
TIDY_FREE_TEXT = {
    "fonasa_schema_by_year": ["age_band_scheme", "aggregation_rule", "unit"],
    "aps_panel": ["unit"],
    "isapre_beneficiaries_national_year": ["rule", "age_note", "aggregation_rule", "unit"],
    "survey_estimates": ["domain", "subgroup_type", "subgroup", "estimate_type", "precision_flag"],
    "pie_series": ["definition", "unit"],
    "junaeb_tea_year_level": ["design_note", "note"],
    "grd_episode_features": ["value"],
    "rem_pathway_annual": ["indicator"],
}


@unittest.skipUnless((CFG.TIDY / "survey_estimates.csv").is_file(), "requiere outputs/tidy/")
class TidyTextTest(unittest.TestCase):
    def test_free_text_of_the_tidy_files_is_declared_in_both_languages(self):
        import pandas as pd
        for name, columns in TIDY_FREE_TEXT.items():
            path = CFG.TIDY / f"{name}.csv"
            if not path.is_file():
                continue
            frame = pd.read_csv(path, dtype=str, keep_default_na=False)
            for column in columns:
                if column not in frame.columns:
                    continue
                for value in sorted({v for v in frame[column] if str(v).strip()}):
                    for lang in LANGS:
                        gloss = (LB.rem_indicator(value, lang) if column == "indicator"
                                 else LB.tidy_text(value, lang))
                        self.assertIsNone(
                            LB.language_leak(gloss, lang),
                            f"{name}.{column} no tiene glosa en «{lang}»: {gloss[:160]}")


# ---------------------------------------------------------------------------
# 3b. La procedencia de los 182 artefactos fuente
# ---------------------------------------------------------------------------
#: Columnas descriptivas de data_provenance.csv que la Tabla S14 imprime (o puede imprimir) y que, por
#: tanto, tienen que existir en los dos idiomas.
PROVENANCE_COLUMNS = ("observation_unit", "period", "stock_or_flow", "definition_breaks",
                      "linkage_restrictions", "use_rule", "population_covered", "geography",
                      "possible_denominator")


@unittest.skipUnless((LA / "data_provenance.csv").is_file(), "requiere data_provenance.csv")
class ProvenanceTextTest(unittest.TestCase):
    """La Tabla S14 traía 544 frases inglesas en 38 páginas del suplemento español porque su nota
    declaraba «se transcriben en inglés tal como constan». Ese texto lo redactó el estudio, no la fuente:
    ahora `labels.provenance_text` lo declara en los dos idiomas y aquí se exige que no falte ninguno."""

    @classmethod
    def setUpClass(cls):
        import pandas as pd
        cls.dp = pd.read_csv(LA / "data_provenance.csv", dtype=str, keep_default_na=False)
        path = CFG.TIDY / "provenance_manifest_checks.csv"
        cls.pm = pd.read_csv(path, dtype=str, keep_default_na=False) if path.is_file() else None

    def test_every_descriptive_field_reads_in_spanish(self):
        missing = []
        for column in PROVENANCE_COLUMNS:
            if column not in self.dp.columns:
                continue
            for value in sorted({v for v in self.dp[column] if str(v).strip()}):
                gloss = LB.provenance_text(value, "es")
                if LB.language_leak(gloss, "es"):
                    missing.append((column, gloss[:150]))
        self.assertEqual(missing, [], f"campos de procedencia sin glosa española: {missing[:6]}")

    def test_every_manifest_note_reads_in_spanish(self):
        if self.pm is None:
            self.skipTest("requiere outputs/tidy/provenance_manifest_checks.csv")
        missing = [n for n in sorted({v for v in self.pm.manifest_note if str(v).strip()})
                   if LB.language_leak(LB.provenance_text(n, "es"), "es")]
        self.assertEqual(missing, [], f"notas de manifiesto sin glosa española: {missing[:6]}")

    def test_the_english_form_is_the_canonical_one(self):
        """`provenance_text(v, 'en')` devuelve el valor tal cual: el CSV guarda la forma inglesa."""
        for column in PROVENANCE_COLUMNS:
            if column not in self.dp.columns:
                continue
            for value in {v for v in self.dp[column] if str(v).strip()}:
                self.assertEqual(LB.provenance_text(value, "en"), value.strip())

    def test_the_spanish_gloss_writes_thousands_with_a_full_stop(self):
        """«167,405 filas» dentro de una frase española es un separador inglés."""
        bad = []
        for column in PROVENANCE_COLUMNS:
            if column not in self.dp.columns:
                continue
            for value in {v for v in self.dp[column] if str(v).strip()}:
                gloss = LB.provenance_text(value, "es")
                if re.search(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?![\d.,])", gloss):
                    bad.append(gloss[:150])
        self.assertEqual(bad, [], f"miles con coma dentro del español: {bad[:5]}")


# ---------------------------------------------------------------------------
# 3c. Las categorías administrativas del episodio GRD (Tablas S54 y S109)
# ---------------------------------------------------------------------------
#: Variables cuyas categorías SON el rótulo que el maestro del GRD asigna a una institución, un convenio
#: o un pueblo originario: se transcriben literales en los dos idiomas y la nota de la tabla lo declara.
GRD_VERBATIM_VARIABLES = ("SERVICIO_SALUD", "ESPECIALIDAD_MEDICA", "PREVISION")
GRD_VERBATIM_VALUES = ("MAPUCHE", "AYMARA", "DIAGUITA", "QUECHUA", "KAWÉSQAR", "COLLA",
                       "YAGÁN (YÁMANA)", "RAPA NUI (PASCUENSE)", "LICAN ANTAI (ATACAMEÑO)")


@unittest.skipUnless((CFG.TIDY / "grd_episode_features.csv").is_file(),
                     "requiere outputs/tidy/grd_episode_features.csv")
class GrdEpisodeCategoryTest(unittest.TestCase):
    """Las Tablas S54 y S109 imprimían en español, dentro del documento en inglés, las categorías de
    TIPO_INGRESO, TIPO_ACTIVIDAD, TIPO_PROCEDENCIA, TIPOALTA, ETNIA y sexo —que están FUERA de la
    exención que su propia nota declara— y los 218 nombres de país de NACIONALIDAD."""

    @classmethod
    def setUpClass(cls):
        import pandas as pd
        cls.feat = pd.read_csv(CFG.TIDY / "grd_episode_features.csv", dtype=str, keep_default_na=False)

    def test_every_category_outside_the_exemption_reads_in_english(self):
        untranslated = []
        for variable, value in sorted({(a, b) for a, b in zip(self.feat.variable, self.feat.value)}):
            if variable in GRD_VERBATIM_VARIABLES or value in GRD_VERBATIM_VALUES:
                continue
            if not any(c.isalpha() for c in value):
                continue
            if value not in LB.TIDY_TEXT and value not in LB.GRD_SOURCE_CATEGORY and value not in LB.GRD_COUNTRY:
                untranslated.append((variable, value))
        self.assertEqual(untranslated, [],
                         f"categorías del episodio sin glosa inglesa declarada: {untranslated[:10]}")

    def test_the_spanish_document_keeps_the_form_of_the_source(self):
        changed = [v for v in sorted(set(self.feat.value))
                   if v in LB.GRD_SOURCE_CATEGORY or v in LB.GRD_COUNTRY
                   if LB.tidy_text(v, "es") != v]
        self.assertEqual(changed, [], f"el español no debe reescribir el valor de la fuente: {changed[:6]}")

    def test_the_data_states_are_glossed_even_inside_the_exempted_variables(self):
        """Cero, ausente y «no informado» son estados distintos del estudio: tienen que leerse."""
        for value in ("DESCONOCIDO", "NO APLICA", "NO IDENTIFICADA", "IGNORADO"):
            self.assertNotEqual(LB.tidy_text(value, "en"), value, value)


# ---------------------------------------------------------------------------
# 3d. El separador de miles de cada idioma
# ---------------------------------------------------------------------------
#: Números con separador de grupo que se escriben IGUAL en los dos idiomas porque no son cantidades.
NUMERIC_LITERALS = ("21.545",)          # el número de la Ley 21.545
#: (rótulo del ítem, módulo productor) de los sitios donde el número sigue con formato inglés dentro del
#: documento español. La lista está VACÍA: las siete cadenas de `pipeline/15b_spatial_correlation.py` que
#: escribían el número con `f"{n:,}"` en las dos ramas de idioma —leyendas de las Figuras S45 y S46 y notas
#: de las Tablas S92 y S93— pasan ahora por `num(n, 0, lang)`, de modo que la prueba las mira como a las
#: demás. Toda entrada nueva aquí es una excepción declarada, no un permiso permanente.
KNOWN_OPEN_NUMBERS: tuple[tuple[str, str], ...] = ()

GROUPED_NUMBER = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d{3})+(?![\d.,])")


def walk_aligned(blocks):
    """(rótulo, dónde, texto) de TODO el texto de un documento, en orden y sin deduplicar.

    Los cuatro documentos se construyen con la misma secuencia de bloques y las mismas tablas, de modo
    que el i-ésimo elemento del español y el del inglés son la MISMA celda."""
    n_tab = n_fig = 0
    for kind, payload in blocks:
        if kind in ("p", "small", "title", "subtitle", "h1", "h2", "h3"):
            yield kind, "text", str(payload)
        elif kind == "bullets":
            for i, item in enumerate(payload):
                yield kind, f"item{i}", str(item)
        elif kind == "panel":
            yield kind, "title", str(payload.get("title", ""))
            for i, (head, text) in enumerate(payload["items"]):
                yield kind, f"head{i}", str(head)
                yield kind, f"text{i}", str(text)
        elif kind == "table":
            n_tab += 1
            label = payload.get("label") or f"table {n_tab}"
            yield label, "title", str(payload.get("title", ""))
            yield label, "note", str(payload.get("note", ""))
            frame = payload["df"]
            for j, column in enumerate(frame.columns):
                yield label, f"header{j}", str(column)
            for j, column in enumerate(frame.columns):
                for i, value in enumerate(frame[column].astype(str)):
                    yield label, f"cell[{j},{i}]", value
        elif kind == "figure":
            n_fig += 1
            label = payload.get("label") or f"figure {n_fig}"
            yield label, "caption", str(payload.get("caption", ""))


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante e idioma")
class NumberFormatTest(unittest.TestCase):
    """Los dos idiomas imprimen el MISMO número, pero no la misma cadena: 25.618 en español y 25,618 en
    inglés. Si la misma celda trae el mismo literal con separador en los dos documentos, uno de los dos
    está escrito en el idioma equivocado (la revisión halló «25,618 episodios de los 25,620», «n =
    56,097 ingresos» y «29,974 personas en 2025» en el suplemento español)."""

    def test_a_grouped_number_is_never_identical_in_both_documents(self):
        import prose_en as E
        import prose_es as S
        known = {label for label, _ in KNOWN_OPEN_NUMBERS}
        found = []
        for variant in VARIANTS:
            english = list(walk_aligned(E.manuscript(variant, E.load_values(variant))))
            spanish = list(walk_aligned(S.manuscript(variant, S.load_values(variant))))
            self.assertEqual(len(english), len(spanish),
                             f"{variant}: los dos documentos no tienen la misma secuencia de bloques")
            for (_, where_en, text_en), (label, where_es, text_es) in zip(english, spanish):
                self.assertEqual(where_en, where_es)
                if label in known:
                    continue
                shared = (set(GROUPED_NUMBER.findall(text_en)) & set(GROUPED_NUMBER.findall(text_es))
                          - set(NUMERIC_LITERALS))
                for token in sorted(shared):
                    found.append((variant, label, where_es, token, text_es[:140]))
        self.assertEqual(found, [], f"{len(found)} número(s) con el separador del otro idioma: {found[:6]}")


# ---------------------------------------------------------------------------
# 4. El diccionario CIE-10
# ---------------------------------------------------------------------------
class Icd10DictionaryTest(unittest.TestCase):
    def test_every_category_has_both_languages_and_neither_leaks(self):
        self.assertGreater(len(LB.ICD10), 150)
        for code, gloss in LB.ICD10.items():
            self.assertEqual(set(gloss), {"es", "en"}, code)
            for lang in LANGS:
                self.assertTrue(gloss[lang].strip(), f"{code}/{lang} vacío")
                self.assertIsNone(LB.language_leak(gloss[lang], lang), f"{code}/{lang}: {gloss[lang]}")

    def test_j30_has_a_label(self):
        self.assertEqual(LB.icd_code_label("J30", "en"), "J30 — Vasomotor and allergic rhinitis")
        self.assertTrue(LB.icd_label("J30", "es"))

    def test_a_code_without_gloss_prints_alone(self):
        self.assertEqual(LB.icd_code_label("A02", "en"), "A02")
        self.assertEqual(LB.icd_code_label("A02", "es"), "A02")

    def test_the_repository_keeps_a_single_icd_dictionary(self):
        """Toda glosa española que usa el pipeline tiene aquí su par en inglés."""
        helpers = LA.parent / "scripts" / "report_helpers.py"
        if not helpers.is_file():
            self.skipTest("scripts/report_helpers.py no está presente")
        tree = ast.parse(helpers.read_text(encoding="utf-8"))
        spanish = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ICD_LABELS":
                spanish = ast.literal_eval(node.value)
        self.assertTrue(spanish, "no se pudo leer ICD_LABELS")
        missing = sorted(code for code in spanish if code not in LB.ICD10)
        self.assertEqual(missing, [], f"códigos sin glosa inglesa en labels.ICD10: {missing}")
        different = sorted(code for code, label in spanish.items() if LB.ICD10[code]["es"] != label)
        self.assertEqual(different, [], f"glosa española distinta de la del pipeline: {different}")

    def test_chapters_and_mental_blocks_are_bilingual(self):
        for start, end, gloss in LB.ICD10_CHAPTERS + LB.ICD10_MENTAL_BLOCKS:
            self.assertEqual(set(gloss), {"es", "en"}, f"{start}-{end}")
            for lang in LANGS:
                self.assertIsNone(LB.language_leak(gloss[lang], lang), f"{start}-{end}/{lang}")
        self.assertEqual(LB.icd_chapter_es_to("Factores que influyen en el estado de salud", "en"),
                         "Factors influencing health status and contact with health services")


# ---------------------------------------------------------------------------
# 5. Los literales que se dibujan dentro de una lámina
# ---------------------------------------------------------------------------
#: Módulos que dibujan texto en las láminas y tablas del material extendido.
FIGURE_MODULES = ("11_grd_episode_detail.py", "13_extra_figures_hospital.py", "14_extra_figures_rem.py",
                  "15_extra_figures_context.py", "15b_spatial_correlation.py")
#: Llamadas de matplotlib que escriben texto visible en la lámina.
TEXT_CALLS = {"set_xlabel", "set_ylabel", "set_title", "suptitle", "set_label", "annotate",
              "set_xticklabels", "set_yticklabels"}


def drawn_literals(path: Path) -> list[tuple[int, str]]:
    """Literales de prosa que se pasan directamente a una llamada de dibujo de texto."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in TEXT_CALLS:
            continue
        args = list(node.args) + [kw.value for kw in node.keywords if kw.arg in ("label", "title", "s", "text")]
        for arg in args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and len(arg.value.split()) >= 3:
                out.append((node.lineno, arg.value))
    return out


class FigureLiteralTest(unittest.TestCase):
    def test_no_prose_literal_is_drawn_on_a_figure(self):
        for name in FIGURE_MODULES:
            path = LA / "pipeline" / name
            if not path.is_file():
                continue
            found = drawn_literals(path)
            self.assertEqual(found, [], f"{name}: texto de lámina sin rótulo bilingüe: {found[:5]}")


if __name__ == "__main__":
    unittest.main()
