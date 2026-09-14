# -*- coding: utf-8 -*-
"""07_controls.py — consolidación de los controles de reproducción (esperado frente a observado) del pipeline Lancet.

Entradas
  outputs/controls/<módulo>_controls.csv   controles escritos por TODOS los módulos del pipeline, del 00 al 17 (columnas name,
                                           key, expected, observed, abs_diff, rel_diff, status, note). Se consolidan todos los
                                           que existan en el directorio, no solo los de la fase 1.
  outputs/tidy/rem_pathway_annual.csv      (opcional) establecimientos reportantes por código-año, para las filas REM de la T8.
  config.CONTROLS                          valores esperados preespecificados (brief del protocolo / DATA_REVIEW.md).

Salidas
  outputs/controls/controls_summary.csv    consolidado con ÁMBITO explícito: scope, module, name, key, expected, observed,
                                           abs_diff, rel_diff, status, note. `scope = "pipeline"` es una fila por control de
                                           cada <módulo>_controls.csv (módulos 00 a 17); `scope = "analysis_plan"` es una fila
                                           por control indicador-año de la tabla preespecificada del plan de análisis. Los dos
                                           ámbitos cuentan cosas distintas y NO se suman: `lancet_americas/controls_registry.py`
                                           expone `totals(scope)` y `phrase(scope, lang)`, y todo documento que imprima uno de
                                           estos totales debe imprimir además su ámbito en palabras (defecto 9 de la revisión).
  outputs/controls/controls_summary.md     mismo contenido en markdown, con totales por ámbito, por estado y por módulo y la
                                           explicación de cada control que difiere.
  outputs/<variante>/<idioma>/tables/T8_controls.csv           una fila por control preespecificado (config.CONTROLS) × año/clave,
                                                               texto final para Word: fuente, indicador, año/clave, esperado,
                                                               observado, diferencia, estado, explicación.
  outputs/<variante>/<idioma>/tables/T8_controls_numeric.csv   versión numérica de la misma tabla.
  outputs/<variante>/<idioma>/tables/T8_controls_compact.csv   versión breve: una fila por familia de control,
                                                               por fila de comprobación y por control del módulo.
  outputs/<variante>/<idioma>/tables/titles.json               entradas T8_controls y T8_controls_compact (fusionadas con las
                                                               entradas de otros módulos si el archivo ya existe).
  outputs/controls/07_controls_controls.csv, outputs/controls/07_controls_runlog.json

La T8 es idéntica en las variantes con y sin Rett: los controles del protocolo se definieron sobre la familia F84 completa
(variante con Rett) y las series de autismo estricto, denominadores, encuestas y educación no dependen de la variante.

El consolidado es una FOTOGRAFÍA de los archivos de control que había en el directorio cuando se ejecutó este
módulo: cualquier módulo que se vuelva a ejecutar deja el resumen atrasado hasta que se vuelve a ejecutar éste.
(Pasó en la fase 4e: `controls_summary.csv` seguía trayendo el recuento de palabras del artículo y el de ítems
suplementarios citados de una corrida anterior del módulo 17.) La comprobación es barata: comparar fila a fila
cada `<módulo>_controls.csv` con su bloque `scope = "pipeline"` del resumen.

Uso (desde la raíz del repositorio):  python3 lancet_americas/pipeline/07_controls.py
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common as C  # noqa: E402
import config as CFG  # noqa: E402
import controls_registry as CR  # noqa: E402  (ámbitos de control: fuente única de los totales publicados)

MODULE = "07_controls"
CONTROLS_DIR = CFG.OUT / "controls"  # config.CONTROLS es el diccionario de valores esperados (sombra del Path homónimo)
# La primera columna es el ÁMBITO: `pipeline` (una fila por control de cada <módulo>_controls.csv, módulos 00 a 17)
# y `analysis_plan` (una fila por control indicador-año de la tabla preespecificada). Sin esa columna el archivo
# admitía dos lecturas distintas del mismo total y los documentos las mezclaban (defecto 9).
SUMMARY_COLS = ["scope", "module", "name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"]
# Módulos que DEBEN haber escrito su archivo de controles antes de consolidar (fase 1 del pipeline).
EXPECTED_MODULES = ["00_provenance", "01_grd_core", "01b_deis_egresos", "02_rem_pathway", "03_denominators", "04_surveys", "05_education"]
# Módulos cuyas filas pueden entrar en la tabla del plan de análisis (ámbito `analysis_plan`). Declararlos aquí
# hace que esa tabla no dependa del orden de ejecución: los módulos de material extendido (11 a 17) se consolidan
# en el ámbito `pipeline` y no añaden filas al plan.
PLAN_MODULES = CR.PLAN_MODULES

# ---------------------------------------------------------------------------
# Rótulos bilingües (ningún literal suelto en el cuerpo del script)
# ---------------------------------------------------------------------------
TXT = {
    "col_source": {"es": "Fuente", "en": "Source"},
    "col_indicator": {"es": "Indicador", "en": "Indicator"},
    "col_key": {"es": "Año / clave", "en": "Year / key"},
    "col_expected": {"es": "Esperado (protocolo)", "en": "Expected (protocol)"},
    "col_observed": {"es": "Observado (pipeline)", "en": "Observed (pipeline)"},
    "col_diff": {"es": "Diferencia", "en": "Difference"},
    "col_status": {"es": "Estado", "en": "Status"},
    "col_explanation": {"es": "Explicación", "en": "Explanation"},
    "status_ok": {"es": "coincide", "en": "matches"},
    "status_differs": {"es": "difiere", "en": "differs"},
    "status_info": {"es": "informativo", "en": "informative"},
    "status_missing": {"es": "pendiente (sin fila del módulo)", "en": "pending (no module row)"},
    "match_summary": {"es": "{ok}/{n} coinciden", "en": "{ok}/{n} match"},
    "differ_keys": {"es": "difieren: {keys}", "en": "differ: {keys}"},
    "missing_keys": {"es": "sin fila del módulo: {keys}", "en": "no module row: {keys}"},
    "reporting_n": {"es": "Establecimientos reportantes: {n}.", "en": "Reporting establishments: {n}."},
    "module_note": {"es": "Nota del módulo: {note}", "en": "Module note: {note}"},
    "no_row": {"es": "El módulo no escribió una fila para este control; no se completa por plausibilidad.",
               "en": "The module wrote no row for this control; it is not filled in by plausibility."},
    "check_row": {"es": "(fila de comprobación)", "en": "(check row)"},
    # Las filas cuyo valor esperado NO viene del protocolo (config.CONTROLS) se rotulan en la propia tabla:
    # el título decía «205 filas, de las cuales 185 con valor esperado preespecificado» y las 20 restantes
    # eran indistinguibles al leerlas, porque todas llevan un número en la columna «Esperado».
    "module_row": {"es": "(control del módulo; el esperado no está en el protocolo)",
                   "en": "(module control; the expected value is not in the protocol)"},
    "group": {
        "grd": {"es": "GRD público 2019–2024 (módulo 01)", "en": "Public GRD 2019–2024 (module 01)"},
        "deis": {"es": "Egresos DEIS 2019–2024, control cruzado (módulo 01b)", "en": "DEIS discharges 2019–2024, cross-check (module 01b)"},
        "rem": {"es": "REM Serie A / Serie P 2019–2025 (módulo 02)", "en": "REM Series A / Series P 2019–2025 (module 02)"},
        "denominators": {"es": "Denominadores y cobertura (módulo 03)", "en": "Denominators and coverage (module 03)"},
        "surveys": {"es": "Encuestas ENDIDE 2022 / ENCAVI 2023–2024 (módulo 04)", "en": "ENDIDE 2022 / ENCAVI 2023–2024 surveys (module 04)"},
        "education": {"es": "Educación PIE / SINACES / JUNAEB (módulo 05)", "en": "Education PIE / SINACES / JUNAEB (module 05)"},
        "module_check": {"es": "Comprobación interna de módulo", "en": "Module internal check"},
    },
    "measure": {
        "annual_sum": {"es": "suma anual", "en": "annual sum"},
        "december_stock": {"es": "stock de diciembre", "en": "December stock"},
        "june_stock": {"es": "stock de junio", "en": "June stock"},
    },
    "junaeb_level": {
        "parvularia": {"es": "Educación parvularia (prekínder/kínder)", "en": "Pre-school (parvularia)"},
        "basico1": {"es": "1.º básico", "en": "1st grade (1.º básico)"},
        "basico5": {"es": "5.º básico", "en": "5th grade (5.º básico)"},
        "medio1": {"es": "1.º medio", "en": "9th grade (1.º medio)"},
    },
    "endide_key": {
        "adults": {"es": "Adultos de 18 años o más (autismo reportado)", "en": "Adults aged 18+ (reported autism)"},
        "children": {"es": "NNA de 2–17 años (autismo reportado)", "en": "Children and adolescents aged 2–17 (reported autism)"},
        "children_confirmed": {"es": "NNA de 2–17 años con confirmación profesional", "en": "Children and adolescents aged 2–17 with professional confirmation"},
    },
    "encavi_key": {
        "positive": {"es": "Respuestas positivas (diagnóstico de autismo, 15+)", "en": "Positive responses (autism diagnosis, 15+)"},
        "n": {"es": "Personas de 15 años o más en la base", "en": "Persons aged 15+ in the file"},
    },
    "md_title": {"es": "# Resumen de controles de reproducción (módulo 07_controls)"},
    "md_generated": {"es": "Generado el {ts} a partir de {n} archivos `<módulo>_controls.csv`. Estado: `ok` = igualdad exacta (conteos) o diferencia relativa ≤ 0,5 % (medias y proporciones); `differs` = en otro caso (explicado abajo); `info` = valor reportado sin referencia esperada."},
    "md_scopes": {"es": "## Totales por ámbito (columna `scope` del CSV)"},
    "md_scopes_note": {"es": "Los dos ámbitos cuentan cosas distintas y NO se suman: `pipeline` es una fila por control escrito por cada módulo; "
                             "`analysis_plan` reexpresa los controles preespecificados del plan de análisis con una fila por indicador y año, más las "
                             "filas de comprobación y las diferencias internas de los módulos 00 a 09b. Todo documento que imprima uno de estos totales "
                             "debe nombrar su ámbito en palabras (`lancet_americas/controls_registry.py`)."},
    "md_totals_status": {"es": "## Totales por estado (ámbito `pipeline`)"},
    "md_totals_module": {"es": "## Totales por módulo y estado (ámbito `pipeline`)"},
    "md_differs": {"es": "## Controles que difieren y su explicación"},
    "md_full": {"es": "## Tabla completa (todos los ámbitos y módulos)"},
    "md_none_differ": {"es": "Ningún control difiere."},
}

# ---------------------------------------------------------------------------
# Especificación de la T8: un bloque por control preespecificado de config.CONTROLS
# ---------------------------------------------------------------------------
# cfg: clave de config.CONTROLS; module: módulo que lo reproduce; names: nombre(s) de control en el CSV del módulo
# (varios nombres cuando config guarda una tupla por año); group: fuente; dec: decimales del valor esperado;
# ind: rótulo del indicador; ok: explicación breve para filas que coinciden; companions: filas de comprobación asociadas.
SPEC = [
    dict(cfg="grd_records_total", module="01_grd_core", names=["grd_records_total"], group="grd", dec=0,
         ind={"es": "Episodios GRD totales (filas del archivo anual)", "en": "Total GRD episodes (rows of the annual file)"},
         ok={"es": "Filas de datos leídas del GRD público (una fila = un episodio), sin eliminar duplicados; denominador de las tasas por 100.000 episodios.",
             "en": "Data rows read from the public GRD file (one row = one episode), no duplicates removed; denominator of the rates per 100,000 episodes."}),
    dict(cfg="grd_hospitals_observed", module="01_grd_core", names=["grd_hospitals_observed"], group="grd", dec=0,
         ind={"es": "Hospitales observados (panel anual)", "en": "Hospitals observed (annual panel)"},
         ok={"es": f"Hospitales (COD_HOSPITAL) distintos con al menos un episodio en el año; el panel fijo son los 65 {C.fixed_panel_gloss('es', 'clause')}, nunca los 72 de 2024.",
             "en": f"Distinct hospitals (COD_HOSPITAL) with at least one episode in the year; the fixed panel is the 65 {C.fixed_panel_gloss('en', 'clause')}, never the 72 of 2024."}),
    dict(cfg="grd_f84_any", module="01_grd_core", names=["grd_f84_any"], group="grd", dec=0,
         ind={"es": "Episodios con F84 documentado (cualquier posición), panel observado", "en": "Episodes with documented F84 (any position), observed panel"},
         ok={"es": "Algún código F84.x en DIAGNOSTICO1–35 (familia completa, variante con Rett), toda actividad, panel observado, sin eliminar duplicados. Reconocimiento administrativo, no prevalencia.",
             "en": "Any F84.x code in DIAGNOSTICO1–35 (full family, with-Rett variant), all activity, observed panel, no duplicates removed. Administrative recognition, not prevalence."}),
    dict(cfg="grd_f84_any_panel65", module="01_grd_core", names=["grd_f84_any_panel65"], group="grd", dec=0,
         ind={"es": "Episodios con F84 documentado, panel fijo de 65 hospitales", "en": "Episodes with documented F84, fixed panel of 65 hospitals"},
         ok={"es": f"Mismo conteo restringido a los 65 {C.fixed_panel_gloss('es', 'membership')} (subconjunto verificado de los 68 de 2023 y los 72 de 2024).",
             "en": f"Same count restricted to the 65 {C.fixed_panel_gloss('en', 'membership')} (verified subset of the 68 of 2023 and 72 of 2024)."}),
    dict(cfg="grd_f84_any_strict_hospitalisation", module="01_grd_core", names=["grd_f84_any_strict_hospitalisation"], group="grd", dec=0,
         ind={"es": "Episodios F84 en hospitalización estricta, panel observado", "en": "F84 episodes in strict hospitalisation, observed panel"},
         ok={"es": "TIPO_ACTIVIDAD = hospitalización, panel observado; desde 2020 solo existen dos categorías (hospitalización y CMA), por lo que hospitalización = cualquier F84 − CMA.",
             "en": "TIPO_ACTIVIDAD = hospitalisation, observed panel; from 2020 only two categories exist (hospitalisation and CMA), so hospitalisation = any F84 − CMA."},
         companions=[dict(name="grd_f84_any_strict_hospitalisation_fixed65",
                          ind={"es": "Episodios F84 en hospitalización estricta, panel fijo de 65", "en": "F84 episodes in strict hospitalisation, fixed panel of 65"},
                          ok={"es": "Fila de comprobación: el mismo indicador en el panel fijo de 65 hospitales reproduce el valor del protocolo en todos los años.",
                              "en": "Check row: the same indicator on the fixed panel of 65 hospitals reproduces the protocol value in every year."})]),
    dict(cfg="grd_cma", module="01_grd_core", names=["grd_cma"], group="grd", dec=0,
         ind={"es": "Episodios F84 en cirugía mayor ambulatoria (CMA), panel observado", "en": "F84 episodes in major ambulatory surgery (CMA), observed panel"},
         ok={"es": "TIPO_ACTIVIDAD = cirugía mayor ambulatoria, panel observado; se presenta separada de la hospitalización, nunca sumada como 'hospitalizaciones por autismo'.",
             "en": "TIPO_ACTIVIDAD = major ambulatory surgery, observed panel; presented separately from hospitalisation, never pooled as 'hospitalisations for autism'."}),
    dict(cfg="grd_f84_principal", module="01_grd_core", names=["grd_f84_principal"], group="grd", dec=0,
         ind={"es": "Episodios con F84 como diagnóstico principal", "en": "Episodes with F84 as principal diagnosis"},
         ok={"es": "F84.x en DIAGNOSTICO1 (con o sin F84 secundario adicional), panel observado; serie de sensibilidad separada de 'F84 documentado'.",
             "en": "F84.x in DIAGNOSTICO1 (with or without an additional secondary F84), observed panel; sensitivity series kept separate from 'documented F84'."}),
    dict(cfg="grd_f84_secondary_only_share_2024", module="01_grd_core", names=["grd_f84_secondary_only_share_2024"], group="grd", dec=3,
         ind={"es": "Proporción de episodios F84 con F84 solo como diagnóstico secundario, 2024", "en": "Share of F84 episodes with F84 only as a secondary diagnosis, 2024"},
         ok={"es": "Episodios con F84 únicamente en posición secundaria / episodios con F84 en cualquier posición ({frac}); el protocolo lo redondea a tres decimales.",
             "en": "Episodes with F84 only in a secondary position / episodes with F84 in any position ({frac}); the protocol rounds it to three decimals."}),
    dict(cfg="grd_coding_depth_all_mean", module="01_grd_core", names=["grd_coding_depth_all_mean"], group="grd", dec=2,
         ind={"es": "Profundidad diagnóstica media, todos los episodios", "en": "Mean coding depth, all episodes"},
         ok={"es": "Media de diagnósticos codificados no vacíos por episodio (DIAGNOSTICO1–35), todos los episodios del panel observado; el protocolo redondea a dos decimales (tolerancia 0,5 %).",
             "en": "Mean number of non-empty coded diagnoses per episode (DIAGNOSTICO1–35), all episodes of the observed panel; the protocol rounds to two decimals (0.5% tolerance)."}),
    dict(cfg="grd_coding_depth_f84_mean", module="01_grd_core", names=["grd_coding_depth_f84_mean"], group="grd", dec=2,
         ind={"es": "Profundidad diagnóstica media, episodios F84", "en": "Mean coding depth, F84 episodes"},
         ok={"es": "Media de diagnósticos codificados entre los episodios con F84 documentado (variante con Rett); el protocolo redondea a dos decimales (tolerancia 0,5 %).",
             "en": "Mean number of coded diagnoses among episodes with documented F84 (with-Rett variant); the protocol rounds to two decimals (0.5% tolerance)."}),
    dict(cfg="grd_persons_within_year_f84_any", module="01_grd_core", names=["grd_persons_within_year_f84_any"], group="grd", dec=0,
         ind={"es": "Personas únicas con F84 dentro del año", "en": "Unique persons with F84 within the year"},
         ok={"es": "Identificadores válidos distintos entre los episodios F84 del año; nunca se deduplica entre años (el identificador cambia de formato entre 2020 y 2021 y no hay solapamiento).",
             "en": "Distinct valid identifiers among the year's F84 episodes; never deduplicated across years (the identifier changes format between 2020 and 2021 with no overlap)."},
         companions=[dict(name="grd_persons_within_year_f84_any_placeholder_as_one_id",
                          ind={"es": "Personas únicas con F84 dentro del año, contando el marcador inválido como una persona", "en": "Unique persons with F84 within the year, counting the invalid placeholder as one person"},
                          ok={"es": "Fila de comprobación: al contar el marcador de identificador inválido como una persona adicional se reproduce el valor del protocolo; esta definición no se usa en las salidas.",
                              "en": "Check row: counting the invalid-identifier placeholder as one extra person reproduces the protocol value; this definition is not used in the outputs."})]),
    dict(cfg="a05_autism_entries", module="02_rem_pathway", names=["a05_autism_entries"], group="rem", dec=0,
         ind={"es": "A05: ingresos a salud mental por autismo (05990022)", "en": "A05: mental-health programme entries for autism (05990022)"},
         ok={"es": "Suma anual de COL01 (ambos sexos) sobre las filas presentes del código 05990022, sin eliminar duplicados; serie de autismo estricto idéntica en ambas variantes.",
             "en": "Annual sum of COL01 (both sexes) over the rows present for code 05990022, no deduplication; strict-autism series identical in both variants."}),
    dict(cfg="a05_autism_exits", module="02_rem_pathway", names=["a05_autism_exits"], group="rem", dec=0,
         ind={"es": "A05: egresos (altas) de salud mental por autismo (05990027)", "en": "A05: mental-health programme discharges for autism (05990027)"},
         ok={"es": "Suma anual de COL01 sobre las filas presentes del código 05990027, sin eliminar duplicados; flujo, no stock.",
             "en": "Annual sum of COL01 over the rows present for code 05990027, no deduplication; a flow, not a stock."}),
    dict(cfg="a27_counselling", module="02_rem_pathway", names=["a27_counselling"], group="rem", dec=0,
         ind={"es": "A27: consejerías M-CHAT-R/F (29101566), intervenciones", "en": "A27: M-CHAT-R/F counselling (29101566), interventions"},
         ok={"es": "Suma anual de COL01 (número de intervenciones, no de personas) del código 29101566, existente desde 2023.",
             "en": "Annual sum of COL01 (number of interventions, not persons) for code 29101566, which exists from 2023."}),
    dict(cfg="a27_assisted_referral", module="02_rem_pathway", names=["a27_assisted_referral"], group="rem", dec=0,
         ind={"es": "A27: referencias asistidas M-CHAT-R/F (29101574), intervenciones", "en": "A27: assisted M-CHAT-R/F referrals (29101574), interventions"},
         ok={"es": "Suma anual de COL01 (intervenciones) del código 29101574, existente desde 2023; no es un cociente entre etapas.",
             "en": "Annual sum of COL01 (interventions) for code 29101574, which exists from 2023; not a between-stage ratio."}),
    dict(cfg="a28_primary", module="02_rem_pathway", names=["a28_primary"], group="rem", dec=0,
         ind={"es": "A28: ingresos por TEA a rehabilitación en APS (29101629)", "en": "A28: TEA entries to primary-care rehabilitation (29101629)"},
         ok={"es": "Suma anual de COL01 del código 29101629, existente desde 2023.", "en": "Annual sum of COL01 for code 29101629, which exists from 2023."}),
    dict(cfg="a28_hospital", module="02_rem_pathway", names=["a28_hospital"], group="rem", dec=0,
         ind={"es": "A28: ingresos por TEA a rehabilitación hospitalaria (29101651)", "en": "A28: TEA entries to hospital rehabilitation (29101651)"},
         ok={"es": "Suma anual de COL01 del código 29101651, existente desde 2023.", "en": "Annual sum of COL01 for code 29101651, which exists from 2023."}),
    dict(cfg="p2_tea_december", module="02_rem_pathway", names=["p2_tea_december"], group="rem", dec=0,
         ind={"es": "P2: NANEAS con TEA bajo control, diciembre (P2500500)", "en": "P2: NANEAS with TEA under control, December (P2500500)"},
         ok={"es": "Stock de diciembre (COL01) del código P2500500; junio solo como sensibilidad y nunca sumado con diciembre.",
             "en": "December stock (COL01) for code P2500500; June only as a sensitivity and never summed with December."}),
    dict(cfg="p2_establishments_december", module="02_rem_pathway", names=["p2_establishments_december"], group="rem", dec=0,
         ind={"es": "P2: establecimientos que reportan TEA en diciembre", "en": "P2: establishments reporting TEA in December"},
         ok={"es": "IdEstablecimiento distintos con una fila de diciembre del código P2500500; parte del crecimiento del stock refleja expansión del reporte.",
             "en": "Distinct IdEstablecimiento with a December row for code P2500500; part of the stock growth reflects reporting expansion."}),
    dict(cfg="p2_naneas_total_december", module="02_rem_pathway", names=["p2_naneas_total_december"], group="rem", dec=0,
         ind={"es": "P2: NANEAS total bajo control, diciembre (P2501878)", "en": "P2: total NANEAS under control, December (P2501878)"},
         ok={"es": "Stock de diciembre (COL01) del código P2501878, que existe desde diciembre de 2023 (sin fila de junio de 2023: no reportado, no cero); denominador interno de P2 solo desde 2023.",
             "en": "December stock (COL01) for code P2501878, which exists from December 2023 (no June 2023 row: not reported, not zero); internal P2 denominator from 2023 only."}),
    dict(cfg="p6_primary_december", module="02_rem_pathway", names=["p6_primary_december"], group="rem", dec=0,
         ind={"es": "P6: población bajo control en APS, diciembre (TGD amplio P6223000 en 2019–2020; autismo P6241010 desde 2021)", "en": "P6: population under control in primary care, December (broad PDD P6223000 in 2019–2020; autism P6241010 from 2021)"},
         ok={"es": "Stock de diciembre (COL01); quiebre de definición entre 2020 (TGD amplio, incluye Rett de forma inseparable) y 2021 (autismo estricto): no es una serie continua.",
             "en": "December stock (COL01); definition break between 2020 (broad PDD, Rett inseparable) and 2021 (strict autism): not a continuous series."}),
    dict(cfg="p6_specialty_december", module="02_rem_pathway", names=["p6_specialty_december"], group="rem", dec=0,
         ind={"es": "P6: población bajo control en especialidad, diciembre (TGD amplio P6223380 en 2019–2020; autismo P6241060 desde 2021)", "en": "P6: population under control in specialty care, December (broad PDD P6223380 in 2019–2020; autism P6241060 from 2021)"},
         ok={"es": "Stock de diciembre (COL01); quiebre de definición entre 2020 (TGD amplio) y 2021 (autismo estricto): no es una serie continua.",
             "en": "December stock (COL01); definition break between 2020 (broad PDD) and 2021 (strict autism): not a continuous series."}),
    dict(cfg="a03_legacy_mchat_done", module="02_rem_pathway", names=["a03_legacy_mchat_done"], group="rem", dec=0,
         ind={"es": "A03 2019–2022: M-CHAT aplicado (03500406)", "en": "A03 2019–2022: M-CHAT administered (03500406)"},
         ok={"es": "Suma anual de COL01 + COL02 (hombres + mujeres) sobre las celdas presentes; el código se restringe a niños con alteración del lenguaje o del área social y no estima cobertura poblacional.",
             "en": "Annual sum of COL01 + COL02 (males + females) over the cells present; the code is restricted to children with language or social alterations and does not estimate population coverage."}),
    dict(cfg="a03_legacy_mchat_altered", module="02_rem_pathway", names=["a03_legacy_mchat_altered"], group="rem", dec=0,
         ind={"es": "A03 2019–2022: M-CHAT alterado (03500407)", "en": "A03 2019–2022: altered M-CHAT (03500407)"},
         ok={"es": "Suma anual de COL01 + COL02 sobre las celdas presentes (31 % de las filas A03 tienen una celda de sexo vacía); no es positividad poblacional.",
             "en": "Annual sum of COL01 + COL02 over the cells present (31% of A03 rows have one empty sex cell); not population positivity."}),
    dict(cfg="a03_2023_low_medium_high", module="02_rem_pathway", names=["a03_2023_2024_low", "a03_2023_2024_medium", "a03_2023_2024_high"], group="rem", dec=0,
         ind={"es": "A03 2023–2024: riesgo bajo / medio / alto (09600213 / 09600214 / 09600215)", "en": "A03 2023–2024: low / medium / high risk (09600213 / 09600214 / 09600215)"},
         ind_by_name={"a03_2023_2024_low": {"es": "A03 2023–2024: riesgo bajo (09600213)", "en": "A03 2023–2024: low risk (09600213)"},
                      "a03_2023_2024_medium": {"es": "A03 2023–2024: riesgo medio (09600214)", "en": "A03 2023–2024: medium risk (09600214)"},
                      "a03_2023_2024_high": {"es": "A03 2023–2024: riesgo alto (09600215)", "en": "A03 2023–2024: high risk (09600215)"}},
         ok={"es": "Suma anual de COL01 + COL02 sobre las celdas presentes; nueva familia de códigos 2023–2024, no comparable con el M-CHAT 2019–2022 ni con el rediseño de 2025.",
             "en": "Annual sum of COL01 + COL02 over the cells present; new 2023–2024 code family, not comparable with the 2019–2022 M-CHAT nor with the 2025 redesign."}),
    dict(cfg="fonasa_beneficiaries_december", module="03_denominators", names=["fonasa_beneficiaries_december"], group="denominators", dec=0,
         ind={"es": "FONASA: beneficiarios en diciembre", "en": "FONASA: beneficiaries in December"},
         ok={"es": "Suma de beneficiarios del archivo agregado de diciembre; las filas repetidas se conservan porque son aditivas ({dups}). Capa de aseguramiento (mezcla inscripción APS y domicilio).",
             "en": "Sum of beneficiaries in the aggregated December file; repeated rows are kept because they are additive ({dups}). Insurance layer (mixes primary-care enrolment and residence)."}),
    dict(cfg="aps_enrolled_december", module="03_denominators", names=["aps_enrolled_december"], group="denominators", dec=0,
         ind={"es": "Inscritos en APS, diciembre", "en": "Primary-care (APS) enrolled persons, December"},
         ok={"es": "Suma de TOTAL_INSCRITOS del corte de diciembre (Inscritos_APS_AAAA12.csv); cobertura operativa por centro (lugar de atención, no residencia).",
             "en": "Sum of TOTAL_INSCRITOS in the December cut (Inscritos_APS_YYYY12.csv); operational coverage by centre (place of care, not residence)."}),
    dict(cfg="aps_centres", module="03_denominators", names=["aps_centres"], group="denominators", dec=0,
         ind={"es": "Centros APS con inscritos, diciembre", "en": "Primary-care centres with enrolled persons, December"},
         ok={"es": "Códigos de centro distintos en el corte de diciembre.", "en": "Distinct centre codes in the December cut."}),
    dict(cfg="isapre_beneficiaries_december", module="03_denominators", names=["isapre_beneficiaries_december"], group="denominators", dec=0,
         ind={"es": "ISAPRE: beneficiarios en diciembre", "en": "ISAPRE: beneficiaries in December"},
         ok={"es": "Total nacional de beneficiarios ISAPRE en diciembre (2019–2020 .xls: cotizantes + cargas + nonatos; desde 2021 .xlsx: total cotizantes + total cargas); geografía administrativa del beneficiario.",
             "en": "National total of ISAPRE beneficiaries in December (2019–2020 .xls: contributors + dependants + unborn; from 2021 .xlsx: total contributors + total dependants); administrative geography of the beneficiary."}),
    dict(cfg="ine_population_national", module="03_denominators", names=["ine_population_national"], group="denominators", dec=0,
         ind={"es": "INE: población nacional proyectada (base Censo 2017)", "en": "INE: projected national population (Census 2017 base)"},
         ok={"es": "Proyecciones INE base Censo 2017 al 30 de junio, suma de comuna × sexo × edad simple (346 comunas); capa territorial (residencia).",
             "en": "INE projections, Census 2017 base, at 30 June, sum over comuna × sex × single age (346 comunas); territorial layer (residence)."}),
    dict(cfg="rem20_panel_188_retention", module="03_denominators", names=["rem20_panel_188_retention"], group="denominators", dec=4,
         ind={"es": "REM-20: retención de egresos del panel de 188 establecimientos", "en": "REM-20: discharge retention of the 188-establishment panel"},
         ok={"es": "Egresos de los 188 establecimientos con 12 meses reportados en cada año 2019–2025 / egresos totales del año (proporción); capacidad y actividad, no población cubierta.",
             "en": "Discharges of the 188 establishments with 12 reported months in every year 2019–2025 / total discharges of the year (proportion); capacity and activity, not covered population."}),
    dict(cfg="aps_panel_1871_retention", module="03_denominators", names=["aps_panel_1871_retention"], group="denominators", dec=4,
         ind={"es": "APS: retención de inscritos del panel de 1.871 centros", "en": "APS: enrolment retention of the 1,871-centre panel"},
         ok={"es": "Inscritos de los 1.871 centros presentes en los siete cortes de diciembre / inscritos totales del año (proporción).",
             "en": "Enrolled persons of the 1,871 centres present in all seven December cuts / total enrolled persons of the year (proportion)."}),
    dict(cfg="endide_unweighted", module="04_surveys", names=["endide_unweighted"], group="surveys", dec=0,
         ind={"es": "ENDIDE 2022: casos no ponderados de autismo reportado", "en": "ENDIDE 2022: unweighted cases of reported autism"},
         ok={"es": "Conteo no ponderado en la base de personas seleccionadas (adultos: c26_33 = 1 entre 18+; NNA: n29_19 = 1 entre 2–17; confirmación: n29a_19 = 1); las estimaciones nacionales usan el diseño complejo, nunca este conteo.",
             "en": "Unweighted count in the selected-persons file (adults: c26_33 = 1 among 18+; children: n29_19 = 1 among 2–17; confirmation: n29a_19 = 1); national estimates use the complex design, never this count."}),
    dict(cfg="encavi_unweighted", module="04_surveys", names=["encavi_unweighted"], group="surveys", dec=0,
         ind={"es": "ENCAVI 2023–2024: respuestas positivas y tamaño de la base", "en": "ENCAVI 2023–2024: positive responses and file size"},
         ok={"es": "Conteo no ponderado (p4_6_1_h = 1) y filas de la base de 15+ (manual: 16.590 casos); la proporción publicada se recalcula con ponderador, estratos y conglomerados.",
             "en": "Unweighted count (p4_6_1_h = 1) and rows of the 15+ file (manual: 16,590 cases); the published proportion is recomputed with weight, strata and clusters."}),
    dict(cfg="pie_tea_strict", module="05_education", names=["pie_tea_strict"], group="education", dec=0,
         ind={"es": "PIE: estudiantes con TEA (definición estricta)", "en": "PIE: students with TEA (strict definition)"},
         ok={"es": "Apuntes 60 (MINEDUC), Tabla 6, p. 11, extraído del PDF con pdftotext; stock escolar anual, no prevalencia.",
             "en": "Apuntes 60 (MINEDUC), Table 6, p. 11, extracted from the PDF with pdftotext; annual school stock, not prevalence."}),
    dict(cfg="pie_tea_asperger", module="05_education", names=["pie_tea_asperger"], group="education", dec=0,
         ind={"es": "PIE: estudiantes con TEA-Asperger", "en": "PIE: students with TEA-Asperger"},
         ok={"es": "Apuntes 60 (MINEDUC), Tabla 6, p. 11; definición mantenida separada de TEA estricto.",
             "en": "Apuntes 60 (MINEDUC), Table 6, p. 11; definition kept separate from strict TEA."}),
    dict(cfg="pie_harmonised", module="05_education", names=["pie_harmonised"], group="education", dec=0,
         ind={"es": "PIE: serie armonizada TEA + TEA-Asperger (2019–2023) y SINACES (2024–2025)", "en": "PIE: harmonised TEA + TEA-Asperger series (2019–2023) and SINACES (2024–2025)"},
         ok={"es": "Suma TEA + TEA-Asperger de Apuntes 60 para 2019–2023 y PIE armonizado del informe SINACES para 2024–2025; 2022 = 42.940 (45.014 − 2.074 escuelas especiales), no los 42.945 impresos en SINACES.",
             "en": "TEA + TEA-Asperger sum from Apuntes 60 for 2019–2023 and harmonised PIE from the SINACES report for 2024–2025; 2022 = 42,940 (45,014 − 2,074 special schools), not the 42,945 printed in SINACES."}),
    dict(cfg="pie_special_schools", module="05_education", names=["pie_special_schools"], group="education", dec=0,
         ind={"es": "Estudiantes autistas en escuelas especiales (SINACES)", "en": "Autistic students in special schools (SINACES)"},
         ok={"es": "Informe SINACES, Tabla 1, p. 8.", "en": "SINACES report, Table 1, p. 8."}),
    dict(cfg="junaeb_unweighted_2024", module="05_education", names=["junaeb_unweighted_2024"], group="education", dec=0,
         ind={"es": "JUNAEB EVE 2024: estudiantes con TEA reportado por el cuidador (no ponderado)", "en": "JUNAEB EVE 2024: students with caregiver-reported TEA (unweighted)"},
         ok={"es": "Conteo no ponderado por nivel; 1.º medio 2024 no estimable (variable vacía, no cero). Cohortes escolares seleccionadas, no prevalencia nacional.",
             "en": "Unweighted count by level; 9th grade 2024 not estimable (empty variable, not zero). Selected school cohorts, not national prevalence."}),
    dict(cfg="junaeb_unweighted_2025", module="05_education", names=["junaeb_unweighted_2025"], group="education", dec=0,
         ind={"es": "JUNAEB EVE 2025: estudiantes con TEA reportado por el cuidador (no ponderado)", "en": "JUNAEB EVE 2025: students with caregiver-reported TEA (unweighted)"},
         ok={"es": "Conteo no ponderado por nivel; las proporciones del artículo usan el ponderador EXP.",
             "en": "Unweighted count by level; the proportions in the article use the EXP weight."}),
]

# Controles internos de otros módulos con estado 'differs' que no están en config.CONTROLS: se añaden a la T8 para que ninguna
# discrepancia del pipeline quede sin explicación en el manuscrito.
EXTRA_LABELS = {
    "grd_f84_exact_duplicates_on_read_columns": dict(group="grd", ind={"es": "Duplicados exactos entre episodios F84 sobre las 45 columnas analizadas", "en": "Exact duplicates among F84 episodes on the 45 analysed columns"}),
    "deis_vs_grd_observed_panel_strict_hospitalisation_vs_config": dict(group="deis", ind={"es": "Hospitalización estricta F84, panel observado (GRD leído por el módulo DEIS) frente al protocolo", "en": "Strict F84 hospitalisation, observed panel (GRD as read by the DEIS module) vs protocol"}),
    "rem20_duplicate_establishment_area_month_rows": dict(group="denominators", ind={"es": "REM-20: filas establecimiento-área-mes repetidas", "en": "REM-20: duplicated establishment-area-month rows"}),
    # Sin esta entrada la tabla imprimía la clave cruda del control como si fuese el nombre del indicador,
    # única fila de las 48 sin un rótulo legible.
    "T2_grd_persons_within_year_f84_any": dict(group="grd", ind={"es": "Personas únicas con F84 dentro del año (identificador válido)",
                                                                "en": "Unique persons with F84 within the year (valid identifier)"}),
}

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _sha(path: Path) -> str:
    return C.sha256_file(path)


def load_module_controls() -> dict[str, pd.DataFrame]:
    mods = {}
    for path in sorted(CONTROLS_DIR.glob("*_controls.csv")):
        module = path.name[: -len("_controls.csv")]
        if module == MODULE:
            continue
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
        for col in ["name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"]:
            if col not in df.columns:
                df[col] = ""
        df["module"] = module
        df["_order"] = np.arange(len(df))
        df["expected_num"] = pd.to_numeric(df["expected"], errors="coerce")
        df["observed_num"] = pd.to_numeric(df["observed"], errors="coerce")
        df["abs_diff_num"] = pd.to_numeric(df["abs_diff"], errors="coerce")
        df["rel_diff_num"] = pd.to_numeric(df["rel_diff"], errors="coerce")
        both = df.expected_num.notna() & df.observed_num.notna()
        df.loc[both & df.abs_diff_num.isna(), "abs_diff_num"] = df.observed_num - df.expected_num
        nz = both & (df.expected_num != 0)
        df.loc[nz & df.rel_diff_num.isna(), "rel_diff_num"] = (df.observed_num - df.expected_num) / df.expected_num
        df.attrs["path"] = str(path)
        mods[module] = df
    return mods


def load_reporting_n() -> dict[tuple[str, str, int], float]:
    """(código, medida, año) → establecimientos reportantes (variante single_code de rem_pathway_annual.csv)."""
    try:
        ann = C.read_tidy("rem_pathway_annual", dtype=str)
    except FileNotFoundError:
        return {}
    ann = ann.loc[ann.variant == "single_code"]
    out = {}
    for r in ann.itertuples(index=False):
        try:
            out[(str(r.code), str(r.measure), int(r.year))] = float(r.n_reporting_establishments)
        except (TypeError, ValueError):
            continue
    return out


def parse_key(module: str, key: str) -> tuple[int | None, str, str]:
    if module == "02_rem_pathway" and key.count("|") == 2:
        code, measure, year = key.split("|")
        return int(year), code, measure
    return (int(key) if re.fullmatch(r"\d{4}", key) else None), "", ""


def key_label(module: str, name: str, key: str, lang: str) -> str:
    year, code, measure = parse_key(module, key)
    if code:
        return f"{year} ({code}, {TXT['measure'][measure][lang]})"
    if name.startswith("junaeb_unweighted") and key in TXT["junaeb_level"]:
        return TXT["junaeb_level"][key][lang]
    if name == "endide_unweighted" and key in TXT["endide_key"]:
        return TXT["endide_key"][key][lang]
    if name == "encavi_unweighted" and key in TXT["encavi_key"]:
        return TXT["encavi_key"][key][lang]
    return key.replace("-", "–") if re.fullmatch(r"\d{4}-\d{4}", key) else key


def fmt_val(x, dec: int, lang: str, observed: bool = False) -> str:
    if x is None or pd.isna(x):
        return "—"
    d = dec + 2 if (observed and dec > 0) else dec
    return C.fmt_number(float(x), d, lang)


def fmt_diff(exp, obs, dec: int, lang: str) -> str:
    if exp is None or obs is None or pd.isna(exp) or pd.isna(obs):
        return "—"
    d = float(obs) - float(exp)
    if abs(d) < 1e-12:
        return "0"
    dd = dec + 2 if dec > 0 else 0
    s = ("+" if d > 0 else "−") + C.fmt_number(abs(d), dd, lang)
    if float(exp) != 0:
        r = 100 * d / float(exp)
        rd = 1 if abs(r) >= 0.1 else 2
        pct = C.fmt_number(abs(r), rd, lang) + (" %" if lang == "es" else "%")
        s += f" ({'+' if r > 0 else '−'}{pct})"
    return s


def status_label(status: str, lang: str) -> str:
    return TXT.get(f"status_{status}", {"es": status, "en": status})[lang]


def config_expected(cfg_key: str, name_index: int, key: str, module: str):
    """Valor esperado del protocolo (config.CONTROLS) para una fila del módulo; None si no aplica."""
    val = CFG.CONTROLS[cfg_key]
    year, _, _ = parse_key(module, key)
    if isinstance(val, dict):
        v = val.get(year) if year is not None else val.get(key)
        if v is None and year is not None:
            v = val.get(str(year))
        if isinstance(v, (tuple, list)):
            return v[name_index] if name_index < len(v) else None
        return v
    return val


def _obs(row) -> float:
    """Observado numérico tanto en filas del módulo (observed_num) como en filas de la T8 larga (observed)."""
    return getattr(row, "observed_num", None) if hasattr(row, "observed_num") else getattr(row, "observed", np.nan)


def _exp(row) -> float:
    return getattr(row, "expected_num", None) if hasattr(row, "expected_num") else getattr(row, "expected_config", np.nan)


def _lookup(mods, module, name, key, col="observed_num"):
    df = mods.get(module)
    if df is None:
        return np.nan
    r = df.loc[(df.name == name) & (df.key == key), col]
    return np.nan if r.empty else r.iloc[0]


# ---------------------------------------------------------------------------
# Explicaciones de las filas que difieren (leídas de la nota del módulo y de las filas de comprobación)
# ---------------------------------------------------------------------------
def ex_strict_hosp(row, mods, lang):
    y = row.key
    f = lambda v: C.fmt_number(v, 0, lang)  # noqa: E731
    any_ = _lookup(mods, "01_grd_core", "grd_f84_any", y)
    cma = _lookup(mods, "01_grd_core", "grd_cma", y)
    hosp = _lookup(mods, "01_grd_core", "grd_hospitals_observed", y)
    fixed = _lookup(mods, "01_grd_core", "grd_f84_any_strict_hospitalisation_fixed65", y)
    if lang == "es":
        return (f"Difiere solo en el panel observado ({f(hosp)} hospitales): {f(_obs(row))} = {f(any_)} episodios con F84 documentado − {f(cma)} CMA. "
                f"El valor del protocolo ({f(_exp(row))}) se reproduce exactamente en el panel fijo de 65 hospitales (fila de comprobación: {f(fixed)}); "
                "el protocolo combinó el panel fijo para la hospitalización con el panel observado para la CMA. No es un error de lectura: la serie principal cita el panel observado y el panel fijo es la sensibilidad.")
    return (f"Differs only on the observed panel ({f(hosp)} hospitals): {f(_obs(row))} = {f(any_)} episodes with documented F84 − {f(cma)} CMA. "
            f"The protocol value ({f(_exp(row))}) is reproduced exactly on the fixed panel of 65 hospitals (check row: {f(fixed)}); "
            "the protocol combined the fixed panel for hospitalisation with the observed panel for CMA. Not a reading error: the main series cites the observed panel and the fixed panel is the sensitivity.")


def ex_persons(row, mods, lang):
    y = row.key
    f = lambda v: C.fmt_number(v, 0, lang)  # noqa: E731
    m = re.search(r"(\d+) episodios F84 sin identificador válido excluidos(?: \(([^)]*)\))?", row.note)
    n_inv = m.group(1) if m else "?"
    ph = (m.group(2) or "").replace(":", " × ") if m else ""
    ph_txt = f" ({ph})" if ph else ""
    check = _lookup(mods, "01_grd_core", "grd_persons_within_year_f84_any_placeholder_as_one_id", y)
    d = abs(float(_obs(row)) - float(_exp(row)))
    if lang == "es":
        return (f"Difiere en exactamente {f(d)}: {n_inv} episodio(s) F84 sin identificador válido{ph_txt} se excluyen del recuento de personas, mientras que el protocolo contó "
                f"el marcador de identificador inválido como una persona adicional (fila de comprobación: {f(check)}). Personas únicas solo dentro del año; nunca se deduplica entre años.")
    return (f"Differs by exactly {f(d)}: {n_inv} F84 episode(s) without a valid identifier{ph_txt} are excluded from the person count, whereas the protocol counted "
            f"the invalid-identifier placeholder as one extra person (check row: {f(check)}). Unique persons within the year only; never deduplicated across years.")


def ex_duplicates(row, mods, lang):
    m = re.search(r"antes=(\d+), después=(\d+)", row.note)
    before, after = (m.group(1), m.group(2)) if m else ("?", "?")
    cols = re.search(r"difieren en (.*)$", row.note)
    cols = cols.group(1) if cols else ""
    f = lambda v: C.fmt_number(float(v), 0, lang) if v != "?" else v  # noqa: E731
    if lang == "es":
        return (f"En {row.key} un par de filas F84 es idéntico en las 45 columnas analizadas pero difiere en {cols}; no existe ningún duplicado de fila completa (129 columnas). "
                f"Se conserva como dos episodios: todos los controles y salidas usan los recuentos sin eliminación ({f(before)} frente a {f(after)} si se eliminara). "
                "El esperado 0 es una expectativa de calidad, no un total oficial.")
    return (f"In {row.key} one pair of F84 rows is identical on the 45 analysed columns but differs in {cols}; no full-row duplicate (129 columns) exists. "
            f"Kept as two episodes: every control and output uses the no-removal counts ({f(before)} versus {f(after)} if removed). "
            "The expected 0 is a data-quality expectation, not an official total.")


def ex_deis_cross(row, mods, lang):
    if lang == "es":
        return ("Control cruzado del módulo DEIS sobre grd_year_summary.csv: reproduce la misma discrepancia que el módulo GRD (panel observado de 68/72 hospitales frente al panel fijo de 65 "
                "usado por el protocolo para 2023–2024); la fila fijo × hospitalización del mismo módulo coincide exactamente. No es un error de lectura.")
    return ("Cross-module check by the DEIS module on grd_year_summary.csv: reproduces the same discrepancy as the GRD module (observed panel of 68/72 hospitals versus the fixed panel of 65 "
            "used by the protocol for 2023–2024); the fixed × hospitalisation row of the same module matches exactly. Not a reading error.")


def ex_rem20(row, mods, lang):
    if lang == "es":
        return ("Anomalía de la fuente REM-20: una fila establecimiento-área-mes repetida (Hospital Comunitario de Laja, código 120105, junio de 2020, área 407: una fila en cero y otra con datos). "
                "Se conserva porque es aditiva y no altera el panel de 188 ni las retenciones; el esperado 0 es una expectativa de calidad, no un total oficial.")
    return ("REM-20 source anomaly: one duplicated establishment-area-month row (Hospital Comunitario de Laja, code 120105, June 2020, area 407: one all-zero row and one data row). "
            "Kept because it is additive and does not alter the 188-establishment panel or the retention shares; the expected 0 is a data-quality expectation, not an official total.")


DIFFERS_EXPLAIN = {
    "grd_f84_any_strict_hospitalisation": ex_strict_hosp,
    "grd_persons_within_year_f84_any": ex_persons,
    "grd_f84_exact_duplicates_on_read_columns": ex_duplicates,
    "deis_vs_grd_observed_panel_strict_hospitalisation_vs_config": ex_deis_cross,
    "rem20_duplicate_establishment_area_month_rows": ex_rem20,
}


def ok_explanation(spec_ok: dict, row, lang: str) -> str:
    text = spec_ok[lang]
    if "{frac}" in text:
        m = re.search(r"=\s*(\d+)/(\d+)", row.note)
        frac = (f"{C.fmt_number(int(m.group(1)), 0, lang)}/{C.fmt_number(int(m.group(2)), 0, lang)}" if m else "—")
        text = text.replace("{frac}", frac)
    if "{dups}" in text:
        m = re.search(r"duplicados conservados=(\d+)", row.note)
        n = int(m.group(1)) if m else None
        if lang == "es":
            dups = f"{C.fmt_number(n, 0, lang)} filas repetidas en este año" if n is not None else "sin información"
        else:
            dups = f"{C.fmt_number(n, 0, lang)} repeated rows this year" if n is not None else "no information"
        text = text.replace("{dups}", dups)
    return text


# Las notas de módulo viajan en los CSV de controles en UN idioma (español, el del módulo productor) y la
# columna «Explicación» de la T8 las imprime tal cual. En el documento en inglés eso era una fuga de idioma:
# la nota de `T2_grd_persons_within_year_f84_any` (pipeline/09a_tables_main.py) se leía en español dentro de
# la Tabla 7 y de la tabla completa de controles. Cada nota que llega a esa columna se declara aquí en los dos
# idiomas; la parte variable (una cifra) se recupera del propio texto. Una nota nueva sin glosa se imprime tal
# cual y `tests/test_language_purity.py` la señala, que es exactamente el aviso que se busca.
NOTE_GLOSS: tuple[tuple[object, dict[str, str]], ...] = (
    (re.compile(r"^personas con identificador válido; el brief cuenta el marcador de identificador inválido "
                r"como una persona adicional \(módulo 01\); episodios F84 sin identificador válido = (?P<n>[\d.,]+)$"),
     {"es": "personas con identificador válido; el brief cuenta el marcador de identificador inválido como una "
            "persona adicional (módulo 01); episodios F84 sin identificador válido = {n}",
      "en": "persons with a valid identifier; the brief counts the invalid-identifier placeholder as one extra "
            "person (module 01); F84 episodes without a valid identifier = {n}"}),
    (re.compile(r"^diagnóstico: personas válidas \+ 1 si existe el marcador de identificador inválido "
                r"\(regla del brief\)$"),
     {"es": "diagnóstico: personas válidas + 1 si existe el marcador de identificador inválido (regla del brief)",
      "en": "diagnostic: valid persons + 1 when the invalid-identifier placeholder exists (the brief's rule)"}),
)


def note_text(note, lang: str) -> str:
    """La nota del módulo en el idioma del documento (los CSV de controles la guardan solo en español)."""
    text = str(note or "").strip()
    if not text:
        return "—"
    if lang == "es":
        return text
    for rx, gloss in NOTE_GLOSS:
        m = rx.match(text)
        if m:
            return gloss[lang].format(**m.groupdict())
    return text


def explanation(row, spec_ok: dict | None, mods, lang: str) -> str:
    if row.status == "differs":
        fn = DIFFERS_EXPLAIN.get(row.name)
        if fn is not None:
            return fn(row, mods, lang)
        return TXT["module_note"][lang].format(note=note_text(row.note, lang))
    if row.status == "missing":
        return TXT["no_row"][lang]
    if spec_ok is not None:
        return ok_explanation(spec_ok, row, lang)
    return TXT["module_note"][lang].format(note=note_text(row.note, lang))


# ---------------------------------------------------------------------------
# Construcción de la T8 (larga, numérica y compacta)
# ---------------------------------------------------------------------------
def build_t8(mods: dict[str, pd.DataFrame], rep_n: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Devuelve la tabla larga (una fila por control × clave, con columnas internas) y los problemas detectados."""
    issues = []
    rows = []
    covered = set()

    def add_rows(cfg_key, module, name, name_index, group, ind, ok, dec, is_companion):
        df = mods.get(module)
        sub = df.loc[df.name == name].copy() if df is not None else pd.DataFrame(columns=["key"])
        if sub.empty:
            issues.append(f"{module}: sin filas para el control '{name}' (config '{cfg_key}')")
            rows.append(dict(cfg_key=cfg_key, group=group, module=module, name=name, key="", year=None, code="", measure="",
                             expected_config=np.nan, expected_module=np.nan, observed=np.nan, abs_diff=np.nan, rel_diff=np.nan,
                             status="missing", note="", n_reporting=np.nan, ind=ind, ok=ok, dec=dec, companion=is_companion, sort=(9999, 0)))
            return
        for r in sub.sort_values("_order").itertuples(index=False):
            year, code, measure = parse_key(module, r.key)
            exp_cfg = None if is_companion else config_expected(cfg_key, name_index, r.key, module)
            if not is_companion and exp_cfg is not None and pd.notna(r.expected_num) and abs(float(exp_cfg) - float(r.expected_num)) > 1e-9:
                issues.append(f"{module}:{name}:{r.key}: expected del módulo ({r.expected}) ≠ config.CONTROLS ({exp_cfg})")
            if not is_companion and exp_cfg is None:
                continue  # clave del módulo fuera del control preespecificado (p. ej. filas adicionales del módulo)
            n_rep = rep_n.get((code, measure, year), np.nan) if code else np.nan
            rows.append(dict(cfg_key=cfg_key, group=group, module=module, name=name, key=r.key, year=year, code=code, measure=measure,
                             expected_config=(float(exp_cfg) if exp_cfg is not None else r.expected_num), expected_module=r.expected_num,
                             observed=r.observed_num, abs_diff=r.abs_diff_num, rel_diff=r.rel_diff_num, status=r.status, note=r.note,
                             n_reporting=n_rep, ind=ind, ok=ok, dec=dec, companion=is_companion, sort=(year if year is not None else 9000, name_index)))
        covered.add((module, name))

    for spec in SPEC:
        if spec["cfg"] not in CFG.CONTROLS:
            issues.append(f"config.CONTROLS no contiene '{spec['cfg']}'")
            continue
        for i, name in enumerate(spec["names"]):
            ind = spec.get("ind_by_name", {}).get(name, spec["ind"])
            add_rows(spec["cfg"], spec["module"], name, i, spec["group"], ind, spec["ok"], spec["dec"], False)
        for comp in spec.get("companions", []):
            add_rows(spec["cfg"], spec["module"], comp["name"], 0, spec["group"], comp["ind"], comp["ok"], spec["dec"], True)
    # Controles 'differs' de los módulos que no están en config.CONTROLS. Solo se examinan los módulos del
    # plan de análisis (00 a 09b): las diferencias de los módulos de material extendido se informan en el
    # ámbito `pipeline` del consolidado y no cambian la tabla del plan según qué módulos se hayan corrido.
    for module, df in mods.items():
        if module not in PLAN_MODULES:
            continue
        for r in df.loc[df.status == "differs"].sort_values("_order").itertuples(index=False):
            if (module, r.name) in covered:
                continue
            lab = EXTRA_LABELS.get(r.name, dict(group="module_check", ind={"es": r.name, "en": r.name}))
            year, code, measure = parse_key(module, r.key)
            rows.append(dict(cfg_key=f"module:{r.name}", group=lab["group"], module=module, name=r.name, key=r.key, year=year, code=code, measure=measure,
                             expected_config=r.expected_num, expected_module=r.expected_num, observed=r.observed_num, abs_diff=r.abs_diff_num,
                             rel_diff=r.rel_diff_num, status=r.status, note=r.note, n_reporting=np.nan, ind=lab["ind"], ok=None, dec=0, companion=False,
                             sort=(year if year is not None else 9000, 0)))
    long = pd.DataFrame(rows)
    long["year"] = long["year"].astype("Int64")
    # Orden: bloque (posición en SPEC/extra) y dentro del bloque por año y nombre
    block_order = {s["cfg"]: i for i, s in enumerate(SPEC)}
    long["_block"] = long.cfg_key.map(lambda k: block_order.get(k, len(SPEC) + (0 if k.startswith("module:grd") else 1 if k.startswith("module:deis") else 2)))
    long["_sort_year"] = long["sort"].map(lambda t: t[0])
    long["_sort_idx"] = long["sort"].map(lambda t: t[1])
    long["_comp"] = long.companion.astype(int)
    long = long.sort_values(["_block", "_comp", "_sort_year", "_sort_idx"], kind="stable").reset_index(drop=True)
    return long, issues


def _origin_tag(r, lang: str) -> str:
    """Rótulo de origen del valor esperado: protocolo (sin marca), fila de comprobación o control del módulo."""
    if getattr(r, "companion", False):
        return f" {TXT['check_row'][lang]}"
    if str(getattr(r, "cfg_key", "")).startswith("module:"):
        return f" {TXT['module_row'][lang]}"
    return ""


def render_t8(long: pd.DataFrame, mods, lang: str) -> pd.DataFrame:
    out = []
    for r in long.itertuples(index=False):
        ind = r.ind[lang] + _origin_tag(r, lang)
        expl = explanation(r, r.ok, mods, lang)
        if r.group == "rem" and pd.notna(r.n_reporting) and r.name != "p2_establishments_december":
            expl = f"{expl} {TXT['reporting_n'][lang].format(n=C.fmt_number(r.n_reporting, 0, lang))}"
        out.append({
            TXT["col_source"][lang]: TXT["group"][r.group][lang],
            TXT["col_indicator"][lang]: ind,
            TXT["col_key"][lang]: key_label(r.module, r.name, r.key, lang) if r.key else "—",
            TXT["col_expected"][lang]: fmt_val(r.expected_config, r.dec, lang),
            TXT["col_observed"][lang]: fmt_val(r.observed, r.dec, lang, observed=True),
            TXT["col_diff"][lang]: fmt_diff(r.expected_config, r.observed, r.dec, lang),
            TXT["col_status"][lang]: status_label(r.status, lang),
            TXT["col_explanation"][lang]: expl,
        })
    return pd.DataFrame(out)


def render_t8_numeric(long: pd.DataFrame) -> pd.DataFrame:
    num = long[["cfg_key", "group", "module", "name", "key", "year", "code", "measure", "expected_config", "expected_module", "observed",
                "abs_diff", "rel_diff", "status", "n_reporting", "companion", "note"]].copy()
    num = num.rename(columns={"n_reporting": "n_reporting_establishments", "companion": "is_check_row", "cfg_key": "config_key"})
    num["year"] = num["year"].astype("Int64")
    return num


def _range_label(keys_years: list[tuple[str, int | None, str, str]], module: str, name: str, lang: str) -> str:
    """Rango compacto de claves: por código consecutivo 'AAAA–AAAA (código, medida)'; si no hay años, lista de rótulos."""
    if keys_years and all(y is not None and pd.notna(y) for _, y, _, _ in keys_years):
        parts = []
        cur = None
        for key, y, code, measure in keys_years:
            y = int(y)
            if cur is None or cur["code"] != code or cur["measure"] != measure or y != cur["y1"] + 1:  # nuevo tramo si cambia el código o hay salto de años
                if cur is not None:
                    parts.append(cur)
                cur = dict(code=code, measure=measure, y0=y, y1=y)
            else:
                cur["y1"] = y
        parts.append(cur)
        labs = []
        for p in parts:
            span = f"{p['y0']}" if p["y0"] == p["y1"] else f"{p['y0']}–{p['y1']}"
            labs.append(f"{span} ({p['code']}, {TXT['measure'][p['measure']][lang]})" if p["code"] else span)
        return "; ".join(labs)
    return "; ".join(key_label(module, name, k, lang) for k, _, _, _ in keys_years if k) or "—"


def render_t8_compact(long: pd.DataFrame, mods, lang: str) -> pd.DataFrame:
    out = []
    for (cfg_key, name), g in long.groupby(["cfg_key", "name"], sort=False):
        g = g.sort_values(["_sort_year", "_sort_idx"])
        first = g.iloc[0]
        keys_years = [(r.key, r.year, r.code, r.measure) for r in g.itertuples(index=False)]
        n = len(g)
        n_ok = int((g.status == "ok").sum())
        differ_keys = [key_label(r.module, r.name, r.key, lang).split(" (")[0] for r in g.itertuples(index=False) if r.status == "differs"]
        missing_keys = [r.key for r in g.itertuples(index=False) if r.status == "missing"]
        status = TXT["match_summary"][lang].format(ok=n_ok, n=n)
        if differ_keys:
            status += "; " + TXT["differ_keys"][lang].format(keys=", ".join(differ_keys))
        if missing_keys:
            status += "; " + TXT["missing_keys"][lang].format(keys=", ".join(k or "—" for k in missing_keys))
        sep = " / "
        exp = sep.join(fmt_val(v, first.dec, lang) for v in g.expected_config)
        obs = sep.join(fmt_val(v, first.dec, lang, observed=True) for v in g.observed)
        diffs = [fmt_diff(e, o, first.dec, lang) for e, o in zip(g.expected_config, g.observed)]
        diff = "0" if all(d == "0" for d in diffs) else sep.join(diffs)
        differs_rows = g.loc[g.status == "differs"]
        if len(differs_rows):
            expl = "; ".join(dict.fromkeys(explanation(r, r.ok, mods, lang) for r in differs_rows.itertuples(index=False)))
        else:
            expl = explanation(first, first.ok, mods, lang)
        if first.group == "rem" and g.n_reporting.notna().any() and name != "p2_establishments_december":
            ns = sep.join(C.fmt_number(v, 0, lang) if pd.notna(v) else "—" for v in g.n_reporting)
            expl = f"{expl} {TXT['reporting_n'][lang].format(n=ns)}"
        out.append({
            TXT["col_source"][lang]: TXT["group"][first.group][lang],
            TXT["col_indicator"][lang]: first.ind[lang] + _origin_tag(first, lang),
            TXT["col_key"][lang]: _range_label(keys_years, first.module, name, lang),
            TXT["col_expected"][lang]: exp,
            TXT["col_observed"][lang]: obs,
            TXT["col_diff"][lang]: diff,
            TXT["col_status"][lang]: status,
            TXT["col_explanation"][lang]: expl,
        })
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Títulos y notas (titles.json)
# ---------------------------------------------------------------------------
def compact_note(note_common: str, lang: str, compact: pd.DataFrame | None) -> str:
    """La nota de la tabla BREVE: la cabecera que no afirma de más, y la cláusula de filas contada sobre ELLA.

    La nota es una sola para las dos tablas de controles —la larga, una fila por control indicador-año, y
    la breve, una fila por familia o por fila rotulada—, y ahí estaba el defecto IC-3: la cabecera abría
    diciendo «una fila por familia de control» y la cláusula del final contaba, sobre la misma tabla de 48
    filas, 42 familias, 2 filas de comprobación y 4 controles del módulo. Seis filas no son familias, y la
    nota se desmentía a sí misma dos oraciones más abajo. Aquí la cabecera remite al recuento del final y
    la cláusula se reescribe con las cifras de la tabla breve, no con las de la larga: así lo que se guarda
    en titles.json es ya lo que se imprime, y `prose_*.table_note` —que reescribe la misma cláusula con la
    misma función de `common`— no tiene nada que corregir."""
    note = note_common
    if compact is not None:
        m = C.CONTROLS_ROWS_CLAUSE_RE[lang].search(note)
        if m:
            note = note[:m.start()] + C.controls_compact_clause(compact, lang) + note[m.end():]
    return C.controls_compact_lead(lang) + note


def titles_entries(long: pd.DataFrame, lang: str, compact: pd.DataFrame | None = None) -> dict:
    n_ctrl = int((~long.companion & ~long.cfg_key.str.startswith("module:")).sum())
    n_diff = int((long.status == "differs").sum())
    n_ok = int((long.status == "ok").sum())
    n_cfg = len(CFG.CONTROLS)
    if lang == "es":
        note_common = (
            f"Esperado = valores preespecificados del protocolo (config.CONTROLS: brief y DATA_REVIEW.md; {n_cfg} familias de control). "
            "Observado = valor reproducido por el módulo indicado a partir de los archivos fuente (SHA-256 en data_provenance.csv). "
            "Estado: coincide = igualdad exacta (conteos) o diferencia relativa ≤ 0,5 % (medias y proporciones); difiere = en otro caso, con la explicación leída de la nota del módulo. "
            "Todos los conteos son reconocimiento administrativo (episodios, ingresos, intervenciones, stocks, inscritos, matrículas), no prevalencia ni incidencia. "
            "GRD: episodios con F84 documentado en cualquier posición (F84 principal como serie separada), panel observado (65/65/65/65/68/72 hospitales en 2019–2024) o panel fijo de 65; personas únicas solo dentro de cada año. "
            "REM: sumas anuales de flujos (A03, A27, A05, A28) y stocks de diciembre (P2, P6), con el número de establecimientos reportantes en la explicación; P6 2019–2020 es TGD amplio y 2021+ autismo estricto (quiebre de definición); junio nunca se suma con diciembre. "
            "Denominadores: INE (residencia), FONASA/ISAPRE (aseguramiento) y APS (lugar de atención) son capas distintas; REM-20 mide actividad, no población cubierta. "
            "Encuestas: conteos no ponderados de comprobación; las estimaciones del artículo usan el diseño complejo. Educación: stocks escolares del PIE y conteos JUNAEB no ponderados. "
            "La tabla es idéntica en las variantes con y sin síndrome de Rett: los controles GRD se definieron sobre la familia F84 completa y las demás series no dependen de la variante. "
            f"Ámbito de esta tabla: {CR.phrase(CR.ANALYSIS_PLAN, 'es')} (columna scope = analysis_plan de controls_summary.csv); no debe sumarse con el total {CR.phrase(CR.PIPELINE, 'es')}, que cuenta una fila por control escrito por cada módulo y se informa en la metodología extendida y en la sección de controles de reproducción del material suplementario. "
            f"Filas: {len(long)} ({n_ok} coinciden, {n_diff} difieren, todas explicadas). 2020–2021: disrupción del reporte por la pandemia; la Ley 21.545 (marzo de 2023) es contexto, no intervención."
        )
        return {
            "T8_controls": {"title": f"Tabla 8. Controles de reproducción: valores esperados del protocolo frente a valores reproducidos por el pipeline, por fuente, indicador y año ({len(long)} filas, de las cuales {n_ctrl} con valor esperado preespecificado en el protocolo y {len(long) - n_ctrl} rotuladas «fila de comprobación» o «control del módulo» en la columna del indicador)", "note": note_common},
            "T8_controls_compact": {"title": "Tabla 8 (versión breve). Controles de reproducción por familia de indicador: esperado frente a observado, estado y explicación", "note": compact_note(note_common, "es", compact)},
        }
    note_common = (
        f"Expected = pre-specified protocol values (config.CONTROLS: brief and DATA_REVIEW.md; {n_cfg} control families). "
        "Observed = value reproduced by the stated module from the source files (SHA-256 in data_provenance.csv). "
        "Status: matches = exact equality (counts) or relative difference ≤ 0.5% (means and proportions); differs = otherwise, with the explanation read from the module note. "
        "All counts are administrative recognition (episodes, entries, interventions, stocks, enrolled persons, school enrolments), not prevalence or incidence. "
        "GRD: episodes with documented F84 in any position (principal F84 as a separate series), observed panel (65/65/65/65/68/72 hospitals in 2019–2024) or fixed panel of 65; unique persons within each year only. "
        "REM: annual sums of flows (A03, A27, A05, A28) and December stocks (P2, P6), with the number of reporting establishments in the explanation; P6 2019–2020 is broad PDD and 2021+ strict autism (definition break); June is never summed with December. "
        "Denominators: INE (residence), FONASA/ISAPRE (insurance) and APS (place of care) are distinct layers; REM-20 measures activity, not covered population. "
        "Surveys: unweighted check counts; the article's estimates use the complex design. Education: PIE school stocks and unweighted JUNAEB counts. "
        "The table is identical in the with- and without-Rett variants: the GRD controls were defined on the full F84 family and the other series do not depend on the variant. "
        f"Scope of this table: {CR.phrase(CR.ANALYSIS_PLAN, 'en')} (column scope = analysis_plan in controls_summary.csv); it must never be added to the total {CR.phrase(CR.PIPELINE, 'en')}, which counts one row per control written by each module and is reported in the extended methodology and in the reproduction-controls section of the supplementary material. "
        f"Rows: {len(long)} ({n_ok} match, {n_diff} differ, all explained). 2020–2021: pandemic reporting disruption; Law 21.545 (March 2023) is context, not an intervention."
    )
    return {
        "T8_controls": {"title": f"Table 8. Reproduction controls: pre-specified protocol values versus values reproduced by the pipeline, by source, indicator and year ({len(long)} rows, of which {n_ctrl} carry a value pre-specified in the protocol and {len(long) - n_ctrl} are labelled 'check row' or 'module control' in the indicator column)", "note": note_common},
        "T8_controls_compact": {"title": "Table 8 (compact). Reproduction controls by indicator family: expected versus observed, status and explanation", "note": compact_note(note_common, "en", compact)},
    }


def merge_titles(path: Path, entries: dict) -> None:
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    data.update(entries)
    C.atomic_write_json(data, path)


# ---------------------------------------------------------------------------
# Resumen consolidado (CSV y markdown)
# ---------------------------------------------------------------------------
def plan_rows(long: pd.DataFrame) -> pd.DataFrame:
    """Filas del ámbito `analysis_plan`: un control indicador-año de la tabla preespecificada por fila.

    No son las mismas filas que las de los módulos: la tabla del plan reexpresa un control por indicador y
    año, añade filas de comprobación y trae las diferencias internas de los módulos del plan. Por eso los dos
    ámbitos NO se suman y el consolidado los separa con la columna `scope`.
    """
    if long.empty:
        return pd.DataFrame(columns=SUMMARY_COLS)
    def _num(v):
        return "" if v is None or pd.isna(v) else repr(float(v))
    rows = []
    for r in long.itertuples(index=False):
        note = f"[{r.cfg_key}]" + (" fila de comprobación;" if r.companion else "") + (f" {r.note}" if r.note else "")
        rows.append(dict(scope=CR.ANALYSIS_PLAN, module=r.module, name=r.name, key=r.key,
                         expected=_num(r.expected_config), observed=_num(r.observed),
                         abs_diff=_num(r.abs_diff), rel_diff=_num(r.rel_diff), status=r.status, note=note.strip()))
    return pd.DataFrame(rows, columns=SUMMARY_COLS)


def build_summary(mods: dict[str, pd.DataFrame], own: pd.DataFrame, long: pd.DataFrame | None = None) -> pd.DataFrame:
    frames = []
    for module in sorted(mods):
        df = mods[module].copy()
        # abs_diff / rel_diff calculados cuando el módulo los dejó vacíos pero ambos valores son numéricos
        fill_abs = (df.abs_diff == "") & df.abs_diff_num.notna()
        fill_rel = (df.rel_diff == "") & df.rel_diff_num.notna()
        df.loc[fill_abs, "abs_diff"] = df.loc[fill_abs, "abs_diff_num"].map(lambda v: repr(float(v)))
        df.loc[fill_rel, "rel_diff"] = df.loc[fill_rel, "rel_diff_num"].map(lambda v: repr(float(v)))
        df["scope"] = CR.PIPELINE
        frames.append(df[SUMMARY_COLS])
    own = own.copy()
    own["module"] = MODULE
    own["scope"] = CR.PIPELINE
    frames.append(own[SUMMARY_COLS].astype(str))
    if long is not None:
        frames.append(plan_rows(long))
    return pd.concat(frames, ignore_index=True)


def _md_escape(s) -> str:
    s = "" if s is None else str(s)
    return re.sub(r"\s+", " ", s).replace("|", "\\|").strip()


def build_markdown(summary: pd.DataFrame, long: pd.DataFrame, mods, n_files: int) -> str:
    L = []
    L.append(TXT["md_title"]["es"])
    L.append("")
    L.append(TXT["md_generated"]["es"].format(ts=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), n=n_files))
    L.append("")
    L.append(TXT["md_scopes"]["es"])
    L.append("")
    L.append("| scope | ámbito en palabras | checks | ok | info | differs | módulos |")
    L.append("|---|---|---|---|---|---|---|")
    for scope in CR.scopes():
        sub = summary.loc[summary.scope == scope]
        st = sub.status.astype(str)
        L.append(f"| `{scope}` | {CR.SCOPES[scope]['phrase']['es'].format(n=sub.module.nunique())} | {len(sub)} | "
                 f"{int((st == 'ok').sum())} | {int((st == 'info').sum())} | {int((st == 'differs').sum())} | "
                 f"{sub.module.nunique()} |")
    L.append("")
    L.append(TXT["md_scopes_note"]["es"])
    L.append("")
    pipeline = summary.loc[summary.scope == CR.PIPELINE]
    L.append(TXT["md_totals_status"]["es"])
    L.append("")
    L.append("| status | n |")
    L.append("|---|---|")
    for st, n in pipeline.status.value_counts().items():
        L.append(f"| {st} | {n} |")
    L.append(f"| **total** | **{len(pipeline)}** |")
    L.append("")
    L.append(TXT["md_totals_module"]["es"])
    L.append("")
    piv = pipeline.pivot_table(index="module", columns="status", values="name", aggfunc="size", fill_value=0)
    statuses = [s for s in ["ok", "differs", "info", "missing"] if s in piv.columns] + [s for s in piv.columns if s not in {"ok", "differs", "info", "missing"}]
    piv = piv.reindex(columns=statuses, fill_value=0)
    piv["total"] = piv.sum(axis=1)
    L.append("| module | " + " | ".join(statuses) + " | total |")
    L.append("|---|" + "---|" * (len(statuses) + 1))
    for module, r in piv.iterrows():
        L.append(f"| {module} | " + " | ".join(str(int(r[s])) for s in statuses) + f" | {int(r['total'])} |")
    L.append("| **total** | " + " | ".join(str(int(piv[s].sum())) for s in statuses) + f" | **{int(piv['total'].sum())}** |")
    L.append("")
    L.append(TXT["md_differs"]["es"])
    L.append("")
    diff = long.loc[long.status == "differs"]
    if diff.empty:
        L.append(TXT["md_none_differ"]["es"])
    else:
        L.append("| module | name | key | expected | observed | explicación |")
        L.append("|---|---|---|---|---|---|")
        for r in diff.itertuples(index=False):
            L.append(f"| {r.module} | {r.name} | {_md_escape(r.key)} | {fmt_val(r.expected_config, r.dec, 'es')} | {fmt_val(r.observed, r.dec, 'es', observed=True)} | {_md_escape(explanation(r, r.ok, mods, 'es'))} |")
    L.append("")
    L.append(TXT["md_full"]["es"])
    L.append("")
    L.append("| " + " | ".join(SUMMARY_COLS) + " |")
    L.append("|" + "---|" * len(SUMMARY_COLS))
    for r in summary.itertuples(index=False):
        L.append("| " + " | ".join(_md_escape(getattr(r, c)) for c in SUMMARY_COLS) + " |")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Controles propios del módulo
# ---------------------------------------------------------------------------
def own_controls(mods, long: pd.DataFrame, issues: list[str], summary_rows: int | None = None) -> pd.DataFrame:
    def row(name, key, expected, observed, note, status=None):
        exp_n, obs_n = pd.to_numeric(expected, errors="coerce"), pd.to_numeric(observed, errors="coerce")
        if status is None:
            if pd.isna(exp_n):
                status = "info"
            else:
                status = "ok" if (pd.notna(obs_n) and abs(float(obs_n) - float(exp_n)) < 1e-9) else "differs"
        return dict(name=name, key=key, expected="" if pd.isna(exp_n) else expected, observed=observed,
                    abs_diff="" if (pd.isna(exp_n) or pd.isna(obs_n)) else float(obs_n) - float(exp_n),
                    rel_diff="" if (pd.isna(exp_n) or pd.isna(obs_n) or float(exp_n) == 0) else (float(obs_n) - float(exp_n)) / float(exp_n),
                    status=status, note=note)

    n_cfg = len(CFG.CONTROLS)
    covered_cfg = {k for k in long.cfg_key.unique() if not str(k).startswith("module:")}
    n_missing_rows = int((long.status == "missing").sum())
    n_mismatch = sum(1 for i in issues if "≠ config.CONTROLS" in i)
    n_diff = int((long.status == "differs").sum())
    n_unexplained = sum(1 for r in long.loc[long.status == "differs"].itertuples(index=False)
                        if r.name not in DIFFERS_EXPLAIN)
    n_required = sum(1 for m in EXPECTED_MODULES if m in mods)
    n_plan = sum(1 for m in PLAN_MODULES if m in mods)
    rows = [
        row("module_control_files_found", "all", len(EXPECTED_MODULES), n_required,
            "módulos de fase 1 que deben existir antes de consolidar, presentes: " + ", ".join(m for m in EXPECTED_MODULES if m in mods)),
        row("control_files_consolidated", "all", np.nan, len(mods) + 1,
            "archivos <módulo>_controls.csv consolidados en controls_summary.csv con scope=pipeline (incluido 07_controls): "
            + ", ".join(sorted(list(mods) + [MODULE]))),
        row("plan_modules_present", "all", len(PLAN_MODULES), n_plan,
            "módulos del plan de análisis (00–09b) cuyas filas 'differs' pueden entrar en la T8: " + ", ".join(m for m in PLAN_MODULES if m in mods)),
        row("config_controls_with_module_rows", "all", n_cfg, len(covered_cfg), "familias de config.CONTROLS con al menos una fila reproducida en la T8"),
        row("config_controls_rows_missing", "all", 0, n_missing_rows, "filas preespecificadas sin fila del módulo (estado 'missing' en la T8)"),
        row("config_expected_equals_module_expected_mismatches", "all", 0, n_mismatch, "valor esperado del módulo distinto del de config.CONTROLS"),
        row("t8_differs_rows_without_curated_explanation", "all", 0, n_unexplained, "filas 'differs' cuya explicación se toma de la nota del módulo sin redacción curada"),
        row("t8_rows_total", "all", np.nan, len(long), "filas de la T8 larga (incluye filas de comprobación y controles internos que difieren)"),
        row("t8_rows_differs", "all", np.nan, n_diff, "filas de la T8 con estado 'differs' (todas explicadas)"),
    ]
    if summary_rows is not None:
        rows.append(row("controls_summary_rows", "all", np.nan, summary_rows,
                        "filas de controls_summary.csv (los dos ámbitos juntos; los ámbitos no se suman entre sí, ver la columna scope)"))
        rows.append(row("controls_summary_rows_scope_pipeline", CR.PIPELINE, np.nan, summary_rows - len(long),
                        "filas con scope=pipeline: un control por cada fila de cada <módulo>_controls.csv"))
        rows.append(row("controls_summary_rows_scope_analysis_plan", CR.ANALYSIS_PLAN, np.nan, len(long),
                        "filas con scope=analysis_plan: un control indicador-año de la tabla preespecificada"))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def main() -> int:
    t0 = time.time()
    mods = load_module_controls()
    missing_mods = [m for m in EXPECTED_MODULES if m not in mods]
    rep_n = load_reporting_n()
    long, issues = build_t8(mods, rep_n)
    if missing_mods:
        issues.append("módulos sin archivo de controles: " + ", ".join(missing_mods))
    written = {}

    # (a) resumen consolidado, con la columna de ámbito
    own_base = own_controls(mods, long, issues)                       # sin las tres filas autorreferentes
    n_pipeline = sum(len(df) for df in mods.values()) + len(own_base) + 3
    own = own_controls(mods, long, issues, summary_rows=n_pipeline + len(long))
    summary = build_summary(mods, own, long)
    if len(summary) != n_pipeline + len(long):                        # el recuento que el propio archivo declara
        raise AssertionError(f"controls_summary.csv: {len(summary)} filas ≠ {n_pipeline + len(long)} declaradas")
    p = C.atomic_write_csv(summary, CONTROLS_DIR / "controls_summary.csv")
    scope_totals = CR.all_totals(path=p, refresh=True)
    written["controls_summary_csv"] = {"path": str(p), "rows": int(len(summary)), "columns": SUMMARY_COLS,
                                       "scopes": {s: {k: t[k] for k in ("checks", "ok", "info", "differs", "modules")}
                                                  for s, t in scope_totals.items()}}
    md = build_markdown(summary, long, mods, len(mods) + 1)
    p_md = CONTROLS_DIR / "controls_summary.md"
    tmp = p_md.with_suffix(".md.tmp")
    tmp.write_text(md, encoding="utf-8")
    tmp.replace(p_md)
    written["controls_summary_md"] = {"path": str(p_md), "bytes": p_md.stat().st_size}

    # (b) T8 por variante e idioma
    numeric = render_t8_numeric(long)
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            tdir = CFG.OUT / variant / lang / "tables"
            t8 = render_t8(long, mods, lang)
            t8c = render_t8_compact(long, mods, lang)
            p1 = C.atomic_write_csv(t8, tdir / "T8_controls.csv")
            p2 = C.atomic_write_csv(numeric, tdir / "T8_controls_numeric.csv")
            p3 = C.atomic_write_csv(t8c, tdir / "T8_controls_compact.csv")
            merge_titles(tdir / "titles.json", titles_entries(long, lang, compact=t8c))
            written[f"T8_{variant}_{lang}"] = {"T8_controls": str(p1), "rows": int(len(t8)), "T8_controls_numeric": str(p2), "T8_controls_compact": str(p3),
                                              "compact_rows": int(len(t8c)), "titles_json": str(tdir / "titles.json")}

    # controles propios y registro de ejecución
    ctl_path = C.atomic_write_csv(own, CONTROLS_DIR / f"{MODULE}_controls.csv")
    seconds = time.time() - t0
    runlog = {
        "module": MODULE, "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seconds_total": round(seconds, 2),
        "inputs": {m: {"path": df.attrs.get("path"), "rows": int(len(df)), "sha256": _sha(Path(df.attrs["path"])),
                       "status": df.status.value_counts().to_dict()} for m, df in mods.items()},
        "rem_pathway_annual_used": bool(rep_n),
        "outputs": written, "own_controls": str(ctl_path), "own_controls_status": own.status.value_counts().to_dict(),
        "issues": issues,
        "t8_status": long.status.value_counts().to_dict(),
        "plan_modules": [m for m in PLAN_MODULES if m in mods],
        "scope_totals": scope_totals,
        "summary_status": summary.loc[summary.scope == CR.PIPELINE].status.value_counts().to_dict(),
    }
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    print(own[["name", "key", "expected", "observed", "status"]].to_string(index=False), flush=True)
    for _s, _t in scope_totals.items():
        print(f"[{MODULE}] ámbito {_s}: {_t['checks']} comprobaciones ({_t['phrase_es']}); "
              f"ok {_t['ok']}, info {_t['info']}, differs {_t['differs']}, módulos {_t['modules']}", flush=True)
    print(f"[{MODULE}] resumen: {runlog['summary_status']}; T8: {runlog['t8_status']}", flush=True)
    for i in issues:
        print(f"[{MODULE}] aviso: {i}", flush=True)
    print(f"[{MODULE}] listo en {seconds:,.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
