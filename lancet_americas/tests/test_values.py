"""Pruebas de values.py: reproducción de controles del protocolo, planitud del diccionario y coherencia entre variantes."""
from pathlib import Path
import json
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import values as VAL  # noqa: E402

HAS_OUTPUTS = (CFG.TIDY / "grd_year_summary.csv").is_file() and (CFG.TIDY / "models_summary.csv").is_file()


@unittest.skipUnless(HAS_OUTPUTS, "requiere las tablas tidy del pipeline (módulos 01–07)")
class ValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = VAL.values("con_rett")
        cls.sin = VAL.values("sin_rett")

    def test_flat_and_json_native(self):
        for V in (self.con, self.sin):
            for k, v in V.items():
                self.assertIsInstance(k, str)
                self.assertTrue(v is None or isinstance(v, (int, float, str, bool)), f"{k}: {type(v)}")
                if isinstance(v, float):
                    self.assertTrue(math.isfinite(v), k)
            json.dumps(V)

    def test_protocol_controls_reproduced(self):
        V = self.con
        for y, n in CFG.CONTROLS["grd_f84_any"].items():
            self.assertEqual(V[f"grd_f84_any_n_{y}"], n)
        for y, n in CFG.CONTROLS["grd_f84_any_panel65"].items():
            self.assertEqual(V[f"grd_f84_any_fixed65_n_{y}"], n)
        for y, n in CFG.CONTROLS["grd_f84_any_strict_hospitalisation"].items():
            self.assertEqual(V[f"grd_f84_any_hosp_fixed65_n_{y}"], n)
        for y, n in CFG.CONTROLS["grd_f84_principal"].items():
            self.assertEqual(V[f"grd_f84_principal_n_{y}"], n)
        for y, n in CFG.CONTROLS["grd_cma"].items():
            self.assertEqual(V[f"grd_f84_any_cma_n_{y}"], n)
        for y, n in CFG.CONTROLS["grd_hospitals_observed"].items():
            self.assertEqual(V[f"grd_hospitals_observed_{y}"], n)
        self.assertAlmostEqual(V["grd_f84_secondary_only_share_2024"], CFG.CONTROLS["grd_f84_secondary_only_share_2024"], places=3)
        self.assertAlmostEqual(V["grd_coding_depth_all_mean_2019"], 4.39, places=2)
        self.assertAlmostEqual(V["grd_coding_depth_all_mean_2024"], 5.78, places=2)
        for y, n in CFG.CONTROLS["a05_autism_entries"].items():
            self.assertEqual(V[f"a05_autism_entries_{y}"], n)
            self.assertEqual(self.sin[f"a05_autism_entries_{y}"], n)
        for y, n in CFG.CONTROLS["a27_assisted_referral"].items():
            self.assertEqual(V[f"a27_assisted_referral_{y}"], n)
        for y, n in CFG.CONTROLS["a28_primary"].items():
            self.assertEqual(V[f"a28_primary_{y}"], n)
        for y, n in CFG.CONTROLS["p2_tea_december"].items():
            self.assertEqual(V[f"p2_tea_dec_{y}"], n)
        for y, n in CFG.CONTROLS["p2_establishments_december"].items():
            self.assertEqual(V[f"p2_tea_dec_estab_{y}"], n)
        for y, n in CFG.CONTROLS["p2_naneas_total_december"].items():
            self.assertEqual(V[f"p2_naneas_dec_{y}"], n)
        for y, n in CFG.CONTROLS["p6_primary_december"].items():
            key = f"p6_primary_broad_dec_{y}" if y < 2021 else f"p6_primary_autism_dec_{y}"
            self.assertEqual(V[key], n)
        for y, n in CFG.CONTROLS["pie_harmonised"].items():
            self.assertEqual(V[f"pie_harmonised_{y}"], n)
        for y, n in CFG.CONTROLS["pie_tea_strict"].items():
            self.assertEqual(V[f"pie_tea_strict_{y}"], n)
        for y, n in CFG.CONTROLS["ine_population_national"].items():
            self.assertEqual(V[f"ine_pop_total_{y}"], n)
        for y, n in CFG.CONTROLS["fonasa_beneficiaries_december"].items():
            self.assertEqual(V[f"fonasa_beneficiaries_{y}"], n)
        self.assertEqual(V["svy_endide_adults_reported_total_cases"], CFG.CONTROLS["endide_unweighted"]["adults"])
        self.assertEqual(V["svy_endide_children_reported_total_cases"], CFG.CONTROLS["endide_unweighted"]["children"])
        self.assertEqual(V["svy_encavi_15plus_diagnosed_total_cases"], CFG.CONTROLS["encavi_unweighted"]["positive"])
        self.assertEqual(V["pie_2022_discrepancy_cases"], 5)
        self.assertEqual(V["junaeb_medio1_all_estimable_2024"], "no")
        self.assertIsNone(V["junaeb_medio1_all_pct_weighted_2024"])

    def test_models_and_intervals(self):
        for V in (self.con, self.sin):
            self.assertIsNone(V["models_aliases_missing"])
            self.assertEqual(V["models_n_encoding_law"], 0)
            for alias in ("apc_grd_any_obs", "apc_grd_principal_obs", "apc_a05_autism_pop", "apc_p2_dec", "apc_pie_harmonised", "apc_deis_principal"):
                self.assertLess(V[f"{alias}_lo"], V[alias])
                self.assertGreater(V[f"{alias}_hi"], V[alias])
            self.assertLessEqual(V["grd_f84_any_rate_lo_2024"], V["grd_f84_any_rate_2024"])
            self.assertGreaterEqual(V["grd_f84_any_rate_hi_2024"], V["grd_f84_any_rate_2024"])

    def test_variants_share_invariant_series(self):
        for k in ("a05_autism_entries_2025", "p2_tea_dec_2025", "p6_primary_autism_dec_2025", "pie_harmonised_2025", "svy_encavi_15plus_diagnosed_total_prop",
                  "ine_pop_total_2025", "grd_f840_strict_any_n_2024", "grd_records_total_2024", "controls_csv_rows", "prov_artefacts_n"):
            self.assertEqual(self.con[k], self.sin[k], k)
        self.assertGreater(self.con["grd_f84_any_n_2024"], self.sin["grd_f84_any_n_2024"])
        self.assertEqual(self.con["grd_f84_any_n_2024"] - self.sin["grd_f84_any_n_2024"], self.con["grd_f84_any_n_rett_only_difference_2024"])
        self.assertTrue(self.con["variant_includes_f842"])
        self.assertFalse(self.sin["variant_includes_f842"])


if __name__ == "__main__":
    unittest.main()
