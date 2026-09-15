# Administrative recognition of autism in Chile, 2019–2025: multi-system study

Folder holding the analytical pipeline and the manuscript builders. `references.py` (Vancouver formatter) and `authors.py` are versioned here because they were lost
with the deleted `paper/` folder. The analysis plan is in
`analysis_plan.md` and the source review in `scripts/downloads/DATA_REVIEW.md`.
It does not modify the reports of `docs/` nor the aggregates of `output_files/`.

**Two complete variants** of the analysis are generated (`con_rett`: full F84 family; `sin_rett`: F84 without Rett
syndrome) and **two languages** (`es`, `en`) for every table, plate and manuscript. The final editorial cut is made
by the author team; the pipeline does not limit the number of tables or figures.

## Running

```sh
export ASESORIAS_DATA_ROOT=/Volumes/Datos/Asesorias_Data   # optional; it is the default value
python study/pipeline/run_all.py                    # runs 00 → 17 in order (10 requires soffice and pdftoppm)
python study/pipeline/run_all.py --from 06          # resumes from a step
```

Each step writes tidy tables to `outputs/tidy/`, controls to `outputs/controls/`, plates and tables by variant and
language to `outputs/<variant>/<language>/`, and the manuscripts to `manuscript/`, which holds two distinct and
separate products:

* **`manuscript/04_submission_study/`**: what is submitted to *the target journal*:
  the article (a single case definition, journal format), its appendix in a single PDF and the Spanish working
  version. Built by `journal/build_journal.py`; `config.SUBMISSION` is its canonical path.
* **`manuscript/02_others/`**: the complete corpus of the study, twelve documents (two variants × two languages ×
  combined, standalone appendix and article-only). It is the working record from which the submission derives and
  against which every figure is audited. Built by `pipeline/10_manuscript.py`; `config.CORPUS` is its canonical path.

Each folder carries its own `README.md`.

The chronological index of the ten versions of the manuscript (`01_paper`, `02_others`, `03_final_2026_09_09`,
`04_submission_study` and the dated revisions `05_` to `10_revision_*`) is in `manuscript/LEEME.md`; the
numeric prefix of each folder is its order of generation. Since 14 September 2026 every version keeps its DOCX and
PDF in `documents/` and the scripts that produce them in `scripts/` (versions 1 to 4) or `technical/sources/`
(revisions).

`manuscript/` and `outputs/` are excluded from git (repository `.gitignore`): they are heavy products regenerated
by the pipeline. The public replica of version 10 (data, plate scripts, equations and resolved content) and the
corpus of results are in `docs/study/` and are read in `docs/study.html`, `docs/study_supplement.html` and
`docs/version_02_corpus.html`.

## Pipeline steps (`pipeline/`)

| Step | Content | Main outputs |
|---|---|---|
| `00_provenance.py` | SHA-256 and metadata of 182 source artefacts (20.8 GB) | `data_provenance.csv`, `provenance_manifest_checks.csv` |
| `01_grd_core.py` | GRD hospital core 2019–2024: F84 by position, observed/fixed panel, activity, coding depth, age/sex, within-year persons, by variant | `grd_year_summary.csv`, `grd_hospital_year.csv`, `grd_age_sex_year.csv`, `grd_coding_depth_year.csv`, `grd_subcode_year.csv` |
| `01b_deis_egresos.py` | DEIS discharges 2019–2024 as an external check (F84 in DIAG1) | `deis_year_summary.csv`, `deis_vs_grd_year.csv` |
| `02_rem_pathway.py` | REM administrative pathway: A03 by era, A27, A05, A28 (flows) and P2/P6 (December stocks; June as sensitivity), reporting facilities, stable panel, verified dictionaries | `rem_pathway_tidy.csv`, `rem_pathway_annual.csv`, `rem_establishment_year.csv`, `rem_a05_age_sex_annual.csv`, `rem_code_dictionary_check.csv` |
| `03_denominators.py` | INE base 2017 (+ Census 2024 and base 2024), FONASA, APS, ISAPRE, REM-20 (panel of 188), commune crosswalk | `ine_population_*.csv`, `fonasa_*.csv`, `aps_*.csv`, `isapre_*.csv`, `rem20_*.csv`, `comuna_crosswalk.csv`, `coverage_layers_year.csv` |
| `04_surveys.py` | ENDIDE 2022 and ENCAVI 2023–24 with complex design (Taylor) | `survey_estimates.csv`, `survey_items_dictionary.csv` |
| `05_education.py` | PIE/SINACES from the PDFs (page and table) and weighted JUNAEB EVE 2019–2025 | `pie_series.csv`, `junaeb_tea_year_level.csv`, `education_summary_year.csv` |
| `06_models.py` … `09b_*.py` | Models, consolidated controls, plates and tables by variant and language | `models_summary.csv`, `outputs/<variant>/<language>/` |
| `10_manuscript.py` | **Twelve** documents, three per variant and language (`prose_en.py` / `prose_es.py` + `docx_builder`): the **combined** manuscript (article with Figures 1–5 and Tables 1–7, plus the supplementary material in the same file after the References), the **standalone appendix** with the same material and the same numbering register, and the **article-only** file, without the supplementary part and with the same plates embedded at 600 dpi. Title page with the authors of `paper/prose.py` and counts measured on the article; `[OPT] ` mark removed with a final index of optional paragraphs; page numbering and wide tables in landscape sections; conversion to PDF (LibreOffice), 45 dpi thumbnails and contact sheets; executive memo | `manuscript/02_others/manuscript_<variant>_<language>.docx|pdf`, `manuscript/02_others/supplement_<variant>_<language>.docx|pdf`, `manuscript/02_others/article_<variant>_<language>.docx|pdf`, `manuscript/02_others/review/`, `manuscript/02_others/build_report.json`, `memo_es.md` |
| `11_grd_episode_detail.py` … `16_extra_tables.py` | GRD episode detail, extended methods with the 33 equations (`equations.py`, `prose_methods_extended.py`), extra hospital, REM and context plates, spatial analysis and territorial correlation, and the extended series of tables | `outputs/tidy/grd_*.csv`, `outputs/tidy/spatial_*.csv`, `outputs/<variant>/<language>/extra/figures|tables/` |
| `17_extended_material.py` | Verifies the supplementary material inside the manuscript: inventory, shared numbering register (Figure S1–S54, Table S1–S125), article citations produced only by the register, equations and aggregates against the tidy tables; with `--build` it rebuilds the twelve documents | `outputs/controls/17_extended_material_controls.csv`, `extended_material_index.md` |

Each module writes `outputs/controls/<module>_controls.csv` with expected versus observed values; the consolidated summary is in `outputs/controls/controls_summary.csv` (written by `07_controls.py`, which consolidates the control files of modules 00 to 17 and must be run again whenever any of them changes).

### Plate layout checker

`common.check_layout(fig)` measures an already drawn plate **on its real renderer** and returns the list of defects; `common.assert_layout_clean(fig, name)` fails with the full list. Nine defect families are measured: text over text, text outside the canvas, axis title over the ticks, legend over data, value label over its marker or its error bar, value label whose box covers its own bar, titles of two neighbouring panels without a gap between them, repeated numeric ticks and panel grid (the norm is 3 × 2; `common.plate_declare(fig, grid=None)` exempts a single-canvas diagram such as Figure 1). The nine plate modules (`06_models.py`, `08a`, `08b`, `08c`, `08d`, `13`, `14`, `15` and `15b`) always save through `common.plate_resolve` or `common.save_fig`, which is where the gate sits, and `tests/test_plate_layout.py` checks that none bypasses it. The gate is switched on with the environment variable `PLATE_CHECK`:

```sh
PLATE_CHECK=off     python study/pipeline/08d_figure_dataflow.py   # default: no check
PLATE_CHECK=report  python study/pipeline/14_extra_figures_rem.py  # accumulates and summarises at the end
PLATE_CHECK=strict  python study/pipeline/run_all.py               # fails at the first bad plate
```

Equivalent in code: `common.plate_check_enable('strict')`. Some modules (for example `08d`) call the checker themselves and exit with an error if any of their plates has defects, regardless of the environment variable.

## Documents

- `analysis_plan.md`: question, conceptual DAG, estimands, denominators, sensitivities and exclusions.
- `data_provenance.csv`: one row per source artefact with SHA-256 and usage rules (step 00).
- `decision_log.md`: discrepancies, assumptions and decisions.
- `reporting_checklist.md`: STROBE, RECORD and journal requirements, with the manuscript section where each item is met.
- `extended_material_index.md`: number, file, origin and description of every supplementary plate and table (step 17).
- `supplementary_material.py`: bilingual inventory, thematic grouping and builder of the supplementary part shared by the manuscript and the standalone appendix.
- `journal_guidelines.md`: verified journal requirements with URL and date consulted.
- `variables_dictionary.md`: dictionary of variables derived from the tidy tables.
- `memo_es.md`: executive memo in Spanish (generated by `pipeline/10_manuscript.py`; figures from `outputs/values_<variant>.json` and `outputs/controls/controls_summary.csv`).
- `prose_en.py`: manuscript and appendix in English as `docx_builder` blocks (`manuscript(variant, V)`, `supplement(variant, V)`, `word_counts`, `citation_keys`, `supplementary_map`); `python prose_en.py --out DIR` builds both variants. Tests in `tests/test_prose_en.py`.
- `prose_es.py`: Spanish version of the manuscript and appendix (same structure, same figures from `outputs/values_<variant>.json`, same citation keys, same `[OPT] ` paragraphs and same supplementary numbering as `prose_en.py`; decimal comma through `common.fmt_number(x, dec, 'es')`; legends, titles and PNG plates from `outputs/<variant>/es/`); `python prose_es.py --out DIR` builds both variants. Tests in `tests/test_prose_es.py`.
