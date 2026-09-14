# Revisión de las nuevas fuentes para el manuscrito de autismo en Chile

**Corte de la revisión:** 4 de septiembre de 2026  
**Estado:** auditoría exploratoria y control de calidad. Los valores de esta nota deben regenerarse en el pipeline analítico final, con intervalos de confianza y tablas de procedencia, antes de enviarlos a una revista.

## Conclusión ejecutiva

Las fuentes nuevas sí pueden elevar sustancialmente el manuscrito, pero no conviene agregarlas como análisis independientes a un texto ya extenso. La reformulación más fuerte es un estudio nacional de vigilancia multisistema sobre **reconocimiento administrativo del autismo y demanda de servicios**, no sobre prevalencia ni incidencia.

Título de trabajo recomendado:

> **Administrative recognition of autism across health and education systems in Chile, 2019–2025: a national multisource surveillance study**

La contribución sería demostrar que el aumento aparece en sistemas independientes —hospitalario, ambulatorio, seguimiento y escolar— y que persiste en sensibilidades de cobertura, mientras se documentan simultáneamente expansión del reporte, cambios de taxonomía, mayor profundidad diagnóstica y presión de capacidad. La Ley 21.545 debe tratarse como contexto de política desde 2023, no como una intervención cuyo efecto causal pueda identificarse con estos datos.

No existe enlace individual entre REM, GRD, FONASA, encuestas o educación. Por eso el término correcto es **ruta administrativa agregada**; no “care cascade” individual.

## Estado de adquisición

El catálogo declarativo está en [`source_catalog.json`](source_catalog.json), el registro metodológico en [`source_registry.csv`](source_registry.csv) y los códigos REM verificados en [`rem_pathway_codes.csv`](rem_pathway_codes.csv).

La continuación de descarga del 4 de septiembre de 2026 incorporó **45 archivos
nuevos, 13.065.742.879 bytes (13,07 GB)**: 28 microdatos JUNAEB, la base CASEN,
ocho complementos CASEN y ocho ZIP FONASA. Todos pasaron sus controles de tamaño
y SHA-256; JUNAEB además coincide con el MD5 oficial y los ZIP FONASA pasaron
la comprobación CRC completa. No quedaron archivos parciales. El manifiesto
del proyecto registra ahora 143 artefactos adquiridos.

| Bloque | Estado local | Ubicación o mecanismo |
|---|---|---|
| GRD 2019–2024 | Canónicos existentes, validados | `/Volumes/Datos/Asesorias_Data/GRD` |
| REM Serie A 2009–2026 | Canónicos existentes; 2026 es año abierto | `/Volumes/Datos/Asesorias_Data/REM/SerieA` |
| REM Serie P 2019–2025 | Extraída y validada desde los ZIP oficiales; 7 CSV + 7 diccionarios | `/Volumes/Datos/Asesorias_Data/REM/SerieP` |
| Egresos DEIS 2001–2024 | Canónicos existentes | `/Volumes/Datos/Asesorias_Data/DEIS/Egresos` |
| REM-20 y establecimientos | Descargados con diccionarios | `/Volumes/Datos/Asesorias_Data/Autism/DEIS` |
| FONASA agregado 2018–2025 y APS 2019–2025 | Descargados | `/Volumes/Datos/Asesorias_Data/FONASA` |
| FONASA innominado 2018–2025 | Ocho ZIP oficiales descargados y verificados | `/Volumes/Datos/Asesorias_Data/FONASA/microdata/sources` |
| ISAPRE comunal 2019–2025 | Descargado | `/Volumes/Datos/Asesorias_Data/Autism/Cobertura/ISAPRE` |
| INE base 2017, Censo 2024 y base 2024 nacional | Descargados | `/Volumes/Datos/Asesorias_Data/Autism/Poblacion/INE` |
| ENDIDE 2022 y ENCAVI 2023–2024 | Microdatos y documentación descargados | `/Volumes/Datos/Asesorias_Data/Autism/Encuestas` |
| CASEN 2024 | Base Stata principal, complemento territorial y siete documentos/libros descargados | `/Volumes/Datos/Asesorias_Data/Autism/Encuestas/CASEN_2024` |
| MINEDUC PIE/SINACES | Tres informes descargados | `/Volumes/Datos/Asesorias_Data/Autism/Educacion/MINEDUC` |
| JUNAEB EVE 2019–2025 | 28 microdatos CSV, cuestionarios y diccionarios descargados | `/Volumes/Datos/Asesorias_Data/Autism/Educacion/JUNAEB/EVE` |

Los 28 microdatos EVE-JUNAEB suman 9.625.722.727 bytes (9,63 GB) y quedaron
descargados el 4 de septiembre de 2026, con cuatro niveles escolares por año.
El descargador verifica el MD5 publicado por el bucket oficial y registra
SHA-256 local; conserva los archivos completos en ejecuciones posteriores.
La opción `--include-large` permite adquirir la colección en otra instalación.
Los diccionarios oficiales solo existen en el bucket para 2019, 2021, 2024 y
2025; sí hay cuestionarios para todos los años 2019–2025.

## Qué mide cada fuente

| Fuente | Unidad | Uso defendible | No interpretar como |
|---|---|---|---|
| A03 | tamizaje o resultado agregado por establecimiento/mes | detección y referencia reportadas | niños únicos o positividad poblacional continua |
| A27 | intervención por establecimiento/mes | apoyo al tamizaje y referencia asistida | personas referidas únicas |
| A05 | ingreso/egreso reportado a programa de salud mental | acceso ambulatorio registrado | incidencia, continuidad individual o retención |
| P2/P6 | stock semestral bajo control | seguimiento registrado en junio/diciembre | flujo anual; nunca sumar ambos semestres |
| A28 | ingreso a rehabilitación por condición | acceso a rehabilitación reportado | trayectoria individual desde A03/A05 |
| GRD | episodio financiado/codificado | uso hospitalario con F84 documentado | todas las hospitalizaciones del país o prevalencia |
| REM-20 | establecimiento × área funcional × mes | actividad/capacidad y panel continuo | población cubierta o personas únicas |
| FONASA/APS/ISAPRE | stock administrativo de diciembre | cobertura/denominador compatible según unidad | una geografía residencial homogénea |
| INE | población territorial | denominador poblacional | usuarios de un prestador específico |
| ENDIDE/ENCAVI | persona encuestada | benchmark poblacional con diseño complejo | validación individual de códigos administrativos |
| PIE/JUNAEB | registro o reporte escolar | reconocimiento y demanda escolar | prevalencia nacional de autismo |

## Hallazgos REM verificados

### Reglas de extracción

- Serie A es un flujo mensual. Para A03 el total nacional se obtuvo como suma de meses de `COL01 + COL02`; para A05, A27 y A28 se sumó `COL01`.
- Serie P es un stock semestral. El análisis primario debe usar diciembre (`MES=12`) y `COL01`; junio es sensibilidad. No sumar junio y diciembre.
- Los códigos y períodos exactos están en [`rem_pathway_codes.csv`](rem_pathway_codes.csv). Deben volver a comprobarse contra el diccionario anual en cada ejecución.
- Diciembre de 2020 y, especialmente, junio de 2020 muestran interrupciones de reporte asociadas a la pandemia.

### A03: el tamizaje no es una sola serie continua

| Año | Indicador | Total nacional preliminar |
|---:|---|---:|
| 2019 | M-CHAT realizado en niños con alteración lenguaje/social (`03500406`) | 2.613 |
| 2019 | M-CHAT alterado dentro de ese grupo (`03500407`) | 1.640 |
| 2020 | M-CHAT realizado / alterado, definición antigua | 816 / 288 |
| 2021 | M-CHAT realizado / alterado, definición antigua | 1.833 / 879 |
| 2022 | M-CHAT realizado / alterado, definición antigua | 3.455 / 1.535 |
| 2023 | bajo / medio / alto riesgo, primera parte | 14.083 / 3.642 / 1.907 |
| 2023 | alto riesgo referido; segunda parte no requiere / requiere referencia | 1.152; 817 / 1.136 |
| 2024 | bajo / medio / alto riesgo, primera parte | 18.142 / 4.698 / 2.234 |
| 2024 | alto riesgo referido; segunda parte no requiere / requiere referencia | 1.741; 2.341 / 2.283 |
| 2025 | bajo; medio sin / con referencia; alto con referencia | 12.971; 1.637 / 2.500; 2.181 |
| 2025 | sospecha 30–59 meses sin / con referencia | 5.140 / 5.883 |

Hay quiebres de definición en 2023 y 2025. Los códigos 2019–2022 se aplican a un subgrupo seleccionado por alteración de lenguaje/área social: su cociente no es positividad M-CHAT de la población examinada. En 2025 cambian tanto los códigos como la separación por motivo, riesgo y referencia. La figura debe usar paneles por era, no una línea ininterrumpida.

### A27, A05 y A28

| Serie | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| A05 ingresos por autismo (`05990022`) | 2.085 | 4.640 | 8.049 | 11.842 | 13.155 |
| A05 egresos por autismo (`05990027`) | 494 | 831 | 1.814 | 3.315 | 3.367 |
| A27 consejería M-CHAT-R/F (`29101566`) | — | — | 2.380 | 3.874 | 3.026 |
| A27 referencia asistida M-CHAT-R/F (`29101574`) | — | — | 672 | 1.068 | 878 |
| A28 rehabilitación primaria TEA (`29101629`) | — | — | 3.962 | 7.033 | 15.859 |
| A28 rehabilitación hospitalaria TEA (`29101651`) | — | — | 731 | 1.045 | 1.740 |

Antes de 2021 A05 solo identifica “trastornos generalizados del desarrollo” (`06902600` para ingresos y `05225000` para egresos), por lo que no debe empalmarse silenciosamente con autismo estricto. A27 solo tiene códigos específicos de tamizaje TEA desde 2023; los códigos anteriores de “referencia asistida” corresponden a alcohol y drogas. A27 cuenta intervenciones, no niños únicos.

### P2/P6: población bajo control en diciembre

| Año | P2 TEA NANEAS | P6 APS, autismo/TGD según era | P6 especialidad, autismo/TGD según era | Establecimientos P2 que reportan diciembre |
|---:|---:|---:|---:|---:|
| 2019 | 1.854 | 5.520 (TGD amplio) | 6.624 (TGD amplio) | 460 |
| 2020 | 1.919 | 5.185 (TGD amplio) | 6.905 (TGD amplio) | 400 |
| 2021 | 3.853 | 2.257 (autismo) | 3.562 (autismo) | 640 |
| 2022 | 7.923 | 5.042 | 4.684 | 897 |
| 2023 | 13.190 | 9.717 | 7.982 | 1.012 |
| 2024 | 21.737 | 15.934 | 8.835 | 1.218 |
| 2025 | 29.974 | 21.843 | 12.645 | 1.325 |

El total NANEAS bajo control (`P2501878`) aparece desde diciembre de 2023: 59.907 en 2023, 77.081 en 2024 y 100.789 en 2025. No existe como denominador comparable para 2019–2022.

La expansión del número de establecimientos que reportan P2 es parte del resultado y parte del sesgo de observación. En junio de 2020 P2 registra solo 172 personas y 28 establecimientos, evidencia suficiente para no promediar semestres ni interpretar la caída como epidemiológica.

## Hospitalización GRD: controles que cambian la interpretación

### Cobertura observada y tipo de atención

Los archivos no constituyen un panel fijo de 72 hospitales: se observan 65 hospitales en 2019–2022, 68 en 2023 y 72 en 2024. El panel fijo de 65 debe ser una sensibilidad obligatoria.

| Año | Registros GRD | Episodios con F84 en cualquier diagnóstico | Personas únicas dentro del año | F84 en panel fijo de 65 |
|---:|---:|---:|---:|---:|
| 2019 | 1.151.475 | 2.385 | 1.983 | 2.385 |
| 2020 | 781.912 | 1.633 | 1.338 | 1.633 |
| 2021 | 816.909 | 2.399 | 1.979 | 2.399 |
| 2022 | 932.839 | 3.912 | 3.265 | 3.912 |
| 2023 | 1.039.587 | 6.473 | 5.268 | 6.421 |
| 2024 | 1.085.813 | 8.818 | 7.214 | 8.557 |

La tendencia persiste al restringir a hospitalización estricta: 1.960, 1.550, 2.217, 3.561, 5.797 y 7.500 episodios de 2019 a 2024. La cirugía mayor ambulatoria aporta 168, 83, 182, 351, 631 y 1.113 episodios, respectivamente. En 2019 también existen categorías de hospitalización diurna y de urgencia que no aparecen igual desde 2020.

### Posición y profundidad diagnóstica

F84 como diagnóstico principal representa solo 241, 163, 189, 304, 366 y 401 episodios por año; la gran mayoría está en diagnósticos secundarios. En 2024, 8.417 de 8.818 episodios (95,5%) tenían F84 únicamente en posición secundaria. El outcome debe llamarse **episodio GRD con F84 documentado**, no “hospitalización por autismo”.

La profundidad de codificación del conjunto GRD aumenta de 4,39 diagnósticos por episodio en 2019 a 5,78 en 2024; entre episodios F84 aumenta de 5,00 a 6,04. Deben incluirse:

1. F84 principal únicamente;
2. F84 en cualquier posición;
3. ajuste o estratificación por número de diagnósticos codificados;
4. hospitalización estricta frente a toda modalidad GRD;
5. panel anual observado frente al panel fijo de 65 hospitales.

El identificador encriptado cambia entre 2020 y 2021: el solapamiento de IDs F84 es cero y también cambia su longitud. No es defendible deduplicar “personas únicas 2019–2024” a través de ese quiebre sin confirmación formal de FONASA. Las cifras anuales sí pueden usarse como deduplicación dentro de cada año.

## Denominadores y cobertura

### FONASA e inscritos APS

| Año | Beneficiarios FONASA, diciembre | Inscritos APS, diciembre | Centros APS |
|---:|---:|---:|---:|
| 2019 | 14.841.577 | 13.777.051 | 1.890 |
| 2020 | 15.142.528 | 13.885.509 | 1.956 |
| 2021 | 15.233.814 | 14.100.841 | 1.984 |
| 2022 | 15.613.584 | 14.522.464 | 2.026 |
| 2023 | 16.229.898 | 15.051.673 | 2.057 |
| 2024 | 16.752.189 | 15.353.689 | 2.078 |
| 2025 | 17.132.611 | 15.791.862 | 2.091 |

Los agregados FONASA cambian de esquema en 2021, 2023, 2024 y 2025. En 2018–2020 hay filas repetidas incluso usando todas las dimensiones visibles; son fragmentos aditivos de una dimensión no expuesta. Eliminarlas con `drop_duplicates()` reduce incorrectamente los totales nacionales. Se deben conservar y sumar los conteos.

La geografía FONASA mezcla comuna del centro de inscripción APS para personas inscritas y domicilio para no inscritas; desde 2023 desaparece la variable que permite separar esa mezcla. APS es siempre comuna del establecimiento. No usar ninguna como residencia homogénea.

Un panel continuo de 1.871 códigos APS retiene 99,87% del total de 2019 y 97,54% de 2025. Dos códigos requieren tratamiento especial por cambio geográfico: `200261` parece reutilizado y `200474` parece corregido. Para 2019–2022, APS restringido a tramos A–D reproduce con diferencia menor de 0,2% el total FONASA marcado como inscrito; los tramos `X` y faltantes no deben mezclarse sin definición.

### ISAPRE, INE, REM-20 y catastro

- Beneficiarios ISAPRE en diciembre: 3.431.126 (2019), 3.339.226, 3.330.254, 3.151.885, 2.788.257, 2.630.026 y 2.517.305 (2025). En 2019–2020 hay una hoja separada para nonatos/sin clasificar; desde 2021 el total es cotizantes + cargas. Nunca sumar hojas por sexo y “Total”, porque son vistas duplicadas.
- Las proyecciones comunales INE base Censo 2017 cubren 346 comunas, 2002–2035, sin llaves repetidas. Población nacional: 19.107.216 (2019) a 20.206.953 (2025). El grupo `Edad=80` es abierto 80+.
- La llave INE comunal usa cuatro dígitos y DEIS cinco con cero inicial. También hay que armonizar `Aisén/Aysén`, `Coihaique/Coyhaique` y `Cabo de Hornos (Ex-Navarino)/Cabo de Hornos`.
- FONASA + ISAPRE equivalen a 95,63% de la proyección INE en 2019 y 97,24% en 2025. La diferencia incluye otros regímenes, personas no cubiertas y fechas de referencia distintas; no es una tasa de no aseguramiento.
- REM-20 contiene 167.405 filas, 2014–julio de 2026, 208 establecimientos y 29 áreas funcionales. Un panel de 188 establecimientos con 12 meses en cada año 2019–2025 conserva 99,76% de los egresos de 2019 y 98,16% en 2025. Es una buena sensibilidad de actividad/capacidad, no un denominador poblacional.
- El catastro DEIS descargable tiene 5.717 establecimientos y enlaza todos los códigos REM-20, pero es un archivo vigente mutable, contiene cerrados y carece de muchas fechas históricas. No permite reconstruir por sí solo un “catastro anual”; el panel histórico debe derivarse del reporte observado en REM/GRD.

## Validación poblacional externa

Resultados preliminares que requieren estimación final con diseño complejo e intervalos de confianza:

| Encuesta | Dominio | Casos no ponderados | Estimación ponderada preliminar |
|---|---|---:|---:|
| ENDIDE 2022 | adultos | 72 | 0,29% |
| ENDIDE 2022 | niños, niñas y adolescentes | 163 | 2,86% |
| ENDIDE 2022 | NNA con confirmación profesional | 139 | no usar sin estimación de dominio y CI |
| ENCAVI 2023–2024 | personas de 15 años o más | 80 | 0,71% (aprox. 114.817 personas) |

Estas encuestas son benchmarks de orden de magnitud. No validan registros uno a uno y no deben desagregarse a comuna. ENDIDE y ENCAVI deben analizarse con ponderadores, estratos y conglomerados, declarando el denominador y el wording exacto de cada pregunta.

## Triangulación educativa

### PIE/MINEDUC

La serie estricta TEA de Apuntes 60 es 11.877, 13.613, 18.801, 28.845 y 47.551 estudiantes en 2019–2023. La categoría histórica TEA-Asperger suma 9.135, 9.977, 12.081, 14.095 y 16.091. Una sensibilidad armonizada `TEA + TEA-Asperger` produce 21.012, 23.590, 30.882, 42.940 y 63.642.

El informe SINACES publicado en 2026 prolonga la serie armonizada PIE a 86.475 en 2024 y 106.786 en 2025; además informa 2.505 y 2.626 estudiantes en escuelas especiales, respectivamente. Para 2022 el informe escribe 42.945, aunque su total 45.014 menos 2.074 en escuelas especiales da 42.940, coincidente con Apuntes 60. El pipeline debe registrar esta discrepancia de cinco casos y adoptar una regla explícita.

PIE refleja registro para subvención, cupos, cobertura y reconocimiento escolar. MINEDUC advierte que no incluye a todo el estudiantado autista. El aumento de postulaciones PIE y de la vía excepcional es evidencia de presión sobre capacidad, no prevalencia.

### JUNAEB EVE

Resultados preliminares ponderados en cohortes escolares seleccionadas:

| Año | Nivel | TEA no ponderado | Proporción ponderada |
|---:|---|---:|---:|
| 2024 | parvularia | 17.641 | 6,74% |
| 2024 | 1º básico | 10.245 | 6,60% |
| 2024 | 5º básico | 7.468 | 4,49% |
| 2024 | 1º medio | variable vacía | no estimable |
| 2025 | parvularia | 18.785 | 7,69% |
| 2025 | 1º básico | 12.536 | 8,35% |
| 2025 | 5º básico | 9.887 | 5,71% |
| 2025 | 1º medio | 9.164 | 5,03% |

En 2024–2025 la identificación usa diagnóstico médico prolongado y la categoría TEA, con ponderador `EXP`. Son reportes de cuidadores en cohortes escolares específicas, no prevalencia nacional ni una serie directamente comparable con PIE.

## Diseño recomendado para *The Lancet Regional Health – Americas*

### Pregunta principal

¿Cómo cambió entre 2019 y 2025 el reconocimiento administrativo del autismo y la demanda registrada de servicios en los sistemas público de salud y educación de Chile, y cuánto del cambio es robusto a variaciones de cobertura, intensidad de codificación y definiciones?

### Estimandos y jerarquía

1. **Primario hospitalario:** episodios GRD con F84 documentado por 100.000 episodios GRD, con panel fijo de 65, hospitalización estricta y profundidad diagnóstica como sensibilidades.
2. **Primario ambulatorio:** ingresos A05 por autismo desde 2021, expresados como conteo, tasa cuando pueda alinearse el denominador por edad/sexo y número de establecimientos que reportan.
3. **Seguimiento:** stocks de diciembre P2/P6 por autismo, con junio como sensibilidad y reporte explícito de establecimientos.
4. **Ruta de detección:** A03 por eras de definición y A27 desde 2023; presentar componentes, no un porcentaje encadenado entre fuentes.
5. **Triangulación externa:** PIE armonizado, JUNAEB 2024–2025 y benchmarks ENDIDE/ENCAVI; no combinar sus porcentajes en un metaanálisis.

FONASA, APS, ISAPRE e INE deben responder preguntas distintas: cobertura pública, inscripción operativa, cobertura privada y población territorial. REM-20 aporta actividad/capacidad. No elegir el denominador que produzca la asociación más favorable.

### Figuras centrales

1. Arquitectura de fuentes, unidades y ausencia de enlace individual.
2. Tendencia hospitalaria: F84 cualquier posición/principal, panel observado/fijo y profundidad de codificación.
3. Ruta REM en paneles separados por quiebre: tamizaje/referencia, ingreso, stock bajo control y rehabilitación.
4. Triangulación educativa y benchmarks poblacionales, usando escalas y denominadores claramente separados.

Mapas comunales extensos, todas las comorbilidades, trayectorias longitudinales GRD y tablas muy granulares deberían ir al suplemento o a un segundo artículo. La presente base permite dos productos coherentes: un artículo multisistema de vigilancia/política para la revista regional y otro hospitalario detallado sobre uso, codificación y trayectorias.

### Afirmaciones que deben evitarse

- “La prevalencia/incidencia de autismo aumentó X%”.
- “La Ley 21.545 causó el aumento”.
- “X niños avanzaron de tamizaje a ingreso/seguimiento”.
- “72 hospitales durante todo el período”.
- “Hospitalizaciones por autismo” cuando F84 es secundario.
- “Personas únicas 2019–2024” atravesando el quiebre del identificador GRD.
- Una tasa comunal con numerador de lugar de atención y denominador de residencia sin análisis de compatibilidad.

### Lenguaje defendible

- “aumento del reconocimiento/registro administrativo”;
- “episodios con F84 documentado”;
- “indicadores agregados de detección, referencia, ingreso y seguimiento”;
- “convergencia descriptiva entre sistemas independientes”;
- “hallazgos compatibles con mayor identificación, expansión del reporte y demanda de servicios”;
- “la contribución relativa de cambios epidemiológicos, de acceso y de codificación no puede separarse con estos datos”.

## Reproducibilidad mínima

```sh
# Verificar datos ya disponibles
python scripts/download_hospital_data.py --audit
python scripts/download_new_chile_data.py --audit

# Conservar los ZIP REM oficiales que contienen todas las series
python scripts/download_hospital_data.py \
  --dataset deis_rem --retain-sources --include-large --years 2019 2025

# Extraer P2/P6 y diccionarios a nombres canónicos
python scripts/downloads/extract_rem_series_p.py --years 2019-2025

# Descargar o actualizar las fuentes de contexto pequeñas
python scripts/download_new_chile_data.py

# Microdatos JUNAEB, solo cuando haya espacio y sean necesarios
python scripts/download_new_chile_data.py \
  --dataset junaeb_eve_microdata --include-large --years 2019 2025
```

Cada archivo descargado queda registrado con URL original/resuelta, fecha UTC, tamaño y SHA-256. La extracción de Serie P tiene un manifiesto separado con SHA-256 de sus 14 artefactos.

## Fuentes oficiales de acceso

- [Datos abiertos REM y egresos DEIS](https://deis.minsal.cl/#datosabiertos)
- [Tablero GRD FONASA](https://public.tableau.com/views/PropuestaTableroGRD/PropuestaTableroGRD?:showVizHome=no)
- [Tablero de beneficiarios FONASA](https://public.tableau.com/views/Beneficiarios_16704273822880/Reporte?:showVizHome=no)
- [Tablero de inscritos APS](https://public.tableau.com/views/ReporteInscritosCentrosAPS/ReporteAPS?:showVizHome=no)
- [ENDIDE 2022](https://observatorio.ministeriodesarrollosocial.gob.cl/endide-2022)
- [ENCAVI 2023–2024](https://datos.gob.cl/dataset/encavi-2023-24)
- [Proyecciones INE](https://www.ine.gob.cl/estadisticas-por-tema/demografia-y-poblacion/estimaciones-y-proyecciones-de-poblacion)
- [Biblioteca de datos JUNAEB](https://bibliotecadatos.sead.junaeb.cl/)
