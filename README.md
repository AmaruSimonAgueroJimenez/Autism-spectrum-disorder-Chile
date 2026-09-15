# Autism in Chile: REM and GRD

Repository of reproducible Python and Quarto analyses of the administrative recognition of autism spectrum disorder (ASD) in the routine records of the Chilean public health and education systems, 2019–2025: hospital discharges grouped by diagnosis-related groups (GRD), the monthly statistical summaries of the public network (REM), diagnostic trajectories, and the results of the multi-source study built on the same data. Nothing in the repository is prevalence or incidence: every figure is a count of episodes, programme entries, follow-up stocks or school enrolments, published with its unit, denominator and coverage. The active documentation contains **six QMD documents**, all in English: four analytical reports and two pages of study results, organised by the version that produced them.

| Document | Content | Rendered version |
|---|---|---|
| [index.qmd](docs/index.qmd) | Home page, scope and main results | [Home](docs/index.html) |
| [methods.qmd](docs/methods.qmd) | Design, epidemiological context, sources, definitions, units, denominators, standardisation, intervals, trends, spatial analysis, REM reading rules, quality, biases, reproducibility and references | [Methods](docs/methods.html) |
| [rem.qmd](docs/rem.qmd) | REM: mental-health programme entries and discharges, population entry rates, age and sex, subcategories, regions, communes, facility panel, screening by stage, rehabilitation and the regional and commune-level ecological comparison with GRD | [REM report](docs/rem.html) |
| [grd.qmd](docs/grd.qmd) | GRD, part A: descriptive epidemiology (crude and standardised rates with intervals, trends, seasonality, sex and age, subcategories, code position, episode characteristics, case fatality, length of stay, hospitals, co-diagnoses, readmission, regions, communes, Moran and LISA); part B: diagnostic trajectories | [GRD report](docs/grd.html) |

The four reports run Python blocks that compute tables and figures from the aggregates. They share the configuration in `docs/_quarto.yml`, the bibliography in `docs/references.bib`, the presentation helpers in `scripts/report_helpers.py` and the epidemiological functions in `scripts/epi_helpers.py`.

## Results of the study

The analysis is built in `study/` with its own pipeline (`pipeline/00_provenance.py` to
`17_extended_material.py`, documented in [study/README.md](study/README.md)) that reads the microdata of
the data volume and writes tidy tables, plates and documents. The study was written in ten versions
between 3 and 14 September 2026 (`study/manuscript/`, index in `study/manuscript/LEEME.md`). Those
version folders, with their DOCX, PDF and 600 dpi plates (~1.5 GB), **stay out of git**, as does
`study/outputs/`; the pipeline code and the results are versioned.

**The text of the manuscript is not part of this repository. Its results are.** They are organised by
the version that produced them, from the index of [docs/index.qmd](docs/index.qmd):

| Document | Content | Rendered version |
|---|---|---|
| [index.qmd](docs/index.qmd) | Common index: the analytical reports, the registry of the ten versions and what each one added to the results | [Home](docs/index.html) |
| [version_02_corpus.qmd](docs/version_02_corpus.qmd) | Version 02, the extended corpus: 59 plates and 132 tables of the pipeline (variant without Rett syndrome), the reference against which later figures are audited | [v02 corpus](docs/version_02_corpus.html) |
| [version_10_panels.qmd](docs/version_10_panels.qmd) | Version 10, the most recent: the four panel figures and the nine supplementary figures, rebuilt at every render from `docs/study/data/` (English and Spanish plates), with their layout check | [v10 results](docs/version_10_panels.html) |

What each version added is audited rather than asserted. `scripts/audit_versions.py` hashes every tidy
result table in each version folder and compares them pairwise; `docs/study/versions.json` records the
outcome and the pages are rendered from it. The audit finds that **no result table ever changed between
versions 05 and 10**: versions only ever add tables, and from version 07 onwards what changes is how the
same numbers are laid out into figures. Run it where the version folders exist:

```sh
python scripts/audit_versions.py
```

`docs/study/data/` contains the public tables the plates are built from (tidy and verified), a commune
extract without commune identifiers and with small cells masked, the STIX equations, the verified facts
file and `contenido_v10.json` with the figure titles and captions, in English and Spanish. These tables
are versioned in git, so the plates can be rebuilt from a clone without the source microdata. Commune
tables that carry cells under five cases are withheld.

```sh
python scripts/render_reports.py --figures  # rebuilds the plates of docs/study and renders the six QMD documents
```

## Questions and interpretation

GRD describes hospitalisations in which an F84 code was documented and reconstructs which hospital diagnoses precede the first observed autism record and whether it appears as principal or secondary. **The rates are of hospitalisations or of hospitalised persons, not of incidence or prevalence; the first record is not the first clinical diagnosis, and prior diagnoses do not demonstrate ruled-out differentials.** Identifiers are analysed separately in 2019–2020 and 2021–2024, with no linkage between the two periods.

REM describes aggregate care activity. A05 distinguishes total, sex and age; A03 requires adding both sexes to obtain the total of a complete row; the A28 codes are kept by section. Population entry rates are indicators of access and recording, not of new cases. The reports do not present those records as incidence or as national unique persons.

## Rendering the documents

Every result on the site carries the code that produced it. Each table and figure has a **Show the
code that produced this** toggle, and the **`</>` Code** button at the top right of a page unfolds or
hides all of them at once. This needs `echo: true` in `docs/_quarto.yml`: with `echo: false` Quarto
strips the code before `code-fold` can wrap it, and the toggle never appears.

On [docs/version_10_panels.qmd](docs/version_10_panels.qmd) the figures are not linked from a folder:
each chunk contains the code that draws its figure, runs it, shows the English plate and exports the
175 mm PNG, SVG and PDF in both languages. That code is a copy of `docs/study/figuras_principales.py`
and `figuras_suplementarias.py`, which stay in place for rebuilding the plates outside the site. To stop
the two copies drifting, the page is generated from those modules and a test compares them:

```sh
python scripts/build_version_pages.py          # rewrite the page from the figure modules
python -m pytest tests/test_page_figure_code.py  # fails if the page and the modules differ
```

Two figures are the exception: S1 and S6 are inherited from earlier revisions by `copy_reused()`, so no
drawing code for them exists here. The [version 02 corpus](docs/version_02_corpus.qmd) is stored images
throughout, because the pipeline that drew those plates reads the GRD and REM microdata, which is not
part of this repository. Both pages say so on the page itself.

Requires Quarto and Python with Jupyter, plus the scientific and geospatial stack pinned in `requirements-analysis.txt` (pandas, scipy, statsmodels, pyarrow, geopandas, libpysal, esda).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-analysis.txt
python scripts/render_reports.py
```

The command runs the six QMD documents and updates `docs/index.html`, `docs/methods.html`, `docs/rem.html`, `docs/grd.html`, `docs/version_02_corpus.html` and `docs/version_10_panels.html`. It uses the aggregates already in `output_files/consolidacion/`, so it does not require mounting the external disk. The maps read `data/comunas.shp` and `data/Regional.shp`; the rates read `data/censo_proyecciones_ano_edad_genero.parquet`.

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
