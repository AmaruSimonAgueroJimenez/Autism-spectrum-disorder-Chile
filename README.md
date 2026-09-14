# Autism in Chile: REM and GRD

Repository of reproducible Python and Quarto analyses of autism spectrum disorder (ASD) in the administrative sources of the Chilean public health system, and of the manuscript "Rising administrative recognition of autism in Chile's health and education systems, 2019–2025: a national multi-source surveillance study" for The Lancet Regional Health – Americas. The active documentation contains **seven QMD documents**, all in English: four reports and three pages of the manuscript (see below):

| Document | Content | Rendered version |
|---|---|---|
| [index.qmd](docs/index.qmd) | Home page, scope and main results | [Home](docs/index.html) |
| [methods.qmd](docs/methods.qmd) | Design, epidemiological context, sources, definitions, units, denominators, standardisation, intervals, trends, spatial analysis, REM reading rules, quality, biases, reproducibility and references | [Methods](docs/methods.html) |
| [rem.qmd](docs/rem.qmd) | REM: mental-health programme entries and discharges, population entry rates, age and sex, subcategories, regions, communes, facility panel, screening by stage, rehabilitation and the regional and commune-level ecological comparison with GRD | [REM report](docs/rem.html) |
| [grd.qmd](docs/grd.qmd) | GRD, part A: descriptive epidemiology (crude and standardised rates with intervals, trends, seasonality, sex and age, subcategories, code position, episode characteristics, case fatality, length of stay, hospitals, co-diagnoses, readmission, regions, communes, Moran and LISA); part B: diagnostic trajectories | [GRD report](docs/grd.html) |

The four reports run Python blocks that compute tables and figures from the aggregates. They share the configuration in `docs/_quarto.yml`, the bibliography in `docs/references.bib`, the presentation helpers in `scripts/report_helpers.py` and the epidemiological functions in `scripts/epi_helpers.py`.

## Manuscript for The Lancet Regional Health – Americas

The manuscript is built in `lancet_americas/` with its own pipeline (`pipeline/00_provenance.py` to `17_extended_material.py`, documented in [lancet_americas/README.md](lancet_americas/README.md)) that reads the microdata of the data volume and writes tidy tables, plates and documents. Its ten versions (`lancet_americas/manuscript/01_paper` to `10_revision_2026-09-14_paneles`; index in `lancet_americas/manuscript/LEEME.md`), with their DOCX, PDF and 600 dpi plates, **stay out of git**, as does `lancet_americas/outputs/`; the pipeline code is versioned.

So that the results are reproducible from the repository, `docs/` includes three more pages, fed by the folder [docs/lancet](docs/lancet/README.md):

| Document | Content | Rendered version |
|---|---|---|
| [lancet.qmd](docs/lancet.qmd) | The article of version 10: text with citations, tables 1 and 2 and panel figures 1 to 4, regenerated from `docs/lancet/data/` by `docs/lancet/figuras_principales.py` (English and Spanish plates) | [Lancet](docs/lancet.html) |
| [lancet_supplement.qmd](docs/lancet_supplement.qmd) | Supplementary material: extended methods A1–A11 with 23 equations, complementary results B1–B4, tables S1–S9 and figures S1–S9 (`docs/lancet/figuras_suplementarias.py`) | [Supplement](docs/lancet_supplement.html) |
| [lancet_corpus.qmd](docs/lancet_corpus.qmd) | Extended corpus of the earlier versions: 59 plates and 132 tables of the pipeline (variant without Rett syndrome) | [Corpus](docs/lancet_corpus.html) |

`docs/lancet/data/` contains public copies of the tables the plates need (tidy and verified), a commune extract without identifiers with small cells masked, the STIX equations and `contenido_v10.json`, exported from the document builder with every figure already resolved, in English and Spanish. The plates generated this way coincide with those of the submitted version.

```sh
python scripts/render_reports.py --lancet-figures  # regenerates the plates of docs/lancet and renders the seven QMD documents
```

## Questions and interpretation

GRD describes hospitalisations in which an F84 code was documented and reconstructs which hospital diagnoses precede the first observed autism record and whether it appears as principal or secondary. **The rates are of hospitalisations or of hospitalised persons, not of incidence or prevalence; the first record is not the first clinical diagnosis, and prior diagnoses do not demonstrate ruled-out differentials.** Identifiers are analysed separately in 2019–2020 and 2021–2024, with no linkage between the two periods.

REM describes aggregate care activity. A05 distinguishes total, sex and age; A03 requires adding both sexes to obtain the total of a complete row; the A28 codes are kept by section. Population entry rates are indicators of access and recording, not of new cases. The reports do not present those records as incidence or as national unique persons.

## Rendering the documents

Requires Quarto and Python with Jupyter, plus the scientific and geospatial stack pinned in `requirements-analysis.txt` (pandas, scipy, statsmodels, pyarrow, geopandas, libpysal, esda).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-analysis.txt
python scripts/render_reports.py
```

The command runs the seven QMD documents and updates `docs/index.html`, `docs/methods.html`, `docs/rem.html`, `docs/grd.html`, `docs/lancet.html`, `docs/lancet_supplement.html` and `docs/lancet_corpus.html`. It uses the aggregates already in `output_files/consolidacion/`, so it does not require mounting the external disk. The maps read `data/comunas.shp` and `data/Regional.shp`; the rates read `data/censo_proyecciones_ano_edad_genero.parquet`.

To extract the sources again, recompute rates and spatial statistics and then render:

```sh
python scripts/render_reports.py --refresh
```

To recompute only rates, ratios, trends, Moran and LISA from the aggregates already extracted:

```sh
python scripts/render_reports.py --rates-only
```

The full extraction takes a few minutes (GRD about one minute; REM about four minutes). The scripts can also be run separately, in this order:

```sh
python scripts/audit_grd_linkage.py      # inventory and identifier continuity
python scripts/audit_rem.py              # catalogue, validation and REM aggregates (region, commune, age/sex, panel)
python scripts/grd_trajectories.py       # hospital histories, cohorts and trajectories
python scripts/grd_epidemiology.py       # F84 records by year, age, sex, commune, position, characteristics and co-diagnoses
python scripts/epi_rates.py              # rates, standardisation, intervals, trends, indirect standardisation, Moran and LISA
python -m unittest discover -s tests -v  # synthetic tests of the trajectories and of the epidemiological functions
python scripts/render_reports.py
```

`grd_epidemiology.py`, `audit_rem.py`, `grd_trajectories.py` and `audit_grd_linkage.py` only need pandas and openpyxl, so they can run in a minimal environment next to the data disk; `epi_rates.py` and the QMD documents need the full stack. The earlier entry point `scripts/build_consolidation_report.py` is kept for compatibility: it calls the renderer of the current documents.

## Data and results

The input root is `ASESORIAS_DATA_ROOT`, by default `/Volumes/Datos/Asesorias_Data`. It must be mounted when running the extraction. The canonical CSV files of `GRD/` and `REM/SerieA/` are read, together with the dictionaries of `REM/SerieA/metadata/diccionarios/` and the hospital catalogue of `GRD/metadata/`. The sources are neither modified nor copied into the repository.

The analysis covers GRD 2019–2024 and REM 2017–2024. The REM 2025–2026 files require validating integrity and coverage before they are incorporated. The denominators are the INE projections based on the 2017 Census by commune, single year of age and sex.

- [Aggregate results and output dictionary](output_files/consolidacion/README.md): tables without patient identifiers.
- `scripts/audit_grd_linkage.py`: identifier continuity and quality.
- `scripts/audit_rem.py`: catalogue by year, column validation and aggregation by region, commune, age and sex, and facility panel.
- `scripts/grd_trajectories.py`: recovery of all discharges and temporal reconstruction.
- `scripts/grd_epidemiology.py`: descriptive aggregates of the F84 records.
- `scripts/epi_helpers.py`: rates, direct (WHO) and indirect standardisation, exact and gamma intervals, ratios, annual percent change, empirical Bayes smoothing.
- `scripts/epi_rates.py`: applies the above to the aggregates, builds the REM–GRD ecological panels by region and by commune, and computes global Moran and LISA with PySAL.
- `tests/`: tests with synthetic data.

The audits accept `--years`; the trajectories accept `--eras`; the extraction scripts accept `--output`. The active QMD documents expect the complete outputs in `output_files/consolidacion/`. Partial runs should use a different output folder to preserve that complete input.

## Historical archive

All the earlier content of `docs/` was moved to [others scripts](<others scripts/README.md>), including QMD, HTML and resources. [The transfer manifest](<others scripts/archive_manifest.csv>) allows verifying the paths and hashes of the original files. The [initial methodological proposal](<others scripts/propuesta-rem-grd.md>) is also kept there. The analyses of those reports (standardised rates, maps, Moran and LISA) were re-implemented on the validated extraction in the current documents.

Earlier results outside `output_files/consolidacion/` are kept for traceability. The current reports are rendered locally; these commands do not publish changes to the remote site.
