"""Generate `docs/version_10_panels.qmd` with the plotting code inlined into the page.

The page must carry the code that draws each figure, not a link to a stored PNG. The drawing code
lives in `docs/study/figuras_principales.py` and `figuras_suplementarias.py`, which stay in place so
the 600 dpi plates can still be rebuilt outside the site. To keep the two copies from drifting, the
page is generated from those modules rather than edited by hand, and
`tests/test_page_figure_code.py` fails if the code in the page stops matching the module.

    python scripts/build_version_pages.py            # rewrite the page
    python scripts/build_version_pages.py --check    # exit 1 if the page is out of date

Every supplementary figure is now drawn from tracked tables: S1 and S6 were static plates inherited
from revision 09 until their drawing code was reconstructed from the published aggregates.
"""
from pathlib import Path
import argparse
import ast
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs" / "study"
PAGE = ROOT / "docs" / "version_10_panels.qmd"

MAIN = ["1", "2", "3", "4"]
SUPP = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]


def module_parts(path):
    """Split a figure module into (preamble source, {figure id: function source})."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    figures, preamble = {}, []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and re.fullmatch(r"fig(S?\d+)", node.name):
            figures[re.fullmatch(r"fig(S?\d+)", node.name).group(1)] = ast.get_source_segment(src, node)
        elif isinstance(node, ast.If) and getattr(getattr(node.test, "left", None), "id", "") == "__name__":
            continue                                    # the command-line entry point is not needed in a page
        elif isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno < 20:
            preamble.append(ast.get_source_segment(src, node))
        else:
            preamble.append(ast.get_source_segment(src, node))
    return "\n".join(p for p in preamble if p), figures


def as_chunk(source, fig_id):
    """Turn a `figN(lang)` function into code a chunk can run: export both languages, show English."""
    name = f"Figure_{fig_id}"
    # Keep the figure open so the chunk can display it, and hand it back to the caller.
    patched = re.sub(rf"save\(fig, '{name}', lang\)", f"save(fig, '{name}', lang, close=False)\n    return fig", source)
    if "return fig" not in patched:
        raise SystemExit(f"{name}: could not find the save() call to patch")
    return patched


def build():
    main_pre, main_figs = module_parts(STUDY / "figuras_principales.py")
    supp_pre, supp_figs = module_parts(STUDY / "figuras_suplementarias.py")
    missing = [f for f in MAIN if f not in main_figs] + [f for f in SUPP if f not in supp_figs]
    if missing:
        raise SystemExit(f"figures not found in the modules: {missing}")

    out = [HEADER]
    out.append(SETUP.format(main_preamble=indent_free(main_pre), supp_preamble=indent_free(supp_pre)))
    out.append(BODY_INTRO)

    out.append("## Panel figures\n")
    for fid in MAIN:
        out.append(figure_section(fid, as_chunk(main_figs[fid], fid)))

    out.append("## Supplementary figures\n")
    for fid in SUPP:
        out.append(figure_section(fid, as_chunk(supp_figs[fid], fid)))

    out.append(TABLES)
    PAGE.write_text("\n".join(out), encoding="utf-8")


def indent_free(source):
    """Drop the module docstring and the shebang-style header lines a page does not need."""
    tree = ast.parse(source)
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) \
            and isinstance(tree.body[0].value.value, str):
        lines = source.splitlines()
        source = "\n".join(lines[tree.body[0].end_lineno:])
    return source.strip("\n")


def figure_section(fig_id, code):
    label = f"Figure {fig_id}"
    return f"""### {label}

```{{python}}
#| label: figura-{fig_id.lower()}
#| fig-cap: "{label}. Drawn by the code above from the public tables in docs/study/data/."
{code}

plt.close(fig{fig_id}('es'))          # Spanish plate: exported to docs/study/figures/es/
fig{fig_id}('en')                     # English plate: exported and shown here
```
"""


HEADER = '''---
title: "Version 10 results: four panel figures"
subtitle: "Results of the most recent version (14 September 2026). Every figure and table on this page is drawn by the code shown with it, from the tables versioned in docs/study/data/"
---

::: {.report-nav}
[Home](index.html) [Methods](methods.html) [REM](rem.html) [GRD](grd.html) [v01](version_01_initial.html) [v02 corpus](version_02_corpus.html) [v05](version_05_revision.html) [v06](version_06_expanded.html) [v07](version_07_editorial.html) [v10 results](version_10_panels.html)
:::
'''

SETUP = '''
```{{python}}
#| label: preparacion
# Everything the figures below need. The drawing code is the code that produced the submitted
# plates: it is generated into this page from docs/study/figuras_*.py by
# scripts/build_version_pages.py, and tests/test_page_figure_code.py fails if the two drift.
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "docs" else Path.cwd()
sys.path.insert(0, str(ROOT / "docs" / "study"))
sys.path.insert(0, str(ROOT / "scripts"))
from report_helpers import kpis, number, show_table
import render_helpers as rh

{main_preamble}

{supp_preamble}
```
'''

BODY_INTRO = '''
```{python}
#| label: resumen
v10 = rh.version("10")
kpis([
    ("13", "Figures drawn by this page from the public tables"),
    ("0", "Figures inherited from earlier revisions with no drawing code"),
    (str(len(rh.data_tables())), "Public tidy tables the page reads"),
    (f"v{v10['identical_results_to']}", "Version whose results these are, unchanged"),
])
```

This page carries the **results** of version 10 of the study: the panel figures, the supplementary
figures and the tables, each drawn by the code shown with it. It does not reproduce the text of the
manuscript, which is not part of this repository.

```{python}
#| label: nota-auditoria
#| output: asis
print(f"> **What version 10 changed.** {v10['results']}\\n>\\n> {rh.audit_note()}\\n")
```

Case definition: GRD episodes with an eligible F84 code, excluding Rett syndrome (F84.2); REM
programmes with the strict autism code except where the "F84 family" is indicated. Every count is
administrative recognition, **not prevalence or incidence**. The [extended corpus](version_02_corpus.html)
holds the plates and tables of the earlier versions, and the [index](index.html#versions) records what
each version of the series added.

::: {.callout-important}
## Figures S1 and S6 are reconstructions, not the original plates

Until version 10 these two were static artwork inherited from revision 09; this repository held no code
that drew them. The code shown with them here was written from the published aggregates, and it
reproduces the same panels and the same numbers, but it is not the code that made the submitted plates
and the artwork is not pixel-identical to them. Figure S6 in particular uses an equal-area projection
fitted to the printed original, which drew the shapefile unprojected, so its map panels differ by one
to two per cent in aspect ratio. Treat both as faithful redraws, not as the originals.
:::

Use **Show the code that produced this** under any figure or table, or the **`</>` Code** button at the
top right, to read the code that drew it. Each figure chunk exports the 175 mm PNG, SVG and PDF files
to `docs/study/figures/` as it runs, in English and Spanish, and displays the English plate.
'''

TABLES = '''
## Tables

Each table is computed here from the aggregated CSVs in `docs/study/data/`, which ship with the
repository, so the whole page can be rebuilt from a clone without the source microdata.

```{python}
#| label: tabla-episodios
import pandas as pd

# Eligible hospital episodes and their rate per 100 000 GRD episodes of the same panel, by year.
# load_grd_summary() is the same loader the figures above use, so the table cannot apply a different
# case definition than the plates: variant sin_rett (F84 family without F84.2), all activities.
observed = (load_grd_summary()
            .query("panel == 'observed' and position == 'any'")
            .loc[:, ["year", "n_episodes_f84", "n_episodes_total_same_panel_activity",
                     "rate_per_100k_episodes", "rate_lo", "rate_hi"]]
            .sort_values("year"))
observed["95% CI"] = observed.apply(lambda r: f"{r.rate_lo:.1f}–{r.rate_hi:.1f}", axis=1)
show_table(observed.drop(columns=["rate_lo", "rate_hi"]).rename(columns={
    "year": "Year", "n_episodes_f84": "Eligible episodes",
    "n_episodes_total_same_panel_activity": "All GRD episodes of the panel",
    "rate_per_100k_episodes": "Per 100 000 GRD episodes"}),
    "Eligible hospital episodes by year, observed panel, code in any diagnostic position",
    {"Per 100 000 GRD episodes": 1})
```

```{python}
#| label: tabla-datos-publicos
# The tables this page reads, so the reader can see exactly what the figures were built from.
show_table(pd.DataFrame(rh.data_tables()).rename(columns={"name": "Table", "rows": "Rows", "kb": "Size (KB)"}),
           f"The {len(rh.data_tables())} public tidy tables in docs/study/data/", {"Size (KB)": 1})
```

Commune-level tables that carry cells under five cases are withheld: the site publishes the masked
commune extract instead, without commune identifiers.
'''


# ------------------------------------------------------------------ one page per distinct version
# Versions 05, 06 and 07 each added result tables without changing any that already existed
# (scripts/audit_versions.py proves this), so each gets a page showing exactly what it added.
# Version 08 has the same 62 tables as 07 and version 10 the same 71 as 09, so they share a page.
VERSION_PAGES = [
    ("05", "version_05_revision.qmd", "Version 05 results: the tidy baseline", None),
    ("06", "version_06_expanded.qmd", "Version 06 results: the expanded supplement", "05"),
    ("07", "version_07_editorial.qmd", "Version 07 results: the editorial restructure", "06"),
]

VERSION_PAGE = """---
title: "{title}"
subtitle: "{subtitle}"
---

::: {{.report-nav}}
[Home](index.html) [Methods](methods.html) [REM](rem.html) [GRD](grd.html) [v01](version_01_initial.html) [v02 corpus](version_02_corpus.html) [v05](version_05_revision.html) [v06](version_06_expanded.html) [v07](version_07_editorial.html) [v10 results](version_10_panels.html)
:::

```{{python}}
#| label: preparacion
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "docs" else Path.cwd()
sys.path.insert(0, str(ROOT / "docs" / "study"))
sys.path.insert(0, str(ROOT / "scripts"))
import json
import pandas as pd
import render_helpers as rh
from report_helpers import kpis, show_table

VID = "{vid}"
PREV = {prev!r}
DATA = ROOT / "docs" / "study" / "data"
manifest = json.loads((ROOT / "docs" / "study" / "version_tables.json").read_text(encoding="utf-8"))
meta = rh.version(VID)
mine = manifest[VID]
added = sorted(set(mine["tables"]) - set(manifest[PREV]["tables"])) if PREV else sorted(mine["tables"])
kpis([
    (str(len(mine["tables"])), "Result tables in this version"),
    (str(len(added)), "Added by this version" if PREV else "Tables of the baseline"),
    ("0", "Tables changed from the previous version"),
    (str(len(mine["withheld"])), "Withheld from publication"),
])
```

```{{python}}
#| label: que-cambio
#| output: asis
print(f"> **What version {{VID}} is.** {{meta['what']}}\\n>\\n> **Its results.** {{meta['results']}}\\n")
```

This page is the result set of version {vid} of the study. The tables below ship with the repository, so
every number here can be read from a clone. What this version added is not an editorial claim:
`scripts/audit_versions.py` hashes every table in every version folder and compares them pairwise, and
this page is rendered from the manifest that script feeds. The audit's finding for the whole series:

```{{python}}
#| label: nota-auditoria
#| output: asis
print(f"> {{rh.audit_note()}}\\n")
```

## {heading}

```{{python}}
#| label: tablas-nuevas
inventory = []
for name in added:
    path = DATA / name
    if not path.exists():
        inventory.append({{"Table": name, "Rows": "withheld", "Columns": "withheld", "Size (KB)": None}})
        continue
    frame = pd.read_csv(path)
    inventory.append({{"Table": name, "Rows": len(frame), "Columns": len(frame.columns),
                      "Size (KB)": round(path.stat().st_size / 1024, 1)}})
show_table(pd.DataFrame(inventory), "{caption}", {{"Size (KB)": 1}})
```

## Every result table of version {vid}

Tables marked as withheld carry commune identifiers with cells under five cases and are not published;
the site ships the masked commune extract instead, without commune identifiers.

```{{python}}
#| label: inventario-completo
rows = [{{"Table": n, "Published": "yes" if n in mine["public"] else "withheld",
         "New in this version": "yes" if n in added else ""}} for n in sorted(mine["tables"])]
show_table(pd.DataFrame(rows), f"The {{len(mine['tables'])}} result tables of version {{VID}}")
```

## Where the rest of the series is

The [index](index.html#versions) lists all ten versions and what each one added. The plates of this
version's results are drawn on the [version 10 page](version_10_panels.html), which carries the same
numbers laid out as panel figures, and the [version 02 corpus](version_02_corpus.html) holds the
earlier plates and tables.
"""


def build_version_pages():
    """Emit one page per version that added result tables."""
    import json as _json
    manifest = _json.loads((STUDY / "version_tables.json").read_text(encoding="utf-8"))
    registry = _json.loads((STUDY / "versions.json").read_text(encoding="utf-8"))
    titles = {v["id"]: v for v in registry["versions"]}
    written = []
    for vid, filename, title, prev in VERSION_PAGES:
        entry = titles[vid]
        n_added = len(set(manifest[vid]["tables"]) - set(manifest[prev]["tables"])) if prev else len(manifest[vid]["tables"])
        heading = f"The {n_added} tables version {vid} added" if prev else f"The {n_added} tables of the baseline"
        caption = (f"Tables added by version {vid} to the {len(manifest[prev]['tables'])} of version {prev}"
                   if prev else f"The {n_added} result tables of the baseline")
        page = VERSION_PAGE.format(
            title=title, vid=vid, prev=prev, heading=heading, caption=caption,
            subtitle=f"{entry['title']} ({entry['date']}) - {len(manifest[vid]['tables'])} result tables, "
                     f"none of them changed from the previous version")
        (ROOT / "docs" / filename).write_text(page, encoding="utf-8")
        written.append(filename)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the page is not what this script would write")
    args = ap.parse_args()
    if args.check:
        before = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""
        build()
        after = PAGE.read_text(encoding="utf-8")
        if before != after:
            PAGE.write_text(before, encoding="utf-8")
            raise SystemExit("docs/version_10_panels.qmd is out of date: run python scripts/build_version_pages.py")
        print("the page matches the figure modules")
        return
    build()
    pages = build_version_pages()
    print(f"written {PAGE.relative_to(ROOT)} and {len(pages)} version pages: {', '.join(pages)}")


if __name__ == "__main__":
    main()
