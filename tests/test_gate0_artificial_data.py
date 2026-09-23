"""Tests for Gate 0.4 Artificial-Data, Flatlines, and Linear Interpolation Detection."""
import unittest
from pathlib import Path
from tests.fixtures.synthetic_series import (
    make_clean_series,
    make_flatlined_series,
    make_interpolated_series,
)
from src.audit.artificial_data import (
    audit_artificial_data,
    detect_linear_interpolation,
    calculate_run_lengths,
)


class TestGate0ArtificialData(unittest.TestCase):
    def test_clean_series_passes_artificial_data_audit(self):
        df = make_clean_series()
        result = audit_artificial_data(df, generate_plots=False)
        self.assertTrue(result.passed, f"Gate 0.4 failed unexpectedly with errors: {result.errors}")
        self.assertEqual(result.status, "PASS")
        self.assertLessEqual(result.max_flatline_hours, 3)
        self.assertEqual(len(result.detected_interpolation_spans), 0)
        self.assertGreaterEqual(result.autocorrelation_lag_1, 0.70)
        self.assertGreaterEqual(result.autocorrelation_lag_24, 0.40)

    def test_flatlined_series_detected_and_fails(self):
        # 12-hour flatline
        df_flat = make_flatlined_series(flatline_hours=12)
        result = audit_artificial_data(df_flat, generate_plots=False)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertGreaterEqual(result.max_flatline_hours, 12)
        self.assertTrue(any("flatline" in e.lower() for e in result.errors))

    def test_linear_interpolation_detected_and_fails(self):
        # 10-hour deterministic linear interpolation
        df_interp = make_interpolated_series(interp_hours=10)
        result = audit_artificial_data(df_interp, generate_plots=False)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertGreaterEqual(result.max_linear_interpolation_hours, 10)
        self.assertTrue(any("linear interpolation" in e.lower() for e in result.errors))

    def test_plot_generation(self):
        df = make_clean_series()
        result = audit_artificial_data(df, generate_plots=True, plot_prefix="synthetic_gate0")
        self.assertEqual(len(result.figure_paths), 2)
        for p in result.figure_paths:
            self.assertTrue(Path(p).exists())
            self.assertIn("synthetic_gate0", p)


if __name__ == "__main__":
    unittest.main()
