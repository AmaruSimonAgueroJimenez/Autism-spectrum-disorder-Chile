# -*- coding: utf-8 -*-
"""dash_audit.py — EL INSTRUMENTO de la regla de la raya (fase 4j, tarea J2).

Cuenta, sobre el MISMO objeto antes y después de un arreglo, cuántos INTERVALOS NUMÉRICOS DE LECTURA se
imprimen con GUION y cuántos con RAYA CORTA. Mide en los tres sitios en los que el lector los ve:

  * `--tables`   las tablas que el documento imprime (`outputs/<variante>/<idioma>/tables/*.csv` y
                 `.../extra/tables/*.csv`), más `titles.json` y `captions.json`. No mira el hermano
                 `_numeric`, ni `outputs/tidy/`, ni `outputs/controls/`: eso es texto de máquina.
  * `--plate NN` el TEXTO QUE LA LÁMINA DIBUJA. Un rótulo de lámina viaja al documento dentro de un mapa
                 de bits y `pdftotext` no lo ve; medirlo sobre el PDF da siempre «cero defectos». Este
                 modo se engancha a `Figure.savefig`, recorre cada objeto `Text` de la figura con la
                 composición YA CONGELADA y cuenta ahí.
  * `--docx F`   el documento construido, celda a celda y párrafo a párrafo (comprobación cruzada).

La clasificación es la del estudio y NO se repite aquí: la trae `common.count_hyphen_ranges` /
`common.count_dash_ranges`, que es la misma función con la que se escriben las tablas y las láminas.

    python3 study/tools/dash_audit.py --tables
    python3 study/tools/dash_audit.py --plate 13 --variants con_rett --langs en --check strict
    python3 study/tools/dash_audit.py --docx study/manuscript/manuscript_con_rett_en.docx
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = PKG.parent
for p in (str(REPO), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

#: Los nueve módulos que dibujan láminas, por si hay que medirlos uno a uno.
PLATE_MODULES = {
    "06": "06_models.py", "08a": "08a_figures_grd.py", "08b": "08b_figures_rem.py",
    "08c": "08c_figures_triangulation.py", "08d": "08d_figure_dataflow.py",
    "13": "13_extra_figures_hospital.py", "14": "14_extra_figures_rem.py",
    "15": "15_extra_figures_context.py", "15b": "15b_spatial_correlation.py",
}


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def audit_tables(out_root=None) -> dict:
    """Las tablas, los títulos y las leyendas que el documento imprime."""
    import common as C
    import config as CFG
    root = Path(out_root) if out_root else CFG.OUT
    per: dict[str, dict] = {}
    tokens: Counter = Counter()
    total = dict(files=0, hyphen=0, dash=0, cells_hyphen=0, cells_dash=0)
    for variant in CFG.VARIANTS:
        for lang in CFG.LANGUAGES:
            base = root / variant / lang
            for tdir in (base / "tables", base / "extra" / "tables"):
                if not tdir.is_dir():
                    continue
                for path in sorted(tdir.glob("*.csv")):
                    if path.stem.endswith("_numeric"):
                        continue
                    total["files"] += 1
                    with path.open(encoding="utf-8-sig", newline="") as fh:
                        for row in csv.reader(fh):
                            for cell in row:
                                h, d = C.count_hyphen_ranges(cell), C.count_dash_ranges(cell)
                                total["hyphen"] += h
                                total["dash"] += d
                                total["cells_hyphen"] += 1 if h else 0
                                total["cells_dash"] += 1 if d else 0
                                e = per.setdefault(path.stem, dict(hyphen=0, dash=0, cells=0))
                                e["hyphen"] += h
                                e["dash"] += d
                                e["cells"] += 1 if h else 0
                                if h:
                                    for tok in str(cell).split():
                                        if C.count_hyphen_ranges(tok):
                                            tokens[tok] += 1
            for sub in ("tables", "figures", "extra/tables", "extra/figures"):
                for nom in ("titles.json", "captions.json"):
                    path = base / sub / nom
                    if not path.is_file():
                        continue
                    total["files"] += 1
                    for s in _strings(json.loads(path.read_text(encoding="utf-8"))):
                        h, d = C.count_hyphen_ranges(s), C.count_dash_ranges(s)
                        total["hyphen"] += h
                        total["dash"] += d
                        e = per.setdefault(f"{sub}/{nom}", dict(hyphen=0, dash=0, cells=0))
                        e["hyphen"] += h
                        e["dash"] += d
                        e["cells"] += 1 if h else 0
    return dict(scope="tables", total=total, by_file=per, tokens=dict(tokens.most_common(40)))


def audit_plate_module(module: str, variants=None, langs=None, check=None, out_root=None) -> dict:
    """Ejecuta el módulo de lámina y mide el texto que cada figura dibuja al guardarse."""
    if check:
        os.environ["PLATE_CHECK"] = check
    import config as CFG
    if out_root:
        Path(out_root, "controls").mkdir(parents=True, exist_ok=True)
        CFG.OUT = Path(out_root)
    import common as C
    if check:
        C.plate_check_enable(check)
        C.plate_check_reset()
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.text import Text

    seen: list[str] = []
    per: dict[str, dict] = {}
    tokens: Counter = Counter()
    total = dict(hyphen=0, dash=0)
    original = Figure.savefig

    def wrapped(self, fname, *a, **kw):
        name = Path(str(fname)).name
        seen.append(name)
        for art in self.findobj(Text):
            try:
                if not art.get_visible():
                    continue
                s = art.get_text()
            except (AttributeError, ValueError, RuntimeError, TypeError):
                continue
            if not s or "$" in s:
                continue
            h, d = C.count_hyphen_ranges(s), C.count_dash_ranges(s)
            total["hyphen"] += h
            total["dash"] += d
            if h:
                e = per.setdefault(name, dict(hyphen=0, dash=0, texts=[]))
                e["hyphen"] += h
                e["dash"] += d
                if len(e["texts"]) < 12:
                    e["texts"].append(s[:90])
                for tok in s.split():
                    if C.count_hyphen_ranges(tok):
                        tokens[tok] += 1
        return original(self, fname, *a, **kw)

    Figure.savefig = wrapped
    path = PKG / "pipeline" / PLATE_MODULES[module]
    spec = importlib.util.spec_from_file_location("_dash_" + module, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    argv = [str(path)]
    if variants:
        argv += ["--variants", *variants]
    if langs:
        argv += ["--langs", *langs]
    sys.argv = argv
    t0 = time.time()
    try:
        spec.loader.exec_module(mod)
        code = mod.main()
    finally:
        Figure.savefig = original
    rep = dict(scope="plates", module=module, seconds=round(time.time() - t0, 1), exit=code,
               plates=len(seen), plate_names=sorted(set(seen)), total=total, by_plate=per,
               tokens=dict(tokens.most_common(40)))
    if check:
        rep["plate_check"] = C.plate_check_summary()
        rep["plate_check_clean"] = not C.plate_check_records()
    return rep


def audit_docx(path) -> dict:
    """Comprobación cruzada sobre el documento construido: celdas de tabla y párrafos."""
    import zipfile
    from lxml import etree
    import common as C
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    total = dict(cells_hyphen=0, cells_dash=0, hyphen=0, dash=0, prose_hyphen=0, prose_dash=0)
    per: dict[str, dict] = {}
    label = "?"
    import re
    head = re.compile(r"\s*(Table|Tabla)\s+([A-Z]?S?\d+[a-z]?)")
    for el in root.find(W + "body"):
        if el.tag == W + "p":
            s = "".join(t.text or "" for t in el.iter(W + "t"))
            m = head.match(s)
            if m:
                label = f"{m.group(1)} {m.group(2)}"
            total["prose_hyphen"] += C.count_hyphen_ranges(s)
            total["prose_dash"] += C.count_dash_ranges(s)
        elif el.tag == W + "tbl":
            for tr in el.findall(W + "tr"):
                for tc in tr.findall(W + "tc"):
                    vm = tc.find(f"{W}tcPr/{W}vMerge")
                    if vm is not None and vm.get(W + "val") != "restart":
                        continue
                    s = "".join(t.text or "" for t in tc.iter(W + "t"))
                    h, d = C.count_hyphen_ranges(s), C.count_dash_ranges(s)
                    total["hyphen"] += h
                    total["dash"] += d
                    total["cells_hyphen"] += 1 if h else 0
                    total["cells_dash"] += 1 if d else 0
                    if h:
                        e = per.setdefault(label, dict(hyphen=0, dash=0, cells=0))
                        e["hyphen"] += h
                        e["dash"] += d
                        e["cells"] += 1
    return dict(scope="docx", document=Path(path).name, total=total, by_table=per)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", action="store_true")
    ap.add_argument("--plate", choices=sorted(PLATE_MODULES))
    ap.add_argument("--docx", nargs="+")
    ap.add_argument("--variants", nargs="*")
    ap.add_argument("--langs", nargs="*")
    ap.add_argument("--check", choices=("off", "report", "strict"))
    ap.add_argument("--out-root", default=None, help="mide contra otro árbol de salidas")
    ap.add_argument("--out", default=None, help="escribe el informe JSON")
    args = ap.parse_args()
    if not (args.tables or args.plate or args.docx):
        ap.error("hay que pedir --tables, --plate o --docx")

    reports = []
    if args.tables:
        rep = audit_tables(args.out_root)
        t = rep["total"]
        print(f"[tablas] {t['files']} archivos impresos: intervalos con guion={t['hyphen']} "
              f"con raya={t['dash']} (celdas {t['cells_hyphen']} / {t['cells_dash']}); "
              f"archivos afectados={sum(1 for v in rep['by_file'].values() if v['hyphen'])}")
        bad = {k: v for k, v in rep["by_file"].items() if v["hyphen"]}
        print(f"    archivos con al menos un intervalo con guion: {len(bad)}")
        for k, v in sorted(bad.items(), key=lambda kv: -kv[1]["hyphen"])[:25]:
            print(f"    {k:46s} guion={v['hyphen']:5d} raya={v['dash']:5d}")
        reports.append(rep)
    if args.plate:
        rep = audit_plate_module(args.plate, args.variants, args.langs, args.check, args.out_root)
        t = rep["total"]
        print(f"[lámina {args.plate}] {rep['plates']} construcciones: intervalos con guion={t['hyphen']} "
              f"con raya={t['dash']}; láminas afectadas={len(rep['by_plate'])} ({rep['seconds']} s)")
        for k, v in sorted(rep["by_plate"].items(), key=lambda kv: -kv[1]["hyphen"]):
            print(f"    {k:46s} guion={v['hyphen']:5d} raya={v['dash']:5d}")
        if args.check:
            print("    " + rep["plate_check"].splitlines()[0])
        reports.append(rep)
    for doc in (args.docx or []):
        rep = audit_docx(doc)
        t = rep["total"]
        print(f"[docx {rep['document']}] celdas con guion={t['cells_hyphen']} con raya={t['cells_dash']}; "
              f"ocurrencias {t['hyphen']} / {t['dash']}; prosa {t['prose_hyphen']} / {t['prose_dash']}; "
              f"tablas afectadas={len(rep['by_table'])}")
        for k, v in sorted(rep["by_table"].items(), key=lambda kv: -kv[1]["cells"])[:25]:
            print(f"    {k:12s} celdas={v['cells']:4d} guion={v['hyphen']:5d} raya={v['dash']:5d}")
        reports.append(rep)
    if args.out:
        Path(args.out).write_text(json.dumps(reports if len(reports) > 1 else reports[0],
                                             ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
