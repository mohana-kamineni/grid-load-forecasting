"""Comprehensive Gate 0.4 & Alignment analysis on real SE3 data."""
import pandas as pd
import numpy as np
from src.audit.artificial_data import (
    calculate_run_lengths,
    detect_linear_interpolation,
    compute_autocorrelation,
)

df_actual = pd.read_parquet("data/processed/real_se3_actual_load_6_1_a_2022_2025.parquet")
df_forecast = pd.read_parquet("data/processed/real_se3_day_ahead_forecast_6_1_b_2022_2025.parquet")

# 1. Filter to 2022-2024 hourly scope first for strict hourly baseline, and then full 4-year
print("==================================================")
print("GATE 0.4: ARTIFICIAL-DATA AUDIT ON REAL SE3 ACTUAL LOAD")
print("==================================================")

for label, data in [
    ("Hourly Period (2022-2024)", df_actual[df_actual.index < "2025-01-01"]),
    ("Full Acquired Series (2022-2025)", df_actual),
]:
    series = data["load_mw"].dropna()
    n = len(series)
    max_run, runs = calculate_run_lengths(series)
    dups = (series.values[1:] == series.values[:-1]).sum()
    dup_rate = dups / (n - 1)
    
    delta1 = series.diff().dropna()
    d1_zeros = (delta1 == 0).sum()
    d1_zero_rate = d1_zeros / len(delta1)
    
    interp_spans = detect_linear_interpolation(series, min_span_length=4)
    max_interp = max([s.duration_hours for s in interp_spans], default=0)
    
    acf = compute_autocorrelation(series, max_lag=168)
    
    print(f"\n--- {label} (N = {n:,}) ---")
    print(f"Load Range: {series.min():.1f} MW to {series.max():.1f} MW (Mean: {series.mean():.1f} MW, Std: {series.std():.1f} MW)")
    print(f"Consecutive Duplicates: {dups} ({dup_rate:.4%})")
    print(f"Max Flatline Duration: {max_run} hours")
    print(f"First Differences: Mean={delta1.mean():.2f} MW, Std={delta1.std():.2f} MW, IQR={(delta1.quantile(0.75)-delta1.quantile(0.25)):.2f} MW")
    print(f"Delta y == 0 rate: {d1_zero_rate:.4%}")
    print(f"Linear Interpolation Spans (length >= 4): {len(interp_spans)}, Max Duration = {max_interp} hours")
    if interp_spans:
        for s in interp_spans[:5]:
            print(f"   Span: {s.start_time} -> {s.end_time}, dur={s.duration_hours}h, slope={s.slope_mw_per_hour:.2f} MW/h")
    print(f"Autocorrelation: Lag-1={acf[1]:.4f}, Lag-24={acf[24]:.4f}, Lag-48={acf[48]:.4f}, Lag-168={acf[168]:.4f}")

print("\n==================================================")
print("ACTUAL [6.1.A] VS FORECAST [6.1.B] ALIGNMENT (2022-2024)")
print("==================================================")
sub_act = df_actual.loc["2022-01-01":"2024-12-31", ["load_mw"]].rename(columns={"load_mw": "actual_mw"})
sub_fc = df_forecast.loc["2022-01-01":"2024-12-31", ["load_mw"]].rename(columns={"load_mw": "forecast_mw"})
merged = sub_act.join(sub_fc, how="inner")
print(f"Common timestamps: {len(merged):,} (Actual: {len(sub_act)}, Forecast: {len(sub_fc)})")
error = merged["actual_mw"] - merged["forecast_mw"]
mae = error.abs().mean()
rmse = np.sqrt((error ** 2).mean())
mape = (error.abs() / merged["actual_mw"]).mean() * 100
bias = error.mean()
print(f"Day-Ahead Forecast Benchmark Performance (2022-2024):")
print(f"  MAE:  {mae:.2f} MW")
print(f"  RMSE: {rmse:.2f} MW")
print(f"  MAPE: {mape:.2f}%")
print(f"  Bias: {bias:.2f} MW (positive = actual > forecast, under-forecast)")
print(f"  Correlation: {merged['actual_mw'].corr(merged['forecast_mw']):.4f}")
