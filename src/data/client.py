"""ENTSO-E Transparency Platform REST API Client.

Implements query execution for:
- Actual Total Load [6.1.A] (documentType=A65, processType=A16)
- Day-ahead Total Load Forecast [6.1.B] (documentType=A65, processType=A01)

Features:
- Parameter validation against official ENTSO-E documentation.
- Fails loudly on authentication, parameter rejection, and empty responses.
- Chunking by calendar year to respect ENTSO-E maximum query interval limits.
- Complete metadata logging without exposing security tokens.
"""

from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
import requests

from config.settings import (
    CONFIG,
    RAW_DATA_DIR,
    METADATA_DIR,
    get_api_key,
    is_api_key_configured,
)

logger = logging.getLogger(__name__)


class ENTSOEBidirectionalError(Exception):
    """Base exception for ENTSO-E API interactions."""


class ENTSOEAuthError(ENTSOEBidirectionalError):
    """Raised when authentication fails (HTTP 401, 403, or invalid token)."""


class ENTSOEAPIError(ENTSOEBidirectionalError):
    """Raised when the API returns an error response (e.g., HTTP 400, 500, or XML Acknowledgement error)."""


class ENTSOENoDataError(ENTSOEBidirectionalError):
    """Raised when the API query returns no time series data (Code 999 or empty time series)."""


class ENTSOEClient:
    """REST Client for ENTSO-E Transparency Platform."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60):
        self.api_key = api_key or get_api_key()
        self.base_url = CONFIG.BASE_URL
        self.timeout = timeout
        self.session = requests.Session()

    def _validate_credentials(self) -> None:
        """Ensure API token is configured."""
        if not self.api_key or not self.api_key.strip():
            raise ENTSOEAuthError(
                "ENTSO-E API security token is missing. "
                "Set ENTSOE_API_KEY environment variable or configure it in .env. "
                "Refer to docs/entsoe_access_guide.md for instructions."
            )

    def _validate_parameters(
        self,
        document_type: str,
        process_type: str,
        bidding_zone: str,
    ) -> None:
        """Validate query parameters against verified ENTSO-E specification."""
        if document_type != CONFIG.DOC_TYPE_TOTAL_LOAD:
            raise ValueError(
                f"Invalid documentType '{document_type}'. Expected '{CONFIG.DOC_TYPE_TOTAL_LOAD}' for Total Load."
            )
        if process_type not in (CONFIG.PROCESS_TYPE_ACTUAL_LOAD, CONFIG.PROCESS_TYPE_DAY_AHEAD_FORECAST):
            raise ValueError(
                f"Invalid processType '{process_type}'. Expected '{CONFIG.PROCESS_TYPE_ACTUAL_LOAD}' (Actual [6.1.A]) "
                f"or '{CONFIG.PROCESS_TYPE_DAY_AHEAD_FORECAST}' (Day-ahead Forecast [6.1.B])."
            )
        if bidding_zone != CONFIG.AREA_CODE_SE3:
            raise ValueError(
                f"Invalid bidding zone '{bidding_zone}'. Current project scope is strictly Sweden SE3 ({CONFIG.AREA_CODE_SE3})."
            )

    def _execute_request(self, params: Dict[str, str]) -> requests.Response:
        """Execute HTTP GET with strict error detection, masking credentials in logs."""
        self._validate_credentials()
        
        request_params = {**params, "securityToken": self.api_key}
        # Masked params for safe logging
        safe_params = {k: ("***MASKED***" if k == "securityToken" else v) for k, v in request_params.items()}
        logger.info("Executing ENTSO-E request: %s with params %s", self.base_url, safe_params)

        try:
            response = self.session.get(self.base_url, params=request_params, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            raise ENTSOEAPIError(f"Network transport error connecting to ENTSO-E: {e}") from e

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            raise ENTSOEAuthError(
                f"ENTSO-E Authentication Failed (HTTP {response.status_code}): Invalid or unapproved security token."
            )
        elif response.status_code >= 400:
            # Parse error text if available in response
            error_msg = response.text[:500] if response.text else "No error text provided"
            raise ENTSOEAPIError(
                f"ENTSO-E API returned HTTP {response.status_code}: {error_msg}"
            )

        # Inspect XML response for Acknowledgement errors or empty messages
        self._inspect_xml_content(response.text, safe_params)
        return response

    def _inspect_xml_content(self, xml_text: str, safe_params: Dict[str, str]) -> None:
        """Parse XML response to detect application-level error codes or empty data."""
        if not xml_text or not xml_text.strip():
            raise ENTSOENoDataError(
                f"ENTSO-E API returned an empty response body for params: {safe_params}"
            )

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise ENTSOEAPIError(f"Failed to parse XML response from ENTSO-E: {e}. Snippet: {xml_text[:300]}") from e

        # Strip namespace if present
        tag_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if "Acknowledgement" in tag_name:
            # Extract reason code and text
            reasons = []
            for reason in root.iter():
                if reason.tag.endswith("Reason"):
                    code = reason.findtext("{*}code", default="")
                    text = reason.findtext("{*}text", default="")
                    reasons.append(f"[{code}] {text}")
            reason_str = "; ".join(reasons) if reasons else xml_text[:300]
            
            # Check for 999 "No matching data found"
            if "999" in reason_str or "No matching data" in reason_str:
                raise ENTSOENoDataError(
                    f"ENTSO-E reported no data found (Reason: {reason_str}). Params: {safe_params}"
                )
            raise ENTSOEAPIError(
                f"ENTSO-E Acknowledgement error: {reason_str}. Params: {safe_params}"
            )

        # Check for TimeSeries presence
        timeseries_found = any(elem.tag.endswith("TimeSeries") for elem in root.iter())
        if not timeseries_found:
            raise ENTSOENoDataError(
                f"ENTSO-E response contained no TimeSeries elements. Root tag: {tag_name}. Params: {safe_params}"
            )

    def query_series_chunk(
        self,
        document_type: str,
        process_type: str,
        start_utc: str,
        end_utc: str,
        bidding_zone: str = CONFIG.AREA_CODE_SE3,
    ) -> str:
        """Fetch a single temporal interval (max 1 calendar year) from ENTSO-E.
        
        start_utc and end_utc format: 'yyyyMMddHHmm'
        """
        self._validate_parameters(document_type, process_type, bidding_zone)
        params = {
            "documentType": document_type,
            "processType": process_type,
            "outBiddingZone_Domain": bidding_zone,
            "periodStart": start_utc,
            "periodEnd": end_utc,
        }
        response = self._execute_request(params)
        return response.text

    def fetch_full_range(
        self,
        process_type: str,
        start_year: int = 2022,
        end_year: int = 2025,
        save_raw: bool = True,
    ) -> List[Path]:
        """Fetch multi-year series chunked by calendar year and save raw payloads."""
        self._validate_parameters(CONFIG.DOC_TYPE_TOTAL_LOAD, process_type, CONFIG.AREA_CODE_SE3)
        series_label = "actual_load_6_1_a" if process_type == CONFIG.PROCESS_TYPE_ACTUAL_LOAD else "day_ahead_forecast_6_1_b"
        saved_files: List[Path] = []

        for year in range(start_year, end_year + 1):
            start_str = f"{year}01010000"
            end_str = f"{year + 1}01010000"
            logger.info("Fetching %s for year %d (%s -> %s)...", series_label, year, start_str, end_str)

            xml_data = self.query_series_chunk(
                document_type=CONFIG.DOC_TYPE_TOTAL_LOAD,
                process_type=process_type,
                start_utc=start_str,
                end_utc=end_str,
                bidding_zone=CONFIG.AREA_CODE_SE3,
            )

            if save_raw:
                timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                raw_filename = f"{series_label}_SE3_{year}_{timestamp_str}.xml"
                raw_path = RAW_DATA_DIR / raw_filename
                raw_path.write_text(xml_data, encoding="utf-8")
                saved_files.append(raw_path)

                # Save metadata manifest
                meta = {
                    "series_label": series_label,
                    "year": year,
                    "document_type": CONFIG.DOC_TYPE_TOTAL_LOAD,
                    "process_type": process_type,
                    "bidding_zone": CONFIG.AREA_CODE_SE3,
                    "period_start_utc": start_str,
                    "period_end_utc": end_str,
                    "retrieved_at_utc": timestamp_str,
                    "raw_filename": raw_filename,
                    "file_size_bytes": len(xml_data.encode("utf-8")),
                }
                meta_path = METADATA_DIR / f"{series_label}_SE3_{year}_manifest.json"
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            # Politeness delay between yearly queries
            time.sleep(1.0)

        return saved_files
