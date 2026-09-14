# -*- coding: utf-8 -*-
"""09b_tables_supplementary.py — tablas suplementarias ST1–ST14 del estudio multisistema.

Entradas (todas en outputs/tidy/, producidas por los módulos 00–05):
  grd_fixed_panel_hospitals, grd_hospital_year, rem_code_dictionary_check, rem_establishment_year, comuna_unmatched,
  comuna_name_matches, comuna_crosswalk, survey_items_dictionary, junaeb_items_dictionary, junaeb_tea_year_level,
  data_provenance, provenance_manifest_checks, grd_identifier_audit, grd_age_sex_year, grd_subcode_year,
  deis_year_summary, deis_vs_grd_year, fonasa_schema_by_year, fonasa_beneficiaries_comuna_year, isapre_beneficiaries_national_year, aps_panel,
  rem_a05_age_sex_annual, rem_pathway_annual.

Salidas, por variante (con_rett / sin_rett) e idioma (es / en), en outputs/<variante>/<idioma>/tables/:
  ST1_grd_hospital_panel            hospitales del panel fijo de 65 y del panel observado, episodios y F84 por año
  ST2_rem_code_dictionary           verificación de cada código REM contra el diccionario anual (2019–2025)
  ST3_rem_reporting_establishments  establecimientos reportantes por módulo, código y año, con panel estable
  ST4a_comuna_crosswalk_summary     resumen del crosswalk comunal por fuente y método (exacto / alias)
  ST4b_comuna_unmatched             nombres no enlazados (marcadores no geográficos) por fuente y año
  ST5_survey_items                  diccionario de ítems ENDIDE 2022 y ENCAVI 2023–2024
  ST6_junaeb_items (+ _long)        diccionario JUNAEB EVE por año y nivel
  ST7_provenance, ST7b_manifest_checks  procedencia completa y concordancia SHA-256 con los manifiestos
  ST8_grd_identifier_audit          auditoría del identificador GRD por año
  ST9_grd_age_sex                   distribución edad × sexo de los episodios con F84 por año
  ST10_grd_f84_subcodes             subcódigos F84 por año y posición
  ST11a_deis_annual, ST11b_deis_vs_grd  resumen anual DEIS y comparación DEIS/GRD (F84 principal frente a principal)
  ST12a_fonasa_schema, ST12b_isapre_rules, ST12c_aps_panel  esquemas FONASA por año y reglas de armonización ISAPRE/APS
  ST13_a05_age_sex                  ingresos A05 por grupo de edad y sexo por año (TGD amplio, familia de la variante, autismo estricto)
  ST14_p2_p6_june_december          stocks P2/P6 de junio frente a diciembre con establecimientos reportantes
  *_numeric.csv                     versiones numéricas legibles por máquina donde corresponde
  titles.json                       {nombre: {title, note}} fusionado con las entradas de otros módulos
  outputs/controls/09b_tables_supplementary_controls.csv y _runlog.json (tiempos de ejecución)

Reglas aplicadas: los conteos son reconocimiento administrativo (nunca prevalencia ni incidencia); el resultado GRD es
«episodios con F84 documentado» y F84 principal es una serie separada; las series REM se presentan por era de definición;
toda tabla REM muestra establecimientos reportantes; Serie P usa diciembre y junio solo como sensibilidad (nunca se suman);
no se muestran cocientes entre fuentes no homologables (DEIS «cualquier posición» = «principal» porque DIAG2 nunca contiene F84);
toda ventana de años impresa lleva raya («2019–2025»), también dentro de una frase, y conservan el guion ASCII las rutas, los
nombres de archivo, las URL del manifiesto y las columnas que declaran transcripción literal (ver `yspan_prose` y `VERBATIM_KEYS`).

Uso (desde la raíz del repositorio):  python3 study/pipeline/09b_tables_supplementary.py
"""
from __future__ import annotations

import csv
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
import labels as LB  # noqa: E402  (glosa bilingüe del texto libre de las tablas tidy y de la procedencia)

MODULE = "09b_tables_supplementary"
#: Las tablas que ESTE módulo escribe, y las únicas que sus controles releen: la carpeta
#: `outputs/<variante>/<idioma>/tables/` la comparten varios módulos.
TABLE_NAMES = ("ST1_grd_hospital_panel", "ST2_rem_code_dictionary", "ST3_rem_reporting_establishments",
               "ST4a_comuna_crosswalk_summary", "ST4b_comuna_unmatched", "ST5_survey_items",
               "ST6_junaeb_items", "ST7_provenance", "ST7b_manifest_checks", "ST8_grd_identifier_audit",
               "ST9_grd_age_sex", "ST10_grd_f84_subcodes", "ST11a_deis_annual", "ST11b_deis_vs_grd",
               "ST12a_fonasa_schema", "ST12b_isapre_rules", "ST12c_aps_panel", "ST13_a05_age_sex",
               "ST14_p2_p6_june_december")
CONTROLS_DIR = CFG.OUT / "controls"
DASH = "—"
YEARS_GRD = CFG.YEARS_GRD
YEARS_REM = CFG.YEARS_REM

# ---------------------------------------------------------------------------
# Rótulos bilingües (ningún literal suelto en el cuerpo del script)
# ---------------------------------------------------------------------------
TXT = {
    "yes": {"es": "Sí", "en": "Yes"}, "no": {"es": "No", "en": "No"},
    # «n/e» (no estimable / not estimable) es el marcador único del estudio y se escribe igual en los dos
    # idiomas; «n/a» era un anglicismo que solo aparecía en la ST13 y desentonaba con las 2.302
    # apariciones de «n/e» del resto del suplemento.
    "na": {"es": "n/e", "en": "n/e"},
    "not_reported": {"es": "no informado (sin filas)", "en": "not reported (no rows)"},
    "not_listed": {"es": "no listado en manifiesto", "en": "not listed in any manifest"},
    "table": {"es": "Tabla", "en": "Table"},
    "variant_suffix": {"es": " — variante {v}", "en": " — {v} variant"},
    "identical_variants": {"es": "Idéntica en las variantes con y sin síndrome de Rett.", "en": "Identical in the with- and without-Rett variants."},
    "admin_note": {"es": "Todos los conteos son reconocimiento administrativo, no prevalencia ni incidencia; las fuentes no se enlazan por persona.",
                   "en": "All counts are administrative recognition, not prevalence or incidence; sources are not linked at person level."},
    "pandemic_law": {"es": "2020–2021: disrupción del reporte por la pandemia; la Ley 21.545 (marzo de 2023) es contexto, no intervención.",
                     "en": "2020–2021: pandemic reporting disruption; Law 21.545 (March 2023) is context, not an intervention."},
    # columnas genéricas
    "col_year": {"es": "Año", "en": "Year"}, "col_code": {"es": "Código", "en": "Code"}, "col_codes": {"es": "Código(s)", "en": "Code(s)"},
    "col_module": {"es": "Módulo REM", "en": "REM module"}, "col_era": {"es": "Era de definición", "en": "Definition era"},
    "col_indicator": {"es": "Indicador", "en": "Indicator"}, "col_series": {"es": "Serie", "en": "Series"},
    "col_source": {"es": "Fuente", "en": "Source"}, "col_file": {"es": "Archivo", "en": "File"},
    "col_sex": {"es": "Sexo", "en": "Sex"}, "col_age_group": {"es": "Grupo de edad (años)", "en": "Age group (years)"},
    "col_variant": {"es": "Variante", "en": "Variant"}, "col_block": {"es": "Bloque", "en": "Block"},
    "col_note": {"es": "Nota", "en": "Note"}, "col_level": {"es": "Nivel", "en": "Level"},
    # ST1
    "col_hospital": {"es": "Hospital", "en": "Hospital"}, "col_fixed_panel": {"es": "Panel fijo de 65", "en": "Fixed panel of 65"},
    "col_years_present": {"es": "Años con episodios (n)", "en": "Years with episodes (n)"},
    "st1_total_observed": {"es": "Total, panel anual observado", "en": "Total, observed annual panel"},
    "st1_total_fixed": {"es": "Total, panel fijo de 65 hospitales", "en": "Total, fixed panel of 65 hospitals"},
    "st1_n_observed": {"es": "Hospitales observados (n)", "en": "Observed hospitals (n)"},
    "st1_n_fixed": {"es": "Hospitales del panel fijo presentes (n)", "en": "Fixed-panel hospitals present (n)"},
    "st1_f84_principal_obs": {"es": "Episodios con F84 principal, panel observado", "en": "Episodes with principal F84, observed panel"},
    # ST2
    "col_dict_label": {"es": "Rótulo del diccionario (último año hallado; textual)", "en": "Dictionary label (last year found; verbatim Spanish)"},
    "col_section": {"es": "Sección del diccionario (textual)", "en": "Dictionary section (verbatim Spanish)"},
    "col_col01": {"es": "Significado de COL01 (textual)", "en": "Meaning of COL01 (verbatim Spanish)"},
    "col_col02": {"es": "Significado de COL02 (textual)", "en": "Meaning of COL02 (verbatim Spanish)"},
    "col_age_columns": {"es": "Columnas de edad × sexo (COL04–COL37)", "en": "Age × sex columns (COL04–COL37)"},
    "col_n_tokens": {"es": "Nº de columnas COL en la fila", "en": "Number of COL tokens in the row"},
    "col_layout": {"es": "Comprobación de diseño", "en": "Layout check"},
    "col_dict_file": {"es": "Diccionario (último año hallado)", "en": "Dictionary file (last year found)"},
    "col_consistency": {"es": "Hallado solo dentro de la era", "en": "Found only within its era"},
    "found": {"es": "Sí", "en": "Yes"}, "found_outside_era": {"es": "Sí (fuera de era)", "en": "Yes (outside era)"},
    "missing_in_era": {"es": "No (falta en era)", "en": "No (missing in era)"}, "layout_ok": {"es": "correcto", "en": "ok"},
    # ST3
    "col_cell_def": {"es": "Definición de la celda", "en": "Cell definition"},
    "st3_cell_a": {"es": "Establecimientos con ≥1 mes reportado (panel estable)", "en": "Establishments with ≥1 month reported (stable panel)"},
    "st3_cell_p": {"es": "Establecimientos con fila de diciembre / de junio (panel estable de diciembre)", "en": "Establishments with a December row / a June row (December stable panel)"},
    "st3_cell_mod": {"es": "Establecimientos con ≥1 fila de cualquier código del módulo", "en": "Establishments with ≥1 row of any code of the module"},
    "st3_module_total": {"es": "Todos los códigos del módulo", "en": "All codes of the module"},
    # ST4
    "col_method": {"es": "Método de enlace", "en": "Linkage method"}, "method_exact": {"es": "exacto (nombre normalizado)", "en": "exact (normalised name)"},
    "method_alias": {"es": "alias explícito", "en": "explicit alias"}, "method_all": {"es": "todos los métodos", "en": "all methods"},
    "col_raw_names": {"es": "Nombres crudos (n)", "en": "Raw names (n)"}, "col_comunas": {"es": "Comunas distintas (n de 346)", "en": "Distinct comunas (n of 346)"},
    "col_years": {"es": "Años", "en": "Years"}, "col_detail": {"es": "Detalle", "en": "Detail"},
    "st4_unmatched_detail": {"es": "Marcadores no geográficos no enlazados: {n}", "en": "Unlinked non-geographic placeholders: {n}"},
    "col_raw_name": {"es": "Nombre crudo", "en": "Raw name"}, "col_normalised": {"es": "Nombre normalizado", "en": "Normalised name"},
    "col_rows": {"es": "Filas", "en": "Rows"}, "col_count": {"es": "Personas en las filas no enlazadas", "en": "Persons in the unlinked rows"},
    "col_share": {"es": "% del total nacional de la fuente", "en": "% of the source's national total"},
    "col_reason": {"es": "Motivo", "en": "Reason"}, "reason_placeholder": {"es": "marcador no geográfico (sin comuna)", "en": "non-geographic placeholder (no comuna)"},
    # ST5
    "col_survey": {"es": "Encuesta", "en": "Survey"}, "col_survey_module": {"es": "Módulo", "en": "Module"}, "col_variable": {"es": "Variable", "en": "Variable"},
    "col_var_label": {"es": "Etiqueta de la variable (textual)", "en": "Variable label (verbatim Spanish)"},
    "col_wording": {"es": "Redacción de la pregunta (textual)", "en": "Question wording (verbatim Spanish)"},
    "col_respondent": {"es": "Informante", "en": "Respondent"}, "col_universe": {"es": "Universo", "en": "Universe"},
    "col_codes_resp": {"es": "Códigos de respuesta", "en": "Response codes"}, "col_missing": {"es": "Códigos perdidos", "en": "Missing codes"},
    "col_treatment": {"es": "Tratamiento en el análisis", "en": "Treatment in the analysis"}, "col_role": {"es": "Rol", "en": "Role"},
    "col_source_doc": {"es": "Documento fuente", "en": "Source document"},
    # ST6
    "col_source_file": {"es": "Archivo de microdatos", "en": "Microdata file"}, "col_encoding": {"es": "Codificación", "en": "Encoding"},
    "col_dictionary": {"es": "Diccionario", "en": "Dictionary"}, "col_questionnaire": {"es": "Cuestionario", "en": "Questionnaire"},
    "col_tea_var": {"es": "Variable TEA", "en": "ASD variable"}, "col_tea_wording": {"es": "Redacción del ítem TEA (textual)", "en": "ASD item wording (verbatim Spanish)"},
    "col_tea_codes": {"es": "Códigos TEA observados", "en": "Observed ASD codes"}, "col_filter_var": {"es": "Variable filtro", "en": "Filter variable"},
    "col_filter_wording": {"es": "Redacción del filtro (textual)", "en": "Filter wording (verbatim Spanish)"},
    "col_weight": {"es": "Ponderador", "en": "Weight"}, "col_sex_var": {"es": "Variable sexo", "en": "Sex variable"}, "col_grade_var": {"es": "Variable curso", "en": "Grade variable"},
    "col_other_cats": {"es": "Otras categorías del ítem (n)", "en": "Other item categories (n)"}, "col_estimable": {"es": "Estimabilidad", "en": "Estimability"},
    # La tabla ST6 pasa de dieciséis columnas a diez agrupando las cuatro de archivos y las tres de
    # variables auxiliares: con dieciséis, ni a 6 pt cabía el ancho de las cabeceras y el reparto a
    # prorrata las partía por la mitad («Y ea r», «Weigh t», «Estimabi lity»).
    # Estados del dato del diccionario JUNAEB: el módulo 05 los escribe en español en la tabla tidy y aquí
    # se traducen, porque la tabla se imprime en los dos idiomas.
    "state_missing": {"es": "sin dato", "en": "no data"},
    "state_blank": {"es": "en blanco", "en": "blank"},
    "col_files": {"es": "Archivos (microdatos · codificación · diccionario · cuestionario)",
                  "en": "Files (microdata · encoding · dictionary · questionnaire)"},
    "col_aux_vars": {"es": "Variables auxiliares (ponderador · sexo · curso)",
                     "en": "Auxiliary variables (weight · sex · grade)"},
    "absent": {"es": "ausente", "en": "absent"}, "weight_absent": {"es": "no publicado", "en": "not published"},
    "est_yes": {"es": "estimable (ponderado)", "en": "estimable (weighted)"}, "est_unweighted": {"es": "solo no ponderado (sin ponderador)", "en": "unweighted only (no weight)"},
    "est_no": {"es": "no estimable", "en": "not estimable"},
    "col_value_codes": {"es": "Códigos observados", "en": "Observed codes"}, "col_value_labels": {"es": "Etiquetas de valores", "en": "Value labels"},
    "role_filter": {"es": "filtro: diagnóstico médico prolongado", "en": "filter: prolonged medical diagnosis"}, "role_tea": {"es": "categoría TEA", "en": "ASD category"},
    "role_weight": {"es": "ponderador", "en": "expansion weight"}, "role_sex": {"es": "sexo", "en": "sex"}, "role_grade": {"es": "curso", "en": "grade"},
    "role_other": {"es": "otra categoría del ítem", "en": "other item category"},
    # ST7
    "col_role_artefact": {"es": "Tipo", "en": "Role"}, "col_provider": {"es": "Productor", "en": "Provider"}, "col_size": {"es": "Tamaño (MB)", "en": "Size (MB)"},
    "col_sha": {"es": "SHA-256 (12 primeros)", "en": "SHA-256 (first 12)"}, "col_date": {"es": "Fecha de descarga/versión", "en": "Download/version date"},
    "col_unit": {"es": "Unidad de observación", "en": "Observation unit"}, "col_period": {"es": "Período", "en": "Period"},
    "col_stock_flow": {"es": "Stock / flujo", "en": "Stock / flow"}, "col_breaks": {"es": "Quiebres de definición", "en": "Definition breaks"},
    "col_linkage": {"es": "Restricciones de enlace", "en": "Linkage restrictions"}, "col_use_rule": {"es": "Regla de uso", "en": "Use rule"},
    "col_manifest_sha": {"es": "SHA-256 coincide con manifiesto", "en": "SHA-256 matches manifest"},
    "col_manifest": {"es": "Manifiesto", "en": "Manifest"}, "col_manifest_sha12": {"es": "SHA-256 del manifiesto (12)", "en": "Manifest SHA-256 (12)"},
    "col_observed_sha12": {"es": "SHA-256 observado (12)", "en": "Observed SHA-256 (12)"}, "col_sha_match": {"es": "SHA coincide", "en": "SHA match"},
    "col_manifest_bytes": {"es": "Bytes según manifiesto", "en": "Manifest bytes"}, "col_observed_bytes": {"es": "Bytes observados", "en": "Observed bytes"},
    "col_bytes_match": {"es": "Bytes coinciden", "en": "Bytes match"}, "col_manifest_date": {"es": "Fecha del manifiesto", "en": "Manifest date"},
    "col_manifest_note": {"es": "Nota del manifiesto", "en": "Manifest note"}, "no_size": {"es": "sin tamaño en manifiesto", "en": "no size in manifest"},
    "role_data": {"es": "datos", "en": "data"}, "role_dictionary": {"es": "diccionario", "en": "dictionary"}, "role_context": {"es": "contexto", "en": "context"},
    "role_documentation": {"es": "documentación", "en": "documentation"}, "role_codemap": {"es": "mapa de códigos", "en": "code map"},
    # ST8
    "col_id_column": {"es": "Columna identificadora", "en": "Identifier column"}, "col_f84_episodes": {"es": "Episodios con F84", "en": "Episodes with F84"},
    "col_valid_id": {"es": "Con identificador válido", "en": "With valid identifier"}, "col_invalid_id": {"es": "Sin identificador válido (valores)", "en": "Without valid identifier (values)"},
    "col_unique_ids": {"es": "Identificadores únicos (personas dentro del año)", "en": "Unique identifiers (persons within the year)"},
    "col_id_length": {"es": "Longitud del identificador: moda (mín–máx)", "en": "Identifier length: mode (min–max)"},
    "col_shared_prev": {"es": "Identificadores F84 compartidos con el año anterior (informativo)", "en": "F84 identifiers shared with the previous year (informative)"},
    "col_f84_comuna": {"es": "Episodios F84 con comuna informada", "en": "F84 episodes with reported comuna"},
    "col_records_total": {"es": "Episodios GRD totales", "en": "Total GRD episodes"}, "col_records_valid": {"es": "Episodios GRD con identificador válido", "en": "GRD episodes with valid identifier"},
    "col_exact_dup": {"es": "Filas F84 duplicadas exactas (no eliminadas)", "en": "Exact duplicate F84 rows (not removed)"},
    "strict_f840": {"es": "Solo F84.0 (autismo infantil; idéntica en ambas variantes)", "en": "F84.0 only (childhood autism; identical in both variants)"},
    "first_year": {"es": "primer año", "en": "first year"},
    # ST9
    "col_position": {"es": "Posición del código F84", "en": "F84 code position"}, "pos_any": {"es": "Cualquier posición", "en": "Any position"},
    "pos_principal": {"es": "Diagnóstico principal", "en": "Principal diagnosis"}, "pos_secondary": {"es": "Posición secundaria (2–35)", "en": "Secondary position (2–35)"},
    "sex_m": {"es": "Hombres", "en": "Males"}, "sex_f": {"es": "Mujeres", "en": "Females"}, "sex_unknown": {"es": "Desconocido", "en": "Unknown"},
    "total": {"es": "Total", "en": "Total"}, "age_unknown": {"es": "Desconocida", "en": "Unknown"},
    # ST10
    "col_subcode": {"es": "Subcódigo CIE-10", "en": "ICD-10 subcode"}, "col_in_variant": {"es": "En el conjunto de códigos de la variante", "en": "In the variant's code set"},
    "excluded": {"es": "No (excluido)", "en": "No (excluded)"},
    # ST11
    "col_layout_deis": {"es": "Presentación del archivo", "en": "File layout"}, "layout_canonical": {"es": "canónico", "en": "canonical"},
    "layout_15col": {"es": "variante de 15 columnas (edad quinquenal, sin enmascarar)", "en": "15-column variant (five-year ages, unmasked)"},
    "col_discharges": {"es": "Egresos DEIS (todos los establecimientos)", "en": "DEIS discharges (all establishments)"},
    "col_snss": {"es": "Egresos SNSS", "en": "SNSS discharges"}, "col_no_snss": {"es": "Egresos no SNSS", "en": "Non-SNSS discharges"},
    "col_suppressed": {"es": "Egresos con pertenencia enmascarada", "en": "Discharges with masked affiliation"},
    "col_masked_share": {"es": "Filas enmascaradas (%)", "en": "Masked rows (%)"},
    "col_f84_diag1": {"es": "F84 en DIAG1 (principal)", "en": "F84 in DIAG1 (principal)"}, "col_f84_diag2": {"es": "F84 en DIAG2 (causa externa)", "en": "F84 in DIAG2 (external cause)"},
    "col_f84_any_deis": {"es": "F84 en cualquiera de las dos posiciones", "en": "F84 in either position"},
    "col_f842_diag1_incl": {"es": "de los cuales F84.2 (Rett) en DIAG1 (incluidos)", "en": "of which F84.2 (Rett) in DIAG1 (included)"},
    "col_f842_diag1_excl": {"es": "F84.2 (Rett) en DIAG1 (excluidos de esta variante)", "en": "F84.2 (Rett) in DIAG1 (excluded from this variant)"},
    "col_f84_deaths": {"es": "Egresos F84 fallecidos", "en": "F84 discharges with death"},
    "col_rate_deis": {"es": "F84 principal por 100.000 egresos (IC 95 % exacto)", "en": "Principal F84 per 100,000 discharges (exact 95% CI)"},
    "col_f84_snss": {"es": "F84 en SNSS", "en": "F84 in SNSS"}, "col_f84_no_snss": {"es": "F84 no SNSS", "en": "F84 non-SNSS"}, "col_f84_supp": {"es": "F84 con pertenencia enmascarada", "en": "F84 with masked affiliation"},
    "col_age_scheme": {"es": "Esquema de edad", "en": "Age scheme"}, "age_decadal": {"es": "decenal", "en": "decadal"}, "age_five_year": {"es": "quinquenal", "en": "five-year"},
    "col_n_columns": {"es": "Columnas del archivo", "en": "Columns in file"},
    "col_deis_f84p": {"es": "DEIS F84 principal (todos)", "en": "DEIS principal F84 (all)"}, "col_deis_f84p_snss": {"es": "DEIS F84 principal SNSS", "en": "DEIS principal F84 SNSS"},
    "col_deis_f84p_nosnss": {"es": "DEIS F84 principal no SNSS", "en": "DEIS principal F84 non-SNSS"}, "col_deis_f84p_supp": {"es": "DEIS F84 principal enmascarado", "en": "DEIS principal F84 masked"},
    "col_grd_episodes": {"es": "Episodios GRD (panel observado)", "en": "GRD episodes (observed panel)"}, "col_grd_hospitals": {"es": "Hospitales GRD", "en": "GRD hospitals"},
    "col_grd_f84p": {"es": "GRD F84 principal", "en": "GRD principal F84"}, "col_grd_rate_p": {"es": "GRD F84 principal por 100.000 episodios", "en": "GRD principal F84 per 100,000 episodes"},
    "col_grd_f84any": {"es": "GRD F84 cualquier posición (sin equivalente DEIS)", "en": "GRD F84 any position (no DEIS equivalent)"},
    "col_grd_f84sec": {"es": "GRD F84 solo secundario", "en": "GRD F84 secondary only"},
    "col_grd_hosp_f84p": {"es": "GRD F84 principal, hospitalización estricta", "en": "GRD principal F84, strict hospitalisation"},
    "col_grd_fixed_f84p": {"es": "GRD F84 principal, panel fijo de 65", "en": "GRD principal F84, fixed panel of 65"},
    "col_ratio_total": {"es": "Cociente egresos DEIS / episodios GRD", "en": "Ratio DEIS discharges / GRD episodes"},
    "col_ratio_p": {"es": "Cociente F84 principal DEIS / GRD", "en": "Ratio principal F84 DEIS / GRD"},
    "col_ratio_p_snss": {"es": "Cociente F84 principal DEIS SNSS / GRD", "en": "Ratio principal F84 DEIS SNSS / GRD"},
    "col_ratio_p_snss_hosp": {"es": "Cociente F84 principal DEIS SNSS / GRD hospitalización estricta", "en": "Ratio principal F84 DEIS SNSS / GRD strict hospitalisation"},
    # ST12
    "col_archive": {"es": "Archivo comprimido", "en": "Archive"}, "col_member": {"es": "Archivo miembro", "en": "Member file"},
    "col_rows_raw": {"es": "Filas crudas", "en": "Raw rows"}, "col_dup_kept": {"es": "Filas duplicadas exactas conservadas (aditivas)", "en": "Exact duplicate rows kept (additive)"},
    "col_count_col": {"es": "Columna de conteo", "en": "Count column"}, "col_tramo_col": {"es": "Columna de tramo", "en": "Tramo column"}, "col_region_col": {"es": "Columna de región", "en": "Region column"},
    "col_has_aps": {"es": "Tiene INSCRITO_APS", "en": "Has INSCRITO_APS"}, "col_has_tipo": {"es": "Tiene TIPO_ASEGURADO", "en": "Has TIPO_ASEGURADO"},
    "col_has_dz": {"es": "Tiene DIRECCION_ZONAL", "en": "Has DIRECCION_ZONAL"}, "col_has_ss": {"es": "Tiene SERVICIO_SALUD", "en": "Has SERVICIO_SALUD"},
    "col_age_scheme_f": {"es": "Esquema de tramos de edad", "en": "Age-band scheme"},
    "col_5y": {"es": "Tramos quinquenales derivables (% de beneficiarios con tramo quinquenal)", "en": "Five-year bands derivable (% of beneficiaries with a five-year band)"},
    "fiveyear_yes": {"es": "Sí ({p})", "en": "Yes ({p})"}, "fiveyear_no": {"es": "No, solo decenales ({p})", "en": "No, 10-year bands only ({p})"},
    "no_date": {"es": "sin fecha", "en": "no date"},
    "col_total_benef": {"es": "Beneficiarios totales (diciembre)", "en": "Total beneficiaries (December)"}, "col_columns": {"es": "Columnas del archivo", "en": "File columns"},
    "col_agg_rule": {"es": "Regla de agregación", "en": "Aggregation rule"},
    "col_cotizantes": {"es": "Cotizantes", "en": "Contributors (cotizantes)"}, "col_cargas": {"es": "Cargas", "en": "Dependants (cargas)"},
    "col_nonatos": {"es": "Nonatos / sin clasificar", "en": "Unborn / unclassified"}, "col_benef_total": {"es": "Beneficiarios totales", "en": "Total beneficiaries"},
    "col_benef_f": {"es": "Mujeres", "en": "Female"}, "col_benef_m": {"es": "Hombres", "en": "Male"}, "col_sex_ni": {"es": "Sexo no informado", "en": "Sex not informed"},
    "col_age_ni": {"es": "Edad no informada", "en": "Age not informed"}, "col_cells": {"es": "Celdas (comuna × sexo × edad)", "en": "Cells (comuna × sex × age)"},
    "col_zero_cells": {"es": "Celdas todo cero omitidas", "en": "All-zero cells omitted"}, "col_rule": {"es": "Regla de lectura", "en": "Reading rule"}, "col_age_note": {"es": "Nota de edad", "en": "Age note"},
    "col_centres_total": {"es": "Centros APS (n)", "en": "APS centres (n)"}, "col_centres_panel": {"es": "Centros del panel continuo (n)", "en": "Continuous-panel centres (n)"},
    "col_enrolled_total": {"es": "Inscritos (diciembre)", "en": "Enrolled (December)"}, "col_enrolled_panel": {"es": "Inscritos en el panel de 1.871 centros", "en": "Enrolled in the 1,871-centre panel"},
    "col_retention": {"es": "Retención del panel (%)", "en": "Panel retention (%)"}, "col_tramo_ad": {"es": "Inscritos tramo A–D", "en": "Enrolled, tramo A–D"},
    "col_tramo_x": {"es": "Inscritos tramo X", "en": "Enrolled, tramo X"}, "col_tramo_missing": {"es": "Inscritos sin tramo", "en": "Enrolled, tramo missing"},
    # ST13
    "st13_block_broad": {"es": "TGD amplio 2019–2020 (06902600; sensibilidad, contiene Rett de forma inseparable)", "en": "Broad PDD 2019–2020 (06902600; sensitivity, Rett inseparable)"},
    "st13_block_family": {"es": "Familia TGD de la variante 2021–2025 ({codes})", "en": "PDD family of the variant 2021–2025 ({codes})"},
    "st13_block_strict": {"es": "Autismo estricto 2021–2025 (05990022; idéntico en ambas variantes)", "en": "Strict autism 2021–2025 (05990022; identical in both variants)"},
    "st13_reporting": {"es": "Establecimientos reportantes (n)", "en": "Reporting establishments (n)"},
    "st13_total_row": {"es": "Total informado (COL02/COL03)", "en": "Reported total (COL02/COL03)"},
    "st13_sum_row": {"es": "Suma de celdas de edad", "en": "Sum of age cells"},
    "st13_col01_row": {"es": "Total COL01 (serie principal de la ruta REM)", "en": "Total COL01 (main series of the REM pathway)"},
    # ST14
    "col_dec_stock": {"es": "Stock de diciembre", "en": "December stock"}, "col_dec_estab": {"es": "Establecimientos reportantes en diciembre", "en": "Establishments reporting in December"},
    "col_stable_n": {"es": "Panel estable de diciembre: establecimientos (n)", "en": "December stable panel: establishments (n)"},
    "col_stable_stock": {"es": "Panel estable de diciembre: stock", "en": "December stable panel: stock"},
    "col_jun_stock": {"es": "Stock de junio (sensibilidad)", "en": "June stock (sensitivity)"}, "col_jun_estab": {"es": "Establecimientos reportantes en junio", "en": "Establishments reporting in June"},
    "col_jun_pct": {"es": "Junio como % de diciembre", "en": "June as % of December"},
    "p6_family_primary": {"es": "P6 APS: familia TGD de la variante", "en": "P6 primary care: PDD family of the variant"},
    "p6_family_specialty": {"es": "P6 especialidad: familia TGD de la variante", "en": "P6 specialty care: PDD family of the variant"},
    "p6_strict_primary": {"es": "P6 APS: autismo estricto", "en": "P6 primary care: strict autism"},
    "p6_strict_specialty": {"es": "P6 especialidad: autismo estricto", "en": "P6 specialty care: strict autism"},
}

CODE_LABELS = {
    "03500404": {"es": "Niños/as con control de salud a los 18 meses", "en": "Children with the 18-month health check"},
    "03500405": {"es": "Alteración del lenguaje o del área social en el control de 18 meses", "en": "Language or social-area alteration at the 18-month check"},
    "03500406": {"es": "M-CHAT aplicado en niños/as con alteración del lenguaje o área social", "en": "M-CHAT performed among children with language/social alteration"},
    "03500407": {"es": "M-CHAT alterado en niños/as con alteración del lenguaje o área social", "en": "Altered M-CHAT among children with language/social alteration"},
    "09600212": {"es": "Sospecha de autismo en otros controles o consultas", "en": "Suspected autism in other checks or consultations"},
    "09600213": {"es": "M-CHAT-R/F primera parte: riesgo bajo", "en": "M-CHAT-R/F first part: low risk"},
    "09600214": {"es": "M-CHAT-R/F primera parte: riesgo medio", "en": "M-CHAT-R/F first part: medium risk"},
    "09600215": {"es": "M-CHAT-R/F primera parte: riesgo alto", "en": "M-CHAT-R/F first part: high risk"},
    "09600216": {"es": "M-CHAT-R/F riesgo alto con derivación a especialista", "en": "M-CHAT-R/F high risk with specialist referral"},
    "09600217": {"es": "M-CHAT-R/F segunda parte: riesgo medio en la primera parte", "en": "M-CHAT-R/F second part: medium risk in first part"},
    "09600218": {"es": "M-CHAT-R/F segunda parte: no requiere derivación", "en": "M-CHAT-R/F second part: no referral required"},
    "09600219": {"es": "M-CHAT-R/F segunda parte: requiere derivación", "en": "M-CHAT-R/F second part: referral required"},
    "03700104": {"es": "Niños/as de 31–59 meses evaluados en control de salud integral", "en": "Children aged 31–59 months evaluated at the integral health check"},
    "03700105": {"es": "Niños/as de 31–59 meses con sospecha en otra instancia", "en": "Children aged 31–59 months suspected elsewhere"},
    "03700106": {"es": "Sospecha de autismo por pauta de señales de alerta: sí", "en": "Autism suspicion by alert-sign guide: yes"},
    "03700107": {"es": "Sospecha de autismo por pauta de señales de alerta: no", "en": "Autism suspicion by alert-sign guide: no"},
    "03700108": {"es": "Derivación tras evaluación de señales de alerta: sí", "en": "Referral after alert-sign evaluation: yes"},
    "03700109": {"es": "Derivación tras evaluación de señales de alerta: no", "en": "Referral after alert-sign evaluation: no"},
    "03710013": {"es": "Motivo de M-CHAT: EEDP alterado en lenguaje/área social (16–30 meses)", "en": "M-CHAT motive: altered EEDP language/social area (16–30 months)"},
    "03710014": {"es": "Motivo de M-CHAT: factor de riesgo o señal de alerta de autismo (16–30 meses)", "en": "M-CHAT motive: autism risk factor or alert sign (16–30 months)"},
    "03710015": {"es": "Motivo de M-CHAT: EEDP alterado y riesgo/alerta de autismo (16–30 meses)", "en": "M-CHAT motive: both altered EEDP and autism risk/alert (16–30 months)"},
    "03710016": {"es": "Resultado M-CHAT-R/F: riesgo bajo", "en": "M-CHAT-R/F result: low risk"},
    "03710017": {"es": "M-CHAT-R/F riesgo medio: sin derivación diagnóstica", "en": "M-CHAT-R/F medium risk: no diagnostic referral required"},
    "03710018": {"es": "M-CHAT-R/F riesgo medio: con derivación diagnóstica", "en": "M-CHAT-R/F medium risk: diagnostic referral required"},
    "03710019": {"es": "M-CHAT-R/F riesgo alto: con derivación diagnóstica", "en": "M-CHAT-R/F high risk: diagnostic referral required"},
    "03710020": {"es": "Sospecha de autismo 30–59 meses: sin derivación diagnóstica", "en": "Suspected autism aged 30–59 months: no diagnostic referral required"},
    "03710021": {"es": "Sospecha de autismo 30–59 meses: con derivación diagnóstica", "en": "Suspected autism aged 30–59 months: diagnostic referral required"},
    "06902600": {"es": "Ingreso a programa de salud mental: TGD amplio (2019–2020)", "en": "Entry to mental-health programme: broad PDD (2019–2020)"},
    "05225000": {"es": "Egreso clínico: TGD amplio (2019–2020)", "en": "Clinical discharge: broad PDD (2019–2020)"},
    "05990022": {"es": "Ingreso: autismo", "en": "Entry: autism"},
    "05990023": {"es": "Ingreso: síndrome de Asperger", "en": "Entry: Asperger syndrome"},
    "05990024": {"es": "Ingreso: síndrome de Rett", "en": "Entry: Rett syndrome"},
    "05990025": {"es": "Ingreso: trastorno desintegrativo infantil", "en": "Entry: childhood disintegrative disorder"},
    "05990026": {"es": "Ingreso: TGD no especificado", "en": "Entry: pervasive developmental disorder, unspecified"},
    "05990027": {"es": "Egreso clínico: autismo", "en": "Clinical discharge: autism"},
    "05990028": {"es": "Egreso clínico: síndrome de Asperger", "en": "Clinical discharge: Asperger syndrome"},
    "05990029": {"es": "Egreso clínico: síndrome de Rett", "en": "Clinical discharge: Rett syndrome"},
    "05990030": {"es": "Egreso clínico: trastorno desintegrativo infantil", "en": "Clinical discharge: childhood disintegrative disorder"},
    "05990031": {"es": "Egreso clínico: TGD no especificado", "en": "Clinical discharge: pervasive developmental disorder, unspecified"},
    "29101566": {"es": "Consejería en contexto de tamizaje: nº de M-CHAT-R/F", "en": "Counselling in the screening context: number of M-CHAT-R/F"},
    "29101574": {"es": "Referencia asistida en contexto de tamizaje: nº de M-CHAT-R/F", "en": "Assisted referral in the screening context: number of M-CHAT-R/F"},
    "29101629": {"es": "Ingreso a rehabilitación de nivel primario por condición de salud: autismo", "en": "Entry to primary-level rehabilitation by health condition: autism"},
    "29101651": {"es": "Ingreso a rehabilitación hospitalaria por condición de salud: autismo", "en": "Entry to hospital-level rehabilitation by health condition: autism"},
    "P2500500": {"es": "Población NANEAS bajo control: trastorno del espectro autista", "en": "NANEAS population under control: autism spectrum disorder"},
    "P2501878": {"es": "Población NANEAS bajo control: total (desde diciembre de 2023)", "en": "NANEAS population under control: total (from December 2023)"},
    "P6223000": {"es": "TGD amplio bajo control en APS (2019–2020)", "en": "Broad PDD under control in primary care (2019–2020)"},
    "P6223380": {"es": "TGD amplio bajo control en especialidad (2019–2020)", "en": "Broad PDD under control in specialty care (2019–2020)"},
    "P6241010": {"es": "Autismo bajo control en APS", "en": "Autism under control in primary care"},
    "P6241020": {"es": "Síndrome de Asperger bajo control en APS", "en": "Asperger syndrome under control in primary care"},
    "P6241030": {"es": "Síndrome de Rett bajo control en APS", "en": "Rett syndrome under control in primary care"},
    "P6241040": {"es": "Trastorno desintegrativo infantil bajo control en APS", "en": "Childhood disintegrative disorder under control in primary care"},
    "P6241050": {"es": "TGD no especificado bajo control en APS", "en": "PDD unspecified under control in primary care"},
    "P6241060": {"es": "Autismo bajo control en especialidad", "en": "Autism under control in specialty care"},
    "P6241070": {"es": "Síndrome de Asperger bajo control en especialidad", "en": "Asperger syndrome under control in specialty care"},
    "P6241080": {"es": "Síndrome de Rett bajo control en especialidad", "en": "Rett syndrome under control in specialty care"},
    "P6241090": {"es": "Trastorno desintegrativo infantil bajo control en especialidad", "en": "Childhood disintegrative disorder under control in specialty care"},
    "P6241100": {"es": "TGD no especificado bajo control en especialidad", "en": "PDD unspecified under control in specialty care"},
}

SUBCODE_LABELS = {
    "F84": {"es": "F84 (sin cuarto carácter)", "en": "F84 (no fourth character)"},
    "F840": {"es": "F84.0 Autismo infantil", "en": "F84.0 Childhood autism"}, "F841": {"es": "F84.1 Autismo atípico", "en": "F84.1 Atypical autism"},
    "F842": {"es": "F84.2 Síndrome de Rett", "en": "F84.2 Rett syndrome"},
    "F843": {"es": "F84.3 Otro trastorno desintegrativo de la infancia", "en": "F84.3 Other childhood disintegrative disorder"},
    "F844": {"es": "F84.4 Trastorno hiperactivo con retraso mental y movimientos estereotipados", "en": "F84.4 Overactive disorder with mental retardation and stereotyped movements"},
    "F845": {"es": "F84.5 Síndrome de Asperger", "en": "F84.5 Asperger syndrome"},
    "F848": {"es": "F84.8 Otros trastornos generalizados del desarrollo", "en": "F84.8 Other pervasive developmental disorders"},
    "F849": {"es": "F84.9 Trastorno generalizado del desarrollo no especificado", "en": "F84.9 Pervasive developmental disorder, unspecified"},
}

# La glosa de stock/flujo vive ahora en labels.PROVENANCE_TEXT, junto con el resto de los campos
# descriptivos de data_provenance.csv, para que una sola tabla los declare todos.
ROLE_ARTEFACT = {"data": "role_data", "dictionary": "role_dictionary", "context": "role_context", "documentation": "role_documentation", "code map": "role_codemap"}
DATE_ES = [("(SOURCES_MANIFEST.md consolidation date)", "(fecha de consolidación de SOURCES_MANIFEST.md)"), ("; file mtime ", "; mtime del archivo "),
           ("(file mtime; not dated in any manifest)", "(mtime del archivo; sin fecha en ningún manifiesto)")]
SURVEY_MODULE_EN = {"Adultos (18+)": "Adults (18+)", "NNA (2-17)": "Children and adolescents (2–17)", "Diseño": "Design", "Personas 15+ (módulo 4)": "Persons aged 15+ (module 4)"}
SURVEY_ROLE_EN = {"ítem principal adultos": "main item, adults", "ítem principal NNA": "main item, children/adolescents", "confirmación profesional NNA": "professional confirmation, children/adolescents",
                  "tratamiento NNA": "treatment, children/adolescents", "nota": "note", "ponderador": "weight", "estrato": "stratum", "conglomerado": "cluster (PSU)",
                  "desagregación": "disaggregation", "ítem principal ENCAVI": "main item, ENCAVI", "tratamiento ENCAVI": "treatment, ENCAVI"}
# Traducciones por variable de los campos analíticos del diccionario de encuestas (respondent, universe, codes, missing, treatment).
SURVEY_EN = {
    "c26_33": ("Selected person aged 18+ (self, assisted or by proxy according to forma_ent_adulto_inicio)", "Selected persons aged 18 years or more (n = 30,010)", "0 No; 1 Yes",
               "none (no missing codes; NaN = outside the universe)", "Numerator = 1; domain = adults with a non-missing item"),
    "n29_19": ("Main caregiver of the child/adolescent (mother 77%, rp2)", "Selected persons aged 2 to 17 years (n = 5,526)", "0 No; 1 Yes", "none (NaN = outside the universe)",
               "Numerator = 1; domain = children/adolescents with a non-missing item"),
    "n29a_19": ("Main caregiver of the child/adolescent", "Children/adolescents with reported autism (n29_19 = 1; n = 163)", "1 Yes; 2 No", "-99 No answer (10 cases); NaN = not applicable (n29_19 ≠ 1)",
                "Primary: domain = valid answers (153); sensitivity: -99 counted as not confirmed (163); also as a proportion of all children/adolescents"),
    "n29b_19": ("Main caregiver of the child/adolescent", "Children/adolescents with reported autism (n = 163)", "1 Yes; 2 No", "-99 No answer (10); NaN = not applicable", "Secondary; domain = valid answers"),
    "n29c_19": ("Main caregiver of the child/adolescent", "Children/adolescents with reported autism (n = 163)", "1 Yes; 2 No", "-99 No answer (10); NaN = not applicable", "Secondary; domain = valid answers"),
    "(no existe)": ("—", "—", "—", "—", "Not estimable: professional confirmation is not reported for adults"),
    "fexp": ("—", "Selected persons (n = 35,536); range 24–15,246; sum 19,348,925", "numeric", "NaN for roster persons not selected",
             "Weight (pw) in all estimates; product of first-phase (Casen en Pandemia 2020 pre-contact) and second-phase factors, adjusted for ineligibility and non-response and calibrated/smoothed"),
    "estrato": ("—", "Selected persons; 32 values = region × zone (urban/rural)", "1–32", "none",
                "Variance stratum. The methodological document describes 96 explicit second-phase strata (age band × region × zone) not published as a variable; the 32 published pseudo-strata are used"),
    "cod_upm": ("—", "Selected persons; 8,477 PSUs (blocks/sections of the Casen en Pandemia 2020 frame); minimum 8 PSUs per stratum", "identifier", "none",
                "Variance cluster (ultimate-cluster with-replacement approximation); captures correlation among persons of the same dwelling/PSU"),
    "sexo / edad": ("Household informant", "Roster", "sex 1 Male 2 Female; age 0–106 (selected 2–104)", "none", "Domains by sex; age groups 18-29/30-44/45-59/60+ (adults) and 2-5/6-11/12-17 (children/adolescents)"),
    "p4_6_1_h": ("Selected person aged 15+ (CAPI personal interview)", "All persons in the dataset (n = 16,590)", "1 Yes; 2 No", "8 Don't know (101); 9 No answer (5) — not read aloud",
                 "Primary: domain = valid answers (16,484); sensitivity: 8/9 counted as not diagnosed (16,590)"),
    "p4_6_2_h": ("Selected person aged 15+", "Persons with p4_6_1_h = 1 (n = 80)", "1 Yes; 2 No", "8 Don't know; 9 No answer (1); NaN = not applicable", "Secondary; domain = valid answers (79)"),
    "w_personas_cal": ("—", "All persons (n = 16,590); range 13.1–7,672.2; sum 16,238,022 (population aged 15+, Census 2017)", "numeric", "none", "Weight (pw)"),
    "varstrat": ("—", "96 pseudo-strata; minimum 2 PSUs per stratum (no singleton units)", "identifier", "none", "Variance stratum (svyset varunit [pw = w_personas_cal], strata(varstrat) singleunit(certainty))"),
    "varunit": ("—", "350 pseudo-clusters", "identifier", "none", "Variance cluster (ultimate cluster with replacement)"),
    "sexo / edad / edad5": ("—", "All persons", "sex 1 Male 2 Female; edad5 1 15-19, 2 20-29, 3 30-49, 4 50-64, 5 65+", "none", "Domains by sex and edad5 age band"),
}
JUNAEB_ROLE = {"filter_prolonged_medical_diagnosis": "role_filter", "tea_category": "role_tea", "expansion_weight": "role_weight", "sex": "role_sex", "grade": "role_grade", "other_category": "role_other"}
# La regla de agregación, la nota de edad y el esquema de tramos de FONASA, APS e ISAPRE los declara
# labels.TIDY_TEXT en los dos idiomas (los mismos valores que imprime el módulo 16): aquí se leen
# con labels.tidy_text para que las dos tablas digan exactamente lo mismo.


def T(key: str, lang: str, **fmt) -> str:
    s = TXT[key][lang]
    return s.format(**fmt) if fmt else s


def code_label(code: str, lang: str) -> str:
    return CODE_LABELS.get(code, {}).get(lang, code)


def variant_label(variant: str, lang: str) -> str:
    return CFG.VARIANTS[variant]["label"][lang]


def rd(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(CFG.TIDY / f"{name}.csv", dtype=str, keep_default_na=False, **kw)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace("", np.nan), errors="coerce")


def fi(x, lang: str) -> str:
    return DASH if x is None or pd.isna(x) else C.fmt_number(float(x), 0, lang)


def fd(x, dec: int, lang: str) -> str:
    return DASH if x is None or pd.isna(x) else C.fmt_number(float(x), dec, lang)


def fpct(x, dec: int, lang: str) -> str:
    if x is None or pd.isna(x):
        return DASH
    return f"{C.fmt_number(float(x), dec, lang)} %" if lang == "es" else f"{C.fmt_number(float(x), dec, lang)}%"


def yn(flag, lang: str) -> str:
    if isinstance(flag, str):
        flag = flag.strip().lower() == "true"
    return T("yes", lang) if bool(flag) else T("no", lang)


# ---------------------------------------------------------------------------
# Ventana de años dentro del texto de una celda
# ---------------------------------------------------------------------------
#: La ventana de años se escribe con RAYA cuando se IMPRIME —«2019–2025»— y con guion ASCII cuando es
#: forma de MÁQUINA; la conversión única del estudio es `common.yspan` (ver el comentario de esa función).
#: Las tablas de este módulo la traían con guion dentro de las FRASES: los campos descriptivos de la
#: procedencia (Tabla ST7: «Questionnaires exist for 2019-2025», «A05: broad PDD only in 2019-2020»), las
#: reglas de agregación de ISAPRE (ST12b) y el nombre de la encuesta (ST5: «ENCAVI 2023-2024»). En la misma
#: página el lector veía «2019-2025» en la nota y «29,7–41,9» en un intervalo: dos trazos para un rango.
#:
#: `yspan_prose` aplica `common.yspan` PALABRA A PALABRA y salta ENTERA la palabra que lleve una marca de
#: MÁQUINA —«:» «_» «=» «|» «[» «]» «%» «\», una extensión de archivo, o «/» acompañado de letras—. Con esa
#: sola regla, y sin lista de columnas que envejezca, quedan literales los nombres de archivo y las rutas
#: (`GRD/metadata/SOURCES_MANIFEST.md`, `ine_estimaciones-y-proyecciones-2002-2035_base-2017_comunas….csv`)
#: y las URL del manifiesto (Tabla ST7b: `source_url=https://…-1992-2070_base-2024_base-de-datos.xlsx?…`),
#: que son la trazabilidad de la fuente y se cruzan carácter a carácter con los manifiestos.
#: COLUMNAS QUE NO SE RETIPOGRAFÍAN porque son TRANSCRIPCIÓN LITERAL de un diccionario o cuestionario
#: chileno. No se listan a mano: son aquellas cuyo PROPIO encabezado declara la transcripción —«(textual)»
#: en español, «verbatim» en inglés—, que es el mismo criterio con el que `tests/test_language_purity.py`
#: exime a una columna de la prueba de idioma. A ellas se suman las cuatro columnas de CÓDIGOS OBSERVADOS
#: y ETIQUETAS DE VALOR, que son el valor del dato tal como lo publica la fuente aunque su encabezado no
#: lleve la palabra. Si mañana una de esas transcripciones trajera «2019-2020» dentro, se imprime como
#: viene: retocarla rompería la cita.
_VERBATIM_EXTRA = ("col_codes_resp", "col_missing", "col_tea_codes", "col_value_codes", "col_value_labels")
VERBATIM_KEYS = tuple(sorted({k for k, v in TXT.items()
                              if "(textual)" in v["es"].lower() or "verbatim" in v["en"].lower()}
                             | set(_VERBATIM_EXTRA)))


def verbatim_headers(lang: str) -> frozenset:
    return frozenset(TXT[k][lang] for k in VERBATIM_KEYS)


#: FASE 4J, TAREA J2. Este módulo tenía aquí su propia copia de la regla y sólo sabía convertir la VENTANA
#: DE AÑOS: la banda de edad quinquenal de la ST9 y de la ST13 («0-4» … «75-79», 704 celdas) salía con
#: guion en la misma página en la que el intervalo de confianza salía con raya. La regla es ahora UNA para
#: todo el corpus y vive en `common` (`C.range_dash`), que trata la ventana de años como un caso más del
#: intervalo numérico. Los tres nombres con los que este módulo la llamaba quedan delegando, y la exención
#: de las columnas de TRANSCRIPCIÓN LITERAL (`VERBATIM_KEYS`) se le pasa como tal.
machine_token = C.is_machine_token
yspan_prose = C.range_dash


def yspan_frame(df: pd.DataFrame, lang: str) -> tuple[pd.DataFrame, int, int]:
    """La regla del intervalo sobre encabezados y celdas del marco IMPRESO (nunca el `_numeric`).

    Devuelve el marco y dos recuentos: intervalos convertidos a raya y guiones entre cifras conservados a
    propósito (clave de máquina, fecha, código, cadena o columna de transcripción literal)."""
    return C.range_dash_frame(df, exempt_headers=verbatim_headers(lang))


#: Recuento de la conversión por variante e idioma, para los controles del módulo.
YSPAN_COUNTS: dict[str, dict[str, int]] = {}


def merge_json(path: Path, new: dict) -> None:
    current = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = {}
    if not isinstance(current, dict):
        current = {}
    current.update(new)
    C.atomic_write_json(current, path)


def title(lang: str, n: str, text: str, variant: str | None = None) -> str:
    s = f"{T('table', lang)} {n}. {text}"
    if variant:
        s += T("variant_suffix", lang, v=variant_label(variant, lang))
    return s


def load_inputs() -> dict:
    return dict(
        fp=rd("grd_fixed_panel_hospitals"), hy=rd("grd_hospital_year"), dc=rd("rem_code_dictionary_check"),
        ey=rd("rem_establishment_year", usecols=["year", "series", "module", "code", "IdEstablecimiento", "months_with_rows", "annual_total", "december_value",
                                                 "june_value", "has_december_row", "has_june_row", "in_stable_panel"]),
        un=rd("comuna_unmatched"), nm=rd("comuna_name_matches"), cw=rd("comuna_crosswalk"), si=rd("survey_items_dictionary"), ji=rd("junaeb_items_dictionary"),
        jt=rd("junaeb_tea_year_level"), dp=rd("data_provenance"), pm=rd("provenance_manifest_checks"), ia=rd("grd_identifier_audit"), ag=rd("grd_age_sex_year"),
        sc=rd("grd_subcode_year"), ds=rd("deis_year_summary"), dv=rd("deis_vs_grd_year"), fs=rd("fonasa_schema_by_year"), isn=rd("isapre_beneficiaries_national_year"),
        ap=rd("aps_panel"), a05=rd("rem_a05_age_sex_annual"), rp=rd("rem_pathway_annual"),
        fb5=fonasa_five_year_share(),
    )


FIVE_YEAR_SHARE_THRESHOLD = 0.99  # solo los tramos «sin información» pueden quedar fuera de un esquema quinquenal derivable


def fonasa_five_year_share() -> pd.DataFrame:
    """Participación de beneficiarios FONASA con tramo quinquenal derivable por año (fonasa_beneficiaries_comuna_year.csv).

    El indicador de módulo 03 (`age_band_5y_derivable`) es True si alguna fila obtiene tramo quinquenal; en 2023 solo el tramo
    «80 y más» lo obtiene (≈3,5 % de los beneficiarios), por lo que aquí se calcula la participación real y se declara derivable
    solo cuando ≥ 99 % de los beneficiarios (todos los tramos informados) se asignan a un tramo quinquenal.
    """
    fb = pd.read_csv(CFG.TIDY / "fonasa_beneficiaries_comuna_year.csv", usecols=["year", "age_band_5y", "age_band_10y", "beneficiaries"],
                     dtype={"age_band_5y": "string", "age_band_10y": "string"})
    fb["beneficiaries"] = pd.to_numeric(fb.beneficiaries, errors="coerce").fillna(0)
    g = fb.groupby("year")
    out = pd.DataFrame({"total": g.beneficiaries.sum(),
                        "with_5y": fb[fb.age_band_5y.notna()].groupby("year").beneficiaries.sum(),
                        "with_10y": fb[fb.age_band_10y.notna()].groupby("year").beneficiaries.sum()}).fillna(0)
    out["share_beneficiaries_with_5y_band"] = out.with_5y / out.total
    out["share_beneficiaries_with_10y_band"] = out.with_10y / out.total
    out["age_band_5y_derivable_all_bands"] = out.share_beneficiaries_with_5y_band >= FIVE_YEAR_SHARE_THRESHOLD
    out.index = out.index.astype(str)
    return out


# ---------------------------------------------------------------------------
# ST1 — hospitales del panel fijo y observado
# ---------------------------------------------------------------------------
def st1(D: dict, variant: str, lang: str):
    fp = D["fp"].copy()
    h = D["hy"][D["hy"].variant == variant].copy()
    intcols = ["n_episodes_total", "n_episodes_hospitalisation", "n_episodes_cma", "n_episodes_other", "n_f84_any", "n_f84_principal", "n_f84_any_hospitalisation",
               "n_f84_any_cma", "persons_within_year_f84_any"]
    for c in intcols:
        h[c] = num(h[c])
    for c in ["coding_depth_mean", "coding_depth_mean_f84"]:
        h[c] = num(h[c])
    h["year"] = h.year.astype(int)
    lookup = {(r.COD_HOSPITAL, r.year): r for r in h.itertuples()}
    fp["_sort"] = np.where(fp.in_fixed_panel == "True", 0, 1)
    fp = fp.sort_values(["_sort", "COD_HOSPITAL"], kind="mergesort")
    ck, ch, cf, cy = T("col_code", lang), T("col_hospital", lang), T("col_fixed_panel", lang), T("col_years_present", lang)
    rows = []
    for r in fp.itertuples():
        row = {ck: r.COD_HOSPITAL, ch: r.hospital_name, cf: yn(r.in_fixed_panel, lang), cy: r.n_years_present}
        for y in YEARS_GRD:
            k = lookup.get((r.COD_HOSPITAL, y))
            row[str(y)] = DASH if k is None else f"{fi(k.n_episodes_total, lang)} ({fi(k.n_f84_any, lang)})"
        rows.append(row)
    obs = h.groupby("year")[["n_episodes_total", "n_f84_any", "n_f84_principal"]].sum()
    n_obs = h.groupby("year").COD_HOSPITAL.nunique()
    fx = h[h.in_fixed_panel == "True"]
    fxs = fx.groupby("year")[["n_episodes_total", "n_f84_any"]].sum()
    n_fx = fx.groupby("year").COD_HOSPITAL.nunique()

    def total_row(label, vals):
        row = {ck: "", ch: label, cf: "", cy: ""}
        row.update({str(y): vals(y) for y in YEARS_GRD})
        return row
    rows.append(total_row(T("st1_total_observed", lang), lambda y: f"{fi(obs.loc[y, 'n_episodes_total'], lang)} ({fi(obs.loc[y, 'n_f84_any'], lang)})"))
    rows.append(total_row(T("st1_total_fixed", lang), lambda y: f"{fi(fxs.loc[y, 'n_episodes_total'], lang)} ({fi(fxs.loc[y, 'n_f84_any'], lang)})"))
    rows.append(total_row(T("st1_f84_principal_obs", lang), lambda y: fi(obs.loc[y, "n_f84_principal"], lang)))
    rows.append(total_row(T("st1_n_observed", lang), lambda y: fi(n_obs.loc[y], lang)))
    rows.append(total_row(T("st1_n_fixed", lang), lambda y: fi(n_fx.loc[y], lang)))
    out = pd.DataFrame(rows)
    numeric = h.sort_values(["year", "COD_HOSPITAL"])[["year", "variant", "COD_HOSPITAL", "hospital_name", "hospital_name_source", "in_fixed_panel"] + intcols +
                                                      ["coding_depth_mean", "coding_depth_mean_f84"]].reset_index(drop=True)
    for c in intcols:
        numeric[c] = numeric[c].astype("Int64")
    n_hosp, n_fixed = len(fp), int((fp.in_fixed_panel == "True").sum())
    obs_txt = "/".join(str(int(n_obs.loc[y])) for y in YEARS_GRD)
    if lang == "es":
        ttl = title(lang, "ST1", f"Hospitales del GRD público 2019–2024: panel fijo de {n_fixed} hospitales y panel anual observado, con episodios GRD y episodios con F84 documentado por año", variant)
        note = (f"Una fila por hospital ({n_hosp} hospitales con episodios en al menos un año). Celda = episodios GRD del hospital-año (entre paréntesis, episodios con F84 documentado en cualquier posición diagnóstica según la variante). "
                f"Panel fijo = {n_fixed} {C.fixed_panel_gloss('es', 'full')}; panel observado = {obs_txt} hospitales. «—» = hospital sin episodios ese año. "
                "Los episodios incluyen hospitalización, cirugía mayor ambulatoria y, en 2019, otras modalidades; F84 principal solo en la fila resumen y en la versión numérica. "
                "Unidad: episodio GRD (una fila del archivo anual, sin eliminar duplicados). " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    else:
        ttl = title(lang, "ST1", f"Public GRD hospitals 2019–2024: fixed panel of {n_fixed} hospitals and observed annual panel, with GRD episodes and episodes with documented F84 by year", variant)
        note = (f"One row per hospital ({n_hosp} hospitals with episodes in at least one year). Cell = GRD episodes of the hospital-year (in brackets, episodes with documented F84 in any diagnosis position according to the variant). "
                f"Fixed panel = {n_fixed} {C.fixed_panel_gloss('en', 'full')}; observed panel = {obs_txt} hospitals. '—' = hospital with no episodes that year. "
                "Episodes include hospitalisation, major ambulatory surgery and, in 2019, other modalities; principal F84 only in the summary row and the numeric version. "
                "Unit: GRD episode (one row of the annual file, duplicates not removed). " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# ST2 — verificación del diccionario de códigos REM
# ---------------------------------------------------------------------------
def st2(D: dict, lang: str):
    dc = D["dc"].copy()
    dc["year"] = dc.year.astype(int)
    order = list(dict.fromkeys(dc.code))
    rows, n_incons = [], 0
    for code in order:
        g = dc[dc.code == code].sort_values("year")
        found = g[g.found_in_dictionary == "True"]
        last = found.iloc[-1] if len(found) else None
        row = {T("col_module", lang): g.sheet.iloc[0], T("col_code", lang): code, T("col_era", lang): g.era.iloc[0], T("col_indicator", lang): code_label(code, lang),
               T("col_dict_label", lang): last.label if last is not None else DASH, T("col_section", lang): last.section if last is not None else DASH,
               T("col_col01", lang): last.col01_meaning if last is not None else DASH, T("col_col02", lang): last.col02_meaning if last is not None else DASH,
               T("col_age_columns", lang): (yn(bool(last.age_columns), lang) if last is not None else DASH),
               T("col_n_tokens", lang): (fi(num(pd.Series([last.n_col_tokens])).iloc[0], lang) if last is not None else DASH),
               T("col_layout", lang): (T("layout_ok", lang) if (last is not None and last.layout_check == "ok") else (last.layout_check if last is not None else DASH)),
               T("col_dict_file", lang): (Path(last.dictionary_file).name if last is not None else DASH)}
        consistent = True
        for y in YEARS_REM:
            r = g[g.year == y]
            if r.empty:
                row[str(y)] = DASH
                continue
            f = r.found_in_dictionary.iloc[0] == "True"
            e = r.in_era.iloc[0] == "True"
            if f and e:
                cell = T("found", lang)
            elif not f and not e:
                cell = DASH
            elif f:
                cell, consistent = T("found_outside_era", lang), False
            else:
                cell, consistent = T("missing_in_era", lang), False
            row[str(y)] = cell
        n_incons += 0 if consistent else 1
        row[T("col_consistency", lang)] = yn(consistent, lang)
        rows.append(row)
    out = pd.DataFrame(rows)
    n_codes, n_rows = len(order), len(dc)
    if lang == "es":
        ttl = title(lang, "ST2", f"Verificación de los {n_codes} códigos REM de la ruta administrativa contra el diccionario oficial de cada año, 2019–2025")
        note = (f"Una fila por código ({n_rows} comprobaciones código-año). Celda anual: «Sí» = el código existe en el diccionario de ese año y el año pertenece a su era de definición; «—» = no existe y no se esperaba; "
                "«Sí (fuera de era)» o «No (falta en era)» marcarían discrepancias (ninguna observada). Rótulo, sección y significado de columnas se transcriben textualmente (en español) del diccionario del último año en que el código se halló; "
                "COL01/COL02 = total ambos sexos o hombres/mujeres según el módulo; las columnas de edad × sexo (COL04–COL37, pares hombres/mujeres) existen solo en A05 y P6. "
                "Eras: A03 legado 2019–2022 (03500406/07 restringidos a niños con alteración de lenguaje/área social), A03 2023–2024 (09600212–219), A03 2024 31–59 meses (03700104–109), A03 2025 rediseño (03710013–021); "
                "A05 TGD amplio 2019–2020 frente a categorías desde 2021; A27 y A28 desde 2023; P2 NANEAS total desde diciembre de 2023; P6 TGD amplio 2019–2020 frente a categorías desde 2021. "
                + T("identical_variants", lang))
    else:
        ttl = title(lang, "ST2", f"Verification of the {n_codes} REM codes of the administrative pathway against the official dictionary of each year, 2019–2025")
        note = (f"One row per code ({n_rows} code-year checks). Yearly cell: 'Yes' = the code exists in that year's dictionary and the year belongs to its definition era; '—' = absent and not expected; "
                "'Yes (outside era)' or 'No (missing in era)' would flag discrepancies (none observed). Label, section and column meanings are transcribed verbatim (Spanish) from the dictionary of the last year in which the code was found; "
                "COL01/COL02 = both-sexes total or males/females depending on the module; age × sex columns (COL04–COL37, male/female pairs) exist only in A05 and P6. "
                "Eras: legacy A03 2019–2022 (03500406/07 restricted to children with language/social alteration), A03 2023–2024 (09600212–219), A03 2024 ages 31–59 months (03700104–109), A03 2025 redesign (03710013–021); "
                "A05 broad PDD 2019–2020 versus categories from 2021; A27 and A28 from 2023; P2 total NANEAS from December 2023; P6 broad PDD 2019–2020 versus categories from 2021. "
                + T("identical_variants", lang))
    return out, None, ttl, note, n_incons


# ---------------------------------------------------------------------------
# ST3 — establecimientos reportantes por módulo, código y año
# ---------------------------------------------------------------------------
def st3_aggregate(D: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    ey = D["ey"].copy()
    ey["year"] = ey.year.astype(int)
    ey["annual_total"] = num(ey.annual_total)
    ey["december_value"] = num(ey.december_value)
    is_p = ey.series == "P"
    ey["positive"] = np.where(is_p, ey.december_value > 0, ey.annual_total > 0)
    agg = ey.groupby(["series", "module", "code", "year"]).agg(
        n_establishments_any_row=("IdEstablecimiento", "nunique"),
        n_stable_panel=("in_stable_panel", lambda s: int((s == "True").sum())),
        n_12_months=("months_with_rows", lambda s: int((s == "12").sum())),
        n_december_row=("has_december_row", lambda s: int((s == "True").sum())),
        n_june_row=("has_june_row", lambda s: int((s == "True").sum())),
        n_value_positive=("positive", "sum")).reset_index()
    mod = ey.groupby(["module", "year"]).IdEstablecimiento.nunique().reset_index().rename(columns={"IdEstablecimiento": "n_establishments_any_row"})
    # cruce con rem_pathway_annual (single_code) para el número de establecimientos reportantes que usan las tablas principales
    rp = D["rp"][(D["rp"].variant == "single_code") & (D["rp"].measure.isin(["annual_sum", "december_stock"]))].copy()
    rp["year"] = rp.year.astype(int)
    rp = rp[["code", "year", "era", "n_reporting_establishments"]].rename(columns={"n_reporting_establishments": "n_reporting_rem_pathway_annual"})
    rp["n_reporting_rem_pathway_annual"] = num(rp.n_reporting_rem_pathway_annual).astype("Int64")
    agg = agg.merge(rp, on=["code", "year"], how="left")
    return agg, mod


def st3(D: dict, agg: pd.DataFrame, mod: pd.DataFrame, lang: str):
    cm, cc, ci, ce, cd = T("col_module", lang), T("col_code", lang), T("col_indicator", lang), T("col_era", lang), T("col_cell_def", lang)
    rows = []
    for module in ["A03", "A27", "A05", "A28", "P2", "P6"]:
        m = mod[mod.module == module].set_index("year").n_establishments_any_row
        row = {cm: module, cc: "", ci: T("st3_module_total", lang), ce: "", cd: T("st3_cell_mod", lang)}
        row.update({str(y): (fi(m.loc[y], lang) if y in m.index else DASH) for y in YEARS_REM})
        rows.append(row)
        sub = agg[agg.module == module]
        for code in list(dict.fromkeys(sub.code)):
            g = sub[sub.code == code].set_index("year")
            is_p = g.series.iloc[0] == "P"
            row = {cm: module, cc: code, ci: code_label(code, lang), ce: g.era.dropna().iloc[0] if g.era.notna().any() else "", cd: T("st3_cell_p" if is_p else "st3_cell_a", lang)}
            for y in YEARS_REM:
                if y not in g.index:
                    row[str(y)] = DASH
                elif is_p:
                    row[str(y)] = f"{fi(g.loc[y, 'n_december_row'], lang)} / {fi(g.loc[y, 'n_june_row'], lang)} ({fi(g.loc[y, 'n_stable_panel'], lang)})"
                else:
                    row[str(y)] = f"{fi(g.loc[y, 'n_establishments_any_row'], lang)} ({fi(g.loc[y, 'n_stable_panel'], lang)})"
            rows.append(row)
    out = pd.DataFrame(rows)
    numeric = agg.sort_values(["series", "module", "code", "year"]).reset_index(drop=True)
    n_codes = agg.code.nunique()
    if lang == "es":
        ttl = title(lang, "ST3", f"Establecimientos que reportan cada código REM por módulo y año, 2019–2025, con el panel estable de establecimientos ({n_codes} códigos)")
        note = ("Serie A (A03, A27, A05, A28; flujos mensuales): celda = establecimientos con al menos un mes reportado para el código en el año (entre paréntesis, establecimientos del panel estable = con filas del código en todos los años de su era). "
                "Serie P (P2, P6; stocks semestrales): celda = establecimientos con fila de diciembre / con fila de junio (entre paréntesis, panel estable definido con diciembre). La fila «todos los códigos del módulo» cuenta establecimientos con alguna fila de cualquier código del módulo. "
                "Una fila REM presente con valor cero o celda vacía cuenta como reportante; la ausencia de fila es «no reportado» y nunca se imputa (P2501878 en junio de 2023: 0 establecimientos con fila, código no reportado ese semestre). «—» = año fuera de la era del código. "
                "Las cifras son cobertura de reporte (lugar de atención), no población cubierta; la versión numérica añade establecimientos con 12 meses, con valor positivo y el N usado en rem_pathway_annual. "
                + T("identical_variants", lang) + " " + T("pandemic_law", lang))
    else:
        ttl = title(lang, "ST3", f"Establishments reporting each REM code by module and year, 2019–2025, with the stable establishment panel ({n_codes} codes)")
        note = ("Series A (A03, A27, A05, A28; monthly flows): cell = establishments with at least one month reported for the code in the year (in brackets, stable-panel establishments = with rows for the code in every year of its era). "
                "Series P (P2, P6; semiannual stocks): cell = establishments with a December row / with a June row (in brackets, stable panel defined on December). The 'all codes of the module' row counts establishments with any row of any code of the module. "
                "A REM row present with a zero value or an empty cell counts as reporting; a missing row is 'not reported' and is never imputed (P2501878 in June 2023: 0 establishments with a row, code not reported that semester). '—' = year outside the code's era. "
                "Figures are reporting coverage (place of care), not covered population; the numeric version adds establishments with 12 months, with a positive value and the N used in rem_pathway_annual. "
                + T("identical_variants", lang) + " " + T("pandemic_law", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# ST4 — crosswalk comunal
# ---------------------------------------------------------------------------
def st4(D: dict, lang: str):
    nm, un, cw = D["nm"].copy(), D["un"].copy(), D["cw"]
    n_cw = len(cw)
    cs, cmeth, cr, cc, cy, cdet = T("col_source", lang), T("col_method", lang), T("col_raw_names", lang), T("col_comunas", lang), T("col_years", lang), T("col_detail", lang)
    rows = []
    for source in ["FONASA", "APS", "ISAPRE"]:
        s = nm[nm.source == source]
        for method in ["exact", "alias"]:
            g = s[s.match_method == method]
            years = sorted({y for ys in g.years for y in ys.split("|") if y})
            detail = "; ".join(f"{r.raw_name} → {r.cut_comuna} ({r.years.replace('|', ', ')})" for r in g.sort_values(["cut_comuna", "raw_name"]).itertuples()) if method == "alias" else ""
            rows.append({cs: source, cmeth: T("method_" + method, lang), cr: fi(g.raw_name.nunique(), lang), cc: fi(g.cut_comuna.nunique(), lang),
                         cy: (f"{years[0]}–{years[-1]}" if years else DASH), cdet: detail})
        years = sorted({y for ys in s.years for y in ys.split("|") if y})
        u = un[un.source == source]
        rows.append({cs: source, cmeth: T("method_all", lang), cr: fi(s.raw_name.nunique(), lang), cc: fi(s.cut_comuna.nunique(), lang), cy: (f"{years[0]}–{years[-1]}" if years else DASH),
                     # Los nombres crudos se glosan con `LB.tidy_text`, igual que en la ST4b: sin ella, la
                     # ST4a española imprimía «(missing)» —el token que escribe el módulo 03 para la celda
                     # sin nombre— en la misma página en que la ST4b lo escribe ya como «(vacío)».
                     cdet: T("st4_unmatched_detail", lang,
                             n=", ".join(sorted(LB.tidy_text(v, lang) for v in u.raw_name.unique())) if len(u) else "0")})
    out_a = pd.DataFrame(rows)
    # ST4b — no enlazados con participación en el total nacional de la fuente
    fs = D["fs"].set_index("year").total_beneficiaries
    isn = D["isn"].set_index("year").beneficiarios_total
    un["count_num"] = num(un["count"])
    un["rows_num"] = num(un["rows"])

    def national(r):
        if r.source == "FONASA" and r.year in fs.index:
            return float(fs.loc[r.year])
        if r.source == "ISAPRE" and r.year in isn.index:
            return float(isn.loc[r.year])
        return np.nan
    un["national_total"] = [national(r) for r in un.itertuples()]
    un["share_pct"] = 100 * un.count_num / un.national_total
    # «DESCONOCIDA», «Sin dato Comuna» y «Sin Código de Comuna» son el valor que trae la fuente y se
    # transcriben; «(missing)» y «MISSING» los escribe el módulo 03 para la celda vacía y por eso se
    # leen en el idioma del documento.
    out_b = pd.DataFrame({T("col_source", lang): un.source, T("col_year", lang): un.year,
                          T("col_raw_name", lang): [LB.tidy_text(v, lang) for v in un.raw_name],
                          T("col_normalised", lang): [LB.tidy_text(v, lang) for v in un.normalised],
                          T("col_rows", lang): [fi(x, lang) for x in un.rows_num], T("col_count", lang): [fi(x, lang) for x in un.count_num],
                          T("col_share", lang): [fpct(x, 2, lang) for x in un.share_pct],
                          T("col_reason", lang): [T("reason_placeholder", lang) if r == "non-geographic placeholder" else r for r in un.reason]})
    numeric_b = un[["source", "year", "raw_name", "normalised", "rows_num", "count_num", "national_total", "share_pct", "reason", "count_unit"]].rename(columns={"rows_num": "rows", "count_num": "count"})
    n_alias = int((nm.match_method == "alias").sum())
    if lang == "es":
        ttl_a = title(lang, "ST4a", f"Crosswalk comunal INE–DEIS: nombres de comuna de FONASA, inscritos APS e ISAPRE enlazados al código único territorial por método (coincidencia exacta o alias explícito), 2019–2025")
        note_a = (f"Crosswalk de {n_cw} comunas (código único territorial INE de 4/5 dígitos ↔ código DEIS de 5 dígitos con cero inicial). Método exacto = nombre normalizado (sin tildes, mayúsculas, sin signos) idéntico al de INE; "
                  f"alias = tabla explícita de variantes ({n_alias} nombres crudos: Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino), La Calera); nunca se usa coincidencia difusa. "
                  "Los nombres no enlazados son marcadores no geográficos («DESCONOCIDA», «Sin dato Comuna», vacío) y se listan en la ST4b; los inscritos APS no tienen filas no enlazadas. "
                  "Geografías distintas: APS = comuna del centro (lugar de atención); FONASA = comuna de inscripción APS (inscritos) o domicilio (no inscritos); ISAPRE = comuna administrativa del beneficiario; INE = residencia. " + T("identical_variants", lang))
        ttl_b = title(lang, "ST4b", "Nombres de comuna no enlazados al crosswalk (marcadores no geográficos) por fuente y año, con las personas afectadas y su participación en el total nacional de la fuente")
        note_b = ("Una fila por fuente × año × nombre crudo no enlazado. Personas = beneficiarios (FONASA) o beneficiarios ISAPRE en las filas no enlazadas (stocks de diciembre); % = personas no enlazadas / total nacional de la fuente en el mismo año "
                  "(FONASA: total de beneficiarios del archivo agregado; ISAPRE: beneficiarios totales). «DESCONOCIDA», «Sin dato Comuna» y «Sin Código de Comuna» son el valor tal como lo escribe la fuente; «(vacío)» y «VACÍO» marcan la celda sin nombre de comuna y los escribe este estudio. "
                  "Estas filas se conservan en los totales nacionales y solo se excluyen de las tasas comunales. " + T("identical_variants", lang))
    else:
        ttl_a = title(lang, "ST4a", "INE–DEIS comuna crosswalk: comuna names of FONASA, APS enrolment and ISAPRE linked to the unique territorial code by method (exact match or explicit alias), 2019–2025")
        note_a = (f"Crosswalk of {n_cw} comunas (4/5-digit INE unique territorial code ↔ 5-digit DEIS code with leading zero). Exact method = normalised name (accents stripped, upper case, punctuation removed) identical to INE; "
                  f"alias = explicit table of spelling variants ({n_alias} raw names: Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino), La Calera); fuzzy matching is never used. "
                  "Unlinked names are non-geographic placeholders ('UNKNOWN', 'Sin dato Comuna', blank) and are listed in ST4b; APS enrolment has no unlinked rows. "
                  "Different geographies: APS = comuna of the centre (place of care); FONASA = comuna of APS enrolment (enrolled) or domicile (not enrolled); ISAPRE = administrative comuna of the beneficiary; INE = residence. " + T("identical_variants", lang))
        ttl_b = title(lang, "ST4b", "Comuna names not linked to the crosswalk (non-geographic placeholders) by source and year, with the persons affected and their share of the source's national total")
        note_b = ("One row per source × year × unlinked raw name. Persons = FONASA beneficiaries or ISAPRE beneficiaries in the unlinked rows (December stocks); % = unlinked persons / national total of the source in the same year "
                  "(FONASA: total beneficiaries of the aggregate file; ISAPRE: total beneficiaries). 'UNKNOWN', 'Sin dato Comuna' and 'Sin Código de Comuna' are the source's own values, glossed into the language of the document where a gloss exists ('DESCONOCIDA' → 'UNKNOWN'; the raw string is kept in the numeric version); '(missing)' and 'MISSING' mark the cell with no comuna name and are written by this study. "
                  "These rows are retained in national totals and excluded only from comuna-level rates. " + T("identical_variants", lang))
    return (out_a, None, ttl_a, note_a), (out_b, numeric_b, ttl_b, note_b)


# ---------------------------------------------------------------------------
# ST5 — diccionario de ítems de encuestas
# ---------------------------------------------------------------------------
def st5(D: dict, lang: str):
    si = D["si"]
    rows = []
    for r in si.itertuples():
        if lang == "en":
            resp, uni, codes, miss, treat = SURVEY_EN.get(r.variable, (r.respondent, r.universe, r.response_codes, r.missing_codes, r.treatment_in_analysis))
            module, role = SURVEY_MODULE_EN.get(r.module, r.module), SURVEY_ROLE_EN.get(r.role, r.role)
        else:
            resp, uni, codes, miss, treat, module, role = r.respondent, r.universe, r.response_codes, r.missing_codes, r.treatment_in_analysis, r.module, r.role
        rows.append({T("col_survey", lang): r.survey, T("col_survey_module", lang): module, T("col_variable", lang): r.variable, T("col_role", lang): role,
                     T("col_var_label", lang): r.variable_label, T("col_wording", lang): r.question_wording, T("col_respondent", lang): resp, T("col_universe", lang): uni,
                     T("col_codes_resp", lang): codes, T("col_missing", lang): miss, T("col_treatment", lang): treat, T("col_source_doc", lang): r.source_document})
    out = pd.DataFrame(rows)
    if lang == "es":
        ttl = title(lang, "ST5", "Diccionario de los ítems de autismo y de las variables de diseño de ENDIDE 2022 y ENCAVI 2023–2024")
        note = ("Ítems: ENDIDE 2022 c26_33 (adultos de 18+, autorreporte o tercero) y n29_19 (NNA de 2–17, informa el/la responsable principal), con confirmación médica n29a_19 y tratamiento n29b/c_19 solo para NNA; "
                "ENCAVI 2023–2024 p4_6_1_h (personas de 15+, diagnóstico declarado) y tratamiento p4_6_2_h. Etiquetas y redacción se transcriben textualmente del libro de códigos/cuestionario. "
                "Diseño complejo: ENDIDE fexp/estrato/cod_upm; ENCAVI w_personas_cal/varstrat/varunit; EE por linealización de Taylor, IC 95 % logit con gl = UPM − estratos; dominios con < 30 casos no ponderados se marcan imprecisos. "
                "Las encuestas son benchmarks de orden de magnitud de autorreporte/reporte de cuidadores, no prevalencia validada ni validación uno a uno de códigos; nunca se desagregan a comuna. " + T("identical_variants", lang))
    else:
        ttl = title(lang, "ST5", "Dictionary of the autism items and design variables of ENDIDE 2022 and ENCAVI 2023–2024")
        note = ("Items: ENDIDE 2022 c26_33 (adults aged 18+, self- or proxy-report) and n29_19 (children/adolescents aged 2–17, reported by the main caregiver), with medical confirmation n29a_19 and treatment n29b/c_19 for children/adolescents only; "
                "ENCAVI 2023–2024 p4_6_1_h (persons aged 15+, declared diagnosis) and treatment p4_6_2_h. Labels and wording are transcribed verbatim (Spanish) from the codebook/questionnaire. "
                "Complex design: ENDIDE fexp/estrato/cod_upm; ENCAVI w_personas_cal/varstrat/varunit; Taylor-linearised SE, logit 95% CI with df = PSUs − strata; domains with < 30 unweighted cases are flagged imprecise. "
                "Surveys are order-of-magnitude benchmarks of self-/caregiver report, not validated prevalence nor one-to-one validation of codes; never disaggregated to comuna. " + T("identical_variants", lang))
    return out, None, ttl, note


# ---------------------------------------------------------------------------
# ST6 — diccionario JUNAEB por año y nivel
# ---------------------------------------------------------------------------
#: «código=frecuencia» es la forma de MÁQUINA con la que el módulo 05 escribe la columna de códigos
#: observados en la tabla tidy; al IMPRIMIRLA se separa el signo igual con espacios. No es un capricho
#: tipográfico: pegado, «blank=184963» es UN SOLO trozo de 12 caracteres sin punto de corte, y en la
#: columna estrecha de la Tabla S43 —dieciséis columnas— Word lo partía por donde le tocaba e imprimía
#: «blank=18496» con un «3» suelto en la línea siguiente, que se lee como 18.496: un orden de magnitud.
#: El español no lo sufría porque «en blanco=184963» ya traía un blanco donde cortar, de modo que los dos
#: idiomas imprimían cosas distintas. Con el espacio, el número queda entero y `docx_builder.numeros_de`
#: lo reconoce y le garantiza el ancho de columna que necesita.
_CODE_EQ_RE = re.compile(r"\s*=\s*(?=\d)")


def _data_states(text: str, lang: str) -> str:
    """Traduce los estados del dato («sin dato», «en blanco») que el módulo 05 escribe en la tabla tidy."""
    s = str(text).replace("sin dato", T("state_missing", lang)).replace("en blanco", T("state_blank", lang))
    return _CODE_EQ_RE.sub(" = ", s)


def st6(D: dict, lang: str):
    ji, jt = D["ji"], D["jt"]
    lvl = jt[["level", "level_label_es", "level_label_en"]].drop_duplicates().set_index("level")
    est = jt[jt.sex == "all"].set_index(["year", "level"]).estimable
    level_order = ["parvularia", "basico1", "basico5", "medio1"]
    rows = []
    for (year, level), g in ji.groupby(["year", "level"], sort=False):
        pick = lambda role: g[g.role == role].iloc[0] if (g.role == role).any() else None  # noqa: E731
        tea, filt, w, sx, gr = pick("tea_category"), pick("filter_prolonged_medical_diagnosis"), pick("expansion_weight"), pick("sex"), pick("grade")
        e = est.get((year, level), "")
        rows.append({T("col_year", lang): year, T("col_level", lang): lvl.loc[level, f"level_label_{lang}"] if level in lvl.index else level,
                     T("col_files", lang): " · ".join(str(x or DASH) for x in (g.source_file.iloc[0], g.encoding.iloc[0], g.dictionary_file.iloc[0], g.questionnaire_file.iloc[0])),
                     T("col_tea_var", lang): (T("absent", lang) if tea is None or tea.variable == "ABSENT" else tea.variable),
                     T("col_tea_wording", lang): (LB.tidy_text(tea.wording, lang) if tea is not None else DASH), T("col_tea_codes", lang): (_data_states(tea.value_codes_observed, lang) if tea is not None and tea.value_codes_observed else DASH),
                     T("col_filter_var", lang): (filt.variable if filt is not None else DASH), T("col_filter_wording", lang): (filt.wording if filt is not None else DASH),
                     T("col_aux_vars", lang): " · ".join([
                         (T("weight_absent", lang) if w is None or w.variable == "ABSENT" else str(w.variable)),
                         (str(sx.variable) if sx is not None else DASH),
                         (str(gr.variable) if gr is not None else DASH)]),
                     T("col_other_cats", lang): fi(int((g.role == "other_category").sum()), lang),
                     T("col_estimable", lang): {"yes": T("est_yes", lang), "unweighted_only": T("est_unweighted", lang), "no": T("est_no", lang)}.get(e, e)})
    out = pd.DataFrame(rows)
    out["_o"] = [level_order.index(l) if l in level_order else 9 for l in ji.groupby(["year", "level"], sort=False).size().index.get_level_values(1)]
    out = out.sort_values([T("col_year", lang), "_o"], kind="mergesort").drop(columns="_o").reset_index(drop=True)
    long = ji.copy()
    long["role"] = [T(JUNAEB_ROLE.get(r, "role_other"), lang) for r in long.role]
    # «ABSENT» y la frase que lo acompaña son el marcador del módulo 05 (el año sin categoría TEA), no
    # la redacción del cuestionario: se leen en el idioma del documento.
    long["variable"] = [LB.tidy_text(v, lang) for v in long.variable]
    long["wording"] = [LB.tidy_text(v, lang) for v in long.wording]
    long = long.rename(columns={"year": T("col_year", lang), "level": T("col_level", lang), "source_file": T("col_source_file", lang), "encoding": T("col_encoding", lang),
                                "dictionary_file": T("col_dictionary", lang), "questionnaire_file": T("col_questionnaire", lang), "variable": T("col_variable", lang), "role": T("col_role", lang),
                                "wording": T("col_wording", lang), "value_codes_observed": T("col_value_codes", lang), "value_labels": T("col_value_labels", lang), "note": T("col_note", lang)}).drop(columns=["script"])
    if lang == "es":
        ttl = title(lang, "ST6", "Diccionario de la Encuesta de Vulnerabilidad Estudiantil (JUNAEB EVE) por año y nivel, 2019–2025: ítem de trastorno del espectro autista, filtro, ponderador y estimabilidad")
        note = ("Una fila por año × nivel (28 archivos de microdatos desidentificados). El ítem TEA es una categoría del ítem de enfermedad o condición de salud diagnosticada por un médico que requiere tratamiento prolongado (reporte del cuidador); "
                "2019–2022: sin categoría TEA (no estimable); 2023: ítem disponible sin ponderador publicado (solo conteos y proporción no ponderada); 2024: ponderador EXP_REG, 1º medio con la variable TEA completamente vacía (no estimable, no cero); 2025: ponderador EXP. "
                "Redacción y códigos observados se transcriben textualmente del diccionario/cuestionario anual («—» = sin diccionario publicado para ese año y nivel; se usa el cuestionario). Cohortes escolares seleccionadas y reporte de cuidadores: no es prevalencia nacional. "
                "La versión larga (ST6_junaeb_items_long) lista todas las variables del ítem por año y nivel. " + T("identical_variants", lang))
    else:
        ttl = title(lang, "ST6", "Dictionary of the Student Vulnerability Survey (JUNAEB EVE) by year and level, 2019–2025: autism spectrum disorder item, filter, weight and estimability")
        note = ("One row per year × level (28 de-identified microdata files). The ASD item is a category of the item on a physician-diagnosed illness or health condition requiring prolonged treatment (caregiver report); "
                "2019–2022: no ASD category (not estimable); 2023: item available without a published weight (counts and unweighted proportion only); 2024: weight EXP_REG, grade 9 (1º medio) with the ASD variable entirely empty (not estimable, not zero); 2025: weight EXP. "
                "Wording and observed codes are transcribed verbatim (Spanish) from the annual dictionary/questionnaire ('—' = no dictionary published for that year and level; the questionnaire is used). Selected school cohorts and caregiver report: not national prevalence. "
                "The long version (ST6_junaeb_items_long) lists every variable of the item by year and level. " + T("identical_variants", lang))
    return out, long, ttl, note


# ---------------------------------------------------------------------------
# ST7 — procedencia completa y concordancia de manifiestos
# ---------------------------------------------------------------------------
def st7(D: dict, lang: str):
    dp, pm = D["dp"].copy(), D["pm"].copy()
    dp["bytes_num"] = num(dp["bytes"])

    def sha_flag(v):
        return {"True": T("yes", lang), "False": T("no", lang), "not_listed": T("not_listed", lang)}.get(v, v)

    def date_txt(v):
        if lang == "es":
            for a, b in DATE_ES:
                v = v.replace(a, b)
        return v
    # Los campos descriptivos de data_provenance.csv están redactados por este estudio (no son una
    # transcripción del diccionario de la fuente), de modo que el documento en español los lee en
    # español: labels.provenance_text da la glosa y la prueba de idioma falla si aparece un valor nuevo.
    pv = (lambda v: LB.provenance_text(v, lang))
    out = pd.DataFrame({T("col_source", lang): dp.source_id, T("col_role_artefact", lang): [T(ROLE_ARTEFACT.get(r, "role_data"), lang) for r in dp.artefact_role],
                        T("col_provider", lang): dp.provider, T("col_file", lang): dp.file, T("col_size", lang): [fd(b / 1e6, 2, lang) for b in dp.bytes_num],
                        T("col_sha", lang): dp.sha256.str[:12], T("col_date", lang): [date_txt(v) for v in dp.downloaded_or_version_date],
                        T("col_unit", lang): [pv(v) for v in dp.observation_unit], T("col_period", lang): [pv(v) for v in dp.period],
                        T("col_stock_flow", lang): [pv(v) for v in dp.stock_or_flow],
                        T("col_breaks", lang): [pv(v) for v in dp.definition_breaks], T("col_linkage", lang): [pv(v) for v in dp.linkage_restrictions],
                        T("col_use_rule", lang): [pv(v) for v in dp.use_rule],
                        T("col_manifest_sha", lang): [sha_flag(v) for v in dp.sha256_matches_manifest]})
    numeric = dp[["source_id", "artefact_role", "provider", "file", "relative_path", "root", "bytes", "sha256", "downloaded_or_version_date", "file_mtime_utc", "observation_unit", "period",
                  "population_covered", "geography", "codes_columns_used", "stock_or_flow", "possible_denominator", "definition_breaks", "linkage_restrictions", "use_rule", "manifest_source",
                  "manifest_sha256", "sha256_matches_manifest", "manifest_bytes", "bytes_match_manifest", "landing_url"]].copy()
    numeric["bytes"] = num(numeric["bytes"]).astype("Int64")
    # ST7b
    pm["manifest_bytes_num"], pm["observed_bytes_num"] = num(pm.manifest_bytes), num(pm.observed_bytes)

    def bflag(r):
        if r.bytes_match == "":
            return T("no_size", lang) if r.manifest else T("not_listed", lang)
        return yn(r.bytes_match, lang)
    out_b = pd.DataFrame({T("col_source", lang): pm.source_id, T("col_file", lang): pm.file, T("col_manifest", lang): [m if m else T("not_listed", lang) for m in pm.manifest],
                          T("col_manifest_sha12", lang): [s[:12] if s else DASH for s in pm.manifest_sha256], T("col_observed_sha12", lang): pm.observed_sha256.str[:12],
                          T("col_sha_match", lang): [yn(v, lang) if v else T("not_listed", lang) for v in pm.sha256_match],
                          T("col_manifest_bytes", lang): [fi(x, lang) for x in pm.manifest_bytes_num], T("col_observed_bytes", lang): [fi(x, lang) for x in pm.observed_bytes_num],
                          T("col_bytes_match", lang): [bflag(r) for r in pm.itertuples()],
                          T("col_manifest_date", lang): [d if d else (T("no_date", lang) if m else DASH) for d, m in zip(pm.manifest_date, pm.manifest)],
                          T("col_manifest_note", lang): [LB.provenance_text(n, lang) if n else DASH for n in pm.manifest_note]})
    numeric_b = pm[["source_id", "file", "relative_path", "manifest", "manifest_sha256", "observed_sha256", "sha256_match", "manifest_bytes", "observed_bytes", "bytes_match", "manifest_date", "manifest_note"]].copy()
    n_art, n_src = len(dp), dp.source_id.nunique()
    gb = dp.bytes_num.sum() / 1e9
    n_match, n_mismatch, n_nl = int((dp.sha256_matches_manifest == "True").sum()), int((dp.sha256_matches_manifest == "False").sum()), int((dp.sha256_matches_manifest == "not_listed").sum())
    n_pm, n_pm_ok, n_pm_bad = len(pm), int((pm.sha256_match == "True").sum()), int((pm.sha256_match == "False").sum())
    if lang == "es":
        ttl = title(lang, "ST7", f"Procedencia completa de los {n_art} artefactos fuente ({n_src} grupos de fuentes, {fd(gb, 2, lang)} GB): archivo, tamaño, SHA-256, fecha, unidad, período, stock/flujo, quiebres, enlace y regla de uso")
        note = (f"Una fila por artefacto en disco (módulo 00_provenance; SHA-256 calculado por bloques de 1 MiB sobre el archivo completo; aquí se muestran los 12 primeros caracteres y la versión numérica el hash completo). "
                f"Concordancia con manifiesto: {n_match} coinciden, {n_mismatch} difieren, {n_nl} no listados en ningún manifiesto. Fecha = fecha de descarga/extracción/consolidación del manifiesto más reciente que lista el archivo, o mtime del archivo cuando ningún manifiesto lo fecha. "
                "Los campos descriptivos (unidad, período, stock/flujo, quiebres de definición, restricciones de enlace y regla de uso) son la redacción de este estudio y se leen en el idioma del documento; los identificadores de la fuente que van dentro de la frase (nombres de archivo, columnas, códigos y rutas) se conservan literales. La forma canónica que guarda data_provenance.csv es la inglesa. "
                "Las bases fuente nunca se copian al repositorio ni se sobrescriben. " + T("identical_variants", lang))
        ttl_b = title(lang, "ST7b", f"Concordancia de SHA-256 y tamaño entre los artefactos en disco y los manifiestos que los listan ({n_pm} entradas)")
        note_b = (f"Una fila por artefacto × manifiesto (download_manifest.csv, source_manifest.csv de FONASA, manifiesto de extracción de Serie P, canonical_manifest.csv de Serie A y DEIS Egresos, SOURCES_MANIFEST.md de GRD). "
                  f"SHA coincide: {n_pm_ok} sí, {n_pm_bad} no, {n_pm - n_pm_ok - n_pm_bad} no listados. Los bytes se comparan solo cuando el manifiesto registra tamaño (el manifiesto GRD registra número de registros). "
                  "«—» = artefacto no listado en ningún manifiesto; «sin fecha» = manifiesto sin fecha para ese artefacto. " + T("identical_variants", lang))
    else:
        ttl = title(lang, "ST7", f"Full provenance of the {n_art} source artefacts ({n_src} source groups, {fd(gb, 2, lang)} GB): file, size, SHA-256, date, unit, period, stock/flow, breaks, linkage and use rule")
        note = (f"One row per artefact on disk (module 00_provenance; SHA-256 computed in 1 MiB blocks over the whole file; the first 12 characters are shown here and the full hash in the numeric version). "
                f"Manifest agreement: {n_match} match, {n_mismatch} differ, {n_nl} not listed in any manifest. Date = download/extraction/consolidation date of the newest manifest listing the file, or file mtime when no manifest dates it. "
                "Descriptive fields (unit, period, stock/flow, definition breaks, linkage restrictions and use rule) are the wording of this study and are read in the language of the document; the source identifiers inside each sentence (file names, columns, codes and paths) are kept verbatim. The canonical form stored in data_provenance.csv is the English one. "
                "Source databases are never copied into the repository nor overwritten. " + T("identical_variants", lang))
        ttl_b = title(lang, "ST7b", f"SHA-256 and size agreement between the artefacts on disk and the manifests listing them ({n_pm} entries)")
        note_b = (f"One row per artefact × manifest (download_manifest.csv, FONASA source_manifest.csv, Series P extraction manifest, Series A and DEIS discharges canonical_manifest.csv, GRD SOURCES_MANIFEST.md). "
                  f"SHA match: {n_pm_ok} yes, {n_pm_bad} no, {n_pm - n_pm_ok - n_pm_bad} not listed. Bytes are compared only when the manifest records a size (the GRD manifest records record counts). "
                  "'—' = artefact not listed in any manifest; 'no date' = manifest without a date for that artefact. " + T("identical_variants", lang))
    return (out, numeric, ttl, note), (out_b, numeric_b, ttl_b, note_b), dict(n_mismatch=n_mismatch, n_pm_bad=n_pm_bad)


# ---------------------------------------------------------------------------
# ST8 — auditoría del identificador GRD
# ---------------------------------------------------------------------------
def st8(D: dict, variant: str, lang: str):
    ia = D["ia"].copy()
    ia = ia[ia.variant.isin([variant, "strict_autism_f840"])].copy()
    ia["_o"] = np.where(ia.variant == variant, 0, 1)
    ia = ia.sort_values(["_o", "year"], kind="mergesort")
    for c in ["n_f84", "n_with_valid_id", "n_without_valid_id", "n_unique_ids", "id_length_mode", "id_length_min", "id_length_max", "n_f84_ids_shared_with_previous_year", "n_f84_with_comuna",
              "n_records_total", "n_records_valid_id_all_episodes", "n_f84_exact_duplicates_on_read_columns"]:
        ia[c] = num(ia[c])
    series = [variant_label(variant, lang) if v == variant else T("strict_f840", lang) for v in ia.variant]
    out = pd.DataFrame({T("col_year", lang): ia.year, T("col_series", lang): series, T("col_id_column", lang): ia.identifier_column,
                        T("col_f84_episodes", lang): [fi(x, lang) for x in ia.n_f84], T("col_valid_id", lang): [fi(x, lang) for x in ia.n_with_valid_id],
                        T("col_invalid_id", lang): [f"{fi(n, lang)}" + (f" ({v})" if v else "") for n, v in zip(ia.n_without_valid_id, ia.invalid_id_values)],
                        T("col_unique_ids", lang): [fi(x, lang) for x in ia.n_unique_ids],
                        T("col_id_length", lang): [f"{fi(m, lang)} ({fi(lo, lang)}–{fi(hi, lang)})" for m, lo, hi in zip(ia.id_length_mode, ia.id_length_min, ia.id_length_max)],
                        T("col_shared_prev", lang): [T("first_year", lang) if pd.isna(x) else fi(x, lang) for x in ia.n_f84_ids_shared_with_previous_year],
                        T("col_f84_comuna", lang): [fi(x, lang) for x in ia.n_f84_with_comuna], T("col_records_total", lang): [fi(x, lang) for x in ia.n_records_total],
                        T("col_records_valid", lang): [fi(x, lang) for x in ia.n_records_valid_id_all_episodes], T("col_exact_dup", lang): [fi(x, lang) for x in ia.n_f84_exact_duplicates_on_read_columns]})
    numeric = ia.drop(columns="_o").reset_index(drop=True)
    if lang == "es":
        ttl = title(lang, "ST8", "Auditoría del identificador de persona del GRD público por año, 2019–2024: validez, unicidad dentro del año, formato y solapamiento informativo entre años", variant)
        note = ("Identificador CIP_ENCRIPTADO (2019–2023) e ID_BENEFICIARIO (2024). Identificador válido = distinto de vacío, «SIN INFORMACIÓN» y «DESCONOCIDO». Personas únicas = identificadores válidos distintos entre los episodios con F84 documentado del mismo año; "
                "el formato cambia entre 2020 y 2021 (longitud modal 6 → 8; 0 identificadores compartidos), por lo que nunca se deduplica a través de 2020/2021 ni entre años; el solapamiento con el año anterior es informativo. "
                "Filas duplicadas exactas (45 columnas analizadas) se cuentan y no se eliminan (reproduce los controles). La serie «solo F84.0» es idéntica en ambas variantes. " + T("admin_note", lang))
    else:
        ttl = title(lang, "ST8", "Audit of the person identifier of the public GRD by year, 2019–2024: validity, within-year uniqueness, format and informative overlap between years", variant)
        note = ("Identifier CIP_ENCRIPTADO (2019–2023) and ID_BENEFICIARIO (2024). Valid identifier = not blank, 'SIN INFORMACIÓN' or 'DESCONOCIDO'. Unique persons = distinct valid identifiers among the episodes with documented F84 of the same year; "
                "the format changes between 2020 and 2021 (modal length 6 → 8; 0 shared identifiers), so persons are never deduplicated across 2020/2021 or between years; the overlap with the previous year is informative only. "
                "Exact duplicate rows (45 analysed columns) are counted and not removed (reproduces the controls). The 'F84.0 only' series is identical in both variants. " + T("admin_note", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# ST9 — edad × sexo de los episodios con F84
# ---------------------------------------------------------------------------
AGE_ORDER = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+", "unknown"]
SEX_ORDER = ["HOMBRE", "MUJER", "unknown"]


def st9(D: dict, variant: str, lang: str):
    ag = D["ag"][D["ag"].variant == variant].copy()
    ag["year"] = ag.year.astype(int)
    ag["n_f84"], ag["n_total_episodes"] = num(ag.n_f84), num(ag.n_total_episodes)
    ag["rate_per_100k_episodes"] = 1e5 * ag.n_f84 / ag.n_total_episodes.where(ag.n_total_episodes > 0)
    sex_lab = {"HOMBRE": T("sex_m", lang), "MUJER": T("sex_f", lang), "unknown": T("sex_unknown", lang)}
    age_lab = lambda a: T("age_unknown", lang) if a == "unknown" else a  # noqa: E731
    main = ag[(ag.panel == "observed") & (ag.activity == "all")]
    cp, cs, ca = T("col_position", lang), T("col_sex", lang), T("col_age_group", lang)
    rows = []
    for pos in ["any", "principal"]:
        m = main[main.position == pos]
        for sex in SEX_ORDER:
            s = m[m.sex == sex]
            if s.n_f84.sum() == 0 and sex == "unknown":
                continue
            for age in AGE_ORDER:
                a = s[s.age_group == age].set_index("year")
                if age == "unknown" and (a.n_f84.sum() if len(a) else 0) == 0:
                    continue
                row = {cp: T("pos_" + pos, lang), cs: sex_lab[sex], ca: age_lab(age)}
                for y in YEARS_GRD:
                    row[str(y)] = DASH if y not in a.index else f"{fi(a.loc[y, 'n_f84'], lang)} ({fd(a.loc[y, 'rate_per_100k_episodes'], 1, lang)})"
                rows.append(row)
            tot = s.groupby("year")[["n_f84", "n_total_episodes"]].sum()
            row = {cp: T("pos_" + pos, lang), cs: sex_lab[sex], ca: T("total", lang)}
            for y in YEARS_GRD:
                row[str(y)] = DASH if y not in tot.index else f"{fi(tot.loc[y, 'n_f84'], lang)} ({fd(1e5 * tot.loc[y, 'n_f84'] / tot.loc[y, 'n_total_episodes'], 1, lang)})"
            rows.append(row)
        tot = m.groupby("year")[["n_f84", "n_total_episodes"]].sum()
        row = {cp: T("pos_" + pos, lang), cs: T("total", lang), ca: T("total", lang)}
        for y in YEARS_GRD:
            row[str(y)] = DASH if y not in tot.index else f"{fi(tot.loc[y, 'n_f84'], lang)} ({fd(1e5 * tot.loc[y, 'n_f84'] / tot.loc[y, 'n_total_episodes'], 1, lang)})"
        rows.append(row)
    out = pd.DataFrame(rows)
    numeric = ag.copy()
    lo, hi = [], []
    for n, d in zip(numeric.n_f84, numeric.n_total_episodes):
        if pd.isna(n) or pd.isna(d) or d <= 0:
            lo.append(np.nan)
            hi.append(np.nan)
        else:
            _, l, h = C.rate_per(int(n), float(d))
            lo.append(l)
            hi.append(h)
    numeric["rate_lo95"], numeric["rate_hi95"] = lo, hi
    numeric["n_f84"] = numeric.n_f84.astype("Int64")
    numeric["n_total_episodes"] = numeric.n_total_episodes.astype("Int64")
    numeric = numeric.sort_values(["panel", "position", "activity", "year", "sex", "age_group"]).reset_index(drop=True)
    if lang == "es":
        ttl = title(lang, "ST9", "Episodios GRD con F84 documentado por sexo y grupo de edad quinquenal, 2019–2024: número y tasa por 100.000 episodios GRD de la misma celda sexo-edad (panel observado, toda modalidad)", variant)
        note = ("Celda = episodios con F84 (entre paréntesis, por 100.000 episodios GRD del mismo año, sexo y grupo de edad; panel anual observado de 65/65/65/65/68/72 hospitales; toda modalidad incluida cirugía mayor ambulatoria). "
                "Bloques: F84 en cualquier posición diagnóstica y F84 como diagnóstico principal (serie separada, nunca «hospitalizaciones por autismo»). Edad = piso((fecha de ingreso − fecha de nacimiento)/365,25); < 0 o > 110 → desconocida. "
                "Las tasas por episodio describen la composición del casemix hospitalario, no el riesgo poblacional; las tasas por población INE están en la tabla S4. La versión numérica añade panel fijo de 65, hospitalización estricta e IC 95 % exactos de Poisson. "
                + T("admin_note", lang) + " " + T("pandemic_law", lang))
    else:
        ttl = title(lang, "ST9", "GRD episodes with documented F84 by sex and five-year age group, 2019–2024: number and rate per 100,000 GRD episodes of the same sex-age cell (observed panel, all modalities)", variant)
        note = ("Cell = episodes with F84 (in brackets, per 100,000 GRD episodes of the same year, sex and age group; observed annual panel of 65/65/65/65/68/72 hospitals; all modalities including major ambulatory surgery). "
                "Blocks: F84 in any diagnosis position and F84 as principal diagnosis (separate series, never 'hospitalisations for autism'). Age = floor((admission date − birth date)/365.25); < 0 or > 110 → unknown. "
                "Rates per episode describe hospital case-mix composition, not population risk; rates per INE population are in table S4. The numeric version adds the fixed panel of 65, strict hospitalisation and exact Poisson 95% CIs. "
                + T("admin_note", lang) + " " + T("pandemic_law", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# ST10 — subcódigos F84 por año y posición
# ---------------------------------------------------------------------------
def st10(D: dict, variant: str, lang: str):
    sc = D["sc"].copy()
    sc["year"] = sc.year.astype(int)
    sc["n_episodes"] = num(sc.n_episodes)
    codes = [c for c in CFG.F84_SUBCODES if c in set(sc.subcode)] + sorted(set(sc.subcode) - set(CFG.F84_SUBCODES))
    vset = set(CFG.VARIANTS[variant]["grd_subcodes"])
    rows, numeric_rows = [], []
    for code in codes:
        for pos in ["any", "principal", "secondary"]:
            g = sc[(sc.subcode == code) & (sc.position == pos)].set_index("year").n_episodes
            row = {T("col_subcode", lang): SUBCODE_LABELS.get(code, {}).get(lang, code), T("col_position", lang): T("pos_" + pos, lang),
                   T("col_in_variant", lang): T("yes", lang) if code in vset else T("excluded", lang)}
            for y in YEARS_GRD:
                n = int(g.loc[y]) if y in g.index else 0
                row[str(y)] = fi(n, lang)
                numeric_rows.append(dict(variant=variant, subcode=code, position=pos, in_variant_code_set=code in vset, year=y, n_episodes=n))
            rows.append(row)
    out = pd.DataFrame(rows)
    numeric = pd.DataFrame(numeric_rows)
    never = [c for c in CFG.F84_SUBCODES if c not in set(sc.subcode)]
    never_txt = ", ".join(never) if never else DASH
    if lang == "es":
        ttl = title(lang, "ST10", "Subcódigos CIE-10 de la familia F84 en los episodios del GRD público por año y posición diagnóstica, 2019–2024", variant)
        note = ("Un episodio cuenta una vez por subcódigo y posición (cualquier posición = DIAGNOSTICO1–35; principal = DIAGNOSTICO1; secundaria = DIAGNOSTICO2–35); un episodio con varios subcódigos F84 aparece en más de una fila, por lo que las filas no se suman al total de episodios con F84. "
                f"0 = ningún episodio con ese subcódigo en esa posición. Códigos del conjunto de config nunca observados en el GRD: {never_txt}. La columna «en el conjunto de la variante» marca F84.2 (síndrome de Rett) como excluido en la variante sin Rett; los conteos por subcódigo son idénticos en ambas variantes. "
                "Panel anual observado (65/65/65/65/68/72 hospitales), toda modalidad. " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    else:
        ttl = title(lang, "ST10", "ICD-10 subcodes of the F84 family in public GRD episodes by year and diagnosis position, 2019–2024", variant)
        note = ("An episode counts once per subcode and position (any position = DIAGNOSTICO1–35; principal = DIAGNOSTICO1; secondary = DIAGNOSTICO2–35); an episode with several F84 subcodes appears in more than one row, so rows do not add up to the total of episodes with F84. "
                f"0 = no episode with that subcode in that position. Codes of the config set never observed in the GRD: {never_txt}. The column 'in the variant's code set' marks F84.2 (Rett syndrome) as excluded in the without-Rett variant; subcode counts are identical in both variants. "
                "Observed annual panel (65/65/65/65/68/72 hospitals), all modalities. " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# ST11 — DEIS anual y DEIS frente a GRD
# ---------------------------------------------------------------------------
def st11(D: dict, variant: str, lang: str):
    ds = D["ds"][D["ds"].variant == variant].copy()
    ds["_o"] = np.where(ds.source_layout == "canonical", 0, 1)
    ds = ds.sort_values(["_o", "year"], kind="mergesort")
    for c in ["discharges_total", "f84_diag1", "f84_diag2", "f84_any", "f84_rett_f842_diag1", "f84_deaths", "rate_per_100k_discharges", "rate_lo95", "rate_hi95", "discharges_snss", "discharges_no_snss",
              "discharges_suppressed", "f84_any_snss", "f84_any_no_snss", "f84_any_suppressed", "masked_rows_share", "n_columns_file"]:
        ds[c] = num(ds[c])
    rett_col = T("col_f842_diag1_incl" if variant == "con_rett" else "col_f842_diag1_excl", lang)
    out_a = pd.DataFrame({T("col_year", lang): ds.year, T("col_layout_deis", lang): [T("layout_canonical", lang) if s == "canonical" else T("layout_15col", lang) for s in ds.source_layout],
                          T("col_discharges", lang): [fi(x, lang) for x in ds.discharges_total], T("col_snss", lang): [fi(x, lang) for x in ds.discharges_snss],
                          T("col_no_snss", lang): [fi(x, lang) for x in ds.discharges_no_snss], T("col_suppressed", lang): [fi(x, lang) for x in ds.discharges_suppressed],
                          T("col_masked_share", lang): [fpct(100 * x, 1, lang) for x in ds.masked_rows_share],
                          T("col_f84_diag1", lang): [fi(x, lang) for x in ds.f84_diag1], T("col_f84_diag2", lang): [fi(x, lang) for x in ds.f84_diag2], T("col_f84_any_deis", lang): [fi(x, lang) for x in ds.f84_any],
                          rett_col: [fi(x, lang) for x in ds.f84_rett_f842_diag1], T("col_f84_deaths", lang): [fi(x, lang) for x in ds.f84_deaths],
                          T("col_rate_deis", lang): [f"{fd(r, 1, lang)} ({C.fmt_ci(lo, hi, 1, lang)})" for r, lo, hi in zip(ds.rate_per_100k_discharges, ds.rate_lo95, ds.rate_hi95)],
                          T("col_f84_snss", lang): [fi(x, lang) for x in ds.f84_any_snss], T("col_f84_no_snss", lang): [fi(x, lang) for x in ds.f84_any_no_snss], T("col_f84_supp", lang): [fi(x, lang) for x in ds.f84_any_suppressed],
                          T("col_age_scheme", lang): [T("age_decadal", lang) if a == "decadal" else T("age_five_year", lang) if a == "five_year" else a for a in ds.age_scheme],
                          T("col_n_columns", lang): [fi(x, lang) for x in ds.n_columns_file], T("col_source_file", lang): ds.source_file})
    numeric_a = ds.drop(columns="_o").reset_index(drop=True)
    # ST11b
    dv = D["dv"][D["dv"].variant.isin([variant, "strict_autism_f840"])].copy()
    dv["_o"] = np.where(dv.variant == variant, 0, 1)
    dv = dv.sort_values(["_o", "year"], kind="mergesort")
    ncols = [c for c in dv.columns if c not in ("year", "variant", "variant_definition", "grd_source", "unit_deis", "unit_grd", "comparability_note", "_o")]
    for c in ncols:
        dv[c] = num(dv[c])
    series = [variant_label(variant, lang) if v == variant else T("strict_f840", lang) for v in dv.variant]
    out_b = pd.DataFrame({T("col_year", lang): dv.year, T("col_series", lang): series,
                          T("col_discharges", lang): [fi(x, lang) for x in dv.deis_discharges_total], T("col_snss", lang): [fi(x, lang) for x in dv.deis_discharges_snss],
                          T("col_deis_f84p", lang): [fi(x, lang) for x in dv.deis_f84_principal], T("col_deis_f84p_snss", lang): [fi(x, lang) for x in dv.deis_f84_principal_snss],
                          T("col_deis_f84p_nosnss", lang): [fi(x, lang) for x in dv.deis_f84_principal_no_snss], T("col_deis_f84p_supp", lang): [fi(x, lang) for x in dv.deis_f84_principal_suppressed],
                          T("col_rate_deis", lang): [f"{fd(r, 1, lang)} ({C.fmt_ci(lo, hi, 1, lang)})" for r, lo, hi in zip(dv.deis_rate_f84_principal_per_100k_discharges, dv.deis_rate_lo95, dv.deis_rate_hi95)],
                          T("col_grd_episodes", lang): [fi(x, lang) for x in dv.grd_records_total], T("col_grd_hospitals", lang): [fi(x, lang) for x in dv.grd_hospitals_observed],
                          T("col_grd_f84p", lang): [fi(x, lang) for x in dv.grd_f84_principal], T("col_grd_rate_p", lang): [fd(x, 1, lang) for x in dv.grd_rate_f84_principal_per_100k_episodes],
                          T("col_grd_hosp_f84p", lang): [fi(x, lang) for x in dv.grd_f84_principal_hospitalisation], T("col_grd_fixed_f84p", lang): [fi(x, lang) for x in dv.grd_f84_principal_fixed65],
                          T("col_grd_f84any", lang): [fi(x, lang) for x in dv.grd_f84_any], T("col_grd_f84sec", lang): [fi(x, lang) for x in dv.grd_f84_secondary_only],
                          T("col_ratio_total", lang): [fd(x, 2, lang) for x in dv.ratio_deis_total_to_grd_total], T("col_ratio_p", lang): [fd(x, 2, lang) for x in dv.ratio_deis_f84_principal_to_grd_f84_principal],
                          T("col_ratio_p_snss", lang): [fd(x, 2, lang) for x in dv.ratio_deis_f84_principal_snss_to_grd_f84_principal],
                          T("col_ratio_p_snss_hosp", lang): [fd(x, 2, lang) for x in dv.ratio_deis_f84_principal_snss_to_grd_f84_principal_hospitalisation]})
    numeric_b = dv.drop(columns=["_o", "ratio_grd_f84_any_to_deis_f84_principal"]).reset_index(drop=True)
    if lang == "es":
        ttl_a = title(lang, "ST11a", "Egresos hospitalarios DEIS 2019–2024: egresos totales, pertenencia al SNSS, enmascaramiento y egresos con F84 por posición diagnóstica, con tasa por 100.000 egresos", variant)
        note_a = ("Unidad: egreso hospitalario DEIS (todos los establecimientos del país, SNSS y no SNSS). DEIS publica DIAG1 = diagnóstico principal y DIAG2 = causa externa (CIE-10 V01–Y98): no existe diagnóstico secundario, por lo que F84 en DIAG2 es 0 por construcción y "
                  "«F84 en cualquiera de las dos posiciones» = «F84 principal». Tasa = F84 principal / egresos totales del mismo año × 100.000, IC 95 % exacto de Poisson. Enmascarado = registros con variables demográficas y pertenencia sustituidas por «*» (conservados en los totales). "
                  "La variante de 15 columnas de 2021 contiene el mismo microdato sin enmascarar (edad quinquenal) y se muestra como fila de sensibilidad, sin mezclarla con la canónica. Códigos: familia F84 según la variante (F84.2 contabilizado aparte). "
                  + T("admin_note", lang) + " " + T("pandemic_law", lang))
        ttl_b = title(lang, "ST11b", "Comparación de cobertura entre egresos DEIS y episodios del GRD público por año, 2019–2024: F84 principal frente a F84 principal (única serie homologable)", variant)
        note_b = ("DEIS y GRD no se enlazan por persona ni por episodio; los cocientes describen cobertura relativa y no son probabilidades. La única comparación homologable es F84 como diagnóstico principal en ambas fuentes (DEIS DIAG1 frente a GRD DIAGNOSTICO1); "
                  "GRD F84 en cualquier posición se muestra solo como contexto porque DEIS no publica diagnósticos secundarios (en 2024 el 95,5 % de los episodios GRD con F84 lo tienen solo en posición secundaria), y por ello no se calcula ningún cociente entre GRD «cualquier posición» y DEIS. "
                  "DEIS cubre todos los establecimientos (SNSS y no SNSS); el GRD público cubre los hospitales SNSS con GRD (panel observado 65/65/65/65/68/72; panel fijo de 65 y hospitalización estricta como sensibilidades). "
                  "La serie «solo F84.0» es idéntica en ambas variantes. " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    else:
        ttl_a = title(lang, "ST11a", "DEIS hospital discharges 2019–2024: total discharges, SNSS affiliation, masking and discharges with F84 by diagnosis position, with rate per 100,000 discharges", variant)
        note_a = ("Unit: DEIS hospital discharge (all establishments in the country, SNSS and non-SNSS). DEIS publishes DIAG1 = principal diagnosis and DIAG2 = external cause (ICD-10 V01–Y98): there is no secondary diagnosis, so F84 in DIAG2 is 0 by construction and "
                  "'F84 in either position' = 'principal F84'. Rate = principal F84 / total discharges of the same year × 100,000, exact Poisson 95% CI. Masked = records whose demographic variables and affiliation are replaced by '*' (retained in totals). "
                  "The 2021 15-column variant holds the same microdata unmasked (five-year ages) and is shown as a sensitivity row, never mixed with the canonical file. Codes: F84 family according to the variant (F84.2 counted separately). "
                  + T("admin_note", lang) + " " + T("pandemic_law", lang))
        ttl_b = title(lang, "ST11b", "Coverage comparison between DEIS discharges and public GRD episodes by year, 2019–2024: principal F84 versus principal F84 (the only comparable series)", variant)
        note_b = ("DEIS and GRD are not linked by person or episode; ratios describe relative coverage and are not probabilities. The only comparable series is F84 as principal diagnosis in both sources (DEIS DIAG1 versus GRD DIAGNOSTICO1); "
                  "GRD F84 in any position is shown as context only because DEIS publishes no secondary diagnoses (in 2024, 95.5% of GRD episodes with F84 carry it only in a secondary position), so no ratio between GRD 'any position' and DEIS is computed. "
                  "DEIS covers all establishments (SNSS and non-SNSS); the public GRD covers SNSS hospitals operating GRD (observed panel 65/65/65/65/68/72; fixed panel of 65 and strict hospitalisation as sensitivities). "
                  "The 'F84.0 only' series is identical in both variants. " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    return (out_a, numeric_a, ttl_a, note_a), (out_b, numeric_b, ttl_b, note_b)


# ---------------------------------------------------------------------------
# ST12 — FONASA, ISAPRE, APS
# ---------------------------------------------------------------------------
def st12(D: dict, lang: str):
    fs, isn, ap, fb5 = D["fs"].copy(), D["isn"].copy(), D["ap"].copy(), D["fb5"]
    for c in ["n_rows_raw", "n_exact_duplicate_rows_kept", "total_beneficiaries"]:
        fs[c] = num(fs[c])
    fs["share_beneficiaries_with_5y_band"] = fs.year.map(fb5.share_beneficiaries_with_5y_band)
    fs["share_beneficiaries_with_10y_band"] = fs.year.map(fb5.share_beneficiaries_with_10y_band)
    fs["age_band_5y_derivable_all_bands"] = fs.year.map(fb5.age_band_5y_derivable_all_bands)

    def five_year(r):
        if pd.isna(r.share_beneficiaries_with_5y_band):
            return DASH
        key = "fiveyear_yes" if bool(r.age_band_5y_derivable_all_bands) else "fiveyear_no"
        return T(key, lang, p=fpct(100 * r.share_beneficiaries_with_5y_band, 1, lang))
    age_es = rule_es = (lambda v: LB.tidy_text(v, lang))
    out_a = pd.DataFrame({T("col_year", lang): fs.year, T("col_archive", lang): fs.source_archive, T("col_member", lang): fs.member_file, T("col_encoding", lang): fs.encoding,
                          T("col_rows_raw", lang): [fi(x, lang) for x in fs.n_rows_raw], T("col_dup_kept", lang): [fi(x, lang) for x in fs.n_exact_duplicate_rows_kept],
                          T("col_count_col", lang): fs.count_column, T("col_tramo_col", lang): fs.tramo_column, T("col_region_col", lang): fs.region_column,
                          T("col_has_aps", lang): [yn(v, lang) for v in fs.has_inscrito_aps], T("col_has_tipo", lang): [yn(v, lang) for v in fs.has_tipo_asegurado],
                          T("col_has_dz", lang): [yn(v, lang) for v in fs.has_direccion_zonal], T("col_has_ss", lang): [yn(v, lang) for v in fs.has_servicio_salud],
                          T("col_age_scheme_f", lang): [age_es(v) for v in fs.age_band_scheme], T("col_5y", lang): [five_year(r) for r in fs.itertuples()],
                          T("col_total_benef", lang): [fi(x, lang) for x in fs.total_beneficiaries], T("col_columns", lang): [c.replace("|", " | ") for c in fs["columns"]],
                          T("col_agg_rule", lang): [rule_es(v) for v in fs.aggregation_rule], T("col_sha", lang): fs.sha256.str[:12]})
    numeric_a = fs.rename(columns={"age_band_5y_derivable": "age_band_5y_derivable_any_row_module03"}).copy()
    for c in ["cotizantes", "cargas", "nonatos_sin_clasificar", "beneficiarios_total", "beneficiarios_female", "beneficiarios_male", "beneficiarios_sex_not_informed", "beneficiarios_age_not_informed", "n_cells", "n_all_zero_cells_dropped"]:
        isn[c] = num(isn[c])
    irule = (lambda v: LB.tidy_text(v, lang))
    out_b = pd.DataFrame({T("col_year", lang): isn.year, T("col_file", lang): isn.source_file, T("col_cotizantes", lang): [fi(x, lang) for x in isn.cotizantes], T("col_cargas", lang): [fi(x, lang) for x in isn.cargas],
                          T("col_nonatos", lang): [fi(x, lang) for x in isn.nonatos_sin_clasificar], T("col_benef_total", lang): [fi(x, lang) for x in isn.beneficiarios_total],
                          T("col_benef_f", lang): [fi(x, lang) for x in isn.beneficiarios_female], T("col_benef_m", lang): [fi(x, lang) for x in isn.beneficiarios_male],
                          T("col_sex_ni", lang): [fi(x, lang) for x in isn.beneficiarios_sex_not_informed], T("col_age_ni", lang): [fi(x, lang) for x in isn.beneficiarios_age_not_informed],
                          T("col_cells", lang): [fi(x, lang) for x in isn.n_cells], T("col_zero_cells", lang): [fi(x, lang) for x in isn.n_all_zero_cells_dropped],
                          T("col_rule", lang): [irule(v) for v in isn.rule], T("col_age_note", lang): [irule(v) for v in isn.age_note], T("col_agg_rule", lang): [irule(v) for v in isn.aggregation_rule]})
    numeric_b = isn.copy()
    for c in ["centres_total", "centres_panel", "enrolled_total", "enrolled_panel_1871", "retention_panel_1871", "enrolled_tramo_AD", "enrolled_tramo_X", "enrolled_tramo_missing"]:
        ap[c] = num(ap[c])
    out_c = pd.DataFrame({T("col_year", lang): ap.year, T("col_centres_total", lang): [fi(x, lang) for x in ap.centres_total], T("col_centres_panel", lang): [fi(x, lang) for x in ap.centres_panel],
                          T("col_enrolled_total", lang): [fi(x, lang) for x in ap.enrolled_total], T("col_enrolled_panel", lang): [fi(x, lang) for x in ap.enrolled_panel_1871],
                          T("col_retention", lang): [fpct(100 * x, 2, lang) for x in ap.retention_panel_1871], T("col_tramo_ad", lang): [fi(x, lang) for x in ap.enrolled_tramo_AD],
                          T("col_tramo_x", lang): [fi(x, lang) for x in ap.enrolled_tramo_X], T("col_tramo_missing", lang): [fi(x, lang) for x in ap.enrolled_tramo_missing]})
    numeric_c = ap.copy()
    if lang == "es":
        ttl_a = title(lang, "ST12a", "Esquema de los archivos agregados de beneficiarios FONASA de diciembre por año, 2018–2025: archivo, codificación, columnas, tramos de edad, duplicados aditivos y total de beneficiarios")
        note_a = ("Una fila por archivo anual (corte de diciembre; stock de aseguramiento público). El esquema cambia en 2021 (desaparece TIPO_ASEGURADO), 2023 (TRAMO_FONASA, sin INSCRITO_APS ni DIRECCION_ZONAL, tramos de edad decenales), 2024 (BENEFICIARIOS, REGIÓN, sin SERVICIO_SALUD) y 2025 (codificación UTF-8). "
                  "Las filas duplicadas exactas de 2018–2020 son fragmentos aditivos y se conservan (eliminarlas reduce los totales oficiales). La geografía mezcla comuna de inscripción APS (inscritos) y domicilio (no inscritos). "
                  "Tramos quinquenales derivables = ≥ 99 % de los beneficiarios (todos los tramos informados) se asignan a un tramo quinquenal a partir de los rótulos publicados; "
                  "en 2023 solo el tramo «80 y más» (≈3,5 % de los beneficiarios) es compatible con un esquema quinquenal, por lo que ese año solo permite tramos decenales y las tablas por edad usan las columnas armonizadas decenales. "
                  "La versión numérica conserva el indicador de módulo 03 (verdadero si alguna fila obtiene tramo quinquenal) junto con la participación calculada. " + T("identical_variants", lang))
        ttl_b = title(lang, "ST12b", "Beneficiarios ISAPRE de diciembre por año, 2019–2025, y reglas de armonización de los archivos comunales de la Superintendencia de Salud")
        note_b = ("Stock de diciembre de personas con beneficios vigentes (cotizantes + cargas; + nonatos/sin clasificar en 2019–2020), comuna administrativa del beneficiario (no lugar de atención ni residencia INE). "
                  "2019–2020: archivos .xls con edades simples («Edad 1»..«Edad 100») colapsadas a tramos quinquenales; desde 2021: .xlsx con tramos quinquenales publicados. Las hojas por sexo y la hoja total son vistas duplicadas y nunca se suman; las celdas todo cero se omiten (ausente = 0). "
                  "Los totales reproducen los controles del protocolo. " + T("identical_variants", lang))
        ttl_c = title(lang, "ST12c", "Inscritos en atención primaria (APS) de diciembre por año, 2019–2025: centros, panel continuo de 1.871 centros y retención")
        note_c = ("Stock de diciembre de personas inscritas y validadas por centro APS (cobertura operativa por lugar de atención, no residencia). Panel continuo = 1.871 códigos de centro presentes en los siete años; retención = inscritos del panel / inscritos totales. "
                  "Los grupos de edad y los nombres de variables cambian en 2024 (tramos de 20 años en 2019–2023); tramo X = inscritos sin tramo FONASA A–D. " + T("identical_variants", lang))
    else:
        ttl_a = title(lang, "ST12a", "Schema of the December FONASA beneficiary aggregate files by year, 2018–2025: file, encoding, columns, age bands, additive duplicates and total beneficiaries")
        note_a = ("One row per annual file (December snapshot; public insurance stock). The schema changes in 2021 (TIPO_ASEGURADO dropped), 2023 (TRAMO_FONASA, no INSCRITO_APS or DIRECCION_ZONAL, decadal age bands), 2024 (BENEFICIARIOS, REGIÓN, no SERVICIO_SALUD) and 2025 (UTF-8 encoding). "
                  "Exact duplicate rows in 2018–2020 are additive fragments and are kept (dropping them reduces the official totals). Geography mixes the comuna of APS enrolment (enrolled) and domicile (not enrolled). "
                  "Five-year bands derivable = at least 99% of beneficiaries (all informed bands) can be assigned to a five-year band from the published labels; "
                  "in 2023 only the '80 and over' band (about 3.5% of beneficiaries) is compatible with a five-year scheme, so that year allows 10-year bands only and the age tables use the harmonised 10-year columns. "
                  "The numeric version keeps the module-03 flag (true if any row obtains a five-year band) alongside the computed share. " + T("identical_variants", lang))
        ttl_b = title(lang, "ST12b", "December ISAPRE beneficiaries by year, 2019–2025, and harmonisation rules of the Superintendencia de Salud comuna files")
        note_b = ("December stock of persons with valid benefits (contributors + dependants; + unborn/unclassified in 2019–2020), administrative comuna of the beneficiary (neither place of care nor INE residence). "
                  "2019–2020: .xls files with single ages ('Edad 1'..'Edad 100') collapsed to five-year bands; from 2021: .xlsx with published five-year bands. Sex sheets and the total sheet are duplicate views and are never summed; all-zero cells are omitted (absent = 0). "
                  "Totals reproduce the protocol controls. " + T("identical_variants", lang))
        ttl_c = title(lang, "ST12c", "December primary-care (APS) enrolment by year, 2019–2025: centres, continuous panel of 1,871 centres and retention")
        note_c = ("December stock of persons enrolled and validated per APS centre (operational coverage by place of care, not residence). Continuous panel = 1,871 centre codes present in all seven years; retention = panel enrolled / total enrolled. "
                  "Age groups and variable names change in 2024 (20-year bands in 2019–2023); tramo X = enrolled without a FONASA tramo A–D. " + T("identical_variants", lang))
    return (out_a, numeric_a, ttl_a, note_a), (out_b, numeric_b, ttl_b, note_b), (out_c, numeric_c, ttl_c, note_c)


# ---------------------------------------------------------------------------
# ST13 — A05 por edad y sexo
# ---------------------------------------------------------------------------
A05_AGE_ORDER = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]


def st13(D: dict, variant: str, lang: str):
    a = D["a05"].copy()
    a["year"] = a.year.astype(int)
    a["count"] = num(a["count"])
    a["n_reporting_establishments"] = num(a.n_reporting_establishments)
    fam_codes = "+".join(CFG.VARIANTS[variant]["a05_entry"])
    rp = D["rp"][(D["rp"].module == "A05") & (D["rp"].measure == "annual_sum")].copy()
    rp["year"] = rp.year.astype(int)
    rp["total"] = num(rp.total)
    col01 = {"broad": rp[(rp.code == "06902600") & (rp.variant == "broad_pre2021")].set_index("year").total,
             "family": rp[(rp.code == fam_codes) & (rp.variant == variant)].set_index("year").total,
             "strict": rp[(rp.code == "05990022") & (rp.variant == "strict_autism")].set_index("year").total}
    blocks = [("broad", T("st13_block_broad", lang), a[(a.variant == "single_code") & (a.category == "broad_pdd") & (a.flow == "entry")], [2019, 2020]),
              ("family", T("st13_block_family", lang, codes=fam_codes), a[(a.variant == variant) & (a.flow == "entry")], [2021, 2022, 2023, 2024, 2025]),
              ("strict", T("st13_block_strict", lang), a[(a.variant == "single_code") & (a.category == "autism") & (a.flow == "entry")], [2021, 2022, 2023, 2024, 2025])]
    sex_lab = {"Hombres": T("sex_m", lang), "Mujeres": T("sex_f", lang)}
    cb, cs, ca = T("col_block", lang), T("col_sex", lang), T("col_age_group", lang)
    rows = []
    for key, label, g, years in blocks:
        for sex in ["Hombres", "Mujeres"]:
            s = g[g.sex == sex]
            for age in A05_AGE_ORDER + ["total"]:
                c = s[s.age_group == age].set_index("year")["count"]
                row = {cb: label, cs: sex_lab[sex], ca: T("st13_total_row", lang) if age == "total" else age}
                for y in YEARS_REM:
                    row[str(y)] = T("na", lang) if y not in years else (fi(c.loc[y], lang) if y in c.index and not pd.isna(c.loc[y]) else T("not_reported", lang))
                rows.append(row)
            ssum = s[s.age_group != "total"].groupby("year")["count"].sum(min_count=1)
            row = {cb: label, cs: sex_lab[sex], ca: T("st13_sum_row", lang)}
            for y in YEARS_REM:
                row[str(y)] = T("na", lang) if y not in years else fi(ssum.loc[y] if y in ssum.index else np.nan, lang)
            rows.append(row)
        tot = g[g.age_group == "total"].groupby("year")["count"].sum(min_count=1)
        row = {cb: label, cs: T("total", lang), ca: T("st13_total_row", lang)}
        for y in YEARS_REM:
            row[str(y)] = T("na", lang) if y not in years else fi(tot.loc[y] if y in tot.index else np.nan, lang)
        rows.append(row)
        c1 = col01[key]
        row = {cb: label, cs: T("total", lang), ca: T("st13_col01_row", lang)}
        for y in YEARS_REM:
            row[str(y)] = T("na", lang) if y not in years else fi(c1.loc[y] if y in c1.index else np.nan, lang)
        rows.append(row)
        rep = g.groupby("year").n_reporting_establishments.max()
        row = {cb: label, cs: "", ca: T("st13_reporting", lang)}
        for y in YEARS_REM:
            row[str(y)] = T("na", lang) if y not in years else fi(rep.loc[y] if y in rep.index else np.nan, lang)
        rows.append(row)
    out = pd.DataFrame(rows)
    numeric = a[(a.variant == variant) | ((a.variant == "single_code") & (a.category.isin(["autism", "broad_pdd"])))].copy()
    numeric["count"] = numeric["count"].astype("Int64")
    numeric["n_reporting_establishments"] = numeric.n_reporting_establishments.astype("Int64")
    numeric = numeric.sort_values(["flow", "variant", "category", "year", "sex", "age_group"]).reset_index(drop=True)
    if lang == "es":
        ttl = title(lang, "ST13", "Ingresos al programa de salud mental por autismo y familia TGD (REM A05) por grupo de edad y sexo y año, 2019–2025, con establecimientos reportantes", variant)
        note = ("Unidad: ingresos reportados (flujo anual = suma de meses de las celdas edad × sexo COL04–COL37; el total informado usa COL02 hombres y COL03 mujeres y puede diferir de la suma de celdas cuando hay celdas vacías). "
                "Bloques por era de definición: TGD amplio 06902600 (2019–2020, contiene síndrome de Rett de forma inseparable; sensibilidad), familia TGD de la variante (2021–2025, suma de los códigos indicados) y autismo estricto 05990022 (2021–2025, idéntico en ambas variantes); «n/e» = año fuera de la era (no estimable); "
                "«no informado» = ninguna celda presente. Establecimientos reportantes = establecimientos con al menos una fila del código en el año (lugar de atención). Los egresos clínicos (05990027–31, 05225000) están en la versión numérica. "
                "El total COL01 es la serie usada en las tablas principales (rem_pathway_annual); pequeñas diferencias entre COL01, COL02+COL03 y la suma de celdas de edad (p. ej. autismo estricto 2025: 13.155 frente a 13.156) son inconsistencias internas de filas fuente y no se corrigen. "
                "Los ingresos cuentan eventos administrativos, no personas ni incidencia. " + T("pandemic_law", lang))
    else:
        ttl = title(lang, "ST13", "Mental-health programme entries for autism and the PDD family (REM A05) by age group, sex and year, 2019–2025, with reporting establishments", variant)
        note = ("Unit: reported entries (annual flow = sum of months of the age × sex cells COL04–COL37; the reported total uses COL02 males and COL03 females and may differ from the sum of cells when cells are empty). "
                "Blocks by definition era: broad PDD 06902600 (2019–2020, Rett syndrome inseparable; sensitivity), PDD family of the variant (2021–2025, sum of the listed codes) and strict autism 05990022 (2021–2025, identical in both variants); 'n/e' = year outside the era (not estimable); "
                "'not reported' = no cell present. Reporting establishments = establishments with at least one row of the code in the year (place of care). Clinical discharges (05990027–31, 05225000) are in the numeric version. "
                "The COL01 total is the series used in the main tables (rem_pathway_annual); small differences between COL01, COL02+COL03 and the sum of age cells (e.g. strict autism 2025: 13,155 versus 13,156) are internal inconsistencies of source rows and are not corrected. "
                "Entries count administrative events, not persons or incidence. " + T("pandemic_law", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# ST14 — P2/P6 junio frente a diciembre
# ---------------------------------------------------------------------------
def st14(D: dict, variant: str, lang: str):
    rp = D["rp"].copy()
    rp["year"] = rp.year.astype(int)
    for c in ["total", "n_reporting_establishments", "n_stable_panel_establishments", "stable_panel_total"]:
        rp[c] = num(rp[c])
    p = rp[rp.series == "P"]
    series = [("P2500500", "single_code", code_label("P2500500", lang)), ("P2501878", "single_code", code_label("P2501878", lang)),
              ("P6223000", "broad_pre2021", code_label("P6223000", lang)), ("P6223380", "broad_pre2021", code_label("P6223380", lang)),
              ("+".join(CFG.VARIANTS[variant]["p6_primary"]), variant, T("p6_family_primary", lang)), ("+".join(CFG.VARIANTS[variant]["p6_specialty"]), variant, T("p6_family_specialty", lang)),
              ("P6241010", "strict_autism", T("p6_strict_primary", lang)), ("P6241060", "strict_autism", T("p6_strict_specialty", lang))]
    rows, numeric_rows = [], []
    for code, var, label in series:
        g = p[(p.code == code) & (p.variant == var)]
        dec = g[g.measure == "december_stock"].set_index("year")
        jun = g[g.measure == "june_stock"].set_index("year")
        for y in sorted(dec.index):
            d = dec.loc[y]
            j = jun.loc[y] if y in jun.index else None
            j_missing = j is None or (pd.isna(j.total) and (pd.isna(j.n_reporting_establishments) or j.n_reporting_establishments == 0))
            pct = np.nan if j_missing or pd.isna(d.total) or d.total == 0 else 100 * j.total / d.total
            rows.append({T("col_series", lang): label, T("col_codes", lang): code, T("col_era", lang): d.era, T("col_year", lang): y,
                         T("col_dec_stock", lang): fi(d.total, lang), T("col_dec_estab", lang): fi(d.n_reporting_establishments, lang),
                         T("col_stable_n", lang): fi(d.n_stable_panel_establishments, lang), T("col_stable_stock", lang): fi(d.stable_panel_total, lang),
                         T("col_jun_stock", lang): T("not_reported", lang) if j_missing else fi(j.total, lang),
                         T("col_jun_estab", lang): T("not_reported", lang) if j_missing else fi(j.n_reporting_establishments, lang),
                         T("col_jun_pct", lang): fpct(pct, 1, lang)})
            numeric_rows.append(dict(variant=variant, series_key=var, code=code, era=d.era, year=y, december_stock=d.total, december_reporting_establishments=d.n_reporting_establishments,
                                     december_stable_panel_establishments=d.n_stable_panel_establishments, december_stable_panel_stock=d.stable_panel_total,
                                     june_stock=np.nan if j_missing else j.total, june_reporting_establishments=np.nan if j_missing else j.n_reporting_establishments,
                                     june_stable_panel_establishments=np.nan if j_missing else j.n_stable_panel_establishments, june_stable_panel_stock=np.nan if j_missing else j.stable_panel_total,
                                     june_reported=not j_missing, june_pct_of_december=pct))
    out = pd.DataFrame(rows)
    numeric = pd.DataFrame(numeric_rows)
    for c in ["december_stock", "december_reporting_establishments", "december_stable_panel_establishments", "december_stable_panel_stock", "june_stock", "june_reporting_establishments",
              "june_stable_panel_establishments", "june_stable_panel_stock"]:
        numeric[c] = numeric[c].astype("Int64")
    if lang == "es":
        ttl = title(lang, "ST14", "Población bajo control por autismo y TGD en REM Serie P (P2 NANEAS y P6 salud mental): stock de diciembre frente a stock de junio por año, 2019–2025, con establecimientos reportantes y panel estable", variant)
        note = ("Unidad: personas bajo control (stock semestral, COL01 de MES = 12 y MES = 06; los semestres nunca se suman ni se promedian). Diciembre es el análisis principal y junio una sensibilidad; junio como % de diciembre describe la estabilidad del stock dentro del año. "
                "Establecimientos reportantes = establecimientos con fila del código en ese semestre; panel estable = establecimientos con fila de diciembre en todos los años de la era del código (stock del panel en diciembre). "
                "Eras: P2 TEA 2019–2025; P2 NANEAS total desde diciembre de 2023 (junio de 2023 no reportado: sin filas, no cero); P6 TGD amplio 2019–2020 (contiene Rett de forma inseparable) frente a familia TGD de la variante y autismo estricto desde 2021 (quiebre de definición; nunca se unen en una serie continua). "
                "Junio de 2020 tiene muy pocos establecimientos (disrupción pandémica del reporte). " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    else:
        ttl = title(lang, "ST14", "Population under control for autism and PDD in REM Series P (P2 NANEAS and P6 mental health): December stock versus June stock by year, 2019–2025, with reporting establishments and stable panel", variant)
        note = ("Unit: persons under control (semiannual stock, COL01 of MES = 12 and MES = 06; semesters are never summed or averaged). December is the main analysis and June a sensitivity; June as % of December describes within-year stock stability. "
                "Reporting establishments = establishments with a row for the code in that semester; stable panel = establishments with a December row in every year of the code's era (December stock of the panel). "
                "Eras: P2 ASD 2019–2025; P2 total NANEAS from December 2023 (June 2023 not reported: no rows, not zero); P6 broad PDD 2019–2020 (Rett inseparable) versus the variant's PDD family and strict autism from 2021 (definition break; never joined into one continuous series). "
                "June 2020 has very few establishments (pandemic reporting disruption). " + T("admin_note", lang) + " " + T("pandemic_law", lang))
    return out, numeric, ttl, note


# ---------------------------------------------------------------------------
# Escritura, controles y ejecución
# ---------------------------------------------------------------------------
def write_table(name: str, variant: str, lang: str, out: pd.DataFrame, numeric: pd.DataFrame | None, ttl: str, note: str, titles: dict, written: dict, numeric_suffix: str = "_numeric") -> None:
    tdir = CFG.OUT / variant / lang / "tables"
    tdir.mkdir(parents=True, exist_ok=True)
    # La ventana de años se retipografía AQUÍ, el único punto por el que pasa todo lo que este módulo
    # IMPRIME. Sobre una COPIA, porque las tablas compartidas entre variantes (`shared[lang]`) se escriben
    # dos veces y no deben mutarse; nunca sobre `numeric`, que es la copia de máquina; y nunca sobre el
    # compañero `_long` de la ST6, que es transcripción literal del diccionario JUNAEB (ver VERBATIM_KEYS).
    out, conv, kept = yspan_frame(out, lang)
    t_before = C.count_hyphen_ranges(ttl) + C.count_hyphen_ranges(note)
    t_after = C.count_kept_hyphens(ttl) + C.count_kept_hyphens(note)
    ttl, note = yspan_prose(ttl), yspan_prose(note)
    c = YSPAN_COUNTS.setdefault(f"{variant}|{lang}", {"converted": 0, "kept": 0})
    c["converted"] += conv + t_before
    c["kept"] += kept + t_after
    # La exención viaja CON el marco: `atomic_write_csv` vuelve a pasar la regla sobre toda tabla impresa
    # (es la red que cubre los módulos que no la llaman) y sin esta marca retipografiaría precisamente las
    # columnas de transcripción literal que aquí se acaban de respetar.
    out.attrs[C.RANGE_DASH_EXEMPT] = tuple(verbatim_headers(lang))
    p = C.atomic_write_csv(out, tdir / f"{name}.csv")
    entry = {"path": str(p), "rows": int(len(out)), "columns": int(out.shape[1])}
    if numeric is not None:
        if numeric_suffix != "_numeric":
            # El compañero `_long` de la ST6 no es la copia de máquina sino la TRANSCRIPCIÓN LITERAL
            # completa del diccionario JUNAEB: se imprime, pero retocar una cita rompe la cita.
            numeric = numeric.copy()
            numeric.attrs[C.RANGE_DASH_EXEMPT] = tuple(str(c) for c in numeric.columns)
        pn = C.atomic_write_csv(numeric, tdir / f"{name}{numeric_suffix}.csv")
        entry["numeric"] = str(pn)
        entry["numeric_rows"] = int(len(numeric))
    titles[name] = {"title": ttl, "note": note}
    written[f"{name}|{variant}|{lang}"] = entry


def ctl(name, key, expected, observed, note="", tol=0.0):
    exp = np.nan if expected is None else float(expected)
    obs = np.nan if observed is None or (isinstance(observed, float) and np.isnan(observed)) else float(observed)
    if np.isnan(exp):
        status, ad, rd_ = "info", np.nan, np.nan
    elif np.isnan(obs):
        status, ad, rd_ = "missing", np.nan, np.nan
    else:
        ad = obs - exp
        rd_ = ad / exp if exp else (0.0 if ad == 0 else np.nan)
        status = "ok" if (abs(rd_) <= tol if exp else ad == 0) else "differs"
    return dict(name=name, key=str(key), expected=exp, observed=obs, abs_diff=ad, rel_diff=rd_, status=status, note=note)


def build_controls(D: dict, agg: pd.DataFrame, st2_incons: int, prov: dict, timings: dict) -> pd.DataFrame:
    rows = []
    fp, hy = D["fp"], D["hy"]
    rows.append(ctl("st1_fixed_panel_hospitals", "all", 65, int((fp.in_fixed_panel == "True").sum()),
                    f"{C.fixed_panel_gloss('es', 'membership')} (grd_fixed_panel_hospitals.csv)"))
    h = hy[hy.variant == "con_rett"].copy()
    h["year"] = h.year.astype(int)
    for c in ["n_episodes_total", "n_f84_any", "n_f84_principal"]:
        h[c] = num(h[c])
    for y, v in CFG.CONTROLS["grd_hospitals_observed"].items():
        rows.append(ctl("st1_hospitals_observed", y, v, h[h.year == y].COD_HOSPITAL.nunique(), "hospitales con ≥1 episodio en grd_hospital_year.csv"))
    for y, v in CFG.CONTROLS["grd_records_total"].items():
        rows.append(ctl("st1_episodes_total_observed", y, v, h[h.year == y].n_episodes_total.sum(), "suma de episodios por hospital (panel observado)"))
    for y, v in CFG.CONTROLS["grd_f84_any"].items():
        rows.append(ctl("st1_f84_any_observed_con_rett", y, v, h[h.year == y].n_f84_any.sum(), "suma de episodios con F84 cualquier posición por hospital (con_rett)"))
    for y, v in CFG.CONTROLS["grd_f84_any_panel65"].items():
        rows.append(ctl("st1_f84_any_fixed65_con_rett", y, v, h[(h.year == y) & (h.in_fixed_panel == "True")].n_f84_any.sum(), "panel fijo de 65 hospitales"))
    for y, v in CFG.CONTROLS["grd_f84_principal"].items():
        rows.append(ctl("st1_f84_principal_observed_con_rett", y, v, h[h.year == y].n_f84_principal.sum(), "F84 en DIAGNOSTICO1 (serie separada)"))
    rows.append(ctl("st2_dictionary_inconsistencies", "all", 0, st2_incons, "códigos hallados fuera de su era o ausentes dentro de ella (rem_code_dictionary_check.csv)"))
    rows.append(ctl("st2_codes_checked", "all", None, D["dc"].code.nunique(), "códigos REM verificados contra el diccionario anual"))
    p2 = agg[(agg.code == "P2500500")].set_index("year")
    for y, v in CFG.CONTROLS["p2_establishments_december"].items():
        rows.append(ctl("st3_p2_december_reporters", y, v, p2.loc[y, "n_december_row"] if y in p2.index else np.nan, "establecimientos con fila de diciembre de P2500500 (rem_establishment_year.csv)"))
    # coherencia ST3 frente a rem_pathway_annual
    a = agg.dropna(subset=["n_reporting_rem_pathway_annual"])
    mism = int(((np.where(a.series == "P", a.n_december_row, a.n_establishments_any_row)) != a.n_reporting_rem_pathway_annual.astype(int)).sum())
    rows.append(ctl("st3_reporting_n_matches_rem_pathway_annual", "all", 0, mism, f"celdas código-año cuyo N reportante difiere entre rem_establishment_year (agregado) y rem_pathway_annual ({len(a)} comparadas)"))
    rows.append(ctl("st4_unmatched_rows", "all", None, len(D["un"]), "filas de comuna_unmatched.csv (marcadores no geográficos)"))
    rows.append(ctl("st4_fuzzy_matches", "all", 0, int((~D["nm"].match_method.isin(["exact", "alias"])).sum()), "ningún enlace difuso: solo exacto o alias explícito"))
    rows.append(ctl("st7_sha_mismatches_provenance", "all", 0, prov["n_mismatch"], "artefactos cuyo SHA-256 difiere del manifiesto (data_provenance.csv)"))
    rows.append(ctl("st7_sha_mismatches_manifest_checks", "all", 0, prov["n_pm_bad"], "entradas artefacto × manifiesto con SHA distinto"))
    rows.append(ctl("st7_artefacts", "all", None, len(D["dp"]), "artefactos en data_provenance.csv"))
    fb5 = D["fb5"]
    rows.append(ctl("st12_fonasa_years_5y_derivable", "all", 7, int(fb5.age_band_5y_derivable_all_bands.sum()),
                    "años 2018–2025 con ≥99 % de beneficiarios asignables a tramo quinquenal: todos salvo 2023 (solo tramos decenales)"))
    rows.append(ctl("st12_fonasa_2023_5y_derivable", "2023", 0, int(bool(fb5.age_band_5y_derivable_all_bands.get("2023", False))),
                    f"2023: {100 * float(fb5.share_beneficiaries_with_5y_band.get('2023', np.nan)):.1f} % de beneficiarios con tramo quinquenal (solo «80 y más»); el indicador any-row de módulo 03 es True"))
    rows.append(ctl("st12_fonasa_2023_10y_share", "2023", None, round(float(fb5.share_beneficiaries_with_10y_band.get("2023", np.nan)), 4), "participación con tramo decenal en 2023 (informativo)"))
    ds = D["ds"]
    rows.append(ctl("st11_deis_f84_diag2", "all", 0, num(ds.f84_diag2).sum(), "F84 nunca aparece en DIAG2 (causa externa): DEIS 'cualquier posición' = 'principal'"))
    a05 = D["a05"]
    strict = a05[(a05.variant == "single_code") & (a05.category == "autism") & (a05.flow == "entry") & (a05.age_group == "total")].copy()
    strict["year"] = strict.year.astype(int)
    strict["count"] = num(strict["count"])
    rp = D["rp"].copy()
    rp["year"] = rp.year.astype(int)
    rp["total"] = num(rp.total)
    c1 = rp[(rp.code == "05990022") & (rp.variant == "strict_autism") & (rp.measure == "annual_sum")].set_index("year").total
    for y, v in CFG.CONTROLS["a05_autism_entries"].items():
        rows.append(ctl("st13_a05_autism_entries_total_col01", y, v, c1.loc[y] if y in c1.index else np.nan, "total COL01 de 05990022 (rem_pathway_annual.csv), fila «Total COL01» de la ST13"))
        obs = strict[strict.year == y]["count"].sum()
        rows.append(ctl("st13_a05_autism_entries_total_col02_col03", y, None, obs,
                        f"suma COL02 + COL03 de 05990022 (rem_a05_age_sex_annual.csv); protocolo (COL01) = {v}; diferencia {int(obs - v):+d} = inconsistencia interna de filas fuente, no corregida"))

    def stock(code, var, measure, y):
        s = rp[(rp.code == code) & (rp.variant == var) & (rp.measure == measure) & (rp.year == y)]
        return s.total.iloc[0] if len(s) else np.nan
    for y, v in CFG.CONTROLS["p2_tea_december"].items():
        rows.append(ctl("st14_p2_tea_december", y, v, stock("P2500500", "single_code", "december_stock", y), "stock de diciembre P2500500"))
    for y, v in CFG.CONTROLS["p2_naneas_total_december"].items():
        rows.append(ctl("st14_p2_naneas_total_december", y, v, stock("P2501878", "single_code", "december_stock", y), "stock de diciembre P2501878"))
    for y, v in CFG.CONTROLS["p6_primary_december"].items():
        obs = stock("P6223000", "broad_pre2021", "december_stock", y) if y <= 2020 else stock("P6241010", "strict_autism", "december_stock", y)
        rows.append(ctl("st14_p6_primary_december", y, v, obs, "P6223000 (TGD amplio) 2019–2020; P6241010 (autismo estricto) desde 2021: eras distintas, nunca una serie continua"))
    for y, v in CFG.CONTROLS["p6_specialty_december"].items():
        obs = stock("P6223380", "broad_pre2021", "december_stock", y) if y <= 2020 else stock("P6241060", "strict_autism", "december_stock", y)
        rows.append(ctl("st14_p6_specialty_december", y, v, obs, "P6223380 (TGD amplio) 2019–2020; P6241060 (autismo estricto) desde 2021"))
    rows.append(ctl("st14_p2501878_june_2023_reported", "2023", 0, int(num(rp[(rp.code == "P2501878") & (rp.measure == "june_stock") & (rp.year == 2023)].n_reporting_establishments).fillna(0).sum()),
                    "junio de 2023 sin filas para P2501878: se muestra como «no informado», no como cero"))
    rows.append(ctl("runtime_seconds", "all", None, round(timings.get("total", np.nan), 1), "segundos totales del módulo"))
    return pd.DataFrame(rows)


#: La medición de la ventana de años va al RUNLOG, no a los controles. Un control nuevo cambia el recuento
#: de `09b_tables_supplementary_controls.csv`, y `outputs/controls/controls_summary.csv` —la fotografía que
#: consolida el módulo 07— dejaría de coincidir fila a fila con él: `tests/test_self_counts.py` lo comprueba
#: y falla, y el total de comprobaciones del pipeline que imprime el apéndice cambiaría por una corrección
#: de tipografía. La medición se escribe entera en el runlog y, si el residuo en prosa no es cero, entra en
#: `issues` y el módulo lo avisa por pantalla. Promoverla a control es barato el día que se vuelva a
#: consolidar el módulo 07.
def year_window_report() -> dict:
    """Intervalos convertidos, conservados y residuo, releyendo los archivos ya escritos.

    Desde la fase 4j mide TODO intervalo numérico de lectura (banda de edad, tramo y ventana de años), no
    sólo la ventana: es la misma regla de `common` con la que se escribieron."""
    rep: dict = {"converted_by_variant_language": {k: dict(v) for k, v in sorted(YSPAN_COUNTS.items())},
                 "hyphen_left_in_prose": {}, "hyphen_left_in_machine_keys": {}}
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            tdir = CFG.OUT / variant / lang / "tables"
            skip = verbatim_headers(lang)
            prose = machine = 0
            for name in TABLE_NAMES:
                path = tdir / f"{name}.csv"
                if not path.is_file():
                    continue
                with path.open(encoding="utf-8", newline="") as fh:
                    reader = csv.reader(fh)
                    header = next(reader, [])
                    keep = [i for i, h in enumerate(header) if h not in skip]
                    for row in [header] + list(reader):
                        for i in keep:
                            if i >= len(row):
                                continue
                            prose += C.count_hyphen_ranges(row[i])
                            machine += C.count_kept_hyphens(row[i])
            rep["hyphen_left_in_prose"][f"{variant}|{lang}"] = prose
            rep["hyphen_left_in_machine_keys"][f"{variant}|{lang}"] = machine
    return rep


def main() -> int:
    t0 = time.time()
    timings, issues, written = {}, [], {}
    t = time.time()
    D = load_inputs()
    timings["load_inputs"] = round(time.time() - t, 2)
    t = time.time()
    agg, mod = st3_aggregate(D)
    timings["st3_aggregate"] = round(time.time() - t, 2)

    # Tablas idénticas entre variantes: se calculan una vez por idioma y se escriben en ambas carpetas.
    shared: dict[str, dict] = {}
    st2_incons = 0
    prov = {}
    for lang in CFG.LANGUAGES:
        t = time.time()
        s2 = st2(D, lang)
        st2_incons = s2[4]
        s3 = st3(D, agg, mod, lang)
        s4a, s4b = st4(D, lang)
        s5 = st5(D, lang)
        s6 = st6(D, lang)
        s7, s7b, prov = st7(D, lang)
        s12a, s12b, s12c = st12(D, lang)
        shared[lang] = {"ST2_rem_code_dictionary": s2[:4], "ST3_rem_reporting_establishments": s3, "ST4a_comuna_crosswalk_summary": s4a, "ST4b_comuna_unmatched": s4b,
                        "ST5_survey_items": s5, "ST6_junaeb_items": s6, "ST7_provenance": s7, "ST7b_manifest_checks": s7b,
                        "ST12a_fonasa_schema": s12a, "ST12b_isapre_rules": s12b, "ST12c_aps_panel": s12c}
        timings[f"shared_{lang}"] = round(time.time() - t, 2)

    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            t = time.time()
            titles: dict = {}
            for name, (out, numeric, ttl, note) in shared[lang].items():
                suffix = "_long" if name == "ST6_junaeb_items" else "_numeric"
                write_table(name, variant, lang, out, numeric, ttl, note, titles, written, numeric_suffix=suffix)
            o, n_, tt, nt = st1(D, variant, lang)
            write_table("ST1_grd_hospital_panel", variant, lang, o, n_, tt, nt, titles, written)
            o, n_, tt, nt = st8(D, variant, lang)
            write_table("ST8_grd_identifier_audit", variant, lang, o, n_, tt, nt, titles, written)
            o, n_, tt, nt = st9(D, variant, lang)
            write_table("ST9_grd_age_sex", variant, lang, o, n_, tt, nt, titles, written)
            o, n_, tt, nt = st10(D, variant, lang)
            write_table("ST10_grd_f84_subcodes", variant, lang, o, n_, tt, nt, titles, written)
            (oa, na, ta, nta), (ob, nb, tb, ntb) = st11(D, variant, lang)
            write_table("ST11a_deis_annual", variant, lang, oa, na, ta, nta, titles, written)
            write_table("ST11b_deis_vs_grd", variant, lang, ob, nb, tb, ntb, titles, written)
            o, n_, tt, nt = st13(D, variant, lang)
            write_table("ST13_a05_age_sex", variant, lang, o, n_, tt, nt, titles, written)
            o, n_, tt, nt = st14(D, variant, lang)
            write_table("ST14_p2_p6_june_december", variant, lang, o, n_, tt, nt, titles, written)
            merge_json(CFG.OUT / variant / lang / "tables" / "titles.json", titles)
            timings[f"{variant}_{lang}"] = round(time.time() - t, 2)
            print(f"[{MODULE}] {variant}/{lang}: {len(titles)} tablas escritas en {timings[f'{variant}_{lang}']:.1f} s", flush=True)

    timings["total"] = round(time.time() - t0, 2)
    controls = build_controls(D, agg, st2_incons, prov, timings)
    for r in controls[controls.status == "differs"].itertuples():
        issues.append(f"control difiere: {r.name} [{r.key}] esperado {r.expected} observado {r.observed}")
    for r in controls[controls.status == "missing"].itertuples():
        issues.append(f"control sin valor observado: {r.name} [{r.key}]")
    yw = year_window_report()
    for key, left in yw["hyphen_left_in_prose"].items():
        if left:
            issues.append(f"ventana de años con guion fuera de una clave de máquina: {left} en {key}")
    print(f"[{MODULE}] ventana de años: "
          f"{sum(c['converted'] for c in YSPAN_COUNTS.values())} convertidas a raya, "
          f"{sum(c['kept'] for c in YSPAN_COUNTS.values())} conservadas con guion", flush=True)
    ctl_path = C.atomic_write_csv(controls, CONTROLS_DIR / f"{MODULE}_controls.csv")
    runlog = {"module": MODULE, "year_windows": yw, "script": str(Path(__file__).resolve()), "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seconds_total": timings["total"],
              "timings_seconds": timings, "inputs": {k: str(CFG.TIDY / f"{k}.csv") for k in ["grd_fixed_panel_hospitals", "grd_hospital_year", "rem_code_dictionary_check", "rem_establishment_year",
                                                                                               "comuna_unmatched", "comuna_name_matches", "comuna_crosswalk", "survey_items_dictionary", "junaeb_items_dictionary",
                                                                                               "junaeb_tea_year_level", "data_provenance", "provenance_manifest_checks", "grd_identifier_audit", "grd_age_sex_year",
                                                                                               "grd_subcode_year", "deis_year_summary", "deis_vs_grd_year", "fonasa_schema_by_year", "isapre_beneficiaries_national_year",
                                                                                               "aps_panel", "rem_a05_age_sex_annual", "rem_pathway_annual", "fonasa_beneficiaries_comuna_year"]},
              "outputs": written, "controls": str(ctl_path), "controls_status": controls.status.value_counts().to_dict(), "issues": issues}
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    print(controls[["name", "key", "expected", "observed", "status"]].to_string(index=False), flush=True)
    for i in issues:
        print(f"[{MODULE}] aviso: {i}", flush=True)
    print(f"[{MODULE}] {len(written)} archivos de tabla; controles: {runlog['controls_status']}; listo en {timings['total']:,.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
