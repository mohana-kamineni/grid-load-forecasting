"""Regression test suite for synthetic artifact provenance and filename safety.

Guards against accidental generation of production-looking filenames (e.g. 'se3', '10Y1001A1001A46L')
from synthetic test fixtures or default parameters.
"""

import inspect
import tempfile
import unittest
from pathlib import Path
import re

from config.settings import CONFIG, FIGURES_DIR
from tests.fixtures.synthetic_series import make_clean_series
from src.audit.artificial_data import audit_artificial_data, generate_audit_plots
from src.audit.gate0_runner import run_gate0_audit

# Prohibited production identifiers in synthetic filenames (case-insensitive)
PROHIBITED_SUBSTRINGS = [
    "se3",
    "se_3",
    "se1",
    "se2",
    "se4",
    CONFIG.AREA_CODE_SE3.lower(),  # "10y1001a1001a46l"
    "10y1001a1001a44p",
    "10y1001a1001a45n",
    "10y1001a1001a47j",
    "a65",
    "a16",
    "a01",
]


class TestArtifactProvenanceRegression(unittest.TestCase):
    """Regression test ensuring synthetic test artifacts cannot masquerade as real-world data."""

    def test_synthetic_audit_plot_filenames_conform_to_rules(self):
        """Verify that synthetic test runs output explicitly synthetic filenames without production identifiers."""
        df = make_clean_series()
        result = audit_artificial_data(df, generate_plots=True, plot_prefix="synthetic_gate0")
        
        self.assertGreater(len(result.figure_paths), 0, "No figures were generated.")
        
        for path_str in result.figure_paths:
            path = Path(path_str)
            filename = path.name.lower()

            # Rule 1: Must contain an explicit synthetic identifier
            self.assertIn(
                "synthetic",
                filename,
                f"Synthetic artifact '{filename}' must contain 'synthetic' identifier."
            )

            # Rule 2: Must NOT contain real bidding zone or production dataset identifiers
            for prohibited in PROHIBITED_SUBSTRINGS:
                self.assertNotIn(
                    prohibited,
                    filename,
                    f"Synthetic artifact '{filename}' illegally contains production identifier '{prohibited}'."
                )

    def test_default_parameter_does_not_inherit_production_identifiers(self):
        """Verify that default parameter values for plot generation do not default to real bidding zones or EICs."""
        # Inspect default argument of generate_audit_plots
        sig_plots = inspect.signature(generate_audit_plots)
        prefix_default_plots = sig_plots.parameters["prefix"].default
        self.assertIsInstance(prefix_default_plots, str)
        for prohibited in PROHIBITED_SUBSTRINGS:
            self.assertNotIn(
                prohibited,
                prefix_default_plots.lower(),
                f"generate_audit_plots default prefix '{prefix_default_plots}' contains production identifier '{prohibited}'."
            )

        # Inspect default argument of audit_artificial_data
        sig_audit = inspect.signature(audit_artificial_data)
        prefix_default_audit = sig_audit.parameters["plot_prefix"].default
        self.assertIsInstance(prefix_default_audit, str)
        for prohibited in PROHIBITED_SUBSTRINGS:
            self.assertNotIn(
                prohibited,
                prefix_default_audit.lower(),
                f"audit_artificial_data default plot_prefix '{prefix_default_audit}' contains production identifier '{prohibited}'."
            )

    def test_default_plot_call_does_not_emit_production_filenames(self):
        """When generate_audit_plots is called with defaults, resulting files must not contain production identifiers."""
        df = make_clean_series()
        series = df["load_mw"].iloc[:500]  # Short slice for quick test
        
        paths = generate_audit_plots(series)
        self.assertGreater(len(paths), 0)

        for p_str in paths:
            path = Path(p_str)
            filename = path.name.lower()
            for prohibited in PROHIBITED_SUBSTRINGS:
                self.assertNotIn(
                    prohibited,
                    filename,
                    f"Default plot filename '{filename}' contains production identifier '{prohibited}'."
                )
            # Clean up default files created by this test
            if path.exists():
                path.unlink()

    def test_gate0_runner_synthetic_run_does_not_emit_production_figures(self):
        """Verify that running gate0_runner with synthetic data does not create SE3-named figures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_report = Path(tmpdir) / "audit_report.md"
            clean_df = make_clean_series()
            
            result = run_gate0_audit(
                actual_load_df=clean_df,
                output_report_path=tmp_report,
                plot_prefix="synthetic_gate0",
            )
            
            art_res = result["artificial_data"]
            for path_str in art_res.figure_paths:
                filename = Path(path_str).name.lower()
                self.assertIn("synthetic", filename)
                for prohibited in PROHIBITED_SUBSTRINGS:
                    self.assertNotIn(
                        prohibited,
                        filename,
                        f"Runner figure '{filename}' contains prohibited production identifier '{prohibited}'."
                    )


if __name__ == "__main__":
    unittest.main()
