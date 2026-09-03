"""Render index, REM and GRD; optionally refresh aggregates from canonical data."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerar agregados desde las fuentes antes de renderizar")
    args = parser.parse_args()
    quarto = shutil.which("quarto")
    if not quarto:
        raise SystemExit("No se encontró Quarto. Instálelo para renderizar los QMD.")
    if args.refresh:
        for name in ["audit_grd_linkage.py", "audit_rem.py", "grd_trajectories.py"]:
            subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, check=True)
    expected = {"index.qmd", "rem.qmd", "grd.qmd"}
    found = {p.name for p in (ROOT / "docs").glob("*.qmd")}
    if found != expected:
        raise SystemExit(f"docs debe contener exactamente {sorted(expected)}; contiene {sorted(found)}")
    env = os.environ.copy()
    env["QUARTO_PYTHON"] = sys.executable
    subprocess.run([quarto, "render", str(ROOT / "docs")], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
