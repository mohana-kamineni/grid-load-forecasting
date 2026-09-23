"""Tests for ENTSO-E API client, parameter enforcement, and error handling."""
import unittest
from unittest.mock import MagicMock, patch
import requests

from config.settings import CONFIG
from src.data.client import (
    ENTSOEClient,
    ENTSOEAuthError,
    ENTSOEAPIError,
    ENTSOENoDataError,
)


class TestENTSOEClient(unittest.TestCase):
    def test_missing_credentials_raises_auth_error(self):
        client = ENTSOEClient(api_key=None)
        with patch("src.data.client.get_api_key", return_value=None):
            client.api_key = None
            with self.assertRaises(ENTSOEAuthError):
                client._validate_credentials()

    def test_parameter_validation_document_type(self):
        client = ENTSOEClient(api_key="mock_key")
        with self.assertRaises(ValueError) as ctx:
            client._validate_parameters("INVALID_DOC", CONFIG.PROCESS_TYPE_ACTUAL_LOAD, CONFIG.AREA_CODE_SE3)
        self.assertIn("Invalid documentType", str(ctx.exception))

    def test_parameter_validation_process_type(self):
        client = ENTSOEClient(api_key="mock_key")
        with self.assertRaises(ValueError) as ctx:
            client._validate_parameters(CONFIG.DOC_TYPE_TOTAL_LOAD, "INVALID_PROC", CONFIG.AREA_CODE_SE3)
        self.assertIn("Invalid processType", str(ctx.exception))

    def test_parameter_validation_bidding_zone(self):
        client = ENTSOEClient(api_key="mock_key")
        with self.assertRaises(ValueError) as ctx:
            client._validate_parameters(CONFIG.DOC_TYPE_TOTAL_LOAD, CONFIG.PROCESS_TYPE_ACTUAL_LOAD, "10Y1001A1001A44P") # SE1
        self.assertIn("Invalid bidding zone", str(ctx.exception))

    def test_verified_process_types_accepted(self):
        client = ENTSOEClient(api_key="mock_key")
        # Actual Total Load [6.1.A] -> A16
        client._validate_parameters(CONFIG.DOC_TYPE_TOTAL_LOAD, "A16", CONFIG.AREA_CODE_SE3)
        # Day-ahead Total Load Forecast [6.1.B] -> A01
        client._validate_parameters(CONFIG.DOC_TYPE_TOTAL_LOAD, "A01", CONFIG.AREA_CODE_SE3)

    @patch("requests.Session.get")
    def test_http_401_raises_auth_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_get.return_value = mock_resp

        client = ENTSOEClient(api_key="invalid_token")
        with self.assertRaises(ENTSOEAuthError):
            client._execute_request({"documentType": "A65"})

    @patch("requests.Session.get")
    def test_http_400_raises_api_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request: Parameter out of range"
        mock_get.return_value = mock_resp

        client = ENTSOEClient(api_key="valid_token")
        with self.assertRaises(ENTSOEAPIError) as ctx:
            client._execute_request({"documentType": "A65"})
        self.assertIn("HTTP 400", str(ctx.exception))

    def test_empty_xml_raises_no_data_error(self):
        client = ENTSOEClient(api_key="valid_token")
        with self.assertRaises(ENTSOENoDataError):
            client._inspect_xml_content("", {"doc": "A65"})

    def test_acknowledgement_code_999_raises_no_data_error(self):
        ack_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
            <mRID>ack123</mRID>
            <Reason>
                <code>999</code>
                <text>No matching data found for query</text>
            </Reason>
        </Acknowledgement_MarketDocument>"""
        client = ENTSOEClient(api_key="valid_token")
        with self.assertRaises(ENTSOENoDataError) as ctx:
            client._inspect_xml_content(ack_xml, {"doc": "A65"})
        self.assertIn("no data found", str(ctx.exception))

    def test_xml_without_timeseries_raises_no_data_error(self):
        empty_doc = """<?xml version="1.0" encoding="UTF-8"?>
        <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
            <mRID>doc123</mRID>
        </GL_MarketDocument>"""
        client = ENTSOEClient(api_key="valid_token")
        with self.assertRaises(ENTSOENoDataError) as ctx:
            client._inspect_xml_content(empty_doc, {"doc": "A65"})
        self.assertIn("no TimeSeries", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
