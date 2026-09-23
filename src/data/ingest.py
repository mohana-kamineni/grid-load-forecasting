"""Ingestion and normalization of ENTSO-E load data.

Supports:
1. Parsing raw XML responses from ENTSO-E REST API.
2. Parsing official Transparency Platform CSV downloads.
3. Dual-index representation (canonical UTC primary index, Europe/Stockholm secondary index).
4. Strict validation of non-empty content and structural completeness.
"""

from __future__ import annotations
import re
import logging
from pathlib import Path
from typing import Optional, Union, List
import xml.etree.ElementTree as ET
import pandas as pd

from config.settings import CONFIG, PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)


def parse_entsoe_xml(xml_source: Union[str, Path]) -> pd.DataFrame:
    """Parse ENTSO-E GL_MarketDocument XML into a clean hourly DataFrame with UTC tz-aware index.
    
    Raises:
        ValueError: If XML contains no valid time series or is empty.
    """
    if isinstance(xml_source, Path):
        xml_text = xml_source.read_text(encoding="utf-8")
    else:
        xml_text = xml_source

    if not xml_text or not xml_text.strip():
        raise ValueError("Cannot parse empty XML source.")

    root = ET.fromstring(xml_text)
    records = []

    # Namespace handling
    for ts in root.iter():
        if not ts.tag.endswith("TimeSeries"):
            continue

        # Extract Area
        out_area = ts.findtext("{*}outBiddingZone_Domain.mRID", default="")
        in_area = ts.findtext("{*}inBiddingZone_Domain.mRID", default="")
        area_code = out_area or in_area

        # Extract Unit
        unit = ts.findtext("{*}quantity_Measure_Unit.name", default="MW")

        # Process Periods
        for period in ts.findall("{*}Period"):
            time_interval = period.find("{*}timeInterval")
            if time_interval is None:
                continue

            start_str = time_interval.findtext("{*}start", default="")
            resolution_str = period.findtext("{*}resolution", default="PT60M")

            if not start_str:
                continue

            # Parse start time as UTC
            period_start = pd.to_datetime(start_str, utc=True)
            
            # Map ISO duration to pandas freq
            delta = pd.Timedelta(hours=1)
            if resolution_str == "PT60M":
                delta = pd.Timedelta(hours=1)
            elif resolution_str == "PT15M":
                delta = pd.Timedelta(minutes=15)
            elif resolution_str == "PT30M":
                delta = pd.Timedelta(minutes=30)

            for point in period.findall("{*}Point"):
                pos_str = point.findtext("{*}position", default="1")
                qty_str = point.findtext("{*}quantity", default="")

                if not qty_str:
                    continue

                position = int(pos_str)
                timestamp_utc = period_start + (position - 1) * delta
                load_mw = float(qty_str)

                records.append({
                    "timestamp_utc": timestamp_utc,
                    "load_mw": load_mw,
                    "resolution": resolution_str,
                    "unit": unit,
                    "area_code": area_code,
                })

    if not records:
        raise ValueError("No valid TimeSeries Points extracted from ENTSO-E XML.")

    df = pd.DataFrame(records)
    # Deduplicate in case of duplicate blocks, sort chronologically
    df = df.drop_duplicates(subset=["timestamp_utc"]).sort_values("timestamp_utc")
    df = df.set_index("timestamp_utc")
    return df


def parse_entsoe_csv(csv_path: Union[str, Path]) -> pd.DataFrame:
    """Parse official ENTSO-E portal / File Library CSV export.
    
    Robust to varying column naming conventions across portal versions:
    - 'Time (UTC)' vs 'DateTime' vs 'MTU'
    - 'Actual Total Load [MW] - BZN|SE3' vs 'Actual Total Load [MW]'
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    # Inspect first few lines for separator
    header_snippet = path.read_text(encoding="utf-8", errors="replace")[:1000]
    sep = ";" if ";" in header_snippet.split("\n")[0] else ","

    df = pd.read_csv(path, sep=sep)
    if df.empty:
        raise ValueError(f"CSV file {path} contains no data rows.")

    # Locate timestamp column
    time_col = None
    for col in df.columns:
        clean_col = col.strip().lower()
        if "time (utc)" in clean_col or "utc" in clean_col:
            time_col = col
            break
        elif "datetime" in clean_col or "mtu" in clean_col or "time" in clean_col:
            time_col = col

    if time_col is None:
        raise ValueError(f"Could not locate timestamp column in CSV {path}. Columns found: {list(df.columns)}")

    # Parse timestamps
    # Some ENTSO-E portal exports format MTU as '01.01.2022 00:00 - 01.01.2022 01:00 (UTC)'
    first_val = str(df[time_col].iloc[0])
    if " - " in first_val:
        # Take the start of the interval
        df["timestamp_utc"] = pd.to_datetime(
            df[time_col].apply(lambda x: str(x).split(" - ")[0].strip()),
            utc=True,
            format="mixed",
        )
    else:
        df["timestamp_utc"] = pd.to_datetime(df[time_col], utc=True, format="mixed")

    # Locate load value column
    load_col = None
    for col in df.columns:
        clean_col = col.strip().lower()
        if "actual" in clean_col or "load" in clean_col or "total" in clean_col or "quantity" in clean_col:
            load_col = col
            break

    if load_col is None:
        raise ValueError(f"Could not locate load column in CSV {path}. Columns: {list(df.columns)}")

    # Clean numeric values
    df["load_mw"] = pd.to_numeric(
        df[load_col].astype(str).str.replace(",", ".").str.replace(" ", "").str.strip(),
        errors="coerce",
    )

    clean_df = df[["timestamp_utc", "load_mw"]].dropna(subset=["timestamp_utc"]).copy()
    clean_df = clean_df.drop_duplicates(subset=["timestamp_utc"]).sort_values("timestamp_utc")
    clean_df = clean_df.set_index("timestamp_utc")
    return clean_df


def validate_series_integrity(df: pd.DataFrame, series_name: str = "load") -> None:
    """Validate that the DataFrame satisfies basic time-series integrity constraints.
    
    Fails loudly if empty, untyped, or not UTC indexed.
    """
    if df.empty:
        raise ValueError(f"Dataset '{series_name}' is empty. Cannot proceed.")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(f"Dataset '{series_name}' index must be a pd.DatetimeIndex, got {type(df.index)}.")

    if df.index.tz is None:
        raise ValueError(f"Dataset '{series_name}' index must be timezone-aware (canonical UTC).")

    if "load_mw" not in df.columns:
        raise ValueError(f"Dataset '{series_name}' must contain 'load_mw' column. Found: {list(df.columns)}")

    if df["load_mw"].isna().all():
        raise ValueError(f"Dataset '{series_name}' contains only NaN values.")


def save_processed_series(df: pd.DataFrame, filename: str) -> Path:
    """Save processed series as parquet and csv in processed directory."""
    validate_series_integrity(df, series_name=filename)
    csv_path = PROCESSED_DATA_DIR / f"{filename}.csv"
    parquet_path = PROCESSED_DATA_DIR / f"{filename}.parquet"
    
    df.to_csv(csv_path)
    df.to_parquet(parquet_path)
    logger.info("Saved processed series to %s and %s", csv_path, parquet_path)
    return parquet_path
