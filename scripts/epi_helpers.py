"""Reusable epidemiological calculations shared by `epi_rates.py` and the QMD reports.

Everything here works on aggregated tables (counts and populations); nothing
reads patient-level data. Conventions:

- Sex labels: ``HOMBRE``, ``MUJER`` and ``TOTAL``.
- Age groups: 17 five-year groups ``0-4`` … ``75-79`` and ``80+``.
- Rates are expressed per 100,000 person-years unless stated otherwise.
- Direct standardisation uses the WHO World Standard Population (Ahmad et al.
  2001, GPE Discussion Paper 31) collapsed to an open ``80+`` group.
- Confidence intervals: exact Poisson (chi-square) limits for counts and crude
  rates; gamma limits of Fay and Feuer (1997) for directly standardised rates;
  log-normal limits for ratios of standardised rates; Byar-type limits for
  standardised ratios.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AGE_GROUPS = [f"{i}-{i + 4}" for i in range(0, 80, 5)] + ["80+"]
WHO_STANDARD = {
    "0-4": 8860, "5-9": 8690, "10-14": 8600, "15-19": 8470, "20-24": 8220, "25-29": 7930,
    "30-34": 7610, "35-39": 7150, "40-44": 6590, "45-49": 6040, "50-54": 5370, "55-59": 4550,
    "60-64": 3720, "65-69": 2960, "70-74": 2210, "75-79": 1520, "80+": 1545,
}
# The published weights sum to 100,030 per 100,000 because of rounding; they are renormalised when applied.
REGION_NAMES = {
    15: "Arica y Parinacota", 1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 13: "Metropolitana", 6: "O'Higgins", 7: "Maule", 16: "Ñuble", 8: "Biobío",
    9: "La Araucanía", 14: "Los Ríos", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
}
REGION_ORDER = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]
# Names used in GRD that differ from the INE projections after normalisation.
COMUNA_ALIASES = {"COIHAIQUE": "COYHAIQUE", "CON CON": "CONCON", "AISEN": "AYSEN", "AYSEN": "AYSEN",
                  "MARCHIGUE": "MARCHIHUE", "PAIHUANO": "PAIGUANO"}
# Non-continental comunas kept out of contiguity-based spatial statistics.
NON_CONTINENTAL = {5201: "Isla de Pascua", 5104: "Juan Fernández", 12202: "Antártica", 12201: "Cabo de Hornos"}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(value: object) -> str:
    if pd.isna(value):
        return ""
    text = strip_accents(str(value)).upper().replace("'", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", text)).strip()
    return COMUNA_ALIASES.get(text, text)


def age_group_from_age(age: pd.Series) -> pd.Series:
    bins = list(range(0, 85, 5)) + [np.inf]
    return pd.cut(age, bins=bins, right=False, labels=AGE_GROUPS).astype("object")


def load_population(path: Path, years: list[int]) -> pd.DataFrame:
    """INE 2017-census-based projections by comuna, single age (80 = 80+) and sex."""
    pop = pd.read_parquet(path)
    pop = pop.rename(columns={"año": "year", "población": "population", "género": "sex", "edad": "age"})
    pop = pop.loc[pop.year.isin(years)].copy()
    pop["year"] = pop.year.astype(int)
    pop["cut_comuna"] = pop.cut_comuna.astype(int)
    pop["cut_region"] = pop.cut_region.astype(int)
    pop["sex"] = pop.sex.map({"masculino": "HOMBRE", "femenino": "MUJER"})
    pop["age_group"] = age_group_from_age(pop.age)
    grouped = pop.groupby(["year", "cut_region", "region", "cut_comuna", "comuna", "sex", "age_group"],
                          observed=True).population.sum().reset_index()
    grouped["comuna_norm"] = grouped.comuna.map(normalize_name)
    return grouped


def comuna_catalogue(population: pd.DataFrame) -> pd.DataFrame:
    cat = population.drop_duplicates("cut_comuna")[["cut_comuna", "comuna", "comuna_norm", "cut_region", "region"]].copy()
    cat["region_short"] = cat.cut_region.map(REGION_NAMES)
    cat["continental"] = ~cat.cut_comuna.isin(NON_CONTINENTAL)
    return cat.sort_values("cut_comuna").reset_index(drop=True)


def poisson_limits(count, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Exact (chi-square) limits for a Poisson count; vectorised."""
    count = np.asarray(count, dtype=float)
    lower = np.where(count > 0, stats.chi2.ppf(alpha / 2, 2 * np.maximum(count, 1e-12)) / 2, 0.0)
    upper = stats.chi2.ppf(1 - alpha / 2, 2 * count + 2) / 2
    return lower, upper


def crude_rate(count, population, per: float = 1e5, alpha: float = 0.05) -> pd.DataFrame:
    count = np.asarray(count, dtype=float)
    population = np.asarray(population, dtype=float)
    lower, upper = poisson_limits(count, alpha)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = np.where(population > 0, per * count / population, np.nan)
        lo = np.where(population > 0, per * lower / population, np.nan)
        hi = np.where(population > 0, per * upper / population, np.nan)
    return pd.DataFrame({"rate": rate, "rate_lo": lo, "rate_hi": hi})


def direct_standardization(frame: pd.DataFrame, count: str = "count", population: str = "population",
                           age: str = "age_group", standard: dict = WHO_STANDARD, per: float = 1e5,
                           alpha: float = 0.05) -> dict:
    """Directly standardised rate with Fay–Feuer gamma limits.

    `frame` holds one row per age group. Groups absent from the frame or with
    zero population have no denominator: they are dropped, flagged in
    `groups_missing`, and the remaining standard weights are renormalised.
    Callers should therefore supply the complete population grid with zero
    counts (see `epi_rates.attach_population`).
    """
    table = frame[[age, count, population]].copy()
    table = table.groupby(age, observed=True)[[count, population]].sum().reindex(list(standard))
    groups_missing = int(table[count].isna().sum())
    table[count] = table[count].fillna(0.0)
    table = table.loc[table[population] > 0]
    if table.empty:
        return dict(asr=np.nan, asr_lo=np.nan, asr_hi=np.nan, asr_var=np.nan, groups_missing=groups_missing)
    weights = np.array([standard[g] for g in table.index], dtype=float)
    weights = weights / weights.sum()
    rates = table[count].to_numpy() / table[population].to_numpy()
    asr = float(np.sum(weights * rates))
    variance = float(np.sum(weights ** 2 * table[count].to_numpy() / table[population].to_numpy() ** 2))
    w_max = float(np.max(weights / table[population].to_numpy()))
    if asr > 0 and variance > 0:
        lower = stats.gamma.ppf(alpha / 2, a=asr ** 2 / variance, scale=variance / asr)
        shape = (asr + w_max) ** 2 / (variance + w_max ** 2)
        upper = stats.gamma.ppf(1 - alpha / 2, a=shape, scale=(variance + w_max ** 2) / (asr + w_max))
    else:
        lower = 0.0
        upper = stats.gamma.ppf(1 - alpha / 2, a=1.0, scale=w_max) if w_max > 0 else np.nan
    return dict(asr=per * asr, asr_lo=per * lower, asr_hi=per * upper, asr_var=per ** 2 * variance,
                groups_missing=groups_missing)


def summarise_rates(frame: pd.DataFrame, keys: list[str], count: str = "count", population: str = "population",
                    age: str = "age_group", per: float = 1e5, alpha: float = 0.05) -> pd.DataFrame:
    """Crude and standardised rates for every combination of `keys`."""
    rows = []
    for values, group in frame.groupby(keys, dropna=False, observed=True):
        values = values if isinstance(values, tuple) else (values,)
        total_count = float(group[count].sum())
        total_pop = float(group[population].sum())
        crude = crude_rate([total_count], [total_pop], per, alpha).iloc[0]
        row = dict(zip(keys, values))
        row.update({"count": total_count, "population": total_pop, "crude": crude.rate,
                    "crude_lo": crude.rate_lo, "crude_hi": crude.rate_hi})
        row.update(direct_standardization(group, count, population, age, per=per, alpha=alpha))
        rows.append(row)
    return pd.DataFrame(rows)


def rate_ratio(rate1, var1, rate2, var2, alpha: float = 0.05) -> tuple[float, float, float]:
    """Ratio of two independent standardised rates with log-normal limits."""
    if not (rate1 > 0 and rate2 > 0):
        return np.nan, np.nan, np.nan
    ratio = rate1 / rate2
    se = np.sqrt(var1 / rate1 ** 2 + var2 / rate2 ** 2)
    z = stats.norm.ppf(1 - alpha / 2)
    return ratio, ratio * np.exp(-z * se), ratio * np.exp(z * se)


def count_ratio(count1, count2, alpha: float = 0.05) -> tuple[float, float, float]:
    """Ratio of two Poisson counts (same population basis) with exact binomial limits."""
    if count2 <= 0 or count1 < 0:
        return np.nan, np.nan, np.nan
    n = count1 + count2
    lo_p, hi_p = stats.beta.ppf(alpha / 2, count1, count2 + 1), stats.beta.ppf(1 - alpha / 2, count1 + 1, count2)
    lo_p = 0.0 if count1 == 0 else lo_p
    hi_p = 1.0 if count2 == 0 else hi_p
    return count1 / count2, lo_p / (1 - lo_p), (hi_p / (1 - hi_p) if hi_p < 1 else np.inf)


def expected_counts(frame: pd.DataFrame, reference: pd.DataFrame, keys: list[str], strata: list[str],
                    count: str = "count", population: str = "population") -> pd.DataFrame:
    """Indirect standardisation: expected counts from reference stratum-specific rates."""
    ref = reference.groupby(strata, observed=True)[[count, population]].sum()
    ref_rate = (ref[count] / ref[population]).rename("ref_rate").reset_index()
    merged = frame.merge(ref_rate, how="left", on=strata)
    merged["expected"] = merged[population] * merged.ref_rate.fillna(0.0)
    return merged.groupby(keys, observed=True).agg(observed=(count, "sum"), expected=("expected", "sum"),
                                                   population=(population, "sum")).reset_index()


def standardized_ratio(observed, expected, alpha: float = 0.05) -> pd.DataFrame:
    observed = np.asarray(observed, dtype=float)
    expected = np.asarray(expected, dtype=float)
    lower, upper = poisson_limits(observed, alpha)
    with np.errstate(divide="ignore", invalid="ignore"):
        sir = np.where(expected > 0, observed / expected, np.nan)
        lo = np.where(expected > 0, lower / expected, np.nan)
        hi = np.where(expected > 0, upper / expected, np.nan)
    return pd.DataFrame({"sir": sir, "sir_lo": lo, "sir_hi": hi})


def empirical_bayes_ratio(observed, expected) -> pd.DataFrame:
    """Global empirical Bayes shrinkage of standardised ratios (Poisson–gamma, method of moments).

    Follows Marshall (1991): the prior mean and variance of the area-specific
    ratios are estimated from the data and each ratio is shrunk towards the
    global ratio with weight expected_i / (expected_i + mean / variance).
    """
    observed = np.asarray(observed, dtype=float)
    expected = np.asarray(expected, dtype=float)
    valid = expected > 0
    ratios = np.where(valid, observed / np.where(valid, expected, 1.0), np.nan)
    e_sum = expected[valid].sum()
    mean = observed[valid].sum() / e_sum
    variance = np.sum(expected[valid] * (ratios[valid] - mean) ** 2) / e_sum - mean / (e_sum / valid.sum())
    variance = max(float(variance), 0.0)
    if variance == 0:
        shrink = np.zeros_like(expected)
    else:
        shrink = np.where(valid, expected / (expected + mean / variance), 0.0)
    smoothed = np.where(valid, shrink * ratios + (1 - shrink) * mean, np.nan)
    return pd.DataFrame({"sir_eb": smoothed, "eb_weight": shrink, "prior_mean": mean, "prior_variance": variance})


def annual_percent_change(frame: pd.DataFrame, year: str = "year", count: str = "count",
                          population: str = "population", alpha: float = 0.05) -> dict:
    """Average annual percent change from a log-linear quasi-Poisson model with population offset."""
    import statsmodels.api as sm
    data = frame.groupby(year, observed=True)[[count, population]].sum().reset_index()
    data = data.loc[(data[population] > 0)]
    if len(data) < 3 or data[count].sum() == 0:
        return dict(apc=np.nan, apc_lo=np.nan, apc_hi=np.nan, p_value=np.nan, years=len(data), dispersion=np.nan)
    x = sm.add_constant((data[year] - data[year].min()).astype(float))
    model = sm.GLM(data[count].astype(float), x, family=sm.families.Poisson(), offset=np.log(data[population].astype(float)))
    fit = model.fit(scale="X2") if len(data) > 2 else model.fit()
    beta = float(fit.params.iloc[1])
    se = float(fit.bse.iloc[1])
    z = stats.norm.ppf(1 - alpha / 2)
    return dict(apc=100 * (np.exp(beta) - 1), apc_lo=100 * (np.exp(beta - z * se) - 1),
                apc_hi=100 * (np.exp(beta + z * se) - 1), p_value=float(fit.pvalues.iloc[1]), years=len(data),
                dispersion=float(fit.scale))


def seasonal_index(frame: pd.DataFrame, year: str = "year", month: str = "month", count: str = "count") -> pd.DataFrame:
    """Ratio of each month's average to the overall monthly average, with a two-sided exact test."""
    table = frame.groupby([year, month], observed=True)[count].sum().reset_index()
    monthly = table.groupby(month)[count].agg(["sum", "size"]).reset_index()
    monthly["mean"] = monthly["sum"] / monthly["size"]
    grand_mean = monthly["mean"].mean()
    monthly["index"] = monthly["mean"] / grand_mean
    return monthly.rename(columns={"sum": "total", "size": "years"})


def chi_square_trend(counts: list[float], populations: list[float]) -> float:
    """Cochran–Armitage style score test for linear trend in rates across ordered groups."""
    counts = np.asarray(counts, dtype=float)
    populations = np.asarray(populations, dtype=float)
    scores = np.arange(len(counts), dtype=float)
    total_c, total_p = counts.sum(), populations.sum()
    if total_c == 0 or total_p == 0:
        return np.nan
    p = total_c / total_p
    numerator = np.sum(scores * (counts - populations * p))
    denominator = p * (1 - p) * (np.sum(populations * scores ** 2) - np.sum(populations * scores) ** 2 / total_p)
    if denominator <= 0:
        return np.nan
    statistic = numerator ** 2 / denominator
    return float(stats.chi2.sf(statistic, 1))
