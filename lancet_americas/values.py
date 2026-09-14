# -*- coding: utf-8 -*-
"""values.py — cantidades citadas por el manuscrito Lancet (una tabla plana por variante).

`values(variant)` lee las tablas tidy (`outputs/tidy/`), los modelos (`models_summary.csv`,
`models_population_rates.csv`, `models_a05_standardised_rates.csv`, `models_convergence_index.csv`,
`hospital_effects.csv`), los controles (`outputs/controls/`) y la procedencia, y devuelve un diccionario
PLANO {clave: número | texto | None} con cada cantidad que la prosa, el resumen, las leyendas o el
suplemento pueden citar. Los valores son crudos (sin formato): la prosa decide decimales e idioma.

Convenciones de clave
---------------------
* prefijo por fuente: grd_, deis_, a03_/a05_/a27_/a28_/p2_/p6_ (REM), ine_/fonasa_/isapre_/aps_/rem20_,
  svy_ (encuestas), pie_/sinaces_/special_/junaeb_ (educación), apc_ (modelos con alias),
  mdl__<model_id>__<campo> (todos los modelos), conv_ (índices), controls_, prov_, src_ (rutas fuente).
* sufijo de año `_YYYY`; sexo `_male`/`_female`/`_total`; edades `0_4` … `80plus`.
* «any» = F84 en cualquier posición diagnóstica; «principal» = F84 principal; «secondary_only» = solo secundario.
* Los conteos son reconocimiento administrativo (episodios, ingresos, intervenciones, stocks, matrícula),
  nunca prevalencia ni incidencia; ninguna clave enlaza personas entre fuentes ni estima efectos de la Ley 21.545.

Uso: `python values.py` escribe outputs/values_con_rett.json, outputs/values_sin_rett.json y
outputs/values_diff_variants.json. `python values.py --variant sin_rett` escribe solo una variante.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config as CFG  # noqa: E402
from common import atomic_write_json  # noqa: E402

TIDY = CFG.TIDY
OUT = CFG.OUT
CONTROLS_DIR = OUT / "controls"  # CFG.CONTROLS es el diccionario de valores esperados
YEARS_GRD = list(CFG.YEARS_GRD)
YEARS_REM = list(CFG.YEARS_REM)
VARIANTS = ["con_rett", "sin_rett"]

SEX = {"HOMBRE": "male", "MUJER": "female", "TOTAL": "total", "Hombres": "male", "Mujeres": "female", "Hombre": "male",
       "Mujer": "female", "male": "male", "female": "female", "all": "all", "total": "total", "unknown": "unknown",
       "M:F": "mf"}
A05_CATS = {"autism": "autism", "asperger": "asperger", "rett": "rett", "disintegrative": "disintegrative", "pdd_nos": "pdd_nos"}


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def _isnan(x) -> bool:
    try:
        return x is None or (isinstance(x, float) and math.isnan(x)) or (not isinstance(x, str) and pd.isna(x))
    except (TypeError, ValueError):
        return False


def _int(x):
    if _isnan(x):
        return None
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isfinite(f) and abs(f - round(f)) < 1e-9:
        return int(round(f))
    return f


def _flt(x):
    if _isnan(x):
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _str(x):
    return None if _isnan(x) else str(x)


def _bool(x):
    return None if _isnan(x) else bool(x)


def _age(a) -> str:
    return str(a).replace("-", "_").replace("+", "plus").replace("<", "lt").replace(" ", "")


def _slug(s) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    return s.strip("_")


def _ratio(a, b):
    a, b = _flt(a), _flt(b)
    return None if a is None or b in (None, 0) else a / b


def _pct_change(new, old):
    r = _ratio(new, old)
    return None if r is None else 100.0 * (r - 1.0)


def _tidy(name: str, **kw) -> pd.DataFrame:
    path = TIDY / (name if name.endswith(".csv") else f"{name}.csv")
    if not path.is_file():
        raise FileNotFoundError(f"Falta {path}; ejecute el módulo del pipeline que lo produce.")
    return pd.read_csv(path, **kw)


def _one(df: pd.DataFrame, **cond):
    m = pd.Series(True, index=df.index)
    for k, v in cond.items():
        m &= df[k] == v
    sub = df[m]
    if len(sub) == 0:
        return None
    if len(sub) > 1:
        raise ValueError(f"Selección ambigua ({len(sub)} filas) para {cond}")
    return sub.iloc[0]


# ---------------------------------------------------------------------------
# GRD (módulo 01) + poblacionales (06) + efectos por hospital (06)
# ---------------------------------------------------------------------------
def _grd(V: dict, variant: str) -> None:
    g = _tidy("grd_year_summary")
    other = "sin_rett" if variant == "con_rett" else "con_rett"
    V["src_grd"] = "outputs/tidy/grd_year_summary.csv"

    def row(var, panel, act, pos, y):
        return _one(g, variant=var, panel=panel, activity=act, position=pos, year=y)

    combos = []
    for panel, ptag in (("observed", ""), ("fixed65", "_fixed65")):
        for act, atag in (("all", ""), ("hospitalisation", "_hosp"), ("cma", "_cma"), ("other", "_other")):
            combos.append(("any", "any", panel, ptag, act, atag))
            if act in ("all", "hospitalisation"):
                combos.append(("principal", "principal", panel, ptag, act, atag))
            if act == "all":
                combos.append(("secondary_only", "secondary_only", panel, ptag, act, atag))
                if panel == "observed":
                    combos.append(("principal_and_secondary", "principal_and_secondary", panel, ptag, act, atag))

    for y in YEARS_GRD:
        base = row(variant, "observed", "all", "any", y)
        V[f"grd_records_total_{y}"] = _int(base.n_episodes_total_same_panel_activity)
        V[f"grd_hospitals_observed_{y}"] = _int(base.hospitals_n)
        V[f"grd_hospitals_fixed65_{y}"] = 65
        V[f"grd_identifier_column_{y}"] = _str(base.identifier_column)
        V[f"grd_coding_depth_all_mean_{y}"] = _flt(base.coding_depth_mean_all)
        V[f"grd_coding_depth_all_median_{y}"] = _flt(base.coding_depth_median_all)
        V[f"grd_coding_depth_f84_mean_{y}"] = _flt(base.coding_depth_mean_f84)
        V[f"grd_coding_depth_f84_median_{y}"] = _flt(base.coding_depth_median_f84)
        fixed = row(variant, "fixed65", "all", "any", y)
        V[f"grd_records_fixed65_{y}"] = _int(fixed.n_episodes_total_same_panel_activity)
        V[f"grd_coding_depth_all_mean_fixed65_{y}"] = _flt(fixed.coding_depth_mean_all)
        hosp = row(variant, "observed", "hospitalisation", "any", y)
        V[f"grd_coding_depth_all_mean_hosp_{y}"] = _flt(hosp.coding_depth_mean_all)
        V[f"grd_coding_depth_f84_mean_hosp_{y}"] = _flt(hosp.coding_depth_mean_f84)
        for act, atag in (("hospitalisation", "hosp"), ("cma", "cma"), ("other", "other")):
            r = row(variant, "observed", act, "any", y)
            V[f"grd_records_{atag}_{y}"] = None if r is None else _int(r.n_episodes_total_same_panel_activity)
        rf = row(variant, "fixed65", "hospitalisation", "any", y)
        V[f"grd_records_hosp_fixed65_{y}"] = None if rf is None else _int(rf.n_episodes_total_same_panel_activity)
        for pos, tag, panel, ptag, act, atag in combos:
            r = row(variant, panel, act, pos, y)
            k = f"grd_f84_{tag}{atag}{ptag}"
            if r is None:
                V[f"{k}_n_{y}"] = None
                continue
            V[f"{k}_n_{y}"] = _int(r.n_episodes_f84)
            V[f"{k}_rate_{y}"] = _flt(r.rate_per_100k_episodes)
            V[f"{k}_rate_lo_{y}"] = _flt(r.rate_lo)
            V[f"{k}_rate_hi_{y}"] = _flt(r.rate_hi)
            if pos in ("any", "principal"):
                V[f"{k}_persons_{y}"] = _int(r.persons_within_year)
            if pos == "any" and panel == "observed" and act == "all":
                V[f"grd_f84_no_valid_id_{y}"] = _int(r.n_f84_without_valid_id)
        # derivadas
        V[f"grd_f84_secondary_only_share_{y}"] = _ratio(V[f"grd_f84_secondary_only_n_{y}"], V[f"grd_f84_any_n_{y}"])
        V[f"grd_f84_principal_share_{y}"] = _ratio(V[f"grd_f84_principal_n_{y}"], V[f"grd_f84_any_n_{y}"])
        V[f"grd_f84_any_share_cma_{y}"] = _ratio(V.get(f"grd_f84_any_cma_n_{y}"), V[f"grd_f84_any_n_{y}"])
        V[f"grd_episodes_per_person_any_{y}"] = _ratio(V[f"grd_f84_any_n_{y}"], V[f"grd_f84_any_persons_{y}"])
        V[f"grd_f84_any_share_of_records_pct_{y}"] = 100.0 * V[f"grd_f84_any_n_{y}"] / V[f"grd_records_total_{y}"]
        V[f"grd_records_fixed65_share_{y}"] = _ratio(V[f"grd_records_fixed65_{y}"], V[f"grd_records_total_{y}"])
        V[f"grd_f84_any_fixed65_share_{y}"] = _ratio(V[f"grd_f84_any_fixed65_n_{y}"], V[f"grd_f84_any_n_{y}"])
        # variante alterna y F84.0 estricto (idéntico en ambas variantes)
        o = row(other, "observed", "all", "any", y)
        V[f"grd_f84_any_n_other_variant_{y}"] = _int(o.n_episodes_f84)
        V[f"grd_f84_any_n_rett_only_difference_{y}"] = abs(_int(base.n_episodes_f84) - _int(o.n_episodes_f84))
        op = row(other, "observed", "all", "principal", y)
        V[f"grd_f84_principal_n_other_variant_{y}"] = _int(op.n_episodes_f84)
        for pos in ("any", "principal"):
            s = row("strict_autism_f840", "observed", "all", pos, y)
            V[f"grd_f840_strict_{pos}_n_{y}"] = _int(s.n_episodes_f84)
            V[f"grd_f840_strict_{pos}_rate_{y}"] = _flt(s.rate_per_100k_episodes)
            V[f"grd_f840_strict_{pos}_rate_lo_{y}"] = _flt(s.rate_lo)
            V[f"grd_f840_strict_{pos}_rate_hi_{y}"] = _flt(s.rate_hi)
            V[f"grd_f840_strict_{pos}_persons_{y}"] = _int(s.persons_within_year)
        V[f"grd_f840_strict_share_of_any_{y}"] = _ratio(V[f"grd_f840_strict_any_n_{y}"], V[f"grd_f84_any_n_{y}"])

    y0, y1 = YEARS_GRD[0], YEARS_GRD[-1]
    for k in ("grd_records_total", "grd_f84_any_n", "grd_f84_any_rate", "grd_f84_principal_n", "grd_f84_principal_rate",
              "grd_f84_any_fixed65_rate", "grd_f84_any_hosp_rate", "grd_f84_any_cma_n", "grd_f84_any_persons",
              "grd_f840_strict_any_rate", "grd_coding_depth_all_mean", "grd_coding_depth_f84_mean"):
        V[f"{k}_ratio_{y1}_{y0}"] = _ratio(V.get(f"{k}_{y1}"), V.get(f"{k}_{y0}"))
        V[f"{k}_ratio_{y1}_2021"] = _ratio(V.get(f"{k}_{y1}"), V.get(f"{k}_2021"))
    V["grd_f84_any_n_total_2019_2024"] = int(sum(V[f"grd_f84_any_n_{y}"] for y in YEARS_GRD))
    V["grd_f84_principal_n_total_2019_2024"] = int(sum(V[f"grd_f84_principal_n_{y}"] for y in YEARS_GRD))
    V["grd_records_total_2019_2024"] = int(sum(V[f"grd_records_total_{y}"] for y in YEARS_GRD))
    V["grd_f84_any_n_change_2024_vs_2023_pct"] = _pct_change(V["grd_f84_any_n_2024"], V["grd_f84_any_n_2023"])
    V["grd_f84_any_n_change_2020_vs_2019_pct"] = _pct_change(V["grd_f84_any_n_2020"], V["grd_f84_any_n_2019"])
    V["grd_records_total_change_2020_vs_2019_pct"] = _pct_change(V["grd_records_total_2020"], V["grd_records_total_2019"])
    V["grd_f84_any_rate_change_2020_vs_2019_pct"] = _pct_change(V["grd_f84_any_rate_2020"], V["grd_f84_any_rate_2019"])
    V["grd_f84_secondary_only_share_2024_pct"] = 100.0 * V["grd_f84_secondary_only_share_2024"]

    # panel fijo y hospitales añadidos
    fp = _tidy("grd_fixed_panel_hospitals")
    V["src_grd_fixed_panel"] = "outputs/tidy/grd_fixed_panel_hospitals.csv"
    V["grd_fixed_panel_n"] = int(fp.in_fixed_panel.sum())
    V["grd_hospitals_ever_observed_n"] = int(len(fp))
    added = fp[~fp.in_fixed_panel]
    V["grd_hospitals_added_2023_n"] = int((added.present_2023).sum())
    V["grd_hospitals_added_2024_only_n"] = int((added.present_2024 & ~added.present_2023).sum())
    V["grd_hospitals_added_names"] = "; ".join(f"{r.COD_HOSPITAL} {r.hospital_name}" for r in added.itertuples())

    # subcódigos (menciones por posición)
    sc = _tidy("grd_subcode_year")
    V["src_grd_subcodes"] = "outputs/tidy/grd_subcode_year.csv"
    sc = sc[sc.variants.str.contains(variant)]
    for y in YEARS_GRD:
        tot_any = sc[(sc.year == y) & (sc.position == "any")].n_episodes.sum()
        for code in CFG.VARIANTS[variant]["grd_subcodes"]:
            if code == "F84":
                continue
            for pos in ("any", "principal", "secondary"):
                r = _one(sc, year=y, subcode=code, position=pos)
                V[f"grd_subcode_{code}_{pos}_n_{y}"] = 0 if r is None else _int(r.n_episodes)
            V[f"grd_subcode_{code}_share_any_{y}"] = _ratio(V[f"grd_subcode_{code}_any_n_{y}"], tot_any)
        V[f"grd_subcode_mentions_any_total_{y}"] = _int(tot_any)
    # F84.2 siempre desde la tabla completa (aunque la variante lo excluya)
    sc_all = _tidy("grd_subcode_year")
    for y in YEARS_GRD:
        for pos in ("any", "principal", "secondary"):
            r = _one(sc_all, year=y, subcode="F842", position=pos)
            V[f"grd_f842_{pos}_n_{y}"] = 0 if r is None else _int(r.n_episodes)
        V[f"grd_f842_share_of_full_f84_any_{y}"] = _ratio(V[f"grd_f842_any_n_{y}"], sc_all[(sc_all.year == y) & (sc_all.position == "any")].n_episodes.sum())
    V["grd_f842_any_n_total_2019_2024"] = int(sum(V[f"grd_f842_any_n_{y}"] for y in YEARS_GRD))

    # profundidad diagnóstica por estrato
    cd = _tidy("grd_coding_depth_year")
    V["src_grd_coding_depth"] = "outputs/tidy/grd_coding_depth_year.csv"
    cd = cd[(cd.variant == variant) & (cd.panel == "observed") & (cd.activity == "all")]
    for r in cd.itertuples():
        b = _age(r.depth_bin)
        V[f"grd_depth_bin_{b}_n_total_{r.year}"] = _int(r.n_total)
        V[f"grd_depth_bin_{b}_n_f84_{r.year}"] = _int(r.n_f84_any)
        V[f"grd_depth_bin_{b}_rate_{r.year}"] = _flt(r.rate_per_100k_episodes)
        V[f"grd_depth_bin_{b}_rate_lo_{r.year}"] = _flt(r.rate_lo)
        V[f"grd_depth_bin_{b}_rate_hi_{r.year}"] = _flt(r.rate_hi)
    for y in YEARS_GRD:
        sub = cd[cd.year == y]
        V[f"grd_depth_share_records_8plus_{y}"] = _ratio(sub[sub.depth_bin.isin(["8-10", "11+"])].n_total.sum(), sub.n_total.sum())
        V[f"grd_depth_share_records_11plus_{y}"] = _ratio(sub[sub.depth_bin == "11+"].n_total.sum(), sub.n_total.sum())
        V[f"grd_depth_share_records_1_2_{y}"] = _ratio(sub[sub.depth_bin.isin(["1", "2"])].n_total.sum(), sub.n_total.sum())
    for b in ("3", "4", "5", "6_7", "8_10", "11plus"):
        V[f"grd_depth_bin_{b}_rate_ratio_{y1}_{y0}"] = _ratio(V.get(f"grd_depth_bin_{b}_rate_{y1}"), V.get(f"grd_depth_bin_{b}_rate_{y0}"))

    # auditoría de identificadores
    ia = _tidy("grd_identifier_audit")
    V["src_grd_identifier_audit"] = "outputs/tidy/grd_identifier_audit.csv"
    for r in ia[ia.variant == variant].itertuples():
        V[f"grd_ids_unique_{r.year}"] = _int(r.n_unique_ids)
        V[f"grd_ids_shared_with_previous_year_{r.year}"] = _int(r.n_f84_ids_shared_with_previous_year)
        V[f"grd_id_length_mode_{r.year}"] = _int(r.id_length_mode)
        V[f"grd_records_valid_id_all_{r.year}"] = _int(r.n_records_valid_id_all_episodes)
        V[f"grd_f84_with_comuna_{r.year}"] = _int(r.n_f84_with_comuna)
        V[f"grd_f84_exact_duplicates_read_columns_{r.year}"] = _int(r.n_f84_exact_duplicates_on_read_columns)

    # categorías de actividad crudas (2019 incluye urgencia y diurna); F84 solo con_rett en esa tabla
    ac = _tidy("grd_activity_categories_year")
    V["src_grd_activity_categories"] = "outputs/tidy/grd_activity_categories_year.csv"
    for r in ac.itertuples():
        s = _slug(r.tipo_actividad_raw)
        V[f"grd_activity_raw_{s}_records_{r.year}"] = _int(r.n_episodes)
        V[f"grd_activity_raw_{s}_f84_any_con_rett_{r.year}"] = _int(r.n_f84_any_con_rett)

    # edad y sexo (panel observado, toda actividad)
    ag = _tidy("grd_age_sex_year")
    V["src_grd_age_sex"] = "outputs/tidy/grd_age_sex_year.csv"
    ag = ag[(ag.variant == variant) & (ag.panel == "observed") & (ag.activity == "all")]
    ages = [a for a in CFG.__dict__.get("AGE_GROUPS", []) if a] or ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]
    for pos in ("any", "principal"):
        sub = ag[ag.position == pos]
        for y in YEARS_GRD:
            sy = sub[sub.year == y]
            for r in sy.itertuples():
                sx, a = SEX.get(r.sex, r.sex), _age(r.age_group)
                V[f"grd_agesex_{pos}_{sx}_{a}_n_{y}"] = _int(r.n_f84)
                V[f"grd_agesex_{pos}_{sx}_{a}_episodes_{y}"] = _int(r.n_total_episodes)
                V[f"grd_agesex_{pos}_{sx}_{a}_rate_{y}"] = None if r.n_total_episodes == 0 else 1e5 * r.n_f84 / r.n_total_episodes
            tot = sy.n_f84.sum()
            for sx_raw, sx in (("HOMBRE", "male"), ("MUJER", "female"), ("unknown", "unknown")):
                V[f"grd_f84_{pos}_{sx}_n_{y}"] = _int(sy[sy.sex == sx_raw].n_f84.sum())
            V[f"grd_f84_{pos}_mf_ratio_n_{y}"] = _ratio(V[f"grd_f84_{pos}_male_n_{y}"], V[f"grd_f84_{pos}_female_n_{y}"])
            V[f"grd_f84_{pos}_male_share_{y}"] = _ratio(V[f"grd_f84_{pos}_male_n_{y}"], tot)
            known = sy[sy.age_group != "unknown"]
            V[f"grd_f84_{pos}_share_age_0_9_{y}"] = _ratio(known[known.age_group.isin(["0-4", "5-9"])].n_f84.sum(), known.n_f84.sum())
            V[f"grd_f84_{pos}_share_age_0_4_{y}"] = _ratio(known[known.age_group == "0-4"].n_f84.sum(), known.n_f84.sum())
            V[f"grd_f84_{pos}_share_age_10_19_{y}"] = _ratio(known[known.age_group.isin(["10-14", "15-19"])].n_f84.sum(), known.n_f84.sum())
            V[f"grd_f84_{pos}_share_age_20plus_{y}"] = _ratio(known[~known.age_group.isin(["0-4", "5-9", "10-14", "15-19"])].n_f84.sum(), known.n_f84.sum())
            both = known.groupby("age_group")[["n_f84", "n_total_episodes"]].sum()
            both = both[both.n_total_episodes > 0]
            rates = 1e5 * both.n_f84 / both.n_total_episodes
            if len(rates):
                V[f"grd_f84_{pos}_peak_age_group_{y}"] = str(rates.idxmax())
                V[f"grd_f84_{pos}_peak_age_rate_{y}"] = float(rates.max())
                for a in ages:
                    if a in rates.index:
                        V[f"grd_agesex_{pos}_both_{_age(a)}_rate_{y}"] = float(rates[a])
                        V[f"grd_agesex_{pos}_both_{_age(a)}_n_{y}"] = _int(both.loc[a, "n_f84"])

    # tasas poblacionales (INE base 2017), brutas y estandarizadas OMS
    pr = _tidy("models_population_rates")
    V["src_grd_population_rates"] = "outputs/tidy/models_population_rates.csv"
    for var, tag in ((variant, "grd_pop"), ("strict_autism_f840", "grd_pop_f840_strict")):
        for r in pr[pr.variant == var].itertuples():
            sx = SEX[r.sex]
            k = f"{tag}_{r.position}_{sx}"
            V[f"{k}_count_{r.year}"] = _int(r.count)
            V[f"{k}_known_count_{r.year}"] = _int(r.known_count)
            V[f"{k}_crude_{r.year}"] = _flt(r.crude)
            V[f"{k}_crude_lo_{r.year}"] = _flt(r.crude_lo)
            V[f"{k}_crude_hi_{r.year}"] = _flt(r.crude_hi)
            V[f"{k}_asr_{r.year}"] = _flt(r.asr)
            V[f"{k}_asr_lo_{r.year}"] = _flt(r.asr_lo)
            V[f"{k}_asr_hi_{r.year}"] = _flt(r.asr_hi)
            if tag == "grd_pop":
                V[f"ine_pop_{sx}_{r.year}"] = _int(r.population)
    for y in YEARS_GRD:
        for pos in ("any", "principal"):
            V[f"grd_pop_{pos}_asr_mf_ratio_{y}"] = _ratio(V.get(f"grd_pop_{pos}_male_asr_{y}"), V.get(f"grd_pop_{pos}_female_asr_{y}"))
            V[f"grd_pop_{pos}_crude_mf_ratio_{y}"] = _ratio(V.get(f"grd_pop_{pos}_male_crude_{y}"), V.get(f"grd_pop_{pos}_female_crude_{y}"))
    for k in ("grd_pop_any_total_crude", "grd_pop_any_total_asr", "grd_pop_principal_total_asr", "grd_pop_any_male_asr", "grd_pop_any_female_asr"):
        V[f"{k}_ratio_{y1}_{y0}"] = _ratio(V.get(f"{k}_{y1}"), V.get(f"{k}_{y0}"))

    # efectos por hospital (2024 y modelos 2019–2024)
    he = _tidy("hospital_effects")
    V["src_grd_hospital_effects"] = "outputs/tidy/hospital_effects.csv"
    h = he[he.variant == variant].copy()
    V["grd_hosp2024_n_hospitals"] = int(len(h))
    V["grd_hosp2024_n_with_f84"] = int((h.n_f84_any > 0).sum())
    V["grd_hosp2024_n_fixed_panel"] = int(h.in_fixed_panel.sum())
    pos_rates = h[h.rate_2024 > 0].rate_2024
    V["grd_hosp2024_rate_min"] = _flt(h.rate_2024.min())
    V["grd_hosp2024_rate_max"] = _flt(h.rate_2024.max())
    V["grd_hosp2024_rate_median"] = _flt(h.rate_2024.median())
    V["grd_hosp2024_rate_q1"] = _flt(h.rate_2024.quantile(0.25))
    V["grd_hosp2024_rate_q3"] = _flt(h.rate_2024.quantile(0.75))
    V["grd_hosp2024_rate_ratio_max_min"] = _ratio(h.rate_2024.max(), pos_rates.min())
    V["grd_hosp2024_rate_ratio_q3_q1"] = _ratio(h.rate_2024.quantile(0.75), h.rate_2024.quantile(0.25))
    top = h.sort_values("rate_2024", ascending=False).head(3)
    for i, r in enumerate(top.itertuples(), 1):
        V[f"grd_hosp2024_top{i}_code"] = _int(r.COD_HOSPITAL)
        V[f"grd_hosp2024_top{i}_name"] = _str(r.hospital_name)
        V[f"grd_hosp2024_top{i}_rate"] = _flt(r.rate_2024)
        V[f"grd_hosp2024_top{i}_rate_lo"] = _flt(r.rate_lo)
        V[f"grd_hosp2024_top{i}_rate_hi"] = _flt(r.rate_hi)
        V[f"grd_hosp2024_top{i}_n_f84"] = _int(r.n_f84_any)
        V[f"grd_hosp2024_top{i}_episodes"] = _int(r.n_episodes_total)
    bottom = h.sort_values("rate_2024").head(3)
    for i, r in enumerate(bottom.itertuples(), 1):
        V[f"grd_hosp2024_bottom{i}_code"] = _int(r.COD_HOSPITAL)
        V[f"grd_hosp2024_bottom{i}_name"] = _str(r.hospital_name)
        V[f"grd_hosp2024_bottom{i}_rate"] = _flt(r.rate_2024)
        V[f"grd_hosp2024_bottom{i}_n_f84"] = _int(r.n_f84_any)
        V[f"grd_hosp2024_bottom{i}_episodes"] = _int(r.n_episodes_total)
    for eff in ("fixed_effects_none", "fixed_effects_depth", "random_intercept_none", "random_intercept_depth"):
        V[f"grd_hosp_rr_{eff}_min"] = _flt(h[f"rr_{eff}"].min())
        V[f"grd_hosp_rr_{eff}_max"] = _flt(h[f"rr_{eff}"].max())
        V[f"grd_hosp_rr_{eff}_ratio_max_min"] = _ratio(h[f"rr_{eff}"].max(), h[f"rr_{eff}"].min())
        V[f"grd_hosp_rr_{eff}_n_above1"] = int((h[f"rr_lo_{eff}"] > 1).sum())
        V[f"grd_hosp_rr_{eff}_n_below1"] = int((h[f"rr_hi_{eff}"] < 1).sum())
    V["grd_hosp_coding_depth_mean_min"] = _flt(h.coding_depth_mean.min())
    V["grd_hosp_coding_depth_mean_max"] = _flt(h.coding_depth_mean.max())
    V["grd_hosp_coding_depth_rate_spearman"] = _flt(h[["coding_depth_mean", "rate_2024"]].corr(method="spearman").iloc[0, 1])


# ---------------------------------------------------------------------------
# DEIS egresos (01b)
# ---------------------------------------------------------------------------
def _deis(V: dict, variant: str) -> None:
    d = _tidy("deis_year_summary")
    V["src_deis"] = "outputs/tidy/deis_year_summary.csv"
    d = d[(d.source_layout == "canonical") & (d.variant == variant)]
    for r in d.itertuples():
        y = r.year
        V[f"deis_discharges_total_{y}"] = _int(r.discharges_total)
        V[f"deis_f84_principal_n_{y}"] = _int(r.f84_diag1)
        V[f"deis_f84_diag2_n_{y}"] = _int(r.f84_diag2)
        V[f"deis_f84_principal_rate_{y}"] = _flt(r.rate_per_100k_discharges)
        V[f"deis_f84_principal_rate_lo_{y}"] = _flt(r.rate_lo95)
        V[f"deis_f84_principal_rate_hi_{y}"] = _flt(r.rate_hi95)
        V[f"deis_f842_principal_n_{y}"] = _int(r.f84_rett_f842_diag1)
        V[f"deis_f84_deaths_{y}"] = _int(r.f84_deaths)
        V[f"deis_discharges_snss_{y}"] = _int(r.discharges_snss)
        V[f"deis_discharges_no_snss_{y}"] = _int(r.discharges_no_snss)
        V[f"deis_discharges_suppressed_{y}"] = _int(r.discharges_suppressed)
        V[f"deis_f84_principal_snss_{y}"] = _int(r.f84_any_snss)
        V[f"deis_f84_principal_no_snss_{y}"] = _int(r.f84_any_no_snss)
        V[f"deis_f84_principal_suppressed_{y}"] = _int(r.f84_any_suppressed)
        V[f"deis_f84_principal_snss_share_{y}"] = _ratio(r.f84_any_snss, r.f84_diag1)
        V[f"deis_discharges_snss_share_{y}"] = _ratio(r.discharges_snss, r.discharges_total)
        V[f"deis_masked_rows_share_{y}"] = _flt(r.masked_rows_share)
    V["deis_f84_principal_n_total_2019_2024"] = int(sum(V[f"deis_f84_principal_n_{y}"] for y in YEARS_GRD))
    V["deis_f84_principal_rate_ratio_2024_2019"] = _ratio(V["deis_f84_principal_rate_2024"], V["deis_f84_principal_rate_2019"])
    V["deis_f84_principal_n_ratio_2024_2019"] = _ratio(V["deis_f84_principal_n_2024"], V["deis_f84_principal_n_2019"])
    V["deis_diag2_definition"] = "external cause (ICD-10 V01–Y98), not a secondary diagnosis"
    vg = _tidy("deis_vs_grd_year")
    V["src_deis_vs_grd"] = "outputs/tidy/deis_vs_grd_year.csv"
    for r in vg[vg.variant == variant].itertuples():
        y = r.year
        V[f"deis_vs_grd_ratio_total_discharges_{y}"] = _flt(r.ratio_deis_total_to_grd_total)
        V[f"deis_vs_grd_ratio_f84_principal_{y}"] = _flt(r.ratio_deis_f84_principal_to_grd_f84_principal)
        V[f"deis_vs_grd_ratio_f84_principal_snss_{y}"] = _flt(r.ratio_deis_f84_principal_snss_to_grd_f84_principal)
        V[f"deis_vs_grd_ratio_f84_principal_snss_hosp_{y}"] = _flt(r.ratio_deis_f84_principal_snss_to_grd_f84_principal_hospitalisation)
        V[f"deis_vs_grd_ratio_grd_any_to_deis_principal_{y}"] = _flt(r.ratio_grd_f84_any_to_deis_f84_principal)
    sub = _tidy("deis_f84_subcode_year")
    for r in sub.itertuples():
        if variant == "sin_rett" and not r.in_variant_sin_rett:
            continue
        V[f"deis_subcode_{r.f84_diag1_code}_principal_n_{r.year}"] = _int(r.discharges_f84_diag1)
    for y in YEARS_GRD:
        V[f"deis_f840_strict_principal_n_{y}"] = V.get(f"deis_subcode_F840_principal_n_{y}", 0)


# ---------------------------------------------------------------------------
# REM (02) + tasas estandarizadas A05 (06)
# ---------------------------------------------------------------------------
def _rem(V: dict, variant: str) -> None:
    R = _tidy("rem_pathway_annual", dtype={"code": str})
    V["src_rem"] = "outputs/tidy/rem_pathway_annual.csv"
    fam_entry = "+".join(CFG.VARIANTS[variant]["a05_entry"])
    fam_exit = "+".join(CFG.VARIANTS[variant]["a05_exit"])
    fam_p6_primary = "+".join(CFG.VARIANTS[variant]["p6_primary"])
    fam_p6_specialty = "+".join(CFG.VARIANTS[variant]["p6_specialty"])
    V["a05_family_codes_entry"] = fam_entry
    V["a05_family_codes_exit"] = fam_exit
    V["p6_family_codes_primary"] = fam_p6_primary
    V["p6_family_codes_specialty"] = fam_p6_specialty

    def put(prefix, code, var, measure, years, stable_key=True, share=False):
        rows = R[(R.code == code) & (R.variant == var) & (R.measure == measure)]
        n_stable = None
        for y in years:
            r = rows[rows.year == y]
            if len(r) == 0:
                V[f"{prefix}_{y}"] = None
                V[f"{prefix}_estab_{y}"] = None
                continue
            r = r.iloc[0]
            V[f"{prefix}_{y}"] = _int(r.total)
            V[f"{prefix}_estab_{y}"] = _int(r.n_reporting_establishments)
            V[f"{prefix}_estab_value_gt0_{y}"] = _int(r.n_establishments_value_gt0)
            V[f"{prefix}_months_covered_{y}"] = _int(r.months_covered)
            if stable_key:
                V[f"{prefix}_stable_total_{y}"] = _int(r.stable_panel_total)
                V[f"{prefix}_stable_share_{y}"] = _ratio(r.stable_panel_total, r.total)
                n_stable = _int(r.n_stable_panel_establishments)
            if share and r.n_reporting_establishments:
                V[f"{prefix}_per_estab_{y}"] = _ratio(r.total, r.n_reporting_establishments)
        if stable_key:
            V[f"{prefix}_stable_panel_n"] = n_stable
        return rows

    Y21 = [2021, 2022, 2023, 2024, 2025]
    Y23 = [2023, 2024, 2025]
    # --- A05 (flujos anuales) ---
    put("a05_autism_entries", CFG.A05_ENTRY["autism"], "single_code", "annual_sum", Y21, share=True)
    put("a05_autism_exits", CFG.A05_EXIT["autism"], "single_code", "annual_sum", Y21, share=True)
    put("a05_family_entries", fam_entry, variant, "annual_sum", Y21, share=True)
    put("a05_family_exits", fam_exit, variant, "annual_sum", Y21, share=True)
    for cat in ("asperger", "rett", "disintegrative", "pdd_nos"):
        put(f"a05_{cat}_entries", CFG.A05_ENTRY[cat], "single_code", "annual_sum", Y21)
        put(f"a05_{cat}_exits", CFG.A05_EXIT[cat], "single_code", "annual_sum", Y21)
    put("a05_broad_pdd_entries", CFG.A05_BROAD_PRE2021["entry"], "single_code", "annual_sum", [2019, 2020], share=True)
    put("a05_broad_pdd_exits", CFG.A05_BROAD_PRE2021["exit"], "single_code", "annual_sum", [2019, 2020])
    for k in ("a05_autism_entries", "a05_family_entries", "a05_autism_exits", "a05_family_exits", "a05_autism_entries_estab", "a05_autism_entries_stable_total"):
        V[f"{k}_ratio_2025_2021"] = _ratio(V.get(f"{k}_2025"), V.get(f"{k}_2021"))
        V[f"{k}_ratio_2024_2021"] = _ratio(V.get(f"{k}_2024"), V.get(f"{k}_2021"))
        V[f"{k}_change_2025_vs_2024_pct"] = _pct_change(V.get(f"{k}_2025"), V.get(f"{k}_2024"))
        V[f"{k}_change_2023_vs_2022_pct"] = _pct_change(V.get(f"{k}_2023"), V.get(f"{k}_2022"))
    V["a05_autism_entries_total_2021_2025"] = int(sum(V[f"a05_autism_entries_{y}"] for y in Y21))
    V["a05_family_entries_total_2021_2025"] = int(sum(V[f"a05_family_entries_{y}"] for y in Y21))
    V["a05_autism_entries_estab_change_2025_2024"] = V["a05_autism_entries_estab_2025"] - V["a05_autism_entries_estab_2024"]
    for y in Y21:
        V[f"a05_autism_share_of_family_entries_{y}"] = _ratio(V[f"a05_autism_entries_{y}"], V[f"a05_family_entries_{y}"])
        V[f"a05_autism_exits_per_100_entries_same_year_{y}"] = 100.0 * _ratio(V[f"a05_autism_exits_{y}"], V[f"a05_autism_entries_{y}"])
    V["a05_note_exits_per_entries"] = "same-year exits/entries within the A05 module; not person-linked, not a retention or discharge probability"

    # --- A03 por era ---
    for name, code in CFG.A03_LEGACY.items():
        yrs = [2019, 2020, 2021, 2022] if name in ("mchat_done", "mchat_altered") else list(range(2019, 2025))
        put(f"a03_legacy_{name}", code, "single_code", "annual_sum", yrs)
    for name, code in CFG.A03_2023_2024.items():
        yrs = [2023] if name == "second_part_medium" else [2023, 2024]
        put(f"a03_2023_{name}", code, "single_code", "annual_sum", yrs)
    for name, code in CFG.A03_2024_31_59.items():
        put(f"a03_2024_31_59_{name}", code, "single_code", "annual_sum", [2024])
    for name, code in CFG.A03_2025.items():
        put(f"a03_2025_{name}", code, "single_code", "annual_sum", [2025])
    for y in (2023, 2024):
        V[f"a03_2023_risk_total_{y}"] = int(sum(V[f"a03_2023_{n}_{y}"] for n in ("low", "medium", "high")))
        V[f"a03_2023_high_share_of_risk_{y}"] = _ratio(V[f"a03_2023_high_{y}"], V[f"a03_2023_risk_total_{y}"])
        V[f"a03_2023_medium_high_share_of_risk_{y}"] = _ratio(V[f"a03_2023_medium_{y}"] + V[f"a03_2023_high_{y}"], V[f"a03_2023_risk_total_{y}"])
    V["a03_2025_risk_total_2025"] = int(sum(V[f"a03_2025_{n}_2025"] for n in ("low", "medium_no_referral", "medium_referral", "high_referral")))
    V["a03_2025_motive_total_2025"] = int(sum(V[f"a03_2025_{n}_2025"] for n in ("motive_eedp", "motive_risk", "motive_both")))
    V["a03_2025_susp_30_59_total_2025"] = V["a03_2025_susp_30_59_no_referral_2025"] + V["a03_2025_susp_30_59_referral_2025"]
    V["a03_2024_31_59_alert_total_2024"] = V["a03_2024_31_59_alert_yes_2024"] + V["a03_2024_31_59_alert_no_2024"]
    V["a03_note_eras"] = "A03 eras are not comparable: legacy 2019–2022 restricted to children with language/social alteration; 2023–2024 M-CHAT-R/F risk categories; 2024 ages 31–59 months; 2025 full redesign"

    # --- A27 / A28 ---
    put("a27_counselling", CFG.A27["counselling"], "single_code", "annual_sum", Y23)
    put("a27_assisted_referral", CFG.A27["assisted_referral"], "single_code", "annual_sum", Y23)
    put("a28_primary", CFG.A28["primary"], "single_code", "annual_sum", Y23, share=True)
    put("a28_hospital", CFG.A28["hospital"], "single_code", "annual_sum", Y23, share=True)
    for k in ("a27_counselling", "a27_assisted_referral", "a28_primary", "a28_hospital"):
        V[f"{k}_ratio_2025_2023"] = _ratio(V[f"{k}_2025"], V[f"{k}_2023"])
        V[f"{k}_change_2025_vs_2024_pct"] = _pct_change(V[f"{k}_2025"], V[f"{k}_2024"])
        V[f"{k}_total_2023_2025"] = int(sum(V[f"{k}_{y}"] for y in Y23))
    V["a27_note"] = "A27 counts interventions, not unique children; assisted referral specific to M-CHAT-R/F only from 2023"

    # --- P2 (stocks) ---
    put("p2_tea_dec", CFG.P2_TEA, "single_code", "december_stock", YEARS_REM, share=True)
    put("p2_tea_jun", CFG.P2_TEA, "single_code", "june_stock", YEARS_REM)
    put("p2_naneas_dec", CFG.P2_NANEAS_TOTAL, "single_code", "december_stock", Y23)
    put("p2_naneas_jun", CFG.P2_NANEAS_TOTAL, "single_code", "june_stock", Y23, stable_key=False)
    for y in YEARS_REM:
        V[f"p2_jun_dec_ratio_{y}"] = _ratio(V[f"p2_tea_jun_{y}"], V[f"p2_tea_dec_{y}"])
        V[f"p2_estab_jun_dec_ratio_{y}"] = _ratio(V[f"p2_tea_jun_estab_{y}"], V[f"p2_tea_dec_estab_{y}"])
    for y in Y23:
        V[f"p2_tea_share_of_naneas_dec_{y}"] = _ratio(V[f"p2_tea_dec_{y}"], V[f"p2_naneas_dec_{y}"])
        V[f"p2_tea_share_of_naneas_dec_pct_{y}"] = 100.0 * V[f"p2_tea_share_of_naneas_dec_{y}"]
        V[f"p2_tea_share_of_naneas_jun_{y}"] = _ratio(V[f"p2_tea_jun_{y}"], V[f"p2_naneas_jun_{y}"])
    V["p2_naneas_jun_2023_reported"] = False
    V["p2_tea_dec_ratio_2025_2019"] = _ratio(V["p2_tea_dec_2025"], V["p2_tea_dec_2019"])
    V["p2_tea_dec_ratio_2025_2021"] = _ratio(V["p2_tea_dec_2025"], V["p2_tea_dec_2021"])
    V["p2_tea_dec_ratio_2025_2022"] = _ratio(V["p2_tea_dec_2025"], V["p2_tea_dec_2022"])
    V["p2_tea_dec_estab_ratio_2025_2019"] = _ratio(V["p2_tea_dec_estab_2025"], V["p2_tea_dec_estab_2019"])
    V["p2_tea_dec_stable_total_ratio_2025_2019"] = _ratio(V["p2_tea_dec_stable_total_2025"], V["p2_tea_dec_stable_total_2019"])
    V["p2_tea_dec_per_estab_ratio_2025_2019"] = _ratio(V["p2_tea_dec_per_estab_2025"], V["p2_tea_dec_per_estab_2019"])
    V["p2_naneas_dec_ratio_2025_2023"] = _ratio(V["p2_naneas_dec_2025"], V["p2_naneas_dec_2023"])
    for y in YEARS_REM[1:]:
        V[f"p2_tea_dec_change_{y}_vs_{y - 1}_pct"] = _pct_change(V[f"p2_tea_dec_{y}"], V[f"p2_tea_dec_{y - 1}"])
    V["p2_note"] = "December stock is the primary series; June is a sensitivity; semesters are never summed; NANEAS total exists only from December 2023"

    # --- P6 (stocks) ---
    put("p6_primary_autism_dec", CFG.P6_PRIMARY["autism"], "single_code", "december_stock", Y21, share=True)
    put("p6_primary_autism_jun", CFG.P6_PRIMARY["autism"], "single_code", "june_stock", Y21)
    put("p6_specialty_autism_dec", CFG.P6_SPECIALTY["autism"], "single_code", "december_stock", Y21, share=True)
    put("p6_specialty_autism_jun", CFG.P6_SPECIALTY["autism"], "single_code", "june_stock", Y21)
    put("p6_primary_family_dec", fam_p6_primary, variant, "december_stock", Y21, share=True)
    put("p6_primary_family_jun", fam_p6_primary, variant, "june_stock", Y21)
    put("p6_specialty_family_dec", fam_p6_specialty, variant, "december_stock", Y21, share=True)
    put("p6_specialty_family_jun", fam_p6_specialty, variant, "june_stock", Y21)
    for cat in ("asperger", "rett", "disintegrative", "pdd_nos"):
        put(f"p6_primary_{cat}_dec", CFG.P6_PRIMARY[cat], "single_code", "december_stock", Y21)
        put(f"p6_specialty_{cat}_dec", CFG.P6_SPECIALTY[cat], "single_code", "december_stock", Y21)
    put("p6_primary_broad_dec", CFG.P6_BROAD_PRE2021["primary"], "single_code", "december_stock", [2019, 2020])
    put("p6_primary_broad_jun", CFG.P6_BROAD_PRE2021["primary"], "single_code", "june_stock", [2019, 2020])
    put("p6_specialty_broad_dec", CFG.P6_BROAD_PRE2021["specialty"], "single_code", "december_stock", [2019, 2020])
    put("p6_specialty_broad_jun", CFG.P6_BROAD_PRE2021["specialty"], "single_code", "june_stock", [2019, 2020])
    for k in ("p6_primary_autism_dec", "p6_specialty_autism_dec", "p6_primary_family_dec", "p6_specialty_family_dec",
              "p6_primary_autism_dec_estab", "p6_specialty_autism_dec_estab"):
        V[f"{k}_ratio_2025_2021"] = _ratio(V.get(f"{k}_2025"), V.get(f"{k}_2021"))
        V[f"{k}_change_2025_vs_2024_pct"] = _pct_change(V.get(f"{k}_2025"), V.get(f"{k}_2024"))
    for y in Y21:
        V[f"p6_primary_autism_jun_dec_ratio_{y}"] = _ratio(V[f"p6_primary_autism_jun_{y}"], V[f"p6_primary_autism_dec_{y}"])
        V[f"p6_specialty_autism_jun_dec_ratio_{y}"] = _ratio(V[f"p6_specialty_autism_jun_{y}"], V[f"p6_specialty_autism_dec_{y}"])
        V[f"p6_primary_autism_share_of_family_dec_{y}"] = _ratio(V[f"p6_primary_autism_dec_{y}"], V[f"p6_primary_family_dec_{y}"])
        V[f"p6_specialty_autism_share_of_family_dec_{y}"] = _ratio(V[f"p6_specialty_autism_dec_{y}"], V[f"p6_specialty_family_dec_{y}"])
    V["p6_note"] = "P6 2019–2020 is broad PDD (taxonomic break); autism categories exist from 2021; primary care (APS) and specialty are separate stocks and are never summed"

    # --- establecimientos con alguna fila por módulo y año ---
    try:
        est = pd.read_csv(TIDY / "rem_establishment_year.csv", usecols=["year", "module", "IdEstablecimiento"], dtype={"IdEstablecimiento": str}, low_memory=False)
        V["src_rem_establishments"] = "outputs/tidy/rem_establishment_year.csv"
        for (y, m), n in est.groupby(["year", "module"]).IdEstablecimiento.nunique().items():
            V[f"rem_{m.lower()}_estab_any_code_{y}"] = int(n)
    except (FileNotFoundError, ValueError):
        pass

    # --- A05 edad y sexo (autismo estricto y familia de la variante) ---
    a = _tidy("rem_a05_age_sex_annual", dtype={"code": str})
    V["src_a05_age_sex"] = "outputs/tidy/rem_a05_age_sex_annual.csv"
    for tag, code, var in (("a05_autism", CFG.A05_ENTRY["autism"], "single_code"), ("a05_family", fam_entry, variant)):
        s = a[(a.code == code) & (a.variant == var) & (a.flow == "entry")]
        for y in Y21:
            sy = s[s.year == y]
            tot = sy[sy.age_group == "total"]
            for r in tot.itertuples():
                V[f"{tag}_entries_{SEX[r.sex]}_{y}"] = _int(r.count)
            V[f"{tag}_entries_mf_ratio_{y}"] = _ratio(V.get(f"{tag}_entries_male_{y}"), V.get(f"{tag}_entries_female_{y}"))
            V[f"{tag}_entries_male_share_{y}"] = _ratio(V.get(f"{tag}_entries_male_{y}"), (V.get(f"{tag}_entries_male_{y}") or 0) + (V.get(f"{tag}_entries_female_{y}") or 0))
            cells = sy[sy.age_group != "total"]
            if tag == "a05_autism":
                for r in cells.itertuples():
                    V[f"a05_autism_agesex_{SEX[r.sex]}_{_age(r.age_group)}_{y}"] = _int(r.count)
            by_age = cells.groupby("age_group")["count"].sum()
            ttl = by_age.sum()
            for ag_, n in by_age.items():
                V[f"{tag}_entries_both_{_age(ag_)}_{y}"] = _int(n)
                V[f"{tag}_entries_age_share_{_age(ag_)}_{y}"] = _ratio(n, ttl)
            V[f"{tag}_entries_share_age_0_9_{y}"] = _ratio(by_age.reindex(["0-4", "5-9"]).sum(), ttl)
            V[f"{tag}_entries_share_age_10_19_{y}"] = _ratio(by_age.reindex(["10-14", "15-19"]).sum(), ttl)
            V[f"{tag}_entries_share_age_20plus_{y}"] = _ratio(ttl - by_age.reindex(["0-4", "5-9", "10-14", "15-19"]).sum(), ttl)
            if len(by_age):
                V[f"{tag}_entries_modal_age_group_{y}"] = str(by_age.idxmax())

    # --- A05 tasas por población INE (brutas y estandarizadas OMS) ---
    st = _tidy("models_a05_standardised_rates")
    V["src_a05_standardised_rates"] = "outputs/tidy/models_a05_standardised_rates.csv"
    for var, tag in (("strict_autism", "a05_autism_pop"), (variant, "a05_family_pop")):
        for r in st[st.variant == var].itertuples():
            sx = SEX[r.sex]
            V[f"{tag}_{sx}_count_{r.year}"] = _int(r.count)
            V[f"{tag}_{sx}_crude_{r.year}"] = _flt(r.crude)
            V[f"{tag}_{sx}_crude_lo_{r.year}"] = _flt(r.crude_lo)
            V[f"{tag}_{sx}_crude_hi_{r.year}"] = _flt(r.crude_hi)
            V[f"{tag}_{sx}_asr_{r.year}"] = _flt(r.asr)
            V[f"{tag}_{sx}_asr_lo_{r.year}"] = _flt(r.asr_lo)
            V[f"{tag}_{sx}_asr_hi_{r.year}"] = _flt(r.asr_hi)
            V[f"{tag}_estab_{r.year}"] = _int(r.n_reporting_establishments)
            if r.year == 2025 and var == "strict_autism":
                V[f"ine_pop_{sx}_2025"] = _int(r.population)
    for y in Y21:
        V[f"a05_autism_pop_asr_mf_ratio_{y}"] = _ratio(V.get(f"a05_autism_pop_male_asr_{y}"), V.get(f"a05_autism_pop_female_asr_{y}"))
        V[f"a05_family_pop_asr_mf_ratio_{y}"] = _ratio(V.get(f"a05_family_pop_male_asr_{y}"), V.get(f"a05_family_pop_female_asr_{y}"))
    for k in ("a05_autism_pop_total_crude", "a05_autism_pop_total_asr", "a05_family_pop_total_asr", "a05_autism_pop_male_asr", "a05_autism_pop_female_asr"):
        V[f"{k}_ratio_2025_2021"] = _ratio(V.get(f"{k}_2025"), V.get(f"{k}_2021"))


# ---------------------------------------------------------------------------
# Denominadores y cobertura (03)
# ---------------------------------------------------------------------------
def _denominators(V: dict) -> None:
    c = _tidy("coverage_layers_year")
    V["src_coverage_layers"] = "outputs/tidy/coverage_layers_year.csv"
    cols = {
        "ine_population_base2017_30jun": "ine_pop_total", "ine_population_base2024_national_30jun": "ine_pop_base2024_total",
        "fonasa_beneficiaries_dec": "fonasa_beneficiaries", "fonasa_inscritos_aps_dec": "fonasa_inscritos_aps",
        "isapre_beneficiaries_dec": "isapre_beneficiaries", "aps_enrolled_dec": "aps_enrolled", "aps_enrolled_tramo_AD_dec": "aps_enrolled_tramo_ad",
        "aps_centres": "aps_centres", "aps_panel_1871_enrolled": "aps_panel_enrolled", "aps_panel_1871_retention": "aps_panel_retention",
        "rem20_establishments_reporting": "rem20_estab", "rem20_discharges_all": "rem20_discharges", "rem20_discharges_panel_188": "rem20_discharges_panel",
        "rem20_panel_188_retention": "rem20_panel_retention", "fonasa_plus_isapre": "fonasa_plus_isapre", "share_fonasa_ine": "share_fonasa_ine",
        "share_isapre_ine": "share_isapre_ine", "share_fonasa_plus_isapre_ine": "share_fonasa_plus_isapre_ine",
        "share_fonasa_plus_isapre_ine_base2024": "share_fonasa_plus_isapre_ine_base2024", "ratio_aps_tramoAD_to_fonasa_inscritos": "ratio_aps_tramo_ad_to_fonasa_inscritos",
        "rem20_discharges_per_1000_ine": "rem20_discharges_per_1000_ine",
    }
    for r in c.itertuples():
        y = r.year
        for src, dst in cols.items():
            val = getattr(r, src)
            V[f"{dst}_{y}"] = _flt(val) if ("share" in dst or "retention" in dst or "ratio" in dst or "per_1000" in dst) else _int(val)
        V[f"share_fonasa_ine_pct_{y}"] = None if V[f"share_fonasa_ine_{y}"] is None else 100.0 * V[f"share_fonasa_ine_{y}"]
        V[f"share_isapre_ine_pct_{y}"] = None if V[f"share_isapre_ine_{y}"] is None else 100.0 * V[f"share_isapre_ine_{y}"]
        V[f"share_fonasa_plus_isapre_ine_pct_{y}"] = 100.0 * V[f"share_fonasa_plus_isapre_ine_{y}"]
        V[f"aps_panel_retention_pct_{y}"] = 100.0 * V[f"aps_panel_retention_{y}"]
        V[f"rem20_panel_retention_pct_{y}"] = 100.0 * V[f"rem20_panel_retention_{y}"]
    V["coverage_caveat"] = _str(c.caveat.iloc[0])
    y0, y1 = YEARS_REM[0], YEARS_REM[-1]
    for k in ("ine_pop_total", "fonasa_beneficiaries", "isapre_beneficiaries", "aps_enrolled", "aps_centres", "fonasa_plus_isapre", "rem20_discharges"):
        V[f"{k}_ratio_{y1}_{y0}"] = _ratio(V[f"{k}_{y1}"], V[f"{k}_{y0}"])
        V[f"{k}_change_{y1}_vs_{y0}_pct"] = _pct_change(V[f"{k}_{y1}"], V[f"{k}_{y0}"])
        V[f"{k}_change_{y1}_vs_{y0}_abs"] = V[f"{k}_{y1}"] - V[f"{k}_{y0}"]
    V["share_fonasa_ine_change_2025_vs_2019_pp"] = 100.0 * (V["share_fonasa_ine_2025"] - V["share_fonasa_ine_2019"])
    V["share_isapre_ine_change_2025_vs_2019_pp"] = 100.0 * (V["share_isapre_ine_2025"] - V["share_isapre_ine_2019"])

    ib = _tidy("ine_population_base_comparison")
    V["src_ine_bases"] = "outputs/tidy/ine_population_base_comparison.csv"
    for r in ib.itertuples():
        V[f"ine_pop_base2024_1jan_{r.year}"] = _int(r.base2024_national_1jan)
        V[f"ine_ratio_base2024_base2017_{r.year}"] = _flt(r.ratio_base2024_to_base2017_30jun)
        if not _isnan(r.censo2024_enumerated):
            V["censo2024_enumerated"] = _int(r.censo2024_enumerated)
            V["ine_ratio_censo2024_base2017_2024"] = _flt(r.ratio_censo2024_to_base2017)
    V["ine_note_bases"] = _str(ib.note.iloc[0])

    fn = _tidy("fonasa_beneficiaries_national_year")
    V["src_fonasa_national"] = "outputs/tidy/fonasa_beneficiaries_national_year.csv"
    for r in fn[fn.dimension == "TOTAL"].itertuples():
        V[f"fonasa_beneficiaries_total_file_{r.year}"] = _int(r.beneficiaries)
    for r in fn[fn.dimension == "INSCRITO_APS"].itertuples():
        V[f"fonasa_inscrito_aps_{_slug(r.category)}_{r.year}"] = _int(r.beneficiaries)
    for r in fn[fn.dimension == "SEXO"].itertuples():
        V[f"fonasa_sex_{_slug(r.category)}_{r.year}"] = _int(r.beneficiaries)
    fs = _tidy("fonasa_schema_by_year")
    V["fonasa_schema_years"] = ", ".join(str(int(y)) for y in sorted(fs.year.unique()))
    V["fonasa_schema_files_n"] = int(len(fs))

    isa = _tidy("isapre_beneficiaries_national_year")
    V["src_isapre_national"] = "outputs/tidy/isapre_beneficiaries_national_year.csv"
    for r in isa.itertuples():
        V[f"isapre_cotizantes_{r.year}"] = _int(r.cotizantes)
        V[f"isapre_cargas_{r.year}"] = _int(r.cargas)
        V[f"isapre_nonatos_sin_clasificar_{r.year}"] = _int(r.nonatos_sin_clasificar)
        V[f"isapre_beneficiaries_female_{r.year}"] = _int(r.beneficiarios_female)
        V[f"isapre_beneficiaries_male_{r.year}"] = _int(r.beneficiarios_male)
        V[f"isapre_source_file_{r.year}"] = _str(r.source_file)

    ap = _tidy("aps_panel")
    V["src_aps_panel"] = "outputs/tidy/aps_panel.csv"
    V["aps_panel_n"] = _int(ap.centres_panel.iloc[0])
    for r in ap.itertuples():
        V[f"aps_enrolled_tramo_x_{r.year}"] = _int(r.enrolled_tramo_X)
        V[f"aps_enrolled_tramo_missing_{r.year}"] = _int(r.enrolled_tramo_missing)
    rp = _tidy("rem20_panel")
    V["src_rem20_panel"] = "outputs/tidy/rem20_panel.csv"
    V["rem20_panel_n"] = _int(rp.establishments_panel.iloc[0])
    for r in rp.itertuples():
        V[f"rem20_estab_12_months_{r.year}"] = _int(r.establishments_with_12_months)
        V[f"rem20_bed_days_{r.year}"] = _int(r.bed_days_available_total)
        V[f"rem20_bed_days_panel_{r.year}"] = _int(r.bed_days_available_panel_188)
        V[f"rem20_bed_days_retention_{r.year}"] = _flt(r.retention_bed_days)
    V["rem20_note"] = _str(rp.note.iloc[0])

    # cobertura por edad (2025, S11) y crosswalk comunal
    try:
        s11 = pd.read_csv(OUT / "con_rett" / "en" / "tables" / "S11_coverage_age_sex_numeric.csv")
        V["src_coverage_age_2025"] = "outputs/con_rett/en/tables/S11_coverage_age_sex_numeric.csv"
        for r in s11.itertuples():
            b = _age(r.age_band_10y)
            for layer in ("ine", "fonasa", "aps", "isapre"):
                V[f"coverage_2025_{layer}_age_{b}"] = _int(getattr(r, layer))
            V[f"coverage_2025_share_fonasa_ine_age_{b}"] = _ratio(r.fonasa, r.ine)
            V[f"coverage_2025_share_isapre_ine_age_{b}"] = _ratio(r.isapre, r.ine)
    except FileNotFoundError:
        pass
    cw = _tidy("comuna_crosswalk")
    V["src_comuna_crosswalk"] = "outputs/tidy/comuna_crosswalk.csv"
    V["crosswalk_comunas_n"] = int(len(cw))
    V["crosswalk_non_continental_n"] = int(cw.non_continental.sum()) if "non_continental" in cw.columns else None
    V["crosswalk_aliases"] = "; ".join(f"{k}→{v}" for k, v in CFG.COMUNA_ALIASES.items())
    um = _tidy("comuna_unmatched")
    V["src_comuna_unmatched"] = "outputs/tidy/comuna_unmatched.csv"
    V["crosswalk_unmatched_rows_n"] = int(len(um))
    for (src, y), n in um.groupby(["source", "year"])["count"].sum().items():
        V[f"crosswalk_unmatched_persons_{_slug(src)}_{y}"] = _int(n)
    for y in YEARS_REM:
        p = V.get(f"crosswalk_unmatched_persons_fonasa_{y}")
        V[f"crosswalk_unmatched_share_fonasa_{y}"] = _ratio(p, V.get(f"fonasa_beneficiaries_{y}"))


# ---------------------------------------------------------------------------
# Encuestas (04)
# ---------------------------------------------------------------------------
_SVY_DOMAINS = [
    ("ENDIDE adultos 18+: autismo reportado", "endide_adults_reported"),
    ("ENDIDE NNA 2-17: autismo reportado y confirmado por un médico", "endide_children_reported_confirmed"),
    ("ENDIDE NNA 2-17: autismo reportado", "endide_children_reported"),
    ("ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)", "endide_children_confirmed_among_reported_sens"),
    ("ENDIDE NNA con autismo reportado: confirmado por un médico", "endide_children_confirmed_among_reported"),
    ("ENDIDE NNA con autismo reportado: ha recibido medicamento", "endide_children_medication_among_reported"),
    ("ENDIDE NNA con autismo reportado: ha recibido otro tratamiento", "endide_children_other_treatment_among_reported"),
    ("ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)", "encavi_15plus_diagnosed_sens"),
    ("ENCAVI 15+: diagnóstico de trastorno del espectro autista", "encavi_15plus_diagnosed"),
    ("ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico", "encavi_15plus_treatment_among_diagnosed"),
]


def _svy_domain_key(domain: str) -> str:
    for text, key in _SVY_DOMAINS:
        if domain == text:
            return key
    return _slug(domain)


def _surveys(V: dict) -> None:
    s = _tidy("survey_estimates")
    V["src_surveys"] = "outputs/tidy/survey_estimates.csv"
    for r in s.itertuples():
        dom = _svy_domain_key(r.domain)
        sub = "total" if r.subgroup_type == "total" else (SEX.get(r.subgroup, None) if r.subgroup_type == "sex" else f"age_{_age(r.subgroup)}")
        k = f"svy_{dom}_{sub}"
        V[f"{k}_prop"] = _flt(r.proportion)
        V[f"{k}_pct"] = None if _isnan(r.proportion) else 100.0 * float(r.proportion)
        V[f"{k}_se"] = _flt(r.se)
        V[f"{k}_lo"] = _flt(r.lo)
        V[f"{k}_hi"] = _flt(r.hi)
        V[f"{k}_lo_pct"] = None if _isnan(r.lo) else 100.0 * float(r.lo)
        V[f"{k}_hi_pct"] = None if _isnan(r.hi) else 100.0 * float(r.hi)
        V[f"{k}_n"] = _int(r.n)
        V[f"{k}_cases"] = _int(r.cases)
        V[f"{k}_weighted_total"] = _flt(r.weighted_total)
        V[f"{k}_weighted_population"] = _flt(r.weighted_population)
        V[f"{k}_deff"] = _flt(r.deff)
        V[f"{k}_rse"] = _flt(r.rse)
        V[f"{k}_df"] = _int(r.df)
        V[f"{k}_n_psu"] = _int(r.n_psu)
        V[f"{k}_n_strata"] = _int(r.n_strata)
        V[f"{k}_precision_flag"] = _str(r.precision_flag)
        V[f"{k}_estimate_type"] = _str(r.estimate_type)
        V[f"{k}_item_variable"] = _str(r.item_variable)
        V[f"{k}_per_100k"] = None if _isnan(r.proportion) else 1e5 * float(r.proportion)
    for svy, tag in (("ENDIDE 2022", "endide"), ("ENCAVI 2023-2024", "encavi")):
        r = s[s.survey == svy].iloc[0]
        V[f"svy_{tag}_weight_var"] = _str(r.weight_var)
        V[f"svy_{tag}_strata_var"] = _str(r.strata_var)
        V[f"svy_{tag}_psu_var"] = _str(r.psu_var)
        V[f"svy_{tag}_ci_method"] = _str(r.ci_method)
        V[f"svy_{tag}_source_file"] = _str(r.source_file)
        V[f"svy_{tag}_source_sha256"] = _str(r.source_sha256)
        V[f"svy_{tag}_module"] = _str(r.module)
        V[f"svy_{tag}_deff_note"] = _str(r.deff_note)
    V["svy_endide_children_mf_ratio_reported"] = _ratio(V.get("svy_endide_children_reported_male_prop"), V.get("svy_endide_children_reported_female_prop"))
    V["svy_endide_adults_mf_ratio_reported"] = _ratio(V.get("svy_endide_adults_reported_male_prop"), V.get("svy_endide_adults_reported_female_prop"))
    V["svy_encavi_mf_ratio_diagnosed"] = _ratio(V.get("svy_encavi_15plus_diagnosed_male_prop"), V.get("svy_encavi_15plus_diagnosed_female_prop"))
    V["svy_precision_rule"] = "imprecise = fewer than 30 unweighted cases in the domain; RSE also reported"
    V["svy_note"] = "Complex-design estimates (Taylor linearisation; logit CI with df = PSUs − strata); benchmarks of self-/caregiver report, not validated prevalence and not linkable to administrative counts"


# ---------------------------------------------------------------------------
# Educación (05)
# ---------------------------------------------------------------------------
def _education(V: dict) -> None:
    p = _tidy("pie_series")
    V["src_pie"] = "outputs/tidy/pie_series.csv"
    for r in p.itertuples():
        V[f"{r.series}_{r.year}"] = _int(r.value) if r.unit == "students" else _flt(r.value)
    V["pie_2022_discrepancy_cases"] = V["pie_harmonised_sinaces_2022"] - V["pie_harmonised_2022"]
    V["pie_2022_sinaces_printed"] = V["pie_harmonised_sinaces_2022"]
    V["pie_2022_sinaces_total_minus_special"] = V["sinaces_total_minus_special_2022"]
    V["pie_2022_apuntes60_sum"] = V["pie_tea_strict_2022"] + V["pie_tea_asperger_2022"]
    V["pie_harmonised_ratio_2025_2019"] = _ratio(V["pie_harmonised_2025"], V["pie_harmonised_2019"])
    V["pie_harmonised_ratio_2023_2019"] = _ratio(V["pie_harmonised_2023"], V["pie_harmonised_2019"])
    V["pie_harmonised_ratio_2025_2021"] = _ratio(V["pie_harmonised_2025"], V["pie_harmonised_2021"])
    V["pie_tea_strict_ratio_2023_2019"] = _ratio(V["pie_tea_strict_2023"], V["pie_tea_strict_2019"])
    V["pie_tea_asperger_ratio_2023_2019"] = _ratio(V["pie_tea_asperger_2023"], V["pie_tea_asperger_2019"])
    V["sinaces_total_autistic_students_ratio_2025_2022"] = _ratio(V["sinaces_total_autistic_students_2025"], V["sinaces_total_autistic_students_2022"])
    for y in range(2020, 2026):
        V[f"pie_harmonised_change_{y}_vs_{y - 1}_pct"] = _pct_change(V[f"pie_harmonised_{y}"], V[f"pie_harmonised_{y - 1}"])
    for y in (2022, 2023, 2024, 2025):
        V[f"pie_tea_exceptional_share_{y}"] = _ratio(V[f"pie_tea_exceptional_entry_{y}"], V[f"pie_tea_exceptional_entry_{y}"] + V[f"pie_tea_regular_entry_{y}"])
        V[f"special_schools_autism_share_of_sinaces_total_{y}"] = _ratio(V[f"special_schools_autism_{y}"], V[f"sinaces_total_autistic_students_{y}"])
    V["pie_tea_strict_share_of_pie_pct_change_2023_vs_2019_pp"] = V["pie_tea_strict_share_of_pie_pct_2023"] - V["pie_tea_strict_share_of_pie_pct_2019"]
    V["pie_note"] = "PIE registers autistic students for subsidy purposes in state-funded schools; it does not include every autistic student (SINACES, p. 8); harmonised = ASD + ASD-Asperger (Apuntes 60 2019–2023; SINACES 2024–2025; 2022 rule = 42,940)"

    j = _tidy("junaeb_tea_year_level")
    V["src_junaeb"] = "outputs/tidy/junaeb_tea_year_level.csv"
    for r in j.itertuples():
        k = f"junaeb_{r.level}_{SEX.get(r.sex, r.sex)}"
        y = r.year
        V[f"{k}_n_students_{y}"] = _int(r.n_students)
        V[f"{k}_tea_n_{y}"] = _int(r.n_tea_unweighted)
        V[f"{k}_pct_weighted_{y}"] = _flt(r.proportion_weighted_pct)
        V[f"{k}_se_pct_{y}"] = _flt(r.se_pct)
        V[f"{k}_lo_pct_{y}"] = _flt(r.lo_pct)
        V[f"{k}_hi_pct_{y}"] = _flt(r.hi_pct)
        V[f"{k}_pct_unweighted_{y}"] = _flt(r.proportion_unweighted_pct)
        V[f"{k}_lo_unweighted_pct_{y}"] = _flt(r.lo_unweighted_pct)
        V[f"{k}_hi_unweighted_pct_{y}"] = _flt(r.hi_unweighted_pct)
        V[f"{k}_weighted_tea_total_{y}"] = _flt(r.weighted_tea_total)
        V[f"{k}_weighted_population_{y}"] = _flt(r.weighted_population)
        V[f"{k}_n_answered_{y}"] = _int(r.n_answered)
        V[f"{k}_pct_weighted_answered_{y}"] = _flt(r.proportion_weighted_answered_pct)
        V[f"{k}_estimable_{y}"] = _str(r.estimable)
        V[f"{k}_weight_variable_{y}"] = _str(r.weight_variable)
        V[f"{k}_item_variable_{y}"] = _str(r.item_variable)
        if r.sex == "all":
            V[f"junaeb_{r.level}_n_rows_{y}"] = _int(r.n_rows)
            V[f"junaeb_{r.level}_n_filter_yes_{y}"] = _int(r.n_filter_yes)
            V[f"junaeb_{r.level}_n_missing_item_{y}"] = _int(r.n_missing_item)
            V[f"junaeb_{r.level}_n_weight_missing_{y}"] = _int(r.n_weight_missing)
            V[f"junaeb_{r.level}_label_en_{y}"] = _str(r.level_label_en)
            V[f"junaeb_{r.level}_label_es_{y}"] = _str(r.level_label_es)
            V[f"junaeb_{r.level}_note_{y}"] = _str(r.note)
            V[f"junaeb_{r.level}_share_tea_among_diagnosed_pct_{y}"] = _flt(r.share_tea_among_diagnosed_pct)
    for lvl in ("parvularia", "basico1", "basico5", "medio1"):
        V[f"junaeb_{lvl}_all_pct_weighted_change_2025_vs_2024_pp"] = (None if V.get(f"junaeb_{lvl}_all_pct_weighted_2025") is None or V.get(f"junaeb_{lvl}_all_pct_weighted_2024") is None
                                                                     else V[f"junaeb_{lvl}_all_pct_weighted_2025"] - V[f"junaeb_{lvl}_all_pct_weighted_2024"])
    V["junaeb_medio1_2024_estimable"] = V.get("junaeb_medio1_all_estimable_2024")
    V["junaeb_levels_not_estimable_2019_2022"] = "all levels 2019–2022 (no ASD item in the questionnaire)"
    V["junaeb_note"] = "Selected school cohorts (pre-kindergarten/kindergarten, grades 1, 5 and 9) and caregiver report with the annual wording; weights EXP_REG (2024) and EXP (2025); 2023 has no published weight; grade 9 in 2024 is not estimable (variable entirely empty), not zero"
    try:
        s12 = pd.read_csv(OUT / "con_rett" / "en" / "tables" / "S12_junaeb_sex_level_ratio_numeric.csv")
        V["src_junaeb_mf_ratio"] = "outputs/con_rett/en/tables/S12_junaeb_sex_level_ratio_numeric.csv"
        for r in s12.itertuples():
            V[f"junaeb_{r.level}_mf_ratio_{r.year}"] = _flt(r.ratio)
            V[f"junaeb_{r.level}_mf_ratio_lo_{r.year}"] = _flt(r.lo)
            V[f"junaeb_{r.level}_mf_ratio_hi_{r.year}"] = _flt(r.hi)
            V[f"junaeb_{r.level}_mf_ratio_estimator_{r.year}"] = _str(r.estimator)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Modelos (06)
# ---------------------------------------------------------------------------
_MODEL_FIELDS = ("apc", "apc_lo", "apc_hi", "p_value", "dispersion", "durbin_watson", "n_obs", "df_resid", "beta", "se",
                 "depth_coef", "re_sd", "re_sd_lo", "re_sd_hi", "stable_panel_n", "years", "model_family", "covariates", "panel",
                 "activity", "position", "denominator_offset", "outcome", "sex", "hospitals_first", "hospitals_last", "note_keys")


def _alias_table(variant: str) -> dict:
    v = variant
    return {
        # GRD por 100.000 episodios (nacional, cuasi-Poisson)
        "apc_grd_any_obs": f"grd_rate:{v}:observed:all:any:none:2019-2024",
        "apc_grd_any_obs_depth": f"grd_rate:{v}:observed:all:any:depth:2019-2024",
        "apc_grd_any_obs_disruption": f"grd_rate:{v}:observed:all:any:disruption:2019-2024",
        "apc_grd_any_obs_depth_disruption": f"grd_rate:{v}:observed:all:any:depth_disruption:2019-2024",
        "apc_grd_any_obs_2021_2024": f"grd_rate:{v}:observed:all:any:none:2021-2024",
        "apc_grd_any_obs_depth_2021_2024": f"grd_rate:{v}:observed:all:any:depth:2021-2024",
        "apc_grd_any_fixed65": f"grd_rate:{v}:fixed65:all:any:none:2019-2024",
        "apc_grd_any_fixed65_depth": f"grd_rate:{v}:fixed65:all:any:depth:2019-2024",
        "apc_grd_any_fixed65_disruption": f"grd_rate:{v}:fixed65:all:any:disruption:2019-2024",
        "apc_grd_any_fixed65_2021_2024": f"grd_rate:{v}:fixed65:all:any:none:2021-2024",
        "apc_grd_any_hosp": f"grd_rate:{v}:observed:hospitalisation:any:none:2019-2024",
        "apc_grd_any_hosp_depth": f"grd_rate:{v}:observed:hospitalisation:any:depth:2019-2024",
        "apc_grd_any_hosp_disruption": f"grd_rate:{v}:observed:hospitalisation:any:disruption:2019-2024",
        "apc_grd_any_hosp_2021_2024": f"grd_rate:{v}:observed:hospitalisation:any:none:2021-2024",
        "apc_grd_any_hosp_fixed65": f"grd_rate:{v}:fixed65:hospitalisation:any:none:2019-2024",
        "apc_grd_principal_obs": f"grd_rate:{v}:observed:all:principal:none:2019-2024",
        "apc_grd_principal_obs_depth": f"grd_rate:{v}:observed:all:principal:depth:2019-2024",
        "apc_grd_principal_obs_disruption": f"grd_rate:{v}:observed:all:principal:disruption:2019-2024",
        "apc_grd_principal_obs_depth_disruption": f"grd_rate:{v}:observed:all:principal:depth_disruption:2019-2024",
        "apc_grd_principal_obs_2021_2024": f"grd_rate:{v}:observed:all:principal:none:2021-2024",
        "apc_grd_principal_fixed65": f"grd_rate:{v}:fixed65:all:principal:none:2019-2024",
        "apc_grd_principal_hosp": f"grd_rate:{v}:observed:hospitalisation:principal:none:2019-2024",
        "apc_grd_principal_hosp_disruption": f"grd_rate:{v}:observed:hospitalisation:principal:disruption:2019-2024",
        "apc_grd_f840_strict_any_obs": "grd_rate:strict_autism_f840:observed:all:any:none:2019-2024",
        "apc_grd_f840_strict_any_obs_depth": "grd_rate:strict_autism_f840:observed:all:any:depth:2019-2024",
        "apc_grd_f840_strict_principal_obs": "grd_rate:strict_autism_f840:observed:all:principal:none:2019-2024",
        # hospital-año
        "apc_grd_hospital_fe": f"grd_hospital:{v}:observed:any:none:2019-2024:model",
        "apc_grd_hospital_fe_cluster": f"grd_hospital:{v}:observed:any:none:2019-2024:cluster",
        "apc_grd_hospital_fe_depth": f"grd_hospital:{v}:observed:any:depth:2019-2024:model",
        "apc_grd_hospital_fe_disruption": f"grd_hospital:{v}:observed:any:disruption:2019-2024:model",
        "apc_grd_hospital_ri": f"grd_hospital:{v}:observed:any:ri_none:2019-2024:random_intercept",
        "apc_grd_hospital_ri_depth": f"grd_hospital:{v}:observed:any:ri_depth:2019-2024:random_intercept",
        "apc_grd_hospital_fe_2021_2024": f"grd_hospital:{v}:observed:any:none:2021-2024:model",
        "apc_grd_hospital_fe_fixed65": f"grd_hospital:{v}:fixed65:any:none:2019-2024:model",
        "apc_grd_hospital_fe_fixed65_cluster": f"grd_hospital:{v}:fixed65:any:none:2019-2024:cluster",
        "apc_grd_hospital_ri_fixed65": f"grd_hospital:{v}:fixed65:any:ri_none:2019-2024:random_intercept",
        # por población INE
        "apc_grd_pop_any_total_crude": f"grd_pop:{v}:any:TOTAL:crude:2019-2024",
        "apc_grd_pop_any_total_ageadj": f"grd_pop:{v}:any:TOTAL:age_adjusted:2019-2024",
        "apc_grd_pop_any_male_ageadj": f"grd_pop:{v}:any:HOMBRE:age_adjusted:2019-2024",
        "apc_grd_pop_any_female_ageadj": f"grd_pop:{v}:any:MUJER:age_adjusted:2019-2024",
        "apc_grd_pop_any_male_crude": f"grd_pop:{v}:any:HOMBRE:crude:2019-2024",
        "apc_grd_pop_any_female_crude": f"grd_pop:{v}:any:MUJER:crude:2019-2024",
        "apc_grd_pop_any_total_ageadj_2021_2024": f"grd_pop:{v}:any:TOTAL:age_adjusted:2021-2024",
        "apc_grd_pop_principal_total_crude": f"grd_pop:{v}:principal:TOTAL:crude:2019-2024",
        "apc_grd_pop_principal_total_ageadj": f"grd_pop:{v}:principal:TOTAL:age_adjusted:2019-2024",
        "apc_grd_pop_principal_male_ageadj": f"grd_pop:{v}:principal:HOMBRE:age_adjusted:2019-2024",
        "apc_grd_pop_principal_female_ageadj": f"grd_pop:{v}:principal:MUJER:age_adjusted:2019-2024",
        "apc_grd_pop_f840_strict_any_total_ageadj": "grd_pop:strict_autism_f840:any:TOTAL:age_adjusted:2019-2024",
        # REM A05
        "apc_a05_autism_pop": "a05_entry:strict_autism:pop:none:2021-2025",
        "apc_a05_autism_pop_2022_2025": "a05_entry:strict_autism:pop:none:2022-2025",
        "apc_a05_autism_pop_disruption2021": "a05_entry:strict_autism:pop:disruption2021:2021-2025",
        "apc_a05_autism_estab": "a05_entry:strict_autism:estab:none:2021-2025",
        "apc_a05_autism_count": "a05_entry:strict_autism:count:none:2021-2025",
        "apc_a05_autism_stable_pop": "a05_entry:strict_autism:stable_pop:none:2021-2025",
        "apc_a05_autism_ageadj_total": "a05_entry:strict_autism:TOTAL:age_adjusted:2021-2025",
        "apc_a05_autism_ageadj_male": "a05_entry:strict_autism:HOMBRE:age_adjusted:2021-2025",
        "apc_a05_autism_ageadj_female": "a05_entry:strict_autism:MUJER:age_adjusted:2021-2025",
        "apc_a05_autism_exit_pop": "a05_exit:strict_autism:pop:none:2021-2025",
        "apc_a05_autism_exit_estab": "a05_exit:strict_autism:estab:none:2021-2025",
        "apc_a05_autism_exit_stable_pop": "a05_exit:strict_autism:stable_pop:none:2021-2025",
        "apc_a05_family_pop": f"a05_entry:{v}:pop:none:2021-2025",
        "apc_a05_family_pop_2022_2025": f"a05_entry:{v}:pop:none:2022-2025",
        "apc_a05_family_estab": f"a05_entry:{v}:estab:none:2021-2025",
        "apc_a05_family_stable_pop": f"a05_entry:{v}:stable_pop:none:2021-2025",
        "apc_a05_family_ageadj_total": f"a05_entry:{v}:TOTAL:age_adjusted:2021-2025",
        "apc_a05_family_ageadj_male": f"a05_entry:{v}:HOMBRE:age_adjusted:2021-2025",
        "apc_a05_family_ageadj_female": f"a05_entry:{v}:MUJER:age_adjusted:2021-2025",
        "apc_a05_family_exit_pop": f"a05_exit:{v}:pop:none:2021-2025",
        "apc_a05_family_exit_estab": f"a05_exit:{v}:estab:none:2021-2025",
        # P2 / P6
        "apc_p2_dec": "p2_dec:none:2019-2025",
        "apc_p2_dec_estab": "p2_dec:estab:2019-2025",
        "apc_p2_dec_stable": "p2_dec:stable:2019-2025",
        "apc_p2_dec_disruption": "p2_dec:none_disruption:2019-2025",
        "apc_p2_dec_estab_disruption": "p2_dec:estab_disruption:2019-2025",
        "apc_p2_dec_2021_2025": "p2_dec:none:2021-2025",
        "apc_p2_dec_estab_2021_2025": "p2_dec:estab:2021-2025",
        "apc_p2_dec_2022_2025": "p2_dec:none:2022-2025",
        "apc_p2_dec_estab_2022_2025": "p2_dec:estab:2022-2025",
        "apc_p2_jun_disruption": "p2_jun:none_disruption:2019-2025",
        "apc_p2_jun_estab_2021_2025": "p2_jun:estab:2021-2025",
        "apc_p2_dec_naneas_offset": "p2_dec:naneas:2023-2025",
        "apc_p6_primary_autism": "p6_primary:strict_autism:none:2021-2025",
        "apc_p6_primary_autism_estab": "p6_primary:strict_autism:estab:2021-2025",
        "apc_p6_primary_autism_stable": "p6_primary:strict_autism:stable:2021-2025",
        "apc_p6_primary_family": f"p6_primary:{v}:none:2021-2025",
        "apc_p6_primary_family_estab": f"p6_primary:{v}:estab:2021-2025",
        "apc_p6_primary_family_stable": f"p6_primary:{v}:stable:2021-2025",
        "apc_p6_specialty_autism": "p6_specialty:strict_autism:none:2021-2025",
        "apc_p6_specialty_autism_estab": "p6_specialty:strict_autism:estab:2021-2025",
        "apc_p6_specialty_autism_stable": "p6_specialty:strict_autism:stable:2021-2025",
        "apc_p6_specialty_family": f"p6_specialty:{v}:none:2021-2025",
        "apc_p6_specialty_family_estab": f"p6_specialty:{v}:estab:2021-2025",
        "apc_p6_specialty_family_stable": f"p6_specialty:{v}:stable:2021-2025",
        # educación y DEIS
        "apc_pie_harmonised": "pie_harmonised:none:2019-2025",
        "apc_pie_harmonised_2019_2023": "pie_harmonised:none:2019-2023",
        "apc_pie_harmonised_2021_2025": "pie_harmonised:none:2021-2025",
        "apc_pie_harmonised_disruption": "pie_harmonised:disruption:2019-2025",
        "apc_pie_tea_strict": "pie_tea_strict_n:none:2019-2023",
        "apc_pie_tea_asperger": "pie_tea_asperger_n:none:2019-2023",
        "apc_deis_principal": f"deis_principal:{v}:none:2019-2024",
        "apc_deis_principal_2021_2024": f"deis_principal:{v}:none:2021-2024",
        "apc_deis_principal_disruption": f"deis_principal:{v}:disruption:2019-2024",
    }


def _models(V: dict, variant: str) -> None:
    m = _tidy("models_summary")
    V["src_models"] = "outputs/tidy/models_summary.csv"
    keep = m[m.variant.isin([variant, "strict_autism_f840", "strict_autism", "both"])]
    V["models_n_total_file"] = int(len(m))
    V["models_n_variant"] = int(len(keep))
    V["models_n_converged"] = int(keep.converged.sum())
    V["models_n_encoding_law"] = int(m.model_id.str.contains("law|its|intervention", case=False).sum())
    by_id = keep.set_index("model_id")
    # clave neutra respecto de la variante (":con_rett:" → ":variant:") para que ambas variantes compartan claves
    for mid, r in by_id.iterrows():
        kid = mid.replace(f":{variant}:", ":variant:")
        V[f"mdl__{kid}__model_id"] = mid
        for f in _MODEL_FIELDS:
            val = r[f]
            V[f"mdl__{kid}__{f}"] = _str(val) if f in ("years", "model_family", "covariates", "panel", "activity", "position", "denominator_offset", "outcome", "sex", "note_keys") else (_int(val) if f in ("n_obs", "stable_panel_n", "hospitals_first", "hospitals_last") else _flt(val))
    missing = []
    for alias, mid in _alias_table(variant).items():
        if mid not in by_id.index:
            missing.append(mid)
            V[alias] = None
            continue
        r = by_id.loc[mid]
        V[alias] = _flt(r.apc)
        V[f"{alias}_lo"] = _flt(r.apc_lo)
        V[f"{alias}_hi"] = _flt(r.apc_hi)
        V[f"{alias}_p"] = _flt(r.p_value)
        V[f"{alias}_disp"] = _flt(r.dispersion)
        V[f"{alias}_dw"] = _flt(r.durbin_watson)
        V[f"{alias}_n"] = _int(r.n_obs)
        V[f"{alias}_years"] = _str(r.years)
        V[f"{alias}_model_id"] = mid
        V[f"{alias}_family"] = _str(r.model_family)
        if not _isnan(r.depth_coef):
            V[f"{alias}_depth_coef"] = _flt(r.depth_coef)
            V[f"{alias}_depth_rr_per_diagnosis"] = float(np.exp(r.depth_coef))
        if not _isnan(r.re_sd):
            V[f"{alias}_re_sd"] = _flt(r.re_sd)
            V[f"{alias}_re_sd_lo"] = _flt(r.re_sd_lo)
            V[f"{alias}_re_sd_hi"] = _flt(r.re_sd_hi)
            V[f"{alias}_re_sd_rr_95_range"] = float(np.exp(1.96 * r.re_sd))
        if not _isnan(r.stable_panel_n):
            V[f"{alias}_stable_panel_n"] = _int(r.stable_panel_n)
    V["models_aliases_missing"] = "; ".join(missing) if missing else None
    # rango de sensibilidades GRD (cualquier posición, 2019–2024, todas las especificaciones cuasi-Poisson nacionales)
    gs = keep[(keep.estimand == "est_grd_rate") & (keep.variant == variant) & (keep.outcome == "out_f84_any") & (keep.years == "2019-2024")]
    V["apc_grd_any_sensitivity_min"] = _flt(gs.apc.min())
    V["apc_grd_any_sensitivity_max"] = _flt(gs.apc.max())
    V["apc_grd_any_sensitivity_n_specs"] = int(len(gs))
    gp = keep[(keep.estimand == "est_grd_rate") & (keep.variant == variant) & (keep.outcome == "out_f84_principal") & (keep.years == "2019-2024") & (keep.covariates != "cov_depth_disruption")]
    V["apc_grd_principal_sensitivity_min"] = _flt(gp.apc.min())
    V["apc_grd_principal_sensitivity_max"] = _flt(gp.apc.max())
    V["apc_grd_principal_sensitivity_n_specs"] = int(len(gp))
    V["models_note"] = "Quasi-Poisson log-linear models with the stated offset; APC = 100·(exp(β)−1) with Wald 95% CI; dispersion = Pearson χ²/df; Durbin–Watson on deviance residuals is weak with < 8 points; no model encodes Law 21.545 as an intervention; the 2020–2021 indicator describes reporting disruption"

    conv = _tidy("models_convergence_index")
    V["src_convergence_index"] = "outputs/tidy/models_convergence_index.csv"
    for r in conv[conv.variant == variant].itertuples():
        V[f"conv_{r.series}_index{r.index_base_year}_{r.year}"] = _flt(r.index)
        V[f"conv_{r.series}_value_{r.year}"] = _flt(r.value)
    V["conv_note"] = _str(conv.note.iloc[0])


# ---------------------------------------------------------------------------
# Controles (07) y procedencia (00)
# ---------------------------------------------------------------------------
def _controls(V: dict) -> None:
    c = pd.read_csv(CONTROLS_DIR / "controls_summary.csv")
    # El consolidado trae DOS ámbitos con nombre (columna `scope`), que cuentan cosas distintas y no se suman:
    # `pipeline` = una fila por control de cada <módulo>_controls.csv; `analysis_plan` = una fila por control
    # indicador-año del plan. Las claves controls_csv_* son SIEMPRE las del ámbito `pipeline`; las del plan
    # llevan el prefijo controls_plan_* y las de la T8 el prefijo t8_. Ver lancet_americas/controls_registry.py.
    if "scope" in c.columns:
        plan = c[c.scope == "analysis_plan"]
        c = c[c.scope == "pipeline"]
        V["controls_plan_rows"] = int(len(plan))
        for st in ("ok", "info", "differs"):
            V[f"controls_plan_{st}"] = int((plan.status == st).sum())
    V["src_controls"] = "outputs/controls/controls_summary.csv"
    V["controls_csv_scope"] = "pipeline"
    V["controls_csv_rows"] = int(len(c))
    for st, n in c.status.value_counts().items():
        V[f"controls_csv_{st}"] = int(n)
    for st in ("ok", "info", "differs"):
        V.setdefault(f"controls_csv_{st}", 0)
    for (mod, st), n in c.groupby(["module", "status"]).size().items():
        V[f"controls_csv_{_slug(mod)}_{st}"] = int(n)
    diff = c[c.status == "differs"]
    V["controls_csv_differs_names"] = "; ".join(sorted(set(f"{r.module}:{r.name}:{r.key}" for r in diff.itertuples())))
    V["controls_csv_modules_n"] = int(c.module.nunique())
    total_files = 0
    for p in sorted(CONTROLS_DIR.glob("*_controls.csv")):
        n = len(pd.read_csv(p))
        total_files += n
        V[f"controls_file_rows_{_slug(p.stem.replace('_controls', ''))}"] = int(n)
    V["controls_files_rows_total"] = int(total_files)
    V["controls_files_n"] = int(len(list(CONTROLS_DIR.glob("*_controls.csv"))))
    t8 = OUT / "con_rett" / "en" / "tables" / "T8_controls_numeric.csv"
    if t8.is_file():
        t = pd.read_csv(t8)
        V["src_t8_controls"] = "outputs/con_rett/en/tables/T8_controls_numeric.csv"
        V["t8_rows"] = int(len(t))
        for st, n in t.status.value_counts().items():
            V[f"t8_{st}"] = int(n)
        V["t8_control_families_n"] = int(t.config_key.nunique()) if "config_key" in t.columns else None
    V["controls_families_prespecified_n"] = int(len(CFG.CONTROLS))
    V["controls_note"] = "ok = exact equality (counts) or relative difference ≤ 0.5% (means/proportions); all 'differs' rows are explained (strict hospitalisation 2023–2024 = fixed-65 panel in the brief vs observed panel; persons within year exclude placeholder identifiers; one duplicate pair on read columns in 2020; one additive REM-20 duplicate row)"
    # controles clave preespecificados (valores esperados del protocolo)
    for y, v in CFG.CONTROLS["grd_f84_any"].items():
        V[f"control_expected_grd_f84_any_{y}"] = int(v)
    for y, v in CFG.CONTROLS["grd_f84_any_strict_hospitalisation"].items():
        V[f"control_expected_grd_strict_hosp_{y}"] = int(v)
    for y, v in CFG.CONTROLS["grd_persons_within_year_f84_any"].items():
        V[f"control_expected_grd_persons_{y}"] = int(v)
    V["control_expected_grd_secondary_only_share_2024"] = float(CFG.CONTROLS["grd_f84_secondary_only_share_2024"])
    V["control_expected_grd_coding_depth_all_2019"] = float(CFG.CONTROLS["grd_coding_depth_all_mean"][2019])
    V["control_expected_grd_coding_depth_all_2024"] = float(CFG.CONTROLS["grd_coding_depth_all_mean"][2024])


def _provenance(V: dict) -> None:
    p = _tidy("data_provenance")
    V["src_provenance"] = "outputs/tidy/data_provenance.csv"
    V["prov_artefacts_n"] = int(len(p))
    V["prov_bytes_total"] = int(p.bytes.sum())
    V["prov_gb_total"] = float(p.bytes.sum() / 1e9)
    V["prov_gib_total"] = float(p.bytes.sum() / 2 ** 30)
    V["prov_sources_n"] = int(p.source_id.nunique())
    V["prov_sha_match_n"] = int((p.sha256_matches_manifest.astype(str) == "True").sum())
    V["prov_sha_mismatch_n"] = int((p.sha256_matches_manifest.astype(str) == "False").sum())
    V["prov_not_listed_n"] = int((p.sha256_matches_manifest.astype(str) == "not_listed").sum())
    for role, n in p.artefact_role.value_counts().items():
        V[f"prov_role_{_slug(role)}_n"] = int(n)
    V["prov_data_artefacts_n"] = int((p.artefact_role == "data").sum())
    ps = _tidy("provenance_summary_by_source")
    for r in ps.itertuples():
        V[f"prov_{r.source_id}_n"] = _int(r.n_artefacts)
        V[f"prov_{r.source_id}_bytes"] = _int(r.bytes_total)
        V[f"prov_{r.source_id}_gb"] = _flt(r.gb)
        V[f"prov_{r.source_id}_sha_match_n"] = _int(r.n_sha_match)
    mc = _tidy("provenance_manifest_checks")
    V["prov_manifest_checks_n"] = int(len(mc))
    for st, n in mc.sha256_match.astype(str).value_counts().items():
        V[f"prov_manifest_sha_{_slug(st)}_n"] = int(n)
    V["prov_manifests_n"] = int(mc.manifest.nunique())
    for r in p[p.source_id.isin(["grd_publico", "rem_serie_a", "rem_serie_p", "deis_egresos"])].itertuples():
        V[f"prov_sha256_{_slug(r.relative_path)}"] = _str(r.sha256)
        V[f"prov_bytes_{_slug(r.relative_path)}"] = _int(r.bytes)
    V["prov_data_root"] = str(CFG.DATA_ROOT)
    V["prov_note"] = "SHA-256 computed over each artefact; source databases are never copied into the repository"


# ---------------------------------------------------------------------------
# Meta y salidas gráficas
# ---------------------------------------------------------------------------
def _meta(V: dict, variant: str) -> None:
    V["variant"] = variant
    V["variant_other"] = "sin_rett" if variant == "con_rett" else "con_rett"
    V["variant_label_en"] = CFG.VARIANTS[variant]["label"]["en"]
    V["variant_label_es"] = CFG.VARIANTS[variant]["label"]["es"]
    V["variant_short_en"] = CFG.VARIANTS[variant]["short"]["en"]
    V["variant_short_es"] = CFG.VARIANTS[variant]["short"]["es"]
    V["variant_grd_subcodes"] = ", ".join(CFG.VARIANTS[variant]["grd_subcodes"])
    V["variant_includes_f842"] = "F842" in CFG.VARIANTS[variant]["grd_subcodes"]
    V["years_grd_first"], V["years_grd_last"] = YEARS_GRD[0], YEARS_GRD[-1]
    V["years_rem_first"], V["years_rem_last"] = YEARS_REM[0], YEARS_REM[-1]
    V["years_a05_autism_first"] = 2021
    V["years_a27_a28_first"] = 2023
    V["law_year"] = CFG.LAW_YEAR
    V["law_date"] = "2023-03-10"
    V["pandemic_years"] = ", ".join(str(y) for y in CFG.PANDEMIC_YEARS)
    V["strict_autism_code_a05_entry"] = CFG.STRICT["a05_entry"]
    V["strict_autism_code_a05_exit"] = CFG.STRICT["a05_exit"]
    V["strict_autism_code_p6_primary"] = CFG.STRICT["p6_primary"]
    V["strict_autism_code_p6_specialty"] = CFG.STRICT["p6_specialty"]
    V["p2_tea_code"] = CFG.P2_TEA
    V["p2_naneas_total_code"] = CFG.P2_NANEAS_TOTAL
    V["a27_codes"] = ", ".join(f"{k}={v}" for k, v in CFG.A27.items())
    V["a28_codes"] = ", ".join(f"{k}={v}" for k, v in CFG.A28.items())
    V["grd_diagnosis_positions"] = 35
    V["rem_pathway_codes_n"] = 57
    for lang in ("en", "es"):
        fdir = OUT / variant / lang / "figures"
        tdir = OUT / variant / lang / "tables"
        if fdir.is_dir():
            figs = sorted(p.name for p in fdir.glob("*.png"))
            V[f"n_figures_main_{lang}"] = len([f for f in figs if re.match(r"fig\d+_", f)])
            V[f"n_figures_supp_files_{lang}"] = len([f for f in figs if f.startswith("figS")])
        if tdir.is_dir():
            tabs = sorted(p.name for p in tdir.glob("*.csv") if not p.name.endswith("_numeric.csv"))
            V[f"n_tables_main_{lang}"] = len([t for t in tabs if re.match(r"T\d+_", t)])
            V[f"n_tables_supp_files_{lang}"] = len([t for t in tabs if t.startswith("S")])


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def values(variant: str = "con_rett") -> dict:
    """Diccionario plano de todas las cantidades citables para la variante (`con_rett` | `sin_rett`)."""
    if variant not in CFG.VARIANTS:
        raise ValueError(f"Variante desconocida: {variant}")
    V: dict = {}
    _meta(V, variant)
    _grd(V, variant)
    _deis(V, variant)
    _rem(V, variant)
    _denominators(V)
    _surveys(V)
    _education(V)
    _models(V, variant)
    _controls(V)
    _provenance(V)
    # normalización final: tipos JSON nativos, NaN → None
    clean = {}
    for k, v in V.items():
        if isinstance(v, (np.integer,)):
            v = int(v)
        elif isinstance(v, (np.floating,)):
            v = None if not math.isfinite(float(v)) else float(v)
        elif isinstance(v, (np.bool_,)):
            v = bool(v)
        elif isinstance(v, float) and not math.isfinite(v):
            v = None
        clean[k] = v
    return clean


def write_values(variant: str) -> Path:
    path = OUT / f"values_{variant}.json"
    atomic_write_json(values(variant), path)
    return path


def diff_variants() -> dict:
    a, b = values("con_rett"), values("sin_rett")
    shared = sorted(set(a) & set(b))
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = {k: {"con_rett": a[k], "sin_rett": b[k]} for k in shared if a[k] != b[k]}
    prefixes = {}
    for k in diff:
        pref = k.split("_")[0] if not k.startswith("mdl__") else "mdl"
        prefixes[pref] = prefixes.get(pref, 0) + 1
    out = {"_meta": {"n_keys_con_rett": len(a), "n_keys_sin_rett": len(b), "n_keys_shared": len(shared), "n_keys_differ": len(diff),
                     "n_keys_only_con_rett": len(only_a), "n_keys_only_sin_rett": len(only_b),
                     "n_differ_by_prefix": dict(sorted(prefixes.items())),
                     "note": "Quantities (shared keys) whose value differs between the full-F84 (con_rett) and F84-without-Rett (sin_rett) analyses; "
                             "strict autism (REM 05990022 / P6241010 / P6241060), F84.0-only checks, A03/A27/A28/P2, education, surveys, "
                             "denominators and controls are identical by construction. Keys present in one variant only are listed separately."},
           "keys_only_con_rett": only_a, "keys_only_sin_rett": only_b, "differences": diff}
    atomic_write_json(out, OUT / "values_diff_variants.json")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", choices=VARIANTS + ["all"], default="all")
    args = ap.parse_args(argv)
    variants = VARIANTS if args.variant == "all" else [args.variant]
    for v in variants:
        path = write_values(v)
        n = len(json.loads(path.read_text(encoding="utf-8")))
        print(f"{path} — {n} claves")
    if args.variant == "all":
        d = diff_variants()
        print(f"{OUT / 'values_diff_variants.json'} — {d['_meta']['n_keys_differ']} claves difieren de {d['_meta']['n_keys_shared']} compartidas; solo con_rett {d['_meta']['n_keys_only_con_rett']}, solo sin_rett {d['_meta']['n_keys_only_sin_rett']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
