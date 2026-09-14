#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03_denominators.py — Capas de denominador y cobertura + crosswalk comunal (módulo 03 del pipeline del estudio).

Capas (cada una responde una pregunta distinta; nunca se mezclan sin marca explícita):
  1. INE (población territorial, base Censo 2017; Censo 2024 y base 2024 nacional sólo como sensibilidad).
  2. FONASA agregado de diciembre 2018–2025 (stock de aseguramiento público; esquema cambia en 2021, 2023, 2024, 2025).
  3. Inscritos APS de diciembre 2019–2025 (cobertura operativa por centro; grupos de edad cambian en 2024).
  4. ISAPRE comunal de diciembre 2019–2025 (cobertura privada; .xls con edades simples 2019–2020, .xlsx quinquenal desde 2021).
  5. REM-20 2019–2025 (actividad/capacidad hospitalaria; panel de 188 establecimientos con 12 meses en todos los años).
  6. Crosswalk comunal INE (CUT 4/5 dígitos) ↔ DEIS (5 dígitos con cero inicial) con alias explícitos.
  7. Tabla de capas de cobertura por año.

Reglas no negociables aplicadas aquí:
  * Nunca `drop_duplicates()` en FONASA 2018–2020: las filas repetidas son fragmentos aditivos.
  * Nunca sumar hojas por sexo con hojas "Total" de ISAPRE (son vistas duplicadas).
  * Nunca usar REM-20 como población cubierta.
  * Nunca hacer fuzzy matching de nombres de comuna: sólo coincidencia exacta del nombre normalizado o alias explícito
    listado en `comuna_crosswalk.csv`; todo lo demás va a `comuna_unmatched.csv`.
  * Nunca mezclar bases censales sin la columna `population_base`.

Ejecución (desde la raíz del repositorio):
    python3 study/pipeline/03_denominators.py [--tmpdir DIR]
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config as CFG  # noqa: E402
from common import AGE_GROUPS, REGION_NAMES, atomic_write_csv, atomic_write_json, sha256_file  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

MODULE = "03_denominators"
SCRIPT = "study/pipeline/03_denominators.py"
YEARS = list(range(2019, 2026))
FONASA_YEARS = list(range(2018, 2026))
MISSING = "(missing)"  # token explícito para nombres ausentes (no se confunde con NA de pandas)
# Etiquetas de geografía por capa (principio 7 del brief: no mezclar lugar de atención con residencia). Se escriben en cada fila comunal.
GEOGRAPHY = {
    "ine": "residence (territorial population; comuna of residence)",
    "fonasa_mixed": ("mixed: comuna of the APS enrolment centre for inscritos and comuna of domicile for non-inscritos (NOT homogeneous residence); "
                     "the split is available only in fonasa_beneficiaries_comuna_tramo_year for 2018-2022"),
    "fonasa_inscrito": "comuna of the APS enrolment centre (place of enrolment, not residence)",
    "fonasa_no_inscrito": "comuna of domicile as registered by FONASA",
    "fonasa_not_separable": "mixed: enrolment centre comuna or domicile; INSCRITO_APS not published from 2023, not separable",
    "aps": "comuna of the APS centre (place of enrolment, not residence)",
    "isapre": "administrative comuna of the beneficiary as recorded by the ISAPRE (not verified residence)",
    "rem20": "establishment (place of care), not residence",
}
ARGS = None
TIDY = CFG.TIDY
CONTROLS_DIR = CFG.OUT / "controls"  # config.CONTROLS es el dict de valores esperados (sombra la ruta)

# ---------------------------------------------------------------------------
# Controles de reproducción
# ---------------------------------------------------------------------------
_controls: list[dict] = []


def add_control(name: str, key, expected, observed, kind: str = "count", note: str = "", tol_rate: float = 0.005):
    """Registra un control. kind='count' exige igualdad exacta; kind='rate' tolera 0,5 % relativo (salvo `tol_rate`)."""
    exp = None if expected is None else float(expected)
    obs = None if observed is None or (isinstance(observed, float) and np.isnan(observed)) else float(observed)
    if exp is None or obs is None:
        status, absd, reld = "missing", np.nan, np.nan
    else:
        absd = obs - exp
        reld = absd / exp if exp != 0 else (0.0 if absd == 0 else np.inf)
        if kind == "count":
            status = "ok" if absd == 0 else "differs"
        else:
            status = "ok" if abs(reld) <= tol_rate else "differs"
    _controls.append(dict(name=name, key=str(key), expected=expected, observed=observed, abs_diff=absd, rel_diff=reld,
                          status=status, note=note))
    return status


# ---------------------------------------------------------------------------
# Nombres de comuna: normalización y alias explícitos (nunca fuzzy)
# ---------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(value) -> str:
    """Mayúsculas sin acentos; apóstrofos, guiones y '¿' (mojibake) pasan a espacio; sólo A-Z0-9 y espacios simples."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = strip_accents(str(value)).upper().replace("'", " ").replace("’", " ").replace("-", " ").replace("¿", " ")
    text = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", text)).strip()
    return text


# Alias explícitos (forma normalizada de la variante -> forma normalizada del nombre INE). Se documentan en el crosswalk.
ALIASES = {
    "AISEN": "AYSEN",                                  # APS, ISAPRE (Aisén / Aisen)
    "COIHAIQUE": "COYHAIQUE",                          # APS, ISAPRE (Coihaique)
    "CABO DE HORNOS EX NAVARINO": "CABO DE HORNOS",    # FONASA/APS/ISAPRE: 'Cabo de Hornos (Ex - Navarino)' y variantes
    "CON CON": "CONCON",                               # GRD/REM (config.COMUNA_ALIASES)
    "LA CALERA": "CALERA",                             # ISAPRE 2019–2020 ('La Calera'); INE usa 'Calera'
    "MARCHIGUE": "MARCHIHUE",                          # scripts/epi_helpers.py (GRD)
    "PAIHUANO": "PAIGUANO",                            # scripts/epi_helpers.py (GRD)
}
for _k, _v in CFG.COMUNA_ALIASES.items():
    ALIASES.setdefault(normalize_name(_k), normalize_name(_v))

# Marcadores no geográficos observados en las fuentes (nunca se asignan a una comuna).
NON_GEOGRAPHIC = {"DESCONOCIDA", "SIN DATO", "SIN DATO COMUNA", "SIN CODIGO DE COMUNA", "", "NAN", "SIN INFORMACION", "MISSING"}

_name_matches: dict[tuple, dict] = {}
_unmatched: dict[tuple, dict] = {}


def match_comuna(raw_names: pd.Series, crosswalk: pd.DataFrame, source: str, year, weights: pd.Series | None = None):
    """Devuelve (cut_comuna, match_method) alineados con `raw_names`. Sólo exacto normalizado o alias explícito."""
    exact = dict(zip(crosswalk.comuna_norm, crosswalk.cut_comuna))
    norm = raw_names.map(normalize_name)
    cut = norm.map(exact)
    method = pd.Series(np.where(cut.notna(), "exact", None), index=raw_names.index, dtype="object")
    alias_target = norm.map(ALIASES)
    via_alias = cut.isna() & alias_target.notna()
    cut = cut.where(~via_alias, alias_target.map(exact))
    method = method.where(~via_alias, "alias")
    unmatched = cut.isna()
    method = method.where(~unmatched, "unmatched")
    # registro auditable
    w = weights if weights is not None else pd.Series(1.0, index=raw_names.index)
    tab = pd.DataFrame({"raw": raw_names.fillna("<NA>").astype(str), "norm": norm, "cut": cut, "method": method, "w": w})
    for (raw, nrm, mth), grp in tab.groupby(["raw", "norm", "method"], dropna=False):
        if mth == "unmatched":
            key = (source, str(year), raw)
            reason = "non-geographic placeholder" if nrm in NON_GEOGRAPHIC else "no exact normalised match (not aliased)"
            _unmatched[key] = dict(source=source, year=year, raw_name=raw, normalised=nrm, rows=int(len(grp)),
                                   count=float(grp.w.sum()), reason=reason)
        else:
            key = (source, raw, mth)
            rec = _name_matches.setdefault(key, dict(source=source, raw_name=raw, normalised=nrm, cut_comuna=int(grp.cut.iloc[0]),
                                                     match_method=mth, years=set()))
            rec["years"].add(int(year))
    return cut.astype("Int64"), method


# ---------------------------------------------------------------------------
# Bandas de edad
# ---------------------------------------------------------------------------
_BAND_RE = re.compile(r"^\s*(\d+)\s*(?:a|-)\s*(\d+)\s*(?:años|anos)?\s*$", re.I)
_MISSING_LABELS = {"s.i.", "si", "s/i", "sin información", "sin informacion", "", "nan", "none", "s.i"}


def parse_band(label) -> tuple[int | None, int | None]:
    """Etiqueta de tramo -> (edad_min, edad_max); edad_max=None si es abierto; (None, None) si falta información."""
    s = strip_accents(str(label)).strip().lower()
    if s in _MISSING_LABELS:
        return None, None
    m = _BAND_RE.match(s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)\s*(?:a|y|o)\s*mas", s)          # '80 a más años', '85 o más'
    if m:
        return int(m.group(1)), None
    m = re.match(r"^mas de\s*(\d+)", s)                    # 'Más de 99 años'
    if m:
        return int(m.group(1)) + 1, None
    m = re.match(r"^>=\s*(\d+)", s)                        # '>=100'
    if m:
        return int(m.group(1)), None
    return None, None


def band_label(lo, hi, width: int, top: int = 80):
    """Banda armonizada de ancho `width` (abierta en `top`+) si [lo, hi] cabe entera en una banda; si no, <NA>."""
    if lo is None:
        return pd.NA
    if lo >= top:
        return f"{top}+"
    start = (lo // width) * width
    end = start + width - 1
    if hi is None or hi > end:
        return pd.NA
    return f"{start}-{end}"


def harmonise_bands(labels: pd.Series, width: int, top: int = 80) -> pd.Series:
    cache = {}
    out = []
    for lab in labels:
        if lab not in cache:
            lo, hi = parse_band(lab)
            cache[lab] = band_label(lo, hi, width, top)
        out.append(cache[lab])
    return pd.Series(out, index=labels.index, dtype="object")


def who_group_from_age(age: pd.Series) -> pd.Series:
    a = pd.to_numeric(age, errors="coerce")
    start = (a // 5 * 5).astype("Int64")
    lab = start.map(lambda s: pd.NA if pd.isna(s) else ("80+" if s >= 80 else f"{int(s)}-{int(s) + 4}"))
    return lab.astype("object")


assert [band_label(s, s + 4, 5) for s in range(0, 80, 5)] + [band_label(80, None, 5)] == AGE_GROUPS


def read_csv_auto(path: Path, **kw) -> tuple[pd.DataFrame, str]:
    """Lee CSV probando utf-8 estricto y luego latin-1; devuelve (df, encoding usado)."""
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, **kw), enc
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8/latin-1", b"", 0, 1, f"no se pudo decodificar {path}")


# ---------------------------------------------------------------------------
# 1. INE base Censo 2017 + crosswalk
# ---------------------------------------------------------------------------
def build_ine_and_crosswalk():
    path = CFG.PATHS["ine"] / "proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv"
    raw = pd.read_csv(path, encoding="latin-1")
    raw = raw.rename(columns={"Sexo (1=Hombre 2=Mujer)": "sexo", "Nombre Region": "region_name", "Nombre Provincia": "provincia_name",
                              "Nombre Comuna": "comuna_name"})
    n_comunas = raw.Comuna.nunique()
    dup_keys = int(raw.duplicated(["Comuna", "sexo", "Edad"]).sum())
    add_control("ine_comunas", "base2017", 346, n_comunas, note="comunas únicas en proyecciones base 2017")
    add_control("ine_duplicate_keys", "base2017", 0, dup_keys, note="llaves comuna×sexo×edad repetidas")
    assert raw.Edad.max() == 80, "Edad 80 debe ser el grupo abierto 80+"

    # crosswalk
    cw = (raw.drop_duplicates("Comuna")[["Region", "region_name", "Provincia", "provincia_name", "Comuna", "comuna_name"]]
          .rename(columns={"Region": "cut_region", "Provincia": "cut_provincia", "Comuna": "cut_comuna", "region_name": "region_name_ine",
                           "comuna_name": "comuna_name_ine"}).copy())
    cw["cut_comuna"] = cw.cut_comuna.astype(int)
    cw["deis_code"] = cw.cut_comuna.map(lambda c: f"{c:05d}")
    cw["comuna_norm"] = cw.comuna_name_ine.map(normalize_name)
    assert not cw.comuna_norm.duplicated().any(), "nombres INE normalizados duplicados"
    alias_by_target = {}
    for k, v in ALIASES.items():
        alias_by_target.setdefault(v, []).append(k)
    cw["aliases_norm"] = cw.comuna_norm.map(lambda n: "|".join(sorted(alias_by_target.get(n, []))))
    cw["non_continental"] = cw.cut_comuna.isin(CFG.NON_CONTINENTAL)
    cw["region_short"] = cw.cut_region.map(lambda r: REGION_NAMES.get(int(r), ""))
    cw = cw[["cut_comuna", "deis_code", "comuna_name_ine", "comuna_norm", "aliases_norm", "cut_provincia", "provincia_name", "cut_region",
             "region_name_ine", "region_short", "non_continental"]].sort_values("cut_comuna").reset_index(drop=True)
    atomic_write_csv(cw, TIDY / "comuna_crosswalk.csv")

    # población larga 2019–2025, grupos OMS
    value_cols = {f"Poblacion {y}": y for y in YEARS}
    long = raw.melt(id_vars=["Region", "region_name", "Provincia", "provincia_name", "Comuna", "comuna_name", "sexo", "Edad"],
                    value_vars=list(value_cols), var_name="col", value_name="population")
    long["year"] = long.col.map(value_cols).astype(int)
    long["sex"] = long.sexo.map({1: "HOMBRE", 2: "MUJER"})
    long["age_group"] = who_group_from_age(long.Edad)
    com = (long.groupby(["year", "Region", "region_name", "Provincia", "provincia_name", "Comuna", "comuna_name", "sex", "age_group"], observed=True)
           .population.sum().reset_index()
           .rename(columns={"Region": "cut_region", "Provincia": "cut_provincia", "Comuna": "cut_comuna"}))
    com["cut_comuna"] = com.cut_comuna.astype(int)
    com["deis_code"] = com.cut_comuna.map(lambda c: f"{c:05d}")
    com["population"] = com.population.astype(int)
    com["population_base"] = "base2017"
    com["reference_date"] = com.year.map(lambda y: f"{y}-06-30")
    com["unit"] = "persons (INE projection, 30 June)"
    com["geography"] = GEOGRAPHY["ine"]
    com = com[["year", "reference_date", "cut_region", "region_name", "cut_provincia", "provincia_name", "cut_comuna", "deis_code", "comuna_name",
               "sex", "age_group", "population", "population_base", "unit", "geography"]].sort_values(["year", "cut_comuna", "sex", "age_group"])
    assert not com.duplicated(["year", "cut_comuna", "sex", "age_group"]).any()
    atomic_write_csv(com, TIDY / "ine_population_comuna_year_age_sex.csv")

    # agregados nacional / regional con sexo TOTAL y edad TOTAL
    agg = aggregate_levels(com, ["cut_region", "region_name"])
    agg["population_base"] = "base2017"
    agg["reference_date"] = agg.year.map(lambda y: f"{y}-06-30")
    agg["unit"] = "persons (INE projection, 30 June)"
    atomic_write_csv(agg, TIDY / "ine_population_region_national_year_age_sex.csv")
    nat = agg[(agg.level == "national") & (agg.sex == "TOTAL") & (agg.age_group == "TOTAL")].set_index("year").population
    for y, exp in CFG.CONTROLS["ine_population_national"].items():
        add_control("ine_population_national", y, exp, int(nat[y]), note="base Censo 2017, 30 de junio")
    return cw, com, agg, path


def aggregate_levels(df: pd.DataFrame, region_cols: list[str]) -> pd.DataFrame:
    """Totales nacionales y regionales por año × sexo (HOMBRE, MUJER, TOTAL) × grupo de edad (17 + TOTAL)."""
    frames = []
    reg = df.groupby(["year"] + region_cols + ["sex", "age_group"], observed=True).population.sum().reset_index()
    reg["level"] = "region"
    nat = df.groupby(["year", "sex", "age_group"], observed=True).population.sum().reset_index()
    nat["level"] = "national"
    nat["cut_region"] = 0
    nat["region_name"] = "Chile"
    base = pd.concat([reg, nat], ignore_index=True)
    frames.append(base)
    # sexo TOTAL
    st = base.groupby(["year", "level", "cut_region", "region_name", "age_group"], observed=True).population.sum().reset_index()
    st["sex"] = "TOTAL"
    frames.append(st)
    both = pd.concat(frames, ignore_index=True)
    at = both.groupby(["year", "level", "cut_region", "region_name", "sex"], observed=True).population.sum().reset_index()
    at["age_group"] = "TOTAL"
    out = pd.concat([both, at], ignore_index=True)
    out["population"] = out.population.astype(int)
    return out[["year", "level", "cut_region", "region_name", "sex", "age_group", "population"]].sort_values(
        ["year", "level", "cut_region", "sex", "age_group"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 1b. Sensibilidad: Censo 2024 (comuna × sexo × quinquenal) y base 2024 nacional
# ---------------------------------------------------------------------------
def build_ine_sensitivity(cw: pd.DataFrame, agg2017: pd.DataFrame):
    frames = []
    # --- Censo 2024, cuadro 4 ---
    censo_path = CFG.PATHS["ine"] / "Censo_2024" / "D1_poblacion_comuna_sexo_edad_quinquenal.xlsx"
    c = pd.read_excel(censo_path, sheet_name="4", header=3)
    c = c[c["Grupos de edad"].notna()]
    c["Código comuna"] = pd.to_numeric(c["Código comuna"], errors="coerce")
    body = c[(c["Código comuna"].fillna(0) != 0) & (~c["Grupos de edad"].astype(str).str.startswith("Total"))].copy()
    body["cut_comuna"] = body["Código comuna"].astype(int)
    body["lo"] = body["Grupos de edad"].map(lambda s: parse_band(s)[0])
    body["hi"] = body["Grupos de edad"].map(lambda s: parse_band(s)[1])
    body["age_group"] = [band_label(lo, hi, 5) for lo, hi in zip(body.lo, body.hi)]
    assert body.age_group.notna().all(), "grupo de edad del Censo 2024 no armonizable"
    long = body.melt(id_vars=["cut_comuna", "age_group"], value_vars=["Hombres", "Mujeres"], var_name="sexo", value_name="population")
    long["sex"] = long.sexo.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    cen = long.groupby(["cut_comuna", "sex", "age_group"], observed=True).population.sum().reset_index()
    cen = cen.merge(cw[["cut_comuna", "comuna_name_ine", "cut_region", "region_name_ine"]], on="cut_comuna", how="left")
    missing_cw = cen.comuna_name_ine.isna().sum()
    add_control("censo2024_comunas", "censo2024", 346, cen.cut_comuna.nunique(), note="comunas en cuadro 4 del Censo 2024")
    add_control("censo2024_comunas_not_in_crosswalk", "censo2024", 0, int(missing_cw))
    cen["year"] = 2024
    cen = cen.rename(columns={"comuna_name_ine": "name", "region_name_ine": "region_name"})
    cen["level"] = "comuna"
    # totales censo (internos): cuadro 1 país
    s1 = pd.read_excel(censo_path, sheet_name="1", header=3)
    nat_census = int(s1.loc[s1["Región"].astype(str).str.strip() == "País", "Población censada"].iloc[0])
    add_control("censo2024_national_enumerated", 2024, nat_census, int(cen.population.sum()),
                note="suma comunal cuadro 4 vs. total país cuadro 1 (control interno del libro)")
    censo_agg = aggregate_levels(cen.assign(region_name=cen.region_name), ["cut_region", "region_name"])
    censo_agg = censo_agg.rename(columns={"region_name": "name"})
    censo_agg["cut_comuna"] = pd.NA
    cen_out = cen[["year", "level", "cut_region", "cut_comuna", "name", "sex", "age_group", "population"]]
    cen_all = pd.concat([cen_out, censo_agg[["year", "level", "cut_region", "cut_comuna", "name", "sex", "age_group", "population"]]], ignore_index=True)
    cen_all["population_base"] = "censo2024"
    cen_all["reference_date"] = "2024 census enumeration (Censo de Población y Vivienda 2024)"
    cen_all["source_file"] = censo_path.name
    cen_all["note"] = "enumerated population; 80-84 and 85+ collapsed to 80+; not a mid-year projection"
    frames.append(cen_all)

    # --- Base 2024 nacional (1 de enero y 30 de junio) ---
    b_path = CFG.PATHS["ine"] / "Base_2024" / "estimaciones_proyecciones_nacionales_1992_2070_base_2024.xlsx"
    b = pd.read_excel(b_path, header=0)
    b.columns = [str(c).strip() for c in b.columns]
    b["FECHA"] = pd.to_datetime(b.FECHA.astype(str), format="%d/%m/%Y")
    b = b[b.FECHA.dt.year.between(2017, 2026)].copy()
    b["year"] = b.FECHA.dt.year
    b["reference_date"] = b.FECHA.dt.strftime("%Y-%m-%d")
    b["sex"] = b.SEXO.map({"H": "HOMBRE", "M": "MUJER"})
    b["age_group"] = who_group_from_age(b.EDAD)
    bb = b.groupby(["year", "reference_date", "sex", "age_group"], observed=True).POBLACION.sum().reset_index().rename(columns={"POBLACION": "population"})
    parts = [bb]
    st = bb.groupby(["year", "reference_date", "age_group"]).population.sum().reset_index().assign(sex="TOTAL")
    parts.append(st)
    both = pd.concat(parts, ignore_index=True)
    at = both.groupby(["year", "reference_date", "sex"]).population.sum().reset_index().assign(age_group="TOTAL")
    base24 = pd.concat([both, at], ignore_index=True)
    base24["level"] = "national"
    base24["cut_region"] = 0
    base24["cut_comuna"] = pd.NA
    base24["name"] = "Chile"
    base24["population_base"] = "base2024_national"
    base24["source_file"] = b_path.name
    base24["note"] = "INE estimates/projections base 2024, national only; both 1 January and 30 June reference dates kept"
    base24["population"] = base24.population.round().astype(int)
    frames.append(base24[["year", "level", "cut_region", "cut_comuna", "name", "sex", "age_group", "population", "population_base", "reference_date",
                          "source_file", "note"]])

    # --- base 2017 nacional/regional (misma tabla, marcada) para comparación directa ---
    a17 = agg2017.rename(columns={"region_name": "name"}).copy()
    a17["cut_comuna"] = pd.NA
    a17["population_base"] = "base2017"
    a17["source_file"] = "proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv"
    a17["note"] = "INE comunal projections base Censo 2017 aggregated to region/national; 30 June"
    frames.append(a17[["year", "level", "cut_region", "cut_comuna", "name", "sex", "age_group", "population", "population_base", "reference_date",
                       "source_file", "note"]])

    sens = pd.concat(frames, ignore_index=True)
    sens["unit"] = "persons"
    sens = sens[["population_base", "year", "reference_date", "level", "cut_region", "cut_comuna", "name", "sex", "age_group", "population", "unit",
                 "source_file", "note"]]
    atomic_write_csv(sens, TIDY / "ine_population_sensitivity.csv")

    # comparación nacional de bases por año
    nat17 = a17[(a17.level == "national") & (a17.sex == "TOTAL") & (a17.age_group == "TOTAL")].set_index("year").population
    b24 = base24[(base24.sex == "TOTAL") & (base24.age_group == "TOTAL")]
    b24_jun = b24[b24.reference_date.str.endswith("06-30")].set_index("year").population
    b24_jan = b24[b24.reference_date.str.endswith("01-01")].set_index("year").population
    comp = pd.DataFrame({"year": YEARS})
    comp["base2017_national_30jun"] = comp.year.map(nat17)
    comp["base2024_national_30jun"] = comp.year.map(b24_jun)
    comp["base2024_national_1jan"] = comp.year.map(b24_jan)
    comp["censo2024_enumerated"] = np.where(comp.year == 2024, nat_census, np.nan)
    comp["ratio_base2024_to_base2017_30jun"] = comp.base2024_national_30jun / comp.base2017_national_30jun
    comp["ratio_censo2024_to_base2017"] = comp.censo2024_enumerated / comp.base2017_national_30jun
    comp["note"] = "bases never merged; base2017 is the primary denominator, base2024/censo2024 are bridge sensitivities"
    atomic_write_csv(comp, TIDY / "ine_population_base_comparison.csv")
    return sens, comp, [censo_path, b_path]


# ---------------------------------------------------------------------------
# 2. FONASA agregados de diciembre 2018–2025
# ---------------------------------------------------------------------------
SEX_MAP = {"HOMBRE": "HOMBRE", "MUJER": "MUJER", "INDETERMINADO": "INDETERMINADO", "HOMBRES": "HOMBRE", "MUJERES": "MUJER",
           "SIN INFORMACION": "SIN_INFORMACION", "SIN INFORMACIÓN": "SIN_INFORMACION"}


def extract_fonasa_archive(year: int, tmpdir: Path) -> tuple[Path, Path]:
    dest = tmpdir / f"fonasa_{year}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    rar = CFG.PATHS["fonasa"] / f"Resultados_{year}12.rar"
    zp = CFG.PATHS["fonasa"] / f"Resultados_{year}12.zip"
    if rar.is_file():
        subprocess.run(["bsdtar", "-xf", str(rar), "-C", str(dest)], check=True)
        archive = rar
    elif zp.is_file():
        with zipfile.ZipFile(zp) as z:
            z.extractall(dest)
        archive = zp
    else:
        raise FileNotFoundError(f"FONASA {year}: falta {rar.name} / {zp.name}")
    csvs = sorted(dest.rglob("*.csv"))
    assert len(csvs) == 1, f"FONASA {year}: se esperaba un CSV, hay {len(csvs)}"
    return archive, csvs[0]


def build_fonasa(cw: pd.DataFrame, tmpdir: Path):
    schema_rows, comuna_frames, national_frames, sources = [], [], [], []
    for year in FONASA_YEARS:
        archive, csv = extract_fonasa_archive(year, tmpdir)
        df, enc = read_csv_auto(csv, dtype=str)
        cols = df.columns.tolist()
        count_col = [c for c in cols if c.upper() in ("CUENTA_BENEFICIARIOS", "BENEFICIARIOS")][0]
        tramo_col = [c for c in cols if c.upper() in ("TRAMO", "TRAMO_FONASA")][0]
        region_col = [c for c in cols if c.upper().startswith("REGI")][0]
        df["n"] = pd.to_numeric(df[count_col], errors="coerce")
        assert df.n.notna().all(), f"FONASA {year}: conteos no numéricos"
        n_dup = int(df.duplicated().sum())  # se conservan: fragmentos aditivos
        total = int(df.n.sum())
        exp = CFG.CONTROLS["fonasa_beneficiaries_december"].get(year)
        if exp is not None:
            add_control("fonasa_beneficiaries_december", year, exp, total, note=f"{csv.name}; duplicados conservados={n_dup}")
        # nacional por dimensión (antes de colapsar)
        for dim in ["TITULAR_CARGA", "NACIONALIDAD", "TIPO_ASEGURADO", "INSCRITO_APS", tramo_col, "SEXO", "EDAD_TRAMO"]:
            if dim in df.columns:
                g = df.groupby(df[dim].fillna("<NA>").astype(str).str.strip().str.upper()).n.sum().reset_index()
                g.columns = ["category", "beneficiaries"]
                g["dimension"] = "TRAMO" if dim == tramo_col else dim
                g["year"] = year
                national_frames.append(g)
        national_frames.append(pd.DataFrame({"year": [year], "dimension": ["TOTAL"], "category": ["TOTAL"], "beneficiaries": [total]}))
        # armonización
        h = pd.DataFrame({
            "year": year,
            "region_raw": df[region_col].fillna(MISSING).astype(str).str.strip(),
            "comuna_raw": df.COMUNA.fillna(MISSING).astype(str).str.strip(),
            "sex_raw": df.SEXO.astype(str).str.strip(),
            "age_band_raw": df.EDAD_TRAMO.astype(str).str.strip(),
            "tramo": df[tramo_col].fillna(MISSING).astype(str).str.strip().str.upper(),
            "inscrito_aps": df.INSCRITO_APS.fillna(MISSING).astype(str).str.strip() if "INSCRITO_APS" in df.columns else "not_available",
            "beneficiaries": df.n,
        })
        h["sex"] = h.sex_raw.str.upper().map(SEX_MAP).fillna(h.sex_raw.str.upper())
        h = (h.groupby(["year", "region_raw", "comuna_raw", "sex", "age_band_raw", "tramo", "inscrito_aps"], observed=True)
             .beneficiaries.sum().reset_index())
        h["cut_comuna"], h["match_method"] = match_comuna(h.comuna_raw, cw, "FONASA", year, weights=h.beneficiaries)
        h["age_band_5y"] = harmonise_bands(h.age_band_raw, 5)
        h["age_band_10y"] = harmonise_bands(h.age_band_raw, 10)
        h["beneficiaries"] = h.beneficiaries.astype(int)
        assert int(h.beneficiaries.sum()) == total
        comuna_frames.append(h)
        bands = sorted(df.EDAD_TRAMO.dropna().unique().tolist())
        schema_rows.append(dict(year=year, source_archive=archive.name, member_file=csv.name, encoding=enc, mes_informacion=df.MES_INFORMACION.iloc[0],
                                columns="|".join(cols), n_rows_raw=len(df), n_exact_duplicate_rows_kept=n_dup, count_column=count_col, tramo_column=tramo_col,
                                region_column=region_col, has_inscrito_aps="INSCRITO_APS" in cols, has_tipo_asegurado="TIPO_ASEGURADO" in cols,
                                has_direccion_zonal="DIRECCION_ZONAL" in cols, has_servicio_salud="SERVICIO_SALUD" in cols,
                                age_band_scheme=f"{len(bands)} labels: {bands[0]} … {bands[-1]}", age_band_5y_derivable=bool(h.age_band_5y.notna().any()),
                                total_beneficiaries=total, sha256=sha256_file(archive),
                                unit="beneficiaries (December stock)",
                                aggregation_rule="rows are additive within a year (exact duplicates kept); geography mixes APS-enrolment comuna (inscritos) and domicile (no inscritos)"))
        sources.append(archive)
        shutil.rmtree(csv.parent, ignore_errors=True)
    full = pd.concat(comuna_frames, ignore_index=True)
    full = full.merge(cw[["cut_comuna", "cut_region"]], on="cut_comuna", how="left")
    full["cut_region"] = full.cut_region.astype("Int64")
    full = full[["year", "region_raw", "cut_region", "comuna_raw", "cut_comuna", "match_method", "sex", "age_band_raw", "age_band_5y", "age_band_10y", "tramo",
                 "inscrito_aps", "beneficiaries"]]
    if ARGS is not None and ARGS.full_grain:
        atomic_write_csv(full.sort_values(["year", "cut_comuna", "sex", "age_band_raw", "tramo", "inscrito_aps"]), TIDY / "fonasa_beneficiaries_comuna_year_full_grain.csv")
    # vista 1: año × comuna × sexo × banda de edad (para denominadores por edad/sexo)
    com = (full.groupby(["year", "region_raw", "cut_region", "comuna_raw", "cut_comuna", "match_method", "sex", "age_band_raw", "age_band_5y", "age_band_10y"], dropna=False, observed=True)
           .beneficiaries.sum().reset_index())
    com["unit"] = "beneficiaries (December stock)"
    com["geography"] = GEOGRAPHY["fonasa_mixed"]
    atomic_write_csv(com.sort_values(["year", "cut_comuna", "sex", "age_band_raw"]), TIDY / "fonasa_beneficiaries_comuna_year.csv")
    # vista 2: año × comuna × tramo × inscrito APS (misma suma total; vistas aditivas independientes, no cruzadas entre sí)
    tr = (full.groupby(["year", "region_raw", "cut_region", "comuna_raw", "cut_comuna", "match_method", "tramo", "inscrito_aps"], dropna=False, observed=True)
          .beneficiaries.sum().reset_index())
    tr["unit"] = "beneficiaries (December stock)"
    tr["geography"] = (tr.inscrito_aps.astype(str).str.strip().str.upper()
                       .map({"SI": GEOGRAPHY["fonasa_inscrito"], "NO": GEOGRAPHY["fonasa_no_inscrito"], "NOT_AVAILABLE": GEOGRAPHY["fonasa_not_separable"]})
                       .fillna(GEOGRAPHY["fonasa_mixed"]))
    atomic_write_csv(tr.sort_values(["year", "cut_comuna", "tramo", "inscrito_aps"]), TIDY / "fonasa_beneficiaries_comuna_tramo_year.csv")
    atomic_write_csv(pd.DataFrame(schema_rows), TIDY / "fonasa_schema_by_year.csv")
    nat = pd.concat(national_frames, ignore_index=True)[["year", "dimension", "category", "beneficiaries"]]
    nat["beneficiaries"] = nat.beneficiaries.astype(int)
    nat["unit"] = "beneficiaries (December stock)"
    atomic_write_csv(nat.sort_values(["year", "dimension", "category"]), TIDY / "fonasa_beneficiaries_national_year.csv")
    return com, nat, sources


# ---------------------------------------------------------------------------
# 3. Inscritos APS 2019–2025
# ---------------------------------------------------------------------------
def build_aps(cw: pd.DataFrame):
    frames, sources = [], []
    for year in YEARS:
        path = CFG.PATHS["fonasa_aps"] / f"Inscritos_APS_{year}12.csv"
        df, enc = read_csv_auto(path, dtype=str)
        cols = df.columns.tolist()
        tramo_col = "TRAMO" if "TRAMO" in cols else "TRAMO_FONASA"
        dep_col = "NOMBRE_DEPENDENCIA" if "NOMBRE_DEPENDENCIA" in cols else "DEPENDENCIA_ADMINISTRATIVA"
        region_col = [c for c in cols if c.upper().startswith("REGI")][0]
        df["n"] = pd.to_numeric(df.TOTAL_INSCRITOS, errors="coerce")
        assert df.n.notna().all(), f"APS {year}: totales no numéricos"
        h = pd.DataFrame({
            "year": year, "periodo_raw": df.PERIODO.astype(str).str.strip(), "servicio_salud": df.SERVICIO_SALUD.astype(str).str.strip(),
            "region_raw": df[region_col].astype(str).str.strip(), "comuna_raw": df.COMUNA.astype(str).str.strip(),
            "cod_centro": df.COD_CENTRO.astype(str).str.strip(), "nombre_centro": df.NOMBRE_CENTRO.astype(str).str.strip(),
            "dependencia": df[dep_col].astype(str).str.strip(), "tramo": df[tramo_col].fillna("missing").astype(str).str.strip().str.upper(),
            "age_band_raw": df.EDAD_TRAMO.astype(str).str.strip(), "sex_raw": df.SEXO.astype(str).str.strip(), "enrolled": df.n.astype(int),
            "source_file": path.name, "encoding": enc, "tramo_column": tramo_col, "dependencia_column": dep_col,
        })
        h["sex"] = h.sex_raw.str.upper().map(SEX_MAP).fillna(h.sex_raw.str.upper())
        h["tramo_group"] = np.where(h.tramo.isin(list("ABCD")), "A-D", np.where(h.tramo == "X", "X", "missing"))
        frames.append(h)
        sources.append(path)
        add_control("aps_enrolled_december", year, CFG.CONTROLS["aps_enrolled_december"][year], int(h.enrolled.sum()), note=path.name)
        add_control("aps_centres", year, CFG.CONTROLS["aps_centres"][year], int(h.cod_centro.nunique()), note="códigos de centro distintos")
    d = pd.concat(frames, ignore_index=True)
    d["age_band_20y"] = harmonise_bands(d.age_band_raw, 20)
    d["age_band_10y"] = harmonise_bands(d.age_band_raw, 10)
    d["comuna_norm"] = d.comuna_raw.map(normalize_name)
    d["cut_comuna"] = pd.array([pd.NA] * len(d), dtype="Int64")
    d["match_method"] = "unmatched"
    for year, idx in d.groupby("year").groups.items():  # coincidencia por año para trazabilidad
        cut, meth = match_comuna(d.loc[idx, "comuna_raw"], cw, "APS", year, weights=d.loc[idx, "enrolled"])
        d.loc[idx, "cut_comuna"] = cut
        d.loc[idx, "match_method"] = meth
    d = d.merge(cw[["cut_comuna", "cut_region", "deis_code"]], on="cut_comuna", how="left")

    # panel continuo de códigos y cambios geográficos
    codes_by_year = d.groupby("year").cod_centro.apply(set)
    panel = set.intersection(*codes_by_year.tolist())
    add_control("aps_panel_size", "2019-2025", 1871, len(panel), note="códigos de centro presentes en los 7 años")
    comuna_sets = d.groupby("cod_centro").comuna_raw.apply(lambda s: set(s.unique()))
    changed = sorted(comuna_sets[comuna_sets.map(len) > 1].index.tolist())
    add_control("aps_codes_with_comuna_change", "2019-2025", 2, len(changed), note="esperados 200261 (código reutilizado) y 200474 (corrección geográfica): " + ",".join(changed))
    flagged = {"200261", "200474"} | set(changed)
    d["in_panel_1871"] = d.cod_centro.isin(panel)
    d["geographic_change_flag"] = d.cod_centro.isin(flagged)

    # centro × año
    key = ["year", "periodo_raw", "cod_centro", "nombre_centro", "servicio_salud", "region_raw", "comuna_raw", "comuna_norm", "cut_comuna", "cut_region",
           "deis_code", "match_method", "dependencia", "in_panel_1871", "geographic_change_flag", "source_file"]
    cen = d.groupby(key, dropna=False, observed=True).agg(enrolled_total=("enrolled", "sum"), n_rows=("enrolled", "size")).reset_index()
    for grp, col in [("A-D", "enrolled_tramo_AD"), ("X", "enrolled_tramo_X"), ("missing", "enrolled_tramo_missing")]:
        s = d[d.tramo_group == grp].groupby(["year", "cod_centro"]).enrolled.sum().rename(col)
        cen = cen.merge(s, on=["year", "cod_centro"], how="left")
        cen[col] = cen[col].fillna(0).astype(int)
    cen["unit"] = "enrolled persons (December stock, comuna of the centre)"
    cen["geography"] = GEOGRAPHY["aps"]
    assert not cen.duplicated(["year", "cod_centro"]).any(), "centro duplicado dentro de un año"
    atomic_write_csv(cen.sort_values(["year", "cod_centro"]), TIDY / "aps_enrolment_centre_year.csv")

    # comuna × año × sexo × banda × tramo
    com = (d.groupby(["year", "region_raw", "comuna_raw", "cut_comuna", "cut_region", "match_method", "sex", "age_band_raw", "age_band_20y", "age_band_10y", "tramo"],
                     dropna=False, observed=True)
           .agg(enrolled=("enrolled", "sum"), n_centres=("cod_centro", "nunique")).reset_index())
    com["tramo_group"] = np.where(com.tramo.isin(list("ABCD")), "A-D", np.where(com.tramo == "X", "X", "missing"))
    # unidad: personas inscritas (stock de diciembre, comuna del centro); `enrolled` es aditivo entre filas, `n_centres` no lo es
    com["unit"] = "enrolled persons (December stock); n_centres = distinct centre codes, not additive across rows"
    com["geography"] = GEOGRAPHY["aps"]
    atomic_write_csv(com.sort_values(["year", "cut_comuna", "sex", "age_band_raw", "tramo"]), TIDY / "aps_enrolment_comuna_year.csv")

    # panel
    rows = []
    for year, g in d.groupby("year"):
        tot = int(g.enrolled.sum())
        pan = int(g[g.in_panel_1871].enrolled.sum())
        rows.append(dict(year=year, centres_total=int(g.cod_centro.nunique()), centres_panel=int(g[g.in_panel_1871].cod_centro.nunique()),
                         enrolled_total=tot, enrolled_panel_1871=pan, retention_panel_1871=pan / tot,
                         enrolled_tramo_AD=int(g[g.tramo_group == "A-D"].enrolled.sum()), enrolled_tramo_X=int(g[g.tramo_group == "X"].enrolled.sum()),
                         enrolled_tramo_missing=int(g[g.tramo_group == "missing"].enrolled.sum())))
    pan = pd.DataFrame(rows)
    for y, exp in CFG.CONTROLS["aps_panel_1871_retention"].items():
        add_control("aps_panel_1871_retention", y, exp, float(pan.set_index("year").retention_panel_1871[y]), kind="rate", note="proporción del total anual retenida por el panel")
    pan["unit"] = "enrolled persons (December stock); centres = distinct centre codes; retention = panel enrolled / total enrolled"
    atomic_write_csv(pan, TIDY / "aps_panel.csv")
    pc = (d[d.in_panel_1871].groupby("cod_centro").agg(nombre_centro_2025=("nombre_centro", "last"), comunas=("comuna_raw", lambda s: "|".join(sorted(set(s)))),
                                                          geographic_change_flag=("geographic_change_flag", "max")).reset_index())
    atomic_write_csv(pc, TIDY / "aps_panel_centres.csv")
    return cen, com, pan, sources


# ---------------------------------------------------------------------------
# 4. ISAPRE comunal 2019–2025
# ---------------------------------------------------------------------------
def _isapre_row_type(c0, c1, c2, c3) -> str:
    s1 = str(c1).strip() if pd.notna(c1) else ""
    s3 = str(c3).strip() if pd.notna(c3) else ""
    u1, u3 = s1.upper(), s3.upper()
    if u1.startswith("TOTAL ISAPRES") or u1.startswith("TOTAL PAIS") or u1.startswith("TOTAL PAÍS"):
        return "total_national"
    if u1.startswith("TOTAL"):
        return "total_region"
    if u1.startswith("FUENTE") or u1.startswith("NOTA") or u1.startswith("FECHA"):
        return "skip"
    if u1 == "SIN DATO" or u3 == "SIN DATO" or u3 == "SIN DATO COMUNA" or u1 == "SIN DATO REGION" or u1 == "SIN CÓDIGO DE COMUNA" or u1 == "SIN CODIGO DE COMUNA":
        return "placeholder"
    if pd.notna(c0) and s3 not in ("", "-") and u3 not in ("NOMBRE COMUNA",):
        return "comuna"
    return "skip"


def parse_isapre_legacy(xl: pd.ExcelFile, sheet: str, year: int) -> tuple[pd.DataFrame, int | None]:
    """Hojas 2019–2020: encabezados en filas 0–2 (Año Mes / Edad 1..100 / tipo), 'Totales' en la última columna."""
    d = xl.parse(sheet, header=None)
    edad_row = d.iloc[1]
    age_cols = [j for j in range(4, d.shape[1]) if pd.notna(edad_row.iloc[j]) and str(d.iloc[0, j]).strip() != "Totales"]
    tot_col = [j for j in range(4, d.shape[1]) if str(d.iloc[0, j]).strip() == "Totales"]
    tot_col = tot_col[0] if tot_col else None
    rows, national = [], None
    for i in range(3, len(d)):
        c0, c1, c2, c3 = d.iloc[i, 0], d.iloc[i, 1], d.iloc[i, 2], d.iloc[i, 3]
        rt = _isapre_row_type(c0, c1, c2, c3)
        if rt == "total_national":
            national = int(pd.to_numeric(d.iloc[i, tot_col if tot_col is not None else 4], errors="coerce"))
            continue
        if rt in ("skip", "total_region"):
            continue
        region_code = pd.to_numeric(c0, errors="coerce")
        comuna = str(c3).strip() if pd.notna(c3) else str(c1).strip()
        vals = pd.to_numeric(d.iloc[i, age_cols], errors="coerce").fillna(0)
        for j, v in zip(age_cols, vals):
            edad = edad_row.iloc[j]
            rows.append((year, region_code, str(c1).strip(), str(c2).strip() if pd.notna(c2) else "", comuna, rt, f"Edad {int(edad)}" if pd.notna(edad) and str(edad) != "-1" else "Nonatos o sin clasificar", int(v)))
        if tot_col is not None:
            row_total = pd.to_numeric(d.iloc[i, tot_col], errors="coerce")
            if pd.notna(row_total) and int(row_total) != int(vals.sum()) and sheet != "Beneficiarios":
                raise AssertionError(f"ISAPRE {year} {sheet} fila {i}: Totales={row_total} != suma de edades {vals.sum()}")
    out = pd.DataFrame(rows, columns=["year", "region_code", "region_raw", "provincia_raw", "comuna_raw", "row_type", "age_band_raw", "beneficiaries"])
    return out, national


def parse_isapre_modern(xl: pd.ExcelFile, sheet: str, year: int) -> tuple[pd.DataFrame, int | None]:
    """Hojas 2021+: encabezado en fila 6 (0-4 … >=100, S/I, Total); datos desde fila 7; 'Total Región' / 'Total Pais' por texto."""
    d = xl.parse(sheet, header=None)
    hdr_idx = next(i for i in range(len(d)) if str(d.iloc[i, 4]).strip() == "0-4")
    header = [str(x).strip() for x in d.iloc[hdr_idx]]
    band_cols = [j for j in range(4, d.shape[1]) if header[j] not in ("Total", "nan", "")]
    tot_col = header.index("Total") if "Total" in header else None
    rows, national = [], None
    for i in range(hdr_idx + 1, len(d)):
        c0, c1, c2, c3 = d.iloc[i, 0], d.iloc[i, 1], d.iloc[i, 2], d.iloc[i, 3]
        rt = _isapre_row_type(c0, c1, c2, c3)
        if rt == "total_national":
            national = int(pd.to_numeric(d.iloc[i, tot_col], errors="coerce"))
            continue
        if rt in ("skip", "total_region"):
            continue
        region_code = pd.to_numeric(c0, errors="coerce")
        vals = pd.to_numeric(d.iloc[i, band_cols], errors="coerce").fillna(0)
        if tot_col is not None:
            row_total = pd.to_numeric(d.iloc[i, tot_col], errors="coerce")
            if pd.notna(row_total) and int(row_total) != int(vals.sum()):
                raise AssertionError(f"ISAPRE {year} {sheet} fila {i}: Total={row_total} != suma de tramos {vals.sum()}")
        for j, v in zip(band_cols, vals):
            rows.append((year, region_code, str(c1).strip(), str(c2).strip() if pd.notna(c2) else "", str(c3).strip(), rt, header[j], int(v)))
    out = pd.DataFrame(rows, columns=["year", "region_code", "region_raw", "provincia_raw", "comuna_raw", "row_type", "age_band_raw", "beneficiaries"])
    return out, national


LEGACY_RAW_LABEL = {band_label(st, st + 4, 5): f"Edad {max(st, 1)}-{st + 4}" for st in range(0, 80, 5)}
LEGACY_RAW_LABEL["80+"] = "Edad 80-100"


def isapre_legacy_band(k: int):
    """Columnas 'Edad 1'..'Edad 100' de 2019–2020 -> banda quinquenal. Inferencia documentada: 'Edad 1' contiene las edades 0–1
    (su magnitud duplica la de 'Edad 2' y la suma 'Edad 1-4' es coherente con el tramo 0-4 publicado desde 2021); 'Edad 100' es abierta."""
    age = 0 if k == 1 else k
    return band_label(age, age if k < 100 else None, 5)


def build_isapre(cw: pd.DataFrame):
    frames, nat_rows, sources = [], [], []
    keys = ["year", "region_code", "region_raw", "provincia_raw", "comuna_raw", "row_type", "sex", "age_band_raw", "age_band_5y"]
    for year in YEARS:
        ext = "xls" if year < 2021 else "xlsx"
        path = CFG.PATHS["isapre"] / f"isapre_beneficiarios_comuna_{year}.{ext}"
        sources.append(path)
        xl = pd.ExcelFile(path)
        parts, nat = [], {}
        if year < 2021:
            spec = [("Cotizantes", "cotizantes", "TOTAL"), ("Cargas", "cargas", "TOTAL"), ("Beneficiarios", "beneficiarios", "TOTAL"),
                    ("Cotizantes (F)", "cotizantes", "MUJER"), ("Cargas (F)", "cargas", "MUJER"), ("Beneficiarios (F)", "beneficiarios", "MUJER"),
                    ("Cotizantes (M)", "cotizantes", "HOMBRE"), ("Cargas (M)", "cargas", "HOMBRE"), ("Beneficiarios (M)", "beneficiarios", "HOMBRE"),
                    ("Nonatos o sin Clasificar", "nonatos", "TOTAL")]
            for sheet, cat, sex in spec:
                df, national = parse_isapre_legacy(xl, sheet, year)
                nat[(cat, sex)] = national
                if cat == "nonatos":
                    df["age_band_5y"], df["age_band_raw"], df["category"] = "nonatos_sin_clasificar", "Nonatos o sin clasificar", "beneficiarios"
                else:
                    k = df.age_band_raw.str.extract(r"Edad (\d+)")[0].astype(int)
                    df["age_band_5y"] = k.map(isapre_legacy_band)
                    df["age_band_raw"] = df.age_band_5y.map(LEGACY_RAW_LABEL)
                    df["category"] = cat
                df["sex"] = sex
                parts.append(df)
            add_control("isapre_internal_cot_plus_cargas_plus_nonatos", year, nat[("beneficiarios", "TOTAL")],
                        nat[("cotizantes", "TOTAL")] + nat[("cargas", "TOTAL")] + nat[("nonatos", "TOTAL")],
                        note="fila TOTAL ISAPRES de la hoja Beneficiarios frente a suma de hojas Cotizantes+Cargas+Nonatos")
            official_total = nat[("beneficiarios", "TOTAL")]
            rule = "sheet 'Beneficiarios' (age columns collapsed to 5-year bands) + sheet 'Nonatos o sin Clasificar'"
        else:
            spec = [("Total Cotizantes", "cotizantes", "TOTAL"), ("Total Cargas", "cargas", "TOTAL"),
                    ("Cotizantes (F)", "cotizantes", "MUJER"), ("Cotizantes (M)", "cotizantes", "HOMBRE"), ("Cotizantes (SI)", "cotizantes", "SIN_INFORMACION"),
                    ("Cargas (F)", "cargas", "MUJER"), ("Cargas (M)", "cargas", "HOMBRE"), ("Cargas (SI)", "cargas", "SIN_INFORMACION")]
            for sheet, cat, sex in spec:
                df, national = parse_isapre_modern(xl, sheet, year)
                nat[(cat, sex)] = national
                df["age_band_5y"] = harmonise_bands(df.age_band_raw, 5).fillna("not_informed")
                df["category"], df["sex"] = cat, sex
                parts.append(df)
            official_total = nat[("cotizantes", "TOTAL")] + nat[("cargas", "TOTAL")]
            add_control("isapre_internal_sex_sheets_sum_to_total", year, official_total, sum(v for (c, s_), v in nat.items() if s_ != "TOTAL"),
                        note="hojas F+M+SI de cotizantes y cargas frente a hojas Total (vistas duplicadas; nunca se suman entre sí)")
            rule = "Total Cotizantes + Total Cargas (derived per cell; sex views derived likewise from the sex sheets)"
        d = pd.concat(parts, ignore_index=True)
        d["region_code"] = pd.to_numeric(d.region_code, errors="coerce").astype("Int64")
        wide = d.groupby(keys + ["category"], dropna=False, observed=True).beneficiaries.sum().unstack("category").reset_index()
        for c in ("cotizantes", "cargas", "beneficiarios"):
            if c not in wide.columns:
                wide[c] = np.nan
        if year < 2021:
            wide.loc[wide.age_band_5y == "nonatos_sin_clasificar", ["cotizantes", "cargas"]] = 0
            wide[["cotizantes", "cargas", "beneficiarios"]] = wide[["cotizantes", "cargas", "beneficiarios"]].fillna(0).astype(int)
            wide["beneficiarios_source"] = np.where(wide.age_band_5y == "nonatos_sin_clasificar", "sheet Nonatos o sin Clasificar", "sheet Beneficiarios")
            mism = int((wide.loc[wide.age_band_5y != "nonatos_sin_clasificar"].eval("abs(beneficiarios - cotizantes - cargas)")).sum())
            add_control("isapre_internal_cells_beneficiarios_eq_cot_plus_cargas", year, 0, mism,
                        note="suma de |Beneficiarios − (Cotizantes + Cargas)| sobre celdas comuna×sexo×banda (hojas 2019–2020)")
        else:
            wide[["cotizantes", "cargas"]] = wide[["cotizantes", "cargas"]].fillna(0).astype(int)
            wide["beneficiarios"] = wide.cotizantes + wide.cargas
            wide["beneficiarios_source"] = "derived: cotizantes + cargas"
        mine = int(wide.loc[wide.sex == "TOTAL", "beneficiarios"].sum())
        add_control("isapre_beneficiaries_december", year, CFG.CONTROLS["isapre_beneficiaries_december"][year], mine, note=f"{path.name}: {rule}")
        add_control("isapre_sheet_total_row_vs_parsed_rows", year, official_total, mine, note="fila total nacional del libro frente a suma de filas parseadas (comunas + marcadores)")
        nat_rows.append(dict(year=year, source_file=path.name, cotizantes=nat[("cotizantes", "TOTAL")], cargas=nat[("cargas", "TOTAL")],
                             nonatos_sin_clasificar=nat.get(("nonatos", "TOTAL"), 0), beneficiarios_total=mine,
                             beneficiarios_female=int(wide.loc[wide.sex == "MUJER", "beneficiarios"].sum()),
                             beneficiarios_male=int(wide.loc[wide.sex == "HOMBRE", "beneficiarios"].sum()),
                             beneficiarios_sex_not_informed=int(wide.loc[wide.sex == "SIN_INFORMACION", "beneficiarios"].sum()),
                             beneficiarios_age_not_informed=int(wide.loc[(wide.sex == "TOTAL") & (wide.age_band_5y == "not_informed"), "beneficiarios"].sum()),
                             n_cells=len(wide), n_all_zero_cells_dropped=int((wide[["cotizantes", "cargas", "beneficiarios"]].sum(axis=1) == 0).sum()), rule=rule))
        frames.append(wide[wide[["cotizantes", "cargas", "beneficiarios"]].sum(axis=1) > 0])
    d = pd.concat(frames, ignore_index=True)
    d["cut_comuna"] = pd.array([pd.NA] * len(d), dtype="Int64")
    d["match_method"] = "unmatched"
    is_com = d.row_type == "comuna"
    for year, idx in d[is_com].groupby("year").groups.items():
        cut, meth = match_comuna(d.loc[idx, "comuna_raw"], cw, "ISAPRE", year, weights=d.loc[idx, "beneficiarios"])
        d.loc[idx, "cut_comuna"] = cut
        d.loc[idx, "match_method"] = meth
    for year, g in d[~is_com].groupby("year"):
        match_comuna(g.comuna_raw, cw, "ISAPRE", year, weights=g.beneficiarios)  # marcadores no geográficos: quedan en unmatched
    d = d.merge(cw[["cut_comuna", "cut_region"]], on="cut_comuna", how="left")
    d["cut_region"] = d.cut_region.astype("Int64")
    d["unit"] = "persons with valid benefits (December stock); sum only within year+sex (TOTAL duplicates the sex views)"
    d["geography"] = GEOGRAPHY["isapre"]
    d = d[["year", "region_code", "region_raw", "provincia_raw", "comuna_raw", "cut_comuna", "cut_region", "match_method", "row_type", "sex", "age_band_raw",
           "age_band_5y", "cotizantes", "cargas", "beneficiarios", "beneficiarios_source", "unit", "geography"]]
    atomic_write_csv(d.sort_values(["year", "sex", "region_code", "comuna_raw", "age_band_5y"]), TIDY / "isapre_beneficiaries_comuna_year.csv")
    nat = pd.DataFrame(nat_rows)
    nat["unit"] = "persons with valid benefits (December stock; administrative comuna of the beneficiary)"
    nat["aggregation_rule"] = ("comuna file: sum ONLY within year+sex; the TOTAL sex view duplicates MUJER+HOMBRE(+SIN_INFORMACION); beneficiarios = cotizantes + cargas "
                               "(+ nonatos in 2019-2020); all-zero cells of the complete source grid are omitted (absent = 0)")
    nat["age_note"] = np.where(nat.year < 2021, "2019-2020 single-year columns 'Edad 1'..'Edad 100' collapsed to 5-year bands; 'Edad 1' inferred to hold ages 0-1; 'Edad 100' open-ended",
                               "5-year bands as published (0-4 … 95-99, >=100 -> 80+); S/I -> not_informed")
    atomic_write_csv(nat, TIDY / "isapre_beneficiaries_national_year.csv")
    return d, nat, sources


# ---------------------------------------------------------------------------
# 5. REM-20 2019–2025: actividad/capacidad hospitalaria y panel de 188
# ---------------------------------------------------------------------------
def build_rem20():
    path = CFG.PATHS["rem20"] / "indicadores_rem20.csv"
    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8")
    num = ["DIAS_CAMAS_OCUPADAS", "DIAS_CAMAS_DISPONIBLES", "DIAS_ESTADA", "NUMERO_EGRESOS", "EGRESOS_FALLECIDOS", "TRASLADOS"]
    for c in num:
        df[c] = pd.to_numeric(df[c].str.replace(",", "."), errors="coerce")
        assert df[c].notna().all(), f"REM-20: {c} con valores no numéricos"
    df["PERIODO"] = df.PERIODO.astype(int)
    df["MES"] = df.MES.astype(int)
    d = df[df.PERIODO.between(2019, 2025)].copy()
    n_dup = int(d.duplicated(["CODIGO_ESTABLECIMIENTO", "PERIODO", "COD_AREA_FUNCIONAL", "MES"]).sum())
    add_control("rem20_duplicate_establishment_area_month_rows", "2019-2025", 0, n_dup,
                note="fila repetida conservada (aditiva): una fila en cero y otra con datos para el mismo establecimiento-área-mes")
    for c in ["ESTABLECIMIENTO", "AREA_FUNCIONAL", "GLOSA_SSS"]:
        d[c] = d[c].str.strip()
    # establecimiento × área × año
    ea = (d.groupby(["PERIODO", "COD_SSS", "GLOSA_SSS", "CODIGO_ESTABLECIMIENTO", "ESTABLECIMIENTO", "COD_AREA_FUNCIONAL", "AREA_FUNCIONAL"], observed=True)
          .agg(months_reported=("MES", "nunique"), discharges=("NUMERO_EGRESOS", "sum"), deaths=("EGRESOS_FALLECIDOS", "sum"), transfers=("TRASLADOS", "sum"),
               bed_days_available=("DIAS_CAMAS_DISPONIBLES", "sum"), bed_days_occupied=("DIAS_CAMAS_OCUPADAS", "sum"), days_of_stay=("DIAS_ESTADA", "sum"))
          .reset_index().rename(columns={"PERIODO": "year", "COD_SSS": "cod_sss", "GLOSA_SSS": "glosa_sss", "CODIGO_ESTABLECIMIENTO": "codigo_establecimiento",
                                         "ESTABLECIMIENTO": "establecimiento", "COD_AREA_FUNCIONAL": "cod_area_funcional", "AREA_FUNCIONAL": "area_funcional"}))
    # establecimiento × año
    est = (d.groupby(["PERIODO", "COD_SSS", "GLOSA_SSS", "CODIGO_ESTABLECIMIENTO", "ESTABLECIMIENTO"], observed=True)
           .agg(months_reported=("MES", "nunique"), n_areas=("COD_AREA_FUNCIONAL", "nunique"), discharges=("NUMERO_EGRESOS", "sum"),
                deaths=("EGRESOS_FALLECIDOS", "sum"), transfers=("TRASLADOS", "sum"), bed_days_available=("DIAS_CAMAS_DISPONIBLES", "sum"),
                bed_days_occupied=("DIAS_CAMAS_OCUPADAS", "sum"), days_of_stay=("DIAS_ESTADA", "sum"))
           .reset_index().rename(columns={"PERIODO": "year", "COD_SSS": "cod_sss", "GLOSA_SSS": "glosa_sss", "CODIGO_ESTABLECIMIENTO": "codigo_establecimiento",
                                          "ESTABLECIMIENTO": "establecimiento"}))
    # un establecimiento puede cambiar de nombre/SS dentro de un año; la llave es código × año
    est = (est.groupby(["year", "codigo_establecimiento"], as_index=False)
           .agg(cod_sss=("cod_sss", "first"), glosa_sss=("glosa_sss", "first"), establecimiento=("establecimiento", "first"), months_reported=("months_reported", "max"),
                n_areas=("n_areas", "sum"), discharges=("discharges", "sum"), deaths=("deaths", "sum"), transfers=("transfers", "sum"),
                bed_days_available=("bed_days_available", "sum"), bed_days_occupied=("bed_days_occupied", "sum"), days_of_stay=("days_of_stay", "sum")))
    months = d.groupby(["CODIGO_ESTABLECIMIENTO", "PERIODO"]).MES.nunique().unstack("PERIODO")
    panel = sorted(months.index[months.notna().all(axis=1) & months.eq(12).all(axis=1)].tolist())
    add_control("rem20_panel_size", "2019-2025", 188, len(panel), note="establecimientos con 12 meses reportados en cada año 2019–2025")
    est["in_panel_188"] = est.codigo_establecimiento.isin(panel)
    est["unit"] = "discharges (episodes) and bed-days; activity/capacity, NOT covered population"
    est["geography"] = GEOGRAPHY["rem20"]
    est["source_file"] = path.name
    for c in ["discharges", "deaths", "transfers", "bed_days_available", "bed_days_occupied", "days_of_stay"]:
        est[c] = est[c].round().astype(int)
        ea[c] = ea[c].round().astype(int)
    ea["in_panel_188"] = ea.codigo_establecimiento.isin(panel)
    ea["unit"] = "discharges (episodes) and bed-days per functional area; activity/capacity, NOT covered population"
    ea["geography"] = GEOGRAPHY["rem20"]
    atomic_write_csv(est.sort_values(["year", "codigo_establecimiento"]), TIDY / "rem20_establishment_year.csv")
    atomic_write_csv(ea.sort_values(["year", "codigo_establecimiento", "cod_area_funcional"]), TIDY / "rem20_establishment_area_year.csv")
    rows = []
    for year, g in est.groupby("year"):
        tot, pan = int(g.discharges.sum()), int(g[g.in_panel_188].discharges.sum())
        bt, bp = int(g.bed_days_available.sum()), int(g[g.in_panel_188].bed_days_available.sum())
        rows.append(dict(year=year, establishments_reporting=int(g.codigo_establecimiento.nunique()), establishments_with_12_months=int((g.months_reported == 12).sum()),
                         establishments_panel=int(g.in_panel_188.sum()), discharges_total=tot, discharges_panel_188=pan, retention_discharges=pan / tot,
                         bed_days_available_total=bt, bed_days_available_panel_188=bp, retention_bed_days=bp / bt))
    pan = pd.DataFrame(rows)
    pan["unit"] = "discharges (episodes); bed-days available"
    pan["note"] = "activity/capacity panel; not a population denominator"
    for y, exp in CFG.CONTROLS["rem20_panel_188_retention"].items():
        add_control("rem20_panel_188_retention", y, exp, float(pan.set_index("year").retention_discharges[y]), kind="rate", note="egresos del panel / egresos totales del año")
    atomic_write_csv(pan, TIDY / "rem20_panel.csv")
    members = est[est.in_panel_188].groupby("codigo_establecimiento").agg(establecimiento=("establecimiento", "last"), cod_sss=("cod_sss", "last"),
                                                                           glosa_sss=("glosa_sss", "last"), discharges_2019_2025=("discharges", "sum")).reset_index()
    atomic_write_csv(members, TIDY / "rem20_panel_establishments.csv")
    return est, pan, path


# ---------------------------------------------------------------------------
# 7. Capas de cobertura por año
# ---------------------------------------------------------------------------
def build_coverage(agg2017, comp, fonasa_nat, aps_pan, isapre_nat, rem20_pan):
    nat = agg2017[(agg2017.level == "national") & (agg2017.sex == "TOTAL") & (agg2017.age_group == "TOTAL")].set_index("year").population
    fon_tot = fonasa_nat[fonasa_nat.dimension == "TOTAL"].set_index("year").beneficiaries
    fon_ins = fonasa_nat[(fonasa_nat.dimension == "INSCRITO_APS") & (fonasa_nat.category == "SI")].set_index("year").beneficiaries
    isa = isapre_nat.set_index("year").beneficiarios_total
    aps = aps_pan.set_index("year")
    rem = rem20_pan.set_index("year")
    rows = []
    for y in YEARS:
        r = dict(year=y, ine_population_base2017_30jun=int(nat[y]), ine_population_base2024_national_30jun=comp.set_index("year").base2024_national_30jun.get(y),
                 fonasa_beneficiaries_dec=int(fon_tot[y]), fonasa_inscritos_aps_dec=(int(fon_ins[y]) if y in fon_ins.index else np.nan),
                 isapre_beneficiaries_dec=int(isa[y]), aps_enrolled_dec=int(aps.enrolled_total[y]), aps_enrolled_tramo_AD_dec=int(aps.enrolled_tramo_AD[y]),
                 aps_centres=int(aps.centres_total[y]), aps_panel_1871_enrolled=int(aps.enrolled_panel_1871[y]), aps_panel_1871_retention=float(aps.retention_panel_1871[y]),
                 rem20_establishments_reporting=int(rem.establishments_reporting[y]), rem20_discharges_all=int(rem.discharges_total[y]),
                 rem20_discharges_panel_188=int(rem.discharges_panel_188[y]), rem20_panel_188_retention=float(rem.retention_discharges[y]))
        r["fonasa_plus_isapre"] = r["fonasa_beneficiaries_dec"] + r["isapre_beneficiaries_dec"]
        r["share_fonasa_ine"] = r["fonasa_beneficiaries_dec"] / r["ine_population_base2017_30jun"]
        r["share_isapre_ine"] = r["isapre_beneficiaries_dec"] / r["ine_population_base2017_30jun"]
        r["share_fonasa_plus_isapre_ine"] = r["fonasa_plus_isapre"] / r["ine_population_base2017_30jun"]
        r["share_fonasa_plus_isapre_ine_base2024"] = (r["fonasa_plus_isapre"] / r["ine_population_base2024_national_30jun"]) if pd.notna(r["ine_population_base2024_national_30jun"]) else np.nan
        r["ratio_aps_tramoAD_to_fonasa_inscritos"] = (r["aps_enrolled_tramo_AD_dec"] / r["fonasa_inscritos_aps_dec"]) if pd.notna(r["fonasa_inscritos_aps_dec"]) else np.nan
        r["rem20_discharges_per_1000_ine"] = 1000 * r["rem20_discharges_all"] / r["ine_population_base2017_30jun"]
        rows.append(r)
    cov = pd.DataFrame(rows)
    cov["caveat"] = ("(FONASA+ISAPRE)/INE is NOT an uninsured rate: it mixes December stocks with a 30 June projection, omits other regimes "
                     "(FF.AA., etc.) and double-counting/classification differences; INE is territorial residence, FONASA mixes APS enrolment comuna and domicile, "
                     "APS is comuna of the centre, ISAPRE is administrative comuna; REM-20 is activity, not population")
    atomic_write_csv(cov, TIDY / "coverage_layers_year.csv")
    for y in (2019, 2025):
        exp = {2019: 0.9563, 2025: 0.9724}[y]
        add_control("share_fonasa_plus_isapre_ine", y, exp, round(float(cov.set_index("year").share_fonasa_plus_isapre_ine[y]), 4), kind="rate",
                    note="DATA_REVIEW: 95,63 % (2019) y 97,24 % (2025); no es tasa de no aseguramiento")
    for y in (2019, 2020, 2021, 2022):
        obs = cov.set_index("year").ratio_aps_tramoAD_to_fonasa_inscritos[y]
        add_control("aps_tramoAD_vs_fonasa_inscritos", y, 1.0, round(float(obs), 5), kind="rate", tol_rate=0.002,
                    note="DATA_REVIEW: APS tramos A–D reproduce el total FONASA 'inscrito' con diferencia < 0,2 % (2019–2022)")
    return cov


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tmpdir", default=None, help="directorio temporal para extraer los archivos FONASA (.rar/.zip); por defecto tempfile")
    ap.add_argument("--full-grain", action="store_true", help="escribe además fonasa_beneficiaries_comuna_year_full_grain.csv (año×comuna×sexo×edad×tramo×inscrito; ~60 MB)")
    args = ap.parse_args()
    global ARGS
    ARGS = args
    t0 = time.time()
    tmp_root = Path(args.tmpdir) if args.tmpdir else Path(tempfile.mkdtemp(prefix="study_03_"))
    tmp_root.mkdir(parents=True, exist_ok=True)
    print(f"[{MODULE}] inicio {dt.datetime.now():%Y-%m-%d %H:%M:%S}; tidy -> {TIDY}")

    cw, com17, agg17, ine_path = build_ine_and_crosswalk()
    print(f"  INE base 2017: {len(com17):,} filas comunales; crosswalk {len(cw)} comunas  ({time.time() - t0:.0f} s)")
    sens, comp, sens_paths = build_ine_sensitivity(cw, agg17)
    print(f"  INE sensibilidad: {len(sens):,} filas  ({time.time() - t0:.0f} s)")
    fon_com, fon_nat, fon_src = build_fonasa(cw, tmp_root)
    print(f"  FONASA: {len(fon_com):,} filas armonizadas  ({time.time() - t0:.0f} s)")
    aps_cen, aps_com, aps_pan, aps_src = build_aps(cw)
    print(f"  APS: {len(aps_cen):,} centro-año; {len(aps_com):,} filas comunales  ({time.time() - t0:.0f} s)")
    isa, isa_nat, isa_src = build_isapre(cw)
    print(f"  ISAPRE: {len(isa):,} filas  ({time.time() - t0:.0f} s)")
    rem_est, rem_pan, rem_path = build_rem20()
    print(f"  REM-20: {len(rem_est):,} establecimiento-año  ({time.time() - t0:.0f} s)")
    cov = build_coverage(agg17, comp, fon_nat, aps_pan, isa_nat, rem_pan)

    # nombres de comuna: coincidencias y no coincidentes
    matches = pd.DataFrame([dict(source=v["source"], raw_name=v["raw_name"], normalised=v["normalised"], cut_comuna=v["cut_comuna"], match_method=v["match_method"],
                                 years="|".join(str(y) for y in sorted(v["years"])), n_years=len(v["years"])) for v in _name_matches.values()])
    atomic_write_csv(matches.sort_values(["source", "cut_comuna", "raw_name"]), TIDY / "comuna_name_matches.csv")
    un = pd.DataFrame(list(_unmatched.values())) if _unmatched else pd.DataFrame(columns=["source", "year", "raw_name", "normalised", "rows", "count", "reason"])
    un["count_unit"] = "beneficiaries/enrolled in the unmatched rows"
    atomic_write_csv(un.sort_values(["source", "year", "raw_name"]), TIDY / "comuna_unmatched.csv")
    add_control("comuna_unmatched_geographic_names", "all", 0, int((un.reason != "non-geographic placeholder").sum()),
                note="nombres geográficos sin coincidencia exacta ni alias explícito (deben ser 0; los marcadores no geográficos se listan aparte)")

    # controles
    ctrl = pd.DataFrame(_controls)[["name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"]]
    atomic_write_csv(ctrl, CONTROLS_DIR / f"{MODULE}_controls.csv")
    runtime = time.time() - t0
    prov = [dict(path=str(p), sha256=sha256_file(p), bytes=p.stat().st_size) for p in [ine_path] + sens_paths + fon_src + aps_src + isa_src + [rem_path]]
    atomic_write_json(dict(module=MODULE, script=SCRIPT, run_at=dt.datetime.now().isoformat(timespec="seconds"), runtime_seconds=round(runtime, 1),
                           controls_ok=int((ctrl.status == "ok").sum()), controls_differ=int((ctrl.status != "ok").sum()), sources=prov),
                      CONTROLS_DIR / f"{MODULE}_run.json")
    if not args.tmpdir:
        shutil.rmtree(tmp_root, ignore_errors=True)
    print(ctrl.to_string(index=False, max_colwidth=60))
    print(f"[{MODULE}] fin: {int((ctrl.status == 'ok').sum())}/{len(ctrl)} controles ok; {runtime:.1f} s")


if __name__ == "__main__":
    main()
