# Autismo en Chile: REM y GRD

Repositorio de análisis reproducibles en Python y Quarto. La documentación activa contiene **exactamente tres QMD**:

| Documento | Contenido | Versión para leer |
|---|---|---|
| [index.qmd](docs/index.qmd) | Índice, alcance y resultados principales | [Inicio](docs/index.html) |
| [rem.qmd](docs/rem.qmd) | REM: ingresos, series mensuales, edad/sexo, tamizaje y rehabilitación | [Informe REM](docs/rem.html) |
| [grd.qmd](docs/grd.qmd) | GRD: antecedentes, primer registro y posición diagnóstica | [Informe GRD](docs/grd.html) |

Los tres QMD ejecutan bloques Python para calcular tablas y figuras desde los agregados. Comparten configuración en `docs/_quarto.yml` y utilidades de presentación en `scripts/report_helpers.py`.

## Preguntas e interpretación

GRD estudia qué diagnósticos hospitalarios preceden al primer registro observado de autismo y si aparece como principal o secundario. **Ese registro no equivale al primer diagnóstico clínico y los antecedentes no demuestran diferenciales descartados.** Los identificadores se analizan separadamente en 2019–2020 y 2021–2024, sin enlaces entre ambos períodos.

REM describe actividad asistencial agregada. A05 distingue total, sexo y edad; A03 requiere sumar ambos sexos para obtener el total de una fila completa. Los códigos A28 se mantienen por sección. Los informes no presentan esos registros como incidencia o personas únicas nacionales.

## Renderizar los tres documentos

Requiere Quarto y Python con Jupyter. Ejecución comprobada con Python 3.14 y las versiones fijadas en `requirements-analysis.txt`.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-analysis.txt
python scripts/render_reports.py
```

El comando ejecuta los tres QMD y actualiza `docs/index.html`, `docs/rem.html` y `docs/grd.html`. Usa los agregados existentes, por lo que no requiere montar el disco externo para volver a generar las tablas y figuras. No modifica los QMD ni lee los informes archivados.

Para volver a extraer las fuentes y después renderizar:

```sh
python scripts/render_reports.py --refresh
```

La extracción completa puede tardar varios minutos. Los scripts también se pueden ejecutar por separado:

```sh
python scripts/audit_grd_linkage.py
python scripts/audit_rem.py
python scripts/grd_trajectories.py
python -m unittest discover -s tests -v
python scripts/render_reports.py
```

La entrada anterior `scripts/build_consolidation_report.py` se conserva como compatibilidad: ahora llama al renderizador de los tres documentos y no vuelve a generar el antiguo QMD combinado.

## Datos y resultados

La raíz de entrada es `ASESORIAS_DATA_ROOT`, por defecto `/Volumes/Datos/Asesorias_Data`. Debe estar montada al ejecutar la extracción. Se leen los CSV canónicos de `GRD/` y `REM/SerieA/`, junto con los diccionarios de `REM/SerieA/metadata/diccionarios/`. No se modifican ni copian las fuentes al repositorio.

El análisis abarca GRD 2019–2024 y REM 2017–2024. Los archivos REM 2025–2026 requieren validar integridad y cobertura antes de incorporarlos.

- [Resultados agregados y diccionario de salidas](output_files/consolidacion/README.md): 20 tablas sin identificadores de pacientes.
- `scripts/audit_grd_linkage.py`: continuidad y calidad del identificador.
- `scripts/grd_trajectories.py`: recuperación de todos los egresos y reconstrucción temporal.
- `scripts/audit_rem.py`: catálogo por año, validación de columnas y agregación.
- `tests/`: pruebas con datos sintéticos de fechas, posiciones, antecedentes y empates.

Las auditorías aceptan `--years`; las trayectorias aceptan `--eras`; los tres scripts de extracción aceptan `--output`. Los QMD activos esperan las salidas completas en `output_files/consolidacion/`. Las ejecuciones parciales deben usar una carpeta de salida distinta para conservar esa entrada completa.

## Archivo histórico

Todo el contenido previo de `docs/` se trasladó a [others scripts](<others scripts/README.md>), incluyendo QMD, HTML y recursos. [El manifiesto del traslado](<others scripts/archive_manifest.csv>) permite verificar las rutas y hashes de los 207 archivos originales. Allí se conserva también la [propuesta metodológica inicial](<others scripts/propuesta-rem-grd.md>).

Los resultados anteriores fuera de `output_files/consolidacion/` se mantienen para trazabilidad. Los informes vigentes se renderizan localmente; estos comandos no publican cambios en el sitio remoto.
