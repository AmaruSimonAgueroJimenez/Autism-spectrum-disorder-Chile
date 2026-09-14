# -*- coding: utf-8 -*-
"""folio_audit.py — cuenta las páginas SIN folio de cada PDF construido.

Por qué existe. El folio no lo escribe el texto del documento: lo escribe un campo `PAGE` en el pie de la
SECCIÓN, y Word hereda ese pie sólo hacia ADELANTE. Una sección sin `w:footerReference` propia toma el de la
anterior, nunca el de la siguiente, de modo que un pie escrito en una sección intermedia deja sin numerar
todo lo que va delante. Eso dejó 171 páginas sin folio en los cuatro apéndices sueltos —de la portada al
final de la metodología extendida— mientras el informe de construcción afirmaba «un folio en cada página»:
ninguna prueba de la suite lo veía, porque la suite comprueba el código y los bloques, no el PDF impreso.

Aquí se mide lo IMPRESO: se extrae el texto de cada página y se exige que su última línea útil sea el
número de página y nada más. Es la misma lectura que hace quien pasa las hojas.

    python study/tools/folio_audit.py
    python study/tools/folio_audit.py --dir study/manuscript --json folios.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent

#: El folio es la última línea útil de la página y sólo el número: hasta cuatro cifras, sin nada alrededor.
FOLIO = re.compile(r"\d{1,4}")


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        raise RuntimeError(f"pdfinfo no devuelve el número de páginas de {pdf}")
    return int(m.group(1))


def pages_without_folio(pdf: Path) -> tuple[int, list[int]]:
    """Devuelve (páginas, lista de páginas sin folio). La página 1 cuenta como cualquier otra."""
    n = page_count(pdf)
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    pages = txt.split("\f")[:n]
    missing = []
    for i, page in enumerate(pages, 1):
        util = [line.strip() for line in page.rstrip().splitlines() if line.strip()]
        if not util or not FOLIO.fullmatch(util[-1]):
            missing.append(i)
    return n, missing


def _ranges(nums: list[int]) -> str:
    if not nums:
        return ""
    out, start, prev = [], nums[0], nums[0]
    for x in nums[1:]:
        if x == prev + 1:
            prev = x
            continue
        out.append(f"{start}" if start == prev else f"{start}–{prev}")
        start = prev = x
    out.append(f"{start}" if start == prev else f"{start}–{prev}")
    return ", ".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(PKG / "manuscript"), help="carpeta con los PDF construidos")
    ap.add_argument("--json", default=None, help="escribir el detalle en este archivo")
    args = ap.parse_args()

    report, total_pages, total_missing = {}, 0, 0
    for pdf in sorted(Path(args.dir).glob("*.pdf")):
        n, missing = pages_without_folio(pdf)
        report[pdf.name] = dict(pages=n, without_folio=len(missing), pages_without_folio=missing)
        total_pages += n
        total_missing += len(missing)
        marca = "  OK" if not missing else f"  SIN FOLIO: pp. {_ranges(missing)}"
        print(f"{pdf.name:34s} {n:5d} pp {marca}")
    print(f"\nTOTAL: {len(report)} documentos, {total_pages:,} páginas, "
          f"{total_missing:,} sin folio")
    if args.json:
        Path(args.json).write_text(json.dumps(
            dict(documents=report, total_pages=total_pages, total_without_folio=total_missing),
            ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if total_missing else 0


if __name__ == "__main__":
    sys.exit(main())
