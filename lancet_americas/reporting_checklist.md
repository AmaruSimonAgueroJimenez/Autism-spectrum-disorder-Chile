# Lista de comprobación de reporte — STROBE, RECORD y requisitos de la revista

Estado: completada por el módulo `pipeline/10_manuscript.py`, revisada a mano sobre `manuscript/manuscript_<variante>_en.docx` y actualizada el **2026-09-08** sobre la compilación del **2026-09-08, 18:19:38 → 18:34:01** (863 s), que es la que hay hoy en `manuscript/` y la que recoge los cuatro arreglos de la fase 4k —la glosa única del panel fijo de 65 hospitales, el par de apellidos «Getis–Ord» y «Gauss–Newton» con raya corta, y el anglicismo «crosswalk» fuera de la prosa española—. «Cumplido» = el ítem está cubierto en la sección indicada; «pendiente (equipo autor)» = requiere una decisión o dato que el pipeline no puede aportar. **AVISO DE ESTADO: ningún punto abierto bloquea el envío.** El único que las dos lecturas independientes dejaban abierto como defecto —el corpus imprimía **dos definiciones del mismo panel fijo de 65 hospitales**— está **cerrado y en el papel**: la glosa se escribe una sola vez en `common.fixed_panel_gloss` y la piden de ahí los siete módulos que la imprimen, de modo que medido sobre estos doce documentos hay **0 enunciados de pertenencia con la ventana 2019–2022** (eran 31 por manuscrito, 30 por apéndice y 1 por artículo) y **48 / 46 / 2** con la ventana 2019–2024. Lo que queda son **trece puntos, y ninguno se lee como defecto**: convenciones declaradas, decisiones ya tomadas que sólo hay que ratificar, deuda de herramienta o trabajo de la pasada de maqueta de la revista, listados uno a uno en la **sección 6 de `memo_es.md`**. **No queda ningún arreglo viviendo sólo en `outputs/`**: los doce documentos son posteriores a la última fuente que leen, y **las 5.925 páginas de los doce PDF llevan folio, ninguna equivocada**.

**Estructura del archivo del manuscrito tras el módulo 17.** El artículo conserva su texto y su orden (Summary, Research in context, Introduction, Methods concisos, Results, Discussion, Conclusion, declaraciones y References) con un único cambio acordado: la lámina del módulo 08d es la **Figura 1** —esquema conceptual de qué se hizo con cada base de datos: seis carriles, uno por familia de fuentes, leídos base de datos → pasos → lo que entrega, con la unidad de la fila en un distintivo (cuadrado «registro», círculo «persona», hexágono «comuna»), las cifras solas sobre las flechas y la regla de no enlace enunciada una vez— y el inventario de fuentes (`T1_sources`) pasó al material suplementario como **Tabla S1**, de modo que el artículo lleva **Figuras 1–5** y **Tablas 1–7**. Después de las Referencias, con salto de página y en el mismo archivo, va el **Material suplementario**: nota e índice, métodos suplementarios S1–S5, la **metodología extendida** con las **33 ecuaciones** numeradas y citadas, las **54 láminas suplementarias** agrupadas por tema y las **125 tablas suplementarias**. Los apéndices separados `supplement_<variante>_<idioma>.docx` contienen el mismo material, construido desde el mismo registro de numeración: «Tabla S8» designa el mismo ítem en ambos documentos y en ambos idiomas. Desde la fase 4c hay además un tercer archivo por variante e idioma, `manuscript/article_<variante>_<idioma>.docx`, que contiene **exactamente el artículo** hasta las Referencias y nada más: es el que se envía. Las **59 láminas** (5 del artículo y 54 suplementarias) se dibujan a **180 × 245 mm en vertical, 1:1, 600 ppp**, en rejilla de 3 × 2 con un máximo de seis paneles, letras de panel en minúscula (a)–(f) y nada por debajo de 6 pt, y **cada una ocupa una página propia** del documento, compartida con la frase que la presenta y con su leyenda. Desde la fase 4d la composición de cada lámina la mide `common.check_layout` sobre el renderizador real —nueve familias: texto sobre texto, texto fuera del lienzo, título de eje sobre sus marcas, leyenda o nota sobre los datos, rótulo de valor sobre su marcador o su barra de error, rótulo de valor cuyo recuadro tapa su propia barra, títulos de dos paneles vecinos sin hueco, marcas numéricas repetidas y recuento de paneles— y los nueve módulos de lámina la ejecutan con `LANCET_PLATE_CHECK`: **cero defectos** en las 244 construcciones que el lector independiente volvió a comprobar con el verificador armado, 242 de ellas idénticas byte a byte a las publicadas, todas de 180,0 × 245,0 mm exactos a 600 ppp y sin tinta en el borde. La región de láminas del suplemento son **58 páginas seguidas en inglés y 60 en español** —las páginas de más llevan la cola rotulada de una leyenda, 938–1.974 caracteres cada una— y **ninguna página de los doce documentos baja de 300 caracteres** (remedido el 2026-09-08 sobre los doce PDF de la compilación vigente, la de las 18:19–18:34: mínimo **315** contando palabras unidas por un espacio y líneas por un salto, descontado el folio, en la portada de `supplement_sin_rett_es`; contando sólo caracteres no blancos esa misma portada baja a **272** y son tres las portadas de apéndice por debajo de 300, bloques de título completos y no páginas vacías). Desde la fase 4e la leyenda de lámina no baja de **7,0 pt** en los cuatro archivos sólo-artículo ni de **6,5 pt** en los ocho largos, y la leyenda de la **Figura 1 cabe entera bajo su lámina** en los ocho sitios donde se imprime (12 líneas en inglés, 13 en español).

## STROBE (estudios transversales y de cohorte con datos rutinarios)

| Ítem | Recomendación | Dónde | Estado |
|---|---|---|---|
| 1 Título y resumen | diseño en el título; resumen informativo | Título («national multisource surveillance study»; «administrative recognition» identifica el tipo de dato); Summary (Background, Methods, Findings, Interpretation, Funding) | cumplido |
| 2 Antecedentes | contexto y justificación | Introduction | cumplido |
| 3 Objetivos | objetivos e hipótesis preespecificados | Introduction (pregunta principal, último párrafo); Methods › Study design and setting; `analysis_plan.md`; Material suplementario › Metodología extendida M1 | cumplido |
| 4 Diseño | elementos clave del diseño | Methods › Study design and setting; Metodología extendida M1 | cumplido |
| 5 Contexto | lugares, fechas, períodos de reclutamiento/seguimiento | Methods › Study design and setting; Methods › Data sources and units of observation (Chile, red pública, 2019–2024 GRD/DEIS y 2019–2025 REM/educación) | cumplido |
| 6 Participantes | criterios de elegibilidad, fuentes, métodos de selección | Methods › Data sources and units of observation; Methods › Case definitions and definition variants; **Figura 1** (carril por carril: qué es una fila —registro, persona o comuna—, n a la entrada, n tras la selección de autismo y las exclusiones en rojo con su motivo) y **Tabla S1** (unidad de observación por fuente; censo de registros, sin reclutamiento individual); Tabla S2 (los recuentos de la Figura 1, con su unidad y su origen) | cumplido |
| 7 Variables | resultados, exposiciones, covariables, criterios diagnósticos | Methods › Case definitions and definition variants; Methods › Denominators and coverage layers; Suplemento S1; Metodología extendida M2–M3 y Tablas S4–S6; `variables_dictionary.md`; Tabla S124 (diccionario de datos de las tablas tidy) | cumplido |
| 8 Fuentes/medición | fuente y método de medición por variable; comparabilidad | Methods › Data sources and units of observation; Tabla S1; Suplemento S1; Tablas S14–S15 (procedencia con SHA-256 y comprobaciones del manifiesto); Tabla S13 (quiebres de definición) | cumplido |
| 9 Sesgo | esfuerzos para abordar sesgos | Methods › Statistical analysis (panel fijo/observado, profundidad de codificación, eras de definición, panel estable REM, junio/diciembre); Metodología extendida M5 (rejilla de sensibilidad, Tabla S8); Discussion (limitaciones) | cumplido |
| 10 Tamaño del estudio | cómo se llegó al tamaño | Methods › Study design and setting (censo de todos los registros públicos; sin muestreo); Results › Sources and coverage; Figura 1 y Tabla S2 (registros leídos por fuente) | cumplido |
| 11 Variables cuantitativas | manejo y agrupaciones | Methods › Statistical analysis (grupos de edad, estratos de profundidad diagnóstica, eras); Suplemento S2; Metodología extendida M3–M4 | cumplido |
| 12 Métodos estadísticos | todos los métodos, subgrupos, missing, sensibilidad | Methods › Statistical analysis; Methods › Reproducibility controls; Suplemento S2 (modelos), S3 (encuestas); **Metodología extendida M4: los 26 estimadores con su fórmula (ecuaciones 1–33), supuestos, implementación, script y archivo de salida** | cumplido |
| 13 Participantes | números en cada etapa; diagrama de flujo | **Figura 1**: por carril, la unidad de la fila (registro, persona o comuna), el n a la entrada, el n tras la selección de autismo y las exclusiones con su n; no hay flujo de individuos porque no hay reclutamiento ni enlace por persona, y la lámina lo declara en la banda roja de trazos que separa los carriles. **Tabla S2** lleva los recuentos que la sustentan; Results › Sources and coverage; Tabla S1 | cumplido |
| 14 Descriptivos | características, missing por variable | Results (todas las subsecciones); Tablas 1–3; Methods › Data sources (missing ≠ cero ≠ ausencia de reporte; establecimientos reportantes en cada tabla REM); Metodología extendida M5 y Tabla S9 (estados del dato) | cumplido |
| 15 Resultados | números de eventos o medidas resumen | Results › Hospital core; Results › Aggregate administrative pathway; Results › Educational triangulation; Tablas 1, 2 y 5; Tablas S104–S125 (series completas) | cumplido |
| 16 Resultados principales | estimaciones ajustadas e IC; categorías | Results › Hospital core (tasas con IC exactos, CPA con IC 95 %); Results › Convergence across systems and sensitivity of the trends; Tabla 6; Tabla S48 (todas las especificaciones) | cumplido |
| 17 Otros análisis | subgrupos, sensibilidad | Results › Convergence…; **Figuras S1–S54 y Tablas S1–S125** (episodios hospitalarios en detalle, ruta REM por era, denominadores, encuestas y educación, razón por sexo entre fuentes, diagnósticos de los modelos y análisis espacial y de correlación territorial) | cumplido |
| 18 Resultados clave | resumen en relación con objetivos | Discussion (primer párrafo) | cumplido |
| 19 Limitaciones | sesgo/imprecisión, dirección y magnitud | Discussion (pandemia, taxonomía, cobertura, geografía, profundidad de codificación, falta de enlace, sesgo de acceso); Metodología extendida M7 (limitaciones del método) | cumplido |
| 20 Interpretación | cautelosa, multiplicidad, evidencia similar | Discussion (reconocimiento ≠ demanda ≠ epidemiología; comparación con registros internacionales; no separabilidad); Conclusion | cumplido |
| 21 Generalizabilidad | validez externa | Discussion (sistemas universales/segmentados de América Latina; red pública, no ISAPRE) | cumplido |
| 22 Financiamiento | fuente y rol | Funding; Methods › Role of the funding source | cumplido en estructura; contenido («None») pendiente (equipo autor) |

## RECORD (extensión para datos rutinarios)

| Ítem | Recomendación | Dónde | Estado |
|---|---|---|---|
| 1.1–1.3 | tipo de datos en título/resumen; bases y período; enlace entre bases | Título («administrative recognition», «multisource»); Summary › Methods («unlinked routine data»); Methods › Data sources and units of observation | cumplido |
| 6.1 | métodos de selección con códigos/algoritmos | Methods › Case definitions and definition variants; Suplemento S1; Metodología extendida M2 y Tablas S4–S5 (definiciones de caso y los 57 códigos REM); Tabla S16 (diccionario REM verificado por año); `config.py` | cumplido |
| 6.2 | validación de los códigos/algoritmos | Discussion (sin validación clínica; ENDIDE/ENCAVI como referencias de autismo reportado, no validación); Results › Population benchmarks | cumplido (declarado como limitación) |
| 6.3 | enlace de bases: diagrama y métodos | Methods › Data sources and units of observation (sin enlace a nivel de persona); **Figura 1** (la banda roja de trazos que separa los seis carriles declara, una sola vez, la ausencia de enlace individual entre sistemas y lleva la prueba de la corrida: 0 identificadores F84 de 2021 aparecen en 2020, frente a 168 de 2020 en 2019, porque el formato del identificador cambia entre 2020 y 2021); Tabla S1 (columna «Person-level linkage»); Tabla S3 (fuentes, unidad e imposibilidad de enlace) | cumplido |
| 7.1 | lista completa de códigos y algoritmos | Suplemento S1; Metodología extendida M2; Tablas S4, S5 y S16; Tabla S13 (quiebres de definición); `config.py` | cumplido |
| 12.1 | calidad de datos y limpieza | Methods › Reproducibility controls; Tabla 7 (controles compactos); Suplemento S5 y Tabla S49 (controles completos); Tabla S12 (controles por módulo); Tabla S19 (auditoría de identificadores GRD); `decision_log.md` | cumplido |
| 12.2 | enlace: calidad y evaluación | n/a (no hay enlace por persona; declarado en Methods › Data sources, en la Figura 1 y en la Tabla S1) | n/a |
| 12.3 | tratamiento de missing | Methods › Data sources and units of observation (missing ≠ cero ≠ ausencia de fila; 2020 como disrupción de reporte, sin interpolación); Tabla 2 (establecimientos reportantes); Tabla S9 (estados del dato) | cumplido |
| 13.1 | selección de la población: diagrama detallado | **Figura 1** y **Tabla S2**; Tabla S1; Tabla S18 (panel de hospitales); Tabla S17 (establecimientos reportantes por módulo y año) | cumplido |
| 19.1 | limitaciones del uso de datos creados con otros fines | Discussion; Metodología extendida M7 | cumplido |
| 22.1 | acceso a datos, código y protocolo | Data sharing statement; Tabla S14 (procedencia); `analysis_plan.md` como protocolo; Metodología extendida M6 (software, versiones, semillas y mapa del pipeline, Tablas S10–S11) | cumplido en estructura; URL/DOI del repositorio pendiente (equipo autor) |

## Requisitos de la revista (ver journal_guidelines.md)

> **A qué versión se aplican estos límites.** Los límites de extensión de la revista (Resumen ≤ 250 palabras;
> texto núcleo Introduction–Conclusion 3500–5000 palabras; ≤ 30 referencias en el núcleo) se aplican al **envío en
> inglés**, que es la versión que se envía y la única que se mide contra ellos. La versión en **español es la
> traducción de trabajo del equipo**: el español se expande frente al inglés (razón observada de palabras del
> cuerpo ≈ 1,16), de modo que su Resumen y su texto núcleo quedan por encima de esos umbrales. Eso no es un
> incumplimiento y **no se corrige recortando contenido**, porque ambas versiones deben llevar exactamente los
> mismos párrafos y las mismas cifras; el requisito aplicable al español es la **paridad con el inglés** (razón
> de palabras dentro de 0,90–1,30 y la misma lista de claves de cita). El paso 17 escribe una fila de control por
> idioma que nombra el límite que le corresponde (`article_summary_words_en` / `article_summary_words_es`,
> `article_core_words_en` / `article_core_words_es`, `article_core_words_parity_es_vs_en`), y la portada de cada
> documento lo declara en su propia nota.

| Requisito | Dónde | Estado |
|---|---|---|
| 3500–5000 palabras, ≤ 30 referencias (**se aplica al inglés**) | Texto núcleo Introduction–Conclusion: **4.995 palabras** en el **inglés**, que es el envío, sin los 11 párrafos `[OPT]` (1.191 palabras) que esta versión conserva y lista en «Optional material index»; **28 referencias** en el núcleo (50 con opcionales). El **español**, traducción de trabajo, tiene **5.795 palabras** de núcleo (razón es/en 1,16) y no se mide contra este límite. Los recuentos se miden sobre `prose_*.article()`, no sobre el archivo completo, porque el material suplementario que sigue a las Referencias no cuenta para los límites | cumplido en el núcleo inglés; el español cumple la paridad exigida (0,90–1,30); recorte de los `[OPT]` pendiente (equipo autor) |
| Resumen de 5 párrafos ≤ 250 palabras (**se aplica al inglés**) | Summary: **249 palabras** en inglés, párrafos Background/Methods/Findings/Interpretation/Funding. El Resumen en **español** tiene **278 palabras** por la expansión del idioma y se comprueba por paridad de contenido, no contra el límite | cumplido en inglés; el español cumple la paridad exigida |
| Research in context sin referencias | Panel «Research in context», sin marcadores de cita (prueba `tests/test_prose_en.py`) | cumplido; cadenas de búsqueda exactas por confirmar (equipo autor) |
| Contributors con verificación de datos por > 1 autor | Contributors | pendiente (equipo autor): un solo autor; se requiere coautor que verifique los datos |
| Declaration of interests, Funding y rol, Data sharing, AI declaration | Declaration of interests; Funding y Methods › Role of the funding source; Data sharing statement; Declaration of the use of artificial intelligence | cumplido en estructura; formularios ICMJE, financiamiento, URL/DOI y versión de la herramienta de IA pendientes (equipo autor) |
| Número de figuras y tablas del artículo | **Figuras 1–5** (qué es una fila y qué se cuenta en cada fuente; completitud, cobertura, paneles y quiebres; núcleo GRD; ruta REM; triangulación) y **Tablas 1–7** (las antiguas 2–8 renumeradas). Ninguna cita está escrita a mano: el registro produce cada «Figure N»/«Table N» con `R.mfig()`/`R.mtab()` y una prueba comprueba que el orden de primera cita es 1, 2, 3, … (`tests/test_17_extended_material.py`) | cumplido; el equipo autor decidirá si alguna de las cinco láminas pasa al suplemento |
| Archivo de envío separado del material suplementario | `manuscript/article_<variante>_<idioma>.docx`: exactamente el artículo hasta las Referencias (5 láminas, 7 tablas, 50 referencias, 64–65 páginas), sin encabezado suplementario ni índice de material opcional; el apéndice va en `manuscript/supplement_<variante>_<idioma>.docx` | cumplido |
| SAGER: análisis por sexo | Results › Hospital core y Aggregate administrative pathway (tasas por sexo, razón H:M); Tablas 1 y 2; Figuras 3, S8, S12 y **S42 (razón hombre:mujer en todas las fuentes que informan sexo)**; Discussion | cumplido |
| Figuras 300 dpi, 107 mm, letras minúsculas, sin títulos internos | Las 59 láminas (Figuras 1–5 y S1–S54) se dibujan a **600 ppp** en un lienzo de **180 × 245 mm en vertical, a escala 1:1** (4251 × 5787 px), rejilla de 3 × 2, máximo seis paneles, cuerpo 8 pt / título de panel 9 pt / marcas y leyenda 7 pt y nada por debajo de 6 pt; **letras de panel en minúscula (a)–(f)** en la figura y en la leyenda, en los dos idiomas; cada lámina ocupa una página propia y se imprime a tamaño natural | resolución, letras minúsculas y composición **cumplidas** (`common.check_layout`: cero defectos en las 236 construcciones del estudio, y cero en las 244 que el lector independiente volvió a comprobar con el verificador armado); la FORMA de la letra de panel está **unificada** desde la fase 4e —«(a)…(f)» en las 59 láminas y en las 58 leyendas con paneles, medido: 0 mayúsculas y 0 letras sin paréntesis, vía `common.plate_panel_letter`— y las citas del texto que quedaban en mayúscula («Figure 3C», «Figure 5A», «Figure 5C», «Figure 5D–E», «Figure 5F») están corregidas con una prueba que las vigila. La COLOCACIÓN de la letra, que la fase 4e dejaba abierta —dieciséis letras desprendidas de su título en siete láminas—, está **cerrada**: las 84 letras de esas siete láminas van hoy en la primera línea de su título en los dos idiomas, y una guarda dura (`letters_off_their_titles`) aborta los módulos 13 y 14 si vuelve a ocurrir. También están cerradas la S9 (d) —dieciséis marcadores visibles: contados por color sobre el PNG de 600 ppp, 16 discos intactos y separados en las cuatro construcciones, ninguno partido ni fundido con otro—, la clave de la S46 (a), hoy entera fuera de los mapas, el punto decimal de la S32 (d) y la S34 (f) españolas, hoy coma, y las diez áreas funcionales de la S37 (e), hoy en inglés. Pendiente (versión de envío): la revista pide 107 mm de ancho —el estudio usa 180 mm de página completa— y ningún título interno de panel, que las láminas conservan. **Cerrado y medido en la lámina misma** (fase 4j): el porcentaje por idioma, el signo menos y la ventana de años ya no tienen ninguna excepción en la lámina —el lector independiente contó **0 rangos con guion en 44.113 rótulos** de las 244 construcciones, 0 rótulos con la puntuación del otro idioma y 0 negativos escritos con guion—, y el cuerpo mínimo de las 61 láminas distintas es exactamente 6,0 pt, el suelo del estudio |
| Tablas 8 pt, n junto a % | Tablas 1–7 y S1–S125 (`docx_builder`: 7–9 pt según columnas; tablas anchas en páginas apaisadas); n junto a % en las tablas de tasas y encuestas | parcial: ajuste tipográfico final pendiente (versión de envío). **Remedido sobre los doce documentos de esta compilación**, con los mismos dos instrumentos y no con otros: **0 cifras partidas** dentro de sus dígitos (`tests/test_table_numbers_unbroken.lineas_partidas_en_numero` sobre el `pdftotext -layout` de los doce PDF) y **0 unidades huérfanas** —ningún signo de porcentaje separado de su cifra por un corte de renglón o de celda— (`docx_builder.unidades_partidas` sobre el mismo texto impreso), en las 5.925 páginas. Los dos detectores llevan control negativo en `tests/test_percent_and_code_breaks.py` para que no puedan quedarse mudos |
| Decimales a media altura y p con dos cifras significativas | Texto y tablas usan punto decimal estándar; valores p en la Tabla S48 | pendiente (versión de envío) |
| Suplemento en un PDF con índice | El material suplementario va **dentro** del manuscrito, tras las Referencias, y también como `manuscript/supplement_<variante>_<idioma>.pdf` (portada, «Contenido», métodos S1–S5, metodología extendida con 33 ecuaciones, Figuras S1–S54, Tablas S1–S125, referencias suplementarias); páginas numeradas en el pie | cumplido (índice textual; sin números de página en el índice) |
| Tamaño de archivo para el envío | Compilación del 2026-09-08, 18:19:38 → 18:34:01 (medida con `pdfinfo` y `stat` sobre los doce PDF y los doce DOCX): **artículo solo** 6,6–6,8 MB en DOCX (64–65 páginas; PDF 5,0–5,1 MB); **apéndice suelto** 66,2–67,7 MB (659–697 páginas; PDF 77,9–79,0 MB); **manuscrito combinado** 72,8–74,4 MB (722–759 páginas; PDF 82,9–84,0 MB). En total **5.925 páginas**, 588,8 MB de DOCX y 667,8 MB de PDF, más 5.937 miniaturas de revisión a 45 ppp (una por página y una hoja de contacto por documento). **Ni una página más ni una menos** que la compilación anterior: los arreglos de la fase 4k son de vocabulario y de trazo y no mueven la maqueta —el reparto por documento es idéntico (725/663/65 · 759/697/64 · 722/659/65 · 752/690/64)— | cumplido; el envío debe ser el **DOCX**, no su PDF: la conversión remuestrea a 300 ppp las cinco figuras del artículo que el DOCX incrusta a 600 |

## Lo que queda abierto

**Ningún punto abierto bloquea el envío.** Dos lectores independientes midieron los doce documentos de la compilación
del **2026-09-08 (14:45:29 → 15:01:26)** —no los de ésta— sobre la página impresa, sobre el XML del propio `.docx` y
sobre las 5.925 páginas rasterizadas, con instrumento propio y control positivo en cada medida. La lectura de **página
y tipografía PASA** en sus once comprobaciones; la de **contenido** cerró tres de sus cuatro puntos y dejó **uno**
abierto. Ese punto está hoy **cerrado y en el papel**, y con él los tres detalles cosméticos que la misma ronda
levantó. Lo que queda son **trece puntos y ninguno se lee como defecto**: no cambian ninguna cifra del estudio ni
ninguna conclusión. Están listados uno a uno —dónde se producen, por qué siguen abiertos y **cuánto cuesta cerrarlos**—
en la **sección 6 de `memo_es.md`**, que el propio constructor escribe en cada corrida desde `review_status.json` y
`manuscript/build_report.json`, de modo que ninguna de esas frases envejece a mano.

**Cerrados en la fase 4k, y medidos sobre estos doce documentos**, con el mismo instrumento antes y después:

* **La glosa del panel fijo de 65 hospitales, dicha de dos maneras.** El corpus imprimía «presentes en 2019–2022» y
  «presentes en todos los años 2019–2024» para el mismo conjunto —los dos enunciados designan los mismos 65
  hospitales, y ninguna cifra cambia—, y los imprimía cerca. Hoy la glosa se escribe **una sola vez** en
  `common.fixed_panel_gloss` (siete formas) y la piden de ahí los siete módulos que la imprimen (06, 07, 09a, 09b, 11,
  13 y 16). Medido con `common.fixed_panel_membership_windows` sobre los párrafos y las celdas de los doce DOCX:
  **31 enunciados con la ventana 2019–2022 por manuscrito, 30 por apéndice y 1 por artículo → 0 en los doce**, y
  **48 / 46 / 2** con la ventana 2019–2024 (eran 16 / 15 / 1). La **regla de construcción** —«intersección de 2019,
  2020, 2021 y 2022, verificada como subconjunto de 2023 y de 2024»— sobrevive donde es exacta, tres veces por
  documento largo, y la metodología extendida explica en una frase por qué la glosa no la repite.
  `tests/test_fixed_panel_gloss.py` cierra la puerta con 18 casos, y su reja se comprobó plantando la versión vieja.
* **«Getis-Ord» con guion.** El par de apellidos se escribía con guion en las leyendas de las láminas espaciales y en
  las notas de tabla, y con raya corta en los encabezados y en la prosa. Se declara hoy una sola vez en el glosario de
  impresión de `labels.py`: **0 con guion** en los doce documentos (eran 3 por documento largo) y **7 con raya corta**
  por documento largo, que es exactamente la suma de los dos repartos anteriores.
* **«Gauss—Newton» con raya larga**, en el título de Wedderburn (1974), donde el renglón se cortaba justo detrás.
  Hoy lleva raya corta y un juntapalabras: **0 con raya larga** y **1 con raya corta** en cada uno de los doce.
* **«crosswalk», anglicismo suelto en la prosa española.** La prosa española imprime «cuadro de equivalencias»:
  **0 apariciones libres** de la palabra inglesa en los seis documentos españoles (eran 1 en el artículo, 45 en el
  manuscrito y 44 en el apéndice) contra **34 / 33 / 1** de la forma española, con los **11 identificadores de
  máquina** por documento largo (`comuna_crosswalk.csv`, `ST4a_comuna_crosswalk_summary`,
  `censo2024_comunas_not_in_crosswalk`, `cartography_comunas_vs_crosswalk`) intactos y el término inglés entero en los
  seis documentos ingleses. **La primera reconstrucción encontró un resto que el arreglo no veía**: el encabezado
  «Geografía y crosswalk.», una vez por documento largo español, se escondía detrás de su propio punto, porque el
  patrón que protege los identificadores prohibía el punto entero. En un identificador el punto siempre lleva detrás
  una letra o una cifra; al final de una frase, no. El patrón se afinó en su único sitio (`labels.PRINTED_TERMS`) y el
  resto desapareció sin tocar ninguno de los cuatro identificadores.

**Lo que las lecturas dieron por correcto y esta compilación vuelve a dar**, medido sobre estos doce archivos: el
**folio en 5.925 de 5.925 páginas**, 0 ausentes; **260 colas de leyenda rotuladas y 0 sin rotular** (4 por archivo
sólo-artículo, 26 en / 39 es por manuscrito, 22 en / 35 es por apéndice); **432 de 432 entradillas** en la página de
su lámina, sobre 472 leyendas localizadas; **0 cifras partidas** dentro de sus dígitos y **0 unidades huérfanas** en
las 5.925 páginas; la página más corta del corpus, **315** caracteres contando palabras unidas por un espacio y
**272** contando sólo los no blancos, que es la portada de `supplement_sin_rett_es` y un bloque de título completo;
las **33 ecuaciones** en los ocho documentos largos; y los recuentos de la portada, **artículo 5 láminas / 7 tablas /
50 referencias**, **apéndice 54 / 125 / 40** y **manuscrito combinado 59 / 132 / 67**. La suite pasa entera sobre este
árbol: **292 pruebas, 1 saltada, 148 sub-pruebas, 0 fallos** (432 s).

**Dos cosas que la página dice y conviene saber, y que no bloquean.** (1) **48 páginas del corpus llevan sólo la cola
rotulada de una leyenda** y detrás mucho blanco —cinco por documento largo en inglés y siete en español—: no están
vacías, llevan su cola con rótulo, su número de figura y su folio, y son el precio medido de la regla nueva frente a
una alternativa peor, 100 colas sin dueño. (2) La cifra declarada de rangos con guion se queda corta frente a lo que
imprime la página; ninguno de ellos es un intervalo de lectura —son claves de modelo y la transcripción literal
declarada del diccionario REM y de los códigos de encuesta—, de modo que falla la cifra, no la regla.

**Dos observaciones que no son defectos.** La conversión a PDF **remuestrea a 300 ppp** las cinco figuras del
artículo, que el DOCX incrusta a 600 ppp y 180 × 245 mm como se declaró: el archivo que se envíe debe ser el DOCX. Y
«ninguna página por debajo de 300 caracteres» depende de la definición, y el informe dice ya de cuál habla: con la
primera cuenta el mínimo del corpus es 315 y ninguna página baja de 300; con la segunda el mínimo es 272 y quedan por
debajo tres portadas de apéndice suelto, que son bloques de título completos y no páginas vacías. Las dos cuentas las
escribe el propio constructor en cada corrida (`review.layout.min_chars` y `min_chars_nonws`).

Lo que necesita un dato o una decisión del equipo autor —afiliación, financiamiento, segundo autor que verifique los
datos, ética, declaración de IA, URL/DOI de datos y código, variante Rett principal, regla PIE 2022, ponderadores
JUNAEB, cadenas de búsqueda del «Research in context», formularios ICMJE y recorte de los párrafos `[OPT]`— está en
la sección 5 del mismo memo, y el memo **termina** con las listas juntas: lo que se lee como defecto, lo que decide
el equipo autor y lo demás que queda abierto, cada punto con su razón y su coste.
