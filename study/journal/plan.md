# Executable editorial plan — journal submission of the `sin_rett` variant to *the target journal*

Synthesised 2026-09-09 from plans A (`A_journal_editor`, winner), B (`B_methods_reviewer`) and C (`C_policy_reader`) and the two judgements, after re-reading the corpus: `prose_en.py` (article blocks, keys per paragraph extracted by AST), `supplementary_material.py` (FIGURE_ORDER 54, TABLE_ORDER 125, `_plate_stems`, `LEGACY_UNREGISTERED_PLATES`), `prose_methods_extended.methods_blocks` (136 blocks: 59 paragraphs, 33 equations, 26 estimator headings, 10 tables, 39 bib keys), `equations` (NUMBER 33, ESTIMATORS 26), `docx_builder.build_document` (block grammar), `pipeline/10_manuscript.py` (build_pair, postprocess_docx, add_page_numbers, landscape_wide_tables, to_pdf, localised_references), `common.py` (plate_resolve, save_fig, check_layout, PLATE_CHECK), `paper/references.py` (Citations renders "(1,2)"; `_author_list(limit=6)`), `outputs/values_sin_rett.json` (17 198 keys; every key named below was checked to exist), `outputs/sin_rett/en/tables/T2_grd_core.csv` (45 rows), `T7_models.csv` + `T7_models_numeric.csv` (54 rows, row-aligned, `model_id` and raw `p_value`), `outputs/tidy/spatial_*.csv`, the four `captions.json`/`titles.json`, `references.bib` (122 keys), `journal_guidelines.md`, `analysis_plan.md`, `reporting_checklist.md`, `tests/` (300 tests collected; baseline 299 passed, 1 skipped).

Four builders work from this file without talking to each other: **(P) plates and shared-builder flags**, **(A) `prose_journal_en.py` + `prose_journal_es.py`**, **(S) `supplement_journal.py`**, **(B) `journal_config.py` + `build_journal.py`**. Section 7 is the contract between them. Where this plan and any earlier plan disagree, this plan wins; where this plan is silent, the corpus rule (decision_log.md, standing rules) wins.

Standing rules (a violation is a blocking defect, restated so no builder needs another file): counts are administrative recognition, never prevalence or incidence; the GRD outcome is "episodes with documented F84", never "hospitalisations for autism"; F84-principal is a separate series; no person-level linkage, cascade or cross-source ratio (the DEIS/GRD principal-vs-principal comparison is a coverage comparison with its non-probability note, never a probability; the any-position/principal ratio is never printed); no causal effect of Law 21.545 (context from March 2023); stocks and flows never on one axis or in one sentence as a ratio; place of care and place of residence never mixed without the warning; the GRD panel is 65 fixed and 65-65-65-65-68-72 observed; persons only within year; surveys with weights and complex design; REM zero, missing and not reported are distinct states; Serie P December primary, June sensitivity, never summed; cells below 5 suppressed; every number printed comes from `values_sin_rett.json` (key named) or a tidy table (file, filter and column named), or is derived in the print funnel from named keys; nothing is typed by hand.

---

## 1. Title, key messages, Summary, Research in context

### 1.1 Title (unchanged from the corpus)

`prose_en.TITLE`: *Administrative recognition of autism across health and education systems in Chile, 2019–2025: a national multisource surveillance study*. Running title `prose_en.RUNNING_TITLE`. Spanish: `prose_es.TITLE`. The subtitle line "Analysis variant: …" is NOT printed on the journal title page; the variant is stated once in Methods (Case definitions) and once in the supplement front matter.

### 1.2 Key messages (for the cover letter and the Discussion's first paragraph; each number with its key)

1. Every unlinked public register in Chile that carries an autism code recorded a several-fold rise between 2019 and 2025, convergent in direction and timing (steepest in 2022–2024): the rate of GRD episodes with documented F84 rose 3·97-fold (`grd_f84_any_rate_ratio_2024_2019`; 202·7 → 804·1 per 100 000 episodes, `grd_f84_any_rate_2019`/`_2024`), strict-autism mental-health entries 6·31-fold (`a05_autism_entries_ratio_2025_2021`; 2085 → 13 155, `a05_autism_entries_2021`/`_2025`), the December stock of children with autism under control 16·2-fold (`p2_tea_dec_ratio_2025_2019`; 1854 → 29 974) and registered autistic students 5·08-fold (`pie_harmonised_ratio_2025_2019`; 21 012 → 106 786). Hospital counts fell with activity in 2020 (`grd_f84_any_n_2020` = 1609; DEIS `deis_f84_principal_n_2020` = 255); the rate per episode (`grd_f84_any_rate_2020` = 205·8) and the stocks (`p2_tea_dec_2020` = 1919; `pie_harmonised_2020` = 23 590) did not. Never write "trough in 2020" for the stocks or the rate.
2. The rise survives every pre-specified sensitivity but its size depends on the specification, which is itself the finding: GRD APC 35·9% (95% CI 30·0–42·1; `apc_grd_any_obs`, `_lo`, `_hi`), 32·9–63·9% across the 16 specifications (`apc_grd_any_sensitivity_min`/`_max`, `apc_grd_any_sensitivity_n_specs`). The gap between growth per reporting establishment and growth per resident (A05 27·9% vs 47·2%, `apc_a05_autism_estab`/`apc_a05_autism_pop`; P2 36·3% per establishment vs 63·5% as a count, `apc_p2_dec_estab`/`apc_p2_dec`) **bounds** the contribution of reporting expansion; it does not quantify it (wording fixed by the judges).
3. Most hospital recognition is documentation, not admission for autism: 95·5% of 2024 episodes carried F84 only as a secondary diagnosis (`grd_f84_secondary_only_share_2024_pct`), principal F84 grew at 14·6% against 35·9% (`apc_grd_principal_obs`), mean coding depth rose from 4·39 to 5·78 (`grd_coding_depth_all_mean_2019`/`_2024`); yet the rate rose in every coding-depth stratum for which a ratio key exists — 3·6, 3·6, 4·4, 5·0, 4·6 and 2·5 for three, four, five, six-to-seven, eight-to-ten and 11+ diagnoses (`grd_depth_bin_{3,4,5,6_7,8_10,11plus}_rate_ratio_2024_2019`) — and strata one and two are printed as rates only (`grd_depth_bin_1_rate_2019`/`_2024`, `grd_depth_bin_2_rate_2019`/`_2024`), never as a hand-computed ratio; each additional coded diagnosis carried a within-hospital rate ratio of 1·07 (`apc_grd_hospital_fe_depth_depth_rr_per_diagnosis`).
4. Recognition is shifting towards girls and women and remains concentrated in early childhood: the male:female ratio of GRD episodes fell from 3·27 to 2·03 (`grd_f84_any_mf_ratio_n_2019`/`_2024`), the ratio of WHO-standardised A05 rates was 2·04 in 2025 (`a05_autism_pop_asr_mf_ratio_2025`), age-adjusted growth was faster in females (GRD 54·9% vs 37·5%, `apc_grd_pop_any_female_ageadj`/`apc_grd_pop_any_male_ageadj`; A05 `apc_a05_autism_ageadj_female`/`apc_a05_autism_ageadj_male`), and 47·7% of GRD episodes and 46·7% of A05 entries were in children aged 0–9 years (`grd_f84_any_share_age_0_9_2024`, `a05_autism_entries_share_age_0_9_2025`). Survey benchmarks are named by instrument: ENDIDE 2022 reported autism in 2·87% of children aged 2–17 years (`svy_endide_children_reported_total_pct`), 2·39% with a physician-confirmed diagnosis (`svy_endide_children_reported_confirmed_total_pct`) and 0·29% of adults (`svy_endide_adults_reported_total_pct`); ENCAVI 2023–24 a declared diagnosis in 0·71% of people aged 15 or older (`svy_encavi_15plus_diagnosed_total_pct`). Never merge the two instruments into one range without naming both.
5. These counts measure demand for diagnosis, care and school support, never prevalence; no effect of Law 21.545 can be identified because it coincides with pandemic recovery, reporting expansion, code redesign and deeper coding; surveillance under the law should print reporting establishments, definition era and coding rule beside every count and move towards person-level linkage with safeguards.

### 1.3 Summary — five paragraphs, measured at **248 words** with `prose_en.word_counts` on journal blocks (Background 40, Methods 56, Findings 102, Interpretation 48, Funding 2)

Builder A prints exactly this text through the corpus formatters (`n0`, `n1`, `n2`, `pct`) and the keys named; the journal number pass (section 7.5) converts "2,334" → "2334", "13,155" → "13 155", "202.7" → "202·7" and "100,000" → "100 000" AFTER counting. Count before every build; if the count exceeds 250, trim in this order: (1) "in school integration programmes" → "in school integration"; (2) delete "(2021)" and "(2025)" and write "in 2021–2025"; (3) delete "; no effect of Law 21.545 was modelled" (the sentence is repeated in Methods).

> **Background** Recorded autism diagnoses have risen steeply in high-income countries; Latin American evidence is scarce. We describe how administrative recognition of autism changed across Chile's public health and education systems in 2019–2025 and its robustness to coverage, coding and definitions.
>
> **Methods** National study of unlinked routine data: public-hospital diagnosis-related-group (GRD) episodes and DEIS discharges (2019–2024), six REM outpatient modules (2019–2025), population denominators, two complex-design surveys and school registers. We estimated rates per 100,000 GRD episodes and per resident, WHO-standardised rates and quasi-Poisson annual percent changes (APC) with pre-specified sensitivities; no effect of Law 21.545 was modelled.
>
> **Findings** GRD episodes with documented F84 rose from [`grd_f84_any_n_2019`] ([`grd_f84_any_rate_2019`] per 100,000 episodes) in 2019 to [`grd_f84_any_n_2024`] ([`grd_f84_any_rate_2024`]) in 2024 (APC [`apc_grd_any_obs`]%, 95% CI [`apc_grd_any_obs_lo`]–[`apc_grd_any_obs_hi`]; [`apc_grd_any_sensitivity_min`]–[`apc_grd_any_sensitivity_max`]% across specifications); [`grd_f84_secondary_only_share_2024_pct`]% carried F84 only as a secondary diagnosis. Strict-autism mental-health entries rose from [`a05_autism_entries_2021`] (2021) to [`a05_autism_entries_2025`] (2025), children with autism under control from [`p2_tea_dec_2019`] to [`p2_tea_dec_2025`] and autistic students in school integration programmes from [`pie_harmonised_2019`] to [`pie_harmonised_2025`]. The male:female ratio of hospital episodes fell from [`grd_f84_any_mf_ratio_n_2019`] to [`grd_f84_any_mf_ratio_n_2024`]. ENDIDE 2022 reported autism in [`svy_endide_children_reported_total_pct`]% of children aged 2–17 years and [`svy_endide_adults_reported_total_pct`]% of adults; ENCAVI 2023–24 in [`svy_encavi_15plus_diagnosed_total_pct`]% of people aged 15 or older.
>
> **Interpretation** Independent health and education systems recorded a several-fold expansion of administrative recognition, coinciding with pandemic recovery, reporting expansion, code changes, deeper coding and, from 2023, Law 21.545. Reporting and coding explain part of the change; underlying epidemiological change cannot be separated. Services and surveillance must keep pace.
>
> **Funding** None.

Rendered values (n0/n1/n2/pct, then the number pass): 2334; 202·7; 8731; 804·1; 35·9; 30·0–42·1; 32·9–63·9; 95·5; 2085; 13 155; 1854; 29 974; 21 012; 106 786; 3·27; 2·03; 2·87; 0·29; 0·71. "Funding None" is author-supplied and stays "None" until the author team says otherwise; the Methods keeps "Role of the funding source".

### 1.4 Research in context (panel block, no references, no citations, ≈418 words)

Reuse `prose_en.py` L461–L495 verbatim (three items: *Evidence before this study* — PubMed and Crossref searched Sept 4, 2026, no language or date restriction, the exact term list and the official portals; *Added value of this study*; *Implications of all the available evidence*). Two edits only: (i) in *Added value* replace "we show that administrative recognition of autism rose several-fold" with "we show that administrative recognition of autism rose several-fold between 2019 and 2025 in the hospital, outpatient, rehabilitation and educational systems" (adds rehabilitation, which the body reports); (ii) in *Implications* keep "cannot be read as prevalence". A test asserts the panel contains no `[@` marker and no digit-only citation.

---

## 2. Body display items, in order of first citation

Six items: Figures 1–4 and Tables 1–2. Every other corpus item leaves the body (section 3). Journal plate mode (section 7.4) is applied only to these four plates, which are read from `outputs/sin_rett/<lang>/journal/figures/` (never from `figures/`).

| # | Kind | Asset key (source folder) | What it shows | Why it is in the body | Journal-format changes |
|---|---|---|---|---|---|
| Figure 1 | figure | `fig1_dataflow` (journal/figures, rendered by 08d in journal mode) | Six lanes (hospital GRD/DEIS; REM Series A; REM Series P; denominators and coverage; surveys and education; territory): database → steps → yield, unit badge (record/person/comuna), n at entry and after the autism selection, exclusions in red, definition breaks, one dashed band stating no record is linked across systems. | The RECORD flow diagram (RECORD 13.1, STROBE 13) for a design without recruitment or linkage; it prevents the reader from reading the pathway as a cascade; the counts it prints are audited in appendix Table S13 (`T_dataflow_counts`). | Single-canvas schematic exempt from the 3 × 2 grid (`plate_declare(grid=None)`, as today); journal mode removes the top-right variant stamp (FS_VARIANT text) and the variant goes into the legend; lane headings stay (labels, not a chart title). Legend: heading "Figure 1. What was done with each database: the six data families of the multisource study, Chile 2019–2025 (F84 family excluding Rett syndrome)" in 10 pt bold, then the reading rules and the linkage statement only (≤ 160 words); the "HOW IT IS DRAWN" and "SOURCE OF THE FIGURES" blocks move to the note of Table S13. |
| Figure 2 | figure | `fig2_grd_core` (journal/figures, 08a) | (a) F84 any position and principal per 100 000 GRD episodes, observed and fixed panels, exact CIs, hospitals per year; (b) all activity, strict hospitalisation, CMA; (c) rate within coding-depth strata 2019 vs 2024 with mean-depth inset; (d) per 100 000 INE residents by age group and sex with the place-of-care warning; (e) 72 hospitals ranked, 2024; (f) episodes vs persons within year, episodes per person, M:F ratio. | The primary estimand with its three threats (panel, activity, coding depth), the SAGER sex result and the hospital heterogeneity the Discussion interprets. | Journal plate mode: the six in-panel titles reduced to "(a)"–"(f)"; the "— F84 without Rett variant" suffix leaves the plate; no outer box; artwork labels "100,000" → "100 000" and decimals to "·"; re-rendered with `PLATE_CHECK=strict`. Legend heading 10 pt bold = the captions.json title without the "Figure 3." prefix; legend body from captions.json trimmed to ≤ 300 words (drop repeated boilerplate: the shading/dotted-line sentence once, the "administrative recognition, not prevalence" sentence once). |
| Figure 3 | figure | `fig3_rem_pathway` (journal/figures, 08b) | (a) A03 by era 2019–2022 and 2023–2024 (log scale, n establishments); (b) 2024 31–59-month codes and 2025 redesign; (c) A27 counselling/assisted referral and A28 rehabilitation entries 2023–2025; (d) A05 entries and discharges with the 2021 break and reporting establishments; (e) P2 December stock, June hollow; (f) P6 primary and specialty stocks with the break. | The outpatient and stock half of the message drawn the only way the rules allow (eras in facets, stocks and flows on separate axes, establishments beside every count). Its 54-row table is appendix Table S49. | Same plate mode; the "definition break" annotations inside (d) and (f) stay (annotations, not titles). Legend ≤ 300 words. |
| Figure 4 | figure | `fig4_triangulation` (journal/figures, 08c) | (a) PIE by definition and source with the 2022 discrepancy declared; (b) JUNAEB by level, "not estimable" never drawn as zero; (c) ENDIDE 2022 and ENCAVI 2023–24 design-based percentages, imprecise domains greyed; (d) indices 2021 = 100 declared as indices; (e) five strips per 100 000 residents, stocks hatched; (f) principal F84 in DEIS vs GRD (coverage comparison). | Carries the convergence claim and the two external anchors (education; population benchmarks) and the only homologous cross-registry comparison. | Same plate mode; strip labels inside (e) are axis labels and stay. Legend ≤ 300 words; the (d) sentence must say "indices, not rates"; the (f) sentence must carry "a coverage comparison between two registries of the same event, not a probability". |
| Table 1 | table | `T2_grd_core` (tables/), 25 of 45 rows | GRD hospital core 2019–2024: panel (hospitals observed/fixed; episodes observed, fixed, strict hospitalisation); F84 any position observed n and rate (95% CI), fixed n and rate, principal n and rate, secondary-only n (%); strict hospitalisation F84 n and rate; CMA F84 n and rate; persons within year and episodes per person; crude rates both sexes, males, females and WHO-standardised both sexes per 100 000 residents; definition sensitivity (full F84 family n, F84.0-only n, episodes whose only F84 code is F84.2). | The primary estimand with exact intervals and each pre-specified sensitivity side by side; prints the panel 65/65/65/65/68/72, n beside every %, the "episodes with documented F84" wording and the 87-episode difference between variants. Full table = appendix Table S37. | Row whitelist by (Block, Indicator) in `journal_config.TABLE_ROWS["T2_grd_core"]` (list below); cells byte-identical to the CSV before the number pass; the two "mean (median)" coding-depth rows are EXCLUDED (journal wants mean (SD)/median (IQR); the means are in the text and in Figure 2c); 10 pt bold heading, 8 pt body, 8 pt bold block headings, mid-height decimals and "100 000" from the number pass, en rules in ranges; landscape section as today; note cut to source, unit, panel and the two standing-rule sentences. |
| Table 2 | table | `T7_models` (tables/) + `T7_models_numeric.csv` (row-aligned), 29 of 54 rows | Pre-specified quasi-Poisson models: estimand, series, specification, years, n, APC (95% CI), p, Pearson dispersion. | Where 35·9% (30·0–42·1) becomes 32·9–63·9% across specifications, where per-establishment and per-resident growth diverge and where dispersion shows why quasi-Poisson was needed. Full 54-row and 220-specification tables = appendix Tables S82 and S83. | Row whitelist by `model_id` (list below) matched through `T7_models_numeric.csv` row index; Notes column dropped; p value column recomputed from the raw `p_value` column of `T7_models_numeric.csv` (equal to `mdl__<model_id with 'sin_rett'→'variant'>__p_value` in values): two significant figures, "<0·0001" when p < 0·0001, never by rewriting the "< 0.001" string; the other cells byte-identical; 10/8/8 pt; landscape. |

**Table 1 whitelist** (`Block` | `Indicator`, exact strings of `T2_grd_core.csv`, in file order):
Panel and episodes | Hospitals observed (n) · Fixed-panel hospitals (n) · GRD episodes, observed panel, all activity (n) · GRD episodes, fixed panel of 65, all activity (n) · GRD episodes, strict hospitalisation (n) —
Episodes with documented F84 | F84 in any position, observed panel (n) · F84 in any position, observed panel, per 100,000 episodes (95% CI) · F84 in any position, fixed panel of 65 (n) · F84 in any position, fixed panel of 65, per 100,000 episodes (95% CI) · F84 principal, observed panel (n) · F84 principal, observed panel, per 100,000 episodes (95% CI) · F84 as secondary diagnosis only, n (% of episodes with F84) —
Activity type (observed panel) | Strict hospitalisation: F84 any position (n) · Strict hospitalisation: F84 any position, per 100,000 episodes (95% CI) · Major ambulatory surgery: F84 any position (n) · Major ambulatory surgery: F84 any position, per 100,000 episodes (95% CI) —
Unique persons (within each year only) | Persons with F84 any position (n, within year) · F84 episodes per person (ratio) —
Per 100,000 population (INE base 2017, residence) | Crude rate, both sexes, F84 any position (95% CI) · WHO age-standardised rate, both sexes, F84 any position (95% CI) · Crude rate, males, F84 any position (95% CI) · Crude rate, females, F84 any position (95% CI) —
Definition sensitivity | Alternative variant, Full F84 family (including Rett syndrome): F84 any position, observed panel (n) · F84.0 childhood autism only (identical in both variants): any position, observed panel (n) · Difference between variants: episodes whose only F84 code is F84.2 (n).
(25 rows; the Block strings are printed as 8 pt bold internal headings; "Indicator" and "Unit" columns keep their text.)

**Table 2 whitelist** (`model_id` of `T7_models_numeric.csv`, in file order; 29 rows):
`grd_rate:sin_rett:observed:all:any:none:2019-2024`, `grd_rate:sin_rett:observed:all:any:depth:2019-2024`, `grd_rate:sin_rett:observed:all:any:disruption:2019-2024`, `grd_rate:sin_rett:observed:all:any:none:2021-2024`, `grd_rate:sin_rett:fixed65:all:any:none:2019-2024`, `grd_rate:sin_rett:observed:hospitalisation:any:none:2019-2024`, `grd_rate:sin_rett:observed:all:principal:none:2019-2024`, `grd_rate:sin_rett:fixed65:all:principal:none:2019-2024`, `grd_rate:strict_autism_f840:observed:all:any:none:2019-2024`, `grd_hospital:sin_rett:observed:any:none:2019-2024:model`, `grd_hospital:sin_rett:observed:any:none:2019-2024:cluster`, `grd_hospital:sin_rett:observed:any:depth:2019-2024:model`, `grd_hospital:sin_rett:observed:any:ri_none:2019-2024:random_intercept`, `grd_pop:sin_rett:any:TOTAL:crude:2019-2024`, `grd_pop:sin_rett:any:TOTAL:age_adjusted:2019-2024`, `grd_pop:sin_rett:any:HOMBRE:age_adjusted:2019-2024`, `grd_pop:sin_rett:any:MUJER:age_adjusted:2019-2024`, `a05_entry:strict_autism:pop:none:2021-2025`, `a05_entry:strict_autism:estab:none:2021-2025`, `a05_entry:strict_autism:stable_pop:none:2021-2025`, `a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025`, `p2_dec:none:2019-2025`, `p2_dec:estab:2019-2025`, `p2_dec:stable:2019-2025`, `p2_dec:naneas:2023-2025`, `p6_primary:strict_autism:none:2021-2025`, `p6_primary:strict_autism:estab:2021-2025`, `pie_harmonised:none:2019-2025`, `deis_principal:sin_rett:none:2019-2024`.
Columns printed: Estimand · Series / variant · Specification (panel; activity; position; denominator/offset; covariates; family) · Years · n (obs.) · APC % (95% CI) · p value · Dispersion (Pearson χ²/df). Estimand groups are the 8 pt bold internal headings (the Estimand cell is printed once per group, as a heading row).

---

## 3. Article structure, paragraph map and word budgets

Word budget (manuscript text = Introduction–Conclusion, measured with `prose_en.word_counts(...)["core_body"]` on the journal blocks BEFORE the number pass; Summary, panel, legends, tables and declarations excluded): **Introduction 400 · Methods 1350 · Results 1650 · Discussion 1000 · Conclusion 80 → 4480; hard ceiling 4800; floor 3500.** Summary ≤ 250. Research in context ≈ 420. Body legends ≤ 300 words each (Figure 1 ≤ 160). Declarations are not counted.

Every paragraph below names its source in `prose_en.py` (line of the `doc.p(` call) so builder A lifts the text and its key expressions from there; "[OPT]" paragraphs are un-tagged and compressed as stated; new text is marked NEW. Appendix citations must appear in the order of section 4 (the numbering is frozen; a test asserts first-citation order is ascending). The dataset citation keys appear ONLY in the "Official sources" sentence and in the order given in section 5.

### Introduction (400 words; 4 paragraphs)
- ¶1 (L497; ≈100): keep; citations in this order: zeidan2022 (drop santomauro2025), russell2022, hansen2015, lundstrom2015, shaw2025, lord2022.
- ¶2 (L505; ≈110): compress: "Latin America contributes little to this evidence: population-based prevalence estimates exist for few countries, caregiver surveys document long diagnostic delays and access barriers [montielnava2024], and routinely collected records have rarely been analysed. Chile has a segmented health system in which the public insurer FONASA covers most of the population (share from `share_fonasa_ine_pct_2025` = 84·8% in 2025, cited from the study's own coverage table) and private ISAPRE insurers a shrinking minority (`share_isapre_ine_pct_2025`); it has one urban prevalence estimate [yanez2021], one school-register estimate [romanurrestarazu2025] and clinical guidelines for early detection since 2011 (no citation). Law 21.545, in force since March 2023, … [ley21545]." Dropped citations: paula2011, fombonne2016, becerril2011, minsal2011, irarrazaval2023.
- ¶3 (L514; ≈95) and ¶4 (L521; ≈95): keep, trimming adjectives.

### Methods (1350 words)
- *Study design and setting* (L531; ≈130): keep; cites vonelm2007, benchimol2015, heidari2016; replace "The analysis plan (appendix) was pre-specified" with "The applied methodology, with every estimator and equation, is in the appendix (Part A, Tables S1–S10); the study is reported according to STROBE and RECORD (appendix Table S11) and the pre-specified analysis plan is reproduced in the appendix (Part A, section A9); every deviation is recorded in the decision log named in the data sharing statement." Keys `ine_pop_total_2019`, `ine_pop_total_2025`.
- *Data sources and units of observation* ¶1 GRD/DEIS (L541; ≈170): keep; "appendix Table S12 and Figure 1 describe the sources"; add "(counts of Figure 1: appendix Table S13)"; drop the cid2024 clause ("used since 2020 as a payment mechanism" → "the IR-GRD system used by FONASA"); panel sentence cites appendix Table S14; identifier sentence cites Table S15. Keys as in L541 (`grd_diagnosis_positions`, `grd_hospitals_observed_{y}` series, `grd_fixed_panel_n`, `grd_hospitals_ever_observed_n`).
- ¶2 REM (L552; ≈150): keep; add "reporting completeness by module and year, with explicit zero, missing and not-reported as distinct states, is in appendix Figure S1"; code dictionary Table S16; definition breaks Table S17; reporting establishments Table S18. Key `rem_pathway_codes_n`.
- ¶3 surveys and education (L562; ≈130): keep; add "item wording verbatim: appendix Tables S19 (ENDIDE, ENCAVI) and S20 (JUNAEB)"; the disability rule sentence: "Autism was identified from the survey questions as reported by the respondent or caregiver; no disability was inferred from a diagnosis."
- ¶4 NEW "Official sources" (from L570 OPT, ≈75 words, no longer optional): "Official sources: GRD files [fonasa_grd], DEIS discharges [deis_egresos], REM [minsal_rem], INE population projections [ine2019], FONASA beneficiaries [fonasa_beneficiarios], ENDIDE 2022 [endide2022], ENCAVI 2023–24 [encavi2023], PIE registers [mineduc_apuntes60; mineduc_sinaces2026] and JUNAEB [junaeb_eve]; the sensitivity layers (INE base 2024 and Census 2024, APS enrolment, ISAPRE, REM-20) are cited in the appendix. Provenance of the `prov_artefacts_n` artefacts (`prov_gb_total` GB) with SHA-256 hashes: appendix Tables S21–S22."
- *Case definitions and definition variants* (L580; ≈200): keep; "this article presents the F84 family excluding Rett syndrome (F84.2); the full-family variant is compared series by series in appendix Figure S2 and Table S24 (the difference is `grd_f84_any_n_rett_only_difference_2024` episodes in 2024)"; subcodes by position appendix Table S23. Education definitions (L595 OPT) compressed to one sentence inside this paragraph.
- *Denominators and coverage layers* (L602; ≈170): keep; cites appendix Table S25 (layers), Figure S3/Table S26 (Census sensitivity), Tables S27–S29 (schemas), Tables S30–S31 (crosswalk), Figure S4/Table S32 (age–sex coverage).
- *Statistical analysis* ¶1 (L614; ≈190): keep; cites ahmad2001, fay1997, wedderburn1974; ¶2 (L628; ≈150): keep without wolter2007 ("Taylor linearisation (appendix Part A, M4, equation 23)"); add the one-sentence sensitivity list compressed from L640: "Pre-specified sensitivities (appendix Table S6): fixed versus observed hospital panel, strict hospitalisation versus all activity, principal versus any position, F84.0 only, coding-depth adjustment and stratification, the 2020–2021 disruption indicator, the 2021–2024 window, hospital fixed and random effects, stable REM panels, per-establishment offsets, June versus December stocks, and the Census 2024 and base-2024 denominators." Model diagnostics: appendix Figure S5, Table S33. Key `models_n_variant`.
- *Reproducibility controls* (L656; ≈70): keep; cites appendix Tables S34–S35 and Figure S6. Keys `controls_families_prespecified_n`, `t8_rows`.
- *Role of the funding source* (L670), *Ethics* (L673), *Use of artificial intelligence in the research process* (L678): keep verbatim (≈140 together).

### Results (1650 words)
- *Sources and coverage* (from L686; ≈110): compress to: GRD records `grd_records_total_2019`/`_2024`, hospitals series, fixed-panel share `grd_records_fixed65_share_2024`, hospitals added (`grd_hospitals_added_2023_n`, `grd_hospitals_added_2024_only_n`), A05 reporting establishments series (`a05_autism_entries_estab_{y}`, YEARS_A05) with the 2025 fall (`a05_autism_entries_estab_change_2025_2024`), P2 establishments series, FONASA share 2019/2025, Census ratio (`ine_ratio_censo2024_base2017_2024`). Cites Figure 1, appendix Figure S1, Table S14. The June 2020 sentence moves to the pathway section.
- *Hospital core: GRD episodes with documented F84* ¶1 (L714; ≈200): keep in full (Table 1, Figure 2; appendix Figure S7 for the subcode/position dynamics; complete series appendix Table S36; full table Table S37). ¶2 depth and persons (L731; ≈95): keep (Figure 2c; multiplicity appendix Figure S8/Table S38). ¶3 age, sex, population (L741; ≈100): keep (appendix Tables S39–S40; Figure 2d). ¶4 NEW compression of L752 + L764 (≈120): "Hospitals were heterogeneous: in 2024 the rate ranged from `grd_hosp2024_rate_min` to `grd_hosp2024_rate_max` per 100 000 episodes (ratio `grd_hosp2024_rate_ratio_max_min`; median `grd_hosp2024_rate_median`, IQR `grd_hosp2024_rate_q1`–`grd_hosp2024_rate_q3`), highest in paediatric hospitals (Figure 2e; appendix Figure S9, Table S41; concentration and rank stability Figure S10, Table S42); `grd_hosp_rr_fixed_effects_none_n_above1` hospitals had a fixed-effect rate ratio above one and `grd_hosp_rr_fixed_effects_none_n_below1` below one, random-intercept SD `apc_grd_hospital_ri_re_sd`. Episodes with F84 as a secondary diagnosis were admitted mainly for [chapters named in appendix Figure S11, Tables S43–S44]. DEIS discharges with principal F84 in all establishments rose from `deis_f84_principal_n_2019` (`k.rate('deis_f84_principal', 2019)`) to `deis_f84_principal_n_2024` (`k.rate('deis_f84_principal', 2024)`), `deis_f84_principal_snss_share_2024` of them in SNSS establishments; the DEIS:GRD principal-F84 count ratio was `deis_vs_grd_ratio_f84_principal_2024` in 2024, a coverage comparison between two unlinked registries of the same event and not a probability (appendix Tables S45–S46, Figures S12–S13, Tables S47–S48)."
- *Aggregate administrative pathway in primary and specialty care* ¶1 (L775 + the high-risk clause of L782; ≈110): keep; Figure 3; appendix Table S49 (T3_rem_pathway), Table S50 (complete code × year), Figures S14–S15 and Tables S51–S52 (A03 detail). Keys `a03_2023_high_2023`, `a03_2023_high_2024`, `a27_assisted_referral_{y}`. ¶2 A05 (L791; ≈125): keep; appendix Figure S16/Table S53 (stable panel), Figure S17/Table S54 (concentration across establishments), Figure S18/Table S55 (standardised rates), Figure S19/Table S56 (age–sex), Figure S20/Table S57 (definition sensitivity). ¶3 P2/P6/A28 (L806; ≈200): keep, adding the June 2020 sentence from L686 (`p2_jun_dec_ratio_2020`); appendix Figure S21/Table S58 (P2/P6 detail), Figure S22/Table S59 (June vs December), Figure S23/Table S60 (seasonality), Figure S24/Table S61 (REM-20 capacity, ecological, never a denominator).
- *Population benchmarks* (L854; ≈150): keep; Figure 4c; appendix Table S62 (full survey table with DEFF/RSE flags), Figure S25/Table S63.
- *Educational triangulation* ¶1 (L874; ≈120) and ¶2 (L889; ≈95): keep; Figure 4a–b; appendix Table S64, Figure S26/Table S65, Figure S27/Table S66.
- *Territory* NEW (≈110 words; every number from tidy rows, filters given): "Comuna-level rates of GRD episodes by residence were spatially clustered: global Moran's I of the empirical-Bayes smoothed standardised ratio was 0·340 (queen contiguity; permutation p = 0·001, 999 permutations; 0·230–0·354 across the four weight matrices) [`outputs/tidy/spatial_moran.csv`: variant = sin_rett, scope = comuna, indicator = grd_episodes, value_type = sir_eb, years = 'full period', subset = 'all comunas', weights ∈ {queen, knn4, knn8, idw}; columns morans_i, p_sim, permutations]. After Benjamini–Hochberg control, 12 comunas were high–high, six low–low and one low–high, and Gi* identified 13 hot and six cold spots of 342 [`spatial_lisa.csv`: same filters with weights = queen; counts of lisa_class and gi_class where lisa_bh_reject/gi_bh_reject is True]. Territorial inequality fell as recognition spread: the Gini coefficient across comunas was 0·373 in 2019 and 0·299 in 2024, comunas with at least one episode rose from 242 to 302 of 346 and the top decile's share of episodes fell from 25·7% to 20·6% [`spatial_inequality.csv`: variant = sin_rett, indicator = grd_episodes, years = 2019 / 2024; columns gini, n_comunas_with_events, n_comunas, top_decile_event_share]. Comuna ranks of GRD episodes (residence) and A05 entries (place of care) were weakly correlated (Spearman ρ 0·27, 95% CI 0·16–0·37) [`spatial_correlations.csv`: variant = sin_rett, scope = comuna, indicator_x = grd_episodes, indicator_y = a05_entries, value_type sir_eb; columns rho, rho_lo, rho_hi], a territorial comparison of two unlinked systems with different geographies, not a linkage (appendix Figures S28–S33, Tables S67–S78)." Builder B exposes these rows through `journal_config.tidy_value(file, filters, column)` so the prose never types them.
- *Convergence across systems and sensitivity of the trends* ¶1 (L904; ≈75): keep; Figure 4d–e; appendix Tables S79–S80, Figure S34/Table S81. ¶2 models (L912; ≈240): keep; Table 2; Figure 4f; appendix Figure S35, Tables S82–S83. ¶3 (compressed L936; ≈90): the A05/P2/P6/PIE APCs with CIs: `k.apc('apc_a05_autism_pop')`, `k.apc('apc_a05_autism_estab')`, `k.apc('apc_a05_autism_stable_pop')`, `k.apc('apc_a05_autism_ageadj_total')` (females `apc_a05_autism_ageadj_female`, males `apc_a05_autism_ageadj_male`), `k.apc('apc_p2_dec')`, `k.apc('apc_p2_dec_estab')`, `k.apc('apc_p2_dec_stable')` (panel `p2_tea_dec_stable_panel_n`), `k.apc('apc_p2_dec_naneas_offset')`, `k.apc('apc_p6_primary_autism')` (`apc_p6_primary_autism_estab`), `k.apc('apc_pie_harmonised')`; close with "Dispersion was large in the count models of flows and stocks, and no specification estimates an effect of Law 21.545." ¶4 controls (L952; ≈25): keep (`t8_rows`, `t8_ok`, `t8_differs`; appendix Tables S34–S35).

### Discussion (1000 words) and Conclusion (80)
- ¶1 (L965; ≈125): keep, with two fixes: "with a trough or plateau in 2020" → "hospital counts fell with activity in 2020 while the stocks did not"; "A05 entries grow at 27·9% per reporting establishment against 47·2% per resident, and the P2 stock at 36·3% per establishment against 63·5% as a count" stays, followed by "a gap that bounds the contribution of reporting expansion".
- ¶2 (L977; ≈200): keep; iezzoni1992, song2010; replace "the gap between the growth per establishment and the growth per resident quantifies the contribution of reporting expansion" with "… bounds the contribution of reporting expansion"; "the rate rose within every coding-depth band" → "the rate rose within every coding-depth stratum of three or more diagnoses" (keys of message 3); "the 77-fold range across hospitals" uses `grd_hosp2024_rate_ratio_max_min` (n0).
- ¶3 (L992; ≈130): keep; loomes2017; add from L1003 the ENDIDE clause with the ratio derived in the print funnel: "the survey benchmark in Chilean children (`svy_endide_children_reported_male_pct` / `svy_endide_children_reported_female_pct` = 4·1:1 in ENDIDE) is nearer the passive-ascertainment values than the administrative flows of 2024–2025" (appendix Figure S36, Table S84). fyfe2026, lai2020, hull2020 are dropped with the rest of L1003.
- ¶4 international (L1008; ≈160): keep; russell2022, hansen2015, lundstrom2015, shaw2025; fix the over-claim: "whereas the administrative flows and stocks remain far below what those benchmarks imply" → "whereas the administrative flows and stocks, which are not prevalence, remain far below the number of people those benchmarks imply".
- ¶5 Latin America (L1022; ≈110): keep without paula2011/fombonne2016/montielnava2024 in the first sentence ("population surveys in Brazil and Mexico estimated prevalences of roughly 0·3% and 0·9%" is deleted; the sentence opens with the six-country study [montielnava2024] and the segmented system); garcia2022 stays. L1031 dropped.
- ¶6 implications (L1036; ≈120): keep (keys `a05_autism_entries_2025`, `p6_primary_autism_dec_ratio_2025_2021`, `a28_primary_ratio_2025_2023`, `pie_tea_strict_share_of_pie_pct_2023`, JUNAEB min/max of the 2025 levels).
- ¶7 limitations (L1048; ≈190): keep; add one clause: "and regional and comuna comparisons are ecological (residence for GRD, place of care for REM)". L1062 strengths: one sentence folded into ¶7's opening ("Its strengths — national coverage of every public source, frozen provenance, pre-specified controls and sensitivities — do not remove the following limitations.").
- ¶8 (L1069; ≈65): keep.
- Conclusion (L1075; ≈80): keep.

### Declarations (not counted; after the Conclusion, before References, in this order and with these headings)
Contributors (L1084; the second-author sentence stays as an author-supplied placeholder in square brackets); Declaration of interests (L1092); Data sharing statement (L1094; cites appendix Table S12 and Table S85 = data dictionary; "URL and DOI to be inserted at acceptance" is a placeholder the author team must fill — the journal refuses "undecided", so the statement says data WILL be shared, what, when and where); Funding (L1105); Acknowledgements (L1107); Declaration of the use of artificial intelligence (L1111; last, separate heading; tool versions are author-supplied). Then References (30, superscript numbers in the text), then the tables (Table 1, Table 2, each with heading and note), then the figures one per page with their legends.

---

## 4. Supplement (ONE English PDF), in order of first citation from the article

Front matter (pp 1–3): title; authors; the sentence "This appendix accompanies the article … It presents the F84 family excluding Rett syndrome (F84.2); the full-family variant is not submitted separately and is compared series by series in Figure S2 and Table S24"; the standing rules stated once (the sentence block of section 0 of this plan, in prose); table of contents with page numbers (two-pass build, section 7.6); page numbers on every page.

### Part A — Applied methodology (the author's binding requirement)
- A1–A7 = `prose_methods_extended.methods_blocks('sin_rett', V, 'en', R=JournalRegistry, first_table=1)` verbatim: M1 design/sources/units/no-linkage; M2 case definitions and code sets; M3 denominators and compatibility; M4 the 26 estimators with the **33 equations** printed once each in numeric order under the estimator that first uses them (crude 1; age-specific 2; DSR, variance, Fay–Feuer 3–5; rate ratio 6; count ratio 7; expected/Byar 8–9; EB 10–11; quasi-Poisson/APC 12–13; FE 14; RI 15; DW 16; Wilson 17; Jeffreys 18; seasonal 19; index 20; Spearman 21; kappa 22; Taylor 23; DEFF 24; Moran, bivariate, LISA, BH, Gi* 25–29; Lorenz, Gini, Theil 30–32; suppression 33) and the estimator map; M5 controls, data states, sensitivity grid; M6 software, seeds, pipeline map; M7 limitations of the methods. Tables S1–S10 = `M1_sources_units` … `M10_reproduction_controls` (all in `extra/tables/`).
- A8 = **Table S11**, STROBE (22 items) + RECORD (13 items) checklist rendered in English from `reporting_checklist.md`, with the "Where" column remapped to the journal sections and S-numbers of this plan and "Status" in English; synthetic key `S_reporting_checklist`.
- A9 = the pre-specified analysis plan, version 1.0 of 4 September 2026, rendered in English (question, DAG, sources and units, variants, estimand hierarchy, models and sensitivities, exclusions and rules); the Spanish original is copied verbatim to `manuscript/04_submission_study/analysis_plan_v1.0_es.md` and its date stamped in A9's first line.
- A10 = appendix references: a separately numbered list (`("refs", None)` at the end of the supplement) covering the 39 keys `methods_blocks` cites plus any key cited in a printed note; it includes the five relocated dataset citations (`ine_base2024`, `ine_censo2024`, `fonasa_aps`, `supersalud_isapre`, `deis_rem20`), `wolter2007`, `who_icd10`, `deis_establecimientos` and the statistical references.

### Part B — Results that did not make the body (first-citation order; source folder in brackets: t = tables/, x = extra/tables/, f = figures/, xf = extra/figures/)

Figures S1–S36:

| S | Key | First cited | Shows | Why it matters / what it adds beyond the body |
|---|---|---|---|---|
| S1 | fig1_sources_coverage (f) | Methods › Data sources ¶2 | REM completeness per module-year (reported/explicit zero/not reported), coverage layers, establishments per module, GRD observed vs fixed, REM-20 retention, breaks | Makes "zero, missing and not reported are distinct" visible; the completeness of every module-year on one page (the 1·3% explicit-zero figure lives in this caption, computed by 08a; never re-typed in prose) |
| S2 | figE28_variant_sensitivity (xf) | Methods › Case definitions | Every series in both variants with absolute and relative differences | The con_rett variant is not submitted; this is where a reviewer sees it changes nothing material |
| S3 | figS10_denominators (f) | Methods › Denominators | INE base 2017 vs base 2024 vs Census 2024, nationally, by region and age; effect on 2024 rates | Denominator sensitivity (the Census effect is derived in the print funnel from `ine_ratio_censo2024_base2017_2024`) |
| S4 | figS11_coverage_age_sex (f) | Methods › Denominators | FONASA, APS, ISAPRE by age and sex 2025; age structures | The population of the public network (71% of children 0–9 in FONASA, `coverage_2025_share_fonasa_ine_age_0_9`) and the selection the Discussion names |
| S5 | figE27_model_diagnostics (xf) | Methods › Statistical analysis | Fitted vs observed, residuals, dispersion of every specification, forest, DW | Justifies quasi-Poisson; dispersion 33·2 of the main GRD model (`apc_grd_any_obs_disp`) |
| S6 | figS15_controls (f) | Methods › Reproducibility controls | Observed vs expected for the numeric module controls, differences listed | Visual proof no control was filled by plausibility |
| S7 | figS2_grd_subcodes (f) | Results › Hospital ¶1 | Subcode mix, position, principal share by subcode, F84.0-only vs family, F84.2 by position | The shift to F84.0 and secondary-only coding behind the 95·5% |
| S8 | EF6_readmission_multiplicity (xf) | Results › Hospital ¶2 | Readmission 30/90/365 d by identifier era, episodes per identifier, persons within year | 1·22 episodes per person is not accumulation across years (eras never crossed) |
| S9 | figS3_grd_hospital_effects (f) | Results › Hospital ¶4 | Fixed effects as RRs, random-intercept shrinkage, rate vs depth, per-hospital 2019 vs 2024 | The heterogeneity the Discussion interprets (28 above one, 19 below) |
| S10 | EF8_hospitals (xf) | Results › Hospital ¶4 | Top-25 rates, rank stability, share of the ten largest, fixed vs added hospitals, Lorenz/Gini | Added hospitals contributed little (fixed panel 96·6% of 2024 episodes) |
| S11 | EF5_codiagnoses (xf) | Results › Hospital ¶4 | Co-diagnoses by chapter, mental-health blocks, principal diagnosis when F84 is secondary | Substantiates "documentation in episodes admitted for other reasons" |
| S12 | figS14_deis_sex_age (f) | Results › Hospital ¶4 | DEIS principal F84 by sex, age, ownership, masking | Independent registry check |
| S13 | EF10_deis_detail (xf) | Results › Hospital ¶4 | DEIS counts/rates, SNSS vs non-SNSS vs masked, homologous comparison, subcodes | Completes the external check; masked rows kept as a state |
| S14 | E12_rem_a03_risk_referral (xf) | Results › Pathway ¶1 | M-CHAT-R/F risk composition, referral of high risk (Wilson CI within code-year), 2024/2025 families | Why eras are not a series |
| S15 | E11_rem_a03_codes_by_era (xf) | Results › Pathway ¶1 | Every A03 code by era incl. the Feb-2019 outlier kept | Transparency about the legacy era |
| S16 | figS6_rem_stable_panel (f) | Results › Pathway ¶2 | All establishments vs stable panel for A05, P2, P6 | Reporting-expansion argument (stable A05 1522 → 6767) |
| S17 | E17_rem_establishment_distribution (xf) | Results › Pathway ¶2 | Lorenz, Gini, top-decile share of REM activity across establishments | Many establishments reporting vs a few reporting more |
| S18 | figS7_rem_education_models (f) | Results › Pathway ¶2 | A05 crude and standardised rates by sex, age-specific rates, P2/P6/PIE fits | Standardised REM rates (14·3 → 90·2) and the fits behind Table 2 |
| S19 | figS8_a05_age_sex (f) | Results › Pathway ¶2 | A05 by age and sex, M:F by age | SAGER for the outpatient series; 46·7% aged 0–9 |
| S20 | E19_rem_definition_era_sensitivity (xf) | Results › Pathway ¶2 | Every REM indicator under strict autism, PDD family and broad pre-2021 | "Definition changes explain part" |
| S21 | E15_rem_p2_p6_detail (xf) | Results › Pathway ¶3 | P2 by region, Dec vs Jun, stock per establishment, ASD per 100 NANEAS, P6 by era | NANEAS share 22·0% → 29·7% |
| S22 | figS5_rem_june_december (f) | Results › Pathway ¶3 | June vs December, never summed; June 2020 collapse | The semester sensitivity of the standing rules |
| S23 | figS13_rem_seasonality (f) | Results › Pathway ¶3 | Monthly index of A05 and A03 | The 2020 fall is in reporting establishments, not persons |
| S24 | figE22_rem20_capacity (xf) | Results › Pathway ¶3 | REM-20 discharges/bed-days, retention, ecological association with GRD F84 (ρ 0·70 lives in this caption, computed by 15) | Capacity context; never a population denominator |
| S25 | figE23_surveys_detail (xf) | Results › Benchmarks | Estimates by domain with DEFF, RSE, case thresholds; unreliable domains greyed | Why most sex/age domains are orders of magnitude |
| S26 | figE24_education_detail (xf) | Results › Education | PIE by definition/source, 2022 discrepancy, shares, special schools, 2023 sex split, exceptional entry | Source of 10·1% (`pie_tea_strict_share_of_pie_pct_2023`) |
| S27 | figS12_junaeb_sex_level (f) | Results › Education | JUNAEB % by sex and level, M:F 2·0–2·9, weighted vs unweighted | SAGER for school cohorts |
| S28 | figS9_regional_maps (f) | Results › Territory | Equal-area (Albers) regional maps: GRD 2024 by residence, A05 by place of care, warning; the regional ρ 0·38 lives in this caption | Journal: equal-area projections |
| S29 | E40_maps_grd_smoothed_ratio (xf) | Results › Territory | Comuna maps of SIR, EB-smoothed SIR, suppression | The territorial pattern behind Moran's I |
| S30 | E42_lisa_gistar_maps (xf) | Results › Territory | LISA and Gi* classes after BH | The local clusters |
| S31 | E47_lorenz_theil (xf) | Results › Territory | Lorenz curves, Gini, Theil decomposition by year | Territorial inequality falling as recognition spreads |
| S32 | E49_regional_summary (xf) | Results › Territory | Regional rates, SIR and ranks | Regional reading |
| S33 | E46_sae_deprivation (xf) | Results › Territory | Association with SAE deprivation (ecological) | Context of supply and deprivation |
| S34 | figE26_cross_source (xf) | Results › Convergence ¶1 | Every system as index, raw value, population rate and value per reporting unit | The per-reporting-unit reading |
| S35 | figS4_models_cpa (f) | Results › Convergence ¶2 | Observed and fitted, forests across sensitivities, standardised rates, indices | Visual form of Table 2 with every CI |
| S36 | figE26b_sex_ratio_multisource (xf) | Discussion ¶3 | M:F in every source: trend, by age, counts vs standardised, forest, both variants | The SAGER synthesis |

Tables S1–S85 (S1–S10 methods tables, S11 checklist as above):

| S | Key | First cited | Shows / adds |
|---|---|---|---|
| S12 | T1_sources (t) | Methods › Data sources ¶1 | 15 sources: provider, unit, period, coverage, geography, stock/flow, denominator, breaks, linkage, files |
| S13 | T_dataflow_counts (x) | Methods › Data sources ¶1 | Every count printed on Figure 1 with unit, source, column, drawn/not drawn; the exclusions; carries the "how it is drawn" note |
| S14 | ST1_grd_hospital_panel (t) | Methods › Data sources ¶1 | 72 hospitals × year, fixed-panel membership |
| S15 | ST8_grd_identifier_audit (t) | Methods › Data sources ¶1 | Identifier validity, uniqueness, format change, 0 shared identifiers 2020/2021 |
| S16 | ST2_rem_code_dictionary (t) | Methods › Data sources ¶2 | 57 codes verified against each year's dictionary |
| S17 | S_definition_breaks (t) | Methods › Data sources ¶2 | One row per break |
| S18 | ST3_rem_reporting_establishments (t) | Methods › Data sources ¶2 | Establishments per code per year, stable panel |
| S19 | ST5_survey_items (t) | Methods › Data sources ¶3 | ENDIDE/ENCAVI items verbatim, design variables (disability rule) |
| S20 | ST6_junaeb_items (t) | Methods › Data sources ¶3 | JUNAEB item, filter, weight, estimability |
| S21 | ST7_provenance (t) | Methods › Official sources | 182 artefacts, SHA-256 |
| S22 | ST7b_manifest_checks (t) | Methods › Official sources | Manifest agreement |
| S23 | ST10_grd_f84_subcodes (t) | Methods › Case definitions | Subcodes × year × position; F84.2 flagged |
| S24 | E28_variant_sensitivity (x) | Methods › Case definitions | Values of Figure S2 |
| S25 | T4_denominators_coverage (t) | Methods › Denominators | Layers by year with retention (was body Table 3) |
| S26 | S10_denominator_sensitivity (t) | Methods › Denominators | Values of Figure S3 |
| S27–S29 | ST12a_fonasa_schema, ST12b_isapre_rules, ST12c_aps_panel (t) | Methods › Denominators | Schema breaks and harmonisation |
| S30–S31 | ST4a_comuna_crosswalk_summary, ST4b_comuna_unmatched (t) | Methods › Denominators | Crosswalk audit |
| S32 | S11_coverage_age_sex (t) | Methods › Denominators | Values of Figure S4 |
| S33 | E27_model_diagnostics (x) | Methods › Statistical analysis | Main specification per estimand with diagnostics |
| S34 | T8_controls_compact (t) | Methods › Reproducibility | 48 rows; 205 indicator-year controls, 191 matched, 14 differed (was body Table 7) |
| S35 | E79_reproduction_controls_by_family (x) | Methods › Reproducibility | The 22 control files; the description prints the TABLE's own totals row, not the values-file tally (5883/5504/353/26 is `controls_csv_*`, quoted only in the Methods text) |
| S36 | E60_grd_annual_full (x) | Results › Hospital ¶1 | Complete annual GRD series by panel, activity, position |
| S37 | T2_grd_core (t), all 45 rows | Results › Hospital ¶1 | The unmodified full table of which Table 1 is the cut |
| S38 | EF6_readmission_multiplicity (x) | Results › Hospital ¶2 | Values of Figure S8 |
| S39 | ST9_grd_age_sex (t) | Results › Hospital ¶3 | Age–sex cells (SAGER) |
| S40 | S_grd_population_rates (t) | Results › Hospital ¶3 | Crude and WHO-standardised rates by sex |
| S41 | S_hospital_rates_2024 (t) | Results › Hospital ¶4 | 72 hospitals with rate, CI, fixed-effect RR |
| S42 | EF8_hospitals (x) | Results › Hospital ¶4 | Values of Figure S10 |
| S43 | EF5_codiagnoses (x) | Results › Hospital ¶4 | Values of Figure S11 |
| S44 | E8_grd_principal_when_secondary (x) | Results › Hospital ¶4 | Principal diagnosis when F84 is secondary — the direct answer to 95·5% |
| S45 | ST11a_deis_annual (t) | Results › Hospital ¶4 | DEIS totals, SNSS share, masking, F84 by position |
| S46 | ST11b_deis_vs_grd (t) | Results › Hospital ¶4 | Principal-vs-principal coverage comparison with its non-probability note; the any/principal ratio column is NOT printed |
| S47 | S14_deis_sex_age (t) | Results › Hospital ¶4 | Values of Figure S12 |
| S48 | EF10_deis_detail (x) | Results › Hospital ¶4 | Values of Figure S13 |
| S49 | T3_rem_pathway (t), 54 rows | Results › Pathway ¶1 | REM pathway by module, code, era, establishments (was body Table 2) |
| S50 | E69_rem_code_year_full (x) | Results › Pathway ¶1 | Complete code × year with establishments and stable totals |
| S51–S52 | E12_rem_a03_risk_referral, E11_rem_a03_codes_by_era (x) | Results › Pathway ¶1 | Values of Figures S14–S15 |
| S53 | S6_stable_panel (t) | Results › Pathway ¶2 | Values of Figure S16 |
| S54 | E17_rem_establishment_distribution (x) | Results › Pathway ¶2 | Values of Figure S17 |
| S55 | S_a05_standardised_rates (t) | Results › Pathway ¶2 | A05 crude and standardised by sex and year |
| S56 | ST13_a05_age_sex (t) | Results › Pathway ¶2 | A05 by age, sex, category, year with establishments |
| S57 | E19_rem_definition_era_sensitivity (x) | Results › Pathway ¶2 | Values of Figure S20 |
| S58 | E15_rem_p2_p6_detail (x) | Results › Pathway ¶3 | Values of Figure S21 |
| S59 | ST14_p2_p6_june_december (t) | Results › Pathway ¶3 | December vs June with establishments and stable panel |
| S60 | S13_rem_seasonality (t) | Results › Pathway ¶3 | Values of Figure S23 with "not reported" vs "n/e" states |
| S61 | E22_rem20_capacity (x) | Results › Pathway ¶3 | Values of Figure S24 |
| S62 | T5_survey_benchmarks (t) | Results › Benchmarks | Survey estimates by domain with design, DEFF, RSE, precision flags (was body Table 4) |
| S63 | E23_surveys_detail (x) | Results › Benchmarks | Values of Figure S25 |
| S64 | T6_education (t) | Results › Education | PIE series, SINACES, special schools, JUNAEB (was body Table 5) |
| S65 | E24_education_detail (x) | Results › Education | Values of Figure S26 |
| S66 | S12_junaeb_sex_level (t) | Results › Education | Values of Figure S27 |
| S67 | S9_regional_rates (t) | Results › Territory | Regional rates 2024 |
| S68 | E40_grd_smoothed_ratio_comuna (x) | Results › Territory | Comuna SIR and EB-smoothed values |
| S69 | E42_local_class_counts (x) | Results › Territory | LISA/Gi* class counts (the source of 12/6/1 and 13/6) |
| S70 | E51_lisa_significant_comunas (x) | Results › Territory | The significant comunas named |
| S71 | E43_moran_sensitivity_main (x) | Results › Territory | Moran's I across weights and value types |
| S72 | E50_moran_gistar_all (x) | Results › Territory | All indicators |
| S73 | E47_inequality_gini_theil (x) | Results › Territory | Gini and Theil by year (the source of 0·373 → 0·299) |
| S74 | E49_regional_summary (x) | Results › Territory | Values of Figure S32 |
| S75 | E44_correlation_matrix_comuna (x) | Results › Territory | Rank correlations between systems by comuna, with the warning |
| S76 | E48_rank_stability (x) | Results › Territory | Rank stability across years |
| S77 | E46_sae_association (x) | Results › Territory | Values of Figure S33 |
| S78 | E41_rem_comuna_place_of_care (x) | Results › Territory | REM comuna values by place of care (companion of the warning) |
| S79 | S_convergence_index (t) | Results › Convergence ¶1 | Indices 2021 = 100 and 2019 = 100 |
| S80 | F4_triangulation_series (t) | Results › Convergence ¶1 | Values of Figure 4e |
| S81 | E26_cross_source (x) | Results › Convergence ¶1 | Values of Figure S34 |
| S82 | T7_models (t), all 54 rows | Results › Convergence ¶2 | The unmodified full table of which Table 2 is the cut (with Notes column) |
| S83 | T7_models_cpa_full (t), 220 rows | Results › Convergence ¶2 | Every specification |
| S84 | E26b_sex_ratio_multisource (x) | Discussion ¶3 | 72 ratios with CIs (values of Figure S36) |
| S85 | E80_tidy_data_dictionary (x) | Data sharing statement | Data dictionary of the tidy tables deposited |

Each supplementary figure is preceded by its bilingual presentation sentence (`supplementary_material.figure_intro(key, label, 'en')`), takes one page with its legend (10 pt; legends may continue on the next page with the "(continued)" label), and each table carries its title and note from `titles.json` (S-number remapped, section 7.7).

---

## 5. Dropped items (with reasons)

Figures (19 of the corpus's 54): `figS1_grd_variants` (duplicate of Figure S2 = figE28); `EF1_seasonality_monthly`, `EF2_length_of_stay`, `EF3_episode_features`, `EF4_severity_weight`, `EF7_age_detail` (descriptive hospital detail with no bearing on the message); `EF9_territory` (duplicates the spatial set); `E13_rem_a05_regional`, `E16_rem_a27_a28_regional` (place-of-care regional flows for 2023–2025 only, ecological); `E14_rem_a05_age_sex` (duplicate of Figure S19); `E18_rem_monthly_series` (duplicate of Figure S23); `figE20_population_structure`, `figE21_insurance_coverage` (duplicate of Figure S4 and Table S25); `figE25_junaeb_detail` (duplicate of Figures S26–S27); `E41_maps_rem_place_of_care` (table kept as S78; the maps duplicate Figure S28's warning); `E43_moran_scatter_weights`, `E44_correlation_matrix`, `E48_rank_stability` (tables kept as S71, S75, S76; the plates add nothing); `E45_bivariate_moran` (with its table: invites a cross-source reading of two unlinked systems). All remain in the repository named in the data sharing statement.

Tables (48 of the corpus's 125): duplicates `F3_rem_pathway_data` (Table S49 + S50 cover it), `S5_june_december` (S59), `S8_a05_age_sex` (S56), `T8_controls` full (S34 + S35), `S15_controls_scatter` (Figure S6 carries its values); hospital detail `E1_grd_seasonality`, `E2_grd_length_of_stay`, `E3_grd_los_by_age`, `E4_grd_episode_features`, `E5_grd_weight_and_groups`, `E6_grd_codiagnoses_top25`, `E7_grd_codiagnosis_chapters`, `E9_grd_readmission`, `E10_grd_multiplicity`, `E11_grd_territory_region`, `E12_grd_age_single_year` and the companions `EF1`, `EF2`, `EF3`, `EF4`, `EF7`, `EF9` (companions of dropped plates); `E13`, `E14`, `E16`, `E18` REM companions; `E20`, `E21`, `E25`; `E45_bivariate_moran_pairs`; complete-data tables `E61`–`E68`, `E70`–`E78`, `E81` (re-list what S36, S50, S83 and the deposited tidy files carry; `E78` duplicates S83). Body relocations are not drops: `T3`, `T4`, `T5`, `T6`, `T8_controls_compact` and `fig1_sources_coverage` are in Part B.

Text dropped: the corpus's "Supplementary methods S1–S5" (superseded by Part A) and the "Optional material index"; the [OPT] paragraphs L1003 (except the ENDIDE clause), L1031, L1062 (except one sentence).

---

## 6. References: exactly 30, Vancouver, numbered by order of first citation, superscript after punctuation

| # | Key | First cited in |
|---|---|---|
| 1 | zeidan2022 | Introduction ¶1 |
| 2 | russell2022 | Introduction ¶1 |
| 3 | hansen2015 | Introduction ¶1 |
| 4 | lundstrom2015 | Introduction ¶1 |
| 5 | shaw2025 | Introduction ¶1 |
| 6 | lord2022 | Introduction ¶1 |
| 7 | montielnava2024 | Introduction ¶2 |
| 8 | yanez2021 | Introduction ¶2 |
| 9 | romanurrestarazu2025 | Introduction ¶2 |
| 10 | ley21545 | Introduction ¶2 |
| 11 | vonelm2007 | Methods › Study design |
| 12 | benchimol2015 | Methods › Study design |
| 13 | heidari2016 | Methods › Study design (SAGER stays in the article) |
| 14 | fonasa_grd | Methods › Official sources |
| 15 | deis_egresos | Methods › Official sources |
| 16 | minsal_rem | Methods › Official sources |
| 17 | ine2019 | Methods › Official sources |
| 18 | fonasa_beneficiarios | Methods › Official sources |
| 19 | endide2022 | Methods › Official sources |
| 20 | encavi2023 | Methods › Official sources |
| 21 | mineduc_apuntes60 | Methods › Official sources |
| 22 | mineduc_sinaces2026 | Methods › Official sources |
| 23 | junaeb_eve | Methods › Official sources |
| 24 | ahmad2001 | Methods › Statistical analysis ¶1 |
| 25 | fay1997 | Methods › Statistical analysis ¶1 (Fay–Feuer limits of Table 1's standardised rates) |
| 26 | wedderburn1974 | Methods › Statistical analysis ¶1 |
| 27 | iezzoni1992 | Discussion ¶2 |
| 28 | song2010 | Discussion ¶2 |
| 29 | loomes2017 | Discussion ¶3 |
| 30 | garcia2022 | Discussion ¶5 |

`journal_config.REFERENCE_KEYS` is this list in this order; a test asserts `prose_en.citation_keys(article_blocks)` equals it exactly (order and content) and that no `[OPT]` paragraph remains.

Dropped from the 50 keys the corpus article cites (reason): `santomauro2025` (the "about 1%" sentence rests on zeidan2022); `paula2011`, `fombonne2016` (the Brazil/Mexico prevalence sentence is deleted; the six-country study covers Latin America); `becerril2011` (segmentation rests on the study's own coverage data, `share_fonasa_ine_pct_2025`, `share_isapre_ine_pct_2025`); `minsal2011` (the guideline clause is stated without citation, dated); `irarrazaval2023` (ley21545 suffices); `cid2024` (payment-mechanism clause deleted); `wolter2007` (Taylor linearisation cited in the appendix at estimator 23); `ine_base2024`, `ine_censo2024`, `fonasa_aps`, `supersalud_isapre`, `deis_rem20` (sensitivity-layer datasets; cited in the appendix where Figures S3–S4, S24 and Tables S25–S32, S61 use them); `fyfe2026`, `lai2020`, `hull2020` (dropped with paragraph L1003); `romanurrestarazu2018`, `cid2016`, `breinbauer2022`, `acevedo2025` (dropped with paragraph L1031). Reference formatting: six authors or fewer all listed, seven or more the first three then "et al" (the shared formatter lists six; the journal build patches `format_vancouver` with limit rule (>6 → first 3), see 7.3), en rule in page ranges, "Available from:" for URLs, DOIs as "doi:".

---

## 7. API contract (module names, signatures, paths, flags)

All journal modules live in `study/journal/`; they import the corpus modules by adding `study/` to `sys.path` (as `tests/` do) and `pipeline/10_manuscript.py` through `importlib.util.spec_from_file_location("m10", …)`. Nothing in the corpus is modified except the flagged journal modes of 7.3 and 7.4, whose defaults keep today's behaviour byte for byte.

### 7.1 `journal_config.py` (builder B; imported by A, S and build_journal)
```
VARIANT = "sin_rett"; LANGS = ("en", "es"); SUBMISSION_LANG = "en"
OUT_DIR = CFG.SUBMISSION                                   # manuscript/04_submission_study/
PLATE_DIR = {lang: CFG.OUT / VARIANT / lang / "journal" / "figures"}
BODY_FIGURES = ["fig1_dataflow", "fig2_grd_core", "fig3_rem_pathway", "fig4_triangulation"]
BODY_TABLES  = ["T2_grd_core", "T7_models"]
TABLE_ROWS   = {"T2_grd_core": [(block, indicator), ...25], "T7_models": [model_id, ...29]}   # section 2
TABLE_COLUMNS = {"T7_models": [...8 columns]}                # section 2
SUPP_FIGURES = [...36 keys in the order of section 4]
SUPP_TABLES  = ["M1_sources_units", ..., "M10_reproduction_controls", "S_reporting_checklist", "T1_sources", ...85]
SUPP_PART_A  = ["M1".."M7", "A8_checklist", "A9_analysis_plan", "A10_references"]
REFERENCE_KEYS = [...30 keys, section 6]; DROPPED_REFERENCE_KEYS = {key: reason}
WORD_BUDGET = dict(summary=250, panel=430, introduction=400, methods=1350, results=1650, discussion=1000,
                   conclusion=80, core_body_max=4800, core_body_min=3500, legend_max=300, legend_fig1_max=160)
PROTECTED_TOKENS = [r"\bF84(?:\.\d)?\b", r"\b\d{8}\b", r"\bP6\d{6}\b", r"(?:Law|Ley) 21\.545", r"\b\d+\.\d+\.\d+\b",
                    r"doi:\S+", r"https?://\S+", r"\b\d{4}-\d{2}-\d{2}\b", r"\S+\.(?:csv|json|py|png|pdf|md|docx)\b",
                    r"\b[a-z_]+:[a-z_]+(?::[A-Za-z0-9_-]+)+\b", r"\bSHA-256\b", r"\bv?\d+\.\d+\b(?= of the plan)"]
def journal_text(s: str, lang: str) -> str           # 7.5; identity for lang != "en"
def journal_text_blocks(blocks: list, lang: str) -> list   # applies journal_text and remap_refs (7.7) to every string of every block payload, after word counting
def format_p(p: float) -> str                        # "<0·0001" if p < 1e-4 else two significant figures with "·"
def tidy_value(file: str, filters: dict, column: str) -> float   # exactly one row must match, else raise
def asset_path(key: str, kind: str, lang: str, body: bool = False) -> Path  # tables/ vs extra/tables, figures/ vs extra/figures; body figures from PLATE_DIR
class JournalRegistry:                               # same surface as prose_en._Registry
    fig(key) -> "Figure Sn"; tab(key) -> "Table Sn"; figp(key, panels); mfig(key) -> "Figure n"; mtab(key) -> "Table n"; mfigp
    figure_block(key, label, body=False) -> ("figure", {...}); table_block(key, label, rows=None, columns=None) -> ("table", {...})
    nrows(key); first_citation_order() -> list; assert_monotone()   # raises if an item is first cited out of ascending order
```
`table_block` for a body table applies `TABLE_ROWS`/`TABLE_COLUMNS` as a presentation filter on the CSV read with `dtype=str, keep_default_na=False`; a test asserts every printed cell equals the CSV cell (before the number pass) and, for `T7_models`, that the p column equals `format_p(float(T7_models_numeric.p_value))` row by row. `S_reporting_checklist` is built by `supplement_journal.checklist_table()`.

### 7.2 Prose and supplement (builders A and S)
```
prose_journal_en.article(V: dict) -> list[tuple]     # docx_builder block grammar: title, subtitle(optional, unused), authors, h1/h2/h3, p, panel, table, figure, refs
prose_journal_es.article(V: dict) -> list[tuple]     # same structure, Spanish; identical keys per paragraph; Spanish number conventions (no number pass)
supplement_journal.blocks(lang: str, V: dict) -> list[tuple]   # lang must be "en"; "es" raises NotImplementedError("bilingual corpus supplement exists")
supplement_journal.checklist_table() -> pd.DataFrame            # columns Item, Recommendation, Where reported, Status (English)
supplement_journal.analysis_plan_blocks() -> list[tuple]        # English rendering of analysis_plan.md v1.0 (2026-09-04)
```
Block payloads follow `docx_builder.build_document` exactly: `("p", text)` with `[@key]` markers and `**bold**` only for the Summary labels; `("panel", {title, items:[(heading, text)]})`; `("table", {df, title, note, label, font_pt})`; `("figure", {path, caption, label, embed_dpi})`; `("eq", (paths, number))` (only in the supplement, produced by `methods_blocks`); `("refs", None)`. The article's block order: title, authors, h1 Summary + 5 p, panel, Introduction … Conclusion, the six declaration h1 sections, ("refs", None), then Table 1, Table 2, then Figures 1–4 (each figure block is preceded by nothing: the legend carries the heading). The article text cites the tables and figures in Results as today (`R.mtab`, `R.mfig`, `R.mfigp`). Every number in prose is produced by `prose_en` helpers (`n0`, `n1`, `n2`, `pct`, `ppct`, `ci`, `nw`, `millions`, `_V.apc/rate/series/svy/est_ci_y`) from the named keys; derived numbers only through the two documented derivations (Census effect from `ine_ratio_censo2024_base2017_2024`; ENDIDE M:F from the two sex keys). `prose_journal_es` mirrors `prose_es.py` for wording.

### 7.3 `build_journal.py` (builder B)
```
python3 journal/build_journal.py [--lang en|es|all] [--skip-pdf] [--render-plates] [--no-strict]
```
- `--render-plates`: runs `pipeline/08d_figure_dataflow.py`, `08a_figures_grd.py`, `08b_figures_rem.py`, `08c_figures_triangulation.py` (08c with `--variants sin_rett`) as subprocesses with `PLATE_JOURNAL=1` and `PLATE_CHECK=strict`; before and after, hashes every file under `outputs/sin_rett/*/figures`, `outputs/sin_rett/*/extra`, `outputs/sin_rett/*/tables`, `outputs/values_*.json`, `outputs/tidy` and aborts if any corpus file changed; asserts the four body PNGs exist in `PLATE_DIR[lang]` at 4251 × 5787 px; writes the strict-check records to `outputs/controls/journal/plate_check_journal.json`.
- Builds, per language: `art = journal_config.journal_text_blocks(prose_journal_<lang>.article(V), lang)` after measuring `prose_en.word_counts` on the un-passed blocks (fails the build if any budget of `WORD_BUDGET` is exceeded or the Summary > 250 or references ≠ 30), then `docx_builder.build_document(blocks, lang, OUT_DIR / f"article_sin_rett_{lang}.docx", bib_path=prose_en.BIB, journal=JOURNAL_DOC_FLAGS)` inside `m10.localised_references(lang)` further patched for the journal author rule; then `m10.postprocess_docx` (landscape tables, page numbers), then `m10.to_pdf` unless `--skip-pdf`; thumbnails under `OUT_DIR / "review"`.
- Supplement (en only): two-pass build (7.6); `supplement_journal.blocks("en", V)`; PDF; `pdfinfo` page count; TOC verification.
- Writes `OUT_DIR / "build_report_journal.json"` (word counts, citation keys, S-number maps, plate records, page audits, checks of section 8) and never touches `manuscript/build_report.json`.
- Outputs: `manuscript/04_submission_study/article_sin_rett_en.docx|pdf`, `supplement_sin_rett_en.docx|pdf`, `article_sin_rett_es.docx|pdf`, `analysis_plan_v1.0_es.md`, `build_report_journal.json`, `review/`. Tests that glob `manuscript/*.docx|*.pdf` are non-recursive, so `manuscript/04_submission_study/` is invisible to them.
- Journal reference rule: `format_vancouver` patched so that an entry with more than six authors prints the first three then ", et al"; hyphens in `pages` become en rules.

### 7.4 Shared plate flag (builder P; `common.py` only)
- `PLATE_JOURNAL` (default unset = today's behaviour). `common.plate_journal_mode() -> bool`.
- `common.journal_redirect(path) -> Path`: when on, maps `outputs/<v>/<lang>/figures/…` and `outputs/<v>/<lang>/extra/figures/…` to `outputs/<v>/<lang>/journal/figures/…`, and `outputs/controls/<module>_runlog.json` to `outputs/controls/journal/<module>_runlog.json`; applied inside `save_fig`, `merge_json`, `atomic_write_json` and `plate_check_write`. Corpus folders are never written in journal mode (the registry test scans `figures/` and `extra/figures/` only, so `journal/figures/` is invisible to it; `LEGACY_UNREGISTERED_PLATES` is untouched).
- In `plate_resolve`, before `_pl_title_fit`: every axes title matching `^\([a-f]\)\s+.+` becomes the bare letter "(a)"; `fig._suptitle` (if any) is emptied; figure-level texts equal to the variant labels (08a `variant_*`/`variant_short_*` strings and 08d's FS_VARIANT stamp) are removed; artwork text tokens "100,000" → "100 000" and `(?<=\d)\.(?=\d)` → "·" in tick labels, annotations and legends for lang "en" only (protected tokens as in 7.1). Legend frames are already off; no outer box is drawn. `check_layout` runs on the modified figure (strict) — the title-gutter and headroom checks now see the bare letters.
- Figure 1 keeps `plate_declare(grid=None)`; its lane headings are not axes titles and are not stripped.

### 7.5 Shared document flag (builder P; `docx_builder.py` only)
`build_document(..., journal: dict | None = None)`; `journal=None` keeps today's behaviour. `JOURNAL_DOC_FLAGS = dict(table_pt=8, table_heading_pt=10, table_internal_heading_pt=8, legend_pt=10, legend_heading_bold=True, heading_pt=10, main_heading_pt=12, body_pt=12, superscript_citations=True, one_figure_per_page=True, page_numbers=True, toc=False)` for the article and the same with `toc=True, body_pt=10` for the supplement. Effects: (a) tables: heading 10 pt bold, body 8 pt single-spaced, rows whose first cell is a Block/Estimand heading printed 8 pt bold across the row; (b) figures: heading (label + title) 10 pt bold as the first run of the legend paragraph, legend 10 pt single-spaced, each plate in its own section/page, legend spill continues on the next page with the "(continued)" label (existing machinery); (c) citations: `Citations.resolve` in journal mode returns a marker `⁣{n[,n]}` that `_add_text` renders as a superscript run placed AFTER the punctuation that immediately follows the marker (regex `\s*\[(@[^\]]+)\]([,.;:]?)` → `\2` + superscript); ranges "1–3" with an en rule; (d) headings: h1 12 pt bold (supplement main heading) / 10 pt bold (sections), h2/h3 10 pt bold; (e) no bold runs in body paragraphs except the Summary labels; (f) references list 10 pt.
`journal_config.journal_text(s, "en")` is applied by build_journal to every string that reaches the document (paragraphs, panel items, captions, table titles, notes, table cells) AFTER counting words: protected tokens masked; `(?<=\d)\.(?=\d)` → "·"; `(?<=\d),(?=\d{3}\b)` removed when the number has four digits and replaced by U+202F (narrow no-break space) when it has five or more; "p < 0.001" strings never survive (Table 2 uses `format_p`); mask restored. For "es" the corpus conventions stay (the Spanish file is the working translation, not the submission).

### 7.6 Supplement table of contents and page numbers
Two-pass build: pass 1 writes the supplement with a TOC whose page column is a fixed-width placeholder ("—"), converts to PDF, reads `pdftotext -layout` page by page to locate "Part A", each "M1."–"M7." heading, "Table S1." … "Table S85.", "Figure S1." … "Figure S36." and "Appendix references"; pass 2 writes the same document with the page numbers filled (same line count, so pagination is unchanged), converts again and verifies every TOC entry against the page where its heading actually starts (fails otherwise). Page numbers come from `m10.add_page_numbers` (every section). Main heading 12 pt bold, headings 10 pt bold, text 10 pt Times New Roman.

### 7.7 Cross-reference remap
`captions.json` and `titles.json` texts carry corpus S-numbers ("Table S27", "Figure S9", "Table 6"). `journal_config.remap_refs(text, lang) -> str` rewrites every "Figure Sn"/"Table Sn"/"Figure n"/"Table n" token from the corpus registry (`supplementary_material.FIGURE_ORDER/TABLE_ORDER`, `prose_en.MAIN_FIGURES/MAIN_TABLES`) to the journal numbering; a token whose target is a dropped item is replaced by "the deposited data" and logged; a test asserts no corpus-numbered token survives in either document.

---

## 8. Verification criteria (each reader applies them on the rendered files, never on a report)

R1 **Numbers**: every number token in `article_sin_rett_en.pdf` text (Summary to Conclusion, legends, table cells) is matched to a key of `values_sin_rett.json`, a tidy row named in section 3, a caption/title string of the corpus, or one of the two documented derivations; the reader recomputes 20 numbers at random from the keys and the two derivations by hand. Spanish article: identical numbers paragraph by paragraph (same keys in the same order, extracted by AST from both prose modules).
R2 **Journal format on the PDF**: `pdffonts` shows only Times New Roman faces; no "(1,2)"-style citation survives (regex `\(\d+(?:[,–-]\d+)*\)` after a word) and every citation is superscript after punctuation (read three pages); no decimal with a full stop outside protected tokens in the English article and supplement; five-digit numbers carry the narrow space; p values two significant figures or "<0·0001"; numbers one to ten in words except with units; no bold except headings and Summary labels; means with SD / medians with IQR where printed.
R3 **Summary and lengths**: five paragraphs, ≤ 250 words; core body 3500–4800; Research in context present with sources, terms and the exact search date and no citation; each body legend ≤ 300 words (Figure 1 ≤ 160); 30 references numbered in order of first citation, ≤ 6 authors listed / 7+ first three + et al, en rules in page ranges.
R4 **Display items**: article PDF ends with Table 1, Table 2, then Figures 1–4 one per page, each with its 10 pt bold heading at the start of the legend; each plate 180 mm wide at 600 dpi (`pdfimages -list` or the docx embed report), lowercase panel letters, no in-graph titles (open the PNG at reduced size), no variant stamp, no box; Table 1 has 25 rows, Table 2 has 29 rows, n beside every %, 8 pt body; cells equal the CSV (spot-check ten cells against `T2_grd_core.csv`/`T7_models.csv`).
R5 **Supplement**: one PDF, page numbers on every page, TOC entries agree with the pages (check ten); Part A carries M1–M7 with equations 1–33 each printed once in numeric order and the estimator map (Table S5); Tables S1–S11 and the analysis plan (dated 4 September 2026) present; Part B in the order of section 4 with S-numbers ascending by first citation from the article (the reader checks the first ten citations in the article text); appendix references separately numbered; the con_rett statement in the front matter.
R6 **Standing rules**: grep both PDFs for "prevalence of autism" as a claim about these counts, "hospitalisations for autism", "hospitalizations for", "cascade", "conversion", "effect of Law", "caused by", "attributable to the law", "trough in 2020" (allowed only for hospital counts), "quantifies the contribution of reporting" — none may occur; every REM count in the body carries its reporting establishments; the DEIS/GRD sentence carries "coverage comparison … not a probability"; Figure 2d and Figure 4e legends carry the place-of-care warning; Figure 4d says "indices".
R7 **Corpus integrity**: `python3 -m pytest study/tests -q` → 299 passed, 1 skipped (baseline); SHA-256 of every file under `outputs/sin_rett/*/figures`, `extra`, `tables`, `outputs/values_*.json`, `outputs/tidy` unchanged after the journal build; `manuscript/*.docx|pdf` untouched; journal plates exist only under `outputs/sin_rett/<lang>/journal/figures/`.
R8 **Author-supplied placeholders** are visible and bracketed, never invented: affiliation, second author who accessed and verified the data, ethics confirmation, repository URL/DOI, AI-tool versions, ICMJE forms, funding "None".

---

## 9. Build-risk register (from B and C, resolved here)
- Legend overflow under a 245 mm plate on A4: ≈ 8 lines of 10 pt fit (≈ 140 words); longer legends continue on the next page labelled "(continued)" through the existing spill machinery; verified by R4 on the PDF, not on the report.
- Artwork decimals and thousands: handled in journal plate mode (7.4) for "en"; verified by reading the four PNGs.
- PDF conversion resamples plates: keep `embed_dpi=600` for body plates; check `pdfimages -list`.
- Word counts inflate with the narrow space: counts are measured before `journal_text`.
- `T7_models` has no `model_id` column: selection goes through `T7_models_numeric.csv` (row-aligned; asserted by row count and by APC string equality after formatting).
- REM 2025 may be incomplete (952 establishments vs 1070): stated in Results and Limitations as today.
- The corpus `Citations` renders "(1,2)": journal superscripts are a docx_builder flag (7.5); a test asserts none survives.
- `figS4_grd_model_sensitivities.png` and `figS7_a05_standardised_rates.png` (legacy, unregistered) are never read: `asset_path` accepts only keys of `SUPP_FIGURES`/`BODY_FIGURES`.
