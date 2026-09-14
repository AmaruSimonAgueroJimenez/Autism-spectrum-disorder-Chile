#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08b_figures_rem.py — Láminas de la ruta administrativa REM (F3 principal; S5, S6, S7, S8 y S13 suplementarias).

Entradas (outputs/tidy/): rem_pathway_annual.csv, rem_establishment_year.csv, rem_a05_age_sex_annual.csv,
rem_pathway_tidy.csv (mensual) e ine_population_region_national_year_age_sex.csv (base 2017, nacional).

Salidas, por variante (con_rett, sin_rett) e idioma (es, en), bajo outputs/<variante>/<idioma>/:
  figures/fig3_rem_pathway.png            F3  ruta administrativa: A03 por era, A27, A05, P2, P6 por era, A28
  figures/figS5_rem_june_december.png     S5  junio frente a diciembre en P2/P6 (nunca sumados)
  figures/figS6_rem_stable_panel.png      S6  panel estable frente a todos los establecimientos (A05, P2, P6)
  figures/figS7_a05_standardised_rates.png S7 A05 tasas brutas y estandarizadas por edad (OMS) por sexo, 2021–2025
  figures/figS8_a05_age_sex.png           S8  A05 ingresos por grupo de edad y sexo por año
  figures/figS13_rem_seasonality.png      S13 estacionalidad mensual (índice respecto de la media anual)
  figures/captions.json (fusionado)       tables/<nombre>.csv (+ _numeric) y tables/titles.json (fusionado)
Controles y registro: outputs/controls/08b_figures_rem_controls.csv y 08b_figures_rem_run_log.json.

Reglas respetadas: los conteos son reconocimiento administrativo (nunca prevalencia); cada era de definición REM va en
una faceta o segmento separado (ninguna línea cruza un quiebre); todo panel muestra el número de establecimientos
reportantes; Serie P usa diciembre (junio solo como sensibilidad; nunca se suman semestres); stocks y flujos nunca
comparten un eje; 2020–2021 se sombrean como disrupción del reporte y la Ley 21.545 se marca como contexto.
Ejecución: `python3 study/pipeline/08b_figures_rem.py` desde la raíz del repositorio.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402
from common import AGE_GROUPS, direct_standardization, poisson_limits  # noqa: E402
# El CUERPO del título de F3_rem_pathway_data nombra una lámina del artículo. El número no se escribe
# literal: se resuelve en el registro compartido (prose_en.MAIN_FIGURES), de modo que una renumeración
# del artículo no pueda dejar el título guardado apuntando a otra lámina.
from prose_en import main_figure_label  # noqa: E402

MODULE = "08b_figures_rem"
SCRIPT = "study/pipeline/08b_figures_rem.py"
VARIANTS = ["con_rett", "sin_rett"]
LANGS = CFG.LANGUAGES
PER = 100_000.0
Z = 1.959964
LAW_YEAR = CFG.LAW_YEAR
DISRUPTION = tuple(CFG.PANDEMIC_YEARS)
OK = C.OKABE
GREY, LIGHT, DARK = "#8c8c8c", "#d9d9d9", "#333333"
SEXCOL = {"HOMBRE": OK[0], "MUJER": OK[1], "TOTAL": DARK}
YEARCOL = {2019: "#9e9e9e", 2020: "#000000", 2021: OK[5], 2022: OK[0], 2023: OK[2], 2024: OK[4], 2025: OK[1]}
FAMILY_ALPHA = 0.45
T0 = time.time()
CONTROLS_DIR = CFG.OUT / "controls"  # config.CONTROLS es el diccionario de controles; la carpeta es outputs/controls


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Rótulos bilingües: todas las cadenas visibles en láminas, tablas y leyendas
# ---------------------------------------------------------------------------
LBL = {
    "figure": {"es": "Figura", "en": "Figure"}, "table": {"es": "Tabla", "en": "Table"},
    "year": {"es": "Año", "en": "Year"}, "month": {"es": "Mes", "en": "Month"},
    "var_con_rett": {"es": "F84 completo (con Rett)", "en": "Full F84 (with Rett)"},
    "var_sin_rett": {"es": "F84 sin Rett", "en": "F84 without Rett"},
    "variant_word": {"es": "variante", "en": "variant"},
    "HOMBRE": {"es": "Hombres", "en": "Males"}, "MUJER": {"es": "Mujeres", "en": "Females"}, "TOTAL": {"es": "Ambos sexos", "en": "Both sexes"},
    "n_estab": {"es": "n = establecimientos reportantes", "en": "n = reporting establishments"},
    "estab_axis": {"es": "Establecimientos reportantes (n)", "en": "Reporting establishments (n)"},
    "estab_short": {"es": "Establec. reportantes", "en": "Reporting establishments"},
    "pandemic": {"es": "Disrupción del\nreporte 2020–21", "en": "Reporting\ndisruption 2020–21"},
    "pandemic_one": {"es": "Disrupción\ndel reporte {y}", "en": "Reporting\ndisruption {y}"},
    "law": {"es": "Ley 21.545\n(contexto)", "en": "Law 21.545\n(context)"},
    "def_break": {"es": "quiebre de\ndefinición", "en": "definition\nbreak"},
    "months_abbr": {"es": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
                    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]},
    # unidades
    "u_screening": {"es": "Registros de tamizaje (flujo anual)", "en": "Screening records (annual flow)"},
    "u_children": {"es": "Niños/as o registros (flujo anual)", "en": "Children or records (annual flow)"},
    "u_interventions": {"es": "Intervenciones (flujo anual; no personas)", "en": "Interventions (annual flow; not persons)"},
    "u_entries": {"es": "Ingresos / altas clínicas (flujo anual)", "en": "Entries / clinical discharges (annual flow)"},
    "u_entries_only": {"es": "Ingresos (flujo anual)", "en": "Entries (annual flow)"},
    "u_stock": {"es": "Personas bajo control (stock)", "en": "People under control (stock)"},
    "u_stock_dec": {"es": "Personas bajo control en diciembre (stock)", "en": "People under control in December (stock)"},
    "u_rehab": {"es": "Ingresos a rehabilitación (flujo anual)", "en": "Rehabilitation entries (annual flow)"},
    "u_rate": {"es": "Ingresos por 100.000 habitantes (INE base 2017)", "en": "Entries per 100,000 population (INE base 2017)"},
    "u_index": {"es": "Índice mensual (media anual = 100)", "en": "Monthly index (annual mean = 100)"},
    "u_share": {"es": "% retenido por el panel estable", "en": "% retained by the stable panel"},
    "u_ratio_jd": {"es": "Razón junio / diciembre", "en": "June / December ratio"},
    "u_entries_count": {"es": "Ingresos reportados", "en": "Entries reported"},
    # F3
    "f3_a1": {"es": "2019–2022 · M-CHAT (03500406/07)", "en": "2019–2022 · M-CHAT (03500406/07)"},
    "f3_a2": {"es": "2023–2024 · M-CHAT-R/F (09600212–19)", "en": "2023–2024 · M-CHAT-R/F (09600212–19)"},
    "f3_a3": {"es": "2024 · 31–59 meses (03700104–09)", "en": "2024 · 31–59 months (03700104–09)"},
    "f3_a4": {"es": "2025 · rediseño (03710013–21)", "en": "2025 · redesign (03710013–21)"},
    "mchat_done": {"es": "M-CHAT realizado*", "en": "M-CHAT done*"},
    "mchat_altered": {"es": "M-CHAT alterado*", "en": "M-CHAT altered*"},
    # La nota va SIN salto de línea: el rótulo del eje de F3 (a) la imprime en una sola línea y el salto
    # que traía aquí se convertía en un ESPACIO, de modo que la lámina inglesa imprimía «language/ social
    # alteration» —espacio después de la barra y ninguno antes—, que es lo que se lee cuando una barra
    # queda a final de línea. Sin salto, el plegado por ancho medido de `plate_wrap` sólo puede partir
    # por un espacio real y «language/social» viaja entera.
    "legacy_note": {"es": "*en niños/as con alteración de lenguaje/área social",
                    "en": "*among children with language/social alteration"},
    "risk_low": {"es": "Riesgo bajo", "en": "Low risk"}, "risk_medium": {"es": "Riesgo medio", "en": "Medium risk"}, "risk_high": {"es": "Riesgo alto", "en": "High risk"},
    "risk_stack": {"es": "Resultado 1.ª parte", "en": "Part-1 result"},
    "ref_high": {"es": "Alto riesgo derivado", "en": "High risk referred"},
    "ref_second": {"es": "2.ª parte: derivación", "en": "Part 2: referral"},
    "c_03700104": {"es": "Evaluados en control integral", "en": "Evaluated at integral control"},
    "c_03700105": {"es": "Sospecha en otra instancia", "en": "Suspected elsewhere"},
    "c_03700106": {"es": "Señales de alerta: sí", "en": "Alert signs: yes"},
    "c_03700107": {"es": "Señales de alerta: no", "en": "Alert signs: no"},
    "c_03700108": {"es": "Derivación: sí", "en": "Referral: yes"},
    "c_03700109": {"es": "Derivación: no", "en": "Referral: no"},
    "c_03710013": {"es": "Motivo: EEDP alterado (16–30 m)", "en": "Motive: altered EEDP (16–30 mo)"},
    "c_03710014": {"es": "Motivo: riesgo/alerta (16–30 m)", "en": "Motive: risk/alert sign (16–30 mo)"},
    "c_03710015": {"es": "Motivo: ambos (16–30 m)", "en": "Motive: both (16–30 mo)"},
    "c_03710016": {"es": "Riesgo bajo", "en": "Low risk"},
    "c_03710017": {"es": "Riesgo medio, sin derivación", "en": "Medium risk, no referral"},
    "c_03710018": {"es": "Riesgo medio, derivación", "en": "Medium risk, referral"},
    "c_03710019": {"es": "Riesgo alto, derivación", "en": "High risk, referral"},
    "c_03710020": {"es": "Sospecha 30–59 m, sin derivación", "en": "Suspected 30–59 mo, no referral"},
    "c_03710021": {"es": "Sospecha 30–59 m, derivación", "en": "Suspected 30–59 mo, referral"},
    "n_done_alt": {"es": "n = establec. realizado / alterado", "en": "n = estab. done / altered"},
    "s_03700104": {"es": "Evaluados", "en": "Evaluated"}, "s_03700105": {"es": "Sospecha otra instancia", "en": "Suspected elsewhere"},
    "s_03700106": {"es": "Alerta: sí", "en": "Alert signs: yes"}, "s_03700107": {"es": "Alerta: no", "en": "Alert signs: no"},
    "s_03700108": {"es": "Derivación: sí", "en": "Referral: yes"}, "s_03700109": {"es": "Derivación: no", "en": "Referral: no"},
    "s_03710013": {"es": "Motivo: EEDP", "en": "Motive: EEDP"}, "s_03710014": {"es": "Motivo: riesgo/alerta", "en": "Motive: risk/alert"}, "s_03710015": {"es": "Motivo: ambos", "en": "Motive: both"},
    "s_03710016": {"es": "Riesgo bajo", "en": "Low risk"}, "s_03710017": {"es": "Medio, sin deriv.", "en": "Medium, no ref."}, "s_03710018": {"es": "Medio, deriv.", "en": "Medium, ref."},
    "s_03710019": {"es": "Alto, deriv.", "en": "High, ref."}, "s_03710020": {"es": "30–59 m, sin deriv.", "en": "30–59 mo, no ref."}, "s_03710021": {"es": "30–59 m, deriv.", "en": "30–59 mo, ref."},
    "f3_b": {"es": "A27 consejería y referencia asistida (M-CHAT-R/F)", "en": "A27 counselling and assisted referral (M-CHAT-R/F)"},
    "f3_title_a": {"es": "A03: M-CHAT y M-CHAT-R/F", "en": "A03: M-CHAT and M-CHAT-R/F"},
    "f3_title_b": {"es": "A03: 2024 y rediseño 2025", "en": "A03: 2024 and 2025 redesign"},
    "f3_title_c": {"es": "A27 y A28, 2023–2025", "en": "A27 and A28, 2023–2025"},
    "f3_title_d": {"es": "A05 ingresos y altas", "en": "A05 entries and discharges"},
    "f3_title_e": {"es": "P2 NANEAS con TEA (dic.)", "en": "P2 NANEAS with ASD (Dec.)"},
    "f3_title_f": {"es": "P6 bajo control en diciembre", "en": "P6 under control in December"},
    "c_09600212": {"es": "Sospecha en otra instancia", "en": "Suspected elsewhere"},
    "c_09600217": {"es": "2.ª parte: riesgo medio", "en": "Part 2: medium risk"},
    "c_09600218": {"es": "2.ª parte: sin derivación", "en": "Part 2: no referral"},
    "counselling": {"es": "Consejería", "en": "Counselling"}, "assisted_referral": {"es": "Referencia asistida", "en": "Assisted referral"},
    "codes_2023": {"es": "códigos desde 2023", "en": "codes from 2023"},
    "f3_c0": {"es": "2019–20:\nTGD amplio", "en": "2019–20:\nbroad PDD"},
    "f3_c1": {"es": "A05 ingresos y altas por autismo,\n2021–2025", "en": "A05 autism entries and discharges,\n2021–2025"},
    "entries_strict": {"es": "Ingresos: autismo estricto", "en": "Entries: strict autism"},
    "exits_strict": {"es": "Altas clínicas: autismo estricto", "en": "Clinical discharges: strict autism"},
    "entries_family": {"es": "Ingresos: familia TGD", "en": "Entries: PDD family"},
    "exits_family": {"es": "Altas: familia TGD", "en": "Discharges: PDD family"},
    "entries_broad": {"es": "Ingresos TGD amplio", "en": "Broad PDD entries"},
    "exits_broad": {"es": "Altas TGD amplio", "en": "Broad PDD discharges"},
    "n_strict": {"es": "n establec. reportantes", "en": "n reporting establishments"},
    "n_family": {"es": "n establec. (familia TGD)", "en": "n establishments (PDD family)"},
    "n_broad": {"es": "n establec. (TGD amplio)", "en": "n establishments (broad PDD)"},
    "f3_d": {"es": "P2 NANEAS con TEA bajo control", "en": "P2 NANEAS with ASD under control"},
    "dec_stock": {"es": "Stock de diciembre", "en": "December stock"},
    "jun_stock": {"es": "Stock de junio (sensibilidad)", "en": "June stock (sensitivity)"},
    "n_dec": {"es": "n establec., dic.", "en": "n establishments, Dec."},
    "n_jun": {"es": "n establec., jun.", "en": "n establishments, Jun."},
    "per100_naneas": {"es": "TEA por 100 NANEAS (dic.)", "en": "ASD per 100 NANEAS (Dec.)"},
    "f3_e0": {"es": "2019–20:\nTGD amplio", "en": "2019–20:\nbroad PDD"},
    "f3_e1": {"es": "P6 bajo control en diciembre,\n2021–2025", "en": "P6 under control in December,\n2021–2025"},
    "primary_strict": {"es": "APS: autismo estricto", "en": "Primary care: strict autism"},
    "specialty_strict": {"es": "Especialidad: autismo estricto", "en": "Specialty: strict autism"},
    "primary_family": {"es": "APS: familia TGD", "en": "Primary care: PDD family"},
    "specialty_family": {"es": "Especialidad: familia TGD", "en": "Specialty: PDD family"},
    "primary_broad": {"es": "APS: TGD amplio", "en": "Primary care: broad PDD"},
    "specialty_broad": {"es": "Especialidad: TGD amplio", "en": "Specialty: broad PDD"},
    "f3_f": {"es": "A28 ingresos a rehabilitación por TEA", "en": "A28 rehabilitation entries for ASD"},
    "rehab_primary": {"es": "Rehabilitación en APS", "en": "Primary-level rehabilitation"},
    "rehab_hospital": {"es": "Rehabilitación hospitalaria", "en": "Hospital-level rehabilitation"},
    # S5
    "s5_a": {"es": "P2 TEA: junio frente a diciembre", "en": "P2 ASD: June versus December"},
    "s5_b": {"es": "P6 APS: junio frente a diciembre", "en": "P6 primary care: June versus December"},
    "s5_c": {"es": "P6 especialidad: junio frente a diciembre", "en": "P6 specialty: June versus December"},
    "s5_d": {"es": "Razón junio/diciembre: stocks y establecimientos", "en": "June/December ratio: stocks and establishments"},
    "s5_e": {"es": "P2 TEA por establecimiento: junio frente a diciembre", "en": "P2 ASD by establishment: June versus December"},
    "s5_f": {"es": "Patrón semestral de reporte por establecimiento", "en": "Semester reporting pattern by establishment"},
    "june": {"es": "Junio", "en": "June"}, "december": {"es": "Diciembre", "en": "December"},
    "family_dec": {"es": "Familia TGD, diciembre", "en": "PDD family, December"},
    "family_jun": {"es": "Familia TGD, junio", "en": "PDD family, June"},
    "broad_label": {"es": "TGD amplio 2019–20", "en": "Broad PDD 2019–20"},
    "ratio_stock": {"es": "stock", "en": "stock"}, "ratio_estab": {"es": "establecimientos", "en": "establishments"},
    "p2_short": {"es": "P2 TEA", "en": "P2 ASD"}, "p6p_short": {"es": "P6 APS", "en": "P6 primary"}, "p6s_short": {"es": "P6 especialidad", "en": "P6 specialty"},
    "june_axis": {"es": "Stock de junio + 1 (escala log)", "en": "June stock + 1 (log scale)"},
    "dec_axis": {"es": "Stock de diciembre + 1 (escala log)", "en": "December stock + 1 (log scale)"},
    "identity": {"es": "junio = diciembre", "en": "June = December"},
    "both_sem": {"es": "Ambos semestres", "en": "Both semesters"}, "dec_only": {"es": "Solo diciembre", "en": "December only"}, "jun_only": {"es": "Solo junio", "en": "June only"},
    "estab_count": {"es": "Establecimientos con fila (n)", "en": "Establishments with a row (n)"},
    "both_n": {"es": "ambos", "en": "both"}, "dec_n": {"es": "solo dic.", "en": "Dec. only"}, "jun_n": {"es": "solo jun.", "en": "June only"},
    # S6
    "s6_a": {"es": "A05 ingresos: autismo estricto", "en": "A05 entries: strict autism"},
    "s6_b": {"es": "A05 ingresos: familia TGD de la variante", "en": "A05 entries: variant PDD family"},
    "s6_c": {"es": "P2 TEA, diciembre", "en": "P2 ASD, December"},
    "s6_d": {"es": "P6 APS, diciembre", "en": "P6 primary care, December"},
    "s6_e": {"es": "P6 especialidad, diciembre", "en": "P6 specialty, December"},
    "s6_f": {"es": "Retención del panel estable: volumen y establecimientos", "en": "Stable-panel retention: volume and establishments"},
    "all_estab": {"es": "Todos los establecimientos", "en": "All establishments"},
    "stable_panel": {"es": "Panel estable", "en": "Stable panel"},
    "share_vol": {"es": "% del volumen retenido", "en": "% of volume retained"},
    "share_est": {"es": "% de establecimientos en el panel", "en": "% of establishments in the panel"},
    "stable_def": {"es": "panel estable = establecimientos con fila del código en cada año de su era", "en": "stable panel = establishments with a row for the code in every year of its era"},
    "a05_strict_short": {"es": "A05 autismo estricto", "en": "A05 strict autism"},
    "a05_family_short": {"es": "A05 familia TGD", "en": "A05 PDD family"},
    "n_all_stable": {"es": "n todos / panel", "en": "n all / panel"},
    # S7
    "s7_a": {"es": "Autismo estricto (05990022): tasas por sexo", "en": "Strict autism (05990022): rates by sex"},
    "s7_b": {"es": "Familia TGD de la variante: tasas por sexo", "en": "Variant PDD family: rates by sex"},
    "s7_c": {"es": "Razón hombre:mujer de las tasas estandarizadas", "en": "Male:female ratio of standardised rates"},
    "s7_d": {"es": "Autismo estricto por edad y sexo, 2021 y 2025", "en": "Strict autism by age and sex, 2021 and 2025"},
    "s7_e": {"es": "Autismo estricto por edad, ambos sexos, por año", "en": "Strict autism by age, both sexes, by year"},
    "u_rate_log": {"es": "Ingresos por 100.000 hab. (INE 2017; escala log.)", "en": "Entries per 100,000 pop. (INE 2017; log scale)"},
    "s7_f": {"es": "TGD amplio 2019–2020 (definición distinta)", "en": "Broad PDD 2019–2020 (different definition)"},
    "crude": {"es": "bruta", "en": "crude"}, "asr": {"es": "estandarizada (OMS)", "en": "standardised (WHO)"},
    "age_axis": {"es": "Grupo de edad (años)", "en": "Age group (years)"},
    "ratio_axis": {"es": "Razón H:M de tasas estandarizadas (IC 95 %)", "en": "M:F ratio of standardised rates (95% CI)"},
    "strict_short": {"es": "Autismo estricto", "en": "Strict autism"}, "family_short": {"es": "Familia TGD", "en": "PDD family"},
    "log_axis": {"es": "(escala log.)", "en": "(log scale)"},
    # S8
    "s8_a": {"es": "Autismo estricto: ingresos, hombres", "en": "Strict autism: entries, males"},
    "s8_b": {"es": "Autismo estricto: ingresos, mujeres", "en": "Strict autism: entries, females"},
    "s8_c": {"es": "Autismo estricto: distribución por edad (%)", "en": "Strict autism: age distribution (%)"},
    "s8_d": {"es": "Autismo estricto: razón H:M de ingresos por edad", "en": "Strict autism: M:F ratio of entries by age"},
    "s8_e": {"es": "Familia TGD: ingresos, hombres", "en": "PDD family: entries, males"},
    "s8_f": {"es": "Familia TGD: ingresos, mujeres", "en": "PDD family: entries, females"},
    "share_axis": {"es": "% de los ingresos del año", "en": "% of the year's entries"},
    "mf_axis": {"es": "Razón H:M de ingresos (IC 95 %)", "en": "M:F ratio of entries (95% CI)"},
    "age_50plus": {"es": "50+", "en": "50+"}, "age_30plus": {"es": "30+", "en": "30+"},
    "cell_absent": {"es": "celda ausente", "en": "cell absent"},
    # S13
    "s13_a": {"es": "A05 ingresos por autismo estricto", "en": "A05 strict-autism entries"},
    "s13_b": {"es": "A05 ingresos familia TGD (variante)", "en": "A05 PDD-family entries (variant)"},
    "s13_c": {"es": "A05 ingresos TGD amplio 2019–2020", "en": "A05 broad PDD entries 2019–2020"},
    "s13_d": {"es": "A03 M-CHAT realizado (legado) 2019–2022", "en": "A03 legacy M-CHAT done 2019–2022"},
    "s13_e": {"es": "A03 resultados M-CHAT-R/F (1.ª parte) por era", "en": "A03 M-CHAT-R/F results (part 1) by era"},
    "s13_f": {"es": "A05 ingresos: establecimientos con fila por mes", "en": "A05 entries: establishments with a row by month"},
    "era_2023": {"es": "era 2023–24", "en": "2023–24 era"}, "era_2025": {"es": "era 2025", "en": "2025 era"},
    "annual_mean": {"es": "media anual = 100", "en": "annual mean = 100"},
    "feb2019_note": {"es": "feb. 2019: 1.051 registros\n(valor atípico del archivo)", "en": "Feb 2019: 1,051 records\n(outlying file value)"},
    "estab_month_axis": {"es": "Establecimientos con fila en el mes (n)", "en": "Establishments with a row in the month (n)"},
    "broad_dashed": {"es": "TGD amplio (línea discontinua)", "en": "broad PDD (dashed)"},
    "ser_a05_strict": {"es": "A05 ingresos autismo estricto", "en": "A05 strict-autism entries"},
    "ser_a05_family": {"es": "A05 ingresos familia TGD (variante)", "en": "A05 PDD-family entries (variant)"},
    "ser_a05_broad": {"es": "A05 ingresos TGD amplio", "en": "A05 broad-PDD entries"},
    "ser_a03_legacy_done": {"es": "A03 M-CHAT realizado (legado)", "en": "A03 legacy M-CHAT done"},
    "ser_a03_mchat_rf_part1": {"es": "A03 M-CHAT-R/F resultados 1.ª parte", "en": "A03 M-CHAT-R/F part-1 results"},
    "ser_a05_broad_estab": {"es": "A05 TGD amplio: establecimientos con fila", "en": "A05 broad PDD: establishments with a row"},
    "ser_a05_strict_estab": {"es": "A05 autismo estricto: establecimientos con fila", "en": "A05 strict autism: establishments with a row"},
    # tablas
    "t_panel": {"es": "Panel", "en": "Panel"}, "t_series": {"es": "Serie", "en": "Series"}, "t_code": {"es": "Código", "en": "Code"},
    "t_era": {"es": "Era de definición", "en": "Definition era"}, "t_measure": {"es": "Medida", "en": "Measure"},
    "t_unit": {"es": "Unidad", "en": "Unit"}, "t_value": {"es": "Valor", "en": "Value"},
    "t_n_est": {"es": "Establecimientos reportantes", "en": "Reporting establishments"},
    "t_n_stable": {"es": "Establecimientos del panel estable", "en": "Stable-panel establishments"},
    "t_stable_total": {"es": "Total del panel estable", "en": "Stable-panel total"},
    "t_share_vol": {"es": "% volumen retenido", "en": "% volume retained"}, "t_share_est": {"es": "% establecimientos retenidos", "en": "% establishments retained"},
    "t_june": {"es": "Junio (stock)", "en": "June (stock)"}, "t_dec": {"es": "Diciembre (stock)", "en": "December (stock)"},
    "t_n_june": {"es": "Establec. junio", "en": "Estab. June"}, "t_n_dec": {"es": "Establec. diciembre", "en": "Estab. December"},
    "t_ratio": {"es": "Razón junio/diciembre", "en": "June/December ratio"},
    "t_sex": {"es": "Sexo", "en": "Sex"}, "t_count": {"es": "Ingresos (suma de celdas edad × sexo)", "en": "Entries (sum of age × sex cells)"},
    "t_pop": {"es": "Población INE", "en": "INE population"}, "t_crude": {"es": "Tasa bruta por 100.000 (IC 95 %)", "en": "Crude rate per 100,000 (95% CI)"},
    "t_asr": {"es": "Tasa estandarizada OMS por 100.000 (IC 95 %)", "en": "WHO-standardised rate per 100,000 (95% CI)"},
    "t_age": {"es": "Grupo de edad", "en": "Age group"}, "t_month": {"es": "Mes", "en": "Month"}, "t_index": {"es": "Índice (media anual = 100)", "en": "Index (annual mean = 100)"},
    "t_total": {"es": "Total del mes", "en": "Month total"},
    # Un solo marcador de celda sin valor en todo el estudio: «n/e». Este módulo escribía «n/d» en español y
    # «n/a» en inglés, de modo que los documentos llegaban con tres marcadores para lo mismo (86 celdas por
    # documento) mientras los otros nueve módulos escriben «n/e». El marcador se GLOSA allí donde se usa: la
    # ausencia de fila y el cero son estados distintos y la nota lo dice con palabras.
    "na": {"es": "n/e", "en": "n/e"}, "absent": {"es": "no reportado", "en": "not reported"},
    "unit_screening records": {"es": "registros de tamizaje", "en": "screening records"}, "unit_children reported": {"es": "niños/as reportados", "en": "children reported"},
    "unit_screening results": {"es": "resultados de tamizaje", "en": "screening results"}, "unit_referral records": {"es": "registros de derivación", "en": "referral records"},
    "unit_entries reported": {"es": "ingresos reportados", "en": "entries reported"}, "unit_exits reported": {"es": "altas clínicas reportadas", "en": "clinical discharges reported"},
    "unit_interventions": {"es": "intervenciones", "en": "interventions"}, "unit_people in stock": {"es": "personas bajo control (stock)", "en": "people under control (stock)"},
    "meas_annual_sum": {"es": "suma anual de meses (flujo)", "en": "annual sum of months (flow)"}, "meas_december_stock": {"es": "stock de diciembre", "en": "December stock"},
    "meas_june_stock": {"es": "stock de junio (sensibilidad)", "en": "June stock (sensitivity)"},
    "t_n_est_month": {"es": "Establecimientos con fila en el mes", "en": "Establishments with a row in the month"},
    "t_n_est_year": {"es": "Establecimientos reportantes en el año", "en": "Reporting establishments in the year"},
    "m_broad": {"es": "TGD amplio", "en": "broad PDD"}, "m_strict": {"es": "autismo estricto", "en": "strict autism"}, "m_family": {"es": "familia TGD", "en": "PDD family"},
    "m_primary": {"es": "APS", "en": "primary care"}, "m_specialty": {"es": "especialidad", "en": "specialty"},
    "m_entries": {"es": "ingresos", "en": "entries"}, "m_exits": {"es": "altas clínicas", "en": "clinical discharges"},
}


def tr(key: str, lang: str) -> str:
    return LBL[key][lang]


def tr_unit(u: str, lang: str) -> str:
    return LBL.get(f"unit_{u}", {}).get(lang, str(u))


def tr_measure(m: str, lang: str) -> str:
    return LBL.get(f"meas_{m}", {}).get(lang, str(m))


#: EL SIGNO NEGATIVO Y EL SIGNO DE PORCENTAJE, las dos convenciones que estas láminas escriben con cifras.
#:
#: El NEGATIVO lleva el menos tipográfico (U+2212), no el guion ASCII: el guion mide 2,9 pt a 8 pt de
#: cuerpo y se dibuja a la altura de la x, mientras la raya de intervalo que estas láminas usan para los
#: rangos («n 460–1.325») mide 4,1 pt, de modo que los dos trazos se confunden en un rótulo de 6 pt. La
#: regla NO se repite aquí: vive en `common.fmt_number` (y por tanto también en `common.fmt_ci`), y este
#: módulo la hereda porque TODA cifra que imprime pasa por `_n` o `_ci` —rótulos de valor, notas, títulos,
#: leyendas y las marcas de eje de `localise_ticks`, `_fmt_y` y `_log_x`—. Lo que este módulo sí garantiza
#: es que no haya atajos: ningún rótulo de lámina se formatea a mano (los únicos formatos crudos que
#: quedan son los años de dos cifras «’19», que nunca son negativos, y las líneas de consola).
#:
#: El PORCENTAJE se escribe «12,3 %» en español y «12.3%» en inglés. Esa regla todavía no está en `common`
#: —la escriben nueve módulos por su cuenta— y aquí la aplica `_pct`.


def _n(x, dec=0, lang="es"):
    return C.fmt_number(x, dec, lang)


def _pct(x, lang="es", dec=1):
    """Porcentaje en la convención del idioma: «12,3 %» en español (espacio) y «12.3%» en inglés (pegado).

    Dos sitios de este módulo escribían a mano el sufijo « %» sin mirar el idioma, de modo que las
    láminas INGLESAS imprimían «76 %» dentro de un corpus que escribe «76%»: el rótulo de retención del
    ayudante `panel()` de la S6 —que dibuja CINCO de sus seis celdas, (a) a (e), no sólo la (b)— y el
    rótulo de participación por banda de edad de la S8 (c)."""
    return _n(x, dec, lang) + (" %" if lang == "es" else "%")


def _ci(lo, hi, dec=1, lang="es"):
    return C.fmt_ci(lo, hi, dec, lang)


def vlab(variant: str, lang: str) -> str:
    return tr(f"var_{variant}", lang)


# ---------------------------------------------------------------------------
# Utilidades de salida
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


def write_table(variant: str, lang: str, name: str, formatted: pd.DataFrame, numeric: pd.DataFrame | None, title: str, note: str) -> list[str]:
    tdir = out_dir(variant, lang, "tables")
    paths = [str(C.atomic_write_csv(formatted, tdir / f"{name}.csv"))]
    if numeric is not None:
        paths.append(str(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv")))
    merge_json(tdir / "titles.json", {name: {"title": title, "note": note}})
    return paths


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
class Data:
    def __init__(self):
        t = time.time()
        self.rem = C.read_tidy("rem_pathway_annual", dtype={"code": str, "month": str})
        self.est = C.read_tidy("rem_establishment_year", dtype={"code": str, "IdEstablecimiento": str},
                               usecols=["year", "series", "module", "code", "IdEstablecimiento", "december_value", "june_value",
                                        "has_december_row", "has_june_row", "in_stable_panel", "annual_total"], low_memory=False)
        self.age = C.read_tidy("rem_a05_age_sex_annual", dtype={"code": str})
        self.tidy = C.read_tidy("rem_pathway_tidy", dtype={"code": str, "IdEstablecimiento": str},
                                usecols=["year", "series", "module", "code", "IdEstablecimiento", "month", "in_era", "total_known", "state"], low_memory=False)
        ine = C.read_tidy("ine_population_region_national_year_age_sex")
        self.ine = ine[ine.level == "national"].copy()
        self.models_asr = None
        p = CFG.TIDY / "models_a05_standardised_rates.csv"
        if p.is_file():
            self.models_asr = pd.read_csv(p)
        log(f"datos cargados en {time.time() - t:.1f} s: rem_pathway_annual {len(self.rem)} filas; establecimiento-año {len(self.est)}; "
            f"edad-sexo {len(self.age)}; tidy mensual {len(self.tidy)}; INE nacional {len(self.ine)}")

    # --- filas anuales ---------------------------------------------------
    def row(self, code: str, variant: str = "single_code", measure: str = "annual_sum") -> pd.DataFrame:
        r = self.rem[(self.rem.code == code) & (self.rem.variant == variant) & (self.rem.measure == measure)].sort_values("year")
        if r.empty:
            raise KeyError(f"sin filas para {code} / {variant} / {measure}")
        return r.reset_index(drop=True)

    def family_code(self, variant: str, key: str) -> str:
        return "+".join(CFG.VARIANTS[variant][key])

    def family(self, variant: str, key: str, measure: str = "annual_sum") -> pd.DataFrame:
        return self.row(self.family_code(variant, key), variant, measure)

    # --- series mensuales -------------------------------------------------
    def monthly(self, codes: list[str], years: list[int] | None = None) -> pd.DataFrame:
        t = self.tidy[self.tidy.code.isin(codes) & self.tidy.in_era]
        if years is not None:
            t = t[t.year.isin(years)]
        g = t.groupby(["year", "month"]).agg(total=("total_known", "sum"), n_est=("IdEstablecimiento", "nunique"), n_rows=("total_known", "size")).reset_index()
        grid = pd.MultiIndex.from_product([sorted(t.year.unique()), range(1, 13)], names=["year", "month"]).to_frame(index=False)
        g = grid.merge(g, on=["year", "month"], how="left")   # meses sin fila = NaN (no reportado), nunca cero
        g["index"] = g.groupby("year")["total"].transform(lambda s: 100 * s / s.mean())
        n_year = t.groupby("year")["IdEstablecimiento"].nunique()
        g["n_year"] = g.year.map(n_year)   # establecimientos con al menos una fila en el año (igual que rem_pathway_annual)
        return g


# ---------------------------------------------------------------------------
# Norma de lámina: 180 × 245 mm en vertical, dibujada 1:1 (una lámina por página, sin reducción)
# 3 filas × 2 columnas, seis paneles como máximo, letras minúsculas, nada bajo 6 pt, 600 dpi.
# ---------------------------------------------------------------------------
PLATE_W_MM, PLATE_H_MM = 180.0, 245.0
MM_PER_IN = 25.4
PLATE_SIZE = (PLATE_W_MM / MM_PER_IN, PLATE_H_MM / MM_PER_IN)
FS_BASE, FS_TITLE, FS_TICK, FS_LEG, FS_MIN = 8.0, 9.0, 7.0, 7.0, 6.0
PLATE_TITLE_CHARS = 33
# Ancho útil del título en una celda de la rejilla (media lámina menos 4 mm) y del texto dentro de los ejes.
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


def new_plate(plt, nrows: int = 3, ncols: int = 2, **kw):
    fig, ax = plt.subplots(nrows, ncols, figsize=PLATE_SIZE, constrained_layout=True, **kw)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05, hspace=0.06)
    return fig, ax


def panel_head(ax, letter_: str, title: str, fs: float = FS_TITLE, pad: float = 3.0, chars: int | None = None, dx: float = 0.0) -> None:
    """Cabecera del panel: letra minúscula y título a la izquierda de SU celda, plegados al ancho de la celda.

    El plegado es por ancho MEDIDO y no por número de caracteres: contando caracteres, los títulos largos en
    español desbordaban la celda y se cortaban contra el borde derecho del lienzo. `chars` y `dx` se conservan
    por compatibilidad con las llamadas antiguas; `C.plate_align_titles` reancla el título a la celda al guardar.
    """
    # matplotlib guarda TRES artistas de título (izquierda, centro, derecha): si un ayudante ya puso el
    # título centrado, escribir el de la izquierda dejaría los dos impresos, uno encima del otro.
    ax.set_title("", loc="center"); ax.set_title("", loc="right")
    ax.set_title(C.plate_wrap(f"({letter_}) {title}", PLATE_TITLE_W_PT, fs, "bold"),
                 loc="left", x=dx, fontsize=fs, fontweight="bold", pad=pad, linespacing=1.15)


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
            axis.set_major_formatter(FuncFormatter(lambda v, _p, dec=dec, lang=lang: _n(v, dec, lang)))


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
    """Guarda sin recorte: el archivo mide exactamente 180 × 245 mm a 600 dpi (1:1 en la página)."""
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
    # Modo revista (PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    fig.savefig(path, dpi=dpi, facecolor="white")
    return path


YEARS = CFG.YEARS_REM
YEAR_SHADE = {y: c for y, c in zip(range(2019, 2026), ["#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"])}


def _fmt_y(ax, lang, dec: int = 0):
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, q: _n(v, dec, lang)))


def _ends_only(years, values, labels, which: str = "both"):
    """Primer y último punto de una serie: los intermedios se leen en la tabla de respaldo de la lámina.

    En una celda de 90 mm siete rótulos de valor sobre una misma serie no caben: dos de ellos («1.854» y
    «1.919», a 65 unidades de distancia en un eje de 44.000) acababan impresos bajo el eje, montados sobre
    las marcas de año. La lámina rotula los extremos, que es lo que da la magnitud, y la tabla F3 (datos)
    lleva TODOS los valores dibujados."""
    years = list(years); values = list(values); labels = list(labels)
    if not years:
        return years, values, labels
    keep_idx = [len(years) - 1] if which == "last" else sorted({0, len(years) - 1})
    return ([years[i] for i in keep_idx], [values[i] for i in keep_idx], [labels[i] for i in keep_idx])


def _era_break(ax, lang, x: float, y: float = 0.985):
    """Quiebre de definición dentro de un mismo eje: línea vertical y rótulo vertical; ninguna serie lo cruza.

    `y` permite bajar el rótulo cuando la parte alta del panel la ocupa la leyenda: en el panel A05 de la
    Figura 4 el rótulo girado quedaba detrás de ella y se leía «…tion break»."""
    ax.axvline(x, color="#999999", ls="-.", lw=0.9, zorder=1)
    t = ax.text(x - 0.06, y, tr("def_break", lang).replace("\n", " "), transform=ax.get_xaxis_transform(),
                ha="right", va="top", rotation=90, fontsize=FS_MIN, color="#777777")
    t.set_gid(C.PLATE_KEEP)          # posición deliberada: junto a SU línea de quiebre


# ---------------------------------------------------------------------------
# Ayudantes gráficos
# ---------------------------------------------------------------------------
def _context(ax, lang, shade=DISRUPTION, law=True, pandemic_pos=0.97, law_pos=0.97, pandemic_text=True, law_va="top", pandemic_va="top", law_x_offset=0.06, fs=7, law_text=True, pandemic_x_offset=0.0):
    """Sombrea los años de disrupción visibles y marca la Ley 21.545 como contexto (nunca como intervención).

    Los dos rótulos se marcan como INAMOVIBLES: el motor de descongestión reubica cualquier nota de panel al
    hueco más vacío de los nueve anclajes estándar, y en estos paneles el hueco de verdad está en una banda
    intermedia que no es ninguno de los nueve; movido allí, el rótulo de la pandemia acababa sobre el del
    quiebre de definición o sobre una serie."""
    xlo, xhi = ax.get_xlim()
    yrs = [y for y in shade if xlo < y < xhi]
    if yrs:
        C.shade_years(ax, yrs)
        if pandemic_text:
            txt = tr("pandemic", lang) if len(yrs) == 2 else tr("pandemic_one", lang).format(y=yrs[0])
            t = ax.text(float(np.mean(yrs)) + pandemic_x_offset, pandemic_pos, txt, transform=ax.get_xaxis_transform(), ha="center", va=pandemic_va, fontsize=fs, color="#555555", linespacing=1.15)
            t.set_gid(C.PLATE_KEEP)
    if law and xlo < LAW_YEAR - 0.35 < xhi:
        x = LAW_YEAR - 0.35
        ax.axvline(x, color="#444444", ls=":", lw=1.2, zorder=1)
        if law_text:
            t = ax.text(x + law_x_offset, law_pos, tr("law", lang), transform=ax.get_xaxis_transform(), ha="left", va=law_va, fontsize=fs, color="#444444", linespacing=1.15)
            t.set_gid(C.PLATE_KEEP)


def _ann(ax, x, y, text, color=DARK, fs=6.5, dy=2, ha="center", va=None, rotation=0, dx=0, bbox=False):
    """Anotación con desplazamiento en puntos; `bbox=True` añade un fondo blanco translúcido para que el texto no se pierda sobre líneas o barras."""
    va = va or ("bottom" if dy >= 0 else "top")
    kw = dict(bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8)) if bbox else {}
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va, fontsize=fs, color=color, rotation=rotation, zorder=6, **kw)


def _letter(ax, ch, dx=-0.09, dy=1.12):
    C.letter(ax, ch, dx=dx, dy=dy)


def _hollow(color):
    return dict(marker="o", mfc="white", mec=color, mew=1.6, ms=6.5, ls="none")


def _facet_title(ax, text, fs=8.5):
    ax.set_title(text, fontsize=fs, fontweight="bold")


def _break_marker(ax, x, lang, y=0.5):
    ax.axvline(x, color="#999999", ls="-.", lw=1.0, zorder=1)
    t = ax.text(x, y, tr("def_break", lang), transform=ax.get_xaxis_transform(), ha="center", va="center", fontsize=6.5, color="#777777",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    t.set_gid(C.PLATE_KEEP)          # posición deliberada: junto a SU línea de quiebre


# ===========================================================================
# F3 · Ruta administrativa REM
# ===========================================================================
def _dot_rows(ax, D, rows, lang, keep, panel, xmax_pad=2.6):
    """Filas de un gráfico de puntos: una fila por código, un punto por año (color = año, escala logarítmica).

    Cada era de definición va en su propio bloque con encabezado; ninguna línea une puntos de eras distintas.
    El rótulo de la fila lleva el número de establecimientos reportantes (n) del código, como exige la regla REM.
    """
    labels, y = [], 0
    ticks, ticklabels = [], []
    for kind, payload in rows:
        if kind == "header":
            ax.text(0.0, y, payload, transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=FS_MIN, fontweight="bold", color="#333333")
            ticks.append(y); ticklabels.append("")
            y -= 1
            continue
        code, name, colr = payload
        r = D.row(code)
        ns = r.n_reporting_establishments
        n_txt = f"n {_n(ns.min(), 0, lang)}–{_n(ns.max(), 0, lang)}" if ns.min() != ns.max() else f"n {_n(ns.iloc[0], 0, lang)}"
        for t in r.itertuples():
            ax.scatter(t.total, y, s=15, color=YEAR_SHADE[int(t.year)], edgecolor="#333333", linewidth=0.35, zorder=3)
            keep(panel, name, t.code, t.era, "annual_sum", t.year, t.total, t.unit, t.n_reporting_establishments,
                 t.n_stable_panel_establishments, t.stable_panel_total)
        if len(r) > 1:
            ax.plot([r.total.min(), r.total.max()], [y, y], color="#bbbbbb", lw=0.7, zorder=1)
        ticks.append(y); ticklabels.append(f"{name} · {n_txt}")
        labels.append(name)
        y -= 1
    ax.set_yticks(ticks); ax.set_yticklabels(ticklabels, fontsize=FS_MIN)
    ax.set_ylim(y + 0.4, 0.7)
    ax.set_xscale("log")
    ax.grid(axis="y", visible=False)
    return y


def _log_x(ax, lang, lo, hi):
    from matplotlib.ticker import LogLocator, NullFormatter, FuncFormatter
    ax.set_xlim(lo, hi)
    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=8))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: _n(v, 0, lang)))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="x", labelsize=FS_MIN + 0.5)


def _year_legend(ax, lang, years, **kw):
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], marker="o", color="w", markerfacecolor=YEAR_SHADE[y], markeredgecolor="#333333",
                markeredgewidth=0.35, markersize=3.6, label=str(y)) for y in years]
    return ax.legend(handles=h, fontsize=FS_MIN, handlelength=0.9, handletextpad=0.3, columnspacing=0.6, **kw)


def figure_f3(D: Data, variant: str, lang: str) -> tuple[str, list[str]]:
    """Lámina vertical de 180 × 245 mm: seis paneles (a–f) en tres filas por dos columnas."""
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    v = variant
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    rows = []  # tabla de respaldo

    def keep(panel, series, code, era, measure, year, value, unit, n_est, n_stable=np.nan, stable_total=np.nan):
        rows.append(dict(panel=panel, series=series, code=code, era=era, measure=measure, year=int(year), value=value, unit=unit,
                         n_reporting_establishments=n_est, n_stable_panel_establishments=n_stable, stable_panel_total=stable_total))

    # ---------------- a · A03: M-CHAT legado 2019–2022 y M-CHAT-R/F 2023–2024 ----------------
    a = ax[0, 0]
    rows_a = [("header", tr("f3_a1", lang)),
              ("row", ("03500406", tr("mchat_done", lang), OK[0])),
              ("row", ("03500407", tr("mchat_altered", lang), OK[1])),
              ("header", tr("f3_a2", lang)),
              ("row", (CFG.A03_2023_2024["suspected_other"], tr("c_09600212", lang), OK[5])),
              ("row", (CFG.A03_2023_2024["low"], tr("risk_low", lang), OK[5])),
              ("row", (CFG.A03_2023_2024["medium"], tr("risk_medium", lang), OK[4])),
              ("row", (CFG.A03_2023_2024["high"], tr("risk_high", lang), OK[1])),
              ("row", (CFG.A03_2023_2024["high_referred"], tr("ref_high", lang), OK[3])),
              ("row", (CFG.A03_2023_2024["second_part_medium"], tr("c_09600217", lang), OK[3])),
              ("row", (CFG.A03_2023_2024["second_no_referral"], tr("c_09600218", lang), OK[2])),
              ("row", (CFG.A03_2023_2024["second_referral"], tr("ref_second", lang), OK[2]))]
    _dot_rows(a, D, rows_a, lang, keep, "a")
    _log_x(a, lang, 150, 60000)
    a.set_xlabel(f'{tr("u_screening", lang)}\n{tr("legacy_note", lang)}', fontsize=FS_MIN + 0.5)
    # El rótulo del eje X de este panel ocupa DOS líneas: la leyenda de años tenía que bajar por debajo de
    # las dos, no de una, o se imprimía sobre ellas.
    _year_legend(a, lang, [2019, 2020, 2021, 2022, 2023, 2024], loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=6, frameon=False, borderaxespad=0.1)
    panel_head(a, "a", tr("f3_title_a", lang), dx=-0.62)

    # ---------------- b · A03: códigos 31–59 meses (2024) y rediseño (2025) ----------------
    b = ax[0, 1]
    rows_b = [("header", tr("f3_a3", lang))]
    rows_b += [("row", (c, tr(f"s_{c}", lang), OK[0])) for c in ["03700104", "03700105", "03700106", "03700107", "03700108", "03700109"]]
    rows_b += [("header", tr("f3_a4", lang))]
    rows_b += [("row", (c, tr(f"s_{c}", lang), OK[0])) for c in ["03710013", "03710014", "03710015", "03710016", "03710017",
                                                                "03710018", "03710019", "03710020", "03710021"]]
    _dot_rows(b, D, rows_b, lang, keep, "b")
    _log_x(b, lang, 900, 90000)
    b.set_xlabel(tr("u_children", lang), fontsize=FS_MIN + 0.5)
    _year_legend(b, lang, [2024, 2025], loc="upper center", bbox_to_anchor=(0.5, -0.115), ncol=2, frameon=False, borderaxespad=0.1)
    panel_head(b, "b", tr("f3_title_b", lang), dx=-0.58)

    # ---------------- c · A27 consejería/referencia y A28 rehabilitación, 2023–2025 ----------------
    c = ax[1, 0]
    cons = D.row(CFG.A27["counselling"]); refa = D.row(CFG.A27["assisted_referral"])
    rp = D.row(CFG.A28["primary"]); rh = D.row(CFG.A28["hospital"])
    x = cons.year.values
    series_c = [(cons, -0.30, OK[0], tr("counselling", lang)), (refa, -0.10, OK[1], tr("assisted_referral", lang)),
                (rp, 0.10, OK[2], tr("rehab_primary", lang)), (rh, 0.30, OK[3], tr("rehab_hospital", lang))]
    for frame, off, colr, lab in series_c:
        c.bar(frame.year + off, frame.total, width=0.19, color=colr, label=lab)
        for r in frame.itertuples():
            _ann(c, r.year + off, r.total, f"{_n(r.total, 0, lang)} · n={_n(r.n_reporting_establishments, 0, lang)}", colr,
                 fs=FS_MIN, dy=2, rotation=90, ha="center", va="bottom")
            keep("c", ("A27 " if lab in (tr("counselling", lang), tr("assisted_referral", lang)) else "A28 ") + lab, r.code, r.era,
                 "annual_sum", r.year, r.total, r.unit, r.n_reporting_establishments, r.n_stable_panel_establishments, r.stable_panel_total)
    c.set_xticks(x); c.set_xticklabels([str(int(t)) for t in x], fontsize=FS_MIN + 0.5); c.set_xlim(2022.5, 2025.5)
    # Los doce rótulos van GIRADOS 90° sobre la punta de su barra y la leyenda ocupa la banda alta del
    # panel (de lado a lado: lleva título y cuatro entradas). Con el tope en 34.000 el rótulo de la barra
    # mayor —«15.859 · n=359», 65 px de alto sobre un eje de 245— terminaba a 1,9 px del borde inferior de
    # la leyenda; el motor de colisiones lo empujaba 19,6 pt HACIA ABAJO y su recuadro blanco acababa
    # tapando el 26 % SUPERIOR de su propia barra: la barra más alta del panel se imprimía más corta de lo
    # que vale. Con el tope en 40.000 ese rótulo termina un 7,5 % de eje (18 px) por debajo de la leyenda y
    # el motor no tiene que mover nada. Lo vigila la familia VALUE LABEL MASKING ITS OWN BAR de
    # `common.check_layout`, que es la que encontró el defecto.
    c.set_ylim(0, 40000)
    c.set_xlabel(f"{tr('year', lang)} ({tr('codes_2023', lang)})"); c.set_ylabel(tr("u_interventions", lang), fontsize=FS_MIN + 1)
    _fmt_y(c, lang)
    c.legend(loc="upper left", fontsize=FS_MIN, ncol=1, handlelength=1.2, title=tr("n_estab", lang), title_fontsize=FS_MIN)
    panel_head(c, "c", tr("f3_title_c", lang), dx=-0.33)

    # ---------------- d · A05 ingresos y altas: TGD amplio 2019–20 y autismo 2021–25 en un eje ----------------
    d = ax[1, 1]
    ent_b = D.row(CFG.A05_BROAD_PRE2021["entry"], "broad_pre2021"); ex_b = D.row(CFG.A05_BROAD_PRE2021["exit"], "broad_pre2021")
    ent_s = D.row(CFG.STRICT["a05_entry"], "strict_autism"); ex_s = D.row(CFG.STRICT["a05_exit"], "strict_autism")
    ent_f = D.family(v, "a05_entry"); ex_f = D.family(v, "a05_exit")
    d2 = d.twinx(); d2.spines["right"].set_visible(True); d2.grid(False)
    d2.plot(ent_s.year, ent_s.n_reporting_establishments, color="#b0b0b0", lw=1.0, ls="-", zorder=0, label=tr("n_strict", lang))
    d2.plot(ent_b.year, ent_b.n_reporting_establishments, color="#b0b0b0", lw=1.0, ls="-", zorder=0)
    d2.set_ylim(0, 3800); d2.set_ylabel(tr("estab_axis", lang), fontsize=FS_MIN + 1); d2.tick_params(labelsize=FS_TICK)
    _fmt_y(d2, lang)
    d.plot(ent_b.year, ent_b.total, "o-", color=GREY, lw=1.2, ms=3.4, label=tr("entries_broad", lang), zorder=3)
    d.plot(ex_b.year, ex_b.total, "s--", color="#555555", lw=1.1, ms=3.0, label=tr("exits_broad", lang), zorder=3)
    d.plot(ent_f.year, ent_f.total, "o-", color=OK[0], alpha=FAMILY_ALPHA, lw=1.1, ms=3.0, label=tr("entries_family", lang), zorder=3)
    d.plot(ex_f.year, ex_f.total, "s--", color=OK[1], alpha=FAMILY_ALPHA, lw=1.0, ms=2.8, label=tr("exits_family", lang), zorder=3)
    d.plot(ent_s.year, ent_s.total, "o-", color=OK[0], lw=1.6, ms=3.8, label=tr("entries_strict", lang), zorder=4)
    d.plot(ex_s.year, ex_s.total, "s--", color=OK[1], lw=1.4, ms=3.4, label=tr("exits_strict", lang), zorder=4)
    C.plate_annotate_no_overlap(d, ent_s.year.to_numpy(float), ent_s.total.to_numpy(float),
                                [_n(t, 0, lang) for t in ent_s.total], fontsize=FS_MIN, color=OK[0],
                                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.8))
    for frame, lab in [(ent_b, tr("entries_broad", lang)), (ex_b, tr("exits_broad", lang)), (ent_s, tr("entries_strict", lang)),
                       (ex_s, tr("exits_strict", lang)), (ent_f, tr("entries_family", lang)), (ex_f, tr("exits_family", lang))]:
        for r in frame.itertuples():
            keep("d", "A05 " + lab, r.code, r.era, "annual_sum", r.year, r.total, r.unit, r.n_reporting_establishments,
                 r.n_stable_panel_establishments, r.stable_panel_total)
    _era_break(d, lang, 2020.5, y=0.34)
    d.set_xticks(list(YEARS)); d.set_xticklabels([f"\u2019{y % 100:02d}" for y in YEARS], fontsize=FS_MIN + 0.5)
    # Aire arriba: la leyenda de siete entradas ocupa el tercio superior y, con el techo anterior, empujaba
    # los rótulos de contexto al pie del panel, encima de las series de altas.
    d.set_xlim(2018.5, 2025.5); d.set_ylim(0, 50000)
    # La marca de la Ley baja a la banda vacía del panel: a media altura caía sobre los rótulos de fin de
    # serie (11.842 y 13.155), que están fijados a su punto por el colocador y no pueden apartarse.
    # El rótulo de la pandemia iba a media altura, justo donde el del quiebre de definición, y el de la Ley
    # caía sobre la serie de altas de la familia TGD (44 % de la serie tapada). Los dos bajan al pie del
    # panel, que en este panel está vacío.
    # Banda libre entre el pie de la leyenda y el techo de las series (13.155 de 42.000 = 0,31)
    _context(d, lang, pandemic_pos=0.58, law_pos=0.45, pandemic_x_offset=0.62, fs=FS_MIN)
    d.set_zorder(d2.get_zorder() + 1); d.patch.set_visible(False)
    d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("u_entries", lang), fontsize=FS_MIN + 1); _fmt_y(d, lang)
    h1, l1 = d.get_legend_handles_labels(); h2, l2 = d2.get_legend_handles_labels()
    plate_legend(d, h1 + h2, l1 + l2, loc="upper left", ncol=2, handlelength=1.2, columnspacing=0.7)
    panel_head(d, "d", tr("f3_title_d", lang), dx=-0.33)

    # ---------------- e · P2 TEA NANEAS bajo control (stock de diciembre) ----------------
    e = ax[2, 0]
    p2d = D.row(CFG.P2_TEA, measure="december_stock"); p2j = D.row(CFG.P2_TEA, measure="june_stock")
    nan_d = D.row(CFG.P2_NANEAS_TOTAL, measure="december_stock")
    e2 = e.twinx(); e2.spines["right"].set_visible(True); e2.grid(False)
    e2.plot(p2d.year, p2d.n_reporting_establishments, color="#b0b0b0", lw=1.0, zorder=0, label=tr("n_dec", lang))
    e2.plot(p2j.year, p2j.n_reporting_establishments, color="#b0b0b0", lw=1.0, ls=":", zorder=0, label=tr("n_jun", lang))
    e2.set_ylim(0, 5200); e2.set_ylabel(tr("estab_axis", lang), fontsize=FS_MIN + 1); e2.tick_params(labelsize=FS_TICK); _fmt_y(e2, lang)
    e.plot(p2d.year, p2d.total, "o-", color=OK[3], lw=1.6, ms=4.0, label=tr("dec_stock", lang), zorder=4)
    e.plot(p2j.year, p2j.total, marker="o", mfc="white", mec=OK[3], mew=1.0, ms=4.0, ls="none", label=tr("jun_stock", lang), zorder=4)
    _ey, _ev, _el = _ends_only(p2d.year.to_numpy(float), p2d.total.to_numpy(float), [_n(t, 0, lang) for t in p2d.total])
    C.plate_annotate_no_overlap(e, _ey, _ev, _el, fontsize=FS_MIN, color=OK[3],
                                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.8))
    for r in p2d.itertuples():
        keep("e", "P2 " + tr("dec_stock", lang), r.code, r.era, "december_stock", r.year, r.total, r.unit,
             r.n_reporting_establishments, r.n_stable_panel_establishments, r.stable_panel_total)
    for r in p2j.itertuples():
        keep("e", "P2 " + tr("jun_stock", lang), r.code, r.era, "june_stock", r.year, r.total, r.unit,
             r.n_reporting_establishments, r.n_stable_panel_establishments, r.stable_panel_total)
    naneas_txt = "; ".join(f"{int(r.year)}: {_n(100 * p2d.loc[p2d.year == r.year, 'total'].iloc[0] / r.total, 1, lang)}" for r in nan_d.itertuples())
    # La nota se imprimía sobre las dos series de stock; la banda entre la leyenda y el arranque de las
    # series (izquierda del panel, mitad alta) está vacía y es donde cabe.
    plate_note(e, f"{tr('per100_naneas', lang)} {naneas_txt}", x=0.03, y=0.44, ha="left", va="top",
               color="#555555", width_pt=80.0).set_gid(C.PLATE_KEEP)
    for r in nan_d.itertuples():
        keep("e", "P2 NANEAS total", r.code, r.era, "december_stock", r.year, r.total, r.unit, r.n_reporting_establishments,
             r.n_stable_panel_establishments, r.stable_panel_total)
    e.set_xticks(list(YEARS)); e.set_xticklabels([f"\u2019{y % 100:02d}" for y in YEARS], fontsize=FS_MIN + 0.5)
    # margen a los lados para que el rótulo de valor de 2019 quepa a la izquierda de su punto
    e.set_xlim(2018.2, 2025.8); e.set_ylim(0, 44000)
    _context(e, lang, pandemic_text=False, law_text=False, fs=FS_MIN)
    e.set_zorder(e2.get_zorder() + 1); e.patch.set_visible(False)
    h1, l1 = e.get_legend_handles_labels(); h2, l2 = e2.get_legend_handles_labels()
    plate_legend(e, h1 + h2, l1 + l2, loc="upper left", handlelength=1.2)
    e.set_xlabel(tr("year", lang)); e.set_ylabel(tr("u_stock_dec", lang), fontsize=FS_MIN + 1); _fmt_y(e, lang)
    panel_head(e, "e", tr("f3_title_e", lang), dx=-0.33)

    # ---------------- f · P6 bajo control en diciembre: dos eras en un eje ----------------
    f = ax[2, 1]
    pb = D.row(CFG.P6_BROAD_PRE2021["primary"], "broad_pre2021", "december_stock"); sb = D.row(CFG.P6_BROAD_PRE2021["specialty"], "broad_pre2021", "december_stock")
    ps = D.row(CFG.STRICT["p6_primary"], "strict_autism", "december_stock"); ss = D.row(CFG.STRICT["p6_specialty"], "strict_autism", "december_stock")
    pf = D.family(v, "p6_primary", "december_stock"); sf = D.family(v, "p6_specialty", "december_stock")
    f.plot(pb.year, pb.total, "o-", color=GREY, lw=1.2, ms=3.4, label=tr("primary_broad", lang))
    f.plot(sb.year, sb.total, "s--", color="#555555", lw=1.1, ms=3.0, label=tr("specialty_broad", lang))
    f.plot(pf.year, pf.total, "o-", color=OK[4], alpha=FAMILY_ALPHA, lw=1.1, ms=3.0, label=tr("primary_family", lang))
    f.plot(sf.year, sf.total, "s--", color=OK[5], alpha=FAMILY_ALPHA, lw=1.0, ms=2.8, label=tr("specialty_family", lang))
    f.plot(ps.year, ps.total, "o-", color=OK[4], lw=1.6, ms=3.8, label=tr("primary_strict", lang), zorder=4)
    f.plot(ss.year, ss.total, "s--", color=OK[5], lw=1.4, ms=3.4, label=tr("specialty_strict", lang), zorder=4)
    _placed = []
    for frame, colr in [(ps, OK[4]), (ss, OK[5])]:
        # Sólo el último punto de cada serie estricta: las dos arrancan en 2021 a 2.257 y 3.562, a menos de
        # medio milímetro una de otra en un eje de 55.000, y sus rótulos de arranque se tocaban.
        _fy, _fv, _fl = _ends_only(frame.year.to_numpy(float), frame.total.to_numpy(float),
                                   [_n(t, 0, lang) for t in frame.total], which="last")
        _placed = C.plate_annotate_no_overlap(
            f, _fy, _fv, _fl, fontsize=FS_MIN, color=colr, state=_placed,
            bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.8))
    for frame, lab in [(pb, tr("primary_broad", lang)), (sb, tr("specialty_broad", lang)), (ps, tr("primary_strict", lang)),
                       (ss, tr("specialty_strict", lang)), (pf, tr("primary_family", lang)), (sf, tr("specialty_family", lang))]:
        for r in frame.itertuples():
            keep("f", "P6 " + lab, r.code, r.era, "december_stock", r.year, r.total, r.unit, r.n_reporting_establishments,
                 r.n_stable_panel_establishments, r.stable_panel_total)
    _era_break(f, lang, 2020.5, y=0.66)
    f.set_xticks(list(YEARS)); f.set_xticklabels([f"\u2019{y % 100:02d}" for y in YEARS], fontsize=FS_MIN + 0.5)
    # Aire arriba para la leyenda de seis entradas, que en el techo anterior se imprimía sobre los rótulos
    # de valor de las dos series estrictas.
    f.set_xlim(2018.2, 2025.8); f.set_ylim(0, 55000)
    _context(f, lang, pandemic_text=False, law_text=False, fs=FS_MIN)
    plate_legend(f, loc="upper left", handlelength=1.2, ncol=1)
    f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("u_stock_dec", lang), fontsize=FS_MIN + 1); _fmt_y(f, lang)
    # Nota corta: «n = establecimientos reportantes» se define en el pie de la figura, de modo que en la
    # celda basta con los dos rangos. La versión larga ocupaba media anchura del panel y caía sobre las series.
    n_txt = f"n {tr('m_primary', lang)} {_n(ps.n_reporting_establishments.min(), 0, lang)}–{_n(ps.n_reporting_establishments.max(), 0, lang)} · " \
            f"{tr('m_specialty', lang)} {_n(ss.n_reporting_establishments.min(), 0, lang)}–{_n(ss.n_reporting_establishments.max(), 0, lang)}"
    # La nota de establecimientos reportantes se imprimía sobre las cuatro series; el pie derecho del panel
    # (años 2023–2025 por debajo de 5.000) no tiene ningún dato.
    plate_note(f, n_txt.replace("\n", " "), x=0.97, y=0.02, ha="right", va="bottom", color="#555555", width_pt=62.0).set_gid(C.PLATE_KEEP)
    panel_head(f, "f", tr("f3_title_f", lang), dx=-0.33)

    path = save_plate(fig, fdir / "fig3_rem_pathway.png")
    plt.close(fig)
    fw = tr("figure", lang); vl = vlab(variant, lang)
    fam_codes = D.family_code(v, "a05_entry").replace("+", ", ")
    p6_codes = D.family_code(v, "p6_primary").replace("+", ", ")
    cap = {
        "title": {"es": f"{fw} 4. Ruta administrativa agregada REM del autismo en la red pública chilena, 2019–2025: detección (A03), consejería, referencia y rehabilitación (A27, A28), ingreso y alta (A05) y población bajo control (P2, P6) — variante {vl}",
                  "en": f"{fw} 4. Aggregated REM administrative pathway for autism in the Chilean public network, 2019–2025: detection (A03), counselling, referral and rehabilitation (A27, A28), entry and discharge (A05) and population under control (P2, P6) — {vl} variant"}[lang],
        "caption": {
            "es": ("Todos los valores son conteos administrativos anuales de la red pública (unidad indicada en cada eje), sumados sobre las filas establecimiento × mes presentes en los archivos REM; "
                   "las fuentes no se enlazan por persona y ningún cociente entre paneles representa una probabilidad individual. n = establecimientos con al menos una fila del código en el año "
                   "(en diciembre o junio para los stocks); el rango n que acompaña a cada rótulo abarca los años mostrados. Cada era de definición ocupa su propio bloque o segmento y ninguna serie "
                   "cruza un quiebre. (a) A03 detección en APS, escala logarítmica, un punto por año (color) y un segmento gris que une el menor y el mayor valor de la era: 2019–2022 M-CHAT realizado "
                   "(03500406) y alterado (03500407) solo en niños/as con alteración de lenguaje o del área social en el control de 18 meses (no es cobertura ni positividad poblacional); 2023–2024 "
                   "M-CHAT-R/F, sospecha en otra instancia (09600212), resultado de la primera parte por riesgo bajo, medio y alto (09600213–15), alto riesgo derivado (09600216) y segunda parte "
                   "(09600217–19). (b) A03 en las eras siguientes, misma lectura: 2024 códigos 03700104–09 para 31–59 meses (evaluados, sospecha en otra instancia, señales de alerta sí/no, derivación "
                   "sí/no) y 2025 rediseño 03710013–21 (motivos del M-CHAT a los 16–30 meses, resultado por riesgo y necesidad de derivación, sospecha a los 30–59 meses). Las eras de (a) y (b) no son "
                   "comparables entre sí. (c) A27 consejería (29101566) y referencia asistida (29101574) en contexto de tamizaje M-CHAT-R/F, y A28 ingresos a rehabilitación por TEA en APS (29101629) y "
                   "hospitalaria (29101651), 2023–2025: intervenciones e ingresos, no personas; sobre cada barra, valor y n. "
                   f"(d) A05 ingresos y altas clínicas del programa de salud mental en un solo eje con el quiebre de definición marcado: TGD amplio 2019–2020 (06902600/05225000, definición no "
                   f"comparable) y autismo estricto 2021–2025 (05990022/05990027, líneas gruesas) con la familia TGD de la variante ({fam_codes}) como líneas claras; línea gris y eje derecho: "
                   "establecimientos reportantes. (e) P2 población NANEAS con TEA bajo control (P2500500): stock de diciembre (puntos llenos) y de junio (marcadores huecos, sensibilidad; los "
                   "semestres nunca se suman); líneas grises y eje derecho: establecimientos con fila en diciembre y en junio; texto: TEA por 100 NANEAS totales (P2501878, disponible desde diciembre "
                   f"de 2023). (f) P6 población bajo control en diciembre en un solo eje con el quiebre marcado: TGD amplio 2019–2020 (P6223000 APS, P6223380 especialidad) y autismo estricto 2021–2025 "
                   f"(P6241010 APS, P6241060 especialidad) con la familia TGD de la variante (APS {p6_codes} y sus equivalentes de especialidad) como líneas claras. Sombreado gris: disrupción del "
                   "reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto, no como intervención; ambas significan lo mismo en todos los paneles y se rotulan una sola vez, en (d). "
                   "Los conteos son reconocimiento administrativo, no prevalencia ni incidencia; stocks (e, f) y flujos (a, b, c, d) nunca comparten un eje."),
            "en": ("All values are annual administrative counts from the public network (unit stated on each axis), summed over the establishment × month rows present in the REM files; sources are not "
                   "person-linked and no ratio between panels represents an individual probability. n = establishments with at least one row for the code in the year (December or June rows for stocks); "
                   "the n range beside each label spans the years shown. Each definition era occupies its own block or segment and no series crosses a break. (a) A03 detection in primary care, log scale, "
                   "one dot per year (colour) and a grey segment joining the era's lowest and highest value: 2019–2022 M-CHAT done (03500406) and altered (03500407) only among children with a language or "
                   "social-area alteration at the 18-month control (neither population coverage nor positivity); 2023–2024 M-CHAT-R/F, suspicion raised elsewhere (09600212), part-1 result by low, medium "
                   "and high risk (09600213–15), high risk referred (09600216) and part 2 (09600217–19). (b) A03 in the following eras, read the same way: 2024 codes 03700104–09 for ages 31–59 months "
                   "(evaluated, suspected elsewhere, alert signs yes/no, referral yes/no) and the 2025 redesign 03710013–21 (M-CHAT motives at 16–30 months, risk result and referral need, suspicion at "
                   "30–59 months). The eras in (a) and (b) are not comparable with one another. (c) A27 counselling (29101566) and assisted referral (29101574) in the M-CHAT-R/F screening context, and A28 "
                   "rehabilitation entries for ASD at primary (29101629) and hospital level (29101651), 2023–2025: interventions and entries, not persons; value and n above each bar. "
                   f"(d) A05 mental-health programme entries and clinical discharges on a single axis with the definition break marked: broad PDD 2019–2020 (06902600/05225000, non-comparable definition) "
                   f"and strict autism 2021–2025 (05990022/05990027, thick lines) with the variant's PDD family ({fam_codes}) as lighter lines; grey line and right axis: reporting establishments. "
                   "(e) P2 NANEAS population with ASD under control (P2500500): December stock (filled points) and June stock (hollow markers, sensitivity; semesters are never summed); grey lines and right "
                   "axis: establishments with a December and a June row; text: ASD per 100 total NANEAS (P2501878, available from December 2023). (f) P6 population under control in December on a single axis "
                   f"with the break marked: broad PDD 2019–2020 (P6223000 primary care, P6223380 specialty) and strict autism 2021–2025 (P6241010 primary care, P6241060 specialty) with the variant's PDD "
                   f"family (primary care {p6_codes} and the specialty equivalents) as lighter lines. Grey shading: 2020–2021 reporting disruption; dotted line: Law 21.545 (March 2023) as context, not as an "
                   "intervention; both mean the same in every panel and are labelled once, in (d). Counts are administrative recognition, not prevalence or incidence; stocks (e, f) and flows (a, b, c, d) "
                   "never share an axis."),
        }[lang],
    }
    merge_json(fdir / "captions.json", {"fig3_rem_pathway": cap})
    # tabla de respaldo
    tab = pd.DataFrame(rows)
    tab["variant"] = variant
    fmt = pd.DataFrame({
        tr("t_panel", lang): tab.panel, tr("t_series", lang): tab.series, tr("t_code", lang): tab.code, tr("t_era", lang): tab.era,
        tr("t_measure", lang): [tr_measure(m, lang) for m in tab.measure], tr("year", lang): tab.year, tr("t_value", lang): [_n(x, 0, lang) for x in tab.value],
        tr("t_unit", lang): [tr_unit(u, lang) for u in tab.unit],
        tr("t_n_est", lang): [_n(x, 0, lang) for x in tab.n_reporting_establishments],
        tr("t_n_stable", lang): [_n(x, 0, lang) if pd.notna(x) else tr("na", lang) for x in tab.n_stable_panel_establishments],
        tr("t_stable_total", lang): [_n(x, 0, lang) if pd.notna(x) else tr("na", lang) for x in tab.stable_panel_total]})
    tw = tr("table", lang)
    paths = write_table(variant, lang, "F3_rem_pathway_data", fmt, tab,
                        {"es": f"{tw} F3 (datos). Valores graficados en la {main_figure_label('fig3_rem_pathway', 'es')}: conteos anuales REM por panel, código, era y año, con establecimientos reportantes y panel estable — variante {vl}",
                         "en": f"{tw} F3 (data). Values plotted in {main_figure_label('fig3_rem_pathway', 'en')}: annual REM counts by panel, code, era and year, with reporting establishments and stable panel — {vl} variant"}[lang],
                        {"es": "Unidad según la columna Unidad (registros de tamizaje, niños/as, intervenciones, ingresos/altas o personas en stock). Flujos = suma de meses; stocks = valor de diciembre o de junio (nunca sumados). "
                               "Establecimientos reportantes = IdEstablecimiento distintos con fila del código (o familia) en el año; panel estable = establecimientos con fila en cada año de la era del código. "
                               "Las eras de definición no son comparables entre sí. Conteos administrativos, no prevalencia.",
                         "en": "Unit as in the Unit column (screening records, children, interventions, entries/discharges or people in stock). Flows = sum of months; stocks = December or June value (never summed). "
                               "Reporting establishments = distinct IdEstablecimiento with a row for the code (or family) in the year; stable panel = establishments with a row in every year of the code's era. "
                               "Definition eras are not comparable with one another. Administrative counts, not prevalence."}[lang])
    return str(path), paths


# ===========================================================================
# S5 · Junio frente a diciembre
# ===========================================================================
def figure_s5(D: Data, variant: str, lang: str) -> tuple[str, list[str]]:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    v = variant
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    rows = []

    def pair_panel(axis, dec, jun, col, label_prefix, letter_, title, fam_dec=None, fam_jun=None, broad_dec=None, broad_jun=None):
        x = dec.year.values
        axis.bar(x - 0.2, dec.total, width=0.38, color=col, label=f"{tr('december', lang)}")
        axis.bar(x + 0.2, jun.total, width=0.38, color="white", edgecolor=col, hatch="////", lw=1.2, label=f"{tr('june', lang)}")
        ymax = dec.total.max()
        # El rótulo «n=…» se ancla al TECHO de su columna, no al de la barra: el rombo de la familia TGD se
        # dibuja por encima de la barra en varios años y el rótulo caía justo encima de él.
        tops: dict = {}

        def note_top(year, off, value):
            key = (float(year), off)
            tops[key] = max(tops.get(key, 0.0), float(value))

        n_labels: list = []
        for r in dec.itertuples():
            note_top(r.year, -0.2, r.total); n_labels.append((r.year, -0.2, r.n_reporting_establishments, col))
        for r in jun.itertuples():
            note_top(r.year, 0.2, r.total); n_labels.append((r.year, 0.2, r.n_reporting_establishments, col))
        if broad_dec is not None:
            xb = broad_dec.year.values
            axis.bar(xb - 0.2, broad_dec.total, width=0.38, color=GREY, label=f"{tr('broad_label', lang)} · {tr('december', lang)}")
            axis.bar(xb + 0.2, broad_jun.total, width=0.38, color="white", edgecolor=GREY, hatch="////", lw=1.2, label=f"{tr('broad_label', lang)} · {tr('june', lang)}")
            for r in broad_dec.itertuples():
                note_top(r.year, -0.2, r.total); n_labels.append((r.year, -0.2, r.n_reporting_establishments, GREY))
            for r in broad_jun.itertuples():
                note_top(r.year, 0.2, r.total); n_labels.append((r.year, 0.2, r.n_reporting_establishments, GREY))
            _break_marker(axis, 2020.5, lang, y=0.55)
            ymax = max(ymax, broad_dec.total.max())
        if fam_dec is not None:
            axis.plot(fam_dec.year - 0.2, fam_dec.total, "D", color=col, alpha=FAMILY_ALPHA, ms=5, label=tr("family_dec", lang), zorder=5)
            axis.plot(fam_jun.year + 0.2, fam_jun.total, "D", mfc="white", mec=col, alpha=FAMILY_ALPHA + 0.2, ms=5, ls="none", label=tr("family_jun", lang), zorder=5)
            for r in fam_dec.itertuples():
                note_top(r.year, -0.2, r.total)
            for r in fam_jun.itertuples():
                note_top(r.year, 0.2, r.total)
            ymax = max(ymax, fam_dec.total.max())
        for year, off, n_est, colr in n_labels:
            _ann(axis, year + off, tops[(float(year), off)], f"n={_n(n_est, 0, lang)}", colr, fs=6.2, rotation=90, dy=4)
        yrs = sorted(set(x) | (set(broad_dec.year.values) if broad_dec is not None else set()))
        axis.set_xticks(yrs); axis.set_xlim(min(yrs) - 0.6, max(yrs) + 0.6); axis.set_ylim(0, ymax * 1.95)
        # Los rótulos de contexto suben por encima de las barras y de sus «n=» girados: a 0,42 y 0,36 se
        # imprimían dentro de la barra de 2023.
        _context(axis, lang, pandemic_pos=0.985, law_pos=0.88, pandemic_text=letter_ == "a", law_text=letter_ == "a")
        axis.set_xlabel(tr("year", lang)); axis.set_ylabel(tr("u_stock", lang)); _fmt_y(axis, lang)
        plate_legend(axis, loc="upper left"); panel_head(axis, letter_, title)
        for frame, m in [(dec, "december_stock"), (jun, "june_stock")] + ([(broad_dec, "december_stock"), (broad_jun, "june_stock")] if broad_dec is not None else []) + \
                        ([(fam_dec, "december_stock"), (fam_jun, "june_stock")] if fam_dec is not None else []):
            for r in frame.itertuples():
                rows.append(dict(panel=letter_, series=label_prefix, code=r.code, variant_row=r.variant, era=r.era, measure=m, year=int(r.year), value=r.total,
                                 n_reporting_establishments=r.n_reporting_establishments))

    p2d = D.row(CFG.P2_TEA, measure="december_stock"); p2j = D.row(CFG.P2_TEA, measure="june_stock")
    pair_panel(ax[0, 0], p2d, p2j, OK[3], tr("p2_short", lang), "a", tr("s5_a", lang))
    pd_s = D.row(CFG.STRICT["p6_primary"], "strict_autism", "december_stock"); pj_s = D.row(CFG.STRICT["p6_primary"], "strict_autism", "june_stock")
    pd_f = D.family(v, "p6_primary", "december_stock"); pj_f = D.family(v, "p6_primary", "june_stock")
    pd_b = D.row(CFG.P6_BROAD_PRE2021["primary"], "broad_pre2021", "december_stock"); pj_b = D.row(CFG.P6_BROAD_PRE2021["primary"], "broad_pre2021", "june_stock")
    pair_panel(ax[0, 1], pd_s, pj_s, OK[4], tr("p6p_short", lang), "b", tr("s5_b", lang), pd_f, pj_f, pd_b, pj_b)
    sd_s = D.row(CFG.STRICT["p6_specialty"], "strict_autism", "december_stock"); sj_s = D.row(CFG.STRICT["p6_specialty"], "strict_autism", "june_stock")
    sd_f = D.family(v, "p6_specialty", "december_stock"); sj_f = D.family(v, "p6_specialty", "june_stock")
    sd_b = D.row(CFG.P6_BROAD_PRE2021["specialty"], "broad_pre2021", "december_stock"); sj_b = D.row(CFG.P6_BROAD_PRE2021["specialty"], "broad_pre2021", "june_stock")
    pair_panel(ax[1, 0], sd_s, sj_s, OK[5], tr("p6s_short", lang), "c", tr("s5_c", lang), sd_f, sj_f, sd_b, sj_b)

    # D — razones junio/diciembre (stock y establecimientos) por segmento de era
    d = ax[1, 1]
    series = [("P2", p2d, p2j, OK[3], tr("p2_short", lang)),
              ("P6p_broad", pd_b, pj_b, OK[4], f"{tr('p6p_short', lang)} · {tr('broad_label', lang)}"),
              ("P6p", pd_s, pj_s, OK[4], tr("p6p_short", lang)),
              ("P6s_broad", sd_b, sj_b, OK[5], f"{tr('p6s_short', lang)} · {tr('broad_label', lang)}"),
              ("P6s", sd_s, sj_s, OK[5], tr("p6s_short", lang))]
    ratio_rows = []
    for key, dec, jun, col, lab in series:
        m = dec.merge(jun, on="year", suffixes=("_dec", "_jun"))
        rs = m.total_jun / m.total_dec
        re_ = m.n_reporting_establishments_jun / m.n_reporting_establishments_dec
        broad = "broad" in key
        d.plot(m.year, rs, "o-" if not broad else "o:", color=col, lw=2.0 if not broad else 1.4, ms=6, alpha=1 if not broad else 0.6, label=None if broad else lab)
        d.plot(m.year, re_, "s--", color=col, lw=1.2, ms=4.5, alpha=0.55 if not broad else 0.35)
        for r, a, b_ in zip(m.itertuples(), rs, re_):
            ratio_rows.append(dict(series=key, year=int(r.year), june_stock=r.total_jun, december_stock=r.total_dec, ratio_stock=a,
                                   n_june=r.n_reporting_establishments_jun, n_december=r.n_reporting_establishments_dec, ratio_establishments=b_))
    d.axhline(1, color="#888888", ls="--", lw=1.0)
    d.set_xticks(CFG.YEARS_STOCK); d.set_xlim(2018.4, 2025.6); d.set_ylim(0, 1.45)
    _era_break(d, lang, 2020.5, y=0.98)
    _context(d, lang, pandemic_pos=0.98, law_pos=0.98, pandemic_text=False, law_text=False)
    from matplotlib.lines import Line2D
    h, l = d.get_legend_handles_labels()
    h += [Line2D([0], [0], color=DARK, marker="o", ls="-", lw=2), Line2D([0], [0], color=DARK, marker="s", ls="--", lw=1.2, alpha=0.6), Line2D([0], [0], color=DARK, marker="o", ls=":", lw=1.4, alpha=0.6)]
    l += [tr("ratio_stock", lang), tr("ratio_estab", lang), tr("broad_label", lang)]
    d.set_xlabel(tr("year", lang)); d.set_ylabel(tr("u_ratio_jd", lang))
    plate_legend(d, h, l, loc="lower right", ncol=2, columnspacing=0.8, handlelength=1.6); panel_head(d, "d", tr("s5_d", lang))

    # E — dispersión por establecimiento P2 TEA
    e = ax[2, 0]
    est = D.est[(D.est.code == CFG.P2_TEA)]
    scatter_rows = []
    for year, col in [(2019, YEARCOL[2019]), (2020, YEARCOL[2020]), (2022, YEARCOL[2022]), (2025, YEARCOL[2025])]:
        s = est[est.year == year]
        both = s[(s.has_december_row == True) & (s.has_june_row == True)]  # noqa: E712
        n_dec_only = int(((s.has_december_row == True) & (s.has_june_row != True)).sum())  # noqa: E712
        n_jun_only = int(((s.has_june_row == True) & (s.has_december_row != True)).sum())  # noqa: E712
        # Entrada de leyenda COMPACTA: la larga («2019: ambos n=…; solo dic …; solo jun …») medía media
        # anchura del panel y la leyenda cruzaba la línea de identidad. El orden de las tres cifras se
        # explica en el título de la leyenda.
        e.scatter(both.june_value + 1, both.december_value + 1, s=16, color=col, alpha=0.55, edgecolor="none",
                  label=f"{year}: {_n(len(both), 0, lang)} · {_n(n_dec_only, 0, lang)} · {_n(n_jun_only, 0, lang)}")
        scatter_rows.append(dict(year=year, n_both=len(both), n_december_only=n_dec_only, n_june_only=n_jun_only))
    lim = max(est.december_value.max(), est.june_value.max()) + 1
    e.plot([1, lim * 1.2], [1, lim * 1.2], color="#888888", ls="--", lw=1.0, label=tr("identity", lang))
    e.set_xscale("log"); e.set_yscale("log"); e.set_xlim(0.9, lim * 1.3); e.set_ylim(0.9, lim * 1.3)
    e.set_xlabel(tr("june_axis", lang)); e.set_ylabel(tr("dec_axis", lang))
    plate_legend(e, loc="upper left",
                 title=f"{tr('both_n', lang)} · {tr('dec_n', lang)} · {tr('jun_n', lang)}", title_fontsize=FS_MIN)
    panel_head(e, "e", tr("s5_e", lang))

    # F — patrón semestral de reporte (P2 TEA y P6 APS)
    f = ax[2, 1]
    pat_rows = []
    for key, codes, off, base_col in [("P2", [CFG.P2_TEA], -0.2, OK[3]), ("P6p", [CFG.P6_BROAD_PRE2021["primary"], CFG.STRICT["p6_primary"]], 0.2, OK[4])]:
        s = D.est[D.est.code.isin(codes)]
        g = s.groupby("year").apply(lambda t: pd.Series({
            "both": int(((t.has_december_row == True) & (t.has_june_row == True)).sum()),  # noqa: E712
            "dec_only": int(((t.has_december_row == True) & (t.has_june_row != True)).sum()),  # noqa: E712
            "jun_only": int(((t.has_june_row == True) & (t.has_december_row != True)).sum())}), include_groups=False).reset_index()  # noqa: E712
        bottom = np.zeros(len(g))
        for cat, alpha, hatch, lab in [("both", 1.0, "", tr("both_sem", lang)), ("dec_only", 0.55, "", tr("dec_only", lang)), ("jun_only", 0.25, "////", tr("jun_only", lang))]:
            f.bar(g.year + off, g[cat], bottom=bottom, width=0.38, color=base_col, alpha=alpha, hatch=hatch, edgecolor="white" if not hatch else base_col,
                  label=f"{tr('p2_short', lang) if key == 'P2' else tr('p6p_short', lang)} · {lab}")
            bottom += g[cat].values
        for r in g.itertuples():
            pat_rows.append(dict(series=key, year=int(r.year), both=r.both, december_only=r.dec_only, june_only=r.jun_only))
    f.set_xticks(CFG.YEARS_STOCK); f.set_xlim(2018.4, 2025.6); f.set_ylim(0, f.get_ylim()[1] * 1.45)
    _break_marker(f, 2020.5, lang, y=0.60)
    _context(f, lang, pandemic_pos=0.98, law_pos=0.72, pandemic_text=False, law_text=False)
    f.set_xlabel(tr("year", lang)); f.set_ylabel(tr("estab_count", lang))
    plate_legend(f, loc="upper left", ncol=2, columnspacing=0.8, handlelength=1.2); panel_head(f, "f", tr("s5_f", lang))

    path = save_plate(fig, fdir / "figS5_rem_june_december.png")
    plt.close(fig)
    fw = tr("figure", lang); vl = vlab(variant, lang)
    cap = {"title": {"es": f"{fw} S5. Stocks REM de junio frente a diciembre (P2 TEA, P6 APS y especialidad), 2019–2025: sensibilidad semestral, nunca sumada — variante {vl}",
                     "en": f"{fw} S5. REM June versus December stocks (P2 ASD, P6 primary care and specialty), 2019–2025: semester sensitivity, never summed — {vl} variant"}[lang],
           "caption": {"es": ("Personas bajo control (stock) en la fila de junio (MES=06, barras rayadas) y de diciembre (MES=12, barras llenas) de cada año; n = establecimientos con fila en ese semestre. "
                              "(a) P2 TEA (P2500500) 2019–2025: junio de 2020 colapsa a 172 personas en 28 establecimientos (disrupción del reporte), frente a 1.919 en 400 establecimientos en diciembre. "
                              f"(b) P6 APS: TGD amplio 2019–2020 (P6223000, gris; definición distinta, separada por el marcador de quiebre) y autismo estricto 2021–2025 (P6241010); rombos: familia TGD de la variante ({D.family_code(v, 'p6_primary').replace('+', ', ')}). "
                              f"(c) P6 especialidad: TGD amplio (P6223380) y autismo estricto (P6241060); rombos: familia de la variante ({D.family_code(v, 'p6_specialty').replace('+', ', ')}). "
                              "(d) Razón junio/diciembre del stock (círculos) y del número de establecimientos reportantes (cuadrados) por serie y segmento de era; los segmentos no se unen a través del quiebre de 2021. "
                              "(e) P2 TEA por establecimiento en 2019, 2020, 2022 y 2025: valor de junio frente a diciembre (+1, escala logarítmica) en establecimientos con ambas filas; la leyenda indica cuántos tienen ambas, solo diciembre o solo junio. "
                              "(f) Número de establecimientos según patrón semestral de reporte (ambos semestres, solo diciembre, solo junio) para P2 TEA y P6 APS (TGD amplio hasta 2020, autismo estricto desde 2021). "
                              "Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto. Los semestres son cortes de stock y nunca se suman; conteos administrativos, no prevalencia."),
                       "en": ("People under control (stock) in the June row (MES=06, hatched bars) and the December row (MES=12, filled bars) of each year; n = establishments with a row in that semester. "
                              "(a) P2 ASD (P2500500) 2019–2025: June 2020 collapses to 172 people in 28 establishments (reporting disruption) against 1,919 in 400 establishments in December. "
                              f"(b) P6 primary care: broad PDD 2019–2020 (P6223000, grey; different definition, separated by the break marker) and strict autism 2021–2025 (P6241010); diamonds: variant PDD family ({D.family_code(v, 'p6_primary').replace('+', ', ')}). "
                              f"(c) P6 specialty: broad PDD (P6223380) and strict autism (P6241060); diamonds: variant family ({D.family_code(v, 'p6_specialty').replace('+', ', ')}). "
                              "(d) June/December ratio of the stock (circles) and of the number of reporting establishments (squares) by series and era segment; segments are not joined across the 2021 break. "
                              "(e) P2 ASD by establishment in 2019, 2020, 2022 and 2025: June versus December value (+1, log scale) in establishments with both rows; the legend gives how many have both, December only or June only. "
                              "(f) Number of establishments by semester reporting pattern (both semesters, December only, June only) for P2 ASD and P6 primary care (broad PDD to 2020, strict autism from 2021). "
                              "Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context. Semesters are stock cuts and are never summed; administrative counts, not prevalence.")}[lang]}
    merge_json(fdir / "captions.json", {"figS5_rem_june_december": cap})
    # tabla
    tab = pd.DataFrame(rows); tab["variant"] = variant
    piv = tab.pivot_table(index=["panel", "series", "code", "variant_row", "era", "year"], columns="measure", values=["value", "n_reporting_establishments"], aggfunc="first").reset_index()
    piv.columns = ["_".join([c for c in col if c]) if isinstance(col, tuple) else col for col in piv.columns]
    for c in ["value_june_stock", "value_december_stock", "n_reporting_establishments_june_stock", "n_reporting_establishments_december_stock"]:
        if c not in piv:
            piv[c] = np.nan
    piv["ratio_june_december"] = piv.value_june_stock / piv.value_december_stock
    fmt = pd.DataFrame({tr("t_panel", lang): piv.panel, tr("t_series", lang): piv.series, tr("t_code", lang): piv.code, tr("t_era", lang): piv.era, tr("year", lang): piv.year,
                        tr("t_dec", lang): [_n(x, 0, lang) if pd.notna(x) else tr("absent", lang) for x in piv.value_december_stock],
                        tr("t_n_dec", lang): [_n(x, 0, lang) if pd.notna(x) else tr("absent", lang) for x in piv.n_reporting_establishments_december_stock],
                        tr("t_june", lang): [_n(x, 0, lang) if pd.notna(x) else tr("absent", lang) for x in piv.value_june_stock],
                        tr("t_n_june", lang): [_n(x, 0, lang) if pd.notna(x) else tr("absent", lang) for x in piv.n_reporting_establishments_june_stock],
                        tr("t_ratio", lang): [_n(x, 2, lang) if pd.notna(x) else tr("na", lang) for x in piv.ratio_june_december]})
    numeric = piv.copy(); numeric["variant"] = variant
    numeric = pd.concat([numeric, pd.DataFrame(ratio_rows).assign(block="ratios"), pd.DataFrame(scatter_rows).assign(block="p2_establishment_patterns_scatter"),
                         pd.DataFrame(pat_rows).assign(block="reporting_patterns")], ignore_index=True, sort=False)
    tw = tr("table", lang)
    paths = write_table(variant, lang, "S5_june_december", fmt, numeric,
                        {"es": f"{tw} S5. Stocks REM de junio y diciembre por serie, código, era y año, con establecimientos reportantes y razón junio/diciembre — variante {vl}",
                         "en": f"{tw} S5. REM June and December stocks by series, code, era and year, with reporting establishments and June/December ratio — {vl} variant"}[lang],
                        {"es": "Personas bajo control en el corte de junio (MES=06) y de diciembre (MES=12); los semestres nunca se suman. Establecimientos = IdEstablecimiento distintos con fila del código en ese mes. "
                               "TGD amplio 2019–2020 y autismo estricto 2021–2025 son definiciones distintas. La versión numérica añade bloques con las razones, los patrones de reporte por establecimiento y el resumen de la dispersión. Conteos administrativos, no prevalencia.",
                         "en": "People under control at the June (MES=06) and December (MES=12) cuts; semesters are never summed. Establishments = distinct IdEstablecimiento with a row for the code in that month. "
                               "Broad PDD 2019–2020 and strict autism 2021–2025 are different definitions. The numeric version adds blocks with the ratios, establishment reporting patterns and the scatter summary. Administrative counts, not prevalence."}[lang])
    return str(path), paths


# ===========================================================================
# S6 · Panel estable frente a todos los establecimientos
# ===========================================================================
def figure_s6(D: Data, variant: str, lang: str) -> tuple[str, list[str]]:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    v = variant
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    rows = []

    def panel(axis, segments, col, letter_, title, ylabel, measure, pandemic_pos=0.50):
        """segments: lista de (frame, es_broad). Cada segmento es una era; nunca se unen."""
        ax2 = axis.twinx(); ax2.spines["right"].set_visible(True); ax2.grid(False)
        ymax = 0
        # Los establecimientos reportantes iban girados 90° sobre cada barra y cruzaban la línea de retención
        # del eje gemelo, sus rótulos de porcentaje y los rótulos de contexto. Pasan a la segunda línea de la
        # marca de cada año, que es donde pertenece un dato por año.
        n_by_year: dict = {}
        for frame, broad in segments:
            c = GREY if broad else col
            x = frame.year.values
            axis.bar(x - 0.2, frame.total, width=0.38, color=c, alpha=0.9, label=f"{tr('all_estab', lang)}{' · ' + tr('broad_label', lang) if broad else ''}")
            axis.bar(x + 0.2, frame.stable_panel_total, width=0.38, color="white", edgecolor=c, hatch="////", lw=1.2,
                     label=f"{tr('stable_panel', lang)} (n={_n(frame.n_stable_panel_establishments.iloc[0], 0, lang)}){' · ' + tr('broad_label', lang) if broad else ''}")
            share = 100 * frame.stable_panel_total / frame.total
            ax2.plot(x, share, "o-" if not broad else "o:", color=DARK, lw=1.6, ms=5, label=tr("share_vol", lang) if not broad else None, zorder=5)
            for r, s in zip(frame.itertuples(), share):
                n_by_year[int(r.year)] = int(r.n_reporting_establishments)
                _ann(ax2, r.year, s, _pct(s, lang, 0), DARK, fs=6.5, dx=5, dy=2, ha="left", bbox=True)  # a la derecha del punto: no choca con el rótulo n= rotado
                rows.append(dict(panel=letter_, series=f"{title} · {tr('broad_label', lang)}" if broad else title, code=r.code, variant_row=r.variant, era=r.era, measure=measure, year=int(r.year), total=r.total,
                                 n_reporting_establishments=r.n_reporting_establishments, n_stable_panel_establishments=r.n_stable_panel_establishments,
                                 stable_panel_total=r.stable_panel_total, share_volume_retained=s, share_establishments_retained=100 * r.n_stable_panel_establishments / r.n_reporting_establishments))
            ymax = max(ymax, frame.total.max())
        yrs = sorted({int(y) for fr, _ in segments for y in fr.year})
        # la leyenda ocupa el tercio superior de la celda: el techo se sube para que ni las barras ni los
        # rótulos «n=» rotados lleguen hasta ella
        axis.set_xticks(yrs)
        axis.set_xticklabels([f"{y}\n{_n(n_by_year.get(y, np.nan), 0, lang)}" if y in n_by_year else str(y) for y in yrs],
                             fontsize=FS_MIN + 0.2)
        axis.set_xlim(min(yrs) - 0.6, max(yrs) + 0.6); axis.set_ylim(0, ymax * 2.2)
        ax2.set_ylim(0, 173); ax2.set_ylabel(tr("u_share", lang), fontsize=FS_BASE)
        if len(segments) > 1:
            _break_marker(axis, 2020.5, lang, y=0.64)
        # La banda 0,72–0,45 queda libre entre el pie de la leyenda y el techo de las barras; el rótulo del
        # sombreado y el de la Ley se escriben una sola vez en la lámina, en el panel (b), que no lleva
        # marcador de quiebre y tiene esa banda entera para ellos.
        _context(axis, lang, pandemic_pos=0.62, law_pos=0.62, pandemic_x_offset=0.55,
                 pandemic_text=letter_ == "b", law_text=letter_ == "b")
        # La línea de retención del eje gemelo es la serie que da sentido al panel y tiene que verse ENTERA:
        # con el intercambio de planos anterior las barras se pintaban encima de ella y la partían.
        # `twinx` ya deja el fondo del gemelo transparente, de modo que basta con no invertir el orden.
        h1, l1 = axis.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        plate_legend(axis, h1 + h2, l1 + l2, loc="upper left")
        axis.set_xlabel(f"{tr('year', lang)} · {tr('n_estab', lang)}"); axis.set_ylabel(ylabel)
        panel_head(axis, letter_, title)

    panel(ax[0, 0], [(D.row(CFG.A05_BROAD_PRE2021["entry"], "broad_pre2021"), True), (D.row(CFG.STRICT["a05_entry"], "strict_autism"), False)], OK[0], "a", tr("s6_a", lang), tr("u_entries_only", lang), "annual_sum")
    panel(ax[0, 1], [(D.family(v, "a05_entry"), False)], OK[0], "b", tr("s6_b", lang), tr("u_entries_only", lang), "annual_sum")
    panel(ax[1, 0], [(D.row(CFG.P2_TEA, measure="december_stock"), False)], OK[3], "c", tr("s6_c", lang), tr("u_stock_dec", lang), "december_stock", pandemic_pos=0.70)
    panel(ax[1, 1], [(D.row(CFG.P6_BROAD_PRE2021["primary"], "broad_pre2021", "december_stock"), True), (D.row(CFG.STRICT["p6_primary"], "strict_autism", "december_stock"), False)], OK[4], "d", tr("s6_d", lang), tr("u_stock_dec", lang), "december_stock")
    panel(ax[2, 0], [(D.row(CFG.P6_BROAD_PRE2021["specialty"], "broad_pre2021", "december_stock"), True), (D.row(CFG.STRICT["p6_specialty"], "strict_autism", "december_stock"), False)], OK[5], "e", tr("s6_e", lang), tr("u_stock_dec", lang), "december_stock")

    # F — resumen de retención
    f = ax[2, 1]
    summary = [(tr("a05_strict_short", lang), D.row(CFG.STRICT["a05_entry"], "strict_autism"), OK[0]),
               (tr("a05_family_short", lang), D.family(v, "a05_entry"), OK[2]),
               (tr("p2_short", lang), D.row(CFG.P2_TEA, measure="december_stock"), OK[3]),
               (tr("p6p_short", lang), D.row(CFG.STRICT["p6_primary"], "strict_autism", "december_stock"), OK[4]),
               (tr("p6s_short", lang), D.row(CFG.STRICT["p6_specialty"], "strict_autism", "december_stock"), OK[5])]
    from matplotlib.lines import Line2D
    handles = []
    for lab, frame, col in summary:
        sv = 100 * frame.stable_panel_total / frame.total
        se = 100 * frame.n_stable_panel_establishments / frame.n_reporting_establishments
        f.plot(frame.year, sv, "o-", color=col, lw=2.0, ms=6)
        f.plot(frame.year, se, "s--", color=col, lw=1.2, ms=4.5, alpha=0.6)
        handles.append(Line2D([0], [0], color=col, lw=2.0, marker="o", ms=5, label=lab))
    # leyenda compacta: color = serie; estilo = volumen (línea continua) o establecimientos (discontinua)
    handles += [Line2D([0], [0], color=DARK, lw=2.0, marker="o", ms=5, ls="-", label=tr("share_vol", lang)),
                Line2D([0], [0], color=DARK, lw=1.2, marker="s", ms=4, ls="--", alpha=0.6, label=tr("share_est", lang))]
    f.set_xticks(CFG.YEARS_STOCK); f.set_xlim(2018.4, 2025.6); f.set_ylim(0, 150)
    _context(f, lang, pandemic_pos=0.66, law_pos=0.66, pandemic_text=False, law_text=False)
    f.set_xlabel(tr("year", lang)); f.set_ylabel("%")
    plate_note(f, tr("stable_def", lang), x=0.01, y=0.02, ha="left", va="bottom", color="#555555").set_gid(C.PLATE_KEEP)
    plate_legend(f, handles=handles, loc="upper left", ncol=2, handlelength=1.8, columnspacing=0.8); panel_head(f, "f", tr("s6_f", lang))

    path = save_plate(fig, fdir / "figS6_rem_stable_panel.png")
    plt.close(fig)
    fw = tr("figure", lang); vl = vlab(variant, lang)
    cap = {"title": {"es": f"{fw} S6. Panel estable de establecimientos frente a todos los establecimientos reportantes en REM A05, P2 y P6, 2019–2025 — variante {vl}",
                     "en": f"{fw} S6. Stable establishment panel versus all reporting establishments in REM A05, P2 and P6, 2019–2025 — {vl} variant"}[lang],
           "caption": {"es": ("Barras llenas: total nacional sobre todos los establecimientos con fila del código en el año (n = establecimientos reportantes); barras rayadas: total restringido al panel estable, "
                              "definido como los establecimientos con fila del código (o familia) en cada año de su era de definición (diciembre para los stocks); línea negra (eje derecho): porcentaje del volumen retenido por el panel estable. "
                              "(a) A05 ingresos: TGD amplio 2019–2020 (06902600, gris, panel estable propio de 395 establecimientos) y autismo estricto 2021–2025 (05990022, panel de 258), separados por el marcador de quiebre. "
                              f"(b) A05 ingresos de la familia TGD de la variante ({D.family_code(v, 'a05_entry').replace('+', ', ')}), 2021–2025. (c) P2 TEA en diciembre (P2500500), 2019–2025, panel de 193. "
                              "(d) P6 APS en diciembre: TGD amplio 2019–2020 (P6223000, panel de 594) y autismo estricto 2021–2025 (P6241010, panel de 353). (e) P6 especialidad: TGD amplio (P6223380, panel de 104) y autismo estricto (P6241060, panel de 68). "
                              "(f) Porcentaje del volumen (círculos) y de los establecimientos (cuadrados) retenidos por el panel estable, por serie y año, eras 2021–2025 (y 2019–2025 para P2). "
                              "La caída de la proporción retenida indica que el crecimiento de los totales se concentra en establecimientos que se incorporan al reporte; unidades: ingresos (flujo, A–B) y personas bajo control en diciembre (stock, C–E). "
                              "Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto. Conteos administrativos, no prevalencia."),
                       "en": ("Filled bars: national total over all establishments with a row for the code in the year (n = reporting establishments); hatched bars: total restricted to the stable panel, "
                              "defined as establishments with a row for the code (or family) in every year of its definition era (December for stocks); black line (right axis): percentage of the volume retained by the stable panel. "
                              "(a) A05 entries: broad PDD 2019–2020 (06902600, grey, own stable panel of 395 establishments) and strict autism 2021–2025 (05990022, panel of 258), separated by the break marker. "
                              f"(b) A05 entries of the variant's PDD family ({D.family_code(v, 'a05_entry').replace('+', ', ')}), 2021–2025. (c) P2 ASD in December (P2500500), 2019–2025, panel of 193. "
                              "(d) P6 primary care in December: broad PDD 2019–2020 (P6223000, panel of 594) and strict autism 2021–2025 (P6241010, panel of 353). (e) P6 specialty: broad PDD (P6223380, panel of 104) and strict autism (P6241060, panel of 68). "
                              "(f) Percentage of the volume (circles) and of the establishments (squares) retained by the stable panel, by series and year, eras 2021–2025 (2019–2025 for P2). "
                              "A falling retained share indicates that growth in the totals is concentrated in establishments joining the reporting base; units: entries (flow, A–B) and people under control in December (stock, C–E). "
                              "Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context. Administrative counts, not prevalence.")}[lang]}
    merge_json(fdir / "captions.json", {"figS6_rem_stable_panel": cap})
    tab = pd.DataFrame(rows); tab["variant"] = variant
    fmt = pd.DataFrame({tr("t_panel", lang): tab.panel, tr("t_series", lang): tab.series, tr("t_code", lang): tab.code, tr("t_era", lang): tab.era, tr("t_measure", lang): [tr_measure(m, lang) for m in tab.measure],
                        tr("year", lang): tab.year, tr("t_value", lang): [_n(x, 0, lang) for x in tab.total], tr("t_n_est", lang): [_n(x, 0, lang) for x in tab.n_reporting_establishments],
                        tr("t_n_stable", lang): [_n(x, 0, lang) for x in tab.n_stable_panel_establishments], tr("t_stable_total", lang): [_n(x, 0, lang) for x in tab.stable_panel_total],
                        tr("t_share_vol", lang): [_n(x, 1, lang) for x in tab.share_volume_retained], tr("t_share_est", lang): [_n(x, 1, lang) for x in tab.share_establishments_retained]})
    tw = tr("table", lang)
    paths = write_table(variant, lang, "S6_stable_panel", fmt, tab,
                        {"es": f"{tw} S6. Totales REM sobre todos los establecimientos y sobre el panel estable, con porcentajes de volumen y de establecimientos retenidos — variante {vl}",
                         "en": f"{tw} S6. REM totals over all establishments and over the stable panel, with percentages of volume and establishments retained — {vl} variant"}[lang],
                        {"es": "Panel estable = establecimientos con fila del código (o familia) en cada año de su era (diciembre para stocks); las eras TGD amplio 2019–2020 y autismo 2021–2025 tienen paneles distintos y no son comparables. "
                               "Flujos = suma de meses; stocks = diciembre. Conteos administrativos, no prevalencia.",
                         "en": "Stable panel = establishments with a row for the code (or family) in every year of its era (December for stocks); the broad-PDD 2019–2020 and autism 2021–2025 eras have different panels and are not comparable. "
                               "Flows = sum of months; stocks = December. Administrative counts, not prevalence."}[lang])
    return str(path), paths


# ===========================================================================
# S7 · A05 tasas brutas y estandarizadas por edad (OMS) por sexo
# ===========================================================================
def a05_rates(D: Data, variant: str) -> pd.DataFrame:
    """Tasas por 100.000 habitantes INE (base 2017, nacional) de ingresos A05 por año y sexo: brutas (Poisson exacto) y estandarizadas OMS (Fay–Feuer)."""
    age = D.age[(D.age.flow == "entry") & (D.age.age_group != "total")].copy()
    age["sex"] = age.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    sel = {"strict": (age.variant == "single_code") & (age.category == "autism"),
           "family": (age.variant == variant),
           "broad": (age.variant == "single_code") & (age.category == "broad_pdd")}
    out = []
    for key, mask in sel.items():
        cells = age[mask]
        for year in sorted(cells.year.unique()):
            for sex in ["HOMBRE", "MUJER", "TOTAL"]:
                cy = cells[cells.year == year] if sex == "TOTAL" else cells[(cells.year == year) & (cells.sex == sex)]
                counts = cy.groupby("age_group")["count"].sum(min_count=1).reindex(AGE_GROUPS)
                n_missing = int(counts.isna().sum()); counts = counts.fillna(0.0)
                pop = D.ine[(D.ine.year == year) & (D.ine.sex == sex)].set_index("age_group").population.reindex(AGE_GROUPS).astype(float)
                frame = pd.DataFrame({"age_group": AGE_GROUPS, "count": counts.values, "population": pop.values})
                ds = direct_standardization(frame)
                k, P = float(counts.sum()), float(pop.sum())
                crude, lo, hi = C.rate_per(k, P)
                out.append(dict(series=key, variant=variant, year=int(year), sex=sex, code=cy.code.iloc[0], count=k, population=P, crude=crude, crude_lo=lo, crude_hi=hi,
                                asr=ds["asr"], asr_lo=ds["asr_lo"], asr_hi=ds["asr_hi"], asr_var=ds["asr_var"], n_reporting_establishments=int(cy.n_reporting_establishments.max()),
                                n_age_cells_missing=n_missing))
    return pd.DataFrame(out)


def age_specific(D: Data, variant: str, key: str, year: int, sex: str, groups: list[str]) -> pd.DataFrame:
    age = D.age[(D.age.flow == "entry") & (D.age.age_group != "total")].copy()
    age["sex"] = age.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    mask = {"strict": (age.variant == "single_code") & (age.category == "autism"), "family": (age.variant == variant),
            "broad": (age.variant == "single_code") & (age.category == "broad_pdd")}[key]
    cy = age[mask & (age.year == year)]
    if sex != "TOTAL":
        cy = cy[cy.sex == sex]
    counts = cy.groupby("age_group")["count"].sum(min_count=1).reindex(groups).fillna(0.0)
    pop = D.ine[(D.ine.year == year) & (D.ine.sex == sex)].set_index("age_group").population.reindex(groups).astype(float)
    lo, hi = poisson_limits(counts.values)
    return pd.DataFrame({"age_group": groups, "count": counts.values, "population": pop.values, "rate": PER * counts.values / pop.values,
                         "rate_lo": PER * lo / pop.values, "rate_hi": PER * hi / pop.values})


def figure_s7(D: Data, variant: str, lang: str, rates: pd.DataFrame) -> tuple[str, list[str]]:
    """Lámina vertical de 180 × 245 mm con la norma del estudio: tres filas por dos columnas.

    La versión anterior era una lámina apaisada de 17 × 10,8 pulgadas con la rejilla al revés (2 × 3), fuera
    de la norma: los seis paneles son los mismos y llevan el mismo contenido, reordenados por columnas."""
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas

    def rates_panel(axis, key, title, letter_, law=True):
        r = rates[rates.series == key]
        for sex in ["HOMBRE", "MUJER", "TOTAL"]:
            s = r[r.sex == sex].sort_values("year")
            axis.plot(s.year, s.crude, "o:", color=SEXCOL[sex], lw=1.1, ms=3.0, label=f"{tr(sex, lang)} · {tr('crude', lang)}")
            axis.plot(s.year, s.asr, "s-", color=SEXCOL[sex], lw=1.5, ms=3.4, label=f"{tr(sex, lang)} · {tr('asr', lang)}")
            axis.fill_between(s.year, s.asr_lo, s.asr_hi, color=SEXCOL[sex], alpha=0.13)
        tot = r[r.sex == "TOTAL"].sort_values("year")
        yrs = tot.year.tolist()
        axis.set_xticks(yrs)
        axis.set_xticklabels([f"{int(t.year)}\n{_n(t.n_reporting_establishments, 0, lang)}" for t in tot.itertuples()],
                             fontsize=FS_MIN + 0.2)
        # banda superior reservada para la leyenda de seis entradas
        axis.set_xlim(min(yrs) - 0.5, max(yrs) + 0.5); axis.set_ylim(0, r.asr_hi.max() * 3.4)
        _context(axis, lang, law=law, pandemic_pos=0.985, law_pos=0.90, fs=FS_MIN)
        axis.set_xlabel(f"{tr('year', lang)} · {tr('n_estab', lang)}"); axis.set_ylabel(tr("u_rate", lang), fontsize=FS_MIN)
        plate_legend(axis, loc="upper left", fs=FS_MIN, ncol=2, columnspacing=0.7, handlelength=1.2)
        panel_head(axis, letter_, title)

    rates_panel(ax[0, 0], "strict", tr("s7_a", lang), "a")
    rates_panel(ax[0, 1], "family", tr("s7_b", lang), "b")
    # c — razón H:M de las TEE
    c = ax[1, 0]
    ratio_rows = []
    for key, col, mk, lab in [("strict", OK[0], "o", tr("strict_short", lang)), ("family", OK[2], "s", tr("family_short", lang)), ("broad", GREY, "^", tr("broad_label", lang))]:
        r = rates[rates.series == key]
        m = r[r.sex == "HOMBRE"].merge(r[r.sex == "MUJER"], on="year", suffixes=("_m", "_f")).sort_values("year")
        ratio = m.asr_m / m.asr_f
        se = np.sqrt(m.asr_var_m / m.asr_m ** 2 + m.asr_var_f / m.asr_f ** 2)
        lo, hi = ratio * np.exp(-Z * se), ratio * np.exp(Z * se)
        c.errorbar(m.year, ratio, yerr=[ratio - lo, hi - ratio], fmt=mk + ("-" if key != "broad" else ":"), color=col, capsize=1.6, ms=3.4, lw=1.4 if key != "broad" else 1.0, label=lab)
        for yr, rt, l_, h_ in zip(m.year, ratio, lo, hi):
            ratio_rows.append(dict(series=key, year=int(yr), mf_ratio_asr=rt, mf_ratio_lo=l_, mf_ratio_hi=h_))
    c.axhline(3, color="#999999", ls=":", lw=1.0); c.text(2025.75, 3.05, "3:1", fontsize=FS_MIN, color="#777777", va="bottom", ha="right")
    c.axhline(4, color="#bbbbbb", ls=":", lw=1.0); c.text(2025.75, 4.05, "4:1", fontsize=FS_MIN, color="#999999", va="bottom", ha="right")
    c.set_xticks(CFG.YEARS_STOCK); c.set_xlim(2018.4, 2025.9); c.set_ylim(0, 8.4)
    _break_marker(c, 2020.5, lang, y=0.86)
    _context(c, lang, pandemic_pos=0.985, law_pos=0.985, pandemic_text=False, law_text=False, fs=FS_MIN)
    c.set_xlabel(tr("year", lang)); c.set_ylabel(tr("ratio_axis", lang), fontsize=FS_MIN + 1)
    plate_legend(c, loc="lower right", fs=FS_MIN)
    panel_head(c, "c", tr("s7_c", lang))
    # d — tasas por edad y sexo, 2021 y 2025 (estricto)
    d = ax[1, 1]
    groups = AGE_GROUPS[:8]
    x = np.arange(len(groups))
    spec_rows = []
    d_hi = 0.0
    for year, ls, mk, off in [(2021, ":", "o", -0.1), (2025, "-", "s", 0.1)]:
        for sex in ["HOMBRE", "MUJER"]:
            s = age_specific(D, variant, "strict", year, sex, groups)
            d.errorbar(x + off, s.rate, yerr=[s.rate - s.rate_lo, s.rate_hi - s.rate], fmt=mk, ls=ls, color=SEXCOL[sex], capsize=1.6, ms=3.2, lw=1.3, label=f"{tr(sex, lang)} {year}")
            d_hi = max(d_hi, float(np.nanmax(s.rate_hi)) if len(s) else 0.0)
            for r in s.itertuples():
                spec_rows.append(dict(series="strict", year=year, sex=sex, age_group=r.age_group, count=r.count, population=r.population, rate=r.rate, rate_lo=r.rate_lo, rate_hi=r.rate_hi))
    d.set_xticks(x); d.set_xticklabels(groups, rotation=45, ha="right", fontsize=FS_MIN + 0.2)
    d.set_ylim(0, d_hi * 1.9)          # banda superior reservada para la leyenda
    d.set_xlabel(tr("age_axis", lang)); d.set_ylabel(tr("u_rate", lang), fontsize=FS_MIN + 1)
    plate_legend(d, loc="upper right", fs=FS_MIN, ncol=2, columnspacing=0.7)
    panel_head(d, "d", tr("s7_d", lang))
    # e — tasas por edad, ambos sexos, por año (log)
    e = ax[2, 0]
    e_hi = 0.0
    for year in range(2021, 2026):
        s = age_specific(D, variant, "strict", year, "TOTAL", groups)
        n_est = int(rates[(rates.series == "strict") & (rates.year == year) & (rates.sex == "TOTAL")].n_reporting_establishments.iloc[0])
        e.plot(x, s.rate.replace(0, np.nan), "o-", color=YEARCOL[year], lw=1.4, ms=3.2, label=f"{year} (n={_n(n_est, 0, lang)})")
        e.fill_between(x, s.rate_lo.replace(0, np.nan), s.rate_hi, color=YEARCOL[year], alpha=0.10)
        e_hi = max(e_hi, float(np.nanmax(s.rate_hi)) if len(s) else 0.0)
        for r in s.itertuples():
            spec_rows.append(dict(series="strict", year=year, sex="TOTAL", age_group=r.age_group, count=r.count, population=r.population, rate=r.rate, rate_lo=r.rate_lo, rate_hi=r.rate_hi))
    e.set_yscale("log"); e.set_xticks(x); e.set_xticklabels(groups, rotation=45, ha="right", fontsize=FS_MIN + 0.2)
    e.set_ylim(top=e_hi * 9.0)         # banda superior reservada para la leyenda de cinco años
    e.set_xlabel(tr("age_axis", lang)); e.set_ylabel(tr("u_rate_log", lang), fontsize=FS_MIN + 1)
    plate_legend(e, loc="upper right", fs=FS_MIN, title=tr("n_estab", lang), title_fontsize=FS_MIN, ncol=2, columnspacing=0.7)
    panel_head(e, "e", tr("s7_e", lang))
    # f — TGD amplio 2019–2020 (definición distinta)
    f = ax[2, 1]
    rb = rates[rates.series == "broad"]
    for sex in ["HOMBRE", "MUJER", "TOTAL"]:
        s = rb[rb.sex == sex].sort_values("year")
        f.errorbar(s.year - 0.05, s.crude, yerr=[s.crude - s.crude_lo, s.crude_hi - s.crude], fmt="o", ls=":", color=SEXCOL[sex], capsize=1.6, ms=3.2, lw=1.1, label=f"{tr(sex, lang)} · {tr('crude', lang)}")
        f.errorbar(s.year + 0.05, s.asr, yerr=[s.asr - s.asr_lo, s.asr_hi - s.asr], fmt="s", ls="-", color=SEXCOL[sex], capsize=1.6, ms=3.2, lw=1.5, label=f"{tr(sex, lang)} · {tr('asr', lang)}")
    tot = rb[rb.sex == "TOTAL"].sort_values("year")
    f.set_xticks(tot.year.tolist())
    f.set_xticklabels([f"{int(t.year)}\n{_n(t.n_reporting_establishments, 0, lang)}" for t in tot.itertuples()], fontsize=FS_MIN + 0.2)
    f.set_xlim(2018.5, 2020.5); f.set_ylim(0, rb.asr_hi.max() * 2.6)
    _context(f, lang, shade=(2020,), law=False, pandemic_pos=0.985, fs=FS_MIN)
    f.set_xlabel(f"{tr('year', lang)} · {tr('n_estab', lang)}"); f.set_ylabel(tr("u_rate", lang), fontsize=FS_MIN + 1)
    plate_legend(f, loc="upper left", fs=FS_MIN, ncol=2, columnspacing=0.7, handlelength=1.2)
    panel_head(f, "f", tr("s7_f", lang))

    path = save_plate(fig, fdir / "figS7_a05_standardised_rates.png")
    plt.close(fig)
    fw = tr("figure", lang); vl = vlab(variant, lang)
    fam = D.family_code(variant, "a05_entry").replace("+", ", ")
    cap = {"title": {"es": f"{fw} S7. Ingresos REM A05 por 100.000 habitantes: tasas brutas y estandarizadas por edad (OMS) por sexo y año, 2021–2025, con TGD amplio 2019–2020 como sensibilidad — variante {vl}",
                     "en": f"{fw} S7. REM A05 entries per 100,000 population: crude and WHO age-standardised rates by sex and year, 2021–2025, with broad PDD 2019–2020 as sensitivity — {vl} variant"}[lang],
           "caption": {"es": ("Numerador: ingresos al programa de salud mental (A05) sumados sobre las celdas edad × sexo (17 grupos quinquenales, COL04–COL37) de las filas en era; denominador: población residente INE (proyección base 2017, 30 de junio, nacional). "
                              "El numerador se localiza por lugar de atención en la red pública y el denominador por residencia (toda la población, asegurada o no): las tasas son razones de reconocimiento administrativo por población, no incidencia. "
                              "Tasas brutas con IC exactos de Poisson; tasas estandarizadas por el estándar mundial OMS con IC de Fay–Feuer; n = establecimientos reportantes del código o familia en el año. "
                              f"(A) Autismo estricto (05990022). (B) Familia TGD de la variante ({fam}). (C) Razón hombre:mujer de las tasas estandarizadas (IC 95 % por aproximación log-normal) para autismo estricto, familia TGD y TGD amplio 2019–2020 "
                              "(definición distinta, separada por el marcador de quiebre); referencias 3:1 y 4:1. (D) Tasas específicas por edad y sexo del autismo estricto en 2021 y 2025 (grupos 0–39 años; IC exactos de Poisson). "
                              "(E) Tasas específicas por edad, ambos sexos, por año 2021–2025 (escala logarítmica; bandas: IC exactos). (F) TGD amplio 2019–2020 (06902600) por sexo, bruta y estandarizada: definición no comparable con 2021+ y afectada por la disrupción de 2020. "
                              "Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 como contexto."),
                       "en": ("Numerator: mental-health programme entries (A05) summed over the age × sex cells (17 five-year groups, COL04–COL37) of in-era rows; denominator: INE resident population (base-2017 projection, 30 June, national). "
                              "The numerator is located by place of care in the public network and the denominator by residence (whole population, insured or not): the rates are administrative-recognition ratios per population, not incidence. "
                              "Crude rates with exact Poisson CI; rates standardised to the WHO world standard with Fay–Feuer CI; n = establishments reporting the code or family in the year. "
                              f"(A) Strict autism (05990022). (B) Variant PDD family ({fam}). (C) Male:female ratio of standardised rates (95% CI by log-normal approximation) for strict autism, PDD family and broad PDD 2019–2020 "
                              "(different definition, separated by the break marker); 3:1 and 4:1 reference lines. (D) Age- and sex-specific rates of strict autism in 2021 and 2025 (ages 0–39; exact Poisson CI). "
                              "(E) Age-specific rates, both sexes, by year 2021–2025 (log scale; bands: exact CI). (F) Broad PDD 2019–2020 (06902600) by sex, crude and standardised: definition not comparable with 2021+ and affected by the 2020 disruption. "
                              "Shading: 2020–2021 reporting disruption; dotted line: Law 21.545 as context.")}[lang]}
    merge_json(fdir / "captions.json", {"figS7_a05_standardised_rates": cap})
    # tabla
    r = rates.sort_values(["series", "year", "sex"]).copy()
    ser = {"strict": tr("m_strict", lang), "family": tr("m_family", lang), "broad": tr("m_broad", lang)}
    fmt = pd.DataFrame({tr("t_series", lang): r.series.map(ser), tr("t_code", lang): r.code, tr("year", lang): r.year, tr("t_sex", lang): [tr(s, lang) for s in r.sex],
                        tr("t_count", lang): [_n(x, 0, lang) for x in r["count"]], tr("t_pop", lang): [_n(x, 0, lang) for x in r.population],
                        tr("t_crude", lang): [f"{_n(a, 1, lang)} ({_ci(b, c_, 1, lang)})" for a, b, c_ in zip(r.crude, r.crude_lo, r.crude_hi)],
                        tr("t_asr", lang): [f"{_n(a, 1, lang)} ({_ci(b, c_, 1, lang)})" for a, b, c_ in zip(r.asr, r.asr_lo, r.asr_hi)],
                        tr("t_n_est", lang): [_n(x, 0, lang) for x in r.n_reporting_establishments]})
    numeric = pd.concat([r, pd.DataFrame(ratio_rows).assign(block="mf_ratio"), pd.DataFrame(spec_rows).assign(block="age_specific")], ignore_index=True, sort=False)
    tw = tr("table", lang)
    paths = write_table(variant, lang, "S7_a05_standardised_rates", fmt, numeric,
                        {"es": f"{tw} S7. Ingresos REM A05 por 100.000 habitantes INE: tasas brutas y estandarizadas por edad (OMS) por serie, año y sexo, con establecimientos reportantes — variante {vl}",
                         "en": f"{tw} S7. REM A05 entries per 100,000 INE population: crude and WHO age-standardised rates by series, year and sex, with reporting establishments — {vl} variant"}[lang],
                        {"es": "Numerador por lugar de atención (red pública); denominador por residencia (INE base 2017, 30 de junio). Bruta: IC exacto de Poisson; estandarizada: estándar OMS, IC de Fay–Feuer. "
                               "TGD amplio 2019–2020 es otra definición. La versión numérica añade las razones H:M de tasas estandarizadas y las tasas específicas por edad. Reconocimiento administrativo por población, no incidencia.",
                         "en": "Numerator by place of care (public network); denominator by residence (INE base 2017, 30 June). Crude: exact Poisson CI; standardised: WHO standard, Fay–Feuer CI. "
                               "Broad PDD 2019–2020 is a different definition. The numeric version adds the M:F ratios of standardised rates and the age-specific rates. Administrative recognition per population, not incidence."}[lang])
    return str(path), paths


# ===========================================================================
# S8 · A05 ingresos por grupo de edad y sexo por año
# ===========================================================================
HEAT_GROUPS = AGE_GROUPS[:10] + ["50+"]


def age_matrix(D: Data, variant: str, key: str, sex: str) -> tuple[pd.DataFrame, pd.Series]:
    """Matriz grupo de edad × año de ingresos (celdas ausentes = NaN) y establecimientos reportantes por año."""
    age = D.age[(D.age.flow == "entry") & (D.age.age_group != "total")].copy()
    age["sex"] = age.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    mask = {"strict": (age.variant == "single_code") & (age.category == "autism"), "family": (age.variant == variant)}[key]
    a = age[mask & (age.sex == sex)].copy()
    a["grp"] = np.where(a.age_group.isin(AGE_GROUPS[:10]), a.age_group, "50+")
    m = a.groupby(["grp", "year"])["count"].sum(min_count=1).unstack("year").reindex(HEAT_GROUPS)
    n = a.groupby("year")["n_reporting_establishments"].max()
    return m, n


def figure_s8(D: Data, variant: str, lang: str) -> tuple[str, list[str]]:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    cmap = sns.color_palette("crest", as_cmap=True)
    rows = []

    def heat(axis, key, sex, title, letter_):
        m, n = age_matrix(D, variant, key, sex)
        years = m.columns.tolist()
        vals = m.values.astype(float)
        im = axis.imshow(np.where(np.isnan(vals), 0, vals), cmap=cmap, aspect="auto", vmin=0, vmax=np.nanmax(vals))
        axis.grid(False)
        for i in range(vals.shape[0]):
            for j in range(vals.shape[1]):
                v_ = vals[i, j]
                txt = tr("na", lang) if np.isnan(v_) else _n(v_, 0, lang)
                axis.text(j, i, txt, ha="center", va="center", fontsize=FS_MIN + 0.3, color="white" if (not np.isnan(v_) and v_ > 0.55 * np.nanmax(vals)) else DARK)
                rows.append(dict(series=key, sex=sex, age_group=HEAT_GROUPS[i], year=int(years[j]), count=v_, n_reporting_establishments=int(n.get(years[j], np.nan))))
        axis.set_xticks(range(len(years))); axis.set_xticklabels([f"{y}\nn={_n(n[y], 0, lang)}" for y in years], fontsize=FS_MIN + 0.2)
        axis.set_yticks(range(len(HEAT_GROUPS))); axis.set_yticklabels(HEAT_GROUPS, fontsize=FS_MIN + 0.5)
        axis.set_xlabel(f"{tr('year', lang)} ({tr('n_estab', lang)})"); axis.set_ylabel(tr("age_axis", lang))
        cb = fig.colorbar(im, ax=axis, fraction=0.04, pad=0.02); cb.set_label(tr("u_entries_count", lang), fontsize=8); cb.ax.tick_params(labelsize=7)
        panel_head(axis, letter_, title)

    heat(ax[0, 0], "strict", "HOMBRE", tr("s8_a", lang), "a")
    heat(ax[0, 1], "strict", "MUJER", tr("s8_b", lang), "b")
    heat(ax[2, 0], "family", "HOMBRE", tr("s8_e", lang), "e")
    heat(ax[2, 1], "family", "MUJER", tr("s8_f", lang), "f")

    # C — distribución por edad (%) del autismo estricto, ambos sexos
    c = ax[1, 0]
    mm, nm = age_matrix(D, variant, "strict", "HOMBRE"); mf, nf = age_matrix(D, variant, "strict", "MUJER")
    tot = mm.fillna(0) + mf.fillna(0)
    bands = [("0-4", ["0-4"]), ("5-9", ["5-9"]), ("10-14", ["10-14"]), ("15-19", ["15-19"]), ("20-29", ["20-24", "25-29"]), (tr("age_30plus", lang), ["30-34", "35-39", "40-44", "45-49", "50+"])]
    years = tot.columns.tolist()
    share = pd.DataFrame({lab: tot.loc[grps].sum() for lab, grps in bands}).T
    share = 100 * share / share.sum(axis=0)
    bottom = np.zeros(len(years))
    pal = sns.color_palette("crest", len(bands))
    for (lab, _), col in zip(bands, pal):
        c.bar(years, share.loc[lab], bottom=bottom, color=col, width=0.7, label=lab, edgecolor="white")
        for x_, b_, s_ in zip(years, bottom, share.loc[lab]):
            if s_ >= 5:
                c.text(x_, b_ + s_ / 2, _pct(s_, lang, 0), ha="center", va="center", fontsize=FS_MIN + 0.2, color="white" if col[2] < 0.6 else DARK)
        bottom += share.loc[lab].values
        for x_, s_ in zip(years, share.loc[lab]):
            rows.append(dict(series="strict_share", sex="TOTAL", age_group=lab, year=int(x_), count=np.nan, share_pct=s_, n_reporting_establishments=int(nm[x_])))
    c.set_xticks(years); c.set_xticklabels([f"{y}\nn={_n(nm[y], 0, lang)}" for y in years], fontsize=FS_MIN + 0.2); c.set_ylim(0, 100)
    c.set_xlabel(f"{tr('year', lang)} ({tr('n_estab', lang)})"); c.set_ylabel(tr("share_axis", lang))
    c.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=FS_MIN + 0.2, frameon=False, columnspacing=0.8,
             handlelength=1.1, title=tr("age_axis", lang), title_fontsize=FS_MIN + 0.2)
    panel_head(c, "c", tr("s8_c", lang))

    # D — razón H:M de ingresos por grupo de edad y año (estricto)
    d = ax[1, 1]
    groups = AGE_GROUPS[:7]
    x = np.arange(len(groups))
    for k, year in enumerate(years):
        m_ = mm[year].reindex(groups).fillna(0).values; f_ = mf[year].reindex(groups).fillna(0).values
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where((m_ > 0) & (f_ > 0), m_ / f_, np.nan)
            se = np.where((m_ > 0) & (f_ > 0), np.sqrt(1 / np.maximum(m_, 1) + 1 / np.maximum(f_, 1)), np.nan)
        lo, hi = ratio * np.exp(-Z * se), ratio * np.exp(Z * se)
        off = (k - (len(years) - 1) / 2) * 0.12
        d.errorbar(x + off, ratio, yerr=[ratio - lo, hi - ratio], fmt="o-", color=YEARCOL[year], capsize=2, ms=4.5, lw=1.4, label=f"{year} (n={_n(nm[year], 0, lang)})")
        for g_, r_, l_, h_, mc, fc in zip(groups, ratio, lo, hi, m_, f_):
            rows.append(dict(series="strict_mf_ratio", sex="M:F", age_group=g_, year=int(year), count=np.nan, males=mc, females=fc, mf_ratio=r_, mf_lo=l_, mf_hi=h_, n_reporting_establishments=int(nm[year])))
    d.axhline(3, color="#999999", ls=":", lw=1.1); d.text(len(groups) - 0.55, 3.05, "3:1", fontsize=FS_MIN + 0.3, color="#777777")
    d.axhline(1, color="#bbbbbb", ls="--", lw=1.0)
    # Banda superior reservada: la leyenda de cinco años se dibujaba sobre las series de razón H:M y sus
    # intervalos (hasta el 22 % de una de ellas tapada).
    d.set_xticks(x); d.set_xticklabels(groups, rotation=45, ha="right")
    d.set_ylim(0, 14); d.set_yticks([0, 2, 4, 6, 8])
    d.set_xlabel(tr("age_axis", lang)); d.set_ylabel(tr("mf_axis", lang))
    plate_legend(d, loc="upper right", title=tr("n_estab", lang), title_fontsize=FS_MIN + 0.2); panel_head(d, "d", tr("s8_d", lang))

    path = save_plate(fig, fdir / "figS8_a05_age_sex.png")
    plt.close(fig)
    fw = tr("figure", lang); vl = vlab(variant, lang)
    fam = D.family_code(variant, "a05_entry").replace("+", ", ")
    cap = {"title": {"es": f"{fw} S8. Ingresos REM A05 por grupo de edad y sexo por año, 2021–2025: autismo estricto y familia TGD de la variante — variante {vl}",
                     "en": f"{fw} S8. REM A05 entries by age group and sex per year, 2021–2025: strict autism and the variant's PDD family — {vl} variant"}[lang],
           "caption": {"es": ("Ingresos al programa de salud mental (flujo anual) leídos de las celdas edad × sexo (COL04–COL37) de las filas A05 en era, sumadas sobre establecimiento y mes; grupos quinquenales hasta 45–49 y 50+ agrupado; "
                              "n = establecimientos reportantes del código o familia en el año. (a–b) Mapas de calor del autismo estricto (05990022) en hombres y mujeres, con el conteo en cada celda («n/e» = la celda edad × sexo no aparece en ninguna fila del código ese año: ausencia de fila, no un cero). "
                              "(c) Distribución porcentual por banda de edad de los ingresos por autismo estricto, ambos sexos. (d) Razón hombre:mujer de los ingresos por autismo estricto por grupo de edad (0–34 años) y año, con IC 95 % (aproximación log-normal de Poisson); "
                              f"referencias 1:1 y 3:1. (e–f) Mapas de calor de la familia TGD de la variante ({fam}) en hombres y mujeres. "
                              "La suma de las celdas puede diferir en pocas unidades del total COL01 del mismo código (tabla S7 numérica). Conteos administrativos por lugar de atención, no prevalencia."),
                       "en": ("Mental-health programme entries (annual flow) read from the age × sex cells (COL04–COL37) of in-era A05 rows, summed over establishment and month; five-year groups up to 45–49 and 50+ pooled; "
                              "n = establishments reporting the code or family in the year. (a–b) Heat maps of strict autism (05990022) in males and females, with the count in each cell ('n/e' = the age × sex cell appears in no row of the code that year: an absent row, not a zero). "
                              "(c) Percentage distribution by age band of strict-autism entries, both sexes. (d) Male:female ratio of strict-autism entries by age group (0–34 years) and year, with 95% CI (Poisson log-normal approximation); "
                              f"1:1 and 3:1 reference lines. (e–f) Heat maps of the variant's PDD family ({fam}) in males and females. "
                              "The sum of the cells may differ by a few units from the COL01 total of the same code (numeric table S7). Administrative counts by place of care, not prevalence.")}[lang]}
    merge_json(fdir / "captions.json", {"figS8_a05_age_sex": cap})
    tab = pd.DataFrame(rows); tab["variant"] = variant
    heat_rows = tab[tab.series.isin(["strict", "family"])]
    ser = {"strict": tr("m_strict", lang), "family": tr("m_family", lang)}
    fmt = heat_rows.pivot_table(index=["series", "sex", "age_group"], columns="year", values="count", aggfunc="first").reindex(HEAT_GROUPS, level="age_group")
    fmt = fmt.reset_index()
    out = pd.DataFrame({tr("t_series", lang): fmt.series.map(ser), tr("t_sex", lang): [tr(s, lang) for s in fmt.sex], tr("t_age", lang): fmt.age_group})
    for y in [c_ for c_ in fmt.columns if isinstance(c_, (int, np.integer))]:
        out[str(y)] = [_n(x, 0, lang) if pd.notna(x) else tr("na", lang) for x in fmt[y]]
    tw = tr("table", lang)
    paths = write_table(variant, lang, "S8_a05_age_sex", out, tab,
                        {"es": f"{tw} S8. Ingresos REM A05 por grupo de edad, sexo y año (celdas edad × sexo), autismo estricto y familia TGD — variante {vl}",
                         "en": f"{tw} S8. REM A05 entries by age group, sex and year (age × sex cells), strict autism and PDD family — {vl} variant"}[lang],
                        {"es": "Suma de las celdas COL04–COL37 de las filas en era; 50+ agrupa 50–54 a 80+; «n/e» = la celda edad × sexo no aparece en ninguna fila del código ese año (ausencia de fila, que no es un cero). La versión numérica añade la distribución porcentual por edad y las razones H:M con IC 95 %. Conteos administrativos, no prevalencia.",
                         "en": "Sum of the COL04–COL37 cells of in-era rows; 50+ pools 50–54 to 80+; 'n/e' = the age × sex cell appears in no row of the code that year (an absent row, which is not a zero). The numeric version adds the age distribution and the M:F ratios with 95% CI. Administrative counts, not prevalence."}[lang])
    return str(path), paths


# ===========================================================================
# S13 · Estacionalidad mensual (índice respecto de la media anual)
# ===========================================================================
def figure_s13(D: Data, variant: str, lang: str) -> tuple[str, list[str]]:
    plt, sns = plate_style()
    fdir = out_dir(variant, lang, "figures")
    fig, ax = new_plate(plt)
    fig._plate_lang = lang        # idioma de la lámina, para el separador de miles de las marcas
    months = tr("months_abbr", lang)
    rows = []

    def index_panel(axis, series_key, codes, years, title, letter_, era_label=None, note=None, ls_by_year=None, era_text=""):
        g = D.monthly(codes, years)
        for year in sorted(g.year.unique()):
            s = g[g.year == year]
            n_est = int(s.n_year.iloc[0])
            ls = (ls_by_year or {}).get(year, "-")
            lab = f"{year} (n={_n(n_est, 0, lang)})" + (f" · {era_label[year]}" if era_label else "")
            axis.plot(s.month, s["index"], marker="o", ls=ls, color=YEARCOL[year], lw=1.9, ms=4.5, label=lab)
            for r in s.itertuples():
                rows.append(dict(series=series_key, code="+".join(codes), year=int(r.year), month=int(r.month), total=r.total, n_establishments=r.n_est, n_establishments_year=r.n_year, index=r.index,
                                 era=era_label[year] if era_label else era_text))
        axis.axhline(100, color="#888888", ls="--", lw=1.0)
        axis.set_xticks(range(1, 13)); axis.set_xticklabels(months, fontsize=8); axis.set_xlabel(tr("month", lang)); axis.set_ylabel(tr("u_index", lang))
        plate_legend(axis, loc="upper left", ncol=2, title=tr("n_estab", lang), title_fontsize=FS_MIN + 0.2,
                     columnspacing=0.8, handlelength=1.4)
        if note:
            plate_note(axis, note, x=0.99, y=0.02, ha="right", va="bottom", color="#555555")
        panel_head(axis, letter_, title)
        return g

    ga = index_panel(ax[0, 0], "a05_strict", [CFG.STRICT["a05_entry"]], list(range(2021, 2026)), tr("s13_a", lang), "a", era_text="2021–2025")
    ax[0, 0].set_ylim(0, max(180, ga["index"].max() * 1.15))
    gb = index_panel(ax[0, 1], "a05_family", CFG.VARIANTS[variant]["a05_entry"], list(range(2021, 2026)), tr("s13_b", lang), "b", era_text="2021–2025")
    ax[0, 1].set_ylim(0, max(180, gb["index"].max() * 1.15))
    gc = index_panel(ax[1, 0], "a05_broad", [CFG.A05_BROAD_PRE2021["entry"]], [2019, 2020], tr("s13_c", lang), "c", note=tr("pandemic_one", lang).format(y=2020).replace("\n", " "), era_text="2019–2020")
    ax[1, 0].set_ylim(0, max(180, gc["index"].max() * 1.15))
    gd = index_panel(ax[1, 1], "a03_legacy_done", [CFG.A03_LEGACY["mchat_done"]], list(range(2019, 2023)), tr("s13_d", lang), "d", note=tr("feb2019_note", lang), era_text="2019–2022")
    ax[1, 1].set_ylim(0, max(180, gd["index"].max() * 1.30))  # holgura para que el pico de feb. 2019 no toque la leyenda
    era = {2023: tr("era_2023", lang), 2024: tr("era_2023", lang), 2025: tr("era_2025", lang)}
    # 2023–2024 y 2025 son familias de códigos distintas: se calculan por separado y se dibujan como líneas por año (nunca unidas)
    g1 = D.monthly([CFG.A03_2023_2024["low"], CFG.A03_2023_2024["medium"], CFG.A03_2023_2024["high"]], [2023, 2024])
    g2 = D.monthly([CFG.A03_2025["low"], CFG.A03_2025["medium_no_referral"], CFG.A03_2025["medium_referral"], CFG.A03_2025["high_referral"]], [2025])
    e = ax[2, 0]
    for g, codes_txt in [(g1, "09600213+09600214+09600215"), (g2, "03710016+03710017+03710018+03710019")]:
        for year in sorted(g.year.unique()):
            s = g[g.year == year]
            n_est = int(s.n_year.iloc[0])
            e.plot(s.month, s["index"], marker="o", ls="-" if year < 2025 else "--", color=YEARCOL[year], lw=1.9, ms=4.5, label=f"{year} (n={_n(n_est, 0, lang)}) · {era[year]}")
            for r in s.itertuples():
                rows.append(dict(series="a03_mchat_rf_part1", code=codes_txt, year=int(r.year), month=int(r.month), total=r.total, n_establishments=r.n_est, n_establishments_year=r.n_year, index=r.index, era=era[year]))
    e.axhline(100, color="#888888", ls="--", lw=1.0)
    e.set_xticks(range(1, 13)); e.set_xticklabels(months, fontsize=8); e.set_xlabel(tr("month", lang)); e.set_ylabel(tr("u_index", lang))
    e.set_ylim(0, max(180, g1["index"].max() * 1.15, g2["index"].max() * 1.15))
    plate_legend(e, loc="upper left", ncol=1, title=tr("n_estab", lang), title_fontsize=FS_MIN + 0.2); panel_head(e, "e", tr("s13_e", lang))
    # F — establecimientos reportantes por mes (A05 ingresos: TGD amplio 2019–20 discontinua; autismo estricto 2021–25)
    f = ax[2, 1]
    gbroad = D.monthly([CFG.A05_BROAD_PRE2021["entry"]], [2019, 2020]); gstrict = D.monthly([CFG.STRICT["a05_entry"]], list(range(2021, 2026)))
    for g, ls, key in [(gbroad, "--", "a05_broad_estab"), (gstrict, "-", "a05_strict_estab")]:
        for year in sorted(g.year.unique()):
            s = g[g.year == year]
            f.plot(s.month, s.n_est, marker="o", ls=ls, color=YEARCOL[year], lw=1.9, ms=4.5, label=f"{year}" + (f" · {tr('m_broad', lang)}" if ls == "--" else f" · {tr('m_strict', lang)}"))
            for r in s.itertuples():
                rows.append(dict(series=key, code=CFG.A05_BROAD_PRE2021["entry"] if ls == "--" else CFG.STRICT["a05_entry"], year=int(r.year), month=int(r.month), total=r.total, n_establishments=r.n_est, n_establishments_year=r.n_year, index=np.nan,
                                 era="2019–2020" if ls == "--" else "2021–2025"))
    f.set_xticks(range(1, 13)); f.set_xticklabels(months, fontsize=8); f.set_xlabel(tr("month", lang)); f.set_ylabel(tr("estab_month_axis", lang))
    f.set_ylim(0, max(gstrict.n_est.max(), gbroad.n_est.max()) * 1.35)
    plate_legend(f, loc="upper left", ncol=2, columnspacing=0.8, handlelength=1.4); panel_head(f, "f", tr("s13_f", lang))

    path = save_plate(fig, fdir / "figS13_rem_seasonality.png")
    plt.close(fig)
    fw = tr("figure", lang); vl = vlab(variant, lang)
    fam = D.family_code(variant, "a05_entry").replace("+", ", ")
    cap = {"title": {"es": f"{fw} S13. Estacionalidad mensual del reporte REM: ingresos A05 y tamizaje A03 por año, índice respecto de la media mensual de cada año — variante {vl}",
                     "en": f"{fw} S13. Monthly seasonality of REM reporting: A05 entries and A03 screening by year, index relative to each year's monthly mean — {vl} variant"}[lang],
           "caption": {"es": ("Cada línea es un año: total mensual nacional (suma de las filas establecimiento × mes presentes) dividido por la media de los 12 meses de ese año × 100; meses sin fila serían vacíos, no cero. "
                              "n = establecimientos con al menos una fila del código en el año. Las eras de definición se dibujan como líneas separadas por año y nunca se unen. "
                              f"(a) A05 ingresos por autismo estricto (05990022), 2021–2025. (b) A05 ingresos de la familia TGD de la variante ({fam}), 2021–2025. (c) A05 ingresos por TGD amplio (06902600), 2019–2020: la caída de abril–agosto de 2020 refleja la disrupción del reporte durante la pandemia. "
                              "(d) A03 M-CHAT realizado en niños/as con alteración de lenguaje/área social (03500406), 2019–2022: febrero de 2019 registra 1.051 registros en el archivo (valor atípico, mostrado sin corrección) y 2020 muestra la caída de abril–septiembre. "
                              "(e) A03 resultados de la primera parte del M-CHAT-R/F: 2023–2024 suma de riesgo bajo/medio/alto (09600213–09600215) y 2025 suma de las categorías de riesgo del rediseño (03710016–03710019, línea discontinua); familias de códigos distintas. "
                              "(f) Número de establecimientos con fila en cada mes para los ingresos A05: TGD amplio 2019–2020 (línea discontinua) y autismo estricto 2021–2025; la caída de 2020 es de establecimientos reportantes, no de personas. "
                              "Conteos administrativos, no prevalencia ni incidencia."),
                       "en": ("Each line is one year: national monthly total (sum of the establishment × month rows present) divided by that year's 12-month mean × 100; months without any row would be blank, not zero. "
                              "n = establishments with at least one row for the code in the year. Definition eras are drawn as separate lines per year and are never joined. "
                              f"(a) A05 strict-autism entries (05990022), 2021–2025. (b) A05 entries of the variant's PDD family ({fam}), 2021–2025. (c) A05 broad-PDD entries (06902600), 2019–2020: the April–August 2020 fall reflects the pandemic reporting disruption. "
                              "(d) A03 M-CHAT done among children with language/social alteration (03500406), 2019–2022: February 2019 holds 1,051 records in the file (outlying value, shown uncorrected) and 2020 shows the April–September fall. "
                              "(e) A03 M-CHAT-R/F part-1 results: 2023–2024 sum of low/medium/high risk (09600213–09600215) and 2025 sum of the redesign's risk categories (03710016–03710019, dashed); different code families. "
                              "(f) Number of establishments with a row in each month for A05 entries: broad PDD 2019–2020 (dashed) and strict autism 2021–2025; the 2020 fall is in reporting establishments, not in persons. "
                              "Administrative counts, not prevalence or incidence.")}[lang]}
    merge_json(fdir / "captions.json", {"figS13_rem_seasonality": cap})
    tab = pd.DataFrame(rows); tab["variant"] = variant
    fmt = pd.DataFrame({tr("t_series", lang): [LBL.get(f"ser_{s}", {}).get(lang, s) for s in tab.series], tr("t_code", lang): tab.code, tr("t_era", lang): tab.era, tr("year", lang): tab.year,
                        tr("t_month", lang): [months[m - 1] for m in tab.month], tr("t_total", lang): [_n(x, 0, lang) if pd.notna(x) else tr("absent", lang) for x in tab.total],
                        tr("t_n_est_month", lang): [_n(x, 0, lang) if pd.notna(x) else tr("absent", lang) for x in tab.n_establishments],
                        tr("t_n_est_year", lang): [_n(x, 0, lang) if pd.notna(x) else tr("na", lang) for x in tab.n_establishments_year],
                        tr("t_index", lang): [_n(x, 1, lang) if pd.notna(x) else tr("na", lang) for x in tab["index"]]})
    tw = tr("table", lang)
    paths = write_table(variant, lang, "S13_rem_seasonality", fmt, tab,
                        {"es": f"{tw} S13. Totales mensuales REM, establecimientos con fila en el mes e índice respecto de la media anual (A05 y A03) — variante {vl}",
                         "en": f"{tw} S13. REM monthly totals, establishments with a row in the month and index relative to the annual mean (A05 and A03) — {vl} variant"}[lang],
                        {"es": "Índice = total del mes / media de los 12 meses del año × 100; cada familia de códigos se indexa por separado y las eras no son comparables. Dos marcadores, dos estados distintos: «no reportado» = el mes no tiene ninguna fila en el archivo (no es un cero); «n/e» = el valor no se puede calcular con lo que hay (el índice y el n anual necesitan las filas del año, que ese mes no aporta). Conteos administrativos, no prevalencia.",
                         "en": "Index = month total / mean of the year's 12 months × 100; each code family is indexed separately and eras are not comparable. Two markers, two distinct states: 'not reported' = the month has no row at all in the file (it is not a zero); 'n/e' = the value cannot be computed from what is there (the index and the annual n need the year's rows, which that month does not contribute). Administrative counts, not prevalence."}[lang])
    return str(path), paths


# ===========================================================================
# Controles de reproducción y ejecución
# ===========================================================================
def controls(D: Data, rates_by_variant: dict[str, pd.DataFrame]) -> pd.DataFrame:
    out = []

    def add(family, key, expected, observed, note=""):
        ok = pd.notna(observed) and (abs(float(observed) - float(expected)) <= 1e-9 or (float(expected) != 0 and abs(float(observed) / float(expected) - 1) <= 0.005))
        out.append(dict(control=family, key=key, expected=expected, observed=observed, status="ok" if ok else "differs", note=note, module=MODULE))

    checks = [("a05_autism_entries", CFG.STRICT["a05_entry"], "strict_autism", "annual_sum"), ("a05_autism_exits", CFG.STRICT["a05_exit"], "strict_autism", "annual_sum"),
              ("a27_counselling", CFG.A27["counselling"], "single_code", "annual_sum"), ("a27_assisted_referral", CFG.A27["assisted_referral"], "single_code", "annual_sum"),
              ("a28_primary", CFG.A28["primary"], "single_code", "annual_sum"), ("a28_hospital", CFG.A28["hospital"], "single_code", "annual_sum"),
              ("p2_tea_december", CFG.P2_TEA, "single_code", "december_stock"), ("p2_naneas_total_december", CFG.P2_NANEAS_TOTAL, "single_code", "december_stock"),
              ("a03_legacy_mchat_done", CFG.A03_LEGACY["mchat_done"], "single_code", "annual_sum"), ("a03_legacy_mchat_altered", CFG.A03_LEGACY["mchat_altered"], "single_code", "annual_sum")]
    for fam, code, var, meas in checks:
        r = D.row(code, var, meas).set_index("year")
        for year, exp in CFG.CONTROLS[fam].items():
            add(fam, f"{code}|{meas}|{year}", exp, r.total.get(year, np.nan), "plotted value equals config.CONTROLS")
    r = D.row(CFG.P2_TEA, measure="december_stock").set_index("year")
    for year, exp in CFG.CONTROLS["p2_establishments_december"].items():
        add("p2_establishments_december", f"{CFG.P2_TEA}|december_stock|{year}", exp, r.n_reporting_establishments.get(year, np.nan), "reporting establishments shown in F3-D")
    for fam, codes in [("p6_primary_december", (CFG.P6_BROAD_PRE2021["primary"], CFG.STRICT["p6_primary"])), ("p6_specialty_december", (CFG.P6_BROAD_PRE2021["specialty"], CFG.STRICT["p6_specialty"]))]:
        for year, exp in CFG.CONTROLS[fam].items():
            code, var = (codes[0], "broad_pre2021") if year <= 2020 else (codes[1], "strict_autism")
            add(fam, f"{code}|december_stock|{year}", exp, D.row(code, var, "december_stock").set_index("year").total.get(year, np.nan), "broad PDD 2019–2020 and strict autism 2021+ are separate facets")
    for year, (lo_, me_, hi_) in CFG.CONTROLS["a03_2023_low_medium_high"].items():
        for code, exp in zip([CFG.A03_2023_2024["low"], CFG.A03_2023_2024["medium"], CFG.A03_2023_2024["high"]], (lo_, me_, hi_)):
            add("a03_2023_low_medium_high", f"{code}|annual_sum|{year}", exp, D.row(code).set_index("year").total.get(year, np.nan), "stacked bar in F3-A2")
    # junio 2020 P2 (disrupción) y ausencia de junio 2023 para P2501878
    j = D.row(CFG.P2_TEA, measure="june_stock").set_index("year")
    add("p2_tea_june_2020", f"{CFG.P2_TEA}|june_stock|2020", 172, j.total.get(2020, np.nan), "June 2020 collapse shown in S5")
    add("p2_establishments_june_2020", f"{CFG.P2_TEA}|june_stock|2020", 28, j.n_reporting_establishments.get(2020, np.nan), "June 2020 collapse shown in S5")
    nj = D.row(CFG.P2_NANEAS_TOTAL, measure="june_stock").set_index("year")
    add("p2_naneas_june_2023_not_reported", f"{CFG.P2_NANEAS_TOTAL}|june_stock|2023", 0, nj.n_reporting_establishments.get(2023, np.nan), "no June 2023 row: not reported, never plotted as zero")
    # S7: concordancia con las tasas estandarizadas del módulo 06 (misma estandarización OMS / Fay–Feuer)
    if D.models_asr is not None:
        for variant, rates in rates_by_variant.items():
            for key, mv in [("strict", "strict_autism"), ("family", variant)]:
                a = rates[rates.series == key][["year", "sex", "asr"]]
                b = D.models_asr[D.models_asr.variant == mv][["year", "sex", "asr"]]
                m = a.merge(b, on=["year", "sex"], suffixes=("_08b", "_06"))
                diff = float((m.asr_08b - m.asr_06).abs().max()) if len(m) else np.nan
                out.append(dict(control="s7_asr_vs_06_models", key=f"{variant}|{key}", expected=0.0, observed=diff, status="ok" if (pd.notna(diff) and diff < 1e-6) else "differs",
                                note=f"max |ASR_08b - ASR_06| over {len(m)} year×sex cells (same WHO standard and INE base 2017)", module=MODULE))
    return pd.DataFrame(out)


def main() -> int:
    D = Data()
    run = {"module": MODULE, "script": SCRIPT, "run_utc": datetime.now(timezone.utc).isoformat(), "figures": [], "tables": [], "timings_s": {}}
    rates_by_variant = {}
    for variant in VARIANTS:
        rates_by_variant[variant] = a05_rates(D, variant)
        for lang in LANGS:
            for name, fn in [("F3", figure_f3), ("S5", figure_s5), ("S6", figure_s6), ("S7", figure_s7), ("S8", figure_s8), ("S13", figure_s13)]:
                t = time.time()
                if name == "S7":
                    fig_path, tabs = fn(D, variant, lang, rates_by_variant[variant])
                else:
                    fig_path, tabs = fn(D, variant, lang)
                dt = round(time.time() - t, 1)
                run["figures"].append(fig_path); run["tables"].extend(tabs); run["timings_s"][f"{variant}/{lang}/{name}"] = dt
                log(f"{variant}/{lang} {name}: {Path(fig_path).name} en {dt} s")
    ctrl = controls(D, rates_by_variant)
    C.atomic_write_csv(ctrl, CONTROLS_DIR / f"{MODULE}_controls.csv")
    n_ok, n_diff = int((ctrl.status == "ok").sum()), int((ctrl.status == "differs").sum())
    run["controls"] = {"n_ok": n_ok, "n_differs": n_diff, "path": str(CONTROLS_DIR / f"{MODULE}_controls.csv")}
    run["total_seconds"] = round(time.time() - T0, 1)
    C.atomic_write_json(run, CONTROLS_DIR / f"{MODULE}_run_log.json")
    log(f"controles: {n_ok} ok, {n_diff} difieren; {len(run['figures'])} láminas y {len(run['tables'])} tablas; total {run['total_seconds']} s")
    return 0 if n_diff == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
