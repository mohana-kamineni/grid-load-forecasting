"""Synthetic test fixtures for Gate 0 audit validation.

Provides:
- make_clean_series: Mathematically continuous 35,064-hour series with realistic diurnal/weekly physics.
- make_flatlined_series: Clean series with injected repeated values / flatlines.
- make_interpolated_series: Clean series with injected deterministic linear interpolations.
- make_dst_flawed_series: Clean series with injected DST transition gaps/duplicates.
- make_gapped_series: Clean series with missing random intervals.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from config.settings import CONFIG


def make_clean_series(
    start: str = CONFIG.START_DATE_UTC,
    end: str = CONFIG.END_DATE_UTC,
    base_load: float = 12000.0,
) -> pd.DataFrame:
    """Generate a realistic, continuous hourly load series in UTC.
    
    Contains:
    - Diurnal 24h sine wave
    - Weekly 168h cycle (lower weekend load)
    - Annual seasonal cycle (higher winter load, lower summer load)
    - Smooth realistic noise (no flatlines, no linear interpolation)
    """
    index = pd.date_range(start=start, end=end, freq="1h", tz="UTC")
    n = len(index)

    # Time variables
    hour_of_day = index.hour.values
    day_of_week = index.dayofweek.values
    day_of_year = index.dayofyear.values

    # Physical components
    diurnal = 2500.0 * np.sin((hour_of_day - 6) * 2 * np.pi / 24)
    weekly = np.where(day_of_week >= 5, -1500.0, 500.0)
    seasonal = 3500.0 * np.cos((day_of_year - 15) * 2 * np.pi / 365.25)
    
    # Stochastic process: AR(1) smooth fluctuations
    np.random.seed(42)
    noise = np.zeros(n)
    white = np.random.normal(0, 150.0, size=n)
    for i in range(1, n):
        noise[i] = 0.85 * noise[i - 1] + white[i]

    load_values = base_load + diurnal + weekly + seasonal + noise
    
    df = pd.DataFrame(
        {
            "load_mw": load_values,
            "unit": "MW",
            "area_code": CONFIG.AREA_CODE_SE3,
        },
        index=index,
    )
    df.index.name = "timestamp_utc"
    return df


def make_flatlined_series(flatline_hours: int = 12) -> pd.DataFrame:
    """Generate series with an injected flatline."""
    df = make_clean_series()
    # Inject flatline at index 500 to 500 + flatline_hours
    flat_val = float(df["load_mw"].iloc[500])
    df.iloc[500 : 500 + flatline_hours, df.columns.get_loc("load_mw")] = flat_val
    return df


def make_interpolated_series(interp_hours: int = 10) -> pd.DataFrame:
    """Generate series with injected deterministic linear interpolation."""
    df = make_clean_series()
    # Interpolate between index 1000 and 1000 + interp_hours
    start_idx = 1000
    end_idx = start_idx + interp_hours
    y0 = df["load_mw"].iloc[start_idx]
    y1 = df["load_mw"].iloc[end_idx]
    interp_vals = np.linspace(y0, y1, interp_hours + 1)
    df.iloc[start_idx : end_idx + 1, df.columns.get_loc("load_mw")] = interp_vals
    return df


def make_dst_flawed_series(transition_date: str = "2023-03-26") -> pd.DataFrame:
    """Generate series where an hour on a DST transition is deleted."""
    df = make_clean_series()
    # Drop 01:00 UTC on transition date
    drop_ts = pd.Timestamp(f"{transition_date} 01:00:00", tz="UTC")
    df = df.drop(index=[drop_ts], errors="ignore")
    return df


def make_gapped_series(gap_hours: int = 5) -> pd.DataFrame:
    """Generate series missing a contiguous block of hours."""
    df = make_clean_series()
    drop_indices = df.index[2000 : 2000 + gap_hours]
    return df.drop(index=drop_indices)
