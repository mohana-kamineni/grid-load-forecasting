"""Gate 0.4 — Artificial-Data, Flatline, and Interpolation Audit.

Directly prevents the fatal artifacts observed in the rejected industrial dataset:
1. Repeated Values / Flatlines:
   - Consecutive duplicate rate P(y_t == y_{t-1})
   - Run-length distribution
   - Maximum flatline duration
2. First Differences:
   - Delta y = y_t - y_{t-1}
   - Proportion equal to zero
   - Distribution summary (mean, std, IQR, min, max)
3. Second Differences & Linear Interpolation Detection:
   - Delta^2 y = y_t - 2*y_{t-1} + y_{t-2}
   - Detects deterministic linear interpolation: sequences where Delta^2 y == 0 and Delta y != 0 for k >= 3
4. Autocorrelation:
   - Lags 1, 24, 48, 168
   - Physical diurnal and weekly structure verification
5. Diagnostic Figures:
   - Generates and saves difference distribution and ACF plots.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from config.settings import FIGURES_DIR


@dataclass
class InterpolationSpan:
    """Record of a detected deterministic linear interpolation span."""
    start_time: str
    end_time: str
    duration_hours: int
    slope_mw_per_hour: float


@dataclass
class ArtificialDataAuditResult:
    """Overall result of Gate 0.4 Artificial-Data & Interpolation Audit."""
    passed: bool
    status: str  # PASS / FAIL / AMBIGUOUS
    total_observations: int
    consecutive_duplicate_count: int
    consecutive_duplicate_rate: float
    max_flatline_hours: int
    first_diff_zero_rate: float
    first_diff_mean: float
    first_diff_std: float
    first_diff_iqr: float
    first_diff_min: float
    first_diff_max: float
    max_linear_interpolation_hours: int
    detected_interpolation_spans: List[InterpolationSpan]
    autocorrelation_lag_1: float
    autocorrelation_lag_24: float
    autocorrelation_lag_48: float
    autocorrelation_lag_168: float
    figure_paths: List[str]
    findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def calculate_run_lengths(series: pd.Series) -> Tuple[int, List[Tuple[int, int]]]:
    """Calculate run lengths of identical consecutive values.
    
    Returns:
        (max_run_length, list_of_runs_greater_than_threshold)
    """
    if len(series) == 0:
        return 0, []

    is_duplicate = series.values[1:] == series.values[:-1]
    if not is_duplicate.any():
        return 1, []

    # Run-length encode duplicates
    runs = []
    current_run = 1
    max_run = 1

    for dup in is_duplicate:
        if dup:
            current_run += 1
            if current_run > max_run:
                max_run = current_run
        else:
            if current_run > 1:
                runs.append(current_run)
            current_run = 1
    if current_run > 1:
        runs.append(current_run)

    return max_run, runs


def detect_linear_interpolation(
    series: pd.Series,
    min_span_length: int = 3,
    tolerance: float = 1e-4,
) -> List[InterpolationSpan]:
    """Identify sequences where second difference is zero but first difference is non-zero.
    
    This is the mathematical fingerprint of deterministic linear interpolation between endpoints.
    """
    if len(series) < min_span_length + 2:
        return []

    values = series.values
    times = series.index
    delta1 = np.diff(values)
    delta2 = np.diff(delta1)

    spans: List[InterpolationSpan] = []
    in_span = False
    span_start_idx = 0

    for i in range(len(delta2)):
        # Linear interpolation signature: delta2 approx 0 AND delta1 not zero (not flatline)
        is_linear_step = (np.abs(delta2[i]) <= tolerance) and (np.abs(delta1[i]) > tolerance)
        
        if is_linear_step:
            if not in_span:
                in_span = True
                span_start_idx = i
        else:
            if in_span:
                span_length = (i - span_start_idx) + 2  # points involved
                if span_length >= min_span_length:
                    start_t = str(times[span_start_idx])
                    end_t = str(times[i + 1])
                    slope = float(delta1[span_start_idx])
                    spans.append(
                        InterpolationSpan(
                            start_time=start_t,
                            end_time=end_t,
                            duration_hours=span_length,
                            slope_mw_per_hour=slope,
                        )
                    )
                in_span = False

    if in_span:
        span_length = (len(delta2) - span_start_idx) + 2
        if span_length >= min_span_length:
            spans.append(
                InterpolationSpan(
                    start_time=str(times[span_start_idx]),
                    end_time=str(times[-1]),
                    duration_hours=span_length,
                    slope_mw_per_hour=float(delta1[span_start_idx]),
                )
            )

    return spans


def compute_autocorrelation(series: pd.Series, max_lag: int = 168) -> Dict[int, float]:
    """Compute sample autocorrelation up to max_lag."""
    s = series.dropna()
    n = len(s)
    if n <= max_lag:
        return {lag: 0.0 for lag in [1, 24, 48, 168]}

    variance = s.var()
    if variance == 0:
        return {lag: 1.0 for lag in [1, 24, 48, 168]}

    mean = s.mean()
    deviations = s - mean
    
    acf = {}
    for lag in [1, 24, 48, 168]:
        if lag < n:
            val = np.sum(deviations.iloc[:-lag].values * deviations.iloc[lag:].values) / ((n - lag) * variance)
            acf[lag] = float(val)
        else:
            acf[lag] = 0.0
    return acf


def generate_audit_plots(series: pd.Series, prefix: str = "diagnostic") -> List[str]:
    """Generate diagnostic figures for differences and autocorrelation."""
    plot_paths = []
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    delta1 = series.diff().dropna()
    delta2 = delta1.diff().dropna()

    # 1. Differences plot
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    
    axes[0].hist(delta1, bins=100, color="steelblue", edgecolor="black", alpha=0.7)
    axes[0].set_title("First Differences: $\\Delta y_t = y_t - y_{t-1}$ [MW]")
    axes[0].set_xlabel("Hourly Load Change (MW)")
    axes[0].set_ylabel("Count")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    axes[1].hist(delta2, bins=100, color="darkorange", edgecolor="black", alpha=0.7)
    axes[1].set_title("Second Differences: $\\Delta^2 y_t = y_t - 2y_{t-1} + y_{t-2}$ [MW]")
    axes[1].set_xlabel("Second Difference (MW)")
    axes[1].set_ylabel("Count")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    diff_path = FIGURES_DIR / f"{prefix}_differences.png"
    fig.savefig(diff_path, dpi=150)
    plt.close(fig)
    plot_paths.append(str(diff_path))

    # 2. Autocorrelation plot up to 168 hours
    lags = list(range(1, 169))
    s_clean = series.dropna()
    n = len(s_clean)
    dev = s_clean - s_clean.mean()
    var = s_clean.var()
    acf_vals = []
    for l in lags:
        if l < n and var > 0:
            acf_vals.append(np.sum(dev.iloc[:-l].values * dev.iloc[l:].values) / ((n - l) * var))
        else:
            acf_vals.append(0.0)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(lags, acf_vals, color="navy", lw=1.5)
    ax.axhline(0, color="black", lw=0.8, linestyle="--")
    # Highlight 24h and 168h lags
    ax.axvline(24, color="crimson", linestyle=":", label="24h Diurnal Lag")
    ax.axvline(168, color="forestgreen", linestyle=":", label="168h Weekly Lag")
    ax.set_title("Autocorrelation Function (ACF) up to 168 Hours (1 Week)")
    ax.set_xlabel("Lag (Hours)")
    ax.set_ylabel("Autocorrelation")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    acf_path = FIGURES_DIR / f"{prefix}_acf.png"
    fig.savefig(acf_path, dpi=150)
    plt.close(fig)
    plot_paths.append(str(acf_path))

    return plot_paths


def audit_artificial_data(
    df: pd.DataFrame,
    target_col: str = "load_mw",
    generate_plots: bool = True,
    plot_prefix: str = "diagnostic",
) -> ArtificialDataAuditResult:
    """Execute Gate 0.4 Artificial-Data and Interpolation Audit."""
    findings = []
    errors = []

    if df.empty or target_col not in df.columns:
        errors.append(f"Target column '{target_col}' not found or DataFrame empty.")
        return ArtificialDataAuditResult(
            passed=False,
            status="FAIL",
            total_observations=0,
            consecutive_duplicate_count=0,
            consecutive_duplicate_rate=0.0,
            max_flatline_hours=0,
            first_diff_zero_rate=0.0,
            first_diff_mean=0.0,
            first_diff_std=0.0,
            first_diff_iqr=0.0,
            first_diff_min=0.0,
            first_diff_max=0.0,
            max_linear_interpolation_hours=0,
            detected_interpolation_spans=[],
            autocorrelation_lag_1=0.0,
            autocorrelation_lag_24=0.0,
            autocorrelation_lag_48=0.0,
            autocorrelation_lag_168=0.0,
            figure_paths=[],
            findings=findings,
            errors=errors,
        )

    series = df[target_col].astype(float)
    total_obs = len(series)

    # 1. Flatlines & Repeated Values
    max_run, all_runs = calculate_run_lengths(series)
    consec_dups = (series.values[1:] == series.values[:-1]).sum()
    consec_dup_rate = float(consec_dups / (total_obs - 1)) if total_obs > 1 else 0.0

    findings.append(f"Consecutive duplicate count: {consec_dups} ({consec_dup_rate:.4%})")
    findings.append(f"Maximum flatline run length: {max_run} hours")

    # Threshold checks
    if max_run > 6:
        errors.append(
            f"FAIL: Unacceptable flatline detected. Maximum continuous identical load is {max_run} hours (> 6h threshold)."
        )
    elif max_run > 3:
        findings.append(f"WARNING: Flatline of {max_run} hours detected. Requires verification.")

    if consec_dup_rate > 0.02:
        errors.append(
            f"FAIL: Consecutive duplicate rate is {consec_dup_rate:.2%} (> 2.0% threshold for regional bidding zone load)."
        )

    # 2. First Differences
    delta1 = series.diff().dropna()
    d1_zeros = (delta1 == 0).sum()
    d1_zero_rate = float(d1_zeros / len(delta1)) if len(delta1) > 0 else 0.0
    d1_mean = float(delta1.mean())
    d1_std = float(delta1.std())
    q25, q75 = delta1.quantile(0.25), delta1.quantile(0.75)
    d1_iqr = float(q75 - q25)
    d1_min = float(delta1.min())
    d1_max = float(delta1.max())

    findings.append(f"First differences: mean={d1_mean:.2f} MW, std={d1_std:.2f} MW, IQR={d1_iqr:.2f} MW")
    findings.append(f"Delta y zero rate: {d1_zero_rate:.4%}")

    # 3. Second Differences & Deterministic Linear Interpolation
    interp_spans = detect_linear_interpolation(series, min_span_length=3)
    max_interp_hours = max([s.duration_hours for s in interp_spans], default=0)
    multi_step_spans = [s for s in interp_spans if s.duration_hours >= 4]

    if max_interp_hours >= 6:
        errors.append(
            f"FAIL: Deterministic linear interpolation detected: {len(interp_spans)} spans found, "
            f"longest span = {max_interp_hours} hours. Delta^2 y is artificially zero."
        )
    elif max_interp_hours >= 4:
        findings.append(
            f"WARNING: Short linear interpolation sequence of {max_interp_hours} hours detected ({len(multi_step_spans)} multi-step spans)."
        )
    else:
        if len(interp_spans) > 0:
            findings.append(
                f"Detected {len(interp_spans)} isolated 3-point sequences (single second-difference zero, k=1) "
                f"consistent with integer telemetry quantization; 0 multi-step linear interpolation spans (duration >= 4h, k >= 2) detected."
            )
        else:
            findings.append("Zero artificial linear interpolation spans detected (min span >= 3 points).")


    # 4. Autocorrelation
    acf = compute_autocorrelation(series, max_lag=168)
    findings.append(
        f"ACF: lag-1={acf[1]:.4f}, lag-24={acf[24]:.4f}, lag-48={acf[48]:.4f}, lag-168={acf[168]:.4f}"
    )

    # Check physical plausibility of ACF
    if acf[1] < 0.70:
        errors.append(f"Suspiciously low lag-1 autocorrelation: {acf[1]:.4f} (< 0.70 for hourly grid load).")
    if acf[24] < 0.40:
        errors.append(f"Suspiciously weak diurnal 24h cycle: lag-24 ACF = {acf[24]:.4f} (< 0.40).")

    # 5. Diagnostic Figures
    plot_paths = []
    if generate_plots:
        try:
            plot_paths = generate_audit_plots(series, prefix=plot_prefix)
            findings.append(f"Generated diagnostic figures: {plot_paths}")
        except Exception as e:
            findings.append(f"Plot generation skipped or failed: {e}")

    passed = len(errors) == 0
    status = "PASS" if passed else "FAIL"
    if passed:
        findings.append(
            "No evidence of the tested artificial-data signatures was detected under the implemented diagnostics and thresholds."
        )


    return ArtificialDataAuditResult(
        passed=passed,
        status=status,
        total_observations=total_obs,
        consecutive_duplicate_count=consec_dups,
        consecutive_duplicate_rate=consec_dup_rate,
        max_flatline_hours=max_run,
        first_diff_zero_rate=d1_zero_rate,
        first_diff_mean=d1_mean,
        first_diff_std=d1_std,
        first_diff_iqr=d1_iqr,
        first_diff_min=d1_min,
        first_diff_max=d1_max,
        max_linear_interpolation_hours=max_interp_hours,
        detected_interpolation_spans=interp_spans,
        autocorrelation_lag_1=acf[1],
        autocorrelation_lag_24=acf[24],
        autocorrelation_lag_48=acf[48],
        autocorrelation_lag_168=acf[168],
        figure_paths=plot_paths,
        findings=findings,
        errors=errors,
    )
