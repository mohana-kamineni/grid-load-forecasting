"""Tests for Gate 0.3 Continuity & Monotonicity Audit."""
import unittest
import pandas as pd
from tests.fixtures.synthetic_series import make_clean_series, make_gapped_series
from src.audit.continuity import audit_continuity


class TestGate0Continuity(unittest.TestCase):
    def test_clean_series_passes_continuity(self):
        df = make_clean_series()
        result = audit_continuity(df)
        self.assertTrue(result.passed, f"Continuity failed with errors: {result.errors}")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.total_actual_hours, 35064)
        self.assertEqual(result.total_missing_hours, 0)
        self.assertEqual(result.total_duplicate_hours, 0)
        self.assertTrue(result.is_strictly_monotonic)
        self.assertEqual(len(result.abnormal_days), 0)
        self.assertEqual(len(result.annual_results), 4)
        for ar in result.annual_results:
            self.assertTrue(ar.passed)

    def test_gapped_series_fails_continuity(self):
        df_gapped = make_gapped_series(gap_hours=5)
        result = audit_continuity(df_gapped)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.total_missing_hours, 5)
        self.assertEqual(len(result.gaps_detected), 1)
        self.assertEqual(result.gaps_detected[0]["missing_hours"], 5)

    def test_duplicate_timestamp_fails_continuity(self):
        df = make_clean_series()
        # Duplicate first row
        df_dup = pd.concat([df.iloc[[0]], df]).sort_index()
        result = audit_continuity(df_dup)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertGreater(result.total_duplicate_hours, 0)

    def test_non_monotonic_fails_continuity(self):
        df = make_clean_series()
        # Swap two rows
        idx_list = list(df.index)
        idx_list[10], idx_list[11] = idx_list[11], idx_list[10]
        df_scrambled = df.copy()
        df_scrambled.index = idx_list
        result = audit_continuity(df_scrambled)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertFalse(result.is_strictly_monotonic)


if __name__ == "__main__":
    unittest.main()
