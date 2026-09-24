"""Data Acquisition Script for Project P4.

Acquires official ENTSO-E Transparency Platform data for Sweden SE3 (2022-2025):
1. [6.1.A] Actual Total Load (A65 / A16)
2. [6.1.B] Day-ahead Total Load Forecast (A65 / A01)

Saves raw XML payloads and metadata manifests in data/raw/ and data/metadata/.
Parses and normalizes harmonized hourly time series in data/processed/.
"""

import logging
import sys
from pathlib import Path
import pandas as pd

from config.settings import (
    CONFIG,
    RAW_DATA_DIR,
    METADATA_DIR,
    PROCESSED_DATA_DIR,
)
from src.data.client import ENTSOEClient
from src.data.ingest import parse_entsoe_xml, save_processed_series

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def acquire_dataset(process_type: str, series_name: str) -> pd.DataFrame:
    """Fetch all 4 years (2022-2025) for a given process type, parse, and save."""
    client = ENTSOEClient()
    logger.info("Starting acquisition of %s (%s)...", series_name, process_type)
    
    raw_files = client.fetch_full_range(
        process_type=process_type,
        start_year=2022,
        end_year=2025,
        save_raw=True,
    )
    logger.info("Successfully fetched %d raw XML files for %s.", len(raw_files), series_name)

    yearly_dfs = []
    for raw_file in raw_files:
        logger.info("Parsing raw XML: %s", raw_file.name)
        df_year = parse_entsoe_xml(raw_file)
        logger.info("  Parsed %d points (from %s to %s)", len(df_year), df_year.index.min(), df_year.index.max())
        yearly_dfs.append(df_year)

    full_df = pd.concat(yearly_dfs)
    full_df = full_df[~full_df.index.duplicated(keep="first")].sort_index()
    logger.info("Combined %s total observations: %d rows (from %s to %s)", series_name, len(full_df), full_df.index.min(), full_df.index.max())

    # Save processed series
    processed_file = save_processed_series(full_df, filename=f"real_se3_{series_name}_2022_2025")
    logger.info("Saved processed dataset to %s", processed_file)
    return full_df


def main():
    logger.info("==================================================")
    logger.info("ENTSO-E SE3 Data Acquisition: 2022-2025")
    logger.info("Bidding Zone: %s (%s)", CONFIG.AREA_NAME, CONFIG.AREA_CODE_SE3)
    logger.info("==================================================")

    # 1. Acquire Actual Total Load [6.1.A]
    actual_df = acquire_dataset(
        process_type=CONFIG.PROCESS_TYPE_ACTUAL_LOAD,
        series_name="actual_load_6_1_a",
    )

    # 2. Acquire Day-ahead Total Load Forecast [6.1.B]
    forecast_df = acquire_dataset(
        process_type=CONFIG.PROCESS_TYPE_DAY_AHEAD_FORECAST,
        series_name="day_ahead_forecast_6_1_b",
    )

    logger.info("Acquisition complete for both 6.1.A and 6.1.B datasets!")
    return actual_df, forecast_df


if __name__ == "__main__":
    main()
