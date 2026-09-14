#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""09a_tables_main.py — Tablas principales T1–T7 del plan de láminas y tablas (figure_table_plan.md), por variante e idioma.

Entradas (outputs/tidy/): data_provenance.csv, provenance_summary_by_source.csv, grd_year_summary.csv, grd_subcode_year.csv,
grd_fixed_panel_hospitals.csv, models_population_rates.csv, rem_pathway_annual.csv, coverage_layers_year.csv, aps_panel.csv,
rem20_panel.csv, isapre_beneficiaries_national_year.csv, fonasa_beneficiaries_national_year.csv, fonasa_schema_by_year.csv,
ine_population_base_comparison.csv, survey_estimates.csv, education_summary_year.csv, junaeb_tea_year_level.csv, pie_series.csv,
models_summary.csv (opcional: si falta, la T7 se escribe como esqueleto con dependencia declarada).

Salidas, por variante (con_rett, sin_rett) e idioma (es, en), en outputs/<variante>/<idioma>/tables/:
  T1_sources.csv                  fuentes, unidades, cobertura, quiebres y enlace (+ T1_sources_numeric.csv)
  T2_grd_core.csv                 GRD anual con todas las sensibilidades (+ _numeric)
  T3_rem_pathway.csv              ruta administrativa REM por módulo/código/era, con establecimientos reportantes (+ _numeric)
  T4_denominators_coverage.csv    capas de denominador y cobertura por año (+ _numeric)
  T5_survey_benchmarks.csv        benchmarks poblacionales ENDIDE/ENCAVI con diseño complejo (+ _numeric)
  T6_education.csv                triangulación educativa PIE/SINACES y JUNAEB (+ _numeric)
  T7_models.csv                   modelos preespecificados: CPA e IC por estimando y sensibilidad (+ _numeric)
  titles.json                     entradas {nombre: {title, note}} fusionadas con las de otros módulos
Además: outputs/controls/09a_tables_main_controls.csv y outputs/controls/09a_tables_main_runlog.json.

Reglas: los conteos son reconocimiento administrativo (nunca prevalencia ni incidencia); GRD = «episodios con F84 documentado»
(F84 principal como serie separada); las series REM se presentan por era de definición con el número de establecimientos
reportantes; Serie P usa diciembre (junio solo como sensibilidad, nunca sumados); stocks y flujos no se mezclan; lugar de
atención y residencia no se mezclan sin nota; 2020–2021 = disrupción del reporte; Ley 21.545 (marzo 2023) = contexto.
Ejecución: `python3 study/pipeline/09a_tables_main.py` desde la raíz del repositorio. No modifica config/common/labels.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402

MODULE = "09a_tables_main"
SCRIPT = "study/pipeline/09a_tables_main.py"
CONTROLS_DIR = CFG.OUT / "controls"
VARIANTS = ["con_rett", "sin_rett"]
LANGS = list(CFG.LANGUAGES)
YEARS_GRD = list(CFG.YEARS_GRD)
YEARS_REM = list(CFG.YEARS_REM)
OTHER_VARIANT = {"con_rett": "sin_rett", "sin_rett": "con_rett"}
T_START = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Rótulos bilingües: toda cadena visible en tablas, títulos y notas sale de aquí (ninguna literal suelta)
# ---------------------------------------------------------------------------
LBL: dict[str, dict[str, str]] = {
    # genéricos
    "dash": {"es": "—", "en": "—"},
    "ne": {"es": "n/e", "en": "n/e"},
    "ne_long": {"es": "no estimable", "en": "not estimable"},
    "not_defined": {"es": "no definido", "en": "not defined"},
    "not_reported": {"es": "no reportado", "en": "not reported"},
    "category_absent": {"es": "categoría ausente", "en": "category absent"},
    "not_published": {"es": "no publicado", "en": "not published"},
    "variable_absent": {"es": "variable ausente", "en": "variable absent"},
    "year": {"es": "Año", "en": "Year"},
    "section": {"es": "Bloque", "en": "Block"},
    "indicator": {"es": "Indicador", "en": "Indicator"},
    "unit": {"es": "Unidad", "en": "Unit"},
    "source_col": {"es": "Fuente (tabla, página)", "en": "Source (table, page)"},
    "n_estab_abbrev": {"es": "n = establecimientos reportantes", "en": "n = reporting establishments"},
    "variant_con_rett": {"es": "F84 completo (incluye síndrome de Rett)", "en": "Full F84 family (including Rett syndrome)"},
    "variant_sin_rett": {"es": "F84 sin síndrome de Rett", "en": "F84 family excluding Rett syndrome"},
    "variant_short_con_rett": {"es": "con Rett", "en": "with Rett"},
    "variant_short_sin_rett": {"es": "sin Rett", "en": "without Rett"},
    "identical_variants": {"es": "Tabla idéntica en las variantes con y sin síndrome de Rett.", "en": "Table identical in the with- and without-Rett variants."},
    "table_word": {"es": "Tabla", "en": "Table"},
    "pandemic_note": {"es": "2020–2021: disrupción del reporte por la pandemia de COVID-19 (no se interpola).", "en": "2020–2021: pandemic (COVID-19) reporting disruption (no interpolation)."},
    "law_note": {"es": "La Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con efecto causal identificable.", "en": "Law 21.545 (March 2023) is policy context, not an intervention with an identifiable causal effect."},
    "admin_note": {"es": "Todos los conteos son reconocimiento administrativo, no prevalencia ni incidencia.", "en": "All counts are administrative recognition, not prevalence or incidence."},
    "no_linkage_note": {"es": "Las fuentes no se enlazan por persona; no se calculan cocientes entre etapas de bases no enlazables.", "en": "Sources are not person-linked; no ratios are computed between stages of non-linkable sources."},
    # T1
    "t1_source": {"es": "Fuente", "en": "Source"},
    "t1_provider": {"es": "Proveedor", "en": "Provider"},
    "t1_unit": {"es": "Unidad de observación", "en": "Unit of observation"},
    "t1_period": {"es": "Período", "en": "Period"},
    "t1_coverage": {"es": "Población o cobertura", "en": "Population or coverage"},
    "t1_geography": {"es": "Geografía", "en": "Geography"},
    "t1_stockflow": {"es": "Stock o flujo", "en": "Stock or flow"},
    "t1_denominator": {"es": "Denominador posible", "en": "Possible denominator"},
    "t1_breaks": {"es": "Quiebres de definición y esquema", "en": "Definition and schema breaks"},
    "t1_linkage": {"es": "Enlace individual", "en": "Person-level linkage"},
    "t1_files": {"es": "Archivos (n; GB; SHA-256)", "en": "Files (n; GB; SHA-256)"},
    "t1_files_fmt": {"es": "{n} archivos; {gb} GB; SHA-256 {ok}/{listed} verificados frente al manifiesto", "en": "{n} files; {gb} GB; SHA-256 {ok}/{listed} verified against the manifest"},
    "t1_files_nomanifest": {"es": "{n} archivos; {gb} GB; SHA-256 calculado (sin manifiesto externo)", "en": "{n} files; {gb} GB; SHA-256 computed (no external manifest)"},
    "t1_version": {"es": "versión/descarga más reciente {d}", "en": "latest version/download {d}"},
    # T2
    "t2_block_panel": {"es": "Panel y episodios", "en": "Panel and episodes"},
    "t2_block_f84": {"es": "Episodios con F84 documentado", "en": "Episodes with documented F84"},
    "t2_block_activity": {"es": "Modalidad de atención (panel observado)", "en": "Activity type (observed panel)"},
    "t2_block_depth": {"es": "Profundidad diagnóstica", "en": "Coding depth"},
    "t2_block_persons": {"es": "Personas únicas (solo dentro de cada año)", "en": "Unique persons (within each year only)"},
    "t2_block_pop": {"es": "Por 100.000 habitantes (INE base 2017, residencia)", "en": "Per 100,000 population (INE base 2017, residence)"},
    "t2_block_sens": {"es": "Sensibilidad de definición", "en": "Definition sensitivity"},
    "t2_hospitals_observed": {"es": "Hospitales observados (n)", "en": "Hospitals observed (n)"},
    "t2_hospitals_fixed": {"es": "Hospitales del panel fijo (n)", "en": "Fixed-panel hospitals (n)"},
    "t2_episodes_observed_all": {"es": "Episodios GRD, panel observado, toda modalidad (n)", "en": "GRD episodes, observed panel, all activity (n)"},
    "t2_episodes_fixed_all": {"es": "Episodios GRD, panel fijo de 65, toda modalidad (n)", "en": "GRD episodes, fixed panel of 65, all activity (n)"},
    "t2_episodes_hosp": {"es": "Episodios GRD, hospitalización estricta (n)", "en": "GRD episodes, strict hospitalisation (n)"},
    "t2_episodes_cma": {"es": "Episodios GRD, cirugía mayor ambulatoria (n)", "en": "GRD episodes, major ambulatory surgery (n)"},
    "t2_episodes_other": {"es": "Episodios GRD, otras modalidades (urgencia, diurna, no identificada) (n)", "en": "GRD episodes, other activity (emergency, day hospital, unidentified) (n)"},
    "t2_any_obs_n": {"es": "F84 en cualquier posición, panel observado (n)", "en": "F84 in any position, observed panel (n)"},
    "t2_any_obs_rate": {"es": "F84 en cualquier posición, panel observado, por 100.000 episodios (IC 95 %)", "en": "F84 in any position, observed panel, per 100,000 episodes (95% CI)"},
    "t2_any_fix_n": {"es": "F84 en cualquier posición, panel fijo de 65 (n)", "en": "F84 in any position, fixed panel of 65 (n)"},
    "t2_any_fix_rate": {"es": "F84 en cualquier posición, panel fijo de 65, por 100.000 episodios (IC 95 %)", "en": "F84 in any position, fixed panel of 65, per 100,000 episodes (95% CI)"},
    "t2_prin_obs_n": {"es": "F84 principal, panel observado (n)", "en": "F84 principal, observed panel (n)"},
    "t2_prin_obs_rate": {"es": "F84 principal, panel observado, por 100.000 episodios (IC 95 %)", "en": "F84 principal, observed panel, per 100,000 episodes (95% CI)"},
    "t2_prin_fix_n": {"es": "F84 principal, panel fijo de 65 (n)", "en": "F84 principal, fixed panel of 65 (n)"},
    "t2_prin_fix_rate": {"es": "F84 principal, panel fijo de 65, por 100.000 episodios (IC 95 %)", "en": "F84 principal, fixed panel of 65, per 100,000 episodes (95% CI)"},
    "t2_sec_only": {"es": "F84 solo como diagnóstico secundario, n (% de los episodios con F84)", "en": "F84 as secondary diagnosis only, n (% of episodes with F84)"},
    "t2_prin_and_sec": {"es": "F84 principal y secundario a la vez (n)", "en": "F84 both principal and secondary (n)"},
    "t2_hosp_any_n": {"es": "Hospitalización estricta: F84 cualquier posición (n)", "en": "Strict hospitalisation: F84 any position (n)"},
    "t2_hosp_fix_any_n": {"es": "Hospitalización estricta, panel fijo de 65: F84 cualquier posición (n)", "en": "Strict hospitalisation, fixed panel of 65: F84 any position (n)"},
    "t2_hosp_fix_any_rate": {"es": "Hospitalización estricta, panel fijo de 65: F84 cualquier posición, por 100.000 episodios (IC 95 %)", "en": "Strict hospitalisation, fixed panel of 65: F84 any position, per 100,000 episodes (95% CI)"},
    "t2_hosp_any_rate": {"es": "Hospitalización estricta: F84 cualquier posición, por 100.000 episodios (IC 95 %)", "en": "Strict hospitalisation: F84 any position, per 100,000 episodes (95% CI)"},
    "t2_hosp_prin_n": {"es": "Hospitalización estricta: F84 principal (n)", "en": "Strict hospitalisation: F84 principal (n)"},
    "t2_hosp_prin_rate": {"es": "Hospitalización estricta: F84 principal, por 100.000 episodios (IC 95 %)", "en": "Strict hospitalisation: F84 principal, per 100,000 episodes (95% CI)"},
    "t2_cma_any_n": {"es": "Cirugía mayor ambulatoria: F84 cualquier posición (n)", "en": "Major ambulatory surgery: F84 any position (n)"},
    "t2_cma_any_rate": {"es": "Cirugía mayor ambulatoria: F84 cualquier posición, por 100.000 episodios (IC 95 %)", "en": "Major ambulatory surgery: F84 any position, per 100,000 episodes (95% CI)"},
    "t2_other_any_n": {"es": "Otras modalidades: F84 cualquier posición (n)", "en": "Other activity: F84 any position (n)"},
    "t2_depth_all": {"es": "Diagnósticos codificados por episodio, todos los episodios: media (mediana)", "en": "Coded diagnoses per episode, all episodes: mean (median)"},
    "t2_depth_f84": {"es": "Diagnósticos codificados por episodio, episodios con F84 cualquier posición: media (mediana)", "en": "Coded diagnoses per episode, episodes with F84 any position: mean (median)"},
    "t2_persons_any": {"es": "Personas con F84 cualquier posición (n, dentro del año)", "en": "Persons with F84 any position (n, within year)"},
    "t2_episodes_per_person": {"es": "Episodios con F84 por persona (razón)", "en": "F84 episodes per person (ratio)"},
    "t2_persons_prin": {"es": "Personas con F84 principal (n, dentro del año)", "en": "Persons with F84 principal (n, within year)"},
    "t2_no_id": {"es": "Episodios con F84 sin identificador válido (n)", "en": "F84 episodes without a valid identifier (n)"},
    "t2_identifier": {"es": "Columna identificadora", "en": "Identifier column"},
    "t2_pop_crude_any": {"es": "Tasa bruta, ambos sexos, F84 cualquier posición (IC 95 %)", "en": "Crude rate, both sexes, F84 any position (95% CI)"},
    "t2_pop_asr_any": {"es": "Tasa estandarizada OMS, ambos sexos, F84 cualquier posición (IC 95 %)", "en": "WHO age-standardised rate, both sexes, F84 any position (95% CI)"},
    "t2_pop_crude_any_m": {"es": "Tasa bruta, hombres, F84 cualquier posición (IC 95 %)", "en": "Crude rate, males, F84 any position (95% CI)"},
    "t2_pop_crude_any_f": {"es": "Tasa bruta, mujeres, F84 cualquier posición (IC 95 %)", "en": "Crude rate, females, F84 any position (95% CI)"},
    "t2_pop_crude_prin": {"es": "Tasa bruta, ambos sexos, F84 principal (IC 95 %)", "en": "Crude rate, both sexes, F84 principal (95% CI)"},
    "t2_pop_asr_prin": {"es": "Tasa estandarizada OMS, ambos sexos, F84 principal (IC 95 %)", "en": "WHO age-standardised rate, both sexes, F84 principal (95% CI)"},
    "t2_other_variant_n": {"es": "Variante alternativa, {v}: F84 cualquier posición, panel observado (n)", "en": "Alternative variant, {v}: F84 any position, observed panel (n)"},
    "t2_other_variant_rate": {"es": "Variante alternativa, {v}: por 100.000 episodios (IC 95 %)", "en": "Alternative variant, {v}: per 100,000 episodes (95% CI)"},
    "t2_strict_n": {"es": "Solo F84.0 autismo infantil (idéntico en ambas variantes): cualquier posición, panel observado (n)", "en": "F84.0 childhood autism only (identical in both variants): any position, observed panel (n)"},
    "t2_strict_rate": {"es": "Solo F84.0: por 100.000 episodios (IC 95 %)", "en": "F84.0 only: per 100,000 episodes (95% CI)"},
    "t2_rett_n": {"es": "F84.2 síndrome de Rett en cualquier posición, con o sin otro código F84 (n)",
                  "en": "F84.2 Rett syndrome in any position, with or without another F84 code (n)"},
    "t2_rett_only_n": {"es": "Diferencia entre variantes: episodios cuyo único código F84 es F84.2 (n)",
                       "en": "Difference between variants: episodes whose only F84 code is F84.2 (n)"},
    "t2_col_unit_n": {"es": "episodios", "en": "episodes"},
    "t2_col_unit_rate": {"es": "por 100.000 episodios GRD", "en": "per 100,000 GRD episodes"},
    "t2_col_unit_pop": {"es": "por 100.000 habitantes", "en": "per 100,000 population"},
    "t2_col_unit_persons": {"es": "personas", "en": "persons"},
    "t2_col_unit_hosp": {"es": "hospitales", "en": "hospitals"},
    "t2_col_unit_depth": {"es": "diagnósticos por episodio", "en": "diagnoses per episode"},
    "t2_col_unit_ratio": {"es": "razón", "en": "ratio"},
    "t2_col_unit_text": {"es": "texto", "en": "text"},
    "t2_col_unit_npct": {"es": "n (%)", "en": "n (%)"},
    # T3
    "t3_module": {"es": "Módulo", "en": "Module"},
    "t3_code": {"es": "Código(s)", "en": "Code(s)"},
    "t3_era": {"es": "Era de definición", "en": "Definition era"},
    "t3_measure": {"es": "Medida (unidad)", "en": "Measure (unit)"},
    "t3_m_annual": {"es": "Suma anual de meses ({u})", "en": "Annual sum of months ({u})"},
    "t3_m_dec": {"es": "Stock de diciembre ({u})", "en": "December stock ({u})"},
    "t3_m_jun": {"es": "Stock de junio, sensibilidad ({u})", "en": "June stock, sensitivity ({u})"},
    "t3_m_stable": {"es": "{m}; panel estable de establecimientos", "en": "{m}; stable establishment panel"},
    "u_children": {"es": "niños/as reportados", "en": "children reported"},
    "u_screening_records": {"es": "registros de tamizaje", "en": "screening records"},
    "u_screening_results": {"es": "resultados de tamizaje", "en": "screening results"},
    "u_referral_records": {"es": "registros de referencia", "en": "referral records"},
    "u_entries": {"es": "ingresos reportados", "en": "entries reported"},
    "u_exits": {"es": "egresos (altas) reportados", "en": "exits reported"},
    "u_interventions": {"es": "intervenciones", "en": "interventions"},
    "u_stock": {"es": "personas bajo control", "en": "people under control"},
    "t3_grp_a03_legacy": {"es": "A03 detección, era legado 2019–2022 (subgrupo con alteración de lenguaje/área social)", "en": "A03 detection, legacy era 2019–2022 (subgroup with language/social alteration)"},
    "t3_grp_a03_ctx": {"es": "A03 contexto del control de 18 meses (2019–2024)", "en": "A03 context of the 18-month check (2019–2024)"},
    "t3_grp_a03_2023": {"es": "A03 detección, era 2023–2024 (M-CHAT-R/F)", "en": "A03 detection, 2023–2024 era (M-CHAT-R/F)"},
    "t3_grp_a03_2024": {"es": "A03 detección, 31–59 meses (solo 2024)", "en": "A03 detection, 31–59 months (2024 only)"},
    "t3_grp_a03_2025": {"es": "A03 detección, rediseño 2025", "en": "A03 detection, 2025 redesign"},
    "t3_grp_a27": {"es": "A27 soporte y referencia asistida (2023–2025)", "en": "A27 support and assisted referral (2023–2025)"},
    "t3_grp_a05_broad": {"es": "A05 TGD amplio 2019–2020 (sensibilidad separada)", "en": "A05 broad PDD 2019–2020 (separate sensitivity)"},
    "t3_grp_a05": {"es": "A05 ingresos y egresos de salud mental (2021–2025)", "en": "A05 mental-health programme entries and exits (2021–2025)"},
    "t3_grp_p2": {"es": "P2 NANEAS bajo control (stock)", "en": "P2 NANEAS under control (stock)"},
    "t3_grp_p6_broad": {"es": "P6 TGD amplio 2019–2020 (sensibilidad separada)", "en": "P6 broad PDD 2019–2020 (separate sensitivity)"},
    "t3_grp_p6": {"es": "P6 salud mental bajo control (2021–2025)", "en": "P6 mental-health population under control (2021–2025)"},
    "t3_grp_a28": {"es": "A28 rehabilitación (2023–2025)", "en": "A28 rehabilitation (2023–2025)"},
    "c_03500404": {"es": "Niños/as con control de salud a los 18 meses (contexto)", "en": "Children with the 18-month health check (context)"},
    "c_03500405": {"es": "Alteración de lenguaje y/o área social en el control de 18 meses (criterio de selección)", "en": "Language and/or social-area alteration at the 18-month check (selection criterion)"},
    "c_03500406": {"es": "M-CHAT aplicado en el subgrupo con alteración de lenguaje/social", "en": "M-CHAT performed in the subgroup with language/social alteration"},
    "c_03500407": {"es": "M-CHAT alterado en el subgrupo con alteración de lenguaje/social", "en": "Altered M-CHAT in the subgroup with language/social alteration"},
    "c_09600212": {"es": "Sospecha de autismo en otros controles o consultas", "en": "Suspected autism in other checks or consultations"},
    "c_09600213": {"es": "M-CHAT-R/F primera parte: riesgo bajo", "en": "M-CHAT-R/F first part: low risk"},
    "c_09600214": {"es": "M-CHAT-R/F primera parte: riesgo medio", "en": "M-CHAT-R/F first part: medium risk"},
    "c_09600215": {"es": "M-CHAT-R/F primera parte: riesgo alto", "en": "M-CHAT-R/F first part: high risk"},
    "c_09600216": {"es": "M-CHAT-R/F riesgo alto con referencia a especialista", "en": "M-CHAT-R/F high risk with specialist referral"},
    "c_09600217": {"es": "M-CHAT-R/F segunda parte: riesgo medio en la primera parte (solo 2023)", "en": "M-CHAT-R/F second part: medium risk in the first part (2023 only)"},
    "c_09600218": {"es": "M-CHAT-R/F segunda parte: sin necesidad de referencia", "en": "M-CHAT-R/F second part: no referral required"},
    "c_09600219": {"es": "M-CHAT-R/F segunda parte: requiere referencia", "en": "M-CHAT-R/F second part: referral required"},
    "c_03700104": {"es": "Niños/as de 31–59 meses evaluados en control de salud integral", "en": "Children aged 31–59 months evaluated at the integral health check"},
    "c_03700105": {"es": "Niños/as de 31–59 meses con sospecha en otra instancia", "en": "Children aged 31–59 months suspected elsewhere"},
    "c_03700106": {"es": "Sospecha de autismo por pauta de señales de alerta: sí", "en": "Autism suspicion by alert-sign guide: yes"},
    "c_03700107": {"es": "Sospecha de autismo por pauta de señales de alerta: no", "en": "Autism suspicion by alert-sign guide: no"},
    "c_03700108": {"es": "Referencia tras evaluación de señales de alerta: sí", "en": "Referral after alert-sign evaluation: yes"},
    "c_03700109": {"es": "Referencia tras evaluación de señales de alerta: no", "en": "Referral after alert-sign evaluation: no"},
    "c_03710013": {"es": "Motivo M-CHAT: EEDP alterado en lenguaje/área social, 16–30 meses", "en": "M-CHAT motive: altered EEDP language/social area, 16–30 months"},
    "c_03710014": {"es": "Motivo M-CHAT: factor de riesgo o señal de alerta de autismo, 16–30 meses", "en": "M-CHAT motive: autism risk factor or alert sign, 16–30 months"},
    "c_03710015": {"es": "Motivo M-CHAT: ambos motivos, 16–30 meses", "en": "M-CHAT motive: both motives, 16–30 months"},
    "c_03710016": {"es": "M-CHAT-R/F resultado: riesgo bajo", "en": "M-CHAT-R/F result: low risk"},
    "c_03710017": {"es": "M-CHAT-R/F riesgo medio: sin necesidad de referencia diagnóstica", "en": "M-CHAT-R/F medium risk: no diagnostic referral required"},
    "c_03710018": {"es": "M-CHAT-R/F riesgo medio: requiere referencia diagnóstica", "en": "M-CHAT-R/F medium risk: diagnostic referral required"},
    "c_03710019": {"es": "M-CHAT-R/F riesgo alto: requiere referencia diagnóstica", "en": "M-CHAT-R/F high risk: diagnostic referral required"},
    "c_03710020": {"es": "Sospecha de autismo 30–59 meses: sin necesidad de referencia diagnóstica", "en": "Suspected autism 30–59 months: no diagnostic referral required"},
    "c_03710021": {"es": "Sospecha de autismo 30–59 meses: requiere referencia diagnóstica", "en": "Suspected autism 30–59 months: diagnostic referral required"},
    "c_29101566": {"es": "Consejería en contexto de tamizaje M-CHAT-R/F (intervenciones, no personas)", "en": "Counselling in M-CHAT-R/F screening context (interventions, not persons)"},
    "c_29101574": {"es": "Referencia asistida en contexto de tamizaje M-CHAT-R/F (intervenciones, no personas)", "en": "Assisted referral in M-CHAT-R/F screening context (interventions, not persons)"},
    "c_06902600": {"es": "Ingresos a salud mental: trastornos generalizados del desarrollo (TGD amplio; incluye Rett de forma inseparable)", "en": "Mental-health programme entries: pervasive developmental disorders (broad PDD; Rett inseparable)"},
    "c_05225000": {"es": "Egresos (altas clínicas) de salud mental: TGD amplio", "en": "Mental-health programme exits (clinical discharges): broad PDD"},
    "c_05990022": {"es": "Ingresos a salud mental por autismo estricto (05990022; idéntico en ambas variantes)", "en": "Mental-health programme entries for strict autism (05990022; identical in both variants)"},
    "c_05990027": {"es": "Egresos (altas clínicas) de salud mental por autismo estricto (05990027; idéntico en ambas variantes)", "en": "Mental-health programme exits for strict autism (05990027; identical in both variants)"},
    "c_a05_family_entry": {"es": "Ingresos a salud mental, familia TGD de la variante: {v}", "en": "Mental-health programme entries, PDD family of the variant: {v}"},
    "c_a05_family_exit": {"es": "Egresos (altas clínicas) de salud mental, familia TGD de la variante: {v}", "en": "Mental-health programme exits, PDD family of the variant: {v}"},
    "c_P2500500": {"es": "NANEAS con trastorno del espectro autista bajo control", "en": "NANEAS with autism spectrum disorder under control"},
    "c_P2501878": {"es": "Total NANEAS bajo control (denominador solo desde diciembre de 2023)", "en": "Total NANEAS under control (denominator only from December 2023)"},
    "c_P6223000": {"es": "APS: TGD amplio bajo control (incluye Rett de forma inseparable)", "en": "Primary care: broad PDD under control (Rett inseparable)"},
    "c_P6223380": {"es": "Especialidad: TGD amplio bajo control (incluye Rett de forma inseparable)", "en": "Specialty: broad PDD under control (Rett inseparable)"},
    "c_P6241010": {"es": "APS: autismo estricto bajo control (P6241010; idéntico en ambas variantes)", "en": "Primary care: strict autism under control (P6241010; identical in both variants)"},
    "c_P6241060": {"es": "Especialidad: autismo estricto bajo control (P6241060; idéntico en ambas variantes)", "en": "Specialty: strict autism under control (P6241060; identical in both variants)"},
    "c_p6_family_primary": {"es": "APS: familia TGD de la variante bajo control: {v}", "en": "Primary care: PDD family of the variant under control: {v}"},
    "c_p6_family_specialty": {"es": "Especialidad: familia TGD de la variante bajo control: {v}", "en": "Specialty: PDD family of the variant under control: {v}"},
    "c_29101629": {"es": "Ingresos a rehabilitación de nivel primario por autismo", "en": "Entries to primary-level rehabilitation for autism"},
    "c_29101651": {"es": "Ingresos a rehabilitación hospitalaria por autismo", "en": "Entries to hospital-level rehabilitation for autism"},
    # T4
    "t4_layer": {"es": "Capa", "en": "Layer"},
    "t4_geo": {"es": "Geografía / unidad", "en": "Geography / unit"},
    "t4_layer_pop": {"es": "Población (INE)", "en": "Population (INE)"},
    "t4_layer_ins": {"es": "Aseguramiento (FONASA, ISAPRE)", "en": "Insurance (FONASA, ISAPRE)"},
    "t4_layer_aps": {"es": "Cobertura operativa (inscritos APS)", "en": "Operational coverage (APS enrolment)"},
    "t4_layer_rem20": {"es": "Actividad y capacidad hospitalaria (REM-20)", "en": "Hospital activity and capacity (REM-20)"},
    "t4_geo_res": {"es": "residencia; personas al 30 de junio", "en": "residence; persons at 30 June"},
    "t4_geo_res_census": {"es": "empadronamiento censal; personas", "en": "census enumeration; persons"},
    "t4_geo_ratio": {"es": "razón", "en": "ratio"},
    "t4_geo_fonasa": {"es": "mixta (comuna del centro APS para inscritos; domicilio para no inscritos); personas en diciembre", "en": "mixed (APS-centre comuna for enrolled; domicile for non-enrolled); persons in December"},
    "t4_geo_isapre": {"es": "comuna administrativa del beneficiario; personas en diciembre", "en": "administrative comuna of the beneficiary; persons in December"},
    "t4_geo_share": {"es": "porcentaje (stock de diciembre / proyección al 30 de junio)", "en": "percentage (December stock / 30 June projection)"},
    "t4_geo_aps": {"es": "comuna del centro APS (lugar de atención); personas en diciembre", "en": "APS-centre comuna (place of care); persons in December"},
    "t4_geo_centres": {"es": "códigos de centro distintos", "en": "distinct centre codes"},
    "t4_geo_estab": {"es": "establecimiento (nunca residencia)", "en": "establishment (never residence)"},
    "t4_geo_episodes": {"es": "egresos (episodios), suma anual", "en": "discharges (episodes), annual sum"},
    "t4_geo_beddays": {"es": "días-cama disponibles, suma anual", "en": "available bed-days, annual sum"},
    "t4_geo_text": {"es": "esquema del archivo", "en": "file schema"},
    "t4_geo_pct_panel": {"es": "porcentaje del total anual retenido por el panel continuo", "en": "percentage of the annual total retained by the continuous panel"},
    "t4_geo_per1000": {"es": "egresos del año por 1.000 habitantes INE base 2017 (actividad, lugar de atención / residencia)", "en": "discharges of the year per 1,000 INE base-2017 population (activity, place of care / residence)"},
    "t4_ine2017": {"es": "INE proyección base Censo 2017 (denominador principal)", "en": "INE projection, Census 2017 base (primary denominator)"},
    "t4_ine2024": {"es": "INE proyección base Censo 2024 (sensibilidad; nunca combinada)", "en": "INE projection, Census 2024 base (sensitivity; never merged)"},
    "t4_ine_ratio": {"es": "Razón base 2024 / base 2017", "en": "Ratio base 2024 / base 2017"},
    "t4_censo2024": {"es": "Censo 2024, población empadronada", "en": "Census 2024, enumerated population"},
    "t4_fonasa": {"es": "FONASA beneficiarios (diciembre)", "en": "FONASA beneficiaries (December)"},
    "t4_fonasa_aps": {"es": "FONASA beneficiarios inscritos en APS (INSCRITO_APS = SI)", "en": "FONASA beneficiaries enrolled in APS (INSCRITO_APS = SI)"},
    "t4_fonasa_scheme": {"es": "FONASA esquema de tramos etarios del archivo", "en": "FONASA age-band scheme of the file"},
    "t4_fonasa_scheme_val": {"es": "{n} bandas", "en": "{n} bands"},
    "t4_isapre": {"es": "ISAPRE beneficiarios (cotizantes + cargas, diciembre)", "en": "ISAPRE beneficiaries (contributors + dependants, December)"},
    "t4_isapre_cot": {"es": "ISAPRE cotizantes", "en": "ISAPRE contributors"},
    "t4_isapre_car": {"es": "ISAPRE cargas", "en": "ISAPRE dependants"},
    "t4_fi": {"es": "FONASA + ISAPRE", "en": "FONASA + ISAPRE"},
    "t4_share_f": {"es": "FONASA / INE base 2017 (%)", "en": "FONASA / INE base 2017 (%)"},
    "t4_share_i": {"es": "ISAPRE / INE base 2017 (%)", "en": "ISAPRE / INE base 2017 (%)"},
    "t4_share_fi": {"es": "(FONASA + ISAPRE) / INE base 2017 (%); no es tasa de aseguramiento", "en": "(FONASA + ISAPRE) / INE base 2017 (%); not an insurance-coverage rate"},
    "t4_share_fi24": {"es": "(FONASA + ISAPRE) / INE base 2024 (%); sensibilidad", "en": "(FONASA + ISAPRE) / INE base 2024 (%); sensitivity"},
    "t4_aps": {"es": "Inscritos APS (diciembre), todos los tramos", "en": "APS enrolled persons (December), all tramos"},
    "t4_aps_ad": {"es": "Inscritos APS tramos FONASA A–D", "en": "APS enrolled persons, FONASA tramos A–D"},
    "t4_aps_x": {"es": "Inscritos APS tramo X (no clasificados)", "en": "APS enrolled persons, tramo X (unclassified)"},
    "t4_aps_centres": {"es": "Centros APS con inscritos (n)", "en": "APS centres with enrolled persons (n)"},
    "t4_aps_panel": {"es": "Panel continuo de 1.871 centros: inscritos", "en": "Continuous panel of 1,871 centres: enrolled persons"},
    "t4_aps_ret": {"es": "Panel continuo de 1.871 centros: retención (%)", "en": "Continuous panel of 1,871 centres: retention (%)"},
    "t4_aps_vs_fonasa": {"es": "Razón inscritos APS A–D / FONASA inscritos APS", "en": "Ratio APS enrolled A–D / FONASA enrolled in APS"},
    "t4_r20_estab": {"es": "REM-20 establecimientos reportantes (n)", "en": "REM-20 reporting establishments (n)"},
    "t4_r20_12m": {"es": "REM-20 establecimientos con 12 meses reportados (n)", "en": "REM-20 establishments with 12 reported months (n)"},
    "t4_r20_disc": {"es": "REM-20 egresos, todos los establecimientos", "en": "REM-20 discharges, all establishments"},
    "t4_r20_disc_p": {"es": "REM-20 egresos, panel de 188 establecimientos", "en": "REM-20 discharges, panel of 188 establishments"},
    "t4_r20_ret": {"es": "REM-20 retención de egresos del panel de 188 (%)", "en": "REM-20 discharge retention of the 188 panel (%)"},
    "t4_r20_bd": {"es": "REM-20 días-cama disponibles, todos", "en": "REM-20 available bed-days, all"},
    "t4_r20_bd_p": {"es": "REM-20 días-cama disponibles, panel de 188", "en": "REM-20 available bed-days, 188 panel"},
    "t4_r20_bd_ret": {"es": "REM-20 retención de días-cama del panel de 188 (%)", "en": "REM-20 bed-day retention of the 188 panel (%)"},
    "t4_r20_per1000": {"es": "REM-20 egresos por 1.000 habitantes INE (intensidad de actividad, no cobertura)", "en": "REM-20 discharges per 1,000 INE population (activity intensity, not coverage)"},
    # T5
    "t5_survey": {"es": "Encuesta", "en": "Survey"},
    "t5_year": {"es": "Año", "en": "Year"},
    "t5_domain": {"es": "Universo (dominio)", "en": "Universe (domain)"},
    "t5_subgroup": {"es": "Subgrupo", "en": "Subgroup"},
    "t5_type": {"es": "Tipo de estimación", "en": "Estimate type"},
    "t5_item": {"es": "Ítem (variable)", "en": "Item (variable)"},
    "t5_wording": {"es": "Redacción del cuestionario", "en": "Questionnaire wording"},
    "t5_n": {"es": "n (no ponderado)", "en": "n (unweighted)"},
    "t5_cases": {"es": "Casos (no ponderados)", "en": "Cases (unweighted)"},
    "t5_pct": {"es": "% ponderado (EE)", "en": "Weighted % (SE)"},
    "t5_ci": {"es": "IC 95 %", "en": "95% CI"},
    "t5_wtotal": {"es": "Total ponderado (personas)", "en": "Weighted total (persons)"},
    "t5_design": {"es": "Diseño (ponderador; estratos; UPM)", "en": "Design (weight; strata; PSU)"},
    "t5_deff": {"es": "DEFF", "en": "DEFF"},
    "t5_rse": {"es": "ERR (%)", "en": "RSE (%)"},
    "t5_precision": {"es": "Precisión", "en": "Precision"},
    "t5_prec_ok": {"es": "adecuada (≥ 30 casos; ERR ≤ 30 %)", "en": "adequate (≥ 30 cases; RSE ≤ 30%)"},
    "t5_prec_imprecise": {"es": "imprecisa (< 30 casos): solo orden de magnitud", "en": "imprecise (< 30 cases): order of magnitude only"},
    "t5_prec_suppressed": {"es": "no estimable (ERR > 30 %): estimación suprimida", "en": "not estimable (RSE > 30%): estimate suppressed"},
    "t5_type_primary": {"es": "principal", "en": "primary"},
    "t5_type_sensitivity": {"es": "sensibilidad", "en": "sensitivity"},
    "t5_type_secondary": {"es": "secundaria", "en": "secondary"},
    "t5_sub_total": {"es": "Total", "en": "Total"},
    "t5_sub_male": {"es": "Hombres", "en": "Males"},
    "t5_sub_female": {"es": "Mujeres", "en": "Females"},
    "t5_age_prefix": {"es": "Edad {a}", "en": "Age {a}"},
    "t5_wording_en_prefix": {"es": "", "en": "Original Spanish wording: "},
    # dominios de encuesta (texto original en español → inglés)
    "dom_endide_adults": {"es": "ENDIDE 2022, adultos de 18+ años: autismo reportado (autorreporte o por tercero)", "en": "ENDIDE 2022, adults aged 18+: reported autism (self-report or by proxy)"},
    "dom_endide_nna": {"es": "ENDIDE 2022, NNA de 2–17 años (responsable principal): autismo reportado", "en": "ENDIDE 2022, children and adolescents aged 2–17 (main caregiver): reported autism"},
    "dom_endide_nna_conf_among": {"es": "ENDIDE 2022, NNA con autismo reportado: confirmado por un médico (respuestas válidas)", "en": "ENDIDE 2022, children with reported autism: confirmed by a physician (valid answers)"},
    "dom_endide_nna_conf_among_sens": {"es": "ENDIDE 2022, NNA con autismo reportado: confirmado por un médico («No responde» = no confirmado)", "en": "ENDIDE 2022, children with reported autism: confirmed by a physician ('No answer' = not confirmed)"},
    "dom_endide_nna_conf": {"es": "ENDIDE 2022, NNA de 2–17 años: autismo reportado y confirmado por un médico", "en": "ENDIDE 2022, children and adolescents aged 2–17: autism reported and confirmed by a physician"},
    "dom_endide_nna_med": {"es": "ENDIDE 2022, NNA con autismo reportado: ha recibido medicamento", "en": "ENDIDE 2022, children with reported autism: has received medication"},
    "dom_endide_nna_other": {"es": "ENDIDE 2022, NNA con autismo reportado: ha recibido otro tratamiento", "en": "ENDIDE 2022, children with reported autism: has received other treatment"},
    "dom_encavi": {"es": "ENCAVI 2023–2024, personas de 15+ años: diagnóstico de trastorno del espectro autista", "en": "ENCAVI 2023–2024, persons aged 15+: diagnosis of autism spectrum disorder"},
    "dom_encavi_sens": {"es": "ENCAVI 2023–2024, personas de 15+ años: diagnóstico de TEA («No sabe/No responde» = no diagnosticado)", "en": "ENCAVI 2023–2024, persons aged 15+: ASD diagnosis ('Don't know/No answer' = not diagnosed)"},
    "dom_encavi_treat": {"es": "ENCAVI 2023–2024, personas de 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico", "en": "ENCAVI 2023–2024, persons aged 15+ with ASD diagnosis: has received or is in medical treatment"},
    "w_c26_33": {"es": "Enfermedad o condición de salud: Autismo (Trastorno del espectro autista)", "en": "Illness or health condition: Autism (autism spectrum disorder)"},
    "w_n29_19": {"es": "Enfermedad o condición de salud: Autismo (Trastorno del espectro Autista)", "en": "Illness or health condition: Autism (autism spectrum disorder)"},
    "w_n29a_19": {"es": "¿Le ha dicho un médico que tiene…? Autismo (Trastorno del espectro Autista)", "en": "Has a physician told you that he/she has…? Autism (autism spectrum disorder)"},
    "w_n29b_19": {"es": "¿Ha recibido medicamento para...? Autismo (Trastorno del espectro Autista)", "en": "Has he/she received medication for…? Autism (autism spectrum disorder)"},
    "w_n29c_19": {"es": "¿Ha recibido otro tratam. para...? Autismo (Trastorno del espectro Autista)", "en": "Has he/she received other treatment for…? Autism (autism spectrum disorder)"},
    "w_p4_6_1_h": {"es": "4.6 Actualmente, ¿Ud. ha sido diagnosticado con alguno de los siguientes problemas, condición de salud o enfermedades? — Trastorno del espectro autista (nota al encuestador: diagnóstico médico tradicional)", "en": "4.6 Currently, have you been diagnosed with any of the following problems, health conditions or illnesses? — Autism spectrum disorder (interviewer note: traditional medical diagnosis)"},
    "w_p4_6_2_h": {"es": "4.6 ¿Y para cuál de ellos ha recibido o está en tratamiento médico? — Trastorno del espectro autista", "en": "4.6 And for which of them have you received or are you in medical treatment? — Autism spectrum disorder"},
    # T6
    "t6_block_pie": {"es": "PIE / SINACES (stock escolar anual; registro para subvención, no prevalencia)", "en": "PIE / SINACES (annual school stock; subsidy registration, not prevalence)"},
    "t6_block_junaeb": {"es": "JUNAEB EVE (reporte de cuidadores en cohortes escolares seleccionadas; % ponderado)", "en": "JUNAEB EVE (caregiver report in selected school cohorts; weighted %)"},
    "t6_pie_strict": {"es": "PIE TEA estricto (n)", "en": "PIE strict ASD (n)"},
    "t6_pie_asperger": {"es": "PIE TEA-Asperger (n)", "en": "PIE ASD-Asperger (n)"},
    "t6_pie_harmonised": {"es": "PIE armonizado TEA + TEA-Asperger (n): Apuntes 60 (2019–2023), SINACES (2024–2025)", "en": "Harmonised PIE ASD + ASD-Asperger (n): Apuntes 60 (2019–2023), SINACES (2024–2025)"},
    "t6_pie_sinaces": {"es": "SINACES estudiantes autistas en PIE (n), como publicado", "en": "SINACES autistic students in PIE (n), as published"},
    "t6_sinaces_total": {"es": "SINACES estudiantes autistas en el sistema educativo, total (n)", "en": "SINACES autistic students in the education system, total (n)"},
    "t6_special": {"es": "Escuelas especiales: estudiantes autistas (n)", "en": "Special schools: autistic students (n)"},
    "t6_pie_total": {"es": "Matrícula total PIE, Apuntes 60 (n)", "en": "Total PIE enrolment, Apuntes 60 (n)"},
    "t6_applicants": {"es": "Postulantes totales al PIE, SINACES (n)", "en": "Total PIE applicants, SINACES (n)"},
    "t6_share_strict": {"es": "TEA estricto como % de la matrícula PIE", "en": "Strict ASD as % of PIE enrolment"},
    "t6_share_harm": {"es": "Armonizado como % de la matrícula PIE", "en": "Harmonised as % of PIE enrolment"},
    "t6_share_appl": {"es": "Armonizado como % de los postulantes al PIE (SINACES)", "en": "Harmonised as % of PIE applicants (SINACES)"},
    "t6_exceptional": {"es": "Ingreso excepcional al PIE de estudiantes autistas (n)", "en": "Exceptional PIE entry of autistic students (n)"},
    "t6_regular": {"es": "Ingreso regular al PIE de estudiantes autistas (n)", "en": "Regular PIE entry of autistic students (n)"},
    "t6_src_apuntes60": {"es": "Apuntes 60 (2024), Tabla 6, p. 11", "en": "Apuntes 60 (2024), Table 6, p. 11"},
    "t6_src_sinaces_t1": {"es": "Reporte Ley 21.545 SINACES (2025), Tabla 1, p. 8", "en": "Law 21.545 SINACES report (2025), Table 1, p. 8"},
    "t6_src_sinaces_t2": {"es": "Reporte Ley 21.545 SINACES (2025), Tabla 2, p. 9", "en": "Law 21.545 SINACES report (2025), Table 2, p. 9"},
    "t6_src_mixed": {"es": "Apuntes 60, Tabla 6, p. 11 (2019–2023); SINACES, Tabla 1, p. 8 (2024–2025)", "en": "Apuntes 60, Table 6, p. 11 (2019–2023); SINACES, Table 1, p. 8 (2024–2025)"},
    "t6_src_derived": {"es": "derivado de las series anteriores", "en": "derived from the series above"},
    "t6_src_junaeb": {"es": "JUNAEB EVE microdatos {y}; ítem {item}; ponderador {w}", "en": "JUNAEB EVE microdata {y}; item {item}; weight {w}"},
    "t6_src_junaeb_generic": {"es": "JUNAEB EVE microdatos por nivel y año (ítem y ponderador anuales en la versión numérica)", "en": "JUNAEB EVE microdata by level and year (annual item and weight in the numeric version)"},
    "t6_junaeb_pct": {"es": "{lvl}: % ponderado con TEA (IC 95 %)", "en": "{lvl}: weighted % with ASD (95% CI)"},
    "t6_junaeb_n": {"es": "{lvl}: estudiantes en el archivo; TEA no ponderado (n; n)", "en": "{lvl}: students in the file; unweighted ASD (n; n)"},
    "t6_ne_no_item": {"es": "n/e (sin ítem TEA)", "en": "n/e (no ASD item)"},
    "t6_ne_no_weight": {"es": "n/e (sin ponderador publicado)", "en": "n/e (no published weight)"},
    "t6_ne_empty": {"es": "n/e (variable vacía)", "en": "n/e (empty variable)"},
    "t6_discrepancy": {"es": "‡ SINACES publica 42.945 en 2022; 45.014 − 2.074 (escuelas especiales) = 42.940, coincidente con Apuntes 60; la serie armonizada usa 42.940.", "en": "‡ SINACES publishes 42,945 for 2022; 45,014 − 2,074 (special schools) = 42,940, matching Apuntes 60; the harmonised series uses 42,940."},
    # T7
    "t7_estimand": {"es": "Estimando", "en": "Estimand"},
    "t7_series": {"es": "Serie / variante", "en": "Series / variant"},
    "t7_spec": {"es": "Especificación (panel; modalidad; posición; denominador/offset; covariables; familia)", "en": "Specification (panel; activity; position; denominator/offset; covariates; family)"},
    "t7_years": {"es": "Años", "en": "Years"},
    "t7_n": {"es": "n (obs.)", "en": "n (obs.)"},
    "t7_apc": {"es": "CPA % (IC 95 %)", "en": "APC % (95% CI)"},
    "t7_p": {"es": "Valor p (Wald)", "en": "p value (Wald)"},
    "t7_disp": {"es": "Dispersión (Pearson χ²/gl)", "en": "Dispersion (Pearson χ²/df)"},
    "t7_notes": {"es": "Notas", "en": "Notes"},
    "t7_pending": {"es": "pendiente: ejecutar 06_models.py (models_summary.csv ausente)", "en": "pending: run 06_models.py (models_summary.csv missing)"},
    "est_grd_rate": {"es": "GRD: episodios con F84 documentado por 100.000 episodios GRD", "en": "GRD: episodes with documented F84 per 100,000 GRD episodes"},
    "est_grd_hospital": {"es": "GRD hospital-año: tendencia con efectos de hospital", "en": "GRD hospital-year: trend with hospital effects"},
    "est_grd_pop": {"es": "GRD: episodios con F84 documentado por 100.000 habitantes (INE base 2017)", "en": "GRD: episodes with documented F84 per 100,000 population (INE base 2017)"},
    "est_a05": {"es": "REM A05: ingresos a salud mental por autismo", "en": "REM A05: mental-health programme entries for autism"},
    "est_a05_exit": {"es": "REM A05: egresos (altas) de salud mental por autismo", "en": "REM A05: mental-health programme exits for autism"},
    "est_a05_pop": {"es": "REM A05: ingresos por autismo por 100.000 habitantes (INE)", "en": "REM A05: autism entries per 100,000 population (INE)"},
    "est_p2": {"es": "REM P2: NANEAS con TEA bajo control (diciembre)", "en": "REM P2: NANEAS with ASD under control (December)"},
    "est_p2_june": {"es": "REM P2: TEA bajo control (junio, sensibilidad)", "en": "REM P2: ASD under control (June, sensitivity)"},
    "est_p2_naneas": {"es": "REM P2: TEA por 100 NANEAS bajo control (diciembre)", "en": "REM P2: ASD per 100 NANEAS under control (December)"},
    "est_p6_primary": {"es": "REM P6 APS: población bajo control por autismo (diciembre)", "en": "REM P6 primary care: population under control for autism (December)"},
    "est_p6_specialty": {"es": "REM P6 especialidad: población bajo control por autismo (diciembre)", "en": "REM P6 specialty: population under control for autism (December)"},
    "est_pie": {"es": "PIE: estudiantes con TEA (stock escolar anual)", "en": "PIE: students with ASD (annual school stock)"},
    "est_deis": {"es": "DEIS: egresos con F84 principal por 100.000 egresos", "en": "DEIS: discharges with F84 principal per 100,000 discharges"},
    "var_con_rett": {"es": "F84 completo (con Rett)", "en": "Full F84 (with Rett)"},
    "var_sin_rett": {"es": "F84 sin Rett", "en": "F84 without Rett"},
    "var_strict_autism_f840": {"es": "solo F84.0 (idéntico en ambas variantes)", "en": "F84.0 only (identical in both variants)"},
    "var_strict_autism": {"es": "autismo estricto REM (idéntico en ambas variantes)", "en": "strict REM autism (identical in both variants)"},
    "var_both": {"es": "no depende de Rett (idéntico)", "en": "independent of Rett (identical)"},
    "out_f84_any": {"es": "F84 cualquier posición", "en": "F84 any position"},
    "out_f84_principal": {"es": "F84 principal", "en": "F84 principal"},
    "out_entries": {"es": "ingresos reportados", "en": "entries reported"},
    "out_entries_stable": {"es": "ingresos, panel estable", "en": "entries, stable panel"},
    "out_exits": {"es": "egresos reportados", "en": "exits reported"},
    "out_stock": {"es": "stock de diciembre", "en": "December stock"},
    "out_stock_stable": {"es": "stock de diciembre, panel estable", "en": "December stock, stable panel"},
    "out_stock_june": {"es": "stock de junio", "en": "June stock"},
    "out_deis_principal": {"es": "F84 en DIAG1", "en": "F84 in DIAG1"},
    "out_pie_harmonised": {"es": "PIE armonizado", "en": "harmonised PIE"},
    "out_pie_strict": {"es": "PIE TEA estricto", "en": "PIE strict ASD"},
    "out_pie_asperger": {"es": "PIE TEA-Asperger", "en": "PIE ASD-Asperger"},
    "off_episodes": {"es": "offset log(episodios GRD del mismo panel y modalidad)", "en": "offset log(GRD episodes, same panel and activity)"},
    "off_pop": {"es": "offset log(población INE base 2017)", "en": "offset log(INE population, base 2017)"},
    "off_hosp_episodes": {"es": "offset log(episodios hospital-año)", "en": "offset log(hospital-year episodes)"},
    "off_none": {"es": "sin offset (conteo)", "en": "no offset (count)"},
    "off_estab": {"es": "offset log(establecimientos reportantes)", "en": "offset log(reporting establishments)"},
    "off_discharges": {"es": "offset log(egresos DEIS)", "en": "offset log(DEIS discharges)"},
    "off_naneas": {"es": "offset log(total NANEAS bajo control)", "en": "offset log(total NANEAS under control)"},
    "panel_observed": {"es": "panel anual observado", "en": "observed annual panel"},
    "panel_fixed65": {"es": "panel fijo de 65 hospitales", "en": "fixed panel of 65 hospitals"},
    "panel_all_estab": {"es": "todos los establecimientos reportantes", "en": "all reporting establishments"},
    "panel_stable": {"es": "panel estable (reporta en todos los años de la era)", "en": "stable panel (reports in every year of the era)"},
    "panel_national": {"es": "nacional", "en": "national"},
    "act_all": {"es": "toda modalidad", "en": "all activity"},
    "act_hospitalisation": {"es": "hospitalización estricta", "en": "strict hospitalisation"},
    "act_na": {"es": "", "en": ""},
    "pos_any": {"es": "cualquier posición", "en": "any position"},
    "pos_principal": {"es": "principal", "en": "principal"},
    "pos_na": {"es": "", "en": ""},
    "cov_none": {"es": "sin covariables", "en": "no covariates"},
    "cov_depth": {"es": "profundidad diagnóstica media (centrada)", "en": "mean coding depth (centred)"},
    "cov_age": {"es": "efectos fijos de grupo de edad (CPA ajustado por edad)", "en": "age-group fixed effects (age-adjusted APC)"},
    "cov_disruption": {"es": "indicador de disrupción del reporte 2020–2021", "en": "2020–2021 reporting-disruption indicator"},
    "cov_disruption_2021": {"es": "indicador de disrupción 2021", "en": "2021 disruption indicator"},
    "cov_depth_disruption": {"es": "profundidad media + indicador 2020–2021", "en": "mean depth + 2020–2021 indicator"},
    "cov_hospital_fe": {"es": "efectos fijos de hospital", "en": "hospital fixed effects"},
    "cov_hospital_fe_depth": {"es": "efectos fijos de hospital + profundidad hospital-año", "en": "hospital fixed effects + hospital-year coding depth"},
    "cov_hospital_fe_disruption": {"es": "efectos fijos de hospital + indicador 2020–2021", "en": "hospital fixed effects + 2020–2021 indicator"},
    "cov_hospital_ri": {"es": "intercepto aleatorio de hospital", "en": "hospital random intercept"},
    "cov_hospital_ri_depth": {"es": "intercepto aleatorio de hospital + profundidad", "en": "hospital random intercept + coding depth"},
    "fam_qp": {"es": "cuasi-Poisson log-lineal", "en": "quasi-Poisson log-linear"},
    "fam_qp_age": {"es": "cuasi-Poisson con efectos de edad", "en": "quasi-Poisson with age effects"},
    "fam_qp_stock": {"es": "cuasi-Poisson log-lineal (stock)", "en": "quasi-Poisson log-linear (stock)"},
    "fam_qp_fe": {"es": "cuasi-Poisson con efectos fijos de hospital", "en": "quasi-Poisson with hospital fixed effects"},
    "fam_qp_fe_cluster": {"es": "cuasi-Poisson, efectos fijos, EE agrupados por hospital", "en": "quasi-Poisson, fixed effects, hospital-clustered SE"},
    "fam_ri_map": {"es": "Poisson con intercepto aleatorio (Laplace/MAP)", "en": "Poisson random intercept (Laplace/MAP)"},
    "sex_HOMBRE": {"es": "hombres", "en": "males"},
    "sex_MUJER": {"es": "mujeres", "en": "females"},
    "sex_TOTAL": {"es": "ambos sexos", "en": "both sexes"},
    "nk_depth": {"es": "profundidad = diagnósticos codificados por episodio", "en": "depth = coded diagnoses per episode"},
    "nk_disruption": {"es": "el indicador 2020–2021 describe la disrupción del reporte, no un efecto causal", "en": "the 2020–2021 indicator describes reporting disruption, not a causal effect"},
    "nk_principal_small": {"es": "numerador pequeño (F84 principal): IC amplio", "en": "small numerator (principal F84): wide CI"},
    "nk_strict_identical": {"es": "serie idéntica en ambas variantes", "en": "series identical in both variants"},
    "nk_df1": {"es": "un grado de libertad residual: dispersión muy inestable", "en": "one residual degree of freedom: dispersion very unstable"},
    "nk_place_vs_residence": {"es": "numerador por lugar de atención y denominador por residencia (INE): lectura complementaria", "en": "numerator by place of care and denominator by residence (INE): complementary reading"},
    "nk_unknown_excluded": {"es": "episodios sin edad/sexo válidos excluidos de la tasa estandarizada", "en": "episodes without valid age/sex excluded from the standardised rate"},
    "nk_age_adj": {"es": "CPA ajustado por grupo de edad", "en": "age-group-adjusted APC"},
    "nk_hospital_fe": {"es": "efectos fijos de hospital; tendencia común; RR frente a la media geométrica de hospitales", "en": "hospital fixed effects; common trend; RR vs geometric mean of hospitals"},
    "nk_hospital_dw": {"es": "Durbin–Watson intrahospitalario", "en": "within-hospital Durbin–Watson"},
    "nk_ecological": {"es": "resultados por hospital descriptivos, sin interpretación ecológica causal", "en": "hospital-level results are descriptive, no causal ecological interpretation"},
    "nk_cluster": {"es": "EE robustos agrupados por hospital", "en": "hospital-clustered robust SE"},
    "nk_ri_ok": {"es": "intercepto aleatorio convergido", "en": "random intercept converged"},
    "nk_ri_prior": {"es": "a priori: efectos fijos N(0, 10²), log-DE del intercepto N(0, 1)", "en": "priors: fixed effects N(0, 10²), intercept log-SD N(0, 1)"},
    "nk_ri_poisson": {"es": "verosimilitud Poisson sin sobredispersión: IC más estrecho que el cuasi-Poisson", "en": "Poisson likelihood without overdispersion: narrower CI than quasi-Poisson"},
    "nk_a05_era": {"es": "era 2021–2025 (códigos de autismo); TGD amplio 2019–2020 no modelado", "en": "2021–2025 era (autism codes); broad PDD 2019–2020 not modelled"},
    "nk_a05_2025": {"es": "menos establecimientos A05 reportan en 2025 (952 frente a 1.070 en 2024)", "en": "fewer A05 establishments report in 2025 (952 vs 1,070 in 2024)"},
    "nk_a05_cells": {"es": "suma de celdas edad × sexo de las filas en era", "en": "sum of the age × sex cells of in-era rows"},
    "nk_stable_panel": {"es": "panel estable de establecimientos (n en la versión numérica)", "en": "stable establishment panel (n in the numeric version)"},
    "nk_estab_offset": {"es": "offset por establecimientos reportantes: tasa por establecimiento", "en": "reporting-establishment offset: rate per establishment"},
    "nk_stock": {"es": "stock (población bajo control), no flujo", "en": "stock (population under control), not a flow"},
    "nk_june": {"es": "junio solo como sensibilidad; nunca sumado con diciembre", "en": "June only as sensitivity; never summed with December"},
    "nk_naneas": {"es": "denominador NANEAS total disponible solo desde diciembre 2023", "en": "total NANEAS denominator available only from December 2023"},
    "nk_pie_source": {"es": "Apuntes 60 (2019–2023) y SINACES (2024–2025)", "en": "Apuntes 60 (2019–2023) and SINACES (2024–2025)"},
    "nk_deis_principal": {"es": "DEIS solo publica DIAG1 (DIAG2 = causa externa): comparable solo con GRD principal", "en": "DEIS publishes DIAG1 only (DIAG2 = external cause): comparable only with GRD principal"},
    "nk_not_causal_law": {"es": "", "en": ""},
    "nk_dw_weak": {"es": "", "en": ""},
}


def T(key: str, lang: str, **kw) -> str:
    """Rótulo bilingüe; falla ruidosamente si falta la clave (ninguna cadena sin traducir)."""
    if key not in LBL:
        raise KeyError(f"Falta el rótulo '{key}' en LBL")
    s = LBL[key][lang]
    return s.format(**kw) if kw else s


def variant_label(variant: str, lang: str) -> str:
    return CFG.VARIANTS[variant]["label"][lang]


def lower_first(s: str) -> str:
    """Minúscula solo en el primer carácter (conserva nombres propios como «Rett» dentro de la frase)."""
    return s[:1].lower() + s[1:] if s else s


# ---------------------------------------------------------------------------
# Formato numérico bilingüe (es: 1.234,5 / en: 1,234.5)
# ---------------------------------------------------------------------------
def is_missing(x) -> bool:
    if x is None:
        return True
    if isinstance(x, str):
        return x.strip() == ""
    try:
        return bool(pd.isna(x))
    except (TypeError, ValueError):
        return False


def fnum(x, dec: int = 0, lang: str = "es") -> str:
    if is_missing(x):
        return T("dash", lang)
    return C.fmt_number(float(x), dec, lang)


def fpct(x, dec: int = 1, lang: str = "es") -> str:
    if is_missing(x):
        return T("dash", lang)
    s = C.fmt_number(float(x), dec, lang)
    return f"{s} %" if lang == "es" else f"{s}%"


def fci(lo, hi, dec: int = 1, lang: str = "es") -> str:
    if is_missing(lo) or is_missing(hi):
        return T("dash", lang)
    return f"{fnum(lo, dec, lang)}–{fnum(hi, dec, lang)}"


def frate(x, lo, hi, dec: int = 1, lang: str = "es") -> str:
    if is_missing(x):
        return T("dash", lang)
    return f"{fnum(x, dec, lang)} ({fci(lo, hi, dec, lang)})"


def fn_pct(n, p, lang: str = "es", dec: int = 1) -> str:
    if is_missing(n):
        return T("dash", lang)
    return f"{fnum(n, 0, lang)} ({fpct(p, dec, lang)})"


def fn_estab(total, n_estab, lang: str = "es") -> str:
    if is_missing(total):
        return T("dash", lang)
    return f"{fnum(total, 0, lang)} (n={fnum(n_estab, 0, lang)})"


def fp(p, lang: str = "es") -> str:
    return C.fmt_p(p, lang)


def yr_cols(years: list[int]) -> list[str]:
    return [str(y) for y in years]


def merge_json(path: Path, new: dict) -> None:
    """Fusiona con el JSON existente (otros módulos escriben en el mismo archivo)."""
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


def out_tables_dir(variant: str, lang: str) -> Path:
    p = CFG.OUT / variant / lang / "tables"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_pair(tdir: Path, name: str, formatted: pd.DataFrame, numeric: pd.DataFrame | None) -> list[Path]:
    paths = [C.atomic_write_csv(formatted, tdir / f"{name}.csv", encoding="utf-8-sig")]
    if numeric is not None:
        paths.append(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv"))
    return paths


def years_in_text(s: str) -> list[int]:
    return [int(y) for y in re.findall(r"(?<!\d)(20[0-3]\d)(?!\d)", str(s))]


def rel(a, b):
    try:
        return (float(a) - float(b)) / float(b) if float(b) != 0 else np.nan
    except (TypeError, ValueError):
        return np.nan


# ---------------------------------------------------------------------------
# T1 — fuentes, unidades, cobertura, quiebres y enlace
# ---------------------------------------------------------------------------
T1_ROWS = [
    # key, source_ids, textos bilingües (name, provider, unit, period, coverage, geography, stockflow, denominator, breaks, linkage)
    dict(key="grd", ids=["grd_publico"],
         name={"es": "GRD público (episodios hospitalarios financiados por FONASA)", "en": "Public GRD (FONASA-financed hospital episodes)"},
         provider={"es": "FONASA", "en": "FONASA"},
         unit={"es": "Episodio GRD (hospitalización o cirugía mayor ambulatoria), una fila por episodio codificado", "en": "GRD episode (hospitalisation or major ambulatory surgery), one row per coded episode"},
         period={"es": "2019–2024 (6 archivos anuales)", "en": "2019–2024 (6 annual files)"},
         coverage={"es": f"Hospitales públicos que reportan al GRD: 65 (2019–2022), 68 (2023) y 72 (2024); el panel fijo son esos mismos 65 hospitales, {C.fixed_panel_gloss('es', 'clause')}; 781.912 a 1.151.475 episodios por año", "en": f"Public hospitals reporting to the GRD: 65 (2019–2022), 68 (2023) and 72 (2024); the fixed panel is those same 65 hospitals, {C.fixed_panel_gloss('en', 'clause')}; 781,912 to 1,151,475 episodes per year"},
         geography={"es": "Hospital de atención (COD_HOSPITAL, servicio de salud); comuna de residencia declarada del paciente (no se mezclan)", "en": "Hospital of care (COD_HOSPITAL, health service); patient's reported comuna of residence (never mixed)"},
         stockflow={"es": "Flujo (episodios egresados en el año)", "en": "Flow (episodes discharged in the year)"},
         denominator={"es": "Episodios GRD del mismo año y panel (por 100.000 episodios); población INE base 2017 por edad y sexo como lectura complementaria", "en": "GRD episodes of the same year and panel (per 100,000 episodes); INE base-2017 population by age and sex as a complementary reading"},
         breaks={"es": f"El identificador cifrado cambia de formato entre 2020 y 2021 (sin solapamiento); panel observado 65/65/65/65/68/72 y {C.fixed_panel_gloss('es', 'named')}; profundidad de codificación media de 4,39 (2019) a 5,78 (2024) diagnósticos por episodio; las categorías de actividad de urgencia y hospital diurno de 2019 desaparecen desde 2020; 2022 omite una fila malformada (932.839 frente a 932.840 registros)", "en": f"Encrypted identifier changes format between 2020 and 2021 (no overlap); observed panel 65/65/65/65/68/72 and {C.fixed_panel_gloss('en', 'named')}; mean coding depth from 4.39 (2019) to 5.78 (2024) diagnoses per episode; 2019 emergency and day-hospital activity categories absent from 2020; 2022 omits one malformed row (932,839 vs 932,840 records)"},
         linkage={"es": "Personas únicas solo dentro de cada año; sin deduplicación a través de 2020/2021; sin enlace con REM, DEIS, FONASA, encuestas ni educación", "en": "Unique persons within each year only; no deduplication across 2020/2021; no linkage to REM, DEIS, FONASA, surveys or education"}),
    dict(key="rem_a", ids=["rem_serie_a"],
         name={"es": "REM Serie A (A03 detección, A27 referencia asistida, A05 ingresos/egresos, A28 rehabilitación)", "en": "REM Series A (A03 detection, A27 assisted referral, A05 entries/exits, A28 rehabilitation)"},
         provider={"es": "DEIS, Ministerio de Salud", "en": "DEIS, Ministry of Health"},
         unit={"es": "Fila establecimiento × mes × código de prestación (celdas Col01–Col50 conservadas como texto)", "en": "Row establishment × month × service code (cells Col01–Col50 kept as text)"},
         period={"es": "2019–2025 (7 archivos anuales)", "en": "2019–2025 (7 annual files)"},
         coverage={"es": "Actividad reportada por establecimientos de la red pública (APS y especialidad); el panel reportante varía por año y código y se informa junto a cada conteo", "en": "Activity reported by public-network establishments (primary and specialty care); the reporting panel varies by year and code and is reported alongside every count"},
         geography={"es": "Establecimiento de atención (IdEstablecimiento, comuna del establecimiento); nunca residencia", "en": "Establishment of care (IdEstablecimiento, establishment's comuna); never residence"},
         stockflow={"es": "Flujo (actividad mensual: tamizajes, intervenciones, ingresos y egresos de programa)", "en": "Flow (monthly activity: screenings, interventions, programme entries and exits)"},
         denominator={"es": "Población INE por edad y sexo (A05); establecimientos reportantes y panel estable; inscritos APS como cobertura operativa; ningún cociente entre etapas", "en": "INE population by age and sex (A05); reporting establishments and stable panel; APS enrolment as operational coverage; no ratios between stages"},
         breaks={"es": "A03: códigos legado 2019–2022 (subgrupo con alteración de lenguaje/área social), familia M-CHAT-R/F 2023–2024, códigos 31–59 meses en 2024, rediseño completo 2025; A05: TGD amplio solo 2019–2020, autismo estricto y categorías desde 2021; A27 específico de TEA desde 2023; A28 desde 2023; disrupción del reporte en 2020", "en": "A03: legacy codes 2019–2022 (subgroup with language/social alteration), M-CHAT-R/F family 2023–2024, 31–59-month codes in 2024, full redesign 2025; A05: broad PDD only 2019–2020, strict autism and categories from 2021; A27 ASD-specific from 2023; A28 from 2023; 2020 reporting disruption"},
         linkage={"es": "Filas agregadas sin personas; A27 cuenta intervenciones, no niños; sin enlace entre A03, A27, A05, A28, P2/P6 ni GRD", "en": "Aggregate rows without persons; A27 counts interventions, not children; no linkage between A03, A27, A05, A28, P2/P6 or GRD"}),
    dict(key="rem_p", ids=["rem_serie_p"],
         name={"es": "REM Serie P (P2 NANEAS, P6 salud mental: población bajo control)", "en": "REM Series P (P2 NANEAS, P6 mental health: population under control)"},
         provider={"es": "DEIS, Ministerio de Salud", "en": "DEIS, Ministry of Health"},
         unit={"es": "Fila establecimiento × semestre (junio, diciembre) × código", "en": "Row establishment × semester (June, December) × code"},
         period={"es": "2019–2025 (7 archivos anuales extraídos de los ZIP oficiales)", "en": "2019–2025 (7 annual files extracted from the official ZIPs)"},
         coverage={"es": "Personas bajo control en establecimientos de la red pública; P2 en diciembre: 460, 400, 640, 897, 1.012, 1.218 y 1.325 establecimientos reportantes (2019–2025)", "en": "People under control in public-network establishments; P2 in December: 460, 400, 640, 897, 1,012, 1,218 and 1,325 reporting establishments (2019–2025)"},
         geography={"es": "Establecimiento de atención; nunca residencia", "en": "Establishment of care; never residence"},
         stockflow={"es": "Stock semestral (diciembre como serie principal; junio solo como sensibilidad; nunca se suman ni promedian)", "en": "Semiannual stock (December as primary series; June only as sensitivity; never summed or averaged)"},
         denominator={"es": "Total NANEAS bajo control (P2501878) solo desde diciembre de 2023; establecimientos reportantes; población INE como contexto territorial", "en": "Total NANEAS under control (P2501878) only from December 2023; reporting establishments; INE population as territorial context"},
         breaks={"es": "P6 cambia de TGD amplio (2019–2020) a autismo y categorías desagregadas (2021); P2501878 existe solo desde diciembre de 2023 (sin fila de junio 2023); junio de 2020 registra 172 personas con TEA en 28 establecimientos (colapso del reporte)", "en": "P6 changes from broad PDD (2019–2020) to autism and disaggregated categories (2021); P2501878 exists only from December 2023 (no June 2023 row); June 2020 records 172 people with ASD in 28 establishments (reporting collapse)"},
         linkage={"es": "Stocks agregados sin personas; no enlazables con ingresos A05, GRD ni educación", "en": "Aggregate stocks without persons; not linkable to A05 entries, GRD or education"}),
    dict(key="deis", ids=["deis_egresos"],
         name={"es": "DEIS egresos hospitalarios (comprobación externa)", "en": "DEIS hospital discharges (external check)"},
         provider={"es": "DEIS, Ministerio de Salud", "en": "DEIS, Ministry of Health"},
         unit={"es": "Egreso hospitalario, una fila por egreso", "en": "Hospital discharge, one row per discharge"},
         period={"es": "2019–2024 (6 archivos anuales)", "en": "2019–2024 (6 annual files)"},
         coverage={"es": "Todos los egresos de establecimientos públicos y privados informados al DEIS (universo más amplio que el panel GRD)", "en": "All discharges from public and private establishments reported to DEIS (broader universe than the GRD panel)"},
         geography={"es": "Residencia del paciente (COMUNA_RESIDENCIA, 5 dígitos con cero inicial) y pertenencia del establecimiento", "en": "Patient's residence (COMUNA_RESIDENCIA, 5 digits with leading zero) and establishment sector"},
         stockflow={"es": "Flujo (egresos del año)", "en": "Flow (discharges of the year)"},
         denominator={"es": "Egresos DEIS del mismo año; población INE", "en": "DEIS discharges of the same year; INE population"},
         breaks={"es": "Solo dos campos diagnósticos: DIAG1 y DIAG2 (causa externa, nunca F84), por lo que «F84 en cualquier posición» equivale a F84 principal; el conjunto de columnas cambia por año; variantes oficiales de 15 columnas en 2021 y 2024", "en": "Only two diagnosis fields: DIAG1 and DIAG2 (external cause, never F84), so 'F84 in any position' equals F84 principal; column set changes by year; official 15-column variants in 2021 and 2024"},
         linkage={"es": "Sin identificador; sin enlace con episodios GRD ni personas; solo comparaciones principal frente a principal", "en": "No identifier; no linkage to GRD episodes or persons; principal-versus-principal comparisons only"}),
    dict(key="fonasa_agg", ids=["fonasa_aggregates"],
         name={"es": "FONASA beneficiarios (agregados de diciembre)", "en": "FONASA beneficiaries (December aggregates)"},
         provider={"es": "Fondo Nacional de Salud (FONASA)", "en": "Fondo Nacional de Salud (FONASA)"},
         unit={"es": "Celda agregada (combinación de dimensiones × conteo) al 31 de diciembre", "en": "Aggregated cell (dimension combination × count) at 31 December"},
         period={"es": "Diciembre 2018–2025 (8 archivos)", "en": "December 2018–2025 (8 files)"},
         coverage={"es": "Beneficiarios FONASA: 14.841.577 (2019) a 17.132.611 (2025)", "en": "FONASA beneficiaries: 14,841,577 (2019) to 17,132,611 (2025)"},
         geography={"es": "Mixta: comuna del centro APS para inscritos y domicilio para no inscritos; la variable INSCRITO_APS que separa la mezcla desaparece desde 2023", "en": "Mixed: APS-centre comuna for enrolled persons and domicile for non-enrolled; the INSCRITO_APS variable that separates the mixture disappears from 2023"},
         stockflow={"es": "Stock (corte de diciembre)", "en": "Stock (December snapshot)"},
         denominator={"es": "Capa de aseguramiento público por comuna, tramo etario y sexo (distinta de INE, APS y REM-20)", "en": "Public insurance layer by comuna, age band and sex (distinct from INE, APS and REM-20)"},
         breaks={"es": "Esquema cambia en 2021, 2023, 2024 y 2025; tramos etarios de 23 bandas (2018–2022 y 2025), 10 bandas decenales (2023) y 18 bandas (2024); filas repetidas aditivas en 2018–2020 (nunca deduplicar); columna de conteo renombrada en 2024; codificación Latin-1 (2018–2024) y UTF-8 (2025)", "en": "Schema changes in 2021, 2023, 2024 and 2025; age bands: 23 (2018–2022 and 2025), 10 ten-year bands (2023) and 18 (2024); additive repeated rows in 2018–2020 (never deduplicate); count column renamed in 2024; Latin-1 (2018–2024) and UTF-8 (2025) encodings"},
         linkage={"es": "Agregado sin personas; no enlazable con REM ni GRD", "en": "Aggregate without persons; not linkable to REM or GRD"}),
    dict(key="fonasa_aps", ids=["fonasa_aps"],
         name={"es": "FONASA inscritos en atención primaria (APS)", "en": "FONASA primary-care (APS) enrolment"},
         provider={"es": "FONASA", "en": "FONASA"},
         unit={"es": "Celda centro APS × tramo × grupo etario × sexo (TOTAL_INSCRITOS al 31 de diciembre)", "en": "Cell APS centre × tramo × age group × sex (TOTAL_INSCRITOS at 31 December)"},
         period={"es": "Diciembre 2019–2025 (7 archivos)", "en": "December 2019–2025 (7 files)"},
         coverage={"es": "Inscritos en centros APS: 13.777.051 (2019) a 15.791.862 (2025); 1.890 a 2.091 centros", "en": "Persons enrolled in APS centres: 13,777,051 (2019) to 15,791,862 (2025); 1,890 to 2,091 centres"},
         geography={"es": "Comuna del centro APS (lugar de atención); nunca residencia", "en": "APS-centre comuna (place of care); never residence"},
         stockflow={"es": "Stock (corte de diciembre)", "en": "Stock (December snapshot)"},
         denominator={"es": "Cobertura operativa por centro (offset para indicadores REM de APS); el panel continuo de 1.871 códigos de centro retiene 99,87 % (2019) y 97,54 % (2025) de los inscritos", "en": "Operational coverage per centre (offset for REM primary-care indicators); the continuous panel of 1,871 centre codes retains 99.87% (2019) and 97.54% (2025) of enrolled persons"},
         breaks={"es": "2024: cambian nombres de variables y grupos etarios (bandas de 20 años en 2019–2023); codificación Latin-1 (2019–2023) y UTF-8 (2024–2025); tramo X y tramos faltantes se mantienen separados", "en": "2024: variable names and age groups change (20-year bands in 2019–2023); Latin-1 (2019–2023) and UTF-8 (2024–2025) encodings; tramo X and missing tramos kept separate"},
         linkage={"es": "Agregado sin personas", "en": "Aggregate without persons"}),
    dict(key="isapre", ids=["isapre_communal"],
         name={"es": "ISAPRE beneficiarios por comuna", "en": "ISAPRE beneficiaries by comuna"},
         provider={"es": "Superintendencia de Salud", "en": "Superintendencia de Salud"},
         unit={"es": "Agregado de cotizantes y cargas por comuna, edad y sexo en diciembre", "en": "Aggregate of contributors and dependants by comuna, age and sex in December"},
         period={"es": "Diciembre 2019–2025 (7 archivos)", "en": "December 2019–2025 (7 files)"},
         coverage={"es": "Beneficiarios ISAPRE: 3.431.126 (2019) a 2.517.305 (2025)", "en": "ISAPRE beneficiaries: 3,431,126 (2019) to 2,517,305 (2025)"},
         geography={"es": "Comuna administrativa del beneficiario (según la Superintendencia)", "en": "Administrative comuna of the beneficiary (as published by the Superintendencia)"},
         stockflow={"es": "Stock (corte de diciembre)", "en": "Stock (December snapshot)"},
         denominator={"es": "Capa de aseguramiento privado; FONASA + ISAPRE = 95,6 % (2019) y 97,2 % (2025) de la proyección INE (no es tasa de no aseguramiento)", "en": "Private insurance layer; FONASA + ISAPRE = 95.6% (2019) and 97.2% (2025) of the INE projection (not a non-insurance rate)"},
         breaks={"es": "Formato .xls → .xlsx y edades simples → grupos quinquenales en 2021; hoja separada de no natos/sin clasificar en 2019–2020; las hojas por sexo y «Total» son vistas duplicadas", "en": "Format .xls → .xlsx and single ages → five-year groups in 2021; separate unborn/unclassified sheet in 2019–2020; sex sheets and 'Total' are duplicated views"},
         linkage={"es": "Agregado sin personas", "en": "Aggregate without persons"}),
    dict(key="ine2017", ids=["ine_population_base2017", "repo_population_parquet"],
         name={"es": "INE proyecciones de población base Censo 2017", "en": "INE population projections, Census 2017 base"},
         provider={"es": "Instituto Nacional de Estadísticas (INE)", "en": "Instituto Nacional de Estadísticas (INE)"},
         unit={"es": "Celda comuna × sexo × edad simple × año (y derivado local en parquet reconciliado)", "en": "Cell comuna × sex × single age × year (and a reconciled local parquet derivative)"},
         period={"es": "2002–2035 (se usan 2019–2025)", "en": "2002–2035 (2019–2025 used)"},
         coverage={"es": "Población residente, 346 comunas; nacional 19.107.216 (2019) a 20.206.953 (2025)", "en": "Resident population, 346 comunas; national 19,107,216 (2019) to 20,206,953 (2025)"},
         geography={"es": "Comuna de residencia (código INE de 4 dígitos; DEIS usa 5 con cero inicial); alias Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)", "en": "Comuna of residence (4-digit INE code; DEIS uses 5 digits with leading zero); aliases Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)"},
         stockflow={"es": "Stock (población a mitad de año)", "en": "Stock (mid-year population)"},
         denominator={"es": "Denominador poblacional territorial (tasas por 100.000 habitantes) y estandarización directa OMS", "en": "Territorial population denominator (rates per 100,000 population) and WHO direct standardisation"},
         breaks={"es": "Base Censo 2017; no se combina con Censo 2024 ni base 2024 sin marca explícita", "en": "Census 2017 base; never combined with Census 2024 or the 2024 base without an explicit flag"},
         linkage={"es": "Territorial; no son usuarios de un prestador específico", "en": "Territorial; not users of a specific provider"}),
    dict(key="ine2024", ids=["ine_censo2024", "ine_base2024_national"],
         name={"es": "INE Censo 2024 y proyección nacional base 2024 (sensibilidad)", "en": "INE Census 2024 and national projection, 2024 base (sensitivity)"},
         provider={"es": "Instituto Nacional de Estadísticas (INE)", "en": "Instituto Nacional de Estadísticas (INE)"},
         unit={"es": "Tabulado censal comuna × sexo × edad quinquenal (D1) y tabulado de discapacidad (P1); estimación nacional por sexo y edad 1992–2070 (base 2024)", "en": "Census tabulation comuna × sex × five-year age (D1) and disability tabulation (P1); national estimate by sex and age 1992–2070 (2024 base)"},
         period={"es": "Censo 2024; proyección 1992–2070", "en": "Census 2024; projection 1992–2070"},
         coverage={"es": "Población empadronada en el Censo 2024 (18.480.432); población residente nacional", "en": "Population enumerated in Census 2024 (18,480,432); national resident population"},
         geography={"es": "Comuna de empadronamiento; nacional", "en": "Comuna of enumeration; national"},
         stockflow={"es": "Stock (noche censal 2024; proyección)", "en": "Stock (census night 2024; projection)"},
         denominator={"es": "Denominador observado de 2024 y puente entre bases censales (solo sensibilidad)", "en": "Observed 2024 denominator and bridge between census bases (sensitivity only)"},
         breaks={"es": "Base distinta de las proyecciones 2017; sin desagregación comunal equivalente en la base 2024; P1 es contexto de discapacidad, no autismo", "en": "Different base from the 2017 projections; no comuna disaggregation equivalent in the 2024 base; P1 is disability context, not autism"},
         linkage={"es": "Territorial", "en": "Territorial"}),
    dict(key="rem20", ids=["deis_rem20"],
         name={"es": "REM-20 indicadores hospitalarios (egresos y días-cama)", "en": "REM-20 hospital indicators (discharges and bed-days)"},
         provider={"es": "DEIS, Ministerio de Salud", "en": "DEIS, Ministry of Health"},
         unit={"es": "Establecimiento × área funcional × mes", "en": "Establishment × functional area × month"},
         period={"es": "2014–julio 2026 (se usan 2019–2025)", "en": "2014–July 2026 (2019–2025 used)"},
         coverage={"es": "Hospitales públicos que reportan REM-20: 192 a 203 establecimientos por año", "en": "Public hospitals reporting REM-20: 192 to 203 establishments per year"},
         geography={"es": "Establecimiento (código DEIS); nunca residencia", "en": "Establishment (DEIS code); never residence"},
         stockflow={"es": "Actividad y capacidad (egresos mensuales y días-cama; las camas son capacidad)", "en": "Activity and capacity (monthly discharges and bed-days; beds are capacity)"},
         denominator={"es": "Intensidad de actividad/capacidad hospitalaria, nunca población cubierta; el panel de 188 establecimientos con 12 meses en todos los años retiene 99,76 % (2019) y 98,16 % (2025) de los egresos", "en": "Hospital activity/capacity intensity, never a covered population; the panel of 188 establishments with 12 months in every year retains 99.76% (2019) and 98.16% (2025) of discharges"},
         breaks={"es": "Conjunto de datos mutable de actualización continua (descarga 2026-09-04); sin diagnósticos ni personas", "en": "Continuously updated mutable dataset (download 2026-09-04); no diagnoses or persons"},
         linkage={"es": "Códigos de establecimiento enlazan al catálogo DEIS; sin personas; la compatibilidad con los códigos GRD debe verificarse", "en": "Establishment codes link to the DEIS catalogue; no persons; compatibility with GRD hospital codes must be verified"}),
    dict(key="endide", ids=["endide_2022"],
         name={"es": "ENDIDE 2022 (Encuesta Nacional de Discapacidad y Dependencia)", "en": "ENDIDE 2022 (National Disability and Dependency Survey)"},
         provider={"es": "Ministerio de Desarrollo Social y Familia", "en": "Ministry of Social Development and Family"},
         unit={"es": "Persona encuestada (adultos, cuidadores y NNA), diseño complejo: ponderador fexp, estratos estrato, conglomerados cod_upm", "en": "Surveyed person (adults, caregivers and children), complex design: weight fexp, strata estrato, clusters cod_upm"},
         period={"es": "2022", "en": "2022"},
         coverage={"es": "Población en hogares de Chile (representatividad nacional y regional); autismo reportado no ponderado: 72 adultos y 163 NNA (139 con confirmación profesional)", "en": "Household population of Chile (national and regional representativeness); unweighted reported autism: 72 adults and 163 children (139 with professional confirmation)"},
         geography={"es": "Nacional y regional; nunca comuna", "en": "National and regional; never comuna"},
         stockflow={"es": "Encuesta transversal (benchmark poblacional)", "en": "Cross-sectional survey (population benchmark)"},
         denominator={"es": "Población ponderada de cada dominio (adultos 18+; NNA 2–17)", "en": "Weighted population of each domain (adults 18+; children 2–17)"},
         breaks={"es": "Autorreporte o reporte del cuidador; no equivale a un código F84 administrativo", "en": "Self- or caregiver report; not equivalent to an administrative F84 code"},
         linkage={"es": "Sin enlace con registros; benchmark de orden de magnitud", "en": "No linkage to registers; order-of-magnitude benchmark"}),
    dict(key="encavi", ids=["encavi_2023_2024"],
         name={"es": "ENCAVI 2023–2024 (Encuesta Nacional de Calidad de Vida y Salud)", "en": "ENCAVI 2023–2024 (National Quality of Life and Health Survey)"},
         provider={"es": "Ministerio de Salud", "en": "Ministry of Health"},
         unit={"es": "Persona encuestada de 15 años o más (16.590), diseño complejo: ponderador w_personas_cal, estratos varstrat, conglomerados varunit", "en": "Surveyed person aged 15 or more (16,590), complex design: weight w_personas_cal, strata varstrat, clusters varunit"},
         period={"es": "2023–2024", "en": "2023–2024"},
         coverage={"es": "Población de 15 años o más de Chile; 80 respuestas positivas no ponderadas de diagnóstico de TEA", "en": "Population aged 15 or more of Chile; 80 unweighted positive ASD-diagnosis responses"},
         geography={"es": "Nacional y regional; nunca comuna", "en": "National and regional; never comuna"},
         stockflow={"es": "Encuesta transversal (benchmark poblacional)", "en": "Cross-sectional survey (population benchmark)"},
         denominator={"es": "Población ponderada de 15 años o más", "en": "Weighted population aged 15 or more"},
         breaks={"es": "Diagnóstico reportado (nota al encuestador: diagnóstico médico tradicional); no equivale a F84 administrativo", "en": "Reported diagnosis (interviewer note: traditional medical diagnosis); not equivalent to administrative F84"},
         linkage={"es": "Sin enlace con registros", "en": "No linkage to registers"}),
    dict(key="pie", ids=["mineduc_pie_reports"],
         name={"es": "MINEDUC Programa de Integración Escolar (Apuntes 59 y 60) y reporte SINACES Ley 21.545", "en": "MINEDUC School Integration Programme (Apuntes 59 and 60) and SINACES Law 21.545 report"},
         provider={"es": "Ministerio de Educación (Centro de Estudios / SINACES)", "en": "Ministry of Education (Centro de Estudios / SINACES)"},
         unit={"es": "Tablas agregadas publicadas de estudiantes en PIE por diagnóstico (3 informes PDF; página y tabla registradas)", "en": "Published aggregate tables of PIE students by diagnosis (3 PDF reports; page and table recorded)"},
         period={"es": "2019–2023 (Apuntes 60), 2023 por sexo (Apuntes 59), 2022–2025 (SINACES)", "en": "2019–2023 (Apuntes 60), 2023 by sex (Apuntes 59), 2022–2025 (SINACES)"},
         coverage={"es": "Estudiantes registrados en PIE (registro para subvención y cupos; MINEDUC advierte que no incluye a todos los estudiantes autistas)", "en": "Students registered in PIE (registration for subsidy and quotas; MINEDUC warns it does not include all autistic students)"},
         geography={"es": "Nacional", "en": "National"},
         stockflow={"es": "Stock (registro del año escolar)", "en": "Stock (school-year registration)"},
         denominator={"es": "Matrícula total del mismo universo PIE cuando se publica (385.995 a 473.006 en 2019–2023; postulantes SINACES 438.783, 473.006, 499.110 y 475.710 en 2022–2025)", "en": "Total enrolment of the same PIE universe when published (385,995 to 473,006 in 2019–2023; SINACES applicants 438,783, 473,006, 499,110 and 475,710 in 2022–2025)"},
         breaks={"es": "TEA estricto, TEA-Asperger y armonizado (TEA + TEA-Asperger) exigen reglas separadas; 2022: SINACES escribe 42.945 mientras 45.014 − 2.074 (escuelas especiales) = 42.940 (Apuntes 60); 2024–2025 solo existe la serie armonizada", "en": "Strict ASD, ASD-Asperger and harmonised (ASD + ASD-Asperger) require separate rules; 2022: SINACES writes 42,945 while 45,014 − 2,074 (special schools) = 42,940 (Apuntes 60); 2024–2025 only the harmonised series exists"},
         linkage={"es": "Agregados sin microdatos; no enlazables con registros de salud", "en": "Aggregates without microdata; not linkable to health registers"}),
    dict(key="junaeb", ids=["junaeb_eve_microdata", "junaeb_eve_metadata"],
         name={"es": "JUNAEB Encuesta de Vulnerabilidad Estudiantil (EVE)", "en": "JUNAEB Student Vulnerability Survey (EVE)"},
         provider={"es": "Junta Nacional de Auxilio Escolar y Becas (JUNAEB)", "en": "Junta Nacional de Auxilio Escolar y Becas (JUNAEB)"},
         unit={"es": "Registro de estudiante desidentificado, un archivo por nivel (parvularia, 1º básico, 5º básico, 1º medio) y año; cuestionarios y diccionarios anuales", "en": "De-identified student record, one file per level (pre-school, grade 1, grade 5, grade 9) and year; annual questionnaires and dictionaries"},
         period={"es": "2019–2025 (28 archivos de microdatos)", "en": "2019–2025 (28 microdata files)"},
         coverage={"es": "Estudiantes de cohortes escolares seleccionadas con cuestionario de cuidadores (cobertura selectiva, no todos los estudiantes); TEA no ponderado 2024: 17.641 / 10.245 / 7.468; 2025: 18.785 / 12.536 / 9.887 / 9.164", "en": "Students in selected school cohorts answering the caregiver questionnaire (selective coverage, not all students); unweighted ASD 2024: 17,641 / 10,245 / 7,468; 2025: 18,785 / 12,536 / 9,887 / 9,164"},
         geography={"es": "Establecimiento y comuna del colegio; no residencia", "en": "School establishment and comuna; not residence"},
         stockflow={"es": "Encuesta escolar transversal (reporte de cuidadores)", "en": "Cross-sectional school survey (caregiver report)"},
         denominator={"es": "Estudiantes ponderados del mismo nivel y año (EXP_REG en 2024; EXP en 2025)", "en": "Weighted students of the same level and year (EXP_REG in 2024; EXP in 2025)"},
         breaks={"es": "Redacción y códigos cambian por año (diccionarios solo 2019, 2021, 2024 y 2025); sin ítem TEA en 2019–2022; 2023 con ítem pero sin ponderador publicado; 2024 1º medio con variable TEA completamente vacía (no estimable, no cero)", "en": "Wording and codes change by year (dictionaries only 2019, 2021, 2024 and 2025); no ASD item in 2019–2022; 2023 has the item but no published weight; 2024 grade 9 ASD variable completely empty (not estimable, not zero)"},
         linkage={"es": "Sin enlace con PIE, registros de salud ni otros años", "en": "No linkage to PIE, health registers or other years"}),
    dict(key="support", ids=["grd_dictionaries", "rem_serie_a_dictionary", "rem_serie_p_dictionary", "deis_egresos_dictionary", "fonasa_dictionary",
                             "deis_establishments", "repo_shapes", "rem_pathway_codes", "casen_2024", "casen_2024_metadata", "sae_poverty_2024"],
         name={"es": "Documentación y contexto: diccionarios (GRD, REM A/P, DEIS, FONASA), catálogo de establecimientos DEIS, cartografía, mapa de códigos REM, CASEN 2024 y SAE 2024", "en": "Documentation and context: dictionaries (GRD, REM A/P, DEIS, FONASA), DEIS establishment catalogue, cartography, REM code map, CASEN 2024 and SAE 2024"},
         provider={"es": "FONASA; DEIS; Ministerio de Desarrollo Social y Familia; repositorio", "en": "FONASA; DEIS; Ministry of Social Development and Family; repository"},
         unit={"es": "Diccionarios anuales de códigos, catálogo de establecimientos, capas de polígonos, mapa de códigos verificado y fuentes de contexto socioeconómico", "en": "Annual code dictionaries, establishment catalogue, polygon layers, verified code map and socioeconomic context sources"},
         period={"es": "2019–2025 (diccionarios); catálogo y cartografía vigentes; CASEN y SAE 2024", "en": "2019–2025 (dictionaries); current catalogue and cartography; CASEN and SAE 2024"},
         coverage={"es": "No aplicable (metadatos y contexto)", "en": "Not applicable (metadata and context)"},
         geography={"es": "Comuna por código (crosswalk auditable; sin coincidencia difusa)", "en": "Comuna by code (auditable crosswalk; no fuzzy matching)"},
         stockflow={"es": "No aplicable", "en": "Not applicable"},
         denominator={"es": "No aplicable (CASEN solo contexto de aseguramiento; SAE covariable territorial con incertidumbre)", "en": "Not applicable (CASEN as insurance context only; SAE territorial covariate with uncertainty)"},
         breaks={"es": "Cada código REM se confirma contra el diccionario de su año; el catálogo de establecimientos es mutable (versión 2026-09-01); CASEN y SAE no son fuentes de autismo", "en": "Every REM code is confirmed against its annual dictionary; the establishment catalogue is mutable (version 2026-09-01); CASEN and SAE are not autism sources"},
         linkage={"es": "Solo enlace por código", "en": "Code-based linkage only"}),
]


def build_t1(prov: pd.DataFrame, summ: pd.DataFrame, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, num = [], []
    for spec in T1_ROWS:
        s = summ.loc[summ.source_id.isin(spec["ids"])]
        p = prov.loc[prov.source_id.isin(spec["ids"])]
        n = int(s.n_artefacts.sum())
        gb = float(s.bytes_total.sum()) / 1e9
        listed = int(s.n_listed_in_manifest.sum())
        ok = int(s.n_sha_match.sum())
        mism = int(s.n_sha_mismatch.sum())
        dates = sorted({str(d)[:10] for d in p.downloaded_or_version_date.dropna()})
        latest = dates[-1] if dates else ""
        if listed > 0:
            files_txt = T("t1_files_fmt", lang, n=fnum(n, 0, lang), gb=fnum(gb, 2, lang), ok=fnum(ok, 0, lang), listed=fnum(listed, 0, lang))
        else:
            files_txt = T("t1_files_nomanifest", lang, n=fnum(n, 0, lang), gb=fnum(gb, 2, lang))
        if latest:
            files_txt += f"; {T('t1_version', lang, d=latest)}"
        rows.append({
            T("t1_source", lang): spec["name"][lang], T("t1_provider", lang): spec["provider"][lang], T("t1_unit", lang): spec["unit"][lang],
            T("t1_period", lang): spec["period"][lang], T("t1_coverage", lang): spec["coverage"][lang], T("t1_geography", lang): spec["geography"][lang],
            T("t1_stockflow", lang): spec["stockflow"][lang], T("t1_denominator", lang): spec["denominator"][lang], T("t1_breaks", lang): spec["breaks"][lang],
            T("t1_linkage", lang): spec["linkage"][lang], T("t1_files", lang): files_txt,
        })
        yrs = sorted({y for per in p.period.dropna() for y in years_in_text(per)})
        num.append(dict(row_key=spec["key"], source_ids="|".join(spec["ids"]), n_artefacts=n, bytes_total=int(s.bytes_total.sum()), gb=round(gb, 3),
                        n_listed_in_manifest=listed, n_sha_match=ok, n_sha_mismatch=mism, latest_version_date=latest,
                        period_year_min=(yrs[0] if yrs else np.nan), period_year_max=(yrs[-1] if yrs else np.nan),
                        stock_or_flow="|".join(sorted(s.stock_or_flow.astype(str).unique())), provider="|".join(sorted(s.provider.astype(str).unique()))))
    return pd.DataFrame(rows), pd.DataFrame(num)


def t1_titles(lang: str, prov: pd.DataFrame) -> dict:
    n_art = len(prov)
    gb = prov.bytes.sum() / 1e9
    if lang == "es":
        return {"title": "Tabla 1. Fuentes de datos, unidad de observación, cobertura, quiebres de definición y ausencia de enlace individual, Chile 2019–2025",
                "note": (f"Una fila por fuente analítica; la última fila agrupa documentación y contexto. Procedencia completa (archivo, SHA-256, fecha, columnas y reglas de uso) en data_provenance.csv "
                         f"({fnum(n_art, 0, lang)} artefactos, {fnum(gb, 1, lang)} GB) y provenance_summary_by_source.csv (módulo 00_provenance). "
                         "Stock = corte en una fecha (población, aseguramiento, inscritos, población bajo control, matrícula); flujo = eventos del período (episodios, egresos, ingresos, intervenciones). "
                         "Cuatro capas de denominador responden preguntas distintas: INE (residencia), FONASA/ISAPRE (aseguramiento), inscritos APS (cobertura operativa por centro) y REM-20 (actividad/capacidad, nunca población cubierta). "
                         "Lugar de atención (GRD hospital, REM, APS, REM-20) y residencia (INE, DEIS, GRD comuna) no se mezclan sin nota de compatibilidad. "
                         f"{T('no_linkage_note', lang)} {T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)} {T('identical_variants', lang)}")}
    return {"title": "Table 1. Data sources, unit of observation, coverage, definition breaks and absence of person-level linkage, Chile 2019–2025",
            "note": (f"One row per analytical source; the last row groups documentation and context. Full provenance (file, SHA-256, date, columns and use rules) in data_provenance.csv "
                     f"({fnum(n_art, 0, lang)} artefacts, {fnum(gb, 1, lang)} GB) and provenance_summary_by_source.csv (module 00_provenance). "
                     "Stock = snapshot at a date (population, insurance, enrolment, population under control, school registration); flow = events of the period (episodes, discharges, entries, interventions). "
                     "Four denominator layers answer different questions: INE (residence), FONASA/ISAPRE (insurance), APS enrolment (operational coverage per centre) and REM-20 (activity/capacity, never a covered population). "
                     "Place of care (GRD hospital, REM, APS, REM-20) and residence (INE, DEIS, GRD comuna) are never mixed without a compatibility note. "
                     f"{T('no_linkage_note', lang)} {T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)} {T('identical_variants', lang)}")}


# ---------------------------------------------------------------------------
# T2 — GRD anual con todas las sensibilidades
# ---------------------------------------------------------------------------
class GrdCore:
    def __init__(self):
        self.g = C.read_tidy("grd_year_summary")
        self.sub = C.read_tidy("grd_subcode_year")
        self.pop = C.read_tidy("models_population_rates")
        fixed = C.read_tidy("grd_fixed_panel_hospitals")
        self.n_fixed = int(fixed.in_fixed_panel.astype(bool).sum())

    def sel(self, variant: str, panel: str, activity: str, position: str) -> pd.DataFrame:
        d = self.g[(self.g.variant == variant) & (self.g.panel == panel) & (self.g.activity == activity) & (self.g.position == position)]
        return d.set_index("year").reindex(YEARS_GRD)

    def pop_sel(self, variant: str, position: str, sex: str) -> pd.DataFrame:
        d = self.pop[(self.pop.variant == variant) & (self.pop.position == position) & (self.pop.sex == sex)]
        return d.set_index("year").reindex(YEARS_GRD)

    def rett(self) -> pd.Series:
        """Episodios con F84.2 en cualquier posición: el código en sí, lleve o no otro código F84 en el episodio."""
        d = self.sub[(self.sub.subcode == "F842") & (self.sub.position == "any")]
        return d.set_index("year").n_episodes.reindex(YEARS_GRD)

    def rett_only(self) -> pd.Series:
        """Diferencia ENTRE VARIANTES: episodios que el F84 completo cuenta y el F84 sin Rett no, es decir, aquellos
        cuyo único código F84 es F84.2. Es siempre ≤ rett(): un episodio con F84.2 y además F84.0 lo cuentan las dos
        variantes y no entra en la diferencia. Se calcula igual en las dos variantes (con_rett − sin_rett), de modo que
        la fila imprime el mismo número en los dos documentos y coincide con la cifra que da el texto del artículo."""
        con = self.sel("con_rett", "observed", "all", "any").n_episodes_f84
        sin = self.sel("sin_rett", "observed", "all", "any").n_episodes_f84
        return (con - sin).reindex(YEARS_GRD)


def build_t2(core: GrdCore, variant: str, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    V, O = variant, OTHER_VARIANT[variant]
    obs_any = core.sel(V, "observed", "all", "any")
    obs_pr = core.sel(V, "observed", "all", "principal")
    obs_sec = core.sel(V, "observed", "all", "secondary_only")
    obs_both = core.sel(V, "observed", "all", "principal_and_secondary")
    fix_any = core.sel(V, "fixed65", "all", "any")
    fix_pr = core.sel(V, "fixed65", "all", "principal")
    hosp_any = core.sel(V, "observed", "hospitalisation", "any")
    hosp_pr = core.sel(V, "observed", "hospitalisation", "principal")
    hosp_fix_any = core.sel(V, "fixed65", "hospitalisation", "any")
    cma_any = core.sel(V, "observed", "cma", "any")
    oth_any = core.sel(V, "observed", "other", "any")
    oth_var = core.sel(O, "observed", "all", "any")
    strict = core.sel("strict_autism_f840", "observed", "all", "any")
    pop_any = core.pop_sel(V, "any", "TOTAL")
    pop_any_m = core.pop_sel(V, "any", "HOMBRE")
    pop_any_f = core.pop_sel(V, "any", "MUJER")
    pop_pr = core.pop_sel(V, "principal", "TOTAL")
    rett = core.rett()
    rett_only = core.rett_only()
    absent = T("category_absent", lang)

    rows: list[dict] = []
    numeric: list[dict] = []

    def add(block: str, key: str, unit_key: str, fmt, num, label_kw: dict | None = None):
        label = T(key, lang, **(label_kw or {}))
        r = {T("section", lang): T(block, lang), T("indicator", lang): label, T("unit", lang): T(unit_key, lang)}
        nrow = {"row_key": key, "variant": V, "block": block}
        for y in YEARS_GRD:
            r[str(y)] = fmt(y)
            nrow[str(y)] = num(y)
        rows.append(r)
        numeric.append(nrow)

    def count(df, col):
        return (lambda y: fnum(df.loc[y, col], 0, lang)), (lambda y: df.loc[y, col])

    def rate(df):
        return (lambda y: frate(df.loc[y, "rate_per_100k_episodes"], df.loc[y, "rate_lo"], df.loc[y, "rate_hi"], 1, lang)), (lambda y: df.loc[y, "rate_per_100k_episodes"])

    def other_count(df, col):
        def f(y):
            tot = df.loc[y, "n_episodes_total_same_panel_activity"]
            return absent if (is_missing(tot) or float(tot) == 0) else fnum(df.loc[y, col], 0, lang)

        def n(y):
            tot = df.loc[y, "n_episodes_total_same_panel_activity"]
            return np.nan if (is_missing(tot) or float(tot) == 0) else df.loc[y, col]
        return f, n

    # Panel y episodios
    add("t2_block_panel", "t2_hospitals_observed", "t2_col_unit_hosp", *count(obs_any, "hospitals_n"))
    add("t2_block_panel", "t2_hospitals_fixed", "t2_col_unit_hosp", lambda y: fnum(core.n_fixed, 0, lang), lambda y: core.n_fixed)
    add("t2_block_panel", "t2_episodes_observed_all", "t2_col_unit_n", *count(obs_any, "n_episodes_total_same_panel_activity"))
    add("t2_block_panel", "t2_episodes_fixed_all", "t2_col_unit_n", *count(fix_any, "n_episodes_total_same_panel_activity"))
    add("t2_block_panel", "t2_episodes_hosp", "t2_col_unit_n", *count(hosp_any, "n_episodes_total_same_panel_activity"))
    add("t2_block_panel", "t2_episodes_cma", "t2_col_unit_n", *count(cma_any, "n_episodes_total_same_panel_activity"))
    add("t2_block_panel", "t2_episodes_other", "t2_col_unit_n", *other_count(oth_any, "n_episodes_total_same_panel_activity"))
    # F84 documentado
    add("t2_block_f84", "t2_any_obs_n", "t2_col_unit_n", *count(obs_any, "n_episodes_f84"))
    add("t2_block_f84", "t2_any_obs_rate", "t2_col_unit_rate", *rate(obs_any))
    add("t2_block_f84", "t2_any_fix_n", "t2_col_unit_n", *count(fix_any, "n_episodes_f84"))
    add("t2_block_f84", "t2_any_fix_rate", "t2_col_unit_rate", *rate(fix_any))
    add("t2_block_f84", "t2_prin_obs_n", "t2_col_unit_n", *count(obs_pr, "n_episodes_f84"))
    add("t2_block_f84", "t2_prin_obs_rate", "t2_col_unit_rate", *rate(obs_pr))
    add("t2_block_f84", "t2_prin_fix_n", "t2_col_unit_n", *count(fix_pr, "n_episodes_f84"))
    add("t2_block_f84", "t2_prin_fix_rate", "t2_col_unit_rate", *rate(fix_pr))
    add("t2_block_f84", "t2_sec_only", "t2_col_unit_npct",
        lambda y: fn_pct(obs_sec.loc[y, "n_episodes_f84"], 100 * obs_sec.loc[y, "n_episodes_f84"] / obs_any.loc[y, "n_episodes_f84"], lang),
        lambda y: 100 * obs_sec.loc[y, "n_episodes_f84"] / obs_any.loc[y, "n_episodes_f84"])
    add("t2_block_f84", "t2_prin_and_sec", "t2_col_unit_n", *count(obs_both, "n_episodes_f84"))
    # Modalidad
    add("t2_block_activity", "t2_hosp_any_n", "t2_col_unit_n", *count(hosp_any, "n_episodes_f84"))
    add("t2_block_activity", "t2_hosp_any_rate", "t2_col_unit_rate", *rate(hosp_any))
    add("t2_block_activity", "t2_hosp_fix_any_n", "t2_col_unit_n", *count(hosp_fix_any, "n_episodes_f84"))
    add("t2_block_activity", "t2_hosp_fix_any_rate", "t2_col_unit_rate", *rate(hosp_fix_any))
    add("t2_block_activity", "t2_hosp_prin_n", "t2_col_unit_n", *count(hosp_pr, "n_episodes_f84"))
    add("t2_block_activity", "t2_hosp_prin_rate", "t2_col_unit_rate", *rate(hosp_pr))
    add("t2_block_activity", "t2_cma_any_n", "t2_col_unit_n", *count(cma_any, "n_episodes_f84"))
    add("t2_block_activity", "t2_cma_any_rate", "t2_col_unit_rate", *rate(cma_any))
    add("t2_block_activity", "t2_other_any_n", "t2_col_unit_n", *other_count(oth_any, "n_episodes_f84"))
    # Profundidad
    add("t2_block_depth", "t2_depth_all", "t2_col_unit_depth",
        lambda y: f"{fnum(obs_any.loc[y, 'coding_depth_mean_all'], 2, lang)} ({fnum(obs_any.loc[y, 'coding_depth_median_all'], 0, lang)})",
        lambda y: obs_any.loc[y, "coding_depth_mean_all"])
    add("t2_block_depth", "t2_depth_f84", "t2_col_unit_depth",
        lambda y: f"{fnum(obs_any.loc[y, 'coding_depth_mean_f84'], 2, lang)} ({fnum(obs_any.loc[y, 'coding_depth_median_f84'], 0, lang)})",
        lambda y: obs_any.loc[y, "coding_depth_mean_f84"])
    # Personas
    add("t2_block_persons", "t2_persons_any", "t2_col_unit_persons", *count(obs_any, "persons_within_year"))
    add("t2_block_persons", "t2_episodes_per_person", "t2_col_unit_ratio",
        lambda y: fnum(obs_any.loc[y, "n_episodes_f84"] / obs_any.loc[y, "persons_within_year"], 2, lang),
        lambda y: obs_any.loc[y, "n_episodes_f84"] / obs_any.loc[y, "persons_within_year"])
    add("t2_block_persons", "t2_persons_prin", "t2_col_unit_persons", *count(obs_pr, "persons_within_year"))
    add("t2_block_persons", "t2_no_id", "t2_col_unit_n", *count(obs_any, "n_f84_without_valid_id"))
    add("t2_block_persons", "t2_identifier", "t2_col_unit_text", lambda y: str(obs_any.loc[y, "identifier_column"]), lambda y: np.nan)
    # Población INE
    for key, df, col in [("t2_pop_crude_any", pop_any, "crude"), ("t2_pop_asr_any", pop_any, "asr"), ("t2_pop_crude_any_m", pop_any_m, "crude"),
                         ("t2_pop_crude_any_f", pop_any_f, "crude"), ("t2_pop_crude_prin", pop_pr, "crude"), ("t2_pop_asr_prin", pop_pr, "asr")]:
        add("t2_block_pop", key, "t2_col_unit_pop",
            (lambda y, df=df, col=col: frate(df.loc[y, col], df.loc[y, f"{col}_lo"], df.loc[y, f"{col}_hi"], 2, lang)),
            (lambda y, df=df, col=col: df.loc[y, col]))
    # Sensibilidad de definición
    ov = variant_label(O, lang)
    add("t2_block_sens", "t2_other_variant_n", "t2_col_unit_n", *count(oth_var, "n_episodes_f84"), label_kw={"v": ov})
    add("t2_block_sens", "t2_other_variant_rate", "t2_col_unit_rate", *rate(oth_var), label_kw={"v": ov})
    add("t2_block_sens", "t2_strict_n", "t2_col_unit_n", *count(strict, "n_episodes_f84"))
    add("t2_block_sens", "t2_strict_rate", "t2_col_unit_rate", *rate(strict))
    add("t2_block_sens", "t2_rett_n", "t2_col_unit_n", lambda y: fnum(rett.loc[y], 0, lang), lambda y: rett.loc[y])
    add("t2_block_sens", "t2_rett_only_n", "t2_col_unit_n", lambda y: fnum(rett_only.loc[y], 0, lang), lambda y: rett_only.loc[y])
    return pd.DataFrame(rows), pd.DataFrame(numeric)


def t2_titles(variant: str, lang: str, core: GrdCore) -> dict:
    obs = core.sel(variant, "observed", "all", "any")
    hosp = "/".join(fnum(h, 0, lang) for h in obs.hospitals_n)
    vl = variant_label(variant, lang)
    if lang == "es":
        return {"title": f"Tabla 2. Núcleo hospitalario GRD 2019–2024: episodios con F84 documentado por posición, panel, modalidad, profundidad diagnóstica, personas y población, con sensibilidades — variante {vl}",
                "note": (f"Fuente: GRD público (FONASA) 2019–2024, módulo 01_grd_core (grd_year_summary.csv, grd_subcode_year.csv) y módulo 06_models (models_population_rates.csv). "
                         f"Variante {vl}: códigos GRD {', '.join(CFG.VARIANTS[variant]['grd_subcodes'])} en DIAGNOSTICO1–DIAGNOSTICO35. "
                         "Unidad: episodio GRD (hospitalización o cirugía mayor ambulatoria); «F84 en cualquier posición» = episodios con F84 documentado (no «hospitalizaciones por autismo»); F84 principal como serie separada. "
                         f"Denominador de las tasas: episodios GRD del mismo año, panel y modalidad, por 100.000, con IC 95 % exactos de Poisson. Cobertura: panel observado de {hosp} hospitales (2019–2024); {C.fixed_panel_gloss(lang, 'named', n=int(core.n_fixed))}. "
                         "Otras modalidades (urgencia, hospitalización diurna, no identificada) existen solo en 2019; desde 2020 la categoría está ausente del archivo (no es cero). "
                         "Profundidad diagnóstica = número de diagnósticos codificados por episodio. Personas únicas solo dentro de cada año (el identificador cambia de formato entre 2020 y 2021; CIP_ENCRIPTADO 2019–2023, ID_BENEFICIARIO 2024); nunca se deduplica entre años. "
                         "Tasas por 100.000 habitantes: numerador por lugar de atención (red pública) y denominador INE base 2017 al 30 de junio (residencia), lectura complementaria; tasa estandarizada OMS con IC de Fay–Feuer. "
                         "La fila «solo F84.0» es idéntica en ambas variantes. Las dos últimas filas cuentan cosas distintas y no deben leerse como una sola: "
                         "«F84.2 en cualquier posición» son los episodios en que aparece el código F84.2, lleve además el episodio otro código F84 o no; "
                         "«diferencia entre variantes» son los episodios cuyo único código F84 es F84.2, es decir, exactamente lo que el F84 completo cuenta de más que el F84 sin Rett, "
                         f"que es la cifra que cita el texto del artículo. La segunda fila es siempre menor o igual que la primera, y ambas imprimen los mismos valores en las dos variantes. {T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)}")}
    return {"title": f"Table 2. GRD hospital core 2019–2024: episodes with documented F84 by code position, panel, activity, coding depth, persons and population, with sensitivities — {vl} variant",
            "note": (f"Source: public GRD (FONASA) 2019–2024, module 01_grd_core (grd_year_summary.csv, grd_subcode_year.csv) and module 06_models (models_population_rates.csv). "
                     f"Variant {vl}: GRD codes {', '.join(CFG.VARIANTS[variant]['grd_subcodes'])} in DIAGNOSTICO1–DIAGNOSTICO35. "
                     "Unit: GRD episode (hospitalisation or major ambulatory surgery); 'F84 in any position' = episodes with documented F84 (not 'hospitalisations for autism'); F84 principal as a separate series. "
                     f"Rate denominator: GRD episodes of the same year, panel and activity, per 100,000, with exact Poisson 95% CIs. Coverage: observed panel of {hosp} hospitals (2019–2024); {C.fixed_panel_gloss(lang, 'named', n=int(core.n_fixed))}. "
                     "Other activity (emergency, day hospital, unidentified) exists only in 2019; from 2020 the category is absent from the file (not zero). "
                     "Coding depth = number of coded diagnoses per episode. Unique persons within each year only (the identifier changes format between 2020 and 2021; CIP_ENCRIPTADO 2019–2023, ID_BENEFICIARIO 2024); never deduplicated across years. "
                     "Rates per 100,000 population: numerator by place of care (public network) and INE base-2017 denominator at 30 June (residence), complementary reading; WHO age-standardised rate with Fay–Feuer CI. "
                     "The 'F84.0 only' row is identical in both variants. The last two rows count different things and must not be read as one: "
                     "'F84.2 in any position' is the number of episodes in which the code F84.2 appears, whether or not the episode also carries another F84 code; "
                     "'difference between variants' is the number of episodes whose only F84 code is F84.2, that is, exactly what the full F84 family counts over and above the F84 family without Rett, "
                     f"which is the figure quoted in the article text. The second row is always less than or equal to the first, and both print the same values in the two variants. {T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)}")}


# ---------------------------------------------------------------------------
# T3 — ruta administrativa REM por módulo, código, era y establecimientos
# ---------------------------------------------------------------------------
UNIT_KEY = {"children reported": "u_children", "screening records": "u_screening_records", "screening results": "u_screening_results",
            "referral records": "u_referral_records", "entries reported": "u_entries", "exits reported": "u_exits", "interventions": "u_interventions",
            "people in stock": "u_stock"}


def t3_row_specs(variant: str) -> list[dict]:
    """Filas de la T3: módulo, código(s), variante de la tabla tidy, medida, grupo, rótulo, sensibilidad de panel estable/junio."""
    fam_entry = "+".join(CFG.VARIANTS[variant]["a05_entry"])
    fam_exit = "+".join(CFG.VARIANTS[variant]["a05_exit"])
    fam_p6p = "+".join(CFG.VARIANTS[variant]["p6_primary"])
    fam_p6s = "+".join(CFG.VARIANTS[variant]["p6_specialty"])
    S = []

    def r(module, code, tvar, measure, grp, label, stable=False, label_kw=None):
        S.append(dict(module=module, code=code, tvar=tvar, measure=measure, grp=grp, label=label, stable=stable, label_kw=label_kw or {}))

    for c in ["03500404", "03500405"]:
        r("A03", c, "single_code", "annual_sum", "t3_grp_a03_ctx", f"c_{c}")
    for c in ["03500406", "03500407"]:
        r("A03", c, "single_code", "annual_sum", "t3_grp_a03_legacy", f"c_{c}")
    for c in ["09600212", "09600213", "09600214", "09600215", "09600216", "09600217", "09600218", "09600219"]:
        r("A03", c, "single_code", "annual_sum", "t3_grp_a03_2023", f"c_{c}")
    for c in ["03700104", "03700105", "03700106", "03700107", "03700108", "03700109"]:
        r("A03", c, "single_code", "annual_sum", "t3_grp_a03_2024", f"c_{c}")
    for c in ["03710013", "03710014", "03710015", "03710016", "03710017", "03710018", "03710019", "03710020", "03710021"]:
        r("A03", c, "single_code", "annual_sum", "t3_grp_a03_2025", f"c_{c}")
    for c in ["29101566", "29101574"]:
        r("A27", c, "single_code", "annual_sum", "t3_grp_a27", f"c_{c}")
    r("A05", "06902600", "broad_pre2021", "annual_sum", "t3_grp_a05_broad", "c_06902600")
    r("A05", "05225000", "broad_pre2021", "annual_sum", "t3_grp_a05_broad", "c_05225000")
    r("A05", "05990022", "strict_autism", "annual_sum", "t3_grp_a05", "c_05990022")
    r("A05", "05990022", "strict_autism", "annual_sum", "t3_grp_a05", "c_05990022", stable=True)
    r("A05", fam_entry, variant, "annual_sum", "t3_grp_a05", "c_a05_family_entry", label_kw={"v": "{v}"})
    r("A05", fam_entry, variant, "annual_sum", "t3_grp_a05", "c_a05_family_entry", stable=True, label_kw={"v": "{v}"})
    r("A05", "05990027", "strict_autism", "annual_sum", "t3_grp_a05", "c_05990027")
    r("A05", fam_exit, variant, "annual_sum", "t3_grp_a05", "c_a05_family_exit", label_kw={"v": "{v}"})
    r("P2", "P2500500", "single_code", "december_stock", "t3_grp_p2", "c_P2500500")
    r("P2", "P2500500", "single_code", "december_stock", "t3_grp_p2", "c_P2500500", stable=True)
    r("P2", "P2500500", "single_code", "june_stock", "t3_grp_p2", "c_P2500500")
    r("P2", "P2501878", "single_code", "december_stock", "t3_grp_p2", "c_P2501878")
    r("P2", "P2501878", "single_code", "june_stock", "t3_grp_p2", "c_P2501878")
    r("P6", "P6223000", "broad_pre2021", "december_stock", "t3_grp_p6_broad", "c_P6223000")
    r("P6", "P6223380", "broad_pre2021", "december_stock", "t3_grp_p6_broad", "c_P6223380")
    r("P6", "P6241010", "strict_autism", "december_stock", "t3_grp_p6", "c_P6241010")
    r("P6", "P6241010", "strict_autism", "december_stock", "t3_grp_p6", "c_P6241010", stable=True)
    r("P6", "P6241010", "strict_autism", "june_stock", "t3_grp_p6", "c_P6241010")
    r("P6", fam_p6p, variant, "december_stock", "t3_grp_p6", "c_p6_family_primary", label_kw={"v": "{v}"})
    r("P6", "P6241060", "strict_autism", "december_stock", "t3_grp_p6", "c_P6241060")
    r("P6", "P6241060", "strict_autism", "december_stock", "t3_grp_p6", "c_P6241060", stable=True)
    r("P6", "P6241060", "strict_autism", "june_stock", "t3_grp_p6", "c_P6241060")
    r("P6", fam_p6s, variant, "december_stock", "t3_grp_p6", "c_p6_family_specialty", label_kw={"v": "{v}"})
    for c in ["29101629", "29101651"]:
        r("A28", c, "single_code", "annual_sum", "t3_grp_a28", f"c_{c}")
    return S


def build_t3(rem: pd.DataFrame, variant: str, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, numeric = [], []
    vl = variant_label(variant, lang)
    for spec in t3_row_specs(variant):
        d = rem[(rem.module == spec["module"]) & (rem.code == spec["code"]) & (rem.variant == spec["tvar"]) & (rem.measure == spec["measure"])]
        if d.empty:
            raise ValueError(f"T3: sin filas en rem_pathway_annual para {spec}")
        d = d.set_index("year")
        first = d.iloc[0]
        unit = T(UNIT_KEY[str(first.unit)], lang)
        if spec["measure"] == "annual_sum":
            measure = T("t3_m_annual", lang, u=unit)
        elif spec["measure"] == "december_stock":
            measure = T("t3_m_dec", lang, u=unit)
        else:
            measure = T("t3_m_jun", lang, u=unit)
        if spec["stable"]:
            measure = T("t3_m_stable", lang, m=measure)
        kw = {k: (vl if v == "{v}" else v) for k, v in spec["label_kw"].items()}
        era_txt = str(first.era)
        m_era = re.fullmatch(r"(\d{4})[–-](\d{4})", era_txt)
        if m_era and m_era.group(1) == m_era.group(2):
            era_txt = m_era.group(1)  # era de un solo año: «2024» en vez de «2024–2024»
        row = {T("section", lang): T(spec["grp"], lang), T("t3_module", lang): spec["module"], T("t3_code", lang): spec["code"].replace("+", " + "),
               T("indicator", lang): T(spec["label"], lang, **kw), T("t3_era", lang): era_txt, T("t3_measure", lang): measure}
        for y in YEARS_REM:
            if y not in d.index:
                row[str(y)] = T("not_defined", lang)
                continue
            rr = d.loc[y]
            if spec["stable"]:
                tot, n = rr.stable_panel_total, rr.n_stable_panel_establishments
            else:
                tot, n = rr.total, rr.n_reporting_establishments
            if is_missing(tot) or (not is_missing(rr.n_rows) and int(rr.n_rows) == 0):
                row[str(y)] = T("not_reported", lang)
            else:
                row[str(y)] = fn_estab(tot, n, lang)
            numeric.append(dict(row_key=f"{spec['module']}:{spec['code']}:{spec['tvar']}:{spec['measure']}:{'stable' if spec['stable'] else 'all'}", module=spec["module"],
                                code=spec["code"], tidy_variant=spec["tvar"], table_variant=variant, measure=spec["measure"], stable_panel=spec["stable"],
                                era=str(rr.era), year=int(y), total=rr.total, total_dedup=rr.total_dedup, n_reporting_establishments=rr.n_reporting_establishments,
                                n_establishments_value_gt0=rr.n_establishments_value_gt0, n_rows=rr.n_rows, n_rows_empty=rr.n_rows_empty,
                                months_covered=rr.months_covered, n_stable_panel_establishments=rr.n_stable_panel_establishments, stable_panel_total=rr.stable_panel_total,
                                unit=str(rr.unit), comparability_warning=str(rr.comparability_warning)))
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(numeric)


def t3_titles(variant: str, lang: str, rem: pd.DataFrame) -> dict:
    vl = variant_label(variant, lang)
    p2 = rem[(rem.code == "P2500500") & (rem.measure == "december_stock")].set_index("year").reindex(YEARS_REM)
    p2n = "/".join(fnum(x, 0, lang) for x in p2.n_reporting_establishments)
    a05 = rem[(rem.code == "05990022") & (rem.variant == "strict_autism")].set_index("year").reindex(range(2021, 2026))
    a05n = "/".join(fnum(x, 0, lang) for x in a05.n_reporting_establishments)
    if lang == "es":
        return {"title": f"Tabla 3. Ruta administrativa agregada REM 2019–2025 por módulo, código y era de definición: totales anuales y stocks de diciembre con establecimientos reportantes — variante {vl}",
                "note": (f"Fuente: REM Serie A (A03, A27, A05, A28) y Serie P (P2, P6) 2019–2025, DEIS; módulo 02_rem_pathway (rem_pathway_annual.csv). Cada celda muestra el total nacional y, entre paréntesis, n = establecimientos con al menos una fila para el código en el año (diciembre o junio para los stocks). "
                         "Unidad por fila: Serie A = suma de los 12 meses (niños/as, registros, ingresos, egresos o intervenciones según el código; A27 cuenta intervenciones, no personas); Serie P = personas bajo control en el corte (stock); diciembre es la serie principal y junio solo sensibilidad; los semestres nunca se suman. "
                         "Filas «panel estable»: total restringido a los establecimientos que reportan el código en todos los años de su era (n = tamaño del panel). «no definido» = código inexistente en ese año (fuera de su era de definición); «no reportado» = código vigente sin fila en el archivo (P2501878 junio 2023). "
                         "Eras de definición: A03 legado 2019–2022 (subgrupo con alteración de lenguaje/área social; no es cobertura ni positividad poblacional), 2023–2024 (M-CHAT-R/F), 31–59 meses solo 2024, rediseño 2025; A05 TGD amplio 2019–2020 (incluye Rett de forma inseparable, sensibilidad separada) y autismo/categorías desde 2021; P6 TGD amplio 2019–2020 y autismo desde 2021; A27 y A28 desde 2023; total NANEAS (P2501878) desde diciembre 2023. Ninguna serie cruza un quiebre de definición. "
                         f"Filas de familia TGD según la variante {vl}: A05 ingresos {' + '.join(CFG.VARIANTS[variant]['a05_entry'])}; P6 APS {' + '.join(CFG.VARIANTS[variant]['p6_primary'])}; P6 especialidad {' + '.join(CFG.VARIANTS[variant]['p6_specialty'])}; las filas de autismo estricto (05990022, 05990027, P6241010, P6241060), A03, A27, A28 y P2 son idénticas en ambas variantes. "
                         f"Establecimientos reportantes de referencia: P2 TEA diciembre {p2n} (2019–2025); A05 autismo estricto {a05n} (2021–2025). Lugar de atención (establecimiento), no residencia. "
                         f"{T('no_linkage_note', lang)} {T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)}")}
    return {"title": f"Table 3. Aggregate REM administrative pathway 2019–2025 by module, code and definition era: annual totals and December stocks with reporting establishments — {vl} variant",
            "note": (f"Source: REM Series A (A03, A27, A05, A28) and Series P (P2, P6) 2019–2025, DEIS; module 02_rem_pathway (rem_pathway_annual.csv). Each cell shows the national total and, in parentheses, n = establishments with at least one row for the code in the year (December or June for stocks). "
                     "Unit per row: Series A = sum of the 12 months (children, records, entries, exits or interventions according to the code; A27 counts interventions, not persons); Series P = people under control at the cut (stock); December is the primary series and June sensitivity only; semesters are never summed. "
                     "'Stable panel' rows: total restricted to establishments reporting the code in every year of its era (n = panel size). 'not defined' = code non-existent in that year (outside its definition era); 'not reported' = code in force but no row in the file (P2501878 June 2023). "
                     "Definition eras: A03 legacy 2019–2022 (subgroup with language/social alteration; not population coverage or positivity), 2023–2024 (M-CHAT-R/F), 31–59 months in 2024 only, 2025 redesign; A05 broad PDD 2019–2020 (Rett inseparable, separate sensitivity) and autism/categories from 2021; P6 broad PDD 2019–2020 and autism from 2021; A27 and A28 from 2023; total NANEAS (P2501878) from December 2023. No series crosses a definition break. "
                     f"PDD-family rows according to the {vl} variant: A05 entries {' + '.join(CFG.VARIANTS[variant]['a05_entry'])}; P6 primary care {' + '.join(CFG.VARIANTS[variant]['p6_primary'])}; P6 specialty {' + '.join(CFG.VARIANTS[variant]['p6_specialty'])}; strict-autism rows (05990022, 05990027, P6241010, P6241060), A03, A27, A28 and P2 are identical in both variants. "
                     f"Reference reporting establishments: P2 ASD December {p2n} (2019–2025); A05 strict autism {a05n} (2021–2025). Place of care (establishment), not residence. "
                     f"{T('no_linkage_note', lang)} {T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)}")}


# ---------------------------------------------------------------------------
# T4 — capas de denominador y cobertura por año
# ---------------------------------------------------------------------------
class Denominators:
    def __init__(self):
        self.cov = C.read_tidy("coverage_layers_year").set_index("year").reindex(YEARS_REM)
        self.aps = C.read_tidy("aps_panel").set_index("year").reindex(YEARS_REM)
        self.r20 = C.read_tidy("rem20_panel").set_index("year").reindex(YEARS_REM)
        self.isa = C.read_tidy("isapre_beneficiaries_national_year").set_index("year").reindex(YEARS_REM)
        fon = C.read_tidy("fonasa_beneficiaries_national_year")
        self.fon_total = fon[(fon.dimension == "TOTAL")].set_index("year").beneficiaries.reindex(YEARS_REM)
        self.fon_aps = fon[(fon.dimension == "INSCRITO_APS") & (fon.category == "SI")].set_index("year").beneficiaries.reindex(YEARS_REM)
        self.schema = C.read_tidy("fonasa_schema_by_year").set_index("year").reindex(YEARS_REM)
        self.ine = C.read_tidy("ine_population_base_comparison").set_index("year").reindex(YEARS_REM)
        self.caveat = str(C.read_tidy("coverage_layers_year").caveat.iloc[0])


def build_t4(den: Denominators, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, numeric = [], []
    cov, aps, r20, isa = den.cov, den.aps, den.r20, den.isa

    def add(layer_key, ind_key, geo_key, fmt, num):
        row = {T("t4_layer", lang): T(layer_key, lang), T("indicator", lang): T(ind_key, lang), T("t4_geo", lang): T(geo_key, lang)}
        nrow = {"row_key": ind_key, "layer": layer_key}
        for y in YEARS_REM:
            row[str(y)] = fmt(y)
            nrow[str(y)] = num(y)
        rows.append(row)
        numeric.append(nrow)

    def cnt(series):
        return (lambda y: fnum(series.loc[y], 0, lang)), (lambda y: series.loc[y])

    def pct(series, scale=100.0, dec=1):
        return (lambda y: fpct(series.loc[y] * scale if not is_missing(series.loc[y]) else np.nan, dec, lang)), (lambda y: series.loc[y] * scale if not is_missing(series.loc[y]) else np.nan)

    def ratio(series, dec=3):
        return (lambda y: fnum(series.loc[y], dec, lang)), (lambda y: series.loc[y])

    add("t4_layer_pop", "t4_ine2017", "t4_geo_res", *cnt(cov.ine_population_base2017_30jun))
    add("t4_layer_pop", "t4_ine2024", "t4_geo_res", *cnt(cov.ine_population_base2024_national_30jun))
    add("t4_layer_pop", "t4_ine_ratio", "t4_geo_ratio", *ratio(den.ine.ratio_base2024_to_base2017_30jun))
    add("t4_layer_pop", "t4_censo2024", "t4_geo_res_census", *cnt(den.ine.censo2024_enumerated))
    add("t4_layer_ins", "t4_fonasa", "t4_geo_fonasa", *cnt(den.fon_total))
    add("t4_layer_ins", "t4_fonasa_aps", "t4_geo_fonasa",
        lambda y: (T("variable_absent", lang) if is_missing(den.fon_aps.loc[y]) else fnum(den.fon_aps.loc[y], 0, lang)), lambda y: den.fon_aps.loc[y])
    add("t4_layer_ins", "t4_fonasa_scheme", "t4_geo_text",
        lambda y: (T("t4_fonasa_scheme_val", lang, n=fnum(int(str(den.schema.age_band_scheme.loc[y]).split()[0]), 0, lang)) if not is_missing(den.schema.age_band_scheme.loc[y]) else T("dash", lang)),
        lambda y: (int(str(den.schema.age_band_scheme.loc[y]).split()[0]) if not is_missing(den.schema.age_band_scheme.loc[y]) else np.nan))
    add("t4_layer_ins", "t4_isapre", "t4_geo_isapre", *cnt(isa.beneficiarios_total))
    add("t4_layer_ins", "t4_isapre_cot", "t4_geo_isapre", *cnt(isa.cotizantes))
    add("t4_layer_ins", "t4_isapre_car", "t4_geo_isapre", *cnt(isa.cargas))
    add("t4_layer_ins", "t4_fi", "t4_geo_fonasa", *cnt(cov.fonasa_plus_isapre))
    add("t4_layer_ins", "t4_share_f", "t4_geo_share", *pct(cov.share_fonasa_ine))
    add("t4_layer_ins", "t4_share_i", "t4_geo_share", *pct(cov.share_isapre_ine))
    add("t4_layer_ins", "t4_share_fi", "t4_geo_share", *pct(cov.share_fonasa_plus_isapre_ine))
    add("t4_layer_ins", "t4_share_fi24", "t4_geo_share", *pct(cov.share_fonasa_plus_isapre_ine_base2024))
    add("t4_layer_aps", "t4_aps", "t4_geo_aps", *cnt(aps.enrolled_total))
    add("t4_layer_aps", "t4_aps_ad", "t4_geo_aps", *cnt(aps.enrolled_tramo_AD))
    add("t4_layer_aps", "t4_aps_x", "t4_geo_aps", *cnt(aps.enrolled_tramo_X))
    add("t4_layer_aps", "t4_aps_centres", "t4_geo_centres", *cnt(aps.centres_total))
    add("t4_layer_aps", "t4_aps_panel", "t4_geo_aps", *cnt(aps.enrolled_panel_1871))
    add("t4_layer_aps", "t4_aps_ret", "t4_geo_pct_panel", *pct(aps.retention_panel_1871, dec=2))
    add("t4_layer_aps", "t4_aps_vs_fonasa", "t4_geo_ratio",
        lambda y: (T("variable_absent", lang) if is_missing(cov.ratio_aps_tramoAD_to_fonasa_inscritos.loc[y]) else fnum(cov.ratio_aps_tramoAD_to_fonasa_inscritos.loc[y], 4, lang)),
        lambda y: cov.ratio_aps_tramoAD_to_fonasa_inscritos.loc[y])
    add("t4_layer_rem20", "t4_r20_estab", "t4_geo_estab", *cnt(r20.establishments_reporting))
    add("t4_layer_rem20", "t4_r20_12m", "t4_geo_estab", *cnt(r20.establishments_with_12_months))
    add("t4_layer_rem20", "t4_r20_disc", "t4_geo_episodes", *cnt(r20.discharges_total))
    add("t4_layer_rem20", "t4_r20_disc_p", "t4_geo_episodes", *cnt(r20.discharges_panel_188))
    add("t4_layer_rem20", "t4_r20_ret", "t4_geo_pct_panel", *pct(r20.retention_discharges, dec=2))
    add("t4_layer_rem20", "t4_r20_bd", "t4_geo_beddays", *cnt(r20.bed_days_available_total))
    add("t4_layer_rem20", "t4_r20_bd_p", "t4_geo_beddays", *cnt(r20.bed_days_available_panel_188))
    add("t4_layer_rem20", "t4_r20_bd_ret", "t4_geo_pct_panel", *pct(r20.retention_bed_days, dec=2))
    add("t4_layer_rem20", "t4_r20_per1000", "t4_geo_per1000", *ratio(cov.rem20_discharges_per_1000_ine, dec=1))
    return pd.DataFrame(rows), pd.DataFrame(numeric)


def t4_titles(lang: str, den: Denominators) -> dict:
    if lang == "es":
        return {"title": "Tabla 4. Capas de denominador y cobertura por año, Chile 2019–2025: población INE, aseguramiento FONASA/ISAPRE, inscritos APS y actividad hospitalaria REM-20",
                "note": ("Fuente: módulo 03_denominators (coverage_layers_year.csv, aps_panel.csv, rem20_panel.csv, isapre_beneficiaries_national_year.csv, fonasa_beneficiaries_national_year.csv, fonasa_schema_by_year.csv, ine_population_base_comparison.csv). "
                         "Cuatro capas que responden preguntas distintas y no se intercambian: INE = población residente proyectada al 30 de junio (base Censo 2017 como denominador principal; base 2024 y Censo 2024 solo como sensibilidad, nunca combinadas); FONASA e ISAPRE = stocks de beneficiarios en diciembre (aseguramiento); inscritos APS = cobertura operativa por centro (lugar de atención); REM-20 = egresos y días-cama (actividad y capacidad hospitalaria, nunca población cubierta). "
                         "(FONASA + ISAPRE)/INE no es una tasa de aseguramiento: mezcla stocks de diciembre con una proyección al 30 de junio, omite otros regímenes (FF.AA. y otros) y arrastra diferencias de clasificación y posible doble conteo; INE es residencia territorial, FONASA mezcla comuna del centro APS (inscritos) y domicilio (no inscritos), APS es comuna del centro e ISAPRE comuna administrativa. "
                         "FONASA cambia de esquema en 2021, 2023, 2024 y 2025 (23 bandas etarias en 2018–2022 y 2025; 10 bandas decenales en 2023; 18 bandas en 2024); la variable INSCRITO_APS existe solo hasta 2022; las filas repetidas de 2018–2020 son aditivas y no se deduplican. APS cambia nombres de variables y grupos etarios en 2024 (bandas de 20 años en 2019–2023). ISAPRE pasa de edades simples a quinquenios y de .xls a .xlsx en 2021. "
                         "Paneles continuos: 1.871 códigos de centro APS y 188 establecimientos REM-20 con 12 meses reportados en todos los años 2019–2025; la retención es la fracción del total anual que conserva el panel. "
                         f"{T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)} {T('identical_variants', lang)}")}
    return {"title": "Table 4. Denominator and coverage layers by year, Chile 2019–2025: INE population, FONASA/ISAPRE insurance, APS enrolment and REM-20 hospital activity",
            "note": ("Source: module 03_denominators (coverage_layers_year.csv, aps_panel.csv, rem20_panel.csv, isapre_beneficiaries_national_year.csv, fonasa_beneficiaries_national_year.csv, fonasa_schema_by_year.csv, ine_population_base_comparison.csv). "
                     "Four layers that answer different questions and are not interchangeable: INE = projected resident population at 30 June (Census 2017 base as primary denominator; 2024 base and Census 2024 as sensitivity only, never merged); FONASA and ISAPRE = December beneficiary stocks (insurance); APS enrolment = operational coverage per centre (place of care); REM-20 = discharges and bed-days (hospital activity and capacity, never a covered population). "
                     "(FONASA + ISAPRE)/INE is not an insurance-coverage rate: it mixes December stocks with a 30 June projection, omits other regimes (armed forces and others) and carries classification differences and possible double counting; INE is territorial residence, FONASA mixes APS-centre comuna (enrolled) and domicile (non-enrolled), APS is the centre's comuna and ISAPRE the administrative comuna. "
                     "FONASA changes schema in 2021, 2023, 2024 and 2025 (23 age bands in 2018–2022 and 2025; 10 ten-year bands in 2023; 18 bands in 2024); the INSCRITO_APS variable exists only up to 2022; repeated 2018–2020 rows are additive and are not deduplicated. APS changes variable names and age groups in 2024 (20-year bands in 2019–2023). ISAPRE moves from single ages to five-year groups and from .xls to .xlsx in 2021. "
                     "Continuous panels: 1,871 APS centre codes and 188 REM-20 establishments with 12 reported months in every year 2019–2025; retention is the fraction of the annual total kept by the panel. "
                     f"{T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)} {T('identical_variants', lang)}")}


# ---------------------------------------------------------------------------
# T5 — benchmarks poblacionales ENDIDE / ENCAVI con diseño complejo
# ---------------------------------------------------------------------------
DOMAIN_KEY = {
    "ENDIDE adultos 18+: autismo reportado": "dom_endide_adults",
    "ENDIDE NNA 2-17: autismo reportado": "dom_endide_nna",
    "ENDIDE NNA con autismo reportado: confirmado por un médico": "dom_endide_nna_conf_among",
    "ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)": "dom_endide_nna_conf_among_sens",
    "ENDIDE NNA 2-17: autismo reportado y confirmado por un médico": "dom_endide_nna_conf",
    "ENDIDE NNA con autismo reportado: ha recibido medicamento": "dom_endide_nna_med",
    "ENDIDE NNA con autismo reportado: ha recibido otro tratamiento": "dom_endide_nna_other",
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista": "dom_encavi",
    "ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)": "dom_encavi_sens",
    "ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico": "dom_encavi_treat",
}
RSE_MAX = 0.30


def t5_subgroup(row, lang: str) -> str:
    if row.subgroup_type == "total":
        return T("t5_sub_total", lang)
    if row.subgroup_type == "sex":
        return T("t5_sub_male", lang) if str(row.subgroup) == "Hombre" else T("t5_sub_female", lang)
    return T("t5_age_prefix", lang, a=str(row.subgroup).replace("-", "–"))


def build_t5(sv: pd.DataFrame, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, numeric = [], []
    for _, r in sv.iterrows():
        dom_key = DOMAIN_KEY.get(str(r.domain))
        if dom_key is None:
            raise KeyError(f"T5: dominio sin traducción: {r.domain}")
        wkey = f"w_{r.item_variable}"
        wording = T(wkey, lang)
        if lang == "en":
            wording = f"{wording} ({T('t5_wording_en_prefix', lang)}«{r.item_wording}»)"
        rse = float(r.rse) if not is_missing(r.rse) else np.nan
        imprecise = str(r.precision_flag) == "imprecise"
        suppressed = (not np.isnan(rse)) and rse > RSE_MAX
        pct_txt = f"{fnum(100 * r.proportion, 2, lang)} ({fnum(100 * r.se, 2, lang)})"
        ci_txt = fci(100 * r.lo, 100 * r.hi, 2, lang)
        wt_txt = fnum(r.weighted_total, 0, lang)
        if suppressed:
            pct_txt, ci_txt, wt_txt = T("ne", lang), T("ne", lang), T("ne", lang)
            prec = T("t5_prec_suppressed", lang)
        elif imprecise:
            pct_txt, ci_txt, wt_txt = f"[{pct_txt}]", f"[{ci_txt}]", f"[{wt_txt}]"
            prec = T("t5_prec_imprecise", lang)
        else:
            prec = T("t5_prec_ok", lang)
        rows.append({
            T("t5_survey", lang): str(r.survey).replace("-", "–"), T("t5_year", lang): str(r.survey_year).replace("-", "–"), T("t5_domain", lang): T(dom_key, lang),
            T("t5_subgroup", lang): t5_subgroup(r, lang), T("t5_type", lang): T(f"t5_type_{r.estimate_type}", lang),
            T("t5_item", lang): str(r.item_variable), T("t5_wording", lang): wording,
            T("t5_n", lang): fnum(r.n, 0, lang), T("t5_cases", lang): fnum(r.cases, 0, lang), T("t5_pct", lang): pct_txt, T("t5_ci", lang): ci_txt,
            T("t5_wtotal", lang): wt_txt, T("t5_design", lang): f"{r.weight_var}; {r.strata_var}; {r.psu_var}",
            T("t5_deff", lang): fnum(r.deff, 2, lang), T("t5_rse", lang): fnum(100 * rse, 1, lang), T("t5_precision", lang): prec,
        })
        numeric.append(dict(survey=r.survey, survey_year=str(r.survey_year), domain_key=dom_key, domain=r.domain, subgroup_type=r.subgroup_type, subgroup=r.subgroup,
                            estimate_type=r.estimate_type, item_variable=r.item_variable, weight_var=r.weight_var, strata_var=r.strata_var, psu_var=r.psu_var,
                            n=r.n, cases=r.cases, proportion=r.proportion, se=r.se, lo=r.lo, hi=r.hi, weighted_total=r.weighted_total, weighted_population=r.weighted_population,
                            deff=r.deff, rse=rse, df=r.df, n_psu=r.n_psu, n_strata=r.n_strata, precision_flag=r.precision_flag, imprecise_lt30_cases=imprecise,
                            suppressed_rse_gt30=suppressed, shown_as_reliable=(not imprecise and not suppressed), source_file=r.source_file, source_sha256=r.source_sha256))
    return pd.DataFrame(rows), pd.DataFrame(numeric)


def t5_titles(lang: str, sv: pd.DataFrame) -> dict:
    # Conteos coherentes con lo que muestra la tabla: las filas imprecisas (< 30 casos) que además tienen ERR > 30 %
    # se suprimen (n/e) y no se muestran entre corchetes.
    sup = pd.to_numeric(sv.rse, errors="coerce") > RSE_MAX
    imp = sv.precision_flag == "imprecise"
    n_sup = int(sup.sum())
    n_imp = int((imp & ~sup).sum())
    n_both = int((imp & sup).sum())
    if lang == "es":
        return {"title": "Tabla 5. Benchmarks poblacionales de autismo reportado con diseño muestral complejo: ENDIDE 2022 y ENCAVI 2023–2024",
                "note": ("Fuente: microdatos ENDIDE 2022 (endide_2022_adultos_cuidadores_nna.dta.zip; ponderador fexp, estratos estrato, conglomerados cod_upm) y ENCAVI 2023–2024 (ENCAVI_2023_2024.dta; ponderador w_personas_cal, estratos varstrat, conglomerados varunit); módulo 04_surveys (survey_estimates.csv). "
                         "Estimador de razón por dominio manteniendo todas las unidades del diseño; error estándar por linealización de Taylor (conglomerados de primera etapa con reemplazo, estratificado); IC 95 % en escala logit con t y gl = UPM − estratos; DEFF = varianza de diseño / varianza de muestreo aleatorio simple con el mismo n no ponderado; ERR = error estándar relativo. "
                         "Unidad: personas; % ponderado del dominio; total ponderado = personas expandidas con autismo reportado. Universos: ENDIDE adultos 18+ (n = 30.010; autorreporte o por tercero), NNA 2–17 con cuestionario del responsable principal (n = 5.526), NNA con autismo reportado y respuesta válida (n = 153); ENCAVI personas de 15+ con respuesta válida (n = 16.484; sensibilidad con «No sabe/No responde» = no diagnosticado, n = 16.590). "
                         f"Precisión: valores entre corchetes = dominios con menos de 30 casos no ponderados y ERR ≤ 30 % ({n_imp} filas; solo orden de magnitud); n/e = ERR > 30 % ({n_sup} filas, de las cuales {n_both} tienen además menos de 30 casos; estimación suprimida, no debe leerse como fiable). "
                         "Autismo reportado (autorreporte, cuidador o diagnóstico declarado) no equivale a un código F84 administrativo ni a prevalencia clínica; sin desagregación comunal; sin enlace con registros. "
                         f"Los ítems no distinguen el síndrome de Rett, por lo que la tabla es idéntica en ambas variantes. {T('law_note', lang)}")}
    return {"title": "Table 5. Population benchmarks of reported autism with complex survey design: ENDIDE 2022 and ENCAVI 2023–2024",
            "note": ("Source: ENDIDE 2022 microdata (endide_2022_adultos_cuidadores_nna.dta.zip; weight fexp, strata estrato, clusters cod_upm) and ENCAVI 2023–2024 (ENCAVI_2023_2024.dta; weight w_personas_cal, strata varstrat, clusters varunit); module 04_surveys (survey_estimates.csv). "
                     "Domain ratio estimator keeping all design units; standard error by Taylor linearisation (stratified, first-stage clusters with replacement); 95% CI on the logit scale with t and df = PSU − strata; DEFF = design variance / simple-random-sampling variance with the same unweighted n; RSE = relative standard error. "
                     "Unit: persons; weighted % of the domain; weighted total = expanded persons with reported autism. Universes: ENDIDE adults 18+ (n = 30,010; self-report or by proxy), children and adolescents 2–17 with the main caregiver's questionnaire (n = 5,526), children with reported autism and a valid answer (n = 153); ENCAVI persons aged 15+ with a valid answer (n = 16,484; sensitivity with 'Don't know/No answer' = not diagnosed, n = 16,590). "
                     f"Precision: values in square brackets = domains with fewer than 30 unweighted cases and RSE ≤ 30% ({n_imp} rows; order of magnitude only); n/e = RSE > 30% ({n_sup} rows, of which {n_both} also have fewer than 30 cases; estimate suppressed, must not be read as reliable). "
                     "Reported autism (self-report, caregiver report or declared diagnosis) is not equivalent to an administrative F84 code or to clinical prevalence; no comuna disaggregation; no linkage to registers. "
                     f"The items do not distinguish Rett syndrome, so the table is identical in both variants. {T('law_note', lang)}")}


# ---------------------------------------------------------------------------
# T6 — triangulación educativa: PIE/SINACES y JUNAEB EVE
# ---------------------------------------------------------------------------
class Education:
    def __init__(self):
        self.edu = C.read_tidy("education_summary_year").set_index("year").reindex(YEARS_REM)
        self.jun = C.read_tidy("junaeb_tea_year_level")
        pie = C.read_tidy("pie_series")
        self.pie = pie
        self.pie_w = pie.pivot_table(index="year", columns="series", values="value", aggfunc="first").reindex(YEARS_REM)

    def jrow(self, level: str, year: int) -> pd.Series | None:
        d = self.jun[(self.jun.level == level) & (self.jun.sex == "all") & (self.jun.year == year)]
        return None if d.empty else d.iloc[0]


LEVELS = ["parvularia", "basico1", "basico5", "medio1"]


def build_t6(ed: Education, lang: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, numeric = [], []
    e, pw = ed.edu, ed.pie_w

    def add(block, key, src_key, fmt, num, label_kw=None):
        row = {T("section", lang): T(block, lang), T("indicator", lang): T(key, lang, **(label_kw or {})), T("source_col", lang): T(src_key, lang)}
        nrow = {"row_key": key if not label_kw else f"{key}:{label_kw.get('lvl_key', '')}", "block": block}
        for y in YEARS_REM:
            row[str(y)] = fmt(y)
            nrow[str(y)] = num(y)
        rows.append(row)
        numeric.append(nrow)

    def cnt(series, absent_key="not_published"):
        return (lambda y: (T(absent_key, lang) if is_missing(series.loc[y]) else fnum(series.loc[y], 0, lang))), (lambda y: series.loc[y])

    def pct(series):
        return (lambda y: (T("not_published", lang) if is_missing(series.loc[y]) else fpct(series.loc[y], 1, lang))), (lambda y: series.loc[y])

    add("t6_block_pie", "t6_pie_strict", "t6_src_apuntes60", *cnt(e.pie_tea_strict_n))
    add("t6_block_pie", "t6_pie_asperger", "t6_src_apuntes60", *cnt(e.pie_tea_asperger_n))
    add("t6_block_pie", "t6_pie_harmonised", "t6_src_mixed", *cnt(e.pie_harmonised_n))
    sin = pw["pie_harmonised_sinaces"]
    add("t6_block_pie", "t6_pie_sinaces", "t6_src_sinaces_t1",
        lambda y: (T("not_published", lang) if is_missing(sin.loc[y]) else (fnum(sin.loc[y], 0, lang) + (" ‡" if y == 2022 else ""))), lambda y: sin.loc[y])
    add("t6_block_pie", "t6_sinaces_total", "t6_src_sinaces_t1", *cnt(pw["sinaces_total_autistic_students"]))
    add("t6_block_pie", "t6_special", "t6_src_sinaces_t1", *cnt(e.special_schools_autism_n))
    add("t6_block_pie", "t6_pie_total", "t6_src_apuntes60", *cnt(e.pie_total_enrolment_apuntes60_n))
    add("t6_block_pie", "t6_applicants", "t6_src_sinaces_t2", *cnt(e.pie_total_applicants_sinaces_n))
    add("t6_block_pie", "t6_share_strict", "t6_src_derived", *pct(e.pie_tea_strict_share_of_pie_pct))
    add("t6_block_pie", "t6_share_harm", "t6_src_derived", *pct(e.pie_harmonised_share_of_pie_pct))
    add("t6_block_pie", "t6_share_appl", "t6_src_derived", *pct(e.pie_harmonised_share_of_applicants_sinaces_pct))
    add("t6_block_pie", "t6_exceptional", "t6_src_sinaces_t2", *cnt(e.pie_tea_exceptional_entry_n))
    add("t6_block_pie", "t6_regular", "t6_src_sinaces_t2", *cnt(pw["pie_tea_regular_entry"]))

    jnum = []
    for lvl in LEVELS:
        sample = ed.jun[(ed.jun.level == lvl)].iloc[0]
        lvl_label = sample.level_label_es if lang == "es" else sample.level_label_en

        def pct_fmt(y, lvl=lvl):
            r = ed.jrow(lvl, y)
            if r is None:
                return T("dash", lang)
            if str(r.estimable) == "yes":
                return f"{fnum(r.proportion_weighted_pct, 2, lang)} ({fci(r.lo_pct, r.hi_pct, 2, lang)})"
            if str(r.item_variable) == "ABSENT":
                return T("t6_ne_no_item", lang)
            if str(r.estimable) == "unweighted_only":
                return T("t6_ne_no_weight", lang)
            return T("t6_ne_empty", lang)

        def pct_num(y, lvl=lvl):
            r = ed.jrow(lvl, y)
            return np.nan if (r is None or str(r.estimable) != "yes") else r.proportion_weighted_pct

        def n_fmt(y, lvl=lvl):
            r = ed.jrow(lvl, y)
            if r is None:
                return T("dash", lang)
            tea = T("dash", lang) if is_missing(r.n_tea_unweighted) else fnum(r.n_tea_unweighted, 0, lang)
            return f"{fnum(r.n_students, 0, lang)}; {tea}"

        def n_num(y, lvl=lvl):
            r = ed.jrow(lvl, y)
            return np.nan if r is None else r.n_students

        add("t6_block_junaeb", "t6_junaeb_pct", "t6_src_junaeb_generic", pct_fmt, pct_num, label_kw={"lvl": lvl_label, "lvl_key": lvl})
        add("t6_block_junaeb", "t6_junaeb_n", "t6_src_junaeb_generic", n_fmt, n_num, label_kw={"lvl": lvl_label, "lvl_key": lvl})
        for y in YEARS_REM:
            r = ed.jrow(lvl, y)
            if r is not None:
                jnum.append(dict(row_key=f"junaeb:{lvl}", level=lvl, year=int(y), n_students=r.n_students, n_tea_unweighted=r.n_tea_unweighted,
                                 proportion_weighted_pct=r.proportion_weighted_pct, se_pct=r.se_pct, lo_pct=r.lo_pct, hi_pct=r.hi_pct,
                                 proportion_unweighted_pct=r.proportion_unweighted_pct, weighted_tea_total=r.weighted_tea_total, weighted_population=r.weighted_population,
                                 estimable=r.estimable, item_variable=r.item_variable, weight_variable=r.weight_variable, source_file=r.source_file))
    numeric_df = pd.DataFrame(numeric)
    jnum_df = pd.DataFrame(jnum)
    return pd.DataFrame(rows), pd.concat([numeric_df, jnum_df], ignore_index=True, sort=False)


def t6_titles(lang: str) -> dict:
    if lang == "es":
        return {"title": "Tabla 6. Triangulación educativa 2019–2025: estudiantes con TEA en el Programa de Integración Escolar (Apuntes 60 / SINACES) y porcentaje ponderado de TEA reportado por cuidadores en la Encuesta de Vulnerabilidad Estudiantil de JUNAEB por nivel",
                "note": ("Fuente: informes MINEDUC Apuntes 60 (2024; Tabla 6, p. 11), Apuntes 59 (2024) y Reporte Ley 21.545 SINACES 2022–2025 (Tablas 1 y 2, pp. 8–9); microdatos JUNAEB EVE 2019–2025 por nivel; módulo 05_education (education_summary_year.csv, pie_series.csv, junaeb_tea_year_level.csv). "
                         "PIE: stock escolar anual de estudiantes registrados (registro para subvención y cupos; no incluye a todos los estudiantes autistas). Series mantenidas separadas: TEA estricto, TEA-Asperger, armonizado = TEA + TEA-Asperger (Apuntes 60 en 2019–2023; SINACES en 2024–2025, donde solo existe la serie armonizada) y SINACES como publicado. "
                         f"{T('t6_discrepancy', lang)} "
                         "JUNAEB: reporte de cuidadores en cohortes escolares seleccionadas (cobertura selectiva), no prevalencia nacional; % ponderado con el ponderador anual (EXP_REG en 2024, EXP en 2025) e IC 95 % por linealización de Taylor; celda «estudiantes; TEA» = registros del archivo y casos TEA no ponderados. "
                         "n/e = no estimable: 2019–2022 el cuestionario no incluye ítem de TEA; 2023 tiene ítem pero no ponderador publicado (solo cifras no ponderadas en la versión numérica); 2024 1º medio tiene la variable TEA completamente vacía (no es cero). La redacción del ítem cambia por año y se registra en la versión numérica. "
                         f"{T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)} Las series educativas no dependen de F84.2: {lower_first(T('identical_variants', lang))}")}
    return {"title": "Table 6. Educational triangulation 2019–2025: students with ASD in the School Integration Programme (Apuntes 60 / SINACES) and weighted percentage of caregiver-reported ASD in JUNAEB's Student Vulnerability Survey by level",
            "note": ("Source: MINEDUC reports Apuntes 60 (2024; Table 6, p. 11), Apuntes 59 (2024) and the Law 21.545 SINACES report 2022–2025 (Tables 1 and 2, pp. 8–9); JUNAEB EVE microdata 2019–2025 by level; module 05_education (education_summary_year.csv, pie_series.csv, junaeb_tea_year_level.csv). "
                     "PIE: annual school stock of registered students (registration for subsidy and quotas; does not include all autistic students). Series kept separate: strict ASD, ASD-Asperger, harmonised = ASD + ASD-Asperger (Apuntes 60 in 2019–2023; SINACES in 2024–2025, where only the harmonised series exists) and SINACES as published. "
                     f"{T('t6_discrepancy', lang)} "
                     "JUNAEB: caregiver report in selected school cohorts (selective coverage), not national prevalence; weighted % with the annual weight (EXP_REG in 2024, EXP in 2025) and 95% CI by Taylor linearisation; the 'students; ASD' cell gives file records and unweighted ASD cases. "
                     "n/e = not estimable: in 2019–2022 the questionnaire has no ASD item; 2023 has the item but no published weight (unweighted figures only in the numeric version); 2024 grade 9 has a completely empty ASD variable (not zero). Item wording changes by year and is recorded in the numeric version. "
                     f"{T('admin_note', lang)} {T('pandemic_note', lang)} {T('law_note', lang)} Educational series do not depend on F84.2: {lower_first(T('identical_variants', lang))}")}


# ---------------------------------------------------------------------------
# T7 — modelos preespecificados: CPA e IC por estimando y sensibilidad
# ---------------------------------------------------------------------------
def t7_model_ids(variant: str) -> list[str]:
    V = variant
    ids = [
        f"grd_rate:{V}:observed:all:any:none:2019-2024", f"grd_rate:{V}:observed:all:any:depth:2019-2024", f"grd_rate:{V}:observed:all:any:disruption:2019-2024",
        f"grd_rate:{V}:observed:all:any:none:2021-2024", f"grd_rate:{V}:fixed65:all:any:none:2019-2024", f"grd_rate:{V}:fixed65:all:any:depth:2019-2024",
        f"grd_rate:{V}:observed:hospitalisation:any:none:2019-2024", f"grd_rate:{V}:observed:hospitalisation:any:depth:2019-2024",
        f"grd_rate:{V}:observed:all:principal:none:2019-2024", f"grd_rate:{V}:observed:all:principal:depth:2019-2024", f"grd_rate:{V}:fixed65:all:principal:none:2019-2024",
        "grd_rate:strict_autism_f840:observed:all:any:none:2019-2024",
        f"grd_hospital:{V}:observed:any:none:2019-2024:model", f"grd_hospital:{V}:observed:any:none:2019-2024:cluster", f"grd_hospital:{V}:observed:any:depth:2019-2024:model",
        f"grd_hospital:{V}:fixed65:any:none:2019-2024:model", f"grd_hospital:{V}:observed:any:ri_none:2019-2024:random_intercept",
        f"grd_pop:{V}:any:TOTAL:crude:2019-2024", f"grd_pop:{V}:any:TOTAL:age_adjusted:2019-2024", f"grd_pop:{V}:any:HOMBRE:age_adjusted:2019-2024",
        f"grd_pop:{V}:any:MUJER:age_adjusted:2019-2024", f"grd_pop:{V}:principal:TOTAL:age_adjusted:2019-2024",
        "a05_entry:strict_autism:pop:none:2021-2025", "a05_entry:strict_autism:estab:none:2021-2025", "a05_entry:strict_autism:stable_pop:none:2021-2025",
        "a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025", "a05_entry:strict_autism:pop:none:2022-2025",
        f"a05_entry:{V}:pop:none:2021-2025", f"a05_entry:{V}:estab:none:2021-2025", f"a05_entry:{V}:stable_pop:none:2021-2025",
        "a05_exit:strict_autism:pop:none:2021-2025", f"a05_exit:{V}:pop:none:2021-2025",
        "p2_dec:none:2019-2025", "p2_dec:estab:2019-2025", "p2_dec:stable:2019-2025", "p2_dec:none_disruption:2019-2025", "p2_dec:none:2021-2025",
        "p2_jun:estab:2021-2025", "p2_dec:naneas:2023-2025",
        "p6_primary:strict_autism:none:2021-2025", "p6_primary:strict_autism:estab:2021-2025", "p6_primary:strict_autism:stable:2021-2025",
        f"p6_primary:{V}:none:2021-2025", f"p6_primary:{V}:estab:2021-2025",
        "p6_specialty:strict_autism:none:2021-2025", "p6_specialty:strict_autism:estab:2021-2025", f"p6_specialty:{V}:none:2021-2025",
        "pie_harmonised:none:2019-2025", "pie_harmonised:none:2019-2023", "pie_harmonised:disruption:2019-2025", "pie_tea_strict_n:none:2019-2023", "pie_tea_asperger_n:none:2019-2023",
        f"deis_principal:{V}:none:2019-2024", f"deis_principal:{V}:none:2021-2024",
    ]
    return ids


GLOBAL_NOTE_KEYS = {"not_causal_law", "dw_weak"}


def t7_spec_text(r: pd.Series, lang: str) -> str:
    parts = [T(str(r.panel), lang)]
    for key in (str(r.activity), str(r.position)):
        txt = T(key, lang)
        if txt:
            parts.append(txt)
    parts.append(T(str(r.denominator_offset), lang))
    parts.append(T(str(r.covariates), lang))
    fam = T(str(r.model_family), lang)
    if str(r.model_family) != "fam_qp":
        parts.append(fam)
    return "; ".join(parts)


def t7_series_text(r: pd.Series, lang: str) -> str:
    s = f"{T(str(r.outcome), lang)} — {T('var_' + str(r.variant), lang)}"
    if not is_missing(r.sex):
        s += f" — {T('sex_' + str(r.sex), lang)}"
    return s


def t7_notes_text(r: pd.Series, lang: str) -> str:
    keys = [k for k in str(r.note_keys).split("|") if k and k not in GLOBAL_NOTE_KEYS]
    parts = []
    for k in keys:
        txt = T(f"nk_{k}", lang)
        if txt:
            parts.append(txt)
    if not is_missing(r.get("stable_panel_n")):
        parts.append(f"n = {fnum(r.stable_panel_n, 0, lang)}")
    if not is_missing(r.get("re_sd")):
        parts.append(("DE del intercepto aleatorio = " if lang == "es" else "random-intercept SD = ") + fnum(r.re_sd, 2, lang))
    return "; ".join(parts) if parts else T("dash", lang)


def build_t7(ms: pd.DataFrame | None, variant: str, lang: str, core: GrdCore) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    rows, numeric, missing = [], [], []
    if ms is None:
        # esqueleto desde las tasas anuales: una fila por estimando GRD con dependencia declarada
        for panel in ("observed", "fixed65"):
            for pos in ("any", "principal"):
                d = core.sel(variant, panel, "all", pos)
                rows.append({T("t7_estimand", lang): T("est_grd_rate", lang), T("t7_series", lang): f"{T('out_f84_' + pos, lang)} — {T('var_' + variant, lang)}",
                             T("t7_spec", lang): "; ".join([T("panel_" + panel, lang), T("act_all", lang), T("pos_" + pos, lang), T("off_episodes", lang), T("cov_none", lang)]),
                             T("t7_years", lang): "2019–2024", T("t7_n", lang): fnum(len(d.dropna(subset=["n_episodes_f84"])), 0, lang), T("t7_apc", lang): T("t7_pending", lang),
                             T("t7_p", lang): T("ne", lang), T("t7_disp", lang): T("ne", lang), T("t7_notes", lang): T("t7_pending", lang)})
                numeric.append(dict(model_id=f"grd_rate:{variant}:{panel}:all:{pos}:none:2019-2024", status="pending_models_summary",
                                    **{f"rate_{y}": d.loc[y, "rate_per_100k_episodes"] for y in YEARS_GRD}))
        return pd.DataFrame(rows), pd.DataFrame(numeric), ["models_summary.csv"]
    idx = ms.set_index("model_id")
    for mid in t7_model_ids(variant):
        if mid not in idx.index:
            missing.append(mid)
            continue
        r = idx.loc[mid]
        rows.append({T("t7_estimand", lang): T(str(r.estimand), lang), T("t7_series", lang): t7_series_text(r, lang), T("t7_spec", lang): t7_spec_text(r, lang),
                     T("t7_years", lang): str(r.years).replace("-", "–"), T("t7_n", lang): fnum(r.n_obs, 0, lang),
                     T("t7_apc", lang): frate(r.apc, r.apc_lo, r.apc_hi, 1, lang), T("t7_p", lang): fp(r.p_value, lang),
                     T("t7_disp", lang): fnum(r.dispersion, 2, lang), T("t7_notes", lang): t7_notes_text(r, lang)})
        numeric.append(dict(model_id=mid, estimand=r.estimand, source=r.source, variant=r.variant, outcome=r.outcome, denominator_offset=r.denominator_offset,
                            panel=r.panel, activity=r.activity, position=r.position, covariates=r.covariates, sex=r.sex, years=r.years, n_obs=r.n_obs, df_resid=r.df_resid,
                            apc=r.apc, apc_lo=r.apc_lo, apc_hi=r.apc_hi, p_value=r.p_value, beta=r.beta, se=r.se, dispersion=r.dispersion, durbin_watson=r.durbin_watson,
                            model_family=r.model_family, converged=r.converged, note_keys=r.note_keys, stable_panel_n=r.get("stable_panel_n"), re_sd=r.get("re_sd")))
    return pd.DataFrame(rows), pd.DataFrame(numeric), missing


def t7_titles(variant: str, lang: str, ms_present: bool, n_rows: int, n_total: int) -> dict:
    vl = variant_label(variant, lang)
    if lang == "es":
        dep = "" if ms_present else " ESQUELETO: models_summary.csv no existe; ejecutar 06_models.py y volver a correr este módulo."
        return {"title": f"Tabla 7. Modelos preespecificados: cambio porcentual anual (CPA) e IC 95 % por estimando y sensibilidad, Chile 2019–2025 — variante {vl}",
                "note": (f"Fuente: módulo 06_models (models_summary.csv; {fnum(n_rows, 0, lang)} de {fnum(n_total, 0, lang)} especificaciones seleccionadas aquí; el conjunto completo está en T7_models_cpa_full.csv del módulo 06).{dep} "
                         "Modelos log-lineales cuasi-Poisson (escala de Pearson) con el offset indicado; CPA = 100·(exp(β) − 1) con IC 95 % de Wald; dispersión = χ² de Pearson / gl. "
                         "GRD: episodios con F84 documentado por 100.000 episodios GRD del mismo panel y modalidad (panel observado 65/65/65/65/68/72 hospitales; panel fijo 65); hospital-año con efectos fijos de hospital y offset log(episodios), EE agrupados por hospital e intercepto aleatorio Poisson como sensibilidad; por 100.000 habitantes con numerador por lugar de atención y denominador INE base 2017 (residencia). "
                         "REM A05 2021–2025 (era de códigos de autismo; TGD amplio 2019–2020 no modelado; menos establecimientos reportan en 2025); P2 y P6 son stocks de diciembre (junio solo sensibilidad; nunca sumados); PIE armonizado = Apuntes 60 (2019–2023) y SINACES (2024–2025); DEIS solo F84 en DIAG1, comparable únicamente con GRD principal. "
                         "El indicador 2020–2021 describe la disrupción del reporte y ninguna especificación estima un efecto causal de la Ley 21.545 (marzo de 2023). Durbin–Watson sobre residuos de devianza con 4–7 puntos es una prueba débil (valores en la versión numérica). Series de autismo estricto REM y solo F84.0 son idénticas en ambas variantes. "
                         f"{T('admin_note', lang)}")}
    dep = "" if ms_present else " SKELETON: models_summary.csv does not exist; run 06_models.py and rerun this module."
    return {"title": f"Table 7. Pre-specified models: annual percent change (APC) and 95% CI by estimand and sensitivity, Chile 2019–2025 — {vl} variant",
            "note": (f"Source: module 06_models (models_summary.csv; {fnum(n_rows, 0, lang)} of {fnum(n_total, 0, lang)} specifications selected here; the full set is in T7_models_cpa_full.csv from module 06).{dep} "
                     "Quasi-Poisson log-linear models (Pearson scale) with the stated offset; APC = 100·(exp(β) − 1) with Wald 95% CI; dispersion = Pearson χ² / df. "
                     "GRD: episodes with documented F84 per 100,000 GRD episodes of the same panel and activity (observed panel 65/65/65/65/68/72 hospitals; fixed panel 65); hospital-year with hospital fixed effects and log(episodes) offset, hospital-clustered SE and a Poisson random intercept as sensitivity; per 100,000 population with a place-of-care numerator and INE base-2017 denominator (residence). "
                     "REM A05 2021–2025 (autism-code era; broad PDD 2019–2020 not modelled; fewer establishments report in 2025); P2 and P6 are December stocks (June sensitivity only; never summed); harmonised PIE = Apuntes 60 (2019–2023) and SINACES (2024–2025); DEIS F84 in DIAG1 only, comparable solely with GRD principal. "
                     "The 2020–2021 indicator describes reporting disruption and no specification estimates a causal effect of Law 21.545 (March 2023). Durbin–Watson on deviance residuals with 4–7 points is a weak test (values in the numeric version). Strict REM autism and F84.0-only series are identical in both variants. "
                     f"{T('admin_note', lang)}")}


# ---------------------------------------------------------------------------
# Controles de reproducción (esperado frente a observado) y ejecución
# ---------------------------------------------------------------------------
def control_row(name: str, key, expected, observed, note: str = "", tol_rel: float = 0.0) -> dict:
    try:
        e, o = float(expected), float(observed)
        diff = o - e
        rd = rel(o, e)
        ok = (diff == 0) if tol_rel == 0 else (abs(rd) <= tol_rel if not np.isnan(rd) else False)
        status = "ok" if ok else "differs"
    except (TypeError, ValueError):
        diff, rd, status = np.nan, np.nan, ("ok" if str(expected) == str(observed) else "differs")
    return dict(module=MODULE, name=name, key=str(key), expected=expected, observed=observed, abs_diff=diff, rel_diff=rd, status=status, note=note)


def series_from_numeric(num: pd.DataFrame, row_key: str) -> dict[int, float]:
    r = num.loc[num.row_key == row_key]
    if r.empty:
        return {}
    r = r.iloc[0]
    return {int(c): r[c] for c in r.index if str(c).isdigit()}


def main() -> int:
    t0 = time.perf_counter()
    timings: dict[str, float] = {}
    log("lectura de tablas tidy")
    prov = C.read_tidy("data_provenance")
    summ = C.read_tidy("provenance_summary_by_source")
    core = GrdCore()
    rem = C.read_tidy("rem_pathway_annual", dtype={"code": str, "month": str})
    den = Denominators()
    sv = C.read_tidy("survey_estimates", dtype={"survey_year": str})
    ed = Education()
    ms_path = CFG.TIDY / "models_summary.csv"
    ms = pd.read_csv(ms_path) if ms_path.is_file() else None
    if ms is None:
        log("AVISO: models_summary.csv ausente; la T7 se escribe como esqueleto con dependencia declarada")
    timings["read"] = round(time.perf_counter() - t0, 2)

    controls: list[dict] = []
    outputs: list[str] = []
    row_counts: dict[str, int] = {}
    t7_missing_all: dict[str, list[str]] = {}
    for variant in VARIANTS:
        for lang in LANGS:
            t1 = time.perf_counter()
            tdir = out_tables_dir(variant, lang)
            titles: dict = {}
            # T1
            f1, n1 = build_t1(prov, summ, lang)
            outputs += [str(p) for p in write_pair(tdir, "T1_sources", f1, n1)]
            titles["T1_sources"] = t1_titles(lang, prov)
            # T2
            f2, n2 = build_t2(core, variant, lang)
            outputs += [str(p) for p in write_pair(tdir, "T2_grd_core", f2, n2)]
            titles["T2_grd_core"] = t2_titles(variant, lang, core)
            # T3
            f3, n3 = build_t3(rem, variant, lang)
            outputs += [str(p) for p in write_pair(tdir, "T3_rem_pathway", f3, n3)]
            titles["T3_rem_pathway"] = t3_titles(variant, lang, rem)
            # T4
            f4, n4 = build_t4(den, lang)
            outputs += [str(p) for p in write_pair(tdir, "T4_denominators_coverage", f4, n4)]
            titles["T4_denominators_coverage"] = t4_titles(lang, den)
            # T5
            f5, n5 = build_t5(sv, lang)
            outputs += [str(p) for p in write_pair(tdir, "T5_survey_benchmarks", f5, n5)]
            titles["T5_survey_benchmarks"] = t5_titles(lang, sv)
            # T6
            f6, n6 = build_t6(ed, lang)
            outputs += [str(p) for p in write_pair(tdir, "T6_education", f6, n6)]
            titles["T6_education"] = t6_titles(lang)
            # T7
            f7, n7, missing = build_t7(ms, variant, lang, core)
            outputs += [str(p) for p in write_pair(tdir, "T7_models", f7, n7)]
            titles["T7_models"] = t7_titles(variant, lang, ms is not None, len(f7), 0 if ms is None else len(ms))
            t7_missing_all[variant] = missing
            merge_json(tdir / "titles.json", titles)
            outputs.append(str(tdir / "titles.json"))
            for name, df in [("T1", f1), ("T2", f2), ("T3", f3), ("T4", f4), ("T5", f5), ("T6", f6), ("T7", f7)]:
                row_counts[f"{variant}/{lang}/{name}"] = len(df)
                n_empty = int(df.isna().sum().sum() + (df.astype(str) == "").sum().sum())
                controls.append(control_row(f"{name}_no_empty_cells", f"{variant}/{lang}", 0, n_empty, "celdas vacías o NaN en la tabla formateada (todas deben tener texto)"))
            timings[f"{variant}/{lang}"] = round(time.perf_counter() - t1, 2)
            log(f"{variant}/{lang}: T1 {len(f1)} filas, T2 {len(f2)}, T3 {len(f3)}, T4 {len(f4)}, T5 {len(f5)}, T6 {len(f6)}, T7 {len(f7)} ({timings[f'{variant}/{lang}']} s)")

            # controles numéricos (una vez por variante, con la versión numérica en inglés)
            if lang == "en":
                if variant == "con_rett":
                    for key, ctrl, note in [("t2_any_obs_n", "grd_f84_any", "T2 con_rett frente a config.CONTROLS"), ("t2_any_fix_n", "grd_f84_any_panel65", "T2 con_rett frente a config.CONTROLS"),
                                            ("t2_prin_obs_n", "grd_f84_principal", "T2 con_rett frente a config.CONTROLS"), ("t2_hospitals_observed", "grd_hospitals_observed", "T2 con_rett frente a config.CONTROLS"),
                                            ("t2_hosp_fix_any_n", "grd_f84_any_strict_hospitalisation", "valores del brief = hospitalización estricta del panel fijo de 65 (módulo 01); la fila del panel observado difiere en 2023–2024 (5.842 y 7.705)"),
                                            ("t2_cma_any_n", "grd_cma", "T2 con_rett frente a config.CONTROLS"), ("t2_episodes_observed_all", "grd_records_total", "T2 con_rett frente a config.CONTROLS")]:
                        obs = series_from_numeric(n2, key)
                        for y, e in CFG.CONTROLS[ctrl].items():
                            controls.append(control_row(f"T2_{ctrl}", y, e, obs.get(y), note))
                    persons = series_from_numeric(n2, "t2_persons_any")
                    no_id = series_from_numeric(n2, "t2_no_id")
                    for y, e in CFG.CONTROLS["grd_persons_within_year_f84_any"].items():
                        controls.append(control_row("T2_grd_persons_within_year_f84_any", y, e, persons.get(y),
                                                    f"personas con identificador válido; el brief cuenta el marcador de identificador inválido como una persona adicional (módulo 01); episodios F84 sin identificador válido = {int(no_id.get(y, 0))}"))
                        controls.append(control_row("T2_grd_persons_within_year_f84_any_plus_placeholder", y, e, persons.get(y) + (1 if no_id.get(y, 0) > 0 else 0),
                                                    "diagnóstico: personas válidas + 1 si existe el marcador de identificador inválido (regla del brief)"))
                    controls.append(control_row("T2_grd_f84_secondary_only_share_2024", 2024, CFG.CONTROLS["grd_f84_secondary_only_share_2024"],
                                                round(series_from_numeric(n2, "t2_sec_only").get(2024, np.nan) / 100, 3), "proporción de episodios F84 solo secundarios", tol_rel=0.005))
                    depth = series_from_numeric(n2, "t2_depth_all")
                    for y, e in CFG.CONTROLS["grd_coding_depth_all_mean"].items():
                        controls.append(control_row("T2_grd_coding_depth_all_mean", y, e, round(depth.get(y, np.nan), 2), "media de diagnósticos por episodio", tol_rel=0.005))
                    for key, ctrl in [("A05:05990022:strict_autism:annual_sum:all", "a05_autism_entries"), ("A05:05990027:strict_autism:annual_sum:all", "a05_autism_exits"),
                                      ("A27:29101574:single_code:annual_sum:all", "a27_assisted_referral"), ("A27:29101566:single_code:annual_sum:all", "a27_counselling"),
                                      ("A28:29101629:single_code:annual_sum:all", "a28_primary"), ("A28:29101651:single_code:annual_sum:all", "a28_hospital"),
                                      ("P2:P2500500:single_code:december_stock:all", "p2_tea_december"), ("P2:P2501878:single_code:december_stock:all", "p2_naneas_total_december"),
                                      ("P6:P6241010:strict_autism:december_stock:all", "p6_primary_december"), ("P6:P6241060:strict_autism:december_stock:all", "p6_specialty_december"),
                                      ("A03:03500406:single_code:annual_sum:all", "a03_legacy_mchat_done"), ("A03:03500407:single_code:annual_sum:all", "a03_legacy_mchat_altered")]:
                        sub = n3[n3.row_key == key].set_index("year")
                        for y, e in CFG.CONTROLS[ctrl].items():
                            if ctrl.startswith("p6_") and y < 2021:
                                continue  # 2019–2020 = TGD amplio (otro código); el control preliminar mezcla eras
                            controls.append(control_row(f"T3_{ctrl}", y, e, sub.total.get(y, np.nan), "T3 frente a config.CONTROLS (total nacional)"))
                    sub = n3[n3.row_key == "P2:P2500500:single_code:december_stock:all"].set_index("year")
                    for y, e in CFG.CONTROLS["p2_establishments_december"].items():
                        controls.append(control_row("T3_p2_establishments_december", y, e, sub.n_reporting_establishments.get(y, np.nan), "establecimientos reportantes P2 diciembre"))
                    for key, ctrl in [("t4_fonasa", "fonasa_beneficiaries_december"), ("t4_aps", "aps_enrolled_december"), ("t4_aps_centres", "aps_centres"),
                                      ("t4_isapre", "isapre_beneficiaries_december"), ("t4_ine2017", "ine_population_national")]:
                        obs = series_from_numeric(n4, key)
                        for y, e in CFG.CONTROLS[ctrl].items():
                            controls.append(control_row(f"T4_{ctrl}", y, e, obs.get(y), "T4 frente a config.CONTROLS"))
                    for key, ctrl in [("t4_r20_ret", "rem20_panel_188_retention"), ("t4_aps_ret", "aps_panel_1871_retention")]:
                        obs = series_from_numeric(n4, key)
                        for y, e in CFG.CONTROLS[ctrl].items():
                            controls.append(control_row(f"T4_{ctrl}", y, e, round(obs.get(y, np.nan) / 100, 4), "retención del panel (proporción)", tol_rel=0.005))
                    for key, ctrl in [("t6_pie_strict", "pie_tea_strict"), ("t6_pie_asperger", "pie_tea_asperger"), ("t6_pie_harmonised", "pie_harmonised"), ("t6_special", "pie_special_schools")]:
                        obs = series_from_numeric(n6, key)
                        for y, e in CFG.CONTROLS[ctrl].items():
                            controls.append(control_row(f"T6_{ctrl}", y, e, obs.get(y), "T6 frente a config.CONTROLS"))
                    for y, ctrl in [(2024, "junaeb_unweighted_2024"), (2025, "junaeb_unweighted_2025")]:
                        for lvl, e in CFG.CONTROLS[ctrl].items():
                            j = n6[(n6.row_key == f"junaeb:{lvl}") & (n6.year == y)]
                            controls.append(control_row(f"T6_{ctrl}", lvl, e, (j.n_tea_unweighted.iloc[0] if len(j) else np.nan), "JUNAEB casos TEA no ponderados"))
                    controls.append(control_row("T5_endide_unweighted_adults", "adults", CFG.CONTROLS["endide_unweighted"]["adults"],
                                                int(n5[(n5.survey == "ENDIDE 2022") & (n5.item_variable == "c26_33") & (n5.subgroup_type == "total")].cases.iloc[0]), "casos no ponderados"))
                    controls.append(control_row("T5_endide_unweighted_children", "children", CFG.CONTROLS["endide_unweighted"]["children"],
                                                int(n5[(n5.survey == "ENDIDE 2022") & (n5.item_variable == "n29_19") & (n5.subgroup_type == "total")].cases.iloc[0]), "casos no ponderados"))
                    controls.append(control_row("T5_encavi_unweighted_positive", "positive", CFG.CONTROLS["encavi_unweighted"]["positive"],
                                                int(n5[(n5.survey == "ENCAVI 2023-2024") & (n5.item_variable == "p4_6_1_h") & (n5.subgroup_type == "total") & (n5.estimate_type == "primary")].cases.iloc[0]), "casos no ponderados"))
                    controls.append(control_row("T5_unreliable_rows_not_shown_as_reliable", "all", 0, int(((n5.imprecise_lt30_cases | n5.suppressed_rse_gt30) & n5.shown_as_reliable).sum()),
                                                "filas imprecisas o con ERR > 30 % nunca mostradas como fiables"))
                # T2 sin_rett: la fila «diferencia entre variantes» (t2_rett_only_n) cuenta los episodios cuyo único
                # código F84 es F84.2 y tiene que caber dentro de la fila «F84.2 en cualquier posición» (t2_rett_n),
                # que cuenta el código lleve el episodio además otro código F84 o no.
                if variant == "sin_rett":
                    obs = series_from_numeric(n2, "t2_any_obs_n")
                    other = series_from_numeric(n2, "t2_other_variant_n")
                    rett = series_from_numeric(n2, "t2_rett_n")
                    for y in YEARS_GRD:
                        diff = other[y] - obs[y]
                        controls.append(control_row("T2_variant_difference_within_F842_episodes", y, True, bool(0 <= diff <= rett[y]),
                                                    f"con_rett − sin_rett = {int(diff)} episodios (solo F84.2 sin otro código F84) ≤ episodios con F84.2 = {int(rett[y])}"))
                controls.append(control_row("T7_missing_model_ids", variant, 0, len(missing), "; ".join(missing) if missing else "todas las especificaciones seleccionadas existen en models_summary.csv"))
    # coherencia entre idiomas
    for variant in VARIANTS:
        for name in ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]:
            controls.append(control_row(f"{name}_rows_es_equals_en", variant, row_counts[f"{variant}/es/{name}"], row_counts[f"{variant}/en/{name}"], "misma cantidad de filas en ambos idiomas"))
    ctrl_df = pd.DataFrame(controls)
    C.atomic_write_csv(ctrl_df, CONTROLS_DIR / f"{MODULE}_controls.csv")
    n_diff = int((ctrl_df.status == "differs").sum())
    total = round(time.perf_counter() - T_START, 2)
    runlog = dict(module=MODULE, script=SCRIPT, run_utc=datetime.now(timezone.utc).isoformat(), total_seconds=total, timings=timings,
                  variants=VARIANTS, languages=LANGS, models_summary_present=ms is not None, t7_missing_model_ids=t7_missing_all,
                  row_counts=row_counts, controls_total=int(len(ctrl_df)), controls_ok=int((ctrl_df.status == "ok").sum()), controls_differ=n_diff,
                  outputs=sorted(set(outputs)))
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    log(f"controles: {len(ctrl_df)} ({n_diff} difieren); runtime total: {total} s")
    if n_diff:
        for _, r in ctrl_df[ctrl_df.status == "differs"].iterrows():
            log(f"  difiere: {r['name']} [{r['key']}] esperado={r['expected']} observado={r['observed']} — {r['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
