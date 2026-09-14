# Plan de láminas y tablas — estado final (2026-09-08)

Este archivo describe lo que el estudio publica hoy. La **autoridad** de la numeración es
`lancet_americas/supplementary_material.py` (`FIGURE_ORDER`, `TABLE_ORDER`, `FIGURE_GROUPS`, `TABLE_GROUPS`); la lista
ítem por ítem, con archivo, tabla tidy de origen y descripción, está en `extended_material_index.md`, que escribe el
módulo 17 en cada corrida. Aquí sólo se fija el diseño: qué lleva cada lámina del artículo, qué reglas cumplen todas y
cómo se agrupa el material suplementario.

Estado medido de la compilación del 2026-09-07 (19:19–19:57), leído de `manuscript/build_report.json` y remedido el
2026-09-08 con `pdfinfo`, `pdftotext` y `stat`: **59 láminas** (5 + 54) y **132 tablas** (7 + 125) en cada manuscrito
combinado, con **33 ecuaciones**; manuscritos de 718–755 páginas (72,7–74,4 MB; PDF 82,8–83,7 MB), apéndices sueltos de
655–693 páginas (66,1–67,6 MB; PDF 77,9–78,7 MB) y archivos sólo con el artículo de 64–65 páginas (6,6–6,8 MB; PDF
5,0–5,1 MB). Los ocho documentos largos ganaron cinco o seis páginas frente a la compilación anterior: es el coste en
papel de ensanchar las columnas de cifra para que ningún número se parta. En `outputs/` hay **244 PNG de lámina** (61
nombres × 2 variantes × 2 idiomas), **todos de 4251 × 5787 px**: las 59 del estudio y dos láminas heredadas que ningún
documento incrusta (`figS4_grd_model_sensitivities` y `figS7_a05_standardised_rates`). La tercera huérfana,
`figS3_hospital_effects` —la única apaisada—, dejó de producirse: `pipeline/06_models.py` ya no la dibuja y sus cuatro
copias se borraron. `supplementary_material.LEGACY_UNREGISTERED_PLATES` sigue nombrándola, y esa línea queda pendiente.

## Norma de lámina (fase 4c, petición del autor) y composición verificada (fase 4d)

Se aplica a **las 59 láminas** del estudio, las 5 del artículo y las 54 suplementarias, sin excepción:

* Lienzo **180 × 245 mm en vertical**, dibujado **a escala 1:1** a **600 ppp** (4251 × 5787 píxeles), de modo que se
  imprime una lámina por página sin encogerla.
* Rejilla de **3 filas × 2 columnas**, **máximo seis paneles**. Una lámina de cuatro o cinco paneles mantiene la
  rejilla y usa la celda libre para su leyenda, sus notas o un panel que se gane el sitio; nunca estira un panel.
  Una lámina que necesitara más de seis paneles se dividiría en láminas consecutivas: en esta fase no hizo falta
  dividir, añadir ni renombrar ninguna, y por eso la numeración suplementaria no cambió.
* Tipografía: cuerpo base **8 pt**, título de panel **9 pt** en negrita, marcas de eje **7 pt**, leyenda **7 pt**, y
  **nada por debajo de 6 pt** en ningún rótulo ni anotación.
* **Letras de panel en minúscula** (a, b, c, d, e, f), en la figura y en la leyenda, en los dos idiomas, como pide la
  revista.
* Paleta Okabe–Ito y estilo compartido con `paper/figures.py`; una copia por variante (`con_rett`, `sin_rett`) e
  idioma (`es`, `en`) en `outputs/<variante>/<idioma>/figures`.
* En el documento, cada lámina abre su propia sección vertical con márgenes de 7 mm arriba, 10 mm abajo y 8,5 mm a los
  lados, y ocupa una página entera, compartida con la frase que la presenta y con su leyenda.
* **Composición medida, no supuesta.** `common.check_layout(fig)` mide la lámina terminada sobre su renderizador real y
  denuncia nueve familias de defecto —texto sobre texto; texto fuera del lienzo; título de eje sobre sus propias marcas;
  leyenda o nota sobre los datos; rótulo de valor sobre su marcador o su barra de error; rótulo de valor cuyo recuadro tapa
  su propia barra; títulos de dos paneles vecinos sin hueco entre ellos; marcas numéricas repetidas; recuento de paneles—,
  cada una con
  el panel, los artistas y el solape en puntos. Los nueve módulos de lámina la ejecutan sin cambiar una línea, por los dos
  embudos que todos atraviesan (`plate_resolve` y `save_fig`), con `LANCET_PLATE_CHECK=off|report|strict`. Los defectos se
  arreglan **en el módulo que dibuja**, nunca retocando la imagen: cero defectos hoy en los diez módulos, las dos variantes
  y los dos idiomas.

Reglas de contenido que ninguna lámina rompe: toda lámina REM muestra el número de establecimientos reportantes; las
eras de definición se presentan en facetas o segmentos separados y ninguna línea cruza un quiebre; stocks y flujos no
comparten eje; un numerador de lugar de atención sobre un denominador de residencia lleva su aviso explícito; las
celdas territoriales por debajo de 5 se suprimen; los dos idiomas llevan exactamente las mismas cifras.

## Láminas del artículo (Figuras 1–5)

| Lámina | Archivo | Paneles |
|---|---|---|
| **Figura 1** Qué se hizo con cada base de datos | `fig1_dataflow.png` | Esquema conceptual de seis carriles, uno por familia de fuentes —atención hospitalaria (GRD, DEIS); ruta de atención (REM Serie A: A03, A05, A27, A28); personas bajo control (REM Serie P: P2, P6); denominadores y cobertura (INE, FONASA, APS, ISAPRE, REM-20); encuestas y educación (ENDIDE, ENCAVI, MINEDUC/PIE, JUNAEB); territorio (cartografía comunal y privación SAE)—, cada uno leído de izquierda a derecha: **base de datos → pasos → lo que entrega**. Tres formas y ninguna más: cilindro = base de datos, caja redondeada = paso, bloque con punta = lo que el carril entrega. La unidad de análisis va en un distintivo sobre cada cilindro, en una palabra y una forma (cuadrado «registro», círculo «persona», hexágono «comuna»); sobre las flechas van sólo cifras (n a la entrada, n tras la selección de autismo y los extremos de la serie del carril); las exclusiones que importan van en rojo con su signo menos; los quiebres de definición se marcan sobre la flecha donde caen; y la regla de no enlace se enuncia una sola vez, como banda roja de trazos que separa los carriles. Sin título impreso, sin frases completas y sin nombres de archivo, de script o de columna: 118 palabras en español y 119 en inglés, sobre un presupuesto de 120 que el módulo cuenta en cada corrida. |
| **Figura 2** Completitud, cobertura, paneles y quiebres | `fig1_sources_coverage.png` | (a) **Estados de una celda REM** (establecimiento × periodo × código) por módulo y año: cada celda de la rejilla es una barra apilada al 100 % de los tres estados excluyentes —valor informado, cero explícito, no informado— con el % informado impreso en su propia banda encima de la barra; el cero explícito nunca pasa del 1,3 % de las celdas y se dibuja con un ancho mínimo visible, de modo que una celda en blanco no puede leerse como un cero; (b) capas de cobertura 2019–2025 en millones (INE, FONASA, ISAPRE, inscritos APS) con (FONASA+ISAPRE)/INE en el eje derecho; (c) establecimientos que reportan cada módulo REM por año; (d) hospitales GRD observados (65, 65, 65, 65, 68, 72) frente al panel fijo de 65 y episodios totales de cada panel; (e) REM-20: egresos de todos los establecimientos y del panel de 188, retención y establecimientos reportantes; (f) cobertura y quiebres de definición por fuente. |
| **Figura 3** Núcleo hospitalario GRD | `fig2_grd_core.png` | (a) Episodios con F84 en cualquier posición y con F84 principal por 100.000 episodios GRD del mismo panel, con IC exactos, panel observado y panel fijo; (b) por modalidad (toda, hospitalización estricta, CMA); (c) tasa de F84 por estrato de profundidad diagnóstica en 2019 y 2024, con la profundidad media en recuadro; (d) episodios por 100.000 habitantes INE por edad y sexo, 2019 frente a 2024, con el aviso de lectura complementaria; (e) tasa por hospital en 2024 (72 hospitales), ordenada, con IC exactos y la tasa nacional; (f) episodios frente a personas únicas **dentro** de cada año, episodios por persona y razón hombre:mujer. |
| **Figura 4** Ruta administrativa agregada REM | `fig3_rem_pathway.png` | (a) A03 detección en APS, era 2019–2022 y era 2023–2024; (b) A03 en las eras 2024 (31–59 meses) y 2025, no comparables con las anteriores; (c) A27 consejería y referencia asistida y A28 ingresos a rehabilitación, 2023–2025 (intervenciones e ingresos, no personas); (d) A05 ingresos y altas con el quiebre TGD amplio 2019–2020 / autismo estricto 2021–2025 marcado; (e) P2 NANEAS con TEA bajo control, stock de diciembre con junio como sensibilidad; (f) P6 APS y especialidad, con el mismo quiebre marcado. Cada rótulo lleva el n de establecimientos reportantes. |
| **Figura 5** Triangulación educativa y benchmarks | `fig4_triangulation.png` | (a) PIE: TEA estricto, TEA-Asperger, serie armonizada y cifra SINACES, con la discrepancia de 2022 (42.940 frente a 42.945) declarada; (b) JUNAEB, % ponderado por nivel, con «no estimable» marcado y nunca leído como cero; (c) ENDIDE 2022 y ENCAVI 2023–2024 con diseño complejo, IC 95 % logit-t y las estimaciones imprecisas en gris; (d) índices con primer año común 2021 = 100, declarados como índices; (e) cinco franjas apiladas, cada una con su eje, por 100.000 habitantes INE; (f) F84 principal: egresos DEIS frente a episodios GRD. |

## Tablas del artículo (Tablas 1–7)

| Tabla | Archivo | Contenido |
|---|---|---|
| Tabla 1 | `T2_grd_core.csv` | Núcleo hospitalario GRD 2019–2024: episodios con F84 por posición, panel, modalidad, profundidad, personas y población, con sus sensibilidades. |
| Tabla 2 | `T3_rem_pathway.csv` | Ruta REM 2019–2025 por módulo, código y era: totales anuales y stocks de diciembre con establecimientos reportantes. |
| Tabla 3 | `T4_denominators_coverage.csv` | Capas de denominador y cobertura: INE, FONASA, ISAPRE, inscritos APS y actividad REM-20. |
| Tabla 4 | `T5_survey_benchmarks.csv` | Benchmarks poblacionales de autismo reportado con diseño complejo: ENDIDE 2022 y ENCAVI 2023–2024. |
| Tabla 5 | `T6_education.csv` | Triangulación educativa 2019–2025: PIE (Apuntes 60 / SINACES) y JUNAEB por nivel. |
| Tabla 6 | `T7_models.csv` | Modelos preespecificados: CPA e IC 95 % por estimando y sensibilidad. |
| Tabla 7 | `T8_controls_compact.csv` | Controles de reproducción por familia de indicador (48 filas): esperado frente a observado, estado y explicación. La tabla completa (205 filas) es la Tabla S49. |

El inventario de fuentes, que en el plan de la fase 2 era la Tabla 1 del artículo, es hoy la **Tabla S1**, y los
recuentos de la Figura 1 son la **Tabla S2**.

## Material suplementario

**54 láminas** en siete grupos temáticos y **125 tablas** en nueve, más 33 ecuaciones numeradas dentro de la
metodología extendida. El orden es el del registro y es idéntico en el manuscrito combinado, en el apéndice suelto y
en los dos idiomas.

| Láminas | Grupo |
|---|---|
| S1–S15 | Láminas suplementarias centrales del artículo |
| S16–S25 | Episodios hospitalarios en detalle |
| S26–S34 | Ruta administrativa REM agregada en detalle |
| S35–S40 | Denominadores, encuestas y educación |
| S41–S42 | Razón por sexo entre fuentes |
| S43–S44 | Diagnósticos de los modelos y sensibilidad a la definición de caso |
| S45–S54 | Análisis espacial y correlación territorial |

| Tablas | Grupo |
|---|---|
| S1–S2 | Fuentes y flujo de datos (inventario de fuentes; recuentos de la Figura 1) |
| S3–S12 | Las diez tablas metodológicas, que se imprimen **dentro** de la metodología extendida, donde se explican; es la única excepción declarada al orden ascendente |
| S13–S50 | Tablas suplementarias centrales del artículo |
| S51–S72 | Episodios hospitalarios en detalle |
| S73–S81 | Ruta administrativa REM agregada en detalle |
| S82–S87 | Denominadores, encuestas y educación |
| S88–S89 | Razón por sexo entre fuentes |
| S90–S91 | Diagnósticos de los modelos y sensibilidad a la definición de caso |
| S92–S103 | Análisis espacial y correlación territorial |
| S104–S125 | Tablas de datos completas e inventario del proyecto |

## Qué cambió respecto del plan de la fase 2

* El plan de la fase 2 preveía cuatro láminas principales (F1–F4) con letras de panel A–F y quince láminas
  suplementarias (S1–S15). El artículo lleva hoy **cinco** láminas (la lámina de flujo de datos se incorporó como
  Figura 1) y el material suplementario **54**.
* El **panel (a) de la Figura 2** ya no es el esquema de fuentes, unidad y ausencia de enlace: eso lo cubre la Figura 1
  entera. En su lugar va el estado de las celdas REM, un hallazgo que no aparece en ningún otro ítem: el cero
  explícito casi no se usa, así que una celda en blanco no es un cero. En la fase 4d ese panel se volvió a dibujar: era
  un mapa de calor con dos recuadros de valor opacos y una barra de color de 60–100 % que no abarcaba los datos, y hoy
  es una barra apilada al 100 % por celda de la rejilla, con los tres estados excluyentes y el % informado en su propia
  banda.
* La **Figura 1** se redibujó en la fase 4d, a petición del autor, como esquema conceptual de qué se hizo con cada base
  de datos —seis carriles, tres formas, pocas palabras y ninguna instrucción—, en lugar de las siete fichas escritas en
  frases completas con un bloque «Cómo leer la lámina» al pie.
* La **composición dentro del panel** dejó de confiarse a la vista: `common.check_layout` la mide sobre el renderizador
  real y los nueve módulos la ejecutan con `LANCET_PLATE_CHECK`. Los defectos que las verificaciones nombraron —títulos
  de eje sobre sus marcas, leyendas y notas sobre los datos, rótulos de valor superpuestos, nombres de región fundidos,
  contenido recortado en español y una lámina que no era 3 × 2— se corrigieron en el módulo que dibuja.
* Las letras de panel pasaron de **mayúscula a minúscula** y las láminas de 432 mm encogidas dentro de la página se
  rehicieron a **180 × 245 mm a escala 1:1**, que es la norma de arriba.
* La antigua **Tabla 1** (inventario de fuentes) es la Tabla S1, y las tablas del artículo se renumeraron 1–7.
