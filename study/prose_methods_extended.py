# -*- coding: utf-8 -*-
"""prose_methods_extended.py — metodología extendida bilingüe (módulo 12) para el material suplementario.

Expone `methods_blocks(variant, V, lang, R)` → lista de bloques de `docx_builder` con la metodología
extendida completa: diseño y fuentes, definiciones de caso y listas de códigos, denominadores y capas de
cobertura, **todos** los estimadores con su fórmula (bloques `eq` con los PNG de `equations.py` y su
número), controles de reproducción, estados del dato, rejilla de sensibilidad, software, semillas, mapa del
pipeline y limitaciones del método. El constructor del manuscrito la inserta como sección de la parte
suplementaria que sigue a las Referencias dentro del mismo archivo; los Métodos concisos del artículo no se
tocan y este módulo **no construye ningún documento**.

Reglas heredadas del estudio y respetadas en todo el texto:
  * los recuentos son reconocimiento administrativo, nunca prevalencia ni incidencia;
  * el resultado GRD es «episodios con F84 documentado» y F84 principal es una serie aparte;
  * las fuentes no se enlazan por persona: no hay cascada ni cocientes entre fuentes no enlazables;
  * la Ley 21.545 es contexto de política, nunca un efecto causal;
  * stocks (P2/P6, FONASA, APS, ISAPRE) y flujos (A03/A05/A27/A28, GRD, REM-20) no comparten eje;
  * lugar de atención (hospital GRD, establecimiento REM) y residencia (INE, comuna de residencia GRD) no se
    mezclan sin una nota explícita;
  * el panel hospitalario es 65 fijo / 65-65-65-65-68-72 observado; personas solo dentro de cada año;
  * las eras de definición REM nunca se unen con una línea;
  * cero, ausente y «no reportado» son estados distintos; celdas con menos de 5 eventos se suprimen;
  * los dominios de encuesta con menos de 30 casos o EER > 30 % se marcan y no se presentan como fiables.

Numeración: las tablas se rotulan con el registro `R` del módulo de prosa que llame (`R.tab(clave)` →
«Tabla S7»/«Table S7»), de modo que la serie es única y compartida con los documentos suplementarios
existentes. Si `R` no conoce las claves nuevas (no se edita `prose_en.py`/`prose_es.py` desde aquí), se usa
una numeración provisional `Tabla S<first_table + i>` que el constructor puede fijar con `first_table`.

API pública:
  methods_blocks(variant, V, lang, R=None, first_table=1)  → bloques de docx_builder
  table_specs(variant, lang, V)                            → {clave: dict(df, title, note, numeric)}
  TABLE_KEYS                                               → claves de tabla en orden de aparición
  word_count(blocks)                                       → palabras del cuerpo (sin marcadores de cita)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TIDY = OUT / "tidy"
CONTROLS_DIR = OUT / "controls"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import config as CFG  # noqa: E402
import controls_registry as CR  # noqa: E402  (ámbitos con nombre de los controles: una sola fuente por total)
import equations as EQ  # noqa: E402
import labels as LBL  # noqa: E402  (rótulos compartidos: nunca literales sueltos para los conceptos del estudio)
from common import fmt_number  # noqa: E402

LANGS = ("es", "en")

# ---------------------------------------------------------------------------
# Utilidades de idioma y de valores
# ---------------------------------------------------------------------------


def _t(d, lang: str) -> str:
    """Selecciona el idioma de un dict {'es': ..., 'en': ...}; una cadena suelta se devuelve tal cual.

    Un nombre propio (por ejemplo «REM Serie A (A03, A05, A27, A28)») se escribe una sola vez; solo los que
    llevan una glosa descriptiva del estudio se declaran en los dos idiomas."""
    return d[lang] if isinstance(d, dict) else str(d)


#: Marcadores comodín de las rutas declaradas por `equations.ESTIMATORS` y por `PIPELINE_MAP`. La forma
#: canónica está escrita en español; el documento en inglés imprime la forma inglesa, porque «outputs/<variante>/
#: <idioma>/…» dentro del documento en inglés es texto en español y así lo señala tests/test_language_purity.py.
PATH_PLACEHOLDERS: dict[str, str] = {"<variante>": "<variant>", "<idioma>": "<language>", "<clave>": "<key>",
                                     "<indicador>": "<indicator>", "<módulo>": "<module>"}


def _paths(text: str, lang: str) -> str:
    """Ruta declarada con sus marcadores comodín en el idioma del documento."""
    out = str(text)
    if lang == "es":
        return out
    for es, en in PATH_PLACEHOLDERS.items():
        out = out.replace(es, en)
    return out


class _V:
    """Accesor tolerante de `outputs/values_<variante>.json`: nunca escribe una cifra literal, y si una clave
    falta devuelve el guion largo en vez de romper la construcción del documento."""

    def __init__(self, values: dict | None, lang: str):
        self.values = values or {}
        self.lang = lang
        self.missing: list[str] = []

    def raw(self, key: str, default=None):
        if key in self.values:
            return self.values[key]
        if key not in self.missing:
            self.missing.append(key)
        return default

    def num(self, key: str, dec=0):
        value = self.raw(key)
        if value is None or isinstance(value, str):
            return "—"
        return fmt_number(value, dec, self.lang)


def _label(R, key: str, lang: str, fallback_number: int) -> str:
    """Rótulo de tabla: el del registro compartido si lo conoce, si no uno provisional «Tabla S<n>»."""
    if R is not None:
        fn = getattr(R, "tab", None)
        if callable(fn):
            try:
                return fn(key)
            except Exception:
                pass
    word = "Tabla" if lang == "es" else "Table"
    return f"{word} S{fallback_number}"


# ---------------------------------------------------------------------------
# Catálogos usados por las tablas de la metodología
# ---------------------------------------------------------------------------
ICD_F84 = {
    "F84": {"es": "Trastornos generalizados del desarrollo (categoría de tres caracteres)",
            "en": "Pervasive developmental disorders (three-character category)"},
    "F840": {"es": "Autismo en la niñez", "en": "Childhood autism"},
    "F841": {"es": "Autismo atípico", "en": "Atypical autism"},
    "F842": {"es": "Síndrome de Rett", "en": "Rett syndrome"},
    "F843": {"es": "Otro trastorno desintegrativo de la niñez", "en": "Other childhood disintegrative disorder"},
    "F844": {"es": "Trastorno hiperactivo asociado con retraso mental y movimientos estereotipados",
             "en": "Overactive disorder associated with mental retardation and stereotyped movements"},
    "F845": {"es": "Síndrome de Asperger", "en": "Asperger syndrome"},
    "F848": {"es": "Otros trastornos generalizados del desarrollo", "en": "Other pervasive developmental disorders"},
    "F849": {"es": "Trastorno generalizado del desarrollo, no especificado",
             "en": "Pervasive developmental disorder, unspecified"},
}

# Módulo REM, era y uso de cada código de `config.py` (el orden fija el orden de la tabla M3).
REM_CODE_SPEC: list[tuple[str, str, str, dict]] = []
for _k, _c in CFG.A03_LEGACY.items():
    REM_CODE_SPEC.append(("A03", _c, "2019–2022/2024",
                          {"es": "Detección: contexto del control de 18 meses (03500404/03500405) y tamizaje M-CHAT en el subgrupo con alteración de lenguaje o área social (03500406/03500407); nunca cobertura poblacional de tamizaje.",
                           "en": "Detection: 18-month check-up context (03500404/03500405) and M-CHAT screening within the subgroup with language or social-area alteration (03500406/03500407); never population screening coverage."}))
for _k, _c in CFG.A03_2023_2024.items():
    REM_CODE_SPEC.append(("A03", _c, "2023–2024",
                          {"es": "Detección M-CHAT-R/F 16–30 meses: categorías de riesgo bajo, medio y alto, segunda parte y referencia; era nueva, no comparable con 2019–2022.",
                           "en": "M-CHAT-R/F detection at 16–30 months: low, medium and high risk, second stage and referral; a new era, not comparable with 2019–2022."}))
for _k, _c in CFG.A03_2024_31_59.items():
    REM_CODE_SPEC.append(("A03", _c, "2024",
                          {"es": "Detección 31–59 meses añadida en 2024: evaluación, sospecha, alerta y referencia.",
                           "en": "Detection at 31–59 months added in 2024: evaluation, suspicion, alert and referral."}))
for _k, _c in CFG.A03_2025.items():
    REM_CODE_SPEC.append(("A03", _c, "2025",
                          {"es": "Rediseño 2025 (16–30 y 30–59 meses): motivo de aplicación, nivel de riesgo y necesidad de referencia; era propia.",
                           "en": "2025 redesign (16–30 and 30–59 months): reason for application, risk level and need for referral; its own era."}))
for _k, _c in CFG.A05_ENTRY.items():
    REM_CODE_SPEC.append(("A05", _c, "2021–2025",
                          {"es": "Ingreso a programa de salud mental por categoría diagnóstica del espectro; 05990022 es la serie estricta de autismo.",
                           "en": "Mental-health programme entry by spectrum diagnostic category; 05990022 is the strict autism series."}))
for _k, _c in CFG.A05_EXIT.items():
    REM_CODE_SPEC.append(("A05", _c, "2021–2025",
                          {"es": "Egreso del programa de salud mental por la misma categoría; nunca se resta del ingreso para construir una prevalencia.",
                           "en": "Mental-health programme exit for the same category; never subtracted from entries to build a prevalence."}))
for _k, _c in CFG.A05_BROAD_PRE2021.items():
    REM_CODE_SPEC.append(("A05", _c, "2019–2020",
                          {"es": "TGD amplio previo a 2021 (ingreso/egreso); contiene Rett de forma inseparable y solo se presenta como sensibilidad marcada.",
                           "en": "Broad PDD before 2021 (entry/exit); inseparably includes Rett and is shown only as a flagged sensitivity."}))
for _k, _c in CFG.A27.items():
    REM_CODE_SPEC.append(("A27", _c, "2023–2025",
                          {"es": "Consejería y referencia asistida específicas del tamizaje M-CHAT-R/F desde 2023; cuenta intervenciones, no personas.",
                           "en": "Counselling and assisted referral specific to M-CHAT-R/F screening from 2023; counts interventions, not people."}))
for _k, _c in CFG.A28.items():
    REM_CODE_SPEC.append(("A28", _c, "2023–2025",
                          {"es": "Ingresos por TEA a rehabilitación de base comunitaria (primaria) y hospitalaria desde 2023.",
                           "en": "ASD entries to community-based (primary) and hospital rehabilitation from 2023."}))
REM_CODE_SPEC.append(("P2", CFG.P2_TEA, "2019–2025",
                      {"es": "Stock semestral de niños, niñas y adolescentes con TEA bajo control en el programa NANEAS; diciembre es el principal y junio la sensibilidad; nunca se suman.",
                       "en": "Half-yearly stock of children and adolescents with ASD under control in the NANEAS programme; December is primary and June the sensitivity; never summed."}))
REM_CODE_SPEC.append(("P2", CFG.P2_NANEAS_TOTAL, "2023–2025",
                      {"es": "Total NANEAS bajo control, disponible solo desde diciembre de 2023; único denominador admisible para la proporción TEA/NANEAS.",
                       "en": "Total NANEAS under control, available only from December 2023; the only admissible denominator for the ASD/NANEAS proportion."}))
for _k, _c in CFG.P6_PRIMARY.items():
    REM_CODE_SPEC.append(("P6", _c, "2021–2025",
                          {"es": "Stock de población bajo control en salud mental de atención primaria por categoría del espectro.",
                           "en": "Stock of the population under mental-health control in primary care by spectrum category."}))
for _k, _c in CFG.P6_SPECIALTY.items():
    REM_CODE_SPEC.append(("P6", _c, "2021–2025",
                          {"es": "Stock de población bajo control en salud mental de especialidad por categoría del espectro.",
                           "en": "Stock of the population under specialty mental-health control by spectrum category."}))
for _k, _c in CFG.P6_BROAD_PRE2021.items():
    REM_CODE_SPEC.append(("P6", _c, "2019–2020",
                          {"es": "TGD amplio previo a 2021 en atención primaria y especialidad; contiene Rett y solo es sensibilidad marcada.",
                           "en": "Broad PDD before 2021 in primary and specialty care; includes Rett and is only a flagged sensitivity."}))

# Mapa del pipeline: descripción y salidas principales por script (los archivos que no estén en el mapa se
# listan igualmente con una descripción genérica, para que la tabla siga el estado real del directorio).
PIPELINE_MAP: dict[str, dict] = {
    "00_provenance.py": {
        "what": {"es": "Congela la procedencia: SHA-256, tamaño, fecha, unidad, período, cobertura, geografía, columnas y restricciones de uso de cada artefacto fuente.",
                 "en": "Freezes provenance: SHA-256, size, date, unit, period, coverage, geography, columns and use restrictions of every source artefact."},
        "outputs": "outputs/tidy/data_provenance.csv; provenance_manifest_checks.csv; provenance_summary_by_source.csv"},
    "01_grd_core.py": {
        "what": {"es": "Núcleo hospitalario GRD 2019–2024: episodios con F84 por posición, panel observado y fijo, actividad, edad, sexo, hospital y profundidad diagnóstica.",
                 "en": "GRD hospital core 2019–2024: episodes with F84 by position, observed and fixed panel, activity, age, sex, hospital and coding depth."},
        "outputs": "outputs/tidy/grd_year_summary.csv; grd_hospital_year.csv; grd_age_sex_year.csv; grd_coding_depth_year.csv; grd_fixed_panel_hospitals.csv"},
    "01b_deis_egresos.py": {
        "what": {"es": "Egresos DEIS 2019–2024 con F84 en el diagnóstico principal (DEIS no publica secundarios); comparación con GRD principal.",
                 "en": "DEIS discharges 2019–2024 with F84 as principal diagnosis (DEIS publishes no secondary diagnoses); comparison with GRD principal."},
        "outputs": "outputs/tidy/deis_year_summary.csv; deis_vs_grd_year.csv; deis_age_sex_year.csv"},
    "02_rem_pathway.py": {
        "what": {"es": "Ruta administrativa REM: tabla establecimiento × mes/semestre × código × año conservando cero, vacío y ausencia de reporte como estados distintos.",
                 "en": "REM administrative pathway: establishment × month/half-year × code × year table keeping zero, empty and absence of reporting as distinct states."},
        "outputs": "outputs/tidy/rem_pathway_tidy.csv; rem_pathway_annual.csv; rem_establishment_year.csv; rem_code_dictionary_check.csv"},
    "03_denominators.py": {
        "what": {"es": "Cuatro capas de denominador (INE, FONASA/ISAPRE, inscritos APS, REM-20) armonizadas entre cambios de esquema, con crosswalk comunal auditable.",
                 "en": "Four denominator layers (INE, FONASA/ISAPRE, APS enrolment, REM-20) harmonised across schema changes, with an auditable comuna crosswalk."},
        "outputs": "outputs/tidy/coverage_layers_year.csv; ine_population_comuna_year_age_sex.csv; comuna_crosswalk.csv; rem20_panel.csv; aps_panel.csv"},
    "04_surveys.py": {
        "what": {"es": "ENDIDE 2022 y ENCAVI 2023–2024 con diseño complejo: proporción, total ponderado, EE por linealización de Taylor, IC logit, DEFF y EER.",
                 "en": "ENDIDE 2022 and ENCAVI 2023–2024 with complex design: proportion, weighted total, Taylor-linearised SE, logit CI, DEFF and RSE."},
        "outputs": "outputs/tidy/survey_estimates.csv; survey_design_check.csv; survey_items_dictionary.csv"},
    "05_education.py": {
        "what": {"es": "Triangulación educativa: PIE TEA estricto, TEA-Asperger y armonizado (Apuntes y SINACES) y JUNAEB EVE con el ponderador EXP.",
                 "en": "Education triangulation: strict ASD, ASD-Asperger and harmonised PIE (Apuntes and SINACES) and JUNAEB EVE with the EXP weight."},
        "outputs": "outputs/tidy/pie_series.csv; junaeb_tea_year_level.csv; education_summary_year.csv"},
    "06_models.py": {
        "what": {"es": "Modelos: tendencias cuasi-Poisson con desplazamiento, tasas estandarizadas, efectos fijos de hospital, intercepto aleatorio, Durbin–Watson e índices de convergencia.",
                 "en": "Models: quasi-Poisson trends with offsets, standardised rates, hospital fixed effects, random intercept, Durbin–Watson and convergence indices."},
        "outputs": "outputs/tidy/models_summary.csv; models_fitted.csv; models_population_rates.csv; models_a05_standardised_rates.csv; hospital_effects.csv; models_convergence_index.csv; outputs/<variante>/<idioma>/figures/figS4_models_cpa.png, figS7_rem_education_models.png"},
    "07_controls.py": {
        "what": {"es": "Consolida los controles de reproducción de todos los módulos y compara esperado frente a observado.",
                 "en": "Consolidates the reproduction controls of every module and compares expected against observed."},
        "outputs": "outputs/controls/controls_summary.csv; controls_summary.md"},
    "08a_figures_grd.py": {"what": {"es": "Láminas del núcleo hospitalario GRD.", "en": "Plates of the GRD hospital core."},
                           "outputs": "outputs/<variante>/<idioma>/figures/fig2_grd_core.png, fig1_sources_coverage.png, figS1_grd_variants.png, figS2_grd_subcodes.png, figS3_grd_hospital_effects.png"},
    "08b_figures_rem.py": {"what": {"es": "Láminas de la ruta administrativa REM, facetadas por era de definición.",
                                    "en": "Plates of the REM administrative pathway, facetted by definition era."},
                           "outputs": "outputs/<variante>/<idioma>/figures/fig3_rem_pathway.png, figS5_rem_june_december.png, figS6_rem_stable_panel.png, figS8_a05_age_sex.png, figS13_rem_seasonality.png"},
    "08c_figures_triangulation.py": {"what": {"es": "Láminas de triangulación entre salud, encuestas y educación.",
                                              "en": "Triangulation plates across health, surveys and education."},
                                     "outputs": "outputs/<variante>/<idioma>/figures/fig4_triangulation.png, figS9_regional_maps.png, figS10_denominators.png, figS11_coverage_age_sex.png, figS12_junaeb_sex_level.png, figS14_deis_sex_age.png, figS15_controls.png"},
    "09a_tables_main.py": {"what": {"es": "Tablas principales formateadas por variante e idioma.", "en": "Main tables formatted by variant and language."},
                           "outputs": "outputs/<variante>/<idioma>/tables/T*.csv (+ _numeric.csv, titles.json)"},
    "09b_tables_supplementary.py": {"what": {"es": "Tablas suplementarias formateadas por variante e idioma.",
                                             "en": "Supplementary tables formatted by variant and language."},
                                    "outputs": "outputs/<variante>/<idioma>/tables/S*.csv, ST*.csv (+ _numeric.csv, titles.json)"},
    "10_manuscript.py": {"what": {"es": "Construye los manuscritos y apéndices Word/PDF con docx_builder y los bloques de prosa.",
                                  "en": "Builds the Word/PDF manuscripts and appendices with docx_builder and the prose blocks."},
                         "outputs": "manuscript/manuscript_<variante>_<idioma>.docx; build_report.json"},
    "11_grd_episode_detail.py": {"what": {"es": "Detalle episódico GRD: calendario mensual, estadía, características del episodio, co-diagnósticos, reingresos, multiplicidad, territorio y edad simple.",
                                          "en": "GRD episode detail: monthly calendar, length of stay, episode features, co-diagnoses, readmissions, multiplicity, territory and single-year age."},
                                 "outputs": "outputs/tidy/grd_monthly.csv; grd_length_of_stay.csv; grd_episode_features.csv; grd_codiagnoses.csv; grd_readmission.csv; grd_territory.csv"},
    "12_methods_extended.py": {"what": {"es": "Compone las ecuaciones, verifica los bloques de la metodología extendida en ambos idiomas y variantes, y escribe sus tablas y controles.",
                                        "en": "Renders the equations, verifies the extended-methodology blocks in both languages and variants, and writes its tables and controls."},
                               "outputs": "outputs/equations/eq_*.png; outputs/<variante>/<idioma>/extra/tables/M*.csv; outputs/controls/12_methods_extended_controls.csv"},
    "08d_figure_dataflow.py": {"what": {"es": "Lámina de flujo de datos (Figura 1): qué es una fila en cada fuente (registros o personas), cuántas hay a la entrada y tras la selección de autismo con sus exclusiones, y qué se cuenta al final y contra qué denominador, con el aviso de que ningún registro se enlaza entre sistemas.",
                                        "en": "Data-workflow plate (Figure 1): what one row is in each source (records or people), how many there are at entry and after the autism selection with its exclusions, and what is finally counted against which denominator, with the warning that no record is linked across systems."},
                               "outputs": "outputs/<variante>/<idioma>/figures/fig1_dataflow.png; outputs/tidy/dataflow_counts.csv"},
    "13_extra_figures_hospital.py": {"what": {"es": "Láminas y tablas suplementarias del núcleo hospitalario (EF1–EF10): calendario, estadía, características del episodio, gravedad y letalidad, co-diagnósticos, reingresos, edad, hospitales y detalle DEIS.",
                                              "en": "Supplementary hospital plates and tables (EF1–EF10): calendar, length of stay, episode features, severity and lethality, co-diagnoses, readmissions, age, hospitals and DEIS detail."},
                                     "outputs": "outputs/<variante>/<idioma>/extra/figures/EF*.png; extra/tables/EF*.csv"},
    "14_extra_figures_rem.py": {"what": {"es": "Láminas y tablas suplementarias de la ruta REM (E11–E19): A03 por era, A05 regional y por edad y sexo, P2/P6, A27/A28, distribución por establecimiento, series mensuales y sensibilidad por era.",
                                         "en": "Supplementary REM plates and tables (E11–E19): A03 by era, A05 by region and by age and sex, P2/P6, A27/A28, distribution across establishments, monthly series and definition-era sensitivity."},
                                "outputs": "outputs/<variante>/<idioma>/extra/figures/E1*.png; extra/tables/E1*.csv"},
    "15_extra_figures_context.py": {"what": {"es": "Láminas y tablas suplementarias de contexto (E20 en adelante): estructura poblacional, cobertura de aseguramiento, capacidad REM-20, encuestas, educación, comparación entre fuentes y razón de sexos multifuente.",
                                             "en": "Supplementary context plates and tables (E20 onwards): population structure, insurance coverage, REM-20 capacity, surveys, education, cross-source comparison and multisource sex ratio."},
                                    "outputs": "outputs/<variante>/<idioma>/extra/figures/E2*.png; extra/tables/E2*.csv"},
    "15b_spatial_correlation.py": {"what": {"es": "Análisis espacial y de correlación territorial completo: indicadores comunales, estandarización indirecta y suavizamiento bayesiano empírico, I de Moran global y bivariada, LISA y Gi* con umbral de Benjamini–Hochberg, correlación entre sistemas, Lorenz/Gini y Theil, estabilidad de rangos, privación SAE y sensibilidades de pesos, escala y denominador.",
                                            "en": "Full spatial and territorial-correlation analysis: comuna indicators, indirect standardisation and empirical-Bayes smoothing, global and bivariate Moran's I, LISA and Gi* with the Benjamini–Hochberg threshold, cross-system correlation, Lorenz/Gini and Theil, rank stability, SAE deprivation and sensitivities of weights, scale and denominator."},
                                   "outputs": "outputs/tidy/spatial_<indicador>.csv; outputs/<variante>/<idioma>/extra/figures/E4*.png; extra/tables/E4*.csv"},
    "16_extra_tables.py": {"what": {"es": "Serie ampliada de tablas suplementarias (E60–E81) construida solo desde tablas tidy y controles ya verificados, incluido el inventario de activos del proyecto.",
                                    "en": "Extended series of supplementary tables (E60–E81) built only from already verified tidy tables and controls, including the project's asset inventory."},
                           "outputs": "outputs/<variante>/<idioma>/extra/tables/E6*.csv, E7*.csv, E8*.csv"},
    "17_extended_material.py": {"what": {"es": "Verifica la parte suplementaria dentro del manuscrito (inventario, numeración, límites del artículo, ecuaciones y agregados) y ordena la construcción de los documentos.",
                                         "en": "Verifies the supplementary part inside the manuscript (inventory, numbering, article limits, equations and aggregates) and drives the build of the documents."},
                                "outputs": "outputs/controls/17_extended_material_controls.csv; extended_material_index.md"},
}

# Rejilla de sensibilidad preespecificada (una fila por análisis).
SENSITIVITY_GRID: list[dict] = [
    dict(analysis={"es": "Definición de caso GRD", "en": "GRD case definition"},
         primary={"es": "Familia F84 completa (con_rett)", "en": "Full F84 family (con_rett)"},
         variation={"es": "F84 sin F84.2 (sin_rett) y F84.0 estricto", "en": "F84 excluding F84.2 (sin_rett) and strict F84.0"},
         threat={"es": "Taxonomía: el síndrome de Rett dejó de considerarse del espectro en el DSM-5.",
                 "en": "Taxonomy: Rett syndrome is no longer within the spectrum in DSM-5."},
         output="outputs/tidy/grd_year_summary.csv; grd_subcode_year.csv"),
    dict(analysis={"es": "Posición del código", "en": "Code position"},
         primary={"es": "F84 en cualquier posición (DIAGNOSTICO1–35)", "en": "F84 in any position (DIAGNOSTICO1–35)"},
         variation={"es": "F84 principal y F84 solo secundario", "en": "F84 principal and F84 secondary-only"},
         threat={"es": "El episodio con F84 secundario no es una hospitalización por autismo.",
                 "en": "An episode with secondary F84 is not a hospitalisation for autism."},
         output="outputs/tidy/grd_year_summary.csv"),
    dict(analysis={"es": "Panel hospitalario", "en": "Hospital panel"},
         primary={"es": "Panel anual observado (65, 65, 65, 65, 68 y 72 hospitales)", "en": "Observed annual panel (65, 65, 65, 65, 68 and 72 hospitals)"},
         variation={"es": "Panel fijo de 65 hospitales presentes en todos los años 2019–2024",
                    "en": "Fixed panel of 65 hospitals present in every year 2019–2024"},
         threat={"es": "Expansión del panel: los hospitales nuevos aportan episodios sin cambio de práctica.",
                 "en": "Panel expansion: new hospitals contribute episodes without any change in practice."},
         output="outputs/tidy/grd_year_summary.csv; grd_fixed_panel_hospitals.csv"),
    dict(analysis={"es": "Modalidad de atención", "en": "Activity type"},
         primary={"es": "Todos los episodios GRD", "en": "All GRD episodes"},
         variation={"es": "Hospitalización estricta y cirugía mayor ambulatoria por separado", "en": "Strict hospitalisation and major ambulatory surgery separately"},
         threat={"es": "Mezcla de modalidades con denominadores y duración distintos.",
                 "en": "Mixing activity types with different denominators and duration."},
         output="outputs/tidy/grd_activity_categories_year.csv"),
    dict(analysis={"es": "Profundidad diagnóstica", "en": "Coding depth"},
         primary={"es": "Modelo sin ajuste", "en": "Unadjusted model"},
         variation={"es": "Ajuste por la profundidad media del panel y estratificación por profundidad",
                    "en": "Adjustment for the panel's mean depth and stratification by depth"},
         threat={"es": "Intensidad de codificación: más diagnósticos por episodio aumentan la captura de F84 secundario.",
                 "en": "Coding intensity: more diagnoses per episode increase the capture of secondary F84."},
         output="outputs/tidy/grd_coding_depth_year.csv; models_summary.csv"),
    dict(analysis={"es": "Disrupción 2020–2021", "en": "2020–2021 disruption"},
         primary={"es": "Tendencia sin indicador", "en": "Trend without an indicator"},
         variation={"es": "Indicador de disrupción de reporte y ventana 2021–2024", "en": "Reporting-disruption indicator and 2021–2024 window"},
         threat={"es": "Pandemia: caída y recuperación del registro, no del fenómeno.",
                 "en": "Pandemic: a fall and recovery of recording, not of the phenomenon."},
         output="outputs/tidy/models_summary.csv"),
    dict(analysis={"es": "Denominador hospitalario", "en": "Hospital denominator"},
         primary={"es": "Episodios GRD del mismo año y panel", "en": "GRD episodes of the same year and panel"},
         variation={"es": "Población INE por edad y sexo (lectura poblacional complementaria)",
                    "en": "INE population by age and sex (complementary population reading)"},
         threat={"es": "Numerador por lugar de atención frente a denominador por residencia.",
                 "en": "Place-of-care numerator against a residence denominator."},
         output="outputs/tidy/models_population_rates.csv"),
    dict(analysis={"es": "Unidad del modelo", "en": "Model unit"},
         primary={"es": "Serie nacional anual", "en": "National annual series"},
         variation={"es": "Hospital-año con efectos fijos, EE robustos por hospital e intercepto aleatorio",
                    "en": "Hospital-year with fixed effects, hospital-clustered SE and a random intercept"},
         threat={"es": "Heterogeneidad y conglomerado por establecimiento.", "en": "Heterogeneity and clustering by establishment."},
         output="outputs/tidy/hospital_effects.csv"),
    dict(analysis={"es": "Fuente hospitalaria", "en": "Hospital source"},
         primary={"es": "GRD público", "en": "Public GRD"},
         variation={"es": "Egresos DEIS con F84 principal (única posición publicada)", "en": "DEIS discharges with principal F84 (the only published position)"},
         threat={"es": "Cobertura y reglas de codificación distintas entre sistemas de registro hospitalario.",
                 "en": "Different coverage and coding rules between hospital recording systems."},
         output="outputs/tidy/deis_vs_grd_year.csv"),
    dict(analysis={"es": "Definición REM de ingreso", "en": "REM entry definition"},
         primary={"es": "Autismo estricto A05 05990022, 2021–2025", "en": "Strict autism A05 05990022, 2021–2025"},
         variation={"es": "Familia TGD de la variante y TGD amplio 2019–2020 en panel separado",
                    "en": "The variant's PDD family and broad PDD 2019–2020 in a separate panel"},
         threat={"es": "Quiebre de definición: las eras no son comparables y no se unen con una línea.",
                 "en": "Definition break: eras are not comparable and are never joined by a line."},
         output="outputs/tidy/rem_pathway_annual.csv"),
    dict(analysis={"es": "Desplazamiento REM", "en": "REM offset"},
         primary={"es": "Población INE", "en": "INE population"},
         variation={"es": "Establecimientos reportantes y panel estable de establecimientos",
                    "en": "Reporting establishments and the stable establishment panel"},
         threat={"es": "Expansión del reporte: más establecimientos informando elevan el recuento sin cambio de práctica.",
                 "en": "Reporting expansion: more establishments reporting raise the count without any change in practice."},
         output="outputs/tidy/rem_establishment_year.csv; models_summary.csv"),
    dict(analysis={"es": "Semestre de los stocks", "en": "Half-year of the stocks"},
         primary={"es": "Stock de diciembre (P2, P6)", "en": "December stock (P2, P6)"},
         variation={"es": "Stock de junio como sensibilidad; los semestres nunca se suman",
                    "en": "June stock as a sensitivity; half-years are never summed"},
         threat={"es": "Confundir un stock semestral con un flujo anual.", "en": "Confusing a half-yearly stock with an annual flow."},
         output="outputs/tidy/rem_pathway_annual.csv"),
    dict(analysis={"es": "Definición educativa", "en": "Education definition"},
         primary={"es": "PIE armonizado (TEA + TEA-Asperger)", "en": "Harmonised PIE (ASD + ASD-Asperger)"},
         variation={"es": "TEA estricto y TEA-Asperger por separado; Apuntes 2019–2023 frente a SINACES 2024–2025",
                    "en": "Strict ASD and ASD-Asperger separately; Apuntes 2019–2023 against SINACES 2024–2025"},
         threat={"es": "Cambio de categorías y de informe oficial (incluida la discrepancia de cinco casos de 2022).",
                 "en": "Change of categories and of official report (including the five-case 2022 discrepancy)."},
         output="outputs/tidy/pie_series.csv"),
    dict(analysis={"es": "Dominio de encuesta", "en": "Survey domain"},
         primary={"es": "Autismo reportado, dominio nacional", "en": "Reported autism, national domain"},
         variation={"es": "Confirmación profesional; dominios por sexo y edad con marca de imprecisión",
                    "en": "Professional confirmation; sex and age domains flagged for imprecision"},
         threat={"es": "Tamaño efectivo insuficiente: menos de 30 casos o EER > 30 %.",
                 "en": "Insufficient effective size: fewer than 30 cases or RSE > 30%."},
         output="outputs/tidy/survey_estimates.csv"),
    dict(analysis={"es": "Base poblacional", "en": "Population base"},
         primary={"es": "Proyecciones INE base Censo 2017", "en": "INE projections, 2017-census base"},
         variation={"es": "Censo 2024 y base 2024 como puente, siempre con marca explícita",
                    "en": "Censo 2024 and the 2024 base as a bridge, always explicitly flagged"},
         threat={"es": "Cambio de base censal: las series no se combinan sin marca.",
                 "en": "Change of census base: series are never combined without a flag."},
         output="outputs/tidy/ine_population_base_comparison.csv; ine_population_sensitivity.csv"),
    dict(analysis={"es": "Análisis territorial", "en": "Territorial analysis"},
         primary={"es": "Razón indirectamente estandarizada por comuna, suavizada por bayes empírico, con contigüidad reina",
                  "en": "Indirectly standardised ratio by comuna, empirical-Bayes smoothed, with queen contiguity"},
         variation={"es": "Razón cruda frente a suavizada; pesos de k = 4, k = 8 y distancia inversa; escala regional; "
                          "exclusión de la Región Metropolitana, de las comunas con menos de 5 eventos y de las no "
                          "continentales; denominador del Censo 2024",
                    "en": "Crude against smoothed ratio; k = 4, k = 8 and inverse-distance weights; regional scale; "
                          "exclusion of the Metropolitan Region, of comunas with fewer than 5 events and of the "
                          "non-continental ones; 2024 Census denominator"},
         threat={"es": "Recuentos pequeños, problema de la unidad de área modificable y riesgo de reidentificación.",
                 "en": "Small counts, the modifiable areal unit problem and re-identification risk."},
         output="outputs/tidy/grd_territory.csv; spatial_comuna_standardised.csv; spatial_moran.csv; "
                "spatial_denominator_sensitivity.csv"),
]

# Estados del dato (cero, ausente, no reportado, no estimable, suprimido).
DATA_STATES: list[dict] = [
    dict(state={"es": "Cero observado", "en": "Observed zero"},
         tidy={"es": "0 en la columna de recuento con la fila presente", "en": "0 in the count column with the row present"},
         published={"es": "0", "en": "0"},
         rule={"es": "El establecimiento informó y no registró eventos; nunca se convierte en ausente.",
               "en": "The establishment reported and recorded no events; never converted into missing."}),
    dict(state={"es": "Celda vacía del REM", "en": "Empty REM cell"},
         tidy={"es": "cadena vacía conservada como texto (las columnas Col01–Col50 se leen como texto)",
               "en": "empty string kept as text (columns Col01–Col50 are read as text)"},
         published={"es": "—", "en": "—"},
         rule={"es": "Vacío no es cero: la fila existe pero la celda no se completó.",
               "en": "Empty is not zero: the row exists but the cell was not filled in."}),
    dict(state={"es": "Establecimiento sin fila", "en": "Establishment with no row"},
         tidy={"es": "ausencia de fila; se cuenta en «establecimientos reportantes»",
               "en": "no row at all; counted in 'reporting establishments'"},
         published={"es": "no reportado", "en": "not reported"},
         rule={"es": "No se imputa ni se interpola; el número de establecimientos reportantes acompaña a toda cifra REM.",
               "en": "Never imputed or interpolated; the number of reporting establishments accompanies every REM figure."}),
    dict(state={"es": "Fecha o edad no analizable", "en": "Unparsable date or age"},
         tidy={"es": "fila «mes = 0» o grupo etario «desconocido», con el recuento informado",
               "en": "'month = 0' row or 'unknown' age group, with the count reported"},
         published={"es": "desconocido (n informado)", "en": "unknown (n reported)"},
         rule={"es": "Se informan y se excluyen del estadístico correspondiente; nunca se imputan.",
               "en": "Reported and excluded from the corresponding statistic; never imputed."}),
    dict(state={"es": "Categoría «no informado»", "en": "'Not reported' category"},
         tidy={"es": "valor propio en la variable (previsión, nacionalidad, etnia, sexo)",
               "en": "its own value in the variable (insurance, nationality, ethnicity, sex)"},
         published={"es": "no informado", "en": "not reported"},
         rule={"es": "Es una categoría de respuesta, no un dato perdido, y se muestra como tal.",
               "en": "A response category, not a missing value, and shown as such."}),
    dict(state={"es": "Recuento de 1 a 4", "en": "Count of 1 to 4"},
         tidy={"es": "valor real más suppression_flag = 1 y n_display = «<5»", "en": "true value plus suppression_flag = 1 and n_display = '<5'"},
         published={"es": "<5", "en": "<5"},
         rule={"es": "Regla de supresión (ecuación 33) en toda tabla territorial; si la fila queda con una sola celda suprimida se suprime la siguiente menor.",
               "en": "Suppression rule (equation 33) in every territorial table; if a row is left with one suppressed cell, the next smallest is also suppressed."}),
    dict(state={"es": "Dominio de encuesta impreciso", "en": "Imprecise survey domain"},
         tidy={"es": "precision_flag = imprecise con DEFF y EER en la misma fila", "en": "precision_flag = imprecise with DEFF and RSE in the same row"},
         published={"es": "cifra con marca de imprecisión", "en": "figure flagged as imprecise"},
         rule={"es": "Menos de 30 casos no ponderados o EER > 30 %: se muestra como orden de magnitud, nunca como estimación nacional.",
               "en": "Fewer than 30 unweighted cases or RSE > 30%: shown as an order of magnitude, never as a national estimate."}),
    dict(state={"es": "No estimable", "en": "Not estimable"},
         tidy={"es": "NaN con la razón documentada (por ejemplo, variable TEA de 1.º medio vacía en JUNAEB 2024)",
               "en": "NaN with the reason documented (for example, the empty 1.º medio ASD variable in JUNAEB 2024)"},
         published={"es": "n/e", "en": "n/e"},
         rule={"es": "Nunca se escribe cero cuando la variable no fue recogida o no está poblada.",
               "en": "Never written as zero when the variable was not collected or is not populated."}),
]

# Fuentes, unidad de observación y regla de enlace (tabla M1).
SOURCE_SPEC: list[dict] = [
    dict(source="GRD público (MINSAL)", period="2019–2024",
         unit={"es": "episodio (hospitalización o cirugía mayor ambulatoria)", "en": "episode (hospitalisation or major ambulatory surgery)"},
         kind={"es": "flujo", "en": "flow"},
         geo={"es": "hospital de atención; comuna de residencia declarada", "en": "hospital of care; declared comuna of residence"},
         ident={"es": "identificador encriptado, formato distinto en 2019–2020 y 2021–2024", "en": "encrypted identifier, different format in 2019–2020 and 2021–2024"},
         link={"es": "personas únicas solo dentro de cada año; nunca entre 2020 y 2021", "en": "unique persons only within each year; never across 2020 and 2021"}),
    dict(source="Egresos DEIS", period="2019–2024",
         unit={"es": "egreso hospitalario", "en": "hospital discharge"}, kind={"es": "flujo", "en": "flow"},
         geo={"es": "establecimiento; comuna de residencia", "en": "establishment; comuna of residence"},
         ident={"es": "ninguno publicado", "en": "none published"},
         link={"es": "sin enlace; solo F84 principal (no publica diagnósticos secundarios)", "en": "no linkage; principal F84 only (no secondary diagnoses published)"}),
    dict(source="REM Serie A (A03, A05, A27, A28)", period="2019–2025",
         unit={"es": "celda establecimiento × mes × código", "en": "establishment × month × code cell"},
         kind={"es": "flujo (actividad)", "en": "flow (activity)"},
         geo={"es": "establecimiento (lugar de atención)", "en": "establishment (place of care)"},
         ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado; A27 cuenta intervenciones, no personas", "en": "aggregated; A27 counts interventions, not people"}),
    dict(source="REM Serie P (P2, P6)", period="2019–2025",
         unit={"es": "celda establecimiento × semestre × código", "en": "establishment × half-year × code cell"},
         kind={"es": "stock (junio y diciembre)", "en": "stock (June and December)"},
         geo={"es": "establecimiento", "en": "establishment"}, ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado; los semestres nunca se suman", "en": "aggregated; half-years are never summed"}),
    dict(source="REM-20 (DEIS)", period="2019–2025",
         unit={"es": "establecimiento × área × mes", "en": "establishment × area × month"},
         kind={"es": "actividad/capacidad", "en": "activity/capacity"},
         geo={"es": "establecimiento", "en": "establishment"}, ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado; nunca es población cubierta", "en": "aggregated; never a covered population"}),
    dict(source={"es": "FONASA (agregados de diciembre)", "en": "FONASA (December aggregates)"}, period="2018–2025",
         unit={"es": "celda agregada de beneficiarios", "en": "aggregated beneficiary cell"}, kind={"es": "stock", "en": "stock"},
         geo={"es": "mezcla inscripción APS y domicilio", "en": "mixes APS enrolment and address"},
         ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado; las filas repetidas de 2018–2020 son aditivas y no se deduplican", "en": "aggregated; repeated 2018–2020 rows are additive and are not deduplicated"}),
    dict(source="Inscritos APS (FONASA)", period="2019–2025",
         unit={"es": "centro de atención primaria × grupo etario", "en": "primary-care centre × age group"}, kind={"es": "stock", "en": "stock"},
         geo={"es": "centro APS", "en": "APS centre"}, ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado; cobertura operativa por centro, no población residente", "en": "aggregated; operational coverage by centre, not resident population"}),
    dict(source="ISAPRE (Superintendencia de Salud)", period="2019–2025",
         unit={"es": "beneficiarios por comuna administrativa", "en": "beneficiaries by administrative comuna"}, kind={"es": "stock", "en": "stock"},
         geo={"es": "geografía administrativa del beneficiario", "en": "administrative geography of the beneficiary"},
         ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado; cambio de .xls a .xlsx y de edad simple a quinquenal en 2021", "en": "aggregated; change from .xls to .xlsx and from single-year to five-year age in 2021"}),
    dict(source="INE (proyecciones base Censo 2017; Censo 2024)", period="2019–2025",
         unit={"es": "población por comuna, edad y sexo", "en": "population by comuna, age and sex"}, kind={"es": "stock", "en": "stock"},
         geo={"es": "residencia", "en": "residence"}, ident={"es": "no aplica", "en": "not applicable"},
         link={"es": "denominador poblacional; bases censales nunca combinadas sin marca", "en": "population denominator; census bases never combined without a flag"}),
    dict(source="ENDIDE 2022", period="2022",
         unit={"es": "persona encuestada (diseño complejo)", "en": "surveyed person (complex design)"},
         kind={"es": "transversal", "en": "cross-sectional"},
         geo={"es": "nacional y regional", "en": "national and regional"}, ident={"es": "ninguno", "en": "none"},
         link={"es": "muestra independiente; sin desagregación comunal", "en": "independent sample; no comuna-level breakdown"}),
    dict(source="ENCAVI 2023–2024", period="2023–2024",
         unit={"es": "persona de 15 años o más (diseño complejo)", "en": "person aged 15 or over (complex design)"},
         kind={"es": "transversal", "en": "cross-sectional"},
         geo={"es": "nacional", "en": "national"}, ident={"es": "ninguno", "en": "none"},
         link={"es": "muestra independiente; sin desagregación comunal", "en": "independent sample; no comuna-level breakdown"}),
    dict(source="PIE / SINACES (MINEDUC)", period="2019–2025",
         unit={"es": "registro escolar agregado", "en": "aggregated school register"}, kind={"es": "stock escolar", "en": "school stock"},
         geo={"es": "nacional", "en": "national"}, ident={"es": "ninguno", "en": "none"},
         link={"es": "agregado publicado; categorías distintas por informe y año", "en": "published aggregate; categories differ by report and year"}),
    dict(source="JUNAEB EVE", period="2019–2025",
         unit={"es": "estudiante de cohortes escolares seleccionadas", "en": "student in selected school cohorts"},
         kind={"es": "stock escolar", "en": "school stock"},
         geo={"es": "establecimiento educacional", "en": "school"},
         ident={"es": "ninguno utilizable", "en": "none usable"},
         link={"es": "reporte de cuidadores con ponderador EXP; no es prevalencia nacional", "en": "caregiver report with the EXP weight; not a national prevalence"}),
]

# Capas de denominador y reglas de compatibilidad (tabla M4).
DENOMINATOR_SPEC: list[dict] = [
    dict(layer={"es": "Episodios GRD del mismo año y panel", "en": "GRD episodes of the same year and panel"},
         unit={"es": "episodio", "en": "episode"},
         question={"es": "¿Qué proporción de la actividad hospitalaria registrada documenta un F84?",
                   "en": "What share of recorded hospital activity documents an F84?"},
         compatible={"es": "episodios con F84 en cualquier posición, F84 principal, hospitalización estricta y CMA",
                     "en": "episodes with F84 in any position, principal F84, strict hospitalisation and MAS"},
         forbidden={"es": "no es población: no da prevalencia ni riesgo individual",
                    "en": "not a population: it yields neither prevalence nor individual risk"},
         file="outputs/tidy/grd_year_summary.csv"),
    dict(layer={"es": "Población INE (base Censo 2017)", "en": "INE population (2017-census base)"},
         unit={"es": "habitante por comuna, edad y sexo", "en": "resident by comuna, age and sex"},
         question={"es": "¿Cuántos eventos registrados hay por 100.000 habitantes residentes?",
                   "en": "How many recorded events are there per 100,000 resident population?"},
         compatible={"es": "numeradores con residencia declarada; numeradores por lugar de atención solo con nota explícita",
                     "en": "numerators with declared residence; place-of-care numerators only with an explicit note"},
         forbidden={"es": "no se combina con el Censo 2024 sin marca; no se usa para tasas por establecimiento",
                    "en": "never combined with the 2024 census without a flag; not used for establishment rates"},
         file="outputs/tidy/ine_population_comuna_year_age_sex.csv"),
    dict(layer={"es": "Beneficiarios FONASA", "en": "FONASA beneficiaries"},
         unit={"es": "beneficiario en diciembre", "en": "beneficiary in December"},
         question={"es": "¿Qué parte de la población está cubierta por el seguro público?",
                   "en": "What share of the population is covered by public insurance?"},
         compatible={"es": "capa de aseguramiento; contexto de cobertura de las series REM y GRD",
                     "en": "insurance layer; coverage context for the REM and GRD series"},
         forbidden={"es": "no es denominador de residencia; mezcla inscripción APS y domicilio",
                    "en": "not a residence denominator; mixes APS enrolment and address"},
         file="outputs/tidy/fonasa_beneficiaries_national_year.csv"),
    dict(layer={"es": "Beneficiarios ISAPRE", "en": "ISAPRE beneficiaries"},
         unit={"es": "beneficiario en diciembre", "en": "beneficiary in December"},
         question={"es": "¿Qué parte de la población está fuera del sistema público?",
                   "en": "What share of the population is outside the public system?"},
         compatible={"es": "complemento del aseguramiento; contexto para interpretar la cobertura pública",
                     "en": "insurance complement; context for interpreting public coverage"},
         forbidden={"es": "no tiene numerador de autismo comparable; no se usa como denominador de las series REM",
                    "en": "has no comparable autism numerator; never used as a denominator for the REM series"},
         file="outputs/tidy/isapre_beneficiaries_national_year.csv"),
    dict(layer={"es": "Inscritos en APS", "en": "APS enrolment"},
         unit={"es": "persona inscrita en un centro de atención primaria", "en": "person enrolled in a primary-care centre"},
         question={"es": "¿Cuál es la cobertura operativa del centro que informa el REM?",
                   "en": "What is the operational coverage of the centre that reports the REM?"},
         compatible={"es": "denominador de las series de atención primaria (A03, A05, P6, P2) por centro",
                     "en": "denominator of the primary-care series (A03, A05, P6, P2) by centre"},
         forbidden={"es": "no es población residente; cambia grupos de edad y nombres de variables en 2024",
                    "en": "not a resident population; age groups and variable names change in 2024"},
         file="outputs/tidy/aps_enrolment_centre_year.csv"),
    dict(layer={"es": "REM-20 (actividad y capacidad)", "en": "REM-20 (activity and capacity)"},
         unit={"es": "establecimiento × área × mes", "en": "establishment × area × month"},
         question={"es": "¿Cuánta actividad y capacidad hospitalaria hay detrás de los recuentos?",
                   "en": "How much hospital activity and capacity lies behind the counts?"},
         compatible={"es": "intensidad de actividad; panel de 188 establecimientos con 12 meses en todos los años",
                     "en": "activity intensity; panel of 188 establishments with 12 months in every year"},
         forbidden={"es": "nunca es población cubierta ni denominador de tasas poblacionales",
                    "en": "never a covered population nor a denominator for population rates"},
         file="outputs/tidy/rem20_panel.csv"),
    dict(layer={"es": "Establecimientos reportantes REM", "en": "Reporting REM establishments"},
         unit={"es": "establecimiento con al menos una fila del código en el período",
               "en": "establishment with at least one row of the code in the period"},
         question={"es": "¿Cuánto del cambio se explica por la expansión del reporte?",
                   "en": "How much of the change is explained by reporting expansion?"},
         compatible={"es": "desplazamiento de los modelos REM y acompañamiento obligatorio de toda cifra REM",
                     "en": "offset of the REM models and mandatory companion of every REM figure"},
         forbidden={"es": "no es población; un establecimiento que informa cero cuenta como reportante",
                    "en": "not a population; an establishment reporting zero counts as reporting"},
         file="outputs/tidy/rem_establishment_year.csv"),
    dict(layer={"es": "Matrícula y NANEAS bajo control", "en": "Enrolment and NANEAS under control"},
         unit={"es": "estudiante del programa PIE; persona bajo control NANEAS", "en": "PIE programme student; person under NANEAS control"},
         question={"es": "¿Qué proporción del programa corresponde a autismo?",
                   "en": "What share of the programme corresponds to autism?"},
         compatible={"es": "proporción TEA/NANEAS solo desde diciembre de 2023 (P2501878); series PIE por definición",
                     "en": "ASD/NANEAS proportion only from December 2023 (P2501878); PIE series by definition"},
         forbidden={"es": "no se cruza con las series de salud como si fueran las mismas personas",
                    "en": "never crossed with the health series as though they were the same people"},
         file="outputs/tidy/education_summary_year.csv; rem_pathway_annual.csv"),
]


# ---------------------------------------------------------------------------
# Tablas de la metodología extendida
# ---------------------------------------------------------------------------
TABLE_KEYS = ["M1_sources_units", "M2_case_definitions", "M3_rem_code_sets", "M4_denominator_layers",
              "M5_estimator_map", "M6_sensitivity_grid", "M7_data_states", "M8_pipeline_map",
              "M9_software_seeds", "M10_reproduction_controls"]

_H = {  # encabezados de columna bilingües
    "source": {"es": "Fuente", "en": "Source"},
    "period": {"es": "Período", "en": "Period"},
    "unit": {"es": "Unidad de observación", "en": "Unit of observation"},
    "kind": {"es": "Stock o flujo", "en": "Stock or flow"},
    "geo": {"es": "Geografía", "en": "Geography"},
    "ident": {"es": "Identificador", "en": "Identifier"},
    "link": {"es": "Regla de enlace", "en": "Linkage rule"},
    "code": {"es": "Código", "en": "Code"},
    "icd": {"es": "Descripción CIE-10", "en": "ICD-10 description"},
    "in_variant": {"es": "En la variante analizada", "en": "In the analysed variant"},
    "in_other": {"es": "En la otra variante", "en": "In the other variant"},
    "strict": {"es": "Serie estricta (F84.0)", "en": "Strict series (F84.0)"},
    "module": {"es": "Módulo REM", "en": "REM module"},
    "era": dict(LBL.L["definition_era"]),  # rótulo compartido, no un literal de este módulo
    "indicator": {"es": "Indicador del diccionario", "en": "Dictionary indicator"},
    "years_dict": {"es": "Años en que el diccionario lo contiene", "en": "Years in which the dictionary contains it"},
    "use": {"es": "Uso en el estudio", "en": "Use in the study"},
    "layer": {"es": "Capa", "en": "Layer"},
    "question": {"es": "Pregunta que responde", "en": "Question it answers"},
    "compatible": {"es": "Numeradores compatibles", "en": "Compatible numerators"},
    "forbidden": {"es": "Usos no permitidos", "en": "Uses not permitted"},
    "file": {"es": "Archivo", "en": "File"},
    "estimator": {"es": "Estimador", "en": "Estimator"},
    "equation": {"es": "Ecuación", "en": "Equation"},
    "script": {"es": "Script", "en": "Script"},
    "output": {"es": "Archivo de salida", "en": "Output file"},
    "status": {"es": "Estado", "en": "Status"},
    "analysis": {"es": "Análisis", "en": "Analysis"},
    "primary": {"es": "Especificación principal", "en": "Primary specification"},
    "variation": {"es": "Variación preespecificada", "en": "Pre-specified variation"},
    "threat": {"es": "Amenaza que aborda", "en": "Threat addressed"},
    "state": {"es": "Estado del dato", "en": "Data state"},
    "tidy": {"es": "Representación en las tablas tidy", "en": "Representation in the tidy tables"},
    "published": {"es": "Representación publicada", "en": "Published representation"},
    "rule": {"es": "Regla", "en": "Rule"},
    "what": {"es": "Qué hace", "en": "What it does"},
    "outputs": {"es": "Salidas principales", "en": "Main outputs"},
    "component": {"es": "Componente", "en": "Component"},
    "version": {"es": "Versión", "en": "Version"},
    "role": {"es": "Uso en el pipeline", "en": "Role in the pipeline"},
    "controls_module": {"es": "Módulo", "en": "Module"},
    "checks": {"es": "Controles", "en": "Checks"},
    "ok": {"es": "Coinciden", "en": "Match"},
    "info": {"es": "Informativas", "en": "Informative"},
    "differs": {"es": "Difieren", "en": "Differ"},
}

_STATUS_WORD = {
    "applied": {"es": "calculado", "en": "computed"},
    "prespecified": {"es": "preespecificado", "en": "pre-specified"},
}
_YES = {"es": "sí", "en": "yes"}
_NO = {"es": "no", "en": "no"}


def _h(key: str, lang: str) -> str:
    return _H[key][lang]


def _note(lang: str, unit: dict, rows: int, source: str, extra: dict | None = None) -> str:
    """Nota estándar: unidad, denominador, cobertura, era de definición, N reportante y archivo fuente.

    `source` es una lista de rutas escrita una sola vez para los dos idiomas: la conjunción se traduce aquí,
    porque escribirla en la cadena imprimía «... .csv y ... .csv» dentro de los documentos en inglés."""
    if isinstance(source, dict):
        source = source[lang]
    else:
        source = re.sub(r"(?<=[.\w]) y (?=[\w*])", " and " if lang == "en" else " y ", str(source))
    base = {"es": (f"Unidad de la fila: {unit['es']}. Denominador: no aplica (tabla de documentación metodológica). "
                   f"Cobertura: todo el estudio, 2019–2025. Era de definición: se indica en la propia tabla cuando "
                   f"corresponde. N informado: {fmt_number(rows, 0, 'es')} filas. Archivo fuente: {source}."),
            "en": (f"Row unit: {unit['en']}. Denominator: not applicable (methodological documentation table). "
                   f"Coverage: the whole study, 2019–2025. Definition era: stated in the table itself where relevant. "
                   f"Reporting N: {fmt_number(rows, 0, 'en')} rows. Source file: {source}.")}[lang]
    if extra:
        base += " " + extra[lang]
    return base


def _t_sources(lang: str) -> dict:
    # El nombre de la fuente es un nombre propio y se transcribe; la GLOSA descriptiva que algunos llevan
    # entre paréntesis («agregados de diciembre») es texto del estudio y se declara en los dos idiomas.
    rows = [{_h("source", lang): _t(s["source"], lang), _h("period", lang): s["period"], _h("unit", lang): _t(s["unit"], lang),
             _h("kind", lang): _t(s["kind"], lang), _h("geo", lang): _t(s["geo"], lang),
             _h("ident", lang): _t(s["ident"], lang), _h("link", lang): _t(s["link"], lang)} for s in SOURCE_SPEC]
    numeric = pd.DataFrame([{"source": _t(s["source"], "en"), "period": s["period"], "unit_en": s["unit"]["en"],
                             "stock_or_flow_en": s["kind"]["en"], "geography_en": s["geo"]["en"],
                             "identifier_en": s["ident"]["en"], "linkage_rule_en": s["link"]["en"]} for s in SOURCE_SPEC])
    title = {"es": "Fuentes, unidad de observación, geografía e imposibilidad de enlace individual",
             "en": "Sources, unit of observation, geography and the impossibility of individual linkage"}[lang]
    note = _note(lang, {"es": "una familia de archivos fuente", "en": "one source file family"}, len(rows),
                 "study/config.py (PATHS) y outputs/tidy/data_provenance.csv",
                 {"es": "Ninguna de las fuentes comparte un identificador de persona con otra: todo indicador que combine "
                        "etapas es una ruta administrativa agregada, nunca una cascada individual.",
                  "en": "No source shares a person identifier with another: any indicator combining stages is an aggregated "
                        "administrative pathway, never an individual cascade."})
    return dict(df=pd.DataFrame(rows), numeric=numeric, title=title, note=note)


def _t_case_definitions(variant: str, lang: str) -> dict:
    spec = CFG.VARIANTS[variant]
    other = "sin_rett" if variant == "con_rett" else "con_rett"
    other_codes = set(CFG.VARIANTS[other]["grd_subcodes"])
    rows, numeric = [], []
    for code in CFG.F84_SUBCODES:
        in_v = code in spec["grd_subcodes"]
        in_o = code in other_codes
        strict = code == "F840"
        rows.append({_h("code", lang): code[:3] + ("" if len(code) == 3 else "." + code[3:]),
                     _h("icd", lang): _t(ICD_F84[code], lang),
                     _h("in_variant", lang): _t(_YES if in_v else _NO, lang),
                     _h("in_other", lang): _t(_YES if in_o else _NO, lang),
                     _h("strict", lang): _t(_YES if strict else _NO, lang)})
        numeric.append(dict(code=code, icd10_en=ICD_F84[code]["en"], in_variant=int(in_v),
                            in_other_variant=int(in_o), strict_f840=int(strict)))
    title = {"es": f"Definición de caso hospitalaria: subcódigos F84 por variante ({_t(spec['label'], lang)})",
             "en": f"Hospital case definition: F84 subcodes by variant ({_t(spec['label'], lang)})"}[lang]
    note = _note(lang, {"es": "un subcódigo CIE-10", "en": "one ICD-10 subcode"}, len(rows),
                 "study/config.py (F84_SUBCODES, RETT_GRD, VARIANTS); CIE-10 (OMS) [@who_icd10]",
                 {"es": "El código se normaliza (sin punto, sin espacios, en mayúsculas) antes de compararlo con las 35 "
                        "columnas de diagnóstico del GRD. La serie estricta F84.0 es idéntica en las dos variantes.",
                  "en": "Codes are normalised (no dot, no spaces, upper case) before being compared with the 35 GRD "
                        "diagnosis columns. The strict F84.0 series is identical in both variants."})
    return dict(df=pd.DataFrame(rows), numeric=pd.DataFrame(numeric), title=title, note=note)


def dictionary_check() -> pd.DataFrame:
    path = TIDY / "rem_code_dictionary_check.csv"
    if not path.is_file():
        return pd.DataFrame(columns=["code", "year", "found_in_dictionary", "indicator", "label", "era"])
    d = pd.read_csv(path, dtype=str, keep_default_na=False)
    return d


def _t_rem_codes(lang: str) -> dict:
    check = dictionary_check()
    by_code: dict[str, dict] = {}
    if len(check):
        for code, grp in check.groupby("code"):
            found = grp.loc[grp.found_in_dictionary.isin(["True", "true", "1"])]
            years = sorted({str(y) for y in found.year})
            label = ""
            indicator = ""
            if len(found):
                label = next((v for v in found.label if v), "")
                indicator = next((v for v in found.indicator if v), "")
            by_code[str(code)] = dict(years=years, label=label, indicator=indicator,
                                      era=next((v for v in grp.era if v), ""))
    rows, numeric = [], []
    for module, code, era, use in REM_CODE_SPEC:
        meta = by_code.get(code, dict(years=[], label="", indicator="", era=""))
        # La era del diccionario verificado manda; el valor de config.py solo cubre los códigos no verificados.
        era_shown = meta.get("era") or era
        # El indicador se glosa con el diccionario bilingüe de labels.REM_INDICATOR: en español manda la
        # redacción literal del diccionario oficial; en inglés, el nombre analítico declarado para ese mismo
        # indicador, de modo que el documento en inglés no imprima una celda en español.
        ind = LBL.rem_indicator((meta["label"] or meta["indicator"]) if lang == "es"
                                else (meta["indicator"] or meta["label"]), lang)
        years = ", ".join(meta["years"]) if meta["years"] else ("no verificado" if lang == "es" else "not verified")
        rows.append({_h("module", lang): module, _h("code", lang): code, _h("era", lang): era_shown,
                     _h("indicator", lang): ind or ("—"), _h("years_dict", lang): years,
                     _h("use", lang): _t(use, lang)})
        numeric.append(dict(module=module, code=code, era=era_shown, era_config=era,
                            dictionary_indicator=meta["indicator"], dictionary_label_es=meta["label"],
                            years_found=";".join(meta["years"]), n_years_found=len(meta["years"]), use_en=use["en"]))
    title = {"es": "Conjuntos de códigos REM por módulo y era de definición, verificados contra el diccionario anual",
             "en": "REM code sets by module and definition era, verified against the annual dictionary"}[lang]
    note = _note(lang, {"es": "un código de prestación REM", "en": "one REM service code"}, len(rows),
                 "study/config.py y outputs/tidy/rem_code_dictionary_check.csv",
                 {"es": "El texto del indicador es la redacción literal del diccionario oficial REM. Un código "
                        "ausente del diccionario de un año no es un cero: significa que la era de definición no lo incluye. "
                        "Las eras nunca se unen con una línea en las láminas.",
                  "en": "The indicator text is the declared English name of each REM dictionary entry; the verbatim Spanish "
                        "wording of the dictionary is reproduced in the REM code-dictionary table and in "
                        "outputs/tidy/rem_code_dictionary_check.csv. A code absent from a given year's dictionary is not a "
                        "zero: it means the definition era does not include it. Eras are never joined by a line in the plates."})
    return dict(df=pd.DataFrame(rows), numeric=pd.DataFrame(numeric), title=title, note=note)


def _t_denominators(lang: str) -> dict:
    rows = [{_h("layer", lang): _t(d["layer"], lang), _h("unit", lang): _t(d["unit"], lang),
             _h("question", lang): _t(d["question"], lang), _h("compatible", lang): _t(d["compatible"], lang),
             _h("forbidden", lang): _t(d["forbidden"], lang), _h("file", lang): d["file"]} for d in DENOMINATOR_SPEC]
    numeric = pd.DataFrame([{"layer_en": d["layer"]["en"], "unit_en": d["unit"]["en"],
                             "compatible_en": d["compatible"]["en"], "forbidden_en": d["forbidden"]["en"],
                             "file": d["file"]} for d in DENOMINATOR_SPEC])
    title = {"es": "Capas de denominador y reglas de compatibilidad", "en": "Denominator layers and compatibility rules"}[lang]
    note = _note(lang, {"es": "una capa de denominador", "en": "one denominator layer"}, len(rows),
                 {"es": "outputs/tidy/coverage_layers_year.csv y los archivos indicados en la última columna",
                  "en": "outputs/tidy/coverage_layers_year.csv and the files listed in the last column"},
                 {"es": "Numerador y denominador deben pertenecer a la misma capa; stocks y flujos nunca comparten eje y el "
                        "lugar de atención no se mezcla con la residencia sin una nota explícita.",
                  "en": "Numerator and denominator must belong to the same layer; stocks and flows never share an axis and place "
                        "of care is not mixed with residence without an explicit note."})
    return dict(df=pd.DataFrame(rows), numeric=numeric, title=title, note=note)


def output_exists(rel: str) -> bool:
    """¿Existen en el disco TODOS los archivos de salida declarados por un estimador?

    `rel` son rutas relativas a la raíz del repositorio separadas por «;». Una ruta sin directorio hereda el
    de la anterior («outputs/tidy/a.csv; b.csv» son dos archivos de outputs/tidy) y los marcadores
    `<variante>` / `<idioma>` se resuelven por comodín, porque esas salidas existen una vez por combinación.
    Una cadena sin ruta (por ejemplo «—») declara que el estimador no tiene archivo de salida en esta corrida.
    """
    root = HERE.parent
    parts = [part.strip() for part in rel.split(";") if part.strip()]
    if not parts:
        return False
    directory = ""
    for part in parts:
        if "/" not in part:
            if not directory:
                return False              # «—» u otra cadena que no es una ruta: no hay archivo de salida
            part = f"{directory}/{part}"
        directory = part.rsplit("/", 1)[0]
        if "<" in part:
            if not any(root.glob(re.sub(r"<[^>]+>", "*", part))):
                return False
        elif not (root / part).is_file():
            return False
    return True


def _estimator_numbers(estimator: dict) -> str:
    """Números de ecuación de un estimador, siempre en orden ascendente."""
    return ", ".join(str(n) for n in sorted(EQ.NUMBER[k] for k in estimator["eq"]))


def _estimator_status(estimator: dict) -> str:
    """Estado derivado del disco, nunca declarado a mano: «calculado» si existe el archivo de salida."""
    return "applied" if output_exists(estimator["output"]) else "prespecified"


def _t_estimator_map(lang: str) -> dict:
    rows, numeric = [], []
    for e in EQ.ESTIMATORS:
        numbers = _estimator_numbers(e)
        state = _estimator_status(e)
        script = _t(e["script"], lang) if isinstance(e["script"], dict) else e["script"]
        rows.append({_h("estimator", lang): _t(e["name"], lang), _h("equation", lang): numbers,
                     _h("script", lang): script, _h("output", lang): _paths(e["output"], lang),
                     _h("status", lang): _t(_STATUS_WORD[state], lang)})
        numeric.append(dict(estimator=e["key"], equation_keys=";".join(e["eq"]), equation_numbers=numbers,
                            implementation=e["impl"], script=script, output=e["output"],
                            status=state, output_file_exists=int(state == "applied")))
    title = {"es": "Mapa de estimadores: ecuación, script y archivo de salida",
             "en": "Estimator map: equation, script and output file"}[lang]
    note = _note(lang, {"es": "un estimador", "en": "one estimator"}, len(rows),
                 "study/equations.py (EQUATIONS, ESTIMATORS)",
                 {"es": "El estado no se declara a mano: se comprueba en el disco. «Calculado» significa que existen todos los "
                        "archivos de salida de la fila en esta corrida; «preespecificado» significa que la fórmula y la "
                        "implementación están fijadas pero la corrida no produce archivo de salida, y en esa situación queda un "
                        "solo estimador, la kappa ponderada, cuya concordancia territorial se informa con ρ de Spearman sobre "
                        "los rangos comunales y regionales. Las salidas del análisis territorial son las trece tablas "
                        "outputs/tidy/spatial_<indicador>.csv del módulo 15b. Los números de ecuación remiten a la numeración secuencial "
                        "de esta sección y son los que DEFINEN al estimador: una ecuación compartida por dos estimadores —el umbral de "
                        "Benjamini–Hochberg, ecuación 28— figura en las dos filas y se imprime una sola vez, bajo el primero que la usa, "
                        "que es lo que cita el encabezado de cada estimador.",
                  "en": "The status is not declared by hand: it is checked on disk. 'Computed' means every output file of the row "
                        "exists in this run; 'pre-specified' means the formula and the implementation are fixed but the run "
                        "produces no output file, and exactly one estimator is in that position, the weighted kappa, whose "
                        "territorial agreement is reported with Spearman's rho on the comuna and region ranks. The outputs of the "
                        "territorial analysis are the thirteen outputs/tidy/spatial_<indicator>.csv tables of module 15b. Equation numbers "
                        "refer to the sequential numbering of this section and are the ones that DEFINE the estimator: an equation shared "
                        "by two estimators —the Benjamini–Hochberg threshold, equation 28— appears in both rows and is printed once, under "
                        "the first estimator that uses it, which is what each estimator heading cites."})
    return dict(df=pd.DataFrame(rows), numeric=pd.DataFrame(numeric), title=title, note=note)


def _t_sensitivity(lang: str) -> dict:
    rows = [{_h("analysis", lang): _t(s["analysis"], lang), _h("primary", lang): _t(s["primary"], lang),
             _h("variation", lang): _t(s["variation"], lang), _h("threat", lang): _t(s["threat"], lang),
             _h("output", lang): _paths(s["output"], lang)} for s in SENSITIVITY_GRID]
    numeric = pd.DataFrame([{"analysis_en": s["analysis"]["en"], "primary_en": s["primary"]["en"],
                             "variation_en": s["variation"]["en"], "threat_en": s["threat"]["en"],
                             "output": s["output"]} for s in SENSITIVITY_GRID])
    title = {"es": "Rejilla de análisis de sensibilidad preespecificados",
             "en": "Grid of pre-specified sensitivity analyses"}[lang]
    note = _note(lang, {"es": "un análisis de sensibilidad", "en": "one sensitivity analysis"}, len(rows),
                 "study/analysis_plan.md y outputs/tidy/models_summary.csv",
                 {"es": "Todas las variaciones se preespecificaron en el plan de análisis antes de explorar asociaciones; los "
                        "cambios posteriores están en decision_log.md. Ninguna variación busca un efecto causal de la Ley 21.545.",
                  "en": "All variations were pre-specified in the analysis plan before associations were explored; later changes are "
                        "in decision_log.md. No variation seeks a causal effect of Law 21.545."})
    return dict(df=pd.DataFrame(rows), numeric=numeric, title=title, note=note)


def _t_states(lang: str) -> dict:
    rows = [{_h("state", lang): _t(s["state"], lang), _h("tidy", lang): _t(s["tidy"], lang),
             _h("published", lang): _t(s["published"], lang), _h("rule", lang): _t(s["rule"], lang)}
            for s in DATA_STATES]
    numeric = pd.DataFrame([{"state_en": s["state"]["en"], "tidy_en": s["tidy"]["en"],
                             "published_en": s["published"]["en"], "rule_en": s["rule"]["en"]} for s in DATA_STATES])
    title = {"es": "Estados del dato: cero, ausente, no reportado, no estimable y suprimido",
             "en": "Data states: zero, missing, not reported, not estimable and suppressed"}[lang]
    note = _note(lang, {"es": "un estado del dato", "en": "one data state"}, len(rows),
                 "outputs/tidy/rem_pathway_tidy.csv, grd_territory.csv y survey_estimates.csv",
                 {"es": "Los cinco estados se mantienen separados en toda la cadena: ninguna tabla convierte un vacío en cero ni "
                        "un «no estimable» en un cero.",
                  "en": "The five states are kept separate along the whole chain: no table turns an empty cell into a zero or a "
                        "'not estimable' into a zero."})
    return dict(df=pd.DataFrame(rows), numeric=numeric, title=title, note=note)


def _t_pipeline(lang: str) -> dict:
    pipeline_dir = HERE / "pipeline"
    files = sorted(p.name for p in pipeline_dir.glob("*.py")) if pipeline_dir.is_dir() else []
    files = [f for f in files if f != "run_all.py"]
    rows, numeric = [], []
    for name in files:
        meta = PIPELINE_MAP.get(name)
        what = _t(meta["what"], lang) if meta else {"es": "Módulo del pipeline no descrito en este mapa; su documentación está en el encabezado del archivo.",
                                                    "en": "Pipeline module not described in this map; its documentation is in the file header."}[lang]
        outputs = meta["outputs"] if meta else "—"
        rows.append({_h("script", lang): f"pipeline/{name}", _h("what", lang): what,
                     _h("outputs", lang): _paths(outputs, lang)})
        numeric.append(dict(script=f"study/pipeline/{name}", documented=int(meta is not None), outputs=outputs))
    for name, meta in [("equations.py", {"what": {"es": "Define en LaTeX todas las fórmulas del estudio y compone los PNG numerados.",
                                                         "en": "Defines every formula of the study in LaTeX and renders the numbered PNGs."},
                                                "outputs": "outputs/equations/eq_NN_<clave>[_a|_b|_c].png; outputs/equations/<idioma>/ (variantes de idioma)"}),
                       ("prose_methods_extended.py", {"what": {"es": "Metodología extendida bilingüe en bloques de docx_builder (este documento).",
                                                               "en": "Bilingual extended methodology as docx_builder blocks (this document)."},
                                                      "outputs": "outputs/<variante>/<idioma>/extra/tables/M*.csv"}),
                       ("prose_en.py / prose_es.py", {"what": {"es": "Texto del artículo y del apéndice; toda cifra proviene de values_<variante>.json.",
                                                               "en": "Article and appendix text; every figure comes from values_<variant>.json."},
                                                      "outputs": "manuscript/*.docx (10_manuscript.py)"}),
                       ("docx_builder.py", {"what": {"es": "Constructor Word bilingüe (Times New Roman 12, A4, tablas, láminas, ecuaciones y referencias).",
                                                     "en": "Bilingual Word builder (Times New Roman 12, A4, tables, plates, equations and references)."},
                                            "outputs": "manuscript/*.docx"}),
                       ("values.py", {"what": {"es": "Extrae de las tablas tidy todas las cifras citables y las escribe en values_<variante>.json.",
                                               "en": "Extracts every citable figure from the tidy tables into values_<variant>.json."},
                                      "outputs": "outputs/values_<variante>.json"})]:
        rows.append({_h("script", lang): name, _h("what", lang): _t(meta["what"], lang),
                     _h("outputs", lang): _paths(meta["outputs"], lang)})
        numeric.append(dict(script=name, documented=1, outputs=meta["outputs"]))
    title = {"es": "Mapa archivo por archivo del pipeline y sus salidas", "en": "File-by-file map of the pipeline and its outputs"}[lang]
    note = _note(lang, {"es": "un script del pipeline", "en": "one pipeline script"}, len(rows),
                 {"es": "study/pipeline/ (listado en tiempo de construcción)",
                  "en": "study/pipeline/ (listed at build time)"},
                 {"es": "Cada script se ejecuta desde la raíz del repositorio con python3 y escribe sus salidas de forma atómica; "
                        "ninguno modifica los datos fuente ni los archivos de otro módulo.",
                  "en": "Each script runs from the repository root with python3 and writes its outputs atomically; none modifies the "
                        "source data or another module's files."})
    return dict(df=pd.DataFrame(rows), numeric=pd.DataFrame(numeric), title=title, note=note)


_SPATIAL_MODULE = HERE / "pipeline" / "15b_spatial_correlation.py"
_SPATIAL_DEFAULTS = {"SEED": "—", "PERMUTATIONS": "999", "FDR_Q": "0.05", "ALPHA": "0.05"}


def _dec(value: str, lang: str) -> str:
    """Separador decimal del idioma del documento (coma en español, punto en inglés)."""
    return value.replace(".", ",") if lang == "es" else value


def _spatial_constant(name: str) -> str:
    """Constante del módulo espacial leída de su código fuente; nunca se copia a mano en este archivo."""
    try:
        text = _SPATIAL_MODULE.read_text(encoding="utf-8")
    except OSError:
        return _SPATIAL_DEFAULTS.get(name, "—")
    found = re.search(rf"^{name}\s*=\s*([0-9.]+)", text, flags=re.MULTILINE)
    return found.group(1) if found else _SPATIAL_DEFAULTS.get(name, "—")


def _versions() -> list[tuple[str, str, dict]]:
    import platform
    from importlib import metadata
    rows = [("Python", platform.python_version(), {"es": "lenguaje del pipeline", "en": "pipeline language"}),
            (platform.system(), platform.release(), {"es": "sistema operativo de la corrida", "en": "operating system of the run"})]
    packages = [("numpy", {"es": "álgebra y vectorización", "en": "algebra and vectorisation"}),
                ("pandas", {"es": "tablas tidy y lectura por trozos", "en": "tidy tables and chunked reading"}),
                ("scipy", {"es": "distribuciones exactas (ji cuadrado, gamma, beta, t) y Spearman",
                           "en": "exact distributions (chi-square, gamma, beta, t) and Spearman"}),
                ("statsmodels", {"es": "GLM cuasi-Poisson, efectos fijos e intercepto aleatorio",
                                 "en": "quasi-Poisson GLM, fixed effects and random intercept"}),
                ("matplotlib", {"es": "láminas y composición de las ecuaciones (mathtext STIX)",
                                "en": "plates and equation rendering (STIX mathtext)"}),
                ("seaborn", {"es": "estilo de las láminas", "en": "plate style"}),
                ("geopandas", {"es": "geometrías comunales del análisis territorial", "en": "comuna geometries of the territorial analysis"}),
                ("libpysal", {"es": "matriz de contigüidad reina estandarizada por filas", "en": "row-standardised queen contiguity matrix"}),
                ("esda", {"es": "I de Moran, LISA, Gi* y umbral FDR", "en": "Moran's I, LISA, Gi* and the FDR threshold"}),
                ("python-docx", {"es": "construcción del documento Word", "en": "Word document construction"}),
                ("pillow", {"es": "dimensiones de las imágenes insertadas", "en": "dimensions of the inserted images"})]
    for name, role in packages:
        try:
            rows.append((name, metadata.version(name), role))
        except Exception:
            rows.append((name, "—", role))
    return rows


def _t_software(lang: str) -> dict:
    rows, numeric = [], []
    for name, version, role in _versions():
        rows.append({_h("component", lang): name, _h("version", lang): version, _h("role", lang): _t(role, lang)})
        numeric.append(dict(component=name, version=version, role_en=role["en"]))
    spatial = "study/pipeline/15b_spatial_correlation.py"
    seed_rows = [(f"SEED = {_spatial_constant('SEED')}",
                  {"es": f"semilla de las permutaciones de I de Moran, LISA, Gi* y Moran bivariada ({spatial})",
                   "en": f"seed of the permutations of Moran's I, LISA, Gi* and bivariate Moran ({spatial})"}),
                 (_spatial_constant("PERMUTATIONS"),
                  {"es": "número de permutaciones de toda inferencia espacial", "en": "number of permutations in every spatial inference"}),
                 ("UTF-8", {"es": "codificación de lectura y escritura (errors='replace' en las fuentes con codificación mixta)",
                            "en": "read/write encoding (errors='replace' in sources with mixed encoding)"}),
                 (f"α = {_dec(_spatial_constant('ALPHA'), lang)} / q = {_dec(_spatial_constant('FDR_Q'), lang)}",
                  {"es": "nivel de los intervalos de confianza y de la tasa de falso descubrimiento",
                   "en": "level of the confidence intervals and of the false discovery rate"})]
    for name, role in seed_rows:
        rows.append({_h("component", lang): name, _h("version", lang): "—", _h("role", lang): _t(role, lang)})
        numeric.append(dict(component=name, version="", role_en=role["en"]))
    title = {"es": "Software, versiones, semillas y constantes de la corrida",
             "en": "Software, versions, seeds and constants of the run"}[lang]
    note = _note(lang, {"es": "un componente de software o constante", "en": "one software component or constant"}, len(rows),
                 {"es": "importlib.metadata en tiempo de construcción; study/pipeline/15b_spatial_correlation.py "
                        "(SEED, PERMUTATIONS, FDR_Q, ALPHA)",
                  "en": "importlib.metadata at build time; study/pipeline/15b_spatial_correlation.py "
                        "(SEED, PERMUTATIONS, FDR_Q, ALPHA)"},
                 {"es": "Las versiones son las de la corrida que generó este documento. Todo el análisis es determinista salvo las "
                        "permutaciones espaciales, que se fijan con la semilla indicada.",
                  "en": "Versions are those of the run that produced this document. The whole analysis is deterministic except the "
                        "spatial permutations, which are fixed with the stated seed."})
    return dict(df=pd.DataFrame(rows), numeric=pd.DataFrame(numeric), title=title, note=note)


def _controls_counts() -> pd.DataFrame:
    rows = []
    if CONTROLS_DIR.is_dir():
        for path in sorted(CONTROLS_DIR.glob("*_controls.csv")):
            if path.name == "controls_summary.csv":
                continue
            try:
                d = pd.read_csv(path, dtype=str, keep_default_na=False)
            except Exception:
                continue
            status = d["status"].str.lower() if "status" in d.columns else pd.Series(dtype=str)
            # `removesuffix`, no `replace`: el nombre del módulo es el tallo SIN el sufijo «_controls» del
            # archivo, y `str.replace` quita TODAS las apariciones — el tallo «07_controls_controls» se
            # quedaba en «07», el único módulo del pipeline cuyo nombre contiene «_controls», y ese rótulo
            # roto no casaba con «07_controls» de la tabla E79 ni con la ruta del mapa del pipeline.
            rows.append(dict(module=path.stem.removesuffix("_controls"), checks=len(d),
                             ok=int((status == "ok").sum()), info=int((status == "info").sum()),
                             differs=int((status == "differs").sum()), file=path.name))
    return pd.DataFrame(rows)


def _t_controls(lang: str) -> dict:
    counts = _controls_counts()
    rows, numeric = [], []
    for _, r in counts.iterrows():
        rows.append({_h("controls_module", lang): r["module"], _h("checks", lang): fmt_number(r["checks"], 0, lang),
                     _h("ok", lang): fmt_number(r["ok"], 0, lang), _h("info", lang): fmt_number(r["info"], 0, lang),
                     _h("differs", lang): fmt_number(r["differs"], 0, lang), _h("file", lang): r["file"]})
        numeric.append(dict(module=r["module"], checks=int(r["checks"]), ok=int(r["ok"]), info=int(r["info"]),
                            differs=int(r["differs"]), file=r["file"]))
    if not rows:
        rows.append({_h("controls_module", lang): "—", _h("checks", lang): "—", _h("ok", lang): "—",
                     _h("info", lang): "—", _h("differs", lang): "—", _h("file", lang): "outputs/controls/"})
    title = {"es": "Controles de reproducción por módulo, " + CR.phrase(CR.PIPELINE, "es") + " (esperado frente a observado)",
             "en": "Reproduction controls by module, " + CR.phrase(CR.PIPELINE, "en") + " (expected against observed)"}[lang]
    note = _note(lang, {"es": "un módulo del pipeline", "en": "one pipeline module"}, len(rows),
                 "outputs/controls/*_controls.csv y outputs/controls/controls_summary.csv",
                 {"es": "Cada control compara un valor esperado (control preliminar del encargo o tabla tidy ya verificada) con el "
                        "observado y guarda diferencia absoluta y relativa. Los archivos de la última columna están en "
                        "outputs/controls/. Las filas que difieren están explicadas una a una en decision_log.md; ninguna cifra se "
                        "completó por plausibilidad.",
                  "en": "Each control compares an expected value (a preliminary control of the brief or an already verified tidy table) "
                        "with the observed one and stores the absolute and relative difference. The files in the last column are in "
                        "outputs/controls/. The rows that differ are explained one by one in decision_log.md; no figure was ever filled "
                        "in by plausibility."})
    return dict(df=pd.DataFrame(rows), numeric=pd.DataFrame(numeric), title=title, note=note)


def table_specs(variant: str, lang: str, V: dict | None = None) -> dict:
    """Todas las tablas de la metodología extendida: {clave: dict(df, numeric, title, note)}."""
    return {
        "M1_sources_units": _t_sources(lang),
        "M2_case_definitions": _t_case_definitions(variant, lang),
        "M3_rem_code_sets": _t_rem_codes(lang),
        "M4_denominator_layers": _t_denominators(lang),
        "M5_estimator_map": _t_estimator_map(lang),
        "M6_sensitivity_grid": _t_sensitivity(lang),
        "M7_data_states": _t_states(lang),
        "M8_pipeline_map": _t_pipeline(lang),
        "M9_software_seeds": _t_software(lang),
        "M10_reproduction_controls": _t_controls(lang),
    }


# ---------------------------------------------------------------------------
# Texto: encabezados de sección
# ---------------------------------------------------------------------------
SECTIONS = {
    "root": {"es": "Metodología extendida", "en": "Extended methodology"},
    "M1": {"es": "M1. Diseño del estudio, fuentes, unidades e imposibilidad de enlace",
           "en": "M1. Study design, sources, units and the impossibility of linkage"},
    "M2": {"es": "M2. Definiciones de caso, variantes y conjuntos de códigos",
           "en": "M2. Case definitions, variants and code sets"},
    "M3": {"es": "M3. Denominadores, capas de cobertura y reglas de compatibilidad",
           "en": "M3. Denominators, coverage layers and compatibility rules"},
    "M4": {"es": "M4. Estimadores: fórmula, supuestos, implementación y script",
           "en": "M4. Estimators: formula, assumptions, implementation and script"},
    "M5": {"es": "M5. Controles de reproducción, estados del dato y rejilla de sensibilidad",
           "en": "M5. Reproduction controls, data states and sensitivity grid"},
    "M6": {"es": "M6. Software, versiones, semillas, mapa del pipeline y controles por módulo",
           "en": "M6. Software, versions, seeds, pipeline map and controls by module"},
    "M7": {"es": "M7. Limitaciones de los métodos", "en": "M7. Limitations of the methods"},
}

INTRO = [
    {"es": "Esta sección del material suplementario reescribe los Métodos del artículo con el detalle necesario para "
           "reimplementar el análisis completo a partir de las fuentes originales. No modifica ninguna estimación ni "
           "reemplaza los Métodos concisos del artículo: los amplía. Cada estimador aparece con su fórmula numerada, sus "
           "supuestos, la función que lo calcula, el script que la invoca y el archivo de salida donde queda registrado el "
           "resultado, de modo que cualquier cifra del artículo pueda rehacerse sin consultar a los autores. Las ecuaciones "
           "se numeran de forma secuencial en esta sección y se citan en el texto que las aplica.",
     "en": "This section of the supplementary material rewrites the Methods of the article with the detail needed to "
           "re-implement the whole analysis from the original sources. It changes no estimate and does not replace the "
           "concise Methods of the article: it expands them. Every estimator is presented with its numbered formula, its "
           "assumptions, the function that computes it, the script that calls it and the output file where the result is "
           "recorded, so that any figure in the article can be rebuilt without consulting the authors. Equations are "
           "numbered sequentially within this section and cited in the text that applies them."},
    {"es": "Tres advertencias gobiernan todo lo que sigue y se repiten en las notas de las tablas. Primero, los recuentos "
           "son reconocimiento administrativo —la existencia de un registro codificado en un sistema— y nunca prevalencia, "
           "incidencia ni «aumento real del autismo». Segundo, las fuentes no comparten identificador de persona: ningún "
           "cociente entre dos de ellas representa una probabilidad individual y ninguna secuencia de indicadores es una "
           "trayectoria de personas. Tercero, la Ley 21.545 (marzo de 2023) se usa como marcador de contexto de política y "
           "nunca como intervención con efecto causal identificable, porque coinciden con ella la recuperación pospandemia, "
           "la expansión del reporte, cambios de códigos REM, mayor profundidad diagnóstica y cambios escolares.",
     "en": "Three warnings govern everything that follows and are repeated in the table notes. First, counts are "
           "administrative recognition —the existence of a coded record in a system— and never prevalence, incidence or a "
           "'real increase in autism'. Second, the sources share no person identifier: no ratio between two of them "
           "represents an individual probability and no sequence of indicators is a trajectory of people. Third, Law 21.545 "
           "(March 2023) is used as a policy context marker and never as an intervention with an identifiable causal effect, "
           "because post-pandemic recovery, reporting expansion, REM code changes, deeper diagnostic coding and school "
           "changes coincide with it."},
]

P_M1 = [
    {"es": "**Diseño.** Estudio nacional, retrospectivo y descriptivo de vigilancia multifuente sobre datos administrativos "
           "de rutina de los sistemas público de salud y de educación de Chile, con período 2019–2025 (2019–2024 en las "
           "fuentes hospitalarias, que cierran un año antes). No hubo contacto con personas, intervención ni acceso a "
           "identificadores directos: todas las bases son agregados publicados o microdatos seudonimizados de acceso "
           "administrativo. El reporte sigue STROBE [@vonelm2007] y RECORD [@benchimol2015] como listas principales y SAGER "
           "[@heidari2016] para la presentación por sexo. El estimando es el reconocimiento administrativo del autismo, es "
           "decir la presencia de un registro codificado en un sistema durante un año, con su cobertura y sus reglas de "
           "codificación explícitas, y no la ocurrencia del autismo en la población.",
     "en": "**Design.** National, retrospective, descriptive multisource surveillance study of routinely collected "
           "administrative data from Chile's public health and education systems, covering 2019–2025 (2019–2024 in the "
           "hospital sources, which close one year earlier). There was no contact with individuals, no intervention and no "
           "access to direct identifiers: every database is either a published aggregate or pseudonymised microdata obtained "
           "administratively. Reporting follows STROBE [@vonelm2007] and RECORD [@benchimol2015] as the main checklists and "
           "SAGER [@heidari2016] for the presentation by sex. The estimand is the administrative recognition of autism, that "
           "is, the presence of a coded record in a system during a year, with its coverage and coding rules made explicit, "
           "and not the occurrence of autism in the population."},
    {"es": "**Fuentes y unidades.** Se utilizaron trece familias de archivos: el GRD público hospitalario [@fonasa_grd], los "
           "egresos DEIS [@deis_egresos], seis módulos del Registro Estadístico Mensual (REM) de atención primaria y "
           "especialidad [@minsal_rem], el REM-20 de actividad y capacidad [@deis_rem20], el catastro de establecimientos "
           "[@deis_establecimientos], los agregados de beneficiarios FONASA y de inscritos en atención primaria "
           "[@fonasa_beneficiarios; @fonasa_aps], los beneficiarios ISAPRE [@supersalud_isapre], las proyecciones de "
           "población del INE [@ine2019] con el Censo 2024 y la base 2024 como sensibilidad [@ine_censo2024; @ine_base2024], "
           "dos encuestas poblacionales con diseño complejo [@endide2022; @encavi2023] y los registros escolares del "
           "programa de integración y de JUNAEB [@mineduc_apuntes60; @mineduc_sinaces2026; @junaeb_eve]. La unidad de "
           "observación, el carácter de stock o flujo, la geografía y el identificador disponible de cada una se detallan en "
           "la tabla de fuentes de esta sección, y sus rutas, versiones y sumas SHA-256 en la tabla de procedencia del "
           "estudio (outputs/tidy/data_provenance.csv). Las dos cifras que el estudio publica sobre sus fuentes cuentan "
           "cosas distintas y no se contradicen: trece son las familias de archivos tal como se obtuvieron, agrupadas "
           "por el registro o producto del que provienen, y quince son las filas de esa tabla de fuentes, una por "
           "fuente de datos.",
     "en": "**Sources and units.** Thirteen file families were used: the public hospital GRD [@fonasa_grd], DEIS discharges "
           "[@deis_egresos], six modules of the monthly statistical register (REM) of primary and specialty care "
           "[@minsal_rem], the REM-20 activity and capacity register [@deis_rem20], the establishment catalogue "
           "[@deis_establecimientos], the aggregates of FONASA beneficiaries and primary-care enrolees [@fonasa_beneficiarios; "
           "@fonasa_aps], ISAPRE beneficiaries [@supersalud_isapre], INE population projections [@ine2019] with the 2024 "
           "census and the 2024 base as a sensitivity [@ine_censo2024; @ine_base2024], two population surveys with a complex "
           "design [@endide2022; @encavi2023] and the school registers of the integration programme and of JUNAEB "
           "[@mineduc_apuntes60; @mineduc_sinaces2026; @junaeb_eve]. The unit of observation, the stock or flow character, "
           "the geography and the identifier available for each are detailed in the source table of this section, and their "
           "paths, versions and SHA-256 sums in the study's provenance table (outputs/tidy/data_provenance.csv). The two "
           "figures the study publishes about its sources count different things and do not contradict each other: "
           "thirteen is the number of file families as obtained, grouped by the register or product they come from, "
           "and fifteen the number of rows of that source table, one per data source."},
    {"es": "**Imposibilidad de enlace individual.** Ninguna de las fuentes comparte un identificador de persona con otra y "
           "ninguna autorización permite enlazarlas. Dentro del GRD existe un identificador seudonimizado, pero cambia de "
           "formato entre 2020 y 2021 y no hay ningún identificador común a ambas eras, por lo que las personas únicas se "
           "informan solo dentro de cada año o dentro de una era validada. Las series REM son celdas agregadas de "
           "establecimiento por mes o semestre y no contienen personas; A27 cuenta intervenciones, no individuos. Las "
           "encuestas son muestras independientes y los registros escolares, agregados publicados. Por eso la secuencia "
           "detección (A03) → consejería y referencia (A27) → ingreso (A05) → población bajo control (P2/P6) → "
           "rehabilitación (A28) → episodio hospitalario (GRD) se describe como ruta administrativa agregada y nunca como "
           "cascada de atención: un cociente entre dos de esos escalones no estima ninguna probabilidad individual.",
     "en": "**Impossibility of individual linkage.** No source shares a person identifier with another and no authorisation "
           "permits linking them. The GRD does carry a pseudonymised identifier, but its format changes between 2020 and 2021 "
           "and no identifier is common to both eras, so unique persons are reported only within a year or within a validated "
           "era. The REM series are aggregated establishment-by-month or half-year cells and contain no persons; A27 counts "
           "interventions, not individuals. The surveys are independent samples and the school registers are published "
           "aggregates. The sequence detection (A03) → counselling and referral (A27) → programme entry (A05) → population "
           "under control (P2/P6) → rehabilitation (A28) → hospital episode (GRD) is therefore described as an aggregated "
           "administrative pathway and never as a care cascade: a ratio between two of those steps estimates no individual "
           "probability."},
    {"es": "**Stocks, flujos, lugar y residencia.** Las series se clasifican explícitamente antes de graficarse. Son flujos "
           "los episodios GRD, los egresos DEIS y las actividades REM A03, A05, A27 y A28; son stocks la población bajo "
           "control P2 y P6, los beneficiarios FONASA e ISAPRE y los inscritos en atención primaria. Un stock y un flujo "
           "nunca comparten eje ni se suman, y los stocks semestrales de junio y diciembre nunca se agregan entre sí: "
           "diciembre es la serie principal y junio la sensibilidad. La geografía tiene la misma disciplina: el GRD y el REM "
           "localizan el lugar de atención (hospital o establecimiento), mientras que el INE y la comuna de residencia "
           "declarada del GRD localizan la residencia; cuando una tasa combina un numerador por lugar de atención con un "
           "denominador por residencia, la lámina o la tabla lo advierte en su propia nota.",
     "en": "**Stocks, flows, place and residence.** Series are explicitly classified before being plotted. GRD episodes, DEIS "
           "discharges and the REM A03, A05, A27 and A28 activities are flows; the P2 and P6 populations under control, "
           "FONASA and ISAPRE beneficiaries and primary-care enrolees are stocks. A stock and a flow never share an axis and "
           "are never added, and the June and December half-yearly stocks are never aggregated with each other: December is "
           "the primary series and June the sensitivity. Geography follows the same discipline: GRD and REM locate the place "
           "of care (hospital or establishment), whereas INE and the declared comuna of residence in the GRD locate "
           "residence; when a rate combines a place-of-care numerator with a residence denominator, the plate or table says "
           "so in its own note."},
    {"es": "**Geografía y crosswalk.** Los territorios se resuelven por código y no por nombre. El INE identifica la comuna "
           "con cuatro dígitos y DEIS con cinco (cero inicial), de modo que se construyó un crosswalk auditable "
           "(outputs/tidy/comuna_crosswalk.csv) que normaliza mayúsculas, tildes y signos y resuelve de forma explícita "
           "Aisén/Aysén, Coihaique/Coyhaique, Con Con/Concón y Cabo de Hornos (Ex-Navarino)/Cabo de Hornos. Ningún nombre se "
           "enlaza por semejanza: los que no resuelven quedan en una tabla de no enlazados y se informan como tales. Las "
           "comunas no continentales (Isla de Pascua, Juan Fernández, Antártica y Cabo de Hornos) se excluyen de los "
           "estadísticos basados en contigüidad y se informan aparte.",
     "en": "**Geography and crosswalk.** Territories are resolved by code, never by name. INE identifies the comuna with four "
           "digits and DEIS with five (leading zero), so an auditable crosswalk was built "
           "(outputs/tidy/comuna_crosswalk.csv) that normalises case, accents and punctuation and explicitly resolves "
           "Aisén/Aysén, Coihaique/Coyhaique, Con Con/Concón and Cabo de Hornos (Ex-Navarino)/Cabo de Hornos. No name is "
           "matched by similarity: those that do not resolve are kept in an unmatched table and reported as such. "
           "Non-continental comunas (Easter Island, Juan Fernández, Antarctica and Cabo de Hornos) are excluded from "
           "contiguity-based statistics and reported separately."},
    {"es": "**Procedencia y escritura.** Antes de cualquier cálculo se congeló la procedencia de cada artefacto (ruta, "
           "tamaño, SHA-256, fecha, unidad, período, población cubierta, geografía, códigos y columnas usadas, condición de "
           "stock o flujo, denominador posible, quiebres de definición y restricciones de enlace). Los datos fuente nunca se "
           "sobrescriben: todas las salidas derivadas se escriben de forma atómica (archivo temporal en el mismo directorio "
           "y renombrado) y las fuentes grandes se leen por trozos, conservando como texto las columnas que distinguen vacío "
           "de cero. Ninguna base voluminosa se copia al repositorio y las rutas se resuelven con las variables de entorno "
           "ASESORIAS_DATA_ROOT y AUTISM_DATA_ROOT.",
     "en": "**Provenance and writing.** Before any computation, the provenance of every artefact was frozen (path, size, "
           "SHA-256, date, unit, period, covered population, geography, codes and columns used, stock or flow status, "
           "possible denominator, definition breaks and linkage restrictions). Source data are never overwritten: all derived "
           "outputs are written atomically (temporary file in the same directory, then renamed) and large sources are read in "
           "chunks, keeping as text the columns that distinguish empty from zero. No large database is copied into the "
           "repository and paths are resolved through the ASESORIAS_DATA_ROOT and AUTISM_DATA_ROOT environment variables."},
]

P_M2 = [
    {"es": "**Las dos variantes.** El análisis completo se ejecuta dos veces. La variante *con Rett* usa toda la familia F84 "
           "(incluido F84.2, síndrome de Rett) y la variante *sin Rett* la excluye, porque el DSM-5 dejó de considerar el "
           "síndrome de Rett dentro del espectro mientras la CIE-10, que es la clasificación de los registros chilenos "
           "[@who_icd10], lo mantiene en F84. Las dos variantes comparten sin cambios las series preespecificadas idénticas: "
           "el autismo estricto del REM (05990022 de ingreso, 05990027 de egreso, P6241010 en atención primaria y P6241060 "
           "en especialidad), F84 en posición principal en el GRD, y las series A03, A27, A28, P2, educativas y de "
           "encuestas, que no admiten desagregación por subcódigo. La tabla de definición de caso de esta sección enumera "
           "los nueve subcódigos con su pertenencia a cada variante.",
     "en": "**The two variants.** The complete analysis is run twice. The *with Rett* variant uses the whole F84 family "
           "(including F84.2, Rett syndrome) and the *without Rett* variant excludes it, because DSM-5 no longer places Rett "
           "syndrome within the spectrum whereas ICD-10, the classification used by the Chilean registers [@who_icd10], keeps "
           "it in F84. Both variants share unchanged the identical pre-specified series: the REM strict autism codes "
           "(05990022 for entry, 05990027 for exit, P6241010 in primary care and P6241060 in specialty care), F84 as "
           "principal diagnosis in the GRD, and the A03, A27, A28, P2, education and survey series, which admit no breakdown "
           "by subcode. The case-definition table of this section lists the nine subcodes and their membership of each "
           "variant."},
    {"es": "**Operacionalización en el GRD.** Cada archivo anual GRD_PUBLICO se lee con separador de barra vertical, todas "
           "las columnas como texto y por trozos de 200.000 filas. Un episodio entra en el numerador cuando alguna de las 35 "
           "columnas de diagnóstico contiene un código de la variante; antes de comparar, el código se normaliza quitando "
           "puntos y espacios y pasando a mayúsculas. Se distinguen tres posiciones: *cualquiera* (columnas 1 a 35), "
           "*principal* (columna 1, incluidos los episodios que además repiten el código como secundario) y *solo "
           "secundario* (columnas 2 a 35 sin aparecer en la 1). El resultado principal es «episodios con F84 documentado», "
           "nunca «hospitalizaciones por autismo»; F84 principal es una serie separada y se informa qué proporción de los "
           "episodios lleva el código únicamente como diagnóstico secundario.",
     "en": "**Operationalisation in the GRD.** Each annual GRD_PUBLICO file is read with a pipe separator, every column as "
           "text and in chunks of 200,000 rows. An episode enters the numerator when any of the 35 diagnosis columns contains "
           "a code of the variant; before comparison the code is normalised by removing dots and spaces and converting to "
           "upper case. Three positions are distinguished: *any* (columns 1 to 35), *principal* (column 1, including episodes "
           "that also repeat the code as a secondary diagnosis) and *secondary-only* (columns 2 to 35 without appearing in "
           "column 1). The primary outcome is 'episodes with documented F84', never 'hospitalisations for autism'; principal "
           "F84 is a separate series and the proportion of episodes carrying the code only as a secondary diagnosis is "
           "reported."},
    {"es": "**Paneles, modalidad y personas.** Los archivos GRD observados contienen 65 hospitales en 2019–2022, 68 en 2023 "
           "y 72 en 2024, de modo que nunca se usan 72 hospitales como panel fijo: toda serie se presenta en el panel anual "
           "observado y en el panel fijo de los 65 hospitales presentes en todos los años 2019–2024. Ese panel se "
           "construye como la intersección de los hospitales de 2019, 2020, 2021 y 2022 —los cuatro años anteriores a la "
           "ampliación— y dos controles verifican que los 65 son además un subconjunto de los 68 de 2023 y de los 72 de "
           "2024: ninguno sale del registro y los 7 restantes entran en 2023 o en 2024. Por eso la glosa de las tablas "
           "dice «presentes en todos los años 2019–2024» y no «presentes en 2019–2022», que es solo la regla de "
           "construcción. La lista queda registrada en "
           "outputs/tidy/grd_fixed_panel_hospitals.csv y no se recalcula en ningún módulo posterior. La modalidad de "
           "atención se separa en hospitalización estricta y cirugía mayor ambulatoria, con denominadores propios. Las "
           "personas únicas se cuentan solo dentro de cada año, porque el identificador cambia de formato entre 2020 y 2021 "
           "y no hay solapamiento; los episodios sin identificador válido se informan en una fila propia y no se imputan.",
     "en": "**Panels, activity and persons.** The observed GRD files contain 65 hospitals in 2019–2022, 68 in 2023 and 72 in "
           "2024, so 72 hospitals are never used as a fixed panel: every series is presented both in the observed annual "
           "panel and in the fixed panel of the 65 hospitals present in every year 2019–2024. That panel is built as the "
           "intersection of the hospitals of 2019, 2020, 2021 and 2022 —the four years before the expansion— and two "
           "controls verify that the 65 are also a subset of the 68 of 2023 and of the 72 of 2024: none leaves the "
           "register and the remaining 7 enter in 2023 or in 2024. This is why the table gloss reads 'present in every "
           "year 2019–2024' and not 'present in 2019–2022', which is only the construction rule. The list is recorded in "
           "outputs/tidy/grd_fixed_panel_hospitals.csv and is never recomputed by a later module. Activity is separated into "
           "strict hospitalisation and major ambulatory surgery, each with its own denominator. Unique persons are counted "
           "only within each year, because the identifier changes format between 2020 and 2021 with no overlap; episodes "
           "without a valid identifier are reported in their own row and never imputed."},
    {"es": "**Verificación de los códigos REM.** Los 57 códigos usados en las seis series REM se declararon en config.py y "
           "se verificaron uno a uno contra el diccionario oficial de cada año: se comprobó su presencia, la redacción "
           "literal del indicador, la sección del formulario, el significado de las columnas de desagregación y la "
           "coherencia del diseño de la fila. El resultado completo queda en outputs/tidy/rem_code_dictionary_check.csv y se "
           "resume en la tabla de conjuntos de códigos de esta sección, con los años en que el diccionario contiene cada "
           "código. La ausencia de un código en el diccionario de un año no es un cero: significa que ese año pertenece a "
           "otra era de definición, y por eso las eras se presentan en paneles o facetas separadas y nunca se unen con una "
           "línea.",
     "en": "**Verification of the REM codes.** The 57 codes used in the six REM series were declared in config.py and "
           "verified one by one against the official dictionary of each year: presence, the verbatim wording of the "
           "indicator, the form section, the meaning of the breakdown columns and the coherence of the row layout were all "
           "checked. The full result is in outputs/tidy/rem_code_dictionary_check.csv and is summarised in the code-set table "
           "of this section, with the years in which the dictionary contains each code. A code absent from a given year's "
           "dictionary is not a zero: it means that year belongs to a different definition era, which is why eras are shown "
           "in separate panels or facets and never joined by a line."},
    {"es": "**Eras de definición.** La detección A03 tiene cuatro eras: en 2019–2022 los códigos 03500406 y 03500407 "
           "registran el M-CHAT solo en los niños con alteración de lenguaje o del área social del control de 18 meses, de "
           "modo que no estiman cobertura ni positividad poblacional; en 2023–2024 aparece la familia 09600212–09600219 con "
           "categorías de riesgo y referencia; en 2024 se añaden los códigos 03700104–03700109 para 31–59 meses; y en 2025 "
           "se rediseña completamente con 03710013–03710021 para 16–30 y 30–59 meses. El ingreso A05 solo distingue autismo "
           "estricto desde 2021: en 2019–2020 existe únicamente el trastorno generalizado del desarrollo amplio (06902600 y "
           "05225000), que contiene Rett de forma inseparable y se presenta solo como sensibilidad marcada. A27 (consejería "
           "y referencia asistida) y A28 (rehabilitación primaria y hospitalaria) existen desde 2023. P2 y P6 son stocks "
           "semestrales, y el total NANEAS (P2501878), único denominador admisible de la proporción TEA/NANEAS, aparece "
           "desde diciembre de 2023.",
     "en": "**Definition eras.** A03 detection has four eras: in 2019–2022 codes 03500406 and 03500407 record the M-CHAT only "
           "among children with a language or social-area alteration at the 18-month check-up, so they estimate neither "
           "population coverage nor population positivity; in 2023–2024 the 09600212–09600219 family appears with risk and "
           "referral categories; in 2024 codes 03700104–03700109 are added for 31–59 months; and in 2025 the module is fully "
           "redesigned with 03710013–03710021 for 16–30 and 30–59 months. A05 entries distinguish strict autism only from "
           "2021: in 2019–2020 only the broad pervasive developmental disorder codes exist (06902600 and 05225000), which "
           "inseparably include Rett and are shown only as a flagged sensitivity. A27 (counselling and assisted referral) and "
           "A28 (primary and hospital rehabilitation) exist from 2023. P2 and P6 are half-yearly stocks, and the NANEAS total "
           "(P2501878), the only admissible denominator of the ASD/NANEAS proportion, appears from December 2023."},
    {"es": "**Definiciones educativas y de encuesta.** En educación se mantienen separadas tres definiciones: el TEA "
           "estricto del programa de integración escolar, la categoría TEA-Asperger y la suma armonizada de ambas, que es la "
           "que publican los informes oficiales de 2024 y 2025 [@mineduc_sinaces2026]; la discrepancia de cinco casos de "
           "2022 entre el informe y la resta de escuelas especiales queda registrada en decision_log.md y no se corrige en "
           "silencio. JUNAEB usa el enunciado del cuestionario de cada año y el ponderador EXP, representa cohortes "
           "escolares seleccionadas y reporte de cuidadores, y la variable de 1.º medio de 2024 está completamente vacía, "
           "por lo que se informa como «no estimable» y jamás como cero. En las encuestas se identifican la pregunta exacta "
           "de autismo y la de confirmación profesional, el universo y los códigos de no respuesta antes de estimar.",
     "en": "**Education and survey definitions.** In education three definitions are kept separate: strict ASD in the school "
           "integration programme, the ASD-Asperger category and the harmonised sum of both, which is what the official 2024 "
           "and 2025 reports publish [@mineduc_sinaces2026]; the five-case discrepancy of 2022 between the report and the "
           "subtraction of special schools is recorded in decision_log.md and is not silently corrected. JUNAEB uses each "
           "year's questionnaire wording and the EXP weight, represents selected school cohorts and caregiver report, and its "
           "2024 first-year secondary variable is entirely empty, so it is reported as 'not estimable' and never as zero. In "
           "the surveys, the exact autism question, the professional-confirmation question, the universe and the "
           "non-response codes are identified before any estimation."},
]

P_M3 = [
    {"es": "**Cuatro capas, cuatro preguntas.** Cada denominador responde una pregunta distinta y ninguno se elige por "
           "conveniencia. Los episodios GRD del mismo año y panel responden qué parte de la actividad hospitalaria "
           "registrada documenta un F84; la población del INE responde cuántos eventos registrados hay por habitante "
           "residente; los beneficiarios de FONASA e ISAPRE describen el aseguramiento; los inscritos en atención primaria "
           "describen la cobertura operativa del centro que informa el REM; y el REM-20 describe actividad y capacidad "
           "hospitalaria. El REM-20 nunca se usa como población cubierta. La tabla de capas de esta sección enumera para "
           "cada una la unidad, los numeradores compatibles, los usos no permitidos y el archivo donde queda registrada.",
     "en": "**Four layers, four questions.** Each denominator answers a different question and none is chosen for "
           "convenience. GRD episodes of the same year and panel answer what share of recorded hospital activity documents an "
           "F84; the INE population answers how many recorded events there are per resident; FONASA and ISAPRE beneficiaries "
           "describe insurance coverage; primary-care enrolees describe the operational coverage of the centre that reports "
           "the REM; and REM-20 describes hospital activity and capacity. REM-20 is never used as a covered population. The "
           "layer table of this section lists, for each, the unit, the compatible numerators, the uses that are not permitted "
           "and the file where it is recorded."},
    {"es": "**Reglas de compatibilidad.** Numerador y denominador deben pertenecer a la misma capa y al mismo año, panel y "
           "modalidad. Las tasas hospitalarias se expresan por 100.000 episodios GRD del mismo panel; la lectura poblacional "
           "por 100.000 habitantes se presenta como complementaria y advierte que el numerador es por lugar de atención y el "
           "denominador por residencia. Las series REM se acompañan siempre del número de establecimientos reportantes y, "
           "cuando el modelo lo requiere, usan ese número como desplazamiento en lugar de la población. La proporción "
           "TEA/NANEAS solo se calcula desde diciembre de 2023, cuando existe el total NANEAS. No se calcula ningún cociente "
           "entre etapas de fuentes no enlazables.",
     "en": "**Compatibility rules.** Numerator and denominator must belong to the same layer and to the same year, panel and "
           "activity type. Hospital rates are expressed per 100,000 GRD episodes of the same panel; the population reading per "
           "100,000 inhabitants is presented as complementary and warns that the numerator is by place of care and the "
           "denominator by residence. The REM series are always accompanied by the number of reporting establishments and, "
           "when the model requires it, use that number as the offset instead of the population. The ASD/NANEAS proportion is "
           "computed only from December 2023, when the NANEAS total exists. No ratio is computed between stages of "
           "unlinkable sources."},
    {"es": "**Armonización de los cambios de esquema.** Los agregados de FONASA cambian de esquema en 2021, 2023, 2024 y "
           "2025; los inscritos en atención primaria cambian de grupos de edad y de nombres de variables en 2024; y los "
           "archivos de ISAPRE pasan de .xls a .xlsx y de edad simple a quinquenal en 2021. Cada cambio se armoniza de forma "
           "explícita conservando las columnas originales junto a las armonizadas, y el resultado queda en "
           "outputs/tidy/fonasa_schema_by_year.csv y en las tablas de cobertura. Las filas repetidas de los agregados FONASA "
           "de 2018–2020 son aditivas y no se eliminan con una deduplicación automática, porque hacerlo reduce los totales "
           "oficiales.",
     "en": "**Harmonising schema changes.** The FONASA aggregates change schema in 2021, 2023, 2024 and 2025; primary-care "
           "enrolment changes age groups and variable names in 2024; and the ISAPRE files move from .xls to .xlsx and from "
           "single-year to five-year ages in 2021. Every change is harmonised explicitly, keeping the original columns "
           "alongside the harmonised ones, and the result is stored in outputs/tidy/fonasa_schema_by_year.csv and in the "
           "coverage tables. The repeated rows of the 2018–2020 FONASA aggregates are additive and are not removed by an "
           "automatic deduplication, because doing so reduces the official totals."},
    {"es": "**Bases poblacionales y paneles de capacidad.** La serie principal usa las proyecciones comunales del INE con "
           "base en el Censo 2017 [@ine2019]; el Censo 2024 y la base 2024 se emplean como sensibilidad y puente "
           "[@ine_censo2024; @ine_base2024], y las bases nunca se combinan sin una marca explícita en la tabla o la lámina. "
           "Para la capacidad se reproduce el panel de 188 establecimientos REM-20 con doce meses informados en todos los "
           "años y se cuantifica cuánto volumen retiene, y para la atención primaria el panel estable de centros con "
           "inscritos en toda la serie; ambos paneles se usan como sensibilidad frente al conjunto observado, nunca como "
           "sustituto silencioso.",
     "en": "**Population bases and capacity panels.** The main series uses the INE comuna projections based on the 2017 census "
           "[@ine2019]; the 2024 census and the 2024 base are used as a sensitivity and bridge [@ine_censo2024; "
           "@ine_base2024], and the bases are never combined without an explicit flag in the table or plate. For capacity, the "
           "panel of 188 REM-20 establishments with twelve reported months in every year is reproduced and the volume it "
           "retains is quantified, and for primary care the stable panel of centres with enrolees throughout the series; both "
           "panels are used as a sensitivity against the observed set, never as a silent substitute."},
]


# ---------------------------------------------------------------------------
# Texto: un párrafo por estimador (mismo orden y claves que equations.ESTIMATORS)
# ---------------------------------------------------------------------------
P_M4_INTRO = [
    {"es": "Todos los estimadores usan α = 0,05 y se informan con intervalo de confianza y tamaño de efecto en vez de "
           "listas de pruebas de significación. En las fórmulas, d son los eventos registrados, n el denominador declarado, "
           "i un área, h un establecimiento u hospital, t el año, a uno de los 17 grupos etarios quinquenales de la "
           "población estándar mundial de la OMS y s el sexo registrado, que las fuentes chilenas codifican como H "
           "(hombres) y M (mujeres); ese es el conjunto que declara la ecuación 2. Cada apartado indica la fórmula con su número, los "
           "supuestos que exige, la función que la implementa, el script que la invoca y la salida donde queda el resultado; "
           "la tabla del mapa de estimadores resume esa correspondencia y marca el estado de cada uno comprobando en el "
           "disco si existe su archivo de salida, de modo que la palabra «calculado» nunca depende de una declaración "
           "escrita a mano.",
     "en": "Every estimator uses α = 0.05 and is reported with a confidence interval and an effect size rather than lists of "
           "significance tests. In the formulae, d are the recorded events, n the stated denominator, i an area, h an "
           "establishment or hospital, t the year, a one of the 17 five-year age groups of the WHO world standard population "
           "and s the recorded sex, written here as M (male) and F (female) —the Chilean sources code these two categories "
           "as H and M— which is the set equation 2 declares. Each subsection gives the formula with its number, the assumptions it requires, the "
           "function that implements it, the script that calls it and the output where the result is stored; the estimator-map "
           "table summarises that correspondence and marks the state of each one by checking on disk whether its output file "
           "exists, so that the word 'computed' never depends on a hand-written declaration."},
    {"es": "**El análisis territorial está calculado, no anunciado.** Los indicadores comunales de esta parte suplementaria "
           "se estandarizan indirectamente dentro de cada fuente: los esperados de cada comuna se obtienen aplicando a su "
           "población por edad, sexo y año las tasas específicas nacionales de la misma fuente (ecuación 8), la razón "
           "observado/esperado se acompaña de límites exactos de Poisson y de la aproximación de Byar (ecuación 9), y esa "
           "razón se suaviza con el estimador bayesiano empírico global de Marshall (ecuaciones 10 y 11), que devuelve "
           "además el peso de contracción de cada comuna y la media y la varianza de la distribución previa. Sobre esas "
           "razones suavizadas se calcula la autocorrelación espacial con una matriz de contigüidad reina estandarizada "
           "por filas —las comunas no continentales quedan fuera de la matriz pero se conservan en las tablas, y las "
           "comunas sin vecino reina se enlazan con su vecino más próximo y se informan—: I de Moran global (ecuación 25), "
           "I de Moran bivariada entre sistemas (ecuación 26), indicadores locales LISA con clasificación por cuadrante "
           "(ecuación 27) y estadístico Gi* de Getis–Ord (ecuación 29). Toda la inferencia es por 999 permutaciones "
           "condicionales con semilla fija, y la multiplicidad de las pruebas locales se controla con el umbral de "
           "Benjamini–Hochberg para una tasa de falso descubrimiento de 0,05 (ecuación 28). La desigualdad territorial se "
           "resume con la curva de Lorenz y el Gini (ecuaciones 30 y 31) y con el índice de Theil descompuesto dentro y "
           "entre regiones (ecuación 32). Se declaran como sensibilidades las matrices de k = 4 y k = 8 vecinos más "
           "próximos y la de distancia inversa, la escala regional, la exclusión de la Región Metropolitana, la exclusión "
           "de las comunas con menos de cinco eventos y el denominador del Censo 2024. Los resultados están en las trece "
           "tablas outputs/tidy/spatial_<indicador>.csv y en las láminas y tablas territoriales de esta parte suplementaria.",
     "en": "**The territorial analysis is computed, not announced.** The comuna-level indicators of this supplementary part "
           "are indirectly standardised within each source: each comuna's expected count is obtained by applying the "
           "national stratum-specific rates of the same source to its population by age, sex and year (equation 8), the "
           "observed-to-expected ratio carries exact Poisson limits and Byar's approximation (equation 9), and that ratio "
           "is smoothed with Marshall's global empirical-Bayes estimator (equations 10 and 11), which also returns each "
           "comuna's shrinkage weight and the mean and variance of the prior. Spatial autocorrelation is computed on those "
           "smoothed ratios with a row-standardised queen contiguity matrix —non-continental comunas stay out of the matrix "
           "but remain in the tables, and comunas with no queen neighbour are attached to their nearest neighbour and "
           "reported—: global Moran's I (equation 25), bivariate Moran's I between systems (equation 26), local LISA "
           "indicators with quadrant classification (equation 27) and the Getis–Ord Gi* statistic (equation 29). All "
           "inference is by 999 conditional permutations with a fixed seed, and the multiplicity of the local tests is "
           "controlled with the Benjamini–Hochberg threshold for a false discovery rate of 0.05 (equation 28). Territorial "
           "inequality is summarised with the Lorenz curve and the Gini coefficient (equations 30 and 31) and with the "
           "Theil index decomposed within and between regions (equation 32). The k = 4 and k = 8 nearest-neighbour and the "
           "inverse-distance matrices, the regional scale, the exclusion of the Metropolitan Region, the exclusion of "
           "comunas with fewer than five events and the 2024 Census denominator are declared sensitivities. The results are "
           "in the thirteen outputs/tidy/spatial_<indicator>.csv tables and in the territorial plates and tables of this "
           "supplementary part."},
]

EST_TEXT = {
    "crude_rate": {
        "es": "La tasa bruta divide los eventos registrados por el denominador declarado y se expresa por 100.000. Los "
              "límites son exactos de Poisson: se obtienen de los cuantiles de la ji cuadrado sobre el recuento, no de una "
              "aproximación normal, porque muchas celdas anuales, hospitalarias o comunales tienen pocos eventos y la "
              "aproximación normal produciría límites negativos o demasiado estrechos. El denominador se trata como fijo y "
              "conocido, lo que es razonable para episodios GRD o establecimientos reportantes y aceptable para la población "
              "proyectada. La misma fórmula se aplica con tres denominadores distintos —episodios GRD del mismo panel, "
              "población INE y establecimientos reportantes—, y en cada tabla se declara cuál se usó: una tasa por 100.000 "
              "episodios no es una tasa poblacional y no admite lectura de riesgo individual.",
        "en": "The crude rate divides recorded events by the stated denominator and is expressed per 100,000. Limits are "
              "exact Poisson limits obtained from chi-square quantiles of the count rather than from a normal approximation, "
              "because many annual, hospital or comuna cells contain few events and the normal approximation would give "
              "negative or too narrow limits. The denominator is treated as fixed and known, which is reasonable for GRD "
              "episodes or reporting establishments and acceptable for projected population. The same formula is applied with "
              "three different denominators —GRD episodes of the same panel, INE population and reporting establishments— and "
              "every table states which was used: a rate per 100,000 episodes is not a population rate and licenses no "
              "individual risk reading."},
    "age_specific": {
        "es": "Las tasas específicas se calculan dentro de cada combinación de grupo etario y sexo, con numerador y "
              "denominador clasificados por las mismas categorías. La edad del episodio se obtiene como la parte entera de "
              "la diferencia entre la fecha de ingreso y la de nacimiento dividida por 365,25; los valores negativos o "
              "mayores de 110 se marcan como desconocidos, se informan y quedan fuera del cálculo, y nunca se imputan. Los "
              "denominadores provienen de la grilla completa de población por comuna, edad y sexo, de modo que un grupo sin "
              "eventos aporta un cero verdadero y no una celda ausente. Estas tasas son el insumo de la estandarización "
              "directa y de la indirecta.",
        "en": "Specific rates are computed within each combination of age group and sex, with numerator and denominator "
              "classified by the same categories. The age of the episode is the integer part of the difference between the "
              "admission and birth dates divided by 365.25; negative values or values above 110 are flagged as unknown, "
              "reported and left out of the calculation, and never imputed. Denominators come from the complete population "
              "grid by comuna, age and sex, so that a group with no events contributes a true zero and not a missing cell. "
              "These rates are the input to both direct and indirect standardisation."},
    "direct_standardisation": {
        "es": "La estandarización directa pondera las tasas específicas por los pesos de la población estándar mundial de la "
              "OMS [@ahmad2001], colapsada en un grupo abierto de 80 años o más; los pesos publicados suman 100.030 por "
              "rounding y se renormalizan al aplicarse. Los grupos sin denominador se excluyen, se cuenta cuántos faltan y "
              "los pesos restantes se renormalizan, de modo que la tasa siempre se refiere a la estructura efectivamente "
              "cubierta. La varianza es la suma ponderada de las varianzas de Poisson por grupo y los intervalos son los "
              "límites gamma de Fay y Feuer [@fay1997], que sustituyen la aproximación normal y mantienen cobertura nominal "
              "con recuentos pequeños; el término w_M es el peso máximo por unidad de población y corrige el límite "
              "superior. La tasa estandarizada permite comparar años, sexos o territorios con estructuras etarias distintas, "
              "pero sigue siendo una tasa de registro administrativo.",
        "en": "Direct standardisation weights the specific rates by the WHO world standard population [@ahmad2001], collapsed "
              "into an open group of 80 years and over; the published weights sum to 100,030 because of rounding and are "
              "renormalised when applied. Groups without a denominator are dropped, the number missing is counted and the "
              "remaining weights are renormalised, so the rate always refers to the structure actually covered. The variance "
              "is the weighted sum of the group-specific Poisson variances and the intervals are the gamma limits of Fay and "
              "Feuer [@fay1997], which replace the normal approximation and keep nominal coverage with small counts; the w_M "
              "term is the maximum weight per unit of population and corrects the upper limit. The standardised rate allows "
              "years, sexes or territories with different age structures to be compared, but it remains a rate of "
              "administrative recording."},
    "rate_ratio": {
        "es": "La razón entre dos tasas estandarizadas —típicamente hombres frente a mujeres— se acompaña de límites "
              "log-normales construidos con las varianzas de ambas tasas. El supuesto es que las dos tasas son "
              "independientes, lo que se cumple entre sexos dentro de la misma fuente y el mismo año. La razón nunca se "
              "calcula entre numeradores de fuentes distintas ni entre etapas de la ruta administrativa, porque esas cifras "
              "no comparten denominador ni población y su cociente no tiene interpretación. En el texto se informa junto con "
              "las dos tasas que la componen, para que el lector vea el nivel además del contraste.",
        "en": "The ratio of two standardised rates —typically males against females— is accompanied by log-normal limits "
              "built from the variances of both rates. The assumption is that the two rates are independent, which holds "
              "between sexes within the same source and year. The ratio is never computed between numerators from different "
              "sources nor between stages of the administrative pathway, because those figures share neither denominator nor "
              "population and their quotient has no interpretation. It is reported together with the two rates that compose "
              "it, so that the reader sees the level as well as the contrast."},
    "count_ratio": {
        "es": "Cuando dos recuentos provienen de la misma base poblacional y del mismo período, su razón admite límites "
              "exactos: condicionando en la suma de ambos, la proporción sigue una binomial y sus cuantiles beta se "
              "transforman en límites de la razón. Es la forma correcta de comparar, por ejemplo, dos subcódigos dentro del "
              "mismo conjunto de episodios, y evita la aproximación normal cuando alguno de los recuentos es pequeño. El "
              "límite superior se declara infinito cuando el recuento del denominador es cero. La regla de uso es estricta: "
              "esta razón no se aplica entre fuentes que no comparten base, es decir, nunca entre GRD, REM, educación o "
              "encuestas.",
        "en": "When two counts come from the same population basis and the same period, their ratio admits exact limits: "
              "conditioning on their sum, the proportion follows a binomial and its beta quantiles are transformed into limits "
              "for the ratio. This is the correct way to compare, for instance, two subcodes within the same set of episodes, "
              "and it avoids the normal approximation when either count is small. The upper limit is declared infinite when "
              "the denominator count is zero. The rule of use is strict: this ratio is never applied between sources that do "
              "not share a basis, that is, never between GRD, REM, education or surveys."},
    "indirect_standardisation": {
        "es": "La estandarización indirecta compara lo observado en un área con lo que se esperaría si tuviera las tasas "
              "específicas nacionales aplicadas a su propia estructura por edad y sexo. Es preferible a la directa cuando los "
              "recuentos por área son pequeños, que es el caso de la mayoría de las comunas chilenas para un código como "
              "F84. Los límites se obtienen dividiendo por el esperado los límites exactos de Poisson del observado; cuando "
              "el observado es grande la aproximación de Byar [@breslow1987; @ulm1990] es equivalente y computacionalmente "
              "más estable. La razón resultante es ecológica: describe el registro del área y no el riesgo de sus "
              "habitantes, y en el GRD mezcla lugar de atención con residencia si el numerador no se restringe a la comuna "
              "declarada.",
        "en": "Indirect standardisation compares what is observed in an area with what would be expected if the national "
              "stratum-specific rates were applied to its own age and sex structure. It is preferable to direct "
              "standardisation when area counts are small, which is the case for most Chilean comunas for a code such as F84. "
              "Limits are obtained by dividing the exact Poisson limits of the observed count by the expected count; when the "
              "observed count is large, Byar's approximation [@breslow1987; @ulm1990] is equivalent and computationally more "
              "stable. The resulting ratio is ecological: it describes the area's recording and not the risk of its "
              "inhabitants, and in the GRD it mixes place of care with residence unless the numerator is restricted to the "
              "declared comuna."},
    "empirical_bayes": {
        "es": "Las razones indirectamente estandarizadas de áreas pequeñas son inestables: una comuna con dos eventos "
              "esperados puede duplicar o anular su razón por un solo caso. El suavizamiento bayesiano empírico global de "
              "Marshall [@marshall1991] contrae cada razón hacia la razón global con un peso que crece con el número de "
              "casos esperados, estimando la media y la varianza de la distribución previa por el método de los momentos; la "
              "varianza se trunca en cero cuando la estimación resulta negativa, en cuyo caso todas las áreas colapsan a la "
              "media global. El suavizamiento no tiene estructura espacial —todas las áreas son intercambiables— y por eso "
              "la lámina de la razón suavizada muestra la contracción además del mapa: el peso de contracción frente al "
              "número de casos esperados, la distribución de la razón cruda y de la suavizada superpuestas, y las comunas "
              "extremas con su razón cruda, su intervalo y su razón suavizada, junto con la media y la varianza de la "
              "distribución previa.",
        "en": "Indirectly standardised ratios for small areas are unstable: a comuna with two expected events can double or "
              "nullify its ratio with a single case. Marshall's global empirical-Bayes smoother [@marshall1991] shrinks each "
              "ratio towards the global ratio with a weight that grows with the number of expected cases, estimating the mean "
              "and variance of the prior by the method of moments; the variance is truncated at zero when the estimate is "
              "negative, in which case every area collapses to the global mean. The smoother has no spatial structure —all "
              "areas are exchangeable— which is why the plate of the smoothed ratio shows the shrinkage alongside the map: "
              "the shrinkage weight against the number of expected cases, the distributions of the crude and the smoothed "
              "ratio superimposed, and the extreme comunas with their crude ratio, its interval and their smoothed ratio, "
              "together with the mean and the variance of the prior."},
    "quasi_poisson": {
        "es": "Las tendencias se modelan con un modelo log-lineal cuasi-Poisson: el logaritmo del valor esperado del "
              "recuento es lineal en el año, con desplazamiento igual al logaritmo del denominador y coeficiente uno, y la "
              "varianza es proporcional a la media con un parámetro de dispersión estimado por la ji cuadrado de Pearson "
              "[@wedderburn1974; @mccullagh1989]. La cuasi-verosimilitud es necesaria porque los recuentos anuales están "
              "claramente sobredispersos respecto de Poisson. El cambio porcentual anual es la exponencial del coeficiente "
              "del año menos uno [@clegg2009], con intervalo de Wald sobre la escala logarítmica. Dos covariables opcionales "
              "capturan las amenazas de comparabilidad: la profundidad diagnóstica media del panel y un indicador de "
              "2020–2021 que describe la disrupción del reporte. Con tres a siete puntos anuales y varios cambios "
              "simultáneos, ningún modelo de este tipo identifica un efecto causal, y no se ajusta ninguna serie de tiempo "
              "interrumpida con pretensión causal.",
        "en": "Trends are modelled with a log-linear quasi-Poisson model: the logarithm of the expected count is linear in "
              "the year, with an offset equal to the logarithm of the denominator and a unit coefficient, and the variance is "
              "proportional to the mean with a dispersion parameter estimated by the Pearson chi-square [@wedderburn1974; "
              "@mccullagh1989]. Quasi-likelihood is needed because the annual counts are clearly overdispersed relative to "
              "Poisson. The annual percent change is the exponential of the year coefficient minus one [@clegg2009], with a "
              "Wald interval on the log scale. Two optional covariates capture the comparability threats: the panel's mean "
              "coding depth and an indicator for 2020–2021 that describes the reporting disruption. With three to seven annual "
              "points and several simultaneous changes, no model of this kind identifies a causal effect, and no interrupted "
              "time series is fitted with causal intent."},
    "hospital_fixed_effects": {
        "es": "Para describir la heterogeneidad entre hospitales se ajusta el mismo modelo log-lineal con un indicador por "
              "hospital, una tendencia común y el desplazamiento del logaritmo de los episodios del hospital-año. Los "
              "efectos se expresan como razones de tasa frente a la media geométrica de los hospitales, lo que evita "
              "depender de una categoría de referencia arbitraria. Los errores estándar se calculan con el estimador "
              "sándwich agrupado por hospital, porque las observaciones de un mismo hospital en años sucesivos están "
              "correlacionadas; con 65 a 72 conglomerados el sándwich es razonablemente estable. Los efectos por hospital se "
              "presentan como descripción del registro por lugar de atención y nunca como medida de calidad ni de "
              "prevalencia del área.",
        "en": "To describe heterogeneity between hospitals, the same log-linear model is fitted with a hospital indicator, a "
              "common trend and an offset of the logarithm of the hospital-year episodes. Effects are expressed as rate ratios "
              "against the geometric mean of hospitals, which avoids depending on an arbitrary reference category. Standard "
              "errors use the sandwich estimator clustered by hospital, because observations from the same hospital in "
              "successive years are correlated; with 65 to 72 clusters the sandwich is reasonably stable. Hospital effects are "
              "presented as a description of recording by place of care and never as a measure of quality or of the area's "
              "prevalence."},
    "random_intercept": {
        "es": "Como sensibilidad del modelo de efectos fijos se ajusta un modelo Poisson con intercepto aleatorio por "
              "hospital, estimado por aproximación de Laplace sobre el máximo a posteriori, con el desplazamiento añadido al "
              "predictor lineal. La contracción hacia cero de los hospitales pequeños hace visible su incertidumbre, pero el "
              "modelo supone equidispersión condicional; el diagnóstico de dispersión condicional de Pearson calculado en el "
              "óptimo muestra valores en torno a tres, es decir, sobredispersión residual apreciable. Por eso el intervalo "
              "del modelo con intercepto aleatorio es anticonservador y el resultado se mantiene solo como sensibilidad "
              "frente al modelo cuasi-Poisson con errores agrupados, que es el que se informa en el texto.",
        "en": "As a sensitivity to the fixed-effects model, a Poisson model with a hospital random intercept is fitted, "
              "estimated by a Laplace approximation at the maximum a posteriori, with the offset added to the linear "
              "predictor. The shrinkage towards zero of small hospitals makes their uncertainty visible, but the model assumes "
              "conditional equidispersion; the conditional Pearson dispersion diagnostic computed at the optimum shows values "
              "around three, that is, appreciable residual overdispersion. The interval of the random-intercept model is "
              "therefore anticonservative and the result is kept only as a sensitivity to the quasi-Poisson model with "
              "clustered errors, which is the one reported in the text."},
    "durbin_watson": {
        "es": "La autocorrelación residual se examina con el estadístico de Durbin–Watson sobre los residuos de devianza "
              "ordenados cronológicamente (y, en los modelos hospital-año, dentro de cada hospital). Valores cercanos a dos "
              "indican ausencia de correlación de primer orden. La advertencia es explícita y se repite en las notas: con "
              "menos de ocho puntos la prueba tiene muy poca potencia y su valor es orientativo, de modo que se informa como "
              "diagnóstico y nunca como justificación para aceptar o rechazar una especificación.",
        "en": "Residual autocorrelation is examined with the Durbin–Watson statistic on deviance residuals ordered "
              "chronologically (and, in the hospital-year models, within each hospital). Values close to two indicate the "
              "absence of first-order correlation. The caveat is explicit and repeated in the notes: with fewer than eight "
              "points the test has very little power and its value is indicative only, so it is reported as a diagnostic and "
              "never as a justification for accepting or rejecting a specification."},
    "wilson": {
        "es": "Las proporciones con denominador cerrado y observado —por ejemplo la proporción de egresos elegibles que "
              "reingresan dentro de un horizonte, o la proporción de episodios que llevan el código solo como diagnóstico "
              "secundario— se informan con el intervalo de Wilson [@wilson1927], que mantiene mejor cobertura que el "
              "intervalo de Wald cuando la proporción se acerca a cero o a uno y no produce límites fuera del rango "
              "[@brown2001]. El denominador debe ser el conjunto realmente elegible: en los reingresos, los egresos con "
              "identificador válido y con el horizonte completo dentro de la era del identificador, nunca a través del corte "
              "de 2020–2021.",
        "en": "Proportions with a closed, observed denominator —for example the share of eligible discharges readmitted within "
              "a horizon, or the share of episodes carrying the code only as a secondary diagnosis— are reported with the "
              "Wilson interval [@wilson1927], which keeps better coverage than the Wald interval when the proportion "
              "approaches zero or one and produces no limits outside the range [@brown2001]. The denominator must be the truly "
              "eligible set: for readmissions, discharges with a valid identifier and with the full horizon inside the "
              "identifier era, never across the 2020–2021 break."},
    "jeffreys": {
        "es": "Para proporciones muy pequeñas se usa el intervalo de Jeffreys, el intervalo bayesiano de cola igual con "
              "previa Beta(1/2, 1/2) [@jeffreys1946]. Su cobertura promedio es mejor que la de Wilson en los extremos y no "
              "colapsa a un punto cuando el numerador es cero [@brown2001]. En estas salidas se aplica a la letalidad "
              "hospitalaria —la proporción de episodios con F84 documentado cuyo tipo de alta es «fallecido», por año y "
              "posición del código—, donde el numerador anual es de pocos casos y el denominador es un conjunto cerrado y "
              "observado. Se informa siempre junto al numerador y al denominador crudos, y las celdas con menos de cinco "
              "eventos se suprimen antes de publicarse, de modo que el intervalo aparece solo en los agregados que superan "
              "el umbral.",
        "en": "For very small proportions the Jeffreys interval is used: the equal-tailed Bayesian interval with a "
              "Beta(1/2, 1/2) prior [@jeffreys1946]. Its average coverage is better than Wilson's at the extremes and it does "
              "not collapse to a point when the numerator is zero [@brown2001]. In these outputs it is applied to in-hospital "
              "lethality —the share of episodes with documented F84 whose discharge type is 'deceased', by year and code "
              "position—, where the annual numerator is a handful of cases and the denominator is a closed, observed set. It "
              "is always reported together with the raw numerator and denominator, and cells with fewer than five events are "
              "suppressed before publication, so the interval appears only in aggregates above the threshold."},
    "seasonal_index": {
        "es": "El índice estacional divide el recuento de cada mes por el promedio mensual de su propio año, de modo que la "
              "media de cada año es uno y el índice no confunde estacionalidad con tendencia; el índice mensual del período "
              "es el promedio de los índices anuales. Los episodios sin fecha de ingreso analizable se asignan a una fila de "
              "«mes desconocido», se informan y quedan fuera del índice. La interpretación es prudente: un máximo en "
              "primavera austral y un mínimo en febrero son compatibles con el calendario escolar y administrativo y no con "
              "una estacionalidad clínica del autismo.",
        "en": "The seasonal index divides each month's count by the mean monthly count of its own year, so that each year "
              "averages one and the index does not confound seasonality with trend; the monthly index for the period is the "
              "mean of the annual indices. Episodes without a parsable admission date are assigned to an 'unknown month' row, "
              "reported and left out of the index. Interpretation is cautious: a peak in the austral spring and a trough in "
              "February are compatible with the school and administrative calendar and not with any clinical seasonality of "
              "autism."},
    "index_numbers": {
        "es": "Para comparar la forma de series que tienen unidades, denominadores y coberturas distintas —episodios "
              "hospitalarios, ingresos ambulatorios, stocks bajo control y matrícula escolar— se usan números índice con el "
              "año base fijado en 100. Se declaran dos bases: 2019, primer año de la serie hospitalaria y de los stocks, y "
              "2021, primer año común a todas las series porque los códigos de autismo estricto del REM comienzan entonces. "
              "El índice compara trayectorias, no niveles, y no autoriza ningún cociente entre fuentes: dos series pueden "
              "crecer al mismo ritmo sin medir lo mismo ni referirse a las mismas personas.",
        "en": "To compare the shape of series with different units, denominators and coverage —hospital episodes, outpatient "
              "entries, stocks under control and school enrolment— index numbers with the base year set to 100 are used. Two "
              "bases are declared: 2019, the first year of the hospital series and of the stocks, and 2021, the first year "
              "common to all series because the REM strict autism codes start then. The index compares trajectories, not "
              "levels, and licenses no ratio between sources: two series can grow at the same pace without measuring the same "
              "thing or referring to the same people."},
    "spearman": {
        "es": "Las asociaciones entre variables ecológicas —por ejemplo la tasa hospitalaria de 2024 y la profundidad "
              "diagnóstica media del hospital— se resumen con el coeficiente de correlación de rangos de Spearman, que no "
              "supone linealidad y es robusto a valores extremos, con intervalo obtenido por la transformación z de Fisher. "
              "El intervalo supone unidades independientes, supuesto que la autocorrelación espacial vulnera en los análisis "
              "comunales; se declara al informarlo. Estas correlaciones describen variación de la práctica de registro entre "
              "prestadores, un fenómeno documentado en otros sistemas [@song2010; @welch2011], y no implican causalidad ni "
              "calidad asistencial.",
        "en": "Associations between ecological variables —for example the 2024 hospital rate and the hospital's mean coding "
              "depth— are summarised with Spearman's rank correlation, which assumes no linearity and is robust to outliers, "
              "with an interval from Fisher's z transformation. The interval assumes independent units, an assumption that "
              "spatial autocorrelation violates in the comuna-level analyses; this is stated when reported. These correlations "
              "describe variation in recording practice between providers, a phenomenon documented in other systems "
              "[@song2010; @welch2011], and imply neither causality nor quality of care."},
    "weighted_kappa": {
        "es": "La concordancia entre dos clasificaciones ordinales del mismo conjunto de áreas —por ejemplo los quintiles de "
              "la tasa hospitalaria y los quintiles de la tasa de ingresos ambulatorios por región— se mide con el kappa de "
              "ponderación lineal, en el que el desacuerdo penaliza en proporción a la distancia entre categorías. Se elige "
              "la ponderación lineal y no la cuadrática porque interesa el orden y no una penalización agresiva de los "
              "desacuerdos extremos. Las unidades son áreas y no personas: un acuerdo alto indica que dos sistemas ordenan "
              "el territorio de forma parecida, no que registren a los mismos individuos. Es el único estimador de esta "
              "sección que no produce archivo de salida en esta corrida: la concordancia territorial entre sistemas se "
              "informa con ρ de Spearman sobre los rangos comunales y regionales y con la I de Moran bivariada, que usan la "
              "información ordinal completa en vez de categorizarla en quintiles.",
        "en": "Agreement between two ordinal classifications of the same set of areas —for example quintiles of the hospital "
              "rate and quintiles of the outpatient entry rate by region— is measured with the linearly weighted kappa, in "
              "which disagreement is penalised in proportion to the distance between categories. Linear rather than quadratic "
              "weights are chosen because what matters is the ordering and not an aggressive penalty on extreme "
              "disagreements. The units are areas, not people: high agreement indicates that two systems rank the territory "
              "similarly, not that they record the same individuals. It is the only estimator in this section that produces "
              "no output file in this run: territorial agreement between systems is reported with Spearman's rho on the "
              "comuna and region ranks and with bivariate Moran's I, which use the full ordinal information instead of "
              "collapsing it into quintiles."},
    "survey_taylor": {
        "es": "Las dos encuestas poblacionales se analizan como muestras con diseño complejo: se declara el ponderador de "
              "expansión, el estrato y el conglomerado de primera etapa, y la proporción de cada dominio se estima como una "
              "razón conservando todas las unidades y anulando la contribución de las que quedan fuera del dominio, en vez "
              "de recortar la muestra, que sesgaría la varianza. El error estándar se obtiene por linealización de Taylor "
              "sobre la variable linealizada de la razón, sumando la varianza entre conglomerados dentro de cada estrato "
              "[@wolter2007; @lumley2004]. El intervalo se construye en la escala logit —de modo que nunca sale del intervalo "
              "unitario— con una t de grados de libertad igual al número de conglomerados menos el de estratos. Los "
              "porcentajes simples sin ponderar no se publican como estimaciones nacionales.",
        "en": "The two population surveys are analysed as complex-design samples: the expansion weight, the stratum and the "
              "first-stage cluster are declared, and each domain proportion is estimated as a ratio, keeping all units and "
              "zeroing the contribution of those outside the domain rather than truncating the sample, which would bias the "
              "variance. The standard error is obtained by Taylor linearisation of the ratio's linearised variable, summing "
              "the between-cluster variance within each stratum [@wolter2007; @lumley2004]. The interval is built on the logit "
              "scale —so that it never leaves the unit interval— with a t distribution whose degrees of freedom are the number "
              "of clusters minus the number of strata. Unweighted simple percentages are never published as national "
              "estimates."},
    "design_effect": {
        "es": "Cada estimación de encuesta se acompaña del efecto de diseño, es decir, del cociente entre la varianza del "
              "diseño complejo y la que tendría un muestreo aleatorio simple con el mismo tamaño no ponderado del dominio, y "
              "del error estándar relativo. Ambos se usan como criterio de publicación: los dominios con menos de 30 casos no "
              "ponderados o con error estándar relativo mayor que 30 % se marcan explícitamente y se presentan solo como "
              "orden de magnitud, nunca como estimaciones nacionales fiables ni desagregadas a nivel comunal. El tamaño "
              "efectivo, que es el tamaño de la muestra dividido por el efecto de diseño, acompaña a la marca.",
        "en": "Every survey estimate is accompanied by the design effect, that is, the ratio of the complex-design variance to "
              "the variance that simple random sampling with the same unweighted domain size would give, and by the relative "
              "standard error. Both are used as publication criteria: domains with fewer than 30 unweighted cases or with a "
              "relative standard error above 30% are explicitly flagged and presented only as an order of magnitude, never as "
              "reliable national estimates nor broken down to comuna level. The effective sample size, the sample size divided "
              "by the design effect, accompanies the flag."},
    "moran_global": {
        "es": "La autocorrelación espacial global se mide con la I de Moran [@moran1950] sobre una matriz de contigüidad "
              "reina estandarizada por filas: dos comunas son vecinas si comparten al menos un punto de frontera y el peso "
              "se divide por el número de vecinos, de modo que el retardo espacial es el promedio de los vecinos. Las "
              "comunas no continentales quedan fuera de la matriz —se conservan en las tablas— y las comunas que quedan sin "
              "vecino reina se informan una a una y se enlazan con su vecino más próximo, de modo que ninguna comuna "
              "continental sale del estadístico. La inferencia es por permutaciones condicionales: se reordenan los valores "
              "999 veces con una semilla fija y el valor p es la proporción de permutaciones que igualan o superan el "
              "estadístico observado, más una corrección de continuidad. La sensibilidad a la definición de vecindad se "
              "declara repitiendo el estadístico con matrices de k = 4 y k = 8 vecinos más próximos y de distancia inversa, "
              "y la sensibilidad a la escala repitiéndolo sobre las 16 regiones. El estadístico describe el patrón del "
              "registro administrativo en el territorio, no el patrón del autismo.",
        "en": "Global spatial autocorrelation is measured with Moran's I [@moran1950] on a row-standardised queen contiguity "
              "matrix: two comunas are neighbours if they share at least one boundary point and the weight is divided by the "
              "number of neighbours, so that the spatial lag is the average of the neighbours. Non-continental comunas stay "
              "out of the matrix —they remain in the tables— and comunas left without a queen neighbour are reported one by "
              "one and attached to their nearest neighbour, so that no continental comuna drops out of the statistic. "
              "Inference is by conditional permutation: values are reshuffled 999 times with a fixed seed and the p value is "
              "the proportion of permutations that equal or exceed the observed statistic, with a continuity correction. "
              "Sensitivity to the definition of neighbourhood is declared by repeating the statistic with k = 4 and k = 8 "
              "nearest-neighbour and inverse-distance matrices, and sensitivity to scale by repeating it over the 16 regions. "
              "The statistic describes the pattern of administrative recording across the territory, not the pattern of "
              "autism."},
    "moran_bivariate": {
        "es": "La I de Moran bivariada relaciona el valor estandarizado de una fuente en cada área con el promedio "
              "ponderado, en las áreas vecinas, del valor estandarizado de otra fuente: por ejemplo, la tasa hospitalaria "
              "frente al retardo espacial de los ingresos ambulatorios. Sirve para describir si dos sistemas administrativos "
              "reconocen el autismo en las mismas zonas del país, y se somete a la misma inferencia por permutaciones. La "
              "advertencia es doble: la asociación es ecológica y, cuando las dos fuentes localizan cosas distintas —lugar de "
              "atención en el REM y residencia declarada en el GRD—, parte de la correlación puede deberse a los flujos de "
              "derivación entre territorios, que no se corrigen.",
        "en": "Bivariate Moran's I relates the standardised value of one source in each area to the weighted average, across "
              "neighbouring areas, of the standardised value of another source: for example, the hospital rate against the "
              "spatial lag of outpatient entries. It describes whether two administrative systems recognise autism in the same "
              "parts of the country, and it is subjected to the same permutation inference. The caveat is twofold: the "
              "association is ecological and, when the two sources locate different things —place of care in the REM and "
              "declared residence in the GRD— part of the correlation may reflect referral flows between territories, which "
              "are not corrected."},
    "lisa": {
        "es": "Los indicadores locales de asociación espacial descomponen la I global en una contribución por área y "
              "permiten identificar conglomerados alto-alto y bajo-bajo y valores atípicos alto-bajo y bajo-alto "
              "[@anselin1995]. Cada área recibe su propio valor p por permutaciones condicionales con la misma matriz de "
              "pesos y la misma semilla. Como se realizan tantas pruebas como áreas, la multiplicidad se controla con el "
              "umbral de Benjamini–Hochberg para una tasa de falso descubrimiento de 0,05 [@benjamini1995], y los mapas "
              "muestran a la vez la clasificación al 5 % sin corregir y la corregida, de modo que el lector vea cuánto "
              "depende el resultado de la corrección.",
        "en": "Local indicators of spatial association decompose the global I into an area-specific contribution and identify "
              "high-high and low-low clusters and high-low and low-high outliers [@anselin1995]. Each area receives its own p "
              "value from conditional permutations with the same weights matrix and the same seed. Because as many tests are "
              "run as there are areas, multiplicity is controlled with the Benjamini–Hochberg threshold for a false discovery "
              "rate of 0.05 [@benjamini1995], and the maps show both the uncorrected 5% classification and the corrected one, "
              "so that the reader sees how much the result depends on the correction."},
    "getis_ord": {
        "es": "El estadístico Gi* de Getis–Ord complementa a los indicadores locales: en vez de contrastar el valor del área "
              "con el de sus vecinos, compara la suma local —el área incluida— con la suma esperada bajo aleatoriedad, de "
              "modo que identifica zonas calientes y frías de valores altos o bajos. Se calcula con la misma matriz de "
              "contigüidad, incluyendo la propia área en el vecindario, y con la misma corrección de multiplicidad "
              "[@rey2010]. Como en todo el análisis territorial, un conglomerado señala dónde se concentra el registro "
              "administrativo y debe leerse junto con la cobertura, la oferta y la profundidad de codificación de esas "
              "comunas.",
        "en": "The Getis–Ord Gi* statistic complements the local indicators: instead of contrasting an area's value with that "
              "of its neighbours, it compares the local sum —including the area itself— with the sum expected under "
              "randomness, thereby identifying hot and cold spots of high or low values. It is computed with the same "
              "contiguity matrix, including the area itself in the neighbourhood, and with the same multiplicity correction "
              "[@rey2010]. As throughout the territorial analysis, a cluster shows where administrative recording "
              "concentrates and must be read together with the coverage, the supply of services and the coding depth of those "
              "comunas."},
    "lorenz_gini": {
        "es": "La concentración territorial del registro se describe con la curva de Lorenz y el coeficiente de Gini: las "
              "áreas se ordenan de menor a mayor tasa y se acumulan, en el eje horizontal, la población del mismo "
              "denominador y, en el vertical, los eventos registrados. Un Gini cercano a cero indica que los eventos se "
              "reparten en proporción a la población y un valor alto que se concentran en pocas áreas. La medida se refiere "
              "a la concentración del registro administrativo, no a la desigualdad de acceso ni a la necesidad no cubierta: "
              "una parte de la concentración proviene de dónde están los prestadores y de a dónde se deriva a los pacientes.",
        "en": "The territorial concentration of recording is described with the Lorenz curve and the Gini coefficient: areas "
              "are ranked from the lowest to the highest rate and the population of the same denominator is cumulated on the "
              "horizontal axis and the recorded events on the vertical one. A Gini close to zero indicates that events are "
              "distributed in proportion to population and a high value that they concentrate in few areas. The measure refers "
              "to the concentration of administrative recording, not to inequality of access or unmet need: part of the "
              "concentration comes from where providers are located and where patients are referred."},
    "theil": {
        "es": "El índice de Theil mide la misma concentración con una métrica de entropía y aporta lo que el Gini no da: se "
              "descompone exactamente en un componente dentro de las regiones y otro entre regiones, lo que permite decir si "
              "la heterogeneidad del país se juega entre macrozonas o entre comunas de una misma región. Requiere valores "
              "estrictamente positivos, de modo que las áreas con cero eventos se informan aparte y no entran en el "
              "logaritmo; su número se declara junto al índice, porque excluirlas altera el resultado. Como el Gini, "
              "describe el registro y no la ocurrencia.",
        "en": "The Theil index measures the same concentration with an entropy metric and adds what the Gini does not give: it "
              "decomposes exactly into a within-region and a between-region component, which makes it possible to say whether "
              "the country's heterogeneity plays out between macro-zones or between comunas of the same region. It requires "
              "strictly positive values, so areas with zero events are reported separately and excluded from the logarithm; "
              "their number is stated next to the index, because excluding them changes the result. Like the Gini, it "
              "describes recording and not occurrence."},
    "suppression": {
        "es": "Toda tabla territorial aplica la regla de supresión: los recuentos de uno a cuatro eventos se publican como "
              "«<5», el cero verdadero se publica como cero y la ausencia de reporte se publica como «no reportado». Si tras "
              "aplicar la regla una fila queda con una sola celda suprimida, se suprime también la siguiente celda más "
              "pequeña, porque de lo contrario el valor exacto se recuperaría restando del total. Las tablas tidy internas "
              "conservan el valor real junto a la marca de supresión y a la columna de presentación, de modo que los "
              "controles de reproducción pueden verificarse sin publicar celdas pequeñas.",
        "en": "Every territorial table applies the suppression rule: counts of one to four events are published as '<5', a "
              "true zero is published as zero and absence of reporting as 'not reported'. If after applying the rule a row is "
              "left with a single suppressed cell, the next smallest cell is also suppressed, because otherwise the exact "
              "value could be recovered by subtracting from the total. The internal tidy tables keep the true value alongside "
              "the suppression flag and the display column, so that the reproduction controls can be verified without "
              "publishing small cells."},
}


# ---------------------------------------------------------------------------
# Texto: secciones M5 a M7
# ---------------------------------------------------------------------------
def _p_m5(v: _V, lang: str) -> list[str]:
    counts = _controls_counts()
    total = int(counts["checks"].sum()) if len(counts) else 0
    ok = int(counts["ok"].sum()) if len(counts) else 0
    info = int(counts["info"].sum()) if len(counts) else 0
    differs = int(counts["differs"].sum()) if len(counts) else 0
    f = lambda x: fmt_number(x, 0, lang)  # noqa: E731
    return {
        "es": [
            "**Sistema de controles.** Cada módulo del pipeline escribe su propio archivo de controles con ocho columnas: "
            "nombre del control, clave, valor esperado, valor observado, diferencia absoluta, diferencia relativa, estado y "
            "nota. El valor esperado proviene de un control preliminar del encargo, de una tabla tidy ya verificada por un "
            "módulo anterior o de una identidad interna que debe cumplirse (por ejemplo, que la suma de los doce meses "
            "iguale el total anual, o que los recuentos por hospital sumen el total nacional del mismo panel). El estado "
            "distingue coincidencia, control informativo y diferencia; ninguna diferencia se corrige en silencio y ninguna "
            "cifra se completa por plausibilidad. Si un número no se reproduce, se elimina del texto o se marca como "
            "pendiente.",
            f"**Estado actual.** Todo total de control lleva aquí su ÁMBITO, porque el estudio cuenta dos conjuntos "
            f"distintos que nunca se suman. En esta corrida, {CR.phrase(CR.PIPELINE, 'es')}, hay {f(total)} "
            f"comprobaciones, de las cuales {f(ok)} coinciden con el valor esperado, {f(info)} son informativas "
            f"(registran una cifra que no tiene un esperado externo) y {f(differs)} difieren y están explicadas una a "
            f"una en decision_log.md; es el mismo total que consolida el módulo 07 en la columna «scope = pipeline» de "
            f"controls_summary.csv; no aparece en la lámina de flujo de datos, que imprime los recuentos de las fuentes "
            f"y no los controles. El otro ámbito, "
            f"{CR.phrase(CR.ANALYSIS_PLAN, 'es')}, reúne {v.num('t8_rows')} controles y es el de la tabla de controles "
            f"preespecificados del artículo. Las diferencias conocidas "
            "corresponden a decisiones explícitas —por ejemplo, el recuento de personas dentro del año que no cuenta el "
            "marcador de identificador inválido como persona— y no a discrepancias sin resolver. El desglose módulo por "
            "módulo es la última tabla de la sección M6, junto al mapa del pipeline que nombra cada script.",
            "**Estados del dato.** Cero, ausente, no reportado, no estimable y suprimido se mantienen como estados "
            "distintos en toda la cadena, según la tabla de estados de esta sección. Un establecimiento que informa una "
            "celda vacía no informa un cero; un establecimiento sin fila no informa nada y se refleja en el número de "
            "establecimientos reportantes; una variable que el instrumento no pobló es «no estimable» y jamás un cero. Los "
            "años 2020 y 2021 se tratan como período de disrupción del reporte y no se interpolan.",
            "**Rejilla de sensibilidad.** Las variaciones de la tabla de sensibilidad se preespecificaron en el plan de "
            "análisis antes de explorar asociaciones. Cubren la definición de caso, la posición del código, el panel "
            "hospitalario, la modalidad de atención, la profundidad diagnóstica, la disrupción de 2020–2021, el "
            "denominador, la unidad del modelo, la fuente hospitalaria, la definición REM de ingreso, el desplazamiento, el "
            "semestre de los stocks, la definición educativa, el dominio de encuesta, la base poblacional y el análisis "
            "territorial. El resultado principal se acompaña siempre del rango de las especificaciones, de modo que el "
            "lector vea cuánto se mueve la conclusión y no solo la estimación central.",
        ],
        "en": [
            "**Control system.** Every pipeline module writes its own control file with eight columns: control name, key, "
            "expected value, observed value, absolute difference, relative difference, status and note. The expected value "
            "comes from a preliminary control of the brief, from a tidy table already verified by an earlier module, or from "
            "an internal identity that must hold (for example, that the sum of the twelve months equals the annual total, or "
            "that the hospital counts add up to the national total of the same panel). The status distinguishes a match, an "
            "informative control and a difference; no difference is silently corrected and no figure is ever filled in by "
            "plausibility. If a number does not reproduce, it is removed from the text or flagged as pending.",
            f"**Current state.** Every control total here carries its SCOPE, because the study counts two different "
            f"sets that are never added together. In this run, {CR.phrase(CR.PIPELINE, 'en')}, there are {f(total)} "
            f"checks, of which {f(ok)} match the expected value, {f(info)} are informative (they record a figure with no "
            f"external expected value) and {f(differs)} differ and are explained one by one in decision_log.md; it is "
            f"the same total that module 07 consolidates under 'scope = pipeline' in controls_summary.csv; it does not "
            f"appear on the data-workflow plate, which prints the counts of the sources and not the controls. "
            f"The other scope, {CR.phrase(CR.ANALYSIS_PLAN, 'en')}, holds "
            f"{v.num('t8_rows')} controls and is the one of the article's table of pre-specified controls. "
            "The known differences correspond to explicit decisions —for example, the within-year "
            "person count that does not treat the invalid-identifier placeholder as a person— and not to unresolved "
            "discrepancies. The module-by-module breakdown is the last table of section M6, next to the pipeline map that "
            "names every script.",
            "**Data states.** Zero, missing, not reported, not estimable and suppressed are kept as distinct states along the "
            "whole chain, as set out in the data-state table of this section. An establishment reporting an empty cell is not "
            "reporting a zero; an establishment with no row is reporting nothing and this is reflected in the number of "
            "reporting establishments; a variable the instrument did not populate is 'not estimable' and never a zero. The "
            "years 2020 and 2021 are treated as a reporting-disruption period and are not interpolated.",
            "**Sensitivity grid.** The variations in the sensitivity table were pre-specified in the analysis plan before "
            "associations were explored. They cover the case definition, the code position, the hospital panel, the activity "
            "type, coding depth, the 2020–2021 disruption, the denominator, the model unit, the hospital source, the REM entry "
            "definition, the offset, the half-year of the stocks, the education definition, the survey domain, the population "
            "base and the territorial analysis. The main result is always accompanied by the range across specifications, so "
            "that the reader sees how much the conclusion moves and not only the central estimate.",
        ],
    }[lang]


P_M6 = [
    {"es": "**Entorno y determinismo.** Todo el análisis se ejecuta en Python desde la raíz del repositorio, con las "
           "versiones que registra la tabla de software de esta sección. Las rutas de datos se resuelven con variables de "
           "entorno y ninguna base voluminosa se copia al repositorio. El análisis es determinista salvo la inferencia "
           "espacial por permutaciones, que se fija con la semilla declarada y 999 permutaciones, de modo que dos corridas "
           "sucesivas producen los mismos valores p. Las tablas se escriben de forma atómica y las láminas a 600 puntos por "
           "pulgada con una paleta segura para daltonismo; las ecuaciones se componen con el motor mathtext de matplotlib y "
           "la familia STIX, y se insertan como imágenes numeradas porque el conversor LaTeX a OMML disponible deforma "
           "raíces y sumatorios.",
     "en": "**Environment and determinism.** The whole analysis runs in Python from the repository root, with the versions "
           "recorded in the software table of this section. Data paths are resolved through environment variables and no large "
           "database is copied into the repository. The analysis is deterministic except for the permutation-based spatial "
           "inference, which is fixed with the declared seed and 999 permutations, so that two successive runs produce the "
           "same p values. Tables are written atomically and plates at 600 dots per inch with a colour-blind-safe palette; the "
           "equations are composed with matplotlib's mathtext engine and the STIX family and inserted as numbered images, "
           "because the available LaTeX-to-OMML converter distorts roots and summations."},
    {"es": "**Orden de ejecución.** Los módulos se ejecutan en orden numérico y cada uno depende solo de las salidas tidy de "
           "los anteriores, nunca de objetos en memoria: procedencia, núcleo hospitalario GRD, egresos DEIS, ruta "
           "administrativa REM, denominadores, encuestas, educación, modelos, controles, láminas, tablas, manuscrito, "
           "detalle episódico y metodología extendida. Cualquier paso puede repetirse por separado siempre que existan las "
           "tablas tidy que consume; los módulos que leen los archivos crudos grandes lo advierten en su documentación y "
           "cachean sus agregados. La tabla del mapa del pipeline enumera cada script con lo que hace y las salidas que "
           "produce.",
     "en": "**Order of execution.** The modules run in numerical order and each depends only on the tidy outputs of the "
           "previous ones, never on in-memory objects: provenance, GRD hospital core, DEIS discharges, REM administrative "
           "pathway, denominators, surveys, education, models, controls, plates, tables, manuscript, episode detail and "
           "extended methodology. Any step can be re-run on its own provided the tidy tables it consumes exist; the modules "
           "that read the large raw files say so in their documentation and cache their aggregates. The pipeline-map table "
           "lists every script with what it does and the outputs it produces."},
    {"es": "**Trazabilidad de las cifras.** Ninguna cifra del artículo, del suplemento o del memo está escrita a mano: todas "
           "provienen de outputs/values_<variante>.json, que un módulo específico construye leyendo las tablas tidy, o de "
           "las propias tablas y controles. Los textos en español e inglés se generan desde módulos de prosa paralelos que "
           "comparten las mismas claves de valores, las mismas claves de citación y el mismo registro de numeración "
           "suplementaria, de modo que las dos versiones no pueden divergir numéricamente. Este documento se construye con "
           "el mismo mecanismo.",
     "en": "**Traceability of the figures.** No figure in the article, the supplement or the memo is written by hand: they all "
           "come from outputs/values_<variant>.json, which a dedicated module builds by reading the tidy tables, or from the "
           "tables and controls themselves. The Spanish and English texts are generated from parallel prose modules that share "
           "the same value keys, the same citation keys and the same supplementary numbering registry, so the two versions "
           "cannot diverge numerically. This document is built by the same mechanism."},
]

P_M7 = [
    {"es": "**Lo que ningún estimador puede arreglar.** La ausencia de enlace individual es una limitación del dato y no de "
           "la técnica: ninguna fórmula de esta sección convierte seis sistemas no enlazados en una trayectoria de personas. "
           "Por eso no se estiman probabilidades de transición, tiempos de espera entre etapas ni proporciones de personas "
           "que avanzan de la detección al diagnóstico. Todo lo que se ofrece son series paralelas con sus denominadores "
           "explícitos y una descripción de si se mueven en la misma dirección.",
     "en": "**What no estimator can fix.** The absence of individual linkage is a limitation of the data and not of the "
           "technique: no formula in this section turns six unlinked systems into a trajectory of people. No transition "
           "probabilities, waiting times between stages or proportions of people moving from detection to diagnosis are "
           "therefore estimated. All that is offered are parallel series with their explicit denominators and a description "
           "of whether they move in the same direction."},
    {"es": "**Modelos de tendencia.** Las series tienen entre tres y siete puntos anuales, y en ese rango la tendencia "
           "log-lineal es una descripción compacta, no un modelo verificado: la log-linealidad no puede contrastarse "
           "seriamente, la prueba de autocorrelación carece de potencia y el intervalo del cambio porcentual anual depende "
           "de la escala de dispersión estimada con muy pocos grados de libertad. La coincidencia temporal de pandemia, "
           "cambios de códigos, expansión del reporte, mayor profundidad diagnóstica y ley impide separar sus "
           "contribuciones: por eso el indicador de 2020–2021 describe una disrupción de registro y no un efecto, y no se "
           "ajusta ninguna serie de tiempo interrumpida con pretensión causal.",
     "en": "**Trend models.** The series have between three and seven annual points, and in that range the log-linear trend is "
           "a compact description, not a verified model: log-linearity cannot be seriously tested, the autocorrelation test "
           "lacks power and the interval of the annual percent change depends on a dispersion scale estimated with very few "
           "degrees of freedom. The temporal coincidence of the pandemic, code changes, reporting expansion, deeper diagnostic "
           "coding and the law makes their contributions inseparable: the 2020–2021 indicator therefore describes a recording "
           "disruption and not an effect, and no interrupted time series is fitted with causal intent."},
    {"es": "**Estandarización y denominadores.** La población estándar mundial es una convención de comparabilidad y no una "
           "población real; una tasa estandarizada no dice nada sobre el tamaño absoluto de la demanda. Los denominadores "
           "poblacionales son proyecciones sujetas a error, especialmente en comunas pequeñas y en los años más alejados del "
           "censo base, y localizan residencia mientras varios numeradores localizan lugar de atención. En el GRD, además, "
           "la edad desconocida y los episodios sin comuna válida se informan aparte pero reducen la base efectiva de las "
           "tasas específicas.",
     "en": "**Standardisation and denominators.** The world standard population is a comparability convention and not a real "
           "population; a standardised rate says nothing about the absolute size of demand. Population denominators are "
           "projections subject to error, especially in small comunas and in the years furthest from the base census, and they "
           "locate residence while several numerators locate place of care. In the GRD, moreover, unknown age and episodes "
           "without a valid comuna are reported separately but reduce the effective base of the specific rates."},
    {"es": "**Análisis territorial.** Los estadísticos espaciales dependen de la definición de vecindad y de la escala: con "
           "contigüidad reina y comunas, el resultado está sujeto al problema de la unidad de área modificable y a efectos "
           "de borde; por eso se repiten con matrices de k vecinos más próximos y de distancia inversa y a escala regional, "
           "y aun así las comunas no continentales quedan fuera de la matriz y las comunas sin vecino reina entran con un "
           "vecino asignado. El suavizamiento bayesiano empírico estabiliza las áreas "
           "pequeñas al precio de acercarlas a la media, de modo que atenúa los contrastes reales; por eso se muestran "
           "siempre el peso de contracción y las dos versiones, cruda y suavizada. La corrección por tasa de falso "
           "descubrimiento reduce, pero no elimina, "
           "el riesgo de conglomerados espurios, y ningún conglomerado identifica una causa: la mayoría de las "
           "concentraciones coinciden con la localización de los prestadores y con los flujos de derivación.",
     "en": "**Territorial analysis.** Spatial statistics depend on the definition of neighbourhood and on scale: with queen "
           "contiguity and comunas, the result is subject to the modifiable areal unit problem and to edge effects; they are "
           "therefore repeated with nearest-neighbour and inverse-distance matrices and at the regional scale, and even so "
           "non-continental comunas stay out of the matrix and comunas without a queen neighbour enter with an assigned "
           "neighbour. Empirical-Bayes smoothing stabilises small areas at the price of pulling them towards the "
           "mean, thereby attenuating real contrasts; the shrinkage weight and both versions, crude and smoothed, are "
           "therefore always shown. The false-discovery-rate correction reduces, but does not eliminate, the risk of spurious "
           "clusters, and no cluster "
           "identifies a cause: most concentrations coincide with the location of providers and with referral flows."},
    {"es": "**Encuestas.** Las dos encuestas poblacionales miden autismo reportado por la persona o por un cuidador, con o "
           "sin confirmación profesional según el ítem, de modo que su validez depende del acceso previo a un diagnóstico y "
           "reproduce las desigualdades que el estudio describe. Los tamaños efectivos son pequeños para un desenlace poco "
           "frecuente: varios dominios quedan por debajo del umbral de 30 casos o superan el 30 % de error estándar "
           "relativo, y ninguno admite desagregación comunal. Sus estimaciones se usan como referencia de orden de magnitud "
           "frente a los registros administrativos, nunca como el valor verdadero contra el cual se mide la subdetección.",
     "en": "**Surveys.** Both population surveys measure autism reported by the person or by a caregiver, with or without "
           "professional confirmation depending on the item, so their validity depends on prior access to a diagnosis and "
           "reproduces the inequalities the study describes. Effective sizes are small for an infrequent outcome: several "
           "domains fall below the 30-case threshold or exceed a 30% relative standard error, and none admits a comuna-level "
           "breakdown. Their estimates are used as an order-of-magnitude benchmark against the administrative registers, never "
           "as the true value against which under-detection is measured."},
    {"es": "**Lo que mejoraría el método.** Tres cambios harían posibles análisis que aquí quedan fuera de alcance: una "
           "autorización de enlace determinista o probabilístico entre GRD, REM y educación con resguardo de "
           "confidencialidad, que permitiría estimar trayectorias reales; una serie posterior a 2025 con códigos REM "
           "estables, que permitiría separar la expansión del reporte del cambio de fondo; y la publicación de diagnósticos "
           "secundarios en los egresos DEIS, que haría comparables las dos fuentes hospitalarias. Mientras tanto, la "
           "convergencia entre sistemas independientes es evidencia descriptiva, no una medición de la ocurrencia del "
           "autismo en Chile.",
     "en": "**What would improve the method.** Three changes would make possible analyses that remain out of reach here: an "
           "authorisation for deterministic or probabilistic linkage between GRD, REM and education with confidentiality "
           "safeguards, which would allow real trajectories to be estimated; a post-2025 series with stable REM codes, which "
           "would allow reporting expansion to be separated from underlying change; and the publication of secondary "
           "diagnoses in the DEIS discharges, which would make the two hospital sources comparable. Until then, convergence "
           "between independent systems is descriptive evidence, not a measurement of the occurrence of autism in Chile."},
]


# ---------------------------------------------------------------------------
# Ensamblado de bloques
# ---------------------------------------------------------------------------
# El orden de esta colocación ES el orden de impresión y debe coincidir con TABLE_KEYS, que es el orden en que
# el registro compartido las numera: la tabla de controles de reproducción (M10) se imprime al final de M6,
# después del mapa del pipeline (M8) y del software y las semillas (M9), y no antes de ellas.
_TABLE_PLACEMENT = {
    "M1": ["M1_sources_units"],
    "M2": ["M2_case_definitions", "M3_rem_code_sets"],
    "M3": ["M4_denominator_layers"],
    "M4": ["M5_estimator_map"],
    "M5": ["M6_sensitivity_grid", "M7_data_states"],
    "M6": ["M8_pipeline_map", "M9_software_seeds", "M10_reproduction_controls"],
}


_SECTION_ORDER = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")   # el orden en que `methods_blocks` emite las secciones


def table_print_order() -> list[str]:
    """Claves de las tablas metodológicas en el orden en que la sección las imprime."""
    return [key for section in _SECTION_ORDER for key in _TABLE_PLACEMENT.get(section, [])]


def table_order_problems() -> list[str]:
    """Diferencias entre el orden de impresión y el orden de numeración (debe ser lista vacía)."""
    printed = table_print_order()
    problems = [f"{key} se imprime en la posición {i} y le corresponde la {TABLE_KEYS.index(key) + 1}"
                for i, key in enumerate(printed, start=1) if TABLE_KEYS.index(key) + 1 != i]
    problems += [f"tabla no impresa: {key}" for key in TABLE_KEYS if key not in printed]
    problems += [f"tabla impresa sin numeración: {key}" for key in printed if key not in TABLE_KEYS]
    return problems


# ---------------------------------------------------------------------------
# Encabezado que cita ecuaciones ↔ ecuaciones que se imprimen debajo
# ---------------------------------------------------------------------------
#: Cada estimador de M4 abre con un encabezado que cita entre paréntesis los números de sus ecuaciones, y
#: la metodología imprime cada ecuación LA PRIMERA VEZ que un estimador la cita: el umbral de
#: Benjamini–Hochberg (ecuación 28) se imprime bajo los indicadores locales y no se repite bajo Gi*, que
#: usa el mismo umbral. Un encabezado que cite las ecuaciones DECLARADAS por el estimador —y no las que se
#: imprimen bajo él— manda al lector a buscar una ecuación que está en la sección anterior. La promesa del
#: encabezado y lo que hay debajo se comparan aquí, sobre los bloques ya ensamblados, y `methods_blocks`
#: no devuelve un documento que las incumpla. El mapa de estimadores (tabla M5) es otra cosa y sigue
#: declarando TODAS las ecuaciones que definen a cada estimador, que es lo que esa columna promete.
_HEADING_EQ_RE = re.compile(r"\((?:Ecuaci(?:ón|ones)|Equations?)\s+([0-9]+(?:\s*,\s*[0-9]+)*)\)\s*$")


def _heading_equation_numbers(text: str) -> list[int] | None:
    """Números citados entre paréntesis por un encabezado, o None si no cita ninguno."""
    m = _HEADING_EQ_RE.search(str(text))
    return [int(n) for n in m.group(1).replace(" ", "").split(",")] if m else None


def heading_equation_problems(blocks: list) -> list[str]:
    """Encabezados cuyos números de ecuación no son los que se imprimen debajo (debe ser lista vacía)."""
    problems: list[str] = []
    head, claimed, printed = None, None, []

    def close() -> None:
        if head is None:
            return
        if claimed is None:
            if printed:
                problems.append(f"«{head}» no cita ecuación y debajo se imprimen "
                                + ", ".join(str(n) for n in printed))
        elif claimed != printed:
            problems.append(f"«{head}» cita " + (", ".join(str(n) for n in claimed) or "nada")
                            + " y debajo se imprime " + (", ".join(str(n) for n in printed) or "nada"))

    for kind, payload in blocks:
        if kind in ("h1", "h2", "h3", "h4"):
            close()
            head, claimed, printed = str(payload), _heading_equation_numbers(payload), []
        elif kind == "eq":
            printed = printed + [int(payload[1])]
    close()
    return problems


def methods_blocks(variant: str, V: dict | None, lang: str, R=None, first_table: int = 1) -> list:
    """Bloques de `docx_builder` con la metodología extendida completa, en `lang` y para `variant`.

    `R` es el registro de numeración suplementaria del módulo de prosa que construye el documento
    (`prose_en._Registry` / `prose_es._Registry`); si no conoce las claves nuevas se usa una numeración
    provisional que empieza en `first_table`. No se construye ningún documento aquí.
    """
    if lang not in LANGS:
        raise ValueError(f"idioma desconocido: {lang!r}")
    if variant not in CFG.VARIANTS:
        raise ValueError(f"variante desconocida: {variant!r}")
    v = _V(V, lang)
    # Dos invariantes de presentación, comprobadas en cada construcción y no solo en las pruebas: las
    # ecuaciones deben imprimirse en el orden de su número y las diez tablas metodológicas en el orden de su
    # numeración. Si alguna se rompe, el documento no se construye.
    EQ.check_display_order()
    problems = table_order_problems()
    if problems:
        raise RuntimeError("el orden de impresión de las tablas metodológicas no sigue su numeración: "
                           + "; ".join(problems))
    eq_paths = EQ.ensure_rendered(lang=lang)
    specs = table_specs(variant, lang, V)
    blocks: list = []
    counter = {"table": first_table}
    emitted_eq: set[str] = set()

    def add_tables(section: str) -> None:
        for key in _TABLE_PLACEMENT.get(section, []):
            spec = specs[key]
            label = _label(R, key, lang, counter["table"])
            counter["table"] += 1
            blocks.append(("table", dict(df=spec["df"], title=spec["title"], note=spec["note"], label=label)))

    def add_equations(estimator: dict) -> None:
        for eq_key in estimator["eq"]:
            if eq_key in emitted_eq:
                continue
            emitted_eq.add(eq_key)
            blocks.append(("eq", (list(eq_paths[eq_key]), EQ.NUMBER[eq_key])))

    blocks.append(("h1", SECTIONS["root"][lang]))
    for para in INTRO:
        blocks.append(("p", para[lang]))

    blocks.append(("h2", SECTIONS["M1"][lang]))
    for para in P_M1:
        blocks.append(("p", para[lang]))
    add_tables("M1")

    blocks.append(("h2", SECTIONS["M2"][lang]))
    for para in P_M2:
        blocks.append(("p", para[lang]))
    add_tables("M2")

    blocks.append(("h2", SECTIONS["M3"][lang]))
    for para in P_M3:
        blocks.append(("p", para[lang]))
    add_tables("M3")

    blocks.append(("h2", SECTIONS["M4"][lang]))
    for para in P_M4_INTRO:
        blocks.append(("p", para[lang]))
    for estimator in EQ.ESTIMATORS:
        # El encabezado cita LO QUE SE IMPRIME DEBAJO de él, no todas las ecuaciones declaradas por el
        # estimador: la ecuación que un estimador anterior ya imprimió no se repite (el umbral de
        # Benjamini–Hochberg, ecuación 28, se imprime bajo los indicadores locales y Gi* lo reutiliza),
        # y citarla aquí mandaba al lector a buscarla bajo un encabezado donde no está. La lista completa
        # de ecuaciones que definen a cada estimador sigue en el mapa de estimadores (tabla M5).
        shown = [k for k in estimator["eq"] if k not in emitted_eq]
        if not shown:
            raise RuntimeError(f"el estimador {estimator['key']!r} no imprime ninguna ecuación propia: "
                               "su encabezado no puede citar ninguna")
        numbers = ", ".join(str(n) for n in sorted(EQ.NUMBER[k] for k in shown))   # ascendentes
        word = ("Ecuación " if len(shown) == 1 else "Ecuaciones ") if lang == "es" else \
               ("Equation " if len(shown) == 1 else "Equations ")
        blocks.append(("h3", f"{_t(estimator['name'], lang)} ({word}{numbers})"))
        blocks.append(("p", EST_TEXT[estimator["key"]][lang]))
        add_equations(estimator)
    add_tables("M4")

    blocks.append(("h2", SECTIONS["M5"][lang]))
    for text in _p_m5(v, lang):
        blocks.append(("p", text))
    add_tables("M5")

    blocks.append(("h2", SECTIONS["M6"][lang]))
    for para in P_M6:
        blocks.append(("p", para[lang]))
    add_tables("M6")

    blocks.append(("h2", SECTIONS["M7"][lang]))
    for para in P_M7:
        blocks.append(("p", para[lang]))
    bad = heading_equation_problems(blocks)
    if bad:
        raise RuntimeError("un encabezado cita ecuaciones que no se imprimen debajo: " + "; ".join(bad))
    return blocks


_CIT_RE = re.compile(r"\[@[^\]]+\]")


def word_count(blocks: list) -> int:
    """Palabras del texto (párrafos y viñetas), sin marcadores de cita ni marcas de énfasis."""
    total = 0
    for kind, payload in blocks:
        if kind in ("p", "small"):
            texts = [payload]
        elif kind == "bullets":
            texts = list(payload)
        else:
            continue
        for text in texts:
            clean = _CIT_RE.sub("", str(text)).replace("**", "").replace("*", "")
            total += len(clean.split())
    return total


def citation_keys(blocks: list) -> list[str]:
    """Claves de citación en orden de aparición (para verificar que existen en el .bib)."""
    keys: list[str] = []
    for kind, payload in blocks:
        texts = []
        if kind in ("p", "small"):
            texts = [payload]
        elif kind == "bullets":
            texts = list(payload)
        elif kind == "table":
            texts = [payload.get("note", ""), payload.get("title", "")]
        for text in texts:
            for marker in _CIT_RE.findall(str(text)):
                for part in marker.strip("[]").split(";"):
                    key = part.strip().lstrip("@")
                    if key and key not in keys:
                        keys.append(key)
    return keys


def estimators_without_equation() -> list[str]:
    """Estimadores del registro sin ecuación o sin párrafo de texto."""
    missing = EQ.orphan_estimators()
    missing += [e["key"] for e in EQ.ESTIMATORS if e["key"] not in EST_TEXT]
    return sorted(set(missing))


if __name__ == "__main__":
    for _lang in LANGS:
        _b = methods_blocks("con_rett", None, _lang)
        print(_lang, len(_b), "bloques;", word_count(_b), "palabras;",
              sum(1 for k, _ in _b if k == "eq"), "ecuaciones;", sum(1 for k, _ in _b if k == "table"), "tablas")
