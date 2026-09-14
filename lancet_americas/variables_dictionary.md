# Diccionario de variables derivadas (tablas tidy de `outputs/tidy/`)

Generado desde los informes de los módulos; cada tabla indica unidad, definición y módulo productor.

## `00_provenance_controls.csv` (módulo 00_provenance)

| Variable | Definición | Unidad |
|---|---|---|
| `expected / observed / abs_diff / rel_diff / status` | Expected value (module brief, DATA_REVIEW.md, manifests) vs observed; abs_diff = observed - expected; rel_diff = abs_diff/expected; status ok if exact or within 0.5% for rates, else differs; note documents the origin of the expectation | count, bytes or proportion |

## `02_rem_pathway_controls` (módulo 02_rem_pathway)

| Variable | Definición | Unidad |
|---|---|---|
| `status` | ok = observed equals expected (counts) or within 0.5% (rates); differs = otherwise (with note); info = reported value without an expected reference. | categorical |

## `04_surveys_controls.csv` (módulo 04_surveys)

| Variable | Definición | Unidad |
|---|---|---|
| `expected / observed / abs_diff / rel_diff / status` | Expected value (brief, config.CONTROLS, codebook, manual or simulation target), reproduced value, differences and 'ok' (exact, within 0.5% for rates, or within the stated simulation tolerance) or 'differs' | count, proportion or ratio |

## `05_education_controls` (módulo 05_education)

| Variable | Definición | Unidad |
|---|---|---|
| `status` | ok if observed equals expected or is within 0.5% relative (0.05 pp absolute for published rounded percentages; 2-decimal rounding for JUNAEB weighted %), else differs | flag |

## `aps_enrolment_centre_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `enrolled_total` | Sum of TOTAL_INSCRITOS for the centre in the December cut (PERIODO 31/12/YYYY). | persons (December stock) |
| `enrolled_tramo_AD / enrolled_tramo_X / enrolled_tramo_missing` | Enrolled persons whose FONASA tramo is A-D, X, or missing (missing only in 2019); kept separate, never pooled without definition. | persons |
| `in_panel_1871` | True if the centre code appears in all seven December files 2019-2025. | boolean |
| `geographic_change_flag` | True for codes whose comuna changes across years: 200261 (code reused for a different centre, Machali -> Chillan in 2022) and 200474 (Posta Pachica, Iquique -> Huara in 2022). | boolean |

## `aps_enrolment_comuna_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `age_band_20y` | Twenty-year band (0-19, 20-39, 40-59, 60-79, 80+) derived from EDAD_TRAMO; available for all years (raw bands are 20-year to 2023 and 10-year from 2024). | category |
| `age_band_10y` | Ten-year band derived from EDAD_TRAMO; available only from 2024 (plus 80+). | category |
| `n_centres` | Distinct centre codes contributing to the row; not additive across rows. | centres |

## `aps_panel` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `retention_panel_1871` | Enrolled in the 1,871 continuous-panel codes divided by total enrolled in the year. | proportion |

## `comuna_crosswalk` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `cut_comuna` | INE Codigo Unico Territorial of the comuna as an integer (4 digits for regions 1-9, 5 digits for regions 10-16). | code |
| `deis_code` | Same CUT zero-padded to 5 characters as used by DEIS/REM (string; read with dtype=str). | code |
| `comuna_norm` | Normalised INE name: accents stripped, upper case, apostrophes/hyphens/'¿' replaced by spaces, non-alphanumerics removed, single spaces. | text |
| `aliases_norm` | Pipe-separated normalised spelling variants explicitly mapped to this comuna (AISEN, COIHAIQUE, CABO DE HORNOS EX NAVARINO, CON CON, LA CALERA, MARCHIGUE, PAIHUANO). | text |
| `non_continental` | True for Isla de Pascua (5201), Juan Fernandez (5104), Cabo de Hornos (12201) and Antartica (12202). | boolean |

## `comuna_name_matches / all source tables` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `match_method` | How the raw comuna name was linked to cut_comuna: 'exact' (normalised name identical to INE), 'alias' (explicit alias table), 'unmatched' (no link; listed in comuna_unmatched.csv). | category |

## `coverage_layers_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `share_fonasa_plus_isapre_ine` | (FONASA December beneficiaries + ISAPRE December beneficiaries) / INE base-2017 population at 30 June. Not an uninsured rate (other regimes, timing and classification differences). | proportion |
| `ratio_aps_tramoAD_to_fonasa_inscritos` | APS enrolled in tramos A-D divided by FONASA beneficiaries with INSCRITO_APS='Si'; consistency check available 2019-2022 only. | ratio |
| `rem20_discharges_per_1000_ine` | All REM-20 discharges of the year per 1,000 INE base-2017 population; an activity-intensity indicator, not a use rate of a defined population. | discharges per 1,000 population |

## `data_provenance.csv` (módulo 00_provenance)

| Variable | Definición | Unidad |
|---|---|---|
| `source_id` | Study source group identifier (28 values: grd_publico, grd_dictionaries, rem_serie_a, rem_serie_a_dictionary, rem_serie_p, rem_serie_p_dictionary, deis_egresos, deis_egresos_dictionary, fonasa_aggregates, fonasa_dictionary, fonasa_aps, isapre_communal, ine_population_base2017, ine_censo2024, ine_base2024_national, deis_rem20, deis_establishments, endide_2022, encavi_2023_2024, casen_2024, casen_2024_metadata, mineduc_pie_reports, junaeb_eve_microdata, junaeb_eve_metadata, sae_poverty_2024, repo_population_parquet, repo_shapes, rem_pathway_codes) | category |
| `file` | Basename of the artefact | text |
| `relative_path` | Path relative to `root` (ASESORIAS_DATA_ROOT=/Volumes/Datos/Asesorias_Data for disk files, REPO for repository files) | text |
| `bytes` | File size from os.stat at run time | bytes |
| `sha256` | SHA-256 hex digest of the whole file computed by common.sha256_file (1 MiB streaming blocks) | hex string (64) |
| `downloaded_or_version_date` | ISO date of download/extraction/consolidation taken from the newest manifest listing the file, with the origin in parentheses (download_manifest.csv downloaded_at_utc; manifest_extract_rem_series_p.csv processed_at_utc; REM/SerieA/.rem_manifest.json normalizado_en; SOURCES_MANIFEST.md consolidation date); '; file mtime YYYY-MM-DD' appended when different; '(file mtime; not dated in any manifest)' when no manifest lists the file | date (UTC) |
| `observation_unit` | What one row of the source represents (episode, establishment x month x code, aggregated cell, surveyed person, polygon, dictionary row...) | text |
| `period` | Reference period of the artefact (year, December snapshot, coverage range, or 'current' for mutable catalogues) | text |
| `population_covered` | Population or activity the artefact covers, including the observed reporting panel (e.g. GRD 65/65/65/65/68/72 hospitals) and documented control totals from DATA_REVIEW.md | text |
| `geography` | Geographic key and its meaning: place of care (establishment/hospital), residence (INE, DEIS), insurance geography (FONASA mixed enrolment/domicile; ISAPRE administrative comuna) | text |
| `codes_columns_used` | Delimiter, columns and code sets the pipeline reads from the artefact (ICD-10 F84 family, REM A03/A05/A27/A28/P2/P6 codes with their year ranges, FONASA/APS column schemas by year, survey design pointers) | text |
| `stock_or_flow` | Whether the artefact is a stock (December/semester snapshot, population), a flow (episodes, discharges, monthly activity), activity/capacity (REM-20), a cross-sectional survey, or not applicable (dictionary/documentation) | category |
| `possible_denominator` | Denominator layer the artefact can legitimately provide or use (GRD episodes; INE population; insurance coverage; APS operational coverage; REM-20 capacity; reporting establishments; weighted survey population) | text |
| `definition_breaks` | Documented schema, code, taxonomy, encoding or panel breaks that affect comparability across years | text |
| `linkage_restrictions` | Person-level linkage that is NOT possible or allowed (within-year GRD persons only; no cross-source linkage; aggregates without persons) | text |
| `use_rule` | Prespecified rule for using the artefact in the study (primary vs sensitivity, aggregation rule, prohibited interpretations, which config.CONTROLS to reproduce) | text |
| `root` | Root against which relative_path is expressed: ASESORIAS_DATA_ROOT or REPO | category |
| `artefact_role` | data / dictionary / documentation / context / code map | category |
| `provider` | Producing institution (FONASA, DEIS/MINSAL, Superintendencia de Salud, INE, MDSF, MINEDUC, JUNAEB, repository) | text |
| `source_container` | Archive member(s) inside a rar/zip (bsdtar -tf) for FONASA and ENDIDE; for Serie P the extraction status, official SERIE_REM zip and member name from the extraction manifest; empty otherwise | text |
| `manifest_source` | Semicolon-separated list of manifests that list the file (download_manifest.csv, FONASA source_manifest.csv, SerieP extraction manifest, SerieA canonical_manifest.csv, DEIS Egresos canonical_manifest.csv, GRD SOURCES_MANIFEST.md); empty if none | text |
| `manifest_sha256` | Distinct SHA-256 value(s) recorded by the listing manifest(s) | hex string |
| `sha256_matches_manifest` | True if the recomputed SHA-256 equals every manifest value, False if any differs (a finding), not_listed if no manifest lists the file | category |
| `manifest_bytes` | Byte count(s) recorded by the listing manifest(s); empty when the manifest records no size (GRD SOURCES_MANIFEST.md records record counts) | bytes |
| `bytes_match_manifest` | True/False/not_listed comparison of on-disk bytes with manifest bytes | category |
| `file_mtime_utc` | File modification date (UTC) from os.stat | date |
| `landing_url` | Official landing page of the source (from source_registry.csv / source_catalog.json) | URL |

## `deis_age_sex_year.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `sex` | Harmonised sex: HOMBRE, MUJER, INTERSEX, DESCONOCIDO, SUPRIMIDO, TOTAL. Text labels 2019-2023 ('INTERSEX (INDETERMINDADO)' in 2022); codes 1=HOMBRE, 2=MUJER, 3=INTERSEX, 9=DESCONOCIDO in 2024 and the 2021 variant (1/2 inferred from obstetric O-codes). | category |
| `age_band_10` | Harmonised age band at admission: <1, 1-9, 10-19, ..., 70-79, 80+, SUPRIMIDO, TOTAL. From decadal labels (2019-2023: 'menor de un año', '1 a 9', ..., '80 a 89' and '90 y más' merged into 80+) or from 5-year labels (2024, 2021 variant: four neonatal/infant groups -> <1; '1 A 4' + '5 A 9' -> 1-9; ...; '80 A 84' + '85 A MAS' -> 80+). | category |
| `level` | Aggregation level of the row: sexxage_band_10 (full cross), sex (age = TOTAL), age_band_10 (sex = TOTAL), total. | category |

## `deis_age_sex_year_detail.csv, deis_cell_counts.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `age_group_raw / age_scheme` | Age label exactly as published by DEIS and the detected scheme: decadal (16-core-column files 2019-2023) or five_year (15-core-column files: 2024 and the 2021 variant). | category |

## `deis_age_who_year.csv, deis_age_sex_year_detail.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `age_group_who` | WHO 5-year age group (0-4, 5-9, ..., 75-79, 80+) derived only from 5-year layouts (2024 canonical; 2021 variant): 0-4 = 'menor a 7 días' + '7 A 27 DIAS' + '28 DIAS A 2 MES' + '2 MESES A MENOS DE 1 AÑO' + '1 A 4 AÑOS'; 80+ = '80 A 84 AÑOS' + '85 A MAS'. 'no derivable (esquema decenal)' for 2019-2023. | category |

## `deis_cell_counts.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `discharges` | Count of records in the cell (year, layout, pertenencia, sex, raw age group, prevision, F84 code in DIAG1 or '', F84 code in DIAG2 or '', CONDICION_EGRESO, raw ANO_EGRESO). Sum over cells = discharges_total. | discharges |

## `deis_establishment_year.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `dimension / category` | pertenencia_snss (SNSS, NO_SNSS, SUPRIMIDO); prevision (FONASA, ISAPRE, CAPREDENA, DIPRECA, SISA, NINGUNA, DESCONOCIDO, SUPRIMIDO from GLOSA_PREVISION); pertenencia_snss_x_prevision (category = 'pertenencia/prevision'). | category |
| `share_of_discharges / share_of_f84` | Category count divided by the year total within the same dimension and variant. | proportion |

## `deis_f84_subcode_year.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `f84_diag1_code / icd10_label_deis / share_of_f84_any_con_rett / in_variant_sin_rett` | 4-character F84.x subcode in DIAG1, official glosa from the DEIS dictionary sheet 'codigo CIE-10', share of all F84 discharges that year, and inclusion flag for the sin_rett variant (False for F842). | discharges / proportion / boolean |

## `deis_file_integrity.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `utf8_multibyte_pairs` | Count of byte pairs (0xC2-0xF4 followed by 0x80-0xBF); zero confirms ISO-8859-1 encoding despite high bytes (Ñ, á, é, í, ó, ú, ñ). | byte pairs |

## `deis_vs_grd_year.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `variant` | con_rett, sin_rett (config.VARIANTS) and strict_autism_f840 (DIAG1 starts with F840; GRD analogue = module 01 variant strict_autism_f840). | category |
| `deis_f84_principal (and _snss, _no_snss, _suppressed)` | DEIS discharges with F84 (per variant) in DIAG1, overall and by SNSS membership. The homologous GRD quantity is grd_f84_principal (DIAGNOSTICO1). | discharges |
| `grd_records_total, grd_f84_any, grd_f84_principal, grd_f84_secondary_only, grd_hospitals_observed` | From grd_year_summary.csv rows with panel = observed, activity = all: n_episodes_total_same_panel_activity, n_episodes_f84 at position any/principal/secondary_only, hospitals_n. | GRD episodes / hospitals |
| `grd_*_fixed65, grd_*_hospitalisation, grd_*_hospitalisation_fixed65` | Same quantities on the fixed panel of 65 hospitals (panel = fixed65) and for TIPO_ACTIVIDAD == HOSPITALIZACIÓN (activity = hospitalisation), observed and fixed65 panels. | GRD episodes |
| `grd_rate_f84_any_per_100k_episodes, grd_rate_f84_principal_per_100k_episodes, grd_rate_f84_principal_hospitalisation_per_100k_episodes` | 100000 x GRD F84 count / GRD episodes of the same panel and activity. | per 100,000 GRD episodes |
| `ratio_deis_total_to_grd_total, ratio_deis_f84_principal_to_grd_f84_principal, ratio_deis_f84_principal_snss_to_grd_f84_principal, ratio_deis_f84_principal_snss_to_grd_f84_principal_hospitalisation, ratio_grd_f84_any_to_deis_f84_principal` | Coverage ratios between the two unlinked registries (DEIS all establishments or SNSS only vs GRD public hospitals). Descriptive comparability indicators, not probabilities or conversion rates. | ratio |
| `grd_source` | Provenance of the GRD columns: 'outputs/tidy/grd_year_summary.csv (módulo 01_grd_core)' or 'config.CONTROLS (...)' fallback. | text |

## `deis_year_summary.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `discharges_total` | Number of DEIS hospital-discharge records in the year file (all establishments, SNSS and non-SNSS, including masked rows). Equals file lines minus header. | discharges (records) |
| `f84_diag1` | Discharges whose principal diagnosis DIAG1 (normalised: upper case, no dots) starts with F84; for variant sin_rett excludes codes starting with F842. | discharges |
| `f84_diag2` | Discharges with an F84 code in DIAG2. DIAG2 is the external-cause field (ICD-10 V01-Y98), so this is 0 by construction and kept as a control. | discharges |
| `f84_any` | Discharges with F84 in DIAG1 or DIAG2 (= f84_diag1 in DEIS). | discharges |
| `f84_principal_share / f84_secondary_only_share` | f84_diag1 / f84_any and (f84_diag2 - f84_both_positions) / f84_any; 1.0 and 0.0 in DEIS because secondary diagnoses are not published. | proportion |
| `f84_rett_f842_diag1` | Discharges with DIAG1 starting with F842 (Rett syndrome); identical in both variants for information, excluded from f84_any under sin_rett. | discharges |
| `f84_deaths` | F84 discharges (per variant) with CONDICION_EGRESO == 2 (fallecido). | discharges |
| `discharges_snss / discharges_no_snss / discharges_suppressed; f84_any_snss / f84_any_no_snss / f84_any_suppressed` | Splits by PERTENENCIA_ESTABLECIMIENTO_SALUD: SNSS = 'Pertenecientes al Sistema Nacional de Servicios de Salud'; NO_SNSS = 'No pertenecientes...' (private clinics, armed forces, mutuales, delegated administration); SUPRIMIDO = '*'. | discharges |
| `masked_rows_share` | discharges_suppressed / discharges_total: share of records whose demographic fields DEIS replaced with '*'. | proportion |

## `deis_year_summary.csv, deis_age_sex_year.csv, deis_age_who_year.csv, deis_establishment_year.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `rate_per_100k_discharges, rate_lo95, rate_hi95` | 100000 x f84_any / discharges_total of the same year, layout and stratum; exact Poisson (chi-square) 95% limits via epi_helpers.crude_rate. | per 100,000 discharges |

## `deis_year_summary.csv, deis_file_integrity.csv` (módulo 01b_deis_egresos)

| Variable | Definición | Unidad |
|---|---|---|
| `extra_field_rows` | Rows with more ';'-separated fields than header columns (2022 free-text glosas); retained by positional cut. | rows |

## `education_summary_year` (módulo 05_education)

| Variable | Definición | Unidad |
|---|---|---|
| `pie_*_n` | Annual PIE/SINACES counts copied from pie_series (strict, asperger, harmonised adopted, harmonised SINACES-printed, special schools, totals, exceptional entry) | students |
| `pie_*_pct` | TEA shares: of PIE enrolment (Apuntes 60, 2019-2023) and of PIE applicants (SINACES, 2022-2025) | percent |
| `junaeb_{level}_tea_n, junaeb_{level}_pct_weighted(_lo/_hi), junaeb_{level}_pct_unweighted, junaeb_{level}_estimable, junaeb_{level}_n_students` | Per-level JUNAEB results for sex=all copied from junaeb_tea_year_level | students / percent / flag |

## `fonasa_beneficiaries_comuna_tramo_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `tramo` | FONASA income tramo A, B, C or D as given (TRAMO or TRAMO_FONASA column). | category |
| `inscrito_aps` | INSCRITO_APS as given ('Si'/'No') for 2018-2022; 'not_available' from 2023 when the variable disappears. | category |

## `fonasa_beneficiaries_comuna_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `beneficiaries` | FONASA beneficiaries in the December cut (MES_INFORMACION=YYYY12), summed from CUENTA_BENEFICIARIOS (2018-2023) or BENEFICIARIOS (2024-2025) without dropping duplicate rows. | persons (December stock) |
| `comuna_raw` | Comuna name exactly as given in the FONASA file (mixes comuna of the APS enrolment centre for inscritos and domicile for non-inscritos); '(missing)' when absent. | text |
| `age_band_raw` | EDAD_TRAMO label as published (23 bands 2018-2022 and 2025; 10 ten-year bands 2023; 18 bands 2024). | text |
| `age_band_5y` | WHO 5-year band derived only when the raw band lies entirely inside one 5-year band (00-02 and 03-04 -> 0-4; 80+ for any band starting at 80 or above); missing otherwise (e.g. 2023 ten-year bands, 'S.I.'). | category |
| `age_band_10y` | Ten-year band (0-9 ... 70-79, 80+) derived when the raw band fits inside it; available for all years. | category |

## `fonasa_beneficiaries_national_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `dimension / category` | National total by one original dimension at a time (TOTAL, TITULAR_CARGA, NACIONALIDAD, TIPO_ASEGURADO, INSCRITO_APS, TRAMO, SEXO, EDAD_TRAMO), categories upper-cased as given. | persons |

## `fonasa_schema_by_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `n_exact_duplicate_rows_kept` | Number of rows identical on every visible column in the raw file; they are additive fragments and were retained. | rows |

## `grd_activity_categories_year` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `tipo_actividad_raw / activity` | Raw TIPO_ACTIVIDAD value and its analytical class; n_episodes (all) and n_f84_any_con_rett. | episodes |

## `grd_age_sex_year` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `sex` | SEXO as published (HOMBRE, MUJER; 1/2 mapped) or 'unknown' (DESCONOCIDO/empty). | category |
| `age_group` | WHO 5-year group of age at admission = floor((FECHA_INGRESO − FECHA_NACIMIENTO)/365.25); 'unknown' when a date is unparseable or age <0 or >110. | category (0-4 … 75-79, 80+, unknown) |
| `n_f84 / n_total_episodes` | F84 episodes (variant, position, panel, activity) and all episodes (panel, activity) in the sex × age cell; full grid with zeros so that sums equal year totals. | episodes |

## `grd_coding_depth_year` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `depth_bin` | Coding depth bin: 0 (only when present), 1, 2, 3, 4, 5, 6-7, 8-10, 11+. | category |
| `share_f84_within_bin` | n_f84_any / n_total within the bin (proportion); rate_per_100k_episodes with Poisson limits is the same quantity per 100,000. | proportion / per 100,000 episodes |

## `grd_fixed_panel_hospitals` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `in_fixed_panel / present_YYYY / n_years_present` | Whether the hospital is in the 65-hospital fixed panel (present in 2019–2022), presence per year, number of years with ≥1 episode. | boolean / count |

## `grd_hospital_year` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `n_episodes_total / n_episodes_hospitalisation / n_episodes_cma / n_episodes_other` | All GRD episodes of the hospital-year, overall and by activity class. | episodes |
| `n_f84_any / n_f84_principal / n_f84_any_hospitalisation / n_f84_any_cma` | Episodes with F84 (variant) in any position, in DIAGNOSTICO1, and in any position within strict hospitalisation / CMA. | episodes |
| `coding_depth_mean / coding_depth_mean_f84` | Mean non-empty diagnosis fields per episode, all episodes / F84 episodes of the hospital-year. | diagnoses per episode |
| `persons_within_year_f84_any` | Distinct valid identifiers among the hospital-year's F84 episodes. | persons (identifiers) |
| `hospital_name / hospital_name_source / in_fixed_panel` | Name from GRD master tables (grd_master), DEIS catalogue (deis_catalogue) or the code itself (code); membership of the fixed panel of 65. | text / category / boolean |

## `grd_identifier_audit` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `n_unique_ids / id_length_mode` | Distinct valid identifiers among F84 episodes of the year and modal string length of those identifiers (6 in 2019–2020, 8 from 2021). | identifiers / characters |
| `n_f84_ids_shared_with_previous_year` | Informational count of F84 identifiers also present among the previous year's F84 identifiers (0 between 2020 and 2021); never used to deduplicate. | identifiers |
| `n_f84_exact_duplicates_on_read_columns` | F84 rows identical on the 45 analysed columns (identifier, hospital, sex, dates, comuna, activity, admission/discharge type, 35 diagnoses); not removed. | rows |

## `grd_subcode_year` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `subcode / position / n_episodes` | Normalised ICD-10 subcode (F840…F849); position principal (DIAGNOSTICO1), secondary (DIAGNOSTICO2..35) or any; an episode counts once per subcode and position. | episodes |
| `variants` | Pipe-separated list of variants whose code set contains the subcode (F842 → con_rett only; F840 → all three). | text |

## `grd_year_summary` (módulo 01_grd_core)

| Variable | Definición | Unidad |
|---|---|---|
| `variant` | Case-definition variant: con_rett = any of F84, F840–F845, F848, F849 (config.VARIANTS['con_rett']); sin_rett = same without F842; strict_autism_f840 = F840 only (identical in both variants). | category |
| `panel` | observed = every hospital with ≥1 episode in the year (65, 65, 65, 65, 68, 72); fixed65 = the 65 hospitals present in all of 2019–2022. | category |
| `activity` | TIPO_ACTIVIDAD class: all (no filter), hospitalisation (== 'HOSPITALIZACIÓN'), cma (== 'CIRUGÍA MAYOR AMBULATORIA (CMA)'), other (2019 only: emergency/day hospitalisation, unknown, not identified). | category |
| `position` | any = F84 in DIAGNOSTICO1..35; principal = F84 in DIAGNOSTICO1; secondary_only = F84 in DIAGNOSTICO2..35 and not in DIAGNOSTICO1; principal_and_secondary = both. | category |
| `n_episodes_f84` | GRD episodes (rows, no deduplication) with documented F84 for the variant/position within the panel and activity. | episodes |
| `n_episodes_total_same_panel_activity` | All GRD episodes of the same year, panel and activity (denominator). | episodes |
| `rate_per_100k_episodes` | 100000 × n_episodes_f84 / n_episodes_total_same_panel_activity; rate_lo/rate_hi = exact Poisson (chi-square) 95% limits of the numerator divided by the fixed denominator. | episodes with F84 per 100,000 GRD episodes |
| `persons_within_year` | Distinct valid identifiers (CIP_ENCRIPTADO 2019–2023, ID_BENEFICIARIO 2024) among the cell's F84 episodes within the year; never deduplicated across years. | persons (identifiers) |
| `n_f84_without_valid_id` | F84 episodes in the cell whose identifier is empty or a placeholder ('DESCONOCIDO', 'SIN INFORMACIÓN', etc.). | episodes |
| `coding_depth_mean_all / coding_depth_median_all` | Mean / median number of non-empty DIAGNOSTICO1..35 fields (after normalisation) across all episodes of the panel and activity. | diagnoses per episode |
| `coding_depth_mean_f84 / coding_depth_median_f84` | Same statistic restricted to the cell's F84 episodes. | diagnoses per episode |
| `hospitals_n` | Distinct COD_HOSPITAL with ≥1 episode in the panel and activity. | hospitals |

## `ine_population_base_comparison` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `ratio_base2024_to_base2017_30jun` | Base-2024 national projection at 30 June divided by base-2017 national projection at 30 June, same year. | ratio |

## `ine_population_comuna_year_age_sex` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `population` | INE projected resident population at 30 June of the year, base Censo 2017, by comuna, sex and WHO 5-year age group. | persons |
| `age_group` | WHO 5-year groups 0-4 ... 75-79 and 80+ (INE single age 80 is the open group 80+). | category |
| `sex` | HOMBRE (INE Sexo=1) or MUJER (Sexo=2); aggregates add TOTAL. | category |
| `population_base` | Population source: base2017 (INE comunal projections base Censo 2017), censo2024 (Censo 2024 enumerated population), base2024_national (INE national projections base 2024). Never combine across bases. | category |

## `ine_population_sensitivity` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `reference_date` | Date the population refers to: 30 June (base 2017), 1 January or 30 June (base 2024), or the 2024 census enumeration. | date/text |

## `isapre_beneficiaries_comuna_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `cotizantes / cargas / beneficiarios` | ISAPRE contributors, dependants and beneficiaries with valid benefits in December; beneficiarios = Beneficiarios sheet (2019-2020, includes nonatos) or cotizantes + cargas (2021-2025, derived). | persons (December stock) |
| `sex` | View of the workbook: TOTAL (Total/unsexed sheets), MUJER, HOMBRE, SIN_INFORMACION (2021+ 'SI' sheets). TOTAL equals the sum of the sex views; sum only within one view. | category |
| `age_band_raw` | Age band as published: '0-4' ... '95-99', '>=100', 'S/I' (2021+); 'Edad 1-4', 'Edad 5-9', ..., 'Edad 80-100' for the collapsed single-year columns of 2019-2020; 'Nonatos o sin clasificar'. | text |
| `age_band_5y` | WHO 5-year band (80+ open) plus 'not_informed' (S/I) and 'nonatos_sin_clasificar'; 2019-2020 mapping assumes 'Edad 1' = ages 0-1 and 'Edad 100' = 100+. | category |
| `row_type` | 'comuna' for named comunas; 'placeholder' for 'sin dato'/'Sin dato Comuna'/'Sin Codigo de Comuna' rows kept for completeness (unmatched). | category |

## `junaeb_items_dictionary` (módulo 05_education)

| Variable | Definición | Unidad |
|---|---|---|
| `role` | filter_prolonged_medical_diagnosis, tea_category, expansion_weight, sex, grade, other_category (each remaining category of the chronic-condition item) | category |
| `wording / value_codes_observed / value_labels` | Verbatim label from the annual dictionary or questionnaire; observed value distribution in the microdata (top codes with counts); dictionary value labels where published (2021, 2025) | text |

## `junaeb_tea_year_level` (módulo 05_education)

| Variable | Definición | Unidad |
|---|---|---|
| `level` | School cohort file: parvularia (NT1/NT2), basico1 (1o basico), basico5 (5o basico), medio1 (1o medio) | category |
| `sex` | all, female, male (categories with n<5 suppressed); sex from SEXO | category |
| `item_variable / item_wording` | Variable capturing the TEA category of the prolonged-medical-diagnosis item (2023: T_E_A/TRASTORNO_ESPECTRO_AUTISTA/DIAGNOSTICO_TEA; 2024: C30_11/D15_11; 2025: D14_11) and its verbatim wording; ABSENT for 2019-2022 | text |
| `filter_variable / filter_wording` | Filter question '¿ha sido diagnosticado/a por un medico con alguna enfermedad o condicion ... por un periodo prolongado de tiempo?' (verbatim per year) and its variable | text |
| `weight_variable` | Expansion factor: EXP_REG (2024, 'factor de expansion regional'), EXP (2025, 'factor de expansion'); ABSENT 2019-2023 | text |
| `n_rows, n_filter_yes, n_filter_no, n_filter_dontknow, n_missing_item` | File-level counts (same on all/female/male rows): rows in file; caregivers answering Si / No / No sabe to the filter; filter blank (item not answered) | students |
| `n_students` | Students in the estimation domain (rows with valid weight in 2024-2025; all rows otherwise), by sex | students |
| `n_weight_missing` | Rows with missing/non-numeric expansion weight (excluded from weighted estimates); NaN when no weight exists | students |
| `n_tea_unweighted` | Unweighted count of students whose caregiver marked the TEA category | students |
| `proportion_unweighted_pct, lo_unweighted_pct, hi_unweighted_pct` | 100 x n_tea_unweighted / n_students with Wilson 95% CI | percent |
| `proportion_weighted_pct, se_pct, lo_pct, hi_pct` | Weighted proportion of TEA reported among all students with a valid weight (filter No/No sabe/blank = not reported); SE by Taylor linearisation with independent students (ignores school clustering); logit 95% CI | percent / percentage points |
| `weighted_tea_total, weighted_population` | Sum of weights for TEA-reported students and for the domain (expanded counts under the JUNAEB regional expansion factor) | weighted students |
| `n_answered, proportion_weighted_answered_pct, se_answered_pct, lo_answered_pct, hi_answered_pct` | Sensitivity: same estimator with the denominator restricted to students whose caregiver answered the filter Si or No (excludes No sabe and blank) | students / percent |
| `share_tea_among_diagnosed_pct` | 100 x TEA-reported / students whose caregiver answered Si to the filter (unweighted, descriptive) | percent |
| `estimable` | yes = weighted estimate available; unweighted_only = item exists but no weight (2023); no = no TEA item (2019-2022) or item entirely empty (2024 1o medio) | flag |
| `runtime_seconds` | Wall-clock seconds to read and process the file | seconds |

## `pie_series` (módulo 05_education)

| Variable | Definición | Unidad |
|---|---|---|
| `series` | Name of the extracted or derived series (e.g. pie_tea_strict, pie_tea_asperger, pie_harmonised, pie_harmonised_sinaces, special_schools_autism, pie_total_enrolment, pie_total_applicants_sinaces, *_female/_male, *_share_*_pct, *_published) | label |
| `value` | Published or derived value for (year, series); students for count series, percent for *_pct series | students or percent (see unit column) |
| `pie_tea_strict` | Students enrolled in PIE with permanent SEN category 'Trastorno del Espectro Autista (P)' in functioning establishments (Apuntes 60 Tabla 6, p.11) | students (annual school stock) |
| `pie_tea_asperger` | Students enrolled in PIE with category 'Trastorno del Espectro Autista - Asperger (P)' (Apuntes 60 Tabla 6) | students |
| `pie_harmonised` | Adopted harmonised series TEA + TEA-Asperger: 2019-2023 = Apuntes 60 category sum (2022 = 42,940 by explicit rule), 2024-2025 = SINACES Tabla 1 PIE row | students |
| `pie_harmonised_sinaces` | Autistic students in PIE as printed by SINACES Tabla 1 (2022 = 42,945) | students |
| `special_schools_autism` | Students enrolled in Escuelas Especiales de Autismo (SINACES Tabla 1) | students |
| `sinaces_total_minus_special` | SINACES total autistic students minus special-school students (derived; equals Apuntes 60 sum in 2022) | students |
| `pie_total_enrolment` | Total students integrated in PIE, all SEN (Apuntes 60 Tabla 6 total row; equals Tablas 2-5) | students |
| `pie_total_applicants_sinaces` | Total PIE applicants ('postulantes'), all SEN (SINACES Tabla 2) | students |
| `pie_tea_regular_entry / pie_tea_exceptional_entry` | Autistic PIE applicants by regular entry (Decreto 170 quota) vs exceptional entry (Seremi authorisation), SINACES Tabla 2 | students |
| `pie_tea_strict_share_of_pie_pct / pie_harmonised_share_of_pie_pct` | 100 x TEA (or TEA+Asperger) / pie_total_enrolment, computed from Apuntes 60 Tabla 6 | percent of PIE students |
| `pie_tea_share_of_applicants_pct` | 100 x autistic applicants / total applicants, computed from SINACES Tabla 2 (published value in *_published_pct) | percent of PIE applicants |
| `*_female / *_male / *_female_share_pct` | 2023 counts by gender for TEA, TEA-Asperger and PIE total (Apuntes 59 Tabla 2, students with gender information only) and derived female share | students / percent |
| `source_sha256, pdf_page, table_or_figure_caption, derived` | Provenance: SHA-256 of the source PDF, physical page (= printed page), caption line of the table/figure, and whether the value is derived (sum/ratio) rather than printed | metadata |

## `provenance_manifest_checks.csv` (módulo 00_provenance)

| Variable | Definición | Unidad |
|---|---|---|
| `manifest` | Manifest providing the entry (empty string = artefact not listed in any manifest) | text |
| `sha256_match` | manifest_sha256 == observed_sha256 (boolean; empty when not listed) | boolean |
| `bytes_match` | manifest_bytes == observed_bytes (boolean; empty when the manifest carries no size) | boolean |
| `manifest_date` | Date recorded by that manifest for the file (empty when the manifest is undated) | date |
| `manifest_note` | Manifest status (downloaded/adopted/verificado_existente), source URL, source zip/member or record count carried from the manifest | text |

## `provenance_summary_by_source.csv` (módulo 00_provenance)

| Variable | Definición | Unidad |
|---|---|---|
| `n_artefacts` | Number of artefacts found on disk for the source_id | count |
| `bytes_total / gb` | Sum of on-disk bytes for the source_id (gb = bytes/1e9, 3 decimals) | bytes / GB |
| `n_listed_in_manifest, n_sha_match, n_sha_mismatch` | Artefacts of the source listed in at least one manifest, and among them those whose recomputed SHA-256 matches / mismatches | count |

## `rem20_establishment_year` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `discharges` | Sum of NUMERO_EGRESOS over all functional areas and months of the year (episodes leaving the establishment: discharged, transferred out or died). | discharges (episodes) |
| `bed_days_available / bed_days_occupied / days_of_stay` | Sums of DIAS_CAMAS_DISPONIBLES, DIAS_CAMAS_OCUPADAS and DIAS_ESTADA over areas and months. | bed-days / patient-days |
| `months_reported` | Number of distinct months (1-12) with at least one REM-20 row for the establishment in the year. | months |
| `in_panel_188` | True for the 188 establishments with 12 months reported in every year 2019-2025. | boolean |

## `rem20_panel` (módulo 03_denominators)

| Variable | Definición | Unidad |
|---|---|---|
| `retention_discharges` | Discharges of the 188-establishment panel divided by all REM-20 discharges of the year; activity/capacity sensitivity, not population coverage. | proportion |

## `rem_a05_age_sex_annual` (módulo 02_rem_pathway)

| Variable | Definición | Unidad |
|---|---|---|
| `sex, age_group, source_col, count` | Sum over in-era A05 rows of the age×sex cell: COL(4+2k)=Hombres and COL(5+2k)=Mujeres for WHO group k (0-4 … 75-79, 80+); age_group='total' uses COL02 (Hombres) and COL03 (Mujeres); NaN if no cell present. | entries reported / exits reported |
| `flow, category, variant` | entry/exit; category autism, asperger, rett, disintegrative, pdd_nos, broad_pdd or pdd_family; variant single_code or con_rett/sin_rett family sum (code = joined codes). | categorical |
| `n_rows, n_rows_cell_present` | Rows aggregated and rows in which the specific cell was non-empty. | rows |

## `rem_code_dictionary_check` (módulo 02_rem_pathway)

| Variable | Definición | Unidad |
|---|---|---|
| `found_in_dictionary, in_era` | Whether the code row (with a COL01 token) exists in the year's dictionary sheet; whether that year is within the code's era (expected pattern: found iff in era). | boolean |
| `label, section` | Dictionary text of the code row before the COL tokens (merged group label prepended in brackets when column B is blank) and the nearest 'SECCIÓN' title above it. | text |
| `col01_meaning, col02_meaning, col03_meaning, col04_meaning, col37_meaning` | Header texts above the COLxx token (top to bottom, joined by ' / ') after hierarchical forward-fill of merged header cells, e.g. 'TOTAL / Ambos Sexos', '18 - 23 meses / Hombres', 'Nº DE INTERVENCIONES'. | text |
| `age_columns, layout_check, n_col_tokens` | Age labels of COL04..COL37 (pairs Hombres/Mujeres), programmatic check of the expected layout per module ('ok' or a description), and number of distinct COL tokens in the row. | text / count |

## `rem_establishment_year` (módulo 02_rem_pathway)

| Variable | Definición | Unidad |
|---|---|---|
| `months_with_rows, months_value, months_zero, months_empty, n_rows` | Per establishment×year×code: distinct months with a row and the number of rows by state. | months / rows |
| `annual_total` | Serie A only: sum over months of total_known (COL01+COL02 for A03, COL01 otherwise); NaN for Serie P (stocks are not summed). | as code unit |
| `december_value, june_value, has_december_row, has_june_row` | Serie P only: COL01 in MES=12 and MES=06 and whether the corresponding row exists. | people in stock; boolean |
| `in_stable_panel` | Establishment reports the code in every year of the code's era (December for stocks). | boolean |

## `rem_pathway_annual` (módulo 02_rem_pathway)

| Variable | Definición | Unidad |
|---|---|---|
| `variant` | single_code (one REM code); con_rett / sin_rett (config.VARIANTS family sums over A05 entry/exit or P6 primary/specialty categories, with/without Rett codes); strict_autism (05990022, 05990027, P6241010, P6241060); broad_pre2021 (06902600, 05225000, P6223000, P6223380). | categorical |
| `identical_across_variants` | True when the row does not depend on the Rett choice (all rows except con_rett/sin_rett). | boolean |
| `measure, month` | annual_sum (Serie A: sum of months 01-12), december_stock (Serie P, MES=12, primary), june_stock (Serie P, MES=06, sensitivity); December and June are never summed. | categorical |
| `total` | National total of total_known over in-era rows of the code (or family codes) for the year and measure, rows kept as in the file; NaN when no rows exist. | unit column: children reported / screening records / screening results / referral records / entries reported / exits reported / interventions / people in stock |
| `total_dedup` | Same as total but excluding exact duplicate rows (sensitivity). | as total |
| `n_reporting_establishments` | Distinct IdEstablecimiento with at least one row (any state) for the code or family in the year (December rows only for december_stock, June rows for june_stock). | establishments |
| `n_establishments_value_gt0` | Distinct establishments with at least one row with total_known > 0. | establishments |
| `n_rows, n_rows_value, n_rows_zero, n_rows_empty, n_rows_exact_duplicate` | Rows aggregated and their state composition; n_rows_empty counts rows present with empty cells (distinct from absent rows). | rows |
| `months_covered` | Distinct months with at least one row for the code/family in the year (max 12 for A, 1 for each stock measure). | months |
| `n_stable_panel_establishments, stable_panel_total` | Establishments with at least one row for the code/family in every year of its era (December rows for stocks), and the total restricted to those establishments (continuous-panel sensitivity). | establishments; as total |
| `era, era_start, era_end, domain, setting, unit, aggregation_rule, comparability_warning` | Definition era and metadata copied from rem_pathway_codes.csv (family rows: 2021–2025 or 2019–2020 with a family-sum warning). | text |

## `rem_pathway_tidy` (módulo 02_rem_pathway)

| Variable | Definición | Unidad |
|---|---|---|
| `year, month` | Reporting year (=Ano, verified equal to the file year) and month (=Mes, 1–12 for Serie A; 6 or 12 for Serie P). | calendar |
| `series, module, code` | Series A (monthly flow) or P (semiannual stock); REM form (A03, A05, A27, A28, P2, P6); CodigoPrestacion normalised (8-digit zero-padded for Serie A, 'P' + 7 digits for Serie P). | categorical |
| `IdServicio, IdRegion, IdComuna, IdEstablecimiento` | Raw identifiers of the reporting establishment (place of care, not residence) as text; IdComuna keeps the file's digits. | text codes |
| `id_comuna_5d` | IdComuna zero-padded to five digits (DEIS convention); needed because Serie P 2024–2025 drops the leading zero. | 5-digit code |
| `in_era` | True when the row's year lies within the code's definition era in rem_pathway_codes.csv (year_start–year_end); only in-era rows enter the annual tables. | boolean |
| `col01..col50` | Raw text of Col01..Col50 exactly as in the file (empty string = empty cell); the meaning of each column is given per code and year in rem_code_dictionary_check.csv. | raw text |
| `col01_num, col02_num, col03_num` | Numeric conversion of Col01–Col03 (empty cell = NaN, distinct from 0). | count |
| `total_known` | Row total: A03 = COL01 (hombres) + COL02 (mujeres) summed over the cells present (NaN if both empty); all other modules = COL01 (total / Nº de intervenciones). | count per row (children/records, entries, exits, interventions or people in stock, per unit column of the code) |
| `total_rule` | Text of the rule used for total_known. | text |
| `state` | reported_value (total_known > 0), reported_zero (total_known = 0), reported_empty (row present but relevant cells empty); reported_negative reserved (never occurred). Absence of a row is 'not reported' and does not appear. | categorical |
| `a03_one_sex_cell_empty` | A03 rows where exactly one of COL01/COL02 is empty (partial sex reporting). | boolean |
| `exact_duplicate` | True for the second and later occurrences of a row identical on all key and value columns within the file; such rows are kept in totals and excluded from total_dedup. | boolean |
| `key_conflict` | True when the same establishment×month×code key appears with different values (none observed). | boolean |
| `n_nonnumeric_cells, n_negative_cells` | Number of Col01..Col50 cells that are non-empty but not numeric, or negative (both 0 in all rows). | count |

## `survey_design_check.csv` (módulo 04_surveys)

| Variable | Definición | Unidad |
|---|---|---|
| `value / reference / ratio` | Simulation statistic (e.g. mean Taylor SE), its reference (empirical Monte Carlo SE, true proportion, bootstrap SE or nominal 0.95) and value/reference | proportion or ratio |

## `survey_estimates.csv` (módulo 04_surveys)

| Variable | Definición | Unidad |
|---|---|---|
| `domain` | Text label of the estimation domain (survey, population and item); domain_definition gives the exact filter in terms of source variables and codes | text |
| `subgroup_type / subgroup` | total; sex (Hombre/Mujer from sexo); age_group (ENDIDE adults 18-29/30-44/45-59/60+ from edad; ENDIDE NNA 2-5/6-11/12-17; ENCAVI edad5 15-19/20-29/30-49/50-64/65+) | category |
| `estimate_type` | primary (prespecified benchmark), sensitivity (alternative missing-code treatment), secondary (treatment items) | category |
| `item_variable / item_wording / positive_definition` | Source variable, exact wording from codebook/questionnaire, and the code defining a positive plus the codes treated as missing | text |
| `weight_var / strata_var / psu_var` | Design variables used: ENDIDE fexp/estrato/cod_upm; ENCAVI w_personas_cal/varstrat/varunit | text |
| `n` | Unweighted number of respondents in the domain (persons with a valid answer to the item) | persons (unweighted) |
| `cases` | Unweighted number of positives in the domain | persons (unweighted) |
| `proportion` | Weighted domain proportion, ratio estimator sum(w*y*d)/sum(w*d) over all design units | proportion 0-1 |
| `se` | Standard error by Taylor linearisation of the ratio estimator, stratified with-replacement PSU (ultimate cluster) variance (common.survey_proportion) | proportion 0-1 |
| `lo / hi` | 95% confidence limits on the logit scale using t with df = n_psu - n_strata | proportion 0-1 |
| `weighted_total` | sum(w*y*d): estimated persons with the characteristic in the domain | persons (expanded) |
| `weighted_population` | sum(w*d): estimated persons in the domain | persons (expanded) |
| `deff` | Design effect = se^2 / (p*(1-p)/n) with the domain's unweighted n and proportion | ratio |
| `rse` | Relative standard error = se / proportion | ratio |
| `df / n_psu / n_strata` | Degrees of freedom (PSU minus strata) and counts of PSUs and strata of the full design (not of the domain) | count |
| `precision_flag` | 'imprecise' if cases < 30 unweighted, else 'adequate'; deff_note adds DEFF, relative SE and a warning when RSE > 30% | category |
| `variant / variant_note` | 'both': survey items are identical under con_rett and sin_rett because reported autism does not separate Rett syndrome | text |
| `source_file / source_sha256 / source_documents / script` | Provenance: microdata file name, SHA-256 (ENDIDE zip 648490f0...; ENCAVI dta 8616caea...), documentation PDFs and producing script | text |

## `survey_items_dictionary.csv` (módulo 04_surveys)

| Variable | Definición | Unidad |
|---|---|---|
| `variable / variable_label / question_wording` | Source variable name, Stata variable label and question wording (ENDIDE from the codebook; ENCAVI from questionnaire section 4.6 and manual) | text |
| `respondent / universe / response_codes / missing_codes / treatment_in_analysis` | Who answers, skip pattern and universe size, valid codes, missing codes (ENDIDE -99 No responde; ENCAVI 8 No sabe, 9 No responde) and how each is handled in the estimates | text |
