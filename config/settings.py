"""Configuration settings for Project P4: Grid Load Forecasting.

Defines all constants, EIC codes, regulatory parameters, and paths.
Credentials are loaded securely from environment or .env without logging secrets.
"""

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"

# Ensure runtime directories exist
for directory in (RAW_DATA_DIR, PROCESSED_DATA_DIR, METADATA_DIR, REPORTS_DIR, FIGURES_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class ENTSOEConfig:
    """Authoritative ENTSO-E parameters for Sweden SE3."""
    BASE_URL: str = "https://web-api.tp.entsoe.eu/api"
    
    # Bidding Zone
    AREA_NAME: str = "Sweden SE3"
    AREA_CODE_SE3: str = "10Y1001A1001A46L"
    
    # Document and Process Types (Regulation EU No 543/2013)
    DOC_TYPE_TOTAL_LOAD: str = "A65"
    PROCESS_TYPE_ACTUAL_LOAD: str = "A16"          # Realised / Actual Total Load [6.1.A]
    PROCESS_TYPE_DAY_AHEAD_FORECAST: str = "A01"   # Day-ahead Total Load Forecast [6.1.B]
    
    # Temporal Scope
    START_DATE_UTC: str = "2022-01-01T00:00:00Z"
    END_DATE_UTC: str = "2025-12-31T23:00:00Z"
    RESOLUTION: str = "PT60M"  # 1 hour
    UNIT: str = "MW"
    
    # Timezones
    CANONICAL_TIMEZONE: str = "UTC"
    LOCAL_TIMEZONE: str = "Europe/Stockholm"
    
    # Expected hours across the 4-year scope
    EXPECTED_HOURS_BY_YEAR: Dict[int, int] = None
    
    # DST transition dates in Sweden (2022-2025)
    # Format: (date_str, transition_type, expected_local_clock_hours)
    DST_TRANSITIONS: List[Tuple[str, str, int]] = None

    def __post_init__(self):
        # We use object.__setattr__ because the dataclass is frozen
        object.__setattr__(
            self,
            "EXPECTED_HOURS_BY_YEAR",
            {
                2022: 8760,
                2023: 8760,
                2024: 8784,  # Leap year
                2025: 8760,
            }
        )
        object.__setattr__(
            self,
            "DST_TRANSITIONS",
            [
                ("2022-03-27", "spring_forward", 23),
                ("2022-10-30", "autumn_fallback", 25),
                ("2023-03-26", "spring_forward", 23),
                ("2023-10-29", "autumn_fallback", 25),
                ("2024-03-31", "spring_forward", 23),
                ("2024-10-27", "autumn_fallback", 25),
                ("2025-03-30", "spring_forward", 23),
                ("2025-10-26", "autumn_fallback", 25),
            ]
        )


def get_api_key() -> str | None:
    """Retrieve ENTSO-E API key from environment without logging it."""
    key = os.getenv("ENTSOE_API_KEY")
    if key and key.strip() and key.strip() != "your_security_token_here":
        return key.strip()
    return None


def is_api_key_configured() -> bool:
    """Check if a non-placeholder API key is set."""
    return get_api_key() is not None


CONFIG = ENTSOEConfig()
