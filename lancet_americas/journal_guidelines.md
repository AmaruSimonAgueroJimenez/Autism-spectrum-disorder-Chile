# Requisitos verificados de *The Lancet Regional Health – Americas*

**Fuente:** PDF oficial «Information for Authors», pie de página «www.thelancet.com August 2026», descargado el 2026-09-04 desde
`https://www.thelancet.com/pb-assets/Lancet/authors/tlam-info-for-authors-1759484803240.pdf` (SHA-256 `1ed6a0a910d81d93a85cd8be5d7673f44d01c0554c5f1a9f6039e1fa88efa13c`; copia y texto en `journal_guidelines/`).
**Bloqueo documentado:** las páginas HTML `thelancet.com/journals/lanam/...` y ScienceDirect devuelven HTTP 403 a clientes automatizados; el PDF se obtuvo con `curl` y un *user agent* de navegador. **El equipo autor debe confirmar estos límites en el sitio antes del envío.**

## Artículos (investigación original)

| Requisito | Texto verificado |
|---|---|
| Extensión | «Be around 3500–5000 words with 30 references (the word count is for the manuscript text only)» |
| Referencias | máximo 30; estilo Vancouver, numeradas por orden de mención, superíndice tras la puntuación; ≤ 6 autores todos, ≥ 7 primeros tres + et al |
| Resumen | «semistructured summary, with five paragraphs (Background, Methods, Findings, Interpretation, and Funding), not exceeding 250 words» |
| Research in context | panel obligatorio en todos los artículos de investigación: *Evidence before this study* (fuentes, criterios, fechas exactas de búsqueda, términos, calidad), *Added value of this study*, *Implications of all the available evidence*; sin referencias en el panel |
| Guías de reporte | estudios observacionales «must be reported according to the STROBE statement, and should be submitted with their protocols»; registro de estudios observacionales «encouraged»; estimaciones globales GATHER; EQUATOR |
| Contribuciones | contribuciones individuales de todos los autores al final del texto; «more than one author directly accessed and verified the underlying data»; todos con acceso completo a los datos |
| Declaración de intereses | subtítulo «Declaration of interests» al final del texto; formulario ICMJE |
| Financiamiento | fuentes en agradecimientos y «role of the funding source» (diseño, recolección, análisis, redacción, decisión de envío) |
| Data sharing | declaración obligatoria: si se compartirán datos («undecided» no se acepta), qué datos, documentos adicionales (protocolo, plan estadístico), cuándo, dónde (URL) y con qué criterios de acceso |
| Inteligencia artificial | declaración separada de uso de IA al final del manuscrito (herramienta, versión, propósito, alcance de la supervisión; prompts si se solicitan); el uso de IA en el proceso de investigación se declara en Métodos; la IA no puede ser autora |
| Sexo y género | análisis por sexo/género según SAGER; usar «sex assigned at birth»; discutir limitaciones |
| Discapacidad | describir instrumentos y métodos de identificación; no inferir discapacidad del diagnóstico |
| Figuras | mínimo 300 dpi y 107 mm de ancho; título de figura en Times New Roman 10 negrita; leyendas 10 pt a un espacio; paneles con letras minúsculas (a, b, c); sin títulos dentro del gráfico; sin recuadro; una figura por página; mapas con proyecciones de área fiel |
| Tablas | título en Times New Roman 10 negrita; cuerpo 8 pt a un espacio; encabezados internos 8 pt negrita; n siempre junto a % |
| Formato de texto | punto decimal a media altura (23·4); números uno a diez en palabras salvo unidades; sin negrita de énfasis; medias con DE, medianas con RIC; valores p con dos cifras significativas salvo p<0·0001 |
| Suplemento | un solo PDF con índice y páginas numeradas; en inglés; texto 10 pt Times New Roman |
| Idioma | inglés; resúmenes traducidos se aceptan tras la aceptación |
| Acceso abierto | revista totalmente OA; APC tras la aceptación (monto en https://www.thelancet.com/open-access; descuentos y exenciones posibles) |
| Datos | conservar datos crudos hasta 10 años tras la publicación |

## Implicaciones para este proyecto

- La versión de revista se recortará a 3500–5000 palabras, ≤ 30 referencias, 4 figuras principales y resumen de 250 palabras; el resto pasa al suplemento (esta primera pasada no limita tablas ni figuras por instrucción del usuario).
- Los paneles de las láminas para la revista usarán letras **minúsculas** y sin títulos internos; las láminas de trabajo actuales usan mayúsculas y títulos, y se ajustarán en la versión de envío.
- STROBE y RECORD (`reporting_checklist.md`); protocolo/plan de análisis (`analysis_plan.md`) para adjuntar.
- Declaración de IA obligatoria: el pipeline y la redacción usaron asistencia de IA bajo supervisión del autor; se describe en Métodos y en la declaración final.
