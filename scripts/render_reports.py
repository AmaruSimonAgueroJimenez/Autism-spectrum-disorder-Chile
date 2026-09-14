"""Render the home page, methods, REM, GRD and the three manuscript pages (article, supplement,
corpus); optionally refresh the aggregates from the canonical data, and regenerate the manuscript plates
of `docs/lancet/` with `--lancet-figures`.

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
DOCUMENTS = {"index.qmd", "methods.qmd", "rem.qmd", "grd.qmd", "lancet.qmd", "lancet_supplement.qmd", "lancet_corpus.qmd"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerate the aggregates from the sources before rendering")
    parser.add_argument("--rates-only", action="store_true", help="Recompute only rates and spatial statistics (epi_rates.py) before rendering")
    parser.add_argument("--skip-spatial", action="store_true", help="Skip Moran and LISA when recomputing rates")
    parser.add_argument("--lancet-figures", action="store_true", help="Regenerate the manuscript plates first (docs/lancet/figuras_*.py) from docs/lancet/data; the article and supplement pages also rebuild them at render time")
    args = parser.parse_args()
    quarto = shutil.which("quarto")
    if not quarto:
        raise SystemExit("Quarto was not found. Install it to render the QMD documents.")
    if args.refresh:
        for name in EXTRACTION:
            subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, check=True)
    if args.lancet_figures:
        for name in ("figuras_principales.py", "figuras_suplementarias.py"):
            subprocess.run([sys.executable, name], cwd=ROOT / "docs" / "lancet", check=True)
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
