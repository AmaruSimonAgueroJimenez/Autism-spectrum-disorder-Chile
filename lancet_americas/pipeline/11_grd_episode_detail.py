#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""11_grd_episode_detail.py — Detalle episódico del núcleo hospitalario GRD 2019–2024 para el material extendido
(paso 11 del pipeline Lancet Regional Health – Americas).

El módulo 01 (`01_grd_core.py`) conservó solo agregados de año/panel/actividad/posición/edad/sexo/hospital y
profundidad de codificación. Este módulo vuelve a leer los archivos crudos `GRD_PUBLICO_{2019..2024}.csv`
(sep='|', 129 columnas, todo como texto, por trozos con `common.iter_grd`) y extrae las dimensiones
episódicas adicionales que exige la metodología extendida y el suplemento, para las tres series de
definición y para el grupo de comparación de todos los episodios GRD.

Series de definición (columna `variant` en todas las salidas):
  * `con_rett`            cualquier F84.x (incluye F84.2, síndrome de Rett) — `config.VARIANTS['con_rett']`.
  * `sin_rett`            F84.x excepto F84.2 — `config.VARIANTS['sin_rett']`.
  * `strict_autism_f840`  solo F84.0 (autismo infantil), idéntica en ambas variantes (mismo nombre que en el módulo 01).
  * `all_episodes`        grupo de comparación: todos los episodios GRD del mismo año, panel y actividad
                          (`position = 'all'`). Nunca es un numerador de autismo.

Posición del código F84 en el episodio (columna `position`):
  * `any`             F84 en DIAGNOSTICO1..35.
  * `principal`       F84 en DIAGNOSTICO1 (incluye los episodios que además lo repiten como secundario).
  * `secondary_only`  F84 en DIAGNOSTICO2..35 y no en DIAGNOSTICO1.
El outcome es «episodios con F84 documentado», nunca «hospitalizaciones por autismo», y nunca prevalencia ni
incidencia: son recuentos de reconocimiento administrativo.

Panel (columna `panel`): `observed` = panel anual observado (65, 65, 65, 65, 68 y 72 hospitales en 2019–2024);
`fixed65` = panel fijo de 65 hospitales leído de `outputs/tidy/grd_fixed_panel_hospitals.csv` (módulo 01).
Nunca se usan 72 hospitales como panel fijo.

Salidas tidy (escritura atómica, solo agregados; nunca salen microdatos):
  outputs/tidy/grd_monthly.csv                año × mes de ingreso × variante × posición × panel: episodios F84,
                                              episodios totales del mismo mes/panel, tasa por 100.000 episodios con IC
                                              exacto de Poisson e índice estacional dentro del año (media del año = 1).
  outputs/tidy/grd_length_of_stay.csv         año × variante × posición × actividad × panel: n con fechas válidas,
                                              media, DE, mediana, p25, p75, p90, máximo, días totales y n con estadía 0,
                                              más el mismo resumen para todos los episodios GRD como comparación.
  outputs/tidy/grd_los_age.csv                lo mismo por grupo etario quinquenal OMS (`epi_helpers.AGE_GROUPS`).
  outputs/tidy/grd_episode_features.csv       año × variante × posición × panel × variable × valor: episodios y % dentro
                                              de la celda, para TIPO_INGRESO, TIPO_ACTIVIDAD, TIPO_PROCEDENCIA, TIPOALTA,
                                              PREVISION (cruda y agrupada), ESPECIALIDAD_MEDICA (20 principales + «otra»),
                                              SERVICIO_SALUD, NACIONALIDAD y ETNIA (crudas y agrupadas),
                                              IR_29301_SEVERIDAD, IR_29301_MORTALIDAD, uso de pabellón, hospital de
                                              procedencia, sexo, tramo etario, grupo OMS y tramo de estadía, con la misma
                                              distribución para todos los episodios GRD como comparación.
  outputs/tidy/grd_grd_weight.csv             año × variante × posición × panel: n, media, DE, mediana, p25 y p75 de
                                              IR_29301_PESO, y los 15 grupos IR_29301_COD_GRD más frecuentes entre los
                                              episodios F84 (más una fila «otros grupos»).
  outputs/tidy/grd_codiagnoses.csv            año × variante × posición × panel × posición del co-diagnóstico ×
                                              categoría CIE-10 de tres caracteres: episodios (un episodio cuenta una vez
                                              por categoría y posición) y % de los episodios F84 de la celda. Las filas con
                                              `position = secondary_only` y `code_position = principal` son el diagnóstico
                                              principal cuando F84 es solo secundario.
  outputs/tidy/grd_codiagnosis_chapters.csv   lo mismo agregado a capítulos CIE-10 y a bloques de salud mental
                                              (`scripts/report_helpers.icd_chapter` / `mental_block`).
  outputs/tidy/grd_readmission.csv            era de identificador × año × variante × posición × panel × horizonte
                                              (30/90/365 días): egresos con identificador y fechas válidas, elegibles con
                                              el horizonte completo dentro de la era, reingresos por cualquier causa y
                                              reingresos con un código F84, con IC de Wilson. Nunca cruza el corte
                                              2020/2021 del identificador.
  outputs/tidy/grd_multiplicity.csv           era × variante × posición × panel: episodios por identificador
                                              (1, 2, 3, 4–5, 6+), personas y episodios.
  outputs/tidy/grd_territory.csv              año × variante × posición × panel × nivel (comuna/región): episodios,
                                              personas dentro del año, CUT por el crosswalk auditable
                                              `outputs/tidy/comuna_crosswalk.csv`, método de enlace y marca de supresión
                                              para celdas con menos de 5 eventos; incluye los nombres no enlazados.
  outputs/tidy/grd_age_single_year.csv        año × variante × posición × panel × sexo × edad simple 0–100 (100 = 100 o más)
                                              y «desconocida»: episodios, más todos los episodios GRD como comparación.
  outputs/tidy/grd_episode_detail_dictionary.csv  una fila por tabla con la definición completa de la unidad, el
                                              denominador, la cobertura, la era de definición, el archivo fuente y las
                                              columnas. Las tablas llevan `unit`, `denominator` y `script` en cada fila y
                                              remiten a este diccionario para el texto largo (repetirlo en cada fila
                                              multiplicaría por diez el tamaño de las tablas grandes).

  outputs/<variante>/<idioma>/extra/tables/E*.csv (+ _numeric.csv + titles.json)
                                              versiones formateadas por idioma (coma decimal en es, punto en en; n junto
                                              a %; IC como «lo–hi»; «n/e» donde no es estimable) para el suplemento.

  outputs/controls/11_grd_episode_detail_controls.csv   esperado frente a observado (grd_year_summary, config.CONTROLS,
                                              suma de meses = total anual, co-diagnósticos ≤ episodios × 35, comparación
                                              con `output_files/consolidacion/grd_epi_los_summary.csv` del primer estudio).
  outputs/controls/11_grd_episode_detail_runlog.json    procedencia (SHA-256, bytes, mtime), tiempos por año y por pasada.

Definiciones operativas adicionales:
  * estadía (LOS) = (FECHAALTA − FECHA_INGRESO) en días, solo cuando ambas fechas se analizan y el alta no es anterior
    al ingreso; las fechas no analizables se cuentan e informan y nunca se imputan.
  * mes = mes de FECHA_INGRESO; los episodios sin fecha analizable se informan en la fila `month = 0` («desconocido»)
    y quedan fuera del índice estacional.
  * edad = floor((FECHA_INGRESO − FECHA_NACIMIENTO)/365,25); <0 o >110 → desconocida; grupos OMS de `epi_helpers`.
  * era de identificador: 2019–2020 (CIP_ENCRIPTADO de 6 dígitos) y 2021–2024 (8–9 dígitos; la columna cambia de nombre a
    ID_BENEFICIARIO en 2024 sin cambiar de formato). El módulo 01 documenta 0 identificadores compartidos entre 2020 y
    2021 y 762 entre 2023 y 2024, por lo que las eras son las de `scripts/grd_trajectories.ERAS`. Las personas nunca se
    deduplican entre eras.
  * cero, ausente y «no informado» se mantienen como estados distintos: los valores vacíos aparecen como «no informado»
    y nunca como cero.

Uso: python3 lancet_americas/pipeline/11_grd_episode_detail.py
       [--years 2019 ... 2024] [--chunksize 200000] [--no-hash] [--no-extra] [--skip-linkage]
       [--max-chunks N (solo pruebas: los controles no se reproducen)]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib  # noqa: E402  — report_helpers importa pyplot al cargarse
matplotlib.use("Agg")

LANCET_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANCET_DIR))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
from labels import t as LBL  # noqa: F401,E402  — rótulos compartidos (se usan en las tablas formateadas)

sys.path.insert(0, str(CFG.REPO / "scripts"))
import labels as LB  # noqa: E402  (glosas CIE-10 bilingües y categorías agrupadas del episodio)
from report_helpers import icd_chapter, icd_label, mental_block  # noqa: E402
from grd_epidemiology import group_ethnicity, group_nationality, group_prevision  # noqa: E402

MODULE = "11_grd_episode_detail"
SCRIPT = str(Path(__file__).resolve().relative_to(CFG.REPO))
CONTROLS_DIR = CFG.OUT / "controls"
CONTROLS_DIR.mkdir(parents=True, exist_ok=True)

DIAGS = C.GRD_DIAG_COLS
ID_CANDIDATES = ["CIP_ENCRIPTADO", "ID_BENEFICIARIO"]
FEATURE_RAW = ["TIPO_INGRESO", "TIPO_ACTIVIDAD", "TIPO_PROCEDENCIA", "TIPOALTA", "PREVISION",
               "ESPECIALIDAD_MEDICA", "SERVICIO_SALUD", "NACIONALIDAD", "ETNIA",
               "IR_29301_SEVERIDAD", "IR_29301_MORTALIDAD"]
EXTRA_RAW = ["COD_HOSPITAL", "SEXO", "FECHA_NACIMIENTO", "FECHA_INGRESO", "FECHAALTA", "COMUNA", "PROVINCIA",
             "USOSPABELLON", "HOSPPROCEDENCIA", "IR_29301_COD_GRD", "IR_29301_PESO"]

VARIANT_CODES: dict[str, set[str]] = {name: set(spec["grd_subcodes"]) for name, spec in CFG.VARIANTS.items()}
VARIANT_CODES["strict_autism_f840"] = {"F840"}
VARIANTS = list(VARIANT_CODES)
PRIMARY_VARIANT = "con_rett"
COMPARISON = "all_episodes"
POSITIONS = ["any", "principal", "secondary_only"]
PANELS = ["observed", "fixed65"]
ACTIVITIES = ["all", "hospitalisation", "cma", "other"]
ERAS = {"2019-2020": [2019, 2020], "2021-2024": [2021, 2022, 2023, 2024]}
HORIZONS = [30, 90, 365]
AGE_LEVELS = list(C.AGE_GROUPS) + ["unknown"]
AGE_BANDS = ["0-4", "5-9", "10-14", "15-19", "20-29", "30-44", "45+"]
LOS_BINS = ["0", "1", "2", "3-4", "5-7", "8-14", "15-30", "31-90", "91+"]
MULTIPLICITY_BINS = ["1", "2", "3", "4-5", "6+"]
TOP_SPECIALTIES = 20
TOP_GRD_GROUPS = 15
SUPPRESSION_THRESHOLD = 5
INVALID_ID_VALUES = {"", "0", "-1", "NA", "NAN", "NULL", "DESCONOCIDO", "SIN INFORMACION", "SIN INFORMACIÓN"}
MAX_DIAG_FIELDS = len(DIAGS)  # 35

SOURCE_FILES = "GRD_PUBLICO_2019..2024.csv (FONASA/MINSAL, sep='|', 129 columnas; SHA-256 en outputs/tidy/data_provenance.csv)"
DEFINITION_ERA = ("CIE-10 F84 en DIAGNOSTICO1..35; con_rett = cualquier F84.x; sin_rett = F84.x salvo F84.2; "
                  "strict_autism_f840 = F84.0; all_episodes = todos los episodios GRD (comparación, no autismo)")
COVERAGE = ("Hospitales públicos que reportan al GRD: panel observado 65/65/65/65/68/72 (2019–2024); "
            f"{C.fixed_panel_gloss('es', 'definition')} (outputs/tidy/grd_fixed_panel_hospitals.csv)")


# ---------------------------------------------------------------------------
# Utilidades de texto, códigos y fechas (idénticas a los módulos 01, 03 y 08c)
# ---------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def normalize_name(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = strip_accents(str(value)).upper().replace("'", " ").replace("’", " ").replace("-", " ").replace("¿", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", text)).strip()


def normalise_codes(series: pd.Series) -> np.ndarray:
    out = (series.fillna("").astype(object).str.replace(".", "", regex=False).str.replace(" ", "", regex=False)
           .str.strip().str.upper())
    return out.to_numpy(dtype=object)


def classify_activity(raw: str) -> str:
    key = strip_accents(raw or "").upper().strip()
    if key == "HOSPITALIZACION":
        return "hospitalisation"
    if key.startswith("CIRUGIA MAYOR AMBULATORIA"):
        return "cma"
    return "other"


def parse_dates(series: pd.Series) -> pd.Series:
    """Solo los dos formatos observados (AAAA-MM-DD y DD-MM-AAAA); todo lo demás es NaT (nunca se infiere)."""
    s = series.fillna("").astype(object).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}$").to_numpy(dtype=bool)
    dmy = s.str.match(r"^\d{2}-\d{2}-\d{4}$").to_numpy(dtype=bool)
    if iso.any():
        out.loc[iso] = pd.to_datetime(s.loc[iso], format="%Y-%m-%d", errors="coerce")
    if dmy.any():
        out.loc[dmy] = pd.to_datetime(s.loc[dmy], format="%d-%m-%Y", errors="coerce")
    return out


def valid_id_mask(ids: pd.Series) -> np.ndarray:
    return (~ids.str.upper().isin(INVALID_ID_VALUES)).to_numpy(dtype=bool)


def clean_text(series: pd.Series) -> pd.Series:
    """Texto crudo del productor con los vacíos marcados como «no informado» (nunca cero)."""
    s = series.fillna("").astype(object).str.strip()
    return s.mask(s.eq("") | s.str.upper().isin({"NAN", "NA", "NULL"}), "no informado")


def group_usos_pabellon(series: pd.Series) -> pd.Series:
    n = pd.to_numeric(series.fillna("").astype(object).str.strip(), errors="coerce")
    out = pd.Series("no informado", index=series.index, dtype=object)
    out[n == 0] = "0"
    out[n == 1] = "1"
    out[n == 2] = "2"
    out[n >= 3] = "3+"
    return out


def group_transfer_origin(series: pd.Series) -> pd.Series:
    s = clean_text(series)
    return pd.Series(np.where(s.eq("no informado"), "sin hospital de procedencia", "con hospital de procedencia"),
                     index=series.index, dtype=object)


def age_band(age: np.ndarray) -> np.ndarray:
    out = pd.cut(pd.Series(age), bins=[0, 5, 10, 15, 20, 30, 45, np.inf], right=False, labels=AGE_BANDS)
    return np.where(pd.isna(out), "unknown", out.astype(object)).astype(object)


def los_bin(days: np.ndarray) -> np.ndarray:
    out = pd.cut(pd.Series(days), bins=[-0.5, 0.5, 1.5, 2.5, 4.5, 7.5, 14.5, 30.5, 90.5, np.inf], labels=LOS_BINS)
    return np.where(pd.isna(out), "no informado", out.astype(object)).astype(object)


def multiplicity_bin(n: pd.Series) -> pd.Series:
    return pd.cut(n, bins=[0, 1, 2, 3, 5, np.inf], labels=MULTIPLICITY_BINS).astype(str)


# ---------------------------------------------------------------------------
# Estadística de distribuciones discretas (grupo de comparación de todos los episodios)
# ---------------------------------------------------------------------------
def dist_quantile(values: np.ndarray, counts: np.ndarray, q: float) -> float:
    """Cuantil por interpolación lineal (misma definición que numpy/pandas) sobre una distribución de frecuencias."""
    n = int(counts.sum())
    if n == 0:
        return float("nan")
    cum = np.cumsum(counts)
    h = (n - 1) * q
    lo, hi = int(np.floor(h)), int(np.ceil(h))
    v_lo = float(values[np.searchsorted(cum, lo + 1, side="left")])
    v_hi = float(values[np.searchsorted(cum, hi + 1, side="left")])
    return v_lo + (h - lo) * (v_hi - v_lo)


def dist_stats(values: np.ndarray, counts: np.ndarray) -> dict:
    """Media, DE (ddof=1), mediana, p25, p75, p90, máximo, días totales y n con valor 0 de una distribución discreta."""
    order = np.argsort(values)
    v = np.asarray(values, dtype=float)[order]
    c = np.asarray(counts, dtype=float)[order]
    n = float(c.sum())
    if n == 0:
        return dict(n=0, mean=np.nan, sd=np.nan, median=np.nan, q25=np.nan, q75=np.nan, p90=np.nan,
                    max=np.nan, total_days=0.0, n_zero=0)
    mean = float((v * c).sum() / n)
    var = float(((c * (v - mean) ** 2).sum()) / (n - 1)) if n > 1 else np.nan
    return dict(n=int(n), mean=mean, sd=float(np.sqrt(var)) if var == var else np.nan,
                median=dist_quantile(v, c, 0.5), q25=dist_quantile(v, c, 0.25), q75=dist_quantile(v, c, 0.75),
                p90=dist_quantile(v, c, 0.90), max=float(v[-1]), total_days=float((v * c).sum()),
                n_zero=int(c[v == 0].sum()))


def series_stats(s: pd.Series) -> dict:
    """Mismo resumen calculado directamente sobre los valores (se compara con `dist_stats` en los controles)."""
    if not len(s):
        return dict(n=0, mean=np.nan, sd=np.nan, median=np.nan, q25=np.nan, q75=np.nan, p90=np.nan,
                    max=np.nan, total_days=0.0, n_zero=0)
    return dict(n=int(len(s)), mean=float(s.mean()), sd=float(s.std(ddof=1)) if len(s) > 1 else np.nan,
                median=float(s.median()), q25=float(s.quantile(.25)), q75=float(s.quantile(.75)),
                p90=float(s.quantile(.90)), max=float(s.max()), total_days=float(s.sum()),
                n_zero=int((s == 0).sum()))


def wilson_frame(k: np.ndarray, n: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p, lo, hi = [], [], []
    for ki, ni in zip(np.asarray(k), np.asarray(n)):
        a, b, c = C.wilson(int(ki), int(ni))
        p.append(a)
        lo.append(b)
        hi.append(c)
    return np.array(p), np.array(lo), np.array(hi)


# ---------------------------------------------------------------------------
# Panel fijo de 65 hospitales (reutiliza la salida del módulo 01; nunca se recalcula aquí)
# ---------------------------------------------------------------------------
def fixed_panel_codes() -> set[str]:
    path = CFG.TIDY / "grd_fixed_panel_hospitals.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Falta {path}: ejecute antes lancet_americas/pipeline/01_grd_core.py")
    df = pd.read_csv(path, dtype={"COD_HOSPITAL": str})
    codes = set(df.loc[df["in_fixed_panel"].astype(bool), "COD_HOSPITAL"].astype(str).str.strip())
    if not codes:
        raise ValueError(f"{path} no contiene hospitales con in_fixed_panel = True")
    return codes


def comuna_lookup() -> tuple[dict[str, tuple[int, int]], dict[str, str], pd.DataFrame]:
    """Crosswalk explícito comuna → CUT (nunca fuzzy matching); alias documentados en comuna_crosswalk.csv."""
    path = CFG.TIDY / "comuna_crosswalk.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Falta {path}: ejecute antes lancet_americas/pipeline/03_denominators.py")
    xw = pd.read_csv(path, dtype=str)
    lookup: dict[str, tuple[int, int]] = {}
    method: dict[str, str] = {}
    for r in xw.itertuples():
        lookup[r.comuna_norm] = (int(r.cut_comuna), int(r.cut_region))
        method[r.comuna_norm] = "exact"
        if isinstance(r.aliases_norm, str) and r.aliases_norm.strip():
            for alias in r.aliases_norm.split("|"):
                alias = alias.strip()
                if alias and alias not in lookup:
                    lookup[alias] = (int(r.cut_comuna), int(r.cut_region))
                    method[alias] = "alias"
    return lookup, method, xw


# ---------------------------------------------------------------------------
# Pasada 1: lectura anual completa (episodios F84 en detalle + agregados de todos los episodios)
# ---------------------------------------------------------------------------
def derive_common(chunk: pd.DataFrame, fixed: set[str]) -> dict:
    """Variables derivadas comunes a todos los episodios de un trozo (vectorizadas)."""
    n = len(chunk)
    hosp = chunk["COD_HOSPITAL"].fillna("").astype(object).str.strip()
    raw_act = chunk["TIPO_ACTIVIDAD"].fillna("").astype(object).str.strip()
    act_map = {v: classify_activity(v) for v in raw_act.unique()}
    act = raw_act.map(act_map).to_numpy(dtype=object)
    raw_sex = chunk["SEXO"].fillna("").astype(object).str.strip().str.upper()
    sex = raw_sex.map({"HOMBRE": "HOMBRE", "MUJER": "MUJER", "1": "HOMBRE", "2": "MUJER"}).fillna("unknown").to_numpy(dtype=object)
    birth = parse_dates(chunk["FECHA_NACIMIENTO"])
    adm = parse_dates(chunk["FECHA_INGRESO"])
    dis = parse_dates(chunk["FECHAALTA"])
    age = np.floor((adm - birth).dt.days.to_numpy(dtype=float) / 365.25)
    age = np.where((age < 0) | (age > 110), np.nan, age)
    ag = pd.cut(age, bins=list(range(0, 85, 5)) + [np.inf], right=False, labels=C.AGE_GROUPS).astype(object)
    ag = np.where(pd.isna(ag), "unknown", ag).astype(object)
    month = adm.dt.month.fillna(0).astype(int).to_numpy()
    valid_los = adm.notna().to_numpy() & dis.notna().to_numpy() & ((dis - adm).dt.days.to_numpy(dtype=float) >= 0)
    los = np.where(valid_los, (dis - adm).dt.days.to_numpy(dtype=float), np.nan)
    age_single = np.where(np.isnan(age), -1, np.minimum(age, 100)).astype(int)
    return dict(n=n, hosp=hosp.to_numpy(dtype=object), in_fixed65=hosp.isin(fixed).to_numpy(dtype=bool),
                activity=act, activity_raw=raw_act, sex=sex, birth=birth, adm=adm, dis=dis,
                age=age, age_group=ag, age_band=age_band(age), age_single=age_single,
                month=month, valid_los=valid_los, los=los, los_bin=los_bin(los))


def feature_series(chunk: pd.DataFrame, der: dict) -> dict[str, pd.Series]:
    """Variables categóricas del episodio: crudas del productor y agrupaciones documentadas."""
    idx = chunk.index
    f: dict[str, pd.Series] = {}
    for col in FEATURE_RAW:
        f[col] = clean_text(chunk[col]) if col in chunk.columns else pd.Series("no informado", index=idx, dtype=object)
    f["PREVISION_grouped"] = chunk["PREVISION"].map(group_prevision) if "PREVISION" in chunk.columns else pd.Series("No identificada", index=idx, dtype=object)
    f["NACIONALIDAD_grouped"] = chunk["NACIONALIDAD"].map(group_nationality) if "NACIONALIDAD" in chunk.columns else pd.Series("Desconocida", index=idx, dtype=object)
    f["ETNIA_grouped"] = chunk["ETNIA"].map(group_ethnicity) if "ETNIA" in chunk.columns else pd.Series("Desconocido", index=idx, dtype=object)
    f["USOSPABELLON_grouped"] = group_usos_pabellon(chunk["USOSPABELLON"]) if "USOSPABELLON" in chunk.columns else pd.Series("no informado", index=idx, dtype=object)
    f["HOSPPROCEDENCIA_reported"] = group_transfer_origin(chunk["HOSPPROCEDENCIA"]) if "HOSPPROCEDENCIA" in chunk.columns else pd.Series("sin hospital de procedencia", index=idx, dtype=object)
    f["sex"] = pd.Series(der["sex"], index=idx, dtype=object)
    f["age_band"] = pd.Series(der["age_band"], index=idx, dtype=object)
    f["age_group_who"] = pd.Series(der["age_group"], index=idx, dtype=object)
    f["los_bin"] = pd.Series(der["los_bin"], index=idx, dtype=object)
    return f


FEATURE_VARIABLES = (FEATURE_RAW + ["PREVISION_grouped", "NACIONALIDAD_grouped", "ETNIA_grouped",
                                    "USOSPABELLON_grouped", "HOSPPROCEDENCIA_reported",
                                    "sex", "age_band", "age_group_who", "los_bin"])


def read_year(year: int, chunksize: int, max_chunks: int | None, do_hash: bool, fixed: set[str]) -> dict:
    path = CFG.PATHS["grd"] / f"GRD_PUBLICO_{year}.csv"
    if not path.is_file():
        raise FileNotFoundError(path)
    header = pd.read_csv(path, sep="|", nrows=0).columns.tolist()
    id_cols = [c for c in ID_CANDIDATES if c in header]
    if len(id_cols) != 1:
        raise ValueError(f"{path.name}: se esperaba exactamente una columna identificadora, hay {id_cols}")
    id_col = id_cols[0]
    usecols = [id_col] + EXTRA_RAW + FEATURE_RAW + DIAGS
    present = [c for c in usecols if c in header]
    missing = sorted(set(usecols) - set(present))

    t0 = time.perf_counter()
    f84_parts: list[pd.DataFrame] = []
    f84_diag_parts: list[np.ndarray] = []
    los_parts: list[pd.DataFrame] = []          # (fix, activity, age_group, los) → n   [todos los episodios]
    losbad_parts: list[pd.DataFrame] = []       # (fix, activity, age_group) → n con fechas inválidas
    month_parts: list[pd.DataFrame] = []        # (fix, activity, month) → n
    feat_parts: list[pd.DataFrame] = []         # (fix, variable, value) → n
    age_parts: list[pd.DataFrame] = []          # (fix, sex, age_single) → n
    terr_parts: list[pd.DataFrame] = []         # (fix, comuna_norm) → n
    n_rows = 0
    dates_unparsed = {"birth": 0, "admission": 0, "discharge": 0}
    n_negative_los = 0

    for k, chunk in enumerate(C.iter_grd(path, present, chunksize=chunksize)):
        n = len(chunk)
        n_rows += n
        der = derive_common(chunk, fixed)
        dates_unparsed["birth"] += int(der["birth"].isna().sum())
        dates_unparsed["admission"] += int(der["adm"].isna().sum())
        dates_unparsed["discharge"] += int(der["dis"].isna().sum())
        n_negative_los += int((der["adm"].notna() & der["dis"].notna() & ((der["dis"] - der["adm"]).dt.days < 0)).sum())
        feats = feature_series(chunk, der)
        comuna = chunk["COMUNA"].fillna("").astype(object).str.strip()
        cmap = {v: normalize_name(v) for v in comuna.unique()}
        comuna_norm = comuna.map(cmap).to_numpy(dtype=object)

        base = pd.DataFrame({"fix": der["in_fixed65"], "activity": der["activity"], "age_group": der["age_group"],
                            "los": der["los"], "valid_los": der["valid_los"], "month": der["month"],
                             "sex": der["sex"], "age_single": der["age_single"], "comuna_norm": comuna_norm})
        ok = base.loc[base.valid_los]
        if len(ok):
            los_parts.append(ok.groupby(["fix", "activity", "age_group", "los"], observed=True).size().rename("n").reset_index())
        bad = base.loc[~base.valid_los]
        if len(bad):
            losbad_parts.append(bad.groupby(["fix", "activity", "age_group"], observed=True).size().rename("n").reset_index())
        month_parts.append(base.groupby(["fix", "activity", "month"], observed=True).size().rename("n").reset_index())
        age_parts.append(base.groupby(["fix", "sex", "age_single"], observed=True).size().rename("n").reset_index())
        terr_parts.append(base.groupby(["fix", "comuna_norm"], observed=True).size().rename("n").reset_index())
        for var in FEATURE_VARIABLES:
            g = (pd.DataFrame({"fix": der["in_fixed65"], "value": feats[var].to_numpy(dtype=object)})
                 .groupby(["fix", "value"], observed=True).size().rename("n").reset_index())
            g.insert(1, "variable", var)
            feat_parts.append(g)

        # --- episodios candidatos (prefijo F84) → pertenencia exacta por variante -----------------
        diag = np.empty((n, len(DIAGS)), dtype=object)
        for j, col in enumerate(DIAGS):
            diag[:, j] = normalise_codes(chunk[col])
        cand = np.zeros(n, dtype=bool)
        for j in range(len(DIAGS)):
            cand |= np.char.startswith(diag[:, j].astype(str), "F84")
        if cand.any():
            idx = np.flatnonzero(cand)
            sub = diag[idx]
            keep_flags = {}
            member = np.zeros(len(idx), dtype=bool)
            for v, codes in VARIANT_CODES.items():
                p = np.isin(sub[:, 0], list(codes))
                s = np.isin(sub[:, 1:], list(codes)).any(axis=1)
                keep_flags[f"{v}_principal"] = p
                keep_flags[f"{v}_secondary"] = s
                member |= p | s
            ids = chunk[id_col].fillna("").astype(object).str.strip()
            weight = pd.to_numeric(chunk["IR_29301_PESO"].fillna("").astype(object).str.replace(",", ".", regex=False),
                                   errors="coerce") if "IR_29301_PESO" in chunk.columns else pd.Series(np.nan, index=chunk.index)
            rec = {"year": year, "hospital": der["hosp"][idx], "in_fixed65": der["in_fixed65"][idx],
                   "id": ids.to_numpy(dtype=object)[idx], "id_valid": valid_id_mask(ids)[idx],
                   "activity": der["activity"][idx], "sex": der["sex"][idx], "age": der["age"][idx],
                   "age_group": der["age_group"][idx], "age_band": der["age_band"][idx],
                   "age_single": der["age_single"][idx], "month": der["month"][idx],
                   "valid_los": der["valid_los"][idx], "los": der["los"][idx], "los_bin": der["los_bin"][idx],
                   "admission": der["adm"].to_numpy()[idx], "discharge": der["dis"].to_numpy()[idx],
                   "comuna_norm": comuna_norm[idx], "weight": weight.to_numpy(dtype=float)[idx],
                   "ir_grd_code": clean_text(chunk["IR_29301_COD_GRD"]).to_numpy(dtype=object)[idx]
                   if "IR_29301_COD_GRD" in chunk.columns else np.full(len(idx), "no informado", dtype=object)}
            for var in FEATURE_VARIABLES:
                rec[f"feat_{var}"] = feats[var].to_numpy(dtype=object)[idx]
            rec.update({key: val for key, val in keep_flags.items()})
            f84 = pd.DataFrame(rec).loc[member].reset_index(drop=True)
            f84_parts.append(f84)
            f84_diag_parts.append(sub[member])
        if max_chunks and k + 1 >= max_chunks:
            print(f"  [prueba] lectura detenida tras {max_chunks} trozo(s)", flush=True)
            break

    def collapse(parts: list[pd.DataFrame], keys: list[str]) -> pd.DataFrame:
        if not parts:
            return pd.DataFrame(columns=keys + ["n"])
        return pd.concat(parts, ignore_index=True).groupby(keys, observed=True)["n"].sum().reset_index()

    f84 = pd.concat(f84_parts, ignore_index=True) if f84_parts else pd.DataFrame()
    diag = np.vstack(f84_diag_parts) if f84_diag_parts else np.empty((0, len(DIAGS)), dtype=object)
    elapsed = time.perf_counter() - t0
    stat = path.stat()
    source = {"path": str(path), "bytes": stat.st_size,
              "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
              "sha256": C.sha256_file(path) if do_hash else None, "identifier_column": id_col,
              "columns_read": present, "columns_absent": missing}
    print(f"GRD {year}: {n_rows:,} filas; {len(f84):,} episodios con F84 ({PRIMARY_VARIANT} u otra variante); "
          f"{elapsed:,.1f} s", flush=True)
    return dict(year=year, id_col=id_col, n_rows=n_rows, f84=f84, diag=diag,
                los=collapse(los_parts, ["fix", "activity", "age_group", "los"]),
                los_invalid=collapse(losbad_parts, ["fix", "activity", "age_group"]),
                month=collapse(month_parts, ["fix", "activity", "month"]),
                features=collapse(feat_parts, ["fix", "variable", "value"]),
                age_single=collapse(age_parts, ["fix", "sex", "age_single"]),
                territory=collapse(terr_parts, ["fix", "comuna_norm"]),
                dates_unparsed=dates_unparsed, n_negative_los=n_negative_los, seconds=elapsed, source=source)


# ---------------------------------------------------------------------------
# Pasada 2: episodios de todas las causas de las personas con al menos un episodio F84 (reingresos)
# ---------------------------------------------------------------------------
def read_year_linkage(year: int, ids_wanted: set[str], chunksize: int, max_chunks: int | None, fixed: set[str]) -> pd.DataFrame:
    path = CFG.PATHS["grd"] / f"GRD_PUBLICO_{year}.csv"
    header = pd.read_csv(path, sep="|", nrows=0).columns.tolist()
    id_col = [c for c in ID_CANDIDATES if c in header][0]
    usecols = [id_col, "COD_HOSPITAL", "FECHA_INGRESO", "FECHAALTA"] + DIAGS
    parts = []
    for k, chunk in enumerate(C.iter_grd(path, usecols, chunksize=chunksize)):
        ids = chunk[id_col].fillna("").astype(object).str.strip()
        hit = ids.isin(ids_wanted).to_numpy(dtype=bool)
        if hit.any():
            idx = np.flatnonzero(hit)
            n = len(idx)
            sub = np.empty((n, len(DIAGS)), dtype=object)
            for j, col in enumerate(DIAGS):
                sub[:, j] = normalise_codes(chunk[col].iloc[idx])
            adm = parse_dates(chunk["FECHA_INGRESO"].iloc[idx])
            dis = parse_dates(chunk["FECHAALTA"].iloc[idx])
            hosp = chunk["COD_HOSPITAL"].fillna("").astype(object).str.strip().iloc[idx]
            rec = {"year": year, "id": ids.to_numpy(dtype=object)[idx],
                   "in_fixed65": hosp.isin(fixed).to_numpy(dtype=bool),
                   "admission": adm.to_numpy(), "discharge": dis.to_numpy()}
            for v, codes in VARIANT_CODES.items():
                p = np.isin(sub[:, 0], list(codes))
                s = np.isin(sub[:, 1:], list(codes)).any(axis=1)
                rec[f"{v}_principal"] = p
                rec[f"{v}_secondary"] = s
            parts.append(pd.DataFrame(rec))
        if max_chunks and k + 1 >= max_chunks:
            break
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ---------------------------------------------------------------------------
# Expansión variante × posición × panel
# ---------------------------------------------------------------------------
def position_masks(df: pd.DataFrame, variant: str) -> dict[str, np.ndarray]:
    p = df[f"{variant}_principal"].to_numpy(dtype=bool)
    s = df[f"{variant}_secondary"].to_numpy(dtype=bool)
    return {"any": p | s, "principal": p, "secondary_only": s & ~p}


def expand(f84: pd.DataFrame, keep: list[str]) -> pd.DataFrame:
    """Una fila por (episodio, variante, posición, panel). El índice original se conserva en `ep`."""
    if not len(f84):
        return pd.DataFrame(columns=keep + ["ep", "variant", "position", "panel"])
    base = f84[keep].copy()
    base["ep"] = np.arange(len(f84))
    parts = []
    for variant in VARIANTS:
        masks = position_masks(f84, variant)
        for position in POSITIONS:
            m = masks[position]
            if not m.any():
                continue
            sub = base.loc[m].copy()
            sub["variant"] = variant
            sub["position"] = position
            parts.append(sub)
    e = pd.concat(parts, ignore_index=True)
    obs = e.copy()
    obs["panel"] = "observed"
    fx = e.loc[e["in_fixed65"].to_numpy(dtype=bool)].copy()
    fx["panel"] = "fixed65"
    return pd.concat([obs, fx], ignore_index=True)


DICTIONARY: list[dict] = []
ROUND_4 = ("pct", "rate", "share", "seasonal", "index", "days", "mean", "sd", "median", "q25", "q75", "p90")


def stamp(df: pd.DataFrame, table: str, unit_short: str, denominator_short: str,
          unit: str, denominator: str) -> pd.DataFrame:
    """Añade las columnas de unidad de cada fila y registra la definición completa en el diccionario derivado.

    Las frases largas (unidad, denominador, cobertura, era de definición y archivo fuente) se escriben una vez por
    tabla en `outputs/tidy/grd_episode_detail_dictionary.csv`; repetirlas en cada fila multiplicaría por diez el
    tamaño de las tablas grandes (co-diagnósticos, territorio) sin añadir información.
    """
    df = df.copy()
    for col in df.columns:
        if df[col].dtype.kind == "f" and any(tok in col for tok in ROUND_4):
            df[col] = df[col].round(4)
    df["unit"] = unit_short
    df["denominator"] = denominator_short
    df["script"] = SCRIPT
    DICTIONARY.append(dict(table=table, rows=int(len(df)), unit=unit_short, denominator=denominator_short,
                           unit_definition=unit, denominator_definition=denominator, coverage=COVERAGE,
                           definition_era=DEFINITION_ERA, source_files=SOURCE_FILES, script=SCRIPT,
                           columns="|".join(map(str, df.columns))))
    return df


# ---------------------------------------------------------------------------
# (a) grd_monthly
# ---------------------------------------------------------------------------
def build_monthly(exp: pd.DataFrame, years_data: list[dict]) -> pd.DataFrame:
    num = (exp.groupby(["year", "variant", "position", "panel", "month"], observed=True).size()
           .rename("n_episodes_f84").reset_index())
    den_parts = []
    for d in years_data:
        m = d["month"]
        for panel in PANELS:
            sel = m if panel == "observed" else m.loc[m.fix]
            g = sel.groupby("month", observed=True)["n"].sum().reset_index()
            g["year"] = d["year"]
            g["panel"] = panel
            den_parts.append(g.rename(columns={"n": "n_episodes_total"}))
    den = pd.concat(den_parts, ignore_index=True)
    grid = pd.MultiIndex.from_product(
        [sorted(exp.year.unique()), VARIANTS, POSITIONS, PANELS, list(range(0, 13))],
        names=["year", "variant", "position", "panel", "month"]).to_frame(index=False)
    out = grid.merge(num, how="left", on=list(grid.columns)).merge(den, how="left", on=["year", "panel", "month"])
    out["n_episodes_f84"] = out["n_episodes_f84"].fillna(0).astype(int)
    out["n_episodes_total"] = out["n_episodes_total"].fillna(0).astype(int)
    lo, hi = C.poisson_limits(out["n_episodes_f84"].to_numpy())
    den_v = out["n_episodes_total"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out["rate_per_100k_episodes"] = np.where(den_v > 0, 1e5 * out["n_episodes_f84"] / den_v, np.nan)
        out["rate_lo"] = np.where(den_v > 0, 1e5 * lo / den_v, np.nan)
        out["rate_hi"] = np.where(den_v > 0, 1e5 * hi / den_v, np.nan)
    # índice estacional dentro del año (media de los 12 meses del calendario = 1); mes 0 = fecha no analizable
    real = out.month.between(1, 12)
    mean_f84 = out.loc[real].groupby(["year", "variant", "position", "panel"])["n_episodes_f84"].transform("mean")
    mean_tot = out.loc[real].groupby(["year", "panel"])["n_episodes_total"].transform("mean")
    mean_rate = out.loc[real].groupby(["year", "variant", "position", "panel"])["rate_per_100k_episodes"].transform("mean")
    out["seasonal_index_f84"] = np.nan
    out["seasonal_index_total"] = np.nan
    out["seasonal_index_rate"] = np.nan
    out.loc[real, "seasonal_index_f84"] = np.where(mean_f84 > 0, out.loc[real, "n_episodes_f84"] / mean_f84, np.nan)
    out.loc[real, "seasonal_index_total"] = np.where(mean_tot > 0, out.loc[real, "n_episodes_total"] / mean_tot, np.nan)
    out.loc[real, "seasonal_index_rate"] = np.where(mean_rate > 0, out.loc[real, "rate_per_100k_episodes"] / mean_rate, np.nan)
    out["month_label"] = np.where(out.month == 0, "unknown (unparsable admission date)", out.month.astype(str))
    out["activity"] = "all"
    return stamp(out.sort_values(["year", "variant", "position", "panel", "month"]).reset_index(drop=True),
                 "grd_monthly", "episodios GRD (mes de ingreso)", "n_episodes_total",
                 "Episodios GRD con F84 documentado por mes de ingreso (un episodio = una fila del GRD publicado)",
                 "Episodios GRD del mismo mes, año y panel (todas las actividades)")


# ---------------------------------------------------------------------------
# (b, c) grd_length_of_stay y grd_los_age
# ---------------------------------------------------------------------------
def _los_row(stats: dict, **keys) -> dict:
    row = dict(keys)
    row.update({"n_valid_dates": stats["n"], "mean_days": stats["mean"], "sd_days": stats["sd"],
                "median_days": stats["median"], "q25_days": stats["q25"], "q75_days": stats["q75"],
                "p90_days": stats["p90"], "max_days": stats["max"], "total_days": stats["total_days"],
                "n_los_zero": stats["n_zero"]})
    return row


def build_los(exp: pd.DataFrame, years_data: list[dict], by_age: bool) -> pd.DataFrame:
    rows = []
    group_cols = ["year", "variant", "position", "panel", "activity"] + (["age_group"] if by_age else [])
    # --- series F84 -----------------------------------------------------------------------------
    for activity in ACTIVITIES:
        sel = exp if activity == "all" else exp.loc[exp.activity == activity]
        if not len(sel):
            continue
        keys = ["year", "variant", "position", "panel"] + (["age_group"] if by_age else [])
        for key, g in sel.groupby(keys, observed=True):
            key = key if isinstance(key, tuple) else (key,)
            d = dict(zip(keys, key))
            d["activity"] = activity
            valid = g.loc[g.valid_los]
            stats = series_stats(valid["los"].astype(float))
            rows.append(_los_row(stats, **d, n_episodes_cell=int(len(g)),
                                 n_invalid_dates=int((~g.valid_los).sum())))
    # --- grupo de comparación: todos los episodios GRD --------------------------------------------
    for d in years_data:
        los = d["los"]
        bad = d["los_invalid"]
        for panel in PANELS:
            sel = los if panel == "observed" else los.loc[los.fix]
            selbad = bad if panel == "observed" else bad.loc[bad.fix]
            for activity in ACTIVITIES:
                s = sel if activity == "all" else sel.loc[sel.activity == activity]
                b = selbad if activity == "all" else selbad.loc[selbad.activity == activity]
                if by_age:
                    ages = sorted(set(s.age_group.unique()) | set(b.age_group.unique()))
                    for ag in ages:
                        sa, ba = s.loc[s.age_group == ag], b.loc[b.age_group == ag]
                        if not len(sa) and not len(ba):
                            continue
                        agg = sa.groupby("los", observed=True)["n"].sum()
                        stats = dist_stats(agg.index.to_numpy(dtype=float), agg.to_numpy()) if len(agg) else dist_stats(np.array([]), np.array([]))
                        rows.append(_los_row(stats, year=d["year"], variant=COMPARISON, position="all", panel=panel,
                                             activity=activity, age_group=ag,
                                             n_episodes_cell=int(stats["n"] + ba["n"].sum()),
                                             n_invalid_dates=int(ba["n"].sum())))
                else:
                    agg = s.groupby("los", observed=True)["n"].sum()
                    stats = dist_stats(agg.index.to_numpy(dtype=float), agg.to_numpy()) if len(agg) else dist_stats(np.array([]), np.array([]))
                    rows.append(_los_row(stats, year=d["year"], variant=COMPARISON, position="all", panel=panel,
                                         activity=activity, n_episodes_cell=int(stats["n"] + b["n"].sum()),
                                         n_invalid_dates=int(b["n"].sum())))
    out = pd.DataFrame(rows)
    out = out[[c for c in group_cols if c in out.columns] + [c for c in out.columns if c not in group_cols]]
    unit = "Días de estadía por episodio GRD ((FECHAALTA − FECHA_INGRESO), solo fechas analizables y alta ≥ ingreso)"
    den = "Episodios de la misma celda con fechas válidas (n_valid_dates); n_invalid_dates queda fuera y nunca se imputa"
    return stamp(out.sort_values(group_cols).reset_index(drop=True),
                 "grd_los_age" if by_age else "grd_length_of_stay", "días de estadía por episodio",
                 "n_valid_dates", unit, den)


# ---------------------------------------------------------------------------
# (d) grd_episode_features
# ---------------------------------------------------------------------------
def build_features(exp: pd.DataFrame, years_data: list[dict], specialty_top: list[str]) -> pd.DataFrame:
    def collapse_specialty(s: pd.Series) -> pd.Series:
        return s.where(s.isin(specialty_top), "otra especialidad (fuera de las 20 principales)")

    rows = []
    for var in FEATURE_VARIABLES:
        col = f"feat_{var}"
        values = exp[col]
        if var == "ESPECIALIDAD_MEDICA":
            values = collapse_specialty(values)
        g = (pd.DataFrame({"year": exp.year, "variant": exp.variant, "position": exp.position, "panel": exp.panel,
                           "value": values.to_numpy(dtype=object)})
             .groupby(["year", "variant", "position", "panel", "value"], observed=True).size()
             .rename("n_episodes").reset_index())
        g.insert(4, "variable", var)
        rows.append(g)
    f84 = pd.concat(rows, ignore_index=True)
    comp_parts = []
    for d in years_data:
        feats = d["features"]
        for panel in PANELS:
            sel = feats if panel == "observed" else feats.loc[feats.fix]
            g = sel.groupby(["variable", "value"], observed=True)["n"].sum().rename("n_episodes").reset_index()
            g["year"] = d["year"]
            g["variant"] = COMPARISON
            g["position"] = "all"
            g["panel"] = panel
            comp_parts.append(g)
    comp = pd.concat(comp_parts, ignore_index=True)
    sp = comp.variable == "ESPECIALIDAD_MEDICA"
    comp.loc[sp, "value"] = collapse_specialty(comp.loc[sp, "value"])
    comp = comp.groupby(["year", "variant", "position", "panel", "variable", "value"], observed=True)["n_episodes"].sum().reset_index()
    out = pd.concat([f84, comp], ignore_index=True)
    out["n_cell_total"] = out.groupby(["year", "variant", "position", "panel", "variable"], observed=True)["n_episodes"].transform("sum")
    out["pct_within_cell"] = 100 * out["n_episodes"] / out["n_cell_total"].replace(0, np.nan)
    out = out.sort_values(["year", "variant", "position", "panel", "variable", "n_episodes"],
                          ascending=[True, True, True, True, True, False]).reset_index(drop=True)
    unit = ("Episodios GRD por categoría de la variable del episodio; los valores vacíos aparecen como «no informado» "
            "(nunca como cero). ESPECIALIDAD_MEDICA se colapsa a las 20 especialidades más frecuentes entre los "
            "episodios F84 (con_rett, cualquier posición, panel observado, 2019–2024) más «otra especialidad»")
    den = "Episodios de la misma celda año × variante × posición × panel (n_cell_total)"
    return stamp(out, "grd_episode_features", "episodios GRD", "n_cell_total", unit, den)


# ---------------------------------------------------------------------------
# (e) grd_grd_weight
# ---------------------------------------------------------------------------
def build_weight(exp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["year", "variant", "position", "panel"]
    for key, g in exp.groupby(keys, observed=True):
        d = dict(zip(keys, key))
        w = g["weight"].astype(float).dropna()
        rows.append(dict(**d, row_type="weight_summary", ir_grd_code="", ir_grd_rank=np.nan,
                         n=int(len(w)), n_episodes_cell=int(len(g)), n_without_weight=int(g["weight"].isna().sum()),
                         mean=float(w.mean()) if len(w) else np.nan,
                         sd=float(w.std(ddof=1)) if len(w) > 1 else np.nan,
                         median=float(w.median()) if len(w) else np.nan,
                         q25=float(w.quantile(.25)) if len(w) else np.nan,
                         q75=float(w.quantile(.75)) if len(w) else np.nan,
                         pct_of_cell=np.nan))
    # 15 grupos IR_29301_COD_GRD más frecuentes por variante/posición/panel (ranking sobre 2019–2024)
    for (variant, position, panel), g in exp.groupby(["variant", "position", "panel"], observed=True):
        totals = g.groupby("ir_grd_code", observed=True).size().sort_values(ascending=False)
        totals = totals.drop(index="no informado", errors="ignore")
        top = list(totals.head(TOP_GRD_GROUPS).index)
        rank = {code: i + 1 for i, code in enumerate(top)}
        for year, gy in g.groupby("year", observed=True):
            n_cell = int(len(gy))
            counts = gy.groupby("ir_grd_code", observed=True).size()
            for code in top:
                n = int(counts.get(code, 0))
                w = gy.loc[gy.ir_grd_code == code, "weight"].astype(float).dropna()
                rows.append(dict(year=year, variant=variant, position=position, panel=panel,
                                 row_type="grd_group", ir_grd_code=code, ir_grd_rank=rank[code],
                                 n=n, n_episodes_cell=n_cell, n_without_weight=int(n - len(w)),
                                 mean=float(w.mean()) if len(w) else np.nan,
                                 sd=float(w.std(ddof=1)) if len(w) > 1 else np.nan,
                                 median=float(w.median()) if len(w) else np.nan,
                                 q25=float(w.quantile(.25)) if len(w) else np.nan,
                                 q75=float(w.quantile(.75)) if len(w) else np.nan,
                                 pct_of_cell=100 * n / n_cell if n_cell else np.nan))
            n_other = int(n_cell - sum(int(counts.get(c, 0)) for c in top))
            rows.append(dict(year=year, variant=variant, position=position, panel=panel,
                             row_type="grd_group_other", ir_grd_code="otros grupos GRD y no informado",
                             ir_grd_rank=np.nan, n=n_other, n_episodes_cell=n_cell, n_without_weight=np.nan,
                             mean=np.nan, sd=np.nan, median=np.nan, q25=np.nan, q75=np.nan,
                             pct_of_cell=100 * n_other / n_cell if n_cell else np.nan))
    out = pd.DataFrame(rows).sort_values(["variant", "position", "panel", "year", "row_type", "ir_grd_rank"]).reset_index(drop=True)
    unit = ("Peso relativo IR-29301 del episodio (IR_29301_PESO, coma decimal en el archivo fuente) y grupos "
            "IR_29301_COD_GRD; row_type = weight_summary (resumen del peso) / grd_group (uno de los 15 grupos más "
            "frecuentes de la celda variante × posición × panel, ordenados por el total 2019–2024) / grd_group_other")
    den = "Episodios de la celda año × variante × posición × panel (n_episodes_cell); n = episodios con peso válido"
    return stamp(out, "grd_grd_weight", "peso relativo IR-29301 / episodios por grupo GRD", "n_episodes_cell", unit, den)


# ---------------------------------------------------------------------------
# (f, g) grd_codiagnoses y grd_codiagnosis_chapters
# ---------------------------------------------------------------------------
def codiagnosis_long(diag: np.ndarray) -> pd.DataFrame:
    """Filas (ep, code3, code_position) con un episodio contado una vez por categoría y posición; excluye F84."""
    rows_ep, rows_code, rows_pos = [], [], []
    for i in range(diag.shape[0]):
        principal, secondary = set(), set()
        for j in range(diag.shape[1]):
            code = diag[i, j]
            if not code or code.startswith("F84"):
                continue
            (principal if j == 0 else secondary).add(code[:3])
        for c in principal:
            rows_ep.append(i)
            rows_code.append(c)
            rows_pos.append("principal")
        for c in secondary:
            rows_ep.append(i)
            rows_code.append(c)
            rows_pos.append("secondary")
        for c in principal | secondary:
            rows_ep.append(i)
            rows_code.append(c)
            rows_pos.append("any")
    return pd.DataFrame({"ep": np.asarray(rows_ep, dtype=np.int64), "code3": rows_code, "code_position": rows_pos})


def build_codiagnoses(exp: pd.DataFrame, long: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keys = exp[["ep", "year", "variant", "position", "panel"]]
    cell = keys.groupby(["year", "variant", "position", "panel"], observed=True).size().rename("n_f84_episodes_cell").reset_index()
    merged = long.merge(keys, how="inner", on="ep")
    codes = (merged.groupby(["year", "variant", "position", "panel", "code_position", "code3"], observed=True)
             .size().rename("n_episodes").reset_index().merge(cell, how="left", on=["year", "variant", "position", "panel"]))
    codes["icd_label_es"] = codes["code3"].map(icd_label)
    codes["pct_of_f84_episodes"] = 100 * codes["n_episodes"] / codes["n_f84_episodes_cell"].replace(0, np.nan)
    codes = codes.sort_values(["year", "variant", "position", "panel", "code_position", "n_episodes"],
                              ascending=[True, True, True, True, True, False]).reset_index(drop=True)
    unit_codes = ("Episodios GRD con F84 documentado que registran, en la posición indicada, al menos un código de la "
                  "categoría CIE-10 de tres caracteres (un episodio cuenta una vez por categoría y posición). Se excluyen "
                  "los propios códigos F84. code_position = principal (DIAGNOSTICO1) / secondary (DIAGNOSTICO2..35) / any; "
                  "las filas position = secondary_only con code_position = principal son el diagnóstico principal cuando "
                  "F84 aparece solo como secundario")
    den_codes = "Episodios F84 de la celda año × variante × posición × panel (n_f84_episodes_cell)"

    # capítulos y bloques: un episodio cuenta una vez por grupo
    long2 = long.copy()
    long2["chapter"] = long2["code3"].map(icd_chapter)
    long2["mental_block"] = long2["code3"].map(mental_block)
    parts = []
    for grouping, col in (("chapter", "chapter"), ("mental_block", "mental_block")):
        sub = long2 if grouping == "chapter" else long2.loc[long2["mental_block"] != "No F"]
        dedup = sub[["ep", "code_position", col]].drop_duplicates()
        m = dedup.merge(keys, how="inner", on="ep")
        g = (m.groupby(["year", "variant", "position", "panel", "code_position", col], observed=True)
             .size().rename("n_episodes").reset_index().rename(columns={col: "group_label"}))
        g.insert(5, "grouping", grouping)
        parts.append(g)
    chapters = pd.concat(parts, ignore_index=True).merge(cell, how="left", on=["year", "variant", "position", "panel"])
    chapters["pct_of_f84_episodes"] = 100 * chapters["n_episodes"] / chapters["n_f84_episodes_cell"].replace(0, np.nan)
    chapters = chapters.sort_values(["year", "variant", "position", "panel", "grouping", "code_position", "n_episodes"],
                                    ascending=[True, True, True, True, True, True, False]).reset_index(drop=True)
    unit_ch = ("Episodios GRD con F84 documentado que registran al menos un código del capítulo CIE-10 "
               "(grouping = chapter, `scripts/report_helpers.icd_chapter`) o del bloque de salud mental "
               "(grouping = mental_block, `mental_block`, excluye «No F»); un episodio cuenta una vez por grupo y posición. "
               "El bloque F84 corresponde a los propios trastornos generalizados del desarrollo y no aparece porque los "
               "códigos F84 se excluyen del numerador de co-diagnósticos")
    return (stamp(codes, "grd_codiagnoses", "episodios GRD con el co-diagnóstico", "n_f84_episodes_cell", unit_codes, den_codes),
            stamp(chapters, "grd_codiagnosis_chapters", "episodios GRD con el co-diagnóstico", "n_f84_episodes_cell", unit_ch, den_codes))


# ---------------------------------------------------------------------------
# (h) grd_readmission
# ---------------------------------------------------------------------------
def build_readmission(link: pd.DataFrame) -> pd.DataFrame:
    """Reingresos dentro de la misma era de identificador, calculados íntegramente sobre los episodios de todas las
    causas de las personas con al menos un episodio F84 (pasada 2). Nunca se enlaza a través del corte 2020/2021."""
    if not len(link):
        return pd.DataFrame()
    link = link.copy()
    link["era"] = link.year.map({y: era for era, years in ERAS.items() for y in years})
    link["valid_dates"] = (link.admission.notna() & link.discharge.notna()
                           & ((link.discharge - link.admission).dt.days >= 0))
    era_end = {era: pd.Timestamp(f"{years[-1]}-12-31") for era, years in ERAS.items()}
    rows = []
    for era, sub in link.loc[link.valid_dates].groupby("era", observed=True):
        sub = sub.sort_values(["id", "admission", "discharge"]).reset_index(drop=True)
        n = len(sub)
        adm_days = sub.admission.values.astype("datetime64[D]").astype("int64")
        dis_days = sub.discharge.values.astype("datetime64[D]").astype("int64")
        end_day = np.datetime64(era_end[era].date(), "D").astype("int64")
        days_to_end = end_day - dis_days
        blocks = list(sub.groupby("id", sort=False).indices.values())
        year = sub.year.to_numpy()
        in_fixed = sub.in_fixed65.to_numpy(dtype=bool)
        for variant in VARIANTS:
            p = sub[f"{variant}_principal"].to_numpy(dtype=bool)
            s = sub[f"{variant}_secondary"].to_numpy(dtype=bool)
            is_f84 = p | s
            posmask = {"any": is_f84, "principal": p, "secondary_only": s & ~p}
            min_gap_any = np.full(n, np.inf)
            min_gap_f84 = np.full(n, np.inf)
            overlapping = np.zeros(n, dtype=bool)
            for blk in blocks:
                if len(blk) < 2:
                    continue
                a, d, f = adm_days[blk], dis_days[blk], is_f84[blk]
                for u in range(len(blk)):
                    later = np.flatnonzero(a > a[u])
                    if not later.size:
                        continue
                    gaps = a[later] - d[u]
                    overlapping[blk[u]] = bool((gaps < 0).any())
                    ok = gaps >= 0
                    if ok.any():
                        min_gap_any[blk[u]] = gaps[ok].min()
                        fo = ok & f[later]
                        if fo.any():
                            min_gap_f84[blk[u]] = gaps[fo].min()
            for panel in PANELS:
                pm = np.ones(n, dtype=bool) if panel == "observed" else in_fixed
                for position in POSITIONS:
                    idx = posmask[position] & pm
                    if not idx.any():
                        continue
                    for y in np.unique(year[idx]):
                        ym = idx & (year == y)
                        for horizon in HORIZONS:
                            elig = ym & (days_to_end >= horizon)
                            rows.append(dict(
                                era=era, year=int(y), variant=variant, position=position, panel=panel,
                                horizon_days=horizon, n_discharges=int(ym.sum()), n_eligible=int(elig.sum()),
                                n_readmitted_any_cause=int((elig & (min_gap_any <= horizon)).sum()),
                                n_readmitted_f84=int((elig & (min_gap_f84 <= horizon)).sum()),
                                n_with_overlapping_next_admission=int((ym & overlapping).sum())))
    out = pd.DataFrame(rows)
    for col, label in (("n_readmitted_any_cause", "any_cause"), ("n_readmitted_f84", "f84")):
        prop, lo, hi = wilson_frame(out[col].to_numpy(), out["n_eligible"].to_numpy())
        out[f"pct_{label}"] = 100 * prop
        out[f"pct_{label}_lo"] = 100 * lo
        out[f"pct_{label}_hi"] = 100 * hi
    unit = ("Egresos GRD con F84 documentado, identificador válido y fechas válidas (n_discharges); elegibles = con el "
            "horizonte completo dentro de la misma era de identificador (n_eligible); reingreso = existe un episodio "
            "posterior del mismo identificador cuyo ingreso ocurre entre 0 y el horizonte de días después del alta índice "
            "(reingreso F84 = ese episodio posterior lleva un código F84 de la variante). Los episodios que se solapan "
            "(ingreso anterior al alta índice, típicamente traslados) se informan aparte y no cuentan como reingreso. "
            "Nunca se enlazan personas a través del corte 2020/2021")
    den = "Egresos elegibles de la celda (n_eligible); proporciones con IC de Wilson al 95 %"
    return stamp(out.sort_values(["era", "year", "variant", "position", "panel", "horizon_days"]).reset_index(drop=True),
                 "grd_readmission", "egresos GRD (índice) y reingresos", "n_eligible", unit, den)


# ---------------------------------------------------------------------------
# (i) grd_multiplicity
# ---------------------------------------------------------------------------
def build_multiplicity(exp: pd.DataFrame) -> pd.DataFrame:
    era_of = {y: era for era, years in ERAS.items() for y in years}
    e = exp.loc[exp.id_valid].copy()
    e["era"] = e.year.map(era_of)
    invalid = exp.loc[~exp.id_valid].copy()
    invalid["era"] = invalid.year.map(era_of)
    no_id = (invalid.groupby(["era", "variant", "position", "panel"], observed=True).size().to_dict()
             if len(invalid) else {})
    rows = []
    for keys, g in e.groupby(["era", "variant", "position", "panel"], observed=True):
        per_id = g.groupby("id", observed=True).size()
        binned = multiplicity_bin(per_id)
        agg = pd.DataFrame({"episodes_per_identifier": binned.to_numpy(), "n": per_id.to_numpy()})
        summary = agg.groupby("episodes_per_identifier", observed=True)["n"].agg(n_persons="size", n_episodes="sum").reset_index()
        total_p, total_e = int(summary.n_persons.sum()), int(summary.n_episodes.sum())
        for b in MULTIPLICITY_BINS:
            r = summary.loc[summary.episodes_per_identifier == b]
            npers = int(r.n_persons.iloc[0]) if len(r) else 0
            neps = int(r.n_episodes.iloc[0]) if len(r) else 0
            rows.append(dict(era=keys[0], variant=keys[1], position=keys[2], panel=keys[3],
                             episodes_per_identifier=b, n_persons=npers, n_episodes=neps,
                             n_persons_total=total_p, n_episodes_total=total_e,
                             pct_persons=100 * npers / total_p if total_p else np.nan,
                             pct_episodes=100 * neps / total_e if total_e else np.nan,
                             n_episodes_without_valid_identifier=no_id.get(keys, 0)))
    unit = ("Identificadores distintos dentro de la era y episodios GRD con F84 documentado por identificador. "
            "Eras: 2019–2020 (CIP_ENCRIPTADO de 6 dígitos) y 2021–2024 (8–9 dígitos; la columna pasa a ID_BENEFICIARIO "
            "en 2024 sin cambiar de formato). Las personas nunca se deduplican entre eras")
    den = "Identificadores válidos de la celda era × variante × posición × panel (n_persons_total)"
    return stamp(pd.DataFrame(rows).sort_values(["era", "variant", "position", "panel", "episodes_per_identifier"]).reset_index(drop=True),
                 "grd_multiplicity", "identificadores y episodios GRD", "n_persons_total", unit, den)


# ---------------------------------------------------------------------------
# (j) grd_territory
# ---------------------------------------------------------------------------
def build_territory(exp: pd.DataFrame, years_data: list[dict], lookup, method, xw) -> pd.DataFrame:
    region_name = dict(zip(xw.cut_region.astype(int), xw.region_name_ine))
    comuna_name = dict(zip(xw.comuna_norm, xw.comuna_name_ine))
    keys = ["year", "variant", "position", "panel", "comuna_norm"]
    g = exp.groupby(keys, observed=True).size().rename("n_episodes").reset_index()
    # personas dentro del año: solo identificadores válidos, nunca deduplicadas entre años ni entre comunas
    persons = (exp.loc[exp.id_valid].groupby(keys, observed=True)["id"].nunique()
               .rename("n_persons_within_year").reset_index())
    g = g.merge(persons, how="left", on=keys)
    g["n_persons_within_year"] = g["n_persons_within_year"].fillna(0).astype(int)
    comp_parts = []
    for d in years_data:
        terr = d["territory"]
        for panel in PANELS:
            sel = terr if panel == "observed" else terr.loc[terr.fix]
            s = sel.groupby("comuna_norm", observed=True)["n"].sum().rename("n_episodes").reset_index()
            s["year"], s["variant"], s["position"], s["panel"] = d["year"], COMPARISON, "all", panel
            s["n_persons_within_year"] = np.nan
            comp_parts.append(s)
    out = pd.concat([g] + comp_parts, ignore_index=True)
    out["cut_comuna"] = out.comuna_norm.map(lambda s: lookup.get(s, (np.nan, np.nan))[0])
    out["cut_region"] = out.comuna_norm.map(lambda s: lookup.get(s, (np.nan, np.nan))[1])
    out["match_method"] = out.comuna_norm.map(lambda s: method.get(s, "unmatched"))
    # El nombre se imprime con su ORTOGRAFÍA OFICIAL: `comuna_crosswalk.csv` conserva el nombre tal como
    # lo publica la fuente que lo enlazó, y esa fuente deja caer la tilde de «Los Ángeles» y «Pitrufquén».
    # `labels.comuna_name` busca por la forma plegada entre las 81 comunas con diacrítico declaradas en la
    # tarea F3.4 y corrige cualquiera de ellas; los nombres sin diacrítico vuelven tal cual. Se aplica SOLO
    # a la columna que se imprime: `comuna_norm`, `cut_comuna` y `cut_region` —las claves de cruce— se
    # dejan exactamente como vienen, de modo que la ortografía no interviene en ningún enlace.
    out["name"] = out.comuna_norm.map(lambda s: LB.comuna_name(comuna_name.get(s, s if s else "no informado")))
    out["level"] = "comuna"
    reg = (out.loc[out.match_method != "unmatched"]
           .groupby(["year", "variant", "position", "panel", "cut_region"], observed=True)
           .agg(n_episodes=("n_episodes", "sum"), n_persons_within_year=("n_persons_within_year", "sum")).reset_index())
    reg["level"] = "region"
    reg["comuna_norm"] = ""
    reg["cut_comuna"] = np.nan
    reg["match_method"] = "aggregated from matched comunas"
    reg["name"] = reg.cut_region.map(lambda c: region_name.get(int(c), str(c)))
    unm = (out.loc[out.match_method == "unmatched"]
           .groupby(["year", "variant", "position", "panel"], observed=True)
           .agg(n_episodes=("n_episodes", "sum"), n_persons_within_year=("n_persons_within_year", "sum")).reset_index())
    unm["level"] = "region"
    unm["comuna_norm"] = ""
    unm["cut_comuna"] = np.nan
    unm["cut_region"] = np.nan
    unm["match_method"] = "unmatched"
    unm["name"] = "no enlazada a comuna INE"
    res = pd.concat([out, reg, unm], ignore_index=True)
    res["suppression_flag"] = (res.n_episodes > 0) & (res.n_episodes < SUPPRESSION_THRESHOLD)
    res["n_episodes_display"] = np.where(res.suppression_flag, f"<{SUPPRESSION_THRESHOLD}", res.n_episodes.astype(int).astype(str))
    unit = ("Episodios GRD con F84 documentado y personas (identificadores válidos distintos dentro del año) por comuna "
            "de residencia declarada en el GRD y por región agregada. La comuna es de RESIDENCIA, no el lugar de atención: "
            "no debe compararse con los denominadores de establecimiento sin una nota explícita. suppression_flag marca "
            f"las celdas con 1 a {SUPPRESSION_THRESHOLD - 1} eventos; n_episodes_display es la versión suprimida que debe "
            "usarse en cualquier tabla o figura publicada")
    den = ("Población INE por comuna cuando se calculen tasas (no incluida aquí); las filas variant = all_episodes dan "
           "los episodios GRD totales de la misma comuna, año y panel")
    return stamp(res.sort_values(["year", "variant", "position", "panel", "level", "name"]).reset_index(drop=True),
                 "grd_territory", "episodios GRD y personas dentro del año", "población INE (no incluida)", unit, den)


# ---------------------------------------------------------------------------
# (k) grd_age_single_year
# ---------------------------------------------------------------------------
def build_age_single(exp: pd.DataFrame, years_data: list[dict]) -> pd.DataFrame:
    g = (exp.groupby(["year", "variant", "position", "panel", "sex", "age_single"], observed=True)
         .size().rename("n_episodes").reset_index())
    comp = []
    for d in years_data:
        a = d["age_single"]
        for panel in PANELS:
            sel = a if panel == "observed" else a.loc[a.fix]
            s = sel.groupby(["sex", "age_single"], observed=True)["n"].sum().rename("n_episodes").reset_index()
            s["year"], s["variant"], s["position"], s["panel"] = d["year"], COMPARISON, "all", panel
            comp.append(s)
    out = pd.concat([g] + comp, ignore_index=True)
    out["age_years"] = out.age_single.where(out.age_single >= 0)
    out["age_label"] = np.where(out.age_single < 0, "unknown",
                                np.where(out.age_single >= 100, "100+", out.age_single.astype(str)))
    out = out.drop(columns=["age_single"])
    out["n_cell_total"] = out.groupby(["year", "variant", "position", "panel"], observed=True)["n_episodes"].transform("sum")
    unit = ("Episodios GRD por edad simple en años cumplidos al ingreso (floor((FECHA_INGRESO − FECHA_NACIMIENTO)/365,25); "
            "100 = 100 años o más; «unknown» = edad no calculable o fuera de 0–110) y sexo declarado")
    den = "Episodios de la misma celda año × variante × posición × panel (n_cell_total)"
    return stamp(out.sort_values(["year", "variant", "position", "panel", "sex", "age_years"]).reset_index(drop=True),
                 "grd_age_single_year", "episodios GRD", "n_cell_total", unit, den)


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------
class Controls:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name, key, expected, observed, note="", tol=0.0):
        try:
            e, o = float(expected), float(observed)
            diff = o - e
            rel = diff / e if e else (0.0 if diff == 0 else np.nan)
            status = "ok" if (diff == 0 or (tol and abs(rel) <= tol)) else "differs"
        except (TypeError, ValueError):
            diff, rel = np.nan, np.nan
            status = "ok" if str(expected) == str(observed) else "differs"
        if expected is None:
            status = "info"
            diff, rel = np.nan, np.nan
        self.rows.append(dict(name=name, key=key, expected=expected, observed=observed,
                              abs_diff=diff, rel_diff=rel, status=status, note=note))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def build_controls(out: dict[str, pd.DataFrame], years_data: list[dict], long: pd.DataFrame,
                   specialty_top: list[str], fixed: set[str]) -> pd.DataFrame:
    ctl = Controls()
    ctl.add("fixed_panel_size", "2019-2022", 65, len(fixed),
            "panel fijo leído de outputs/tidy/grd_fixed_panel_hospitals.csv (módulo 01); nunca se recalcula aquí")

    # --- totales anuales frente a grd_year_summary.csv (módulo 01) --------------------------------
    ys = C.read_tidy("grd_year_summary")
    ys = ys.loc[ys.activity == "all"]
    mon = out["grd_monthly"]
    for variant in VARIANTS:
        for panel in PANELS:
            for position in POSITIONS:
                r = ys.loc[(ys.variant == variant) & (ys.panel == panel) & (ys.position == position)]
                for year in sorted(mon.year.unique()):
                    exp_v = r.loc[r.year == year, "n_episodes_f84"]
                    if exp_v.empty:
                        continue
                    obs = int(mon.loc[(mon.year == year) & (mon.variant == variant) & (mon.panel == panel) &
                                      (mon.position == position), "n_episodes_f84"].sum())
                    ctl.add("grd_year_summary_vs_monthly_sum", f"{variant}|{panel}|{position}|{year}",
                            int(exp_v.iloc[0]), obs,
                            "suma de los 12 meses más la fila de fecha de ingreso no analizable = total anual del módulo 01")
    # denominador mensual = episodios totales del año
    for d in years_data:
        obs = int(mon.loc[(mon.year == d["year"]) & (mon.panel == "observed") & (mon.variant == PRIMARY_VARIANT) &
                          (mon.position == "any"), "n_episodes_total"].sum())
        ctl.add("grd_records_total_vs_monthly_denominator", d["year"], d["n_rows"], obs,
                "suma de los episodios totales por mes (panel observado) = filas leídas del archivo anual")
        exp_v = CFG.CONTROLS["grd_records_total"].get(d["year"])
        if exp_v is not None:
            ctl.add("grd_records_total", d["year"], exp_v, d["n_rows"], "config.CONTROLS (valor preespecificado del brief)")
    for year, exp_v in CFG.CONTROLS["grd_f84_any"].items():
        obs = int(mon.loc[(mon.year == year) & (mon.variant == PRIMARY_VARIANT) & (mon.panel == "observed") &
                          (mon.position == "any"), "n_episodes_f84"].sum())
        ctl.add("grd_f84_any", year, exp_v, obs, "config.CONTROLS; variante con_rett, panel observado, cualquier posición")
    for year, exp_v in CFG.CONTROLS["grd_f84_principal"].items():
        obs = int(mon.loc[(mon.year == year) & (mon.variant == PRIMARY_VARIANT) & (mon.panel == "observed") &
                          (mon.position == "principal"), "n_episodes_f84"].sum())
        ctl.add("grd_f84_principal", year, exp_v, obs, "config.CONTROLS; DIAGNOSTICO1 ∈ F84")
    for year, exp_v in CFG.CONTROLS["grd_f84_any_panel65"].items():
        obs = int(mon.loc[(mon.year == year) & (mon.variant == PRIMARY_VARIANT) & (mon.panel == "fixed65") &
                          (mon.position == "any"), "n_episodes_f84"].sum())
        ctl.add("grd_f84_any_panel65", year, exp_v, obs, "config.CONTROLS; panel fijo de 65 hospitales")

    # --- coherencia interna de cada tabla ---------------------------------------------------------
    los = out["grd_length_of_stay"]
    losa = out["grd_los_age"]
    for keys, g in los.loc[los.activity == "all"].groupby(["year", "variant", "position", "panel"], observed=True):
        a = losa.loc[(losa.year == keys[0]) & (losa.variant == keys[1]) & (losa.position == keys[2]) &
                     (losa.panel == keys[3]) & (losa.activity == "all")]
        ctl.add("los_age_sum_equals_los_total", "|".join(map(str, keys)), int(g.n_valid_dates.sum()),
                int(a.n_valid_dates.sum()), "la suma de los grupos etarios OMS reproduce el total de la celda")
    feat = out["grd_episode_features"]
    for keys, g in feat.groupby(["year", "variant", "position", "panel", "variable"], observed=True):
        ctl.add("features_sum_equals_cell_total", "|".join(map(str, keys)), int(g.n_cell_total.iloc[0]),
                int(g.n_episodes.sum()), "la suma de las categorías reproduce el total de la celda")
    cod = out["grd_codiagnoses"]
    for keys, g in cod.loc[cod.code_position == "any"].groupby(["year", "variant", "position", "panel"], observed=True):
        n_eps = int(g.n_f84_episodes_cell.iloc[0])
        obs = int(g.n_episodes.sum())
        ceiling = n_eps * MAX_DIAG_FIELDS
        ctl.rows.append(dict(name="codiagnoses_not_above_episodes_times_35", key="|".join(map(str, keys)),
                             expected=f"<= {ceiling}", observed=obs, abs_diff=obs - ceiling,
                             rel_diff=(obs - ceiling) / ceiling if ceiling else np.nan,
                             status="ok" if obs <= ceiling else "differs",
                             note=("un episodio aporta como máximo 34 categorías distintas de co-diagnóstico "
                                   f"(episodios de la celda = {n_eps}; techo teórico = episodios × 35)")))
    terr = out["grd_territory"]
    for keys, g in terr.loc[terr.level == "comuna"].groupby(["year", "variant", "position", "panel"], observed=True):
        exp_v = int(mon.loc[(mon.year == keys[0]) & (mon.variant == keys[1]) & (mon.position == keys[2]) &
                            (mon.panel == keys[3]), "n_episodes_f84"].sum()) if keys[1] != COMPARISON else \
            int(mon.loc[(mon.year == keys[0]) & (mon.panel == keys[3]) & (mon.variant == PRIMARY_VARIANT) &
                        (mon.position == "any"), "n_episodes_total"].sum())
        ctl.add("territory_sum_equals_annual_total", "|".join(map(str, keys)), exp_v, int(g.n_episodes.sum()),
                "la suma de las comunas (incluidas las no enlazadas) reproduce el total anual de la celda")
    age = out["grd_age_single_year"]
    for keys, g in age.groupby(["year", "variant", "position", "panel"], observed=True):
        exp_v = int(mon.loc[(mon.year == keys[0]) & (mon.variant == keys[1]) & (mon.position == keys[2]) &
                            (mon.panel == keys[3]), "n_episodes_f84"].sum()) if keys[1] != COMPARISON else \
            int(mon.loc[(mon.year == keys[0]) & (mon.panel == keys[3]) & (mon.variant == PRIMARY_VARIANT) &
                        (mon.position == "any"), "n_episodes_total"].sum())
        ctl.add("age_single_sum_equals_annual_total", "|".join(map(str, keys)), exp_v, int(g.n_episodes.sum()),
                "la suma de las edades simples (incluida «unknown») reproduce el total anual de la celda")

    # --- método de cuantiles: distribución de frecuencias frente a los valores directos -------------
    rng = np.random.default_rng(20260905)
    sample = rng.integers(0, 60, size=5000)
    s = pd.Series(sample, dtype=float)
    vc = s.value_counts().sort_index()
    direct, weighted = series_stats(s), dist_stats(vc.index.to_numpy(dtype=float), vc.to_numpy())
    for key in ("mean", "sd", "median", "q25", "q75", "p90", "max"):
        ctl.add("los_quantile_method_agreement", key, round(direct[key], 10), round(weighted[key], 10),
                "dist_stats (distribución de frecuencias, usada en el grupo de comparación) reproduce series_stats "
                "(valores directos, usado en las series F84) sobre una muestra de verificación de 5.000 valores")

    # --- comparación con el primer estudio (output_files/consolidacion/grd_epi_los_summary.csv) ------
    ref_path = CFG.REPO / "output_files" / "consolidacion" / "grd_epi_los_summary.csv"
    if ref_path.is_file():
        ref = pd.read_csv(ref_path)
        ref = ref.loc[(ref.year == 2024) & (ref.TIPO_ACTIVIDAD == "HOSPITALIZACIÓN")]
        pairs = [("con_rett", "F84_historico"), ("sin_rett", "TEA_operacional"), ("strict_autism_f840", "autismo_F840")]
        for variant, definition in pairs:
            r = ref.loc[ref.definition == definition]
            # el primer estudio separa 'principal' (solo principal) y 'principal_y_secundario'
            for position, roles in (("principal", ["principal", "principal_y_secundario"]), ("secondary_only", ["solo_secundario"])):
                sub = r.loc[r.role.isin(roles)]
                if sub.empty:
                    continue
                n_ref = int(sub.n.sum())
                med_ref = float(sub["median"].iloc[0]) if len(sub) == 1 else np.nan
                mine = los.loc[(los.year == 2024) & (los.variant == variant) & (los.position == position) &
                               (los.panel == "observed") & (los.activity == "hospitalisation")]
                n_mine = int(mine["n_valid_dates"].iloc[0]) if len(mine) else np.nan
                med_mine = float(mine["median_days"].iloc[0]) if len(mine) else np.nan
                note = (f"primer estudio ({definition}, roles {'+'.join(roles)}, 2024, HOSPITALIZACIÓN) frente a este módulo "
                        f"({variant}, {position}); las definiciones no son idénticas (TEA_operacional = F84.0/.1/.5/.8/.9 "
                        "mientras sin_rett = F84 sin F84.2) y el primer estudio elimina duplicados exactos: se informa la "
                        "comparación, no se fuerza igualdad")
                ctl.add("los_2024_n_vs_first_study", f"{variant}|{position}", n_ref, n_mine, note)
                if med_ref == med_ref:
                    ctl.add("los_2024_median_vs_first_study", f"{variant}|{position}", med_ref, med_mine, note)
                else:
                    ctl.add("los_2024_median_vs_first_study", f"{variant}|{position}", None,
                            med_mine, note + "; el primer estudio separa la mediana en dos roles y no se puede sumar")
    else:
        ctl.add("los_2024_median_vs_first_study", "grd_epi_los_summary.csv", None, "archivo ausente",
                f"no se encontró {ref_path}; la comparación con el primer estudio queda pendiente")

    # --- información descriptiva (sin valor esperado) ----------------------------------------------
    for d in years_data:
        ctl.add("dates_unparsed_admission", d["year"], 0, d["dates_unparsed"]["admission"],
                "FECHA_INGRESO no analizable (AAAA-MM-DD o DD-MM-AAAA); esos episodios van al mes «unknown» y quedan fuera de la estadía")
        ctl.add("dates_unparsed_discharge", d["year"], 0, d["dates_unparsed"]["discharge"],
                "FECHAALTA no analizable; el episodio queda sin estadía (nunca se imputa)")
        ctl.add("negative_length_of_stay", d["year"], 0, d["n_negative_los"],
                "alta anterior al ingreso: se excluye de la estadía y se informa en n_invalid_dates")
        ctl.add("seconds_pass1", d["year"], None, round(d["seconds"], 1), "segundos de lectura de la pasada 1")
    ctl.add("specialty_top20", "|".join(specialty_top), None, len(specialty_top),
            "20 especialidades más frecuentes entre los episodios F84 (con_rett, cualquier posición, panel observado, 2019–2024)")
    unm = terr.loc[(terr.level == "comuna") & (terr.match_method == "unmatched"), "comuna_norm"].unique()
    ctl.add("unmatched_comuna_names", "|".join(sorted(map(str, unm))) or "(ninguna)", None, len(unm),
            "nombres de comuna del GRD sin correspondencia en comuna_crosswalk.csv; nunca se aplica fuzzy matching")
    ctl.add("codiagnosis_rows", "grd_codiagnoses", None, len(long),
            "filas (episodio, categoría CIE-10, posición) antes de la expansión por variante/posición/panel")
    return ctl.frame()


# ---------------------------------------------------------------------------
# Tablas formateadas por variante e idioma (outputs/<variante>/<idioma>/extra/tables)
# ---------------------------------------------------------------------------
MONTHS = {"es": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]}
POSITION_LABEL = {"any": {"es": "Cualquier posición", "en": "Any position"},
                  "principal": {"es": "F84 principal", "en": "F84 principal"},
                  "secondary_only": {"es": "Solo secundario", "en": "Secondary only"},
                  "all": {"es": "Todos los episodios GRD", "en": "All GRD episodes"}}
ACTIVITY_LABEL = {"all": {"es": "Todas las actividades", "en": "All activities"},
                  "hospitalisation": {"es": "Hospitalización", "en": "Hospitalisation"},
                  "cma": {"es": "Cirugía mayor ambulatoria", "en": "Major ambulatory surgery"},
                  "other": {"es": "Otras modalidades (solo 2019)", "en": "Other modalities (2019 only)"}}
SEX_LABEL = {"HOMBRE": {"es": "Hombres", "en": "Males"}, "MUJER": {"es": "Mujeres", "en": "Females"},
             "unknown": {"es": "Sexo no informado", "en": "Sex not reported"}}
NE = {"es": "n/e", "en": "n/e"}


def num(x, dec=0, lang="es"):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) or pd.isna(x):
        return NE[lang]
    return C.fmt_number(float(x), dec, lang)


def pct(x, lang="es", dec=1):
    if x is None or pd.isna(x):
        return NE[lang]
    return C.fmt_number(float(x), dec, lang) + (" %" if lang == "es" else "%")


def n_pct(n, p, lang="es"):
    return f"{num(n, 0, lang)} ({pct(p, lang)})"


def ci(lo, hi, dec=1, lang="es"):
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi):
        return NE[lang]
    return f"{num(lo, dec, lang)}–{num(hi, dec, lang)}"


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


NOTE_COMMON = {
    "es": ("Los recuentos son reconocimiento administrativo (episodios GRD con F84 documentado), nunca prevalencia ni "
           "incidencia, y un episodio con F84 secundario no es una «hospitalización por autismo». Fuente: "
           "GRD_PUBLICO_2019..2024.csv (FONASA/MINSAL). Panel observado: 65, 65, 65, 65, 68 y 72 hospitales en 2019–2024; "
           f"{C.fixed_panel_gloss('es', 'definition')}. 2020–2021: disrupción del reporte por la "
           "pandemia; la Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con efecto estimable. "
           "Las personas se cuentan solo dentro de cada año o era de identificador."),
    "en": ("Counts are administrative recognition (GRD episodes with documented F84), never prevalence or incidence, and "
           "an episode with a secondary F84 is not a 'hospitalisation for autism'. Source: GRD_PUBLICO_2019..2024.csv "
           "(FONASA/MINSAL). Observed panel: 65, 65, 65, 65, 68 and 72 hospitals in 2019–2024; "
           f"{C.fixed_panel_gloss('en', 'definition')}. 2020–2021: pandemic reporting disruption; Law 21.545 (March 2023) is policy "
           "context, not an intervention with an estimable effect. Persons are counted only within each year or "
           "identifier era."),
}


def extra_dir(variant: str, lang: str) -> Path:
    p = CFG.OUT / variant / lang / "extra" / "tables"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_pair(tdir: Path, name: str, formatted: pd.DataFrame, numeric: pd.DataFrame) -> list[str]:
    paths = [str(C.atomic_write_csv(formatted, tdir / f"{name}.csv", encoding="utf-8-sig")),
             str(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv"))]
    return paths


def build_extra_tables(out: dict[str, pd.DataFrame], variant: str, lang: str) -> tuple[list[str], dict]:
    """Tablas formateadas del suplemento para una variante y un idioma."""
    tdir = extra_dir(variant, lang)
    written: list[str] = []
    titles: dict = {}
    years = sorted(out["grd_monthly"].year.unique())
    ylabels = [str(y) for y in years]
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    note = NOTE_COMMON[lang]

    def add(name, formatted, numeric, title, tnote):
        written.extend(write_pair(tdir, name, formatted, numeric))
        titles[name] = {"title": title, "note": tnote}

    # --- E1 estacionalidad ------------------------------------------------------------------------
    m = out["grd_monthly"]
    sel = m.loc[(m.variant == variant) & (m.position == "any") & (m.panel == "observed")]
    rows = []
    for month in range(1, 13):
        r = {"__k": MONTHS[lang][month - 1]}
        for y in years:
            c = sel.loc[(sel.year == y) & (sel.month == month)]
            if c.empty:
                r[str(y)] = NE[lang]
            else:
                r[str(y)] = f"{num(c.n_episodes_f84.iloc[0], 0, lang)} ({num(c.seasonal_index_f84.iloc[0], 2, lang)})"
        rows.append(r)
    unk = {"__k": {"es": "Fecha de ingreso no analizable", "en": "Unparsable admission date"}[lang]}
    for y in years:
        c = sel.loc[(sel.year == y) & (sel.month == 0)]
        unk[str(y)] = num(c.n_episodes_f84.iloc[0] if len(c) else 0, 0, lang)
    rows.append(unk)
    tot = {"__k": {"es": "Total del año", "en": "Year total"}[lang]}
    for y in years:
        tot[str(y)] = num(sel.loc[sel.year == y, "n_episodes_f84"].sum(), 0, lang)
    rows.append(tot)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Mes de ingreso", "en": "Month of admission"}[lang]})
    add("E1_grd_seasonality", f, sel.copy(),
        {"es": f"Episodios GRD con F84 documentado por mes de ingreso e índice estacional dentro del año, 2019–2024 — {vlabel}",
         "en": f"GRD episodes with documented F84 by month of admission and within-year seasonal index, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: episodios (índice estacional, media de los 12 meses del año = 1). Cualquier posición, panel observado. " + note,
         "en": "Cell: episodes (seasonal index, mean of the year's 12 months = 1). Any position, observed panel. " + note}[lang])

    # --- E2 estadía -------------------------------------------------------------------------------
    los = out["grd_length_of_stay"]
    rows = []
    for position in POSITIONS + ["all"]:
        v = variant if position != "all" else COMPARISON
        sub = los.loc[(los.variant == v) & (los.position == position) & (los.panel == "observed") &
                      (los.activity == "hospitalisation")]
        r = {"__k": POSITION_LABEL[position][lang]}
        for y in years:
            c = sub.loc[sub.year == y]
            if c.empty or not c.n_valid_dates.iloc[0]:
                r[str(y)] = NE[lang]
            else:
                c = c.iloc[0]
                r[str(y)] = (f"{num(c.n_valid_dates, 0, lang)}; {num(c.median_days, 0, lang)} "
                             f"({num(c.q25_days, 0, lang)}–{num(c.q75_days, 0, lang)}); {num(c.mean_days, 1, lang)}")
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Posición de F84", "en": "F84 position"}[lang]})
    numeric = los.loc[((los.variant == variant) | (los.variant == COMPARISON)) & (los.panel == "observed")]
    add("E2_grd_length_of_stay", f, numeric.copy(),
        {"es": f"Estadía hospitalaria de los episodios GRD con F84 documentado y de todos los episodios GRD, 2019–2024 — {vlabel}",
         "en": f"Length of stay of GRD episodes with documented F84 and of all GRD episodes, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: n con fechas válidas; mediana (P25–P75); media, en días. Solo hospitalización, panel observado. "
               "Los episodios con fechas no analizables o alta anterior al ingreso se excluyen y se informan en la tabla "
               "numérica (n_invalid_dates); nunca se imputan. " + note,
         "en": "Cell: n with valid dates; median (P25–P75); mean, in days. Hospitalisation only, observed panel. Episodes "
               "with unparsable dates or discharge before admission are excluded and reported in the numeric companion "
               "(n_invalid_dates); they are never imputed. " + note}[lang])

    # --- E3 estadía por edad ----------------------------------------------------------------------
    losa = out["grd_los_age"]
    sub = losa.loc[(losa.panel == "observed") & (losa.activity == "hospitalisation") &
                   (((losa.variant == variant) & (losa.position == "any")) |
                    ((losa.variant == COMPARISON) & (losa.position == "all")))]
    rows = []
    for ag in AGE_LEVELS:
        r = {"__k": ag if ag != "unknown" else {"es": "Edad desconocida", "en": "Unknown age"}[lang]}
        for who, lbl in ((variant, {"es": "F84 documentado", "en": "Documented F84"}[lang]),
                         (COMPARISON, POSITION_LABEL["all"][lang])):
            c = sub.loc[(sub.variant == who) & (sub.age_group == ag)]
            n = int(c.n_valid_dates.sum()) if len(c) else 0
            if n == 0:
                # cero observado con mediana no estimable; nunca se presenta como dato ausente
                r[lbl] = f"{num(0, 0, lang)}; {NE[lang]}"
                continue
            with_data = c.loc[c.n_valid_dates > 0]
            med = float(with_data.loc[with_data.year == with_data.year.max(), "median_days"].iloc[0])
            r[lbl] = f"{num(n, 0, lang)}; {num(med, 0, lang)}"
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Grupo etario OMS", "en": "WHO age group"}[lang]})
    add("E3_grd_los_by_age", f, sub.copy(),
        {"es": f"Estadía hospitalaria por grupo etario quinquenal (OMS), episodios con F84 documentado y todos los episodios GRD, 2019–2024 — {vlabel}",
         "en": f"Length of stay by five-year WHO age group, episodes with documented F84 and all GRD episodes, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: n acumulado 2019–2024 con fechas válidas; mediana del último año disponible, en días. La tabla "
               "numérica contiene todos los años y estadísticos. Solo hospitalización, panel observado, cualquier posición. " + note,
         "en": "Cell: cumulative 2019–2024 n with valid dates; median of the latest available year, in days. The numeric "
               "companion carries every year and statistic. Hospitalisation only, observed panel, any position. " + note}[lang])

    # --- E4 características del episodio ----------------------------------------------------------
    feat = out["grd_episode_features"]
    sub = feat.loc[(feat.panel == "observed") &
                   (((feat.variant == variant) & (feat.position == "any")) | (feat.variant == COMPARISON))]
    rows = []
    last = years[-1]
    for var in FEATURE_VARIABLES:
        v = sub.loc[(sub.variable == var) & (sub.variant == variant)]
        order = v.groupby("value", observed=True)["n_episodes"].sum().sort_values(ascending=False)
        for value in order.index:
            r = {"__v": var, "__c": LB.tidy_text(value, lang)}
            for y in years:
                c = v.loc[(v.year == y) & (v.value == value)]
                r[str(y)] = n_pct(c.n_episodes.iloc[0], c.pct_within_cell.iloc[0], lang) if len(c) else n_pct(0, 0.0, lang)
            comp_var = sub.loc[(sub.variable == var) & (sub.variant == COMPARISON) & (sub.year == last)]
            comp = comp_var.loc[comp_var.value == value]
            # la variable existe pero la categoría no aparece → cero observado; si no hay filas de la
            # variable en ese año, la celda es «no estimable» (estados distintos, nunca se confunden)
            r[{"es": f"Todos los episodios GRD {last}", "en": f"All GRD episodes {last}"}[lang]] = (
                n_pct(comp.n_episodes.iloc[0], comp.pct_within_cell.iloc[0], lang) if len(comp)
                else (n_pct(0, 0.0, lang) if len(comp_var) else NE[lang]))
            rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__v": {"es": "Variable", "en": "Variable"}[lang],
                                           "__c": {"es": "Categoría", "en": "Category"}[lang]})
    add("E4_grd_episode_features", f, sub.copy(),
        {"es": f"Características administrativas de los episodios GRD con F84 documentado, 2019–2024, con todos los episodios GRD como comparación — {vlabel}",
         "en": f"Administrative characteristics of GRD episodes with documented F84, 2019–2024, with all GRD episodes as comparison — {vlabel}"}[lang],
        # La regla de traducción de las categorías del episodio es UNA y se declara en `labels.py`
        # (`GRD_CATEGORY_NOTE`), de modo que esta tabla y la Tabla S109 del módulo 16 digan lo mismo. La
        # redacción propia que había aquí afirmaba que el PAÍS se imprime en su forma original del GRD en
        # los dos idiomas, mientras la S109 declaraba —y las dos tablas hacen— lo contrario, y además
        # callaba TIPO_INGRESO, TIPO_ACTIVIDAD, TIPO_PROCEDENCIA, TIPOALTA y el sexo, que también se traducen.
        {"es": "Celda: episodios (% de la columna del año). Cualquier posición, panel observado. Los valores vacíos "
               "aparecen como «no informado» y nunca como cero. ESPECIALIDAD_MEDICA se colapsa a las 20 especialidades "
               "más frecuentes entre los episodios F84 más «otra especialidad». " + LB.GRD_CATEGORY_NOTE["es"] + " " + note,
         "en": "Cell: episodes (% of the year column). Any position, observed panel. Empty values appear as 'not reported' "
               "and never as zero. ESPECIALIDAD_MEDICA is collapsed to the 20 most frequent specialties among F84 episodes "
               "plus 'other specialty'. " + LB.GRD_CATEGORY_NOTE["en"] + " " + note}[lang])

    # --- E5 peso GRD y grupos ---------------------------------------------------------------------
    w = out["grd_grd_weight"]
    sub = w.loc[(w.variant == variant) & (w.position == "any") & (w.panel == "observed")]
    rows = []
    r = {"__k": {"es": "Peso relativo IR-29301: mediana (P25–P75)", "en": "IR-29301 relative weight: median (P25–P75)"}[lang]}
    for y in years:
        c = sub.loc[(sub.year == y) & (sub.row_type == "weight_summary")]
        r[str(y)] = (f"{num(c['median'].iloc[0], 3, lang)} "
                     f"({num(c['q25'].iloc[0], 3, lang)}–{num(c['q75'].iloc[0], 3, lang)})") if len(c) else NE[lang]
    rows.append(r)
    r = {"__k": {"es": "Peso relativo IR-29301: media", "en": "IR-29301 relative weight: mean"}[lang]}
    for y in years:
        c = sub.loc[(sub.year == y) & (sub.row_type == "weight_summary")]
        r[str(y)] = num(c["mean"].iloc[0], 3, lang) if len(c) else NE[lang]
    rows.append(r)
    top = sub.loc[sub.row_type == "grd_group"].sort_values("ir_grd_rank")
    for code in top.drop_duplicates("ir_grd_code").ir_grd_code:
        r = {"__k": f"GRD {code}"}
        for y in years:
            c = top.loc[(top.year == y) & (top.ir_grd_code == code)]
            r[str(y)] = n_pct(c.n.iloc[0], c.pct_of_cell.iloc[0], lang) if len(c) else n_pct(0, 0.0, lang)
        rows.append(r)
    other = sub.loc[sub.row_type == "grd_group_other"]
    r = {"__k": {"es": "Otros grupos GRD y no informado", "en": "Other GRD groups and not reported"}[lang]}
    for y in years:
        c = other.loc[other.year == y]
        r[str(y)] = n_pct(c.n.iloc[0], c.pct_of_cell.iloc[0], lang) if len(c) else NE[lang]
    rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Indicador", "en": "Indicator"}[lang]})
    add("E5_grd_weight_and_groups", f, sub.copy(),
        {"es": f"Peso relativo IR-29301 y 15 grupos GRD más frecuentes entre los episodios con F84 documentado, 2019–2024 — {vlabel}",
         "en": f"IR-29301 relative weight and 15 most frequent GRD groups among episodes with documented F84, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda de los grupos: episodios (% de los episodios F84 del año). El ranking se fija con el total 2019–2024 "
               "de la celda variante × posición × panel. Cualquier posición, panel observado. " + note,
         "en": "Group cell: episodes (% of the year's F84 episodes). Ranking is fixed on the 2019–2024 total of the "
               "variant × position × panel cell. Any position, observed panel. " + note}[lang])

    # --- E6 co-diagnósticos -----------------------------------------------------------------------
    cod = out["grd_codiagnoses"]
    sub = cod.loc[(cod.variant == variant) & (cod.position == "any") & (cod.panel == "observed") & (cod.code_position == "any")]
    order = sub.groupby("code3", observed=True)["n_episodes"].sum().sort_values(ascending=False).head(25)
    rows = []
    for code in order.index:
        rows.append({"__k": LB.icd_code_label(code, lang),
                     **{str(y): (lambda c: n_pct(c.n_episodes.iloc[0], c.pct_of_f84_episodes.iloc[0], lang) if len(c) else n_pct(0, 0.0, lang))(
                         sub.loc[(sub.year == y) & (sub.code3 == code)]) for y in years}})
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Categoría CIE-10 (3 caracteres)", "en": "ICD-10 category (3 characters)"}[lang]})
    add("E6_grd_codiagnoses_top25", f, sub.copy(),
        {"es": f"25 co-diagnósticos CIE-10 más frecuentes en los episodios GRD con F84 documentado, 2019–2024 — {vlabel}",
         "en": f"25 most frequent ICD-10 co-diagnoses in GRD episodes with documented F84, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: episodios con al menos un código de la categoría (% de los episodios F84 del año). Un episodio "
               "cuenta una vez por categoría. Se excluyen los propios códigos F84. Cualquier posición, panel observado. "
               "La profundidad de codificación media de todos los episodios pasó de 4,39 (2019) a 5,78 (2024): parte del "
               "aumento de co-diagnósticos refleja codificación, no morbilidad. " + LB.ICD10_SOURCE[lang] + " " + note,
         "en": "Cell: episodes with at least one code of the category (% of the year's F84 episodes). An episode counts "
               "once per category. F84 codes themselves are excluded. Any position, observed panel. Mean coding depth of "
               "all episodes rose from 4.39 (2019) to 5.78 (2024): part of the rise in co-diagnoses reflects coding, not "
               "morbidity. " + LB.ICD10_SOURCE[lang] + " " + note}[lang])

    # --- E7 capítulos y bloques -------------------------------------------------------------------
    ch = out["grd_codiagnosis_chapters"]
    sub = ch.loc[(ch.variant == variant) & (ch.position == "any") & (ch.panel == "observed") & (ch.code_position == "any")]
    rows = []
    for grouping in ("chapter", "mental_block"):
        g = sub.loc[sub.grouping == grouping]
        order = g.groupby("group_label", observed=True)["n_episodes"].sum().sort_values(ascending=False)
        for label in order.index:
            rows.append({"__g": {"chapter": {"es": "Capítulo CIE-10", "en": "ICD-10 chapter"}[lang],
                                 "mental_block": {"es": "Bloque de salud mental (F)", "en": "Mental-health block (F)"}[lang]}[grouping],
                         "__k": LB.icd_chapter_es_to(label, lang),
                         **{str(y): (lambda c: n_pct(c.n_episodes.iloc[0], c.pct_of_f84_episodes.iloc[0], lang) if len(c) else n_pct(0, 0.0, lang))(
                             g.loc[(g.year == y) & (g.group_label == label)]) for y in years}})
    f = pd.DataFrame(rows).rename(columns={"__g": {"es": "Agrupación", "en": "Grouping"}[lang],
                                           "__k": {"es": "Grupo", "en": "Group"}[lang]})
    add("E7_grd_codiagnosis_chapters", f, sub.copy(),
        {"es": f"Co-diagnósticos por capítulo CIE-10 y bloque de salud mental en los episodios GRD con F84 documentado, 2019–2024 — {vlabel}",
         "en": f"Co-diagnoses by ICD-10 chapter and mental-health block in GRD episodes with documented F84, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: episodios con al menos un código del grupo (% de los episodios F84 del año). Un episodio cuenta una "
               "vez por grupo. Cualquier posición, panel observado. " + note,
         "en": "Cell: episodes with at least one code of the group (% of the year's F84 episodes). An episode counts once "
               "per group. Any position, observed panel. " + note}[lang])

    # --- E8 diagnóstico principal cuando F84 es solo secundario ------------------------------------
    sub = cod.loc[(cod.variant == variant) & (cod.position == "secondary_only") & (cod.panel == "observed") &
                  (cod.code_position == "principal")]
    order = sub.groupby("code3", observed=True)["n_episodes"].sum().sort_values(ascending=False).head(25)
    rows = []
    for code in order.index:
        rows.append({"__k": LB.icd_code_label(code, lang),
                     **{str(y): (lambda c: n_pct(c.n_episodes.iloc[0], c.pct_of_f84_episodes.iloc[0], lang) if len(c) else n_pct(0, 0.0, lang))(
                         sub.loc[(sub.year == y) & (sub.code3 == code)]) for y in years}})
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Diagnóstico principal (CIE-10, 3 caracteres)", "en": "Principal diagnosis (ICD-10, 3 characters)"}[lang]})
    add("E8_grd_principal_when_secondary", f, sub.copy(),
        {"es": f"Diagnóstico principal de los episodios GRD en que F84 aparece solo como diagnóstico secundario, 2019–2024 — {vlabel}",
         "en": f"Principal diagnosis of GRD episodes in which F84 appears only as a secondary diagnosis, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: episodios (% de los episodios con F84 solo secundario del año). En 2024, 95,5 % de los episodios con "
               "F84 lo tienen solo como diagnóstico secundario: esta tabla muestra por qué motivo se hospitaliza. Panel "
               "observado. " + LB.ICD10_SOURCE[lang] + " " + note,
         "en": "Cell: episodes (% of the year's secondary-only F84 episodes). In 2024, 95.5% of episodes with F84 carry it "
               "only as a secondary diagnosis: this table shows the reason for admission. Observed panel. "
               + LB.ICD10_SOURCE[lang] + " " + note}[lang])

    # --- E9 reingresos ----------------------------------------------------------------------------
    re_ = out.get("grd_readmission", pd.DataFrame())
    sub = (re_.loc[(re_.variant == variant) & (re_.panel == "observed") & (re_.position == "any")]
           if len(re_) else re_)
    rows = []
    for era in ERAS:
        for horizon in HORIZONS:
            g = sub.loc[(sub.era == era) & (sub.horizon_days == horizon)]
            if g.empty:
                continue
            elig = int(g.n_eligible.sum())
            any_c = int(g.n_readmitted_any_cause.sum())
            f84_c = int(g.n_readmitted_f84.sum())
            p_any, lo_any, hi_any = C.wilson(any_c, elig)
            p_f84, lo_f84, hi_f84 = C.wilson(f84_c, elig)
            rows.append({{"es": "Era del identificador", "en": "Identifier era"}[lang]: C.yspan(era),
                         {"es": "Horizonte (días)", "en": "Horizon (days)"}[lang]: num(horizon, 0, lang),
                         {"es": "Egresos", "en": "Discharges"}[lang]: num(int(g.n_discharges.sum()), 0, lang),
                         {"es": "Elegibles", "en": "Eligible"}[lang]: num(elig, 0, lang),
                         {"es": "Reingreso por cualquier causa, n (%) [", "en": "Readmission for any cause, n (%) ["}[lang] + LBL("ci95", lang) + "]":
                             f"{n_pct(any_c, 100 * p_any if elig else np.nan, lang)} [{ci(100 * lo_any, 100 * hi_any, 1, lang)}]" if elig else NE[lang],
                         {"es": "Reingreso con código F84, n (%) [", "en": "Readmission with an F84 code, n (%) ["}[lang] + LBL("ci95", lang) + "]":
                             f"{n_pct(f84_c, 100 * p_f84 if elig else np.nan, lang)} [{ci(100 * lo_f84, 100 * hi_f84, 1, lang)}]" if elig else NE[lang]})
    f = pd.DataFrame(rows)
    if len(f):
        add("E9_grd_readmission", f, sub.copy(),
            {"es": f"Reingresos hospitalarios tras un egreso GRD con F84 documentado, por era de identificador y horizonte — {vlabel}",
             "en": f"Hospital readmissions after a GRD discharge with documented F84, by identifier era and horizon — {vlabel}"}[lang],
            {"es": "Elegibles = egresos con identificador y fechas válidas y con el horizonte completo dentro de la misma era. "
                   "El identificador cambia de formato entre 2020 y 2021: las eras 2019–2020 y 2021–2024 nunca se enlazan. "
                   "Los reingresos son episodios del mismo identificador dentro de la era; no son trayectorias individuales "
                   "verificadas ni se enlazan con otras fuentes. IC de Wilson al 95 %. " + note,
             "en": "Eligible = discharges with a valid identifier and valid dates and with the full horizon inside the same era. "
                   "The identifier changes format between 2020 and 2021: the 2019–2020 and 2021–2024 eras are never linked. "
                   "Readmissions are episodes of the same identifier within the era; they are not verified individual "
                   "trajectories and are not linked to other sources. Wilson 95% CI. " + note}[lang])

    # --- E10 multiplicidad ------------------------------------------------------------------------
    mu = out["grd_multiplicity"]
    sub = mu.loc[(mu.variant == variant) & (mu.panel == "observed") & (mu.position == "any")]
    rows = []
    for b in MULTIPLICITY_BINS:
        r = {"__k": b}
        for era in ERAS:
            c = sub.loc[(sub.era == era) & (sub.episodes_per_identifier == b)]
            # La era es la clave de MÁQUINA («2019-2020») y también la CABECERA impresa de la columna: al
            # rotular se pasa a la raya corta que el resto del corpus usa para una ventana de años.
            r[C.yspan(era)] = f"{n_pct(c.n_persons.iloc[0], c.pct_persons.iloc[0], lang)}" if len(c) else NE[lang]
        rows.append(r)
    r = {"__k": {"es": "Total de identificadores", "en": "Total identifiers"}[lang]}
    for era in ERAS:
        c = sub.loc[sub.era == era]
        r[C.yspan(era)] = num(c.n_persons_total.iloc[0], 0, lang) if len(c) else NE[lang]
    rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Episodios por identificador", "en": "Episodes per identifier"}[lang]})
    add("E10_grd_multiplicity", f, sub.copy(),
        {"es": f"Episodios GRD con F84 documentado por identificador, dentro de cada era de identificador — {vlabel}",
         "en": f"GRD episodes with documented F84 per identifier, within each identifier era — {vlabel}"}[lang],
        {"es": "Celda: identificadores (% de los identificadores de la era). Los identificadores no se deduplican entre "
               "eras y no son personas verificadas: el GRD no está enlazado con ninguna otra fuente. " + note,
         "en": "Cell: identifiers (% of the era's identifiers). Identifiers are not deduplicated across eras and are not "
               "verified persons: the GRD is not linked to any other source. " + note}[lang])

    # --- E11 territorio (región) ------------------------------------------------------------------
    terr = out["grd_territory"]
    sub = terr.loc[(terr.variant == variant) & (terr.position == "any") & (terr.panel == "observed") & (terr.level == "region")]
    rows = []
    for name_ in sub.drop_duplicates("name").sort_values("cut_region")["name"]:
        r = {"__k": name_}
        for y in years:
            c = sub.loc[(sub.year == y) & (sub.name == name_)]
            r[str(y)] = c.n_episodes_display.iloc[0] if len(c) else num(0, 0, lang)
        rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Región de residencia", "en": "Region of residence"}[lang]})
    add("E11_grd_territory_region", f, terr.loc[(terr.variant == variant) & (terr.panel == "observed")].copy(),
        {"es": f"Episodios GRD con F84 documentado por región de RESIDENCIA declarada, 2019–2024 — {vlabel}",
         "en": f"GRD episodes with documented F84 by declared region of RESIDENCE, 2019–2024 — {vlabel}"}[lang],
        {"es": "Celda: episodios; las celdas con 1 a 4 eventos se muestran como «<5». La región es de residencia declarada "
               "en el GRD y no el lugar de atención: no debe compararse con denominadores de establecimiento sin nota "
               "explícita, y los flujos de derivación interregional no están corregidos. La tabla numérica incluye el "
               "nivel comunal y los nombres no enlazados al crosswalk INE. " + note,
         "en": "Cell: episodes; cells with 1 to 4 events are shown as '<5'. The region is the declared region of residence "
               "in the GRD, not the place of care: it must not be compared with establishment denominators without an "
               "explicit note, and inter-regional referral flows are not corrected. The numeric companion carries the "
               "comuna level and the names unmatched to the INE crosswalk. " + note}[lang])

    # --- E12 edad simple --------------------------------------------------------------------------
    age = out["grd_age_single_year"]
    sub = age.loc[(age.variant == variant) & (age.position == "any") & (age.panel == "observed")]
    rows = []
    bands = [(0, 4), (5, 9), (10, 14), (15, 19), (20, 29), (30, 44), (45, 200)]
    for lo_a, hi_a in bands:
        label = f"{lo_a}–{hi_a}" if hi_a < 200 else "45+"
        r = {"__k": label}
        for sex in ["HOMBRE", "MUJER"]:
            for y in [years[0], years[-1]]:
                c = sub.loc[(sub.year == y) & (sub.sex == sex) & sub.age_years.between(lo_a, hi_a)]
                r[f"{SEX_LABEL[sex][lang]} {y}"] = num(int(c.n_episodes.sum()), 0, lang)
        rows.append(r)
    r = {"__k": {"es": "Edad desconocida", "en": "Unknown age"}[lang]}
    for sex in ["HOMBRE", "MUJER"]:
        for y in [years[0], years[-1]]:
            c = sub.loc[(sub.year == y) & (sub.sex == sex) & (sub.age_label == "unknown")]
            r[f"{SEX_LABEL[sex][lang]} {y}"] = num(int(c.n_episodes.sum()), 0, lang)
    rows.append(r)
    f = pd.DataFrame(rows).rename(columns={"__k": {"es": "Tramo etario", "en": "Age band"}[lang]})
    add("E12_grd_age_single_year", f, sub.copy(),
        {"es": f"Episodios GRD con F84 documentado por tramo etario y sexo, primer y último año de la serie — {vlabel}",
         "en": f"GRD episodes with documented F84 by age band and sex, first and last year of the series — {vlabel}"}[lang],
        {"es": "Celda: episodios. La tabla numérica contiene la edad simple 0–100 (100 = 100 años o más) por año, sexo y "
               "panel, y los episodios totales del GRD como comparación. Cualquier posición, panel observado. " + note,
         "en": "Cell: episodes. The numeric companion carries single-year age 0–100 (100 = 100 or more) by year, sex and "
               "panel, and total GRD episodes as comparison. Any position, observed panel. " + note}[lang])

    merge_json(tdir / "titles.json", titles)
    written.append(str(tdir / "titles.json"))
    return written, titles


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", type=int, nargs="+", default=CFG.YEARS_GRD)
    ap.add_argument("--chunksize", type=int, default=200_000)
    ap.add_argument("--max-chunks", type=int, default=None, help="solo pruebas: limita los trozos leídos por año")
    ap.add_argument("--no-hash", action="store_true", help="omite el SHA-256 de los archivos fuente")
    ap.add_argument("--no-extra", action="store_true", help="omite las tablas formateadas por variante e idioma")
    ap.add_argument("--skip-linkage", action="store_true", help="omite la pasada 2 (reingresos)")
    args = ap.parse_args(argv)

    t_start = time.perf_counter()
    started = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    print(f"[{MODULE}] GRD en {CFG.PATHS['grd']}; años {args.years}; trozos de {args.chunksize:,} filas", flush=True)
    fixed = fixed_panel_codes()
    lookup, method, xw = comuna_lookup()
    print(f"  panel fijo: {len(fixed)} hospitales; crosswalk de comunas: {len(lookup)} nombres", flush=True)

    years_data = [read_year(y, args.chunksize, args.max_chunks, not args.no_hash, fixed) for y in args.years]
    f84 = pd.concat([d["f84"] for d in years_data], ignore_index=True)
    diag = np.vstack([d["diag"] for d in years_data]) if len(years_data) else np.empty((0, len(DIAGS)), dtype=object)
    print(f"[{MODULE}] pasada 1 completa: {len(f84):,} episodios con F84 en 2019–2024", flush=True)

    t_agg = time.perf_counter()
    keep = (["year", "hospital", "in_fixed65", "id", "id_valid", "activity", "sex", "age", "age_group", "age_band",
             "age_single", "month", "valid_los", "los", "los_bin", "comuna_norm", "weight", "ir_grd_code"] +
            [f"feat_{v}" for v in FEATURE_VARIABLES])
    exp = expand(f84, keep)
    print(f"  expansión variante × posición × panel: {len(exp):,} filas ({time.perf_counter() - t_agg:.1f} s)", flush=True)

    # 20 especialidades más frecuentes entre los episodios F84 (con_rett, cualquier posición, panel observado)
    ref = exp.loc[(exp.variant == PRIMARY_VARIANT) & (exp.position == "any") & (exp.panel == "observed")]
    counts = ref["feat_ESPECIALIDAD_MEDICA"].value_counts()
    specialty_top = [v for v in counts.index if v != "no informado"][:TOP_SPECIALTIES]
    if "no informado" in counts.index:
        specialty_top.append("no informado")

    out: dict[str, pd.DataFrame] = {}
    steps = {}
    for name, fn in (("grd_monthly", lambda: build_monthly(exp, years_data)),
                     ("grd_length_of_stay", lambda: build_los(exp, years_data, by_age=False)),
                     ("grd_los_age", lambda: build_los(exp, years_data, by_age=True)),
                     ("grd_episode_features", lambda: build_features(exp, years_data, specialty_top)),
                     ("grd_grd_weight", lambda: build_weight(exp)),
                     ("grd_age_single_year", lambda: build_age_single(exp, years_data)),
                     ("grd_multiplicity", lambda: build_multiplicity(exp)),
                     ("grd_territory", lambda: build_territory(exp, years_data, lookup, method, xw))):
        t0 = time.perf_counter()
        out[name] = fn()
        steps[name] = round(time.perf_counter() - t0, 1)
        print(f"  {name}: {len(out[name]):,} filas ({steps[name]} s)", flush=True)

    t0 = time.perf_counter()
    long = codiagnosis_long(diag)
    out["grd_codiagnoses"], out["grd_codiagnosis_chapters"] = build_codiagnoses(exp, long)
    steps["grd_codiagnoses"] = round(time.perf_counter() - t0, 1)
    print(f"  grd_codiagnoses: {len(out['grd_codiagnoses']):,} filas; grd_codiagnosis_chapters: "
          f"{len(out['grd_codiagnosis_chapters']):,} filas ({steps['grd_codiagnoses']} s)", flush=True)

    # --- pasada 2: reingresos ---------------------------------------------------------------------
    linkage_seconds = {}
    if args.skip_linkage:
        out["grd_readmission"] = pd.DataFrame()
        print("  [--skip-linkage] pasada 2 omitida: grd_readmission queda vacía", flush=True)
    else:
        link_parts = []
        for era, era_years in ERAS.items():
            era_years = [y for y in era_years if y in args.years]
            if not era_years:
                continue
            ids = set(f84.loc[f84.id_valid & f84.year.isin(era_years), "id"].unique())
            print(f"  pasada 2 · era {era}: {len(ids):,} identificadores con al menos un episodio F84", flush=True)
            for y in era_years:
                t0 = time.perf_counter()
                part = read_year_linkage(y, ids, args.chunksize, args.max_chunks, fixed)
                linkage_seconds[y] = round(time.perf_counter() - t0, 1)
                print(f"    GRD {y}: {len(part):,} episodios de esas personas ({linkage_seconds[y]} s)", flush=True)
                link_parts.append(part)
        link = pd.concat(link_parts, ignore_index=True) if link_parts else pd.DataFrame()
        t0 = time.perf_counter()
        out["grd_readmission"] = build_readmission(link)
        steps["grd_readmission"] = round(time.perf_counter() - t0, 1)
        print(f"  grd_readmission: {len(out['grd_readmission']):,} filas ({steps['grd_readmission']} s)", flush=True)

    # --- escritura --------------------------------------------------------------------------------
    written = {}
    for name, df in out.items():
        if not len(df):
            continue
        path = C.atomic_write_csv(df, CFG.TIDY / f"{name}.csv")
        written[name] = {"path": str(path), "rows": int(len(df)), "columns": list(df.columns)}

    dictionary = pd.DataFrame(DICTIONARY)
    dict_path = C.atomic_write_csv(dictionary, CFG.TIDY / "grd_episode_detail_dictionary.csv")
    written["grd_episode_detail_dictionary"] = {"path": str(dict_path), "rows": int(len(dictionary))}

    controls = build_controls(out, years_data, long, specialty_top, fixed)
    ctl_path = C.atomic_write_csv(controls, CONTROLS_DIR / f"{MODULE}_controls.csv")
    written["controls"] = {"path": str(ctl_path), "rows": int(len(controls))}

    extra = {}
    if not args.no_extra:
        for variant in CFG.VARIANTS:
            for lang in CFG.LANGUAGES:
                t0 = time.perf_counter()
                paths, titles = build_extra_tables(out, variant, lang)
                extra[f"{variant}/{lang}"] = {"files": len(paths), "tables": sorted(titles), "seconds": round(time.perf_counter() - t0, 1)}
                print(f"  extra {variant}/{lang}: {len(titles)} tablas formateadas ({extra[f'{variant}/{lang}']['seconds']} s)", flush=True)

    runlog = {
        "module": MODULE, "script": SCRIPT, "started_utc": started,
        "seconds_total": round(time.perf_counter() - t_start, 1), "args": vars(args),
        "fixed_panel_size": len(fixed), "specialty_top": specialty_top,
        "years": [{k: v for k, v in d.items() if k not in {"f84", "diag", "los", "los_invalid", "month",
                                                           "features", "age_single", "territory"}} for d in years_data],
        "seconds_by_table": steps, "seconds_linkage_by_year": linkage_seconds,
        "outputs": written, "extra_tables": extra,
        "controls_status": controls.status.value_counts().to_dict(),
    }
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    differs = controls.loc[controls.status == "differs"]
    if len(differs):
        print(differs[["name", "key", "expected", "observed", "note"]].to_string(index=False, max_colwidth=90), flush=True)
    print(f"[{MODULE}] listo en {runlog['seconds_total']:,.1f} s; controles: {runlog['controls_status']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
