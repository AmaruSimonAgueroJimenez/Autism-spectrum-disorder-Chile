# Reference cut — the 50 keys the full `sin_rett` article cites, and what the journal submission does with each

Source of the 50: every `[@key]` marker of `prose_en.article("sin_rett", V)` in block order, including the
`[OPT]` paragraphs and the "Official sources" sentence (28 keys in the un-tagged text, 7 in the three `[OPT]`
paragraphs, 15 dataset keys in the "Official sources" sentence). Journal list: `journal_config.REFERENCE_KEYS`
(30, in order of first citation; asserted by `tests/test_journal_prose.py` against
`prose_en.citation_keys(prose_journal_en.article(V))`). Reasons for the drops: `journal_config.DROPPED_REFERENCE_KEYS`
(plan.md, section 6). The journal allows a maximum of 30 references (`journal_guidelines.md`, "Extensión").

Measured on `manuscript/04_submission_lancet_americas/article_sin_rett_en.pdf` (build of 2026-09-09, after the second reading round): 30
numbered entries, numbered 1–30 in order of first citation, superscript numbers after the punctuation, ≤ 6 authors
listed in full, ≥ 7 authors as the first three and "et al" (10 entries: fyfe2026 has 12 authors). Round 2: the
readers' one formatting failure (ref 27, Iezzoni 1992, whose title ends in "?") is fixed at its source — the journal
form regex of `journal_reference_style` now accepts a title closed by ".", "?" or "!" — and the readers'
recommendation to give the slot of `heidari2016` to `fyfe2026` is adopted: the SAGER sentence of Methods stands
without a citation ("following the SAGER guidelines") and fyfe2026 (BMJ 2026, time trends in the male:female
ratio of autism incidence in a population-based birth cohort) is cited in Discussion ¶3 beside loomes2017 as the
comparator of the falling ratio that the Summary, Results and Discussion headline. `supersalud_isapre` is not
restored (no 31st slot; it stays in the appendix list where Tables S25 and S28 use it). Reference form of the journal (journal mode of
`pipeline/10_manuscript.py`, `journal_reference_style`, default behaviour untouched): journal names abbreviated as in
Index Medicus (`JOURNAL_ABBREVIATIONS`, 24 names; every journal met in the article and the appendix list is covered,
`JOURNAL_UNABBREVIATED` empty), journal articles printed in the journal's own example form «Lancet 1998; 351:
1687–92» (no issue number, en rule, end page shortened to the digits that differ), and every online source (the 11
official portals and the law, refs 10 and 14–23, plus ref 24) with the access date read from the .bib `urldate`
(«accessed Sept 4, 2026»). Two keys are cited twice in the article (zeidan2022 in Introduction ¶1 and ¶2; the five
repeated context keys of the Discussion), which changes no number.

| # corpus | Key | Journal | Journal # | Where cited in the journal article | Reason |
|---|---|---|---|---|---|
| 1 | zeidan2022 | kept | 1 | Introduction ¶1; Introduction ¶2 ("population-based prevalence estimates exist for few countries", the claim that paula2011/fombonne2016 supported) | global prevalence estimate ("about 1%") and the scarcity of Latin American population estimates rest on this review |
| 2 | santomauro2025 | dropped | — | — | the "about 1%" sentence rests on zeidan2022 alone |
| 3 | russell2022 | kept | 2 | Introduction ¶1; Discussion ¶4 | UK time trends in recorded diagnoses |
| 4 | hansen2015 | kept | 3 | Introduction ¶1; Discussion ¶4 | Danish register: reporting practices explain most of the rise |
| 5 | lundstrom2015 | kept | 4 | Introduction ¶1; Discussion ¶4 | Swedish register vs phenotype |
| 6 | shaw2025 | kept | 5 | Introduction ¶1; Discussion ¶4 | ADDM 2022 surveillance |
| 7 | lord2022 | kept | 6 | Introduction ¶1 | Lancet Commission |
| 8 | paula2011 | dropped | — | — | the Brazil/Mexico prevalence sentence is deleted; the "few countries" claim now cites zeidan2022 (ref 1) |
| 9 | fombonne2016 | dropped | — | — | same sentence as paula2011; the "few countries" claim now cites zeidan2022 (ref 1) |
| 10 | montielnava2024 | kept | 7 | Introduction ¶2; Discussion ¶5 | Latin American caregiver survey: diagnostic delay and barriers |
| 11 | becerril2011 | dropped | — | — | segmentation of the Chilean system is stated from the study's own coverage data (`share_fonasa_ine_pct_2025`, `share_isapre_ine_pct_2025`) |
| 12 | yanez2021 | kept | 8 | Introduction ¶2 | the one urban prevalence estimate for Chile |
| 13 | romanurrestarazu2025 | kept | 9 | Introduction ¶2 | the one school-register estimate for Chile |
| 14 | minsal2011 | dropped | — | — | the early-detection guideline clause was deleted from Introduction ¶2 after round 1 (an uncited factual claim is not left in the text) |
| 15 | ley21545 | kept | 10 | Introduction ¶2 (context only) | the law itself |
| 16 | irarrazaval2023 | dropped | — | — | ley21545 suffices for the law's content |
| 17 | vonelm2007 | kept | 11 | Methods › Study design | STROBE |
| 18 | benchimol2015 | kept | 12 | Methods › Study design | RECORD |
| 19 | heidari2016 | dropped (round 2) | — | — | the SAGER statement of Methods stands without a citation; its slot goes to fyfe2026, the comparator of the headline finding (readers' recommendation) |
| 20 | cid2024 | dropped | — | — | the "GRD used since 2020 as a payment mechanism" clause is deleted |
| 21 | fonasa_grd | kept | 13 | Methods › Official sources | GRD files (primary source) |
| 22 | deis_egresos | kept | 14 | Methods › Official sources | DEIS discharges |
| 23 | minsal_rem | kept | 15 | Methods › Official sources | REM |
| 24 | deis_rem20 | dropped | — | appendix references (Figure S24, Table S61) | sensitivity layer (REM-20 capacity), cited where used, in the appendix |
| 25 | ine2019 | kept | 16 | Methods › Official sources | INE projections, base 2017 (primary denominator) |
| 26 | ine_base2024 | dropped | — | appendix references (Figure S3, Table S26) | sensitivity denominator, cited in the appendix |
| 27 | ine_censo2024 | dropped | — | appendix references (Figure S3, Table S26) | sensitivity denominator, cited in the appendix |
| 28 | fonasa_beneficiarios | kept | 17 | Methods › Official sources | FONASA beneficiaries (coverage) |
| 29 | fonasa_aps | dropped | — | appendix references (Tables S25, S29) | APS enrolment layer, cited in the appendix |
| 30 | supersalud_isapre | dropped | — | appendix references (Tables S25, S28) | ISAPRE layer, cited in the appendix |
| 31 | endide2022 | kept | 18 | Methods › Official sources | ENDIDE 2022 (population benchmark) |
| 32 | encavi2023 | kept | 19 | Methods › Official sources | ENCAVI 2023–24 (population benchmark) |
| 33 | mineduc_apuntes60 | kept | 20 | Methods › Official sources | PIE registers (Apuntes 60) |
| 34 | mineduc_sinaces2026 | kept | 21 | Methods › Official sources | PIE registers (SINACES) |
| 35 | junaeb_eve | kept | 22 | Methods › Official sources | JUNAEB survey |
| 36 | ahmad2001 | kept | 23 | Methods › Statistical analysis ¶1 | WHO world standard population |
| 37 | fay1997 | kept | 24 | Methods › Statistical analysis ¶1 | Fay–Feuer limits of the standardised rates of Table 1 |
| 38 | wedderburn1974 | kept | 25 | Methods › Statistical analysis ¶1 | quasi-likelihood |
| 39 | wolter2007 | dropped | — | appendix references (Part A, M4, estimator 23) | Taylor linearisation is cited where the equation is printed |
| 40 | iezzoni1992 | kept | 26 | Discussion ¶2 | coding depth and comorbidity documentation |
| 41 | song2010 | kept | 27 | Discussion ¶2 | regional variation in diagnostic practice |
| 42 | loomes2017 | kept | 28 | Discussion ¶3 | male-to-female ratio meta-analysis |
| 43 | fyfe2026 | kept (round 2) | 29 | Discussion ¶3 | population-based birth cohort documenting the falling male:female ratio of autism incidence — the comparator of the headline sex-ratio finding; takes the slot of heidari2016 |
| 44 | lai2020 | dropped | — | — | dropped with the optional sex-ratio paragraph |
| 45 | hull2020 | dropped | — | — | dropped with the optional sex-ratio paragraph |
| 46 | garcia2022 | kept | 30 | Discussion ¶5 | Chilean caregiver survey |
| 47 | romanurrestarazu2018 | dropped | — | — | dropped with the optional Chilean-context paragraph (L1031) |
| 48 | cid2016 | dropped | — | — | dropped with the optional Chilean-context paragraph |
| 49 | breinbauer2022 | dropped | — | — | dropped with the optional Chilean-context paragraph |
| 50 | acevedo2025 | dropped | — | — | dropped with the optional Chilean-context paragraph |

Totals: 30 kept, 20 dropped. Of the 20 dropped, 6 (deis_rem20, ine_base2024, ine_censo2024, fonasa_aps,
supersalud_isapre, wolter2007) are cited in the supplementary appendix's separately numbered reference list (39
entries: the 39 keys `prose_methods_extended.methods_blocks` cites), so no source used by the study is left
uncited in the submission; 13 supported sentences that the journal version deletes, and heidari2016 supported a
statement (SAGER) that the article keeps without a citation. All 50 keys remain in
`references_lancet.bib` (122 verified entries) and in the full bilingual corpus.
