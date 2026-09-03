"""Synthetic tests: no real identifiers or clinical histories are included."""
import sys
from pathlib import Path
import unittest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_grd_linkage import parse_dates, valid_id
from grd_trajectories import DIAGS, DEFINITIONS, normalize_icd, role, summarize


def encounter(admission, discharge, principal, secondary="", patient="synthetic-a"):
    row = {c: "" for c in DIAGS}
    row.update(id=patient, admission=pd.Timestamp(admission), discharge=pd.Timestamp(discharge),
               birth=pd.Timestamp("2010-01-01"), sex="HOMBRE", source_year=pd.Timestamp(discharge).year,
               link_eligible=True, valid_dates=True, DIAGNOSTICO1=principal, DIAGNOSTICO2=secondary)
    return row


class TrajectoryTests(unittest.TestCase):
    def test_dates_are_explicit_and_day_first(self):
        result = parse_dates(pd.Series(["2023-02-01", "01-02-2023", "DESCONOCIDO", "31-02-2023"]))
        self.assertEqual(result.iloc[0], result.iloc[1])
        self.assertTrue(result.iloc[2:].isna().all())

    def test_code_boundaries_and_position(self):
        self.assertEqual(normalize_icd(" f84.0 "), "F840")
        self.assertNotIn(normalize_icd("F84.00"), DEFINITIONS["TEA_operacional"])
        self.assertNotIn("F842", DEFINITIONS["TEA_operacional"])
        row = pd.Series(encounter("2022-01-01", "2022-01-02", "F840", "F845"))
        self.assertEqual(role(row, DEFINITIONS["TEA_operacional"]), "principal_y_secundario")

    def test_missing_identifiers(self):
        ids = pd.Series(["0", "-1", "DESCONOCIDO", None, "synthetic-a"], dtype="string")
        self.assertEqual(valid_id(ids).tolist(), [False, False, False, False, True])

    def test_prior_concurrent_and_later_diagnoses_are_separate(self):
        records = [encounter("2021-02-01", "2021-02-02", "F809"),
                   encounter("2022-01-02", "2022-01-09", "G409"),
                   encounter("2022-01-01", "2022-01-10", "J189", "F840"),
                   encounter("2022-02-01", "2022-02-03", "F840")]
        results = summarize(pd.DataFrame(records), "2021-2024", "TEA_operacional", DEFINITIONS["TEA_operacional"])
        codes = results["previous_codes"]
        self.assertEqual(set(codes.code), {"F809"})
        summary = results["cohort_summary"].iloc[0]
        self.assertEqual(summary.prior_hospitalization, 1)
        self.assertEqual(summary.concurrent_prior_records, 1)
        self.assertEqual(results["first_position"].iloc[0].index_role, "solo_secundario")
        self.assertEqual(results["principal_transitions"].iloc[0].later_principal_365d, 1)

    def test_same_day_ties_are_not_arbitrarily_ordered(self):
        records = [encounter("2022-01-01", "2022-01-10", "F840"),
                   encounter("2022-01-02", "2022-01-10", "J189", "F840")]
        result = summarize(pd.DataFrame(records), "2021-2024", "TEA_operacional", DEFINITIONS["TEA_operacional"])
        self.assertEqual(result["first_position"].iloc[0].index_role, "mixto_mismo_dia")
        self.assertEqual(result["cohort_summary"].iloc[0].prior_hospitalization, 0)

    def test_inconsistent_ids_do_not_enter_cohort(self):
        row = encounter("2022-01-01", "2022-01-10", "F840")
        row["link_eligible"] = False
        result = summarize(pd.DataFrame([row]), "2021-2024", "TEA_operacional", DEFINITIONS["TEA_operacional"])
        self.assertEqual(result["cohort_summary"].iloc[0].patients, 0)


if __name__ == "__main__":
    unittest.main()
