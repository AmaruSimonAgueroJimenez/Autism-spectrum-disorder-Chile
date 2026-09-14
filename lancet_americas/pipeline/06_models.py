#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""06_models.py — Modelos preespecificados (analysis_plan.md, «Modelado y sensibilidad») para ambas variantes e idiomas.

Produce, bajo `lancet_americas/outputs/`:
  tidy/models_summary.csv      una fila por modelo: estimando, fuente, variante, outcome, denominador/offset, panel, actividad,
                               posición, covariables, años, n_obs, CPA e IC 95 %, p, dispersión (Pearson), Durbin–Watson,
                               familia del modelo y notas.
  tidy/models_fitted.csv       valores observados (tasa e IC exacto) y ajustados (banda 95 %) por año para cada modelo.
  tidy/hospital_effects.csv    efectos por hospital (efectos fijos cuasi-Poisson e intercepto aleatorio) y tasas 2024 con IC exacto.
  tidy/models_population_rates.csv, tidy/models_a05_standardised_rates.csv, tidy/models_convergence_index.csv
  <variante>/<idioma>/tables/*.csv (+ *_numeric.csv, titles.json) y <variante>/<idioma>/figures/*.png (+ captions.json):
                               dos láminas por variante e idioma, `figS4_models_cpa` y `figS7_rem_education_models`.
  controls/06_models_controls.csv y controls/06_models_run_log.json

La heterogeneidad entre hospitales NO se dibuja aquí. Este módulo escribía además `figS3_hospital_effects.png`, una
lámina apaisada de 434,6 × 277,0 mm con rejilla 2 × 3 y letras de panel en mayúscula que ningún documento incrustaba:
el registro asigna la Figura S3 a `figS3_grd_hospital_effects` (08a_figures_grd.py), y sus seis paneles ya estaban
todos publicados —los efectos fijos, la contracción del intercepto aleatorio, la tasa frente a la profundidad y la
dispersión anual son los paneles (a)-(d) de esa Figura S3; el bosque de CPA hospital-año es el panel (c) de la
Figura S4 de este módulo; y el orden de hospitales de 2024 está en `figS3_grd_hospital_effects` (e, f) y en la tabla
`S_hospital_rates_2024`—. Se dejó de producir en la fase 4f: era la única lámina que el verificador de composición
suspendía y su nombre casi idéntico invitaba a coger el archivo equivocado. `hospital_effects.csv` (abajo) sigue
siendo la fuente de esos paneles.

Especificaciones (todas descriptivas; ninguna estima un efecto causal de la Ley 21.545):
  1. GRD: episodios con F84 documentado (cualquier posición; principal) por 100.000 episodios GRD — cuasi-Poisson log-lineal con
     offset log(episodios), 2019–2024 y 2021–2024, panel observado y fijo de 65, toda modalidad y hospitalización estricta,
     con/sin profundidad diagnóstica media y con indicador de disrupción del reporte 2020–2021 (no causal).
  2. Hospital-año: cuasi-Poisson con efectos fijos de hospital y tendencia anual (offset log(episodios)), EE robustos por hospital,
     e intercepto aleatorio Poisson (PoissonBayesMixedGLM con offset añadido por subclase; Laplace/MAP y VB) como sensibilidad,
     con dispersión de Pearson condicional a los efectos aleatorios (n − p − 1, solo diagnóstica) y DW dentro de hospital;
     tabla caterpillar 2024 con IC exacto.
  3. GRD por 100.000 habitantes (INE base 2017, nacional): tasas brutas y estandarizadas OMS por año y sexo, CPA bruto y ajustado por edad.
  4. REM A05 ingresos por autismo 2021–2025 (estricto y familia por variante): CPA con offset log(población INE), sensibilidad con
     offset log(establecimientos reportantes) y panel estable; tasas estandarizadas por edad y sexo.
  5. Stocks REM P2 (diciembre 2019–2025) y P6 (diciembre 2021–2025): crecimiento log-lineal con/sin offset log(establecimientos);
     P2 por 100 NANEAS 2023–2025; junio solo como sensibilidad.
  6. PIE armonizado 2019–2025: crecimiento log-lineal.  7. DEIS F84 principal por 100.000 egresos (comprobación externa).
  8. Índices de convergencia (primer año común = 100), rotulados como índices.

Ejecución: `python3 lancet_americas/pipeline/06_models.py` desde la raíz del repositorio. No modifica config.py/common.py/labels.py.
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.genmod.bayes_mixed_glm import PoissonBayesMixedGLM

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
from common import AGE_GROUPS, direct_standardization  # noqa: E402

MODULE = "06_models"
SCRIPT = "lancet_americas/pipeline/06_models.py"
Z = float(stats.norm.ppf(0.975))
PER = 100_000.0
VARIANTS = ["con_rett", "sin_rett"]
STRICT_GRD = "strict_autism_f840"     # F84.0 only (identical in both variants)
STRICT_REM = "strict_autism"          # 05990022 / P6241010 / P6241060 (identical in both variants)
BOTH = "both"                         # series that do not depend on the Rett choice (P2, education)
LANGS = CFG.LANGUAGES
DISRUPTION_YEARS = tuple(CFG.PANDEMIC_YEARS)
LAW_YEAR = CFG.LAW_YEAR
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Rótulos bilingües (todas las cadenas visibles en tablas y láminas)
# ---------------------------------------------------------------------------
LBL = {
    "year": {"es": "Año", "en": "Year"},
    "estimand": {"es": "Estimando", "en": "Estimand"},
    "source": {"es": "Fuente", "en": "Source"},
    "variant": {"es": "Variante", "en": "Variant"},
    "outcome": {"es": "Desenlace (numerador)", "en": "Outcome (numerator)"},
    "offset": {"es": "Denominador / offset", "en": "Denominator / offset"},
    "panel": {"es": "Panel", "en": "Panel"},
    "activity": {"es": "Modalidad", "en": "Activity"},
    "position": {"es": "Posición del código", "en": "Code position"},
    "covariates": {"es": "Covariables", "en": "Covariates"},
    "years": {"es": "Años", "en": "Years"},
    "n_obs": {"es": "n (obs.)", "en": "n (obs.)"},
    "apc_ci": {"es": "CPA % (IC 95 %)", "en": "APC % (95% CI)"},
    "apc_axis": {"es": "Cambio porcentual anual (%) e IC 95 %", "en": "Annual percent change (%) and 95% CI"},
    "p": {"es": "Valor p (Wald)", "en": "p value (Wald)"},
    "dispersion": {"es": "Dispersión (Pearson χ²/gl)", "en": "Dispersion (Pearson χ²/df)"},
    "dw": {"es": "Durbin–Watson", "en": "Durbin–Watson"},
    "family": {"es": "Familia del modelo", "en": "Model family"},
    "note": {"es": "Nota", "en": "Note"},
    # estimands
    "est_grd_rate": {"es": "GRD: episodios con F84 documentado por 100.000 episodios GRD", "en": "GRD: episodes with documented F84 per 100,000 GRD episodes"},
    "est_grd_hospital": {"es": "GRD hospital-año: tendencia con efectos de hospital", "en": "GRD hospital-year: trend with hospital effects"},
    "est_grd_pop": {"es": "GRD: episodios con F84 documentado por 100.000 habitantes (INE base 2017)", "en": "GRD: episodes with documented F84 per 100,000 population (INE base 2017)"},
    "est_a05": {"es": "REM A05: ingresos a salud mental por autismo", "en": "REM A05: mental-health programme entries for autism"},
    "est_a05_exit": {"es": "REM A05: egresos (altas) de salud mental por autismo", "en": "REM A05: mental-health programme exits for autism"},
    "est_a05_pop": {"es": "REM A05: ingresos por autismo por 100.000 habitantes (INE)", "en": "REM A05: autism entries per 100,000 population (INE)"},
    "est_p2": {"es": "REM P2: población NANEAS con TEA bajo control (diciembre)", "en": "REM P2: NANEAS population with ASD under control (December)"},
    "est_p2_june": {"es": "REM P2: TEA bajo control (junio, sensibilidad)", "en": "REM P2: ASD under control (June, sensitivity)"},
    "est_p2_naneas": {"es": "REM P2: TEA por 100 NANEAS bajo control (diciembre)", "en": "REM P2: ASD per 100 NANEAS under control (December)"},
    "est_p6_primary": {"es": "REM P6 APS: población bajo control por autismo (diciembre)", "en": "REM P6 primary care: population under control for autism (December)"},
    "est_p6_specialty": {"es": "REM P6 especialidad: población bajo control por autismo (diciembre)", "en": "REM P6 specialty: population under control for autism (December)"},
    "est_pie": {"es": "PIE: estudiantes con TEA (stock escolar anual)", "en": "PIE: students with ASD (annual school stock)"},
    "est_deis": {"es": "DEIS: egresos con F84 principal por 100.000 egresos", "en": "DEIS: discharges with F84 principal per 100,000 discharges"},
    # sources
    "src_grd": {"es": "GRD público 2019–2024", "en": "Public GRD 2019–2024"},
    "src_a05": {"es": "REM A05 2021–2025", "en": "REM A05 2021–2025"},
    "src_p2": {"es": "REM P2 2019–2025", "en": "REM P2 2019–2025"},
    "src_p6": {"es": "REM P6 2021–2025", "en": "REM P6 2021–2025"},
    "src_pie": {"es": "MINEDUC PIE (Apuntes 60) / SINACES", "en": "MINEDUC PIE (Apuntes 60) / SINACES"},
    "src_deis": {"es": "DEIS egresos hospitalarios 2019–2024", "en": "DEIS hospital discharges 2019–2024"},
    # variants
    "var_con_rett": {"es": "F84 completo (con Rett)", "en": "Full F84 (with Rett)"},
    "var_sin_rett": {"es": "F84 sin Rett", "en": "F84 without Rett"},
    "var_strict_autism_f840": {"es": "Solo F84.0 (idéntico en ambas variantes)", "en": "F84.0 only (identical in both variants)"},
    "var_strict_autism": {"es": "Autismo estricto REM (idéntico en ambas variantes)", "en": "Strict REM autism (identical in both variants)"},
    "var_both": {"es": "No depende de Rett (idéntico)", "en": "Independent of Rett (identical)"},
    "var_family": {"es": "Familia TGD por variante", "en": "PDD family by variant"},
    # outcomes
    "out_f84_any": {"es": "Episodios con F84 en cualquier posición", "en": "Episodes with F84 in any position"},
    "out_f84_principal": {"es": "Episodios con F84 principal", "en": "Episodes with F84 as principal diagnosis"},
    "out_entries": {"es": "Ingresos reportados", "en": "Entries reported"},
    "out_exits": {"es": "Egresos reportados", "en": "Exits reported"},
    "out_stock": {"es": "Personas bajo control (stock de diciembre)", "en": "People under control (December stock)"},
    "out_stock_june": {"es": "Personas bajo control (stock de junio)", "en": "People under control (June stock)"},
    "out_stock_stable": {"es": "Stock de diciembre, panel estable", "en": "December stock, stable panel"},
    "out_entries_stable": {"es": "Ingresos, panel estable", "en": "Entries, stable panel"},
    "out_pie_harmonised": {"es": "PIE TEA + TEA-Asperger (armonizado)", "en": "PIE ASD + ASD-Asperger (harmonised)"},
    "out_pie_strict": {"es": "PIE TEA estricto", "en": "PIE strict ASD"},
    "out_pie_asperger": {"es": "PIE TEA-Asperger", "en": "PIE ASD-Asperger"},
    "out_deis_principal": {"es": "Egresos con F84 en DIAG1 (principal)", "en": "Discharges with F84 in DIAG1 (principal)"},
    # offsets
    "off_episodes": {"es": "log(episodios GRD del mismo panel y modalidad)", "en": "log(GRD episodes, same panel and activity)"},
    "off_hosp_episodes": {"es": "log(episodios del hospital-año)", "en": "log(hospital-year episodes)"},
    "off_pop": {"es": "log(población INE base 2017)", "en": "log(INE population, base 2017)"},
    "off_estab": {"es": "log(establecimientos reportantes)", "en": "log(reporting establishments)"},
    "off_none": {"es": "Ninguno (conteo)", "en": "None (count)"},
    "off_naneas": {"es": "log(NANEAS total bajo control)", "en": "log(total NANEAS under control)"},
    "off_discharges": {"es": "log(egresos DEIS)", "en": "log(DEIS discharges)"},
    # panels / activity / position
    "panel_observed": {"es": "Panel anual observado", "en": "Observed annual panel"},
    "panel_fixed65": {"es": "Panel fijo de 65 hospitales", "en": "Fixed panel of 65 hospitals"},
    "panel_all_estab": {"es": "Todos los establecimientos reportantes", "en": "All reporting establishments"},
    "panel_stable": {"es": "Panel estable (reporta en todos los años de la era)", "en": "Stable panel (reports in every year of the era)"},
    "panel_national": {"es": "Nacional", "en": "National"},
    "panel_na": {"es": "—", "en": "—"},
    "act_all": {"es": "Toda modalidad", "en": "All activity"},
    "act_hospitalisation": {"es": "Hospitalización estricta", "en": "Strict hospitalisation"},
    "act_na": {"es": "—", "en": "—"},
    "pos_any": {"es": "Cualquier posición", "en": "Any position"},
    "pos_principal": {"es": "Principal", "en": "Principal"},
    "pos_na": {"es": "—", "en": "—"},
    # covariates
    "cov_none": {"es": "Sin covariables", "en": "No covariates"},
    "cov_depth": {"es": "Profundidad diagnóstica media (centrada)", "en": "Mean coding depth (centred)"},
    "cov_disruption": {"es": "Indicador de disrupción del reporte 2020–2021", "en": "2020–2021 reporting-disruption indicator"},
    "cov_depth_disruption": {"es": "Profundidad media + indicador de disrupción 2020–2021", "en": "Mean coding depth + 2020–2021 disruption indicator"},
    "cov_hospital_fe": {"es": "Efectos fijos de hospital", "en": "Hospital fixed effects"},
    "cov_hospital_fe_depth": {"es": "Efectos fijos de hospital + profundidad del hospital-año", "en": "Hospital fixed effects + hospital-year coding depth"},
    "cov_hospital_fe_disruption": {"es": "Efectos fijos de hospital + indicador 2020–2021", "en": "Hospital fixed effects + 2020–2021 indicator"},
    "cov_hospital_ri": {"es": "Intercepto aleatorio de hospital", "en": "Hospital random intercept"},
    "cov_hospital_ri_depth": {"es": "Intercepto aleatorio de hospital + profundidad", "en": "Hospital random intercept + coding depth"},
    "cov_age": {"es": "Efectos fijos de grupo de edad (ajuste por edad)", "en": "Age-group fixed effects (age adjustment)"},
    "cov_age_sex": {"es": "Efectos fijos de edad y sexo", "en": "Age-group and sex fixed effects"},
    "cov_disruption_2021": {"es": "Indicador de disrupción 2021", "en": "2021 disruption indicator"},
    # families
    "fam_qp": {"es": "Cuasi-Poisson log-lineal", "en": "Quasi-Poisson log-linear"},
    "fam_qp_stock": {"es": "Cuasi-Poisson log-lineal (crecimiento de stock)", "en": "Quasi-Poisson log-linear (stock growth)"},
    "fam_poisson_sat": {"es": "Poisson (modelo saturado; dispersión no estimable)", "en": "Poisson (saturated model; dispersion not estimable)"},
    "fam_qp_fe": {"es": "Cuasi-Poisson con efectos fijos de hospital", "en": "Quasi-Poisson with hospital fixed effects"},
    "fam_qp_fe_cluster": {"es": "Cuasi-Poisson, efectos fijos, EE robustos por hospital", "en": "Quasi-Poisson, fixed effects, hospital-clustered SE"},
    "fam_ri_map": {"es": "Poisson con intercepto aleatorio (Laplace/MAP)", "en": "Poisson random intercept (Laplace/MAP)"},
    "fam_ri_vb": {"es": "Poisson con intercepto aleatorio (Bayes variacional)", "en": "Poisson random intercept (variational Bayes)"},
    "fam_qp_age": {"es": "Cuasi-Poisson con efectos de edad (CPA ajustado)", "en": "Quasi-Poisson with age effects (adjusted APC)"},
    # sexes
    "HOMBRE": {"es": "Hombres", "en": "Males"},
    "MUJER": {"es": "Mujeres", "en": "Females"},
    "TOTAL": {"es": "Ambos sexos", "en": "Both sexes"},
    "sex": {"es": "Sexo", "en": "Sex"},
    # table columns (rates)
    "count": {"es": "Episodios", "en": "Episodes"},
    "count_entries": {"es": "Ingresos", "en": "Entries"},
    "unknown": {"es": "Sin edad/sexo válido (solo en tasa bruta)", "en": "Unknown age/sex (crude rate only)"},
    "population": {"es": "Población INE (30 de junio)", "en": "INE population (30 June)"},
    "crude": {"es": "Tasa bruta por 100.000 (IC 95 %)", "en": "Crude rate per 100,000 (95% CI)"},
    "asr": {"es": "Tasa estandarizada OMS por 100.000 (IC 95 %)", "en": "WHO age-standardised rate per 100,000 (95% CI)"},
    "estab": {"es": "Establecimientos reportantes", "en": "Reporting establishments"},
    "hospitals": {"es": "Hospitales", "en": "Hospitals"},
    "series": {"es": "Serie", "en": "Series"},
    "index": {"es": "Índice (2021 = 100)", "en": "Index (2021 = 100)"},
    "index2019": {"es": "Índice (2019 = 100)", "en": "Index (2019 = 100)"},
    "value": {"es": "Valor", "en": "Value"},
    "unit": {"es": "Unidad", "en": "Unit"},
    "hospital": {"es": "Hospital", "en": "Hospital"},
    "code": {"es": "Código", "en": "Code"},
    "fixed_member": {"es": "Panel fijo de 65", "en": "Fixed panel of 65"},
    "episodes_total": {"es": "Episodios GRD 2024", "en": "GRD episodes 2024"},
    "f84_2024": {"es": "Episodios con F84 2024", "en": "Episodes with F84 2024"},
    "rate_2024": {"es": "Tasa por 100.000 episodios (IC 95 % exacto)", "en": "Rate per 100,000 episodes (exact 95% CI)"},
    "depth_2024": {"es": "Profundidad diagnóstica media 2024", "en": "Mean coding depth 2024"},
    "rr_fe": {"es": "RR efecto fijo 2019–2024 frente a la media de hospitales (IC 95 %)", "en": "Fixed-effect RR 2019–2024 vs hospital mean (95% CI)"},
    "rr_fe_depth": {"es": "RR efecto fijo ajustado por profundidad (IC 95 %)", "en": "Depth-adjusted fixed-effect RR (95% CI)"},
    "rr_ri": {"es": "RR intercepto aleatorio (IC 95 % a posteriori)", "en": "Random-intercept RR (95% posterior interval)"},
    "yes": {"es": "Sí", "en": "Yes"},
    "no": {"es": "No", "en": "No"},
    "na": {"es": "no disponible", "en": "not available"},
    "per_naneas": {"es": "TEA por 100 NANEAS (IC 95 %)", "en": "ASD per 100 NANEAS (95% CI)"},
    "naneas_total": {"es": "NANEAS total bajo control", "en": "Total NANEAS under control"},
    # figure strings
    "fig_rate_axis": {"es": "Episodios con F84 por 100.000 episodios GRD", "en": "Episodes with F84 per 100,000 GRD episodes"},
    "fig_principal_axis": {"es": "F84 principal por 100.000 episodios / egresos", "en": "Principal F84 per 100,000 episodes / discharges"},
    "fig_pop_axis": {"es": "Episodios con F84 por 100.000 habitantes", "en": "Episodes with F84 per 100,000 population"},
    "fig_a05_axis": {"es": "Ingresos A05 por 100.000 habitantes", "en": "A05 entries per 100,000 population"},
    "fig_obs": {"es": "observado (IC 95 % exacto)", "en": "observed (exact 95% CI)"},
    "fig_fit": {"es": "ajuste cuasi-Poisson (banda 95 %)", "en": "quasi-Poisson fit (95% band)"},
    "fig_pandemic": {"es": "Disrupción del\nreporte 2020–21", "en": "Reporting\ndisruption 2020–21"},
    "fig_law": {"es": "Ley 21.545\n(contexto)", "en": "Law 21.545\n(context)"},
    "fig_any_obs": {"es": "Panel observado", "en": "Observed panel"},
    "fig_any_fixed": {"es": "Panel fijo 65", "en": "Fixed panel 65"},
    "fig_prin_obs": {"es": "GRD, panel observado", "en": "GRD, observed panel"},
    "fig_prin_fixed": {"es": "GRD, panel fijo 65", "en": "GRD, fixed panel 65"},
    "fig_deis_prin": {"es": "DEIS principal", "en": "DEIS principal"},
    "fig_title_a": {"es": "GRD: tasa por episodios (observado y ajuste)", "en": "GRD: episode rate (observed and fitted)"},
    "fig_title_b": {"es": "F84 principal: GRD y DEIS", "en": "Principal F84: GRD and DEIS"},
    "fig_title_c": {"es": "GRD: CPA según sensibilidades (cuasi-Poisson)", "en": "GRD: APC across sensitivities (quasi-Poisson)"},
    "fig_title_d": {"es": "GRD por 100.000 hab.: bruta y estandarizada", "en": "GRD per 100,000 pop.: crude and standardised"},
    "fig_title_f": {"es": "REM, educación y DEIS: CPA (cuasi-Poisson)", "en": "REM, education and DEIS: APC (quasi-Poisson)"},
    "fig_title_e": {"es": "Índices de convergencia (2021 = 100)", "en": "Convergence indices (2021 = 100)"},
    "fig_index_axis": {"es": "Índice (primer año común 2021 = 100; escala log)", "en": "Index (first common year 2021 = 100; log scale)"},
    "fig_index_note": {"es": "Índices, no niveles: cada serie tiene unidad y denominador propios", "en": "Indices, not levels: each series has its own unit and denominator"},
    "fig_grd_estab": {"es": "Año (n = hospitales GRD reportantes)", "en": "Year (n = reporting GRD hospitals)"},
    "crude_short": {"es": "bruta", "en": "crude"},
    "asr_short": {"es": "estandarizada OMS", "en": "WHO-standardised"},
    # REM/education figure
    "rfig_title_a": {"es": "A05 autismo estricto: tasas por 100.000 hab. por sexo", "en": "A05 strict autism: rates per 100,000 pop. by sex"},
    "rfig_title_b": {"es": "A05 familia TGD (variante): tasas por 100.000 hab.", "en": "A05 PDD family (variant): rates per 100,000 pop."},
    "rfig_title_c": {"es": "A05 estricto: tasas por edad y sexo, 2021 y 2025", "en": "A05 strict: rates by age and sex, 2021 and 2025"},
    "rfig_title_d": {"es": "P2 TEA bajo control en diciembre: observado y ajustado", "en": "P2 ASD under control in December: observed and fitted"},
    "rfig_title_e": {"es": "P6 autismo estricto bajo control en diciembre", "en": "P6 strict autism under control in December"},
    "rfig_title_f": {"es": "PIE armonizado: observado y ajustado", "en": "Harmonised PIE: observed and fitted"},
    "rfig_age_axis": {"es": "Grupo de edad (años)", "en": "Age group (years)"},
    "rfig_stock_axis": {"es": "Personas bajo control (diciembre)", "en": "People under control (December)"},
    "rfig_estab_axis": {"es": "Establecimientos reportantes (diciembre)", "en": "Reporting establishments (December)"},
    "rfig_students_axis": {"es": "Estudiantes en PIE con TEA", "en": "PIE students with ASD"},
    "rfig_fit_nooff": {"es": "ajuste log-lineal sin offset", "en": "log-linear fit, no offset"},
    "rfig_fit_off": {"es": "ajuste con offset log(establecimientos)", "en": "fit with log(establishments) offset"},
    "rfig_estab": {"es": "establecimientos reportantes", "en": "reporting establishments"},
    "rfig_june": {"es": "junio (sensibilidad)", "en": "June (sensitivity)"},
    "rfig_stable": {"es": "panel estable", "en": "stable panel"},
    "rfig_primary": {"es": "APS (P6241010)", "en": "Primary care (P6241010)"},
    "rfig_specialty": {"es": "Especialidad (P6241060)", "en": "Specialty (P6241060)"},
    "rfig_source_change": {"es": "cambio de fuente\n(Apuntes 60 → SINACES)", "en": "source change\n(Apuntes 60 → SINACES)"},
    "rfig_source_change_leg": {"es": "cambio de fuente: Apuntes 60 → SINACES", "en": "source change: Apuntes 60 → SINACES"},
    "rfig_a05_estab": {"es": "Año (n = establecimientos A05 reportantes)", "en": "Year (n = A05 reporting establishments)"},
    "rfig_broad_note": {"es": "TGD amplio 2019–2020 excluido (era distinta)", "en": "Broad PDD 2019–2020 excluded (different era)"},
    "figure": {"es": "Figura", "en": "Figure"},
    "table": {"es": "Tabla", "en": "Table"},
}


def tr(key: str, lang: str) -> str:
    if key in LBL:
        return LBL[key][lang]
    raise KeyError(f"Falta rótulo bilingüe: {key}")


# Notas codificadas (traducidas en tablas; texto inglés en el tidy).
NOTES = {
    "dw_weak": {"es": "Durbin–Watson con menos de 8 puntos: prueba débil, solo orientativa.", "en": "Durbin–Watson with fewer than 8 points: weak, indicative only."},
    "saturated": {"es": "Modelo saturado (gl residual 0): dispersión no estimable; EE Poisson.", "en": "Saturated model (0 residual df): dispersion not estimable; Poisson SE."},
    "df1": {"es": "Un solo grado de libertad residual: dispersión muy inestable.", "en": "One residual degree of freedom: dispersion very unstable."},
    "disruption": {"es": "El indicador 2020–2021 describe la disrupción del reporte; no es un efecto causal.", "en": "The 2020–2021 indicator describes reporting disruption; it is not a causal effect."},
    "not_causal_law": {"es": "Ninguna especificación estima un efecto de la Ley 21.545.", "en": "No specification estimates an effect of Law 21.545."},
    "stable_panel": {"es": "Panel estable: establecimientos con fila para el código en todos los años de la era.", "en": "Stable panel: establishments with a row for the code in every year of the era."},
    "estab_offset": {"es": "Offset log(establecimientos reportantes): tasa por establecimiento, no cobertura poblacional.", "en": "Offset log(reporting establishments): per-establishment rate, not population coverage."},
    "place_vs_residence": {"es": "Numerador por lugar de atención (red pública) y denominador por residencia (INE): lectura complementaria, no prevalencia.", "en": "Numerator by place of care (public network) and denominator by residence (INE): complementary reading, not prevalence."},
    "stock": {"es": "Stock semestral de diciembre; junio nunca se suma; crecimiento log-lineal descriptivo.", "en": "December semi-annual stock; June is never summed; descriptive log-linear growth."},
    "june": {"es": "Sensibilidad con el stock de junio (2020 con 28 establecimientos: disrupción).", "en": "Sensitivity with the June stock (2020 with 28 establishments: disruption)."},
    "naneas": {"es": "NANEAS total disponible solo desde diciembre de 2023: 3 puntos.", "en": "Total NANEAS available only from December 2023: 3 points."},
    "pie_source": {"es": "2019–2023 Apuntes 60 (suma de categorías; 2022 = 42.940 por regla explícita); 2024–2025 SINACES.", "en": "2019–2023 Apuntes 60 (category sum; 2022 = 42,940 by explicit rule); 2024–2025 SINACES."},
    "deis_principal": {"es": "DEIS solo publica DIAG1 (DIAG2 es causa externa): F84 'cualquier posición' = principal; comparar solo con GRD principal.", "en": "DEIS publishes DIAG1 only (DIAG2 is external cause): 'any position' = principal; compare only with GRD principal."},
    "a05_2025": {"es": "En 2025 reportan menos establecimientos A05 (952 frente a 1.070 en 2024).", "en": "Fewer A05 establishments report in 2025 (952 vs 1,070 in 2024)."},
    "a05_era": {"es": "Era 2021–2025 (códigos de autismo); TGD amplio 2019–2020 no se modela (era distinta).", "en": "Era 2021–2025 (autism codes); broad PDD 2019–2020 not modelled (different era)."},
    "depth": {"es": "Profundidad diagnóstica = media de diagnósticos codificados por episodio (panel y modalidad del modelo).", "en": "Coding depth = mean coded diagnoses per episode (model's panel and activity)."},
    "hospital_fe": {"es": "Efectos fijos de hospital (variables indicadoras); tendencia común; RR frente a la media geométrica de hospitales.", "en": "Hospital fixed effects (indicator variables); common trend; RR vs geometric mean of hospitals."},
    "hospital_dw": {"es": "Durbin–Watson dentro de hospital (pares de años consecutivos).", "en": "Within-hospital Durbin–Watson (consecutive-year pairs)."},
    "cluster": {"es": "EE robustos agrupados por hospital.", "en": "Hospital-clustered robust SE."},
    "ri_ok": {"es": "Intercepto aleatorio Poisson con offset (subclase de PoissonBayesMixedGLM); convergió.", "en": "Poisson random intercept with offset (PoissonBayesMixedGLM subclass); converged."},
    "ri_fail": {"es": "El modelo de intercepto aleatorio no convergió; se informa sin IC.", "en": "Random-intercept model did not converge; reported without CI."},
    "ri_prior": {"es": "Priores: EE fijos N(0, 10²); log-DE del intercepto N(0, 1); offset centrado en la tasa agregada.", "en": "Priors: fixed effects N(0, 10²); log-SD of intercept N(0, 1); offset centred on the pooled rate."},
    "ecological": {"es": "Resultados por hospital descriptivos; sin interpretación ecológica causal.", "en": "Hospital-level results are descriptive; no causal ecological interpretation."},
    "unknown_excluded": {"es": "Episodios sin edad o sexo válido excluidos de la tasa estandarizada (incluidos en la bruta).", "en": "Episodes without valid age or sex excluded from the standardised rate (included in the crude rate)."},
    "age_adj": {"es": "CPA ajustado: conteos por edad (y sexo) con efectos fijos de estrato y offset log(población).", "en": "Adjusted APC: counts by age (and sex) with stratum fixed effects and log(population) offset."},
    "a05_cells": {"es": "Numerador = suma de celdas edad × sexo (puede diferir ≤1 del total COL01).", "en": "Numerator = sum of age × sex cells (may differ by ≤1 from the COL01 total)."},
    "principal_small": {"es": "Numerador pequeño (F84 principal): IC amplios.", "en": "Small numerator (principal F84): wide CI."},
    "index": {"es": "Índices (primer año común = 100), no niveles comparables entre fuentes.", "en": "Indices (first common year = 100), not comparable levels across sources."},
    "strict_identical": {"es": "Serie idéntica en ambas variantes.", "en": "Series identical in both variants."},
    "ri_poisson": {"es": "Verosimilitud Poisson sin parámetro de sobredispersión: IC más estrecho que el cuasi-Poisson; la dispersión mostrada es el χ² de Pearson condicional a los efectos aleatorios (MAP) / (n − p − 1), solo diagnóstica; leer como sensibilidad.",
                   "en": "Poisson likelihood without a dispersion parameter: narrower CI than quasi-Poisson; the dispersion shown is the Pearson χ² conditional on the random effects (MAP) / (n − p − 1), diagnostic only; read as sensitivity."},
}


def note_text(keys: list[str], lang: str) -> str:
    return " ".join(NOTES[k][lang] for k in keys if k in NOTES)


# ---------------------------------------------------------------------------
# Estadística: cuasi-Poisson, bandas, Durbin–Watson, intercepto aleatorio con offset
# ---------------------------------------------------------------------------
def durbin_watson(resid, groups=None) -> float:
    """DW = Σ(e_t − e_{t−1})² / Σe²; con `groups` solo pares consecutivos dentro del mismo grupo."""
    e = np.asarray(resid, dtype=float)
    if len(e) < 3 or not np.isfinite(e).all() or np.sum(e ** 2) == 0:
        return np.nan
    if groups is None:
        return float(np.sum(np.diff(e) ** 2) / np.sum(e ** 2))
    g = np.asarray(groups)
    same = g[1:] == g[:-1]
    if same.sum() == 0:
        return np.nan
    return float(np.sum((e[1:] - e[:-1])[same] ** 2) / np.sum(e ** 2))


def fit_glm(y, X: pd.DataFrame, offset=None, cluster=None):
    """GLM Poisson; escala de Pearson (cuasi-Poisson) si hay gl residuales; opcionalmente EE agrupados."""
    y = np.asarray(y, dtype=float)
    off = None if offset is None else np.asarray(offset, dtype=float)
    model = sm.GLM(y, X, family=sm.families.Poisson(), offset=off)
    df_resid = len(y) - X.shape[1]
    kw = {}
    if cluster is not None:
        kw = dict(cov_type="cluster", cov_kwds={"groups": pd.factorize(np.asarray(cluster))[0]})
    fit = model.fit(scale="X2", **kw) if df_resid > 0 else model.fit(**kw)
    return fit, df_resid


def term_summary(fit, term: str) -> dict:
    beta, se = float(fit.params[term]), float(fit.bse[term])
    return dict(beta=beta, se=se, apc=100 * (np.exp(beta) - 1), apc_lo=100 * (np.exp(beta - Z * se) - 1),
                apc_hi=100 * (np.exp(beta + Z * se) - 1), p_value=float(fit.pvalues[term]))


def fitted_band(fit, X: pd.DataFrame, offset, per: float) -> pd.DataFrame:
    """Tasa ajustada por `per` unidades del denominador con banda 95 % (delta en escala log)."""
    Xv = np.asarray(X, dtype=float)
    V = np.asarray(fit.cov_params(), dtype=float)
    lp = Xv @ np.asarray(fit.params, dtype=float)
    se = np.sqrt(np.einsum("ij,jk,ik->i", Xv, V, Xv))
    off = np.zeros(len(lp)) if offset is None else np.asarray(offset, dtype=float)
    return pd.DataFrame({"fitted_rate": per * np.exp(lp), "fitted_lo": per * np.exp(lp - Z * se), "fitted_hi": per * np.exp(lp + Z * se),
                         "fitted_count": np.exp(lp + off)})


class Store:
    """Acumula filas de resumen, ajustes y efectos por hospital."""

    def __init__(self):
        self.summary, self.fitted, self.hosp = [], [], []

    def add_trend(self, model_id, years, counts, offsets, covariates: dict | None, per: float, meta: dict, note_keys: list[str],
                  term="t", cluster=None, extra: dict | None = None, offsets_label=None):
        years = np.asarray(years, dtype=int)
        y = np.asarray(counts, dtype=float)
        t = (years - years.min()).astype(float)
        X = pd.DataFrame({"const": 1.0, "t": t})
        if covariates:
            for k, v in covariates.items():
                X[k] = np.asarray(v, dtype=float)
        off = None if offsets is None else np.log(np.asarray(offsets, dtype=float))
        fit, df_resid = fit_glm(y, X, off, cluster)
        ts = term_summary(fit, term)
        notes = list(note_keys)
        if df_resid == 0:
            notes.insert(0, "saturated")
        elif df_resid == 1:
            notes.insert(0, "df1")
        if len(y) < 8:
            notes.append("dw_weak")
        dispersion = float(fit.pearson_chi2 / df_resid) if df_resid > 0 else np.nan
        family = meta.get("model_family", "fam_qp")
        if df_resid == 0:
            family = "fam_poisson_sat"
        row = dict(model_id=model_id, **{k: v for k, v in meta.items() if k != "model_family"}, model_family=family,
                   years=f"{years.min()}-{years.max()}", n_obs=int(len(y)), df_resid=int(df_resid), apc=ts["apc"], apc_lo=ts["apc_lo"],
                   apc_hi=ts["apc_hi"], p_value=ts["p_value"], beta=ts["beta"], se=ts["se"], dispersion=dispersion,
                   durbin_watson=durbin_watson(fit.resid_deviance), dw_check="deviance residuals, chronological",
                   converged=bool(getattr(fit, "converged", True)), note_keys="|".join(notes), note=note_text(notes, "en"))
        if extra:
            row.update(extra)
        self.summary.append(row)
        band = fitted_band(fit, X, off, per)
        den = np.ones(len(y)) if offsets is None else np.asarray(offsets, dtype=float)
        lo, hi = C.poisson_limits(y)
        for i, yr in enumerate(years):
            self.fitted.append(dict(model_id=model_id, variant=meta.get("variant"), estimand=meta.get("estimand"), year=int(yr), observed_count=float(y[i]),
                                    denominator=float(den[i]), per=per, observed_rate=per * y[i] / den[i], observed_lo=per * lo[i] / den[i],
                                    observed_hi=per * hi[i] / den[i], fitted_rate=float(band.fitted_rate[i]), fitted_lo=float(band.fitted_lo[i]),
                                    fitted_hi=float(band.fitted_hi[i]), fitted_count=float(band.fitted_count[i]),
                                    reporting_n=(None if offsets_label is None else float(offsets_label[i]))))
        return fit, row


class PoissonBayesMixedGLMOffset(PoissonBayesMixedGLM):
    """PoissonBayesMixedGLM con offset conocido en el predictor lineal (statsmodels 0.14 no lo admite).

    Además FIJA el punto de partida del optimizador. `_BayesMixedGLM._get_start` de statsmodels 0.14 arranca
    los efectos aleatorios en `np.random.normal(size=k_vc)` —el generador global de numpy, sin semilla—, y
    como el BFGS de estos ajustes para por fallo de la búsqueda lineal (`success=False`, |grad| ~ 1e-5) y no
    por tolerancia, el punto en el que para depende del arranque: dos ejecuciones del módulo con el MISMO
    código y los MISMOS datos daban `models_summary.csv` y `hospital_effects.csv` distintos en la séptima
    cifra, y con ellos dos láminas publicadas distintas byte a byte. Un artículo cuya tesis es la
    reproducibilidad no puede embarcar eso.
    """

    def __init__(self, endog, exog, exog_vc, ident, offset, **kw):
        super().__init__(endog, exog, exog_vc, ident, **kw)
        self.offset = np.asarray(offset, dtype=float)

    def _get_start(self):
        """Arranque FIJO: efectos fijos en 0, log-DE del componente de varianza en 1, efectos aleatorios en 0.

        Cero es la media a priori de los interceptos aleatorios, de modo que el ajuste parte del modelo sin
        heterogeneidad y la busca en los datos. No hay simetría que romper —cada hospital tiene su propio
        gradiente desde el primer paso—, así que el arranque aleatorio de statsmodels no aportaba nada que
        no aporte éste, y sí quitaba la reproducibilidad.
        """
        return np.concatenate([np.zeros(self.k_fep), np.ones(self.k_vcp), np.zeros(self.k_vc)])

    def _linpred(self, fep, vc):
        lp = self.offset.copy()
        if self.k_fep > 0:
            lp = lp + np.dot(self.exog, fep)
        if self.k_vc > 0:
            lp = lp + self.exog_vc.dot(vc)
        return lp

    def logposterior(self, params):
        fep, vcp, vc = self._unpack(params)
        mu = self.family.link.inverse(self._linpred(fep, vc))
        ll = self.family.loglike(self.endog, mu)
        if self.k_vc > 0:
            vcp0 = vcp[self.ident]
            s = np.exp(vcp0)
            ll -= 0.5 * np.sum(vc ** 2 / s ** 2) + np.sum(vcp0)
            ll -= 0.5 * np.sum(vcp ** 2 / self.vcp_p ** 2)
        if self.k_fep > 0:
            ll -= 0.5 * np.sum(fep ** 2 / self.fe_p ** 2)
        return ll

    def logposterior_grad(self, params):
        fep, vcp, vc = self._unpack(params)
        mu = self.family.link.inverse(self._linpred(fep, vc))
        score_factor = (self.endog - mu) / self.family.link.deriv(mu)
        score_factor /= self.family.variance(mu)
        te = [None, None, None]
        if self.k_fep > 0:
            te[0] = np.dot(score_factor, self.exog)
        if self.k_vc > 0:
            te[2] = self.exog_vc.transpose().dot(score_factor)
            vcp0 = vcp[self.ident]
            s = np.exp(vcp0)
            u = vc ** 2 / s ** 2 - 1
            te[1] = np.bincount(self.ident, weights=u)
            te[2] -= vc / s ** 2
            te[1] -= vcp / self.vcp_p ** 2
        if self.k_fep > 0:
            te[0] -= fep / self.fe_p ** 2
        return np.concatenate([x for x in te if x is not None])

    def _lp_stats(self, fep_mean, fep_sd, vc_mean, vc_sd):
        tm, tv = super()._lp_stats(fep_mean, fep_sd, vc_mean, vc_sd)
        return tm + self.offset, tv


def fit_random_intercept(y, exog: pd.DataFrame, groups, offset_log) -> dict:
    """Intercepto aleatorio Poisson (Laplace/MAP; VB como comprobación). Devuelve efectos fijos, DE del intercepto y efectos por grupo."""
    y = np.asarray(y, dtype=float)
    codes, uniques = pd.factorize(np.asarray(groups))
    exog_vc = np.zeros((len(y), len(uniques)))
    exog_vc[np.arange(len(y)), codes] = 1.0
    centre = float(np.log(y.sum()) - np.log(np.exp(np.asarray(offset_log, dtype=float)).sum()))
    off = np.asarray(offset_log, dtype=float) + centre
    out = dict(converged=False, method="fam_ri_map", message="")
    model = PoissonBayesMixedGLMOffset(y, exog.to_numpy(dtype=float), exog_vc, np.zeros(len(uniques), dtype=int), off,
                                       fe_p=10.0, vcp_p=1.0, fep_names=list(exog.columns), vcp_names=["hospital"], vc_names=[str(u) for u in uniques])
    res = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = model.fit_map(minim_opts={"maxiter": 5000, "gtol": 1e-6})
            grad = np.sqrt(np.sum(model.logposterior_grad(res.params) ** 2))
            ok = bool(res.optim_retvals.success) or grad < 1e-3
            out.update(converged=ok, message=f"MAP: success={res.optim_retvals.success}, |grad|={grad:.2e}, iterations={res.optim_retvals.nit}")
        except Exception as exc:  # noqa: BLE001
            out.update(message=f"MAP failed: {exc}")
        if res is None or not out["converged"]:
            try:
                res_vb = model.fit_vb(minim_opts={"maxiter": 5000})
                res = res_vb
                out.update(converged=True, method="fam_ri_vb", message=out["message"] + " | VB used as fallback")
            except Exception as exc:  # noqa: BLE001
                out.update(message=out["message"] + f" | VB failed: {exc}")
    if res is None:
        return out
    fep, vcp, vc = model._unpack(np.asarray(res.params, dtype=float))
    fe_sd, vcp_sd, vc_sd = res.fe_sd, res.vcp_sd, res.vc_sd
    # Diagnóstico de sobredispersión condicional a los efectos aleatorios (estimaciones MAP): χ² de Pearson / (n − p − 1),
    # convención de lme4 (gl residuales = n − efectos fijos − componentes de varianza). La verosimilitud Poisson no tiene
    # parámetro de dispersión: el valor solo indica cuánta sobredispersión no absorbe el intercepto aleatorio.
    mu = np.exp(model._linpred(fep, vc))
    pearson = float(np.sum((y - mu) ** 2 / mu))
    df_cond = int(len(y) - (len(fep) + 1))
    out.update(pearson_chi2=pearson, df_cond=df_cond, dispersion_cond=(pearson / df_cond if df_cond > 0 else np.nan),
               resid_deviance=np.asarray(sm.families.Poisson().resid_dev(y, mu), dtype=float))
    out.update(fep=dict(zip(exog.columns, fep)), fe_sd=dict(zip(exog.columns, fe_sd)), intercept_centre=centre,
               re_sd=float(np.exp(vcp[0])), re_sd_lo=float(np.exp(vcp[0] - Z * vcp_sd[0])), re_sd_hi=float(np.exp(vcp[0] + Z * vcp_sd[0])),
               effects=pd.DataFrame({"group": uniques, "re_mean": vc, "re_sd": vc_sd}))
    return out


def merge_json(path: Path, new: dict) -> None:
    """Combina con el JSON existente (otros módulos escriben en el mismo archivo)."""
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


def status_of(expected, observed, tol_rel=0.005, tol_abs=0.0):
    try:
        e, o = float(expected), float(observed)
    except (TypeError, ValueError):
        return ("ok" if str(expected) == str(observed) else "differs"), np.nan, np.nan
    if np.isnan(o):
        return "differs", np.nan, np.nan
    diff = o - e
    rel = diff / e if e != 0 else (0.0 if diff == 0 else np.inf)
    ok = abs(diff) <= tol_abs or abs(rel) <= tol_rel
    return ("ok" if ok else "differs"), diff, rel


class Controls:
    def __init__(self):
        self.rows = []

    def add(self, name, key, expected, observed, note="", tol_rel=0.005, tol_abs=0.0):
        st, diff, rel = status_of(expected, observed, tol_rel, tol_abs)
        self.rows.append(dict(name=name, key=str(key), expected=expected, observed=observed, abs_diff=diff, rel_diff=rel, status=st, note=note))

    def frame(self):
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"])


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def load_data(ctl: Controls) -> dict:
    D = {}
    D["grd"] = C.read_tidy("grd_year_summary")
    D["grd_hosp"] = C.read_tidy("grd_hospital_year")
    D["grd_age"] = C.read_tidy("grd_age_sex_year")
    ine = C.read_tidy("ine_population_region_national_year_age_sex")
    ine = ine[(ine.level == "national") & (ine.population_base == "base2017") & (ine.age_group != "TOTAL")]
    D["ine_age"] = ine[["year", "sex", "age_group", "population"]].copy()
    D["ine_total"] = ine.groupby(["year", "sex"]).population.sum()
    D["rem"] = C.read_tidy("rem_pathway_annual", dtype={"code": str})
    D["a05_age"] = C.read_tidy("rem_a05_age_sex_annual", dtype={"code": str})
    deis = C.read_tidy("deis_year_summary")
    D["deis"] = deis[deis.source_layout == "canonical"].copy()
    D["edu"] = C.read_tidy("education_summary_year")
    for yr, exp in CFG.CONTROLS["ine_population_national"].items():
        ctl.add("ine_population_national", yr, exp, int(D["ine_total"].loc[(yr, "TOTAL")]), "INE base 2017, national, 30 June (sum of age groups)")
    g = D["grd"]
    base = g[(g.variant == "con_rett") & (g.panel == "observed") & (g.activity == "all") & (g.position == "any")].set_index("year")
    for yr, exp in CFG.CONTROLS["grd_f84_any"].items():
        ctl.add("grd_f84_any_used_in_models", yr, exp, int(base.loc[yr, "n_episodes_f84"]), "numerator of the primary GRD model")
    for yr, exp in CFG.CONTROLS["grd_records_total"].items():
        ctl.add("grd_records_total_used_as_offset", yr, exp, int(base.loc[yr, "n_episodes_total_same_panel_activity"]), "offset of the primary GRD model")
    a05 = D["rem"][(D["rem"].module == "A05") & (D["rem"].variant == STRICT_REM) & (D["rem"].code == CFG.STRICT["a05_entry"])].set_index("year")
    for yr, exp in CFG.CONTROLS["a05_autism_entries"].items():
        ctl.add("a05_autism_entries_used_in_models", yr, exp, int(a05.loc[yr, "total"]), "numerator of the A05 strict model")
    p2 = D["rem"][(D["rem"].module == "P2") & (D["rem"].code == CFG.P2_TEA) & (D["rem"].measure == "december_stock")].set_index("year")
    for yr, exp in CFG.CONTROLS["p2_tea_december"].items():
        ctl.add("p2_tea_december_used_in_models", yr, exp, int(p2.loc[yr, "total"]), "P2 December stock modelled")
    for yr, exp in CFG.CONTROLS["p2_establishments_december"].items():
        ctl.add("p2_establishments_december_offset", yr, exp, int(p2.loc[yr, "n_reporting_establishments"]), "P2 establishments used as offset")
    edu = D["edu"].set_index("year")
    for yr, exp in CFG.CONTROLS["pie_harmonised"].items():
        ctl.add("pie_harmonised_used_in_models", yr, exp, int(edu.loc[yr, "pie_harmonised_n"]), "PIE harmonised series modelled")
    return D


def grd_meta(variant, panel, activity, position, cov, offset_key="off_episodes", estimand="est_grd_rate"):
    return dict(estimand=estimand, source="src_grd", variant=variant,
                outcome="out_f84_any" if position == "any" else "out_f84_principal", denominator_offset=offset_key,
                panel=f"panel_{panel}", activity=f"act_{activity}", position=f"pos_{position}", covariates=f"cov_{cov}")


# ---------------------------------------------------------------------------
# 1. GRD: tasas por episodios (nacional)
# ---------------------------------------------------------------------------
def grd_models(D: dict, S: Store, ctl: Controls) -> None:
    g = D["grd"]
    n = 0
    for variant in VARIANTS + [STRICT_GRD]:
        for panel in ["observed", "fixed65"]:
            for activity in ["all", "hospitalisation"]:
                for position in ["any", "principal"]:
                    sub = g[(g.variant == variant) & (g.panel == panel) & (g.activity == activity) & (g.position == position)].sort_values("year")
                    for y0, y1 in [(2019, 2024), (2021, 2024)]:
                        s = sub[(sub.year >= y0) & (sub.year <= y1)]
                        covsets = ["none", "depth", "disruption", "depth_disruption"] if y0 == 2019 else ["none", "depth"]
                        for cs in covsets:
                            cov, notes = {}, ["not_causal_law"]
                            if "depth" in cs:
                                cov["depth"] = s.coding_depth_mean_all.values - s.coding_depth_mean_all.mean()
                                notes.append("depth")
                            if "disruption" in cs:
                                cov["disruption"] = s.year.isin(DISRUPTION_YEARS).astype(float).values
                                notes.append("disruption")
                            if position == "principal":
                                notes.append("principal_small")
                            if variant == STRICT_GRD:
                                notes.append("strict_identical")
                            mid = f"grd_rate:{variant}:{panel}:{activity}:{position}:{cs}:{y0}-{y1}"
                            S.add_trend(mid, s.year.values, s.n_episodes_f84.values, s.n_episodes_total_same_panel_activity.values, cov or None, PER,
                                        grd_meta(variant, panel, activity, position, cs), notes, offsets_label=s.hospitals_n.values,
                                        extra=dict(hospitals_first=int(s.hospitals_n.iloc[0]), hospitals_last=int(s.hospitals_n.iloc[-1])))
                            n += 1
    # Control: la CPA del modelo primario coincide con common.quasi_poisson_trend
    base = g[(g.variant == "con_rett") & (g.panel == "observed") & (g.activity == "all") & (g.position == "any")].sort_values("year")
    ref = C.quasi_poisson_trend(base.year.values, base.n_episodes_f84.values, base.n_episodes_total_same_panel_activity.values)
    mine = next(r for r in S.summary if r["model_id"] == "grd_rate:con_rett:observed:all:any:none:2019-2024")
    ctl.add("apc_matches_common_quasi_poisson_trend", "grd any observed all 2019-2024", round(ref["apc"], 6), round(mine["apc"], 6), "same GLM specification", tol_rel=1e-6)
    ctl.add("dispersion_matches_common", "grd any observed all 2019-2024", round(ref["dispersion"], 6), round(mine["dispersion"], 6), "Pearson scale", tol_rel=1e-6)
    log(f"GRD national models: {n}")


# ---------------------------------------------------------------------------
# 2. GRD hospital-año: efectos fijos, EE agrupados, intercepto aleatorio, caterpillar 2024
# ---------------------------------------------------------------------------
def hospital_models(D: dict, S: Store, ctl: Controls) -> pd.DataFrame:
    h = D["grd_hosp"]
    effects = []
    ri_status, ri_seconds = {}, {}
    for variant in VARIANTS:
        hv = h[h.variant == variant].copy()
        hv["log_ep"] = np.log(hv.n_episodes_total)
        for panel in ["observed", "fixed65"]:
            hp = hv if panel == "observed" else hv[hv.in_fixed_panel.astype(bool)]
            for y0, y1 in [(2019, 2024), (2021, 2024)]:
                d = hp[(hp.year >= y0) & (hp.year <= y1)].sort_values(["COD_HOSPITAL", "year"]).reset_index(drop=True)
                t = (d.year - y0).astype(float).values
                dummies = pd.get_dummies(d.COD_HOSPITAL.astype(str), prefix="h", dtype=float)
                covsets = ["none", "depth", "disruption"] if y0 == 2019 else ["none", "depth"]
                for cs in covsets:
                    X = dummies.copy()
                    X["t"] = t
                    notes = ["hospital_fe", "hospital_dw", "ecological", "not_causal_law"]
                    if cs == "depth":
                        X["depth"] = d.coding_depth_mean.values - d.coding_depth_mean.mean()
                        notes.append("depth")
                    if cs == "disruption":
                        X["disruption"] = d.year.isin(DISRUPTION_YEARS).astype(float).values
                        notes.append("disruption")
                    for robust in ([False, True] if cs == "none" else [False]):
                        fit, df_resid = fit_glm(d.n_f84_any.values, X, d.log_ep.values, cluster=d.COD_HOSPITAL.values if robust else None)
                        ts = term_summary(fit, "t")
                        nk = notes + (["cluster"] if robust else [])
                        mid = f"grd_hospital:{variant}:{panel}:any:{cs}:{y0}-{y1}:{'cluster' if robust else 'model'}"
                        S.summary.append(dict(model_id=mid, estimand="est_grd_hospital", source="src_grd", variant=variant, outcome="out_f84_any",
                                              denominator_offset="off_hosp_episodes", panel=f"panel_{panel}", activity="act_all", position="pos_any",
                                              covariates=f"cov_hospital_fe{'' if cs == 'none' else '_' + cs}", model_family="fam_qp_fe_cluster" if robust else "fam_qp_fe",
                                              years=f"{y0}-{y1}", n_obs=int(len(d)), df_resid=int(df_resid), apc=ts["apc"], apc_lo=ts["apc_lo"], apc_hi=ts["apc_hi"],
                                              p_value=ts["p_value"], beta=ts["beta"], se=ts["se"], dispersion=float(fit.pearson_chi2 / df_resid),
                                              durbin_watson=durbin_watson(fit.resid_deviance, d.COD_HOSPITAL.values), dw_check="deviance residuals, within hospital",
                                              converged=bool(fit.converged), note_keys="|".join(nk), note=note_text(nk, "en"),
                                              hospitals_first=int(d.COD_HOSPITAL.nunique()), hospitals_last=int(d.COD_HOSPITAL.nunique()),
                                              depth_coef=(float(fit.params["depth"]) if cs == "depth" else np.nan)))
                        if not robust and panel == "observed" and (y0, y1) == (2019, 2024) and cs in ("none", "depth"):
                            # efectos fijos centrados en la media de los coeficientes de hospital
                            hcols = list(dummies.columns)
                            V = fit.cov_params().loc[hcols, hcols].to_numpy()
                            coef = fit.params[hcols].to_numpy()
                            k = len(hcols)
                            for j, col in enumerate(hcols):
                                c = -np.ones(k) / k
                                c[j] += 1.0
                                eff = float(c @ coef)
                                se = float(np.sqrt(c @ V @ c))
                                effects.append(dict(variant=variant, model=f"fixed_effects_{cs}", COD_HOSPITAL=int(col[2:]), effect_log=eff, effect_se=se,
                                                    rr=np.exp(eff), rr_lo=np.exp(eff - Z * se), rr_hi=np.exp(eff + Z * se), years="2019-2024", panel="observed"))
                # intercepto aleatorio (sensibilidad) — panel observado y fijo, 2019–2024, sin y con profundidad
                if (y0, y1) == (2019, 2024):
                    for cs in ["none", "depth"]:
                        if cs == "depth" and panel == "fixed65":
                            continue
                        exog = pd.DataFrame({"const": 1.0, "t": t})
                        if cs == "depth":
                            exog["depth"] = d.coding_depth_mean.values - d.coding_depth_mean.mean()
                        t0 = time.perf_counter()
                        ri = fit_random_intercept(d.n_f84_any.values, exog, d.COD_HOSPITAL.values, d.log_ep.values)
                        secs = time.perf_counter() - t0
                        mid = f"grd_hospital:{variant}:{panel}:any:ri_{cs}:{y0}-{y1}:random_intercept"
                        ri_status[mid] = ri.get("message", "")
                        nk = ["ri_ok" if ri["converged"] else "ri_fail", "ri_prior", "ri_poisson", "ecological", "not_causal_law"] + (["depth"] if cs == "depth" else [])
                        row = dict(model_id=mid, estimand="est_grd_hospital", source="src_grd", variant=variant, outcome="out_f84_any",
                                   denominator_offset="off_hosp_episodes", panel=f"panel_{panel}", activity="act_all", position="pos_any",
                                   covariates="cov_hospital_ri" if cs == "none" else "cov_hospital_ri_depth", model_family=ri.get("method", "fam_ri_map"),
                                   years=f"{y0}-{y1}", n_obs=int(len(d)), df_resid=ri.get("df_cond", np.nan), apc=np.nan, apc_lo=np.nan, apc_hi=np.nan, p_value=np.nan,
                                   beta=np.nan, se=np.nan, dispersion=ri.get("dispersion_cond", np.nan),
                                   durbin_watson=(durbin_watson(ri["resid_deviance"], d.COD_HOSPITAL.values) if "resid_deviance" in ri else np.nan),
                                   dw_check="conditional deviance residuals at MAP estimates, within hospital; dispersion = conditional Pearson chi2/(n - p_fixed - 1), diagnostic only",
                                   converged=bool(ri["converged"]),
                                   note_keys="|".join(nk), note=note_text(nk, "en") + " " + ri.get("message", ""),
                                   hospitals_first=int(d.COD_HOSPITAL.nunique()), hospitals_last=int(d.COD_HOSPITAL.nunique()),
                                   re_sd=ri.get("re_sd", np.nan), re_sd_lo=ri.get("re_sd_lo", np.nan), re_sd_hi=ri.get("re_sd_hi", np.nan))
                        # El tiempo de ajuste va al registro de ejecución, NUNCA a models_summary.csv: una
                        # columna de segundos hace que dos ejecuciones idénticas den archivos distintos y
                        # convierte la comprobación byte a byte de la reconstrucción en imposible.
                        ri_seconds[mid] = round(secs, 3)
                        if "fep" in ri:
                            b, s_ = ri["fep"]["t"], ri["fe_sd"]["t"]
                            row.update(apc=100 * (np.exp(b) - 1), apc_lo=100 * (np.exp(b - Z * s_) - 1), apc_hi=100 * (np.exp(b + Z * s_) - 1), beta=b, se=s_,
                                       p_value=float(2 * stats.norm.sf(abs(b / s_))), depth_coef=(ri["fep"].get("depth", np.nan)))
                            if ri["converged"] and panel == "observed":
                                for _, r in ri["effects"].iterrows():
                                    effects.append(dict(variant=variant, model=f"random_intercept_{cs}", COD_HOSPITAL=int(r.group), effect_log=float(r.re_mean),
                                                        effect_se=float(r.re_sd), rr=np.exp(r.re_mean), rr_lo=np.exp(r.re_mean - Z * r.re_sd),
                                                        rr_hi=np.exp(r.re_mean + Z * r.re_sd), years="2019-2024", panel="observed"))
                        S.summary.append(row)
                        log(f"random intercept {variant}/{panel}/{cs}: converged={ri['converged']} ({secs:.1f} s) {ri.get('message', '')}")
    # Caterpillar 2024: tasa por 100.000 episodios con IC exacto, por hospital y variante
    cat = []
    for variant in VARIANTS:
        d24 = h[(h.variant == variant) & (h.year == 2024)].copy()
        lo, hi = C.poisson_limits(d24.n_f84_any.values)
        d24["rate_2024"] = PER * d24.n_f84_any / d24.n_episodes_total
        d24["rate_lo"] = PER * lo / d24.n_episodes_total
        d24["rate_hi"] = PER * hi / d24.n_episodes_total
        cat.append(d24[["variant", "COD_HOSPITAL", "hospital_name", "in_fixed_panel", "n_episodes_total", "n_f84_any", "n_f84_principal", "coding_depth_mean",
                        "rate_2024", "rate_lo", "rate_hi"]])
    cat = pd.concat(cat, ignore_index=True)
    eff = pd.DataFrame(effects)
    wide = eff.pivot_table(index=["variant", "COD_HOSPITAL"], columns="model", values=["effect_log", "effect_se", "rr", "rr_lo", "rr_hi"], aggfunc="first")
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    hosp = cat.merge(wide, on=["variant", "COD_HOSPITAL"], how="left")
    hosp["rate_unit"] = "episodes with F84 (any position) per 100,000 GRD episodes of the hospital, 2024; exact Poisson 95% limits"
    hosp["effects_note"] = "fixed effects: quasi-Poisson 2019-2024 observed panel, centred on the mean of hospital coefficients; random intercept: Poisson MAP posterior mean and SD"
    ctl.add("hospital_year_sum_equals_year_total_2024", "con_rett", CFG.CONTROLS["grd_f84_any"][2024], int(cat[cat.variant == "con_rett"].n_f84_any.sum()), "sum over hospitals 2024")
    ctl.add("hospitals_2024", "observed", 72, int(cat[cat.variant == "con_rett"].COD_HOSPITAL.nunique()), "hospitals in the caterpillar table")
    S.hosp = hosp
    S.ri_status = ri_status
    S.ri_seconds = ri_seconds
    log(f"hospital effects rows: {len(hosp)}; hospital-level models: {sum(1 for r in S.summary if r['estimand'] == 'est_grd_hospital')}")
    return hosp


# ---------------------------------------------------------------------------
# 3. GRD por 100.000 habitantes (INE base 2017): tasas brutas, estandarizadas OMS y CPA
# ---------------------------------------------------------------------------
def _standardise(counts_by_age: pd.Series, pop_by_age: pd.Series, total_count: float) -> dict:
    frame = pd.DataFrame({"age_group": AGE_GROUPS, "count": counts_by_age.reindex(AGE_GROUPS).fillna(0.0).values,
                          "population": pop_by_age.reindex(AGE_GROUPS).values})
    asr = direct_standardization(frame, "count", "population", "age_group", per=PER)
    pop_total = float(frame.population.sum())
    crude, lo, hi = C.rate_per(int(round(total_count)), pop_total, PER)
    return dict(population=pop_total, crude=crude, crude_lo=lo, crude_hi=hi, asr=asr["asr"], asr_lo=asr["asr_lo"], asr_hi=asr["asr_hi"],
                known_count=float(frame["count"].sum()))


def _age_adjusted_apc(S: Store, model_id: str, cells: pd.DataFrame, meta: dict, notes: list[str], strata: list[str]) -> None:
    """Cuasi-Poisson sobre celdas (estrato × año) con efectos fijos de estrato, tendencia común y offset log(población)."""
    cells = cells[cells.population > 0].copy()
    cells = cells.sort_values(strata + ["year"]).reset_index(drop=True)
    t = (cells.year - cells.year.min()).astype(float).values
    key = cells[strata].astype(str).agg("|".join, axis=1)
    dummies = pd.get_dummies(key, prefix="s", dtype=float)
    X = dummies.copy()
    X["t"] = t
    fit, df_resid = fit_glm(cells["count"].values, X, np.log(cells.population.values))
    ts = term_summary(fit, "t")
    nk = list(notes) + ["age_adj"]
    S.summary.append(dict(model_id=model_id, **meta, model_family="fam_qp_age", years=f"{cells.year.min()}-{cells.year.max()}", n_obs=int(len(cells)),
                          df_resid=int(df_resid), apc=ts["apc"], apc_lo=ts["apc_lo"], apc_hi=ts["apc_hi"], p_value=ts["p_value"], beta=ts["beta"], se=ts["se"],
                          dispersion=float(fit.pearson_chi2 / df_resid), durbin_watson=durbin_watson(fit.resid_deviance, key.values),
                          dw_check="deviance residuals, within stratum", converged=bool(fit.converged), note_keys="|".join(nk), note=note_text(nk, "en")))


def population_rates(D: dict, S: Store, ctl: Controls) -> pd.DataFrame:
    ga, ine = D["grd_age"], D["ine_age"]
    rows = []
    for variant in VARIANTS + [STRICT_GRD]:
        for position in ["any", "principal"]:
            sub = ga[(ga.variant == variant) & (ga.panel == "observed") & (ga.activity == "all") & (ga.position == position)]
            cells_all = []
            for sex in ["HOMBRE", "MUJER", "TOTAL"]:
                per_year = []
                for year in CFG.YEARS_GRD:
                    cy = sub[sub.year == year]
                    if sex == "TOTAL":
                        total_count = cy.n_f84.sum()
                        known = cy[(cy.sex != "unknown") & (cy.age_group != "unknown")].groupby("age_group").n_f84.sum()
                    else:
                        cs = cy[cy.sex == sex]
                        total_count = cs.n_f84.sum()
                        known = cs[cs.age_group != "unknown"].groupby("age_group").n_f84.sum()
                    pop = ine[(ine.year == year) & (ine.sex == sex)].set_index("age_group").population.astype(float)
                    r = _standardise(known, pop, total_count)
                    r.update(variant=variant, position=position, year=year, sex=sex, count=int(total_count), unknown_excluded=int(total_count - r["known_count"]))
                    rows.append(r)
                    per_year.append(r)
                    for ag in AGE_GROUPS:
                        cells_all.append(dict(year=year, sex=sex, age_group=ag, count=float(known.get(ag, 0.0)), population=float(pop.get(ag, np.nan))))
                py = pd.DataFrame(per_year)
                notes = ["place_vs_residence", "unknown_excluded", "not_causal_law"] + (["principal_small"] if position == "principal" else []) + (["strict_identical"] if variant == STRICT_GRD else [])
                meta = dict(estimand="est_grd_pop", source="src_grd", variant=variant, outcome="out_f84_any" if position == "any" else "out_f84_principal",
                            denominator_offset="off_pop", panel="panel_observed", activity="act_all", position=f"pos_{position}", covariates="cov_none", sex=sex)
                for y0, y1 in [(2019, 2024), (2021, 2024)]:
                    w = py[(py.year >= y0) & (py.year <= y1)]
                    S.add_trend(f"grd_pop:{variant}:{position}:{sex}:crude:{y0}-{y1}", w.year.values, w["count"].values, w.population.values, None, PER, meta, notes)
                    cells = pd.DataFrame([c for c in cells_all if c["sex"] == sex and y0 <= c["year"] <= y1])
                    _age_adjusted_apc(S, f"grd_pop:{variant}:{position}:{sex}:age_adjusted:{y0}-{y1}", cells, {**meta, "covariates": "cov_age"}, notes, ["age_group"])
    out = pd.DataFrame(rows)
    out["per"] = PER
    out["unit"] = "GRD episodes with documented F84 (observed panel, all activity) per 100,000 INE resident population (base 2017, 30 June); crude with exact Poisson limits, WHO-standardised with Fay-Feuer limits"
    base = out[(out.variant == "con_rett") & (out.position == "any") & (out.sex == "TOTAL")].set_index("year")
    ctl.add("grd_pop_crude_2019_total", "con_rett any", round(PER * CFG.CONTROLS["grd_f84_any"][2019] / CFG.CONTROLS["ine_population_national"][2019], 3),
            round(float(base.loc[2019, "crude"]), 3), "2,385 / 19,107,216 x 100,000", tol_rel=1e-6)
    log(f"population-rate rows: {len(out)}")
    return out


# ---------------------------------------------------------------------------
# 4. REM A05: ingresos por autismo 2021–2025, offsets alternativos, tasas estandarizadas
# ---------------------------------------------------------------------------
def a05_series(rem: pd.DataFrame, variant: str, flow: str) -> pd.DataFrame:
    prefix = CFG.STRICT["a05_entry"] if flow == "entry" else CFG.STRICT["a05_exit"]
    if variant == STRICT_REM:
        s = rem[(rem.module == "A05") & (rem.variant == STRICT_REM) & (rem.code == prefix)]
    else:
        s = rem[(rem.module == "A05") & (rem.variant == variant) & (rem.code.str.startswith(prefix))]
    return s[s.measure == "annual_sum"].sort_values("year")


def a05_models(D: dict, S: Store, ctl: Controls) -> pd.DataFrame:
    rem, ine_tot, ine = D["rem"], D["ine_total"], D["ine_age"]
    a05 = D["a05_age"]
    a05 = a05[a05.flow == "entry"].copy()
    a05["sex"] = a05.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    rows = []
    for variant in [STRICT_REM] + VARIANTS:
        for flow in ["entry", "exit"]:
            s = a05_series(rem, variant, flow)
            pop = np.array([ine_tot.loc[(y, "TOTAL")] for y in s.year])
            est = "est_a05" if flow == "entry" else "est_a05_exit"
            outc = "out_entries" if flow == "entry" else "out_exits"
            notes = ["a05_era", "a05_2025", "not_causal_law"] + (["strict_identical"] if variant == STRICT_REM else [])
            meta = dict(estimand=est, source="src_a05", variant=variant, outcome=outc, denominator_offset="off_pop", panel="panel_all_estab",
                        activity="act_na", position="pos_na", covariates="cov_none")
            tag = f"a05_{flow}:{variant}"
            for y0, y1 in ([(2021, 2025), (2022, 2025)] if flow == "entry" else [(2021, 2025)]):
                w = (s.year >= y0) & (s.year <= y1)
                S.add_trend(f"{tag}:pop:none:{y0}-{y1}", s.year[w].values, s.total[w].values, pop[w], None, PER, {**meta, "estimand": "est_a05_pop" if flow == "entry" else est},
                            notes + ["place_vs_residence"], offsets_label=s.n_reporting_establishments[w].values)
            if flow == "entry":
                S.add_trend(f"{tag}:pop:disruption2021:2021-2025", s.year.values, s.total.values, pop, {"disruption": (s.year == 2021).astype(float).values}, PER,
                            {**meta, "estimand": "est_a05_pop", "covariates": "cov_disruption_2021"}, notes + ["place_vs_residence", "disruption"], offsets_label=s.n_reporting_establishments.values)
            S.add_trend(f"{tag}:estab:none:2021-2025", s.year.values, s.total.values, s.n_reporting_establishments.values, None, 1.0,
                        {**meta, "denominator_offset": "off_estab"}, notes + ["estab_offset"], offsets_label=s.n_reporting_establishments.values)
            S.add_trend(f"{tag}:count:none:2021-2025", s.year.values, s.total.values, None, None, 1.0, {**meta, "denominator_offset": "off_none"}, notes,
                        offsets_label=s.n_reporting_establishments.values)
            S.add_trend(f"{tag}:stable_pop:none:2021-2025", s.year.values, s.stable_panel_total.values, pop, None, PER,
                        {**meta, "estimand": "est_a05_pop" if flow == "entry" else est, "panel": "panel_stable", "outcome": "out_entries_stable" if flow == "entry" else outc},
                        notes + ["stable_panel", "place_vs_residence"], offsets_label=s.n_stable_panel_establishments.values,
                        extra=dict(stable_panel_n=int(s.n_stable_panel_establishments.iloc[0])))
        # tasas estandarizadas por edad y sexo (solo ingresos)
        if variant == STRICT_REM:
            cells_src = a05[(a05.variant == "single_code") & (a05.category == "autism")]
        else:
            cells_src = a05[(a05.variant == variant) & (a05.category == "pdd_family")]
        cells_all = []
        for sex in ["HOMBRE", "MUJER", "TOTAL"]:
            per_year = []
            for year in range(2021, 2026):
                cy = cells_src[(cells_src.year == year) & (cells_src.age_group != "total")]
                cy = cy if sex == "TOTAL" else cy[cy.sex == sex]
                known = cy.groupby("age_group")["count"].sum()
                pop = ine[(ine.year == year) & (ine.sex == sex)].set_index("age_group").population.astype(float)
                r = _standardise(known, pop, known.sum())
                estab = int(cells_src[cells_src.year == year].n_reporting_establishments.max())
                col01 = float(cells_src[(cells_src.year == year) & (cells_src.age_group == "total") & ((cells_src.sex == sex) if sex != "TOTAL" else True)]["count"].sum())
                r.update(variant=variant, year=year, sex=sex, count=int(known.sum()), col01_total=col01, n_reporting_establishments=estab, unknown_excluded=0)
                rows.append(r)
                per_year.append(r)
                for ag in AGE_GROUPS:
                    cells_all.append(dict(year=year, sex=sex, age_group=ag, count=float(known.get(ag, 0.0)), population=float(pop.get(ag, np.nan))))
            notes = ["a05_era", "a05_cells", "place_vs_residence", "not_causal_law"] + (["strict_identical"] if variant == STRICT_REM else [])
            meta = dict(estimand="est_a05_pop", source="src_a05", variant=variant, outcome="out_entries", denominator_offset="off_pop", panel="panel_all_estab",
                        activity="act_na", position="pos_na", covariates="cov_age", sex=sex)
            cells = pd.DataFrame([c for c in cells_all if c["sex"] == sex])
            _age_adjusted_apc(S, f"a05_entry:{variant}:{sex}:age_adjusted:2021-2025", cells, meta, notes, ["age_group"])
    out = pd.DataFrame(rows)
    out["per"] = PER
    out["unit"] = "REM A05 autism entries (sum of age x sex cells, in-era rows) per 100,000 INE resident population (base 2017); crude with exact Poisson limits; WHO-standardised with Fay-Feuer limits; place of care vs residence"
    chk = out[(out.variant == STRICT_REM) & (out.sex == "TOTAL")].set_index("year")
    for yr, exp in CFG.CONTROLS["a05_autism_entries"].items():
        ctl.add("a05_age_cells_sum_vs_control", yr, exp, int(chk.loc[yr, "count"]), "sum of age x sex cells of 05990022 (tolerance 0.5%)")
    log(f"A05 standardised-rate rows: {len(out)}")
    return out


# ---------------------------------------------------------------------------
# 5. Stocks REM P2/P6 (diciembre; junio sensibilidad); P2 por 100 NANEAS
# ---------------------------------------------------------------------------
def stock_models(D: dict, S: Store) -> None:
    rem = D["rem"]
    p2 = rem[(rem.module == "P2") & (rem.code == CFG.P2_TEA) & (rem.measure == "december_stock")].sort_values("year")
    meta = dict(estimand="est_p2", source="src_p2", variant=BOTH, outcome="out_stock", denominator_offset="off_none", panel="panel_all_estab",
                activity="act_na", position="pos_na", covariates="cov_none", model_family="fam_qp_stock")
    base_notes = ["stock", "not_causal_law"]
    for y0, y1 in [(2019, 2025), (2021, 2025), (2022, 2025)]:
        w = (p2.year >= y0) & (p2.year <= y1)
        S.add_trend(f"p2_dec:none:{y0}-{y1}", p2.year[w].values, p2.total[w].values, None, None, 1.0, meta, base_notes, offsets_label=p2.n_reporting_establishments[w].values)
        S.add_trend(f"p2_dec:estab:{y0}-{y1}", p2.year[w].values, p2.total[w].values, p2.n_reporting_establishments[w].values, None, 1.0,
                    {**meta, "denominator_offset": "off_estab"}, base_notes + ["estab_offset"], offsets_label=p2.n_reporting_establishments[w].values)
    S.add_trend("p2_dec:none_disruption:2019-2025", p2.year.values, p2.total.values, None, {"disruption": p2.year.isin(DISRUPTION_YEARS).astype(float).values}, 1.0,
                {**meta, "covariates": "cov_disruption"}, base_notes + ["disruption"], offsets_label=p2.n_reporting_establishments.values)
    S.add_trend("p2_dec:estab_disruption:2019-2025", p2.year.values, p2.total.values, p2.n_reporting_establishments.values,
                {"disruption": p2.year.isin(DISRUPTION_YEARS).astype(float).values}, 1.0, {**meta, "denominator_offset": "off_estab", "covariates": "cov_disruption"},
                base_notes + ["estab_offset", "disruption"], offsets_label=p2.n_reporting_establishments.values)
    S.add_trend("p2_dec:stable:2019-2025", p2.year.values, p2.stable_panel_total.values, None, None, 1.0, {**meta, "panel": "panel_stable", "outcome": "out_stock_stable"},
                base_notes + ["stable_panel"], offsets_label=p2.n_stable_panel_establishments.values, extra=dict(stable_panel_n=int(p2.n_stable_panel_establishments.iloc[0])))
    # junio (sensibilidad): 2020 con 28 establecimientos → indicador de disrupción obligado
    p2j = rem[(rem.module == "P2") & (rem.code == CFG.P2_TEA) & (rem.measure == "june_stock")].sort_values("year")
    S.add_trend("p2_jun:none_disruption:2019-2025", p2j.year.values, p2j.total.values, None, {"disruption": p2j.year.isin(DISRUPTION_YEARS).astype(float).values}, 1.0,
                {**meta, "estimand": "est_p2_june", "outcome": "out_stock_june", "covariates": "cov_disruption"}, base_notes + ["june", "disruption"],
                offsets_label=p2j.n_reporting_establishments.values)
    S.add_trend("p2_jun:estab:2021-2025", p2j.year[p2j.year >= 2021].values, p2j.total[p2j.year >= 2021].values, p2j.n_reporting_establishments[p2j.year >= 2021].values, None, 1.0,
                {**meta, "estimand": "est_p2_june", "outcome": "out_stock_june", "denominator_offset": "off_estab"}, base_notes + ["june", "estab_offset"],
                offsets_label=p2j.n_reporting_establishments[p2j.year >= 2021].values)
    # P2 por 100 NANEAS (2023–2025)
    nan_ = rem[(rem.module == "P2") & (rem.code == CFG.P2_NANEAS_TOTAL) & (rem.measure == "december_stock")].set_index("year").total
    w = p2.year.isin(nan_.index)
    S.add_trend("p2_dec:naneas:2023-2025", p2.year[w].values, p2.total[w].values, nan_.loc[p2.year[w]].values, None, 100.0,
                {**meta, "estimand": "est_p2_naneas", "denominator_offset": "off_naneas"}, base_notes + ["naneas"], offsets_label=p2.n_reporting_establishments[w].values)
    # P6 diciembre 2021–2025: estricto y familia por variante, APS y especialidad
    for setting, prefix_key in [("primary", "p6_primary"), ("specialty", "p6_specialty")]:
        prefix = CFG.STRICT[prefix_key]
        for variant in [STRICT_REM] + VARIANTS:
            if variant == STRICT_REM:
                s = rem[(rem.module == "P6") & (rem.variant == STRICT_REM) & (rem.code == prefix) & (rem.measure == "december_stock")]
            else:
                s = rem[(rem.module == "P6") & (rem.variant == variant) & (rem.code.str.startswith(prefix)) & (rem.measure == "december_stock")]
            s = s.sort_values("year")
            m6 = dict(estimand=f"est_p6_{setting}", source="src_p6", variant=variant, outcome="out_stock", denominator_offset="off_none", panel="panel_all_estab",
                      activity="act_na", position="pos_na", covariates="cov_none", model_family="fam_qp_stock")
            nk = base_notes + ["a05_era"] + (["strict_identical"] if variant == STRICT_REM else [])
            tag = f"p6_{setting}:{variant}"
            S.add_trend(f"{tag}:none:2021-2025", s.year.values, s.total.values, None, None, 1.0, m6, nk, offsets_label=s.n_reporting_establishments.values)
            S.add_trend(f"{tag}:estab:2021-2025", s.year.values, s.total.values, s.n_reporting_establishments.values, None, 1.0, {**m6, "denominator_offset": "off_estab"},
                        nk + ["estab_offset"], offsets_label=s.n_reporting_establishments.values)
            S.add_trend(f"{tag}:stable:2021-2025", s.year.values, s.stable_panel_total.values, None, None, 1.0, {**m6, "panel": "panel_stable", "outcome": "out_stock_stable"},
                        nk + ["stable_panel"], offsets_label=s.n_stable_panel_establishments.values, extra=dict(stable_panel_n=int(s.n_stable_panel_establishments.iloc[0])))
    log("stock models done")


# ---------------------------------------------------------------------------
# 6. Educación (PIE) y 7. DEIS
# ---------------------------------------------------------------------------
def education_models(D: dict, S: Store) -> None:
    e = D["edu"].sort_values("year")
    meta = dict(estimand="est_pie", source="src_pie", variant=BOTH, outcome="out_pie_harmonised", denominator_offset="off_none", panel="panel_national",
                activity="act_na", position="pos_na", covariates="cov_none", model_family="fam_qp_stock")
    for y0, y1 in [(2019, 2025), (2019, 2023), (2021, 2025)]:
        w = (e.year >= y0) & (e.year <= y1)
        S.add_trend(f"pie_harmonised:none:{y0}-{y1}", e.year[w].values, e.pie_harmonised_n[w].values, None, None, 1.0, meta, ["pie_source", "stock", "not_causal_law"])
    S.add_trend("pie_harmonised:disruption:2019-2025", e.year.values, e.pie_harmonised_n.values, None, {"disruption": e.year.isin(DISRUPTION_YEARS).astype(float).values}, 1.0,
                {**meta, "covariates": "cov_disruption"}, ["pie_source", "stock", "disruption", "not_causal_law"])
    for col, outc in [("pie_tea_strict_n", "out_pie_strict"), ("pie_tea_asperger_n", "out_pie_asperger")]:
        w = e[col].notna()
        S.add_trend(f"{col}:none:2019-2023", e.year[w].values, e[col][w].values, None, None, 1.0, {**meta, "outcome": outc}, ["stock", "not_causal_law"])


def deis_models(D: dict, S: Store) -> None:
    d = D["deis"].sort_values("year")
    for variant in VARIANTS:
        s = d[d.variant == variant]
        meta = dict(estimand="est_deis", source="src_deis", variant=variant, outcome="out_deis_principal", denominator_offset="off_discharges", panel="panel_national",
                    activity="act_all", position="pos_principal", covariates="cov_none")
        for y0, y1 in [(2019, 2024), (2021, 2024)]:
            w = (s.year >= y0) & (s.year <= y1)
            S.add_trend(f"deis_principal:{variant}:none:{y0}-{y1}", s.year[w].values, s.f84_diag1[w].values, s.discharges_total[w].values, None, PER, meta,
                        ["deis_principal", "not_causal_law"])
        S.add_trend(f"deis_principal:{variant}:disruption:2019-2024", s.year.values, s.f84_diag1.values, s.discharges_total.values,
                    {"disruption": s.year.isin(DISRUPTION_YEARS).astype(float).values}, PER, {**meta, "covariates": "cov_disruption"}, ["deis_principal", "disruption", "not_causal_law"])


# ---------------------------------------------------------------------------
# 8. Índices de convergencia (primer año común = 100)
# ---------------------------------------------------------------------------
def convergence_index(D: dict) -> pd.DataFrame:
    rem, g, e, d = D["rem"], D["grd"], D["edu"].set_index("year"), D["deis"]
    rows = []
    for variant in VARIANTS:
        series = {}
        gv = g[(g.variant == variant) & (g.panel == "observed") & (g.activity == "all")]
        series["grd_any_rate"] = (gv[gv.position == "any"].set_index("year").rate_per_100k_episodes, "episodes with F84 (any position) per 100,000 GRD episodes", "rate")
        series["grd_principal_rate"] = (gv[gv.position == "principal"].set_index("year").rate_per_100k_episodes, "episodes with F84 principal per 100,000 GRD episodes", "rate")
        series["deis_principal_rate"] = (d[d.variant == variant].set_index("year").rate_per_100k_discharges, "DEIS discharges with F84 principal per 100,000 discharges", "rate")
        series["a05_strict_entries"] = (a05_series(rem, STRICT_REM, "entry").set_index("year").total, "A05 autism entries (05990022), count", "flow")
        series["a05_family_entries"] = (a05_series(rem, variant, "entry").set_index("year").total, f"A05 PDD family entries ({variant}), count", "flow")
        p2 = rem[(rem.module == "P2") & (rem.code == CFG.P2_TEA) & (rem.measure == "december_stock")].set_index("year").total
        series["p2_december_stock"] = (p2, "P2 ASD under control in December, people", "stock")
        p6 = rem[(rem.module == "P6") & (rem.variant == STRICT_REM) & (rem.code == CFG.STRICT["p6_primary"]) & (rem.measure == "december_stock")].set_index("year").total
        series["p6_primary_strict_stock"] = (p6, "P6 primary-care autism under control in December (P6241010), people", "stock")
        series["pie_harmonised"] = (e.pie_harmonised_n, "PIE ASD + ASD-Asperger students (harmonised), annual stock", "stock")
        for name, (ser, unit, kind) in series.items():
            ser = ser.dropna().sort_index()
            for base in [2021, 2019]:
                if base not in ser.index:
                    continue
                for yr, val in ser.items():
                    rows.append(dict(variant=variant, series=name, unit=unit, stock_or_flow=kind, index_base_year=base, year=int(yr), value=float(val),
                                     index=100.0 * float(val) / float(ser.loc[base]), first_year=int(ser.index.min()), last_year=int(ser.index.max())))
    out = pd.DataFrame(rows)
    out["note"] = "Indices (base year = 100) of series with different units, denominators and coverage; never levels; first common year across all series is 2021 (A05 autism codes start in 2021)"
    return out


# ---------------------------------------------------------------------------
# Tablas formateadas por variante e idioma
# ---------------------------------------------------------------------------
def _fmt_apc(r, lang):
    if pd.isna(r.apc):
        return tr("na", lang)
    return f"{C.fmt_number(r.apc, 1, lang)} ({C.fmt_ci(r.apc_lo, r.apc_hi, 1, lang)})"


def _variant_rows(df: pd.DataFrame, variant: str) -> pd.DataFrame:
    return df[df.variant.isin([variant, STRICT_GRD, STRICT_REM, BOTH])]


def format_summary(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    out = pd.DataFrame({
        tr("estimand", lang): df.estimand.map(lambda k: tr(k, lang)),
        tr("source", lang): df.source.map(lambda k: tr(k, lang)),
        tr("variant", lang): df.variant.map(lambda v: tr(f"var_{v}", lang)),
        tr("outcome", lang): df.outcome.map(lambda k: tr(k, lang)) + df.get("sex", pd.Series(index=df.index, dtype=object)).map(lambda s: "" if pd.isna(s) else f" · {tr(s, lang)}"),
        tr("offset", lang): df.denominator_offset.map(lambda k: tr(k, lang)),
        tr("panel", lang): df.panel.map(lambda k: tr(k, lang)),
        tr("activity", lang): df.activity.map(lambda k: tr(k, lang)),
        tr("position", lang): df.position.map(lambda k: tr(k, lang)),
        tr("covariates", lang): df.covariates.map(lambda k: tr(k, lang)),
        tr("years", lang): df.years.str.replace("-", "–"),
        tr("n_obs", lang): df.n_obs.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("apc_ci", lang): [_fmt_apc(r, lang) for r in df.itertuples()],
        tr("p", lang): df.p_value.map(lambda p: C.fmt_p(p, lang)),
        tr("dispersion", lang): df.dispersion.map(lambda v: C.fmt_number(v, 2, lang)),
        tr("dw", lang): df.durbin_watson.map(lambda v: C.fmt_number(v, 2, lang)),
        tr("family", lang): df.model_family.map(lambda k: tr(k, lang)),
        tr("note", lang): df.note_keys.map(lambda k: note_text(str(k).split("|"), lang)),
    })
    return out


MAIN_IDS = {
    "grd": ["grd_rate:{v}:observed:all:any:none:2019-2024", "grd_rate:{v}:observed:all:any:depth:2019-2024", "grd_rate:{v}:observed:all:any:disruption:2019-2024",
            "grd_rate:{v}:observed:all:any:depth_disruption:2019-2024", "grd_rate:{v}:observed:all:any:none:2021-2024", "grd_rate:{v}:fixed65:all:any:none:2019-2024",
            "grd_rate:{v}:fixed65:all:any:depth:2019-2024", "grd_rate:{v}:observed:hospitalisation:any:none:2019-2024", "grd_rate:{v}:observed:all:principal:none:2019-2024",
            "grd_rate:{v}:fixed65:all:principal:none:2019-2024", "grd_rate:{v}:observed:all:principal:none:2021-2024",
            "grd_rate:strict_autism_f840:observed:all:any:none:2019-2024",
            "grd_hospital:{v}:observed:any:none:2019-2024:model", "grd_hospital:{v}:observed:any:none:2019-2024:cluster", "grd_hospital:{v}:observed:any:depth:2019-2024:model",
            "grd_hospital:{v}:fixed65:any:none:2019-2024:model", "grd_hospital:{v}:observed:any:ri_none:2019-2024:random_intercept",
            "grd_pop:{v}:any:TOTAL:crude:2019-2024", "grd_pop:{v}:any:TOTAL:age_adjusted:2019-2024", "grd_pop:{v}:any:HOMBRE:age_adjusted:2019-2024",
            "grd_pop:{v}:any:MUJER:age_adjusted:2019-2024", "grd_pop:{v}:any:TOTAL:age_adjusted:2021-2024"],
    "rem": ["a05_entry:strict_autism:pop:none:2021-2025", "a05_entry:strict_autism:pop:none:2022-2025", "a05_entry:strict_autism:estab:none:2021-2025",
            "a05_entry:strict_autism:stable_pop:none:2021-2025", "a05_entry:strict_autism:count:none:2021-2025", "a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025",
            "a05_entry:{v}:pop:none:2021-2025", "a05_entry:{v}:estab:none:2021-2025", "a05_entry:{v}:TOTAL:age_adjusted:2021-2025",
            "p2_dec:none:2019-2025", "p2_dec:estab:2019-2025", "p2_dec:none_disruption:2019-2025", "p2_dec:stable:2019-2025", "p2_dec:none:2021-2025", "p2_dec:naneas:2023-2025",
            "p6_primary:strict_autism:none:2021-2025", "p6_primary:strict_autism:estab:2021-2025", "p6_specialty:strict_autism:none:2021-2025", "p6_specialty:strict_autism:estab:2021-2025",
            "p6_primary:{v}:none:2021-2025", "p6_specialty:{v}:none:2021-2025",
            "pie_harmonised:none:2019-2025", "pie_harmonised:none:2019-2023", "pie_harmonised:disruption:2019-2025", "pie_harmonised:none:2021-2025",
            "deis_principal:{v}:none:2019-2024", "deis_principal:{v}:none:2021-2024"],
}


def main_ids(variant: str) -> list[str]:
    return [m.format(v=variant) for m in MAIN_IDS["grd"] + MAIN_IDS["rem"]]


def write_tables(S: Store, pop: pd.DataFrame, a05: pd.DataFrame, conv: pd.DataFrame, summary: pd.DataFrame, variant: str, lang: str, ctl: Controls) -> dict:
    tdir = out_dir(variant, lang, "tables")
    titles = {}
    fig_word, tab_word = tr("figure", lang), tr("table", lang)
    # T7: modelos (completa y principal)
    rows = _variant_rows(summary, variant)
    full = format_summary(rows, lang)
    C.atomic_write_csv(full, tdir / "T7_models_cpa_full.csv")
    C.atomic_write_csv(rows, tdir / "T7_models_cpa_full_numeric.csv")
    ids = main_ids(variant)
    main = rows.set_index("model_id").reindex([i for i in ids if i in set(rows.model_id)]).reset_index()
    C.atomic_write_csv(format_summary(main, lang), tdir / "T7_models_cpa.csv")
    C.atomic_write_csv(main, tdir / "T7_models_cpa_numeric.csv")
    vlab = tr(f"var_{variant}", lang)
    titles["T7_models_cpa"] = {
        "title": {"es": f"{tab_word} 7. Cambio porcentual anual (CPA) de los indicadores de reconocimiento administrativo del autismo según estimando y sensibilidad, Chile 2019–2025 — variante {vlab}",
                  "en": f"{tab_word} 7. Annual percent change (APC) of administrative-recognition indicators of autism by estimand and sensitivity, Chile 2019–2025 — {vlab} variant"}[lang],
        "note": {"es": "Modelos log-lineales cuasi-Poisson (escala de Pearson) con el offset indicado; CPA = 100·(exp(β)−1) con IC 95 % de Wald. GRD: episodios con F84 documentado por 100.000 episodios GRD del mismo panel y modalidad (panel observado: 65, 65, 65, 65, 68 y 72 hospitales; panel fijo: 65). Hospital-año: efectos fijos de hospital con offset log(episodios); EE robustos por hospital e intercepto aleatorio Poisson como sensibilidad. Por 100.000 habitantes: población INE base 2017 (residencia) frente a numerador por lugar de atención. REM A05 2021–2025 (era de códigos de autismo; TGD amplio 2019–2020 excluido), con número de establecimientos reportantes en la tabla de tasas; P2/P6 son stocks de diciembre (junio solo como sensibilidad; nunca sumados). PIE armonizado: Apuntes 60 (2019–2023) y SINACES (2024–2025). DEIS: F84 en DIAG1 (DEIS no publica diagnósticos secundarios), comparable solo con GRD principal. El indicador 2020–2021 describe la disrupción del reporte y la Ley 21.545 (marzo 2023) es contexto: ningún modelo estima efectos causales. Durbin–Watson sobre residuos de devianza; con 4–7 puntos es una prueba débil. Los conteos son reconocimiento administrativo, no prevalencia ni incidencia.",
                 "en": "Quasi-Poisson log-linear models (Pearson scale) with the stated offset; APC = 100·(exp(β)−1) with Wald 95% CI. GRD: episodes with documented F84 per 100,000 GRD episodes of the same panel and activity (observed panel: 65, 65, 65, 65, 68 and 72 hospitals; fixed panel: 65). Hospital-year: hospital fixed effects with log(episodes) offset; hospital-clustered SE and a Poisson random intercept as sensitivity. Per 100,000 population: INE base-2017 resident population against a place-of-care numerator. REM A05 2021–2025 (autism-code era; broad PDD 2019–2020 excluded), with reporting establishments in the rate table; P2/P6 are December stocks (June only as sensitivity; never summed). Harmonised PIE: Apuntes 60 (2019–2023) and SINACES (2024–2025). DEIS: F84 in DIAG1 (DEIS publishes no secondary diagnoses), comparable only with GRD principal. The 2020–2021 indicator describes reporting disruption and Law 21.545 (March 2023) is context: no model estimates causal effects. Durbin–Watson on deviance residuals; with 4–7 points it is a weak test. Counts are administrative recognition, not prevalence or incidence."}[lang]}
    titles["T7_models_cpa_full"] = {"title": titles["T7_models_cpa"]["title"].replace("Tabla 7.", "Tabla S7.").replace("Table 7.", "Table S7.") + (" (todas las especificaciones)" if lang == "es" else " (all specifications)"),
                                    "note": titles["T7_models_cpa"]["note"]}
    # Hospital 2024
    hv = S.hosp[S.hosp.variant == variant].sort_values("rate_2024", ascending=False)
    def rr(r, a):
        v, lo, hi = r.get(f"rr_{a}", np.nan), r.get(f"rr_lo_{a}", np.nan), r.get(f"rr_hi_{a}", np.nan)
        return tr("na", lang) if pd.isna(v) else f"{C.fmt_number(v, 2, lang)} ({C.fmt_ci(lo, hi, 2, lang)})"
    ht = pd.DataFrame({
        tr("code", lang): hv.COD_HOSPITAL.astype(str),
        tr("hospital", lang): hv.hospital_name,
        tr("fixed_member", lang): hv.in_fixed_panel.map(lambda b: tr("yes", lang) if b else tr("no", lang)),
        tr("episodes_total", lang): hv.n_episodes_total.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("f84_2024", lang): hv.n_f84_any.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("rate_2024", lang): [f"{C.fmt_number(r.rate_2024, 1, lang)} ({C.fmt_ci(r.rate_lo, r.rate_hi, 1, lang)})" for r in hv.itertuples()],
        tr("depth_2024", lang): hv.coding_depth_mean.map(lambda v: C.fmt_number(v, 2, lang)),
        tr("rr_fe", lang): [rr(r, "fixed_effects_none") for _, r in hv.iterrows()],
        tr("rr_fe_depth", lang): [rr(r, "fixed_effects_depth") for _, r in hv.iterrows()],
        tr("rr_ri", lang): [rr(r, "random_intercept_none") for _, r in hv.iterrows()],
    })
    C.atomic_write_csv(ht, tdir / "S_hospital_rates_2024.csv")
    C.atomic_write_csv(hv, tdir / "S_hospital_rates_2024_numeric.csv")
    titles["S_hospital_rates_2024"] = {
        "title": {"es": f"{tab_word} S3. Episodios con F84 documentado por 100.000 episodios GRD según hospital, 2024, con efectos de hospital 2019–2024 — variante {vlab}",
                  "en": f"{tab_word} S3. Episodes with documented F84 per 100,000 GRD episodes by hospital, 2024, with hospital effects 2019–2024 — {vlab} variant"}[lang],
        "note": {"es": f"72 hospitales observados en 2024 (65 del panel fijo, {C.fixed_panel_gloss('es', 'clause')}, y 7 incorporados en 2023–2024). Tasa = episodios con F84 en cualquier posición / episodios GRD del hospital × 100.000, IC 95 % exacto de Poisson. RR de efecto fijo: cuasi-Poisson 2019–2024 con indicadores de hospital, tendencia común y offset log(episodios), expresado frente a la media geométrica de los hospitales (sin y con ajuste por la profundidad diagnóstica del hospital-año). RR de intercepto aleatorio: media a posteriori (Laplace/MAP) con intervalo ±1,96 DE. Resultados descriptivos por lugar de atención; no se interpretan ecológicamente ni como calidad de atención.",
                 "en": f"72 hospitals observed in 2024 (65 from the fixed panel, {C.fixed_panel_gloss('en', 'clause')}, and 7 added in 2023–2024). Rate = episodes with F84 in any position / GRD episodes of the hospital × 100,000, exact Poisson 95% CI. Fixed-effect RR: quasi-Poisson 2019–2024 with hospital indicators, common trend and log(episodes) offset, expressed against the geometric mean of hospitals (without and with adjustment for hospital-year coding depth). Random-intercept RR: posterior mean (Laplace/MAP) with ±1.96 SD interval. Descriptive results by place of care; not interpreted ecologically nor as quality of care."}[lang]}
    # GRD por población
    pv = pop[(pop.variant == variant) & (pop.position == "any")].sort_values(["sex", "year"])
    pt = pd.DataFrame({
        tr("sex", lang): pv.sex.map(lambda s: tr(s, lang)), tr("year", lang): pv.year,
        tr("count", lang): pv["count"].map(lambda v: C.fmt_number(v, 0, lang)),
        tr("unknown", lang): pv.unknown_excluded.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("population", lang): pv.population.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("crude", lang): [f"{C.fmt_number(r.crude, 1, lang)} ({C.fmt_ci(r.crude_lo, r.crude_hi, 1, lang)})" for r in pv.itertuples()],
        tr("asr", lang): [f"{C.fmt_number(r.asr, 1, lang)} ({C.fmt_ci(r.asr_lo, r.asr_hi, 1, lang)})" for r in pv.itertuples()],
    })
    C.atomic_write_csv(pt, tdir / "S_grd_population_rates.csv")
    C.atomic_write_csv(pop[pop.variant == variant], tdir / "S_grd_population_rates_numeric.csv")
    titles["S_grd_population_rates"] = {
        "title": {"es": f"{tab_word} S4. Episodios GRD con F84 documentado por 100.000 habitantes, brutos y estandarizados por edad (OMS), según sexo y año, 2019–2024 — variante {vlab}",
                  "en": f"{tab_word} S4. GRD episodes with documented F84 per 100,000 population, crude and WHO age-standardised, by sex and year, 2019–2024 — {vlab} variant"}[lang],
        "note": {"es": "Numerador: episodios GRD con F84 en cualquier posición, panel anual observado y toda modalidad (lugar de atención, red pública). Denominador: proyecciones INE base Censo 2017 al 30 de junio (residencia). Tasa bruta con IC exacto de Poisson; tasa estandarizada por método directo con la población estándar OMS (grupos quinquenales, 80+) e IC gamma de Fay–Feuer. Los episodios sin edad o sexo válidos se incluyen en la tasa bruta y se excluyen de la estandarizada. Lectura complementaria de episodios por población; no es prevalencia ni incidencia de autismo.",
                 "en": "Numerator: GRD episodes with F84 in any position, observed annual panel and all activity (place of care, public network). Denominator: INE projections based on the 2017 Census at 30 June (residence). Crude rate with exact Poisson CI; directly standardised rate with the WHO standard population (five-year groups, 80+) and Fay–Feuer gamma CI. Episodes without valid age or sex are included in the crude rate and excluded from the standardised rate. Complementary reading of episodes per population; not prevalence or incidence of autism."}[lang]}
    # A05 estandarizadas
    av = a05[a05.variant.isin([STRICT_REM, variant])].copy()
    av["order"] = av.variant.map({STRICT_REM: 0, variant: 1})
    av = av.sort_values(["order", "sex", "year"])
    at = pd.DataFrame({
        tr("series", lang): av.variant.map(lambda v: tr("var_strict_autism", lang) if v == STRICT_REM else f"{tr('var_family', lang)}: {vlab}"),
        tr("sex", lang): av.sex.map(lambda s: tr(s, lang)), tr("year", lang): av.year,
        tr("count_entries", lang): av["count"].map(lambda v: C.fmt_number(v, 0, lang)),
        tr("estab", lang): av.n_reporting_establishments.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("population", lang): av.population.map(lambda v: C.fmt_number(v, 0, lang)),
        tr("crude", lang): [f"{C.fmt_number(r.crude, 1, lang)} ({C.fmt_ci(r.crude_lo, r.crude_hi, 1, lang)})" for r in av.itertuples()],
        tr("asr", lang): [f"{C.fmt_number(r.asr, 1, lang)} ({C.fmt_ci(r.asr_lo, r.asr_hi, 1, lang)})" for r in av.itertuples()],
    })
    C.atomic_write_csv(at, tdir / "S_a05_standardised_rates.csv")
    C.atomic_write_csv(av.drop(columns="order"), tdir / "S_a05_standardised_rates_numeric.csv")
    titles["S_a05_standardised_rates"] = {
        "title": {"es": f"{tab_word} S7. Ingresos REM A05 por autismo por 100.000 habitantes, brutos y estandarizados por edad (OMS), según sexo y año, 2021–2025 — variante {vlab}",
                  "en": f"{tab_word} S7. REM A05 autism entries per 100,000 population, crude and WHO age-standardised, by sex and year, 2021–2025 — {vlab} variant"}[lang],
        "note": {"es": "Ingresos a programas de salud mental por autismo estricto (código 05990022) y por la familia TGD de la variante (05990022–05990026, sin 05990024 en la variante sin Rett), sumados sobre las celdas edad × sexo de las filas en era (2021–2025); el TGD amplio 2019–2020 es otra definición y no se incluye. Número de establecimientos reportantes por año (2025: 952 frente a 1.070 en 2024). Denominador INE base 2017 (residencia) frente a numerador por lugar de atención (red pública): lectura complementaria. Tasa bruta con IC exacto de Poisson; estandarización directa OMS con IC de Fay–Feuer. Las intervenciones reportadas son actividad administrativa, no prevalencia.",
                 "en": "Mental-health programme entries for strict autism (code 05990022) and for the variant's PDD family (05990022–05990026, without 05990024 in the without-Rett variant), summed over the age × sex cells of in-era rows (2021–2025); broad PDD 2019–2020 is a different definition and is not included. Number of reporting establishments per year (2025: 952 vs 1,070 in 2024). INE base-2017 denominator (residence) against a place-of-care numerator (public network): complementary reading. Crude rate with exact Poisson CI; direct WHO standardisation with Fay–Feuer CI. Reported entries are administrative activity, not prevalence."}[lang]}
    # Índices de convergencia
    cv = conv[conv.variant == variant]
    piv = cv[cv.index_base_year == 2021].pivot(index="year", columns="series", values="index")
    piv19 = cv[cv.index_base_year == 2019].pivot(index="year", columns="series", values="index")
    order = ["grd_any_rate", "grd_principal_rate", "deis_principal_rate", "a05_strict_entries", "a05_family_entries", "p2_december_stock", "p6_primary_strict_stock", "pie_harmonised"]
    names = {"grd_any_rate": {"es": "GRD F84 cualquier posición (tasa por 100.000 episodios)", "en": "GRD F84 any position (rate per 100,000 episodes)"},
             "grd_principal_rate": {"es": "GRD F84 principal (tasa por 100.000 episodios)", "en": "GRD F84 principal (rate per 100,000 episodes)"},
             "deis_principal_rate": {"es": "DEIS F84 principal (tasa por 100.000 egresos)", "en": "DEIS F84 principal (rate per 100,000 discharges)"},
             "a05_strict_entries": {"es": "A05 ingresos autismo estricto (conteo)", "en": "A05 strict autism entries (count)"},
             "a05_family_entries": {"es": "A05 ingresos familia TGD, variante (conteo)", "en": "A05 PDD-family entries, variant (count)"},
             "p2_december_stock": {"es": "P2 TEA bajo control, diciembre (stock)", "en": "P2 ASD under control, December (stock)"},
             "p6_primary_strict_stock": {"es": "P6 APS autismo estricto, diciembre (stock)", "en": "P6 primary-care strict autism, December (stock)"},
             "pie_harmonised": {"es": "PIE armonizado TEA + Asperger (stock escolar)", "en": "Harmonised PIE ASD + Asperger (school stock)"}}
    ct = pd.DataFrame({tr("year", lang): piv.index})
    for s in order:
        ct[f"{names[s][lang]} — {tr('index', lang)}"] = [C.fmt_number(v, 1, lang) for v in piv[s].reindex(piv.index)]
    for s in [o for o in order if o in piv19.columns]:
        ct[f"{names[s][lang]} — {tr('index2019', lang)}"] = [C.fmt_number(v, 1, lang) for v in piv19[s].reindex(piv.index)]
    C.atomic_write_csv(ct, tdir / "S_convergence_index.csv")
    C.atomic_write_csv(cv, tdir / "S_convergence_index_numeric.csv")
    titles["S_convergence_index"] = {
        "title": {"es": f"{tab_word} S8. Índices de crecimiento (2021 = 100; 2019 = 100 cuando la serie existe) de los indicadores administrativos de autismo por sistema, 2019–2025 — variante {vlab}",
                  "en": f"{tab_word} S8. Growth indices (2021 = 100; 2019 = 100 where the series exists) of administrative autism indicators by system, 2019–2025 — {vlab} variant"}[lang],
        "note": {"es": "Índices, no niveles: cada serie tiene su propia unidad (tasa por episodios/egresos, conteo de ingresos o stock), denominador, cobertura y era de definición, y las fuentes no se enlazan por persona. 2021 es el primer año común (los códigos A05 de autismo existen desde 2021); GRD y DEIS terminan en 2024. GRD y DEIS: tasas por 100.000 episodios/egresos (panel observado, toda modalidad); A05: ingresos anuales (flujo); P2 y P6: stocks de diciembre; PIE: stock escolar anual armonizado (Apuntes 60 hasta 2023, SINACES desde 2024). 2020–2021 fueron años de disrupción del reporte.",
                 "en": "Indices, not levels: each series has its own unit (rate per episodes/discharges, entry count or stock), denominator, coverage and definition era, and the sources are not linked at the person level. 2021 is the first common year (A05 autism codes exist from 2021); GRD and DEIS end in 2024. GRD and DEIS: rates per 100,000 episodes/discharges (observed panel, all activity); A05: annual entries (flow); P2 and P6: December stocks; PIE: harmonised annual school stock (Apuntes 60 to 2023, SINACES from 2024). 2020–2021 were reporting-disruption years."}[lang]}
    merge_json(tdir / "titles.json", titles)
    return titles


# ---------------------------------------------------------------------------
# Láminas (estilo paper/figures.py: 2x3, 17x10.8 in, 600 dpi, Okabe–Ito)
# ---------------------------------------------------------------------------
OK = C.OKABE
SEXCOL = {"HOMBRE": OK[0], "MUJER": OK[1], "TOTAL": "#333333"}


def _num(x, dec=1, lang="es"):
    return C.fmt_number(x, dec, lang)


_POS = {"top": (0.97, "top"), "mid": (0.55, "center"), "bottom": (0.03, "bottom")}


def _context(ax, lang, law=True, pandemic="top", law_pos="top", shade=DISRUPTION_YEARS, law_ha="left"):
    """Sombrea 2020–2021 (disrupción del reporte) y marca la Ley 21.545 como contexto (línea punteada, nunca intervención).

    `law_ha='right'` escribe la marca de la Ley a la IZQUIERDA de su línea. En los paneles cuya serie sube
    justo después de 2023 (S4 d, S7 f) el hueco está antes de la línea, no después: escrita a la derecha, la
    marca caía sobre la serie que la lámina describe."""
    C.shade_years(ax, shade)
    y, va = _POS[pandemic]
    ax.text(2020.5, y, tr("fig_pandemic", lang), transform=ax.get_xaxis_transform(), ha="center", va=va, fontsize=7.5, color="#555555")
    if law:
        x = LAW_YEAR - 0.35
        ax.axvline(x, color="#444444", ls=":", lw=1.2, zorder=1)
        y, va = _POS[law_pos]
        dx = 0.06 if law_ha == "left" else -0.06
        ax.text(x + dx, y, tr("fig_law", lang), transform=ax.get_xaxis_transform(), ha=law_ha, va=va, fontsize=7.5, color="#444444")


# ---------------------------------------------------------------------------
# Norma de lámina: 180 × 245 mm en vertical, dibujada 1:1 (una lámina por página, sin reducción)
# 3 filas × 2 columnas, seis paneles como máximo, letras minúsculas, nada bajo 6 pt, 600 dpi.
# ---------------------------------------------------------------------------
PLATE_W_MM, PLATE_H_MM = 180.0, 245.0
MM_PER_IN = 25.4
PLATE_SIZE = (PLATE_W_MM / MM_PER_IN, PLATE_H_MM / MM_PER_IN)
FS_BASE, FS_TITLE, FS_TICK, FS_LEG, FS_MIN = 8.0, 9.0, 7.0, 7.0, 6.0
PLATE_TITLE_W_PT = (PLATE_W_MM / MM_PER_IN * 72.0) / 2 - (4.0 / MM_PER_IN * 72.0)
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


def new_plate(plt, nrows: int = 3, ncols: int = 2, **kw):
    fig, ax = plt.subplots(nrows, ncols, figsize=PLATE_SIZE, constrained_layout=True, **kw)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    return fig, ax


def panel_head(ax, letter_: str, title: str, fs: float = FS_TITLE, pad: float = 3.0) -> None:
    """Cabecera del panel: letra minúscula y título a la izquierda de SU celda, plegados al ancho medido."""
    ax.set_title("", loc="center"); ax.set_title("", loc="right")
    ax.set_title(C.plate_wrap(f"({letter_}) {title}", PLATE_TITLE_W_PT, fs, "bold"),
                 loc="left", fontsize=fs, fontweight="bold", pad=pad, linespacing=1.15)


def plate_legend(ax, *args, loc: str = "upper left", fs: float | None = None, ncol: int = 1, **kw):
    """Leyenda de celda estrecha: cuerpo 6,2 pt y recuadro blanco translúcido sobre las series."""
    lg = ax.legend(*args, loc=loc, fontsize=fs if fs is not None else FS_MIN + 0.2, ncol=ncol,
                   frameon=True, framealpha=0.82, edgecolor="none", facecolor="white", borderpad=0.25, **kw)
    lg.set_zorder(6)
    # Una leyenda ancha SÍ gobierna el reparto de `constrained_layout`: con etiquetas largas encogía los ejes
    # de la celda hasta colapsarlos. La que se dibuja DENTRO del panel se saca del reparto; la que se ancla
    # fuera (bbox_to_anchor, bajo el eje) tiene que seguir en él para que se le reserve sitio.
    if "bbox_to_anchor" not in kw:
        lg.set_in_layout(False)
    return lg


def freeze_texts(fig) -> None:
    """Los rótulos sueltos no gobiernan el reparto del lienzo: colapsarían los ejes de la celda."""
    for ax in fig.axes:
        for t in ax.texts:
            t.set_in_layout(False)


def localise_ticks(fig, lang: str) -> None:
    """Separador de miles del idioma en TODAS las marcas numéricas de la lámina (español 20.000, inglés 20,000).

    Los paneles de esta lámina no llamaban a ningún formateador y por eso imprimían «50000», «160000» o
    «35000» a secas, que no es la convención de ninguno de los dos idiomas mientras el resto del estudio
    escribe «50.000» / «50,000». Se recorre la lámina entera justo antes de componerla para que ningún panel
    se quede fuera. Un eje de AÑOS se reconoce por sus marcas (enteros entre 1900 y 2100 en un rango de 40
    años) y se deja como está: el año no lleva separador. Los ejes con rótulos fijos o escala logarítmica ya
    traen su propio formateador y no se tocan."""
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
            axis.set_major_formatter(FuncFormatter(lambda v, _p, dec=dec, lang=lang: _num(v, dec, lang)))


def fit_left_decorations(fig, margin_px: float = 1.5) -> None:
    """Devuelve a SU celda las marcas y el rótulo del eje Y que asoman por la izquierda.

    `constrained_layout` reparte el ancho del lienzo, no el de la celda nominal de la rejilla: en la columna
    derecha las marcas «40.000» / «160.000» y el rótulo girado empezaban a la izquierda del borde de la
    celda, y la guarda de recorte de `common.py` («nada sale de su celda») los devolvía dentro empujando el
    rótulo doce píxeles a la derecha, justo encima de las marcas que rotula. Ese es el defecto de los paneles
    (d) y (f) de la Figura S7. Aquí, con la composición ya congelada, se estrecha el panel por la izquierda
    lo justo para que la columna de marcas y su rótulo quepan dentro de la celda: el rótulo se queda donde lo
    puso `plate_ylabel` y la guarda de recorte ya no tiene nada que empujar. El panel pierde unos pocos
    píxeles de ancho; el rótulo, ninguno."""
    fig.canvas.draw()
    r = C._pl_renderer(fig, draw=False)
    groups = {}
    for ax in fig.axes:
        if not ax.get_visible() or not hasattr(ax, "get_subplotspec") or ax.get_subplotspec() is None:
            continue
        pos = ax.get_position()
        groups.setdefault((round(pos.x0, 6), round(pos.y0, 6), round(pos.x1, 6), round(pos.y1, 6)), []).append(ax)
    for _, axes in groups.items():
        cell = C.plate_cell_box(fig, axes[0])
        left = None
        for ax in axes:
            arts = list(ax.yaxis.get_ticklabels()) + [ax.yaxis.label]
            if ax.yaxis.get_label_position() == "right":
                arts = [a for a in arts if a is not ax.yaxis.label]
            for a in arts:
                if a is None or not a.get_visible() or not str(a.get_text()).strip():
                    continue
                b = C._pl_extent(a, r)
                if b is not None:
                    left = b.x0 if left is None else min(left, b.x0)
        if left is None:
            continue
        deficit = (cell.x0 + margin_px) - left
        if deficit <= 0.5:
            continue
        dx = deficit / float(fig.bbox.width)
        for ax in axes:
            pos = ax.get_position()
            if pos.width - dx <= 0.05:
                continue
            ax.set_position([pos.x0 + dx, pos.y0, pos.width - dx, pos.height])
    fig.canvas.draw()


def _forest_layout(fig) -> None:
    """Reserva a la derecha de cada «forest» la COLUMNA que ocupan sus valores, ya medida.

    Cada fila escribía su «57,8 (34,9; 84,6)» a 1,5 unidades de SU propio extremo superior. En las filas de
    intervalo ancho ese punto de partida cae tan a la derecha que el rótulo se sale del panel, y la guarda de
    recorte lo devuelve dentro imprimiéndolo sobre la mitad derecha de su propio intervalo: el lector ya no
    sabe dónde acaba la barra. Aquí se mide el rótulo más ancho con la composición YA resuelta, se ensancha
    el eje lo justo para que quepa esa columna a la derecha del dato mayor y se alinean todos los rótulos en
    esa columna. Nada se sale, nada se imprime sobre un intervalo y la lectura es la de una tabla."""
    r = C._pl_renderer(fig)
    for ax in fig.axes:
        info = getattr(ax, "_forest_column", None)
        if not info or not info["texts"]:
            continue
        width = 0.0
        for t in info["texts"]:
            b = C._pl_extent(t, r)
            if b is not None:
                width = max(width, b.width)
        axw = float(ax.bbox.width)
        if axw <= 1.0 or width <= 0.0:
            continue
        frac = min(0.60, (width + 0.05 * axw) / axw)     # columna de valores + un respiro
        lo_, hi_ = info["lo"], info["hi"]
        left = lo_ - 0.05 * (hi_ - lo_ + 1.0)
        right = left + (hi_ - left) / max(1e-6, 1.0 - frac)
        ax.set_xlim(left, right)
        x_lab = left + (1.0 - frac + 0.012) * (right - left)
        for t in info["texts"]:
            t.set_x(x_lab)
    fig.canvas.draw()


def plate_ylabel(ax, text: str, **kw):
    """`C.plate_ylabel` recordando el encargo, para volver a medirlo cuando cambien las marcas.

    El rótulo se coloca a partir del ANCHO YA MEDIDO de la columna de marcas: si después se le pone al eje el
    separador de miles del idioma («50000» → «50.000»), esa columna se ensancha y el rótulo volvería a caer
    encima. Por eso el encargo queda anotado en el eje y `save_plate` lo repite con las marcas definitivas."""
    ax._plate_ylabel = (str(text), dict(kw))
    return C.plate_ylabel(ax, text, **kw)


def _reapply_ylabels(fig) -> None:
    for ax in fig.axes:
        job = getattr(ax, "_plate_ylabel", None)
        if job:
            C.plate_ylabel(ax, job[0], **job[1])


def save_plate(fig, path: Path, dpi: int = 600, lang: str | None = None) -> Path:
    """Guarda sin recorte: el archivo mide exactamente 180 × 245 mm a 600 ppp (1:1 en la página)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    freeze_texts(fig)
    # Motor de descongestión (common.py): mide lo dibujado y resuelve colisiones, recortes y leyendas.
    # `plate_fit` actúa con la composición todavía viva (marcas de eje, rótulos de eje, leyendas);
    # `plate_resolve`, ya congelada, separa los rótulos que se pisan y devuelve dentro lo que se sale.
    # El separador de miles y el rótulo del eje Y se fijan ANTES: los dos cambian el ancho que mide el motor.
    if lang is not None:
        localise_ticks(fig, lang)
    _reapply_ylabels(fig)
    C.plate_fit(fig)
    C.plate_align_titles(fig)
    fit_left_decorations(fig)
    _forest_layout(fig)
    _reapply_ylabels(fig)
    C.plate_frame_notes(fig)
    C.plate_resolve(fig)
    # Modo revista (LANCET_PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    fig.savefig(path, dpi=dpi, facecolor="white")
    return path


_FOREST_PERIOD = ""


def _forest_strip_period(rows, lang):
    """Saca de la etiqueta el periodo que comparte la mayoría de las filas y lo guarda para el eje X."""
    global _FOREST_PERIOD
    _FOREST_PERIOD = ""
    tails = [str(r[0]).rsplit(" · ", 1)[-1] for r in rows]
    # Los candidatos se recorren en ORDEN DE APARICIÓN, no en el de una tabla hash: el orden de un `set` de
    # cadenas cambia con PYTHONHASHSEED, y `max(...)` devuelve el primer máximo, así que con dos periodos
    # empatados la lámina salía distinta de una ejecución a otra sin que cambiara ni un dato.
    common = [t for t in dict.fromkeys(tails) if tails.count(t) > 1 and any(ch.isdigit() for ch in t)]
    if not common:
        return rows
    modal = max(common, key=tails.count)
    if tails.count(modal) < max(2, len(rows) // 2):
        return rows
    _FOREST_PERIOD = {"es": f"salvo indicación, {modal}", "en": f"unless stated, {modal}"}[lang]
    out = []
    for r, tail in zip(rows, tails):
        lab = str(r[0])
        if tail == modal and " · " in lab:
            lab = lab.rsplit(" · ", 1)[0]
        out.append((lab,) + tuple(r[1:]))
    return out


def _forest(ax, rows, lang, xlabel, ref=0.0, key=None):
    """Diagrama de bosque de especificaciones, con la etiqueta del modelo en el eje Y.

    La etiqueta va SIEMPRE en una línea. Con quince especificaciones el paso entre filas es de unos 10 pt y
    una etiqueta plegada en dos líneas mide 15: plegarla imprimía tres filas una encima de otra e ilegibles
    (defecto S4c). Para que quepa en una línea se saca de la etiqueta el periodo que comparten casi todas las
    filas y se declara en el rótulo del eje X; las filas con otro periodo lo conservan."""
    rows = _forest_strip_period(rows, lang)
    n = len(rows)
    values = []
    for i, (lab, e, lo, hi, col) in enumerate(rows):
        y = n - 1 - i
        if pd.isna(e):
            values.append(ax.text(ref, y, tr("na", lang), va="center", fontsize=FS_MIN, color="#777777"))
            continue
        ax.plot([lo, hi], [y, y], color=col, lw=2.0, zorder=2)
        ax.scatter(e, y, s=40, color=col, zorder=3, edgecolor="white", linewidth=1)
        # El valor va en una COLUMNA a la derecha, no a 1,5 unidades del extremo de SU intervalo: la x
        # definitiva la fija `_forest_layout` cuando el ancho del panel ya está resuelto (ver allí).
        values.append(ax.text(max(hi, ref) + 1.5, y, f"{_num(e, 1, lang)} ({_num(lo, 1, lang)}; {_num(hi, 1, lang)})",
                              va="center", ha="left", fontsize=FS_MIN, color="#333333"))
    ax.axvline(ref, color="#888888", ls="--", lw=1.0, zorder=0)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=FS_MIN)
    ax.set_xlabel(xlabel if not _FOREST_PERIOD else f"{xlabel} · {_FOREST_PERIOD}")
    finite = [v for r in rows for v in (r[2], r[3]) if pd.notna(v)]
    if finite:
        lo_, hi_ = min(finite + [ref]), max(finite + [ref])
        ax.set_xlim(lo_ - 0.05 * (hi_ - lo_ + 1), hi_ + 0.55 * (hi_ - lo_ + 1))
        ax._forest_column = dict(texts=values, lo=float(lo_), hi=float(hi_))
    ax.margins(y=0.05)
    if key:
        # La clave de color se dibuja en una BANDA RESERVADA bajo la última fila, no sobre las filas: una
        # leyenda flotante caía sobre los intervalos de las tres últimas y empujaba sus valores a la fila
        # vecina, con lo que el número dejaba de poder atribuirse a su especificación.
        from matplotlib.lines import Line2D
        ax.set_ylim(-0.6 - 1.25 * len(key), n - 1 + 0.6)
        lg = ax.legend([Line2D([], [], color=c, lw=2.4) for c, _ in key], [t for _, t in key],
                       loc="lower left", fontsize=FS_MIN, ncol=1, frameon=True, framealpha=0.85,
                       edgecolor="none", facecolor="white", borderpad=0.25, handlelength=1.4,
                       handletextpad=0.5, labelspacing=0.25)
        lg.set_gid(C.PLATE_KEEP); lg.set_zorder(6); lg.set_in_layout(False)


def _fit_series(Fd: pd.DataFrame, mid: str) -> pd.DataFrame:
    return Fd[Fd.model_id == mid].sort_values("year")


def _plot_fit(ax, Fd, mid, color, label, lang, marker="o", ls="-", band=True, obs_ci=True, offset=0.0):
    f = _fit_series(Fd, mid)
    if f.empty:
        return
    # Una sola entrada de leyenda por serie: el marcador es lo observado con su IC y la línea el ajuste, y el
    # pie lo dice. Dos entradas por serie doblaban la leyenda y la sacaban de la celda.
    if obs_ci:
        ax.errorbar(f.year + offset, f.observed_rate, yerr=[f.observed_rate - f.observed_lo, f.observed_hi - f.observed_rate], fmt=marker, color=color, capsize=2.5,
                    markersize=5.5, lw=1.4, ls=ls, label=str(label), zorder=3)
    else:
        ax.plot(f.year + offset, f.observed_rate, marker, color=color, markersize=5.5, label=str(label), zorder=3)
    ax.plot(f.year + offset, f.fitted_rate, ls=ls, color=color, lw=2.0, zorder=2)
    if band:
        ax.fill_between(f.year + offset, f.fitted_lo, f.fitted_hi, color=color, alpha=0.13, zorder=1)


def _short(summary_row, lang):
    r = summary_row
    p = {"panel_observed": {"es": "obs.", "en": "obs."}, "panel_fixed65": {"es": "fijo 65", "en": "fixed 65"}, "panel_stable": {"es": "panel estable", "en": "stable panel"},
         "panel_all_estab": {"es": "", "en": ""}, "panel_national": {"es": "", "en": ""}}
    a = {"act_all": {"es": "toda", "en": "all"}, "act_hospitalisation": {"es": "hosp.", "en": "hosp."}, "act_na": {"es": "", "en": ""}}
    pos = {"pos_any": {"es": "cualq.", "en": "any"}, "pos_principal": {"es": "princ.", "en": "princ."}, "pos_na": {"es": "", "en": ""}}
    cov = {"cov_none": {"es": "", "en": ""}, "cov_depth": {"es": "+profundidad", "en": "+depth"}, "cov_disruption": {"es": "+disrupción", "en": "+disruption"},
           "cov_depth_disruption": {"es": "+prof.+disr.", "en": "+depth+disr."}, "cov_age": {"es": "ajust. edad", "en": "age-adj."}, "cov_disruption_2021": {"es": "+disr. 2021", "en": "+disr. 2021"},
           "cov_hospital_fe": {"es": "EF hospital", "en": "hospital FE"}, "cov_hospital_fe_depth": {"es": "EF hospital +prof.", "en": "hospital FE +depth"},
           "cov_hospital_fe_disruption": {"es": "EF hospital +disr.", "en": "hospital FE +disr."}, "cov_hospital_ri": {"es": "IA hospital", "en": "hospital RI"},
           "cov_hospital_ri_depth": {"es": "IA hospital +prof.", "en": "hospital RI +depth"}}
    off = {"off_episodes": "", "off_hosp_episodes": "", "off_pop": {"es": "/pobl. INE", "en": "/INE pop."}, "off_estab": {"es": "/establec.", "en": "/estab."},
           "off_none": {"es": "conteo", "en": "count"}, "off_naneas": {"es": "/100 NANEAS", "en": "/100 NANEAS"}, "off_discharges": ""}
    parts = [p.get(r.panel, {}).get(lang, "") if isinstance(p.get(r.panel), dict) else "", a[r.activity][lang], pos[r.position][lang], cov[r.covariates][lang]]
    o = off.get(r.denominator_offset, "")
    parts.append(o if isinstance(o, str) else o[lang])
    if r.model_family == "fam_qp_fe_cluster":
        parts.append({"es": "EE robustos", "en": "robust SE"}[lang])
    y0, y1 = r.years.split("-")
    return " · ".join([x for x in parts if x]) + f" · {y0}–{y1[2:]}"


def figure_models(S: Store, summary: pd.DataFrame, Fd: pd.DataFrame, pop: pd.DataFrame, conv: pd.DataFrame, variant: str, lang: str) -> dict:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    v = variant
    fig, ax = new_plate(plt)
    # A — tasa GRD cualquier posición: observado y ajustado, panel observado y fijo
    a = ax[0, 0]
    _plot_fit(a, Fd, f"grd_rate:{v}:observed:all:any:none:2019-2024", OK[0], tr("fig_any_obs", lang), lang, "o", "-")
    _plot_fit(a, Fd, f"grd_rate:{v}:fixed65:all:any:none:2019-2024", OK[1], tr("fig_any_fixed", lang), lang, "s", "--", offset=0.08)
    f = _fit_series(Fd, f"grd_rate:{v}:observed:all:any:none:2019-2024")
    _context(a, lang, pandemic="mid", law_pos="bottom")
    # El n de hospitales va BAJO SU AÑO, no flotando sobre la serie: el panel observado tiene 65 hospitales
    # en 2019 y en 2020, y los dos rótulos se imprimían uno sobre otro («n=6n=65», «n=(n=65)» en español).
    # Es la misma solución que ya usan los paneles (a) y (b) de la Figura S7 para los establecimientos.
    nrep = {int(r.year): int(r.reporting_n) for r in f.itertuples()}
    a.set_xticks(CFG.YEARS_GRD)
    a.set_xticklabels([f"{y}\nn={nrep[y]}" if y in nrep else str(y) for y in CFG.YEARS_GRD], fontsize=FS_MIN + 0.2)
    a.set_xlabel(tr("fig_grd_estab", lang)); plate_ylabel(a, tr("fig_rate_axis", lang)); a.set_ylim(0, f.observed_hi.max() * 1.45)
    plate_legend(a); panel_head(a, "a", tr("fig_title_a", lang))
    # B — F84 principal GRD (observado/fijo) y DEIS principal
    b = ax[0, 1]
    _plot_fit(b, Fd, f"grd_rate:{v}:observed:all:principal:none:2019-2024", OK[0], tr("fig_prin_obs", lang), lang, "o", "-")
    _plot_fit(b, Fd, f"grd_rate:{v}:fixed65:all:principal:none:2019-2024", OK[1], tr("fig_prin_fixed", lang), lang, "s", "--", offset=0.08)
    _plot_fit(b, Fd, f"deis_principal:{v}:none:2019-2024", OK[2], tr("fig_deis_prin", lang), lang, "^", "-.", offset=-0.08)
    _context(b, lang, pandemic="bottom", law_pos="bottom")
    fb = _fit_series(Fd, f"grd_rate:{v}:observed:all:principal:none:2019-2024")
    b.set_xticks(CFG.YEARS_GRD); b.set_xlabel(tr("year", lang)); plate_ylabel(b, tr("fig_principal_axis", lang)); b.set_ylim(0, fb.observed_hi.max() * 1.55)
    plate_legend(b); panel_head(b, "b", tr("fig_title_b", lang))
    # c — forest GRD
    c = ax[1, 0]
    sm_ = summary.set_index("model_id")
    ids = [m.format(v=v) for m in MAIN_IDS["grd"][:11]] + [f"grd_hospital:{v}:observed:any:none:2019-2024:model", f"grd_hospital:{v}:observed:any:depth:2019-2024:model",
                                                          f"grd_hospital:{v}:observed:any:ri_none:2019-2024:random_intercept", f"grd_pop:{v}:any:TOTAL:age_adjusted:2019-2024"]
    rows = []
    for mid in ids:
        if mid not in sm_.index:
            continue
        r = sm_.loc[mid]
        col = OK[0] if r.estimand == "est_grd_rate" and r.position == "pos_any" else (OK[1] if r.position == "pos_principal" else (OK[2] if r.estimand == "est_grd_hospital" else OK[3]))
        rows.append((_short(r, lang), r.apc, r.apc_lo, r.apc_hi, col))
    # El estimando (tasa por episodios, hospital-año, por población) iba delante de CADA etiqueta y se
    # llevaba 40 pt de los 90 mm de la celda, obligando a plegarla en dos o tres líneas ilegibles: aquí lo
    # dice el color y la clave lo traduce una sola vez, en una banda propia bajo las filas.
    key = list(zip([OK[0], OK[1], OK[2], OK[3]],
                   {"es": ["tasa por episodios · cualquier posición", "tasa por episodios · principal",
                           "hospital-año", "por 100.000 habitantes"],
                    "en": ["rate per episodes · any position", "rate per episodes · principal",
                           "hospital-year", "per 100,000 population"]}[lang]))
    _forest(c, rows, lang, tr("apc_axis", lang), key=key)
    panel_head(c, "c", tr("fig_title_c", lang))
    # d — por población: bruta y estandarizada por sexo
    d = ax[1, 1]
    pv = pop[(pop.variant == v) & (pop.position == "any")]
    for sex in ["HOMBRE", "MUJER", "TOTAL"]:
        s = pv[pv.sex == sex].sort_values("year")
        d.plot(s.year, s.crude, "o:", color=SEXCOL[sex], lw=1.4, markersize=5, label=f"{tr(sex, lang)} · {tr('crude_short', lang)}")
        d.plot(s.year, s.asr, "s-", color=SEXCOL[sex], lw=2.0, markersize=5, label=f"{tr(sex, lang)} · {tr('asr_short', lang)}")
        d.fill_between(s.year, s.asr_lo, s.asr_hi, color=SEXCOL[sex], alpha=0.12)
    # La leyenda de seis entradas ocupa la franja superior del panel: la marca de la Ley se escribía ahí
    # («Ambos sexos · estandarizada OMS» sobre «Ley 21.545») y va al pie, donde ninguna serie llega antes de
    # 2024. Después se mide la leyenda y se lleva a la primera posición que no tape dato ni marca.
    _context(d, lang, pandemic="mid", law_pos="mid", law_ha="right")
    d.set_xticks(CFG.YEARS_GRD); d.set_xlabel(tr("year", lang)); plate_ylabel(d, tr("fig_pop_axis", lang)); d.set_ylim(0, pv.asr_hi.max() * 1.5)
    lg_d = plate_legend(d, ncol=1); C.plate_place_legend(d, lg_d, outside_below=False, prefer=("upper left", "upper center"))
    panel_head(d, "d", tr("fig_title_d", lang))
    # f — forest REM / educación / DEIS
    e = ax[2, 1]
    ids = ["a05_entry:strict_autism:pop:none:2021-2025", "a05_entry:strict_autism:estab:none:2021-2025", "a05_entry:strict_autism:stable_pop:none:2021-2025",
           "a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025", f"a05_entry:{v}:pop:none:2021-2025", "p2_dec:none:2019-2025", "p2_dec:estab:2019-2025",
           "p2_dec:none_disruption:2019-2025", "p2_dec:none:2021-2025", "p2_dec:naneas:2023-2025", "p6_primary:strict_autism:none:2021-2025", "p6_primary:strict_autism:estab:2021-2025",
           "p6_specialty:strict_autism:none:2021-2025", "pie_harmonised:none:2019-2025", "pie_harmonised:none:2019-2023", f"deis_principal:{v}:none:2019-2024"]
    pre = {"est_a05": "A05 ", "est_a05_pop": "A05 ", "est_p2": "P2 ", "est_p2_naneas": "P2 ", "est_p6_primary": "P6 APS ", "est_p6_specialty": {"es": "P6 espec. ", "en": "P6 spec. "}[lang],
           "est_pie": "PIE ", "est_deis": "DEIS "}
    colmap = {"est_a05": OK[2], "est_a05_pop": OK[2], "est_p2": OK[3], "est_p2_naneas": OK[3], "est_p6_primary": OK[4], "est_p6_specialty": OK[4], "est_pie": OK[5], "est_deis": OK[6]}
    rows = []
    for mid in ids:
        if mid not in sm_.index:
            continue
        r = sm_.loc[mid]
        lab = pre[r.estimand] + ({"es": "familia ", "en": "family "}[lang] if r.variant in VARIANTS and r.estimand.startswith("est_a05") else "") + _short(r, lang)
        rows.append((lab, r.apc, r.apc_lo, r.apc_hi, colmap[r.estimand]))
    _forest(e, rows, lang, tr("apc_axis", lang))
    panel_head(e, "f", tr("fig_title_f", lang))
    # e — índices de convergencia
    f_ = ax[2, 0]
    cv = conv[(conv.variant == v) & (conv.index_base_year == 2021)]
    names = {"grd_any_rate": {"es": "GRD F84 cualquier posición (tasa/episodios)", "en": "GRD F84 any position (rate/episodes)"},
             "deis_principal_rate": {"es": "DEIS F84 principal (tasa/egresos)", "en": "DEIS F84 principal (rate/discharges)"},
             "a05_strict_entries": {"es": "A05 ingresos autismo (flujo)", "en": "A05 autism entries (flow)"},
             "p2_december_stock": {"es": "P2 TEA diciembre (stock)", "en": "P2 ASD December (stock)"},
             "p6_primary_strict_stock": {"es": "P6 APS autismo diciembre (stock)", "en": "P6 primary autism December (stock)"},
             "pie_harmonised": {"es": "PIE armonizado (stock escolar)", "en": "Harmonised PIE (school stock)"}}
    mk = {"grd_any_rate": "o", "deis_principal_rate": "^", "a05_strict_entries": "s", "p2_december_stock": "D", "p6_primary_strict_stock": "v", "pie_harmonised": "P"}
    f_.set_yscale("log")
    f_.set_xlim(2020.6, 2025.9)          # columna reservada a la derecha para el valor final de cada serie
    for i, s in enumerate(names):
        z = cv[cv.series == s].sort_values("year")
        z = z[z.year >= 2021]
        f_.plot(z.year, z["index"], marker=mk[s], ls="-", color=OK[i], lw=2.0, markersize=6, label=names[s][lang])
    f_.axhline(100, color="#999999", ls="--", lw=1)
    # Franja libre reservada arriba para la leyenda de seis series: con 4,5 el borde inferior de la leyenda
    # rozaba la serie P6 en 2024 (3 % de la línea tapada) en la lámina española, cuyos rótulos son más largos.
    f_.set_ylim(70, cv["index"].max() * 6.0)
    # El valor final se coloca MIDIENDO: con `annotate(xytext=(4, 0))` los seis rótulos del último año caían
    # fuera del panel, la guarda de recorte los devolvía dentro y acababan lejos de su marcador (el «968» del
    # P6 impreso a media altura, sin punto al lado). `plate_value_label` esquiva marcadores y rótulos ya
    # colocados y se queda dentro del eje.
    last = []
    for i, s in enumerate(names):
        z = cv[cv.series == s].sort_values("year")
        z = z[z.year >= 2021]
        last.append((float(z["index"].iloc[-1]), float(z.year.iloc[-1]), OK[i]))
    # De arriba abajo: el rótulo de la serie más alta se coloca primero y se queda a la derecha de su punto;
    # los de abajo esquivan. Colocados en el orden de la leyenda, el «968» del P6 acababa impreso bajo el
    # «778» del P2, es decir en el orden inverso al de sus marcadores.
    for value, year, col in sorted(last, key=lambda q: -q[0]):
        C.plate_value_label(f_, year, value, _num(value, 0, lang), fontsize=FS_MIN, color=col,
                            ha="left", va="center", prefer=((1, 0), (1, 1), (1, -1), (0, 1), (0, -1)))
    C.shade_years(f_, [2021])
    x = LAW_YEAR - 0.35
    f_.axvline(x, color="#444444", ls=":", lw=1.2); f_.text(x + 0.05, 0.03, tr("fig_law", lang), transform=f_.get_xaxis_transform(), fontsize=FS_MIN, va="bottom", color="#444444")
    f_.set_xticks(range(2021, 2026))
    # La nota del eje X se pliega AQUÍ, al ancho de la celda y con su cuerpo definitivo. Plegada después de
    # componer la lámina (que es lo que hacía la guarda de ancho) añadía una tercera línea para la que ya no
    # quedaba sitio reservado, y en español los 42 píxeles de la última línea se perdían por el borde
    # inferior del lienzo de 245 mm.
    f_.set_xlabel(f"{tr('year', lang)}\n{C.plate_wrap('(' + tr('fig_index_note', lang) + ')', 118.0, FS_MIN + 0.5, 'normal')}",
                  fontsize=FS_MIN + 0.5, linespacing=1.20)
    plate_ylabel(f_, tr("fig_index_axis", lang))
    lg_e = plate_legend(f_); C.plate_place_legend(f_, lg_e, outside_below=False, prefer=("upper left", "upper center"))
    panel_head(f_, "e", tr("fig_title_e", lang))
    path = save_plate(fig, fdir / "figS4_models_cpa.png", lang=lang)
    plt.close(fig)
    vlab = tr(f"var_{variant}", lang)
    fig_word = tr("figure", lang)
    cap = {"title": {"es": f"{fig_word} S4. Modelos cuasi-Poisson del reconocimiento administrativo del autismo: GRD, REM, educación y DEIS, Chile 2019–2025 — variante {vlab}",
                     "en": f"{fig_word} S4. Quasi-Poisson models of administrative recognition of autism: GRD, REM, education and DEIS, Chile 2019–2025 — {vlab} variant"}[lang],
           "caption": {"es": "(a) Episodios GRD con F84 documentado en cualquier posición por 100.000 episodios GRD (toda modalidad): puntos = observado con IC 95 % exacto de Poisson; líneas = ajuste log-lineal cuasi-Poisson 2019–2024 con offset log(episodios) y banda 95 %; panel anual observado (n = hospitales por año) y panel fijo de 65 hospitales. (b) F84 principal en GRD (observado y fijo) y egresos DEIS con F84 en DIAG1 por 100.000 egresos: comparación principal frente a principal (DEIS no publica diagnósticos secundarios). (c) Cambio porcentual anual (CPA) e IC 95 % de los modelos GRD según panel, modalidad, posición, covariables (profundidad diagnóstica media; indicador de disrupción del reporte 2020–2021, no causal), ventana (2019–2024, 2021–2024), modelos hospital-año (efectos fijos, EE robustos, intercepto aleatorio) y tasa por población ajustada por edad. (d) Episodios por 100.000 habitantes INE (base 2017, residencia; numerador por lugar de atención): tasas brutas y estandarizadas OMS por sexo, IC 95 % de Fay–Feuer. (e) Índices (2021 = 100, primer año común; escala logarítmica) de series con unidades y denominadores distintos: son índices, no niveles comparables. (f) CPA de REM A05 (ingresos por autismo 2021–2025 con offset poblacional, por establecimiento reportante, panel estable y ajuste por edad), P2 (stock TEA de diciembre 2019–2025 con y sin offset de establecimientos, indicador de disrupción, ventana 2021–2025 y por 100 NANEAS 2023–2025), P6 (stocks de diciembre 2021–2025), PIE armonizado (2019–2025; 2019–2023 solo Apuntes 60) y DEIS principal. Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto, no como intervención. Los conteos son reconocimiento administrativo, no prevalencia ni incidencia.",
                       "en": "(a) GRD episodes with documented F84 in any position per 100,000 GRD episodes (all activity): points = observed with exact Poisson 95% CI; lines = quasi-Poisson log-linear fit 2019–2024 with log(episodes) offset and 95% band; observed annual panel (n = hospitals per year) and fixed panel of 65 hospitals. (b) Principal F84 in GRD (observed and fixed) and DEIS discharges with F84 in DIAG1 per 100,000 discharges: principal-versus-principal comparison (DEIS publishes no secondary diagnoses). (c) Annual percent change (APC) and 95% CI of GRD models by panel, activity, position, covariates (mean coding depth; 2020–2021 reporting-disruption indicator, not causal), window (2019–2024, 2021–2024), hospital-year models (fixed effects, robust SE, random intercept) and age-adjusted population rate. (d) Episodes per 100,000 INE population (base 2017, residence; place-of-care numerator): crude and WHO-standardised rates by sex, Fay–Feuer 95% CI. (e) Indices (2021 = 100, first common year; log scale) of series with different units and denominators: indices, not comparable levels. (f) APC of REM A05 (autism entries 2021–2025 with population offset, per reporting establishment, stable panel and age adjustment), P2 (December ASD stock 2019–2025 with and without establishment offset, disruption indicator, 2021–2025 window and per 100 NANEAS 2023–2025), P6 (December stocks 2021–2025), harmonised PIE (2019–2025; 2019–2023 Apuntes 60 only) and DEIS principal. Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context, not intervention. Counts are administrative recognition, not prevalence or incidence."}[lang]}
    merge_json(fdir / "captions.json", {"figS4_models_cpa": cap})
    return {"figS4_models_cpa": str(path)}


def figure_rem_education(S: Store, D: dict, summary: pd.DataFrame, Fd: pd.DataFrame, a05: pd.DataFrame, variant: str, lang: str) -> dict:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    v = variant
    vlab = tr(f"var_{variant}", lang)
    fig, ax = new_plate(plt)
    yrs5 = list(range(2021, 2026))

    def rates_panel(axis, series_variant, title):
        av = a05[a05.variant == series_variant]
        for sex in ["HOMBRE", "MUJER", "TOTAL"]:
            s = av[av.sex == sex].sort_values("year")
            axis.plot(s.year, s.crude, "o:", color=SEXCOL[sex], lw=1.4, markersize=5, label=f"{tr(sex, lang)} · {tr('crude_short', lang)}")
            axis.plot(s.year, s.asr, "s-", color=SEXCOL[sex], lw=2.0, markersize=5, label=f"{tr(sex, lang)} · {tr('asr_short', lang)}")
            axis.fill_between(s.year, s.asr_lo, s.asr_hi, color=SEXCOL[sex], alpha=0.12)
        tot = av[av.sex == "TOTAL"].sort_values("year")
        C.shade_years(axis, [2021])
        x = LAW_YEAR - 0.35
        axis.axvline(x, color="#444444", ls=":", lw=1.2); axis.text(x + 0.05, 0.55, tr("fig_law", lang), transform=axis.get_xaxis_transform(), fontsize=FS_MIN, va="center", color="#444444")
        axis.set_xticks(yrs5); axis.set_xticklabels([f"{int(r.year)}\nn={int(r.n_reporting_establishments)}" for r in tot.itertuples()], fontsize=FS_MIN + 0.2)
        axis.set_xlabel(tr("rfig_a05_estab", lang)); axis.set_ylabel(tr("fig_a05_axis", lang)); axis.set_ylim(0, av.asr_hi.max() * 1.7)
        axis.set_title(title); plate_legend(axis, ncol=1)

    a = ax[0, 0]
    rates_panel(a, STRICT_REM, tr("rfig_title_a", lang)); panel_head(a, "a", tr("rfig_title_a", lang))
    b = ax[0, 1]
    rates_panel(b, v, tr("rfig_title_b", lang)); panel_head(b, "b", tr("rfig_title_b", lang))
    # c — tasas específicas por edad, 2021 y 2025, autismo estricto
    c = ax[1, 0]
    cells = D["a05_age"]
    cells = cells[(cells.flow == "entry") & (cells.variant == "single_code") & (cells.category == "autism") & (cells.age_group != "total")].copy()
    cells["sex"] = cells.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    ine = D["ine_age"]
    order = AGE_GROUPS[:8]
    x = np.arange(len(order))
    for year, ls, mk, off in [(2021, ":", "o", -0.1), (2025, "-", "s", 0.1)]:
        for sex in ["HOMBRE", "MUJER"]:
            cy = cells[(cells.year == year) & (cells.sex == sex)].groupby("age_group")["count"].sum().reindex(order).fillna(0)
            pop = ine[(ine.year == year) & (ine.sex == sex)].set_index("age_group").population.reindex(order).astype(float)
            lo, hi = C.poisson_limits(cy.values)
            rate = PER * cy.values / pop.values
            c.errorbar(x + off, rate, yerr=[rate - PER * lo / pop.values, PER * hi / pop.values - rate], fmt=mk, ls=ls, color=SEXCOL[sex], capsize=2, markersize=5, lw=1.6,
                       label=f"{tr(sex, lang)} {year}")
    c.set_xticks(x); c.set_xticklabels(order, rotation=45, ha="right"); c.set_xlabel(tr("rfig_age_axis", lang)); c.set_ylabel(tr("fig_a05_axis", lang))
    plate_legend(c, loc="upper right"); panel_head(c, "c", tr("rfig_title_c", lang))
    # d — P2 diciembre: observado, ajuste sin offset y con offset de establecimientos; junio como marcador; establecimientos en eje secundario
    d = ax[1, 1]
    rem = D["rem"]
    p2 = rem[(rem.module == "P2") & (rem.code == CFG.P2_TEA) & (rem.measure == "december_stock")].sort_values("year")
    p2j = rem[(rem.module == "P2") & (rem.code == CFG.P2_TEA) & (rem.measure == "june_stock")].sort_values("year")
    d2 = d.twinx(); d2.spines["right"].set_visible(True); d2.grid(False)
    d2.bar(p2.year, p2.n_reporting_establishments, width=0.6, color="#d9d9d9", alpha=0.7, zorder=0, label=tr("rfig_estab", lang))
    d2.set_ylim(0, p2.n_reporting_establishments.max() * 3.2); plate_ylabel(d2, tr("rfig_estab_axis", lang), right=True)
    f1 = _fit_series(Fd, "p2_dec:none:2019-2025")
    d.plot(f1.year, f1.fitted_rate, "-", color=OK[3], lw=2.0, label=tr("rfig_fit_nooff", lang), zorder=3)
    d.fill_between(f1.year, f1.fitted_lo, f1.fitted_hi, color=OK[3], alpha=0.13, zorder=2)
    f2 = _fit_series(Fd, "p2_dec:estab:2019-2025")
    d.plot(f2.year, f2.fitted_count, "--", color=OK[6], lw=1.8, label=tr("rfig_fit_off", lang), zorder=3)
    d.plot(p2.year, p2.total, "o", color=OK[3], markersize=7, label=f"{tr('stock_december', lang) if False else tr('rfig_stock_axis', lang)}", zorder=4)
    d.plot(p2j.year, p2j.total, "^", color="#777777", markersize=6, label=tr("rfig_june", lang), zorder=4)
    d.plot(p2.year, p2.stable_panel_total, "d:", color=OK[2], lw=1.2, markersize=5, label=f"{tr('rfig_stable', lang)} (n={int(p2.n_stable_panel_establishments.iloc[0])})", zorder=4)
    _context(d, lang, pandemic="mid", law_pos="mid")
    d.set_xticks(CFG.YEARS_REM); d.set_xlabel(tr("year", lang)); d.set_ylim(0, f1.fitted_hi.max() * 1.45)
    plate_ylabel(d, tr("rfig_stock_axis", lang)); d.set_zorder(d2.get_zorder() + 1); d.patch.set_visible(False)
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels()
    plate_legend(d, h1 + h2, l1 + l2, loc="upper left")
    panel_head(d, "d", tr("rfig_title_d", lang))
    # e — P6 estricto APS y especialidad, diciembre 2021–2025
    e = ax[2, 0]
    for key, code, col, lab in [("primary", CFG.STRICT["p6_primary"], OK[4], tr("rfig_primary", lang)), ("specialty", CFG.STRICT["p6_specialty"], OK[5], tr("rfig_specialty", lang))]:
        s = rem[(rem.module == "P6") & (rem.variant == STRICT_REM) & (rem.code == code) & (rem.measure == "december_stock")].sort_values("year")
        f = _fit_series(Fd, f"p6_{key}:strict_autism:none:2021-2025")
        e.plot(f.year, f.fitted_rate, "-", color=col, lw=2.0, zorder=2)
        e.fill_between(f.year, f.fitted_lo, f.fitted_hi, color=col, alpha=0.13)
        e.plot(s.year, s.total, "o", color=col, markersize=7, zorder=4, label=lab)
        # Los dos «n=» de 2021 (APS y especialidad) se escribían a 8 % del valor, uno encima del otro y con
        # el de la izquierda medio fuera del eje. `plate_value_label` mide y aparta.
        for r in s.itertuples():
            C.plate_value_label(e, float(r.year), float(r.total), f"n={int(r.n_reporting_establishments)}",
                                fontsize=FS_MIN, color=col,
                                prefer=((0, 1), (0, -1), (1, 0), (-1, 0)) if key == "primary" else ((0, -1), (0, 1), (1, 0), (-1, 0)))
    e.text(0.99, 0.02, C.plate_wrap(tr("rfig_broad_note", lang), 150.0, FS_MIN, "normal"), transform=e.transAxes, ha="right", va="bottom",
           fontsize=FS_MIN, color="#555555", bbox=NOTE_BBOX, linespacing=1.25, zorder=6)
    C.shade_years(e, [2021])
    x = LAW_YEAR - 0.35
    e.axvline(x, color="#444444", ls=":", lw=1.2); e.text(x + 0.05, 0.55, tr("fig_law", lang), transform=e.get_xaxis_transform(), fontsize=FS_MIN, va="center", color="#444444")
    fe_ = _fit_series(Fd, "p6_primary:strict_autism:none:2021-2025")
    e.set_xticks(yrs5); e.set_xlabel(tr("year", lang)); e.set_ylim(0, fe_.fitted_hi.max() * 1.4); plate_ylabel(e, tr("rfig_stock_axis", lang))
    plate_legend(e); panel_head(e, "e", tr("rfig_title_e", lang))
    # f — PIE armonizado observado y ajustado; estricto y Asperger hasta 2023
    f_ = ax[2, 1]
    edu = D["edu"].sort_values("year")
    fp = _fit_series(Fd, "pie_harmonised:none:2019-2025")
    f_.plot(fp.year, fp.fitted_rate, "-", color=OK[5], lw=2.0, zorder=2)
    f_.fill_between(fp.year, fp.fitted_lo, fp.fitted_hi, color=OK[5], alpha=0.13)
    f_.plot(edu.year, edu.pie_harmonised_n, "o", color=OK[5], markersize=7, label=tr("out_pie_harmonised", lang), zorder=4)
    f_.plot(edu.year, edu.pie_tea_strict_n, "s--", color=OK[0], lw=1.5, markersize=5, label=tr("out_pie_strict", lang))
    f_.plot(edu.year, edu.pie_tea_asperger_n, "^--", color=OK[1], lw=1.5, markersize=5, label=tr("out_pie_asperger", lang))
    # El cambio de fuente se marca con la línea y se EXPLICA EN LA LEYENDA. Escrito girado junto a la línea,
    # el rótulo de dos líneas cruzaba la banda de confianza y la serie PIE armonizada entre 2023 y 2024:
    # tapaba justo el tramo del que habla. La leyenda tiene sitio y se coloca midiendo.
    from matplotlib.lines import Line2D
    f_.axvline(2023.5, color="#999999", ls="-.", lw=1.0)
    _context(f_, lang, pandemic="mid", law_pos="mid", law_ha="right")
    f_.set_xticks(CFG.YEARS_REM); f_.set_xlabel(tr("year", lang)); f_.set_ylim(0, fp.fitted_hi.max() * 1.4)
    plate_ylabel(f_, tr("rfig_students_axis", lang))
    h_f, l_f = f_.get_legend_handles_labels()
    h_f.append(Line2D([], [], color="#999999", ls="-.", lw=1.0)); l_f.append(tr("rfig_source_change_leg", lang))
    lg_f = plate_legend(f_, h_f, l_f)
    C.plate_place_legend(f_, lg_f, outside_below=False, prefer=("upper left", "upper center"))
    panel_head(f_, "f", tr("rfig_title_f", lang))
    path = save_plate(fig, fdir / "figS7_rem_education_models.png", lang=lang)
    plt.close(fig)
    fig_word = tr("figure", lang)
    cap = {"title": {"es": f"{fig_word} S7. REM A05 por edad y sexo, stocks P2/P6 y PIE: tasas estandarizadas y ajustes log-lineales, 2019–2025 — variante {vlab}",
                     "en": f"{fig_word} S7. REM A05 by age and sex, P2/P6 stocks and PIE: standardised rates and log-linear fits, 2019–2025 — {vlab} variant"}[lang],
           "caption": {"es": "(a) Ingresos REM A05 por autismo estricto (código 05990022, 2021–2025) por 100.000 habitantes INE (base 2017, residencia; numerador por lugar de atención en la red pública): tasas brutas (IC exacto de Poisson) y estandarizadas por edad OMS (IC de Fay–Feuer) por sexo; n = establecimientos reportantes por año. (b) Ídem para la familia TGD de la variante (05990022–05990026; sin 05990024 en la variante sin Rett). (c) Tasas específicas por edad y sexo de ingresos por autismo estricto en 2021 y 2025 (IC exacto de Poisson; grupos 0–39 años). (d) P2: población NANEAS con TEA bajo control en diciembre 2019–2025 (puntos), ajuste log-lineal cuasi-Poisson sin offset (banda 95 %) y ajuste con offset log(establecimientos reportantes) (línea discontinua: conteo ajustado), stock de junio como marcador de sensibilidad (nunca sumado con diciembre), panel estable de 193 establecimientos y establecimientos reportantes de diciembre (barras, eje derecho). (e) P6: población bajo control por autismo estricto en diciembre 2021–2025 en APS (P6241010) y especialidad (P6241060) con ajuste log-lineal y establecimientos reportantes; el TGD amplio 2019–2020 es otra definición y se excluye. (f) PIE: estudiantes con TEA + TEA-Asperger (armonizado; Apuntes 60 2019–2023, SINACES 2024–2025) con ajuste log-lineal 2019–2025, y series TEA estricto y TEA-Asperger 2019–2023. Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto. Stocks y flujos nunca se combinan en un mismo eje; los conteos son reconocimiento administrativo, no prevalencia.",
                       "en": "(a) REM A05 entries for strict autism (code 05990022, 2021–2025) per 100,000 INE population (base 2017, residence; place-of-care numerator in the public network): crude (exact Poisson CI) and WHO age-standardised rates (Fay–Feuer CI) by sex; n = reporting establishments per year. (b) Same for the variant's PDD family (05990022–05990026; without 05990024 in the without-Rett variant). (c) Age- and sex-specific rates of strict-autism entries in 2021 and 2025 (exact Poisson CI; ages 0–39). (d) P2: NANEAS population with ASD under control in December 2019–2025 (points), quasi-Poisson log-linear fit without offset (95% band) and fit with log(reporting establishments) offset (dashed: fitted count), June stock as sensitivity marker (never summed with December), stable panel of 193 establishments and December reporting establishments (bars, right axis). (e) P6: population under control for strict autism in December 2021–2025 in primary care (P6241010) and specialty (P6241060) with log-linear fit and reporting establishments; broad PDD 2019–2020 is a different definition and is excluded. (f) PIE: students with ASD + ASD-Asperger (harmonised; Apuntes 60 2019–2023, SINACES 2024–2025) with log-linear fit 2019–2025, and strict ASD and ASD-Asperger series 2019–2023. Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context. Stocks and flows are never combined on one axis; counts are administrative recognition, not prevalence."}[lang]}
    merge_json(fdir / "captions.json", {"figS7_rem_education_models": cap})
    return {"figS7_rem_education_models": str(path)}


# ---------------------------------------------------------------------------
def main() -> int:
    t_start = time.perf_counter()
    ctl = Controls()
    D = load_data(ctl)
    S = Store()
    timings = {}
    for name, fn in [("grd_models", lambda: grd_models(D, S, ctl)), ("hospital_models", lambda: hospital_models(D, S, ctl))]:
        t0 = time.perf_counter(); fn(); timings[name] = round(time.perf_counter() - t0, 1)
    t0 = time.perf_counter(); pop = population_rates(D, S, ctl); timings["population_rates"] = round(time.perf_counter() - t0, 1)
    t0 = time.perf_counter(); a05 = a05_models(D, S, ctl); timings["a05_models"] = round(time.perf_counter() - t0, 1)
    t0 = time.perf_counter(); stock_models(D, S); education_models(D, S); deis_models(D, S); timings["stock_education_deis"] = round(time.perf_counter() - t0, 1)
    conv = convergence_index(D)

    summary = pd.DataFrame(S.summary)
    front = ["model_id", "estimand", "source", "variant", "outcome", "denominator_offset", "panel", "activity", "position", "covariates", "sex", "years", "n_obs", "df_resid",
             "apc", "apc_lo", "apc_hi", "p_value", "beta", "se", "dispersion", "durbin_watson", "dw_check", "model_family", "converged", "note_keys", "note"]
    for col in front:
        if col not in summary:
            summary[col] = np.nan
    summary = summary[front + [c for c in summary.columns if c not in front]]
    summary["script"] = SCRIPT
    summary["label_note"] = "estimand/source/outcome/denominator_offset/panel/activity/position/covariates/model_family are label keys (bilingual text in 06_models.py LBL); apc = 100*(exp(beta)-1) with Wald 95% CI; dispersion = Pearson chi2/df (random intercept: conditional Pearson chi2/(n - p_fixed - 1) at the MAP estimates, diagnostic only); durbin_watson on deviance residuals (weak with < 8 points; random intercept: conditional deviance residuals within hospital)"
    fitted = pd.DataFrame(S.fitted)
    fitted["script"] = SCRIPT
    C.atomic_write_csv(summary, CFG.TIDY / "models_summary.csv")
    C.atomic_write_csv(fitted, CFG.TIDY / "models_fitted.csv")
    hosp = S.hosp.copy(); hosp["script"] = SCRIPT
    C.atomic_write_csv(hosp, CFG.TIDY / "hospital_effects.csv")
    pop["script"] = SCRIPT; a05["script"] = SCRIPT; conv["script"] = SCRIPT
    C.atomic_write_csv(pop, CFG.TIDY / "models_population_rates.csv")
    C.atomic_write_csv(a05, CFG.TIDY / "models_a05_standardised_rates.csv")
    C.atomic_write_csv(conv, CFG.TIDY / "models_convergence_index.csv")
    log(f"models_summary.csv: {len(summary)} modelos; models_fitted.csv: {len(fitted)} filas; hospital_effects.csv: {len(hosp)} filas")

    # Controles de los propios modelos
    ctl.add("all_models_converged", "GLM", 0, int((~summary[summary.model_family != "fam_ri_vb"].converged.astype(bool)).sum()), "number of non-converged fits (0 expected)")
    ctl.add("every_model_has_ci", "apc_lo/apc_hi", 0, int(summary[summary.apc.notna()][["apc_lo", "apc_hi"]].isna().any(axis=1).sum()), "models with APC but missing CI")
    prim = summary.set_index("model_id")
    ctl.add("primary_apc_positive", "grd any observed all 2019-2024", "positive", "positive" if prim.loc["grd_rate:con_rett:observed:all:any:none:2019-2024", "apc_lo"] > 0 else "not positive",
            "lower CI limit above 0")
    ri_rows = summary[summary.covariates.str.startswith("cov_hospital_ri")]
    ctl.add("random_intercept_fits_converged", "n converged / n attempted", int(len(ri_rows)), int(ri_rows.converged.astype(bool).sum()), "PoissonBayesMixedGLM with offset (MAP; VB fallback)")
    ctl.add("no_causal_law_model", "interrupted time series", 0, int(summary.model_id.str.contains("law|its|intervention", case=False).sum()), "no model encodes the law as intervention")
    for variant in VARIANTS:
        cv = conv[(conv.variant == variant) & (conv.index_base_year == 2021) & (conv.year == 2021)]
        ctl.add("convergence_index_base_is_100", variant, 100.0, float(cv["index"].round(9).unique().max()) if len(cv) else np.nan, "all series = 100 in 2021", tol_abs=1e-6)

    # Tablas y láminas por variante e idioma
    outputs = {}
    t0 = time.perf_counter()
    for variant in VARIANTS:
        for lang in LANGS:
            titles = write_tables(S, pop, a05, conv, summary, variant, lang, ctl)
            figs = {}
            figs.update(figure_models(S, summary, fitted, pop, conv, variant, lang))
            figs.update(figure_rem_education(S, D, summary, fitted, a05, variant, lang))
            outputs[f"{variant}/{lang}"] = dict(tables=sorted(titles), figures=figs)
            log(f"{variant}/{lang}: {len(titles)} tablas, {len(figs)} láminas")
    timings["tables_figures"] = round(time.perf_counter() - t0, 1)

    controls = ctl.frame()
    C.atomic_write_csv(controls, CFG.OUT / "controls" / f"{MODULE}_controls.csv")
    n_diff = int((controls.status != "ok").sum())
    log(f"controles: {len(controls)} ({n_diff} difieren)")
    if n_diff:
        print(controls[controls.status != "ok"].to_string(index=False))
    total = time.perf_counter() - t_start
    C.atomic_write_json(dict(module=MODULE, script=SCRIPT, run_utc=datetime.now(timezone.utc).isoformat(), total_seconds=round(total, 1), timings=timings,
                             n_models=int(len(summary)), n_fitted_rows=int(len(fitted)), n_hospital_rows=int(len(hosp)), random_intercept=S.ri_status,
                             random_intercept_seconds=S.ri_seconds, outputs=outputs, controls=dict(n=int(len(controls)), differ=n_diff)), CFG.OUT / "controls" / f"{MODULE}_run_log.json")
    log(f"runtime total: {total:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
