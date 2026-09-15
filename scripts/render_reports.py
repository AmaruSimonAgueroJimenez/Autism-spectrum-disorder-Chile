"""Render the report: a Quarto book whose chapters are the front page, methods, results, the two
source chapters and the extended material; optionally refresh the aggregates from the canonical data,
and regenerate the plates of `docs/study/` with `--figures`.

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
DOCUMENTS = {"index.qmd", "methods.qmd", "results.qmd", "hospital.qmd", "community.qmd", "tables.qmd", "plates_core.qmd", "plates_hospital.qmd", "plates_community.qmd", "plates_territory.qmd", "plates_context.qmd", "extended_tables.qmd", "reproducibility.qmd"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerate the aggregates from the sources before rendering")
    parser.add_argument("--rates-only", action="store_true", help="Recompute only rates and spatial statistics (epi_rates.py) before rendering")
    parser.add_argument("--skip-spatial", action="store_true", help="Skip Moran and LISA when recomputing rates")
    parser.add_argument("--figures", action="store_true", help="Regenerate the plates first (docs/study/figuras_*.py) from docs/study/data; the version 10 page also rebuilds them at render time")
    args = parser.parse_args()
    quarto = shutil.which("quarto")
    if not quarto:
        raise SystemExit("Quarto was not found. Install it to render the QMD documents.")
    if args.refresh:
        for name in EXTRACTION:
            subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, check=True)
    if args.figures:
        for name in ("figuras_principales.py", "figuras_suplementarias.py"):
            subprocess.run([sys.executable, name], cwd=ROOT / "docs" / "study", check=True)
    if args.refresh or args.rates_only:
        command = [sys.executable, str(ROOT / "scripts" / "epi_rates.py")]
        if args.skip_spatial:
            command.append("--skip-spatial")
        subprocess.run(command, cwd=ROOT, check=True)
    found = {p.name for p in (ROOT / "docs").glob("*.qmd")}
    if found != DOCUMENTS:
        raise SystemExit(f"docs must contain exactly {sorted(DOCUMENTS)}; it contains {sorted(found)}")
    env = os.environ.copy()
    env["QUARTO_PYTHON"] = sys.executable
    subprocess.run([quarto, "render", str(ROOT / "docs")], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
