"""Render index, metodología, REM and GRD; optionally refresh aggregates from canonical data.

Refresh order: identifier audit, REM extraction, GRD trajectories, GRD descriptive
epidemiology and, finally, rates and spatial statistics (which need the INE
projections, the shapefiles and the scientific Python stack).
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXTRACTION = ["audit_grd_linkage.py", "audit_rem.py", "grd_trajectories.py", "grd_epidemiology.py"]
DOCUMENTS = {"index.qmd", "metodologia.qmd", "rem.qmd", "grd.qmd"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerar agregados desde las fuentes antes de renderizar")
    parser.add_argument("--rates-only", action="store_true", help="Recalcular solo tasas y estadísticos espaciales (epi_rates.py) antes de renderizar")
    parser.add_argument("--skip-spatial", action="store_true", help="Omitir Moran y LISA al recalcular tasas")
    args = parser.parse_args()
    quarto = shutil.which("quarto")
    if not quarto:
        raise SystemExit("No se encontró Quarto. Instálelo para renderizar los QMD.")
    if args.refresh:
        for name in EXTRACTION:
            subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, check=True)
    if args.refresh or args.rates_only:
        command = [sys.executable, str(ROOT / "scripts" / "epi_rates.py")]
        if args.skip_spatial:
            command.append("--skip-spatial")
        subprocess.run(command, cwd=ROOT, check=True)
    found = {p.name for p in (ROOT / "docs").glob("*.qmd")}
    if found != DOCUMENTS:
        raise SystemExit(f"docs debe contener exactamente {sorted(DOCUMENTS)}; contiene {sorted(found)}")
    env = os.environ.copy()
    env["QUARTO_PYTHON"] = sys.executable
    subprocess.run([quarto, "render", str(ROOT / "docs")], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
