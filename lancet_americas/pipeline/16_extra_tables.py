#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""16_extra_tables.py — módulo 16: serie ampliada de tablas suplementarias (E60–E81).

Este módulo NO recalcula nada desde las bases fuente: lee exclusivamente las tablas tidy ya verificadas
(`outputs/tidy/*.csv`), los controles de reproducción (`outputs/controls/*_controls.csv`) y los registros de
títulos/leyendas ya escritos por los módulos anteriores, y produce un conjunto grande de tablas formateadas
por variante (`con_rett`, `sin_rett`) e idioma (`es`, `en`) en
`outputs/<variante>/<idioma>/extra/tables/<nombre>.csv` (+ `<nombre>_numeric.csv` + `titles.json`).

Numeración. Los módulos 11 y 12 ya escribieron `E1`–`E12` y `M1`–`M10` en esa misma carpeta. Los módulos 13,
14 y 15 todavía no han producido sus archivos, de modo que este módulo numera su propia serie desde **E60**,
como pide el encargo, y verifica en tiempo de ejecución que ninguno de los nombres E60–E81 esté ya ocupado
por otro módulo (si lo estuviera, se detiene y lo informa en los controles en vez de sobrescribir).

Tablas producidas (22 por variante e idioma):

  E60  serie anual completa GRD por variante, panel, modalidad y posición, con tasas e intervalos
  E61  GRD por hospital y año (los 72 hospitales) con tasas, intervalos y pertenencia al panel fijo
  E62  GRD por región de RESIDENCIA y año con tasas poblacionales INE
  E63  GRD por edad simple y sexo
  E64  lista completa de co-diagnósticos CIE-10 con al menos 20 episodios
  E65  distribución completa de las características administrativas del episodio
  E66  estadía por año, posición, modalidad y grupo etario
  E67  reingresos por era de identificador, año y horizonte
  E68  multiplicidad de episodios por identificador dentro de cada era
  E69  tabla REM completa código × año con totales, establecimientos, panel estable y era
  E70  A05 por edad, sexo y año
  E71  P2 y P6 por región y año (stock de diciembre), por era de definición
  E72  establecimientos reportantes por módulo REM y año
  E73  capas de denominador por año, región, edad y sexo
  E74  reglas de armonización FONASA, APS e ISAPRE por año
  E75  estimaciones de encuesta con todos los dominios, variables de diseño, DEFF y EER
  E76  educación: serie PIE completa (definiciones separadas)
  E77  educación: JUNAEB por año, nivel y sexo
  E78  tabla de modelos con todas las especificaciones
  E79  controles de reproducción por familia
  E80  diccionario de datos de todos los archivos tidy
  E81  inventario de todas las figuras, tablas y ecuaciones del proyecto, con el rótulo actual de cada pieza
       resuelto en el registro compartido (prose_en.MAIN_FIGURES/MAIN_TABLES, supplementary_material.
       FIGURE_ORDER/TABLE_ORDER, equations_lancet.NUMBER) y una columna que dice dónde se usa

Reglas no negociables respetadas y repetidas en las notas: los recuentos son reconocimiento administrativo,
nunca prevalencia ni incidencia; el resultado GRD es «episodios con F84 documentado» y F84 principal es una
serie aparte; las fuentes no se enlazan por persona (sin cascada ni cocientes entre fuentes no enlazadas);
la Ley 21.545 es contexto de política, no una intervención con efecto estimable; stocks y flujos nunca
comparten eje; lugar de atención y residencia nunca se mezclan sin nota explícita; el panel hospitalario es
65 fijo / 65-65-65-65-68-72 observado; las personas se cuentan solo dentro del año; las eras de definición
REM no se unen; cero, ausente y «no reportado» son estados distintos; las celdas con menos de cinco eventos
se suprimen en las tablas territoriales; los dominios de encuesta con menos de 30 casos o EER > 30 % se
marcan y no se presentan como confiables. Toda VENTANA DE AÑOS que el lector ve impresa lleva raya
(«2019–2024»), también dentro de una frase; conservan el guion ASCII las claves de máquina —identificador
de modelo (E78), familia de control (E79), rutas, nombres de archivo y URL—: ver `yspan_prose`.

Uso:
    python3 lancet_americas/pipeline/16_extra_tables.py
    python3 lancet_americas/pipeline/16_extra_tables.py --variants con_rett --langs en
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # lancet_americas/pipeline
LA = HERE.parent                                # lancet_americas
REPO = LA.parent
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import config as CFG  # noqa: E402
import common as C  # noqa: E402
import controls_registry as CR  # noqa: E402  (ámbitos con nombre de los controles: una sola fuente por total)
import labels as LB  # noqa: E402
from epi_helpers import REGION_NAMES, REGION_ORDER, AGE_GROUPS, crude_rate  # noqa: E402

MODULE = "16_extra_tables"
SCRIPT = "lancet_americas/pipeline/16_extra_tables.py"
CONTROLS_DIR = CFG.OUT / "controls"
CONTROLS_DIR.mkdir(parents=True, exist_ok=True)
BASE_NUMBER = 60          # los módulos 13–15 aún no han escrito tablas; se numera desde E60
# Nombres canónicos de este módulo, en orden. Se usan para detectar colisiones de numeración con otros
# módulos y para comprobar al final que se escribió exactamente esta lista.
TABLE_NAMES = (
    f"E{BASE_NUMBER + 0}_grd_annual_full", f"E{BASE_NUMBER + 1}_grd_hospital_year_full",
    f"E{BASE_NUMBER + 2}_grd_region_population_rates", f"E{BASE_NUMBER + 3}_grd_age_single_sex_full",
    f"E{BASE_NUMBER + 4}_grd_codiagnoses_full", f"E{BASE_NUMBER + 5}_grd_episode_features_full",
    f"E{BASE_NUMBER + 6}_grd_length_of_stay_full", f"E{BASE_NUMBER + 7}_grd_readmission_full",
    f"E{BASE_NUMBER + 8}_grd_multiplicity_full", f"E{BASE_NUMBER + 9}_rem_code_year_full",
    f"E{BASE_NUMBER + 10}_rem_a05_age_sex_full", f"E{BASE_NUMBER + 11}_rem_p2_p6_region_year",
    f"E{BASE_NUMBER + 12}_rem_establishments_by_module", f"E{BASE_NUMBER + 13}_denominator_layers_full",
    f"E{BASE_NUMBER + 14}_coverage_harmonisation_rules", f"E{BASE_NUMBER + 15}_survey_estimates_full",
    f"E{BASE_NUMBER + 16}_education_pie_full", f"E{BASE_NUMBER + 17}_education_junaeb_full",
    f"E{BASE_NUMBER + 18}_models_all_specifications", f"E{BASE_NUMBER + 19}_reproduction_controls_by_family",
    f"E{BASE_NUMBER + 20}_tidy_data_dictionary", f"E{BASE_NUMBER + 21}_project_asset_inventory",
)
COMPARISON = "all_episodes"
STRICT_GRD = "strict_autism_f840"
T0 = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{MODULE}] [{time.perf_counter() - T0:7.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Formato bilingüe (mismas convenciones que los módulos 11 y 12)
# ---------------------------------------------------------------------------
NE = {"es": "n/e", "en": "n/e"}
#: Rótulos del esquema de las capas de cobertura (E74). Los escribe este estudio para nombrar la
#: columna de la fuente que va a continuación, de modo que se leen en el idioma del documento; el
#: nombre de la columna (CUENTA_BENEFICIARIOS, TRAMO_FONASA, REGIÓN…) se conserva literal.
SCH = {
    "count": {"es": "conteo", "en": "count"},
    "tramo": {"es": "tramo", "en": "bracket"},
    "tramo_missing": {"es": "tramo ausente", "en": "bracket missing"},
    "region": {"es": "región", "en": "region"},
    "age": {"es": "edad", "en": "age"},
    "centres": {"es": "centros", "en": "centres"},
    "panel": {"es": "panel", "en": "panel"},
    "cotizantes": {"es": "cotizantes", "en": "contributors"},
    "cargas": {"es": "cargas", "en": "dependants"},
    "nonatos": {"es": "nonatos/sin clasificar", "en": "unborn/unclassified"},
}
NR = {"es": "no reportado", "en": "not reported"}
SUP = {"es": "< 5", "en": "< 5"}
OUT_ERA = {"es": "código no vigente", "en": "code not in force"}


#: Raya de INTERVALO (U+2013 EN DASH). El signo negativo lo escribe `format` con el guion ASCII, que a 8 pt
#: mide 2,9 pt frente a los 4,1 pt de la raya: pegados no se distinguen, y la columna «CPA % (IC 95 %)» de
#: la Tabla E78 se leía «-2,2 (-16,8–15,1)» —tres trazos casi iguales, ninguno separable del otro—. Es el
#: choque que la tarea F3.3 corrigió en el módulo 15b y que aquí seguía en pie. La cura NO es un signo
#: nuevo sino el separador que el estudio ya usa en sus tablas de modelos: ver `ci()` y `build_E78`.
EN_DASH = "\u2013"


def num(x, dec=0, lang="es"):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return NE[lang]
    try:
        if pd.isna(x):
            return NE[lang]
    except (TypeError, ValueError):
        pass
    return C.fmt_number(float(x), dec, lang)


def pct(x, lang="es", dec=1):
    if x is None or pd.isna(x):
        return NE[lang]
    return C.fmt_number(float(x), dec, lang) + (" %" if lang == "es" else "%")


def n_pct(n, p, lang="es"):
    return f"{num(n, 0, lang)} ({pct(p, lang)})"


def ci(lo, hi, dec=1, lang="es"):
    """Intervalo con RAYA, salvo que algún extremo sea negativo: entonces manda «a»/«to».

    La raya sólo se puede usar cuando ningún extremo lleva signo. Con un límite negativo, «-16,8–15,1»
    pone el guion del signo contra la raya del rango y el lector no ve dónde acaba un número y empieza el
    otro; ahí se escribe con el separador de palabra de `common.fmt_ci`, que es además el que usan las
    tablas de modelos del estudio. Hoy ninguna tabla de este módulo distinta de E78 imprime un extremo
    negativo (medidas las 22 tablas × 2 variantes × 2 idiomas: cero), de modo que la rama sólo existe
    para que el defecto no pueda volver en silencio si los datos cambian de signo.
    """
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi):
        return NE[lang]
    if float(lo) < 0 or float(hi) < 0:
        return C.fmt_ci(float(lo), float(hi), dec, lang)
    return f"{num(lo, dec, lang)}{EN_DASH}{num(hi, dec, lang)}"


def yr(value, lang="es"):
    """Un año se escribe sin separador de miles en ningún idioma."""
    if value is None or pd.isna(value):
        return NE[lang]
    return str(int(value))


#: Una VENTANA DE AÑOS impresa se escribe con RAYA, como todo rango del estudio: «2019–2024». Los archivos
#: tidy del módulo 06 y de los controles GRD la traen con guion ASCII («2019-2024») y este módulo la
#: imprimía tal cual, de modo que en una misma fila de la Tabla E78 convivían «2019-2024» en la columna
#: Años y «2020–2021 disruption indicator» en la de covariables.
#:
#: La conversión es UNA para todo el corpus y vive en `common.yspan`: sólo el guion que separa dos años de
#: CUATRO cifras, con la centinela `(?<!\d)`/`(?!\d)` a los lados. Este módulo tenía hasta esta ronda su
#: propia copia, más laxa —`(?<=\d)\s*-\s*(?=\d{4}\b)`—, que también habría convertido el guion de un
#: identificador como «F84-2019»; era la deuda G5.9 del registro de decisiones y aquí queda saldada. Se
#: comprobó antes de unificar que ninguna tabla tidy del estudio escribe la ventana con espacios
#: («2019 - 2024»: cero coincidencias en `outputs/tidy/*.csv`), que es lo único que la copia laxa sabía
#: hacer y la de `common` no.
def yspan(value, lang="es"):
    """Ventana de años como rótulo impreso: «2019-2024» → «2019–2024». Respeta la centinela «n/e»."""
    s = txt(value, lang)
    return s if s == NE[lang] else C.yspan(s)


# ---------------------------------------------------------------------------
# La misma ventana, pero DENTRO DE UNA FRASE
# ---------------------------------------------------------------------------
#: `yspan` sirve donde la ventana ES la celda («Años», «Era de definición»). La lectura de contenido
#: encontró la otra mitad del defecto: la ventana escrita dentro de una NOTA o de una regla —«… (+ nonatos
#: in 2019-2020)», «ENCAVI 2023-2024»— seguía con guion ASCII, y en la misma línea impresa convivía con el
#: «29,7–41,9» de un intervalo de confianza: dos trazos distintos para el mismo tipo de rango.
#:
#: `yspan_prose` aplica `common.yspan` PALABRA A PALABRA y salta ENTERA la palabra que lleve una marca de
#: MÁQUINA —«:» «_» «=» «|» «[» «]» «%» «\», una extensión de archivo, o «/» acompañado de letras—, porque
#: ahí la ventana no es un rótulo sino parte de una clave que alguien vuelve a leer o a cruzar. Con esa
#: sola regla, sin una lista de columnas que se quede vieja, quedan literales:
#:   * los identificadores de modelo de la Tabla E78 — `grd_rate:con_rett:observed:all:any:none:2019-2024`;
#:   * las claves de familia de control de la Tabla E79 — `EF6_readmission_le_episodes[con_rett|2019-2020]`,
#:     que se cruzan carácter a carácter con `outputs/controls/*_controls.csv`;
#:   * los nombres de archivo y las rutas — `GRD/metadata/SOURCES_MANIFEST.md`,
#:     `ine_estimaciones-y-proyecciones-2002-2035_base-2017_comunas….csv`;
#:   * las URL — `source_url=https://…-1992-2070_base-2024_base-de-datos.xlsx?sfvrsn=…`.
#: Y sí se convierte lo que el lector lee como texto, incluido «2019-2024/25 series»: la barra sin letras
#: no es una ruta. Es idempotente, no toca las tablas `_numeric` y no ve las bandas de edad («0-4»,
#: «16-30 meses»), que no son dos años de cuatro cifras.
#: FASE 4J, TAREA J2. Este módulo tenía aquí su propia copia de la regla, y sólo sabía convertir la VENTANA
#: DE AÑOS: la banda de edad («0-4»), el tramo («6-7») y el decil salían con guion en las mismas tablas en
#: las que el intervalo de confianza salía con raya —1.792 celdas sólo en la Tabla S114—. La regla es ahora
#: UNA para todo el corpus y vive en `common` (`C.range_dash`), que trata la ventana de años como un caso
#: más del intervalo numérico y conserva el guion de la clave de máquina, la fecha, el código con prefijo
#: alfabético y la cadena de tres o más números. Aquí quedan los tres nombres con los que el módulo la
#: llamaba, delegando, para que el título, la nota y el marco impreso sigan pasando por el mismo sitio.
machine_token = C.is_machine_token
yspan_prose = C.range_dash


def yspan_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """La regla del intervalo sobre encabezados y celdas del marco IMPRESO (nunca el `_numeric`).

    Devuelve el marco y dos recuentos: intervalos convertidos a raya y guiones entre cifras conservados a
    propósito (clave de máquina, fecha, código o cadena), que es exactamente lo que se quiere conservar."""
    return C.range_dash_frame(df)


#: Recuento de la conversión por variante e idioma, para los controles del módulo.
YSPAN_COUNTS: dict[str, dict[str, int]] = {}


def txt(value, lang="es"):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return NE[lang]
    try:
        if pd.isna(value):
            return NE[lang]
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    return s if s else NE[lang]


def stxt(value, lang="es"):
    """Texto libre que viene de un archivo tidy, escrito en el idioma del documento.

    Los módulos productores dejan la unidad, la geografía, la regla de armonización, el dominio de
    encuesta, la definición de la serie educativa o la nota de diseño en UN idioma. `labels.tidy_text`
    devuelve la glosa del idioma pedido; si el valor no está declarado allí devuelve el valor tal cual y
    `tests/test_language_purity.py` lo señala como fuga, que es la señal para declararlo."""
    raw = txt(value, lang)
    return raw if raw == NE[lang] else LB.tidy_text(raw, lang)


def merge_json(path: Path, new: dict) -> None:
    current: dict = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = {}
    if not isinstance(current, dict):
        current = {}
    current.update(new)
    C.atomic_write_json(current, path)


def extra_dir(variant: str, lang: str) -> Path:
    p = CFG.OUT / variant / lang / "extra" / "tables"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_pair(tdir: Path, name: str, formatted: pd.DataFrame, numeric: pd.DataFrame) -> list[str]:
    return [str(C.atomic_write_csv(formatted, tdir / f"{name}.csv", encoding="utf-8-sig")),
            str(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv"))]


# ---------------------------------------------------------------------------
# Rótulos
# ---------------------------------------------------------------------------
L = {
    "year": {"es": "Año", "en": "Year"},
    "series": {"es": "Serie", "en": "Series"},
    "panel": {"es": "Panel", "en": "Panel"},
    "activity": {"es": "Modalidad", "en": "Activity"},
    "position": {"es": "Posición del código", "en": "Code position"},
    "hospital": {"es": "Hospital (código GRD — nombre)", "en": "Hospital (GRD code — name)"},
    "region": {"es": "Región de residencia declarada", "en": "Declared region of residence"},
    "age": {"es": "Edad (años cumplidos)", "en": "Age (completed years)"},
    "sex": {"es": "Sexo", "en": "Sex"},
    "block": {"es": "Bloque", "en": "Block"},
    "indicator": {"es": "Indicador", "en": "Indicator"},
    "code": {"es": "Código", "en": "Code"},
    "era": {"es": "Era de definición", "en": "Definition era"},
    "module": {"es": "Módulo REM", "en": "REM module"},
    "measure": {"es": "Medida", "en": "Measure"},
    "layer": {"es": "Capa de denominador", "en": "Denominator layer"},
    "dimension": {"es": "Dimensión", "en": "Dimension"},
    "category": {"es": "Categoría", "en": "Category"},
    "variable": {"es": "Variable", "en": "Variable"},
    "value": {"es": "Valor", "en": "Value"},
    "total_2019_2024": {"es": "Total 2019–2024", "en": "Total 2019–2024"},
    "fixed_panel": {"es": "Panel fijo de 65", "en": "Fixed panel of 65"},
    "yes": {"es": "Sí", "en": "Yes"},
    "no": {"es": "No", "en": "No"},
    "source": {"es": "Fuente", "en": "Source"},
    "file": {"es": "Archivo", "en": "File"},
    "rule": {"es": "Regla", "en": "Rule"},
    "note": {"es": "Nota", "en": "Note"},
    "unit": {"es": "Unidad", "en": "Unit"},
    "geography": {"es": "Geografía", "en": "Geography"},
    "script": {"es": "Script productor", "en": "Producing script"},
    "columns": {"es": "Columnas", "en": "Columns"},
    "rows": {"es": "Filas", "en": "Rows"},
    "kind": {"es": "Tipo", "en": "Kind"},
    "used_in": {"es": "Uso actual", "en": "Current use"},
    "title": {"es": "Título", "en": "Title"},
    "family": {"es": "Familia de control", "en": "Control family"},
    "status": {"es": "Estado", "en": "Status"},
    "model": {"es": "Modelo (identificador)", "en": "Model (identifier)"},
    "level": {"es": "Nivel", "en": "Level"},
    "domain": {"es": "Dominio", "en": "Domain"},
    "subgroup": {"es": "Subgrupo", "en": "Subgroup"},
    "establishments": {"es": "Establecimientos reportantes", "en": "Reporting establishments"},
    "horizon": {"es": "Horizonte", "en": "Horizon"},
    "episodes_per_id": {"es": "Episodios por identificador", "en": "Episodes per identifier"},
}
POSITION_LABEL = {"any": {"es": "Cualquier posición", "en": "Any position"},
                  "principal": {"es": "F84 principal", "en": "F84 principal"},
                  "secondary_only": {"es": "Solo secundario", "en": "Secondary only"},
                  "principal_and_secondary": {"es": "Principal y secundario", "en": "Principal and secondary"},
                  "all": {"es": "Todos los episodios GRD", "en": "All GRD episodes"}}
ACTIVITY_LABEL = {"all": {"es": "Todas las modalidades", "en": "All activities"},
                  "hospitalisation": {"es": "Hospitalización estricta", "en": "Strict hospitalisation"},
                  "cma": {"es": "Cirugía mayor ambulatoria", "en": "Major ambulatory surgery"},
                  "other": {"es": "Otras modalidades (solo 2019)", "en": "Other modalities (2019 only)"}}
#: Los seis tamaños anuales del panel observado son una ENUMERACIÓN, no un intervalo: unidos por guion
#: («65-65-65-65-68-72») el lector veía en la misma tabla dos oficios para el mismo trazo, y la regla de la
#: raya los deja fuera a propósito. Se escriben con la misma forma con que el corpus ya los escribe en la
#: nota de los modelos y en la de la propia E60: «65, 65, 65, 65, 68 y 72».
PANEL_LABEL = {"observed": {"es": "Panel anual observado (65, 65, 65, 65, 68 y 72)", "en": "Observed annual panel (65, 65, 65, 65, 68 and 72)"},
               "fixed65": {"es": "Panel fijo de 65 hospitales", "en": "Fixed panel of 65 hospitals"}}
SEX_LABEL = {"HOMBRE": {"es": "Hombres", "en": "Males"}, "MUJER": {"es": "Mujeres", "en": "Females"},
             "Hombres": {"es": "Hombres", "en": "Males"}, "Mujeres": {"es": "Mujeres", "en": "Females"},
             "unknown": {"es": "Sexo no informado", "en": "Sex not reported"},
             "SIN_INFORMACION": {"es": "Sexo no informado", "en": "Sex not reported"},
             "INDETERMINADO": {"es": "Sexo indeterminado", "en": "Sex indeterminate"},
             "TOTAL": {"es": "Total", "en": "Total"}, "all": {"es": "Ambos sexos", "en": "Both sexes"},
             "male": {"es": "Hombres", "en": "Males"}, "female": {"es": "Mujeres", "en": "Females"}}
FLOW_LABEL = {"entry": {"es": "Ingresos", "en": "Entries"}, "exit": {"es": "Egresos", "en": "Exits"}}
A05_CATEGORY = {
    "pdd_family": {"es": "Familia TGD de la variante (suma de códigos)", "en": "Variant PDD family (sum of codes)"},
    "autism": {"es": "Autismo (código único)", "en": "Autism (single code)"},
    "asperger": {"es": "Síndrome de Asperger", "en": "Asperger syndrome"},
    "rett": {"es": "Síndrome de Rett", "en": "Rett syndrome"},
    "disintegrative": {"es": "Trastorno desintegrativo infantil", "en": "Childhood disintegrative disorder"},
    "pdd_nos": {"es": "Otros TGD y TGD no especificado", "en": "Other and unspecified PDD"},
    "broad_pdd": {"es": "TGD amplio (era 2019–2020, serie separada)",
                  "en": "Broad PDD (2019–2020 era, separate series)"},
}
JUNAEB_LEVEL = {"parvularia": {"es": "Educación parvularia", "en": "Pre-school"},
                "basico1": {"es": "1.º básico", "en": "Grade 1"},
                "basico5": {"es": "5.º básico", "en": "Grade 5"},
                "medio1": {"es": "1.º medio", "en": "Year 9"}}


def sex_lbl(value, lang):
    return SEX_LABEL.get(str(value), {"es": str(value), "en": str(value)})[lang]


def region_label(cut, lang):
    if cut is None or pd.isna(cut):
        return {"es": "No enlazada a comuna INE", "en": "Not linked to an INE comuna"}[lang]
    return REGION_NAMES.get(int(cut), str(cut))


# ---------------------------------------------------------------------------
# Notas comunes (unidad, denominador, cobertura, era, N reportante, archivo fuente)
# ---------------------------------------------------------------------------
NOTE_GRD = {
    "es": ("Unidad: episodio GRD (no persona). Los recuentos son reconocimiento administrativo —episodios GRD con "
           "F84 documentado— y nunca prevalencia, incidencia ni «hospitalizaciones por autismo»; F84 en posición "
           "principal se presenta como serie separada. Cobertura: hospitales públicos con GRD; panel observado de 65, "
           f"65, 65, 65, 68 y 72 hospitales en 2019–2024 y panel fijo de 65 {C.fixed_panel_gloss('es', 'paren')}. Personas contadas "
           "solo dentro de cada año (el identificador cambia de formato entre 2020 y 2021). 2020–2021: disrupción del "
           "reporte por la pandemia. La Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con "
           "efecto estimable. Archivos fuente: GRD_PUBLICO_2019..2024.csv (FONASA/MINSAL), vía "
           "outputs/tidy/ (SHA-256 en data_provenance.csv)."),
    "en": ("Unit: GRD episode (not person). Counts are administrative recognition —GRD episodes with documented F84— "
           "and never prevalence, incidence or 'hospitalisations for autism'; F84 in the principal position is reported "
           "as a separate series. Coverage: public hospitals reporting GRD; observed panel of 65, 65, 65, 65, 68 and 72 "
           f"hospitals in 2019–2024 and fixed panel of 65 {C.fixed_panel_gloss('en', 'paren')}. Persons are counted only within each "
           "year (the identifier changes format between 2020 and 2021). 2020–2021: pandemic reporting disruption. Law "
           "21.545 (March 2023) is policy context, not an intervention with an estimable effect. Source files: "
           "GRD_PUBLICO_2019..2024.csv (FONASA/MINSAL), through outputs/tidy/ (SHA-256 in data_provenance.csv)."),
}
NOTE_REM = {
    "es": ("Unidad: prestación o persona bajo control según el indicador; los REM no se enlazan por persona con el GRD "
           "ni con ninguna otra fuente, de modo que no se calculan cocientes entre etapas ni trayectorias individuales. "
           "A03/A05/A27/A28 son flujos y P2/P6 son stocks semestrales: nunca se suman ni se grafican en un mismo eje. "
           "Las eras de definición se informan explícitamente y no se unen con una línea. Cero, celda vacía y "
           "establecimiento que no reporta son estados distintos. Toda celda informa el número de establecimientos "
           "reportantes. Archivos fuente: REM/SerieA/SerieA_2019..2025.csv y REM/SerieP/SerieP_2019..2025.csv (DEIS), "
           "vía outputs/tidy/rem_pathway_annual.csv y rem_establishment_year.csv."),
    "en": ("Unit: activity or person under control depending on the indicator; REM records are not person-linked to GRD "
           "or to any other source, so no between-stage ratios and no individual trajectories are computed. "
           "A03/A05/A27/A28 are flows and P2/P6 are semi-annual stocks: they are never summed nor plotted on one axis. "
           "Definition eras are stated explicitly and never joined by a line. Zero, empty cell and non-reporting "
           "establishment are distinct states. Every cell reports the number of reporting establishments. Source files: "
           "REM/SerieA/SerieA_2019..2025.csv and REM/SerieP/SerieP_2019..2025.csv (DEIS), through "
           "outputs/tidy/rem_pathway_annual.csv and rem_establishment_year.csv."),
}
NOTE_GEO = {
    "es": ("Nota de geografía: esta tabla usa la comuna de RESIDENCIA declarada en el GRD y la población INE de "
           "residencia; no se mezcla con el lugar de atención (hospital GRD, establecimiento REM). Las celdas con menos "
           "de cinco episodios se suprimen («< 5»)."),
    "en": ("Geography note: this table uses the comuna of RESIDENCE declared in GRD and the INE residence population; "
           "it is never mixed with place of care (GRD hospital, REM establishment). Cells with fewer than five episodes "
           "are suppressed ('< 5')."),
}


# ---------------------------------------------------------------------------
# Carga de insumos
# ---------------------------------------------------------------------------
class Inputs:
    """Carga perezosa de las tablas tidy y de los registros ya verificados."""

    def __init__(self):
        self._cache: dict[str, pd.DataFrame] = {}

    def tidy(self, name: str, **kw) -> pd.DataFrame:
        if name not in self._cache:
            t = time.perf_counter()
            self._cache[name] = C.read_tidy(name, **kw)
            log(f"  leído tidy/{name}.csv: {len(self._cache[name]):,} filas ({time.perf_counter() - t:.1f} s)")
        return self._cache[name]

    def controls(self) -> pd.DataFrame:
        if "_controls" not in self._cache:
            parts = []
            for path in sorted(CONTROLS_DIR.glob("*_controls.csv")):
                module = path.stem[: -len("_controls")]
                # se excluyen el resumen y los controles de este mismo módulo (se escriben después de las
                # tablas, de modo que incluirlos haría la tabla dependiente del orden de ejecución)
                if module in ("controls_summary", MODULE):
                    continue
                d = pd.read_csv(path, dtype=str)
                if "module" not in d.columns:
                    d.insert(0, "module", module)
                # Algunos módulos llaman «control» a la columna que el resto llama «name» (por ejemplo
                # 08b_figures_rem_controls.csv). Sin esta armonización esos controles quedan con name vacío y
                # groupby los descarta en silencio, subestimando el total de comprobaciones del proyecto.
                if "name" not in d.columns and "control" in d.columns:
                    d["name"] = d["control"]
                elif "name" in d.columns and "control" in d.columns:
                    d["name"] = d["name"].fillna(d["control"])
                d["control_file"] = path.name
                parts.append(d)
            self._cache["_controls"] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
            log(f"  leídos {len(parts)} archivos de controles: {len(self._cache['_controls']):,} filas")
        return self._cache["_controls"]


def model_labels() -> dict:
    """LBL de pipeline/06_models.py leído con `ast` (no se importa ni se modifica ese módulo)."""
    tree = ast.parse((HERE / "06_models.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "LBL":
            return ast.literal_eval(node.value)
    return {}


def model_notes() -> dict:
    """NOTES de pipeline/06_models.py leído con `ast`: la nota de cada modelo está declarada en los dos
    idiomas y se reconstruye desde `note_keys`, en vez de copiar la columna `note`, que 06_models escribe
    siempre en inglés."""
    tree = ast.parse((HERE / "06_models.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "NOTES":
            return ast.literal_eval(node.value)
    return {}


MLBL = model_labels()
MNOTES = model_notes()


_FLOAT_REPR = re.compile(r"-?\d+\.\d+")
_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
_MAP_DIAG = re.compile(r"MAP:\s*success\s*=\s*(True|False)\s*,\s*\|grad\|\s*=\s*([0-9.eE+-]+)\s*,\s*iterations\s*=\s*(\d+)")


def _sci(value: float, lang: str, dec: int = 2) -> str:
    """8.22e-06 → «8,22 × 10⁻⁶» en español y «8.22 × 10⁻⁶» en inglés (nunca un punto decimal en español)."""
    x = float(value)
    if x == 0:
        return num(0.0, dec, lang)
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / (10.0 ** exp)
    return f"{num(mant, dec, lang)} × 10{str(exp).translate(_SUPERSCRIPT)}"


def map_diagnostic(text: str, lang: str) -> str:
    """Glosa en el idioma del documento el diagnóstico del optimizador del intercepto aleatorio.

    `06_models.py` escribe en la columna `note` la cadena que devuelve statsmodels, «MAP: success=False,
    |grad|=8.22e-06, iterations=113»: un booleano inglés y un punto decimal inglés que se imprimían tal cual
    en la Tabla E21 española. El dato no cambia; cambia quién lo lee."""
    def one(m) -> str:
        ok = m.group(1) == "True"
        grad, nit = _sci(float(m.group(2)), lang), num(int(m.group(3)), 0, lang)
        if lang == "es":
            return (f"optimizador MAP: convergencia declarada = {'sí' if ok else 'no'}; "
                    f"|gradiente| = {grad}; iteraciones = {nit}")
        return (f"MAP optimiser: reported convergence = {'yes' if ok else 'no'}; "
                f"|gradient| = {grad}; iterations = {nit}")
    return _MAP_DIAG.sub(one, str(text))


def mnote(note_keys, raw_note, lang) -> str:
    """Nota del modelo en `lang`, reconstruida desde `note_keys`.

    El resto de la columna `note` que no proviene de una clave (el diagnóstico «MAP: success=…» del
    modelo de intercepto aleatorio) es texto de máquina: se glosa en el idioma del documento en vez de
    imprimirse tal cual (`map_diagnostic`)."""
    keys = [k for k in str(note_keys).split("|") if k in MNOTES]
    built = " ".join(MNOTES[k][lang] for k in keys)
    english = " ".join(MNOTES[k]["en"] for k in keys)
    raw = map_diagnostic(txt(raw_note, lang), lang)
    english_here = map_diagnostic(english, lang) if english else english
    extra = raw[len(english_here):].strip() if english_here and raw.startswith(english_here) else ""
    if not keys:
        return raw if raw != NE[lang] else NE[lang]
    return f"{built} {extra}".strip() if extra else built


def mlbl(key, lang):
    v = MLBL.get(str(key))
    if isinstance(v, dict):
        return v.get(lang, str(key))
    return str(key)


# ---------------------------------------------------------------------------
# Registro de una tabla
# ---------------------------------------------------------------------------
class Registry:
    def __init__(self, variant: str, lang: str):
        self.variant, self.lang = variant, lang
        self.dir = extra_dir(variant, lang)
        self.written: list[str] = []
        self.titles: dict = {}
        self.rows: list[dict] = []

    def add(self, name, formatted: pd.DataFrame, numeric: pd.DataFrame, title: str, note: str) -> None:
        formatted = formatted.fillna(NE[self.lang])
        # El intervalo numérico se retipografía AQUÍ, en el único punto por el que pasa todo lo que este
        # módulo IMPRIME —las 22 tablas, sus encabezados, su título y su nota—, y nunca sobre el marco
        # `_numeric`, que es la copia de máquina. La regla es `C.range_dash` (ver `yspan_frame`).
        formatted, conv, kept = yspan_frame(formatted)
        t_conv = C.count_hyphen_ranges(title) + C.count_hyphen_ranges(note)
        t_kept = C.count_kept_hyphens(title) + C.count_kept_hyphens(note)
        title, note = yspan_prose(title), yspan_prose(note)
        c = YSPAN_COUNTS.setdefault(f"{self.variant}|{self.lang}", {"converted": 0, "kept_machine": 0})
        c["converted"] += conv + t_conv
        c["kept_machine"] += kept + t_kept
        self.written.extend(write_pair(self.dir, name, formatted, numeric))
        self.titles[name] = {"title": title, "note": note}
        self.rows.append({"name": name, "rows_formatted": int(len(formatted)), "cols_formatted": int(formatted.shape[1]),
                          "rows_numeric": int(len(numeric))})

    def flush(self) -> None:
        merge_json(self.dir / "titles.json", self.titles)
        self.written.append(str(self.dir / "titles.json"))


# ===========================================================================
# E60 — serie anual GRD por variante, panel, modalidad y posición
# ===========================================================================
def build_E60(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    ys = I.tidy("grd_year_summary")
    keep = [variant, STRICT_GRD]
    sub = ys.loc[ys.variant.isin(keep)].copy()
    years = sorted(sub.year.unique())
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    series_label = {variant: vlabel,
                    STRICT_GRD: {"es": "Autismo estricto F84.0 (serie preespecificada)",
                                 "en": "Strict autism F84.0 (pre-specified series)"}[lang]}
    rows = []
    for v in keep:
        for panel in ("observed", "fixed65"):
            for activity in ("all", "hospitalisation", "cma", "other"):
                for position in ("any", "principal", "secondary_only", "principal_and_secondary"):
                    s = sub.loc[(sub.variant == v) & (sub.panel == panel) & (sub.activity == activity) &
                                (sub.position == position)]
                    if s.empty:
                        continue
                    r = {"__s": series_label[v], "__p": PANEL_LABEL[panel][lang],
                         "__a": ACTIVITY_LABEL[activity][lang], "__q": POSITION_LABEL[position][lang]}
                    for y in years:
                        c = s.loc[s.year == y]
                        if c.empty:
                            r[str(y)] = NE[lang]
                            continue
                        c = c.iloc[0]
                        r[str(y)] = (f"{num(c.n_episodes_f84, 0, lang)}; {num(c.rate_per_100k_episodes, 1, lang)} "
                                     f"({ci(c.rate_lo, c.rate_hi, 1, lang)})")
                    rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__s": L["series"][lang], "__p": L["panel"][lang],
                                           "__a": L["activity"][lang], "__q": L["position"][lang]})
    note = {"es": ("Celda: episodios con F84 documentado; tasa por 100.000 episodios GRD del mismo panel y modalidad "
                   "(IC 95 % exacto de Poisson). Denominador: todos los episodios GRD de la misma celda panel × "
                   "modalidad (n en la tabla numérica, columna n_episodes_total_same_panel_activity). La versión "
                   "numérica añade personas dentro del año, episodios sin identificador válido, profundidad "
                   "diagnóstica media y mediana y el número de hospitales reportantes de cada año. "),
            "en": ("Cell: episodes with documented F84; rate per 100,000 GRD episodes of the same panel and activity "
                   "(exact Poisson 95% CI). Denominator: all GRD episodes of the same panel × activity cell (n in the "
                   "numeric companion, column n_episodes_total_same_panel_activity). The numeric companion adds persons "
                   "within year, episodes without a valid identifier, mean and median coding depth and the number of "
                   "reporting hospitals of each year. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Serie anual completa de episodios GRD con F84 documentado por serie, panel, modalidad y posición del código, 2019–2024 — {vlabel}",
             "en": f"Complete annual series of GRD episodes with documented F84 by series, panel, activity and code position, 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER}_grd_annual_full", f, sub, title, note)
    return sub


# ===========================================================================
# E61 — GRD por hospital y año
# ===========================================================================
def build_E61(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    h = I.tidy("grd_hospital_year")
    sub = h.loc[h.variant == variant].copy()
    years = sorted(sub.year.unique())
    rates = crude_rate(sub.n_f84_any, sub.n_episodes_total, per=1e5)
    sub = pd.concat([sub.reset_index(drop=True), rates.reset_index(drop=True)], axis=1)
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    codes = (sub.groupby(["COD_HOSPITAL", "hospital_name"], observed=True)
             .agg(total=("n_f84_any", "sum"), fixed=("in_fixed_panel", "max")).reset_index()
             .sort_values(["fixed", "total"], ascending=[False, False]))
    rows = []
    for _, hh in codes.iterrows():
        r = {"__h": f"{hh.COD_HOSPITAL} — {txt(hh.hospital_name, lang)}",
             "__f": L["yes"][lang] if bool(hh.fixed) else L["no"][lang]}
        for y in years:
            c = sub.loc[(sub.COD_HOSPITAL == hh.COD_HOSPITAL) & (sub.year == y)]
            if c.empty:
                # el hospital no aparece en el archivo de ese año: «no reportado», distinto de cero
                r[str(y)] = NR[lang]
                continue
            c = c.iloc[0]
            r[str(y)] = (f"{num(c.n_f84_any, 0, lang)}; {num(c.rate, 1, lang)} ({ci(c.rate_lo, c.rate_hi, 1, lang)})")
        r[L["total_2019_2024"][lang]] = num(hh.total, 0, lang)
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__h": L["hospital"][lang], "__f": L["fixed_panel"][lang]})
    note = {"es": ("Celda: episodios con F84 documentado en cualquier posición; tasa por 100.000 episodios GRD del "
                   "mismo hospital y año (IC 95 % exacto de Poisson). Denominador: todos los episodios GRD del "
                   "hospital-año (n_episodes_total en la tabla numérica). «no reportado» significa que el hospital no "
                   "aparece en el archivo GRD de ese año, estado distinto de cero. El panel observado crece de 65 a 72 "
                   f"hospitales; la columna de panel fijo identifica los 65 {C.fixed_panel_gloss('es', 'clause')}. El hospital es el "
                   "LUGAR DE ATENCIÓN, nunca la residencia del paciente, y estas tasas no son comparaciones de calidad: "
                   "la profundidad de codificación (columna coding_depth_mean) difiere entre centros. La versión "
                   "numérica añade F84 principal, hospitalización estricta, CMA y personas dentro del año. "),
            "en": ("Cell: episodes with documented F84 in any position; rate per 100,000 GRD episodes of the same "
                   "hospital and year (exact Poisson 95% CI). Denominator: all GRD episodes of the hospital-year "
                   "(n_episodes_total in the numeric companion). 'not reported' means the hospital is absent from that "
                   "year's GRD file, a state distinct from zero. The observed panel grows from 65 to 72 hospitals; the "
                   f"fixed-panel column identifies the 65 {C.fixed_panel_gloss('en', 'clause')}. The hospital is the PLACE OF CARE, never "
                   "the patient's residence, and these rates are not quality comparisons: coding depth (column "
                   "coding_depth_mean) differs between centres. The numeric companion adds principal F84, strict "
                   "hospitalisation, major ambulatory surgery and persons within year. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Episodios GRD con F84 documentado por hospital y año, con tasas, intervalos y pertenencia al panel fijo (todos los hospitales observados), 2019–2024 — {vlabel}",
             "en": f"GRD episodes with documented F84 by hospital and year, with rates, intervals and fixed-panel membership (all observed hospitals), 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 1}_grd_hospital_year_full", f, sub, title, note)
    return sub


# ===========================================================================
# E62 — GRD por región de residencia y año, con tasas poblacionales
# ===========================================================================
def build_E62(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    terr = I.tidy("grd_territory")
    pop = I.tidy("ine_population_region_national_year_age_sex")
    sub = terr.loc[(terr.level == "region") & (terr.variant == variant) & (terr.position == "any") &
                   (terr.panel == "observed")].copy()
    years = sorted(sub.year.unique())
    popr = (pop.loc[(pop.level == "region") & (pop.sex == "TOTAL")]
            .groupby(["year", "cut_region"], observed=True).population.sum().reset_index())
    sub = sub.merge(popr, on=["year", "cut_region"], how="left")
    rates = crude_rate(sub.n_episodes, sub.population, per=1e5)
    sub = pd.concat([sub.reset_index(drop=True), rates.reset_index(drop=True)], axis=1)
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    order = [r for r in REGION_ORDER if r in set(sub.cut_region.dropna().astype(int))]
    rows = []
    for cut in order + [None]:
        s = sub.loc[sub.cut_region.isna()] if cut is None else sub.loc[sub.cut_region == cut]
        if s.empty:
            continue
        r = {"__r": region_label(cut, lang)}
        for y in years:
            c = s.loc[s.year == y]
            if c.empty:
                r[str(y)] = NE[lang]
                continue
            c = c.iloc[0]
            if bool(c.suppression_flag):
                r[str(y)] = SUP[lang]
                continue
            rate = (f"{num(c.rate, 1, lang)} ({ci(c.rate_lo, c.rate_hi, 1, lang)})"
                    if pd.notna(c.population) else NE[lang])
            r[str(y)] = f"{num(c.n_episodes, 0, lang)}; {rate}"
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__r": L["region"][lang]})
    note = {"es": ("Celda: episodios con F84 documentado en cualquier posición; tasa por 100.000 habitantes de la "
                   "región (IC 95 % exacto de Poisson). Denominador: proyección INE de población comunal agregada a "
                   "región, base Censo 2017, al 30 de junio de cada año. Numerador y denominador comparten la "
                   "definición de residencia. Las comunas del GRD que no se enlazan con el catálogo INE se informan en "
                   "la fila «no enlazada»; nunca se aplica emparejamiento aproximado silencioso. "),
            "en": ("Cell: episodes with documented F84 in any position; rate per 100,000 regional inhabitants (exact "
                   "Poisson 95% CI). Denominator: INE comuna population projection aggregated to region, 2017-census "
                   "base, at 30 June of each year. Numerator and denominator share the residence definition. GRD "
                   "comunas that do not link to the INE catalogue are reported in the 'not linked' row; silent fuzzy "
                   "matching is never applied. ")}[lang] + NOTE_GEO[lang] + " " + NOTE_GRD[lang]
    title = {"es": f"Episodios GRD con F84 documentado por región de residencia declarada y año, con tasas poblacionales INE, 2019–2024 — {vlabel}",
             "en": f"GRD episodes with documented F84 by declared region of residence and year, with INE population rates, 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 2}_grd_region_population_rates", f, sub, title, note)
    return sub


# ===========================================================================
# E63 — GRD por edad simple y sexo
# ===========================================================================
def build_E63(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    a = I.tidy("grd_age_single_year")
    sub = a.loc[(a.variant == variant) & (a.position == "any") & (a.panel == "observed")].copy()
    years = sorted(sub.year.unique())
    ages = sorted([x for x in sub.age_years.dropna().unique()])
    rows = []
    for age in ages:
        for sex in ("HOMBRE", "MUJER", "unknown"):
            s = sub.loc[(sub.age_years == age) & (sub.sex == sex)]
            if s.empty and sex == "unknown":
                continue
            r = {"__a": num(age, 0, lang), "__s": sex_lbl(sex, lang)}
            tot = 0
            for y in years:
                c = s.loc[s.year == y]
                v = int(c.n_episodes.iloc[0]) if len(c) else 0
                tot += v
                r[str(y)] = num(v, 0, lang)
            r[L["total_2019_2024"][lang]] = num(tot, 0, lang)
            rows.append(r)
    unknown_age = sub.loc[sub.age_years.isna()]
    if len(unknown_age):
        for sex in sorted(unknown_age.sex.unique()):
            s = unknown_age.loc[unknown_age.sex == sex]
            r = {"__a": {"es": "Edad no informada", "en": "Age not reported"}[lang], "__s": sex_lbl(sex, lang)}
            tot = 0
            for y in years:
                c = s.loc[s.year == y]
                v = int(c.n_episodes.iloc[0]) if len(c) else 0
                tot += v
                r[str(y)] = num(v, 0, lang)
            r[L["total_2019_2024"][lang]] = num(tot, 0, lang)
            rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__a": L["age"][lang], "__s": L["sex"][lang]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Celda: episodios con F84 documentado en cualquier posición, panel observado. Unidad: episodio, no "
                   "persona; un mismo paciente puede aportar varios episodios en un año. No se calculan tasas por edad "
                   "en esta tabla porque el denominador poblacional por edad simple no es comparable con el "
                   "denominador de episodios; las tasas poblacionales estandarizadas están en la tabla de modelos y en "
                   "models_population_rates.csv. Cero es cero observado; «edad no informada» es un estado distinto. "),
            "en": ("Cell: episodes with documented F84 in any position, observed panel. Unit: episode, not person; the "
                   "same patient may contribute several episodes within a year. No age-specific rates are given here "
                   "because a single-year population denominator is not comparable with the episode denominator; "
                   "standardised population rates are in the model table and in models_population_rates.csv. Zero is an "
                   "observed zero; 'age not reported' is a distinct state. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Episodios GRD con F84 documentado por edad simple (años cumplidos) y sexo, 2019–2024 — {vlabel}",
             "en": f"GRD episodes with documented F84 by single year of age and sex, 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 3}_grd_age_single_sex_full", f, sub, title, note)
    return sub


# ===========================================================================
# E64 — lista completa de co-diagnósticos con al menos 20 episodios
# ===========================================================================
MIN_CODIAG = 20


def build_E64(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    cod = I.tidy("grd_codiagnoses")
    sub = cod.loc[(cod.variant == variant) & (cod.position == "any") & (cod.panel == "observed") &
                  (cod.code_position == "any")].copy()
    years = sorted(sub.year.unique())
    totals = sub.groupby("code3", observed=True).n_episodes.sum().sort_values(ascending=False)
    keep = totals.loc[totals >= MIN_CODIAG]
    sub = sub.loc[sub.code3.isin(keep.index)]
    rows = []
    for code, tot in keep.items():
        rows.append({"__k": LB.icd_code_label(code, lang),
                     **{str(y): (lambda c: n_pct(c.n_episodes.iloc[0], c.pct_of_f84_episodes.iloc[0], lang)
                                 if len(c) else n_pct(0, 0.0, lang))(sub.loc[(sub.year == y) & (sub.code3 == code)])
                        for y in years},
                     L["total_2019_2024"][lang]: num(tot, 0, lang)})
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Categoría CIE-10 (3 caracteres)",
                                                   "en": "ICD-10 category (3 characters)"}[lang]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": (f"Lista completa de las categorías CIE-10 con al menos {MIN_CODIAG} episodios acumulados en "
                   f"2019–2024 ({len(keep)} categorías de {len(totals)} observadas). Celda: episodios con al menos un "
                   "código de la categoría (% de los episodios con F84 documentado de ese año). Denominador: episodios "
                   "F84 del año (columna n_f84_episodes_cell). Un episodio cuenta una vez por categoría; los propios "
                   "códigos F84 se excluyen. La profundidad diagnóstica media de todos los episodios pasó de 4,39 en "
                   "2019 a 5,78 en 2024: parte del aumento de co-diagnósticos refleja codificación, no morbilidad, y "
                   "esta tabla no permite inferir comorbilidad poblacional. "),
            "en": (f"Complete list of ICD-10 categories with at least {MIN_CODIAG} cumulative episodes in 2019–2024 "
                   f"({len(keep)} of {len(totals)} observed categories). Cell: episodes with at least one code of the "
                   "category (% of that year's episodes with documented F84). Denominator: F84 episodes of the year "
                   "(column n_f84_episodes_cell). An episode counts once per category; F84 codes themselves are "
                   "excluded. Mean coding depth of all episodes rose from 4.39 in 2019 to 5.78 in 2024: part of the "
                   "rise in co-diagnoses reflects coding, not morbidity, and this table does not support inferences "
                   "about population comorbidity. ")}[lang] + LB.ICD10_SOURCE[lang] + " " + NOTE_GRD[lang]
    title = {"es": f"Lista completa de co-diagnósticos CIE-10 con al menos {MIN_CODIAG} episodios en los episodios GRD con F84 documentado, 2019–2024 — {vlabel}",
             "en": f"Complete list of ICD-10 co-diagnoses with at least {MIN_CODIAG} episodes among GRD episodes with documented F84, 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 4}_grd_codiagnoses_full", f, sub, title, note)
    return sub


# ===========================================================================
# E65 — distribución completa de características del episodio
# ===========================================================================
def build_E65(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    feat = I.tidy("grd_episode_features")
    sub = feat.loc[(feat.panel == "observed") &
                   (((feat.variant == variant) & (feat.position == "any")) |
                    ((feat.variant == COMPARISON) & (feat.position == "all")))].copy()
    years = sorted(sub.year.unique())
    last = years[-1]
    mine = sub.loc[sub.variant == variant]
    comp = sub.loc[sub.variant == COMPARISON]
    comp_col = {"es": f"Todos los episodios GRD {last}", "en": f"All GRD episodes {last}"}[lang]
    rows = []
    for var in sorted(mine.variable.unique()):
        v = mine.loc[mine.variable == var]
        order = v.groupby("value", observed=True).n_episodes.sum().sort_values(ascending=False)
        for value in order.index:
            r = {"__v": var, "__c": stxt(value, lang)}
            for y in years:
                c = v.loc[(v.year == y) & (v.value == value)]
                r[str(y)] = n_pct(c.n_episodes.iloc[0], c.pct_within_cell.iloc[0], lang) if len(c) else n_pct(0, 0.0, lang)
            cv = comp.loc[(comp.variable == var) & (comp.year == last)]
            cc = cv.loc[cv.value == value]
            r[comp_col] = (n_pct(cc.n_episodes.iloc[0], cc.pct_within_cell.iloc[0], lang) if len(cc)
                           else (n_pct(0, 0.0, lang) if len(cv) else NE[lang]))
            rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__v": L["variable"][lang], "__c": L["category"][lang]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Distribución completa: todas las variables administrativas del episodio y todas sus categorías "
                   "observadas, sin recortes. Celda: episodios (% de la columna del año). Denominador: episodios con "
                   "F84 documentado del año (n_cell_total en la tabla numérica). Cualquier posición, panel observado. "
                   "Los valores vacíos aparecen como «no informado» y nunca como cero. Las variables terminadas en "
                   "«_grouped» son agrupaciones prespecificadas de la variable original, que también se presenta "
                   "completa. " + LB.GRD_CATEGORY_NOTE["es"] + " La columna de comparación usa "
                   "todos los episodios GRD del último año disponible; nunca se interpretan como diferencias "
                   "clínicas. "),
            "en": ("Complete distribution: every administrative episode variable and all its observed categories, with "
                   "no truncation. Cell: episodes (% of the year column). Denominator: episodes with documented F84 of "
                   "the year (n_cell_total in the numeric companion). Any position, observed panel. Empty values appear "
                   "as 'not reported' and never as zero. Variables ending in '_grouped' are pre-specified groupings of "
                   "the original variable, which is also shown in full. " + LB.GRD_CATEGORY_NOTE["en"] +
                   " The comparison column uses "
                   "all GRD episodes of the latest available year; differences are never interpreted as clinical. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Distribución completa de las características administrativas de los episodios GRD con F84 documentado, 2019–2024 — {vlabel}",
             "en": f"Complete distribution of administrative characteristics of GRD episodes with documented F84, 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 5}_grd_episode_features_full", f, sub, title, note)
    return sub


# ===========================================================================
# E66 — estadía por año, posición, modalidad y grupo etario
# ===========================================================================
def build_E66(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    los = I.tidy("grd_length_of_stay")
    losa = I.tidy("grd_los_age")
    years = sorted(los.year.unique())
    b1 = los.loc[((los.variant == variant) | (los.variant == COMPARISON)) & (los.panel == "observed")].copy()
    b2 = losa.loc[(losa.panel == "observed") & (losa.activity == "hospitalisation") &
                  (((losa.variant == variant) & (losa.position == "any")) |
                   ((losa.variant == COMPARISON) & (losa.position == "all")))].copy()
    blk = {"es": ("Posición × modalidad", "Grupo etario OMS (hospitalización, cualquier posición)"),
           "en": ("Position × activity", "WHO age group (hospitalisation, any position)")}[lang]

    def cell(c):
        if c.empty or not int(c.n_valid_dates.iloc[0]):
            return NE[lang]
        c = c.iloc[0]
        return (f"{num(c.n_valid_dates, 0, lang)}; {num(c.median_days, 0, lang)} "
                f"({num(c.q25_days, 0, lang)}–{num(c.q75_days, 0, lang)}); {num(c.mean_days, 1, lang)}")

    rows = []
    for position in ("any", "principal", "secondary_only", "all"):
        v = variant if position != "all" else COMPARISON
        for activity in ("all", "hospitalisation", "cma", "other"):
            s = b1.loc[(b1.variant == v) & (b1.position == position) & (b1.activity == activity)]
            if s.empty:
                continue
            r = {"__b": blk[0], "__k": f"{POSITION_LABEL[position][lang]} · {ACTIVITY_LABEL[activity][lang]}"}
            for y in years:
                r[str(y)] = cell(s.loc[s.year == y])
            rows.append(r)
    for who, lbl in ((variant, {"es": "F84 documentado", "en": "Documented F84"}[lang]),
                     (COMPARISON, POSITION_LABEL["all"][lang])):
        for ag in AGE_GROUPS + ["unknown"]:
            s = b2.loc[(b2.variant == who) & (b2.age_group == ag)]
            if s.empty:
                continue
            aglbl = ag if ag != "unknown" else {"es": "Edad no informada", "en": "Age not reported"}[lang]
            r = {"__b": blk[1], "__k": f"{lbl} · {aglbl}"}
            for y in years:
                r[str(y)] = cell(s.loc[s.year == y])
            rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__b": L["block"][lang], "__k": L["indicator"][lang]})
    numeric = pd.concat([b1.assign(table_block="position_activity"), b2.assign(table_block="age_group")],
                        ignore_index=True)
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Celda: n de episodios con fechas válidas; mediana (P25–P75); media, en días. Unidad: día de "
                   "estadía por episodio. Denominador: episodios de la celda con fechas de ingreso y alta analizables; "
                   "los episodios con fechas no analizables o con alta anterior al ingreso se excluyen, se informan en "
                   "n_invalid_dates de la tabla numérica y nunca se imputan. La cirugía mayor ambulatoria tiene por "
                   "definición estadías de cero o un día y no es comparable con la hospitalización estricta. "),
            "en": ("Cell: n episodes with valid dates; median (P25–P75); mean, in days. Unit: day of stay per episode. "
                   "Denominator: episodes of the cell with parsable admission and discharge dates; episodes with "
                   "unparsable dates or discharge before admission are excluded, reported in n_invalid_dates of the "
                   "numeric companion and never imputed. Major ambulatory surgery has by definition stays of zero or "
                   "one day and is not comparable with strict hospitalisation. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Estadía hospitalaria por año, posición del código, modalidad y grupo etario quinquenal (OMS), 2019–2024 — {vlabel}",
             "en": f"Length of stay by year, code position, activity and five-year WHO age group, 2019–2024 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 6}_grd_length_of_stay_full", f, numeric, title, note)
    return numeric


# ===========================================================================
# E67 — reingresos
# ===========================================================================
def build_E67(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    try:
        rd = I.tidy("grd_readmission")
    except FileNotFoundError:
        rd = pd.DataFrame()
    sub = rd.loc[(rd.variant == variant) & (rd.position == "any") & (rd.panel == "observed")].copy() if len(rd) else rd
    cols = {"era": L["era"][lang], "year": L["year"][lang], "horizon": L["horizon"][lang],
            "disch": {"es": "Altas elegibles", "en": "Eligible discharges"}[lang],
            "any": {"es": "Reingreso por cualquier causa, n (%, IC 95 %)", "en": "All-cause readmission, n (%, 95% CI)"}[lang],
            "f84": {"es": "Reingreso con F84 documentado, n (%, IC 95 %)", "en": "Readmission with documented F84, n (%, 95% CI)"}[lang],
            "ovl": {"es": "Ingreso siguiente solapado", "en": "Overlapping next admission"}[lang]}
    rows = []
    for _, c in sub.sort_values(["era", "year", "horizon_days"]).iterrows():
        rows.append({cols["era"]: yspan(c.era, lang), cols["year"]: yr(c.year, lang),
                     cols["horizon"]: f"{num(c.horizon_days, 0, lang)} " + ("días" if lang == "es" else "days"),
                     cols["disch"]: f"{num(c.n_eligible, 0, lang)} / {num(c.n_discharges, 0, lang)}",
                     cols["any"]: f"{num(c.n_readmitted_any_cause, 0, lang)} ({pct(c.pct_any_cause, lang)}, "
                                  f"{ci(c.pct_any_cause_lo, c.pct_any_cause_hi, 1, lang)})",
                     cols["f84"]: f"{num(c.n_readmitted_f84, 0, lang)} ({pct(c.pct_f84, lang)}, "
                                  f"{ci(c.pct_f84_lo, c.pct_f84_hi, 1, lang)})",
                     cols["ovl"]: num(c.n_with_overlapping_next_admission, 0, lang)})
    f = pd.DataFrame(rows) if rows else pd.DataFrame({cols["era"]: [NE[lang]]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Cobertura de esta tabla: F84 en CUALQUIER posición (principal o secundaria) y panel anual "
                   "observado; el panel fijo de 65 y la serie de F84 principal no se muestran aquí y están en la "
                   "tabla numérica. Unidad: alta hospitalaria con F84 documentado. Denominador: altas elegibles, es decir, con "
                   "identificador válido y con horizonte de seguimiento completo dentro de la MISMA era de "
                   "identificador. El identificador cambia de formato entre 2020 y 2021 y no hay solapamiento: los "
                   "reingresos NUNCA se siguen a través de las eras y no existe una serie continua 2019–2024. IC 95 % "
                   "de Wilson. Un reingreso con F84 documentado no es un reingreso «por autismo». "),
            "en": ("Coverage of this table: F84 in ANY position (principal or secondary) and the observed annual "
                  "panel; the fixed panel of 65 and the F84-principal series are not shown here and are in the "
                  "numeric companion. Unit: hospital discharge with documented F84. Denominator: eligible discharges, that is, with a "
                   "valid identifier and a complete follow-up horizon within the SAME identifier era. The identifier "
                   "changes format between 2020 and 2021 with no overlap: readmissions are NEVER followed across eras "
                   "and no continuous 2019–2024 series exists. Wilson 95% CI. A readmission with documented F84 is not "
                   "a readmission 'for autism'. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Reingresos hospitalarios tras un alta GRD con F84 documentado, por era de identificador, año y horizonte — {vlabel}",
             "en": f"Hospital readmissions after a GRD discharge with documented F84, by identifier era, year and horizon — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 7}_grd_readmission_full", f, sub, title, note)
    return sub


# ===========================================================================
# E68 — multiplicidad
# ===========================================================================
def build_E68(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    mu = I.tidy("grd_multiplicity")
    sub = mu.loc[(mu.variant == variant) & (mu.position == "any") & (mu.panel == "observed")].copy()
    cols = {"era": L["era"][lang], "k": L["episodes_per_id"][lang],
            "p": {"es": "Personas, n (%)", "en": "Persons, n (%)"}[lang],
            "e": {"es": "Episodios, n (%)", "en": "Episodes, n (%)"}[lang],
            "noid": {"es": "Episodios sin identificador válido", "en": "Episodes without a valid identifier"}[lang]}
    rows = []
    for _, c in sub.sort_values(["era", "episodes_per_identifier"]).iterrows():
        rows.append({cols["era"]: yspan(c.era, lang), cols["k"]: txt(c.episodes_per_identifier, lang),
                     cols["p"]: n_pct(c.n_persons, c.pct_persons, lang),
                     cols["e"]: n_pct(c.n_episodes, c.pct_episodes, lang),
                     cols["noid"]: num(c.n_episodes_without_valid_identifier, 0, lang)})
    f = pd.DataFrame(rows) if rows else pd.DataFrame({cols["era"]: [NE[lang]]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Cobertura de esta tabla: F84 en CUALQUIER posición (principal o secundaria) y panel anual "
                   "observado; el panel fijo de 65 y la serie de F84 principal no se muestran aquí. "
                   "Unidad: identificador dentro de una era (2019–2020 y 2021–2024), nunca una persona seguida a lo "
                   "largo de todo el período: el identificador cambia de formato entre 2020 y 2021 y no hay "
                   "solapamiento, de modo que las personas únicas solo se informan dentro de cada año o era validada. "
                   "Denominador: personas con identificador válido de la era (n_persons_total) y episodios de la era "
                   "(n_episodes_total). Los episodios sin identificador válido se informan aparte y no se imputan. "),
            "en": ("Coverage of this table: F84 in ANY position (principal or secondary) and the observed annual "
                  "panel; the fixed panel of 65 and the F84-principal series are not shown here. "
                  "Unit: identifier within an era (2019–2020 and 2021–2024), never a person followed across the whole "
                   "period: the identifier changes format between 2020 and 2021 with no overlap, so unique persons are "
                   "reported only within each year or validated era. Denominator: persons with a valid identifier in "
                   "the era (n_persons_total) and episodes of the era (n_episodes_total). Episodes without a valid "
                   "identifier are reported separately and never imputed. ")}[lang] + NOTE_GRD[lang]
    title = {"es": f"Multiplicidad: episodios GRD con F84 documentado por identificador, dentro de cada era de identificador — {vlabel}",
             "en": f"Multiplicity: GRD episodes with documented F84 per identifier, within each identifier era — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 8}_grd_multiplicity_full", f, sub, title, note)
    return sub


# ===========================================================================
# E69 — tabla REM completa código × año
# ===========================================================================
REM_VARIANT_KEEP = ("single_code", "strict_autism", "broad_pre2021")


def build_E69(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    ra = I.tidy("rem_pathway_annual")
    sub = ra.loc[ra.variant.isin(set(REM_VARIANT_KEEP) | {variant})].copy()
    years = sorted(sub.year.unique())
    rows = []
    key = ["series", "module", "code", "variant", "indicator", "era", "domain", "measure"]
    for k, g in sub.groupby(key, observed=True, sort=False):
        series, module, code, var, indicator, era, domain, measure = k
        r = {"__m": f"{series}-{module}", "__c": txt(code, lang), "__i": LB.rem_indicator(indicator, lang),
             "__e": txt(era, lang),
             "__d": {"annual_sum": {"es": "Flujo: suma anual", "en": "Flow: annual sum"},
                     "december_stock": {"es": "Stock: diciembre", "en": "Stock: December"},
                     "june_stock": {"es": "Stock: junio (sensibilidad)", "en": "Stock: June (sensitivity)"}}
             .get(str(measure), {"es": str(measure), "en": str(measure)})[lang]}
        e0, e1 = g.era_start.min(), g.era_end.max()
        for y in years:
            c = g.loc[g.year == y]
            if c.empty:
                # el código no está vigente en ese año (fuera de su era) o no hay filas: estados distintos
                r[str(y)] = (OUT_ERA[lang] if pd.notna(e0) and pd.notna(e1) and not (e0 <= y <= e1)
                             else NR[lang])
                continue
            c = c.iloc[0]
            if pd.isna(c.total):
                r[str(y)] = NR[lang]
                continue
            r[str(y)] = (f"{num(c.total, 0, lang)}; {num(c.n_reporting_establishments, 0, lang)}; "
                         f"{num(c.stable_panel_total, 0, lang)}")
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__m": L["module"][lang], "__c": L["code"][lang],
                                           "__i": L["indicator"][lang], "__e": L["era"][lang],
                                           "__d": L["measure"][lang]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Celda: total del año; establecimientos reportantes; total del panel estable de establecimientos. "
                   "Unidad: la que declara cada indicador (prestaciones, ingresos, egresos o personas bajo control). "
                   "Denominador: ninguno; son recuentos absolutos y no se dividen por poblaciones no compatibles. "
                   "«no reportado» significa que el código no existe en el diccionario de ese año o que no hay filas: "
                   "es distinto de cero. Cada fila indica su era de definición; filas de eras distintas NUNCA forman "
                   "una serie continua. Las filas de familia (variante, autismo estricto, TGD amplio 2019–2020) suman "
                   "los códigos indicados en config.py y no deben sumarse entre sí. "),
            "en": ("Cell: year total; reporting establishments; stable-establishment-panel total. Unit: as declared by "
                   "each indicator (activities, entries, exits or persons under control). Denominator: none; these are "
                   "absolute counts and are not divided by non-compatible populations. 'not reported' means the code "
                   "does not exist in that year's dictionary or that no rows exist: it is distinct from zero. Each row "
                   "states its definition era; rows from different eras NEVER form a continuous series. Family rows "
                   "(variant, strict autism, broad PDD 2019–2020) sum the codes listed in config.py and must not be "
                   "added to one another. ")}[lang] + NOTE_REM[lang]
    title = {"es": f"Tabla REM completa: código × año con totales, establecimientos reportantes, total del panel estable y era de definición, 2019–2025 — {vlabel}",
             "en": f"Complete REM table: code × year with totals, reporting establishments, stable-panel total and definition era, 2019–2025 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 9}_rem_code_year_full", f, sub, title, note)
    return sub


# ===========================================================================
# E70 — A05 por edad, sexo y año
# ===========================================================================
def build_E70(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    a = I.tidy("rem_a05_age_sex_annual")
    sub = a.loc[a.variant.isin({variant, "single_code"})].copy()
    years = sorted(sub.year.unique())
    rows = []
    for (flow, category, code, sex), g in sub.groupby(["flow", "category", "code", "sex"], observed=True, sort=False):
        for ag in [x for x in sub.age_group.unique() if x != "total"] + ["total"]:
            s = g.loc[g.age_group == ag]
            if s.empty:
                continue
            r = {"__f": FLOW_LABEL.get(str(flow), {"es": str(flow), "en": str(flow)})[lang],
                 "__c": A05_CATEGORY.get(str(category), {"es": str(category), "en": str(category)})[lang],
                 "__k": txt(code, lang), "__s": sex_lbl(sex, lang),
                 "__a": ag if ag != "total" else {"es": "Total", "en": "Total"}[lang]}
            for y in years:
                c = s.loc[s.year == y]
                if c.empty:
                    r[str(y)] = NE[lang]
                    continue
                c = c.iloc[0]
                if pd.isna(c["count"]):
                    r[str(y)] = NR[lang]
                    continue
                r[str(y)] = f"{num(c['count'], 0, lang)} ({num(c.n_reporting_establishments, 0, lang)})"
            rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__f": {"es": "Flujo", "en": "Flow"}[lang],
                                           "__c": L["category"][lang], "__k": L["code"][lang],
                                           "__s": L["sex"][lang], "__a": {"es": "Grupo etario", "en": "Age group"}[lang]})
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Celda: prestaciones informadas (establecimientos reportantes del código-año entre paréntesis). "
                   "Unidad: ingreso o egreso del programa de salud mental, nunca persona única ni prevalencia. "
                   "Denominador: ninguno; las tasas poblacionales estandarizadas del A05 están en "
                   "models_a05_standardised_rates.csv. Cobertura: APS y especialidad del sistema público que reportan "
                   "REM A05; el número de establecimientos crece a lo largo del período y explica parte del aumento. "
                   "Era: el autismo estricto y las categorías desagregadas existen desde 2021; 2019–2020 solo tienen "
                   "TGD amplio, que se informa por separado y no se une a la serie posterior. Las columnas de edad del "
                   "REM cambian de posición entre años; la tabla numérica conserva la columna fuente (source_col). "),
            "en": ("Cell: reported activities (reporting establishments of the code-year in brackets). Unit: entry to "
                   "or exit from the mental-health programme, never a unique person and never prevalence. Denominator: "
                   "none; standardised population rates for A05 are in models_a05_standardised_rates.csv. Coverage: "
                   "primary-care and specialty public facilities reporting REM A05; the number of establishments grows "
                   "over the period and explains part of the increase. Era: strict autism and the disaggregated "
                   "categories exist from 2021; 2019–2020 carry only broad PDD, reported separately and never joined to "
                   "the later series. REM age columns change position between years; the numeric companion keeps the "
                   "source column (source_col). ")}[lang] + NOTE_REM[lang]
    title = {"es": f"REM A05: ingresos y egresos por edad, sexo, categoría y año, 2021–2025 (TGD amplio 2019–2020 como serie separada) — {vlabel}",
             "en": f"REM A05: entries and exits by age, sex, category and year, 2021–2025 (broad PDD 2019–2020 as a separate series) — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 10}_rem_a05_age_sex_full", f, sub, title, note)
    return sub


# ===========================================================================
# E71 — P2 y P6 por región y año (stock de diciembre)
# ===========================================================================
def build_E71(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    e = I.tidy("rem_establishment_year", low_memory=False)
    p = e.loc[e.module.isin(["P2", "P6"])].copy()
    p["december_value"] = pd.to_numeric(p.december_value, errors="coerce")
    p["has_december_row"] = p.has_december_row.astype(str).str.lower().isin(["true", "1"])
    blocks = [
        ("P2_tea", [CFG.P2_TEA], "2019–2025",
         {"es": "P2 · Personas con TEA bajo control (código único, sin quiebre)",
          "en": "P2 · Persons with ASD under control (single code, no break)"}),
        ("P2_naneas", [CFG.P2_NANEAS_TOTAL], "2023–2025",
         {"es": "P2 · Total NANEAS bajo control (existe desde diciembre de 2023)",
          "en": "P2 · Total NANEAS under control (exists from December 2023)"}),
        ("P6_primary_broad", [CFG.P6_BROAD_PRE2021["primary"]], "2019–2020",
         {"es": "P6 · APS, TGD amplio (era 2019–2020)", "en": "P6 · Primary care, broad PDD (2019–2020 era)"}),
        ("P6_primary_family", CFG.VARIANTS[variant]["p6_primary"], "2021–2025",
         {"es": "P6 · APS, familia F84 de la variante (era 2021–2025)",
          "en": "P6 · Primary care, variant F84 family (2021–2025 era)"}),
        ("P6_specialty_broad", [CFG.P6_BROAD_PRE2021["specialty"]], "2019–2020",
         {"es": "P6 · Especialidad, TGD amplio (era 2019–2020)", "en": "P6 · Specialty, broad PDD (2019–2020 era)"}),
        ("P6_specialty_family", CFG.VARIANTS[variant]["p6_specialty"], "2021–2025",
         {"es": "P6 · Especialidad, familia F84 de la variante (era 2021–2025)",
          "en": "P6 · Specialty, variant F84 family (2021–2025 era)"}),
    ]
    years = sorted(p.year.unique())
    num_rows, rows = [], []
    for block_id, codes, era, blabel in blocks:
        g = p.loc[p.code.isin(codes) & p.has_december_row]
        if g.empty:
            continue
        agg = (g.groupby(["year", "IdRegion"], observed=True)
               .agg(december_total=("december_value", "sum"),
                    establishments=("IdEstablecimiento", "nunique")).reset_index())
        agg["block"] = block_id
        agg["era"] = era
        agg["codes"] = "+".join(codes)
        agg["suppressed"] = agg.december_total < 5
        num_rows.append(agg)
        regions = [r for r in REGION_ORDER if r in set(agg.IdRegion.dropna().astype(int))]
        for cut in regions:
            s = agg.loc[agg.IdRegion == cut]
            r = {"__b": blabel[lang], "__e": era, "__r": region_label(cut, lang)}
            for y in years:
                c = s.loc[s.year == y]
                if c.empty:
                    r[str(y)] = NR[lang]
                    continue
                c = c.iloc[0]
                r[str(y)] = (SUP[lang] if c.december_total < 5
                             else f"{num(c.december_total, 0, lang)} ({num(c.establishments, 0, lang)})")
            rows.append(r)
        tot = g.groupby("year", observed=True).december_value.sum().reset_index(name="december_total")
        est = g.groupby("year", observed=True).IdEstablecimiento.nunique().reset_index(name="establishments")
        tot = tot.merge(est, on="year", how="left")
        r = {"__b": blabel[lang], "__e": era, "__r": {"es": "Chile (total nacional)", "en": "Chile (national total)"}[lang]}
        for y in years:
            c = tot.loc[tot.year == y]
            r[str(y)] = (f"{num(c.december_total.iloc[0], 0, lang)} ({num(c.establishments.iloc[0], 0, lang)})"
                         if len(c) else NR[lang])
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__b": L["block"][lang], "__e": L["era"][lang], "__r": {"es": "Región del establecimiento", "en": "Region of the establishment"}[lang]})
    numeric = pd.concat(num_rows, ignore_index=True) if num_rows else pd.DataFrame()
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Celda: personas bajo control en diciembre (establecimientos que reportan diciembre entre "
                   "paréntesis). Unidad: stock semestral, NUNCA un flujo: diciembre y junio no se suman y esta tabla "
                   "usa solo diciembre (junio está en las tablas de sensibilidad). Denominador: ninguno; no se calculan "
                   "tasas porque el REM localiza al ESTABLECIMIENTO (lugar de atención) y no la residencia del "
                   "paciente, de modo que la población INE regional no es un denominador compatible. Las celdas con "
                   "menos de cinco personas se suprimen («< 5»). «no reportado» significa que ningún establecimiento de "
                   "la región informó diciembre para ese código-año, estado distinto de cero. Los bloques de eras "
                   "distintas (TGD amplio 2019–2020 y familia F84 desde 2021) NUNCA forman una serie continua. "),
            "en": ("Cell: persons under control in December (establishments reporting December in brackets). Unit: "
                   "semi-annual stock, NEVER a flow: December and June are never summed and this table uses December "
                   "only (June is in the sensitivity tables). Denominator: none; no rates are computed because REM "
                   "locates the ESTABLISHMENT (place of care) and not the patient's residence, so the regional INE "
                   "population is not a compatible denominator. Cells with fewer than five persons are suppressed "
                   "('< 5'). 'not reported' means no establishment in the region reported December for that code-year, "
                   "a state distinct from zero. Blocks from different eras (broad PDD 2019–2020 and F84 family from "
                   "2021) NEVER form a continuous series. ")}[lang] + NOTE_REM[lang]
    title = {"es": f"REM P2 y P6: personas bajo control en diciembre por región del establecimiento, año y era de definición, 2019–2025 — {vlabel}",
             "en": f"REM P2 and P6: persons under control in December by region of the establishment, year and definition era, 2019–2025 — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 11}_rem_p2_p6_region_year", f, numeric, title, note)
    return numeric


# ===========================================================================
# E72 — establecimientos reportantes por módulo REM y año
# ===========================================================================
def build_E72(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    e = I.tidy("rem_establishment_year", low_memory=False)
    ra = I.tidy("rem_pathway_annual")
    years = sorted(e.year.unique())
    e = e.copy()
    e["annual_total"] = pd.to_numeric(e.annual_total, errors="coerce")
    # Las series de flujo (A03/A05/A27/A28) llevan el valor en annual_total; las series de stock (P2/P6) lo llevan
    # en december_value (y en june_value cuando no hay fila de diciembre) y dejan annual_total vacío. Usar solo
    # annual_total haría que el recuento de establecimientos con un valor > 0 fuese CERO en todos los años de P2 y
    # P6, lo que no es un cero observado sino una columna que no aplica a esa serie.
    e["december_value"] = pd.to_numeric(e.december_value, errors="coerce")
    e["june_value"] = pd.to_numeric(e.june_value, errors="coerce")
    e["value_for_gt0"] = e.annual_total.where(e.annual_total.notna(),
                                              e.december_value.where(e.december_value.notna(), e.june_value))
    e["in_stable_panel"] = e.in_stable_panel.astype(str).str.lower().isin(["true", "1"])
    rows, num_rows = [], []
    metrics = [("rows", {"es": "Establecimientos con al menos una fila", "en": "Establishments with at least one row"}),
               ("gt0", {"es": "Establecimientos con al menos un valor > 0", "en": "Establishments with at least one value > 0"}),
               ("panel", {"es": "Establecimientos del panel estable", "en": "Establishments in the stable panel"}),
               ("codes", {"es": "Códigos vigentes en el año", "en": "Codes in force in the year"})]
    for module in ["A03", "A05", "A27", "A28", "P2", "P6"]:
        g = e.loc[e.module == module]
        for mid, mlabel in metrics:
            r = {"__m": module, "__k": mlabel[lang]}
            for y in years:
                gy = g.loc[g.year == y]
                if mid == "rows":
                    v = gy.IdEstablecimiento.nunique()
                elif mid == "gt0":
                    v = gy.loc[gy.value_for_gt0.fillna(0) > 0, "IdEstablecimiento"].nunique()
                elif mid == "panel":
                    v = gy.loc[gy.in_stable_panel, "IdEstablecimiento"].nunique()
                else:
                    v = ra.loc[(ra.module == module) & (ra.year == y), "code"].nunique()
                r[str(y)] = num(v, 0, lang) if v or len(gy) else NR[lang]
                num_rows.append({"module": module, "metric": mid, "year": y, "value": int(v)})
            rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__m": L["module"][lang], "__k": L["indicator"][lang]})
    numeric = pd.DataFrame(num_rows)
    note = {"es": ("Unidad: establecimiento REM distinto (IdEstablecimiento), contado una vez por módulo y año; los "
                   "recuentos de módulos distintos NO son aditivos porque un mismo establecimiento reporta varios "
                   "módulos. Denominador: ninguno. «Panel estable» es el subconjunto de establecimientos con reporte en "
                   "todos los años de la serie del módulo, usado como sensibilidad. La expansión del número de "
                   "establecimientos reportantes es una amenaza de comparabilidad de primer orden y debe leerse junto a "
                   "cualquier serie de conteos REM. Serie P: los stocks se cuentan en diciembre, de modo que el "
                   "recuento de establecimientos con un valor mayor que cero usa el stock de diciembre (y el de junio "
                   "cuando no hay fila de diciembre), mientras que en las series de flujo A03/A05/A27/A28 usa el total "
                   "anual; las dos magnitudes no se suman ni se comparan entre sí. "),
            "en": ("Unit: distinct REM establishment (IdEstablecimiento), counted once per module and year; counts from "
                   "different modules are NOT additive because the same establishment reports several modules. "
                   "Denominator: none. The 'stable panel' is the subset of establishments reporting in every year of "
                   "the module's series, used as a sensitivity analysis. The expansion in the number of reporting "
                   "establishments is a first-order comparability threat and must be read alongside any REM count "
                   "series. P series: stocks are counted in December, so the count of establishments with a value "
                   "greater than zero uses the December stock (and the June stock where no December row exists), while "
                   "for the flow series A03/A05/A27/A28 it uses the annual total; the two quantities are never summed "
                   "nor compared with each other. ")}[lang] + NOTE_REM[lang]
    title = {"es": "Establecimientos reportantes por módulo REM y año, con panel estable y número de códigos vigentes, 2019–2025",
             "en": "Reporting establishments by REM module and year, with the stable panel and the number of codes in force, 2019–2025"}[lang]
    reg.add(f"E{BASE_NUMBER + 12}_rem_establishments_by_module", f, numeric, title, note)
    return numeric


# ===========================================================================
# E73 — capas de denominador por año, región, edad y sexo
# ===========================================================================
def build_E73(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    cov = I.tidy("coverage_layers_year")
    ine = I.tidy("ine_population_region_national_year_age_sex")
    fo = I.tidy("fonasa_beneficiaries_comuna_year",
                usecols=["year", "cut_region", "sex", "age_band_5y", "beneficiaries"])
    iso = I.tidy("isapre_beneficiaries_comuna_year",
                 usecols=["year", "cut_region", "sex", "age_band_5y", "beneficiarios"])
    aps = I.tidy("aps_enrolment_comuna_year",
                 usecols=["year", "cut_region", "sex", "age_band_10y", "enrolled"])
    years = sorted(cov.year.unique())
    iso = iso.loc[iso.sex != "TOTAL"]          # la vista TOTAL duplica las vistas por sexo
    fo = fo.loc[fo.year.isin(years)]
    layers = {
        "ine": ({"es": "Población INE (proyección base Censo 2017, 30 de junio)",
                 "en": "INE population (2017-census-based projection, 30 June)"},
                {"es": "residencia (territorial)", "en": "residence (territorial)"}),
        "fonasa": ({"es": "Beneficiarios FONASA (stock de diciembre)", "en": "FONASA beneficiaries (December stock)"},
                   {"es": "mixta: comuna del centro APS para inscritos y domicilio para no inscritos",
                    "en": "mixed: APS-centre comuna for enrollees and domicile for non-enrollees"}),
        "isapre": ({"es": "Beneficiarios ISAPRE (stock de diciembre)", "en": "ISAPRE beneficiaries (December stock)"},
                   {"es": "comuna administrativa del beneficiario", "en": "administrative comuna of the beneficiary"}),
        "aps": ({"es": "Inscritos APS (stock de diciembre)", "en": "APS enrolled (December stock)"},
                {"es": "comuna del centro de inscripción (lugar de atención)",
                 "en": "comuna of the enrolment centre (place of care)"}),
    }
    num_rows, rows = [], []

    def emit(layer, dimension, category, series_by_year):
        r = {"__l": layers[layer][0][lang], "__d": dimension, "__c": category}
        for y in years:
            v = series_by_year.get(y)
            r[str(y)] = num(v, 0, lang) if v is not None and pd.notna(v) else NE[lang]
            num_rows.append({"layer": layer, "dimension": dimension, "category": category, "year": y,
                             "value": (float(v) if v is not None and pd.notna(v) else np.nan),
                             "geography": layers[layer][1]["en"]})
        rows.append(r)

    dim_nat = {"es": "Total nacional", "en": "National total"}[lang]
    dim_reg = {"es": "Región", "en": "Region"}[lang]
    dim_age = {"es": "Grupo etario", "en": "Age group"}[lang]
    dim_sex = {"es": "Sexo", "en": "Sex"}[lang]
    # nacional
    emit("ine", dim_nat, {"es": "Chile", "en": "Chile"}[lang],
         cov.set_index("year").ine_population_base2017_30jun.to_dict())
    emit("fonasa", dim_nat, {"es": "Chile", "en": "Chile"}[lang],
         cov.set_index("year").fonasa_beneficiaries_dec.to_dict())
    emit("isapre", dim_nat, {"es": "Chile", "en": "Chile"}[lang],
         cov.set_index("year").isapre_beneficiaries_dec.to_dict())
    emit("aps", dim_nat, {"es": "Chile", "en": "Chile"}[lang],
         cov.set_index("year").aps_enrolled_dec.to_dict())
    # región
    src = {"ine": (ine.loc[ine.level == "region"], "cut_region", "population"),
           "fonasa": (fo, "cut_region", "beneficiaries"),
           "isapre": (iso, "cut_region", "beneficiarios"),
           "aps": (aps, "cut_region", "enrolled")}
    for layer, (d, col, val) in src.items():
        d = d.loc[d.sex != "TOTAL"] if "sex" in d.columns else d
        agg = d.groupby(["year", col], observed=True)[val].sum()
        for cut in REGION_ORDER:
            s = {y: agg.get((y, cut)) for y in years}
            if all(v is None or pd.isna(v) for v in s.values()):
                continue
            emit(layer, dim_reg, region_label(cut, lang), s)
        miss = d.loc[d[col].isna()]
        if len(miss):
            s = miss.groupby("year", observed=True)[val].sum().to_dict()
            emit(layer, dim_reg, {"es": "Comuna no enlazada", "en": "Comuna not linked"}[lang], s)
    # edad
    age_src = {"ine": (ine.loc[ine.level == "national"], "age_group", "population"),
               "fonasa": (fo, "age_band_5y", "beneficiaries"),
               "isapre": (iso, "age_band_5y", "beneficiarios"),
               "aps": (aps, "age_band_10y", "enrolled")}
    for layer, (d, col, val) in age_src.items():
        d2 = d.loc[d.sex != "TOTAL"] if "sex" in d.columns else d
        agg = d2.groupby(["year", col], observed=True)[val].sum()
        present = set(map(str, d2[col].dropna()))
        cats = [c for c in AGE_GROUPS if c in present]
        cats = cats + sorted(present - set(cats))
        for cat in cats:
            emit(layer, dim_age, str(cat), {y: agg.get((y, cat)) for y in years})
        miss = d2.loc[d2[col].isna()]
        if len(miss):
            emit(layer, dim_age, {"es": "Edad no informada", "en": "Age not reported"}[lang],
                 miss.groupby("year", observed=True)[val].sum().to_dict())
    # sexo
    sex_src = {"ine": (ine.loc[(ine.level == "national") & (ine.sex != "TOTAL")], "population"),
               "fonasa": (fo, "beneficiaries"), "isapre": (iso, "beneficiarios"), "aps": (aps, "enrolled")}
    for layer, (d, val) in sex_src.items():
        agg = d.groupby(["year", "sex"], observed=True)[val].sum()
        for sx in sorted(set(d.sex.dropna())):
            emit(layer, dim_sex, sex_lbl(sx, lang), {y: agg.get((y, sx)) for y in years})
    f = pd.DataFrame(rows).rename(columns={"__l": L["layer"][lang], "__d": L["dimension"][lang],
                                           "__c": L["category"][lang]})
    numeric = pd.DataFrame(num_rows)
    note = {"es": ("Unidad: personas. Las cuatro capas responden preguntas distintas y NO son intercambiables: INE es "
                   "población territorial de residencia y es el único denominador válido para tasas poblacionales; "
                   "FONASA e ISAPRE son cobertura de aseguramiento (stocks de diciembre) con geografía administrativa "
                   "mixta; los inscritos APS son cobertura operativa por centro, es decir, LUGAR DE ATENCIÓN y no "
                   "residencia. Por eso no se calculan cocientes entre capas con geografías distintas sin una nota "
                   "explícita, y REM-20 no se usa nunca como población cubierta. Las filas nacionales provienen de "
                   "coverage_layers_year.csv; las filas por región, edad y sexo se agregan desde los archivos "
                   "comunales. El total nacional ISAPRE agregado desde el archivo comunal excluye a los nonatos o sin "
                   "clasificar, que sí están en el total oficial de diciembre. Las bandas etarias difieren entre "
                   "fuentes (INE y FONASA/ISAPRE en grupos quinquenales; APS en grupos decenales, con cambio de "
                   "esquema en 2024) y no se armonizan silenciosamente. "),
            "en": ("Unit: persons. The four layers answer different questions and are NOT interchangeable: INE is the "
                   "territorial residence population and is the only valid denominator for population rates; FONASA and "
                   "ISAPRE are insurance coverage (December stocks) with mixed administrative geography; APS enrollees "
                   "are operational coverage by centre, that is, PLACE OF CARE and not residence. Ratios between layers "
                   "with different geographies are therefore never computed without an explicit note, and REM-20 is "
                   "never used as a covered population. National rows come from coverage_layers_year.csv; region, age "
                   "and sex rows are aggregated from the comuna files. The ISAPRE national total aggregated from the "
                   "comuna file excludes unborn/unclassified beneficiaries, which are included in the official December "
                   "total. Age bands differ between sources (INE and FONASA/ISAPRE in five-year groups; APS in ten-year "
                   "groups, with a scheme change in 2024) and are never harmonised silently. ")}[lang]
    title = {"es": "Capas de denominador por año, región, grupo etario y sexo: población INE, beneficiarios FONASA, beneficiarios ISAPRE e inscritos APS, 2019–2025",
             "en": "Denominator layers by year, region, age group and sex: INE population, FONASA beneficiaries, ISAPRE beneficiaries and APS enrollees, 2019–2025"}[lang]
    reg.add(f"E{BASE_NUMBER + 13}_denominator_layers_full", f, numeric, title, note)
    return numeric


# ===========================================================================
# E74 — reglas de armonización FONASA / APS / ISAPRE
# ===========================================================================
def build_E74(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    fs = I.tidy("fonasa_schema_by_year")
    ap = I.tidy("aps_panel")
    iso = I.tidy("isapre_beneficiaries_national_year")
    cols = {"src": L["source"][lang], "y": L["year"][lang], "file": L["file"][lang],
            "sch": {"es": "Esquema y columnas clave", "en": "Scheme and key columns"}[lang],
            "tot": {"es": "Total (diciembre)", "en": "Total (December)"}[lang],
            "rule": L["rule"][lang], "sha": "SHA-256"}
    rows = []
    for _, c in fs.sort_values("year").iterrows():
        rows.append({cols["src"]: "FONASA", cols["y"]: yr(c.year, lang),
                     cols["file"]: f"{txt(c.source_archive, lang)} → {txt(c.member_file, lang)}",
                     cols["sch"]: (f"{txt(c.encoding, lang)}; n={num(c.n_rows_raw, 0, lang)}; "
                                   f"{SCH['count'][lang]}={txt(c.count_column, lang)}; "
                                   f"{SCH['tramo'][lang]}={txt(c.tramo_column, lang)}; "
                                   f"{SCH['region'][lang]}={txt(c.region_column, lang)}; "
                                   f"{SCH['age'][lang]}: {stxt(c.age_band_scheme, lang)}"),
                     cols["tot"]: num(c.total_beneficiaries, 0, lang),
                     cols["rule"]: stxt(c.aggregation_rule, lang),
                     cols["sha"]: txt(c.sha256, lang)[:16]})
    for _, c in ap.sort_values("year").iterrows():
        rows.append({cols["src"]: "APS", cols["y"]: yr(c.year, lang),
                     cols["file"]: "Inscritos_APS_YYYY12.csv",
                     cols["sch"]: (f"{SCH['centres'][lang]}={num(c.centres_total, 0, lang)}; "
                                   f"{SCH['panel'][lang]} {num(1871, 0, lang)}={num(c.centres_panel, 0, lang)}; "
                                   f"{SCH['tramo'][lang]} A–D={num(c.enrolled_tramo_AD, 0, lang)}; "
                                   f"{SCH['tramo'][lang]} X={num(c.enrolled_tramo_X, 0, lang)}; "
                                   f"{SCH['tramo_missing'][lang]}={num(c.enrolled_tramo_missing, 0, lang)}"),
                     cols["tot"]: num(c.enrolled_total, 0, lang),
                     cols["rule"]: (f"{stxt(c.unit, lang)}; " +
                                    {"es": f"retención del panel de 1.871 centros = {pct(100 * c.retention_panel_1871, lang, 2)}",
                                     "en": f"retention of the 1,871-centre panel = {pct(100 * c.retention_panel_1871, lang, 2)}"}[lang]),
                     cols["sha"]: NE[lang]})
    for _, c in iso.sort_values("year").iterrows():
        rows.append({cols["src"]: "ISAPRE", cols["y"]: yr(c.year, lang),
                     cols["file"]: txt(c.source_file, lang),
                     cols["sch"]: (f"{stxt(c.rule, lang)}; {SCH['cotizantes'][lang]}={num(c.cotizantes, 0, lang)}; "
                                   f"{SCH['cargas'][lang]}={num(c.cargas, 0, lang)}; "
                                   f"{SCH['nonatos'][lang]}={num(c.nonatos_sin_clasificar, 0, lang)}; "
                                   f"{stxt(c.age_note, lang)}"),
                     cols["tot"]: num(c.beneficiarios_total, 0, lang),
                     cols["rule"]: stxt(c.aggregation_rule, lang), cols["sha"]: NE[lang]})
    f = pd.DataFrame(rows)
    numeric = pd.concat([fs.assign(source="FONASA"), ap.assign(source="APS"), iso.assign(source="ISAPRE")],
                        ignore_index=True)
    note = {"es": ("Unidad: personas (stock de diciembre). Esta tabla documenta, año por año, los quiebres de esquema "
                   "que obligan a armonizar explícitamente y a conservar las columnas originales. FONASA agregado "
                   "cambia de esquema en 2021, 2023, 2024 y 2025; sus filas repetidas son ADITIVAS y nunca se eliminan "
                   "con drop_duplicates, porque hacerlo reduce los totales oficiales. APS cambia grupos de edad y "
                   "nombres de variables en 2024. ISAPRE pasa de .xls a .xlsx y de edades simples a quinquenales en "
                   "2021. Ninguna de las tres capas es población territorial: véase la tabla de capas de denominador. "
                   "En la columna de esquema, los rótulos que nombran cada campo se leen en el idioma del documento y "
                   "lo que va después del signo igual es el nombre de la columna o el rótulo de tramo de edad tal como "
                   "los escribe la fuente (textual, en español). "
                   "SHA-256 truncado a 16 caracteres; el valor completo está en data_provenance.csv. "),
            "en": ("Unit: persons (December stock). This table documents, year by year, the scheme breaks that force "
                   "explicit harmonisation and the retention of the original columns. Aggregated FONASA changes scheme "
                   "in 2021, 2023, 2024 and 2025; its repeated rows are ADDITIVE and are never removed with "
                   "drop_duplicates, because doing so reduces the official totals. APS changes age groups and variable "
                   "names in 2024. ISAPRE moves from .xls to .xlsx and from single years to five-year bands in 2021. "
                   "None of the three layers is a territorial population: see the denominator-layers table. In the "
                   "scheme column the labels naming each field are read in the language of the document, and whatever "
                   "follows the equals sign is the column name or the age-band label exactly as the source writes it "
                   "(verbatim Spanish). SHA-256 "
                   "truncated to 16 characters; the full value is in data_provenance.csv. ")}[lang]
    title = {"es": "Reglas de armonización de FONASA, inscritos APS e ISAPRE por año: archivo, esquema, columnas clave, total de diciembre y regla de agregación",
             "en": "Harmonisation rules for FONASA, APS enrolment and ISAPRE by year: file, scheme, key columns, December total and aggregation rule"}[lang]
    reg.add(f"E{BASE_NUMBER + 14}_coverage_harmonisation_rules", f, numeric, title, note)
    return numeric


# ===========================================================================
# E75 — estimaciones de encuesta
# ===========================================================================
def build_E75(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    s = I.tidy("survey_estimates").copy()
    cols = {"sv": {"es": "Encuesta", "en": "Survey"}[lang], "dom": L["domain"][lang],
            "sub": L["subgroup"][lang], "typ": {"es": "Tipo de estimación", "en": "Estimate type"}[lang],
            "n": {"es": "n del dominio; casos", "en": "Domain n; cases"}[lang],
            "p": {"es": "% ponderado (IC 95 %)", "en": "Weighted % (95% CI)"}[lang],
            "tot": {"es": "Total ponderado", "en": "Weighted total"}[lang],
            "des": {"es": "Diseño: ponderador / estrato / conglomerado", "en": "Design: weight / stratum / cluster"}[lang],
            "dq": {"es": "DEFF; EER; gl; UPM; estratos", "en": "DEFF; RSE; df; PSU; strata"}[lang],
            "flag": {"es": "Marca de precisión", "en": "Precision flag"}[lang]}
    rows = []
    for _, c in s.iterrows():
        reliable = (pd.notna(c.cases) and c.cases >= 30) and (pd.notna(c.rse) and c.rse <= 30)
        flag = stxt(c.precision_flag, lang)
        if not reliable:
            flag = (f"{flag} — " + {"es": "no presentar como estimación confiable (casos < 30 o EER > 30 %)",
                                    "en": "not to be presented as a reliable estimate (cases < 30 or RSE > 30%)"}[lang])
        rows.append({cols["sv"]: txt(c.survey, lang), cols["dom"]: stxt(c.domain, lang),
                     cols["sub"]: f"{stxt(c.subgroup_type, lang)}: {stxt(c.subgroup, lang)}",
                     cols["typ"]: stxt(c.estimate_type, lang),
                     cols["n"]: f"{num(c.n, 0, lang)}; {num(c.cases, 0, lang)}",
                     cols["p"]: (f"{num(100 * c.proportion, 2, lang)} "
                                 f"({ci(100 * c.lo, 100 * c.hi, 2, lang)})") if pd.notna(c.proportion) else NE[lang],
                     cols["tot"]: num(c.weighted_total, 0, lang),
                     cols["des"]: f"{txt(c.weight_var, lang)} / {txt(c.strata_var, lang)} / {txt(c.psu_var, lang)}",
                     cols["dq"]: (f"{num(c.deff, 2, lang)}; {pct(c.rse, lang)}; {num(c.df, 0, lang)}; "
                                  f"{num(c.n_psu, 0, lang)}; {num(c.n_strata, 0, lang)}"),
                     cols["flag"]: flag})
    f = pd.DataFrame(rows)
    note = {"es": ("Unidad: persona encuestada. Denominador: universo del dominio declarado en la columna "
                   "domain_definition de la tabla numérica. Todas las proporciones son ESTIMACIONES DE DISEÑO "
                   "COMPLEJO: ponderador, estrato y conglomerado se declaran en cada fila y el error estándar usa "
                   "linealización de Taylor con IC 95 % en escala logit; ningún porcentaje simple sin ponderar se "
                   "presenta como estimación nacional. Los dominios con menos de 30 casos o con error estándar "
                   "relativo (EER) superior al 30 % se marcan y NO deben presentarse como estimaciones confiables. "
                   "Estas encuestas miden autorreporte o reporte del cuidador con o sin confirmación profesional: son "
                   "referencias de contraste poblacional, no una medida del reconocimiento administrativo, y no se "
                   "desagregan a comuna. Archivos fuente y SHA-256 en la tabla numérica (columnas source_file y "
                   "source_sha256). "),
            "en": ("Unit: surveyed person. Denominator: the domain universe declared in the domain_definition column of "
                   "the numeric companion. All proportions are COMPLEX-DESIGN ESTIMATES: weight, stratum and cluster "
                   "are declared in every row and the standard error uses Taylor linearisation with logit-scale 95% CI; "
                   "no simple unweighted percentage is presented as a national estimate. Domains with fewer than 30 "
                   "cases or with a relative standard error (RSE) above 30% are flagged and must NOT be presented as "
                   "reliable estimates. These surveys measure self- or carer-report with or without professional "
                   "confirmation: they are population contrast benchmarks, not a measure of administrative recognition, "
                   "and are never disaggregated to comuna. Source files and SHA-256 in the numeric companion (columns "
                   "source_file and source_sha256). ")}[lang]
    title = {"es": "Estimaciones de encuesta poblacional (ENDIDE 2022 y ENCAVI 2023–2024): todos los dominios y subgrupos con variables de diseño, DEFF, error estándar relativo y marcas de precisión",
             "en": "Population survey estimates (ENDIDE 2022 and ENCAVI 2023–2024): every domain and subgroup with design variables, DEFF, relative standard error and precision flags"}[lang]
    reg.add(f"E{BASE_NUMBER + 15}_survey_estimates_full", f, s, title, note)
    return s


# ===========================================================================
# E76 — educación: serie PIE completa
# ===========================================================================
def build_E76(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    p = I.tidy("pie_series")
    years = sorted(p.year.unique())
    rows = []
    for series, g in p.groupby("series", observed=True, sort=True):
        r = {"__s": series, "__d": stxt(g.definition.dropna().iloc[0] if g.definition.notna().any() else None, lang)}
        for y in years:
            c = g.loc[g.year == y]
            if c.empty:
                r[str(y)] = NR[lang]
                continue
            v = c.value.iloc[0]
            unit = str(c.unit.iloc[0])
            r[str(y)] = num(v, 2 if "pct" in unit or "pct" in series else 0, lang)
        src = g.drop_duplicates("source_file")
        r[L["source"][lang]] = "; ".join(f"{txt(x.source_file, lang)} (p. {txt(x.pdf_page, lang)})"
                                         for _, x in src.iterrows())
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__s": L["series"][lang],
                                           "__d": {"es": "Definición", "en": "Definition"}[lang]})
    note = {"es": ("Unidad: estudiantes del Programa de Integración Escolar (PIE) y de escuelas especiales, según la "
                   "definición de cada fila; los porcentajes publicados se conservan tal como aparecen en la fuente. "
                   "Denominador: matrícula PIE o postulantes SINACES según la fila. Las definiciones NO se mezclan: "
                   "TEA estricto, TEA-Asperger y la armonización TEA + TEA-Asperger son series distintas y solo la "
                   "armonizada es comparable con el informe SINACES. Discrepancia registrada de cinco casos en 2022: "
                   "el informe SINACES escribe 42.945, mientras que 45.014 menos 2.074 de escuelas especiales da "
                   "42.940, coincidente con Apuntes 60; se conserva 42.940 y se declara la diferencia. La educación "
                   "cubre establecimientos con financiamiento estatal y no es una medida de prevalencia. «no "
                   "reportado» indica que la fuente no publica esa serie en ese año, estado distinto de cero. Páginas "
                   "físicas del PDF y SHA-256 en la tabla numérica. La columna «Serie» contiene el identificador de "
                   "máquina de la serie, idéntico en ambos idiomas; la columna «Definición» da su significado. "),
            "en": ("Unit: students in the School Integration Programme (PIE) and in special schools, as defined in each "
                   "row; published percentages are kept exactly as they appear in the source. Denominator: PIE "
                   "enrolment or SINACES applicants depending on the row. Definitions are NOT mixed: strict ASD, "
                   "ASD-Asperger and the harmonised ASD + ASD-Asperger series are distinct, and only the harmonised one "
                   "is comparable with the SINACES report. Recorded five-case discrepancy in 2022: the SINACES report "
                   "writes 42,945, whereas 45,014 minus 2,074 special-school students gives 42,940, matching Apuntes "
                   "60; 42,940 is kept and the difference is declared. Education covers state-funded establishments and "
                   "is not a measure of prevalence. 'not reported' means the source does not publish that series in "
                   "that year, a state distinct from zero. Physical PDF pages and SHA-256 in the numeric "
                   "companion. The 'Series' column carries the machine identifier of the series, identical in both "
                   "languages; the 'Definition' column gives its meaning. ")}[lang]
    title = {"es": "Educación: serie PIE completa por definición y año (TEA estricto, TEA-Asperger, armonizado, escuelas especiales y denominadores publicados), 2019–2025",
             "en": "Education: complete PIE series by definition and year (strict ASD, ASD-Asperger, harmonised, special schools and published denominators), 2019–2025"}[lang]
    reg.add(f"E{BASE_NUMBER + 16}_education_pie_full", f, p, title, note)
    return p


# ===========================================================================
# E77 — educación: JUNAEB
# ===========================================================================
def build_E77(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    j = I.tidy("junaeb_tea_year_level")
    cols = {"y": L["year"][lang], "lv": L["level"][lang], "sx": L["sex"][lang],
            "n": {"es": "Estudiantes; casos TEA", "en": "Students; ASD cases"}[lang],
            "pw": {"es": "% ponderado (IC 95 %)", "en": "Weighted % (95% CI)"}[lang],
            "pu": {"es": "% sin ponderar", "en": "Unweighted %"}[lang],
            "tot": {"es": "Total ponderado; población ponderada", "en": "Weighted total; weighted population"}[lang],
            "w": {"es": "Ponderador y diseño", "en": "Weight and design"}[lang],
            "est": {"es": "Estimable", "en": "Estimable"}[lang]}
    rows = []
    for _, c in j.sort_values(["year", "level", "sex"]).iterrows():
        estimable = str(c.estimable).lower() in ("true", "1", "yes", "sí")
        rows.append({cols["y"]: yr(c.year, lang),
                     cols["lv"]: JUNAEB_LEVEL.get(str(c.level), {"es": str(c.level), "en": str(c.level)})[lang],
                     cols["sx"]: sex_lbl(c.sex, lang),
                     cols["n"]: f"{num(c.n_students, 0, lang)}; {num(c.n_tea_unweighted, 0, lang)}",
                     cols["pw"]: (f"{num(c.proportion_weighted_pct, 2, lang)} ({ci(c.lo_pct, c.hi_pct, 2, lang)})"
                                  if estimable and pd.notna(c.proportion_weighted_pct) else NE[lang]),
                     cols["pu"]: (num(c.proportion_unweighted_pct, 2, lang)
                                  if pd.notna(c.proportion_unweighted_pct) else NE[lang]),
                     cols["tot"]: f"{num(c.weighted_tea_total, 0, lang)}; {num(c.weighted_population, 0, lang)}",
                     cols["w"]: f"{stxt(c.weight_variable, lang)}; {stxt(c.design_note, lang)}",
                     cols["est"]: (L["yes"][lang] if estimable else
                                   f"{L['no'][lang]} — {stxt(c.note, lang)}")})
    f = pd.DataFrame(rows)
    note = {"es": ("Unidad: estudiante de la cohorte encuestada. Denominador: estudiantes con respuesta al ítem TEA en "
                   "el nivel y año (n_students; n_answered en la tabla numérica). Se aplica el ponderador EXP declarado "
                   "en cada fila; JUNAEB no publica estratos ni conglomerados, de modo que el intervalo es de muestreo "
                   "aleatorio simple ponderado y subestima la varianza real. JUNAEB representa cohortes escolares "
                   "seleccionadas y REPORTE DE CUIDADORES, no prevalencia nacional ni diagnóstico confirmado. En 2024 "
                   "la variable TEA de 1.º medio está completamente vacía: se informa «no estimable», jamás cero. El "
                   "cuestionario y la redacción del ítem cambian entre años; ambas se conservan en la tabla numérica "
                   "(item_wording, filter_wording). "),
            "en": ("Unit: student of the surveyed cohort. Denominator: students answering the ASD item in the level and "
                   "year (n_students; n_answered in the numeric companion). The EXP weight declared in each row is "
                   "applied; JUNAEB publishes no strata or clusters, so the interval is weighted simple random sampling "
                   "and understates the true variance. JUNAEB represents selected school cohorts and CARER REPORT, not "
                   "national prevalence and not confirmed diagnosis. In 2024 the Year-9 ASD variable is entirely empty: "
                   "it is reported as 'not estimable', never as zero. The questionnaire and item wording change between "
                   "years; both are kept in the numeric companion (item_wording, filter_wording). ")}[lang]
    title = {"es": "Educación: encuesta JUNAEB por año, nivel y sexo, con proporciones ponderadas, intervalos y estados de estimabilidad, 2019–2025",
             "en": "Education: JUNAEB survey by year, level and sex, with weighted proportions, intervals and estimability states, 2019–2025"}[lang]
    reg.add(f"E{BASE_NUMBER + 17}_education_junaeb_full", f, j, title, note)
    return j


# ===========================================================================
# E78 — tabla de modelos con todas las especificaciones
# ===========================================================================
def build_E78(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    m = I.tidy("models_summary")
    keep = {variant, "strict_autism_f840", "strict_autism", "both"}
    sub = m.loc[m.variant.isin(keep)].copy()
    cols = {"id": L["model"][lang], "est": mlbl("estimand", lang), "src": mlbl("source", lang),
            "out": mlbl("outcome", lang), "off": mlbl("offset", lang), "pan": mlbl("panel", lang),
            "act": mlbl("activity", lang), "pos": mlbl("position", lang), "cov": mlbl("covariates", lang),
            "yrs": mlbl("years", lang), "n": mlbl("n_obs", lang),
            "apc": {"es": "CPA % (IC 95 %)", "en": "APC % (95% CI)"}[lang], "p": "p",
            "disp": {"es": "Dispersión de Pearson", "en": "Pearson dispersion"}[lang],
            "dw": "Durbin–Watson", "fam": mlbl("family", lang),
            "conv": {"es": "Convergió", "en": "Converged"}[lang], "note": L["note"][lang]}
    rows = []
    for _, c in sub.iterrows():
        rows.append({cols["id"]: txt(c.model_id, lang), cols["est"]: mlbl(c.estimand, lang),
                     cols["src"]: mlbl(c.source, lang), cols["out"]: mlbl(c.outcome, lang),
                     cols["off"]: mlbl(c.denominator_offset, lang), cols["pan"]: mlbl(c.panel, lang),
                     cols["act"]: mlbl(c.activity, lang), cols["pos"]: mlbl(c.position, lang),
                     cols["cov"]: mlbl(c.covariates, lang), cols["yrs"]: yspan(c.years, lang),
                     cols["n"]: num(c.n_obs, 0, lang),
                     # E78 imprime LAS MISMAS 220 especificaciones que `T7_models_cpa_full.csv` del módulo
                     # 06, en el mismo documento: el intervalo se compone con el MISMO ayudante compartido
                     # (`common.fmt_ci`, «a»/«to»), de modo que las dos impresiones de la misma fila salen
                     # carácter a carácter iguales y el guion del negativo no cae nunca contra una raya.
                     cols["apc"]: (f"{num(c.apc, 1, lang)} ({C.fmt_ci(c.apc_lo, c.apc_hi, 1, lang)})"
                                   if pd.notna(c.apc) else NE[lang]),
                     cols["p"]: C.fmt_p(c.p_value, lang) if pd.notna(c.p_value) else NE[lang],
                     cols["disp"]: num(c.dispersion, 2, lang), cols["dw"]: num(c.durbin_watson, 2, lang),
                     cols["fam"]: mlbl(c.model_family, lang),
                     cols["conv"]: L["yes"][lang] if str(c.converged).lower() in ("true", "1") else L["no"][lang],
                     cols["note"]: mnote(c.note_keys, c.note, lang)})
    f = pd.DataFrame(rows)
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = {"es": ("Unidad de análisis: año (o hospital-año en las especificaciones con efectos de hospital). Todas las "
                   "especificaciones son log-lineales cuasi-Poisson con desplazamiento log(denominador); el CPA es "
                   "100 × (exp(β) − 1) con IC 95 % de Wald, y se informan la dispersión de Pearson y el estadístico de "
                   "Durbin–Watson sobre residuos de devianza (débil con menos de ocho puntos, solo indicativo). "
                   "NINGUNA especificación estima un efecto de la Ley 21.545: una serie corta con pandemia, expansión "
                   "del reporte, cambios de códigos REM y mayor profundidad diagnóstica simultáneos no identifica un "
                   "efecto causal de política, y los modelos describen tendencias, no causas. Las tendencias de "
                   "fuentes distintas no se comparan como si midieran lo mismo. Los rótulos de estimando, fuente, "
                   "outcome, denominador, panel, modalidad, posición, covariables y familia provienen del registro "
                   "bilingüe de 06_models.py. "),
            "en": ("Unit of analysis: year (or hospital-year in specifications with hospital effects). All "
                   "specifications are quasi-Poisson log-linear with a log-denominator offset; the APC is "
                   "100 × (exp(β) − 1) with a Wald 95% CI, and Pearson dispersion and the Durbin–Watson statistic on "
                   "deviance residuals are reported (weak with fewer than eight points, indicative only). NO "
                   "specification estimates an effect of Law 21.545: a short series with simultaneous pandemic, "
                   "reporting expansion, REM code changes and rising coding depth does not identify a causal policy "
                   "effect, and the models describe trends, not causes. Trends from different sources are never "
                   "compared as if they measured the same thing. Labels for estimand, source, outcome, denominator, "
                   "panel, activity, position, covariates and family come from the bilingual registry in "
                   "06_models.py. ")}[lang]
    title = {"es": f"Tabla de modelos: todas las especificaciones ajustadas, con estimando, fuente, denominador, panel, covariables, CPA con IC 95 %, dispersión y diagnóstico — {vlabel}",
             "en": f"Model table: every fitted specification, with estimand, source, denominator, panel, covariates, APC with 95% CI, dispersion and diagnostics — {vlabel}"}[lang]
    reg.add(f"E{BASE_NUMBER + 18}_models_all_specifications", f, sub, title, note)
    return sub


# ===========================================================================
# E79 — controles de reproducción por familia
# ===========================================================================
def build_E79(I: Inputs, variant: str, lang: str, reg: Registry) -> pd.DataFrame:
    ctl = I.controls().copy()
    if ctl.empty:
        f = pd.DataFrame({L["family"][lang]: [NE[lang]]})
        reg.add(f"E{BASE_NUMBER + 19}_reproduction_controls_by_family", f, ctl,
                {"es": "Controles de reproducción por familia", "en": "Reproduction controls by family"}[lang], "")
        return ctl
    ctl["rel_diff_num"] = pd.to_numeric(ctl.rel_diff, errors="coerce")
    # Ninguna fila puede perderse: groupby descarta las claves vacías, de modo que una familia sin nombre se
    # rotula explícitamente en vez de desaparecer del recuento (véase Inputs.controls).
    if "name" not in ctl.columns:
        ctl["name"] = np.nan
    ctl["name"] = ctl["name"].fillna({"es": "(familia sin nombre en el archivo de controles)",
                                      "en": "(family unnamed in the controls file)"}[lang])
    grouped = (ctl.groupby(["module", "name"], observed=True, sort=True)
               .agg(n=("key", "size"),
                    ok=("status", lambda s: int((s == "ok").sum())),
                    differs=("status", lambda s: int((s == "differs").sum())),
                    info=("status", lambda s: int((s == "info").sum())),
                    max_rel=("rel_diff_num", "max"),
                    note=("note", lambda s: s.dropna().iloc[0] if s.notna().any() else ""))
               .reset_index())
    # La columna `note` de un control es la anotación de diagnóstico que cada módulo productor escribe en
    # SU idioma de trabajo, no una glosa redactada para el lector: imprimirla ponía texto en español dentro
    # del documento en inglés y texto en inglés dentro del español (defecto 7 de la revisión). Se conserva
    # completa, fila por fila, en la tabla numérica de esta misma tabla, y la nota lo declara.
    cols = {"mod": {"es": "Módulo", "en": "Module"}[lang], "fam": L["family"][lang],
            "n": {"es": "Controles", "en": "Checks"}[lang],
            "ok": {"es": "Reproducidos", "en": "Reproduced"}[lang],
            "df": {"es": "Difieren", "en": "Differ"}[lang],
            "inf": {"es": "Informativos", "en": "Informative"}[lang],
            "mx": {"es": "Máx. |diferencia relativa|", "en": "Max |relative difference|"}[lang]}
    rows = []
    for _, c in grouped.iterrows():
        rows.append({cols["mod"]: txt(c["module"], lang), cols["fam"]: txt(c["name"], lang),
                     cols["n"]: num(c["n"], 0, lang), cols["ok"]: num(c["ok"], 0, lang),
                     cols["df"]: num(c["differs"], 0, lang), cols["inf"]: num(c["info"], 0, lang),
                     cols["mx"]: (num(c["max_rel"], 4, lang) if pd.notna(c["max_rel"]) else NE[lang])})
    total = {cols["mod"]: {"es": "TOTAL", "en": "TOTAL"}[lang], cols["fam"]: "",
             cols["n"]: num(grouped["n"].sum(), 0, lang), cols["ok"]: num(grouped["ok"].sum(), 0, lang),
             cols["df"]: num(grouped["differs"].sum(), 0, lang), cols["inf"]: num(grouped["info"].sum(), 0, lang),
             cols["mx"]: num(grouped["max_rel"].max(), 4, lang)}
    f = pd.concat([pd.DataFrame(rows), pd.DataFrame([total])], ignore_index=True)
    note = {"es": ("Unidad: control de reproducción, es decir, una comparación entre un valor esperado prespecificado "
                   "(brief del estudio, DATA_REVIEW.md o una tabla tidy ya verificada) y el valor observado que "
                   "reproduce el pipeline desde los archivos fuente. Denominador: ninguno. «Difieren» no significa "
                   "error: significa que la diferencia está documentada y explicada en decision_log.md; ninguna cifra "
                   "se completa por plausibilidad y ninguna diferencia se corrige silenciosamente. «Informativos» son "
                   "controles sin valor esperado (recuentos y tiempos de ejecución). La tabla numérica contiene los "
                   "controles fila por fila, con módulo, clave, esperado, observado, diferencia absoluta y relativa, "
                   "y con la anotación de diagnóstico (columna note) que cada módulo productor escribe en su idioma "
                   "de trabajo: esa anotación no se traduce y por eso no se imprime en la tabla. "),
            "en": ("Unit: reproduction control, that is, a comparison between a pre-specified expected value (study "
                   "brief, DATA_REVIEW.md or an already-verified tidy table) and the observed value reproduced by the "
                   "pipeline from the source files. Denominator: none. 'Differ' does not mean error: it means the "
                   "difference is documented and explained in decision_log.md; no figure is filled in by plausibility "
                   "and no difference is silently corrected. 'Informative' controls have no expected value (counts and "
                   "runtimes). The numeric companion carries the controls row by row, with module, key, expected, "
                   "observed and absolute and relative difference, and with the diagnostic annotation (column note) "
                  "that each producing module writes in its own working language: that annotation is not translated "
                  "and is therefore not printed in the table. ")}[lang]
    # Rótulo de ÁMBITO: sin él, el TOTAL de esta tabla y el que imprime la lámina de flujo de datos se leen
    # como dos versiones contradictorias de la misma cifra (defecto 9 de la revisión). Difieren por una razón
    # concreta y declarada: esta tabla se construye antes de que este módulo escriba su propio archivo de
    # controles, de modo que cuenta un archivo menos.
    n_here, files_here = int(grouped["n"].sum()), int(ctl["control_file"].nunique())
    pipe = CR.totals(CR.PIPELINE)
    own = pipe["checks"] - n_here
    scope_note = {"es": (f"Ámbito de esta tabla: los {files_here} archivos de control presentes en outputs/controls/ cuando "
                         f"se compone la tabla, que son todos los del pipeline menos el de este módulo, todavía sin escribir "
                         f"(el orden de los archivos en el directorio no es el orden de ejecución), es decir "
                         f"{num(n_here, 0, lang)} comprobaciones. El total del pipeline completo, "
                         f"{CR.phrase(CR.PIPELINE, lang)}, es de {num(pipe['checks'], 0, lang)} comprobaciones y cuenta "
                         f"además los {num(own, 0, lang)} controles de este mismo módulo; son la misma clase de "
                         f"comprobación sobre un conjunto de archivos distinto y nunca se suman entre sí. "),
                  "en": (f"Scope of this table: the {files_here} control files present in outputs/controls/ when the table is "
                         f"composed, which are every pipeline file except this module's own, not yet written (the order of "
                         f"the files in the directory is not the order of execution), that is {num(n_here, 0, lang)} checks. "
                         f"The whole-pipeline total, {CR.phrase(CR.PIPELINE, lang)}, "
                         f"is {num(pipe['checks'], 0, lang)} checks and additionally counts the {num(own, 0, lang)} controls "
                         f"of this module itself; they are the same kind of check over a different set of files and are "
                         f"never added together. ")}[lang]
    note = scope_note + note if own > 0 else note
    title = {"es": f"Controles de reproducción por módulo y familia: número de comprobaciones, reproducidas, con diferencia documentada e informativas ({len(grouped)} familias)",
             "en": f"Reproduction controls by module and family: number of checks, reproduced, with a documented difference and informative ({len(grouped)} families)"}[lang]
    reg.add(f"E{BASE_NUMBER + 19}_reproduction_controls_by_family", f, ctl, title, note)
    return grouped


# ===========================================================================
# E80 — diccionario de datos de los archivos tidy
# ===========================================================================
def count_lines(path: Path) -> int:
    n = 0
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 22):
            n += chunk.count(b"\n")
    return max(n - 1, 0)


def pipeline_producer_map() -> dict[str, list[str]]:
    """Mapa nombre-de-archivo-tidy → scripts del pipeline que lo nombran (auditable, sin adivinar)."""
    texts = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in sorted(HERE.glob("*.py"))}
    out: dict[str, list[str]] = {}
    for path in sorted(CFG.TIDY.glob("*.csv")):
        stem = path.stem
        out[stem] = [name for name, text in texts.items()
                     if re.search(rf'["\']{re.escape(stem)}(\.csv)?["\']', text)]
    return out


def build_E80(I: Inputs, variant: str, lang: str, reg: Registry, cache: dict) -> pd.DataFrame:
    if "E80" not in cache:
        producers = pipeline_producer_map()
        rows = []
        for path in sorted(CFG.TIDY.glob("*.csv")):
            head = pd.read_csv(path, nrows=2000, low_memory=False)
            units = sorted({str(x) for x in head["unit"].dropna().unique()}) if "unit" in head.columns else []
            geo = sorted({str(x) for x in head["geography"].dropna().unique()}) if "geography" in head.columns else []
            den = sorted({str(x) for x in head["denominator"].dropna().unique()}) if "denominator" in head.columns else []
            scripts = sorted({str(x) for x in head["script"].dropna().unique()}) if "script" in head.columns else []
            # Los valores se guardan SIN recortar y sin traducir: la traducción y el recorte se hacen al
            # componer la tabla, para que el recorte no parta una glosa a mitad de palabra en un idioma y
            # no en el otro.
            rows.append({"file": path.name, "n_rows": count_lines(path), "n_columns": int(head.shape[1]),
                         "size_bytes": path.stat().st_size,
                         "columns": "|".join(map(str, head.columns)),
                         "unit_values": " | ".join(units[:3]),
                         "denominator_values": " | ".join(den[:3]),
                         "geography_values": " | ".join(geo[:3]),
                         "script_column": " | ".join(scripts[:3]),
                         "producing_pipeline_files": "|".join(producers.get(path.stem, []))})
        cache["E80"] = pd.DataFrame(rows)
    numeric = cache["E80"]
    cols = {"f": L["file"][lang], "r": L["rows"][lang], "c": {"es": "N.º de columnas", "en": "Number of columns"}[lang],
            "u": L["unit"][lang], "d": {"es": "Denominador declarado", "en": "Declared denominator"}[lang],
            "g": L["geography"][lang], "s": L["script"][lang], "co": L["columns"][lang]}
    def declared(value, lang, limit=160):
        """Cada valor declarado por el archivo, traducido y luego recortado a `limit` caracteres.

        Un archivo puede declarar el denominador como NÚMERO: `models_fitted.csv` trae 1.0, 10045585.0 y
        100789.0, que impresos con `str()` salían como el repr de coma flotante de Python —punto decimal
        inglés— idéntico en los dos idiomas. Se reconoce esa forma exacta (dígitos, punto, dígitos) y se
        escribe con el separador del idioma; un año («2024») no la cumple y se deja intacto."""
        parts = []
        for v in str(value).split(" | "):
            v = str(v).strip()
            if not v:
                continue
            if _FLOAT_REPR.fullmatch(v):
                x = float(v)
                parts.append(num(x, 0 if float(x).is_integer() else 2, lang))
            else:
                parts.append(stxt(v, lang)[:limit])
        return " | ".join(parts) if parts else NE[lang]

    rows = []
    for _, c in numeric.iterrows():
        rows.append({cols["f"]: c["file"], cols["r"]: num(c["n_rows"], 0, lang),
                     cols["c"]: num(c["n_columns"], 0, lang),
                     cols["u"]: declared(c["unit_values"], lang), cols["d"]: declared(c["denominator_values"], lang),
                     cols["g"]: declared(c["geography_values"], lang),
                     cols["s"]: txt(c["script_column"] or c["producing_pipeline_files"], lang),
                     cols["co"]: c["columns"]})
    f = pd.DataFrame(rows)
    note = {"es": ("Una fila por archivo tidy de outputs/tidy/. «Unidad», «denominador» y «geografía» se leen de las "
                   "propias columnas del archivo cuando existen (se muestran hasta tres valores distintos, con la "
                   "glosa bilingüe de labels.tidy_text y recortados a 160 caracteres); si el "
                   "archivo no las declara, la celda queda como «n/e» en lugar de suponer un valor. El script productor "
                   "se toma de la columna script del archivo y, si falta, de los archivos del pipeline que nombran el "
                   "archivo. Las filas se cuentan sobre el archivo completo; la unidad, el denominador y la geografía "
                   "se leen de las primeras 2.000 filas. Ningún archivo tidy sobrescribe datos fuente y todos se "
                   "escriben de forma atómica. "),
            "en": ("One row per tidy file in outputs/tidy/. 'Unit', 'denominator' and 'geography' are read from the "
                   "file's own columns when they exist (up to three distinct values shown, with the bilingual gloss "
                   "of labels.tidy_text and truncated to 160 characters); if the file does not "
                   "declare them, the cell stays 'n/e' rather than assuming a value. The producing script is taken from "
                   "the file's script column and, failing that, from the pipeline files that name the file. Rows are "
                   "counted over the whole file; unit, denominator and geography are read from the first 2,000 rows. No "
                   "tidy file overwrites source data and all are written atomically. ")}[lang]
    title = {"es": f"Diccionario de datos: los {len(numeric)} archivos tidy del estudio con sus columnas, unidad, denominador, geografía y script productor",
             "en": f"Data dictionary: the {len(numeric)} tidy files of the study with their columns, unit, denominator, geography and producing script"}[lang]
    reg.add(f"E{BASE_NUMBER + 20}_tidy_data_dictionary", f, numeric, title, note)
    return numeric


# ===========================================================================
# E81 — inventario de figuras, tablas y ecuaciones del proyecto
# ===========================================================================
# Se busca el identificador de cada archivo en TODOS los scripts del pipeline, no en una lista escrita a mano:
# una lista fija envejece en cuanto se añade un módulo (08d, 13, 14, 15, 15b) y entonces la columna «uso actual»
# declara como «solo registro suplementario» piezas que sí se producen y se citan, por ejemplo fig1_dataflow.
USAGE_FILES = sorted(p.name for p in HERE.glob("*.py") if p.name != "run_all.py")


# ---------------------------------------------------------------------------
# Resolución del rótulo desde el REGISTRO COMPARTIDO (nunca desde el título almacenado)
# ---------------------------------------------------------------------------
# El título que cada módulo productor guarda en captions.json / titles.json lleva un prefijo de rótulo
# heredado («Figure 1. », «Tabla S13. ») que quedó obsoleto con la renumeración del artículo: fig1_dataflow
# pasó a ser la Figura 1, T1_sources pasó a ser la Tabla S1 y las antiguas Tablas 2–8 pasaron a ser las
# Tablas 1–7. Imprimir ese prefijo aquí produce rótulos duplicados («dos Figura S3») e inválidos («Tabla
# S1b»). Por eso el inventario (a) borra el prefijo almacenado con la misma expresión regular que usa el
# constructor del documento y (b) vuelve a resolver el rótulo en el registro compartido:
#     figuras del artículo   -> prose_en.MAIN_FIGURES          (posición + 1)
#     tablas del artículo    -> prose_en.MAIN_TABLES           (posición + 1)
#     figuras suplementarias -> supplementary_material.FIGURE_ORDER  (posición + 1, con «S»)
#     tablas suplementarias  -> supplementary_material.TABLE_ORDER   (posición + 1, con «S»)
#     ecuaciones             -> equations_lancet.NUMBER        (los PNG se imprimen numerados en la
#                                                               metodología extendida)
# Un archivo que ninguno de esos registros lleva se declara «no se usa en los documentos»: nunca se le
# inventa un número. Un mismo identificador puede ser a la vez lámina y tabla (EF1_seasonality_monthly,
# E11_rem_a03_codes_by_era, …), de modo que la resolución y el título se buscan siempre por tipo de archivo.
USAGE_ARTICLE_FIG = "article_figure"
USAGE_ARTICLE_TAB = "article_table"
USAGE_SUPP_FIG = "supplementary_figure"
USAGE_SUPP_TAB = "supplementary_table"
USAGE_EQUATION = "extended_methodology_equation"
USAGE_NONE = "not_used"

USAGE_LABEL = {
    USAGE_ARTICLE_FIG: {"es": "lámina del artículo", "en": "article figure"},
    USAGE_ARTICLE_TAB: {"es": "tabla del artículo", "en": "article table"},
    USAGE_SUPP_FIG: {"es": "lámina suplementaria", "en": "supplementary figure"},
    USAGE_SUPP_TAB: {"es": "tabla suplementaria", "en": "supplementary table"},
    USAGE_EQUATION: {"es": "ecuación numerada de la metodología extendida",
                     "en": "numbered equation of the extended methodology"},
    USAGE_NONE: {"es": "no se usa en los documentos", "en": "not used in the documents"},
}
USAGE_WORD = {
    USAGE_ARTICLE_FIG: {"es": "Figura", "en": "Figure"},
    USAGE_ARTICLE_TAB: {"es": "Tabla", "en": "Table"},
    USAGE_SUPP_FIG: {"es": "Figura S", "en": "Figure S"},
    USAGE_SUPP_TAB: {"es": "Tabla S", "en": "Table S"},
    USAGE_EQUATION: {"es": "Ecuación", "en": "Equation"},
}


def _registry():
    """Registro compartido de numeración (importado una sola vez y cacheado)."""
    cached = getattr(_registry, "_cache", None)
    if cached is None:
        import prose_en as PEN                    # MAIN_FIGURES / MAIN_TABLES y el borrador de prefijos
        import supplementary_material as SM       # FIGURE_ORDER / TABLE_ORDER
        import equations_lancet as EQ             # NUMBER (ecuaciones de la metodología extendida)
        # Una ecuación puede ocuparse en varias líneas y entonces se compone en varios PNG (…_a, …_b, …):
        # todos llevan el MISMO número de ecuación y se distinguen por la letra de la parte, de modo que
        # dos PNG con el número 1 no son un rótulo duplicado sino las dos líneas de la ecuación 1.
        eq_stem: dict[str, tuple[int, str]] = {}
        for eq_key, eq_number in EQ.NUMBER.items():
            parts = EQ.paths_for(eq_key)
            for path in parts:
                letter = path.stem.rsplit("_", 1)[-1] if len(parts) > 1 else ""
                eq_stem[path.stem] = (int(eq_number), letter if len(letter) == 1 else "")
        cached = {
            "main_figures": list(PEN.MAIN_FIGURES),
            "main_tables": list(PEN.MAIN_TABLES),
            "supp_figures": list(SM.FIGURE_ORDER),
            "supp_tables": list(SM.TABLE_ORDER),
            "equations": eq_stem,
            # misma expresión regular que prose_en/prose_es aplican al construir el documento, de modo que
            # el inventario borra exactamente los mismos prefijos heredados que el constructor
            "strip": PEN._strip_prefix,
        }
        _registry._cache = cached
    return cached


def strip_stored_label(title: str) -> tuple[str, str]:
    """Devuelve (título sin prefijo, prefijo heredado que se borró)."""
    clean = _registry()["strip"](title or "")
    raw = (title or "").strip()
    stored = raw[:len(raw) - len(clean)].strip() if clean and raw.endswith(clean) else (raw if not clean else "")
    return clean, stored.rstrip(".: ").strip()


def resolve_label(stem: str, kind: str) -> tuple[str, int | None, str]:
    """(uso, número, parte) de un archivo según el registro compartido; (USAGE_NONE, None, '') si no lo lleva."""
    reg = _registry()
    if kind.startswith("figure"):
        if stem in reg["main_figures"]:
            return USAGE_ARTICLE_FIG, reg["main_figures"].index(stem) + 1, ""
        if stem in reg["supp_figures"]:
            return USAGE_SUPP_FIG, reg["supp_figures"].index(stem) + 1, ""
    elif kind.startswith("table"):
        if stem in reg["main_tables"]:
            return USAGE_ARTICLE_TAB, reg["main_tables"].index(stem) + 1, ""
        if stem in reg["supp_tables"]:
            return USAGE_SUPP_TAB, reg["supp_tables"].index(stem) + 1, ""
    elif kind == "equation" and stem in reg["equations"]:
        number, part = reg["equations"][stem]
        return USAGE_EQUATION, number, part
    return USAGE_NONE, None, ""


def label_text(usage: str, number, lang: str, part: str = "") -> str:
    """«Figura 2», «Table S49», «Ecuación 12 (a)» o el texto de «no se usa en los documentos»."""
    if usage == USAGE_NONE or number is None or (isinstance(number, float) and np.isnan(number)):
        return USAGE_LABEL[USAGE_NONE][lang]
    word = USAGE_WORD[usage][lang]
    suffix = f" ({part})" if isinstance(part, str) and part else ""
    return f"{word}{'' if word.endswith('S') else ' '}{int(number)}{suffix}"


def build_E81(I: Inputs, variant: str, lang: str, reg: Registry, cache: dict) -> pd.DataFrame:
    key = f"E81:{variant}:{lang}"
    if key not in cache:
        texts = {}
        for name in USAGE_FILES:
            p = HERE / name
            if p.is_file():
                texts[name] = p.read_text(encoding="utf-8", errors="replace")
        for name in ("prose_es.py", "prose_en.py", "prose_methods_extended.py", "values.py", "docx_builder.py"):
            p = LA / name
            if p.is_file():
                texts[name] = p.read_text(encoding="utf-8", errors="replace")
        base = CFG.OUT / variant / lang
        # Un identificador puede ser lámina y tabla a la vez, así que los títulos se guardan por tipo y no
        # en un único diccionario que se pisaría a sí mismo.
        meta_by_kind: dict[str, dict] = {"figure": {}, "table": {}}
        for jpath, group in ((base / "figures" / "captions.json", "figure"),
                             (base / "extra" / "figures" / "captions.json", "figure"),
                             (base / "tables" / "titles.json", "table"),
                             (base / "extra" / "tables" / "titles.json", "table")):
            if jpath.is_file():
                try:
                    meta_by_kind[group].update(json.loads(jpath.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, OSError):
                    pass
        rows = []
        groups = [("figure", base / "figures", "*.png"), ("figure_extra", base / "extra" / "figures", "*.png"),
                  ("table", base / "tables", "*.csv"), ("table_extra", base / "extra" / "tables", "*.csv"),
                  ("equation", CFG.OUT / "equations", "*.png")]
        for kind, folder, pattern in groups:
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob(pattern)):
                stem = path.stem
                if stem.endswith("_numeric") or path.name in ("captions.json", "titles.json"):
                    continue
                meta = meta_by_kind.get("figure" if kind.startswith("figure") else
                                        "table" if kind.startswith("table") else "", {}).get(stem, {})
                numeric = path.with_name(f"{stem}_numeric.csv")
                data_file = numeric.name if numeric.is_file() else ""
                if kind.startswith("figure"):
                    # una lámina figS10_… se empareja con las tablas cuyo prefijo es la misma etiqueta (S10_…)
                    tdir = base / ("extra/tables" if kind == "figure_extra" else "tables")
                    token = re.sub(r"^fig", "", stem).split("_")[0]
                    cands = sorted(p.name for p in tdir.glob(f"{token}_*.csv")
                                   if not p.stem.endswith("_numeric")) if tdir.is_dir() else []
                    data_file = "|".join(cands)
                used = [name for name, text in texts.items() if stem in text]
                clean_title, stored_label = strip_stored_label(meta.get("title") or meta.get("caption") or "")
                usage, number, part = resolve_label(stem, kind)
                rows.append({"asset": stem, "kind": kind,
                             "file": str(path.relative_to(CFG.OUT)),
                             "usage": usage, "number": number, "part": part,
                             "label": label_text(usage, number, lang, part),
                             "stored_label": stored_label,
                             "title": clean_title[:400],
                             "paired_data_file": data_file,
                             "referenced_in": "|".join(used) or ""})
        cache[key] = pd.DataFrame(rows)
    numeric = cache[key]
    cols = {"a": {"es": "Identificador del archivo", "en": "File identifier"}[lang], "k": L["kind"][lang],
            "n": {"es": "Rótulo en los documentos", "en": "Label in the documents"}[lang],
            "w": {"es": "Dónde se usa", "en": "Where it is used"}[lang],
            "f": L["file"][lang], "t": L["title"][lang],
            "d": {"es": "Tabla o archivo de datos asociado", "en": "Associated data file"}[lang],
            "u": L["used_in"][lang]}
    kind_lbl = {"figure": {"es": "Figura", "en": "Figure"}, "figure_extra": {"es": "Figura suplementaria adicional", "en": "Additional supplementary figure"},
                "table": {"es": "Tabla", "en": "Table"}, "table_extra": {"es": "Tabla suplementaria adicional", "en": "Additional supplementary table"},
                "equation": {"es": "Ecuación (PNG)", "en": "Equation (PNG)"}}
    rows = []
    for _, c in numeric.iterrows():
        rows.append({cols["a"]: c["asset"],
                     cols["k"]: kind_lbl.get(c["kind"], {"es": c["kind"], "en": c["kind"]})[lang],
                     cols["n"]: txt(c["label"], lang),
                     cols["w"]: USAGE_LABEL[c["usage"]][lang],
                     cols["f"]: c["file"], cols["t"]: txt(c["title"], lang),
                     cols["d"]: txt(c["paired_data_file"], lang),
                     cols["u"]: txt(c["referenced_in"], lang) if c["referenced_in"] else
                     {"es": "no citado por ningún script del manuscrito (solo registro suplementario)",
                      "en": "not cited by any manuscript script (supplementary registry only)"}[lang]})
    f = pd.DataFrame(rows)
    n_used = int((numeric["usage"] != USAGE_NONE).sum())
    n_free = int(len(numeric) - n_used)
    note = {"es": ("Inventario de todos los archivos de figura, tabla y ecuación presentes para esta variante y este "
                   "idioma en el momento en que se construyó la tabla; el inventario de las otras tres combinaciones "
                   "variante × idioma se comprueba en outputs/controls/16_extra_tables_controls.csv "
                   "(E81_assets_per_variant_language) y una diferencia significa que algún módulo productor todavía no "
                   "había escrito esa combinación. La columna «uso actual» se obtiene buscando el identificador del archivo en los "
                   "scripts del pipeline y de la prosa, de modo que es verificable y no una atribución editorial: una "
                   "figura o tabla que solo aparece en el registro suplementario se declara como tal. Los archivos "
                   "terminados en _numeric.csv son las versiones numéricas de cada tabla formateada y no se listan "
                   "como piezas independientes. El «rótulo en los documentos» y la columna «dónde se usa» NO se copian "
                   "del título almacenado por el módulo productor —que conserva el número provisional anterior a la "
                   "renumeración del artículo— sino que se resuelven en el registro compartido de numeración: las "
                   "láminas y tablas del artículo en prose_en.MAIN_FIGURES y prose_en.MAIN_TABLES, las suplementarias "
                   "en supplementary_material.FIGURE_ORDER y supplementary_material.TABLE_ORDER, y las ecuaciones en "
                   "equations_lancet.NUMBER; el prefijo heredado del título se borra con la misma expresión regular "
                   f"que aplica el constructor del documento. {n_used} archivos se imprimen en los documentos y "
                   f"{n_free} no: un archivo que el registro no lleva se declara «no se usa en los documentos» y nunca "
                   "recibe un número inventado (es el caso de las alternativas descartadas de una misma casilla, por "
                   "ejemplo figS3_hospital_effects frente a figS3_grd_hospital_effects). Un mismo identificador puede "
                   "ser a la vez lámina y tabla, y entonces cada fila resuelve su rótulo y su título según el tipo de "
                   "archivo. Las láminas y tablas suplementarias se numeran en el orden en que aparecen en la parte "
                   "suplementaria, que es temático, y el artículo las cita por ese número. "),
            "en": ("Inventory of every figure, table and equation file present for this variant and language at the "
                   "moment the table was built; the inventory of the other three variant × language combinations is "
                   "checked in outputs/controls/16_extra_tables_controls.csv (E81_assets_per_variant_language) and a "
                   "difference means that some producing module had not yet written that combination. "
                   "The 'current use' column is obtained by searching the file identifier in the pipeline and prose "
                   "scripts, so it is verifiable and not an editorial attribution: a figure or table that appears only "
                   "in the supplementary registry is declared as such. Files ending in _numeric.csv are the numeric "
                   "companions of each formatted table and are not listed as separate items. The 'label in the "
                   "documents' and 'where it is used' columns are NOT copied from the title stored by the producing "
                   "module — which keeps the provisional number that preceded the renumbering of the article — but are "
                   "resolved in the shared numbering registry: article figures and tables in prose_en.MAIN_FIGURES and "
                   "prose_en.MAIN_TABLES, supplementary ones in supplementary_material.FIGURE_ORDER and "
                   "supplementary_material.TABLE_ORDER, and equations in equations_lancet.NUMBER; the inherited prefix "
                   "of the stored title is stripped with the same regular expression the document builder applies. "
                   f"{n_used} files are printed in the documents and {n_free} are not: a file the registry does not "
                   "carry is declared 'not used in the documents' and never receives an invented number (this is the "
                   "case of the discarded alternatives for one slot, for example figS3_hospital_effects against "
                   "figS3_grd_hospital_effects). One identifier can be both a plate and a table, and then each row "
                   "resolves its label and its title according to the kind of file. Supplementary figures and tables "
                   "are numbered in the order in which they appear in the supplementary part, which is thematic, and "
                   "the article cites them by that number. ")}[lang]
    title = {"es": f"Inventario de todas las figuras, tablas y ecuaciones del proyecto ({len(numeric)} archivos) con su ruta, su rótulo actual resuelto en el registro compartido, dónde se usa, su título, su archivo de datos asociado y los scripts que lo citan",
             "en": f"Inventory of every figure, table and equation of the project ({len(numeric)} files) with its path, its current label resolved in the shared registry, where it is used, its title, its associated data file and the scripts that cite it"}[lang]
    reg.add(f"E{BASE_NUMBER + 21}_project_asset_inventory", f, numeric, title, note)
    return numeric


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------
class Controls:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, name, key, expected, observed, note="", tol=0.0):
        exp = None if expected is None else float(expected) if isinstance(expected, (int, float, np.integer, np.floating)) else expected
        obs = None if observed is None else float(observed) if isinstance(observed, (int, float, np.integer, np.floating)) else observed
        abs_diff = rel_diff = None
        status = "info"
        if isinstance(exp, float) and isinstance(obs, float):
            abs_diff = abs(obs - exp)
            rel_diff = abs_diff / abs(exp) if exp else (0.0 if abs_diff == 0 else np.inf)
            status = "ok" if (abs_diff <= tol or rel_diff <= tol) else "differs"
        elif exp is not None and obs is not None:
            status = "ok" if str(exp) == str(obs) else "differs"
            abs_diff = rel_diff = 0.0 if status == "ok" else np.nan
        self.rows.append({"name": name, "key": key, "expected": exp, "observed": obs,
                          "abs_diff": abs_diff, "rel_diff": rel_diff, "status": status, "note": note})

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff",
                                                "status", "note"])


def build_controls(I: Inputs, per_variant: dict, names_written: list[str], n_files: int) -> pd.DataFrame:
    ctl = Controls()
    ys = I.tidy("grd_year_summary")
    ra = I.tidy("rem_pathway_annual")

    for variant, tabs in per_variant.items():
        # E60 reproduce grd_year_summary y los controles prespecificados
        base = ys.loc[(ys.variant == variant) & (ys.panel == "observed") & (ys.activity == "all") &
                      (ys.position == "any")].set_index("year").n_episodes_f84
        if variant == "con_rett":
            for y, exp in CFG.CONTROLS["grd_f84_any"].items():
                ctl.add("E60_grd_f84_any_vs_config", f"{variant}:{y}", exp, base.get(y),
                        "serie anual de E60 frente a config.CONTROLS (fuente: grd_year_summary.csv)")
        e61 = tabs["E61"]
        for y in sorted(base.index):
            ctl.add("E61_hospital_sum_equals_year_summary", f"{variant}:{y}", base.get(y),
                    e61.loc[e61.year == y, "n_f84_any"].sum(),
                    "suma de E61 sobre todos los hospitales = grd_year_summary (panel observado, todas las modalidades, cualquier posición)")
        e62 = tabs["E62"]
        for y in sorted(base.index):
            ctl.add("E62_region_sum_equals_year_summary", f"{variant}:{y}", base.get(y),
                    e62.loc[e62.year == y, "n_episodes"].sum(),
                    "suma de E62 sobre todas las regiones (incluida la fila no enlazada) = grd_year_summary")
        e63 = tabs["E63"]
        for y in sorted(base.index):
            ctl.add("E63_age_sum_equals_year_summary", f"{variant}:{y}", base.get(y),
                    e63.loc[e63.year == y, "n_episodes"].sum(),
                    "suma de E63 sobre edad y sexo = grd_year_summary")
        # E69 reproduce rem_pathway_annual y los controles REM prespecificados
        e69 = tabs["E69"]
        a05 = e69.loc[(e69.module == "A05") & (e69.variant == "strict_autism") & (e69.domain == "entry")]
        for y, exp in CFG.CONTROLS["a05_autism_entries"].items():
            obs = a05.loc[a05.year == y, "total"]
            ctl.add("E69_a05_autism_entries", f"{variant}:{y}", exp, obs.iloc[0] if len(obs) else None,
                    "ingresos A05 de autismo estricto en E69 frente a config.CONTROLS")
        p2 = e69.loc[(e69.module == "P2") & (e69.code == CFG.P2_TEA) & (e69.measure == "december_stock")]
        for y, exp in CFG.CONTROLS["p2_tea_december"].items():
            obs = p2.loc[p2.year == y, "total"]
            ctl.add("E69_p2_tea_december", f"{variant}:{y}", exp, obs.iloc[0] if len(obs) else None,
                    "stock P2 TEA de diciembre en E69 frente a config.CONTROLS")
        for y, exp in CFG.CONTROLS["p2_establishments_december"].items():
            obs = p2.loc[p2.year == y, "n_reporting_establishments"]
            ctl.add("E69_p2_establishments_december", f"{variant}:{y}", exp, obs.iloc[0] if len(obs) else None,
                    "establecimientos que reportan P2 en diciembre")
        for y, exp in CFG.CONTROLS["a28_primary"].items():
            s = e69.loc[(e69.module == "A28") & (e69.code == CFG.A28["primary"]) & (e69.year == y), "total"]
            ctl.add("E69_a28_primary", f"{variant}:{y}", exp, s.iloc[0] if len(s) else None,
                    "ingresos A28 de rehabilitación primaria")
        # E70 reproduce el total A05 del año a partir de la desagregación por edad y sexo
        e70 = tabs["E70"]
        strict_entry = ra.loc[(ra.module == "A05") & (ra.variant == "strict_autism") & (ra.domain == "entry")]
        tot70 = e70.loc[(e70.category == "autism") & (e70.flow == "entry") & (e70.age_group == "total")]
        if len(tot70):
            for y in sorted(tot70.year.unique()):
                exp = strict_entry.loc[strict_entry.year == y, "total"]
                ctl.add("E70_a05_age_sex_total", f"{variant}:{y}", exp.iloc[0] if len(exp) else None,
                        tot70.loc[tot70.year == y, "count"].sum(),
                        "suma por sexo de la fila 'total' de edad en E70 = total anual COL01 de rem_pathway_annual; "
                        "diferencia documentada en decision_log.md (2026-09-04, 02_rem_pathway): en unas pocas filas "
                        "del A05 las 34 celdas de edad no suman COL01, de modo que la serie por edad excede a COL01 "
                        "en 1 en 2022, 2024 y 2025; no se corrige ni se imputa")
        # E71 suma regional = total nacional de diciembre del mismo código
        e71 = tabs["E71"]
        if len(e71):
            p2b = e71.loc[e71.block == "P2_tea"]
            for y, exp in CFG.CONTROLS["p2_tea_december"].items():
                ctl.add("E71_p2_region_sum", f"{variant}:{y}", exp,
                        p2b.loc[p2b.year == y, "december_total"].sum(),
                        "suma regional del stock P2 TEA de diciembre = total nacional")
        # E73 capas nacionales frente a config.CONTROLS
        e73 = tabs["E73"]
        nat = e73.loc[e73.dimension.isin(["Total nacional", "National total"])]
        for layer, ckey in (("fonasa", "fonasa_beneficiaries_december"), ("aps", "aps_enrolled_december"),
                            ("isapre", "isapre_beneficiaries_december"), ("ine", "ine_population_national")):
            for y, exp in CFG.CONTROLS[ckey].items():
                s = nat.loc[(nat.layer == layer) & (nat.year == y), "value"]
                ctl.add(f"E73_{layer}_national", f"{variant}:{y}", exp, s.iloc[0] if len(s) else None,
                        "capa nacional de E73 frente a config.CONTROLS (fuente: coverage_layers_year.csv)")
        # E75 encuestas: n y casos sin ponderar
        e75 = tabs["E75"]
        endide_child = e75.loc[e75.domain.str.contains("NNA 2-17: autismo reportado", na=False) &
                               (e75.subgroup == "total") & (e75.estimate_type == "primary")]
        if len(endide_child):
            ctl.add("E75_endide_children_cases", variant, CFG.CONTROLS["endide_unweighted"]["children"],
                    endide_child.cases.iloc[0], "casos sin ponderar de NNA con autismo reportado (ENDIDE 2022)")
        encavi = e75.loc[e75.survey.str.startswith("ENCAVI", na=False) & (e75.subgroup == "total") &
                         (e75.estimate_type == "primary")]
        if len(encavi):
            ctl.add("E75_encavi_cases", variant, CFG.CONTROLS["encavi_unweighted"]["positive"],
                    encavi.cases.iloc[0], "respuestas positivas sin ponderar (ENCAVI 2023–2024)")
            ctl.add("E75_encavi_domain_n", variant, CFG.CONTROLS["encavi_unweighted"]["n"] - 106, encavi.n.iloc[0],
                    "n del dominio primario de 15 años o más con respuesta válida (ENCAVI 2023–2024). El control "
                    "prespecificado de 16.590 son las filas de la base; las 106 respuestas «No sabe/No responde» "
                    "quedan fuera del dominio primario y se analizan como sensibilidad, según "
                    "04_surveys_controls.csv")
            ctl.add("E75_encavi_file_rows", variant, CFG.CONTROLS["encavi_unweighted"]["n"], None,
                    "filas de la base ENCAVI de 15 años o más (control informativo; verificado en el módulo 04)")
        # E76 educación
        e76 = tabs["E76"]
        for series, ckey in (("pie_tea_strict", "pie_tea_strict"), ("pie_tea_asperger", "pie_tea_asperger"),
                             ("pie_harmonised", "pie_harmonised")):
            for y, exp in CFG.CONTROLS[ckey].items():
                s = e76.loc[(e76.series == series) & (e76.year == y), "value"]
                if not len(s) and series == "pie_harmonised":
                    s = e76.loc[(e76.series == "pie_harmonised_sinaces") & (e76.year == y), "value"]
                ctl.add(f"E76_{series}", f"{variant}:{y}", exp, s.iloc[0] if len(s) else None,
                        "serie PIE de E76 frente a config.CONTROLS")
        # E78 modelos
        e78 = tabs["E78"]
        ctl.add("E78_models_rows", variant, None, len(e78),
                "especificaciones incluidas para esta variante (models_summary.csv)")
    ctl.add("tables_per_variant_language", "n", len(TABLE_NAMES),
            len(per_variant[list(per_variant)[0]]["names"]), "tablas formateadas escritas por variante e idioma")
    ctl.add("files_written", "n", None, n_files, "archivos escritos (formateado + numérico + titles.json)")
    # E81 es una fotografía del árbol de salidas: si un módulo productor (13, 14, 15, 15b) todavía no ha escrito
    # una combinación variante × idioma, el inventario de esa combinación queda corto. El control lo hace visible
    # en vez de dejar que la nota afirme una identidad no comprobada.
    counts = {}
    for v in CFG.VARIANTS:
        for lg in CFG.LANGUAGES:
            f81 = extra_dir(v, lg) / f"E{BASE_NUMBER + 21}_project_asset_inventory_numeric.csv"
            if f81.is_file():
                counts[f"{v}/{lg}"] = int(len(pd.read_csv(f81, dtype=str)))
    if counts:
        ref = max(counts.values())
        for k, n_assets in counts.items():
            ctl.add("E81_assets_per_variant_language", k, ref, n_assets,
                    "archivos inventariados en E81 frente al máximo de las cuatro combinaciones; una diferencia "
                    "indica que un módulo productor no había escrito esa combinación cuando se construyó E81, "
                    "no un error de este módulo: vuelva a ejecutar 16_extra_tables.py después de 13, 14, 15 y 15b")
    # Los rótulos de E81 se resuelven en el registro compartido, nunca en el título almacenado por el módulo
    # productor. Estos controles comprueban esa resolución: cada ítem del registro aparece exactamente una vez,
    # ningún rótulo se repite, ningún título conserva el prefijo heredado y ninguna fila sin registro lleva número.
    # Un rótulo heredado termina siempre en punto o en dos puntos («Table S9. », «Figure 1. »): esa es la firma
    # que se busca. Una referencia cruzada dentro del propio título («Figure 4 series per 100,000 population»)
    # no lleva ese delimitador, no es un prefijo y el constructor del documento tampoco la borra.
    stale_re = (r"^(?:Figure|Figura|Table|Tabla|Plate|Lámina)\s+[A-Za-z]{0,3}\d+[a-zA-Z]?\s*"
                r"(?:\([^)]*\)\s*)?[.:]")
    R81 = _registry()
    expected_items = (len(R81["main_figures"]) + len(R81["main_tables"])
                      + len(R81["supp_figures"]) + len(R81["supp_tables"]))
    for v in CFG.VARIANTS:
        for lg in CFG.LANGUAGES:
            f81 = extra_dir(v, lg) / f"E{BASE_NUMBER + 21}_project_asset_inventory_numeric.csv"
            if not f81.is_file():
                continue
            e81 = pd.read_csv(f81)
            if not len(e81) or "usage" not in e81.columns:
                continue
            e81["part"] = e81["part"].fillna("") if "part" in e81.columns else ""
            key = f"{v}/{lg}"
            used_rows = e81.loc[e81["usage"] != USAGE_NONE]
            doc_rows = used_rows.loc[used_rows["usage"] != USAGE_EQUATION]
            ctl.add("E81_registry_items_inventoried", key, expected_items,
                    len(doc_rows.drop_duplicates(subset=["usage", "number"])),
                    "ítems del registro compartido (MAIN_FIGURES + MAIN_TABLES + FIGURE_ORDER + TABLE_ORDER) que "
                    "E81 encuentra como archivo producido; una diferencia significa que falta el archivo de un "
                    "ítem citado")
            ctl.add("E81_duplicate_labels", key, 0,
                    int(len(used_rows) - len(used_rows.drop_duplicates(subset=["usage", "number", "part"]))),
                    "rótulos repetidos en E81; con la resolución por registro debe ser cero (antes se repetían "
                    "«Figura S3», «Figura S4», «Figura S7», «Tabla S7», «Tabla S8» y «Tabla S13»); las dos o tres "
                    "líneas de una misma ecuación llevan el mismo número y se distinguen por la letra de la parte")
            ctl.add("E81_equations_numbered", key, len(R81["equations"]),
                    int((used_rows["usage"] == USAGE_EQUATION).sum()),
                    "PNG de ecuación inventariados frente a los que declara equations_lancet.paths_for; cada uno "
                    "lleva el número de equations_lancet.NUMBER y la letra de su línea")
            titles = e81["title"].fillna("").astype(str)
            ctl.add("E81_titles_with_stale_prefix", key, 0, int(titles.str.match(stale_re).sum()),
                    "títulos de E81 que todavía empiezan por un rótulo heredado; el inventario los borra con la "
                    "misma expresión regular que aplica el constructor del documento")
            ctl.add("E81_unused_assets_without_number", key, 0,
                    int(e81.loc[e81["usage"] == USAGE_NONE, "number"].notna().sum()),
                    "archivos fuera del registro a los que se les hubiera asignado un número; debe ser cero: se "
                    "declaran «no se usa en los documentos»")
            # Solo informativo y NO un error de este módulo: el cuerpo de algunos títulos guardados por los
            # módulos productores cita un número de lámina del artículo anterior a la renumeración
            # (F4_triangulation_series, F3_rem_pathway_data). El prefijo no se toca porque no es un prefijo.
            body = int(titles.str.contains(r"\b(?:Figure|Figura)\s+\d\b", regex=True).sum())
            ctl.add("E81_titles_citing_a_main_figure_in_the_body", key, None, body,
                    "títulos cuyo CUERPO cita una lámina del artículo por número; corresponde a los módulos "
                    "productores (09a/09b, 08b/08c) revisar que ese número siga siendo el vigente")
    ctl.add("numbering_base", "E", BASE_NUMBER, BASE_NUMBER,
            "los módulos 13–15 aún no han producido tablas E; esta serie se numera desde E60, como pide el encargo")
    ctl.add("names_match_registry", "set", "|".join(TABLE_NAMES), "|".join(sorted(set(names_written))),
            "los nombres escritos coinciden exactamente con la lista canónica TABLE_NAMES del módulo")
    ctl.add("distinct_table_names", "n", len(TABLE_NAMES), len(set(names_written)),
            "nombres distintos de tabla del módulo; cada nombre se escribe una vez por combinación "
            "variante × idioma, de modo que la lista completa los repite")
    return ctl.frame()


#: La medición de la ventana de años va al RUNLOG, no a los controles. Un control nuevo cambia el recuento
#: de `<módulo>_controls.csv`, y `outputs/controls/controls_summary.csv` —la fotografía que consolida el
#: módulo 07— dejaría de coincidir fila a fila con él: `tests/test_self_counts.py` lo comprueba y falla, y
#: el total de comprobaciones del pipeline que imprime el apéndice cambiaría por una corrección de
#: tipografía. La medición se escribe entera en el runlog y, si el residuo en prosa no es cero, el módulo
#: lo AVISA por pantalla. Promoverla a control es barato el día que se vuelva a consolidar el módulo 07.
def year_window_report(variants) -> dict:
    """Intervalos convertidos, conservados y residuo, releyendo los archivos ya escritos.

    Desde la fase 4j mide TODO intervalo numérico de lectura (banda de edad, tramo, decil y ventana de
    años), no sólo la ventana: es la misma regla de `common` con la que se escribieron."""
    rep: dict = {"converted_by_variant_language": {k: dict(v) for k, v in sorted(YSPAN_COUNTS.items())},
                 "hyphen_left_in_prose": {}, "hyphen_left_in_machine_keys": {}}
    for variant in sorted(variants):
        for lang in CFG.LANGUAGES:
            tdir = extra_dir(variant, lang)
            prose = machine = 0
            for name in TABLE_NAMES:
                path = tdir / f"{name}.csv"
                if not path.is_file():
                    continue
                # celda a celda con el lector de CSV: leer el archivo como texto plano pegaría el final de
                # una celda con el principio de la siguiente por la coma y clasificaría mal la palabra.
                with path.open(encoding="utf-8-sig", newline="") as fh:
                    for row in csv.reader(fh):
                        for cell in row:
                            prose += C.count_hyphen_ranges(cell)
                            machine += C.count_kept_hyphens(cell)
            rep["hyphen_left_in_prose"][f"{variant}|{lang}"] = prose
            rep["hyphen_left_in_machine_keys"][f"{variant}|{lang}"] = machine
    return rep


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def existing_numbers() -> dict[str, list[str]]:
    """Números E ya ocupados por otros módulos en las carpetas extra/tables."""
    used: dict[str, list[str]] = {}
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            path = extra_dir(variant, lang) / "titles.json"
            if not path.is_file():
                continue
            try:
                titles = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for name in titles:
                m = re.match(r"^E(\d+)_", name)
                if m:
                    used.setdefault(m.group(1), []).append(f"{variant}/{lang}:{name}")
    return used


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=list(CFG.VARIANTS))
    ap.add_argument("--langs", nargs="+", default=list(CFG.LANGUAGES))
    args = ap.parse_args(argv)

    started = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    t_start = time.perf_counter()
    used = existing_numbers()
    mine_numbers = {str(BASE_NUMBER + i) for i in range(len(TABLE_NAMES))}
    # una colisión real es un número de esta serie ocupado por un NOMBRE que no es de este módulo
    clash = {k: [x for x in v if x.split(":", 1)[1] not in TABLE_NAMES]
             for k, v in used.items() if k in mine_numbers}
    clash = {k: v for k, v in clash.items() if v}
    prior = sorted({int(k) for k in used})
    log(f"números E ya presentes en extra/tables: {prior or '(ninguno)'}; esta corrida usa "
        f"E{BASE_NUMBER}–E{BASE_NUMBER + 21}")
    if clash:
        log(f"AVISO: colisión de numeración con otro módulo: {clash}")

    I = Inputs()
    cache: dict = {}
    per_variant: dict[str, dict] = {}
    all_names: list[str] = []
    n_files = 0
    for variant in args.variants:
        for lang in args.langs:
            t0 = time.perf_counter()
            reg = Registry(variant, lang)
            tabs = {}
            tabs["E60"] = build_E60(I, variant, lang, reg)
            tabs["E61"] = build_E61(I, variant, lang, reg)
            tabs["E62"] = build_E62(I, variant, lang, reg)
            tabs["E63"] = build_E63(I, variant, lang, reg)
            tabs["E64"] = build_E64(I, variant, lang, reg)
            tabs["E65"] = build_E65(I, variant, lang, reg)
            tabs["E66"] = build_E66(I, variant, lang, reg)
            tabs["E67"] = build_E67(I, variant, lang, reg)
            tabs["E68"] = build_E68(I, variant, lang, reg)
            tabs["E69"] = build_E69(I, variant, lang, reg)
            tabs["E70"] = build_E70(I, variant, lang, reg)
            tabs["E71"] = build_E71(I, variant, lang, reg)
            tabs["E72"] = build_E72(I, variant, lang, reg)
            tabs["E73"] = build_E73(I, variant, lang, reg)
            tabs["E74"] = build_E74(I, variant, lang, reg)
            tabs["E75"] = build_E75(I, variant, lang, reg)
            tabs["E76"] = build_E76(I, variant, lang, reg)
            tabs["E77"] = build_E77(I, variant, lang, reg)
            tabs["E78"] = build_E78(I, variant, lang, reg)
            tabs["E79"] = build_E79(I, variant, lang, reg)
            tabs["E80"] = build_E80(I, variant, lang, reg, cache)
            tabs["E81"] = build_E81(I, variant, lang, reg, cache)
            reg.flush()
            tabs["names"] = sorted(reg.titles)
            all_names.extend(reg.titles)
            n_files += len(reg.written)
            per_variant.setdefault(variant, tabs)
            log(f"{variant}/{lang}: {len(reg.titles)} tablas, {len(reg.written)} archivos "
                f"({time.perf_counter() - t0:.1f} s)")

    controls = build_controls(I, per_variant, all_names, n_files)
    yw = year_window_report(per_variant)
    left = {k: v for k, v in yw["hyphen_left_in_prose"].items() if v}
    log(f"ventana de años: {sum(c['converted'] for c in YSPAN_COUNTS.values())} convertidas a raya, "
        f"{sum(c['kept_machine'] for c in YSPAN_COUNTS.values())} conservadas con guion en claves de máquina")
    if left:
        log(f"AVISO: quedan ventanas de años con guion FUERA de una clave de máquina: {left}")
    ctl_path = C.atomic_write_csv(controls, CONTROLS_DIR / f"{MODULE}_controls.csv")
    runlog = {"module": MODULE, "script": SCRIPT, "started_utc": started,
              "seconds_total": round(time.perf_counter() - t_start, 1),
              "args": vars(args), "numbering_base": BASE_NUMBER,
              "existing_E_numbers_before_run": prior,
              "tables_per_variant_language": sorted(per_variant[args.variants[0]]["names"]),
              "files_written": n_files,
              "controls_status": controls.status.value_counts().to_dict(),
              "controls_path": str(ctl_path),
              "year_windows": yw,
              "pandas": pd.__version__, "numpy": np.__version__, "python": sys.version.split()[0]}
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    differs = controls.loc[controls.status == "differs"]
    if len(differs):
        print(differs.to_string(index=False, max_colwidth=80), flush=True)
    log(f"listo en {runlog['seconds_total']:,.1f} s; {n_files} archivos; controles: {runlog['controls_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
