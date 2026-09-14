"""Pruebas de los estimadores compartidos del pipeline del estudio (datos sintéticos)."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as M  # noqa: E402


class SurveyProportionTest(unittest.TestCase):
    def synthetic(self, seed=7, n_strata=4, psu_per_stratum=12, n_per_psu=25, p=0.03):
        rng = np.random.default_rng(seed)
        rows = []
        for s in range(n_strata):
            for c in range(psu_per_stratum):
                effect = rng.normal(0, 0.01)
                for _ in range(n_per_psu):
                    rows.append(dict(strata=s, psu=f"{s}-{c}", w=rng.uniform(50, 150), y=int(rng.uniform() < p + effect), dom=int(rng.uniform() < .6)))
        return pd.DataFrame(rows)

    def test_point_estimate_equals_weighted_mean(self):
        d = self.synthetic()
        res = M.survey_proportion(d, "y", "w", "strata", "psu")
        naive = np.average(d.y, weights=d.w)
        self.assertAlmostEqual(res["proportion"], naive, places=12)
        self.assertGreater(res["se"], 0)
        self.assertLess(res["lo"], res["proportion"])
        self.assertGreater(res["hi"], res["proportion"])
        self.assertEqual(res["n_psu"], 48)
        self.assertEqual(res["n_strata"], 4)

    def test_domain_estimate_keeps_all_units_and_matches_bootstrap(self):
        d = self.synthetic(seed=11)
        res = M.survey_proportion(d, "y", "w", "strata", "psu", domain=d.dom)
        sub = d.loc[d.dom == 1]
        self.assertAlmostEqual(res["proportion"], np.average(sub.y, weights=sub.w), places=12)
        self.assertEqual(res["n_domain"], int(d.dom.sum()))
        rng = np.random.default_rng(3)
        boots = []
        groups = {k: g for k, g in d.groupby("strata")}
        for _ in range(300):
            parts = []
            for s, g in groups.items():
                psus = g.psu.unique()
                pick = rng.choice(psus, size=len(psus), replace=True)
                parts.append(pd.concat([g.loc[g.psu == p_] for p_ in pick]))
            b = pd.concat(parts)
            bs = b.loc[b.dom == 1]
            boots.append(np.average(bs.y, weights=bs.w))
        self.assertLess(abs(np.std(boots, ddof=1) - res["se"]) / res["se"], 0.35)

    def test_zero_cases_are_handled(self):
        d = self.synthetic(seed=5)
        d["y"] = 0
        res = M.survey_proportion(d, "y", "w", "strata", "psu")
        self.assertEqual(res["proportion"], 0.0)
        self.assertEqual(res["n_cases"], 0)


class TrendTest(unittest.TestCase):
    def test_quasi_poisson_recovers_exponential_growth(self):
        years = np.arange(2019, 2025)
        offsets = np.full(len(years), 1_000_000.0)
        counts = 100 * np.exp(0.4 * (years - 2019))
        res = M.quasi_poisson_trend(years, counts, offsets)
        self.assertAlmostEqual(res["apc"], 100 * (np.exp(0.4) - 1), places=4)
        self.assertLessEqual(res["apc_lo"], res["apc"])
        self.assertGreaterEqual(res["apc_hi"], res["apc"])


class AtomicWriteTest(unittest.TestCase):
    def test_atomic_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            M.atomic_write_csv(pd.DataFrame({"a": [1, 2]}), path)
            self.assertEqual(pd.read_csv(path).a.tolist(), [1, 2])
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["x.csv"])

    def test_formatting(self):
        self.assertEqual(M.fmt_number(1234.5, 1, "es"), "1.234,5")
        self.assertEqual(M.fmt_number(1234.5, 1, "en"), "1,234.5")
        self.assertEqual(M.fmt_p(0.0004, "en"), "< 0.001")
        self.assertEqual(M.fmt_ci(1.2, 3.4, 1, "es"), "1,2 a 3,4")


class YearSpanTest(unittest.TestCase):
    """`yspan`: la ventana de años pasa a raya corta AL ROTULAR, y sólo la ventana de años.

    El guion ASCII es la forma de máquina —viaja por el tidy, por las claves `comparison`/`years` y por los
    nombres de archivo— y la raya corta es la forma impresa, que es la que usa el resto del corpus. Lo que
    guardan estas comprobaciones es el LÍMITE: que la conversión no muerda un identificador ni un negativo.
    """

    def test_converts_a_year_window(self):
        self.assertEqual(M.yspan("2019-2021"), "2019\u20132021")
        self.assertEqual(M.yspan("2019-2021 vs 2022-2025"), "2019\u20132021 vs 2022\u20132025")
        self.assertEqual(M.yspan("Smoothed ratio (EB) 2019-2021"), "Smoothed ratio (EB) 2019\u20132021")

    def test_leaves_machine_keys_and_negatives_alone(self):
        for intact in ("REM-20", "knn-4", "F84", "2019", "full period", "-5", "2019-20", "A05-2019"):
            with self.subTest(text=intact):
                self.assertEqual(M.yspan(intact), intact)

    def test_is_idempotent(self):
        once = M.yspan("2019-2021")
        self.assertEqual(M.yspan(once), once)

    def test_accepts_a_non_string(self):
        self.assertEqual(M.yspan(2019), "2019")


if __name__ == "__main__":
    unittest.main()
