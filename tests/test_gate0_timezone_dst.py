"""Tests for Gate 0.2 Timezone & DST Integrity Audit (HARD GATE)."""
import unittest
import pandas as pd
from tests.fixtures.synthetic_series import make_clean_series, make_dst_flawed_series
from src.audit.timezone_dst import audit_timezone_dst


class TestGate0TimezoneDST(unittest.TestCase):
    def test_clean_series_passes_all_8_transitions(self):
        df = make_clean_series()
        result = audit_timezone_dst(df)
        self.assertTrue(result.passed, f"Gate 0.2 failed unexpectedly with errors: {result.errors}")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.transitions_evaluated, 8)
        self.assertEqual(result.transitions_passed, 8)
        self.assertEqual(len(result.errors), 0)

        # Verify spring forward (23h local) vs autumn fallback (25h local)
        for tr in result.transition_results:
            self.assertEqual(tr.actual_physical_hours_utc, 24)
            if tr.transition_type == "spring_forward":
                self.assertEqual(tr.actual_local_clock_hours, 23)
            elif tr.transition_type == "autumn_fallback":
                self.assertEqual(tr.actual_local_clock_hours, 25)

    def test_dst_flawed_series_fails_hard(self):
        # 2023-03-26 missing an hour
        df_flawed = make_dst_flawed_series(transition_date="2023-03-26")
        result = audit_timezone_dst(df_flawed)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.transitions_passed, 7)
        self.assertTrue(any("2023-03-26" in e for e in result.errors))

    def test_naive_timezone_index_fails_hard(self):
        df_naive = make_clean_series()
        df_naive.index = df_naive.index.tz_localize(None)
        result = audit_timezone_dst(df_naive)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("timezone-aware" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
