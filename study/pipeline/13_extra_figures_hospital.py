#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""13_extra_figures_hospital.py — láminas adicionales del núcleo hospitalario (serie E) y sus tablas acompañantes,
por variante (`con_rett`, `sin_rett`) e idioma (`es`, `en`), para la parte suplementaria del manuscrito.

Lee solo tablas tidy ya verificadas (`outputs/tidy/`) escritas por los módulos 01, 01b, 02, 03 y 11; nunca vuelve a
leer microdatos ni modifica otro módulo. Escribe:

  outputs/<variante>/<idioma>/extra/figures/EF1..EF10_*.png     diez láminas 2×3 (600 ppp, Okabe–Ito, letras de panel)
  outputs/<variante>/<idioma>/extra/figures/captions.json       {nombre: {title, caption}} (fusionado con lo existente)
  outputs/<variante>/<idioma>/extra/tables/EF1..EF10_*.csv      tabla acompañante formateada por idioma
  outputs/<variante>/<idioma>/extra/tables/EF*_numeric.csv      la misma tabla en valores numéricos crudos
  outputs/<variante>/<idioma>/extra/tables/titles.json          {nombre: {title, note}} (fusionado con lo existente)
  outputs/controls/13_extra_figures_hospital_controls.csv       name,key,expected,observed,abs_diff,rel_diff,status,note
  outputs/controls/13_extra_figures_hospital_runlog.json        tiempos, entradas, salidas y avisos

Láminas (cada una con su tabla acompañante del mismo nombre):
  EF1  estacionalidad y serie mensual        (grd_monthly; A05 mensual de rem_pathway_tidy como comparación separada)
  EF2  estadía hospitalaria                  (grd_length_of_stay, grd_los_age, grd_episode_features/los_bin)
  EF3  características del episodio          (grd_episode_features: ingreso, actividad, procedencia, alta, previsión, especialidad)
  EF4  gravedad, riesgo de muerte y peso GRD (grd_episode_features IR-29301, grd_grd_weight, letalidad con IC de Jeffreys)
  EF5  co-diagnósticos                       (grd_codiagnoses, grd_codiagnosis_chapters, grd_year_summary)
  EF6  reingresos y multiplicidad            (grd_readmission, grd_multiplicity, grd_year_summary)
  EF7  detalle de edad                       (grd_age_single_year, grd_age_sex_year, ine_population_region_national_year_age_sex)
  EF8  hospitales                            (grd_hospital_year, grd_fixed_panel_hospitals)
  EF9  territorio                            (grd_territory, ine_population_comuna/región, data/comunas.shp si hay geopandas)
  EF10 detalle DEIS                          (deis_year_summary, deis_establishment_year, deis_age_sex_year, deis_f84_subcode_year, deis_vs_grd_year)

Reglas no negociables respetadas en todas las láminas, tablas y notas:
  * los recuentos son reconocimiento administrativo, nunca prevalencia ni incidencia;
  * el resultado GRD es «episodios con F84 documentado» y F84 principal es una serie separada;
  * las fuentes no están enlazadas por persona: no hay cascada ni cocientes entre fuentes no enlazadas;
  * la Ley 21.545 (marzo de 2023) es contexto de política, nunca un efecto causal;
  * stocks y flujos nunca comparten eje; GRD, DEIS y REM tampoco, salvo la única serie homologable entre DEIS y
    GRD (F84 principal, lámina EF10 panel e), donde cada serie usa su propio denominador y no se calcula ningún
    cociente entre fuentes;
  * lugar de atención (hospital GRD, establecimiento REM) y residencia (INE, comuna de residencia GRD) solo se combinan
    con nota explícita (láminas EF7 y EF9);
  * panel hospitalario fijo de 65 y panel observado 65-65-65-65-68-72;
  * las personas se cuentan solo dentro del año o de la era de identificador (el formato cambia entre 2020 y 2021);
  * las eras de definición REM nunca se unen con una línea;
  * cero, ausente y «no reportado» se mantienen distintos («n/e» cuando no es estimable);
  * en las tablas territoriales se suprimen las celdas con menos de 5 eventos.

Uso:
    python3 study/pipeline/13_extra_figures_hospital.py
    python3 study/pipeline/13_extra_figures_hospital.py --variants con_rett --langs es --only EF1 EF9
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy import stats

STUDY_DIR = Path(__file__).resolve().parents[1]
if str(STUDY_DIR) not in sys.path:
    sys.path.insert(0, str(STUDY_DIR))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
import labels as LB  # noqa: E402  (diccionario único CIE-10 y glosas bilingües compartidas)

MODULE = "13_extra_figures_hospital"
SCRIPT = "study/pipeline/13_extra_figures_hospital.py"
VARIANTS = ["con_rett", "sin_rett"]
LANGS = list(CFG.LANGUAGES)
YEARS = list(CFG.YEARS_GRD)                 # 2019–2024
PANDEMIC = list(CFG.PANDEMIC_YEARS)         # 2020–2021
LAW_X = CFG.LAW_YEAR + 2.5 / 12 - 0.5       # marzo de 2023 sobre un eje de años centrados
PER = 100_000.0
OKABE = C.OKABE
SUPPRESS_MIN = 5                            # celdas territoriales con menos de 5 eventos: suprimidas
WARNINGS: list[str] = []
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

COL = {"any": OKABE[0], "principal": OKABE[1], "secondary_only": OKABE[4], "all": "#7f8c8d",
       "hosp": OKABE[2], "cma": OKABE[3], "male": OKABE[0], "female": OKABE[1], "grey": "#7f8c8d",
       "f84": OKABE[0], "rem": OKABE[2], "deis": OKABE[3], "fixed": OKABE[0], "new": OKABE[1],
       "y2019": OKABE[5], "y2024": OKABE[1], "snss": OKABE[0], "no_snss": OKABE[1]}
YEAR_COLORS = [OKABE[5], OKABE[0], OKABE[2], OKABE[6], OKABE[4], OKABE[1]]   # 2019 … 2024


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    log(f"AVISO: {msg}")


# ===========================================================================
# Rótulos bilingües (ninguna cadena visible se escribe suelta en el código)
# ===========================================================================
LBL: dict[str, dict[str, str]] = {
    "year": {"es": "Año", "en": "Year"},
    "month": {"es": "Mes de ingreso", "en": "Month of admission"},
    "months_short": {"es": "E|F|M|A|M|J|J|A|S|O|N|D", "en": "J|F|M|A|M|J|J|A|S|O|N|D"},
    "episodes": {"es": "Episodios", "en": "Episodes"},
    "episodes_f84": {"es": "Episodios con F84 documentado", "en": "Episodes with documented F84"},
    "all_episodes": {"es": "Todos los episodios GRD", "en": "All GRD episodes"},
    "rate_100k_ep": {"es": "Por 100.000 episodios GRD", "en": "Per 100,000 GRD episodes"},
    "rate_100k_pop": {"es": "Por 100.000 habitantes", "en": "Per 100,000 population"},
    "rate_100k_disch": {"es": "Por 100.000 egresos", "en": "Per 100,000 discharges"},
    "pct_episodes": {"es": "% de los episodios", "en": "% of episodes"},
    "pct_f84": {"es": "% de los episodios con F84", "en": "% of episodes with F84"},
    "pp_diff": {"es": "Diferencia (F84 − todos), puntos porcentuales", "en": "Difference (F84 − all), percentage points"},
    "position": {"es": "Posición de F84", "en": "F84 position"},
    "pos_any": {"es": "Cualquier posición", "en": "Any position"},
    "pos_principal": {"es": "F84 principal", "en": "Principal F84"},
    "pos_secondary_only": {"es": "Solo secundario", "en": "Secondary only"},
    "pos_all": {"es": "Todos los episodios GRD", "en": "All GRD episodes"},
    "act_all": {"es": "Todas las actividades", "en": "All activities"},
    "act_hosp": {"es": "Hospitalización", "en": "Hospitalisation"},
    "act_cma": {"es": "Cirugía mayor ambulatoria", "en": "Major ambulatory surgery"},
    "act_other": {"es": "Otras modalidades (solo 2019)", "en": "Other modalities (2019 only)"},
    "panel_observed": {"es": "Panel observado", "en": "Observed panel"},
    "panel_fixed": {"es": "Panel fijo de 65 hospitales", "en": "Fixed panel of 65 hospitals"},
    "pandemic": {"es": "Disrupción del\nreporte 2020–21", "en": "Reporting\ndisruption 2020–21"},
    "law": {"es": "Ley 21.545\n(marzo 2023, contexto)", "en": "Law 21.545\n(March 2023, context)"},
    # En una celda de 90 mm la glosa completa de la ley se sale del panel; la marca lleva la versión breve y el pie
    # de cada lámina conserva la frase entera («línea punteada: Ley 21.545 (marzo de 2023) como contexto»).
    "law_short": {"es": "Ley 21.545\n(2023)", "en": "Law 21.545\n(2023)"},
    "ci95": {"es": "IC 95 %", "en": "95% CI"},
    "male": {"es": "Hombres", "en": "Males"},
    "female": {"es": "Mujeres", "en": "Females"},
    "sex_unknown": {"es": "Sexo no informado", "en": "Sex not reported"},
    "not_estimable": {"es": "n/e", "en": "n/e"},
    "not_reported": {"es": "no informado", "en": "not reported"},
    "suppressed": {"es": "suprimido (< 5)", "en": "suppressed (< 5)"},
    "days": {"es": "Días", "en": "Days"},
    "median_iqr": {"es": "Mediana (P25–P75)", "en": "Median (P25–P75)"},
    "total": {"es": "Total", "en": "Total"},
    "unknown_month": {"es": "Fecha de ingreso no analizable", "en": "Unparsable admission date"},
    "n_hospitals": {"es": "Hospitales", "en": "Hospitals"},
    "region": {"es": "Región de residencia", "en": "Region of residence"},
    "age_years": {"es": "Edad (años cumplidos)", "en": "Age (completed years)"},
    "age_group": {"es": "Grupo etario", "en": "Age group"},
    "variant_prefix": {"es": "Definición", "en": "Definition"},
    # --- EF1 -------------------------------------------------------------------------------------
    "ef1_title": {"es": "Estacionalidad y serie mensual de los episodios GRD con F84 documentado",
                  "en": "Seasonality and monthly series of GRD episodes with documented F84"},
    "ef1_a": {"es": "Episodios con F84 por mes de ingreso y año", "en": "Episodes with F84 by month of admission and year"},
    "ef1_b": {"es": "Tasa mensual por 100.000 episodios GRD del mismo mes", "en": "Monthly rate per 100,000 GRD episodes of the same month"},
    "ef1_c": {"es": "Índice estacional dentro del año (media del año = 1)", "en": "Within-year seasonal index (year mean = 1)"},
    "ef1_d": {"es": "Disrupción 2020–2021: mes frente al mismo mes de 2019", "en": "2020–2021 disruption: month versus same month of 2019"},
    "ef1_e": {"es": "Comparación REM A05: ingresos mensuales por autismo (2021–2025)",
              "en": "REM A05 comparison: monthly autism programme entries (2021–2025)"},
    "ef1_f": {"es": "Índice de dispersión de los recuentos mensuales", "en": "Index of dispersion of the monthly counts"},
    "ef1_ratio": {"es": "Cociente frente a 2019 (mismo mes)", "en": "Ratio to 2019 (same month)"},
    "ef1_disp": {"es": "Varianza / media de los 12 meses", "en": "Variance / mean of the 12 months"},
    "ef1_poisson": {"es": "Poisson (= 1)", "en": "Poisson (= 1)"},
    "ef1_a05": {"es": "Ingresos A05 autismo (05990022)", "en": "A05 autism entries (05990022)"},
    "ef1_a05_axis": {"es": "Ingresos REM A05 (mes)", "en": "REM A05 entries (month)"},
    "ef1_sep_axis": {"es": "Fuente distinta y eje propio: REM no es GRD", "en": "Different source, own axis: REM is not GRD"},
    # --- EF2 -------------------------------------------------------------------------------------
    "ef2_title": {"es": "Estadía hospitalaria de los episodios con F84 documentado",
                  "en": "Length of stay of episodes with documented F84"},
    "ef2_a": {"es": "Mediana y P25–P75 por año y posición (hospitalización)", "en": "Median and P25–P75 by year and position (hospitalisation)"},
    "ef2_b": {"es": "Estadía por grupo etario: media acumulada 2019–2024 y mediana de 2024",
              "en": "Stay by age group: pooled 2019–2024 mean and 2024 median"},
    "ef2_c": {"es": "Percentil 90 de la estadía por año", "en": "90th percentile of stay by year"},
    "ef2_d": {"es": "Episodios con estadía cero (%)", "en": "Episodes with zero-day stay (%)"},
    "ef2_e": {"es": "Distribución por tramos de estadía, 2024", "en": "Distribution by stay bands, 2024"},
    "ef2_f": {"es": "Hospitalización frente a cirugía mayor ambulatoria", "en": "Hospitalisation versus major ambulatory surgery"},
    "ef2_los_bin": {"es": "Tramo de estadía (días)", "en": "Stay band (days)"},
    "ef2_zero": {"es": "% de episodios con estadía cero", "en": "% of episodes with zero-day stay"},
    "ef2_p90": {"es": "P90 de la estadía (días)", "en": "P90 of stay (days)"},
    "ef2_median_days": {"es": "Mediana de días (línea)", "en": "Median days (line)"},
    # --- EF3 -------------------------------------------------------------------------------------
    "ef3_title": {"es": "Características administrativas del episodio: F84 documentado frente a todos los episodios GRD",
                  "en": "Administrative characteristics of the episode: documented F84 versus all GRD episodes"},
    "ef3_a": {"es": "Tipo de ingreso", "en": "Type of admission"},
    "ef3_b": {"es": "Tipo de actividad", "en": "Type of activity"},
    "ef3_c": {"es": "Procedencia", "en": "Provenance"},
    "ef3_d": {"es": "Tipo de alta", "en": "Type of discharge"},
    "ef3_e": {"es": "Previsión (tramo)", "en": "Insurance (tramo)"},
    "ef3_f": {"es": "Especialidad médica", "en": "Medical specialty"},
    "ef3_other": {"es": "Otras categorías (agrupadas)", "en": "Other categories (pooled)"},
    # --- EF4 -------------------------------------------------------------------------------------
    "ef4_title": {"es": "Gravedad, riesgo de mortalidad IR-29301, peso GRD y letalidad hospitalaria",
                  "en": "Severity, IR-29301 mortality risk, GRD weight and in-hospital lethality"},
    "ef4_a": {"es": "Gravedad IR-29301 (% de episodios)", "en": "IR-29301 severity (% of episodes)"},
    "ef4_b": {"es": "Riesgo de mortalidad IR-29301 (% de episodios)", "en": "IR-29301 mortality risk (% of episodes)"},
    "ef4_c": {"es": "Peso relativo GRD: mediana y cuartiles por año", "en": "GRD relative weight: median and quartiles by year"},
    "ef4_d": {"es": "Grupos GRD más frecuentes entre los episodios con F84", "en": "Most frequent GRD groups among episodes with F84"},
    "ef4_e": {"es": "Letalidad hospitalaria (alta = fallecido), IC 95 % de Jeffreys",
              "en": "In-hospital lethality (discharge = death), Jeffreys 95% CI"},
    "ef4_f": {"es": "Peso medio por posición y episodios sin peso", "en": "Mean weight by position and episodes without weight"},
    "ef4_sev": {"es": "Gravedad (0 = menor, 3 = extrema)", "en": "Severity (0 = minor, 3 = extreme)"},
    "ef4_mor": {"es": "Riesgo de mortalidad (0 = menor, 3 = extremo)", "en": "Mortality risk (0 = minor, 3 = extreme)"},
    "ef4_weight": {"es": "Peso relativo IR-29301", "en": "IR-29301 relative weight"},
    "ef4_leth": {"es": "Letalidad (%)", "en": "Lethality (%)"},
    "ef4_nowt": {"es": "Episodios sin peso (%)", "en": "Episodes without weight (%)"},
    "ef4_grd_group": {"es": "Grupo GRD IR-29301", "en": "IR-29301 GRD group"},
    # --- EF5 -------------------------------------------------------------------------------------
    "ef5_title": {"es": "Co-diagnósticos de los episodios con F84 documentado",
                  "en": "Co-diagnoses of episodes with documented F84"},
    "ef5_a": {"es": "10 categorías CIE-10 de tres caracteres más frecuentes, 2019–2024",
              "en": "10 most frequent three-character ICD-10 categories, 2019–2024"},
    "ef5_b": {"es": "Capítulos CIE-10: episodios con mención por 100 episodios con F84",
              "en": "ICD-10 chapters: episodes with a mention per 100 episodes with F84"},
    "ef5_c": {"es": "Bloques de salud mental (F00–F99, sin F84)", "en": "Mental-health blocks (F00–F99, excluding F84)"},
    "ef5_d": {"es": "Diagnóstico principal cuando F84 es solo secundario", "en": "Principal diagnosis when F84 is secondary only"},
    "ef5_e": {"es": "Cambio entre 2019 y 2024 (10 categorías principales)", "en": "Change between 2019 and 2024 (top 10 categories)"},
    "ef5_f": {"es": "Categorías por episodio y profundidad diagnóstica", "en": "Categories per episode and coding depth"},
    "ef5_per100": {"es": "Episodios con ≥ 1 mención por 100 episodios con F84",
                   "en": "Episodes with ≥ 1 mention per 100 episodes with F84"},
    "ef5_cats": {"es": "Categorías CIE-10 distintas por episodio", "en": "Distinct ICD-10 categories per episode"},
    "ef5_depth": {"es": "Diagnósticos codificados por episodio", "en": "Coded diagnoses per episode"},
    # --- EF6 -------------------------------------------------------------------------------------
    "ef6_title": {"es": "Reingresos y multiplicidad de episodios por identificador",
                  "en": "Readmission and multiplicity of episodes per identifier"},
    "ef6_a": {"es": "Reingreso por cualquier causa (IC 95 % de Wilson)", "en": "All-cause readmission (Wilson 95% CI)"},
    "ef6_b": {"es": "Reingreso con F84 documentado (IC 95 % de Wilson)", "en": "Readmission with documented F84 (Wilson 95% CI)"},
    "ef6_c": {"es": "Episodios por identificador dentro de la era", "en": "Episodes per identifier within the era"},
    "ef6_d": {"es": "Personas dentro del año y episodios por persona", "en": "Persons within year and episodes per person"},
    "ef6_e": {"es": "Reingreso a 30 días por posición de F84", "en": "30-day readmission by F84 position"},
    "ef6_f": {"es": "Estados del dato: egresos, elegibles y solapamientos", "en": "Data states: discharges, eligible and overlaps"},
    "ef6_pct": {"es": "% de los egresos elegibles", "en": "% of eligible discharges"},
    "ef6_era": {"es": "Era de identificador", "en": "Identifier era"},
    "ef6_persons": {"es": "Personas dentro del año", "en": "Persons within year"},
    "ef6_epi_person": {"es": "Episodios por persona", "en": "Episodes per person"},
    "ef6_horizon": {"es": "Horizonte", "en": "Horizon"},
    "ef8_other_hosp": {"es": "Resto de los hospitales", "en": "All other hospitals"},
    "ef6_pct_persons": {"es": "% de los identificadores", "en": "% of identifiers"},
    "ef6_eligible": {"es": "Elegibles con horizonte completo", "en": "Eligible with full horizon"},
    "ef6_discharges": {"es": "Egresos índice", "en": "Index discharges"},
    "ef6_overlap": {"es": "Con ingreso siguiente solapado", "en": "With overlapping next admission"},
    # --- EF7 -------------------------------------------------------------------------------------
    "ef7_title": {"es": "Detalle de edad de los episodios con F84 documentado",
                  "en": "Age detail of episodes with documented F84"},
    "ef7_a": {"es": "Edad simple por sexo, 2019 y 2024", "en": "Single-year age by sex, 2019 and 2024"},
    "ef7_b": {"es": "Tasa por 100.000 habitantes según grupo etario y año", "en": "Rate per 100,000 population by age group and year"},
    "ef7_c": {"es": "Razón hombre:mujer por grupo etario", "en": "Male-to-female ratio by age group"},
    "ef7_d": {"es": "Desplazamiento de la distribución de edad, 2019 frente a 2024", "en": "Shift of the age distribution, 2019 versus 2024"},
    "ef7_e": {"es": "Tasa por 100.000 habitantes: grupo etario × año", "en": "Rate per 100,000 population: age group × year"},
    "ef7_f": {"es": "Tasa por edad y sexo, 2024 (IC 95 % exactos)", "en": "Rate by age and sex, 2024 (exact 95% CI)"},
    "ef7_cum": {"es": "% acumulado de episodios", "en": "Cumulative % of episodes"},
    "ef7_ratio": {"es": "Razón hombre:mujer (IC 95 %)", "en": "Male:female ratio (95% CI)"},
    "ef7_place_note": {"es": "Numerador: lugar de atención · Denominador: residencia",
                       "en": "Numerator: place of care · Denominator: residence"},
    # --- EF8 -------------------------------------------------------------------------------------
    "ef8_title": {"es": "Hospitales del panel GRD: tasas, estabilidad del orden y concentración",
                  "en": "GRD panel hospitals: rates, rank stability and concentration"},
    "ef8_a": {"es": "Tasa por 100.000 episodios del hospital (12 hospitales con más episodios con F84 y el resto agregado)",
              "en": "Rate per 100,000 hospital episodes (12 hospitals with most F84 episodes and the rest pooled)"},
    "ef8_b": {"es": "Estabilidad del orden entre años (ρ de Spearman)", "en": "Rank stability across years (Spearman ρ)"},
    "ef8_c": {"es": "Contribución de los 10 hospitales mayores", "en": "Contribution of the 10 largest hospitals"},
    "ef8_d": {"es": "Panel fijo de 65 frente a hospitales incorporados", "en": "Fixed panel of 65 versus hospitals added"},
    "ef8_e": {"es": "Distribución de las tasas por hospital y año", "en": "Distribution of hospital rates by year"},
    "ef8_f": {"es": "Concentración de los episodios con F84 (curva de Lorenz)", "en": "Concentration of episodes with F84 (Lorenz curve)"},
    "ef8_rho": {"es": "ρ de Spearman entre años", "en": "Spearman ρ between years"},
    "ef8_share_top10": {"es": "% de los episodios con F84", "en": "% of episodes with F84"},
    "ef8_cum_hosp": {"es": "% acumulado de hospitales (orden creciente)", "en": "Cumulative % of hospitals (ascending)"},
    "ef8_cum_epi": {"es": "% acumulado de episodios con F84", "en": "Cumulative % of episodes with F84"},
    "ef8_added": {"es": "Hospitales incorporados en 2023–2024", "en": "Hospitals added in 2023–2024"},
    "ef8_hosp_rate": {"es": "Tasa del hospital por 100.000 episodios", "en": "Hospital rate per 100,000 episodes"},
    # --- EF9 -------------------------------------------------------------------------------------
    "ef9_title": {"es": "Territorio: episodios y personas por región y comuna de residencia declarada",
                  "en": "Territory: episodes and persons by reported region and comuna of residence"},
    "ef9_a": {"es": "Episodios por 100.000 residentes: región × año", "en": "Episodes per 100,000 residents: region × year"},
    "ef9_b": {"es": "Tendencia regional, 2019–2024", "en": "Regional trend, 2019–2024"},
    "ef9_c": {"es": "Personas dentro del año frente a episodios, 2024", "en": "Persons within year versus episodes, 2024"},
    "ef9_d": {"es": "Razón observada/esperada suavizada por comuna, 2019–2024", "en": "Smoothed observed/expected ratio by comuna, 2019–2024"},
    "ef9_e": {"es": "Episodios sin comuna enlazable", "en": "Episodes without a linkable comuna"},
    "ef9_f": {"es": "Tasa regional 2019 frente a 2024", "en": "Regional rate 2019 versus 2024"},
    "ef9_sir": {"es": "Razón O/E suavizada (Bayes empírico)", "en": "Smoothed O/E ratio (empirical Bayes)"},
    "ef9_unmatched": {"es": "% de episodios sin comuna enlazable", "en": "% of episodes without a linkable comuna"},
    "ef9_persons_rate": {"es": "Personas por 100.000 residentes", "en": "Persons per 100,000 residents"},
    "ef9_rate_residents": {"es": "Por 100.000 residentes", "en": "Per 100,000 residents"},
    "ef9_episodes_rate": {"es": "Episodios por 100.000 residentes", "en": "Episodes per 100,000 residents"},
    "ef9_no_geo": {"es": "geopandas o el archivo de límites comunales no están disponibles;\nel mapa no se dibuja y la tabla acompañante conserva los valores",
                   "en": "geopandas or the comuna boundary file is unavailable;\nthe map is not drawn and the companion table keeps the values"},
    # --- EF10 ------------------------------------------------------------------------------------
    "ef10_title": {"es": "Egresos DEIS con F84 como diagnóstico principal: detalle y comparación con GRD",
                   "en": "DEIS discharges with F84 as principal diagnosis: detail and comparison with GRD"},
    "ef10_a": {"es": "Egresos con F84 principal y tasa por 100.000 egresos", "en": "Discharges with principal F84 and rate per 100,000 discharges"},
    "ef10_b": {"es": "Establecimientos SNSS frente a no SNSS", "en": "SNSS versus non-SNSS establishments"},
    "ef10_c": {"es": "Por sexo registrado", "en": "By recorded sex"},
    "ef10_d": {"es": "Por banda de edad, 2019 y 2024", "en": "By age band, 2019 and 2024"},
    "ef10_e": {"es": "DEIS frente a GRD: única serie homologable (F84 principal)",
               "en": "DEIS versus GRD: the only homologous series (principal F84)"},
    "ef10_f": {"es": "Subcódigos F84 en DIAG1 y celdas enmascaradas", "en": "F84 subcodes in DIAG1 and masked cells"},
    "ef10_snss": {"es": "SNSS (hospitales públicos)", "en": "SNSS (public hospitals)"},
    "ef10_no_snss": {"es": "No SNSS (privados, FF.AA., mutuales)", "en": "Non-SNSS (private, armed forces, mutual)"},
    "ef10_masked": {"es": "Enmascarado por DEIS", "en": "Masked by DEIS"},
    "ef10_deis": {"es": "DEIS: F84 principal por 100.000 egresos", "en": "DEIS: principal F84 per 100,000 discharges"},
    "ef10_grd": {"es": "GRD: F84 principal por 100.000 episodios", "en": "GRD: principal F84 per 100,000 episodes"},
    "ef10_subcode": {"es": "% de los egresos con F84 principal", "en": "% of discharges with principal F84"},
    "ef10_age_band": {"es": "Banda de edad (años)", "en": "Age band (years)"},
}


def T(key: str, lang: str) -> str:
    try:
        return LBL[key][lang]
    except KeyError as exc:                                   # error explícito, nunca una cadena inventada
        raise KeyError(f"rótulo ausente: {key}/{lang}") from exc


# --- Traducción de categorías administrativas (el dato queda en su idioma original en las tablas es) ---
CAT_EN = {
    # TIPO_INGRESO
    "URGENCIA": "Emergency", "PROGRAMADA": "Scheduled", "NO PROGRAMADA": "Unscheduled", "OBSTETRICA": "Obstetric",
    "NO IDENTIFICADA": "Not identified", "NO IDENTIFICADO": "Not identified", "DESCONOCIDO": "Not reported",
    # TIPO_ACTIVIDAD
    "HOSPITALIZACIÓN": "Hospitalisation", "CIRUGÍA MAYOR AMBULATORIA (CMA)": "Major ambulatory surgery (CMA)",
    "HOSPITALIZACIÓN EN URGENCIA": "Emergency-room hospitalisation", "HOSPITALIZACIÓN DIURNA": "Day hospitalisation",
    # TIPO_PROCEDENCIA
    "SERVICIO EMERGENCIA (DOMICILIO)": "Emergency department (from home)",
    "CENTRO ESPECIALIDADES (CDT, CRS, CONSULTORIO ADOS. ESP)": "Specialty centre (CDT, CRS)",
    "OTROS HOSPITALES DE LA RED": "Other hospitals of the service network",
    "OTROS HOSPITALES RED NACIONAL": "Other hospitals of the national network",
    "CONSULTA PRIVADA": "Private consultation", "APS URGENCIA (SAPU, SUR, SUC)": "Primary-care emergency (SAPU, SUR, SUC)",
    "APS CONSULTORIO (CESFAM)": "Primary-care centre (CESFAM)",
    "OTRAS INSTITUCIONES SALUD (CLÍNICAS PRIVADAS, DE REHABILITAC": "Other health institutions (private, rehabilitation)",
    "OTRAS INSTITUCIONES (CÁRCEL, HOGARES DE ANCIANOS, SENAME, EC": "Other institutions (prison, care homes, SENAME)",
    "POSTA RURAL": "Rural post", "HOSPITALIZACIÓN DOMICILIARIA": "Home hospitalisation",
    "LISTA DE ESPERA": "Waiting list", "UGCC": "Central case-management unit (UGCC)",
    "PLAN DE RESOLUCIÓN LE": "Waiting-list resolution plan", "ESTRATEGIA CRR": "CRR strategy",
    "CARDIOCIRUGÍA PAGO GRD": "Cardiac surgery, GRD payment",
    # TIPOALTA
    "DOMICILIO": "Home", "FALLECIDO": "Died", "ALTA VOLUNTARIA": "Discharge against medical advice",
    "DERIVACIÓN OTRO HOSPITAL DEL SERVICIO": "Referral to another hospital of the service",
    "DERIVACIÓN OTRO HOSPITAL DE LA RED NACIONAL": "Referral to another hospital of the national network",
    "DERIVACIÓN INST. PRIVADA (COMPRA DE SERVICIOS": "Referral to a private institution (purchased care)",
    "DERIVACIÓN INST. PRIVADA (VOLUNTARIO)": "Referral to a private institution (voluntary)",
    "DERIVACIÓN A OTROS CENTROS (CÁRCEL, HOGAR DE": "Referral to other centres (prison, care home)",
    "FUGA DEL PACIENTE": "Patient absconded",
    # PREVISION_grouped
    "FONASA MAI A": "FONASA MAI A", "FONASA MAI B": "FONASA MAI B", "FONASA MAI C": "FONASA MAI C",
    "FONASA MAI D": "FONASA MAI D", "FONASA libre elección": "FONASA free choice", "ISAPRE": "ISAPRE",
    "Particular": "Out of pocket", "FFAA y de Orden": "Armed forces and police", "No identificada": "Not identified",
    "Otra": "Other",
    # ESPECIALIDAD_MEDICA
    "PEDIATRÍA": "Paediatrics", "NEUROLOGÍA PEDIÁTRICA": "Paediatric neurology",
    "PSIQUIATRÍA PEDIÁTRICA Y DE LA ADOLESCENCIA": "Child and adolescent psychiatry",
    "PSIQUIATRÍA ADULTO": "Adult psychiatry", "CIRUGÍA PEDIÁTRICA": "Paediatric surgery",
    "CIRUGÍA GENERAL": "General surgery", "MEDICINA INTERNA": "Internal medicine",
    "ODONTOPEDIATRÍA": "Paediatric dentistry", "OTORRINOLARINGOLOGÍA": "Otorhinolaryngology",
    "TRAUMATOLOGÍA Y ORTOPEDIA": "Orthopaedics and traumatology", "OFTALMOLOGÍA": "Ophthalmology",
    "NEUROCIRUGÍA": "Neurosurgery", "NEUROLOGÍA ADULTO": "Adult neurology",
    "OBSTETRICIA Y GINECOLOGÍA": "Obstetrics and gynaecology", "UROLOGÍA": "Urology",
    "ONCOLOGÍA MÉDICA": "Medical oncology", "HEMATO-ONCOLOGÍA PEDIÁTRICA": "Paediatric haemato-oncology",
    "MEDICINA INTENSIVA PEDIÁTRICA": "Paediatric intensive care",
    "ENFERMEDADES RESPIRATORIAS PEDIÁTRICAS (BRONCOPULMONAR PEDIATRICO)": "Paediatric respiratory medicine",
    "CIRUGÍA Y TRAUMATOLOGÍA BUCO MAXILOFACIAL": "Oral and maxillofacial surgery",
    "otra especialidad (fuera de las 20 principales)": "Other specialty (outside the top 20)",
    # los_bin / USOSPABELLON
    "no informado": "not reported", "3+": "3+", "91+": "91+",
}
# Los capítulos, los bloques de salud mental y las glosas CIE-10 vienen del ÚNICO diccionario del
# repositorio (`study/labels.py`), que declara para cada categoría de tres caracteres su glosa
# en español (MINSAL/DEIS) y en inglés (rúbrica de la CIE-10 de la OMS). Aquí no se repite ninguna.
def cat_label(value: str, lang: str) -> str:
    """Categoría administrativa en el idioma de salida; si no hay traducción verificada, se conserva el original."""
    v = str(value)
    if lang == "es":
        return v
    return CAT_EN.get(v, v)


def icd3_label(code: str, spanish: str, lang: str) -> str:
    """«J45 · Asma» / «J45 · Asthma»; el código solo cuando no hay glosa en el idioma pedido.

    El argumento `spanish` es la glosa que trae la tabla tidy; se ignora, porque la glosa autorizada de
    los dos idiomas está en `labels.ICD10` y así el documento en inglés nunca imprime la española."""
    return LB.icd_code_label(code, lang, sep=" · ")


def chapter_label(value: str, lang: str) -> str:
    return LB.icd_chapter_es_to(value, lang)


def block_label(value: str, lang: str) -> str:
    return LB.icd_chapter_es_to(value, lang)


_ABBR = [("Complejo Hospitalario ", "C.H. "), ("Complejo Asistencial ", "C.A. "), ("Hospital Clínico Metropolitano ", "H.C.M. "),
         ("Hospital Clínico Regional ", "H.C.R. "), ("Hospital Clínico de Niños ", "H. Niños "), ("Hospital de Niños ", "H. Niños "),
         ("Hospital Clínico ", "H.C. "), ("Hospital Provincial ", "H. Prov. "), ("Hospital Regional ", "H. Reg. "), ("Hospital Base ", "H. Base "),
         ("Hospital de Urgencia Asistencia Pública ", "H.U.A.P. "), ("Hospital Intercultural ", "H. Interc. "), ("Hospital ", "H. "),
         ("Instituto Nacional de Enfermedades Respiratorias y Cirugía Torácica", "Inst. Nac. Enf. Respiratorias"),
         ("Instituto ", "Inst. "), ("Doctor ", "Dr. "), ("Doctora ", "Dra. "), ("Monseñor ", "Mons. "), ("Presidente ", "Pdte. ")]


def abbreviate_hospital(name: str, max_core: int = 24) -> str:
    name = str(name)
    m = re.search(r"\(([^)]*)\)", name)
    city = m.group(1).split(",")[-1].strip() if m else ""
    core = re.sub(r"\s*\([^)]*\)", "", name).strip()
    for a, b in _ABBR:
        core = core.replace(a, b)
    if len(core) > max_core:
        core = core[: max_core - 1].rstrip() + "…"
    return f"{core} ({city})" if city and city not in core else core


# ===========================================================================
# Carga de las tablas tidy (solo lectura; ninguna se reescribe)
# ===========================================================================
INPUT_TABLES = ["grd_monthly", "grd_length_of_stay", "grd_los_age", "grd_episode_features", "grd_grd_weight",
                "grd_codiagnoses", "grd_codiagnosis_chapters", "grd_readmission", "grd_multiplicity", "grd_territory",
                "grd_age_single_year", "grd_year_summary", "grd_hospital_year", "grd_fixed_panel_hospitals",
                "grd_age_sex_year", "grd_subcode_year", "deis_year_summary", "deis_establishment_year",
                "deis_age_sex_year", "deis_f84_subcode_year", "deis_vs_grd_year", "rem_pathway_tidy",
                "ine_population_region_national_year_age_sex", "ine_population_comuna_year_age_sex"]


def load() -> SimpleNamespace:
    D = SimpleNamespace()
    D.monthly = C.read_tidy("grd_monthly")
    D.los = C.read_tidy("grd_length_of_stay")
    D.los_age = C.read_tidy("grd_los_age")
    D.feat = C.read_tidy("grd_episode_features")
    D.weight = C.read_tidy("grd_grd_weight", dtype={"ir_grd_code": "string"})
    D.codiag = C.read_tidy("grd_codiagnoses")
    D.chapters = C.read_tidy("grd_codiagnosis_chapters")
    D.readm = C.read_tidy("grd_readmission")
    D.mult = C.read_tidy("grd_multiplicity")
    D.terr = C.read_tidy("grd_territory")
    D.age1 = C.read_tidy("grd_age_single_year")
    D.year = C.read_tidy("grd_year_summary")
    D.hosp = C.read_tidy("grd_hospital_year")
    D.panel65 = C.read_tidy("grd_fixed_panel_hospitals")
    D.age_sex = C.read_tidy("grd_age_sex_year")
    D.deis_year = C.read_tidy("deis_year_summary")
    D.deis_estab = C.read_tidy("deis_establishment_year")
    D.deis_age_sex = C.read_tidy("deis_age_sex_year")
    D.deis_sub = C.read_tidy("deis_f84_subcode_year")
    D.deis_grd = C.read_tidy("deis_vs_grd_year")
    D.pop_reg = C.read_tidy("ine_population_region_national_year_age_sex")
    D.pop_com = C.read_tidy("ine_population_comuna_year_age_sex")
    rem = C.read_tidy("rem_pathway_tidy", dtype={"code": "string"}, low_memory=False)
    D.a05_month = (rem.loc[(rem.module == "A05") & (rem.code == CFG.STRICT["a05_entry"]) & (rem.in_era.astype(str) == "True")]
                   .groupby(["year", "month"], as_index=False)
                   .agg(entries=("total_known", "sum"), n_establishments=("IdEstablecimiento", "nunique")))
    D.a05_month["month"] = D.a05_month.month.astype(int)
    D.shapes_comuna = None                                    # se carga bajo demanda en EF9
    return D


# ===========================================================================
# Formato bilingüe de celdas
# ===========================================================================
def num(x, dec=0, lang="es") -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return T("not_estimable", lang)
    try:
        if pd.isna(x):
            return T("not_estimable", lang)
    except (TypeError, ValueError):
        pass
    return C.fmt_number(float(x), dec, lang)


def pct(x, lang="es", dec=1) -> str:
    if x is None or pd.isna(x):
        return T("not_estimable", lang)
    return num(float(x), dec, lang) + (" %" if lang == "es" else "%")


def n_pct(n, p, lang="es", dec=1) -> str:
    return f"{num(n, 0, lang)} ({pct(p, lang, dec)})"


def ci(lo, hi, dec=1, lang="es") -> str:
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi):
        return T("not_estimable", lang)
    return f"{num(lo, dec, lang)}–{num(hi, dec, lang)}"


def val_ci(v, lo, hi, dec=1, lang="es") -> str:
    if v is None or pd.isna(v):
        return T("not_estimable", lang)
    return f"{num(v, dec, lang)} ({ci(lo, hi, dec, lang)})"


# ===========================================================================
# Estadística auxiliar
# ===========================================================================
def jeffreys(k: float, n: float, alpha: float = 0.05) -> tuple[float, float, float]:
    """Intervalo de Jeffreys (previa Beta(1/2,1/2)) para una proporción; k = 0 y k = n dan límites truncados."""
    if n is None or n <= 0 or pd.isna(n):
        return np.nan, np.nan, np.nan
    k = float(k)
    n = float(n)
    p = k / n
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k + 0.5, n - k + 0.5))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 0.5, n - k + 0.5))
    return p, lo, hi


def ratio_ci(a: float, b: float, alpha: float = 0.05) -> tuple[float, float, float]:
    """Razón de dos recuentos independientes de Poisson con IC por el método delta en escala logarítmica."""
    if a <= 0 or b <= 0:
        return (np.nan, np.nan, np.nan)
    r = a / b
    se = np.sqrt(1.0 / a + 1.0 / b)
    z = stats.norm.ppf(1 - alpha / 2)
    return float(r), float(r * np.exp(-z * se)), float(r * np.exp(z * se))


def rate_ci(count, denominator, per=PER):
    if denominator is None or denominator <= 0 or pd.isna(denominator) or pd.isna(count):
        return np.nan, np.nan, np.nan
    return C.rate_per(float(count), float(denominator), per=per)


def gini(values: np.ndarray) -> float:
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return np.nan
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v).sum()) / (n * v.sum()) - (n + 1) / n)


# ===========================================================================
# Estilo de láminas
# ===========================================================================
plt, sns = C.style()
import matplotlib.ticker as mticker  # noqa: E402  (después de C.style(), que fija el backend)

# --- Norma de lámina de esta fase -----------------------------------------------------------------
# Lienzo vertical de 180 × 245 mm dibujado a escala 1:1 (una lámina por página, sin reducción al
# insertarla), rejilla de tres filas por dos columnas, seis paneles como máximo, letras de panel en
# minúscula y 600 ppp. Las láminas anteriores se dibujaban a 432 mm de ancho y se reducían dentro de
# la página, lo que dejaba varios paneles al límite de la legibilidad.
PLATE_W_IN = 180.0 / 25.4          # 7.09 pulgadas
PLATE_H_IN = 245.0 / 25.4          # 9.65 pulgadas
PLATE_ROWS, PLATE_COLS = 3, 2
PLATE_LETTERS = "abcdef"           # minúsculas, en la lámina y en el pie, en los dos idiomas
FS_TITLE = 9.0                     # título de panel (negrita)
FS_BASE = 8.0                      # tipografía base y rótulos de eje
FS_TICK = 7.0                      # marcas de eje y leyenda
FS_LEG = 7.0
FS_ANN = 6.4                       # anotaciones dentro del panel
FS_CELL = 6.0                      # texto más pequeño admitido (celdas de mapa de calor)
FS_LETTER = 10.0                   # letra de panel

plt.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 600,
    "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold", "axes.labelsize": FS_BASE,
    "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "legend.fontsize": FS_LEG, "legend.title_fontsize": FS_LEG,
    # Toda leyenda de estas láminas se dibuja DENTRO del panel: sin recuadro se leía sobre las barras y
    # sobre las series. Con el recuadro blanco translúcido el dato sigue visible bajo ella y el texto
    # sigue legible, que es lo que la revista exige.
    "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
    "legend.edgecolor": "none", "legend.borderpad": 0.25,
    "legend.handlelength": 1.4, "legend.handletextpad": 0.5, "legend.columnspacing": 1.0,
    "legend.labelspacing": 0.35, "legend.borderaxespad": 0.3,
    "axes.linewidth": 0.7, "grid.linewidth": 0.5, "grid.alpha": 0.32,
    "lines.linewidth": 1.1, "lines.markersize": 3.2,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.2, "ytick.major.size": 2.2,
    "xtick.major.pad": 1.6, "ytick.major.pad": 1.6,
    "axes.titlepad": 4.0, "axes.labelpad": 2.0,
})

# Recuadro translúcido para las anotaciones de contexto: el texto sigue siendo legible cuando cae sobre una serie.
CTX_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.4)
_MEASURE_FIG = plt.figure(figsize=(1, 1))   # lienzo auxiliar: solo se usa para medir texto


def clip_label(text: str, width: int) -> str:
    """Recorta una etiqueta larga añadiendo puntos suspensivos (nunca deja la palabra cortada sin marca)."""
    s = str(text)
    return s if len(s) <= width else s[: max(1, width - 1)].rstrip() + "…"


def tick_label(text: str, width: int = 24, lines: int = 2) -> str:
    """Etiqueta de eje categórico para una celda estrecha: hasta `lines` líneas antes de recortar.

    Recortar en una sola línea confundía categorías que solo se distinguen por su final («derivación a otro
    hospital del servicio» frente a «… de la red nacional»); repartirlas en dos líneas conserva la parte que las
    diferencia sin bajar del cuerpo mínimo de la norma.
    """
    parts = textwrap.wrap(str(text), width) or [str(text)]
    if len(parts) <= lines:
        return "\n".join(parts)
    keep = parts[:lines]
    keep[-1] = clip_label(keep[-1] + " " + parts[lines], width)
    return "\n".join(keep)


def _tick_decimals(values) -> int:
    """Decimales necesarios para representar sin pérdida las marcas visibles de un eje (máximo 3)."""
    dec = 0
    for v in values:
        if v is None or not np.isfinite(v):
            continue
        for k in range(4):
            if abs(round(float(v), k) - float(v)) < 1e-9:
                dec = max(dec, k)
                break
        else:
            dec = 3
    return dec


def localise_ticks(fig, lang: str) -> None:
    """Separador decimal y de millares según idioma en todos los ejes numéricos continuos de la lámina.

    Solo se tocan los ejes lineales cuyo formateador sigue siendo el ScalarFormatter por defecto: los ejes de años,
    los ejes categóricos y los mapas de calor fijan sus rótulos con set_*ticklabels (FixedFormatter) y los ejes
    logarítmicos muestran potencias de diez, de modo que ninguno de ellos se modifica.
    """
    for ax in fig.axes:
        cbar = getattr(ax, "_colorbar", None)
        if cbar is not None:                     # la barra de color reaplica su propio formateador al dibujar
            axis = cbar.ax.xaxis if cbar.orientation == "horizontal" else cbar.ax.yaxis
            try:
                lo, hi = sorted(cbar.mappable.get_clim())
                ticks = list(axis.get_major_locator().tick_values(lo, hi))
            except (TypeError, ValueError, AttributeError):
                ticks = list(axis.get_majorticklocs())
            dec = _tick_decimals(ticks)
            cbar.formatter = mticker.FuncFormatter(lambda v, _p, d=dec, lg=lang: C.fmt_number(v, d, lg))
            cbar.update_ticks()
            continue
        for axis, scale, lim in ((ax.xaxis, ax.get_xscale(), ax.get_xlim()),
                                 (ax.yaxis, ax.get_yscale(), ax.get_ylim())):
            if scale != "linear":
                continue
            fmt = axis.get_major_formatter()
            # Se puede volver a llamar: un eje ya localizado se REVISA (si el panel se ensanchó después, sus
            # marcas son otras y los decimales que necesitan también), y uno con rótulos fijados a mano se
            # deja como está.
            if not getattr(axis, "_localised", False):
                if not isinstance(fmt, mticker.ScalarFormatter) or isinstance(fmt, mticker.FixedFormatter):
                    continue
            lo, hi = (min(lim), max(lim))
            try:
                ticks = list(axis.get_major_locator().tick_values(lo, hi))
            except (TypeError, ValueError):
                ticks = list(axis.get_majorticklocs())
            vis = [t for t in ticks if lo - 1e-9 <= t <= hi + 1e-9] or ticks
            dec = _tick_decimals(vis)
            axis.set_major_formatter(mticker.FuncFormatter(lambda v, _p, d=dec, lg=lang: C.fmt_number(v, d, lg)))
            axis._localised = True


#: Separador decimal de cada idioma. Un eje no puede escribir el del otro: en la lámina española «0.6» y
#: «1.012» ponen el mismo punto a significar decimal y millar, y el lector no tiene forma de distinguirlos.
DECIMAL_MARK = {"es": ",", "en": "."}


def _decimal_mark_of(token: str) -> str | None:
    """Marca decimal que usa un número IMPRESO, o None si el número no lo dice sin ambigüedad.

    «0.6» y «1,05» lo dicen (el grupo tras el separador no tiene tres cifras); «1.012» y «20,000» no —son
    millares en un idioma y decimales de tres cifras en el otro—, y por eso no se juzgan.
    """
    parts = re.split(r"([.,])", token)
    seps, runs = parts[1::2], parts[2::2]
    if not seps or not all(runs):
        return None
    if len(set(seps)) == 2:
        return seps[-1]                    # «1.234,5»: el último separador es el decimal
    return seps[-1] if len(runs[-1]) != 3 else None


#: Todo lo que en una lámina separa un número de lo que tiene al lado: espacios, guiones de intervalo, la
#: barra de una razón, el signo menos tipográfico, los paréntesis de un IC. Partiendo por aquí, «(47,9–50,8)»
#: son dos números y «F84.0» sigue siendo una sola pieza —con letras— que no se juzga como número.
_NUM_SPLIT = re.compile(r"[\s\u00a0=/±()\[\]{}«»<>≤≥~≈+\-−–—*†‡%‰$;:]+")


def _printed_numbers(text: str) -> list[str]:
    """Números impresos dentro de una cadena, sin los que no son números (F84.0, 1.ª parte, 10³)."""
    out = []
    for chunk in _NUM_SPLIT.split(str(text).replace("\n", " ")):
        w = chunk
        while w and w[-1] in ".,":          # punto o coma de puntuación al final de la frase
            w = w[:-1]
        if w and re.fullmatch(r"\d[\d.,]*", w):
            out.append(w)
    return out


def numbers_against_the_language(fig, lang: str) -> list[str]:
    """Marcas de eje o rótulos que escriben el separador decimal del OTRO idioma.

    Comprueba el panel entero —marcas de los dos ejes, del gemelo, de la barra de color, título, rótulos de
    eje, leyenda y anotaciones—, de modo que un eje no puede discrepar del panel en el que está: los dos se
    miden contra la misma convención, la del idioma que se está imprimiendo. El defecto que cierra: un eje
    que iba de 0 a 1 se quedaba fuera del localizador de millares y matplotlib lo escribía «0.0 … 1.0» en la
    versión española, en el mismo panel cuya leyenda imprimía «n=1.012».
    """
    want = DECIMAL_MARK[lang]
    faults = []

    def judge(where: str, strings) -> None:
        for s in strings:
            if not str(s).strip() or "$" in str(s):      # las potencias de diez van en mathtext
                continue
            for tok in _printed_numbers(s):
                mark = _decimal_mark_of(tok)
                if mark is not None and mark != want:
                    faults.append(f"{where}: «{tok}» usa «{mark}» como separador decimal ({lang} escribe «{want}»)")

    todos = list(fig.axes)
    i = 0
    while i < len(todos):
        todos.extend(a for a in getattr(todos[i], "child_axes", []) if a not in todos)
        i += 1
    for k, ax in enumerate(todos):
        who = getattr(getattr(ax, "_panel_letter", None), "get_text", lambda: f"#{k}")()
        for nom, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            # Un eje apagado (`ax.axis("off")`) no imprime marcas: sus rótulos por omisión «0.0 … 1.0» no
            # llegan al papel y no se juzgan.
            if not axis.get_visible() or not getattr(ax, "axison", True):
                continue
            judge(f"{who} eje {nom}", [t.get_text() for t in axis.get_ticklabels() if t.get_visible()])
            judge(f"{who} rótulo del eje {nom}", [axis.label.get_text()])
        t = panel_title_artist(ax)
        judge(f"{who} título", [t.get_text()] if t is not None else [])
        judge(f"{who} texto", [x.get_text() for x in ax.texts if x.get_visible()])
        lg = ax.get_legend()
        if lg is not None and lg.get_visible():
            judge(f"{who} leyenda", [x.get_text() for x in lg.get_texts()]
                  + ([lg.get_title().get_text()] if lg.get_title() is not None else []))
    return faults


def new_plate(nrows: int = PLATE_ROWS, ncols: int = PLATE_COLS, figsize=(PLATE_W_IN, PLATE_H_IN)):
    """Lienzo de la norma: 180 × 245 mm, tres filas por dos columnas, en orden de lectura (a b / c d / e f)."""
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055)
    return fig, np.atleast_1d(axes).ravel()


def letter(ax, ch: str, dx: float = -30.0, dy: float = 11.0) -> None:
    """Letra de panel en minúscula y entre paréntesis; `anchor_panel_letters` la clava a su título.

    La letra va ENTRE PARÉNTESIS, «(a)», que es la convención que escriben las 58 leyendas con
    paneles y la que ya imprimían las láminas de 06/08a/08b/08c: con la letra a secas el artículo
    publicaba dos convenciones y la leyenda no casaba con su propia lámina.
    """
    t = ax.annotate(C.plate_panel_letter(ch), xy=(0.0, 1.0), xycoords="axes fraction", xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=FS_LETTER, fontweight="bold", va="top", ha="left", family="DejaVu Sans",
                    annotation_clip=False)
    # La letra es parte del título: su sitio lo fija `anchor_panel_letters` midiendo la caja del título, en
    # la línea del título y a la izquierda de su celda, y la columna de letras de la lámina solo se lee si
    # las seis están alineadas. Se marca para que el motor de descongestión no la desplace por su cuenta (el
    # verificador la sigue comprobando: marcarla no la exime de nada, solo impide que la muevan).
    t.set_gid(C.PLATE_KEEP)
    ax._panel_letter = t
    return t


CELL_MARGIN = 2.0 / 180.0   # margen izquierdo de la celda, en fracción de figura (2 mm)
TITLE_W_PT = (PLATE_W_IN * 72.0 / PLATE_COLS) - 2.0 * 72.0 / 25.4 - 31.0   # celda − margen − letra
LETTER_GAP_PT = 22.0      # hueco entre la letra del panel y el comienzo del título


def _text_width_pt(s: str, fontsize: float = FS_TITLE, weight: str = "bold") -> float:
    """Ancho tipográfico real de una cadena (puntos), medido con la misma fuente con que se dibujará."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.backends.backend_agg import get_hinting_flag
    fig = _MEASURE_FIG
    r = fig.canvas.get_renderer()
    prop = FontProperties(size=fontsize, weight=weight)
    w, _h, _d = r.get_text_width_height_descent(s, prop, False)
    return w * 72.0 / fig.dpi


def wrap_measured(text: str, max_pt: float = TITLE_W_PT, fontsize: float = FS_TITLE, weight: str = "bold") -> str:
    """Ajuste de línea por ancho medido, no por número de caracteres.

    El español es ~15 % más largo que el inglés y las palabras del registro son largas: contar caracteres deja
    títulos que se salen de la celda en un idioma y cortos en el otro. Midiendo el texto, la misma norma vale para
    los cuatro documentos.
    """
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and _text_width_pt(trial, fontsize, weight) > max_pt:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return "\n".join(lines) if lines else str(text)


def panel(ax, ch: str, title: str, width: int | None = None) -> None:
    """Letra de panel y título, ambos anclados a la izquierda de la celda por `align_panel_titles`.

    `width` se conserva por compatibilidad con las llamadas antiguas pero ya no se usa: el ajuste es por ancho
    medido de la celda, de modo que ningún título invade la columna vecina en ninguno de los dos idiomas.
    """
    letter(ax, ch)
    ax.set_title(wrap_measured(title), fontsize=FS_TITLE, fontweight="bold", loc="left")


def _cell_bounds(fig, spec) -> tuple[float, float]:
    """Bordes izquierdo y derecho, en fracción de figura, de la celda de la rejilla que ocupa `spec`.

    `SubplotSpec.get_position` devuelve el rectángulo ya descontadas las decoraciones (rótulos, marcas), que se
    mueve con ellas; la geometría de la rejilla es fija y es la que define la columna de la lámina.
    """
    gs = spec.get_gridspec()
    parent = getattr(gs, "_subplot_spec", None)
    x0, x1 = _cell_bounds(fig, parent) if parent is not None else (0.0, 1.0)
    n = gs.ncols
    return (x0 + (x1 - x0) * spec.colspan.start / n, x0 + (x1 - x0) * spec.colspan.stop / n)


def panel_title_artist(ax):
    """El texto que hace de título del panel: `set_title(loc="left")` no escribe en `ax.title`."""
    return next((c for c in (getattr(ax, "_left_title", None), ax.title, getattr(ax, "_right_title", None))
                 if c is not None and str(c.get_text()).strip()), None)


def _letter_cell_x(fig, ax) -> float:
    """Borde izquierdo de la CELDA, en fracción de los ejes: la columna en que van todas las letras."""
    spec = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
    pos = ax.get_position()
    if spec is None or pos.width <= 0:
        return 0.0
    return (_cell_bounds(fig, spec)[0] + CELL_MARGIN - pos.x0) / pos.width


def _grid_cell_key(ax):
    """Celda de la rejilla de la lámina que ocupa unos ejes (la de la NORMA, no la de una subrejilla)."""
    sp = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
    if sp is None:
        return None
    try:
        top = sp.get_topmost_subplotspec()
        return (id(top.get_gridspec()), top.rowspan.start, top.rowspan.stop, top.colspan.start, top.colspan.stop)
    except (AttributeError, ValueError):
        return None


def panel_letter_title(fig, ax):
    """Título al que pertenece la letra de este panel, y si es el de SUS ejes o el de su celda.

    Un panel puede estar repartido en varias facetas —el mapa comunal de la EF9 son tres franjas en una sola
    celda, con el título sobre la del centro y la letra en la de la izquierda—: la letra sigue siendo la de un
    solo panel y su título es el de la celda, dibujado sobre otros ejes."""
    t = panel_title_artist(ax)
    if t is not None:
        return t, True
    key = _grid_cell_key(ax)
    if key is not None:
        for other in fig.axes:
            if other is ax or _grid_cell_key(other) != key:
                continue
            t = panel_title_artist(other)
            if t is not None:
                return t, False
    return None, False


def anchor_panel_letters(fig, gap_pt: float = LETTER_GAP_PT) -> None:
    """Clava cada letra de panel a la CAJA DE SU TÍTULO, para que las dos viajen juntas.

    La letra se colocaba en una coordenada de eje calculada UNA vez, con el alto que el título tenía en ese
    momento; después `C.plate_resolve` repliega el título que se sale de su celda (una línea más de las
    previstas), baja el panel cuyo título ya no cabe, y `make_room` vuelve a repartir el ancho. Cada uno de
    esos pasos movía el título y dejaba la letra donde estaba: los verificadores encontraron dieciséis
    letras separadas de su título entre una y cinco líneas, y una impresa dentro del área de datos.

    Anclada al ARTISTA del título —matplotlib admite un artista como sistema de coordenadas de una
    anotación, y (0, 1) es la esquina superior izquierda de su caja— la letra se recoloca sola en cada
    dibujo: da igual que el título se pliegue a una, dos o tres líneas, que el panel se estreche o que se
    baje. El desplazamiento es de `gap_pt` puntos a la izquierda del título, de modo que las letras siguen
    formando una columna (todos los títulos arrancan en el mismo borde de celda).
    """
    for ax in fig.axes:
        lt = getattr(ax, "_panel_letter", None)
        if lt is None:
            continue
        t, own = panel_letter_title(fig, ax)
        lt.set_ha("left")
        if t is not None and own:
            lt.xycoords = t
            lt.xy = (0.0, 1.0)               # esquina superior izquierda de la PRIMERA línea del título
            lt.set_va("top")
            lt.set_position((-gap_pt, 0.0))  # `textcoords="offset points"`: el hueco no depende del dibujo
        elif t is not None:
            # Panel repartido en facetas: el título está sobre OTROS ejes (la franja central del mapa
            # comunal), así que la letra toma de él solo la ALTURA —la línea del título, como en los demás
            # paneles— y la x del borde izquierdo de SU CELDA, para no acabar impresa sobre el mapa. La x se
            # mide sobre la celda y no sobre los ejes, que el aspecto igual estrecha y centra.
            lt.xycoords = ("axes fraction", t)
            lt.xy = (_letter_cell_x(fig, ax), 1.0)
            lt.set_va("top")
            lt.set_position((0.0, 0.0))
        else:
            # Ni título propio ni título de celda: la letra se queda en el borde izquierdo de su celda y
            # 2 pt por encima de sus ejes, que es lo único a lo que puede anclarse.
            lt.xycoords = "axes fraction"
            lt.xy = (_letter_cell_x(fig, ax), 1.0)
            lt.set_va("bottom")
            lt.set_position((0.0, 2.0))
        lt.set_gid(C.PLATE_KEEP)


def letters_off_their_titles(fig, tol_pt: float = 2.0) -> list[str]:
    """Letras de panel que NO están en la línea de su título, o que caen dentro del área de datos.

    Es la comprobación que hicieron los verificadores a mano sobre la lámina impresa: la letra se lee en la
    línea del título, a su izquierda y fuera del panel. Se mide sobre el dibujo real, de modo que ningún
    cambio posterior (un título replegado, un panel bajado, un rótulo movido) puede volver a separarlas sin
    que la lámina falle aquí."""
    r = fig.canvas.get_renderer()
    s = 72.0 / fig.dpi
    faults = []
    for ax in fig.axes:
        lt = getattr(ax, "_panel_letter", None)
        if lt is None or not lt.get_visible():
            continue
        t, own = panel_letter_title(fig, ax)
        try:
            lb = lt.get_window_extent(r)
        except (AttributeError, ValueError, RuntimeError):
            continue
        name = str(lt.get_text())
        if t is not None:
            tb = t.get_window_extent(r)
            if abs(lb.y1 - tb.y1) * s > tol_pt:
                faults.append(f"{name}: la letra está a {abs(lb.y1 - tb.y1) * s:.1f} pt de la primera línea de su título")
            if own and lb.x1 > tb.x0 + tol_pt / s:
                faults.append(f"{name}: la letra se solapa con su título")
        try:
            ab = ax.get_window_extent()
        except (AttributeError, ValueError, RuntimeError):
            continue
        if min(lb.x1, ab.x1) - max(lb.x0, ab.x0) > 1.0 and min(lb.y1, ab.y1) - max(lb.y0, ab.y0) > 1.0:
            faults.append(f"{name}: la letra se imprime dentro del área de datos de su panel")
    return faults


def align_panel_titles(fig) -> None:
    """Ancla el título de cada panel al borde izquierdo de SU celda, y la letra al título.

    En una celda estrecha un título centrado se desplaza con los ejes: si las etiquetas del eje Y son largas los
    ejes empiezan muy a la derecha, el título se corre con ellos, se sale de la celda y choca con el panel vecino.
    Anclado a la celda, cada lámina muestra una columna de títulos estable y la letra queda siempre a su izquierda,
    en la línea del título.
    """
    fig.canvas.draw()
    # El motor de composición se congela aquí: si siguiera activo, cada dibujo posterior (incluido el de
    # `savefig`) volvería a mover los ejes y el título quedaría anclado a una posición que ya no existe.
    fig.set_layout_engine("none")
    fig.canvas.draw()
    W = fig.bbox.width
    gap = LETTER_GAP_PT * fig.dpi / 72.0
    for ax in fig.axes:
        spec = ax.get_subplotspec()
        lt = getattr(ax, "_panel_letter", None)
        pos = ax.get_position()
        if spec is None or lt is None or pos.width <= 0 or pos.height <= 0:
            continue
        # set_title(loc="left") no escribe en ax.title sino en el texto de esa esquina
        t = panel_title_artist(ax)
        if t is None:
            continue
        x_cell = (_cell_bounds(fig, spec)[0] + CELL_MARGIN - pos.x0) / pos.width
        t.set_ha("left")
        t.set_x(x_cell + gap / (pos.width * W))
    anchor_panel_letters(fig)
    fig.canvas.draw()


def detach_annotations(fig) -> None:
    """Las anotaciones escritas dentro de un panel dejan de competir por el espacio de la composición.

    `constrained_layout` mide cada eje con el rectángulo de TODOS sus hijos de texto: una nota larga escrita dentro
    del panel encogía la columna entera —en la lámina de hospitales llegó a dejar los seis ejes sin ancho— porque
    el solucionador intentaba hacerle sitio fuera. Marcadas como ajenas a la composición, se siguen dibujando donde
    el panel las puso y ya no deforman la lámina.
    """
    for ax in fig.axes:
        for t in list(ax.texts):
            t.set_in_layout(False)


YLABEL_H_PT = 138.0       # alto útil del área de ejes de una celda: un rótulo de eje Y más largo se parte en líneas


def wrap_axis_labels(fig) -> None:
    """Parte en varias líneas el rótulo del eje Y que sea más largo que el alto de su panel.

    Un rótulo vertical más alto que los ejes sobresale por arriba y se cruza con la letra del panel; partido en
    dos líneas cabe dentro y conserva su cuerpo de 8 pt."""
    for ax in fig.axes:
        for axis in (ax.yaxis,):
            lbl = axis.label
            txt = lbl.get_text()
            if not txt or "\n" in txt:
                continue
            if _text_width_pt(txt, lbl.get_fontsize(), "normal") > YLABEL_H_PT:
                lbl.set_text(wrap_measured(txt, YLABEL_H_PT, lbl.get_fontsize(), "normal"))
                lbl.set_linespacing(1.0)


def note_in_panel(ax, text: str, x: float = 0.02, y: float = 0.03, ha: str = "left", va: str = "bottom",
                  fontsize: float = FS_ANN, color: str = "#555555", max_pt: float = 148.0, **kw):
    """Nota metodológica dentro del panel, ajustada por ancho medido para no salirse de la celda."""
    return ax.text(x, y, wrap_measured(text, max_pt, fontsize, "normal"), transform=ax.transAxes,
                   fontsize=fontsize, color=color, ha=ha, va=va, **kw)


# --- Sitio propio para cada pieza de texto del panel ------------------------------------------------
# El defecto más repetido que los verificadores encontraron en estas láminas no es DÓNDE está escrita la
# nota, sino que el panel no le deja sitio: la marca de la pandemia, la de la Ley y la leyenda se escriben
# en una fracción fija del eje y la serie sube hasta ahí. Reubicarlas no resuelve nada —en un panel lleno
# todos los rincones tienen tinta—: lo que hace falta es ESPACIO. Aquí se mide cuánta tinta de datos cae
# bajo cada pieza y se estira el eje por el lado más barato hasta que su banda queda vacía. Nadie se mueve
# de donde su autor lo puso, ningún cuerpo se reduce y ningún dato se recorta: el panel se ensancha.
GROW_CAP = 2.6            # ningún eje se estira más de esta proporción de su recorrido original
GROW_PAD_PT = 2.0         # holgura entre la tinta y la pieza, en puntos
GROW_SIDES = {"top": 1.0, "right": 1.2, "bottom": 1.35, "left": 1.6}   # preferencia: arriba antes que abajo


def _extent(artist, r):
    """Caja de pantalla de un artista, o None si todavía no tiene una medible."""
    try:
        b = artist.get_window_extent(r)
    except (AttributeError, ValueError, RuntimeError, TypeError):
        return None
    if not np.isfinite([b.x0, b.y0, b.x1, b.y1]).all() or b.width <= 0 or b.height <= 0:
        return None
    return b


def _over(a, b) -> float:
    """Área de solape de dos rectángulos de pantalla (0 si no se tocan)."""
    return (max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0)) * max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0)))


def _ink_points(ax) -> np.ndarray:
    """Puntos de la TINTA DE DATOS del panel, en píxeles.

    Se cuenta lo que está dibujado en coordenadas de dato —líneas (densificadas: una recta larga solo tiene
    dos vértices), barras, nubes de puntos, bandas y barras de error— y se excluye deliberadamente el
    contexto en coordenadas mixtas (la banda 2020–2021, la línea de la Ley): son marcas de contexto, no
    datos, y la norma del estudio prohíbe leerlas como intervención.
    """
    out = []

    def dense(q):
        q = np.asarray(q, dtype=float)
        q = q[np.isfinite(q).all(axis=1)] if q.ndim == 2 and len(q) else np.empty((0, 2))
        if len(q) < 2:
            return q
        t = np.linspace(0.0, 1.0, 12)[:, None, None]
        return np.vstack([q, (q[None, :-1, :] * (1 - t) + q[None, 1:, :] * t).reshape(-1, 2)])

    for ln in ax.lines:
        if not ln.get_visible() or ln.get_transform() is not ax.transData:
            continue
        d = np.asarray(ln.get_xydata(), dtype=float)
        if d.ndim != 2 or not len(d):
            continue
        out.append(dense(ax.transData.transform(d[np.isfinite(d).all(axis=1)])))
    for patch in ax.patches:
        if not patch.get_visible():
            continue
        try:
            if patch.get_data_transform() is not ax.transData:
                continue                      # axvspan y axhspan: contexto en coordenadas mixtas
            b = patch.get_window_extent()
        except (AttributeError, ValueError, TypeError):
            continue
        if b is None or not np.isfinite([b.x0, b.y0, b.x1, b.y1]).all():
            continue
        xs = np.linspace(b.x0, b.x1, 5)
        out.append(np.column_stack([np.repeat(xs, 3), np.tile([b.y0, 0.5 * (b.y0 + b.y1), b.y1], len(xs))]))
    for coll in ax.collections:
        if not coll.get_visible():
            continue
        try:
            offs = np.asarray(coll.get_offsets(), dtype=float)
        except (AttributeError, ValueError, TypeError):
            offs = np.empty((0, 2))
        if offs.ndim == 2 and len(offs) and not (len(offs) == 1 and not np.any(offs)):
            try:
                out.append(np.asarray(coll.get_offset_transform().transform(offs), dtype=float))
            except (AttributeError, ValueError, TypeError):
                pass
            continue
        try:
            tr = coll.get_transform()
            if tr is not ax.transData:
                continue                      # la colección no vive en coordenadas de dato
            for path in coll.get_paths():
                v = np.asarray(path.vertices, dtype=float)
                if len(v):
                    out.append(dense(tr.transform(v[np.isfinite(v).all(axis=1)])))
        except (AttributeError, ValueError, TypeError):
            continue
    pts = [q for q in out if len(q)]
    return np.vstack(pts) if pts else np.empty((0, 2))


def _panel_pieces(ax, r) -> list:
    """Piezas de texto que RESERVAN sitio en el panel: la leyenda y las notas escritas sobre el eje.

    Se excluyen los rótulos anclados a un dato (`annotate`, que señala un punto concreto y se resuelve con
    su propio criterio) y los rótulos de valor en coordenadas de dato. Cada pieza viaja con el artista, su
    caja y si se le permite cambiar de altura dentro del panel (la leyenda no: su sitio lo elige el motor
    de composición; una nota sí, siempre que no acabe encima de otra pieza)."""
    pieces = []
    lg = ax.get_legend()
    if lg is not None and lg.get_visible():
        b = _extent(lg, r)
        if b is not None:
            pieces.append(dict(art=lg, ax=ax, box=b, movable=False, sides=_piece_sides(lg, ax)))
    for t in ax.texts:
        if not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == C.PLATE_KEEP:
            continue
        if type(t).__name__ == "Annotation":
            continue                          # señala un dato: no es una nota de panel
        if t.get_transform() is ax.transData:
            continue
        b = _extent(t, r)
        if b is not None:
            pieces.append(dict(art=t, ax=ax, box=b, movable=True, sides=_piece_sides(t, ax)))
    return pieces


def _piece_sides(art, ax) -> tuple:
    """Lados por los que TIENE SENTIDO estirar el eje para despejar esta pieza.

    Una marca de contexto se escribe en coordenadas mixtas: su x es el dato (el centro de la banda
    2020–2021, la fecha de la Ley) y viaja con el eje. Estirar el eje X la arrastra con la serie y no
    despeja nada —además de dejar años vacíos en un eje de años—, de modo que solo se estira en vertical.
    """
    tr = getattr(art, "get_transform", lambda: None)()
    try:
        if tr is ax.get_xaxis_transform():
            return ("top", "bottom")
        if tr is ax.get_yaxis_transform():
            return ("right", "left")
    except (AttributeError, ValueError):
        pass
    return ("top", "bottom", "right", "left")


#: Alturas candidatas de una nota dentro del panel (fracción del eje, alineación vertical). La primera es
#: la banda alta, bajo el título; las intermedias caben bajo una leyenda superior; la última es el pie del
#: panel. La nota se queda donde su autor la puso salvo que ahí no haya forma de dejarle sitio.
NOTE_ANCHORS = [(0.975, "top"), (0.80, "top"), (0.62, "top"), (0.02, "bottom"), (0.22, "bottom")]


def _band_box(axb, box):
    """Franja del panel entero a la altura de `box`: lo que hay que dejar libre para una leyenda."""
    from matplotlib.transforms import Bbox
    return Bbox.from_extents(axb.x0, box.y0, axb.x1, box.y1)


def _anchor_box(axb, box, y: float, va: str):
    """Caja que ocuparía una pieza anclada a la fracción `y` del eje, sin cambiar su columna."""
    from matplotlib.transforms import Bbox
    edge = axb.y0 + float(y) * axb.height
    y1 = edge if va == "top" else edge + box.height
    return Bbox.from_extents(box.x0, y1 - box.height, box.x1, y1)


def _grow_factor(ax, pts, box, side, pad) -> float:
    """Cuánto hay que estirar el eje de `ax` por `side` para que la tinta salga de `box` (1.0 = nada)."""
    if not len(pts):
        return 1.0
    try:
        axb = ax.get_window_extent()
    except (AttributeError, ValueError):
        return np.inf
    vertical = side in ("top", "bottom")
    p0, p1 = (axb.y0, axb.y1) if vertical else (axb.x0, axb.x1)
    lo, hi = ax.get_ylim() if vertical else ax.get_xlim()
    log = (ax.get_yscale() if vertical else ax.get_xscale()) == "log"
    if p1 <= p0 or not np.isfinite([lo, hi]).all() or hi <= lo or (log and lo <= 0):
        return np.inf
    # Un eje con las marcas fijadas a mano (años, meses, categorías) no se estira: el recorrido que se
    # añadiría no tiene marcas y la lámina mostraría un año en blanco donde no hay ningún año.
    if isinstance((ax.yaxis if vertical else ax.xaxis).get_major_formatter(), mticker.FixedFormatter):
        return np.inf
    # solo estorba la tinta que cae en la franja perpendicular de la pieza
    if vertical:
        sel = (pts[:, 0] >= box.x0 - pad) & (pts[:, 0] <= box.x1 + pad)
        near = pts[sel, 1]
    else:
        sel = (pts[:, 1] >= box.y0 - pad) & (pts[:, 1] <= box.y1 + pad)
        near = pts[sel, 0]
    if not len(near):
        return 1.0
    if side in ("top", "right"):
        edge = (box.y0 - pad) if side == "top" else (box.x0 - pad)
        extreme = float(np.max(near))
        if extreme <= edge:
            return 1.0
    else:
        edge = (box.y1 + pad) if side == "bottom" else (box.x1 + pad)
        extreme = float(np.min(near))
        if extreme >= edge:
            return 1.0
    f = (extreme - p0) / (p1 - p0)
    g = (edge - p0) / (p1 - p0)
    L, H = (np.log10(lo), np.log10(hi)) if log else (lo, hi)
    v = L + f * (H - L)
    if side in ("top", "right"):
        if g <= 0.08:
            return np.inf                     # la pieza ocupa el panel entero: estirar no la despeja
        new_lo, new_hi = L, L + (v - L) / g
    else:
        if g >= 0.92:
            return np.inf
        new_lo, new_hi = (v - g * H) / (1.0 - g), H
    if not np.isfinite([new_lo, new_hi]).all() or new_hi <= new_lo:
        return np.inf
    factor = (new_hi - new_lo) / (H - L)
    if factor > GROW_CAP:
        return np.inf
    if not log and side in ("bottom", "left") and lo >= 0.0 > new_lo:
        return np.inf                         # un eje de recuentos o de porcentajes no se abre bajo cero
    return max(1.0, factor)


def _no_harm_cap(ax, pts, boxes, side, pad, served) -> float:
    """Hasta dónde se puede estirar por `side` SIN meter la tinta bajo otra pieza del panel.

    Estirar por arriba empuja la serie hacia abajo: si al pie del panel hay una nota que no puede
    despejarse —un eje de porcentajes no se abre bajo cero—, el estiramiento que despeja la leyenda de
    arriba enterraría esa nota. Aquí se mide ese límite y se aplica lo que quepa: hacer sitio a una pieza
    nunca puede quitárselo a otra."""
    if not len(pts):
        return np.inf
    try:
        axb = ax.get_window_extent()
    except (AttributeError, ValueError):
        return np.inf
    cap = np.inf
    for box in boxes:
        if box is served:
            continue
        if side in ("top", "bottom"):
            sel = (pts[:, 0] >= box.x0 - pad) & (pts[:, 0] <= box.x1 + pad)
            near = pts[sel, 1]
        else:
            sel = (pts[:, 1] >= box.y0 - pad) & (pts[:, 1] <= box.y1 + pad)
            near = pts[sel, 0]
        if not len(near):
            continue
        if side == "top" and float(np.min(near)) >= box.y1 + pad:
            cap = min(cap, (float(np.min(near)) - axb.y0) / max(1.0, box.y1 + pad - axb.y0))
        elif side == "bottom" and float(np.max(near)) <= box.y0 - pad:
            cap = min(cap, (axb.y1 - float(np.max(near))) / max(1.0, axb.y1 - box.y0 + pad))
        elif side == "right" and float(np.min(near)) >= box.x1 + pad:
            cap = min(cap, (float(np.min(near)) - axb.x0) / max(1.0, box.x1 + pad - axb.x0))
        elif side == "left" and float(np.max(near)) <= box.x0 - pad:
            cap = min(cap, (axb.x1 - float(np.max(near))) / max(1.0, axb.x1 - box.x0 + pad))
    return max(1.0, cap)


def _apply_grow(ax, side, factor) -> None:
    """Estira el eje conservando el extremo opuesto (y la escala, lineal o logarítmica)."""
    vertical = side in ("top", "bottom")
    lo, hi = ax.get_ylim() if vertical else ax.get_xlim()
    log = (ax.get_yscale() if vertical else ax.get_xscale()) == "log"
    L, H = (np.log10(lo), np.log10(hi)) if log else (lo, hi)
    span = (H - L) * factor
    L2, H2 = (L, L + span) if side in ("top", "right") else (H - span, H)
    new = (10.0 ** L2, 10.0 ** H2) if log else (L2, H2)
    if vertical:
        ax.set_ylim(*new)
    else:
        ax.set_xlim(*new)


def _room_cost(group, pts, box, pad, band=None, sides=None) -> tuple:
    """Lado más barato para dejar `box` sobre banda vacía, y su coste (0 = ya está libre).

    `band` es el recuadro que se reserva al estirar hacia arriba o hacia abajo. Para una leyenda es la
    FRANJA ENTERA del panel a esa altura, no solo su columna: el motor de composición compartido reordena
    las leyendas al final —cuenta como tinta la banda de la pandemia, que esta lámina considera contexto—,
    y una franja libre de lado a lado deja el panel limpio se quede la leyenda a la izquierda o a la
    derecha."""
    allowed = tuple(sides) if sides else tuple(GROW_SIDES)
    best, best_cost = None, np.inf
    for tier in (("top", "bottom"), ("right", "left")):
        for side in tier:
            if side not in allowed:
                continue
            room = (band if band is not None else box) if side in ("top", "bottom") else box
            factors = [_grow_factor(ax, pts[id(ax)], room, side, pad) for ax in group]
            worst = max(factors) if factors else np.inf
            if not np.isfinite(worst):
                continue
            if worst <= 1.0:
                return None, 0.0              # la pieza ya está sobre banda vacía: no se toca nada
            cost = (worst - 1.0) * GROW_SIDES[side]
            if cost < best_cost:
                best, best_cost = side, cost
        if best is not None:
            return best, best_cost            # estirar en vertical antes que en horizontal
    return best, best_cost


def make_room(fig, rounds: int = 4, pad_pt: float = GROW_PAD_PT, move: bool = True) -> None:
    """Ensancha cada panel hasta que ninguna leyenda ni nota quede sobre la tinta de sus datos.

    Se mide la lámina ya dibujada: para cada pieza se calcula, lado a lado, cuánto habría que estirar el eje
    para que la tinta salga de su recuadro, y se aplica el estiramiento más barato (arriba antes que abajo:
    un eje de recuentos no se abre bajo cero). Cuando ningún estiramiento la despeja —una nota al pie de un
    eje de porcentajes, que no puede abrirse bajo cero— la nota busca otra altura del panel, siempre sin
    montarse sobre la leyenda ni sobre otra nota. Los ejes gemelos se estiran a la vez, cada uno con el
    factor que pide su propia serie, de modo que las dos escalas siguen siendo legibles y ninguna miente.
    """
    for _ in range(rounds):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        pad = pad_pt * fig.dpi / 72.0
        changed = False
        for group in _plate_groups(fig):
            pieces = [q for ax in group for q in _panel_pieces(ax, r)]
            if not pieces:
                continue
            pts = {id(ax): _ink_points(ax) for ax in group}
            if not any(len(q) for q in pts.values()):
                continue
            axb = _extent(group[0], r)
            if axb is None:
                continue
            pieces.sort(key=lambda q: -q["box"].width * q["box"].height)
            placed, need, served = [], {}, {}
            for piece in pieces:
                box = piece["box"]
                band = _band_box(axb, box) if not piece["movable"] else None
                side, cost = _room_cost(group, pts, box, pad, band, piece["sides"])
                cands = [(cost + 20.0 * sum(_over(box, q) for q in placed) / max(1.0, box.width * box.height),
                          side, box, band, None)]
                if move and piece["movable"] and cost > 0.0:
                    x, y0 = piece["art"].get_position()
                    for y, va in NOTE_ANCHORS:
                        cand = _anchor_box(axb, box, y, va)
                        c_side, c_cost = _room_cost(group, pts, cand, pad, None, piece["sides"])
                        c_cost += 20.0 * sum(_over(cand, q) for q in placed) / max(1.0, box.width * box.height)
                        c_cost += 0.25 * abs(y - float(y0))          # a igualdad, se queda donde estaba
                        cands.append((c_cost, c_side, cand, None, (x, y, va)))
                cost, side, box, band, anchor = min(cands, key=lambda q: q[0])
                if anchor is not None and (anchor[1], anchor[2]) != (piece["art"].get_position()[1],
                                                                     piece["art"].get_va()):
                    piece["art"].set_position((anchor[0], anchor[1]))
                    piece["art"].set_va(anchor[2])
                    changed = True
                placed.append(box)
                if side is None:
                    continue
                room = (band if band is not None else box) if side in ("top", "bottom") else box
                for ax in group:
                    f = _grow_factor(ax, pts[id(ax)], room, side, pad)
                    if np.isfinite(f) and f > 1.001:
                        need[(id(ax), side)] = max(need.get((id(ax), side), 1.0), f)
                        served.setdefault((id(ax), side), []).append(room)
            for ax in group:
                for side in GROW_SIDES:
                    f = need.get((id(ax), side))
                    if not f:
                        continue
                    mine = served.get((id(ax), side), [])
                    cap = min(_no_harm_cap(ax, pts[id(ax)], placed, side, pad, q) for q in mine)
                    f = min(f, cap)
                    if f > 1.001:
                        _apply_grow(ax, side, f)
                        changed = True
        if not changed:
            return
    fig.canvas.draw()


def _plate_groups(fig) -> list:
    """Ejes agrupados por rectángulo: un panel con eje gemelo es UN panel, y se estira entero."""
    groups: dict = {}
    for ax in fig.axes:
        if not ax.get_visible() or getattr(ax, "_colorbar", None) is not None:
            continue
        pos = ax.get_position()
        if pos.width <= 0 or pos.height <= 0:
            continue
        groups.setdefault((round(pos.x0, 4), round(pos.y0, 4), round(pos.x1, 4), round(pos.y1, 4)), []).append(ax)
    return list(groups.values())


def _siblings(fig, ax) -> list:
    """Los demás ejes que ocupan el mismo rectángulo (el gemelo de un panel con dos escalas)."""
    pos = ax.get_position()
    key = (round(pos.x0, 4), round(pos.y0, 4), round(pos.x1, 4), round(pos.y1, 4))
    out = []
    for other in fig.axes:
        if other is ax or not other.get_visible():
            continue
        q = other.get_position()
        if (round(q.x0, 4), round(q.y0, 4), round(q.x1, 4), round(q.y1, 4)) == key:
            out.append(other)
    return out


def _push_title(ax, extra_pt: float) -> None:
    """Sube el título de panel `extra_pt` puntos conservando cuerpo, peso, color, alineación y posición."""
    t = next((c for c in (getattr(ax, "_left_title", None), ax.title, getattr(ax, "_right_title", None))
              if c is not None and c.get_text()), None)
    if t is None:
        return
    pad = float(getattr(ax, "_pl_title_pad", plt.rcParams.get("axes.titlepad", 4.0))) + float(extra_pt)
    ax._pl_title_pad = pad
    loc = "center"
    if t is getattr(ax, "_left_title", None):
        loc = "left"
    elif t is getattr(ax, "_right_title", None):
        loc = "right"
    ax.set_title(t.get_text(), loc=loc, pad=pad, fontsize=t.get_size(), fontweight=t.get_fontweight(),
                 color=t.get_color(), x=t.get_position()[0])


def fit_ylabels(fig) -> None:
    """El rótulo del eje Y que no cabe a la izquierda de sus marcas se escribe en horizontal sobre el panel.

    Causa del defecto que el informe señaló en S19 (d), S21 (d) y (f) y S25 (a): el rótulo girado no cabe en
    la celda —la columna de marcas se lo come—, la guarda de recorte lo devuelve dentro y aterriza encima de
    las propias marcas que rotula. Escrito como una línea horizontal corta sobre el panel cabe, se lee sin
    girar la cabeza y deja la columna de marcas libre; el título del panel se sube lo justo para hacerle
    sitio. La información no se pierde ni se abrevia: es el mismo rótulo, en otra orientación.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax in list(fig.axes):
        if not ax.get_visible() or not getattr(ax, "axison", True) or not ax.yaxis.get_visible():
            continue
        lbl = ax.yaxis.label
        txt = " ".join(str(lbl.get_text()).split())
        if not txt:
            continue
        b = _extent(lbl, r)
        if b is None:
            continue
        cell = C.plate_cell_box(fig, ax)
        right = ax.yaxis.get_label_position() == "right"
        out = (b.x1 - (cell.x1 - 1.0)) if right else ((cell.x0 + 1.0) - b.x0)
        # Dos síntomas de la misma causa: el rótulo no cabe en la columna que le deja su celda. O se sale de
        # la celda (y la guarda de recorte lo devuelve dentro, encima de las marcas), o ya está tocando sus
        # propias marcas. En los dos casos la solución es la misma: escribirlo en horizontal sobre el panel.
        touch = max((min(b.x1, q.x1) - max(b.x0, q.x0) for q in
                     (_extent(lab, r) for lab in ax.yaxis.get_ticklabels() if lab.get_visible()
                      and str(lab.get_text()).strip())
                     if q is not None and min(b.y1, q.y1) - max(b.y0, q.y0) > 0.0), default=-1.0)
        if out <= 0.5 and touch <= 0.0:
            continue
        # El hueco es generoso a propósito: el título de panel se pliega en dos líneas en español y, con la
        # separación mínima, la línea baja del título y el rótulo horizontal se rozaban (S25 (a)).
        t = C.plate_ylabel(ax, txt, right=right, above=True, gap_pt=5.0, fontsize=FS_BASE,
                           color=lbl.get_color())
        t.set_gid(C.PLATE_KEEP)          # es mobiliario del eje, no una nota: su sitio ya está medido
        # El rótulo del eje DERECHO vive en el eje gemelo, que no tiene título: quien tiene que subir para
        # dejarle sitio es el título del panel, que está en el eje principal (defecto de S25 (a), donde el
        # rótulo horizontal se imprimía sobre la segunda línea del título).
        own = next((c for c in (getattr(ax, "_left_title", None), ax.title, getattr(ax, "_right_title", None))
                    if c is not None and c.get_text()), None)
        if own is None:
            b = _extent(t, r)
            extra = (b.height * 72.0 / fig.dpi + 5.0) if b is not None else FS_BASE + 5.0
            for sib in _siblings(fig, ax):
                _push_title(sib, extra)
        fig.canvas.draw()
        r = fig.canvas.get_renderer()


def separate_wrapped_ticks(fig, gap_pt: float = 1.4) -> None:
    """Deja un blanco visible ENTRE categorías cuando el rótulo de una ocupa dos líneas.

    Con la interlínea por omisión (1,2) un rótulo de dos líneas mide 2,2 em; en un eje de trece categorías
    el paso entre filas es de unos 13,8 pt y a 6,4 pt de cuerpo esas dos líneas miden 14,1: la segunda línea
    de una categoría quedaba pegada a la primera de la siguiente y la columna de rótulos se leía como un
    bloque continuo de texto (defecto de S20 (c) y S23 (a)). Aquí se aprieta la interlínea DENTRO del
    rótulo y, si aún no cabe, se baja el cuerpo hasta el mínimo de la norma, de modo que el blanco entre
    categorías sea siempre mayor que el blanco entre las dos líneas de una misma categoría."""
    fig.canvas.draw()
    for ax in fig.axes:
        labs = [t for t in ax.yaxis.get_ticklabels() if t.get_visible() and str(t.get_text()).strip()]
        if len(labs) < 2 or not any("\n" in str(t.get_text()) for t in labs):
            continue
        locs = list(ax.yaxis.get_ticklocs())
        if len(locs) < 2:
            continue
        y0, y1 = ax.get_ylim()
        span = abs(y1 - y0)
        if span <= 0:
            continue
        height_pt = ax.get_window_extent().height * 72.0 / fig.dpi
        pitch = abs(locs[1] - locs[0]) / span * height_pt
        for t in labs:
            n = str(t.get_text()).count("\n") + 1
            if n < 2:
                continue
            t.set_linespacing(1.05)
            size = float(t.get_size())
            while size > C.PLATE_FS_FLOOR and size * (1.0 + 1.05 * (n - 1)) > pitch - gap_pt:
                size = max(C.PLATE_FS_FLOOR, size - 0.2)
                t.set_size(size)
    fig.canvas.draw()


def save_plate(fig, path: Path):
    """Guarda a 600 ppp SIN recorte: el archivo mide exactamente 180 × 245 mm y se inserta a escala 1:1."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # LA RAYA DEL INTERVALO, PRIMERO (fase 4j, tarea J2). Este módulo era uno de los cuatro que dibujan
    # láminas y no aplicaban la regla: la EF7 rotulaba «0-4» … «75-79» en las mismas caras en las que la
    # EF2 titulaba «Median and P25–P75» con raya, 376 intervalos con guion frente a 152 con raya en sus
    # cuatro combinaciones. La regla es la única del estudio (`common.range_dash`) y `common` la aplica
    # sola al principio de `plate_resolve`; se ADELANTA aquí para que el texto ya esté en su forma
    # definitiva cuando `make_room` y `separate_wrapped_ticks` midan, porque una marca crece ~1,5 pt al
    # pasar de guion a raya. Es idempotente: la pasada de `plate_resolve` no encuentra nada detrás.
    C.plate_range_dash(fig)
    # Motor de descongestión (common.py): mide lo dibujado y resuelve colisiones, recortes y leyendas.
    # `plate_fit` actúa con la composición todavía viva (marcas de eje, rótulos de eje, leyendas);
    # `plate_resolve`, ya congelada, separa los rótulos que se pisan y devuelve dentro lo que se sale.
    C.plate_frame_notes(fig)
    # El verificador de `common.py` se dispara al final de `plate_resolve`; aquí se adelanta la marca para
    # que mire el estado DEFINITIVO —después del último ensanchado— y no uno intermedio. La lámina se
    # comprueba igual, una sola vez, justo antes de escribirse.
    fig._plate_checked = True
    C.plate_resolve(fig)
    # El motor de composición reordena leyendas y notas con su propio mapa de tinta, que cuenta la banda de
    # la pandemia como si fuera dato (para esta lámina es contexto, y la norma del estudio prohíbe leerla
    # como intervención). Por eso, después de que el motor decida, se vuelve a ensanchar el panel hasta que
    # lo que haya colocado quede sobre banda vacía: estirar un eje no mueve ningún texto, de modo que la
    # colocación del motor se respeta entera y solo se le hace sitio.
    make_room(fig, rounds=3, move=False)
    lang = getattr(fig, "_study_lang", "es")
    localise_ticks(fig, lang)
    separate_wrapped_ticks(fig)
    # `localise_ticks` reinstala el formateador de los ejes numéricos: la regla se vuelve a pasar DESPUÉS,
    # o un eje recién reformateado volvería a escribir el guion. No mueve nada si ya está puesta.
    C.plate_range_dash(fig)
    C.plate_check(fig, path.name)
    # Las dos comprobaciones de esta fase, sobre la lámina YA dibujada y en el estado en que se guarda.
    # Ninguna corrige nada: si una letra se separó de su título o un eje escribe el decimal del otro
    # idioma, la lámina no se escribe.
    fig.canvas.draw()
    faults = letters_off_their_titles(fig) + numbers_against_the_language(fig, lang)
    if faults:
        raise AssertionError(f"{path.name}: " + "; ".join(faults))
    # Modo revista (PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    fig.savefig(path, dpi=600, facecolor="white")
    return path


def context(ax, lang, law=True, pandemic=True, law_pos=0.97, pandemic_pos=0.97, fs=FS_TICK, shade=None):
    """Sombreado 2020–2021 (disrupción del reporte) y marca de la Ley 21.545 como contexto, nunca como intervención."""
    years = PANDEMIC if shade is None else shade
    C.shade_years(ax, years)
    if pandemic:
        ax.text(float(np.mean(years)), pandemic_pos, T("pandemic", lang), transform=ax.get_xaxis_transform(),
                ha="center", va="bottom" if pandemic_pos < 0.5 else "top", fontsize=fs, color="#555555",
                bbox=CTX_BBOX, zorder=6)
    if law:
        ax.axvline(LAW_X, color="#444444", ls=":", lw=1.2, zorder=1)
        ax.text(LAW_X + 0.06, law_pos, T("law_short", lang), transform=ax.get_xaxis_transform(), ha="left",
                va="bottom" if law_pos < 0.5 else "top", fontsize=fs, color="#444444",
                bbox=CTX_BBOX, zorder=6)


def headroom(ax, frac: float = 0.30, axis: str = "y") -> None:
    """Amplía el extremo del eje donde se dibuja la leyenda para que no quede encima de la serie."""
    if axis == "x":
        lo, hi = ax.get_xlim()
        if ax.get_xscale() == "log":
            if lo > 0 and hi > lo:
                ax.set_xlim(lo, hi * (hi / lo) ** frac)
        elif hi > lo:
            ax.set_xlim(lo, hi + (hi - lo) * frac)
        return
    lo, hi = ax.get_ylim()
    if ax.get_yscale() == "log":
        if lo > 0 and hi > lo:
            ax.set_ylim(lo, hi * (hi / lo) ** frac)
    elif hi > lo:
        ax.set_ylim(lo, hi + (hi - lo) * frac)


def legend_wrapped(ax, *args, width: int = 24, expand=None, expand_axis: str = "y", **kw):
    """Leyenda pensada para una celda estrecha: los rótulos largos se parten en líneas, nunca se reduce el cuerpo.

    En una celda de 88 mm de ancho una leyenda de una sola línea larga se sale del panel o tapa la serie. Aquí el
    rótulo se parte en varias líneas —el cuerpo se mantiene en los 7 pt de la norma— y, cuando la leyenda se coloca
    en la mitad superior (o se deja a criterio de matplotlib), el eje se estira lo justo para que la leyenda tenga
    su propio espacio en blanco en vez de taparle la serie al lector.
    """
    if len(args) >= 2:
        handles, labels, args = args[0], args[1], args[2:]
    else:
        handles, labels, args = (*ax.get_legend_handles_labels(), ())
    labels = [textwrap.fill(str(t), width) for t in labels]
    kw.setdefault("fontsize", FS_LEG)
    title = kw.get("title")
    if title:
        kw.setdefault("title_fontsize", FS_LEG)
        kw["title"] = textwrap.fill(str(title), width + 8)
    kw.setdefault("borderpad", 0.28)
    kw.setdefault("labelspacing", 0.3)
    loc = kw.get("loc", "best")
    if expand is None:
        expand = isinstance(loc, str) and (loc.startswith("upper") or loc == "best")
    if expand:
        ncol = int(kw.get("ncol", 1)) or 1
        rows = -(-len(labels) // ncol)
        lines = max(rows, sum(str(t).count("\n") + 1 for t in labels) // ncol)
        lines += (str(kw.get("title", "")).count("\n") + 1) if kw.get("title") else 0
        headroom(ax, min(0.62, 0.030 + 0.062 * lines), axis=expand_axis)
    return ax.legend(handles, labels, *args, **kw)


XLABEL_W_PT = 150.0       # ancho útil de la nota bajo un panel de la celda vertical


def long_xlabel(ax, text: str, width: int | None = None, fontsize: float = FS_ANN) -> None:
    """Etiqueta del eje X con nota metodológica, ajustada por ancho medido al área de ejes de la celda.

    Contar caracteres dejaba la nota más ancha que el panel y el texto se salía del lienzo por la izquierda;
    midiéndola con su propia fuente, la nota queda siempre dentro de su celda en los dos idiomas.
    """
    ax.set_xlabel(wrap_measured(text, XLABEL_W_PT, fontsize, "normal"), fontsize=fontsize)


def year_axis(ax, lang, years=None):
    years = YEARS if years is None else years
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_xlabel(T("year", lang))


def heat(ax, mat: pd.DataFrame, fmt_cell, cmap="YlGnBu", fontsize=FS_ANN, ylabels=None, xlabels=None,
         cbar_label="", fig=None, vmin=None, vmax=None):
    data = mat.to_numpy(dtype=float)
    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(mat.shape[1]))
    ax.set_xticklabels(xlabels if xlabels is not None else [str(c) for c in mat.columns], fontsize=FS_BASE)
    ax.set_yticks(range(mat.shape[0]))
    ax.set_yticklabels(ylabels if ylabels is not None else [str(i) for i in mat.index], fontsize=FS_TICK)
    ax.grid(False)
    finite = data[np.isfinite(data)]
    lo = float(np.nanmin(finite)) if vmin is None and finite.size else (vmin if vmin is not None else 0.0)
    hi = float(np.nanmax(finite)) if vmax is None and finite.size else (vmax if vmax is not None else 1.0)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = data[i, j]
            if not np.isfinite(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=fontsize, color="#777777")
                continue
            shade = (v - lo) / (hi - lo) if hi > lo else 0.0     # el texto se aclara solo sobre celdas oscuras
            ax.text(j, i, fmt_cell(v), ha="center", va="center", fontsize=fontsize,
                    color="white" if shade > 0.62 else "#1a1a1a")
    if fig is not None:
        cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.015)
        cb.ax.tick_params(labelsize=FS_TICK)
        if cbar_label:
            cb.set_label(cbar_label, fontsize=FS_TICK)
    return im


def hbars_compare(ax, labels, share_f84, share_all, lang, colour=None, show_diff=True, fontsize=FS_TICK,
                  legend=True, legend_loc="lower right"):
    """Barras horizontales pareadas: % entre episodios con F84 frente a % entre todos los episodios GRD.

    En la celda vertical de esta fase las barras van ordenadas de mayor a menor, de modo que el vértice inferior
    derecho queda libre y la leyenda cabe ahí sin tapar ninguna barra; `legend=False` deja el panel sin leyenda
    cuando la lámina ya la lleva en otro panel.
    """
    colour = colour or COL["f84"]
    y = np.arange(len(labels))
    ax.barh(y - 0.2, share_f84, height=0.38, color=colour, label=T("episodes_f84", lang))
    ax.barh(y + 0.2, share_all, height=0.38, color=COL["all"], alpha=0.85, label=T("all_episodes", lang))
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=fontsize)
    ax.invert_yaxis()
    ax.set_xlabel(T("pct_episodes", lang))
    if show_diff:
        span = max(list(share_f84) + list(share_all) + [1.0])
        for i, (a, b) in enumerate(zip(share_f84, share_all)):
            d = a - b
            ax.text(max(a, b) + span * 0.02, i, f"{'+' if d >= 0 else '−'}{num(abs(d), 1, lang)}",
                    va="center", fontsize=FS_ANN, color="#333333")
        ax.set_xlim(0, span * 1.24)
    if legend:
        legend_wrapped(ax, loc=legend_loc, expand=False, width=20, frameon=True, framealpha=0.92, edgecolor="none")


# ===========================================================================
# Escritura de salidas
# ===========================================================================
def out_dirs(variant: str, lang: str) -> tuple[Path, Path]:
    fdir = CFG.OUT / variant / lang / "extra" / "figures"
    tdir = CFG.OUT / variant / lang / "extra" / "tables"
    fdir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)
    return fdir, tdir


def merge_json(path: Path, new: dict) -> None:
    """Fusiona con el JSON existente sin borrar las entradas de otros módulos."""
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


def write_table(tdir: Path, name: str, formatted: pd.DataFrame, numeric: pd.DataFrame) -> list[str]:
    return [str(C.atomic_write_csv(formatted, tdir / f"{name}.csv", encoding="utf-8-sig")),
            str(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv"))]


# --- Notas y encabezados comunes de todas las salidas -------------------------------------------
SOURCE_GRD = {"es": "GRD_PUBLICO_2019..2024.csv (FONASA/MINSAL), vía outputs/tidy/ del módulo 11",
              "en": "GRD_PUBLICO_2019..2024.csv (FONASA/MINSAL), through outputs/tidy/ of module 11"}
NOTE_CORE = {
    "es": ("Unidad: episodio GRD (hospitalización, cirugía mayor ambulatoria u otra modalidad). Los recuentos son "
           "reconocimiento administrativo (episodios con F84 documentado), nunca prevalencia, incidencia ni "
           "«hospitalizaciones por autismo»; F84 principal es una serie separada. Denominador: episodios GRD del mismo "
           "año, panel y actividad. Cobertura: hospitales públicos con GRD; panel observado de 65, 65, 65, 65, 68 y 72 "
           f"hospitales en 2019–2024 y panel fijo de 65 {C.fixed_panel_gloss('es', 'paren')}. Era de definición: familia F84 de la "
           "CIE-10 en 35 posiciones diagnósticas, sin cambios en 2019–2024. 2020–2021: disrupción del reporte por la "
           "pandemia; la Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con efecto estimable. "
           "Las personas se cuentan solo dentro del año o de la era de identificador (el formato cambia entre 2020 y "
           "2021). Cero, ausente y «no informado» son estados distintos; «n/e» = no estimable."),
    "en": ("Unit: GRD episode (hospitalisation, major ambulatory surgery or another modality). Counts are administrative "
           "recognition (episodes with documented F84), never prevalence, incidence or 'hospitalisations for autism'; "
           "principal F84 is a separate series. Denominator: GRD episodes of the same year, panel and activity. Coverage: "
           "public hospitals with GRD; observed panel of 65, 65, 65, 65, 68 and 72 hospitals in 2019–2024 and fixed panel "
           f"of 65 {C.fixed_panel_gloss('en', 'paren')}. Definition era: ICD-10 F84 family across 35 diagnostic positions, unchanged in "
           "2019–2024. 2020–2021: pandemic reporting disruption; Law 21.545 (March 2023) is policy context, not an "
           "intervention with an estimable effect. Persons are counted only within a year or identifier era (the format "
           "changes between 2020 and 2021). Zero, missing and 'not reported' are distinct states; 'n/e' = not estimable."),
}


def variant_label(variant: str, lang: str) -> str:
    return CFG.VARIANTS[variant]["label"][lang]


def plate_title(nplate: str, key: str, variant: str, lang: str) -> str:
    head = {"es": "Lámina", "en": "Plate"}[lang]
    return f"{head} {nplate}. {T(key, lang)} — {variant_label(variant, lang)}"


def table_title(nplate: str, key: str, variant: str, lang: str) -> str:
    head = {"es": "Tabla acompañante de la lámina", "en": "Companion table of plate"}[lang]
    return f"{head} {nplate}. {T(key, lang)} — {variant_label(variant, lang)}"


def source_line(files: str, lang: str) -> str:
    return {"es": f"Archivos fuente: {files}.", "en": f"Source files: {files}."}[lang]


# ===========================================================================
# Controles de reproducción
# ===========================================================================
class Controls:
    """name,key,expected,observed,abs_diff,rel_diff,status,note (mismo formato que el resto del pipeline)."""

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, name: str, key, expected, observed, note: str = "", tol: float = 1e-9, status: str | None = None) -> None:
        abs_diff = rel_diff = ""
        if status is None:
            try:
                e, o = float(expected), float(observed)
                abs_diff = o - e
                rel_diff = (o - e) / e if e else ""
                status = "ok" if abs(abs_diff) <= tol else "differs"
            except (TypeError, ValueError):
                status = "ok" if str(expected) == str(observed) else "differs"
        self.rows.append(dict(name=name, key=key, expected=expected, observed=observed, abs_diff=abs_diff,
                              rel_diff=rel_diff, status=status, note=note))

    def info(self, name: str, key, observed, note: str = "") -> None:
        self.rows.append(dict(name=name, key=key, expected="", observed=observed, abs_diff="", rel_diff="",
                              status="info", note=note))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff",
                                                "status", "note"])


def finish(fig, name: str, fdir: Path, tdir: Path, formatted: pd.DataFrame, numeric: pd.DataFrame, lang: str,
           cap_title: str, caption: str, tab_title: str, note: str) -> dict:
    # Orden deliberado. 1) Las notas dejan de competir por el reparto del espacio. 2) Se les pone recuadro y
    # se pliegan al ancho de su panel ANTES de medir nada: una nota más ancha que el panel crece hacia abajo
    # al plegarse y volvería a caer sobre la serie. 3) Se fijan los separadores de millares, porque el ancho
    # de la columna de marcas decide si el rótulo del eje Y cabe en su celda. 4) Los rótulos del eje que no
    # caben pasan a escribirse en horizontal sobre el panel. 5) Con la geometría ya definitiva se ensancha
    # cada panel hasta que ninguna pieza quede sobre la tinta. 6) Se revisan los decimales de las marcas,
    # que el ensanchado puede haber cambiado.
    fig._study_lang = lang
    detach_annotations(fig)
    C.plate_frame_notes(fig)
    localise_ticks(fig, lang)
    wrap_axis_labels(fig)
    fit_ylabels(fig)
    make_room(fig)
    localise_ticks(fig, lang)
    # Segunda pasada: ensanchar un panel cambia el ancho de la columna de marcas de TODA la lámina (el
    # reparto sigue vivo), de modo que un rótulo de eje que cabía en su celda puede haber dejado de caber.
    # Lo que quede por resolver se resuelve con el mismo criterio, y el último ensanchado (en `save_plate`)
    # vuelve a comprobar que nada quede sobre la tinta.
    fit_ylabels(fig)
    align_panel_titles(fig)
    path = save_plate(fig, fdir / f"{name}.png")
    plt.close(fig)
    tables = write_table(tdir, name, formatted, numeric)
    return {"figure": str(path), "tables": tables,
            "captions": {name: {"title": cap_title, "caption": caption}},
            "titles": {name: {"title": tab_title, "note": note}}}


def month_axis(ax, lang):
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(T("months_short", lang).split("|"), fontsize=FS_BASE)
    ax.set_xlabel(T("month", lang))


def context_decimal(ax, lang, law=True, pandemic=True, fs=FS_TICK):
    """Contexto sobre un eje decimal de años (series mensuales): 2020–2021 completos y marca de la ley."""
    ax.axvspan(2020.0, 2022.0, color="grey", alpha=0.12, zorder=0)
    if pandemic:
        ax.text(2021.0, 0.97, T("pandemic", lang), transform=ax.get_xaxis_transform(), ha="center", va="top",
                fontsize=fs, color="#555555", bbox=CTX_BBOX, zorder=6)
    if law:
        x = CFG.LAW_YEAR + 2.5 / 12
        ax.axvline(x, color="#444444", ls=":", lw=1.2, zorder=1)
        ax.text(x + 0.06, 0.97, T("law_short", lang), transform=ax.get_xaxis_transform(), ha="left", va="top",
                fontsize=fs, color="#444444", bbox=CTX_BBOX, zorder=6)


# ===========================================================================
# EF1 · Estacionalidad y serie mensual
# ===========================================================================
def ef1(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF1_seasonality_monthly"
    m = D.monthly
    sel = m.loc[(m.variant == variant) & (m.position == "any") & (m.panel == "observed")].copy()
    mm = sel.loc[sel.month > 0].copy()
    unknown = sel.loc[sel.month == 0].set_index("year")

    # control: la suma de los meses reproduce el total anual verificado
    ys = D.year
    for y in YEARS:
        exp = float(ys.loc[(ys.year == y) & (ys.variant == variant) & (ys.panel == "observed") &
                           (ys.activity == "all") & (ys.position == "any"), "n_episodes_f84"].iloc[0])
        obs = float(sel.loc[sel.year == y, "n_episodes_f84"].sum())
        ctl.add(f"EF1_monthly_sum_equals_annual[{variant}]", y, exp, obs,
                "grd_monthly (meses 0–12) frente a grd_year_summary (panel observado, cualquier posición, todas las actividades)")

    disp = []
    for y in YEARS:
        f = mm.loc[mm.year == y, "n_episodes_f84"].to_numpy(dtype=float)
        t = mm.loc[mm.year == y, "n_episodes_total"].to_numpy(dtype=float)
        disp.append(dict(year=y,
                         dispersion_f84=float(np.var(f, ddof=1) / np.mean(f)) if f.size and np.mean(f) > 0 else np.nan,
                         dispersion_total=float(np.var(t, ddof=1) / np.mean(t)) if t.size and np.mean(t) > 0 else np.nan,
                         n_f84=float(f.sum()), n_total=float(t.sum())))
    disp = pd.DataFrame(disp)

    fig, ax = new_plate()
    # (a) episodios por mes y año
    for i, y in enumerate(YEARS):
        s = mm.loc[mm.year == y].sort_values("month")
        ax[0].plot(s.month, s.n_episodes_f84, marker="o", ms=3.4, lw=1.6, color=YEAR_COLORS[i], label=str(y))
    month_axis(ax[0], lang)
    ax[0].set_ylabel(T("episodes_f84", lang))
    legend_wrapped(ax[0], ncol=3, fontsize=FS_TICK, title=T("year", lang), title_fontsize=FS_LEG, frameon=True, framealpha=0.9,
                 edgecolor="none")
    panel(ax[0], "a", T("ef1_a", lang))

    # (b) tasa mensual por 100.000 episodios sobre eje decimal
    mm["x"] = mm.year + (mm.month - 0.5) / 12
    s = mm.sort_values("x")
    ax[1].fill_between(s.x, s.rate_lo, s.rate_hi, color=COL["f84"], alpha=0.18, lw=0)
    ax[1].plot(s.x, s.rate_per_100k_episodes, lw=1.5, color=COL["f84"])
    ax[1].plot(s.x, s.rate_per_100k_episodes.rolling(12, center=True, min_periods=12).mean(), lw=2.2,
               color=OKABE[1], ls="--")
    context_decimal(ax[1], lang)
    ax[1].set_xticks(YEARS + [2025])
    ax[1].set_xticklabels([str(y) for y in YEARS] + ["2025"])
    ax[1].set_xlabel(T("year", lang))
    ax[1].set_ylabel(T("rate_100k_ep", lang))
    panel(ax[1], "b", T("ef1_b", lang))

    # (c) índice estacional (mes × año)
    idx = mm.pivot_table(index="month", columns="year", values="seasonal_index_f84", aggfunc="first").sort_index()
    heat(ax[2], idx, lambda v: num(v, 2, lang), cmap="RdYlBu_r", fontsize=FS_ANN,
         ylabels=T("months_short", lang).split("|"), fig=fig, cbar_label=T("ef1_c", lang))
    ax[2].set_xlabel(T("year", lang))
    panel(ax[2], "c", T("ef1_c", lang))

    # (d) 2020 y 2021 frente al mismo mes de 2019
    base = mm.loc[mm.year == 2019].set_index("month")
    for i, y in enumerate([2020, 2021]):
        cur = mm.loc[mm.year == y].set_index("month")
        common = base.index.intersection(cur.index)
        r_f84 = (cur.loc[common, "n_episodes_f84"] / base.loc[common, "n_episodes_f84"].replace(0, np.nan))
        r_all = (cur.loc[common, "n_episodes_total"] / base.loc[common, "n_episodes_total"].replace(0, np.nan))
        ax[3].plot(common, r_f84, marker="o", ms=3.4, lw=1.7, color=YEAR_COLORS[i + 1], label=f"{y} · {T('episodes_f84', lang)}")
        ax[3].plot(common, r_all, marker="s", ms=3.0, lw=1.4, ls="--", color=YEAR_COLORS[i + 1], alpha=0.75,
                   label=f"{y} · {T('all_episodes', lang)}")
    ax[3].axhline(1.0, color="#444444", lw=1.0, ls=":")
    month_axis(ax[3], lang)
    ax[3].set_ylabel(T("ef1_ratio", lang))
    legend_wrapped(ax[3], fontsize=FS_ANN, ncol=1, loc="upper left")
    panel(ax[3], "d", T("ef1_d", lang))

    # (e) comparación REM A05 (fuente distinta, eje propio; sin línea entre eras)
    a05 = D.a05_month
    for i, y in enumerate(sorted(a05.year.unique())):
        s = a05.loc[a05.year == y].sort_values("month")
        ax[4].plot(s.month, s.entries, marker="o", ms=3.2, lw=1.5, color=YEAR_COLORS[i % len(YEAR_COLORS)], label=str(y))
    month_axis(ax[4], lang)
    ax[4].set_ylabel(T("ef1_a05_axis", lang))
    legend_wrapped(ax[4], ncol=3, fontsize=FS_TICK, title=T("ef1_a05", lang), title_fontsize=FS_LEG)
    note_in_panel(ax[4], T("ef1_sep_axis", lang), 0.02, 0.02, fontsize=FS_TICK)
    # Todo panel REM declara cuántos establecimientos reportan el código: el numerador depende de la cobertura del reporte.
    estab = a05.groupby("year").n_establishments.agg(["median", "min", "max"])
    estab_txt = "; ".join(f"{int(y)}: {num(r['median'], 0, lang)} ({num(r['min'], 0, lang)}–{num(r['max'], 0, lang)})"
                          for y, r in estab.iterrows())
    long_xlabel(ax[4], {"es": f"{T('month', lang)} — establecimientos REM que reportan el código, mediana mensual (mín.–máx.): {estab_txt}",
                        "en": f"{T('month', lang)} — REM establishments reporting the code, monthly median (min.–max.): {estab_txt}"}[lang],
                width=86, fontsize=FS_ANN)
    panel(ax[4], "e", T("ef1_e", lang))

    # (f) índice de dispersión
    w = 0.38
    ax[5].bar(np.array(YEARS) - w / 2, disp.dispersion_f84, width=w, color=COL["f84"], label=T("episodes_f84", lang))
    ax[5].bar(np.array(YEARS) + w / 2, disp.dispersion_total, width=w, color=COL["all"], label=T("all_episodes", lang))
    ax[5].axhline(1.0, color="#444444", ls=":", lw=1.1)
    ax[5].text(0.015, 0.02, T("ef1_poisson", lang), transform=ax[5].transAxes, fontsize=FS_TICK, color="#444444",
               va="bottom", ha="left", bbox=CTX_BBOX, zorder=6)
    ax[5].set_yscale("log")
    year_axis(ax[5], lang)
    ax[5].set_ylabel(T("ef1_disp", lang))
    legend_wrapped(ax[5], fontsize=FS_TICK, loc="upper left")
    panel(ax[5], "f", T("ef1_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    months = T("months_short", lang).split("|")
    month_names = {"es": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                          "Octubre", "Noviembre", "Diciembre"],
                   "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                          "October", "November", "December"]}[lang]
    for k in range(1, 13):
        r = {"__k": month_names[k - 1]}
        for y in YEARS:
            c = mm.loc[(mm.year == y) & (mm.month == k)]
            r[str(y)] = (f"{num(c.n_episodes_f84.iloc[0], 0, lang)} ({num(c.rate_per_100k_episodes.iloc[0], 1, lang)})"
                         if len(c) else T("not_estimable", lang))
        rows.append(r)
    r = {"__k": T("unknown_month", lang)}
    for y in YEARS:
        r[str(y)] = num(unknown.loc[y, "n_episodes_f84"] if y in unknown.index else 0, 0, lang)
    rows.append(r)
    r = {"__k": T("total", lang)}
    for y in YEARS:
        r[str(y)] = num(sel.loc[sel.year == y, "n_episodes_f84"].sum(), 0, lang)
    rows.append(r)
    for key, col in ((T("ef1_disp", lang) + f" · {T('episodes_f84', lang)}", "dispersion_f84"),
                     (T("ef1_disp", lang) + f" · {T('all_episodes', lang)}", "dispersion_total")):
        r = {"__k": key}
        for y in YEARS:
            r[str(y)] = num(disp.loc[disp.year == y, col].iloc[0], 2, lang)
        rows.append(r)
    r = {"__k": T("ef1_a05", lang)}
    for y in YEARS:
        v = a05.loc[a05.year == y, "entries"].sum() if (a05.year == y).any() else np.nan
        r[str(y)] = num(v, 0, lang) if (a05.year == y).any() else T("not_estimable", lang)
    rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": T("month", lang)})
    numeric = pd.concat([
        sel.assign(block="grd_monthly"),
        disp.assign(block="dispersion_index", variant=variant),
        D.a05_month.assign(block="rem_a05_monthly", variant="rem_a05_strict_autism"),
    ], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Episodios GRD con F84 documentado (cualquier posición, panel observado) por mes de ingreso y año. "
               f"(b) Tasa mensual por 100.000 episodios GRD del mismo mes con IC 95 % exactos de Poisson (banda) y media "
               f"móvil de 12 meses (línea discontinua). (c) Índice estacional dentro de cada año (media de los 12 meses "
               f"= 1); los episodios sin fecha de ingreso analizable quedan fuera del índice. (d) Meses de 2020 y 2021 "
               f"frente al mismo mes de 2019, para los episodios con F84 y para todos los episodios GRD (cociente dentro "
               f"de la misma fuente, no entre fuentes). (e) Comparación con la ruta REM: ingresos mensuales al programa "
               f"de salud mental por autismo (código 05990022, era 2021–2025); es otra fuente, con su propio eje y sin "
               f"enlace individual con el GRD, y la era anterior (TGD amplio 2019–2020) no se une con esta línea. "
               f"(f) Índice de dispersión (varianza/media) de los 12 recuentos mensuales de cada año; la línea de "
               f"referencia marca el valor 1 esperado bajo Poisson. Sombreado: disrupción del reporte 2020–2021; línea "
               f"punteada: Ley 21.545 (marzo de 2023) como contexto. Definición: {vl}. Los recuentos son reconocimiento "
               f"administrativo, nunca prevalencia ni incidencia."),
        "en": (f"(a) GRD episodes with documented F84 (any position, observed panel) by month of admission and year. "
               f"(b) Monthly rate per 100,000 GRD episodes of the same month with exact Poisson 95% CIs (band) and a "
               f"12-month moving average (dashed). (c) Within-year seasonal index (mean of the year's 12 months = 1); "
               f"episodes without a parsable admission date are excluded from the index. (d) Months of 2020 and 2021 "
               f"versus the same month of 2019, for episodes with F84 and for all GRD episodes (a ratio within one "
               f"source, never between sources). (e) Comparison with the REM pathway: monthly entries to the mental-health "
               f"programme for autism (code 05990022, era 2021–2025); a different source with its own axis and no "
               f"individual linkage to GRD, and the earlier era (broad PDD 2019–2020) is not joined to this line. "
               f"(f) Index of dispersion (variance/mean) of each year's 12 monthly counts; the reference line marks the "
               f"value 1 expected under Poisson. Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 "
               f"(March 2023) as context. Definition: {vl}. Counts are administrative recognition, never prevalence or "
               f"incidence."),
    }[lang]
    note = {
        "es": ("Celda: episodios con F84 documentado (tasa por 100.000 episodios GRD del mismo mes). Filas finales: total "
               "anual, índice de dispersión de los 12 meses e ingresos anuales REM A05 por autismo (fuente distinta, sin "
               "enlace individual; era 2021–2025, «n/e» antes de 2021). " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_monthly.csv, grd_year_summary.csv y rem_pathway_tidy.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes with documented F84 (rate per 100,000 GRD episodes of the same month). Final rows: annual "
               "total, index of dispersion of the 12 months and annual REM A05 autism entries (a different source with no "
               "individual linkage; era 2021–2025, 'n/e' before 2021). " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_monthly.csv, grd_year_summary.csv and rem_pathway_tidy.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF1", "ef1_title", variant, lang), cap,
                  table_title("EF1", "ef1_title", variant, lang), note)


# ===========================================================================
# EF2 · Estadía hospitalaria
# ===========================================================================
POSITIONS = ["any", "principal", "secondary_only"]
POS_KEY = {"any": "pos_any", "principal": "pos_principal", "secondary_only": "pos_secondary_only", "all": "pos_all"}
COMPARISON = "all_episodes"


def ef2(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF2_length_of_stay"
    los = D.los.loc[D.los.panel == "observed"]
    la = D.los_age.loc[D.los_age.panel == "observed"]

    def series(activity, position, who=None):
        who = who or variant
        s = los.loc[(los.variant == who) & (los.position == position) & (los.activity == activity)]
        return s.sort_values("year")

    # control: episodios con fechas válidas + no válidas = episodios de la celda (grd_year_summary)
    ys = D.year
    for y in YEARS:
        cell = series("all", "any").loc[lambda d: d.year == y]
        exp = float(ys.loc[(ys.year == y) & (ys.variant == variant) & (ys.panel == "observed") &
                           (ys.activity == "all") & (ys.position == "any"), "n_episodes_f84"].iloc[0])
        obs = float(cell.n_valid_dates.iloc[0] + cell.n_invalid_dates.iloc[0]) if len(cell) else np.nan
        ctl.add(f"EF2_los_valid_plus_invalid[{variant}]", y, exp, obs,
                "grd_length_of_stay: n_valid_dates + n_invalid_dates frente a los episodios anuales de grd_year_summary")

    fig, ax = new_plate()
    # (a) mediana e IQR por año y posición (hospitalización)
    for i, position in enumerate(POSITIONS):
        s = series("hospitalisation", position)
        if s.empty:
            continue
        err = np.vstack([(s.median_days - s.q25_days).clip(lower=0), (s.q75_days - s.median_days).clip(lower=0)])
        ax[0].errorbar(s.year + (i - 1) * 0.09, s.median_days, yerr=err, marker="o", ms=4.2, lw=1.6, capsize=2.6,
                       color=COL[position], label=T(POS_KEY[position], lang))
    s = series("hospitalisation", "all", who=COMPARISON)
    err = np.vstack([(s.median_days - s.q25_days).clip(lower=0), (s.q75_days - s.median_days).clip(lower=0)])
    ax[0].errorbar(s.year + 0.27, s.median_days, yerr=err, marker="s", ms=4.0, lw=1.4, capsize=2.6, ls="--",
                   color=COL["all"], label=T("pos_all", lang))
    # Las glosas de contexto van al pie (la mediana sube con los años) y la banda superior queda reservada
    # para la leyenda de cuatro entradas: en español ocupa dos filas y sin la reserva se sentaba sobre la
    # serie de 2019.
    headroom(ax[0], 0.34)
    context(ax[0], lang, pandemic_pos=0.04, law_pos=0.04)
    year_axis(ax[0], lang)
    ax[0].set_ylabel(f"{T('median_iqr', lang)} · {T('days', lang).lower()}")
    legend_wrapped(ax[0], fontsize=FS_TICK, ncol=2, loc="upper left", expand=False,
                   frameon=True, framealpha=0.85, edgecolor="none")
    panel(ax[0], "a", T("ef2_a", lang))

    # (b) por grupo etario: media acumulada y mediana de 2024
    order = [g for g in C.AGE_GROUPS] + ["unknown"]
    rows_b = []
    for g in order:
        f = la.loc[(la.variant == variant) & (la.position == "any") & (la.activity == "hospitalisation") & (la.age_group == g)]
        a = la.loc[(la.variant == COMPARISON) & (la.position == "all") & (la.activity == "hospitalisation") & (la.age_group == g)]
        if f.empty and a.empty:
            continue
        rows_b.append(dict(age_group=g,
                           n_f84=float(f.n_valid_dates.sum()),
                           mean_f84=float(f.total_days.sum() / f.n_valid_dates.sum()) if f.n_valid_dates.sum() > 0 else np.nan,
                           median_f84_2024=float(f.loc[f.year == 2024, "median_days"].iloc[0]) if (f.year == 2024).any() and f.loc[f.year == 2024, "n_valid_dates"].iloc[0] > 0 else np.nan,
                           n_all=float(a.n_valid_dates.sum()),
                           mean_all=float(a.total_days.sum() / a.n_valid_dates.sum()) if a.n_valid_dates.sum() > 0 else np.nan,
                           median_all_2024=float(a.loc[a.year == 2024, "median_days"].iloc[0]) if (a.year == 2024).any() and a.loc[a.year == 2024, "n_valid_dates"].iloc[0] > 0 else np.nan))
    B = pd.DataFrame(rows_b)
    yb = np.arange(len(B))
    ax[1].barh(yb - 0.2, B.mean_f84, height=0.38, color=COL["f84"], label=f"{T('episodes_f84', lang)} · x̄")
    ax[1].barh(yb + 0.2, B.mean_all, height=0.38, color=COL["all"], alpha=0.85, label=f"{T('all_episodes', lang)} · x̄")
    ax[1].plot(B.median_f84_2024, yb - 0.2, "o", ms=4.2, color="#111111", label=f"{T('episodes_f84', lang)} · 2024 med.")
    ax[1].plot(B.median_all_2024, yb + 0.2, "s", ms=3.8, color="#555555", label=f"{T('all_episodes', lang)} · 2024 med.")
    ax[1].set_yticks(yb)
    ax[1].set_yticklabels([g if g != "unknown" else T("not_reported", lang) for g in B.age_group], fontsize=FS_TICK)
    ax[1].invert_yaxis()
    ax[1].set_xlabel(T("days", lang))
    ax[1].set_ylabel(T("age_group", lang))
    legend_wrapped(ax[1], ncol=1, loc="upper right", expand=True, expand_axis="x", width=22,
                   frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[1], "b", T("ef2_b", lang))

    # (c) percentil 90
    for position, marker in (("any", "o"), ("principal", "^")):
        s = series("hospitalisation", position)
        ax[2].plot(s.year, s.p90_days, marker=marker, ms=4.2, lw=1.7, color=COL[position], label=T(POS_KEY[position], lang))
    s = series("hospitalisation", "all", who=COMPARISON)
    ax[2].plot(s.year, s.p90_days, marker="s", ms=4.0, lw=1.5, ls="--", color=COL["all"], label=T("pos_all", lang))
    context(ax[2], lang, pandemic_pos=0.04, law_pos=0.04)
    year_axis(ax[2], lang)
    ax[2].set_ylabel(T("ef2_p90", lang))
    legend_wrapped(ax[2], fontsize=FS_TICK, frameon=True, framealpha=0.85, edgecolor="none")
    panel(ax[2], "c", T("ef2_c", lang))

    # (d) estadía cero
    combos = [("all", variant, "any", COL["f84"], "-", f"{T('episodes_f84', lang)} · {T('act_all', lang).lower()}"),
              ("hospitalisation", variant, "any", COL["hosp"], "-", f"{T('episodes_f84', lang)} · {T('act_hosp', lang).lower()}"),
              ("all", COMPARISON, "all", COL["all"], "--", f"{T('all_episodes', lang)} · {T('act_all', lang).lower()}"),
              ("hospitalisation", COMPARISON, "all", "#4d4d4d", "--", f"{T('all_episodes', lang)} · {T('act_hosp', lang).lower()}")]
    for activity, who, position, colour, ls, lab in combos:
        s = series(activity, position, who=who)
        share = 100 * s.n_los_zero / s.n_valid_dates.replace(0, np.nan)
        ax[3].plot(s.year, share, marker="o", ms=3.8, lw=1.6, ls=ls, color=colour, label=lab)
    context(ax[3], lang, pandemic_pos=0.14, law_pos=0.14)
    year_axis(ax[3], lang)
    ax[3].set_ylabel(T("ef2_zero", lang))
    # Cuatro entradas largas plegadas a 24 caracteres ocupaban doce líneas y la banda que hay que reservarles
    # se comía media celda: al ancho real del panel caben en ocho y la serie recupera su sitio.
    legend_wrapped(ax[3], fontsize=FS_ANN, width=34, loc="upper right", frameon=True, framealpha=0.85,
                   edgecolor="none")
    panel(ax[3], "d", T("ef2_d", lang))

    # (e) tramos de estadía en 2024
    feat = D.feat.loc[(D.feat.panel == "observed") & (D.feat.variable == "los_bin") & (D.feat.year == 2024)]
    f84 = feat.loc[(feat.variant == variant) & (feat.position == "any")].set_index("value")
    alle = feat.loc[feat.variant == COMPARISON].set_index("value")
    bins = ["0", "1", "2", "3-4", "5-7", "8-14", "15-30", "31-90", "91+", "no informado"]
    bins = [b for b in bins if b in f84.index or b in alle.index]
    labels = [cat_label(b, lang) if b == "no informado" else b for b in bins]
    hbars_compare(ax[4], labels,
                  [float(f84.pct_within_cell.get(b, 0.0)) for b in bins],
                  [float(alle.pct_within_cell.get(b, 0.0)) for b in bins], lang)
    ax[4].set_ylabel(T("ef2_los_bin", lang))
    panel(ax[4], "e", T("ef2_e", lang))

    # (f) hospitalización frente a CMA
    w = 0.38
    hosp = series("hospitalisation", "any")
    cma = series("cma", "any")
    ax[5].bar(hosp.year - w / 2, hosp.n_episodes_cell, width=w, color=COL["hosp"], label=T("act_hosp", lang))
    ax[5].bar(cma.year + w / 2, cma.n_episodes_cell, width=w, color=COL["cma"], label=T("act_cma", lang))
    ax[5].set_ylabel(T("episodes_f84", lang))
    ax2 = ax[5].twinx()
    # Cada actividad tiene su propia línea de mediana de días y ambas se rotulan: la de CMA es cero por definición.
    ax2.plot(hosp.year, hosp.median_days, marker="o", ms=4.0, lw=1.6, color="#1a1a1a",
             label=f"{T('ef2_median_days', lang)} · {T('act_hosp', lang).lower()}")
    ax2.plot(cma.year, cma.median_days, marker="s", ms=3.8, lw=1.4, ls="--", color="#666666",
             label=f"{T('ef2_median_days', lang)} · {T('act_cma', lang).lower()}")
    ax2.set_ylabel(T("ef2_median_days", lang))
    ax2.grid(False)
    context(ax[5], lang, law=False, pandemic_pos=0.38)
    year_axis(ax[5], lang)
    # Espacio libre en ambos ejes para que la leyenda no tape ninguna serie.
    ax[5].set_ylim(0, float(np.nanmax(hosp.n_episodes_cell)) * 1.45)
    _md = float(np.nanmax(np.concatenate([hosp.median_days.to_numpy(dtype=float),
                                          cma.median_days.to_numpy(dtype=float)])))
    ax2.set_ylim(0, (_md if np.isfinite(_md) and _md > 0 else 1.0) * 1.55)
    h1, l1 = ax[5].get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    legend_wrapped(ax[5], h1 + h2, l1 + l2, fontsize=FS_ANN, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[5], "f", T("ef2_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    for lab, who, position, activity in ((f"{T('episodes_f84', lang)} · {T('act_hosp', lang).lower()}", variant, "any", "hospitalisation"),
                                         (f"{T('pos_principal', lang)} · {T('act_hosp', lang).lower()}", variant, "principal", "hospitalisation"),
                                         (f"{T('episodes_f84', lang)} · {T('act_cma', lang).lower()}", variant, "any", "cma"),
                                         (f"{T('all_episodes', lang)} · {T('act_hosp', lang).lower()}", COMPARISON, "all", "hospitalisation")):
        s = series(activity, position, who=who)
        for metric, dec, col in ((T("median_iqr", lang), 0, None), (T("ef2_p90", lang), 0, "p90_days"),
                                 (T("ef2_zero", lang), 1, "zero")):
            r = {"__k": f"{lab} — {metric}"}
            for y in YEARS:
                c = s.loc[s.year == y]
                if c.empty or float(c.n_valid_dates.iloc[0]) == 0:
                    r[str(y)] = T("not_estimable", lang)
                    continue
                c = c.iloc[0]
                if col is None:
                    r[str(y)] = f"{num(c.median_days, 0, lang)} ({num(c.q25_days, 0, lang)}–{num(c.q75_days, 0, lang)})"
                elif col == "zero":
                    r[str(y)] = n_pct(c.n_los_zero, 100 * c.n_los_zero / c.n_valid_dates, lang)
                else:
                    r[str(y)] = num(c[col], 0, lang)
            rows.append(r)
        r = {"__k": f"{lab} — n"}
        for y in YEARS:
            c = s.loc[s.year == y]
            r[str(y)] = (f"{num(c.n_valid_dates.iloc[0], 0, lang)} (+{num(c.n_invalid_dates.iloc[0], 0, lang)})"
                         if len(c) else T("not_estimable", lang))
        rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": {"es": "Serie y estadístico", "en": "Series and statistic"}[lang]})
    numeric = pd.concat([los.loc[los.variant.isin([variant, COMPARISON])].assign(block="length_of_stay"),
                         la.loc[la.variant.isin([variant, COMPARISON])].assign(block="length_of_stay_by_age"),
                         feat.assign(block="los_bin_2024")], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Mediana y rango intercuartílico de la estadía (días) de los episodios con F84 documentado por año y "
               f"posición del código, y de todos los episodios GRD, solo hospitalización y panel observado. (b) Media "
               f"acumulada 2019–2024 (barras) y mediana de 2024 (puntos) por grupo etario quinquenal de la OMS. "
               f"(c) Percentil 90 de la estadía por año. (d) Porcentaje de episodios con estadía de cero días, en todas "
               f"las actividades y solo en hospitalización: la cirugía mayor ambulatoria es cero por definición, por lo "
               f"que ambas series se muestran separadas. (e) Distribución por tramos de estadía en 2024, episodios con "
               f"F84 frente a todos los episodios GRD, con la diferencia en puntos porcentuales. (f) Episodios con F84 "
               f"por actividad (barras, eje izquierdo) y mediana de días de cada actividad (líneas, eje derecho). Los "
               f"episodios con fechas no analizables o con alta anterior al ingreso se excluyen del cálculo, se informan "
               f"en la tabla acompañante y nunca se imputan. Sombreado: disrupción del reporte 2020–2021; línea punteada: "
               f"Ley 21.545 (marzo de 2023) como contexto. Definición: {vl}."),
        "en": (f"(a) Median and interquartile range of length of stay (days) of episodes with documented F84 by year and "
               f"code position, and of all GRD episodes, hospitalisation only and observed panel. (b) Pooled 2019–2024 "
               f"mean (bars) and 2024 median (points) by five-year WHO age group. (c) 90th percentile of stay by year. "
               f"(d) Percentage of episodes with a zero-day stay, across all activities and for hospitalisation only: "
               f"major ambulatory surgery is zero by definition, so both series are shown separately. (e) Distribution by "
               f"stay bands in 2024, episodes with F84 versus all GRD episodes, with the difference in percentage points. "
               f"(f) Episodes with F84 by activity (bars, left axis) and median days of each activity (lines, right axis). "
               f"Episodes with unparsable dates or discharge before admission are excluded from the calculation, reported "
               f"in the companion table and never imputed. Shading: 2020–2021 reporting disruption; dotted line: Law "
               f"21.545 (March 2023) as context. Definition: {vl}."),
    }[lang]
    note = {
        "es": ("Unidad: días de estadía por episodio (alta − ingreso). Denominador de cada estadístico: episodios con dos "
               "fechas válidas (n; entre paréntesis, episodios con fechas no analizables, excluidos y nunca imputados). "
               + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_length_of_stay.csv, grd_los_age.csv y grd_episode_features.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Unit: days of stay per episode (discharge − admission). Denominator of every statistic: episodes with two "
               "valid dates (n; in brackets, episodes with unparsable dates, excluded and never imputed). "
               + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_length_of_stay.csv, grd_los_age.csv and grd_episode_features.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF2", "ef2_title", variant, lang), cap,
                  table_title("EF2", "ef2_title", variant, lang), note)


# ===========================================================================
# EF3 · Características administrativas del episodio
# ===========================================================================
def feature_pooled(feat: pd.DataFrame, who: str, position: str, variable: str, years=None) -> tuple[pd.DataFrame, float]:
    """Distribución acumulada 2019–2024 de una variable del episodio; denominador = episodios de la celda por año."""
    years = YEARS if years is None else years
    s = feat.loc[(feat.panel == "observed") & (feat.variant == who) & (feat.position == position) &
                 (feat.variable == variable) & (feat.year.isin(years))]
    if s.empty:
        return pd.DataFrame(columns=["value", "n_episodes", "pct"]), 0.0
    den = float(s.groupby("year").n_cell_total.first().sum())
    agg = s.groupby("value", as_index=False).n_episodes.sum()
    agg["pct"] = 100 * agg.n_episodes / den if den else np.nan
    return agg.sort_values("n_episodes", ascending=False).reset_index(drop=True), den


def feature_year(feat: pd.DataFrame, who: str, position: str, variable: str, year: int) -> pd.DataFrame:
    s = feat.loc[(feat.panel == "observed") & (feat.variant == who) & (feat.position == position) &
                 (feat.variable == variable) & (feat.year == year)]
    return s.set_index("value")


#: Categorías dibujadas por panel. La celda vertical de 90 × 82 mm no admite las 10 procedencias ni las 15
#: especialidades del diseño apaisado anterior sin bajar del cuerpo mínimo, de modo que cada panel muestra las
#: siete categorías más frecuentes entre los episodios con F84 y agrega el resto en una fila «otras categorías»
#: explícita —nunca se descarta una categoría—; la tabla acompañante conserva TODAS las categorías con su n, su
#: porcentaje en cada serie y la diferencia, que es donde vive ahora el detalle largo.
EF3_TOP = 7
EF3_VARS = [("TIPO_INGRESO", "ef3_a"), ("TIPO_ACTIVIDAD", "ef3_b"), ("TIPO_PROCEDENCIA", "ef3_c"),
            ("TIPOALTA", "ef3_d"), ("PREVISION_grouped", "ef3_e"), ("ESPECIALIDAD_MEDICA", "ef3_f")]


def ef3(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF3_episode_features"
    feat = D.feat
    fig, ax = new_plate()
    table_rows = []
    numeric_rows = []
    for k, (variable, key) in enumerate(EF3_VARS):
        f84, den_f = feature_pooled(feat, variant, "any", variable)
        alle, den_a = feature_pooled(feat, COMPARISON, "all", variable)
        ctl.add(f"EF3_feature_denominator[{variant}|{variable}]",
                "sum_2019_2024", float(D.year.loc[(D.year.variant == variant) & (D.year.panel == "observed") &
                                                  (D.year.activity == "all") & (D.year.position == "any"), "n_episodes_f84"].sum()),
                den_f, "denominador acumulado de grd_episode_features frente a la suma anual de grd_year_summary")
        every = list(f84.value)                      # todas las categorías: van completas a la tabla acompañante
        order = every[:EF3_TOP]
        rest = every[EF3_TOP:]
        a_map = alle.set_index("value")
        share_f = [float(f84.loc[f84.value == v, "pct"].iloc[0]) for v in order]
        share_a = [float(a_map.pct.get(v, 0.0)) for v in order]
        labels = [tick_label(cat_label(v, lang), 24) for v in order]
        if rest:                                     # el resto no se descarta: se agrega en una fila explícita
            share_f.append(float(f84.loc[f84.value.isin(rest), "pct"].sum()))
            share_a.append(float(sum(a_map.pct.get(v, 0.0) for v in rest)))
            labels.append(f"{T('ef3_other', lang)} ({len(rest)})")
        hbars_compare(ax[k], labels, share_f, share_a, lang, legend=(k == 0))
        ctl.info(f"EF3_categories_drawn[{variant}|{variable}]", "n_drawn_of_total", f"{len(order)}/{len(every)}",
                 "la lámina dibuja las siete categorías más frecuentes y una fila «otras»; la tabla acompañante conserva todas")
        panel(ax[k], PLATE_LETTERS[k], T(key, lang))
        f2019 = feature_year(feat, variant, "any", variable, 2019)
        f2024 = feature_year(feat, variant, "any", variable, 2024)
        for v in every:
            n_f = float(f84.loc[f84.value == v, "n_episodes"].iloc[0])
            n_a = float(a_map.n_episodes.get(v, 0.0))
            table_rows.append({"__v": variable, "__c": cat_label(v, lang),
                               "f84": n_pct(n_f, float(f84.loc[f84.value == v, "pct"].iloc[0]), lang),
                               "all": n_pct(n_a, float(a_map.pct.get(v, 0.0)), lang),
                               "diff": num(float(f84.loc[f84.value == v, "pct"].iloc[0]) - float(a_map.pct.get(v, 0.0)), 1, lang),
                               "y2019": pct(float(f2019.pct_within_cell.get(v, 0.0)), lang) if len(f2019) else T("not_estimable", lang),
                               "y2024": pct(float(f2024.pct_within_cell.get(v, 0.0)), lang) if len(f2024) else T("not_estimable", lang)})
            numeric_rows.append(dict(variable=variable, value=v, n_f84_2019_2024=n_f, pct_f84_2019_2024=float(f84.loc[f84.value == v, "pct"].iloc[0]),
                                     n_all_2019_2024=n_a, pct_all_2019_2024=float(a_map.pct.get(v, 0.0)),
                                     pct_f84_2019=float(f2019.pct_within_cell.get(v, np.nan)) if len(f2019) else np.nan,
                                     pct_f84_2024=float(f2024.pct_within_cell.get(v, np.nan)) if len(f2024) else np.nan,
                                     denominator_f84=den_f, denominator_all=den_a, variant=variant, panel="observed", position="any"))

    cols = {"__v": {"es": "Variable", "en": "Variable"}[lang], "__c": {"es": "Categoría", "en": "Category"}[lang],
            "f84": {"es": "F84 documentado 2019–2024, n (%)", "en": "Documented F84 2019–2024, n (%)"}[lang],
            "all": {"es": "Todos los episodios GRD, n (%)", "en": "All GRD episodes, n (%)"}[lang],
            "diff": {"es": "Diferencia (pp)", "en": "Difference (pp)"}[lang],
            "y2019": {"es": "% F84 en 2019", "en": "% F84 in 2019"}[lang],
            "y2024": {"es": "% F84 en 2024", "en": "% F84 in 2024"}[lang]}
    formatted = pd.DataFrame(table_rows).rename(columns=cols)
    numeric = pd.DataFrame(numeric_rows)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"Distribución acumulada 2019–2024 (panel observado) de seis variables administrativas del episodio entre "
               f"los episodios con F84 documentado en cualquier posición y entre todos los episodios GRD, con la "
               f"diferencia en puntos porcentuales junto a cada barra: (a) tipo de ingreso; (b) tipo de actividad; "
               f"(c) procedencia; (d) tipo de alta; (e) previsión agrupada por tramo; (f) especialidad médica (el módulo "
               f"11 conserva las 20 principales y agrupa el resto en «otra especialidad»). Cada panel dibuja las siete "
               f"categorías más frecuentes entre los episodios con F84 y agrega el resto en una fila «otras categorías» "
               f"con el número de categorías agrupadas entre paréntesis: ninguna categoría se descarta y la tabla "
               f"acompañante conserva todas con su n, su porcentaje en cada serie y su diferencia. El denominador de cada porcentaje es el total "
               f"de episodios de la celda (mismo año, panel y actividad), de modo que las categorías suman 100 %. Las "
               f"categorías «no identificada» y «desconocido» se conservan como estados propios y nunca se convierten en "
               f"cero ni se funden con otras. Definición: {vl}. Los recuentos son reconocimiento administrativo, no "
               f"prevalencia; un episodio con F84 secundario no es una hospitalización por autismo."),
        "en": (f"Pooled 2019–2024 distribution (observed panel) of six administrative episode variables among episodes "
               f"with documented F84 in any position and among all GRD episodes, with the difference in percentage points "
               f"beside each bar: (a) type of admission; (b) type of activity; (c) provenance; (d) type of discharge; "
               f"(e) insurance grouped by tramo; (f) medical specialty (module 11 keeps the top 20 and pools the rest "
               f"into 'other specialty'). Each panel draws the seven most frequent categories among episodes with F84 and "
               f"pools the remainder into an explicit 'other categories' row with the number of pooled categories in "
               f"brackets: no category is dropped, and the companion table keeps every category with its n, its "
               f"percentage in each series and its difference. The denominator "
               f"of every percentage is the total number of episodes in the cell (same year, panel and activity), so "
               f"categories add to 100%. The 'not identified' and 'not reported' categories are kept as states of their "
               f"own and are never turned into zero or merged. Definition: {vl}. Counts are administrative recognition, "
               f"not prevalence; an episode with a secondary F84 is not a hospitalisation for autism."),
    }[lang]
    note = {
        "es": ("Celda: episodios (porcentaje dentro de la celda). Acumulado 2019–2024, panel observado, F84 en cualquier "
               "posición; la columna de comparación son todos los episodios GRD del mismo panel y período. Las categorías "
               "se muestran en el idioma del registro original cuando no existe una traducción verificada. " +
               NOTE_CORE[lang] + " " + source_line("outputs/tidy/grd_episode_features.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes (percentage within the cell). Pooled 2019–2024, observed panel, F84 in any position; the "
               "comparison column is all GRD episodes of the same panel and period. Categories are shown in the language "
               "of the original register when no verified translation exists. " +
               NOTE_CORE[lang] + " " + source_line("outputs/tidy/grd_episode_features.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF3", "ef3_title", variant, lang), cap,
                  table_title("EF3", "ef3_title", variant, lang), note)


# ===========================================================================
# EF4 · Gravedad, riesgo de mortalidad, peso GRD y letalidad
# ===========================================================================
SEV_COLORS = ["#deebf7", "#9ecae1", "#4292c6", "#08519c", "#bdbdbd"]
SEV_ORDER = ["0", "1", "2", "3", "DESCONOCIDO"]


def stacked_severity(ax, feat, variant, variable, lang, ctl=None):
    """Barras apiladas al 100 % por año: episodios con F84 (izquierda) y todos los episodios GRD (derecha)."""
    w = 0.36
    for offset, who, position, hatch in ((-w / 2 - 0.02, variant, "any", None), (w / 2 + 0.02, COMPARISON, "all", "//")):
        bottom = np.zeros(len(YEARS))
        for j, cat in enumerate(SEV_ORDER):
            vals = []
            for y in YEARS:
                s = feat.loc[(feat.panel == "observed") & (feat.variant == who) & (feat.position == position) &
                             (feat.variable == variable) & (feat.year == y) & (feat.value == cat)]
                vals.append(float(s.pct_within_cell.iloc[0]) if len(s) else 0.0)
            vals = np.array(vals)
            ax.bar(np.array(YEARS) + offset, vals, bottom=bottom, width=w, color=SEV_COLORS[j], hatch=hatch,
                   edgecolor="white", linewidth=0.4,
                   label=(cat if cat != "DESCONOCIDO" else T("not_reported", lang)) if hatch is None else None)
            bottom += vals
    ax.set_ylim(0, 100)
    ax.set_ylabel(T("pct_episodes", lang))


def ef4(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF4_severity_weight"
    feat = D.feat
    wt = D.weight.loc[(D.weight.panel == "observed") & (D.weight.variant == variant)]
    fig, ax = new_plate()

    # (a) y (b) gravedad y riesgo de mortalidad
    bars_note = {"es": "barras lisas: F84 · rayadas: todos los episodios",
                 "en": "solid bars: F84 · hatched: all episodes"}[lang]
    stacked_severity(ax[0], feat, variant, "IR_29301_SEVERIDAD", lang)
    year_axis(ax[0], lang)
    ax[0].set_ylim(0, 148)                      # banda superior reservada para la leyenda: las barras siguen sumando 100 %
    legend_wrapped(ax[0], fontsize=FS_ANN, ncol=5, title=f"{T('ef4_sev', lang)} ({bars_note})", title_fontsize=FS_LEG,
                   loc="upper center", expand=False, width=30, columnspacing=0.8, handlelength=1.1,
                   frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[0], "a", T("ef4_a", lang))
    stacked_severity(ax[1], feat, variant, "IR_29301_MORTALIDAD", lang)
    year_axis(ax[1], lang)
    ax[1].set_ylim(0, 148)                      # banda superior reservada para la leyenda: las barras siguen sumando 100 %
    legend_wrapped(ax[1], fontsize=FS_ANN, ncol=5, title=f"{T('ef4_mor', lang)} ({bars_note})", title_fontsize=FS_LEG,
                   loc="upper center", expand=False, width=30, columnspacing=0.8, handlelength=1.1,
                   frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[1], "b", T("ef4_b", lang))

    # (c) peso relativo: mediana y cuartiles por año y posición
    summ = wt.loc[wt.row_type == "weight_summary"]
    for position in POSITIONS:
        s = summ.loc[summ.position == position].sort_values("year")
        if s.empty:
            continue
        ax[2].fill_between(s.year, s.q25, s.q75, color=COL[position], alpha=0.16, lw=0)
        ax[2].plot(s.year, s["median"], marker="o", ms=4.0, lw=1.7, color=COL[position], label=T(POS_KEY[position], lang))
        ax[2].plot(s.year, s["mean"], marker="^", ms=3.4, lw=1.1, ls=":", color=COL[position])
    context(ax[2], lang)
    year_axis(ax[2], lang)
    ax[2].set_ylabel(T("ef4_weight", lang))
    lo_c, hi_c = ax[2].get_ylim()
    ax[2].set_ylim(lo_c, hi_c + (hi_c - lo_c) * 0.16)
    legend_wrapped(ax[2], fontsize=FS_TICK, loc="lower left", frameon=True, framealpha=0.95, edgecolor="none",
                 title={"es": "Mediana (banda P25–P75); punteado: media",
                        "en": "Median (P25–P75 band); dotted: mean"}[lang], title_fontsize=FS_LEG)
    panel(ax[2], "c", T("ef4_c", lang))

    # (d) grupos GRD más frecuentes (acumulado)
    grp = wt.loc[(wt.row_type == "grd_group") & (wt.position == "any")]
    pooled = grp.groupby("ir_grd_code", as_index=False).agg(n=("n", "sum"), weight=("mean", "mean"))
    den = float(summ.loc[summ.position == "any", "n_episodes_cell"].sum())
    pooled["pct"] = 100 * pooled.n / den if den else np.nan
    pooled = pooled.sort_values("n", ascending=False).head(12)
    yb = np.arange(len(pooled))
    ax[3].barh(yb, pooled.pct, color=COL["f84"])
    ax[3].set_yticks(yb)
    ax[3].set_yticklabels([str(c) for c in pooled.ir_grd_code], fontsize=FS_TICK)
    ax[3].invert_yaxis()
    ax[3].set_xlabel(T("pct_f84", lang))
    ax[3].set_ylabel(T("ef4_grd_group", lang))
    for i, (p, wv) in enumerate(zip(pooled.pct, pooled.weight)):
        ax[3].text(p + max(pooled.pct) * 0.02, i, f"{num(p, 1, lang)} % · {T('ef4_weight', lang).split()[0].lower()} {num(wv, 2, lang)}"
                   if lang == "es" else f"{num(p, 1, lang)}% · weight {num(wv, 2, lang)}", va="center", fontsize=FS_ANN)
    ax[3].set_xlim(0, max(pooled.pct) * 1.45 if len(pooled) else 1)
    panel(ax[3], "d", T("ef4_d", lang))

    # (e) letalidad hospitalaria con IC de Jeffreys
    leth_rows = []
    for who, position, colour, lab, off in ((variant, "any", COL["f84"], T("episodes_f84", lang), -0.08),
                                            (COMPARISON, "all", COL["all"], T("all_episodes", lang), 0.08)):
        xs, ps, los_, his = [], [], [], []
        for y in YEARS:
            s = feat.loc[(feat.panel == "observed") & (feat.variant == who) & (feat.position == position) &
                         (feat.variable == "TIPOALTA") & (feat.year == y)]
            if s.empty:
                continue
            n = float(s.n_cell_total.iloc[0])
            k = float(s.loc[s.value == "FALLECIDO", "n_episodes"].sum())     # categoría ausente = cero observado
            p, lo, hi = jeffreys(k, n)
            xs.append(y + off); ps.append(100 * p); los_.append(100 * lo); his.append(100 * hi)
            leth_rows.append(dict(year=y, series=who, position=position, deaths=k, episodes=n, lethality_pct=100 * p,
                                  lethality_lo=100 * lo, lethality_hi=100 * hi, method="Jeffreys Beta(0.5,0.5)"))
        ax[4].errorbar(xs, ps, yerr=[np.array(ps) - np.array(los_), np.array(his) - np.array(ps)], marker="o", ms=4.2,
                       lw=1.6, capsize=2.6, color=colour, label=lab)
    context(ax[4], lang)
    year_axis(ax[4], lang)
    ax[4].set_ylabel(T("ef4_leth", lang))
    legend_wrapped(ax[4], fontsize=FS_TICK, loc="center right", frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[4], "e", T("ef4_e", lang))

    # (f) peso medio por posición y episodios sin peso
    for position in POSITIONS:
        s = summ.loc[summ.position == position].sort_values("year")
        if s.empty:
            continue
        ax[5].plot(s.year, s["mean"], marker="o", ms=4.0, lw=1.6, color=COL[position], label=T(POS_KEY[position], lang))
    ax[5].set_ylabel(T("ef4_weight", lang))
    ax5b = ax[5].twinx()
    s = summ.loc[summ.position == "any"].sort_values("year")
    nowt = 100 * s.n_without_weight / s.n.replace(0, np.nan)
    ax5b.bar(s.year, nowt.fillna(0.0), width=0.5, color="#cccccc", alpha=0.75, zorder=0)
    ax5b.set_ylabel(T("ef4_nowt", lang))
    ax5b.grid(False)
    if float(np.nanmax(nowt.to_numpy(dtype=float))) == 0:        # cero observado, no dato ausente
        ax5b.set_ylim(0, 1)
        ax5b.text(0.985, 0.985, {"es": "Sin episodios sin peso registrado (0 %)",
                                 "en": "No episodes without a recorded weight (0%)"}[lang], transform=ax5b.transAxes,
                  ha="right", va="top", fontsize=FS_ANN, color="#555555", bbox=CTX_BBOX, zorder=7)
    context(ax[5], lang, pandemic_pos=0.04, law_pos=0.04)
    year_axis(ax[5], lang)
    lo_f, hi_f = ax[5].get_ylim()
    _span = hi_f - lo_f
    ax[5].set_ylim(lo_f - _span * 0.14, hi_f + _span * 0.22)
    legend_wrapped(ax[5], fontsize=FS_TICK, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    ax[5].set_zorder(ax5b.get_zorder() + 1)
    ax[5].patch.set_visible(False)
    panel(ax[5], "f", T("ef4_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    for cat in SEV_ORDER:
        r = {"__k": f"{T('ef4_sev', lang)} — {cat if cat != 'DESCONOCIDO' else T('not_reported', lang)}"}
        for y in YEARS:
            s = feat.loc[(feat.panel == "observed") & (feat.variant == variant) & (feat.position == "any") &
                         (feat.variable == "IR_29301_SEVERIDAD") & (feat.year == y) & (feat.value == cat)]
            r[str(y)] = n_pct(s.n_episodes.iloc[0], s.pct_within_cell.iloc[0], lang) if len(s) else n_pct(0, 0.0, lang)
        rows.append(r)
    for cat in SEV_ORDER:
        r = {"__k": f"{T('ef4_mor', lang)} — {cat if cat != 'DESCONOCIDO' else T('not_reported', lang)}"}
        for y in YEARS:
            s = feat.loc[(feat.panel == "observed") & (feat.variant == variant) & (feat.position == "any") &
                         (feat.variable == "IR_29301_MORTALIDAD") & (feat.year == y) & (feat.value == cat)]
            r[str(y)] = n_pct(s.n_episodes.iloc[0], s.pct_within_cell.iloc[0], lang) if len(s) else n_pct(0, 0.0, lang)
        rows.append(r)
    r = {"__k": f"{T('ef4_weight', lang)} — {T('median_iqr', lang)}"}
    for y in YEARS:
        s = summ.loc[(summ.position == "any") & (summ.year == y)]
        r[str(y)] = (f"{num(s['median'].iloc[0], 2, lang)} ({num(s.q25.iloc[0], 2, lang)}–{num(s.q75.iloc[0], 2, lang)})"
                     if len(s) else T("not_estimable", lang))
    rows.append(r)
    r = {"__k": f"{T('ef4_weight', lang)} — x̄ (DE)"}
    for y in YEARS:
        s = summ.loc[(summ.position == "any") & (summ.year == y)]
        r[str(y)] = f"{num(s['mean'].iloc[0], 2, lang)} ({num(s.sd.iloc[0], 2, lang)})" if len(s) else T("not_estimable", lang)
    rows.append(r)
    leth = pd.DataFrame(leth_rows)
    for who, lab in ((variant, T("episodes_f84", lang)), (COMPARISON, T("all_episodes", lang))):
        r = {"__k": f"{T('ef4_leth', lang)} — {lab}"}
        for y in YEARS:
            s = leth.loc[(leth.series == who) & (leth.year == y)]
            r[str(y)] = (f"{num(s.deaths.iloc[0], 0, lang)}/{num(s.episodes.iloc[0], 0, lang)}; "
                         f"{val_ci(s.lethality_pct.iloc[0], s.lethality_lo.iloc[0], s.lethality_hi.iloc[0], 2, lang)}"
                         if len(s) else T("not_estimable", lang))
        rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": {"es": "Indicador", "en": "Indicator"}[lang]})
    numeric = pd.concat([wt.assign(block="grd_weight"),
                         feat.loc[(feat.panel == "observed") & feat.variable.isin(["IR_29301_SEVERIDAD", "IR_29301_MORTALIDAD", "TIPOALTA"]) &
                                  feat.variant.isin([variant, COMPARISON])].assign(block="ir_and_discharge"),
                         leth.assign(block="lethality_jeffreys")], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Gravedad y (b) riesgo de mortalidad del agrupador IR-29301 (0 = menor a 3 = extremo; «no informado» "
               f"como categoría propia) por año: barras lisas, episodios con F84 documentado; barras rayadas, todos los "
               f"episodios GRD del mismo panel. (c) Peso relativo IR-29301 de los episodios con F84: mediana (línea), "
               f"rango intercuartílico (banda) y media (punteado) por año y posición del código. (d) Doce grupos GRD más "
               f"frecuentes entre los episodios con F84, acumulado 2019–2024, como porcentaje de esos episodios y con su "
               f"peso relativo medio; el módulo 11 conserva los 15 grupos principales de cada año y agrupa el resto. "
               f"(e) Letalidad hospitalaria (alta registrada como «fallecido») por año, con intervalos de Jeffreys al "
               f"95 %, para los episodios con F84 y para todos los episodios GRD; los recuentos son pequeños y el "
               f"intervalo lo refleja. (f) Peso medio por posición del código (líneas) y porcentaje de episodios sin peso "
               f"registrado (barras grises, eje derecho). Sombreado: disrupción del reporte 2020–2021; línea punteada: "
               f"Ley 21.545 (marzo de 2023) como contexto. Definición: {vl}. La letalidad describe el episodio, no la "
               f"mortalidad de las personas con autismo."),
        "en": (f"(a) Severity and (b) mortality risk of the IR-29301 grouper (0 = minor to 3 = extreme; 'not reported' as "
               f"its own category) by year: solid bars, episodes with documented F84; hatched bars, all GRD episodes of "
               f"the same panel. (c) IR-29301 relative weight of episodes with F84: median (line), interquartile range "
               f"(band) and mean (dotted) by year and code position. (d) Twelve most frequent GRD groups among episodes "
               f"with F84, pooled 2019–2024, as a percentage of those episodes and with their mean relative weight; "
               f"module 11 keeps each year's top 15 groups and pools the remainder. (e) In-hospital lethality (discharge "
               f"recorded as 'died') by year with Jeffreys 95% intervals, for episodes with F84 and for all GRD episodes; "
               f"counts are small and the interval reflects it. (f) Mean weight by code position (lines) and percentage of "
               f"episodes without a recorded weight (grey bars, right axis). Shading: 2020–2021 reporting disruption; "
               f"dotted line: Law 21.545 (March 2023) as context. Definition: {vl}. Lethality describes the episode, not "
               f"the mortality of autistic people."),
    }[lang]
    note = {
        "es": ("Celda: episodios (porcentaje dentro de la celda) para gravedad y riesgo; peso relativo IR-29301 como "
               "mediana (P25–P75) y media (DE); letalidad como fallecidos/episodios y porcentaje con IC 95 % de Jeffreys. "
               "Panel observado, F84 en cualquier posición. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_grd_weight.csv y grd_episode_features.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes (percentage within the cell) for severity and risk; IR-29301 relative weight as median "
               "(P25–P75) and mean (SD); lethality as deaths/episodes and percentage with Jeffreys 95% CI. Observed panel, "
               "F84 in any position. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_grd_weight.csv and grd_episode_features.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF4", "ef4_title", variant, lang), cap,
                  table_title("EF4", "ef4_title", variant, lang), note)


# ===========================================================================
# EF5 · Co-diagnósticos
# ===========================================================================
#: La celda vertical de 90 × 82 mm no admite las 25 categorías CIE-10 ni las 15 del diseño apaisado con la glosa
#: legible: cada panel de ranking muestra las diez primeras con su glosa en dos líneas y la tabla acompañante
#: conserva las 25 con su n y su porcentaje año a año, que es donde vive el detalle largo.
EF5_TOP = 10
EF5_CHAPTERS = 6


def ef5(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF5_codiagnoses"
    cd = D.codiag.loc[(D.codiag.panel == "observed") & (D.codiag.variant == variant)]
    ch = D.chapters.loc[(D.chapters.panel == "observed") & (D.chapters.variant == variant)]
    any_pos = cd.loc[(cd.position == "any") & (cd.code_position == "any")]
    sec_only = cd.loc[(cd.position == "secondary_only") & (cd.code_position == "principal")]

    den_any = float(any_pos.groupby("year").n_f84_episodes_cell.first().sum())
    den_sec = float(sec_only.groupby("year").n_f84_episodes_cell.first().sum()) if len(sec_only) else np.nan
    ctl.add(f"EF5_codiag_denominator[{variant}]", "sum_2019_2024",
            float(D.year.loc[(D.year.variant == variant) & (D.year.panel == "observed") & (D.year.activity == "all") &
                             (D.year.position == "any"), "n_episodes_f84"].sum()), den_any,
            "denominador acumulado de grd_codiagnoses (cualquier posición) frente a grd_year_summary")

    pooled = (any_pos.groupby(["code3", "icd_label_es"], as_index=False).n_episodes.sum()
              .sort_values("n_episodes", ascending=False))
    pooled["pct"] = 100 * pooled.n_episodes / den_any
    top25 = pooled.head(25)                      # detalle largo: va completo a la tabla acompañante
    top_plot = pooled.head(EF5_TOP)              # celda vertical: diez categorías con la glosa legible

    fig, ax = new_plate()
    # (a) categorías principales
    yb = np.arange(len(top_plot))
    ax[0].barh(yb, top_plot.pct, color=COL["f84"])
    ax[0].set_yticks(yb)
    ax[0].set_yticklabels([tick_label(icd3_label(c, l, lang), 18) for c, l in zip(top_plot.code3, top_plot.icd_label_es)],
                          fontsize=FS_ANN)
    ax[0].invert_yaxis()
    ax[0].set_xlabel(T("pct_f84", lang))
    panel(ax[0], "a", T("ef5_a", lang))

    # (b) capítulos por año — mapa de calor: los nombres de capítulo de la CIE-10 son demasiado largos para
    #     caber en la leyenda de una celda vertical, y ocho series superpuestas en 90 mm no se distinguen; en
    #     filas, cada capítulo lleva su nombre completo y cada celda su valor.
    chap = ch.loc[(ch.grouping == "chapter") & (ch.position == "any") & (ch.code_position == "any")]
    top_ch = (chap.groupby("group_label", as_index=False).n_episodes.sum()
              .sort_values("n_episodes", ascending=False).head(EF5_CHAPTERS).group_label.tolist())
    mat_ch = pd.DataFrame({y: [float(chap.loc[(chap.group_label == g) & (chap.year == y), "pct_of_f84_episodes"].sum())
                               if len(chap.loc[(chap.group_label == g) & (chap.year == y)]) else np.nan
                               for g in top_ch] for y in YEARS}, index=top_ch)
    heat(ax[1], mat_ch, lambda v: num(v, 1, lang), cmap="YlGnBu", fontsize=FS_CELL,
         ylabels=[tick_label(chapter_label(g, lang), 20) for g in top_ch],
         xlabels=[str(y) for y in YEARS], fig=fig, cbar_label=T("ef5_per100", lang))
    ax[1].tick_params(axis="y", labelsize=FS_CELL)
    # Contexto sobre un eje de columnas: la disrupción cubre las columnas de 2020 y 2021; la ley cae entre 2022 y 2023
    ax[1].axvspan(0.5, 2.5, color="grey", alpha=0.16, zorder=3)
    ax[1].axvline(3.5, color="#222222", ls=":", lw=1.2, zorder=4)
    # El sombreado y la línea punteada quedan dibujados; su glosa va bajo el eje, no sobre las celdas.
    long_xlabel(ax[1], {"es": f"{T('year', lang)} — sombreado: {T('pandemic', lang)}; línea punteada: {T('law', lang)}",
                        "en": f"{T('year', lang)} — shading: {T('pandemic', lang)}; dotted line: {T('law', lang)}"}[lang])
    panel(ax[1], "b", T("ef5_b", lang))

    # (c) bloques de salud mental: 2019 frente a 2024
    blocks = ch.loc[(ch.grouping == "mental_block") & (ch.position == "any") & (ch.code_position == "any")]
    order = (blocks.groupby("group_label", as_index=False).n_episodes.sum()
             .sort_values("n_episodes", ascending=False).group_label.tolist())
    yb = np.arange(len(order))
    v19 = [float(blocks.loc[(blocks.group_label == g) & (blocks.year == 2019), "pct_of_f84_episodes"].sum()) for g in order]
    v24 = [float(blocks.loc[(blocks.group_label == g) & (blocks.year == 2024), "pct_of_f84_episodes"].sum()) for g in order]
    for i, (a, b) in enumerate(zip(v19, v24)):
        ax[2].plot([a, b], [i, i], color="#bbbbbb", lw=1.6, zorder=1)
    ax[2].scatter(v19, yb, s=26, color=COL["y2019"], zorder=2, label="2019")
    ax[2].scatter(v24, yb, s=26, color=COL["y2024"], zorder=2, label="2024")
    ax[2].set_yticks(yb)
    ax[2].set_yticklabels([tick_label(block_label(g, lang), 18) for g in order], fontsize=FS_ANN)
    ax[2].invert_yaxis()
    ax[2].set_xlabel(T("pct_f84", lang))
    legend_wrapped(ax[2], fontsize=FS_TICK, loc="lower right", expand=False,
                   frameon=True, framealpha=0.92, edgecolor="none")
    panel(ax[2], "c", T("ef5_c", lang))

    # (d) diagnóstico principal cuando F84 es solo secundario
    pooled_sec = (sec_only.groupby(["code3", "icd_label_es"], as_index=False).n_episodes.sum()
                  .sort_values("n_episodes", ascending=False))
    pooled_sec["pct"] = 100 * pooled_sec.n_episodes / den_sec if den_sec and not np.isnan(den_sec) else np.nan
    top_sec = pooled_sec.head(EF5_TOP)
    yb = np.arange(len(top_sec))
    ax[3].barh(yb, top_sec.pct, color=COL["secondary_only"])
    ax[3].set_yticks(yb)
    ax[3].set_yticklabels([tick_label(icd3_label(c, l, lang), 18) for c, l in zip(top_sec.code3, top_sec.icd_label_es)],
                          fontsize=FS_ANN)
    ax[3].invert_yaxis()
    ax[3].set_xlabel({"es": "% de los episodios con F84 solo secundario",
                      "en": "% of episodes with F84 secondary only"}[lang])
    panel(ax[3], "d", T("ef5_d", lang))

    # (e) cambio 2019 → 2024 de las 15 categorías principales
    top15 = pooled.head(EF5_TOP)
    yb = np.arange(len(top15))
    a19 = [float(any_pos.loc[(any_pos.code3 == c) & (any_pos.year == 2019), "pct_of_f84_episodes"].sum()) for c in top15.code3]
    a24 = [float(any_pos.loc[(any_pos.code3 == c) & (any_pos.year == 2024), "pct_of_f84_episodes"].sum()) for c in top15.code3]
    for i, (a, b) in enumerate(zip(a19, a24)):
        ax[4].plot([a, b], [i, i], color="#bbbbbb", lw=1.6, zorder=1)
    ax[4].scatter(a19, yb, s=26, color=COL["y2019"], zorder=2, label="2019")
    ax[4].scatter(a24, yb, s=26, color=COL["y2024"], zorder=2, label="2024")
    ax[4].set_yticks(yb)
    ax[4].set_yticklabels([tick_label(icd3_label(c, l, lang), 18) for c, l in zip(top15.code3, top15.icd_label_es)],
                          fontsize=FS_ANN)
    ax[4].invert_yaxis()
    ax[4].set_xlabel(T("pct_f84", lang))
    legend_wrapped(ax[4], fontsize=FS_TICK, loc="lower right", expand=False,
                   frameon=True, framealpha=0.92, edgecolor="none")
    panel(ax[4], "e", T("ef5_e", lang))

    # (f) categorías por episodio y profundidad diagnóstica
    per_ep = (any_pos.groupby("year").agg(mentions=("n_episodes", "sum"), cell=("n_f84_episodes_cell", "first")))
    per_ep["cats_per_episode"] = per_ep.mentions / per_ep.cell
    ys = D.year.loc[(D.year.variant == variant) & (D.year.panel == "observed") & (D.year.activity == "all") &
                    (D.year.position == "any")].set_index("year").sort_index()
    ax[5].plot(per_ep.index, per_ep.cats_per_episode, marker="o", ms=4.2, lw=1.7, color=COL["f84"], label=T("ef5_cats", lang))
    ax[5].plot(ys.index, ys.coding_depth_mean_f84, marker="^", ms=4.0, lw=1.5, color=OKABE[1],
               label=T("episodes_f84", lang))
    ax[5].plot(ys.index, ys.coding_depth_mean_all, marker="s", ms=3.8, lw=1.4, ls="--", color=COL["all"],
               label=T("all_episodes", lang))
    context(ax[5], lang, law_pos=0.5)
    year_axis(ax[5], lang)
    ax[5].set_ylabel(T("ef5_depth", lang))
    # Rótulos cortos y margen inferior: la caja de la leyenda cabe dentro del panel y no tapa las marcas del eje.
    _lo5, _hi5 = ax[5].get_ylim()
    ax[5].set_ylim(_lo5 - (_hi5 - _lo5) * 0.46, _hi5)
    legend_wrapped(ax[5], fontsize=FS_ANN, loc="lower right", frameon=True, framealpha=0.9, edgecolor="none",
                 title=T("ef5_depth", lang), title_fontsize=FS_LEG)
    panel(ax[5], "f", T("ef5_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    for _, r0 in top25.iterrows():
        r = {"__k": icd3_label(r0.code3, r0.icd_label_es, lang)}
        for y in YEARS:
            s = any_pos.loc[(any_pos.code3 == r0.code3) & (any_pos.year == y)]
            r[str(y)] = n_pct(s.n_episodes.iloc[0], s.pct_of_f84_episodes.iloc[0], lang) if len(s) else n_pct(0, 0.0, lang)
        r[{"es": "2019–2024", "en": "2019–2024"}[lang]] = n_pct(r0.n_episodes, r0.pct, lang)
        rows.append(r)
    r = {"__k": T("ef5_cats", lang)}
    for y in YEARS:
        r[str(y)] = num(per_ep.cats_per_episode.get(y, np.nan), 2, lang)
    r[{"es": "2019–2024", "en": "2019–2024"}[lang]] = num(per_ep.mentions.sum() / per_ep.cell.sum(), 2, lang)
    rows.append(r)
    r = {"__k": f"{T('ef5_depth', lang)} · {T('episodes_f84', lang)}"}
    for y in YEARS:
        r[str(y)] = num(ys.coding_depth_mean_f84.get(y, np.nan), 2, lang)
    r[{"es": "2019–2024", "en": "2019–2024"}[lang]] = T("not_estimable", lang)
    rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": {"es": "Categoría CIE-10 (tres caracteres)",
                                                          "en": "ICD-10 category (three characters)"}[lang]})
    numeric = pd.concat([any_pos.assign(block="codiagnoses_any"), sec_only.assign(block="principal_when_secondary_only"),
                         chap.assign(block="chapters"), blocks.assign(block="mental_blocks"),
                         per_ep.reset_index().assign(block="categories_per_episode", variant=variant)], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Diez categorías CIE-10 de tres caracteres más frecuentes entre los episodios con F84 "
               f"documentado, acumulado 2019–2024 (panel observado, cualquier posición); un episodio cuenta una sola vez "
               f"por categoría, de modo que el porcentaje es la proporción de episodios con al menos una mención. La "
               f"familia F84 está excluida del recuento de co-diagnósticos; la tabla acompañante conserva las veinticinco "
               f"primeras con su n y su porcentaje año a año. (b) Seis capítulos CIE-10 con más episodios afectados, por "
               f"año, en mapa de calor: cada celda es el número de episodios con al menos una mención del capítulo por "
               f"100 episodios con F84 del mismo año (el nombre completo del capítulo va en la fila, no en una leyenda). (c) Bloques de salud mental (F00–F99 sin F84): porcentaje de episodios con F84 que "
               f"tienen al menos un código del bloque, 2019 frente a 2024. (d) Diagnóstico principal de los episodios en "
               f"que F84 aparece solo como diagnóstico secundario (10 categorías más frecuentes, acumulado). (e) Cambio "
               f"entre 2019 y 2024 de las 10 categorías principales. (f) Categorías CIE-10 distintas por episodio con F84 "
               f"y profundidad diagnóstica media (diagnósticos codificados por episodio) de los episodios con F84 y de "
               f"todos los episodios GRD: la comparabilidad entre años depende de esta profundidad. Sombreado: disrupción "
               f"del reporte 2020–2021; línea punteada: Ley 21.545 (marzo de 2023) como contexto. Definición: {vl}."),
        "en": (f"(a) Ten most frequent three-character ICD-10 categories among episodes with documented F84, "
               f"pooled 2019–2024 (observed panel, any position); an episode counts once per category, so the percentage "
               f"is the proportion of episodes with at least one mention. The F84 family itself is excluded from the "
               f"co-diagnosis count; the companion table keeps the top twenty-five with their n and their percentage year "
               f"by year. (b) Six ICD-10 chapters with the most affected episodes, by year, as a heat map: each cell is "
               f"the number of episodes with at least one mention of the chapter per 100 episodes with F84 of the same "
               f"year (the full chapter name sits in the row, not in a legend). (c) Mental-health "
               f"blocks (F00–F99 excluding F84): percentage of episodes with F84 carrying at least one code of the block, "
               f"2019 versus 2024. (d) Principal diagnosis of episodes in which F84 appears only as a secondary diagnosis "
               f"(10 most frequent categories, pooled). (e) Change between 2019 and 2024 of the top 10 categories. "
               f"(f) Distinct ICD-10 categories per episode with F84 and mean coding depth (coded diagnoses per episode) "
               f"of episodes with F84 and of all GRD episodes: comparability across years depends on this depth. Shading: "
               f"2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context. Definition: {vl}."),
    }[lang]
    note = {
        "es": ("Celda: episodios con al menos una mención de la categoría (porcentaje de los episodios con F84 del mismo "
               "año). Panel observado, F84 en cualquier posición; el denominador anual es el número de episodios con F84 "
               "de esa celda y el acumulado es su suma 2019–2024. Un episodio puede aparecer en varias categorías: las "
               "columnas no suman 100 %. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_codiagnoses.csv, grd_codiagnosis_chapters.csv y grd_year_summary.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes with at least one mention of the category (percentage of the episodes with F84 of the same "
               "year). Observed panel, F84 in any position; the annual denominator is the number of episodes with F84 in "
               "that cell and the pooled figure is their 2019–2024 sum. One episode can appear in several categories: "
               "columns do not add to 100%. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_codiagnoses.csv, grd_codiagnosis_chapters.csv and grd_year_summary.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF5", "ef5_title", variant, lang), cap,
                  table_title("EF5", "ef5_title", variant, lang), note)


# ===========================================================================
# EF6 · Reingresos y multiplicidad
# ===========================================================================
HORIZONS = [30, 90, 365]
HOR_COLORS = {30: OKABE[0], 90: OKABE[2], 365: OKABE[1]}
MIN_ELIGIBLE = 30          # por debajo de 30 egresos elegibles el porcentaje no se interpreta (se marca, no se oculta)


def ef6(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF6_readmission_multiplicity"
    rd = D.readm.loc[(D.readm.panel == "observed") & (D.readm.variant == variant)]
    mu = D.mult.loc[(D.mult.panel == "observed") & (D.mult.variant == variant) & (D.mult.position == "any")]
    ys = D.year.loc[(D.year.variant == variant) & (D.year.panel == "observed") & (D.year.activity == "all") &
                    (D.year.position == "any")].set_index("year").sort_index()

    for era, sub in rd.loc[rd.position == "any"].groupby("era"):
        ctl.add(f"EF6_readmission_le_episodes[{variant}|{era}]", "n_discharges<=episodes", True,
                bool((sub.groupby("year").n_discharges.first() <= ys.n_episodes_f84.reindex(sub.year.unique())).all()),
                "los egresos índice del análisis de reingreso no superan los episodios anuales con F84", status=None)

    fig, ax = new_plate()

    def readm_lines(axis, column, lo, hi):
        weak_marks = []
        for h in HORIZONS:
            for era, sub in rd.loc[(rd.position == "any") & (rd.horizon_days == h)].groupby("era"):
                sub = sub.sort_values("year")
                stable = sub.loc[sub.n_eligible >= MIN_ELIGIBLE]
                weak = sub.loc[sub.n_eligible < MIN_ELIGIBLE]
                if len(stable):
                    axis.errorbar(stable.year, stable[column],
                                  yerr=[stable[column] - stable[lo], stable[hi] - stable[column]],
                                  marker="o", ms=3.8, lw=1.6, capsize=2.2, color=HOR_COLORS[h],
                                  label=f"{h} {T('days', lang).lower()}" if era == "2019-2020" else None)
                # Los años con menos de MIN_ELIGIBLE egresos elegibles NO se dibujan: el porcentaje procede de un
                # denominador de uno o dos egresos y colocarlo en el eje equivaldría a dibujar como 0 % (o como 50 %)
                # algo que no es estimable. Se rotula «n/e» al pie del año correspondiente.
                for _, r in weak.iterrows():
                    weak_marks.append(axis.annotate(f"{T('not_estimable', lang)}\n{h} {T('days', lang).lower()}",
                                                    xy=(float(r.year), 0.02), xycoords=("data", "axes fraction"),
                                                    ha="center", va="bottom", fontsize=FS_ANN, color=HOR_COLORS[h]))
        # La banda superior se reserva para la leyenda (una sola fila de tres horizontes) y las glosas de contexto
        # van debajo de ella, de modo que ninguna tapa a la otra en una celda de 90 mm.
        headroom(axis, 0.34)
        if weak_marks:
            # Franja al pie, FUERA de la escala, para las marcas «n/e»: escritas dentro del área de datos
            # caían sobre los marcadores de los horizontes que sí son estimables (defecto de S21 (a) y (b)),
            # y el lector podía leer el «n/e» como si fuera el valor de esos puntos. Las marcas del eje se
            # quedan en cero y arriba: la franja no representa ningún porcentaje, y por eso no se rotula.
            y0, y1 = axis.get_ylim()
            span = y1 - y0
            ticks = [q for q in mticker.MaxNLocator(nbins=6).tick_values(max(0.0, y0), y1) if 0.0 <= q <= y1]
            # La franja se MIDE, no se supone: con el 20 % fijo, la marca «n/e» de dos líneas del último
            # año subía hasta el marcador de 30 días y su recuadro blanco le mordía casi una cuarta parte
            # del disco. Se mide la altura real del rótulo sobre el renderizador y se abre la franja justa
            # (con un 40 % de holgura, porque el reparto todavía puede encoger el panel).
            fig_ = axis.figure
            fig_.canvas.draw()
            rr = fig_.canvas.get_renderer()
            ax_h = float(axis.get_window_extent(rr).height) or 1.0
            lab_h = max((float(a.get_window_extent(rr).height) for a in weak_marks), default=0.0)
            need = min(0.45, max(0.20, 0.02 + 1.40 * lab_h / ax_h))
            axis.set_ylim(y0 - need / (1.0 - need) * span, y1)
            if ticks:
                axis.set_yticks(ticks)
            axis.spines["left"].set_bounds(max(0.0, y0), y1)
        context(axis, lang, pandemic_pos=0.78, law_pos=0.78)
        year_axis(axis, lang)
        axis.set_ylabel(T("ef6_pct", lang))
        legend_wrapped(axis, fontsize=FS_TICK, title=T("ef6_horizon", lang), title_fontsize=FS_LEG, loc="upper left",
                       ncol=3, expand=False, columnspacing=0.9, frameon=True, framealpha=0.9, edgecolor="none")
        long_xlabel(axis, {"es": f"Año — series separadas por era de identificador (2019–2020 | 2021–2024); «n/e»: menos de {MIN_ELIGIBLE} egresos elegibles, porcentaje no estimable y por eso no representado",
                           "en": f"Year — series split by identifier era (2019–2020 | 2021–2024); 'n/e': fewer than {MIN_ELIGIBLE} eligible discharges, percentage not estimable and therefore not plotted"}[lang])

    readm_lines(ax[0], "pct_any_cause", "pct_any_cause_lo", "pct_any_cause_hi")
    panel(ax[0], "a", T("ef6_a", lang))
    readm_lines(ax[1], "pct_f84", "pct_f84_lo", "pct_f84_hi")
    panel(ax[1], "b", T("ef6_b", lang))

    # (c) episodios por identificador
    cats = ["1", "2", "3", "4-5", "6+"]
    eras = sorted(mu.era.unique())
    w = 0.36
    for i, era in enumerate(eras):
        s = mu.loc[mu.era == era].set_index("episodes_per_identifier")
        vals = [float(s.pct_persons.get(c, 0.0)) for c in cats]
        # `era` es la CLAVE de máquina («2019-2020»), la que compara la línea 2856 y la que viaja por el tidy;
        # el rótulo dibujado lleva la raya corta, como la leyenda y el eje de esta misma lámina.
        ax[2].bar(np.arange(len(cats)) + (i - 0.5) * w, vals, width=w, color=OKABE[i], label=C.yspan(era))
    ax[2].set_xticks(range(len(cats)))
    ax[2].set_xticklabels(cats)
    ax[2].set_xlabel({"es": "Episodios con F84 por identificador", "en": "Episodes with F84 per identifier"}[lang])
    ax[2].set_ylabel(T("ef6_pct_persons", lang))
    legend_wrapped(ax[2], fontsize=FS_TICK, title=T("ef6_era", lang), title_fontsize=FS_LEG)
    panel(ax[2], "c", T("ef6_c", lang))

    # (d) personas dentro del año y episodios por persona
    ax[3].bar(ys.index, ys.persons_within_year, width=0.6, color=COL["f84"], label=T("ef6_persons", lang))
    ax[3].set_ylabel(T("ef6_persons", lang))
    ax3b = ax[3].twinx()
    ax3b.plot(ys.index, ys.n_episodes_f84 / ys.persons_within_year.replace(0, np.nan), marker="o", ms=4.2, lw=1.7,
              color=OKABE[1], label=T("ef6_epi_person", lang))
    ax3b.set_ylabel(T("ef6_epi_person", lang))
    ax3b.grid(False)
    context(ax[3], lang, law=False, pandemic=False)
    year_axis(ax[3], lang)
    long_xlabel(ax[3], {"es": "Año (sombreado: disrupción del reporte 2020–2021) — personas solo dentro del año: el identificador cambia de formato entre 2020 y 2021",
                        "en": "Year (shading: 2020–2021 reporting disruption) — persons only within year: the identifier format changes between 2020 and 2021"}[lang])
    lo_d, hi_d = ax[3].get_ylim()
    ax[3].set_ylim(lo_d, hi_d * 1.18)
    h1, l1 = ax[3].get_legend_handles_labels()
    h2, l2 = ax3b.get_legend_handles_labels()
    legend_wrapped(ax[3], h1 + h2, l1 + l2, fontsize=FS_TICK, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[3], "d", T("ef6_d", lang))

    # (e) reingreso a 30 días por posición
    sub30 = rd.loc[rd.horizon_days == 30]
    w = 0.26
    for i, position in enumerate(POSITIONS):
        s = sub30.loc[sub30.position == position].sort_values("year")
        if s.empty:
            continue
        err = np.vstack([(s.pct_any_cause - s.pct_any_cause_lo).clip(lower=0), (s.pct_any_cause_hi - s.pct_any_cause).clip(lower=0)])
        ax[4].bar(s.year + (i - 1) * w, s.pct_any_cause, width=w, color=COL[position], yerr=err, capsize=2.0,
                  error_kw=dict(lw=0.9), label=T(POS_KEY[position], lang))
    context(ax[4], lang, law=False)
    year_axis(ax[4], lang)
    ax[4].set_ylabel(T("ef6_pct", lang))
    legend_wrapped(ax[4], fontsize=FS_TICK)
    panel(ax[4], "e", T("ef6_e", lang))

    # (f) estados del dato
    s365 = rd.loc[(rd.position == "any") & (rd.horizon_days == 365)].sort_values("year")
    w = 0.28
    ax[5].bar(s365.year - w, s365.n_discharges, width=w, color=COL["all"], label=T("ef6_discharges", lang))
    ax[5].bar(s365.year, s365.n_eligible, width=w, color=COL["f84"], label=T("ef6_eligible", lang))
    ax[5].bar(s365.year + w, s365.n_with_overlapping_next_admission, width=w, color=OKABE[3], label=T("ef6_overlap", lang))
    year_axis(ax[5], lang)
    ax[5].set_ylabel(T("episodes", lang))
    long_xlabel(ax[5], {"es": "Año — horizonte de 365 días: la elegibilidad cae al final de cada era de identificador",
                        "en": "Year — 365-day horizon: eligibility falls at the end of each identifier era"}[lang])
    legend_wrapped(ax[5], fontsize=FS_TICK, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[5], "f", T("ef6_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    for h in HORIZONS:
        for column, lo, hi, lab in (("pct_any_cause", "pct_any_cause_lo", "pct_any_cause_hi",
                                     {"es": "cualquier causa", "en": "any cause"}[lang]),
                                    ("pct_f84", "pct_f84_lo", "pct_f84_hi",
                                     {"es": "con F84", "en": "with F84"}[lang])):
            r = {"__k": f"{h} {T('days', lang).lower()} — {lab}"}
            for y in YEARS:
                s = rd.loc[(rd.position == "any") & (rd.horizon_days == h) & (rd.year == y)]
                if not len(s):
                    r[str(y)] = T("not_estimable", lang)
                    continue
                k = num(s[column.replace('pct_', 'n_readmitted_')].iloc[0] if column != 'pct_any_cause'
                        else s.n_readmitted_any_cause.iloc[0], 0, lang)
                n_el = float(s.n_eligible.iloc[0])
                # Por debajo de MIN_ELIGIBLE egresos elegibles el porcentaje no es estimable: se muestran los
                # recuentos y «n/e», nunca un porcentaje calculado sobre uno o dos egresos.
                pctxt = (val_ci(s[column].iloc[0], s[lo].iloc[0], s[hi].iloc[0], 1, lang)
                         if n_el >= MIN_ELIGIBLE else T("not_estimable", lang))
                r[str(y)] = f"{k}/{num(n_el, 0, lang)}; {pctxt}"
            rows.append(r)
    for era in eras:
        s = mu.loc[mu.era == era].set_index("episodes_per_identifier")
        # `era` es la CLAVE de máquina («2019-2020»), la que filtra el tidy en la línea de arriba; el
        # rótulo de la fila que lee el lector lleva la raya corta, igual que la leyenda del panel (c).
        r = {"__k": f"{T('ef6_c', lang)} — {C.yspan(era)}"}
        for y in YEARS:
            r[str(y)] = T("not_estimable", lang)
        r[str(YEARS[0])] = "; ".join(f"{c}: {n_pct(s.n_persons.get(c, 0), s.pct_persons.get(c, 0.0), lang)}" for c in cats)
        rows.append(r)
    r = {"__k": T("ef6_persons", lang)}
    for y in YEARS:
        r[str(y)] = num(ys.persons_within_year.get(y, np.nan), 0, lang)
    rows.append(r)
    r = {"__k": T("ef6_epi_person", lang)}
    for y in YEARS:
        r[str(y)] = num(ys.n_episodes_f84.get(y, np.nan) / ys.persons_within_year.get(y, np.nan), 2, lang)
    rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": {"es": "Indicador", "en": "Indicator"}[lang]})
    numeric = pd.concat([rd.assign(block="readmission"), mu.assign(block="multiplicity"),
                         ys.reset_index().assign(block="persons_within_year")], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Reingreso hospitalario por cualquier causa y (b) reingreso con un código F84 documentado, dentro de "
               f"30, 90 y 365 días de un egreso con F84 (IC 95 % de Wilson). Las series se cortan entre las eras de "
               f"identificador 2019–2020 y 2021–2024: el formato del identificador cambia entre 2020 y 2021 y ninguna "
               f"persona se sigue a través del corte. Los años cuyo horizonte deja menos de 30 egresos elegibles no se "
               f"representan y se rotulan «n/e»: un porcentaje calculado sobre uno o dos egresos no es estimable. "
               f"(c) Distribución de episodios con F84 por identificador dentro de "
               f"cada era. (d) Personas distintas dentro de cada año (barras) y episodios por persona (línea, eje "
               f"derecho); las personas nunca se deduplican entre años. (e) Reingreso a 30 días por cualquier causa según "
               f"la posición del código F84 en el episodio índice. (f) Estados del dato del análisis de reingreso a 365 "
               f"días: egresos índice, egresos elegibles con horizonte completo dentro de la era y egresos con un ingreso "
               f"siguiente solapado. Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo de "
               f"2023) como contexto. Definición: {vl}. El reingreso describe el uso hospitalario registrado, no la "
               f"evolución clínica."),
        "en": (f"(a) All-cause readmission and (b) readmission with a documented F84 code, within 30, 90 and 365 days of a "
               f"discharge with F84 (Wilson 95% CI). The series are cut between the 2019–2020 and 2021–2024 identifier "
               f"eras: the identifier format changes between 2020 and 2021 and no person is followed across the cut. Years "
               f"whose horizon leaves fewer than 30 eligible discharges are not plotted and are labelled 'n/e': a "
               f"percentage computed on one or two discharges is not estimable. "
               f"(c) Distribution of episodes with F84 per identifier within each era. (d) Distinct persons within each "
               f"year (bars) and episodes per person (line, right axis); persons are never deduplicated across years. "
               f"(e) 30-day all-cause readmission by the position of the F84 code in the index episode. (f) Data states of "
               f"the 365-day readmission analysis: index discharges, discharges eligible with a full horizon inside the "
               f"era, and discharges with an overlapping next admission. Shading: 2020–2021 reporting disruption; dotted "
               f"line: Law 21.545 (March 2023) as context. Definition: {vl}. Readmission describes recorded hospital use, "
               f"not clinical course."),
    }[lang]
    note = {
        "es": ("Celda: reingresos/egresos elegibles; porcentaje (IC 95 % de Wilson). Unidad: egreso índice con F84 "
               "documentado y fechas válidas dentro de la era de identificador. Las filas de multiplicidad se refieren a "
               "toda la era (columna del primer año) y no a un año concreto: «n/e» en las demás columnas. " +
               NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_readmission.csv, grd_multiplicity.csv y grd_year_summary.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: readmissions/eligible discharges; percentage (Wilson 95% CI). Unit: index discharge with documented "
               "F84 and valid dates within the identifier era. Multiplicity rows refer to the whole era (shown in the "
               "first-year column) and not to a single year: 'n/e' in the other columns. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_readmission.csv, grd_multiplicity.csv and grd_year_summary.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF6", "ef6_title", variant, lang), cap,
                  table_title("EF6", "ef6_title", variant, lang), note)


# ===========================================================================
# EF7 · Detalle de edad
# ===========================================================================
def national_population(D, year: int, sex: str | None = None) -> pd.Series:
    """Población nacional INE (base 2017, 30 de junio) por grupo etario quinquenal; sexo None = ambos."""
    p = D.pop_reg
    s = p.loc[(p.level == "national") & (p.year == year) & (p.age_group != "TOTAL")]
    s = s.loc[s.sex == (sex if sex else "TOTAL")]
    return s.groupby("age_group").population.sum()


def ef7(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF7_age_detail"
    a1 = D.age1.loc[(D.age1.panel == "observed") & (D.age1.variant == variant) & (D.age1.position == "any")]
    asx = D.age_sex.loc[(D.age_sex.panel == "observed") & (D.age_sex.variant == variant) &
                        (D.age_sex.position == "any") & (D.age_sex.activity == "all")]
    for y in YEARS:
        exp = float(D.year.loc[(D.year.year == y) & (D.year.variant == variant) & (D.year.panel == "observed") &
                               (D.year.activity == "all") & (D.year.position == "any"), "n_episodes_f84"].iloc[0])
        ctl.add(f"EF7_single_year_sum[{variant}]", y, exp, float(a1.loc[a1.year == y, "n_episodes"].sum()),
                "grd_age_single_year (todas las edades y sexos) frente a grd_year_summary")
        ctl.add(f"EF7_age_sex_sum[{variant}]", y, exp, float(asx.loc[asx.year == y, "n_f84"].sum()),
                "grd_age_sex_year (todos los grupos y sexos) frente a grd_year_summary")

    known = a1.loc[a1.age_label != "unknown"].copy()
    known["age"] = known.age_years.astype(float)

    fig, ax = new_plate()
    # (a) edad simple por sexo, 2019 y 2024
    for y, ls in ((2019, "--"), (2024, "-")):
        for sex, colour in (("HOMBRE", COL["male"]), ("MUJER", COL["female"])):
            s = known.loc[(known.year == y) & (known.sex == sex)].groupby("age", as_index=False).n_episodes.sum()
            tot = s.n_episodes.sum()
            if tot == 0:
                continue
            s = s.loc[s.age <= 40]
            ax[0].plot(s.age, 100 * s.n_episodes / tot, ls=ls, lw=1.6, color=colour,
                       label=f"{y} · {T('male', lang) if sex == 'HOMBRE' else T('female', lang)}")
    ax[0].set_xlabel(T("age_years", lang))
    ax[0].set_ylabel({"es": "% de los episodios del año y sexo", "en": "% of the year's and sex's episodes"}[lang])
    legend_wrapped(ax[0], fontsize=FS_TICK)
    panel(ax[0], "a", T("ef7_a", lang))

    # (b) tasa por 100.000 habitantes según grupo etario y año
    groups = [g for g in C.AGE_GROUPS]
    rate_rows = []
    for i, y in enumerate(YEARS):
        pop = national_population(D, y)
        s = asx.loc[(asx.year == y) & (asx.age_group != "unknown")].groupby("age_group").n_f84.sum()
        vals, los_, his = [], [], []
        for g in groups:
            k = float(s.get(g, 0.0))
            n = float(pop.get(g, np.nan))
            r, lo, hi = rate_ci(k, n)
            vals.append(r); los_.append(lo); his.append(hi)
            rate_rows.append(dict(year=y, age_group=g, n_f84=k, population=n, rate_per_100k=r, rate_lo=lo, rate_hi=hi))
        ax[1].plot(range(len(groups)), vals, marker="o", ms=3.4, lw=1.5, color=YEAR_COLORS[i], label=str(y))
    ax[1].set_xticks(range(len(groups)))
    # Diecisiete grupos etarios en una celda de 88 mm: a 60° cada rótulo se imprimía sobre el siguiente
    # («20-24» sobre «25-29»). En vertical cada uno ocupa el ancho de una línea de texto y los diecisiete
    # caben sin reducir el cuerpo por debajo de la norma ni ocultar ninguno.
    ax[1].set_xticklabels(groups, rotation=90, ha="center", va="top", fontsize=FS_TICK)
    ax[1].set_yscale("log")
    ax[1].set_xlabel(T("age_group", lang))
    ax[1].set_ylabel(T("rate_100k_pop", lang))
    legend_wrapped(ax[1], ncol=3, fontsize=FS_TICK, title=T("year", lang), title_fontsize=FS_LEG)
    note_in_panel(ax[1], T("ef7_place_note", lang))
    panel(ax[1], "b", T("ef7_b", lang))
    rates = pd.DataFrame(rate_rows)

    # (c) razón hombre:mujer por grupo etario (acumulado 2019–2024)
    ratio_rows = []
    for g in groups:
        m = float(asx.loc[(asx.age_group == g) & (asx.sex == "HOMBRE"), "n_f84"].sum())
        f = float(asx.loc[(asx.age_group == g) & (asx.sex == "MUJER"), "n_f84"].sum())
        r, lo, hi = ratio_ci(m, f)
        ratio_rows.append(dict(age_group=g, n_male=m, n_female=f, ratio=r, ratio_lo=lo, ratio_hi=hi))
    R = pd.DataFrame(ratio_rows)
    xs = np.arange(len(R))
    ok = R.ratio.notna()
    ax[2].errorbar(xs[ok.to_numpy()], R.ratio[ok], yerr=[(R.ratio - R.ratio_lo)[ok], (R.ratio_hi - R.ratio)[ok]],
                   fmt="o", ms=4.2, lw=1.4, capsize=2.4, color=COL["f84"])
    ax[2].axhline(1.0, color="#444444", ls=":", lw=1.0)
    ax[2].set_xticks(xs)
    ax[2].set_xticklabels(R.age_group, rotation=90, ha="center", va="top", fontsize=FS_TICK)
    ax[2].set_ylabel(T("ef7_ratio", lang))
    ax[2].set_yscale("log")
    panel(ax[2], "c", T("ef7_c", lang))

    # (d) desplazamiento de la distribución de edad
    med = {}
    for y, colour in ((2019, COL["y2019"]), (2024, COL["y2024"])):
        s = known.loc[known.year == y].groupby("age", as_index=False).n_episodes.sum().sort_values("age")
        cum = 100 * s.n_episodes.cumsum() / s.n_episodes.sum()
        ax[3].plot(s.age, cum, lw=1.9, color=colour, label=str(y))
        med[y] = float(np.interp(50, cum, s.age))
    for y, colour in ((2019, COL["y2019"]), (2024, COL["y2024"])):
        ax[3].axvline(med[y], color=colour, ls=":", lw=1.2)
    ax[3].axhline(50, color="#888888", ls=":", lw=1.0)
    ax[3].set_xlim(0, 60)
    ax[3].set_xlabel(T("age_years", lang))
    ax[3].set_ylabel(T("ef7_cum", lang))
    legend_wrapped(ax[3], fontsize=FS_TICK, title={"es": f"Mediana: {num(med[2019], 1, lang)} → {num(med[2024], 1, lang)} años",
                                      "en": f"Median: {num(med[2019], 1, lang)} → {num(med[2024], 1, lang)} years"}[lang],
                 title_fontsize=FS_LEG)
    panel(ax[3], "d", T("ef7_d", lang))

    # (e) mapa de calor tasa por grupo etario y año
    mat = rates.pivot_table(index="age_group", columns="year", values="rate_per_100k").reindex(groups)
    heat(ax[4], mat, lambda v: num(v, 1, lang), cmap="YlOrRd", fontsize=FS_CELL, fig=fig, cbar_label=T("rate_100k_pop", lang))
    ax[4].set_xlabel(T("year", lang))
    panel(ax[4], "e", T("ef7_e", lang))

    # (f) tasa por edad y sexo en 2024
    for sex, colour, lab in (("HOMBRE", COL["male"], T("male", lang)), ("MUJER", COL["female"], T("female", lang))):
        pop = national_population(D, 2024, sex)
        s = asx.loc[(asx.year == 2024) & (asx.sex == sex) & (asx.age_group != "unknown")].groupby("age_group").n_f84.sum()
        vals, los_, his = [], [], []
        for g in groups:
            r, lo, hi = rate_ci(float(s.get(g, 0.0)), float(pop.get(g, np.nan)))
            vals.append(r); los_.append(lo); his.append(hi)
        vals = np.array(vals); los_ = np.array(los_); his = np.array(his)
        ax[5].errorbar(range(len(groups)), vals, yerr=[np.clip(vals - los_, 0, None), np.clip(his - vals, 0, None)],
                       marker="o", ms=3.8, lw=1.5, capsize=2.2, color=colour, label=lab)
    ax[5].set_xticks(range(len(groups)))
    ax[5].set_xticklabels(groups, rotation=90, ha="center", va="top", fontsize=FS_TICK)
    ax[5].set_yscale("log")
    ax[5].set_ylabel(T("rate_100k_pop", lang))
    legend_wrapped(ax[5], fontsize=FS_TICK)
    note_in_panel(ax[5], T("ef7_place_note", lang))
    panel(ax[5], "f", T("ef7_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    for g in groups:
        r = {"__k": g}
        for y in YEARS:
            s = rates.loc[(rates.age_group == g) & (rates.year == y)]
            r[str(y)] = (f"{num(s.n_f84.iloc[0], 0, lang)}; {val_ci(s.rate_per_100k.iloc[0], s.rate_lo.iloc[0], s.rate_hi.iloc[0], 1, lang)}"
                         if len(s) else T("not_estimable", lang))
        rr = R.loc[R.age_group == g]
        r[{"es": "Razón H:M 2019–2024", "en": "M:F ratio 2019–2024"}[lang]] = (
            val_ci(rr.ratio.iloc[0], rr.ratio_lo.iloc[0], rr.ratio_hi.iloc[0], 2, lang) if len(rr) else T("not_estimable", lang))
        rows.append(r)
    r = {"__k": {"es": "Edad desconocida (episodios)", "en": "Unknown age (episodes)"}[lang]}
    for y in YEARS:
        r[str(y)] = num(a1.loc[(a1.year == y) & (a1.age_label == "unknown"), "n_episodes"].sum(), 0, lang)
    r[{"es": "Razón H:M 2019–2024", "en": "M:F ratio 2019–2024"}[lang]] = T("not_estimable", lang)
    rows.append(r)
    r = {"__k": {"es": "Mediana de edad (años)", "en": "Median age (years)"}[lang]}
    for y in YEARS:
        s = known.loc[known.year == y].groupby("age", as_index=False).n_episodes.sum().sort_values("age")
        cum = 100 * s.n_episodes.cumsum() / s.n_episodes.sum()
        r[str(y)] = num(float(np.interp(50, cum, s.age)), 1, lang)
    r[{"es": "Razón H:M 2019–2024", "en": "M:F ratio 2019–2024"}[lang]] = T("not_estimable", lang)
    rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": T("age_group", lang)})
    numeric = pd.concat([rates.assign(block="age_specific_rates", variant=variant),
                         R.assign(block="male_female_ratio", variant=variant),
                         a1.assign(block="single_year_age")], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Distribución de la edad simple (0–40 años) de los episodios con F84 documentado por sexo, 2019 "
               f"(discontinuo) y 2024 (continuo), como porcentaje de los episodios del mismo año y sexo. (b) Tasa de "
               f"episodios por 100.000 habitantes según grupo etario quinquenal y año (escala logarítmica). (c) Razón "
               f"hombre:mujer de los episodios por grupo etario, acumulado 2019–2024, con IC 95 % por el método delta en "
               f"escala logarítmica. (d) Distribución acumulada de la edad en 2019 y 2024, con la mediana marcada. "
               f"(e) Tasa por 100.000 habitantes: grupo etario × año. (f) Tasa por grupo etario y sexo en 2024 con IC "
               f"95 % exactos de Poisson. En (b), (e) y (f) el numerador se localiza por lugar de atención (hospitales "
               f"públicos con GRD) y el denominador por residencia (proyecciones INE base 2017, 30 de junio), de modo que "
               f"la tasa es una lectura complementaria y no la tasa de uso de una población definida. Los episodios con "
               f"edad desconocida (informados en la tabla acompañante) quedan fuera de las tasas y nunca se imputan. "
               f"Definición: {vl}. Reconocimiento administrativo, no prevalencia ni incidencia."),
        "en": (f"(a) Single-year age distribution (0–40 years) of episodes with documented F84 by sex, 2019 (dashed) and "
               f"2024 (solid), as a percentage of the episodes of the same year and sex. (b) Episode rate per 100,000 "
               f"population by five-year age group and year (log scale). (c) Male-to-female ratio of episodes by age "
               f"group, pooled 2019–2024, with 95% CI by the delta method on the log scale. (d) Cumulative age "
               f"distribution in 2019 and 2024, with the median marked. (e) Rate per 100,000 population: age group × "
               f"year. (f) Rate by age group and sex in 2024 with exact Poisson 95% CIs. In (b), (e) and (f) the "
               f"numerator is located by place of care (public hospitals with GRD) and the denominator by residence (INE "
               f"projections, 2017 base, 30 June), so the rate is a complementary reading and not the use rate of a "
               f"defined population. Episodes with unknown age (reported in the companion table) are excluded from the "
               f"rates and never imputed. Definition: {vl}. Administrative recognition, not prevalence or incidence."),
    }[lang]
    note = {
        "es": ("Celda: episodios con F84 documentado; tasa por 100.000 habitantes (IC 95 % exacto de Poisson). "
               "Denominador: población nacional INE del mismo año y grupo etario (base 2017, 30 de junio, residencia); "
               "el numerador se registra por lugar de atención. Panel observado, F84 en cualquier posición, todas las "
               "actividades. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_age_single_year.csv, grd_age_sex_year.csv e "
                           "ine_population_region_national_year_age_sex.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes with documented F84; rate per 100,000 population (exact Poisson 95% CI). Denominator: INE "
               "national population of the same year and age group (2017 base, 30 June, residence); the numerator is "
               "recorded by place of care. Observed panel, F84 in any position, all activities. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_age_single_year.csv, grd_age_sex_year.csv and "
                           "ine_population_region_national_year_age_sex.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF7", "ef7_title", variant, lang), cap,
                  table_title("EF7", "ef7_title", variant, lang), note)


# ===========================================================================
# EF8 · Hospitales
# ===========================================================================
EF8_TOP = 12          # hospitales dibujados en el mapa de calor; el resto va agregado en una fila explícita


def ef8(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF8_hospitals"
    h = D.hosp.loc[D.hosp.variant == variant].copy()
    h["rate"] = PER * h.n_f84_any / h.n_episodes_total.replace(0, np.nan)
    for y in YEARS:
        exp = float(D.year.loc[(D.year.year == y) & (D.year.variant == variant) & (D.year.panel == "observed") &
                               (D.year.activity == "all") & (D.year.position == "any"), "n_episodes_f84"].iloc[0])
        ctl.add(f"EF8_hospital_sum[{variant}]", y, exp, float(h.loc[h.year == y, "n_f84_any"].sum()),
                "grd_hospital_year (todos los hospitales) frente a grd_year_summary")
        ctl.add(f"EF8_hospitals_observed[{variant}]", y, CFG.CONTROLS["grd_hospitals_observed"][y],
                int(h.loc[h.year == y, "COD_HOSPITAL"].nunique()), "hospitales observados por año (config.CONTROLS)")

    fig, ax = new_plate()
    # (a) mapa de calor de tasas por hospital. El diseño apaisado ponía 25 hospitales con su nombre completo en una
    #     celda de 140 mm; en la celda vertical de 90 mm eso obligaba a reducir el nombre por debajo del cuerpo
    #     mínimo y empujaba los ejes de toda la columna. Aquí van los doce hospitales con más episodios con F84 y
    #     una fila final con el RESTO de los hospitales del año (tasa agregada, no promedio de tasas), de modo que
    #     ningún hospital desaparece del panel; la tabla acompañante conserva los veinticinco primeros uno a uno.
    ranked = (h.groupby(["COD_HOSPITAL", "hospital_name"], as_index=False).n_f84_any.sum()
              .sort_values("n_f84_any", ascending=False))
    top = ranked.head(25)                                   # tabla acompañante
    top_plot = ranked.head(EF8_TOP)                         # lámina
    mat = (h.loc[h.COD_HOSPITAL.isin(top_plot.COD_HOSPITAL)]
           .pivot_table(index="COD_HOSPITAL", columns="year", values="rate")
           .reindex(top_plot.COD_HOSPITAL))
    rest_codes = set(ranked.COD_HOSPITAL) - set(top_plot.COD_HOSPITAL)
    rest = h.loc[h.COD_HOSPITAL.isin(rest_codes)].groupby("year").agg(n_f84=("n_f84_any", "sum"),
                                                                     n_tot=("n_episodes_total", "sum"))
    rest_rate = pd.Series({y: (PER * rest.loc[y, "n_f84"] / rest.loc[y, "n_tot"]
                               if y in rest.index and rest.loc[y, "n_tot"] > 0 else np.nan) for y in mat.columns})
    mat = pd.concat([mat, rest_rate.to_frame().T.set_axis(["__rest"])])
    names = [tick_label(abbreviate_hospital(n, 18), 20) for n in top_plot.hospital_name]
    names.append(f"{T('ef8_other_hosp', lang)} ({len(rest_codes)})")
    heat(ax[0], mat, lambda v: num(v, 0, lang), cmap="YlGnBu", fontsize=FS_CELL, ylabels=names, fig=fig,
         cbar_label=T("ef8_hosp_rate", lang))
    ax[0].tick_params(axis="y", labelsize=FS_CELL)
    ax[0].set_xlabel(T("year", lang))
    ctl.info(f"EF8_hospitals_drawn[{variant}]", "n_drawn_of_total", f"{EF8_TOP}/{int(ranked.COD_HOSPITAL.nunique())}",
             "la lámina dibuja los doce hospitales con más episodios y una fila agregada con el resto; la tabla conserva los 25 primeros")
    panel(ax[0], "a", T("ef8_a", lang))

    # (b) estabilidad del orden entre años
    pairs = [(YEARS[i], YEARS[i + 1]) for i in range(len(YEARS) - 1)] + [(YEARS[0], YEARS[-1])]
    rho_rows = []
    for y0, y1 in pairs:
        a = h.loc[(h.year == y0) & (h.n_episodes_total > 0), ["COD_HOSPITAL", "rate"]].set_index("COD_HOSPITAL")
        b = h.loc[(h.year == y1) & (h.n_episodes_total > 0), ["COD_HOSPITAL", "rate"]].set_index("COD_HOSPITAL")
        common = a.index.intersection(b.index)
        if len(common) >= 5:
            rho, p = stats.spearmanr(a.loc[common, "rate"], b.loc[common, "rate"])
        else:
            rho, p = np.nan, np.nan
        rho_rows.append(dict(pair=f"{y0}–{y1}", year_from=y0, year_to=y1, n_hospitals=len(common), spearman_rho=rho, p_value=p))
    RH = pd.DataFrame(rho_rows)
    ax[1].bar(range(len(RH)), RH.spearman_rho, color=[COL["f84"]] * (len(RH) - 1) + [OKABE[1]])
    ax[1].set_xticks(range(len(RH)))
    # Seis pares de años en una celda de 88 mm: girados 45° cada rótulo caía sobre el siguiente. Partidos en
    # dos líneas caben derechos, se leen sin girar la cabeza y el par completo sigue en la tabla acompañante.
    ax[1].set_xticklabels([str(q).replace("–", "–\n") for q in RH.pair], rotation=0, fontsize=FS_TICK)
    ax[1].set_ylabel(T("ef8_rho", lang))
    # ρ no pasa de 1 y las marcas llegan hasta 1: el aire de arriba es solo el sitio del rótulo «n=…», que
    # dentro de la barra se leía sobre el color.
    ax[1].set_ylim(0, 1.12)
    ax[1].set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for i, r0 in RH.iterrows():
        # «n = 65» junto a «n = 65» de la barra siguiente se leían como una sola cadena en una celda de
        # 88 mm: la forma compacta y el colocador medido dejan un hueco claro entre los seis rótulos.
        C.plate_value_label(ax[1], i, (r0.spearman_rho if np.isfinite(r0.spearman_rho) else 0.0),
                            f"n={num(r0.n_hospitals, 0, lang)}", fontsize=FS_ANN)
    panel(ax[1], "b", T("ef8_b", lang))

    # (c) contribución de los 10 hospitales mayores
    shares, shares_fixed = [], []
    top10_2024 = h.loc[h.year == 2024].nlargest(10, "n_f84_any").COD_HOSPITAL.tolist()
    for y in YEARS:
        s = h.loc[h.year == y]
        tot = s.n_f84_any.sum()
        shares.append(100 * s.nlargest(10, "n_f84_any").n_f84_any.sum() / tot if tot else np.nan)
        shares_fixed.append(100 * s.loc[s.COD_HOSPITAL.isin(top10_2024), "n_f84_any"].sum() / tot if tot else np.nan)
    ax[2].plot(YEARS, shares, marker="o", ms=4.2, lw=1.7, color=COL["f84"],
               label={"es": "10 mayores del propio año", "en": "10 largest of the same year"}[lang])
    ax[2].plot(YEARS, shares_fixed, marker="s", ms=4.0, lw=1.5, ls="--", color=OKABE[1],
               label={"es": "10 mayores de 2024 (fijos)", "en": "10 largest of 2024 (fixed)"}[lang])
    # Las dos glosas de contexto van al pie, en la banda que las series dejan libre: a media altura la de la
    # Ley caía sobre la serie de los diez mayores del propio año, y la leyenda ocupa la banda de arriba.
    context(ax[2], lang, pandemic_pos=0.03, law_pos=0.03)
    year_axis(ax[2], lang)
    ax[2].set_ylabel(T("ef8_share_top10", lang))
    legend_wrapped(ax[2], fontsize=FS_TICK, loc="upper right", width=22, expand=True,
                   frameon=True, framealpha=0.92, edgecolor="none")
    panel(ax[2], "c", T("ef8_c", lang))

    # (d) panel fijo frente a hospitales incorporados
    w = 0.38
    fixed = h.loc[h.in_fixed_panel].groupby("year").agg(n_f84=("n_f84_any", "sum"), n_tot=("n_episodes_total", "sum"))
    added = h.loc[~h.in_fixed_panel].groupby("year").agg(n_f84=("n_f84_any", "sum"), n_tot=("n_episodes_total", "sum"))
    ax[3].bar(fixed.index - w / 2, fixed.n_f84, width=w, color=COL["fixed"], label=T("panel_fixed", lang))
    ax[3].bar(added.index + w / 2, added.n_f84, width=w, color=COL["new"], label=T("ef8_added", lang))
    ax[3].set_ylabel(T("episodes_f84", lang))
    ax3b = ax[3].twinx()
    ax3b.plot(fixed.index, PER * fixed.n_f84 / fixed.n_tot, marker="o", ms=3.8, lw=1.5, color="#1a1a1a")
    ax3b.plot(added.index, PER * added.n_f84 / added.n_tot, marker="s", ms=3.6, lw=1.4, ls="--", color="#666666")
    ax3b.set_ylabel(T("rate_100k_ep", lang))
    ax3b.grid(False)
    year_axis(ax[3], lang)
    legend_wrapped(ax[3], fontsize=FS_TICK, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    long_xlabel(ax[3], {"es": "Año — líneas (eje derecho): tasa por 100.000 episodios de cada grupo",
                        "en": "Year — lines (right axis): rate per 100,000 episodes of each group"}[lang])
    panel(ax[3], "d", T("ef8_d", lang))

    # (e) distribución de tasas por hospital
    data = [h.loc[(h.year == y) & (h.n_episodes_total > 0), "rate"].replace(0, np.nan).dropna().to_numpy() for y in YEARS]
    bp = ax[4].boxplot(data, positions=YEARS, widths=0.55, showfliers=False, patch_artist=True)
    for b in bp["boxes"]:
        b.set(facecolor="#dfe9f3", edgecolor="#33546e", linewidth=0.9)
    for k, y in enumerate(YEARS):
        xs = np.random.default_rng(7 + k).normal(y, 0.06, size=len(data[k]))
        ax[4].plot(xs, data[k], "o", ms=2.2, alpha=0.45, color=COL["f84"])
    ax[4].set_yscale("log")
    year_axis(ax[4], lang)
    ax[4].set_ylabel(T("ef8_hosp_rate", lang))
    note_in_panel(ax[4], {"es": "Cajas: mediana y cuartiles de los hospitales con episodios; hospitales sin episodios con F84 excluidos de la escala logarítmica",
                          "en": "Boxes: median and quartiles of hospitals with episodes; hospitals with no F84 episodes are outside the log scale"}[lang],
                  0.02, 0.985, va="top", bbox=CTX_BBOX)
    panel(ax[4], "e", T("ef8_e", lang))

    # (f) concentración (Lorenz)
    ginis = {}
    for y, colour in ((2019, COL["y2019"]), (2024, COL["y2024"])):
        v = np.sort(h.loc[h.year == y, "n_f84_any"].to_numpy(dtype=float))
        cum = np.concatenate([[0], np.cumsum(v) / v.sum()]) * 100
        xs = np.linspace(0, 100, len(cum))
        ginis[y] = gini(v)
        ax[5].plot(xs, cum, lw=1.9, color=colour, label=f"{y} · Gini {num(ginis[y], 2, lang)}")
    ax[5].plot([0, 100], [0, 100], ls=":", color="#888888", lw=1.0)
    ax[5].set_xlabel(T("ef8_cum_hosp", lang))
    ax[5].set_ylabel(T("ef8_cum_epi", lang))
    legend_wrapped(ax[5], fontsize=FS_TICK)
    panel(ax[5], "f", T("ef8_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    for _, r0 in top.iterrows():
        r = {"__k": abbreviate_hospital(r0.hospital_name, 40)}
        for y in YEARS:
            s = h.loc[(h.COD_HOSPITAL == r0.COD_HOSPITAL) & (h.year == y)]
            if s.empty:
                r[str(y)] = T("not_estimable", lang)
            else:
                r[str(y)] = f"{num(s.n_f84_any.iloc[0], 0, lang)}; {num(s.rate.iloc[0], 0, lang)}"
        rows.append(r)
    for lab, frame in ((T("panel_fixed", lang), fixed), (T("ef8_added", lang), added)):
        r = {"__k": lab}
        for y in YEARS:
            if y in frame.index and frame.loc[y, "n_tot"] > 0:
                r[str(y)] = f"{num(frame.loc[y, 'n_f84'], 0, lang)}; {num(PER * frame.loc[y, 'n_f84'] / frame.loc[y, 'n_tot'], 0, lang)}"
            else:
                r[str(y)] = T("not_estimable", lang)
        rows.append(r)
    r = {"__k": T("ef8_share_top10", lang)}
    for y, v in zip(YEARS, shares):
        r[str(y)] = pct(v, lang)
    rows.append(r)
    r = {"__k": T("n_hospitals", lang)}
    for y in YEARS:
        r[str(y)] = num(h.loc[h.year == y, "COD_HOSPITAL"].nunique(), 0, lang)
    rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": {"es": "Hospital o grupo", "en": "Hospital or group"}[lang]})
    numeric = pd.concat([h.assign(block="hospital_year"), RH.assign(block="rank_stability", variant=variant),
                         pd.DataFrame(dict(year=YEARS, share_top10_same_year=shares, share_top10_2024=shares_fixed,
                                           block="top10_share", variant=variant))], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Tasa de episodios con F84 documentado por 100.000 episodios GRD del propio hospital y año, en los 25 "
               f"hospitales con más episodios con F84 en 2019–2024 (nombres abreviados; la tabla acompañante conserva los "
               f"recuentos). (b) Estabilidad del ordenamiento: ρ de Spearman entre las tasas hospitalarias de años "
               f"consecutivos y entre 2019 y 2024, sobre los hospitales presentes en ambos años (n indicado). "
               f"(c) Porcentaje de los episodios con F84 aportado por los diez hospitales mayores de cada año y por los "
               f"diez mayores de 2024 mantenidos fijos. (d) Panel fijo de 65 hospitales frente a los hospitales "
               f"incorporados en 2023–2024: episodios (barras) y tasa por 100.000 episodios de cada grupo (líneas, eje "
               f"derecho). (e) Distribución de las tasas hospitalarias por año (caja: mediana y cuartiles; puntos: "
               f"hospitales; escala logarítmica). (f) Concentración de los episodios con F84 entre hospitales: curva de "
               f"Lorenz de 2019 y 2024 con el índice de Gini. Ninguna comparación entre hospitales debe leerse como "
               f"medida de calidad: refleja composición de casos, profundidad de codificación y cartera de servicios. "
               f"Definición: {vl}."),
        "en": (f"(a) Rate of episodes with documented F84 per 100,000 GRD episodes of the same hospital and year, for the "
               f"25 hospitals with most episodes with F84 in 2019–2024 (abbreviated names; the companion table keeps the "
               f"counts). (b) Rank stability: Spearman ρ between hospital rates of consecutive years and between 2019 and "
               f"2024, over hospitals present in both years (n shown). (c) Percentage of episodes with F84 contributed by "
               f"each year's ten largest hospitals and by the ten largest of 2024 held fixed. (d) Fixed panel of 65 "
               f"hospitals versus hospitals added in 2023–2024: episodes (bars) and rate per 100,000 episodes of each "
               f"group (lines, right axis). (e) Distribution of hospital rates by year (box: median and quartiles; points: "
               f"hospitals; log scale). (f) Concentration of episodes with F84 across hospitals: Lorenz curve for 2019 and "
               f"2024 with the Gini index. No comparison between hospitals should be read as a quality measure: it "
               f"reflects case mix, coding depth and service portfolio. Definition: {vl}."),
    }[lang]
    note = {
        "es": ("Celda: episodios con F84 documentado; tasa por 100.000 episodios GRD del mismo hospital y año. Los "
               "hospitales se identifican por COD_HOSPITAL y el nombre se abrevia. Panel observado (65, 65, 65, 65, 68 y "
               f"72 hospitales); el panel fijo de 65 son los {C.fixed_panel_gloss('es', 'full')}; "
               "los 7 restantes se incorporan en 2023 o en 2024 y nunca aparecen antes. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_hospital_year.csv y grd_fixed_panel_hospitals.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes with documented F84; rate per 100,000 GRD episodes of the same hospital and year. Hospitals "
               "are identified by COD_HOSPITAL and the name is abbreviated. Observed panel (65, 65, 65, 65, 68 and 72 "
               f"hospitals); the fixed panel of 65 are the {C.fixed_panel_gloss('en', 'full')}; the remaining "
               "7 enter in 2023 or in 2024 and never appear before. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_hospital_year.csv and grd_fixed_panel_hospitals.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF8", "ef8_title", variant, lang), cap,
                  table_title("EF8", "ef8_title", variant, lang), note)


# ===========================================================================
# EF9 · Territorio
# ===========================================================================
BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]


def load_comuna_shapes():
    """Comunas continentales en proyección cónica de igual área para Chile; None si geopandas o el archivo faltan."""
    try:
        import geopandas as gpd
        from shapely.geometry import box
    except ImportError:
        warn("geopandas no está disponible: la lámina EF9 se dibuja sin mapa")
        return None
    path = CFG.PATHS["repo_shapes_comunas"]
    if not Path(path).is_file():
        warn(f"no se encuentra {path}: la lámina EF9 se dibuja sin mapa")
        return None
    shp = gpd.read_file(path)
    shp = shp.loc[shp.cod_comuna > 0, ["cod_comuna", "Comuna", "codregion", "geometry"]].rename(columns={"cod_comuna": "cut_comuna"})
    shp["cut_comuna"] = shp.cut_comuna.astype(int)
    shp["codregion"] = shp.codregion.astype(int)
    shp = shp.to_crs(4326)
    try:
        shp["geometry"] = shp.geometry.make_valid()
    except AttributeError:
        shp["geometry"] = shp.geometry.buffer(0)
    shp["geometry"] = shp.geometry.intersection(box(-76.5, -56.6, -66.0, -17.3))
    shp = shp.loc[~shp.geometry.is_empty].copy()
    shp = shp.to_crs("+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 +datum=WGS84 +units=m +no_defs")
    shp["geometry"] = shp.geometry.simplify(600)
    return shp


def comuna_map(fig, slot_ax, shapes, values: pd.Series, lang, title, cbar_label, cmap="RdYlBu_r", letter_="d"):
    """Tres franjas (norte, centro, sur) con la misma escala métrica y una barra de color común."""
    from matplotlib.colors import TwoSlopeNorm, Normalize
    from matplotlib import cm
    spec = slot_ax.get_subplotspec()
    slot_ax.remove()
    sub = spec.subgridspec(1, 3, wspace=0.02)
    vals = values.reindex(shapes.cut_comuna).to_numpy(dtype=float)
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return []
    vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
    norm = TwoSlopeNorm(vmin=min(vmin, 0.99), vcenter=1.0, vmax=max(vmax, 1.01)) if vmin < 1 < vmax else Normalize(vmin, vmax)
    mapper = cm.ScalarMappable(norm=norm, cmap=cmap)
    span = max((shapes.loc[shapes.codregion.isin(b)].total_bounds[3] -
                shapes.loc[shapes.codregion.isin(b)].total_bounds[1]) for b in BANDS) * 1.04
    axes = []
    for k, band in enumerate(BANDS):
        a = fig.add_subplot(sub[0, k])
        g = shapes.loc[shapes.codregion.isin(band)].copy()
        cols = [mapper.to_rgba(v) if np.isfinite(v) else "#f2f2f2" for v in values.reindex(g.cut_comuna).to_numpy(dtype=float)]
        g.plot(color=cols, edgecolor="#666666", linewidth=0.18, ax=a)
        b = g.total_bounds
        cy, cx = (b[1] + b[3]) / 2, (b[0] + b[2]) / 2
        a.set_ylim(cy - span / 2, cy + span / 2)
        a.set_xlim(cx - span * 0.18, cx + span * 0.18)
        a.set_aspect("equal")
        a.set_axis_off()
        axes.append(a)
    axes[1].set_title(textwrap.fill(title, 34), fontsize=FS_TITLE, fontweight="bold")
    cb = fig.colorbar(mapper, ax=axes, orientation="horizontal", fraction=0.05, pad=0.02, shrink=0.9)
    cb.set_label(cbar_label, fontsize=FS_TICK)
    cb.ax.tick_params(labelsize=FS_TICK)
    letter(axes[0], letter_, dx=-6.0, dy=6.0)
    return axes


def region_population(D, year: int) -> pd.Series:
    p = D.pop_reg
    s = p.loc[(p.level == "region") & (p.year == year) & (p.sex == "TOTAL") & (p.age_group == "TOTAL")]
    return s.set_index("cut_region").population


def ef9(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF9_territory"
    t = D.terr.loc[(D.terr.panel == "observed") & (D.terr.variant == variant) & (D.terr.position == "any")]
    reg = t.loc[(t.level == "region") & t.cut_region.notna()].copy()
    reg["cut_region"] = reg.cut_region.astype(int)
    unmatched = t.loc[(t.level == "region") & t.cut_region.isna()]
    com = t.loc[(t.level == "comuna") & t.cut_comuna.notna()].copy()
    com["cut_comuna"] = com.cut_comuna.astype(int)

    for y in YEARS:
        exp = float(D.year.loc[(D.year.year == y) & (D.year.variant == variant) & (D.year.panel == "observed") &
                               (D.year.activity == "all") & (D.year.position == "any"), "n_episodes_f84"].iloc[0])
        ctl.add(f"EF9_region_sum[{variant}]", y, exp, float(t.loc[(t.level == "region") & (t.year == y), "n_episodes"].sum()),
                "grd_territory nivel región (incluida la fila sin comuna enlazable) frente a grd_year_summary")

    rows = []
    for y in YEARS:
        pop = region_population(D, y)
        for r0 in reg.loc[reg.year == y].itertuples():
            n = float(r0.n_episodes)
            per = float(pop.get(r0.cut_region, np.nan))
            rate, lo, hi = rate_ci(n, per)
            pr, plo, phi = rate_ci(float(r0.n_persons_within_year) if pd.notna(r0.n_persons_within_year) else np.nan, per)
            rows.append(dict(year=y, cut_region=r0.cut_region, region=C.REGION_NAMES.get(r0.cut_region, str(r0.cut_region)),
                             n_episodes=n, n_persons_within_year=float(r0.n_persons_within_year) if pd.notna(r0.n_persons_within_year) else np.nan,
                             population=per, rate_per_100k=rate, rate_lo=lo, rate_hi=hi, persons_rate_per_100k=pr))
    RG = pd.DataFrame(rows)

    fig, ax = new_plate()
    order = [r for r in C.REGION_ORDER if r in set(RG.cut_region)]
    mat = RG.pivot_table(index="cut_region", columns="year", values="rate_per_100k").reindex(order)
    heat(ax[0], mat, lambda v: num(v, 1, lang), cmap="YlGnBu", fontsize=FS_ANN,
         ylabels=[C.REGION_NAMES.get(i, str(i)) for i in mat.index], fig=fig, cbar_label=T("ef9_episodes_rate", lang))
    ax[0].set_xlabel(T("year", lang))
    panel(ax[0], "a", T("ef9_a", lang))

    # (b) tendencia regional
    last = RG.loc[RG.year == YEARS[-1]].nlargest(4, "rate_per_100k").cut_region.tolist()
    for r in order:
        s = RG.loc[RG.cut_region == r].sort_values("year")
        if r in last:
            ax[1].plot(s.year, s.rate_per_100k, marker="o", ms=3.4, lw=1.8,
                       color=OKABE[last.index(r) % len(OKABE)], label=C.REGION_NAMES.get(r, str(r)), zorder=3)
        else:
            ax[1].plot(s.year, s.rate_per_100k, lw=1.0, color="#b8b8b8", zorder=1)
    nat = RG.groupby("year").agg(n=("n_episodes", "sum"), p=("population", "sum"))
    ax[1].plot(nat.index, PER * nat.n / nat.p, lw=2.2, color="#111111", ls="--",
               label={"es": "Total nacional", "en": "National total"}[lang], zorder=4)
    context(ax[1], lang, law_pos=0.45)
    year_axis(ax[1], lang)
    ax[1].set_ylabel(T("ef9_episodes_rate", lang))
    legend_wrapped(ax[1], fontsize=FS_ANN)
    panel(ax[1], "b", T("ef9_b", lang))

    # (c) personas dentro del año frente a episodios, por región (2024)
    # Antes era una nube de puntos con los dieciséis nombres de región escritos junto a su marcador: en una
    # celda de 88 mm los nombres se imprimían de tres en tres unos sobre otros («Tarapacá» sobre
    # «Valparaíso», «Aysén» sobre «La Araucanía»), que es el defecto que el informe señaló en S24 (c).
    # Con una fila por región el nombre vive en el eje —donde ya vive en el panel (a) de esta misma lámina—
    # y los dos valores se leen en la misma línea: el segmento entre ambos ES la multiplicidad de episodios
    # por persona dentro del año. No se pierde ningún dato: los mismos dieciséis pares, más legibles.
    s = RG.loc[RG.year == YEARS[-1]].set_index("cut_region").reindex(order)
    yy = np.arange(len(s))
    ax[2].hlines(yy, s.persons_rate_per_100k, s.rate_per_100k, color="#c0c0c0", lw=1.6, zorder=1)
    ax[2].plot(s.rate_per_100k, yy, "o", ms=4.4, color=COL["f84"], zorder=3, ls="none",
               label=T("episodes", lang))
    ax[2].plot(s.persons_rate_per_100k, yy, "s", ms=3.8, color=OKABE[2], zorder=3, ls="none",
               label=T("ef6_persons", lang))
    ax[2].set_yticks(yy)
    ax[2].set_yticklabels([C.REGION_NAMES.get(i, str(i)) for i in s.index], fontsize=FS_TICK)
    # Banda propia para la leyenda SOBRE la primera región: dentro del área de filas, sus dos símbolos se
    # leen como si fueran dos regiones más (un círculo suelto a la altura de Los Lagos parece un dato).
    ax[2].set_ylim(len(s) - 0.4, -3.0)                 # norte arriba, como en el panel (a)
    ax[2].set_xlim(0, float(np.nanmax(s.rate_per_100k.to_numpy(dtype=float))) * 1.12)
    ax[2].set_xlabel(T("ef9_rate_residents", lang))
    ax[2].grid(axis="y", lw=0.0)
    legend_wrapped(ax[2], fontsize=FS_TICK, loc="upper left", ncol=1, expand=False, width=26,
                   frameon=True, framealpha=0.92, edgecolor="none")
    panel(ax[2], "c", T("ef9_c", lang))

    # (d) mapa comunal de la razón O/E suavizada (acumulado 2019–2024)
    obs = com.groupby("cut_comuna").n_episodes.sum()
    pop_com = (D.pop_com.loc[D.pop_com.year.isin(YEARS)].groupby(["cut_comuna", "year"]).population.sum()
               .groupby("cut_comuna").sum())
    idx = obs.index.union(pop_com.index)
    O = obs.reindex(idx).fillna(0.0)
    E_pop = pop_com.reindex(idx)
    national_rate = O.sum() / E_pop.sum()
    E = E_pop * national_rate
    eb = C.empirical_bayes_ratio(O.to_numpy(), E.to_numpy())
    SIR = pd.DataFrame(dict(cut_comuna=idx, observed=O.to_numpy(), expected=E.to_numpy(),
                            sir=np.where(E.to_numpy() > 0, O.to_numpy() / E.to_numpy(), np.nan),
                            sir_eb=eb.sir_eb.to_numpy(), eb_weight=eb.eb_weight.to_numpy()))
    if D.shapes_comuna is None:
        D.shapes_comuna = load_comuna_shapes()
    if D.shapes_comuna is not None:
        vals = SIR.set_index("cut_comuna").sir_eb
        comuna_map(fig, ax[3], D.shapes_comuna, vals, lang, T("ef9_d", lang), T("ef9_sir", lang))
    else:
        ax[3].axis("off")
        ax[3].text(0.5, 0.5, T("ef9_no_geo", lang), ha="center", va="center", fontsize=FS_TITLE, transform=ax[3].transAxes)
        panel(ax[3], "d", T("ef9_d", lang))

    # (e) episodios sin comuna enlazable
    un = unmatched.set_index("year").n_episodes if len(unmatched) else pd.Series(dtype=float)
    tot = t.loc[t.level == "region"].groupby("year").n_episodes.sum()
    share = 100 * un.reindex(YEARS).fillna(0.0) / tot.reindex(YEARS)
    counts = un.reindex(YEARS).fillna(0.0)
    ax[4].bar(YEARS, counts, width=0.6, color=OKABE[3])
    ax[4].set_ylabel(T("episodes", lang))
    top_e = max(float(counts.max()), 1.0)
    ax[4].set_ylim(0, top_e * 1.35)
    ax4b = ax[4].twinx()
    ax4b.plot(YEARS, share, marker="o", ms=4.0, lw=1.6, color="#1a1a1a")
    ax4b.set_ylabel(T("ef9_unmatched", lang))
    ax4b.grid(False)
    # Los rótulos se escriben DESPUÉS de la línea del eje gemelo y con el colocador medido: con cero
    # episodios sin comuna, el «0» de la barra caía justo sobre el marcador del 0 % de la línea.
    for y, v in zip(YEARS, counts):
        # Se busca sitio primero a la izquierda: la línea del eje gemelo cae casi vertical sobre el centro
        # de la barra de 2019 y el rótulo, centrado encima, quedaba partido por ella.
        C.plate_value_label(ax[4], y, float(v), num(v, 0, lang), fontsize=FS_TICK,
                            prefer=((-1, 1), (-1, 0), (0, 1), (1, 1), (1, 0), (0, -1)))
    year_axis(ax[4], lang)
    long_xlabel(ax[4], {"es": "Año — comuna «DESCONOCIDO» o sin correspondencia en el cuadro de equivalencias auditable; nunca se aplica emparejamiento aproximado",
                        "en": "Year — comuna 'DESCONOCIDO' or without a match in the auditable crosswalk; approximate matching is never applied"}[lang])
    panel(ax[4], "e", T("ef9_e", lang))

    # (f) 2019 frente a 2024 por región
    yb = np.arange(len(order))
    a19 = [float(RG.loc[(RG.cut_region == r) & (RG.year == YEARS[0]), "rate_per_100k"].sum()) for r in order]
    a24 = [float(RG.loc[(RG.cut_region == r) & (RG.year == YEARS[-1]), "rate_per_100k"].sum()) for r in order]
    for i, (a, b) in enumerate(zip(a19, a24)):
        ax[5].plot([a, b], [i, i], color="#bbbbbb", lw=1.6, zorder=1)
    ax[5].scatter(a19, yb, s=26, color=COL["y2019"], zorder=2, label=str(YEARS[0]))
    ax[5].scatter(a24, yb, s=26, color=COL["y2024"], zorder=2, label=str(YEARS[-1]))
    ax[5].set_yticks(yb)
    ax[5].set_yticklabels([C.REGION_NAMES.get(r, str(r)) for r in order], fontsize=FS_TICK)
    ax[5].invert_yaxis()
    ax[5].set_xlabel(T("ef9_episodes_rate", lang))
    legend_wrapped(ax[5], fontsize=FS_TICK)
    panel(ax[5], "f", T("ef9_f", lang))

    # --- tabla acompañante (supresión de celdas con menos de 5 eventos) ---------------------------
    rows = []
    for r in order:
        row = {"__k": C.REGION_NAMES.get(r, str(r))}
        for y in YEARS:
            s = RG.loc[(RG.cut_region == r) & (RG.year == y)]
            if s.empty:
                row[str(y)] = T("not_estimable", lang)
            elif float(s.n_episodes.iloc[0]) < SUPPRESS_MIN:
                row[str(y)] = T("suppressed", lang)
            else:
                row[str(y)] = f"{num(s.n_episodes.iloc[0], 0, lang)}; {val_ci(s.rate_per_100k.iloc[0], s.rate_lo.iloc[0], s.rate_hi.iloc[0], 1, lang)}"
        rows.append(row)
    row = {"__k": {"es": "Sin comuna enlazable", "en": "Without a linkable comuna"}[lang]}
    for y in YEARS:
        v = float(un.get(y, 0.0))
        row[str(y)] = T("suppressed", lang) if 0 < v < SUPPRESS_MIN else num(v, 0, lang)
    rows.append(row)
    row = {"__k": {"es": "Total nacional", "en": "National total"}[lang]}
    for y in YEARS:
        n = float(nat.loc[y, "n"])
        row[str(y)] = f"{num(n, 0, lang)}; {num(PER * n / nat.loc[y, 'p'], 1, lang)}"
    rows.append(row)
    formatted = pd.DataFrame(rows).rename(columns={"__k": T("region", lang)})
    numeric = pd.concat([RG.assign(block="region_rates", variant=variant),
                         SIR.assign(block="comuna_smoothed_ratio", variant=variant,
                                    national_rate_2019_2024=float(national_rate)),
                         pd.DataFrame(dict(year=YEARS, n_unmatched=un.reindex(YEARS).fillna(0.0).to_numpy(),
                                           pct_unmatched=share.to_numpy(), block="unmatched", variant=variant))],
                        ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Episodios con F84 documentado por 100.000 residentes: región de residencia declarada × año. "
               f"(b) Tendencia regional 2019–2024 (gris: cada región; color: las cuatro con mayor tasa en {YEARS[-1]}; "
               f"discontinua negra: total nacional). (c) Una fila por región, ordenadas de norte a sur: episodios "
               f"(círculo) y personas dentro del año (cuadrado), ambas por 100.000 residentes en {YEARS[-1]}; el "
               f"segmento une los dos valores de la región y su longitud es la multiplicidad de episodios por persona "
               f"dentro del año. Las personas nunca se deduplican entre años. (d) Mapa comunal de la razón observada/esperada suavizada por Bayes empírico (Marshall), "
               f"acumulado 2019–2024: esperados = población comunal INE × tasa nacional del período (razón cruda, sin "
               f"estandarizar por edad, porque el GRD no publica edad por comuna); el mapa no muestra recuentos, y las "
               f"comunas con menos de cinco episodios se suprimen en las tablas. (e) Episodios cuya comuna de residencia "
               f"no pudo enlazarse al crosswalk auditable (barras) y su porcentaje del total (línea, eje derecho). "
               f"(f) Tasa regional en {YEARS[0]} frente a {YEARS[-1]}. El numerador cubre solo hospitales públicos con "
               f"GRD, de modo que la tasa por residentes no es una tasa de hospitalización de la población regional; "
               f"combina residencia (denominador INE) con episodios atendidos en la red pública. Definición: {vl}."),
        "en": (f"(a) Episodes with documented F84 per 100,000 residents: reported region of residence × year. "
               f"(b) Regional trend 2019–2024 (grey: each region; colour: the four with the highest rate in {YEARS[-1]}; "
               f"black dashed: national total). (c) One row per region, ordered north to south: episodes (circle) and "
               f"persons within year (square), both per 100,000 residents in {YEARS[-1]}; the segment joins the region's "
               f"two values and its length is the multiplicity of episodes per person within the year. Persons are never "
               f"deduplicated across years. (d) Comuna "
               f"map of the observed/expected ratio smoothed by empirical Bayes (Marshall), pooled 2019–2024: expected = "
               f"INE comuna population × the period's national rate (a crude ratio, not age-standardised, because GRD "
               f"does not publish age by comuna); the map displays no counts, and comunas with fewer than five episodes "
               f"are suppressed in the tables. (e) Episodes whose comuna of residence could not be linked to the "
               f"auditable crosswalk (bars) and their percentage of the total (line, right axis). (f) Regional rate in "
               f"{YEARS[0]} versus {YEARS[-1]}. The numerator covers only public hospitals with GRD, so the rate per "
               f"resident is not a hospitalisation rate of the regional population; it combines residence (INE "
               f"denominator) with episodes attended in the public network. Definition: {vl}."),
    }[lang]
    note = {
        "es": ("Celda: episodios con F84 documentado; tasa por 100.000 residentes (IC 95 % exacto de Poisson). "
               "Denominador: población regional INE del mismo año (base 2017, 30 de junio, residencia). Las celdas con "
               "menos de cinco episodios se suprimen («suprimido (< 5)»); la tabla numérica acompañante conserva los "
               "valores agregados de región y la razón suavizada por comuna, nunca recuentos comunales pequeños en la "
               "versión formateada. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_territory.csv, ine_population_region_national_year_age_sex.csv, "
                           "ine_population_comuna_year_age_sex.csv y comuna_crosswalk.csv; " + SOURCE_GRD[lang], lang)),
        "en": ("Cell: episodes with documented F84; rate per 100,000 residents (exact Poisson 95% CI). Denominator: INE "
               "regional population of the same year (2017 base, 30 June, residence). Cells with fewer than five episodes "
               "are suppressed ('suppressed (< 5)'); the numeric companion keeps the regional aggregates and the smoothed "
               "comuna ratio, never small comuna counts in the formatted version. " + NOTE_CORE[lang] + " " +
               source_line("outputs/tidy/grd_territory.csv, ine_population_region_national_year_age_sex.csv, "
                           "ine_population_comuna_year_age_sex.csv and comuna_crosswalk.csv; " + SOURCE_GRD[lang], lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF9", "ef9_title", variant, lang), cap,
                  table_title("EF9", "ef9_title", variant, lang), note)


# ===========================================================================
# EF10 · Detalle DEIS
# ===========================================================================
DEIS_SEX = {"HOMBRE": "male", "MUJER": "female"}


def ef10(D, variant, lang, fdir, tdir, ctl) -> dict:
    name = "EF10_deis_detail"
    dy = D.deis_year.loc[(D.deis_year.source_layout == "canonical") & (D.deis_year.variant == variant)].sort_values("year")
    de = D.deis_estab.loc[(D.deis_estab.source_layout == "canonical") & (D.deis_estab.variant == variant) &
                          (D.deis_estab.dimension == "pertenencia_snss")]
    das = D.deis_age_sex.loc[(D.deis_age_sex.source_layout == "canonical") & (D.deis_age_sex.variant == variant)]
    dvg = D.deis_grd.loc[D.deis_grd.variant == variant].sort_values("year")
    years_deis = sorted(dy.year.unique())

    for y in years_deis:
        ctl.add(f"EF10_deis_estab_sum[{variant}]", y, float(dy.loc[dy.year == y, "f84_diag1"].iloc[0]),
                float(de.loc[de.year == y, "f84_diag1"].sum()),
                "deis_establishment_year (SNSS + no SNSS + suprimido) frente a deis_year_summary")
    for y in [yy for yy in years_deis if yy in CFG.CONTROLS["grd_f84_principal"]]:
        ctl.add(f"EF10_grd_principal_control[{variant}]", y, CFG.CONTROLS["grd_f84_principal"][y] if variant == "con_rett" else "",
                float(dvg.loc[dvg.year == y, "grd_f84_principal"].iloc[0]) if (dvg.year == y).any() else np.nan,
                "F84 principal del GRD en deis_vs_grd_year frente a config.CONTROLS (solo la variante con Rett tiene valor esperado)",
                status=None if variant == "con_rett" else "info")

    fig, ax = new_plate()
    # (a) egresos con F84 principal y tasa
    ax[0].bar(dy.year, dy.f84_diag1, width=0.6, color=COL["deis"], label={"es": "Egresos con F84 principal",
                                                                          "en": "Discharges with principal F84"}[lang])
    ax[0].set_ylabel({"es": "Egresos DEIS con F84 principal", "en": "DEIS discharges with principal F84"}[lang])
    ax0b = ax[0].twinx()
    ax0b.errorbar(dy.year, dy.rate_per_100k_discharges,
                  yerr=[dy.rate_per_100k_discharges - dy.rate_lo95, dy.rate_hi95 - dy.rate_per_100k_discharges],
                  marker="o", ms=4.2, lw=1.7, capsize=2.4, color="#1a1a1a", label=T("rate_100k_disch", lang))
    ax0b.set_ylabel(T("rate_100k_disch", lang))
    ax0b.grid(False)
    context(ax[0], lang, law=False, pandemic_pos=0.55)   # franja libre entre las barras y la leyenda
    year_axis(ax[0], lang, years_deis)
    h1, l1 = ax[0].get_legend_handles_labels()
    h2, l2 = ax0b.get_legend_handles_labels()
    legend_wrapped(ax[0], h1 + h2, l1 + l2, fontsize=FS_TICK, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    panel(ax[0], "a", T("ef10_a", lang))

    # (b) SNSS frente a no SNSS
    for cat, colour, lab in (("SNSS", COL["snss"], T("ef10_snss", lang)),
                             ("NO_SNSS", COL["no_snss"], T("ef10_no_snss", lang)),
                             ("SUPRIMIDO", "#999999", T("ef10_masked", lang))):
        s = de.loc[de.category == cat].sort_values("year")
        if s.empty:
            continue
        ax[1].errorbar(s.year, s.rate_per_100k_discharges,
                       yerr=[s.rate_per_100k_discharges - s.rate_lo95, s.rate_hi95 - s.rate_per_100k_discharges],
                       marker="o", ms=4.0, lw=1.6, capsize=2.2, color=colour, label=lab)
    context(ax[1], lang, law=False, pandemic_pos=0.03)
    year_axis(ax[1], lang, years_deis)
    ax[1].set_ylabel(T("rate_100k_disch", lang))
    legend_wrapped(ax[1], fontsize=FS_TICK, framealpha=0.9, edgecolor="none")
    panel(ax[1], "b", T("ef10_b", lang))

    # (c) por sexo
    sx = das.loc[das.level == "sex"]
    for cat, colour, lab in (("HOMBRE", COL["male"], T("male", lang)), ("MUJER", COL["female"], T("female", lang)),
                             ("SUPRIMIDO", "#999999", T("ef10_masked", lang))):
        s = sx.loc[sx.sex == cat].sort_values("year")
        if s.empty:
            continue
        ax[2].errorbar(s.year, s.rate_per_100k_discharges,
                       yerr=[s.rate_per_100k_discharges - s.rate_lo95, s.rate_hi95 - s.rate_per_100k_discharges],
                       marker="o", ms=4.0, lw=1.6, capsize=2.2, color=colour, label=lab)
    context(ax[2], lang, law=False, pandemic_pos=0.03)
    year_axis(ax[2], lang, years_deis)
    ax[2].set_ylabel(T("rate_100k_disch", lang))
    legend_wrapped(ax[2], fontsize=FS_TICK)
    panel(ax[2], "c", T("ef10_c", lang))

    # (d) por banda de edad, primer y último año
    ab = das.loc[(das.level == "age_band_10") & (das.age_band_10 != "SUPRIMIDO")]
    bands = [b for b in ["<1", "1-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
             if b in set(ab.age_band_10)]
    xs = np.arange(len(bands))
    w = 0.38
    for i, (y, colour) in enumerate(((years_deis[0], COL["y2019"]), (years_deis[-1], COL["y2024"]))):
        s = ab.loc[ab.year == y].set_index("age_band_10")
        vals = [float(s.rate_per_100k_discharges.get(b, np.nan)) for b in bands]
        ax[3].bar(xs + (i - 0.5) * w, vals, width=w, color=colour, label=str(y))
    ax[3].set_xticks(xs)
    ax[3].set_xticklabels(bands, rotation=45, fontsize=FS_TICK)
    ax[3].set_xlabel(T("ef10_age_band", lang))
    ax[3].set_ylabel(T("rate_100k_disch", lang))
    legend_wrapped(ax[3], fontsize=FS_TICK)
    panel(ax[3], "d", T("ef10_d", lang))

    # (e) DEIS frente a GRD (única serie homologable)
    ax[4].plot(dvg.year, dvg.deis_rate_f84_principal_per_100k_discharges, marker="o", ms=4.2, lw=1.7,
               color=COL["deis"], label=T("ef10_deis", lang))
    ax[4].plot(dvg.year, dvg.grd_rate_f84_principal_per_100k_episodes, marker="s", ms=4.0, lw=1.6,
               color=COL["f84"], label=T("ef10_grd", lang))
    ax[4].plot(dvg.year, dvg.grd_rate_f84_principal_hospitalisation_per_100k_episodes, marker="^", ms=3.8, lw=1.4,
               ls="--", color=COL["hosp"], label={"es": "GRD: F84 principal, solo hospitalización",
                                                  "en": "GRD: principal F84, hospitalisation only"}[lang])
    context(ax[4], lang, law=False, pandemic_pos=0.55)   # franja libre sobre las series y bajo la leyenda
    year_axis(ax[4], lang, years_deis)
    ax[4].set_ylabel({"es": "Por 100.000 egresos o episodios de la propia fuente",
                      "en": "Per 100,000 discharges or episodes of the same source"}[lang])
    legend_wrapped(ax[4], fontsize=FS_ANN, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    long_xlabel(ax[4], {"es": "Año — fuentes no enlazadas por persona ni episodio; no se calculan cocientes entre ellas",
                        "en": "Year — sources are not linked by person or episode; no ratios are computed between them"}[lang])
    panel(ax[4], "e", T("ef10_e", lang))

    # (f) subcódigos F84 en DIAG1 y celdas enmascaradas
    sub = D.deis_sub.copy()
    if variant == "sin_rett":
        sub = sub.loc[sub.in_variant_sin_rett.astype(str) == "True"]
    codes = sorted(sub.f84_diag1_code.unique())
    bottom = np.zeros(len(years_deis))
    totals = sub.groupby("year").discharges_f84_diag1.sum()
    for i, code in enumerate(codes):
        s = sub.loc[sub.f84_diag1_code == code].set_index("year").discharges_f84_diag1
        vals = np.array([100 * float(s.get(y, 0.0)) / float(totals.get(y, np.nan)) for y in years_deis])
        ax[5].bar(years_deis, vals, bottom=bottom, width=0.62, color=OKABE[i % len(OKABE)], label=code,
                  edgecolor="white", linewidth=0.4)
        bottom += np.nan_to_num(vals)
    year_axis(ax[5], lang, years_deis)
    ax[5].set_ylabel(T("ef10_subcode", lang))
    ax[5].set_ylim(0, 128)
    legend_wrapped(ax[5], fontsize=FS_ANN, ncol=5, loc="upper center", frameon=True, framealpha=0.9, edgecolor="none")
    masked = "; ".join(f"{y}: {num(dy.loc[dy.year == y, 'f84_any_suppressed'].iloc[0], 0, lang)}" for y in years_deis)
    long_xlabel(ax[5], {"es": f"Año — celdas F84 enmascaradas por DEIS: {masked}",
                        "en": f"Year — F84 cells masked by DEIS: {masked}"}[lang])
    panel(ax[5], "f", T("ef10_f", lang))

    # --- tabla acompañante ------------------------------------------------------------------------
    rows = []
    r = {"__k": {"es": "DEIS: F84 principal (todos los establecimientos)", "en": "DEIS: principal F84 (all establishments)"}[lang]}
    for y in years_deis:
        s = dy.loc[dy.year == y]
        r[str(y)] = f"{num(s.f84_diag1.iloc[0], 0, lang)}; {val_ci(s.rate_per_100k_discharges.iloc[0], s.rate_lo95.iloc[0], s.rate_hi95.iloc[0], 1, lang)}"
    rows.append(r)
    for cat, lab in (("SNSS", T("ef10_snss", lang)), ("NO_SNSS", T("ef10_no_snss", lang)), ("SUPRIMIDO", T("ef10_masked", lang))):
        r = {"__k": f"DEIS — {lab}"}
        for y in years_deis:
            s = de.loc[(de.category == cat) & (de.year == y)]
            r[str(y)] = (f"{num(s.f84_diag1.iloc[0], 0, lang)}; {val_ci(s.rate_per_100k_discharges.iloc[0], s.rate_lo95.iloc[0], s.rate_hi95.iloc[0], 1, lang)}"
                         if len(s) else T("not_estimable", lang))
        rows.append(r)
    for cat, lab in (("HOMBRE", T("male", lang)), ("MUJER", T("female", lang))):
        r = {"__k": f"DEIS — {lab}"}
        for y in years_deis:
            s = sx.loc[(sx.sex == cat) & (sx.year == y)]
            r[str(y)] = (f"{num(s.f84_diag1.iloc[0], 0, lang)}; {val_ci(s.rate_per_100k_discharges.iloc[0], s.rate_lo95.iloc[0], s.rate_hi95.iloc[0], 1, lang)}"
                         if len(s) else T("not_estimable", lang))
        rows.append(r)
    r = {"__k": T("ef10_grd", lang)}
    for y in years_deis:
        s = dvg.loc[dvg.year == y]
        r[str(y)] = (f"{num(s.grd_f84_principal.iloc[0], 0, lang)}; {num(s.grd_rate_f84_principal_per_100k_episodes.iloc[0], 1, lang)}"
                     if len(s) else T("not_estimable", lang))
    rows.append(r)
    r = {"__k": {"es": "Celdas F84 enmascaradas (DEIS)", "en": "F84 cells masked (DEIS)"}[lang]}
    for y in years_deis:
        r[str(y)] = num(dy.loc[dy.year == y, "f84_any_suppressed"].iloc[0], 0, lang)
    rows.append(r)
    formatted = pd.DataFrame(rows).rename(columns={"__k": {"es": "Serie", "en": "Series"}[lang]})
    numeric = pd.concat([dy.assign(block="deis_year"), de.assign(block="deis_establishment"),
                         das.assign(block="deis_age_sex"), sub.assign(block="deis_subcodes"),
                         dvg.assign(block="deis_vs_grd")], ignore_index=True)

    vl = variant_label(variant, lang)
    cap = {
        "es": (f"(a) Egresos hospitalarios DEIS con F84 como diagnóstico principal (DIAG1) por año (barras) y tasa por "
               f"100.000 egresos con IC 95 % exactos de Poisson (línea, eje derecho); DEIS publica solo el diagnóstico "
               f"principal, por lo que no existe en esta fuente un equivalente de «F84 en cualquier posición». (b) Tasa "
               f"según pertenencia del establecimiento al Sistema Nacional de Servicios de Salud (SNSS) frente a los "
               f"demás (clínicas privadas, FF.AA. y de Orden, mutuales, administración delegada) y celdas enmascaradas "
               f"por DEIS, que se conservan como categoría propia y nunca se reparten. (c) Tasa por sexo registrado, con "
               f"la categoría enmascarada aparte. (d) Tasa por banda de edad decenal en {years_deis[0]} y "
               f"{years_deis[-1]}. (e) Única comparación homologable entre fuentes: F84 principal por 100.000 egresos "
               f"DEIS y por 100.000 episodios GRD (y solo hospitalización en el GRD). Las fuentes no están enlazadas por "
               f"persona ni por episodio, cubren universos distintos —DEIS todos los establecimientos, GRD los "
               f"hospitales públicos con GRD— y no se calcula ningún cociente entre ellas. (f) Composición de subcódigos "
               f"F84 en DIAG1 por año y número de celdas F84 enmascaradas por DEIS. Definición: {vl}. Reconocimiento "
               f"administrativo, no prevalencia ni incidencia."),
        "en": (f"(a) DEIS hospital discharges with F84 as principal diagnosis (DIAG1) by year (bars) and rate per 100,000 "
               f"discharges with exact Poisson 95% CIs (line, right axis); DEIS publishes only the principal diagnosis, "
               f"so this source has no equivalent of 'F84 in any position'. (b) Rate by establishment membership of the "
               f"National Health Services System (SNSS) versus the rest (private clinics, armed forces and police, mutual "
               f"insurers, delegated administration) and cells masked by DEIS, which are kept as a category of their own "
               f"and never redistributed. (c) Rate by recorded sex, with the masked category shown separately. (d) Rate by "
               f"ten-year age band in {years_deis[0]} and {years_deis[-1]}. (e) The only homologous comparison between "
               f"sources: principal F84 per 100,000 DEIS discharges and per 100,000 GRD episodes (and hospitalisation "
               f"only in GRD). The sources are not linked by person or episode, cover different universes —DEIS all "
               f"establishments, GRD the public hospitals with GRD— and no ratio between them is computed. "
               f"(f) Composition of F84 subcodes in DIAG1 by year and number of F84 cells masked by DEIS. Definition: "
               f"{vl}. Administrative recognition, not prevalence or incidence."),
    }[lang]
    note = {
        "es": ("Celda: egresos con F84 en DIAG1; tasa por 100.000 egresos del mismo estrato (IC 95 % exacto de Poisson). "
               "Unidad: egreso hospitalario DEIS (todos los establecimientos del país; DIAG1 principal y DIAG2 causa "
               "externa, sin diagnósticos secundarios). Cobertura: archivos anuales DEIS 2019–2024, disposición "
               "canónica; la disposición alternativa de 2021 con edad detallada se conserva en la tabla numérica. Era "
               "de definición: familia F84 de la CIE-10 en DIAG1, sin cambios en 2019–2024; DEIS no publica "
               "diagnósticos secundarios, por lo que no existe una serie de «cualquier posición». N reportante: el "
               "total anual de egresos del archivo (denominador de cada tasa) figura en la tabla numérica. Las celdas "
               "enmascaradas por DEIS se informan aparte y no se imputan. Estas cifras no son comparables con el GRD "
               "salvo en F84 principal, y las fuentes no están enlazadas por persona ni por episodio. " +
               source_line("outputs/tidy/deis_year_summary.csv, deis_establishment_year.csv, deis_age_sex_year.csv, "
                           "deis_f84_subcode_year.csv y deis_vs_grd_year.csv (DEIS, Egresos hospitalarios)", lang)),
        "en": ("Cell: discharges with F84 in DIAG1; rate per 100,000 discharges of the same stratum (exact Poisson 95% "
               "CI). Unit: DEIS hospital discharge (all establishments in the country; DIAG1 principal and DIAG2 external "
               "cause, no secondary diagnoses). Coverage: annual DEIS files 2019–2024, canonical layout; the alternative "
               "2021 layout with detailed age is kept in the numeric companion. Definition era: ICD-10 F84 family in "
               "DIAG1, unchanged in 2019–2024; DEIS publishes no secondary diagnoses, so there is no 'any position' "
               "series. Reporting N: the annual total of discharges in the file (the denominator of every rate) is in "
               "the numeric companion. Cells masked by DEIS are reported separately and never imputed. These figures are "
               "not comparable with GRD except for principal F84, and the sources are not linked by person or episode. " +
               source_line("outputs/tidy/deis_year_summary.csv, deis_establishment_year.csv, deis_age_sex_year.csv, "
                           "deis_f84_subcode_year.csv and deis_vs_grd_year.csv (DEIS, hospital discharges)", lang)),
    }[lang]
    return finish(fig, name, fdir, tdir, formatted, numeric, lang,
                  plate_title("EF10", "ef10_title", variant, lang), cap,
                  table_title("EF10", "ef10_title", variant, lang), note)


# ===========================================================================
# main
# ===========================================================================
PLATES = {"EF1": ef1, "EF2": ef2, "EF3": ef3, "EF4": ef4, "EF5": ef5,
          "EF6": ef6, "EF7": ef7, "EF8": ef8, "EF9": ef9, "EF10": ef10}


def global_controls(D, ctl: Controls) -> None:
    """Reproducción de los controles ya verificados del estudio con las mismas tablas que alimentan estas láminas."""
    ys = D.year
    for key, panel_name in (("grd_f84_any", "observed"), ("grd_f84_any_panel65", "fixed65")):
        for y, expected in CFG.CONTROLS[key].items():
            obs = ys.loc[(ys.year == y) & (ys.variant == "con_rett") & (ys.panel == panel_name) & (ys.activity == "all") &
                         (ys.position == "any"), "n_episodes_f84"]
            ctl.add(f"control_{key}", y, expected, float(obs.iloc[0]) if len(obs) else np.nan,
                    "config.CONTROLS frente a grd_year_summary (variante con Rett)")
    for y, expected in CFG.CONTROLS["grd_f84_principal"].items():
        obs = ys.loc[(ys.year == y) & (ys.variant == "con_rett") & (ys.panel == "observed") & (ys.activity == "all") &
                     (ys.position == "principal"), "n_episodes_f84"]
        ctl.add("control_grd_f84_principal", y, expected, float(obs.iloc[0]) if len(obs) else np.nan,
                "config.CONTROLS frente a grd_year_summary")
    for y, expected in CFG.CONTROLS["grd_f84_any_strict_hospitalisation"].items():
        # decision_log (2026-09-04): el control de hospitalización estricta de 2023–2024 es una cantidad del panel fijo de 65;
        # se compara con ese panel y se informa también el panel observado, sin editar config.py.
        for panel_name in ("fixed65", "observed"):
            obs = ys.loc[(ys.year == y) & (ys.variant == "con_rett") & (ys.panel == panel_name) &
                         (ys.activity == "hospitalisation") & (ys.position == "any"), "n_episodes_f84"]
            value = float(obs.iloc[0]) if len(obs) else np.nan
            if panel_name == "fixed65":
                ctl.add("control_grd_hospitalisation_fixed65", y, expected, value,
                        "config.CONTROLS frente a grd_year_summary (panel fijo de 65; el control del protocolo es una cantidad de panel fijo, decision_log 2026-09-04)")
            else:
                ctl.info("control_grd_hospitalisation_observed", y, value,
                         "panel observado (65–72 hospitales); difiere del control del protocolo en 2023–2024 por diseño, no por error")
    for y, expected in CFG.CONTROLS["a05_autism_entries"].items():
        obs = D.a05_month.loc[D.a05_month.year == y, "entries"].sum()
        ctl.add("control_a05_autism_entries", y, expected, float(obs),
                "config.CONTROLS frente a la suma mensual de rem_pathway_tidy (código 05990022, era 2021–2025)")
    ctl.info("suppression_rule", "territorial_tables", f"< {SUPPRESS_MIN}",
             "las celdas territoriales con menos de cinco episodios se muestran como «suprimido» en las tablas formateadas")


def main() -> int:
    ap = argparse.ArgumentParser(description="Láminas adicionales del núcleo hospitalario (serie E) y sus tablas.")
    ap.add_argument("--variants", nargs="+", default=VARIANTS, choices=VARIANTS)
    ap.add_argument("--langs", nargs="+", default=LANGS, choices=LANGS)
    ap.add_argument("--only", nargs="+", default=list(PLATES), choices=list(PLATES))
    args = ap.parse_args()

    t0 = time.time()
    log("cargando tablas tidy")
    D = load()
    log(f"tablas cargadas en {time.time() - t0:.1f} s")
    ctl = Controls()
    global_controls(D, ctl)

    outputs: list[str] = []
    timings: dict[str, float] = {}
    for variant in args.variants:
        for lang in args.langs:
            fdir, tdir = out_dirs(variant, lang)
            captions: dict = {}
            titles: dict = {}
            for key in args.only:
                t1 = time.time()
                res = PLATES[key](D, variant, lang, fdir, tdir, ctl)
                outputs.append(res["figure"])
                outputs.extend(res["tables"])
                captions.update(res["captions"])
                titles.update(res["titles"])
                timings[f"{variant}/{lang}/{key}"] = round(time.time() - t1, 1)
                log(f"{variant}/{lang} · {key} en {time.time() - t1:.1f} s")
            merge_json(fdir / "captions.json", C.strip_caption_paths(captions))
            merge_json(tdir / "titles.json", titles)
            outputs.extend([str(fdir / "captions.json"), str(tdir / "titles.json")])

    controls = ctl.frame().drop_duplicates()
    cpath = CFG.OUT / "controls" / f"{MODULE}_controls.csv"
    C.atomic_write_csv(controls, cpath)
    runtime = time.time() - t0
    runlog = dict(module=MODULE, script=SCRIPT, timestamp=datetime.now(timezone.utc).isoformat(),
                  runtime_seconds=round(runtime, 1), variants=args.variants, languages=args.langs, plates=args.only,
                  inputs=INPUT_TABLES, outputs=sorted(set(outputs)), timings_seconds=timings,
                  n_controls=int(len(controls)), n_controls_differs=int((controls.status == "differs").sum()),
                  warnings=sorted(set(WARNINGS)),
                  versions=dict(pandas=pd.__version__, numpy=np.__version__, python=sys.version.split()[0]))
    C.atomic_write_json(runlog, CFG.OUT / "controls" / f"{MODULE}_runlog.json")
    log(f"listo en {runtime:.1f} s; {len(set(outputs))} salidas; controles: {len(controls)} "
        f"({int((controls.status == 'differs').sum())} con diferencia); avisos: {len(set(WARNINGS))}")
    for w in sorted(set(WARNINGS)):
        log(f"aviso: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
