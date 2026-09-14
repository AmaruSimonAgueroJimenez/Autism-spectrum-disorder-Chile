#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08a_figures_grd.py — Láminas F1 (fuentes, unidades y cobertura), F2 (núcleo hospitalario GRD) y suplementarias
S1–S4 del bloque GRD, por variante (`con_rett`, `sin_rett`) e idioma (`es`, `en`).

Lee únicamente las tablas tidy de `lancet_americas/outputs/tidy/` producidas por los módulos 01–06 y escribe:
  <variante>/<idioma>/figures/fig1_sources_coverage.png       F1: esquema de fuentes, capas de cobertura, establecimientos
                                                              reportantes REM, hospitales GRD, panel REM-20 y quiebres de definición.
  <variante>/<idioma>/figures/fig2_grd_core.png               F2: F84 cualquier posición/principal por 100.000 episodios (panel
                                                              observado y fijo, IC exactos), hospitalización estricta vs CMA,
                                                              profundidad diagnóstica, tasas poblacionales INE por edad y sexo,
                                                              caterpillar por hospital 2024 y personas dentro del año.
  <variante>/<idioma>/figures/figS1_grd_variants.png          S1: diferencias con/sin Rett en cada serie GRD.
  <variante>/<idioma>/figures/figS2_grd_subcodes.png          S2: composición de subcódigos F84 y posición por año.
  <variante>/<idioma>/figures/figS3_grd_hospital_effects.png  S3: efectos por hospital (hospital_effects.csv) y dumbbell 2019 vs 2024.
  <variante>/<idioma>/figures/figS4_grd_model_sensitivities.png  S4: forest de sensibilidades cuasi-Poisson (models_summary.csv).
  <variante>/<idioma>/figures/captions.json                   (fusionado con el existente) {nombre: {title, caption}}
  <variante>/<idioma>/tables/S_definition_breaks.csv + titles.json (fusionado): tabla de quiebres de definición por fuente.
  controls/08a_figures_grd_runlog.json                        registro de ejecución (tiempo, archivos, avisos).

Reglas respetadas: conteos = reconocimiento administrativo (nunca prevalencia/incidencia); GRD = «episodios con F84 documentado»
(F84 principal como serie separada); ninguna línea cruza un quiebre de definición REM; todo panel REM muestra establecimientos
reportantes; Serie P usa diciembre; stocks y flujos nunca comparten un eje; lugar de atención y residencia solo se combinan con
nota explícita; 2020–2021 sombreados como disrupción del reporte; Ley 21.545 (marzo 2023) marcada como contexto, no intervención;
panel fijo = 65 hospitales; personas únicas solo dentro del año.

Ejecución: `python3 lancet_americas/pipeline/08a_figures_grd.py` desde la raíz del repositorio. No modifica config/common/labels.
"""
from __future__ import annotations

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

MODULE = "08a_figures_grd"
SCRIPT = "lancet_americas/pipeline/08a_figures_grd.py"
VARIANTS = ["con_rett", "sin_rett"]
LANGS = CFG.LANGUAGES
YEARS_GRD = CFG.YEARS_GRD
YEARS_REM = CFG.YEARS_REM
PANDEMIC = CFG.PANDEMIC_YEARS
LAW_X = CFG.LAW_YEAR - 0.30          # marzo de 2023 en un eje con años centrados
PER = 100_000.0
OKABE = C.OKABE
COL = {"any": OKABE[0], "principal": OKABE[1], "hosp": OKABE[2], "cma": OKABE[3], "all": OKABE[0],
       "fixed": OKABE[0], "new": OKABE[1], "male": OKABE[0], "female": OKABE[1], "grey": "#7f8c8d",
       "con": OKABE[0], "sin": OKABE[1], "strict": OKABE[2]}
WARNINGS: list[str] = []
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Rótulos bilingües (todas las cadenas visibles)
# ---------------------------------------------------------------------------
LBL = {
    "figure": {"es": "Figura", "en": "Figure"},
    "table": {"es": "Tabla", "en": "Table"},
    "year": {"es": "Año", "en": "Year"},
    "law": {"es": "Ley 21.545\n(marzo 2023, contexto)", "en": "Law 21.545\n(March 2023, context)"},
    "law_plate": {"es": "Ley 21.545\n(marzo 2023,\ncontexto)", "en": "Law 21.545\n(March 2023,\ncontext)"},
    "pandemic_plate": {"es": "Disrupción del\nreporte\n2020–21", "en": "Reporting\ndisruption\n2020–21"},
    "pandemic": {"es": "Disrupción del\nreporte 2020–21", "en": "Reporting\ndisruption 2020–21"},
    "millions": {"es": "Millones de personas", "en": "Millions of people"},
    "thousands": {"es": "miles", "en": "thousands"},
    "variant_con_rett": {"es": "F84 completo (con Rett)", "en": "Full F84 (with Rett)"},
    "variant_sin_rett": {"es": "F84 sin Rett", "en": "F84 without Rett"},
    # Etiqueta corta para las leyendas de celda estrecha: en una celda de 90 mm la etiqueta larga
    # («F84 completo (con Rett)») multiplicada por cuatro series se sale del panel.
    "variant_short_con_rett": {"es": "con Rett", "en": "with Rett"},
    "variant_short_sin_rett": {"es": "sin Rett", "en": "without Rett"},
    "strict_f840": {"es": "Solo F84.0 (idéntico en ambas variantes)", "en": "F84.0 only (identical in both variants)"},
    "identical_note": {"es": "Idéntica en ambas variantes de definición", "en": "Identical in both definition variants"},
    # F1
    "f1_title_b": {"es": "Capas de cobertura, 2019–2025", "en": "Coverage layers, 2019–2025"},
    "f1_title_c": {"es": "Establecimientos REM por era", "en": "REM establishments by era"},
    "f1_title_d": {"es": "Hospitales y episodios GRD", "en": "GRD hospitals and episodes"},
    "f1_title_e": {"es": "REM-20: panel de 188 y retención", "en": "REM-20: 188-panel and retention"},
    "f1_title_f": {"es": "Quiebres por fuente, 2019–2025", "en": "Breaks by source, 2019–2025"},
    "f1_ine": {"es": "INE (30 jun)", "en": "INE (30 June)"},
    "f1_fonasa": {"es": "FONASA (dic)", "en": "FONASA (Dec)"},
    "f1_aps": {"es": "APS inscritos (dic)", "en": "APS enrolled (Dec)"},
    "f1_isapre": {"es": "ISAPRE (dic)", "en": "ISAPRE (Dec)"},
    "f1_share": {"es": "Cociente (eje der.)", "en": "Ratio (right axis)"},
    "f1_share_axis": {"es": "(FONASA + ISAPRE) / INE (%)", "en": "(FONASA + ISAPRE) / INE (%)"},
    "f1_share_caveat": {"es": "El cociente no es una tasa de aseguramiento:\nstocks de diciembre frente a proyección al 30 de\njunio; omite otros regímenes",
                        "en": "The ratio is not an insurance rate: December\nstocks versus a 30-June projection; other\nregimes are omitted"},
    "f1_estab_axis": {"es": "Establecimientos reportantes (log)", "en": "Reporting establishments (log)"},
    "f1_a03_legacy": {"es": "A03 M-CHAT legado 2019–22 (03500406/07)", "en": "A03 legacy M-CHAT 2019–22 (03500406/07)"},
    "f1_a03_2023": {"es": "A03 M-CHAT-R/F 2023–24 (09600212–19)", "en": "A03 M-CHAT-R/F 2023–24 (09600212–19)"},
    "f1_a03_3159": {"es": "A03 31–59 meses 2024 (03700104–09)", "en": "A03 31–59 months 2024 (03700104–09)"},
    "f1_a03_2025": {"es": "A03 rediseño 2025 (03710013–21)", "en": "A03 redesign 2025 (03710013–21)"},
    "f1_a05_broad": {"es": "A05 TGD amplio 2019–20 (06902600)", "en": "A05 broad PDD 2019–20 (06902600)"},
    "f1_a05_autism": {"es": "A05 autismo 2021–25 (05990022)", "en": "A05 autism 2021–25 (05990022)"},
    "f1_a27": {"es": "A27 consejería/referencia 2023–25", "en": "A27 counselling/referral 2023–25"},
    "f1_a28": {"es": "A28 rehabilitación 2023–25", "en": "A28 rehabilitation 2023–25"},
    "f1_p2": {"es": "P2 TEA NANEAS, diciembre (P2500500)", "en": "P2 ASD NANEAS, December (P2500500)"},
    "f1_p6_broad": {"es": "P6 TGD amplio, dic 2019–20", "en": "P6 broad PDD, Dec 2019–20"},
    "f1_p6_autism": {"es": "P6 autismo, dic 2021–25", "en": "P6 autism, Dec 2021–25"},
    "f1_estab_note": {"es": "Máximo entre los códigos de la era; ninguna línea cruza un quiebre de definición",
                      "en": "Maximum across the era's codes; no line crosses a definition break"},
    "f1_hosp_obs": {"es": "Hospitales observados", "en": "Hospitals observed"},
    "f1_hosp_fixed": {"es": "Panel fijo (65)", "en": "Fixed panel (65)"},
    "f1_hosp_axis": {"es": "Hospitales GRD", "en": "GRD hospitals"},
    "f1_epi_obs": {"es": "Episodios GRD, panel observado (millones)", "en": "GRD episodes, observed panel (millions)"},
    "f1_epi_fixed": {"es": "Episodios GRD, panel fijo (millones)", "en": "GRD episodes, fixed panel (millions)"},
    "f1_epi_axis": {"es": "Episodios GRD (millones)", "en": "GRD episodes (millions)"},
    "f1_rem20_all": {"es": "Todos los establecimientos", "en": "All establishments"},
    "f1_rem20_panel": {"es": "Panel de 188", "en": "188-panel"},
    "f1_rem20_axis": {"es": "Egresos (miles)", "en": "Discharges (thousands)"},
    "f1_rem20_ret": {"es": "Retención del panel (%)", "en": "Panel retention (%)"},
    "f1_rem20_n": {"es": "n reportantes", "en": "n reporting"},
    "f1_rem20_note": {"es": "Actividad/capacidad hospitalaria;\nno es un denominador poblacional",
                      "en": "Hospital activity/capacity;\nnot a population denominator"},
    "f1_tl_axis": {"es": "Año de reporte", "en": "Reporting year"},
    "f1_tl_def": {"es": "Cambio de definición/códigos", "en": "Definition/code change"},
    "f1_tl_panel": {"es": "Cambio de panel/cobertura/esquema", "en": "Panel/coverage/schema change"},
    "f1_tl_start": {"es": "Inicio de serie", "en": "Series start"},
    "f1_tl_note": {"es": "Cada quiebre, en la tabla de quiebres", "en": "Each break, in the definition-breaks table"},
    # F1a — estados de la celda REM (reemplaza el esquema de fuentes, ya cubierto por la Figura 1)
    "f1_title_a": {"es": "Estados de una celda REM", "en": "States of a REM cell"},
    "f1_states_value": {"es": "valor informado", "en": "reported value"},
    "f1_states_zero": {"es": "cero explícito", "en": "explicit zero"},
    "f1_states_nr": {"es": "no informado", "en": "not reported"},
    "f1_states_rows": {"es": "Filas\n(miles)", "en": "Rows\n(thousands)"},
    "f1_states_deis": {"es": "Celdas en blanco {b} · filas duplicadas {d}. Un blanco no es un cero. DEIS enmascara {n} egresos.",
                       "en": "Blank cells {b} · duplicate rows {d}. A blank is not a zero. DEIS masks {n} discharges."},
    # F1c — rótulos cortos de la leyenda (celda vertical)
    "f1_s_a03_legacy": {"es": "A03 M-CHAT 2019–22", "en": "A03 M-CHAT 2019–22"},
    "f1_s_a03_2023": {"es": "A03 M-CHAT-R/F 2023–24", "en": "A03 M-CHAT-R/F 2023–24"},
    "f1_s_a03_3159": {"es": "A03 31–59 meses 2024", "en": "A03 31–59 months 2024"},
    "f1_s_a03_2025": {"es": "A03 rediseño 2025", "en": "A03 redesign 2025"},
    "f1_s_a05_broad": {"es": "A05 TGD amplio 2019–20", "en": "A05 broad PDD 2019–20"},
    "f1_s_a05_autism": {"es": "A05 autismo 2021–25", "en": "A05 autism 2021–25"},
    "f1_s_a27": {"es": "A27 consejería 2023–25", "en": "A27 counselling 2023–25"},
    "f1_s_a28": {"es": "A28 rehabilitación 2023–25", "en": "A28 rehabilitation 2023–25"},
    "f1_s_p2": {"es": "P2 TEA NANEAS, dic", "en": "P2 ASD NANEAS, Dec"},
    "f1_s_p6_broad": {"es": "P6 TGD amplio, dic 2019–20", "en": "P6 broad PDD, Dec 2019–20"},
    "f1_s_p6_autism": {"es": "P6 autismo, dic 2021–25", "en": "P6 autism, Dec 2021–25"},
    # naturaleza de la fuente (tabla de quiebres)
    "s_flow": {"es": "Flujo", "en": "Flow"}, "s_stock": {"es": "Stock", "en": "Stock"},
    "s_activity": {"es": "Actividad/capacidad", "en": "Activity/capacity"},
    "s_survey": {"es": "Encuesta transversal", "en": "Cross-sectional survey"},
    "s_education": {"es": "Stock escolar", "en": "School stock"},
    # F2
    "f2_title_a": {"es": "F84 por 100.000 episodios GRD", "en": "F84 per 100,000 GRD episodes"},
    "f2_title_b": {"es": "Hospitalización y CMA", "en": "Hospitalisation and CMA"},
    "f2_title_c": {"es": "Profundidad diagnóstica y tasa", "en": "Coding depth and rate"},
    "f2_title_d": {"es": "Población: edad y sexo", "en": "Population: age and sex"},
    "f2_title_e": {"es": "Tasa por hospital, 2024", "en": "Rate by hospital, 2024"},
    "f2_title_f": {"es": "Personas y episodios", "en": "Persons and episodes"},
    "f2_rate_axis": {"es": "Episodios con F84 por 100.000 episodios GRD (log)", "en": "Episodes with F84 per 100,000 GRD episodes (log)"},
    "f2_rate_axis_lin": {"es": "Episodios con F84 por 100.000 episodios GRD", "en": "Episodes with F84 per 100,000 GRD episodes"},
    "f2_any_obs": {"es": "Cualquier posición, panel observado", "en": "Any position, observed panel"},
    "f2_any_fixed": {"es": "Cualquier posición, panel fijo de 65", "en": "Any position, fixed panel of 65"},
    "f2_pri_obs": {"es": "Principal, panel observado", "en": "Principal, observed panel"},
    "f2_pri_fixed": {"es": "Principal, panel fijo de 65", "en": "Principal, fixed panel of 65"},
    "f2_hosp_n": {"es": "Hospitales:", "en": "Hospitals:"},
    "f2_act_all": {"es": "Toda modalidad", "en": "All activity"},
    "f2_act_hosp": {"es": "Hospitalización estricta", "en": "Strict hospitalisation"},
    "f2_act_cma": {"es": "Cirugía mayor ambulatoria (CMA)", "en": "Major ambulatory surgery (CMA)"},
    "f2_other_note": {"es": "«Otra» modalidad: categoría ausente 2020–2024 (no cero)", "en": "'Other' activity: category absent 2020–2024 (not zero)"},
    "f2_depth_bin_axis": {"es": "Diagnósticos codificados por episodio (estrato)", "en": "Coded diagnoses per episode (stratum)"},
    "f2_depth_rate_axis": {"es": "F84 por 100.000 episodios del estrato", "en": "F84 per 100,000 episodes in stratum"},
    "f2_depth_all": {"es": "Todos los episodios", "en": "All episodes"},
    "f2_depth_f84": {"es": "Episodios con F84", "en": "Episodes with F84"},
    "f2_depth_inset": {"es": "Profundidad media", "en": "Mean depth"},
    "f2_depth_year": {"es": "Año", "en": "Year"},
    "f2_age_axis": {"es": "Grupo de edad (años)", "en": "Age group (years)"},
    "f2_pop_axis": {"es": "Episodios con F84 por 100.000 habitantes (log)", "en": "Episodes with F84 per 100,000 population (log)"},
    "f2_pop_note": {"es": "Numerador: lugar de atención (hospitales\npúblicos GRD); denominador: residencia\n(INE base 2017). Lectura complementaria.",
                    "en": "Numerator: place of care (public GRD\nhospitals); denominator: residence\n(INE base 2017). Complementary reading."},
    "males": {"es": "Hombres", "en": "Males"}, "females": {"es": "Mujeres", "en": "Females"},
    "f2_cat_rank": {"es": "Hospitales ordenados por tasa (n = 72)", "en": "Hospitals ranked by rate (n = 72)"},
    "f2_cat_axis": {"es": "F84 por 100.000 episodios del hospital (log, IC 95 % exacto)", "en": "F84 per 100,000 hospital episodes (log, exact 95% CI)"},
    "f2_cat_fixed": {"es": "Panel fijo 2019–2024 (65)", "en": "Fixed panel 2019–2024 (65)"},
    "f2_cat_new": {"es": "Incorporado en 2023–2024 (7)", "en": "Added in 2023–2024 (7)"},
    "f2_cat_nat": {"es": "Nacional", "en": "National"},
    "f2_episodes": {"es": "Episodios con F84 (cualquier posición)", "en": "Episodes with F84 (any position)"},
    "f2_persons": {"es": "Personas únicas dentro del año", "en": "Unique persons within year"},
    "f2_count_axis": {"es": "Episodios / personas (miles)", "en": "Episodes / persons (thousands)"},
    "f2_epp": {"es": "episodios por persona", "en": "episodes per person"},
    "f2_mf": {"es": "Razón H:M de episodios (IC 95 %)", "en": "M:F ratio of episodes (95% CI)"},
    "f2_mf_axis": {"es": "Razón hombre:mujer", "en": "Male:female ratio"},
    "f2_persons_note": {"es": "Sin deduplicación entre años\n(el identificador cambia en 2020/2021)", "en": "No deduplication across years\n(identifier changes in 2020/2021)"},
    # S1
    "s1_title_a": {"es": "Cualquier posición, toda modalidad (panel observado)", "en": "Any position, all activity (observed panel)"},
    "s1_title_b": {"es": "F84 principal, toda modalidad (panel observado)", "en": "Principal F84, all activity (observed panel)"},
    "s1_title_c": {"es": "Hospitalización estricta y CMA (cualquier posición)", "en": "Strict hospitalisation and CMA (any position)"},
    "s1_title_d": {"es": "Episodios con F84.2 (Rett) por posición", "en": "Episodes with F84.2 (Rett) by position"},
    "s1_title_e": {"es": "Diferencia relativa con − sin Rett por serie", "en": "Relative difference with − without Rett by series"},
    "s1_title_f": {"es": "Panel fijo de 65 y personas dentro del año", "en": "Fixed panel of 65 and persons within year"},
    "s1_rett_any": {"es": "F84.2 en cualquier posición", "en": "F84.2 in any position"},
    "s1_rett_pri": {"es": "F84.2 principal", "en": "F84.2 principal"},
    "s1_rett_share": {"es": "% de la familia F84", "en": "% of the F84 family"},
    "s1_rel_axis": {"es": "(con − sin) / sin, %", "en": "(with − without) / without, %"},
    "s1_series_any": {"es": "Cualquier posición · toda modalidad", "en": "Any position · all activity"},
    "s1_series_pri": {"es": "Principal · toda modalidad", "en": "Principal · all activity"},
    "s1_series_hosp": {"es": "Cualquier posición · hospitalización", "en": "Any position · hospitalisation"},
    "s1_series_cma": {"es": "Cualquier posición · CMA", "en": "Any position · CMA"},
    "s1_series_persons": {"es": "Personas dentro del año", "en": "Persons within year"},
    "s1_fixed_any": {"es": "Cualquier posición, panel fijo", "en": "Any position, fixed panel"},
    "s1_fixed_pri": {"es": "Principal, panel fijo", "en": "Principal, fixed panel"},
    "s1_persons_axis": {"es": "Personas únicas dentro del año", "en": "Unique persons within year"},
    "s1_persons_bar": {"es": "Personas", "en": "Persons"},
    "episodes": {"es": "Episodios", "en": "Episodes"},
    # S2
    "s2_title_a": {"es": "Composición de subcódigos (menciones, cualquier posición)", "en": "Subcode composition (mentions, any position)"},
    "s2_title_b": {"es": "Menciones por subcódigo", "en": "Mentions by subcode"},
    "s2_title_c": {"es": "% de menciones en posición principal", "en": "% of mentions in principal position"},
    "s2_title_d": {"es": "Posición del código en el episodio", "en": "Code position within the episode"},
    "s2_title_e": {"es": "Solo F84.0 frente a familia F84 por 100.000 episodios", "en": "F84.0 only versus F84 family per 100,000 episodes"},
    "s2_title_f": {"es": "F84.2 (síndrome de Rett) por posición", "en": "F84.2 (Rett syndrome) by position"},
    "s2_share_axis": {"es": "% de las menciones F84", "en": "% of F84 mentions"},
    "s2_count_axis": {"es": "Menciones (escala logarítmica)", "en": "Mentions (log scale)"},
    "s2_pct_pri_axis": {"es": "% principal dentro del subcódigo", "en": "% principal within subcode"},
    "s2_pos_principal": {"es": "Solo principal", "en": "Principal only"},
    "s2_pos_both": {"es": "Principal y secundario", "en": "Principal and secondary"},
    "s2_pos_secondary": {"es": "Solo secundario", "en": "Secondary only"},
    "s2_pct_sec": {"es": "% solo secundario", "en": "% secondary only"},
    "s2_family": {"es": "Familia F84 (variante)", "en": "F84 family (variant)"},
    "s2_rett_note_con": {"es": "Incluido en esta variante", "en": "Included in this variant"},
    "s2_rett_note_sin": {"es": "Excluido de esta variante (se muestra como referencia)", "en": "Excluded from this variant (shown for reference)"},
    "s2_mentions_note": {"es": "Un episodio puede tener más de un subcódigo F84: menciones ≠ episodios",
                         "en": "An episode may carry more than one F84 subcode: mentions ≠ episodes"},
    # S3
    "s3_title_a": {"es": "Efectos fijos de hospital (RR)", "en": "Hospital fixed effects (RR)"},
    "s3_title_b": {"es": "Contracción del intercepto aleatorio", "en": "Random-intercept shrinkage"},
    "s3_title_c": {"es": "Tasa 2024 frente a profundidad diagnóstica del hospital", "en": "2024 rate versus hospital coding depth"},
    "s3_title_d": {"es": "Distribución de tasas por hospital y año", "en": "Distribution of hospital rates by year"},
    "s3_title_e": {"es": "Tasa por hospital, 2019 frente a 2024: mitad con la tasa 2024 más alta",
                   "en": "Rate by hospital, 2019 versus 2024: half with the higher 2024 rate"},
    "s3_title_f": {"es": "Tasa por hospital, 2019 frente a 2024: mitad con la tasa 2024 más baja",
                   "en": "Rate by hospital, 2019 versus 2024: half with the lower 2024 rate"},
    "s3_rr_axis": {"es": "Razón de tasas (log, IC 95 %)", "en": "Rate ratio (log, 95% CI)"},
    "s3_rank": {"es": "Hospitales ordenados", "en": "Hospitals ranked"},
    "s3_fe_depth": {"es": "Ajustado por profundidad del hospital-año", "en": "Adjusted for hospital-year coding depth"},
    "s3_fe_axis": {"es": "Efecto fijo centrado (log)", "en": "Centred fixed effect (log)"},
    "s3_ri_axis": {"es": "Intercepto aleatorio, media posterior (log)", "en": "Random intercept, posterior mean (log)"},
    "s3_identity": {"es": "Identidad", "en": "Identity"},
    "s3_sd": {"es": "DE del intercepto", "en": "Intercept SD"},
    "s3_depth_axis": {"es": "Profundidad diagnóstica media del hospital, 2024", "en": "Mean hospital coding depth, 2024"},
    "s3_rate_axis": {"es": "F84 por 100.000 episodios del hospital (log)", "en": "F84 per 100,000 hospital episodes (log)"},
    "s3_spearman": {"es": "ρ de Spearman", "en": "Spearman ρ"},
    "s3_eco_note": {"es": "Asociación ecológica; no implica causalidad ni calidad", "en": "Ecological association; implies neither causality nor quality"},
    "s3_box_note": {"es": "Cajas: mediana y cuartiles; puntos: hospitales; línea: mediana del panel fijo",
                    "en": "Boxes: median and quartiles; points: hospitals; line: fixed-panel median"},
    "s3_zero": {"es": "0 en 2019 (sin episodios F84)", "en": "0 in 2019 (no F84 episodes)"},
    "s3_fallback": {"es": "hospital_effects.csv no disponible: se muestran solo tasas por hospital", "en": "hospital_effects.csv not available: hospital rates only"},
    # S4
    "s4_title_any": {"es": "F84 en cualquier posición", "en": "F84 in any position"},
    "s4_title_pri": {"es": "F84 principal", "en": "Principal F84"},
    "s4_axis": {"es": "Cambio porcentual anual (%) e IC 95 %", "en": "Annual percent change (%) and 95% CI"},
    "s4_grp_rate": {"es": "Por 100.000 episodios GRD (nacional)", "en": "Per 100,000 GRD episodes (national)"},
    "s4_grp_hosp": {"es": "Hospital-año (offset log episodios del hospital)", "en": "Hospital-year (log hospital-episodes offset)"},
    "s4_grp_pop": {"es": "Por 100.000 habitantes INE (ambos sexos)", "en": "Per 100,000 INE population (both sexes)"},
    "s4_note": {"es": "Ninguna especificación estima un efecto de la Ley 21.545; el indicador 2020–21 describe la disrupción del reporte",
                "en": "No specification estimates an effect of Law 21.545; the 2020–21 indicator describes reporting disruption"},
    "s4_base": {"es": "Modelo base", "en": "Base model"},
    # Rótulos CORTOS de fila para la lámina vertical: en una celda de 90 mm el rótulo largo mide 150 pt y
    # el hueco a la izquierda del panel da para 85. El nombre completo de cada especificación está en la
    # tabla de modelos y en el pie de la figura.
    "s4_sh_panel_observed": {"es": "obs.", "en": "obs."},
    "s4_sh_panel_fixed65": {"es": "fijo 65", "en": "fixed 65"},
    "s4_sh_act_all": {"es": "toda", "en": "all"},
    "s4_sh_act_hospitalisation": {"es": "hosp.", "en": "hosp."},
    "s4_sh_cov_none": {"es": "sin cov.", "en": "no cov."},
    "s4_sh_cov_depth": {"es": "+prof.", "en": "+depth"},
    "s4_sh_cov_disruption": {"es": "+2020–21", "en": "+2020–21"},
    "s4_sh_cov_depth_disruption": {"es": "+prof.+2020–21", "en": "+depth+2020–21"},
    "s4_sh_cov_hospital_fe": {"es": "EF hosp.", "en": "hosp. FE"},
    "s4_sh_cov_hospital_fe_depth": {"es": "EF hosp.+prof.", "en": "hosp. FE+depth"},
    "s4_sh_cov_hospital_fe_disruption": {"es": "EF hosp.+2020–21", "en": "hosp. FE+2020–21"},
    "s4_sh_cov_hospital_ri": {"es": "int. aleat.", "en": "random int."},
    "s4_sh_cov_hospital_ri_depth": {"es": "int. aleat.+prof.", "en": "random int.+depth"},
    "s4_sh_cov_age": {"es": "ajustadas por edad", "en": "age-adjusted"},
    "s4_sh_fam_qp_fe_cluster": {"es": "EE rob.", "en": "robust SE"},
    "s4_sh_fam_ri_map": {"es": "Laplace", "en": "Laplace"},
    "s4_sh_crude": {"es": "brutas", "en": "crude"},
    "s4_none": {"es": "Sin especificaciones estimadas para esta serie", "en": "No specifications estimated for this series"},
    "s4_abbr": {"es": "Rótulos abreviados; especificación completa en la tabla de modelos",
                "en": "Labels abbreviated; full specification in the models table"},
    "s4_w1924": {"es": "Ventana 2019–2024", "en": "Window 2019–2024"},
    "s4_w2124": {"es": "Ventana 2021–2024", "en": "Window 2021–2024"},
    "s4_clipped": {"es": "IC truncado en el eje", "en": "CI clipped at axis"},
    "panel_observed": {"es": "panel observado", "en": "observed panel"},
    "panel_fixed65": {"es": "panel fijo 65", "en": "fixed panel 65"},
    "act_all": {"es": "toda modalidad", "en": "all activity"},
    "act_hospitalisation": {"es": "hosp. estricta", "en": "strict hosp."},
    "cov_none": {"es": "sin covariables", "en": "no covariates"},
    "cov_depth": {"es": "+ profundidad", "en": "+ coding depth"},
    "cov_disruption": {"es": "+ indicador 2020–21", "en": "+ 2020–21 indicator"},
    "cov_depth_disruption": {"es": "+ profundidad + 2020–21", "en": "+ depth + 2020–21"},
    "cov_hospital_fe": {"es": "EF de hospital", "en": "hospital FE"},
    "cov_hospital_fe_depth": {"es": "EF de hospital + profundidad", "en": "hospital FE + depth"},
    "cov_hospital_fe_disruption": {"es": "EF de hospital + 2020–21", "en": "hospital FE + 2020–21"},
    "cov_hospital_ri": {"es": "intercepto aleatorio", "en": "random intercept"},
    "cov_hospital_ri_depth": {"es": "intercepto aleatorio + profundidad", "en": "random intercept + depth"},
    "cov_age": {"es": "ajustado por edad", "en": "age-adjusted"},
    "fam_qp_fe_cluster": {"es": "EE robustos por hospital", "en": "hospital-clustered SE"},
    "fam_ri_map": {"es": "Laplace/MAP", "en": "Laplace/MAP"},
    "crude": {"es": "bruto", "en": "crude"},
    # tabla de quiebres
    "tb_source": {"es": "Fuente", "en": "Source"}, "tb_years": {"es": "Años", "en": "Years"},
    "tb_unit": {"es": "Unidad", "en": "Unit"}, "tb_type": {"es": "Stock/flujo", "en": "Stock/flow"},
    "tb_break_year": {"es": "Año del quiebre", "en": "Break year"}, "tb_break": {"es": "Quiebre", "en": "Break"},
    "tb_kind": {"es": "Tipo", "en": "Kind"},
}


def tr(key: str, lang: str) -> str:
    return LBL[key][lang]


#: EL SIGNO NEGATIVO Y EL SIGNO DE PORCENTAJE, las dos convenciones que esta lámina escribe con cifras.
#:
#: El NEGATIVO lleva el menos tipográfico (U+2212), no el guion ASCII: el guion mide 2,9 pt a 8 pt de
#: cuerpo y se dibuja a la altura de la x, mientras la raya de intervalo de la misma lámina mide 4,1 pt, de
#: modo que en la nota de la S3 (c) —«ρ de Spearman = −0,06»— el signo y un separador de rango vecino se
#: leían igual. La regla NO se repite aquí: vive en `common.fmt_number` (con `common.MINUS_SIGN` y
#: `common.to_ascii_minus` para el camino de vuelta) y este módulo la hereda porque TODA cifra que imprime
#: pasa por `num` —rótulos de valor, notas, títulos, leyendas y las marcas de eje de `localise_ticks`,
#: `fmt_axis` y `log_axis_fmt`—. Lo que este módulo sí garantiza es que no haya atajos: ningún rótulo de
#: lámina se formatea con `f"{x:.1f}"` a mano (los únicos formatos crudos que quedan son los años de dos
#: cifras «’19», que nunca son negativos, y las líneas de consola). El RANGO conserva su raya (U+2013):
#: son dos signos con dos oficios (ver `figS4`, donde la ventana de años pasa de guion a raya).
#:
#: El PORCENTAJE se escribe «12,3 %» en español y «12.3%» en inglés. Esa regla todavía no está en `common`
#: —la escriben nueve módulos por su cuenta— y aquí la aplica `pct_str`.


def num(x, dec=0, lang="es") -> str:
    return C.fmt_number(x, dec, lang)


def pct_str(x, lang="es", dec=1) -> str:
    """Porcentaje en la convención del idioma: «12,3 %» en español (espacio) y «12.3%» en inglés (pegado).

    Tres rótulos de valor de este módulo —S1 (d), S2 (a) y S2 (d)— escribían a mano el sufijo « %» sin
    mirar el idioma, de modo que las láminas INGLESAS imprimían «89.9 %» dentro de un corpus que en el
    texto y en las tablas escribe «89.9%». Se llama `pct_str` y no `pct` porque `figS2` usa `pct` como
    nombre de una serie local: una función de módulo con ese nombre quedaría tapada justo donde se la
    necesita."""
    return num(x, dec, lang) + (" %" if lang == "es" else "%")


def variant_label(variant: str, lang: str) -> str:
    return tr(f"variant_{variant}", lang)


def variant_short(variant: str, lang: str) -> str:
    """Etiqueta corta de variante para las leyendas de una celda de lámina."""
    return tr(f"variant_short_{variant}", lang)


# ---------------------------------------------------------------------------
# Norma de lámina: 180 × 245 mm en vertical, dibujada 1:1 (una lámina por página, sin reducción)
# 3 filas × 2 columnas, seis paneles como máximo, letras minúsculas, nada bajo 6 pt, 600 dpi.
# ---------------------------------------------------------------------------
PLATE_W_MM, PLATE_H_MM = 180.0, 245.0
MM_PER_IN = 25.4
PLATE_SIZE = (PLATE_W_MM / MM_PER_IN, PLATE_H_MM / MM_PER_IN)   # 7,09 × 9,65 pulgadas
FS_BASE, FS_TITLE, FS_TICK, FS_LEG, FS_MIN = 8.0, 9.0, 7.0, 7.0, 6.0


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


def new_plate(plt, nrows: int = 3, ncols: int = 2, **kw):
    """Lienzo de 180 × 245 mm con la rejilla de la norma (3 × 2 por omisión)."""
    fig, ax = plt.subplots(nrows, ncols, figsize=PLATE_SIZE, constrained_layout=True, **kw)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    return fig, ax


# Recuadro translúcido para notas y anotaciones: la nota sigue legible cuando cae sobre una serie y la
# serie sigue visible bajo la nota. Ninguna nota de esta norma se dibuja sin él.
NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.4)

# Ancho útil del título en una celda de la rejilla: media lámina menos 4 mm de margen. El plegado se hace
# por ancho MEDIDO (C.plate_wrap) y no por número de caracteres, que dejaba títulos largos en español
# desbordando la celda y cortados contra el borde derecho del lienzo.
PLATE_TITLE_W_PT = (PLATE_W_MM / MM_PER_IN * 72.0) / 2 - (4.0 / MM_PER_IN * 72.0)


def panel_head(ax, letter_: str, title: str, fs: float = FS_TITLE, pad: float = 3.0, chars: int | None = None) -> None:
    """Cabecera del panel: letra minúscula y título a la izquierda de SU celda, plegados al ancho de la celda.

    `chars` se conserva por compatibilidad con las llamadas antiguas y ya no se usa."""
    # matplotlib guarda TRES artistas de título (izquierda, centro, derecha): si un ayudante ya puso el
    # título centrado, escribir el de la izquierda dejaría los dos impresos, uno encima del otro.
    ax.set_title("", loc="center"); ax.set_title("", loc="right")
    ax.set_title(C.plate_wrap(f"({letter_}) {title}", PLATE_TITLE_W_PT, fs, "bold"),
                 loc="left", fontsize=fs, fontweight="bold", pad=pad, linespacing=1.15)


# Ancho útil del texto dentro de una celda: la celda mide 90 mm, de los que el rótulo y las marcas del eje
# Y se llevan unos 20 mm; el área de ejes queda en 52–58 mm ≈ 150 pt. Las notas se pliegan a ese ancho, no
# al de la celda, porque se dibujan DENTRO de los ejes.
NOTE_W_PT = 150.0


def plate_legend(ax, *args, loc: str = "upper left", fs: float | None = None, ncol: int = 1, **kw):
    """Leyenda de celda estrecha: cuerpo 6,2 pt, una columna y recuadro blanco translúcido.

    En una celda de 90 mm una leyenda sin recuadro se lee sobre las series y las oculta; con el recuadro
    translúcido la serie sigue visible bajo ella y el texto sigue legible."""
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
    """Nota dentro del panel, plegada al ancho MEDIDO de la celda y sobre recuadro blanco translúcido.

    Las notas sin plegar se cortaban contra el borde del lienzo o se imprimían encima de las barras."""
    fs = FS_MIN + 0.3 if fs is None else fs
    return ax.text(x, y, C.plate_wrap(text, width_pt, fs, "normal"), transform=ax.transAxes, fontsize=fs,
                   ha=ha, va=va, color=color, bbox=NOTE_BBOX, linespacing=1.25, zorder=6)


def freeze_texts(fig) -> None:
    """Excluye del reparto del lienzo los rótulos sueltos (ax.text / annotate).

    Un rótulo de valor o una nota son más anchos que su celda y, si entran en el cálculo de `constrained_layout`,
    el motor encoge los ejes hasta colapsarlos. Títulos, rótulos de eje y leyendas sí siguen gobernando el reparto.
    """
    for ax in fig.axes:
        for t in ax.texts:
            t.set_in_layout(False)


def localise_ticks(fig, lang: str) -> None:
    """Separador de miles del idioma en TODAS las marcas numéricas de la lámina (español 20.000, inglés 20,000).

    Los paneles que no llamaban al formateador imprimían «50000» a secas, que no es la convención de ninguno de
    los dos idiomas. Se recorre la lámina entera justo antes de componerla, de modo que ningún panel se quede
    fuera. Un eje de AÑOS se reconoce por sus marcas (enteros entre 1900 y 2100 en un rango de 40 años) y se
    deja como está: el año no lleva separador. Los ejes con rótulos fijos o escala logarítmica ya traen su
    propio formateador y no se tocan.
    """
    from matplotlib.ticker import ScalarFormatter, FuncFormatter
    for ax in fig.axes:
        for axis, scale in ((ax.xaxis, ax.get_xscale()), (ax.yaxis, ax.get_yscale())):
            if scale != "linear" or not isinstance(axis.get_major_formatter(), ScalarFormatter):
                continue
            lo, hi = sorted(axis.get_view_interval())
            ticks = [t for t in axis.get_majorticklocs() if lo - 1e-9 <= t <= hi + 1e-9]
            if not ticks:
                continue
            if (all(abs(t - round(t)) < 1e-6 and 1900.0 <= t <= 2100.0 for t in ticks)
                    and max(ticks) - min(ticks) <= 40.0):
                continue                      # eje de años: 2019, nunca 2.019
            dec = 3
            for d in range(4):
                if all(abs(t * 10 ** d - round(t * 10 ** d)) < 1e-6 for t in ticks):
                    dec = d
                    break
            axis.set_major_formatter(FuncFormatter(lambda v, _p, dec=dec, lang=lang: num(v, dec, lang)))


def spread_value_labels(ax, anns, gap_pt: float = 1.2, rounds: int = 8) -> None:
    """Separa en vertical los rótulos de valor que, ya colocados, siguen tocándose.

    `C.plate_value_label` mide y esquiva marcadores y barras de error, pero cuando NINGUNA posición queda
    libre prefiere solaparse con otro rótulo antes que con un dato. En una nube de dieciséis regiones eso
    dejaba «Arica y P.» impreso sobre «Aysén». Aquí se mide el par que se toca y se apartan los dos, medio
    solape cada uno, en el sistema de coordenadas propio de la anotación (desplazamiento en puntos).
    """
    fig = ax.figure
    anns = [a for a in anns if a is not None]
    for _ in range(max(1, rounds)):
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        boxes = []
        for a in anns:
            try:
                boxes.append(a.get_window_extent(r))
            except (AttributeError, ValueError, RuntimeError):
                boxes.append(None)
        moved = False
        for i in range(len(anns)):
            for j in range(i + 1, len(anns)):
                ba, bb = boxes[i], boxes[j]
                if ba is None or bb is None:
                    continue
                over_x = min(ba.x1, bb.x1) - max(ba.x0, bb.x0)
                over_y = min(ba.y1, bb.y1) - max(ba.y0, bb.y0)
                if over_x <= 0.0 or over_y <= 0.0:
                    continue
                push = (over_y / 2.0) * 72.0 / fig.dpi + gap_pt
                up, down = (i, j) if (ba.y0 + ba.y1) >= (bb.y0 + bb.y1) else (j, i)
                for k, sgn in ((up, 1.0), (down, -1.0)):
                    dx, dy = anns[k].xyann
                    anns[k].xyann = (dx, dy + sgn * push)
                moved = True
        if not moved:
            return


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


def save_plate(fig, path: Path, dpi: int = 600) -> Path:
    """Guarda sin recorte para que el archivo mida exactamente 180 × 245 mm a 600 dpi (1:1 en la página)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    localise_ticks(fig, getattr(fig, "_plate_lang", "es"))
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
    # Los rótulos que hay que separar a mano se apartan con la composición YA CONGELADA: hecho antes, el
    # reparto del lienzo movía los ejes y el par volvía a tocarse.
    for _ax, _anns in getattr(fig, "_plate_spread", []):
        spread_value_labels(_ax, _anns)
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


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
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


def optional_tidy(name: str, **kw):
    path = CFG.TIDY / f"{name}.csv"
    if not path.is_file():
        WARNINGS.append(f"missing optional table {name}.csv")
        return None
    return pd.read_csv(path, **kw)


def load() -> SimpleNamespace:
    D = SimpleNamespace()
    D.ys = C.read_tidy("grd_year_summary")
    D.depth = C.read_tidy("grd_coding_depth_year", dtype={"depth_bin": str})
    D.agesex = C.read_tidy("grd_age_sex_year")
    D.hosp = C.read_tidy("grd_hospital_year")
    D.panel = C.read_tidy("grd_fixed_panel_hospitals")
    D.sub = C.read_tidy("grd_subcode_year")
    D.cov = C.read_tidy("coverage_layers_year")
    D.rem20 = C.read_tidy("rem20_panel")
    D.rem = C.read_tidy("rem_pathway_annual", dtype={"code": str})
    D.ine = C.read_tidy("ine_population_region_national_year_age_sex")
    D.rem_est = C.read_tidy("rem_establishment_year", dtype={"code": str}, low_memory=False)
    D.states = rem_cell_states(D.rem_est)
    deis = C.read_tidy("deis_year_summary")
    D.deis_masked = int(deis[deis.variant == "con_rett"].discharges_suppressed.sum())
    D.heff = optional_tidy("hospital_effects")
    D.models = optional_tidy("models_summary")
    return D


def poisson_rate(count, denom, per=PER):
    count = np.asarray(count, dtype=float)
    denom = np.asarray(denom, dtype=float)
    lo, hi = C.poisson_limits(count)
    with np.errstate(divide="ignore", invalid="ignore"):
        return per * count / denom, per * np.asarray(lo) / denom, per * np.asarray(hi) / denom


def ratio_ci(a, b, alpha=0.05):
    """Razón a/b de dos conteos Poisson vía Wilson sobre p = a/(a+b)."""
    n = a + b
    if n == 0 or b == 0:
        return np.nan, np.nan, np.nan
    p, lo, hi = C.wilson(a, n, alpha)
    return a / b, lo / (1 - lo) if lo < 1 else np.nan, hi / (1 - hi) if hi < 1 else np.nan


def tick_fmt(lang: str, dec: int = 0):
    from matplotlib.ticker import FuncFormatter
    return FuncFormatter(lambda v, p: num(v, dec, lang))


def fmt_axis(ax, lang, axis="y", dec=0):
    f = tick_fmt(lang, dec)
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(f)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(f)


def log_axis_fmt(ax, lang, axis="y"):
    from matplotlib.ticker import NullFormatter, LogLocator, FuncFormatter
    f = FuncFormatter(lambda v, p: num(v, 0 if v >= 1 else (1 if v >= 0.1 else 2), lang))
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0), numticks=12))
    a.set_major_formatter(f)
    a.set_minor_formatter(NullFormatter())


def context(ax, lang, law=True, law_y=0.97, pandemic_label=True, pandemic_y=0.97, law_ha="left", fs=7, plate=False, law_label=True):
    """Contexto común: sombreado 2020–21 y línea de la Ley 21.545.

    En las láminas verticales el sombreado y la línea punteada se rotulan una sola vez por lámina (el pie explica que
    significan lo mismo en todos los paneles): repetir ambos rótulos en seis celdas de 60 mm los volvía ilegibles.
    """
    C.shade_years(ax, PANDEMIC)
    if pandemic_label:
        ax.text(2020.5, pandemic_y, tr("pandemic_plate" if plate else "pandemic", lang), transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=fs, color="#555555", linespacing=1.15)
    if law:
        ax.axvline(LAW_X, color="#444444", ls=":", lw=1.0, zorder=1)
        if law_label:
            ax.text(LAW_X + (0.06 if law_ha == "left" else -0.06), law_y, tr("law_plate" if plate else "law", lang),
                    transform=ax.get_xaxis_transform(), ha=law_ha, va="top", fontsize=fs, color="#444444", linespacing=1.15)


_ABBR = [("Complejo Hospitalario ", "C.H. "), ("Complejo Asistencial ", "C.A. "), ("Hospital Clínico Metropolitano ", "H.C.M. "),
         ("Hospital Clínico Regional ", "H.C.R. "), ("Hospital Clínico de Niños ", "H. Niños "), ("Hospital de Niños ", "H. Niños "),
         ("Hospital Clínico ", "H.C. "), ("Hospital Provincial ", "H. Prov. "), ("Hospital Regional ", "H. Reg. "), ("Hospital Base ", "H. Base "),
         ("Hospital de Urgencia Asistencia Pública ", "H.U.A.P. "), ("Hospital Intercultural ", "H. Interc. "), ("Hospital ", "H. "),
         ("Instituto Nacional de Enfermedades Respiratorias y Cirugía Torácica", "Inst. Nac. Enf. Respiratorias"),
         ("Instituto ", "Inst. "), ("Doctor ", "Dr. "), ("Doctora ", "Dra. "), ("Monseñor ", "Mons. "), ("Presidente ", "Pdte. ")]


def abbreviate_hospital(name: str, max_core: int = 26) -> str:
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
# F1 · Fuentes, unidades y cobertura
# ===========================================================================
REM_MODULES = ["A03", "A05", "A27", "A28", "P2", "P6"]


def rem_cell_states(est: pd.DataFrame) -> pd.DataFrame:
    """Estados de la celda REM por módulo y año (unidad: celda establecimiento × periodo × código).

    Rejilla potencial = establecimientos que presentaron al menos una fila del módulo en el año × periodos de reporte
    del año (12 meses en la Serie A; junio y diciembre en la Serie P) × códigos del módulo vigentes ese año.
    Tres estados excluyentes: valor informado (celda con número > 0), cero explícito (celda con un 0 escrito) y
    no informado (no hay fila para esa combinación, o la fila existe con la celda en blanco). Las celdas en blanco
    dentro de filas presentes y las filas duplicadas exactas se cuentan aparte porque el pipeline ya las registra.
    """
    rows = []
    for (mod, year), g in est.groupby(["module", "year"], sort=True):
        series = str(g.series.iloc[0])
        periods = 12 if series == "A" else 2          # Serie P sólo informa junio y diciembre
        n_est = int(g.IdEstablecimiento.nunique())
        n_codes = int(g.code.astype(str).nunique())
        cells = n_est * periods * n_codes
        value, zero, empty = int(g.months_value.sum()), int(g.months_zero.sum()), int(g.months_empty.sum())
        rows.append(dict(module=str(mod), year=int(year), series=series, n_establishments=n_est, n_codes=n_codes,
                         periods=periods, cells=cells, rows_present=int(g.n_rows.sum()), value=value, zero=zero,
                         empty_cells=empty, not_reported=cells - value - zero,
                         duplicates=int(g.n_exact_duplicate_rows.sum())))
    d = pd.DataFrame(rows)
    for col in ("value", "zero", "not_reported"):
        d[f"pct_{col}"] = 100.0 * d[col] / d.cells
    return d.sort_values(["module", "year"]).reset_index(drop=True)


def _cell_states(ax, D, lang):
    """F1a — completitud del reporte REM: los TRES estados de la celda, en una barra apilada por celda.

    Unidad: la celda establecimiento × periodo × código. Cada celda de la rejilla (módulo × año) lleva una barra
    apilada al 100 % con los tres estados excluyentes —valor informado, cero explícito y no informado—, de modo que
    la comparación se lee de un vistazo y la escala abarca por construcción todo el recorrido de los datos (0–100 %).
    Sustituye al mapa de calor anterior, cuyo color iba de 60 a 100 % (más de un tercio de la rejilla quedaba pegada
    al tono más pálido) y cuyas dos cifras por celda, con su recuadro blanco, tapaban el color que daban a leer.
    Sobre cada barra, en su propia banda, va el porcentaje con valor informado; el cero explícito nunca llega al 1,4 %
    de las celdas, así que su segmento se dibuja con un ancho mínimo visible y su máximo se declara en la nota.
    Fila inferior: filas establecimiento × mes presentes en los archivos, en miles.
    """
    from matplotlib.patches import Rectangle
    st = D.states
    years = list(YEARS_REM)
    mods = [m for m in REM_MODULES if m in set(st.module)]
    nx, ny = len(years), len(mods)
    val = st.pivot_table(index="module", columns="year", values="pct_value").reindex(index=mods, columns=years)
    zer = st.pivot_table(index="module", columns="year", values="pct_zero").reindex(index=mods, columns=years)
    rws = st.pivot_table(index="module", columns="year", values="rows_present", aggfunc="sum").reindex(index=mods, columns=years)

    C_VAL, C_ZERO, C_NR = OKABE[0], OKABE[1], "#dcdcdc"
    BW, BH = 0.90, 0.30              # ancho y alto de la barra dentro de la celda (unidades de la rejilla)
    ZMIN = 0.05                      # ancho mínimo dibujado del segmento de cero explícito (fracción de la barra)
    y_num, y_bar = -0.30, 0.02       # bandas de la fila: la cifra arriba, la barra debajo; nunca se solapan

    ax.set_axis_off()
    # Canalón izquierdo justo para el rótulo del módulo: cada columna de la rejilla mide 141 pt / 7,7 u en
    # español, y una cifra de cuatro caracteres a 6 pt mide 14,8 pt. Con el canalón anterior (1,4 u más
    # ancho) las cifras de dos columnas contiguas se tocaban en español.
    x_lo, x_hi = -1.10, nx - 0.42
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(ny + 3.05, -1.35)    # bajo la rejilla: fila de filas presentes, leyenda de estados y nota
    for i in range(ny):
        ax.text(-0.58, i + (y_num + y_bar + BH / 2) / 2, mods[i], ha="right", va="center",
                fontsize=FS_MIN + 0.5, fontweight="bold", color="#222222")
        for j in range(nx):
            v, z = val.iloc[i, j], zer.iloc[i, j]
            x_left, y_top = j - BW / 2, i + y_bar
            if not np.isfinite(v):
                ax.add_patch(Rectangle((x_left, y_top), BW, BH, fc="#f7f7f7", ec="#bdbdbd", lw=0.4, hatch="///"))
                continue
            f_val = max(0.0, float(v)) / 100.0
            f_zer = 0.0 if not np.isfinite(z) or z <= 0 else max(ZMIN, float(z) / 100.0)
            f_nr = max(0.0, 1.0 - f_val - f_zer)
            x = x_left
            for frac, colr in ((f_val, C_VAL), (f_zer, C_ZERO), (f_nr, C_NR)):
                if frac <= 0:
                    continue
                ax.add_patch(Rectangle((x, y_top), BW * frac, BH, fc=colr, ec="none"))
                x += BW * frac
            ax.add_patch(Rectangle((x_left, y_top), BW, BH, fc="none", ec="white", lw=0.6))
            t = ax.text(j, i + y_num, num(v, 1, lang), ha="center", va="center",
                        fontsize=FS_MIN, fontweight="bold", color="#111111")
            t.set_bbox(dict(facecolor="none", edgecolor="none", pad=0.0))   # sin halo: la cifra va en su banda
    for j, y in enumerate(years):
        ax.text(j, -0.85, str(y), ha="center", va="center", fontsize=FS_MIN, color="#333333")

    # fila inferior: filas establecimiento × mes presentes en los archivos (miles), por año
    yrow = ny + 0.05
    ax.plot([-0.5, nx - 0.5], [yrow - 0.40, yrow - 0.40], color="#999999", lw=0.5)
    ax.text(-0.58, yrow, tr("f1_states_rows", lang), ha="right", va="center", fontsize=FS_MIN,
            color="#333333", linespacing=1.15)
    for j, y in enumerate(years):
        ax.text(j, yrow, num(rws[y].sum() / 1000.0, 1, lang), ha="center", va="center", fontsize=FS_MIN, color="#333333")

    # leyenda de los tres estados: tres muestras en una fila, dibujadas dentro del eje (no es una leyenda
    # de matplotlib, de modo que no puede caer sobre ningún dato ni gobernar el reparto del lienzo)
    # El ancho del eje lo decide el reparto del lienzo (la columna derecha necesita sitio para dos rótulos
    # de eje), de modo que la fila de la leyenda y la nota se colocan en coordenadas de EJE: se reparten
    # con el ancho real del panel y no se salen de la celda ni se montan unas sobre otras.
    def frac(y_data):
        lo, hi = ax.get_ylim()
        return (y_data - lo) / (hi - lo)

    # Dos filas de muestras (2 + 1): en español las tres entradas en una sola fila no caben en 141 pt y la
    # muestra del segundo estado se imprimía sobre el texto del primero.
    for f0, y_data, (colr, key) in ((0.015, ny + 0.80, (C_VAL, "f1_states_value")),
                                    (0.520, ny + 0.80, (C_ZERO, "f1_states_zero")),
                                    (0.015, ny + 1.35, (C_NR, "f1_states_nr"))):
        y_key = frac(y_data)
        h_key = frac(y_data - 0.26) - y_key
        ax.add_patch(Rectangle((f0, y_key), 0.050, h_key, fc=colr, ec="#888888", lw=0.35,
                               transform=ax.transAxes, clip_on=False))
        ax.text(f0 + 0.068, y_key + h_key / 2, tr(key, lang), transform=ax.transAxes, ha="left", va="center",
                fontsize=FS_MIN, color="#333333")
    # Una sola nota: dos bloques de texto sueltos se imprimían uno sobre otro en cuanto el idioma cambiaba
    # el número de líneas. El convenio de dibujo de la barra y el techo del cero explícito van en el pie.
    ax.text(0.0, frac(ny + 1.80), tr("f1_states_deis", lang).format(b=num(int(st.empty_cells.sum()), 0, lang),
                                                                    d=num(int(st.duplicates.sum()), 0, lang),
                                                                    n=num(D.deis_masked, 0, lang)),
            transform=ax.transAxes, ha="left", va="top", fontsize=FS_MIN, color="#333333", linespacing=1.30)
    # Este panel es un esquema compuesto a mano: cada cifra, cada muestra de la leyenda y cada nota están
    # puestas en una coordenada de dato calculada aquí, y la rejilla es lo que da sentido a cada una.
    # El motor de descongestión resuelve colisiones moviendo texto, que es justo lo que aquí no se puede
    # hacer: movida una cifra media fila, deja de pertenecer a su celda. Se marca el panel entero como
    # inamovible.
    for t in ax.texts:
        t.set_gid(C.PLATE_KEEP)


def _rem_estab_series(rem: pd.DataFrame):
    """Establecimientos reportantes por módulo/era: máximo entre los códigos de la era (sin cruzar quiebres)."""
    def by_codes(codes, years, measure="annual_sum"):
        d = rem[(rem.code.isin(codes)) & (rem.measure == measure) & (rem.variant == "single_code") & (rem.year.isin(years))]
        g = d.groupby("year").n_reporting_establishments.max()
        return g.reindex(years)
    return [
        ("f1_a03_legacy", by_codes(["03500406", "03500407"], [2019, 2020, 2021, 2022]), OKABE[0], "o", "-"),
        ("f1_a03_2023", by_codes(list(CFG.A03_2023_2024.values()), [2023, 2024]), OKABE[0], "s", "-"),
        ("f1_a03_3159", by_codes(list(CFG.A03_2024_31_59.values()), [2024]), OKABE[0], "^", "-"),
        ("f1_a03_2025", by_codes(list(CFG.A03_2025.values()), [2025]), OKABE[0], "D", "-"),
        ("f1_a05_broad", by_codes([CFG.A05_BROAD_PRE2021["entry"]], [2019, 2020]), OKABE[1], "o", "--"),
        ("f1_a05_autism", by_codes([CFG.STRICT["a05_entry"]], [2021, 2022, 2023, 2024, 2025]), OKABE[1], "o", "-"),
        ("f1_a27", by_codes(list(CFG.A27.values()), [2023, 2024, 2025]), OKABE[2], "o", "-"),
        ("f1_a28", by_codes(list(CFG.A28.values()), [2023, 2024, 2025]), OKABE[3], "o", "-"),
        ("f1_p2", by_codes([CFG.P2_TEA], YEARS_REM, "december_stock"), "#000000", "o", "-"),
        ("f1_p6_broad", by_codes(list(CFG.P6_BROAD_PRE2021.values()), [2019, 2020], "december_stock"), OKABE[5], "o", "--"),
        ("f1_p6_autism", by_codes([CFG.STRICT["p6_primary"], CFG.STRICT["p6_specialty"]], [2021, 2022, 2023, 2024, 2025], "december_stock"), OKABE[5], "o", "-"),
    ]


BREAKS = [
    # (fuente, año_inicio, año_fin, tipo, [(año, clase, {es, en}, posición_del_rótulo)])
    ("GRD", 2019, 2024, "flow", [(2021, "panel", {"es": "nuevo formato de ID; sin enlace 2020/21", "en": "new ID format; no 2020/21 linkage"}, "below"),
                                 (2023, "panel", {"es": "68 hospitales", "en": "68 hospitals"}, "above"), (2024, "panel", {"es": "72 hospitales", "en": "72 hospitals"}, "below")]),
    ("DEIS", 2019, 2024, "flow", [(2019, "def", {"es": "solo DIAG1; DIAG2 nunca contiene F84", "en": "DIAG1 only; DIAG2 never contains F84"}, "below")]),
    ("REM-20", 2019, 2025, "activity", [(2019, "panel", {"es": "panel de 188 con 12 meses cada año", "en": "188-panel with 12 months every year"}, "below")]),
    ("REM A03", 2019, 2025, "flow", [(2023, "def", {"es": "familia 09600212–19", "en": "family 09600212–19"}, "above"),
                                     (2024, "def", {"es": "códigos 31–59 meses", "en": "31–59-month codes"}, "below"), (2025, "def", {"es": "rediseño 03710013–21", "en": "redesign 03710013–21"}, "above")]),
    ("REM A27", 2023, 2025, "flow", [(2023, "start", {"es": "consejería y referencia asistida M-CHAT-R/F", "en": "M-CHAT-R/F counselling and assisted referral"}, "below")]),
    ("REM A05", 2019, 2025, "flow", [(2021, "def", {"es": "TGD amplio → autismo + categorías", "en": "broad PDD → autism + categories"}, "above_left")]),
    ("REM A28", 2023, 2025, "flow", [(2023, "start", {"es": "ingresos por TEA a rehabilitación", "en": "ASD entries to rehabilitation"}, "above")]),
    ("REM P2", 2019, 2025, "stock", [(2023, "def", {"es": "total NANEAS (P2501878) desde dic 2023", "en": "NANEAS total (P2501878) from Dec 2023"}, "above")]),
    ("REM P6", 2019, 2025, "stock", [(2021, "def", {"es": "TGD amplio → autismo", "en": "broad PDD → autism"}, "above")]),
    ("FONASA", 2019, 2025, "stock", [(2021, "panel", {"es": "esquema", "en": "schema"}, "above"), (2023, "panel", {"es": "esquema; tramos 10 años", "en": "schema; 10-year bands"}, "below"),
                                     (2024, "panel", {"es": "esquema", "en": "schema"}, "above"), (2025, "panel", {"es": "esquema", "en": "schema"}, "below")]),
    ("APS", 2019, 2025, "stock", [(2024, "panel", {"es": "grupos de edad y nombres de variables", "en": "age bands and variable names"}, "below")]),
    ("ISAPRE", 2019, 2025, "stock", [(2021, "panel", {"es": ".xlsx; edades quinquenales", "en": ".xlsx; five-year ages"}, "above")]),
    ("INE", 2019, 2025, "stock", [(2024, "panel", {"es": "Censo 2024 / base 2024 (sensibilidad)", "en": "Census 2024 / base 2024 (sensitivity)"}, "above")]),
    ("ENDIDE", 2022, 2022, "survey", [(2022, "start", {"es": "transversal, diseño complejo", "en": "cross-sectional, complex design"}, "above")]),
    ("ENCAVI", 2023, 2024, "survey", [(2023, "start", {"es": "transversal 2023–24", "en": "cross-sectional 2023–24"}, "above")]),
    ("PIE/SINACES", 2019, 2025, "education", [(2024, "panel", {"es": "fuente SINACES (Apuntes 60 hasta 2023)", "en": "SINACES source (Apuntes 60 to 2023)"}, "above")]),
    ("JUNAEB", 2019, 2025, "education", [(2024, "def", {"es": "1º medio no estimable", "en": "1º medio not estimable"}, "above")]),
]


def _timeline(ax, lang):
    """F1f — cobertura y quiebres por fuente, girada para la celda vertical: fuentes en el eje x, años en el eje y.

    La versión apaisada ponía las fuentes en filas y el año en el eje x, con un rótulo sobre cada marcador; a 180 mm de
    ancho esos rótulos eran ilegibles. Aquí cada fuente es una columna, cada año una fila, y el texto de cada quiebre se
    conserva íntegro en la tabla de quiebres de definición (S_definition_breaks.csv), que este mismo módulo escribe.
    """
    from matplotlib.lines import Line2D
    face = {"flow": OKABE[0], "stock": OKABE[1], "activity": "#777777", "survey": OKABE[2], "education": OKABE[3]}
    marker = {"def": ("D", "#000000"), "panel": ("s", "#555555"), "start": ("^", "#000000")}
    n = len(BREAKS)
    ax.axhspan(PANDEMIC[0] - 0.5, PANDEMIC[-1] + 0.5, color="grey", alpha=0.12, zorder=0)
    for i, (src, y0, y1, kind, brks) in enumerate(BREAKS):
        ax.bar(i, y1 - y0 + 0.76, bottom=y0 - 0.38, width=0.62, color=face[kind], alpha=0.38, zorder=1)
        for (yr, cls, lab, pos) in brks:
            mk, colr = marker[cls]
            ax.scatter(i, yr, marker=mk, s=13, color=colr, zorder=4, edgecolor="white", linewidth=0.4)
    ax.set_xticks(range(n)); ax.set_xticklabels([b[0] for b in BREAKS], fontsize=FS_MIN + 0.5, rotation=90)
    ax.set_xlim(-0.75, n - 0.25)
    ax.set_ylim(2018.45, 2025.55); ax.set_yticks(YEARS_REM)
    ax.set_yticklabels([str(y) for y in YEARS_REM], fontsize=FS_MIN + 0.5)
    ax.set_ylabel(tr("f1_tl_axis", lang))
    ax.axhline(CFG.LAW_YEAR - 0.30, color="#444444", ls=":", lw=1.0, zorder=2)
    handles = [Line2D([0], [0], marker=marker[k][0], color="w", markerfacecolor=marker[k][1], markersize=3.6, label=tr(f"f1_tl_{k}", lang))
               for k in ("def", "panel", "start")]
    leg = ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.30), fontsize=FS_MIN, ncol=1, frameon=False,
                    handlelength=1.0, borderaxespad=0.1, labelspacing=0.2, title=tr("f1_tl_note", lang), title_fontsize=FS_MIN)
    leg.get_title().set_color("#555555")
    ax.grid(axis="x", visible=False)


def fig1(D, variant, lang, fdir):
    """Lámina vertical de 180 × 245 mm: seis paneles (a–f) en tres filas por dos columnas."""
    plt, sns = plate_style()
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas

    # a — completitud del reporte REM y los tres estados de una celda (sustituye al esquema de fuentes: la Figura 1 ya lo cubre)
    a = ax[0, 0]
    _cell_states(a, D, lang); panel_head(a, "a", tr("f1_title_a", lang))

    # b — capas de cobertura
    b = ax[0, 1]
    cv = D.cov.sort_values("year")
    ends = []
    for col, key, colr, mk in [("ine_population_base2017_30jun", "f1_ine", "#000000", "o"), ("fonasa_beneficiaries_dec", "f1_fonasa", OKABE[0], "s"),
                               ("aps_enrolled_dec", "f1_aps", OKABE[2], "^"), ("isapre_beneficiaries_dec", "f1_isapre", OKABE[1], "D")]:
        b.plot(cv.year, cv[col] / 1e6, marker=mk, lw=1.4, color=colr, label=tr(key, lang), markersize=3.2)
        ends.append((float(cv.year.iloc[-1]), float(cv[col].iloc[-1]) / 1e6, colr))
    # El techo del eje reserva la banda superior para la leyenda: las series llegan a 20,2 millones y la
    # leyenda ocupa de 32 a ~24, de modo que no tapa ninguna de ellas.
    b.set_ylim(0, 32); b.set_yticks([0, 5, 10, 15, 20, 25]); b.set_xticks(YEARS_REM)
    b.set_xticklabels([str(y) for y in YEARS_REM], fontsize=FS_MIN + 0.5); b.set_xlabel(tr("year", lang))
    # Margen derecho REAL para los rótulos de fin de serie: con el margen anterior, 17,1 y 15,8 se
    # imprimían sobre el espinazo derecho, contra las marcas del eje secundario.
    b.set_ylabel(tr("millions", lang)); b.set_xlim(YEARS_REM[0] - 0.35, YEARS_REM[-1] + 1.85)
    fmt_axis(b, lang, "y", 0)
    b2 = b.twinx(); b2.spines["right"].set_visible(True); b2.grid(False)
    b2.plot(cv.year, 100 * cv.share_fonasa_plus_isapre_ine, ls="--", marker="x", color=COL["grey"], lw=1.1, markersize=3.2, label=tr("f1_share", lang))
    b2.set_ylim(80, 122); b2.set_yticks([80, 85, 90, 95, 100]); b2.set_ylabel(tr("f1_share_axis", lang)); fmt_axis(b2, lang, "y", 0)
    b2.tick_params(labelsize=FS_TICK)
    context(b, lang, law_y=0.30, pandemic_y=0.30, fs=FS_MIN, plate=True)
    h1, l1 = b.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
    # La leyenda tenía cinco entradas largas y una nota de tres líneas por título: ocupaba media anchura del
    # panel, tapaba la serie del INE y la línea punteada de la Ley 21.545 se imprimía a través de su texto.
    # Ahora: rótulos cortos (el nombre completo de cada capa está en el pie), recuadro OPACO —de modo que
    # ninguna marca de contexto atraviese el texto— y sitio reservado en la banda superior del panel.
    leg = b.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=FS_MIN, ncol=1, handlelength=1.2,
                   handletextpad=0.4, borderpad=0.25, labelspacing=0.28, borderaxespad=0.3,
                   frameon=True, framealpha=1.0, edgecolor="#cccccc", facecolor="white")
    leg.set_zorder(8); leg.set_in_layout(False)
    # Los rótulos de fin de serie de FONASA (17,1) y APS (15,8) quedan a 1,3 millones uno de otro: colocados
    # sin más, el descendente de la coma del primero desaparecía bajo el segundo y «17,1» se leía «17.1».
    # Se separan al guardar, con la composición ya congelada, dejando aire para el descendente.
    _end_anns = [C.plate_value_label(b, x_end, y_end, num(y_end, 1, lang), fontsize=FS_MIN + 0.5, color=colr,
                                     fontweight="bold", ha="left", va="center", step_pt=2.5,
                                     prefer=((1, 0), (1, 1), (1, -1)))
                 for x_end, y_end, colr in ends]
    fig._plate_spread = [(b, _end_anns)]
    panel_head(b, "b", tr("f1_title_b", lang))

    # c — establecimientos reportantes REM por módulo y era
    c = ax[1, 0]
    for key, ser, colr, mk, ls in _rem_estab_series(D.rem):
        ser = ser.dropna()
        if not len(ser):
            WARNINGS.append(f"F1c: no rows for {key}")
            continue
        c.plot(ser.index, ser.values, marker=mk, ls=ls, lw=1.2, color=colr, markersize=3.0, label=tr(f"f1_s_{key[3:]}", lang))
    for xb in (2020.5, 2022.5, 2024.5):
        c.axvline(xb, color="#999999", ls=(0, (2, 2)), lw=0.7, zorder=0)
    c.set_yscale("log"); log_axis_fmt(c, lang); c.set_ylim(50, 3000)
    c.set_xticks(YEARS_REM); c.set_xticklabels([str(y) for y in YEARS_REM], fontsize=FS_MIN + 0.5); c.set_xlabel(tr("year", lang))
    c.set_ylabel(tr("f1_estab_axis", lang)); c.margins(x=0.08)
    context(c, lang, law=True, pandemic_label=False, law_label=False, fs=FS_MIN, plate=True)
    # La nota de la era («máximo entre los códigos; ninguna línea cruza un quiebre») se imprimía sobre las
    # series P2 y P6, tapando hasta el 38 % de una de ellas; su texto está íntegro en el pie de la figura.
    c.legend(loc="upper center", bbox_to_anchor=(0.5, -0.155), fontsize=FS_MIN, ncol=2, columnspacing=0.6, handlelength=1.4, borderaxespad=0.1)
    panel_head(c, "c", tr("f1_title_c", lang))

    # d — hospitales GRD y episodios
    d = ax[1, 1]
    ys = D.ys[(D.ys.variant == "con_rett") & (D.ys.activity == "all") & (D.ys.position == "any")]
    obs = ys[ys.panel == "observed"].set_index("year").reindex(YEARS_GRD)
    fix = ys[ys.panel == "fixed65"].set_index("year").reindex(YEARS_GRD)
    x = np.array(YEARS_GRD)
    d.bar(x - 0.2, obs.hospitals_n, width=0.38, color=OKABE[0], label=tr("f1_hosp_obs", lang))
    d.bar(x + 0.2, fix.hospitals_n, width=0.38, color="#b0b0b0", label=tr("f1_hosp_fixed", lang))
    for xi, v, vf in zip(x, obs.hospitals_n, fix.hospitals_n):
        d.text(xi - 0.2, v / 2, num(v, 0, lang), ha="center", va="center", fontsize=FS_MIN, fontweight="bold", color="white", rotation=90)
        d.text(xi + 0.2, vf / 2, num(vf, 0, lang), ha="center", va="center", fontsize=FS_MIN, fontweight="bold", color="white", rotation=90)
    d.set_ylim(0, 165); d.set_xticks(YEARS_GRD); d.set_xticklabels([str(y) for y in YEARS_GRD], fontsize=FS_MIN + 0.5)
    d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("f1_hosp_axis", lang))
    d2 = d.twinx(); d2.spines["right"].set_visible(True); d2.grid(False)
    d2.plot(x, obs.n_episodes_total_same_panel_activity / 1e6, "o-", color="#000000", lw=1.3, markersize=3.2, label=tr("f1_epi_obs", lang))
    d2.plot(x, fix.n_episodes_total_same_panel_activity / 1e6, "s--", color="#555555", lw=1.1, markersize=3.0, label=tr("f1_epi_fixed", lang))
    d2.set_ylim(0, 1.85); d2.set_ylabel(tr("f1_epi_axis", lang)); fmt_axis(d2, lang, "y", 1); d2.tick_params(labelsize=FS_TICK)
    context(d, lang, pandemic_label=False, law_label=False, fs=FS_MIN, plate=True)
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels()
    leg = d.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=FS_MIN, ncol=1, handlelength=1.4,
                   frameon=True, framealpha=1.0, edgecolor="#cccccc", facecolor="white", borderpad=0.25)
    leg.set_zorder(8); leg.set_in_layout(False)
    panel_head(d, "d", tr("f1_title_d", lang))

    # e — REM-20: panel de 188 establecimientos y retención
    e = ax[2, 0]
    r20 = D.rem20.sort_values("year")
    x = r20.year.values
    e.bar(x - 0.2, r20.discharges_total / 1e3, width=0.38, color="#9ecae1", label=tr("f1_rem20_all", lang))
    e.bar(x + 0.2, r20.discharges_panel_188 / 1e3, width=0.38, color=OKABE[0], label=tr("f1_rem20_panel", lang))
    e.set_ylim(0, 2100); e.set_yticks([0, 500, 1000, 1500, 2000]); e.set_xticks(YEARS_REM)
    # El número de establecimientos reportantes iba girado 90° dentro de las barras y su texto cruzaba la
    # línea de retención del eje gemelo; ahora es la segunda línea de la marca de cada año, que es donde
    # pertenece (un dato por año) y donde no puede caer sobre ninguna serie.
    n_by_year = dict(zip(x, r20.establishments_reporting))
    e.set_xticklabels([f"{y}\n{num(n_by_year.get(y, np.nan), 0, lang)}" if y in n_by_year else str(y)
                       for y in YEARS_REM], fontsize=FS_MIN + 0.5)
    e.set_xlabel(f"{tr('year', lang)} · {tr('f1_rem20_n', lang)}")
    e.set_ylabel(tr("f1_rem20_axis", lang)); fmt_axis(e, lang, "y", 0)
    e2 = e.twinx(); e2.spines["right"].set_visible(True); e2.grid(False)
    e2.plot(x, 100 * r20.retention_discharges, "o-", color=OKABE[1], lw=1.3, markersize=3.2, label=tr("f1_rem20_ret", lang))
    for xi, v in zip(x, r20.retention_discharges):
        e2.text(xi, 100 * v + 0.10, num(100 * v, 1, lang), ha="center", fontsize=FS_MIN, color=OKABE[1])
    e2.set_ylim(95, 102.5); e2.set_yticks([96, 97, 98, 99, 100]); e2.set_ylabel(tr("f1_rem20_ret", lang))
    fmt_axis(e2, lang, "y", 0); e2.tick_params(labelsize=FS_TICK)
    context(e, lang, pandemic_label=False, law_label=False, fs=FS_MIN, plate=True)
    h1, l1 = e.get_legend_handles_labels(); h2, l2 = e2.get_legend_handles_labels()
    leg = e.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=FS_MIN, handlelength=1.4,
                   title=tr("f1_rem20_note", lang), title_fontsize=FS_MIN,
                   frameon=True, framealpha=1.0, edgecolor="#cccccc", facecolor="white", borderpad=0.25)
    leg.get_title().set_color("#555555"); leg.set_zorder(8); leg.set_in_layout(False)
    panel_head(e, "e", tr("f1_title_e", lang))

    # f — línea de tiempo de quiebres (sin rótulos por marcador: cada quiebre se describe en la tabla de quiebres)
    f = ax[2, 1]
    _timeline(f, lang); panel_head(f, "f", tr("f1_title_f", lang))

    path = save_plate(fig, fdir / "fig1_sources_coverage.png"); plt.close(fig)
    return path


# ===========================================================================
# F2 · Núcleo hospitalario GRD
# ===========================================================================
def _ys(D, variant, panel, activity, position):
    d = D.ys[(D.ys.variant == variant) & (D.ys.panel == panel) & (D.ys.activity == activity) & (D.ys.position == position)]
    return d.set_index("year").reindex(YEARS_GRD)


def _plot_rate(ax, d, color, label, ls="-", mk="o", band=True, lw=2.2):
    ax.plot(d.index, d.rate_per_100k_episodes, ls=ls, marker=mk, color=color, lw=lw, markersize=5.5, label=label,
            markerfacecolor=color if ls == "-" else "white")
    if band:
        ax.fill_between(d.index, d.rate_lo, d.rate_hi, color=color, alpha=0.13, lw=0)


def _pop_rates(D, variant, year, sex):
    """Tasas por 100.000 habitantes INE (nacional base 2017) por grupo de edad OMS con 45+ agrupado; numerador lugar de atención."""
    groups = [g for g in C.AGE_GROUPS if int(g.split("-")[0].replace("+", "")) < 45]
    num_ = D.agesex[(D.agesex.variant == variant) & (D.agesex.panel == "observed") & (D.agesex.position == "any") & (D.agesex.activity == "all")
                    & (D.agesex.year == year) & (D.agesex.sex == sex)].set_index("age_group").n_f84
    pop = D.ine[(D.ine.level == "national") & (D.ine.population_base == "base2017") & (D.ine.year == year) & (D.ine.sex == sex)].set_index("age_group").population
    older = [g for g in C.AGE_GROUPS if g not in groups]
    counts = [float(num_.get(g, 0)) for g in groups] + [float(sum(num_.get(g, 0) for g in older))]
    pops = [float(pop.get(g, np.nan)) for g in groups] + [float(sum(pop.get(g, 0) for g in older))]
    labels = groups + ["45+"]
    r, lo, hi = poisson_rate(counts, pops)
    return pd.DataFrame({"age_group": labels, "count": counts, "population": pops, "rate": r, "lo": lo, "hi": hi})


def _mf_ratio(D, variant):
    d = D.agesex[(D.agesex.variant == variant) & (D.agesex.panel == "observed") & (D.agesex.position == "any") & (D.agesex.activity == "all")]
    g = d.groupby(["year", "sex"]).n_f84.sum().unstack().reindex(YEARS_GRD)
    rows = []
    for y in YEARS_GRD:
        m, w = float(g.loc[y, "HOMBRE"]), float(g.loc[y, "MUJER"])
        r, lo, hi = ratio_ci(m, w)
        rows.append(dict(year=y, males=m, females=w, ratio=r, lo=lo, hi=hi))
    return pd.DataFrame(rows).set_index("year")


def fig2(D, variant, lang, fdir):
    """Lámina vertical de 180 × 245 mm: seis paneles (a–f) en tres filas por dos columnas."""
    plt, sns = plate_style()
    from matplotlib.lines import Line2D
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    first, last = YEARS_GRD[0], YEARS_GRD[-1]
    yrs = [str(y) for y in YEARS_GRD]

    # a — cualquier posición y principal, panel observado y fijo
    a = ax[0, 0]
    ao, af = _ys(D, variant, "observed", "all", "any"), _ys(D, variant, "fixed65", "all", "any")
    po, pf = _ys(D, variant, "observed", "all", "principal"), _ys(D, variant, "fixed65", "all", "principal")
    _plot_rate(a, ao, COL["any"], tr("f2_any_obs", lang))
    _plot_rate(a, af, COL["any"], tr("f2_any_fixed", lang), ls="--", mk="o", band=False, lw=1.0)
    _plot_rate(a, po, COL["principal"], tr("f2_pri_obs", lang), mk="s")
    _plot_rate(a, pf, COL["principal"], tr("f2_pri_fixed", lang), ls="--", mk="s", band=False, lw=1.0)
    for d_, colr in [(ao, COL["any"]), (po, COL["principal"])]:
        a.annotate(num(d_.rate_per_100k_episodes.iloc[-1], 0, lang), (last, d_.rate_per_100k_episodes.iloc[-1]), xytext=(3, 0),
                   textcoords="offset points", fontsize=FS_MIN + 0.5, color=colr, va="center", fontweight="bold")
    a.set_yscale("log"); log_axis_fmt(a, lang); a.set_ylim(8, 4000)
    a.set_xticks(YEARS_GRD); a.set_xticklabels(yrs, fontsize=FS_MIN + 0.5); a.set_xlabel(tr("year", lang))
    a.set_ylabel(tr("f2_rate_axis", lang)); a.margins(x=0.13)
    a.text(0.01, 0.085, tr("f2_hosp_n", lang), transform=a.transAxes, fontsize=FS_MIN, color="#333333", ha="left", va="center")
    for y in YEARS_GRD:
        a.text(y, 10.0, num(ao.loc[y, "hospitals_n"], 0, lang), fontsize=FS_MIN, ha="center", va="center", color="#333333")
    context(a, lang, law_y=0.40, pandemic_y=0.40, fs=FS_MIN, plate=True)
    a.legend(loc="upper left", fontsize=FS_MIN, handlelength=1.5)
    panel_head(a, "a", tr("f2_title_a", lang))

    # b — hospitalización estricta frente a CMA (panel observado)
    b = ax[0, 1]
    for act, key, colr, mk in [("all", "f2_act_all", COL["all"], "o"), ("hospitalisation", "f2_act_hosp", COL["hosp"], "s"), ("cma", "f2_act_cma", COL["cma"], "^")]:
        d_ = _ys(D, variant, "observed", act, "any")
        _plot_rate(b, d_, colr, tr(key, lang), mk=mk)
        b.annotate(num(d_.rate_per_100k_episodes.iloc[-1], 0, lang), (last, d_.rate_per_100k_episodes.iloc[-1]), xytext=(3, 0),
                   textcoords="offset points", fontsize=FS_MIN + 0.5, color=colr, va="center", fontweight="bold")
    b.set_xticks(YEARS_GRD); b.set_xticklabels(yrs, fontsize=FS_MIN + 0.5); b.set_xlabel(tr("year", lang))
    # Marcas de TRES cifras: en la columna derecha el hueco a la izquierda del panel da para la columna de
    # marcas y el rótulo girado, pero no si las marcas llevan cuatro cifras («1.000», «1.200»), y entonces la
    # guarda de recorte devolvía el rótulo dentro, encima de ellas.
    b.margins(x=0.13); b.set_ylim(0, 1050); b.set_yticks([0, 200, 400, 600, 800])
    b.set_ylabel(tr("f2_rate_axis_lin", lang))
    fmt_axis(b, lang, "y", 0)
    context(b, lang, pandemic_label=False, law_label=False, fs=FS_MIN, plate=True)
    plate_legend(b, loc="upper left", fs=FS_MIN, handlelength=1.5)
    panel_head(b, "b", tr("f2_title_b", lang))

    # c — profundidad diagnóstica
    c = ax[1, 0]
    bins = ["1", "2", "3", "4", "5", "6-7", "8-10", "11+"]
    dp = D.depth[(D.depth.variant == variant) & (D.depth.panel == "observed") & (D.depth.activity == "all")]
    xb = np.arange(len(bins))
    for off, y, colr in [(-0.2, first, "#9ecae1"), (0.2, last, OKABE[0])]:
        r = dp[dp.year == y].set_index("depth_bin").reindex(bins)
        c.bar(xb + off, r.rate_per_100k_episodes, width=0.38, color=colr, label=str(y))
        c.errorbar(xb + off, r.rate_per_100k_episodes, yerr=[r.rate_per_100k_episodes - r.rate_lo, r.rate_hi - r.rate_per_100k_episodes],
                   fmt="none", ecolor="#333333", elinewidth=0.6, capsize=1.2)
    c.set_xticks(xb); c.set_xticklabels(bins, fontsize=FS_MIN + 0.5); c.set_xlabel(tr("f2_depth_bin_axis", lang))
    c.set_ylabel(tr("f2_depth_rate_axis", lang))
    fmt_axis(c, lang, "y", 0); c.set_ylim(0, dp[dp.depth_bin.isin(bins)].rate_hi.max() * 2.35)
    c.legend(loc="upper left", fontsize=FS_MIN, handlelength=1.2, title=tr("f2_depth_year", lang), title_fontsize=FS_MIN)
    ci = c.inset_axes([0.36, 0.60, 0.60, 0.36])
    yo = _ys(D, variant, "observed", "all", "any")
    ci.plot(yo.index, yo.coding_depth_mean_all, "o-", color="#555555", lw=1.0, markersize=2.6, label=tr("f2_depth_all", lang))
    ci.plot(yo.index, yo.coding_depth_mean_f84, "s-", color=OKABE[1], lw=1.0, markersize=2.6, label=tr("f2_depth_f84", lang))
    C.shade_years(ci, PANDEMIC)
    ci.set_xticks(YEARS_GRD); ci.set_xticklabels([f"'{y % 100:02d}" for y in YEARS_GRD], fontsize=FS_MIN)
    ci.tick_params(labelsize=FS_MIN, length=1.6, pad=1.0)
    ci.set_title(tr("f2_depth_inset", lang), fontsize=FS_MIN + 0.8, fontweight="bold", pad=1.6)
    ci.legend(fontsize=FS_MIN, loc="lower right", handlelength=1.0, borderpad=0.2, labelspacing=0.15)
    ci.set_ylim(3.5, 7.6); fmt_axis(ci, lang, "y", 1); ci.grid(alpha=0.3)
    panel_head(c, "c", tr("f2_title_c", lang))

    # d — tasas poblacionales por edad y sexo, primer y último año
    d = ax[1, 1]
    series = [(first, "HOMBRE", "#9ecae1", "o", "--"), (last, "HOMBRE", COL["male"], "o", "-"), (first, "MUJER", "#f4b183", "s", "--"), (last, "MUJER", COL["female"], "s", "-")]
    xd, labels = None, []
    for y, sex, colr, mk, ls in series:
        r = _pop_rates(D, variant, y, sex)
        xd = np.arange(len(r))
        off = -0.1 if sex == "HOMBRE" else 0.1
        d.errorbar(xd + off, r.rate.replace(0, np.nan), yerr=[(r.rate - r.lo).clip(lower=0), (r.hi - r.rate)], fmt=mk + ls, color=colr,
                   lw=1.1, capsize=1.2, markersize=2.8, elinewidth=0.6,
                   label=f"{tr('males' if sex == 'HOMBRE' else 'females', lang)} {y}")
        labels = r.age_group.tolist()
    d.set_xticks(xd); d.set_xticklabels(labels, rotation=60, ha="right", fontsize=FS_MIN)
    # Techo del eje ajustado a los datos (la tasa más alta y su IC no pasan de 364 por 100.000): con el
    # techo anterior la columna de marcas llegaba a «2.000» y, en la columna derecha de la lámina, no dejaba
    # sitio para el rótulo girado, que acababa impreso sobre ella.
    d.set_yscale("log"); log_axis_fmt(d, lang); d.set_ylim(0.06, 700)
    d.tick_params(axis="y", labelsize=FS_MIN)   # columna de marcas más estrecha: sitio para el rótulo girado
    d.set_xlabel(tr("f2_age_axis", lang))
    # mismo motivo que en (b) y (f): el rótulo girado y su columna de marcas comparten un hueco estrecho
    d.set_ylabel(tr("f2_pop_axis", lang), fontsize=FS_MIN + 0.5)
    d.text(0.02, 0.03, tr("f2_pop_note", lang), transform=d.transAxes, fontsize=FS_MIN, color="#555555", va="bottom", linespacing=1.25)
    d.legend(loc="upper right", fontsize=FS_MIN, ncol=2, handlelength=1.4, columnspacing=0.7)
    panel_head(d, "d", tr("f2_title_d", lang))

    # e — hospitales ordenados por tasa, 2024: eje girado a vertical (el rango ordenado ocupa el alto de la celda)
    e = ax[2, 0]
    h = D.hosp[(D.hosp.variant == variant) & (D.hosp.year == last)].copy()
    r, lo, hi = poisson_rate(h.n_f84_any.values, h.n_episodes_total.values)
    h["rate"], h["lo"], h["hi"] = r, lo, hi
    h = h.sort_values("rate").reset_index(drop=True)
    cols = [COL["fixed"] if bool(v) else COL["new"] for v in h.in_fixed_panel]
    yr = np.arange(len(h))
    floor = max(1.0, np.nanmin(h.rate[h.rate > 0]) * 0.5)
    e.errorbar(h.rate.clip(lower=floor), yr, xerr=[(h.rate - h.lo).clip(lower=0), (h.hi - h.rate)], fmt="none", ecolor="#a5a5a5", elinewidth=0.5, zorder=1)
    e.scatter(h.rate.clip(lower=floor), yr, c=cols, s=7, zorder=3, edgecolor="white", linewidth=0.3)
    nat = PER * h.n_f84_any.sum() / h.n_episodes_total.sum()
    e.axvline(nat, color="#333333", ls="--", lw=0.9)
    # Márgenes reservados: la banda izquierda (~9 %) y la derecha (~20 %) del panel quedan SIN datos, para
    # alojar los rótulos de los ocho hospitales extremos. Los límites se fijan aquí porque las posiciones de
    # esos rótulos se calculan en coordenadas de dato a partir de ellos.
    from matplotlib.ticker import LogLocator
    x_lo, x_hi = floor * 0.42, float(h.hi.max()) * 6.5
    y_lo, y_hi = -2.5, len(h) + 0.5
    e.set_xscale("log"); log_axis_fmt(e, lang, axis="x"); e.set_xlim(x_lo, x_hi)
    e.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=8))
    e.set_ylim(y_lo, y_hi); e.set_yticks([])

    def fx(frac):                       # fracción del ancho del panel → coordenada de dato (eje logarítmico)
        return x_lo * (x_hi / x_lo) ** frac

    def fy(frac):
        return y_lo + frac * (y_hi - y_lo)

    # El rótulo de la tasa nacional iba girado 90° sobre las barras de error de media docena de hospitales;
    # ahora va horizontal, sobre su línea, en la banda superior del panel, que a esa altura no tiene datos.
    e.text(nat, 0.985, f"{tr('f2_cat_nat', lang)} = {num(nat, 0, lang)}", transform=e.get_xaxis_transform(),
           fontsize=FS_MIN, color="#333333", va="top", ha="center")
    # los extremos se numeran en la lámina y se nombran en el pie: ocho nombres de hospital no caben legibles en 62 mm
    n_top, n_bot = 5, 3
    extremes = []
    # Los cinco hospitales de mayor tasa están a menos de 1 mm entre sí en el eje vertical. El escalonado
    # anterior sumaba un desplazamiento fijo en puntos a anclas de altura distinta y dejaba «2» impreso sobre
    # «3» y varios rótulos sobre su propia barra de error. Ahora cada rótulo se escribe en el margen, con un
    # paso fijo del 7,5 % del alto del panel (≈ 11 pt), y una guía dibujada aparte lo une con su punto. La
    # guía va como línea de datos y no como flecha de `annotate`: la caja de una anotación con flecha incluye
    # la flecha, y ocho guías que salen del mismo sitio se «solapaban» entre sí para el verificador.
    for k, i in enumerate(range(len(h) - 1, len(h) - n_top - 1, -1)):
        y_lab = fy(0.975 - 0.075 * k)
        e.plot([h.hi.iloc[i], fx(0.885)], [yr[i], y_lab], color="#999999", lw=0.4, zorder=1, solid_capstyle="butt")
        e.text(fx(0.905), y_lab, str(k + 1), fontsize=FS_MIN, ha="left", va="center", color="#333333", fontweight="bold")
        extremes.append((str(k + 1), abbreviate_hospital(h.hospital_name.iloc[i], 34), float(h.rate.iloc[i])))
    for k, i in enumerate(range(n_bot)):
        tag = "xyz"[k]
        # los tres hospitales de menor tasa están igual de juntos: se abren hacia abajo, con su misma guía
        y_lab = fy(0.170 - 0.075 * k)
        e.plot([max(h.lo.iloc[i], floor), fx(0.092)], [yr[i], y_lab], color="#999999", lw=0.4, zorder=1, solid_capstyle="butt")
        e.text(fx(0.072), y_lab, tag, fontsize=FS_MIN, ha="right", va="center", color="#333333", fontweight="bold")
        extremes.append((tag, abbreviate_hospital(h.hospital_name.iloc[i], 34), float(h.rate.iloc[i])))
    n_fixed, n_new = int(h.in_fixed_panel.sum()), int((~h.in_fixed_panel.astype(bool)).sum())
    plate_legend(e, handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=COL["fixed"], markersize=3.6, label=tr("f2_cat_fixed", lang).replace("65", num(n_fixed, 0, lang))),
                             Line2D([0], [0], marker="o", color="w", markerfacecolor=COL["new"], markersize=3.6, label=tr("f2_cat_new", lang).replace("7", num(n_new, 0, lang)))],
                 loc="upper left", fs=FS_MIN, handlelength=1.0)
    e.set_ylabel(tr("f2_cat_rank", lang).replace("72", num(len(h), 0, lang)))
    e.set_xlabel(tr("f2_cat_axis", lang))
    e.tick_params(axis="x", labelsize=FS_MIN + 0.5)
    e.grid(axis="y", visible=False)
    panel_head(e, "e", tr("f2_title_e", lang))

    # f — personas dentro del año, episodios y razón H:M
    f = ax[2, 1]
    x = np.array(YEARS_GRD)
    # Conteos en MILES: con las cifras completas la columna de marcas medía seis caracteres («22.500») y en
    # la columna derecha no quedaba sitio para el rótulo girado, que la guarda de recorte devolvía encima de
    # ellas. Las cifras exactas están en la tabla de la lámina y en el pie.
    f.bar(x - 0.2, ao.n_episodes_f84 / 1e3, width=0.38, color="#9ecae1", label=tr("f2_episodes", lang))
    f.bar(x + 0.2, ao.persons_within_year / 1e3, width=0.38, color=OKABE[0], label=tr("f2_persons", lang))
    for xi, ne, npers in zip(x, ao.n_episodes_f84, ao.persons_within_year):
        f.text(xi, max(ne, npers) / 1e3 * 1.03, num(ne / npers, 2, lang), ha="center", fontsize=FS_MIN, color="#333333")
    f.set_ylim(0, ao.n_episodes_f84.max() / 1e3 * 2.5); f.set_xticks(YEARS_GRD); f.set_xticklabels(yrs, fontsize=FS_MIN + 0.5)
    f.set_xlabel(tr("year", lang)); fmt_axis(f, lang, "y", 0)
    f2 = f.twinx(); f2.spines["right"].set_visible(True); f2.grid(False)
    mf = _mf_ratio(D, variant)
    f2.errorbar(x, mf.ratio, yerr=[mf.ratio - mf.lo, mf.hi - mf.ratio], fmt="o-", color=OKABE[1], lw=1.2, capsize=1.6, markersize=3.0,
                elinewidth=0.6, label=tr("f2_mf", lang))
    f2.set_ylim(0, 6.6); f2.set_yticks([0, 1, 2, 3, 4, 5, 6]); f2.set_ylabel(tr("f2_mf_axis", lang))
    fmt_axis(f2, lang, "y", 1); f2.tick_params(labelsize=FS_TICK)
    # La nota («episodios por persona ↑; sin deduplicación entre años») se imprimía sobre la razón H:M y
    # sobre sus barras de error, tapando hasta el 28 % de la serie; su texto está íntegro en el pie.
    context(f, lang, pandemic_label=False, law_label=False, fs=FS_MIN, plate=True)
    h1, l1 = f.get_legend_handles_labels(); h2, l2 = f2.get_legend_handles_labels()
    plate_legend(f, h1 + h2, l1 + l2, loc="upper left", fs=FS_MIN, handlelength=1.4)
    f.set_ylabel(tr("f2_count_axis", lang))
    panel_head(f, "f", tr("f2_title_f", lang))

    path = save_plate(fig, fdir / "fig2_grd_core.png"); plt.close(fig)
    return path, dict(nat_rate_2024=nat, n_hosp_last=len(h), n_fixed=n_fixed, n_new=n_new, extremes=extremes)


# ===========================================================================
# S1 · Diferencias entre variantes
# ===========================================================================
def figS1(D, variant, lang, fdir):
    plt, sns = plate_style()
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    last = YEARS_GRD[-1]
    vl = {"con_rett": variant_label("con_rett", lang), "sin_rett": variant_label("sin_rett", lang)}

    a = ax[0, 0]
    for v, colr in [("con_rett", COL["con"]), ("sin_rett", COL["sin"])]:
        _plot_rate(a, _ys(D, v, "observed", "all", "any"), colr, vl[v], mk="o" if v == "con_rett" else "s")
    a.set_xticks(YEARS_GRD); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("f2_rate_axis_lin", lang)); fmt_axis(a, lang); a.set_ylim(0, None)
    context(a, lang, law_y=0.30, pandemic_y=0.62, plate=True, fs=FS_MIN + 0.3); plate_legend(a); panel_head(a, "a", tr("s1_title_a", lang))

    b = ax[0, 1]
    for v, colr in [("con_rett", COL["con"]), ("sin_rett", COL["sin"])]:
        _plot_rate(b, _ys(D, v, "observed", "all", "principal"), colr, vl[v], mk="o" if v == "con_rett" else "s")
    b.set_xticks(YEARS_GRD); b.set_xlabel(tr("year", lang)); b.set_ylabel(tr("f2_rate_axis_lin", lang)); fmt_axis(b, lang); b.set_ylim(0, None)
    context(b, lang, pandemic_label=False, law_label=False); plate_legend(b); panel_head(b, "b", tr("s1_title_b", lang))

    c = ax[1, 0]
    for act, key, mk in [("hospitalisation", "f2_act_hosp", "s"), ("cma", "f2_act_cma", "^")]:
        for v, colr, ls in [("con_rett", COL["con"], "-"), ("sin_rett", COL["sin"], "--")]:
            _plot_rate(c, _ys(D, v, "observed", act, "any"), colr, f"{tr(key, lang)} · {variant_short(v, lang)}", ls=ls, mk=mk, band=(v == "con_rett"))
    c.set_xticks(YEARS_GRD); c.set_xlabel(tr("year", lang)); c.set_ylabel(tr("f2_rate_axis_lin", lang)); fmt_axis(c, lang); c.set_ylim(0, None)
    context(c, lang, pandemic_label=False, law_label=False); plate_legend(c); panel_head(c, "c", tr("s1_title_c", lang))

    d = ax[1, 1]
    rett = D.sub[D.sub.subcode == "F842"].pivot_table(index="year", columns="position", values="n_episodes", aggfunc="sum").reindex(YEARS_GRD).fillna(0)
    x = np.array(YEARS_GRD)
    d.bar(x - 0.2, rett.get("any", 0), width=0.38, color=OKABE[4], label=tr("s1_rett_any", lang))
    d.bar(x + 0.2, rett.get("principal", 0), width=0.38, color=OKABE[1], label=tr("s1_rett_pri", lang))
    con_any = _ys(D, "con_rett", "observed", "all", "any").n_episodes_f84
    for xi, v_any in zip(x, rett.get("any", pd.Series(0, index=YEARS_GRD))):
        d.text(xi - 0.2, v_any + 2, pct_str(100 * v_any / con_any.loc[xi], lang, 1), ha="center", fontsize=7.5, color="#333333")
    d.set_xticks(YEARS_GRD); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("episodes", lang)); fmt_axis(d, lang); d.set_ylim(0, rett.get("any", pd.Series([1])).max() * 1.35)
    context(d, lang, pandemic_label=False, law_label=False)
    plate_legend(d, title=f"{tr('s1_rett_share', lang)} ↑", title_fontsize=FS_MIN + 0.2)
    panel_head(d, "d", tr("s1_title_d", lang))

    e = ax[2, 0]
    specs = [("s1_series_any", "all", "any", "rate_per_100k_episodes", OKABE[0], "o"), ("s1_series_pri", "all", "principal", "rate_per_100k_episodes", OKABE[1], "s"),
             ("s1_series_hosp", "hospitalisation", "any", "rate_per_100k_episodes", OKABE[2], "^"), ("s1_series_cma", "cma", "any", "rate_per_100k_episodes", OKABE[3], "D"),
             ("s1_series_persons", "all", "any", "persons_within_year", OKABE[4], "v")]
    for key, act, pos, col, colr, mk in specs:
        con, sin = _ys(D, "con_rett", "observed", act, pos)[col], _ys(D, "sin_rett", "observed", act, pos)[col]
        e.plot(YEARS_GRD, 100 * (con - sin) / sin, marker=mk, color=colr, lw=1.8, markersize=5, label=tr(key, lang))
    e.axhline(0, color="#888888", lw=1); e.set_xticks(YEARS_GRD); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("s1_rel_axis", lang)); fmt_axis(e, lang, "y", 1)
    e.set_ylim(0, None); context(e, lang, pandemic_label=False, law_label=False); plate_legend(e, loc="upper right"); panel_head(e, "e", tr("s1_title_e", lang))

    f = ax[2, 1]
    for v, colr, ls in [("con_rett", COL["con"], "-"), ("sin_rett", COL["sin"], "--")]:
        vs = variant_short(v, lang)
        _plot_rate(f, _ys(D, v, "fixed65", "all", "any"), colr, f"{tr('s1_fixed_any', lang)} · {vs}", ls=ls, mk="o", band=False)
        _plot_rate(f, _ys(D, v, "fixed65", "all", "principal"), colr, f"{tr('s1_fixed_pri', lang)} · {vs}", ls=ls, mk="s", band=False, lw=1.5)
    f.set_yscale("log"); log_axis_fmt(f, lang); f.set_ylim(8, 20000); f.set_xticks(YEARS_GRD); f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("f2_rate_axis", lang))
    f2 = f.twinx(); f2.spines["right"].set_visible(True); f2.grid(False)
    x = np.array(YEARS_GRD)
    f2.bar(x - 0.2, _ys(D, "con_rett", "observed", "all", "any").persons_within_year, width=0.38, color=COL["con"], alpha=0.25, label=f"{tr('s1_persons_bar', lang)} · {variant_short('con_rett', lang)}")
    f2.bar(x + 0.2, _ys(D, "sin_rett", "observed", "all", "any").persons_within_year, width=0.38, color=COL["sin"], alpha=0.25, label=f"{tr('s1_persons_bar', lang)} · {variant_short('sin_rett', lang)}")
    f2.set_ylim(0, _ys(D, "con_rett", "observed", "all", "any").persons_within_year.max() * 4.0); f2.set_ylabel(tr("s1_persons_axis", lang)); fmt_axis(f2, lang)
    context(f, lang, pandemic_label=False, law_label=False)
    h1, l1 = f.get_legend_handles_labels(); h2, l2 = f2.get_legend_handles_labels()
    plate_legend(f, h1 + h2, l1 + l2, loc="upper left"); panel_head(f, "f", tr("s1_title_f", lang))

    path = save_plate(fig, fdir / "figS1_grd_variants.png"); plt.close(fig)
    return path


# ===========================================================================
# S2 · Subcódigos F84 y posición
# ===========================================================================
SUBCODE_LABEL = {"F840": "F84.0", "F841": "F84.1", "F842": "F84.2", "F843": "F84.3", "F844": "F84.4", "F845": "F84.5", "F848": "F84.8", "F849": "F84.9"}


def figS2(D, variant, lang, fdir):
    plt, sns = plate_style()
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    subs = [s for s in CFG.VARIANTS[variant]["grd_subcodes"] if s in SUBCODE_LABEL]
    sub = D.sub[D.sub.subcode.isin(subs)]
    anyp = sub[sub.position == "any"].pivot_table(index="year", columns="subcode", values="n_episodes", aggfunc="sum").reindex(YEARS_GRD).reindex(columns=subs).fillna(0)
    prin = sub[sub.position == "principal"].pivot_table(index="year", columns="subcode", values="n_episodes", aggfunc="sum").reindex(YEARS_GRD).reindex(columns=subs).fillna(0)
    x = np.array(YEARS_GRD)
    palette = dict(zip(subs, OKABE[: len(subs)]))

    a = ax[0, 0]
    share = 100 * anyp.div(anyp.sum(axis=1), axis=0)
    bottom = np.zeros(len(x))
    for s in subs:
        a.bar(x, share[s], bottom=bottom, color=palette[s], width=0.7, label=SUBCODE_LABEL[s])
        bottom += share[s].values
    for xi, v in zip(x, share["F840"]):
        a.text(xi, v / 2, pct_str(v, lang, 0), ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    a.set_ylim(0, 100); a.set_xticks(YEARS_GRD); a.set_xlabel(tr("year", lang)); a.set_ylabel(tr("s2_share_axis", lang))
    a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, fontsize=FS_MIN + 0.3, frameon=False, columnspacing=0.8, handlelength=1.1); panel_head(a, "a", tr("s2_title_a", lang))

    b = ax[0, 1]
    for s in subs:
        b.plot(x, anyp[s].replace(0, np.nan), "o-", color=palette[s], lw=1.8, markersize=4.5, label=SUBCODE_LABEL[s])
    b.set_yscale("log"); log_axis_fmt(b, lang); b.set_ylim(0.5, 50000); b.set_xticks(YEARS_GRD); b.set_xlabel(tr("year", lang)); b.set_ylabel(tr("s2_count_axis", lang))
    context(b, lang, law_y=0.99, pandemic_y=0.99, plate=True, fs=FS_MIN + 0.3)
    plate_note(b, tr("s2_mentions_note", lang), x=0.02, y=0.06, ha="left", va="bottom", color="#555555")
    b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, fontsize=FS_MIN + 0.3, frameon=False, columnspacing=0.8, handlelength=1.1); panel_head(b, "b", tr("s2_title_b", lang))

    c = ax[1, 0]
    big = [s for s in subs if (anyp[s] >= 20).all()]
    for s in big:
        c.plot(x, 100 * prin[s] / anyp[s], "o-", color=palette[s], lw=1.8, markersize=4.5, label=SUBCODE_LABEL[s])
    c.plot(x, 100 * prin.sum(axis=1) / anyp.sum(axis=1), "k--", lw=2, label=tr("s2_family", lang))
    # Banda superior reservada para la leyenda de siete entradas: con el techo anterior (42 %) se dibujaba
    # sobre la serie de F84.1.
    c.set_ylim(0, 62); c.set_yticks([0, 10, 20, 30, 40]); c.set_xticks(YEARS_GRD)
    c.set_xlabel(tr("year", lang)); c.set_ylabel(tr("s2_pct_pri_axis", lang)); fmt_axis(c, lang, "y", 0)
    context(c, lang, pandemic_label=False, law_label=False); plate_legend(c, loc="upper right", ncol=2); panel_head(c, "c", tr("s2_title_c", lang))

    d = ax[1, 1]
    ys = D.ys[(D.ys.variant == variant) & (D.ys.panel == "observed") & (D.ys.activity == "all")]
    pos = ys.pivot_table(index="year", columns="position", values="n_episodes_f84").reindex(YEARS_GRD)
    bottom = np.zeros(len(x))
    for key, lab, colr in [("principal", "s2_pos_principal", OKABE[1]), ("principal_and_secondary", "s2_pos_both", OKABE[4]), ("secondary_only", "s2_pos_secondary", OKABE[0])]:
        if key in pos:
            d.bar(x, pos[key], bottom=bottom, color=colr, width=0.7, label=tr(lab, lang)); bottom += pos[key].values
    d.set_xticks(YEARS_GRD); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("episodes", lang)); fmt_axis(d, lang); d.set_ylim(0, pos["any"].max() * 1.3)
    d2 = d.twinx(); d2.spines["right"].set_visible(True); d2.grid(False)
    pct = 100 * pos["secondary_only"] / pos["any"]
    d2.plot(x, pct, "o-", color="#333333", lw=1.8, markersize=5, label=tr("s2_pct_sec", lang))
    for xi, v in zip(x, pct):
        d2.text(xi, v + 0.6, pct_str(v, lang, 1), ha="center", fontsize=7.5)
    d2.set_ylim(80, 100); d2.set_ylabel(tr("s2_pct_sec", lang)); fmt_axis(d2, lang)
    context(d, lang, pandemic_label=False, law_label=False)
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels()
    plate_legend(d, h1 + h2, l1 + l2, loc="upper left"); panel_head(d, "d", tr("s2_title_d", lang))

    e = ax[2, 0]
    _plot_rate(e, _ys(D, variant, "observed", "all", "any"), OKABE[0], f"{tr('s2_family', lang)}: {variant_label(variant, lang)}")
    _plot_rate(e, _ys(D, "strict_autism_f840", "observed", "all", "any"), COL["strict"], tr("strict_f840", lang), mk="s")
    e.set_xticks(YEARS_GRD); e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("f2_rate_axis_lin", lang)); fmt_axis(e, lang); e.set_ylim(0, None)
    context(e, lang, pandemic_label=False, law_label=False); plate_legend(e); panel_head(e, "e", tr("s2_title_e", lang))

    f = ax[2, 1]
    rett = D.sub[D.sub.subcode == "F842"].pivot_table(index="year", columns="position", values="n_episodes", aggfunc="sum").reindex(YEARS_GRD).fillna(0)
    f.bar(x - 0.2, rett.get("secondary", 0), width=0.38, color=OKABE[0], label=tr("s2_pos_secondary", lang))
    f.bar(x + 0.2, rett.get("principal", 0), width=0.38, color=OKABE[1], label=tr("s2_pos_principal", lang))
    f.set_xticks(YEARS_GRD); f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("episodes", lang)); fmt_axis(f, lang); f.set_ylim(0, rett.get("secondary", pd.Series([1])).max() * 1.4)
    context(f, lang, pandemic_label=False, law_label=False)
    plate_legend(f, title=tr("s2_rett_note_con" if variant == "con_rett" else "s2_rett_note_sin", lang), title_fontsize=FS_MIN + 0.2)
    panel_head(f, "f", tr("s2_title_f", lang))

    path = save_plate(fig, fdir / "figS2_grd_subcodes.png"); plt.close(fig)
    return path


# ===========================================================================
# S3 · Efectos por hospital
# ===========================================================================
def _dumbbell(ax, D, variant, lang, half: str | None = None, show_xlabel: bool = True):
    """Tasa 2019 frente a 2024 de cada hospital del panel fijo, un renglón por hospital.

    En la lámina vertical el panel fijo de 65 hospitales no cabe en una celda de 62 mm de alto: 65 renglones
    dejarían los nombres a 3,5 pt. La lista se parte por la mediana de la tasa de 2024 y cada mitad ocupa su
    propio panel (`half` = "top" o "bottom"), de modo que ningún hospital se pierde y los nombres se leen a
    6,2 pt. `half=None` conserva la lista completa para las llamadas heredadas.
    """
    first, last = YEARS_GRD[0], YEARS_GRD[-1]
    h = D.hosp[(D.hosp.variant == variant) & (D.hosp.in_fixed_panel.astype(bool)) & (D.hosp.year.isin([first, last]))]
    p = h.pivot_table(index=["COD_HOSPITAL", "hospital_name"], columns="year", values=["n_f84_any", "n_episodes_total"])
    r0 = PER * p[("n_f84_any", first)] / p[("n_episodes_total", first)]
    r1 = PER * p[("n_f84_any", last)] / p[("n_episodes_total", last)]
    full = pd.DataFrame({"name": [i[1] for i in p.index], "r0": r0.values, "r1": r1.values}).sort_values("r1").reset_index(drop=True)
    floor = max(1.0, np.nanmin(full.r0[full.r0 > 0]) * 0.6)
    corte = len(full) // 2
    df = full if half is None else (full.iloc[corte:] if half == "top" else full.iloc[:corte])
    df = df.reset_index(drop=True)
    yy = np.arange(len(df))
    for i, row in df.iterrows():
        x0 = row.r0 if row.r0 > 0 else floor
        ax.plot([x0, row.r1], [i, i], color="#bbbbbb", lw=1.6, zorder=1)
        ax.scatter(x0, i, s=13, color="#56B4E9" if row.r0 > 0 else "white", edgecolor="#56B4E9", zorder=3, marker="o" if row.r0 > 0 else "x", linewidth=0.9)
        ax.scatter(row.r1, i, s=13, color=OKABE[1], zorder=4, edgecolor="white", linewidth=0.4)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor="#56B4E9", markersize=4.5, label=str(first)),
               Line2D([0], [0], marker="o", color="w", markerfacecolor=OKABE[1], markersize=4.5, label=str(last))]
    if (df.r0 <= 0).any():
        handles.append(Line2D([0], [0], marker="x", color="#56B4E9", lw=0, markersize=4.5, label=tr("s3_zero", lang)))
    lg = ax.legend(handles=handles, loc="lower right", fontsize=FS_MIN + 0.2, framealpha=1.0, frameon=True,
                   edgecolor="#cccccc", facecolor="white", borderpad=0.25)
    lg.set_zorder(8); lg.set_in_layout(False)
    ax.set_yticks(yy); ax.set_yticklabels([abbreviate_hospital(n, 24) for n in df.name], fontsize=FS_MIN + 0.2)
    # Banda derecha reservada: con el margen anterior la leyenda se dibujaba encima de los renglones de la
    # parte baja de la lista y llegaba a tapar por completo cuatro de ellos.
    ax.set_xscale("log"); log_axis_fmt(ax, lang, "x"); ax.set_xlim(floor * 0.8, full.r1.max() * 6.0); ax.set_ylim(-1, len(df))
    if show_xlabel:
        ax.set_xlabel(tr("s3_rate_axis", lang))
    ax.grid(axis="y", visible=False)
    return df


def figS3(D, variant, lang, fdir):
    plt, sns = plate_style()
    from matplotlib.lines import Line2D
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    hv = None if D.heff is None else D.heff[D.heff.variant == variant].copy()
    has_effects = hv is not None and len(hv) and hv.rr_fixed_effects_none.notna().any()

    # a — efectos fijos RR
    a = ax[0, 0]
    if has_effects:
        fe = hv.dropna(subset=["rr_fixed_effects_none"]).sort_values("rr_fixed_effects_none").reset_index(drop=True)
        cols = [COL["fixed"] if bool(v) else COL["new"] for v in fe.in_fixed_panel]
        xr = np.arange(len(fe))
        a.errorbar(xr, fe.rr_fixed_effects_none, yerr=[fe.rr_fixed_effects_none - fe.rr_lo_fixed_effects_none, fe.rr_hi_fixed_effects_none - fe.rr_fixed_effects_none], fmt="none", ecolor="#999999", elinewidth=0.6, zorder=1)
        a.scatter(xr, fe.rr_fixed_effects_none, c=cols, s=12, zorder=3, edgecolor="white", linewidth=0.35)
        if fe.rr_fixed_effects_depth.notna().any():
            a.scatter(xr, fe.rr_fixed_effects_depth, marker="x", s=10, color="#555555", zorder=4, linewidth=0.7)
        a.axhline(1, color="#333333", ls="--", lw=0.9); a.set_yscale("log"); log_axis_fmt(a, lang)
        # banda superior reservada: la leyenda se dibujaba sobre el tercio alto de los intervalos
        top = float(np.nanmax(fe.rr_hi_fixed_effects_none)) if fe.rr_hi_fixed_effects_none.notna().any() else 1.0
        bot = float(np.nanmin(fe.rr_lo_fixed_effects_none)) if fe.rr_lo_fixed_effects_none.notna().any() else 0.1
        a.set_ylim(max(1e-3, bot * 0.75), top * 12.0)
        plate_legend(a, handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=COL["fixed"], markersize=4.5, label=tr("f2_cat_fixed", lang)),
                                 Line2D([0], [0], marker="o", color="w", markerfacecolor=COL["new"], markersize=4.5, label=tr("f2_cat_new", lang)),
                                 Line2D([0], [0], marker="x", color="#555555", lw=0, markersize=4.5, label=tr("s3_fe_depth", lang))],
                     loc="upper left", fs=FS_MIN + 0.2)
        a.set_xticks([]); a.set_xlabel(tr("s3_rank", lang)); a.set_ylabel(tr("s3_rr_axis", lang))
    else:
        a.text(0.5, 0.5, tr("s3_fallback", lang), ha="center", va="center", transform=a.transAxes, fontsize=FS_TICK, wrap=True); a.set_xticks([]); a.set_yticks([])
    panel_head(a, "a", tr("s3_title_a", lang))

    # b — contracción
    b = ax[0, 1]
    if has_effects and hv.effect_log_random_intercept_none.notna().any():
        z = hv.dropna(subset=["effect_log_random_intercept_none", "effect_log_fixed_effects_none"])
        b.scatter(z.effect_log_fixed_effects_none, z.effect_log_random_intercept_none, c=[COL["fixed"] if bool(v) else COL["new"] for v in z.in_fixed_panel], s=13, edgecolor="white", linewidth=0.35, zorder=3)
        lim = [min(z.effect_log_fixed_effects_none.min(), z.effect_log_random_intercept_none.min()) - 0.1, max(z.effect_log_fixed_effects_none.max(), z.effect_log_random_intercept_none.max()) + 0.1]
        b.plot(lim, lim, ls="--", color="#888888", lw=0.9, label=tr("s3_identity", lang))
        # banda superior libre: la nota de la DE se imprimía sobre la línea de identidad
        b.set_xlim(lim[0], lim[1]); b.set_ylim(lim[0], lim[1] + 0.45 * (lim[1] - lim[0]))
        if D.models is not None:
            sd_row = D.models[D.models.model_id == f"grd_hospital:{variant}:observed:any:ri_none:2019-2024:random_intercept"]
            if len(sd_row) and pd.notna(sd_row.iloc[0].re_sd):
                r = sd_row.iloc[0]
                b.text(0.03, 0.97, f"{tr('s3_sd', lang)} = {num(r.re_sd, 2, lang)}\n({num(r.re_sd_lo, 2, lang)}; {num(r.re_sd_hi, 2, lang)})",
                       transform=b.transAxes, fontsize=FS_MIN + 0.3, va="top", bbox=NOTE_BBOX)
        plate_legend(b, loc="lower right"); b.set_xlabel(tr("s3_fe_axis", lang)); b.set_ylabel(tr("s3_ri_axis", lang)); fmt_axis(b, lang, "both", 1)
    else:
        b.text(0.5, 0.5, tr("s3_fallback", lang), ha="center", va="center", transform=b.transAxes, fontsize=FS_TICK, wrap=True); b.set_xticks([]); b.set_yticks([])
    panel_head(b, "b", tr("s3_title_b", lang))

    # c — tasa 2024 frente a profundidad
    c = ax[1, 0]
    last = YEARS_GRD[-1]
    h24 = D.hosp[(D.hosp.variant == variant) & (D.hosp.year == last)].copy()
    h24["rate"] = PER * h24.n_f84_any / h24.n_episodes_total
    ok = h24[(h24.rate > 0) & h24.coding_depth_mean.notna()]
    c.scatter(ok.coding_depth_mean, ok.rate, c=[COL["fixed"] if bool(v) else COL["new"] for v in ok.in_fixed_panel], s=13, edgecolor="white", linewidth=0.35, zorder=3)
    rho, pval = stats.spearmanr(ok.coding_depth_mean, ok.rate)
    c.set_yscale("log"); log_axis_fmt(c, lang); fmt_axis(c, lang, "x", 1); c.set_xlabel(tr("s3_depth_axis", lang)); c.set_ylabel(tr("s3_rate_axis", lang))
    c.set_ylim(top=ok.rate.max() * 12.0)
    # Sólo el estadístico: la advertencia sobre la asociación ecológica está íntegra en el pie de la figura y,
    # dentro del panel, la nota entera se imprimía sobre la nube de puntos.
    plate_note(c, f"{tr('s3_spearman', lang)} = {num(rho, 2, lang)} (p {C.fmt_p(pval, lang) if pval < 0.001 else '= ' + C.fmt_p(pval, lang)}; n = {num(len(ok), 0, lang)})",
               x=0.02, y=0.985, ha="left")
    panel_head(c, "c", tr("s3_title_c", lang))

    # d — distribución por año
    d = ax[1, 1]
    hh = D.hosp[D.hosp.variant == variant].copy()
    hh["rate"] = PER * hh.n_f84_any / hh.n_episodes_total
    hh = hh[hh.rate > 0]
    data = [hh[hh.year == y].rate.values for y in YEARS_GRD]
    d.boxplot(data, positions=YEARS_GRD, widths=0.55, showfliers=False, patch_artist=True, boxprops=dict(facecolor="#dbe9f6", color="#333333", linewidth=0.6), medianprops=dict(color=OKABE[1], lw=1.2), whiskerprops=dict(linewidth=0.6), capprops=dict(linewidth=0.6))
    rng = np.random.default_rng(20260904)
    for y, vals, fp in zip(YEARS_GRD, data, [hh[hh.year == y].in_fixed_panel.astype(bool).values for y in YEARS_GRD]):
        d.scatter(y + rng.uniform(-0.18, 0.18, len(vals)), vals, s=4, c=[COL["fixed"] if v else COL["new"] for v in fp], alpha=0.7, zorder=3, linewidths=0)
    med = [np.median(hh[(hh.year == y) & hh.in_fixed_panel.astype(bool)].rate) for y in YEARS_GRD]
    d.plot(YEARS_GRD, med, "-", color="#333333", lw=1.1, zorder=4)
    d.set_yscale("log"); log_axis_fmt(d, lang); d.set_xticks(YEARS_GRD); d.set_xticklabels([str(y) for y in YEARS_GRD]); d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("s3_rate_axis", lang))
    d.set_ylim(max(0.5, hh.rate.min() * 0.3), hh.rate.max() * 12.0)
    d.tick_params(axis="x", labelrotation=45)
    for lb in d.get_xticklabels():
        lb.set_ha("right")
    context(d, lang, pandemic_label=False, law_label=False)
    # La nota («cajas: mediana y cuartiles; puntos: hospitales…») se imprimía sobre la nube de puntos; su
    # texto está íntegro en el pie de la figura.
    panel_head(d, "d", tr("s3_title_d", lang))

    # e / f — el panel fijo de 65 hospitales, partido por la mediana de la tasa de 2024
    from matplotlib.ticker import LogLocator, NullFormatter
    for cell, half, ch, key in [(ax[2, 0], "top", "e", "s3_title_e"), (ax[2, 1], "bottom", "f", "s3_title_f")]:
        _dumbbell(cell, D, variant, lang, half=half)
        # sólo décadas: con los subrótulos 2 y 5 los seis números se imprimían pegados
        cell.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=8))
        cell.xaxis.set_minor_locator(LogLocator(base=10, subs=(2.0, 5.0), numticks=16))
        cell.xaxis.set_minor_formatter(NullFormatter())
        panel_head(cell, ch, tr(key, lang))

    path = save_plate(fig, fdir / "figS3_grd_hospital_effects.png"); plt.close(fig)
    return path, has_effects


# ===========================================================================
# S4 · Forest de sensibilidades de los modelos
# ===========================================================================
def _model_rows(D, variant, position):
    m = D.models
    base = m[(m.variant == variant) & (m.position == f"pos_{position}")]
    rows = []
    rate = base[base.estimand == "est_grd_rate"].copy()
    order_cov = ["cov_none", "cov_depth", "cov_disruption", "cov_depth_disruption"]
    rate["_p"] = rate.panel.map({"panel_observed": 0, "panel_fixed65": 1}); rate["_a"] = rate.activity.map({"act_all": 0, "act_hospitalisation": 1})
    rate["_c"] = rate.covariates.map({k: i for i, k in enumerate(order_cov)}); rate["_y"] = rate.years.map({"2019-2024": 0, "2021-2024": 1})
    for _, r in rate.sort_values(["_p", "_a", "_y", "_c"]).iterrows():
        rows.append(("rate", r))
    hosp = base[base.estimand == "est_grd_hospital"].copy()
    if len(hosp):
        hosp["_p"] = hosp.panel.map({"panel_observed": 0, "panel_fixed65": 1}); hosp["_y"] = hosp.years.map({"2019-2024": 0, "2021-2024": 1})
        for _, r in hosp.sort_values(["_p", "_y", "covariates", "model_family"]).iterrows():
            rows.append(("hosp", r))
    pop = base[(base.estimand == "est_grd_pop") & (base.sex == "TOTAL")].copy()
    for _, r in pop.sort_values(["years", "covariates"]).iterrows():
        rows.append(("pop", r))
    return rows


def _row_label(kind, r, lang):
    yrs = str(r.years).replace("-", "–")
    if kind == "rate":
        return f"{tr(r.panel, lang)} · {tr(r.activity, lang)} · {tr(r.covariates, lang)} · {yrs}"
    if kind == "hosp":
        fam = f" ({tr(r.model_family, lang)})" if r.model_family in ("fam_qp_fe_cluster", "fam_ri_map") else ""
        return f"{tr(r.panel, lang)} · {tr(r.covariates, lang)}{fam} · {yrs}"
    return f"{tr('crude', lang) if r.covariates == 'cov_none' else tr(r.covariates, lang)} · {yrs}"


def _row_label_short(kind, r, lang):
    """Rótulo de fila para la lámina vertical: mismas componentes, abreviadas al ancho de la celda."""
    yrs = str(r.years).replace("2019-2024", "19–24").replace("2021-2024", "21–24")
    if kind == "rate":
        return f"{tr('s4_sh_' + r.panel, lang)} · {tr('s4_sh_' + r.activity, lang)} · {tr('s4_sh_' + r.covariates, lang)} · {yrs}"
    if kind == "hosp":
        fam = f" · {tr('s4_sh_' + r.model_family, lang)}" if r.model_family in ("fam_qp_fe_cluster", "fam_ri_map") else ""
        return f"{tr('s4_sh_' + r.panel, lang)} · {tr('s4_sh_' + r.covariates, lang)}{fam} · {yrs}"
    kind_lab = tr("s4_sh_crude", lang) if r.covariates == "cov_none" else tr("s4_sh_" + r.covariates, lang)
    return f"{kind_lab} · {yrs}"


def figS4(D, variant, lang, fdir):
    """Lámina vertical de 180 × 245 mm con la norma del estudio: tres filas (familia de modelo) por dos
    columnas (posición del código). La versión anterior era una lámina apaisada de 17 × 12,5 pulgadas con
    dos paneles, fuera de la norma, y su leyenda de figura se cortaba contra el borde inferior del lienzo."""
    if D.models is None:
        WARNINGS.append("S4 skipped: models_summary.csv not available")
        return None
    plt, sns = plate_style()
    from matplotlib.lines import Line2D
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    xlim = (-40, 130)
    colour = {"rate": OKABE[0], "hosp": OKABE[2], "pop": OKABE[1]}
    rows_by_pos = {pos: _model_rows(D, variant, pos) for pos in ("any", "principal")}
    letters = {("rate", "any"): "a", ("rate", "principal"): "b", ("hosp", "any"): "c",
               ("hosp", "principal"): "d", ("pop", "any"): "e", ("pop", "principal"): "f"}
    titles = {"rate": "s4_grp_rate", "hosp": "s4_grp_hosp", "pop": "s4_grp_pop"}
    pos_title = {"any": "s4_title_any", "principal": "s4_title_pri"}
    base_apc = {}
    for kind, r in rows_by_pos["any"]:
        if (kind == "rate" and r.panel == "panel_observed" and r.activity == "act_all"
                and r.covariates == "cov_none" and str(r.years) == "2019-2024"):
            base_apc["any"] = float(r.apc)
    for kind, r in rows_by_pos["principal"]:
        if (kind == "rate" and r.panel == "panel_observed" and r.activity == "act_all"
                and r.covariates == "cov_none" and str(r.years) == "2019-2024"):
            base_apc["principal"] = float(r.apc)

    for i, kind in enumerate(("rate", "hosp", "pop")):
        for j, pos in enumerate(("any", "principal")):
            cell = ax[i, j]
            rows = [(k, r) for k, r in rows_by_pos[pos] if k == kind]
            head = f"{tr(pos_title[pos], lang)} — {tr(titles[kind], lang)}"
            if not rows:
                # «no estimable» no se dibuja como cero: la celda lo dice con palabras
                cell.text(0.5, 0.5, C.plate_wrap(tr("s4_none", lang), 120.0, FS_MIN + 0.5, "normal"),
                          ha="center", va="center", transform=cell.transAxes, fontsize=FS_MIN + 0.5, color="#555555")
                cell.set_xticks([]); cell.set_yticks([])
                panel_head(cell, letters[(kind, pos)], head)
                continue
            yy = np.arange(len(rows))[::-1]
            for y_, (_k, r) in zip(yy, rows):
                lo, hi = float(r.apc_lo), float(r.apc_hi)
                clipped = (lo < xlim[0]) or (hi > xlim[1])
                cell.plot([max(lo, xlim[0]), min(hi, xlim[1])], [y_, y_], color=colour[kind], lw=1.2, zorder=2)
                mk = "o" if str(r.years) == "2019-2024" else "^"
                cell.scatter(float(r.apc), y_, s=11, color=colour[kind], marker=mk, zorder=3,
                             edgecolor="white", linewidth=0.4)
                if clipped:
                    cell.text(xlim[1] - 2, y_, "*", fontsize=FS_MIN, color=colour[kind], va="center", ha="right")
            cell.axvline(0, color="#888888", ls="--", lw=0.9, zorder=0)
            if pos in base_apc:
                cell.axvline(base_apc[pos], color=OKABE[0], ls=":", lw=0.9, zorder=0)
            cell.set_yticks(yy)
            cell.set_yticklabels([_row_label_short(k, r, lang) for k, r in rows], fontsize=FS_MIN)
            # banda libre en (a) para la única leyenda de la lámina: un «forest» no tiene hueco entre filas
            cell.set_ylim(-0.8, len(rows) - 0.2 + (5.5 if (kind, pos) == ("rate", "any") else 0.0))
            cell.set_xlim(*xlim); cell.set_xticks([-25, 0, 25, 50, 75, 100, 125])
            cell.tick_params(axis="x", labelsize=FS_MIN)
            fmt_axis(cell, lang, "x", 0)
            cell.set_xlabel(tr("s4_axis", lang))
            cell.grid(axis="y", visible=False)
            panel_head(cell, letters[(kind, pos)], head)

    # Leyenda ÚNICA de la lámina, dentro del primer panel (la leyenda de figura anterior colgaba bajo el
    # lienzo y sus cuatro entradas se cortaban contra el borde inferior).
    key = plate_legend(ax[0, 0],
                       handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor="#333333", markersize=3.6, label=tr("s4_w1924", lang)),
                                Line2D([0], [0], marker="^", color="w", markerfacecolor="#333333", markersize=3.6, label=tr("s4_w2124", lang)),
                                Line2D([0], [0], color=OKABE[0], ls=":", lw=0.9, label=tr("s4_base", lang)),
                                Line2D([0], [0], color="w", label=f"* {tr('s4_clipped', lang)}")],
                       loc="upper right", fs=FS_MIN, ncol=2)
    # sitio reservado a medida: el motor no debe reubicarla, porque en un «forest» completo no hay hueco
    # que no sea el que se ha reservado a propósito
    key.set_gid(C.PLATE_KEEP)
    path = save_plate(fig, fdir / "figS4_grd_model_sensitivities.png"); plt.close(fig)
    return path


# ===========================================================================
# Tabla suplementaria: quiebres de definición
# ===========================================================================
def breaks_table(lang):
    kind_lbl = {"flow": tr("s_flow", lang), "stock": tr("s_stock", lang), "activity": tr("s_activity", lang), "survey": tr("s_survey", lang), "education": tr("s_education", lang)}
    cls_lbl = {"def": tr("f1_tl_def", lang), "panel": tr("f1_tl_panel", lang), "start": tr("f1_tl_start", lang)}
    rows = []
    for src, y0, y1, kind, brks in BREAKS:
        for yr, cls, lab, _pos in brks:
            rows.append({tr("tb_source", lang): src, tr("tb_years", lang): f"{y0}–{y1}" if y0 != y1 else str(y0), tr("tb_type", lang): kind_lbl[kind],
                         tr("tb_break_year", lang): str(yr), tr("tb_kind", lang): cls_lbl[cls], tr("tb_break", lang): lab[lang]})
    return pd.DataFrame(rows)


# ===========================================================================
# Leyendas autónomas
# ===========================================================================
def captions(variant, lang, info):
    vl = variant_label(variant, lang)
    hosp_years = "65, 65, 65, 65, 68 y 72" if lang == "es" else "65, 65, 65, 65, 68 and 72"
    nat = num(info.get("nat_rate_2024", np.nan), 0, lang)
    extremes = "; ".join(f"{tag} = {name} ({num(rate, 0, lang)})" for tag, name, rate in info.get("extremes", []))
    if lang == "es":
        return {
            "fig1_sources_coverage": {
                "title": "Figura 2. Completitud del reporte administrativo, capas de cobertura, paneles y quiebres de definición del estudio multisistema, Chile 2019–2025",
                "caption": ("(a) Completitud del reporte REM por módulo y año. La unidad es la celda establecimiento × periodo × código: la rejilla potencial de cada módulo y año son "
                            "los establecimientos que presentaron al menos una fila de ese módulo ese año, multiplicados por los periodos de reporte del año (doce meses en la Serie A; "
                            "junio y diciembre en la Serie P) y por los códigos del módulo vigentes ese año. Cada celda de la rejilla lleva una barra apilada al 100 % con los tres estados "
                            "excluyentes de esa celda —valor informado (azul), cero explícito (naranja) y no informado, es decir, sin fila para esa combinación o con la celda en blanco "
                            "(gris)—, y sobre la barra se imprime el porcentaje con valor informado. El cero explícito casi no se usa (nunca pasa del 1,3 % de las celdas), de modo que su "
                            "segmento se dibuja con un ancho mínimo visible y no es proporcional cuando es muy pequeño; una celda en blanco no puede leerse como un cero. La fila inferior "
                            "son las filas establecimiento × mes presentes en los archivos (miles) y el rayado marca los códigos no vigentes; DEIS añade un cuarto estado, los "
                            "egresos en filas enmascaradas por el proveedor. Un porcentaje alto de celdas no informadas es esperable cuando el módulo tiene una familia amplia de códigos "
                            "(A05 y P6 desde 2021) y no indica ausencia de actividad. (b) Capas de cobertura 2019–2025 en millones: población INE (base 2017, residencia, 30 de junio, "
                            "«INE» en la leyenda), beneficiarios FONASA e ISAPRE (stocks de diciembre) e inscritos APS (diciembre, lugar de atención); la cifra al final de cada serie es su "
                            "valor en 2025. Eje derecho: cociente (FONASA + ISAPRE)/INE, que no es una tasa de "
                            "aseguramiento (mezcla stocks de diciembre con una proyección a junio y omite otros regímenes). (c) Establecimientos que reportan cada módulo REM por año "
                            "(máximo entre los códigos de la era; escala logarítmica): A03 por era de definición (2019–2022 legado 03500406/07; 2023–2024 familia 09600212–19; 2024 códigos "
                            "31–59 meses; 2025 rediseño 03710013–21), A05 TGD amplio 2019–2020 y autismo 2021–2025, A27 y A28 desde 2023, P2 y P6 en diciembre (P6 TGD amplio 2019–2020 y "
                            "autismo 2021–2025); ninguna línea cruza un quiebre de definición y las líneas verticales discontinuas marcan los quiebres. (d) Hospitales GRD observados por "
                            "año (" + hosp_years + ") frente al panel fijo de 65 y episodios GRD totales de cada panel (eje derecho). (e) REM-20: egresos de todos los establecimientos y del "
                            "panel de 188 con 12 meses en todos los años, retención del panel (%, eje derecho) y número de establecimientos reportantes; es un panel de actividad/capacidad, "
                            "no un denominador poblacional. (f) Cobertura y quiebres por fuente: cada columna es una fuente (color según su naturaleza: flujo, stock, actividad/capacidad, "
                            "encuesta transversal o stock escolar), la barra abarca los años cubiertos y cada marcador es un quiebre de definición o de códigos (rombo), de panel, cobertura "
                            "o esquema (cuadrado) o el inicio de la serie (triángulo); el texto de cada quiebre se lista íntegro en la tabla de quiebres de definición del material "
                            "suplementario. Banda gris: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto, no como intervención; ambas significan lo "
                            "mismo en todos los paneles y se rotulan una sola vez, en (b). Todos los conteos son reconocimiento administrativo, no prevalencia ni incidencia. Lámina "
                            "idéntica en ambas variantes de definición (con/sin Rett)."),
            },
            "fig2_grd_core": {
                "title": f"Figura 3. Episodios GRD con F84 documentado en hospitales públicos de Chile, 2019–2024: tasas por episodios, modalidad, profundidad diagnóstica, edad y sexo, hospitales y personas — variante {vl}",
                "caption": (f"(a) Episodios con F84 en cualquier posición y con F84 principal por 100.000 episodios GRD del mismo panel y año (escala logarítmica; IC 95 % exactos de Poisson), "
                            f"panel anual observado ({hosp_years} hospitales en 2019–2024, indicados al pie) y panel fijo de 65 hospitales. (b) Panel observado por modalidad: toda modalidad, "
                            "hospitalización estricta y cirugía mayor ambulatoria (CMA), cualquier posición; la categoría «otra» está ausente de los archivos 2020–2024 (ausencia, no cero). "
                            "(c) Tasa de F84 por 100.000 episodios dentro de cada estrato de profundidad diagnóstica (diagnósticos codificados por episodio) en 2019 y 2024 con IC exactos; "
                            "recuadro: profundidad media de todos los episodios y de los episodios con F84 por año. (d) Episodios con F84 (cualquier posición) por 100.000 habitantes INE (base 2017, "
                            "nacional) por grupo de edad (45 y más agrupado) y sexo, 2019 frente a 2024 (IC exactos; escala logarítmica): el numerador se localiza por lugar de atención (hospitales "
                            "públicos GRD) y el denominador por residencia, por lo que es una lectura complementaria y no una tasa de uso de una población definida. (e) Tasa de F84 por 100.000 "
                            f"episodios de cada hospital en 2024 ({num(info.get('n_hosp_last', 72), 0, lang)} hospitales: {num(info.get('n_fixed', 65), 0, lang)} del panel fijo y "
                            f"{num(info.get('n_new', 7), 0, lang)} incorporados en 2023–2024), ordenados de menor a mayor en el eje vertical, con IC exactos y tasa nacional ({nat}); "
                            f"los cinco hospitales con la tasa más alta se numeran 1–5 y los tres con la más baja x, y y z: {extremes}. "
                            "(f) Episodios con F84 y personas únicas dentro de cada año, en miles (sin deduplicación entre años: el identificador cambia de formato entre 2020 y 2021), episodios por persona "
                            "(cifras sobre las barras) y razón hombre:mujer de los episodios con IC 95 % (eje derecho). Banda gris: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 "
                            "(marzo 2023) como contexto; ambas significan lo mismo en todos los paneles y se rotulan una sola vez, en (a). "
                            f"Definición: {vl}. Los conteos son reconocimiento administrativo (episodios con F84 documentado, no «hospitalizaciones por autismo»), no prevalencia ni incidencia."),
            },
            "figS1_grd_variants": {
                "title": f"Figura S1. Sensibilidad de las series GRD a la inclusión del síndrome de Rett (F84.2): variante F84 completo frente a F84 sin Rett, 2019–2024",
                "caption": ("(a) Episodios con F84 en cualquier posición por 100.000 episodios GRD (panel observado, toda modalidad) en ambas variantes, con IC 95 % exactos. (b) Ídem para F84 principal. "
                            "(c) Hospitalización estricta y CMA (cualquier posición) por variante. (d) Episodios con F84.2 en cualquier posición y en posición principal por año, con su porcentaje "
                            "dentro de la familia F84 completa. (e) Diferencia relativa (con − sin)/sin, en %, para cada serie: cualquier posición, principal, hospitalización, CMA y personas únicas "
                            "dentro del año. (f) Panel fijo de 65 hospitales (cualquier posición y principal, escala logarítmica) y personas únicas dentro del año (barras, eje derecho) por variante. "
                            "Las series de autismo estricto REM y F84.0 no cambian entre variantes. Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto. "
                            "Lámina idéntica en ambas variantes; los conteos son reconocimiento administrativo."),
            },
            "figS2_grd_subcodes": {
                "title": f"Figura S2. Composición de subcódigos F84 y posición del código en los episodios GRD, 2019–2024 — variante {vl}",
                "caption": (f"Subcódigos de la variante ({vl}). (a) Distribución porcentual de las menciones de subcódigos F84 en cualquier posición por año (un episodio puede tener más de un "
                            "subcódigo: menciones ≠ episodios). (b) Menciones por subcódigo (escala logarítmica). (c) Porcentaje de las menciones de cada subcódigo registradas como diagnóstico "
                            "principal (solo subcódigos con ≥ 20 menciones en todos los años) y de la familia completa. (d) Episodios con F84 según posición del código (solo principal, principal "
                            "y secundario, solo secundario; panel observado, toda modalidad) y porcentaje solo secundario. (e) Solo F84.0 (idéntico en ambas variantes) frente a la familia F84 de la "
                            "variante por 100.000 episodios GRD, con IC exactos. (f) Episodios con F84.2 (síndrome de Rett) por posición: incluidos en la variante F84 completo y excluidos en la "
                            "variante sin Rett. Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto. Reconocimiento administrativo, no prevalencia."),
            },
            "figS3_grd_hospital_effects": {
                "title": f"Figura S3. Heterogeneidad entre hospitales GRD: efectos por hospital, profundidad diagnóstica y tasas 2019 frente a 2024 — variante {vl}",
                "caption": ("(a) Efectos fijos de hospital del modelo cuasi-Poisson 2019–2024 (indicadores de hospital, tendencia común, offset log(episodios)), expresados como razones de tasas "
                            "frente a la media geométrica de los hospitales, con IC 95 %; cruces: ajustados por profundidad diagnóstica del hospital-año; color: panel fijo 2019–2024 (65) frente "
                            "a hospitales incorporados en 2023–2024. (b) Medias posteriores del intercepto aleatorio Poisson (Laplace/MAP) frente al efecto fijo centrado: la contracción hacia cero "
                            "refleja la incertidumbre de los hospitales pequeños; se indica la DE del intercepto con IC. (c) Tasa 2024 por 100.000 episodios del hospital frente a su profundidad "
                            "diagnóstica media (asociación ecológica, ρ de Spearman); no implica causalidad ni calidad. (d) Distribución de las tasas por hospital y año (cajas: mediana y cuartiles; "
                            "puntos: hospitales; línea: mediana del panel fijo; escala logarítmica). (e, f) Tasa de cada uno de los 65 hospitales del panel fijo en 2019 frente a 2024, ordenados "
                            "por la tasa de 2024 y partidos por su mediana para que cada hospital lleve un nombre legible: (e) la mitad con la tasa 2024 más alta, (f) la mitad con la más baja "
                            "(escala logarítmica; aspa: sin episodios F84 en 2019; nombres abreviados). Si hospital_effects.csv no está disponible, a y b lo indican. Resultados descriptivos por lugar de "
                            "atención; sombreado 2020–2021: disrupción del reporte; Ley 21.545 solo como contexto."),
            },
            "figS4_grd_model_sensitivities": {
                "title": f"Figura S4. Sensibilidad del cambio porcentual anual (CPA) de los episodios GRD con F84 documentado a panel, modalidad, covariables, ventana y unidad de análisis — variante {vl}",
                "caption": ("Tres filas (familia de modelo) por dos columnas (posición del código); los rótulos de fila van abreviados (obs. = panel observado; fijo 65 = panel fijo de 65 "
                            "hospitales; toda = toda modalidad; hosp. = hospitalización estricta; sin cov. = sin covariables; +prof. = con profundidad diagnóstica media; +2020–21 = con "
                            "indicador de disrupción; EF hosp. = efectos fijos de hospital; int. aleat. = intercepto aleatorio; EE rob. = errores estándar robustos por hospital; 19–24 y "
                            "21–24 = ventana) y la especificación completa de cada fila, con su estimación y su intervalo, está en la tabla de modelos del material suplementario. "
                            "(a) y (b) F84 en cualquier posición y F84 principal: CPA e IC 95 % (Wald) de modelos cuasi-Poisson log-lineales por 100.000 episodios GRD (offset log(episodios) del mismo "
                            "panel y modalidad; panel observado con 65–72 hospitales o panel fijo de 65; toda modalidad u hospitalización estricta; sin covariables, con profundidad diagnóstica "
                            "media, con indicador de disrupción 2020–2021 o ambos; ventanas 2019–2024 y 2021–2024), de modelos hospital-año (efectos fijos de hospital con offset log(episodios del "
                            "hospital), EE robustos por hospital, ajuste por profundidad, indicador 2020–2021 e intercepto aleatorio Poisson Laplace/MAP) y de tasas por 100.000 habitantes INE "
                            "(ambos sexos; brutas y ajustadas por edad). Círculos: ventana 2019–2024; triángulos: 2021–2024; asterisco: IC truncado en el eje; línea punteada: modelo base. "
                            "Ninguna especificación estima un efecto de la Ley 21.545; el indicador 2020–2021 describe la disrupción del reporte. Con 4–6 puntos anuales las estimaciones nacionales "
                            "son descriptivas y sensibles a la profundidad diagnóstica. Reconocimiento administrativo, no prevalencia."),
            },
        }
    return {
        "fig1_sources_coverage": {
            "title": "Figure 2. Administrative reporting completeness, coverage layers, panels and definition breaks of the multisource study, Chile 2019–2025",
            "caption": ("(a) REM reporting completeness by module and year. The unit is the establishment × period × code cell: each module-year's potential grid is the establishments that "
                        "filed at least one row of that module in that year, multiplied by the year's reporting periods (twelve months in Series A; June and December in Series P) and by the "
                        "module's codes in force that year. Each grid cell carries a 100% stacked bar of that cell's three mutually exclusive states — reported value (blue), explicit zero "
                        "(orange) and not reported at all, that is, no row for the combination or a row with the cell left blank (grey) — and the percentage with a reported value is printed "
                        "above the bar. Explicit zeros are barely used (never above 1.3% of cells), so their segment is drawn at a minimum visible width and is not proportional when very small; "
                        "a blank cell cannot be read as a zero. The bottom line gives the establishment × month rows present in the files (thousands) and hatching marks codes not in force; "
                        "DEIS adds a fourth state, discharges in provider-masked rows. A high not-reported percentage is expected "
                        "where the module carries a broad code family (A05 and P6 from 2021) and does not indicate absence of activity. (b) Coverage layers 2019–2025 in millions: INE population "
                        "(base 2017, residence, 30 June; 'INE' in the legend), FONASA and ISAPRE beneficiaries (December stocks) and APS enrolled (December, place of care); the figure at the end "
                        "of each series is its 2025 value. Right axis: the (FONASA + ISAPRE)/INE ratio, which "
                        "is not an insurance rate (it mixes December stocks with a 30-June projection and omits other regimes). (c) Establishments reporting each REM module by year (maximum "
                        "across the era's codes; log scale): A03 by definition era (2019–2022 legacy 03500406/07; 2023–2024 family 09600212–19; 2024 31–59-month codes; 2025 redesign "
                        "03710013–21), A05 broad PDD 2019–2020 and autism 2021–2025, A27 and A28 from 2023, P2 and P6 in December (P6 broad PDD 2019–2020 and autism 2021–2025); no line crosses "
                        "a definition break and the dashed vertical lines mark the breaks. (d) GRD hospitals observed per year (" + hosp_years + ") against the fixed panel of 65, and total GRD "
                        "episodes of each panel (right axis). (e) REM-20: discharges of all establishments and of the 188-establishment panel with 12 months in every year, panel retention "
                        "(%, right axis) and the number of reporting establishments; this is an activity/capacity panel, not a population denominator. (f) Coverage and breaks by source: each "
                        "column is a source (colour by its nature: flow, stock, activity/capacity, cross-sectional survey or school stock), the bar spans the years covered, and each marker is a "
                        "definition or code break (diamond), a panel, coverage or schema break (square) or the start of the series (triangle); the text of every break is listed in full in the "
                        "definition-breaks table of the supplementary material. Grey band: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context, not as an intervention; "
                        "both mean the same in every panel and are labelled once, in (b). All counts are administrative recognition, not prevalence or incidence. The plate is identical in both "
                        "definition variants (with/without Rett)."),
        },
        "fig2_grd_core": {
            "title": f"Figure 3. GRD episodes with documented F84 in Chilean public hospitals, 2019–2024: rates per episode, activity, coding depth, age and sex, hospitals and persons — {vl} variant",
            "caption": (f"(a) Episodes with F84 in any position and with principal F84 per 100,000 GRD episodes of the same panel and year (log scale; exact 95% Poisson CIs), observed annual panel "
                        f"({hosp_years} hospitals in 2019–2024, printed at the foot) and fixed panel of 65 hospitals. (b) Observed panel by activity: all activity, strict hospitalisation and major "
                        "ambulatory surgery (CMA), any position; the 'other' category is absent from the 2020–2024 files (absence, not zero). (c) F84 rate per 100,000 episodes within each coding-depth "
                        "stratum (coded diagnoses per episode) in 2019 and 2024 with exact CIs; inset: mean depth of all episodes and of episodes with F84 by year. (d) Episodes with F84 (any position) "
                        "per 100,000 INE population (base 2017, national) by age group (45 and over pooled) and sex, 2019 versus 2024 (exact CIs; log scale): the numerator is located by place of care "
                        "(public GRD hospitals) and the denominator by residence, so this is a complementary reading and not a use rate for a defined population. (e) F84 rate per 100,000 episodes of "
                        f"each hospital in 2024 ({num(info.get('n_hosp_last', 72), 0, lang)} hospitals: {num(info.get('n_fixed', 65), 0, lang)} from the fixed panel and "
                        f"{num(info.get('n_new', 7), 0, lang)} added in 2023–2024), ranked from lowest to highest along the vertical axis, with exact CIs and the national rate ({nat}); the five "
                        f"hospitals with the highest rate are numbered 1–5 and the three lowest x, y and z: {extremes}. "
                        "(f) Episodes with F84 and unique persons within each year, in thousands (no deduplication across years: the identifier changes format between 2020 and 2021), episodes per person (figures "
                        "above the bars) and the male:female ratio of episodes with 95% CIs (right axis). Grey band: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context; "
                        "both mean the same in every panel and are labelled once, in (a). "
                        f"Definition: {vl}. Counts are administrative recognition (episodes with documented F84, not 'hospitalisations for autism'), not prevalence or incidence."),
        },
        "figS1_grd_variants": {
            "title": "Figure S1. Sensitivity of the GRD series to the inclusion of Rett syndrome (F84.2): full F84 versus F84 without Rett, 2019–2024",
            "caption": ("(a) Episodes with F84 in any position per 100,000 GRD episodes (observed panel, all activity) in both variants, with exact 95% CI. (b) Same for principal F84. "
                        "(c) Strict hospitalisation and CMA (any position) by variant. (d) Episodes with F84.2 in any position and as principal diagnosis by year, with their percentage of the "
                        "full F84 family. (e) Relative difference (with − without)/without, in %, for each series: any position, principal, hospitalisation, CMA and unique persons within year. "
                        "(f) Fixed panel of 65 hospitals (any position and principal, log scale) and unique persons within year (bars, right axis) by variant. The strict REM autism and F84.0 "
                        "series do not change between variants. Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context. Identical in both variants; counts are "
                        "administrative recognition."),
        },
        "figS2_grd_subcodes": {
            "title": f"Figure S2. F84 subcode composition and code position in GRD episodes, 2019–2024 — {vl} variant",
            "caption": (f"Subcodes of the variant ({vl}). (a) Percentage distribution of F84 subcode mentions in any position by year (an episode may carry more than one subcode: mentions ≠ "
                        "episodes). (b) Mentions by subcode (log scale). (c) Percentage of each subcode's mentions recorded as principal diagnosis (subcodes with ≥ 20 mentions in every year) and "
                        "of the whole family. (d) Episodes with F84 by code position (principal only, principal and secondary, secondary only; observed panel, all activity) and percentage secondary "
                        "only. (e) F84.0 only (identical in both variants) versus the variant's F84 family per 100,000 GRD episodes, with exact CIs. (f) Episodes with F84.2 (Rett syndrome) by "
                        "position: included in the full-F84 variant and excluded in the without-Rett variant. Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context. "
                        "Administrative recognition, not prevalence."),
        },
        "figS3_grd_hospital_effects": {
            "title": f"Figure S3. Heterogeneity across GRD hospitals: hospital effects, coding depth and rates 2019 versus 2024 — {vl} variant",
            "caption": ("(a) Hospital fixed effects from the quasi-Poisson model 2019–2024 (hospital indicators, common trend, log(episodes) offset), expressed as rate ratios against the "
                        "geometric mean of hospitals, with 95% CI; crosses: adjusted for hospital-year coding depth; colour: 2019–2024 fixed panel (65) versus hospitals added in 2023–2024. "
                        "(b) Posterior means of the Poisson random intercept (Laplace/MAP) against the centred fixed effect: shrinkage towards zero reflects the uncertainty of small hospitals; "
                        "intercept SD with CI. (c) 2024 rate per 100,000 hospital episodes versus the hospital's mean coding depth (ecological association, Spearman ρ); implies neither causality "
                        "nor quality. (d) Distribution of hospital rates by year (boxes: median and quartiles; points: hospitals; line: fixed-panel median; log scale). (e, f) Rate of each of the 65 "
                        "fixed-panel hospitals in 2019 versus 2024, ranked by the 2024 rate and split at its median so that every hospital carries a legible name: (e) the half with the higher "
                        "2024 rate, (f) the half with the lower one (log scale; cross: no F84 episodes in 2019; abbreviated names). If hospital_effects.csv is unavailable, a and b say so. "
                        "Descriptive results by place of care; 2020–2021 shading: reporting disruption; Law 21.545 as context only."),
        },
        "figS4_grd_model_sensitivities": {
            "title": f"Figure S4. Sensitivity of the annual percent change (APC) of GRD episodes with documented F84 to panel, activity, covariates, window and unit of analysis — {vl} variant",
            "caption": ("Three rows (model family) by two columns (code position); row labels are abbreviated (obs. = observed panel; fixed 65 = fixed panel of 65 hospitals; all = all activity; "
                        "hosp. = strict hospitalisation; no cov. = no covariates; +depth = with mean coding depth; +2020–21 = with the disruption indicator; hosp. FE = hospital fixed effects; "
                        "random int. = random intercept; robust SE = hospital-clustered standard errors; 19–24 and 21–24 = window), and the full specification of every row, with its estimate "
                        "and interval, is in the models table of the supplementary material. "
                        "(a) and (b) F84 in any position and principal F84: APC and Wald 95% CI from quasi-Poisson log-linear models per 100,000 GRD episodes (log(episodes) offset of the same panel "
                        "and activity; observed panel with 65–72 hospitals or fixed panel of 65; all activity or strict hospitalisation; no covariates, mean coding depth, 2020–2021 disruption "
                        "indicator or both; 2019–2024 and 2021–2024 windows), from hospital-year models (hospital fixed effects with log(hospital episodes) offset, hospital-clustered SE, depth "
                        "adjustment, 2020–2021 indicator and Poisson random intercept, Laplace/MAP) and from rates per 100,000 INE population (both sexes; crude and age-adjusted). Circles: "
                        "2019–2024 window; triangles: 2021–2024; asterisk: CI clipped at the axis; dotted line: base model. No specification estimates an effect of Law 21.545; the 2020–2021 "
                        "indicator describes reporting disruption. With 4–6 annual points the national estimates are descriptive and sensitive to coding depth. Administrative recognition, "
                        "not prevalence."),
        },
    }


def breaks_title(lang):
    if lang == "es":
        return {"S_definition_breaks": {"title": "Tabla S1b. Quiebres de definición, panel y esquema por fuente administrativa, 2019–2025",
                                        "note": "Una fila por quiebre; fuente, años cubiertos, carácter de stock/flujo, año y tipo del quiebre (definición/códigos; panel/cobertura/esquema; inicio de serie). "
                                                "Los quiebres REM siguen rem_pathway_codes.csv y los diccionarios anuales; GRD: identificador con formato distinto en 2020 y 2021 (sin enlace de personas entre esos años) "
                                                "y panel observado de 65/65/65/65/68/72 hospitales; DEIS publica solo el diagnóstico principal. 2020–2021: disrupción del reporte por la pandemia; Ley 21.545 (marzo 2023): contexto, no intervención."}}
    return {"S_definition_breaks": {"title": "Table S1b. Definition, panel and schema breaks by administrative source, 2019–2025",
                                    "note": "One row per break; source, years covered, stock/flow nature, year and kind of break (definition/codes; panel/coverage/schema; series start). "
                                            "REM breaks follow rem_pathway_codes.csv and the annual dictionaries; GRD: identifier format differs between 2020 and 2021 (no person linkage across those years) "
                                            "and observed panel of 65/65/65/65/68/72 hospitals; DEIS publishes the principal diagnosis only. 2020–2021: pandemic reporting disruption; Law 21.545 (March 2023): context, not an intervention."}}


# ===========================================================================
# main
# ===========================================================================
def main() -> int:
    t0 = time.time()
    log("loading tidy tables")
    D = load()
    outputs = []
    for variant in VARIANTS:
        for lang in LANGS:
            t1 = time.time()
            fdir, tdir = out_dir(variant, lang, "figures"), out_dir(variant, lang, "tables")
            p1 = fig1(D, variant, lang, fdir); outputs.append(str(p1))
            p2, info = fig2(D, variant, lang, fdir); outputs.append(str(p2))
            p3 = figS1(D, variant, lang, fdir); outputs.append(str(p3))
            p4 = figS2(D, variant, lang, fdir); outputs.append(str(p4))
            p5, has_eff = figS3(D, variant, lang, fdir); outputs.append(str(p5))
            p6 = figS4(D, variant, lang, fdir)
            if p6 is not None:
                outputs.append(str(p6))
            caps = captions(variant, lang, info)
            if p6 is None:
                caps.pop("figS4_grd_model_sensitivities", None)
            merge_json(fdir / "captions.json", caps)
            tb = breaks_table(lang)
            C.atomic_write_csv(tb, tdir / "S_definition_breaks.csv"); outputs.append(str(tdir / "S_definition_breaks.csv"))
            merge_json(tdir / "titles.json", breaks_title(lang))
            log(f"{variant}/{lang}: 6 figures + breaks table in {time.time() - t1:.1f} s (hospital effects: {has_eff})")
    runtime = time.time() - t0
    runlog = dict(module=MODULE, script=SCRIPT, timestamp=datetime.now(timezone.utc).isoformat(), runtime_seconds=round(runtime, 1),
                  variants=VARIANTS, languages=LANGS, outputs=outputs, warnings=sorted(set(WARNINGS)),
                  inputs=["grd_year_summary", "grd_coding_depth_year", "grd_age_sex_year", "grd_hospital_year", "grd_fixed_panel_hospitals", "grd_subcode_year",
                          "coverage_layers_year", "rem20_panel", "rem_pathway_annual", "rem_establishment_year", "deis_year_summary",
                          "ine_population_region_national_year_age_sex", "hospital_effects (optional)", "models_summary (optional)"])
    C.atomic_write_json(runlog, CFG.OUT / "controls" / f"{MODULE}_runlog.json")
    log(f"done in {runtime:.1f} s; {len(outputs)} outputs; warnings: {len(set(WARNINGS))}")
    for w in sorted(set(WARNINGS)):
        log(f"warning: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
