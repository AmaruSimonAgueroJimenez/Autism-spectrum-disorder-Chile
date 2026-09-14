# docs/lancet: public replica of the manuscript for The Lancet Regional Health – Americas

This folder contains everything needed to reproduce, from the repository and without the microdata, the content
of **version 10** of the manuscript (14 September 2026) and to show the corpus of results of the earlier
versions. The site pages that use it are `docs/lancet.qmd` (article), `docs/lancet_supplement.qmd`
(supplementary material) and `docs/lancet_corpus.qmd` (extended corpus); their HTML files sit next to the QMD.

The complete versions of the manuscript (DOCX, PDF, 600 dpi plates, revision data) live in
`lancet_americas/manuscript/` and, together with `lancet_americas/outputs/`, stay out of git (`.gitignore`).
The pipeline code (`lancet_americas/*.py`, `pipeline/`, `journal/`) is versioned.

## Contents

| Path | What it is | Origin |
|---|---|---|
| `data/*.csv` | Public tables read by the figure scripts: 10 tidy tables (`lancet_americas/outputs/tidy`) and 23 verified tables of revision 10 (`technical/data`) | unmodified copies |
| `data/communes_public.csv` | Commune comparison 2021–2024 (GRD, A05 and P2 rates per 100 000; Metropolitan Region flag). No identifiers or denominators; cells with 1 to 4 records are masked variable by variable, so that `dropna()` leaves exactly the communes shown in figure 4d and figure S7 (153, 216 and 133) | derived from `S4_common_window_analytic_communes_PRIVATE.csv`, which is not published |
| `data/S7d_threshold_sensitivity.csv` | Sensitivity of the Spearman ρ GRD–A05 to the minimum count k (figure S7d), computed on the complete commune file | precomputed |
| `data/contenido_v10.json` | Resolved text (numbered citations), tables, legends, equations and references of the four documents (manuscript and supplement, en and es) | `export_docs_content.py` (revision 10), which runs the real builder with its writing methods intercepted |
| `data/facts_v10.json` | Verified figures that resolve the placeholders of the text | copy |
| `figstyle.py`, `overlap_qa.py`, `figuras_principales.py`, `figuras_suplementarias.py` | Generators of plates 1–4 and S2–S9 (en and es), with the automatic overlap checker; adapted copies of `technical/sources/` of revision 10 (only the paths and the commune source change) | revision 10 |
| `figures/<language>/Figure_*.{png,svg,pdf}` | 175 mm plates (PNG at 300 dpi; vector SVG and PDF). S1 and S6 are plates inherited from revision 09 (no SVG) | generated here |
| `qa/` | 150 dpi previews (the ones embedded in the HTML pages) and `figuras_*_qa.json` records (size, fonts, off-canvas text and overlaps, which must be zero) | generated here |
| `equations/<language>/` | The 23 equations of the extended methods, composed with STIX at 600 dpi by `lancet_americas/equations_lancet.py` | copies |
| `render_helpers.py` | Presentation in the QMD pages: text, tables, figures, equations, references and the corpus index | |
| `corpus/` | Corpus of version 02 (variant without Rett syndrome, English): 61 plates as 1000 px JPG previews, 134 presentation tables in CSV with their titles and notes, and the module-17 index | `lancet_americas/outputs/sin_rett/en/` |

## Reproduce

```sh
python3 docs/lancet/figuras_principales.py          # Figure_1 … Figure_4, en and es
python3 docs/lancet/figuras_suplementarias.py       # Figure_S2 … Figure_S9 and the check of S1 and S6
python3 scripts/render_reports.py --lancet-figures  # the above and then the seven QMD documents (requires Quarto and Jupyter)
```

The plates generated here are identical to those of the submitted version: the same code reads the same
tables, and the comparison of the SVG text with `lancet_americas/manuscript/10_revision_2026-09-14_paneles/figures/`
shows no differences. To update `contenido_v10.json` after changing the manuscript, run
`technical/sources/export_docs_content.py` in the revision folder.

## Notes

- All counts are administrative recognition (episodes, entries, stocks, enrolments), not prevalence or
  incidence. Case definition: F84 without F84.2 (without Rett) for GRD; strict autism code for REM.
- `lancet_corpus.html` does not embed its resources (`embed-resources: false`) so as not to exceed 15 MB;
  it needs `docs/lancet_corpus_files/` and `docs/lancet/corpus/figures/`.
