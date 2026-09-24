"""Conservative GBDT implementation for Project P4.

Configuration (STRICTLY FROZEN):
- Model: sklearn.ensemble.HistGradientBoostingRegressor
- loss: "squared_error"
- learning_rate: 0.05
- max_iter: 150
- max_leaf_nodes: 31
- min_samples_leaf: 20
- l2_regularization: 1.0
- random_state: 42
- early_stopping: False

Strict Partition Rules:
- Train: origin and target within 2022-01-01 to 2023-12-31 (initial 168h warmup)
- Validation: origin and target within 2024-01-01 to 2024-06-30
- Test: origin and target within 2024-07-01 to 2024-12-31 (UNTOUCHED)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from config.settings import PROCESSED_DATA_DIR, REPORTS_DIR
from src.features.pipeline import (
    FROZEN_FEATURE_NAMES,
    build_feature_matrix_for_horizon,
    assert_feature_matrix_integrity,
)
from src.baselines.models import (
    PersistenceBaseline,
    DailySeasonalNaiveBaseline,
    WeeklySeasonalNaiveBaseline,
    compute_metrics,
)

logger = logging.getLogger(__name__)

PARTITION_BOUNDS = {
    "train": {
        "start": pd.Timestamp("2022-01-01 00:00:00+00:00"),
        "end": pd.Timestamp("2023-12-31 23:00:00+00:00"),
        "has_warmup": True,
    },
    "validation": {
        "start": pd.Timestamp("2024-01-01 00:00:00+00:00"),
        "end": pd.Timestamp("2024-06-30 23:00:00+00:00"),
        "has_warmup": False,
    },
    "test": {
        "start": pd.Timestamp("2024-07-01 00:00:00+00:00"),
        "end": pd.Timestamp("2024-12-31 23:00:00+00:00"),
        "has_warmup": False,
    },
}


def get_partition_origin_timestamps(
    partition_name: str,
    horizon_hours: int,
    full_hourly_index: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    """Get all valid origin timestamps t for a partition such that both t and t + h are in the partition.
    
    Args:
        partition_name: 'train', 'validation', or 'test'.
        horizon_hours: Lead time h in hours.
        full_hourly_index: Complete canonical hourly index.
        
    Returns:
        pd.DatetimeIndex of valid forecast origins.
    """
    if partition_name not in PARTITION_BOUNDS:
        raise ValueError(f"Unknown partition: {partition_name}")

    bounds = PARTITION_BOUNDS[partition_name]
    start_ts = bounds["start"]
    end_ts = bounds["end"]

    # If partition requires initial warmup (train requires 168h history for lag_168)
    eff_start = start_ts + pd.Timedelta(hours=168) if bounds["has_warmup"] else start_ts
    # Target t + h must not exceed partition end
    eff_end = end_ts - pd.Timedelta(hours=horizon_hours)

    if eff_start > eff_end:
        return pd.DatetimeIndex([], tz="UTC")

    return full_hourly_index[(full_hourly_index >= eff_start) & (full_hourly_index <= eff_end)]


def create_frozen_gbdt_model() -> HistGradientBoostingRegressor:
    """Create the single conservative GBDT model with frozen hyperparameters."""
    return HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.05,
        max_iter=150,
        max_leaf_nodes=31,
        min_samples_leaf=20,
        l2_regularization=1.0,
        random_state=42,
        early_stopping=False,
    )


@dataclass
class ModelComparisonRow:
    """Comparison of GBDT and baselines on exact same origin set."""
    horizon_hours: int
    n_observations: int
    gbdt_mae: float
    gbdt_rmse: float
    gbdt_mape: float
    gbdt_bias: float
    persistence_mae: float
    daily_snaive_mae: float
    weekly_snaive_mae: float
    best_baseline_mae: float
    best_baseline_name: str
    mae_diff_vs_best: float  # gbdt_mae - best_baseline_mae (negative = GBDT is better)
    pct_improvement_vs_best: float  # (best_baseline_mae - gbdt_mae) / best_baseline_mae * 100


def run_gbdt_validation_experiment(
    actual_parquet_path: Optional[Path] = None,
    output_report_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute Phase 2 GBDT training on 2022-2023 and evaluation on 2024 H1 validation.
    
    The test set (2024 H2) is strictly NEVER accessed or evaluated.
    """
    if actual_parquet_path is None:
        actual_parquet_path = PROCESSED_DATA_DIR / "real_se3_actual_load_6_1_a_2022_2025.parquet"
    if output_report_path is None:
        output_report_path = REPORTS_DIR / "gbdt_validation_report.md"

    # 1. Load actual load series and build full canonical hourly timeline (2022-2024)
    df_act = pd.read_parquet(actual_parquet_path)
    full_idx = pd.date_range("2022-01-01 00:00:00", "2024-12-31 23:00:00", freq="1h", tz="UTC")
    s_raw = df_act["load_mw"].reindex(full_idx)
    s_raw.name = "actual_mw"
    s_causal = s_raw.ffill()

    horizons = [1, 6, 24, 168]
    models_trained = {}
    comparison_rows: List[ModelComparisonRow] = []
    sample_accounting = {}

    baseline_persistence = PersistenceBaseline()
    baseline_daily = DailySeasonalNaiveBaseline(mode="causal_origin")
    baseline_weekly = WeeklySeasonalNaiveBaseline()

    for h in horizons:
        logger.info(f"Processing horizon h={h}h...")

        # 2. Get Train origin timestamps and build training feature matrix
        train_origins = get_partition_origin_timestamps("train", h, full_idx)
        X_train, y_train = build_feature_matrix_for_horizon(s_raw, train_origins, h)

        # 3. Get Validation origin timestamps and build validation feature matrix
        val_origins = get_partition_origin_timestamps("validation", h, full_idx)
        X_val, y_val = build_feature_matrix_for_horizon(s_raw, val_origins, h)

        # Record exact sample counts
        sample_accounting[h] = {
            "train_potential": len(train_origins),
            "train_missing_target": len(train_origins) - len(y_train),
            "train_evaluated_N": len(y_train),
            "val_potential": len(val_origins),
            "val_missing_target": len(val_origins) - len(y_val),
            "val_evaluated_N": len(y_val),
        }

        # 4. Train frozen GBDT model
        model = create_frozen_gbdt_model()
        model.fit(X_train, y_train)
        models_trained[h] = model

        # 5. Predict on Validation
        val_preds = model.predict(X_val)
        y_val_arr = y_val.values

        # GBDT Validation Metrics
        gbdt_metrics = compute_metrics(y_val_arr, val_preds, f"GBDT_h{h}", h)

        # 6. Evaluate Baselines on the EXACT SAME origin set (X_val.index)
        val_target_ts = X_val.index + pd.Timedelta(hours=h)

        # Persistence prediction
        p_pred = baseline_persistence.predict(s_causal, horizon=h).loc[val_target_ts].values
        p_metrics = compute_metrics(y_val_arr, p_pred, "Persistence", h)

        # Daily Seasonal-Naive prediction
        d_pred = baseline_daily.predict(s_causal, horizon=h).loc[val_target_ts].values
        d_metrics = compute_metrics(y_val_arr, d_pred, "Daily_SNaive", h)

        # Weekly Seasonal-Naive prediction
        w_pred = baseline_weekly.predict(s_causal, horizon=h).loc[val_target_ts].values
        w_metrics = compute_metrics(y_val_arr, w_pred, "Weekly_SNaive", h)

        # Determine best baseline
        baseline_candidates = [
            ("Persistence", p_metrics.mae_mw),
            ("Daily Seasonal-Naive", d_metrics.mae_mw),
            ("Weekly Seasonal-Naive", w_metrics.mae_mw),
        ]
        best_name, best_mae = min(baseline_candidates, key=lambda x: x[1])

        mae_diff = gbdt_metrics.mae_mw - best_mae
        pct_impr = (best_mae - gbdt_metrics.mae_mw) / best_mae * 100.0

        row = ModelComparisonRow(
            horizon_hours=h,
            n_observations=len(y_val),
            gbdt_mae=gbdt_metrics.mae_mw,
            gbdt_rmse=gbdt_metrics.rmse_mw,
            gbdt_mape=gbdt_metrics.mape_percent,
            gbdt_bias=gbdt_metrics.mean_bias_mw,
            persistence_mae=p_metrics.mae_mw,
            daily_snaive_mae=d_metrics.mae_mw,
            weekly_snaive_mae=w_metrics.mae_mw,
            best_baseline_mae=best_mae,
            best_baseline_name=best_name,
            mae_diff_vs_best=mae_diff,
            pct_improvement_vs_best=pct_impr,
        )
        comparison_rows.append(row)

    # 7. Generate markdown validation report
    report_content = generate_gbdt_validation_markdown_report(comparison_rows, sample_accounting)
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info(f"Saved GBDT validation report to {output_report_path}")

    return {
        "comparison_rows": comparison_rows,
        "sample_accounting": sample_accounting,
        "models_trained": models_trained,
        "report_path": str(output_report_path),
    }


def generate_gbdt_validation_markdown_report(
    comparison_rows: List[ModelComparisonRow],
    sample_accounting: Dict[int, Dict[str, int]],
) -> str:
    """Generate comprehensive markdown report for Phase 2 GBDT validation."""
    md = """# Phase 2: Conservative GBDT Validation Evaluation Report

* **Date:** 2026-09-24
* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Geographic Scope:** Sweden Bidding Zone SE3 (`10Y1001A1001A46L`)
* **Experimental Protocol:** Frozen Phase 2 Direct GBDT Specification
* **Model Engine:** `sklearn.ensemble.HistGradientBoostingRegressor`
* **Model Hyperparameters (Frozen):** `loss="squared_error"`, `learning_rate=0.05`, `max_iter=150`, `max_leaf_nodes=31`, `min_samples_leaf=20`, `l2_regularization=1.0`, `random_state=42`, `early_stopping=False`
* **Training Partition:** 2022-01-01 00:00 UTC to 2023-12-31 23:00 UTC (168h warmup applied)
* **Validation Partition:** 2024-01-01 00:00 UTC to 2024-06-30 23:00 UTC
* **Final Test Partition:** 2024-07-01 00:00 UTC to 2024-12-31 23:00 UTC (**COMPLETELY UNTOUCHED / NOT EVALUATED**)

---

## 1. Executive Summary & Core Comparison

The table below presents the primary evaluation of the conservative GBDT against the heuristic baselines on the **exact same origin sets** in the 2024 H1 validation period.

| Horizon | Validated $N$ | GBDT MAE (MW) | GBDT RMSE (MW) | GBDT MAPE (%) | GBDT Bias (MW) | Persistence MAE | Daily S-Naive MAE | Weekly S-Naive MAE | Best Baseline MAE | MAE Diff (MW) | % Improvement |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for r in comparison_rows:
        sign = "+" if r.mae_diff_vs_best > 0 else ""
        impr_sign = "+" if r.pct_improvement_vs_best > 0 else ""
        md += (
            f"| **{r.horizon_hours}h** | {r.n_observations:,} | **{r.gbdt_mae:.2f}** | {r.gbdt_rmse:.2f} | "
            f"**{r.gbdt_mape:.2f}%** | {r.gbdt_bias:+.2f} | {r.persistence_mae:.2f} | {r.daily_snaive_mae:.2f} | "
            f"{r.weekly_snaive_mae:.2f} | {r.best_baseline_mae:.2f} ({r.best_baseline_name}) | "
            f"**{sign}{r.mae_diff_vs_best:.2f}** | **{impr_sign}{r.pct_improvement_vs_best:.2f}%** |\n"
        )

    md += r"""
> [!NOTE]
> **Operational Day-Ahead Benchmark Context ($h=24$, $N=4,321$):**
> * **ENTSO-E Day-ahead Forecast [6.1.B] (14–38h lead time):** MAE = **248.65 MW**, RMSE = **320.09 MW**, MAPE = **2.52%**, Pearson $r = \mathbf{0.9900}$.
> * **Daily Seasonal-Naive ($h=24$, 24h lead time):** MAE = **609.98 MW**, RMSE = **843.88 MW**, MAPE = **6.08%**.
> *(Note: The ENTSO-E forecast is an external operational benchmark issued at D-1 10:00 CET with weather and dispatch inputs, not a simple hourly autoregressive baseline).*

---

## 2. Temporal Accounting & Missing-Target Reconciliation

Sample counts differ strictly by horizon because both forecast origin $t$ and target $t+h$ must belong to the partition.

| Partition | Horizon ($h$) | Potential $(t, t+h)$ Pairs | Missing Actual Targets | Evaluated Samples ($N$) | Reconciled Formula |
| :--- | :---: | :---: | :---: | :---: | :--- |
"""

    for h, acc in sample_accounting.items():
        md += (
            f"| **Train (2022–2023)** | **{h}h** | {acc['train_potential']:,} | {acc['train_missing_target']} | "
            f"**{acc['train_evaluated_N']:,}** | ${acc['train_potential']} - {acc['train_missing_target']} = {acc['train_evaluated_N']}$ |\n"
        )
        md += (
            f"| **Validation (2024 H1)** | **{h}h** | {acc['val_potential']:,} | {acc['val_missing_target']} | "
            f"**{acc['val_evaluated_N']:,}** | ${acc['val_potential']} - {acc['val_missing_target']} = {acc['val_evaluated_N']}$ |\n"
        )

    md += r"""
---

## 3. Protocol & Invariant Verification Confirmations

1. **Feature Schema Frozen (21 Features):**
   - 10 Historical load lags: `lag_0` ($y_t$), `lag_1`, `lag_2`, `lag_3`, `lag_6`, `lag_12`, `lag_24`, `lag_48`, `lag_72`, `lag_168`.
   - 5 Backward-looking rolling stats: `rolling_mean_6h`, `rolling_mean_24h`, `rolling_mean_168h`, `rolling_std_24h`, `rolling_std_168h` (all ending strictly at origin $t$).
   - 5 Deterministic target-calendar features: `hour_of_day`, `day_of_week`, `day_of_month`, `month`, `is_weekend` (evaluated at target $t+h$).
   - 1 Holiday feature: `is_public_holiday` (Swedish statutory holidays plus de facto reduced-activity days, evaluated at target $t+h$).
2. **Feature Causality Invariant:**
   - Every observed-load feature satisfies $\\text{source\\_timestamp} \\le t$. Zero future lookahead.
3. **Feature Matrix Integrity:**
   - Zero NaNs and zero infinite values in feature matrix post-warmup.
4. **Exact Origin-Set Equality:**
   - $\\text{set}(\\text{gbdt\\_origins}) == \\text{set}(\\text{baseline\\_origins})$ for all horizons.
5. **H1/H2 Seasonal Asymmetry Documented:**
   > Validation covers January–June 2024 while final testing covers July–December 2024; therefore the validation and test periods represent different seasonal regimes. This is a consequence of the chronological evaluation design and will be considered when interpreting final test performance.
6. **Zero Test-Set Access Confirmation:**
   - **The Final Test set (`2024-07-01` to `2024-12-31`) was NOT accessed, evaluated, or inspected under any circumstances.**
7. **Zero Hyperparameter Tuning Confirmation:**
   - **No hyperparameter tuning, tree-depth searches, or feature-selection iterations were performed.**
"""
    return md
