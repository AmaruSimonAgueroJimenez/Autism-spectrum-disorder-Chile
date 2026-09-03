"""Rates, standardisation, trends and spatial statistics from the aggregated GRD and REM tables.

Inputs (all in `output_files/consolidacion/`): `grd_epi_*.csv` written by
`grd_epidemiology.py`, `rem_a05_age_sex.csv` and `rem_a05_region_age_sex.csv`
written by `audit_rem.py`, the INE population projections in `data/` and the
comuna shapefile in `data/`. Outputs are CSV tables with explicit units so the
QMD reports only format and plot them.

Denominators are person-years from the INE 2017-census-based projections.
Rates of hospital records are hospitalisation rates (episodes per 100,000
person-years); rates of persons are annual (or period) rates of distinct
identifiers hospitalised. Neither is incidence or prevalence of autism.
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from epi_helpers import (AGE_GROUPS, NON_CONTINENTAL, REGION_NAMES, annual_percent_change, comuna_catalogue,
                         count_ratio, empirical_bayes_ratio, expected_counts, load_population, normalize_name,
                         rate_ratio, standardized_ratio, summarise_rates)

ROOT = Path(__file__).resolve().parents[1]
YEARS = list(range(2019, 2025))
ERAS = {"2019-2020": [2019, 2020], "2021-2024": [2021, 2022, 2023, 2024]}
DEFINITIONS = ["autismo_F840", "TEA_operacional", "F84_historico"]
MAIN = "TEA_operacional"
SEED = 20260903


def read(output: Path, name: str, **kwargs) -> pd.DataFrame:
    return pd.read_csv(output / name, dtype={"code": str, "IdRegion": str, "IdComuna": str, "COD_HOSPITAL": str}, **kwargs)


def with_sex_total(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Append TOTAL rows (both sexes) so every summary carries HOMBRE, MUJER and TOTAL."""
    total = frame.groupby([k for k in keys if k != "sex"] + ["age_group"], observed=True, dropna=False)[["count", "population"]].sum().reset_index()
    total["sex"] = "TOTAL"
    return pd.concat([frame, total], ignore_index=True)


def attach_population(counts: pd.DataFrame, population: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Full outer join on the population grid so empty strata carry zero cases."""
    pop = population.groupby(keys + ["sex", "age_group"], observed=True).population.sum().reset_index()
    merged = pop.merge(counts, how="left", on=keys + ["sex", "age_group"])
    merged["count"] = merged["count"].fillna(0.0)
    return merged


def grd_rates(output: Path, population: pd.DataFrame, catalogue: pd.DataFrame) -> None:
    strata = read(output, "grd_epi_strata.csv")
    strata["comuna_norm"] = strata.comuna_norm.fillna("").map(normalize_name)
    strata = strata.merge(catalogue[["comuna_norm", "cut_comuna", "cut_region"]], how="left", on="comuna_norm")
    unmatched = strata.loc[strata.cut_comuna.isna()].groupby("comuna_norm").records.sum().reset_index()
    unmatched.to_csv(output / "grd_comuna_unmatched.csv", index=False)
    usable = strata.dropna(subset=["sex", "age_group"])
    excluded = strata.loc[strata.sex.isna() | strata.age_group.isna()].groupby(["year", "definition"]).records.sum()
    excluded.rename("records_without_sex_or_age").reset_index().to_csv(output / "grd_rates_excluded.csv", index=False)
    pop_nat = population.groupby(["year", "sex", "age_group"], observed=True).population.sum().reset_index()
    pop_reg = population.groupby(["year", "cut_region", "sex", "age_group"], observed=True).population.sum().reset_index()
    persons_year = read(output, "grd_epi_persons_year.csv").dropna(subset=["sex", "age_group"])
    persons_year["comuna_norm"] = persons_year.comuna_norm.fillna("").map(normalize_name)
    persons_year = persons_year.merge(catalogue[["comuna_norm", "cut_comuna", "cut_region"]], how="left", on="comuna_norm")

    # 1. National rates: records by role and persons, by sex and TOTAL.
    national = []
    rec = usable.groupby(["year", "definition", "role", "sex", "age_group"], observed=True).records.sum().reset_index()
    rec_any = rec.groupby(["year", "definition", "sex", "age_group"], observed=True).records.sum().reset_index().assign(role="cualquiera")
    rec = pd.concat([rec, rec_any], ignore_index=True).rename(columns={"records": "count"})
    for (definition, role), group in rec.groupby(["definition", "role"]):
        merged = attach_population(group.drop(columns=["definition", "role"]), population, ["year"])
        merged = with_sex_total(merged, ["year", "sex"])
        summary = summarise_rates(merged, ["year", "sex"])
        summary.insert(1, "definition", definition)
        summary.insert(2, "unit", "records")
        summary.insert(3, "role", role)
        national.append(summary)
    per = persons_year.groupby(["year", "definition", "sex", "age_group"], observed=True).persons.sum().reset_index().rename(columns={"persons": "count"})
    for definition, group in per.groupby("definition"):
        merged = attach_population(group.drop(columns=["definition"]), population, ["year"])
        merged = with_sex_total(merged, ["year", "sex"])
        summary = summarise_rates(merged, ["year", "sex"])
        summary.insert(1, "definition", definition)
        summary.insert(2, "unit", "persons")
        summary.insert(3, "role", "cualquiera")
        national.append(summary)
    national = pd.concat(national, ignore_index=True)
    national.to_csv(output / "grd_rates_national.csv", index=False)

    # 2. Age-specific rates (records any role and persons) by sex, year and age group.
    age_rows = []
    for definition in DEFINITIONS:
        for unit, source in [("records", rec_any.loc[rec_any.definition == definition].rename(columns={"records": "count"})),
                             ("persons", per.loc[per.definition == definition])]:
            merged = attach_population(source[["year", "sex", "age_group", "count"]], population, ["year"])
            merged = with_sex_total(merged, ["year", "sex"])
            from epi_helpers import crude_rate
            limits = crude_rate(merged["count"], merged.population)
            merged = pd.concat([merged.reset_index(drop=True), limits], axis=1)
            merged.insert(0, "unit", unit)
            merged.insert(0, "definition", definition)
            age_rows.append(merged)
    pd.concat(age_rows, ignore_index=True).to_csv(output / "grd_rates_age_specific.csv", index=False)

    # 3. Sex ratios of standardised rates and of counts.
    ratios = []
    for (definition, unit, role, year), group in national.groupby(["definition", "unit", "role", "year"]):
        men = group.loc[group.sex == "HOMBRE"].iloc[0]
        women = group.loc[group.sex == "MUJER"].iloc[0]
        rr = rate_ratio(men.asr, men.asr_var, women.asr, women.asr_var)
        cr = count_ratio(men["count"], women["count"])
        ratios.append(dict(definition=definition, unit=unit, role=role, year=year, count_men=men["count"],
                           count_women=women["count"], asr_men=men.asr, asr_women=women.asr,
                           asr_ratio=rr[0], asr_ratio_lo=rr[1], asr_ratio_hi=rr[2],
                           count_ratio=cr[0], count_ratio_lo=cr[1], count_ratio_hi=cr[2]))
    pd.DataFrame(ratios).to_csv(output / "grd_sex_ratio.csv", index=False)

    # 4. Trends: average annual percent change (quasi-Poisson, population offset).
    trends = []
    for (definition, unit, role, sex), group in national.groupby(["definition", "unit", "role", "sex"]):
        for label, years in [("2019-2024", YEARS), ("2021-2024", ERAS["2021-2024"])]:
            subset = group.loc[group.year.isin(years)]
            result = annual_percent_change(subset)
            trends.append(dict(definition=definition, unit=unit, role=role, sex=sex, period=label, **result))
    pd.DataFrame(trends).to_csv(output / "grd_trends_apc.csv", index=False)

    # 5. Subcode rates (records; a record counts once per subcode and position).
    sub = read(output, "grd_epi_subcodes.csv").dropna(subset=["sex", "age_group"])
    sub_any = sub.groupby(["year", "code", "sex", "age_group"], observed=True).records.sum().reset_index().assign(code_position="cualquiera")
    sub = pd.concat([sub, sub_any], ignore_index=True).rename(columns={"records": "count"})
    sub_rows = []
    for (code, position), group in sub.groupby(["code", "code_position"]):
        merged = attach_population(group[["year", "sex", "age_group", "count"]], population, ["year"])
        merged = with_sex_total(merged, ["year", "sex"])
        summary = summarise_rates(merged, ["year", "sex"])
        summary.insert(1, "code", code)
        summary.insert(2, "code_position", position)
        sub_rows.append(summary)
    pd.concat(sub_rows, ignore_index=True).to_csv(output / "grd_rates_subcodes.csv", index=False)

    # 6. Regional rates: annual and pooled, records (any role) and persons, by sex and TOTAL.
    regional = []
    rec_region = usable.loc[usable.definition == MAIN].groupby(["year", "cut_region", "sex", "age_group"], observed=True).records.sum().reset_index().rename(columns={"records": "count"})
    per_region = persons_year.loc[persons_year.definition == MAIN].groupby(["year", "cut_region", "sex", "age_group"], observed=True).persons.sum().reset_index().rename(columns={"persons": "count"})
    for unit, source in [("records", rec_region), ("persons", per_region)]:
        merged = attach_population(source.dropna(subset=["cut_region"]), population, ["year", "cut_region"])
        merged = with_sex_total(merged, ["year", "cut_region", "sex"])
        annual = summarise_rates(merged, ["year", "cut_region", "sex"]).assign(period=lambda d: d.year.astype(str))
        pooled = []
        for label, years in [("2019-2024", YEARS), ("2021-2024", ERAS["2021-2024"])]:
            pool = merged.loc[merged.year.isin(years)]
            pooled.append(summarise_rates(pool, ["cut_region", "sex"]).assign(period=label, year=np.nan))
        both = pd.concat([annual] + pooled, ignore_index=True)
        both.insert(0, "unit", unit)
        regional.append(both)
    regional = pd.concat(regional, ignore_index=True)
    regional["cut_region"] = regional.cut_region.astype(int)
    regional["region"] = regional.cut_region.map(REGION_NAMES)
    regional.to_csv(output / "grd_rates_regional.csv", index=False)
    # Records whose comuna could not be assigned to a region, for the coverage note.
    usable.loc[usable.definition == MAIN].assign(assigned=lambda d: d.cut_region.notna()).groupby(["year", "assigned"]).records.sum().reset_index().to_csv(output / "grd_rates_regional_coverage.csv", index=False)

    # 7. Comunal rates pooled 2019–2024 (records) and 2021–2024 (persons); indirect standardisation and EB shrinkage.
    comunal = []
    rec_com = usable.loc[usable.definition == MAIN].dropna(subset=["cut_comuna"]).groupby(["year", "cut_comuna", "sex", "age_group"], observed=True).records.sum().reset_index().rename(columns={"records": "count"})
    persons_era = read(output, "grd_epi_persons_era.csv").dropna(subset=["sex", "age_group"])
    persons_era["comuna_norm"] = persons_era.comuna_norm.fillna("").map(normalize_name)
    persons_era = persons_era.merge(catalogue[["comuna_norm", "cut_comuna"]], how="left", on="comuna_norm")
    per_com = persons_era.loc[(persons_era.definition == MAIN) & (persons_era.era == "2021-2024")].dropna(subset=["cut_comuna"]).groupby(["cut_comuna", "sex", "age_group"], observed=True).persons.sum().reset_index().rename(columns={"persons": "count"})
    for unit, source, years in [("records", rec_com, YEARS), ("persons", per_com, ERAS["2021-2024"])]:
        pop_years = population.loc[population.year.isin(years)]
        if unit == "records":
            merged = attach_population(source, pop_years, ["year", "cut_comuna"])
            merged = merged.groupby(["cut_comuna", "sex", "age_group"], observed=True)[["count", "population"]].sum().reset_index()
        else:
            # Persons over the period against the mean annual population (person-period denominator).
            mean_pop = pop_years.groupby(["cut_comuna", "sex", "age_group"], observed=True).population.sum().reset_index()
            mean_pop["population"] = mean_pop.population / len(years)
            merged = mean_pop.merge(source, how="left", on=["cut_comuna", "sex", "age_group"])
            merged["count"] = merged["count"].fillna(0.0)
        total = merged.groupby(["cut_comuna", "age_group"], observed=True)[["count", "population"]].sum().reset_index().assign(sex="TOTAL")
        both = pd.concat([merged, total], ignore_index=True)
        summary = summarise_rates(both.loc[both.sex == "TOTAL"], ["cut_comuna"])
        expected = expected_counts(merged, merged, ["cut_comuna"], ["sex", "age_group"])
        summary = summary.merge(expected[["cut_comuna", "expected"]], on="cut_comuna")
        summary = pd.concat([summary, standardized_ratio(summary["count"], summary.expected)], axis=1)
        summary = pd.concat([summary, empirical_bayes_ratio(summary["count"], summary.expected)], axis=1)
        summary.insert(0, "unit", unit)
        summary.insert(1, "period", f"{years[0]}-{years[-1]}")
        comunal.append(summary)
    comunal = pd.concat(comunal, ignore_index=True)
    comunal["cut_comuna"] = comunal.cut_comuna.astype(int)
    comunal = comunal.merge(catalogue[["cut_comuna", "comuna", "cut_region", "region_short", "continental"]], how="left", on="cut_comuna")
    comunal.to_csv(output / "grd_rates_comunal.csv", index=False)


def spatial(output: Path, shapefile: Path, catalogue: pd.DataFrame) -> None:
    import geopandas as gpd
    from esda import fdr
    from esda.moran import Moran, Moran_Local
    from libpysal.weights import Queen

    comunal = pd.read_csv(output / "grd_rates_comunal.csv")
    shapes = gpd.read_file(shapefile)
    shapes = shapes.loc[shapes.cod_comuna > 0, ["cod_comuna", "Comuna", "codregion", "geometry"]].rename(columns={"cod_comuna": "cut_comuna"})
    shapes = shapes.loc[~shapes.cut_comuna.isin(NON_CONTINENTAL)].reset_index(drop=True)
    moran_rows, lisa_frames = [], []
    for (unit, period), table in comunal.groupby(["unit", "period"]):
        gdf = shapes.merge(table, how="left", on="cut_comuna")
        gdf["count"] = gdf["count"].fillna(0.0)
        gdf["sir_eb"] = gdf.sir_eb.fillna(gdf.prior_mean.dropna().iloc[0] if gdf.prior_mean.notna().any() else 1.0)
        gdf["asr"] = gdf.asr.fillna(0.0)
        gdf["sir"] = gdf.sir.fillna(0.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            weights = Queen.from_dataframe(gdf, use_index=False)
        weights.transform = "r"
        islands = list(weights.islands)
        for variable in ["asr", "sir", "sir_eb"]:
            values = gdf[variable].to_numpy(dtype=float)
            if np.nanvar(values) == 0:
                continue
            np.random.seed(SEED)
            moran = Moran(values, weights, permutations=999)
            moran_rows.append(dict(unit=unit, period=period, variable=variable, n_comunas=len(gdf), islands=len(islands),
                                   moran_i=moran.I, expected_i=moran.EI, z_norm=moran.z_norm, p_norm=moran.p_norm,
                                   z_sim=moran.z_sim, p_sim=moran.p_sim, permutations=999))
            np.random.seed(SEED)
            local = Moran_Local(values, weights, permutations=999, seed=SEED)
            threshold = fdr(local.p_sim, 0.05)
            frame = pd.DataFrame({"unit": unit, "period": period, "variable": variable,
                                  "cut_comuna": gdf.cut_comuna, "comuna": gdf.Comuna, "codregion": gdf.codregion,
                                  "value": values, "spatial_lag": weights.sparse @ values, "local_i": local.Is,
                                  "quadrant": local.q, "p_sim": local.p_sim, "fdr_threshold": threshold,
                                  "island": gdf.index.isin(islands)})
            labels = {1: "Alto-Alto", 2: "Bajo-Alto", 3: "Bajo-Bajo", 4: "Alto-Bajo"}
            frame["cluster_p05"] = np.where(frame.p_sim < 0.05, frame.quadrant.map(labels), "No significativo")
            frame["cluster_fdr"] = np.where(frame.p_sim <= threshold, frame.quadrant.map(labels), "No significativo")
            lisa_frames.append(frame)
    pd.DataFrame(moran_rows).to_csv(output / "grd_spatial_moran.csv", index=False)
    pd.concat(lisa_frames, ignore_index=True).to_csv(output / "grd_spatial_lisa.csv", index=False)


def rem_rates(output: Path, population: pd.DataFrame) -> None:
    """Age-standardised rates of REM A05 admissions (ingresos) per 100,000 population, national and regional."""
    ages = read(output, "rem_a05_age_sex.csv")
    ages["sex"] = ages.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    regional = read(output, "rem_a05_region_age_sex.csv")
    regional["sex"] = regional.sex.map({"Hombres": "HOMBRE", "Mujeres": "MUJER"})
    regional["cut_region"] = pd.to_numeric(regional.IdRegion, errors="coerce")
    groups = {"05990022": ["05990022"], "06902600": ["06902600"],
              "A05_ingresos_TGD_total": ["05990022", "05990023", "05990024", "05990025", "05990026"],
              "A05_egresos_TGD_total": ["05990027", "05990028", "05990029", "05990030", "05990031"],
              "05990027": ["05990027"], "05225000": ["05225000"]}
    rows, age_rows, reg_rows = [], [], []
    for label, codes in groups.items():
        source = ages.loc[ages.code.isin(codes)].groupby(["year", "sex", "age_group"], observed=True)["count"].sum().reset_index()
        source = source.loc[source.year.isin(population.year.unique())]
        if source.empty:
            continue
        merged = attach_population(source, population.loc[population.year.isin(source.year.unique())], ["year"])
        merged = with_sex_total(merged, ["year", "sex"])
        summary = summarise_rates(merged, ["year", "sex"])
        summary.insert(1, "series", label)
        rows.append(summary)
        from epi_helpers import crude_rate
        limits = crude_rate(merged["count"], merged.population)
        specific = pd.concat([merged.reset_index(drop=True), limits], axis=1)
        specific.insert(0, "series", label)
        age_rows.append(specific)
        reg = regional.loc[regional.code.isin(codes)].dropna(subset=["cut_region"]).groupby(["year", "cut_region", "sex", "age_group"], observed=True)["count"].sum().reset_index()
        reg = reg.loc[reg.year.isin(population.year.unique())]
        if reg.empty:
            continue
        merged_reg = attach_population(reg, population.loc[population.year.isin(reg.year.unique())], ["year", "cut_region"])
        merged_reg = with_sex_total(merged_reg, ["year", "cut_region", "sex"])
        annual = summarise_rates(merged_reg, ["year", "cut_region", "sex"]).assign(period=lambda d: d.year.astype(str))
        pooled = summarise_rates(merged_reg.loc[merged_reg.year >= 2021], ["cut_region", "sex"]).assign(period="2021-2024", year=np.nan)
        both = pd.concat([annual, pooled], ignore_index=True)
        both.insert(0, "series", label)
        reg_rows.append(both)
    pd.concat(rows, ignore_index=True).to_csv(output / "rem_rates_national.csv", index=False)
    pd.concat(age_rows, ignore_index=True).to_csv(output / "rem_rates_age_specific.csv", index=False)
    regional_out = pd.concat(reg_rows, ignore_index=True)
    regional_out["cut_region"] = regional_out.cut_region.astype(int)
    regional_out["region"] = regional_out.cut_region.map(REGION_NAMES)
    regional_out.to_csv(output / "rem_rates_regional.csv", index=False)


def ecological(output: Path) -> None:
    """Region-year panel joining REM admission rates and GRD hospitalisation rates (2021–2024)."""
    rem = pd.read_csv(output / "rem_rates_regional.csv")
    grd = pd.read_csv(output / "grd_rates_regional.csv")
    rem = rem.loc[(rem.series == "05990022") & (rem.sex == "TOTAL") & rem.year.notna(), ["year", "cut_region", "region", "count", "crude", "asr"]]
    rem = rem.rename(columns={"count": "rem_ingresos", "crude": "rem_crude", "asr": "rem_asr"})
    parts = [rem]
    for unit in ["records", "persons"]:
        sub = grd.loc[(grd.unit == unit) & (grd.sex == "TOTAL") & grd.year.notna(), ["year", "cut_region", "count", "crude", "asr"]]
        parts.append(sub.rename(columns={"count": f"grd_{unit}", "crude": f"grd_{unit}_crude", "asr": f"grd_{unit}_asr"}))
    panel = parts[0]
    for part in parts[1:]:
        panel = panel.merge(part, how="inner", on=["year", "cut_region"])
    panel = panel.loc[panel.year >= 2021]
    panel.to_csv(output / "rem_grd_ecological.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output_files" / "consolidacion")
    parser.add_argument("--population", type=Path, default=ROOT / "data" / "censo_proyecciones_ano_edad_genero.parquet")
    parser.add_argument("--shapefile", type=Path, default=ROOT / "data" / "comunas.shp")
    parser.add_argument("--skip-spatial", action="store_true")
    args = parser.parse_args()
    population = load_population(args.population, list(range(2017, 2025)))
    catalogue = comuna_catalogue(population)
    catalogue.to_csv(args.output / "catalogo_comunas.csv", index=False)
    population.groupby(["year", "cut_region", "sex", "age_group"], observed=True).population.sum().reset_index().to_csv(
        args.output / "population_regional.csv", index=False)
    young = pd.read_parquet(args.population).rename(columns={"año": "year", "población": "population", "edad": "age"})
    young = young.loc[(young.age <= 5) & young.year.between(2017, 2024)]
    young.groupby(["year", "cut_region", "age"]).population.sum().reset_index().astype({"year": int, "cut_region": int, "age": int}).to_csv(
        args.output / "population_regional_young.csv", index=False)
    grd_rates(args.output, population.loc[population.year.isin(YEARS)], catalogue)
    print("GRD: tasas nacionales, regionales y comunales calculadas", flush=True)
    rem_rates(args.output, population)
    print("REM: tasas de ingresos A05 calculadas", flush=True)
    ecological(args.output)
    if not args.skip_spatial:
        spatial(args.output, args.shapefile, catalogue)
        print("Espacial: Moran global y LISA calculados", flush=True)


if __name__ == "__main__":
    main()
