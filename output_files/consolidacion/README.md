# Diccionario de salidas

Ejecución completa: 3 de septiembre de 2026. Datos fuente: GRD 2019–2024, REM 2017–2024, proyecciones INE base Censo 2017 y cartografía comunal y regional. Esta carpeta contiene únicamente agregados y metadatos. Los identificadores de paciente se procesan en memoria y no se exportan.

## Auditoría

| Archivo | Unidad y contenido |
|---|---|
| `grd_source_inventory.csv` | Archivo/año: tamaño, modificación y filas; los hashes originales están en el manifiesto externo GRD |
| `grd_linkage_by_year.csv` | Año: registros, identificadores, faltantes e inconsistencias demográficas internas |
| `grd_linkage_between_years.csv` | Par de años: identificadores compartidos y concordancia entre aquellos comparables |
| `grd_trajectory_quality.csv` | Período: universo F84 antes de exclusiones, duplicados, identificadores inconsistentes, episodios ambiguos y fechas inválidas; causas solapadas |
| `rem_code_catalogue.csv` | Año/código: etiqueta, formulario, sección, regla de total y referencia exacta a archivo/hoja/fila de diccionario |
| `rem_quality.csv` | Año: cobertura de códigos, duplicados, verificaciones de sexo/edad entre filas completas y metadatos de entrada |
| `grd_epi_quality.csv` | Año: registros leídos, registros F84, duplicados exactos, sin identificador, sin sexo, fechas inválidas, edad implausible, sin comuna, altas por fallecimiento |
| `grd_comuna_unmatched.csv` | Nombres de comuna de residencia no enlazados al catálogo INE, con registros afectados |
| `grd_rates_excluded.csv` | Año/definición: registros sin sexo o sin edad excluidos de las tasas |
| `grd_rates_regional_coverage.csv` | Año: registros con y sin región de residencia asignada |
| `catalogo_comunas.csv` | Código único territorial, nombre, nombre normalizado, región y marca de comuna continental |
| `grd_hospital_catalogue.csv` | Código de hospital y nombre según el catálogo GRD |

## GRD

Todas las tablas analíticas llevan `era` y `definition`. Los períodos no se enlazan ni se suman como personas únicas. Las definiciones se solapan: tampoco se suman entre sí.

- `autismo_F840`: F84.0.
- `TEA_operacional`: F84.0, F84.1, F84.5, F84.8, F84.9.
- `F84_historico`: F84 y sus subcategorías válidas F84.0–.5, .8 y .9; incluye Rett. No equivale automáticamente a TEA según clasificaciones clínicas actuales.

| Archivo | Unidad y denominador |
|---|---|
| `grd_annual_positions.csv` | Año/posición: registros con identificador tras deduplicación exacta e identificadores distintos dentro de la celda. Un ID puede aparecer en varias posiciones/años. Incluye los ID luego excluidos de la cohorte longitudinal |
| `grd_cohort_summary.csv` | Una fila por período/definición: ID incluidos tras controles, número con egresos previos, grupos de interés, edad y oportunidad de observación |
| `grd_first_position.csv` | Posición en el primer alta observada con el código: categorías mutuamente excluyentes y exhaustivas para la cohorte |
| `grd_cohort_strata.csv` | Año índice, posición, sexo y banda de edad: denominador `patients` de la celda |
| `grd_previous_codes.csv` | Código previo por ventana y posición: un ID una vez por código/ventana/posición. Denominador de referencia: cohorte o ID con egresos previos, indicándolo expresamente |
| `grd_previous_groups.csv` | Igual que códigos previos, agrupados en categorías exploratorias. Los grupos pueden coexistir |
| `grd_first_hospital_principal.csv` | Principal del primer egreso observado del ID, que puede ser el propio índice si no hay antecedentes |
| `grd_last_prior_principal.csv` | Último principal estrictamente anterior al ingreso índice, entre ID con egreso previo |
| `grd_index_principal.csv` | Diagnóstico principal del episodio índice, por posición del código TEA. Es contemporáneo, no antecedente |
| `grd_sequences.csv` | Primer principal → último principal previo → posición índice. Solo ID con antecedentes y sin empates en las dos etapas previas; no es toda la cohorte |
| `grd_principal_transitions.csv` | Posición inicial: transición posterior a principal. `later_principal_365d / eligible_followup_365d` es el cociente a un año; `later_principal` admite todo el seguimiento disponible |

Los códigos CIE-10 se conservan normalizados sin punto. `window=all` corresponde a todo el período previo observable; `365d` y `730d` restringen las fechas de los antecedentes, pero **no restringen la cohorte a personas con esas ventanas completas**. `position=principal` es DIAGNOSTICO1 y `any` incluye 1–35. Un antecedente debe haber egresado antes del ingreso índice. No se incluyen los diagnósticos contemporáneos como antecedentes.

`lookback_365d/730d` mide calendario disponible desde el comienzo del período; `observed_prior_365d/730d` exige al menos un egreso previo a esa distancia. Ninguna variable demuestra observación clínica continua. El tiempo hasta principal se mide desde el alta índice al ingreso posterior. Los empates de fecha conservan todos los códigos pertinentes, por lo que las tablas por código pueden superar el número de ID al sumarlas.

### Epidemiología descriptiva (`grd_epidemiology.py`)

Todas las tablas usan la definición (`definition`) y el rol del código en el episodio (`role`: `principal`, `solo_secundario`, `principal_y_secundario`). Un registro es un episodio tras deduplicación exacta dentro del año.

| Archivo | Unidad y contenido |
|---|---|
| `grd_epi_strata.csv` | Año/definición/rol/sexo/grupo de edad/comuna de residencia normalizada: registros, identificadores distintos en la celda y registros sin identificador |
| `grd_epi_persons_year.csv` | Año/definición/sexo/grupo de edad/comuna: identificadores distintos en el año (atributos del primer registro del año) |
| `grd_epi_persons_era.csv` | Período/definición/sexo/grupo de edad/comuna: identificadores distintos en el período |
| `grd_epi_age_single.csv` | Año/definición/rol/sexo/edad simple: registros |
| `grd_epi_monthly.csv` | Año/definición/rol/mes de ingreso: registros |
| `grd_epi_subcodes.csv` | Año/subcategoría F84/posición/sexo/grupo de edad: registros; un registro cuenta una vez por subcategoría y posición |
| `grd_epi_features.csv` | Año/definición/rol/variable/valor: registros. Variables crudas del productor y agrupadas (`prevision_grupo`, `nacionalidad_grupo`, `etnia_grupo`, `age_band`, `los_bin`) |
| `grd_epi_los.csv`, `grd_epi_los_summary.csv`, `grd_epi_los_age.csv` | Estancia en días por año/definición/rol/tipo de actividad (y grupo de edad): n, media, DE, mediana, cuartiles, P90, máximo, días totales y estancias 0 |
| `grd_epi_grd_weight.csv` | Año/definición/rol: peso relativo IR-GRD (n, media, mediana, cuartiles) |
| `grd_epi_hospitals.csv` | Año/definición/rol/hospital: registros e identificadores |
| `grd_epi_codiagnoses.csv` | Año/definición/rol del TEA/posición del código/categoría CIE-10 de tres caracteres: registros; un registro cuenta una vez por categoría y posición |
| `grd_epi_readmissions.csv` | Período/definición/año/horizonte: egresos con identificador y fechas, elegibles con horizonte disponible y rehospitalizados con código de la definición |
| `grd_epi_multiplicity.csv` | Período/definición/número de episodios por identificador: personas y registros |

### Tasas, tendencias y estadísticos espaciales (`epi_rates.py`)

Denominadores: personas-año INE. `unit` distingue `records` (episodios) y `persons` (identificadores distintos). Las tasas estandarizadas usan la población estándar OMS y límites gamma (Fay–Feuer); las crudas, límites exactos de Poisson.

| Archivo | Unidad y contenido |
|---|---|
| `population_regional.csv`, `population_comunal` (implícita en las tablas), `population_regional_young.csv` | Población INE por año, región, sexo y grupo de edad; y por edad simple 0 a 5 años |
| `grd_rates_national.csv` | Año/definición/unidad/rol/sexo (HOMBRE, MUJER, TOTAL): conteo, población, tasa cruda e IC, TEE e IC, varianza de la TEE |
| `grd_rates_age_specific.csv` | Definición/unidad/año/sexo/grupo de edad: tasa específica e IC exacto |
| `grd_sex_ratio.csv` | Definición/unidad/rol/año: razón H:M de TEE (IC log-normal) y de conteos (IC binomial exacto) |
| `grd_trends_apc.csv` | Definición/unidad/rol/sexo/período: cambio porcentual anual promedio cuasi-Poisson, IC, valor p y factor de sobredispersión |
| `grd_rates_subcodes.csv` | Año/subcategoría/posición/sexo: conteo, tasa cruda y TEE con IC |
| `grd_rates_regional.csv` | Unidad/período (anual, 2019–2024, 2021–2024)/región de residencia/sexo: conteo, personas-año, tasa cruda y TEE con IC |
| `grd_rates_comunal.csv` | Unidad/período/comuna: conteo, personas-año, tasa cruda, TEE con IC, esperados por estandarización indirecta, razón de hospitalización estandarizada (RHE) con IC, RHE suavizada (empirical Bayes), peso de contracción y parámetros a priori |
| `grd_spatial_moran.csv` | Unidad/período/variable (TEE, RHE, RHE suavizada): I de Moran global, esperanza, z y p analíticos y por 999 permutaciones, comunas e islas |
| `grd_spatial_lisa.csv` | Comuna: valor, rezago espacial, I local, cuadrante, p de permutación, umbral FDR y clasificación con p < 0,05 y con FDR |
| `rem_rates_national.csv` | Año/serie (autismo 05990022, TGD genérico 06902600, totales de ingresos y egresos de subcategorías)/sexo: ingresos por 100.000 habitantes, crudos y TEE con IC |
| `rem_rates_age_specific.csv` | Serie/año/sexo/grupo de edad: tasa de ingreso específica e IC |
| `rem_rates_regional.csv` | Serie/período/región del establecimiento/sexo: ingresos, población, tasa cruda y TEE con IC |
| `rem_grd_ecological.csv` | Región/año 2021–2024: tasas REM de ingresos y tasas GRD de registros y de personas |

## REM

| Archivo | Unidad y contenido |
|---|---|
| `rem_monthly_region_raw_columns.csv` | Año/mes/región/código: sumas de columnas originales, filas y establecimientos informantes |
| `rem_annual_by_code.csv` | Año/código: sumas, catálogo, meses presentes y cobertura de campos |
| `rem_a05_age_sex.csv` | Año/código/banda de edad/sexo: sumas de valores observados de las columnas A05 04–37; no incluye totales ni subgrupos adicionales |
| `rem_a05_region_age_sex.csv` | Año/código/región/banda de edad/sexo: las mismas sumas por región del establecimiento |
| `rem_annual_comuna.csv` | Año/código/región/comuna del establecimiento: sumas de `Col01` a `Col03`, `total_known`, filas, filas con total y establecimientos informantes |
| `rem_establishment_panel.csv` | Año/código/servicio/región/comuna/establecimiento: meses con fila, filas, meses con total positivo, sumas de `total_known` y `Col01` |

**Las columnas crudas no tienen semántica universal.** A05: `Col01` total, `Col02` hombres, `Col03` mujeres. A03 en las secciones seleccionadas: `Col01` hombres, `Col02` mujeres; no son total y subgrupo. A28 se mantiene por sección, sin sumar automáticamente los dos códigos de ingreso.

`total_known` suma los totales de **filas completas para esa regla**: en A03 exige ambas columnas de sexo, en A05/A28 exige Col01. `rows_total_known` cuenta las filas que cumplieron esa condición. Si es menor que `rows`, `total_known` no es un total completo del código; no usarlo directamente como denominador poblacional o como total nacional. Las columnas crudas se agregan por sus valores observados con `min_count=1`, por lo que pueden representar coberturas diferentes. Se mantienen vacíos cuando no hay ningún valor observado.

`months=12` acredita presencia del código en doce meses, no completitud de todos los establecimientos. `reporting_establishments` cuenta establecimientos con una fila seleccionada, no toda la red ni necesariamente establecimientos activos con prestación positiva. Las sumas territoriales no certifican personas únicas.

La ausencia de una fila, una celda vacía y un cero explícito se distinguen; no se imputa cero automáticamente. Los resultados actuales no calculan positividad de tamizaje, incidencia, prevalencia, retención ni tasas poblacionales.
