# -*- coding: utf-8 -*-
"""supplementary_material.py — inventario bilingüe y constructor de la PARTE SUPLEMENTARIA (módulo 17).

Fuente única de verdad de:

  * el orden y la agrupación temática de las láminas y tablas suplementarias
    (`FIGURE_GROUPS`, `TABLE_GROUPS`, `METHODS_TABLES`);
  * la norma de lámina de la fase 4c —lienzo vertical de 180 × 245 mm a 600 dpi, rejilla de 3 × 2 y
    seis paneles como máximo, letras de panel en minúscula— y las listas explícitas de lo que todavía
    no la cumple (`PLATE_PX`, `PLATES_PENDING_STANDARD`, `CAPTIONS_PENDING_LOWERCASE`,
    `LEGACY_UNREGISTERED_PLATES`), que `tests/test_supplementary_registry.py` comprueba archivo por
    archivo en las dos variantes y los dos idiomas; la lista de tolerancia se comprueba además a sí misma
    —`stale_legacy_unregistered_plates()`, exigida por `material_blocks()`— para que no siga nombrando una
    lámina que ningún módulo escribe ya;
  * la frase de presentación bilingüe de cada lámina (`FIGURE_INTRO`), que indica qué muestra,
    su unidad y su denominador antes de la leyenda autónoma que viene de `captions.json`;
  * el texto de encabezado, la nota y el índice de la parte suplementaria;
  * el constructor `material_blocks(lang, variant, V, R)`, que devuelve los bloques de
    `docx_builder` con (a) la metodología extendida de `prose_methods_extended.methods_blocks`
    —todas las ecuaciones numeradas y citadas—, (b) las láminas suplementarias agrupadas por tema
    y (c) las tablas suplementarias.

`prose_en.supplementary_part()` y `prose_es.supplementary_part()` delegan aquí, de modo que el
documento inglés y el español contienen exactamente los mismos ítems, en el mismo orden, con la
misma numeración (Figura/Figure S1, S2, … y Tabla/Table S1, S2, …) y con las mismas cifras: la
prueba de paridad numérica entre idiomas exige que estas frases no introduzcan ningún número
distinto del propio rótulo.

Reglas heredadas y respetadas en cada frase de este archivo: los recuentos son reconocimiento
administrativo, nunca prevalencia ni incidencia; el resultado GRD es «episodios con F84
documentado»; las fuentes no se enlazan por persona (ruta administrativa agregada, sin cascada ni
cocientes entre fuentes); stocks y flujos no comparten eje; lugar de atención y residencia no se
mezclan sin nota explícita; las eras de definición REM nunca se unen con una línea; la Ley 21.545
(marzo de 2023) es contexto de política, nunca una intervención con efecto estimable.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import config as CFG  # noqa: E402
import prose_methods_extended as PME  # noqa: E402

LANGS = ("es", "en")

# ---------------------------------------------------------------------------
# Norma de lámina (fase 4c) y estado de su aplicación
# ---------------------------------------------------------------------------
# Toda lámina multipanel —del artículo y del suplemento— se dibuja en un lienzo VERTICAL de
# 180 × 245 mm a 600 dpi (4251 × 5787 px) a escala 1:1, para que se imprima una lámina por página sin
# reducirla, con una rejilla de tres filas por dos columnas, seis paneles como máximo y letras de panel
# en MINÚSCULA (a, b, c, d, e, f) en la lámina, en la leyenda y en los dos idiomas, como pide la revista.
# Una lámina de cuatro o cinco paneles conserva la rejilla y usa la celda libre para su leyenda, sus notas
# o un panel que se gane el sitio; una que necesitaría más de seis se DIVIDE en láminas consecutivas, y
# entonces la división se anuncia en `outputs/phase4c_manifest_<tarea>.json` y se fusiona en este registro,
# que renumera por orden de impresión. Ninguna de las cuatro tareas de diseño de la fase 4c añadió, dividió
# ni renombró una lámina: `FIGURE_ORDER` y `TABLE_ORDER` siguen teniendo 54 y 125 ítems.
#
# Estas constantes existen para que `tests/test_supplementary_registry.py` compruebe la norma sobre los
# ARCHIVOS que el registro imprime, no sobre el parámetro con que se pidió el dibujo.
PLATE_W_MM, PLATE_H_MM, PLATE_DPI = 180.0, 245.0, 600
PLATE_PX: tuple[int, int] = (4251, 5787)   # 180 × 245 mm a 600 dpi, guardado sin recorte
PLATE_MAX_PANELS = 6
PLATE_MIN_PT = 6.0                         # nada por debajo de 6 pt, tampoco en las anotaciones

#: Láminas registradas pendientes de reconstruir a la norma vertical. La lista está VACÍA: las quince del
#: primer grupo temático —las últimas que quedaban, dibujadas a 433–444 mm y reducidas al ancho de la caja
#: de texto— se rehicieron a 180 × 245 mm con la rejilla de 3 × 2 y letras minúsculas en
#: `06_models.py`, `08a_figures_grd.py`, `08b_figures_rem.py` y `08c_figures_triangulation.py`. La prueba
#: exige que ninguna lámina FUERA de esta lista incumpla la norma, de modo que vaciarla aprieta la guarda.
PLATES_PENDING_STANDARD: tuple[str, ...] = ()

#: Leyendas que todavía abren con una referencia de panel en MAYÚSCULA. La lista está VACÍA: las tres que
#: quedaban («(A, B)», «(A–C)», «(A–D)», en `pipeline/14_extra_figures_rem.py`) se pasaron a minúscula, que
#: es como la lámina letra sus paneles. La prueba exige que ninguna otra leyenda las imite.
CAPTIONS_PENDING_LOWERCASE: tuple[str, ...] = ()

#: Archivos de lámina que quedan en `outputs/<variante>/<idioma>/figures/` SIN clave en el registro: son
#: láminas de planes de figuras anteriores que su módulo SIGUE escribiendo (`08a_figures_grd.py` escribe
#: `figS4_grd_model_sensitivities`; `08b_figures_rem.py`, `figS7_a05_standardised_rates`). No entran en
#: ningún documento —el registro imprime, con el mismo prefijo pero con otro contenido, `figS4_models_cpa` y
#: `figS7_rem_education_models`—, pero conservan su leyenda y su título guardado, y ese título dice
#: «Figure S4 / S7», el mismo rótulo de la lámina que sí se imprime: quien mire la carpeta puede coger el
#: archivo equivocado, y por eso la prueba de biyección los tolera NOMBRÁNDOLOS, en vez de callar cualquier
#: archivo sobrante.
#:
#: LA LISTA SE PUDRE SI NO SE COMPRUEBA (fase 4g, tarea G2). Hasta aquí nombraba además
#: `figS3_hospital_effects`, la lámina apaisada que el módulo 06 dejó de producir: tres entradas de
#: tolerancia para dos huérfanas reales, y un comentario que seguía afirmando que el módulo 06 la escribía.
#: No rompía nada —la biyección la usa como conjunto de nombres PERMITIDOS, y permitir un archivo que no
#: existe no acusa a nadie— y por eso pasó dos verificaciones enteras sin que nada fallara. Se quita, y con
#: ella se quita la posibilidad de que vuelva a pasar: `stale_legacy_unregistered_plates()` mira el disco y
#: `material_blocks()` —que es por donde pasa todo documento que imprime la parte suplementaria, y que se
#: ejecuta después de los módulos de láminas— exige que la lista esté al día. Una tolerancia que nombra un
#: archivo inexistente es una tolerancia que ya no se puede leer: hay que borrar la entrada.
LEGACY_UNREGISTERED_PLATES: tuple[str, ...] = (
    "figS4_grd_model_sensitivities", "figS7_a05_standardised_rates",
)


def _plate_stems(variant: str, lang: str) -> set[str]:
    """Nombres (sin extensión) de los PNG de lámina de una combinación, en las dos carpetas que los llevan."""
    base = CFG.OUT / variant / lang
    return {path.stem for sub in ("figures", "extra/figures") for path in (base / sub).glob("*.png")}


def stale_legacy_unregistered_plates() -> tuple[str, ...]:
    """Entradas de `LEGACY_UNREGISTERED_PLATES` que ya no corresponden a ningún archivo en disco.

    Se mide SOLO contra las salidas COMPLETAS —aquéllas en las que están TODAS las láminas registradas—, de
    modo que una reconstrucción a medias, o un árbol recién clonado sin `outputs/`, no acusa a la lista: sin
    ninguna salida completa devuelve la tupla vacía y no hay nada que comprobar. Cuando sí hay una salida
    completa y un nombre tolerado no aparece en ninguna de ellas, ese nombre sobra.
    """
    registered = set(FIGURE_ORDER)
    present: set[str] = set()
    complete = 0
    for variant in CFG.VARIANTS:
        for lang in LANGS:
            stems = _plate_stems(variant, lang)
            if registered <= stems:          # esta salida está construida entera: su ausencia sí prueba algo
                complete += 1
                present |= stems
    if not complete:
        return ()
    return tuple(key for key in LEGACY_UNREGISTERED_PLATES if key not in present)


def assert_legacy_unregistered_plates_current() -> None:
    """Falla si la lista de tolerancia nombra una lámina que ya no existe. La llama `material_blocks`."""
    stale = stale_legacy_unregistered_plates()
    if stale:
        raise AssertionError(
            f"LEGACY_UNREGISTERED_PLATES nombra {len(stale)} lámina(s) que ningún módulo escribe ya y que no "
            f"están en ninguna salida completa: {', '.join(stale)}. La lista tolera archivos huérfanos REALES; "
            f"un nombre sin archivo sólo estorba. Quítalo de supplementary_material.py (y del comentario que "
            f"dice qué módulo lo escribe).")


# ---------------------------------------------------------------------------
# Láminas suplementarias: grupos temáticos en orden de aparición
# ---------------------------------------------------------------------------
FIGURE_GROUPS: list[tuple[dict, list[str]]] = [
    ({"en": "Core supplementary figures of the article",
      "es": "Láminas suplementarias centrales del artículo"},
     ["figS1_grd_variants", "figS2_grd_subcodes", "figS3_grd_hospital_effects", "figS4_models_cpa",
      "figS5_rem_june_december", "figS6_rem_stable_panel", "figS7_rem_education_models", "figS8_a05_age_sex",
      "figS9_regional_maps", "figS10_denominators", "figS11_coverage_age_sex", "figS12_junaeb_sex_level",
      "figS13_rem_seasonality", "figS14_deis_sex_age", "figS15_controls"]),
    ({"en": "Hospital episodes in detail", "es": "Episodios hospitalarios en detalle"},
     ["EF1_seasonality_monthly", "EF2_length_of_stay", "EF3_episode_features", "EF4_severity_weight",
      "EF5_codiagnoses", "EF6_readmission_multiplicity", "EF7_age_detail", "EF8_hospitals", "EF9_territory",
      "EF10_deis_detail"]),
    ({"en": "Aggregate REM administrative pathway in detail",
      "es": "Ruta administrativa REM agregada en detalle"},
     ["E11_rem_a03_codes_by_era", "E12_rem_a03_risk_referral", "E13_rem_a05_regional", "E14_rem_a05_age_sex",
      "E15_rem_p2_p6_detail", "E16_rem_a27_a28_regional", "E17_rem_establishment_distribution",
      "E18_rem_monthly_series", "E19_rem_definition_era_sensitivity"]),
    ({"en": "Denominators, surveys and education", "es": "Denominadores, encuestas y educación"},
     ["figE20_population_structure", "figE21_insurance_coverage", "figE22_rem20_capacity", "figE23_surveys_detail",
      "figE24_education_detail", "figE25_junaeb_detail"]),
    ({"en": "Sex ratio across sources", "es": "Razón por sexo entre fuentes"},
     ["figE26_cross_source", "figE26b_sex_ratio_multisource"]),
    ({"en": "Model diagnostics and case-definition sensitivity",
      "es": "Diagnósticos de los modelos y sensibilidad a la definición de caso"},
     ["figE27_model_diagnostics", "figE28_variant_sensitivity"]),
    ({"en": "Spatial analysis and territorial correlation",
      "es": "Análisis espacial y correlación territorial"},
     ["E40_maps_grd_smoothed_ratio", "E41_maps_rem_place_of_care", "E42_lisa_gistar_maps", "E43_moran_scatter_weights",
      "E44_correlation_matrix", "E45_bivariate_moran", "E46_sae_deprivation", "E47_lorenz_theil", "E48_rank_stability",
      "E49_regional_summary"]),
]

# ---------------------------------------------------------------------------
# Tablas suplementarias: grupos temáticos en orden de aparición
# ---------------------------------------------------------------------------
# Las diez tablas metodológicas se imprimen dentro de la metodología extendida, donde se comentan,
# y por eso no vuelven a aparecer en la sección de tablas.
METHODS_TABLES: list[str] = list(PME.TABLE_KEYS)

TABLE_GROUPS: list[tuple[dict, list[str]]] = [
    ({"en": "Sources and data workflow", "es": "Fuentes y flujo de datos"},
     ["T1_sources", "T_dataflow_counts"]),
    ({"en": "Core supplementary tables of the article", "es": "Tablas suplementarias centrales del artículo"},
     ["S_definition_breaks", "ST7_provenance", "ST7b_manifest_checks", "ST2_rem_code_dictionary",
      "ST3_rem_reporting_establishments", "ST1_grd_hospital_panel", "ST8_grd_identifier_audit",
      "ST10_grd_f84_subcodes", "ST9_grd_age_sex", "S_grd_population_rates", "S_hospital_rates_2024",
      "ST11a_deis_annual", "ST11b_deis_vs_grd", "S14_deis_sex_age", "F3_rem_pathway_data", "S5_june_december",
      "ST14_p2_p6_june_december", "S6_stable_panel", "ST13_a05_age_sex", "S8_a05_age_sex",
      "S_a05_standardised_rates", "S13_rem_seasonality", "ST4a_comuna_crosswalk_summary", "ST4b_comuna_unmatched",
      "ST12a_fonasa_schema", "ST12b_isapre_rules", "ST12c_aps_panel", "S10_denominator_sensitivity",
      "S11_coverage_age_sex", "ST5_survey_items", "ST6_junaeb_items", "S12_junaeb_sex_level",
      "F4_triangulation_series", "S9_regional_rates", "S_convergence_index", "T7_models_cpa_full",
      "T8_controls", "S15_controls_scatter"]),
    ({"en": "Hospital episodes in detail", "es": "Episodios hospitalarios en detalle"},
     ["E1_grd_seasonality", "E2_grd_length_of_stay", "E3_grd_los_by_age", "E4_grd_episode_features",
      "E5_grd_weight_and_groups", "E6_grd_codiagnoses_top25", "E7_grd_codiagnosis_chapters",
      "E8_grd_principal_when_secondary", "E9_grd_readmission", "E10_grd_multiplicity", "E11_grd_territory_region",
      "E12_grd_age_single_year", "EF1_seasonality_monthly", "EF2_length_of_stay", "EF3_episode_features",
      "EF4_severity_weight", "EF5_codiagnoses", "EF6_readmission_multiplicity", "EF7_age_detail", "EF8_hospitals",
      "EF9_territory", "EF10_deis_detail"]),
    ({"en": "Aggregate REM administrative pathway in detail",
      "es": "Ruta administrativa REM agregada en detalle"},
     ["E11_rem_a03_codes_by_era", "E12_rem_a03_risk_referral", "E13_rem_a05_regional", "E14_rem_a05_age_sex",
      "E15_rem_p2_p6_detail", "E16_rem_a27_a28_regional", "E17_rem_establishment_distribution",
      "E18_rem_monthly_series", "E19_rem_definition_era_sensitivity"]),
    ({"en": "Denominators, surveys and education", "es": "Denominadores, encuestas y educación"},
     ["E20_population_structure", "E21_insurance_coverage", "E22_rem20_capacity", "E23_surveys_detail",
      "E24_education_detail", "E25_junaeb_detail"]),
    ({"en": "Sex ratio across sources", "es": "Razón por sexo entre fuentes"},
     ["E26_cross_source", "E26b_sex_ratio_multisource"]),
    ({"en": "Model diagnostics and case-definition sensitivity",
      "es": "Diagnósticos de los modelos y sensibilidad a la definición de caso"},
     ["E27_model_diagnostics", "E28_variant_sensitivity"]),
    ({"en": "Spatial analysis and territorial correlation",
      "es": "Análisis espacial y correlación territorial"},
     ["E40_grd_smoothed_ratio_comuna", "E41_rem_comuna_place_of_care", "E42_local_class_counts",
      "E43_moran_sensitivity_main", "E44_correlation_matrix_comuna", "E45_bivariate_moran_pairs",
      "E46_sae_association", "E47_inequality_gini_theil", "E48_rank_stability", "E49_regional_summary",
      "E50_moran_gistar_all", "E51_lisa_significant_comunas"]),
    ({"en": "Complete data tables and project inventory",
      "es": "Tablas de datos completas e inventario del proyecto"},
     ["E60_grd_annual_full", "E61_grd_hospital_year_full", "E62_grd_region_population_rates",
      "E63_grd_age_single_sex_full", "E64_grd_codiagnoses_full", "E65_grd_episode_features_full",
      "E66_grd_length_of_stay_full", "E67_grd_readmission_full", "E68_grd_multiplicity_full",
      "E69_rem_code_year_full", "E70_rem_a05_age_sex_full", "E71_rem_p2_p6_region_year",
      "E72_rem_establishments_by_module", "E73_denominator_layers_full", "E74_coverage_harmonisation_rules",
      "E75_survey_estimates_full", "E76_education_pie_full", "E77_education_junaeb_full",
      "E78_models_all_specifications", "E79_reproduction_controls_by_family", "E80_tidy_data_dictionary",
      "E81_project_asset_inventory"]),
]

# Orden final de la numeración compartida (= orden de aparición de la parte suplementaria; las diez
# tablas metodológicas se numeran junto a las dos tablas de fuentes porque se imprimen al comienzo,
# dentro de la metodología extendida).
FIGURE_ORDER: list[str] = [key for _, keys in FIGURE_GROUPS for key in keys]
TABLE_ORDER: list[str] = (TABLE_GROUPS[0][1] + METHODS_TABLES
                          + [key for _, keys in TABLE_GROUPS[1:] for key in keys])

# ---------------------------------------------------------------------------
# Frase de presentación de cada lámina (qué muestra, unidad y denominador)
# ---------------------------------------------------------------------------
FIGURE_INTRO: dict[str, dict] = {
    "figS1_grd_variants": {
        "en": "{L} contrasts the two case-definition variants in the hospital series. The unit is the GRD episode and "
              "the denominator the GRD episodes of the same year, panel and activity.",
        "es": "La {L} contrasta las dos variantes de definición de caso en la serie hospitalaria. La unidad es el "
              "episodio GRD y el denominador, los episodios GRD del mismo año, panel y actividad."},
    "figS2_grd_subcodes": {
        "en": "{L} decomposes the F84 family into subcodes and diagnostic positions. The unit is the episode and the "
              "denominator the episodes with documented F84 of the same year.",
        "es": "La {L} descompone la familia F84 en subcódigos y posiciones diagnósticas. La unidad es el episodio y el "
              "denominador, los episodios con F84 documentado del mismo año."},
    "figS3_grd_hospital_effects": {
        "en": "{L} shows how far hospitals differ once their volume is taken into account. The unit is the "
              "hospital-year and the denominator the GRD episodes of the same hospital and year.",
        "es": "La {L} muestra cuánto difieren los hospitales una vez considerado su volumen. La unidad es el "
              "hospital-año y el denominador, los episodios GRD del mismo hospital y año."},
    "figS4_models_cpa": {
        "en": "{L} collects the quasi-Poisson annual percent changes of every system. The unit is the model "
              "specification and the denominator the offset declared for each one.",
        "es": "La {L} reúne los cambios porcentuales anuales cuasi-Poisson de todos los sistemas. La unidad es la "
              "especificación del modelo y el denominador, el desplazamiento declarado en cada una."},
    "figS5_rem_june_december": {
        "en": "{L} compares the June and December cuts of the REM stocks, which are never summed. The unit is a person "
              "under control at the cut date and the denominator the establishments reporting that same cut.",
        "es": "La {L} compara los cortes de junio y diciembre de los stocks REM, que nunca se suman. La unidad es una "
              "persona bajo control a la fecha de corte y el denominador, los establecimientos que reportan ese corte."},
    "figS6_rem_stable_panel": {
        "en": "{L} repeats the REM series in the panel of establishments that reported the code every year. The unit is "
              "the entry or the person under control and the denominator the establishments of the panel.",
        "es": "La {L} repite las series REM en el panel de establecimientos que reportaron el código todos los años. La "
              "unidad es el ingreso o la persona bajo control y el denominador, los establecimientos del panel."},
    "figS7_rem_education_models": {
        "en": "{L} fits the REM and education series with standardised rates and log-linear trends. The unit is the "
              "entry, the person under control or the registered student and the denominator the resident population "
              "or the reporting units of the same year.",
        "es": "La {L} ajusta las series REM y educativas con tasas estandarizadas y tendencias log-lineales. La unidad "
              "es el ingreso, la persona bajo control o el estudiante registrado y el denominador, la población "
              "residente o las unidades reportantes del mismo año."},
    "figS8_a05_age_sex": {
        "en": "{L} distributes the A05 autism entries by age group and sex. The unit is a programme entry, never a "
              "person, and the denominator the entries of the same year.",
        "es": "La {L} distribuye los ingresos A05 por autismo según grupo de edad y sexo. La unidad es un ingreso al "
              "programa, nunca una persona, y el denominador, los ingresos del mismo año."},
    "figS9_regional_maps": {
        "en": "{L} maps the regional distribution of hospital and REM recognition. The unit is the region — of "
              "residence for GRD and of the establishment for A05, which are not the same geography — and the "
              "denominator the resident population of the region.",
        "es": "La {L} cartografía la distribución regional del reconocimiento hospitalario y REM. La unidad es la "
              "región —de residencia en GRD y del establecimiento en A05, que no son la misma geografía— y el "
              "denominador, la población residente de la región."},
    "figS10_denominators": {
        "en": "{L} compares the population bases available as denominators. The unit is the resident person and the "
              "denominator the national or regional population of the same year under each base.",
        "es": "La {L} compara las bases poblacionales disponibles como denominador. La unidad es la persona residente "
              "y el denominador, la población nacional o regional del mismo año bajo cada base."},
    "figS11_coverage_age_sex": {
        "en": "{L} describes the insurance and operational coverage layers by age and sex. The unit is the beneficiary "
              "or enrolled person at the December cut and the denominator the projected resident population.",
        "es": "La {L} describe las capas de cobertura aseguradora y operativa por edad y sexo. La unidad es el "
              "beneficiario o inscrito al corte de diciembre y el denominador, la población residente proyectada."},
    "figS12_junaeb_sex_level": {
        "en": "{L} gives the caregiver-reported autism percentages by sex and school level. The unit is the surveyed "
              "student and the denominator the students of the same cohort with a valid answer.",
        "es": "La {L} entrega los porcentajes de autismo informado por la persona cuidadora según sexo y nivel "
              "escolar. La unidad es el estudiante encuestado y el denominador, los estudiantes de la misma cohorte "
              "con respuesta válida."},
    "figS13_rem_seasonality": {
        "en": "{L} shows the monthly profile of REM reporting. The unit is the establishment-month record and the "
              "denominator each year's own monthly mean.",
        "es": "La {L} muestra el perfil mensual del reporte REM. La unidad es el registro establecimiento-mes y el "
              "denominador, la media mensual del propio año."},
    "figS14_deis_sex_age": {
        "en": "{L} describes the DEIS discharges with F84 as principal diagnosis. The unit is the discharge and the "
              "denominator the discharges of the same year and ownership.",
        "es": "La {L} describe los egresos DEIS con F84 como diagnóstico principal. La unidad es el egreso y el "
              "denominador, los egresos del mismo año y dependencia."},
    # «Control indicador-año» es el término que el estudio reserva para las filas del PLAN DE ANÁLISIS; esta
    # lámina y su tabla acompañante cuentan los controles numéricos POR MÓDULO del pipeline completo, que es
    # otro ámbito y nunca se suma con aquel. La frase de presentación nombra ahora su propio ámbito.
    "figS15_controls": {
        "en": "{L} confronts each expected control value with the value reproduced by the pipeline. The unit is the "
              "numeric module control of the whole pipeline —not the indicator-year row of the analysis plan— and "
              "there is no denominator: the plate compares counts.",
        "es": "La {L} confronta cada valor de control esperado con el valor reproducido por el pipeline. La unidad es "
              "el control numérico por módulo del pipeline completo —no la fila indicador-año del plan de análisis— y "
              "no hay denominador: la lámina compara recuentos."},
    "EF1_seasonality_monthly": {
        "en": "{L} follows the hospital series month by month. The unit is the episode with documented F84 and the "
              "denominator the GRD episodes of the same month.",
        "es": "La {L} sigue la serie hospitalaria mes a mes. La unidad es el episodio con F84 documentado y el "
              "denominador, los episodios GRD del mismo mes."},
    "EF2_length_of_stay": {
        "en": "{L} describes the length of stay of episodes with documented F84. The unit is the episode and the "
              "denominator the episodes with valid admission and discharge dates.",
        "es": "La {L} describe la estadía de los episodios con F84 documentado. La unidad es el episodio y el "
              "denominador, los episodios con fechas de ingreso y egreso válidas."},
    "EF3_episode_features": {
        "en": "{L} contrasts the administrative features of episodes with documented F84 against all GRD episodes. The "
              "unit is the episode and the denominator the episodes of the same group and year.",
        "es": "La {L} contrasta las características administrativas de los episodios con F84 documentado frente a "
              "todos los episodios GRD. La unidad es el episodio y el denominador, los episodios del mismo grupo y año."},
    "EF4_severity_weight": {
        "en": "{L} presents severity, mortality risk, GRD weight and in-hospital lethality. The unit is the episode and "
              "the denominator the episodes with the corresponding field reported.",
        "es": "La {L} presenta severidad, riesgo de mortalidad, peso GRD y letalidad intrahospitalaria. La unidad es el "
              "episodio y el denominador, los episodios con el campo correspondiente informado."},
    "EF5_codiagnoses": {
        "en": "{L} lists the diagnoses recorded together with F84. The unit is the diagnosis within an episode and the "
              "denominator the episodes with documented F84 of the same year.",
        "es": "La {L} lista los diagnósticos registrados junto con F84. La unidad es el diagnóstico dentro de un "
              "episodio y el denominador, los episodios con F84 documentado del mismo año."},
    "EF6_readmission_multiplicity": {
        "en": "{L} counts the episodes recorded under the same identifier within a year. The unit is the "
              "identifier-year and the denominator the identifiers with at least one episode with documented F84; "
              "identifiers are never followed across the 2020–2021 format change.",
        "es": "La {L} cuenta los episodios registrados bajo un mismo identificador dentro de un año. La unidad es el "
              "identificador-año y el denominador, los identificadores con al menos un episodio con F84 documentado; "
              "los identificadores nunca se siguen a través del cambio de formato de 2020–2021."},
    "EF7_age_detail": {
        "en": "{L} shows the age distribution of episodes with documented F84 in single years and in standard age "
              "groups. The unit is the episode and the denominator the episodes of the same age group and year.",
        "es": "La {L} muestra la distribución etaria de los episodios con F84 documentado en años simples y en grupos "
              "de edad estándar. La unidad es el episodio y el denominador, los episodios del mismo grupo de edad y año."},
    "EF8_hospitals": {
        "en": "{L} ranks the panel hospitals and measures how stable and how concentrated their rates are. The unit is "
              "the hospital-year and the denominator the GRD episodes of the same hospital and year.",
        "es": "La {L} ordena los hospitales del panel y mide cuán estables y concentradas son sus tasas. La unidad es "
              "el hospital-año y el denominador, los episodios GRD del mismo hospital y año."},
    "EF9_territory": {
        "en": "{L} distributes episodes and persons within the year by reported region and comuna of residence. The "
              "unit is the episode or the person within the year and the denominator the resident population of the "
              "territory.",
        "es": "La {L} distribuye episodios y personas dentro del año por región y comuna de residencia informadas. La "
              "unidad es el episodio o la persona dentro del año y el denominador, la población residente del "
              "territorio."},
    "EF10_deis_detail": {
        "en": "{L} details the DEIS discharges with principal F84 and compares them with the homologous GRD series. "
              "The unit is the discharge and the denominator the discharges of the same year; the two registries are "
              "not linked by person.",
        "es": "La {L} detalla los egresos DEIS con F84 principal y los compara con la serie GRD homóloga. La unidad es "
              "el egreso y el denominador, los egresos del mismo año; los dos registros no se enlazan por persona."},
    "E11_rem_a03_codes_by_era": {
        "en": "{L} opens the A03 screening module code by code and era by era. The unit is the establishment-month "
              "record and the denominator, where a proportion is shown, the screenings performed in the same era; no "
              "line joins two eras.",
        "es": "La {L} abre el módulo de tamizaje A03 código por código y era por era. La unidad es el registro "
              "establecimiento-mes y el denominador, cuando se muestra una proporción, los tamizajes realizados en la "
              "misma era; ninguna línea une dos eras."},
    "E12_rem_a03_risk_referral": {
        "en": "{L} shows the risk and referral structure of M-CHAT-R/F screening. The unit is the recorded screening "
              "result and the denominator the results of the same era and age band.",
        "es": "La {L} muestra la estructura de riesgo y derivación del tamizaje M-CHAT-R/F. La unidad es el resultado "
              "de tamizaje registrado y el denominador, los resultados de la misma era y tramo de edad."},
    "E13_rem_a05_regional": {
        "en": "{L} distributes the A05 autism entries by region and year. The unit is a programme entry and the "
              "denominator the resident population of the region, whose establishments report the entry.",
        "es": "La {L} distribuye los ingresos A05 por autismo según región y año. La unidad es un ingreso al programa y "
              "el denominador, la población residente de la región cuyos establecimientos informan el ingreso."},
    "E14_rem_a05_age_sex": {
        "en": "{L} standardises the A05 entries by age and sex and derives the male-to-female ratio. The unit is the "
              "entry and the denominator the resident population of the same age group and sex.",
        "es": "La {L} estandariza los ingresos A05 por edad y sexo y deriva la razón hombre:mujer. La unidad es el "
              "ingreso y el denominador, la población residente del mismo grupo de edad y sexo."},
    "E15_rem_p2_p6_detail": {
        "en": "{L} opens the P2 and P6 December stocks by category and level of care. The unit is a person under "
              "control at the December cut and the denominator the establishments reporting that cut; semesters are "
              "never summed.",
        "es": "La {L} abre los stocks de diciembre de P2 y P6 por categoría y nivel de atención. La unidad es una "
              "persona bajo control al corte de diciembre y el denominador, los establecimientos que reportan ese "
              "corte; los semestres nunca se suman."},
    "E16_rem_a27_a28_regional": {
        "en": "{L} distributes counselling, assisted referral and rehabilitation entries by region. The unit is the "
              "intervention (A27) or the entry (A28), never a person, and the denominator the resident population of "
              "the region.",
        "es": "La {L} distribuye consejerías, derivaciones asistidas e ingresos a rehabilitación por región. La unidad "
              "es la intervención (A27) o el ingreso (A28), nunca una persona, y el denominador, la población "
              "residente de la región."},
    "E17_rem_establishment_distribution": {
        "en": "{L} measures how unevenly REM activity is distributed across establishments. The unit is the "
              "establishment-year and the denominator the total activity of the same indicator and year.",
        "es": "La {L} mide cuán desigualmente se distribuye la actividad REM entre establecimientos. La unidad es el "
              "establecimiento-año y el denominador, la actividad total del mismo indicador y año."},
    "E18_rem_monthly_series": {
        "en": "{L} follows the REM flows month by month. The unit is the establishment-month record and the "
              "denominator each year's own monthly mean; the fall observed during the pandemic is a fall in reporting "
              "establishments, not necessarily in persons.",
        "es": "La {L} sigue los flujos REM mes a mes. La unidad es el registro establecimiento-mes y el denominador, la "
              "media mensual del propio año; la caída observada durante la pandemia es una caída de establecimientos "
              "reportantes, no necesariamente de personas."},
    "E19_rem_definition_era_sensitivity": {
        "en": "{L} repeats every REM indicator under strict autism, the variant's pervasive-developmental-disorder "
              "family and the broad pre-2021 category. The unit is the entry or the person under control and the "
              "denominator the establishments reporting the same era.",
        "es": "La {L} repite todos los indicadores REM bajo autismo estricto, la familia de trastornos generalizados "
              "del desarrollo de la variante y la categoría amplia previa a 2021. La unidad es el ingreso o la persona "
              "bajo control y el denominador, los establecimientos que reportan la misma era."},
    "figE20_population_structure": {
        "en": "{L} describes the reference population used as denominator. The unit is the resident person and the "
              "denominator the national or regional population of the same year.",
        "es": "La {L} describe la población de referencia usada como denominador. La unidad es la persona residente y "
              "el denominador, la población nacional o regional del mismo año."},
    "figE21_insurance_coverage": {
        "en": "{L} details the December stocks of insurance and primary-care enrolment. The unit is the beneficiary or "
              "enrolled person and the denominator the projected resident population; these are coverage layers, never "
              "case denominators.",
        "es": "La {L} detalla los stocks de diciembre de aseguramiento e inscripción en atención primaria. La unidad es "
              "el beneficiario o inscrito y el denominador, la población residente proyectada; son capas de cobertura, "
              "nunca denominadores de casos."},
    "figE22_rem20_capacity": {
        "en": "{L} relates hospital activity and capacity to the hospital series of episodes with documented F84. The "
              "unit is the establishment-year and the denominator the activity of the same year; activity is never "
              "used as a covered population.",
        "es": "La {L} relaciona la actividad y capacidad hospitalarias con la serie de episodios con F84 documentado. "
              "La unidad es el establecimiento-año y el denominador, la actividad del mismo año; la actividad nunca se "
              "usa como población cubierta."},
    "figE23_surveys_detail": {
        "en": "{L} presents the survey estimates with their complex design, their precision and the domains flagged as "
              "unreliable. The unit is the survey respondent and the denominator the weighted population of the domain.",
        "es": "La {L} presenta las estimaciones de encuesta con su diseño complejo, su precisión y los dominios "
              "marcados como poco fiables. La unidad es la persona encuestada y el denominador, la población ponderada "
              "del dominio."},
    "figE24_education_detail": {
        "en": "{L} opens the educational registers of autism. The unit is the registered student in the school year "
              "and the denominator the students of the same programme and year.",
        "es": "La {L} abre los registros educativos de autismo. La unidad es el estudiante registrado en el año escolar "
              "y el denominador, los estudiantes del mismo programa y año."},
    "figE25_junaeb_detail": {
        "en": "{L} details the caregiver survey of whole school cohorts by cohort and year. The unit is the surveyed "
              "student and the denominator the students with a valid answer, weighted where a weight is published.",
        "es": "La {L} detalla la encuesta a cuidadores de cohortes escolares completas por cohorte y año. La unidad es "
              "el estudiante encuestado y el denominador, los estudiantes con respuesta válida, ponderados donde hay "
              "ponderador publicado."},
    "figE26_cross_source": {
        "en": "{L} places every system side by side as an index, as a population rate and as a value per reporting "
              "unit. Each series keeps its own unit and denominator and no ratio between systems is computed.",
        "es": "La {L} pone todos los sistemas lado a lado como índice, como tasa poblacional y como valor por unidad "
              "reportante. Cada serie conserva su unidad y su denominador y no se calcula ningún cociente entre "
              "sistemas."},
    "figE26b_sex_ratio_multisource": {
        "en": "{L} compares the male-to-female ratio in every source that reports sex. The unit varies by source "
              "(episodes, discharges, entries, persons under control, students or respondents) and the denominator is "
              "always the female count of the same source and year.",
        "es": "La {L} compara la razón hombre:mujer en todas las fuentes que informan sexo. La unidad varía según la "
              "fuente (episodios, egresos, ingresos, personas bajo control, estudiantes o personas encuestadas) y el "
              "denominador es siempre el recuento femenino de la misma fuente y año."},
    "figE27_model_diagnostics": {
        "en": "{L} gives the diagnostics of the quasi-Poisson models. The unit is the model specification and the "
              "denominator its declared offset; dispersion, residual autocorrelation and influence are reported.",
        "es": "La {L} entrega los diagnósticos de los modelos cuasi-Poisson. La unidad es la especificación del modelo "
              "y el denominador, su desplazamiento declarado; se informan dispersión, autocorrelación residual e "
              "influencia."},
    "figE28_variant_sensitivity": {
        "en": "{L} repeats every series in the two case-definition variants. The unit is that of each series and the "
              "denominator the value of the variant that excludes Rett syndrome.",
        "es": "La {L} repite todas las series en las dos variantes de definición de caso. La unidad es la de cada serie "
              "y el denominador, el valor de la variante que excluye el síndrome de Rett."},
    "E40_maps_grd_smoothed_ratio": {
        "en": "{L} maps hospital recognition by comuna of residence with empirical-Bayes smoothing. The unit is the "
              "episode or the person within the year and the denominator the expected count derived from the national "
              "age and sex rates.",
        "es": "La {L} cartografía el reconocimiento hospitalario por comuna de residencia con suavizamiento "
              "empirical-Bayes. La unidad es el episodio o la persona dentro del año y el denominador, el recuento "
              "esperado derivado de las tasas nacionales por edad y sexo."},
    "E41_maps_rem_place_of_care": {
        "en": "{L} maps the REM indicators by comuna of the reporting establishment, which is place of care and not "
              "residence. The unit is the entry or the person under control and the denominator the comuna population, "
              "with that incompatibility stated in the caption.",
        "es": "La {L} cartografía los indicadores REM por comuna del establecimiento reportante, que es lugar de "
              "atención y no residencia. La unidad es el ingreso o la persona bajo control y el denominador, la "
              "población comunal, con esa incompatibilidad declarada en la leyenda."},
    "E42_lisa_gistar_maps": {
        "en": "{L} locates the local clusters of the smoothed ratios. The unit is the comuna and the denominator its "
              "expected count; the p-values are obtained by permutation and corrected for multiplicity.",
        "es": "La {L} localiza los conglomerados locales de las razones suavizadas. La unidad es la comuna y el "
              "denominador, su recuento esperado; los valores p se obtienen por permutación y se corrigen por "
              "multiplicidad."},
    "E43_moran_scatter_weights": {
        "en": "{L} tests how far the global spatial autocorrelation depends on the neighbourhood definition. The unit "
              "is the comuna and the denominator its expected count; non-continental comunas are treated explicitly.",
        "es": "La {L} pone a prueba cuánto depende la autocorrelación espacial global de la definición de vecindad. La "
              "unidad es la comuna y el denominador, su recuento esperado; las comunas no continentales se tratan de "
              "forma explícita."},
    "E44_correlation_matrix": {
        "en": "{L} correlates the territorial indicators of the different systems at comuna and at regional scale. The "
              "unit is the territory and there is no denominator: each cell is a rank correlation between two "
              "administrative counts of sources that are not person-linked, so the association is ecological.",
        "es": "La {L} correlaciona los indicadores territoriales de los distintos sistemas a escala comunal y regional. "
              "La unidad es el territorio y no hay denominador: cada celda es una correlación de rangos entre dos "
              "recuentos administrativos de fuentes que no se enlazan por persona, de modo que la asociación es "
              "ecológica."},
    "E45_bivariate_moran": {
        "en": "{L} measures the spatial cross-correlation between pairs of systems. The unit is the comuna and the "
              "denominator its expected count; the statistic describes neighbourhoods, never persons.",
        "es": "La {L} mide la correlación espacial cruzada entre pares de sistemas. La unidad es la comuna y el "
              "denominador, su recuento esperado; el estadístico describe vecindades, nunca personas."},
    "E46_sae_deprivation": {
        "en": "{L} relates administrative recognition to comuna deprivation estimated for small areas. The unit is the "
              "comuna and the denominator its expected count; the association is ecological and supports no "
              "individual-level inference.",
        "es": "La {L} relaciona el reconocimiento administrativo con la privación comunal estimada para áreas "
              "pequeñas. La unidad es la comuna y el denominador, su recuento esperado; la asociación es ecológica y "
              "no sustenta ninguna inferencia individual."},
    "E47_lorenz_theil": {
        "en": "{L} quantifies how unequally recognition is distributed across the territory. The unit is the comuna and "
              "the denominator the national total of the same indicator and year.",
        "es": "La {L} cuantifica cuán desigualmente se distribuye el reconocimiento en el territorio. La unidad es la "
              "comuna y el denominador, el total nacional del mismo indicador y año."},
    "E48_rank_stability": {
        "en": "{L} asks whether the territorial ordering is stable over time. The unit is the comuna-year and the "
              "denominator its expected count in the same year.",
        "es": "La {L} pregunta si el ordenamiento territorial es estable en el tiempo. La unidad es la comuna-año y el "
              "denominador, su recuento esperado en el mismo año."},
    "E49_regional_summary": {
        "en": "{L} summarises the same territorial analysis at regional scale, where counts are larger and intervals "
              "narrower. The unit is the region and the denominator its resident population or its expected count.",
        "es": "La {L} resume el mismo análisis territorial a escala regional, donde los recuentos son mayores y los "
              "intervalos más estrechos. La unidad es la región y el denominador, su población residente o su recuento "
              "esperado."},
}

# ---------------------------------------------------------------------------
# Encabezados y textos de la parte suplementaria
# ---------------------------------------------------------------------------
W = {
    "part_h1": {"en": "Supplementary material", "es": "Material suplementario"},
    "contents_h1": {"en": "Contents", "es": "Contenido"},
    "methods_h1": {"en": "Supplementary methods: extended methodology",
                   "es": "Métodos suplementarios: metodología extendida"},
    "figs_h1": {"en": "Supplementary figures", "es": "Láminas suplementarias"},
    "tabs_h1": {"en": "Supplementary tables", "es": "Tablas suplementarias"},
    "note": {
        "en": ("{opening} Supplementary items are numbered in a single thematic sequence rather than by order of "
               "first citation, and the article cites them by number: the supplementary figures run from S1 to "
               "S{nfig} in the order in which they are printed here, and the supplementary tables from S1 to S{ntab}, "
               "with one deliberate exception — the {nmt} methodological tables are printed inside the extended "
               "methodology, where they are discussed, and therefore appear ahead of Tables S1 and S2. Every count in this part is "
               "administrative recognition of autism — the recording of an "
               "autism code in a contact with a service — and never prevalence or incidence; the hospital outcome is "
               "episodes with documented F84 and F84 as principal diagnosis is a separate series; the sources are not "
               "linked at the person level, so no figure or table here is a care cascade and no ratio between two "
               "sources is an individual probability; stocks and flows never share an axis; place of care and place of "
               "residence are never mixed without an explicit note; definition eras are never joined by a line; and "
               "Law 21.545 (March 2023) appears only as policy context, never as an intervention with an estimable "
               "effect."),
        "es": ("{opening} Los ítems suplementarios se numeran en una sola secuencia temática y no por orden de "
               "primera cita, y el artículo los cita por ese número: las láminas suplementarias van de S1 a S{nfig} "
               "en el orden en que se imprimen aquí, y las tablas suplementarias de S1 a S{ntab}, con una excepción "
               "deliberada: las {nmt} tablas metodológicas se imprimen dentro de la metodología extendida, donde se "
               "discuten, y por eso aparecen antes que las Tablas S1 y S2. Todo recuento de esta parte es "
               "reconocimiento administrativo del autismo —el registro de un código de autismo en un contacto con un "
               "servicio— y "
               "nunca prevalencia ni incidencia; el resultado hospitalario son episodios con F84 documentado y F84 "
               "como diagnóstico principal es una serie aparte; las fuentes no se enlazan a nivel de persona, por lo "
               "que ninguna lámina ni tabla de aquí es una cascada asistencial y ningún cociente entre dos fuentes es "
               "una probabilidad individual; stocks y flujos nunca comparten eje; lugar de atención y lugar de "
               "residencia nunca se mezclan sin una nota explícita; las eras de definición nunca se unen con una "
               "línea; y la Ley 21.545 (marzo de 2023) aparece solo como contexto de política, nunca como una "
               "intervención con efecto estimable."),
    },
    "index": {
        "en": ("Contents of this part. (a) Supplementary methods: the extended methodology, which restates the "
               "Methods of the article with every estimator, its {neq} numbered equations, cited in the text that "
               "applies them, and the {nmt} methodological tables ({mt_range}), printed where they are discussed. "
               "(b) Supplementary figures: {nfig} plates in {ngf} thematic groups (core supplementary figures; "
               "hospital episodes; aggregate REM administrative pathway; denominators, surveys and education; sex "
               "ratio across sources; model diagnostics and case-definition sensitivity; spatial analysis and "
               "territorial correlation), each with its self-contained caption. (c) Supplementary tables: {ntab} "
               "tables beginning with the source inventory ({t_first}) and the counts behind the data-workflow figure "
               "({t_second}), followed by the tables of the article's appendix and the complete data tables. Figures "
               "are numbered S1 to {f_last_short} and tables S1 to {t_last_short} in a single sequential series."),
        "es": ("Contenido de esta parte. (a) Métodos suplementarios: la metodología extendida, que reescribe los "
               "Métodos del artículo con todos los estimadores, sus {neq} ecuaciones numeradas, citadas en el texto "
               "que las aplica, y las {nmt} tablas metodológicas ({mt_range}), impresas donde se comentan. (b) "
               "Láminas suplementarias: {nfig} láminas en {ngf} grupos temáticos (láminas suplementarias centrales; "
               "episodios hospitalarios; ruta administrativa REM agregada; denominadores, encuestas y educación; "
               "razón por sexo entre fuentes; diagnósticos de los modelos y sensibilidad a la definición de caso; "
               "análisis espacial y correlación territorial), cada una con su leyenda autónoma. (c) Tablas "
               "suplementarias: {ntab} tablas que comienzan con el inventario de fuentes ({t_first}) y los recuentos "
               "que sustentan la lámina de flujo de datos ({t_second}), seguidos por las tablas del apéndice del "
               "artículo y las tablas de datos completas. Las láminas se numeran de S1 a {f_last_short} y las tablas "
               "de S1 a {t_last_short} en una única serie secuencial."),
    },
    "figs_intro": {
        "en": ("The plates below are grouped by theme and keep the sequential numbering of the shared registry. Each "
               "is preceded by one or two sentences stating what it shows, its unit and its denominator, and carries "
               "a self-contained caption that states coverage, definition era, the number of reporting establishments "
               "or hospitals and the source file."),
        "es": ("Las láminas siguientes se agrupan por tema y conservan la numeración secuencial del registro "
               "compartido. Cada una va precedida de una o dos frases que indican qué muestra, su unidad y su "
               "denominador, y lleva una leyenda autónoma que declara cobertura, era de definición, número de "
               "establecimientos u hospitales reportantes y archivo de origen."),
    },
    "tabs_intro": {
        "en": ("The tables below keep the sequential numbering of the shared registry and carry the title and the note "
               "of their output file, which state unit, denominator, coverage, definition era, reporting N and source "
               "file. The {nmt} methodological tables ({mt_range}) are not repeated here: they are printed inside the "
               "extended methodology, where they are discussed. Cells with fewer than five events are suppressed in "
               "the territorial tables and survey domains with fewer than 30 cases or a relative standard error above "
               "30% are flagged and are not presented as reliable."),
        "es": ("Las tablas siguientes conservan la numeración secuencial del registro compartido y llevan el título y "
               "la nota de su archivo de salida, que declaran unidad, denominador, cobertura, era de definición, N "
               "informado y archivo de origen. Las {nmt} tablas metodológicas ({mt_range}) no se repiten aquí: se "
               "imprimen dentro de la metodología extendida, donde se comentan. Las celdas con menos de cinco eventos "
               "se suprimen en las tablas territoriales y los dominios de encuesta con menos de 30 casos o con un "
               "error estándar relativo superior al 30 % se marcan y no se presentan como fiables."),
    },
}


def _t(d: dict, lang: str) -> str:
    return d[lang]


def figure_intro(key: str, label: str, lang: str) -> str:
    """Frase de presentación de una lámina, con su rótulo ya resuelto por el registro."""
    if key not in FIGURE_INTRO:
        raise KeyError(f"falta la frase de presentación bilingüe de la lámina '{key}' en supplementary_material.py")
    return FIGURE_INTRO[key][lang].format(L=label)


_PLURAL = {"Table": "Tables", "Tabla": "Tablas", "Figure": "Figures", "Figura": "Figuras"}


def _range(labels: list[str]) -> str:
    """«Table S3» o «Tables S3–S12»: el plural se usa cuando el rango cubre más de un ítem."""
    if len(labels) == 1:
        return labels[0]
    word, first = labels[0].split()
    return f"{_PLURAL.get(word, word)} {first}–{labels[-1].split()[-1]}"


def _short(label: str) -> str:
    """Solo la parte numerada del rótulo («S54»), para no repetir la palabra en una enumeración."""
    return label.split()[-1]


def material_blocks(lang: str, variant: str, V: dict | None, R) -> list:
    """Bloques de la parte suplementaria: metodología extendida, láminas y tablas.

    `R` es el registro de numeración compartido de `prose_en`/`prose_es` (métodos `fig`, `tab`,
    `figure_block`, `table_block`). El orden de las listas de este módulo fija la numeración.
    """
    if lang not in LANGS:
        raise ValueError(f"idioma desconocido: {lang!r}")
    assert_legacy_unregistered_plates_current()
    blocks: list = []

    # (a) Metodología extendida (módulo 12), con sus ecuaciones y sus tablas metodológicas.
    methods = PME.methods_blocks(variant, V, lang, R=R)
    if not methods or methods[0][0] != "h1":
        raise RuntimeError("prose_methods_extended.methods_blocks debe empezar por un encabezado h1")
    methods[0] = ("h1", _t(W["methods_h1"], lang))
    blocks += methods

    # (b) Láminas suplementarias agrupadas por tema.
    blocks.append(("h1", _t(W["figs_h1"], lang)))
    blocks.append(("p", _t(W["figs_intro"], lang)))
    for title, keys in FIGURE_GROUPS:
        blocks.append(("h2", _t(title, lang)))
        for key in keys:
            label = R.fig(key)
            blocks.append(("p", figure_intro(key, label, lang)))
            blocks.append(R.figure_block(key, label))

    # (c) Tablas suplementarias (las metodológicas ya se imprimieron en la metodología extendida).
    mt_labels = [R.tab(key) for key in METHODS_TABLES]
    blocks.append(("h1", _t(W["tabs_h1"], lang)))
    blocks.append(("p", _t(W["tabs_intro"], lang).format(nmt=len(METHODS_TABLES), mt_range=_range(mt_labels))))
    for title, keys in TABLE_GROUPS:
        blocks.append(("h2", _t(title, lang)))
        for key in keys:
            blocks.append(R.table_block(key, R.tab(key)))
    return blocks


# Frase de apertura de la nota: el apéndice separado NO puede decir «el artículo impreso más arriba»
# (no hay artículo en ese archivo) ni «el mismo contenido está además disponible como apéndice separado»
# (ese archivo ES el apéndice). Cada documento recibe la suya.
OPENING = {
    "combined": {
        "en": ("This part is supplementary to the article printed above; it is not part of the main text and none of "
               "its content is required to read the article. The same content is also available as a separate "
               "appendix file, built from the same numbering registry, so a citation such as {ex} means the same item "
               "in both documents."),
        "es": ("Esta parte es suplementaria del artículo impreso más arriba; no forma parte del texto principal y "
               "nada de su contenido es necesario para leer el artículo. El mismo contenido está disponible además "
               "como archivo de apéndice separado, construido desde el mismo registro de numeración, de modo que una "
               "cita como {ex} designa el mismo ítem en ambos documentos."),
    },
    "standalone": {
        "en": ("This file is the supplementary appendix of the article; it is not part of the main text and none of "
               "its content is required to read the article. The same content is also printed after the References "
               "of the manuscript file, built from the same numbering registry, so a citation such as {ex} means the "
               "same item in both documents."),
        "es": ("Este archivo es el apéndice suplementario del artículo; no forma parte del texto principal y nada de "
               "su contenido es necesario para leer el artículo. El mismo contenido se imprime también tras las "
               "Referencias del archivo del manuscrito, construido desde el mismo registro de numeración, de modo "
               "que una cita como {ex} designa el mismo ítem en ambos documentos."),
    },
}


def part_texts(lang: str, R, standalone: bool = False) -> tuple[str, str]:
    """Nota y párrafo de índice de la parte suplementaria (mismas cifras en ambos idiomas).

    `standalone` distingue el apéndice separado del manuscrito combinado: la nota abre con una frase
    distinta en cada uno porque las dos afirmaciones de la otra serían falsas del propio archivo."""
    import equations_lancet as EQ  # import local: evita un ciclo si el módulo se importa temprano

    mt_labels = [R.tab(key) for key in METHODS_TABLES]
    fig_labels = [R.fig(key) for key in FIGURE_ORDER]
    tab_labels = [R.tab(key) for key in TABLE_ORDER]
    # La nota declara explícitamente la regla de numeración (secuencia temática, no orden de primera cita)
    # y la única excepción, las tablas metodológicas: la decisión está en lancet_americas/decision_log.md
    # (sección «2026-09-05 — Fase 4b · corrección de quince defectos», donde se fusionó el texto íntegro
    # de outputs/phase4b_decisions.md el 2026-09-06, antes de borrar ese archivo).
    opening = _t(OPENING["standalone" if standalone else "combined"], lang).format(ex=tab_labels[7])
    note = _t(W["note"], lang).format(opening=opening, nfig=len(FIGURE_ORDER), ntab=len(TABLE_ORDER),
                                      nmt=len(METHODS_TABLES))
    index = _t(W["index"], lang).format(
        neq=len(EQ.NUMBER), nmt=len(METHODS_TABLES), mt_range=_range(mt_labels),
        nfig=len(FIGURE_ORDER), ngf=len(FIGURE_GROUPS), ntab=len(TABLE_ORDER),
        t_first=tab_labels[0], t_second=tab_labels[1], t_last_short=_short(tab_labels[-1]),
        f_last_short=_short(fig_labels[-1]))
    return note, index


def counts() -> dict:
    """Tamaños del registro compartido: la ÚNICA fuente de «cuántas láminas / tablas / ecuaciones» hay.

    Cualquier documento o lámina que diga cuántas piezas suplementarias contiene el estudio debe leer esta
    función (o las listas que devuelve) y nunca contar archivos en disco: contar archivos daba 115 tablas en
    lugar de 125 (dejaba fuera las diez tablas metodológicas y colapsaba prefijos repetidos) y 44 ecuaciones en
    lugar de 33 (varias ecuaciones se componen de dos o tres PNG). La lámina de flujo de datos, su leyenda y su
    tabla de recuentos (Tabla S2) se comprueban contra estas cifras en
    `lancet_americas/pipeline/08d_figure_dataflow.py` y en `lancet_americas/tests/test_self_counts.py`.
    """
    import equations_lancet as EQ  # import local: evita un ciclo si el módulo se importa temprano

    return dict(figures=len(FIGURE_ORDER), tables=len(TABLE_ORDER), methods_tables=len(METHODS_TABLES),
                figure_groups=len(FIGURE_GROUPS), table_groups=len(TABLE_GROUPS), equations=len(EQ.NUMBER))


def inventory() -> list[dict]:
    """Inventario plano (tipo, clave, grupo temático) en el orden de numeración compartido."""
    rows: list[dict] = []
    group_of_fig = {key: title for title, keys in FIGURE_GROUPS for key in keys}
    group_of_tab = {key: title for title, keys in TABLE_GROUPS for key in keys}
    for i, key in enumerate(FIGURE_ORDER, 1):
        rows.append(dict(kind="figure", number=i, key=key, group_en=group_of_fig[key]["en"],
                         group_es=group_of_fig[key]["es"]))
    methods_group = {"en": "Extended methodology", "es": "Metodología extendida"}
    for i, key in enumerate(TABLE_ORDER, 1):
        group = group_of_tab.get(key, methods_group)
        rows.append(dict(kind="table", number=i, key=key, group_en=group["en"], group_es=group["es"]))
    return rows


if __name__ == "__main__":
    print(f"{len(FIGURE_ORDER)} láminas en {len(FIGURE_GROUPS)} grupos; "
          f"{len(TABLE_ORDER)} tablas ({len(METHODS_TABLES)} metodológicas dentro de la metodología extendida)")
    missing = [k for k in FIGURE_ORDER if k not in FIGURE_INTRO]
    print("láminas sin frase de presentación:", missing or "ninguna")
    print("claves duplicadas:", [k for k in set(FIGURE_ORDER) if FIGURE_ORDER.count(k) > 1]
          or [k for k in set(TABLE_ORDER) if TABLE_ORDER.count(k) > 1] or "ninguna")
    print("láminas huérfanas toleradas:", ", ".join(LEGACY_UNREGISTERED_PLATES) or "ninguna")
    print("entradas de tolerancia sin archivo:", ", ".join(stale_legacy_unregistered_plates()) or "ninguna")
