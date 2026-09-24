"""Heuristic Forecasting Baselines for Project P4.

Defines non-learned forecasting baselines to establish the empirical forecasting floor:
1. Baseline A — Persistence:
   hat{y}_{t+h} = y_t
2. Baseline B — Daily Seasonal-Naive:
   hat{y}_{t+h} = y_{t+h-24}
3. Baseline C — Weekly Seasonal-Naive:
   hat{y}_{t+h} = y_{t+h-168}

Methodological Principles:
- Strict information boundary: At forecast origin t, only data observed <= t is available.
- Missing targets in actual load are NOT imputed and are strictly excluded from evaluation.
- Causal forward-fill is permitted ONLY for constructing lag features from history.
- Zero future lookahead.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class BaselineMetrics:
    """Evaluation summary metrics for a baseline model at a specific horizon."""
    model_name: str
    horizon_hours: int
    n_observations: int
    mae_mw: float
    rmse_mw: float
    mape_percent: float
    mean_bias_mw: float
    forecast_mode: str  # 'direct' or 'recursive'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "horizon_hours": self.horizon_hours,
            "n_observations": self.n_observations,
            "mae_mw": self.mae_mw,
            "rmse_mw": self.rmse_mw,
            "mape_percent": self.mape_percent,
            "mean_bias_mw": self.mean_bias_mw,
            "forecast_mode": self.forecast_mode,
        }


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    horizon_hours: int,
    forecast_mode: str = "direct",
) -> BaselineMetrics:
    """Calculate MAE, RMSE, MAPE, and Mean Bias on aligned non-null arrays."""
    if len(y_true) == 0 or len(y_pred) == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")

    err = y_true - y_pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    mape = float(np.mean(np.abs(err / y_true)) * 100.0)
    bias = float(np.mean(err))

    return BaselineMetrics(
        model_name=model_name,
        horizon_hours=horizon_hours,
        n_observations=len(y_true),
        mae_mw=round(mae, 2),
        rmse_mw=round(rmse, 2),
        mape_percent=round(mape, 2),
        mean_bias_mw=round(bias, 2),
        forecast_mode=forecast_mode,
    )


class PersistenceBaseline:
    """Baseline A: Persistence (Last Observed Value).
    
    Formula:
        hat{y}_{t+h} = y_t
    
    Direct vs Recursive Analysis:
    - Direct: Forecaster at origin t predicts y_t directly for all h >= 1.
    - Recursive: 1-step forecast is y_t; propagating recursively forward
      (hat{y}_{t+k} = hat{y}_{t+k-1}) yields hat{y}_{t+h} = y_t.
    - Both direct and recursive formulations are mathematically identical.
    """

    def __init__(self):
        self.name = "Persistence"

    def predict(
        self,
        series_causal: pd.Series,
        horizon: int,
    ) -> pd.Series:
        """Generate persistence forecast for target timestamp T = t + h.
        
        Args:
            series_causal: Causally forward-filled historical series indexed by UTC timestamp.
            horizon: Lead time h in hours.
            
        Returns:
            pd.Series indexed by target timestamp T, where value is y_{T-h} = y_t.
        """
        # For target T = t + h, the prediction made at origin t is y_t = y_{T - h}.
        return series_causal.shift(horizon)


class DailySeasonalNaiveBaseline:
    """Baseline B: Daily Seasonal-Naive.
    
    Formula:
        hat{y}_{t+h} = y_{t+h-24}
    
    Direct vs Recursive Analysis:
    - For h <= 24 (e.g. h = 1, 6, 24):
      The index t + h - 24 <= t. Thus, y_{t+h-24} was observed historically
      at or before origin t. This is a direct forecast from origin t.
    - For h > 24 (e.g. h = 168):
      The index t + 168 - 24 = t + 144 is in the future relative to origin t.
      - Under recursive / periodic forecasting from origin t (repeating the 24h diurnal cycle):
        hat{y}_{t+k} = hat{y}_{t+k-24} for k > 24.
        For h = 168 = 7 * 24, repeating the cycle 7 times yields hat{y}_{t+168} = y_t.
      - Under direct lag-24 mapping (evaluated at target T as y_{T-24}):
        The forecast uses the observation 24 hours prior to target T (origin T - 24).
    """

    def __init__(self, mode: str = "causal_origin"):
        """
        Args:
            mode: 'causal_origin' (strictly from origin t, recursive for h > 24)
                  or 'fixed_lag_24' (always uses y_{T-24}, origin T - 24).
        """
        self.name = "Daily Seasonal-Naive"
        self.mode = mode

    def predict(
        self,
        series_causal: pd.Series,
        horizon: int,
    ) -> pd.Series:
        """Generate daily seasonal-naive forecast for target timestamp T = t + h."""
        if horizon <= 24:
            # Direct causal forecast: for target T, y_{T-24} is observed <= origin t
            return series_causal.shift(24)
        else:
            if self.mode == "causal_origin":
                # Propagate 24h cycle forward from origin t:
                # Target T = t + h; shift back by 24 * ceil(h/24) to reach origin <= t
                step_back = 24 * int(np.ceil(horizon / 24))
                return series_causal.shift(step_back)
            else:
                # Fixed lag-24 relative to target (origin T-24)
                return series_causal.shift(24)


class WeeklySeasonalNaiveBaseline:
    """Baseline C: Weekly Seasonal-Naive.
    
    Formula:
        hat{y}_{t+h} = y_{t+h-168}
    
    Direct vs Recursive Analysis:
    - For all evaluated horizons h in {1, 6, 24, 168}:
      t + h - 168 <= t.
      At target T = t + h, y_{T-168} = y_{t+h-168} was observed at or before origin t.
      - h = 1: observed 167 hours before origin t (same hour, same day-of-week last week).
      - h = 6: observed 162 hours before origin t.
      - h = 24: observed 144 hours before origin t.
      - h = 168: observed at origin t (y_t).
    - Thus, for all h <= 168, Weekly Seasonal-Naive is a direct forecast from origin t.
    """

    def __init__(self):
        self.name = "Weekly Seasonal-Naive"

    def predict(
        self,
        series_causal: pd.Series,
        horizon: int,
    ) -> pd.Series:
        """Generate weekly seasonal-naive forecast for target timestamp T = t + h."""
        # For target T = t + h, prediction is y_{T-168} = y_{t+h-168}
        return series_causal.shift(168)


def evaluate_baseline(
    series_raw: pd.Series,
    baseline_model: Any,
    horizon: int,
    eval_start: Optional[str] = None,
    eval_end: Optional[str] = None,
    warmup_hours: int = 168,
) -> Tuple[BaselineMetrics, pd.Series, pd.Series]:
    """Evaluate a baseline model under the strict P4 protocol.
    
    Args:
        series_raw: Raw, un-imputed actual load series on a regular hourly DatetimeIndex.
        baseline_model: Instance of PersistenceBaseline, DailySeasonalNaiveBaseline, or WeeklySeasonalNaiveBaseline.
        horizon: Forecast horizon in hours.
        eval_start: Optional start timestamp for evaluation (defaults to series_raw.index[warmup_hours]).
        eval_end: Optional end timestamp for evaluation (defaults to series_raw.index[-1]).
        warmup_hours: Initial warmup period in hours to ensure all historical lags are available (default 168).
        
    Returns:
        (BaselineMetrics, y_true_evaluated, y_pred_evaluated)
    """
    if not isinstance(series_raw.index, pd.DatetimeIndex):
        raise TypeError("series_raw must have DatetimeIndex.")

    # 1. Causal forward-fill for feature construction ONLY
    # Raw series preserves genuine NaNs for target evaluation
    series_causal = series_raw.ffill()

    # 2. Generate predictions aligned by target timestamp T
    y_pred_all = baseline_model.predict(series_causal, horizon=horizon)

    # 3. Determine evaluation window
    start_ts = pd.Timestamp(eval_start) if eval_start else series_raw.index[warmup_hours]
    end_ts = pd.Timestamp(eval_end) if eval_end else series_raw.index[-1]

    mask = (series_raw.index >= start_ts) & (series_raw.index <= end_ts)
    y_true_window = series_raw.loc[mask]
    y_pred_window = y_pred_all.loc[mask]

    # 4. Strict exclusion of missing targets and missing predictions
    valid_mask = (~y_true_window.isna()) & (~y_pred_window.isna())
    y_true_eval = y_true_window.loc[valid_mask]
    y_pred_eval = y_pred_window.loc[valid_mask]

    # 5. Compute metrics
    mode = getattr(baseline_model, "mode", "direct")
    if getattr(baseline_model, "name", "") == "Persistence":
        mode = "direct/recursive (identical)"
    elif getattr(baseline_model, "name", "") == "Weekly Seasonal-Naive":
        mode = "direct"

    metrics = compute_metrics(
        y_true=y_true_eval.values,
        y_pred=y_pred_eval.values,
        model_name=baseline_model.name,
        horizon_hours=horizon,
        forecast_mode=mode,
    )

    return metrics, y_true_eval, y_pred_eval
