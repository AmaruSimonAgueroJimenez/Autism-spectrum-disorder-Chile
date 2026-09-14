# Descarga reproducible de datos chilenos

Estos programas adquieren las fuentes oficiales que pueden fortalecer el estudio de autismo sin copiar las bases grandes dentro del repositorio. El código y el catálogo quedan en Git; los archivos descargados se guardan en el disco externo.

## Uso rápido

Con `/Volumes/Datos` montado:

```sh
# Comprobar las bases canónicas ya disponibles, sin usar internet
python scripts/download_hospital_data.py --audit
python scripts/download_new_chile_data.py --audit

# Ver el catálogo hospitalario sin descargar
python scripts/download_hospital_data.py --list

# Completar metadatos y fuentes hospitalarias pequeñas; reutiliza GRD/REM/DEIS existentes
python scripts/download_hospital_data.py

# Descargar denominadores, encuestas, educación y contexto territorial
python scripts/download_new_chile_data.py

# Resolver URLs y tamaños sin escribir
python scripts/download_new_chile_data.py --dry-run
```

Para disponer de P2/P6 de manera reproducible, primero hay que conservar los
ZIP REM oficiales —la carpeta `SerieA/sources/official_zips` conserva ese nombre
por compatibilidad histórica, pero cada ZIP contiene **todas** las series— y
después extraer Serie P:

```sh
python scripts/download_hospital_data.py \
  --dataset deis_rem --retain-sources --include-large --years 2019 2025

python scripts/downloads/extract_rem_series_p.py --years 2019-2025
```

El extractor valida rutas internas, esquema, año, firma y CRC, escribe de forma
atómica y genera `/Volumes/Datos/Asesorias_Data/REM/SerieP/manifest_extract_rem_series_p.csv`
con tamaño y SHA-256. Una segunda ejecución verifica y conserva los archivos
idénticos.

La ruta compartida se toma de `ASESORIAS_DATA_ROOT` y por defecto es `/Volumes/Datos/Asesorias_Data`. Las nuevas fuentes específicas del proyecto van a `AUTISM_DATA_ROOT` o, si no está definida, a `${ASESORIAS_DATA_ROOT}/Autism`.

El punto de entrada completo es:

```sh
python scripts/downloads/download_chile_sources.py --profile core
python scripts/downloads/download_chile_sources.py --dataset encavi_2023_2024 endide_2022
python scripts/downloads/download_chile_sources.py --profile all --years 2019 2024
```

## Qué cubre

| Grupo | Fuentes automáticas | Función prevista |
|---|---|---|
| Hospital | GRD público 2019–2024, egresos DEIS, REM, REM-20, establecimientos, diccionarios GRD | Núcleo, profundidad/cobertura de codificación y panel estable |
| Cobertura | Beneficiarios FONASA, inscritos APS, beneficiarios ISAPRE | Denominadores y sesgo público/privado |
| Población | Proyecciones INE y Censo 2024 | Denominadores y sensibilidad |
| Encuestas | ENDIDE 2022 y ENCAVI 2023–2024 | Benchmarks poblacionales externos |
| Educación | Informes PIE/SINACES y EVE-JUNAEB 2019–2025 | Triangulación escolar y definiciones |
| Territorio | Pobreza comunal SAE 2024 | Covariable territorial preespecificada |

El ZIP REM anual contiene todas las series necesarias. Por eso A03, A05, A27,
A28, P2 y P6 no se descargan como seis copias separadas. Los códigos, unidades y
quiebres comprobados están en [rem_pathway_codes.csv](rem_pathway_codes.csv), y
la revisión empírica completa está en [DATA_REVIEW.md](DATA_REVIEW.md).

Los enlaces GRD proceden de la pestaña **Catálogo de Datos** del [tablero público de FONASA](https://public.tableau.com/views/PropuestaTableroGRD/PropuestaTableroGRD?:showVizHome=no). Los archivos observados cubren 65 hospitales en 2019–2022, 68 en 2023 y 72 en 2024; incluyen hospitalización y cirugía mayor ambulatoria. Debe informarse la cobertura anual y usarse el panel fijo de 65 como sensibilidad. FONASA exige citar `datosabiertos.fonasa.cl`. Los archivos originales se pueden retener así:

```sh
python scripts/download_hospital_data.py \
  --dataset grd_publico \
  --retain-sources \
  --include-large \
  --full-archive-check
```

Sin `--retain-sources`, el programa detecta `GRD/GRD_PUBLICO_<año>.csv`, `REM/SerieA/SerieA_<año>.csv` y `DEIS/Egresos/<año>.csv` y no crea copias redundantes. La adquisición de fuentes nunca reemplaza esos canónicos.

## Descargas grandes

Estas colecciones se describen en el catálogo, pero exigen `--include-large`:

- contenedores oficiales GRD, REM y egresos cuando no existe ya el canónico;
- microdatos individuales FONASA 2018–2025 (aproximadamente 1,82 GB comprimidos en total);
- microdatos EVE-JUNAEB 2019–2025 (aproximadamente 9,6 GB según el catálogo al 4 de septiembre de 2026);
- CASEN 2024 (aproximadamente 1,6 GB).

La opción evita descargar varios gigabytes por accidente. Los agregados FONASA suelen bastar para los denominadores y deben preferirse si responden la pregunta.

Para completar o reanudar las colecciones grandes de contexto:

```sh
python scripts/download_new_chile_data.py \
  --dataset junaeb_eve_microdata casen_2024 casen_2024_metadata fonasa_microdata \
  --include-large --full-archive-check
```

El programa conserva y verifica los archivos completos. CASEN incluye la base
Stata principal, el complemento provincia/comuna, ambos libros de códigos,
cuestionario, nota de uso y documentación metodológica. La alternativa RData
equivalente queda documentada en el catálogo para quien prefiera ese formato.

## Integridad y procedencia

Cada archivo pasa por estas comprobaciones antes de reemplazar el destino:

1. descarga reanudable a un archivo `.part`, con sidecar de identidad remota y
   `If-Range` solo cuando existe un ETag fuerte;
2. rechazo de HTML/XML servido con nombre de datos;
3. comprobación de firma según formato;
4. lectura del directorio ZIP/XLSX y, con `--full-archive-check`, CRC de todos sus miembros;
5. tamaño remoto y `Content-Range` exacto cuando el servidor lo informa;
6. checksum remoto cuando existe, más SHA-256 local;
7. URL GCS fijada a su generación cuando está disponible;
8. reemplazo atómico y bloqueo de corrida para proteger manifiestos y parciales.

La bitácora queda en `${AUTISM_DATA_ROOT}/metadata/download_manifest.csv`, con URL original y resuelta, fecha UTC, tamaño, SHA-256, ETag, modificación remota y ruta relativa. El archivo [source_registry.csv](source_registry.csv) registra además finalidad, cobertura, acceso y limitaciones. Las rutas descargadas no se versionan.

## Fuentes no automáticas

- Los microdatos diagnósticos PIE no tienen una descarga pública reproducible identificada; requieren Transparencia o convenio.
- El Registro Nacional de la Discapacidad no es un denominador de autismo y su acceso masivo es restringido.
- El Registro Nacional de Prestadores Individuales no debe consultarse masivamente sin API o convenio.
- SINIM y los geodatos INE exigen escoger indicador/capa y versión; el catálogo conserva sus páginas de acceso, pero no adivina esa decisión metodológica.

Un archivo público no es automáticamente comparable. Antes de unir fuentes hay
que documentar unidad de observación, código CUT, período, residencia frente a
ubicación del establecimiento, cobertura, ponderadores y quiebres de definición.
El catastro DEIS descargable es vigente y mutable, no una secuencia de catastros
anuales; el panel histórico debe reconstruirse desde el reporte observado en
REM/GRD. REM-20 mide establecimiento × área funcional × mes y sirve para
actividad/capacidad, no como población cubierta.

El plan analítico del estudio está en [analysis_plan.md](../../study/analysis_plan.md).
