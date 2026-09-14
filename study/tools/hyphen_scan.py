"""Instrumento J3(1). Ventana de años con guion corto en una CELDA DE PRESENTACIÓN
(no en una columna de clave de máquina ni en una URL) de las tablas formateadas."""
import csv, json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "outputs"
RE = re.compile(r"(?<!\d)(?:19|20)\d{2}-(?:19|20)\d{2}(?!\d)")
KEY_COLS = {"model (identifier)", "modelo (identificador)", "key", "clave",
            "column or key", "columna o clave", "control family", "familia de control", "familia de controles",
            "detail", "detalle"}

def is_key_col(h: str) -> bool:
    return h.replace("﻿", "").strip().lower() in KEY_COLS

leaks, keys = [], []
for variant in ("con_rett", "sin_rett"):
    for lang in ("es", "en"):
        base = ROOT / variant / lang
        if not base.exists():
            continue
        for csvp in sorted(base.rglob("*.csv")):
            if csvp.stem.endswith("_numeric"):
                continue
            with csvp.open(encoding="utf-8") as fh:
                rows = list(csv.reader(fh))
            if not rows:
                continue
            head = rows[0]
            for i, row in enumerate(rows[1:], 1):
                for j, cell in enumerate(row):
                    if not RE.search(cell):
                        continue
                    hdr = head[j] if j < len(head) else ""
                    bucket = keys if (is_key_col(hdr) or "http" in cell) else leaks
                    for m in RE.finditer(cell):
                        bucket.append((f"{variant}/{lang}", csvp.name, hdr.replace("﻿", ""),
                                       m.group(0), cell[:80]))

print(f"DISPLAY_LEAKS={len(leaks)}   (machine-key/URL cells excused: {len(keys)})")
for (v, f, h, w, c), n in Counter(leaks).most_common():
    print(f"   {n:3d}  {v:14s} {f:34s} [{h}]  {c}")
