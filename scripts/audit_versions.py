"""Compare the tidy result tables of the manuscript versions and report what each one added.

The claim the site makes -- that no result changed between versions 05 and 10, and that versions
only ever add tables -- is checked here rather than asserted: every CSV in each version's
`technical/data` folder is hashed and compared with the previous version's.

The version folders live in `study/manuscript/`, which is not versioned in git (~1.5 GB of DOCX,
PDF and 600 dpi plates), so this script only runs where those folders exist. `docs/study/versions.json`
carries the result for the site, which is why the pages can be rendered from a clone without them.

    python scripts/audit_versions.py             # human-readable report
    python scripts/audit_versions.py --json      # machine-readable, to refresh versions.json
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "study" / "manuscript"


def digest(path):
    """SHA-256 of one file, read in chunks so a large table does not sit in memory."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inventory():
    """Map every version folder to {table name: digest}, or None when it keeps no tidy tables."""
    if not MANUSCRIPT.is_dir():
        raise SystemExit(f"{MANUSCRIPT} does not exist: the version folders are not versioned in git.")
    out = {}
    for folder in sorted(d for d in MANUSCRIPT.iterdir() if d.is_dir() and d.name[:2].isdigit()):
        data = folder / "technical" / "data"
        out[folder.name] = {p.name: digest(p) for p in sorted(data.rglob("*.csv"))} if data.is_dir() else None
    return out


def compare(inv):
    """Walk consecutive versions that keep tidy tables and record what changed between them."""
    series = [(name, tables) for name, tables in inv.items() if tables]
    steps = []
    for (prev_name, prev), (name, cur) in zip(series, series[1:]):
        common = set(prev) & set(cur)
        changed = sorted(f for f in common if prev[f] != cur[f])
        steps.append({
            "from": prev_name, "to": name,
            "tables_before": len(prev), "tables_after": len(cur),
            "added": sorted(set(cur) - set(prev)),
            "removed": sorted(set(prev) - set(cur)),
            "changed": changed,
            "identical_results": not changed and not (set(cur) - set(prev)),
        })
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit the comparison as JSON")
    args = parser.parse_args()

    inv = inventory()
    steps = compare(inv)
    if args.json:
        json.dump({"inventory": {k: (len(v) if v else None) for k, v in inv.items()}, "steps": steps},
                  sys.stdout, indent=2, ensure_ascii=False)
        print()
        return

    print("Tidy result tables per version")
    for name, tables in inv.items():
        print(f"  {name:<38} {len(tables) if tables else '-':>3} {'CSV' if tables else '(keeps no tidy tables)'}")

    print("\nWhat each version changed")
    drifted = False
    for s in steps:
        print(f"\n  {s['from']}  ->  {s['to']}   ({s['tables_before']} -> {s['tables_after']} tables)")
        if s["changed"]:
            drifted = True
            print(f"    CHANGED {len(s['changed'])} table(s) that already existed:")
            for f in s["changed"]:
                print(f"      ~ {f}")
        else:
            print("    no existing table changed")
        if s["added"]:
            print(f"    added {len(s['added'])}: {', '.join(s['added'][:6])}{' ...' if len(s['added']) > 6 else ''}")
        if s["removed"]:
            print(f"    removed {len(s['removed'])}: {', '.join(s['removed'])}")
        if s["identical_results"]:
            print(f"    -> {s['to']} carries the same results as {s['from']}: the difference is layout only")

    print("\n" + ("A result table changed between versions; versions.json needs refreshing."
                  if drifted else
                  "No existing result table changed in the whole series: versions only ever add tables."))


if __name__ == "__main__":
    main()
