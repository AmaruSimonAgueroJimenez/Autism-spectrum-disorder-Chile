"""Generate the extended-plate chapters, inlining the drawing code of every plate that has one.

The extended plates were stored images: the pipeline that drew them is versioned but reads microdata
that is not in the repository. Where a plate's series survive in a published table, `docs/study/plates/`
holds a module that redraws it. This script writes those modules into the chapters, so each redrawn
plate is printed together with the code that draws it rather than linked from a folder — and the
plates that have no module keep their stored image and say why.

One chapter per thematic group of the corpus, because a single chapter carrying every plate's code
would be unreadable and would render to a very large page.

    python scripts/build_plates_chapters.py            # rewrite the chapters
    python scripts/build_plates_chapters.py --check    # exit 1 if they are out of date
"""
from pathlib import Path
import argparse
import ast
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
STUDY = DOCS / "study"
MODULES = STUDY / "plates"

# Group key in the corpus index -> (chapter file, chapter title, subtitle)
CHAPTERS = [
    ("__article__", "plates_core.qmd", "Principal plates",
     "The plates that carry the main findings, with the core supplementary set that supports them"),
    ("Core supplementary plates of the article", "plates_core.qmd", None, None),
    ("Hospital episodes in detail", "plates_hospital.qmd", "Hospital episodes in detail",
     "Every plate describing the hospital discharge records in depth"),
    ("Aggregate REM administrative pathway in detail", "plates_community.qmd", "Community pathway in detail",
     "Every plate describing the monthly statistical returns of the public network"),
    ("Spatial analysis and territorial correlation", "plates_territory.qmd", "Territory and spatial structure",
     "Every plate describing where recognition happens and how it clusters"),
    ("Denominators, surveys and education", "plates_context.qmd", "Denominators, surveys and education",
     "The plates that place the health records against population, survey and school sources"),
    ("Sex ratio across sources", "plates_context.qmd", None, None),
    ("Model diagnostics and case-definition sensitivity", "plates_context.qmd", None, None),
]


def module_source(plate_id):
    """The drawing code of one plate, ready to inline: docstring dropped, draw() renamed per plate."""
    path = MODULES / f"{plate_id}.py"
    if not path.is_file():
        return None
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) \
            and isinstance(tree.body[0].value.value, str):
        src = "\n".join(src.splitlines()[tree.body[0].end_lineno:]).lstrip("\n")
    safe = re.sub(r"\W", "_", plate_id)
    src = re.sub(r"\bdef draw\(\)", f"def draw_{safe}()", src)
    if f"def draw_{safe}()" not in src:
        raise SystemExit(f"{plate_id}: no draw() to rename")
    return inline_safe(src), safe


# A module resolves its paths from __file__, which does not exist inside a notebook chunk. The chapter's
# setup chunk already defines ROOT, so the same paths are rewritten against it when the code is inlined.
FILE_PATHS = [
    (r"Path\(__file__\)\.resolve\(\)\.parents\[3\]", 'ROOT'),
    (r"Path\(__file__\)\.resolve\(\)\.parents\[2\]", 'ROOT / "docs"'),
    (r"Path\(__file__\)\.resolve\(\)\.parents\[1\]", 'ROOT / "docs" / "study"'),
    (r"Path\(__file__\)\.resolve\(\)\.parent\b", 'ROOT / "docs" / "study" / "plates"'),
    (r"Path\(__file__\)\.parent\b", 'ROOT / "docs" / "study" / "plates"'),
]


def inline_safe(src):
    """Make module source runnable inside a chapter chunk: no __file__, no command-line entry point."""
    tree = ast.parse(src)
    lines = src.splitlines()
    for node in tree.body:
        if isinstance(node, ast.If) and getattr(getattr(node.test, "left", None), "id", "") == "__name__":
            for i in range(node.lineno - 1, node.end_lineno):
                lines[i] = None
    src = "\n".join(l for l in lines if l is not None)
    for pattern, replacement in FILE_PATHS:
        src = re.sub(pattern, replacement, src)
    if "__file__" in src:
        raise SystemExit(f"unhandled __file__ reference after inlining:\n"
                         + "\n".join(l for l in src.splitlines() if "__file__" in l))
    return src.rstrip() + "\n"


def plate_section(item, caps, titles, helpers):
    """One plate: its code and figure if a module exists, otherwise the stored image."""
    plate_id = item["file"].replace(".png", "")
    meta = helpers.corpus_lookup(plate_id, caps["main"], caps["extra"], item["id"], item["desc"])
    title = meta.get("title", plate_id)
    made = module_source(plate_id)
    head = f"### {item['id']}. {title}\n"
    if not made:
        body = (f"\n::: {{.callout-note collapse=\"true\"}}\n"
                f"## Stored image — this plate has no drawing code here\n\n"
                f"Its series are not fully carried by any published table, so it cannot be redrawn from a\n"
                f"clone. The code that produced it is in `study/pipeline/`; what is missing is the microdata\n"
                f"it reads.\n:::\n\n"
                + helpers.corpus_figure_md(plate_id, meta) + "\n")
        return head + body
    src, safe = made
    return f"""{head}
```{{python}}
#| label: lamina-{safe.lower()}
#| fig-cap: "{item['id']}. Redrawn here from the published tables by the code above."
{src}

draw_{safe}()
```
"""


def build():
    sys.path.insert(0, str(STUDY))
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_helpers as helpers

    idx = helpers.corpus_index()
    caps, titles = helpers.corpus_captions(), helpers.corpus_titles()
    by_group = {"__article__": idx["article_figures"]}
    for it in idx["figures"]:
        by_group.setdefault(it["group"], []).append(it)

    pages, written = {}, []
    for group, filename, title, subtitle in CHAPTERS:
        items = by_group.get(group, [])
        if filename not in pages:
            pages[filename] = {"title": title, "subtitle": subtitle, "parts": []}
        pages[filename]["parts"].append((group, items))

    for filename, page in pages.items():
        drawn = sum(1 for _, items in page["parts"] for it in items
                    if (MODULES / f"{it['file'].replace('.png', '')}.py").is_file())
        total = sum(len(items) for _, items in page["parts"])
        out = [f"""---
title: "{page['title']}"
subtitle: "{page['subtitle']}"
---

```{{python}}
#| label: preparacion
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "docs" else Path.cwd()
sys.path.insert(0, str(ROOT / "docs" / "study"))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import render_helpers as rh
from report_helpers import kpis
from figstyle import *

idx = rh.corpus_index(); caps = rh.corpus_captions(); titles = rh.corpus_titles()
kpis([
    ("{drawn}", "Plates redrawn here, with their code"),
    ("{total - drawn}", "Plates kept as stored images"),
    ("{total}", "Plates in this chapter"),
])
```

Of the {total} plates in this chapter, {drawn} are redrawn from the published tables by the code shown
with each one; the rest are stored images because their series are not fully carried by any published
table. Use **Show the code that produced this** under a redrawn plate to read how it is built.

::: {{.callout-important}}
## Redrawn plates are faithful reconstructions, not the original artwork

The code that produced the stored plates lives in `study/pipeline/` and reads microdata that is not in
this repository. What is shown here was written from the published aggregates: the panels, the series
and the numbers are the same, checked value by value against the original, but the artwork is not
pixel-identical — fonts, tick formatting and label placement differ. Each module in
`docs/study/plates/` records its own deviations.
:::
"""]
        for group, items in page["parts"]:
            if not items:
                continue
            if group != "__article__":
                out.append(f"\n## {group}\n")
            for it in items:
                out.append(plate_section(it, caps, titles, helpers))
        (DOCS / filename).write_text("\n".join(out), encoding="utf-8")
        written.append(filename)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the chapters are not what this script would write")
    args = ap.parse_args()
    files = [DOCS / f for _, f, _, _ in CHAPTERS]
    if args.check:
        before = {f: f.read_text(encoding="utf-8") if f.exists() else "" for f in set(files)}
        build()
        stale = [f.name for f, text in before.items() if f.read_text(encoding="utf-8") != text]
        if stale:
            for f, text in before.items():
                f.write_text(text, encoding="utf-8")
            raise SystemExit(f"out of date: {', '.join(stale)} — run python scripts/build_plates_chapters.py")
        print("the plate chapters match the modules")
        return
    written = build()
    print(f"written {len(written)} chapters: {', '.join(written)}")


if __name__ == "__main__":
    main()
