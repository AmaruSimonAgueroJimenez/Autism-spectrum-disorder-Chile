#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""15_extra_figures_context.py — módulo 15: láminas y tablas adicionales de contexto (serie E20–E28) para
denominadores, cobertura de aseguramiento, capacidad hospitalaria REM-20, encuestas, educación, comparación
entre fuentes, razón de sexos multifuente, diagnóstico de modelos y sensibilidad a la variante de definición.

Continúa la serie E del material extendido (módulos 11 y 13–14 usan E1–E19); este módulo escribe E20 en adelante.
Lee EXCLUSIVAMENTE las tablas tidy ya verificadas de `lancet_americas/outputs/tidy/` y `outputs/values_<variante>.json`;
no vuelve a leer microdatos ni modifica ningún otro módulo.

Láminas (600 ppp, Okabe–Ito, letras de panel con `common.letter`, sombreado de pandemia con `common.shade_years`,
Ley 21.545 solo como marcador de contexto), en `outputs/<variante>/<idioma>/extra/figures/`:

  figE20_population_structure.png  Estructura poblacional INE: pirámides 2019 y 2025, población 0–19 por región,
                                   base 2017 frente a base 2024 y frente al Censo 2024 por edad, y total nacional.
  figE21_insurance_coverage.png    Cobertura de aseguramiento en detalle: FONASA por tramo; FONASA por edad y sexo;
                                   ISAPRE por edad; inscritos APS por tramo; distribución regional; capas anuales.
                                   Todos los valores son stocks de diciembre (INE es proyección al 30 de junio).
  figE22_rem20_capacity.png        REM-20: egresos y días-cama por año, panel de 188 establecimientos, distribución
                                   por establecimiento, áreas funcionales y relación ecológica capacidad ↔ episodios F84.
  figE23_surveys_detail.png        ENDIDE 2022 y ENCAVI 2023–2024 con diseño complejo: estimaciones por sexo y grupo
                                   etario, efecto de diseño, error estándar relativo con el umbral de 30 %, casos no
                                   ponderados y dominios no estimables (nunca presentados como fiables).
  figE24_education_detail.png      PIE por año y categoría con la regla de armonización, la discrepancia de 2022,
                                   participación en la matrícula PIE y en los postulantes, escuelas especiales y el
                                   desglose por sexo de 2023.
  figE25_junaeb_detail.png         JUNAEB EVE: porcentaje ponderado por nivel, año y sexo con IC, celdas «no
                                   estimable», recuentos no ponderados y el cambio de cuestionario entre años.
  figE26_cross_source.png          Comparación entre fuentes: valor anual indexado a un año base declarado, valor por
                                   100.000 residentes y valor por unidad reportante, en tres paneles con ejes separados.
  figE26b_sex_ratio_multisource.png  Razón hombre:mujer medida en todas las fuentes que informan sexo, con IC 95 %,
                                   líneas de referencia 3:1 y 4:1, tendencia, edad, conteos frente a tasas
                                   estandarizadas, forest del último año y comparación entre variantes.
  figE27_model_diagnostics.png     Ajustado frente a observado, residuos de Pearson por año, dispersión por
                                   especificación y forest de sensibilidad de `models_summary.csv`.
  figE28_variant_sensitivity.png   Sensibilidad de cada cifra a la variante de definición (con_rett vs sin_rett) en
                                   GRD, REM y educación, con diferencias absolutas y relativas.

Tablas acompañantes (una por lámina) en `outputs/<variante>/<idioma>/extra/tables/`:
  E20_population_structure, E21_insurance_coverage, E22_rem20_capacity, E23_surveys_detail, E24_education_detail,
  E25_junaeb_detail, E26_cross_source, E26b_sex_ratio_multisource, E27_model_diagnostics, E28_variant_sensitivity
cada una como `<nombre>.csv` (cadenas formateadas por idioma: coma decimal en es, punto en en; n junto a %;
IC como «lo–hi»; «n/e» donde no es estimable), `<nombre>_numeric.csv` (valores sin formato) y una entrada en
`titles.json` con `title` y `note` (unidad, denominador, cobertura, era de definición, N reportante y archivo fuente).

Controles: `outputs/controls/15_extra_figures_context_controls.csv` (name,key,expected,observed,abs_diff,rel_diff,
status,note) compara los agregados de este módulo contra las tablas tidy ya verificadas y `config.CONTROLS`.
Registro: `outputs/controls/15_extra_figures_context_runlog.json`.

Reglas no negociables respetadas: los recuentos son reconocimiento administrativo, nunca prevalencia ni incidencia;
el resultado GRD es «episodios con F84 documentado» y F84 principal es una serie aparte; las fuentes no se enlazan
por persona (ningún cociente entre fuentes se interpreta como cascada o probabilidad individual); no se atribuye
efecto causal a la Ley 21.545; stocks y flujos nunca comparten eje; lugar de atención y residencia nunca se combinan
sin nota explícita; el panel GRD es 65 fijo / 65-65-65-65-68-72 observado; las personas se cuentan solo dentro del
año; las eras de definición REM nunca se unen con una línea; cero, ausente y «no reportado» son estados distintos;
las celdas con menos de cinco eventos se suprimen en tablas territoriales; los dominios de encuesta con menos de 30
casos o EER > 30 % se marcan y no se presentan como fiables.

Uso: python3 lancet_americas/pipeline/15_extra_figures_context.py
       [--variants con_rett sin_rett] [--langs es en] [--only E20 E26b] [--no-figures] [--no-tables]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
from labels import t as LBL  # noqa: E402,F401
from labels import rem20_area_short as LB_AREA_SHORT  # noqa: E402

MODULE = "15_extra_figures_context"
SCRIPT = "lancet_americas/pipeline/15_extra_figures_context.py"
VARIANTS = ["con_rett", "sin_rett"]
LANGS = list(CFG.LANGUAGES)
YEARS_GRD = list(CFG.YEARS_GRD)          # 2019–2024
YEARS_REM = list(CFG.YEARS_REM)          # 2019–2025
PANDEMIC = list(CFG.PANDEMIC_YEARS)
LAW_X = CFG.LAW_YEAR - 0.30              # marzo de 2023 sobre un eje de años centrados
PER = 100_000.0
Z95 = float(stats.norm.ppf(0.975))
OKABE = C.OKABE
GREY = "#7f8c8d"
NE = {"es": "n/e", "en": "n/e"}
WARNINGS: list[str] = []
T0 = time.time()

FIG_NAMES = {
    "E20": "figE20_population_structure", "E21": "figE21_insurance_coverage", "E22": "figE22_rem20_capacity",
    "E23": "figE23_surveys_detail", "E24": "figE24_education_detail", "E25": "figE25_junaeb_detail",
    "E26": "figE26_cross_source", "E26b": "figE26b_sex_ratio_multisource", "E27": "figE27_model_diagnostics",
    "E28": "figE28_variant_sensitivity",
}
TABLE_NAMES = {
    "E20": "E20_population_structure", "E21": "E21_insurance_coverage", "E22": "E22_rem20_capacity",
    "E23": "E23_surveys_detail", "E24": "E24_education_detail", "E25": "E25_junaeb_detail",
    "E26": "E26_cross_source", "E26b": "E26b_sex_ratio_multisource", "E27": "E27_model_diagnostics",
    "E28": "E28_variant_sensitivity",
}
PLATES = list(FIG_NAMES)
CONTROLS_DIR = CFG.OUT / "controls"      # CFG.CONTROLS es el diccionario de valores esperados, no un directorio
CONTROLS_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {MODULE}: {msg}", flush=True)


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    log(f"AVISO — {msg}")


# ===========================================================================
# Formato bilingüe
# ===========================================================================
def num(x, dec=0, lang="es"):
    if x is None:
        return NE[lang]
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NE[lang]
    if not np.isfinite(v):
        return NE[lang]
    return C.fmt_number(v, dec, lang)


def pct(x, lang="es", dec=1):
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return NE[lang]
    return C.fmt_number(float(x), dec, lang) + (" %" if lang == "es" else "%")


def n_pct(n, p, lang="es", dec=1):
    return f"{num(n, 0, lang)} ({pct(p, lang, dec)})"


def ci(lo, hi, dec=2, lang="es"):
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi) or not np.isfinite(float(lo)) or not np.isfinite(float(hi)):
        return NE[lang]
    return f"{num(lo, dec, lang)}–{num(hi, dec, lang)}"


def val_ci(v, lo, hi, dec=2, lang="es"):
    if v is None or pd.isna(v) or not np.isfinite(float(v)):
        return NE[lang]
    return f"{num(v, dec, lang)} ({ci(lo, hi, dec, lang)})"


def fmt_axis(ax, lang, which="y", dec=0):
    import matplotlib.ticker as mticker
    f = mticker.FuncFormatter(lambda v, _p: C.fmt_number(v, dec, lang))
    (ax.yaxis if which == "y" else ax.xaxis).set_major_formatter(f)


def log_axis_fmt(ax, lang, which="y"):
    import matplotlib.ticker as mticker
    axis = ax.yaxis if which == "y" else ax.xaxis
    def _f(v, _p):
        if v <= 0:
            return ""
        dec = 0 if v >= 1 else min(4, max(1, int(np.ceil(-np.log10(v)))))
        return C.fmt_number(v, dec, lang)
    axis.set_major_formatter(mticker.FuncFormatter(_f))
    axis.set_minor_formatter(mticker.NullFormatter())


def merge_json(path: Path, new: dict) -> None:
    current: dict = {}
    if Path(path).is_file():
        try:
            current = json.loads(Path(path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = {}
    if not isinstance(current, dict):
        current = {}
    current.update(new)
    C.atomic_write_json(current, Path(path))


def out_dir(variant: str, lang: str, kind: str) -> Path:
    p = CFG.OUT / variant / lang / "extra" / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_pair(tdir: Path, name: str, formatted: pd.DataFrame, numeric: pd.DataFrame) -> list[str]:
    return [str(C.atomic_write_csv(formatted, tdir / f"{name}.csv", encoding="utf-8-sig")),
            str(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv"))]


# ===========================================================================
# Estadística de razones (todas con IC 95 %)
# ===========================================================================
def ratio_counts_ci(m, f, alpha=0.05):
    """Razón hombre:mujer de dos recuentos independientes, con límites binomiales exactos (Clopper–Pearson)
    sobre p = m/(m+f) transformados a p/(1-p). Devuelve (razón, lo, hi); NaN cuando no es estimable."""
    try:
        m, f = float(m), float(f)
    except (TypeError, ValueError):
        return np.nan, np.nan, np.nan
    if not (np.isfinite(m) and np.isfinite(f)) or m < 0 or f < 0 or (m + f) <= 0:
        return np.nan, np.nan, np.nan
    n = m + f
    lo_p = 0.0 if m <= 0 else float(stats.beta.ppf(alpha / 2, m, n - m + 1))
    hi_p = 1.0 if f <= 0 else float(stats.beta.ppf(1 - alpha / 2, m + 1, n - m))
    r = np.inf if f <= 0 else m / f
    lo = 0.0 if lo_p <= 0 else lo_p / (1 - lo_p)
    hi = np.inf if hi_p >= 1 else hi_p / (1 - hi_p)
    if not np.isfinite(r):
        return np.nan, np.nan, np.nan          # sin mujeres en la celda: la razón no es estimable
    return r, lo, (hi if np.isfinite(hi) else np.nan)


def ratio_rates_ci(r1, lo1, hi1, r2, lo2, hi2, alpha=0.05):
    """Razón de dos tasas (p. ej. estandarizadas por edad) con intervalo log-normal; el EE de log(tasa) se
    aproxima a partir de los límites publicados: se = (log hi − log lo)/(2 z)."""
    vals = [r1, lo1, hi1, r2, lo2, hi2]
    if any(v is None or pd.isna(v) or float(v) <= 0 for v in vals):
        return np.nan, np.nan, np.nan
    z = float(stats.norm.ppf(1 - alpha / 2))
    se1 = (np.log(float(hi1)) - np.log(float(lo1))) / (2 * z)
    se2 = (np.log(float(hi2)) - np.log(float(lo2))) / (2 * z)
    rr = float(r1) / float(r2)
    se = float(np.sqrt(se1 ** 2 + se2 ** 2))
    return rr, rr * np.exp(-z * se), rr * np.exp(z * se)


def ratio_props_ci(p1, se1, p2, se2, alpha=0.05):
    """Razón de dos proporciones estimadas con diseño complejo (o con EE binomial), método delta sobre el
    logaritmo. Los dominios se tratan como independientes: es una aproximación, declarada en la nota."""
    for v in (p1, se1, p2, se2):
        if v is None or pd.isna(v):
            return np.nan, np.nan, np.nan
    p1, se1, p2, se2 = float(p1), float(se1), float(p2), float(se2)
    if p1 <= 0 or p2 <= 0:
        return np.nan, np.nan, np.nan
    z = float(stats.norm.ppf(1 - alpha / 2))
    rr = p1 / p2
    se = float(np.sqrt((se1 / p1) ** 2 + (se2 / p2) ** 2))
    return rr, rr * np.exp(-z * se), rr * np.exp(z * se)


def wilson_se(k, n):
    """EE binomial simple de una proporción (para las series escolares sin ponderador publicado)."""
    if n is None or pd.isna(n) or float(n) <= 0 or k is None or pd.isna(k):
        return np.nan, np.nan
    p = float(k) / float(n)
    return p, float(np.sqrt(max(p * (1 - p), 0.0) / float(n)))


def poisson_rate(count, denom, per=PER):
    count = np.asarray(count, dtype=float)
    denom = np.asarray(denom, dtype=float)
    lo = np.where(count > 0, stats.chi2.ppf(0.025, 2 * count) / 2.0, 0.0)
    hi = stats.chi2.ppf(0.975, 2 * (count + 1)) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        return per * count / denom, per * lo / denom, per * hi / denom


# ===========================================================================
# Carga de tablas tidy (solo lectura)
# ===========================================================================
TIDY_INPUTS = [
    "ine_population_region_national_year_age_sex", "ine_population_base_comparison", "ine_population_sensitivity",
    "fonasa_beneficiaries_national_year", "fonasa_beneficiaries_comuna_year", "fonasa_beneficiaries_comuna_tramo_year",
    "aps_enrolment_comuna_year", "aps_panel", "isapre_beneficiaries_national_year", "isapre_beneficiaries_comuna_year",
    "rem20_establishment_year", "rem20_establishment_area_year", "rem20_panel", "coverage_layers_year",
    "survey_estimates", "junaeb_tea_year_level", "pie_series", "education_summary_year",
    "models_summary", "models_fitted", "models_population_rates", "models_a05_standardised_rates",
    "models_convergence_index", "grd_year_summary", "grd_age_sex_year", "grd_hospital_year",
    "rem_pathway_annual", "rem_a05_age_sex_annual", "deis_age_sex_year", "deis_year_summary",
]
OPTIONAL_INPUTS = {"ine_population_sensitivity", "deis_year_summary", "fonasa_beneficiaries_comuna_tramo_year"}


def load() -> SimpleNamespace:
    d = {}
    for name in TIDY_INPUTS:
        path = CFG.TIDY / f"{name}.csv"
        if not path.is_file():
            if name in OPTIONAL_INPUTS:
                warn(f"falta la tabla opcional {name}.csv; los paneles que dependen de ella se marcan «no estimable»")
                d[name] = pd.DataFrame()
                continue
            raise FileNotFoundError(f"Falta {path}; ejecute el módulo del pipeline que la produce.")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d[name] = pd.read_csv(path, low_memory=False)
    # P2/P6 por sexo: COL02 = Hombres, COL03 = Mujeres del diccionario REM (rem_code_dictionary_check.csv).
    p_path = CFG.TIDY / "rem_pathway_tidy.csv"
    if p_path.is_file():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            d["rem_pathway_tidy"] = pd.read_csv(
                p_path, usecols=["year", "series", "module", "code", "month", "in_era", "IdEstablecimiento",
                                 "col01_num", "col02_num", "col03_num", "state"], low_memory=False)
    else:
        warn("falta rem_pathway_tidy.csv; la razón de sexos de P2/P6 se marca «no estimable»")
        d["rem_pathway_tidy"] = pd.DataFrame()
    values = {}
    for v in VARIANTS:
        vp = CFG.OUT / f"values_{v}.json"
        values[v] = json.loads(vp.read_text(encoding="utf-8")) if vp.is_file() else {}
        if not values[v]:
            warn(f"falta values_{v}.json; las anotaciones que lo usan quedan vacías")
    d["values"] = values
    return SimpleNamespace(**{ALIAS.get(k, k): v for k, v in d.items()})


ALIAS = {
    "ine_population_region_national_year_age_sex": "ine", "ine_population_base_comparison": "ine_bases",
    "ine_population_sensitivity": "ine_sens",
    "fonasa_beneficiaries_national_year": "fonasa_nat", "fonasa_beneficiaries_comuna_year": "fonasa_com",
    "fonasa_beneficiaries_comuna_tramo_year": "fonasa_tramo",
    "aps_enrolment_comuna_year": "aps_com", "aps_panel": "aps_panel",
    "isapre_beneficiaries_national_year": "isapre_nat", "isapre_beneficiaries_comuna_year": "isapre_com",
    "rem20_establishment_year": "r20_estab", "rem20_establishment_area_year": "r20_area", "rem20_panel": "r20_panel",
    "coverage_layers_year": "coverage", "survey_estimates": "surveys", "junaeb_tea_year_level": "junaeb",
    "pie_series": "pie", "education_summary_year": "edu",
    "models_summary": "mod", "models_fitted": "fitted", "models_population_rates": "pop_rates",
    "models_a05_standardised_rates": "a05_asr", "models_convergence_index": "conv",
    "grd_year_summary": "grd", "grd_age_sex_year": "grd_as", "grd_hospital_year": "grd_hosp",
    "rem_pathway_annual": "rem", "rem_a05_age_sex_annual": "a05_as", "rem_pathway_tidy": "rem_tidy",
    "deis_age_sex_year": "deis_as", "deis_year_summary": "deis",
}


# ===========================================================================
# Texto bilingüe (todo rótulo vive aquí; nunca literales sueltos en los paneles)
# ===========================================================================
TX = {
    "year": {"es": "Año", "en": "Year"},
    "persons": {"es": "Personas", "en": "Persons"},
    "males": {"es": "Hombres", "en": "Males"},
    "females": {"es": "Mujeres", "en": "Females"},
    "age_group": {"es": "Grupo etario", "en": "Age group"},
    "region": {"es": "Región", "en": "Region"},
    "ci95": {"es": "IC 95 %", "en": "95% CI"},
    "ratio_mf": {"es": "Razón hombre:mujer", "en": "Male-to-female ratio"},
    "source": {"es": "Fuente", "en": "Source"},
    "unit": {"es": "Unidad", "en": "Unit"},
    "not_estimable": {"es": "no estimable", "en": "not estimable"},
    "pandemic": {"es": "Pandemia 2020–2021 (disrupción del reporte)", "en": "2020–2021 pandemic (reporting disruption)"},
    "law": {"es": "Ley 21.545 (marzo 2023, contexto)", "en": "Law 21.545 (March 2023, context)"},
    # Marcas dentro del panel: en un panel de media página el rótulo largo no cabe (el de la ley,
    # rotado 90°, medía más que el alto del panel). El texto completo va en la leyenda de la lámina.
    "law_mark": {"es": "Ley 21.545 (2023)", "en": "Law 21.545 (2023)"},
    "pandemic_mark": {"es": "2020–2021 (pandemia)", "en": "2020–2021 (pandemic)"},
    "dec_stock": {"es": "Stock de diciembre", "en": "December stock"},
    # --- E20 -------------------------------------------------------------------------------------
    "e20_title": {"es": "Figura E20. Estructura de la población de referencia (INE), 2019–2025",
                  "en": "Figure E20. Structure of the reference population (INE), 2019–2025"},
    "e20_a": {"es": "A. Pirámide de población, 2019 (base Censo 2017)", "en": "A. Population pyramid, 2019 (Censo 2017 base)"},
    "e20_b": {"es": "B. Pirámide de población, 2025 (base Censo 2017)", "en": "B. Population pyramid, 2025 (Censo 2017 base)"},
    "e20_c": {"es": "C. Población de 0 a 19 años por región, 2019 y 2025", "en": "C. Population aged 0–19 by region, 2019 and 2025"},
    "e20_d": {"es": "D. Base 2017 frente a base 2024 (nacional)", "en": "D. 2017 base versus 2024 base (national)"},
    "e20_e": {"es": "E. Base 2017 (2024) frente a Censo 2024, por edad", "en": "E. 2017 base (2024) versus Censo 2024, by age"},
    "e20_f": {"es": "F. Población nacional y proporción de 0 a 19 años", "en": "F. National population and share aged 0–19"},
    "e20_pct_axis": {"es": "Proporción de la población total (%)", "en": "Share of total population (%)"},
    "e20_pop_axis": {"es": "Población (millones)", "en": "Population (millions)"},
    "e20_pop_thousands": {"es": "Población 0–19 (miles)", "en": "Population aged 0–19 (thousands)"},
    "e20_pop_thousands_all": {"es": "Población (miles)", "en": "Population (thousands)"},
    "e20_ratio_axis": {"es": "Razón base 2024 / base 2017", "en": "Ratio 2024 base / 2017 base"},
    "e20_share_axis": {"es": "0–19 años (% del total)", "en": "Aged 0–19 (% of total)"},
    "e20_base2017": {"es": "Base Censo 2017 (30 jun)", "en": "Censo 2017 base (30 Jun)"},
    "e20_base2024": {"es": "Base 2024 (30 jun)", "en": "2024 base (30 Jun)"},
    "e20_censo2024": {"es": "Censo 2024 (enumerado)", "en": "Censo 2024 (enumerated)"},
    "e20_note_bases": {"es": "Las bases censales nunca se funden: la base 2017 es el denominador principal.",
                       "en": "Census bases are never merged: the 2017 base is the primary denominator."},
    # --- E21 -------------------------------------------------------------------------------------
    "e21_title": {"es": "Figura E21. Cobertura de aseguramiento en detalle (stocks de diciembre), 2019–2025",
                  "en": "Figure E21. Insurance coverage in detail (December stocks), 2019–2025"},
    "e21_a": {"es": "A. FONASA por tramo, total nacional", "en": "A. FONASA by tramo, national total"},
    "e21_b": {"es": "B. FONASA por edad y sexo, último año", "en": "B. FONASA by age and sex, latest year"},
    "e21_c": {"es": "C. ISAPRE por edad, primer y último año", "en": "C. ISAPRE by age, first and last year"},
    "e21_d": {"es": "D. Inscritos APS por tramo y centros reportantes", "en": "D. APS enrolment by tramo and reporting centres"},
    "e21_e": {"es": "E. Distribución regional del aseguramiento, último año", "en": "E. Regional distribution of insurance, latest year"},
    "e21_f": {"es": "F. Capas de cobertura por año", "en": "F. Coverage layers by year"},
    "e21_benef_axis": {"es": "Beneficiarios (millones)", "en": "Beneficiaries (millions)"},
    "e21_benef_thousands": {"es": "Beneficiarios (miles)", "en": "Beneficiaries (thousands)"},
    "e21_enrolled_axis": {"es": "Inscritos APS (millones)", "en": "APS enrolled (millions)"},
    "e21_centres_axis": {"es": "Centros APS reportantes", "en": "Reporting APS centres"},
    "e21_share_axis": {"es": "% de la población INE de la región", "en": "% of the region's INE population"},
    "e21_tramo": {"es": "Tramo FONASA", "en": "FONASA tramo"},
    "e21_note_stock": {"es": "Stocks de diciembre; INE es una proyección al 30 de junio: la razón es indicativa, no una tasa de no aseguramiento.",
                       "en": "December stocks; INE is a 30 June projection: the ratio is indicative, not an uninsured rate."},
    "e21_note_geo": {"es": "Geografías distintas: FONASA mezcla comuna de inscripción APS y domicilio, APS localiza el centro e ISAPRE la comuna administrativa.",
                     "en": "Different geographies: FONASA mixes APS-enrolment comuna and domicile, APS locates the centre and ISAPRE the administrative comuna."},
    # --- E22 -------------------------------------------------------------------------------------
    "e22_title": {"es": "Figura E22. Capacidad y actividad hospitalaria REM-20, 2019–2025",
                  "en": "Figure E22. REM-20 hospital capacity and activity, 2019–2025"},
    "e22_a": {"es": "A. Egresos: todos y panel de 188", "en": "A. Discharges: all and 188-panel"},
    "e22_b": {"es": "B. Días-cama y ocupación", "en": "B. Bed-days and occupancy"},
    "e22_c": {"es": "C. Egresos por establecimiento", "en": "C. Discharges per establishment"},
    "e22_d": {"es": "D. Retención del panel de 188", "en": "D. Retention of the 188-panel"},
    "e22_e": {"es": "E. Días-cama por área funcional", "en": "E. Bed-days by functional area"},
    "e22_f": {"es": "F. Capacidad y episodios F84 (ecológico)", "en": "F. Capacity and F84 episodes (ecological)"},
    "e22_disch_axis": {"es": "Egresos (millones)", "en": "Discharges (millions)"},
    "e22_disch_axis_n": {"es": "Egresos por establecimiento", "en": "Discharges per establishment"},
    "e22_bed_axis": {"es": "Días-cama (millones)", "en": "Bed-days (millions)"},
    "e22_occ_axis": {"es": "Ocupación (%)", "en": "Occupancy (%)"},
    "e22_ret_axis": {"es": "Retención del panel (%)", "en": "Panel retention (%)"},
    "e22_estab_axis": {"es": "Establecimientos reportantes", "en": "Reporting establishments"},
    "e22_f84_axis": {"es": "Episodios GRD con F84 documentado", "en": "GRD episodes with documented F84"},
    "e22_area_axis": {"es": "Días-cama disponibles (miles)", "en": "Available bed-days (thousands)"},
    "e22_eco_warn": {"es": "ADVERTENCIA ECOLÓGICA: la asociación es entre establecimientos, no entre personas; no describe riesgo individual.",
                     "en": "ECOLOGICAL WARNING: the association is between establishments, not persons; it does not describe individual risk."},
    "e22_note_unit": {"es": "REM-20 mide actividad y capacidad, nunca población cubierta.",
                      "en": "REM-20 measures activity and capacity, never covered population."},
    # --- E23 -------------------------------------------------------------------------------------
    "e23_title": {"es": "Figura E23. Encuestas poblacionales con diseño complejo: ENDIDE 2022 y ENCAVI 2023–2024",
                  "en": "Figure E23. Population surveys with complex design: ENDIDE 2022 and ENCAVI 2023–2024"},
    "e23_a": {"es": "A. ENDIDE 2022, adultos de 18 años o más", "en": "A. ENDIDE 2022, adults aged 18 and over"},
    "e23_b": {"es": "B. ENDIDE 2022, NNA de 2 a 17 años", "en": "B. ENDIDE 2022, children and adolescents aged 2–17"},
    "e23_c": {"es": "C. ENCAVI 2023–2024, personas de 15 años o más", "en": "C. ENCAVI 2023–2024, persons aged 15 and over"},
    "e23_d": {"es": "D. Efecto de diseño (DEFF) por dominio", "en": "D. Design effect (DEFF) by domain"},
    "e23_e": {"es": "E. Error estándar relativo por dominio", "en": "E. Relative standard error by domain"},
    "e23_f": {"es": "F. Casos no ponderados y tamaño del dominio", "en": "F. Unweighted cases and domain size"},
    "e23_prop_axis": {"es": "Proporción ponderada (%)", "en": "Weighted proportion (%)"},
    "e23_deff_axis": {"es": "DEFF", "en": "DEFF"},
    "e23_rse_axis": {"es": "Error estándar relativo (%)", "en": "Relative standard error (%)"},
    "e23_n_axis": {"es": "Casos no ponderados", "en": "Unweighted cases"},
    "e23_imprecise": {"es": "Dominio impreciso (EER > 30 % o < 30 casos): no se presenta como fiable",
                      "en": "Imprecise domain (RSE > 30% or < 30 cases): not presented as reliable"},
    "e23_adequate": {"es": "Dominio adecuado", "en": "Adequate domain"},
    "e23_no_region": {"es": "Dominios regionales: no estimados (el tamaño efectivo no los sostiene); no se desagrega a comuna.",
                      "en": "Regional domains: not estimated (effective sample does not support them); no comuna disaggregation."},
    "e23_rse_line": {"es": "Umbral 30 %", "en": "30% threshold"},
    "e23_n30": {"es": "Umbral de 30 casos", "en": "30-case threshold"},
    # --- E24 -------------------------------------------------------------------------------------
    "e24_title": {"es": "Figura E24. Reconocimiento educativo del autismo: PIE y escuelas especiales, 2019–2025",
                  "en": "Figure E24. Educational recognition of autism: PIE and special schools, 2019–2025"},
    "e24_a": {"es": "A. Series PIE por definición y fuente", "en": "A. PIE series by definition and source"},
    "e24_b": {"es": "B. Discrepancia de 2022 en el PIE armonizado", "en": "B. The 2022 discrepancy in harmonised PIE"},
    "e24_c": {"es": "C. PIE TEA como proporción de la matrícula PIE y de los postulantes", "en": "C. PIE autism as a share of PIE enrolment and of applicants"},
    "e24_d": {"es": "D. Escuelas especiales y total SINACES", "en": "D. Special schools and SINACES total"},
    "e24_e": {"es": "E. Desglose por sexo, 2023 (único año publicado)", "en": "E. Sex split, 2023 (the only published year)"},
    "e24_f": {"es": "F. Ingreso regular y excepcional al PIE", "en": "F. Regular and exceptional entry to PIE"},
    "e24_students": {"es": "Estudiantes", "en": "Students"},
    "e24_students_thousands": {"es": "Estudiantes (miles)", "en": "Students (thousands)"},
    "e24_share_axis": {"es": "Proporción (%)", "en": "Share (%)"},
    "e24_note_harm": {"es": "Regla de armonización: TEA estricto + TEA-Asperger (Apuntes 60, 2019–2023); SINACES publica el total armonizado 2022–2025.",
                      "en": "Harmonisation rule: strict autism + autism-Asperger (Apuntes 60, 2019–2023); SINACES publishes the harmonised total for 2022–2025."},
    # --- E25 -------------------------------------------------------------------------------------
    "e25_title": {"es": "Figura E25. JUNAEB EVE: reporte de cuidadores en cohortes escolares seleccionadas, 2019–2025",
                  "en": "Figure E25. JUNAEB EVE: caregiver report in selected school cohorts, 2019–2025"},
    "e25_a": {"es": "A. Porcentaje ponderado por nivel y año", "en": "A. Weighted percentage by level and year"},
    "e25_b": {"es": "B. Porcentaje por sexo, nivel y año", "en": "B. Percentage by sex, level and year"},
    "e25_c": {"es": "C. Estudiantes en el dominio y casos con TEA", "en": "C. Students in the domain and autism cases"},
    "e25_d": {"es": "D. Ponderado frente a no ponderado", "en": "D. Weighted versus unweighted"},
    "e25_e": {"es": "E. Razón hombre:mujer por nivel y año", "en": "E. Male-to-female ratio by level and year"},
    "e25_f": {"es": "F. Disponibilidad del ítem y del ponderador por año", "en": "F. Item and weight availability by year"},
    "e25_pct_axis": {"es": "Porcentaje ponderado (%)", "en": "Weighted percentage (%)"},
    "e25_students_axis": {"es": "Estudiantes (miles)", "en": "Students (thousands)"},
    "e25_note_junaeb": {"es": "JUNAEB no es prevalencia nacional: son cohortes escolares seleccionadas y reporte de cuidadores.",
                        "en": "JUNAEB is not national prevalence: selected school cohorts with caregiver report."},
    "e25_no_item": {"es": "Sin ítem TEA", "en": "No autism item"},
    "e25_unw_only": {"es": "Sin ponderador publicado", "en": "No published weight"},
    "e25_weighted": {"es": "Ponderado", "en": "Weighted"},
    "e25_empty_var": {"es": "Variable vacía", "en": "Empty variable"},
    # --- E26 -------------------------------------------------------------------------------------
    "e26_title": {"es": "Figura E26. Comparación entre sistemas administrativos: índice, tasa poblacional y valor por unidad reportante",
                  "en": "Figure E26. Comparison across administrative systems: index, population rate and value per reporting unit"},
    "e26_a": {"es": "A. Valor anual indexado al año base declarado", "en": "A. Annual value indexed to the stated base year"},
    "e26_b": {"es": "B. Valor por 100.000 residentes (INE, base 2017)", "en": "B. Value per 100,000 residents (INE, 2017 base)"},
    "e26_c": {"es": "C. Valor por unidad reportante", "en": "C. Value per reporting unit"},
    "e26_index_axis": {"es": "Índice (año base = 100)", "en": "Index (base year = 100)"},
    "e26_rate_axis": {"es": "Por 100.000 residentes", "en": "Per 100,000 residents"},
    "e26_unit_axis": {"es": "Valor por unidad reportante", "en": "Value per reporting unit"},
    "e26_units_differ": {"es": "LAS UNIDADES DIFIEREN: episodios, ingresos, personas bajo control y estudiantes no son intercambiables; los ejes son separados y no hay enlace por persona entre fuentes.",
                         "en": "UNITS DIFFER: episodes, entries, persons under control and students are not interchangeable; axes are separate and there is no person-level linkage across sources."},
    # --- E26b ------------------------------------------------------------------------------------
    "e26b_title": {"es": "Figura E26b. Razón hombre:mujer del reconocimiento administrativo del autismo en todas las fuentes que informan sexo",
                   "en": "Figure E26b. Male-to-female ratio of administrative autism recognition in every source that reports sex"},
    "e26b_a": {"es": "A. Tendencia de la razón por fuente", "en": "A. Trend of the ratio by source"},
    "e26b_b": {"es": "B. Razón por grupo etario y fuente", "en": "B. Ratio by age group and source"},
    "e26b_c": {"es": "C. Razón de conteos frente a razón de tasas estandarizadas", "en": "C. Ratio of counts versus ratio of standardised rates"},
    "e26b_d": {"es": "D. Forest del último año por fuente", "en": "D. Forest of the latest year by source"},
    "e26b_e": {"es": "E. Razón en las dos variantes de definición de caso", "en": "E. Ratio in the two case-definition variants"},
    "e26b_f": {"es": "F. Numeradores por sexo que sostienen cada razón", "en": "F. Sex-specific numerators behind each ratio"},
    "e26b_ratio_axis": {"es": "Razón hombre:mujer (escala log)", "en": "Male-to-female ratio (log scale)"},
    "e26b_count_axis": {"es": "Razón de conteos", "en": "Ratio of counts"},
    "e26b_asr_axis": {"es": "Razón de tasas estandarizadas por edad", "en": "Ratio of age-standardised rates"},
    "e26b_ref3": {"es": "Referencia 3:1", "en": "3:1 reference"},
    "e26b_ref4": {"es": "Referencia 4:1", "en": "4:1 reference"},
    "e26b_no_link": {"es": "Las fuentes NO se enlazan por persona y miden cosas distintas (episodios, personas, ingresos, estudiantes, encuestados): las razones no son comparables entre sí como si midieran lo mismo.",
                     "en": "Sources are NOT person-linked and measure different things (episodes, persons, entries, students, respondents): the ratios are not comparable as if they measured the same thing."},
    "e26b_ref_note": {"es": "Las líneas 3:1 y 4:1 son referencias de la literatura clínica, no un valor esperado de estos registros.",
                      "en": "The 3:1 and 4:1 lines are clinical-literature references, not an expected value for these registries."},
    # --- E27 -------------------------------------------------------------------------------------
    "e27_title": {"es": "Figura E27. Diagnóstico de los modelos cuasi-Poisson y sensibilidad entre especificaciones",
                  "en": "Figure E27. Quasi-Poisson model diagnostics and sensitivity across specifications"},
    "e27_a": {"es": "A. Ajustado frente a observado", "en": "A. Fitted versus observed"},
    "e27_b": {"es": "B. Residuos de Pearson por año", "en": "B. Pearson residuals by year"},
    "e27_c": {"es": "C. Dispersión por especificación", "en": "C. Dispersion by specification"},
    "e27_d": {"es": "D. Forest de sensibilidad: CPA por especificación", "en": "D. Sensitivity forest: APC by specification"},
    "e27_e": {"es": "E. Durbin–Watson por especificación", "en": "E. Durbin–Watson by specification"},
    "e27_f": {"es": "F. CPA de la especificación principal por estimando", "en": "F. APC of the main specification by estimand"},
    "e27_obs_axis": {"es": "Recuento observado", "en": "Observed count"},
    "e27_fit_axis": {"es": "Recuento ajustado", "en": "Fitted count"},
    "e27_resid_axis": {"es": "Residuo de Pearson", "en": "Pearson residual"},
    "e27_disp_axis": {"es": "Dispersión (χ² de Pearson / gl)", "en": "Dispersion (Pearson χ² / df)"},
    "e27_apc_axis": {"es": "Cambio porcentual anual (%)", "en": "Annual percent change (%)"},
    "e27_dw_axis": {"es": "Durbin–Watson", "en": "Durbin–Watson"},
    "e27_dw_note": {"es": "Con menos de 8 puntos, Durbin–Watson es indicativo y no concluyente.",
                    "en": "With fewer than 8 points, Durbin–Watson is indicative and not conclusive."},
    "e27_no_causal": {"es": "Ninguna especificación estima un efecto de la Ley 21.545.",
                      "en": "No specification estimates an effect of Law 21.545."},
    # --- E28 -------------------------------------------------------------------------------------
    "e28_title": {"es": "Figura E28. Sensibilidad de cada serie a la variante de definición de caso (con Rett frente a sin Rett)",
                  "en": "Figure E28. Sensitivity of every series to the case-definition variant (with versus without Rett)"},
    "e28_a": {"es": "A. GRD: episodios con F84 documentado", "en": "A. GRD: episodes with documented F84"},
    "e28_b": {"es": "B. REM A05: ingresos por familia TGD", "en": "B. REM A05: PDD-family entries"},
    "e28_c": {"es": "C. REM P6: población bajo control en diciembre", "en": "C. REM P6: December population under control"},
    "e28_d": {"es": "D. DEIS: egresos con F84 principal", "en": "D. DEIS: discharges with principal F84"},
    "e28_e": {"es": "E. Diferencia absoluta con_rett − sin_rett", "en": "E. Absolute difference con_rett − sin_rett"},
    "e28_f": {"es": "F. Diferencia relativa (%)", "en": "F. Relative difference (%)"},
    "e28_abs_axis": {"es": "Diferencia absoluta (casos)", "en": "Absolute difference (cases)"},
    "e28_rel_axis": {"es": "Diferencia relativa (%)", "en": "Relative difference (%)"},
    "e28_identical": {"es": "Series idénticas en ambas variantes: educación, encuestas, A03/A27/A28, P2 y autismo estricto.",
                      "en": "Series identical in both variants: education, surveys, A03/A27/A28, P2 and strict autism."},
    "e28_con": {"es": "con Rett (F84 completo)", "en": "with Rett (full F84)"},
    "e28_sin": {"es": "sin Rett (F84 excepto F84.2)", "en": "without Rett (F84 except F84.2)"},
}


def tr(key: str, lang: str) -> str:
    return TX[key][lang]


def reserve_band(ax, frac: float = 0.16, side: str = "top") -> None:
    """Abre una banda VACÍA del `frac` del alto del panel arriba (o abajo) sin comprimir el dato.

    Es la forma de que un rótulo de contexto —la banda 2020–2021, la marca de la Ley— no se imprima
    encima de la serie que acompaña. En eje logarítmico la banda se abre multiplicando, para que mida
    en la lámina lo mismo que en un eje lineal."""
    lo, hi = ax.get_ylim()
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        return
    inverted = hi < lo
    a, b = (hi, lo) if inverted else (lo, hi)
    if ax.get_yscale() == "log":
        if a <= 0 or b <= 0:
            return
        grow = (b / a) ** float(frac)
        a, b = (a / grow, b) if side == "bottom" else (a, b * grow)
    else:
        d = (b - a) * float(frac)
        a, b = (a - d, b) if side == "bottom" else (a, b + d)
    ax.set_ylim((b, a) if inverted else (a, b))


def context_markers(ax, lang, law_y=0.96, pandemic_y=0.90, law=True, pandemic=True, xmin=None, xmax=None,
                    pandemic_x=0.02, band="top", reserve=0.16):
    """Sombreado de pandemia y marcador vertical de la Ley 21.545 (contexto, nunca intervención).

    Los dos rótulos van en una BANDA RESERVADA, arriba o abajo del panel según dónde haya sitio, y se
    escriben en horizontal. Escritos dentro del área de datos —y con recuadro blanco, que es lo que les
    pone el motor antes de guardar— tapaban la serie que acompañan: hasta el 53 % de una serie en S39 (a)
    y una barra de cada tres en S37 (a)-(b). El rótulo de la Ley, además, iba girado 90°: ocupaba un
    cuarto del alto del panel y ninguna banda razonable le daba sitio. `law_y` y `pandemic_y` se aceptan
    por compatibilidad y ya no fijan la altura: la fija la banda.
    """
    if reserve:
        reserve_band(ax, reserve, side="bottom" if band == "bottom" else "top")
    y = 0.012 if band == "bottom" else 0.988
    va = "bottom" if band == "bottom" else "top"
    years = [y_ for y_ in PANDEMIC if (xmin is None or y_ >= xmin) and (xmax is None or y_ <= xmax)]
    if pandemic:
        C.shade_years(ax, years)
        if years:
            # El rótulo va CENTRADO sobre la banda que nombra: así se lee sin buscar a qué se refiere.
            ax.text(0.5 * (min(years) + max(years)), y, tr("pandemic_mark", lang),
                    transform=ax.get_xaxis_transform(), fontsize=6.2, color="#555555", va=va, ha="center",
                    zorder=6)
    if law and (xmin is None or LAW_X >= xmin - 0.5) and (xmax is None or LAW_X <= xmax + 0.5):
        ax.axvline(LAW_X, color="#333333", ls=":", lw=1.1, zorder=0)
        x0, x1 = ax.get_xlim()
        frac = (LAW_X - x0) / (x1 - x0) if x1 != x0 else 0.5
        ha = "left" if frac < 0.60 else "right"
        ax.text(LAW_X, y, (" " if ha == "left" else "") + tr("law_mark", lang) + ("" if ha == "left" else " "),
                transform=ax.get_xaxis_transform(), fontsize=6.2, color="#333333", va=va, ha=ha, zorder=6)


# ===========================================================================
# Preparación de datos (una vez por corrida; independiente del idioma)
# ===========================================================================
AGE5 = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]
CHILD_BANDS = ["0-4", "5-9", "10-14", "15-19"]
JUNAEB_LEVELS = ["parvularia", "basico1", "basico5", "medio1"]


def prep_e20(D) -> dict:
    ine = D.ine
    nat = ine[(ine.level == "national") & (ine.population_base == "base2017")]
    pyr = (nat[(nat.sex.isin(["HOMBRE", "MUJER"])) & (nat.age_group.isin(AGE5))]
           .pivot_table(index=["year", "age_group"], columns="sex", values="population", aggfunc="sum").reset_index())
    tot = nat[(nat.sex == "TOTAL") & (nat.age_group == "TOTAL")].set_index("year")["population"]
    child = (nat[(nat.sex == "TOTAL") & (nat.age_group.isin(CHILD_BANDS))].groupby("year")["population"].sum())
    reg = ine[(ine.level == "region") & (ine.sex == "TOTAL") & (ine.age_group.isin(CHILD_BANDS))]
    reg = reg.groupby(["year", "cut_region", "region_name"], as_index=False)["population"].sum()
    bases = D.ine_bases.copy()
    # Comparación por edad 2024: base 2017 (proyección 30 jun) frente al Censo 2024 enumerado (bases nunca fundidas)
    b17 = nat[(nat.year == 2024) & (nat.sex == "TOTAL") & (nat.age_group.isin(AGE5))].set_index("age_group")["population"]
    if len(D.ine_sens):
        c24 = D.ine_sens[(D.ine_sens.population_base == "censo2024") & (D.ine_sens.level == "national") &
                         (D.ine_sens.sex == "TOTAL")]
        c24 = c24[c24.age_group.isin(AGE5)].groupby("age_group")["population"].sum()
    else:
        c24 = pd.Series(dtype=float)
    age24 = pd.DataFrame({"base2017_2024": b17.reindex(AGE5), "censo2024": c24.reindex(AGE5)})
    age24["ratio"] = age24.censo2024 / age24.base2017_2024
    natl = pd.DataFrame({"population": tot, "child_0_19": child})
    natl["child_share_pct"] = 100 * natl.child_0_19 / natl.population
    return dict(pyramid=pyr, national=natl.reset_index(), regions=reg, bases=bases, age2024=age24.reset_index())


def prep_e21(D) -> dict:
    fn = D.fonasa_nat
    tramo = (fn[fn.dimension == "TRAMO"].pivot_table(index="year", columns="category", values="beneficiaries",
                                                     aggfunc="sum"))
    tramo = tramo.reindex([y for y in YEARS_REM if y in tramo.index])
    fc = D.fonasa_com
    fon_grid = fc.year.isin(YEARS_REM) & fc.sex.isin(["HOMBRE", "MUJER"]) & fc.age_band_5y.isin(AGE5)
    fon_as = (fc[fon_grid].groupby(["year", "sex", "age_band_5y"], as_index=False)["beneficiaries"].sum())
    # Fuera de la rejilla: sexo INDETERMINADO, edad sin información y los años cuyo archivo publica solo bandas
    # decenales (2023). Se informa, nunca se reparte ni se imputa.
    fon_excluded = (fc[fc.year.isin(YEARS_REM) & ~fon_grid].groupby("year", as_index=False)["beneficiaries"].sum()
                    .rename(columns={"beneficiaries": "outside_sex_age_grid"}))
    fon_scheme = (fc[fc.year.isin(YEARS_REM)].groupby("year")["age_band_raw"].nunique()
                  .rename("n_age_bands_published").reset_index())
    ic = D.isapre_com
    isa_age = (ic[(ic.row_type == "comuna") & ic.sex.isin(["HOMBRE", "MUJER", "SIN_INFORMACION"]) &
                  ic.age_band_5y.isin(AGE5)]
               .groupby(["year", "age_band_5y"], as_index=False)["beneficiarios"].sum())
    isa_excl = (ic[(ic.row_type == "comuna") & ic.sex.isin(["HOMBRE", "MUJER", "SIN_INFORMACION"]) &
                   (~ic.age_band_5y.isin(AGE5))].groupby("year", as_index=False)["beneficiarios"].sum()
                .rename(columns={"beneficiarios": "outside_age_bands"}))
    aps = D.aps_panel.set_index("year")
    ac = D.aps_com
    aps_age = (ac[ac.year.isin(YEARS_REM) & ac.sex.isin(["HOMBRE", "MUJER"])]
               .groupby(["year", "sex", "age_band_20y"], as_index=False)["enrolled"].sum())
    last = int(max(YEARS_REM))
    ine_reg = D.ine[(D.ine.level == "region") & (D.ine.sex == "TOTAL") & (D.ine.age_group == "TOTAL") &
                    (D.ine.population_base == "base2017")]
    ine_reg = ine_reg[ine_reg.year == last][["cut_region", "region_name", "population"]]
    fon_reg = fc[fc.year == last].groupby("cut_region", as_index=False)["beneficiaries"].sum()
    isa_reg = (ic[(ic.year == last) & (ic.row_type == "comuna") & ic.sex.isin(["HOMBRE", "MUJER", "SIN_INFORMACION"])]
               .groupby("cut_region", as_index=False)["beneficiarios"].sum())
    aps_reg = ac[ac.year == last].groupby("cut_region", as_index=False)["enrolled"].sum()
    regional = (ine_reg.merge(fon_reg, on="cut_region", how="left").merge(isa_reg, on="cut_region", how="left")
                .merge(aps_reg, on="cut_region", how="left"))
    for col, new in (("beneficiaries", "fonasa_pct"), ("beneficiarios", "isapre_pct"), ("enrolled", "aps_pct")):
        regional[new] = 100 * regional[col] / regional["population"]
    return dict(tramo=tramo, fonasa_age_sex=fon_as, fonasa_excluded=fon_excluded, fonasa_scheme=fon_scheme,
                isapre_age=isa_age, isapre_outside=isa_excl,
                aps_panel=aps, aps_age_sex=aps_age, regional=regional.sort_values("cut_region"),
                coverage=D.coverage.set_index("year"), last_year=last)


def prep_e22(D, variant: str) -> dict:
    panel = D.r20_panel.set_index("year")
    est = D.r20_estab.copy()
    est["occupancy_pct"] = 100 * est.bed_days_occupied / est.bed_days_available.replace(0, np.nan)
    by_year = est.groupby("year").agg(establishments=("codigo_establecimiento", "nunique"),
                                      discharges=("discharges", "sum"),
                                      bed_days_available=("bed_days_available", "sum"),
                                      bed_days_occupied=("bed_days_occupied", "sum"))
    by_year["occupancy_pct"] = 100 * by_year.bed_days_occupied / by_year.bed_days_available
    last = int(est.year.max())
    area = (D.r20_area[D.r20_area.year == last].groupby("area_funcional", as_index=False)
            .agg(bed_days_available=("bed_days_available", "sum"), discharges=("discharges", "sum"))
            .sort_values("bed_days_available", ascending=False))
    # Panel ecológico: GRD 2024 (último año GRD) frente a REM-20 del mismo año, por código de establecimiento.
    gyear = int(max(YEARS_GRD))
    g = D.grd_hosp[(D.grd_hosp.variant == variant) & (D.grd_hosp.year == gyear)][
        ["COD_HOSPITAL", "hospital_name", "n_episodes_total", "n_f84_any", "in_fixed_panel"]].copy()
    g["COD_HOSPITAL"] = g.COD_HOSPITAL.astype("Int64").astype(str)
    r = est[est.year == gyear][["codigo_establecimiento", "establecimiento", "discharges", "bed_days_available",
                                "in_panel_188"]].copy()
    r["codigo_establecimiento"] = r.codigo_establecimiento.astype("Int64").astype(str)
    eco = g.merge(r, left_on="COD_HOSPITAL", right_on="codigo_establecimiento", how="inner")
    rho = tau = np.nan
    if len(eco) > 3:
        ok = eco[(eco.discharges > 0) & (eco.n_f84_any >= 0)]
        if len(ok) > 3:
            rho = float(stats.spearmanr(ok.discharges, ok.n_f84_any).statistic)
            tau = float(stats.spearmanr(ok.discharges, ok.n_f84_any).pvalue)
    return dict(panel=panel, by_year=by_year, per_estab=est, area=area, eco=eco, rho=rho, rho_p=tau,
                last_year=last, grd_year=gyear)


#: `survey` es una CLAVE DE MÁQUINA: con guion ASCII en la ventana de años, es la que viaja por
#: outputs/tidy/survey_estimates.csv y la que compara `SURVEY_ORDER`. El rótulo que LEE el lector se
#: obtiene de la clave al imprimirla, con `survey_label`, que le pone la raya corta como el resto del
#: corpus. Las claves de abajo NO se tocan: si llevaran la raya, el filtro dejaría de encontrar filas.
SURVEY_ORDER = [
    ("ENDIDE 2022", "ENDIDE adultos 18+: autismo reportado"),
    ("ENDIDE 2022", "ENDIDE NNA 2-17: autismo reportado"),
    ("ENDIDE 2022", "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico"),
    ("ENCAVI 2023-2024", "ENCAVI 15+: diagnóstico de trastorno del espectro autista"),
]


def survey_label(key) -> str:
    """Rótulo impreso de una encuesta a partir de su clave: «ENCAVI 2023-2024» → «ENCAVI 2023–2024»."""
    return C.yspan(key)


def prep_e23(D) -> dict:
    s = D.surveys.copy()
    s["reliable"] = (s.precision_flag == "adequate") & (s.cases >= 30)
    s["pct"] = 100 * s.proportion
    s["pct_lo"] = 100 * s.lo
    s["pct_hi"] = 100 * s.hi
    s["rse_pct"] = 100 * s.rse
    s["label_key"] = s.survey + " · " + s.domain + " · " + s.subgroup_type + "=" + s.subgroup
    prim = s[s.estimate_type == "primary"].copy()
    return dict(all=s, primary=prim,
                has_region=bool((s.subgroup_type == "region").any()))


def prep_e24(D) -> dict:
    p = D.pie.pivot_table(index="year", columns="series", values="value", aggfunc="first")
    p = p.reindex([y for y in YEARS_REM if y in p.index])
    edu = D.edu.set_index("year")
    disc = {}
    if 2022 in p.index:
        total = p.at[2022, "sinaces_total_autistic_students"] if "sinaces_total_autistic_students" in p else np.nan
        special = p.at[2022, "special_schools_autism"] if "special_schools_autism" in p else np.nan
        derived = (total - special) if (pd.notna(total) and pd.notna(special)) else np.nan
        published = p.at[2022, "pie_harmonised_sinaces"] if "pie_harmonised_sinaces" in p else np.nan
        apuntes = p.at[2022, "pie_harmonised_apuntes60"] if "pie_harmonised_apuntes60" in p else np.nan
        disc = dict(total=total, special=special, derived=derived, published=published, apuntes=apuntes,
                    gap=(published - derived) if (pd.notna(published) and pd.notna(derived)) else np.nan)
    sex2023 = {}
    for base, key in (("pie_tea_strict", "strict"), ("pie_tea_asperger", "asperger"), ("pie_total_enrolment", "pie_total")):
        m = p.at[2023, f"{base}_male"] if f"{base}_male" in p.columns and 2023 in p.index else np.nan
        f = p.at[2023, f"{base}_female"] if f"{base}_female" in p.columns and 2023 in p.index else np.nan
        r, lo, hi = ratio_counts_ci(m, f)
        sex2023[key] = dict(male=m, female=f, ratio=r, lo=lo, hi=hi)
    return dict(pie=p, edu=edu, discrepancy=disc, sex2023=sex2023)


def prep_e25(D) -> dict:
    j = D.junaeb.copy()
    j["ratio"] = np.nan
    j["ratio_lo"] = np.nan
    j["ratio_hi"] = np.nan
    ratios = []
    for (y, lvl), g in j.groupby(["year", "level"]):
        male = g[g.sex == "male"]
        fem = g[g.sex == "female"]
        if male.empty or fem.empty:
            continue
        m, f = male.iloc[0], fem.iloc[0]
        if pd.notna(m.proportion_weighted_pct) and pd.notna(f.proportion_weighted_pct):
            r, lo, hi = ratio_props_ci(m.proportion_weighted_pct, m.se_pct, f.proportion_weighted_pct, f.se_pct)
            basis = "weighted"
        elif pd.notna(m.proportion_unweighted_pct) and pd.notna(f.proportion_unweighted_pct):
            pm, sem = wilson_se(m.n_tea_unweighted, m.n_students)
            pf, sef = wilson_se(f.n_tea_unweighted, f.n_students)
            r, lo, hi = ratio_props_ci(100 * pm, 100 * sem, 100 * pf, 100 * sef)
            basis = "unweighted"
        else:
            r = lo = hi = np.nan
            basis = "not_estimable"
        ratios.append(dict(year=int(y), level=lvl, ratio=r, lo=lo, hi=hi, basis=basis,
                           male_pct=m.proportion_weighted_pct if basis == "weighted" else m.proportion_unweighted_pct,
                           female_pct=f.proportion_weighted_pct if basis == "weighted" else f.proportion_unweighted_pct,
                           male_cases=m.n_tea_unweighted, female_cases=f.n_tea_unweighted,
                           male_n=m.n_students, female_n=f.n_students))
    return dict(junaeb=j, ratios=pd.DataFrame(ratios),
                availability=(j[j.sex == "all"][["year", "level", "estimable", "weight_variable", "item_variable",
                                                 "n_students", "n_tea_unweighted"]].copy()))


# --- E26: comparación entre sistemas -----------------------------------------------------------
SYS_LABEL = {
    "grd": {"es": "GRD: episodios con F84 documentado", "en": "GRD: episodes with documented F84"},
    "deis": {"es": "DEIS: egresos con F84 principal", "en": "DEIS: discharges with principal F84"},
    "a05": {"es": "REM A05: ingresos por autismo estricto", "en": "REM A05: strict-autism entries"},
    "p2": {"es": "REM P2: población bajo control en diciembre", "en": "REM P2: December population under control"},
    "pie": {"es": "Educación: PIE armonizado", "en": "Education: harmonised PIE"},
}
SYS_UNIT = {
    "grd": {"es": "episodios", "en": "episodes"}, "deis": {"es": "egresos", "en": "discharges"},
    "a05": {"es": "ingresos", "en": "entries"}, "p2": {"es": "personas bajo control", "en": "persons under control"},
    "pie": {"es": "estudiantes", "en": "students"},
}
SYS_REPORTING_UNIT = {
    "grd": {"es": "por hospital GRD reportante", "en": "per reporting GRD hospital"},
    "deis": {"es": "por 100.000 egresos DEIS", "en": "per 100,000 DEIS discharges"},
    "a05": {"es": "por establecimiento REM reportante", "en": "per reporting REM establishment"},
    "p2": {"es": "por establecimiento REM reportante", "en": "per reporting REM establishment"},
    "pie": {"es": "por 1.000 postulantes al PIE", "en": "per 1,000 PIE applicants"},
}
SYS_COLOR = {"grd": OKABE[0], "deis": OKABE[5], "a05": OKABE[1], "p2": OKABE[2], "pie": OKABE[3]}


def prep_e26(D, variant: str) -> dict:
    ine_nat = (D.ine[(D.ine.level == "national") & (D.ine.sex == "TOTAL") & (D.ine.age_group == "TOTAL") &
                     (D.ine.population_base == "base2017")].set_index("year")["population"])
    g = D.grd[(D.grd.variant == variant) & (D.grd.panel == "observed") & (D.grd.activity == "all") &
              (D.grd.position == "any")].set_index("year")
    de = D.deis[(D.deis.variant == variant) & (D.deis.source_layout == "canonical")].set_index("year")
    rem = D.rem
    a05 = rem[(rem.module == "A05") & (rem.variant == "strict_autism") &
              rem.indicator.str.contains("ingresos", case=False, na=False)].set_index("year")
    p2 = rem[(rem.code == CFG.P2_TEA) & (rem.measure == "december_stock")].set_index("year")
    pie = D.pie.pivot_table(index="year", columns="series", values="value", aggfunc="first")
    rows = []
    for year in YEARS_REM:
        pop = float(ine_nat.get(year, np.nan))
        entries = [
            ("grd", g.n_episodes_f84.get(year, np.nan), g.hospitals_n.get(year, np.nan),
             g.n_episodes_total_same_panel_activity.get(year, np.nan)),
            ("deis", de.f84_diag1.get(year, np.nan), np.nan, de.discharges_total.get(year, np.nan)),
            ("a05", a05.total.get(year, np.nan), a05.n_reporting_establishments.get(year, np.nan), np.nan),
            ("p2", p2.total.get(year, np.nan), p2.n_reporting_establishments.get(year, np.nan), np.nan),
            ("pie", pie.at[year, "pie_harmonised"] if year in pie.index and "pie_harmonised" in pie.columns else np.nan,
             np.nan, pie.at[year, "pie_total_applicants_sinaces"]
             if year in pie.index and "pie_total_applicants_sinaces" in pie.columns else np.nan),
        ]
        for sysk, value, units, denom in entries:
            if pd.isna(value):
                continue
            per_pop = PER * float(value) / pop if pd.notna(pop) and pop else np.nan
            if sysk in ("grd", "a05", "p2") and pd.notna(units) and float(units) > 0:
                per_unit = float(value) / float(units)
            elif sysk == "deis" and pd.notna(denom) and float(denom) > 0:
                per_unit = PER * float(value) / float(denom)
            elif sysk == "pie" and pd.notna(denom) and float(denom) > 0:
                per_unit = 1000.0 * float(value) / float(denom)
            else:
                per_unit = np.nan
            rows.append(dict(system=sysk, year=int(year), value=float(value), population=pop,
                             per_100k_residents=per_pop, reporting_units=units, denominator=denom,
                             per_reporting_unit=per_unit))
    df = pd.DataFrame(rows)
    conv = D.conv[D.conv.variant.isin([variant, "both"])].copy() if len(D.conv) else pd.DataFrame()
    if len(conv) and "index_base_year" in conv.columns:
        # Un solo año base: el primer año común a todas las series (los códigos A05 de autismo empiezan en 2021).
        bases = sorted(conv.index_base_year.unique())
        chosen = max(bases)
        conv = conv[conv.index_base_year == chosen].copy()
    return dict(table=df, convergence=conv, ine=ine_nat)


# --- E26b: razón de sexos multifuente ----------------------------------------------------------
SRC_LABEL = {
    "grd_any": {"es": "GRD · episodios con F84 documentado (conteos)", "en": "GRD · episodes with documented F84 (counts)"},
    "grd_any_asr": {"es": "GRD · episodios con F84 (tasas estandarizadas)", "en": "GRD · episodes with F84 (standardised rates)"},
    "grd_principal": {"es": "GRD · episodios con F84 principal", "en": "GRD · episodes with principal F84"},
    "grd_persons": {"es": "GRD · personas únicas dentro del año", "en": "GRD · unique persons within year"},
    "deis_principal": {"es": "DEIS · egresos con F84 principal", "en": "DEIS · discharges with principal F84"},
    "a05_entries": {"es": "REM A05 · ingresos por autismo (conteos)", "en": "REM A05 · autism entries (counts)"},
    "a05_asr": {"es": "REM A05 · ingresos por autismo (tasas estandarizadas)", "en": "REM A05 · autism entries (standardised rates)"},
    "p2_december": {"es": "REM P2 · población bajo control, diciembre", "en": "REM P2 · population under control, December"},
    "p6_primary": {"es": "REM P6 · bajo control en APS, diciembre", "en": "REM P6 · under control in primary care, December"},
    "p6_specialty": {"es": "REM P6 · bajo control en especialidad, diciembre", "en": "REM P6 · under control in specialty care, December"},
    "pie_strict": {"es": "PIE · autismo estricto (2023, único año publicado)", "en": "PIE · strict autism (2023, only published year)"},
    "junaeb_parvularia": {"es": "JUNAEB · parvularia", "en": "JUNAEB · pre-school"},
    "junaeb_basico1": {"es": "JUNAEB · 1º básico", "en": "JUNAEB · grade 1"},
    "junaeb_basico5": {"es": "JUNAEB · 5º básico", "en": "JUNAEB · grade 5"},
    "junaeb_medio1": {"es": "JUNAEB · 1º medio", "en": "JUNAEB · grade 9"},
    "endide_adults": {"es": "ENDIDE 2022 · adultos 18+", "en": "ENDIDE 2022 · adults 18+"},
    "endide_children": {"es": "ENDIDE 2022 · NNA 2–17", "en": "ENDIDE 2022 · children 2–17"},
    "encavi": {"es": "ENCAVI 2023–24 · personas 15+", "en": "ENCAVI 2023–24 · persons 15+"},
}
SRC_UNIT = {
    "grd_any": {"es": "episodios", "en": "episodes"}, "grd_any_asr": {"es": "episodios", "en": "episodes"},
    "grd_principal": {"es": "episodios", "en": "episodes"}, "grd_persons": {"es": "personas", "en": "persons"},
    "deis_principal": {"es": "egresos", "en": "discharges"}, "a05_entries": {"es": "ingresos", "en": "entries"},
    "a05_asr": {"es": "ingresos", "en": "entries"}, "p2_december": {"es": "personas bajo control", "en": "persons under control"},
    "p6_primary": {"es": "personas bajo control", "en": "persons under control"},
    "p6_specialty": {"es": "personas bajo control", "en": "persons under control"},
    "pie_strict": {"es": "estudiantes", "en": "students"},
    "junaeb_parvularia": {"es": "encuestados", "en": "respondents"}, "junaeb_basico1": {"es": "encuestados", "en": "respondents"},
    "junaeb_basico5": {"es": "encuestados", "en": "respondents"}, "junaeb_medio1": {"es": "encuestados", "en": "respondents"},
    "endide_adults": {"es": "encuestados", "en": "respondents"}, "endide_children": {"es": "encuestados", "en": "respondents"},
    "encavi": {"es": "encuestados", "en": "respondents"},
}
METHOD_LABEL = {
    "exact_binomial": {"es": "binomial exacto sobre p = H/(H+M)", "en": "exact binomial on p = M/(M+F)"},
    "lognormal_rates": {"es": "log-normal sobre la razón de tasas estandarizadas", "en": "log-normal on the ratio of standardised rates"},
    "design_based": {"es": "delta sobre log, errores estándar de diseño complejo", "en": "delta on log, complex-design standard errors"},
    "binomial_props": {"es": "delta sobre log, errores estándar binomiales (sin ponderador publicado)",
                       "en": "delta on log, binomial standard errors (no published weight)"},
    "not_estimable": {"es": "no estimable: la fuente no publica el sexo de esta serie",
                      "en": "not estimable: the source does not publish sex for this series"},
}
#: Rótulo corto de cada fuente para la lámina E26b: en un panel de media página (85 mm) el rótulo
#: largo de `SRC_LABEL` ocupaba más de la mitad del ancho. El rótulo largo sigue en la leyenda y en la
#: tabla acompañante; aquí se conserva SIEMPRE la unidad junto a la fuente, que es lo que impide leer
#: las razones como si midieran lo mismo.
SRC_SHORT = {
    "grd_any": {"es": "GRD F84 (conteo)", "en": "GRD F84 (count)"},
    "grd_any_asr": {"es": "GRD F84 (t. est.)", "en": "GRD F84 (ASR)"},
    "grd_principal": {"es": "GRD F84 princ.", "en": "GRD F84 princ."},
    "grd_persons": {"es": "GRD personas", "en": "GRD persons"},
    "deis_principal": {"es": "DEIS F84 princ.", "en": "DEIS F84 princ."},
    "a05_entries": {"es": "REM A05 (conteo)", "en": "REM A05 (count)"},
    "a05_asr": {"es": "REM A05 (t. est.)", "en": "REM A05 (ASR)"},
    "p2_december": {"es": "REM P2 dic.", "en": "REM P2 Dec."},
    "p6_primary": {"es": "REM P6 APS", "en": "REM P6 primary"},
    "p6_specialty": {"es": "REM P6 espec.", "en": "REM P6 specialty"},
    "pie_strict": {"es": "PIE estricto 2023", "en": "PIE strict 2023"},
    "junaeb_parvularia": {"es": "JUNAEB parvul.", "en": "JUNAEB pre-sch."},
    "junaeb_basico1": {"es": "JUNAEB 1º bás.", "en": "JUNAEB grade 1"},
    "junaeb_basico5": {"es": "JUNAEB 5º bás.", "en": "JUNAEB grade 5"},
    "junaeb_medio1": {"es": "JUNAEB 1º med.", "en": "JUNAEB grade 9"},
    "endide_adults": {"es": "ENDIDE 18+", "en": "ENDIDE 18+"},
    "endide_children": {"es": "ENDIDE 2–17", "en": "ENDIDE 2–17"},
    "encavi": {"es": "ENCAVI 15+", "en": "ENCAVI 15+"},
}
SRC_COLOR = {"grd_any": OKABE[0], "grd_any_asr": OKABE[0], "grd_principal": OKABE[4], "grd_persons": "#9ecae1",
             "deis_principal": OKABE[5], "a05_entries": OKABE[1], "a05_asr": OKABE[1], "p2_december": OKABE[2],
             "p6_primary": OKABE[6], "p6_specialty": "#8c6d31", "pie_strict": OKABE[3],
             "junaeb_parvularia": "#7b3294", "junaeb_basico1": "#a35fb5", "junaeb_basico5": "#c994c7",
             "junaeb_medio1": "#dfa6d6", "endide_adults": "#004c6d", "endide_children": "#2a7fa8", "encavi": "#5aa9c9"}


def _rem_sex_stock(rem_tidy: pd.DataFrame, codes, month: int = 12) -> pd.DataFrame:
    """Suma COL02 (Hombres) y COL03 (Mujeres) de las filas en era del stock del mes indicado."""
    if not len(rem_tidy):
        return pd.DataFrame(columns=["year", "males", "females", "total", "n_reporting_establishments"])
    d = rem_tidy[(rem_tidy.code.isin(list(codes))) & (rem_tidy.month == month)]
    d = d[d.in_era.astype(str).str.lower().isin(["true", "1"])]
    if not len(d):
        return pd.DataFrame(columns=["year", "males", "females", "total", "n_reporting_establishments"])
    g = d.groupby("year").agg(males=("col02_num", "sum"), females=("col03_num", "sum"),
                              total=("col01_num", "sum"),
                              n_reporting_establishments=("IdEstablecimiento", "nunique")).reset_index()
    return g


def prep_e26b(D, variant: str) -> dict:
    rows = []

    def add(source, year, males, females, method, basis, extra=None):
        if method == "exact_binomial":
            r, lo, hi = ratio_counts_ci(males, females)
        else:
            r, lo, hi = extra if extra is not None else (np.nan, np.nan, np.nan)
        rows.append(dict(source=source, year=int(year) if pd.notna(year) else np.nan, males=males, females=females,
                         ratio=r, lo=lo, hi=hi, method=method, basis=basis, variant=variant))

    # GRD: episodios (cualquier posición y principal), panel observado, toda actividad
    gs = D.grd_as[(D.grd_as.variant == variant) & (D.grd_as.panel == "observed") & (D.grd_as.activity == "all")]
    for position, key in (("any", "grd_any"), ("principal", "grd_principal")):
        sub = gs[gs.position == position]
        agg = sub[sub.sex.isin(["HOMBRE", "MUJER"])].groupby(["year", "sex"])["n_f84"].sum().unstack()
        for year in agg.index:
            add(key, year, agg.at[year, "HOMBRE"] if "HOMBRE" in agg else np.nan,
                agg.at[year, "MUJER"] if "MUJER" in agg else np.nan, "exact_binomial", "counts")
    # GRD: personas únicas dentro del año — el sexo no se publica para esta serie
    gp = D.grd[(D.grd.variant == variant) & (D.grd.panel == "observed") & (D.grd.activity == "all") &
               (D.grd.position == "any")]
    for _, r in gp.iterrows():
        rows.append(dict(source="grd_persons", year=int(r.year), males=np.nan, females=np.nan, ratio=np.nan,
                         lo=np.nan, hi=np.nan, method="not_estimable", basis="persons", variant=variant))
    # GRD: tasas estandarizadas por edad (Fay–Feuer) por sexo
    pr = D.pop_rates[(D.pop_rates.variant == variant) & (D.pop_rates.position == "any")]
    for year, g in pr.groupby("year"):
        m = g[g.sex == "HOMBRE"]
        f = g[g.sex == "MUJER"]
        if len(m) and len(f):
            rr = ratio_rates_ci(m.asr.iloc[0], m.asr_lo.iloc[0], m.asr_hi.iloc[0],
                                f.asr.iloc[0], f.asr_lo.iloc[0], f.asr_hi.iloc[0])
            add("grd_any_asr", year, m["count"].iloc[0], f["count"].iloc[0], "lognormal_rates", "standardised_rates", rr)
    # DEIS: egresos con F84 principal
    ds = D.deis_as[(D.deis_as.variant == variant) & (D.deis_as.level == "sex") &
                   (D.deis_as.source_layout == "canonical")]
    for year, g in ds.groupby("year"):
        m = g[g.sex == "HOMBRE"]
        f = g[g.sex == "MUJER"]
        add("deis_principal", year, m.f84_diag1.sum() if len(m) else np.nan,
            f.f84_diag1.sum() if len(f) else np.nan, "exact_binomial", "counts")
    # REM A05: ingresos por autismo estricto (05990022), conteos por sexo
    aa = D.a05_as[(D.a05_as.age_group == "total") & (D.a05_as.flow == "entry") & (D.a05_as.code == "05990022")]
    for year, g in aa.groupby("year"):
        m = g[g.sex == "Hombres"]["count"].sum()
        f = g[g.sex == "Mujeres"]["count"].sum()
        add("a05_entries", year, m, f, "exact_binomial", "counts")
    # REM A05: tasas estandarizadas por edad
    ar = D.a05_asr[D.a05_asr.variant == "strict_autism"]
    for year, g in ar.groupby("year"):
        m = g[g.sex == "HOMBRE"]
        f = g[g.sex == "MUJER"]
        if len(m) and len(f):
            rr = ratio_rates_ci(m.asr.iloc[0], m.asr_lo.iloc[0], m.asr_hi.iloc[0],
                                f.asr.iloc[0], f.asr_lo.iloc[0], f.asr_hi.iloc[0])
            add("a05_asr", year, m["count"].iloc[0], f["count"].iloc[0], "lognormal_rates", "standardised_rates", rr)
    # REM P2 y P6: stocks de diciembre por sexo (COL02/COL03 del diccionario REM)
    for key, codes in (("p2_december", [CFG.P2_TEA]),
                       ("p6_primary", CFG.VARIANTS[variant]["p6_primary"]),
                       ("p6_specialty", CFG.VARIANTS[variant]["p6_specialty"])):
        st = _rem_sex_stock(D.rem_tidy, codes, 12)
        for _, r in st.iterrows():
            add(key, r.year, r.males, r.females, "exact_binomial", "counts")
    # PIE: autismo estricto 2023 (único año con desglose por sexo publicado)
    pie = D.pie.pivot_table(index="year", columns="series", values="value", aggfunc="first")
    if 2023 in pie.index and "pie_tea_strict_male" in pie.columns:
        add("pie_strict", 2023, pie.at[2023, "pie_tea_strict_male"], pie.at[2023, "pie_tea_strict_female"],
            "exact_binomial", "counts")
    # JUNAEB: porcentajes ponderados (o no ponderados donde no hay ponderador publicado)
    jr = prep_e25(D)["ratios"]
    for _, r in jr.iterrows():
        if r.basis == "not_estimable":
            continue
        rows.append(dict(source=f"junaeb_{r.level}", year=int(r.year), males=r.male_cases, females=r.female_cases,
                         ratio=r.ratio, lo=r.lo, hi=r.hi,
                         method="design_based" if r.basis == "weighted" else "binomial_props",
                         basis="proportions", variant=variant))
    # Encuestas: razón de proporciones estimadas con diseño complejo
    sv = D.surveys[(D.surveys.subgroup_type == "sex") & (D.surveys.estimate_type == "primary")]
    survey_map = {"ENDIDE adultos 18+: autismo reportado": ("endide_adults", 2022),
                  "ENDIDE NNA 2-17: autismo reportado": ("endide_children", 2022),
                  "ENCAVI 15+: diagnóstico de trastorno del espectro autista": ("encavi", 2024)}
    for domain, (key, year) in survey_map.items():
        g = sv[sv.domain == domain]
        m = g[g.subgroup == "Hombre"]
        f = g[g.subgroup == "Mujer"]
        if len(m) and len(f):
            rr = ratio_props_ci(m.proportion.iloc[0], m.se.iloc[0], f.proportion.iloc[0], f.se.iloc[0])
            rows.append(dict(source=key, year=year, males=m.cases.iloc[0], females=f.cases.iloc[0],
                             ratio=rr[0], lo=rr[1], hi=rr[2], method="design_based", basis="proportions",
                             variant=variant))
    trend = pd.DataFrame(rows)

    # Panel B: razón por grupo etario (GRD último año y A05 último año), celdas < 5 eventos suprimidas
    age_rows = []
    gy = int(D.grd_as.year.max())
    ga = gs[(gs.position == "any") & (gs.year == gy) & gs.sex.isin(["HOMBRE", "MUJER"])]
    ga = ga[ga.age_group != "unknown"]
    piv = ga.pivot_table(index="age_group", columns="sex", values="n_f84", aggfunc="sum")
    for ag in AGE5:
        if ag not in piv.index:
            continue
        m, f = float(piv.at[ag, "HOMBRE"]), float(piv.at[ag, "MUJER"])
        supp = (m < 5) or (f < 5)
        r, lo, hi = ratio_counts_ci(m, f)
        age_rows.append(dict(source="grd_any", year=gy, age_group=ag, males=m, females=f,
                             ratio=np.nan if supp else r, lo=np.nan if supp else lo, hi=np.nan if supp else hi,
                             suppressed=supp))
    ay = int(D.a05_as.year.max())
    aage = D.a05_as[(D.a05_as.flow == "entry") & (D.a05_as.code == "05990022") & (D.a05_as.year == ay) &
                    (D.a05_as.age_group != "total")]
    pv = aage.pivot_table(index="age_group", columns="sex", values="count", aggfunc="sum")
    for ag in AGE5:
        if ag not in pv.index:
            continue
        m = float(pv.at[ag, "Hombres"]) if "Hombres" in pv.columns else np.nan
        f = float(pv.at[ag, "Mujeres"]) if "Mujeres" in pv.columns else np.nan
        supp = (not np.isfinite(m)) or (not np.isfinite(f)) or (m < 5) or (f < 5)
        r, lo, hi = ratio_counts_ci(m, f)
        age_rows.append(dict(source="a05_entries", year=ay, age_group=ag, males=m, females=f,
                             ratio=np.nan if supp else r, lo=np.nan if supp else lo, hi=np.nan if supp else hi,
                             suppressed=supp))
    by_age = pd.DataFrame(age_rows)

    # Panel E: la misma razón en las dos variantes de definición de caso
    var_rows = []
    for other in VARIANTS:
        gso = D.grd_as[(D.grd_as.variant == other) & (D.grd_as.panel == "observed") &
                       (D.grd_as.activity == "all") & (D.grd_as.position == "any")]
        agg = gso[gso.sex.isin(["HOMBRE", "MUJER"])].groupby(["year", "sex"])["n_f84"].sum().unstack()
        for year in agg.index:
            r, lo, hi = ratio_counts_ci(agg.at[year, "HOMBRE"], agg.at[year, "MUJER"])
            var_rows.append(dict(source="grd_any", variant=other, year=int(year), ratio=r, lo=lo, hi=hi))
        dso = D.deis_as[(D.deis_as.variant == other) & (D.deis_as.level == "sex") &
                        (D.deis_as.source_layout == "canonical")]
        for year, g in dso.groupby("year"):
            m = g[g.sex == "HOMBRE"].f84_diag1.sum()
            f = g[g.sex == "MUJER"].f84_diag1.sum()
            r, lo, hi = ratio_counts_ci(m, f)
            var_rows.append(dict(source="deis_principal", variant=other, year=int(year), ratio=r, lo=lo, hi=hi))
        aao = D.a05_as[(D.a05_as.age_group == "total") & (D.a05_as.flow == "entry") & (D.a05_as.variant == other)]
        for year, g in aao.groupby("year"):
            r, lo, hi = ratio_counts_ci(g[g.sex == "Hombres"]["count"].sum(), g[g.sex == "Mujeres"]["count"].sum())
            var_rows.append(dict(source="a05_family", variant=other, year=int(year), ratio=r, lo=lo, hi=hi))
        st = _rem_sex_stock(D.rem_tidy, CFG.VARIANTS[other]["p6_primary"], 12)
        for _, r0 in st.iterrows():
            r, lo, hi = ratio_counts_ci(r0.males, r0.females)
            var_rows.append(dict(source="p6_primary", variant=other, year=int(r0.year), ratio=r, lo=lo, hi=hi))
    by_variant = pd.DataFrame(var_rows)
    return dict(trend=trend, by_age=by_age, by_variant=by_variant)


# --- E27: diagnóstico de modelos ---------------------------------------------------------------
ESTIMAND_LABEL = {
    "est_grd_rate": {"es": "GRD: F84 por 100.000 episodios", "en": "GRD: F84 per 100,000 episodes"},
    "est_grd_pop": {"es": "GRD: F84 por 100.000 habitantes", "en": "GRD: F84 per 100,000 population"},
    "est_grd_hospital": {"es": "GRD: modelos por hospital", "en": "GRD: hospital-level models"},
    "est_a05": {"es": "REM A05: ingresos", "en": "REM A05: entries"},
    "est_a05_pop": {"es": "REM A05: ingresos por 100.000 habitantes", "en": "REM A05: entries per 100,000 population"},
    "est_a05_exit": {"es": "REM A05: egresos clínicos", "en": "REM A05: clinical discharges"},
    "est_p2": {"es": "REM P2: stock de diciembre", "en": "REM P2: December stock"},
    "est_p2_june": {"es": "REM P2: stock de junio (sensibilidad)", "en": "REM P2: June stock (sensitivity)"},
    "est_p2_naneas": {"es": "REM P2: NANEAS total", "en": "REM P2: total NANEAS"},
    "est_p6_primary": {"es": "REM P6: bajo control en APS", "en": "REM P6: under control in primary care"},
    "est_p6_specialty": {"es": "REM P6: bajo control en especialidad", "en": "REM P6: under control in specialty care"},
    "est_pie": {"es": "Educación: PIE armonizado", "en": "Education: harmonised PIE"},
    "est_deis": {"es": "DEIS: F84 principal", "en": "DEIS: principal F84"},
}


#: Rótulo compacto y ÚNICO de cada estimando (≤ 22 caracteres) para los ejes de E27: con el rótulo
#: largo truncado había cuatro pares de filas con el mismo texto en pantalla.
ESTIMAND_TINY = {
    "est_grd_rate": {"es": "GRD: F84/100k episod.", "en": "GRD: F84/100k episodes"},
    "est_grd_pop": {"es": "GRD: F84/100k hab.", "en": "GRD: F84/100k popul."},
    "est_grd_hospital": {"es": "GRD: por hospital", "en": "GRD: by hospital"},
    "est_a05": {"es": "REM A05: ingresos", "en": "REM A05: entries"},
    "est_a05_pop": {"es": "REM A05: ingr./100k", "en": "REM A05: entries/100k"},
    "est_a05_exit": {"es": "REM A05: egresos", "en": "REM A05: discharges"},
    "est_p2": {"es": "REM P2: dic.", "en": "REM P2: December"},
    "est_p2_june": {"es": "REM P2: jun. (sens.)", "en": "REM P2: June (sens.)"},
    "est_p2_naneas": {"es": "REM P2: NANEAS total", "en": "REM P2: total NANEAS"},
    "est_p6_primary": {"es": "REM P6: APS", "en": "REM P6: primary care"},
    "est_p6_specialty": {"es": "REM P6: especialidad", "en": "REM P6: specialty"},
    "est_pie": {"es": "Educación: PIE arm.", "en": "Education: harm. PIE"},
    "est_deis": {"es": "DEIS: F84 principal", "en": "DEIS: principal F84"},
}


def est_tiny(key, lang):
    return ESTIMAND_TINY.get(key, ESTIMAND_LABEL.get(key, {"es": key, "en": key}))[lang]
COV_LABEL = {
    "cov_none": {"es": "sin covariables", "en": "no covariates"},
    "cov_depth": {"es": "profundidad de codificación", "en": "coding depth"},
    "cov_disruption": {"es": "disrupción 2020–2021", "en": "2020–2021 disruption"},
    "cov_depth_disruption": {"es": "profundidad + disrupción", "en": "depth + disruption"},
    "cov_hospital_fe": {"es": "efectos fijos de hospital", "en": "hospital fixed effects"},
    "cov_hospital_fe_depth": {"es": "efectos fijos + profundidad", "en": "fixed effects + depth"},
    "cov_hospital_fe_disruption": {"es": "efectos fijos + disrupción", "en": "fixed effects + disruption"},
    "cov_hospital_ri": {"es": "intercepto aleatorio de hospital", "en": "hospital random intercept"},
    "cov_hospital_ri_depth": {"es": "intercepto aleatorio + profundidad", "en": "random intercept + depth"},
    "cov_age": {"es": "edad", "en": "age"},
    "cov_disruption_2021": {"es": "disrupción 2021", "en": "2021 disruption"},
}
VARIANT_SCOPE = {"con_rett": ["con_rett", "both", "strict_autism", "strict_autism_f840"],
                 "sin_rett": ["sin_rett", "both", "strict_autism", "strict_autism_f840"]}

#: La columna `variant` del tidy viaja con las claves del estudio; `both` es la única que es una PALABRA
#: inglesa y se imprimía tal cual en la columna «Variante» de la Tabla E27 española, donde el resto del
#: documento escribe «ambas variantes».
VARIANT_LABEL = {
    "con_rett": {"es": "con_rett", "en": "con_rett"},
    "sin_rett": {"es": "sin_rett", "en": "sin_rett"},
    "both": {"es": "ambas variantes", "en": "both variants"},
    "strict_autism": {"es": "autismo estricto REM (idéntico en ambas variantes)",
                      "en": "strict REM autism (identical in both variants)"},
    "strict_autism_f840": {"es": "solo F84.0 (idéntico en ambas variantes)",
                           "en": "F84.0 only (identical in both variants)"},
}


def variant_label(v, lang: str) -> str:
    lab = VARIANT_LABEL.get(str(v))
    return lab[lang] if lab else str(v)


def prep_e27(D, variant: str) -> dict:
    mod = D.mod[D.mod.variant.isin(VARIANT_SCOPE[variant])].copy()
    fit = D.fitted[D.fitted.model_id.isin(mod.model_id)].copy()
    fit = fit.merge(mod[["model_id", "estimand", "covariates", "model_family", "dispersion", "variant", "years"]]
                    .rename(columns={"estimand": "estimand_m", "variant": "variant_m"}), on="model_id", how="left")
    with np.errstate(divide="ignore", invalid="ignore"):
        fit["pearson"] = (fit.observed_count - fit.fitted_count) / np.sqrt(fit.fitted_count.replace(0, np.nan))
    # Especificación principal por estimando: sin covariables, serie más larga, variante exacta si existe
    main_ids = []
    for est, g in mod.groupby("estimand"):
        cand = g[g.covariates.isin(["cov_none"])] if (g.covariates == "cov_none").any() else g
        cand = cand.assign(span=cand.years.str.slice(5).astype(float) - cand.years.str.slice(0, 4).astype(float),
                           exact=(cand.variant == variant).astype(int))
        cand = cand.sort_values(["exact", "span"], ascending=[False, False])
        main_ids.append(cand.model_id.iloc[0])
    main = mod[mod.model_id.isin(main_ids)].copy()
    return dict(models=mod, fitted=fit, main=main, main_ids=main_ids)


# --- E28: sensibilidad a la variante -----------------------------------------------------------
def prep_e28(D) -> dict:
    rows = []
    g = D.grd[(D.grd.panel == "observed") & (D.grd.activity == "all") & (D.grd.position == "any")]
    for year, sub in g.groupby("year"):
        c = sub[sub.variant == "con_rett"].n_episodes_f84
        s = sub[sub.variant == "sin_rett"].n_episodes_f84
        if len(c) and len(s):
            rows.append(dict(series="grd_any", year=int(year), con_rett=float(c.iloc[0]), sin_rett=float(s.iloc[0])))
    gp = D.grd[(D.grd.panel == "observed") & (D.grd.activity == "all") & (D.grd.position == "principal")]
    for year, sub in gp.groupby("year"):
        c = sub[sub.variant == "con_rett"].n_episodes_f84
        s = sub[sub.variant == "sin_rett"].n_episodes_f84
        if len(c) and len(s):
            rows.append(dict(series="grd_principal", year=int(year), con_rett=float(c.iloc[0]), sin_rett=float(s.iloc[0])))
    rem = D.rem
    a05 = rem[(rem.module == "A05") & rem.variant.isin(["con_rett", "sin_rett"]) &
              rem.indicator.str.contains("ingresos", case=False, na=False)]
    for year, sub in a05.groupby("year"):
        c = sub[sub.variant == "con_rett"].total
        s = sub[sub.variant == "sin_rett"].total
        if len(c) and len(s):
            rows.append(dict(series="a05_family", year=int(year), con_rett=float(c.iloc[0]), sin_rett=float(s.iloc[0])))
    for label, key in (("APS", "p6_primary"), ("especialidad", "p6_specialty")):
        sel = rem[(rem.module == "P6") & rem.variant.isin(["con_rett", "sin_rett"]) &
                  (rem.measure == "december_stock") &
                  rem.indicator.str.contains("APS" if key == "p6_primary" else "especialidad", na=False)]
        for year, sub in sel.groupby("year"):
            c = sub[sub.variant == "con_rett"].total
            s = sub[sub.variant == "sin_rett"].total
            if len(c) and len(s):
                rows.append(dict(series=key, year=int(year), con_rett=float(c.iloc[0]), sin_rett=float(s.iloc[0])))
    de = D.deis[D.deis.source_layout == "canonical"]
    for year, sub in de.groupby("year"):
        c = sub[sub.variant == "con_rett"].f84_diag1
        s = sub[sub.variant == "sin_rett"].f84_diag1
        if len(c) and len(s):
            rows.append(dict(series="deis_principal", year=int(year), con_rett=float(c.iloc[0]), sin_rett=float(s.iloc[0])))
    pie = D.pie.pivot_table(index="year", columns="series", values="value", aggfunc="first")
    for year in pie.index:
        v = pie.at[year, "pie_harmonised"] if "pie_harmonised" in pie.columns else np.nan
        if pd.notna(v):
            rows.append(dict(series="pie_harmonised", year=int(year), con_rett=float(v), sin_rett=float(v)))
    df = pd.DataFrame(rows)
    if len(df):
        df["abs_diff"] = df.con_rett - df.sin_rett
        with np.errstate(divide="ignore", invalid="ignore"):
            df["rel_diff_pct"] = 100 * df.abs_diff / df.sin_rett.replace(0, np.nan)
    return dict(table=df)


E28_SHORT = {
    "grd_any": {"es": "GRD F84 cualquiera", "en": "GRD F84 any"},
    "grd_principal": {"es": "GRD F84 principal", "en": "GRD F84 principal"},
    "a05_family": {"es": "A05 familia TGD", "en": "A05 PDD family"},
    "p6_primary": {"es": "P6 APS", "en": "P6 primary"},
    "p6_specialty": {"es": "P6 especialidad", "en": "P6 specialty"},
    "deis_principal": {"es": "DEIS F84 principal", "en": "DEIS principal F84"},
    "pie_harmonised": {"es": "PIE armonizado", "en": "Harmonised PIE"},
}
E28_SERIES_LABEL = {
    "grd_any": {"es": "GRD · F84 documentado (cualquier posición)", "en": "GRD · documented F84 (any position)"},
    "grd_principal": {"es": "GRD · F84 principal", "en": "GRD · principal F84"},
    "a05_family": {"es": "REM A05 · ingresos familia TGD", "en": "REM A05 · PDD-family entries"},
    "p6_primary": {"es": "REM P6 · APS, diciembre", "en": "REM P6 · primary care, December"},
    "p6_specialty": {"es": "REM P6 · especialidad, diciembre", "en": "REM P6 · specialty care, December"},
    "deis_principal": {"es": "DEIS · F84 principal", "en": "DEIS · principal F84"},
    "pie_harmonised": {"es": "Educación · PIE armonizado (idéntico)", "en": "Education · harmonised PIE (identical)"},
}


# ===========================================================================
# Láminas
# ===========================================================================
# NORMA DE LÁMINA (fase 4c). Toda lámina multipanel se dibuja a tamaño final: lienzo vertical de
# 180 × 245 mm (7,09 × 9,65 pulgadas) a escala 1:1, rejilla de TRES FILAS POR DOS COLUMNAS, un máximo
# de seis paneles, letras de panel en minúscula (a…f) tanto en la lámina como en la leyenda, tipografía
# base de 8 pt, título de panel de 9 pt en negrita, rótulos de eje de 7 pt, leyenda de 7 pt, nada por
# debajo de 6 pt y 600 ppp. Las láminas anteriores se dibujaban con 432 mm de ancho y se encogían al
# insertarse en el documento (factor 0,41), que es la razón por la que varias eran apenas legibles.
# Los paneles se direccionan por su índice de lectura (0…5 = a…f), nunca por (fila, columna), porque la
# rejilla ya no es la de 2 × 3 de la fase anterior.
PLATE_W_IN = 180 / 25.4                  # 7,09 pulgadas
PLATE_H_IN = 245 / 25.4                  # 9,65 pulgadas
PLATE_ROWS, PLATE_COLS = 3, 2
PLATE_MAX_PANELS = PLATE_ROWS * PLATE_COLS
PLATE_DPI = 600
FS_BASE, FS_TITLE, FS_TICK, FS_LEGEND = 8.0, 9.0, 7.0, 7.0
FS_MIN = 6.0                             # nada, ni una anotación, baja de aquí
PANEL_LETTERS = "abcdef"


def _plate_style():
    """Estilo de la lámina a escala 1:1: la tipografía que se declara aquí es la que se imprime."""
    plt, _ = C.style()
    plt.rcParams.update({
        "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold",
        "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
        "legend.fontsize": FS_LEGEND, "figure.dpi": 100, "savefig.dpi": PLATE_DPI,
        # Toda leyenda de estas láminas se dibuja DENTRO del panel: sin recuadro se leía sobre las barras y
        # sobre las series. Con el recuadro blanco translúcido el dato sigue visible bajo ella y el texto
        # sigue legible, que es lo que la revista exige.
        "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
        "legend.edgecolor": "none", "legend.borderpad": 0.25,
        "lines.linewidth": 1.3, "lines.markersize": 4.0, "axes.linewidth": 0.7,
        "xtick.major.size": 2.4, "ytick.major.size": 2.4, "xtick.major.pad": 1.8, "ytick.major.pad": 1.8,
        "axes.labelpad": 2.2, "axes.titlepad": 3.5,
    })
    return plt


def _new_plate(n_panels=PLATE_MAX_PANELS, note_lines=0, full_width_rows=False):
    """Lámina vertical de 3 × 2 a escala 1:1.

    Devuelve ``(plt, fig, panels)`` con ``panels`` en orden de lectura: ``panels[0]`` es el panel a,
    ``panels[1]`` el b, y así hasta el f. ``note_lines`` reserva al pie el alto de una nota de lámina
    (que se escribe con ``_plate_note``); ``full_width_rows`` da a cada panel la fila completa, que es
    lo que necesita una lámina de tres paneles con eje temporal ancho.
    """
    if n_panels > PLATE_MAX_PANELS:
        raise ValueError(f"una lámina no admite más de {PLATE_MAX_PANELS} paneles; pedidos {n_panels}")
    plt = _plate_style()
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), constrained_layout=True)
    gs = fig.add_gridspec(PLATE_ROWS, PLATE_COLS)
    if full_width_rows:
        slots = [gs[r, :] for r in range(PLATE_ROWS)][:n_panels]
    else:
        slots = [gs[i // PLATE_COLS, i % PLATE_COLS] for i in range(n_panels)]
    panels = [fig.add_subplot(s) for s in slots]
    # El sitio del pie ya no se adivina con `note_lines`: lo MIDE `_save_plate` cuando el bloque de notas
    # está compuesto, que es lo único que sabe cuántos renglones ocupa en cada idioma (el español pide un
    # 15 % más de texto y era donde el pie se comía la fila inferior de paneles).
    _set_plate_rect(fig, 0.0)
    return plt, fig, panels


def _set_plate_rect(fig, foot: float) -> None:
    """Reparto de la lámina dejando `foot` (fracción del alto) libre al pie para las notas."""
    engine = fig.get_layout_engine()
    if engine is None:
        return
    foot = float(min(max(foot, 0.0), 0.16))
    engine.set(rect=(0.006, foot + 0.004, 0.982, 0.990 - foot),
               w_pad=0.026, h_pad=0.022, wspace=0.050, hspace=0.060)


def _letter(ax, i):
    """Letra de panel EN MINÚSCULA y ENTRE PARÉNTESIS delante del título, alineado a la izquierda.

    La revista pide a, b, c… en la lámina y en la leyenda. El rótulo va dentro del título y no como
    un texto suelto fuera de los ejes: sin recorte «tight» un texto fuera de los ejes se pierde, y un
    título centrado más ancho que el panel se monta sobre la letra.
    """
    # Entre paréntesis, «(a)»: es la convención de las 58 leyendas con paneles y la que ya imprimían las
    # láminas de 06/08a/08b/08c. Con la letra a secas el artículo publicaba dos convenciones.
    ch = C.plate_panel_letter(PANEL_LETTERS[i] if isinstance(i, int) else i)
    txt = ax.get_title(loc="center")
    ax.set_title("", loc="center")
    # La letra se antepone a la PRIMERA línea del título ya envuelto: volver a envolver el texto
    # completo partía otra vez las líneas y producía títulos de tres y cuatro renglones.
    rows = str(txt).split("\n") if txt else [""]
    rows[0] = f"{ch} {rows[0]}".rstrip()
    ax.set_title("\n".join(rows), loc="left", fontsize=FS_TITLE, fontweight="bold", pad=_title_pad(ax))


#: Cuerpo y ancho útil del bloque de notas del pie: 6,4 pt (el mínimo de la norma más un pelo) sobre
#: 180 mm menos 3 mm de margen a cada lado.
FOOT_FS = FS_MIN + 0.4
FOOT_W_PT = PLATE_W_IN * 72.0 - 2.0 * (3.0 / 25.4 * 72.0)
FOOT_LINE = 1.30                                   # interlineado del pie, en múltiplos del cuerpo


def _plate_note(fig, text, colour=None):
    """Nota de LÁMINA —la que vale para todos los paneles— al pie del lienzo.

    No dibuja: registra. El bloque entero lo compone `_save_plate`, que es quien sabe cuántos renglones
    ocupa y cuánto sitio hay que descontarle al reparto de los paneles."""
    fig._plate_notes = list(getattr(fig, "_plate_notes", [])) + [(" ".join(str(text).split()),
                                                                 colour or "#555555")]


def _note(ax, letter, text, colour=None):
    """Nota EXPLICATIVA de un panel: se imprime al PIE de la lámina con su letra delante.

    Dentro del panel, una nota de dos o tres renglones a 6,2 pt acaba siempre sobre la serie que explica:
    es el defecto que los verificadores describieron en S37 (a)-(b), S39 (a)-(b)-(e)-(f), S40 (b)-(c),
    S42 (b)-(e) y S44 (f) —«la nota tapa los datos que explica»—. Al pie sigue en la MISMA página, con la
    letra del panel delante para que el lector sepa a qué panel pertenece, y el panel queda entero para el
    dato. El detalle completo sigue además en la tabla acompañante de la lámina."""
    fig = ax.figure
    fig._plate_panel_notes = list(getattr(fig, "_plate_panel_notes", [])) + [
        (str(letter), " ".join(str(text).split()), colour or "#555555")]


def _foot_blocks(fig) -> list:
    """Bloques del pie ya plegados al ancho de la lámina: [(texto, color, n_renglones)]."""
    blocks = []
    panel = list(getattr(fig, "_plate_panel_notes", []))
    if panel:
        grey = " ".join(f"({l}) {t}" for l, t, c in panel if c == "#555555")
        other = [(c, " ".join(f"({l}) {t}" for l, t, cc in panel if cc == c))
                 for c in dict.fromkeys(c for _, _, c in panel if c != "#555555")]
        if grey:
            blocks.append((grey, "#555555"))
        blocks += [(txt, colr) for colr, txt in other]
    blocks += list(getattr(fig, "_plate_notes", []))
    out = []
    for text, colour in blocks:
        wrapped = C.plate_wrap(text, FOOT_W_PT, FOOT_FS, "normal")
        out.append((wrapped, colour, wrapped.count("\n") + 1))
    return out


def _draw_foot(fig) -> float:
    """Escribe el bloque de notas al pie y devuelve la fracción de alto que ocupa (para el reparto)."""
    blocks = _foot_blocks(fig)
    if not blocks:
        return 0.0
    lh = FOOT_FS * FOOT_LINE / (PLATE_H_IN * 72.0)
    gap = 0.35 * lh
    total = sum(n for _, _, n in blocks)
    if total > 12:
        # El pie tiene un tope (16 % del alto de la lámina): pasado ese punto se comería la fila inferior
        # de paneles y habría que llevar parte del texto a la tabla acompañante. Se avisa, no se recorta.
        warn(f"el bloque de notas al pie ocupa {total} renglones: revisar qué baja a la tabla acompañante")
    y = 0.004
    for text, colour, n in reversed(blocks):
        fig.text(0.008, y, text, fontsize=FOOT_FS, color=colour, va="bottom", ha="left",
                 linespacing=FOOT_LINE, gid=C.PLATE_KEEP)
        y += n * lh + gap
    return y - gap + 0.004


def _title_pad(ax, extra_pt: float = 0.0) -> float:
    """Separación del título de panel, con el sitio que le hayan reservado encima.

    El rótulo horizontal del eje derecho (`_right_ylabel`) vive entre el panel y su título: el título tiene
    que subir lo justo para dejarle su renglón, y ni `_letter` ni `_anchor_titles` —que reescriben el
    título— pueden volver a bajarlo."""
    pad = float(getattr(ax, "_pl_title_pad", 3.5)) + float(extra_pt)
    ax._pl_title_pad = pad
    return pad


def _right_ylabel(ax2, text, base=None):
    """Rótulo del eje Y DERECHO de un panel gemelo, que nunca cae sobre sus propias marcas.

    Se coloca MIDIENDO la columna de marcas ya dibujada (`common.plate_ylabel`), y el sitio para que quepa
    entero dentro de la celda lo abre `_fit_cells` encogiendo el panel. Escrito sin medir, la guarda de
    recorte lo devolvía dentro de la celda imprimiéndolo sobre sus propias cifras: es el defecto que los
    verificadores describieron en S38 (e) («0,80 · 0,90 · 1,00» bajo el rótulo) y en S40 (c) («siete
    marcas»). `base` se acepta para el panel que lo alberga; ya no hace falta subirle el título."""
    return C.plate_ylabel(ax2, text, right=True)


#: Hueco mínimo, en puntos, entre el título de un panel y el del panel VECINO de la derecha. Sin él el
#: límite de plegado era el borde de la celda y el título de la columna izquierda podía terminar a 1,4 pt
#: del paréntesis que abre el de la derecha —un tercio del espacio de palabra que llevan dentro—, de modo
#: que las dos líneas se leían como una sola frase («… 2019–2024 — Smoothed(b) GRD persons/year …»).
#: 14 pt son más de tres espacios de palabra: el corte entre un título y el siguiente se ve.
TITLE_GUTTER_PT = 14.0


def _plate_column(ax, pos) -> int:
    """Columna de la rejilla a la que pertenece un panel, leída del `SubplotSpec`."""
    try:
        top = ax.get_subplotspec().get_topmost_subplotspec()
        return int(top.colspan.start) % PLATE_COLS
    except (AttributeError, ValueError, TypeError):
        return 0 if pos.x0 + pos.width / 2 < 0.5 else 1


def _anchor_titles(fig):
    """Alinea el título de cada panel con el borde IZQUIERDO VISIBLE del panel.

    `loc="left"` alinea con el borde de los ejes, no con el del panel: cuando el eje y lleva rótulos
    largos (las fuentes de E26b, los dominios de E23) el título arrancaba muy a la derecha y se salía
    del lienzo. Se resuelve primero el reparto, se congela y después se recoloca el título sobre el
    borde de las marcas del eje y, que es donde el lector ve empezar el panel.
    """
    fig.canvas.draw()
    fig.set_layout_engine("none")
    r = fig.canvas.get_renderer()
    width = fig.bbox.width
    edges = []
    for ax in fig.axes:
        if not ax.get_title(loc="left"):
            continue
        pos = ax.get_position()
        left = pos.x0
        try:
            left = min(left, ax.yaxis.get_tightbbox(r).x0 / width)
        except (AttributeError, ValueError, TypeError):
            pass
        # El título nunca arranca fuera de SU celda: cuando las marcas del eje Y de un panel de la columna
        # derecha son largas y cruzan la mitad del lienzo, su título arrancaba dentro de la columna
        # izquierda y se imprimía sobre el título del panel vecino.
        cell_left = _plate_column(ax, pos) / PLATE_COLS
        edges.append((ax, pos, min(max(left, cell_left + 0.004), pos.x0)))
    # una sola sangría por columna: los títulos de la misma columna arrancan alineados
    columns: dict[int, float] = {}
    keys = {}
    for ax, pos, left in edges:
        key = _plate_column(ax, pos)
        keys[id(ax)] = key
        columns[key] = min(columns.get(key, left), left)
    for ax, pos, left in edges:
        key = keys[id(ax)]
        x0 = columns[key]
        # El título arranca en x0, que no es el borde de la celda sino el borde VISIBLE de la columna: el
        # ancho que le queda hasta el borde derecho de su celda es lo que hay, y a ese ancho se pliega. Sin
        # este segundo plegado los títulos largos se cortaban contra el borde del lienzo («Spearman's r»,
        # «(smoothed rati», «between peri»).
        # El borde derecho útil no es el de la CELDA sino donde ARRANCA el título del panel vecino, que
        # puede empezar a la izquierda de ese borde; y hasta él hay que dejar un hueco visible.
        right = columns.get(key + 1)
        gutter = TITLE_GUTTER_PT if right is not None else 4.0
        if right is None:
            right = (key + 1) / PLATE_COLS
        disponible = max(60.0, (right - x0) * width * 72.0 / fig.dpi - gutter)
        texto = " ".join(ax.get_title(loc="left").split())
        ax.set_title(C.plate_wrap(texto, disponible, FS_TITLE, "bold"), loc="left", fontsize=FS_TITLE,
                     fontweight="bold", pad=_title_pad(ax), x=(x0 - pos.x0) / pos.width)


def _deco_span(group, r):
    """Extremos izquierdo y derecho de un panel CONTANDO sus adornos de eje Y (marcas y rótulo)."""
    box = C._pl_extent(group[0], r)
    if box is None:
        return None
    x0, x1 = box.x0, box.x1
    for a in group:
        if not getattr(a, "axison", True) or not a.yaxis.get_visible():
            continue
        for art in [a.yaxis.label] + list(C._pl_tick_texts(a.yaxis)):
            if art is None or not str(art.get_text()).strip():
                continue
            b = C._pl_extent(art, r)
            if b is not None:
                x0, x1 = min(x0, b.x0), max(x1, b.x1)
    return x0, x1


def _fit_cells(fig, rounds: int = 3, gap: float = 6.0) -> None:
    """Encoge un panel solo cuando sus adornos llegarían a tocar los del panel vecino o el borde.

    `constrained_layout` reparte los adornos del eje por el PASILLO que queda entre las dos columnas, y
    ahí no estorban: el rótulo del eje derecho de un panel de la izquierda vive en ese pasillo desde
    siempre. Lo que no puede pasar es que dos paneles se disputen el mismo pasillo, ni que un rótulo se
    salga del lienzo. Cuando eso ocurre se le quita ancho al PANEL —a los dos, a partes iguales— en vez de
    mover el rótulo sobre sus propias marcas, que es lo que hacía la guarda de recorte y lo que los
    verificadores leyeron en S38 (e) y S40 (c)."""
    width = fig.bbox.width
    for _ in range(rounds):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        groups = [g for g in C._pl_axes_groups(fig) if C._pl_extent(g[0], r) is not None]
        rows: dict = {}
        shave: dict = {}
        for g in groups:
            # La fila se lee de la REJILLA, no de la posición: dos paneles de la misma fila no comparten
            # `y0` cuando uno lleva las marcas del eje X giradas y el otro no, y agrupándolos por posición
            # el par (e)-(f) de S42 no se comparaba nunca —de ahí que los rótulos de fila del panel (f)
            # cruzaran la mitad del lienzo y el título del panel (d) arrancara dentro de la columna
            # izquierda, impreso sobre el título del panel (c)—.
            try:
                top = g[0].get_subplotspec().get_topmost_subplotspec()
                key = int(top.rowspan.start)
            except (AttributeError, ValueError, TypeError):
                key = round(g[0].get_position().y0, 3)
            rows.setdefault(key, []).append(g)
            span = _deco_span(g, r)
            if span is None:
                continue
            shave[id(g[0])] = [max(0.0, 1.0 - span[0]), max(0.0, span[1] - (width - 1.0))]
        for _y, row in rows.items():
            row.sort(key=lambda g: g[0].get_position().x0)
            for left, right in zip(row[:-1], row[1:]):
                a, b = _deco_span(left, r), _deco_span(right, r)
                if a is None or b is None:
                    continue
                clash = (a[1] + gap) - b[0]
                if clash > 0.5:
                    shave[id(left[0])][1] += clash / 2.0
                    shave[id(right[0])][0] += clash / 2.0
        moved = False
        for g in groups:
            dl, dr = shave.get(id(g[0]), (0.0, 0.0))
            if dl < 0.5 and dr < 0.5:
                continue
            pos = g[0].get_position()
            new_w = pos.width - (dl + dr) / width
            if new_w <= 0.35 * pos.width:
                continue
            for a in g:
                a.set_position([pos.x0 + dl / width, pos.y0, new_w, pos.height])
            moved = True
        if not moved:
            return


def _keep_axis_labels(fig) -> None:
    """El rótulo de un eje es del eje: nadie lo mueve.

    La guarda de recorte de `plate_resolve` devuelve dentro de la celda todo lo que sobresale, y con el
    rótulo del eje su remedio es peor que la enfermedad: empujarlo lo imprime sobre las cifras que
    rotula. El sitio ya lo garantiza `_fit_cells`, que le hace hueco encogiendo el panel."""
    for ax in fig.axes:
        for lbl in (ax.xaxis.label, ax.yaxis.label):
            if lbl is not None and str(lbl.get_text()).strip():
                lbl.set_gid(C.PLATE_KEEP)


def _legend_below_axis_label(ax, lg, pad_px: float = 2.5) -> None:
    """Baja la leyenda colgada del panel hasta quedar DEBAJO del rótulo del eje X.

    `plate_place_legend` la cuelga bajo las marcas del eje; el rótulo del eje («Año») vive por debajo de
    ellas y quedaba tapado por el recuadro blanco de la leyenda, que es lo que se veía en S44 (e)-(f).
    Se mide y se baja lo que falte, dándole al panel esa altura de menos."""
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    lb = C._pl_extent(lg, r)
    xl = C._pl_extent(ax.xaxis.label, r)
    axb = C._pl_extent(ax, r)
    if lb is None or xl is None or axb is None or axb.height <= 0:
        return
    delta = lb.y1 - (xl.y0 - pad_px)
    if delta <= 0:
        return
    anchor = lg.get_bbox_to_anchor()
    try:
        y = (anchor.y0 - axb.y0) / axb.height
    except (AttributeError, ZeroDivisionError):
        return
    lg.set_bbox_to_anchor((0.5, y - delta / axb.height), transform=ax.transAxes)
    pos = ax.get_position()
    drop = delta / fig.bbox.height
    if 0 < drop < pos.height * 0.4:
        ax.set_position([pos.x0, pos.y0 + drop, pos.width, pos.height - drop])
    fig.canvas.draw()


def _place_legends(fig) -> None:
    """Cada leyenda, al primer anclaje que no tapa NI dato NI rótulo del panel.

    `C.plate_place_legend` se queda con el primer anclaje de los nueve que no tiene tinta de datos debajo
    y, si no hay ninguno, saca la leyenda bajo el eje X con sitio reservado. El ORDEN en que se le ofrecen
    los nueve es lo que decide cuál de los libres se usa: aquí se ordenan por lo que taparían de lo ya
    escrito en el panel —la marca de la pandemia, la de la Ley, el título, los rótulos de valor—, de modo
    que la leyenda no cambia «tapar una barra» por «taparle el rótulo a otro».
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for group in C._pl_axes_groups(fig):
        for ax in group:
            lg = ax.get_legend()
            if lg is None or not lg.get_visible() or lg.get_gid() == C.PLATE_KEEP:
                continue
            axb = C._pl_extent(ax, r)
            lg.set_bbox_to_anchor(None)          # el anclaje propio se cede al motor de colocación
            b = C._pl_extent(lg, r)
            if axb is None or b is None:
                continue
            obstacles = []
            for a in group:
                for t in a.texts:
                    if not t.get_visible() or not str(t.get_text()).strip():
                        continue
                    if t.get_transform() is a.transData:
                        continue                 # rótulo de valor: lo vigila la otra familia
                    q = C._pl_extent(t, r)
                    if q is not None:
                        obstacles.append(q)
                ttl = next((c for c in (getattr(a, "_left_title", None), a.title)
                            if c is not None and c.get_text()), None)
                if ttl is not None:
                    q = C._pl_extent(ttl, r)
                    if q is not None:
                        obstacles.append(q)
            pad = 0.012 * min(axb.width, axb.height) + 2.0
            order = sorted(C._PL_LOCS,
                           key=lambda loc: sum(C._pl_over(C._pl_loc_box(loc, axb, b.width, b.height, pad), q)
                                               for q in obstacles))
            loc = C.plate_place_legend(ax, prefer=tuple(order))
            placed = ax.get_legend()
            if placed is not None:
                # Colocada a conciencia: el motor de `plate_resolve` no vuelve a probar formas ni sitios.
                placed.set_gid(C.PLATE_KEEP)
                placed.set_zorder(max(6, placed.get_zorder()))
            if loc == "outside below" and placed is not None:
                _legend_below_axis_label(ax, placed)


def _save_plate(fig, path: Path, plt):
    """Guarda a 600 ppp SIN recorte «tight»: el archivo mide exactamente 180 × 245 mm.

    Las anotaciones dentro de un panel (`ax.text`, `annotate`) se excluyen del cálculo del reparto:
    `constrained_layout` las suma al recuadro del panel y, con una nota larga, concluía que el panel
    medía cero y abandonaba el reparto —de ahí las láminas descuadradas de la versión anterior—.
    Los títulos, los rótulos de eje, las marcas y las leyendas sí siguen contando.
    """
    _set_plate_rect(fig, _draw_foot(fig))
    for ax in fig.axes:
        for txt in ax.texts:
            txt.set_in_layout(False)
    # Motor de descongestión (common.py): mide lo dibujado y resuelve colisiones, recortes y leyendas.
    # `plate_fit` actúa con la composición todavía viva (marcas de eje, rótulos de eje, leyendas);
    # `plate_resolve`, ya congelada, separa los rótulos que se pisan y devuelve dentro lo que se sale.
    # LA RAYA DEL INTERVALO (fase 4j, tarea J2) la aplica `plate_fit` en su primera línea, con la regla
    # única del estudio (`common.range_dash`): este módulo era uno de los cuatro que dibujan láminas y no
    # la tenían —488 intervalos con guion frente a 402 con raya en la E20, la E21, la E23 y la E26b—, y
    # ahora la hereda sin llamarla, con el texto ya definitivo cuando el motor mide.
    C.plate_fit(fig)
    _anchor_titles(fig)
    _fit_cells(fig)
    # Con la anchura definitiva se vuelven a ajustar marcas, rótulos y leyendas (el reparto ya está
    # congelado, así que `plate_fit` no mueve los paneles: solo lo que se dibuja dentro y al lado).
    C.plate_fit(fig)
    _anchor_titles(fig)
    _keep_axis_labels(fig)
    _fit_forest_labels(fig)
    _place_legends(fig)
    C.plate_frame_notes(fig)
    C.plate_resolve(fig)
    path = Path(path)
    # Modo revista (LANCET_PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=PLATE_DPI, facecolor="white")
    plt.close(fig)
    return path


def _fit_forest_labels(fig) -> None:
    """Ensancha el eje de un forest hasta que su columna de rótulos cabe DENTRO del panel.

    Los rótulos («4,57 (3,70–5,63); n=129») se anclan al extremo superior de su intervalo y, cuando la
    estimación del ancho del panel se queda corta, el más ancho se sale por el borde derecho del lienzo:
    impreso a 180 mm, el último dígito cae sobre el corte. Con la composición ya congelada se mide lo
    dibujado y se estira el límite del eje —lo que acerca cada rótulo al centro— hasta que ninguno asoma."""
    fig.canvas.draw()
    r = C._pl_renderer(fig, draw=False)
    for ax in fig.axes:
        items = getattr(ax, "_forest_labels", None)
        if not items:
            continue
        pad = float(getattr(ax, "_forest_pad", 0.0))
        for _ in range(6):
            axb = C._pl_extent(ax, r)
            if axb is None:
                break
            over = 0.0
            for t, _xh in items:
                b = C._pl_extent(t, r)
                if b is not None:
                    over = max(over, b.x1 - (axb.x1 - 1.0))
            if over <= 0.5:
                break
            x0, x1 = ax.get_xlim()
            new_x1 = x1 * (1.0 + over / max(axb.width, 1.0) * 1.12)
            ax.set_xlim(x0, new_x1)
            for t, xh in items:
                t.set_x(xh + pad * new_x1)
            fig.canvas.draw()
            r = fig.canvas.get_renderer()


def _abbrev(s, n=26):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _abbrev_distinct(values, lang: str, n: int = 26, cap: int = 38) -> list[str]:
    """Abrevia una lista de áreas funcionales REM-20 SIN volver indistinguibles dos de ellas.

    Recortar por caracteres a ciegas imprimía «Médico-Quirúrgico Cuidado…» en dos filas seguidas del panel
    (e) de la Figura E22: dos áreas funcionales distintas con el mismo rótulo, que el lector no puede
    separar ni completar. Y abreviar SIEMPRE la cadena española —el REM-20 sólo publica el nombre en
    español— rotulaba las diez barras del panel (e) en español dentro de la lámina inglesa. Aquí se parte
    del nombre del área EN EL IDIOMA DEL DOCUMENTO (`labels.rem20_area_short`, que aplica el glosario de
    recorte de ese mismo idioma) y, si el recorte todavía deja dos rótulos iguales, se alarga hasta que
    dejan de serlo (o se imprime el nombre entero). El nombre completo, en el idioma del documento, está
    declarado en `labels.REM20_AREA`."""
    full = [LB_AREA_SHORT(v, lang) for v in values]
    for width in range(n, cap + 1, 2):
        out = [_abbrev(t, width) for t in full]
        if len(set(out)) == len(out):
            return out
    return full


def _region_short(name, n=17):
    """Nombre de región abreviado por el glosario de la norma antes de cortarlo por la mitad.

    Cortar por caracteres dejaba en el eje «Metropolitana de…», «Libertador Gener…» y «Aysén del
    Genera…»: tres nombres distintos que el lector no puede completar. El glosario de `common` da la
    forma corta que usa la revista y el nombre completo sigue en la tabla acompañante."""
    s = str(name)
    return _abbrev(REGION_SHORT.get(s, C.PLATE_LABEL_GLOSSARY.get(s, s)), n)


#: Formas cortas que el glosario de `common` no trae porque la fuente INE las escribe con el nombre largo.
REGION_SHORT = {"Metropolitana de Santiago": "Metropol.",
                "Libertador General Bernardo O'Higgins": "O'Higgins",
                "Aysén del General Carlos Ibáñez del Campo": "Aysén",
                "Magallanes y de la Antártica Chilena": "Magallanes",
                "Arica y Parinacota": "Arica y P."}


def _wrap(text: str, width: int = 60) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(str(text), width))


#: Ancho de línea del título de panel: 85 mm de panel a 9 pt en negrita ≈ 42 caracteres.
TITLE_WRAP = 38


#: Ancho útil del título dentro de una celda: media lámina menos 5 mm de margen y el hueco de la letra.
TITLE_W_PT = (PLATE_W_IN * 72.0) / 2 - (5.0 / 25.4 * 72.0) - 12.0


def _title(ax, text, width=None, **kw):
    """Título de panel plegado al ancho MEDIDO de la celda, sin el prefijo «A. » heredado.

    Contar caracteres dejaba títulos largos —sobre todo en español, un 15 % más largo— fuera de la celda
    y cortados contra el borde del lienzo. `width` se acepta y se ignora por compatibilidad."""
    s = re.sub(r"^[A-F]\.\s+", "", str(text))
    s = "\n".join(C.plate_wrap(part, TITLE_W_PT, FS_TITLE, "bold") for part in s.split("\n"))
    kw.setdefault("fontsize", FS_TITLE)
    return ax.set_title(s, **kw)


def fig_e20(P, lang, fdir):
    plt, fig, A = _new_plate()
    pyr, natl, reg, bases, age24 = P["pyramid"], P["national"], P["regions"], P["bases"], P["age2024"]
    natl = natl.set_index("year")
    ypos = np.arange(len(AGE5))

    for k, (year, a) in enumerate(((2019, A[0]), (2025, A[1]))):
        p = pyr[pyr.year == year].set_index("age_group").reindex(AGE5)
        total = float(p[["HOMBRE", "MUJER"]].sum().sum())
        a.barh(ypos, -100 * p.HOMBRE / total, height=0.82, color=OKABE[0], label=tr("males", lang))
        a.barh(ypos, 100 * p.MUJER / total, height=0.82, color=OKABE[1], label=tr("females", lang))
        a.set_yticks(ypos); a.set_yticklabels(AGE5, fontsize=6.5)
        a.set_xlabel(tr("e20_pct_axis", lang)); a.set_ylabel(tr("age_group", lang))
        lim = max(4.6, 1.15 * float(np.nanmax(100 * p[["HOMBRE", "MUJER"]].max() / total)))
        a.set_xlim(-lim, lim)
        a.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _p: C.fmt_number(abs(v), 0, lang)))
        a.axvline(0, color="#333333", lw=0.8)
        # El total de personas es una cifra del PANEL ENTERO y su sitio es el título: escrita dentro, en
        # cualquiera de las cuatro esquinas, competía con la leyenda por el único hueco libre de una
        # pirámide y acababa sobre las barras de 75-79 y 80+. La banda reservada arriba queda entonces
        # entera para la leyenda.
        reserve_band(a, 0.11)
        a.legend(loc="upper right", fontsize=8)
        _title(a, f"{tr('e20_a' if k == 0 else 'e20_b', lang)} · {num(total, 0, lang)} "
                  f"{tr('persons', lang).lower()}")
        _letter(a, k)

    c = A[2]
    r19 = reg[reg.year == 2019].set_index("cut_region")
    r25 = reg[reg.year == 2025].set_index("cut_region")
    order = r25.sort_values("population").index
    yr = np.arange(len(order))
    c.barh(yr - 0.2, r19.reindex(order).population / 1e3, height=0.38, color="#9ecae1", label="2019")
    c.barh(yr + 0.2, r25.reindex(order).population / 1e3, height=0.38, color=OKABE[0], label="2025")
    c.set_yticks(yr); c.set_yticklabels([_region_short(r25.at[i, "region_name"]) for i in order], fontsize=6.5)
    c.set_xlabel(tr("e20_pop_thousands", lang)); c.set_xscale("log"); log_axis_fmt(c, lang, "x")
    for j, i in enumerate(order):
        ch = 100 * (r25.at[i, "population"] - r19.at[i, "population"]) / r19.at[i, "population"]
        # El signo de porcentaje se compone con `pct`, que pone el espacio antes del signo en español
        # («+1,7 %») y lo omite en inglés («+1.7%»), como el resto del estudio.
        c.text(r25.at[i, "population"] / 1e3 * 1.08, yr[j], f"{'+' if ch >= 0 else ''}{pct(ch, lang, 1)}",
               fontsize=6.3, va="center", color="#333333")
    c.set_xlim(None, float(r25.population.max()) / 1e3 * 2.6)
    c.legend(loc="lower right", fontsize=8); _title(c, tr("e20_c", lang)); _letter(c, 2)

    d = A[3]
    b = bases.set_index("year")
    d.plot(b.index, b.base2017_national_30jun / 1e6, "o-", color=OKABE[0], lw=2, label=tr("e20_base2017", lang))
    d.plot(b.index, b.base2024_national_30jun / 1e6, "s--", color=OKABE[1], lw=2, label=tr("e20_base2024", lang))
    d.set_xticks(list(b.index)); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("e20_pop_axis", lang))
    fmt_axis(d, lang, "y", 1)
    d2 = d.twinx(); d2.grid(False); d2.spines["right"].set_visible(True)
    d2.plot(b.index, b.ratio_base2024_to_base2017_30jun, "^:", color=GREY, lw=1.5, markersize=5,
            label=tr("e20_ratio_axis", lang))
    d2.set_ylim(0.97, 1.03); fmt_axis(d2, lang, "y", 3)
    _right_ylabel(d2, tr("e20_ratio_axis", lang), base=d)
    _note(d, "d", tr("e20_note_bases", lang))
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels()
    d.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=7.2)
    _title(d, tr("e20_d", lang)); _letter(d, 3)

    e = A[4]
    a24 = age24.set_index("age_group").reindex(AGE5)
    xe = np.arange(len(AGE5))
    e.bar(xe - 0.2, a24.base2017_2024 / 1e3, width=0.38, color=OKABE[0], label=tr("e20_base2017", lang))
    if a24.censo2024.notna().any():
        e.bar(xe + 0.2, a24.censo2024 / 1e3, width=0.38, color=OKABE[2], label=tr("e20_censo2024", lang))
    else:
        e.text(0.5, 0.5, tr("not_estimable", lang), transform=e.transAxes, ha="center", fontsize=8, color=GREY)
    e.set_xticks(xe); e.set_xticklabels(AGE5, rotation=90, fontsize=6.2)
    e.set_xlabel(tr("age_group", lang)); e.set_ylabel(tr("e20_pop_thousands_all", lang)); fmt_axis(e, lang, "y", 0)
    e2 = e.twinx(); e2.grid(False); e2.spines["right"].set_visible(True)
    e2.plot(xe, a24.ratio, "k^:", markersize=4, lw=1.2)
    e2.axhline(1.0, color=GREY, lw=0.8, ls="--")
    if a24.ratio.notna().any():
        lo_r, hi_r = float(np.nanmin(a24.ratio)), float(np.nanmax(a24.ratio))
        e2.set_ylim(min(0.85, lo_r * 0.95), max(1.15, hi_r * 1.05))
    fmt_axis(e2, lang, "y", 2)
    # El rótulo del eje derecho se coloca MIDIENDO su columna de marcas: escrito sin medir, la guarda de
    # recorte lo empujaba hacia dentro y acababa impreso sobre sus propias cifras (0,80 · 0,90 · 1,00).
    _right_ylabel(e2, {"es": "Razón Censo 2024 / base 2017", "en": "Ratio Censo 2024 / 2017 base"}[lang],
                  base=e)
    e.legend(loc="upper right", fontsize=8); _title(e, tr("e20_e", lang)); _letter(e, 4)

    f = A[5]
    f.bar(natl.index, natl.population / 1e6, width=0.62, color=OKABE[0])
    for y in natl.index:
        f.text(y, natl.at[y, "population"] / 1e6 + 0.12, num(natl.at[y, "population"] / 1e6, 2, lang),
               ha="center", fontsize=7, color="#333333")
    f.set_ylim(0, float(natl.population.max()) / 1e6 * 1.22)
    f.set_xticks(list(natl.index)); f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("e20_pop_axis", lang))
    fmt_axis(f, lang, "y", 1)
    f2 = f.twinx(); f2.grid(False); f2.spines["right"].set_visible(True)
    f2.plot(natl.index, natl.child_share_pct, "s-", color=OKABE[1], lw=2, markersize=5)
    fmt_axis(f2, lang, "y", 1)
    f2.set_ylim(float(natl.child_share_pct.min()) - 1.2, float(natl.child_share_pct.max()) + 1.2)
    _right_ylabel(f2, tr("e20_share_axis", lang), base=f)
    _title(f, tr("e20_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E20']}.png", plt)
    return path


def fig_e21(P, lang, fdir):
    plt, fig, A = _new_plate()
    last = P["last_year"]
    tramo, cov = P["tramo"], P["coverage"]

    a = A[0]
    cols = [c for c in ["A", "B", "C", "D"] if c in tramo.columns]
    bottom = np.zeros(len(tramo))
    for i, ccol in enumerate(cols):
        a.bar(tramo.index, tramo[ccol] / 1e6, bottom=bottom, width=0.66, color=OKABE[i],
              label=f"{tr('e21_tramo', lang)} {ccol}")
        bottom += (tramo[ccol] / 1e6).values
    a.set_xticks(list(tramo.index)); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("e21_benef_axis", lang))
    fmt_axis(a, lang, "y", 1)
    for y in tramo.index:
        a.text(y, bottom[list(tramo.index).index(y)] + 0.2, num(tramo.loc[y, cols].sum() / 1e6, 2, lang),
               ha="center", fontsize=7, color="#333333")
    a.set_ylim(0, bottom.max() * 1.42)
    _note(a, "a, f", tr("e21_note_stock", lang))
    a.legend(loc="upper left", fontsize=6.4, ncol=2)
    _title(a, tr("e21_a", lang)); _letter(a, 0)

    b = A[1]
    fas = P["fonasa_age_sex"]
    fl = fas[fas.year == last].pivot_table(index="age_band_5y", columns="sex", values="beneficiaries", aggfunc="sum")
    fl = fl.reindex(AGE5)
    xb = np.arange(len(AGE5))
    b.bar(xb - 0.2, fl.HOMBRE / 1e3, width=0.38, color=OKABE[0], label=tr("males", lang))
    b.bar(xb + 0.2, fl.MUJER / 1e3, width=0.38, color=OKABE[1], label=tr("females", lang))
    b.set_xticks(xb); b.set_xticklabels(AGE5, rotation=90, fontsize=6.2)
    b.set_xlabel(tr("age_group", lang)); b.set_ylabel(tr("e21_benef_thousands", lang)); fmt_axis(b, lang, "y", 0)
    exc = P["fonasa_excluded"]
    exc_last = float(exc.loc[exc.year == last, "outside_sex_age_grid"].iloc[0]) if len(exc[exc.year == last]) else 0.0

    _note(b, "b", {"es": f"Fuera de la rejilla sexo × banda quinquenal: {num(exc_last, 0, lang)} "
                         "beneficiarios (sexo indeterminado o edad sin información). El archivo de 2023 "
                         "publica solo bandas decenales y no aparece aquí.",
                   "en": f"Outside the sex × five-year band grid: {num(exc_last, 0, lang)} beneficiaries "
                         "(indeterminate sex or age not reported). The 2023 file publishes ten-year bands "
                         "only and is not shown here."}[lang])
    b.legend(loc="upper right", fontsize=6.4, framealpha=0.9)
    _title(b, f"{tr('e21_b', lang)} ({last} · {tr('dec_stock', lang)})"); _letter(b, 1)

    c = A[2]
    ia = P["isapre_age"]
    first_i = int(ia.year.min())
    for yy, colr, mk in ((first_i, "#9ecae1", "o"), (last, OKABE[0], "s")):
        s = ia[ia.year == yy].set_index("age_band_5y").reindex(AGE5)
        c.plot(np.arange(len(AGE5)), s.beneficiarios / 1e3, mk + "-", color=colr, lw=2, markersize=5, label=str(yy))
    c.set_xticks(np.arange(len(AGE5))); c.set_xticklabels(AGE5, rotation=90, fontsize=6.2)
    c.set_xlabel(tr("age_group", lang)); c.set_ylabel(tr("e21_benef_thousands", lang)); fmt_axis(c, lang, "y", 0)
    out = P["isapre_outside"]
    if len(out):
        o_last = out[out.year == last].outside_age_bands
        _note(c, "c", f"{num(float(o_last.iloc[0]) if len(o_last) else 0, 0, lang)} "
              + {"es": "beneficiarios fuera de las bandas etarias (nonatos o edad no informada).",
                 "en": "beneficiaries outside the age bands (unborn or age not reported)."}[lang])
    c.legend(loc="upper right", fontsize=6.4, framealpha=0.9); _title(c, tr("e21_c", lang)); _letter(c, 2)

    d = A[3]
    ap = P["aps_panel"]
    d.bar(ap.index - 0.19, ap.enrolled_tramo_AD / 1e6, width=0.36, color=OKABE[0], label="A–D")
    d.bar(ap.index + 0.19, ap.enrolled_tramo_X / 1e6, width=0.36, color=OKABE[1], label="X")
    if "enrolled_tramo_missing" in ap.columns:
        d.plot(ap.index, ap.enrolled_tramo_missing / 1e6, "kv:", markersize=4, lw=1.1,
               label={"es": "tramo no informado", "en": "tramo not reported"}[lang])
    d.set_xticks(list(ap.index)); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("e21_enrolled_axis", lang))
    d.set_ylim(0, float(ap.enrolled_tramo_AD.max()) / 1e6 * 1.45)
    fmt_axis(d, lang, "y", 1)
    d2 = d.twinx(); d2.grid(False); d2.spines["right"].set_visible(True)
    d2.plot(ap.index, ap.centres_total, "^-", color=GREY, lw=1.6, markersize=5, label=tr("e21_centres_axis", lang))
    fmt_axis(d2, lang, "y", 0)
    d2.set_ylim(float(ap.centres_total.min()) * 0.9, float(ap.centres_total.max()) * 1.12)
    _right_ylabel(d2, tr("e21_centres_axis", lang), base=d)
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels()
    d.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=6.2, ncol=2, framealpha=0.9)
    _title(d, tr("e21_d", lang)); _letter(d, 3)

    e = A[4]
    rg = P["regional"].copy().sort_values("fonasa_pct")
    ye = np.arange(len(rg))
    e.barh(ye - 0.26, rg.fonasa_pct, height=0.25, color=OKABE[0], label="FONASA")
    e.barh(ye, rg.isapre_pct, height=0.25, color=OKABE[1], label="ISAPRE")
    e.barh(ye + 0.26, rg.aps_pct, height=0.25, color=OKABE[2], label={"es": "Inscritos APS", "en": "APS enrolled"}[lang])
    e.set_yticks(ye); e.set_yticklabels([_region_short(n) for n in rg.region_name], fontsize=6.5)
    e.set_xlabel(tr("e21_share_axis", lang)); fmt_axis(e, lang, "x", 0)
    e.axvline(100, color="#333333", ls="--", lw=0.9); e.set_xlim(0, 118)
    _note(e, "e", tr("e21_note_geo", lang))
    e.legend(loc="upper right", fontsize=6.4, framealpha=0.85)
    _title(e, tr("e21_e", lang) + f" ({last})"); _letter(e, 4)

    f = A[5]
    f.plot(cov.index, cov.ine_population_base2017_30jun / 1e6, "o-", color="#333333", lw=2,
           label={"es": "INE (30 jun, base 2017)", "en": "INE (30 Jun, 2017 base)"}[lang])
    f.plot(cov.index, cov.fonasa_beneficiaries_dec / 1e6, "s-", color=OKABE[0], lw=2, label="FONASA")
    f.plot(cov.index, cov.aps_enrolled_dec / 1e6, "^-", color=OKABE[2], lw=2,
           label={"es": "Inscritos APS", "en": "APS enrolled"}[lang])
    f.plot(cov.index, cov.isapre_beneficiaries_dec / 1e6, "d-", color=OKABE[1], lw=2, label="ISAPRE")
    f.set_xticks(list(cov.index)); f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("e21_benef_axis", lang))
    fmt_axis(f, lang, "y", 0)
    f2 = f.twinx(); f2.grid(False); f2.spines["right"].set_visible(True)
    f2.plot(cov.index, 100 * cov.share_fonasa_plus_isapre_ine, "v:", color=GREY, lw=1.4, markersize=5,
            label={"es": "(FONASA+ISAPRE)/INE", "en": "(FONASA+ISAPRE)/INE"}[lang])
    f2.set_ylim(80, 105); fmt_axis(f2, lang, "y", 0)
    _right_ylabel(f2, "%", base=f)
    h1, l1 = f.get_legend_handles_labels(); h2, l2 = f2.get_legend_handles_labels()
    f_lo, f_hi = f.get_ylim()
    f.set_ylim(f_lo, f_hi + 0.62 * (f_hi - f_lo))   # banda libre arriba para la leyenda de cinco capas
    f.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=6.2, ncol=2, framealpha=0.9)
    _title(f, tr("e21_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E21']}.png", plt)
    return path


def fig_e22(P, lang, fdir):
    plt, fig, A = _new_plate()
    panel, by_year, est, area, eco = P["panel"], P["by_year"], P["per_estab"], P["area"], P["eco"]

    a = A[0]
    a.bar(panel.index - 0.19, panel.discharges_total / 1e6, width=0.36, color=OKABE[0],
          label={"es": "Todos los establecimientos", "en": "All establishments"}[lang])
    a.bar(panel.index + 0.19, panel.discharges_panel_188 / 1e6, width=0.36, color=OKABE[2],
          label={"es": "Panel de 188 establecimientos", "en": "188-establishment panel"}[lang])
    a.set_xticks(list(panel.index)); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("e22_disch_axis", lang))
    fmt_axis(a, lang, "y", 2)
    a2 = a.twinx(); a2.grid(False); a2.spines["right"].set_visible(True)
    a2.plot(panel.index, panel.establishments_reporting, "^-", color=GREY, lw=1.6, markersize=5,
            label=tr("e22_estab_axis", lang))
    fmt_axis(a2, lang, "y", 0)
    a2.set_ylim(float(panel.establishments_reporting.min()) * 0.9, float(panel.establishments_reporting.max()) * 1.15)
    _right_ylabel(a2, tr("e22_estab_axis", lang), base=a)
    context_markers(a, lang, xmin=min(panel.index), xmax=max(panel.index))
    h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    a.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=7.2)
    _title(a, tr("e22_a", lang)); _letter(a, 0)

    b = A[1]
    b.bar(by_year.index - 0.19, by_year.bed_days_available / 1e6, width=0.36, color="#9ecae1",
          label={"es": "Días-cama disponibles", "en": "Available bed-days"}[lang])
    b.bar(by_year.index + 0.19, by_year.bed_days_occupied / 1e6, width=0.36, color=OKABE[0],
          label={"es": "Días-cama ocupados", "en": "Occupied bed-days"}[lang])
    b.set_xticks(list(by_year.index)); b.set_xlabel(tr("year", lang)); b.set_ylabel(tr("e22_bed_axis", lang))
    fmt_axis(b, lang, "y", 1)
    b2 = b.twinx(); b2.grid(False); b2.spines["right"].set_visible(True)
    b2.plot(by_year.index, by_year.occupancy_pct, "s-", color=OKABE[1], lw=2, markersize=5,
            label=tr("e22_occ_axis", lang))
    b2.set_ylim(0, 118); fmt_axis(b2, lang, "y", 0)     # el 18 % de arriba es la banda de los rótulos de contexto
    _right_ylabel(b2, tr("e22_occ_axis", lang), base=b)
    context_markers(b, lang, xmin=min(by_year.index), xmax=max(by_year.index))
    h1, l1 = b.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
    b.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=7.2)
    _title(b, tr("e22_b", lang)); _letter(b, 1)

    c = A[2]
    years = sorted(est.year.unique())
    data = [est[est.year == y].discharges.replace(0, np.nan).dropna().values for y in years]
    bp = c.boxplot(data, positions=range(len(years)), widths=0.6, showfliers=False, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#9ecae1"); patch.set_alpha(0.85); patch.set_edgecolor("#333333")
    for med in bp["medians"]:
        med.set_color(OKABE[1]); med.set_linewidth(1.8)
    c.set_xticks(range(len(years))); c.set_xticklabels([str(y) for y in years])
    c.set_yscale("log"); log_axis_fmt(c, lang)
    c.set_xlabel(tr("year", lang)); c.set_ylabel(tr("e22_disch_axis_n", lang))
    c_lo, c_hi = c.get_ylim()
    c.set_ylim(c_lo, c_hi * 1.6)   # abajo quedan libres los n por año; la nota ya no vive dentro del panel
    for i, y in enumerate(years):
        c.text(i, c_lo * 1.35, num(len(data[i]), 0, lang), ha="center", fontsize=6.6, color="#333333")
    _note(c, "c", tr("e22_note_unit", lang))
    _title(c, tr("e22_c", lang)); _letter(c, 2)

    d = A[3]
    d.plot(panel.index, 100 * panel.retention_discharges, "o-", color=OKABE[0], lw=2, markersize=5,
           label={"es": "Egresos retenidos por el panel", "en": "Discharges retained by the panel"}[lang])
    d.plot(panel.index, 100 * panel.retention_bed_days, "s--", color=OKABE[2], lw=2, markersize=5,
           label={"es": "Días-cama retenidos", "en": "Bed-days retained"}[lang])
    d.set_xticks(list(panel.index)); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("e22_ret_axis", lang))
    d.set_ylim(94, 100.6); fmt_axis(d, lang, "y", 1)
    for y in panel.index:
        d.text(y, 100 * panel.at[y, "retention_discharges"] + 0.10, num(100 * panel.at[y, "retention_discharges"], 1, lang),
               ha="center", fontsize=6.6, color="#333333")
    d.legend(loc="lower left", fontsize=7.5); _title(d, tr("e22_d", lang)); _letter(d, 3)

    e = A[4]
    top = area.head(10).iloc[::-1]
    ye = np.arange(len(top))
    e.barh(ye, top.bed_days_available / 1e3, height=0.7, color=OKABE[0])
    # El prefijo «Área » es común a todas y sólo gasta ancho: sin él los nombres se distinguen.
    e.set_yticks(ye); e.set_yticklabels(_abbrev_distinct(top.area_funcional, lang, 26), fontsize=6.2)
    e.set_xlabel(tr("e22_area_axis", lang)); fmt_axis(e, lang, "x", 0)
    # La barra mide días-cama disponibles; los egresos son otra magnitud y se rotulan aparte,
    # con su unidad, para que el número junto a la barra nunca se lea como el valor de la barra.
    #
    # Los rótulos NO se escriben cada uno en la punta de SU barra. Escrito así, el de la barra más larga
    # («2.236 miles de días-cama», dos líneas de 6,2 pt) no cabía en el 0,38 de eje que quedaba a su
    # derecha, la pasada de colisiones lo devolvía sobre su propia barra y `_pl_backing` le pintaba
    # detrás un recuadro blanco al 0,78 que borraba la mitad de la barra: la categoría MAYOR se imprimía
    # más corta que la segunda y el panel contradecía sus propios datos. Van todos en UNA columna, a la
    # derecha de la barra más larga, con el eje ensanchado hasta que la columna cabe —el mismo patrón de
    # `_fit_forest_labels` que usan los forest de la E23—, de modo que ningún rótulo pisa tinta y la
    # longitud de cada barra vuelve a ser proporcional a su valor.
    labels = []
    for j in range(len(top)):
        bd_k = float(top.bed_days_available.iloc[j]) / 1e3
        dis = float(top.discharges.iloc[j])
        labels.append({"es": f"{num(bd_k, 0, lang)} miles de días-cama\n{num(dis, 0, lang)} egresos",
                       "en": f"{num(bd_k, 0, lang)} thousand bed-days\n{num(dis, 0, lang)} discharges"}[lang])
    bar_max = float(top.bed_days_available.max()) / 1e3
    w_pt = max((max(C.plate_text_width_pt(line, 6.2, "normal") for line in t.split("\n")) for t in labels),
               default=0.0)
    axis_pt = PLATE_W_IN * 72.0 / 2.0 - 78.0      # media lámina menos rótulos de fila, marcas y márgenes
    share = min(0.62, w_pt / axis_pt)
    pad = 5.0 / axis_pt                           # blanco entre la punta de la barra más larga y la columna
    xmax_e = bar_max / max(0.2, 1.0 - share - pad)
    e.set_xlim(0, xmax_e)
    placed_e = []
    for j in range(len(top)):
        t_ = e.text(bar_max + pad * xmax_e, ye[j], labels[j], fontsize=6.2, va="center", ha="left",
                    color="#333333", linespacing=1.25, gid=C.PLATE_KEEP)
        placed_e.append((t_, bar_max))
    # El ancho del panel se estima arriba con la mitad de la lámina menos un margen fijo; el reparto
    # definitivo no es exactamente ese, así que `_fit_forest_labels` vuelve a medir la columna con la
    # composición ya congelada y ensancha el eje hasta que entra entera.
    e._forest_labels = placed_e
    e._forest_pad = pad
    _title(e, f"{tr('e22_e', lang)} ({P['last_year']})"); _letter(e, 4)

    f = A[5]
    if len(eco) > 3:
        colr = [OKABE[0] if bool(v) else OKABE[1] for v in eco.in_fixed_panel]
        f.scatter(eco.discharges, eco.n_f84_any.clip(lower=0.5), c=colr, s=30, alpha=0.85, edgecolor="white",
                  linewidth=0.5)
        f.set_xscale("log"); f.set_yscale("log"); log_axis_fmt(f, lang); log_axis_fmt(f, lang, "x")
        f.set_xlabel({"es": f"Egresos REM-20 del establecimiento, {P['grd_year']}",
                      "en": f"REM-20 discharges of the establishment, {P['grd_year']}"}[lang])
        f.set_ylabel(tr("e22_f84_axis", lang))
        note = ({"es": f"ρ de Spearman = {num(P['rho'], 2, lang)}; n = {num(len(eco), 0, lang)} establecimientos enlazados por código DEIS.",
                 "en": f"Spearman ρ = {num(P['rho'], 2, lang)}; n = {num(len(eco), 0, lang)} establishments linked by DEIS code."}[lang])
        # La nube ocupa el panel entero: las dos notas, escritas dentro, tapaban una de cada siete
        # observaciones. Bajan al pie, con la letra del panel delante y la advertencia en rojo.
        _note(f, "f", note)
        _note(f, "f", tr("e22_eco_warn", lang), colour=C.RED)
        from matplotlib.lines import Line2D
        f.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=OKABE[0], markersize=7,
                                 label={"es": "Panel fijo de 65", "en": "Fixed panel of 65"}[lang]),
                          Line2D([0], [0], marker="o", color="w", markerfacecolor=OKABE[1], markersize=7,
                                 label={"es": "Hospital incorporado después", "en": "Hospital added later"}[lang])],
                 loc="lower right", fontsize=7)
    else:
        f.text(0.5, 0.5, tr("not_estimable", lang), transform=f.transAxes, ha="center", fontsize=8, color=GREY)
    _title(f, tr("e22_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E22']}.png", plt)
    return path


SUBGROUP_LABEL = {"total": {"es": "Total del dominio", "en": "Domain total"},
                  "Hombre": {"es": "Hombres", "en": "Males"}, "Mujer": {"es": "Mujeres", "en": "Females"}}
DOMAIN_SHORT = {
    "ENDIDE adultos 18+: autismo reportado": {"es": "ENDIDE adultos: reportado", "en": "ENDIDE adults: reported"},
    "ENDIDE NNA 2-17: autismo reportado": {"es": "ENDIDE NNA: reportado", "en": "ENDIDE children: reported"},
    "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico":
        {"es": "ENDIDE NNA: reportado y confirmado", "en": "ENDIDE children: reported & confirmed"},
    "ENDIDE NNA con autismo reportado: confirmado por un médico":
        {"es": "ENDIDE NNA: confirmado | reportado", "en": "ENDIDE children: confirmed | reported"},
    "ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)":
        {"es": "ENDIDE NNA: confirmado (sensib.)", "en": "ENDIDE children: confirmed (sens.)"},
    "ENDIDE NNA con autismo reportado: ha recibido medicamento":
        {"es": "ENDIDE NNA: medicamento | reportado", "en": "ENDIDE children: medication | reported"},
    "ENDIDE NNA con autismo reportado: ha recibido otro tratamiento":
        {"es": "ENDIDE NNA: otro tratamiento | reportado", "en": "ENDIDE children: other treatment | reported"},
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista":
        {"es": "ENCAVI 15+: diagnosticado", "en": "ENCAVI 15+: diagnosed"},
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)":
        {"es": "ENCAVI 15+: diagnosticado (sensib.)", "en": "ENCAVI 15+: diagnosed (sens.)"},
    "ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico":
        {"es": "ENCAVI: en tratamiento | diagnosticado", "en": "ENCAVI: in treatment | diagnosed"},
}


def _domain_short(row, lang):
    base = DOMAIN_SHORT.get(row.domain, {"es": row.domain, "en": row.domain})[lang]
    return f"{base} · {_sub_label(row, lang)}"


#: Rótulo compacto y ÚNICO de cada dominio para el eje y de los paneles d–f (≤ 26 caracteres): con el
#: rótulo de `DOMAIN_SHORT` truncado, dos dominios distintos de ENDIDE quedaban con el mismo texto.
DOMAIN_TINY = {
    "ENDIDE adultos 18+: autismo reportado": {"es": "ENDIDE 18+: reportado", "en": "ENDIDE 18+: reported"},
    "ENDIDE NNA 2-17: autismo reportado": {"es": "ENDIDE 2–17: reportado", "en": "ENDIDE 2–17: reported"},
    "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico":
        {"es": "ENDIDE 2–17: rep.+conf.", "en": "ENDIDE 2–17: rep.+conf."},
    "ENDIDE NNA con autismo reportado: confirmado por un médico":
        {"es": "ENDIDE 2–17: conf.|rep.", "en": "ENDIDE 2–17: conf.|rep."},
    "ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)":
        {"es": "ENDIDE 2–17: conf. (sens.)", "en": "ENDIDE 2–17: conf. (sens.)"},
    "ENDIDE NNA con autismo reportado: ha recibido medicamento":
        {"es": "ENDIDE 2–17: medic.|rep.", "en": "ENDIDE 2–17: medic.|rep."},
    "ENDIDE NNA con autismo reportado: ha recibido otro tratamiento":
        {"es": "ENDIDE 2–17: trat.|rep.", "en": "ENDIDE 2–17: treat.|rep."},
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista":
        {"es": "ENCAVI 15+: diagnóstico", "en": "ENCAVI 15+: diagnosed"},
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)":
        {"es": "ENCAVI 15+: diag. (sens.)", "en": "ENCAVI 15+: diag. (sens.)"},
    "ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico":
        {"es": "ENCAVI 15+: trat.|diag.", "en": "ENCAVI 15+: treat.|diag."},
}

FLAG_TEXT = {"few_cases": {"es": "< 30 casos", "en": "< 30 cases"},
             "high_rse": {"es": "EER > 30 %", "en": "RSE > 30%"}}


def _sub_label(row, lang):
    if row.subgroup_type == "total":
        return SUBGROUP_LABEL["total"][lang]
    if row.subgroup_type == "sex":
        return SUBGROUP_LABEL.get(row.subgroup, {"es": row.subgroup, "en": row.subgroup})[lang]
    return f"{row.subgroup} " + ({"es": "años", "en": "years"}[lang])


def _survey_forest(ax, rows, lang, title, letter=None, note=None, note_colour="#555555"):
    """Forest de un dominio de encuesta.

    El rótulo de cada fila —estimación, intervalo y casos— se escribe a la DERECHA del extremo superior
    del intervalo, con la separación medida en puntos y no en unidades del dato: con una separación
    proporcional al máximo del panel, el rótulo de la fila más ancha caía sobre su propia barra y el
    remate del bigote se comía el punto decimal («0|91» en lugar de «0,91», S38 (a), fila 18-29). Se marca
    además como colocado a conciencia: es un rótulo ANCLADO A SU FILA y, apartado media fila por el motor
    de descongestión, pasaba a leerse como el valor de la fila vecina (S38 (a), fila 30-44). La nota del
    panel va al pie de la lámina."""
    rows = rows.reset_index(drop=True)
    y = np.arange(len(rows))[::-1]
    labels = []
    for _, r in rows.iterrows():
        txt = f"{num(r.pct, 2, lang)} ({ci(r.pct_lo, r.pct_hi, 2, lang)}); n={num(r.cases, 0, lang)}"
        if not bool(r.reliable):
            # La marca de fiabilidad va en un SEGUNDO renglón: en el mismo, el rótulo de la fila más ancha
            # medía más que el hueco a su derecha y se metía en las marcas del panel vecino.
            txt += "\n" + (FLAG_TEXT["few_cases"][lang] if r.cases < 30 else FLAG_TEXT["high_rse"][lang])
        labels.append(txt)
    # El límite del eje se calcula MIDIENDO el rótulo más ancho: el hueco a la derecha del intervalo tiene
    # que dar para él sin invadir la celda vecina, y con un múltiplo fijo (1,95) no daba.
    w_pt = max((max(C.plate_text_width_pt(line, 6.2, "normal") for line in t.split("\n")) for t in labels),
               default=0.0)
    axis_pt = PLATE_W_IN * 72.0 / 2.0 - 78.0            # media lámina menos rótulos, marcas y márgenes
    share = min(0.62, w_pt / axis_pt)
    pad = 5.0 / axis_pt                                # remate del bigote (3 pt) más un blanco de 2 pt
    top = float(rows.pct_hi.max())
    xmax = max(top * 1.30, max(float(r.pct_hi) for _, r in rows.iterrows()) / max(0.2, 1.0 - share - pad))
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.75, float(len(rows)) - 0.25)
    placed = []
    for i, r in rows.iterrows():
        reliable = bool(r.reliable)
        colr = OKABE[0] if reliable else GREY
        ax.errorbar(r.pct, y[i], xerr=[[max(r.pct - r.pct_lo, 0)], [max(r.pct_hi - r.pct, 0)]], fmt="o",
                    color=colr, markersize=6, capsize=3, lw=1.6, alpha=1.0 if reliable else 0.55)
        t_ = ax.text(float(r.pct_hi) + pad * xmax, y[i], labels[i], fontsize=6.2, va="center", ha="left",
                     linespacing=1.15, color="#333333" if reliable else GREY, gid=C.PLATE_KEEP)
        placed.append((t_, float(r.pct_hi)))
    # El ancho del panel se estima aquí con la mitad de la lámina menos un margen fijo, pero el reparto
    # definitivo no es exactamente ese: con la estimación corta, el rótulo más ancho de la fila
    # «Hombres» llegaba a la ÚLTIMA columna de píxeles del lienzo y, impreso, el último dígito quedaba
    # sobre el corte. `_fit_forest_labels` los vuelve a medir con la composición ya congelada y ensancha
    # el eje hasta que el rótulo más ancho cabe dentro del panel.
    ax._forest_labels = placed
    ax._forest_pad = pad
    ax.set_yticks(y); ax.set_yticklabels([_sub_label(r, lang) for _, r in rows.iterrows()], fontsize=7.5)
    ax.set_xlabel(tr("e23_prop_axis", lang)); fmt_axis(ax, lang, "x", 1)
    if note:
        _note(ax, letter, note, colour=note_colour)
    _title(ax, title)


def fig_e23(P, lang, fdir):
    plt, fig, A = _new_plate()
    prim = P["primary"]
    panels = [
        (A[0], 0, tr("e23_a", lang), ("ENDIDE 2022", "ENDIDE adultos 18+: autismo reportado")),
        (A[1], 1, tr("e23_b", lang), ("ENDIDE 2022", "ENDIDE NNA 2-17: autismo reportado")),
        (A[2], 2, tr("e23_c", lang), ("ENCAVI 2023-2024", "ENCAVI 15+: diagnóstico de trastorno del espectro autista")),
    ]
    notes = {
        1: ({"es": "Serie adicional: confirmación profesional del reporte (tabla acompañante).",
             "en": "Additional series: professional confirmation of the report (companion table)."}[lang], "#555555"),
        2: (tr("e23_no_region", lang), C.RED),
    }
    for a, letter_, title, (survey, domain) in panels:
        rows = prim[(prim.survey == survey) & (prim.domain == domain)].copy()
        order = {"total": 0, "sex": 1, "age_group": 2}
        rows = rows.assign(_o=rows.subgroup_type.map(order)).sort_values(["_o"]).drop(columns="_o")
        note, colour = notes.get(letter_, (None, "#555555"))
        _survey_forest(a, rows, lang, title, letter=PANEL_LETTERS[letter_], note=note, note_colour=colour)
        _letter(a, letter_)

    # Los paneles d–f resumen el DOMINIO (la fila «total»): los subgrupos por sexo y por grupo etario ya
    # aparecen en los forest a–c y completos en la tabla acompañante. Con los subgrupos, el rótulo del eje
    # ocupaba más de la mitad del panel de media página y la lámina dejaba de ser legible.
    allrows = P["all"].copy()
    allrows = allrows[allrows.subgroup_type == "total"].copy()
    allrows["short"] = [_abbrev(DOMAIN_TINY.get(r.domain, DOMAIN_SHORT.get(
        r.domain, {"es": r.domain, "en": r.domain}))[lang], 26) for _, r in allrows.iterrows()]
    d = A[3]
    dd = allrows.sort_values("deff")
    yd = np.arange(len(dd))
    d.barh(yd, dd.deff, height=0.7, color=[OKABE[0] if bool(v) else GREY for v in dd.reliable])
    d.axvline(1.0, color="#333333", ls="--", lw=0.9)
    d.set_yticks(yd); d.set_yticklabels(list(dd.short), fontsize=6.4)
    d.set_xlabel(tr("e23_deff_axis", lang)); fmt_axis(d, lang, "x", 1)
    _title(d, tr("e23_d", lang)); _letter(d, 3)

    e = A[4]
    de = allrows.sort_values("rse_pct")
    ye = np.arange(len(de))
    e.barh(ye, de.rse_pct, height=0.7, color=[OKABE[0] if bool(v) else GREY for v in de.reliable])
    e.axvline(30, color=C.RED, ls="--", lw=1.2)
    # El rótulo del umbral se escribía a la altura del eje X, justo sobre la marca «30»: las dos cifras se
    # leían pegadas («3030 % threshold»). Va dentro del panel, en la parte alta de la línea de umbral.
    e.text(30, 0.99, " " + tr("e23_rse_line", lang), transform=e.get_xaxis_transform(), fontsize=FS_LEGEND,
           color=C.RED, va="top", ha="left")
    e.set_yticks(ye); e.set_yticklabels(list(de.short), fontsize=6.4)
    e.set_xlabel(tr("e23_rse_axis", lang)); fmt_axis(e, lang, "x", 0)
    _title(e, tr("e23_e", lang)); _letter(e, 4)

    f = A[5]
    df = allrows.sort_values("cases")
    yf = np.arange(len(df))
    f.barh(yf, df.cases, height=0.7, color=[OKABE[0] if bool(v) else GREY for v in df.reliable])
    f.axvline(30, color=C.RED, ls="--", lw=1.2)
    f.text(30, 0.99, " " + tr("e23_n30", lang), transform=f.get_xaxis_transform(), fontsize=FS_LEGEND,
           color=C.RED, va="top", ha="left")
    for i, r in enumerate(df.itertuples()):
        f.text(float(r.cases) * 1.10, yf[i], f"n={num(r.n, 0, lang)}", fontsize=6.2, va="center", color="#555555")
    f.set_xscale("log"); log_axis_fmt(f, lang, "x")
    f.set_xlim(0.8, float(df.cases.max()) * 9)
    f.set_yticks(yf); f.set_yticklabels(list(df.short), fontsize=6.4)
    f.set_ylim(-0.8, float(np.max(yf)) + 2.4)   # banda libre para la leyenda de fiabilidad
    f.set_xlabel(tr("e23_n_axis", lang))
    from matplotlib.patches import Patch
    if not bool(df.reliable.all()):
        f.legend(handles=[Patch(facecolor=OKABE[0], label=tr("e23_adequate", lang)),
                          Patch(facecolor=GREY, label=_wrap(tr("e23_imprecise", lang), 26))],
                 loc="upper left", fontsize=6.2, framealpha=0.95)
    _title(f, tr("e23_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E23']}.png", plt)
    return path


PIE_SERIES_LABEL = {
    "pie_tea_strict": {"es": "PIE TEA estricto (Apuntes 60)", "en": "PIE strict autism (Apuntes 60)"},
    "pie_tea_asperger": {"es": "PIE TEA-Asperger (Apuntes 60)", "en": "PIE autism-Asperger (Apuntes 60)"},
    "pie_harmonised_apuntes60": {"es": "PIE armonizado (Apuntes 60, 2019–2023)", "en": "Harmonised PIE (Apuntes 60, 2019–2023)"},
    "pie_harmonised_sinaces": {"es": "PIE armonizado (SINACES, 2022–2025)", "en": "Harmonised PIE (SINACES, 2022–2025)"},
    "special_schools_autism": {"es": "Escuelas especiales (TEA)", "en": "Special schools (autism)"},
    "sinaces_total_autistic_students": {"es": "Total SINACES de estudiantes autistas", "en": "SINACES total autistic students"},
}


def fig_e24(P, lang, fdir):
    plt, fig, A = _new_plate()
    p, disc, sx = P["pie"], P["discrepancy"], P["sex2023"]

    a = A[0]
    styles = [("pie_tea_strict", OKABE[0], "o", "-"), ("pie_tea_asperger", OKABE[1], "s", "-"),
              ("pie_harmonised_apuntes60", OKABE[2], "^", "-"), ("pie_harmonised_sinaces", OKABE[3], "D", "--")]
    for key, colr, mk, ls in styles:
        if key not in p.columns:
            continue
        ser = p[key].dropna()
        if not len(ser):
            continue
        a.plot(ser.index, ser.values / 1e3, mk + ls, color=colr, lw=2, markersize=6, label=PIE_SERIES_LABEL[key][lang])
        a.annotate(num(ser.values[-1], 0, lang), (ser.index[-1], ser.values[-1] / 1e3), xytext=(5, 2),
                   textcoords="offset points", fontsize=7, color=colr, fontweight="bold")
    a.set_xticks(list(p.index)); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("e24_students_thousands", lang))
    fmt_axis(a, lang, "y", 0)
    a.set_ylim(0, float(np.nanmax(p[[k for k, _, _, _ in styles if k in p.columns]].values)) / 1e3 * 1.35)
    _note(a, "a", tr("e24_note_harm", lang))
    context_markers(a, lang, xmin=min(p.index), xmax=max(p.index))
    a.legend(loc="upper left", fontsize=7); _title(a, tr("e24_a", lang)); _letter(a, 0)

    b = A[1]
    if disc:
        keys = [("total", {"es": "Total SINACES 2022", "en": "SINACES total 2022"}, OKABE[4]),
                ("special", {"es": "Escuelas especiales", "en": "Special schools"}, OKABE[1]),
                ("derived", {"es": "Total − escuelas especiales", "en": "Total − special schools"}, OKABE[0]),
                ("published", {"es": "PIE armonizado publicado (SINACES)", "en": "Published harmonised PIE (SINACES)"}, OKABE[3]),
                ("apuntes", {"es": "PIE armonizado (Apuntes 60)", "en": "Harmonised PIE (Apuntes 60)"}, OKABE[2])]
        vals = [disc.get(k, np.nan) for k, _, _ in keys]
        xb = np.arange(len(keys))
        b.bar(xb, [v / 1e3 if pd.notna(v) else 0 for v in vals], width=0.62,
              color=[c for _, _, c in keys])
        for i, v in enumerate(vals):
            b.text(xb[i], (v / 1e3 if pd.notna(v) else 0) + 0.6, num(v, 0, lang), ha="center", fontsize=7.5,
                   color="#333333", fontweight="bold")
        b.set_xticks(xb); b.set_xticklabels([_wrap(l[lang], 11) for _, l, _ in keys], fontsize=6.2)
        b.set_ylabel(tr("e24_students_thousands", lang)); fmt_axis(b, lang, "y", 0)
        b.set_ylim(0, float(np.nanmax(vals)) / 1e3 * 1.28)
        gap = disc.get("gap", np.nan)
        _note(b, "b", {"es": f"Discrepancia documentada: {num(gap, 0, lang)} casos entre el total publicado y "
                             "la resta.",
                       "en": f"Documented discrepancy: {num(gap, 0, lang)} cases between the published total and "
                             "the subtraction."}[lang], colour=C.RED)
    _title(b, tr("e24_b", lang)); _letter(b, 1)

    c = A[2]
    for key, colr, mk, lbl in (("pie_harmonised_share_of_pie_pct", OKABE[0], "o",
                                {"es": "PIE armonizado / matrícula PIE", "en": "Harmonised PIE / PIE enrolment"}),
                               ("pie_tea_strict_share_of_pie_pct", OKABE[1], "s",
                                {"es": "TEA estricto / matrícula PIE", "en": "Strict autism / PIE enrolment"}),
                               ("pie_tea_share_of_applicants_pct", OKABE[2], "^",
                                {"es": "PIE armonizado / postulantes SINACES", "en": "Harmonised PIE / SINACES applicants"})):
        if key in p.columns and p[key].notna().any():
            ser = p[key].dropna()
            c.plot(ser.index, ser.values, mk + "-", color=colr, lw=2, markersize=6, label=lbl[lang])
            c.annotate(pct(ser.values[-1], lang), (ser.index[-1], ser.values[-1]), xytext=(5, 2),
                       textcoords="offset points", fontsize=7, color=colr, fontweight="bold")
    c.set_xticks(list(p.index)); c.set_xlabel(tr("year", lang)); c.set_ylabel(tr("e24_share_axis", lang))
    fmt_axis(c, lang, "y", 0); c.set_ylim(0, None)
    context_markers(c, lang, xmin=min(p.index), xmax=max(p.index))
    c.legend(loc="upper left", fontsize=7)
    _title(c, tr("e24_c", lang)); _letter(c, 2)

    d = A[3]
    ss = p["special_schools_autism"].dropna() if "special_schools_autism" in p.columns else pd.Series(dtype=float)
    st = p["sinaces_total_autistic_students"].dropna() if "sinaces_total_autistic_students" in p.columns else pd.Series(dtype=float)
    if len(st):
        d.bar(st.index, st.values / 1e3, width=0.6, color="#9ecae1", label=PIE_SERIES_LABEL["sinaces_total_autistic_students"][lang])
    if len(ss):
        d.bar(ss.index, ss.values / 1e3, width=0.6, color=OKABE[1], label=PIE_SERIES_LABEL["special_schools_autism"][lang])
        for y in ss.index:
            d.text(y, ss.at[y] / 1e3 + 1.5, num(ss.at[y], 0, lang), ha="center", fontsize=7, color=OKABE[1])
    d.set_xticks(sorted(set(list(ss.index) + list(st.index)))); d.set_xlabel(tr("year", lang))
    d.set_ylabel(tr("e24_students_thousands", lang)); fmt_axis(d, lang, "y", 0)
    d.legend(loc="upper left", fontsize=7.5); _title(d, tr("e24_d", lang)); _letter(d, 3)

    e = A[4]
    keys = [("strict", {"es": "TEA estricto", "en": "Strict autism"}), ("asperger", {"es": "TEA-Asperger", "en": "Autism-Asperger"}),
            ("pie_total", {"es": "Matrícula PIE total", "en": "Total PIE enrolment"})]
    xe = np.arange(len(keys))
    male = [sx[k]["male"] for k, _ in keys]
    fem = [sx[k]["female"] for k, _ in keys]
    e.bar(xe - 0.2, [v / 1e3 if pd.notna(v) else 0 for v in male], width=0.38, color=OKABE[0], label=tr("males", lang))
    e.bar(xe + 0.2, [v / 1e3 if pd.notna(v) else 0 for v in fem], width=0.38, color=OKABE[1], label=tr("females", lang))
    e.set_yscale("log"); log_axis_fmt(e, lang)
    top = float(np.nanmax([v for v in male + fem if pd.notna(v)])) / 1e3
    e.set_ylim(max(0.5, float(np.nanmin([v for v in male + fem if pd.notna(v)])) / 1e3 * 0.35), top * 8)
    # La razón hombre:mujer va BAJO su categoría, en el rótulo del eje: escrita sobre las barras, tres
    # rótulos de dos renglones medían más que el paso entre categorías, el motor los apartaba media
    # categoría y el lector ya no sabía a qué par de barras pertenecía cada razón. El rótulo de eje no se
    # aparta nunca y señala su categoría sin ambigüedad; qué es la cifra lo dice la nota del pie.
    e.set_xticks(xe)
    e.set_xticklabels([_wrap(l[lang], 12) + "\n" + val_ci(sx[k]["ratio"], sx[k]["lo"], sx[k]["hi"], 2, lang)
                       for k, l in keys], fontsize=6.4)
    _note(e, "e", {"es": "la cifra bajo cada categoría es la razón hombre:mujer con su IC 95 %.",
                   "en": "the figure under each category is the male-to-female ratio with its 95% CI."}[lang])
    e.set_ylabel(tr("e24_students_thousands", lang))
    e.legend(loc="upper left", fontsize=7.5)
    _title(e, tr("e24_e", lang)); _letter(e, 4)

    f = A[5]
    reg = p["pie_tea_regular_entry"].dropna() if "pie_tea_regular_entry" in p.columns else pd.Series(dtype=float)
    exc = p["pie_tea_exceptional_entry"].dropna() if "pie_tea_exceptional_entry" in p.columns else pd.Series(dtype=float)
    if len(reg):
        f.bar(reg.index - 0.19, reg.values / 1e3, width=0.36, color=OKABE[0],
              label={"es": "Ingreso regular", "en": "Regular entry"}[lang])
    if len(exc):
        f.bar(exc.index + 0.19, exc.values / 1e3, width=0.36, color=OKABE[1],
              label={"es": "Ingreso excepcional", "en": "Exceptional entry"}[lang])
        for y in exc.index:
            share = 100 * exc.at[y] / (reg.at[y] + exc.at[y]) if y in reg.index else np.nan
            f.text(y + 0.19, exc.at[y] / 1e3 + 1.2, pct(share, lang, 0), ha="center", fontsize=6.8, color="#333333")
    f.set_xticks(sorted(set(list(reg.index) + list(exc.index)))); f.set_xlabel(tr("year", lang))
    f.set_ylabel(tr("e24_students_thousands", lang)); fmt_axis(f, lang, "y", 0)
    f.legend(loc="upper left", fontsize=7.5); _title(f, tr("e24_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E24']}.png", plt)
    return path


LEVEL_LABEL = {"parvularia": {"es": "Parvularia", "en": "Pre-school"}, "basico1": {"es": "1º básico", "en": "Grade 1"},
               "basico5": {"es": "5º básico", "en": "Grade 5"}, "medio1": {"es": "1º medio", "en": "Grade 9"}}
LEVEL_COLOR = {"parvularia": OKABE[0], "basico1": OKABE[1], "basico5": OKABE[2], "medio1": OKABE[3]}
#: Códigos cortos de nivel para las cabeceras de la rejilla del panel f: una columna de 8 mm no admite
#: «Pre-school» ni «1º básico» a 6,4 pt y las cabeceras se imprimían pegadas («YearPre-schGradeGradeGrade»).
#: La clave bajo la tabla los desarrolla.
LEVEL_SHORT = {"parvularia": {"es": "Parv.", "en": "Pre"}, "basico1": {"es": "1ºB", "en": "G1"},
               "basico5": {"es": "5ºB", "en": "G5"}, "medio1": {"es": "1ºM", "en": "G9"}}


def fig_e25(P, lang, fdir):
    plt, fig, A = _new_plate()
    j, ratios, avail = P["junaeb"], P["ratios"], P["availability"]
    years = sorted(j.year.unique())
    ja = j[j.sex == "all"]

    a = A[0]
    a_labels = []
    for lvl in JUNAEB_LEVELS:
        sub = ja[ja.level == lvl].set_index("year").reindex(years)
        ok = sub[sub.proportion_weighted_pct.notna()]
        if len(ok):
            a.errorbar(np.asarray(ok.index, dtype=float), ok.proportion_weighted_pct.to_numpy(dtype=float),
                       yerr=[(ok.proportion_weighted_pct - ok.lo_pct).to_numpy(dtype=float),
                             (ok.hi_pct - ok.proportion_weighted_pct).to_numpy(dtype=float)],
                       fmt="o-", color=LEVEL_COLOR[lvl], lw=2, markersize=6, capsize=3, label=LEVEL_LABEL[lvl][lang])
            # Solo se rotula el ÚLTIMO año de cada nivel: doce cifras sobre cuatro series que se cruzan no
            # caben en medio folio —el buscador de hueco las dejaba sobre el marcador del nivel vecino— y
            # la serie completa está en la tabla acompañante, que es donde se leen los valores exactos.
            y_end = ok.index[-1]
            a_labels.append((y_end, float(ok.at[y_end, "proportion_weighted_pct"]),
                             float(ok.at[y_end, "lo_pct"]), float(ok.at[y_end, "hi_pct"]), LEVEL_COLOR[lvl]))
    ne_rows = ja[ja.estimable != "yes"]
    for _, r in ne_rows.iterrows():
        reason = tr("e25_no_item", lang) if r.item_variable == "ABSENT" and pd.isna(r.n_tea_unweighted) else (
            tr("e25_unw_only", lang) if r.estimable == "unweighted_only" else tr("e25_empty_var", lang))
        a.plot([r.year], [0.25], marker="x", color=GREY, markersize=6)
    _note(a, "a", {"es": "se rotula el último año de cada nivel; la serie completa, en la tabla acompañante. "
                         "× = no estimable como porcentaje ponderado (sin ítem TEA 2019–2022; sin ponderador "
                         "publicado en 2023; 1º medio 2024 con la variable completamente vacía: «no estimable», "
                         "nunca cero).",
                   "en": "the last year of each level is labelled; the full series is in the companion table. "
                         "× = not estimable as a weighted percentage (no autism item 2019–2022; no published "
                         "weight in 2023; grade 9 in 2024 has a completely empty variable: 'not estimable', "
                         "never zero)."}[lang])
    a.set_xticks(years); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("e25_pct_axis", lang))
    a.set_ylim(0, 13); fmt_axis(a, lang, "y", 0)
    context_markers(a, lang, xmin=min(years), xmax=max(years))
    # Los rótulos se colocan al final, con LOS LÍMITES DEFINITIVOS del panel y las cuatro series ya
    # dibujadas: colocados nivel a nivel, o antes de fijar el eje, el buscador de hueco medía sobre una
    # geometría que después cambiaba y el valor acababa sobre el marcador del nivel vecino (S40 (a):
    # «5,03», «6,60», «7,69»). Y con sitio A LA DERECHA del último punto, que pegado al borde no lo había.
    a.set_xlim(min(years) - 0.45, max(years) + 1.15)
    for y, v, lo, hi, colr in a_labels:
        C.plate_value_label(a, y, v, num(v, 2, lang), err=(lo, hi), fontsize=6.4, color=colr,
                            prefer=((1, 0), (1, 1), (1, -1), (0, 1), (0, -1)))
    a.legend(loc="upper left", fontsize=7.5); _title(a, tr("e25_a", lang)); _letter(a, 0)

    b = A[1]
    sexes = [("male", tr("males", lang), OKABE[0]), ("female", tr("females", lang), OKABE[1])]
    js = j[j.sex.isin(["male", "female"])].copy()
    js["value"] = js.proportion_weighted_pct.fillna(js.proportion_unweighted_pct)
    keys = [(y, l) for y in years for l in JUNAEB_LEVELS if len(js[(js.year == y) & (js.level == l)])]
    xb = np.arange(len(keys))
    for off, (sk, slab, colr) in zip((-0.2, 0.2), sexes):
        vals, los, his = [], [], []
        for y, l in keys:
            r = js[(js.year == y) & (js.level == l) & (js.sex == sk)]
            v = float(r.value.iloc[0]) if len(r) and pd.notna(r.value.iloc[0]) else np.nan
            vals.append(v)
            lo = float(r.lo_pct.iloc[0]) if len(r) and pd.notna(r.lo_pct.iloc[0]) else v
            hi = float(r.hi_pct.iloc[0]) if len(r) and pd.notna(r.hi_pct.iloc[0]) else v
            los.append(max(v - lo, 0) if pd.notna(v) else 0); his.append(max(hi - v, 0) if pd.notna(v) else 0)
        b.bar(xb + off, [0 if pd.isna(v) else v for v in vals], width=0.38, color=colr, label=slab)
        b.errorbar(xb + off, vals, yerr=[los, his], fmt="none", ecolor="#333333", elinewidth=0.8, capsize=2)
    unw = {(y, l) for y, l in keys
           if not js[(js.year == y) & (js.level == l)].proportion_weighted_pct.notna().any()}
    b.set_xticks(xb)
    b.set_xticklabels([f"{LEVEL_LABEL[l][lang]} {y}" + (" *" if (y, l) in unw else "") for y, l in keys],
                      fontsize=6.2, rotation=45, ha="right")
    _note(b, "b", {"es": "* porcentaje no ponderado (2023 no tiene ponderador publicado); 1º medio 2024 no es "
                         "estimable.",
                   "en": "* unweighted percentage (2023 has no published weight); grade 9 in 2024 is not "
                         "estimable."}[lang])
    b.set_ylabel(tr("e25_pct_axis", lang)); fmt_axis(b, lang, "y", 0)
    b.set_ylim(0, float(np.nanmax(js.value)) * 1.25)
    b.legend(loc="upper right", fontsize=7.5); _title(b, tr("e25_b", lang)); _letter(b, 1)

    c = A[2]
    xc = np.arange(len(years))
    for i, lvl in enumerate(JUNAEB_LEVELS):
        sub = ja[ja.level == lvl].set_index("year").reindex(years)
        c.bar(xc + (i - 1.5) * 0.2, sub.n_students / 1e3, width=0.19, color=LEVEL_COLOR[lvl], label=LEVEL_LABEL[lvl][lang])
    c.set_xticks(xc); c.set_xticklabels([str(y) for y in years]); c.set_xlabel(tr("year", lang))
    c.set_ylabel(tr("e25_students_axis", lang)); fmt_axis(c, lang, "y", 0)
    c2 = c.twinx(); c2.grid(False); c2.spines["right"].set_visible(True)
    for i, lvl in enumerate(JUNAEB_LEVELS):
        sub = ja[ja.level == lvl].set_index("year").reindex(years)
        c2.plot(xc, sub.n_tea_unweighted / 1e3, "o:", color=LEVEL_COLOR[lvl], lw=1.4, markersize=4)
    fmt_axis(c2, lang, "y", 1)
    _right_ylabel(c2, {"es": "Casos TEA no ponderados (miles)",
                       "en": "Unweighted autism cases (thousands)"}[lang], base=c)
    c.set_ylim(0, float(ja.n_students.max()) / 1e3 * 1.40)
    c.legend(loc="upper right", fontsize=6.2, ncol=1, framealpha=0.95)
    _note(c, "c", {"es": "casos TEA no ponderados: solo 2023–2025, y sin 1º medio en 2024.",
                   "en": "unweighted autism cases: 2023–2025 only, and no grade 9 in 2024."}[lang])
    _title(c, tr("e25_c", lang)); _letter(c, 2)

    d = A[3]
    dd = ja[ja.proportion_weighted_pct.notna()]
    if len(dd):
        d.scatter(dd.proportion_unweighted_pct, dd.proportion_weighted_pct,
                  c=[LEVEL_COLOR[l] for l in dd.level], s=60, edgecolor="white", linewidth=0.6, zorder=3)
        lim = float(max(dd.proportion_unweighted_pct.max(), dd.proportion_weighted_pct.max())) * 1.18
        d.plot([0, lim], [0, lim], "--", color=GREY, lw=1.0)
        C.plate_annotate_no_overlap(
            d, dd.proportion_unweighted_pct.to_numpy(dtype=float), dd.proportion_weighted_pct.to_numpy(dtype=float),
            [f"{LEVEL_SHORT[r.level][lang]} {int(r.year)}" for _, r in dd.iterrows()], fontsize=6.2)
        d.set_xlim(0, lim * 1.30); d.set_ylim(0, lim)
    d.set_xlabel({"es": "Porcentaje no ponderado (%)", "en": "Unweighted percentage (%)"}[lang])
    d.set_ylabel(tr("e25_pct_axis", lang)); fmt_axis(d, lang, "y", 0); fmt_axis(d, lang, "x", 0)
    _note(d, "d", tr("e25_note_junaeb", lang))
    _title(d, tr("e25_d", lang)); _letter(d, 3)

    e = A[4]
    rr = ratios[ratios.ratio.notna()].sort_values(["level", "year"])
    if len(rr):
        xe = np.arange(len(rr))
        e.errorbar(xe, rr.ratio, yerr=[(rr.ratio - rr.lo).clip(lower=0), (rr.hi - rr.ratio).clip(lower=0)],
                   fmt="o", color=OKABE[0], markersize=6, capsize=3, lw=1.6)
        for i, r in enumerate(rr.itertuples()):
            e.scatter([xe[i]], [r.ratio], color=LEVEL_COLOR[r.level], s=55, zorder=4, edgecolor="white", linewidth=0.6)
        e.axhline(3, color=C.RED, ls="--", lw=1.0); e.axhline(4, color=C.RED, ls=":", lw=1.0)
        e.text(len(rr) - 0.5, 3, " 3:1", fontsize=7, color=C.RED, va="bottom", ha="right")
        e.text(len(rr) - 0.5, 4, " 4:1", fontsize=7, color=C.RED, va="bottom", ha="right")
        e.set_xticks(xe)
        e.set_xticklabels([f"{LEVEL_LABEL[r.level][lang]} {r.year}"
                           + ("" if r.basis == "weighted" else " *")
                           for r in rr.itertuples()], fontsize=6.4, rotation=45, ha="right")
        _note(e, "e", {"es": "* razón de porcentajes no ponderados (2023 no tiene ponderador publicado).",
                       "en": "* ratio of unweighted percentages (2023 has no published weight)."}[lang])
        e.set_ylim(0, max(4.6, float(rr.hi.max()) * 1.12))
    e.set_ylabel(tr("ratio_mf", lang)); fmt_axis(e, lang, "y", 1)
    _title(e, tr("e25_e", lang)); _letter(e, 4)

    f = A[5]
    f.axis("off")
    # Rejilla compacta: en un panel de media página el texto completo del estado («solo no ponderado»)
    # no cabe en una celda de 12 mm. Se imprime un símbolo por celda y la clave va bajo la tabla.
    status = {"yes": "✓", "unweighted_only": "~", "no": "×"}
    niveles = " · ".join(f"{LEVEL_SHORT[l][lang]} = {LEVEL_LABEL[l][lang]}" for l in JUNAEB_LEVELS)
    key = {"es": f"✓ = % ponderado · ~ = solo no ponderado · × = no estimable. Niveles: {niveles}.",
           "en": f"✓ = weighted % · ~ = unweighted only · × = not estimable. Levels: {niveles}."}[lang]
    fill = {"yes": "#d9ead3", "unweighted_only": "#fce5cd", "no": "#f4cccc"}
    hdr = [tr("year", lang)] + [LEVEL_SHORT[l][lang] for l in JUNAEB_LEVELS] + \
          [{"es": "Ítem TEA", "en": "Autism item"}[lang], {"es": "Ponder.", "en": "Weight"}[lang]]
    rows, colours = [], []
    for y in years:
        sub = avail[avail.year == y].set_index("level")
        cells = [str(int(y))]
        cols = ["white"]
        for l in JUNAEB_LEVELS:
            st = sub.at[l, "estimable"] if l in sub.index else "no"
            cells.append(status.get(st, "×"))
            cols.append(fill.get(st, "white"))
        item = sub.item_variable.iloc[0] if len(sub) else "ABSENT"
        wv = sorted({str(v) for v in sub.weight_variable}) if len(sub) else ["ABSENT"]
        cells.append({"es": "ausente", "en": "absent"}[lang] if item == "ABSENT" else str(item))
        cells.append(", ".join(w if w != "ABSENT" else {"es": "ausente", "en": "absent"}[lang] for w in wv))
        cols += ["white", "white"]
        rows.append(cells); colours.append(cols)
    tbl = f.table(cellText=rows, colLabels=hdr, cellColours=colours, cellLoc="center",
                  colWidths=[0.11, 0.095, 0.095, 0.095, 0.095, 0.26, 0.25],
                  bbox=[0.0, 0.40, 1.0, 0.56])
    tbl.auto_set_font_size(False); tbl.set_fontsize(6.4)
    for (row, _col), cell in tbl.get_celld().items():
        cell.set_linewidth(0.4)
        if row == 0:
            cell.set_text_props(fontweight="bold"); cell.set_facecolor("#e8e8e8")
    _title(f, tr("e25_f", lang)); _letter(f, 5)
    # La clave de los símbolos va DEBAJO de la rejilla y ahí se queda: el motor de descongestión no ve la
    # tinta de una tabla —no son barras ni líneas— y creía vacío el hueco donde está, de modo que subía la
    # clave al «hueco más vacío» y borraba la cabecera y la fila de 2019 (S40 (f)). Marcada, no se mueve.
    f.text(0.0, 0.34, _wrap(key, 62), transform=f.transAxes, fontsize=6.2, color="#333333", va="top",
           linespacing=1.3, gid=C.PLATE_KEEP)
    _note(f, "f", {"es": "el ítem TEA aparece en 2023; el ponderador publicado cambia de EXP_REG (2024) a "
                         "EXP (2025). En 2024 la variable TEA de 1º medio está completamente vacía: «no "
                         "estimable», nunca cero.",
                   "en": "the autism item appears in 2023; the published weight changes from EXP_REG (2024) "
                         "to EXP (2025). In 2024 the grade-9 autism variable is completely empty: 'not "
                         "estimable', never zero."}[lang])

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E25']}.png", plt)
    return path


#: Nombre corto de cada sistema para las leyendas de la lámina E26 (el nombre completo va en el título de
#: la tabla acompañante y en el pie de figura).
SYS_SHORT = {"grd": {"es": "GRD", "en": "GRD"}, "deis": {"es": "DEIS", "en": "DEIS"},
             "a05": {"es": "REM A05", "en": "REM A05"}, "p2": {"es": "REM P2", "en": "REM P2"},
             "pie": {"es": "PIE", "en": "PIE"}}
#: Qué es el denominador de cada fuente en el panel (f): sin decirlo, «por unidad reportante» no se puede leer.
SYS_DENOM = {
    "grd": {"es": "hospitales GRD reportantes", "en": "reporting GRD hospitals"},
    "deis": {"es": "egresos DEIS totales", "en": "total DEIS discharges"},
    "a05": {"es": "establecimientos REM reportantes", "en": "reporting REM establishments"},
    "p2": {"es": "establecimientos REM reportantes", "en": "reporting REM establishments"},
    "pie": {"es": "postulantes al PIE", "en": "PIE applicants"},
}


def fig_e26(P, lang, fdir):
    """Comparación entre fuentes en seis paneles: cada normalización junto al denominador que la sostiene.

    La versión anterior era de tres paneles a lo ancho de la lámina —tres filas por UNA columna—, que no es
    la norma de la serie (tres filas por dos columnas). Los tres paneles nuevos no inventan nada: son los
    denominadores que ya usaban los tres primeros (el valor bruto antes de normalizar, la población INE que
    divide el panel (c) y las unidades reportantes que dividen el panel (e)), y sin ellos «por unidad
    reportante» no se puede leer."""
    plt, fig, A = _new_plate()
    tbl, conv = P["table"], P["convergence"]
    ine = P["ine"]

    a = A[0]
    base_year = int(conv.index_base_year.iloc[0]) if len(conv) else 2021
    conv_label = {"grd_any_rate": "grd", "deis_principal_rate": "deis", "a05_strict_entries": "a05",
                  "p2_december_stock": "p2", "pie_harmonised": "pie"}
    for series, sysk in conv_label.items():
        sub = conv[conv.series == series].sort_values("year")
        if not len(sub):
            continue
        # El valor de final de serie va EN LA LEYENDA, con su año. Escrito junto al último punto, cinco
        # rótulos se disputaban media década del eje logarítmico y el motor apartaba el de DEIS hasta
        # dejarlo huérfano de su propia línea (S41 (a)); en la leyenda dice lo mismo y no tapa nada.
        a.plot(sub.year, sub["index"], "o-", color=SYS_COLOR[sysk], lw=2, markersize=5,
               label=f"{SYS_LABEL[sysk][lang]} — {num(float(sub['index'].iloc[-1]), 0, lang)} "
                     f"({int(sub.year.iloc[-1])})")
    a.axhline(100, color="#333333", ls="--", lw=1.0)
    a.set_yscale("log"); log_axis_fmt(a, lang)
    a.set_xticks(YEARS_REM); a.set_xlabel(tr("year", lang))
    a.set_ylabel(f"{tr('e26_index_axis', lang)} — {base_year} = 100")
    a.margins(x=0.10); a.set_ylim(30, 6000)
    context_markers(a, lang, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    a.legend(loc="upper left", fontsize=6.4); _title(a, tr("e26_a", lang)); _letter(a, 0)

    b = A[1]
    for sysk in SYS_LABEL:
        sub = tbl[tbl.system == sysk].sort_values("year")
        if not len(sub) or sub.value.isna().all():
            continue
        b.plot(sub.year, sub.value, "o-", color=SYS_COLOR[sysk], lw=2, markersize=5,
               label=f"{SYS_SHORT[sysk][lang]} ({SYS_UNIT[sysk][lang]})")
    b.set_yscale("log"); log_axis_fmt(b, lang)
    b.set_xticks(YEARS_REM); b.set_xlabel(tr("year", lang))
    b.set_ylabel({"es": "Valor anual (escala log)", "en": "Annual value (log scale)"}[lang])
    b.margins(x=0.10)
    context_markers(b, lang, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    b.legend(loc="upper left", fontsize=6.2)
    _title(b, {"es": "Valor anual bruto de cada fuente", "en": "Raw annual value of each source"}[lang])
    _letter(b, 1)

    c = A[2]
    for sysk in SYS_LABEL:
        sub = tbl[tbl.system == sysk].sort_values("year")
        if not len(sub) or sub.per_100k_residents.isna().all():
            continue
        c.plot(sub.year, sub.per_100k_residents, "o-", color=SYS_COLOR[sysk], lw=2, markersize=5,
               label=f"{SYS_SHORT[sysk][lang]} ({SYS_UNIT[sysk][lang]})")
    c.set_yscale("log"); log_axis_fmt(c, lang)
    c.set_xticks(YEARS_REM); c.set_xlabel(tr("year", lang)); c.set_ylabel(tr("e26_rate_axis", lang))
    c.margins(x=0.10); c.set_ylim(1.0, 3000)
    context_markers(c, lang, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    c.legend(loc="upper left", fontsize=6.2); _title(c, tr("e26_b", lang)); _letter(c, 2)

    d = A[3]
    yrs = [y for y in YEARS_REM if y in ine.index]
    d.bar(yrs, [float(ine[y]) / 1e6 for y in yrs], width=0.62, color="#9ecae1")
    for y in yrs:
        d.text(y, float(ine[y]) / 1e6, num(float(ine[y]) / 1e6, 2, lang), ha="center", va="bottom",
               fontsize=6.6, color="#333333")
    d.set_xticks(YEARS_REM); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("e20_pop_axis", lang))
    fmt_axis(d, lang, "y", 1)
    d.set_ylim(0, max(float(ine[y]) for y in yrs) / 1e6 * 1.12)
    context_markers(d, lang, law=False, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    _title(d, {"es": "Denominador del panel (c): población INE (base 2017, 30 jun)",
               "en": "Denominator of panel (c): INE population (2017 base, 30 Jun)"}[lang])
    _letter(d, 3)

    e = A[4]
    for sysk in SYS_LABEL:
        sub = tbl[tbl.system == sysk].sort_values("year")
        if not len(sub) or sub.per_reporting_unit.isna().all():
            continue
        e.plot(sub.year, sub.per_reporting_unit, "o-", color=SYS_COLOR[sysk], lw=2, markersize=5,
               label=f"{SYS_SHORT[sysk][lang]} — {SYS_REPORTING_UNIT[sysk][lang]}")
    e.set_yscale("log"); log_axis_fmt(e, lang)
    e.set_xticks(YEARS_REM); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("e26_unit_axis", lang))
    e.margins(x=0.10); e.set_ylim(2.0, 3000)
    context_markers(e, lang, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    _note(e, "e", {"es": "El número de establecimientos escolares no se publica en las fuentes usadas; el "
                         "denominador educativo son los postulantes al PIE.",
                   "en": "The number of schools is not published in the sources used; the education "
                         "denominator is PIE applicants."}[lang])
    e.legend(loc="upper left", fontsize=6.2); _title(e, tr("e26_c", lang)); _letter(e, 4)

    f = A[5]
    for sysk in SYS_LABEL:
        sub = tbl[tbl.system == sysk].sort_values("year")
        col = "reporting_units" if sysk in ("grd", "a05", "p2") else "denominator"
        if not len(sub) or sub[col].isna().all():
            continue
        f.plot(sub.year, sub[col], "o-", color=SYS_COLOR[sysk], lw=2, markersize=5,
               label=f"{SYS_SHORT[sysk][lang]} — {SYS_DENOM[sysk][lang]}")
    f.set_yscale("log"); log_axis_fmt(f, lang)
    f.set_xticks(YEARS_REM); f.set_xlabel(tr("year", lang))
    f.set_ylabel({"es": "Unidades o base (escala log)", "en": "Units or base (log scale)"}[lang])
    f.margins(x=0.10)
    context_markers(f, lang, law=False, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    f.legend(loc="upper left", fontsize=6.0)
    _title(f, {"es": "Denominador del panel (e): unidades reportantes por año",
               "en": "Denominator of panel (e): reporting units by year"}[lang])
    _letter(f, 5)

    _plate_note(fig, tr("e26_units_differ", lang), colour=C.RED)
    path = _save_plate(fig, fdir / f"{FIG_NAMES['E26']}.png", plt)
    return path


def fig_e26b(P, lang, fdir):
    plt, fig, A = _new_plate(note_lines=3)
    trend, by_age, by_var = P["trend"], P["by_age"], P["by_variant"]

    def refs(a, xmax=None):
        a.axhline(3, color=C.RED, ls="--", lw=1.0)
        a.axhline(4, color=C.RED, ls=":", lw=1.0)
        x = a.get_xlim()[1] if xmax is None else xmax
        # El rótulo de una línea de referencia SOLO significa algo pegado a su línea: se marca para que el
        # motor de descongestión no lo aparte (apartado, «4:1» acababa a la altura de 10 y mentía).
        for yv, key in ((3, "e26b_ref3"), (4, "e26b_ref4")):
            a.text(x, yv, " " + tr(key, lang), fontsize=6.4, color=C.RED, va="bottom", ha="right",
                   gid=C.PLATE_KEEP)

    a = A[0]
    trend_sources = [("grd_any", "-", 1.9), ("grd_principal", "-", 1.5), ("deis_principal", "-", 1.5),
                     ("a05_entries", "-", 1.9), ("p2_december", "-", 1.9), ("p6_primary", "-", 1.5),
                     ("p6_specialty", "-", 1.5), ("junaeb_parvularia", ":", 1.4), ("junaeb_basico1", ":", 1.4),
                     ("junaeb_basico5", ":", 1.4), ("junaeb_medio1", ":", 1.4)]
    for src, ls, lw in trend_sources:
        sub = trend[(trend.source == src) & trend.ratio.notna()].sort_values("year")
        if not len(sub):
            continue
        a.plot(sub.year, sub.ratio, "o" + ls, color=SRC_COLOR[src], lw=lw, markersize=3.4, label=SRC_SHORT[src][lang])
        if src in ("grd_any", "a05_entries", "p2_december"):
            a.fill_between(sub.year, sub.lo, sub.hi, color=SRC_COLOR[src], alpha=0.13, linewidth=0)
    for src, mk in (("pie_strict", "D"), ("endide_children", "*"), ("endide_adults", "P"), ("encavi", "X")):
        sub = trend[(trend.source == src) & trend.ratio.notna()]
        for _, r in sub.iterrows():
            a.errorbar([r.year], [r.ratio], yerr=[[max(r.ratio - r.lo, 0)], [max(r.hi - r.ratio, 0)]], fmt=mk,
                       color=SRC_COLOR[src], markersize=6, capsize=2, lw=1.1, label=SRC_SHORT[src][lang])
    a.set_yscale("log"); log_axis_fmt(a, lang)
    a.set_xticks(YEARS_REM); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("e26b_ratio_axis", lang))
    # Dieciséis series piden una leyenda de dieciséis entradas, y en una celda de 90 mm esa leyenda ocupaba
    # un cuarto del área de datos, con 2019–2021 debajo. La escala es logarítmica: subir el techo del eje
    # abre una banda vacía SOBRE los datos —no los comprime de forma apreciable— y la leyenda cabe entera
    # sin taparlos ni desplazar la marca de la pandemia contra el título.
    a.set_ylim(1.0, 90); refs(a, max(YEARS_REM) + 0.45)
    a.margins(x=0.06)
    # Los rótulos de contexto van a la banda de ABAJO: la de arriba la ocupa entera la leyenda de dieciséis
    # entradas, y ninguna razón de sexos baja de 1,5, de modo que bajo esa cota no hay dato que tapar.
    context_markers(a, lang, band="bottom", reserve=0.0, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    # Dieciséis entradas a dos columnas ocupan casi todo el ancho del panel: la única forma que cabe es
    # ancha y baja, y su sitio es la banda vacía que abre el techo del eje. Se fija aquí y se marca para que
    # el motor no vuelva a probar formas: a una columna es una tira de dieciséis filas que cruza el panel.
    lg_a = a.legend(loc="upper left", fontsize=6.0, ncol=2, borderpad=0.25, labelspacing=0.26,
                    handlelength=1.1, columnspacing=0.7, handletextpad=0.35, framealpha=0.9,
                    edgecolor="none", facecolor="white")
    lg_a.set_gid(C.PLATE_KEEP); lg_a.set_zorder(6); lg_a.set_in_layout(False)
    _title(a, tr("e26b_a", lang)); _letter(a, 0)

    b = A[1]
    b_supp, b_levels = [], []
    labels = AGE5
    xb = np.arange(len(labels))
    for src, off, mk in (("grd_any", -0.14, "o"), ("a05_entries", 0.14, "s")):
        sub = by_age[by_age.source == src].set_index("age_group").reindex(labels)
        yy = int(by_age[by_age.source == src].year.iloc[0]) if len(by_age[by_age.source == src]) else 0
        b.errorbar(xb + off, sub.ratio, yerr=[(sub.ratio - sub.lo).clip(lower=0), (sub.hi - sub.ratio).clip(lower=0)],
                   fmt=mk, color=SRC_COLOR[src], markersize=5, capsize=2, lw=1.3,
                   label=f"{SRC_SHORT[src][lang]} · {yy}")
        b_supp += [(xb[i] + off, len(b_levels), SRC_COLOR[src]) for i, ag in enumerate(labels)
                   if ag in sub.index and bool(sub.at[ag, "suppressed"])]
        b_levels.append(src)
    b.set_yscale("log"); log_axis_fmt(b, lang)
    b.set_xticks(xb); b.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    b.set_xlabel(tr("age_group", lang)); b.set_ylabel(tr("e26b_ratio_axis", lang)); b.set_ylim(0.35, 9.5)
    # La marca «<5» de la celda suprimida va en una banda reservada BAJO todos los intervalos: escrita a la
    # altura de 0,40 caía sobre la barra de error del otro sexo de esa misma banda de edad (S42 (b)).
    reserve_band(b, 0.19, side="bottom")
    lo_b, hi_b = b.get_ylim()
    for xs, level, colr in b_supp:
        # Una fila por fuente dentro de la banda: las dos fuentes suprimen la misma banda de edad y sus
        # marcas, a la misma altura, se imprimían una sobre otra. Cada una conserva el color y el
        # desplazamiento en x de su serie, de modo que se sabe a cuál pertenece.
        y_s = lo_b * (0.35 / lo_b) ** (0.22 + 0.42 * level)
        b.text(xs, y_s, "<5", fontsize=6.2, ha="center", va="center", color=colr, rotation=90,
               gid=C.PLATE_KEEP)
    refs(b, len(labels) - 0.6)
    _note(b, "b", {"es": "«<5» = celda suprimida (menos de 5 eventos en algún sexo).",
                   "en": "'<5' = suppressed cell (fewer than 5 events in either sex)."}[lang])
    b.legend(loc="upper right", fontsize=6.4); _title(b, tr("e26b_b", lang)); _letter(b, 1)

    c = A[2]
    c_years = []          # (x, y) de cada trayectoria, para ajustar los límites del panel al dato
    pairs = [("grd_any", "grd_any_asr", OKABE[0], "o"), ("a05_entries", "a05_asr", OKABE[1], "s")]
    for cnt_src, asr_src, colr, mk in pairs:
        cn = trend[trend.source == cnt_src].set_index("year")
        ar = trend[trend.source == asr_src].set_index("year")
        common = sorted(set(cn.index) & set(ar.index))
        if not common:
            continue
        c.errorbar([cn.at[y, "ratio"] for y in common], [ar.at[y, "ratio"] for y in common],
                   xerr=[[max(cn.at[y, "ratio"] - cn.at[y, "lo"], 0) for y in common],
                         [max(cn.at[y, "hi"] - cn.at[y, "ratio"], 0) for y in common]],
                   yerr=[[max(ar.at[y, "ratio"] - ar.at[y, "lo"], 0) for y in common],
                         [max(ar.at[y, "hi"] - ar.at[y, "ratio"], 0) for y in common]],
                   fmt=mk, color=colr, markersize=6, capsize=2, lw=1.2,
                   label=f"{SRC_LABEL[cnt_src][lang].split(' · ')[0]} ({common[0]}–{common[-1]})")
        # Trayectoria: una línea fina une los años consecutivos y una punta de flecha marca el año más
        # reciente. Catorce fechas escritas dentro de un panel cuadrado de 4 cm se disputaban el mismo
        # hueco —los intervalos de confianza cruzan el panel en las dos direcciones y no queda un rincón
        # libre— y siete quedaban impresas sobre su propio marcador (S42 (c)). El intervalo de años de
        # cada fuente ya está en su entrada de la leyenda y el valor de cada año, en la tabla acompañante.
        c.plot([cn.at[y, "ratio"] for y in common], [ar.at[y, "ratio"] for y in common], "-",
               color=colr, lw=0.9, alpha=0.55, zorder=1)
        c_years.append(([cn.at[y, "ratio"] for y in common], [ar.at[y, "ratio"] for y in common]))
        if len(common) >= 2:
            c.annotate("", xy=(cn.at[common[-1], "ratio"], ar.at[common[-1], "ratio"]),
                       xytext=(cn.at[common[-2], "ratio"], ar.at[common[-2], "ratio"]),
                       arrowprops=dict(arrowstyle="-|>", color=colr, lw=0.9, alpha=0.85,
                                       shrinkA=6, shrinkB=6), zorder=2)
    # Los límites se ajustan AL DATO (mismo intervalo en los dos ejes, que la diagonal exige): con el
    # cuadro fijo de 1,5 a 4,2 los puntos de la variante sin Rett se apelotonaban en un tercio del panel y
    # sus fechas no tenían dónde caer.
    c_vals = [v for xs, ys in c_years for v in list(xs) + list(ys)]
    c_span = [v for v in c_vals if np.isfinite(v)] or [1.5, 4.2]
    lo_l = min(1.6, min(c_span) * 0.88)
    hi_l = max(max(c_span) * 1.20, lo_l + 1.0)
    c.plot([lo_l, hi_l], [lo_l, hi_l], "--", color=GREY, lw=1.0)
    c.set_xlim(lo_l, hi_l); c.set_ylim(lo_l, hi_l)
    c.set_xlabel(tr("e26b_count_axis", lang)); c.set_ylabel(tr("e26b_asr_axis", lang))
    fmt_axis(c, lang, "y", 1); fmt_axis(c, lang, "x", 1)
    _note(c, "c", {"es": "la razón de conteos y la de tasas estandarizadas responden preguntas distintas: "
                         "la segunda descuenta la composición etaria. La línea une los años consecutivos de "
                         "cada fuente y la punta de flecha señala el año más reciente; el intervalo de años "
                         "de cada fuente está en la leyenda y el valor de cada año, en la tabla acompañante.",
                   "en": "the ratio of counts and the ratio of standardised rates answer different "
                         "questions: the latter removes the age composition. The line joins consecutive "
                         "years of each source and the arrowhead marks the most recent year; the year range "
                         "of each source is in the legend and the year-by-year values are in the companion "
                         "table."}[lang])
    c.legend(loc="lower right", fontsize=6.6); _title(c, tr("e26b_c", lang)); _letter(c, 2)

    d = A[3]
    last = trend[trend.ratio.notna()].sort_values("year").groupby("source").tail(1).sort_values("ratio")
    yd = np.arange(len(last))[::-1]
    d_labels = [f"{num(r.ratio, 2, lang)} ({ci(r.lo, r.hi, 2, lang)}) · {int(r.year)}"
                for r in last.itertuples()]
    # El eje se estira MIDIENDO el rótulo más ancho —en décadas del eje logarítmico— para que quepa a la
    # derecha del intervalo de su fila: con un múltiplo fijo, el rótulo de la fila más alta no cabía, el
    # motor lo apartaba y pasaba a leerse como el valor de la fila vecina (S42 (d)).
    d_w = max((C.plate_text_width_pt(t, 6.2, "normal") for t in d_labels), default=0.0)
    d_axis_pt = PLATE_W_IN * 72.0 / 2.0 - 96.0
    d_share = min(0.60, d_w / d_axis_pt)
    d_lo = 0.9
    d_hi_dec = np.log10(max(float(max(r.hi, r.ratio)) for r in last.itertuples()))
    # COLUMNA ÚNICA de rótulos, y a la DERECHA de la referencia 4:1. Escritos cada uno pegado al extremo
    # de su propio intervalo, los rótulos de las filas de razón baja caían dentro de la banda que cruzan
    # las dos reglas de referencia (3:1 a trazos y 4:1 punteada) y una regla roja recorría las dieciséis
    # cifras, en varias justo sobre la coma decimal o sobre el paréntesis: el punteado se leía como un
    # signo del propio número. Alineados en una columna a la derecha de la 4:1 —como el bosque de la
    # S38—, ninguna regla los toca y las cifras quedan además comparables entre filas.
    # 0,055 décadas de hueco ≈ el radio del marcador (3 pt) más un blanco: con menos, el rótulo de una
    # fila de intervalo estrecho arrancaba pegado a su propio punto.
    D_REFS = (3.0, 4.0)
    d_col_dec = max(d_hi_dec + 0.055, np.log10(max(D_REFS)) + 0.030)
    d_max = 10.0 ** ((d_col_dec - d_share * np.log10(d_lo)) / (1.0 - d_share))
    d_col_x = 10.0 ** d_col_dec
    for i, r in enumerate(last.itertuples()):
        d.errorbar(r.ratio, yd[i], xerr=[[max(r.ratio - r.lo, 0)], [max(r.hi - r.ratio, 0)]], fmt="o",
                   color=SRC_COLOR[r.source], markersize=6, capsize=3, lw=1.6)
        d.text(d_col_x, yd[i], d_labels[i], fontsize=6.2, va="center", ha="left",
               color="#333333", gid=C.PLATE_KEEP)
    d.axvline(D_REFS[0], color=C.RED, ls="--", lw=1.0); d.axvline(D_REFS[1], color=C.RED, ls=":", lw=1.0)
    # Control local: la columna de rótulos arranca a la derecha de la última referencia y del extremo
    # derecho de todos los intervalos. Si alguna vez deja de cumplirse, la lámina vuelve al defecto.
    assert d_col_x > max(D_REFS) and all(d_col_x > max(r.hi, r.ratio) for r in last.itertuples()), \
        "S42 (d): la columna de rótulos volvería a caer sobre una referencia o sobre un intervalo"
    d.set_yticks(yd)
    d.set_ylim(-0.9, float(np.max(yd)) + 3.1)   # banda libre para la nota de «no estimable»
    d.set_yticklabels([_abbrev(f"{SRC_SHORT[r.source][lang]} · {SRC_UNIT[r.source][lang]}", 28)
                       for r in last.itertuples()], fontsize=6.4)
    d.set_xscale("log"); log_axis_fmt(d, lang, "x"); d.set_xlim(d_lo, max(46.0, float(d_max)))
    d.set_xlabel(tr("e26b_ratio_axis", lang))
    ne_sources = sorted(set(trend[trend.method == "not_estimable"].source))
    if ne_sources:
        _note(d, "d", {"es": "no estimable: " + "; ".join(SRC_SHORT[s][lang] for s in ne_sources)
                             + " (la fuente no publica el sexo de esa serie).",
                       "en": "not estimable: " + "; ".join(SRC_SHORT[s][lang] for s in ne_sources)
                             + " (the source does not publish sex for that series)."}[lang])
    _title(d, tr("e26b_d", lang)); _letter(d, 3)

    e = A[4]
    vsrc = ["grd_any", "deis_principal", "a05_family", "p6_primary"]
    vlab = {"grd_any": SRC_LABEL["grd_any"][lang], "deis_principal": SRC_LABEL["deis_principal"][lang],
            "a05_family": {"es": "REM A05 · ingresos familia TGD", "en": "REM A05 · PDD-family entries"}[lang],
            "p6_primary": SRC_LABEL["p6_primary"][lang]}
    keys = [(s, int(y)) for s in vsrc for y in sorted(by_var[by_var.source == s].year.unique())]
    xe = np.arange(len(keys))
    for off, variant_key, colr in ((-0.17, "con_rett", OKABE[0]), (0.17, "sin_rett", OKABE[1])):
        vals, los, his = [], [], []
        for s, y in keys:
            r = by_var[(by_var.source == s) & (by_var.variant == variant_key) & (by_var.year == y)]
            v = float(r.ratio.iloc[0]) if len(r) else np.nan
            vals.append(v)
            los.append(max(v - float(r.lo.iloc[0]), 0) if len(r) and pd.notna(v) else 0)
            his.append(max(float(r.hi.iloc[0]) - v, 0) if len(r) and pd.notna(v) else 0)
        e.errorbar(xe + off, vals, yerr=[los, his], fmt="o", color=colr, markersize=4.5, capsize=2, lw=1.2,
                   label=tr("e28_con", lang) if variant_key == "con_rett" else tr("e28_sin", lang))
    e.set_xticks(xe)
    e.set_xticklabels([f"{_abbrev(vlab[s].split(' · ')[0], 12)} {y}" for s, y in keys], rotation=90, fontsize=6.2)
    e.set_ylabel(tr("ratio_mf", lang)); fmt_axis(e, lang, "y", 1)
    e.set_ylim(1.0, 6.4); refs(e, len(keys) - 0.6)
    _note(e, "e", {"es": "intervalos recortados por el eje en las celdas con pocos eventos (tabla "
                         "acompañante).",
                   "en": "intervals clipped by the axis in cells with few events (companion table)."}[lang])
    e.legend(loc="upper right", fontsize=6.6); _title(e, tr("e26b_e", lang)); _letter(e, 4)

    f = A[5]
    lastn = last.copy()
    yf = np.arange(len(lastn))[::-1]
    f.barh(yf - 0.19, lastn.males.fillna(0), height=0.36, color=OKABE[0], label=tr("males", lang))
    f.barh(yf + 0.19, lastn.females.fillna(0), height=0.36, color=OKABE[1], label=tr("females", lang))
    f.set_xscale("log"); log_axis_fmt(f, lang, "x"); f.set_xlim(0.8, float(np.nanmax(lastn.males)) * 6)
    f.set_yticks(yf)
    f.set_yticklabels([_abbrev(f"{SRC_SHORT[r.source][lang]} · {int(r.year)}", 24) for r in lastn.itertuples()],
                      fontsize=6.4)
    f.set_xlabel({"es": "Numerador por sexo (escala log; las unidades difieren)",
                  "en": "Sex-specific numerator (log scale; units differ)"}[lang])
    f.tick_params(axis="x", labelsize=6.8)
    f.set_ylim(-0.8, float(yf.max()) + 1.5)
    # La unidad de cada fila pasa a ser una MARCA del eje derecho. Escrita como texto suelto junto a la
    # barra, el motor de descongestión la apartaba una fila entera de su barra y dos unidades contiguas
    # se imprimían una sobre otra («discharges» sobre «episodes», S42 (f)); una marca de eje no se aparta
    # nunca y siempre señala su fila.
    f2 = f.twinx(); f2.grid(False); f2.spines["right"].set_visible(True)
    f2.set_ylim(f.get_ylim()); f2.set_yticks(yf)
    f2.set_yticklabels([SRC_UNIT[r.source][lang] if pd.notna(r.males) else "" for r in lastn.itertuples()],
                       fontsize=6.2, color="#555555")
    f2.tick_params(axis="y", length=0)
    _right_ylabel(f2, tr("unit", lang), base=f)
    f.legend(loc="upper left", fontsize=6.6, ncol=2)
    _title(f, tr("e26b_f", lang)); _letter(f, 5)

    _plate_note(fig, tr("e26b_no_link", lang) + " " + tr("e26b_ref_note", lang), colour=C.RED)
    path = _save_plate(fig, fdir / f"{FIG_NAMES['E26b']}.png", plt)
    return path


def _est_colour(estimands):
    return {e: OKABE[i % len(OKABE)] for i, e in enumerate(sorted(estimands))}


def fig_e27(P, lang, fdir):
    plt, fig, A = _new_plate()
    mod, fit, main = P["models"], P["fitted"], P["main"]
    main_ids = list(P["main_ids"])
    fmain = fit[fit.model_id.isin(main_ids)].copy()
    cols = _est_colour(mod.estimand.unique())

    a = A[0]
    for est, g in fmain.groupby("estimand"):
        a.scatter(g.observed_count, g.fitted_count, s=42, color=cols[est], alpha=0.9, edgecolor="white",
                  linewidth=0.5, label=ESTIMAND_LABEL.get(est, {"es": est, "en": est})[lang])
    lo = float(np.nanmin([fmain.observed_count.min(), fmain.fitted_count.min()]))
    hi = float(np.nanmax([fmain.observed_count.max(), fmain.fitted_count.max()]))
    a.plot([lo * 0.7, hi * 1.4], [lo * 0.7, hi * 1.4], "--", color=GREY, lw=1.0)
    a.set_xscale("log"); a.set_yscale("log"); log_axis_fmt(a, lang); log_axis_fmt(a, lang, "x")
    a.set_xlabel(tr("e27_obs_axis", lang)); a.set_ylabel(tr("e27_fit_axis", lang))
    _note(a, "a", {"es": "un color por estimando; los nombres están en los paneles c, e y f.",
                   "en": "one colour per estimand; the names are in panels c, e and f."}[lang])
    _title(a, tr("e27_a", lang)); _letter(a, 0)

    b = A[1]
    for est, g in fmain.groupby("estimand"):
        gg = g.sort_values("year")
        b.plot(gg.year, gg.pearson, "o-", color=cols[est], lw=1.5, markersize=5,
               label=ESTIMAND_LABEL.get(est, {"es": est, "en": est})[lang])
    b.axhline(0, color="#333333", lw=1.0)
    for lvl in (-2, 2):
        b.axhline(lvl, color=GREY, ls=":", lw=0.9)
    b.set_xticks(YEARS_REM); b.set_xlabel(tr("year", lang)); b.set_ylabel(tr("e27_resid_axis", lang))
    fmt_axis(b, lang, "y", 0)
    context_markers(b, lang, xmin=min(YEARS_REM), xmax=max(YEARS_REM))
    _title(b, tr("e27_b", lang)); _letter(b, 1)

    c = A[2]
    dd = mod.dropna(subset=["dispersion"]).copy()
    dd["group"] = dd.estimand.map(lambda e: est_tiny(e, lang))
    order = dd.groupby("group").dispersion.median().sort_values().index.tolist()
    for i, gname in enumerate(order):
        vals = dd[dd.group == gname].dispersion.values
        jitter = (np.random.RandomState(20260905 + i).rand(len(vals)) - 0.5) * 0.32
        est_key = dd[dd.group == gname].estimand.iloc[0]
        c.scatter(vals, np.full(len(vals), i) + jitter, s=18, color=cols[est_key], alpha=0.75, edgecolor="none")
        c.scatter([np.median(vals)], [i], marker="|", s=260, color="#333333", zorder=4)
    c.axvline(1.0, color=C.RED, ls="--", lw=1.0)
    c.set_yticks(range(len(order))); c.set_yticklabels([_abbrev(g, 24) for g in order], fontsize=6.4)
    c.set_xscale("log"); log_axis_fmt(c, lang, "x")
    c.set_xlabel(tr("e27_disp_axis", lang))
    _note(c, "c", {"es": "línea roja: dispersión = 1 (Poisson); a la derecha, sobredispersión.",
                   "en": "red line: dispersion = 1 (Poisson); to the right, overdispersion."}[lang])
    _title(c, tr("e27_c", lang)); _letter(c, 2)

    d = A[3]
    key_est = ["est_grd_rate", "est_a05_pop", "est_p2", "est_pie", "est_deis"]
    sub = mod[mod.estimand.isin(key_est) & mod.apc.notna()].copy()
    sub = sub.sort_values(["estimand", "apc"])
    yd = np.arange(len(sub))[::-1]
    for i, r in enumerate(sub.itertuples()):
        d.errorbar(r.apc, yd[i], xerr=[[max(r.apc - r.apc_lo, 0)], [max(r.apc_hi - r.apc, 0)]], fmt="o",
                   color=cols[r.estimand], markersize=4, capsize=2, lw=1.1,
                   alpha=1.0 if r.model_id in main_ids else 0.55)
    d.axvline(0, color="#333333", lw=1.0)
    d.set_yticks([]); d.set_xlabel(tr("e27_apc_axis", lang)); fmt_axis(d, lang, "x", 0)
    # Banda libre sobre la primera fila: la leyenda tapaba especificaciones tanto arriba como abajo.
    d.set_ylim(-1.2, float(len(sub)) * 1.26)
    from matplotlib.lines import Line2D
    d.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=cols[e], markersize=5,
                             label=est_tiny(e, lang)) for e in key_est if e in cols],
             loc="upper right", fontsize=6.2, framealpha=0.92)
    _note(d, "d", {"es": f"{num(len(sub), 0, lang)} especificaciones; opacas = especificación principal. "
                        + tr("e27_no_causal", lang),
                   "en": f"{num(len(sub), 0, lang)} specifications; opaque = main specification. "
                        + tr("e27_no_causal", lang)}[lang])
    _title(d, tr("e27_d", lang)); _letter(d, 3)

    e = A[4]
    ee = mod.dropna(subset=["durbin_watson"]).copy()
    ee["group"] = ee.estimand.map(lambda x: est_tiny(x, lang))
    order_e = ee.groupby("group").durbin_watson.median().sort_values().index.tolist()
    for i, gname in enumerate(order_e):
        vals = ee[ee.group == gname].durbin_watson.values
        jitter = (np.random.RandomState(20260906 + i).rand(len(vals)) - 0.5) * 0.32
        est_key = ee[ee.group == gname].estimand.iloc[0]
        e.scatter(vals, np.full(len(vals), i) + jitter, s=18, color=cols[est_key], alpha=0.75, edgecolor="none")
    e.axvline(2.0, color=C.RED, ls="--", lw=1.0)
    e.set_yticks(range(len(order_e))); e.set_yticklabels([_abbrev(g, 24) for g in order_e], fontsize=6.4)
    e.set_xlabel(tr("e27_dw_axis", lang)); fmt_axis(e, lang, "x", 1)
    _note(e, "e", tr("e27_dw_note", lang))
    _title(e, tr("e27_e", lang)); _letter(e, 4)

    f = A[5]
    mm = main.dropna(subset=["apc"]).copy()
    mm["group"] = mm.estimand.map(lambda x: est_tiny(x, lang))
    mm = mm.sort_values("apc")
    yf = np.arange(len(mm))[::-1]
    f_labels = [f"{num(r.apc, 1, lang)} ({ci(r.apc_lo, r.apc_hi, 1, lang)}); disp. {num(r.dispersion, 1, lang)}"
                for r in mm.itertuples()]
    # El eje se estira MIDIENDO el rótulo más ancho, para que quepa entero a la derecha del intervalo de su
    # fila; y el rótulo se marca como anclado a su fila, porque apartado pasa a leerse como el de la vecina.
    f_w = max((C.plate_text_width_pt(t, 6.2, "normal") for t in f_labels), default=0.0)
    f_axis_pt = PLATE_W_IN * 72.0 / 2.0 - 90.0
    f_share = min(0.60, f_w / f_axis_pt)
    f_lo = min(-10.0, float(mm.apc_lo.min()) * 1.15)
    f_gap = 2.0
    f_hi = float(mm.apc_hi.max())
    f_max = (f_hi + f_gap - f_share * f_lo) / (1.0 - f_share)
    for i, r in enumerate(mm.itertuples()):
        f.errorbar(r.apc, yf[i], xerr=[[max(r.apc - r.apc_lo, 0)], [max(r.apc_hi - r.apc, 0)]], fmt="o",
                   color=cols[r.estimand], markersize=6, capsize=3, lw=1.6)
        f.text(r.apc_hi + f_gap, yf[i], f_labels[i], fontsize=6.2, va="center", ha="left", color="#333333",
               gid=C.PLATE_KEEP)
    f.axvline(0, color="#333333", lw=1.0)
    f.set_yticks(yf); f.set_yticklabels([_abbrev(str(g), 22) for g in mm.group], fontsize=6.4)
    f.set_xlabel(tr("e27_apc_axis", lang)); fmt_axis(f, lang, "x", 0)
    f.set_xlim(f_lo, max(f_max, f_hi * 1.2))
    # El periodo ajustado de cada estimando ya no cabe en el rótulo del eje: queda en la tabla acompañante.
    # La nota vive en una BANDA RESERVADA bajo la última fila: el panel es un bosque que ocupa todo el
    # recuadro y, sin banda, la nota tapaba el valor de una fila —daba igual cuál— y ese numero se perdia.
    f.set_ylim(-0.8, float(yf.max()) + 0.6)
    _note(f, "f", {"es": "el periodo ajustado de cada estimando está en la tabla acompañante.",
                   "en": "the fitted period of each estimand is in the companion table."}[lang])
    _title(f, tr("e27_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E27']}.png", plt)
    return path


def fig_e28(P, lang, fdir):
    plt, fig, A = _new_plate()
    t = P["table"]
    panels = [(A[0], 0, tr("e28_a", lang), ["grd_any", "grd_principal"]),
              (A[1], 1, tr("e28_b", lang), ["a05_family"]),
              (A[2], 2, tr("e28_c", lang), ["p6_primary", "p6_specialty"]),
              (A[3], 3, tr("e28_d", lang), ["deis_principal"])]
    for a, letter_, title, series in panels:
        keys = [(s, int(y)) for s in series for y in sorted(t[t.series == s].year.unique())]
        x = np.arange(len(keys))
        con = [float(t[(t.series == s) & (t.year == y)].con_rett.iloc[0]) for s, y in keys]
        sin = [float(t[(t.series == s) & (t.year == y)].sin_rett.iloc[0]) for s, y in keys]
        a.bar(x - 0.19, con, width=0.36, color=OKABE[0], label=tr("e28_con", lang))
        a.bar(x + 0.19, sin, width=0.36, color=OKABE[1], label=tr("e28_sin", lang))
        for i, (c_, s_) in enumerate(zip(con, sin)):
            if c_ != s_:
                a.text(x[i], max(c_, s_) * 1.02, f"−{num(c_ - s_, 0, lang)}", ha="center", fontsize=6.2,
                       color="#333333")
        a.set_xticks(x)
        a.set_xticklabels([str(y) if len(series) == 1 else f"{E28_SHORT[s][lang]}\n{y}" for s, y in keys],
                          fontsize=6.4, rotation=0 if len(series) == 1 else 45,
                          ha="center" if len(series) == 1 else "right")
        a.set_ylabel({"es": "Casos (recuento anual)", "en": "Cases (annual count)"}[lang]); fmt_axis(a, lang, "y", 0)
        a.set_ylim(0, max(max(con), max(sin)) * 1.22)
        a.legend(loc="upper left", fontsize=7); _title(a, title); _letter(a, letter_)

    e = A[4]
    series_order = [s for s in E28_SERIES_LABEL if s in set(t.series)]
    for s in series_order:
        sub = t[t.series == s].sort_values("year")
        e.plot(sub.year, sub.abs_diff, "o-", lw=1.8, markersize=5,
               color=OKABE[series_order.index(s) % len(OKABE)], label=E28_SERIES_LABEL[s][lang])
    e.axhline(0, color="#333333", lw=1.0)
    e.set_xticks(YEARS_REM); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("e28_abs_axis", lang))
    fmt_axis(e, lang, "y", 0)
    e.legend(loc="upper left", fontsize=6.2); _title(e, tr("e28_e", lang)); _letter(e, 4)

    f = A[5]
    for s in series_order:
        sub = t[t.series == s].sort_values("year")
        f.plot(sub.year, sub.rel_diff_pct, "o-", lw=1.8, markersize=5,
               color=OKABE[series_order.index(s) % len(OKABE)], label=E28_SERIES_LABEL[s][lang])
    f.axhline(0, color="#333333", lw=1.0)
    f.set_xticks(YEARS_REM); f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("e28_rel_axis", lang))
    fmt_axis(f, lang, "y", 1)
    _note(f, "f", tr("e28_identical", lang))
    f.legend(loc="upper right", fontsize=6.2); _title(f, tr("e28_f", lang)); _letter(f, 5)

    path = _save_plate(fig, fdir / f"{FIG_NAMES['E28']}.png", plt)
    return path


# ===========================================================================
# Tablas acompañantes (una por lámina)
# ===========================================================================
NOTE_GLOBAL = {
    "es": ("Los recuentos son reconocimiento administrativo, nunca prevalencia ni incidencia. Las fuentes no se enlazan "
           "por persona: ningún cociente entre fuentes es una cascada ni una probabilidad individual. La Ley 21.545 "
           "(marzo de 2023) es contexto de política, no una intervención con efecto estimable. 2020–2021: disrupción del "
           "reporte por la pandemia."),
    "en": ("Counts are administrative recognition, never prevalence or incidence. Sources are not person-linked: no ratio "
           "between sources is a cascade or an individual probability. Law 21.545 (March 2023) is policy context, not an "
           "intervention with an estimable effect. 2020–2021: pandemic reporting disruption."),
}


def _tw(tdir, name, formatted, numeric, titles, title, note):
    write_pair(tdir, name, formatted, numeric)
    titles[name] = {"title": title, "note": note + " " + NOTE_GLOBAL[titles["_lang"]]}


def build_tables(P: dict, variant: str, lang: str, tdir: Path) -> dict:
    """Escribe las diez tablas acompañantes y devuelve el diccionario de títulos y notas."""
    titles: dict = {"_lang": lang}
    vlabel = CFG.VARIANTS[variant]["label"][lang]
    yl = tr("year", lang)

    # --- E20 --------------------------------------------------------------------------------------
    p20 = P["E20"]
    pyr = p20["pyramid"]
    a24 = p20["age2024"].set_index("age_group")
    rows = []
    for ag in AGE5:
        r = {tr("age_group", lang): ag}
        for y in (2019, 2025):
            sub = pyr[(pyr.year == y) & (pyr.age_group == ag)]
            if not len(sub):
                r[f"{y} · {tr('males', lang)}"] = NE[lang]; r[f"{y} · {tr('females', lang)}"] = NE[lang]; continue
            tot = float(pyr[pyr.year == y][["HOMBRE", "MUJER"]].sum().sum())
            r[f"{y} · {tr('males', lang)}"] = n_pct(sub.HOMBRE.iloc[0], 100 * sub.HOMBRE.iloc[0] / tot, lang, 2)
            r[f"{y} · {tr('females', lang)}"] = n_pct(sub.MUJER.iloc[0], 100 * sub.MUJER.iloc[0] / tot, lang, 2)
        r[{"es": "Censo 2024 / base 2017 (2024)", "en": "Censo 2024 / 2017 base (2024)"}[lang]] = (
            num(a24.at[ag, "ratio"], 3, lang) if ag in a24.index else NE[lang])
        rows.append(r)
    natl = p20["national"].set_index("year")
    total_row = {tr("age_group", lang): {"es": "Total", "en": "Total"}[lang]}
    child_row = {tr("age_group", lang): tr("e20_share_axis", lang)}
    for y in (2019, 2025):
        total_row[f"{y} · {tr('males', lang)}"] = num(pyr[pyr.year == y].HOMBRE.sum(), 0, lang)
        total_row[f"{y} · {tr('females', lang)}"] = num(pyr[pyr.year == y].MUJER.sum(), 0, lang)
        child_row[f"{y} · {tr('males', lang)}"] = num(natl.at[y, "child_0_19"], 0, lang)
        child_row[f"{y} · {tr('females', lang)}"] = pct(natl.at[y, "child_share_pct"], lang)
    ratio_col = {"es": "Censo 2024 / base 2017 (2024)", "en": "Censo 2024 / 2017 base (2024)"}[lang]
    total_row[ratio_col] = num(p20["age2024"].censo2024.sum() / p20["age2024"].base2017_2024.sum(), 3, lang)
    child_row[ratio_col] = NE[lang]
    rows.extend([total_row, child_row])
    f20 = pd.DataFrame(rows)
    n20 = pyr.merge(p20["national"], on="year", how="left")
    _tw(tdir, TABLE_NAMES["E20"], f20, n20, titles,
        {"es": f"Tabla E20. Estructura de la población de referencia (INE, proyección al 30 de junio, base Censo 2017), 2019 y 2025 — {vlabel}",
         "en": f"Table E20. Structure of the reference population (INE 30 June projection, Censo 2017 base), 2019 and 2025 — {vlabel}"}[lang],
        {"es": "Unidad: personas residentes. Denominador de los porcentajes: población nacional total del mismo año. "
               "Cobertura: territorio nacional, 16 regiones, grupos quinquenales de la OMS (80+ abierto). Era de "
               "definición: proyecciones base Censo 2017 (serie principal) y Censo 2024 enumerado (puente, nunca fundido "
               "con la base 2017). N reportante: 16 regiones y 346 comunas. Fuente: outputs/tidy/"
               "ine_population_region_national_year_age_sex.csv, ine_population_base_comparison.csv e "
               "ine_population_sensitivity.csv (INE, proyecciones y Censo 2024).",
         "en": "Unit: resident persons. Denominator of the percentages: national population of the same year. Coverage: "
               "national territory, 16 regions, WHO five-year age groups (80+ open-ended). Definition era: Censo 2017 "
               "base projections (primary series) and enumerated Censo 2024 (bridge, never merged with the 2017 base). "
               "Reporting N: 16 regions and 346 comunas. Source: outputs/tidy/"
               "ine_population_region_national_year_age_sex.csv, ine_population_base_comparison.csv and "
               "ine_population_sensitivity.csv (INE projections and Censo 2024)."}[lang])

    # --- E21 --------------------------------------------------------------------------------------
    p21 = P["E21"]
    tramo, cov, aps = p21["tramo"], p21["coverage"], p21["aps_panel"]
    rows = []
    for y in YEARS_REM:
        if y not in cov.index:
            continue
        tot_f = float(cov.at[y, "fonasa_beneficiaries_dec"])
        r = {yl: str(y), "FONASA": num(tot_f, 0, lang)}
        for cl in ["A", "B", "C", "D"]:
            v = float(tramo.at[y, cl]) if y in tramo.index and cl in tramo.columns else np.nan
            r[f"{tr('e21_tramo', lang)} {cl}"] = n_pct(v, 100 * v / tot_f, lang) if pd.notna(v) else NE[lang]
        r["ISAPRE"] = num(cov.at[y, "isapre_beneficiaries_dec"], 0, lang)
        r[{"es": "Inscritos APS", "en": "APS enrolled"}[lang]] = num(cov.at[y, "aps_enrolled_dec"], 0, lang)
        r[{"es": "Centros APS", "en": "APS centres"}[lang]] = num(cov.at[y, "aps_centres"], 0, lang)
        r[{"es": "INE (30 jun)", "en": "INE (30 Jun)"}[lang]] = num(cov.at[y, "ine_population_base2017_30jun"], 0, lang)
        r["(FONASA+ISAPRE)/INE"] = pct(100 * cov.at[y, "share_fonasa_plus_isapre_ine"], lang)
        rows.append(r)
    f21 = pd.DataFrame(rows)
    n21 = cov.reset_index().merge(tramo.reset_index().rename(columns={c: f"fonasa_tramo_{c}" for c in tramo.columns}),
                                  on="year", how="left")
    _tw(tdir, TABLE_NAMES["E21"], f21, n21, titles,
        {"es": f"Tabla E21. Capas de aseguramiento y cobertura operativa (stocks de diciembre), 2019–2025 — {vlabel}",
         "en": f"Table E21. Insurance layers and operational coverage (December stocks), 2019–2025 — {vlabel}"}[lang],
        {"es": "Unidad: beneficiarios o inscritos (stock al 31 de diciembre); INE es una proyección al 30 de junio. "
               "Denominador de los porcentajes de tramo: beneficiarios FONASA del mismo año; de (FONASA+ISAPRE)/INE: "
               "población INE base 2017. Cobertura: FONASA e ISAPRE nacionales; APS localiza el centro de inscripción. "
               "Era de definición: el esquema FONASA cambia en 2021, 2023, 2024 y 2025; APS cambia grupos de edad y "
               "nombres en 2024; ISAPRE pasa de .xls a .xlsx y de edades simples a quinquenales en 2021. N reportante: "
               "centros APS de la columna correspondiente. (FONASA+ISAPRE)/INE NO es una tasa de no aseguramiento: mezcla "
               "stocks de diciembre con una proyección de junio y omite otros regímenes. Fuente: outputs/tidy/"
               "coverage_layers_year.csv, fonasa_beneficiaries_national_year.csv, aps_panel.csv, "
               "isapre_beneficiaries_national_year.csv.",
         "en": "Unit: beneficiaries or enrolled persons (31 December stock); INE is a 30 June projection. Denominator of "
               "the tramo percentages: FONASA beneficiaries of the same year; of (FONASA+ISAPRE)/INE: INE 2017-base "
               "population. Coverage: FONASA and ISAPRE nationwide; APS locates the enrolment centre. Definition era: the "
               "FONASA schema changes in 2021, 2023, 2024 and 2025; APS changes age groups and variable names in 2024; "
               "ISAPRE moves from .xls to .xlsx and from single years to five-year bands in 2021. Reporting N: APS centres "
               "in the corresponding column. (FONASA+ISAPRE)/INE is NOT an uninsured rate: it mixes December stocks with a "
               "June projection and omits other regimes. Source: outputs/tidy/coverage_layers_year.csv, "
               "fonasa_beneficiaries_national_year.csv, aps_panel.csv, isapre_beneficiaries_national_year.csv."}[lang])

    # --- E22 --------------------------------------------------------------------------------------
    p22 = P["E22"]
    panel, by_year, est = p22["panel"], p22["by_year"], p22["per_estab"]
    rows = []
    for y in sorted(panel.index):
        med = float(est[est.year == y].discharges.median())
        q1, q3 = est[est.year == y].discharges.quantile([0.25, 0.75])
        rows.append({yl: str(y),
                     tr("e22_estab_axis", lang): num(panel.at[y, "establishments_reporting"], 0, lang),
                     {"es": "Egresos (todos)", "en": "Discharges (all)"}[lang]: num(panel.at[y, "discharges_total"], 0, lang),
                     {"es": "Egresos (panel 188)", "en": "Discharges (188-panel)"}[lang]:
                         n_pct(panel.at[y, "discharges_panel_188"], 100 * panel.at[y, "retention_discharges"], lang),
                     {"es": "Días-cama disponibles", "en": "Available bed-days"}[lang]:
                         num(by_year.at[y, "bed_days_available"], 0, lang),
                     tr("e22_occ_axis", lang): pct(by_year.at[y, "occupancy_pct"], lang),
                     {"es": "Egresos por establecimiento: mediana (P25–P75)",
                      "en": "Discharges per establishment: median (P25–P75)"}[lang]:
                         f"{num(med, 0, lang)} ({num(q1, 0, lang)}–{num(q3, 0, lang)})"})
    eco = p22["eco"]
    rows.append({yl: {"es": f"Relación ecológica {p22['grd_year']}", "en": f"Ecological relationship {p22['grd_year']}"}[lang],
                 tr("e22_estab_axis", lang): num(len(eco), 0, lang),
                 {"es": "Egresos (todos)", "en": "Discharges (all)"}[lang]:
                     {"es": f"ρ de Spearman = {num(p22['rho'], 2, lang)}", "en": f"Spearman ρ = {num(p22['rho'], 2, lang)}"}[lang],
                 {"es": "Egresos (panel 188)", "en": "Discharges (188-panel)"}[lang]:
                     {"es": "ecológico: no describe riesgo individual", "en": "ecological: does not describe individual risk"}[lang]})
    f22 = pd.DataFrame(rows)
    n22 = panel.reset_index().merge(by_year.reset_index(), on="year", how="left")
    _tw(tdir, TABLE_NAMES["E22"], f22, n22, titles,
        {"es": f"Tabla E22. Actividad y capacidad hospitalaria REM-20 y su relación ecológica con los episodios GRD con F84, 2019–2025 — {vlabel}",
         "en": f"Table E22. REM-20 hospital activity and capacity and its ecological relationship with GRD episodes with F84, 2019–2025 — {vlabel}"}[lang],
        {"es": "Unidad: egresos (episodios) y días-cama; REM-20 mide actividad y capacidad, NUNCA población cubierta y "
               "nunca es un denominador poblacional. Denominador de la retención: egresos o días-cama de todos los "
               "establecimientos del mismo año. Cobertura: establecimientos que reportan REM-20 (columna de "
               "establecimientos reportantes); panel de 188 = establecimientos con 12 meses en todos los años 2019–2025. "
               "Era de definición: serie REM-20 continua 2019–2025. La última fila enlaza el año GRD más reciente con "
               "REM-20 por código de establecimiento DEIS: es una asociación ecológica entre establecimientos, nunca "
               "entre personas. Fuente: outputs/tidy/rem20_panel.csv, rem20_establishment_year.csv, "
               "rem20_establishment_area_year.csv y grd_hospital_year.csv.",
         "en": "Unit: discharges (episodes) and bed-days; REM-20 measures activity and capacity, NEVER covered population "
               "and never a population denominator. Denominator of the retention: discharges or bed-days of all "
               "establishments in the same year. Coverage: establishments reporting REM-20 (reporting-establishments "
               "column); 188-panel = establishments with 12 months in every year 2019–2025. Definition era: continuous "
               "REM-20 series 2019–2025. The last row links the most recent GRD year with REM-20 by DEIS establishment "
               "code: it is an ecological association between establishments, never between persons. Source: "
               "outputs/tidy/rem20_panel.csv, rem20_establishment_year.csv, rem20_establishment_area_year.csv and "
               "grd_hospital_year.csv."}[lang])

    # --- E23 --------------------------------------------------------------------------------------
    p23 = P["E23"]
    allrows = p23["all"].copy()
    rows = []
    for _, r in allrows.iterrows():
        rows.append({{"es": "Encuesta", "en": "Survey"}[lang]: survey_label(r.survey),
                     {"es": "Dominio", "en": "Domain"}[lang]: DOMAIN_SHORT.get(r.domain, {"es": r.domain, "en": r.domain})[lang],
                     {"es": "Subgrupo", "en": "Subgroup"}[lang]: _sub_label(r, lang),
                     "n": num(r.n, 0, lang), {"es": "Casos", "en": "Cases"}[lang]: num(r.cases, 0, lang),
                     f"% ({tr('ci95', lang)})": val_ci(100 * r.proportion, 100 * r.lo, 100 * r.hi, 2, lang),
                     {"es": "Total ponderado", "en": "Weighted total"}[lang]: num(r.weighted_total, 0, lang),
                     "DEFF": num(r.deff, 2, lang),
                     {"es": "EER", "en": "RSE"}[lang]: pct(100 * r.rse, lang),
                     "gl" if lang == "es" else "df": num(r.df, 0, lang),
                     {"es": "Precisión", "en": "Precision"}[lang]:
                         (tr("e23_adequate", lang) if bool(r.reliable) else
                          (FLAG_TEXT["few_cases"][lang] if r.cases < 30 else FLAG_TEXT["high_rse"][lang]))})
    f23 = pd.DataFrame(rows)
    _tw(tdir, TABLE_NAMES["E23"], f23, allrows, titles,
        {"es": f"Tabla E23. ENDIDE 2022 y ENCAVI 2023–2024 con diseño muestral complejo: estimaciones, precisión y dominios marcados — {vlabel}",
         "en": f"Table E23. ENDIDE 2022 and ENCAVI 2023–2024 with complex sampling design: estimates, precision and flagged domains — {vlabel}"}[lang],
        {"es": "Unidad: personas encuestadas. Denominador: personas del dominio con el ítem no perdido (n). Estimador de "
               "razón con linealización de Taylor; IC 95 % logit con t y gl = UPM − estratos; ponderador, estrato y "
               "conglomerado declarados en survey_estimates.csv. Cobertura: ENDIDE 2022 (adultos 18+ y NNA 2–17 por el "
               "responsable principal) y ENCAVI 2023–2024 (personas de 15 años o más). Era de definición: cada encuesta "
               "usa su propia pregunta de autismo, transcrita en la tabla numérica. N reportante: n del dominio y casos no "
               "ponderados. Los dominios con menos de 30 casos o EER > 30 % se marcan y NO se presentan como estimaciones "
               "fiables. No se estiman dominios regionales ni comunales. Fuente: outputs/tidy/survey_estimates.csv "
               "(endide_2022_adultos_cuidadores_nna.dta.zip; ENCAVI 2023–2024).",
         "en": "Unit: surveyed persons. Denominator: persons in the domain with a non-missing item (n). Ratio estimator "
               "with Taylor linearisation; 95% CI on the logit scale with t and df = PSU − strata; weight, stratum and "
               "cluster declared in survey_estimates.csv. Coverage: ENDIDE 2022 (adults 18+ and children 2–17 through the "
               "main carer) and ENCAVI 2023–2024 (persons aged 15 and over). Definition era: each survey uses its own "
               "autism question, transcribed in the numeric companion. Reporting N: domain n and unweighted cases. "
               "Domains with fewer than 30 cases or RSE > 30% are flagged and are NOT presented as reliable estimates. No "
               "regional or comuna domains are estimated. Source: outputs/tidy/survey_estimates.csv "
               "(endide_2022_adultos_cuidadores_nna.dta.zip; ENCAVI 2023–2024)."}[lang])

    # --- E24 --------------------------------------------------------------------------------------
    p24 = P["E24"]
    pie = p24["pie"]
    cols24 = [("pie_tea_strict", {"es": "TEA estricto", "en": "Strict autism"}),
              ("pie_tea_asperger", {"es": "TEA-Asperger", "en": "Autism-Asperger"}),
              ("pie_harmonised_apuntes60", {"es": "Armonizado (Apuntes 60)", "en": "Harmonised (Apuntes 60)"}),
              ("pie_harmonised_sinaces", {"es": "Armonizado (SINACES)", "en": "Harmonised (SINACES)"}),
              ("special_schools_autism", {"es": "Escuelas especiales", "en": "Special schools"}),
              ("pie_tea_regular_entry", {"es": "Ingreso regular", "en": "Regular entry"}),
              ("pie_tea_exceptional_entry", {"es": "Ingreso excepcional", "en": "Exceptional entry"})]
    rows = []
    for y in pie.index:
        r = {yl: str(int(y))}
        for key, lbl in cols24:
            r[lbl[lang]] = num(pie.at[y, key], 0, lang) if key in pie.columns else NE[lang]
        r[{"es": "% de la matrícula PIE", "en": "% of PIE enrolment"}[lang]] = (
            pct(pie.at[y, "pie_harmonised_share_of_pie_pct"], lang)
            if "pie_harmonised_share_of_pie_pct" in pie.columns else NE[lang])
        r[{"es": "% de los postulantes SINACES", "en": "% of SINACES applicants"}[lang]] = (
            pct(pie.at[y, "pie_tea_share_of_applicants_pct"], lang)
            if "pie_tea_share_of_applicants_pct" in pie.columns else NE[lang])
        rows.append(r)
    disc = p24["discrepancy"]
    if disc:
        rows.append({yl: {"es": "Discrepancia 2022", "en": "2022 discrepancy"}[lang],
                     cols24[3][1][lang]: num(disc.get("published"), 0, lang),
                     cols24[2][1][lang]: num(disc.get("apuntes"), 0, lang),
                     cols24[4][1][lang]: num(disc.get("special"), 0, lang),
                     cols24[0][1][lang]: {"es": f"total {num(disc.get('total'), 0, lang)} − escuelas especiales = "
                                                f"{num(disc.get('derived'), 0, lang)} (diferencia {num(disc.get('gap'), 0, lang)})",
                                          "en": f"total {num(disc.get('total'), 0, lang)} − special schools = "
                                                f"{num(disc.get('derived'), 0, lang)} (gap {num(disc.get('gap'), 0, lang)})"}[lang]})
    sx = p24["sex2023"]
    for key, lbl in (("strict", {"es": "TEA estricto 2023 por sexo", "en": "Strict autism 2023 by sex"}),
                     ("asperger", {"es": "TEA-Asperger 2023 por sexo", "en": "Autism-Asperger 2023 by sex"}),
                     ("pie_total", {"es": "Matrícula PIE 2023 por sexo", "en": "PIE enrolment 2023 by sex"})):
        r0 = sx[key]
        rows.append({yl: lbl[lang], cols24[0][1][lang]: f"{tr('males', lang)}: {num(r0['male'], 0, lang)}",
                     cols24[1][1][lang]: f"{tr('females', lang)}: {num(r0['female'], 0, lang)}",
                     cols24[2][1][lang]: f"{tr('ratio_mf', lang)}: {val_ci(r0['ratio'], r0['lo'], r0['hi'], 2, lang)}"})
    f24 = pd.DataFrame(rows)
    _tw(tdir, TABLE_NAMES["E24"], f24, pie.reset_index(), titles,
        {"es": f"Tabla E24. Reconocimiento educativo del autismo: PIE, SINACES y escuelas especiales, 2019–2025 — {vlabel}",
         "en": f"Table E24. Educational recognition of autism: PIE, SINACES and special schools, 2019–2025 — {vlabel}"}[lang],
        {"es": "Unidad: estudiantes (stock escolar anual, no episodios ni personas del sistema de salud). Denominador de "
               "«% de la matrícula PIE»: matrícula total del PIE del mismo año; de «% de los postulantes SINACES»: total "
               "de postulantes al PIE publicado por SINACES. Cobertura: establecimientos con subvención de educación "
               "especial que participan del PIE; las escuelas especiales se informan aparte y NO se suman al PIE. Era de "
               "definición: Apuntes 60 publica TEA estricto y TEA-Asperger 2019–2023 (regla de armonización = suma de "
               "ambos); SINACES publica el total armonizado 2022–2025. La fila «Discrepancia 2022» documenta que el "
               "informe SINACES escribe 42.945 mientras 45.014 − 2.074 = 42.940, coincidente con Apuntes 60. El desglose "
               "por sexo existe solo en 2023. Estas series son idénticas en las dos variantes de definición de caso. "
               "Fuente: outputs/tidy/pie_series.csv y education_summary_year.csv (APUNTES_60_2024_tendencia_PIE_2019_2023.pdf "
               "e informes SINACES).",
         "en": "Unit: students (annual school stock, not health-system episodes or persons). Denominator of '% of PIE "
               "enrolment': total PIE enrolment of the same year; of '% of SINACES applicants': total PIE applicants "
               "published by SINACES. Coverage: schools with special-education funding that take part in PIE; special "
               "schools are reported separately and are NOT added to PIE. Definition era: Apuntes 60 publishes strict "
               "autism and autism-Asperger for 2019–2023 (harmonisation rule = sum of both); SINACES publishes the "
               "harmonised total for 2022–2025. The '2022 discrepancy' row documents that the SINACES report writes "
               "42,945 while 45,014 − 2,074 = 42,940, matching Apuntes 60. The sex split exists only for 2023. These "
               "series are identical in both case-definition variants. Source: outputs/tidy/pie_series.csv and "
               "education_summary_year.csv (APUNTES_60_2024_tendencia_PIE_2019_2023.pdf and SINACES reports)."}[lang])

    # --- E25 --------------------------------------------------------------------------------------
    p25 = P["E25"]
    j, ratios = p25["junaeb"], p25["ratios"]
    rows = []
    for _, r in j[j.sex == "all"].sort_values(["year", "level"]).iterrows():
        rr = ratios[(ratios.year == r.year) & (ratios.level == r.level)]
        rows.append({yl: str(int(r.year)), {"es": "Nivel", "en": "Level"}[lang]: LEVEL_LABEL[r.level][lang],
                     {"es": "Estudiantes del dominio", "en": "Students in domain"}[lang]: num(r.n_students, 0, lang),
                     {"es": "Casos TEA (no ponderados)", "en": "Autism cases (unweighted)"}[lang]:
                         num(r.n_tea_unweighted, 0, lang) if pd.notna(r.n_tea_unweighted) else NE[lang],
                     f"% {tr('e25_weighted', lang)} ({tr('ci95', lang)})":
                         val_ci(r.proportion_weighted_pct, r.lo_pct, r.hi_pct, 2, lang),
                     {"es": "% no ponderado", "en": "% unweighted"}[lang]: pct(r.proportion_unweighted_pct, lang, 2),
                     f"{tr('ratio_mf', lang)} ({tr('ci95', lang)})":
                         (val_ci(rr.ratio.iloc[0], rr.lo.iloc[0], rr.hi.iloc[0], 2, lang) if len(rr) else NE[lang]),
                     {"es": "Ponderador", "en": "Weight"}[lang]:
                         (tr("not_estimable", lang) if r.weight_variable == "ABSENT" else str(r.weight_variable)),
                     {"es": "Estimable", "en": "Estimable"}[lang]:
                         {"yes": {"es": "sí (ponderado)", "en": "yes (weighted)"},
                          "unweighted_only": {"es": "solo no ponderado", "en": "unweighted only"},
                          "no": {"es": "no estimable", "en": "not estimable"}}.get(
                             r.estimable, {"es": r.estimable, "en": r.estimable})[lang]})
    f25 = pd.DataFrame(rows)
    _tw(tdir, TABLE_NAMES["E25"], f25, j, titles,
        {"es": f"Tabla E25. JUNAEB EVE: porcentaje de estudiantes con autismo reportado por el cuidador, por nivel, año y sexo, 2019–2025 — {vlabel}",
         "en": f"Table E25. JUNAEB EVE: percentage of students with caregiver-reported autism by level, year and sex, 2019–2025 — {vlabel}"}[lang],
        {"es": "Unidad: estudiantes encuestados (reporte del cuidador), NO prevalencia nacional. Denominador: estudiantes "
               "del dominio de estimación (filas con ponderador válido en 2024–2025; todas las filas antes). Cobertura: "
               "cohortes escolares seleccionadas de parvularia, 1º básico, 5º básico y 1º medio. Era de definición: el "
               "ítem de TEA aparece en 2023 (sin ponderador publicado, solo porcentaje no ponderado con IC de Wilson); el "
               "ponderador publicado es EXP_REG en 2024 y EXP en 2025; en 2019–2022 el cuestionario no incluye categoría "
               "TEA. En 2024 la variable de 1º medio está completamente vacía: «no estimable», nunca cero. N reportante: "
               "columna de estudiantes del dominio. La razón hombre:mujer usa el método delta sobre el logaritmo con "
               "errores estándar de diseño (2024–2025) o binomiales (2023). Fuente: outputs/tidy/junaeb_tea_year_level.csv "
               "(microdata/{año}/EV_*_JUNAEB_*_desidentificada.csv).",
         "en": "Unit: surveyed students (caregiver report), NOT national prevalence. Denominator: students in the "
               "estimation domain (rows with a valid weight in 2024–2025; all rows before). Coverage: selected school "
               "cohorts in pre-school, grade 1, grade 5 and grade 9. Definition era: the autism item appears in 2023 (no "
               "published weight, unweighted percentage with Wilson CI only); the published weight is EXP_REG in 2024 and "
               "EXP in 2025; in 2019–2022 the questionnaire has no autism category. In 2024 the grade-9 variable is "
               "completely empty: 'not estimable', never zero. Reporting N: students-in-domain column. The male-to-female "
               "ratio uses the delta method on the log scale with design-based (2024–2025) or binomial (2023) standard "
               "errors. Source: outputs/tidy/junaeb_tea_year_level.csv "
               "(microdata/{year}/EV_*_JUNAEB_*_desidentificada.csv)."}[lang])

    # --- E26 --------------------------------------------------------------------------------------
    p26 = P["E26"]
    t26 = p26["table"]
    rows = []
    for y in YEARS_REM:
        r = {yl: str(y)}
        for sysk in SYS_LABEL:
            sub = t26[(t26.system == sysk) & (t26.year == y)]
            if not len(sub):
                r[SYS_LABEL[sysk][lang]] = NE[lang]
                continue
            s0 = sub.iloc[0]
            r[SYS_LABEL[sysk][lang]] = (f"{num(s0.value, 0, lang)} {SYS_UNIT[sysk][lang]}; "
                                        f"{num(s0.per_100k_residents, 1, lang)} /100.000" if lang == "es" else
                                        f"{num(s0.value, 0, lang)} {SYS_UNIT[sysk][lang]}; "
                                        f"{num(s0.per_100k_residents, 1, lang)} /100,000")
            r[SYS_LABEL[sysk][lang]] += f"; {num(s0.per_reporting_unit, 1, lang)} {SYS_REPORTING_UNIT[sysk][lang]}"
        rows.append(r)
    f26 = pd.DataFrame(rows)
    _tw(tdir, TABLE_NAMES["E26"], f26, t26, titles,
        {"es": f"Tabla E26. Comparación entre sistemas administrativos: valor anual, valor por 100.000 residentes y valor por unidad reportante, 2019–2025 — {vlabel}",
         "en": f"Table E26. Comparison across administrative systems: annual value, value per 100,000 residents and value per reporting unit, 2019–2025 — {vlabel}"}[lang],
        {"es": "Celda: valor anual y unidad; valor por 100.000 residentes (población INE base Censo 2017 al 30 de junio); "
               "valor por unidad reportante. LAS UNIDADES DIFIEREN y no son intercambiables: episodios GRD con F84 "
               "documentado, egresos DEIS con F84 principal, ingresos REM A05 por autismo estricto, personas bajo control "
               "REM P2 en diciembre y estudiantes del PIE armonizado. Las fuentes NO se enlazan por persona: ninguna "
               "columna puede leerse como una cascada ni como una probabilidad individual. Unidad reportante: hospital "
               "GRD (panel observado de 65/65/65/65/68/72), establecimiento REM reportante, 100.000 egresos DEIS y 1.000 "
               "postulantes al PIE (el número de establecimientos escolares no se publica en las fuentes usadas). Era de "
               "definición: A05 de autismo estricto solo desde 2021; PIE armonizado combina Apuntes 60 (2019–2023) y "
               "SINACES (2022–2025); GRD y DEIS terminan en 2024. Fuente: outputs/tidy/grd_year_summary.csv, "
               "deis_year_summary.csv, rem_pathway_annual.csv, pie_series.csv, "
               "ine_population_region_national_year_age_sex.csv y models_convergence_index.csv.",
         "en": "Cell: annual value and unit; value per 100,000 residents (INE Censo 2017-base population at 30 June); "
               "value per reporting unit. UNITS DIFFER and are not interchangeable: GRD episodes with documented F84, "
               "DEIS discharges with principal F84, REM A05 strict-autism entries, REM P2 persons under control in "
               "December and harmonised PIE students. Sources are NOT person-linked: no column can be read as a cascade "
               "or an individual probability. Reporting unit: GRD hospital (observed panel of 65/65/65/65/68/72), "
               "reporting REM establishment, 100,000 DEIS discharges and 1,000 PIE applicants (the number of schools is "
               "not published in the sources used). Definition era: strict-autism A05 only from 2021; harmonised PIE "
               "combines Apuntes 60 (2019–2023) and SINACES (2022–2025); GRD and DEIS end in 2024. Source: "
               "outputs/tidy/grd_year_summary.csv, deis_year_summary.csv, rem_pathway_annual.csv, pie_series.csv, "
               "ine_population_region_national_year_age_sex.csv and models_convergence_index.csv."}[lang])

    # --- E26b -------------------------------------------------------------------------------------
    p26b = P["E26b"]
    trend = p26b["trend"]
    rows = []
    for _, r in trend.sort_values(["source", "year"]).iterrows():
        rows.append({{"es": "Fuente", "en": "Source"}[lang]: SRC_LABEL[r.source][lang], yl: str(int(r.year)),
                     tr("unit", lang): SRC_UNIT[r.source][lang],
                     tr("males", lang): num(r.males, 0, lang), tr("females", lang): num(r.females, 0, lang),
                     f"{tr('ratio_mf', lang)} ({tr('ci95', lang)})": val_ci(r.ratio, r.lo, r.hi, 2, lang),
                     {"es": "Método del intervalo", "en": "Interval method"}[lang]: METHOD_LABEL[r.method][lang],
                     {"es": "Base", "en": "Basis"}[lang]:
                         {"counts": {"es": "conteos", "en": "counts"},
                          "standardised_rates": {"es": "tasas estandarizadas por edad", "en": "age-standardised rates"},
                          "proportions": {"es": "proporciones", "en": "proportions"},
                          "persons": {"es": "personas", "en": "persons"}}.get(
                             r.basis, {"es": r.basis, "en": r.basis})[lang]})
    f26b = pd.DataFrame(rows)
    n26b = pd.concat([trend.assign(panel="trend"),
                      p26b["by_age"].assign(panel="by_age", variant=variant),
                      p26b["by_variant"].assign(panel="by_variant")], ignore_index=True)
    _tw(tdir, TABLE_NAMES["E26b"], f26b, n26b, titles,
        {"es": f"Tabla E26b. Razón hombre:mujer del reconocimiento administrativo del autismo en todas las fuentes que informan sexo, 2019–2025 — {vlabel}",
         "en": f"Table E26b. Male-to-female ratio of administrative autism recognition in every source that reports sex, 2019–2025 — {vlabel}"}[lang],
        {"es": "Unidad: la de cada fuente (episodios, personas, egresos, ingresos, personas bajo control, estudiantes, "
               "encuestados); se declara en la columna correspondiente y NO son intercambiables. Denominador: para las "
               "razones de conteos, el propio conteo del sexo opuesto (IC binomial exacto de Clopper–Pearson sobre "
               "p = H/(H+M)); para las razones de tasas, tasas estandarizadas por edad con la población estándar de la OMS "
               "e IC log-normal; para las razones de proporciones, método delta sobre el logaritmo con errores estándar de "
               "diseño complejo (encuestas y JUNAEB 2024–2025) o binomiales (JUNAEB 2023), tratando los dominios como "
               "independientes, que es una aproximación. Cobertura: GRD panel observado (65/65/65/65/68/72 hospitales, "
               "2019–2024); DEIS todos los establecimientos (2019–2024); REM A05 y P2/P6 establecimientos reportantes "
               "(2021–2025 y 2019–2025); PIE 2023, único año con desglose por sexo publicado; JUNAEB cohortes escolares "
               "seleccionadas (2023–2025); ENDIDE 2022 y ENCAVI 2023–2024. Era de definición: A05/P6 de autismo estricto "
               "desde 2021; P2 usa el stock de diciembre; el TGD amplio 2019–2020 no se incluye. N reportante: los "
               "numeradores por sexo aparecen en la tabla. Las personas únicas del GRD dentro del año se informan como "
               "«no estimable» porque la fuente no publica su sexo. Las líneas 3:1 y 4:1 de la lámina son referencias de "
               "la literatura clínica, no un valor esperado. Las celdas con menos de cinco eventos en algún sexo se "
               "suprimen en el desglose por edad. Fuente: outputs/tidy/grd_age_sex_year.csv, models_population_rates.csv, "
               "deis_age_sex_year.csv, rem_a05_age_sex_annual.csv, models_a05_standardised_rates.csv, "
               "rem_pathway_tidy.csv (COL02 Hombres y COL03 Mujeres del diccionario REM), pie_series.csv, "
               "junaeb_tea_year_level.csv y survey_estimates.csv.",
         "en": "Unit: that of each source (episodes, persons, discharges, entries, persons under control, students, "
               "respondents); it is stated in the corresponding column and the units are NOT interchangeable. "
               "Denominator: for ratios of counts, the count of the opposite sex itself (exact Clopper–Pearson binomial "
               "interval on p = M/(M+F)); for ratios of rates, WHO-standardised rates with a log-normal interval; for "
               "ratios of proportions, the delta method on the log scale with complex-design standard errors (surveys and "
               "JUNAEB 2024–2025) or binomial ones (JUNAEB 2023), treating the domains as independent, which is an "
               "approximation. Coverage: GRD observed panel (65/65/65/65/68/72 hospitals, 2019–2024); DEIS all "
               "establishments (2019–2024); REM A05 and P2/P6 reporting establishments (2021–2025 and 2019–2025); PIE "
               "2023, the only year with a published sex split; JUNAEB selected school cohorts (2023–2025); ENDIDE 2022 "
               "and ENCAVI 2023–2024. Definition era: strict-autism A05/P6 from 2021; P2 uses the December stock; the "
               "2019–2020 broad PDD codes are not included. Reporting N: the sex-specific numerators are in the table. "
               "GRD unique persons within year are reported as 'not estimable' because the source does not publish their "
               "sex. The 3:1 and 4:1 lines in the plate are clinical-literature references, not an expected value. Cells "
               "with fewer than five events in either sex are suppressed in the age breakdown. Source: "
               "outputs/tidy/grd_age_sex_year.csv, models_population_rates.csv, deis_age_sex_year.csv, "
               "rem_a05_age_sex_annual.csv, models_a05_standardised_rates.csv, rem_pathway_tidy.csv (COL02 males and "
               "COL03 females in the REM dictionary), pie_series.csv, junaeb_tea_year_level.csv and "
               "survey_estimates.csv."}[lang])

    # --- E27 --------------------------------------------------------------------------------------
    p27 = P["E27"]
    main = p27["main"].copy()
    rows = []
    for _, r in main.sort_values("estimand").iterrows():
        rows.append({{"es": "Estimando", "en": "Estimand"}[lang]:
                         ESTIMAND_LABEL.get(r.estimand, {"es": r.estimand, "en": r.estimand})[lang],
                     {"es": "Variante", "en": "Variant"}[lang]: variant_label(r.variant, lang),
                     {"es": "Años", "en": "Years"}[lang]: C.yspan(r.years),
                     "n": num(r.n_obs, 0, lang),
                     {"es": "Covariables", "en": "Covariates"}[lang]:
                         COV_LABEL.get(r.covariates, {"es": r.covariates, "en": r.covariates})[lang],
                     f"CPA % ({tr('ci95', lang)})" if lang == "es" else f"APC % ({tr('ci95', lang)})":
                         val_ci(r.apc, r.apc_lo, r.apc_hi, 1, lang),
                     {"es": "Dispersión", "en": "Dispersion"}[lang]: num(r.dispersion, 1, lang),
                     "Durbin–Watson": num(r.durbin_watson, 2, lang),
                     {"es": "Especificaciones evaluadas", "en": "Specifications evaluated"}[lang]:
                         num((p27["models"].estimand == r.estimand).sum(), 0, lang)})
    f27 = pd.DataFrame(rows)
    n27 = p27["models"].merge(p27["fitted"][["model_id", "year", "observed_count", "fitted_count", "pearson"]],
                              on="model_id", how="left")
    _tw(tdir, TABLE_NAMES["E27"], f27, n27, titles,
        {"es": f"Tabla E27. Modelos cuasi-Poisson: especificación principal por estimando y diagnóstico entre especificaciones — {vlabel}",
         "en": f"Table E27. Quasi-Poisson models: main specification by estimand and diagnostics across specifications — {vlabel}"}[lang],
        {"es": "Unidad: la del estimando (episodios, ingresos, personas bajo control, estudiantes o egresos). Denominador: "
               "el desplazamiento declarado en el propio modelo (episodios GRD del mismo panel, población INE base 2017, "
               "establecimientos reportantes o ninguno). Cobertura y era de definición: la de cada serie; A05/P6 de "
               "autismo estricto desde 2021, GRD y DEIS hasta 2024, REM hasta 2025. N reportante: n = puntos anuales del "
               "modelo. CPA = 100·(exp(β)−1) con IC 95 % de Wald; dispersión = χ² de Pearson / gl; con menos de ocho "
               "puntos Durbin–Watson es indicativo y no concluyente. Especificación principal = sin covariables y con la "
               "serie más larga disponible; la tabla numérica contiene todas las especificaciones. Ninguna especificación "
               "estima un efecto de la Ley 21.545 y ninguna es una serie de tiempo interrumpida causal. Fuente: "
               "outputs/tidy/models_summary.csv y models_fitted.csv.",
         "en": "Unit: that of the estimand (episodes, entries, persons under control, students or discharges). "
               "Denominator: the offset declared in the model itself (GRD episodes of the same panel, INE 2017-base "
               "population, reporting establishments or none). Coverage and definition era: those of each series; "
               "strict-autism A05/P6 from 2021, GRD and DEIS to 2024, REM to 2025. Reporting N: n = annual points in the "
               "model. APC = 100·(exp(β)−1) with Wald 95% CI; dispersion = Pearson χ² / df; with fewer than eight points "
               "Durbin–Watson is indicative and not conclusive. Main specification = no covariates and the longest "
               "available series; the numeric companion carries every specification. No specification estimates an effect "
               "of Law 21.545 and none is a causal interrupted time series. Source: outputs/tidy/models_summary.csv and "
               "models_fitted.csv."}[lang])

    # --- E28 --------------------------------------------------------------------------------------
    t28 = P["E28"]["table"]
    rows = []
    for _, r in t28.sort_values(["series", "year"]).iterrows():
        rows.append({{"es": "Serie", "en": "Series"}[lang]: E28_SERIES_LABEL.get(
                        r.series, {"es": r.series, "en": r.series})[lang],
                     yl: str(int(r.year)),
                     tr("e28_con", lang): num(r.con_rett, 0, lang),
                     tr("e28_sin", lang): num(r.sin_rett, 0, lang),
                     tr("e28_abs_axis", lang): num(r.abs_diff, 0, lang),
                     tr("e28_rel_axis", lang): pct(r.rel_diff_pct, lang, 2)})
    f28 = pd.DataFrame(rows)
    _tw(tdir, TABLE_NAMES["E28"], f28, t28, titles,
        {"es": "Tabla E28. Sensibilidad de cada serie a la variante de definición de caso: F84 completo (con síndrome de Rett) frente a F84 sin Rett, 2019–2025",
         "en": "Table E28. Sensitivity of every series to the case-definition variant: full F84 (with Rett syndrome) versus F84 without Rett, 2019–2025"}[lang],
        {"es": "Unidad: la de cada serie (episodios GRD, egresos DEIS, ingresos REM A05, personas bajo control REM P6, "
               "estudiantes del PIE). Denominador de la diferencia relativa: el valor de la variante sin Rett. Cobertura: "
               "GRD panel observado 2019–2024; DEIS todos los establecimientos 2019–2024; REM establecimientos reportantes "
               "2021–2025 (P6) y 2021–2025 (A05); educación 2019–2025. Era de definición: con_rett incluye F84.2 en GRD y "
               "DEIS y las filas de Rett en REM (05990024/05990029, P6241030/P6241080); sin_rett las excluye. Las series "
               "de educación, encuestas, A03/A27/A28, P2 y autismo estricto son idénticas en ambas variantes y se muestran "
               "con diferencia cero. Fuente: outputs/tidy/grd_year_summary.csv, deis_year_summary.csv, "
               "rem_pathway_annual.csv y pie_series.csv.",
         "en": "Unit: that of each series (GRD episodes, DEIS discharges, REM A05 entries, REM P6 persons under control, "
               "PIE students). Denominator of the relative difference: the value of the without-Rett variant. Coverage: "
               "GRD observed panel 2019–2024; DEIS all establishments 2019–2024; REM reporting establishments 2021–2025 "
               "(P6) and 2021–2025 (A05); education 2019–2025. Definition era: con_rett includes F84.2 in GRD and DEIS "
               "and the Rett rows in REM (05990024/05990029, P6241030/P6241080); sin_rett excludes them. The education, "
               "survey, A03/A27/A28, P2 and strict-autism series are identical in both variants and are shown with a zero "
               "difference. Source: outputs/tidy/grd_year_summary.csv, deis_year_summary.csv, rem_pathway_annual.csv and "
               "pie_series.csv."}[lang])

    titles.pop("_lang", None)
    return titles


# ===========================================================================
# Leyendas autónomas de las láminas
# ===========================================================================
def captions(P: dict, variant: str, lang: str) -> dict:
    v = CFG.VARIANTS[variant]["label"][lang]
    last21 = P["E21"]["last_year"]
    last22 = P["E22"]["last_year"]
    gy = P["E22"]["grd_year"]
    rho = P["E22"]["rho"]
    n_eco = len(P["E22"]["eco"])
    g = NOTE_GLOBAL[lang]
    C_ = {}
    if lang == "es":
        C_[FIG_NAMES["E20"]] = {
            "title": f"Figura E20. Estructura de la población de referencia (INE), 2019–2025 — {v}",
            "caption": (
                "(a) y (b) Pirámides de población nacional en 2019 y 2025 por grupo quinquenal de la OMS y sexo, como "
                "porcentaje de la población total del mismo año (proyecciones INE base Censo 2017 al 30 de junio; "
                "80+ abierto). (c) Población de 0 a 19 años por región en 2019 y 2025, en miles y escala logarítmica, con "
                "el cambio porcentual entre ambos años junto a cada barra (16 regiones). (d) Total nacional según la base "
                "Censo 2017 y la base 2024, con su cociente en el eje derecho: las bases censales nunca se funden y la "
                "base 2017 es el denominador principal de todo el estudio. (e) Población de 2024 por grupo etario según "
                "la proyección base 2017 al 30 de junio y según el Censo 2024 enumerado, con su cociente: el Censo 2024 "
                "enumera menos población infantil que la proyección, de modo que las tasas por 100.000 habitantes "
                "dependen de la base elegida. (f) Población nacional por año y proporción de 0 a 19 años. Unidad: "
                "personas residentes; denominador: población nacional del mismo año; cobertura: territorio nacional. "
                "Fuente: outputs/tidy/ine_population_region_national_year_age_sex.csv, "
                "ine_population_base_comparison.csv e ine_population_sensitivity.csv. " + g)}
        C_[FIG_NAMES["E21"]] = {
            "title": f"Figura E21. Cobertura de aseguramiento y cobertura operativa en detalle (stocks de diciembre), 2019–2025 — {v}",
            "caption": (
                "(a) Beneficiarios FONASA por tramos A a D y año, en millones, con el total anotado sobre cada barra. "
                "(b) Beneficiarios FONASA por grupo quinquenal de edad y sexo en el último año disponible "
                f"({last21}). (c) Beneficiarios ISAPRE por grupo quinquenal de edad en el primer y el último año, con el "
                "número de beneficiarios fuera de las bandas etarias (nonatos o edad no informada) indicado en el panel. "
                "(d) Inscritos APS por tramo (A–D, X y tramo no informado) y centros APS reportantes en el eje derecho. "
                f"(e) Distribución regional en {last21}: beneficiarios FONASA, beneficiarios ISAPRE e inscritos APS como "
                "porcentaje de la población INE de cada región; las geografías NO son homogéneas (FONASA mezcla comuna de "
                "inscripción APS y domicilio, APS localiza el centro e ISAPRE usa la comuna administrativa del "
                "beneficiario), por lo que la suma puede superar el 100 %. (f) Capas de cobertura por año con "
                "(FONASA+ISAPRE)/INE en el eje derecho. Unidad: beneficiarios o inscritos, stock al 31 de diciembre; INE "
                "es una proyección al 30 de junio, de modo que el cociente es indicativo y NO una tasa de no "
                "aseguramiento. Ninguna de estas capas es un denominador de autismo: responden preguntas distintas "
                "(cobertura de aseguramiento, cobertura operativa y población territorial). Fuente: outputs/tidy/"
                "coverage_layers_year.csv, fonasa_beneficiaries_national_year.csv, fonasa_beneficiaries_comuna_year.csv, "
                "aps_panel.csv, aps_enrolment_comuna_year.csv, isapre_beneficiaries_comuna_year.csv. " + g)}
        C_[FIG_NAMES["E22"]] = {
            "title": f"Figura E22. Actividad y capacidad hospitalaria REM-20 y su relación ecológica con los episodios GRD con F84, 2019–2025 — {v}",
            "caption": (
                "(a) Egresos REM-20 por año en todos los establecimientos y en el panel fijo de 188 establecimientos con "
                "doce meses reportados en todos los años, con el número de establecimientos reportantes en el eje "
                "derecho. (b) Días-cama disponibles y ocupados por año y porcentaje de ocupación. (c) Distribución de los "
                "egresos por establecimiento y año (caja: P25–P75; línea: mediana; bigotes sin valores extremos; el "
                "número de establecimientos aparece bajo cada caja). (d) Retención del panel de 188: proporción de los "
                "egresos y de los días-cama del total que el panel conserva cada año. "
                f"(e) Días-cama disponibles por área funcional en {last22} (diez áreas mayores) con los egresos "
                f"anotados. (f) Relación ecológica en {gy} entre los egresos REM-20 del establecimiento y los episodios "
                f"GRD con F84 documentado del mismo establecimiento, enlazados por código DEIS "
                f"(n = {num(n_eco, 0, lang)} establecimientos; ρ de Spearman = {num(rho, 2, lang)}; ambos ejes "
                "logarítmicos). ADVERTENCIA ECOLÓGICA: la asociación es entre establecimientos, no entre personas, y no "
                "describe riesgo individual. Unidad: egresos (episodios) y días-cama; REM-20 mide actividad y capacidad, "
                "nunca población cubierta. Fuente: outputs/tidy/rem20_panel.csv, rem20_establishment_year.csv, "
                "rem20_establishment_area_year.csv y grd_hospital_year.csv. " + g)}
        C_[FIG_NAMES["E23"]] = {
            "title": "Figura E23. ENDIDE 2022 y ENCAVI 2023–2024 analizadas con su diseño muestral complejo: estimaciones, precisión y dominios marcados",
            "caption": (
                "(a) ENDIDE 2022, adultos de 18 años o más: proporción ponderada de autismo reportado, por total, sexo y "
                "grupo etario, con IC 95 % y el número de casos no ponderados junto a cada punto. (b) ENDIDE 2022, niños, "
                "niñas y adolescentes de 2 a 17 años informados por el responsable principal. (c) ENCAVI 2023–2024, "
                "personas de 15 años o más con diagnóstico de trastorno del espectro autista. (d) Efecto de diseño (DEFF) "
                "por dominio, con la referencia DEFF = 1. (e) Error estándar relativo por dominio con el umbral de 30 %. "
                "(f) Casos no ponderados y tamaño del dominio (escala logarítmica) con el umbral de 30 casos. Los "
                "paneles d–f resumen el DOMINIO (la fila «total»); los subgrupos por sexo y por grupo etario aparecen en "
                "los paneles a–c y completos en la tabla acompañante. Los "
                "dominios con menos de 30 casos o con error estándar relativo mayor que 30 % se dibujan en gris y NO se "
                "presentan como estimaciones fiables. No se estiman dominios regionales ni comunales porque el tamaño "
                "efectivo no los sostiene. Unidad: personas encuestadas; denominador: personas del dominio con el ítem no "
                "perdido; estimador de razón con linealización de Taylor e IC logit con t y gl = UPM − estratos. Fuente: "
                "outputs/tidy/survey_estimates.csv. " + g)}
        C_[FIG_NAMES["E24"]] = {
            "title": "Figura E24. Reconocimiento educativo del autismo: PIE, SINACES y escuelas especiales, 2019–2025",
            "caption": (
                "(a) Series del PIE por definición y fuente: TEA estricto y TEA-Asperger (Apuntes 60, 2019–2023), el "
                "armonizado de Apuntes 60 (regla: TEA estricto + TEA-Asperger) y el armonizado publicado por SINACES "
                "(2022–2025); las dos series armonizadas se dibujan por separado porque provienen de informes distintos. "
                "(b) La discrepancia de 2022: el total SINACES menos las escuelas especiales da 42.940, coincidente con "
                "Apuntes 60, mientras el informe SINACES escribe 42.945; la diferencia de cinco casos se documenta y no "
                "se corrige. (c) PIE armonizado y TEA estricto como proporción de la matrícula PIE, y PIE armonizado como "
                "proporción de los postulantes SINACES. (d) Estudiantes autistas en escuelas especiales y total SINACES "
                "por año; las escuelas especiales no se suman al PIE. (e) Desglose por sexo de 2023, único año publicado, "
                "con la razón hombre:mujer e IC binomial exacto (escala logarítmica). (f) Ingreso regular y excepcional "
                "al PIE, con la proporción de ingresos excepcionales anotada. Unidad: estudiantes (stock escolar anual); "
                "cobertura: establecimientos con subvención de educación especial que participan del PIE. Estas series "
                "son idénticas en las dos variantes de definición de caso. Fuente: outputs/tidy/pie_series.csv y "
                "education_summary_year.csv. " + g)}
        C_[FIG_NAMES["E25"]] = {
            "title": "Figura E25. JUNAEB EVE: autismo reportado por el cuidador en cohortes escolares seleccionadas, 2019–2025",
            "caption": (
                "(a) Porcentaje ponderado de estudiantes con autismo reportado por nivel y año, con IC 95 %; las cruces "
                "marcan los años no estimables como porcentaje ponderado. (b) Porcentaje por sexo, nivel y año; el "
                "asterisco señala las celdas sin ponderador publicado, donde se muestra el porcentaje no ponderado. "
                "(c) Estudiantes del dominio de estimación (barras, eje izquierdo) y casos con autismo no ponderados "
                "(puntos y línea punteada, eje derecho). (d) Porcentaje ponderado frente a no ponderado, con la "
                "diagonal de identidad. (e) Razón hombre:mujer por nivel y año, con las referencias 3:1 y 4:1 de la "
                "literatura clínica. (f) Disponibilidad del ítem de autismo y del ponderador por año y nivel. El "
                "cuestionario no incluye categoría de autismo en 2019–2022; el ítem aparece en 2023 sin ponderador "
                "publicado; el ponderador publicado es EXP_REG en 2024 y EXP en 2025; en 2024 la variable de 1º medio "
                "está completamente vacía y se informa como «no estimable», nunca como cero. Unidad: estudiantes "
                "encuestados (reporte del cuidador); denominador: estudiantes del dominio de estimación. JUNAEB "
                "representa cohortes escolares seleccionadas y NO es prevalencia nacional. Fuente: outputs/tidy/"
                "junaeb_tea_year_level.csv. " + g)}
        C_[FIG_NAMES["E26"]] = {
            "title": f"Figura E26. Comparación entre sistemas administrativos: índice, valor bruto, tasa poblacional y valor por unidad reportante, con sus denominadores, 2019–2025 — {v}",
            "caption": (
                "(a) Valor anual de cada sistema indexado al año base declarado en el eje (el primer año común a todas "
                "las series, porque los códigos REM de autismo estricto empiezan en 2021), en escala logarítmica: los "
                "índices comparan trayectorias, nunca niveles; junto a cada entrada de la leyenda, el valor del último "
                "año de esa serie. (b) Valor anual bruto de cada fuente en su propia unidad, en escala logarítmica, "
                "antes de cualquier normalización. (c) Valor anual por 100.000 residentes usando la población "
                "INE base Censo 2017 al 30 de junio como denominador común, y (d) ese denominador poblacional año a año. "
                "(e) Valor por unidad reportante: episodios "
                "GRD por hospital del panel observado, egresos DEIS por 100.000 egresos, ingresos REM A05 y personas bajo "
                "control REM P2 por establecimiento reportante, y estudiantes del PIE por 1.000 postulantes (el número de "
                "establecimientos escolares no se publica en las fuentes usadas); (f) los denominadores de ese panel: "
                "hospitales GRD reportantes, establecimientos REM reportantes, egresos DEIS totales y postulantes al PIE. "
                "LAS UNIDADES DIFIEREN: episodios, "
                "egresos, ingresos, personas bajo control y estudiantes no son intercambiables; los paneles tienen "
                "ejes separados y las fuentes NO se enlazan por persona, por lo que ninguna comparación puede leerse como "
                "una cascada ni como una probabilidad individual. Fuente: outputs/tidy/models_convergence_index.csv, "
                "grd_year_summary.csv, deis_year_summary.csv, rem_pathway_annual.csv, pie_series.csv e "
                "ine_population_region_national_year_age_sex.csv. " + g)}
        C_[FIG_NAMES["E26b"]] = {
            "title": f"Figura E26b. Razón hombre:mujer del reconocimiento administrativo del autismo en todas las fuentes que informan sexo, 2019–2025 — {v}",
            "caption": (
                "(a) Tendencia de la razón hombre:mujer por fuente (escala logarítmica): episodios GRD con F84 "
                "documentado y con F84 principal, egresos DEIS con F84 principal, ingresos REM A05 por autismo, stock de "
                "diciembre de REM P2 y de REM P6 en APS y en especialidad, porcentajes ponderados de JUNAEB por nivel, el "
                "desglose por sexo del PIE de 2023 y las estimaciones de ENDIDE 2022 y ENCAVI 2023–2024; las bandas "
                "muestran el IC 95 % de las tres series principales. (b) Razón por grupo etario quinquenal y fuente en el "
                "último año disponible de cada una; las celdas con menos de cinco eventos en algún sexo se suprimen y se "
                "marcan «<5». (c) Razón de conteos frente a razón de tasas estandarizadas por edad para GRD y REM A05, "
                "con la diagonal de identidad: la estandarización descuenta la composición etaria y por eso las dos "
                "medidas no coinciden. (d) Forest del último año disponible en cada fuente, con la unidad de cada punto "
                "(episodios, personas, egresos, ingresos, personas bajo control, estudiantes o encuestados) y el intervalo "
                "correspondiente. (e) La misma razón calculada en las dos variantes de definición de caso. (f) "
                "Numeradores por sexo que sostienen cada razón, en escala logarítmica, con la unidad de cada fuente "
                "junto a la barra; el método del intervalo de cada fuente está en la tabla acompañante. "
                "Intervalos: binomial exacto de Clopper–Pearson para razones de conteos, log-normal para "
                "razones de tasas estandarizadas y método delta sobre el logaritmo con errores estándar de diseño "
                "complejo (encuestas y JUNAEB 2024–2025) o binomiales (JUNAEB 2023) para razones de proporciones. Las "
                "líneas 3:1 y 4:1 son referencias de la literatura clínica, no un valor esperado de estos registros. LAS "
                "FUENTES NO SE ENLAZAN POR PERSONA y miden cosas distintas, de modo que las razones no son comparables "
                "entre sí como si midieran lo mismo; las personas únicas del GRD dentro del año se informan como «no "
                "estimable» porque la fuente no publica su sexo. Fuente: outputs/tidy/grd_age_sex_year.csv, "
                "models_population_rates.csv, deis_age_sex_year.csv, rem_a05_age_sex_annual.csv, "
                "models_a05_standardised_rates.csv, rem_pathway_tidy.csv, pie_series.csv, junaeb_tea_year_level.csv y "
                "survey_estimates.csv. " + g)}
        C_[FIG_NAMES["E27"]] = {
            "title": f"Figura E27. Diagnóstico de los modelos cuasi-Poisson y sensibilidad entre especificaciones — {v}",
            "caption": (
                "(a) Recuento ajustado frente a recuento observado de la especificación principal de cada estimando, en "
                "escala logarítmica, con la diagonal de identidad; el color identifica el estimando y sus nombres están "
                "rotulados en los paneles c, e y f. (b) Residuos de Pearson por año, con las referencias "
                "±2; los años 2020–2021 aparecen sombreados como disrupción del reporte. (c) Dispersión (χ² de Pearson / "
                "gl) de todas las especificaciones por estimando, con la mediana marcada y la referencia de dispersión = "
                "1: la sobredispersión motiva el uso de errores cuasi-Poisson. (d) Forest de sensibilidad con el cambio "
                "porcentual anual e IC 95 % de todas las especificaciones de los estimandos principales; las "
                "especificaciones principales aparecen en tono pleno. (e) Durbin–Watson de todas las especificaciones; "
                "con menos de ocho puntos anuales es indicativo y no concluyente. (f) Cambio porcentual anual de la "
                "especificación principal por estimando, con IC 95 % y dispersión; el periodo ajustado de cada "
                "estimando está en la tabla acompañante. Unidad y denominador: los del propio "
                "estimando (episodios GRD del mismo panel, población INE base 2017, establecimientos reportantes o "
                "ninguno). Ninguna especificación estima un efecto de la Ley 21.545 y ninguna constituye una serie de "
                "tiempo interrumpida causal. Fuente: outputs/tidy/models_summary.csv y models_fitted.csv. " + g)}
        C_[FIG_NAMES["E28"]] = {
            "title": "Figura E28. Sensibilidad de cada serie a la variante de definición de caso: F84 completo (con síndrome de Rett) frente a F84 sin Rett, 2019–2025",
            "caption": (
                "(a) Episodios GRD con F84 documentado en cualquier posición y con F84 principal, panel observado. "
                "(b) Ingresos REM A05 de la familia de trastornos generalizados del desarrollo, 2021–2025. (c) Población "
                "REM P6 bajo control en diciembre, en APS y en especialidad. (d) Egresos DEIS con F84 principal. En los "
                "cuatro paneles la anotación sobre cada par indica el número de casos que aporta el síndrome de Rett. "
                "(e) Diferencia absoluta con_rett − sin_rett por serie y año. (f) Diferencia relativa, con el valor de la "
                "variante sin Rett como denominador. Las series de educación, encuestas, A03/A27/A28, P2 y autismo "
                "estricto son idénticas en ambas variantes y aparecen con diferencia cero. Unidad: la de cada serie "
                "(episodios, egresos, ingresos, personas bajo control o estudiantes). Fuente: outputs/tidy/"
                "grd_year_summary.csv, deis_year_summary.csv, rem_pathway_annual.csv y pie_series.csv. " + g)}
    else:
        C_[FIG_NAMES["E20"]] = {
            "title": f"Figure E20. Structure of the reference population (INE), 2019–2025 — {v}",
            "caption": (
                "(a) and (b) National population pyramids in 2019 and 2025 by WHO five-year age group and sex, as a "
                "percentage of the total population of the same year (INE Censo 2017-base projections at 30 June; 80+ "
                "open-ended). (c) Population aged 0–19 by region in 2019 and 2025, in thousands on a log scale, with the "
                "percentage change between the two years beside each bar (16 regions). (d) National total under the Censo "
                "2017 base and the 2024 base, with their ratio on the right axis: census bases are never merged and the "
                "2017 base is the primary denominator throughout the study. (e) The 2024 population by age group under "
                "the 2017-base 30 June projection and under the enumerated Censo 2024, with their ratio: Censo 2024 "
                "enumerates fewer children than the projection, so rates per 100,000 population depend on the base "
                "chosen. (f) National population by year and share aged 0–19. Unit: resident persons; denominator: "
                "national population of the same year; coverage: national territory. Source: outputs/tidy/"
                "ine_population_region_national_year_age_sex.csv, ine_population_base_comparison.csv and "
                "ine_population_sensitivity.csv. " + g)}
        C_[FIG_NAMES["E21"]] = {
            "title": f"Figure E21. Insurance and operational coverage in detail (December stocks), 2019–2025 — {v}",
            "caption": (
                "(a) FONASA beneficiaries by tramos A to D and year, in millions, with the total annotated above each bar. "
                f"(b) FONASA beneficiaries by five-year age group and sex in the latest available year ({last21}). "
                "(c) ISAPRE beneficiaries by five-year age group in the first and last year, with the number of "
                "beneficiaries outside the age bands (unborn or age not reported) stated in the panel. (d) APS enrolment "
                "by tramo (A–D, X and tramo not reported) and reporting APS centres on the right axis. (e) Regional "
                f"distribution in {last21}: FONASA beneficiaries, ISAPRE beneficiaries and APS enrolment as a percentage "
                "of each region's INE population; the geographies are NOT homogeneous (FONASA mixes APS-enrolment comuna "
                "and domicile, APS locates the centre and ISAPRE uses the beneficiary's administrative comuna), so the "
                "sum can exceed 100%. (f) Coverage layers by year with (FONASA+ISAPRE)/INE on the right axis. Unit: "
                "beneficiaries or enrolled persons, 31 December stock; INE is a 30 June projection, so the ratio is "
                "indicative and NOT an uninsured rate. None of these layers is an autism denominator: they answer "
                "different questions (insurance coverage, operational coverage and territorial population). Source: "
                "outputs/tidy/coverage_layers_year.csv, fonasa_beneficiaries_national_year.csv, "
                "fonasa_beneficiaries_comuna_year.csv, aps_panel.csv, aps_enrolment_comuna_year.csv, "
                "isapre_beneficiaries_comuna_year.csv. " + g)}
        C_[FIG_NAMES["E22"]] = {
            "title": f"Figure E22. REM-20 hospital activity and capacity and its ecological relationship with GRD episodes with F84, 2019–2025 — {v}",
            "caption": (
                "(a) REM-20 discharges by year in all establishments and in the fixed panel of 188 establishments with "
                "twelve months reported in every year, with the number of reporting establishments on the right axis. "
                "(b) Available and occupied bed-days by year and occupancy percentage. (c) Distribution of discharges per "
                "establishment and year (box: P25–P75; line: median; whiskers without outliers; the number of "
                f"establishments appears under each box). (d) Retention of the 188-panel: the share of total discharges "
                f"and bed-days the panel retains each year. (e) Available bed-days by functional area in {last22} (ten "
                f"largest areas) with discharges annotated. (f) Ecological relationship in {gy} between an "
                "establishment's REM-20 discharges and the GRD episodes with documented F84 of the same establishment, "
                f"linked by DEIS code (n = {num(n_eco, 0, lang)} establishments; Spearman ρ = {num(rho, 2, lang)}; both "
                "axes logarithmic). ECOLOGICAL WARNING: the association is between establishments, not persons, and does "
                "not describe individual risk. Unit: discharges (episodes) and bed-days; REM-20 measures activity and "
                "capacity, never covered population. Source: outputs/tidy/rem20_panel.csv, rem20_establishment_year.csv, "
                "rem20_establishment_area_year.csv and grd_hospital_year.csv. " + g)}
        C_[FIG_NAMES["E23"]] = {
            "title": "Figure E23. ENDIDE 2022 and ENCAVI 2023–2024 analysed with their complex sampling design: estimates, precision and flagged domains",
            "caption": (
                "(a) ENDIDE 2022, adults aged 18 and over: weighted proportion of reported autism by total, sex and age "
                "group, with 95% CI and the number of unweighted cases beside each point. (b) ENDIDE 2022, children and "
                "adolescents aged 2–17 reported by the main carer. (c) ENCAVI 2023–2024, persons aged 15 and over with a "
                "diagnosis of autism spectrum disorder. (d) Design effect (DEFF) by domain, with the DEFF = 1 reference. "
                "(e) Relative standard error by domain with the 30% threshold. (f) Unweighted cases and domain size (log "
                "scale) with the 30-case threshold. Panels d-f summarise the DOMAIN (the 'total' row); the sex and age "
                "subgroups are in panels a-c and complete in the companion table. "
                "Domains with fewer than 30 cases or a relative standard error above "
                "30% are drawn in grey and are NOT presented as reliable estimates. Regional and comuna domains are not "
                "estimated because the effective sample does not support them. Unit: surveyed persons; denominator: "
                "persons in the domain with a non-missing item; ratio estimator with Taylor linearisation and a logit CI "
                "with t and df = PSU − strata. Source: outputs/tidy/survey_estimates.csv. " + g)}
        C_[FIG_NAMES["E24"]] = {
            "title": "Figure E24. Educational recognition of autism: PIE, SINACES and special schools, 2019–2025",
            "caption": (
                "(a) PIE series by definition and source: strict autism and autism-Asperger (Apuntes 60, 2019–2023), the "
                "Apuntes 60 harmonised series (rule: strict autism + autism-Asperger) and the harmonised total published "
                "by SINACES (2022–2025); the two harmonised series are drawn separately because they come from different "
                "reports. (b) The 2022 discrepancy: the SINACES total minus special schools gives 42,940, matching "
                "Apuntes 60, while the SINACES report writes 42,945; the five-case difference is documented and not "
                "corrected. (c) Harmonised PIE and strict autism as a share of PIE enrolment, and harmonised PIE as a "
                "share of SINACES applicants. (d) Autistic students in special schools and the SINACES total by year; "
                "special schools are not added to PIE. (e) The 2023 sex split, the only published year, with the "
                "male-to-female ratio and an exact binomial interval (log scale). (f) Regular and exceptional entry to "
                "PIE, with the share of exceptional entries annotated. Unit: students (annual school stock); coverage: "
                "schools with special-education funding that take part in PIE. These series are identical in both "
                "case-definition variants. Source: outputs/tidy/pie_series.csv and education_summary_year.csv. " + g)}
        C_[FIG_NAMES["E25"]] = {
            "title": "Figure E25. JUNAEB EVE: caregiver-reported autism in selected school cohorts, 2019–2025",
            "caption": (
                "(a) Weighted percentage of students with reported autism by level and year, with 95% CI; crosses mark "
                "the years that are not estimable as a weighted percentage. (b) Percentage by sex, level and year; the "
                "asterisk marks cells without a published weight, where the unweighted percentage is shown. (c) Students "
                "in the estimation domain (bars, left axis) and unweighted autism cases (dots and dotted line, right "
                "axis). (d) Weighted versus unweighted percentage, with the identity diagonal. (e) Male-to-female ratio "
                "by level and year, with the 3:1 and 4:1 clinical-literature references. (f) Availability of the autism "
                "item and of the weight by year and level. The questionnaire has no autism category in 2019–2022; the "
                "item appears in 2023 with no published weight; the published weight is EXP_REG in 2024 and EXP in 2025; "
                "in 2024 the grade-9 variable is completely empty and is reported as 'not estimable', never as zero. "
                "Unit: surveyed students (caregiver report); denominator: students in the estimation domain. JUNAEB "
                "represents selected school cohorts and is NOT national prevalence. Source: outputs/tidy/"
                "junaeb_tea_year_level.csv. " + g)}
        C_[FIG_NAMES["E26"]] = {
            "title": f"Figure E26. Comparison across administrative systems: index, raw value, population rate and value per reporting unit, with their denominators, 2019–2025 — {v}",
            "caption": (
                "(a) Annual value of each system indexed to the base year stated on the axis (the first year common to "
                "all series, because the REM strict-autism codes start in 2021), on a log scale: indices compare "
                "trajectories, never levels; each legend entry carries the value of the last year of that series. "
                "(b) Raw annual value of each source in its own unit, on a log scale, before any normalisation. "
                "(c) Annual value per 100,000 residents using the INE Censo 2017-base "
                "population at 30 June as a common denominator, and (d) that population denominator year by year. "
                "(e) Value per reporting unit: GRD episodes per hospital "
                "of the observed panel, DEIS discharges per 100,000 discharges, REM A05 entries and REM P2 persons under "
                "control per reporting establishment, and PIE students per 1,000 applicants (the number of schools is not "
                "published in the sources used); (f) the denominators of that panel: reporting GRD hospitals, reporting "
                "REM establishments, total DEIS discharges and PIE applicants. "
                "UNITS DIFFER: episodes, discharges, entries, persons under control and "
                "students are not interchangeable; the panels have separate axes and the sources are NOT "
                "person-linked, so no comparison can be read as a cascade or an individual probability. Source: "
                "outputs/tidy/models_convergence_index.csv, grd_year_summary.csv, deis_year_summary.csv, "
                "rem_pathway_annual.csv, pie_series.csv and ine_population_region_national_year_age_sex.csv. " + g)}
        C_[FIG_NAMES["E26b"]] = {
            "title": f"Figure E26b. Male-to-female ratio of administrative autism recognition in every source that reports sex, 2019–2025 — {v}",
            "caption": (
                "(a) Trend of the male-to-female ratio by source (log scale): GRD episodes with documented F84 and with "
                "principal F84, DEIS discharges with principal F84, REM A05 autism entries, the December stock of REM P2 "
                "and of REM P6 in primary and specialty care, JUNAEB weighted percentages by level, the 2023 PIE sex "
                "split and the ENDIDE 2022 and ENCAVI 2023–2024 estimates; bands show the 95% CI of the three main "
                "series. (b) Ratio by five-year age group and source in the latest available year of each; cells with "
                "fewer than five events in either sex are suppressed and marked '<5'. (c) Ratio of counts versus ratio of "
                "age-standardised rates for GRD and REM A05, with the identity diagonal: standardisation removes the age "
                "composition, which is why the two measures differ. (d) Forest of the latest available year in each "
                "source, with the unit of each point (episodes, persons, discharges, entries, persons under control, "
                "students or respondents) and its interval. (e) The same ratio computed in the two case-definition "
                "variants. (f) The sex-specific numerators behind each ratio, on a log scale, with the unit of each "
                "source next to the bar; the interval method of each source is in the companion table. "
                "Intervals: exact Clopper–Pearson binomial for ratios of counts, log-normal for ratios "
                "of standardised rates, and the delta method on the log scale with complex-design standard errors "
                "(surveys and JUNAEB 2024–2025) or binomial ones (JUNAEB 2023) for ratios of proportions. The 3:1 and 4:1 "
                "lines are clinical-literature references, not an expected value for these registries. SOURCES ARE NOT "
                "PERSON-LINKED and measure different things, so the ratios are not comparable as if they measured the "
                "same thing; GRD unique persons within year are reported as 'not estimable' because the source does not "
                "publish their sex. Source: outputs/tidy/grd_age_sex_year.csv, models_population_rates.csv, "
                "deis_age_sex_year.csv, rem_a05_age_sex_annual.csv, models_a05_standardised_rates.csv, "
                "rem_pathway_tidy.csv, pie_series.csv, junaeb_tea_year_level.csv and survey_estimates.csv. " + g)}
        C_[FIG_NAMES["E27"]] = {
            "title": f"Figure E27. Quasi-Poisson model diagnostics and sensitivity across specifications — {v}",
            "caption": (
                "(a) Fitted versus observed count of the main specification of each estimand, on a log scale, with the "
                "identity diagonal; colour identifies the estimand and the names are labelled in panels c, e and f. "
                "(b) Pearson residuals by year, with ±2 references; 2020–2021 are shaded as a "
                "reporting disruption. (c) Dispersion (Pearson χ² / df) of every specification by estimand, with the "
                "median marked and the dispersion = 1 reference: overdispersion is what motivates quasi-Poisson standard "
                "errors. (d) Sensitivity forest with the annual percent change and 95% CI of every specification of the "
                "main estimands; the main specifications are drawn at full opacity. (e) Durbin–Watson of every "
                "specification; with fewer than eight annual points it is indicative and not conclusive. (f) Annual "
                "percent change of the main specification by estimand, with 95% CI and dispersion; the fitted period of "
                "each estimand is in the companion table. Unit and denominator: "
                "those of the estimand itself (GRD episodes of the same panel, INE 2017-base population, reporting "
                "establishments or none). No specification estimates an effect of Law 21.545 and none constitutes a "
                "causal interrupted time series. Source: outputs/tidy/models_summary.csv and models_fitted.csv. " + g)}
        C_[FIG_NAMES["E28"]] = {
            "title": "Figure E28. Sensitivity of every series to the case-definition variant: full F84 (with Rett syndrome) versus F84 without Rett, 2019–2025",
            "caption": (
                "(a) GRD episodes with documented F84 in any position and with principal F84, observed panel. (b) REM A05 "
                "entries for the pervasive developmental disorder family, 2021–2025. (c) REM P6 population under control "
                "in December, in primary and specialty care. (d) DEIS discharges with principal F84. In all four panels "
                "the annotation above each pair gives the number of cases contributed by Rett syndrome. (e) Absolute "
                "difference con_rett − sin_rett by series and year. (f) Relative difference, with the without-Rett value "
                "as denominator. The education, survey, A03/A27/A28, P2 and strict-autism series are identical in both "
                "variants and appear with a zero difference. Unit: that of each series (episodes, discharges, entries, "
                "persons under control or students). Source: outputs/tidy/grd_year_summary.csv, deis_year_summary.csv, "
                "rem_pathway_annual.csv and pie_series.csv. " + g)}
    return C_


# ===========================================================================
# Controles de reproducción
# ===========================================================================
class Controls:
    """name,key,expected,observed,abs_diff,rel_diff,status,note (mismo formato que el resto del pipeline)."""

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, name, key, expected, observed, note="", tol=0.0, status=None):
        abs_diff = rel_diff = ""
        if status is None:
            try:
                e, o = float(expected), float(observed)
                abs_diff = o - e
                rel_diff = (o - e) / e if e else ""
                status = "ok" if abs(abs_diff) <= tol + 1e-9 else "differs"
            except (TypeError, ValueError):
                status = "ok" if str(expected) == str(observed) else "differs"
        self.rows.append(dict(name=name, key=str(key), expected=expected, observed=observed, abs_diff=abs_diff,
                              rel_diff=rel_diff, status=status, note=note))

    def info(self, name, key, observed, note=""):
        self.rows.append(dict(name=name, key=str(key), expected="", observed=observed, abs_diff="", rel_diff="",
                              status="info", note=note))

    def frame(self):
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff",
                                                "status", "note"])


def build_controls(D, PREP: dict) -> pd.DataFrame:
    K = Controls()
    ref = "con_rett" if "con_rett" in PREP else sorted(PREP)[0]
    p20, p21, p22 = PREP[ref]["E20"], PREP[ref]["E21"], PREP[ref]["E22"]
    natl = p20["national"].set_index("year")
    for y, exp in CFG.CONTROLS["ine_population_national"].items():
        K.add("ine_population_national", y, exp, int(natl.at[y, "population"]) if y in natl.index else np.nan,
              "INE base Censo 2017, 30 de junio; agregado de este módulo frente a config.CONTROLS")
    cov = p21["coverage"]
    for key, col in (("fonasa_beneficiaries_december", "fonasa_beneficiaries_dec"),
                     ("aps_enrolled_december", "aps_enrolled_dec"), ("aps_centres", "aps_centres"),
                     ("isapre_beneficiaries_december", "isapre_beneficiaries_dec")):
        for y, exp in CFG.CONTROLS[key].items():
            K.add(key, y, exp, int(cov.at[y, col]) if y in cov.index else np.nan,
                  "stock de diciembre; coverage_layers_year.csv frente a config.CONTROLS")
    tramo_sum = p21["tramo"].sum(axis=1)
    for y in tramo_sum.index:
        K.add("fonasa_tramo_sum_equals_total", y, int(cov.at[y, "fonasa_beneficiaries_dec"]) if y in cov.index else np.nan,
              int(tramo_sum.at[y]), "suma de los tramos A–D frente al total FONASA de diciembre del mismo año")
    fas = p21["fonasa_age_sex"].groupby("year").beneficiaries.sum()
    fexc = p21["fonasa_excluded"].set_index("year")["outside_sex_age_grid"]
    for y in fas.index:
        if y not in cov.index:
            continue
        used = int(fas.at[y])
        outside = int(fexc.get(y, 0))
        K.add("fonasa_grid_plus_excluded_equals_total", y, int(cov.at[y, "fonasa_beneficiaries_dec"]), used + outside,
              "celdas sexo × banda quinquenal usadas en la lámina E21B más las excluidas (sexo indeterminado, edad sin "
              "información y el archivo de 2023, que publica solo bandas decenales) frente al total nacional de "
              "diciembre; las filas repetidas de FONASA son aditivas y no se eliminan")
        K.info("fonasa_outside_sex_age_grid", y, outside,
               "beneficiarios fuera de la rejilla sexo × banda quinquenal; se informan y nunca se reparten ni se imputan")
    panel = p22["panel"]
    for y, exp in CFG.CONTROLS["rem20_panel_188_retention"].items():
        K.add("rem20_panel_188_retention", y, exp, float(panel.at[y, "retention_discharges"]) if y in panel.index else np.nan,
              "retención de egresos del panel de 188 establecimientos", tol=5e-4)
    for y, exp in CFG.CONTROLS["aps_panel_1871_retention"].items():
        ap = p21["aps_panel"]
        K.add("aps_panel_1871_retention", y, exp, float(ap.at[y, "retention_panel_1871"]) if y in ap.index else np.nan,
              "retención de inscritos del panel de 1.871 centros APS", tol=5e-4)
    # --- GRD, REM y educación: los agregados de este módulo frente a las tablas tidy verificadas ---
    grd = D.grd[(D.grd.variant == ref) & (D.grd.panel == "observed") & (D.grd.activity == "all") &
                (D.grd.position == "any")].set_index("year")
    grd_key = "grd_f84_any" if ref == "con_rett" else "grd_f84_any"
    for y, exp in CFG.CONTROLS[grd_key].items():
        K.add("grd_f84_any", y, exp, int(grd.at[y, "n_episodes_f84"]) if y in grd.index else np.nan,
              f"grd_year_summary.csv (variante {ref}, panel observado, toda actividad, cualquier posición) frente a "
              "config.CONTROLS (valores de la familia F84 completa)")
    gs = D.grd_as[(D.grd_as.variant == ref) & (D.grd_as.panel == "observed") &
                  (D.grd_as.activity == "all") & (D.grd_as.position == "any")]
    for y in sorted(gs.year.unique()):
        K.add("grd_age_sex_sum_equals_year_total", y, int(grd.at[y, "n_episodes_f84"]) if y in grd.index else np.nan,
              int(gs[gs.year == y].n_f84.sum()),
              "suma de grd_age_sex_year (incluye sexo y edad desconocidos) frente al total anual de grd_year_summary")
    rem = D.rem
    a05 = rem[(rem.module == "A05") & (rem.variant == "strict_autism") &
              rem.indicator.str.contains("ingresos", case=False, na=False)].set_index("year")
    for y, exp in CFG.CONTROLS["a05_autism_entries"].items():
        K.add("a05_autism_entries", y, exp, int(a05.at[y, "total"]) if y in a05.index else np.nan,
              "rem_pathway_annual.csv (A05 autismo estricto, ingresos) frente a config.CONTROLS")
    p2 = rem[(rem.code == CFG.P2_TEA) & (rem.measure == "december_stock")].set_index("year")
    for y, exp in CFG.CONTROLS["p2_tea_december"].items():
        K.add("p2_tea_december", y, exp, int(p2.at[y, "total"]) if y in p2.index else np.nan,
              "rem_pathway_annual.csv (P2 TEA, stock de diciembre) frente a config.CONTROLS")
    for y, exp in CFG.CONTROLS["p2_establishments_december"].items():
        K.add("p2_establishments_december", y, exp,
              int(p2.at[y, "n_reporting_establishments"]) if y in p2.index else np.nan,
              "establecimientos que reportan P2 en diciembre")
    # P2 y P6 por sexo (COL02 + COL03) frente al total (COL01) de la misma fila
    for label, codes in (("p2_sex_sum_equals_total", [CFG.P2_TEA]),
                         ("p6_primary_sex_sum_equals_total", CFG.VARIANTS[ref]["p6_primary"]),
                         ("p6_specialty_sex_sum_equals_total", CFG.VARIANTS[ref]["p6_specialty"])):
        st = _rem_sex_stock(D.rem_tidy, codes, 12)
        for _, r in st.iterrows():
            K.add(label, int(r.year), float(r.total), float(r.males) + float(r.females),
                  "COL02 (Hombres) + COL03 (Mujeres) frente a COL01 (Ambos sexos) del diccionario REM", tol=0.0)
    a05_as = D.a05_as[(D.a05_as.age_group == "total") & (D.a05_as.flow == "entry") & (D.a05_as.code == "05990022")]
    for y in sorted(a05_as.year.unique()):
        K.add("a05_sex_sum_equals_annual_total", y, int(a05.at[y, "total"]) if y in a05.index else np.nan,
              int(a05_as[a05_as.year == y]["count"].sum()),
              "rem_a05_age_sex_annual (COL02 Hombres + COL03 Mujeres) frente a rem_pathway_annual (COL01, autismo "
              "estricto, ingresos). Una diferencia de una unidad en 2025 corresponde a la fila establecimiento × mes "
              "con COL01 vacío y las celdas de sexo informadas (n_rows_empty = 1 en rem_pathway_annual): cero, ausente "
              "y «no reportado» se mantienen como estados distintos y la celda no se imputa")
    pie = PREP[ref]["E24"]["pie"]
    for key, col in (("pie_tea_strict", "pie_tea_strict"), ("pie_tea_asperger", "pie_tea_asperger"),
                     ("pie_harmonised", "pie_harmonised"), ("pie_special_schools", "special_schools_autism")):
        for y, exp in CFG.CONTROLS[key].items():
            K.add(key, y, exp, float(pie.at[y, col]) if (y in pie.index and col in pie.columns) else np.nan,
                  "pie_series.csv frente a config.CONTROLS")
    junaeb = PREP[ref]["E25"]["junaeb"]
    for year, expected in (("2024", CFG.CONTROLS["junaeb_unweighted_2024"]),
                           ("2025", CFG.CONTROLS["junaeb_unweighted_2025"])):
        for lvl, exp in expected.items():
            sub = junaeb[(junaeb.year == int(year)) & (junaeb.level == lvl) & (junaeb.sex == "all")]
            K.add(f"junaeb_unweighted_{year}", lvl, exp,
                  int(sub.n_tea_unweighted.iloc[0]) if len(sub) and pd.notna(sub.n_tea_unweighted.iloc[0]) else np.nan,
                  "casos TEA no ponderados de junaeb_tea_year_level.csv frente a config.CONTROLS")
    sv = D.surveys
    end_ad = sv[(sv.domain == "ENDIDE adultos 18+: autismo reportado") & (sv.subgroup_type == "total")]
    end_nna = sv[(sv.domain == "ENDIDE NNA 2-17: autismo reportado") & (sv.subgroup_type == "total")]
    end_cf = sv[(sv.domain == "ENDIDE NNA con autismo reportado: confirmado por un médico") & (sv.subgroup_type == "total")]
    K.add("endide_unweighted", "adults", CFG.CONTROLS["endide_unweighted"]["adults"],
          int(end_ad.cases.iloc[0]) if len(end_ad) else np.nan, "survey_estimates.csv frente a config.CONTROLS")
    K.add("endide_unweighted", "children", CFG.CONTROLS["endide_unweighted"]["children"],
          int(end_nna.cases.iloc[0]) if len(end_nna) else np.nan, "survey_estimates.csv frente a config.CONTROLS")
    K.add("endide_unweighted", "children_confirmed", CFG.CONTROLS["endide_unweighted"]["children_confirmed"],
          int(end_cf.cases.iloc[0]) if len(end_cf) else np.nan, "survey_estimates.csv frente a config.CONTROLS")
    enc = sv[(sv.domain == "ENCAVI 15+: diagnóstico de trastorno del espectro autista") & (sv.subgroup_type == "total")]
    K.add("encavi_unweighted", "positive", CFG.CONTROLS["encavi_unweighted"]["positive"],
          int(enc.cases.iloc[0]) if len(enc) else np.nan, "survey_estimates.csv frente a config.CONTROLS")
    # --- coherencia interna de las láminas E26 y E26b ---------------------------------------------
    for variant in PREP:
        t26 = PREP[variant]["E26"]["table"]
        gsel = D.grd[(D.grd.variant == variant) & (D.grd.panel == "observed") & (D.grd.activity == "all") &
                     (D.grd.position == "any")].set_index("year")
        for y in sorted(t26[t26.system == "grd"].year.unique()):
            K.add(f"e26_grd_value_{variant}", y, int(gsel.at[y, "n_episodes_f84"]),
                  int(t26[(t26.system == "grd") & (t26.year == y)].value.iloc[0]),
                  "valor de la lámina E26 frente a grd_year_summary.csv")
        tr26b = PREP[variant]["E26b"]["trend"]
        gsx = D.grd_as[(D.grd_as.variant == variant) & (D.grd_as.panel == "observed") &
                       (D.grd_as.activity == "all") & (D.grd_as.position == "any")]
        for y in sorted(tr26b[tr26b.source == "grd_any"].year.unique()):
            got = tr26b[(tr26b.source == "grd_any") & (tr26b.year == y)]
            K.add(f"e26b_grd_sex_sum_{variant}", y, int(gsx[gsx.year == y].n_f84.sum()),
                  int(float(got.males.iloc[0]) + float(got.females.iloc[0])
                      + int(gsx[(gsx.year == y) & (gsx.sex == "unknown")].n_f84.sum())),
                  "hombres + mujeres + sexo desconocido de la lámina E26b frente al total de grd_age_sex_year")
        t28 = PREP[variant]["E28"]["table"]
        neg = t28[t28.abs_diff < 0]
        K.add("e28_con_rett_never_below_sin_rett", variant, 0, int(len(neg)),
              "el número de casos con Rett nunca puede ser menor que el número sin Rett en ninguna serie ni año")
    ratios = PREP[ref]["E26b"]["trend"]
    K.add("e26b_all_ratios_have_ci", "n_missing_ci", 0,
          int(((ratios.ratio.notna()) & (ratios.lo.isna() | ratios.hi.isna())).sum()),
          "toda razón estimada debe llevar un intervalo de 95 %")
    K.info("e26b_sources", "n_sources", int(ratios.source.nunique()),
           "fuentes distintas con razón hombre:mujer en la lámina E26b (incluye las marcadas «no estimable»)")
    K.info("e26b_not_estimable", "sources",
           "; ".join(sorted(set(ratios.loc[ratios.method == "not_estimable", "source"]))) or "—",
           "series cuya razón por sexo no es estimable porque la fuente no publica el sexo")
    imprecise = D.surveys[(D.surveys.precision_flag != "adequate") | (D.surveys.cases < 30)]
    K.info("survey_flagged_domains", "n", int(len(imprecise)),
           "dominios de encuesta con menos de 30 casos o EER > 30 %: se marcan y no se presentan como fiables")
    return K.frame()


# ===========================================================================
# main
# ===========================================================================
FIG_BUILDERS = {"E20": fig_e20, "E21": fig_e21, "E22": fig_e22, "E23": fig_e23, "E24": fig_e24,
                "E25": fig_e25, "E26": fig_e26, "E26b": fig_e26b, "E27": fig_e27, "E28": fig_e28}


def prepare(D, variant: str) -> dict:
    return {"E20": prep_e20(D), "E21": prep_e21(D), "E22": prep_e22(D, variant), "E23": prep_e23(D),
            "E24": prep_e24(D), "E25": prep_e25(D), "E26": prep_e26(D, variant), "E26b": prep_e26b(D, variant),
            "E27": prep_e27(D, variant), "E28": prep_e28(D)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=VARIANTS, choices=VARIANTS)
    ap.add_argument("--langs", nargs="+", default=LANGS, choices=LANGS)
    ap.add_argument("--only", nargs="+", default=PLATES, choices=PLATES,
                    help="láminas a construir (por defecto todas)")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--no-tables", action="store_true")
    args = ap.parse_args()

    t_start = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    log("cargando tablas tidy verificadas (solo lectura)")
    D = load()

    prep_seconds = {}
    PREP = {}
    for variant in args.variants:
        t0 = time.perf_counter()
        PREP[variant] = prepare(D, variant)
        prep_seconds[variant] = round(time.perf_counter() - t0, 1)
        log(f"datos preparados para {variant} ({prep_seconds[variant]} s)")

    outputs: list[str] = []
    seconds = {}
    for variant in args.variants:
        for lang in args.langs:
            t0 = time.perf_counter()
            fdir, tdir = out_dir(variant, lang, "figures"), out_dir(variant, lang, "tables")
            caps = captions(PREP[variant], variant, lang)
            made = {}
            if not args.no_figures:
                for key in args.only:
                    p = FIG_BUILDERS[key](PREP[variant][key], lang, fdir)
                    outputs.append(str(p))
                    made[key] = str(p)
                merge_json(fdir / "captions.json", C.strip_caption_paths({k: v for k, v in caps.items()
                                                                          if k in {FIG_NAMES[x] for x in args.only}}))
                outputs.append(str(fdir / "captions.json"))
            if not args.no_tables:
                titles = build_tables(PREP[variant], variant, lang, tdir)
                keep = {TABLE_NAMES[x] for x in args.only}
                titles = {k: v for k, v in titles.items() if k in keep}
                for name in titles:
                    outputs.append(str(tdir / f"{name}.csv"))
                    outputs.append(str(tdir / f"{name}_numeric.csv"))
                merge_json(tdir / "titles.json", titles)
                outputs.append(str(tdir / "titles.json"))
            seconds[f"{variant}/{lang}"] = round(time.perf_counter() - t0, 1)
            log(f"{variant}/{lang}: {len(made)} láminas y "
                f"{0 if args.no_tables else len(args.only)} tablas en {seconds[f'{variant}/{lang}']} s")

    controls = build_controls(D, PREP)
    ctl_path = C.atomic_write_csv(controls, CONTROLS_DIR / f"{MODULE}_controls.csv")
    outputs.append(str(ctl_path))
    status_counts = controls.status.value_counts().to_dict()
    differs = controls[controls.status == "differs"]
    if len(differs):
        log(f"{len(differs)} controles con diferencia:")
        print(differs[["name", "key", "expected", "observed", "abs_diff", "note"]]
              .to_string(index=False, max_colwidth=70), flush=True)

    runtime = round(time.perf_counter() - t_start, 1)
    runlog = dict(module=MODULE, script=SCRIPT, started_utc=started, runtime_seconds=runtime, args=vars(args),
                  variants=args.variants, languages=args.langs, plates=args.only,
                  figures={k: FIG_NAMES[k] for k in args.only}, tables={k: TABLE_NAMES[k] for k in args.only},
                  seconds_prepare=prep_seconds, seconds_by_variant_lang=seconds,
                  n_outputs=len(outputs), outputs=outputs, controls_status=status_counts,
                  warnings=sorted(set(WARNINGS)), inputs=TIDY_INPUTS + ["rem_pathway_tidy", "values_<variant>.json"])
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    log(f"listo en {runtime:,.1f} s; {len(outputs)} salidas; controles: {status_counts}; "
        f"avisos: {len(set(WARNINGS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
