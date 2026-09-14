#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08d_figure_dataflow.py — Figura 1 del artículo: ESQUEMA CONCEPTUAL de qué se hizo con cada base de
datos, por variante (`con_rett`, `sin_rett`) e idioma (`es`, `en`).

No es una tabla de fichas ni un texto ilustrado: es un DIAGRAMA DE FLUJO que se entiende de un vistazo y
sin instrucciones. Seis carriles, uno por familia de datos, cada uno leído de izquierda a derecha:

    base de datos  →  paso  →  paso  →  lo que entrega

Tres formas y ninguna más, cada una con un solo significado:

  * CILINDRO         una base de datos. Lleva su identificación, su periodo y un distintivo con UNA
                     palabra que dice qué es una fila: «registro» (cuadrado), «persona» (círculo) o
                     «comuna» (hexágono), que son las tres unidades de análisis del estudio.
  * CAJA REDONDEADA  un paso de tratamiento realmente aplicado a esa base, en cinco palabras o menos.
  * BLOQUE CON PUNTA lo que el carril entrega, en seis palabras o menos.

Sobre las flechas van solo CIFRAS: la n a la entrada, la n tras la selección de autismo y el extremo de
la serie que el carril produce. En rojo, y solo en rojo, lo que se excluye o nunca se suma, con su
número. Una flecha cortada por dos trazos marca el punto donde cambia la definición, con tres o cuatro
palabras al pie. La banda de trazos rojos que separa los carriles dice, UNA sola vez, la regla que
gobierna la lámina entera: sin enlace individual entre sistemas.

La lámina no lleva bloque de «cómo leer», ni frases completas, ni párrafos explicativos, ni símbolo
alguno que necesite leyenda; tampoco nombres de archivo, de script ni de columna, ni referencia a un
repositorio de datos. Todo lo que un lector pueda necesitar además está en el PIE de la figura: qué
significan las unidades, qué significan las marcas, la regla de no enlace, dónde cambia la definición de
una serie y de dónde salen las cifras. El pie NO puede crecer sin límite: se compone bajo una lámina de
245 mm en A4 y dispone de 3,876 cm —trece líneas al suelo de 7,0 pt de la leyenda, contando el título,
que va en el mismo párrafo—; pasado eso se parte y la cola ocupa una página propia rotulada «Figura 1
(continuación)». Por eso el pie no recita las cifras: las que el esquema imprime se leen en el esquema y
las que no, en la tabla de recuentos que lo acompaña. Véase la docstring de `caption()`.

Presupuesto de texto, comprobado en tiempo de ejecución y registrado en el runlog: excluidos los números
y los seis títulos de carril, la lámina no pasa de 120 palabras y ninguna caja pasa de 8.

Salidas:
  outputs/<variante>/<idioma>/figures/fig1_dataflow.png          lámina, 180 × 245 mm, 600 dpi, dibujada 1:1
  outputs/<variante>/<idioma>/figures/captions.json              (fusionado) {nombre: {title, caption}}
  outputs/<variante>/<idioma>/extra/tables/T_dataflow_counts.csv (+ _numeric.csv y titles.json fusionado)
  outputs/tidy/dataflow_counts.csv                               una fila por cifra del carril, trazable
  outputs/controls/08d_figure_dataflow_controls.csv              esperado (fuente autoritativa) vs observado
  outputs/controls/08d_figure_dataflow_runlog.json               registro de ejecución

Ninguna cifra está escrita a mano: todas se leen en tiempo de ejecución de outputs/tidy/*.csv y de
values_<variante>.json para la variante en curso. Si una cifra de la lámina no coincide con su fuente
autoritativa, el módulo termina con error. La tabla de recuentos que acompaña a la figura conserva TODAS
las cifras registradas y marca cuáles se imprimen en el esquema y cuáles solo lo sostienen.

La composición también se comprueba aquí dentro: `common.check_layout` mide las cuatro láminas terminadas
sobre el renderizador real (texto fuera del lienzo, texto impreso sobre texto) y el módulo termina con
error si alguna trae defectos. La lámina es un diagrama de un solo lienzo, de modo que se la exime de la
regla de tres filas por dos columnas —`plate_declare(..., grid=None)`— y de ninguna otra; el piso de 6 pt
lo vigila `MIN_FS_USED`.

Ejecución: `python3 lancet_americas/pipeline/08d_figure_dataflow.py` desde la raíz del repositorio.
No modifica config.py, common.py ni labels.py.
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
from prose_en import main_figure_label  # noqa: E402

MODULE = "08d_figure_dataflow"
CTRL_DIR = CFG.OUT / "controls"
SCRIPT = "lancet_americas/pipeline/08d_figure_dataflow.py"
VARIANTS = ["con_rett", "sin_rett"]
LANGS = CFG.LANGUAGES
FIG_NAME = "fig1_dataflow"
TABLE_NAME = "T_dataflow_counts"

# ---------------------------------------------------------------------------
# Geometría del esquema, en milímetros (1 unidad de datos = 1 mm), dibujado 1:1
# ---------------------------------------------------------------------------
W_MM, H_MM = 180.0, 245.0
MM_PER_IN = 25.4
PT_MM = 0.3528

X0, X1 = 3.5, 176.5                      # márgenes del contenido
LANES_TOP, LANES_BOT = 241.6, 3.2        # franja que ocupan los seis carriles
SEP_MIN, SEP_MAX = 4.4, 9.0              # separación entre carriles: ahí va la barrera de no enlace

DB_W = 33.0                              # ancho del cilindro de base de datos
YIELD_W = 34.0                           # ancho del bloque de resultado
YIELD_TIP = 4.4                          # punta del bloque de resultado
STEP_W_MAX = 40.0
STEP_W_MIN = 15.0
ARROW_MIN = 8.5                          # flecha mínima entre dos elementos
BREAK_ROOM = 6.2                         # espacio que la marca de quiebre necesita sobre la flecha
DRUM_E = 3.0                             # alto de las elipses del cilindro
PAD = 1.30                               # relleno interior de las cajas
LINE_FACTOR = 1.18
CHIP_R = 1.25                            # medio lado / radio del distintivo de unidad
CHIP_GAP = 0.95                          # separación entre el distintivo y su palabra
TITLE_GAP = 1.6                          # entre el título del carril y su primera fila
ROW_GAP = 2.0                            # entre dos filas del mismo carril

TOL_MM = 0.12

# ---------------------------------------------------------------------------
# Tipografía (puntos). Norma de la fase: nada por debajo de 6 pt en ninguna parte.
# ---------------------------------------------------------------------------
FS_VARIANT = 8.0                         # distintivo de variante, arriba a la derecha
FS_LANE = 8.8                            # título del carril
FS_DB = 8.4                              # nombre de la base de datos
FS_DB_SUB = 7.2                          # periodo o códigos de la base
FS_CHIP = 6.9                            # la palabra de la unidad de análisis
FS_STEP = 7.6                            # paso de tratamiento
FS_YIELD = 7.8                           # lo que entrega el carril
FS_NUM = 8.2                             # cifras sobre la flecha
FS_NOTE = 7.1                            # quiebres, exclusiones y notas al pie del carril
FS_BARRIER = 7.9                         # la regla de no enlace
FS_HARD_FLOOR = 6.0

# Presupuesto de texto de la lámina (excluidos números y títulos de carril)
WORD_BUDGET = 120
BOX_WORD_BUDGET = 8

# ---------------------------------------------------------------------------
# Paleta: un color por carril; el rojo es SIEMPRE exclusión o barrera
# ---------------------------------------------------------------------------
LANE_INK = ["#0B5FA5", "#0E7C7B", "#1F7A3C", "#8A6100", "#6A4C93", "#44586B"]
LANE_FILL = ["#e9f1fa", "#e5f4f3", "#e9f4ed", "#f8f0dd", "#efeaf7", "#eceff3"]
EXCL_COL = "#B02A1A"                                                  # exclusiones y barrera
INK = "#1a1a1a"
MUTED = "#4d4d4d"
CHIP_EDGE = "#2f2f2f"

RECORD, PERSON, PLACE = "record", "person", "place"

WARNINGS: list[str] = []
MIN_FS_USED: list[float] = []
LAYOUT_PROBLEMS: list[str] = []          # defectos de composición vistos por C.check_layout, lámina por lámina
PLATE_WORDS: list[str] = []              # palabras dibujadas en la lámina en curso (sin números ni títulos de carril)
BOX_WORDS: list[tuple[str, int]] = []    # (rótulo, palabras) de cada caja de la lámina en curso
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)



def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"[{MODULE}] WARNING {msg}", flush=True)



# ===========================================================================
# Rótulos bilingües fijos (los únicos textos de la lámina que no son de un carril)
# ===========================================================================
TXT = {
    "unit_record": {"es": "registro", "en": "record"},
    "unit_person": {"es": "persona", "en": "person"},
    "unit_place": {"es": "comuna", "en": "comuna"},
    "barrier": {"es": "sin enlace individual entre sistemas",
                "en": "no person-level linkage between systems"},
}
UNIT_WORD = {RECORD: "unit_record", PERSON: "unit_person", PLACE: "unit_place"}


def tr(key: str, lang: str) -> str:
    return TXT[key][lang]



# ===========================================================================
# Registro de recuentos: toda cifra impresa pasa por aquí
# ===========================================================================
class Registry:
    """Guarda cada cifra de la lámina con su pregunta, su etiqueta bilingüe, su unidad y su origen exacto."""

    def __init__(self, variant: str):
        self.variant = variant
        self.rows: dict[str, dict] = {}
        self.used: set[str] = set()
        self.on_plate: set[str] = set()   # claves dibujadas en el esquema (las demás solo lo sostienen)

    def add(self, key, question, source, unit_kind, label_en, label_es, unit_en, unit_es, value,
            source_file, source_key):
        self.rows[key] = dict(variant=self.variant, question=question, source=source, unit_kind=unit_kind,
                              key=key, label_en=label_en, label_es=label_es, unit_en=unit_en, unit_es=unit_es,
                              value=(None if value is None else float(value)), source_file=source_file,
                              source_column_or_key=source_key)
        return value

    def value(self, key):
        return self.rows[key]["value"]

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(list(self.rows.values()))


def fmt(reg: Registry, key: str, lang: str, dec: int = 0) -> str:
    """Formatea una cifra del registro (coma decimal en español) y anota su uso."""
    if key not in reg.rows:
        raise KeyError(f"{key} no está en dataflow_counts")
    reg.used.add(key)
    v = reg.rows[key]["value"]
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/e"
    return C.fmt_number(v, dec, lang)


def pct_suffix(suffix: str, lang: str) -> str:
    """Regla del proyecto para el signo de porcentaje: '12,3 %' en español, '12.3%' en inglés.

    Las especificaciones de `lanes()` declaran el sufijo en su forma española (" %"); aquí se
    convierte a la forma inglesa cuando corresponde, de modo que la Figura 1 siga la misma regla
    que el resto de los módulos. Cualquier otro sufijo pasa sin cambios.
    """
    if suffix.strip() == "%":
        return " %" if lang == "es" else "%"
    return suffix


# ===========================================================================
# Carga
# ===========================================================================
def tidy(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(CFG.TIDY / f"{name}.csv", **kw)


def load() -> SimpleNamespace:
    D = SimpleNamespace()
    D.values = {v: json.loads((CFG.OUT / f"values_{v}.json").read_text(encoding="utf-8")) for v in VARIANTS}
    D.grd = tidy("grd_year_summary")
    D.grd_los = tidy("grd_length_of_stay")
    D.grd_ids = tidy("grd_identifier_audit")
    D.deis = tidy("deis_year_summary")
    D.rem_annual = tidy("rem_pathway_annual", dtype={"code": str})
    D.cov = tidy("coverage_layers_year")
    D.surveys = tidy("survey_estimates")
    D.pie = tidy("pie_series")
    D.junaeb = tidy("junaeb_tea_year_level")
    D.edu = tidy("education_summary_year")
    D.grd_panel = tidy("grd_fixed_panel_hospitals")
    D.geo = tidy("comuna_crosswalk")
    D.spatial = tidy("spatial_comuna_standardised", usecols=["cut_comuna"])
    return D


# ===========================================================================
# Construcción de los recuentos (una fila por cifra impresa)
# ===========================================================================
Q_UNIT, Q_IN, Q_SEL, Q_EXCL, Q_OUT = "1_unit", "2_entry", "2_selection", "2_exclusion", "3_counted"
Q_BREAK = "3_break"


def build_counts(D: SimpleNamespace, variant: str) -> Registry:
    R = Registry(variant)
    V = D.values[variant]
    VJ = f"lancet_americas/outputs/values_{variant}.json"

    def T(name):
        return f"lancet_americas/outputs/tidy/{name}.csv"

    yr_first, yr_last = min(CFG.YEARS_GRD), max(CFG.YEARS_GRD)

    # ---------------- 1 · episodios hospitalarios (GRD) — REGISTROS ----------------
    g = D.grd[(D.grd.variant == variant) & (D.grd.panel == "observed") & (D.grd.activity == "all")]
    g_any = g[g.position == "any"].sort_values("year")
    g_pr = g[g.position == "principal"].sort_values("year")
    R.add("grd_in", Q_IN, "GRD", RECORD, "GRD episodes at entry", "Episodios GRD a la entrada",
          "episodes", "episodios", g_any.n_episodes_total_same_panel_activity.sum(),
          T("grd_year_summary"), "n_episodes_total_same_panel_activity (observed, all, any)")
    R.add("grd_sel", Q_SEL, "GRD", RECORD, "GRD episodes with documented F84",
          "Episodios GRD con F84 documentado", "episodes", "episodios", g_any.n_episodes_f84.sum(),
          T("grd_year_summary"), "n_episodes_f84 (observed, all, any)")
    R.add("grd_principal", Q_SEL, "GRD", RECORD, "Of these, episodes with F84 as the principal diagnosis",
          "De ellos, episodios con F84 como diagnóstico principal", "episodes", "episodios",
          g_pr.n_episodes_f84.sum(), T("grd_year_summary"), "n_episodes_f84 (position=principal)")
    R.add("b_grd_no_id", Q_EXCL, "GRD", RECORD,
          "F84 episodes without a valid identifier, excluded from the person counts",
          "Episodios F84 sin identificador válido, excluidos del conteo de personas", "episodes", "episodios",
          g_any.n_f84_without_valid_id.sum(), T("grd_year_summary"), "n_f84_without_valid_id")
    los_all = D.grd_los[(D.grd_los.variant == "all_episodes") & (D.grd_los.panel == "observed")
                        & (D.grd_los.activity == "all")]
    R.add("b_grd_bad_dates", Q_EXCL, "GRD", RECORD,
          "GRD episodes of any diagnosis with invalid or inconsistent dates, excluded from length of stay",
          "Episodios GRD de cualquier diagnóstico con fechas inválidas o inconsistentes, excluidos de la estadía",
          "episodes", "episodios", los_all.n_invalid_dates.sum(), T("grd_length_of_stay"),
          "n_invalid_dates (variant=all_episodes, panel=observed, activity=all)")
    los_f84 = D.grd_los[(D.grd_los.variant == variant) & (D.grd_los.position == "any")
                        & (D.grd_los.panel == "observed") & (D.grd_los.activity == "all")]
    R.add("b_grd_bad_dates_f84", Q_EXCL, "GRD", RECORD,
          "Of these, episodes with documented F84, excluded from length of stay",
          "De ellos, episodios con F84 documentado, excluidos de la estadía", "episodes", "episodios",
          los_f84.n_invalid_dates.sum(), T("grd_length_of_stay"),
          f"n_invalid_dates (variant={variant}, position=any, panel=observed, activity=all)")
    R.add("grd_hosp_min", Q_BREAK, "GRD", RECORD, "Hospitals in the observed panel, first year",
          "Hospitales del panel observado, primer año", "hospitals", "hospitales", g_any.hospitals_n.min(),
          T("grd_year_summary"), "hospitals_n (min)")
    R.add("grd_hosp_max", Q_BREAK, "GRD", RECORD, "Hospitals in the observed panel, last year",
          "Hospitales del panel observado, último año", "hospitals", "hospitales", g_any.hospitals_n.max(),
          T("grd_year_summary"), "hospitals_n (max)")
    R.add("grd_rate_first", Q_OUT, "GRD", RECORD,
          f"Episodes with documented F84 per 100,000 GRD episodes, {yr_first}",
          f"Episodios con F84 documentado por 100.000 episodios GRD, {yr_first}",
          "per 100,000 episodes", "por 100.000 episodios", g_any.rate_per_100k_episodes.iloc[0],
          T("grd_year_summary"), f"rate_per_100k_episodes ({yr_first})")
    R.add("grd_rate_last", Q_OUT, "GRD", RECORD,
          f"Episodes with documented F84 per 100,000 GRD episodes, {yr_last}",
          f"Episodios con F84 documentado por 100.000 episodios GRD, {yr_last}",
          "per 100,000 episodes", "por 100.000 episodios", g_any.rate_per_100k_episodes.iloc[-1],
          T("grd_year_summary"), f"rate_per_100k_episodes ({yr_last})")
    R.add("grd_persons_last", Q_OUT, "GRD", PERSON,
          f"Distinct persons with a documented F84 episode inside {yr_last}",
          f"Personas distintas con un episodio con F84 documentado dentro de {yr_last}", "people", "personas",
          g_any.persons_within_year.iloc[-1], T("grd_year_summary"), f"persons_within_year ({yr_last})")
    ids = D.grd_ids[D.grd_ids.variant == variant].set_index("year")
    R.add("grd_ids_shared_2020", Q_UNIT, "GRD", PERSON,
          "F84 identifiers of 2020 that also appear in 2019", "Identificadores F84 de 2020 que también aparecen en 2019",
          "identifiers", "identificadores", ids.loc[2020, "n_f84_ids_shared_with_previous_year"],
          T("grd_identifier_audit"), "n_f84_ids_shared_with_previous_year (2020)")
    R.add("grd_ids_shared_2021", Q_UNIT, "GRD", PERSON,
          "F84 identifiers of 2021 that also appear in 2020", "Identificadores F84 de 2021 que también aparecen en 2020",
          "identifiers", "identificadores", ids.loc[2021, "n_f84_ids_shared_with_previous_year"],
          T("grd_identifier_audit"), "n_f84_ids_shared_with_previous_year (2021)")

    # ---------------- 2 · egresos hospitalarios (DEIS) — REGISTROS ----------------
    d = D.deis[(D.deis.variant == variant) & (D.deis.source_layout == "canonical")].sort_values("year")
    R.add("deis_in", Q_IN, "DEIS", RECORD, "DEIS discharges at entry", "Egresos DEIS a la entrada",
          "discharges", "egresos", d.discharges_total.sum(), T("deis_year_summary"),
          "discharges_total (source_layout=canonical)")
    R.add("deis_sel", Q_SEL, "DEIS", RECORD, "DEIS discharges with F84 as the principal diagnosis",
          "Egresos DEIS con F84 como diagnóstico principal", "discharges", "egresos", d.f84_diag1.sum(),
          T("deis_year_summary"), "f84_diag1")
    R.add("deis_positions", Q_EXCL, "DEIS", RECORD, "Diagnosis positions published by DEIS",
          "Posiciones diagnósticas publicadas por DEIS", "positions", "posiciones",
          d.diagnosis_positions.max(), T("deis_year_summary"), "diagnosis_positions")
    R.add("deis_masked", Q_EXCL, "DEIS", RECORD,
          "DEIS discharges in provider-masked rows, kept in the national totals and out of the territorial tables",
          "Egresos DEIS en filas enmascaradas por el proveedor, conservados en los totales nacionales y fuera de las tablas territoriales",
          "discharges", "egresos", d.discharges_suppressed.sum(), T("deis_year_summary"), "discharges_suppressed")
    R.add("deis_rate_first", Q_OUT, "DEIS", RECORD,
          f"Discharges with principal F84 per 100,000 discharges, {yr_first}",
          f"Egresos con F84 principal por 100.000 egresos, {yr_first}", "per 100,000 discharges",
          "por 100.000 egresos", d.rate_per_100k_discharges.iloc[0], T("deis_year_summary"),
          f"rate_per_100k_discharges ({yr_first})")
    R.add("deis_rate_last", Q_OUT, "DEIS", RECORD,
          f"Discharges with principal F84 per 100,000 discharges, {yr_last}",
          f"Egresos con F84 principal por 100.000 egresos, {yr_last}", "per 100,000 discharges",
          "por 100.000 egresos", d.rate_per_100k_discharges.iloc[-1], T("deis_year_summary"),
          f"rate_per_100k_discharges ({yr_last})")

    # ---------------- 3 · ingresos ambulatorios (REM Serie A, A05) — REGISTROS ----------------
    sc = D.rem_annual[D.rem_annual.variant == "single_code"]
    R.add("rema_in", Q_IN, "REM Series A", RECORD,
          "REM Series A establishment-month rows at entry", "Filas establecimiento × mes de REM Serie A a la entrada",
          "establishment-month rows", "filas establecimiento × mes", sc[sc.series == "A"].n_rows.sum(),
          T("rem_pathway_annual"), "n_rows (series=A, variant=single_code)")
    a05 = sc[(sc.code == CFG.STRICT["a05_entry"]) & (sc.measure == "annual_sum")].sort_values("year")
    y_a05_first, y_a05_last = int(a05.year.iloc[0]), int(a05.year.iloc[-1])
    R.add("a05_first", Q_SEL, "REM A05", RECORD, f"Autism entries into ambulatory care, {y_a05_first}",
          f"Ingresos por autismo a la atención ambulatoria, {y_a05_first}", "entries", "ingresos",
          a05.total.iloc[0], T("rem_pathway_annual"), f"total (code={CFG.STRICT['a05_entry']}, {y_a05_first})")
    R.add("a05_last", Q_SEL, "REM A05", RECORD, f"Autism entries into ambulatory care, {y_a05_last}",
          f"Ingresos por autismo a la atención ambulatoria, {y_a05_last}", "entries", "ingresos",
          a05.total.iloc[-1], T("rem_pathway_annual"), f"total (code={CFG.STRICT['a05_entry']}, {y_a05_last})")
    R.add("a05_estab_last", Q_OUT, "REM A05", RECORD, f"Establishments reporting autism entries, {y_a05_last}",
          f"Establecimientos que reportan ingresos por autismo, {y_a05_last}", "establishments", "establecimientos",
          a05.n_reporting_establishments.iloc[-1], T("rem_pathway_annual"), "n_reporting_establishments")
    R.add("rem_empty", Q_EXCL, "REM", RECORD,
          "REM establishment-month cells reported empty, kept as empty and never read as zero",
          "Celdas establecimiento × mes de REM vacías, conservadas como vacío y nunca leídas como cero",
          "cells", "celdas", sc.n_rows_empty.sum(), T("rem_pathway_annual"),
          "n_rows_empty (variant=single_code)")
    R.add("rem_dup", Q_EXCL, "REM", RECORD, "REM exactly duplicated rows removed",
          "Filas exactamente duplicadas de REM eliminadas", "rows", "filas", sc.n_rows_exact_duplicate.sum(),
          T("rem_pathway_annual"), "n_rows_exact_duplicate (variant=single_code)")

    # ---------------- 4 · personas bajo control (REM Serie P, P2) — PERSONAS ----------------
    R.add("remp_in", Q_IN, "REM Series P", RECORD,
          "REM Series P establishment-month rows at entry", "Filas establecimiento × mes de REM Serie P a la entrada",
          "establishment-month rows", "filas establecimiento × mes", sc[sc.series == "P"].n_rows.sum(),
          T("rem_pathway_annual"), "n_rows (series=P, variant=single_code)")
    p2 = sc[(sc.code == CFG.P2_TEA) & (sc.measure == "december_stock")].sort_values("year")
    y_p2_first, y_p2_last = int(p2.year.iloc[0]), int(p2.year.iloc[-1])
    R.add("p2_first", Q_SEL, "REM P2", PERSON, f"People with autism under control in December {y_p2_first}",
          f"Personas con autismo bajo control en diciembre de {y_p2_first}", "people", "personas",
          p2.total.iloc[0], T("rem_pathway_annual"), f"total (code={CFG.P2_TEA}, december_stock, {y_p2_first})")
    R.add("p2_last", Q_SEL, "REM P2", PERSON, f"People with autism under control in December {y_p2_last}",
          f"Personas con autismo bajo control en diciembre de {y_p2_last}", "people", "personas",
          p2.total.iloc[-1], T("rem_pathway_annual"), f"total (code={CFG.P2_TEA}, december_stock, {y_p2_last})")
    R.add("p2_estab_last", Q_OUT, "REM P2", PERSON, f"Establishments reporting the December {y_p2_last} stock",
          f"Establecimientos que reportan el stock de diciembre de {y_p2_last}", "establishments",
          "establecimientos", p2.n_reporting_establishments.iloc[-1], T("rem_pathway_annual"),
          "n_reporting_establishments")
    p2_jun = sc[(sc.code == CFG.P2_TEA) & (sc.measure == "june_stock")].sort_values("year")
    R.add("p2_june_last", Q_EXCL, "REM P2", PERSON, f"June {y_p2_last} stock, a sensitivity never added to December",
          f"Stock de junio de {y_p2_last}, sensibilidad que nunca se suma a diciembre", "people", "personas",
          p2_jun.total.iloc[-1], T("rem_pathway_annual"), f"total (code={CFG.P2_TEA}, june_stock, {y_p2_last})")

    # ---------------- 5 · población y cobertura — PERSONAS (denominadores) ----------------
    cov = D.cov.set_index("year")
    y_cov = int(D.cov.year.max())
    R.add("cov_ine", Q_IN, "INE", PERSON, f"Residents projected at 30 June {y_cov}",
          f"Residentes proyectados al 30 de junio de {y_cov}", "people", "personas",
          cov.ine_population_base2017_30jun.loc[y_cov], T("coverage_layers_year"),
          f"ine_population_base2017_30jun ({y_cov})")
    R.add("cov_fonasa", Q_IN, "FONASA", PERSON, f"FONASA beneficiaries in December {y_cov}",
          f"Beneficiarios FONASA en diciembre de {y_cov}", "people", "personas",
          cov.fonasa_beneficiaries_dec.loc[y_cov], T("coverage_layers_year"), f"fonasa_beneficiaries_dec ({y_cov})")
    R.add("cov_aps", Q_IN, "APS", PERSON, f"People enrolled in municipal primary care in December {y_cov}",
          f"Inscritos en la atención primaria municipal en diciembre de {y_cov}", "people", "personas",
          cov.aps_enrolled_dec.loc[y_cov], T("coverage_layers_year"), f"aps_enrolled_dec ({y_cov})")
    R.add("cov_isapre", Q_IN, "ISAPRE", PERSON, f"ISAPRE beneficiaries in December {y_cov}",
          f"Beneficiarios ISAPRE en diciembre de {y_cov}", "people", "personas",
          cov.isapre_beneficiaries_dec.loc[y_cov], T("coverage_layers_year"), f"isapre_beneficiaries_dec ({y_cov})")
    R.add("cov_share_fonasa", Q_OUT, "FONASA", PERSON,
          f"FONASA beneficiaries as a percentage of the projected resident population, {y_cov}",
          f"Beneficiarios FONASA como porcentaje de la población residente proyectada, {y_cov}", "percent",
          "por ciento", 100 * cov.share_fonasa_ine.loc[y_cov], T("coverage_layers_year"),
          f"share_fonasa_ine ({y_cov}) × 100")

    # ---------------- 6 · encuestas poblacionales — PERSONAS ----------------
    sv = D.surveys
    ad = sv[(sv.survey == "ENDIDE 2022") & (sv.subgroup_type == "total")
            & (sv.domain == "ENDIDE adultos 18+: autismo reportado")].iloc[0]
    ch = sv[(sv.survey == "ENDIDE 2022") & (sv.subgroup_type == "total")
            & (sv.domain == "ENDIDE NNA 2-17: autismo reportado")].iloc[0]
    ec = sv[(sv.survey == "ENCAVI 2023-2024") & (sv.subgroup_type == "total")
            & (sv.domain == "ENCAVI 15+: diagnóstico de trastorno del espectro autista")].iloc[0]
    R.add("endide_adults", Q_IN, "ENDIDE", PERSON, "ENDIDE respondents aged 18 or more",
          "Personas de 18 años o más que respondieron ENDIDE", "respondents", "personas encuestadas",
          ad.n, T("survey_estimates"), "n (ENDIDE 2022, adults 18+, total)")
    R.add("endide_children", Q_IN, "ENDIDE", PERSON, "ENDIDE children aged 2-17 answered for by a caregiver",
          "NNA de 2 a 17 años de ENDIDE respondidos por su cuidador", "respondents", "personas encuestadas",
          ch.n, T("survey_estimates"), "n (ENDIDE 2022, children 2-17, total)")
    R.add("encavi_n", Q_IN, "ENCAVI", PERSON, "ENCAVI respondents aged 15 or more",
          "Personas de 15 años o más que respondieron ENCAVI", "respondents", "personas encuestadas",
          ec.n, T("survey_estimates"), "n (ENCAVI 2023-2024, 15+, total)")
    R.add("endide_adult_cases", Q_SEL, "ENDIDE", PERSON, "ENDIDE adults reporting autism",
          "Adultos de ENDIDE que reportan autismo", "respondents", "personas encuestadas",
          ad.cases, T("survey_estimates"), "cases (ENDIDE 2022, adults 18+)")
    R.add("endide_child_cases", Q_SEL, "ENDIDE", PERSON, "ENDIDE children reported as autistic",
          "NNA de ENDIDE reportados como autistas", "respondents", "personas encuestadas",
          ch.cases, T("survey_estimates"), "cases (ENDIDE 2022, children 2-17)")
    R.add("encavi_cases", Q_SEL, "ENCAVI", PERSON, "ENCAVI respondents reporting an autism diagnosis",
          "Personas de ENCAVI que reportan un diagnóstico de autismo", "respondents", "personas encuestadas",
          ec.cases, T("survey_estimates"), "cases (ENCAVI 2023-2024, 15+)")
    R.add("svy_imprecise", Q_EXCL, "Surveys", PERSON,
          "Survey domains flagged imprecise (fewer than 30 cases or a relative standard error above 30%)",
          "Dominios de encuesta marcados imprecisos (menos de 30 casos o error estándar relativo mayor que 30 %)",
          "domains", "dominios", int((sv.precision_flag == "imprecise").sum()), T("survey_estimates"),
          "precision_flag=imprecise")
    R.add("endide_adult_pct", Q_OUT, "ENDIDE", PERSON, "Design-weighted percentage of adults 18+ reporting autism",
          "Porcentaje ponderado por diseño de adultos de 18+ que reportan autismo", "percent", "por ciento",
          100 * ad.proportion, T("survey_estimates"), "proportion × 100 (ENDIDE adults 18+)")
    R.add("endide_child_pct", Q_OUT, "ENDIDE", PERSON,
          "Design-weighted percentage of children 2-17 reported as autistic",
          "Porcentaje ponderado por diseño de NNA de 2 a 17 años reportados como autistas", "percent",
          "por ciento", 100 * ch.proportion, T("survey_estimates"), "proportion × 100 (ENDIDE children 2-17)")
    R.add("encavi_pct", Q_OUT, "ENCAVI", PERSON,
          "Design-weighted percentage of people aged 15+ reporting an autism diagnosis",
          "Porcentaje ponderado por diseño de personas de 15+ que reportan un diagnóstico de autismo", "percent",
          "por ciento", 100 * ec.proportion, T("survey_estimates"), "proportion × 100 (ENCAVI 15+)")

    # ---------------- 7 · educación — PERSONAS (estudiantes) ----------------
    pie = D.pie
    apps = pie[pie.series == "pie_total_applicants_sinaces"].sort_values("year")
    y_pie = int(apps.year.iloc[-1])
    R.add("pie_base_last", Q_IN, "MINEDUC", PERSON,
          f"Students in the published base of the school integration programme, {y_pie}",
          f"Estudiantes en la base publicada del programa de integración escolar, {y_pie}", "students",
          "estudiantes", apps.value.iloc[-1], T("pie_series"), f"pie_total_applicants_sinaces ({y_pie})")
    edu = D.edu.sort_values("year")
    y_edu_first, y_edu_last = int(edu.year.iloc[0]), int(edu.year.iloc[-1])
    R.add("pie_first", Q_SEL, "MINEDUC", PERSON, f"Autistic students in the harmonised programme series, {y_edu_first}",
          f"Estudiantes autistas en la serie armonizada del programa, {y_edu_first}", "students", "estudiantes",
          edu.pie_harmonised_n.iloc[0], T("education_summary_year"), f"pie_harmonised_n ({y_edu_first})")
    R.add("pie_last", Q_SEL, "MINEDUC", PERSON, f"Autistic students in the harmonised programme series, {y_edu_last}",
          f"Estudiantes autistas en la serie armonizada del programa, {y_edu_last}", "students", "estudiantes",
          edu.pie_harmonised_n.iloc[-1], T("education_summary_year"), f"pie_harmonised_n ({y_edu_last})")
    e22 = edu[edu.year == 2022].iloc[0]
    R.add("pie_2022_adopted", Q_EXCL, "MINEDUC", PERSON, "Harmonised 2022 series adopted", "Serie armonizada de 2022 adoptada",
          "students", "estudiantes", e22.pie_harmonised_n, T("education_summary_year"), "pie_harmonised_n (2022)")
    R.add("pie_2022_other", Q_EXCL, "MINEDUC", PERSON, "The other published figure for the same 2022 series",
          "La otra cifra publicada para la misma serie de 2022", "students", "estudiantes",
          e22.pie_harmonised_sinaces_n, T("education_summary_year"), "pie_harmonised_sinaces_n (2022)")
    R.add("pie_share_last", Q_OUT, "MINEDUC", PERSON,
          f"Autistic students as a percentage of the programme's published base, {y_pie}",
          f"Estudiantes autistas como porcentaje de la base publicada del programa, {y_pie}", "percent",
          "por ciento", edu.set_index("year").pie_harmonised_share_of_applicants_sinaces_pct.loc[y_pie],
          T("education_summary_year"), f"pie_harmonised_share_of_applicants_sinaces_pct ({y_pie})")
    ja = D.junaeb[D.junaeb.sex == "all"]
    jl = edu.set_index("year")
    R.add("junaeb_in_last", Q_IN, "JUNAEB", PERSON,
          f"Pre-school students who answered the JUNAEB survey, {y_edu_last}",
          f"Estudiantes de educación parvularia que respondieron la encuesta JUNAEB, {y_edu_last}", "students",
          "estudiantes", jl.junaeb_parvularia_n_students.loc[y_edu_last], T("education_summary_year"),
          f"junaeb_parvularia_n_students ({y_edu_last})")
    R.add("junaeb_sel_last", Q_SEL, "JUNAEB", PERSON,
          f"Pre-school students reported as autistic, {y_edu_last}",
          f"Estudiantes de educación parvularia reportados como autistas, {y_edu_last}", "students",
          "estudiantes", jl.junaeb_parvularia_tea_n.loc[y_edu_last], T("education_summary_year"),
          f"junaeb_parvularia_tea_n ({y_edu_last})")
    R.add("junaeb_pct_last", Q_OUT, "JUNAEB", PERSON,
          f"Design-weighted percentage of pre-school students reported as autistic, {y_edu_last}",
          f"Porcentaje ponderado por diseño de estudiantes de parvularia reportados como autistas, {y_edu_last}",
          "percent", "por ciento", jl.junaeb_parvularia_pct_weighted.loc[y_edu_last],
          T("education_summary_year"), f"junaeb_parvularia_pct_weighted ({y_edu_last})")
    R.add("junaeb_no", Q_EXCL, "JUNAEB", PERSON,
          "Level-years with no autism item at all: not estimable, never zero",
          "Nivel-año sin ítem de autismo: no estimable, nunca cero", "level-years", "nivel-año",
          int((ja.estimable == "no").sum()), T("junaeb_tea_year_level"), "estimable=no (sex=all)")
    R.add("junaeb_unw", Q_EXCL, "JUNAEB", PERSON,
          "Level-years with no usable weight, not comparable with the weighted years",
          "Nivel-año sin ponderador utilizable, no comparables con los años ponderados", "level-years",
          "nivel-año", int((ja.estimable == "unweighted_only").sum()), T("junaeb_tea_year_level"),
          "estimable=unweighted_only (sex=all)")

    # ---------------- 8 · territorio — COMUNAS ----------------
    R.add("geo_comunas", Q_IN, "Cartography", PLACE, "Comunas in the national cartography",
          "Comunas de la cartografía nacional", "comunas", "comunas", D.geo.cut_comuna.nunique(),
          T("comuna_crosswalk"), "cut_comuna (distinct)")

    # ---------------- quiebres de definición que el esquema marca sobre la flecha ----------------
    gf = D.grd[(D.grd.variant == variant) & (D.grd.panel != "observed") & (D.grd.activity == "all")
               & (D.grd.position == "any")]
    R.add("grd_hosp_fixed", Q_BREAK, "GRD", RECORD, "Hospitals in the fixed panel",
          "Hospitales del panel fijo", "hospitals", "hospitales", gf.hospitals_n.max(),
          T("grd_year_summary"), "hospitals_n (panel=fixed65)")
    R.add("a05_era_year", Q_BREAK, "REM A05", RECORD,
          "First year of the code era of the autism entry indicator",
          "Primer año de la era del código de ingreso por autismo", "year", "año",
          sc[sc.code == CFG.STRICT["a05_entry"]].era_start.min(), T("rem_pathway_annual"),
          f"era_start (code={CFG.STRICT['a05_entry']})")
    R.add("p6_era_year", Q_BREAK, "REM P6", PERSON,
          "First year of the code era of the specialty autism indicator",
          "Primer año de la era del código de autismo de especialidad", "year", "año",
          sc[sc.code == CFG.STRICT["p6_primary"]].era_start.min(), T("rem_pathway_annual"),
          f"era_start (code={CFG.STRICT['p6_primary']})")
    src = edu.set_index("year").pie_harmonised_source
    R.add("edu_source_year", Q_BREAK, "MINEDUC", PERSON,
          "First year published by the second source of the programme series",
          "Primer año publicado por la segunda fuente de la serie del programa", "year", "año",
          int(src[src != src.iloc[0]].index.min()), T("education_summary_year"),
          "pie_harmonised_source (first year that changes)")

    # cifra leída de values_<variante>.json, para que la lámina y el texto compartan el mismo origen
    R.add("grd_positions", Q_UNIT, "GRD", RECORD, "Diagnosis positions screened in every GRD episode",
          "Posiciones diagnósticas revisadas en cada episodio GRD", "positions", "posiciones",
          V["grd_diagnosis_positions"], VJ, "grd_diagnosis_positions")
    return R


# ===========================================================================
# Controles: cada cifra de la lámina se rederiva de su fuente autoritativa
# ===========================================================================
def build_controls(D: SimpleNamespace, regs: dict[str, Registry]) -> pd.DataFrame:
    rows = []

    def add(variant, name, key, expected, note, tol=1e-6):
        obs = regs[variant].value(key)
        exp = None if expected is None else float(expected)
        rows.append(dict(name=name, key=f"{variant}:{key}", expected=exp, observed=obs, note=note, tol=tol))

    for variant in VARIANTS:
        V = D.values[variant]
        yg, yr = CFG.YEARS_GRD, CFG.YEARS_REM
        add(variant, "grd_episodes_at_entry", "grd_in", sum(V[f"grd_records_total_{y}"] for y in yg),
            "expected = sum of grd_records_total_<year> in values_<variant>.json; observed = grd_year_summary.csv")
        add(variant, "grd_f84_any_total", "grd_sel", sum(V[f"grd_f84_any_n_{y}"] for y in yg),
            "expected = sum of grd_f84_any_n_<year> in values_<variant>.json; observed = grd_year_summary.csv")
        add(variant, "grd_f84_principal_total", "grd_principal", sum(V[f"grd_f84_principal_n_{y}"] for y in yg),
            "expected = sum of grd_f84_principal_n_<year> in values_<variant>.json; observed = grd_year_summary.csv")
        add(variant, "grd_hospitals_first_year", "grd_hosp_min", CFG.CONTROLS["grd_hospitals_observed"][min(yg)],
            "expected = config.CONTROLS['grd_hospitals_observed'][2019]; observed = grd_year_summary.csv")
        add(variant, "grd_hospitals_last_year", "grd_hosp_max", CFG.CONTROLS["grd_hospitals_observed"][max(yg)],
            "expected = config.CONTROLS['grd_hospitals_observed'][2024]; observed = grd_year_summary.csv")
        add(variant, "grd_persons_within_last_year", "grd_persons_last",
            D.grd_ids[(D.grd_ids.variant == variant) & (D.grd_ids.year == max(yg))].n_unique_ids.iloc[0],
            "expected = grd_identifier_audit.csv n_unique_ids (2024); observed = grd_year_summary.csv persons_within_year")
        add(variant, "grd_rate_last_year", "grd_rate_last",
            1e5 * V[f"grd_f84_any_n_{max(yg)}"] / V[f"grd_records_total_{max(yg)}"],
            "expected = 100,000 × grd_f84_any_n_2024 / grd_records_total_2024 from values_<variant>.json; "
            "observed = rate_per_100k_episodes of grd_year_summary.csv")
        add(variant, "deis_discharges_at_entry", "deis_in", sum(V[f"deis_discharges_total_{y}"] for y in yg),
            "expected = sum of deis_discharges_total_<year> in values_<variant>.json; observed = deis_year_summary.csv")
        add(variant, "deis_f84_principal_total", "deis_sel", sum(V[f"deis_f84_principal_n_{y}"] for y in yg),
            "expected = sum of deis_f84_principal_n_<year> in values_<variant>.json; observed = deis_year_summary.csv")
        add(variant, "a05_autism_entries_first", "a05_first", CFG.CONTROLS["a05_autism_entries"][2021],
            "expected = config.CONTROLS['a05_autism_entries'][2021]; observed = rem_pathway_annual.csv")
        add(variant, "a05_autism_entries_last", "a05_last", CFG.CONTROLS["a05_autism_entries"][2025],
            "expected = config.CONTROLS['a05_autism_entries'][2025]; observed = rem_pathway_annual.csv")
        add(variant, "a05_establishments_last", "a05_estab_last", V["a05_autism_entries_estab_2025"],
            "expected = a05_autism_entries_estab_2025 in values_<variant>.json; observed = rem_pathway_annual.csv")
        add(variant, "p2_tea_june_last", "p2_june_last", V["p2_tea_jun_2025"],
            "expected = p2_tea_jun_2025 in values_<variant>.json (the June cut, never added to December); "
            "observed = rem_pathway_annual.csv")
        add(variant, "p2_tea_december_first", "p2_first", CFG.CONTROLS["p2_tea_december"][2019],
            "expected = config.CONTROLS['p2_tea_december'][2019]; observed = rem_pathway_annual.csv")
        add(variant, "p2_tea_december_last", "p2_last", CFG.CONTROLS["p2_tea_december"][2025],
            "expected = config.CONTROLS['p2_tea_december'][2025]; observed = rem_pathway_annual.csv")
        add(variant, "p2_establishments_december_last", "p2_estab_last",
            CFG.CONTROLS["p2_establishments_december"][2025],
            "expected = config.CONTROLS['p2_establishments_december'][2025]; observed = rem_pathway_annual.csv")
        add(variant, "ine_population_last", "cov_ine", CFG.CONTROLS["ine_population_national"][max(yr)],
            "expected = config.CONTROLS['ine_population_national'][2025]; observed = coverage_layers_year.csv")
        add(variant, "fonasa_beneficiaries_last", "cov_fonasa",
            CFG.CONTROLS["fonasa_beneficiaries_december"][max(yr)],
            "expected = config.CONTROLS['fonasa_beneficiaries_december'][2025]; observed = coverage_layers_year.csv")
        add(variant, "aps_enrolled_last", "cov_aps", CFG.CONTROLS["aps_enrolled_december"][max(yr)],
            "expected = config.CONTROLS['aps_enrolled_december'][2025]; observed = coverage_layers_year.csv")
        add(variant, "isapre_beneficiaries_last", "cov_isapre",
            CFG.CONTROLS["isapre_beneficiaries_december"][max(yr)],
            "expected = config.CONTROLS['isapre_beneficiaries_december'][2025]; observed = coverage_layers_year.csv")
        add(variant, "endide_adult_respondents", "endide_adults", V["svy_endide_adults_reported_total_n"],
            "expected = svy_endide_adults_reported_total_n in values_<variant>.json; observed = survey_estimates.csv")
        add(variant, "endide_child_respondents", "endide_children", V["svy_endide_children_reported_total_n"],
            "expected = svy_endide_children_reported_total_n in values_<variant>.json; observed = survey_estimates.csv")
        add(variant, "encavi_respondents", "encavi_n", V["svy_encavi_15plus_diagnosed_total_n"],
            "expected = svy_encavi_15plus_diagnosed_total_n in values_<variant>.json; observed = survey_estimates.csv")
        add(variant, "endide_adult_percentage", "endide_adult_pct", V["svy_endide_adults_reported_total_pct"],
            "expected = svy_endide_adults_reported_total_pct in values_<variant>.json; observed = survey_estimates.csv",
            tol=1e-9)
        add(variant, "endide_child_percentage", "endide_child_pct", V["svy_endide_children_reported_total_pct"],
            "expected = svy_endide_children_reported_total_pct in values_<variant>.json; observed = survey_estimates.csv",
            tol=1e-9)
        add(variant, "endide_child_cases", "endide_child_cases", CFG.CONTROLS["endide_unweighted"]["children"],
            "expected = config.CONTROLS['endide_unweighted']['children']; observed = survey_estimates.csv")
        add(variant, "endide_adult_cases", "endide_adult_cases", CFG.CONTROLS["endide_unweighted"]["adults"],
            "expected = config.CONTROLS['endide_unweighted']['adults']; observed = survey_estimates.csv")
        add(variant, "encavi_positive_cases", "encavi_cases", CFG.CONTROLS["encavi_unweighted"]["positive"],
            "expected = config.CONTROLS['encavi_unweighted']['positive']; observed = survey_estimates.csv")
        add(variant, "pie_harmonised_first", "pie_first", CFG.CONTROLS["pie_harmonised"][2019],
            "expected = config.CONTROLS['pie_harmonised'][2019]; observed = education_summary_year.csv")
        add(variant, "pie_harmonised_last", "pie_last", CFG.CONTROLS["pie_harmonised"][2025],
            "expected = config.CONTROLS['pie_harmonised'][2025]; observed = education_summary_year.csv")
        add(variant, "pie_harmonised_2022_adopted", "pie_2022_adopted", CFG.CONTROLS["pie_harmonised"][2022],
            "expected = config.CONTROLS['pie_harmonised'][2022] (Apuntes 60 rule); observed = education_summary_year.csv")
        add(variant, "junaeb_parvularia_cases_last", "junaeb_sel_last",
            CFG.CONTROLS["junaeb_unweighted_2025"]["parvularia"],
            "expected = config.CONTROLS['junaeb_unweighted_2025']['parvularia']; observed = education_summary_year.csv")
        add(variant, "junaeb_parvularia_students_last", "junaeb_in_last", V["junaeb_parvularia_all_n_students_2025"],
            "expected = junaeb_parvularia_all_n_students_2025 in values_<variant>.json; observed = education_summary_year.csv")
        add(variant, "junaeb_parvularia_percentage_last", "junaeb_pct_last",
            V["junaeb_parvularia_all_pct_weighted_2025"],
            "expected = junaeb_parvularia_all_pct_weighted_2025 in values_<variant>.json; observed = education_summary_year.csv",
            tol=1e-9)
        add(variant, "pie_published_base_last", "pie_base_last", V["pie_total_applicants_sinaces_2025"],
            "expected = pie_total_applicants_sinaces_2025 in values_<variant>.json; observed = pie_series.csv")
        add(variant, "coverage_share_fonasa_last", "cov_share_fonasa", V["share_fonasa_ine_pct_2025"],
            "expected = share_fonasa_ine_pct_2025 in values_<variant>.json; observed = coverage_layers_year.csv",
            tol=1e-6)
        # --- lo que la lámina dice sobre sí misma ---------------------------------------------------
        los_v = D.grd_los[(D.grd_los.variant == variant) & (D.grd_los.panel == "observed")
                          & (D.grd_los.activity == "all")]
        add(variant, "grd_invalid_dates_f84_by_position", "b_grd_bad_dates_f84",
            los_v[los_v.position.isin(["principal", "secondary_only"])].n_invalid_dates.sum(),
            "expected = principal + secondary_only in grd_length_of_stay.csv; observed = position=any (F84 subset)")
        add(variant, "grd_invalid_dates_all_episodes", "b_grd_bad_dates",
            D.grd_los[(D.grd_los.variant == "all_episodes") & (D.grd_los.panel == "observed")
                      & (D.grd_los.activity == "all")].n_invalid_dates.sum(),
            "expected = variant=all_episodes in grd_length_of_stay.csv (ALL GRD episodes, not the F84 subset)")
        add(variant, "grd_identifier_break_2021", "grd_ids_shared_2021", 0,
            "expected = 0 F84 identifiers shared between 2020 and 2021: the identifier changes format, which is why "
            "persons are counted only within a year; observed = grd_identifier_audit.csv")
        add(variant, "pie_share_of_base_last", "pie_share_last",
            100 * regs[variant].value("pie_last") / regs[variant].value("pie_base_last"),
            "expected = 100 × autistic students / students in the published base, the two numbers printed beside it on "
            "the plate; observed = education_summary_year.csv (published to three decimals)", tol=5e-4)
        add(variant, "encavi_percentage_last", "encavi_pct", V["svy_encavi_15plus_diagnosed_total_pct"],
            "expected = svy_encavi_15plus_diagnosed_total_pct in values_<variant>.json; observed = survey_estimates.csv",
            tol=1e-9)
        add(variant, "grd_fixed_panel_hospitals", "grd_hosp_fixed",
            int(D.grd_panel.in_fixed_panel.astype(bool).sum()),
            "expected = hospitals flagged in_fixed_panel in grd_fixed_panel_hospitals.csv; observed = hospitals_n of "
            "the fixed panel in grd_year_summary.csv (65 fixed hospitals against the 65-65-65-65-68-72 observed)")
        add(variant, "a05_code_era_first_year", "a05_era_year", min(CFG.CONTROLS["a05_autism_entries"]),
            "expected = first year of config.CONTROLS['a05_autism_entries'] (the autism entry code exists only from "
            "2021); observed = era_start of rem_pathway_annual.csv")
        add(variant, "p6_code_era_first_year", "p6_era_year", regs[variant].value("a05_era_year"),
            "expected = the same era start as the A05 autism entry code: both REM code families change era in the same "
            "year; observed = era_start of rem_pathway_annual.csv for the specialty code")
        add(variant, "education_source_change_year", "edu_source_year",
            min(CFG.CONTROLS["pie_special_schools"]),
            "expected = first year of config.CONTROLS['pie_special_schools'], published only by the second education "
            "source; observed = first year in which pie_harmonised_source changes in education_summary_year.csv")
        add(variant, "cartography_comunas", "geo_comunas", D.spatial.cut_comuna.nunique(),
            "expected = distinct comunas with a standardised indicator in spatial_comuna_standardised.csv; observed = "
            "distinct comunas of comuna_crosswalk.csv")
    df = pd.DataFrame(rows)
    df["abs_diff"] = (df.observed - df.expected).abs()
    df["rel_diff"] = np.where(df.expected.abs() > 0, df.abs_diff / df.expected.abs(), np.nan)
    df["status"] = np.where(df.expected.isna() | df.observed.isna(), "info",
                            np.where(df.abs_diff <= df.tol, "ok", "differs"))
    return df[["name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"]]


# ===========================================================================
# Lienzo y motor de texto (medición real, sin adivinar el ancho)
# ===========================================================================
class Canvas:
    def __init__(self, fig, ax):
        self.fig, self.ax = fig, ax
        self.renderer = fig.canvas.get_renderer()
        self.rects: list[tuple[float, float, float, float, str]] = []
        self.n_boxes = 0
        self._cache: dict[tuple, float] = {}

    def width_mm(self, s, fs, weight="normal"):
        key = (s, round(fs, 2), weight)
        if key not in self._cache:
            t = self.ax.text(0, 0, s, fontsize=fs, fontweight=weight)
            bb = t.get_window_extent(renderer=self.renderer)
            t.remove()
            self._cache[key] = bb.width / self.fig.dpi * MM_PER_IN
        return self._cache[key]

    def register(self, x, y, w, h, name):
        for (x2, y2, w2, h2, n2) in self.rects:
            if x < x2 + w2 - 0.05 and x2 < x + w - 0.05 and y < y2 + h2 - 0.05 and y2 < y + h - 0.05:
                warn(f"box overlap: {name} overlaps {n2}")
        self.rects.append((x, y, w, h, name))


# ===========================================================================
# Contabilidad de palabras: la lámina tiene un presupuesto y se comprueba
# ---------------------------------------------------------------------------
# Cuenta como PALABRA cualquier fragmento que lleve al menos una letra; las cifras, los años, los
# rangos y los porcentajes no cuentan, y los seis títulos de carril tampoco (se dibujan con
# `count=False`). Los nombres de las bases y los códigos administrativos SÍ cuentan: es el recuento
# más severo posible y es el que se registra en el runlog.
# ===========================================================================
_WORD_STRIP = "·—–-()[]{},;:.%&/→←+*«»\"'¿?¡!"


def words_of(s) -> list[str]:
    out = []
    for tok in str(s).split():
        t = tok.strip(_WORD_STRIP)
        if any(ch.isalpha() for ch in t):
            out.append(t)
    return out


def wrap_fit(cv: Canvas, s, fs, weight, max_w, floor=6.6):
    """Parte `s` en líneas que caben en `max_w`. Si una palabra sola no cabe, reduce el cuerpo hasta
    el piso tipográfico antes de rendirse: ninguna caja deja texto fuera de su borde."""
    s = str(s)
    while True:
        lines, cur = [], ""
        for w in s.split():
            trial = f"{cur} {w}".strip()
            if cur and cv.width_mm(trial, fs, weight) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        lines = lines or [""]
        widest = max(cv.width_mm(ln, fs, weight) for ln in lines)
        if widest <= max_w + 0.05:
            return lines, fs
        if fs <= floor + 1e-9:
            warn(f"'{s}' needs {widest:.1f} mm in {max_w:.1f} mm at the {fs:.1f} pt floor")
            return lines, fs
        fs = max(floor, fs - 0.1)


def fit_fs(cv: Canvas, s, fs, weight, max_w, floor=6.6):
    """Reduce el cuerpo de una línea que no se parte hasta que quepa en `max_w`."""
    while cv.width_mm(s, fs, weight) > max_w and fs > floor + 1e-9:
        fs = max(floor, fs - 0.1)
    if cv.width_mm(s, fs, weight) > max_w + 0.05:
        warn(f"'{s}' needs {cv.width_mm(s, fs, weight):.1f} mm in {max_w:.1f} mm at the {fs:.1f} pt floor")
    return fs


def plate_subst(txt: str, R: Registry, lang: str) -> str:
    """Sustituye {clave}, {clave:1} y {clave:y} por la cifra registrada y la anota como impresa.

    `:y` imprime un año sin separador de millares; el resto usa los separadores del idioma."""
    out, i = [], 0
    while i < len(txt):
        ch = txt[i]
        if ch == "{":
            j = txt.index("}", i)
            key, _, spec = txt[i + 1:j].partition(":")
            R.on_plate.add(key)
            if spec == "y":
                out.append(str(int(R.value(key))))
            else:
                out.append(fmt(R, key, lang, int(spec) if spec else 0))
            i = j + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ===========================================================================
# Vocabulario visual: tres formas, un color por carril, el rojo solo para exclusiones
# ===========================================================================
def text(cv: Canvas, x, y, s, fs, *, weight="normal", colour=INK, ha="left", va="baseline",
         count=True, zorder=6, bbox=None):
    if count:
        PLATE_WORDS.extend(words_of(s))
    MIN_FS_USED.append(fs)
    return cv.ax.text(x, y, s, fontsize=fs, fontweight=weight, color=colour, ha=ha, va=va,
                      zorder=zorder, bbox=bbox)


def text_block(cv: Canvas, xc, yc, lines, fs, *, weight="normal", colour=INK, ha="center",
               count=True, zorder=6, bbox=None):
    """Bloque de líneas centrado verticalmente en `yc`."""
    lh = fs * PT_MM * LINE_FACTOR
    top = yc + len(lines) * lh / 2.0
    for i, ln in enumerate(lines):
        yb = top - (i + 1) * lh + fs * PT_MM * 0.30
        text(cv, xc, yb, ln, fs, weight=weight, colour=colour, ha=ha, va="baseline", count=count,
             zorder=zorder, bbox=bbox)


def text_down(cv: Canvas, x, y_top, lines, fs, *, weight="normal", colour=INK, ha="left",
              count=True, zorder=6):
    """Bloque de líneas que cuelga hacia abajo desde `y_top`. Devuelve la y final."""
    lh = fs * PT_MM * LINE_FACTOR
    yy = y_top
    for ln in lines:
        yy -= lh
        text(cv, x, yy + fs * PT_MM * 0.30, ln, fs, weight=weight, colour=colour, ha=ha,
             va="baseline", count=count, zorder=zorder)
    return yy


def drum(cv: Canvas, x, y, w, h, edge, name=None):
    """Cilindro: una BASE DE DATOS. Es la única forma con tapas elípticas."""
    from matplotlib.patches import Ellipse, Rectangle
    if name:
        cv.register(x, y, w, h, name)
    cv.n_boxes += 1
    e = min(DRUM_E, h * 0.34)
    cv.ax.add_patch(Ellipse((x + w / 2, y + e / 2), w, e, fc="white", ec=edge, lw=1.15, zorder=2))
    cv.ax.add_patch(Rectangle((x, y + e / 2), w, h - e, fc="white", ec="none", zorder=2))
    cv.ax.plot([x, x], [y + e / 2, y + h - e / 2], color=edge, lw=1.15, zorder=3)
    cv.ax.plot([x + w, x + w], [y + e / 2, y + h - e / 2], color=edge, lw=1.15, zorder=3)
    cv.ax.add_patch(Ellipse((x + w / 2, y + h - e / 2), w, e, fc="white", ec=edge, lw=1.15, zorder=3))


def step_box(cv: Canvas, x, y, w, h, edge, name=None):
    """Caja redondeada: un PASO de tratamiento."""
    from matplotlib.patches import FancyBboxPatch
    if name:
        cv.register(x, y, w, h, name)
    cv.n_boxes += 1
    cv.ax.add_patch(FancyBboxPatch((x + 0.5, y + 0.5), w - 1.0, h - 1.0,
                                   boxstyle="round,pad=0.5,rounding_size=1.2",
                                   fc="white", ec=edge, lw=0.85, zorder=2))


def yield_block(cv: Canvas, x, y, w, h, colour, name=None):
    """Bloque con punta: lo que el carril ENTREGA."""
    from matplotlib.patches import Polygon
    if name:
        cv.register(x, y, w, h, name)
    cv.n_boxes += 1
    pts = [(x, y), (x + w - YIELD_TIP, y), (x + w, y + h / 2), (x + w - YIELD_TIP, y + h), (x, y + h)]
    cv.ax.add_patch(Polygon(pts, closed=True, fc=colour, ec=colour, lw=0.8, zorder=2))


def flow_arrow(cv: Canvas, x0, x1, y, colour, broken_x=None):
    """Flecha del flujo. `broken_x` corta la flecha justo donde cambia la definición de la serie."""
    from matplotlib.patches import FancyArrowPatch
    cv.ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=7.5, lw=1.15,
                                    color=colour, shrinkA=0, shrinkB=0, zorder=3))
    if broken_x is not None:
        xm = broken_x
        for dx in (-0.85, 0.85):
            cv.ax.plot([xm + dx - 0.7, xm + dx + 0.7], [y - 1.55, y + 1.55], color=colour, lw=1.25,
                       solid_capstyle="round", zorder=5)


def unit_chip(cv: Canvas, x, yc, kind, word, fs, colour=CHIP_EDGE):
    """Distintivo de la unidad de análisis: cuadrado = registro, círculo = persona, hexágono = comuna.
    La palabra va siempre al lado, de modo que la forma no necesita leyenda."""
    from matplotlib.patches import Rectangle, Circle, RegularPolygon
    if kind == RECORD:
        cv.ax.add_patch(Rectangle((x, yc - CHIP_R), 2 * CHIP_R, 2 * CHIP_R, fc="white", ec=colour,
                                  lw=1.0, zorder=5))
    elif kind == PERSON:
        cv.ax.add_patch(Circle((x + CHIP_R, yc), CHIP_R, fc="white", ec=colour, lw=1.0, zorder=5))
    else:
        cv.ax.add_patch(RegularPolygon((x + CHIP_R, yc), 6, radius=CHIP_R * 1.18, orientation=0.0,
                                       fc="white", ec=colour, lw=1.0, zorder=5))
    text(cv, x + 2 * CHIP_R + CHIP_GAP, yc - fs * PT_MM * 0.34, word, fs, colour=colour, ha="left",
         va="baseline")


def chip_width(cv: Canvas, word, fs):
    return 2 * CHIP_R + CHIP_GAP + cv.width_mm(word, fs)


# ===========================================================================
# Contenido: seis carriles, cada uno «base → pasos → lo que entrega»
# ---------------------------------------------------------------------------
# Cada paso es una operación realmente aplicada por la tubería a esa base. Ninguna cifra está escrita
# a mano: `nums` nombra claves del registro y se dibuja sobre la flecha indicada (0 = de la base al
# primer paso, n = del último paso al resultado); `brk` es una plantilla {clave} que se resuelve
# igual y marca, en esa misma flecha, el punto donde cambia la definición; `note` cuelga bajo el paso
# indicado, en rojo si es una exclusión.
# ===========================================================================
def lanes():
    g0, g1 = min(CFG.YEARS_GRD), max(CFG.YEARS_GRD)
    r0, r1 = min(CFG.YEARS_REM), max(CFG.YEARS_REM)
    grd_span = {"es": f"{g0}–{g1}", "en": f"{g0}–{g1}"}
    rem_span = {"es": f"{r0}–{r1}", "en": f"{r0}–{r1}"}
    return [
        dict(key="hospital", title={"es": "Atención hospitalaria", "en": "Hospital care"},
             rows=[
                 dict(name={"es": "GRD", "en": "GRD"}, sub=[grd_span], unit=RECORD,
                      steps=[{"es": "seleccionar F84", "en": "select F84 codes"},
                             {"es": "posición y actividad", "en": "position and activity"}],
                      nums={0: [[("grd_in", 0, "")]], 1: [[("grd_sel", 0, "")]],
                            2: [[("grd_rate_first", 0, ""), ("grd_rate_last", 0, "")]]},
                      brk={1: {"es": "{grd_hosp_fixed} fijos · {grd_hosp_min}–{grd_hosp_max} observados",
                               "en": "{grd_hosp_fixed} fixed · {grd_hosp_min}–{grd_hosp_max} observed"}},
                      out={"es": "F84 por 100.000 episodios", "en": "F84 per 100,000 episodes"}),
                 dict(name={"es": "DEIS", "en": "DEIS"}, sub=[grd_span], unit=RECORD,
                      steps=[{"es": "F84 principal", "en": "principal F84"},
                             {"es": "por residencia", "en": "by residence"}],
                      nums={0: [[("deis_in", 0, "")]], 1: [[("deis_sel", 0, "")]],
                            2: [[("deis_rate_first", 0, ""), ("deis_rate_last", 0, "")]]},
                      note=dict(at=1, kind="excl", n=("deis_masked", 0),
                                text={"es": "egresos enmascarados", "en": "masked discharges"}),
                      out={"es": "F84 por 100.000 egresos", "en": "F84 per 100,000 discharges"}),
             ]),
        dict(key="rem_pathway", title={"es": "Ruta de atención · REM Serie A (A03, A05, A27, A28)",
                                       "en": "Care pathway · REM Series A (A03, A05, A27, A28)"},
             rows=[
                 dict(name=None,
                      sub=[{"es": "tamizaje · ingresos", "en": "screening · entries"},
                           {"es": "consejería · rehabilitación", "en": "counselling · rehabilitation"},
                           rem_span],
                      unit=RECORD,
                      steps=[{"es": "armonizar códigos", "en": "harmonise codes"},
                             {"es": "contar establecimientos", "en": "count establishments"}],
                      nums={0: [[("rema_in", 0, "")]],
                            2: [[("a05_first", 0, ""), ("a05_last", 0, "")]]},
                      brk={1: {"es": "código nuevo, {a05_era_year:y}",
                               "en": "code changes, {a05_era_year:y}"}},
                      note=dict(at=0, kind="excl", n=("rem_empty", 0),
                                text={"es": "celdas vacías, nunca cero", "en": "empty cells, never zero"}),
                      out={"es": "ingresos por año", "en": "entries per year"}),
             ]),
        dict(key="under_control", title={"es": "Personas bajo control · REM Serie P",
                                         "en": "People under control · REM Series P"},
             rows=[
                 dict(name=None, sub=[{"es": "P2 · P6", "en": "P2 · P6"}, rem_span], unit=PERSON,
                      steps=[{"es": "armonizar códigos", "en": "harmonise codes"},
                             {"es": "tomar diciembre", "en": "take December"}],
                      nums={0: [[("remp_in", 0, "")]],
                            2: [[("p2_first", 0, ""), ("p2_last", 0, "")]]},
                      brk={1: {"es": "código nuevo, {p6_era_year:y}",
                               "en": "code changes, {p6_era_year:y}"}},
                      note=dict(at=1, kind="excl", n=("p2_june_last", 0),
                                text={"es": "en junio, nunca sumado", "en": "June, never added"}),
                      out={"es": "stock de diciembre", "en": "December stock"}),
             ]),
        dict(key="denominators", title={"es": "Denominadores y cobertura",
                                        "en": "Denominators and coverage"},
             rows=[
                 dict(name=None, sub=[{"es": "INE · FONASA", "en": "INE · FONASA"},
                                      {"es": "APS · ISAPRE · REM-20", "en": "APS · ISAPRE · REM-20"}],
                      unit=PERSON,
                      steps=[{"es": "tomar diciembre", "en": "take December"},
                             {"es": "edad y sexo", "en": "age and sex"}],
                      nums={0: [[("cov_ine", 0, "")]], 2: [[("cov_share_fonasa", 1, " %")]]},
                      note=dict(at=0, kind="plain", n=None,
                                text={"es": "sin código de autismo", "en": "no autism code"}),
                      out={"es": "residentes como denominador", "en": "residents as denominator"}),
             ]),
        dict(key="surveys_education", title={"es": "Encuestas y educación",
                                             "en": "Surveys and education"},
             rows=[
                 dict(name=None, sub=[{"es": "ENDIDE 18+", "en": "ENDIDE 18+"},
                                      {"es": "ENDIDE 2–17", "en": "ENDIDE 2–17"},
                                      {"es": "ENCAVI 15+", "en": "ENCAVI 15+"}],
                      unit=PERSON,
                      steps=[{"es": "aplicar el diseño", "en": "apply survey design"}],
                      nums={0: [[("endide_adults", 0, "")], [("endide_children", 0, "")],
                                [("encavi_n", 0, "")]],
                            1: [[("endide_adult_cases", 0, "")], [("endide_child_cases", 0, "")],
                                [("encavi_cases", 0, "")]],
                            2: [[("endide_adult_pct", 2, " %")], [("endide_child_pct", 2, " %")],
                                [("encavi_pct", 2, " %")]]},
                      out={"es": "porcentaje ponderado", "en": "design-weighted percentage"}),
                 dict(name=None, sub=[{"es": "MINEDUC · PIE", "en": "MINEDUC · PIE"},
                                      {"es": "JUNAEB", "en": "JUNAEB"}],
                      unit=PERSON,
                      steps=[{"es": "armonizar serie", "en": "harmonise the series"},
                             {"es": "ponderar encuesta", "en": "weight the survey"}],
                      nums={0: [[("pie_base_last", 0, "")], [("junaeb_in_last", 0, "")]],
                            1: [[("pie_last", 0, "")], [("junaeb_sel_last", 0, "")]],
                            2: [[("pie_share_last", 1, " %")], [("junaeb_pct_last", 1, " %")]]},
                      brk={0: {"es": "fuente nueva, {edu_source_year:y}",
                               "en": "source changes, {edu_source_year:y}"}},
                      out={"es": "estudiantes por año", "en": "students per year"}),
             ]),
        dict(key="territory", title={"es": "Territorio", "en": "Territory"},
             rows=[
                 dict(name=None, sub=[{"es": "SAE · privación", "en": "SAE · deprivation"},
                                      {"es": "cartografía", "en": "cartography"}],
                      unit=PLACE,
                      steps=[{"es": "estandarizar edad y sexo", "en": "standardise by age and sex"},
                             {"es": "suavizar por comuna", "en": "smooth by comuna"}],
                      nums={0: [[("geo_comunas", 0, "")]]},
                      out={"es": "razón comunal suavizada", "en": "smoothed comuna ratio"}),
             ]),
    ]


# ===========================================================================
# Medición de una fila: todo se mide sobre el renderizador antes de dibujar nada
# ===========================================================================
def plan_row(cv: Canvas, row, lang, R, xa, xb, scale):
    fs = SimpleNamespace(db=FS_DB * scale, sub=FS_DB_SUB * scale, chip=FS_CHIP * scale,
                         step=FS_STEP * scale, out=FS_YIELD * scale, num=FS_NUM * scale,
                         note=FS_NOTE * scale)
    P = dict(fs=fs)

    def L(d):
        return d[lang]

    # --- cifras sobre las flechas -------------------------------------------------------------
    n_steps = len(row["steps"])
    n_arrows = n_steps + 1
    nums: dict[int, list[str]] = {}
    for a, spec_lines in row.get("nums", {}).items():
        lines = []
        for spec in spec_lines:
            parts = []
            for key, dec, suffix in spec:
                R.on_plate.add(key)
                parts.append(fmt(R, key, lang, dec) + pct_suffix(suffix, lang))
            lines.append(" → ".join(parts))
        nums[a] = lines
    P["nums"] = nums

    # --- ancho de cada flecha: la cifra manda ---------------------------------------------------
    gaps = []
    for a in range(n_arrows):
        w = max([cv.width_mm(ln, fs.num, "bold") for ln in nums.get(a, [])], default=0.0)
        room = BREAK_ROOM if a in row.get("brk", {}) else 0.0
        gaps.append(max(ARROW_MIN + room, w + 4.6 + room) if w else max(ARROW_MIN, room + 4.0))
    span = (xb - xa) - DB_W - YIELD_W
    step_w = (span - sum(gaps)) / n_steps
    if step_w > STEP_W_MAX:
        gaps = [g + (step_w - STEP_W_MAX) * n_steps / n_arrows for g in gaps]
        step_w = STEP_W_MAX
    if step_w < STEP_W_MIN:
        warn(f"step boxes only {step_w:.1f} mm wide in lane row {L(row['out'])}")
    P["gaps"], P["step_w"], P["n_steps"], P["n_arrows"] = gaps, step_w, n_steps, n_arrows

    # --- cilindro ------------------------------------------------------------------------------
    inner = DB_W - 2 * PAD
    chip_word = tr(UNIT_WORD[row["unit"]], lang)
    name = L(row["name"]) if row.get("name") else None
    sub = [L(s) for s in row["sub"]]
    lh_chip = fs.chip * PT_MM * LINE_FACTOR + 0.6
    fs_name = fit_fs(cv, name, fs.db, "bold", inner) if name is not None else fs.db
    lh_db = fs_name * PT_MM * LINE_FACTOR
    sub_fit = []
    for k, s in enumerate(sub):
        head = name is None and k == 0
        w = "bold" if head else "normal"
        lines, f = wrap_fit(cv, s, fs.sub, w, inner)
        sub_fit.append((lines, f, head))
    inline = False
    if name is not None:
        inline = cv.width_mm(name, fs_name, "bold") + 1.7 + chip_width(cv, chip_word, fs.chip) <= inner
    drum_h = ((lh_db if name is not None else 0.0)
              + sum(len(ls) * f * PT_MM * LINE_FACTOR for ls, f, _ in sub_fit)
              + (0.0 if inline else lh_chip) + 2 * PAD + DRUM_E)
    P["drum"] = dict(name=name, fs_name=fs_name, sub=sub_fit, chip=chip_word, inline=inline, h=drum_h,
                     lh_db=lh_db, lh_chip=lh_chip)

    # --- pasos ---------------------------------------------------------------------------------
    steps = []
    for s in row["steps"]:
        steps.append(wrap_fit(cv, L(s), fs.step, "normal", step_w - 2 * PAD))
        BOX_WORDS.append((L(s), len(words_of(L(s)))))
    step_h = max(max(len(ln) * f * PT_MM * LINE_FACTOR for ln, f in steps) + 2 * PAD, 8.6)
    P["steps"], P["step_h"] = steps, step_h

    # --- lo que entrega ------------------------------------------------------------------------
    out_txt = L(row["out"])
    out_lines, fs_out = wrap_fit(cv, out_txt, fs.out, "bold", YIELD_W - YIELD_TIP - 2 * PAD)
    BOX_WORDS.append((out_txt, len(words_of(out_txt))))
    out_h = max(len(out_lines) * fs_out * PT_MM * LINE_FACTOR + 2 * PAD, 9.8)
    P["out"], P["fs_out"], P["out_h"] = out_lines, fs_out, out_h

    # --- alto del núcleo: la caja más alta y la pila de cifras más larga -------------------------
    num_h = max([len(v) for v in nums.values()], default=0) * fs.num * PT_MM * LINE_FACTOR
    P["core_h"] = max(drum_h, step_h, out_h, num_h + 1.8)

    # --- quiebres de definición, al pie de su flecha ---------------------------------------------
    lh_note = fs.note * PT_MM * LINE_FACTOR
    brk = {a: wrap_fit(cv, plate_subst(L(t), R, lang), fs.note, "normal", 46.0)[0]
           for a, t in row.get("brk", {}).items()}
    P["brk"] = brk
    P["brk_h"] = (max([len(v) for v in brk.values()], default=0) * lh_note + 1.5) if brk else 0.0

    # --- nota: exclusión en rojo, o aclaración en gris ---------------------------------------------
    note = row.get("note")
    P["note"], P["note_h"] = None, 0.0
    if note:
        head = ""
        if note["n"] is not None:
            key, dec = note["n"]
            R.on_plate.add(key)
            head = "−" + fmt(R, key, lang, dec) + "  "
        body = head + L(note["text"])
        BOX_WORDS.append((L(note["text"]), len(words_of(L(note["text"])))))
        P["note"] = dict(at=note["at"], kind=note["kind"],
                         lines=wrap_fit(cv, body, fs.note, "normal", 64.0)[0])
        P["note_h"] = len(P["note"]["lines"]) * lh_note + 2.4

    P["h"] = P["core_h"] + P["brk_h"] + P["note_h"]
    return P


def draw_row(cv: Canvas, P, row, lang, xa, xb, ytop, ink, tag):
    fs = P["fs"]
    core_h, step_w, gaps = P["core_h"], P["step_w"], P["gaps"]
    yc = ytop - core_h / 2.0

    # --- cilindro ------------------------------------------------------------------------------
    d = P["drum"]
    drum(cv, xa, yc - d["h"] / 2, DB_W, d["h"], ink, f"{tag}-db")
    xc = xa + DB_W / 2
    yy = yc + d["h"] / 2 - DRUM_E / 2 - PAD
    if d["name"] is not None:
        fn = d["fs_name"]
        if d["inline"]:
            w_name = cv.width_mm(d["name"], fn, "bold")
            x_start = xc - (w_name + 1.7 + chip_width(cv, d["chip"], fs.chip)) / 2
            text(cv, x_start, yy - d["lh_db"] + fn * PT_MM * 0.30, d["name"], fn,
                 weight="bold", colour=ink, ha="left", va="baseline")
            unit_chip(cv, x_start + w_name + 1.7, yy - d["lh_db"] * 0.52, row["unit"], d["chip"], fs.chip)
        else:
            text(cv, xc, yy - d["lh_db"] + fn * PT_MM * 0.30, d["name"], fn, weight="bold",
                 colour=ink, ha="center", va="baseline")
        yy -= d["lh_db"]
    for lines, f, head in d["sub"]:
        for s in lines:
            yy -= f * PT_MM * LINE_FACTOR
            text(cv, xc, yy + f * PT_MM * 0.30, s, f, weight="bold" if head else "normal",
                 colour=ink if head else MUTED, ha="center", va="baseline")
    if not d["inline"]:
        w_chip = chip_width(cv, d["chip"], fs.chip)
        unit_chip(cv, xc - w_chip / 2, yy - d["lh_chip"] * 0.5, row["unit"], d["chip"], fs.chip)

    # --- geometría de pasos y flechas --------------------------------------------------------------
    xs, x = [], xa + DB_W
    for i in range(P["n_steps"]):
        x += gaps[i]
        xs.append(x)
        x += step_w
    x_out = xb - YIELD_W
    spans, prev = [], xa + DB_W
    for i in range(P["n_steps"]):
        spans.append((prev, xs[i]))
        prev = xs[i] + step_w
    spans.append((prev, x_out))

    for i, (lines, f) in enumerate(P["steps"]):
        step_box(cv, xs[i], yc - P["step_h"] / 2, step_w, P["step_h"], ink, f"{tag}-step{i}")
        text_block(cv, xs[i] + step_w / 2, yc, lines, f, colour=INK)

    yield_block(cv, x_out, yc - P["out_h"] / 2, YIELD_W, P["out_h"], ink, f"{tag}-out")
    text_block(cv, x_out + (YIELD_W - YIELD_TIP) / 2, yc, P["out"], P["fs_out"], weight="bold",
               colour="white")

    for a, (x_left, x_right) in enumerate(spans):
        has_num = a in P["nums"]
        # con cifra, la marca de quiebre va en el hueco reservado a la izquierda del recuadro blanco;
        # sin cifra, en el centro del tramo.
        broken = (x_left + BREAK_ROOM * 0.48 if has_num else (x_left + x_right) / 2) \
            if a in P["brk"] else None
        flow_arrow(cv, x_left, x_right, yc, ink, broken_x=broken)
        if has_num:
            xn = ((x_left + BREAK_ROOM) + x_right) / 2 if a in P["brk"] else (x_left + x_right) / 2
            text_block(cv, xn, yc, P["nums"][a], fs.num, weight="bold", colour=INK,
                       count=False, zorder=7,
                       bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))

    # --- quiebre de definición, al pie de su flecha ------------------------------------------------
    y_brk = yc - core_h / 2 - 1.0
    for a, lines in P["brk"].items():
        x_left, x_right = spans[a]
        half = max(cv.width_mm(ln, fs.note) for ln in lines) / 2 + 0.5
        xm = min(max((x_left + x_right) / 2, xa + half), xb - half)
        text_down(cv, xm, y_brk, lines, fs.note, colour=ink, ha="center")

    # --- nota: exclusión en rojo (con flecha hacia abajo) o aclaración en gris ----------------------
    nt = P["note"]
    if nt:
        y_top = yc - core_h / 2 - P["brk_h"] - 0.7
        xm = xs[nt["at"]] + step_w / 2
        if nt["kind"] == "excl":
            from matplotlib.patches import FancyArrowPatch
            cv.ax.add_patch(FancyArrowPatch((xm, y_top + 0.5), (xm, y_top - 2.3), arrowstyle="-|>",
                                            mutation_scale=6.0, lw=1.0, color=EXCL_COL, shrinkA=0,
                                            shrinkB=0, zorder=4))
            wmax = max(cv.width_mm(ln, fs.note) for ln in nt["lines"])
            text_down(cv, min(xm + 1.9, xb - wmax - 0.4), y_top - 0.7, nt["lines"], fs.note,
                      colour=EXCL_COL, ha="left")
        else:
            text_down(cv, xm, y_top - 0.5, nt["lines"], fs.note, colour=MUTED, ha="center")


# ===========================================================================
# Dibujo de la lámina
# ===========================================================================
def build_figure(R: Registry, variant: str, lang: str, path: Path):
    plt, _ = C.style()
    plt.rcParams["savefig.pad_inches"] = 0.0
    from matplotlib.patches import FancyBboxPatch
    fig = plt.figure(figsize=(W_MM / MM_PER_IN, H_MM / MM_PER_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.set_facecolor("white")
    ax.axis("off")
    ax.set_xticks([])
    ax.set_yticks([])
    fig.canvas.draw()
    cv = Canvas(fig, ax)
    del PLATE_WORDS[:]
    del BOX_WORDS[:]
    R.on_plate = set()

    LN = lanes()
    avail = LANES_TOP - LANES_BOT

    # --- medida: se planifica todo antes de dibujar y se reduce el cuerpo si no cabe --------------
    scale, need, plans, lane_h = 1.0, 0.0, [], []
    while True:
        del BOX_WORDS[:]
        plans, lane_h = [], []
        for L_ in LN:
            rows = [plan_row(cv, r, lang, R, X0 + 1.4, X1 - 1.4, scale) for r in L_["rows"]]
            plans.append(rows)
            lane_h.append(FS_LANE * scale * PT_MM * LINE_FACTOR + TITLE_GAP
                          + sum(p["h"] for p in rows) + ROW_GAP * (len(rows) - 1) + 1.6)
        need = sum(lane_h) + SEP_MIN * (len(LN) - 1)
        if need <= avail + TOL_MM or FS_NOTE * scale <= 6.4:
            break
        scale -= 0.01
    if need > avail + TOL_MM:
        warn(f"the six lanes need {need:.1f} mm in {avail:.1f} mm (body scale {scale:.2f})")

    slack = max(avail - sum(lane_h) - SEP_MIN * (len(LN) - 1), 0.0)
    sep = min(SEP_MAX, SEP_MIN + slack * 0.55 / (len(LN) - 1))
    rest = max(avail - sum(lane_h) - sep * (len(LN) - 1), 0.0)
    pad = [rest * h / sum(lane_h) for h in lane_h]

    # --- distintivo de variante, arriba a la derecha ------------------------------------------------
    text(cv, X1, H_MM - 1.2, CFG.VARIANTS[variant]["short"][lang], FS_VARIANT * scale, weight="bold",
         colour=MUTED, ha="right", va="top")

    # --- carriles --------------------------------------------------------------------------------
    y = LANES_TOP
    for i, (L_, rows, h, pad_extra) in enumerate(zip(LN, plans, lane_h, pad)):
        hh = h + pad_extra
        ink, fill = LANE_INK[i], LANE_FILL[i]
        ax.add_patch(FancyBboxPatch((X0 + 0.6, y - hh + 0.6), X1 - X0 - 1.2, hh - 1.2,
                                    boxstyle="round,pad=0.6,rounding_size=1.8", fc=fill, ec=fill,
                                    lw=0.0, zorder=1))
        lh_lane = FS_LANE * scale * PT_MM * LINE_FACTOR
        text(cv, X0 + 2.4, y - 1.0 - lh_lane + FS_LANE * scale * PT_MM * 0.30, L_["title"][lang],
             FS_LANE * scale, weight="bold", colour=ink, ha="left", va="baseline", count=False)
        yr = y - 1.0 - lh_lane - TITLE_GAP - pad_extra * 0.5
        for j, (P, row) in enumerate(zip(rows, L_["rows"])):
            draw_row(cv, P, row, lang, X0 + 1.4, X1 - 1.4, yr, ink, f"{L_['key']}{j}")
            yr -= P["h"] + ROW_GAP
        y -= hh
        if i < len(LN) - 1:
            yb = y - sep / 2
            ax.plot([X0, X1], [yb, yb], color=EXCL_COL, lw=1.0, ls=(0, (3.0, 2.2)), zorder=4)
            if i == 2:
                text(cv, (X0 + X1) / 2, yb, tr("barrier", lang), FS_BARRIER * scale, weight="bold",
                     colour=EXCL_COL, ha="center", va="center", zorder=7,
                     bbox=dict(boxstyle="round,pad=0.30", fc="white", ec=EXCL_COL, lw=0.7))
            y -= sep

    # --- presupuesto de texto ----------------------------------------------------------------------
    n_words = len(PLATE_WORDS)
    max_box = max([b[1] for b in BOX_WORDS], default=0)
    if n_words > WORD_BUDGET:
        warn(f"{variant}/{lang}: the plate carries {n_words} words, over the {WORD_BUDGET} budget")
    for lab, n in BOX_WORDS:
        if n > BOX_WORD_BUDGET:
            warn(f"{variant}/{lang}: box over {BOX_WORD_BUDGET} words ({n}): {lab}")

    # --- verificador de composición -----------------------------------------------------------
    # La lámina es un DIAGRAMA de un solo lienzo dibujado a mano: la regla de tres filas por dos
    # columnas no le aplica y se la exime declarándola con `grid=None`. Todo lo demás sí: nada de
    # texto fuera del lienzo, nada impreso sobre otro texto y nada por debajo de 6 pt (esto último lo
    # vigila `MIN_FS_USED` al final del módulo). Se mide sobre el renderizador real, con la lámina ya
    # terminada, y no se guarda en silencio una lámina con defectos: `main` termina con error.
    C.plate_declare(fig, path.name, grid=None)
    for prob in C.check_layout(fig, panels=False):
        LAYOUT_PROBLEMS.append(f"{variant}/{lang} {path.name}: {prob}")

    C.save_fig(fig, path, dpi=600)
    plt.close(fig)
    return path, cv.n_boxes, n_words, max_box


# ===========================================================================
# Tabla de recuentos y pie de la figura
# ===========================================================================
QUESTION = {
    Q_UNIT: {"es": "1 · Qué es una fila", "en": "1 · What one row is"},
    Q_IN: {"es": "2 · A la entrada", "en": "2 · At entry"},
    Q_SEL: {"es": "2 · Tras la selección de autismo", "en": "2 · After the autism selection"},
    Q_EXCL: {"es": "2 · Excluido o no estimable", "en": "2 · Excluded or not estimable"},
    Q_OUT: {"es": "3 · Qué se cuenta al final", "en": "3 · What is finally counted"},
    Q_BREAK: {"es": "3 · Quiebre de definición de la serie", "en": "3 · Definition break in the series"},
}
UNIT_KIND_LABEL = {RECORD: {"es": "registros", "en": "records"},
                   PERSON: {"es": "personas", "en": "people"},
                   PLACE: {"es": "comunas", "en": "comunas"}}
COLS = {
    "question": {"es": "Pregunta", "en": "Question"},
    "source": {"es": "Fuente", "en": "Source"},
    "kind": {"es": "La fila cuenta", "en": "The row counts"},
    "label": {"es": "Cifra", "en": "Count"},
    "unit": {"es": "Unidad", "en": "Unit"},
    "value": {"es": "Valor", "en": "Value"},
    "plate": {"es": "En el esquema", "en": "On the schematic"},
    "source_file": {"es": "Tabla de origen", "en": "Source table"},
    "key": {"es": "Columna o clave", "en": "Column or key"},
}
YES_NO = {"es": ("sí", "no"), "en": ("yes", "no")}


def formatted_table(R: Registry, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    num = R.frame().copy()
    order = {q: i for i, q in enumerate([Q_UNIT, Q_IN, Q_SEL, Q_EXCL, Q_OUT, Q_BREAK])}
    num["_o"] = num.question.map(order)
    num = num.sort_values(["_o", "source", "key"]).drop(columns="_o").reset_index(drop=True)
    num["on_plate"] = [k in R.on_plate for k in num.key]
    dec = [2 if u == "percent" else (0 if not str(u).startswith("per 100,000") else 1) for u in num.unit_en]
    yes, no = YES_NO[lang]
    out = pd.DataFrame({
        COLS["question"][lang]: [QUESTION[q][lang] for q in num.question],
        COLS["source"][lang]: num.source,
        COLS["kind"][lang]: [UNIT_KIND_LABEL[k][lang] for k in num.unit_kind],
        COLS["label"][lang]: num.label_es if lang == "es" else num.label_en,
        COLS["unit"][lang]: num.unit_es if lang == "es" else num.unit_en,
        COLS["value"][lang]: [C.fmt_number(v, d, lang) if pd.notna(v) else "n/e" for v, d in zip(num.value, dec)],
        COLS["plate"][lang]: [yes if p else no for p in num.on_plate],
        COLS["source_file"][lang]: num.source_file,
        COLS["key"][lang]: num.source_column_or_key,
    })
    return out, num


def table_titles(variant: str, lang: str, n_rows: int, n_plate: int) -> dict:
    vl = CFG.VARIANTS[variant]["label"][lang]
    if lang == "es":
        return {TABLE_NAME: {
            "title": (f"Cifras que sostienen la {main_figure_label(FIG_NAME, 'es')}, con la unidad de análisis y "
                      f"el origen de cada una — variante {vl}"),
            "note": ("Una fila por cifra del flujo de datos, ordenadas por la pregunta que responden: qué es una fila, "
                     "cuántas hay a la entrada y tras la selección de autismo, qué se excluye y con qué motivo, y qué se "
                     "cuenta al final. La columna «En el esquema» distingue las cifras que la Figura 1 imprime sobre las "
                     f"flechas ({n_plate} de {n_rows}) de las que la sostienen sin aparecer dibujadas. La columna «La fila "
                     "cuenta» distingue las fuentes que cuentan registros (un episodio de atención, un egreso, un reporte "
                     "mensual de establecimiento) de las que cuentan personas (una persona en un stock a una fecha, una "
                     "persona encuestada, un estudiante) y de las que cuentan comunas (la cartografía y el índice de "
                     "privación comunal); esa distinción gobierna toda comparación del artículo. Cada cifra se lee en "
                     "tiempo de ejecución de la tabla de origen y la columna que se indican, para la variante analizada; "
                     "ninguna está escrita a mano. Los recuentos son reconocimiento administrativo, nunca prevalencia ni "
                     "incidencia; en el GRD son «episodios con F84 documentado» y F84 principal es una serie separada. Las "
                     "fuentes no se enlazan por persona: no hay identificador común y las personas se cuentan solo dentro "
                     "de cada año. Stocks y flujos nunca comparten eje, y los recuentos de establecimientos reportantes "
                     f"acompañan a toda cifra REM. N informado: {n_rows} filas. Módulo {SCRIPT}.")}}
    return {TABLE_NAME: {
        "title": (f"Counts behind {main_figure_label(FIG_NAME, 'en')}, with the unit of analysis and the origin "
                  f"of each — {vl}"),
        "note": ("One row per count in the data flow, ordered by the question it answers: what one row is, how many at "
                 "entry and after the autism selection, what is excluded and why, and what is finally counted. The column "
                 f"'On the schematic' separates the counts Figure 1 prints on its arrows ({n_plate} of {n_rows}) from "
                 "those that support it without being drawn. The column 'The row counts' separates the sources that count "
                 "records (an episode of care, a discharge, a monthly establishment report) from those that count people "
                 "(a person in a stock at one date, a survey respondent, a student) and from those that count comunas "
                 "(the cartography and the comuna deprivation index); that distinction governs every comparison in the "
                 "paper. Every count is read at run time from the source table and column named here, for the variant "
                 "analysed; none is hard-coded. Counts are administrative recognition, never prevalence or incidence; in "
                 "GRD they are 'episodes with documented F84' and principal F84 is a separate series. The sources are not "
                 "person-linked: there is no common identifier and persons are counted only within a year. Stocks and "
                 "flows never share an axis, and reporting-establishment counts accompany every REM figure. "
                 f"Reporting N: {n_rows} rows. Module {SCRIPT}.")}}


def caption(variant: str, lang: str, R: Registry) -> dict:
    """Título y pie de la Figura 1: lo que hace falta para LEER el esquema, y nada que el esquema ya diga.

    PRESUPUESTO, y por qué manda. El documento imprime el título y el pie en UN SOLO párrafo bajo la
    lámina; la lámina mide 245 mm en una página A4 y deja 3,876 cm, que al SUELO tipográfico de la
    leyenda —7,0 pt desde la tarea Y2 de esta fase, `docx_builder.PLATE_CAP_MIN_PT`— son TRECE líneas.
    El pie anterior llevaba a la vez el bloque de «cómo leer» que se sacó de la lámina y el recitado
    carril por carril de las cifras: 37 líneas en inglés y 39 en español, de modo que se partía y la cola
    ocupaba una página propia rotulada «Figura 1 (continuación)» en el artículo y en los cuatro
    manuscritos combinados.

    QUÉ SE CONSERVA: lo que no está en ningún otro sitio. Qué significan las tres formas y las tres
    unidades de análisis, la regla de que ningún registro se enlaza entre sistemas y que las personas se
    cuentan solo dentro de un año, dónde cambia la definición de una serie, las reglas que gobiernan toda
    la lámina y de dónde salen las cifras.

    QUÉ SE VA: el recitado de cifras, que era repetición. Las que el esquema imprime se leen en el
    esquema —41 de 62— y las 21 que no imprime están en la tabla de recuentos que lo acompaña, con su
    unidad, su tabla de origen, su columna y la marca «en el esquema». Entre ellas las dos de fechas
    inválidas, que distinguen los episodios F84 de los episodios GRD de cualquier diagnóstico (defecto
    10): la distinción sigue vigilada por `tests/test_self_counts.py`, ahora sobre la tabla, que es donde
    esa cifra vive. El TÍTULO también se acorta —medía 217 caracteres, contra 136, 191 y 146 de las Figuras
    2, 3 y 5—: decía dos veces lo que es el estudio. Título y pie comparten párrafo, de modo que lo que
    ocupa el título se lo quita al pie.

    MEDIDA (docx_builder._wrapped_lines sobre título + pie, 7,0 pt, columna de 19,6 cm, las dos
    variantes): 12 líneas y 3,514 cm en inglés, 13 líneas y 3,798 cm en español, dentro de los 3,876 cm
    de la página. Sin cola y sin página de continuación.

    Ninguna cifra está escrita a mano: `n()` e `y()` las leen del registro de la variante en curso.
    """
    vl = CFG.VARIANTS[variant]["label"][lang]

    def n(key, dec=0):
        return fmt(R, key, lang, dec)

    def y(key):
        return str(int(R.value(key)))

    # Los dos códigos de autismo del REM empiezan hoy el mismo año; si alguna vez dejaran de hacerlo, el
    # pie lo diría por separado en vez de imprimir un año que valdría solo para uno de los dos.
    a05y, p6y = y("a05_era_year"), y("p6_era_year")

    if lang == "es":
        title = (f"{main_figure_label(FIG_NAME, 'es')}. Qué se hizo con cada base de datos: las seis familias "
                 f"de fuentes del estudio multisistema, Chile 2019–2025 — variante {vl}")
        quiebre = (f"los códigos de autismo de las Series A y P del REM empiezan en {a05y}" if a05y == p6y else
                   f"el código de autismo de la Serie A del REM empieza en {a05y} y el de la Serie P en {p6y}")
        cap = (
            "Cada carril se lee de izquierda a derecha. CÓMO ESTÁ DIBUJADO. El cilindro es una base de datos; la caja "
            "redondeada, un paso aplicado a ella; el bloque con punta, lo que el carril entrega. Su distintivo dice "
            "qué es una fila, en una palabra y una forma: cuadrado, REGISTROS (un episodio, un egreso, un reporte "
            "mensual); círculo, PERSONAS (una persona en un stock a una fecha, una encuestada, un estudiante); "
            "hexágono, COMUNAS (cartografía, privación). En un carril de registros una persona puede repetirse: "
            "ningún total es un número de personas. Las flechas llevan solo cifras: la n a la entrada, la n tras la "
            "selección de autismo, los extremos de la serie. El rojo marca solo lo excluido o nunca sumado, con su "
            f"signo menos. Dos trazos sobre la flecha marcan un quiebre de definición: {quiebre}, la fuente de "
            f"educación cambia en {y('edu_source_year')}, el GRD lleva panel fijo y observado. "
            "SIN ENLACE, lo que enuncia la banda de trazos rojos. Ningún registro se enlaza entre sistemas: los seis "
            "carriles no comparten identificador; nada dibujado es una trayectoria ni una cascada, y una persona "
            "puede estar contada en más de un carril. Las personas se cuentan solo dentro de un año: el identificador "
            "del GRD cambia de formato entre 2020 y 2021. "
            "REGLAS. Los recuentos son reconocimiento administrativo, no prevalencia ni incidencia; en el GRD son "
            "«episodios con F84 documentado» y F84 principal es una serie aparte; stocks y flujos nunca comparten "
            "eje; cero, ausente y «sin reporte» son distintos; lugar de atención y residencia nunca se mezclan sin "
            "advertirlo; las celdas territoriales con menos de 5 eventos se suprimen; y no se estima ningún efecto de "
            "la Ley 21.545 (marzo de 2023). "
            "ORIGEN DE LAS CIFRAS. Cada cifra se lee en tiempo de ejecución de su tabla de origen para la variante "
            "analizada; la tabla de recuentos da a cada una su unidad, su origen, su columna y si está dibujada, y "
            "guarda las demás, exclusiones incluidas. La tabla de fuentes del suplemento enumera quince fuentes de "
            "datos, una por fila.")
        return {FIG_NAME: {"title": title, "caption": cap}}

    title = (f"{main_figure_label(FIG_NAME, 'en')}. What was done with each database: the six data families "
             f"of the multisource study, Chile 2019–2025 — {vl}")
    brk = (f"the REM autism codes of Series A and P begin in {a05y}" if a05y == p6y else
           f"the REM autism code of Series A begins in {a05y} and that of Series P in {p6y}")
    cap = (
        "Each lane is read from left to right. HOW IT IS DRAWN. A cylinder is a database, a rounded box a step "
        "applied to it, a pointed block what the lane yields. Its badge says what one row is, in a word and a shape: "
        "square, RECORDS (an episode of care, a discharge, a monthly report); circle, PEOPLE (a person in a stock at "
        "one date, a respondent, a student); hexagon, COMUNAS (cartography, deprivation). In a record lane one person "
        "may recur and no total is a number of people. Arrows carry only figures: the n at entry, the n after the "
        "autism selection, the ends of the series. Red marks only what is excluded or never added, with its minus "
        f"sign. Two strokes across an arrow mark a definition break: {brk}, the education source changes in "
        f"{y('edu_source_year')}, the GRD arrow carries fixed and observed panels. "
        "NO LINKAGE, what the dashed red band states once. No record is linked across systems: the six lanes share no "
        "identifier; nothing here is a trajectory or a cascade, and one person may be counted in more than one lane. "
        "Persons are counted only within a year: the GRD identifier changes format between 2020 and 2021. "
        "RULES. Counts are administrative recognition, not prevalence or incidence; in GRD they are 'episodes with "
        "documented F84', principal F84 being a separate series; stocks and flows never share an axis; zero, missing "
        "and 'not reported' are distinct; place of care and residence are never mixed without a warning; territorial "
        "cells under 5 events are suppressed; and no effect of Law 21.545 (March 2023) is estimated. "
        "SOURCE OF THE FIGURES. Every figure is read at run time from its source table, for the variant analysed; the "
        "companion table of counts gives each its unit, source, column and whether it is drawn, and holds the rest, "
        "exclusions included. The supplementary source table lists fifteen data sources, one per row.")
    return {FIG_NAME: {"title": title, "caption": cap}}




def merge_json(path: Path, new: dict) -> None:
    current = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
    current.update(new)
    C.atomic_write_json(current, path)


def out_dir(variant: str, lang: str, *parts: str) -> Path:
    p = CFG.OUT.joinpath(variant, lang, *parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ===========================================================================
# main
# ===========================================================================
def main() -> int:
    t0 = time.time()
    log("loading tidy tables and values")
    D = load()

    regs = {v: build_counts(D, v) for v in VARIANTS}

    counts = pd.concat([regs[v].frame() for v in VARIANTS], ignore_index=True)
    counts = counts[["variant", "question", "source", "unit_kind", "key", "label_en", "label_es",
                     "unit_en", "unit_es", "value", "source_file", "source_column_or_key"]]
    C.atomic_write_csv(counts, CFG.TIDY / "dataflow_counts.csv")
    log(f"dataflow_counts.csv: {len(counts)} rows ({len(regs['con_rett'].rows)} per variant)")

    ctrl = build_controls(D, regs)
    C.atomic_write_csv(ctrl, CTRL_DIR / f"{MODULE}_controls.csv")
    bad = ctrl[ctrl.status == "differs"]
    log(f"controls: {len(ctrl)} checks, {int((ctrl.status == 'ok').sum())} ok, "
        f"{int((ctrl.status == 'info').sum())} info, {len(bad)} differ")
    if len(bad):
        for _, r in bad.iterrows():
            log(f"MISMATCH {r['name']} [{r['key']}]: expected {r.expected}, observed {r.observed}")
        raise SystemExit(f"[{MODULE}] {len(bad)} figure counts do not match their authoritative source; see "
                         f"outputs/controls/{MODULE}_controls.csv")

    outputs = [str(CFG.TIDY / "dataflow_counts.csv"), str(CTRL_DIR / f"{MODULE}_controls.csv")]
    box_counts: list[int] = []
    word_counts: list[int] = []
    box_word_max: list[int] = []
    for variant in VARIANTS:
        for lang in LANGS:
            t1 = time.time()
            R = regs[variant]
            R.used = set()
            fdir = out_dir(variant, lang, "figures")
            xdir = out_dir(variant, lang, "extra", "tables")
            p, n_boxes, n_words, max_box = build_figure(R, variant, lang, fdir / f"{FIG_NAME}.png")
            merge_json(fdir / "captions.json", caption(variant, lang, R))
            fmtd, num = formatted_table(R, lang)
            C.atomic_write_csv(fmtd, xdir / f"{TABLE_NAME}.csv")
            C.atomic_write_csv(num, xdir / f"{TABLE_NAME}_numeric.csv")
            merge_json(xdir / "titles.json", table_titles(variant, lang, len(num), int(num.on_plate.sum())))
            outputs += [str(p), str(fdir / "captions.json"), str(xdir / f"{TABLE_NAME}.csv"),
                        str(xdir / f"{TABLE_NAME}_numeric.csv"), str(xdir / "titles.json")]
            missing = sorted(R.used - set(R.rows))
            if missing:
                raise SystemExit(f"[{MODULE}] keys printed but not registered: {missing}")
            # El esquema imprime un subconjunto deliberado de las cifras registradas: el resto sostiene
            # la figura desde la tabla de recuentos, que las lleva todas y marca cuáles se dibujan.
            off = sorted(set(R.rows) - R.on_plate)
            box_counts.append(n_boxes)
            word_counts.append(n_words)
            box_word_max.append(max_box)
            log(f"{variant}/{lang}: schematic + counts table in {time.time() - t1:.1f} s "
                f"({len(R.on_plate)} counts drawn, {len(off)} carried only by the table, {n_boxes} boxes, "
                f"{n_words} words, longest box {max_box} words)")

    # El presupuesto de texto es una condición del encargo, no una preferencia: si una lámina se pasa,
    # el módulo termina con error igual que si tuviera un defecto de composición.
    if max(word_counts, default=0) > WORD_BUDGET or max(box_word_max, default=0) > BOX_WORD_BUDGET:
        raise SystemExit(f"[{MODULE}] the schematic is over its text budget: "
                         f"{max(word_counts, default=0)} words (limit {WORD_BUDGET}), longest box "
                         f"{max(box_word_max, default=0)} words (limit {BOX_WORD_BUDGET}); see the WARNING "
                         f"lines above")

    min_fs = round(min(MIN_FS_USED), 2) if MIN_FS_USED else None
    if min_fs is not None and min_fs < FS_HARD_FLOOR - 1e-9:
        raise SystemExit(f"[{MODULE}] smallest type on the plate is {min_fs} pt, below the {FS_HARD_FLOOR} pt floor")
    if LAYOUT_PROBLEMS:
        for prob in LAYOUT_PROBLEMS:
            log(f"LAYOUT {prob}")
        raise SystemExit(f"[{MODULE}] {len(LAYOUT_PROBLEMS)} layout problem(s) on the four plates; see the "
                         f"LAYOUT lines above")
    log(f"layout check: {len(VARIANTS) * len(LANGS)} plates measured on the real renderer, no problems")
    runtime = time.time() - t0
    runlog = dict(module=MODULE, script=SCRIPT, timestamp=datetime.now(timezone.utc).isoformat(),
                  runtime_seconds=round(runtime, 1), variants=VARIANTS, languages=LANGS,
                  figure_mm=[W_MM, H_MM], dpi=600, min_font_pt=min_fs,
                  layout_check=dict(plates=len(VARIANTS) * len(LANGS), problems=len(LAYOUT_PROBLEMS),
                                    panels_rule="exempt: single-canvas diagram"),
                  n_counts_per_variant=len(regs["con_rett"].rows), n_controls=len(ctrl),
                  n_counts_drawn=len(regs["con_rett"].on_plate),
                  n_boxes=max(box_counts) if box_counts else 0,
                  words=dict(budget=WORD_BUDGET, per_plate=word_counts, max=max(word_counts) if word_counts else 0,
                             box_budget=BOX_WORD_BUDGET,
                             longest_box=max(box_word_max) if box_word_max else 0),
                  outputs=sorted(set(outputs)), warnings=sorted(set(WARNINGS)),
                  inputs=["outputs/values_<variant>.json", "outputs/tidy/grd_year_summary.csv",
                          "outputs/tidy/grd_length_of_stay.csv", "outputs/tidy/grd_identifier_audit.csv",
                          "outputs/tidy/deis_year_summary.csv", "outputs/tidy/rem_pathway_annual.csv",
                          "outputs/tidy/coverage_layers_year.csv", "outputs/tidy/survey_estimates.csv",
                          "outputs/tidy/pie_series.csv", "outputs/tidy/junaeb_tea_year_level.csv",
                          "outputs/tidy/education_summary_year.csv",
                          "outputs/tidy/grd_fixed_panel_hospitals.csv", "outputs/tidy/comuna_crosswalk.csv",
                          "outputs/tidy/spatial_comuna_standardised.csv"])
    C.atomic_write_json(runlog, CTRL_DIR / f"{MODULE}_runlog.json")
    log(f"done in {runtime:.1f} s; {len(set(outputs))} outputs; min font {min_fs} pt; "
        f"warnings: {len(set(WARNINGS))}")
    for w in sorted(set(WARNINGS)):
        log(f"warning: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
