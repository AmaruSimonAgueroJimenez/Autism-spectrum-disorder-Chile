"""Exploratory hospital diagnostic histories; outputs contain aggregates only.

Identifier eras are deliberately separate. The 2021–2024 linkage is empirical,
not a certification by the data producer. No matching by demographics is used.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import pandas as pd
from audit_grd_linkage import data_root, parse_dates, valid_id

DIAGS = [f"DIAGNOSTICO{i}" for i in range(1, 36)]
DEFINITIONS = {
    "autismo_F840": {"F840"},
    "TEA_operacional": {"F840", "F841", "F845", "F848", "F849"},
    "F84_historico": {"F84", "F840", "F841", "F842", "F843", "F844", "F845", "F848", "F849"},
}
ERAS = {"2019-2020": [2019, 2020], "2021-2024": [2021, 2022, 2023, 2024]}


def normalize_icd(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[.\s]", "", str(value).upper())


def antecedent_group(code: str) -> str | None:
    prefix = code[:3]
    if prefix in {"F80", "F81", "F82", "F83", "F88", "F89"}:
        return "Lenguaje_aprendizaje_desarrollo"
    if prefix == "F90":
        return "Hiperactividad_atencion"
    if prefix in {f"F{i}" for i in range(70, 80)}:
        return "Discapacidad_intelectual"
    if prefix in {"F91", "F92", "F93", "F94", "F95", "F98"}:
        return "Conducta_emociones_infancia"
    if prefix in {f"F{i}" for i in range(20, 30)}:
        return "Psicosis"
    if prefix in {f"F{i}" for i in range(30, 49)}:
        return "Animo_ansiedad_estres"
    if prefix in {"G40", "G41"}:
        return "Epilepsia"
    if prefix in {"H90", "H91"}:
        return "Audicion"
    if prefix in {"R62", "R47", "R48"}:
        return "Signos_desarrollo_habla"
    return None


def role(row: pd.Series, codes: set[str]) -> str:
    principal = row["DIAGNOSTICO1"] in codes
    secondary = any(row[c] in codes for c in DIAGS[1:])
    if principal and secondary:
        return "principal_y_secundario"
    if principal:
        return "principal"
    if secondary:
        return "solo_secundario"
    return "sin_codigo"


def histories_for_era(root: Path, years: list[int]) -> tuple[pd.DataFrame, dict]:
    ids: set[str] = set()
    no_id_records = 0
    for year in years:
        path = root / "GRD" / f"GRD_PUBLICO_{year}.csv"
        id_col = "ID_BENEFICIARIO" if year == 2024 else "CIP_ENCRIPTADO"
        for chunk in pd.read_csv(path, sep="|", dtype="string", usecols=[id_col] + DIAGS, chunksize=150000):
            # Broad prefilter only; exact normalized membership is checked below.
            mask = pd.Series(False, index=chunk.index)
            for column in DIAGS:
                mask |= chunk[column].str.match(r"(?i)^\s*F\.?84", na=False)
            subset = chunk.loc[mask].copy()
            subset[id_col] = subset[id_col].str.strip()
            for column in DIAGS:
                subset[column] = subset[column].map(normalize_icd)
            exact = subset[DIAGS].isin(DEFINITIONS["F84_historico"]).any(axis=1)
            subset = subset.loc[exact]
            good = valid_id(subset[id_col])
            ids.update(subset.loc[good, id_col])
            no_id_records += int((~good).sum())
        print(f"GRD {year}: selección F84 completada", flush=True)
    selected = []
    for year in years:
        path = root / "GRD" / f"GRD_PUBLICO_{year}.csv"
        id_col = "ID_BENEFICIARIO" if year == 2024 else "CIP_ENCRIPTADO"
        # Read every diagnosis and every encounter of the selected identifiers.
        # Full raw rows permit exact deduplication without collapsing different codes.
        for chunk in pd.read_csv(path, sep="|", dtype="string", chunksize=100000):
            chunk[id_col] = chunk[id_col].str.strip()
            subset = chunk.loc[chunk[id_col].isin(ids)].copy().rename(columns={id_col: "id"})
            subset["source_year"] = year
            selected.append(subset)
        print(f"GRD {year}: antecedentes recuperados", flush=True)
    data = pd.concat(selected, ignore_index=True)
    raw_columns = [c for c in data.columns if c != "source_year"]
    duplicates = int(data.duplicated(raw_columns).sum())
    data = data.drop_duplicates(raw_columns).copy()
    for column in DIAGS:
        data[column] = data[column].map(normalize_icd)
    data["birth"] = parse_dates(data.FECHA_NACIMIENTO)
    data["admission"] = parse_dates(data.FECHA_INGRESO)
    data["discharge"] = parse_dates(data.FECHAALTA)
    data["sex"] = data.SEXO.str.strip().str.upper().replace({"1": "HOMBRE", "2": "MUJER"})
    data.loc[~data.sex.isin(["HOMBRE", "MUJER"]), "sex"] = pd.NA
    data["valid_dates"] = data.admission.notna() & data.discharge.notna() & (data.discharge >= data.admission)
    duplicate_key = data.duplicated(["id", "COD_HOSPITAL", "admission", "discharge"], keep=False)
    profiles = data.groupby("id").agg(birth_values=("birth", "nunique"), sex_values=("sex", "nunique"),
                                      birth=("birth", "first"), sex=("sex", "first"))
    conflicted = profiles.index[(profiles.birth_values != 1) | (profiles.sex_values != 1)]
    bad_ids = set(conflicted) | set(data.loc[duplicate_key, "id"])
    data["link_eligible"] = ~data.id.isin(bad_ids)
    qc = dict(raw_F84_identifiers=len(ids), F84_records_missing_id=no_id_records,
              history_records=len(data), exact_duplicate_rows_removed=duplicates,
              ids_inconsistent_or_missing_birth_sex=len(conflicted),
              ids_ambiguous_encounter_key=data.loc[duplicate_key,"id"].nunique(),
              history_records_invalid_dates=int((~data.valid_dates).sum()))
    return data, qc


def summarize(data: pd.DataFrame, era: str, name: str, codes: set[str]) -> dict[str, pd.DataFrame]:
    data = data.copy()
    data["is_case"] = data[DIAGS].isin(codes).any(axis=1)
    data["role"] = data.apply(role, axis=1, codes=codes)
    cases = data.loc[data.is_case]
    annual = cases.groupby(["source_year", "role"]).agg(records=("id", "size"), identifiers=("id", "nunique")).reset_index()
    invalid_case_ids = set(cases.loc[~cases.valid_dates, "id"])
    eligible_ids = set(cases.loc[cases.link_eligible, "id"]) - invalid_case_ids
    history = data.loc[data.id.isin(eligible_ids) & data.valid_dates].copy()
    # Exclude implausible birth/age histories instead of silently imputing dates.
    birth_map = history.groupby("id").birth.first()
    history["birth"] = history.id.map(birth_map)
    bad_age = (history.admission < history.birth) | ((history.admission - history.birth).dt.days > 120*365.25)
    age_excluded = set(history.loc[bad_age, "id"])
    history = history.loc[~history.id.isin(age_excluded)]
    cohort, prior_codes, first_codes, last_codes, index_primary, sequences = [], [], [], [], [], []
    prior_groups, transitions = [], []
    end = pd.Timestamp(f"{ERAS[era][-1]}-12-31")
    start = pd.Timestamp(f"{ERAS[era][0]}-01-01")
    for patient, encounters in history.groupby("id", sort=False):
        autism = encounters.loc[encounters.is_case]
        if autism.empty:
            continue
        index_date = autism.discharge.min()
        index = autism.loc[autism.discharge == index_date]
        index_start = index.admission.min()
        index_roles = set(index.role)
        index_role = next(iter(index_roles)) if len(index_roles) == 1 else "mixto_mismo_dia"
        # A previous hospital discharge must precede the start of the index encounter.
        before = encounters.loc[encounters.discharge < index_start]
        concurrent = encounters.loc[(encounters.discharge >= index_start) & (encounters.discharge < index_date)]
        after = encounters.loc[encounters.admission > index_date]
        principal_after = after.loc[after.DIAGNOSTICO1.isin(codes)]
        groups_seen: set[str] = set()
        for window, antecedents in [("all", before), ("365d", before.loc[before.discharge >= index_start-pd.Timedelta(days=365)]),
                                     ("730d", before.loc[before.discharge >= index_start-pd.Timedelta(days=730)])]:
            for position, columns in [("principal", DIAGS[:1]), ("any", DIAGS)]:
                unique_codes = set(antecedents[columns].to_numpy().ravel()) - {""}
                for code in unique_codes:
                    prior_codes.append(dict(window=window, position=position, code=code, patients=1))
                unique_groups = {antecedent_group(c) for c in unique_codes} - {None}
                for group in unique_groups:
                    prior_groups.append(dict(window=window, position=position, group=group, patients=1))
                if window == "all" and position == "any":
                    groups_seen = unique_groups
        first_seen = encounters.loc[encounters.discharge == encounters.discharge.min()]
        for code in set(first_seen.DIAGNOSTICO1) - {""}:
            first_codes.append(dict(code=code, patients=1))
        if not before.empty:
            last = before.loc[before.discharge == before.discharge.max()]
            for code in set(last.DIAGNOSTICO1) - {""}:
                last_codes.append(dict(code=code, patients=1))
            if len(first_seen) == 1 and len(last) == 1:
                sequences.append(dict(first_principal=first_seen.DIAGNOSTICO1.iloc[0],
                                      last_prior_principal=last.DIAGNOSTICO1.iloc[0],
                                      index_role=index_role, patients=1))
        for code in set(index.DIAGNOSTICO1) - {""}:
            index_primary.append(dict(index_role=index_role, code=code, patients=1))
        sex = encounters.sex.dropna().iloc[0]
        birth = encounters.birth.dropna().iloc[0]
        age = (index_start - birth).days / 365.25
        to_principal = (principal_after.admission.min() - index_date).days if len(principal_after) else None
        cohort.append(dict(index_year=index_date.year, index_role=index_role, sex=sex, age=age,
                           age_band="0-4" if age < 5 else "5-9" if age < 10 else "10-14" if age < 15 else "15-19" if age < 20 else "20+",
                           prior_hospitalizations=len(before), prior_candidate_group=bool(groups_seen),
                           days_first_prior_to_index=(index_start-before.discharge.min()).days if len(before) else None,
                           lookback_available_days=max(0, (index_start-start).days),
                           observed_prior_365d=bool((before.discharge <= index_start-pd.Timedelta(days=365)).any()),
                           observed_prior_730d=bool((before.discharge <= index_start-pd.Timedelta(days=730)).any()),
                           index_ties=len(index), overlapping_prior_records=len(concurrent),
                           eligible_followup_365d=(end-index_date).days >= 365,
                           later_principal=to_principal is not None,
                           later_principal_365d=to_principal is not None and to_principal <= 365,
                           days_to_principal=to_principal))
    c = pd.DataFrame(cohort)
    def counted(rows: list[dict], columns: list[str]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=columns+["patients"])
        return pd.DataFrame(rows).groupby(columns, dropna=False).patients.sum().reset_index().sort_values("patients", ascending=False)
    if c.empty:
        empty = {"annual_positions": annual, "cohort_summary": pd.DataFrame([dict(patients=0)])}
        for frame in empty.values():
            frame.insert(0, "definition", name)
            frame.insert(0, "era", era)
        return empty
    n = len(c)
    summary = dict(patients=n, case_ids_before_qc=cases.id.nunique(),
                   case_ids_invalid_index_dates=len(invalid_case_ids), ids_implausible_age=len(age_excluded),
                   prior_hospitalization=int((c.prior_hospitalizations > 0).sum()),
                   prior_candidate_group=int(c.prior_candidate_group.sum()),
                   age_median=c.age.median(), age_q25=c.age.quantile(.25), age_q75=c.age.quantile(.75),
                   lookback_365d=int((c.lookback_available_days >= 365).sum()),
                   lookback_730d=int((c.lookback_available_days >= 730).sum()),
                   observed_prior_365d=int(c.observed_prior_365d.sum()),
                   observed_prior_730d=int(c.observed_prior_730d.sum()),
                   index_same_day_ties=int((c.index_ties > 1).sum()),
                   concurrent_prior_records=int(c.overlapping_prior_records.sum()),
                   days_first_prior_to_index_median=c.days_first_prior_to_index.dropna().median() if c.days_first_prior_to_index.notna().any() else None)
    for initial in sorted(c.index_role.unique()):
        subset = c.loc[c.index_role == initial]
        comparable = subset.loc[subset.eligible_followup_365d]
        transitions.append(dict(index_role=initial, patients=len(subset),
                                later_principal=int(subset.later_principal.sum()),
                                eligible_followup_365d=len(comparable),
                                later_principal_365d=int(comparable.later_principal_365d.sum()),
                                days_to_principal_median=subset.days_to_principal.dropna().median() if subset.days_to_principal.notna().any() else None))
    stratified = c.groupby(["index_year", "index_role", "sex", "age_band"]).agg(
        patients=("age", "size"), prior_hospitalization=("prior_hospitalizations", lambda s: int((s>0).sum())),
        prior_candidate_group=("prior_candidate_group", "sum"), age_median=("age", "median")).reset_index()
    results = dict(annual_positions=annual, cohort_summary=pd.DataFrame([summary]),
                   first_position=c.groupby("index_role").size().reset_index(name="patients"),
                   cohort_strata=stratified, previous_codes=counted(prior_codes, ["window", "position", "code"]),
                   previous_groups=counted(prior_groups, ["window", "position", "group"]),
                   first_hospital_principal=counted(first_codes, ["code"]),
                   last_prior_principal=counted(last_codes, ["code"]),
                   index_principal=counted(index_primary, ["index_role", "code"]),
                   sequences=counted(sequences, ["first_principal", "last_prior_principal", "index_role"]),
                   principal_transitions=pd.DataFrame(transitions))
    for key, frame in results.items():
        frame.insert(0, "definition", name)
        frame.insert(0, "era", era)
    return results


def run(root: Path, output: Path, eras: list[str]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    combined: dict[str, list[pd.DataFrame]] = {}
    quality = []
    for era in eras:
        history, qc = histories_for_era(root, ERAS[era])
        quality.append(dict(era=era, **qc))
        for name, codes in DEFINITIONS.items():
            results = summarize(history, era, name, codes)
            for key, frame in results.items():
                combined.setdefault(key, []).append(frame)
            print(f"GRD {era}: {name} analizado", flush=True)
    for key, frames in combined.items():
        pd.concat(frames, ignore_index=True).to_csv(output / f"grd_{key}.csv", index=False)
    pd.DataFrame(quality).to_csv(output / "grd_trajectory_quality.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output_files/consolidacion"))
    parser.add_argument("--eras", nargs="+", choices=list(ERAS), default=list(ERAS))
    args = parser.parse_args()
    run(data_root(), args.output, args.eras)
