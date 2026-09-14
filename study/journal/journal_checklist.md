# Journal checklist — *the target journal*, measured on the built files (build of 2026-09-09T20:38, after the second reading round)

One row per rule of `journal_guidelines.md` (the archived "Information for Authors", August 2026; the official text in
`journal_guidelines/tlam-info-for-authors-1759484803240.txt`). Every value below was MEASURED on the rendered
deliverables in `manuscript/04_submission_study/` — `article_sin_rett_en.pdf` (31 pages, A4), `supplement_sin_rett_en.pdf`
(491 pages, A4), `article_sin_rett_es.pdf` (35 pages) and their DOCX — with `pdftotext -layout`, `pdffonts`,
`pdfimages -list`, the DOCX XML (run sizes, superscripts, line spacing, row properties, footers) and
`build_report_journal.json` (word counts with `prose_en.word_counts` on the blocks BEFORE the number pass, the count the
plan defines). Scripts: `scratchpad/gather.py`, `measure_r2.py` and `write_checklist_r2.py` of the CLOSE ROUND 2
session; the pages named below were also read as images. "Residual" names what is not met, what is author-supplied,
or what a standing rule keeps. The readers' second-round items and what was done with each are in `decisions.md`
(CLOSE ROUND 2).

## A. Article (original research)

| Rule (journal_guidelines.md) | Where satisfied | Measured value | Status |
|---|---|---|---|
| Length 3500–5000 words of manuscript text | `article_sin_rett_en.pdf` Introduction → Conclusion | 4977 words (`word_counts.core_body`; Introduction 388, Methods 1534, Results 1908, Discussion 1069, Conclusion 78); every budget of `journal_config.WORD_BUDGET` met (`budgets_ok` = True; ceiling 4980) after the numerators beside every percentage (+118 words) were paid for by compressing six Results passages | met |
| Maximum 30 references | reference list | 30 entries in order of first citation (`citation_keys` == `REFERENCE_KEYS`); heidari2016 → fyfe2026 (readers' recommendation; `reference_cut.md`) | met |
| Vancouver, numbered by order of mention, superscript after punctuation | body text | 34 superscript runs in the DOCX; 0 "(1,2)"-style citations on the PDF text | met |
| Journal names abbreviated as in Index Medicus; journal form «Lancet 1998; 351: 1687–92» | reference list | 14 entries in the journal's form; reference 26 (Iezzoni 1992, title ending in «?») now prints «JAMA 1992; 267: 2197–203.» (regex of `journal_reference_style` accepts «.», «?» or «!» before the journal name); page ranges of the list tied at the dash (0 broken ranges: `measure_r2.broken_numbers` = []) | met |
| Online material cited with the URL and the date accessed | refs 10, 13–22, 23 | 11 entries end «Available from: <URL> (accessed Sept 4, 2026).» | met |
| ≤ 6 authors all listed; ≥ 7 authors first three + "et al" | reference list | 10 entries with ≥ 7 authors print three names + «et al» (fyfe2026 has 12), the rest all authors (`journal_author_list`) | met |
| Summary: five paragraphs (Background, Methods, Findings, Interpretation, Funding), ≤ 250 words | p 1 | five labelled paragraphs; 241 words before the number pass (the Law 21.545 sentence, repeated in Methods and Interpretation, was removed); on the PDF text 249 words with the labels whether a thin-spaced thousand counts as one word or two; no reference; «95·5% (8341 episodes)» carries its n | met |
| Research in context (sources, terms, exact dates, the quality/risk of bias of the evidence; Added value; Implications), no references | pp 2–3 | three headings; «PubMed and Crossref on Sept 4, 2026» with the term list and portals; quality of the evidence present; 479 words; 0 citation markers | met |
| STROBE (observational study), submitted with the protocol | Methods › Study design; appendix A8 (Table S11) and A9 (analysis plan v1.0, 4 September 2026) | present; TOC verified | met |
| Title page: brief title, names, preferred degree (one), affiliations with full addresses, corresponding author's name, address, email and telephone | p 1 | title, name + «[preferred degree …]», affiliation + «[full postal address …]», «Corresponding author: … [postal address …]; email; telephone [to be completed by the author]»; running title; no build stamp (False) and no word counts (False) on the submission page | met in structure; degree, addresses and telephone author-supplied |
| Contributors: individual contributions; more than one author accessed and verified the data; all authors full access | Contributors | present; «[Second author, to be named before submission] independently accessed … re-ran the pipeline, and verified …» | met in structure; second author author-supplied (never invented) |
| Declaration of interests; funding and the role of the funding source; data sharing statement never "undecided"; separate AI declaration at the end | Declarations | all present; «undecided» absent; 7 bracketed author-supplied placeholders on the PDF (ethics confirmation, ICMJE forms, repository URL/DOI, Codex version, second author, degree/addresses/telephone) | met; placeholders author-supplied |
| Sex and gender per SAGER; limitations discussed | Methods › Study design («following the SAGER guidelines», no citation); Discussion › limitations | statement present | met |
| Disability: no disability inferred from a diagnosis | Methods › Data sources ¶3 | sentence present | met |
| Data: numbers always provided if % is shown | Introduction, Results | every percentage of the Introduction and the Results prints its numerator and base beside it from a named key or tidy row (FONASA/ISAPRE as millions, Census 18 480 432 of 20 086 377, GRD age bands 4167 and 1004 of 8728 with a known age, A05 6143 of 13 155, NANEAS 13 190 of 59 907 and 29 974 of 100 789, June cut 172 against 1919, physician-confirmed 139 of 153, PIE 47 551 of 473 006 and 11 877 of 385 995, the seven JUNAEB proportions as unweighted cases/respondents, the top-decile shares with their base of 2332 and 8731 episodes with a comuna of residence); the Discussion recaps print the percentages already given with their n in Results | met (the top-decile numerator is not a tidy value and is not hand-derived: standing rule) |
| Means with SD, medians with IQR; p values two significant figures or «<0·0001» | Results | no bare median or mean in the text: the coding-depth sentence points to the mean-depth inset of Figure 2c («means only; no dispersion is drawn»: the pipeline computes no SD or IQR for coding depth); hospital rates «median 638·0, IQR 393·3–976·1»; Table 2 p column «<0·0001» / «0·016»; Moran «p = 0·0010» | met |
| Figures ≥ 300 dpi and ≥ 107 mm wide; one figure per page; lowercase panel letters; no titles in the graph; no box | pp 25–30 (each figure opens its own page; Figures 2–4 continue their legend on the following page, labelled «(continued)») | `pdfimages -list`: 4 plate images at [180] mm and 600 ppi (p 25 4251×5787 px; p 26 4251×5787 px; p 28 4251×5787 px; p 30 4251×5787 px); the plates never shrink (`plate_min_w_cm` = 18), so the smallest artwork text prints at 6.0 pt (`common.PLATE_FS_FLOOR` at 1:1); the Figure 2c inset title «Mean depth» removed in journal mode (`common.JOURNAL_TITLES_TO_LEGEND`); no variant stamp, no box | met |
| Figure title 10 pt bold at the start of the legend; legends 10 pt single spaced | legends | 7 legend paragraphs (4 heads + 3 «(continued)» tails), run sizes [10.0], line spacing 240; legend words {'Figure 1': 152, 'Figure 2': 293, 'Figure 3': 292, 'Figure 4': 296} (Figure 1 ≤ 160, others ≤ 300) | met |
| Tables: heading 10 pt bold; body 8 pt single spaced; internal headings 8 pt bold; legends (notes) 10 pt; n beside %; no row split across pages | Tables 1–2 (landscape, pp 20–24) | tables by minimum run size {'8.0': 2, '10.5': 1} (the 10·5 pt table is the Research in context panel); notes [10.0] pt; every row `w:cantSplit` (74 of 74 rows) so no row is split across pages; internal heading rows bold, merged and kept with their first row | met |
| Text: mid-height decimal point; thousands «100 000»; numbers one to ten in words; no bold for emphasis; serial comma; "eg," without stops | whole article | 558 mid-height points; 0 ASCII decimals outside protected tokens; 50 «100 000» with a narrow no-break space and 0 with a plain space; 0 «e.g.»/«i.e.»; 0 lines opening with a range dash | met |
| Fonts | `pdffonts` | ['TimesNewRomanPS-BoldItalicMT', 'TimesNewRomanPS-BoldMT', 'TimesNewRomanPS-ItalicMT', 'TimesNewRomanPSMT'] | met |
| Near-empty pages | whole PDF | p 27 (659 characters): the labelled tail of the Figure 2 legend (one figure per page: a tail page cannot carry the next figure) | residual by construction (180 mm plates) |

## B. Supplementary material

| Rule | Where satisfied | Measured value | Status |
|---|---|---|---|
| One PDF, in English, with a table of contents and numbered pages | `supplement_sin_rett_en.pdf` | one file, 491 pages (569 in round 1); «Contents» with 151 entries verified entry by entry on the PDF (`toc.verified` = True, 2 passes); folio on 491 of 491 pages | met |
| Text 10 pt Times New Roman single spaced; main heading 12 pt bold; headings 10 pt bold | DOCX | line spacing values {'240': 55530, '20': 32, '288': 1, '276': 1} (240 = single; the 139 paragraphs at 1·15 of round 1 — front matter, analysis plan, presentation paragraphs, appendix references — are now single spaced through `aux_line_spacing`; the one 276 is the subtitle's italic line); fonts ['TimesNewRomanPS-BoldItalicMT', 'TimesNewRomanPS-BoldMT', 'TimesNewRomanPS-ItalicMT', 'TimesNewRomanPSMT'] | met |
| Tables 10/8/8 pt, legends 10 pt; no words broken inside cells; no row split across pages | 111 table blocks of 91 tables | 111 table bodies at 8 pt and 0 below (the 33 at 10 pt are the equation rows and the panel); 18 tables printed in parts (Table S12, Table S15, Table S16, Table S19, Table S20, Table S21, Table S22, Table S27, Table S28, Table S37, Table S46, Table S47, Table S54, Table S65, Table S80, Table S85, Table S89, Table S91; 38 part labels) with the key columns repeated; internal heading rows and lettered footnotes in Tables S88–S89; spot check of the words the readers saw broken («Comu|na», «SH|A-256», «Denominato|r», «Durbin–Wat|son», «Superintendenci|a», «Discharg|es», «Questionnair|e»): 0 occurrences; notes at [10.0] pt; every row `w:cantSplit` (6611 rows) | met |
| Numbers never broken inside a cell; ranges never split at the dash | tables | the number-width guard measures the pieces LibreOffice cannot break (`docx_builder.set_journal_atoms`: «29 587/1 151 475», «(−20·1», tied «30·0–42·1» and «2019–2024»); Table S45 lethality row «29 587/1 151 475; 2·57 (2·54–2·60)» intact; Table S80 «−0·08» intact; Table S89 APC intervals intact; 0 lines opening with a range dash (40 in round 1); [] lone «<» lines; Table S82 p column from `E48_rank_stability_numeric.csv` (0 «< 0·001» cells left) | met |
| Applied methodology | Part A | M1–M7 verbatim, Tables S1–S10, the 33 equations once each in numeric order (in order; 33 «Eq. n» labels), A8 checklist (Table S11), A9 analysis plan, «A10. Appendix references» present | met |
| Results not in the body, precisely presented | Part B | Figures S1–S36 and Tables S12–S91 in first-citation order; each figure introduced by what it shows, why it matters and what it adds; each table by what it holds and what it adds; section B12 names the items not printed; un-remapped legacy tokens: «the deposited data» 0, «table Sn» 0, «plate EFn» 5 (in the B12 list of corpus titles) | met |
| Supplementary plates: journal renders, 300 dpi minimum, legend with its plate | Part B | 36 plates embedded at 300 ppi and 180 mm (smallest artwork text 6.0 pt at print size); every legend heading on its plate's page (0 off-plate heads; the presentation paragraph rides with the plate only when three legend lines still fit under it); 36 legends continue on the next page labelled «(continued)»; Figure S15 facet labels in regular weight; Figure S17 panel letters no longer overlap the «100» tick (invisible, not blank, titles keep the letter anchored) | met |
| p values | Tables S76, S77, S82, S88, S89 | rebuilt from the numeric companions through `format_p`: 0 «< 0·001» cells left | met |
| Con_rett statement | front matter | present, with the 87-episode difference | met |
| Near-empty pages | whole PDF | p 50 (606 characters), p 64 (639 characters), p 150 (535 characters), p 156 (591 characters), p 203 (417 characters), p 205 (261 characters), p 226 (345 characters), p 237 (523 characters), p 252 (311 characters), p 347 (449 characters), p 419 (407 characters), p 469 (492 characters) — section openings whose presentation paragraph no longer fits under a 180 mm plate (B2, B5, B8, B9, B10), legend tails before the next plate, one table note (S41) and two short table pages | residual by construction (180 mm plates; a note is kept together) |

## C. Spanish working translation (`article_sin_rett_es.pdf`)

35 pages; the same block sequence and the same numbers per paragraph (`tests/test_journal_prose.py::test_numeric_parity_en_es`); Spanish number conventions; the build stamp stays on its title page (True); 11 references with «consultado el 4 de septiembre de 2026»; 0 lines opening with a range dash; plates at [180] mm; near-empty pages: p 22 (228 characters) (the last reference alone at the end of the list).

## D. Standing rules of the study (R6 of the plan)

Re-checked on the new PDFs (`tests/test_journal_prose.py::test_standing_rules_and_house_style` and a grep of both PDFs): no «prevalence of autism» as a claim about these counts, no «hospitalisations for autism», «cascade», «conversion», «effect of Law», «caused by», «attributable to the law», «trough in 2020» or «quantifies the contribution of reporting»; every REM count with its reporting establishments; the DEIS/GRD sentence with «coverage comparison … not a probability»; Figures 2d and 4e with the place-of-care warning; Figure 4d «indices»; the two new derivations (age-band numerators) are sums of named tidy cells asserted against the share keys at build time; the top-decile numerator is not derived by hand.

## E. Corpus integrity and tests

| Check | Value |
|---|---|
| `python -m pytest study/tests -q` | 330 passed, 4 skipped, 99 warnings, 121 subtests passed in 367.59s (0:06:07) / EXIT 0 |
| SHA-256 of `outputs/sin_rett/*/{figures,extra,tables}`, `outputs/values_*.json`, `outputs/tidy` before/after the build | unchanged (`corpus_unchanged` = True); the journal re-renders of 08a–08d (`--render-plates`), 13 and 14 audited the same way: 0 corpus files changed |
| `manuscript/*.docx|pdf` | untouched (timestamps of Sept 8) |
| Journal plates | only under `outputs/sin_rett/<lang>/journal/figures/`; `outputs/controls/journal/plate_check_journal.json` written by `--render-plates` (False) |

## F. Residuals for the author team and the readers

1. Author-supplied placeholders, bracketed and never invented: preferred degree, postal addresses, telephone, second author who accessed and verified the data, ethics confirmation, ICMJE forms, repository URL/DOI, Codex version, funding «None».
2. Pages that a 180 mm plate leaves partly blank: the labelled legend tails of Figures 2–4 in the article and, in the appendix, the pages before a plate that carry a section opening or a legend tail (listed above); the alternative — shrinking the plate — prints its 6 pt text below 6 pt, which the readers marked blocking.
3. Table notes are kept together, so one long note (Table S41) opens a page on its own; splitting notes across pages was the round-1 defect.
4. Plate-level items left as they are: the Figure 3f note over a data line (no backing); the bold era headings of Figure 3a–b and the group/strip headings of Figure 4c/e (row-group labels of dot plots, kept as the plan decided); the ~20 mm band between the rows of Figure 3 that holds its shared year legend; the three row labels of Figure S36d truncated with an ellipsis and the Figure S16f annotation touching the dashed data line (both need per-plate edits in modules 15 and 08b; not done: cost and risk of re-laying out two corpus plates for a cosmetic gain).
5. The original papers of Getis–Ord, Durbin–Watson, Theil/Gini and M-CHAT-R/F are not added to the appendix list.


## Medición del 2026-09-09 (compilación 22:08)

| medida | artículo EN | artículo ES | apéndice EN |
|---|---|---|---|
| páginas | 31 | 35 | 504 |
| rayas de rango que abren renglón | 0 | 0 | 0 |
| nombres compuestos partidos | 0 | 0 | 0 |
| resumen (palabras) | 239 | 287 | — |
| texto del manuscrito (Introducción→Conclusión) | 4 977 | 5 812 | — |
| porcentajes del resumen sin n | 0 | 0 | — |

Batería completa: 330 pruebas, 4 saltadas, 121 sub-pruebas, 0 fallos.
