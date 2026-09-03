"""Unit checks for the epidemiological helpers (rates, standardisation, intervals, trends)."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from epi_helpers import (WHO_STANDARD, annual_percent_change, count_ratio, crude_rate, direct_standardization,
                         empirical_bayes_ratio, expected_counts, normalize_name, poisson_limits, rate_ratio,
                         standardized_ratio, summarise_rates)


class PoissonLimitsTest(unittest.TestCase):
    def test_exact_limits_match_reference_values(self):
        lower, upper = poisson_limits([0, 1, 10, 100])
        np.testing.assert_allclose(lower, [0.0, 0.0253, 4.795, 81.36], rtol=1e-2)
        np.testing.assert_allclose(upper, [3.689, 5.572, 18.39, 121.6], rtol=1e-2)

    def test_crude_rate_scales_by_population(self):
        table = crude_rate([50], [1_000_000])
        self.assertAlmostEqual(table.rate.iloc[0], 5.0)
        self.assertLess(table.rate_lo.iloc[0], 5.0)
        self.assertGreater(table.rate_hi.iloc[0], 5.0)


class StandardizationTest(unittest.TestCase):
    def frame(self, rate_per_group):
        return pd.DataFrame({"age_group": list(WHO_STANDARD), "population": 100_000.0,
                             "count": [rate_per_group * 1.0] * len(WHO_STANDARD)})

    def test_constant_rates_give_the_same_standardized_rate(self):
        result = direct_standardization(self.frame(20))
        self.assertAlmostEqual(result["asr"], 20.0, places=6)
        self.assertLess(result["asr_lo"], 20.0)
        self.assertGreater(result["asr_hi"], 20.0)

    def test_missing_groups_are_flagged_and_weights_renormalised(self):
        frame = self.frame(20).iloc[:5]
        result = direct_standardization(frame)
        self.assertEqual(result["groups_missing"], len(WHO_STANDARD) - 5)
        self.assertAlmostEqual(result["asr"], 20.0, places=6)

    def test_zero_cases_have_zero_lower_limit(self):
        result = direct_standardization(self.frame(0))
        self.assertEqual(result["asr"], 0.0)
        self.assertEqual(result["asr_lo"], 0.0)
        self.assertGreater(result["asr_hi"], 0.0)

    def test_summarise_rates_returns_one_row_per_key(self):
        frame = pd.concat([self.frame(10).assign(year=2019), self.frame(30).assign(year=2020)])
        summary = summarise_rates(frame, ["year"])
        self.assertEqual(list(summary.year), [2019, 2020])
        self.assertAlmostEqual(summary.crude.iloc[1], 30.0)
        self.assertAlmostEqual(summary.asr.iloc[1], 30.0)


class RatioTest(unittest.TestCase):
    def test_rate_ratio_interval_contains_ratio(self):
        ratio, lo, hi = rate_ratio(30, 1.0, 10, 0.5)
        self.assertAlmostEqual(ratio, 3.0)
        self.assertTrue(lo < 3.0 < hi)

    def test_count_ratio_exact_limits(self):
        ratio, lo, hi = count_ratio(300, 100)
        self.assertAlmostEqual(ratio, 3.0)
        self.assertTrue(lo < 3.0 < hi)
        self.assertTrue(np.isnan(count_ratio(10, 0)[0]))


class IndirectStandardizationTest(unittest.TestCase):
    def test_expected_counts_equal_observed_for_the_reference(self):
        frame = pd.DataFrame({"area": ["a", "a", "b", "b"], "sex": ["H", "M", "H", "M"],
                              "count": [10, 5, 20, 10], "population": [1000, 1000, 2000, 2000]})
        expected = expected_counts(frame, frame, ["area"], ["sex"])
        self.assertAlmostEqual(expected.expected.sum(), 45.0)
        np.testing.assert_allclose(expected.expected, expected.observed)
        ratios = standardized_ratio(expected.observed, expected.expected)
        np.testing.assert_allclose(ratios.sir, [1.0, 1.0])

    def test_empirical_bayes_shrinks_small_areas_more(self):
        observed = np.array([0, 2, 60, 100, 300])
        expected = np.array([0.5, 1.0, 30.0, 100.0, 150.0])
        result = empirical_bayes_ratio(observed, expected)
        self.assertLess(result.eb_weight.iloc[0], result.eb_weight.iloc[3])
        self.assertTrue(abs(result.sir_eb.iloc[0] - result.prior_mean.iloc[0]) < abs(0 - result.prior_mean.iloc[0]))


class TrendTest(unittest.TestCase):
    def test_apc_recovers_exponential_growth(self):
        years = np.arange(2019, 2025)
        population = np.full(len(years), 1_000_000.0)
        counts = 100 * 1.2 ** (years - 2019)
        result = annual_percent_change(pd.DataFrame({"year": years, "count": counts, "population": population}))
        self.assertAlmostEqual(result["apc"], 20.0, places=4)
        self.assertLess(result["apc_lo"], 20.0)


class NamesTest(unittest.TestCase):
    def test_normalisation_and_aliases(self):
        self.assertEqual(normalize_name("Viña del Mar"), "VINA DEL MAR")
        self.assertEqual(normalize_name("COIHAIQUE"), "COYHAIQUE")
        self.assertEqual(normalize_name("O'Higgins"), "O HIGGINS")
        self.assertEqual(normalize_name(None), "")


if __name__ == "__main__":
    unittest.main()
