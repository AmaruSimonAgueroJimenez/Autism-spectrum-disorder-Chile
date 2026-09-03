# Autismo en Chile: REM y GRD

Repositorio de análisis reproducibles en Python y Quarto sobre el trastorno del espectro autista (TEA) en las fuentes administrativas del sistema público de salud chileno. La documentación activa contiene **cuatro QMD**:

| Documento | Contenido | Versión para leer |
|---|---|---|
| [index.qmd](docs/index.qmd) | Índice, alcance y resultados principales | [Inicio](docs/index.html) |
| [metodologia.qmd](docs/metodologia.qmd) | Diseño, contexto epidemiológico, fuentes, definiciones, unidades, denominadores, estandarización, intervalos, tendencias, análisis espacial, reglas de lectura REM, calidad, sesgos, reproducibilidad y referencias | [Metodología](docs/metodologia.html) |
| [rem.qmd](docs/rem.qmd) | REM: ingresos y egresos de salud mental, tasas de ingreso por población, edad y sexo, subcategorías, regiones, comunas, panel de establecimientos, tamizaje por etapa, rehabilitación y comparación ecológica con GRD | [Informe REM](docs/rem.html) |
| [grd.qmd](docs/grd.qmd) | GRD, parte A: epidemiología descriptiva (tasas crudas y estandarizadas con intervalos, tendencias, estacionalidad, sexo y edad, subcategorías, posición del código, características del episodio, letalidad, estancia, hospitales, codiagnósticos, rehospitalización, regiones, comunas, Moran y LISA); parte B: trayectorias diagnósticas | [Informe GRD](docs/grd.html) |

Los cuatro QMD ejecutan bloques Python para calcular tablas y figuras desde los agregados. Comparten configuración en `docs/_quarto.yml`, bibliografía en `docs/references.bib`, utilidades de presentación en `scripts/report_helpers.py` y funciones epidemiológicas en `scripts/epi_helpers.py`.

## Preguntas e interpretación

GRD describe hospitalizaciones en las que se consignó un código F84 y reconstruye qué diagnósticos hospitalarios preceden al primer registro observado de autismo y si aparece como principal o secundario. **Las tasas son de hospitalizaciones o de personas hospitalizadas, no de incidencia ni prevalencia; el primer registro no equivale al primer diagnóstico clínico y los antecedentes no demuestran diferenciales descartados.** Los identificadores se analizan separadamente en 2019–2020 y 2021–2024, sin enlaces entre ambos períodos.

REM describe actividad asistencial agregada. A05 distingue total, sexo y edad; A03 requiere sumar ambos sexos para obtener el total de una fila completa; los códigos A28 se mantienen por sección. Las tasas de ingreso por población son indicadores de acceso y registro, no de casos nuevos. Los informes no presentan esos registros como incidencia o personas únicas nacionales.

## Renderizar los documentos

Requiere Quarto y Python con Jupyter, más la pila científica y geoespacial fijada en `requirements-analysis.txt` (pandas, scipy, statsmodels, pyarrow, geopandas, libpysal, esda).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-analysis.txt
python scripts/render_reports.py
```

El comando ejecuta los cuatro QMD y actualiza `docs/index.html`, `docs/metodologia.html`, `docs/rem.html` y `docs/grd.html`. Usa los agregados existentes en `output_files/consolidacion/`, por lo que no requiere montar el disco externo. Los mapas leen `data/comunas.shp` y `data/Regional.shp`; las tasas leen `data/censo_proyecciones_ano_edad_genero.parquet`.

Para volver a extraer las fuentes, recalcular tasas y estadísticos espaciales y después renderizar:

```sh
python scripts/render_reports.py --refresh
```

Para recalcular solo tasas, razones, tendencias, Moran y LISA a partir de los agregados ya extraídos:

```sh
python scripts/render_reports.py --rates-only
```

La extracción completa tarda algunos minutos (GRD alrededor de un minuto; REM unos cuatro minutos). Los scripts también se pueden ejecutar por separado, en este orden:

```sh
python scripts/audit_grd_linkage.py      # inventario y continuidad del identificador
python scripts/audit_rem.py              # catálogo, validación y agregados REM (región, comuna, edad/sexo, panel)
python scripts/grd_trajectories.py       # historias hospitalarias, cohortes y trayectorias
python scripts/grd_epidemiology.py       # registros F84 por año, edad, sexo, comuna, posición, características y codiagnósticos
python scripts/epi_rates.py              # tasas, estandarización, intervalos, tendencias, estandarización indirecta, Moran y LISA
python -m unittest discover -s tests -v  # pruebas sintéticas de trayectorias y de las funciones epidemiológicas
python scripts/render_reports.py
```

`grd_epidemiology.py`, `audit_rem.py`, `grd_trajectories.py` y `audit_grd_linkage.py` solo necesitan pandas y openpyxl, por lo que pueden ejecutarse en un entorno mínimo junto al disco de datos; `epi_rates.py` y los QMD necesitan la pila completa. La entrada anterior `scripts/build_consolidation_report.py` se conserva como compatibilidad: llama al renderizador de los documentos actuales.

## Datos y resultados

La raíz de entrada es `ASESORIAS_DATA_ROOT`, por defecto `/Volumes/Datos/Asesorias_Data`. Debe estar montada al ejecutar la extracción. Se leen los CSV canónicos de `GRD/` y `REM/SerieA/`, junto con los diccionarios de `REM/SerieA/metadata/diccionarios/` y el catálogo de hospitales de `GRD/metadata/`. No se modifican ni copian las fuentes al repositorio.

El análisis abarca GRD 2019–2024 y REM 2017–2024. Los archivos REM 2025–2026 requieren validar integridad y cobertura antes de incorporarlos. Los denominadores son las proyecciones INE base Censo 2017 por comuna, edad simple y sexo.

- [Resultados agregados y diccionario de salidas](output_files/consolidacion/README.md): tablas sin identificadores de pacientes.
- `scripts/audit_grd_linkage.py`: continuidad y calidad del identificador.
- `scripts/audit_rem.py`: catálogo por año, validación de columnas y agregación por región, comuna, edad y sexo, y panel de establecimientos.
- `scripts/grd_trajectories.py`: recuperación de todos los egresos y reconstrucción temporal.
- `scripts/grd_epidemiology.py`: agregados descriptivos de los registros F84.
- `scripts/epi_helpers.py`: tasas, estandarización directa (OMS) e indirecta, intervalos exactos y gamma, razones, cambio porcentual anual, suavizado empírico bayesiano.
- `scripts/epi_rates.py`: aplica lo anterior a los agregados y calcula Moran global y LISA con PySAL.
- `tests/`: pruebas con datos sintéticos.

Las auditorías aceptan `--years`; las trayectorias aceptan `--eras`; los scripts de extracción aceptan `--output`. Los QMD activos esperan las salidas completas en `output_files/consolidacion/`. Las ejecuciones parciales deben usar una carpeta de salida distinta para conservar esa entrada completa.

## Archivo histórico

Todo el contenido previo de `docs/` se trasladó a [others scripts](<others scripts/README.md>), incluyendo QMD, HTML y recursos. [El manifiesto del traslado](<others scripts/archive_manifest.csv>) permite verificar las rutas y hashes de los archivos originales. Allí se conserva también la [propuesta metodológica inicial](<others scripts/propuesta-rem-grd.md>). Los análisis de esos informes (tasas estandarizadas, mapas, Moran y LISA) fueron reimplementados sobre la extracción validada en los documentos actuales.

Los resultados anteriores fuera de `output_files/consolidacion/` se mantienen para trazabilidad. Los informes vigentes se renderizan localmente; estos comandos no publican cambios en el sitio remoto.
