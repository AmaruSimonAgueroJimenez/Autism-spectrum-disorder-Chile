#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""14_extra_figures_rem.py — Láminas y tablas suplementarias adicionales de la ruta administrativa REM (serie E11–E19).

Continúa la serie E del material suplementario (E1–E10 provienen de los módulos de detalle GRD) con nueve láminas
multipanel de 600 ppp y su tabla de respaldo, por variante de definición (con_rett, sin_rett) e idioma (es, en):

  E11 A03 en detalle: cada código de cada era con su total anual y sus establecimientos reportantes, el atípico de
      febrero de 2019 marcado y la razón alterado/realizado dentro de la era legado (nunca «positividad poblacional»).
  E12 A03 2023–2025: estructura de riesgo y derivación (composición bajo/medio/alto, derivación de riesgo alto,
      resultados de la segunda parte, códigos 31–59 meses de 2024 y rediseño de 2025), cada era en su faceta.
  E13 A05 regional: ingresos por 100.000 residentes por región y año, establecimientos, estabilidad del rango
      regional y participación del panel estable.
  E14 A05 edad y sexo: 17 grupos OMS por sexo y año, tasas estandarizadas por sexo, razón hombre:mujer por edad y
      desplazamiento de la composición etaria 2021→2025.
  E15 P2 y P6 en detalle: stock de diciembre por región por 100.000 residentes, junio frente a diciembre, stock por
      establecimiento reportante, P2 sobre el total NANEAS desde 2023 y P6 APS frente a especialidad por era.
  E16 A27 y A28: consejería y referencia asistida por región y año, ingresos a rehabilitación por región y sus
      establecimientos.
  E17 Distribuciones por establecimiento: curva de Lorenz y participación del decil superior (A05, P2, P6) y número
      de establecimientos que cruzan umbrales.
  E18 Series mensuales: A05 ingresos, A03 tamizajes y A28 rehabilitación por mes, la disrupción de 2020 y el índice
      estacional.
  E19 Sensibilidad por era de definición: para cada indicador REM, los totales bajo el código estricto de autismo, la
      familia de la variante y la categoría amplia pre-2021, uno al lado del otro y nunca como serie continua.

Entradas (outputs/tidy/): rem_pathway_tidy.csv, rem_pathway_annual.csv, rem_establishment_year.csv,
rem_a05_age_sex_annual.csv, comuna_crosswalk.csv, ine_population_region_national_year_age_sex.csv y
(solo para un control) models_a05_standardised_rates.csv.

Salidas: outputs/<variante>/<idioma>/extra/figures/<nombre>.png (+ captions.json fusionado) y
outputs/<variante>/<idioma>/extra/tables/<nombre>.csv, <nombre>_numeric.csv (+ titles.json fusionado).
Controles: outputs/controls/14_extra_figures_rem_controls.csv y 14_extra_figures_rem_run_log.json.

Reglas respetadas: los recuentos son reconocimiento administrativo y actividad registrada, nunca prevalencia ni
incidencia; las fuentes no se enlazan por persona (no hay cascada ni razones entre fuentes no enlazables); stocks
(P2/P6) y flujos (A03/A05/A27/A28) nunca comparten eje; cada era de definición va en su faceta y ninguna línea cruza
un quiebre; toda tabla y lámina REM muestra los establecimientos reportantes; el REM localiza al prestador, no la
residencia, y toda tasa con población INE lleva la advertencia ecológica; cero, vacío y «no reportado» se mantienen
distintos; en las tablas territoriales las celdas con menos de 5 eventos se suprimen («<5»).

Ejecución (desde la raíz del repositorio):  python3 lancet_americas/pipeline/14_extra_figures_rem.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
from common import AGE_GROUPS, direct_standardization, poisson_limits  # noqa: E402
from epi_helpers import count_ratio  # noqa: E402  (common ya insertó scripts/ en sys.path)

MODULE = "14_extra_figures_rem"
SCRIPT = "lancet_americas/pipeline/14_extra_figures_rem.py"
VARIANTS = list(CFG.VARIANTS)
LANGS = CFG.LANGUAGES
CONTROLS_DIR = CFG.OUT / "controls"   # config.CONTROLS es el diccionario de valores esperados; la carpeta es outputs/controls
CONTROLS_DIR.mkdir(parents=True, exist_ok=True)

OK = C.OKABE
DARK, GREY, LIGHT = "#333333", "#8c8c8c", "#d9d9d9"
PER = 100_000.0
LAW_YEAR = CFG.LAW_YEAR
DISRUPTION = tuple(CFG.PANDEMIC_YEARS)
SUPPRESS = 5           # celdas territoriales con menos de 5 eventos
YEARCOL = {2019: "#9e9e9e", 2020: "#000000", 2021: OK[5], 2022: OK[0], 2023: OK[2], 2024: OK[4], 2025: OK[1]}
T0 = time.time()

PLATES = {
    "E11": "E11_rem_a03_codes_by_era",
    "E12": "E12_rem_a03_risk_referral",
    "E13": "E13_rem_a05_regional",
    "E14": "E14_rem_a05_age_sex",
    "E15": "E15_rem_p2_p6_detail",
    "E16": "E16_rem_a27_a28_regional",
    "E17": "E17_rem_establishment_distribution",
    "E18": "E18_rem_monthly_series",
    "E19": "E19_rem_definition_era_sensitivity",
}


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Rótulos bilingües (ninguna cadena visible se escribe suelta en el código)
# ---------------------------------------------------------------------------
LBL = {
    "figure": {"es": "Figura", "en": "Figure"},
    "year": {"es": "Año", "en": "Year"},
    "month": {"es": "Mes", "en": "Month"},
    "region": {"es": "Región", "en": "Region"},
    "code": {"es": "Código", "en": "Code"},
    "era": {"es": "Era de definición", "en": "Definition era"},
    "indicator": {"es": "Indicador", "en": "Indicator"},
    "series_col": {"es": "Serie", "en": "Series"},
    "panel": {"es": "Panel", "en": "Panel"},
    "value": {"es": "Valor", "en": "Value"},
    "total_year": {"es": "Total del año", "en": "Year total"},
    "national": {"es": "Chile (total nacional)", "en": "Chile (national total)"},
    "months_abbr": {"es": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
                    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]},
    "var_con_rett": {"es": "F84 completo (con Rett)", "en": "Full F84 (with Rett)"},
    "var_sin_rett": {"es": "F84 sin Rett", "en": "F84 without Rett"},
    "n_estab": {"es": "n = establecimientos reportantes", "en": "n = reporting establishments"},
    "estab_axis": {"es": "Establecimientos reportantes (n)", "en": "Reporting establishments (n)"},
    "estab_short": {"es": "Establec. reportantes", "en": "Reporting establishments"},
    "pandemic": {"es": "Disrupción del\nreporte 2020–21", "en": "Reporting\ndisruption 2020–21"},
    "pandemic_one": {"es": "Disrupción\ndel reporte {y}", "en": "Reporting\ndisruption {y}"},
    "law": {"es": "Ley 21.545\n(contexto)", "en": "Law 21.545\n(context)"},
    "def_break": {"es": "quiebre de\ndefinición", "en": "definition\nbreak"},
    "not_reported": {"es": "no reportado", "en": "not reported"},
    "outside_era": {"es": "fuera de la era", "en": "outside the era"},
    "suppressed": {"es": "<5", "en": "<5"},
    "na": {"es": "n/e", "en": "n/e"},
    "legend_state": {"es": "gris = no reportado; «<5» = celda suprimida", "en": "grey = not reported; '<5' = suppressed cell"},
    # unidades y ejes
    "u_screen": {"es": "Registros de tamizaje (flujo anual)", "en": "Screening records (annual flow)"},
    "u_children": {"es": "Niños/as o registros (flujo anual)", "en": "Children or records (annual flow)"},
    "u_entries": {"es": "Ingresos (flujo anual)", "en": "Entries (annual flow)"},
    "u_exits": {"es": "Altas clínicas (flujo anual)", "en": "Clinical discharges (annual flow)"},
    "u_interventions": {"es": "Intervenciones (flujo anual; no personas)", "en": "Interventions (annual flow; not persons)"},
    "u_rehab": {"es": "Ingresos a rehabilitación (flujo anual)", "en": "Rehabilitation entries (annual flow)"},
    # Rótulo de la BARRA DE COLOR: una barra de 2 mm de ancho junto al borde de la celda solo admite un
    # rótulo de una línea. Con la glosa entera («…; no personas») el rótulo se plegaba en dos líneas y la
    # segunda se imprimía sobre sus propias marcas —el defecto de S31 (b) y (d)—. La unidad completa, con su
    # advertencia, pasa al rótulo del eje X del mismo panel, donde hay sitio y se lee antes.
    "cb_interventions": {"es": "Intervenciones", "en": "Interventions"},
    "cb_rehab": {"es": "Ingresos", "en": "Entries"},
    "cb_rate_entries": {"es": "Por 100.000 hab.", "en": "Per 100,000 residents"},
    "cb_rate_stock": {"es": "Por 100.000 hab.", "en": "Per 100,000 residents"},
    "cb_estab": {"es": "Establecimientos (n)", "en": "Establishments (n)"},
    "estab_regions": {"es": "sobre cada barra: establecimientos reportantes (regiones con fila del código)",
                      "en": "above each bar: reporting establishments (regions with a row for the code)"},
    "dec_bars_jun_marks": {"es": "barras = diciembre; marcadores huecos = junio (los dos semestres nunca se suman)",
                           "en": "bars = December; hollow markers = June (the two semesters are never summed)"},
    "n_rows": {"es": "bajo el eje, n = establecimientos reportantes, una fila por serie en su color",
               "en": "below the axis, n = reporting establishments, one row per series in its colour"},
    "u_stock_dec": {"es": "Personas bajo control en diciembre (stock)", "en": "People under control in December (stock)"},
    "u_rate_pop": {"es": "por 100.000 residentes (INE base 2017)", "en": "per 100,000 residents (INE base 2017)"},
    "u_rate_entries": {"es": "Ingresos por 100.000 residentes", "en": "Entries per 100,000 residents"},
    "u_rate_stock": {"es": "Bajo control por 100.000 residentes", "en": "Under control per 100,000 residents"},
    "u_share": {"es": "% del total del año", "en": "% of the year total"},
    "u_index": {"es": "Índice mensual (media anual = 100)", "en": "Monthly index (annual mean = 100)"},
    "u_per_estab": {"es": "Registros por establecimiento reportante", "en": "Records per reporting establishment"},
    "u_estab": {"es": "Establecimientos con fila de diciembre para el código", "en": "Establishments with a December row for the code"},
    "monthly_total": {"es": "Total del mes", "en": "Month total"},
    "log_scale": {"es": "(escala log.)", "en": "(log scale)"},
    "ratio_axis": {"es": "Razón (IC 95 %)", "en": "Ratio (95% CI)"},
    "ci95": {"es": "IC 95 %", "en": "95% CI"},
    "sex_m": {"es": "Hombres", "en": "Males"},
    "sex_f": {"es": "Mujeres", "en": "Females"},
    "both_sex": {"es": "Ambos sexos", "en": "Both sexes"},
    "age_axis": {"es": "Grupo de edad (años)", "en": "Age group (years)"},
    # E11
    "e11_a": {"es": "A03 era legado 2019–2024: control de 18 meses y alteración detectada", "en": "A03 legacy era 2019–2024: 18-month control and detected alteration"},
    "e11_b": {"es": "A03 era legado 2019–2022: M-CHAT realizado y alterado", "en": "A03 legacy era 2019–2022: M-CHAT performed and altered"},
    "e11_c": {"es": "Era legado por mes, 2019: el atípico de febrero", "en": "Legacy era by month, 2019: the February outlier"},
    "e11_d": {"es": "Razón alterado/realizado dentro de la era legado", "en": "Altered-to-performed ratio within the legacy era"},
    "e11_e": {"es": "A03 era 2023–2024 (M-CHAT-R/F): todos los códigos", "en": "A03 2023–2024 era (M-CHAT-R/F): every code"},
    "e11_f": {"es": "A03 eras 2024 y 2025: códigos de 31–59 meses y del rediseño",
              "en": "A03 2024 and 2025 eras: 31–59-month codes and the redesign"},
    "e11_f1": {"es": "era 2024: 31–59 meses", "en": "2024 era: 31–59 months"},
    "e11_f2": {"es": "era 2025: rediseño", "en": "2025 era: redesign"},
    "feb_outlier": {"es": "feb. 2019: 1.051 realizados y 1.028 alterados en un solo mes\n(valor atípico del archivo; se informa, no se corrige)",
                    "en": "Feb 2019: 1,051 performed and 1,028 altered in a single month\n(outlying file value; reported, never corrected)"},
    "ratio_all": {"es": "Todos los meses", "en": "All months"},
    "ratio_nofeb": {"es": "Sin febrero de 2019", "en": "Excluding February 2019"},
    "ratio_axis_alt": {"es": "Alterados / realizados (%, IC 95 % de Wilson)", "en": "Altered / performed (%, Wilson 95% CI)"},
    "not_positivity": {"es": "no es positividad poblacional del M-CHAT: el denominador son niños/as\ncon alteración de lenguaje o área social ya detectada",
                       "en": "not population M-CHAT positivity: the denominator is children with an\nalready detected language or social-area alteration"},
    # E12
    "e12_a": {"es": "Composición del resultado de 1.ª parte, 2023–2024", "en": "Composition of the part-1 result, 2023–2024"},
    "e12_b": {"es": "Derivación del riesgo alto, 2023–2024", "en": "Referral of high risk, 2023–2024"},
    "e12_c": {"es": "Resultados de la 2.ª parte, 2023–2024", "en": "Part-2 outcomes, 2023–2024"},
    "e12_d": {"es": "Códigos de 31–59 meses, era 2024", "en": "31–59-month codes, 2024 era"},
    "e12_e": {"es": "Rediseño de 2025: motivos y resultados", "en": "2025 redesign: motives and results"},
    "e12_f": {"es": "Composición del riesgo por era (nunca una serie continua)", "en": "Risk composition by era (never a continuous series)"},
    "risk_low": {"es": "Riesgo bajo", "en": "Low risk"},
    "risk_medium": {"es": "Riesgo medio", "en": "Medium risk"},
    "risk_high": {"es": "Riesgo alto", "en": "High risk"},
    "high_referred": {"es": "Riesgo alto con derivación a especialista", "en": "High risk with specialist referral"},
    "share_referred": {"es": "% del riesgo alto con derivación (IC 95 % de Wilson)", "en": "% of high risk with referral (Wilson 95% CI)"},
    "second_part": {"es": "2.ª parte", "en": "Part 2"},
    "era_2023_24": {"es": "Era 2023–2024", "en": "2023–2024 era"},
    "era_2024_31_59": {"es": "Era 2024 (31–59 meses)", "en": "2024 era (31–59 months)"},
    "era_2025": {"es": "Era 2025", "en": "2025 era"},
    "motives": {"es": "Motivos del tamizaje (16–30 meses)", "en": "Screening motives (16–30 months)"},
    "results_2025": {"es": "Resultados y derivación", "en": "Results and referral"},
    # E13
    "e13_a": {"es": "A05 ingresos por autismo estricto por 100.000 residentes", "en": "A05 strict-autism entries per 100,000 residents"},
    "e13_b": {"es": "Establecimientos que reportan A05 autismo estricto", "en": "Establishments reporting A05 strict autism"},
    "e13_c": {"es": "Estabilidad del rango regional", "en": "Regional rank stability"},
    "e13_d": {"es": "Participación del panel estable en los ingresos", "en": "Share of entries from the stable panel"},
    "e13_e": {"es": "Tasa regional de la familia TGD, último año", "en": "Regional PDD-family rate, last year"},
    "e13_f": {"es": "Dispersión de las tasas regionales", "en": "Dispersion of the regional rates"},
    "rank_axis": {"es": "Rango de la tasa regional (1 = más alta)", "en": "Rank of the regional rate (1 = highest)"},
    "spearman": {"es": "ρ de Spearman frente a 2021", "en": "Spearman ρ against 2021"},
    "share_panel": {"es": "% de los ingresos aportado por el panel estable", "en": "% of entries contributed by the stable panel"},
    "stable_panel_def": {"es": "panel estable = establecimientos con fila del código en cada año de su era", "en": "stable panel = establishments with a row for the code in every year of its era"},
    "median_iqr": {"es": "Mediana regional (RIC)", "en": "Regional median (IQR)"},
    "range_minmax": {"es": "Mínimo–máximo regional", "en": "Regional minimum–maximum"},
    "ecological": {"es": "tasa ecológica: el REM localiza al prestador, no la residencia", "en": "ecological rate: REM locates the provider, not residence"},
    # E14
    "e14_a": {"es": "Ingresos por edad y año, hombres (autismo estricto)", "en": "Entries by age and year, males (strict autism)"},
    "e14_b": {"es": "Ingresos por edad y año, mujeres (autismo estricto)", "en": "Entries by age and year, females (strict autism)"},
    "e14_c": {"es": "Tasas bruta y estandarizada (OMS) por sexo", "en": "Crude and WHO-standardised rates by sex"},
    "e14_d": {"es": "Razón hombre:mujer de los ingresos por edad", "en": "Male-to-female ratio of entries by age"},
    "e14_e": {"es": "Composición etaria de los ingresos, 2021 y 2025", "en": "Age composition of entries, 2021 and 2025"},
    "e14_f": {"es": "Familia TGD de la variante frente a autismo estricto por edad", "en": "Variant PDD family versus strict autism by age"},
    "crude": {"es": "bruta", "en": "crude"},
    "asr": {"es": "estandarizada (OMS)", "en": "WHO-standardised"},
    "mf_ratio": {"es": "Razón H:M (IC 95 % exacto)", "en": "M:F ratio (exact 95% CI)"},
    "age_composition": {"es": "% de los ingresos del año", "en": "% of the year's entries"},
    "family_minus_strict": {"es": "Familia TGD − autismo estricto", "en": "PDD family − strict autism"},
    # E15
    "e15_a": {"es": "P2 TEA bajo control en diciembre por 100.000 residentes", "en": "P2 ASD under control in December per 100,000 residents"},
    "e15_b": {"es": "Junio frente a diciembre (nunca se suman)", "en": "June versus December (never summed)"},
    "e15_c": {"es": "Stock por establecimiento reportante", "en": "Stock per reporting establishment"},
    "e15_d": {"es": "P2 TEA sobre el total NANEAS bajo control (diciembre)", "en": "P2 ASD as a share of total NANEAS under control (December)"},
    "e15_e": {"es": "P6 APS y especialidad por era de definición", "en": "P6 primary care and specialty by definition era"},
    "e15_e_hatch": {"es": "Rayado = TGD amplio 2019–2020", "en": "Hatched = broad PDD 2019–2020"},
    "e15_e1": {"es": "P6 2019–2020: TGD amplio", "en": "P6 2019–2020: broad PDD"},
    "e15_e2": {"es": "P6 2021–2025: autismo estricto y familia", "en": "P6 2021–2025: strict autism and family"},
    "e15_f": {"es": "P6 APS y especialidad por región, último año", "en": "P6 primary care and specialty by region, last year"},
    "p2_short": {"es": "P2 TEA", "en": "P2 ASD"},
    "p6p_short": {"es": "P6 APS", "en": "P6 primary care"},
    "p6s_short": {"es": "P6 especialidad", "en": "P6 specialty"},
    "june": {"es": "Junio", "en": "June"},
    "december": {"es": "Diciembre", "en": "December"},
    "per100_naneas": {"es": "TEA por 100 NANEAS bajo control (IC 95 % de Wilson)", "en": "ASD per 100 NANEAS under control (Wilson 95% CI)"},
    "primary": {"es": "APS", "en": "Primary care"},
    "specialty": {"es": "Especialidad", "en": "Specialty"},
    "strict_short": {"es": "Autismo estricto", "en": "Strict autism"},
    "family_short": {"es": "Familia TGD (variante)", "en": "PDD family (variant)"},
    "broad_short": {"es": "TGD amplio (pre-2021)", "en": "Broad PDD (pre-2021)"},
    # E16
    "e16_a": {"es": "A27 consejería (M-CHAT-R/F) por región", "en": "A27 counselling (M-CHAT-R/F) by region"},
    "e16_b": {"es": "A27 referencia asistida por región", "en": "A27 assisted referral by region"},
    "e16_c": {"es": "A28 rehabilitación en APS por región", "en": "A28 primary-level rehabilitation by region"},
    "e16_d": {"es": "A28 rehabilitación hospitalaria por región", "en": "A28 hospital-level rehabilitation by region"},
    "e16_e": {"es": "Establecimientos reportantes y regiones con reporte", "en": "Reporting establishments and regions with a report"},
    "e16_f": {"es": "Totales nacionales por 100.000 residentes", "en": "National totals per 100,000 residents"},
    "counselling": {"es": "Consejería (29101566)", "en": "Counselling (29101566)"},
    "assisted_referral": {"es": "Referencia asistida (29101574)", "en": "Assisted referral (29101574)"},
    "rehab_primary": {"es": "Rehabilitación APS (29101629)", "en": "Primary rehabilitation (29101629)"},
    "rehab_hospital": {"es": "Rehabilitación hospitalaria (29101651)", "en": "Hospital rehabilitation (29101651)"},
    # Versiones breves para las leyendas de la celda vertical: el código REM completo queda en el pie y en la tabla.
    "rehab_primary_short": {"es": "Rehabilitación APS", "en": "Primary rehabilitation"},
    "rehab_hospital_short": {"es": "Rehabilitación hospitalaria", "en": "Hospital rehabilitation"},
    "n_regions": {"es": "Regiones con al menos una fila", "en": "Regions with at least one row"},
    # E17
    "e17_a": {"es": "Lorenz: A05 ingresos por autismo estricto", "en": "Lorenz: A05 strict-autism entries"},
    "e17_b": {"es": "Lorenz: P2 TEA bajo control (diciembre)", "en": "Lorenz: P2 ASD under control (December)"},
    "e17_c": {"es": "Lorenz: P6 APS bajo control (diciembre)", "en": "Lorenz: P6 primary care under control (December)"},
    "e17_d": {"es": "Decil superior y Gini por indicador y año", "en": "Top decile and Gini by indicator and year"},
    "e17_e": {"es": "Establecimientos que cruzan umbrales", "en": "Establishments crossing thresholds"},
    "e17_f": {"es": "Distribución del valor por establecimiento (A05)", "en": "Distribution of the value per establishment (A05)"},
    "lorenz_x": {"es": "% acumulado de establecimientos (de menor a mayor)", "en": "Cumulative % of establishments (smallest to largest)"},
    "lorenz_y": {"es": "% acumulado del total del año", "en": "Cumulative % of the year total"},
    "equality": {"es": "igualdad perfecta", "en": "perfect equality"},
    "top_decile": {"es": "% aportado por el decil superior", "en": "% contributed by the top decile"},
    "gini": {"es": "Gini", "en": "Gini"},
    "threshold_axis": {"es": "Establecimientos con valor ≥ umbral (n)", "en": "Establishments with value ≥ threshold (n)"},
    "value_per_estab": {"es": "Valor por establecimiento", "en": "Value per establishment"},
    # E18
    "e18_a": {"es": "A05 ingresos por autismo estricto por mes", "en": "A05 strict-autism entries by month"},
    "e18_b": {"es": "A03 M-CHAT realizado por mes (era legado)", "en": "A03 M-CHAT performed by month (legacy era)"},
    "e18_c": {"es": "A28 rehabilitación en APS por mes", "en": "A28 primary-level rehabilitation by month"},
    "e18_d": {"es": "Índice estacional medio por indicador y era", "en": "Mean seasonal index by indicator and era"},
    "e18_e": {"es": "Establecimientos con fila en el mes", "en": "Establishments with a row in the month"},
    "e18_f": {"es": "Disrupción de 2020: mes de 2020 frente al mismo mes de 2019", "en": "2020 disruption: 2020 month against the same 2019 month"},
    "ratio_2020_2019": {"es": "Razón 2020 / 2019 del mismo mes", "en": "2020 / 2019 ratio of the same month"},
    "no_row_month": {"es": "mes sin fila = no reportado (nunca cero)", "en": "month with no row = not reported (never zero)"},
    # E19
    "e19_a": {"es": "A05 ingresos por era y definición", "en": "A05 entries by era and definition"},
    "e19_b": {"es": "A05 altas clínicas por era y definición", "en": "A05 clinical discharges by era and definition"},
    "e19_c": {"es": "P6 APS (diciembre) por era y definición", "en": "P6 primary care (December) by era and definition"},
    "e19_d": {"es": "P6 especialidad (diciembre) por era y definición", "en": "P6 specialty (December) by era and definition"},
    "e19_e": {"es": "Composición de la familia TGD por categoría", "en": "Composition of the PDD family by category"},
    "e19_f": {"es": "Razón familia / autismo estricto", "en": "PDD family / strict autism ratio"},
    "cat_autism": {"es": "Autismo", "en": "Autism"},
    "cat_asperger": {"es": "Asperger", "en": "Asperger"},
    "cat_rett": {"es": "Síndrome de Rett", "en": "Rett syndrome"},
    "cat_disintegrative": {"es": "Trastorno desintegrativo", "en": "Disintegrative disorder"},
    "cat_pdd_nos": {"es": "TGD no especificado", "en": "PDD unspecified"},
    "no_continuity": {"es": "eras separadas: los totales no forman una serie continua", "en": "separate eras: the totals do not form a continuous series"},
    "family_over_strict": {"es": "Familia / estricto", "en": "Family / strict"},
    # tablas
    "t_series": {"es": "Serie", "en": "Series"},
    "t_measure": {"es": "Medida", "en": "Measure"},
    "t_value_n": {"es": "valor (n establecimientos)", "en": "value (n establishments)"},
}

A03_CODE_LABEL = {
    "03500404": {"es": "Control de salud a los 18 meses", "en": "Health control at 18 months"},
    "03500405": {"es": "Alteración de lenguaje y/o área social en el control", "en": "Language and/or social-area alteration at the control"},
    "03500406": {"es": "M-CHAT realizado (en niños/as con alteración)", "en": "M-CHAT performed (children with an alteration)"},
    "03500407": {"es": "M-CHAT alterado (en niños/as con alteración)", "en": "M-CHAT altered (children with an alteration)"},
    "09600212": {"es": "Sospecha de autismo en otros controles o consultas", "en": "Autism suspicion in other controls or consultations"},
    "09600213": {"es": "M-CHAT-R/F 1.ª parte: riesgo bajo", "en": "M-CHAT-R/F part 1: low risk"},
    "09600214": {"es": "M-CHAT-R/F 1.ª parte: riesgo medio", "en": "M-CHAT-R/F part 1: medium risk"},
    "09600215": {"es": "M-CHAT-R/F 1.ª parte: riesgo alto", "en": "M-CHAT-R/F part 1: high risk"},
    "09600216": {"es": "Riesgo alto con derivación a especialista", "en": "High risk with specialist referral"},
    "09600217": {"es": "M-CHAT-R/F 2.ª parte: riesgo medio en 1.ª parte", "en": "M-CHAT-R/F part 2: medium risk in part 1"},
    "09600218": {"es": "M-CHAT-R/F 2.ª parte: sin derivación", "en": "M-CHAT-R/F part 2: no referral required"},
    "09600219": {"es": "M-CHAT-R/F 2.ª parte: con derivación", "en": "M-CHAT-R/F part 2: referral required"},
    "03700104": {"es": "31–59 meses evaluados en control integral", "en": "31–59 months evaluated at the integral control"},
    "03700105": {"es": "31–59 meses con sospecha en otra instancia", "en": "31–59 months suspected elsewhere"},
    "03700106": {"es": "Guía de señales de alerta: sí", "en": "Alert-sign guide: yes"},
    "03700107": {"es": "Guía de señales de alerta: no", "en": "Alert-sign guide: no"},
    "03700108": {"es": "Derivación tras señales de alerta: sí", "en": "Referral after alert signs: yes"},
    "03700109": {"es": "Derivación tras señales de alerta: no", "en": "Referral after alert signs: no"},
    "03710013": {"es": "Motivo: EEDP alterado (16–30 meses)", "en": "Motive: altered EEDP (16–30 months)"},
    "03710014": {"es": "Motivo: factor de riesgo o señal de alerta (16–30 meses)", "en": "Motive: risk factor or alert sign (16–30 months)"},
    "03710015": {"es": "Motivo: ambos (16–30 meses)", "en": "Motive: both (16–30 months)"},
    "03710016": {"es": "M-CHAT-R/F: riesgo bajo", "en": "M-CHAT-R/F: low risk"},
    "03710017": {"es": "M-CHAT-R/F riesgo medio: sin derivación", "en": "M-CHAT-R/F medium risk: no referral"},
    "03710018": {"es": "M-CHAT-R/F riesgo medio: con derivación", "en": "M-CHAT-R/F medium risk: referral"},
    "03710019": {"es": "M-CHAT-R/F riesgo alto: con derivación", "en": "M-CHAT-R/F high risk: referral"},
    "03710020": {"es": "Sospecha 30–59 meses: sin derivación", "en": "Suspected 30–59 months: no referral"},
    "03710021": {"es": "Sospecha 30–59 meses: con derivación", "en": "Suspected 30–59 months: referral"},
}
A03_SHORT = {
    "09600212": {"es": "Sospecha otras\ninstancias", "en": "Suspected\nelsewhere"},
    "09600213": {"es": "Riesgo bajo", "en": "Low risk"},
    "09600214": {"es": "Riesgo medio", "en": "Medium risk"},
    "09600215": {"es": "Riesgo alto", "en": "High risk"},
    "09600216": {"es": "Alto con\nderivación", "en": "High with\nreferral"},
    "09600217": {"es": "2.ª parte:\nmedio en 1.ª", "en": "Part 2:\nmedium in part 1"},
    "09600218": {"es": "2.ª parte:\nsin derivación", "en": "Part 2:\nno referral"},
    "09600219": {"es": "2.ª parte:\ncon derivación", "en": "Part 2:\nreferral"},
    "03700104": {"es": "Evaluados", "en": "Evaluated"},
    "03700105": {"es": "Sospecha\notra instancia", "en": "Suspected\nelsewhere"},
    "03700106": {"es": "Alerta: sí", "en": "Alert: yes"},
    "03700107": {"es": "Alerta: no", "en": "Alert: no"},
    "03700108": {"es": "Derivación: sí", "en": "Referral: yes"},
    "03700109": {"es": "Derivación: no", "en": "Referral: no"},
    "03710013": {"es": "Motivo:\nEEDP", "en": "Motive:\nEEDP"},
    "03710014": {"es": "Motivo:\nriesgo/alerta", "en": "Motive:\nrisk/alert"},
    "03710015": {"es": "Motivo:\nambos", "en": "Motive:\nboth"},
    "03710016": {"es": "Riesgo bajo", "en": "Low risk"},
    "03710017": {"es": "Medio\nsin deriv.", "en": "Medium\nno referral"},
    "03710018": {"es": "Medio\ncon deriv.", "en": "Medium\nreferral"},
    "03710019": {"es": "Alto\ncon deriv.", "en": "High\nreferral"},
    "03710020": {"es": "30–59 m\nsin deriv.", "en": "30–59 mo\nno referral"},
    "03710021": {"es": "30–59 m\ncon deriv.", "en": "30–59 mo\nreferral"},
}
E17_SHORT = {"a05_strict": {"es": "A05 autismo estricto (ingresos)", "en": "A05 strict autism (entries)"},
             "a05_family": {"es": "A05 familia TGD (ingresos)", "en": "A05 PDD family (entries)"},
             "p2": {"es": "P2 TEA (diciembre)", "en": "P2 ASD (December)"},
             "p6_primary": {"es": "P6 APS (diciembre)", "en": "P6 primary care (December)"},
             "p6_specialty": {"es": "P6 especialidad (diciembre)", "en": "P6 specialty (December)"}}
E19_SHORT = {"a05_entry": {"es": "A05 ingresos", "en": "A05 entries"},
             "a05_exit": {"es": "A05 altas clínicas", "en": "A05 clinical discharges"},
             "p6_primary": {"es": "P6 APS", "en": "P6 primary care"},
             "p6_specialty": {"es": "P6 especialidad", "en": "P6 specialty"}}
CATEGORY_KEY = {"autism": "cat_autism", "asperger": "cat_asperger", "rett": "cat_rett",
                "disintegrative": "cat_disintegrative", "pdd_nos": "cat_pdd_nos"}


def tr(key: str, lang: str):
    return LBL[key][lang]


# ---------------------------------------------------------------------------
# Notas comunes: unidad, denominador, cobertura, era, N reportante y archivo fuente
# ---------------------------------------------------------------------------
SRC_A = "REM Serie A (SerieA_2019.csv … SerieA_2025.csv, DEIS/MINSAL)"
SRC_P = "REM Serie P (SerieP_2019.csv … SerieP_2025.csv, DEIS/MINSAL)"
#: El nombre del archivo se transcribe; la glosa entre paréntesis es texto del estudio y se declara en los
#: dos idiomas (la forma inglesa ya existía en otras notas del mismo documento: «INE projections, 2017 base,
#: 30 June»). Escrita en español dentro de las tablas inglesas, era la única frase descriptiva sin traducir.
SRC_INE = {"es": "ine_population_region_national_year_age_sex.csv (proyecciones INE, base Censo 2017, 30 de junio)",
           "en": "ine_population_region_national_year_age_sex.csv (INE projections, 2017 base, 30 June)"}
SRC_TIDY = "outputs/tidy/rem_pathway_tidy.csv, rem_pathway_annual.csv, rem_establishment_year.csv"

NOTE_COMMON = {
    "es": ("Los recuentos son reconocimiento administrativo y actividad registrada, nunca prevalencia ni incidencia. "
           "Las fuentes no se enlazan por persona: no hay cascada individual ni razones entre fuentes no enlazables; "
           "A03, A05, A27 y A28 cuentan registros o intervenciones, no personas. Serie A es flujo (suma de meses) y "
           "Serie P es stock (diciembre como principal y junio como sensibilidad; los semestres nunca se suman). Cada "
           "era de definición se muestra por separado y ninguna línea cruza un quiebre. El REM localiza al prestador "
           "(lugar de atención) y no la residencia; las tasas con población INE son ecológicas. Cero, celda vacía y "
           "«no reportado» (ausencia de fila) se mantienen distintos y nunca se imputan. 2020–2021: disrupción del "
           "reporte por la pandemia; la Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con "
           "efecto estimable."),
    "en": ("Counts are administrative recognition and recorded activity, never prevalence or incidence. Sources are not "
           "person-linked: there is no individual cascade and no ratios between unlinked sources; A03, A05, A27 and A28 "
           "count records or interventions, not persons. Series A is a flow (sum of months) and Series P is a stock "
           "(December as the main measure, June as a sensitivity; semesters are never summed). Every definition era is "
           "shown separately and no line crosses a break. REM locates the provider (place of care), not residence; rates "
           "against INE population are ecological. Zero, empty cell and 'not reported' (absent row) are kept distinct and "
           "never imputed, and 'outside the era' means the code did not exist that year. 2020–2021: pandemic reporting "
           "disruption; Law 21.545 (March 2023) is policy context, not an intervention with an estimable effect."),
}
NOTE_SUPPRESSION = {
    "es": "En las tablas territoriales las celdas con menos de 5 eventos se muestran como «<5»; «no reportado» indica que la región no presentó ninguna fila del código ese año.",
    "en": "In territorial tables, cells with fewer than 5 events are shown as '<5'; 'not reported' means the region filed no row for that code that year.",
}


def note(lang: str, unit: str, denominator: str, coverage: str, era: str, reporting: str, sources: str, extra: str = "") -> str:
    head = {"es": (f"Unidad: {unit}. Denominador: {denominator}. Cobertura: {coverage}. Era de definición: {era}. "
                   f"N reportante: {reporting}. "),
            "en": (f"Unit: {unit}. Denominator: {denominator}. Coverage: {coverage}. Definition era: {era}. "
                   f"Reporting N: {reporting}. ")}[lang]
    tail = {"es": f" Fuente: {sources}.", "en": f" Source: {sources}."}[lang]
    return head + NOTE_COMMON[lang] + (" " + extra if extra else "") + tail


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------
def num(x, dec=0, lang="es"):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) or (not isinstance(x, str) and pd.isna(x)):
        return tr("na", lang)
    return C.fmt_number(float(x), dec, lang)


def pct(x, lang="es", dec=1):
    if x is None or pd.isna(x):
        return tr("na", lang)
    return C.fmt_number(float(x), dec, lang) + (" %" if lang == "es" else "%")


#: EL SEPARADOR DEL INTERVALO IMPRESO. Entre dos cotas POSITIVAS va la raya corta —«0,02–0,23» se lee sin
#: esfuerzo—; en cuanto una cota es NEGATIVA, no: «−0,21–0,00» pone el menos tipográfico (U+2212, 47 px a
#: 600 ppp) y la raya (U+2013, 29 px) a cuatro caracteres uno de otro, dos trazos de peso distinto en una
#: misma expresión, y el lector tiene que decidir cuál separa y cuál es el signo. Es el defecto que el
#: verificador de contenido leyó en la Figura S51 (a) y (b). En ese caso —y sólo en ese, para no alargar
#: los rótulos donde no hace falta— se separa con la conjunción con la que el resto del corpus separa las
#: cotas (`common.fmt_ci`: «19,9 a 21,6» / «19.9 to 21.6»). Hoy todo intervalo de este módulo es un
#: porcentaje, una tasa o una razón, y ninguna de sus cotas puede ser negativa; la regla se escribe igual,
#: porque lo que no puede depender del dato es la tipografía.
_CI_WORD = {"es": " a ", "en": " to "}


def ci(lo, hi, dec=1, lang="es"):
    """Intervalo impreso: raya corta entre dos cotas positivas, conjunción si alguna es negativa."""
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi):
        return tr("na", lang)
    sep = _CI_WORD[lang] if (float(lo) < 0 or float(hi) < 0) else "\u2013"
    return f"{num(lo, dec, lang)}{sep}{num(hi, dec, lang)}"


def val_n(value, n_est, lang="es", dec=0, suppress=False):
    """Celda «valor (n establecimientos)»; respeta la supresión y el estado «no reportado»."""
    if value is None or pd.isna(value):
        return tr("not_reported", lang)
    if suppress and 0 < float(value) < SUPPRESS:
        return f"{tr('suppressed', lang)} ({num(n_est, 0, lang)})"
    return f"{num(value, dec, lang)} ({num(n_est, 0, lang)})"


def vlabel(variant: str, lang: str) -> str:
    return CFG.VARIANTS[variant]["label"][lang]


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------
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


def fig_dir(variant: str, lang: str) -> Path:
    p = CFG.OUT / variant / lang / "extra" / "figures"
    p.mkdir(parents=True, exist_ok=True)
    return p


def tab_dir(variant: str, lang: str) -> Path:
    p = CFG.OUT / variant / lang / "extra" / "tables"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_plate(fig, name: str, variant: str, lang: str, title: str, caption: str) -> str:
    d = fig_dir(variant, lang)
    # El verificador de composición nombra la lámina por su archivo (si no, informa «figure#7f…»).
    C.plate_declare(fig, f"{name}.png")
    finish_plate(fig, lang)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.png"
    # Modo revista (LANCET_PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    # Sin recorte: el archivo mide exactamente 180 × 245 mm y se inserta a escala 1:1, una lámina por página.
    fig.savefig(path, dpi=600, facecolor="white")
    merge_json(d / "captions.json", C.strip_caption_paths({name: {"title": title, "caption": caption}}))
    import matplotlib.pyplot as plt
    plt.close(fig)
    return str(path)


def write_table(name: str, variant: str, lang: str, formatted: pd.DataFrame, numeric: pd.DataFrame, title: str, tnote: str) -> list[str]:
    d = tab_dir(variant, lang)
    paths = [str(C.atomic_write_csv(formatted, d / f"{name}.csv", encoding="utf-8-sig")),
             str(C.atomic_write_csv(numeric, d / f"{name}_numeric.csv"))]
    merge_json(d / "titles.json", {name: {"title": title, "note": tnote}})
    return paths


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
class Data:
    def __init__(self):
        t = time.time()
        self.ann = C.read_tidy("rem_pathway_annual", dtype={"code": str, "month": str})
        self.est = C.read_tidy("rem_establishment_year", dtype={"code": str, "IdEstablecimiento": str, "IdRegion": str},
                               usecols=["year", "series", "module", "code", "IdEstablecimiento", "IdRegion", "annual_total",
                                        "december_value", "june_value", "has_december_row", "has_june_row", "in_stable_panel"],
                               low_memory=False)
        self.age = C.read_tidy("rem_a05_age_sex_annual", dtype={"code": str})
        self.tidy = C.read_tidy("rem_pathway_tidy", dtype={"code": str, "IdEstablecimiento": str, "IdRegion": str},
                                usecols=["year", "series", "module", "code", "IdEstablecimiento", "IdRegion", "month",
                                         "in_era", "total_known", "state"], low_memory=False)
        self.tidy = self.tidy.loc[self.tidy.in_era].copy()
        self.tidy["cut_region"] = pd.to_numeric(self.tidy.IdRegion, errors="coerce").astype("Int64")
        self.est["cut_region"] = pd.to_numeric(self.est.IdRegion, errors="coerce").astype("Int64")
        ine = C.read_tidy("ine_population_region_national_year_age_sex")
        nat = ine[(ine.level == "national")]
        self.pop_nat = nat[(nat.sex == "TOTAL") & (nat.age_group == "TOTAL")].set_index("year").population.astype(float)
        self.pop_nat_sex_age = nat[(nat.sex != "TOTAL") & (nat.age_group != "TOTAL")][["year", "sex", "age_group", "population"]].copy()
        reg = ine[(ine.level == "region") & (ine.sex == "TOTAL") & (ine.age_group == "TOTAL")]
        self.pop_reg = reg.pivot(index="cut_region", columns="year", values="population").astype(float)
        cw = C.read_tidy("comuna_crosswalk")
        self.region_name = cw.drop_duplicates("cut_region").set_index("cut_region").region_short.to_dict()
        self.region_order = [r for r in C.REGION_ORDER if r in self.region_name]
        p = CFG.TIDY / "models_a05_standardised_rates.csv"
        self.models_asr = pd.read_csv(p) if p.is_file() else None
        log(f"datos cargados en {time.time() - t:.1f} s: anual {len(self.ann)}, establecimiento-año {len(self.est)}, "
            f"edad-sexo {len(self.age)}, tidy en era {len(self.tidy)}, INE regional {self.pop_reg.shape}")

    # --- agregados nacionales del módulo 02 -------------------------------
    def row(self, code: str, variant: str = "single_code", measure: str = "annual_sum") -> pd.DataFrame:
        r = self.ann[(self.ann.code == code) & (self.ann.variant == variant) & (self.ann.measure == measure)].sort_values("year")
        if r.empty:
            raise KeyError(f"sin filas anuales para {code} / {variant} / {measure}")
        return r.reset_index(drop=True)

    def family_code(self, variant: str, key: str) -> str:
        return "+".join(CFG.VARIANTS[variant][key])

    def family(self, variant: str, key: str, measure: str = "annual_sum") -> pd.DataFrame:
        return self.row(self.family_code(variant, key), variant, measure)

    # --- agregados propios de este módulo ---------------------------------
    def national(self, codes: list[str], month: int | None = None) -> pd.DataFrame:
        """Total nacional y establecimientos reportantes de un conjunto de códigos (establecimiento contado una vez)."""
        t = self.tidy[self.tidy.code.isin(codes)]
        if month is not None:
            t = t[t.month == month]
        g = t.groupby("year").agg(total=("total_known", lambda s: s.sum(min_count=1)),
                                  n_est=("IdEstablecimiento", "nunique"), n_rows=("total_known", "size")).reset_index()
        return g

    def by_region(self, codes: list[str], month: int | None = None) -> pd.DataFrame:
        t = self.tidy[self.tidy.code.isin(codes)]
        if month is not None:
            t = t[t.month == month]
        g = t.groupby(["year", "cut_region"]).agg(total=("total_known", lambda s: s.sum(min_count=1)),
                                                  n_est=("IdEstablecimiento", "nunique"),
                                                  n_rows=("total_known", "size")).reset_index()
        g["cut_region"] = g.cut_region.astype(int)
        return g

    def by_month(self, codes: list[str]) -> pd.DataFrame:
        """Serie mensual completa: los meses sin fila quedan como NaN («no reportado»), nunca como cero."""
        t = self.tidy[self.tidy.code.isin(codes)]
        g = t.groupby(["year", "month"]).agg(total=("total_known", lambda s: s.sum(min_count=1)),
                                             n_est=("IdEstablecimiento", "nunique")).reset_index()
        years = sorted(t.year.unique())
        grid = pd.MultiIndex.from_product([years, range(1, 13)], names=["year", "month"]).to_frame(index=False)
        g = grid.merge(g, on=["year", "month"], how="left")
        g["index"] = g.groupby("year")["total"].transform(lambda s: 100 * s / s.mean())
        return g

    def by_establishment(self, codes: list[str], measure: str = "annual_sum") -> pd.DataFrame:
        """Valor por establecimiento y año (suma de la familia dentro del establecimiento)."""
        col = {"annual_sum": "annual_total", "december_stock": "december_value", "june_stock": "june_value"}[measure]
        e = self.est[self.est.code.isin(codes)]
        g = e.groupby(["year", "IdEstablecimiento"], as_index=False).agg(
            value=(col, lambda s: s.sum(min_count=1)), cut_region=("cut_region", "first"),
            in_stable_panel=("in_stable_panel", "any"))
        return g.dropna(subset=["value"])

    def region_matrix(self, codes: list[str], years: list[int], month: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Matrices región × año de total, establecimientos y máscara de supresión (0 < valor < 5)."""
        g = self.by_region(codes, month=month)
        g = g[g.year.isin(years)]
        idx = self.region_order
        tot = g.pivot(index="cut_region", columns="year", values="total").reindex(index=idx, columns=years)
        est = g.pivot(index="cut_region", columns="year", values="n_est").reindex(index=idx, columns=years)
        sup = (tot > 0) & (tot < SUPPRESS)
        return tot, est, sup.fillna(False)


# ---------------------------------------------------------------------------
# Norma de lámina de esta fase
# ---------------------------------------------------------------------------
# Lienzo vertical de 180 × 245 mm dibujado a escala 1:1 (una lámina por página, sin reducción al insertarla),
# rejilla de tres filas por dos columnas, seis paneles como máximo, letras de panel en minúscula y 600 ppp.
# Las láminas anteriores se dibujaban a 483 mm de ancho y se reducían dentro de la página, lo que dejaba varios
# paneles al límite de la legibilidad; esta norma sustituye aquel diseño apaisado.
import textwrap  # noqa: E402

plt, _sns = C.style()
import matplotlib.ticker  # noqa: E402  (el formateador de marcas del idioma hereda de matplotlib.ticker)

PLATE_W_IN = 180.0 / 25.4          # 7.09 pulgadas
PLATE_H_IN = 245.0 / 25.4          # 9.65 pulgadas
PLATE_ROWS, PLATE_COLS = 3, 2
PLATE_LETTERS = "abcdef"
FS_TITLE = 9.0                     # título de panel (negrita)
FS_BASE = 8.0                      # tipografía base y rótulos de eje
FS_TICK = 7.0                      # marcas de eje y leyenda
FS_LEG = 7.0
FS_ANN = 6.4                       # anotaciones dentro del panel
FS_CELL = 6.0                      # cuerpo mínimo admitido (celdas de mapa de calor)
FS_LETTER = 10.0
PLATE_FS_FLOOR = 6.0               # suelo tipográfico de la norma: ninguna cadena impresa baja de aquí
CELL_MARGIN = 2.0 / 180.0          # margen izquierdo de la celda, en fracción de figura (2 mm)
TITLE_W_PT = (PLATE_W_IN * 72.0 / PLATE_COLS) - 2.0 * 72.0 / 25.4 - 31.0    # celda − margen − letra
XLABEL_W_PT = 150.0                # ancho útil de una nota bajo el panel
YLABEL_H_PT = 138.0                # alto útil del área de ejes: un rótulo más largo se parte en líneas
CBAR_LABEL_PT = 100.0              # alto útil de una barra de color: su rótulo cabe en UNA línea o se reduce
LETTER_GAP_PT = 22.0

PLATE_RC = {
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
}
plt.rcParams.update(PLATE_RC)
_MEASURE_FIG = plt.figure(figsize=(1, 1))          # lienzo auxiliar: solo se usa para medir texto


def plate_style():
    """Estilo del estudio más la norma de lámina de esta fase (C.style vuelve a fijar el estilo apaisado)."""
    p, _ = C.style()
    p.rcParams.update(PLATE_RC)
    return p


def new_plate():
    """Lienzo de la norma: 180 × 245 mm, tres filas por dos columnas, en orden de lectura (a b / c d / e f)."""
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.055, h_pad=0.045, wspace=0.045, hspace=0.055)
    return fig, fig.add_gridspec(PLATE_ROWS, PLATE_COLS)


def _text_width_pt(s: str, fontsize: float = FS_TITLE, weight: str = "bold") -> float:
    """Ancho tipográfico real de una cadena (puntos), medido con la misma fuente con que se dibujará."""
    from matplotlib.font_manager import FontProperties
    r = _MEASURE_FIG.canvas.get_renderer()
    w, _h, _d = r.get_text_width_height_descent(s, FontProperties(size=fontsize, weight=weight), False)
    return w * 72.0 / _MEASURE_FIG.dpi


def wrap_measured(text: str, max_pt: float = TITLE_W_PT, fontsize: float = FS_TITLE, weight: str = "bold") -> str:
    """Ajuste de línea por ancho medido, no por número de caracteres.

    El español es ~15 % más largo que el inglés y los nombres del registro son largos: contar caracteres deja
    títulos que se salen de la celda en un idioma y cortos en el otro. Midiendo el texto, la misma norma vale
    para los cuatro documentos."""
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


def clip_label(text: str, width: int) -> str:
    s = str(text)
    return s if len(s) <= width else s[: max(1, width - 1)].rstrip() + "…"


def tick_label(text: str, width: int = 24, lines: int = 2) -> str:
    """Etiqueta de eje categórico para una celda estrecha: hasta `lines` líneas antes de recortar."""
    parts = textwrap.wrap(str(text), width) or [str(text)]
    if len(parts) <= lines:
        return "\n".join(parts)
    keep = parts[:lines]
    keep[-1] = clip_label(keep[-1] + " " + parts[lines], width)
    return "\n".join(keep)


def age_ticks(ax, groups, fontsize: float = FS_ANN) -> None:
    """Eje X de los 17 grupos quinquenales de la OMS, escritos en VERTICAL.

    A 60° cada rótulo se apoya sobre el siguiente: los verificadores encontraron los diecisiete pegados de
    dos en dos en cinco paneles de la lámina S29. En vertical la anchura de cada rótulo es la de una letra y
    los diecisiete caben con holgura en una celda de 90 mm, sin bajar de 6 pt ni esconder ningún grupo."""
    ax.set_xticks(np.arange(len(groups)))
    ax.set_xticklabels(list(groups), fontsize=max(PLATE_FS_FLOOR, fontsize), rotation=90, ha="center", va="top")


def letter(ax, ch: str, dx: float = -30.0, dy: float = 11.0):
    """Letra de panel en minúscula y entre paréntesis; `anchor_panel_letters` la clava a su título.

    La letra va ENTRE PARÉNTESIS, «(a)», que es la convención que escriben las 58 leyendas con
    paneles y la que ya imprimían las láminas de 06/08a/08b/08c: con la letra a secas el artículo
    publicaba dos convenciones y la leyenda no casaba con su propia lámina.
    """
    t = ax.annotate(C.plate_panel_letter(ch), xy=(0.0, 1.0), xycoords="axes fraction", xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=FS_LETTER, fontweight="bold", va="top", ha="left", family="DejaVu Sans",
                    annotation_clip=False)
    # La letra es parte del título: su sitio lo fija `anchor_panel_letters` midiendo la caja del título, y
    # el motor de descongestión no puede reubicarla por su cuenta. Sin esta marca, `_pl_resolve_texts`
    # trataba la letra como una nota más y la empujaba hacia dentro del panel para esquivar una colisión:
    # así acabó la (c) de la S29 impresa sobre los datos, a cinco líneas de su título.
    t.set_gid(C.PLATE_KEEP)
    ax._panel_letter = t
    return t


def _cell_bounds(fig, spec) -> tuple[float, float]:
    """Bordes izquierdo y derecho, en fracción de figura, de la celda de la rejilla que ocupa `spec`."""
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

    La letra se colocaba en una coordenada de eje calculada UNA vez, a partir del alto que el título tenía en
    ese momento; después `C.plate_resolve` repliega el título que se sale de su celda (una línea más), baja el
    panel cuyo título ya no cabe y `make_room` vuelve a repartir el ancho. Cada uno de esos pasos movía el
    título y dejaba la letra donde estaba: los verificadores encontraron dieciséis letras separadas de su
    título entre una y cinco líneas, y la (c) de la S29 impresa dentro del área de datos.

    Anclada al ARTISTA del título —matplotlib admite un artista como sistema de coordenadas de una anotación,
    (0, 1) es la esquina superior izquierda de su caja— la letra se recoloca sola en cada dibujo: da igual que
    el título se pliegue a una, dos o tres líneas, que el panel se estreche o que se baje. El desplazamiento
    es de `gap_pt` puntos a la izquierda del título, de modo que las letras siguen formando una columna (todos
    los títulos arrancan en el mismo borde de celda) y la letra queda siempre en la línea del título.
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

    La comprobación es la que hicieron los verificadores a mano sobre la lámina impresa: la letra se lee en la
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
    ejes empiezan muy a la derecha, el título se corre con ellos y choca con el panel vecino. Anclado a la celda,
    la lámina muestra una columna de títulos estable y la letra queda a su izquierda, en la línea del título."""
    fig.canvas.draw()
    # El motor de composición se congela: si siguiera activo, el dibujo de `savefig` movería otra vez los ejes.
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

    `constrained_layout` mide cada eje con el rectángulo de TODOS sus hijos de texto: una nota larga dentro del
    panel encoge la columna entera. Marcadas como ajenas a la composición se siguen dibujando donde el panel las
    puso y ya no deforman la lámina."""
    for ax in fig.axes:
        for t in list(ax.texts):
            t.set_in_layout(False)


def wrap_axis_labels(fig) -> None:
    """Parte en varias líneas el rótulo del eje Y que sea más alto que su panel (si no, cruza la letra)."""
    for ax in fig.axes:
        lbl = ax.yaxis.label
        txt = lbl.get_text()
        if not txt or "\n" in txt:
            continue
        if _text_width_pt(txt, lbl.get_fontsize(), "normal") > YLABEL_H_PT:
            lbl.set_text(wrap_measured(txt, YLABEL_H_PT, lbl.get_fontsize(), "normal"))
            lbl.set_linespacing(1.0)


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
    """Leyenda para una celda estrecha: los rótulos largos se parten en líneas, nunca se reduce el cuerpo.

    Cuando la leyenda va en la mitad superior (o se deja a criterio de matplotlib) el eje se estira lo justo para
    que la leyenda tenga su propio espacio en blanco en vez de taparle la serie al lector."""
    if len(args) >= 2:
        handles, labels, args = args[0], args[1], args[2:]
    else:
        handles, labels, args = (*ax.get_legend_handles_labels(), ())
    labels = [textwrap.fill(str(t), width) for t in labels]
    kw.setdefault("fontsize", FS_LEG)
    if kw.get("title"):
        kw.setdefault("title_fontsize", FS_LEG)
        kw["title"] = textwrap.fill(str(kw["title"]), width + 8)
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
    leg = ax.legend(handles, labels, *args, **kw)
    if "bbox_to_anchor" not in kw:
        # Una leyenda más ancha que sus ejes hace que `constrained_layout` les reserve sitio fuera y encoja la
        # columna entera; partida en líneas cabe dentro del panel y deja de participar en la composición.
        leg.set_in_layout(False)
    return leg


def n_strip(ax, rows, lang, fs: float = FS_CELL, first_pt: float = -16.0, gap_pt: float = 8.5) -> None:
    """Escribe los establecimientos reportantes en una TIRA bajo el eje X, una fila por serie.

    Tres series por siete años son veintiún «n=» que no caben encima de unas barras separadas 5 pt: girados
    se pisaban, y el recuadro de cada uno borraba la primera cifra del vecino (el defecto de S30 (b)). Bajo
    el eje cada número queda en la vertical de su barra, en el color de su serie y sin tocar un solo dato;
    es la misma convención de la fila de «números en riesgo» de una curva de supervivencia.

    `rows` es una lista de (color, [(x, valor), …]) en el orden de la leyenda."""
    for i, (color, values) in enumerate(rows):
        for x, v in values:
            if v is None or pd.isna(v):
                continue
            t = ax.annotate(num(v, 0, lang), xy=(float(x), 0.0), xycoords=("data", "axes fraction"),
                            xytext=(0.0, first_pt - i * gap_pt), textcoords="offset points",
                            ha="center", va="top", fontsize=fs, color=color, annotation_clip=False)
            t.set_gid(C.PLATE_KEEP)          # la tira es una rejilla: ningún número se mueve de su columna
    ax.xaxis.labelpad = abs(first_pt) + gap_pt * (len(rows) - 1) + 8.0


def note_in_panel(ax, text: str, x: float = 0.02, y: float = 0.03, ha: str = "left", va: str = "bottom",
                  fontsize: float = FS_ANN, color: str = "#555555", max_pt: float = 148.0, **kw):
    """Nota metodológica dentro del panel, ajustada por ancho medido para no salirse de la celda."""
    return ax.text(x, y, wrap_measured(text, max_pt, fontsize, "normal"), transform=ax.transAxes,
                   fontsize=fontsize, color=color, ha=ha, va=va, **kw)


def long_xlabel(ax, text: str, fontsize: float = FS_ANN) -> None:
    """Rótulo del eje X con nota metodológica, ajustado por ancho medido al área de ejes de la celda."""
    ax.set_xlabel(wrap_measured(text, XLABEL_W_PT, fontsize, "normal"), fontsize=fontsize)


def _is_year_ticks(vals) -> bool:
    """Marcas de AÑO: enteros dentro del rango de un calendario. «2019» nunca lleva separador de millares."""
    return bool(vals) and all(float(v).is_integer() and 1900 <= float(v) <= 2100 for v in vals)


class _LocaleTickFormatter(matplotlib.ticker.Formatter):
    """Marca de eje lineal en la convención del idioma, con los decimales resueltos AL ESCRIBIR.

    Cuántos decimales lleva un eje lo deciden sus marcas EN CONJUNTO, y las marcas cambian después de
    instalar el formateador: `plate_fit` ensancha el panel, `legend_wrapped` estira el eje para hacerle
    sitio a la leyenda y el localizador vuelve a repartir de 0,2 en 0,2. Congelar el número de decimales
    dejaba el eje con marcas repetidas; mirarlas en cada llamada no puede desincronizarse.

    El defecto que cierra esta clase: el eje derecho del Gini de la S32 (d) y el eje de razón de la S34 (f)
    iban de 0 a 1, así que el localizador de millares —que solo miraba ejes con marcas de mil o más— no los
    tocaba y matplotlib los escribía «0.0 0.2 … 1.0» EN LA VERSIÓN ESPAÑOLA, en el mismo panel cuya leyenda
    imprimía «n=1.012». El mismo glifo significaba decimal y millar en un solo panel. Aquí pasan por `num()`
    todos los ejes numéricos, tengan la magnitud que tengan.
    """

    def __init__(self, axis, lang: str):
        super().__init__()
        self.axis, self.lang = axis, lang

    def _ticks(self) -> list[float]:
        try:
            lo, hi = sorted(self.axis.get_view_interval())
            return [float(t) for t in self.axis.get_majorticklocs() if lo - 1e-9 <= t <= hi + 1e-9]
        except (AttributeError, TypeError, ValueError):
            return []

    def __call__(self, v, pos=None) -> str:
        if v is None or not np.isfinite(v):
            return ""
        ticks = self._ticks() or [float(v)]
        if _is_year_ticks(ticks):
            return str(int(round(float(v))))
        dec = 0
        for d in range(4):
            if all(abs(t * 10 ** d - round(t * 10 ** d)) < 1e-6 for t in ticks):
                dec = d
                break
        else:
            dec = 3
        return num(v, dec, self.lang)


def localise_axes(fig, lang: str) -> None:
    """TODA marca numérica de la lámina —ejes, gemelos, encartes y barras de color— pasa por `num()`.

    Los rótulos de valor y las leyendas ya se escribían con `num()`, pero las marcas de eje las escribía
    matplotlib con la convención inglesa: en la misma lámina se leía «1.208» sobre la barra y «5000» en el
    eje, y en la S32 (d) «n=1.012» en la leyenda junto a «0.0 … 1.0» en el eje del Gini. Un solo glifo no
    puede significar decimal y millar en un mismo panel.

    Quedan fuera, a propósito: los ejes logarítmicos (10³ es la notación correcta y quién lleva rótulo lo
    decide matplotlib) y los ejes categóricos, cuyas marcas son texto fijado a mano.
    """
    import matplotlib.ticker as mticker

    # Los encartes (`inset_axes`) NO están en `fig.axes`: sin recorrer `child_axes` las dos facetas del
    # panel f de la lámina E11 seguían rotulando «20000».
    todos = list(fig.axes)
    i = 0
    while i < len(todos):
        todos.extend(a for a in getattr(todos[i], "child_axes", []) if a not in todos)
        i += 1
    for ax in todos:
        cbar = getattr(ax, "_colorbar", None)
        if cbar is not None:
            # La barra de color reaplica su propio formateador al dibujarse: hay que dárselo a ELLA.
            axis = cbar.ax.xaxis if cbar.orientation == "horizontal" else cbar.ax.yaxis
            if not isinstance(cbar.formatter, _LocaleTickFormatter):
                cbar.formatter = _LocaleTickFormatter(axis, lang)
                cbar.update_ticks()
            continue
        for axis in (ax.xaxis, ax.yaxis):
            if not axis.get_visible() or not getattr(ax, "axison", True):
                continue
            scale = ax.get_xscale() if axis is ax.xaxis else ax.get_yscale()
            if scale != "linear":
                continue
            fmt = axis.get_major_formatter()
            # Un eje ya localizado se deja como está (el formateador resuelve sus decimales al escribir), y
            # uno con rótulos fijados a mano —FixedFormatter, los ejes categóricos y los de año— no se toca.
            if isinstance(fmt, _LocaleTickFormatter) or not isinstance(fmt, mticker.ScalarFormatter):
                continue
            axis.set_major_formatter(_LocaleTickFormatter(axis, lang))


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
    miden contra la misma convención, la del idioma que se está imprimiendo.
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
            # Un eje apagado (`ax.axis("off")`, el anfitrión de las dos facetas del panel f de la E11) no
            # imprime marcas: sus rótulos por omisión «0.0 … 1.0» no llegan al papel y no se juzgan.
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


def value_label(ax, x, y, text, *, fontsize: float = FS_CELL, color: str = DARK, err=None, **kw) -> None:
    """Encola un rotulo de valor para colocarlo cuando la composicion ya este CONGELADA.

    `C.plate_value_label` mide el panel dibujado y aparta el rotulo de todos los marcadores, de la barra de
    error de su dato y de los rotulos ya colocados. Llamarlo mientras `constrained_layout` sigue vivo no
    sirve: el reparto posterior cambia el tamano del panel, los puntos se acercan y el desplazamiento
    calculado --que esta en PUNTOS-- vuelve a caer sobre el marcador. Aqui se anota la peticion y
    `finish_plate` la resuelve al final, con la geometria definitiva."""
    ax._deferred_values = getattr(ax, "_deferred_values", []) + [
        (float(x), float(y), str(text), dict(fontsize=fontsize, color=color, err=err, **kw))]


def place_value_labels(fig) -> None:
    """Coloca, ya congelada la lamina, todos los rotulos de valor encolados con `value_label`."""
    for ax in fig.axes:
        pend = getattr(ax, "_deferred_values", None)
        if not pend:
            continue
        ax._deferred_values = []
        for x, y, text, kw in pend:
            C.plate_value_label(ax, x, y, text, **kw)  # noqa: E501


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


def finish_plate(fig, lang: str = "es") -> None:
    """Cierre común de toda lámina: notas fuera de la composición, rótulos ajustados y títulos anclados."""
    detach_annotations(fig)
    localise_axes(fig, lang)
    wrap_axis_labels(fig)
    # Motor de descongestión (common.py): mide lo dibujado y resuelve colisiones, recortes y leyendas.
    # `plate_fit` actúa con la composición todavía viva (marcas de eje, rótulos de eje, leyendas);
    # `plate_resolve`, ya congelada, separa los rótulos que se pisan y devuelve dentro lo que se sale.
    # La regla de la raya se aplica ANTES del reparto: el motor mide el texto definitivo y una
    # marca que crece 1,5 pt al cambiar de trazo no se sale de su columna después de medida.
    dash_intervals(fig)
    C.plate_fit(fig)
    align_panel_titles(fig)
    place_value_labels(fig)
    C.plate_frame_notes(fig)
    # `plate_fit` estira ejes y `legend_wrapped` los amplía: los ejes que aparecieron o cambiaron de marcas
    # después del primer paso también tienen que pasar por el idioma antes de que nadie mida nada.
    localise_axes(fig, lang)
    # Antes de congelar: el rótulo escrito al final de una barra necesita su hueco a la derecha, o el
    # guardia de recorte lo devolverá dentro encima de la barra que rotula (Figura S26 (e)).
    room_for_end_labels(fig)
    localise_axes(fig, lang)
    C.plate_resolve(fig)
    # Las dos comprobaciones de esta fase, sobre la lámina YA dibujada y en el estado en que se guarda.
    # Ninguna corrige nada: si algo se separó, la lámina no se publica.
    fig.canvas.draw()
    faults = letters_off_their_titles(fig) + numbers_against_the_language(fig, lang)
    if faults:
        name = getattr(fig, "_plate_name", "?")
        raise AssertionError(f"{name}: " + "; ".join(faults))


# ---------------------------------------------------------------------------
# Ayudantes gráficos
# ---------------------------------------------------------------------------
def _context(ax, lang, shade=DISRUPTION, law=True, pandemic_pos=0.97, law_pos=0.97, pandemic_text=True, law_x_offset=0.06,
             pandemic_va="top", law_va="top"):
    """Sombrea la disrupción del reporte y marca la Ley 21.545 como contexto (nunca como intervención)."""
    xlo, xhi = ax.get_xlim()
    yrs = [y for y in shade if xlo < y < xhi]
    if yrs:
        C.shade_years(ax, yrs)
        if pandemic_text:
            txt = tr("pandemic", lang) if len(yrs) == 2 else tr("pandemic_one", lang).format(y=yrs[0])
            t = ax.text(float(np.mean(yrs)), pandemic_pos, txt, transform=ax.get_xaxis_transform(), ha="center", va=pandemic_va, fontsize=FS_TICK, color="#555555")
            t.set_gid(C.PLATE_KEEP)
    if law and xlo < LAW_YEAR - 0.35 < xhi:
        x = LAW_YEAR - 0.35
        ax.axvline(x, color="#444444", ls=":", lw=1.2, zorder=1)
        t = ax.text(x + law_x_offset, law_pos, tr("law", lang), transform=ax.get_xaxis_transform(), ha="left", va=law_va, fontsize=FS_TICK, color="#444444")
        # Un rótulo de contexto NO puede alejarse de su línea: apartado dos años para dejar sitio a la
        # leyenda, «Ley 21.545» pasaba a leerse como el rótulo del quiebre de definición. Se clava aquí y es
        # la leyenda la que se aparta (el motor cuenta los rótulos del panel al elegir su hueco).
        t.set_gid(C.PLATE_KEEP)


#: Halo de un RÓTULO DE VALOR. `plate_frame_notes` pone recuadro blanco de 1,4 pt de margen a todo texto que
#: no esté en coordenadas de dato: con rótulos «n=…» a dos o tres puntos unos de otros, ese margen imprimía el
#: recuadro del vecino ENCIMA de la primera cifra —la «n» perdida que denunciaron los verificadores en S30 (b)
#: y (d) y en S26 (a)—. Aquí cada rótulo trae su propio halo ceñido al trazo (0,05 em ≈ 0,3 pt): sigue
#: separando el texto de la línea o de la banda que cruza, y ya no puede tapar a su vecino.
VALUE_HALO = dict(boxstyle="square,pad=0.05", fc="white", ec="none", alpha=0.80)
NOTE_HALO = dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85)


def _ann(ax, x, y, text, color=DARK, fs=FS_ANN, dy=3, ha="center", va=None, rotation=0, dx=0, bbox=False):
    va = va or ("bottom" if dy >= 0 else "top")
    kw = dict(bbox=dict(NOTE_HALO if bbox else VALUE_HALO))
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va, fontsize=fs, color=color,
                rotation=rotation, zorder=6, **kw)


def _facet_title(ax, text, fs=FS_TITLE):
    """Título de panel: ajuste por ancho medido de la celda y anclado a su izquierda por `align_panel_titles`."""
    ax.set_title(wrap_measured(text, TITLE_W_PT, fs, "bold"), fontsize=fs, fontweight="bold", loc="left")


def _break_marker(ax, x, lang, y=0.5):
    ax.axvline(x, color="#999999", ls="-.", lw=1.0, zorder=1)
    t = ax.text(x, y, tr("def_break", lang), transform=ax.get_xaxis_transform(), ha="center", va="center", fontsize=FS_ANN,
                color="#777777", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    t.set_gid(C.PLATE_KEEP)          # el quiebre marca un año concreto: su rótulo no se mueve de él


def heat(ax, wide: pd.DataFrame, rowlabels: list[str], lang: str, fmt, cmap="Blues", cbar_label="",
         suppressed: pd.DataFrame | None = None, fs=FS_CELL, cbar=True):
    """Mapa de calor región × año: celdas sin fila en gris («no reportado») y celdas suprimidas rotuladas «<5»."""
    import matplotlib as mpl
    data = wide.to_numpy(dtype=float)
    sup = suppressed.to_numpy(dtype=bool) if suppressed is not None else np.zeros_like(data, dtype=bool)
    mask = (~np.isfinite(data)) | sup
    cm = mpl.colormaps[cmap].resampled(256).copy()
    cm.set_bad("#e8e8e8")
    im = ax.imshow(np.ma.masked_array(data, mask), aspect="auto", cmap=cm)
    ax.set_xticks(range(wide.shape[1]))
    # A partir de seis columnas los rótulos de año no caben en horizontal en una celda de 90 mm: se inclinan.
    ax.set_xticklabels([str(c) for c in wide.columns], fontsize=FS_TICK,
                       rotation=45 if wide.shape[1] > 6 else 0,
                       ha="right" if wide.shape[1] > 6 else "center")
    ax.set_yticks(range(wide.shape[0]))
    ax.set_yticklabels(rowlabels, fontsize=FS_ANN)
    ax.grid(False)
    for i in range(wide.shape[0]):
        for j in range(wide.shape[1]):
            v = data[i, j]
            if not np.isfinite(v):
                txt, col = "—", "#777777"
            elif sup[i, j]:
                txt, col = tr("suppressed", lang), "#555555"
            else:
                txt = fmt(v, lang)
                # El color del texto se decide por la luminancia real de la celda, no por un umbral sobre el valor:
                # con un umbral sobre el valor el blanco cae sobre celdas claras y el número queda ilegible.
                rr, gg, bb, _aa = im.cmap(im.norm(v))
                col = "white" if (0.2126 * rr + 0.7152 * gg + 0.0722 * bb) < 0.55 else DARK
            ax.text(j, i, txt, ha="center", va="center", fontsize=fs, color=col)
    if cbar:
        cb = ax.figure.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
        cb.ax.tick_params(labelsize=FS_ANN)
        # Una sola línea, garantizada por medida: la barra es tan estrecha que un rótulo plegado en dos
        # líneas crece hacia dentro y acaba sobre sus propias marcas. Si no cabe, se reduce hasta el suelo
        # de 6 pt; si aun así no cabe, la unidad completa vive en el rótulo del eje X del panel.
        fs_cb = FS_ANN
        while fs_cb > PLATE_FS_FLOOR and _text_width_pt(str(cbar_label), fs_cb, "normal") > CBAR_LABEL_PT:
            fs_cb -= 0.2
        cb.set_label(str(cbar_label), fontsize=max(PLATE_FS_FLOOR, fs_cb), labelpad=2.0)
    return im


def lorenz(values) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Curva de Lorenz, Gini y participación del decil superior de una distribución de valores no negativos."""
    v = np.sort(np.asarray([x for x in np.asarray(values, dtype=float) if np.isfinite(x) and x > 0]))
    n = v.size
    if n == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.nan, np.nan
    total = v.sum()
    cum = np.concatenate([[0.0], np.cumsum(v) / total])
    x = np.concatenate([[0.0], np.arange(1, n + 1) / n])
    i = np.arange(1, n + 1)
    gini = float((2.0 * np.sum(i * v)) / (n * total) - (n + 1.0) / n)
    k = int(np.ceil(n / 10))
    top = float(v[-k:].sum() / total)
    return x, cum, gini, top


def wilson_pct(k, n, lang=None):
    p, lo, hi = C.wilson(float(k), float(n)) if n and n > 0 else (np.nan, np.nan, np.nan)
    return 100 * p, 100 * lo, 100 * hi


def rate_ci(count, population, per=PER):
    if count is None or pd.isna(count) or population is None or pd.isna(population) or population <= 0:
        return np.nan, np.nan, np.nan
    lo, hi = poisson_limits([float(count)])
    return per * float(count) / population, per * float(lo[0]) / population, per * float(hi[0]) / population


def bars_with_n(ax, years, values, n_est, color, label, width=0.38, offset=0.0, lang="es", fs=FS_CELL, show_n=True):
    x = np.asarray(years, dtype=float) + offset
    ax.bar(x, values, width=width, color=color, label=label)
    if show_n:
        for xi, v, n in zip(x, values, n_est):
            if pd.notna(v):
                _ann(ax, xi, v, f"n={num(n, 0, lang)}", DARK, fs=fs, dy=2)
    return x


def hbars_by_year(ax, labels, mat: pd.DataFrame, years, lang, colors=None, fs=FS_CELL, n_est: pd.DataFrame | None = None):
    """Barras horizontales agrupadas por año para un conjunto de códigos (una fila por código)."""
    colors = colors or [YEARCOL.get(int(y), OK[i % len(OK)]) for i, y in enumerate(years)]
    n = len(years)
    h = 0.8 / n
    ypos = np.arange(len(labels))
    tagged: list[tuple] = []
    for k, y in enumerate(years):
        vals = mat[y].to_numpy(dtype=float)
        off = (k - (n - 1) / 2) * h
        ax.barh(ypos + off, np.nan_to_num(vals), height=h * 0.92, color=colors[k], label=str(y))
        for i, v in enumerate(vals):
            if pd.notna(v):
                extra = ""
                if n_est is not None:
                    extra = f" (n={num(n_est[y].to_numpy()[i], 0, lang)})"
                t = ax.text(v, ypos[i] + off, f" {num(v, 0, lang)}{extra}", va="center", ha="left", fontsize=fs, color=DARK)
                tagged.append((t, float(v)))
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=FS_ANN)
    ax.invert_yaxis()
    # Holgura PROVISIONAL: el hueco definitivo lo mide `room_for_end_labels` con la composición congelada,
    # porque el ancho del eje todavía no existe (`plate_fit` lo reparte después).
    ax.set_xlim(0, float(np.nanmax(mat.to_numpy(dtype=float))) * 1.45)
    ax._end_labels = getattr(ax, "_end_labels", []) + tagged
    return ypos


def room_for_end_labels(fig) -> None:
    """Ensancha el eje x hasta que el rótulo escrito al FINAL de una barra horizontal quepa dentro.

    El rótulo se escribe en `x = v` con `ha="left"`, de modo que empieza donde acaba su barra y crece hacia
    la derecha. Si no cabe, `common._pl_clip_guard` —que devuelve dentro de su celda todo texto que se
    salga— lo empuja a la izquierda, y el único sitio al que puede empujarlo es ENCIMA de la barra que
    rotula: en el panel (e) de la Figura S26 el «18.142 (n=1.082)» de 2024 se imprimía sobre su propia
    barra (3,7 mm de solape en inglés, 4,9 mm en español) y el borde de la barra partía la cifra.

    El verificador de composición no lo ve, y por eso el módulo salía limpio: `_ck_value_labels` mide el
    rótulo contra marcadores y barras de error, nunca contra el rectángulo de una barra, y `_ck_bar_masks`
    sólo juzga rótulos CON recuadro —un rótulo sin recuadro no borra la barra—, y éste no lo tiene porque
    `_pl_backing` corre ANTES de `_pl_clip_guard`: cuando se decidió que no había tinta debajo, el rótulo
    todavía estaba fuera. La cura es no darle nunca el motivo para moverse.

    La cuenta, con el eje ya congelado: si el eje ocupa A píxeles desde `x0`, la barra acaba en `v` y su
    rótulo mide `w` píxeles, el rótulo cabe cuando `A·(v−x0)/(X−x0) + w ≤ límite − borde izquierdo`, es
    decir cuando el eje llega al menos a `x0 + A·(v−x0)/R`, con `R` el hueco que queda a la derecha. El
    límite es el mismo que aplica `_pl_clip_guard` (el borde de la celda de rejilla), y nunca más allá del
    propio eje. Sólo se ENSANCHA: un eje que ya tiene sitio no se toca.
    """
    r = C._pl_renderer(fig)
    for ax in fig.axes:
        tagged = [(t, v) for t, v in getattr(ax, "_end_labels", []) if t.get_visible()]
        if not tagged or not ax.get_visible():
            continue
        box = ax.get_window_extent(renderer=r)
        cell = C.plate_cell_box(fig, ax)
        limit = min(box.x1, cell.x1 - 1.0, fig.bbox.x1 - 1.0)
        span = float(box.width)
        if span <= 0.0:
            continue
        x0, x1 = ax.get_xlim()
        need = float(x1)
        for t, v in tagged:
            b = C._pl_extent(t, r)
            if b is None or v <= x0:
                continue
            room = limit - float(box.x0) - float(b.width) - 1.0     # un píxel de aire contra el límite
            if room <= 0.05 * span:
                continue          # ni vaciando el eje cabría: lo resuelve quien escribió el rótulo
            need = max(need, x0 + span * (v - x0) / room)
        if need > x1:
            ax.set_xlim(x0, need)


# ===========================================================================
# E11 · A03 en detalle: cada código de cada era
# ===========================================================================
A03_ERAS = {
    "legacy_long": ["03500404", "03500405"],
    "legacy_mchat": ["03500406", "03500407"],
    "era2023": ["09600212", "09600213", "09600214", "09600215", "09600216", "09600217", "09600218", "09600219"],
    "era2024": ["03700104", "03700105", "03700106", "03700107", "03700108", "03700109"],
    "era2025": ["03710013", "03710014", "03710015", "03710016", "03710017", "03710018", "03710019", "03710020", "03710021"],
}
A03_ALL = [c for v in A03_ERAS.values() for c in v]


def prep_e11(D: Data) -> dict:
    """Totales anuales y establecimientos de cada código A03, la serie mensual legado y la razón alterado/realizado."""
    long = []
    for code in A03_ALL:
        r = D.row(code)
        for t in r.itertuples():
            long.append(dict(code=code, era=t.era, year=int(t.year), total=t.total, n_reporting_establishments=int(t.n_reporting_establishments),
                             n_stable_panel_establishments=int(t.n_stable_panel_establishments), stable_panel_total=t.stable_panel_total,
                             n_rows=int(t.n_rows), n_rows_zero=int(t.n_rows_zero), n_rows_empty=int(t.n_rows_empty), unit=t.unit,
                             aggregation_rule=t.aggregation_rule, source_file=t.source_file))
    long = pd.DataFrame(long)
    monthly = D.by_month(["03500404", "03500405", "03500406", "03500407"])
    per_code_month = (D.tidy[D.tidy.code.isin(["03500406", "03500407"])]
                      .groupby(["year", "month", "code"], as_index=False)
                      .agg(total=("total_known", lambda s: s.sum(min_count=1)), n_est=("IdEstablecimiento", "nunique")))
    monthly_codes = (D.tidy[D.tidy.code.isin(["03500404", "03500405", "03500406", "03500407"])]
                     .groupby(["year", "month", "code"], as_index=False)
                     .agg(total=("total_known", lambda s: s.sum(min_count=1)), n_est=("IdEstablecimiento", "nunique")))
    ratio = []
    for y in range(2019, 2023):
        for scope in ("all", "no_feb_2019"):
            sub = per_code_month[per_code_month.year == y]
            if scope == "no_feb_2019" and y == 2019:
                sub = sub[sub.month != 2]
            done = sub.loc[sub.code == "03500406", "total"].sum(min_count=1)
            alt = sub.loc[sub.code == "03500407", "total"].sum(min_count=1)
            p, lo, hi = wilson_pct(alt, done) if pd.notna(done) and done > 0 else (np.nan, np.nan, np.nan)
            ratio.append(dict(year=y, scope=scope, performed=done, altered=alt, ratio_pct=p, ratio_lo=lo, ratio_hi=hi))
    ratio = pd.DataFrame(ratio)
    feb = per_code_month[(per_code_month.year == 2019) & (per_code_month.month == 2)]
    return dict(long=long, monthly=monthly, monthly_codes=monthly_codes, ratio=ratio,
                feb2019=dict(done=float(feb.loc[feb.code == "03500406", "total"].sum()),
                             altered=float(feb.loc[feb.code == "03500407", "total"].sum())))


def plate_e11(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e11"]
    long, monthly_codes, ratio = E["long"], E["monthly_codes"], E["ratio"]
    fig, gs = new_plate()

    # --- A: era legado larga (2019–2024) -------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    rows_a = []
    for k, (code, col) in enumerate([("03500404", OK[0]), ("03500405", OK[1])]):
        s = long[long.code == code].sort_values("year")
        off = -0.19 + 0.38 * k
        bars_with_n(ax, s.year, s.total, s.n_reporting_establishments, col, A03_CODE_LABEL[code][lang],
                    width=0.38, offset=off, lang=lang, show_n=False)
        rows_a.append((col, list(zip(s.year.to_numpy(dtype=float) + off, s.n_reporting_establishments))))
    ax.set_xticks(sorted(long[long.code == "03500404"].year.unique()))
    ax.set_ylabel(tr("u_children", lang), fontsize=FS_BASE)
    # Los «n=» de dos barras contiguas se tocaban encima de ellas y el recuadro de uno borraba la primera
    # cifra del otro. Bajo el eje, cada número queda en la vertical de su barra y en el color de su serie.
    n_strip(ax, rows_a, lang)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('n_rows', lang)}")
    ax.set_ylim(0, float(long[long.code == "03500404"].total.max()) * 1.35)
    _context(ax, lang, pandemic_text=False, law_pos=0.985, law_va="top")
    # Leyenda estrecha (una columna, texto plegado a 18 caracteres): a lo ancho ocupaba el cielo entero del
    # panel y no dejaba sitio a la marca de la Ley, que es un rótulo clavado a su línea.
    legend_wrapped(ax, loc="upper left", width=18, fontsize=FS_ANN, ncol=1,
                   title=tr("n_estab", lang), title_fontsize=FS_ANN).set_gid(C.PLATE_KEEP)
    _facet_title(ax, tr("e11_a", lang))
    letter(ax, "a")

    # --- B: era legado M-CHAT (2019–2022) ------------------------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    rows_b = []
    for k, (code, col) in enumerate([("03500406", OK[2]), ("03500407", OK[3])]):
        s = long[long.code == code].sort_values("year")
        off = -0.19 + 0.38 * k
        bars_with_n(ax, s.year, s.total, s.n_reporting_establishments, col, A03_CODE_LABEL[code][lang],
                    width=0.38, offset=off, lang=lang, show_n=False)
        rows_b.append((col, list(zip(s.year.to_numpy(dtype=float) + off, s.n_reporting_establishments))))
    ax.set_xticks(sorted(long[long.code == "03500406"].year.unique()))
    ax.set_ylabel(tr("u_screen", lang), fontsize=FS_BASE)
    n_strip(ax, rows_b, lang)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('n_rows', lang)}")
    ax.set_ylim(0, float(long[long.code == "03500406"].total.max()) * 1.45)
    _context(ax, lang, law=False, pandemic_text=False)
    legend_wrapped(ax, loc="upper left", width=18, fontsize=FS_ANN, ncol=1,
                   title=tr("n_estab", lang), title_fontsize=FS_ANN)
    _facet_title(ax, tr("e11_b", lang))
    letter(ax, "b")

    # --- C: la serie mensual de 2019 y el atípico de febrero -----------------------------------
    ax = fig.add_subplot(gs[1, 0])
    m2019 = monthly_codes[monthly_codes.year == 2019]
    for code, col in [("03500404", OK[0]), ("03500405", OK[1]), ("03500406", OK[2]), ("03500407", OK[3])]:
        s = m2019[m2019.code == code].sort_values("month")
        ax.plot(s.month, s.total, marker="o", ms=4, lw=1.6, color=col, label=A03_CODE_LABEL[code][lang])
    ax.set_yscale("log")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(tr("months_abbr", lang), fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(f"{tr('monthly_total', lang)} {tr('log_scale', lang)}", fontsize=FS_BASE)
    ax.axvspan(1.6, 2.4, color=OK[1], alpha=0.10, zorder=0)
    # La nota llevaba una flecha hasta el pico de febrero: la caja de una anotación con flecha es la UNIÓN
    # del texto y de la flecha, de modo que barría los ocho marcadores de enero a marzo por muy arriba que
    # se escribiera el texto. La banda naranja ya señala febrero y la nota empieza por «feb. 2019», así que
    # la flecha sobra.
    headroom(ax, 0.62)
    ax.text(2.7, 0.985, wrap_measured(tr("feb_outlier", lang), 108.0, FS_ANN, "normal"),
            transform=ax.get_xaxis_transform(), fontsize=FS_ANN, color="#8a3b12", ha="left", va="top")
    legend_wrapped(ax, loc="upper center", bbox_to_anchor=(0.5, -0.16), expand=False, ncol=2, width=21,
                   fontsize=FS_CELL)
    _facet_title(ax, tr("e11_c", lang))
    letter(ax, "c")

    # --- D: razón alterado/realizado dentro de la era legado -----------------------------------
    ax = fig.add_subplot(gs[1, 1])
    for k, (scope, col, lab) in enumerate([("all", OK[0], tr("ratio_all", lang)), ("no_feb_2019", OK[4], tr("ratio_nofeb", lang))]):
        s = ratio[ratio.scope == scope].sort_values("year")
        x = s.year.to_numpy(dtype=float) + (-0.12 + 0.24 * k)
        ax.errorbar(x, s.ratio_pct, yerr=[s.ratio_pct - s.ratio_lo, s.ratio_hi - s.ratio_pct], fmt="o", ms=6,
                    color=col, ecolor=col, elinewidth=1.4, capsize=3, label=lab)
        for xi, r in zip(x, s.itertuples()):
            if scope == "all" or r.year == 2019:
                _ann(ax, xi, r.ratio_hi, f"{num(r.altered, 0, lang)}/{num(r.performed, 0, lang)}", col, fs=FS_CELL, dy=4)
    ax.set_xticks(sorted(ratio.year.unique()))
    ax.set_ylabel(tr("ratio_axis_alt", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    ax.set_ylim(0, 100)
    _context(ax, lang, law=False, pandemic_pos=0.66, pandemic_va="bottom")
    legend_wrapped(ax, loc="lower right", expand=False, fontsize=FS_ANN, frameon=True, framealpha=0.92, edgecolor="none")
    note_in_panel(ax, tr("not_positivity", lang), 0.02, 0.985, va="top", color="#8a3b12")
    _facet_title(ax, tr("e11_d", lang))
    letter(ax, "d")

    # --- E: era 2023–2024, todos los códigos ---------------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    codes = A03_ERAS["era2023"]
    mat = long[long.code.isin(codes)].pivot(index="code", columns="year", values="total").reindex(codes)
    nes = long[long.code.isin(codes)].pivot(index="code", columns="year", values="n_reporting_establishments").reindex(codes)
    hbars_by_year(ax, [A03_SHORT[c][lang].replace("\n", " ") for c in codes], mat, [2023, 2024], lang, n_est=nes)
    ax.set_xlabel(tr("u_screen", lang), fontsize=FS_BASE)
    legend_wrapped(ax, fontsize=FS_TICK, title=tr("n_estab", lang), title_fontsize=FS_ANN, loc="lower right")
    _facet_title(ax, tr("e11_e", lang))
    letter(ax, "e")

    # --- F: eras 2024 (31–59 meses) y 2025 (rediseño) en facetas separadas ---------------------
    # El panel f es UNO: sus dos facetas son dos eras del mismo código, no dos paneles. El título del panel
    # y su letra van sobre los ejes anfitriones; cada faceta lleva sólo un rótulo pequeño, sin negrita, para
    # que no se lea como una cabecera de panel propia.
    host = fig.add_subplot(gs[2, 1]); host.axis("off")
    f1 = host.inset_axes([0.34, 0.56, 0.64, 0.34])
    f2 = host.inset_axes([0.34, 0.06, 0.64, 0.34])
    for axx, key, ttl in ((f1, "era2024", tr("e11_f1", lang)), (f2, "era2025", tr("e11_f2", lang))):
        codes = A03_ERAS[key]
        year = 2024 if key == "era2024" else 2025
        s = long[long.code.isin(codes) & (long.year == year)].set_index("code").reindex(codes)
        axx.barh(np.arange(len(codes)), s.total.to_numpy(dtype=float), color=OK[5] if key == "era2024" else OK[2], height=0.72)
        for i, r in enumerate(s.itertuples()):
            axx.text(r.total, i, f" {num(r.total, 0, lang)} (n={num(r.n_reporting_establishments, 0, lang)})", va="center", ha="left", fontsize=FS_CELL, color=DARK)
        axx.set_yticks(range(len(codes)))
        axx.set_yticklabels([A03_SHORT[c][lang].replace("\n", " ") for c in codes], fontsize=FS_CELL)
        axx.invert_yaxis()
        axx.set_xlim(0, float(np.nanmax(s.total.to_numpy(dtype=float))) * 1.55)
        axx.tick_params(labelsize=FS_ANN)
        if axx is f2:                       # las dos facetas comparten unidad: la glosa se escribe una sola vez
            axx.set_xlabel(tr("u_screen", lang), fontsize=FS_ANN)
        axx.set_title(wrap_measured(ttl, TITLE_W_PT * 0.66, FS_TICK, "normal"), fontsize=FS_TICK,
                      fontweight="normal", color="#555555", loc="left", pad=2.0)
    _facet_title(host, tr("e11_f", lang))
    letter(host, "f")

    name = PLATES["E11"]
    title = {"es": f"A03 en detalle: todos los códigos de tamizaje de autismo en la APS por era de definición, Chile 2019–2025 — {vlabel(variant, lang)}",
             "en": f"A03 in detail: every primary-care autism screening code by definition era, Chile 2019–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a) Códigos 03500404 y 03500405 de la era legado, presentes de 2019 a 2024. (b) M-CHAT realizado (03500406) y "
                      "alterado (03500407), presentes solo de 2019 a 2022. (c) Los cuatro códigos legado por mes en 2019 en escala "
                      "logarítmica: febrero de 2019 concentra 1.051 M-CHAT realizados y 1.028 alterados, un valor atípico del archivo "
                      "que se informa y no se corrige ni se elimina. (d) Razón entre M-CHAT alterados y realizados dentro de la era "
                      "legado, con y sin febrero de 2019, con intervalos de Wilson; no es positividad poblacional del M-CHAT porque el "
                      "denominador son niños/as con alteración de lenguaje o área social ya detectada en el control de 18 meses. "
                      "(e) Los ocho códigos de la era 2023–2024 (M-CHAT-R/F) con su total anual. (f) Los seis códigos de 31–59 meses "
                      "añadidos en 2024 y los nueve del rediseño de 2025, en facetas separadas. En todos los paneles n es el número de "
                      "establecimientos con al menos una fila del código en el año. Ninguna línea une eras distintas. La banda gris marca la "
                      "disrupción del reporte de 2020–2021 y la línea punteada la publicación de la Ley 21.545 (marzo de 2023), presente solo "
                      "como contexto de política."),
               "en": ("(a) Legacy-era codes 03500404 and 03500405, present from 2019 to 2024. (b) M-CHAT performed (03500406) and altered "
                      "(03500407), present only from 2019 to 2022. (c) The four legacy codes by month in 2019 on a logarithmic scale: "
                      "February 2019 concentrates 1,051 M-CHATs performed and 1,028 altered, an outlying file value that is reported and "
                      "neither corrected nor deleted. (d) Ratio of altered to performed M-CHATs within the legacy era, with and without "
                      "February 2019, with Wilson intervals; this is not population M-CHAT positivity because the denominator is children "
                      "with an already detected language or social-area alteration at the 18-month control. (e) The eight codes of the "
                      "2023–2024 era (M-CHAT-R/F) with their annual totals. (f) The six 31–59-month codes added in 2024 and the nine codes "
                      "of the 2025 redesign, in separate facets. In every panel n is the number of establishments with at least one row for "
                      "the code in the year. No line joins different eras. The grey band marks the 2020–2021 reporting disruption and the "
                      "dotted line the publication of Law 21.545 (March 2023), present only as policy context.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla de respaldo ---------------------------------------------------------------------
    years = list(range(2019, 2026))
    rows = []
    for code in A03_ALL:
        s = long[long.code == code].set_index("year")
        r = {tr("code", lang): code, tr("indicator", lang): A03_CODE_LABEL[code][lang],
             tr("era", lang): s.era.iloc[0] if len(s) else tr("na", lang)}
        for y in years:
            r[str(y)] = val_n(s.total.get(y, np.nan), s.n_reporting_establishments.get(y, np.nan), lang) if y in s.index else tr("outside_era", lang)
        rows.append(r)
    for scope, lab in (("all", tr("ratio_all", lang)), ("no_feb_2019", tr("ratio_nofeb", lang))):
        s = ratio[ratio.scope == scope].set_index("year")
        r = {tr("code", lang): "03500407 / 03500406", tr("indicator", lang): f"{tr('e11_d', lang)} — {lab}", tr("era", lang): "2019–2022"}
        for y in years:
            r[str(y)] = f"{pct(s.ratio_pct.get(y), lang)} ({ci(s.ratio_lo.get(y), s.ratio_hi.get(y), 1, lang)})" if y in s.index else tr("outside_era", lang)
        rows.append(r)
    formatted = pd.DataFrame(rows)
    numeric = long.merge(pd.DataFrame({"code": list(A03_CODE_LABEL), "indicator_label": [A03_CODE_LABEL[c]["en"] for c in A03_CODE_LABEL]}), on="code", how="left")
    numeric = pd.concat([numeric.assign(measure="annual_sum"),
                         ratio.assign(code="03500407/03500406", indicator_label="altered/performed within the legacy era", measure="ratio_pct_wilson",
                                      era="2019–2022", total=ratio.ratio_pct, n_reporting_establishments=np.nan)], ignore_index=True)
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "registros de tamizaje o de control (flujo anual, suma de meses de COL01+COL02)", "en": "screening or control records (annual flow, sum of months of COL01+COL02)"}[lang],
                 denominator={"es": "ninguno para los conteos; para la razón, los M-CHAT realizados del mismo código-año", "en": "none for the counts; for the ratio, the M-CHATs performed in the same code-year"}[lang],
                 coverage={"es": "red pública de APS que reporta el código", "en": "public primary-care network reporting the code"}[lang],
                 era={"es": "03500404/03500405 2019–2024; 03500406/03500407 2019–2022; 09600212–09600219 2023–2024 (09600217 solo 2023); 03700104–03700109 2024; 03710013–03710021 2025",
                      "en": "03500404/03500405 2019–2024; 03500406/03500407 2019–2022; 09600212–09600219 2023–2024 (09600217 in 2023 only); 03700104–03700109 2024; 03710013–03710021 2025"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con al menos una fila del código en el año", "en": "n in brackets = establishments with at least one row for the code in the year"}[lang],
                 sources=f"{SRC_A}; {SRC_TIDY}",
                 extra={"es": "La razón alterado/realizado se calcula solo dentro de la era legado y no es positividad poblacional del M-CHAT.",
                        "en": "The altered-to-performed ratio is computed only within the legacy era and is not population M-CHAT positivity."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E12 · A03 2023–2025: estructura de riesgo y derivación
# ===========================================================================
def prep_e12(D: Data, e11: dict) -> dict:
    long = e11["long"].set_index(["code", "year"])

    def g(code, year, field="total"):
        try:
            return float(long.loc[(code, year), field])
        except KeyError:
            return np.nan

    comp = []
    for y in (2023, 2024):
        low, med, high = g("09600213", y), g("09600214", y), g("09600215", y)
        tot = np.nansum([low, med, high])
        comp.append(dict(era="2023–2024", year=y, low=low, medium=med, high=high, part1_total=tot,
                         low_pct=100 * low / tot, medium_pct=100 * med / tot, high_pct=100 * high / tot,
                         n_est=g("09600213", y, "n_reporting_establishments")))
    low, med_nr, med_r, high = g("03710016", 2025), g("03710017", 2025), g("03710018", 2025), g("03710019", 2025)
    tot = np.nansum([low, med_nr, med_r, high])
    comp.append(dict(era="2025", year=2025, low=low, medium=med_nr + med_r, high=high, part1_total=tot,
                     low_pct=100 * low / tot, medium_pct=100 * (med_nr + med_r) / tot, high_pct=100 * high / tot,
                     n_est=g("03710016", 2025, "n_reporting_establishments")))
    comp = pd.DataFrame(comp)

    ref = []
    for y in (2023, 2024):
        high, refh = g("09600215", y), g("09600216", y)
        p, lo, hi = wilson_pct(refh, high)
        ref.append(dict(era="2023–2024", year=y, denominator_code="09600215", numerator_code="09600216",
                        denominator=high, numerator=refh, pct=p, lo=lo, hi=hi,
                        n_est=g("09600216", y, "n_reporting_establishments"),
                        n_est_denominator=g("09600215", y, "n_reporting_establishments")))
    med_tot = med_nr + med_r
    p, lo, hi = wilson_pct(med_r, med_tot)
    ref.append(dict(era="2025", year=2025, denominator_code="03710017+03710018", numerator_code="03710018",
                    denominator=med_tot, numerator=med_r, pct=p, lo=lo, hi=hi,
                    n_est=g("03710018", 2025, "n_reporting_establishments")))
    susp_nr, susp_r = g("03710020", 2025), g("03710021", 2025)
    p, lo, hi = wilson_pct(susp_r, susp_nr + susp_r)
    ref.append(dict(era="2025", year=2025, denominator_code="03710020+03710021", numerator_code="03710021",
                    denominator=susp_nr + susp_r, numerator=susp_r, pct=p, lo=lo, hi=hi,
                    n_est=g("03710021", 2025, "n_reporting_establishments")))
    ref = pd.DataFrame(ref)

    second = []
    for y in (2023, 2024):
        no_ref, with_ref = g("09600218", y), g("09600219", y)
        tot2 = np.nansum([no_ref, with_ref])
        p, lo, hi = wilson_pct(with_ref, tot2)
        second.append(dict(year=y, medium_in_part1=g("09600217", y), no_referral=no_ref, referral=with_ref,
                           second_total=tot2, referral_pct=p, referral_lo=lo, referral_hi=hi,
                           n_est=g("09600219", y, "n_reporting_establishments"),
                           n_est_medium=g("09600217", y, "n_reporting_establishments"),
                           n_est_no_referral=g("09600218", y, "n_reporting_establishments")))
    second = pd.DataFrame(second)
    return dict(comp=comp, ref=ref, second=second)


def plate_e12(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E, E11 = P["e12"], P["e11"]
    long = E11["long"]
    comp, ref, second = E["comp"], E["ref"], E["second"]
    fig, gs = new_plate()

    # --- A: composición del resultado de 1.ª parte, 2023–2024 ----------------------------------
    ax = fig.add_subplot(gs[0, 0])
    s = comp[comp.era == "2023–2024"]
    x = s.year.to_numpy(dtype=float)
    bottom = np.zeros(len(s))
    for key, col, lab in (("low", OK[5], tr("risk_low", lang)), ("medium", OK[4], tr("risk_medium", lang)), ("high", OK[1], tr("risk_high", lang))):
        v = s[key].to_numpy(dtype=float)
        ax.bar(x, v, bottom=bottom, width=0.5, color=col, label=lab)
        for xi, vi, bi, pc in zip(x, v, bottom, s[f"{key}_pct"]):
            ax.text(xi, bi + vi / 2, f"{num(vi, 0, lang)}\n{pct(pc, lang)}", ha="center", va="center", fontsize=FS_ANN, color="white" if key != "low" else DARK)
        bottom = bottom + np.nan_to_num(v)
    for xi, r in zip(x, s.itertuples()):
        _ann(ax, xi, r.part1_total, f"n={num(r.n_est, 0, lang)}", DARK, fs=FS_ANN, dy=3)
    ax.set_xticks(x); ax.set_xlim(2022.5, 2024.5)
    ax.set_ylim(0, float(s.part1_total.max()) * 1.20)
    ax.set_ylabel(tr("u_screen", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_TICK)
    _facet_title(ax, tr("e12_a", lang))
    letter(ax, "a")

    # --- B: derivación del riesgo alto ---------------------------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    s = ref[ref.era == "2023–2024"]
    x = s.year.to_numpy(dtype=float)
    ax.bar(x - 0.16, s.denominator, width=0.32, color=OK[1], label=tr("risk_high", lang))
    ax.bar(x + 0.16, s.numerator, width=0.32, color=OK[3], label=tr("high_referred", lang))
    for r in s.itertuples():
        # cada n rotula la barra a la que pertenece: 09600215 (denominador) y 09600216 (numerador)
        _ann(ax, r.year - 0.16, r.denominator, f"n={num(r.n_est_denominator, 0, lang)}", DARK, fs=FS_ANN, dy=3)
        _ann(ax, r.year + 0.16, r.numerator, f"n={num(r.n_est, 0, lang)}", DARK, fs=FS_ANN, dy=3)
    ax.set_xticks(x); ax.set_xlim(2022.5, 2024.5)
    ax.set_ylim(0, float(s.denominator.max()) * 1.45)
    ax.set_ylabel(tr("u_screen", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_TICK)
    ax2 = ax.twinx()
    ax2.errorbar(x, s.pct, yerr=[s.pct - s.lo, s.hi - s.pct], fmt="D", ms=6, color=DARK, ecolor=DARK, elinewidth=1.3, capsize=3)
    for r in s.itertuples():
        _ann(ax2, r.year, r.hi, pct(r.pct, lang), DARK, fs=FS_ANN, dy=4)
    ax2.set_ylim(0, 100); ax2.grid(False)
    ax2.set_ylabel(tr("share_referred", lang), fontsize=FS_TICK)
    _facet_title(ax, tr("e12_b", lang))
    letter(ax, "b")

    # --- C: resultados de la segunda parte -----------------------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    x = second.year.to_numpy(dtype=float)
    ax.bar(x - 0.22, second.medium_in_part1, width=0.21, color=OK[4], label=A03_SHORT["09600217"][lang].replace("\n", " "))
    ax.bar(x, second.no_referral, width=0.21, color=OK[0], label=A03_SHORT["09600218"][lang].replace("\n", " "))
    ax.bar(x + 0.22, second.referral, width=0.21, color=OK[2], label=A03_SHORT["09600219"][lang].replace("\n", " "))
    for r in second.itertuples():
        # cada n rotula su propia barra (09600217, 09600218 y 09600219); el porcentaje va sobre la barra de derivación
        _ann(ax, r.year + 0.22, r.referral, f"{pct(r.referral_pct, lang)}\n({ci(r.referral_lo, r.referral_hi, 1, lang)})\nn={num(r.n_est, 0, lang)}",
             DARK, fs=FS_CELL, dy=3)
        _ann(ax, r.year, r.no_referral, f"n={num(r.n_est_no_referral, 0, lang)}", DARK, fs=FS_ANN, dy=3)
        if pd.notna(r.medium_in_part1):
            _ann(ax, r.year - 0.22, r.medium_in_part1, f"n={num(r.n_est_medium, 0, lang)}", DARK, fs=FS_ANN, dy=3)
    ax.set_xticks(x); ax.set_xlim(2022.5, 2024.5)
    ax.set_ylim(0, float(np.nanmax([second.medium_in_part1.max(), second.no_referral.max(), second.referral.max()])) * 1.62)
    ax.set_ylabel(tr("u_screen", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_ANN)
    _facet_title(ax, tr("e12_c", lang))
    letter(ax, "c")

    # --- D: códigos 31–59 meses de 2024 --------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    codes = A03_ERAS["era2024"]
    s = long[long.code.isin(codes) & (long.year == 2024)].set_index("code").reindex(codes)
    # Eje transpuesto: los seis rótulos de código no caben bajo un eje X de 90 mm sin superponerse ni bajar del
    # cuerpo mínimo; en barras horizontales cada rótulo tiene su propia línea.
    yb = np.arange(len(codes))
    ax.barh(yb, s.total.to_numpy(dtype=float), color=[OK[0], OK[5], OK[1], OK[2], OK[3], OK[4]], height=0.68)
    for i, r in enumerate(s.itertuples()):
        ax.text(r.total, i, f" {num(r.total, 0, lang)} (n={num(r.n_reporting_establishments, 0, lang)})",
                va="center", ha="left", fontsize=FS_ANN, color=DARK)
    ax.set_yticks(yb)
    ax.set_yticklabels([tick_label(A03_SHORT[c][lang].replace("\n", " "), 15) for c in codes], fontsize=FS_ANN)
    ax.invert_yaxis()
    ax.set_xlim(0, float(np.nanmax(s.total.to_numpy(dtype=float))) * 1.42)
    ax.set_xlabel(tr("u_children", lang), fontsize=FS_BASE)
    _facet_title(ax, tr("e12_d", lang))
    letter(ax, "d")

    # --- E: rediseño de 2025 -------------------------------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    codes = A03_ERAS["era2025"]
    s = long[long.code.isin(codes) & (long.year == 2025)].set_index("code").reindex(codes)
    cols = [OK[0]] * 3 + [OK[5], OK[4], OK[4], OK[1], OK[2], OK[2]]
    # Eje transpuesto: nueve códigos con rótulo propio; la línea que separa motivos de resultados pasa a ser
    # horizontal y cada bloque conserva su glosa.
    yb = np.arange(len(codes))
    ax.barh(yb, s.total.to_numpy(dtype=float), color=cols, height=0.72)
    for i, r in enumerate(s.itertuples()):
        ax.text(r.total, i, f" {num(r.total, 0, lang)} (n={num(r.n_reporting_establishments, 0, lang)})",
                va="center", ha="left", fontsize=FS_CELL, color=DARK)
    ax.axhline(2.5, color=GREY, ls="--", lw=1.0)
    # Las dos glosas de bloque se parten en líneas: en una sola caben menos que el ancho de la celda y se
    # escribían sobre el rótulo de valor de la barra más corta de su bloque.
    for _y, _key in ((2.0, "motives"), (6.0, "results_2025")):
        ax.text(0.985, _y, wrap_measured(tr(_key, lang), 74.0, FS_ANN, "normal"),
                transform=ax.get_yaxis_transform(), ha="right", va="center", linespacing=1.05,
                fontsize=FS_ANN, color="#555555", bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
    ax.set_yticks(yb)
    ax.set_yticklabels([tick_label(A03_SHORT[c][lang].replace("\n", " "), 15) for c in codes], fontsize=FS_CELL)
    ax.invert_yaxis()
    ax.set_xlim(0, float(np.nanmax(s.total.to_numpy(dtype=float))) * 1.45)
    ax.set_xlabel(tr("u_screen", lang), fontsize=FS_BASE)
    _facet_title(ax, f"{tr('e12_e', lang)} — {tr('era_2025', lang)}")
    letter(ax, "e")

    # --- F: composición del riesgo por era (facetas separadas, sin serie continua) --------------
    ax = fig.add_subplot(gs[2, 1])
    pos = [0, 1, 3]
    labs = ["2023", "2024", "2025"]
    bottom = np.zeros(3)
    for key, col, lab in (("low_pct", OK[5], tr("risk_low", lang)), ("medium_pct", OK[4], tr("risk_medium", lang)), ("high_pct", OK[1], tr("risk_high", lang))):
        v = comp[key].to_numpy(dtype=float)
        ax.bar(pos, v, bottom=bottom, width=0.62, color=col, label=lab)
        for p_, vi, bi in zip(pos, v, bottom):
            ax.text(p_, bi + vi / 2, pct(vi, lang), ha="center", va="center", fontsize=FS_ANN, color="white" if key != "low_pct" else DARK)
        bottom = bottom + np.nan_to_num(v)
    ax.axvline(2.0, color="#999999", ls="-.", lw=1.1)
    ax.text(2.0, 0.5, tr("def_break", lang), transform=ax.get_xaxis_transform(), ha="center", va="center", fontsize=FS_ANN,
            color="#777777", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))
    for p_, r in zip(pos, comp.itertuples()):
        _ann(ax, p_, 100, f"N={num(r.part1_total, 0, lang)}\nn={num(r.n_est, 0, lang)}", DARK, fs=FS_CELL, dy=3)
    ax.set_xticks(pos); ax.set_xticklabels(labs, fontsize=FS_BASE)
    ax.set_xlim(-0.7, 3.7); ax.set_ylim(0, 138)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel(tr("u_share", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("no_continuity", lang), fontsize=FS_TICK, color="#8a3b12")
    legend_wrapped(ax, loc="upper center", fontsize=FS_ANN, ncol=3)
    _facet_title(ax, tr("e12_f", lang))
    letter(ax, "f")

    name = PLATES["E12"]
    title = {"es": f"A03 2023–2025: estructura de riesgo y derivación del tamizaje M-CHAT-R/F por era de definición, Chile — {vlabel(variant, lang)}",
             "en": f"A03 2023–2025: risk and referral structure of M-CHAT-R/F screening by definition era, Chile — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a) Composición del resultado de la primera parte del M-CHAT-R/F en 2023 y 2024 (códigos 09600213–09600215), con el "
                      "recuento y el porcentaje de cada categoría. (b) Registros de riesgo alto (09600215) y de riesgo alto derivado a "
                      "especialista (09600216); el eje derecho muestra el porcentaje derivado con intervalo de Wilson, calculado dentro del "
                      "mismo código-año y nunca entre fuentes distintas. (c) Resultados de la segunda parte (09600217 riesgo medio en la "
                      "primera parte, presente solo en 2023; 09600218 sin derivación; 09600219 con derivación) y porcentaje derivado dentro "
                      "de la segunda parte. (d) Los seis códigos de 31–59 meses de la era 2024. (e) El rediseño de 2025: tres códigos de "
                      "motivo (16–30 meses) y seis de resultado y derivación. (f) Composición porcentual del resultado de riesgo por era, con "
                      "el quiebre de definición marcado: en 2025 el riesgo medio se registra ya separado por necesidad de derivación, de modo "
                      "que las tres barras describen instrumentos distintos y no forman una serie continua. n = establecimientos con al menos "
                      "una fila del código en el año; N = total de registros de primera parte del año."),
               "en": ("(a) Composition of the M-CHAT-R/F part-1 result in 2023 and 2024 (codes 09600213–09600215), with the count and the "
                      "percentage of each category. (b) High-risk records (09600215) and high risk referred to a specialist (09600216); the "
                      "right axis shows the percentage referred with a Wilson interval, computed within the same code-year and never across "
                      "different sources. (c) Part-2 outcomes (09600217 medium risk in part 1, present only in 2023; 09600218 no referral "
                      "required; 09600219 referral required) and the percentage referred within part 2. (d) The six 31–59-month codes of the "
                      "2024 era. (e) The 2025 redesign: three motive codes (16–30 months) and six result and referral codes. (f) Percentage "
                      "composition of the risk result by era, with the definition break marked: in 2025 medium risk is already recorded split "
                      "by referral need, so the three bars describe different instruments and do not form a continuous series. n = "
                      "establishments with at least one row for the code in the year; N = total part-1 records of the year.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    years = [2023, 2024, 2025]
    rows = []
    for code in A03_ERAS["era2023"] + A03_ERAS["era2024"] + A03_ERAS["era2025"]:
        s = long[long.code == code].set_index("year")
        r = {tr("code", lang): code, tr("indicator", lang): A03_CODE_LABEL[code][lang], tr("era", lang): s.era.iloc[0] if len(s) else tr("na", lang)}
        for y in years:
            r[str(y)] = val_n(s.total.get(y, np.nan), s.n_reporting_establishments.get(y, np.nan), lang) if y in s.index else tr("outside_era", lang)
        rows.append(r)
    derived = []
    d = {tr("code", lang): "09600213+09600214+09600215 / 03710016–03710019", tr("indicator", lang): tr("e12_f", lang), tr("era", lang): "2023–2024 | 2025"}
    for y in years:
        c = comp[comp.year == y]
        d[str(y)] = (f"{tr('risk_low', lang)} {pct(c.low_pct.iloc[0], lang)}; {tr('risk_medium', lang)} {pct(c.medium_pct.iloc[0], lang)}; "
                     f"{tr('risk_high', lang)} {pct(c.high_pct.iloc[0], lang)}") if len(c) else tr("outside_era", lang)
    derived.append(d)
    for key, lab in (("09600216/09600215", tr("e12_b", lang)),):
        d = {tr("code", lang): key, tr("indicator", lang): lab, tr("era", lang): "2023–2024"}
        s = ref[ref.numerator_code == "09600216"].set_index("year")
        for y in years:
            d[str(y)] = f"{pct(s.pct.get(y), lang)} ({ci(s.lo.get(y), s.hi.get(y), 1, lang)})" if y in s.index else tr("outside_era", lang)
        derived.append(d)
    d = {tr("code", lang): "09600219 / (09600218+09600219)", tr("indicator", lang): tr("e12_c", lang), tr("era", lang): "2023–2024"}
    s = second.set_index("year")
    for y in years:
        d[str(y)] = f"{pct(s.referral_pct.get(y), lang)} ({ci(s.referral_lo.get(y), s.referral_hi.get(y), 1, lang)})" if y in s.index else tr("outside_era", lang)
    derived.append(d)
    formatted = pd.DataFrame(rows + derived)
    numeric = pd.concat([comp.assign(block="risk_composition"), ref.assign(block="referral_share"), second.assign(block="second_part")], ignore_index=True)
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "registros de tamizaje M-CHAT-R/F y de derivación (flujo anual)", "en": "M-CHAT-R/F screening and referral records (annual flow)"}[lang],
                 denominator={"es": "para los porcentajes, el código de la misma era y año indicado en la columna «código»", "en": "for the percentages, the code of the same era and year named in the 'code' column"}[lang],
                 coverage={"es": "red pública de APS que reporta el código", "en": "public primary-care network reporting the code"}[lang],
                 era={"es": "09600212–09600219 (2023–2024; 09600217 solo 2023); 03700104–03700109 (2024); 03710013–03710021 (2025)",
                      "en": "09600212–09600219 (2023–2024; 09600217 in 2023 only); 03700104–03700109 (2024); 03710013–03710021 (2025)"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con al menos una fila del código en el año", "en": "n in brackets = establishments with at least one row for the code in the year"}[lang],
                 sources=f"{SRC_A}; {SRC_TIDY}",
                 extra={"es": "Los porcentajes se calculan dentro del mismo código-año; no son probabilidades individuales ni conversiones entre etapas de una cascada.",
                        "en": "Percentages are computed within the same code-year; they are not individual probabilities and not conversions between the stages of a cascade."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E13 · A05 regional
# ===========================================================================
A05_YEARS = [2021, 2022, 2023, 2024, 2025]


def prep_e13(D: Data, variant: str) -> dict:
    strict = [CFG.STRICT["a05_entry"]]
    fam = CFG.VARIANTS[variant]["a05_entry"]
    tot, est, sup = D.region_matrix(strict, A05_YEARS)
    pop = D.pop_reg.reindex(index=tot.index, columns=A05_YEARS)
    rate = PER * tot / pop
    ftot, fest, fsup = D.region_matrix(fam, A05_YEARS)
    frate = PER * ftot / pop
    # rangos y estabilidad
    ranks = rate.rank(ascending=False, method="min")
    rho = {}
    base = rate[A05_YEARS[0]]
    for y in A05_YEARS:
        m = base.notna() & rate[y].notna()
        rho[y] = float(stats.spearmanr(base[m], rate[y][m]).statistic) if m.sum() > 2 else np.nan
    # panel estable
    e = D.est[(D.est.code == CFG.STRICT["a05_entry"]) & D.est.year.isin(A05_YEARS)].copy()
    g = e.groupby(["year", "cut_region"]).apply(
        lambda s: pd.Series(dict(total=s.annual_total.sum(min_count=1),
                                 panel_total=s.loc[s.in_stable_panel, "annual_total"].sum(min_count=1),
                                 n_panel=int(s.in_stable_panel.sum()), n_est=int(s.IdEstablecimiento.nunique()))), include_groups=False).reset_index()
    g["share_panel"] = 100 * g.panel_total / g.total
    panel = g.pivot(index="cut_region", columns="year", values="share_panel").reindex(index=tot.index, columns=A05_YEARS)
    nat_panel = e.groupby("year").apply(lambda s: 100 * s.loc[s.in_stable_panel, "annual_total"].sum() / s.annual_total.sum(), include_groups=False)
    # tasa nacional y dispersión
    nat = D.national(strict).set_index("year")
    nat_rate = PER * nat.total / D.pop_nat.reindex(nat.index)
    disp = pd.DataFrame(dict(year=A05_YEARS,
                             national=[float(nat_rate.get(y, np.nan)) for y in A05_YEARS],
                             median=[float(rate[y].median()) for y in A05_YEARS],
                             q1=[float(rate[y].quantile(0.25)) for y in A05_YEARS],
                             q3=[float(rate[y].quantile(0.75)) for y in A05_YEARS],
                             minimum=[float(rate[y].min()) for y in A05_YEARS],
                             maximum=[float(rate[y].max()) for y in A05_YEARS]))
    last = A05_YEARS[-1]
    cat = []
    for r in ftot.index:
        cnt, pp = ftot.loc[r, last], pop.loc[r, last]
        v, lo, hi = rate_ci(cnt, pp)
        cat.append(dict(cut_region=r, count=cnt, population=pp, rate=v, lo=lo, hi=hi, n_est=fest.loc[r, last],
                        suppressed=bool(fsup.loc[r, last])))
    cat = pd.DataFrame(cat).sort_values("rate", ascending=False)
    fam_nat = D.national(fam).set_index("year")
    nat_fam_rate = PER * float(fam_nat.total.get(last, np.nan)) / float(D.pop_nat.get(last, np.nan))
    return dict(tot=tot, est=est, sup=sup, rate=rate, ftot=ftot, fest=fest, fsup=fsup, frate=frate, ranks=ranks, rho=rho,
                panel=panel, nat_panel=nat_panel, disp=disp, cat=cat, nat_rate=nat_rate, nat_fam_rate=nat_fam_rate,
                pop=pop, nat=nat, fam_nat=fam_nat, last=last)


def plate_e13(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e13"]
    rlab = [D.region_name[r] for r in E["tot"].index]
    fig, gs = new_plate()

    # --- A: tasa por 100.000 residentes --------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    heat(ax, E["rate"], rlab, lang, lambda v, lg: num(v, 1, lg), cmap="Blues",
         cbar_label=tr("cb_rate_entries", lang), suppressed=E["sup"])
    long_xlabel(ax, f"{tr('year', lang)} — {tr('ecological', lang)}")
    ax.xaxis.label.set_color("#8a3b12")
    _facet_title(ax, tr("e13_a", lang))
    letter(ax, "a")

    # --- B: establecimientos reportantes -------------------------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    heat(ax, E["est"], rlab, lang, lambda v, lg: num(v, 0, lg), cmap="Greens", cbar_label=tr("cb_estab", lang))
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    _facet_title(ax, tr("e13_b", lang))
    letter(ax, "b")

    # --- C: estabilidad del rango --------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    ranks = E["ranks"]
    # El rótulo de cada región NO hereda el color de su línea: dos colores de la paleta (el amarillo
    # #F0E442 y el celeste claro) son ilegibles como texto sobre blanco. El color queda en la línea y en
    # su marcador; el nombre se imprime en gris oscuro, que se lee siempre.
    for i, r in enumerate(ranks.index):
        ax.plot(A05_YEARS, ranks.loc[r], marker="o", ms=4, lw=1.3, color=OK[i % len(OK)], alpha=0.85)
        if pd.notna(ranks.loc[r, A05_YEARS[-1]]):
            ax.plot([A05_YEARS[-1] + 0.05], [ranks.loc[r, A05_YEARS[-1]]], marker="o", ms=3.4,
                    color=OK[i % len(OK)], clip_on=False)
            ax.text(A05_YEARS[-1] + 0.26, ranks.loc[r, A05_YEARS[-1]],
                    clip_label(C.PLATE_LABEL_GLOSSARY.get(D.region_name[r], D.region_name[r]), 15),
                    fontsize=FS_CELL, va="center", color="#333333")
    ax.invert_yaxis()
    ax.set_xticks(A05_YEARS); ax.set_xlim(A05_YEARS[0] - 0.2, A05_YEARS[-1] + 2.4)
    ax.set_ylabel(tr("rank_axis", lang), fontsize=FS_BASE)
    txt = "; ".join(f"{y}: {num(E['rho'][y], 2, lang)}" for y in A05_YEARS[1:])
    long_xlabel(ax, f"{tr('year', lang)} — {tr('spearman', lang)}: {txt}")
    _facet_title(ax, tr("e13_c", lang))
    letter(ax, "c")

    # --- D: participación del panel estable ----------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    panel = E["panel"]
    for i, r in enumerate(panel.index):
        ax.plot(A05_YEARS, panel.loc[r], marker="o", ms=3, lw=1.0, color=GREY, alpha=0.55)
    ax.plot(A05_YEARS, [100 * 0 + float(E["nat_panel"].get(y, np.nan)) for y in A05_YEARS], marker="s", ms=7, lw=2.6, color=OK[1], label=tr("national", lang))
    for y in A05_YEARS:
        v = float(E["nat_panel"].get(y, np.nan))
        if pd.notna(v):
            value_label(ax, y, v, pct(v, lang), fontsize=FS_ANN, color=OK[1], bbox=dict(VALUE_HALO),
                        prefer=((0, 1),), max_steps=5)
    ax.set_xticks(A05_YEARS)
    ax.set_ylim(0, 105)
    ax.set_ylabel(tr("share_panel", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper right", fontsize=FS_TICK)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('stable_panel_def', lang)}")
    _facet_title(ax, tr("e13_d", lang))
    letter(ax, "d")

    # --- E: tasa regional de la familia TGD en el último año -----------------------------------
    ax = fig.add_subplot(gs[2, 0])
    cat = E["cat"]
    y = np.arange(len(cat))
    ax.errorbar(cat.rate, y, xerr=[cat.rate - cat.lo, cat.hi - cat.rate], fmt="o", ms=6, color=OK[0], ecolor=GREY, elinewidth=1.3, capsize=2.5)
    ax.axvline(E["nat_fam_rate"], color=OK[1], ls="--", lw=1.4, label=f"{tr('national', lang)}: {num(E['nat_fam_rate'], 1, lang)}")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{D.region_name[int(r.cut_region)]} (n={num(r.n_est, 0, lang)})" for r in cat.itertuples()], fontsize=FS_ANN)
    ax.invert_yaxis()
    ax.set_xlabel(f"{tr('u_rate_entries', lang)} — {tr('ci95', lang)}", fontsize=FS_BASE)
    legend_wrapped(ax, loc="lower right", fontsize=FS_TICK)
    _facet_title(ax, f"{tr('e13_e', lang)} ({E['last']}) — {vlabel(variant, lang)}")
    letter(ax, "e")

    # --- F: dispersión de las tasas regionales -------------------------------------------------
    ax = fig.add_subplot(gs[2, 1])
    d = E["disp"]
    ax.fill_between(d.year, d.q1, d.q3, color=OK[0], alpha=0.18, label=tr("median_iqr", lang))
    ax.plot(d.year, d["median"], marker="o", ms=6, lw=2.0, color=OK[0])
    ax.vlines(d.year, d.minimum, d.maximum, color=GREY, lw=1.2, label=tr("range_minmax", lang))
    ax.plot(d.year, d.national, marker="s", ms=6, lw=2.0, color=OK[1], label=tr("national", lang))
    for r in d.itertuples():
        _ann(ax, r.year, r.maximum, num(r.maximum, 0, lang), GREY, fs=FS_CELL, dy=3)
    ax.set_xticks(A05_YEARS)
    ax.set_ylabel(tr("u_rate_entries", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_TICK)
    _facet_title(ax, tr("e13_f", lang))
    letter(ax, "f")

    name = PLATES["E13"]
    title = {"es": f"A05 regional: ingresos a salud mental por autismo por región y año, Chile 2021–2025 — {vlabel(variant, lang)}",
             "en": f"A05 regional: mental-health programme entries for autism by region and year, Chile 2021–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a) Ingresos del código de autismo estricto (05990022) por 100.000 residentes, por región de la unidad que reporta y "
                      "año, con la población INE de residencia (base Censo 2017) como denominador: es una tasa ecológica porque el REM "
                      "localiza al prestador y no la residencia del usuario. (b) Establecimientos que reportan el código en cada región y "
                      "año. (c) Rango de la tasa regional por año (1 = más alta) y ρ de Spearman de cada año frente a 2021. (d) Porcentaje "
                      "de los ingresos aportado por el panel estable de establecimientos (líneas grises: regiones; línea roja: total "
                      "nacional). (e) Tasa regional de la familia TGD de la variante en el último año, con intervalos exactos de Poisson y "
                      "el número de establecimientos reportantes. (f) Dispersión de las tasas regionales: mediana con rango intercuartílico, "
                      "mínimo–máximo y tasa nacional. Celdas grises: la región no presentó ninguna fila del código ese año; «<5»: celda "
                      "suprimida por tener menos de cinco eventos."),
               "en": ("(a) Entries under the strict autism code (05990022) per 100,000 residents, by region of the reporting unit and year, "
                      "using the INE residence population (Census 2017 base) as denominator: this is an ecological rate because REM locates "
                      "the provider and not the user's residence. (b) Establishments reporting the code in each region and year. (c) Rank of "
                      "the regional rate by year (1 = highest) and the Spearman ρ of each year against 2021. (d) Percentage of entries "
                      "contributed by the stable establishment panel (grey lines: regions; red line: national total). (e) Regional rate of the "
                      "variant PDD family in the last year, with exact Poisson intervals and the number of reporting establishments. "
                      "(f) Dispersion of the regional rates: median with interquartile range, minimum–maximum and the national rate. Grey "
                      "cells: the region filed no row for that code that year; '<5': cell suppressed because it holds fewer than five events.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    rows = []
    for r in E["tot"].index:
        rec = {tr("region", lang): D.region_name[r]}
        for y in A05_YEARS:
            rec[str(y)] = (tr("not_reported", lang) if pd.isna(E["tot"].loc[r, y]) else
                           (f"{tr('suppressed', lang)} ({num(E['est'].loc[r, y], 0, lang)})" if E["sup"].loc[r, y] else
                            f"{num(E['tot'].loc[r, y], 0, lang)} / {num(E['rate'].loc[r, y], 1, lang)} ({num(E['est'].loc[r, y], 0, lang)})"))
        rec[f"{tr('share_panel', lang)} ({A05_YEARS[-1]})"] = pct(E["panel"].loc[r, A05_YEARS[-1]], lang)
        rows.append(rec)
    nat = E["nat"]
    rec = {tr("region", lang): tr("national", lang)}
    for y in A05_YEARS:
        rec[str(y)] = f"{num(nat.total.get(y), 0, lang)} / {num(E['nat_rate'].get(y), 1, lang)} ({num(nat.n_est.get(y), 0, lang)})"
    rec[f"{tr('share_panel', lang)} ({A05_YEARS[-1]})"] = pct(E["nat_panel"].get(A05_YEARS[-1]), lang)
    rows.append(rec)
    formatted = pd.DataFrame(rows)
    numeric = []
    for r in E["tot"].index:
        for y in A05_YEARS:
            numeric.append(dict(cut_region=r, region=D.region_name[r], year=y, code=CFG.STRICT["a05_entry"],
                                entries=E["tot"].loc[r, y], population=E["pop"].loc[r, y], rate_per_100k=E["rate"].loc[r, y],
                                n_reporting_establishments=E["est"].loc[r, y], suppressed=bool(E["sup"].loc[r, y]),
                                rank=E["ranks"].loc[r, y], share_from_stable_panel_pct=E["panel"].loc[r, y],
                                family_code="+".join(CFG.VARIANTS[variant]["a05_entry"]), family_entries=E["ftot"].loc[r, y],
                                family_rate_per_100k=E["frate"].loc[r, y], family_n_establishments=E["fest"].loc[r, y]))
    numeric = pd.DataFrame(numeric)
    numeric["variant"] = variant
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "ingresos reportados (flujo anual, suma de meses de COL01)", "en": "entries reported (annual flow, sum of months of COL01)"}[lang],
                 denominator={"es": "población residente INE por región (proyecciones base Censo 2017, 30 de junio); tasa ecológica", "en": "INE resident population by region (Census 2017 base projections, 30 June); ecological rate"}[lang],
                 coverage={"es": "red pública que reporta el código A05; la región es la de la unidad que reporta, no la residencia del usuario", "en": "public network reporting the A05 code; the region is that of the reporting unit, not the user's residence"}[lang],
                 era={"es": "autismo estricto 05990022 y familia TGD de la variante, 2021–2025 (los códigos amplios 2019–2020 son otra definición y no se incluyen aquí)",
                      "en": "strict autism 05990022 and the variant PDD family, 2021–2025 (the broad 2019–2020 codes are a different definition and are not included here)"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con al menos una fila del código en la región y el año", "en": "n in brackets = establishments with at least one row for the code in the region and year"}[lang],
                 sources=f"{SRC_A}; {SRC_INE[lang]}; {SRC_TIDY}",
                 extra=NOTE_SUPPRESSION[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E14 · A05 edad y sexo
# ===========================================================================
SEXMAP = {"Hombres": "HOMBRE", "Mujeres": "MUJER"}


def _age_matrix(age: pd.DataFrame, code: str, flow: str, variant: str | None = None) -> pd.DataFrame:
    s = age[(age.code == code) & (age.flow == flow) & (age.age_group != "total")]
    if variant is not None:
        s = s[s.variant == variant]
    return s.pivot_table(index="age_group", columns=["year", "sex"], values="count", aggfunc="sum").reindex(AGE_GROUPS)


def prep_e14(D: Data, variant: str) -> dict:
    strict_code = CFG.STRICT["a05_entry"]
    fam_code = "+".join(CFG.VARIANTS[variant]["a05_entry"])
    strict = _age_matrix(D.age, strict_code, "entry", "single_code")
    fam = _age_matrix(D.age, fam_code, "entry", variant)
    est = (D.age[(D.age.code == strict_code) & (D.age.flow == "entry")].groupby("year").n_reporting_establishments.max())
    est_fam = (D.age[(D.age.code == fam_code) & (D.age.flow == "entry")].groupby("year").n_reporting_establishments.max())
    pop = D.pop_nat_sex_age
    rates = []
    for series, mat, code in (("strict", strict, strict_code), ("family", fam, fam_code)):
        for y in A05_YEARS:
            for sx_es, sx_ine in SEXMAP.items():
                if (y, sx_es) not in mat.columns:
                    continue
                cnt = mat[(y, sx_es)]
                pp = pop[(pop.year == y) & (pop.sex == sx_ine)][["age_group", "population"]]
                frame = pd.DataFrame({"age_group": AGE_GROUPS, "count": cnt.reindex(AGE_GROUPS).values}).merge(pp, on="age_group", how="left")
                total = float(np.nansum(frame["count"]))
                popn = float(frame.population.sum())
                cr, cl, ch = rate_ci(total, popn)
                std = direct_standardization(frame.fillna({"count": 0.0}), count="count", population="population", age="age_group")
                rates.append(dict(series=series, code=code, year=y, sex=sx_ine, count=total, population=popn,
                                  crude=cr, crude_lo=cl, crude_hi=ch, asr=std["asr"], asr_lo=std["asr_lo"], asr_hi=std["asr_hi"],
                                  asr_var=std["asr_var"], n_reporting_establishments=int((est if series == "strict" else est_fam).get(y, 0))))
    rates = pd.DataFrame(rates)
    mf = []
    for series, mat in (("strict", strict), ("family", fam)):
        for y in A05_YEARS:
            for a in AGE_GROUPS:
                m = mat[(y, "Hombres")].get(a, np.nan) if (y, "Hombres") in mat.columns else np.nan
                f = mat[(y, "Mujeres")].get(a, np.nan) if (y, "Mujeres") in mat.columns else np.nan
                r, lo, hi = count_ratio(0 if pd.isna(m) else float(m), 0 if pd.isna(f) else float(f))
                mf.append(dict(series=series, year=y, age_group=a, males=m, females=f, ratio=r, lo=lo, hi=hi))
    mf = pd.DataFrame(mf)
    comp = {}
    for series, mat in (("strict", strict), ("family", fam)):
        both = pd.DataFrame({y: mat[[c for c in mat.columns if c[0] == y]].sum(axis=1, min_count=1) for y in A05_YEARS})
        comp[series] = 100 * both / both.sum()
        comp[series + "_counts"] = both
    return dict(strict=strict, fam=fam, rates=rates, mf=mf, comp=comp, est=est, est_fam=est_fam,
                strict_code=strict_code, fam_code=fam_code)


#: Sólo se rotulan los grupos de edad que llegan a este porcentaje. Los rótulos van GIRADOS 90° y su caja
#: mide más de un grupo de ancho, mientras que dos barras vecinas distan 0,4 grupos: con el umbral en 1 %
#: se escribían veinte rótulos en dieciocho grupos y, en la cola, la caja de uno caía sobre la barra del
#: vecino. En español, «1,4» tapaba el 54 % de la barra naranja de 20-24, que se imprimía como 2,8 en vez
#: de 4,0. Con el umbral en 5 % quedan rotulados los cuatro grupos que concentran los ingresos —que es lo
#: que el panel cuenta— y las cajas ya no se tocan; la cola, por debajo del 5 %, se lee en el eje, y la
#: tabla numérica acompañante conserva TODOS los grupos con su valor exacto. La lámina abrevia, no oculta.
COMP_LABEL_MIN_PCT = 5.0


def plate_e14(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e14"]
    fig, gs = new_plate()
    x = np.arange(len(AGE_GROUPS))

    # --- A y B: ingresos por edad y año, por sexo ----------------------------------------------
    for k, (sx, key, ttl) in enumerate([("Hombres", "e14_a", tr("sex_m", lang)), ("Mujeres", "e14_b", tr("sex_f", lang))]):
        ax = fig.add_subplot(gs[0, k] if k < 2 else gs[1, 0])
        for y in A05_YEARS:
            if (y, sx) not in E["strict"].columns:
                continue
            v = E["strict"][(y, sx)].reindex(AGE_GROUPS).to_numpy(dtype=float)
            ax.plot(x, np.where(v > 0, v, np.nan), marker="o", ms=4.5, lw=1.7, color=YEARCOL[y],
                    label=f"{y} (n={num(E['est'].get(y, np.nan), 0, lang)})")
        ax.set_yscale("log")
        age_ticks(ax, AGE_GROUPS)
        ax.set_xlabel(tr("age_axis", lang), fontsize=FS_BASE)
        ax.set_ylabel(f"{tr('u_entries', lang)} {tr('log_scale', lang)}", fontsize=FS_BASE)
        legend_wrapped(ax, loc="upper right", fontsize=FS_ANN, title=tr("n_estab", lang), title_fontsize=FS_CELL)
        _facet_title(ax, f"{tr(key, lang)}")
        letter(ax, PLATE_LETTERS[k])

    # --- C: tasas bruta y estandarizada por sexo -----------------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    r = E["rates"][E["rates"].series == "strict"]
    for sx, col, lab in (("HOMBRE", OK[0], tr("sex_m", lang)), ("MUJER", OK[1], tr("sex_f", lang))):
        s = r[r.sex == sx].sort_values("year")
        ax.plot(s.year, s.crude, marker="o", ms=5, lw=1.5, ls="--", color=col, alpha=0.7, label=f"{lab} — {tr('crude', lang)}")
        ax.errorbar(s.year, s.asr, yerr=[s.asr - s.asr_lo, s.asr_hi - s.asr], fmt="s", ms=7, lw=2.2, color=col,
                    ecolor=col, elinewidth=1.3, capsize=3, label=f"{lab} — {tr('asr', lang)}")
        for t in s.itertuples():
            _ann(ax, t.year, t.asr_hi, num(t.asr, 1, lang), col, fs=FS_ANN, dy=4)
    ax.set_xticks(A05_YEARS)
    ax.set_ylabel(f"{tr('u_rate_entries', lang)}", fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_ANN, ncol=2)
    _facet_title(ax, tr("e14_c", lang))
    letter(ax, "c")

    # --- D: razón hombre:mujer por edad --------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    mf = E["mf"][(E["mf"].series == "strict") & E["mf"].year.isin([A05_YEARS[0], A05_YEARS[-1]])]
    for k, y in enumerate([A05_YEARS[0], A05_YEARS[-1]]):
        s = mf[mf.year == y].set_index("age_group").reindex(AGE_GROUPS)
        # una razón de cero (ningún registro masculino) es un valor real pero no tiene lugar en un eje logarítmico:
        # se deja en blanco en la lámina y se conserva en la tabla numérica, nunca se dibuja como barra sin punto.
        ok = s.ratio.notna() & (s.ratio > 0) & np.isfinite(s.hi)
        xx = x[ok.to_numpy()] + (-0.14 + 0.28 * k)
        ax.errorbar(xx, s.ratio[ok], yerr=[(s.ratio - s.lo)[ok], (s.hi - s.ratio)[ok]], fmt="o", ms=5,
                    color=YEARCOL[y], ecolor=YEARCOL[y], elinewidth=1.1, capsize=2, label=str(y))
    ax.axhline(1.0, color=GREY, ls=":", lw=1.2)
    ax.set_yscale("log")
    age_ticks(ax, AGE_GROUPS)
    ax.set_xlabel(tr("age_axis", lang), fontsize=FS_BASE)
    ax.set_ylabel(f"{tr('mf_ratio', lang)} {tr('log_scale', lang)}", fontsize=FS_BASE)
    legend_wrapped(ax, loc="lower left", fontsize=FS_TICK)
    _facet_title(ax, tr("e14_d", lang))
    letter(ax, "d")

    # --- E: composición etaria 2021 y 2025 -----------------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    comp = E["comp"]["strict"]
    for k, y in enumerate([A05_YEARS[0], A05_YEARS[-1]]):
        v = comp[y].reindex(AGE_GROUPS).to_numpy(dtype=float)
        ax.bar(x + (-0.2 + 0.4 * k), v, width=0.38, color=YEARCOL[y], label=str(y))
        for xi, vi in zip(x + (-0.2 + 0.4 * k), v):
            if pd.notna(vi) and vi >= COMP_LABEL_MIN_PCT:
                _ann(ax, xi, vi, num(vi, 1, lang), DARK, fs=FS_CELL, dy=2, rotation=90)
    age_ticks(ax, AGE_GROUPS)
    ax.set_xlabel(tr("age_axis", lang), fontsize=FS_BASE)
    ax.set_ylabel(tr("age_composition", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper right", fontsize=FS_TICK)
    _facet_title(ax, tr("e14_e", lang))
    letter(ax, "e")

    # --- F: familia frente a autismo estricto por edad -----------------------------------------
    ax = fig.add_subplot(gs[2, 1])
    last = A05_YEARS[-1]
    sv = E["comp"]["strict_counts"][last].reindex(AGE_GROUPS).to_numpy(dtype=float)
    fv = E["comp"]["family_counts"][last].reindex(AGE_GROUPS).to_numpy(dtype=float)
    ax.bar(x - 0.2, sv, width=0.38, color=OK[0], label=f"{tr('strict_short', lang)} (n={num(E['est'].get(last, np.nan), 0, lang)})")
    ax.bar(x + 0.2, fv, width=0.38, color=OK[2], label=f"{tr('family_short', lang)} (n={num(E['est_fam'].get(last, np.nan), 0, lang)})")
    for xi, s_, f_ in zip(x, sv, fv):
        if pd.notna(f_) and pd.notna(s_) and f_ > 0:
            _ann(ax, xi + 0.2, f_, f"+{num(f_ - s_, 0, lang)}", OK[2], fs=FS_CELL, dy=2)
    age_ticks(ax, AGE_GROUPS)
    ax.set_xlabel(tr("age_axis", lang), fontsize=FS_BASE)
    ax.set_ylabel(tr("u_entries", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper right", fontsize=FS_TICK)
    _facet_title(ax, f"{tr('e14_f', lang)} ({last})")
    letter(ax, "f")

    name = PLATES["E14"]
    title = {"es": f"A05 por edad y sexo: ingresos por autismo en 17 grupos etarios de la OMS, tasas estandarizadas y razón hombre:mujer, Chile 2021–2025 — {vlabel(variant, lang)}",
             "en": f"A05 by age and sex: autism entries in 17 WHO age groups, standardised rates and male-to-female ratio, Chile 2021–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a, b) Ingresos del código de autismo estricto (05990022) por los 17 grupos etarios quinquenales de la OMS y año, en "
                      "hombres y mujeres, en escala logarítmica; las celdas de edad × sexo son las columnas COL04–COL37 del REM. (c) Tasa "
                      "bruta (línea discontinua) y tasa estandarizada por edad con la población estándar de la OMS (marcadores cuadrados, "
                      "límites de Fay–Feuer) por sexo, con la población residente INE por sexo y edad como denominador. (d) Razón "
                      "hombre:mujer de los ingresos por grupo de edad en el primer y el último año, con límites exactos; la razón es de "
                      "registros, no de tasas, y no describe personas. En A, B y D el eje logarítmico no admite el cero: un grupo de edad "
                      "con cero registros (o con razón cero por no haber registros masculinos) queda en blanco, lo que no equivale a "
                      "ausencia de reporte; la tabla numérica conserva todos los ceros. (e) Composición etaria de los ingresos del año, en porcentaje; "
                      "se rotulan los grupos que llegan al 5 % —los rótulos van girados y sus cajas no caben juntas en la cola— y la tabla "
                      "numérica acompañante conserva el valor de los 17 grupos. "
                      "(f) Familia TGD de la variante frente al autismo estricto por edad en el último año; la diferencia rotulada es el "
                      "aporte de las demás categorías del grupo. n = establecimientos que reportan el código en el año."),
               "en": ("(a, b) Entries under the strict autism code (05990022) by the 17 five-year WHO age groups and year, in males and "
                      "females, on a logarithmic scale; the age × sex cells are REM columns COL04–COL37. (c) Crude rate (dashed line) and "
                      "age-standardised rate with the WHO standard population (square markers, Fay–Feuer limits) by sex, with the INE "
                      "resident population by sex and age as denominator. (d) Male-to-female ratio of entries by age group in the first and "
                      "last year, with exact limits; the ratio is of records, not of rates, and does not describe persons. In A, B and D the "
                      "logarithmic axis cannot hold a zero: an age group with zero records (or a ratio of zero because there is no male "
                      "record) is left blank, which is not the same as absence of reporting; the numeric companion keeps every zero. (e) Age composition "
                      "of the year's entries, in per cent; groups reaching 5% are labelled —the labels are rotated and their boxes do not "
                      "fit side by side in the tail— and the numeric companion keeps the value of all 17 groups. "
                      "(f) Variant PDD family against strict autism by age in the last year; the labelled "
                      "difference is the contribution of the remaining categories of the group. n = establishments reporting the code in the year.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    rows = []
    for a in AGE_GROUPS:
        for sx in ("Hombres", "Mujeres"):
            rec = {tr("age_axis", lang): a, LBL["t_series"][lang]: tr("sex_m", lang) if sx == "Hombres" else tr("sex_f", lang)}
            for y in A05_YEARS:
                v = E["strict"][(y, sx)].get(a, np.nan) if (y, sx) in E["strict"].columns else np.nan
                rec[str(y)] = num(v, 0, lang)
            rows.append(rec)
    for sx_ine, lab in (("HOMBRE", tr("sex_m", lang)), ("MUJER", tr("sex_f", lang))):
        s = E["rates"][(E["rates"].series == "strict") & (E["rates"].sex == sx_ine)].set_index("year")
        for field, flab in (("crude", tr("crude", lang)), ("asr", tr("asr", lang))):
            rec = {tr("age_axis", lang): f"{tr('u_rate_entries', lang)} — {flab}", LBL["t_series"][lang]: lab}
            for y in A05_YEARS:
                rec[str(y)] = (f"{num(s[field].get(y), 1, lang)} ({ci(s[f'{field}_lo'].get(y), s[f'{field}_hi'].get(y), 1, lang)})"
                               if y in s.index else tr("outside_era", lang))
            rows.append(rec)
    rec = {tr("age_axis", lang): tr("estab_short", lang), LBL["t_series"][lang]: tr("strict_short", lang)}
    for y in A05_YEARS:
        rec[str(y)] = num(E["est"].get(y, np.nan), 0, lang)
    rows.append(rec)
    formatted = pd.DataFrame(rows)
    long = []
    for series, mat in (("strict", E["strict"]), ("family", E["fam"])):
        for (y, sx) in mat.columns:
            for a in AGE_GROUPS:
                long.append(dict(series=series, variant=variant, year=y, sex=SEXMAP[sx], age_group=a, count=mat[(y, sx)].get(a, np.nan)))
    numeric = pd.concat([pd.DataFrame(long), E["rates"].assign(block="rates"), E["mf"].assign(block="male_female_ratio")], ignore_index=True)
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "ingresos reportados (flujo anual); celdas de edad × sexo COL04–COL37 y totales por sexo COL02/COL03", "en": "entries reported (annual flow); age × sex cells COL04–COL37 and sex totals COL02/COL03"}[lang],
                 denominator={"es": "población residente INE por sexo y grupo de edad (base Censo 2017) para las tasas; estándar OMS para la estandarización directa", "en": "INE resident population by sex and age group (Census 2017 base) for the rates; WHO standard for the direct standardisation"}[lang],
                 coverage={"es": "red pública que reporta el código A05", "en": "public network reporting the A05 code"}[lang],
                 era={"es": "autismo estricto 05990022 y familia TGD de la variante, 2021–2025", "en": "strict autism 05990022 and the variant PDD family, 2021–2025"}[lang],
                 reporting={"es": "establecimientos que reportan el código en el año (fila final)", "en": "establishments reporting the code in the year (last row)"}[lang],
                 sources=f"{SRC_A}; {SRC_INE[lang]}; outputs/tidy/rem_a05_age_sex_annual.csv",
                 extra={"es": "La razón hombre:mujer del archivo numérico es una razón de registros con límites exactos, no una razón de tasas.",
                        "en": "The male-to-female ratio in the numeric companion is a ratio of records with exact limits, not a ratio of rates."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E15 · P2 y P6 en detalle (stocks semestrales)
# ===========================================================================
STOCK_YEARS = list(range(2019, 2026))
P6_ERA1 = [2019, 2020]
P6_ERA2 = [2021, 2022, 2023, 2024, 2025]


def prep_e15(D: Data, variant: str) -> dict:
    p2 = [CFG.P2_TEA]
    tot, est, sup = D.region_matrix(p2, STOCK_YEARS, month=12)
    pop = D.pop_reg.reindex(index=tot.index, columns=STOCK_YEARS)
    rate = PER * tot / pop
    series = {}
    defs = {
        "p2": dict(codes=[CFG.P2_TEA], years=STOCK_YEARS, label="p2_short"),
        "p6p_broad": dict(codes=[CFG.P6_BROAD_PRE2021["primary"]], years=P6_ERA1, label="p6p_short"),
        "p6s_broad": dict(codes=[CFG.P6_BROAD_PRE2021["specialty"]], years=P6_ERA1, label="p6s_short"),
        "p6p_strict": dict(codes=[CFG.STRICT["p6_primary"]], years=P6_ERA2, label="p6p_short"),
        "p6s_strict": dict(codes=[CFG.STRICT["p6_specialty"]], years=P6_ERA2, label="p6s_short"),
        "p6p_family": dict(codes=list(CFG.VARIANTS[variant]["p6_primary"]), years=P6_ERA2, label="p6p_short"),
        "p6s_family": dict(codes=list(CFG.VARIANTS[variant]["p6_specialty"]), years=P6_ERA2, label="p6s_short"),
        "naneas": dict(codes=[CFG.P2_NANEAS_TOTAL], years=[2023, 2024, 2025], label="p2_short"),
    }
    for key, spec in defs.items():
        dec = D.national(spec["codes"], month=12).set_index("year").reindex(spec["years"])
        jun = D.national(spec["codes"], month=6).set_index("year").reindex(spec["years"])
        series[key] = pd.DataFrame(dict(year=spec["years"],
                                        december=dec.total.values, dec_est=dec.n_est.values,
                                        june=jun.total.values, jun_est=jun.n_est.values))
        series[key]["per_establishment"] = series[key].december / series[key].dec_est
        series[key]["june_december_ratio"] = series[key].june / series[key].december
        series[key]["codes"] = "+".join(spec["codes"])
    naneas = []
    for y in (2023, 2024, 2025):
        a = float(series["p2"].set_index("year").december.get(y, np.nan))
        b = float(series["naneas"].set_index("year").december.get(y, np.nan))
        p, lo, hi = C.wilson(a, b) if b and b > 0 else (np.nan, np.nan, np.nan)
        naneas.append(dict(year=y, asd=a, naneas_total=b, per100=100 * p, lo=100 * lo, hi=100 * hi,
                           n_est_asd=float(series["p2"].set_index("year").dec_est.get(y, np.nan)),
                           n_est_naneas=float(series["naneas"].set_index("year").dec_est.get(y, np.nan))))
    naneas = pd.DataFrame(naneas)
    last = STOCK_YEARS[-1]
    reg6 = {}
    for key, codes in (("primary", [CFG.STRICT["p6_primary"]]), ("specialty", [CFG.STRICT["p6_specialty"]])):
        t, e, s_ = D.region_matrix(codes, [last], month=12)
        reg6[key] = pd.DataFrame(dict(cut_region=t.index, total=t[last].values, n_est=e[last].values,
                                      suppressed=s_[last].values,
                                      rate=PER * t[last].values / D.pop_reg.reindex(t.index)[last].values))
    return dict(tot=tot, est=est, sup=sup, rate=rate, pop=pop, series=series, naneas=naneas,
                reg6=reg6, last=last)


def plate_e15(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e15"]
    S = E["series"]
    rlab = [D.region_name[r] for r in E["tot"].index]
    fig, gs = new_plate()

    # --- A: P2 diciembre por región y año, por 100.000 residentes -------------------------------
    ax = fig.add_subplot(gs[0, 0])
    heat(ax, E["rate"], rlab, lang, lambda v, lg: num(v, 1, lg), cmap="Purples",
         cbar_label=tr("cb_rate_stock", lang), suppressed=E["sup"])
    long_xlabel(ax, f"{tr('year', lang)} — {tr('ecological', lang)}")
    ax.xaxis.label.set_color("#8a3b12")
    _facet_title(ax, tr("e15_a", lang))
    letter(ax, "a")

    # --- B: junio frente a diciembre -----------------------------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    trio = [("p2", OK[0], tr("p2_short", lang), STOCK_YEARS),
            ("p6p_strict", OK[2], tr("p6p_short", lang), P6_ERA2),
            ("p6s_strict", OK[1], tr("p6s_short", lang), P6_ERA2)]
    w = 0.26
    # La leyenda llevaba «serie — diciembre» y «serie — junio»: seis rótulos largos que ocupaban media celda
    # y empujaban la marca de la Ley al centro del panel, encima de las barras. El color identifica la serie
    # y la FORMA el semestre (barra llena = diciembre, marcador hueco = junio); la equivalencia va bajo el
    # eje, donde no puede tapar un dato.
    for k, (key, col, lab, yrs) in enumerate(trio):
        s = S[key]
        xx = s.year.to_numpy(dtype=float) + (-w + w * k)
        ax.bar(xx, s.december, width=w * 0.92, color=col, label=lab)
        ax.plot(xx, s.june, ls="none", marker="o", ms=6, mfc="white", mec=col, mew=1.6)
    ax.set_xticks(STOCK_YEARS)
    ax.set_ylabel(tr("u_stock_dec", lang), fontsize=FS_BASE)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('dec_bars_jun_marks', lang)} — {tr('n_rows', lang)}")
    ax.set_ylim(0, float(np.nanmax(S["p2"].december)) * 1.30)
    _context(ax, lang, pandemic_text=False, law_pos=0.985, law_va="top")
    _break_marker(ax, 2020.5, lang, y=0.30)
    legend_wrapped(ax, loc="upper left", width=16, fontsize=FS_ANN).set_gid(C.PLATE_KEEP)
    # Los «n=» de las tres series de un año arrancan TODOS a la altura del elemento más alto de ese año
    # (barra de diciembre o marcador de junio): forman una fila ordenada por encima de todo el grupo, cada
    # uno sobre su propia barra. Pegados a su barra, el marcador hueco de junio y el recuadro del rótulo
    # vecino se comían la primera cifra —«=1.218» en lugar de «n=1.218»— y colocados de uno en uno
    # quedaban a alturas distintas, lo que rompía la correspondencia con la barra.
    n_strip(ax, [(col, [(t.year + (-w + w * k), t.dec_est) for t in S[key].itertuples()])
                 for k, (key, col, lab, yrs) in enumerate(trio)], lang)
    _facet_title(ax, tr("e15_b", lang))
    letter(ax, "b")

    # --- C: stock por establecimiento reportante -----------------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    ax.plot(S["p2"].year, S["p2"].per_establishment, marker="o", ms=6, lw=2.0, color=OK[0], label=tr("p2_short", lang))
    for key, col, lab, ls in (("p6p_broad", OK[2], tr("p6p_short", lang), "--"), ("p6p_strict", OK[2], tr("p6p_short", lang), "-"),
                              ("p6s_broad", OK[1], tr("p6s_short", lang), "--"), ("p6s_strict", OK[1], tr("p6s_short", lang), "-")):
        s = S[key]
        ax.plot(s.year, s.per_establishment, marker="s" if ls == "-" else "^", ms=5.5, lw=2.0, ls=ls, color=col)
    ax.set_xticks(STOCK_YEARS)
    ax.set_ylabel(tr("u_per_estab", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    # La leyenda de cinco entradas y la marca de la Ley se escribían a media altura, sobre la serie de
    # especialidad (que tapaban en un 42 %). Con cielo reservado las dos viven por encima de todas las
    # series y ninguna cruza un dato.
    headroom(ax, 0.62)
    _context(ax, lang, pandemic_text=False, law_pos=0.995, law_va="top")
    _break_marker(ax, 2020.5, lang, y=0.20)
    # Cinco rótulos de dos conceptos («serie — era») ocupaban media celda de alto y de ancho y caían sobre
    # la serie de especialidad. El color codifica la SERIE y el trazo la ERA: cinco entradas cortas.
    from matplotlib.lines import Line2D as _LD
    hs_c = [_LD([], [], color=OK[0], marker="o", ms=6, lw=2.0),
            _LD([], [], color=OK[2], marker="s", ms=5.5, lw=2.0),
            _LD([], [], color=OK[1], marker="s", ms=5.5, lw=2.0),
            _LD([], [], color=GREY, marker="^", ms=5.5, lw=2.0, ls="--"),
            _LD([], [], color=GREY, marker="s", ms=5.5, lw=2.0, ls="-")]
    ls_c = [tr("p2_short", lang), tr("p6p_short", lang), tr("p6s_short", lang),
            tr("broad_short", lang), tr("strict_short", lang)]
    legend_wrapped(ax, hs_c, ls_c, loc="upper left", expand=False, width=18, ncol=1,
                   fontsize=FS_CELL).set_gid(C.PLATE_KEEP)
    _facet_title(ax, tr("e15_c", lang))
    letter(ax, "c")

    # --- D: P2 sobre el total NANEAS -----------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    n = E["naneas"]
    x = n.year.to_numpy(dtype=float)
    ax.bar(x - 0.18, n.naneas_total, width=0.34, color=LIGHT, label=f"NANEAS (P2501878)")
    ax.bar(x + 0.18, n.asd, width=0.34, color=OK[0], label=f"{tr('p2_short', lang)} (P2500500)")
    for t in n.itertuples():
        # El rombo rosa del eje derecho caía justo sobre el «n=» de la barra NANEAS y se comía sus últimas
        # cifras en 2023. Colocados al final y medidos, los rótulos se apartan del rombo y de su intervalo.
        value_label(ax, t.year - 0.18, t.naneas_total, f"n={num(t.n_est_naneas, 0, lang)}", fontsize=FS_CELL,
                    color=DARK, bbox=dict(VALUE_HALO), prefer=((0, 1),), max_steps=6)
        value_label(ax, t.year + 0.18, t.asd, f"n={num(t.n_est_asd, 0, lang)}", fontsize=FS_CELL,
                    color=DARK, bbox=dict(VALUE_HALO), prefer=((0, 1),), max_steps=6)
    ax.set_xticks(x); ax.set_xlim(2022.5, 2025.5)
    ax.set_ylim(0, float(n.naneas_total.max()) * 1.35)
    ax.set_ylabel(tr("u_stock_dec", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_TICK)
    ax2 = ax.twinx()
    ax2.errorbar(x, n.per100, yerr=[n.per100 - n.lo, n.hi - n.per100], fmt="D", ms=7, color=OK[3], ecolor=OK[3], elinewidth=1.4, capsize=3)
    for t in n.itertuples():
        value_label(ax2, t.year, t.per100, pct(t.per100, lang), fontsize=FS_ANN, color=OK[3],
                    err=(t.lo, t.hi), bbox=dict(VALUE_HALO))
    ax2.set_ylim(0, max(40.0, float(n.hi.max()) * 1.7)); ax2.grid(False)
    ax2.set_ylabel(tr("per100_naneas", lang), fontsize=FS_TICK, color=OK[3])
    _facet_title(ax, tr("e15_d", lang))
    letter(ax, "d")

    # --- E: P6 APS y especialidad, las dos eras en una celda entera -----------------------------
    # Antes eran dos facetas apiladas dentro de media celda: los rótulos «n=» girados de las cuatro series
    # se imprimían unos sobre otros en los cinco grupos de años, la leyenda de cuatro entradas caía sobre
    # las barras y su columna derecha se cortaba contra el borde. Con la celda entera cada barra tiene el
    # ancho que necesita; el número de establecimientos por año, que era lo que multiplicaba los rótulos,
    # pasa a una nota con su rango por serie y sigue año a año en la tabla acompañante. Las dos eras
    # comparten eje pero NO se unen ni se suman: el quiebre de definición va marcado entre ellas.
    ax = fig.add_subplot(gs[2, 0])
    era_keys = [("p6p_broad", "p6p_strict", OK[2], tr("primary", lang)),
                ("p6s_broad", "p6s_strict", OK[1], tr("specialty", lang)),
                (None, "p6p_family", OK[4], f"{tr('primary', lang)} — {tr('family_short', lang)}"),
                (None, "p6s_family", OK[3], f"{tr('specialty', lang)} — {tr('family_short', lang)}")]
    w = 0.8 / len(era_keys)
    rng = []
    for j, (k_broad, k_strict, col, lab) in enumerate(era_keys):
        off = (j - (len(era_keys) - 1) / 2) * w
        seen = []
        for k_, hatch in ((k_broad, "//"), (k_strict, None)):
            if k_ is None:
                continue
            sr = S[k_]
            ax.bar(sr.year.to_numpy(dtype=float) + off, sr.december, width=w * 0.9, color=col,
                   hatch=hatch, edgecolor="white" if hatch else "none", linewidth=0.4,
                   label=None)
            seen.extend(sr.dec_est.dropna().tolist())
        # El rango de establecimientos de cada serie viaja EN SU ENTRADA DE LEYENDA: como nota dentro del
        # panel tapaba el 13 % de una barra y como rótulo del eje X ocupaba cinco líneas y aplastaba el
        # panel. El detalle año a año sigue en la tabla acompañante.
        rng.append(f"{lab} (n = {num(min(seen), 0, lang)}–{num(max(seen), 0, lang)})" if seen else lab)
        ax.bar([np.nan], [np.nan], color=col, label=rng[-1])
    ax.set_xticks(list(STOCK_YEARS))
    ax.set_xticklabels([str(y) for y in STOCK_YEARS])
    ax.set_ylim(0, float(np.nanmax([S[k2].december.max() for _, k2, _, _ in era_keys])) * 1.42)
    ax.set_ylabel(wrap_measured(tr("u_stock_dec", lang), 96.0, FS_BASE, "normal"), fontsize=FS_BASE)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('n_estab', lang)}")
    _context(ax, lang, law=False, pandemic_pos=0.99, pandemic_text=False)
    _break_marker(ax, 2020.5, lang, y=0.30)
    legend_wrapped(ax, loc="upper left", ncol=1, width=26, fontsize=FS_CELL,
                   title=tr("e15_e_hatch", lang), title_fontsize=FS_CELL)
    _facet_title(ax, tr("e15_e", lang))
    letter(ax, "e")

    # --- F: P6 por región en el último año, en mancuerna ---------------------------------------
    # Barras pareadas por región dejaban los dos rótulos «tasa (n=…)» a menos de 5 pt uno del otro y
    # colisionaban en quince de las dieciséis regiones. En mancuerna hay una fila por región —el paso se
    # duplica— y los dos valores se escriben en los EXTREMOS de la línea, a x distintas por construcción.
    ax = fig.add_subplot(gs[2, 1])
    pr, sp = E["reg6"]["primary"], E["reg6"]["specialty"]
    order = pr.sort_values("rate", ascending=False).cut_region.tolist()
    pr = pr.set_index("cut_region").reindex(order)
    sp = sp.set_index("cut_region").reindex(order)
    y = np.arange(len(order))
    for i, (a, b) in enumerate(zip(pr.itertuples(), sp.itertuples())):
        ra = np.nan if a.suppressed else a.rate
        rb = np.nan if b.suppressed else b.rate
        if pd.notna(ra) and pd.notna(rb):
            ax.plot([ra, rb], [i, i], color="#b8b8b8", lw=1.1, zorder=1)
        for v, col in ((ra, OK[2]), (rb, OK[1])):
            if pd.notna(v):
                ax.scatter(v, i, s=26, color=col, zorder=3, edgecolor="white", linewidth=0.5)
        pair = [v for v in (ra, rb) if pd.notna(v)]
        if pair:
            lo_, hi_ = min(pair), max(pair)
            ax.text(lo_, i, f"{num(lo_, 0, lang)} ", va="center", ha="right", fontsize=FS_CELL, color=DARK)
            if hi_ != lo_:
                ax.text(hi_, i, f" {num(hi_, 0, lang)}", va="center", ha="left", fontsize=FS_CELL, color=DARK)
    ax.scatter([], [], s=26, color=OK[2], label=f"{tr('primary', lang)} (P6241010)")
    ax.scatter([], [], s=26, color=OK[1], label=f"{tr('specialty', lang)} (P6241060)")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{D.region_name[int(r)]} ({num(pe, 0, lang)}/{num(se, 0, lang)})"
                        for r, pe, se in zip(order, pr.n_est, sp.n_est)], fontsize=FS_ANN)
    ax.invert_yaxis()
    ax.set_xlabel(tr("u_rate_stock", lang), fontsize=FS_BASE)
    hi_all = float(np.nanmax([pr.rate.max(), sp.rate.max()]))
    ax.set_xlim(-0.18 * hi_all, hi_all * 1.28)
    legend_wrapped(ax, loc="lower right", expand=False, width=22, fontsize=FS_CELL,
                   frameon=True, framealpha=0.92, edgecolor="none")
    _facet_title(ax, f"{tr('e15_f', lang)} ({E['last']})")
    letter(ax, "f")


    name = PLATES["E15"]
    title = {"es": f"P2 y P6 en detalle: población bajo control con TEA en la red pública, stock de diciembre, Chile 2019–2025 — {vlabel(variant, lang)}",
             "en": f"P2 and P6 in detail: ASD population under control in the public network, December stock, Chile 2019–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("Serie P es un stock semestral: diciembre es la medida principal y junio la sensibilidad; los dos semestres nunca se "
                      "suman y nunca comparten un eje con los flujos A03/A05/A27/A28. (a) P2 (NANEAS con TEA bajo control, P2500500) en "
                      "diciembre por 100.000 residentes, por región de la unidad que reporta; tasa ecológica. (b) Diciembre (barras) frente a "
                      "junio (marcadores huecos) para P2, P6 APS y P6 especialidad, con el quiebre de definición de P6 marcado en 2020–2021; bajo el eje, una fila por serie —en el color de la serie— con sus establecimientos reportantes de diciembre. "
                      "(c) Stock por establecimiento reportante; las líneas discontinuas son la categoría amplia de TGD de 2019–2020 y las "
                      "continuas el autismo estricto desde 2021, sin unión entre eras. (d) P2 con TEA frente al total de NANEAS bajo control "
                      "(P2501878, disponible desde diciembre de 2023) y su cociente por 100 con intervalo de Wilson: ambos numerador y "
                      "denominador provienen del mismo código-año de la misma fuente. (e) P6 APS y especialidad por era de definición sobre un solo eje: "
                      "barras rayadas = TGD amplio 2019–2020, barras llenas = autismo estricto y familia de la variante 2021–2025; las eras "
                      "no se unen ni se suman y el quiebre va marcado entre ellas. El rango de establecimientos reportantes de cada serie va "
                      "en su entrada de leyenda y el detalle año a año, en la tabla acompañante. (f) P6 APS y especialidad por región en el último "
                      "año, por 100.000 residentes, en mancuerna: un punto por serie unidos por su línea y el valor de cada uno en su extremo; "
                      "entre paréntesis, tras el nombre de la región, los establecimientos con fila de diciembre de APS y de especialidad. "
                      "n = establecimientos con fila de diciembre para el código. La banda gris marca "
                      "la disrupción del reporte de 2020–2021 y la línea punteada la publicación de la Ley 21.545 (marzo de 2023), presente "
                      "solo como contexto de política."),
               "en": ("Series P is a semester stock: December is the main measure and June the sensitivity; the two semesters are never summed "
                      "and never share an axis with the A03/A05/A27/A28 flows. (a) P2 (NANEAS with ASD under control, P2500500) in December per "
                      "100,000 residents, by region of the reporting unit; ecological rate. (b) December (bars) against June (hollow markers) "
                      "for P2, P6 primary care and P6 specialty, with the P6 definition break marked at 2020–2021; below the axis, one row per series — in the series colour — with its December reporting establishments. (c) Stock per reporting "
                      "establishment; dashed lines are the broad PDD category of 2019–2020 and solid lines strict autism from 2021, with no join "
                      "between eras. (d) P2 with ASD against the total NANEAS under control (P2501878, available from December 2023) and their "
                      "ratio per 100 with a Wilson interval: numerator and denominator come from the same code-year of the same source. (e) P6 "
                      "primary care and specialty by definition era on a single axis: hatched bars = broad PDD 2019–2020, solid bars = strict "
                      "autism and the variant family 2021–2025; the eras are neither joined nor summed and the break is marked between them. "
                      "The range of reporting establishments for each series is in its legend entry and the year-by-year detail in the companion "
                      "table. (f) P6 primary care and specialty by region in the last year, per 100,000 residents, as a dumbbell: one marker per "
                      "series joined by its line, each value written at its own end; in brackets after the region name, the establishments with a "
                      "December row for primary care and for specialty. n = establishments with a "
                      "December row for the code. The grey band marks the 2020\u20132021 reporting disruption and the dotted line the "
                      "publication of Law 21.545 (March 2023), present only as policy context.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    rows = []
    keymap = [("p2", tr("p2_short", lang), STOCK_YEARS), ("p6p_broad", f"{tr('p6p_short', lang)} — {tr('broad_short', lang)}", P6_ERA1),
              ("p6s_broad", f"{tr('p6s_short', lang)} — {tr('broad_short', lang)}", P6_ERA1),
              ("p6p_strict", f"{tr('p6p_short', lang)} — {tr('strict_short', lang)}", P6_ERA2),
              ("p6s_strict", f"{tr('p6s_short', lang)} — {tr('strict_short', lang)}", P6_ERA2),
              ("p6p_family", f"{tr('p6p_short', lang)} — {tr('family_short', lang)}", P6_ERA2),
              ("p6s_family", f"{tr('p6s_short', lang)} — {tr('family_short', lang)}", P6_ERA2),
              ("naneas", "NANEAS (P2501878)", [2023, 2024, 2025])]
    for key, lab, yrs in keymap:
        s = S[key].set_index("year")
        for measure, field, est_field in ((tr("december", lang), "december", "dec_est"), (tr("june", lang), "june", "jun_est")):
            rec = {LBL["t_series"][lang]: lab, tr("code", lang): S[key].codes.iloc[0], LBL["t_measure"][lang]: measure}
            for y in STOCK_YEARS:
                rec[str(y)] = val_n(s[field].get(y, np.nan), s[est_field].get(y, np.nan), lang) if y in s.index else tr("outside_era", lang)
            rows.append(rec)
    rec = {LBL["t_series"][lang]: tr("e15_d", lang), tr("code", lang): "P2500500 / P2501878", LBL["t_measure"][lang]: tr("per100_naneas", lang)}
    nn = E["naneas"].set_index("year")
    for y in STOCK_YEARS:
        rec[str(y)] = f"{pct(nn.per100.get(y), lang)} ({ci(nn.lo.get(y), nn.hi.get(y), 1, lang)})" if y in nn.index else tr("outside_era", lang)
    rows.append(rec)
    formatted = pd.DataFrame(rows)
    numeric = pd.concat([S[k].assign(series=k) for k in S], ignore_index=True)
    reg_long = []
    for r in E["tot"].index:
        for y in STOCK_YEARS:
            reg_long.append(dict(series="p2_region", cut_region=r, region=D.region_name[r], year=y,
                                 december=E["tot"].loc[r, y], dec_est=E["est"].loc[r, y],
                                 population=E["pop"].loc[r, y], rate_per_100k=E["rate"].loc[r, y],
                                 suppressed=bool(E["sup"].loc[r, y])))
    numeric = pd.concat([numeric, pd.DataFrame(reg_long), E["naneas"].assign(series="p2_over_naneas")], ignore_index=True)
    numeric["variant"] = variant
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "personas bajo control (stock semestral, COL01); diciembre principal y junio sensibilidad, nunca sumados", "en": "people under control (semester stock, COL01); December main and June sensitivity, never summed"}[lang],
                 denominator={"es": "población residente INE por región para las tasas; para P2/NANEAS, el total NANEAS del mismo código-año", "en": "INE resident population by region for the rates; for P2/NANEAS, the total NANEAS of the same code-year"}[lang],
                 coverage={"es": "red pública que reporta el código; la región es la de la unidad que reporta", "en": "public network reporting the code; the region is that of the reporting unit"}[lang],
                 era={"es": "P2500500 2019–2025; P2501878 desde diciembre de 2023; P6 TGD amplio 2019–2020 (P6223000/P6223380) y autismo/familia 2021–2025 (P6241010/P6241060 y la familia de la variante)",
                      "en": "P2500500 2019–2025; P2501878 from December 2023; P6 broad PDD 2019–2020 (P6223000/P6223380) and autism/family 2021–2025 (P6241010/P6241060 and the variant family)"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con fila del semestre correspondiente", "en": "n in brackets = establishments with a row for the corresponding semester"}[lang],
                 sources=f"{SRC_P}; {SRC_INE[lang]}; {SRC_TIDY}",
                 extra=NOTE_SUPPRESSION[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E16 · A27 y A28 por región
# ===========================================================================
A27_A28_YEARS = [2023, 2024, 2025]
A27_A28 = [(CFG.A27["counselling"], "counselling", "Blues"), (CFG.A27["assisted_referral"], "assisted_referral", "Oranges"),
           (CFG.A28["primary"], "rehab_primary", "Greens"), (CFG.A28["hospital"], "rehab_hospital", "Purples")]


def prep_e16(D: Data) -> dict:
    out = {}
    for code, key, _ in A27_A28:
        tot, est, sup = D.region_matrix([code], A27_A28_YEARS)
        nat = D.national([code]).set_index("year").reindex(A27_A28_YEARS)
        nat["rate"] = PER * nat.total / D.pop_nat.reindex(A27_A28_YEARS)
        nat["n_regions"] = [int(tot[y].notna().sum()) for y in A27_A28_YEARS]
        out[key] = dict(code=code, tot=tot, est=est, sup=sup, nat=nat)
    return out


def plate_e16(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e16"]
    rlab = [D.region_name[r] for r in E["counselling"]["tot"].index]
    fig, gs = new_plate()
    for k, (code, key, cmap) in enumerate(A27_A28):
        ax = fig.add_subplot(gs[k // 2, k % 2])
        s = E[key]
        unit = tr("u_interventions", lang) if key in ("counselling", "assisted_referral") else tr("u_rehab", lang)
        cb_unit = tr("cb_interventions", lang) if key in ("counselling", "assisted_referral") else tr("cb_rehab", lang)
        heat(ax, s["tot"], rlab, lang, lambda v, lg: num(v, 0, lg), cmap=cmap, cbar_label=cb_unit, suppressed=s["sup"])
        long_xlabel(ax, f"{tr('year', lang)} — {unit} — {tr('n_estab', lang)}", fontsize=FS_TICK)
        ax.xaxis.labelpad = 16
        _facet_title(ax, tr(f"e16_{'abcd'[k]}", lang))
        letter(ax, PLATE_LETTERS[k])
        for j, y in enumerate(A27_A28_YEARS):
            ax.text(j, -0.055, f"n={num(s['nat'].n_est.get(y), 0, lang)}", transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=FS_ANN, color="#555555")

    # --- e: establecimientos y regiones con reporte ---------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    w = 0.2
    for k, (code, key, _) in enumerate(A27_A28):
        s = E[key]["nat"]
        xx = np.asarray(A27_A28_YEARS, dtype=float) + (k - 1.5) * w
        ax.bar(xx, s.n_est, width=w * 0.9, color=OK[k], label=f"{tr(key, lang)}")
        for xi, v, nr in zip(xx, s.n_est, s.n_regions):
            # Doce barras de 3 mm en una celda de 90 mm: un rótulo de DOS líneas encima de cada una no cabe
            # (en español además se rozaban), y apartarlo lo metía dentro de la barra vecina. Una sola línea
            # girada —«establecimientos (regiones con fila)»— cabe sobre su propia barra y nada se pierde:
            # el rótulo del eje X dice qué es cada número y la tabla acompañante los lleva por separado.
            _ann(ax, xi, v, f"{num(v, 0, lang)} ({num(nr, 0, lang)})", DARK, fs=FS_CELL, dy=2, rotation=90)
    ax.set_xticks(A27_A28_YEARS)
    ax.set_ylabel(tr("estab_axis", lang), fontsize=FS_BASE)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('estab_regions', lang)}")
    ax.set_ylim(0, float(max(E[k2]["nat"].n_est.max() for _, k2, _ in A27_A28)) * 1.85)
    legend_wrapped(ax, loc="upper left", fontsize=FS_ANN)
    _facet_title(ax, tr("e16_e", lang))
    letter(ax, "e")

    # --- F: totales nacionales por 100.000 residentes -------------------------------------------
    ax = fig.add_subplot(gs[2, 1])
    marks = []
    for k, (code, key, _) in enumerate(A27_A28):
        s = E[key]["nat"]
        ax.plot(A27_A28_YEARS, s.rate, marker="o", ms=6, lw=2.0, color=OK[k], label=f"{tr(key, lang)}")
        marks += [(y, v, num(v, 1, lang), OK[k]) for y, v in zip(A27_A28_YEARS, s.rate)]
    ax.set_ylim(0, float(max(E[k2]["nat"].rate.max() for _, k2, _ in A27_A28)) * 1.24)
    # Cuatro series con tasas casi idénticas: cada rótulo se aparta de TODOS los marcadores del panel y de
    # los rótulos ya colocados (apilarlos verticalmente los separaba entre sí, pero los dejaba sobre el
    # marcador de la serie vecina).
    for mx, my, mtxt, mcol in marks:
        if pd.notna(my):
            value_label(ax, mx, my, mtxt, fontsize=FS_ANN, color=mcol,
                                bbox=dict(VALUE_HALO))
    ax.set_xticks(A27_A28_YEARS)
    ax.set_ylabel(f"{tr('u_rate_pop', lang)}", fontsize=FS_BASE)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('ecological', lang)}")
    ax.xaxis.label.set_color("#8a3b12")
    legend_wrapped(ax, loc="upper left", fontsize=FS_ANN)
    _facet_title(ax, tr("e16_f", lang))
    letter(ax, "f")

    name = PLATES["E16"]
    title = {"es": f"A27 y A28 por región: consejería y referencia asistida del tamizaje y ingresos a rehabilitación por TEA, Chile 2023–2025 — {vlabel(variant, lang)}",
             "en": f"A27 and A28 by region: screening counselling and assisted referral and ASD rehabilitation entries, Chile 2023–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a) Consejería en el contexto del tamizaje M-CHAT-R/F (29101566) y (b) referencia asistida (29101574), por región de la "
                      "unidad que reporta y año; A27 cuenta intervenciones, no personas. (c) Ingresos a rehabilitación en APS (29101629) y "
                      "(d) a rehabilitación hospitalaria (29101651). Los cuatro códigos existen solo desde 2023. Bajo cada columna se indica el "
                      "número nacional de establecimientos reportantes. (e) Establecimientos reportantes por año, con las regiones con al menos una "
                      "fila del código entre paréntesis sobre cada barra: varias regiones no presentan ninguna fila en algunos años, lo que "
                      "es ausencia de reporte y nunca un cero. (f) Totales nacionales por 100.000 residentes (INE base 2017); son tasas ecológicas porque el REM localiza "
                      "al prestador y no la residencia. Celdas grises: la región no presentó ninguna fila; «<5»: celda suprimida por tener menos "
                      "de cinco eventos."),
               "en": ("(a) Counselling in the M-CHAT-R/F screening context (29101566) and (b) assisted referral (29101574), by region of the "
                      "reporting unit and year; A27 counts interventions, not persons. (c) Entries to primary-level rehabilitation (29101629) "
                      "and (d) to hospital-level rehabilitation (29101651). The four codes exist only from 2023. Below each column is the "
                      "national number of reporting establishments. (e) Reporting establishments by year, with the regions that filed at least one row "
                      "for the code in brackets above each bar: several regions file no row in some years, which is absence of reporting and "
                      "never a zero. "
                      "(f) National totals per 100,000 residents (INE 2017 base); these are ecological rates because REM locates the provider and "
                      "not residence. Grey cells: the region filed no row; '<5': cell suppressed because it holds fewer than five events.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    rows = []
    for code, key, _ in A27_A28:
        s = E[key]
        for r in s["tot"].index:
            rec = {LBL["t_series"][lang]: tr(key, lang), tr("region", lang): D.region_name[r]}
            for y in A27_A28_YEARS:
                rec[str(y)] = (tr("not_reported", lang) if pd.isna(s["tot"].loc[r, y]) else
                               (f"{tr('suppressed', lang)} ({num(s['est'].loc[r, y], 0, lang)})" if s["sup"].loc[r, y] else
                                val_n(s["tot"].loc[r, y], s["est"].loc[r, y], lang)))
            rows.append(rec)
        rec = {LBL["t_series"][lang]: tr(key, lang), tr("region", lang): tr("national", lang)}
        for y in A27_A28_YEARS:
            rec[str(y)] = val_n(s["nat"].total.get(y), s["nat"].n_est.get(y), lang)
        rows.append(rec)
    formatted = pd.DataFrame(rows)
    long = []
    for code, key, _ in A27_A28:
        s = E[key]
        for r in s["tot"].index:
            for y in A27_A28_YEARS:
                long.append(dict(indicator=key, code=code, cut_region=r, region=D.region_name[r], year=y,
                                 total=s["tot"].loc[r, y], n_reporting_establishments=s["est"].loc[r, y],
                                 suppressed=bool(s["sup"].loc[r, y])))
        for y in A27_A28_YEARS:
            long.append(dict(indicator=key, code=code, cut_region=0, region="Chile", year=y, total=s["nat"].total.get(y),
                             n_reporting_establishments=s["nat"].n_est.get(y), suppressed=False,
                             rate_per_100k=s["nat"].rate.get(y), n_regions_with_rows=s["nat"].n_regions.get(y)))
    numeric = pd.DataFrame(long)
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "intervenciones (A27) e ingresos a rehabilitación (A28); flujo anual, suma de meses de COL01", "en": "interventions (A27) and rehabilitation entries (A28); annual flow, sum of months of COL01"}[lang],
                 denominator={"es": "ninguno para los conteos; población residente INE (base Censo 2017) para las tasas nacionales del panel f", "en": "none for the counts; INE resident population (Census 2017 base) for the national rates in panel f"}[lang],
                 coverage={"es": "red pública que reporta el código; la región es la de la unidad que reporta", "en": "public network reporting the code; the region is that of the reporting unit"}[lang],
                 era={"es": "29101566 y 29101574 (A27) y 29101629 y 29101651 (A28), todos desde 2023", "en": "29101566 and 29101574 (A27) and 29101629 and 29101651 (A28), all from 2023"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con al menos una fila del código en la región y el año", "en": "n in brackets = establishments with at least one row for the code in the region and year"}[lang],
                 sources=f"{SRC_A}; {SRC_INE[lang]}; {SRC_TIDY}",
                 extra=NOTE_SUPPRESSION[lang] + {"es": " A27 cuenta intervenciones, no personas, y no se relaciona por cociente con ninguna otra fuente.",
                                                 "en": " A27 counts interventions, not persons, and is never related by a ratio to any other source."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E17 · Distribuciones por establecimiento (Lorenz, decil superior y umbrales)
# ===========================================================================
THRESHOLDS = [1, 5, 10, 25, 50, 100]


def prep_e17(D: Data, variant: str) -> dict:
    specs = {
        "a05_strict": dict(codes=[CFG.STRICT["a05_entry"]], measure="annual_sum", years=A05_YEARS, label="e17_a"),
        "a05_family": dict(codes=list(CFG.VARIANTS[variant]["a05_entry"]), measure="annual_sum", years=A05_YEARS, label="e17_a"),
        "p2": dict(codes=[CFG.P2_TEA], measure="december_stock", years=STOCK_YEARS, label="e17_b"),
        "p6_primary": dict(codes=[CFG.STRICT["p6_primary"]], measure="december_stock", years=P6_ERA2, label="e17_c"),
        "p6_specialty": dict(codes=[CFG.STRICT["p6_specialty"]], measure="december_stock", years=P6_ERA2, label="e17_c"),
    }
    out = {"curves": {}, "summary": [], "thresholds": [], "values": {}}
    for key, spec in specs.items():
        g = D.by_establishment(spec["codes"], spec["measure"])
        out["values"][key] = g
        for y in spec["years"]:
            v = g.loc[g.year == y, "value"].to_numpy(dtype=float)
            x, cum, gini, top = lorenz(v)
            out["curves"][(key, y)] = (x, cum)
            pos = v[v > 0]
            out["summary"].append(dict(indicator=key, codes="+".join(spec["codes"]), measure=spec["measure"], year=y,
                                       n_establishments=int(v.size), n_establishments_positive=int(pos.size),
                                       total=float(np.nansum(v)), gini=gini, top_decile_share_pct=100 * top,
                                       median=float(np.median(pos)) if pos.size else np.nan,
                                       p25=float(np.percentile(pos, 25)) if pos.size else np.nan,
                                       p75=float(np.percentile(pos, 75)) if pos.size else np.nan,
                                       maximum=float(pos.max()) if pos.size else np.nan))
            for th in THRESHOLDS:
                out["thresholds"].append(dict(indicator=key, year=y, threshold=th, n_establishments=int((v >= th).sum()),
                                              share_of_total_pct=100 * float(v[v >= th].sum()) / float(v.sum()) if v.sum() else np.nan))
    out["summary"] = pd.DataFrame(out["summary"])
    out["thresholds"] = pd.DataFrame(out["thresholds"])
    return out


def plate_e17(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e17"]
    summ = E["summary"].set_index(["indicator", "year"])
    fig, gs = new_plate()

    for k, (key, years, ttl) in enumerate([("a05_strict", A05_YEARS, tr("e17_a", lang)), ("p2", STOCK_YEARS, tr("e17_b", lang)),
                                           ("p6_primary", P6_ERA2, tr("e17_c", lang))]):
        ax = fig.add_subplot(gs[0, k] if k < 2 else gs[1, 0])
        # la diagonal de igualdad perfecta va en las mismas unidades que las curvas (porcentajes, 0–100)
        ax.plot([0, 100], [0, 100], ls=":", lw=1.2, color=GREY, label=tr("equality", lang))
        # La leyenda llevaba «año: Gini …; D10 …; n=…»: una tabla de ocho filas y tres cifras que ocupaba
        # media celda y se imprimía sobre la diagonal de igualdad perfecta. El Gini y el decil superior de
        # estos mismos indicadores y años son EL PANEL (d) de esta lámina y una fila de la tabla
        # acompañante; en la leyenda queda el año con sus establecimientos reportantes, que es lo que
        # identifica cada curva. Así cabe entera en el triángulo vacío sobre la diagonal.
        for y in years:
            x, cum = E["curves"][(key, y)]
            ax.plot(100 * x, 100 * cum, lw=1.9, color=YEARCOL[y],
                    label=f"{y} (n={num(summ.loc[(key, y), 'n_establishments'], 0, lang)})")
        ax.set_xlim(0, 100); ax.set_ylim(0, 100)
        ax.set_xlabel(tr("lorenz_x", lang), fontsize=FS_BASE)
        ax.set_ylabel(tr("lorenz_y", lang), fontsize=FS_BASE)
        legend_wrapped(ax, loc="upper left", expand=False, width=26, fontsize=FS_CELL).set_gid(C.PLATE_KEEP)
        _facet_title(ax, ttl)
        letter(ax, PLATE_LETTERS[k])

    # --- D: decil superior y Gini --------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    keys = [("a05_strict", OK[0], E17_SHORT["a05_strict"][lang]), ("p2", OK[3], E17_SHORT["p2"][lang]),
            ("p6_primary", OK[2], E17_SHORT["p6_primary"][lang]), ("p6_specialty", OK[1], E17_SHORT["p6_specialty"][lang])]
    for key, col, lab in keys:
        s = E["summary"][E["summary"].indicator == key].sort_values("year")
        ax.plot(s.year, s.top_decile_share_pct, marker="o", ms=5.5, lw=2.0, color=col, label=lab)
    ax.set_xticks(STOCK_YEARS)
    ax.set_ylim(0, 100)
    ax.set_ylabel(tr("top_decile", lang), fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="lower left", fontsize=FS_ANN)
    ax2 = ax.twinx()
    for key, col, lab in keys:
        s = E["summary"][E["summary"].indicator == key].sort_values("year")
        ax2.plot(s.year, s.gini, marker="^", ms=4.5, lw=1.2, ls="--", color=col, alpha=0.75)
    ax2.set_ylim(0, 1); ax2.grid(False)
    ax2.set_ylabel(f"{tr('gini', lang)} (- -)", fontsize=FS_TICK)
    _facet_title(ax, tr("e17_d", lang))
    letter(ax, "d")

    # --- E: establecimientos que cruzan umbrales -----------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    thr = E["thresholds"]
    last = {"a05_strict": A05_YEARS[-1], "p2": STOCK_YEARS[-1], "p6_primary": P6_ERA2[-1]}
    first = {"a05_strict": A05_YEARS[0], "p2": STOCK_YEARS[0], "p6_primary": P6_ERA2[0]}
    xs = np.arange(len(THRESHOLDS))
    for k, (key, col, lab) in enumerate([("a05_strict", OK[0], E17_SHORT["a05_strict"][lang]), ("p2", OK[3], E17_SHORT["p2"][lang]),
                                         ("p6_primary", OK[2], E17_SHORT["p6_primary"][lang])]):
        s = thr[(thr.indicator == key) & (thr.year == last[key])].set_index("threshold").reindex(THRESHOLDS)
        s0 = thr[(thr.indicator == key) & (thr.year == first[key])].set_index("threshold").reindex(THRESHOLDS)
        xx = xs + (k - 1) * 0.27
        ax.bar(xx, s.n_establishments, width=0.25, color=col, label=f"{lab} — {last[key]}")
        ax.plot(xx, s0.n_establishments, ls="none", marker="o", ms=5.5, mfc="white", mec=col, mew=1.5,
                label=f"{lab} — {first[key]}")
        for xi, v in zip(xx, s.n_establishments):
            _ann(ax, xi, v, num(v, 0, lang), DARK, fs=FS_CELL, dy=2, rotation=90)
    ax.set_xticks(xs); ax.set_xticklabels([f"≥ {t}" for t in THRESHOLDS], fontsize=FS_TICK)
    ax.set_yscale("log")
    ax.set_ylabel(f"{tr('threshold_axis', lang)} {tr('log_scale', lang)}", fontsize=FS_BASE)
    # Los rótulos girados de las tres barras de cada umbral necesitan ~30 pt por encima de la barra más
    # alta: con el tope anterior se salían del panel y las cifras de «≥ 1» aparecían cortadas y pegadas
    # («9521,32»). El eje es logarítmico, así que el sitio se compra multiplicando el tope.
    ax.set_ylim(top=float(thr.n_establishments.max()) * 60.0)
    legend_wrapped(ax, loc="upper center", expand=False, width=22, ncol=2, columnspacing=0.7, fontsize=FS_CELL,
                   frameon=True, framealpha=0.92, edgecolor="none").set_gid(C.PLATE_KEEP)
    _facet_title(ax, tr("e17_e", lang))
    letter(ax, "e")

    # --- F: distribución del valor por establecimiento (A05 estricto) --------------------------
    ax = fig.add_subplot(gs[2, 1])
    g = E["values"]["a05_strict"]
    data = [g.loc[(g.year == y) & (g.value > 0), "value"].to_numpy(dtype=float) for y in A05_YEARS]
    bp = ax.boxplot(data, positions=np.arange(len(A05_YEARS)), widths=0.55, showfliers=True,
                    patch_artist=True, flierprops=dict(marker=".", ms=3, mfc=GREY, mec="none", alpha=0.5))
    for patch, y in zip(bp["boxes"], A05_YEARS):
        patch.set_facecolor(YEARCOL[y]); patch.set_alpha(0.55); patch.set_edgecolor(DARK)
    for med in bp["medians"]:
        med.set_color(DARK); med.set_linewidth(1.6)
    for i, y in enumerate(A05_YEARS):
        s = summ.loc[("a05_strict", y)]
        value_label(ax, i, float(s["maximum"]),
                    f"n={num(s['n_establishments_positive'], 0, lang)}\nmed={num(s['median'], 0, lang)}",
                    fontsize=FS_CELL, color=DARK, bbox=dict(VALUE_HALO), prefer=((0, 1),), max_steps=6)
    ax.set_yscale("log")
    # El rótulo «n=… / med=…» se ancla en el valor máximo del año, que es el atípico más alto de la caja:
    # sin cielo por encima no tenía adónde apartarse y se imprimía sobre ese punto.
    ax.set_ylim(top=float(np.nanmax([summ.loc[("a05_strict", y), "maximum"] for y in A05_YEARS])) * 4.0)
    ax.set_xticks(np.arange(len(A05_YEARS))); ax.set_xticklabels([str(y) for y in A05_YEARS], fontsize=FS_BASE)
    ax.set_ylabel(f"{tr('value_per_estab', lang)} {tr('log_scale', lang)}", fontsize=FS_BASE)
    ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
    _facet_title(ax, f"{tr('e17_f', lang)} — {tr('strict_short', lang)}")
    letter(ax, "f")

    name = PLATES["E17"]
    title = {"es": f"Distribución de la actividad REM entre establecimientos: curvas de Lorenz, decil superior y umbrales, Chile 2019–2025 — {vlabel(variant, lang)}",
             "en": f"Distribution of REM activity across establishments: Lorenz curves, top decile and thresholds, Chile 2019–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a–c) Curvas de Lorenz del valor por establecimiento y año para los ingresos A05 de autismo estricto (flujo anual), el "
                      "stock P2 de diciembre y el stock P6 de APS en diciembre; la diagonal punteada es la igualdad perfecta y la leyenda "
                      "identifica cada curva por su año y sus establecimientos con valor; el Gini y la participación del decil superior de "
                      "estos mismos indicadores y años están en el panel (d) y en la tabla acompañante. (d) Participación del "
                      "decil superior (líneas continuas, eje izquierdo) y Gini (líneas discontinuas, eje derecho) por indicador y año. "
                      "(e) Número de establecimientos con un valor igual o mayor a cada umbral en el último año (barras) y en el primer año "
                      "de la era (marcadores huecos), en escala logarítmica. (f) Distribución del valor por establecimiento en los ingresos "
                      "A05 de autismo estricto: caja con mediana y cuartiles y valores atípicos individuales, escala logarítmica; n = "
                      "establecimientos con valor mayor que cero. Los establecimientos con fila pero valor cero se conservan en el cálculo del "
                      "Gini y de los umbrales; los establecimientos sin fila no existen en el año y nunca se cuentan como cero."),
               "en": ("(a–c) Lorenz curves of the value per establishment and year for A05 strict-autism entries (annual flow), the December P2 "
                      "stock and the December P6 primary-care stock; the dotted diagonal is perfect equality and the legend identifies each "
                      "curve by its year and its establishments with a value; the Gini coefficient and the top-decile share of these same "
                      "indicators and years are in panel (d) and in the companion table. (d) Top-decile share (solid lines, left "
                      "axis) and Gini (dashed lines, right axis) by indicator and year. (e) Number of establishments with a value at or above "
                      "each threshold in the last year (bars) and in the first year of the era (hollow markers), on a logarithmic scale. "
                      "(f) Distribution of the value per establishment for A05 strict-autism entries: box with median and quartiles and "
                      "individual outliers, logarithmic scale; n = establishments with a value greater than zero. Establishments with a row but "
                      "a zero value are kept in the Gini and threshold calculations; establishments with no row do not exist in that year and "
                      "are never counted as zero.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    ind_label = {k: E17_SHORT[k][lang] for k in ("a05_strict", "a05_family", "p2", "p6_primary", "p6_specialty")}
    rows = []
    for key in ind_label:
        s = E["summary"][E["summary"].indicator == key].set_index("year")
        for field, flab, dec in (("n_establishments", tr("estab_short", lang), 0), ("gini", tr("gini", lang), 2),
                                 ("top_decile_share_pct", tr("top_decile", lang), 1), ("median", tr("value_per_estab", lang), 1)):
            rec = {LBL["t_series"][lang]: ind_label[key], tr("value", lang): flab}
            for y in STOCK_YEARS:
                rec[str(y)] = (num(s[field].get(y), dec, lang) if y in s.index else tr("outside_era", lang))
            rows.append(rec)
        for th in THRESHOLDS:
            t = E["thresholds"][(E["thresholds"].indicator == key) & (E["thresholds"].threshold == th)].set_index("year")
            rec = {LBL["t_series"][lang]: ind_label[key], tr("value", lang): f"{tr('threshold_axis', lang)}: ≥ {th}"}
            for y in STOCK_YEARS:
                rec[str(y)] = num(t.n_establishments.get(y), 0, lang) if y in t.index else tr("outside_era", lang)
            rows.append(rec)
    formatted = pd.DataFrame(rows)
    numeric = pd.concat([E["summary"].assign(block="distribution"), E["thresholds"].assign(block="thresholds")], ignore_index=True)
    numeric["variant"] = variant
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "valor por establecimiento y año: ingresos reportados (A05, flujo) o personas bajo control en diciembre (P2, P6, stock)",
                       "en": "value per establishment and year: entries reported (A05, flow) or people under control in December (P2, P6, stock)"}[lang],
                 denominator={"es": "el total del año del mismo indicador (para el Gini, el decil superior y la participación de los umbrales)",
                              "en": "the year total of the same indicator (for the Gini, the top decile and the threshold shares)"}[lang],
                 coverage={"es": "establecimientos con al menos una fila del código en el año; los establecimientos sin fila no se cuentan como cero",
                           "en": "establishments with at least one row for the code in the year; establishments with no row are not counted as zero"}[lang],
                 era={"es": "A05 autismo estricto y familia 2021–2025; P2 2019–2025; P6 autismo estricto 2021–2025", "en": "A05 strict autism and family 2021–2025; P2 2019–2025; P6 strict autism 2021–2025"}[lang],
                 reporting={"es": "la fila «establecimientos reportantes» de cada indicador", "en": "the 'reporting establishments' row of each indicator"}[lang],
                 sources=f"{SRC_A}; {SRC_P}; outputs/tidy/rem_establishment_year.csv",
                 extra={"es": "Las medidas de concentración describen el reporte administrativo entre establecimientos, no la distribución de personas con autismo.",
                        "en": "The concentration measures describe administrative reporting across establishments, not the distribution of people with autism."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E18 · Series mensuales REM
# ===========================================================================
def prep_e18(D: Data, variant: str) -> dict:
    m = {
        "a05_strict": D.by_month([CFG.STRICT["a05_entry"]]),
        "a05_broad": D.by_month([CFG.A05_BROAD_PRE2021["entry"]]),
        "a03_done": D.by_month([CFG.A03_LEGACY["mchat_done"]]),
        "a03_altered": D.by_month([CFG.A03_LEGACY["mchat_altered"]]),
        "a28_primary": D.by_month([CFG.A28["primary"]]),
        "a28_hospital": D.by_month([CFG.A28["hospital"]]),
    }
    season = {}
    for key, df in m.items():
        season[key] = df.groupby("month")["index"].agg(["mean", "min", "max"]).reindex(range(1, 13))
    both = []
    for key, codes in (("a03_control", [CFG.A03_LEGACY["control_18m"]]), ("a03_alteration", [CFG.A03_LEGACY["language_social_alteration"]]),
                       ("a03_done", [CFG.A03_LEGACY["mchat_done"]]), ("a03_altered", [CFG.A03_LEGACY["mchat_altered"]]),
                       ("a05_broad", [CFG.A05_BROAD_PRE2021["entry"]])):
        df = D.by_month(codes)
        a = df[df.year == 2019].set_index("month").total
        b = df[df.year == 2020].set_index("month").total
        for mo in range(1, 13):
            both.append(dict(indicator=key, month=mo, value_2019=a.get(mo, np.nan), value_2020=b.get(mo, np.nan),
                             ratio=(b.get(mo, np.nan) / a.get(mo, np.nan)) if a.get(mo, np.nan) else np.nan))
    return dict(m=m, season=season, ratio2020=pd.DataFrame(both))


def plate_e18(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e18"]
    M, S = E["m"], E["season"]
    months = tr("months_abbr", lang)
    fig, gs = new_plate()

    # --- A: A05 por mes ------------------------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    for y in A05_YEARS:
        s = M["a05_strict"][M["a05_strict"].year == y].sort_values("month")
        ax.plot(s.month, s.total, marker="o", ms=4, lw=1.8, color=YEARCOL[y], label=f"{y} — {tr('strict_short', lang)}")
    for y in (2019, 2020):
        s = M["a05_broad"][M["a05_broad"].year == y].sort_values("month")
        ax.plot(s.month, s.total, marker="^", ms=4, lw=1.4, ls="--", color=YEARCOL[y], alpha=0.85, label=f"{y} — {tr('broad_short', lang)}")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(tr("u_entries", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper left", fontsize=FS_CELL, ncol=2)
    # La advertencia «eras separadas» se escribía dentro del panel, sobre la serie amplia de 2020 (el 21 %
    # de la línea). Bajo el eje dice lo mismo y no tapa nada.
    long_xlabel(ax, tr("no_continuity", lang))
    ax.xaxis.label.set_color("#8a3b12")
    _facet_title(ax, tr("e18_a", lang))
    letter(ax, "a")

    # --- B: A03 legado por mes -----------------------------------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    for y in (2019, 2020, 2021, 2022):
        s = M["a03_done"][M["a03_done"].year == y].sort_values("month")
        ax.plot(s.month, s.total, marker="o", ms=4, lw=1.8, color=YEARCOL[y], label=str(y))
    ax.set_yscale("log")
    v2019 = float(M["a03_done"][(M["a03_done"].year == 2019) & (M["a03_done"].month == 2)].total.iloc[0])
    # El recuadro de la nota caía sobre los propios puntos que señala; se sube al cielo del panel, con la
    # flecha apuntando al dato, y el eje se estira lo justo para que quepa.
    headroom(ax, 0.55)
    ax.annotate(wrap_measured(tr("feb_outlier", lang), 104.0, FS_ANN, "normal"),
                xy=(2, v2019), xytext=(4.2, v2019 * 2.6), fontsize=FS_ANN, color="#8a3b12",
                ha="left", va="bottom", arrowprops=dict(arrowstyle="->", color="#8a3b12", lw=1.0))
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(f"{tr('u_screen', lang)} {tr('log_scale', lang)}", fontsize=FS_BASE)
    legend_wrapped(ax, loc="lower right", fontsize=FS_ANN, ncol=2)
    _facet_title(ax, tr("e18_b", lang))
    letter(ax, "b")

    # --- C: A28 por mes ------------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    for y in A27_A28_YEARS:
        s = M["a28_primary"][M["a28_primary"].year == y].sort_values("month")
        ax.plot(s.month, s.total, marker="o", ms=4.5, lw=1.9, color=YEARCOL[y], label=f"{y} — {tr('rehab_primary', lang)}")
        s2 = M["a28_hospital"][M["a28_hospital"].year == y].sort_values("month")
        ax.plot(s2.month, s2.total, marker="s", ms=3.6, lw=1.2, ls=":", color=YEARCOL[y], alpha=0.85,
                label=f"{y} — {tr('rehab_hospital', lang)}")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(tr("u_rehab", lang), fontsize=FS_BASE)
    # El color codifica el año y el trazo el nivel de atención: cinco entradas en vez de seis rótulos largos.
    from matplotlib.lines import Line2D
    hs = ([Line2D([], [], color=YEARCOL[y], marker="o", ms=4.5, lw=1.9) for y in A27_A28_YEARS] +
          [Line2D([], [], color=GREY, marker="o", ms=4.5, lw=1.9),
           Line2D([], [], color=GREY, marker="s", ms=3.6, lw=1.2, ls=":")])
    ls_ = [str(y) for y in A27_A28_YEARS] + [tr("rehab_primary_short", lang), tr("rehab_hospital_short", lang)]
    # UNA LEYENDA DE VARIAS COLUMNAS NO MEZCLA ENTRADAS DE UNA LÍNEA CON ENTRADAS DE DOS. Con el
    # plegado anterior los cinco años ocupaban una línea y las dos claves de trazo dos, de modo que
    # (i) matplotlib centraba el marcador gris entre las dos líneas de su rótulo —no quedaba a la
    # altura de ninguna— y (ii) cada columna se empaqueta por su cuenta, así que la segunda entrada
    # gris caía a la altura de la fila TERCERA de la primera columna. El ancho de plegado se sube
    # por encima del rótulo más largo y las columnas bajan a dos: todas las entradas miden una
    # línea, el marcador queda sobre su rótulo y las filas se leen en horizontal.
    legend_wrapped(ax, hs, ls_, loc="upper left", ncol=2, width=28, columnspacing=0.7, fontsize=FS_CELL)
    _facet_title(ax, tr("e18_c", lang))
    letter(ax, "c")

    # --- D: índice estacional medio ------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    for key, col, lab in (("a05_strict", OK[0], f"A05 {tr('strict_short', lang)} 2021–2025"),
                          ("a03_done", OK[2], f"A03 M-CHAT 2019–2022"),
                          ("a28_primary", OK[1], f"A28 {tr('rehab_primary', lang)} 2023–2025")):
        s = S[key]
        ax.plot(s.index, s["mean"], marker="o", ms=5, lw=2.0, color=col, label=lab)
        ax.fill_between(s.index, s["min"], s["max"], color=col, alpha=0.12)
    ax.axhline(100, color=GREY, ls=":", lw=1.2)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(tr("u_index", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper right", fontsize=FS_ANN)
    _facet_title(ax, tr("e18_d", lang))
    letter(ax, "d")

    # --- E: establecimientos con fila en el mes ------------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    for key, ls, lab in (("a05_strict", "-", f"A05 {tr('strict_short', lang)}"), ("a28_primary", "--", f"A28 {tr('rehab_primary', lang)}")):
        for y in sorted(M[key].year.unique()):
            s = M[key][M[key].year == y].sort_values("month")
            ax.plot(s.month, s.n_est, marker="o", ms=3.2, lw=1.4, ls=ls, color=YEARCOL[y],
                    label=f"{y} — {lab}")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(tr("estab_axis", lang), fontsize=FS_BASE)
    long_xlabel(ax, tr("no_row_month", lang))
    ax.xaxis.label.set_color("#555555")
    from matplotlib.lines import Line2D as _L2
    yrs_e = sorted(set(M["a05_strict"].year.unique()) | set(M["a28_primary"].year.unique()))
    hs = ([_L2([], [], color=YEARCOL[y], marker="o", ms=3.2, lw=1.4) for y in yrs_e] +
          [_L2([], [], color=GREY, marker="o", ms=3.2, lw=1.4),
           _L2([], [], color=GREY, marker="o", ms=3.2, lw=1.4, ls="--")])
    ls_ = [str(y) for y in yrs_e] + [f"A05 {tr('strict_short', lang)}", f"A28 {tr('rehab_primary_short', lang)}"]
    headroom(ax, 0.34)
    # UNA LEYENDA DE VARIAS COLUMNAS NO MEZCLA ENTRADAS DE UNA LÍNEA CON ENTRADAS DE DOS. Con el
    # plegado anterior los cinco años ocupaban una línea y las dos claves de trazo dos, de modo que
    # (i) matplotlib centraba el marcador gris entre las dos líneas de su rótulo —no quedaba a la
    # altura de ninguna— y (ii) cada columna se empaqueta por su cuenta, así que la segunda entrada
    # gris caía a la altura de la fila TERCERA de la primera columna. El ancho de plegado se sube
    # por encima del rótulo más largo y las columnas bajan a dos: todas las entradas miden una
    # línea, el marcador queda sobre su rótulo y las filas se leen en horizontal.
    legend_wrapped(ax, hs, ls_, loc="upper left", expand=False, ncol=2, width=28, columnspacing=0.7, fontsize=FS_CELL)
    _facet_title(ax, tr("e18_e", lang))
    letter(ax, "e")

    # --- F: disrupción de 2020 -----------------------------------------------------------------
    ax = fig.add_subplot(gs[2, 1])
    lab2020 = {"a03_control": A03_CODE_LABEL["03500404"][lang], "a03_alteration": A03_CODE_LABEL["03500405"][lang],
               "a03_done": A03_CODE_LABEL["03500406"][lang], "a03_altered": A03_CODE_LABEL["03500407"][lang],
               "a05_broad": f"A05 {tr('broad_short', lang)}"}
    for k, key in enumerate(lab2020):
        s = E["ratio2020"][E["ratio2020"].indicator == key].sort_values("month")
        ax.plot(s.month, 100 * s.ratio, marker="o", ms=4, lw=1.7, color=OK[k % len(OK)], label=lab2020[key])
    ax.axhline(100, color=GREY, ls=":", lw=1.2)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=FS_TICK, rotation=45, ha="right")
    ax.set_ylabel(f"{tr('ratio_2020_2019', lang)} (%)", fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper right", width=20, fontsize=FS_CELL,
                   frameon=True, framealpha=0.92, edgecolor="none")
    _facet_title(ax, tr("e18_f", lang))
    letter(ax, "f")

    name = PLATES["E18"]
    title = {"es": f"Series mensuales REM: ingresos A05, tamizaje A03 y rehabilitación A28 por mes, estacionalidad y disrupción de 2020, Chile 2019–2025 — {vlabel(variant, lang)}",
             "en": f"Monthly REM series: A05 entries, A03 screening and A28 rehabilitation by month, seasonality and the 2020 disruption, Chile 2019–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a) Ingresos A05 por mes: líneas continuas para el autismo estricto de 2021–2025 y líneas discontinuas para la "
                      "categoría amplia de TGD de 2019–2020, que es una definición distinta y no continúa la serie. (b) M-CHAT realizado de la "
                      "era legado por mes en escala logarítmica, con el atípico de febrero de 2019 señalado. (c) Ingresos a rehabilitación A28 "
                      "por mes, en APS (línea continua) y hospitalaria (línea punteada). (d) Índice estacional medio por mes dentro de cada era "
                      "(media de los doce meses del año = 100), con la banda de mínimo a máximo entre años. (e) Establecimientos con al menos "
                      "una fila en el mes; un mes sin fila es ausencia de reporte y nunca un cero. (f) Disrupción del reporte en 2020: cociente "
                      "entre cada mes de 2020 y el mismo mes de 2019 para los códigos presentes en ambos años. Ningún panel mezcla stocks con "
                      "flujos ni une eras de definición distintas."),
               "en": ("(a) A05 entries by month: solid lines for strict autism in 2021–2025 and dashed lines for the broad PDD category of "
                      "2019–2020, which is a different definition and does not continue the series. (b) Legacy-era M-CHAT performed by month on "
                      "a logarithmic scale, with the February 2019 outlier marked. (c) A28 rehabilitation entries by month, primary-level (solid "
                      "line) and hospital-level (dotted line). (d) Mean seasonal index by month within each era (mean of the year's twelve months "
                      "= 100), with the minimum-to-maximum band across years. (e) Establishments with at least one row in the month; a month "
                      "without a row is absence of reporting and never a zero. (f) 2020 reporting disruption: ratio of each 2020 month to the "
                      "same month of 2019 for the codes present in both years. No panel mixes stocks with flows or joins different definition "
                      "eras.")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    ind_lab = {"a05_strict": f"A05 {tr('strict_short', lang)}", "a05_broad": f"A05 {tr('broad_short', lang)}",
               "a03_done": A03_CODE_LABEL["03500406"][lang], "a03_altered": A03_CODE_LABEL["03500407"][lang],
               "a28_primary": tr("rehab_primary", lang), "a28_hospital": tr("rehab_hospital", lang)}
    rows = []
    for key, lab in ind_lab.items():
        df = M[key]
        for y in sorted(df.year.unique()):
            rec = {LBL["t_series"][lang]: lab, tr("year", lang): str(y)}
            s = df[df.year == y].set_index("month")
            for mo in range(1, 13):
                rec[months[mo - 1]] = val_n(s.total.get(mo, np.nan), s.n_est.get(mo, np.nan), lang)
            rec[tr("total_year", lang)] = num(s.total.sum(min_count=1), 0, lang)
            rows.append(rec)
    formatted = pd.DataFrame(rows)
    numeric = pd.concat([M[k].assign(indicator=k) for k in M], ignore_index=True)
    numeric = pd.concat([numeric, E["ratio2020"].assign(block="ratio_2020_2019")], ignore_index=True)
    numeric["variant"] = variant
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "registros del mes (flujo mensual; COL01, o COL01+COL02 en A03)", "en": "records of the month (monthly flow; COL01, or COL01+COL02 in A03)"}[lang],
                 denominator={"es": "para el índice estacional, la media de los doce meses del mismo año", "en": "for the seasonal index, the mean of the twelve months of the same year"}[lang],
                 coverage={"es": "red pública que reporta el código en el mes", "en": "public network reporting the code in the month"}[lang],
                 era={"es": "A05 amplio 2019–2020 y estricto 2021–2025; A03 legado 2019–2022; A28 desde 2023", "en": "A05 broad 2019–2020 and strict 2021–2025; A03 legacy 2019–2022; A28 from 2023"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con fila en ese mes", "en": "n in brackets = establishments with a row in that month"}[lang],
                 sources=f"{SRC_A}; outputs/tidy/rem_pathway_tidy.csv",
                 extra={"es": "Un mes sin fila aparece como «no reportado» y nunca se interpola ni se lee como cero.",
                        "en": "A month without a row appears as 'not reported' and is never interpolated or read as zero."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# E19 · Sensibilidad por era de definición
# ===========================================================================
E19_INDICATORS = [
    ("a05_entry", "A05", "annual_sum", "e19_a", CFG.STRICT["a05_entry"], "a05_entry", CFG.A05_BROAD_PRE2021["entry"], CFG.A05_ENTRY),
    ("a05_exit", "A05", "annual_sum", "e19_b", CFG.STRICT["a05_exit"], "a05_exit", CFG.A05_BROAD_PRE2021["exit"], CFG.A05_EXIT),
    ("p6_primary", "P6", "december_stock", "e19_c", CFG.STRICT["p6_primary"], "p6_primary", CFG.P6_BROAD_PRE2021["primary"], CFG.P6_PRIMARY),
    ("p6_specialty", "P6", "december_stock", "e19_d", CFG.STRICT["p6_specialty"], "p6_specialty", CFG.P6_BROAD_PRE2021["specialty"], CFG.P6_SPECIALTY),
]


def prep_e19(D: Data, variant: str) -> dict:
    month = {"annual_sum": None, "december_stock": 12}
    out, comp, ratio = {}, [], []
    for key, module, measure, _lab, strict, famkey, broad, catmap in E19_INDICATORS:
        mo = month[measure]
        years2 = P6_ERA2 if module == "P6" else A05_YEARS
        s_strict = D.national([strict], month=mo).set_index("year").reindex(years2)
        fam_codes = list(CFG.VARIANTS[variant][famkey])
        s_family = D.national(fam_codes, month=mo).set_index("year").reindex(years2)
        s_broad = D.national([broad], month=mo).set_index("year").reindex(P6_ERA1)
        out[key] = dict(strict=s_strict, family=s_family, broad=s_broad, module=module, measure=measure,
                        strict_code=strict, family_codes="+".join(fam_codes), broad_code=broad, years2=years2)
        for cat, code in catmap.items():
            if code not in fam_codes:
                continue
            s = D.national([code], month=mo).set_index("year").reindex(years2)
            for y in years2:
                comp.append(dict(indicator=key, category=cat, code=code, year=y, total=s.total.get(y, np.nan),
                                 n_est=s.n_est.get(y, np.nan)))
        for y in years2:
            a, b = s_family.total.get(y, np.nan), s_strict.total.get(y, np.nan)
            ratio.append(dict(indicator=key, year=y, family=a, strict=b, ratio=a / b if b else np.nan,
                              excess=a - b, excess_pct=100 * (a - b) / a if a else np.nan))
    comp = pd.DataFrame(comp)
    comp["share_pct"] = 100 * comp.total / comp.groupby(["indicator", "year"]).total.transform("sum")
    return dict(series=out, comp=comp, ratio=pd.DataFrame(ratio))


def plate_e19(D: Data, P: dict, variant: str, lang: str) -> tuple[str, list[str]]:
    plt = plate_style()
    E = P["e19"]
    fig, gs = new_plate()

    for k, (key, module, measure, lab, *_rest) in enumerate(E19_INDICATORS):
        ax = fig.add_subplot(gs[k // 2, k % 2])
        s = E["series"][key]
        yb = P6_ERA1
        ax.bar(np.asarray(yb, dtype=float), s["broad"].total.reindex(yb), width=0.52, color=LIGHT, edgecolor=DARK,
               linewidth=0.6, label=tr("broad_short", lang))
        for t in s["broad"].reindex(yb).itertuples():
            if pd.notna(t.total):
                _ann(ax, t.Index, t.total, f"{num(t.total, 0, lang)}\nn={num(t.n_est, 0, lang)}", DARK, fs=FS_CELL, dy=2)
        y2 = np.asarray(s["years2"], dtype=float)
        ax.bar(y2 - 0.19, s["strict"].total, width=0.36, color=OK[0], label=tr("strict_short", lang))
        ax.bar(y2 + 0.19, s["family"].total, width=0.36, color=OK[2], label=tr("family_short", lang))
        for t in s["strict"].itertuples():
            if pd.notna(t.total):
                _ann(ax, t.Index - 0.19, t.total, f"n={num(t.n_est, 0, lang)}", DARK, fs=FS_CELL, dy=2, rotation=90)
        for t in s["family"].itertuples():
            if pd.notna(t.total):
                _ann(ax, t.Index + 0.19, t.total, f"{num(t.total, 0, lang)}", OK[2], fs=FS_CELL, dy=2, rotation=90)
        _break_marker(ax, 2020.5, lang, y=0.55)
        ax.set_xticks(STOCK_YEARS)
        ax.set_xlim(2018.4, 2025.7)
        top = float(np.nanmax([np.nanmax(s["family"].total.to_numpy(dtype=float)), np.nanmax(s["broad"].total.to_numpy(dtype=float))]))
        ax.set_ylim(0, top * 1.35)
        ax.set_ylabel({"a05_entry": tr("u_entries", lang), "a05_exit": tr("u_exits", lang)}.get(key, tr("u_stock_dec", lang)), fontsize=FS_BASE)
        ax.set_xlabel(tr("year", lang), fontsize=FS_BASE)
        _context(ax, lang, pandemic_text=False, law_pos=0.80)
        legend_wrapped(ax, loc="upper left", fontsize=FS_ANN)
        _facet_title(ax, tr(lab, lang))
        letter(ax, PLATE_LETTERS[k])

    # --- e: composición de la familia por categoría --------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    comp = E["comp"]
    cats = [c for c in CATEGORY_KEY if c in set(comp.category)]
    keys = [k for k, *_ in E19_INDICATORS]
    pos, labs, bottoms = [], [], []
    p = 0
    for key in keys:
        years2 = E["series"][key]["years2"]
        for y in [years2[0], years2[-1]]:
            pos.append(p); labs.append(f"{y}")
            p += 1
        p += 0.7
    bottom = np.zeros(len(pos))
    for ci_, cat in enumerate(cats):
        vals = []
        for key in keys:
            years2 = E["series"][key]["years2"]
            for y in [years2[0], years2[-1]]:
                s = comp[(comp.indicator == key) & (comp.category == cat) & (comp.year == y)]
                vals.append(float(s.share_pct.iloc[0]) if len(s) else np.nan)
        vals = np.asarray(vals, dtype=float)
        ax.bar(pos, np.nan_to_num(vals), bottom=bottom, width=0.72, color=OK[ci_ % len(OK)], label=tr(CATEGORY_KEY[cat], lang))
        for pi, vi, bi in zip(pos, vals, bottom):
            if pd.notna(vi) and vi >= 4:
                ax.text(pi, bi + vi / 2, num(vi, 1, lang), ha="center", va="center", fontsize=FS_CELL, color="white")
        bottom = bottom + np.nan_to_num(vals)
    ax.set_xticks(pos); ax.set_xticklabels(labs, fontsize=FS_ANN)
    ax.tick_params(axis="x", pad=2)
    # Barras apiladas al 100 %: dentro del panel no queda un solo hueco libre, así que la leyenda va en un
    # cielo RESERVADO por encima del 100 % (las marcas del eje siguen llegando solo hasta 100). Antes se
    # dibujaba sobre las barras y tapaba hasta un tercio de dos de ellas.
    ax.set_ylim(0, 132)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel(tr("u_share", lang), fontsize=FS_BASE)
    legend_wrapped(ax, loc="upper center", expand=False, fontsize=FS_CELL, ncol=3, width=18)
    for i, key in enumerate(keys):
        centre = np.mean(pos[2 * i:2 * i + 2])
        # Cuatro glosas de indicador bajo un eje de 55 mm: se parten en líneas para no escribirse una sobre otra
        ax.text(centre, -0.085, tick_label(E19_SHORT[key][lang], 12, 3), transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=FS_CELL, color="#555555", linespacing=1.0)
    _facet_title(ax, f"{tr('e19_e', lang)} — {vlabel(variant, lang)}")
    letter(ax, "e")

    # --- F: razón familia / estricto -----------------------------------------------------------
    ax = fig.add_subplot(gs[2, 1])
    marks, rmax = [], 0.0
    for k, key in enumerate(keys):
        s = E["ratio"][E["ratio"].indicator == key].sort_values("year")
        ax.plot(s.year, s.ratio, marker="o", ms=5.5, lw=2.0, color=OK[k], label=E19_SHORT[key][lang])
        marks += [(t.year, t.ratio, num(t.ratio, 2, lang), OK[k]) for t in s.itertuples()]
        rmax = max(rmax, float(np.nanmax(s.ratio.to_numpy(dtype=float))))
    ax.axhline(1.0, color=GREY, ls=":", lw=1.2)
    ax.set_ylim(0.9, rmax * 1.28)
    # Cuatro series con razones casi iguales: apilar las etiquetas verticalmente las separaba entre sí pero
    # las dejaba encima del marcador de la serie vecina. `plate_value_label` mide el panel ya dibujado y
    # aparta cada rótulo de TODOS los marcadores y de los rótulos ya colocados.
    for mx, my, mtxt, mcol in marks:
        if pd.notna(my):
            value_label(ax, mx, my, mtxt, fontsize=FS_CELL, color=mcol,
                                bbox=dict(VALUE_HALO))
    ax.set_xticks(P6_ERA2)
    ax.set_ylabel(tr("family_over_strict", lang), fontsize=FS_BASE)
    long_xlabel(ax, f"{tr('year', lang)} — {tr('no_continuity', lang)}")
    ax.xaxis.label.set_color("#8a3b12")
    legend_wrapped(ax, loc="upper right", fontsize=FS_ANN)
    _facet_title(ax, tr("e19_f", lang))
    letter(ax, "f")

    name = PLATES["E19"]
    title = {"es": f"Sensibilidad por era de definición: cada indicador REM bajo el autismo estricto, la familia TGD de la variante y la categoría amplia pre-2021, Chile 2019–2025 — {vlabel(variant, lang)}",
             "en": f"Definition-era sensitivity: every REM indicator under strict autism, the variant PDD family and the broad pre-2021 category, Chile 2019–2025 — {vlabel(variant, lang)}"}[lang]
    caption = {"es": ("(a–d) Para los ingresos y las altas clínicas A05 y para el stock P6 de diciembre en APS y en especialidad, los totales "
                      "nacionales bajo tres definiciones: la categoría amplia de trastornos generalizados del desarrollo de 2019–2020 (barra "
                      "gris), el código estricto de autismo desde 2021 (barra azul) y la familia TGD de la variante desde 2021 (barra verde). "
                      "El quiebre de definición está marcado entre 2020 y 2021: las barras de los dos lados miden objetos distintos y no forman "
                      "una serie continua, por lo que no se unen con una línea ni se comparan como si fueran el mismo indicador. "
                      "(e) Composición porcentual de la familia TGD por categoría en el primer y el último año de cada indicador. (f) Razón "
                      "entre el total de la familia y el del autismo estricto, calculada dentro del mismo año y la misma fuente. "
                      "La banda gris marca la disrupción del reporte de 2020–2021 y la línea punteada la publicación de la Ley 21.545 "
                      "(marzo de 2023), presente solo como contexto de política. n = establecimientos que reportan el código o cualquier "
                      "código de la familia en el año (contados una sola vez)."),
               "en": ("(a–d) For A05 entries and clinical discharges and for the December P6 stock in primary care and in specialty care, the "
                      "national totals under three definitions: the broad pervasive developmental disorder category of 2019–2020 (grey bar), the "
                      "strict autism code from 2021 (blue bar) and the variant PDD family from 2021 (green bar). The definition break is marked "
                      "between 2020 and 2021: the bars on either side measure different objects and do not form a continuous series, so they are "
                      "neither joined by a line nor compared as if they were the same indicator. (e) Percentage composition of the PDD family by "
                      "category in the first and last year of each indicator. (f) Ratio of the family total to the strict-autism total, computed "
                      "within the same year and the same source. The grey band marks the 2020–2021 reporting disruption and the dotted line "
                      "the publication of Law 21.545 (March 2023), present only as policy context. n = establishments reporting the code or "
                      "any code of the family in the year (counted once).")}[lang]
    fpath = write_plate(fig, name, variant, lang, title, caption)

    # --- tabla ---------------------------------------------------------------------------------
    ind_lab = {k: E19_SHORT[k][lang] for k in E19_SHORT}
    rows = []
    for key in ind_lab:
        s = E["series"][key]
        for defkey, deflab, frame in (("broad", tr("broad_short", lang), s["broad"]), ("strict", tr("strict_short", lang), s["strict"]),
                                      ("family", tr("family_short", lang), s["family"])):
            code = {"broad": s["broad_code"], "strict": s["strict_code"], "family": s["family_codes"]}[defkey]
            rec = {LBL["t_series"][lang]: ind_lab[key], tr("code", lang): code, tr("era", lang): deflab}
            for y in STOCK_YEARS:
                rec[str(y)] = val_n(frame.total.get(y, np.nan), frame.n_est.get(y, np.nan), lang) if y in frame.index else tr("outside_era", lang)
            rows.append(rec)
        r = E["ratio"][E["ratio"].indicator == key].set_index("year")
        rec = {LBL["t_series"][lang]: ind_lab[key], tr("code", lang): f"{s['family_codes']} / {s['strict_code']}", tr("era", lang): tr("family_over_strict", lang)}
        for y in STOCK_YEARS:
            rec[str(y)] = num(r.ratio.get(y), 2, lang) if y in r.index else tr("outside_era", lang)
        rows.append(rec)
    formatted = pd.DataFrame(rows)
    long = []
    for key in ind_lab:
        s = E["series"][key]
        for defkey, frame in (("broad", s["broad"]), ("strict", s["strict"]), ("family", s["family"])):
            for y in frame.index:
                long.append(dict(indicator=key, definition=defkey, module=s["module"], measure=s["measure"],
                                 code={"broad": s["broad_code"], "strict": s["strict_code"], "family": s["family_codes"]}[defkey],
                                 year=int(y), total=frame.total.get(y, np.nan), n_reporting_establishments=frame.n_est.get(y, np.nan)))
    numeric = pd.concat([pd.DataFrame(long), E["comp"].assign(block="family_composition"), E["ratio"].assign(block="family_over_strict")], ignore_index=True)
    numeric["variant"] = variant
    numeric["script"] = SCRIPT
    tnote = note(lang,
                 unit={"es": "ingresos y altas clínicas reportados (A05, flujo anual) y personas bajo control en diciembre (P6, stock)",
                       "en": "entries and clinical discharges reported (A05, annual flow) and people under control in December (P6, stock)"}[lang],
                 denominator={"es": "para la razón familia/estricto, el total del autismo estricto del mismo año y la misma fuente",
                              "en": "for the family/strict ratio, the strict-autism total of the same year and the same source"}[lang],
                 coverage={"es": "red pública que reporta el código o cualquier código de la familia", "en": "public network reporting the code or any code of the family"}[lang],
                 era={"es": "TGD amplio 2019–2020 (06902600, 05225000, P6223000, P6223380) frente a autismo estricto y familia TGD 2021–2025; son definiciones distintas y no forman una serie continua",
                      "en": "broad PDD 2019–2020 (06902600, 05225000, P6223000, P6223380) against strict autism and the PDD family 2021–2025; these are different definitions and do not form a continuous series"}[lang],
                 reporting={"es": "n entre paréntesis = establecimientos con al menos una fila del código o de la familia en el año", "en": "n in brackets = establishments with at least one row for the code or the family in the year"}[lang],
                 sources=f"{SRC_A}; {SRC_P}; {SRC_TIDY}",
                 extra={"es": "Los totales de las dos eras no deben restarse ni dividirse entre sí: la categoría amplia pre-2021 no aísla el autismo.",
                        "en": "The totals of the two eras must not be subtracted from or divided by each other: the broad pre-2021 category cannot isolate autism."}[lang])
    tpaths = write_table(name, variant, lang, formatted, numeric, title, tnote)
    return fpath, tpaths


# ===========================================================================
# Controles de reproducción
# ===========================================================================
def build_controls(D: Data, preps: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict] = []

    def add(name, key, expected, observed, note_="", kind="count", tol=0.005):
        exp = np.nan if expected is None else float(expected)
        obs = np.nan if observed is None or (isinstance(observed, float) and (np.isnan(observed) or np.isinf(observed))) or pd.isna(observed) else float(observed)
        if np.isnan(exp):
            status, absd, reld = "info", np.nan, np.nan
        elif np.isnan(obs):
            status, absd, reld = "differs", np.nan, np.nan
            note_ = (note_ + "; " if note_ else "") + "observed value missing"
        else:
            absd = obs - exp
            reld = absd / exp if exp else np.nan
            if kind == "count":
                ok = absd == 0
            elif kind == "abs_tol":
                ok = abs(absd) <= tol
            else:
                ok = pd.notna(reld) and abs(reld) <= tol
            status = "ok" if ok else "differs"
        rows.append(dict(name=name, key=key, expected=exp, observed=obs, abs_diff=absd, rel_diff=reld, status=status, note=note_))

    CT = CFG.CONTROLS
    # 1. Totales del encargo reproducidos por la agregación propia de este módulo (tidy → national)
    simple = {"a05_autism_entries": ([CFG.STRICT["a05_entry"]], None), "a05_autism_exits": ([CFG.STRICT["a05_exit"]], None),
              "a27_counselling": ([CFG.A27["counselling"]], None), "a27_assisted_referral": ([CFG.A27["assisted_referral"]], None),
              "a28_primary": ([CFG.A28["primary"]], None), "a28_hospital": ([CFG.A28["hospital"]], None),
              "p2_tea_december": ([CFG.P2_TEA], 12), "p2_naneas_total_december": ([CFG.P2_NANEAS_TOTAL], 12),
              "a03_legacy_mchat_done": ([CFG.A03_LEGACY["mchat_done"]], None), "a03_legacy_mchat_altered": ([CFG.A03_LEGACY["mchat_altered"]], None)}
    for name, (codes, mo) in simple.items():
        s = D.national(codes, month=mo).set_index("year")
        for y, exp in CT[name].items():
            add(name, f"{'+'.join(codes)}|{'12' if mo else '01-12'}|{y}", exp, s.total.get(y, np.nan),
                "config.CONTROLS reproduced by this module's own aggregation of rem_pathway_tidy.csv")
    s = D.national([CFG.P2_TEA], month=12).set_index("year")
    for y, exp in CT["p2_establishments_december"].items():
        add("p2_establishments_december", f"{CFG.P2_TEA}|12|{y}", exp, s.n_est.get(y, np.nan), "distinct IdEstablecimiento with a December row")
    for name, pre, post in (("p6_primary_december", CFG.P6_BROAD_PRE2021["primary"], CFG.STRICT["p6_primary"]),
                            ("p6_specialty_december", CFG.P6_BROAD_PRE2021["specialty"], CFG.STRICT["p6_specialty"])):
        for y, exp in CT[name].items():
            code = pre if y <= 2020 else post
            add(name, f"{code}|12|{y}", exp, D.national([code], month=12).set_index("year").total.get(y, np.nan),
                "broad PDD 2019-2020 and strict autism 2021+ are separate definition eras")
    for y, (lo_, me_, hi_) in CT["a03_2023_low_medium_high"].items():
        for code, exp, lab in ((CFG.A03_2023_2024["low"], lo_, "low"), (CFG.A03_2023_2024["medium"], me_, "medium"), (CFG.A03_2023_2024["high"], hi_, "high")):
            add(f"a03_2023_low_medium_high_{lab}", f"{code}|01-12|{y}", exp, D.national([code], month=None).set_index("year").total.get(y, np.nan),
                "plotted in E12-A; COL01+COL02 cells present")

    # 2. Agregados propios frente a la tabla ya verificada rem_pathway_annual
    checks = [(CFG.STRICT["a05_entry"], "single_code", "annual_sum", None), (CFG.STRICT["a05_exit"], "single_code", "annual_sum", None),
              (CFG.A27["counselling"], "single_code", "annual_sum", None), (CFG.A28["primary"], "single_code", "annual_sum", None),
              (CFG.P2_TEA, "single_code", "december_stock", 12), (CFG.STRICT["p6_primary"], "single_code", "december_stock", 12),
              (CFG.STRICT["p6_specialty"], "single_code", "december_stock", 12)] + \
             [(c, "single_code", "annual_sum", None) for c in A03_ALL]
    for code, var, meas, mo in checks:
        ref = D.row(code, var, meas).set_index("year")
        own = D.national([code], month=mo).set_index("year")
        for y in ref.index:
            add("own_aggregate_vs_rem_pathway_annual", f"{code}|{meas}|{y}", ref.total.get(y), own.total.get(y, np.nan),
                "module aggregation of rem_pathway_tidy.csv must equal rem_pathway_annual.csv")
            add("own_establishments_vs_rem_pathway_annual", f"{code}|{meas}|{y}", ref.n_reporting_establishments.get(y), own.n_est.get(y, np.nan),
                "reporting establishments must equal rem_pathway_annual.csv")

    # 3. Suma regional = total nacional; suma mensual = total anual; suma por establecimiento = total anual
    for code, mo, label in ((CFG.STRICT["a05_entry"], None, "A05 strict entries"), (CFG.P2_TEA, 12, "P2 ASD December"),
                            (CFG.A27["counselling"], None, "A27 counselling"), (CFG.A28["primary"], None, "A28 primary rehabilitation"),
                            (CFG.STRICT["p6_primary"], 12, "P6 primary December")):
        nat = D.national([code], month=mo).set_index("year")
        reg = D.by_region([code], month=mo).groupby("year").total.sum(min_count=1)
        for y in nat.index:
            add("regional_sum_equals_national", f"{code}|{y}", nat.total.get(y), reg.get(y, np.nan), f"{label}: sum over the 16 regions")
    for code, label in ((CFG.STRICT["a05_entry"], "A05 strict entries"), (CFG.A03_LEGACY["mchat_done"], "A03 legacy M-CHAT done"),
                        (CFG.A28["primary"], "A28 primary rehabilitation")):
        nat = D.national([code]).set_index("year")
        mon = D.by_month([code]).groupby("year").total.sum(min_count=1)
        for y in nat.index:
            add("monthly_sum_equals_annual", f"{code}|{y}", nat.total.get(y), mon.get(y, np.nan), f"{label}: sum of the twelve months")
    for code, meas, mo, label in ((CFG.STRICT["a05_entry"], "annual_sum", None, "A05 strict entries"),
                                  (CFG.P2_TEA, "december_stock", 12, "P2 ASD December"),
                                  (CFG.STRICT["p6_primary"], "december_stock", 12, "P6 primary December")):
        nat = D.national([code], month=mo).set_index("year")
        est = D.by_establishment([code], meas).groupby("year").value.sum(min_count=1)
        for y in nat.index:
            add("establishment_sum_equals_annual", f"{code}|{meas}|{y}", nat.total.get(y), est.get(y, np.nan), f"{label}: sum over establishments")

    # 4. Panel estable
    ref = D.row(CFG.STRICT["a05_entry"]).set_index("year")
    e = D.est[D.est.code == CFG.STRICT["a05_entry"]]
    own = e[e.in_stable_panel].groupby("year").annual_total.sum(min_count=1)
    for y in ref.index:
        add("stable_panel_total", f"{CFG.STRICT['a05_entry']}|annual_sum|{y}", ref.stable_panel_total.get(y), own.get(y, np.nan),
            f"{int(ref.n_stable_panel_establishments.get(y, 0))} establishments reporting in every year of the era")

    # 5. Por variante: edad × sexo, tasas estandarizadas, Gini y supresión
    for variant, P in preps.items():
        E14 = P["e14"]
        ref = D.row(CFG.STRICT["a05_entry"]).set_index("year")
        mref = (D.models_asr[(D.models_asr.variant == "strict_autism") & (D.models_asr.sex.isin(["HOMBRE", "MUJER"]))]
                .groupby("year")["count"].sum()) if D.models_asr is not None else None
        for y in A05_YEARS:
            tot = float(np.nansum([E14["strict"][(y, sx)].sum() for sx in ("Hombres", "Mujeres") if (y, sx) in E14["strict"].columns]))
            if mref is not None:
                add(f"age_sex_cells_match_06_models[{variant}]", f"{CFG.STRICT['a05_entry']}|{y}", mref.get(y), tot,
                    "sum of the COL04-COL37 age x sex cells must equal the count used by module 06")
            add(f"age_sex_cells_minus_col01_total[{variant}]", f"{CFG.STRICT['a05_entry']}|{y}", None,
                tot - float(ref.total.get(y, np.nan)),
                "informative: age x sex cells minus the COL01 annual total; non-zero values are the rows already reported by module 02 "
                "as data_quality_a05_age_sum_mismatch (cells that do not add up to COL01); never corrected, never imputed")
        if D.models_asr is not None:
            for series, mv in (("strict", "strict_autism"), ("family", variant)):
                a = E14["rates"][E14["rates"].series == series][["year", "sex", "asr"]]
                b = D.models_asr[(D.models_asr.variant == mv) & (D.models_asr.sex.isin(["HOMBRE", "MUJER"]))][["year", "sex", "asr"]]
                m = a.merge(b, on=["year", "sex"], suffixes=("_14", "_06"))
                diff = float((m.asr_14 - m.asr_06).abs().max()) if len(m) else np.nan
                add(f"asr_matches_06_models[{variant}]", f"{series}|{mv}", 0.0, diff,
                    f"max |ASR(module 14) - ASR(module 06)| over {len(m)} year x sex cells (same WHO standard and INE base 2017)",
                    kind="abs_tol", tol=1e-9)
        E17 = P["e17"]
        bad = E17["summary"][(E17["summary"].gini < 0) | (E17["summary"].gini > 1)]
        add(f"gini_within_bounds[{variant}]", "all indicators", 0, len(bad), "Gini must lie in [0, 1]")
        for name_, key in (("e13_a05_regional", "e13"), ("e15_p2_regional", "e15")):
            add(f"suppressed_cells[{variant}]", name_, None, int(P[key]["sup"].to_numpy().sum()),
                "territorial cells with 1-4 events, shown as '<5' in the formatted table")
        add(f"suppressed_cells[{variant}]", "e16_a27_a28", None,
            int(sum(P["e16"][k]["sup"].to_numpy().sum() for k in P["e16"])), "territorial cells with 1-4 events across the four A27/A28 codes")
        add(f"not_reported_region_years[{variant}]", "e16_a27_a28", None,
            int(sum(P["e16"][k]["tot"].isna().to_numpy().sum() for k in P["e16"])), "region-years with no row at all (absence of reporting, never zero)")
        E19 = P["e19"]
        for key in [k for k, *_ in E19_INDICATORS]:
            s = E19["series"][key]
            for y in s["years2"]:
                fam, strict_ = s["family"].total.get(y, np.nan), s["strict"].total.get(y, np.nan)
                add(f"family_ge_strict[{variant}]", f"{key}|{y}", None, (fam - strict_) if pd.notna(fam) and pd.notna(strict_) else np.nan,
                    "the variant family total must be at least the strict-autism total; value is the excess")
    return pd.DataFrame(rows)


# ===========================================================================
# Ejecución
# ===========================================================================
PLATE_FUNCS = {"E11": plate_e11, "E12": plate_e12, "E13": plate_e13, "E14": plate_e14, "E15": plate_e15,
               "E16": plate_e16, "E17": plate_e17, "E18": plate_e18, "E19": plate_e19}


def build_prep(D: Data, variant: str) -> dict:
    t = time.time()
    P = {}
    P["e11"] = prep_e11(D)
    P["e12"] = prep_e12(D, P["e11"])
    P["e13"] = prep_e13(D, variant)
    P["e14"] = prep_e14(D, variant)
    P["e15"] = prep_e15(D, variant)
    P["e16"] = prep_e16(D)
    P["e17"] = prep_e17(D, variant)
    P["e18"] = prep_e18(D, variant)
    P["e19"] = prep_e19(D, variant)
    log(f"{variant}: agregados preparados en {time.time() - t:.1f} s")
    return P


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="*", default=VARIANTS)
    ap.add_argument("--langs", nargs="*", default=LANGS)
    ap.add_argument("--plates", nargs="*", default=list(PLATES))
    args = ap.parse_args(argv)

    D = Data()
    run = {"module": MODULE, "script": SCRIPT, "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "figures": [], "tables": [], "timings_s": {}}
    preps: dict[str, dict] = {}
    for variant in args.variants:
        preps[variant] = build_prep(D, variant)
        for lang in args.langs:
            for plate in args.plates:
                t = time.time()
                fpath, tpaths = PLATE_FUNCS[plate](D, preps[variant], variant, lang)
                dt = round(time.time() - t, 1)
                run["figures"].append(fpath)
                run["tables"].extend(tpaths)
                run["timings_s"][f"{variant}/{lang}/{plate}"] = dt
                log(f"{variant}/{lang} {plate}: {Path(fpath).name} + {len(tpaths)} archivos de tabla en {dt} s")
    ctrl = build_controls(D, preps)
    C.atomic_write_csv(ctrl, CONTROLS_DIR / f"{MODULE}_controls.csv")
    n_ok = int((ctrl.status == "ok").sum())
    n_diff = int((ctrl.status == "differs").sum())
    n_info = int((ctrl.status == "info").sum())
    run["controls"] = {"n_ok": n_ok, "n_differs": n_diff, "n_info": n_info, "path": str(CONTROLS_DIR / f"{MODULE}_controls.csv")}
    run["total_seconds"] = round(time.time() - T0, 1)
    C.atomic_write_json(run, CONTROLS_DIR / f"{MODULE}_run_log.json")
    log(f"controles: {n_ok} ok, {n_diff} difieren, {n_info} informativos; {len(run['figures'])} láminas y "
        f"{len(run['tables'])} archivos de tabla; tiempo total {run['total_seconds']} s")
    if n_diff:
        print(ctrl.loc[ctrl.status == "differs"].to_string(), flush=True)
    return 0 if n_diff == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
