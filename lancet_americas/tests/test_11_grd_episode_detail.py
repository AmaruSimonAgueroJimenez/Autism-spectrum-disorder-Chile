# -*- coding: utf-8 -*-
"""Pruebas del módulo 11 (detalle episódico GRD).

No leen los GRD crudos: verifican la coherencia interna de las tablas tidy ya escritas y la equivalencia
de los dos estimadores de distribución sobre datos sintéticos. Si las tablas no existen todavía, las
pruebas que dependen de ellas se omiten con un mensaje explícito.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

LANCET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANCET))
import config as CFG  # noqa: E402

_spec = importlib.util.spec_from_file_location("mod11", LANCET / "pipeline" / "11_grd_episode_detail.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

TABLES = ["grd_monthly", "grd_length_of_stay", "grd_los_age", "grd_episode_features", "grd_grd_weight",
          "grd_codiagnoses", "grd_codiagnosis_chapters", "grd_readmission", "grd_multiplicity",
          "grd_territory", "grd_age_single_year"]


def load(name: str) -> pd.DataFrame | None:
    path = CFG.TIDY / f"{name}.csv"
    return pd.read_csv(path) if path.is_file() else None


class DistributionStatisticsTest(unittest.TestCase):
    """`dist_stats` (distribución de frecuencias, grupo de comparación) = `series_stats` (valores directos, series F84)."""

    def test_agreement(self):
        rng = np.random.default_rng(11)
        for size, high in ((37, 4), (5000, 60), (100_000, 900)):
            values = pd.Series(rng.integers(0, high, size=size), dtype=float)
            counts = values.value_counts().sort_index()
            direct = M.series_stats(values)
            weighted = M.dist_stats(counts.index.to_numpy(dtype=float), counts.to_numpy())
            for key in ("n", "mean", "sd", "median", "q25", "q75", "p90", "max", "total_days", "n_zero"):
                self.assertAlmostEqual(direct[key], weighted[key], places=8, msg=f"{key} con n={size}")

    def test_empty_distribution(self):
        stats = M.dist_stats(np.array([]), np.array([]))
        self.assertEqual(stats["n"], 0)
        self.assertTrue(np.isnan(stats["median"]))


class TidyOutputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = {name: load(name) for name in TABLES}
        cls.summary = load("grd_year_summary")
        cls.dictionary = load("grd_episode_detail_dictionary")

    def require(self, *names):
        for name in names:
            if self.tables.get(name) is None:
                self.skipTest(f"falta outputs/tidy/{name}.csv; ejecute pipeline/11_grd_episode_detail.py")

    # Tablas que llevan el grupo de comparación de todos los episodios GRD como filas propias.
    # En `grd_monthly` la comparación es la columna `n_episodes_total`, no una fila.
    WITH_COMPARISON = {"grd_length_of_stay", "grd_los_age", "grd_episode_features", "grd_territory",
                       "grd_age_single_year"}

    def test_every_table_has_variant_and_unit_columns(self):
        self.require(*TABLES)
        for name, df in self.tables.items():
            for column in ("variant", "unit", "denominator", "script"):
                self.assertIn(column, df.columns, f"{name} sin columna {column}")
            variants = set(df.variant)
            for variant in ("con_rett", "sin_rett", "strict_autism_f840"):
                self.assertIn(variant, variants, name)
            self.assertEqual("all_episodes" in variants, name in self.WITH_COMPARISON, name)

    def test_dictionary_covers_every_table(self):
        self.require(*TABLES)
        if self.dictionary is None:
            self.skipTest("falta grd_episode_detail_dictionary.csv")
        self.assertEqual(set(self.dictionary.table), set(TABLES))
        for column in ("unit_definition", "denominator_definition", "coverage", "definition_era", "source_files"):
            self.assertTrue(self.dictionary[column].astype(str).str.len().gt(20).all(), column)

    def test_monthly_sum_equals_module_01_annual_totals(self):
        self.require("grd_monthly")
        if self.summary is None:
            self.skipTest("falta grd_year_summary.csv (módulo 01)")
        monthly = self.tables["grd_monthly"]
        ref = self.summary.loc[self.summary.activity == "all"]
        merged = (monthly.groupby(["year", "variant", "position", "panel"], as_index=False)["n_episodes_f84"].sum()
                  .merge(ref[["year", "variant", "position", "panel", "n_episodes_f84"]],
                         on=["year", "variant", "position", "panel"], suffixes=("_monthly", "_module01")))
        self.assertGreater(len(merged), 100)
        pd.testing.assert_series_equal(merged.n_episodes_f84_monthly, merged.n_episodes_f84_module01,
                                       check_names=False)

    def test_protocol_controls_reproduced(self):
        self.require("grd_monthly")
        monthly = self.tables["grd_monthly"]
        primary = monthly.loc[(monthly.variant == "con_rett") & (monthly.panel == "observed")]
        for position, key in (("any", "grd_f84_any"), ("principal", "grd_f84_principal")):
            observed = primary.loc[primary.position == position].groupby("year")["n_episodes_f84"].sum()
            for year, expected in CFG.CONTROLS[key].items():
                self.assertEqual(int(observed.get(year, -1)), expected, f"{key} {year}")
        fixed = monthly.loc[(monthly.variant == "con_rett") & (monthly.panel == "fixed65") & (monthly.position == "any")]
        observed = fixed.groupby("year")["n_episodes_f84"].sum()
        for year, expected in CFG.CONTROLS["grd_f84_any_panel65"].items():
            self.assertEqual(int(observed.get(year, -1)), expected, f"grd_f84_any_panel65 {year}")

    def test_seasonal_index_averages_one(self):
        self.require("grd_monthly")
        monthly = self.tables["grd_monthly"]
        real = monthly.loc[monthly.month.between(1, 12) & monthly.seasonal_index_f84.notna()]
        means = real.groupby(["year", "variant", "position", "panel"])["seasonal_index_f84"].mean()
        # el índice se redondea a 4 decimales al escribirse; la media de los 12 meses es 1 salvo ese redondeo
        self.assertEqual(set(real.groupby(["year", "variant", "position", "panel"]).size()), {12})
        self.assertTrue(np.allclose(means.to_numpy(), 1.0, atol=1e-4))
        self.assertTrue(monthly.loc[monthly.month == 0, "seasonal_index_f84"].isna().all())

    def test_features_and_age_sum_to_cell_total(self):
        self.require("grd_episode_features", "grd_age_single_year")
        features = self.tables["grd_episode_features"]
        summed = features.groupby(["year", "variant", "position", "panel", "variable"], as_index=False).agg(
            observed=("n_episodes", "sum"), expected=("n_cell_total", "first"))
        self.assertTrue((summed.observed == summed.expected).all())
        age = self.tables["grd_age_single_year"]
        summed = age.groupby(["year", "variant", "position", "panel"], as_index=False).agg(
            observed=("n_episodes", "sum"), expected=("n_cell_total", "first"))
        self.assertTrue((summed.observed == summed.expected).all())

    def test_codiagnoses_never_exceed_episodes_times_35(self):
        self.require("grd_codiagnoses")
        codiag = self.tables["grd_codiagnoses"]
        self.assertFalse(codiag.code3.str.startswith("F84").any(), "los propios códigos F84 deben excluirse")
        for position in ("principal", "secondary", "any"):
            block = codiag.loc[codiag.code_position == position]
            summed = block.groupby(["year", "variant", "position", "panel"], as_index=False).agg(
                total=("n_episodes", "sum"), episodes=("n_f84_episodes_cell", "first"))
            self.assertTrue((summed.total <= summed.episodes * M.MAX_DIAG_FIELDS).all(), position)
        # un episodio cuenta una vez por categoría: ningún recuento supera los episodios de la celda
        self.assertTrue((codiag.n_episodes <= codiag.n_f84_episodes_cell).all())

    def test_length_of_stay_is_internally_consistent(self):
        self.require("grd_length_of_stay", "grd_los_age")
        los = self.tables["grd_length_of_stay"]
        valid = los.loc[los.n_valid_dates > 0]
        self.assertTrue((valid.q25_days <= valid.median_days).all())
        self.assertTrue((valid.median_days <= valid.q75_days).all())
        self.assertTrue((valid.q75_days <= valid.p90_days).all())
        self.assertTrue((valid.p90_days <= valid.max_days).all())
        self.assertTrue((valid.n_los_zero <= valid.n_valid_dates).all())
        by_age = self.tables["grd_los_age"]
        keys = ["year", "variant", "position", "panel", "activity"]
        merged = (by_age.groupby(keys, as_index=False)["n_valid_dates"].sum()
                  .merge(los[keys + ["n_valid_dates"]], on=keys, suffixes=("_by_age", "_total")))
        self.assertGreater(len(merged), 100)
        self.assertTrue((merged.n_valid_dates_by_age == merged.n_valid_dates_total).all())

    def test_readmission_counts_are_nested(self):
        self.require("grd_readmission")
        readm = self.tables["grd_readmission"]
        self.assertTrue((readm.n_readmitted_f84 <= readm.n_readmitted_any_cause).all())
        self.assertTrue((readm.n_readmitted_any_cause <= readm.n_eligible).all())
        self.assertTrue((readm.n_eligible <= readm.n_discharges).all())
        self.assertEqual(set(readm.era), set(M.ERAS))
        # la elegibilidad decrece con el horizonte (hay que tener el seguimiento completo dentro de la era),
        # por eso los reingresos observados a 365 días pueden ser MENOS que a 90: las columnas no son comparables
        # entre sí sin fijar el conjunto elegible, y así se advierte en la nota de la tabla.
        wide = readm.pivot_table(index=["era", "year", "variant", "position", "panel"], columns="horizon_days",
                                 values="n_eligible")
        self.assertTrue(((wide[30] >= wide[90]) & (wide[90] >= wide[365])).all())

    def test_multiplicity_totals(self):
        self.require("grd_multiplicity")
        mult = self.tables["grd_multiplicity"]
        summed = mult.groupby(["era", "variant", "position", "panel"], as_index=False).agg(
            persons=("n_persons", "sum"), persons_total=("n_persons_total", "first"),
            episodes=("n_episodes", "sum"), episodes_total=("n_episodes_total", "first"))
        self.assertTrue((summed.persons == summed.persons_total).all())
        self.assertTrue((summed.episodes == summed.episodes_total).all())
        self.assertTrue((mult.n_episodes >= mult.n_persons).all())

    def test_territory_suppression_and_totals(self):
        self.require("grd_territory", "grd_monthly")
        terr = self.tables["grd_territory"]
        flagged = terr.n_episodes.between(1, M.SUPPRESSION_THRESHOLD - 1)
        pd.testing.assert_series_equal(terr.suppression_flag.astype(bool), flagged, check_names=False)
        self.assertTrue((terr.loc[terr.suppression_flag, "n_episodes_display"] == "<5").all())
        self.assertTrue((terr.n_persons_within_year.dropna() <= terr.loc[terr.n_persons_within_year.notna(), "n_episodes"]).all())
        monthly = self.tables["grd_monthly"]
        keys = ["year", "variant", "position", "panel"]
        comuna = terr.loc[terr.level == "comuna"].groupby(keys, as_index=False)["n_episodes"].sum()
        annual = monthly.groupby(keys, as_index=False)["n_episodes_f84"].sum()
        merged = comuna.merge(annual, on=keys)
        self.assertGreater(len(merged), 100)
        self.assertTrue((merged.n_episodes == merged.n_episodes_f84).all())

    def test_variants_are_nested(self):
        self.require("grd_monthly")
        monthly = self.tables["grd_monthly"]
        wide = monthly.loc[(monthly.position == "any") & (monthly.panel == "observed")].pivot_table(
            index="year", columns="variant", values="n_episodes_f84", aggfunc="sum")
        self.assertTrue((wide["sin_rett"] <= wide["con_rett"]).all())
        self.assertTrue((wide["strict_autism_f840"] <= wide["sin_rett"]).all())


if __name__ == "__main__":
    unittest.main()
