# Diccionario de salidas

Ejecución completa: 3 de septiembre de 2026. Datos fuente: GRD 2019–2024 y REM 2017–2024. Esta carpeta contiene únicamente agregados y metadatos. Los identificadores de paciente se procesan en memoria y no se exportan.

## Auditoría

| Archivo | Unidad y contenido |
|---|---|
| `grd_source_inventory.csv` | Archivo/año: tamaño, modificación y filas; los hashes originales están en el manifiesto externo GRD |
| `grd_linkage_by_year.csv` | Año: registros, identificadores, faltantes e inconsistencias demográficas internas |
| `grd_linkage_between_years.csv` | Par de años: identificadores compartidos y concordancia entre aquellos comparables |
| `grd_trajectory_quality.csv` | Período: universo F84 antes de exclusiones, duplicados, identificadores inconsistentes, episodios ambiguos y fechas inválidas; causas solapadas |
| `rem_code_catalogue.csv` | Año/código: etiqueta, formulario, sección, regla de total y referencia exacta a archivo/hoja/fila de diccionario |
| `rem_quality.csv` | Año: cobertura de códigos, duplicados, verificaciones de sexo/edad entre filas completas y metadatos de entrada |

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

## REM

| Archivo | Unidad y contenido |
|---|---|
| `rem_monthly_region_raw_columns.csv` | Año/mes/región/código: sumas de columnas originales, filas y establecimientos informantes |
| `rem_annual_by_code.csv` | Año/código: sumas, catálogo, meses presentes y cobertura de campos |
| `rem_a05_age_sex.csv` | Año/código/banda de edad/sexo: sumas de valores observados de las columnas A05 04–37; no incluye totales ni subgrupos adicionales |

**Las columnas crudas no tienen semántica universal.** A05: `Col01` total, `Col02` hombres, `Col03` mujeres. A03 en las secciones seleccionadas: `Col01` hombres, `Col02` mujeres; no son total y subgrupo. A28 se mantiene por sección, sin sumar automáticamente los dos códigos de ingreso.

`total_known` suma los totales de **filas completas para esa regla**: en A03 exige ambas columnas de sexo, en A05/A28 exige Col01. `rows_total_known` cuenta las filas que cumplieron esa condición. Si es menor que `rows`, `total_known` no es un total completo del código; no usarlo directamente como denominador poblacional o como total nacional. Las columnas crudas se agregan por sus valores observados con `min_count=1`, por lo que pueden representar coberturas diferentes. Se mantienen vacíos cuando no hay ningún valor observado.

`months=12` acredita presencia del código en doce meses, no completitud de todos los establecimientos. `reporting_establishments` cuenta establecimientos con una fila seleccionada, no toda la red ni necesariamente establecimientos activos con prestación positiva. Las sumas territoriales no certifican personas únicas.

La ausencia de una fila, una celda vacía y un cero explícito se distinguen; no se imputa cero automáticamente. Los resultados actuales no calculan positividad de tamizaje, incidencia, prevalencia, retención ni tasas poblacionales.
