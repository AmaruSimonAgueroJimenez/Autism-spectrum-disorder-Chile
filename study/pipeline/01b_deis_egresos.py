# -*- coding: utf-8 -*-
"""01b_deis_egresos.py — Comprobación externa de la señal hospitalaria con los egresos hospitalarios DEIS 2019–2024.

Qué hace
--------
Lee los archivos abiertos de egresos hospitalarios del DEIS (`<DATA_ROOT>/DEIS/Egresos/{año}.csv`), documenta su
estructura (delimitador, codificación, columnas por año) y calcula, por año y por variante de definición
(`con_rett`: cualquier F84.x; `sin_rett`: F84.x excepto F84.2):
  * egresos totales; egresos con F84 en DIAG1, en DIAG2 y en cualquiera de las dos posiciones;
  * participación de F84 principal frente a secundario (en DEIS es 100 % principal por construcción, ver abajo);
  * desgloses por sexo, grupo de edad (esquema decenal 2019–2023; quinquenal OMS en 2024 y en la variante de 15
    columnas de 2021) y por pertenencia al SNSS / previsión;
  * tasas por 100.000 egresos del mismo año (IC 95 % exactos de Poisson);
  * una tabla de comparación anual con el GRD público (`deis_vs_grd_year.csv`): DEIS F84 principal (total, SNSS, no SNSS)
    frente a GRD F84 principal/cualquier posición del módulo 01 (`grd_year_summary.csv`, panel observado y fijo de 65,
    toda modalidad y hospitalización estricta), para `con_rett`, `sin_rett` y la serie estricta `strict_autism_f840`
    (solo F84.0). Si el módulo 01 no ha corrido, se usan los valores esperados de `config.CONTROLS` (solo con_rett) y el
    control `deis_vs_grd_join_source` queda en `differs`.

Diferencias DEIS frente a GRD (por qué NO son intercambiables)
--------------------------------------------------------------
* Cobertura: DEIS reúne los egresos de TODOS los establecimientos hospitalarios del país, pertenecientes y no
  pertenecientes al SNSS (clínicas privadas, FF.AA. y de Orden, mutuales, administración delegada). El GRD público
  cubre solo los hospitales del SNSS que operan el sistema GRD (65 en 2019–2022, 68 en 2023, 72 en 2024).
* Posiciones diagnósticas: DEIS publica dos columnas, DIAG1 = diagnóstico principal y DIAG2 = CAUSA EXTERNA
  (capítulo XX, V01–Y98) según el diccionario oficial. No existe diagnóstico secundario: un F84 documentado como
  comorbilidad no es observable en DEIS. GRD trae 35 posiciones y en 2024 el 95,5 % de los episodios F84 lo tienen
  solo en posición secundaria. La comparación válida es DEIS F84 principal frente a GRD F84 principal.
* Unidad: DEIS = egreso hospitalario (alta de una hospitalización); GRD = episodio financiado/codificado, que incluye
  cirugía mayor ambulatoria y otras modalidades. No se enlazan por persona ni por episodio.
* Edad: DEIS entrega grupos de edad, no fecha de nacimiento (decenales 2019–2023; quinquenales con subdivisión
  neonatal en 2024 y en la variante de 15 columnas de 2021).
* Establecimiento: DEIS no publica código de establecimiento; solo `PERTENENCIA_ESTABLECIMIENTO_SALUD` (SNSS/no SNSS).
* Supresión: DEIS enmascara con `*` las variables demográficas de una fracción de registros (1,7 %–7,9 % según año:
  2,6 % en 2019, 2,8 % en 2020, 2,4 % en 2021, 2,5 % en 2022, 7,9 % en 2023 y 1,7 % en 2024). Esos registros se conservan
  en los totales y se muestran como categoría `SUPRIMIDO`. La variante de 15 columnas de 2021 (`variants/detailed_age_15col`)
  contiene el mismo microdato SIN enmascarar (0 filas `*`; 35.656 en el canónico): sus totales SNSS/no SNSS difieren del
  canónico exactamente en las filas suprimidas, y se conservan ambas presentaciones sin mezclarlas.

Estructura observada (auditada el 2026-09-04)
---------------------------------------------
* sep=';', codificación ISO-8859-1 (latin-1), fin de línea CRLF, sin comillas salvo 2022 (glosas de intervención y
  procedimiento con comillas triples y ';' internos → 7.651 filas con 19–22 campos). El lector divide cada línea con
  `split(';', ncore)` y conserva solo las columnas núcleo (hasta CONDICION_EGRESO), lo que es robusto a esos campos.
* 2019 y 2023 escriben `PERTENENCIA_ESTABLECIMIENTO_SALU` (sin D). 2024 no trae ETNIA y codifica SEXO como 1/2
  (1 = hombre, 2 = mujer; comprobado con los códigos obstétricos O00–O99, que solo aparecen en el código 2).
* ANO_EGRESO vale `*` en las filas enmascaradas de 2019–2023.

Controles: no hay totales oficiales preespecificados. Se comprueban filas leídas frente a líneas del archivo, SHA-256
frente al manifiesto canónico, F84 en DIAG2 = 0, una precomprobación independiente con awk (F84 en DIAG1 y filas con
campos extra), categorías sin mapear = 0 y sumas internas.

Ejecución: `python3 study/pipeline/01b_deis_egresos.py [--years 2019 2024] [--no-sha]`
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402
import config as CFG  # noqa: E402

MODULE = "01b_deis_egresos"
# config.CONTROLS es el diccionario de valores esperados (sombrea la ruta homónima); la carpeta se define aquí.
CONTROLS_DIR = CFG.OUT / "controls"
DEIS_DIR = CFG.PATHS["deis_egresos"]
MANIFEST = DEIS_DIR / "metadata" / "canonical_manifest.csv"
DICTIONARY = DEIS_DIR / "metadata" / "Diccionario BD egresos hospitalario.xlsx"
VARIANT_2021 = DEIS_DIR / "variants" / "detailed_age_15col" / "2021.csv"
YEARS = list(CFG.YEARS_GRD)
VARIANTS = list(CFG.VARIANTS)

# Precomprobación independiente (awk -F';' sobre los archivos canónicos, 2026-09-04). Sirve como control interno de la
# implementación pandas, no como total oficial.
AWK_F84_DIAG1 = {2019: 336, 2020: 267, 2021: 309, 2022: 480, 2023: 600, 2024: 690}
AWK_ROWS = {2019: 1_667_180, 2020: 1_330_477, 2021: 1_467_062, 2022: 1_597_118, 2023: 1_612_267, 2024: 1_667_349}
AWK_EXTRA_FIELD_ROWS = {2019: 0, 2020: 0, 2021: 0, 2022: 7_651, 2023: 0, 2024: 0}

# ---------------------------------------------------------------------------
# Diccionarios de armonización (claves normalizadas: sin acentos, mayúsculas, espacios simples)
# ---------------------------------------------------------------------------
SEX_MAP = {"HOMBRE": "HOMBRE", "MUJER": "MUJER", "1": "HOMBRE", "2": "MUJER",
           "INTERSEX (INDETERMINDADO)": "INTERSEX", "3": "INTERSEX", "9": "DESCONOCIDO", "*": "SUPRIMIDO"}
PERTENENCIA_MAP = {"PERTENECIENTES AL SISTEMA NACIONAL DE SERVICIOS DE SALUD, SNSS": "SNSS",
                   "NO PERTENECIENTES AL SISTEMA NACIONAL DE SERVICIOS DE SALUD, SNSS": "NO_SNSS", "*": "SUPRIMIDO"}
PREVISION_MAP = {"FONASA": "FONASA", "ISAPRE": "ISAPRE", "CAPREDENA": "CAPREDENA", "DIPRECA": "DIPRECA", "SISA": "SISA",
                 "NINGUNA": "NINGUNA", "DESCONOCIDO": "DESCONOCIDO", "*": "SUPRIMIDO"}
AGE_BANDS_10 = ["<1", "1-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
# Esquema decenal (2019–2023): etiqueta cruda → banda decenal armonizada. 80 a 89 y 90 y más se funden en 80+ para
# que la banda sea comparable con el esquema quinquenal (80 a 84, 85 a más).
AGE_DECADAL = {"MENOR DE UN ANO": "<1", "1 A 9": "1-9", "10 A 19": "10-19", "20 A 29": "20-29", "30 A 39": "30-39",
               "40 A 49": "40-49", "50 A 59": "50-59", "60 A 69": "60-69", "70 A 79": "70-79", "80 A 89": "80+",
               "90 Y MAS": "80+", "*": "SUPRIMIDO"}
# Esquema quinquenal (2024 canónico y variante 2021): etiqueta cruda → (banda decenal, grupo OMS de 5 años).
AGE_FIVE = {"MENOR A 7 DIAS": ("<1", "0-4"), "7 A 27 DIAS": ("<1", "0-4"), "28 DIAS A 2 MES": ("<1", "0-4"),
            "2 MESES A MENOS DE 1 ANO": ("<1", "0-4"), "1 A 4 ANOS": ("1-9", "0-4"), "5 A 9 ANOS": ("1-9", "5-9"),
            "80 A 84 ANOS": ("80+", "80+"), "85 A MAS": ("80+", "80+"), "*": ("SUPRIMIDO", "SUPRIMIDO")}
for _lo in range(10, 80, 5):
    AGE_FIVE[f"{_lo} A {_lo + 4} ANOS"] = (f"{_lo // 10 * 10}-{_lo // 10 * 10 + 9}", f"{_lo}-{_lo + 4}")
WHO_ORDER = C.AGE_GROUPS + ["SUPRIMIDO"]
SEX_ORDER = ["HOMBRE", "MUJER", "INTERSEX", "DESCONOCIDO", "SUPRIMIDO", "TOTAL"]

COLUMN_NOTES = {
    "PERTENENCIA_ESTABLECIMIENTO_SALUD": "Pertenencia del establecimiento al SNSS (única variable de establecimiento; no hay código). 2019 y 2023 la escriben sin la D final.",
    "SEXO": "Texto HOMBRE/MUJER (2019–2023; 2022 añade INTERSEX (INDETERMINDADO)); código 1/2 en 2024 y en la variante 2021 (1 = hombre, 2 = mujer, 3 = intersex, 9 = desconocido).",
    "GRUPO_EDAD": "Grupo de edad al ingreso: decenal (menor de un año, 1 a 9, …, 90 y más) en 2019–2023; quinquenal con subdivisión neonatal (menor a 7 días … 85 a más) en 2024 y en la variante 2021.",
    "ETNIA": "Autoidentificación étnica; ausente en 2024.",
    "GLOSA_PAIS_ORIGEN": "Chileno/extranjero o país.",
    "COMUNA_RESIDENCIA": "Código DEIS de comuna de residencia (5 dígitos con cero inicial); enmascarada (*) en 2023–2024 para las filas suprimidas.",
    "GLOSA_COMUNA_RESIDENCIA": "Nombre de la comuna de residencia.",
    "REGION_RESIDENCIA": "Código de región de residencia (2 dígitos).",
    "GLOSA_REGION_RESIDENCIA": "Nombre de la región de residencia.",
    "PREVISION": "Código de previsión: 1 FONASA, 2 ISAPRE, 3 CAPREDENA, 4 DIPRECA, 5 SISA, 96 NINGUNA, 99 DESCONOCIDO.",
    "GLOSA_PREVISION": "Glosa de previsión.",
    "ANO_EGRESO": "Año del egreso; vale * en las filas enmascaradas de 2019–2023.",
    "DIAG1": "CIE-10 del diagnóstico principal (4 caracteres sin punto; unos pocos códigos en minúscula en 2021–2022).",
    "DIAG2": "CIE-10 de la CAUSA EXTERNA (V/W/X/Y) — no es un diagnóstico secundario; vacío cuando no aplica.",
    "DIAS_ESTADA": "Días de estada.",
    "CONDICION_EGRESO": "1 = vivo, 2 = fallecido.",
    "INTERV_Q": "Indicador de intervención quirúrgica (solo 2019–2021).",
    "PROCED": "Indicador de procedimiento (solo 2019–2021).",
    "GLOSA_INTERV_Q_PPAL": "Glosa de la intervención quirúrgica principal (solo 2022; texto libre con ';' y comillas).",
    "GLOSA_PROCED_PPAL": "Glosa del procedimiento principal (solo 2022; texto libre).",
}


def norm_label(value) -> str:
    text = "" if value is None else str(value)
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().upper()


# ---------------------------------------------------------------------------
# Integridad binaria y lectura
# ---------------------------------------------------------------------------
def file_integrity(path: Path, compute_sha: bool = True) -> dict:
    """Un solo paso binario: SHA-256, líneas (\\n), retornos (\\r), comillas y bytes altos (para confirmar latin-1)."""
    h = hashlib.sha256()
    n_lf = n_cr = n_quote = size = utf8_pairs = 0
    high = np.zeros(256, dtype=np.int64)
    tail = b""
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 24):
            size += len(chunk)
            if compute_sha:
                h.update(chunk)
            n_lf += chunk.count(b"\n")
            n_cr += chunk.count(b"\r")
            n_quote += chunk.count(b'"')
            arr = np.frombuffer(chunk, dtype=np.uint8)
            high += np.bincount(arr, minlength=256)
            # Pares (byte inicial UTF-8 0xC2–0xF4, byte de continuación 0x80–0xBF): en texto latin-1 son ~0 porque tras
            # Ñ/á/é/í/ó/ú/ñ sigue casi siempre un byte ASCII. Se incluye el último byte del trozo anterior.
            arr2 = np.frombuffer(tail + chunk, dtype=np.uint8) if tail else arr
            lead = (arr2[:-1] >= 0xC2) & (arr2[:-1] <= 0xF4)
            cont = (arr2[1:] >= 0x80) & (arr2[1:] <= 0xBF)
            utf8_pairs += int(np.count_nonzero(lead & cont))
            tail = chunk[-1:]
    hi = {f"0x{b:02x}": int(high[b]) for b in range(128, 256) if high[b]}
    return dict(size_bytes=size, sha256=h.hexdigest() if compute_sha else "", newlines=n_lf, carriage_returns=n_cr,
                quotes=n_quote, high_bytes=hi, utf8_multibyte_pairs=utf8_pairs)


def iter_deis(path: Path, chunksize: int = 500_000):
    """Lee un archivo DEIS por líneas (latin-1, sep ';', sin tratamiento de comillas) y devuelve trozos con las columnas
    núcleo (hasta CONDICION_EGRESO). Las columnas posteriores (INTERV_Q, PROCED, glosas 2022) se descartan; en 2022
    contienen ';' y comillas, por lo que el corte por posición es la única lectura fiel a la estructura publicada."""
    with open(path, encoding="latin-1", newline="") as fh:
        header = fh.readline().rstrip("\r\n").split(";")
        nfull = len(header)
        ncore = header.index("CONDICION_EGRESO") + 1
        cols = header[:ncore]
        stats = dict(rows=0, extra_fields=0, short_rows=0, n_columns_file=nfull, n_columns_core=ncore, header=header)
        buf = []
        for line in fh:
            body = line.rstrip("\r\n")
            if body.count(";") + 1 > nfull:
                stats["extra_fields"] += 1
            parts = body.split(";", ncore)[:ncore]
            if len(parts) < ncore:
                stats["short_rows"] += 1
                parts = parts + [""] * (ncore - len(parts))
            buf.append(parts)
            if len(buf) >= chunksize:
                stats["rows"] += len(buf)
                yield pd.DataFrame(buf, columns=cols), stats
                buf = []
        if buf:
            stats["rows"] += len(buf)
            yield pd.DataFrame(buf, columns=cols), stats


CELL_KEYS = ["pertenencia_raw", "sexo_raw", "age_group_raw", "prevision_raw", "f84_diag1_code", "f84_diag2_code",
             "condicion_egreso", "ano_egreso_raw"]


def cell_counts(path: Path) -> tuple[pd.DataFrame, dict]:
    """Agrega el microdato a celdas (valores crudos) sin dejar ningún registro individual en memoria de salida."""
    parts = []
    stats = {}
    for chunk, stats in iter_deis(path):
        d = pd.DataFrame({
            "pertenencia_raw": chunk.iloc[:, 0].str.strip(),
            "sexo_raw": chunk["SEXO"].str.strip(),
            "age_group_raw": chunk["GRUPO_EDAD"].str.strip(),
            "prevision_raw": chunk["GLOSA_PREVISION"].str.strip(),
            "condicion_egreso": chunk["CONDICION_EGRESO"].str.strip(),
            "ano_egreso_raw": chunk["ANO_EGRESO"].str.strip(),
        })
        d1 = chunk["DIAG1"].map(C.normalize_code)
        d2 = chunk["DIAG2"].map(C.normalize_code)
        d["f84_diag1_code"] = d1.where(d1.str.startswith("F84"), "")
        d["f84_diag2_code"] = d2.where(d2.str.startswith("F84"), "")
        parts.append(d.groupby(CELL_KEYS, dropna=False).size().rename("discharges").reset_index())
    cells = pd.concat(parts).groupby(CELL_KEYS, dropna=False)["discharges"].sum().reset_index()
    return cells, stats


def harmonise(cells: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica los diccionarios de armonización y devuelve las categorías sin mapear por variable."""
    out = cells.copy()
    unmapped = {}
    out["pertenencia"] = out.pertenencia_raw.map(norm_label).map(PERTENENCIA_MAP)
    out["sex"] = out.sexo_raw.map(norm_label).map(SEX_MAP)
    out["prevision"] = out.prevision_raw.map(norm_label).map(PREVISION_MAP)
    labels = set(out.age_group_raw.map(norm_label))
    if labels <= set(AGE_FIVE):
        scheme = "five_year"
        out["age_band_10"] = out.age_group_raw.map(norm_label).map(lambda k: AGE_FIVE[k][0])
        out["age_group_who"] = out.age_group_raw.map(norm_label).map(lambda k: AGE_FIVE[k][1])
    elif labels <= set(AGE_DECADAL):
        scheme = "decadal"
        out["age_band_10"] = out.age_group_raw.map(norm_label).map(AGE_DECADAL)
        out["age_group_who"] = ""  # no derivable: los grupos decenales no se subdividen
    else:
        scheme = "unknown"
        out["age_band_10"] = out.age_group_raw.map(norm_label).map({**AGE_DECADAL, **{k: v[0] for k, v in AGE_FIVE.items()}})
        out["age_group_who"] = ""
        unmapped["GRUPO_EDAD"] = sorted(labels - set(AGE_DECADAL) - set(AGE_FIVE))
    for col, raw in [("pertenencia", "pertenencia_raw"), ("sex", "sexo_raw"), ("prevision", "prevision_raw")]:
        bad = out.loc[out[col].isna(), raw].unique().tolist()
        if bad:
            unmapped[raw] = bad
    out["age_scheme"] = scheme
    return out, unmapped


def f84_flag(codes: pd.Series, variant: str) -> pd.Series:
    """F84 según variante: con_rett = cualquier F84.x; sin_rett = F84.x excepto F84.2 (config.RETT_GRD)."""
    is_f84 = codes.str.startswith("F84")
    if variant == "sin_rett":
        is_f84 &= ~codes.str.startswith(tuple(CFG.RETT_GRD))
    return is_f84


def rate_cols(count: pd.Series, denom: pd.Series, per: float = 1e5) -> pd.DataFrame:
    r = C.crude_rate(count.to_numpy(), denom.to_numpy(), per=per)
    r.columns = ["rate_per_100k_discharges", "rate_lo95", "rate_hi95"]
    return r.set_index(count.index)


# ---------------------------------------------------------------------------
# Tablas derivadas
# ---------------------------------------------------------------------------
def summarise_by(cells: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Conteos por claves y variante: egresos totales, F84 principal (DIAG1), F84 en DIAG2, F84 en cualquiera, ambas."""
    rows = []
    for v in VARIANTS:
        d = cells.assign(_a=f84_flag(cells.f84_diag1_code, v), _b=f84_flag(cells.f84_diag2_code, v))
        d["_f84_diag1"] = d.discharges.where(d._a, 0)
        d["_f84_diag2"] = d.discharges.where(d._b, 0)
        d["_f84_any"] = d.discharges.where(d._a | d._b, 0)
        d["_f84_both"] = d.discharges.where(d._a & d._b, 0)
        d["_f84_deaths"] = d.discharges.where(d._a & (d.condicion_egreso == "2"), 0)
        g = d.groupby(keys, dropna=False).agg(discharges_total=("discharges", "sum"), f84_diag1=("_f84_diag1", "sum"),
                                              f84_diag2=("_f84_diag2", "sum"), f84_any=("_f84_any", "sum"),
                                              f84_both_positions=("_f84_both", "sum"), f84_deaths=("_f84_deaths", "sum")).reset_index()
        g.insert(len(keys), "variant", v)
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    out = pd.concat([out, rate_cols(out.f84_any, out.discharges_total)], axis=1)
    return out


def add_marginals(cells: pd.DataFrame, base_keys: list[str], dims: list[str]) -> pd.DataFrame:
    """Cruce completo más marginales por cada dimensión y total; `level` indica el nivel de agregación."""
    frames = []
    full = summarise_by(cells, base_keys + dims)
    full["level"] = "x".join(dims)
    frames.append(full)
    for dim in dims:
        others = [d for d in dims if d != dim]
        m = summarise_by(cells, base_keys + others)
        m[dim] = "TOTAL"
        m["level"] = "x".join(others) if others else "total"
        frames.append(m)
    t = summarise_by(cells, base_keys)
    for dim in dims:
        t[dim] = "TOTAL"
    t["level"] = "total"
    frames.append(t)
    return pd.concat(frames, ignore_index=True)


def f84_labels() -> dict:
    """Glosas oficiales F84.x del diccionario DEIS (hoja 'codigo CIE-10')."""
    try:
        raw = pd.read_excel(DICTIONARY, sheet_name="codigo CIE-10", header=None)
        hdr_idx = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("CODIGO SUBCATEGORIA")][0]
        tab = raw.iloc[hdr_idx + 1:, :2]
        tab.columns = ["code", "label"]
        tab["code"] = tab.code.map(C.normalize_code)
        return tab.loc[tab.code.str.startswith("F84")].drop_duplicates("code").set_index("code")["label"].to_dict()
    except Exception as exc:  # pragma: no cover — el diccionario es auxiliar
        print(f"[{MODULE}] aviso: no se pudo leer el diccionario CIE-10 ({exc})")
        return {}


GRD_REQUIRED = {"year", "variant", "panel", "activity", "position", "n_episodes_f84", "n_episodes_total_same_panel_activity", "hospitals_n"}
COMPARISON_DEFINITIONS = ["con_rett", "sin_rett", "strict_autism_f840"]
DEFINITION_LABEL = {"con_rett": CFG.VARIANTS["con_rett"]["label"]["es"], "sin_rett": CFG.VARIANTS["sin_rett"]["label"]["es"],
                    "strict_autism_f840": "solo F84.0 (autismo en la niñez); serie estricta idéntica en ambas variantes"}


def load_grd_summary() -> tuple[pd.DataFrame | None, str]:
    """Lee outputs/tidy/grd_year_summary.csv del módulo 01 (formato largo: año × variante × panel × actividad × posición).
    Si falta o su esquema no es el esperado, la comparación usa los valores esperados de config.CONTROLS (solo con_rett)."""
    path = CFG.TIDY / "grd_year_summary.csv"
    if not path.is_file():
        return None, "config.CONTROLS (valores esperados del brief; outputs/tidy/grd_year_summary.csv no existe aún)"
    g = pd.read_csv(path)
    missing = GRD_REQUIRED - set(g.columns)
    if missing:
        return None, f"config.CONTROLS (grd_year_summary.csv existe pero le faltan columnas {sorted(missing)})"
    return g, "outputs/tidy/grd_year_summary.csv (módulo 01_grd_core)"


def grd_value(g: pd.DataFrame, year: int, variant: str, panel: str, activity: str, position: str, col: str) -> float:
    sub = g.loc[(g.year == year) & (g.variant == variant) & (g.panel == panel) & (g.activity == activity) & (g.position == position), col]
    return float(sub.iloc[0]) if len(sub) else np.nan


def deis_definition_flag(codes: pd.Series, definition: str) -> pd.Series:
    """con_rett / sin_rett según config; strict_autism_f840 = solo F84.0 (análogo DEIS de la serie estricta del módulo 01)."""
    if definition == "strict_autism_f840":
        return codes.str.startswith("F840")
    return f84_flag(codes, definition)


def build_grd_comparison(cells: pd.DataFrame) -> pd.DataFrame:
    """Tabla anual DEIS frente a GRD. Serie homologable: F84 principal (DIAG1 en DEIS; DIAGNOSTICO1 en GRD). Se añaden
    el panel fijo de 65 y la hospitalización estricta del GRD porque DEIS solo contiene egresos de hospitalización."""
    grd, grd_source = load_grd_summary()
    canon = cells.loc[cells.source_layout == "canonical"]
    grd_cols = ["grd_records_total", "grd_f84_any", "grd_f84_principal", "grd_f84_secondary_only", "grd_hospitals_observed",
                "grd_records_total_fixed65", "grd_f84_any_fixed65", "grd_f84_principal_fixed65",
                "grd_records_hospitalisation", "grd_f84_any_hospitalisation", "grd_f84_principal_hospitalisation",
                "grd_records_hospitalisation_fixed65", "grd_f84_any_hospitalisation_fixed65", "grd_f84_principal_hospitalisation_fixed65"]
    rows = []
    for y in sorted(canon.year.unique()):
        cy = canon.loc[canon.year == y]
        total = int(cy.discharges.sum())
        snss_total = int(cy.loc[cy.pertenencia == "SNSS", "discharges"].sum())
        for d in COMPARISON_DEFINITIONS:
            f = cy.discharges.where(deis_definition_flag(cy.f84_diag1_code, d), 0)
            n = int(f.sum())
            rate = C.crude_rate([n], [total]).iloc[0]
            rec = dict(year=int(y), variant=d, variant_definition=DEFINITION_LABEL[d], deis_discharges_total=total, deis_discharges_snss=snss_total,
                       deis_f84_principal=n, deis_f84_principal_snss=int(f[cy.pertenencia == "SNSS"].sum()),
                       deis_f84_principal_no_snss=int(f[cy.pertenencia == "NO_SNSS"].sum()), deis_f84_principal_suppressed=int(f[cy.pertenencia == "SUPRIMIDO"].sum()),
                       deis_rate_f84_principal_per_100k_discharges=float(rate.rate), deis_rate_lo95=float(rate.rate_lo), deis_rate_hi95=float(rate.rate_hi))
            rec.update({c: np.nan for c in grd_cols})
            if grd is not None and ((grd.year == y) & (grd.variant == d)).any():
                spec = {"grd_records_total": ("observed", "all", "any", "n_episodes_total_same_panel_activity"),
                        "grd_f84_any": ("observed", "all", "any", "n_episodes_f84"),
                        "grd_f84_principal": ("observed", "all", "principal", "n_episodes_f84"),
                        "grd_f84_secondary_only": ("observed", "all", "secondary_only", "n_episodes_f84"),
                        "grd_hospitals_observed": ("observed", "all", "any", "hospitals_n"),
                        "grd_records_total_fixed65": ("fixed65", "all", "any", "n_episodes_total_same_panel_activity"),
                        "grd_f84_any_fixed65": ("fixed65", "all", "any", "n_episodes_f84"),
                        "grd_f84_principal_fixed65": ("fixed65", "all", "principal", "n_episodes_f84"),
                        "grd_records_hospitalisation": ("observed", "hospitalisation", "any", "n_episodes_total_same_panel_activity"),
                        "grd_f84_any_hospitalisation": ("observed", "hospitalisation", "any", "n_episodes_f84"),
                        "grd_f84_principal_hospitalisation": ("observed", "hospitalisation", "principal", "n_episodes_f84"),
                        "grd_records_hospitalisation_fixed65": ("fixed65", "hospitalisation", "any", "n_episodes_total_same_panel_activity"),
                        "grd_f84_any_hospitalisation_fixed65": ("fixed65", "hospitalisation", "any", "n_episodes_f84"),
                        "grd_f84_principal_hospitalisation_fixed65": ("fixed65", "hospitalisation", "principal", "n_episodes_f84")}
                rec.update({c: grd_value(grd, y, d, *args) for c, args in spec.items()})
                rec["grd_source"] = grd_source
            elif d == "con_rett":
                rec.update(grd_records_total=CFG.CONTROLS["grd_records_total"].get(y, np.nan), grd_f84_any=CFG.CONTROLS["grd_f84_any"].get(y, np.nan),
                           grd_f84_principal=CFG.CONTROLS["grd_f84_principal"].get(y, np.nan), grd_hospitals_observed=CFG.CONTROLS["grd_hospitals_observed"].get(y, np.nan),
                           grd_f84_any_fixed65=CFG.CONTROLS["grd_f84_any_panel65"].get(y, np.nan),
                           grd_f84_any_hospitalisation_fixed65=CFG.CONTROLS["grd_f84_any_strict_hospitalisation"].get(y, np.nan),
                           grd_source="config.CONTROLS (valores esperados del brief; sin archivo del módulo 01)")
            else:
                rec["grd_source"] = f"sin valores GRD para {d}: grd_year_summary.csv no disponible o sin esa variante"
            rows.append(rec)
    out = pd.DataFrame(rows)
    out["grd_rate_f84_any_per_100k_episodes"] = 1e5 * out.grd_f84_any / out.grd_records_total
    out["grd_rate_f84_principal_per_100k_episodes"] = 1e5 * out.grd_f84_principal / out.grd_records_total
    out["grd_rate_f84_principal_hospitalisation_per_100k_episodes"] = 1e5 * out.grd_f84_principal_hospitalisation / out.grd_records_hospitalisation
    out["ratio_deis_total_to_grd_total"] = out.deis_discharges_total / out.grd_records_total
    out["ratio_deis_f84_principal_to_grd_f84_principal"] = out.deis_f84_principal / out.grd_f84_principal
    out["ratio_deis_f84_principal_snss_to_grd_f84_principal"] = out.deis_f84_principal_snss / out.grd_f84_principal
    out["ratio_deis_f84_principal_snss_to_grd_f84_principal_hospitalisation"] = out.deis_f84_principal_snss / out.grd_f84_principal_hospitalisation
    out["ratio_grd_f84_any_to_deis_f84_principal"] = out.grd_f84_any / out.deis_f84_principal
    out["unit_deis"] = "egreso hospitalario DEIS (todos los establecimientos; DIAG1 principal, DIAG2 causa externa)"
    out["unit_grd"] = "episodio GRD público (hospitales SNSS con GRD; 35 posiciones diagnósticas; 'all' incluye CMA y otras modalidades)"
    out["comparability_note"] = ("Comparación de cobertura entre registros no enlazados por persona ni episodio. La única serie "
                                 "homologable es F84 principal en ambas fuentes; GRD F84 en cualquier posición no tiene equivalente "
                                 "en DEIS porque DEIS no publica diagnósticos secundarios. Los cocientes no son probabilidades.")
    return out


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------
class Controls:
    def __init__(self):
        self.rows = []

    def add(self, name, key, expected, observed, note="", tol_rel=0.0):
        if isinstance(expected, str) or isinstance(observed, str):
            status = "ok" if str(expected) == str(observed) else "differs"
            self.rows.append(dict(name=name, key=key, expected=expected, observed=observed, abs_diff=np.nan, rel_diff=np.nan, status=status, note=note))
            return
        exp = np.nan if expected is None else float(expected)
        obs = np.nan if observed is None else float(observed)
        abs_diff = obs - exp if not (np.isnan(exp) or np.isnan(obs)) else np.nan
        rel_diff = abs_diff / exp if (not np.isnan(abs_diff) and exp != 0) else (0.0 if abs_diff == 0 else np.nan)
        if np.isnan(abs_diff):
            status = "differs"
        elif abs_diff == 0 or (tol_rel and abs(rel_diff) <= tol_rel):
            status = "ok"
        else:
            status = "differs"
        self.rows.append(dict(name=name, key=key, expected=expected, observed=observed, abs_diff=abs_diff, rel_diff=rel_diff, status=status, note=note))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"])


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--years", nargs="*", type=int, default=YEARS)
    ap.add_argument("--no-sha", action="store_true", help="omite el SHA-256 (solo cuenta líneas)")
    ap.add_argument("--skip-variant", action="store_true", help="omite la variante 2021 de 15 columnas")
    args = ap.parse_args(argv)
    t0 = time.perf_counter()
    ctl = Controls()
    manifest = pd.read_csv(MANIFEST, dtype=str).set_index("year") if MANIFEST.is_file() else None

    files = [(y, DEIS_DIR / f"{y}.csv", "canonical") for y in args.years]
    if not args.skip_variant and VARIANT_2021.is_file() and 2021 in args.years:
        files.append((2021, VARIANT_2021, "variant_detailed_age_15col"))

    all_cells, inventory, year_rows, integrity_rows = [], [], [], []
    for year, path, layout in files:
        if not path.is_file():
            print(f"[{MODULE}] falta {path}; se omite")
            continue
        t1 = time.perf_counter()
        integ = file_integrity(path, compute_sha=not args.no_sha)
        cells, stats = cell_counts(path)
        cells, unmapped = harmonise(cells)
        cells.insert(0, "year", year)
        cells.insert(1, "source_layout", layout)
        cells["source_file"] = str(path.relative_to(DEIS_DIR))
        all_cells.append(cells)
        n_rows = int(cells.discharges.sum())
        rel = str(path.relative_to(DEIS_DIR))
        key = f"{year}|{layout}"
        print(f"[{MODULE}] {rel}: {n_rows:,} egresos, {stats['n_columns_file']} columnas ({stats['n_columns_core']} núcleo), "
              f"campos extra {stats['extra_fields']:,}, F84 DIAG1 {int(cells.loc[cells.f84_diag1_code != '', 'discharges'].sum()):,}, "
              f"{time.perf_counter() - t1:.1f} s")

        # Inventario de columnas
        for pos, col in enumerate(stats["header"], start=1):
            std = "PERTENENCIA_ESTABLECIMIENTO_SALUD" if col.startswith("PERTENENCIA_ESTABLECIMIENTO") else col
            inventory.append(dict(year=year, source_layout=layout, source_file=rel, position=pos, column_name=col, column_std=std,
                                  core=pos <= stats["n_columns_core"], note=COLUMN_NOTES.get(std, "")))
        integrity_rows.append(dict(year=year, source_layout=layout, source_file=rel, **{k: v for k, v in integ.items() if k != "high_bytes"},
                                   high_bytes=str(integ["high_bytes"]), rows_read=n_rows, extra_field_rows=stats["extra_fields"],
                                   short_rows=stats["short_rows"], n_columns_file=stats["n_columns_file"], n_columns_core=stats["n_columns_core"],
                                   encoding="ISO-8859-1", delimiter=";", line_terminator="CRLF" if integ["carriage_returns"] == integ["newlines"] else "mixed",
                                   age_scheme=cells.age_scheme.iloc[0]))

        # Controles de integridad
        ctl.add("deis_rows_vs_file_lines", key, integ["newlines"] - 1, n_rows, "filas leídas frente a saltos de línea menos cabecera")
        ctl.add("deis_rows_vs_awk_precheck", key, AWK_ROWS.get(year) if layout == "canonical" else AWK_ROWS.get(year), n_rows, "precomprobación awk 2026-09-04")
        ctl.add("deis_short_rows", key, 0, stats["short_rows"], "filas con menos campos que las columnas núcleo")
        ctl.add("deis_extra_field_rows", key, AWK_EXTRA_FIELD_ROWS.get(year, 0) if layout == "canonical" else 0, stats["extra_fields"],
                "filas con más campos que la cabecera (2022: glosas con ';'); se conservan porque el corte es por posición")
        ctl.add("deis_crlf_consistent", key, integ["newlines"], integ["carriage_returns"], "un \\r por cada \\n")
        ctl.add("deis_latin1_no_utf8_sequences", key, 0, integ["utf8_multibyte_pairs"],
                "pares byte inicial UTF-8 + byte de continuación; 0 confirma ISO-8859-1 (los bytes altos observados son Ñ/á/é/í/ó/ú/ñ)")
        if manifest is not None and layout == "canonical" and not args.no_sha:
            ctl.add("deis_sha256_vs_manifest", key, manifest.loc[str(year), "sha256"], integ["sha256"], "metadata/canonical_manifest.csv")
        f84_d1 = int(cells.loc[cells.f84_diag1_code != "", "discharges"].sum())
        f84_d2 = int(cells.loc[cells.f84_diag2_code != "", "discharges"].sum())
        ctl.add("deis_f84_diag1_vs_awk_precheck", key, AWK_F84_DIAG1.get(year), f84_d1, "precomprobación awk 2026-09-04 (variante 2021 debe igualar al canónico)")
        ctl.add("deis_f84_diag2_zero", key, 0, f84_d2, "DIAG2 es causa externa (V/W/X/Y); F84 no puede aparecer")
        for var, bad in unmapped.items():
            ctl.add("deis_unmapped_categories", f"{key}|{var}", 0, len(bad), f"valores sin mapear: {bad}")
        if not unmapped:
            ctl.add("deis_unmapped_categories", key, 0, 0, "SEXO, GRUPO_EDAD, PERTENENCIA y PREVISION mapean por completo")
        bad_year = int(cells.loc[~cells.ano_egreso_raw.isin([str(year), "*"]), "discharges"].sum())
        ctl.add("deis_ano_egreso_consistent", key, 0, bad_year, "ANO_EGRESO distinto del año del archivo y de *")
        ctl.add("deis_condicion_egreso_domain", key, 0, int(cells.loc[~cells.condicion_egreso.isin(["1", "2"]), "discharges"].sum()), "valores fuera de {1,2}")
        ctl.add("deis_age_scheme", key, "five_year" if stats["n_columns_core"] == 15 else "decadal", cells.age_scheme.iloc[0],
                "15 columnas núcleo ⇒ grupos quinquenales; 16 ⇒ decenales")

    if not all_cells:
        print(f"[{MODULE}] no se leyó ningún archivo")
        return 1
    cells = pd.concat(all_cells, ignore_index=True)
    cells["f84_rett_f842"] = cells.f84_diag1_code.str.startswith("F842")

    # ---- Tabla de celdas (base trazable de todas las demás) --------------------------------------
    cell_out = cells[["year", "source_layout", "source_file", "pertenencia", "sex", "age_scheme", "age_group_raw", "age_band_10",
                      "age_group_who", "prevision", "f84_diag1_code", "f84_diag2_code", "condicion_egreso", "ano_egreso_raw", "discharges"]].copy()
    cell_out["unit"] = "egresos (registros DEIS)"
    C.atomic_write_csv(cell_out.sort_values(["year", "source_layout", "pertenencia", "sex", "age_group_raw", "prevision", "f84_diag1_code"]),
                       CFG.TIDY / "deis_cell_counts.csv")

    # ---- Resumen anual ------------------------------------------------------------------------------
    summ = summarise_by(cells, ["year", "source_layout"])
    summ["f84_principal_only"] = summ.f84_diag1 - summ.f84_both_positions
    summ["f84_secondary_only"] = summ.f84_diag2 - summ.f84_both_positions
    summ["f84_principal_share"] = summ.f84_diag1 / summ.f84_any
    summ["f84_secondary_only_share"] = summ.f84_secondary_only / summ.f84_any
    rett = cells.loc[cells.f84_rett_f842].groupby(["year", "source_layout"]).discharges.sum().rename("f84_rett_f842_diag1")
    summ = summ.merge(rett.reset_index(), on=["year", "source_layout"], how="left").fillna({"f84_rett_f842_diag1": 0})
    by_pert = summarise_by(cells, ["year", "source_layout", "pertenencia"])
    for cat, suffix in [("SNSS", "snss"), ("NO_SNSS", "no_snss"), ("SUPRIMIDO", "suppressed")]:
        sub = by_pert.loc[by_pert.pertenencia == cat, ["year", "source_layout", "variant", "discharges_total", "f84_any"]]
        sub = sub.rename(columns={"discharges_total": f"discharges_{suffix}", "f84_any": f"f84_any_{suffix}"})
        summ = summ.merge(sub, on=["year", "source_layout", "variant"], how="left")
        # La tabla de celdas es exhaustiva por archivo: una categoría ausente es un cero verdadero (p. ej. la variante 2021
        # no trae filas enmascaradas), no un dato faltante.
        summ[[f"discharges_{suffix}", f"f84_any_{suffix}"]] = summ[[f"discharges_{suffix}", f"f84_any_{suffix}"]].fillna(0).astype(int)
    summ["masked_rows_share"] = summ.discharges_suppressed / summ.discharges_total
    integ_df = pd.DataFrame(integrity_rows)
    summ = summ.merge(integ_df[["year", "source_layout", "source_file", "sha256", "size_bytes", "newlines", "n_columns_file", "n_columns_core", "age_scheme",
                                "extra_field_rows"]], on=["year", "source_layout"], how="left")
    summ["file_lines_minus_header"] = summ.newlines - 1
    summ["diagnosis_positions"] = 2
    summ["diag2_definition"] = "causa externa (CIE-10 V01–Y98), no diagnóstico secundario"
    summ["unit_count"] = "egresos hospitalarios (registros DEIS, todos los establecimientos)"
    summ["unit_rate"] = "por 100.000 egresos DEIS del mismo año y archivo; IC 95 % exacto de Poisson"
    summ["variant_definition"] = summ.variant.map({v: CFG.VARIANTS[v]["label"]["es"] for v in VARIANTS})
    summ = summ.drop(columns=["newlines"])
    order = ["year", "source_layout", "variant", "variant_definition", "discharges_total", "f84_diag1", "f84_diag2", "f84_any", "f84_both_positions",
             "f84_principal_only", "f84_secondary_only", "f84_principal_share", "f84_secondary_only_share", "f84_rett_f842_diag1", "f84_deaths",
             "rate_per_100k_discharges", "rate_lo95", "rate_hi95", "discharges_snss", "discharges_no_snss", "discharges_suppressed",
             "f84_any_snss", "f84_any_no_snss", "f84_any_suppressed", "masked_rows_share", "file_lines_minus_header", "extra_field_rows",
             "n_columns_file", "n_columns_core", "age_scheme", "diagnosis_positions", "diag2_definition", "unit_count", "unit_rate",
             "source_file", "sha256", "size_bytes"]
    summ = summ[order].sort_values(["source_layout", "year", "variant"], ascending=[False, True, True]).reset_index(drop=True)
    C.atomic_write_csv(summ, CFG.TIDY / "deis_year_summary.csv")

    # ---- Edad y sexo --------------------------------------------------------------------------------
    canon = cells.loc[cells.source_layout == "canonical"]
    age_sex = add_marginals(canon, ["year"], ["sex", "age_band_10"])
    age_sex["age_scheme_source"] = age_sex.year.map(canon.groupby("year").age_scheme.first())
    age_sex["source_layout"] = "canonical"
    age_sex["unit_count"] = "egresos (registros DEIS)"
    age_sex["unit_rate"] = "F84 en DIAG1 por 100.000 egresos del mismo estrato (año × sexo × banda de edad)"
    age_sex["age_band_definition"] = ("bandas decenales armonizadas a partir de los grupos publicados: <1, 1-9, …, 70-79, 80+ "
                                      "(80+ funde 80 a 89 y 90 y más en 2019–2023 y 80 a 84 y 85 a más en 2024)")
    age_sex["sex"] = pd.Categorical(age_sex.sex, SEX_ORDER)
    age_sex["age_band_10"] = pd.Categorical(age_sex.age_band_10, AGE_BANDS_10 + ["SUPRIMIDO", "TOTAL"])
    age_sex = age_sex.sort_values(["year", "variant", "level", "sex", "age_band_10"]).reset_index(drop=True)
    cols_as = ["year", "source_layout", "variant", "level", "sex", "age_band_10", "discharges_total", "f84_diag1", "f84_diag2", "f84_any",
               "f84_deaths", "rate_per_100k_discharges", "rate_lo95", "rate_hi95", "age_scheme_source", "age_band_definition", "unit_count", "unit_rate"]
    C.atomic_write_csv(age_sex[cols_as], CFG.TIDY / "deis_age_sex_year.csv")

    # Detalle con los grupos crudos (todas las capas; incluye grupo OMS cuando existe)
    detail = summarise_by(cells, ["year", "source_layout", "age_scheme", "sex", "age_group_raw", "age_band_10", "age_group_who"])
    detail["age_group_who"] = detail.age_group_who.replace("", "no derivable (esquema decenal)")
    detail["unit_count"] = "egresos (registros DEIS)"
    detail["unit_rate"] = "F84 en DIAG1 por 100.000 egresos del mismo estrato"
    C.atomic_write_csv(detail.sort_values(["year", "source_layout", "variant", "sex", "age_group_raw"]), CFG.TIDY / "deis_age_sex_year_detail.csv")

    # Grupos OMS quinquenales donde el esquema lo permite (2024 canónico y variante 2021)
    five = cells.loc[cells.age_scheme == "five_year"]
    if len(five):
        who = add_marginals(five, ["year", "source_layout"], ["sex", "age_group_who"])
        who["sex"] = pd.Categorical(who.sex, SEX_ORDER)
        who["age_group_who"] = pd.Categorical(who.age_group_who, WHO_ORDER + ["TOTAL"])
        who = who.sort_values(["year", "source_layout", "variant", "level", "sex", "age_group_who"]).reset_index(drop=True)
        who["unit_count"] = "egresos (registros DEIS)"
        who["unit_rate"] = "F84 en DIAG1 por 100.000 egresos del mismo estrato"
        who["age_group_definition"] = "grupos quinquenales OMS (0-4 … 75-79, 80+) derivados de los grupos publicados; 0-4 incluye las cuatro subdivisiones neonatales/infantiles y 1 a 4 años"
        cols_who = ["year", "source_layout", "variant", "level", "sex", "age_group_who", "discharges_total", "f84_diag1", "f84_any", "f84_deaths",
                    "rate_per_100k_discharges", "rate_lo95", "rate_hi95", "age_group_definition", "unit_count", "unit_rate"]
        C.atomic_write_csv(who[cols_who], CFG.TIDY / "deis_age_who_year.csv")

    # ---- Pertenencia SNSS y previsión ----------------------------------------------------------------
    est_frames = []
    for dim, label in [("pertenencia", "pertenencia_snss"), ("prevision", "prevision")]:
        e = summarise_by(canon, ["year", dim]).rename(columns={dim: "category"})
        e.insert(1, "dimension", label)
        tot = e.groupby(["year", "variant"])[["discharges_total", "f84_any"]].transform("sum")
        e["share_of_discharges"] = e.discharges_total / tot.discharges_total
        e["share_of_f84"] = e.f84_any / tot.f84_any
        est_frames.append(e)
    cross = summarise_by(canon, ["year", "pertenencia", "prevision"])
    cross["category"] = cross.pertenencia + "|" + cross.prevision
    cross.insert(1, "dimension", "pertenencia_snss_x_prevision")
    tot = cross.groupby(["year", "variant"])[["discharges_total", "f84_any"]].transform("sum")
    cross["share_of_discharges"] = cross.discharges_total / tot.discharges_total
    cross["share_of_f84"] = cross.f84_any / tot.f84_any
    est_frames.append(cross.drop(columns=["pertenencia", "prevision"]))
    est = pd.concat(est_frames, ignore_index=True)
    est["category_definition"] = est.dimension.map({
        "pertenencia_snss": "SNSS = establecimiento perteneciente al Sistema Nacional de Servicios de Salud (hospitales públicos); NO_SNSS = clínicas privadas, FF.AA. y de Orden, mutuales, administración delegada y otros; SUPRIMIDO = enmascarado (*) por DEIS",
        "prevision": "previsión de salud del paciente al ingreso (glosa DEIS); SUPRIMIDO = enmascarado (*)",
        "pertenencia_snss_x_prevision": "cruce pertenencia SNSS × previsión",
    })
    est["source_layout"] = "canonical"
    est["unit_count"] = "egresos (registros DEIS)"
    est["unit_rate"] = "F84 en DIAG1 por 100.000 egresos de la misma categoría y año"
    cols_est = ["year", "source_layout", "variant", "dimension", "category", "discharges_total", "f84_diag1", "f84_any", "f84_deaths",
                "share_of_discharges", "share_of_f84", "rate_per_100k_discharges", "rate_lo95", "rate_hi95", "category_definition", "unit_count", "unit_rate"]
    C.atomic_write_csv(est[cols_est].sort_values(["year", "variant", "dimension", "category"]), CFG.TIDY / "deis_establishment_year.csv")

    # ---- Subcódigos F84.x -------------------------------------------------------------------------------
    labels = f84_labels()
    sub = canon.loc[canon.f84_diag1_code != ""].groupby(["year", "f84_diag1_code"]).discharges.sum().rename("discharges_f84_diag1").reset_index()
    sub["share_of_f84_any_con_rett"] = sub.discharges_f84_diag1 / sub.groupby("year").discharges_f84_diag1.transform("sum")
    sub["icd10_label_deis"] = sub.f84_diag1_code.map(labels).fillna("")
    sub["in_variant_sin_rett"] = ~sub.f84_diag1_code.str.startswith(tuple(CFG.RETT_GRD))
    sub["unit"] = "egresos con el subcódigo en DIAG1 (registros DEIS)"
    C.atomic_write_csv(sub.sort_values(["year", "f84_diag1_code"]), CFG.TIDY / "deis_f84_subcode_year.csv")

    # ---- Comparación con GRD --------------------------------------------------------------------------------
    comp = build_grd_comparison(cells)
    C.atomic_write_csv(comp.sort_values(["variant", "year"]), CFG.TIDY / "deis_vs_grd_year.csv")

    # ---- Inventario e integridad ------------------------------------------------------------------------------
    C.atomic_write_csv(pd.DataFrame(inventory), CFG.TIDY / "deis_columns_inventory.csv")
    C.atomic_write_csv(integ_df, CFG.TIDY / "deis_file_integrity.csv")

    # ---- Controles de consistencia interna entre tablas ------------------------------------------------------
    for (y, v), r in summ.loc[summ.source_layout == "canonical"].set_index(["year", "variant"]).iterrows():
        a = age_sex.loc[(age_sex.year == y) & (age_sex.variant == v) & (age_sex.level == "sexxage_band_10")]
        ctl.add("deis_age_sex_sum_equals_total", f"{y}|{v}", r.discharges_total, int(a.discharges_total.sum()), "suma de celdas sexo × banda")
        ctl.add("deis_age_sex_f84_sum_equals_total", f"{y}|{v}", r.f84_any, int(a.f84_any.sum()))
        e = est.loc[(est.year == y) & (est.variant == v) & (est.dimension == "pertenencia_snss")]
        ctl.add("deis_pertenencia_sum_equals_total", f"{y}|{v}", r.discharges_total, int(e.discharges_total.sum()))
        ctl.add("deis_f84_any_equals_diag1", f"{y}|{v}", r.f84_diag1, r.f84_any, "en DEIS F84 solo puede estar en DIAG1")
    for y in sorted(summ.year.unique()):
        s = summ.loc[(summ.year == y) & (summ.source_layout == "canonical")].set_index("variant")
        if {"con_rett", "sin_rett"} <= set(s.index):
            ctl.add("deis_sin_rett_equals_con_rett_minus_f842", str(y), s.loc["con_rett", "f84_any"] - s.loc["con_rett", "f84_rett_f842_diag1"], s.loc["sin_rett", "f84_any"])
    v21 = summ.loc[(summ.year == 2021) & (summ.variant == "con_rett")].set_index("source_layout")
    if {"canonical", "variant_detailed_age_15col"} <= set(v21.index):
        ctl.add("deis_variant2021_rows_equal_canonical", "2021", v21.loc["canonical", "discharges_total"], v21.loc["variant_detailed_age_15col", "discharges_total"],
                "la variante de 15 columnas es otra presentación del mismo microdato")
        ctl.add("deis_variant2021_f84_equal_canonical", "2021", v21.loc["canonical", "f84_any"], v21.loc["variant_detailed_age_15col", "f84_any"])
        ctl.add("deis_variant2021_no_masked_rows", "2021", 0, v21.loc["variant_detailed_age_15col", "discharges_suppressed"],
                "la variante de 15 columnas no trae filas enmascaradas (*): es la presentación sin supresión del mismo microdato")
        ctl.add("deis_variant2021_snss_split_reconciles_masked", "2021", v21.loc["canonical", "discharges_suppressed"],
                (v21.loc["variant_detailed_age_15col", "discharges_snss"] - v21.loc["canonical", "discharges_snss"])
                + (v21.loc["variant_detailed_age_15col", "discharges_no_snss"] - v21.loc["canonical", "discharges_no_snss"]),
                "exceso SNSS + exceso no SNSS de la variante frente al canónico = filas suprimidas del canónico")
    for _, r in comp.loc[comp.variant == "con_rett"].iterrows():
        y = int(r.year)
        ctl.add("deis_vs_grd_join_source", str(y), "outputs/tidy/grd_year_summary.csv (módulo 01_grd_core)", r.grd_source,
                "origen de las columnas GRD de deis_vs_grd_year.csv; 'differs' significa que se usaron los valores esperados de config")
        if "grd_year_summary" in str(r.grd_source):
            for name, col in [("grd_records_total", "grd_records_total"), ("grd_f84_any", "grd_f84_any"), ("grd_f84_principal", "grd_f84_principal"),
                              ("grd_hospitals_observed", "grd_hospitals_observed"), ("grd_f84_any_panel65", "grd_f84_any_fixed65"),
                              ("grd_f84_any_strict_hospitalisation", "grd_f84_any_hospitalisation_fixed65")]:
                ctl.add(f"deis_vs_grd_file_matches_config_{name}", str(y), CFG.CONTROLS[name].get(y), r[col],
                        "valores GRD leídos de grd_year_summary.csv frente a config.CONTROLS (control cruzado entre módulos)"
                        + ("; el control del brief para hospitalización estricta corresponde al panel fijo de 65 (módulo 01)" if "strict" in name else ""))
            ctl.add("deis_vs_grd_observed_panel_strict_hospitalisation_vs_config", str(y), CFG.CONTROLS["grd_f84_any_strict_hospitalisation"].get(y), r["grd_f84_any_hospitalisation"],
                    "panel OBSERVADO × hospitalización (grd_year_summary.csv) frente al control del brief; difiere en 2023–2024 porque el brief usa el panel fijo de 65 "
                    "(65 hospitales; 68 y 72 observados). Discrepancia documentada por el módulo 01, no un error de lectura.")
        if not np.isnan(r.grd_f84_principal):
            ctl.add("deis_snss_f84_principal_ge_grd_f84_principal", str(y), 1, int(r.deis_f84_principal_snss >= r.grd_f84_principal),
                    f"DEIS SNSS {int(r.deis_f84_principal_snss)} ≥ GRD principal {int(r.grd_f84_principal)} (1 = se cumple; plausibilidad de cobertura, no control oficial)")

    ctl_df = ctl.frame()
    C.atomic_write_csv(ctl_df, CONTROLS_DIR / f"{MODULE}_controls.csv")
    runtime = time.perf_counter() - t0
    C.atomic_write_json(dict(module=MODULE, runtime_seconds=round(runtime, 1), files=[str(p) for _, p, _ in files], n_controls=len(ctl_df),
                             n_differs=int((ctl_df.status == "differs").sum()), pandas=pd.__version__, python=sys.version.split()[0]),
                        CONTROLS_DIR / f"{MODULE}_runlog.json")
    print(ctl_df.loc[ctl_df.status == "differs"].to_string() if (ctl_df.status == "differs").any() else f"[{MODULE}] todos los controles ok ({len(ctl_df)})")
    print(f"[{MODULE}] listo en {runtime:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
