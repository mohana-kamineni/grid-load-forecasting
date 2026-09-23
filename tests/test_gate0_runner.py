"""Tests for Gate 0 master runner and report generation."""
import unittest
import tempfile
from pathlib import Path
from tests.fixtures.synthetic_series import make_clean_series, make_flatlined_series
from src.audit.gate0_runner import run_gate0_audit


class TestGate0Runner(unittest.TestCase):
    def test_run_gate0_without_data_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "test_report.md"
            result = run_gate0_audit(actual_load_df=None, output_report_path=report_path)
            self.assertEqual(result["overall_status"], "AMBIGUOUS — DO NOT MODEL YET")
            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("Gate 0 Decision", content)
            self.assertIn("AMBIGUOUS", content)

    def test_run_gate0_with_clean_data_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "test_report.md"
            clean_df = make_clean_series()
            result = run_gate0_audit(
                actual_load_df=clean_df,
                output_report_path=report_path,
                plot_prefix="synthetic_gate0",
            )
            self.assertEqual(result["overall_status"], "PASS")
            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("PASS", content)
            self.assertIn("35,064", content)
            # Verify table of all 8 transitions
            self.assertIn("2022-03-27", content)
            self.assertIn("2025-10-26", content)

    def test_run_gate0_with_faulty_data_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "test_report.md"
            flat_df = make_flatlined_series(flatline_hours=12)
            result = run_gate0_audit(
                actual_load_df=flat_df,
                output_report_path=report_path,
                plot_prefix="synthetic_gate0",
            )
            self.assertEqual(result["overall_status"], "FAIL")
            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("FAIL", content)


if __name__ == "__main__":
    unittest.main()
