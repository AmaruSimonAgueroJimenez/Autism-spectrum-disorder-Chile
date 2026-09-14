# -*- coding: utf-8 -*-
"""run_all.py — ejecuta los pasos numerados del pipeline en orden, desde un entorno limpio.

    python lancet_americas/pipeline/run_all.py            # todos los pasos
    python lancet_americas/pipeline/run_all.py --from 06  # desde el paso 06
    python lancet_americas/pipeline/run_all.py --only 02  # un solo paso
    python lancet_americas/pipeline/run_all.py --list     # muestra los pasos detectados

Los pasos son los archivos `NN_*.py` (y `NNx_*.py`) de esta carpeta, ordenados por su prefijo.
Cada paso se ejecuta como proceso separado con el mismo intérprete; un fallo detiene la cadena.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PATTERN = re.compile(r"^(\d{2}[a-z]?)_.+\.py$")


def steps() -> list[tuple[str, Path]]:
    found = []
    for path in sorted(HERE.glob("*.py")):
        m = PATTERN.match(path.name)
        if m:
            found.append((m.group(1), path))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="start", help="prefijo del primer paso a ejecutar (p. ej. 06)")
    parser.add_argument("--only", help="ejecutar solo el paso con este prefijo")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    selected = steps()
    if args.list:
        for prefix, path in selected:
            print(prefix, path.name)
        return 0
    if args.only:
        selected = [(p, f) for p, f in selected if p == args.only]
    elif args.start:
        selected = [(p, f) for p, f in selected if p >= args.start]
    if not selected:
        print("No hay pasos que ejecutar", file=sys.stderr)
        return 1
    t0 = time.time()
    for prefix, path in selected:
        print(f"=== [{prefix}] {path.name}", flush=True)
        t1 = time.time()
        result = subprocess.run([sys.executable, str(path)], cwd=REPO)
        print(f"=== [{prefix}] terminado en {time.time() - t1:.0f} s (código {result.returncode})", flush=True)
        if result.returncode != 0:
            print(f"El paso {prefix} falló; se detiene la cadena.", file=sys.stderr)
            return result.returncode
    print(f"Pipeline completo en {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
