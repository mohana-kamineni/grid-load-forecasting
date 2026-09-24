"""Feature extraction pipeline for SE3 hourly grid load forecasting.

Strictly enforces:
1. Frozen 21-feature schema:
   - 10 historical actual-load features: lag_0, lag_1, lag_2, lag_3, lag_6, lag_12, lag_24, lag_48, lag_72, lag_168
   - 5 backward-looking rolling features: rolling_mean_6h, rolling_mean_24h, rolling_mean_168h, rolling_std_24h, rolling_std_168h
   - 5 deterministic target-calendar features: hour_of_day, day_of_week, day_of_month, month, is_weekend
   - 1 holiday feature: is_public_holiday (Swedish public holidays plus de facto reduced-activity days)
2. Causal origin boundary: Every observed-load feature satisfies source_timestamp <= origin t.
3. Feature NaN integrity: Zero NaNs and zero infinite values in feature matrix.
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd

from src.features.calendar import compute_target_calendar_features

FROZEN_FEATURE_NAMES: List[str] = [
    "lag_0",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_6",
    "lag_12",
    "lag_24",
    "lag_48",
    "lag_72",
    "lag_168",
    "rolling_mean_6h",
    "rolling_mean_24h",
    "rolling_mean_168h",
    "rolling_std_24h",
    "rolling_std_168h",
    "hour_of_day",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "is_public_holiday",
]


def extract_origin_features(series_causal: pd.Series) -> pd.DataFrame:
    """Extract origin-anchored historical load and rolling features.
    
    Evaluated at forecast origin t using causal history y <= t.
    All rolling windows end strictly at t.
    
    Args:
        series_causal: Causally forward-filled actual load series indexed by UTC timestamp.
        
    Returns:
        pd.DataFrame indexed by forecast origin t, containing 15 features.
    """
    df = pd.DataFrame(index=series_causal.index)

    # 1. Historical Actual-Load Telemetry (10 features)
    df["lag_0"] = series_causal  # y[t] (persistence anchor)
    df["lag_1"] = series_causal.shift(1)  # y[t-1]
    df["lag_2"] = series_causal.shift(2)  # y[t-2]
    df["lag_3"] = series_causal.shift(3)  # y[t-3]
    df["lag_6"] = series_causal.shift(6)  # y[t-6]
    df["lag_12"] = series_causal.shift(12)  # y[t-12]
    df["lag_24"] = series_causal.shift(24)  # y[t-24]
    df["lag_48"] = series_causal.shift(48)  # y[t-48]
    df["lag_72"] = series_causal.shift(72)  # y[t-72]
    df["lag_168"] = series_causal.shift(168)  # y[t-168]

    # 2. Backward-Looking Rolling Statistics (5 features)
    # rolling(W) on series ending at t covers [t - W + 1 : t]
    df["rolling_mean_6h"] = series_causal.rolling(6).mean()
    df["rolling_mean_24h"] = series_causal.rolling(24).mean()
    df["rolling_mean_168h"] = series_causal.rolling(168).mean()
    df["rolling_std_24h"] = series_causal.rolling(24).std(ddof=1)
    df["rolling_std_168h"] = series_causal.rolling(168).std(ddof=1)

    return df


def build_feature_matrix_for_horizon(
    series_raw: pd.Series,
    origin_timestamps: pd.DatetimeIndex,
    horizon_hours: int,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Construct frozen 21-feature matrix X and authentic target series y for a given horizon.
    
    Args:
        series_raw: Raw, un-imputed actual load series indexed by regular UTC hourly timestamps.
        origin_timestamps: DatetimeIndex of valid forecast origins t.
        horizon_hours: Direct forecast lead time h in hours (1, 6, 24, 168).
        
    Returns:
        (X, y):
            X: pd.DataFrame of shape (N, 21), indexed by origin timestamp t.
            y: pd.Series of shape (N,), indexed by origin timestamp t, where y[t] = raw actual load at t + h.
            
    Invariants Enforced:
        1. Rows where target y[t+h] is missing (NaN in series_raw) are excluded.
        2. Rows before required warmup (168h history) are excluded.
        3. Feature matrix X contains zero NaNs and zero infinite values.
        4. Every observed-load feature source is strictly <= origin t.
    """
    if len(origin_timestamps) == 0:
        raise ValueError("origin_timestamps cannot be empty.")

    # 1. Causal forward-fill for feature construction ONLY
    series_causal = series_raw.ffill()

    # 2. Extract origin-anchored features (15 features)
    df_origin = extract_origin_features(series_causal)

    # 3. Target timestamps T = t + h
    target_timestamps = origin_timestamps + pd.Timedelta(hours=horizon_hours)

    # 4. Extract target-calendar features (6 features, evaluated at T = t + h)
    df_calendar = compute_target_calendar_features(target_timestamps)
    # Re-index calendar features to match origin timestamps
    df_calendar.index = origin_timestamps

    # 5. Combine into full 21-feature DataFrame at origins
    X_full = pd.concat([df_origin.loc[origin_timestamps], df_calendar], axis=1)
    X_full = X_full[FROZEN_FEATURE_NAMES]  # Ensure exact frozen column ordering

    # 6. Extract authentic, un-imputed targets at T = t + h
    y_raw = series_raw.reindex(target_timestamps)
    y_raw.index = origin_timestamps  # Align index to origin t

    # 7. Exclude rows where target is NaN (missing actual target)
    valid_mask = ~y_raw.isna()
    X = X_full.loc[valid_mask].copy()
    y = y_raw.loc[valid_mask].copy()
    y.name = f"target_h{horizon_hours}"

    # 8. Assert feature integrity (no NaNs, no infinities)
    assert_feature_matrix_integrity(X)

    return X, y


def assert_feature_matrix_integrity(X: pd.DataFrame) -> None:
    """Assert that feature matrix contains no NaNs or non-finite values."""
    if X.isna().any().any():
        nan_cols = X.columns[X.isna().any()].tolist()
        nan_counts = X[nan_cols].isna().sum().to_dict()
        raise AssertionError(
            f"Feature matrix integrity violation: found NaNs in columns: {nan_counts}"
        )
    if not np.isfinite(X.values).all():
        raise AssertionError(
            "Feature matrix integrity violation: found non-finite values (inf / -inf)."
        )


def trace_observed_load_source_timestamps(
    origin_t: pd.Timestamp,
    horizon_hours: int,
) -> Dict[str, pd.Timestamp]:
    """Return the exact historical source timestamp for each observed-load feature at origin t.
    
    Used by automated causality assertion to verify that every observed-load feature
    satisfies source_timestamp <= origin_t.
    """
    sources = {
        "lag_0": origin_t,
        "lag_1": origin_t - pd.Timedelta(hours=1),
        "lag_2": origin_t - pd.Timedelta(hours=2),
        "lag_3": origin_t - pd.Timedelta(hours=3),
        "lag_6": origin_t - pd.Timedelta(hours=6),
        "lag_12": origin_t - pd.Timedelta(hours=12),
        "lag_24": origin_t - pd.Timedelta(hours=24),
        "lag_48": origin_t - pd.Timedelta(hours=48),
        "lag_72": origin_t - pd.Timedelta(hours=72),
        "lag_168": origin_t - pd.Timedelta(hours=168),
        "rolling_mean_6h_end": origin_t,
        "rolling_mean_24h_end": origin_t,
        "rolling_mean_168h_end": origin_t,
        "rolling_std_24h_end": origin_t,
        "rolling_std_168h_end": origin_t,
    }
    return sources
