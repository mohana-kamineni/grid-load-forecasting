"""Tests for Gate 0.1 Provenance Audit."""
import unittest
import pandas as pd
from config.settings import CONFIG
from src.audit.provenance import audit_provenance


class TestGate0Provenance(unittest.TestCase):
    def test_default_provenance_audit_passes(self):
        result = audit_provenance()
        self.assertTrue(result.passed)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.eic_code, "10Y1001A1001A46L")
        self.assertEqual(result.target_doc_type, "A65")
        self.assertEqual(result.target_process_type, "A16")
        self.assertEqual(result.benchmark_process_type, "A01")
        self.assertEqual(result.unit, "MW")
        self.assertEqual(result.resolution, "PT60M")

    def test_provenance_with_valid_dataframe(self):
        df = pd.DataFrame(
            {"load_mw": [12000.0], "unit": ["MW"], "area_code": [CONFIG.AREA_CODE_SE3]},
            index=pd.date_range("2023-01-01", periods=1, freq="1h", tz="UTC"),
        )
        result = audit_provenance(df=df)
        self.assertTrue(result.passed)
        self.assertEqual(result.status, "PASS")

    def test_provenance_with_wrong_area_fails(self):
        metadata = {"bidding_zone": "10Y1001A1001A44P"} # SE1
        result = audit_provenance(metadata=metadata)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("mismatch" in e for e in result.errors))

    def test_provenance_with_wrong_unit_fails(self):
        df = pd.DataFrame(
            {"load_mw": [12000.0], "unit": ["GW"]},
            index=pd.date_range("2023-01-01", periods=1, freq="1h", tz="UTC"),
        )
        result = audit_provenance(df=df)
        self.assertFalse(result.passed)
        self.assertEqual(result.status, "FAIL")


if __name__ == "__main__":
    unittest.main()
