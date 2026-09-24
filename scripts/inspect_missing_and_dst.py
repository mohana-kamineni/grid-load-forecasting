"""Forensic analysis of missing hours and DST transition behavior in real SE3 data."""
import pandas as pd
from config.settings import CONFIG

df_actual = pd.read_parquet("data/processed/real_se3_actual_load_6_1_a_2022_2025.parquet")
df_forecast = pd.read_parquet("data/processed/real_se3_day_ahead_forecast_6_1_b_2022_2025.parquet")

# 1. Missing hours check year by year (for hourly data)
for yr in [2022, 2023, 2024]:
    ideal_yr = pd.date_range(f"{yr}-01-01 00:00:00", f"{yr}-12-31 23:00:00", freq="1h", tz="UTC")
    sub = df_actual[df_actual.index.year == yr]
    missing = ideal_yr.difference(sub.index)
    print(f"\n=== Year {yr} Actual Load: {len(missing)} missing hours ===")
    for m in missing:
        print("  Missing:", m)

# 2. DST transitions check
print("\n==================================================")
print("DST TRANSITIONS IN REAL DATA")
print("==================================================")
for date_str, trans_type, exp_local_clock in CONFIG.DST_TRANSITIONS:
    start_utc = pd.Timestamp(f"{date_str} 00:00:00", tz="UTC")
    end_utc = pd.Timestamp(f"{date_str} 23:59:59", tz="UTC")
    
    slice_act = df_actual.loc[(df_actual.index >= start_utc) & (df_actual.index <= end_utc)]
    slice_fc = df_forecast.loc[(df_forecast.index >= start_utc) & (df_forecast.index <= end_utc)]
    
    # Check local clock
    df_act_local = df_actual.tz_convert("Europe/Stockholm")
    local_slice = df_act_local.loc[date_str] if date_str in df_act_local.index else pd.DataFrame()

    print(f"\nDST Date: {date_str} ({trans_type})")
    print(f"  Actual Load: {len(slice_act)} rows in UTC (unique: {slice_act.index.nunique()}), {len(local_slice)} rows in Europe/Stockholm (expected {exp_local_clock})")
    print(f"  Forecast:    {len(slice_fc)} rows in UTC (unique: {slice_fc.index.nunique()})")
