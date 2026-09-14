"""Instrumento J3(3): glosa del panel fijo de 65 en los títulos/notas/leyendas ya escritos."""
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "outputs"
# la glosa: «panel fijo … » / «fixed panel …» seguida de lo que la califica hasta el punto o el punto y coma
RX = re.compile(r"(?:panel fijo|fixed panel)[^.;]{0,110}")
# la que dice el AÑO en el que están presentes
WINDOW = re.compile(r"(?:presentes?|present)[^.;]{0,25}(20\d\d[–-]20\d\d|todos los años|every year)")

def strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)
    elif isinstance(obj, str):
        yield obj

glosses = Counter()
windows = Counter()
for variant in ("con_rett", "sin_rett"):
    for lang in ("es", "en"):
        for jp in sorted((ROOT / variant / lang).rglob("*.json")):
            for s in strings(json.loads(jp.read_text(encoding="utf-8"))):
                for m in RX.finditer(s):
                    glosses[m.group(0).strip()] += 1
                    w = WINDOW.search(m.group(0))
                    if w:
                        windows[w.group(1)] += 1

print(f"GLOSSES={sum(glosses.values())}  distinct={len(glosses)}")
print("year-window wording used:", dict(windows))
for k, v in glosses.most_common():
    print(f"   {v:3d}  {k}")
