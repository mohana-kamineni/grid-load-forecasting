"""Tests for Gate 0.5 Forecast Semantics and Information Boundary Audit."""
import unittest
import pandas as pd
from src.audit.forecast_semantics import audit_forecast_semantics


class TestGate0ForecastSemantics(unittest.TestCase):
    def test_forecast_semantics_formulation(self):
        result = audit_forecast_semantics()
        self.assertTrue(result.passed)
        self.assertEqual(result.status, "PASS")
        self.assertIn("6.1.b", result.regulatory_article)
        self.assertIn("12:00", result.market_gate_closure_cet)
        self.assertIn("10:00", result.mandatory_publication_deadline_cet)
        self.assertIn("D-1 10:00", result.information_boundary_cutoff)
        self.assertIn("ZERO information", result.leakage_prevention_rule)

    def test_forecast_dataframe_validation(self):
        df_forecast = pd.DataFrame(
            {"load_mw": [11000.0, 11500.0]},
            index=pd.date_range("2023-01-01", periods=2, freq="1h", tz="UTC"),
        )
        result = audit_forecast_semantics(forecast_df=df_forecast)
        self.assertTrue(result.passed)
        self.assertEqual(result.status, "PASS")

    def test_invalid_forecast_dataframe_fails(self):
        df_invalid = pd.DataFrame(
            {"incorrect_col": [11000.0]},
            index=pd.date_range("2023-01-01", periods=1, freq="1h", tz="UTC"),
        )
        result = audit_forecast_semantics(forecast_df=df_invalid)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")


if __name__ == "__main__":
    unittest.main()
