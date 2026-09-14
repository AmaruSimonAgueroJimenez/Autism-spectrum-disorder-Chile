# Results map — every result of the FULL `sin_rett` manuscript and where it went in the journal submission

Sources: the full manuscript = `prose_en.article("sin_rett", V)` (Results section, 18 paragraphs in 8 subsections, including the three `[OPT]` paragraphs) and its 59 figures (5 body + `supplementary_material.FIGURE_ORDER`, 54) and 132 tables (7 body + `TABLE_ORDER`, 125); the journal = `prose_journal_en.article(V)` (4 figures, 2 tables) and `supplement_journal.blocks("en", V)` (36 figures, 91 tables of which 90 are corpus tables and one, Table S11, is the synthetic STROBE/RECORD checklist). Journal S-numbers are `journal_config.SUPP_FIGURES` / `SUPP_TABLES` positions (order of first citation from the article, asserted ascending by `JournalRegistry.assert_monotone`). Numbers were traced mechanically: every numeric token of each corpus Results paragraph was searched in the journal article blocks and, failing that, in the supplement blocks (text, captions, notes and table cells); the few tokens found in neither are named below with the reason.

Totals: figures 59 = 4 body + 36 supplement + 19 dropped; tables 132 = 2 body (cut) + 88 supplement + 42 dropped (the two body tables reappear in full as Tables S37 and S88, so 90 corpus tables are printed in the supplement; six were restored after the first reading round, see section E). Dropped items stay in the repository named in the data sharing statement and in the full bilingual corpus (`manuscript/manuscript_sin_rett_*.pdf`, `supplement_sin_rett_*.pdf`).

## A. Results text of the full manuscript, paragraph by paragraph

| Corpus subsection | Paragraph (first words) | Words | Numbers | Where in the journal | Not found verbatim (reason) |
|---|---|---|---|---|---|
| Sources and coverage | Figure 2 and Table S1 summarise the sources, and Figure 1 answers, sou… | 238 | 31 (27 in the body, 4 only in the supplement) | body: Results › Sources and coverage (compressed to ≈110 words; Figure 1, appendix Figure S1, Table S14); the June 2020 P2 sentence moved to Results › Pathway ¶3 | — |
| Hospital core: GRD episodes with documented F84 | Episodes with documented F84 in any position numbered 2,334, 1,609, 2,… | 193 | 37 (36 in the body, 1 only in the supplement) | body: Results › Hospital core ¶1 in full (Table 1, Figure 2; appendix Figure S7, Tables S36–S37) | — |
| Hospital core: GRD episodes with documented F84 | The increase was not only a by-product of deeper coding: within each c… | 91 | 15 (13 in the body, 2 only in the supplement) | body: Results › Hospital core ¶2 (Figure 2c; appendix Figure S8, Table S38) | — |
| Hospital core: GRD episodes with documented F84 | In 2024 the highest rate per 100,000 episodes was in the 5–9-year age … | 98 | 16 (14 in the body, 2 only in the supplement) | body: Results › Hospital core ¶3 (Figure 2d; appendix Tables S39–S40) | — |
| Hospital core: GRD episodes with documented F84 | [OPT] [OPT] Hospitals were heterogeneous: in 2024 the rate ranged from 67.9 … | 96 | 11 (9 in the body, 2 only in the supplement) | body: Results › Hospital core ¶4 (compressed; Figure 2e; appendix Figures S9–S11, Tables S41–S44) — the hospital names leave the text (Table S41 lists them) | — |
| Hospital core: GRD episodes with documented F84 | [OPT] [OPT] DEIS discharges with F84 as principal diagnosis in all establish… | 71 | 11 (11 in the body, 0 only in the supplement) | body: Results › Hospital core ¶4, DEIS sentence (appendix Figures S12–S13, Tables S46–S49) with the 'coverage comparison … not a probability' wording | — |
| Aggregate administrative pathway in primary and specialty care | Table 2 and Figure 4 present the REM modules by era with their reporti… | 83 | 5 (5 in the body, 0 only in the supplement) | body: Results › Pathway ¶1 (Figure 3; appendix Table S50–S51) | — |
| Aggregate administrative pathway in primary and specialty care | [OPT] [OPT] In the legacy A03 era, M-CHAT screening among children with a la… | 90 | 22 (7 in the body, 12 only in the supplement) | partly body (the 2023–2025 high-risk and referral clause of ¶1) and supplement: Figure S14/Table S52 (risk and referral by era), Figure S15/Table S53 (every A03 code by era), Table S50 | 19 632, 25 074, 19 289 = annual totals of M-CHAT-R/F records 2023–2025 (`a03_2023_risk_total_2023/2024`, `a03_2025_risk_total_2025`), sums over the risk classes; the classes are printed in Figure 3a–b, Figure S14 and Tables S50/S51, the totals are not printed |
| Aggregate administrative pathway in primary and specialty care | Strict-autism entries to mental-health programmes (A05) rose from 2,08… | 123 | 24 (21 in the body, 2 only in the supplement) | body: Results › Pathway ¶2 (appendix Figures S16–S20, Tables S54–S59) | 39 771 = five-year total of A05 entries (`a05_autism_entries_total_2021_2025`), a sum of the five annual values printed in the body |
| Aggregate administrative pathway in primary and specialty care | The December stock of children and adolescents with autism under contr… | 196 | 31 (23 in the body, 8 only in the supplement) | body: Results › Pathway ¶3 with the June 2020 sentence (appendix Figures S21–S24, Tables S60–S64) | — |
| Coverage and denominator layers | [OPT] [OPT] The INE resident population grew from 19.11 million to 20.21 mil… | 177 | 27 (7 in the body, 14 only in the supplement) | supplement: the coverage layers are Methods › Denominators (Table S25, Figure S3/Table S26, Figures S4/Table S32); the paragraph itself is not in the body (was body Table 3 + [OPT] text) | 19·11/20·21 million INE residents are printed as 19·1/20·2 million in Methods (same keys, one decimal); 14·84/17·13 million FONASA and 13·78/15·79 million APS enrolled are derived from the December counts printed in Table S25 (rows FONASA beneficiaries, enrolled in APS); the 8·7% Census effect is derived from `ine_ratio_censo2024_base2017_2024` (Table S25/S26) and no longer printed |
| Population benchmarks | With the complex design, ENDIDE 2022 estimated reported autism in 0.29… | 160 | 31 (26 in the body, 5 only in the supplement) | body: Results › Population benchmarks (Figure 4c; appendix Table S65, Figure S25/Table S66) | — |
| Educational triangulation | Autistic students registered in the PIE rose from 11,877 (strict ASD) … | 128 | 21 (17 in the body, 4 only in the supplement) | body: Results › Educational triangulation ¶1 (Figure 4a; appendix Table S67, Figure S26/Table S68) | — |
| Educational triangulation | In JUNAEB's whole-cohort caregiver survey, the weighted percentage of … | 104 | 9 (9 in the body, 0 only in the supplement) | body: Results › Educational triangulation ¶2 (Figure 4b; appendix Figure S27/Table S69) | — |
| Convergence across systems and sensitivity of the trends | Indexed to 2021 = 100, the GRD rate of episodes with F84 stood at 278 … | 72 | 7 (7 in the body, 0 only in the supplement) | body: Results › Convergence ¶1 (Figure 4d–e; appendix Tables S85–S87, Figure S34) | — |
| Convergence across systems and sensitivity of the trends | Table 6 gives the pre-specified models. The APC of GRD episodes with F… | 233 | 45 (44 in the body, 1 only in the supplement) | body: Results › Convergence ¶2 (Table 2, Figure 4f; appendix Figure S35, Tables S88–S89) | — |
| Convergence across systems and sensitivity of the trends | [OPT] [OPT] Strict-autism A05 entries grew at 47.2% (95% CI 27.4 to 70.0) pe… | 183 | 43 (37 in the body, 5 only in the supplement) | body: Results › Convergence ¶3 (compressed: every APC with its CI; the dispersions are in Table 2) | 355·7 = Pearson dispersion of the A05 per-resident model, printed as 355·73 in Table 2 (cell of `T7_models.csv`) |
| Convergence across systems and sensitivity of the trends | The 205 reproduction controls of the analysis plan (191 matched, 14 di… | 23 | 3 (3 in the body, 0 only in the supplement) | body: Results › Convergence ¶4 (appendix Tables S34–S35) | — |

The Results › Territory paragraph of the journal is NEW (plan section 3): every number comes from `outputs/tidy/spatial_{moran,lisa,inequality,correlations}.csv` through `journal_config.tidy_value`/`tidy_count`; it summarises Figures S28–S33 and Tables S70–S84, which the full manuscript printed only in its supplement.

Second reading round (2026-09-09, CLOSE ROUND 2): every percentage of the Introduction and the Results now prints its numerator and base beside it, from named keys or tidy rows — FONASA/ISAPRE coverage (`fonasa_beneficiaries_{2019,2025}`, `isapre_beneficiaries_2025`, `ine_pop_total_{2019,2025}`, printed as millions to one decimal), the Census ratio (`censo2024_enumerated` of `ine_pop_total_2024`), the NANEAS shares (`p2_tea_dec_{2023,2025}` of `p2_naneas_dec_{2023,2025}`), the June 2020 cut (`p2_tea_jun_2020` against `p2_tea_dec_2020`), the physician-confirmed share (`svy_endide_children_confirmed_among_reported_total_{cases,n}`), the PIE shares (`pie_tea_strict_{2019,2023}` of `pie_total_enrolment_{2019,2023}`), the seven JUNAEB proportions (`junaeb_<level>_all_tea_n_<year>` / `junaeb_<level>_all_n_answered_<year>`, unweighted cases/respondents) and the top-decile share (the base `total_count` of `spatial_inequality.csv`; its numerator is not a tidy value and is not hand-derived). Two further documented derivations join the Census effect and the ENDIDE male:female ratio: (3) the GRD age-band numerators of 2024 (`prose_journal_en.grd_age_count`: sums of the sex × five-year cells of `outputs/tidy/grd_age_sex_year.csv` for the observed panel, any position, all activity, with the episodes of known age as the base, asserted equal to `grd_f84_any_share_age_{0_9,20plus}_2024` to four decimals before printing), and (4) the A05 entries aged 0–9 in 2025 (`a05_autism_entries_both_0_4_2025` + `a05_autism_entries_both_5_9_2025`, asserted against `a05_autism_entries_share_age_0_9_2025`). The coding-depth sentence no longer prints a bare median (no interquartile range is computed by the pipeline): it points to the mean-depth inset of Figure 2c, whose legend now says «means only; no dispersion is drawn».

## B. Figures of the full manuscript (59)

| Corpus label | Key | Title (corpus) | Journal | Note / reason |
|---|---|---|---|---|
| Figure 1 | `fig1_dataflow` | What was done with each database: the six data families of the multisource study, Chile 2019–2025 | body: Figure 1 | journal plate mode (no in-graph titles) |
| Figure 2 | `fig1_sources_coverage` | Administrative reporting completeness, coverage layers, panels and definition breaks of the multisource study, Chile 201 | supplement: Figure S1 | relocated (was a body figure) |
| Figure 3 | `fig2_grd_core` | GRD episodes with documented F84 in Chilean public hospitals, 2019–2024: rates per episode, activity, coding depth, age  | body: Figure 2 | journal plate mode (no in-graph titles) |
| Figure 4 | `fig3_rem_pathway` | Aggregated REM administrative pathway for autism in the Chilean public network, 2019–2025: detection (A03), counselling, | body: Figure 3 | journal plate mode (no in-graph titles) |
| Figure 5 | `fig4_triangulation` | Educational triangulation and population benchmarks of administrative autism recognition, Chile 2019–2025 | body: Figure 4 | journal plate mode (no in-graph titles) |
| Figure S1 | `figS1_grd_variants` | Sensitivity of the GRD series to the inclusion of Rett syndrome (F84.2): full F84 versus F84 without Rett, 2019–2024 | dropped | duplicate of Figure S2 (figE28_variant_sensitivity: every series in both variants) |
| Figure S2 | `figS2_grd_subcodes` | F84 subcode composition and code position in GRD episodes, 2019–2024 | supplement: Figure S7 | kept |
| Figure S3 | `figS3_grd_hospital_effects` | Heterogeneity across GRD hospitals: hospital effects, coding depth and rates 2019 versus 2024 | supplement: Figure S9 | kept |
| Figure S4 | `figS4_models_cpa` | Quasi-Poisson models of administrative recognition of autism: GRD, REM, education and DEIS, Chile 2019–2025 | supplement: Figure S35 | kept |
| Figure S5 | `figS5_rem_june_december` | REM June versus December stocks (P2 ASD, P6 primary care and specialty), 2019–2025: semester sensitivity, never summed | supplement: Figure S22 | kept |
| Figure S6 | `figS6_rem_stable_panel` | Stable establishment panel versus all reporting establishments in REM A05, P2 and P6, 2019–2025 | supplement: Figure S16 | kept |
| Figure S7 | `figS7_rem_education_models` | REM A05 by age and sex, P2/P6 stocks and PIE: standardised rates and log-linear fits, 2019–2025 | supplement: Figure S18 | kept |
| Figure S8 | `figS8_a05_age_sex` | REM A05 entries by age group and sex per year, 2021–2025: strict autism and the variant's PDD family | supplement: Figure S19 | kept |
| Figure S9 | `figS9_regional_maps` | Regional distribution of administrative recognition: GRD by region of residence (both variants) and REM A05 by region of | supplement: Figure S28 | kept |
| Figure S10 | `figS10_denominators` | Sensitivity of population denominators: INE base 2017 vs Census 2024 and base 2024 | supplement: Figure S3 | kept |
| Figure S11 | `figS11_coverage_age_sex` | Coverage layers: FONASA, APS enrolment and ISAPRE by age and sex (2025) and national series 2019–2025 | supplement: Figure S4 | kept |
| Figure S12 | `figS12_junaeb_sex_level` | JUNAEB: caregiver-reported ASD by sex and school level, 2023–2025 | supplement: Figure S27 | kept |
| Figure S13 | `figS13_rem_seasonality` | Monthly seasonality of REM reporting: A05 entries and A03 screening by year, index relative to each year's monthly mean | supplement: Figure S23 | kept |
| Figure S14 | `figS14_deis_sex_age` | DEIS hospital discharges with F84 as principal diagnosis by sex, age and ownership, 2019–2024 | supplement: Figure S12 | kept |
| Figure S15 | `figS15_controls` | Reproduction controls: pre-specified protocol values vs values reproduced by the pipeline | supplement: Figure S6 | kept |
| Plate EF1 | `EF1_seasonality_monthly` | Seasonality and monthly series of GRD episodes with documented F84 | dropped | descriptive hospital detail (monthly seasonality) with no bearing on the message; companion table also dropped |
| Plate EF2 | `EF2_length_of_stay` | Length of stay of episodes with documented F84 | dropped | descriptive hospital detail (length of stay) with no bearing on the message |
| Plate EF3 | `EF3_episode_features` | Administrative characteristics of the episode: documented F84 versus all GRD episodes | dropped | descriptive hospital detail (episode characteristics) with no bearing on the message |
| Plate EF4 | `EF4_severity_weight` | Severity, IR-29301 mortality risk, GRD weight and in-hospital lethality | dropped | descriptive hospital detail (severity, GRD weight, lethality) with no bearing on the message |
| Plate EF5 | `EF5_codiagnoses` | Co-diagnoses of episodes with documented F84 | supplement: Figure S11 | kept |
| Plate EF6 | `EF6_readmission_multiplicity` | Readmission and multiplicity of episodes per identifier | supplement: Figure S8 | kept |
| Plate EF7 | `EF7_age_detail` | Age detail of episodes with documented F84 | dropped | descriptive hospital detail (single-year age); the age–sex result is in Figure 2d and Table S39 |
| Plate EF8 | `EF8_hospitals` | GRD panel hospitals: rates, rank stability and concentration | supplement: Figure S10 | kept |
| Plate EF9 | `EF9_territory` | Territory: episodes and persons by reported region and comuna of residence | dropped | duplicates the spatial set (Figures S28–S33) |
| Plate EF10 | `EF10_deis_detail` | DEIS discharges with F84 as principal diagnosis: detail and comparison with GRD | supplement: Figure S13 | kept |
| extra plate | `E11_rem_a03_codes_by_era` | A03 in detail: every primary-care autism screening code by definition era, Chile 2019–2025 | supplement: Figure S15 | kept |
| extra plate | `E12_rem_a03_risk_referral` | A03 2023–2025: risk and referral structure of M-CHAT-R/F screening by definition era, Chile | supplement: Figure S14 | kept |
| extra plate | `E13_rem_a05_regional` | A05 regional: mental-health programme entries for autism by region and year, Chile 2021–2025 | dropped | place-of-care regional flows for 2023–2025 only, ecological; the regional reading is Figure S32/Table S79 |
| extra plate | `E14_rem_a05_age_sex` | A05 by age and sex: autism entries in 17 WHO age groups, standardised rates and male-to-female ratio, Chile 2021–2025 | dropped | duplicate of Figure S19 (figS8_a05_age_sex) |
| extra plate | `E15_rem_p2_p6_detail` | P2 and P6 in detail: ASD population under control in the public network, December stock, Chile 2019–2025 | supplement: Figure S21 | kept |
| extra plate | `E16_rem_a27_a28_regional` | A27 and A28 by region: screening counselling and assisted referral and ASD rehabilitation entries, Chile 2023–2025 | dropped | place-of-care regional flows for 2023–2025 only, ecological |
| extra plate | `E17_rem_establishment_distribution` | Distribution of REM activity across establishments: Lorenz curves, top decile and thresholds, Chile 2019–2025 | supplement: Figure S17 | kept |
| extra plate | `E18_rem_monthly_series` | Monthly REM series: A05 entries, A03 screening and A28 rehabilitation by month, seasonality and the 2020 disruption, Chi | dropped | duplicate of Figure S23 (figS13_rem_seasonality) |
| extra plate | `E19_rem_definition_era_sensitivity` | Definition-era sensitivity: every REM indicator under strict autism, the variant PDD family and the broad pre-2021 categ | supplement: Figure S20 | kept |
| Figure E20 | `figE20_population_structure` | Structure of the reference population (INE), 2019–2025 | dropped | duplicate of Figure S4 and Table S25 (population structure is a denominator layer) |
| Figure E21 | `figE21_insurance_coverage` | Insurance and operational coverage in detail (December stocks), 2019–2025 | dropped | duplicate of Figure S4 and Table S25 (coverage layers) |
| Figure E22 | `figE22_rem20_capacity` | REM-20 hospital activity and capacity and its ecological relationship with GRD episodes with F84, 2019–2025 | supplement: Figure S24 | kept |
| Figure E23 | `figE23_surveys_detail` | ENDIDE 2022 and ENCAVI 2023–2024 analysed with their complex sampling design: estimates, precision and flagged domains | supplement: Figure S25 | kept |
| Figure E24 | `figE24_education_detail` | Educational recognition of autism: PIE, SINACES and special schools, 2019–2025 | supplement: Figure S26 | kept |
| Figure E25 | `figE25_junaeb_detail` | JUNAEB EVE: caregiver-reported autism in selected school cohorts, 2019–2025 | dropped | duplicate of Figures S26–S27 |
| Figure E26 | `figE26_cross_source` | Comparison across administrative systems: index, raw value, population rate and value per reporting unit, with their den | supplement: Figure S34 | kept |
| Figure E26b | `figE26b_sex_ratio_multisource` | Male-to-female ratio of administrative autism recognition in every source that reports sex, 2019–2025 | supplement: Figure S36 | kept |
| Figure E27 | `figE27_model_diagnostics` | Quasi-Poisson model diagnostics and sensitivity across specifications | supplement: Figure S5 | kept |
| Figure E28 | `figE28_variant_sensitivity` | Sensitivity of every series to the case-definition variant: full F84 (with Rett syndrome) versus F84 without Rett, 2019– | supplement: Figure S2 | kept |
| extra plate | `E40_maps_grd_smoothed_ratio` | Territorial distribution of hospital recognition of autism by comuna of residence, Chile 2019–2024 | supplement: Figure S29 | kept |
| extra plate | `E41_maps_rem_place_of_care` | Territorial distribution of the REM autism indicators by comuna of the establishment, Chile 2019–2025 | dropped | the maps duplicate the place-of-care warning of Figure S28; the table is kept as Table S84 |
| extra plate | `E42_lisa_gistar_maps` | Local clusters of administrative recognition of autism: LISA and Gi*, Chile | supplement: Figure S30 | kept |
| extra plate | `E43_moran_scatter_weights` | Global spatial autocorrelation and its sensitivity to the weight definition, Chile | dropped | the plate adds nothing to Table S76 (Moran sensitivity across weights) |
| extra plate | `E44_correlation_matrix` | Territorial correlation between the administrative systems, comunas and regions | dropped | the plate adds nothing to Table S80 (rank correlations with the warning) |
| extra plate | `E45_bivariate_moran` | Spatial cross-correlation between systems: bivariate Moran's I | dropped | invites a cross-source reading of two unlinked systems (standing rule); dropped with its table |
| extra plate | `E46_sae_deprivation` | Administrative recognition of autism and comuna deprivation estimated for small areas (SAE 2024) | supplement: Figure S33 | kept |
| extra plate | `E47_lorenz_theil` | Territorial inequality of the distribution of administrative recognition | supplement: Figure S31 | kept |
| extra plate | `E48_rank_stability` | Temporal stability of the territorial distribution | dropped | the plate adds nothing to Table S82 (rank stability) |
| extra plate | `E49_regional_summary` | Regional-scale summary: rates, standardised ratios and intervals | supplement: Figure S32 | kept |

## C. Tables of the full manuscript (132)

| Corpus label | Key | Title (corpus) | Journal | Note / reason |
|---|---|---|---|---|
| Table 2 | `T2_grd_core` | GRD hospital core 2019–2024: episodes with documented F84 by code position, panel, activity, coding depth, persons and p | body: Table 1 | cut to 25 rows; the full table is Table S37 |
| Table 3 | `T3_rem_pathway` | Aggregate REM administrative pathway 2019–2025 by module, code and definition era: annual totals and December stocks wit | supplement: Table S50 | relocated (was a body table) |
| Table 4 | `T4_denominators_coverage` | Denominator and coverage layers by year, Chile 2019–2025: INE population, FONASA/ISAPRE insurance, APS enrolment and REM | supplement: Table S25 | relocated (was a body table) |
| Table 5 | `T5_survey_benchmarks` | Population benchmarks of reported autism with complex survey design: ENDIDE 2022 and ENCAVI 2023–2024 | supplement: Table S65 | relocated (was a body table) |
| Table 6 | `T6_education` | Educational triangulation 2019–2025: students with ASD in the School Integration Programme (Apuntes 60 / SINACES) and we | supplement: Table S67 | relocated (was a body table) |
| Table 7 | `T7_models` | Pre-specified models: annual percent change (APC) and 95% CI by estimand and sensitivity, Chile 2019–2025 | body: Table 2 | cut to 29 rows; the full table is Table S88 |
| Table 8 | `T8_controls_compact` | Reproduction controls by indicator family: expected versus observed, status and explanation | supplement: Table S34 | relocated (was a body table) |
| Table 1 | `T1_sources` | Data sources, unit of observation, coverage, definition breaks and absence of person-level linkage, Chile 2019–2025 | supplement: Table S12 | kept |
| extra table | `T_dataflow_counts` | Counts behind Figure 1, with the unit of analysis and the origin of each | supplement: Table S13 | kept |
| extra table | `M1_sources_units` | Sources, unit of observation, geography and the impossibility of individual linkage | supplement: Table S1 | kept |
| extra table | `M2_case_definitions` | Hospital case definition: F84 subcodes by variant (F84 family excluding Rett syndrome) | supplement: Table S2 | kept |
| extra table | `M3_rem_code_sets` | REM code sets by module and definition era, verified against the annual dictionary | supplement: Table S3 | kept |
| extra table | `M4_denominator_layers` | Denominator layers and compatibility rules | supplement: Table S4 | kept |
| extra table | `M5_estimator_map` | Estimator map: equation, script and output file | supplement: Table S5 | kept |
| extra table | `M6_sensitivity_grid` | Grid of pre-specified sensitivity analyses | supplement: Table S6 | kept |
| extra table | `M7_data_states` | Data states: zero, missing, not reported, not estimable and suppressed | supplement: Table S7 | kept |
| extra table | `M8_pipeline_map` | File-by-file map of the pipeline and its outputs | supplement: Table S8 | kept |
| extra table | `M9_software_seeds` | Software, versions, seeds and constants of the run | supplement: Table S9 | kept |
| extra table | `M10_reproduction_controls` | Reproduction controls by module, across the 22 control files of the whole pipeline (expected against observed) | supplement: Table S10 | kept |
| Table S1b | `S_definition_breaks` | Definition, panel and schema breaks by administrative source, 2019–2025 | supplement: Table S17 | kept |
| Table ST7 | `ST7_provenance` | Full provenance of the 182 source artefacts (28 source groups, 20.84 GB): file, size, SHA-256, date, unit, period, stock | supplement: Table S21 | kept |
| Table ST7b | `ST7b_manifest_checks` | SHA-256 and size agreement between the artefacts on disk and the manifests listing them (189 entries) | supplement: Table S22 | kept |
| Table ST2 | `ST2_rem_code_dictionary` | Verification of the 57 REM codes of the administrative pathway against the official dictionary of each year, 2019–2025 | supplement: Table S16 | kept |
| Table ST3 | `ST3_rem_reporting_establishments` | Establishments reporting each REM code by module and year, 2019–2025, with the stable establishment panel (57 codes) | supplement: Table S18 | kept |
| Table ST1 | `ST1_grd_hospital_panel` | Public GRD hospitals 2019–2024: fixed panel of 65 hospitals and observed annual panel, with GRD episodes and episodes wi | supplement: Table S14 | kept |
| Table ST8 | `ST8_grd_identifier_audit` | Audit of the person identifier of the public GRD by year, 2019–2024: validity, within-year uniqueness, format and inform | supplement: Table S15 | kept |
| Table ST10 | `ST10_grd_f84_subcodes` | ICD-10 subcodes of the F84 family in public GRD episodes by year and diagnosis position, 2019–2024 | supplement: Table S23 | kept |
| Table ST9 | `ST9_grd_age_sex` | GRD episodes with documented F84 by sex and five-year age group, 2019–2024: number and rate per 100,000 GRD episodes of  | supplement: Table S39 | kept |
| Table S4 | `S_grd_population_rates` | GRD episodes with documented F84 per 100,000 population, crude and WHO age-standardised, by sex and year, 2019–2024 | supplement: Table S40 | kept |
| Table S3 | `S_hospital_rates_2024` | Episodes with documented F84 per 100,000 GRD episodes by hospital, 2024, with hospital effects 2019–2024 | supplement: Table S41 | kept |
| Table ST11a | `ST11a_deis_annual` | DEIS hospital discharges 2019–2024: total discharges, SNSS affiliation, masking and discharges with F84 by diagnosis pos | supplement: Table S46 | kept |
| Table ST11b | `ST11b_deis_vs_grd` | Coverage comparison between DEIS discharges and public GRD episodes by year, 2019–2024: principal F84 versus principal F | supplement: Table S47 | kept |
| Table S14 | `S14_deis_sex_age` | DEIS discharges with F84 as principal diagnosis per 100,000 discharges by sex and 10-year age band, 2019–2024 | supplement: Table S48 | kept |
| Table F3 | `F3_rem_pathway_data` | Values plotted in Figure 4: annual REM counts by panel, code, era and year, with reporting establishments and stable pan | dropped | duplicate: Tables S50 and S50 carry the plotted values |
| Table S5 | `S5_june_december` | REM June and December stocks by series, code, era and year, with reporting establishments and June/December ratio | dropped | duplicate of Table S61 (ST14_p2_p6_june_december) |
| Table ST14 | `ST14_p2_p6_june_december` | Population under control for autism and PDD in REM Series P (P2 NANEAS and P6 mental health): December stock versus June | supplement: Table S61 | kept |
| Table S6 | `S6_stable_panel` | REM totals over all establishments and over the stable panel, with percentages of volume and establishments retained | supplement: Table S54 | kept |
| Table ST13 | `ST13_a05_age_sex` | Mental-health programme entries for autism and the PDD family (REM A05) by age group, sex and year, 2019–2025, with repo | supplement: Table S57 | kept |
| Table S8 | `S8_a05_age_sex` | REM A05 entries by age group, sex and year (age × sex cells), strict autism and PDD family | dropped | duplicate of Table S57 (ST13_a05_age_sex) |
| Table S7 | `S_a05_standardised_rates` | REM A05 autism entries per 100,000 population, crude and WHO age-standardised, by sex and year, 2021–2025 | supplement: Table S56 | kept |
| Table S13 | `S13_rem_seasonality` | REM monthly totals, establishments with a row in the month and index relative to the annual mean (A05 and A03) | supplement: Table S62 | kept |
| Table ST4a | `ST4a_comuna_crosswalk_summary` | INE–DEIS comuna crosswalk: comuna names of FONASA, APS enrolment and ISAPRE linked to the unique territorial code by met | supplement: Table S30 | kept |
| Table ST4b | `ST4b_comuna_unmatched` | Comuna names not linked to the crosswalk (non-geographic placeholders) by source and year, with the persons affected and | supplement: Table S31 | kept |
| Table ST12a | `ST12a_fonasa_schema` | Schema of the December FONASA beneficiary aggregate files by year, 2018–2025: file, encoding, columns, age bands, additi | supplement: Table S27 | kept |
| Table ST12b | `ST12b_isapre_rules` | December ISAPRE beneficiaries by year, 2019–2025, and harmonisation rules of the Superintendencia de Salud comuna files | supplement: Table S28 | kept |
| Table ST12c | `ST12c_aps_panel` | December primary-care (APS) enrolment by year, 2019–2025: centres, continuous panel of 1,871 centres and retention | supplement: Table S29 | kept |
| Table S11 | `S10_denominator_sensitivity` | Sensitivity of national denominators: INE base 2017 vs base 2024 and Census 2024, 2019–2025 | supplement: Table S26 | kept |
| Table S12 | `S11_coverage_age_sex` | Coverage layers at December 2025 by 10-year age band and sex: FONASA, APS enrolment, ISAPRE and INE population | supplement: Table S32 | kept |
| Table ST5 | `ST5_survey_items` | Dictionary of the autism items and design variables of ENDIDE 2022 and ENCAVI 2023–2024 | supplement: Table S19 | kept |
| Table ST6 | `ST6_junaeb_items` | Dictionary of the Student Vulnerability Survey (JUNAEB EVE) by year and level, 2019–2025: autism spectrum disorder item, | supplement: Table S20 | kept |
| Table S13 | `S12_junaeb_sex_level` | JUNAEB: students with caregiver-reported ASD by year, level and sex, 2019–2025 | supplement: Table S69 | kept |
| Table S9 | `F4_triangulation_series` | Figure 5 series per 100,000 population: GRD, REM A05, REM P2 and PIE, 2019–2025 | supplement: Table S86 | kept |
| Table S10 | `S9_regional_rates` | Regional rates 2024 per 100,000 population: GRD episodes with F84 by region of residence (both variants) and REM A05 ent | supplement: Table S70 | kept |
| Table S8 | `S_convergence_index` | Growth indices (2021 = 100; 2019 = 100 where the series exists) of administrative autism indicators by system, 2019–2025 | supplement: Table S85 | kept |
| Table S7 | `T7_models_cpa_full` | Annual percent change (APC) of administrative-recognition indicators of autism by estimand and sensitivity, Chile 2019–2 | supplement: Table S89 | kept |
| Table 8 | `T8_controls` | Reproduction controls: pre-specified protocol values versus values reproduced by the pipeline, by source, indicator and  | dropped | the full control list; Table S34 (compact) and Table S35 (by family) cover it |
| Table S15 | `S15_controls_scatter` | Numeric reproduction controls used in Figure S15: expected, observed, relative difference and status, by module | dropped | Figure S6 carries its values |
| extra table | `E1_grd_seasonality` | GRD episodes with documented F84 by month of admission and within-year seasonal index, 2019–2024 | supplement: Table S63 | restored after round 1: the GRD monthly index of equation 19; cited from Results › Pathway ¶3 beside the REM seasonality |
| extra table | `E2_grd_length_of_stay` | Length of stay of GRD episodes with documented F84 and of all GRD episodes, 2019–2024 | dropped | hospital detail (length of stay) |
| extra table | `E3_grd_los_by_age` | Length of stay by five-year WHO age group, episodes with documented F84 and all GRD episodes, 2019–2024 | dropped | hospital detail (length of stay by age) |
| extra table | `E4_grd_episode_features` | Administrative characteristics of GRD episodes with documented F84, 2019–2024, with all GRD episodes as comparison | dropped | hospital detail (episode characteristics) |
| extra table | `E5_grd_weight_and_groups` | IR-29301 relative weight and 15 most frequent GRD groups among episodes with documented F84, 2019–2024 | dropped | hospital detail (GRD weight and groups) |
| extra table | `E6_grd_codiagnoses_top25` | 25 most frequent ICD-10 co-diagnoses in GRD episodes with documented F84, 2019–2024 | dropped | hospital detail; the co-diagnosis message is Figure S11/Tables S43–S44 |
| extra table | `E7_grd_codiagnosis_chapters` | Co-diagnoses by ICD-10 chapter and mental-health block in GRD episodes with documented F84, 2019–2024 | dropped | hospital detail; chapters are in Figure S11/Table S43 |
| extra table | `E8_grd_principal_when_secondary` | Principal diagnosis of GRD episodes in which F84 appears only as a secondary diagnosis, 2019–2024 | supplement: Table S44 | kept |
| extra table | `E9_grd_readmission` | Hospital readmissions after a GRD discharge with documented F84, by identifier era and horizon | dropped | hospital detail; readmission is Figure S8/Table S38 |
| extra table | `E10_grd_multiplicity` | GRD episodes with documented F84 per identifier, within each identifier era | dropped | hospital detail; multiplicity is Figure S8/Table S38 |
| extra table | `E11_grd_territory_region` | GRD episodes with documented F84 by declared region of RESIDENCE, 2019–2024 | dropped | regional GRD detail; the territorial reading is Tables S70–S84 |
| extra table | `E12_grd_age_single_year` | GRD episodes with documented F84 by age band and sex, first and last year of the series | dropped | hospital detail (single-year age); age–sex cells are Table S39 |
| extra table | `EF1_seasonality_monthly` | Companion table of plate EF1. Seasonality and monthly series of GRD episodes with documented F84 | dropped | companion of a dropped plate (EF1) |
| extra table | `EF2_length_of_stay` | Companion table of plate EF2. Length of stay of episodes with documented F84 | dropped | companion of a dropped plate (EF2) |
| extra table | `EF3_episode_features` | Companion table of plate EF3. Administrative characteristics of the episode: documented F84 versus all GRD episodes | dropped | companion of a dropped plate (EF3) |
| extra table | `EF4_severity_weight` | Companion table of plate EF4. Severity, IR-29301 mortality risk, GRD weight and in-hospital lethality | supplement: Table S45 | restored after round 1: the output of equation 18 (Jeffreys intervals of in-hospital lethality) that the methodology describes; cited from Results › Hospital ¶4 |
| extra table | `EF5_codiagnoses` | Companion table of plate EF5. Co-diagnoses of episodes with documented F84 | supplement: Table S43 | kept |
| extra table | `EF6_readmission_multiplicity` | Companion table of plate EF6. Readmission and multiplicity of episodes per identifier | supplement: Table S38 | kept |
| extra table | `EF7_age_detail` | Companion table of plate EF7. Age detail of episodes with documented F84 | dropped | companion of a dropped plate (EF7) |
| extra table | `EF8_hospitals` | Companion table of plate EF8. GRD panel hospitals: rates, rank stability and concentration | supplement: Table S42 | kept |
| extra table | `EF9_territory` | Companion table of plate EF9. Territory: episodes and persons by reported region and comuna of residence | dropped | companion of a dropped plate (EF9) |
| extra table | `EF10_deis_detail` | Companion table of plate EF10. DEIS discharges with F84 as principal diagnosis: detail and comparison with GRD | supplement: Table S49 | kept |
| extra table | `E11_rem_a03_codes_by_era` | A03 in detail: every primary-care autism screening code by definition era, Chile 2019–2025 | supplement: Table S53 | kept |
| extra table | `E12_rem_a03_risk_referral` | A03 2023–2025: risk and referral structure of M-CHAT-R/F screening by definition era, Chile | supplement: Table S52 | kept |
| extra table | `E13_rem_a05_regional` | A05 regional: mental-health programme entries for autism by region and year, Chile 2021–2025 | supplement: Table S72 | restored after round 1: the region × year A05 table by reporting establishment (place of care), companion of the GRD one; cited from Results › Territory |
| extra table | `E14_rem_a05_age_sex` | A05 by age and sex: autism entries in 17 WHO age groups, standardised rates and male-to-female ratio, Chile 2021–2025 | supplement: Table S58 | restored after round 1: the output of equation 7 (exact binomial count ratio of the A05 male:female ratio by age); cited from Results › Pathway ¶2 beside Table S57 |
| extra table | `E15_rem_p2_p6_detail` | P2 and P6 in detail: ASD population under control in the public network, December stock, Chile 2019–2025 | supplement: Table S60 | kept |
| extra table | `E16_rem_a27_a28_regional` | A27 and A28 by region: screening counselling and assisted referral and ASD rehabilitation entries, Chile 2023–2025 | dropped | REM companion of a dropped plate (E16) |
| extra table | `E17_rem_establishment_distribution` | Distribution of REM activity across establishments: Lorenz curves, top decile and thresholds, Chile 2019–2025 | supplement: Table S55 | kept |
| extra table | `E18_rem_monthly_series` | Monthly REM series: A05 entries, A03 screening and A28 rehabilitation by month, seasonality and the 2020 disruption, Chi | dropped | REM companion of a dropped plate (E18); duplicate of Table S62 |
| extra table | `E19_rem_definition_era_sensitivity` | Definition-era sensitivity: every REM indicator under strict autism, the variant PDD family and the broad pre-2021 categ | supplement: Table S59 | kept |
| Table E20 | `E20_population_structure` | Structure of the reference population (INE 30 June projection, Censo 2017 base), 2019 and 2025 | dropped | duplicate of Table S25 (denominator layers) |
| Table E21 | `E21_insurance_coverage` | Insurance layers and operational coverage (December stocks), 2019–2025 | dropped | duplicate of Table S25 (coverage layers) |
| Table E22 | `E22_rem20_capacity` | REM-20 hospital activity and capacity and its ecological relationship with GRD episodes with F84, 2019–2025 | supplement: Table S64 | kept |
| Table E23 | `E23_surveys_detail` | ENDIDE 2022 and ENCAVI 2023–2024 with complex sampling design: estimates, precision and flagged domains | supplement: Table S66 | kept |
| Table E24 | `E24_education_detail` | Educational recognition of autism: PIE, SINACES and special schools, 2019–2025 | supplement: Table S68 | kept |
| Table E25 | `E25_junaeb_detail` | JUNAEB EVE: percentage of students with caregiver-reported autism by level, year and sex, 2019–2025 | dropped | duplicate of Tables S67 and S66 |
| Table E26 | `E26_cross_source` | Comparison across administrative systems: annual value, value per 100,000 residents and value per reporting unit, 2019–2 | supplement: Table S87 | kept |
| Table E26b | `E26b_sex_ratio_multisource` | Male-to-female ratio of administrative autism recognition in every source that reports sex, 2019–2025 | supplement: Table S90 | kept |
| Table E27 | `E27_model_diagnostics` | Quasi-Poisson models: main specification by estimand and diagnostics across specifications | supplement: Table S33 | kept |
| Table E28 | `E28_variant_sensitivity` | Sensitivity of every series to the case-definition variant: full F84 (with Rett syndrome) versus F84 without Rett, 2019– | supplement: Table S24 | kept |
| extra table | `E40_grd_smoothed_ratio_comuna` | GRD episodes with documented F84 by comuna of residence: observed, expected, rate and standardised ratios, Chile 2019–20 | supplement: Table S73 | kept |
| extra table | `E41_rem_comuna_place_of_care` | REM autism indicators by comuna of the establishment: A05, P2 and P6, Chile 2019–2025 | supplement: Table S84 | kept |
| extra table | `E42_local_class_counts` | Comunas per class of the local indicators (LISA and Gi*) and Benjamini–Hochberg threshold | supplement: Table S74 | kept |
| extra table | `E43_moran_sensitivity_main` | Moran's I of the main indicator: weight definition, value type, period and sensitivity analyses | supplement: Table S76 | kept |
| extra table | `E44_correlation_matrix_comuna` | Matrix of Spearman's rho between territorial indicators, comunas and regions | supplement: Table S80 | kept |
| extra table | `E45_bivariate_moran_pairs` | Bivariate Moran's I of every pair of territorial indicators | supplement: Table S81 | restored after round 1: the output of equation 26 (bivariate Moran's I) that the article Methods, M4 and Table S5 describe; cited from Results › Territory with the standing-rule wording (co-location of unlinked systems, no direction, no linkage) |
| extra table | `E46_sae_association` | Ecological association of each territorial indicator with SAE 2024 comuna deprivation and urbanicity | supplement: Table S83 | kept |
| extra table | `E47_inequality_gini_theil` | Territorial inequality: Gini, decomposed Theil index and decile ratio, by source and year | supplement: Table S78 | kept |
| extra table | `E48_rank_stability` | Stability of the territorial ranking between years and between periods | supplement: Table S82 | kept |
| extra table | `E49_regional_summary` | Regional summary: observed, expected, rates and standardised ratios with intervals | supplement: Table S79 | kept |
| extra table | `E50_moran_gistar_all` | Every spatial-autocorrelation statistic computed: global Moran's I and Gi* classes | supplement: Table S77 | kept |
| extra table | `E51_lisa_significant_comunas` | Comunas with a significant local cluster (LISA or Gi*, Benjamini–Hochberg q < 0.05) | supplement: Table S75 | kept |
| extra table | `E60_grd_annual_full` | Complete annual series of GRD episodes with documented F84 by series, panel, activity and code position, 2019–2024 | supplement: Table S36 | kept |
| extra table | `E61_grd_hospital_year_full` | GRD episodes with documented F84 by hospital and year, with rates, intervals and fixed-panel membership (all observed ho | dropped | complete-data table; Table S41 and the deposited tidy files carry it |
| extra table | `E62_grd_region_population_rates` | GRD episodes with documented F84 by declared region of residence and year, with INE population rates, 2019–2024 | supplement: Table S71 | restored after round 1: the region × year GRD table by residence with population rates, the regional reading a regional-health journal expects; cited from Results › Territory |
| extra table | `E63_grd_age_single_sex_full` | GRD episodes with documented F84 by single year of age and sex, 2019–2024 | dropped | complete-data table; Table S39 and the deposited tidy files carry it |
| extra table | `E64_grd_codiagnoses_full` | Complete list of ICD-10 co-diagnoses with at least 20 episodes among GRD episodes with documented F84, 2019–2024 | dropped | complete-data table; Table S43 and the deposited tidy files carry it |
| extra table | `E65_grd_episode_features_full` | Complete distribution of administrative characteristics of GRD episodes with documented F84, 2019–2024 | dropped | complete-data table (episode characteristics); deposited tidy files |
| extra table | `E66_grd_length_of_stay_full` | Length of stay by year, code position, activity and five-year WHO age group, 2019–2024 | dropped | complete-data table (length of stay); deposited tidy files |
| extra table | `E67_grd_readmission_full` | Hospital readmissions after a GRD discharge with documented F84, by identifier era, year and horizon | dropped | complete-data table; Table S38 and the deposited tidy files carry it |
| extra table | `E68_grd_multiplicity_full` | Multiplicity: GRD episodes with documented F84 per identifier, within each identifier era | dropped | complete-data table; Table S38 and the deposited tidy files carry it |
| extra table | `E69_rem_code_year_full` | Complete REM table: code × year with totals, reporting establishments, stable-panel total and definition era, 2019–2025 | supplement: Table S51 | kept |
| extra table | `E70_rem_a05_age_sex_full` | REM A05: entries and exits by age, sex, category and year, 2021–2025 (broad PDD 2019–2020 as a separate series) | dropped | complete-data table; Table S57 and the deposited tidy files carry it |
| extra table | `E71_rem_p2_p6_region_year` | REM P2 and P6: persons under control in December by region of the establishment, year and definition era, 2019–2025 | dropped | complete-data table; Table S60 and the deposited tidy files carry it |
| extra table | `E72_rem_establishments_by_module` | Reporting establishments by REM module and year, with the stable panel and the number of codes in force, 2019–2025 | dropped | complete-data table; Table S18 and the deposited tidy files carry it |
| extra table | `E73_denominator_layers_full` | Denominator layers by year, region, age group and sex: INE population, FONASA beneficiaries, ISAPRE beneficiaries and AP | dropped | complete-data table; Tables S25 and S32 and the deposited tidy files carry it |
| extra table | `E74_coverage_harmonisation_rules` | Harmonisation rules for FONASA, APS enrolment and ISAPRE by year: file, scheme, key columns, December total and aggregat | dropped | complete-data table; Tables S27–S29 carry the rules |
| extra table | `E75_survey_estimates_full` | Population survey estimates (ENDIDE 2022 and ENCAVI 2023–2024): every domain and subgroup with design variables, DEFF, r | dropped | complete-data table; Tables S65–S66 and the deposited tidy files carry it |
| extra table | `E76_education_pie_full` | Education: complete PIE series by definition and year (strict ASD, ASD-Asperger, harmonised, special schools and publish | dropped | complete-data table; Tables S67–S68 carry it |
| extra table | `E77_education_junaeb_full` | Education: JUNAEB survey by year, level and sex, with weighted proportions, intervals and estimability states, 2019–2025 | dropped | complete-data table; Table S69 carries it |
| extra table | `E78_models_all_specifications` | Model table: every fitted specification, with estimand, source, denominator, panel, covariates, APC with 95% CI, dispers | dropped | duplicates Table S89 (every specification) |
| extra table | `E79_reproduction_controls_by_family` | Reproduction controls by module and family: number of checks, reproduced, with a documented difference and informative ( | supplement: Table S35 | kept |
| extra table | `E80_tidy_data_dictionary` | Data dictionary: the 88 tidy files of the study with their columns, unit, denominator, geography and producing script | supplement: Table S91 | kept |
| extra table | `E81_project_asset_inventory` | Inventory of every figure, table and equation of the project (240 files) with its path, its current label resolved in th | dropped | inventory of the project files; superseded by the data dictionary (Table S91) and the repository |

## D. Supplement-only text of the full manuscript

- The corpus 'Supplementary methods S1–S5' and the 'Optional material index' are superseded by Part A of the journal appendix (`prose_methods_extended.methods_blocks` verbatim: M1–M7, Tables S1–S10, 33 equations), the STROBE/RECORD checklist (A8, Table S11) and the analysis plan v1.0 (A9).
- The three `[OPT]` article paragraphs L1003 (sex ratio in cohorts), L1031 (Chilean context) and L1062 (strengths) are dropped except the ENDIDE clause of L1003 (Discussion ¶3, with the derived ENDIDE M:F) and one strengths sentence folded into the limitations paragraph; their seven references are in `reference_cut.md`.
- Nothing was dropped silently: every dropped figure or table above carries its reason, and every number of the corpus Results not printed verbatim in the journal is named in section A with its key.

## E. Close of the first reading round (2026-09-09)

Six tables returned to the appendix so that no estimator described in the methodology is left without its printed
output and so that the regional reading exists by year: `EF4_severity_weight` (equation 18, Table S45),
`E14_rem_a05_age_sex` (equation 7, Table S58), `E1_grd_seasonality` (equation 19 for the GRD, Table S63),
`E62_grd_region_population_rates` (Table S71), `E13_rem_a05_regional` (Table S72) and `E45_bivariate_moran_pairs`
(equation 26, Table S81, with the standing-rule wording). Every table after S44 is renumbered accordingly (91 tables,
36 figures); the numbers above are the new ones. Drops now 19 figures and 42 tables, all named in section B12 of the
appendix and deposited with the data (the article's data sharing statement names the full set: 59 figures and 132
tables of the corpus, of which the article and appendix print 40 and 90). Sizes are read from the registries
(`journal_config.SUPP_FIGURES`/`SUPP_TABLES`, `supplementary_material.FIGURE_ORDER`/`TABLE_ORDER`,
`prose_en.MAIN_FIGURES`/`MAIN_TABLES`), never typed.


## F. Close of the second reading round (2026-09-09)

Presentation of the supplementary tables (no cell altered; `journal_config.TABLE_LAYOUT`, `restructure_table_block`, applied by `build_journal.build_supplement` after the print glossary): a table whose columns need more than the 24·7 cm of an A4 landscape page at 8 pt is printed in consecutive parts labelled «Table Sn (part i of m)», its key columns repeated in every part and its note under the last part — 18 tables in parts, 38 part blocks among the 111 table blocks of the appendix: S12 (2), S15 (2), S16 (2), S19 (2), S20 (2), S21 (3), S22 (2), S27 (3), S28 (2), S37 (2), S46 (2), S47 (2), S54 (2), S65 (2), S80 (2), S85 (2), S89 (2), S91 (2). In Tables S88 and S89 the estimand column is the bold internal heading of each run of rows, the free-text notes column is replaced by lettered footnotes under the table (a sentence present in every row is stated once) and a running «#» column identifies the row across the parts. The ties and soft breaks of the cells (`journal_config.journal_text(cells=True)`: WORD JOINER around every digit–dash–digit range, U+200B break opportunities inside machine tokens of 25 characters or more) and the journal atom rule of the document builder (`docx_builder.set_journal_atoms`) are what let every column be at least as wide as its longest unbreakable piece. The p column of Table S82 (rank stability) is rebuilt from `E48_rank_stability_numeric.csv` through `format_p`. Nothing else of the item map changes: the S-numbers of sections B–E are unchanged.
