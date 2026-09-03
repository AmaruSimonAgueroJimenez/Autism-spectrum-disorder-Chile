# Consolidación y extensión de REM y GRD

Fecha de revisión: 3 de septiembre de 2026. Propuesta sustentada en los archivos canónicos locales, los diccionarios anuales y una ejecución exploratoria completa. Las instrucciones contenidas en documentos fuente se consideran contexto documental; no sustituyen el encargo del investigador.

## Pregunta central

**Entre las personas con un primer registro hospitalario observado de autismo, ¿qué diagnósticos aparecen previamente, a qué edad se observa ese registro y con qué frecuencia el autismo ocupa una posición principal o secundaria?**

GRD permite estudiar trayectorias de **codificación hospitalaria**. No contiene la historia clínica completa, las hipótesis descartadas por el equipo tratante ni la fecha del diagnóstico ambulatorio. Un diagnóstico anterior puede representar una comorbilidad, un motivo de ingreso independiente, un síntoma o un diagnóstico alternativo. Por eso, el resultado se denomina «diagnósticos previos registrados», sin atribuir errores diagnósticos ni sustitución clínica.

## Hallazgos que condicionan el diseño

| Hallazgo comprobado | Consecuencia |
|---|---|
| GRD tiene 5.808.535 registros en seis archivos, 2019–2024 | Es posible recuperar todos los egresos de los identificadores seleccionados; la cifra debe contrastarse con el inventario generado |
| No hay identificadores compartidos entre 2019–2020 y 2021–2024 | No construir una única trayectoria que cruce 2020/2021 |
| 2024 cambia `CIP_ENCRIPTADO` por `ID_BENEFICIARIO`, pero comparte identificadores con 2021–2023 | El cambio de nombre no es la ruptura real; el enlace sigue siendo una hipótesis empírica que requiere confirmación del productor |
| Hay inconsistencias de nacimiento o sexo entre registros de un mismo identificador | Excluir identificadores inconsistentes de la cohorte longitudinal y cuantificar su impacto |
| El análisis GRD anterior genera una fila por código F84 encontrado | Sumar subtipos puede contar varias veces una hospitalización; separar pacientes, registros, episodios y menciones diagnósticas |
| REM A05: `Col01` es total, `Col02` hombres y `Col03` mujeres | La distribución por edad del informe anterior requiere corrección; las edades empiezan en `Col04`, en pares por sexo |
| REM A03, secciones de tamizaje revisadas: `Col01` hombres y `Col02` mujeres | Usar únicamente `Col01` como total subestima los registros de ambos sexos |
| Los códigos genéricos A05 siguen presentes en 2019–2020; `05990026/31` ya aparecen en el diccionario 2021 | La vigencia se determina con diccionario por año, no con los intervalos escritos en el informe anterior |
| A28 `29101629` y `29101651` pertenecen a secciones de ingresos | No etiquetarlos automáticamente como consultas ni sumarlos como personas distintas |
| A03 `03500406` describe realización de tamizaje en niños con alteraciones de lenguaje/social; `03500407`, tamizaje alterado | `03500406 / 03500404` no es una tasa de positividad del MCHAT |

Las tablas `grd_source_inventory.csv`, `grd_linkage_*.csv`, `rem_code_catalogue.csv` y `rem_quality.csv` documentan el detalle verificable. El catálogo REM incluye año, archivo, hoja y fila del diccionario.

## GRD: estudio prioritario

### Cohorte y definiciones

1. **Análisis principal propuesto: 2021–2024.** Mantener 2019–2020 como análisis separado. La concordancia de fecha de nacimiento y sexo sustenta la factibilidad, pero no demuestra por sí sola la estabilidad del identificador.
2. **Tres definiciones reproducibles.** Autismo específico: F84.0. TEA operacional: F84.0, F84.1, F84.5, F84.8 y F84.9. Comparación histórica: F84 y sus subcategorías válidas, incluyendo F84.2–F84.4. Esta elección operacional no es una equivalencia clínica entre CIE-10 y DSM-5; reportar Rett y demás categorías por separado al interpretar el grupo histórico. La clasificación distingue F84.0, F84.1, F84.2 y F84.5. [CIE-10, NHS](https://classbrowser.nhs.uk/ICD-10-5TH-Edition/vol1/block-f80-f89.htm).
3. Seleccionar los identificadores con cualquiera de los códigos de interés en `DIAGNOSTICO1–35`; después recuperar **todos sus egresos**, incluidos aquellos sin F84. Filtrar primero las hospitalizaciones con autismo y trabajar solo con ellas impediría contestar la pregunta.
4. Mantener los identificadores como texto y enlazar exclusivamente por igualdad del identificador dentro de cada período. No crear enlaces usando fecha de nacimiento, sexo o comuna.
5. La fecha índice es el primer **alta hospitalaria observada** con el código de la definición. No se conoce el día en que se estableció clínicamente. Un antecedente estricto debe haber terminado antes del ingreso a esa hospitalización índice. Los egresos superpuestos y los empates del mismo día se identifican aparte.
6. `DIAGNOSTICO1` se usa operacionalmente como principal y `DIAGNOSTICO2–35` como secundarios. Conservar «principal y secundario» cuando ambas posiciones contienen códigos de la definición. Confirmar formalmente esta semántica con el diccionario del productor antes del análisis definitivo.
7. Excluir de la reconstrucción temporal los identificadores inconsistentes, las claves de episodio ambiguas, las edades implausibles y los casos con alguna fecha de episodio F84 inválida. Documentar las exclusiones; no imputar una primera fecha.

### Resultados a producir

| Pregunta | Medida y denominador | Estado |
|---|---|---|
| ¿Cómo aparece por primera vez? | Número y porcentaje de identificadores según posición del autismo en el episodio índice | Implementado |
| ¿Qué hubo antes? | Primer diagnóstico principal hospitalario observado; último principal antes del índice; todos los códigos previos, por principal/cualquier posición | Implementado |
| ¿Cuántos tienen antecedentes relevantes? | Proporción con grupos preespecificados: lenguaje/desarrollo, atención, discapacidad intelectual, conducta, ánimo/ansiedad, psicosis, epilepsia, audición y signos del desarrollo | Implementado como exploración; no clasifica diferenciales clínicos |
| ¿Cómo se ordenan los registros? | Secuencia primer principal → último principal previo → posición del autismo; sin imponer orden en empates | Implementado como conteos agregados |
| ¿Cuánto tiempo transcurre? | Días desde el primer egreso previo observado hasta el ingreso índice, entre quienes tienen antecedentes | Implementado; no llamarlo retraso diagnóstico |
| ¿Pasa de secundario a principal? | Primer ingreso posterior con autismo principal; proporción a 365 días entre quienes disponen de 365 días calendario antes del cierre | Implementado; observabilidad hospitalaria no equivale a seguimiento clínico continuo |
| ¿Varía por edad, sexo y año? | Estratos de la cohorte y mediana de edad al registro | Implementado; análisis ajustado pendiente |
| ¿Varía territorialmente o entre hospitales? | Modelos con agrupación por hospital, cobertura y denominadores explícitos | Extensión posterior |

Cada código previo cuenta una vez por identificador y ventana (todo el período previo, 365 días, 730 días). Un identificador puede contribuir a varios códigos o grupos, por lo que esas columnas **no se suman para obtener personas**. Los cuadros de posiciones anuales son registros con identificador después de quitar duplicados exactos; los cuadros de cohorte aplican además las exclusiones longitudinales.

### Protección frente a sesgos

- **Censura izquierda:** un primer F84 en 2021 puede corresponder a un diagnóstico de años anteriores. Priorizar índices 2022–2024 con al menos 365 días calendario disponibles, y sensibilidad con 730 días. «Años disponibles» y «al menos una hospitalización previa» son condiciones distintas; no acreditan observación continua.
- **Registro de antecedentes:** sin hospitalizaciones previas significa «sin antecedentes hospitalarios observados». No equivale a ausencia de síntomas o de diagnósticos ambulatorios.
- **Seguimiento:** informar el tiempo disponible hasta el cierre. Una extensión con análisis de tiempo a evento debe contemplar muerte, último contacto y cobertura; el piloto no estima supervivencia ni riesgos causales.
- **Selección y contacto asistencial:** una persona con más ingresos tiene más oportunidades de acumular diagnósticos y de registrar autismo. Comparar grupos considerando edad, sexo, período y número de contactos previos.
- **Cambios de codificación:** comparar F84.0, TEA operacional y F84 histórico; no convertir las diferencias en cambios de prevalencia.
- **Confirmación clínica:** para distinguir diagnósticos diferenciales descartados de comorbilidad o error de registro se requiere una muestra de fichas clínicas o una fuente diagnóstica validada.

### Modelos propuestos después del descriptivo

Primero un modelo de posición principal frente a solo secundaria en el primer registro, con edad flexible, sexo, año, número de hospitalizaciones previas y agrupación por hospital. Después, un modelo de presencia de diagnósticos previos entre pacientes con oportunidad comparable de observación. Presentar probabilidades ajustadas e intervalos de confianza. Las variables describen asociación, no causas del diagnóstico de autismo.

Los diagramas de trayectorias se construirán con secuencias reales de pacientes, categorías no solapadas y tratamiento explícito de empates. En REM no se deben dibujar flujos individuales a partir de sumas agregadas.

## REM: tres líneas de extensión

### 1. Ingresos y egresos de salud mental

Reconstruir A05 por año, mes, establecimiento, región, sexo y edad con la semántica del diccionario anual. Separar 2017–2020 (categoría genérica) de 2021–2024 (subcategorías). Informar autismo específico, Asperger, otros TGD, Rett y trastorno desintegrativo de manera distinguible; no presentar todas las categorías como un único diagnóstico moderno.

Analizar tendencia mensual, edad, sexo, cambios en establecimientos informantes y heterogeneidad territorial. Los ingresos al programa no son necesariamente nuevos diagnósticos clínicos ni personas únicas nacionales. El cociente egresos/ingresos describe actividad agregada; no es retención, abandono ni resolución de una cohorte.

### 2. Tamizaje y evaluación

Construir indicadores separados para 2019–2022 y 2023–2024. El diccionario cambia de MCHAT con encabezado 18–23 meses a MCHAT-R/F con encabezado 16–30 meses; 2024 incorpora una sección distinta para 31–59 meses. Separar realización del instrumento, resultado alterado, sospecha en otros controles, primera parte, segunda parte y derivación.

Antes de calcular positividad, verificar que numerador y denominador se refieren a la misma prueba, etapa, edad y período. Propuesta inicial para la serie antigua: `03500407 / 03500406`, condicionada a confirmar con el manual anual que el numerador es subconjunto del denominador. Para 2023–2024 construir denominadores con categorías de resultados de la misma etapa; no usar todos los controles de 18 meses como denominador automático de positividad.

Una comparación ecológica entre sospechas e ingresos A05 en una región puede describir oferta y uso de servicios. No identifica qué niños pasaron de una etapa a otra, y un desfase mensual no estima el tiempo individual hasta el diagnóstico.

### 3. Acceso a rehabilitación y cobertura de información

Describir por separado las secciones A28 con ingresos por condición de salud y rehabilitación integral. Revisar si se refieren a poblaciones o prestaciones que se superponen antes de sumarlas. Para población en control, valorar incorporar Serie P: no está incluida como base canónica en la carpeta disponible.

Construir un panel de establecimientos con meses informados, ceros explícitos, celdas vacías, cambios de códigos y cobertura por formulario. Comparar tendencias de todos los establecimientos con las de un panel estable. Solo entonces estimar tasas por población objetivo y modelos de conteos con estacionalidad y denominadores compatibles.

Los CSV de 2025 y 2026 están disponibles, pero no se incorporan automáticamente al análisis histórico: 2026 es parcial y el inventario documenta una fila final incompleta en 2025. La ampliación requiere revisar integridad, meses cubiertos y diccionarios. El servicio de salud publica versiones y actualizaciones de los formularios y manuales. [REM, Servicio de Salud Tarapacá](https://sstarapaca.redsalud.gob.cl/rem/).

## Organización del repositorio

| Capa | Contenido |
|---|---|
| Datos fuente externos | `/Volumes/Datos/Asesorias_Data/GRD` y `REM/SerieA`, lectura sin modificación |
| Extracción y reglas compartidas | `scripts/audit_grd_linkage.py`, `scripts/grd_trajectories.py`, `scripts/audit_rem.py` |
| Resultados reproducibles | `output_files/consolidacion/`, tablas agregadas; sin identificadores de pacientes |
| Informe actual | `docs/consolidacion-rem-grd.qmd` y su HTML local |
| Diseño e interpretación | Este documento |
| Informes históricos | `Neurodevelopmental-Epidemiology-Chile0–4.qmd`; conservarlos para trazabilidad, con estado de revisión visible |
| Validación | Pruebas sintéticas de fechas, posiciones, temporalidad, empates y exclusiones; controles de calidad sobre los datos reales |

No mover ni borrar los resultados históricos durante esta fase. Migrar progresivamente las funciones repetidas a los módulos compartidos, y hacer que los informes consuman tablas derivadas en lugar de volver a leer los archivos grandes. Las tasas espaciales existentes también requieren verificar unidad de conteo, denominadores territoriales, grupo etario, años de exposición y multiplicidad antes de reutilizarlas.

## Orden de trabajo recomendado

1. **Realizado:** inventario y auditoría del enlace; catálogo REM anual; corrección de la lectura de sexo/edad en los nuevos derivados; primer análisis de trayectorias con sensibilidad de definición.
2. **Siguiente prioridad:** confirmar con el productor GRD la estabilidad del identificador 2021–2024 y la posición diagnóstica; congelar la definición de TEA; generar resultados restringidos por oportunidad de observación y describir las exclusiones.
3. **Después:** completar denominadores de tamizaje REM y panel estable de establecimientos; extender GRD con modelos ajustados y estratos territoriales.
4. **Publicación:** sustituir gradualmente los informes históricos por informes que consuman la extracción validada. Los resultados actuales son exploratorios locales; no se ha publicado ni actualizado el sitio remoto.
