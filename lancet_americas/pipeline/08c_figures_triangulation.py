# -*- coding: utf-8 -*-
"""08c_figures_triangulation.py — lámina principal F4 (triangulación y benchmarks) y suplementarias S9–S12, S14 y S15.

Entradas (outputs/tidy/ y outputs/controls/): education_summary_year, pie_series, junaeb_tea_year_level, survey_estimates,
models_convergence_index, grd_year_summary, grd_age_sex_year, deis_vs_grd_year, deis_establishment_year, deis_age_who_year,
deis_age_sex_year, rem_pathway_annual, rem_establishment_year, ine_population_*, coverage_layers_year, fonasa/aps/isapre
por comuna y nacionales, comuna_crosswalk, y los *_controls.csv de fase 1. Para S9 (GRD por región de residencia) el módulo
lee los GRD anuales (comuna de residencia + 35 posiciones diagnósticas) y guarda la tabla tidy
`grd_residence_comuna_year.csv` (se reutiliza si existe; `--refresh-grd` fuerza la relectura).

Salidas por variante (con_rett, sin_rett) e idioma (es, en):
  outputs/<variante>/<idioma>/figures/fig4_triangulation.png, figS9_regional_maps.png, figS10_denominators.png,
  figS11_coverage_age_sex.png, figS12_junaeb_sex_level.png, figS14_deis_sex_age.png, figS15_controls.png (+ captions.json)
  outputs/<variante>/<idioma>/tables/F4_triangulation_series.csv, S9_regional_rates.csv, S10_denominator_sensitivity.csv,
  S11_coverage_age_sex.csv, S12_junaeb_sex_level.csv, S14_deis_sex_age.csv, S15_controls_scatter.csv (+ *_numeric.csv, titles.json)
  outputs/controls/08c_figures_triangulation_controls.csv y _runlog.json

Reglas: conteos = reconocimiento administrativo (nunca prevalencia/incidencia); GRD = episodios con F84 documentado (principal
aparte); las eras REM no se unen; toda lámina REM muestra establecimientos reportantes; stocks y flujos no comparten eje;
lugar de atención (REM) y residencia (INE, GRD) no se mezclan sin nota; 2020–2021 sombreados; Ley 21.545 solo como contexto.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
# El CUERPO del título de F4_triangulation_series nombra una lámina del artículo; el número se resuelve en el
# registro compartido (prose_en.MAIN_FIGURES) y nunca se escribe literal.
from prose_en import main_figure_label  # noqa: E402

MODULE = "08c_figures_triangulation"
# Módulos cuyos controles reproducen valores preespecificados del protocolo (S15); los módulos de láminas/tablas de fase 2
# producen comprobaciones de consistencia propias y no se mezclan aquí.
REPRODUCTION_MODULES = ["00_provenance", "01_grd_core", "01b_deis_egresos", "02_rem_pathway", "03_denominators", "04_surveys", "05_education", "06_models", "07_controls"]
SCRIPT = "lancet_americas/pipeline/08c_figures_triangulation.py"
VARIANTS = list(CFG.VARIANTS)
LANGS = CFG.LANGUAGES
CONTROLS_DIR = CFG.OUT / "controls"
DISRUPTION = tuple(CFG.PANDEMIC_YEARS)
LAW_YEAR = CFG.LAW_YEAR
OK = C.OKABE
REGION_ORDER = list(C.REGION_ORDER)
REGION_NAMES = dict(C.REGION_NAMES)
#: Nombre CORTO de la región para escribirlo dentro de su polígono: la franja del mapa mide 26 mm de ancho
#: y «Arica y Parinacota» o «Metropolitana» se cortaban contra el borde del eje. El nombre completo está en
#: el pie de la figura y en la tabla regional; la lámina abrevia, no oculta.
REGION_NAMES_SHORT = {k: C.PLATE_LABEL_GLOSSARY.get(v, v) for k, v in REGION_NAMES.items()}
AGE_GROUPS = list(C.AGE_GROUPS)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

T0 = time.perf_counter()
TIMINGS: dict[str, float] = {}


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Rótulos bilingües (toda cadena visible en láminas y tablas)
# ---------------------------------------------------------------------------
LBL = {
    "figure": {"es": "Figura", "en": "Figure"}, "table": {"es": "Tabla", "en": "Table"},
    "var_con_rett": {"es": "F84 completo (con Rett)", "en": "Full F84 (with Rett)"},
    "var_sin_rett": {"es": "F84 sin Rett", "en": "F84 without Rett"},
    "year": {"es": "Año", "en": "Year"},
    "pandemic": {"es": "Disrupción del\nreporte 2020–21", "en": "Reporting\ndisruption 2020–21"},
    "law": {"es": "Ley 21.545\n(contexto)", "en": "Law 21.545\n(context)"},
    "not_estimable": {"es": "no estimable", "en": "not estimable"},
    "students": {"es": "Estudiantes (stock escolar anual)", "en": "Students (annual school stock)"},
    "pie_strict": {"es": "PIE TEA estricto (Apuntes 60)", "en": "PIE strict ASD (Apuntes 60)"},
    "pie_asperger": {"es": "PIE TEA-Asperger (Apuntes 60)", "en": "PIE ASD-Asperger (Apuntes 60)"},
    "pie_harm": {"es": "PIE armonizado TEA + Asperger", "en": "Harmonised PIE ASD + Asperger"},
    "pie_harm_sinaces": {"es": "PIE armonizado según SINACES", "en": "Harmonised PIE as printed by SINACES"},
    "pie_special": {"es": "Escuelas especiales, autismo (SINACES)", "en": "Special schools, autism (SINACES)"},
    "pie_source_change": {"es": "fuente: SINACES\n(2024–2025)", "en": "source: SINACES\n(2024–2025)"},
    "pie_note_2022": {"es": "2022: SINACES 42.945 frente a\n42.940 (Apuntes 60): 5 estudiantes", "en": "2022: SINACES 42,945 versus\n42,940 (Apuntes 60): 5 students"},
    "f4a_title": {"es": "PIE: estudiantes autistas", "en": "PIE: autistic students"},
    "f4b_title": {"es": "JUNAEB: TEA reportado (%)", "en": "JUNAEB: reported ASD (%)"},
    "f4b_axis": {"es": "% de estudiantes con TEA reportado (IC 95 %)", "en": "% of students with reported ASD (95% CI)"},
    "jun_parvularia": {"es": "Parvularia (NT1–NT2)", "en": "Pre-school (NT1–NT2)"},
    "jun_basico1": {"es": "1º básico", "en": "Grade 1 (1º básico)"},
    "jun_basico5": {"es": "5º básico", "en": "Grade 5 (5º básico)"},
    "jun_medio1": {"es": "1º medio", "en": "Grade 9 (1º medio)"},
    "jun_weighted": {"es": "ponderado (EXP), IC 95 %", "en": "weighted (EXP), 95% CI"},
    "jun_unweighted": {"es": "2023: no ponderado (IC de Wilson)", "en": "2023: unweighted (Wilson CI)"},
    "jun_ne": {"es": "no estimable (ver pie)", "en": "not estimable (see caption)"},
    "jun_strip": {"es": "no estimable", "en": "not estimable"},
    "f4c_title": {"es": "Encuestas: % ponderado", "en": "Surveys: weighted %"},
    "svy_cases_note": {"es": "casos / n del dominio", "en": "cases / domain n"},
    "svy_cases_row": {"es": "rótulo de fila: casos / n no ponderado del dominio",
                      "en": "row label: cases / unweighted domain n"},
    "f4c_axis": {"es": "% ponderado (IC 95 %, escala log)", "en": "Weighted % (95% CI, log scale)"},
    "svy_endide_adults": {"es": "ENDIDE 2022 · adultos 18+", "en": "ENDIDE 2022 · adults 18+"},
    "svy_endide_children": {"es": "ENDIDE 2022 · NNA 2–17 reportado", "en": "ENDIDE 2022 · 2–17 reported"},
    "svy_endide_confirmed": {"es": "ENDIDE 2022 · NNA 2–17 confirmado", "en": "ENDIDE 2022 · 2–17 confirmed"},
    "svy_encavi": {"es": "ENCAVI 2023–24 · personas 15+", "en": "ENCAVI 2023–24 · persons 15+"},
    "total": {"es": "Total", "en": "Total"}, "Hombre": {"es": "Hombres", "en": "Males"}, "Mujer": {"es": "Mujeres", "en": "Females"},
    "HOMBRE": {"es": "Hombres", "en": "Males"}, "MUJER": {"es": "Mujeres", "en": "Females"}, "TOTAL": {"es": "Ambos sexos", "en": "Both sexes"},
    "imprecise": {"es": "impreciso (< 30 casos o EE relativo > 30 %): en gris", "en": "imprecise (< 30 cases or RSE > 30%): greyed"},
    "cases": {"es": "casos", "en": "cases"},
    "f4d_title": {"es": "Índices (2021 = 100)", "en": "Indices (2021 = 100)"},
    "f4d_axis": {"es": "Índice (primer año común 2021 = 100; escala log)", "en": "Index (first common year 2021 = 100; log scale)"},
    "idx_grd": {"es": "GRD: F84 cualquier posición (tasa)", "en": "GRD: F84 any position (rate)"},
    "idx_deis": {"es": "DEIS: F84 principal (tasa)", "en": "DEIS: principal F84 (rate)"},
    "idx_a05": {"es": "REM A05: ingresos, flujo (n {n})", "en": "REM A05: entries, flow (n {n})"},
    "idx_p2": {"es": "REM P2: dic., stock (n {n})", "en": "REM P2: Dec., stock (n {n})"},
    "idx_pie": {"es": "PIE armonizado (stock escolar)", "en": "Harmonised PIE (school stock)"},
    "idx_note": {"es": "unidad, denominador y cobertura difieren;\nlos niveles no son comparables; 2019–2020\npunteados = antes del primer año común", "en": "units, denominators and coverage differ;\nlevels are not comparable; dotted 2019–2020\n= before the first common year"},
    "f4e_title": {"es": "Por 100.000 habitantes", "en": "Per 100,000 population"},
    "f4e_axis_full": {"es": "por 100.000 hab. (INE 2017); un eje por franja", "en": "per 100,000 pop. (INE 2017); one axis per strip"},
    "f4e_axis": {"es": "por 100.000 hab.", "en": "per 100,000 pop."},
    "e_grd_ep": {"es": "GRD episodios F84\n(flujo)", "en": "GRD F84 episodes\n(flow)"},
    "e_grd_pe": {"es": "GRD personas/año F84\n(flujo)", "en": "GRD persons/year F84\n(flow)"},
    "e_a05": {"es": "A05 ingresos autismo\n(flujo)", "en": "A05 autism entries\n(flow)"},
    "e_p2": {"es": "P2 TEA diciembre\n(stock)", "en": "P2 ASD December\n(stock)"},
    "e_pie": {"es": "PIE armonizado\n(stock escolar)", "en": "Harmonised PIE\n(school stock)"},
    "e_legend_flow": {"es": "flujo (eventos del año)", "en": "flow (events in the year)"},
    "e_xlabel_rem": {"es": "año / n establecimientos reportantes", "en": "year / n reporting establishments"},
    "e_legend_stock": {"es": "stock (personas en una fecha)", "en": "stock (persons at a date)"},
    "e_note": {"es": "Denominador: población residente total INE (base 2017, 30 de junio), todas las edades (residencia).\nNumeradores: GRD y REM = lugar de atención (red pública); PIE = matrícula nacional.\nCada panel tiene su propio eje; no comparar alturas entre paneles. n = establecimientos reportantes REM.", "en": "Denominator: total INE resident population (base 2017, 30 June), all ages (residence).\nNumerators: GRD and REM = place of care (public network); PIE = national enrolment.\nEach panel has its own axis; do not compare heights across panels. n = REM reporting establishments."},
    "f4f_title": {"es": "F84 principal: DEIS y GRD", "en": "Principal F84: DEIS and GRD"},
    "f4f_axis": {"es": "F84 principal por 100.000\negresos / episodios (IC 95 %)", "en": "Principal F84 per 100,000\ndischarges / episodes (95% CI)"},
    "deis_all": {"es": "DEIS: todos los establecimientos", "en": "DEIS: all establishments"},
    "deis_snss": {"es": "DEIS: subconjunto SNSS (hospitales públicos)", "en": "DEIS: SNSS subset (public hospitals)"},
    "grd_prin": {"es": "GRD: F84 principal, panel observado, toda modalidad", "en": "GRD: principal F84, observed panel, all activity"},
    "grd_prin_hosp": {"es": "GRD: F84 principal, hospitalización estricta", "en": "GRD: principal F84, strict hospitalisation"},
    "deis_note": {"es": "DEIS DIAG2 = causa externa (nunca F84):\nDEIS «cualquier posición» = principal. El F84\nsecundario del GRD no tiene equivalente DEIS.", "en": "DEIS DIAG2 = external cause (never F84):\nDEIS 'any position' = principal. Secondary\nF84 in GRD has no DEIS equivalent."},
    # S9
    "s9_grd_title": {"es": "GRD {v}: F84 por 100.000 hab., residencia, 2024", "en": "GRD {v}: F84 per 100,000 pop., residence, 2024"},
    "s9_a05_title": {"es": "REM A05: ingresos por 100.000 hab., establecimiento, 2024 (n = {n})", "en": "REM A05: entries per 100,000 pop., establishment, 2024 (n = {n})"},
    "s9_rate": {"es": "por 100.000 habitantes", "en": "per 100,000 population"},
    "s9_nodata": {"es": "sin datos", "en": "no data"},
    "s9_d_title": {"es": "GRD {v}: episodios F84 por 100.000 hab. según región de residencia y año", "en": "GRD {v}: F84 episodes per 100,000 pop. by region of residence and year"},
    "s9_e_title": {"es": "REM A05 autismo: ingresos por 100.000 hab. según región del establecimiento", "en": "REM A05 autism: entries per 100,000 pop. by region of establishment"},
    "s9_f_title": {"es": "Regiones 2024: GRD (residencia)\nfrente a A05 (lugar de atención)", "en": "Regions 2024: GRD (residence)\nvs A05 (place of care)"},
    "s9_f_x": {"es": "A05 ingresos por 100.000 hab. (log)", "en": "A05 entries per 100,000 pop. (log)"},
    "s9_f_y": {"es": "GRD episodios F84 por 100.000 hab. (log)", "en": "GRD F84 episodes per 100,000 pop. (log)"},
    "s15_f_note": {"es": "La explicación de cada diferencia se imprime íntegra en la tabla de controles de reproducción del material suplementario.",
                   "en": "The explanation of each difference is printed in full in the reproduction-controls table of the supplementary material."},
    "s9_n_estab": {"es": "n = establecimientos reportantes", "en": "n = reporting establishments"},
    "s9_warning": {"es": "ADVERTENCIA: REM localiza el establecimiento (lugar de atención) y GRD la comuna de residencia; los flujos interregionales de pacientes no se corrigen. Comparación ecológica.", "en": "WARNING: REM locates the establishment (place of care) and GRD the comuna of residence; inter-regional patient flows are not corrected. Ecological comparison."},
    "region": {"es": "Región", "en": "Region"}, "north_south": {"es": "(norte → sur)", "en": "(north → south)"},
    "unknown_res": {"es": "residencia desconocida", "en": "unknown residence"},
    "spearman": {"es": "ρ de Spearman", "en": "Spearman ρ"},
    # S10
    "s10_a_title": {"es": "Población nacional según base de proyección", "en": "National population by projection base"},
    "s10_a_axis": {"es": "Millones de personas", "en": "Millions of persons"},
    "base2017": {"es": "INE base Censo 2017, 30 de junio (principal)", "en": "INE base Census 2017, 30 June (primary)"},
    "base2024_jun": {"es": "INE base 2024, 30 de junio (sensibilidad)", "en": "INE base 2024, 30 June (sensitivity)"},
    "base2024_jan": {"es": "INE base 2024, 1 de enero (sensibilidad)", "en": "INE base 2024, 1 January (sensitivity)"},
    "censo2024": {"es": "Censo 2024, población enumerada", "en": "Census 2024, enumerated population"},
    "s10_b_title": {"es": "Razón frente a la base 2017 (nacional)", "en": "Ratio to base 2017 (national)"},
    "s10_b_axis": {"es": "Razón de denominadores (= razón inversa de tasas)", "en": "Denominator ratio (= inverse ratio of rates)"},
    "r_base2024": {"es": "base 2024 (30 jun) / base 2017", "en": "base 2024 (30 Jun) / base 2017"},
    "r_censo": {"es": "Censo 2024 / base 2017 (2024)", "en": "Census 2024 / base 2017 (2024)"},
    "s10_c_title": {"es": "Censo 2024 / base 2017 según región, 2024", "en": "Census 2024 / base 2017 by region, 2024"},
    "s10_d_title": {"es": "Razón según grupo de edad, 2024 (nacional)", "en": "Ratio by age group, 2024 (national)"},
    "age_group": {"es": "Grupo de edad (años)", "en": "Age group (years)"},
    "s10_e_title": {"es": "GRD {v} 2024\nsegún grupo de edad: tres denominadores", "en": "GRD {v} 2024\nby age group: three denominators"},
    "s10_e_axis": {"es": "Episodios F84 por 100.000 hab. (escala log)", "en": "F84 episodes per 100,000 pop. (log scale)"},
    "s10_f_title": {"es": "GRD {v} 2024\npor región de residencia: base 2017 frente a Censo 2024", "en": "GRD {v} 2024\nby region of residence: base 2017 vs Census 2024"},
    "s10_f_axis": {"es": "Episodios F84 por 100.000 hab. (IC 95 % exacto con base 2017)", "en": "F84 episodes per 100,000 pop. (exact 95% CI with base 2017)"},
    "with_base2017": {"es": "con base 2017", "en": "with base 2017"}, "with_censo": {"es": "con Censo 2024", "en": "with Census 2024"},
    "with_base2024": {"es": "con base 2024 (30 jun)", "en": "with base 2024 (30 Jun)"},
    # S11
    "s11_a_title": {"es": "FONASA 2025: beneficiarios según edad y sexo", "en": "FONASA 2025: beneficiaries by age and sex"},
    "s11_b_title": {"es": "APS 2025: inscritos según edad y sexo", "en": "APS 2025: enrolled persons by age and sex"},
    "s11_c_title": {"es": "ISAPRE 2025: beneficiarios según edad y sexo", "en": "ISAPRE 2025: beneficiaries by age and sex"},
    "thousands": {"es": "Miles de personas (stock de diciembre)", "en": "Thousands of persons (December stock)"},
    "s11_d_title": {"es": "Capas de cobertura, 2019–2025 (stocks de diciembre; INE 30 jun)", "en": "Coverage layers, 2019–2025 (December stocks; INE 30 Jun)"},
    "ine": {"es": "INE población residente (base 2017)", "en": "INE resident population (base 2017)"},
    "fonasa": {"es": "FONASA beneficiarios", "en": "FONASA beneficiaries"}, "aps": {"es": "Inscritos APS (lugar de inscripción)", "en": "APS enrolled (place of enrolment)"},
    "isapre": {"es": "ISAPRE beneficiarios", "en": "ISAPRE beneficiaries"},
    "s11_e_title": {"es": "Razón frente a la población INE", "en": "Ratio to INE population"},
    "s11_e_axis": {"es": "Personas de la capa / población INE", "en": "Persons in layer / INE population"},
    "s11_e_note": {"es": "No es una tasa de aseguramiento: mezcla stocks de diciembre con\nla proyección de junio, omite otros regímenes (FF.AA.) y las\ngeografías difieren (residencia, domicilio/inscripción, centro).", "en": "Not an insurance-coverage rate: mixes December stocks with the\nJune projection, omits other regimes (armed forces) and the\ngeographies differ (residence, domicile/enrolment, centre)."},
    "s11_f_title": {"es": "Estructura etaria 2025: % por banda decenal", "en": "Age structure 2025: % by 10-year band"},
    "s11_f_axis": {"es": "% de las personas de cada fuente", "en": "% of persons in each source"},
    "sex_unknown": {"es": "sexo/edad sin información excluidos de la pirámide", "en": "unknown sex/age excluded from the pyramid"},
    # S12
    "s12_a_title": {"es": "JUNAEB 2023: TEA según sexo y nivel (NO ponderado)", "en": "JUNAEB 2023: ASD by sex and level (UNWEIGHTED)"},
    "s12_b_title": {"es": "JUNAEB 2024: TEA ponderado (EXP_REG)", "en": "JUNAEB 2024: weighted ASD (EXP_REG)"},
    "s12_c_title": {"es": "JUNAEB 2025: TEA ponderado (EXP)", "en": "JUNAEB 2025: weighted ASD (EXP)"},
    "s12_d_title": {"es": "Razón hombre:mujer del % TEA según nivel y año", "en": "Male:female ratio of ASD % by level and year"},
    "s12_d_axis": {"es": "Razón H:M (IC 95 % aproximado, delta en log)", "en": "M:F ratio (approximate 95% CI, log-delta)"},
    "s12_e_title": {"es": "Estudiantes encuestados (n no ponderado) según nivel y año", "en": "Surveyed students (unweighted n) by level and year"},
    "s12_e_axis": {"es": "Estudiantes con respuesta (miles)", "en": "Students with a response (thousands)"},
    "s12_f_title": {"es": "Ponderado frente a no ponderado, 2024–2025", "en": "Weighted vs unweighted, 2024–2025"},
    "s12_f_x": {"es": "% no ponderado", "en": "Unweighted %"}, "s12_f_y": {"es": "% ponderado", "en": "Weighted %"},
    "unweighted_pct": {"es": "% no ponderado (IC 95 % de Wilson)", "en": "Unweighted % (Wilson 95% CI)"},
    "weighted_pct": {"es": "% ponderado (IC 95 %)", "en": "Weighted % (95% CI)"},
    "male": {"es": "Hombres", "en": "Males"}, "female": {"es": "Mujeres", "en": "Females"}, "all": {"es": "Todos", "en": "All"},
    "ne_reason_medio1": {"es": "1º medio 2024: variable TEA\ncompletamente vacía → no estimable", "en": "Grade 9 2024: ASD variable\nentirely empty → not estimable"},
    "tea_cases": {"es": "TEA reportado (n)", "en": "reported ASD (n)"},
    # S14
    "s14_a_title": {"es": "DEIS: F84 principal por 100.000 egresos según sexo", "en": "DEIS: principal F84 per 100,000 discharges by sex"},
    "s14_axis": {"es": "F84 en DIAG1 por 100.000 egresos (IC 95 % exacto)", "en": "F84 in DIAG1 per 100,000 discharges (exact 95% CI)"},
    "s14_b_title": {"es": "DEIS: según grupo de edad OMS, 2021 y 2024", "en": "DEIS: by WHO age group, 2021 and 2024"},
    "s14_c_title": {"es": "DEIS 2024: según sexo y grupo de edad OMS", "en": "DEIS 2024: by sex and WHO age group"},
    "s14_d_title": {"es": "DEIS: tasa según banda decenal y año", "en": "DEIS: rate by 10-year age band and year"},
    "s14_e_title": {"es": "DEIS: SNSS (público) frente a no SNSS", "en": "DEIS: SNSS (public) vs non-SNSS"},
    "s14_f_title": {"es": "DEIS: egresos con F84 principal según pertenencia", "en": "DEIS: discharges with principal F84 by ownership"},
    "s14_f_axis": {"es": "Egresos con F84 en DIAG1", "en": "Discharges with F84 in DIAG1"},
    "snss": {"es": "SNSS (hospitales públicos)", "en": "SNSS (public hospitals)"}, "no_snss": {"es": "No SNSS (privados, FF.AA., otros)", "en": "Non-SNSS (private, armed forces, other)"},
    "suppressed": {"es": "Suprimido por DEIS", "en": "Suppressed by DEIS"},
    "s14_note": {"es": "DEIS DIAG2 es causa externa y nunca contiene F84: «cualquier posición» = principal.", "en": "DEIS DIAG2 is the external cause and never contains F84: 'any position' = principal."},
    "age_band": {"es": "Banda de edad (años)", "en": "Age band (years)"},
    "share_snss": {"es": "% SNSS", "en": "% SNSS"},
    "s14_f_labels": {"es": "sobre cada barra: total y % SNSS", "en": "above each bar: total and % SNSS"},
    "s11_d_naps": {"es": "n = centros APS", "en": "n = primary-care centres"},
    "s11_e_note_short": {"es": "No es una tasa de aseguramiento (véase el pie)", "en": "Not an insurance-coverage rate (see caption)"},
    # S15
    "s15_a_title": {"es": "Controles de reproducción: observado frente a esperado", "en": "Reproduction controls: observed vs expected"},
    "expected": {"es": "Esperado (escala symlog)", "en": "Expected (symlog scale)"}, "observed": {"es": "Observado (escala symlog)", "en": "Observed (symlog scale)"},
    "identity": {"es": "identidad", "en": "identity"},
    "s15_b_title": {"es": "Diferencia relativa según magnitud esperada", "en": "Relative difference by expected magnitude"},
    "s15_b_axis": {"es": "100 × (observado − esperado) / esperado", "en": "100 × (observed − expected) / expected"},
    "s15_b_x": {"es": "Esperado (escala log; esperado ≠ 0)", "en": "Expected (log scale; expected ≠ 0)"},
    "s15_c_title": {"es": "Estado de los controles según módulo", "en": "Control status by module"},
    "s15_c_axis": {"es": "Número de controles", "en": "Number of controls"},
    "status_ok": {"es": "coincide", "en": "matches"}, "status_differs": {"es": "difiere (explicado)", "en": "differs (explained)"}, "status_info": {"es": "informativo (sin valor esperado)", "en": "informative (no expected value)"},
    "s15_d_title": {"es": "GRD y DEIS (módulos 01, 01b)", "en": "GRD and DEIS (modules 01, 01b)"},
    "s15_e_title": {"es": "REM, denominadores, encuestas, educación y modelos (02–06)", "en": "REM, denominators, surveys, education and models (02–06)"},
    "s15_f_title": {"es": "Controles que difieren y su explicación", "en": "Controls that differ and their explanation"},
    "tol": {"es": "tolerancia ±0,5 %", "en": "±0.5% tolerance"},
    "mod_00_provenance": {"es": "00 procedencia", "en": "00 provenance"}, "mod_01_grd_core": {"es": "01 GRD", "en": "01 GRD"}, "mod_01b_deis_egresos": {"es": "01b DEIS", "en": "01b DEIS"},
    "mod_02_rem_pathway": {"es": "02 REM", "en": "02 REM"}, "mod_03_denominators": {"es": "03 denominadores", "en": "03 denominators"}, "mod_04_surveys": {"es": "04 encuestas", "en": "04 surveys"},
    "mod_05_education": {"es": "05 educación", "en": "05 education"}, "mod_06_models": {"es": "06 modelos", "en": "06 models"}, "mod_07_controls": {"es": "07 controles", "en": "07 controls"},
    "mod_08c_figures_triangulation": {"es": "08c triangulación", "en": "08c triangulation"},
    "expl_grd_f84_any_strict_hospitalisation": {"es": "el valor esperado 2023–2024 corresponde al panel fijo de 65; el observado usa el panel anual (68/72 hospitales)", "en": "expected 2023–2024 values refer to the fixed panel of 65; observed uses the annual panel (68/72 hospitals)"},
    "expl_deis_vs_grd_observed_panel_strict_hospitalisation_vs_config": {"es": "misma discrepancia de panel (observado 68/72 frente a fijo 65), documentada por el módulo 01", "en": "same panel discrepancy (observed 68/72 vs fixed 65), documented by module 01"},
    "expl_grd_persons_within_year_f84_any": {"es": "diferencia de 1 persona: episodios F84 sin identificador válido excluidos del conteo de personas", "en": "1-person difference: F84 episodes without a valid identifier excluded from the person count"},
    "expl_grd_f84_exact_duplicates_on_read_columns": {"es": "un par de filas duplicado sobre las columnas leídas (difieren en otras columnas); se conserva sin eliminar", "en": "one duplicate pair over the columns read (they differ in other columns); kept, not removed"},
    "expl_rem20_duplicate_establishment_area_month_rows": {"es": "una fila repetida aditiva (una en cero y otra con datos) conservada", "en": "one additive repeated row (one zero, one with data) kept"},
    "expl_default": {"es": "véase la nota del módulo en T8", "en": "see the module note in T8"},
    # tablas
    "system": {"es": "Sistema", "en": "System"}, "series": {"es": "Serie", "en": "Series"}, "value": {"es": "Valor", "en": "Value"}, "unit": {"es": "Unidad", "en": "Unit"},
    "denominator": {"es": "Denominador", "en": "Denominator"}, "reporting_n": {"es": "N reportante", "en": "Reporting N"}, "rate_100k": {"es": "Por 100.000 hab. (IC 95 %)", "en": "Per 100,000 pop. (95% CI)"},
    "note": {"es": "Nota", "en": "Note"}, "population": {"es": "Población INE 2024 (base 2017)", "en": "INE population 2024 (base 2017)"},
    "grd_ep_2024": {"es": "GRD episodios F84 2024", "en": "GRD F84 episodes 2024"}, "a05_2024": {"es": "A05 ingresos autismo 2024", "en": "A05 autism entries 2024"},
    "estab": {"es": "Establecimientos reportantes", "en": "Reporting establishments"},
    "level": {"es": "Nivel", "en": "Level"}, "sex": {"es": "Sexo", "en": "Sex"}, "n_students": {"es": "Estudiantes con respuesta (n)", "en": "Students with a response (n)"},
    "n_tea": {"es": "TEA reportado (n)", "en": "Reported ASD (n)"}, "estimator": {"es": "Estimador", "en": "Estimator"}, "estimable": {"es": "Estimable", "en": "Estimable"},
    "yes": {"es": "sí", "en": "yes"}, "no": {"es": "no", "en": "no"},
    "discharges": {"es": "Egresos DEIS", "en": "DEIS discharges"}, "f84_diag1": {"es": "F84 en DIAG1", "en": "F84 in DIAG1"}, "rate_disch": {"es": "Por 100.000 egresos (IC 95 %)", "en": "Per 100,000 discharges (95% CI)"},
    "module": {"es": "Módulo", "en": "Module"}, "control": {"es": "Control", "en": "Control"}, "key": {"es": "Clave", "en": "Key"}, "status": {"es": "Estado", "en": "Status"},
    "rel_diff": {"es": "Diferencia relativa (%)", "en": "Relative difference (%)"}, "explanation": {"es": "Explicación", "en": "Explanation"},
    "col_expected": {"es": "Esperado", "en": "Expected"}, "col_observed": {"es": "Observado", "en": "Observed"},
    "ratio": {"es": "Razón", "en": "Ratio"}, "share_ine": {"es": "% de la población INE", "en": "% of INE population"},
}


def tr(key: str, lang: str, **kw) -> str:
    s = LBL[key][lang]
    return s.format(**kw) if kw else s


#: EL SIGNO NEGATIVO Y EL SIGNO DE PORCENTAJE, las dos convenciones que estas láminas escriben con cifras.
#:
#: El NEGATIVO lleva el menos tipográfico (U+2212), no el guion ASCII: el guion mide 2,9 pt a 8 pt de
#: cuerpo y se dibuja a la altura de la x, mientras la S15 (b) —el panel que imprime las cifras
#: negativas— separa sus intervalos con raya (U+2013, 4,1 pt), de modo que puestos uno junto al otro se
#: leían igual. La regla NO
#: se repite aquí: vive en `common.fmt_number` (y por tanto en `common.fmt_ci`), y este módulo la hereda
#: porque TODA cifra que imprime pasa por `num` —rótulos de valor, notas, títulos, leyendas, las marcas de
#: eje de `localise_ticks` y las tablas formateadas—. Lo que este módulo sí garantiza es que no haya
#: atajos: ningún rótulo de lámina se formatea a mano (los únicos formatos crudos que quedan son los años
#: de dos cifras «’19», que nunca son negativos, y las líneas de consola y de diagnóstico). Las columnas
#: `*_numeric.csv`, que son para leer con una máquina, siguen llevando el número crudo.
#:
#: El PORCENTAJE se escribe «12,3 %» en español y «12.3%» en inglés. Esa regla todavía no está en `common`
#: —la escriben nueve módulos por su cuenta— y aquí la aplica `pct_str`.


def num(x, dec=0, lang="es"):
    return C.fmt_number(x, dec, lang)


def pct_str(x, lang="es", dec=1):
    """Porcentaje en la convención del idioma: «12,3 %» en español (espacio) y «12.3%» en inglés (pegado).

    El rótulo de valor de la S14 (f) escribía a mano el sufijo « %» sin mirar el idioma, de modo que la
    lámina INGLESA imprimía «78 %» dentro de un corpus que escribe «78%». Se llama `pct_str` y no `pct`
    porque `figS12` y `figS15` usan `pct` como nombre de una variable local: una función de módulo con ese
    nombre quedaría tapada justo donde se la necesita."""
    return num(x, dec, lang) + (" %" if lang == "es" else "%")


#: EL SEPARADOR DEL INTERVALO IMPRESO. Entre dos cotas POSITIVAS va la raya corta —«0,02–0,23» se lee sin
#: esfuerzo—; en cuanto una cota es NEGATIVA, no: «−0,21–0,00» pone el menos tipográfico (U+2212, 47 px a
#: 600 ppp) y la raya (U+2013, 29 px) a cuatro caracteres uno de otro, dos trazos de peso distinto en una
#: misma expresión, y el lector tiene que decidir cuál separa y cuál es el signo. Es el defecto que el
#: verificador de contenido leyó en la Figura S51 (a) y (b). En ese caso —y sólo en ese, para no alargar
#: los rótulos donde no hace falta— se separa con la conjunción con la que el resto del corpus separa las
#: cotas (`common.fmt_ci`: «19,9 a 21,6» / «19.9 to 21.6»). Es la misma regla que aplica `ci` en
#: `15b_spatial_correlation.py`, escrita aquí para que ningún intervalo de este módulo pueda saltársela.
_CI_WORD = {"es": " a ", "en": " to "}


def ci_span(lo, hi, dec=2, lang="es") -> str:
    """Intervalo impreso: raya corta entre dos cotas positivas, conjunción si alguna es negativa."""
    sep = _CI_WORD[lang] if (float(lo) < 0 or float(hi) < 0) else C.EN_DASH
    return f"{num(lo, dec, lang)}{sep}{num(hi, dec, lang)}"


def merge_json(path: Path, new: dict) -> None:
    current = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
    current.update(new)
    C.atomic_write_json(current, path)


def out_dir(variant: str, lang: str, kind: str) -> Path:
    p = CFG.OUT / variant / lang / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def localise_ticks(fig, lang: str) -> None:
    """Formatea los rótulos numéricos de ejes lineales con el separador decimal del idioma (coma en 'es', punto en 'en')
    y separador de miles a partir de 10.000 (los años quedan sin separador). Los ejes con rótulos fijos o escala log no se tocan."""
    from matplotlib.ticker import ScalarFormatter, FuncFormatter
    for ax in fig.axes:
        for axis, scale in ((ax.xaxis, ax.get_xscale()), (ax.yaxis, ax.get_yscale())):
            if scale != "linear" or not isinstance(axis.get_major_formatter(), ScalarFormatter):
                continue
            lo, hi = sorted(axis.get_view_interval())
            ticks = [t for t in axis.get_majorticklocs() if lo - 1e-9 <= t <= hi + 1e-9]
            if not ticks:
                continue
            # Un eje de AÑOS se reconoce por sus marcas y se deja como está; el resto SIEMPRE lleva el
            # separador de miles del idioma. La regla anterior («entero por debajo de 10.000, sin
            # separador») imprimía «5000» a secas, que no es la convención de ninguno de los dos idiomas.
            if (all(abs(t - round(t)) < 1e-6 and 1900.0 <= t <= 2100.0 for t in ticks)
                    and max(ticks) - min(ticks) <= 40.0):
                continue
            dec = 3
            for d in range(4):
                if all(abs(t * 10 ** d - round(t * 10 ** d)) < 1e-6 for t in ticks):
                    dec = d
                    break
            axis.set_major_formatter(FuncFormatter(lambda v, _p, dec=dec, lang=lang: num(v, dec, lang)))


def save(fig, path: Path, lang: str) -> Path:
    localise_ticks(fig, lang)
    return C.save_fig(fig, path)


# ---------------------------------------------------------------------------
# Norma de lámina: 180 × 245 mm en vertical, dibujada 1:1 (una lámina por página, sin reducción)
# 3 filas × 2 columnas, seis paneles como máximo, letras minúsculas, nada bajo 6 pt, 600 dpi.
# ---------------------------------------------------------------------------
PLATE_W_MM, PLATE_H_MM = 180.0, 245.0
MM_PER_IN = 25.4
PLATE_SIZE = (PLATE_W_MM / MM_PER_IN, PLATE_H_MM / MM_PER_IN)
FS_BASE, FS_TITLE, FS_TICK, FS_LEG, FS_MIN = 8.0, 9.0, 7.0, 7.0, 6.0
PLATE_TITLE_CHARS = 33
PLATE_TITLE_W_PT = (PLATE_W_MM / MM_PER_IN * 72.0) / 2 - (4.0 / MM_PER_IN * 72.0)
NOTE_W_PT = 150.0
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)


def plate_style():
    """Estilo de la lámina vertical: base 8 pt, título de panel 9 pt negrita, marcas 7 pt, leyenda 7 pt."""
    plt, sns = C.style()
    plt.rcParams.update({
        "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold", "axes.labelsize": FS_BASE,
        "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK, "legend.fontsize": FS_LEG, "legend.title_fontsize": FS_LEG,
        "axes.linewidth": 0.7, "grid.linewidth": 0.45, "lines.linewidth": 1.3, "lines.markersize": 3.4,
        "patch.linewidth": 0.6, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
        "xtick.major.size": 2.2, "ytick.major.size": 2.2, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
        "axes.labelpad": 2.0, "axes.titlepad": 3.0, "legend.handlelength": 1.5, "legend.handletextpad": 0.5,
        "legend.labelspacing": 0.30, "legend.columnspacing": 0.9, "legend.borderpad": 0.3,
        "figure.dpi": 100, "savefig.dpi": 600,
    })
    return plt, sns


def new_plate(plt, nrows: int = 3, ncols: int = 2):
    fig = plt.figure(figsize=PLATE_SIZE, constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    gs = fig.add_gridspec(nrows, ncols)
    return fig, gs


def panel_head(ax, letter_: str, title: str, fs: float = FS_TITLE, pad: float = 3.0, chars: int | None = None, dx: float = 0.0) -> None:
    """Cabecera del panel: letra minúscula y título a la izquierda de SU celda, plegados al ancho de la celda.

    El plegado es por ancho MEDIDO y no por número de caracteres; `C.plate_align_titles` reancla el título al
    borde izquierdo de la celda al guardar, de modo que ninguno se sale del lienzo. `chars` y `dx` se conservan
    por compatibilidad con las llamadas antiguas."""
    # matplotlib guarda TRES artistas de título (izquierda, centro, derecha): si un ayudante ya puso el
    # título centrado, escribir el de la izquierda dejaría los dos impresos, uno encima del otro.
    ax.set_title("", loc="center"); ax.set_title("", loc="right")
    ax.set_title(C.plate_wrap(f"({letter_}) {title}", PLATE_TITLE_W_PT, fs, "bold"),
                 loc="left", x=dx, fontsize=fs, fontweight="bold", pad=pad, linespacing=1.15)


def add_letter(ax, letter_: str, fs: float = FS_TITLE, pad: float = 3.0) -> None:
    """Antepone la letra minúscula al título que ya puso un ayudante (pirámide, barras JUNAEB, mapa…)."""
    panel_head(ax, letter_, ax.get_title("center") or ax.get_title("left"), fs=fs, pad=pad)


def plate_legend(ax, *args, loc: str = "upper left", fs: float | None = None, ncol: int = 1, **kw):
    """Leyenda de celda estrecha: cuerpo 6,2 pt y recuadro blanco OPACO.

    Con el recuadro translúcido anterior, la línea punteada de la Ley 21.545 y el sombreado 2020–21 se
    imprimían a través del texto de la leyenda y lo dejaban ilegible."""
    lg = ax.legend(*args, loc=loc, fontsize=fs if fs is not None else FS_MIN + 0.2, ncol=ncol,
                   frameon=True, framealpha=1.0, edgecolor="#cccccc", facecolor="white",
                   borderpad=0.25, **kw)
    lg.set_zorder(6)
    # Una leyenda ancha SÍ gobierna el reparto de `constrained_layout`: con etiquetas largas encogía los ejes
    # de la celda hasta colapsarlos. La que se dibuja DENTRO del panel se saca del reparto; la que se ancla
    # fuera (bbox_to_anchor, bajo el eje) tiene que seguir en él para que se le reserve sitio.
    if "bbox_to_anchor" not in kw:
        lg.set_in_layout(False)
    return lg


def plate_note(ax, text: str, x: float = 0.5, y: float = 0.985, ha: str = "center", va: str = "top",
               fs: float | None = None, color: str = "#333333", width_pt: float = NOTE_W_PT):
    """Nota dentro del panel, plegada al ancho medido del área de ejes y sobre recuadro blanco translúcido."""
    fs = FS_MIN + 0.3 if fs is None else fs
    return ax.text(x, y, C.plate_wrap(text, width_pt, fs, "normal"), transform=ax.transAxes, fontsize=fs,
                   ha=ha, va=va, color=color, bbox=NOTE_BBOX, linespacing=1.25, zorder=6)


def freeze_texts(fig) -> None:
    """Los rótulos sueltos (ax.text / annotate) no deben gobernar el reparto del lienzo: colapsarían los ejes."""
    for ax in fig.axes:
        for t in ax.texts:
            t.set_in_layout(False)


def reserve_ylabel_room(fig, margin_px: float = 2.0, rounds: int = 2) -> None:
    """Reserva DENTRO de la celda el hueco que el rótulo girado del eje Y necesita a la izquierda.

    El reparto del lienzo mide los márgenes de una celda con ejes gemelos por el gemelo —que no tiene marcas
    a la izquierda— y deja al panel un canalón de 27 pt donde su columna de marcas y su rótulo girado piden
    45. matplotlib coloca entonces el rótulo fuera de la celda, la guarda de recorte lo devuelve dentro y
    acaba impreso sobre sus propias marcas: es el defecto «rótulo de eje sobre sus marcas» que los
    verificadores encontraron en la Figura 3 (f), la S1 (f), la S2 (b, d) y la S7 (d, f).

    Aquí se mide la composición YA CONGELADA y, cuando falta sitio, se estrecha el panel lo justo: el rótulo
    vuelve a su colocación automática, a la izquierda de unas marcas que ahora empiezan más adentro. Se
    aplica a todos los ejes que comparten celda (el panel y su gemelo) para no romper la superposición.
    """
    for _ in range(max(1, rounds)):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        groups: dict = {}
        for ax in fig.axes:
            spec = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
            if spec is None or not ax.get_visible():
                continue
            groups.setdefault((spec.num1, spec.num2), []).append(ax)
        moved = False
        for group in groups.values():
            cell = C.plate_cell_box(fig, group[0])
            grow_left = grow_right = 0.0
            for ax in group:
                if not getattr(ax, "axison", True) or not ax.yaxis.get_visible():
                    continue
                lab = ax.yaxis.label
                if not str(lab.get_text()).strip():
                    continue
                try:
                    b = lab.get_window_extent(r)
                except (AttributeError, ValueError, RuntimeError):
                    continue
                pad_px = float(ax.yaxis.labelpad) * fig.dpi / 72.0
                boxes = []
                for t in ax.get_yticklabels():
                    if t.get_visible() and str(t.get_text()).strip():
                        try:
                            boxes.append(t.get_window_extent(r))
                        except (AttributeError, ValueError, RuntimeError):
                            pass
                if ax.yaxis.get_label_position() == "right":
                    edge = max((q.x1 for q in boxes), default=ax.bbox.x1)
                    grow_right = max(grow_right, edge - (cell.x1 - margin_px - b.width - pad_px))
                else:
                    edge = min((q.x0 for q in boxes), default=ax.bbox.x0)
                    grow_left = max(grow_left, (cell.x0 + margin_px + b.width + pad_px) - edge)
            if grow_left <= 0.5 and grow_right <= 0.5:
                continue
            dl = max(0.0, grow_left) / fig.bbox.width
            dr = max(0.0, grow_right) / fig.bbox.width
            for ax in group:
                pos = ax.get_position()
                width = pos.width - dl - dr
                if width <= 0.35 * pos.width:
                    continue
                ax.set_position([pos.x0 + dl, pos.y0, width, pos.height])
                moved = True
        if not moved:
            return


def separate_xticks(fig, gap_pt: float = 1.0) -> None:
    """Deja un blanco visible entre marcas VECINAS del eje X.

    En el mapa de calor del panel (e) de la S9 las seis marcas de año se imprimían pegadas de borde a borde
    y «201920202021202220232024» se leía como un solo número: la columna de nombres de región dejaba al eje
    menos ancho que la suma de los rótulos. Se mide lo dibujado y se actúa por el orden de la norma: reducir
    el cuerpo hasta el mínimo de 6 pt y, sólo si aún se tocan, girar los rótulos."""
    fig.canvas.draw()
    r = C._pl_renderer(fig, draw=False)

    def clashes(labs):
        boxes = sorted([b for b in (C._pl_extent(t, r) for t in labs) if b is not None], key=lambda b: b.x0)
        gap = gap_pt * fig.dpi / 72.0
        return any(boxes[i].x1 + gap > boxes[i + 1].x0 for i in range(len(boxes) - 1))

    for ax in fig.axes:
        labs = [t for t in ax.xaxis.get_ticklabels() if t.get_visible() and str(t.get_text()).strip()]
        if len(labs) < 2 or max(abs(t.get_rotation() % 180) for t in labs) > 20:
            continue
        if not clashes(labs):
            continue
        for fs in (6.5, C.PLATE_FS_FLOOR):
            if min(t.get_size() for t in labs) <= fs:
                continue
            for t in labs:
                t.set_size(min(t.get_size(), fs))
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            if not clashes(labs):
                break
        if clashes(labs):
            for t in labs:
                t.set_rotation(90)
                t.set_ha("center")
                t.set_va("top")
            fig.canvas.draw()
            r = fig.canvas.get_renderer()


# ---------------------------------------------------------------------------
# LA RAYA DEL INTERVALO IMPRESO (fase 4i, tarea H3; unificada en la fase 4j, tarea J2)
# ---------------------------------------------------------------------------
#: UN INTERVALO NUMÉRICO QUE EL LECTOR LEE SE SEPARA CON RAYA CORTA (U+2013), NUNCA CON GUION; el guion
#: ASCII queda para lo que una máquina vuelve a leer (las claves `age_group`, `depth_bin`, `years` y
#: `age_band_10` de las tablas tidy, los nombres de archivo y los códigos), y el menos tipográfico para el
#: número negativo.
#:
#: LA REGLA YA NO VIVE AQUÍ. Hasta la fase 4i estaba copiada, palabra por palabra, en CINCO módulos —`08a`,
#: `08b`, `08c`, `14` y `15b`— y por eso NO estaba en los otros cuatro que dibujan láminas (`06`, `08d`,
#: `13`, `15`): 448 intervalos con guion frente a 774 con raya en nueve láminas publicadas. Está escrita una
#: sola vez en `common` (`C.range_dash` y `C.plate_range_dash`), con sus cuatro categorías y sus tres
#: trazos, y `common` la aplica sola al principio de `plate_fit` y de `plate_resolve`, por los que pasan
#: TODAS las láminas del estudio. Estas dos funciones se conservan porque el módulo las nombra en su
#: guardado y porque dejan EXPLÍCITO el momento en que se aplica: antes del reparto, para que el motor mida
#: el texto definitivo y una marca que crece 1,5 pt al cambiar de trazo no se salga de su columna.
def dash_label(s: str) -> str:
    """«0-4» → «0–4». Delega en la regla única del estudio (`common.range_dash`)."""
    return C.range_dash(s)


def dash_intervals(fig) -> int:
    """Pasa la regla por todo el texto que la lámina dibuja. Delega en `common.plate_range_dash`.

    Devuelve cuántos rótulos cambió: 0 en una lámina que ya cumple, de modo que sirve de medida."""
    return C.plate_range_dash(fig)


# ---------------------------------------------------------------------------
# LA LÍNEA DE CONTEXTO NO DEJA UN PUNTO SUELTO SOBRE LA LEYENDA (fase 4i, tarea H3)
# ---------------------------------------------------------------------------
#: Las marcas de contexto de estas láminas —la línea punteada de la Ley 21.545 y el borde de la disrupción
#: del reporte de 2020–21— se dibujan de SUELO A TECHO del panel, y la leyenda se apoya a `borderaxespad`
#: del borde superior del eje: 3,1 pt con el cuerpo de 6,2 pt de estas celdas. Como el recuadro de la
#: leyenda es OPACO —lo es a propósito, para que ninguna marca de contexto atraviese su texto—, tapaba la
#: línea entera SALVO esos tres puntos de arriba, y la página imprimía un punto aislado flotando sobre la
#: leyenda, sin línea debajo que lo explicara. Es lo que el verificador de contenido leyó en la Figura 2
#: (d), y está en veinte láminas más de los mismos tres módulos.
#:
#: La línea se recorta a la altura del borde INFERIOR de la leyenda que la cruza: sigue entrando en el
#: recuadro —que es lo que un lector espera de una línea que pasa por detrás— y no deja rastro por encima.
#: Sólo se recorta el asomo CORTO (≤ `max_gap_pt`): un tramo largo por encima de una leyenda es línea, no
#: suciedad, y se deja intacto. Se hace DESPUÉS de `plate_resolve`, que es quien mueve por última vez ejes
#: y leyendas: medido antes, el asomo volvía en tres paneles de cada lámina. Recortar una línea sólo QUITA
#: tinta, de modo que la lámina que el verificador acaba de dar por limpia sigue estándolo.
def tuck_context_lines(fig, max_gap_pt: float = 10.0) -> int:
    """Recorta bajo la leyenda opaca que la cruza toda línea vertical de contexto que sólo asoma un punto.

    Devuelve cuántas líneas recortó, que es la medida de la que se informa (0 en una lámina limpia)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    trimmed = 0
    for ax in fig.axes:
        lg = ax.get_legend()
        if lg is None or not lg.get_visible() or not lg.get_frame_on():
            continue
        try:
            frame = lg.get_frame()
            if float(frame.get_alpha() if frame.get_alpha() is not None else 1.0) < 0.9:
                continue
            axb, lb = ax.get_window_extent(renderer=r), lg.get_window_extent(renderer=r)
        except (AttributeError, ValueError, RuntimeError, TypeError):
            continue
        if axb.height <= 0 or lb.y0 <= axb.y0 or lb.x1 <= axb.x0 or lb.x0 >= axb.x1:
            continue
        gap_pt = (axb.y1 - lb.y1) * 72.0 / fig.dpi
        if not 0.05 < gap_pt <= max_gap_pt:
            continue
        floor_frac = max(0.0, min(1.0, (lb.y0 - axb.y0) / axb.height))
        for ln in list(ax.lines):
            try:
                xd, yd = list(ln.get_xdata()), list(ln.get_ydata())
                # firma de `axvline`: dos puntos, misma x, y de 0 a 1 en coordenadas del eje
                if (len(xd) != 2 or len(yd) != 2 or xd[0] != xd[1]
                        or [float(v) for v in yd] != [0.0, 1.0] or not ln.get_visible()
                        or ln.get_zorder() >= lg.get_zorder()):
                    continue
                xpix = float(ax.transData.transform((float(xd[0]), 0.0))[0])
            except (AttributeError, ValueError, RuntimeError, TypeError):
                continue
            if lb.x0 - 1.0 <= xpix <= lb.x1 + 1.0:
                ln.set_ydata([0.0, floor_frac])
                trimmed += 1
    if trimmed:
        fig.canvas.draw()
    return trimmed


def save_plate(fig, path: Path, lang: str, dpi: int = 600) -> Path:
    """Guarda sin recorte: el archivo mide exactamente 180 × 245 mm a 600 dpi (1:1 en la página)."""
    localise_ticks(fig, lang)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    freeze_texts(fig)
    # Motor de descongestión (common.py): mide lo dibujado y resuelve colisiones, recortes y leyendas.
    # `plate_fit` actúa con la composición todavía viva (marcas de eje, rótulos de eje, leyendas);
    # `plate_resolve`, ya congelada, separa los rótulos que se pisan y devuelve dentro lo que se sale.
    # La regla de la raya se aplica ANTES del reparto: el motor mide el texto definitivo y una
    # marca que crece 1,5 pt al cambiar de trazo no se sale de su columna después de medida.
    dash_intervals(fig)
    C.plate_fit(fig)
    C.plate_align_titles(fig)
    reserve_ylabel_room(fig)
    C.plate_align_titles(fig)
    # Los rótulos de nube se colocan con la composición YA CONGELADA: hecho antes, el reparto del lienzo
    # movía los ejes y el rótulo acababa sobre un marcador que en el momento de medir no estaba ahí.
    for _ax, _anns in getattr(fig, "_plate_points", []):
        place_point_labels(_ax, _anns)
    separate_xticks(fig)
    C.plate_frame_notes(fig)
    C.plate_resolve(fig)
    # El recorte de las líneas de contexto va DESPUÉS de `plate_resolve`, que es quien mueve por
    # última vez ejes y rótulos: medido antes, la leyenda de tres paneles de cada lámina todavía
    # cambiaba de sitio y el asomo volvía. Recortar una línea sólo QUITA tinta, de modo que la
    # lámina que el verificador acaba de dar por limpia sigue estándolo.
    tuck_context_lines(fig)
    # Modo revista (LANCET_PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    fig.savefig(path, dpi=dpi, facecolor="white")
    return path


def timed(name: str):
    def deco(fn):
        def wrapper(*a, **k):
            t = time.perf_counter()
            r = fn(*a, **k)
            TIMINGS[name] = TIMINGS.get(name, 0.0) + time.perf_counter() - t
            return r
        return wrapper
    return deco


# ---------------------------------------------------------------------------
# Utilidades de nombres y códigos (idénticas a los módulos 01 y 03)
# ---------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = strip_accents(str(value)).upper().replace("'", " ").replace("’", " ").replace("-", " ").replace("¿", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", text)).strip()


def normalise_codes(series: pd.Series) -> np.ndarray:
    out = (series.fillna("").astype(object).str.replace(".", "", regex=False).str.replace(" ", "", regex=False).str.strip().str.upper())
    return out.to_numpy(dtype=object)


class Controls:
    def __init__(self):
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
        self.rows.append(dict(name=name, key=key, expected=expected, observed=observed, abs_diff=diff, rel_diff=rel, status=status, note=note))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


# ---------------------------------------------------------------------------
# GRD por comuna de residencia (S9): lectura de los GRD anuales y tabla tidy reutilizable
# ---------------------------------------------------------------------------
@timed("grd_residence_scan")
def grd_residence_comuna_year(refresh: bool, ctl: Controls) -> pd.DataFrame:
    path = CFG.TIDY / "grd_residence_comuna_year.csv"
    if path.is_file() and not refresh:
        df = pd.read_csv(path, dtype={"comuna_norm": str, "match_method": str})
        log(f"GRD por comuna de residencia: reutilizada {path.name} ({len(df)} filas)")
        return df
    diags = C.GRD_DIAG_COLS
    codes = {v: list(CFG.VARIANTS[v]["grd_subcodes"]) for v in VARIANTS}
    frames = []
    for year in CFG.YEARS_GRD:
        f = CFG.PATHS["grd"] / f"GRD_PUBLICO_{year}.csv"
        if not f.is_file():
            raise FileNotFoundError(f"Falta {f}; S9 requiere los GRD anuales para la región de residencia.")
        t = time.perf_counter()
        parts = []
        for chunk in C.iter_grd(f, ["COMUNA"] + diags, chunksize=200_000):
            n = len(chunk)
            diag = np.empty((n, len(diags)), dtype=object)
            for j, col in enumerate(diags):
                diag[:, j] = normalise_codes(chunk[col]) if col in chunk.columns else ""
            cand = np.zeros(n, dtype=bool)
            for j in range(len(diags)):
                cand |= np.char.startswith(diag[:, j].astype(str), "F84")
            raw = chunk["COMUNA"].fillna("").astype(object).str.strip()
            cmap = {v: normalize_name(v) for v in raw.unique()}
            df = pd.DataFrame({"comuna_norm": raw.map(cmap).to_numpy(dtype=object), "n_episodes": 1})
            idx = np.flatnonzero(cand)
            for v in VARIANTS:
                anyv = np.zeros(n, dtype=int)
                prin = np.zeros(n, dtype=int)
                if len(idx):
                    sub = diag[idx]
                    anyv[idx] = np.isin(sub, codes[v]).any(axis=1).astype(int)
                    prin[idx] = np.isin(sub[:, 0], codes[v]).astype(int)
                df[f"n_f84_any_{v}"] = anyv
                df[f"n_f84_principal_{v}"] = prin
            parts.append(df.groupby("comuna_norm", as_index=False).sum())
        agg = pd.concat(parts).groupby("comuna_norm", as_index=False).sum()
        agg.insert(0, "year", year)
        frames.append(agg)
        log(f"GRD {year}: {int(agg.n_episodes.sum()):,} episodios, {len(agg)} comunas de residencia ({time.perf_counter() - t:.0f} s)")
    out = pd.concat(frames, ignore_index=True)
    # crosswalk explícito (sin fuzzy): nombre normalizado INE y alias documentados
    xw = pd.read_csv(CFG.TIDY / "comuna_crosswalk.csv", dtype=str)
    lookup, method = {}, {}
    for r in xw.itertuples():
        lookup[r.comuna_norm] = (int(r.cut_comuna), int(r.cut_region))
        method[r.comuna_norm] = "exact"
        if isinstance(r.aliases_norm, str) and r.aliases_norm.strip():
            for a in r.aliases_norm.split("|"):
                a = a.strip()
                if a and a not in lookup:
                    lookup[a] = (int(r.cut_comuna), int(r.cut_region))
                    method[a] = "alias"
    out["cut_comuna"] = out.comuna_norm.map(lambda s: lookup.get(s, (np.nan, np.nan))[0])
    out["cut_region"] = out.comuna_norm.map(lambda s: lookup.get(s, (np.nan, np.nan))[1])
    out["match_method"] = out.comuna_norm.map(lambda s: method.get(s, "unmatched"))
    out["unit"] = "GRD episodes (rows) by normalised COMUNA of residence; F84 any position / principal per variant"
    out["geography"] = "comuna of residence as recorded in GRD (matched to INE names via comuna_crosswalk; unmatched kept as unknown)"
    out["script"] = SCRIPT
    C.atomic_write_csv(out, path)
    log(f"escrita {path.name}: {len(out)} filas; no enlazadas: {sorted(out.loc[out.match_method == 'unmatched', 'comuna_norm'].unique())}")
    return out


# ---------------------------------------------------------------------------
# Carga de tablas tidy
# ---------------------------------------------------------------------------
@timed("load")
def load_all(refresh_grd: bool, ctl: Controls) -> dict:
    D = {}
    D["edu"] = C.read_tidy("education_summary_year")
    D["pie"] = C.read_tidy("pie_series")
    D["jun"] = C.read_tidy("junaeb_tea_year_level")
    D["surv"] = C.read_tidy("survey_estimates", dtype={"survey_year": str})
    D["conv"] = C.read_tidy("models_convergence_index")
    D["grd"] = C.read_tidy("grd_year_summary")
    D["grd_age"] = C.read_tidy("grd_age_sex_year")
    D["dvg"] = C.read_tidy("deis_vs_grd_year")
    D["dest"] = C.read_tidy("deis_establishment_year")
    D["dage"] = C.read_tidy("deis_age_who_year")
    D["dsex"] = C.read_tidy("deis_age_sex_year")
    D["dsum"] = C.read_tidy("deis_year_summary")
    D["rem"] = C.read_tidy("rem_pathway_annual", dtype={"code": str})
    D["remest"] = C.read_tidy("rem_establishment_year", dtype={"code": str, "IdRegion": str, "IdComuna": str, "id_comuna_5d": str}, low_memory=False)
    D["ine"] = C.read_tidy("ine_population_region_national_year_age_sex")
    D["ine_sens"] = C.read_tidy("ine_population_sensitivity")
    D["ine_cmp"] = C.read_tidy("ine_population_base_comparison")
    D["cov"] = C.read_tidy("coverage_layers_year")
    D["fon_nat"] = C.read_tidy("fonasa_beneficiaries_national_year")
    D["isa_nat"] = C.read_tidy("isapre_beneficiaries_national_year")
    fon = C.read_tidy("fonasa_beneficiaries_comuna_year", usecols=["year", "sex", "age_band_5y", "age_band_10y", "beneficiaries"])
    D["fon_age"] = fon.groupby(["year", "sex", "age_band_5y", "age_band_10y"], dropna=False, as_index=False).beneficiaries.sum()
    aps = C.read_tidy("aps_enrolment_comuna_year", usecols=["year", "sex", "age_band_20y", "age_band_10y", "enrolled"])
    D["aps_age"] = aps.groupby(["year", "sex", "age_band_20y", "age_band_10y"], dropna=False, as_index=False).enrolled.sum()
    isa = C.read_tidy("isapre_beneficiaries_comuna_year", usecols=["year", "row_type", "sex", "age_band_5y", "beneficiarios"])
    isa = isa[isa.sex != "TOTAL"]
    D["isa_age"] = isa.groupby(["year", "sex", "age_band_5y"], dropna=False, as_index=False).beneficiarios.sum()
    D["pop_rates"] = C.read_tidy("models_population_rates")
    D["grd_res"] = grd_residence_comuna_year(refresh_grd, ctl)
    # controles: *_controls.csv de los módulos de fase 1 y 2 (excepto este módulo)
    ctrl = []
    for f in sorted(CONTROLS_DIR.glob("*_controls.csv")):
        mod = f.name.replace("_controls.csv", "")
        if mod not in REPRODUCTION_MODULES:
            continue
        d = pd.read_csv(f, dtype={"expected": str, "observed": str, "key": str})
        if "module" in d.columns:
            d = d.rename(columns={"module": "module_source"})
        d.insert(0, "module", mod)
        ctrl.append(d)
    D["ctrl"] = pd.concat(ctrl, ignore_index=True)
    log(f"tablas cargadas; controles de fase 1: {len(D['ctrl'])} filas de {D['ctrl'].module.nunique()} módulos")
    return D


# ---------------------------------------------------------------------------
# Derivadas compartidas
# ---------------------------------------------------------------------------
def ine_national(D: dict) -> pd.Series:
    i = D["ine"]
    s = i[(i.level == "national") & (i.sex == "TOTAL") & (i.age_group == "TOTAL")].set_index("year").population
    return s.astype(float)


def ine_national_age(D: dict, ages: list[str]) -> pd.Series:
    i = D["ine"]
    s = i[(i.level == "national") & (i.sex == "TOTAL") & (i.age_group.isin(ages))].groupby("year").population.sum()
    return s.astype(float)


def ine_region_year(D: dict) -> pd.DataFrame:
    i = D["ine"]
    r = i[(i.level == "region") & (i.sex == "TOTAL") & (i.age_group == "TOTAL")]
    return r.pivot(index="cut_region", columns="year", values="population").astype(float)


def rate_ci(count, den, per=100_000):
    if den is None or not np.isfinite(den) or den <= 0 or pd.isna(count):
        return np.nan, np.nan, np.nan
    return C.rate_per(int(round(count)), float(den), per)


@timed("derive")
def derive(D: dict, ctl: Controls) -> dict:
    X = {}
    pop = ine_national(D)
    X["pop"] = pop
    X["pop_5_19"] = ine_national_age(D, ["5-9", "10-14", "15-19"])
    # --- F4 E / tabla: series por 100.000 habitantes ---
    grd = D["grd"]
    rem = D["rem"]
    edu = D["edu"].set_index("year")
    a05 = rem[(rem.module == "A05") & (rem.code == "05990022") & (rem.variant == "strict_autism") & (rem.measure == "annual_sum")].set_index("year")
    p2 = rem[(rem.module == "P2") & (rem.code == "P2500500") & (rem.measure == "december_stock")].set_index("year")
    X["a05"], X["p2"] = a05, p2
    rows = []
    for v in VARIANTS:
        g = grd[(grd.variant == v) & (grd.panel == "observed") & (grd.activity == "all") & (grd.position == "any")].set_index("year")
        for y in g.index:
            r, lo, hi = rate_ci(g.loc[y, "n_episodes_f84"], pop.get(y))
            rows.append(dict(variant=v, series="grd_episodes_f84_any", stock_or_flow="flow", year=y, value=g.loc[y, "n_episodes_f84"], reporting_n=g.loc[y, "hospitals_n"],
                             denominator=pop.get(y), rate=r, rate_lo=lo, rate_hi=hi))
            r, lo, hi = rate_ci(g.loc[y, "persons_within_year"], pop.get(y))
            rows.append(dict(variant=v, series="grd_persons_within_year_f84_any", stock_or_flow="flow", year=y, value=g.loc[y, "persons_within_year"], reporting_n=g.loc[y, "hospitals_n"],
                             denominator=pop.get(y), rate=r, rate_lo=lo, rate_hi=hi))
    for y in a05.index:
        r, lo, hi = rate_ci(a05.loc[y, "total"], pop.get(y))
        rows.append(dict(variant="both", series="a05_autism_entries", stock_or_flow="flow", year=y, value=a05.loc[y, "total"], reporting_n=a05.loc[y, "n_reporting_establishments"],
                         denominator=pop.get(y), rate=r, rate_lo=lo, rate_hi=hi))
    for y in p2.index:
        r, lo, hi = rate_ci(p2.loc[y, "total"], pop.get(y))
        rows.append(dict(variant="both", series="p2_asd_december_stock", stock_or_flow="stock", year=y, value=p2.loc[y, "total"], reporting_n=p2.loc[y, "n_reporting_establishments"],
                         denominator=pop.get(y), rate=r, rate_lo=lo, rate_hi=hi))
    for y in edu.index:
        val = edu.loc[y, "pie_harmonised_n"]
        if pd.isna(val):
            continue
        r, lo, hi = rate_ci(val, pop.get(y))
        r5, lo5, hi5 = rate_ci(val, X["pop_5_19"].get(y))
        rows.append(dict(variant="both", series="pie_harmonised_stock", stock_or_flow="stock", year=y, value=val, reporting_n=np.nan, denominator=pop.get(y), rate=r, rate_lo=lo, rate_hi=hi,
                         rate_per_100k_aged_5_19=r5, rate_5_19_lo=lo5, rate_5_19_hi=hi5))
    X["per_pop"] = pd.DataFrame(rows)
    # control: tasa bruta GRD por población frente a models_population_rates (TOTAL, any)
    pr = D["pop_rates"]
    for v in VARIANTS:
        m = pr[(pr.variant == v) & (pr.position == "any") & (pr.sex == "TOTAL")].set_index("year")
        z = X["per_pop"][(X["per_pop"].variant == v) & (X["per_pop"].series == "grd_episodes_f84_any")].set_index("year")
        for y in m.index:
            ctl.add("grd_crude_rate_per_pop_vs_06_models", f"{v}|{y}", round(float(m.loc[y, "crude"]), 6), round(float(z.loc[y, "rate"]), 6), "tasa bruta por 100.000 INE reproducida en 08c frente a models_population_rates", tol=1e-6)
    # --- S9: regional ---
    res = D["grd_res"]
    known = res[res.match_method != "unmatched"]
    unk = res[res.match_method == "unmatched"]
    popr = ine_region_year(D)
    reg_rows = []
    for v in VARIANTS:
        col = f"n_f84_any_{v}"
        byr = known.groupby(["year", "cut_region"])[col].sum().reset_index()
        for r in byr.itertuples():
            rr, lo, hi = rate_ci(getattr(r, col), popr.loc[int(r.cut_region), r.year] if int(r.cut_region) in popr.index else np.nan)
            reg_rows.append(dict(source="grd_f84_any_residence", variant=v, year=int(r.year), cut_region=int(r.cut_region), count=float(getattr(r, col)), reporting_n=np.nan,
                                 population=popr.loc[int(r.cut_region), r.year], rate=rr, rate_lo=lo, rate_hi=hi))
        tot = res.groupby("year")[col].sum()
        g = grd[(grd.variant == v) & (grd.panel == "observed") & (grd.activity == "all") & (grd.position == "any")].set_index("year")
        for y in g.index:
            ctl.add("grd_residence_scan_f84_any_total", f"{v}|{y}", int(g.loc[y, "n_episodes_f84"]), int(tot.get(y, 0)), "suma por comuna de residencia (incl. desconocida) frente a grd_year_summary observado/toda modalidad/cualquier posición")
    tot_ep = res.groupby("year").n_episodes.sum()
    for y in CFG.YEARS_GRD:
        ctl.add("grd_residence_scan_episodes_total", str(y), CFG.CONTROLS["grd_records_total"][y], int(tot_ep.get(y, 0)), "episodios totales leídos en la lectura por residencia")
    X["grd_unknown_res"] = {v: unk.groupby("year")[f"n_f84_any_{v}"].sum().to_dict() for v in VARIANTS}
    X["grd_unknown_res_values"] = sorted(unk.comuna_norm.unique())
    re_ = D["remest"]
    a = re_[(re_.module == "A05") & (re_.code == "05990022")]
    byr = a.groupby(["year", "IdRegion"]).agg(count=("annual_total", "sum"), n_estab=("IdEstablecimiento", "nunique")).reset_index()
    for r in byr.itertuples():
        reg = int(r.IdRegion)
        rr, lo, hi = rate_ci(r.count, popr.loc[reg, r.year] if reg in popr.index else np.nan)
        reg_rows.append(dict(source="a05_autism_entries_establishment", variant="both", year=int(r.year), cut_region=reg, count=float(r.count), reporting_n=int(r.n_estab),
                             population=popr.loc[reg, r.year], rate=rr, rate_lo=lo, rate_hi=hi))
    for y in a05.index:
        ctl.add("a05_autism_region_sum_vs_national", str(y), float(a05.loc[y, "total"]), float(byr[byr.year == y]["count"].sum()), "suma regional de rem_establishment_year (05990022) frente a rem_pathway_annual")
        ctl.add("a05_autism_region_establishments_vs_national", str(y), int(a05.loc[y, "n_reporting_establishments"]), int(a[a.year == y].IdEstablecimiento.nunique()), "establecimientos distintos con fila")
    X["regional"] = pd.DataFrame(reg_rows)
    # --- S10: denominadores ---
    s = D["ine_sens"]
    nat = s[(s.level == "national") & (s.sex == "TOTAL")]
    X["sens_nat_age"] = nat
    reg = s[(s.level == "region") & (s.sex == "TOTAL") & (s.age_group == "TOTAL")]
    X["sens_reg"] = reg
    return X


# ---------------------------------------------------------------------------
# Ayudas gráficas
# ---------------------------------------------------------------------------
_POS = {"top": (0.97, "top"), "mid": (0.55, "center"), "bottom": (0.03, "bottom")}


def context(ax, lang, law=True, pandemic="top", law_pos="top", shade=DISRUPTION, fs=7.5, law_text=True):
    """Sombreado 2020–21 y línea de la Ley 21.545. En las láminas verticales ambos se rotulan una sola vez por lámina."""
    C.shade_years(ax, shade)
    if pandemic:
        y, va = _POS[pandemic]
        t = ax.text(np.mean(shade), y, tr("pandemic", lang), transform=ax.get_xaxis_transform(), ha="center", va=va, fontsize=fs, color="#555555", linespacing=1.15)
        t.set_gid(C.PLATE_KEEP)     # posición deliberada: sobre SU banda sombreada
    if law:
        x = LAW_YEAR - 0.35
        ax.axvline(x, color="#444444", ls=":", lw=1.2, zorder=1)
        if law_text:
            y, va = _POS[law_pos]
            t = ax.text(x + 0.06, y, tr("law", lang), transform=ax.get_xaxis_transform(), ha="left", va=va, fontsize=fs, color="#444444", linespacing=1.15)
            t.set_gid(C.PLATE_KEEP)  # posición deliberada: junto a SU línea de contexto


def load_regions_equal_area():
    """Regiones continentales (islas oceánicas recortadas) en proyección cónica de igual área (Albers) para Chile."""
    import geopandas as gpd
    from shapely.geometry import box
    shp = gpd.read_file(CFG.PATHS["repo_shapes_regiones"])
    shp = shp.loc[shp.codregion.astype(int) > 0, ["codregion", "Region", "geometry"]].rename(columns={"codregion": "cut_region"})
    shp["cut_region"] = shp.cut_region.astype(int)
    shp = shp.to_crs(4326)
    try:
        shp["geometry"] = shp.geometry.make_valid()
    except AttributeError:
        shp["geometry"] = shp.geometry.buffer(0)
    bbox = box(-76.5, -56.6, -66.0, -17.3)
    shp["geometry"] = shp.geometry.intersection(bbox)
    shp = shp[~shp.geometry.is_empty].copy()
    shp = shp.to_crs("+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 +datum=WGS84 +units=m +no_defs")
    shp["geometry"] = shp.geometry.simplify(800)
    return shp


BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]


# ---------------------------------------------------------------------------
# Rótulos de una nube de puntos: colocación MEDIDA y línea guía hasta su punto
# ---------------------------------------------------------------------------
#: Línea guía que une cada rótulo con SU marcador (gris medio, 0,45 pt, por DEBAJO de los marcadores).
LEADER_COLOR, LEADER_LW, LEADER_ZORDER = "#8a8a8a", 0.45, 2.2
#: Direcciones y distancias candidatas del rótulo respecto del BORDE de su marcador (en puntos).
LABEL_DIRS = 24
LABEL_DISTS_PT = (2.0, 3.5, 5.5, 8.0, 11.5, 16.0, 22.0, 30.0, 40.0, 52.0)
#: Muestreo del disco del marcador con puntos de igual área (anillos en sqrt((k+½)/n)): sirve para medir
#: qué FRACCIÓN de un marcador queda bajo una caja de texto, que es la medida del verificador.
_DISC_SAMPLES = np.array([(np.sqrt((k + 0.5) / 4.0) * np.cos(2.0 * np.pi * (j + 0.5 * (k % 2)) / 16.0),
                           np.sqrt((k + 0.5) / 4.0) * np.sin(2.0 * np.pi * (j + 0.5 * (k % 2)) / 16.0))
                          for k in range(4) for j in range(16)], dtype=float)
#: Fracción de un marcador que un rótulo puede tapar. Cero de verdad: en la S9 (d) el recuadro blanco de un
#: rótulo vecino BORRABA cuatro marcadores enteros, y medio marcador tapado ya no se lee como un dato.
LABEL_COVER_MAX = 0.01


def point_label(ax, x, y, text, *, fontsize: float = FS_MIN, color: str = "#222222"):
    """Rótulo de un punto de nube. La colocación la decide `place_point_labels` al guardar.

    El rótulo lleva recuadro PROPIO: el motor de composición pinta un recuadro blanco detrás de todo texto
    con tinta debajo, y ese recuadro —el de un rótulo VECINO— era el que borraba cuatro de los dieciséis
    marcadores de la Figura S9 (d). Con el suyo ya puesto el motor no lo toca, y la colocación de abajo
    puede medir la caja definitiva, recuadro incluido.
    """
    ann = ax.annotate(str(text), xy=(float(x), float(y)), xycoords="data", textcoords="offset points",
                      xytext=(0.0, 5.0), fontsize=fontsize, color=color, ha="center", va="center", zorder=7,
                      bbox=dict(boxstyle="square,pad=0.18", facecolor="white", edgecolor="none", alpha=0.88))
    ann.set_gid(C.PLATE_KEEP)
    return ann


def _win_box(artist, r):
    """Caja de pantalla de un artista, o None si no se puede medir."""
    try:
        b = artist.get_window_extent(r)
    except (AttributeError, ValueError, RuntimeError, TypeError):
        return None
    if not np.isfinite([b.x0, b.y0, b.x1, b.y1]).all() or b.width <= 0 or b.height <= 0:
        return None
    return np.array([b.x0, b.y0, b.x1, b.y1], dtype=float)


def _cover_fracs(box, pts, rad: float):
    """Fracción del disco de cada marcador cubierta por `box` (0 fuera, 1 tapado entero)."""
    p = pts[:, None, :] + _DISC_SAMPLES[None, :, :] * rad
    inside = ((p[:, :, 0] >= box[0]) & (p[:, :, 0] <= box[2])
              & (p[:, :, 1] >= box[1]) & (p[:, :, 1] <= box[3]))
    return inside.mean(axis=1)


def _inter_area(a, b) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _touches(a, b, tol_px: float) -> bool:
    """¿Se solapan dos cajas por MÁS que el roce? Misma tolerancia que el verificador (0,5 pt de lado)."""
    return (min(a[2], b[2]) - max(a[0], b[0]) > tol_px) and (min(a[3], b[3]) - max(a[1], b[1]) > tol_px)


def place_point_labels(ax, anns, *, marker_radius_pt: float = 2.6, gap_pt: float = 1.1,
                       rounds: int = 5, leader_min_pt: float = 3.0) -> list:
    """Coloca los rótulos de una nube de modo que NINGÚN marcador quede tapado y une cada uno con el suyo.

    El defecto que resuelve es el de la Figura S9 (d): con dieciséis regiones en una celda de 90 × 80 mm, el
    colocador anterior escogía la posición de cada rótulo mirando solo los marcadores del momento, una pasada
    posterior los separaba en vertical SIN volver a mirar los marcadores, y el motor les pintaba detrás un
    recuadro blanco. Resultado: Antofagasta bajo «Tarapacá», Tarapacá bajo «Magallanes», Coquimbo bajo
    «Araucanía» y Los Lagos bajo su propio rótulo —cuatro puntos borrados y ningún hilo que los recupere—.

    Aquí se mide la lámina YA CONGELADA y se resuelve de una vez: cada rótulo se prueba en 24 direcciones ×
    10 distancias alrededor del borde de su marcador; el coste castiga (i) tapar CUALQUIER marcador, el
    propio o el del vecino, (ii) pisar otro rótulo ya colocado, (iii) salirse del panel, (iv) caer sobre la
    nota del panel y (v) alejarse del punto. Se recorre en orden fijo —los puntos más apretados primero— y se
    repite hasta que nadie se mueve, de modo que el resultado es determinista. Cuando el rótulo no queda
    pegado a su marcador se dibuja una línea guía que va del borde del marcador al borde del recuadro, por
    debajo de los marcadores, para que cada nombre se lea unido a SU punto.

    La posición final se guarda en coordenadas de EJE (`axes fraction`), no en desplazamiento de puntos: si
    el motor todavía reajustase el rectángulo del panel, rótulo y punto se moverían juntos.

    Devuelve las líneas guía dibujadas. Levanta `RuntimeError` si al terminar algún marcador queda tapado,
    dos rótulos se pisan o un rótulo cae sobre la nota del panel: el verificador de composición exime a los
    artistas con `PLATE_KEEP` —y estos lo llevan, porque su sitio lo fija esta rutina—, así que la garantía
    tiene que darla el módulo.
    """
    fig = ax.figure
    anns = [a for a in anns if a is not None]
    if not anns:
        return []
    s = fig.dpi / 72.0
    rad, gap = marker_radius_pt * s, gap_pt * s
    for a in anns:
        a.set_anncoords("offset points")
        a.xyann = (0.0, 0.0)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    pts = np.asarray(ax.transData.transform([a.xy for a in anns]), dtype=float)
    sizes, deltas = [], []
    for a, p in zip(anns, pts):
        b = _win_box(a, r)
        if b is None:
            raise RuntimeError(f"place_point_labels: no se puede medir el rótulo «{a.get_text()}»")
        sizes.append((b[2] - b[0], b[3] - b[1]))
        deltas.append((0.5 * (b[0] + b[2]) - p[0], 0.5 * (b[1] + b[3]) - p[1]))
    sizes, deltas = np.asarray(sizes, dtype=float), np.asarray(deltas, dtype=float)
    axb = _win_box(ax, r)
    bound = axb + np.array([1.0, 1.0, -1.0, -1.0]) if axb is not None else None
    # Obstáculos fijos del panel: la nota (el aviso de lugar de atención frente a residencia) y la leyenda.
    own = {id(a) for a in anns}
    obstacles = []
    for t in ax.texts:
        if id(t) in own or not t.get_visible() or not str(t.get_text()).strip():
            continue
        b = _win_box(t, r)
        if b is not None:
            obstacles.append(b)
    lg = ax.get_legend()
    if lg is not None and lg.get_visible():
        b = _win_box(lg, r)
        if b is not None:
            obstacles.append(b)

    ang = 2.0 * np.pi * np.arange(LABEL_DIRS) / LABEL_DIRS
    dirs = np.stack([np.cos(ang), np.sin(ang)], axis=1)
    cand, static = [], []
    for i, (p, (w, h)) in enumerate(zip(pts, sizes)):
        rows, cost = [], []
        area = max(1.0, w * h)
        for u in dirs:
            tx = (w / 2.0) / abs(u[0]) if abs(u[0]) > 1e-9 else np.inf
            ty = (h / 2.0) / abs(u[1]) if abs(u[1]) > 1e-9 else np.inf
            exit_ = min(tx, ty)                       # del centro de la caja a su borde, en esa dirección
            for dpt in LABEL_DISTS_PT:
                c = p + u * (rad + dpt * s + exit_)
                box = np.array([c[0] - w / 2.0, c[1] - h / 2.0, c[0] + w / 2.0, c[1] + h / 2.0])
                grown = box + np.array([-gap, -gap, gap, gap])
                v = 4000.0 * float(_cover_fracs(grown, pts, rad).sum())
                if bound is not None:
                    v += 1500.0 * (area - _inter_area(box, bound)) / area
                for ob in obstacles:
                    v += 900.0 * _inter_area(grown, ob) / area
                v += 0.55 * dpt
                if dpt > leader_min_pt:               # la guía tampoco debe cruzar otro marcador
                    q = np.linspace(0.0, 1.0, 32)[:, None]
                    seg = p[None, :] * (1.0 - q) + c[None, :] * q
                    near = np.linalg.norm(seg[:, None, :] - pts[None, :, :], axis=2) < rad + 1.2 * s
                    near[:, i] = False
                    v += 60.0 * float(near.any(axis=0).sum())
                rows.append((box, c, float(dpt)))
                cost.append(v)
        cand.append(rows)
        static.append(np.asarray(cost, dtype=float))

    # Orden fijo: primero el punto con más vecinos a menos de 60 pt, que es el que menos sitio tiene.
    crowd = [int(np.sum(np.linalg.norm(pts - p, axis=1) < 60.0 * s)) for p in pts]
    order = sorted(range(len(anns)), key=lambda i: (-crowd[i], i))
    chosen = [None] * len(anns)
    boxes: list = [None] * len(anns)
    for _ in range(max(1, rounds)):
        moved = False
        for i in order:
            w, h = sizes[i]
            area = max(1.0, w * h)
            best, best_c = 0, np.inf
            for j, (box, _c, _dpt) in enumerate(cand[i]):
                v = static[i][j]
                grown = box + np.array([-gap, -gap, gap, gap])
                for k, ob in enumerate(boxes):
                    if k == i or ob is None:
                        continue
                    v += 1200.0 * _inter_area(grown, ob) / area
                    if v >= best_c:
                        break
                if v < best_c - 1e-9:
                    best, best_c = j, v
            moved = moved or (chosen[i] != best)
            chosen[i], boxes[i] = best, cand[i][best][0]
        if not moved:
            break

    inv = ax.transAxes.inverted()
    leaders = []
    for i, a in enumerate(anns):
        box, c, dpt = cand[i][chosen[i]]
        fx, fy = inv.transform(c - deltas[i])
        a.set_anncoords("axes fraction")
        a.xyann = (float(fx), float(fy))
        if dpt <= leader_min_pt:
            continue                                   # pegado a su punto: la guía sobraría
        v = c - pts[i]
        length = float(np.hypot(v[0], v[1]))
        if length <= 1e-6:
            continue
        u = v / length
        w, h = sizes[i]
        tx = (w / 2.0) / abs(u[0]) if abs(u[0]) > 1e-9 else np.inf
        ty = (h / 2.0) / abs(u[1]) if abs(u[1]) > 1e-9 else np.inf
        start = pts[i] + u * (rad + 0.9 * s)
        end = c - u * (min(tx, ty) + 0.7 * s)
        if float(np.hypot(*(end - start))) < 1.2 * s:
            continue
        (x0, y0), (x1, y1) = inv.transform(np.vstack([start, end]))
        ln, = ax.plot([x0, x1], [y0, y1], transform=ax.transAxes, color=LEADER_COLOR, lw=LEADER_LW,
                      solid_capstyle="butt", zorder=LEADER_ZORDER, clip_on=True, label="_nolegend_")
        ln.set_in_layout(False)
        leaders.append(ln)

    # Comprobación sobre el dibujo REAL. Estos rótulos llevan el gid `PLATE_KEEP` —su sitio lo decide esta
    # rutina y nadie más debe moverlos—, y el verificador de composición exime a los `PLATE_KEEP`: la
    # garantía de que ninguno tapa un marcador ni pisa a otro rótulo tiene que darla el módulo, aquí.
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    final = [_win_box(a, r) for a in anns]
    bad = []
    for i, a in enumerate(anns):
        if final[i] is None:
            continue
        cov = _cover_fracs(final[i], pts, rad)
        for j in np.flatnonzero(cov > LABEL_COVER_MAX):
            bad.append(f"«{a.get_text()}» tapa el {100.0 * cov[j]:.0f} % de un marcador")
        for k in range(i + 1, len(anns)):
            if final[k] is None:
                continue
            if _touches(final[i], final[k], 0.5 * s):
                bad.append(f"«{a.get_text()}» se imprime sobre «{anns[k].get_text()}»")
        for ob in obstacles:
            if _touches(final[i], ob, 0.5 * s):
                bad.append(f"«{a.get_text()}» se imprime sobre una nota o leyenda del panel")
    if bad:
        raise RuntimeError("place_point_labels: " + "; ".join(bad))
    gaps = [cand[i][chosen[i]][2] for i in range(len(anns))]
    log(f"nube: {len(anns)} rótulos colocados, {len(leaders)} con línea guía, "
        f"separación del marcador {min(gaps):.1f}–{max(gaps):.1f} pt; "
        f"ningún marcador tapado, ningún rótulo sobre otro")
    return leaders


def chile_map(fig, slot, shapes, values: pd.Series, lang, title, cmap="YlGnBu", vmin=None, vmax=None, letter_=None, cbar_label=""):
    """Tres franjas (norte, centro, sur) con la misma escala métrica; escala de color común y barra horizontal.

    La celda de la lámina vertical mide 90 × 80 mm: la franja se dibuja con relación de aspecto fija, así que el
    título NO puede colgar de los ejes del mapa (al reservarle sitio, el motor de composición encoge los ejes y,
    con el aspecto fijo, los colapsa). Va en una fila propia de la subrejilla, sobre unos ejes invisibles de alto
    casi nulo, y desde ahí `C.plate_align_titles` lo ancla al borde izquierdo de la celda.
    """
    from matplotlib.colors import Normalize
    from matplotlib import cm
    sub = slot.subgridspec(3, 3, height_ratios=[0.001, 1, 0.05], wspace=0.04, hspace=0.05)
    tax = fig.add_subplot(sub[0, :])
    tax.set_axis_off()
    if letter_:
        panel_head(tax, letter_, title)
    else:
        tax.set_title(title, fontsize=FS_TITLE, fontweight="bold", loc="left")
    vals = values.reindex(shapes.cut_region).to_numpy(dtype=float)
    finite = vals[np.isfinite(vals)]
    vmin = float(np.nanmin(finite)) if vmin is None else vmin
    vmax = float(np.nanmax(finite)) if vmax is None else vmax
    norm = Normalize(vmin=vmin, vmax=vmax)
    mapper = cm.ScalarMappable(norm=norm, cmap=cmap)
    bounds = [shapes[shapes.cut_region.isin(band)].total_bounds for band in BANDS]
    span = max(b[3] - b[1] for b in bounds) * 1.04
    # ventana en x COMÚN a las tres franjas: la escala métrica tiene que ser la misma y ningún rótulo de
    # región puede quedar fuera de su eje (el texto no se recorta solo)
    width = max(span * 0.36, max(b[2] - b[0] for b in bounds) * 1.30)
    axes = []
    for k, band in enumerate(BANDS):
        ax = fig.add_subplot(sub[1, k])
        g = shapes[shapes.cut_region.isin(band)].copy()
        cols = [mapper.to_rgba(v) if np.isfinite(v) else "#f2f2f2" for v in values.reindex(g.cut_region).to_numpy(dtype=float)]
        g.plot(color=cols, edgecolor="#555555", linewidth=0.3, ax=ax)
        b = g.total_bounds
        cy = (b[1] + b[3]) / 2
        ax.set_ylim(cy - span / 2, cy + span / 2)
        cx = (b[0] + b[2]) / 2
        ax.set_xlim(cx - width / 2, cx + width / 2)
        ax.set_aspect("equal")
        ax.set_axis_off()
        # El nombre de cada región va PEGADO a su polígono y no puede moverse: movido, deja de nombrar a la
        # región que nombra. Se marca inamovible; el reparto vertical se hace aquí, a mano.
        for r in g.itertuples():
            q = r.geometry.representative_point()
            t = ax.text(q.x, q.y, REGION_NAMES_SHORT.get(r.cut_region, str(r.cut_region)), fontsize=FS_MIN, ha="center", va="center",
                        color="#222222", clip_on=True,
                        bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.70))
            t.set_gid(C.PLATE_KEEP)
        axes.append(ax)
    cax = fig.add_subplot(sub[2, :])
    cb = fig.colorbar(mapper, cax=cax, orientation="horizontal")
    cb.set_label(cbar_label or tr("s9_rate", lang), fontsize=FS_MIN + 0.5)
    cb.ax.tick_params(labelsize=FS_MIN + 0.2)
    return axes


def heatmap(ax, mat: pd.DataFrame, lang, fmt_cell, cmap="YlGnBu", fontsize=6.5, extra: pd.DataFrame | None = None):
    data = mat.to_numpy(dtype=float)
    im = ax.imshow(data, cmap=cmap, aspect="auto")
    ax.set_xticks(range(mat.shape[1])); ax.set_xticklabels([str(c) for c in mat.columns], fontsize=FS_MIN + 0.5)
    # Los nombres de región se abrevian por el glosario de la norma («Arica y Parinacota» → «Arica y P.»).
    # No es sólo el ancho del rótulo: la columna de nombres se comía la mitad de la celda y dejaba al mapa
    # de calor 80 pt para seis años, con lo que las marcas del eje X se imprimían sin ningún blanco entre
    # ellas y «201920202021202220232024» se leía como un solo número. El nombre completo vuelve siempre en
    # la tabla acompañante: la lámina abrevia, no oculta.
    ax.set_yticks(range(mat.shape[0]))
    ax.set_yticklabels([C.PLATE_LABEL_GLOSSARY.get(REGION_NAMES.get(i, str(i)), REGION_NAMES.get(i, str(i)))
                        for i in mat.index], fontsize=FS_MIN + 0.2)
    ax.grid(False)
    vmax = np.nanmax(data) if np.isfinite(data).any() else 1
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = data[i, j]
            if not np.isfinite(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=fontsize, color="#777777")
                continue
            txt = fmt_cell(v)
            if extra is not None:
                e = extra.iloc[i, j]
                if pd.notna(e):
                    txt += f"\n(n={int(e)})"
            ax.text(j, i, txt, ha="center", va="center", fontsize=fontsize, color="white" if v > 0.6 * vmax else "#222222")
    return im


# ---------------------------------------------------------------------------
# F4 — triangulación y benchmarks
# ---------------------------------------------------------------------------
@timed("fig4")
def fig4(D, X, variant, lang) -> dict:
    """Lámina vertical de 180 × 245 mm: seis paneles (a–f) en tres filas por dos columnas."""
    plt, sns = plate_style()
    from matplotlib.lines import Line2D
    fdir = out_dir(variant, lang, "figures")
    fig, gs = new_plate(plt)
    edu = D["edu"].set_index("year")
    yrs_short = [f"\u2019{y % 100:02d}" for y in range(2019, 2026)]

    # a — PIE: estudiantes autistas
    a = fig.add_subplot(gs[0, 0])
    yrs = edu.index.to_numpy()
    a.plot(yrs, edu.pie_tea_strict_n, "s--", color=OK[0], lw=1.1, ms=3.2, label=tr("pie_strict", lang))
    a.plot(yrs, edu.pie_tea_asperger_n, "^--", color=OK[1], lw=1.1, ms=3.2, label=tr("pie_asperger", lang))
    h = edu.pie_harmonised_n
    y_ap = [y for y in yrs if y <= 2023]; y_si = [y for y in yrs if y >= 2023]
    a.plot(y_ap, h.loc[y_ap], "o-", color=OK[5], lw=1.6, ms=3.8, label=tr("pie_harm", lang))
    a.plot(y_si, h.loc[y_si], "D--", color=OK[5], lw=1.3, ms=3.2, mfc="white")
    a.plot(yrs, edu.pie_harmonised_sinaces_n, "x", color="#333333", ms=4, mew=1.0, label=tr("pie_harm_sinaces", lang))
    a.plot(yrs, edu.special_schools_autism_n, "v-", color=OK[3], lw=1.0, ms=3.0, label=tr("pie_special", lang))
    _hy = [y for y in yrs if pd.notna(h.get(y))]
    a.axvline(2023.5, color="#888888", ls="-.", lw=0.9)
    # La nota del cambio de fuente iba pegada al eje X, encima de la serie PIE TEA-Asperger; sube a la banda
    # alta del panel, a la derecha del quiebre, donde no hay ninguna serie.
    a.text(2023.55, 0.62, tr("pie_source_change", lang), transform=a.get_xaxis_transform(), fontsize=FS_MIN,
           color="#666666", va="bottom").set_gid(C.PLATE_KEEP)
    context(a, lang, pandemic="mid", law_pos="mid", fs=FS_MIN)
    a.set_xticks(yrs); a.set_xticklabels([f"\u2019{int(y) % 100:02d}" for y in yrs], fontsize=FS_MIN + 0.5)
    a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("students", lang), fontsize=FS_MIN + 1)
    a.set_ylim(0, float(h.max()) * 2.3)
    # Los rótulos de valor se colocan con los límites YA fijados y midiendo cada rótulo ya dibujado: el
    # colocador por rectángulo estimado dejaba «106.786» impreso sobre «86.475».
    for _y in _hy:
        C.plate_value_label(a, float(_y), float(h[_y]), num(h[_y], 0, lang), fontsize=FS_MIN, color=OK[5],
                            step_pt=2.4, max_steps=5)
    plate_legend(a, loc="upper left", handlelength=1.4)
    panel_head(a, "a", tr("f4a_title", lang), dx=-0.17)

    # b — JUNAEB
    b = fig.add_subplot(gs[0, 1])
    jun = D["jun"]
    levels = ["parvularia", "basico1", "basico5", "medio1"]
    offs = {"parvularia": -0.24, "basico1": -0.08, "basico5": 0.08, "medio1": 0.24}
    lcol = {lv: OK[i] for i, lv in enumerate(levels)}
    ymax = float(jun.hi_pct.max()) if jun.hi_pct.notna().any() else 10
    strip_y = -0.13 * ymax
    _b_labels: list = []
    for lv in levels:
        dd = jun[(jun.level == lv) & (jun.sex == "all")].sort_values("year")
        w = dd[dd.estimable == "yes"]
        b.errorbar(w.year + offs[lv], w.proportion_weighted_pct, yerr=[w.proportion_weighted_pct - w.lo_pct, w.hi_pct - w.proportion_weighted_pct],
                   fmt="o-", color=lcol[lv], lw=1.2, ms=3.4, capsize=1.4, elinewidth=0.6, label=tr(f"jun_{lv}", lang))
        u = dd[dd.estimable == "unweighted_only"]
        b.errorbar(u.year + offs[lv], u.proportion_unweighted_pct, yerr=[u.proportion_unweighted_pct - u.lo_unweighted_pct, u.hi_unweighted_pct - u.proportion_unweighted_pct],
                   fmt="o", color=lcol[lv], mfc="white", ms=3.4, capsize=1.4, lw=0.9, elinewidth=0.6)
        ne = dd[dd.estimable == "no"]
        b.scatter(ne.year + offs[lv], np.full(len(ne), strip_y), marker="s", s=13, facecolor="white", edgecolor=lcol[lv], hatch="///", linewidth=0.6, zorder=3)
        _b_labels.append((np.asarray(w.year + offs[lv], dtype=float),
                          np.asarray(w.proportion_weighted_pct, dtype=float),
                          np.asarray(w.lo_pct, dtype=float), np.asarray(w.hi_pct, dtype=float),
                          [num(v, 1, lang) for v in w.proportion_weighted_pct], lcol[lv]))
    b.axhline(0, color="#333333", lw=0.8)
    b.axhspan(strip_y * 1.9, strip_y * 0.25, color="#eeeeee", zorder=0)
    context(b, lang, pandemic=None, law_text=False, fs=FS_MIN)
    # La leyenda de seis entradas se llevaba el 45 % superior del panel y obligaba a un eje hasta 14 cuando
    # el máximo del dato es 8,3: las siete series quedaban aplastadas en el tercio inferior. La franja
    # 2019–2022 no tiene ningún punto ponderado, de modo que la leyenda cabe sobre ella —el motor de
    # colocación la lleva al hueco medido— y el eje sólo necesita el aire de los rótulos de valor.
    # El último marcador de cada serie cae junto al borde derecho: sin ese margen, el rótulo «5,0» no tenía
    # a dónde apartarse y volvía sobre su propio punto.
    b.set_ylim(strip_y * 1.9, ymax * 1.22); b.set_xticks(range(2019, 2026)); b.set_xlim(2018.4, 2025.95)
    b.set_xticklabels(yrs_short, fontsize=FS_MIN + 0.5)
    yt = [t for t in b.get_yticks() if 0 <= t <= ymax * 1.20]
    ydec = 0 if all(abs(t - round(t)) < 1e-9 for t in yt) else 1
    b.set_yticks(list(yt) + [strip_y]); b.set_yticklabels([num(t, ydec, lang) for t in yt] + [tr("jun_strip", lang)])
    b.get_yticklabels()[-1].set_fontsize(FS_MIN); b.get_yticklabels()[-1].set_color("#555555")
    b.set_xlabel(tr("year", lang)); b.set_ylabel(tr("f4b_axis", lang), fontsize=FS_MIN + 1)
    # Los rótulos de porcentaje se colocan con los límites YA fijados, midiendo cada rótulo ya dibujado y
    # esquivando la barra de error de su propio dato: el colocador anterior dejaba «8,3» bajo el recuadro de
    # «5,7» (se leía «8 3») y «7,7» junto al marcador de otra serie.
    for _bx, _by, _blo, _bhi, _blab, _bcol in _b_labels:
        for _x, _y, _lo, _hi, _t in zip(_bx, _by, _blo, _bhi, _blab):
            C.plate_value_label(b, float(_x), float(_y), _t, err=(float(_lo), float(_hi)),
                                fontsize=FS_MIN, color=_bcol, step_pt=2.6, max_steps=8)
    handles, labels = b.get_legend_handles_labels()
    handles += [Line2D([0], [0], marker="o", color="#555555", mfc="white", lw=0, ms=3.4, label=tr("jun_unweighted", lang)),
                Line2D([0], [0], marker="s", color="#555555", mfc="white", lw=0, ms=3.8, label=tr("jun_ne", lang))]
    lg_b = plate_legend(b, handles=handles, loc="upper left", handlelength=1.3, ncol=1)
    C.plate_place_legend(b, lg_b, outside_below=False, prefer=("upper left", "center left", "upper center"))
    panel_head(b, "b", tr("f4b_title", lang), dx=-0.30)

    # c — encuestas (forest)
    c = fig.add_subplot(gs[1, 0])
    sv = D["surv"]
    groups = [("svy_endide_adults", (sv.survey.str.startswith("ENDIDE")) & (sv.module.str.startswith("Adultos")) & (sv.estimate_type == "primary"), OK[0]),
              ("svy_endide_children", (sv.survey.str.startswith("ENDIDE")) & (sv.domain.str.contains("NNA 2-17: autismo reportado$", regex=True)) & (sv.estimate_type == "primary"), OK[2]),
              ("svy_endide_confirmed", (sv.survey.str.startswith("ENDIDE")) & (sv.domain.str.contains("NNA 2-17: autismo reportado y confirmado")) & (sv.estimate_type == "primary"), OK[3]),
              ("svy_encavi", (sv.survey.str.startswith("ENCAVI")) & (sv.estimate_type == "primary") & (sv.domain.str.contains("diagnóstico")), OK[1])]
    rows = []
    for key, mask, col in groups:
        g = sv[mask & sv.subgroup_type.isin(["total", "sex"])]
        if g.empty:
            log(f"aviso: grupo de encuesta sin filas: {key}")
        rows.append(("header", tr(key, lang), None, col))
        for sub_ in ["total", "Hombre", "Mujer"]:
            r = g[g.subgroup == sub_]
            if r.empty:
                continue
            r = r.iloc[0]
            grey = (r.precision_flag == "imprecise") or (pd.notna(r.rse) and r.rse > 0.30)
            rows.append(("row", tr(sub_ if sub_ != "total" else "total", lang), r, "#999999" if grey else col))
    n = len(rows)
    for i, (kind, lab, r, col) in enumerate(rows):
        y = n - 1 - i
        if kind == "header":
            c.text(0.0, y, lab, fontsize=FS_MIN, fontweight="bold", color=col, va="center", ha="left", transform=c.get_yaxis_transform())
            continue
        pct, lo, hi = 100 * r.proportion, 100 * r.lo, 100 * r.hi
        c.plot([lo, hi], [y, y], color=col, lw=1.2, zorder=2)
        c.scatter(pct, y, s=11, color=col, zorder=3, edgecolor="white", linewidth=0.5)
        # El valor va en UNA línea. Con dieciséis filas en una celda de 82 mm el paso entre filas es de
        # unos 9 pt y un bloque de dos líneas mide 15: el rótulo invadía la fila vecina y no se sabía a
        # cuál pertenecía cada número. Los casos y el n del dominio pasan al rótulo de la fila.
        c.text(11.0, y, f"{num(pct, 2, lang)} ({ci_span(lo, hi, 2, lang)})",
               va="center", ha="left", fontsize=FS_MIN, color="#333333")
    c.set_xscale("log"); c.set_xlim(0.05, 420)
    c.set_xticks([0.1, 0.3, 1, 3, 10]); c.set_xticklabels([num(v, 1, lang) for v in [0.1, 0.3, 1, 3, 10]], fontsize=FS_MIN + 0.5)
    c.set_yticks([n - 1 - i for i, r in enumerate(rows) if r[0] == "row"])
    c.set_yticklabels([f"{r[1]} · {int(r[2].cases)}/{num(r[2].n, 0, lang)}" for r in rows if r[0] == "row"],
                      fontsize=FS_MIN)
    c.set_ylim(-1.6, n - 0.3)
    c.set_xlabel(f'{tr("f4c_axis", lang)}\n{tr("svy_cases_row", lang)}', fontsize=FS_MIN + 0.5)
    c.text(0.0, -1.15, tr("imprecise", lang), transform=c.get_yaxis_transform(), fontsize=FS_MIN, ha="left", va="center", color="#777777")
    panel_head(c, "c", tr("f4c_title", lang), dx=-0.16)

    # d — índices
    d = fig.add_subplot(gs[1, 1])
    cv = D["conv"]; cv = cv[(cv.variant == variant) & (cv.index_base_year == 2021)]
    a05, p2 = X["a05"], X["p2"]
    names = {"grd_any_rate": tr("idx_grd", lang), "deis_principal_rate": tr("idx_deis", lang),
             "a05_strict_entries": tr("idx_a05", lang, n=f"{num(a05.n_reporting_establishments.min(), 0, lang)}–{num(a05.n_reporting_establishments.max(), 0, lang)}"),
             "p2_december_stock": tr("idx_p2", lang, n=f"{num(p2.n_reporting_establishments.min(), 0, lang)}–{num(p2.n_reporting_establishments.max(), 0, lang)}"),
             "pie_harmonised": tr("idx_pie", lang)}
    mk = {"grd_any_rate": "o", "deis_principal_rate": "^", "a05_strict_entries": "s", "p2_december_stock": "D", "pie_harmonised": "P"}
    for i, ser in enumerate(names):
        z = cv[cv.series == ser].sort_values("year")
        post = z[z.year >= 2021]; pre = z[z.year <= 2021]
        if ser == "pie_harmonised":   # cambio de fuente Apuntes 60 → SINACES (2024–2025): trazo discontinuo, como en (a)
            d.plot(post[post.year <= 2023].year, post[post.year <= 2023]["index"], marker=mk[ser], ls="-", color=OK[i], lw=1.3, ms=3.4, label=names[ser])
            d.plot(post[post.year >= 2023].year, post[post.year >= 2023]["index"], marker=mk[ser], ls="--", color=OK[i], lw=1.1, ms=3.4, mfc="white")
        else:
            d.plot(post.year, post["index"], marker=mk[ser], ls="-", color=OK[i], lw=1.3, ms=3.4, label=names[ser])
        if len(pre) > 1:
            d.plot(pre.year, pre["index"], marker=mk[ser], ls=":", color=OK[i], lw=0.9, ms=2.6, alpha=0.6)
        d.annotate(num(post["index"].iloc[-1], 0, lang), (post.year.iloc[-1], post["index"].iloc[-1]), xytext=(3, 0),
                   textcoords="offset points", fontsize=FS_MIN, color=OK[i], va="center")
    d.set_yscale("log"); d.axhline(100, color="#999999", ls="--", lw=0.8)
    d.set_ylim(35, float(cv["index"].max()) * 9)
    context(d, lang, pandemic=None, law_text=False, fs=FS_MIN)
    d.set_xticks(range(2019, 2026)); d.set_xticklabels(yrs_short, fontsize=FS_MIN + 0.5)
    d.set_xlabel(f"{tr('year', lang)}\n{tr('idx_note', lang)}", fontsize=FS_MIN + 0.5)
    d.set_ylabel(tr("f4d_axis", lang), fontsize=FS_MIN + 1); d.margins(x=0.14)
    d.legend(loc="upper left", fontsize=FS_MIN, handlelength=1.4)
    panel_head(d, "d", tr("f4d_title", lang), dx=-0.30)

    # e — por 100.000 habitantes: cinco ejes separados, apilados como franjas (stocks y flujos nunca comparten un eje)
    sub = gs[2, 0].subgridspec(5, 1, hspace=0.16)
    pp = X["per_pop"]
    specs = [("grd_episodes_f84_any", variant, "e_grd_ep", OK[0], False), ("grd_persons_within_year_f84_any", variant, "e_grd_pe", OK[5], False),
             ("a05_autism_entries", "both", "e_a05", OK[2], False), ("p2_asd_december_stock", "both", "e_p2", OK[3], True),
             ("pie_harmonised_stock", "both", "e_pie", OK[4], True)]
    e_axes = []
    for k, (ser, var, lab, col, stock) in enumerate(specs):
        axk = fig.add_subplot(sub[k])
        z = pp[(pp.series == ser) & (pp.variant == var)].sort_values("year")
        if stock:
            axk.bar(z.year, z.rate, color="white", edgecolor=col, hatch="///", linewidth=0.8, width=0.72)
        else:
            axk.bar(z.year, z.rate, color=col, width=0.72)
        C.shade_years(axk, DISRUPTION, alpha=0.1)
        axk.set_xlim(2018.4, 2025.9)
        axk.set_ylim(0, float(z.rate.max()) * 1.55)   # banda superior libre para el rótulo de la franja
        axk.set_yticks([0, round(float(z.rate.max()), 1 if z.rate.max() < 100 else 0)])
        axk.tick_params(axis="y", labelsize=FS_MIN, length=1.6, pad=1.0)
        strip_lab = tr(lab, lang).replace("\n", " ")
        if ser in ("a05_autism_entries", "p2_asd_december_stock"):
            strip_lab += f" · n {num(z.reporting_n.min(), 0, lang)}–{num(z.reporting_n.max(), 0, lang)}"
        axk.text(0.012, 0.97, strip_lab, transform=axk.transAxes, ha="left", va="top", fontsize=FS_MIN,
                 fontweight="bold", color="#333333").set_gid(C.PLATE_KEEP)
        if k < len(specs) - 1:
            axk.set_xticks(range(2019, 2026)); axk.set_xticklabels([])
        else:
            axk.set_xticks(range(2019, 2026)); axk.set_xticklabels(yrs_short, fontsize=FS_MIN + 0.5)
            axk.set_xlabel(f"{tr('year', lang)} · {tr('f4e_axis_full', lang)}", fontsize=FS_MIN + 0.5)
        e_axes.append(axk)
    # el rótulo de cada franja ya dice flujo o stock; la nota de denominadores y numeradores va en el pie
    panel_head(e_axes[0], "e", tr("f4e_title", lang), dx=-0.06)

    # f — GRD frente a DEIS (principal frente a principal)
    f = fig.add_subplot(gs[2, 1])
    dv = D["dvg"]; dv = dv[dv.variant == variant].sort_values("year")
    f.errorbar(dv.year - 0.1, dv.deis_rate_f84_principal_per_100k_discharges,
               yerr=[dv.deis_rate_f84_principal_per_100k_discharges - dv.deis_rate_lo95, dv.deis_rate_hi95 - dv.deis_rate_f84_principal_per_100k_discharges],
               fmt="^-", color=OK[2], lw=1.2, ms=3.4, capsize=1.4, elinewidth=0.6, label=tr("deis_all", lang))
    de = D["dest"]; de = de[(de.variant == variant) & (de.dimension == "pertenencia_snss") & (de.category == "SNSS")].sort_values("year")
    f.errorbar(de.year + 0.1, de.rate_per_100k_discharges, yerr=[de.rate_per_100k_discharges - de.rate_lo95, de.rate_hi95 - de.rate_per_100k_discharges],
               fmt="v--", color=OK[6], lw=1.1, ms=3.4, capsize=1.4, elinewidth=0.6, label=tr("deis_snss", lang))
    g = D["grd"]; g0 = g[(g.variant == variant) & (g.panel == "observed") & (g.activity == "all") & (g.position == "principal")].sort_values("year")
    f.errorbar(g0.year, g0.rate_per_100k_episodes, yerr=[g0.rate_per_100k_episodes - g0.rate_lo, g0.rate_hi - g0.rate_per_100k_episodes],
               fmt="o-", color=OK[0], lw=1.2, ms=3.4, capsize=1.4, elinewidth=0.6, label=tr("grd_prin", lang))
    g1 = g[(g.variant == variant) & (g.panel == "observed") & (g.activity == "hospitalisation") & (g.position == "principal")].sort_values("year")
    f.plot(g1.year, g1.rate_per_100k_episodes, "s:", color=OK[1], lw=1.0, ms=3.0, label=tr("grd_prin_hosp", lang))
    for r in g0.itertuples():
        f.text(r.year, 1.0, f"n={int(r.hospitals_n)}", ha="center", va="bottom", fontsize=FS_MIN, color=OK[0], rotation=90)
    context(f, lang, pandemic=None, law_text=False, fs=FS_MIN)
    f.set_ylim(0, float(max(de.rate_hi95.max(), g1.rate_per_100k_episodes.max())) * 2.6)
    f.set_xticks(CFG.YEARS_GRD); f.set_xticklabels([f"\u2019{y % 100:02d}" for y in CFG.YEARS_GRD], fontsize=FS_MIN + 0.5)
    f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("f4f_axis", lang), fontsize=FS_MIN + 1)
    f.legend(loc="upper left", fontsize=FS_MIN, handlelength=1.4)
    # La nota se imprimía sobre las series de DEIS y GRD; con el techo ampliado, la banda entre el pie de la
    # leyenda y el techo de las series queda libre y es donde se ancla, sin que el motor la mueva.
    f.text(0.03, 0.56, tr("deis_note", lang), transform=f.transAxes, fontsize=FS_MIN, ha="left", va="top",
           color="#444444", linespacing=1.25).set_gid(C.PLATE_KEEP)
    panel_head(f, "f", tr("f4f_title", lang), dx=-0.30)

    path = save_plate(fig, fdir / "fig4_triangulation.png", lang)
    plt.close(fig)
    return {"fig4_triangulation": str(path)}


# ---------------------------------------------------------------------------
# S9 — mapas regionales (GRD residencia, ambas variantes; REM A05 lugar de atención)
# ---------------------------------------------------------------------------
@timed("figS9")
def figS9(D, X, variant, lang, shapes) -> dict:
    plt, sns = plate_style()
    from scipy import stats
    fdir = out_dir(variant, lang, "figures")
    fig, gs = new_plate(plt)
    R = X["regional"]
    grd_last = 2024
    a05_last = 2024
    vmax_grd = float(R[(R.source == "grd_f84_any_residence") & (R.year == grd_last)].rate.max())
    # Fila 0: los dos mapas GRD (una variante por celda). Fila 1: el mapa A05 y la dispersión regional.
    # Fila 2: los dos mapas de calor por región y año. En vertical los mapas no caben en una fila de tres.
    for k, (v, letter_) in enumerate(zip(VARIANTS, ["a", "b"])):
        z = R[(R.source == "grd_f84_any_residence") & (R.variant == v) & (R.year == grd_last)].set_index("cut_region").rate
        chile_map(fig, gs[0, k], shapes, z, lang, tr("s9_grd_title", lang, v=tr(f"var_{v}", lang)), vmin=0, vmax=vmax_grd, letter_=letter_)
    za = R[(R.source == "a05_autism_entries_establishment") & (R.year == a05_last)].set_index("cut_region")
    chile_map(fig, gs[1, 0], shapes, za.rate, lang, tr("s9_a05_title", lang, n=num(za.reporting_n.sum(), 0, lang)), cmap="YlOrRd", vmin=0, letter_="c")
    zg = R[(R.source == "grd_f84_any_residence") & (R.variant == variant)]
    zz = R[R.source == "a05_autism_entries_establishment"]

    # d — dispersión regional GRD (residencia) frente a A05 (establecimiento), 2024
    d = fig.add_subplot(gs[1, 1])
    g24 = zg[zg.year == grd_last].set_index("cut_region").rate
    a24 = zz[zz.year == a05_last].set_index("cut_region").rate
    both = pd.DataFrame({"grd": g24, "a05": a24}).dropna()
    d.scatter(both.a05, both.grd, s=16, color=OK[0], edgecolor="white", linewidth=0.4, zorder=3)
    # Nombres abreviados: dieciséis rótulos no caben enteros en una celda de 90 mm (el nombre completo está
    # en el pie y en S9_regional_rates.csv). La COLOCACIÓN es de `place_point_labels`, al guardar: prueba 24
    # direcciones × 10 distancias alrededor de cada marcador, castiga tapar cualquiera de los dieciséis
    # —el propio o el del vecino— y tira una línea guía cuando el rótulo no queda pegado a su punto.
    rho, p = stats.spearmanr(both.a05, both.grd)
    d.set_xscale("log"); d.set_yscale("log")
    from matplotlib.ticker import FixedLocator, NullFormatter, FuncFormatter
    for axis_, vals in [(d.xaxis, both.a05), (d.yaxis, both.grd)]:
        lo_, hi_ = float(vals.min()), float(vals.max())
        ticks = [t for t in [10, 15, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300] if lo_ * 0.85 <= t <= hi_ * 1.15]
        axis_.set_major_locator(FixedLocator(ticks)); axis_.set_major_formatter(FuncFormatter(lambda v, _p: num(v, 0, lang))); axis_.set_minor_formatter(NullFormatter())
    d.set_ylim(bottom=float(both.grd.min()) * 0.80, top=float(both.grd.max()) * 2.6)   # aire para los rótulos y la nota
    d.set_xlim(float(both.a05.min()) * 0.80, float(both.a05.max()) * 1.28)
    _d_anns = [point_label(d, float(both.a05.loc[_reg]), float(both.grd.loc[_reg]),
                           REGION_NAMES_SHORT.get(_reg, str(_reg)), fontsize=FS_MIN)
               for _reg in both.grd.sort_values(ascending=False).index]
    fig._plate_points = [(d, _d_anns)]   # se colocan al guardar, con la composición ya congelada
    d.set_xlabel(tr("s9_f_x", lang)); d.set_ylabel(tr("s9_f_y", lang))
    plate_note(d, tr("s9_warning", lang), x=0.02, y=0.985, ha="left", color="#8b0000")
    panel_head(d, "d", f"{tr('s9_f_title', lang)}; {tr('spearman', lang)} = {num(rho, 2, lang)} (n = {len(both)})")

    # e — mapa de calor GRD por región y año
    e = fig.add_subplot(gs[2, 0])
    mat = zg.pivot(index="cut_region", columns="year", values="rate").reindex(REGION_ORDER)
    heatmap(e, mat, lang, lambda v: num(v, 0, lang), fontsize=FS_MIN + 0.2)
    e.set_xlabel(tr("year", lang)); e.set_ylabel(f"{tr('region', lang)} {tr('north_south', lang)}")
    panel_head(e, "e", tr("s9_d_title", lang, v=tr(f"var_{variant}", lang)))

    # f — mapa de calor A05: la tasa en la celda; el número de establecimientos, en el rótulo del año
    f = fig.add_subplot(gs[2, 1])
    mat = zz.pivot(index="cut_region", columns="year", values="rate").reindex(REGION_ORDER)
    est = zz.pivot(index="cut_region", columns="year", values="reporting_n").reindex(REGION_ORDER)
    heatmap(f, mat, lang, lambda v: num(v, 0, lang), cmap="YlOrRd", fontsize=FS_MIN + 0.2)
    f.set_xticklabels([f"{c}\nn={num(est[c].sum(), 0, lang)}" for c in mat.columns], fontsize=FS_MIN)
    f.set_xlabel(f"{tr('year', lang)} ({tr('s9_n_estab', lang)})"); f.set_ylabel("")
    panel_head(f, "f", tr("s9_e_title", lang))
    X["s9_rho"] = float(rho)
    path = save_plate(fig, fdir / "figS9_regional_maps.png", lang)
    plt.close(fig)
    return {"figS9_regional_maps": str(path)}


# ---------------------------------------------------------------------------
# S10 — sensibilidad de denominadores
# ---------------------------------------------------------------------------
@timed("figS10")
def figS10(D, X, variant, lang) -> dict:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = plt.subplots(3, 2, figsize=PLATE_SIZE, constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    cmp_ = D["ine_cmp"].sort_values("year")
    # A — población nacional según base
    a = ax[0, 0]
    a.plot(cmp_.year, cmp_.base2017_national_30jun / 1e6, "o-", color=OK[0], lw=2.2, ms=6, label=tr("base2017", lang))
    a.plot(cmp_.year, cmp_.base2024_national_30jun / 1e6, "s--", color=OK[1], lw=2, ms=6, label=tr("base2024_jun", lang))
    a.plot(cmp_.year, cmp_.base2024_national_1jan / 1e6, "^:", color=OK[2], lw=1.8, ms=6, label=tr("base2024_jan", lang))
    cz = cmp_[cmp_.censo2024_enumerated.notna()]
    a.scatter(cz.year, cz.censo2024_enumerated / 1e6, marker="*", s=180, color=OK[3], zorder=4, label=tr("censo2024", lang))
    for r in cz.itertuples():
        a.annotate(num(r.censo2024_enumerated / 1e6, 2, lang), (r.year, r.censo2024_enumerated / 1e6), xytext=(6, -10), textcoords="offset points", fontsize=7.5, color=OK[3])
    a.set_xticks(cmp_.year); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("s10_a_axis", lang)); a.set_title(tr("s10_a_title", lang))
    a.set_ylim(18, 20.6); plate_legend(a, loc="upper left"); add_letter(a, "a")
    # B — razones nacionales
    b = ax[0, 1]
    b.plot(cmp_.year, cmp_.ratio_base2024_to_base2017_30jun, "s-", color=OK[1], lw=2, ms=6, label=tr("r_base2024", lang))
    b.scatter(cz.year, cz.ratio_censo2024_to_base2017, marker="*", s=180, color=OK[3], zorder=4, label=tr("r_censo", lang))
    b.axhline(1, color="#888888", ls="--", lw=1)
    b.set_ylim(0.9, 1.02); b.set_xticks(cmp_.year); b.set_xlabel(tr("year", lang)); b.set_ylabel(tr("s10_b_axis", lang)); b.set_title(tr("s10_b_title", lang))
    # El rótulo del Censo 2024 se escribía a 6 pt del centro de una estrella de 180 pt²: dentro del propio
    # marcador. Se coloca midiendo, con los límites del eje ya fijados.
    for r in cmp_.itertuples():
        C.plate_value_label(b, float(r.year), float(r.ratio_base2024_to_base2017_30jun),
                            num(r.ratio_base2024_to_base2017_30jun, 3, lang), fontsize=FS_MIN, color=OK[1],
                            step_pt=2.4, max_steps=5)
    for r in cz.itertuples():
        C.plate_value_label(b, float(r.year), float(r.ratio_censo2024_to_base2017),
                            num(r.ratio_censo2024_to_base2017, 3, lang), fontsize=FS_MIN, color=OK[3],
                            step_pt=3.6, max_steps=5)
    plate_legend(b, loc="lower right")
    add_letter(b, "b")
    # C — razón regional Censo 2024 / base 2017
    c = ax[1, 0]
    reg = X["sens_reg"]
    r17 = reg[(reg.population_base == "base2017") & (reg.year == 2024)].set_index("cut_region").population
    rcz = reg[(reg.population_base == "censo2024")].set_index("cut_region").population
    ratio = (rcz / r17).reindex(REGION_ORDER)
    x = np.arange(len(REGION_ORDER))
    c.bar(x, ratio, color=[OK[3] if v < 1 else OK[2] for v in ratio])
    for xi, v in zip(x, ratio):
        c.text(xi, v + 0.003, num(v, 2, lang), ha="center", fontsize=6.5)
    c.axhline(1, color="#888888", ls="--", lw=1)
    nat_ratio = float(cz.ratio_censo2024_to_base2017.iloc[0])
    c.axhline(nat_ratio, color=OK[3], ls=":", lw=1.2, label=f"Chile = {num(nat_ratio, 3, lang)}")
    plate_legend(c, loc="upper right")
    c.set_xticks(x); c.set_xticklabels([REGION_NAMES[r] for r in REGION_ORDER], rotation=55, ha="right")
    c.set_ylim(0.8, 1.06); c.set_ylabel(tr("ratio", lang)); c.set_xlabel(f"{tr('region', lang)} {tr('north_south', lang)}"); c.set_title(tr("s10_c_title", lang)); add_letter(c, "c")
    # D — razón por grupo de edad, 2024 nacional
    d = ax[1, 1]
    nat = X["sens_nat_age"]
    b17 = nat[(nat.population_base == "base2017") & (nat.year == 2024)].set_index("age_group").population
    b24 = nat[(nat.population_base == "base2024_national") & (nat.year == 2024) & (nat.reference_date.astype(str).str.contains("06-30"))].set_index("age_group").population
    cz_age = nat[(nat.population_base == "censo2024")].set_index("age_group").population
    xa = np.arange(len(AGE_GROUPS))
    d.plot(xa, (b24 / b17).reindex(AGE_GROUPS), "s-", color=OK[1], lw=2, ms=5, label=tr("r_base2024", lang))
    d.plot(xa, (cz_age / b17).reindex(AGE_GROUPS), "*-", color=OK[3], lw=2, ms=8, label=tr("r_censo", lang))
    d.axhline(1, color="#888888", ls="--", lw=1)
    d.set_xticks(xa); d.set_xticklabels(AGE_GROUPS, rotation=45, ha="right")
    d.set_xlabel(tr("age_group", lang)); d.set_ylabel(tr("s10_b_axis", lang)); d.set_title(tr("s10_d_title", lang)); plate_legend(d, loc="lower right"); add_letter(d, "d")
    # E — GRD 2024 por edad con tres denominadores (escala log)
    e = ax[2, 0]
    ga = D["grd_age"]
    ga = ga[(ga.variant == variant) & (ga.panel == "observed") & (ga.activity == "all") & (ga.position == "any") & (ga.year == 2024) & (ga.age_group.isin(AGE_GROUPS))]
    cnt = ga.groupby("age_group").n_f84.sum().reindex(AGE_GROUPS)
    for den, col, mk, lab in [(b17, OK[0], "o", tr("with_base2017", lang)), (b24, OK[1], "s", tr("with_base2024", lang)), (cz_age, OK[3], "*", tr("with_censo", lang))]:
        rate = 1e5 * cnt / den.reindex(AGE_GROUPS)
        e.plot(xa, rate, marker=mk, ls="-", color=col, lw=1.6, ms=6 if mk != "*" else 9, label=lab)
    e.set_yscale("log")
    e.set_xticks(xa); e.set_xticklabels(AGE_GROUPS, rotation=45, ha="right")
    e.set_xlabel(tr("age_group", lang)); e.set_ylabel(tr("s10_e_axis", lang)); e.set_title(tr("s10_e_title", lang, v=tr(f"var_{variant}", lang))); plate_legend(e, loc="upper right")
    add_letter(e, "e")
    # F — GRD 2024 por región de residencia: base 2017 frente a Censo 2024
    f = ax[2, 1]
    R = X["regional"]
    z = R[(R.source == "grd_f84_any_residence") & (R.variant == variant) & (R.year == 2024)].set_index("cut_region").reindex(REGION_ORDER)
    rate_cz = 1e5 * z["count"] / rcz.reindex(REGION_ORDER)
    yy = np.arange(len(REGION_ORDER))[::-1]
    for yi, reg_ in zip(yy, REGION_ORDER):
        f.plot([z.loc[reg_, "rate"], rate_cz.loc[reg_]], [yi, yi], color="#bbbbbb", lw=3, zorder=1)
    f.errorbar(z.rate, yy, xerr=[z.rate - z.rate_lo, z.rate_hi - z.rate], fmt="o", color=OK[0], ms=6, capsize=2.5, lw=1.2, label=tr("with_base2017", lang), zorder=3)
    f.scatter(rate_cz, yy, marker="*", s=110, color=OK[3], zorder=4, label=tr("with_censo", lang))
    f.set_yticks(yy); f.set_yticklabels([REGION_NAMES[r] for r in REGION_ORDER])
    f.set_xlabel(tr("s10_f_axis", lang)); f.set_title(tr("s10_f_title", lang, v=tr(f"var_{variant}", lang))); plate_legend(f, loc="upper left"); add_letter(f, "f")
    X["s10_age_rates"] = pd.DataFrame({"age_group": AGE_GROUPS, "count_2024": cnt.values, "base2017": b17.reindex(AGE_GROUPS).values, "base2024_30jun": b24.reindex(AGE_GROUPS).values,
                                       "censo2024": cz_age.reindex(AGE_GROUPS).values})
    X["s10_region_ratio"] = ratio
    path = save_plate(fig, fdir / "figS10_denominators.png", lang)
    plt.close(fig)
    return {"figS10_denominators": str(path)}


# ---------------------------------------------------------------------------
# S11 — FONASA, APS e ISAPRE por edad y sexo (2025) y series nacionales
# ---------------------------------------------------------------------------
BANDS_10 = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]


def pyramid(ax, frame: pd.DataFrame, bands: list[str], sex_col: str, band_col: str, val_col: str, lang, title):
    m = frame[frame[sex_col] == "HOMBRE"].groupby(band_col)[val_col].sum().reindex(bands).fillna(0) / 1e3
    w = frame[frame[sex_col] == "MUJER"].groupby(band_col)[val_col].sum().reindex(bands).fillna(0) / 1e3
    y = np.arange(len(bands))
    ax.barh(y, -m, color=OK[0], label=tr("HOMBRE", lang))
    ax.barh(y, w, color=OK[1], label=tr("MUJER", lang))
    ax.set_yticks(y); ax.set_yticklabels(bands)
    lim = float(max(m.max(), w.max())) * 1.30   # margen para los totales de las esquinas altas
    ax.set_xlim(-lim, lim)
    ticks = ax.get_xticks()
    ax.set_xticks(ticks); ax.set_xticklabels([num(abs(t), 0, lang) for t in ticks])
    # La advertencia sobre sexo/edad sin información se imprimía sobre las barras más largas de la pirámide
    # (hasta el 86 % de una de ellas tapada); baja al rótulo del eje X, fuera del área de datos.
    ax.set_xlabel(f"{tr('thousands', lang)} · {tr('sex_unknown', lang)}", fontsize=FS_MIN + 0.5)
    ax.set_ylabel(tr("age_band", lang)); ax.set_title(title)
    tot_m, tot_w = float(m.sum()), float(w.sum())
    # Los totales van en las esquinas altas, donde las bandas de edad mayores dejan la pirámide vacía, y no
    # se mueven: la esquina dice a qué sexo pertenece cada total.
    ax.text(0.02, 0.98, f"{tr('HOMBRE', lang)}: {num(tot_m * 1e3, 0, lang)}", transform=ax.transAxes, fontsize=FS_MIN + 0.5, va="top", color=OK[0]).set_gid(C.PLATE_KEEP)
    ax.text(0.98, 0.98, f"{tr('MUJER', lang)}: {num(tot_w * 1e3, 0, lang)}", transform=ax.transAxes, fontsize=FS_MIN + 0.5, va="top", ha="right", color=OK[1]).set_gid(C.PLATE_KEEP)
    plate_legend(ax, loc="center right")


def to_10y(band5: str) -> str:
    if band5 == "80+":
        return "80+"
    lo = int(str(band5).split("-")[0])
    return f"{lo // 10 * 10}-{lo // 10 * 10 + 9}"


@timed("figS11")
def figS11(D, X, variant, lang) -> dict:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = plt.subplots(3, 2, figsize=PLATE_SIZE, constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    last = 2025
    fon = D["fon_age"]; fon = fon[(fon.year == last) & fon.age_band_5y.notna()]
    aps = D["aps_age"]; aps = aps[(aps.year == last) & aps.age_band_10y.notna()]
    isa = D["isa_age"]; isa = isa[(isa.year == last) & isa.age_band_5y.isin(AGE_GROUPS)]
    pyramid(ax[0, 0], fon, AGE_GROUPS, "sex", "age_band_5y", "beneficiaries", lang, tr("s11_a_title", lang)); add_letter(ax[0, 0], "a")
    pyramid(ax[0, 1], aps, BANDS_10, "sex", "age_band_10y", "enrolled", lang, tr("s11_b_title", lang)); add_letter(ax[0, 1], "b")
    pyramid(ax[1, 0], isa, AGE_GROUPS, "sex", "age_band_5y", "beneficiarios", lang, tr("s11_c_title", lang)); add_letter(ax[1, 0], "c")
    # D — series nacionales
    d = ax[1, 1]
    cov = D["cov"].sort_values("year")
    for col, lab, c_, mk in [("ine_population_base2017_30jun", "ine", "#333333", "o"), ("fonasa_beneficiaries_dec", "fonasa", OK[0], "s"), ("aps_enrolled_dec", "aps", OK[2], "^"), ("isapre_beneficiaries_dec", "isapre", OK[1], "D")]:
        d.plot(cov.year, cov[col] / 1e6, marker=mk, ls="-", color=c_, lw=2, ms=6, label=tr(lab, lang))
        d.annotate(num(cov[col].iloc[-1] / 1e6, 2, lang), (cov.year.iloc[-1], cov[col].iloc[-1] / 1e6), xytext=(5, 0), textcoords="offset points", fontsize=7.5, color=c_, va="center")
    # El número de centros APS iba sobre la serie, un rótulo por año, y dos rótulos contiguos no caben en el
    # paso entre años: pasa a la segunda línea de la marca de cada año, con su separador de miles.
    n_aps = {int(r.year): int(r.aps_centres) for r in cov.itertuples()}
    context(d, lang, pandemic="top", law_pos="top")
    d.set_xticks(cov.year)
    d.set_xticklabels([f"{int(y)}\n{num(n_aps[int(y)], 0, lang)}" if int(y) in n_aps else str(int(y)) for y in cov.year],
                      fontsize=FS_MIN + 0.2)
    d.set_xlabel(f"{tr('year', lang)} · {tr('s11_d_naps', lang)}"); d.set_ylabel(tr("s10_a_axis", lang))
    d.set_title(tr("s11_d_title", lang)); d.set_ylim(0, 24)
    d.set_xlim(float(cov.year.min()) - 0.4, float(cov.year.max()) + 1.5)   # sitio para los rótulos de fin de serie
    plate_legend(d, loc="center left", bbox_to_anchor=(0.0, 0.33)); add_letter(d, "d")
    # E — razones frente a INE
    e = ax[2, 0]
    for col, lab, c_, mk in [("share_fonasa_ine", "fonasa", OK[0], "s"), ("share_isapre_ine", "isapre", OK[1], "D")]:
        e.plot(cov.year, cov[col], marker=mk, ls="-", color=c_, lw=2, ms=6, label=tr(lab, lang))
    e.plot(cov.year, cov.aps_enrolled_dec / cov.ine_population_base2017_30jun, marker="^", ls="-", color=OK[2], lw=2, ms=6, label=tr("aps", lang))
    e.plot(cov.year, cov.share_fonasa_plus_isapre_ine, marker="o", ls="--", color="#333333", lw=1.6, ms=5, label="FONASA + ISAPRE")
    for col in ["share_fonasa_ine", "share_isapre_ine", "share_fonasa_plus_isapre_ine"]:
        e.annotate(num(cov[col].iloc[-1], 3, lang), (cov.year.iloc[-1], cov[col].iloc[-1]), xytext=(5, 0), textcoords="offset points", fontsize=7.5, va="center")
    # Banda superior libre para la advertencia (con el techo de 1,1 se imprimía sobre la serie FONASA +
    # ISAPRE, tapándola por completo) y margen derecho para los rótulos de fin de serie.
    e.set_ylim(0, 1.75); e.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
    e.set_xticks(cov.year); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("s11_e_axis", lang)); e.set_title(tr("s11_e_title", lang))
    e.set_xlim(float(cov.year.min()) - 0.4, float(cov.year.max()) + 1.5)
    context(e, lang, pandemic=None, law_text=False)   # rotulados una sola vez en la lámina, en (d)
    # Sitio reservado a propósito en la banda alta: el motor la llevaba al hueco de abajo, encima de la
    # serie de ISAPRE, que es la más baja del panel.
    plate_legend(e, loc="upper right").set_gid(C.PLATE_KEEP)
    # Una línea al pie del panel, donde no llega ninguna serie: la advertencia completa (tres líneas) tapaba
    # por entero la serie FONASA + ISAPRE y, subida arriba, la leyenda. Su texto está íntegro en el pie.
    e.text(0.02, 0.015, tr("s11_e_note_short", lang), transform=e.transAxes, fontsize=FS_MIN + 0.4,
           color="#8b0000", va="bottom").set_gid(C.PLATE_KEEP)
    add_letter(e, "e")
    # F — estructura etaria decenal 2025
    f = ax[2, 1]
    i = D["ine"]; ine = i[(i.level == "national") & (i.sex == "TOTAL") & (i.year == last) & (i.age_group.isin(AGE_GROUPS))].copy()
    ine["b10"] = ine.age_group.map(to_10y)
    fon2 = fon.copy(); fon2["b10"] = fon2.age_band_5y.map(to_10y)
    isa2 = isa.copy(); isa2["b10"] = isa2.age_band_5y.map(to_10y)
    series = [("ine", ine.groupby("b10").population.sum(), "#333333", "o"), ("fonasa", fon2.groupby("b10").beneficiaries.sum(), OK[0], "s"),
              ("aps", aps.groupby("age_band_10y").enrolled.sum(), OK[2], "^"), ("isapre", isa2.groupby("b10").beneficiarios.sum(), OK[1], "D")]
    xb = np.arange(len(BANDS_10))
    table_rows = {}
    for lab, s, c_, mk in series:
        s = s.reindex(BANDS_10).fillna(0)
        pct = 100 * s / s.sum()
        f.plot(xb, pct, marker=mk, ls="-", color=c_, lw=2, ms=6, label=tr(lab, lang))
        table_rows[lab] = s
    f.set_xticks(xb); f.set_xticklabels(BANDS_10); f.set_xlabel(tr("age_band", lang)); f.set_ylabel(tr("s11_f_axis", lang)); f.set_title(tr("s11_f_title", lang))
    plate_legend(f, loc="upper right"); add_letter(f, "f")
    X["s11_age10"] = pd.DataFrame(table_rows).reindex(BANDS_10)
    X["s11_sex_age"] = dict(fonasa=fon, aps=aps, isapre=isa)
    path = save_plate(fig, fdir / "figS11_coverage_age_sex.png", lang)
    plt.close(fig)
    return {"figS11_coverage_age_sex": str(path)}


# ---------------------------------------------------------------------------
# S12 — JUNAEB por sexo y nivel
# ---------------------------------------------------------------------------
JLEVELS = ["parvularia", "basico1", "basico5", "medio1"]
SEXCOL = {"male": OK[0], "female": OK[1], "all": "#333333"}


def _junaeb_bars(ax, jun, year, lang, weighted: bool, title):
    d = jun[jun.year == year]
    x = np.arange(len(JLEVELS))
    _val_labels: list = []
    for k, sex in enumerate(["male", "female", "all"]):
        off = (k - 1) * 0.27
        vals, lo, hi = [], [], []
        for lv in JLEVELS:
            r = d[(d.level == lv) & (d.sex == sex)]
            if r.empty or r.iloc[0].estimable == "no":
                vals.append(np.nan); lo.append(np.nan); hi.append(np.nan)
                continue
            r = r.iloc[0]
            if weighted:
                vals.append(r.proportion_weighted_pct); lo.append(r.lo_pct); hi.append(r.hi_pct)
            else:
                vals.append(r.proportion_unweighted_pct); lo.append(r.lo_unweighted_pct); hi.append(r.hi_unweighted_pct)
        vals, lo, hi = np.array(vals, dtype=float), np.array(lo, dtype=float), np.array(hi, dtype=float)
        ax.bar(x + off, np.nan_to_num(vals), width=0.25, color=SEXCOL[sex] if weighted else "white", edgecolor=SEXCOL[sex], linewidth=1.3,
               yerr=[np.nan_to_num(vals - lo), np.nan_to_num(hi - vals)], error_kw=dict(ecolor="#444444", lw=1, capsize=2.5), label=tr(sex, lang), hatch=None if weighted else "\\\\")
        for xi, v, l_, h_ in zip(x + off, vals, lo, hi):
            if np.isfinite(v):
                _val_labels.append((float(xi), float(v), float(l_) if np.isfinite(l_) else float(v),
                                    float(h_) if np.isfinite(h_) else float(v), num(v, 1, lang), SEXCOL[sex]))
        for xi, v in zip(x + off, vals):
            if not np.isfinite(v):
                ax.scatter(xi, 0.35, marker="s", s=60, facecolor="white", edgecolor=SEXCOL[sex], hatch="////", linewidth=1, zorder=3)
                if sex == "female":
                    ax.text(xi, 0.9, tr("not_estimable", lang), ha="center", fontsize=6.5, color="#8b0000")
    ax.set_xticks(x); ax.set_xticklabels([C.plate_wrap(tr(f"jun_{lv}", lang), 46.0, FS_MIN + 0.5, "normal") for lv in JLEVELS],
                                        fontsize=FS_MIN + 0.5)
    ax.set_ylabel(tr("weighted_pct" if weighted else "unweighted_pct", lang)); ax.set_title(title)
    # Banda superior libre para la leyenda y para los rótulos de valor, que se colocan MIDIENDO y esquivando
    # la barra de error de su propio dato: escritos a 0,25 sobre la barra, caían sobre su propio remate.
    _top = max([h for _x, _v, _l, h, _t, _c in _val_labels] + [0.0])
    ax.set_ylim(0, _top * 1.75 if _top > 0 else None)
    for _x, _v, _l, _h, _t, _c in _val_labels:
        C.plate_value_label(ax, _x, _v, _t, err=(_l, _h), fontsize=FS_MIN, color=_c, step_pt=2.2, max_steps=5)
    plate_legend(ax, loc="upper right")


@timed("figS12")
def figS12(D, X, variant, lang) -> dict:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = plt.subplots(3, 2, figsize=PLATE_SIZE, constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    jun = D["jun"]
    ymax = float(np.nanmax([jun.hi_pct.max(), jun.hi_unweighted_pct.max()])) * 1.3
    _junaeb_bars(ax[0, 0], jun, 2023, lang, False, tr("s12_a_title", lang)); ax[0, 0].set_ylim(0, ymax); add_letter(ax[0, 0], "a")
    _junaeb_bars(ax[0, 1], jun, 2024, lang, True, tr("s12_b_title", lang)); ax[0, 1].set_ylim(0, ymax); add_letter(ax[0, 1], "b")
    plate_note(ax[0, 1], tr("ne_reason_medio1", lang), x=0.98, y=0.72, ha="right", va="top", color="#8b0000", width_pt=95.0)
    _junaeb_bars(ax[1, 0], jun, 2025, lang, True, tr("s12_c_title", lang)); ax[1, 0].set_ylim(0, ymax); add_letter(ax[1, 0], "c")
    # D — razón hombre:mujer
    d = ax[1, 1]
    rows = []
    for year, weighted in [(2023, False), (2024, True), (2025, True)]:
        for lv in JLEVELS:
            m = jun[(jun.year == year) & (jun.level == lv) & (jun.sex == "male")]
            w = jun[(jun.year == year) & (jun.level == lv) & (jun.sex == "female")]
            if m.empty or w.empty or m.iloc[0].estimable == "no" or w.iloc[0].estimable == "no":
                rows.append(dict(year=year, level=lv, ratio=np.nan, lo=np.nan, hi=np.nan, estimator="not estimable"))
                continue
            m, w = m.iloc[0], w.iloc[0]
            if weighted:
                pm, pw, sm, sw = m.proportion_weighted_pct, w.proportion_weighted_pct, m.se_pct, w.se_pct
            else:
                pm, pw = m.proportion_unweighted_pct, w.proportion_unweighted_pct
                sm, sw = (m.hi_unweighted_pct - m.lo_unweighted_pct) / 3.92, (w.hi_unweighted_pct - w.lo_unweighted_pct) / 3.92
            ratio = pm / pw
            se_log = np.sqrt((sm / pm) ** 2 + (sw / pw) ** 2)
            rows.append(dict(year=year, level=lv, ratio=ratio, lo=ratio * np.exp(-1.96 * se_log), hi=ratio * np.exp(1.96 * se_log), estimator="weighted" if weighted else "unweighted"))
    RR = pd.DataFrame(rows)
    X["s12_ratio"] = RR
    x = np.arange(len(JLEVELS))
    _d_labels: list = []
    for k, (year, mk) in enumerate([(2023, "o"), (2024, "s"), (2025, "D")]):
        z = RR[RR.year == year].set_index("level").reindex(JLEVELS)
        off = (k - 1) * 0.22
        # marcador al tamaño de la lámina vertical (7 pt en una celda de 90 mm no dejaba sitio a su rótulo)
        d.errorbar(x + off, z.ratio, yerr=[z.ratio - z.lo, z.hi - z.ratio], fmt=mk, color=OK[k], ms=4.0, capsize=1.8, lw=1.2, mfc="white" if year == 2023 else OK[k], label=f"{year}" + (" (" + tr("s12_f_x", lang).lower() + ")" if year == 2023 else ""))
        for xi, v, lo_, hi_ in zip(x + off, z.ratio, z.lo, z.hi):
            if np.isfinite(v):
                _d_labels.append((float(xi), float(v), float(lo_) if np.isfinite(lo_) else float(v),
                                  float(hi_) if np.isfinite(hi_) else float(v), num(v, 2, lang), OK[k]))
            else:
                d.scatter(xi, 0.25, marker="s", s=60, facecolor="white", edgecolor=OK[k], hatch="////", linewidth=1, zorder=3)
                d.text(xi, 0.5, tr("not_estimable", lang), ha="center", fontsize=6.5, color="#8b0000")
    d.axhline(1, color="#888888", ls="--", lw=1)
    d.set_xticks(x); d.set_xticklabels([C.plate_wrap(tr(f"jun_{lv}", lang), 46.0, FS_MIN + 0.5, "normal") for lv in JLEVELS],
                                       fontsize=FS_MIN + 0.5); d.set_xlim(-0.6, len(JLEVELS) - 0.25)
    d.set_ylim(0, 7.2); d.set_yticks([0, 1, 2, 3, 4])   # aire para la leyenda y para los rótulos de razón
    d.set_ylabel(tr("s12_d_axis", lang)); d.set_title(tr("s12_d_title", lang))
    # Los rótulos de razón se escribían a 6 pt del centro de su propio marcador (7 pt de diámetro con su
    # remate blanco) y caían dentro de él; se colocan midiendo, con los límites ya fijados.
    for _x, _v, _lo, _hi, _t, _c in _d_labels:
        # El colocador ya ha medido el hueco: la pasada de colisiones no debe volver a moverlo (lo devolvía
        # sobre su propio marcador).
        C.plate_value_label(d, _x, _v, _t, err=(_lo, _hi), fontsize=FS_MIN, color=_c, step_pt=3.0,
                            max_steps=10).set_gid(C.PLATE_KEEP)
    plate_legend(d, loc="upper right"); add_letter(d, "d")
    # E — n estudiantes por nivel y año (todos), con casos TEA
    e = ax[2, 0]
    yrs = sorted(jun.year.unique())
    # Los cuatro rótulos de un año son texto GIRADO de unos 7,5 pt de ancho y las barras tienen un paso de
    # 5,3 pt: escritos cada uno sobre SU barra, se metían en el de al lado y los recuadros blancos se fundían
    # en una sola columna de dígitos, además de caer sobre la barra vecina. Se escriben a una altura COMÚN
    # por año —por encima de la barra más alta del grupo, de modo que ninguno cae sobre una barra— y en DOS
    # filas alternas: dos rótulos vecinos nunca comparten altura, y los que sí la comparten están a dos
    # barras de distancia, que es más que su ancho.
    tops = (jun[(jun.level.isin(JLEVELS)) & (jun.sex == "all")]
            .groupby("year").n_students.max().div(1e3).to_dict())
    for k, lv in enumerate(JLEVELS):
        z = jun[(jun.level == lv) & (jun.sex == "all")].set_index("year").reindex(yrs)
        off = (k - 1.5) * 0.2
        e.bar(np.array(yrs) + off, z.n_students / 1e3, width=0.19, color=OK[k], label=tr(f"jun_{lv}", lang))
        for y, r in z.iterrows():
            if pd.notna(r.n_tea_unweighted):
                e.annotate(num(r.n_tea_unweighted, 0, lang), xy=(y + off, tops.get(y, float(r.n_students) / 1e3)),
                           xycoords="data", textcoords="offset points", xytext=(0, 4.0 + (k % 2) * 25.0),
                           ha="center", va="bottom", rotation=90, fontsize=6.2, color=OK[k],
                           gid=C.PLATE_KEEP)
    e.set_xticks(yrs); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("s12_e_axis", lang)); e.set_title(tr("s12_e_title", lang)); e.set_ylim(0, 520)
    e.text(0.01, 0.98, tr("tea_cases", lang) + " ↑", transform=e.transAxes, fontsize=7, va="top", color="#555555")
    plate_legend(e, loc="upper right", ncol=2); add_letter(e, "e")
    # F — ponderado frente a no ponderado
    f = ax[2, 1]
    z = jun[(jun.estimable == "yes")]
    for k, sex in enumerate(["male", "female", "all"]):
        zz = z[z.sex == sex]
        f.scatter(zz.proportion_unweighted_pct, zz.proportion_weighted_pct, s=[55 if y == 2025 else 35 for y in zz.year], color=SEXCOL[sex], edgecolor="white", label=tr(sex, lang), zorder=3)
    lim = float(max(z.proportion_unweighted_pct.max(), z.proportion_weighted_pct.max())) * 1.25
    f.plot([0, lim], [0, lim], color="#888888", ls="--", lw=1, label=tr("identity", lang))
    f.set_xlim(0, lim); f.set_ylim(0, lim); f.set_xlabel(tr("s12_f_x", lang)); f.set_ylabel(tr("s12_f_y", lang)); f.set_title(tr("s12_f_title", lang))
    # Los rótulos de nivel y año se colocan MIDIENDO: escritos a 5 pt del punto caían dentro del marcador
    # (55 pt² en 2025) o sobre el marcador vecino.
    for r in z[z.sex == "all"].itertuples():
        C.plate_value_label(f, float(r.proportion_unweighted_pct), float(r.proportion_weighted_pct),
                            f"{tr('jun_' + r.level, lang)} {r.year}", fontsize=FS_MIN, color="#222222",
                            step_pt=3.4, max_steps=6)
    plate_legend(f, loc="upper left")
    add_letter(f, "f")
    path = save_plate(fig, fdir / "figS12_junaeb_sex_level.png", lang)
    plt.close(fig)
    return {"figS12_junaeb_sex_level": str(path)}


# ---------------------------------------------------------------------------
# S14 — DEIS F84 principal por sexo, edad OMS y pertenencia
# ---------------------------------------------------------------------------
BANDS_DEIS = ["<1", "1-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]


@timed("figS14")
def figS14(D, X, variant, lang) -> dict:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = plt.subplots(3, 2, figsize=PLATE_SIZE, constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    ds = D["dsex"]; ds = ds[(ds.variant == variant) & (ds.source_layout == "canonical")]
    # A — por sexo y año
    a = ax[0, 0]
    for sex, col, mk in [("HOMBRE", OK[0], "o"), ("MUJER", OK[1], "s")]:
        z = ds[(ds.level == "sex") & (ds.sex == sex)].sort_values("year")
        a.errorbar(z.year + (-0.06 if sex == "HOMBRE" else 0.06), z.rate_per_100k_discharges, yerr=[z.rate_per_100k_discharges - z.rate_lo95, z.rate_hi95 - z.rate_per_100k_discharges], fmt=mk + "-", color=col, lw=2, ms=6, capsize=3, label=tr(sex, lang))
    z = ds[(ds.level == "total")].sort_values("year")
    a.plot(z.year, z.rate_per_100k_discharges, "^--", color="#333333", lw=1.6, ms=5, label=tr("TOTAL", lang))
    # Banda superior reservada (leyenda arriba a la izquierda, nota arriba a la derecha) y los rótulos de
    # contexto en la banda intermedia, que no tiene series: a media altura y al pie caían sobre ellas.
    a.set_xticks(CFG.YEARS_GRD); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("s14_axis", lang)); a.set_title(tr("s14_a_title", lang))
    a.set_ylim(0, float(ds[(ds.level == "sex") & ds.sex.isin(["HOMBRE", "MUJER"])].rate_hi95.max()) * 2.4)
    context(a, lang, pandemic="mid", law_pos="mid")
    # La nota «DEIS DIAG2 es causa externa…» ocupaba, plegada, el ancho entero del panel y se imprimía sobre
    # la leyenda; su texto está íntegro en el pie de la figura.
    plate_legend(a, loc="upper left")
    add_letter(a, "a")
    # B — grupos OMS 2021 y 2024
    b = ax[0, 1]
    dw = D["dage"]; dw = dw[dw.variant == variant]
    xa = np.arange(len(AGE_GROUPS))
    for year, col, mk in [(2021, OK[5], "o"), (2024, OK[0], "s")]:
        z = dw[(dw.year == year) & (dw.level == "age_group_who") & (dw.sex == "TOTAL")].set_index("age_group_who").reindex(AGE_GROUPS)
        b.errorbar(xa + (-0.1 if year == 2021 else 0.1), z.rate_per_100k_discharges, yerr=[z.rate_per_100k_discharges - z.rate_lo95, z.rate_hi95 - z.rate_per_100k_discharges], fmt=mk + "-", color=col, lw=1.8, ms=5.5, capsize=2.5, label=str(year))
    b.set_xticks(xa); b.set_xticklabels(AGE_GROUPS, rotation=45, ha="right"); b.set_xlabel(tr("age_group", lang)); b.set_ylabel(tr("s14_axis", lang)); b.set_title(tr("s14_b_title", lang))
    plate_legend(b, loc="upper right"); add_letter(b, "b")
    # C — 2024 por sexo y grupo OMS
    c = ax[1, 0]
    for sex, col, mk, off in [("HOMBRE", OK[0], "o", -0.1), ("MUJER", OK[1], "s", 0.1)]:
        z = dw[(dw.year == 2024) & (dw.level == "sexxage_group_who") & (dw.sex == sex)].set_index("age_group_who").reindex(AGE_GROUPS)
        c.errorbar(xa + off, z.rate_per_100k_discharges, yerr=[z.rate_per_100k_discharges - z.rate_lo95, z.rate_hi95 - z.rate_per_100k_discharges], fmt=mk + "-", color=col, lw=1.8, ms=5.5, capsize=2.5, label=tr(sex, lang))
    c.set_xticks(xa); c.set_xticklabels(AGE_GROUPS, rotation=45, ha="right"); c.set_xlabel(tr("age_group", lang)); c.set_ylabel(tr("s14_axis", lang)); c.set_title(tr("s14_c_title", lang))
    plate_legend(c, loc="upper right"); add_letter(c, "c")
    # D — mapa de calor banda decenal × año
    d = ax[1, 1]
    z = ds[(ds.level == "age_band_10") & (ds.sex == "TOTAL") & (ds.age_band_10.isin(BANDS_DEIS))]
    mat = z.pivot(index="age_band_10", columns="year", values="rate_per_100k_discharges").reindex(BANDS_DEIS)
    data = mat.to_numpy(dtype=float)
    d.imshow(data, cmap="YlGnBu", aspect="auto"); d.grid(False)
    d.set_xticks(range(mat.shape[1])); d.set_xticklabels(mat.columns); d.set_yticks(range(len(BANDS_DEIS))); d.set_yticklabels(BANDS_DEIS)
    vmax = np.nanmax(data)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = data[i, j]
            d.text(j, i, num(v, 0, lang) if np.isfinite(v) else "—", ha="center", va="center", fontsize=7, color="white" if v > 0.6 * vmax else "#222222")
    d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("age_band", lang)); d.set_title(tr("s14_d_title", lang)); add_letter(d, "d")
    # E — SNSS frente a no SNSS
    e = ax[2, 0]
    de = D["dest"]; de = de[(de.variant == variant) & (de.dimension == "pertenencia_snss")]
    for cat, col, mk, lab in [("SNSS", OK[0], "o", "snss"), ("NO_SNSS", OK[1], "s", "no_snss"), ("SUPRIMIDO", "#999999", "x", "suppressed")]:
        z = de[de.category == cat].sort_values("year")
        e.errorbar(z.year, z.rate_per_100k_discharges, yerr=[z.rate_per_100k_discharges - z.rate_lo95, z.rate_hi95 - z.rate_per_100k_discharges], fmt=mk + ("-" if cat != "SUPRIMIDO" else ":"), color=col, lw=2 if cat != "SUPRIMIDO" else 1, ms=6, capsize=3, label=tr(lab, lang), alpha=1 if cat != "SUPRIMIDO" else 0.7)
    e.set_xticks(CFG.YEARS_GRD); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("s14_axis", lang)); e.set_title(tr("s14_e_title", lang))
    e.set_ylim(0, float(de[de.category != "SUPRIMIDO"].rate_hi95.max()) * 3.0)
    context(e, lang, pandemic=None, law_text=False)   # rotulados una sola vez en la lámina, en (a)
    plate_legend(e, loc="upper left"); add_letter(e, "e")
    # F — conteos apilados
    f = ax[2, 1]
    piv = de.pivot(index="year", columns="category", values="f84_diag1").reindex(columns=["SNSS", "NO_SNSS", "SUPRIMIDO"]).fillna(0)
    bottom = np.zeros(len(piv))
    for cat, col, lab in [("SNSS", OK[0], "snss"), ("NO_SNSS", OK[1], "no_snss"), ("SUPRIMIDO", "#999999", "suppressed")]:
        f.bar(piv.index, piv[cat], bottom=bottom, color=col, label=tr(lab, lang), width=0.7)
        bottom += piv[cat].values
    # Bloque de valor ESTRECHO: «336 % SNSS = 78» medía 42 pt y el paso entre barras 25, de modo que los
    # bloques se montaban sobre la barra vecina y el motor los apartaba, dejando 2023 y 2024 en el orden
    # cambiado. Ahora es el total sobre el porcentaje, cada uno de cuatro caracteres, pegado a SU barra;
    # el significado de las dos cifras va en el título del panel y en el pie.
    f.set_ylim(0, float(bottom.max()) * 1.55)
    for y, tot in zip(piv.index, bottom):
        f.text(y, tot + 8, f"{num(tot, 0, lang)}\n{pct_str(100 * piv.loc[y, 'SNSS'] / tot, lang, 0)}",
               ha="center", va="bottom", fontsize=FS_MIN, linespacing=1.15).set_gid(C.PLATE_KEEP)
    context(f, lang, pandemic=None, law_text=False)   # rotulados una sola vez en la lámina, en (a)
    f.set_xticks(CFG.YEARS_GRD); f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("s14_f_axis", lang))
    f.set_title(f"{tr('s14_f_title', lang)} · {tr('s14_f_labels', lang)}")
    plate_legend(f, loc="upper left"); add_letter(f, "f")
    path = save_plate(fig, fdir / "figS14_deis_sex_age.png", lang)
    plt.close(fig)
    return {"figS14_deis_sex_age": str(path)}


# ---------------------------------------------------------------------------
# S15 — controles de reproducción: observado frente a esperado
# ---------------------------------------------------------------------------
def controls_numeric(ctrl: pd.DataFrame) -> pd.DataFrame:
    d = ctrl.copy()
    d["expected_num"] = pd.to_numeric(d.expected, errors="coerce")
    d["observed_num"] = pd.to_numeric(d.observed, errors="coerce")
    d = d[d.status.isin(["ok", "differs"]) & d.expected_num.notna() & d.observed_num.notna()].copy()
    d["rel_pct"] = np.where(d.expected_num != 0, 100 * (d.observed_num - d.expected_num) / d.expected_num, np.nan)
    return d


def explain(name: str, lang: str) -> str:
    key = f"expl_{name}"
    return LBL[key][lang] if key in LBL else tr("expl_default", lang)


def wrap_identifier(s: str, width: int, indent: str = "") -> list[str]:
    """Envuelve una línea que contiene identificadores sin partir ninguna palabra por la mitad.

    `textwrap.wrap` con sus valores por omisión parte cualquier palabra más larga que la caja carácter a
    carácter: `deis_vs_grd_observed_panel_strict_hospitalisation_vs_config` se imprimía como
    «…_vs_conf» / «ig: …» y el nombre del control ya no podía recuperarse de la página. Aquí los únicos
    puntos de corte son el espacio y el guion bajo —el corte queda DESPUÉS del `_`, que se ve al final de
    la línea y anuncia que el nombre sigue—, de modo que cada trozo impreso es un trozo real del nombre.
    Un fragmento que por sí solo no cabe se deja entero y desborda: vale más una línea larga que un
    identificador irrecuperable.
    """
    tokens: list[tuple[str, str]] = []          # (separador antes del trozo, trozo)
    for w, word in enumerate(s.split()):
        pieces = [pc for pc in re.split(r"(?<=_)", word) if pc]
        for i, piece in enumerate(pieces):
            tokens.append((" " if (w and i == 0) else "", piece))
    lines: list[str] = []
    cur = ""
    for sep, piece in tokens:
        room = width - (0 if not lines else len(indent))
        cand = cur + sep + piece if cur else piece
        if cur and len(cand) > room:
            lines.append(cur)
            cur = piece
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return [ln if i == 0 else indent + ln for i, ln in enumerate(lines)]


@timed("figS15")
def figS15(D, X, variant, lang) -> dict:
    plt, sns = plate_style()
    import textwrap
    fdir = out_dir(variant, lang, "figures")
    fig, ax = plt.subplots(3, 2, figsize=PLATE_SIZE, constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    ctrl = D["ctrl"]
    d = controls_numeric(ctrl)
    d = d.sort_values(["module", "name", "key"]).reset_index(drop=True)
    d["differs_id"] = np.nan
    diff_idx = d.index[d.status == "differs"]
    d.loc[diff_idx, "differs_id"] = np.arange(1, len(diff_idx) + 1)
    modules = sorted(d.module.unique())
    extra_colours = ["#8c564b", "#7f7f7f", "#17becf"]
    mcol = {m: (OK[i] if i < len(OK) else extra_colours[(i - len(OK)) % len(extra_colours)]) for i, m in enumerate(modules)}

    def scatter(axis, frame, title, letter_, label_differs=True):
        for m in modules:
            z = frame[frame.module == m]
            if z.empty:
                continue
            axis.scatter(z.expected_num, z.observed_num, s=28, color=mcol[m], alpha=0.75, edgecolor="white", linewidth=0.5, label=tr(f"mod_{m}", lang) if f"mod_{m}" in LBL else m, zorder=3)
        lim = float(max(frame.expected_num.max(), frame.observed_num.max())) * 40.0
        axis.plot([0, lim], [0, lim], color="#888888", ls="--", lw=1, label=tr("identity", lang), zorder=1)
        axis.set_xscale("symlog", linthresh=1); axis.set_yscale("symlog", linthresh=1)
        # Margen: con el tope anterior la última marca de la década caía pegada al borde del panel y su
        # rótulo se imprimía sobre el de la primera marca del panel vecino.
        axis.set_xlim(-0.5, lim); axis.set_ylim(-0.5, lim)
        axis.tick_params(axis="both", labelsize=FS_MIN)
        if label_differs:
            for r in frame[frame.status == "differs"].itertuples():
                axis.scatter(r.expected_num, r.observed_num, s=70, facecolor="none", edgecolor="#8b0000", linewidth=1.2, zorder=4)
            for r in frame[frame.status == "differs"].itertuples():
                C.plate_value_label(axis, float(r.expected_num), float(r.observed_num), f"{int(r.differs_id)}",
                                    fontsize=FS_MIN, color="#8b0000", step_pt=4.2, max_steps=5, fontweight="bold")
        axis.set_xlabel(tr("expected", lang)); axis.set_ylabel(tr("observed", lang)); axis.set_title(title); plate_legend(axis, loc="upper left")
        add_letter(axis, letter_)
    scatter(ax[0, 0], d, tr("s15_a_title", lang), "a")
    # B — diferencia relativa
    b = ax[0, 1]
    z = d[d.expected_num != 0]
    for m in modules:
        zz = z[z.module == m]
        b.scatter(zz.expected_num.abs(), zz.rel_pct, s=28, color=mcol[m], alpha=0.75, edgecolor="white", linewidth=0.5, zorder=3)
    b.axhspan(-0.5, 0.5, color=OK[2], alpha=0.12); b.axhline(0, color="#888888", lw=1)
    b.text(0.99, 0.98, tr("tol", lang), transform=b.transAxes, fontsize=7, ha="right", va="top", color=OK[2])
    for k, r in enumerate(z[z.status == "differs"].itertuples()):
        b.annotate(f"{int(r.differs_id)}", (abs(r.expected_num), r.rel_pct), xytext=(7 + 9 * (k % 3), 4), textcoords="offset points", fontsize=6.5, color="#8b0000", fontweight="bold")
        b.scatter(abs(r.expected_num), r.rel_pct, s=70, facecolor="none", edgecolor="#8b0000", linewidth=1.2, zorder=4)
    b.set_xscale("log"); b.set_xlabel(tr("s15_b_x", lang)); b.set_ylabel(tr("s15_b_axis", lang)); b.set_title(tr("s15_b_title", lang))
    _bx = z.expected_num.abs()
    _bx = _bx[_bx > 0]
    if len(_bx):
        b.set_xlim(float(_bx.min()) * 0.04, float(_bx.max()) * 25.0)
    b.tick_params(axis="both", labelsize=FS_MIN)
    ylim = float(np.nanmax(np.abs(z.rel_pct))) * 1.4 if z.rel_pct.notna().any() else 5
    b.set_ylim(-max(ylim, 1), max(ylim, 1)); add_letter(b, "b")
    # C — estado por módulo
    c = ax[1, 0]
    st = ctrl.groupby(["module", "status"]).size().unstack(fill_value=0).reindex(columns=["ok", "differs", "info"], fill_value=0)
    mods = list(st.index)
    y = np.arange(len(mods))
    left = np.zeros(len(mods))
    for stt, col in [("ok", OK[2]), ("differs", "#8b0000"), ("info", "#bbbbbb")]:
        c.barh(y, st[stt], left=left, color=col, label=tr(f"status_{stt}", lang))
        for yi, (l0, v) in enumerate(zip(left, st[stt])):
            _wide = float(v) >= 0.06 * float(st.to_numpy().sum(axis=1).max())
            if v > 0 and _wide:
                c.text(l0 + v / 2, yi, str(int(v)), ha="center", va="center", fontsize=FS_MIN, color="white" if stt != "info" else "#333333")
        left += st[stt].values
    c.set_yticks(y); c.set_yticklabels([tr(f"mod_{m}", lang) if f"mod_{m}" in LBL else m for m in mods])
    # Total al final de cada barra: un segmento de uno o dos controles es más estrecho que su propia cifra
    # y dos cifras contiguas se imprimían una sobre otra. Los controles que difieren se enumeran, uno a uno,
    # en el panel (f) y en la tabla de controles de reproducción.
    for yi, tot in enumerate(left):
        c.text(tot + 0.012 * float(left.max()), yi, str(int(tot)), ha="left", va="center", fontsize=FS_MIN, color="#333333")
    c.set_xlim(0, float(left.max()) * 1.16)
    c.set_xlabel(tr("s15_c_axis", lang)); c.set_title(tr("s15_c_title", lang)); plate_legend(c, loc="lower right"); c.invert_yaxis(); add_letter(c, "c")
    # D — GRD y DEIS
    scatter(ax[1, 1], d[d.module.isin(["01_grd_core", "01b_deis_egresos"])], tr("s15_d_title", lang), "d")
    # E — REM, denominadores, encuestas, educación, modelos
    scatter(ax[2, 0], d[d.module.isin(["02_rem_pathway", "03_denominators", "04_surveys", "05_education", "06_models"])], tr("s15_e_title", lang), "e")
    # F — listado de controles que difieren
    f = ax[2, 1]; f.set_axis_off()
    # Una línea por control: en una celda de 90 × 62 mm no caben las explicaciones, que se imprimen íntegras
    # en la tabla de controles de reproducción del material suplementario.
    lines = []
    for r in d[d.status == "differs"].itertuples():
        head = (f"{int(r.differs_id)}. {tr(f'mod_{r.module}', lang) if f'mod_{r.module}' in LBL else r.module} · {r.name}: "
                f"{num(r.expected_num, 0 if float(r.expected_num).is_integer() else 2, lang)} → "
                f"{num(r.observed_num, 0 if float(r.observed_num).is_integer() else 2, lang)}")
        lines.extend(wrap_identifier(head, 62, indent="     "))
    lines.append("")
    lines.extend(textwrap.wrap(tr("s15_f_note", lang), 62))
    text = "\n".join(lines) if lines else "—"
    f.text(0.0, 0.99, text, transform=f.transAxes, fontsize=FS_MIN + 0.2, va="top", ha="left", family="DejaVu Sans", linespacing=1.25)
    f.set_title(tr("s15_f_title", lang)); add_letter(f, "f")
    X["s15"] = d
    path = save_plate(fig, fdir / "figS15_controls.png", lang)
    plt.close(fig)
    return {"figS15_controls": str(path)}


# ---------------------------------------------------------------------------
# Leyendas autónomas (captions.json)
# ---------------------------------------------------------------------------
def captions(D, X, variant, lang) -> dict:
    v = tr(f"var_{variant}", lang)
    F = tr("figure", lang)
    a05, p2 = X["a05"], X["p2"]
    est_a05 = "/".join(num(n, 0, lang) for n in a05.n_reporting_establishments)
    est_p2 = "/".join(num(n, 0, lang) for n in p2.n_reporting_establishments)
    unk = X["grd_unknown_res"][variant]
    unk_txt = "/".join(f"{int(unk.get(y, 0))}" for y in CFG.YEARS_GRD)
    rho = num(X.get("s9_rho", np.nan), 2, lang)
    es = {
        "fig4_triangulation": {
            "title": f"{F} 5. Triangulación educativa y benchmarks poblacionales del reconocimiento administrativo del autismo, Chile 2019–2025 — variante {v}",
            "caption": ("(a) Estudiantes autistas en el Programa de Integración Escolar (PIE; stock escolar anual, matrícula nacional): TEA estricto y TEA-Asperger 2019–2023 (Apuntes 60, Tabla 6), serie armonizada TEA + Asperger 2019–2025 (Apuntes 60 hasta 2023; SINACES 2024–2025, marcadores huecos y trazo discontinuo), la cifra armonizada impresa por SINACES 2022–2025 y el autismo en escuelas especiales 2022–2025. "
                        "Discrepancia de 2022: SINACES imprime 42.945 mientras 45.014 − 2.074 = 42.940 coincide con Apuntes 60; se adopta 42.940 (5 estudiantes, 0,01 %). "
                        "(b) JUNAEB (Encuesta de Vulnerabilidad): % de estudiantes con TEA reportado por cuidadores según nivel; 2024 (ponderador EXP_REG) y 2025 (EXP) con IC 95 %; 2023 sin ponderador publicado (marcadores huecos, % no ponderado con IC de Wilson); 2019–2022 sin ítem TEA y 1º medio 2024 con variable vacía se marcan como «no estimable» en la franja inferior, nunca como cero. Cohortes escolares seleccionadas y reporte de cuidadores; no es prevalencia nacional. "
                        "(c) Proporciones ponderadas con diseño complejo (ponderador, estrato y conglomerado; IC 95 % logit-t): ENDIDE 2022 adultos 18+, NNA 2–17 con autismo reportado por el cuidador y reportado con confirmación médica, y ENCAVI 2023–2024 personas 15+ con diagnóstico de TEA, total y por sexo; a la derecha de cada fila, % (IC 95 %); en el rótulo de la fila, casos / n no ponderado del dominio; estimaciones imprecisas (< 30 casos o EE relativo > 30 %) en gris. Escala logarítmica. "
                        f"(d) Índices (primer año común 2021 = 100; escala log) de series con unidades, denominadores y coberturas distintas: GRD F84 en cualquier posición por 100.000 episodios (panel observado), DEIS F84 principal por 100.000 egresos, ingresos A05 por autismo (flujo; establecimientos reportantes 2021–2025: {est_a05}), stock P2 de diciembre (establecimientos 2019–2025: {est_p2}) y PIE armonizado (marcadores huecos y trazo discontinuo 2023–2025 = fuente SINACES, como en a); son índices, no niveles comparables. "
                        "(e) Cinco franjas apiladas, cada una con su propio eje vertical, por 100.000 habitantes INE (base Censo 2017, 30 de junio, población total de todas las edades; residencia): episodios GRD con F84 (variante), personas únicas dentro del año, ingresos A05 y stock P2 de diciembre (numeradores por lugar de atención, red pública; n = establecimientos reportantes) y PIE armonizado. Las barras rayadas son stocks y las llenas flujos, y nunca comparten un eje; el máximo de cada franja está rotulado en su propio eje y las alturas no se comparan entre franjas. "
                        "(f) F84 en posición principal: egresos DEIS (todos los establecimientos y subconjunto SNSS) por 100.000 egresos frente a episodios GRD (panel observado, toda modalidad y hospitalización estricta; n = hospitales) por 100.000 episodios, IC 95 % exacto de Poisson; DEIS no registra diagnósticos secundarios (DIAG2 es causa externa), por lo que el F84 secundario de GRD no tiene equivalente. "
                        "Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto, no como intervención; ambas significan lo mismo en todos los paneles y se rotulan una sola vez, en (a). Las fuentes no se enlazan por persona; los conteos son reconocimiento administrativo, no prevalencia ni incidencia.")},
        "figS9_regional_maps": {
            "title": f"{F} S9. Distribución regional del reconocimiento administrativo: GRD por región de residencia (ambas variantes) y REM A05 por región del establecimiento — variante {v}",
            "caption": (f"(a, b) Episodios GRD 2024 con F84 documentado en cualquier posición por 100.000 habitantes INE (base 2017, 30 de junio) según región de residencia (comuna informada en el GRD, enlazada por nombre normalizado al crosswalk INE; sin enlace difuso), para F84 completo (a) y F84 sin Rett (b); episodios con residencia desconocida excluidos (variante {v}: {unk_txt} en 2019–2024). "
                        "(c) Ingresos REM A05 por autismo estricto (código 05990022) 2024 por 100.000 habitantes según región del establecimiento reportante (lugar de atención; n = establecimientos con fila en la región). Mapas en proyección cónica de igual área (Albers), tres franjas norte–centro–sur con la misma escala métrica; islas oceánicas recortadas. "
                        f"(d) Regiones en 2024: GRD (residencia) frente a A05 (lugar de atención), escalas log; ρ de Spearman = {rho}. "
                        f"(e) GRD (variante {v}) por región de residencia y año 2019–2024. (f) A05 por región del establecimiento y año 2021–2025; bajo cada año, el número de establecimientos reportantes del país (2025: 952 frente a 1.070 en 2024). ADVERTENCIA: REM localiza al prestador y GRD la residencia; los pacientes atendidos fuera de su región de residencia (p. ej. derivaciones a la Región Metropolitana) no se corrigen; comparación ecológica que no implica causalidad ni calidad de atención. Conteos administrativos, no prevalencia.")},
        "figS10_denominators": {
            "title": f"{F} S10. Sensibilidad de los denominadores poblacionales: INE base 2017 frente a Censo 2024 y base 2024 — variante {v}",
            "caption": ("(a) Población nacional 2019–2025 según la base de proyección: INE base Censo 2017 al 30 de junio (denominador principal), INE base 2024 al 30 de junio y al 1 de enero (sensibilidad) y población enumerada por el Censo 2024 (18.480.432). (b) Razón base 2024 / base 2017 por año y Censo 2024 / base 2017 en 2024: como cualquier tasa por población es inversamente proporcional al denominador, la razón equivale al cambio relativo de las tasas. "
                        "(c) Razón Censo 2024 / base 2017 por región, 2024 (regiones de norte a sur; línea punteada = razón nacional). (d) Razón por grupo quinquenal OMS, 2024 nacional: base 2024 y Censo 2024 frente a base 2017. "
                        f"(e) Episodios GRD 2024 con F84 documentado (variante {v}, panel observado, toda modalidad, cualquier posición; episodios sin edad válida excluidos) por 100.000 habitantes según grupo de edad con los tres denominadores (escala log). "
                        f"(f) Episodios GRD 2024 (variante {v}) por región de residencia por 100.000 habitantes con base 2017 (IC 95 % exacto de Poisson) frente a Censo 2024 (estrellas). "
                        "Las bases nunca se combinan en una misma serie; el Censo 2024 es población enumerada (no proyección a mitad de año) y las diferencias reflejan revisiones de migración, omisión censal y estructura etaria. Numeradores por lugar de atención (red pública) frente a denominadores de residencia. Conteos administrativos, no prevalencia.")},
        "figS11_coverage_age_sex": {
            "title": f"{F} S11. Capas de cobertura: FONASA, inscritos APS e ISAPRE por edad y sexo (2025) y series nacionales 2019–2025 — variante {v}",
            "caption": ("(a) Beneficiarios FONASA a diciembre de 2025 por grupo quinquenal y sexo (agregados oficiales por comuna sumados a nivel nacional; sexo indeterminado y edad sin información excluidos de la pirámide). (b) Inscritos validados en APS a diciembre de 2025 por banda decenal y sexo (comuna del centro de inscripción, no residencia; 2019–2023 se publican en bandas de 20 años y 2024–2025 en bandas de 10). "
                        "(c) Beneficiarios ISAPRE (cotizantes + cargas) a diciembre de 2025 por grupo quinquenal y sexo (comuna administrativa del beneficiario). (d) Series nacionales 2019–2025: población INE base 2017 (30 de junio), beneficiarios FONASA, inscritos APS (n = centros con inscritos) y beneficiarios ISAPRE, en millones. "
                        "(e) Razón de cada capa frente a la población INE del mismo año: no es una tasa de aseguramiento (mezcla stocks de diciembre con la proyección de junio, omite FF.AA. y otros regímenes, y las geografías —residencia, domicilio/inscripción, centro— difieren). (f) Estructura etaria 2025 (% por banda decenal) de INE, FONASA, APS e ISAPRE: las diferencias de estructura justifican estandarizar por edad al usar cada capa como denominador. "
                        "Cada capa responde una pregunta distinta (territorial, aseguramiento, cobertura operativa) y ninguna es la población en riesgo de los indicadores; son idénticas en ambas variantes. Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto.")},
        "figS12_junaeb_sex_level": {
            "title": f"{F} S12. JUNAEB: TEA reportado por cuidadores según sexo y nivel escolar, 2023–2025 — variante {v}",
            "caption": ("Encuesta de Vulnerabilidad Estudiantil de JUNAEB (cohortes escolares seleccionadas: parvularia NT1–NT2, 1º básico, 5º básico y 1º medio; reporte de cuidadores con el wording del cuestionario anual). "
                        "(a) 2023: % no ponderado con IC 95 % de Wilson (sin ponderador publicado; barras huecas), por sexo y nivel. (b) 2024: % ponderado con EXP_REG e IC 95 %; 1º medio no estimable (variable TEA completamente vacía), marcado con un cuadro rayado y nunca como cero. (c) 2025: % ponderado con EXP e IC 95 %. "
                        "(d) Razón hombre:mujer del % TEA por nivel y año, con IC 95 % aproximado (método delta en escala log; para 2023 el EE se deriva del IC de Wilson). (e) Estudiantes con respuesta (n no ponderado, miles) por nivel y año 2019–2025, con el número de casos TEA reportados (2019–2022 sin ítem TEA). (f) % ponderado frente a % no ponderado en 2024–2025 (identidad punteada): el ponderador cambia poco las estimaciones. "
                        "Las proporciones describen reporte de cuidadores en cohortes escolares, no prevalencia nacional; idénticas en ambas variantes.")},
        "figS14_deis_sex_age": {
            "title": f"{F} S14. Egresos hospitalarios DEIS con F84 en diagnóstico principal según sexo, edad y pertenencia, 2019–2024 — variante {v}",
            "caption": (f"Egresos DEIS (todos los establecimientos del país) con F84 (variante {v}) en DIAG1 por 100.000 egresos del mismo estrato, IC 95 % exacto de Poisson. DEIS registra DIAG1 (principal) y DIAG2 (causa externa, CIE-10 V01–Y98), que nunca contiene F84: «cualquier posición» = principal. "
                        "(a) Por sexo y año 2019–2024 (ambos sexos en línea discontinua). (b) Por grupo quinquenal OMS en 2021 (layout con edad detallada) y 2024 (canónico); en 2019–2023 el archivo canónico publica bandas decenales. (c) 2024 por sexo y grupo OMS. (d) Tasa por banda decenal armonizada y año. "
                        "(e) Establecimientos SNSS (hospitales públicos) frente a no SNSS (clínicas privadas, FF.AA., mutuales, administración delegada) y registros enmascarados por DEIS. (f) Egresos con F84 principal según pertenencia (apilados) y % SNSS. "
                        "Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto. Egresos son eventos, no personas; conteos administrativos, no prevalencia.")},
        "figS15_controls": {
            "title": f"{F} S15. Controles de reproducción: valores esperados del protocolo frente a valores reproducidos por el pipeline — variante {v}",
            "caption": ("Cada punto es un control numérico de los módulos de fase 1 y 2 (00 procedencia, 01 GRD, 01b DEIS, 02 REM, 03 denominadores, 04 encuestas, 05 educación, 06 modelos, 07 controles), con el valor esperado (brief, DATA_REVIEW.md, manifiestos y config.CONTROLS) y el observado. "
                        "(a) Observado frente a esperado, ejes symlog (los ceros se muestran en el tramo lineal) e identidad punteada; los controles que difieren se rotulan. (b) Diferencia relativa (%) según magnitud esperada (esperado ≠ 0), con la tolerancia ±0,5 % usada para tasas y medias. (c) Número de controles por módulo y estado (coincide, difiere con explicación, informativo sin valor esperado). "
                        "(d) Detalle GRD y DEIS. (e) Detalle REM, denominadores, encuestas, educación y modelos. (f) Listado de los controles que difieren y su explicación: en todos los casos la diferencia es de panel (esperado del panel fijo de 65 frente al panel anual observado de 68/72 hospitales), de identificadores no válidos (1 persona) o de filas repetidas conservadas. "
                        "La tabla es idéntica en ambas variantes porque los controles se definieron sobre la familia F84 completa y el resto de las series no depende de la variante. Ningún control se completó por plausibilidad.")},
    }
    en = {
        "fig4_triangulation": {
            "title": f"{F} 5. Educational triangulation and population benchmarks of administrative autism recognition, Chile 2019–2025 — {v} variant",
            "caption": ("(a) Autistic students in the School Integration Programme (PIE; annual school stock, national enrolment): strict ASD and ASD-Asperger 2019–2023 (Apuntes 60, Table 6), the harmonised ASD + Asperger series 2019–2025 (Apuntes 60 to 2023; SINACES 2024–2025, hollow markers and dashed line), the harmonised figure as printed by SINACES 2022–2025, and autism in special schools 2022–2025. "
                        "2022 discrepancy: SINACES prints 42,945 while 45,014 − 2,074 = 42,940 matches Apuntes 60; 42,940 is adopted (5 students, 0.01%). "
                        "(b) JUNAEB (Student Vulnerability Survey): % of students with caregiver-reported ASD by level; 2024 (EXP_REG weight) and 2025 (EXP) with 95% CIs; 2023 has no published weight (hollow markers, unweighted % with Wilson CI); 2019–2022 have no ASD item and Grade 9 in 2024 has an empty variable, both marked 'not estimable' in the lower strip and never as zero. Selected school cohorts and caregiver report; not national prevalence. "
                        "(c) Design-based weighted proportions (weight, stratum and cluster; logit-t 95% CIs): ENDIDE 2022 adults 18+, children 2–17 with caregiver-reported autism and with physician-confirmed report, and ENCAVI 2023–2024 persons 15+ with an ASD diagnosis, total and by sex; to the right of each row, % (95% CI); in the row label, cases / unweighted domain n; imprecise estimates (< 30 cases or relative SE > 30%) in grey. Log scale. "
                        f"(d) Indices (first common year 2021 = 100; log scale) of series with different units, denominators and coverage: GRD F84 in any position per 100,000 episodes (observed panel), DEIS principal F84 per 100,000 discharges, A05 autism entries (flow; reporting establishments 2021–2025: {est_a05}), P2 December stock (establishments 2019–2025: {est_p2}) and harmonised PIE (hollow markers and dashed line 2023–2025 = SINACES source, as in a); these are indices, not comparable levels. "
                        "(e) Five stacked strips, each with its own vertical axis, per 100,000 INE population (2017 Census base, 30 June, total population of all ages; residence): GRD episodes with F84 (variant), unique persons within the year, A05 entries and the P2 December stock (numerators by place of care, public network; n = reporting establishments) and harmonised PIE. Hatched bars are stocks and solid bars flows, and they never share an axis; each strip's maximum is labelled on its own axis and heights are not compared across strips. "
                        "(f) F84 in the principal position: DEIS discharges (all establishments and the SNSS subset) per 100,000 discharges against GRD episodes (observed panel, all activity and strict hospitalisation; n = hospitals) per 100,000 episodes, exact 95% Poisson CIs; DEIS does not record secondary diagnoses (DIAG2 is the external cause), so secondary F84 in GRD has no equivalent. "
                        "Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context, not as an intervention; both mean the same in every panel and are labelled once, in (a). Sources are not person-linked; counts are administrative recognition, not prevalence or incidence.")},
        "figS9_regional_maps": {
            "title": f"{F} S9. Regional distribution of administrative recognition: GRD by region of residence (both variants) and REM A05 by region of establishment — {v} variant",
            "caption": (f"(a, b) GRD episodes in 2024 with documented F84 in any position per 100,000 INE population (base 2017, 30 June) by region of residence (comuna recorded in the GRD, linked by normalised name to the INE crosswalk; no fuzzy matching), for the full F84 family (a) and F84 without Rett (b); episodes with unknown residence excluded ({v} variant: {unk_txt} in 2019–2024). "
                        "(c) REM A05 entries for strict autism (code 05990022) in 2024 per 100,000 population by region of the reporting establishment (place of care; n = establishments with a row in the region). Maps in an equal-area conic projection (Albers), three north–centre–south strips at the same metric scale; oceanic islands clipped. "
                        f"(d) Regions in 2024: GRD (residence) vs A05 (place of care), log scales; Spearman ρ = {rho}. "
                        f"(e) GRD ({v} variant) by region of residence and year 2019–2024. (f) A05 by region of establishment and year 2021–2025; under each year, the national number of reporting establishments (2025: 952 vs 1,070 in 2024). WARNING: REM locates the provider and GRD the residence; patients treated outside their region of residence (e.g. referrals to the Metropolitan Region) are not corrected; an ecological comparison implying neither causality nor quality of care. Administrative counts, not prevalence.")},
        "figS10_denominators": {
            "title": f"{F} S10. Sensitivity of population denominators: INE base 2017 vs Census 2024 and base 2024 — {v} variant",
            "caption": ("(a) National population 2019–2025 by projection base: INE base Census 2017 at 30 June (primary denominator), INE base 2024 at 30 June and 1 January (sensitivity) and the population enumerated by the 2024 Census (18,480,432). (b) Ratio base 2024 / base 2017 by year and Census 2024 / base 2017 in 2024: since any population rate is inversely proportional to its denominator, the ratio equals the relative change in rates. "
                        "(c) Ratio Census 2024 / base 2017 by region, 2024 (regions north to south; dotted line = national ratio). (d) Ratio by WHO five-year age group, 2024 national: base 2024 and Census 2024 against base 2017. "
                        f"(e) GRD episodes in 2024 with documented F84 ({v} variant, observed panel, all activity, any position; episodes without valid age excluded) per 100,000 population by age group under the three denominators (log scale). "
                        f"(f) GRD episodes 2024 ({v} variant) by region of residence per 100,000 population with base 2017 (exact Poisson 95% CI) vs Census 2024 (stars). "
                        "Bases are never combined within one series; the 2024 Census is an enumerated population (not a mid-year projection) and differences reflect migration revisions, census omission and age structure. Place-of-care numerators (public network) against residence denominators. Administrative counts, not prevalence.")},
        "figS11_coverage_age_sex": {
            "title": f"{F} S11. Coverage layers: FONASA, APS enrolment and ISAPRE by age and sex (2025) and national series 2019–2025 — {v} variant",
            "caption": ("(a) FONASA beneficiaries at December 2025 by five-year age group and sex (official comuna aggregates summed nationally; undetermined sex and unknown age excluded from the pyramid). (b) Validated APS enrolment at December 2025 by 10-year band and sex (comuna of the enrolment centre, not residence; 2019–2023 are published in 20-year bands and 2024–2025 in 10-year bands). "
                        "(c) ISAPRE beneficiaries (contributors + dependants) at December 2025 by five-year group and sex (administrative comuna of the beneficiary). (d) National series 2019–2025: INE population base 2017 (30 June), FONASA beneficiaries, APS enrolment (n = centres with enrolees) and ISAPRE beneficiaries, in millions. "
                        "(e) Ratio of each layer to the INE population of the same year: not an insurance-coverage rate (it mixes December stocks with the June projection, omits the armed forces and other regimes, and the geographies — residence, domicile/enrolment, centre — differ). (f) Age structure in 2025 (% by 10-year band) of INE, FONASA, APS and ISAPRE: structural differences justify age standardisation when a layer is used as a denominator. "
                        "Each layer answers a different question (territorial, insurance, operational coverage) and none is the population at risk of the indicators; identical in both variants. Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context.")},
        "figS12_junaeb_sex_level": {
            "title": f"{F} S12. JUNAEB: caregiver-reported ASD by sex and school level, 2023–2025 — {v} variant",
            "caption": ("JUNAEB Student Vulnerability Survey (selected school cohorts: pre-school NT1–NT2, Grade 1, Grade 5 and Grade 9; caregiver report with the wording of each annual questionnaire). "
                        "(a) 2023: unweighted % with Wilson 95% CI (no published weight; hollow bars), by sex and level. (b) 2024: weighted % with EXP_REG and 95% CI; Grade 9 not estimable (ASD variable entirely empty), marked with a hatched square and never as zero. (c) 2025: weighted % with EXP and 95% CI. "
                        "(d) Male:female ratio of the ASD % by level and year, with approximate 95% CI (delta method on the log scale; for 2023 the SE is derived from the Wilson CI). (e) Students with a response (unweighted n, thousands) by level and year 2019–2025, with the number of reported ASD cases (2019–2022 had no ASD item). (f) Weighted vs unweighted % in 2024–2025 (dotted identity): weighting changes the estimates little. "
                        "Proportions describe caregiver report in school cohorts, not national prevalence; identical in both variants.")},
        "figS14_deis_sex_age": {
            "title": f"{F} S14. DEIS hospital discharges with F84 as principal diagnosis by sex, age and ownership, 2019–2024 — {v} variant",
            "caption": (f"DEIS discharges (all establishments in the country) with F84 ({v} variant) in DIAG1 per 100,000 discharges of the same stratum, exact Poisson 95% CI. DEIS records DIAG1 (principal) and DIAG2 (external cause, ICD-10 V01–Y98), which never contains F84: 'any position' = principal. "
                        "(a) By sex and year 2019–2024 (both sexes dashed). (b) By WHO five-year age group in 2021 (detailed-age layout) and 2024 (canonical); the canonical files publish 10-year bands in 2019–2023. (c) 2024 by sex and WHO age group. (d) Rate by harmonised 10-year band and year. "
                        "(e) SNSS establishments (public hospitals) vs non-SNSS (private clinics, armed forces, mutual insurers, delegated administration) and records masked by DEIS. (f) Discharges with principal F84 by ownership (stacked) and % SNSS. "
                        "Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context. Discharges are events, not persons; administrative counts, not prevalence.")},
        "figS15_controls": {
            "title": f"{F} S15. Reproduction controls: pre-specified protocol values vs values reproduced by the pipeline — {v} variant",
            "caption": ("Each point is a numeric control from the phase-1 and phase-2 modules (00 provenance, 01 GRD, 01b DEIS, 02 REM, 03 denominators, 04 surveys, 05 education, 06 models, 07 controls), with the expected value (brief, DATA_REVIEW.md, manifests and config.CONTROLS) and the observed value. "
                        "(a) Observed vs expected on symlog axes (zeros shown in the linear segment) with the dotted identity; controls that differ are labelled. (b) Relative difference (%) by expected magnitude (expected ≠ 0), with the ±0.5% tolerance used for rates and means. (c) Number of controls per module and status (matches, differs with explanation, informative without an expected value). "
                        "(d) GRD and DEIS detail. (e) REM, denominators, surveys, education and models detail. (f) List of the controls that differ and their explanation: in every case the difference is a panel issue (expected from the fixed panel of 65 vs the observed annual panel of 68/72 hospitals), invalid identifiers (1 person) or repeated rows kept. "
                        "The table is identical in both variants because the controls were defined on the full F84 family and the other series do not depend on the variant. No control was filled in by plausibility.")},
    }
    return es if lang == "es" else en


# ---------------------------------------------------------------------------
# Tablas (formateadas + numéricas) y titles.json
# ---------------------------------------------------------------------------
SERIES_LABEL = {
    "grd_episodes_f84_any": {"es": "GRD: episodios con F84 documentado (cualquier posición)", "en": "GRD: episodes with documented F84 (any position)"},
    "grd_persons_within_year_f84_any": {"es": "GRD: personas únicas dentro del año con F84", "en": "GRD: unique persons within the year with F84"},
    "a05_autism_entries": {"es": "REM A05: ingresos por autismo estricto (05990022)", "en": "REM A05: strict-autism entries (05990022)"},
    "p2_asd_december_stock": {"es": "REM P2: TEA bajo control, diciembre (P2500500)", "en": "REM P2: ASD under control, December (P2500500)"},
    "pie_harmonised_stock": {"es": "PIE armonizado TEA + Asperger (stock escolar)", "en": "Harmonised PIE ASD + Asperger (school stock)"},
}
UNIT_LABEL = {
    "grd_episodes_f84_any": {"es": "episodios (flujo)", "en": "episodes (flow)"}, "grd_persons_within_year_f84_any": {"es": "personas/año (flujo)", "en": "persons/year (flow)"},
    "a05_autism_entries": {"es": "ingresos (flujo)", "en": "entries (flow)"}, "p2_asd_december_stock": {"es": "personas en diciembre (stock)", "en": "persons in December (stock)"},
    "pie_harmonised_stock": {"es": "estudiantes (stock)", "en": "students (stock)"},
}


def rate_str(r, lo, hi, dec, lang):
    return "—" if pd.isna(r) else f"{num(r, dec, lang)} ({C.fmt_ci(lo, hi, dec, lang)})"


@timed("tables")
def write_tables(D, X, variant, lang) -> dict:
    tdir = out_dir(variant, lang, "tables")
    T = tr("table", lang)
    v = tr(f"var_{variant}", lang)
    titles = {}
    # F4 series
    pp = X["per_pop"]; pp = pp[pp.variant.isin([variant, "both"])].copy()
    ft = pd.DataFrame({
        tr("series", lang): pp.series.map(lambda s: SERIES_LABEL[s][lang]), tr("year", lang): pp.year.astype(int),
        tr("value", lang): pp.value.map(lambda x: num(x, 0, lang)), tr("unit", lang): pp.series.map(lambda s: UNIT_LABEL[s][lang]),
        tr("reporting_n", lang): pp.reporting_n.map(lambda x: "—" if pd.isna(x) else num(x, 0, lang)),
        tr("denominator", lang): pp.denominator.map(lambda x: num(x, 0, lang)),
        tr("rate_100k", lang): [rate_str(r.rate, r.rate_lo, r.rate_hi, 1, lang) for r in pp.itertuples()],
    })
    C.atomic_write_csv(ft, tdir / "F4_triangulation_series.csv"); C.atomic_write_csv(pp, tdir / "F4_triangulation_series_numeric.csv")
    titles["F4_triangulation_series"] = {
        "title": {"es": f"{T} S9. Series de la {main_figure_label('fig4_triangulation', 'es')} por 100.000 habitantes: GRD, REM A05, REM P2 y PIE, 2019–2025 — variante {v}",
                  "en": f"{T} S9. {main_figure_label('fig4_triangulation', 'en')} series per 100,000 population: GRD, REM A05, REM P2 and PIE, 2019–2025 — {v} variant"}[lang],
        "note": {"es": "Denominador: población residente INE base Censo 2017 al 30 de junio, todas las edades (residencia). Numeradores: episodios GRD con F84 documentado y personas únicas dentro del año (panel observado: 65/65/65/65/68/72 hospitales; toda modalidad; lugar de atención), ingresos A05 por autismo estricto (era 2021–2025) y stock P2 de diciembre (nunca sumado con junio) con el número de establecimientos reportantes, y PIE armonizado (Apuntes 60 2019–2023; SINACES 2024–2025; la versión numérica añade la tasa por 100.000 habitantes de 5–19 años). IC 95 % exacto de Poisson con denominador fijo. Flujos y stocks se listan con su unidad y no son comparables entre sí; conteos administrativos, no prevalencia.",
                 "en": "Denominator: INE resident population, base Census 2017, 30 June, all ages (residence). Numerators: GRD episodes with documented F84 and unique persons within the year (observed panel: 65/65/65/65/68/72 hospitals; all activity; place of care), A05 strict-autism entries (2021–2025 era) and P2 December stock (never summed with June) with the number of reporting establishments, and harmonised PIE (Apuntes 60 2019–2023; SINACES 2024–2025; the numeric version adds the rate per 100,000 residents aged 5–19). Exact Poisson 95% CI with fixed denominator. Flows and stocks are listed with their unit and are not comparable with each other; administrative counts, not prevalence."}[lang]}
    # S9 regional
    R = X["regional"]
    rows = []
    popr = ine_region_year(D)
    for reg in REGION_ORDER:
        g = {vv: R[(R.source == "grd_f84_any_residence") & (R.variant == vv) & (R.year == 2024) & (R.cut_region == reg)] for vv in VARIANTS}
        a = R[(R.source == "a05_autism_entries_establishment") & (R.year == 2024) & (R.cut_region == reg)]
        row = {tr("region", lang): REGION_NAMES[reg], tr("population", lang): num(popr.loc[reg, 2024], 0, lang)}
        for vv in VARIANTS:
            z = g[vv]
            row[f"{tr('grd_ep_2024', lang)} · {tr('var_' + vv, lang)}"] = "—" if z.empty else num(z["count"].iloc[0], 0, lang)
            row[f"{tr('rate_100k', lang)} · GRD {tr('var_' + vv, lang)}"] = "—" if z.empty else rate_str(z.rate.iloc[0], z.rate_lo.iloc[0], z.rate_hi.iloc[0], 1, lang)
        row[tr("a05_2024", lang)] = "—" if a.empty else num(a["count"].iloc[0], 0, lang)
        row[tr("estab", lang)] = "—" if a.empty else num(a.reporting_n.iloc[0], 0, lang)
        row[f"{tr('rate_100k', lang)} · A05"] = "—" if a.empty else rate_str(a.rate.iloc[0], a.rate_lo.iloc[0], a.rate_hi.iloc[0], 1, lang)
        rows.append(row)
    C.atomic_write_csv(pd.DataFrame(rows), tdir / "S9_regional_rates.csv"); C.atomic_write_csv(R, tdir / "S9_regional_rates_numeric.csv")
    unk = X["grd_unknown_res"]
    titles["S9_regional_rates"] = {
        "title": {"es": f"{T} S10. Tasas regionales 2024 por 100.000 habitantes: episodios GRD con F84 por región de residencia (ambas variantes) e ingresos REM A05 por región del establecimiento — variante {v}",
                  "en": f"{T} S10. Regional rates 2024 per 100,000 population: GRD episodes with F84 by region of residence (both variants) and REM A05 entries by region of establishment — {v} variant"}[lang],
        "note": {"es": f"Denominador: población INE base 2017 al 30 de junio de 2024 por región de residencia. GRD: episodios 2024 con F84 en cualquier posición (panel observado de 72 hospitales, toda modalidad) según la comuna de residencia informada, enlazada por nombre normalizado al crosswalk INE (alias explícitos, sin enlace difuso); episodios con residencia desconocida excluidos (F84 completo: {int(unk['con_rett'].get(2024, 0))}; sin Rett: {int(unk['sin_rett'].get(2024, 0))} en 2024). REM A05: ingresos por autismo estricto (05990022) en 2024 según la región del establecimiento reportante (lugar de atención), con el número de establecimientos con fila. IC 95 % exacto de Poisson. Residencia y lugar de atención no son comparables sin corregir flujos interregionales; la versión numérica contiene todos los años (GRD 2019–2024; A05 2021–2025). Conteos administrativos, no prevalencia.",
                 "en": f"Denominator: INE base-2017 population at 30 June 2024 by region of residence. GRD: 2024 episodes with F84 in any position (observed panel of 72 hospitals, all activity) by recorded comuna of residence, linked by normalised name to the INE crosswalk (explicit aliases, no fuzzy matching); episodes with unknown residence excluded (full F84: {int(unk['con_rett'].get(2024, 0))}; without Rett: {int(unk['sin_rett'].get(2024, 0))} in 2024). REM A05: strict-autism entries (05990022) in 2024 by region of the reporting establishment (place of care), with the number of establishments with a row. Exact Poisson 95% CI. Residence and place of care are not comparable without correcting inter-regional flows; the numeric version contains all years (GRD 2019–2024; A05 2021–2025). Administrative counts, not prevalence."}[lang]}
    # S10 denominadores
    cmp_ = D["ine_cmp"].sort_values("year")
    st = pd.DataFrame({
        tr("year", lang): cmp_.year.astype(int),
        tr("base2017", lang): cmp_.base2017_national_30jun.map(lambda x: num(x, 0, lang)),
        tr("base2024_jun", lang): cmp_.base2024_national_30jun.map(lambda x: num(x, 0, lang)),
        tr("base2024_jan", lang): cmp_.base2024_national_1jan.map(lambda x: num(x, 0, lang)),
        tr("censo2024", lang): cmp_.censo2024_enumerated.map(lambda x: "—" if pd.isna(x) else num(x, 0, lang)),
        tr("r_base2024", lang): cmp_.ratio_base2024_to_base2017_30jun.map(lambda x: num(x, 4, lang)),
        tr("r_censo", lang): cmp_.ratio_censo2024_to_base2017.map(lambda x: "—" if pd.isna(x) else num(x, 4, lang)),
    })
    C.atomic_write_csv(st, tdir / "S10_denominator_sensitivity.csv")
    numeric = cmp_.copy()
    age = X.get("s10_age_rates")
    if age is not None:
        for b in ["base2017", "base2024_30jun", "censo2024"]:
            age[f"rate_per_100k_{b}"] = 1e5 * age.count_2024 / age[b]
        C.atomic_write_csv(age, tdir / "S10_denominator_sensitivity_age_numeric.csv")
    C.atomic_write_csv(numeric, tdir / "S10_denominator_sensitivity_numeric.csv")
    titles["S10_denominator_sensitivity"] = {
        "title": {"es": f"{T} S11. Sensibilidad de los denominadores nacionales: INE base 2017 frente a base 2024 y Censo 2024, 2019–2025 — variante {v}",
                  "en": f"{T} S11. Sensitivity of national denominators: INE base 2017 vs base 2024 and Census 2024, 2019–2025 — {v} variant"}[lang],
        "note": {"es": "INE base Censo 2017 al 30 de junio es el denominador principal de todas las tasas por población; base 2024 (30 de junio y 1 de enero) y la población enumerada por el Censo 2024 son sensibilidades puente y nunca se combinan en una misma serie. La razón de denominadores equivale al factor inverso de las tasas (una razón de 0,92 aumenta cualquier tasa por población en 8,7 %). La tabla numérica de edad (…_age_numeric) da los episodios GRD 2024 con F84 documentado por grupo quinquenal y la tasa con cada denominador. Idéntica en ambas variantes salvo la tabla de edad.",
                 "en": "INE base Census 2017 at 30 June is the primary denominator of every population rate; base 2024 (30 June and 1 January) and the population enumerated by the 2024 Census are bridge sensitivities and are never combined within one series. The denominator ratio equals the inverse factor of the rates (a ratio of 0.92 raises any population rate by 8.7%). The age numeric table (…_age_numeric) gives GRD 2024 episodes with documented F84 by five-year group and the rate under each denominator. Identical in both variants except the age table."}[lang]}
    # S11 cobertura por edad (decenal) y sexo 2025
    a10 = X["s11_age10"]
    sa = X["s11_sex_age"]
    rows = []
    for band in BANDS_10:
        fon = sa["fonasa"].copy(); fon["b10"] = fon.age_band_5y.map(to_10y)
        isa = sa["isapre"].copy(); isa["b10"] = isa.age_band_5y.map(to_10y)
        aps = sa["aps"]
        for sex in ["HOMBRE", "MUJER"]:
            rows.append({tr("age_band", lang): band, tr("sex", lang): tr(sex, lang),
                         tr("fonasa", lang): num(fon[(fon.b10 == band) & (fon.sex == sex)].beneficiaries.sum(), 0, lang),
                         tr("aps", lang): num(aps[(aps.age_band_10y == band) & (aps.sex == sex)].enrolled.sum(), 0, lang),
                         tr("isapre", lang): num(isa[(isa.b10 == band) & (isa.sex == sex)].beneficiarios.sum(), 0, lang)})
        rows.append({tr("age_band", lang): band, tr("sex", lang): tr("TOTAL", lang), tr("fonasa", lang): num(a10.loc[band, "fonasa"], 0, lang), tr("aps", lang): num(a10.loc[band, "aps"], 0, lang),
                     tr("isapre", lang): num(a10.loc[band, "isapre"], 0, lang), tr("ine", lang): num(a10.loc[band, "ine"], 0, lang),
                     tr("share_ine", lang) + " FONASA": num(100 * a10.loc[band, "fonasa"] / a10.loc[band, "ine"], 1, lang), tr("share_ine", lang) + " ISAPRE": num(100 * a10.loc[band, "isapre"] / a10.loc[band, "ine"], 1, lang)})
    C.atomic_write_csv(pd.DataFrame(rows), tdir / "S11_coverage_age_sex.csv")
    C.atomic_write_csv(a10.reset_index().rename(columns={"index": "age_band_10y"}), tdir / "S11_coverage_age_sex_numeric.csv")
    titles["S11_coverage_age_sex"] = {
        "title": {"es": f"{T} S12. Capas de cobertura a diciembre de 2025 según banda decenal de edad y sexo: FONASA, inscritos APS, ISAPRE y población INE — variante {v}",
                  "en": f"{T} S12. Coverage layers at December 2025 by 10-year age band and sex: FONASA, APS enrolment, ISAPRE and INE population — {v} variant"}[lang],
        "note": {"es": "Stocks de diciembre de 2025 (FONASA beneficiarios por comuna sumados a nivel nacional; inscritos APS validados, comuna del centro; beneficiarios ISAPRE = cotizantes + cargas, comuna administrativa) frente a la población INE base 2017 al 30 de junio de 2025 (residencia). Los totales por sexo excluyen sexo indeterminado y edad sin información; las bandas quinquenales de FONASA e ISAPRE se agregan a decenales para alinearlas con APS 2025. El % de la población INE no es una tasa de aseguramiento (geografías y fechas de referencia distintas; otros regímenes omitidos). Idéntica en ambas variantes.",
                 "en": "December 2025 stocks (FONASA beneficiaries by comuna summed nationally; validated APS enrolment, comuna of the centre; ISAPRE beneficiaries = contributors + dependants, administrative comuna) against the INE base-2017 population at 30 June 2025 (residence). Sex totals exclude undetermined sex and unknown age; FONASA and ISAPRE five-year groups are aggregated to 10-year bands to align with APS 2025. The % of INE population is not an insurance-coverage rate (different geographies and reference dates; other regimes omitted). Identical in both variants."}[lang]}
    # S12 JUNAEB
    jun = D["jun"].sort_values(["year", "level", "sex"])
    jt = pd.DataFrame({
        tr("year", lang): jun.year.astype(int), tr("level", lang): jun.level.map(lambda lv: tr(f"jun_{lv}", lang)), tr("sex", lang): jun.sex.map(lambda s: tr(s, lang)),
        tr("n_students", lang): jun.n_students.map(lambda x: num(x, 0, lang)), tr("n_tea", lang): jun.n_tea_unweighted.map(lambda x: "—" if pd.isna(x) else num(x, 0, lang)),
        tr("unweighted_pct", lang): [rate_str(r.proportion_unweighted_pct, r.lo_unweighted_pct, r.hi_unweighted_pct, 2, lang) for r in jun.itertuples()],
        tr("weighted_pct", lang): [rate_str(r.proportion_weighted_pct, r.lo_pct, r.hi_pct, 2, lang) for r in jun.itertuples()],
        tr("estimator", lang): jun.weight_variable.map(lambda w: "—" if w == "ABSENT" else w),
        tr("estimable", lang): jun.estimable.map(lambda e: {"yes": tr("yes", lang), "no": tr("not_estimable", lang), "unweighted_only": tr("s12_f_x", lang).lower()}.get(e, e)),
    })
    C.atomic_write_csv(jt, tdir / "S12_junaeb_sex_level.csv")
    C.atomic_write_csv(pd.concat([jun.drop(columns=[c for c in ["item_wording", "filter_wording", "note", "design_note", "grades_in_file"] if c in jun.columns])], axis=1), tdir / "S12_junaeb_sex_level_numeric.csv")
    if "s12_ratio" in X:
        C.atomic_write_csv(X["s12_ratio"], tdir / "S12_junaeb_sex_level_ratio_numeric.csv")
    titles["S12_junaeb_sex_level"] = {
        "title": {"es": f"{T} S13. JUNAEB: estudiantes con TEA reportado por cuidadores según año, nivel y sexo, 2019–2025 — variante {v}",
                  "en": f"{T} S13. JUNAEB: students with caregiver-reported ASD by year, level and sex, 2019–2025 — {v} variant"}[lang],
        "note": {"es": "Encuesta de Vulnerabilidad Estudiantil (cohortes escolares seleccionadas; reporte de cuidadores con el wording anual). 2019–2022: el cuestionario no incluye categoría TEA (no estimable). 2023: sin ponderador publicado (solo % no ponderado con IC de Wilson; no es estimación nacional). 2024: ponderador EXP_REG; 1º medio no estimable porque la variable TEA está completamente vacía (no es cero). 2025: ponderador EXP. IC 95 % de los % ponderados por linealización con el ponderador. No es prevalencia; idéntica en ambas variantes.",
                 "en": "Student Vulnerability Survey (selected school cohorts; caregiver report with the annual wording). 2019–2022: the questionnaire has no ASD category (not estimable). 2023: no published weight (unweighted % with Wilson CI only; not a national estimate). 2024: EXP_REG weight; Grade 9 not estimable because the ASD variable is entirely empty (not zero). 2025: EXP weight. 95% CI of weighted % by linearisation with the weight. Not prevalence; identical in both variants."}[lang]}
    # S14 DEIS
    ds = D["dsex"]; ds = ds[(ds.variant == variant) & (ds.source_layout == "canonical") & (ds.level.isin(["total", "sex", "age_band_10"]))].sort_values(["year", "level", "sex", "age_band_10"])
    dt = pd.DataFrame({
        tr("year", lang): ds.year.astype(int), tr("sex", lang): ds.sex.map(lambda s: tr(s, lang) if s in ("HOMBRE", "MUJER", "TOTAL") else s),
        tr("age_band", lang): ds.age_band_10, tr("discharges", lang): ds.discharges_total.map(lambda x: num(x, 0, lang)), tr("f84_diag1", lang): ds.f84_diag1.map(lambda x: num(x, 0, lang)),
        tr("rate_disch", lang): [rate_str(r.rate_per_100k_discharges, r.rate_lo95, r.rate_hi95, 1, lang) for r in ds.itertuples()],
    })
    C.atomic_write_csv(dt, tdir / "S14_deis_sex_age.csv"); C.atomic_write_csv(ds, tdir / "S14_deis_sex_age_numeric.csv")
    titles["S14_deis_sex_age"] = {
        "title": {"es": f"{T} S14. Egresos DEIS con F84 en diagnóstico principal por 100.000 egresos según sexo y banda decenal de edad, 2019–2024 — variante {v}",
                  "en": f"{T} S14. DEIS discharges with F84 as principal diagnosis per 100,000 discharges by sex and 10-year age band, 2019–2024 — {v} variant"}[lang],
        "note": {"es": f"Egresos hospitalarios DEIS de todos los establecimientos (SNSS y no SNSS; filas enmascaradas por DEIS en categoría SUPRIMIDO) con F84 ({v}) en DIAG1; DIAG2 es causa externa y nunca contiene F84, por lo que «cualquier posición» = principal. Tasa por 100.000 egresos del mismo estrato con IC 95 % exacto de Poisson; bandas decenales armonizadas (80+ funde los grupos superiores). Egresos son eventos, no personas; conteos administrativos, no prevalencia.",
                 "en": f"DEIS hospital discharges from all establishments (SNSS and non-SNSS; rows masked by DEIS in the SUPPRESSED category) with F84 ({v}) in DIAG1; DIAG2 is the external cause and never contains F84, so 'any position' = principal. Rate per 100,000 discharges of the same stratum with exact Poisson 95% CI; harmonised 10-year bands (80+ merges the upper groups). Discharges are events, not persons; administrative counts, not prevalence."}[lang]}
    # S15 controles
    d = X["s15"].sort_values(["module", "name", "key"])
    ct = pd.DataFrame({
        tr("module", lang): d.module.map(lambda m: tr(f"mod_{m}", lang) if f"mod_{m}" in LBL else m), tr("control", lang): d.name, tr("key", lang): d.key,
        tr("col_expected", lang): d.expected_num.map(lambda x: num(x, 0 if float(x).is_integer() else 4, lang)), tr("col_observed", lang): d.observed_num.map(lambda x: num(x, 0 if float(x).is_integer() else 4, lang)),
        tr("rel_diff", lang): d.rel_pct.map(lambda x: "—" if pd.isna(x) else num(x, 3, lang)),
        tr("status", lang): d.status.map(lambda s: tr(f"status_{s}", lang)),
        tr("explanation", lang): [explain(r.name, lang) if r.status == "differs" else "" for r in d.itertuples()],
    })
    C.atomic_write_csv(ct, tdir / "S15_controls_scatter.csv"); C.atomic_write_csv(d.drop(columns=["expected", "observed"]), tdir / "S15_controls_scatter_numeric.csv")
    titles["S15_controls_scatter"] = {
        "title": {"es": f"{T} S15. Controles numéricos de reproducción usados en la Figura S15: esperado, observado, diferencia relativa y estado, según módulo — variante {v}",
                  "en": f"{T} S15. Numeric reproduction controls used in Figure S15: expected, observed, relative difference and status, by module — {v} variant"}[lang],
        "note": {"es": f"Filas numéricas con estado «coincide» o «difiere» de los archivos <módulo>_controls.csv de fase 1 y 2 ({len(d)} controles; los informativos sin valor esperado se excluyen). Esperado = valores preespecificados (brief, DATA_REVIEW.md, manifiestos, config.CONTROLS); observado = valor reproducido por el módulo. Diferencias explicadas: panel fijo de 65 frente a panel observado (68/72 hospitales en 2023–2024), episodios F84 sin identificador válido (1 persona) y filas repetidas conservadas. Idéntica en ambas variantes.",
                 "en": f"Numeric rows with status 'matches' or 'differs' from the phase-1 and phase-2 <module>_controls.csv files ({len(d)} controls; informative rows without an expected value are excluded). Expected = pre-specified values (brief, DATA_REVIEW.md, manifests, config.CONTROLS); observed = value reproduced by the module. Explained differences: fixed panel of 65 vs observed panel (68/72 hospitals in 2023–2024), F84 episodes without a valid identifier (1 person) and repeated rows kept. Identical in both variants."}[lang]}
    merge_json(tdir / "titles.json", titles)
    return titles


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh-grd", action="store_true", help="relee los GRD anuales para la tabla de residencia (S9)")
    parser.add_argument("--variants", nargs="*", default=VARIANTS)
    parser.add_argument("--langs", nargs="*", default=LANGS)
    args = parser.parse_args()
    ctl = Controls()
    D = load_all(args.refresh_grd, ctl)
    X = derive(D, ctl)
    # controles adicionales de entrada
    edu = D["edu"].set_index("year")
    for y, val in CFG.CONTROLS["pie_harmonised"].items():
        ctl.add("pie_harmonised_used_in_F4", str(y), val, int(edu.loc[y, "pie_harmonised_n"]), "education_summary_year.pie_harmonised_n")
    for y, val in CFG.CONTROLS["p2_tea_december"].items():
        ctl.add("p2_december_used_in_F4", str(y), val, int(X["p2"].loc[y, "total"]), "rem_pathway_annual P2500500 diciembre")
    for y, val in CFG.CONTROLS["p2_establishments_december"].items():
        ctl.add("p2_establishments_used_in_F4", str(y), val, int(X["p2"].loc[y, "n_reporting_establishments"]), "establecimientos reportantes P2 diciembre")
    for y, val in CFG.CONTROLS["a05_autism_entries"].items():
        ctl.add("a05_entries_used_in_F4", str(y), val, int(X["a05"].loc[y, "total"]), "rem_pathway_annual 05990022 suma anual")
    cv = D["conv"]
    for v in VARIANTS:
        z = cv[(cv.variant == v) & (cv.index_base_year == 2021) & (cv.year == 2021)]
        ctl.add("convergence_index_base_year_equals_100", v, 100.0, float(z["index"].round(9).abs().max()), "índice 2021 = 100 en todas las series", tol=1e-9)
    sv = D["surv"]
    ctl.add("survey_rows_flagged_imprecise", "all", None, int(((sv.precision_flag == "imprecise") | (sv.rse > 0.30)).sum()), "filas en gris u omitidas en F4C")
    ctl.add("survey_endide_adults_cases", "72", CFG.CONTROLS["endide_unweighted"]["adults"], int(sv[(sv.module.str.startswith("Adultos")) & (sv.subgroup == "total") & (sv.estimate_type == "primary")].cases.iloc[0]), "casos no ponderados usados en F4C")
    ctl.add("survey_encavi_cases", "80", CFG.CONTROLS["encavi_unweighted"]["positive"], int(sv[(sv.survey.str.startswith("ENCAVI")) & (sv.subgroup == "total") & (sv.estimate_type == "primary")].cases.iloc[0]), "casos no ponderados usados en F4C")
    jun = D["jun"]
    ctl.add("junaeb_medio1_2024_not_estimable", "2024|medio1", "no", str(jun[(jun.year == 2024) & (jun.level == "medio1") & (jun.sex == "all")].estimable.iloc[0]), "1º medio 2024 marcado como no estimable (nunca cero)")
    shapes = load_regions_equal_area()
    outputs = {}
    for variant in args.variants:
        for lang in args.langs:
            figs = {}
            figs.update(fig4(D, X, variant, lang))
            figs.update(figS9(D, X, variant, lang, shapes))
            figs.update(figS10(D, X, variant, lang))
            figs.update(figS11(D, X, variant, lang))
            figs.update(figS12(D, X, variant, lang))
            figs.update(figS14(D, X, variant, lang))
            figs.update(figS15(D, X, variant, lang))
            merge_json(out_dir(variant, lang, "figures") / "captions.json", captions(D, X, variant, lang))
            titles = write_tables(D, X, variant, lang)
            outputs[f"{variant}/{lang}"] = dict(figures=figs, tables=sorted(titles))
            log(f"{variant}/{lang}: {len(figs)} láminas, {len(titles)} tablas")
    n_figs = sum(len(o["figures"]) for o in outputs.values())
    ctl.add("figures_written", "all", 7 * len(args.variants) * len(args.langs), n_figs, "láminas por variante × idioma")
    ctrl = ctl.frame()
    C.atomic_write_csv(ctrl, CONTROLS_DIR / f"{MODULE}_controls.csv")
    total = time.perf_counter() - T0
    runlog = dict(module=MODULE, script=SCRIPT, run_utc=datetime.now(timezone.utc).isoformat(), total_seconds=round(total, 1),
                  timings={k: round(v, 1) for k, v in TIMINGS.items()}, outputs=outputs,
                  controls=dict(rows=len(ctrl), ok=int((ctrl.status == "ok").sum()), differs=int((ctrl.status == "differs").sum()), info=int((ctrl.status == "info").sum())),
                  grd_unknown_residence=X["grd_unknown_res_values"], s9_spearman_2024=X.get("s9_rho"))
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    log(f"controles: {runlog['controls']}; runtime {total:.1f} s")
    if (ctrl.status == "differs").any():
        log("controles que difieren:\n" + ctrl[ctrl.status == "differs"].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
