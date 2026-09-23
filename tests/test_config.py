"""Tests for configuration settings."""
import unittest
from config.settings import CONFIG, get_api_key, is_api_key_configured


class TestConfig(unittest.TestCase):
    def test_eic_code_and_area(self):
        self.assertEqual(CONFIG.AREA_CODE_SE3, "10Y1001A1001A46L")
        self.assertEqual(CONFIG.AREA_NAME, "Sweden SE3")

    def test_document_and_process_types(self):
        self.assertEqual(CONFIG.DOC_TYPE_TOTAL_LOAD, "A65")
        self.assertEqual(CONFIG.PROCESS_TYPE_ACTUAL_LOAD, "A16")
        self.assertEqual(CONFIG.PROCESS_TYPE_DAY_AHEAD_FORECAST, "A01")

    def test_temporal_scope_and_hours(self):
        self.assertEqual(CONFIG.START_DATE_UTC, "2022-01-01T00:00:00Z")
        self.assertEqual(CONFIG.END_DATE_UTC, "2025-12-31T23:00:00Z")
        self.assertEqual(CONFIG.RESOLUTION, "PT60M")
        self.assertEqual(CONFIG.UNIT, "MW")
        
        # 4-year hours
        self.assertEqual(CONFIG.EXPECTED_HOURS_BY_YEAR[2022], 8760)
        self.assertEqual(CONFIG.EXPECTED_HOURS_BY_YEAR[2023], 8760)
        self.assertEqual(CONFIG.EXPECTED_HOURS_BY_YEAR[2024], 8784)  # leap year
        self.assertEqual(CONFIG.EXPECTED_HOURS_BY_YEAR[2025], 8760)
        self.assertEqual(sum(CONFIG.EXPECTED_HOURS_BY_YEAR.values()), 35064)

    def test_dst_transitions_count(self):
        # Must cover exactly all 8 transitions across 2022-2025
        self.assertEqual(len(CONFIG.DST_TRANSITIONS), 8)
        years = [int(t[0][:4]) for t in CONFIG.DST_TRANSITIONS]
        self.assertEqual(set(years), {2022, 2023, 2024, 2025})

    def test_credential_helpers(self):
        # Without setting env var, is_api_key_configured should return False or match env
        self.assertIsInstance(is_api_key_configured(), bool)


if __name__ == "__main__":
    unittest.main()
