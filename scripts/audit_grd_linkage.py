"""Audit identifier continuity without exporting identifiers or patient records."""
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path
import os
import pandas as pd


def parse_dates(values: pd.Series) -> pd.Series:
    """Parse the two observed formats explicitly; never infer ambiguous dates."""
    values = values.astype("string").str.strip()
    iso = pd.to_datetime(values, format="%Y-%m-%d", errors="coerce")
    return iso.fillna(pd.to_datetime(values, format="%d-%m-%Y", errors="coerce"))


def data_root() -> Path:
    root = Path(os.environ.get("ASESORIAS_DATA_ROOT", "/Volumes/Datos/Asesorias_Data"))
    if not root.is_dir():
        raise FileNotFoundError(f"Monte el disco o configure ASESORIAS_DATA_ROOT: {root}")
    return root


def valid_id(values: pd.Series) -> pd.Series:
    return values.notna() & ~values.str.strip().str.upper().isin(
        ["", "0", "-1", "NA", "NAN", "NULL", "DESCONOCIDO", "SIN INFORMACION", "SIN INFORMACIÓN"]
    )


def audit(root: Path, output: Path, years: list[int]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    profiles, annual, sources = {}, [], []
    for year in years:
        path = root / "GRD" / f"GRD_PUBLICO_{year}.csv"
        header = pd.read_csv(path, sep="|", nrows=0).columns
        id_col = "ID_BENEFICIARIO" if "ID_BENEFICIARIO" in header else "CIP_ENCRIPTADO"
        frame = pd.read_csv(path, sep="|", dtype="string", usecols=[id_col, "SEXO", "FECHA_NACIMIENTO"])
        frame = frame.rename(columns={id_col: "id"})
        frame["id"] = frame["id"].str.strip()
        valid = valid_id(frame.id)
        frame["birth"] = parse_dates(frame.FECHA_NACIMIENTO)
        frame["sex"] = frame.SEXO.str.strip().str.upper().replace({"1": "HOMBRE", "2": "MUJER"})
        frame.loc[~frame.sex.isin(["HOMBRE", "MUJER"]), "sex"] = pd.NA
        grouped = frame.loc[valid].groupby("id", sort=False)
        profile = grouped.agg(birth=("birth", "first"), sex=("sex", "first"),
                              birth_values=("birth", "nunique"), sex_values=("sex", "nunique"))
        profile["ambiguous"] = (profile.birth_values > 1) | (profile.sex_values > 1)
        profiles[year] = profile
        annual.append(dict(year=year, identifier_column=id_col, records=len(frame),
                           missing_identifier=int((~valid).sum()), identifiers=len(profile),
                           ids_conflicting_birth_or_sex=int(profile.ambiguous.sum()),
                           records_invalid_birth=int(frame.birth.isna().sum())))
        sources.append(dict(year=year, path=str(path.relative_to(root)), bytes=path.stat().st_size,
                            mtime_ns=path.stat().st_mtime_ns, records=len(frame)))
        print(f"GRD {year}: {len(frame):,} registros auditados", flush=True)
    pairs = []
    for a, b in combinations(years, 2):
        shared = profiles[a].join(profiles[b], how="inner", lsuffix="_a", rsuffix="_b")
        eligible = (~shared.ambiguous_a & ~shared.ambiguous_b & shared.birth_a.notna()
                    & shared.birth_b.notna() & shared.sex_a.notna() & shared.sex_b.notna())
        agrees = eligible & (shared.birth_a == shared.birth_b) & (shared.sex_a == shared.sex_b)
        pairs.append(dict(year_a=a, year_b=b, shared_identifiers=len(shared),
                          pct_ids_a_shared=100 * len(shared) / len(profiles[a]) if len(profiles[a]) else None,
                          comparable_ids=int(eligible.sum()), agreeing_birth_and_sex=int(agrees.sum()),
                          pct_agreement=100 * agrees.sum() / eligible.sum() if eligible.sum() else None))
    pd.DataFrame(annual).to_csv(output / "grd_linkage_by_year.csv", index=False)
    pd.DataFrame(pairs).to_csv(output / "grd_linkage_between_years.csv", index=False)
    pd.DataFrame(sources).to_csv(output / "grd_source_inventory.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output_files/consolidacion"))
    parser.add_argument("--years", type=int, nargs="+", default=list(range(2019, 2025)))
    args = parser.parse_args()
    audit(data_root(), args.output, args.years)
