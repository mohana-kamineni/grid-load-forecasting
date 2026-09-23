"""Tests for data ingestion, XML/CSV parsing, and validation."""
import unittest
import pandas as pd
from pathlib import Path
from src.data.ingest import parse_entsoe_xml, parse_entsoe_csv, validate_series_integrity


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
    <mRID>test_doc</mRID>
    <type>A65</type>
    <process.processType>A16</process.processType>
    <outBiddingZone_Domain.mRID>10Y1001A1001A46L</outBiddingZone_Domain.mRID>
    <TimeSeries>
        <mRID>1</mRID>
        <businessType>A04</businessType>
        <outBiddingZone_Domain.mRID>10Y1001A1001A46L</outBiddingZone_Domain.mRID>
        <quantity_Measure_Unit.name>MW</quantity_Measure_Unit.name>
        <Period>
            <timeInterval>
                <start>2023-01-01T00:00Z</start>
                <end>2023-01-01T04:00Z</end>
            </timeInterval>
            <resolution>PT60M</resolution>
            <Point>
                <position>1</position>
                <quantity>11500</quantity>
            </Point>
            <Point>
                <position>2</position>
                <quantity>11200</quantity>
            </Point>
            <Point>
                <position>3</position>
                <quantity>10950</quantity>
            </Point>
            <Point>
                <position>4</position>
                <quantity>10800</quantity>
            </Point>
        </Period>
    </TimeSeries>
</GL_MarketDocument>"""


class TestIngest(unittest.TestCase):
    def test_parse_valid_xml(self):
        df = parse_entsoe_xml(SAMPLE_XML)
        self.assertEqual(len(df), 4)
        self.assertIsInstance(df.index, pd.DatetimeIndex)
        self.assertEqual(str(df.index.tz), "UTC")
        self.assertEqual(list(df["load_mw"]), [11500.0, 11200.0, 10950.0, 10800.0])
        self.assertEqual(df["unit"].iloc[0], "MW")
        self.assertEqual(df["area_code"].iloc[0], "10Y1001A1001A46L")

    def test_parse_empty_xml_raises_error(self):
        with self.assertRaises(ValueError):
            parse_entsoe_xml("")

    def test_validate_series_integrity_success(self):
        df = parse_entsoe_xml(SAMPLE_XML)
        # Should not raise
        validate_series_integrity(df, "test_series")

    def test_validate_series_integrity_empty_fails(self):
        with self.assertRaises(ValueError):
            validate_series_integrity(pd.DataFrame(), "empty_df")

    def test_validate_series_integrity_naive_tz_fails(self):
        df = pd.DataFrame(
            {"load_mw": [100.0, 105.0]},
            index=pd.date_range("2023-01-01", periods=2, freq="1h"),  # tz-naive
        )
        with self.assertRaises(ValueError) as ctx:
            validate_series_integrity(df, "naive_tz")
        self.assertIn("timezone-aware", str(ctx.exception))

    def test_validate_series_integrity_missing_column_fails(self):
        df = pd.DataFrame(
            {"wrong_col": [100.0, 105.0]},
            index=pd.date_range("2023-01-01", periods=2, freq="1h", tz="UTC"),
        )
        with self.assertRaises(ValueError) as ctx:
            validate_series_integrity(df, "wrong_col_df")
        self.assertIn("load_mw", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
