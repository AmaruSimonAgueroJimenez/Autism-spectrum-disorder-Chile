# Output dictionary

Full run: 3 September 2026. Source data: GRD 2019–2024, REM 2017–2024, INE projections based on the 2017 Census, and commune and regional cartography. This folder contains only aggregates and metadata. Patient identifiers are processed in memory and are not exported.

## Audit

| File | Unit and content |
|---|---|
| `grd_source_inventory.csv` | File/year: size, modification and rows; the original hashes are in the external GRD manifest |
| `grd_linkage_by_year.csv` | Year: records, identifiers, missing values and internal demographic inconsistencies |
| `grd_linkage_between_years.csv` | Pair of years: shared identifiers and concordance among the comparable ones |
| `grd_trajectory_quality.csv` | Period: F84 universe before exclusions, duplicates, inconsistent identifiers, ambiguous episodes and invalid dates; overlapping causes |
| `rem_code_catalogue.csv` | Year/code: label, form, section, total rule and exact reference to the dictionary file/sheet/row |
| `rem_quality.csv` | Year: code coverage, duplicates, sex/age checks among complete rows and input metadata |
| `grd_epi_quality.csv` | Year: records read, F84 records, exact duplicates, without identifier, without sex, invalid dates, implausible age, without commune, discharges by death |
| `grd_comuna_unmatched.csv` | Commune-of-residence names not linked to the INE catalogue, with affected records |
| `grd_rates_excluded.csv` | Year/definition: records without sex or age excluded from the rates |
| `grd_rates_regional_coverage.csv` | Year: records with and without an assigned region of residence |
| `catalogo_comunas.csv` | Unique territorial code, name, normalised name, region and continental-commune flag |
| `grd_hospital_catalogue.csv` | Hospital code and name according to the GRD catalogue |

## GRD

All analytical tables carry `era` and `definition`. Periods are neither linked nor added as unique persons. Definitions overlap: they are not added to one another either.

- `autismo_F840`: F84.0.
- `TEA_operacional`: F84.0, F84.1, F84.5, F84.8, F84.9.
- `F84_historico`: F84 and its valid subcategories F84.0–.5, .8 and .9; includes Rett. It is not automatically equivalent to ASD under current clinical classifications.

| File | Unit and denominator |
|---|---|
| `grd_annual_positions.csv` | Year/position: records with identifier after exact deduplication and distinct identifiers within the cell. An ID can appear in several positions/years. Includes the IDs later excluded from the longitudinal cohort |
| `grd_cohort_summary.csv` | One row per period/definition: IDs included after controls, number with prior discharges, groups of interest, age and observation opportunity |
| `grd_first_position.csv` | Position at the first observed discharge with the code: mutually exclusive and exhaustive categories for the cohort |
| `grd_cohort_strata.csv` | Index year, position, sex and age band: cell denominator `patients` |
| `grd_previous_codes.csv` | Prior code by window and position: one ID once per code/window/position. Reference denominator: cohort or IDs with prior discharges, stated explicitly |
| `grd_previous_groups.csv` | Same as prior codes, grouped into exploratory categories. Groups can coexist |
| `grd_first_hospital_principal.csv` | Principal diagnosis of the ID's first observed discharge, which may be the index itself when there is no prior history |
| `grd_last_prior_principal.csv` | Last principal diagnosis strictly before the index admission, among IDs with a prior discharge |
| `grd_index_principal.csv` | Principal diagnosis of the index episode, by position of the ASD code. It is contemporaneous, not prior |
| `grd_sequences.csv` | First principal → last prior principal → index position. Only IDs with prior history and without ties in the two previous stages; not the whole cohort |
| `grd_principal_transitions.csv` | Initial position: later transition to principal. `later_principal_365d / eligible_followup_365d` is the one-year quotient; `later_principal` admits all available follow-up |

ICD-10 codes are kept normalised without a dot. `window=all` corresponds to the whole observable prior period; `365d` and `730d` restrict the dates of prior episodes, but **do not restrict the cohort to persons with those complete windows**. `position=principal` is DIAGNOSTICO1 and `any` includes 1–35. A prior episode must have been discharged before the index admission. Contemporaneous diagnoses are not included as prior history.

`lookback_365d/730d` measures available calendar time from the start of the period; `observed_prior_365d/730d` requires at least one prior discharge at that distance. No variable demonstrates continuous clinical observation. Time to principal is measured from the index discharge to the later admission. Date ties keep all relevant codes, so tables by code can exceed the number of IDs when added.

### Descriptive epidemiology (`grd_epidemiology.py`)

All tables use the definition (`definition`) and the role of the code in the episode (`role`: `principal`, `solo_secundario`, `principal_y_secundario`). A record is an episode after exact deduplication within the year.

| File | Unit and content |
|---|---|
| `grd_epi_strata.csv` | Year/definition/role/sex/age group/normalised commune of residence: records, distinct identifiers in the cell and records without identifier |
| `grd_epi_persons_year.csv` | Year/definition/sex/age group/commune: distinct identifiers in the year (attributes of the first record of the year) |
| `grd_epi_persons_era.csv` | Period/definition/sex/age group/commune: distinct identifiers in the period |
| `grd_epi_age_single.csv` | Year/definition/role/sex/single year of age: records |
| `grd_epi_monthly.csv` | Year/definition/role/month of admission: records |
| `grd_epi_subcodes.csv` | Year/F84 subcategory/position/sex/age group: records; a record counts once per subcategory and position |
| `grd_epi_features.csv` | Year/definition/role/variable/value: records. Raw producer variables and grouped ones (`prevision_grupo`, `nacionalidad_grupo`, `etnia_grupo`, `age_band`, `los_bin`) |
| `grd_epi_los.csv`, `grd_epi_los_summary.csv`, `grd_epi_los_age.csv` | Length of stay in days by year/definition/role/activity type (and age group): n, mean, SD, median, quartiles, P90, maximum, total days and zero-day stays |
| `grd_epi_grd_weight.csv` | Year/definition/role: IR-GRD relative weight (n, mean, median, quartiles) |
| `grd_epi_hospitals.csv` | Year/definition/role/hospital: records and identifiers |
| `grd_epi_codiagnoses.csv` | Year/definition/ASD role/code position/three-character ICD-10 category: records; a record counts once per category and position |
| `grd_epi_readmissions.csv` | Period/definition/year/horizon: discharges with identifier and dates, eligible with available horizon and readmitted with a code of the definition |
| `grd_epi_multiplicity.csv` | Period/definition/number of episodes per identifier: persons and records |

### Rates, trends and spatial statistics (`epi_rates.py`)

Denominators: INE person-years. `unit` distinguishes `records` (episodes) and `persons` (distinct identifiers). Standardised rates use the WHO standard population and gamma limits (Fay–Feuer); crude rates use exact Poisson limits.

| File | Unit and content |
|---|---|
| `population_regional.csv`, `population_comunal` (implicit in the tables), `population_regional_young.csv` | INE population by year, region, sex and age group; and by single year of age 0 to 5 |
| `grd_rates_national.csv` | Year/definition/unit/role/sex (HOMBRE, MUJER, TOTAL): count, population, crude rate and CI, ASR and CI, ASR variance |
| `grd_rates_age_specific.csv` | Definition/unit/year/sex/age group: specific rate and exact CI |
| `grd_sex_ratio.csv` | Definition/unit/role/year: M:F ratio of ASRs (log-normal CI) and of counts (exact binomial CI) |
| `grd_trends_apc.csv` | Definition/unit/role/sex/period: quasi-Poisson average annual percent change, CI, p-value and overdispersion factor |
| `grd_rates_subcodes.csv` | Year/subcategory/position/sex: count, crude rate and ASR with CI |
| `grd_rates_regional.csv` | Unit/period (annual, 2019–2024, 2021–2024)/region of residence/sex: count, person-years, crude rate and ASR with CI |
| `grd_rates_comunal.csv` | Unit/period/commune: count, person-years, crude rate, ASR with CI, expected by indirect standardisation, standardised hospitalisation ratio (SHR) with CI, smoothed SHR (empirical Bayes), shrinkage weight and prior parameters |
| `grd_spatial_moran.csv` | Unit/period/variable (ASR, SHR, smoothed SHR): global Moran's I, expectation, analytical and 999-permutation z and p, communes and islands |
| `grd_spatial_lisa.csv` | Commune: value, spatial lag, local I, quadrant, permutation p, FDR threshold and classification with p < 0.05 and with FDR (cluster labels stored in Spanish: `Alto-Alto`, `Bajo-Bajo`, `Alto-Bajo`, `Bajo-Alto`, `No significativo`) |
| `rem_rates_national.csv` | Year/series (autism 05990022, generic PDD 06902600, totals of entries and discharges of subcategories)/sex: entries per 100 000 population, crude and ASR with CI |
| `rem_rates_age_specific.csv` | Series/year/sex/age group: specific entry rate and CI |
| `rem_rates_regional.csv` | Series/period/facility region/sex: entries, population, crude rate and ASR with CI |
| `rem_grd_ecological.csv` | Region/year 2021–2024: REM entry rates and GRD record and person rates |
| `rem_grd_ecological_comunal.csv` | Commune/period (annual 2021–2024 and pooled 2021–2024): person-years; REM entries of the autism code by facility commune with reporting-commune flag, rows and facilities, crude rate and CI, expected and standardised entry ratio (SER) with CI; GRD records and persons by commune of residence with crude rate and CI, expected and SHR with CI. Expected values use the national sex- and age-specific rates of the same source and period; pooled persons use the mean annual population. Communes without a REM row keep the entry empty, not zero |

## REM

| File | Unit and content |
|---|---|
| `rem_monthly_region_raw_columns.csv` | Year/month/region/code: sums of original columns, rows and reporting facilities |
| `rem_annual_by_code.csv` | Year/code: sums, catalogue, months present and field coverage |
| `rem_a05_age_sex.csv` | Year/code/age band/sex: sums of observed values of A05 columns 04–37; excludes totals and additional subgroups |
| `rem_a05_region_age_sex.csv` | Year/code/region/age band/sex: the same sums by facility region |
| `rem_annual_comuna.csv` | Year/code/region/facility commune: sums of `Col01` to `Col03`, `total_known`, rows, rows with total and reporting facilities |
| `rem_establishment_panel.csv` | Year/code/health service/region/commune/facility: months with a row, rows, months with a positive total, sums of `total_known` and `Col01` |

**Raw columns have no universal semantics.** A05: `Col01` total, `Col02` males, `Col03` females. A03 in the selected sections: `Col01` males, `Col02` females; they are not total and subgroup. A28 is kept by section, without automatically adding the two entry codes.

`total_known` adds the totals of **rows complete for that rule**: in A03 it requires both sex columns, in A05/A28 it requires Col01. `rows_total_known` counts the rows that met that condition. If it is lower than `rows`, `total_known` is not a complete total of the code; do not use it directly as a population denominator or as a national total. Raw columns are aggregated by their observed values with `min_count=1`, so they can represent different coverages. They stay empty when there is no observed value.

`months=12` certifies the presence of the code in twelve months, not the completeness of all facilities. `reporting_establishments` counts facilities with a selected row, not the whole network nor necessarily active facilities with a positive service. Territorial sums do not certify unique persons.

The absence of a row, an empty cell and an explicit zero are distinguished; zero is not imputed automatically. The current results do not compute screening positivity, incidence, prevalence, retention or population rates.
