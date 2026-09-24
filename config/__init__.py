"""Config package."""
from config.settings import (
    CONFIG,
    ENTSOEConfig,
    PROJECT_ROOT,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    METADATA_DIR,
    REPORTS_DIR,
    FIGURES_DIR,
    DOCS_DIR,
    get_api_key,
    is_api_key_configured,
)

__all__ = [
    "CONFIG",
    "ENTSOEConfig",
    "PROJECT_ROOT",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "METADATA_DIR",
    "REPORTS_DIR",
    "FIGURES_DIR",
    "DOCS_DIR",
    "get_api_key",
    "is_api_key_configured",
]

