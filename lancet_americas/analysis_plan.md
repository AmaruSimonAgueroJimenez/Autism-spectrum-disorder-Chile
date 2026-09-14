# Plan de análisis — Reconocimiento administrativo del autismo en Chile, 2019–2025

**Versión:** 1.0, 4 de septiembre de 2026. Preespecificado antes de explorar asociaciones; los cambios posteriores se registran en `decision_log.md`.

## Pregunta principal

¿Cómo cambió entre 2019 y 2025 el reconocimiento administrativo del autismo y la demanda registrada de servicios en los sistemas público de salud y educación de Chile, y cuánto del cambio es robusto a variaciones de cobertura, intensidad de codificación y definiciones?

La contribución no es estimar prevalencia ni incidencia. Es mostrar la convergencia descriptiva entre sistemas administrativos independientes, cuantificar las amenazas de comparabilidad y traducir los hallazgos en necesidades de vigilancia y capacidad. La Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con efecto causal identificable.

## DAG conceptual (simple)

```
Ocurrencia subyacente ──┐
Conciencia social/Ley ──┼─► Búsqueda de atención ─► Contacto con el sistema ─► Reconocimiento administrativo (código/registro)
Oferta y capacidad ─────┤                                   ▲                              ▲
Pandemia (2020–2021) ───┘                     Cobertura del sistema / panel reportante   Profundidad y taxonomía de codificación
```
Ningún dato permite separar las contribuciones de ocurrencia, búsqueda de atención, cobertura y codificación; el estudio las describe y las somete a sensibilidades.

## Fuentes, unidades y enlace

| Fuente | Unidad | Stock/flujo | Geografía | Enlace individual |
|---|---|---|---|---|
| GRD público 2019–2024 | episodio (hospitalización o CMA) | flujo | hospital; comuna de residencia informada | identificador dentro del año; sin enlace 2020/2021 |
| REM A03/A27/A05/A28 2019–2025 | fila establecimiento × mes × código | flujo (actividad) | establecimiento | ninguno |
| REM P2/P6 2019–2025 | stock semestral por establecimiento | stock (junio, diciembre) | establecimiento | ninguno |
| DEIS egresos 2019–2024 | egreso | flujo | establecimiento; residencia | ninguno |
| FONASA agregados 2018–2025; APS 2019–2025; ISAPRE 2019–2025 | celda agregada de diciembre | stock | inscripción/domicilio; centro APS; comuna administrativa | ninguno |
| INE base 2017 (Censo 2024 y base 2024 como sensibilidad) | población | stock | residencia | n/a |
| REM-20 2019–2025 | establecimiento × área × mes | actividad/capacidad | establecimiento | ninguno |
| ENDIDE 2022, ENCAVI 2023–24 | persona encuestada | transversal | nacional/región | ninguno |
| PIE/SINACES 2019–2025; JUNAEB EVE 2019–2025 | registro escolar agregado; estudiante | stock escolar | nacional; establecimiento | ninguno |

Las fuentes no se enlazan por persona. Todo indicador que combine etapas es una **ruta administrativa agregada**, no una cascada individual.

## Variantes de definición (dos análisis completos)

| Variante | GRD | REM A05 / P6 | Series idénticas en ambas |
|---|---|---|---|
| `con_rett` | cualquier F84.x, incluido F84.2 | todas las categorías TGD incluidas las filas de Rett | autismo estricto REM (05990022, P6241010, P6241060), F84 principal, A03/A27/A28/P2, educación, encuestas |
| `sin_rett` | F84.x excepto F84.2 | mismas categorías sin Rett | ídem |

El TGD amplio 2019–2020 de REM (06902600, 05225000, P6223000, P6223380) contiene Rett de forma inseparable: se presenta solo como sensibilidad marcada en ambas variantes.

## Estimandos y jerarquía

1. **Primario hospitalario (GRD).** Episodios con F84 documentado en cualquier posición por 100.000 episodios GRD del mismo año y panel. Sensibilidades obligatorias: F84 principal; hospitalización estricta frente a toda modalidad (CMA aparte); panel anual observado frente a panel fijo de 65 hospitales; estratificación/ajuste por profundidad diagnóstica (número de diagnósticos codificados); personas únicas solo dentro de cada año; tasas por población INE por edad y sexo (por 100.000 habitantes) como lectura poblacional complementaria; efectos por hospital (aleatorios) si el modelo es estable.
2. **Primario ambulatorio (REM A05).** Ingresos por autismo desde 2021: conteo, tasa por 100.000 habitantes INE con estandarización por edad cuando el desglose por edad/sexo lo permita, número de establecimientos reportantes y panel estable. TGD amplio 2019–2020 solo como sensibilidad separada.
3. **Seguimiento (REM P2/P6).** Stocks de diciembre por autismo (P2 NANEAS, P6 APS y especialidad), con junio como sensibilidad y sin sumar semestres; establecimientos reportantes; NANEAS total como denominador solo desde 2023.
4. **Detección y referencia (REM A03/A27).** Componentes por era de definición (2019–2022, 2023–2024, 2024 31–59 meses, 2025) y A27 desde 2023, presentados en facetas separadas; ningún cociente entre etapas de bases no enlazables.
5. **Rehabilitación (REM A28).** Ingresos por TEA a rehabilitación primaria y hospitalaria desde 2023.
6. **Denominadores y cobertura.** INE (poblacional), FONASA/ISAPRE (aseguramiento), inscritos APS (cobertura operativa), REM-20 (actividad/capacidad; panel de 188). Cada uno responde una pregunta distinta y ninguno se elige por conveniencia.
7. **Validación poblacional.** ENDIDE 2022 y ENCAVI 2023–24 con diseño complejo: proporción, total ponderado, EE e IC 95 %; sin desagregación comunal.
8. **Triangulación educativa.** PIE TEA estricto, TEA-Asperger, armonizado (regla explícita para la discrepancia de 2022) y SINACES 2024–2025; JUNAEB EVE 2019–2025 con el wording anual y el ponderador `EXP`; 1º medio 2024 «no estimable».

## Modelado y sensibilidad preespecificados

- Familia: log-lineal cuasi-Poisson con desplazamiento del denominador (episodios GRD, población INE o establecimientos reportantes según el estimando); CPA con IC 95 %; verificación de sobredispersión y de autocorrelación residual.
- Unidad: año (nacional) y establecimiento/hospital-año para modelos con efectos aleatorios de establecimiento.
- Covariables mínimas: profundidad diagnóstica media del panel (GRD), indicador de 2020–2021 como disrupción de reporte (no como efecto causal), era de definición (REM).
- Panel completo frente a observado; missing frente a cero (la ausencia de fila REM no es cero).
- Sin series de tiempo interrumpidas causales: la coincidencia de pandemia, cambios de códigos, expansión del reporte y ley impide identificar un efecto de la Ley 21.545.
- Multiplicidad: los análisis son descriptivos; las comparaciones locales del análisis espacial (si se incluyen en suplemento) usan FDR.
- Supresión: celdas con menos de 5 eventos se muestran como «<5» en tablas territoriales.

## Exclusiones y reglas

- No llamar prevalencia, incidencia ni «aumento real del autismo» a conteos administrativos.
- No llamar «hospitalizaciones por autismo» a episodios con F84 secundario.
- No sumar junio y diciembre de Serie P; no interpolar 2020.
- No deduplicar personas GRD a través de 2020/2021.
- No eliminar filas repetidas de FONASA 2018–2020 (son aditivas).
- No mezclar lugar de atención con residencia sin análisis de compatibilidad.
- No usar 72 hospitales como panel fijo.
- Toda cifra debe rastrearse a archivo, versión, filtro y script; si no se reproduce, se elimina o se marca pendiente.
