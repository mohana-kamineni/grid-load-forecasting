"""Forensic Inspection of Acquired Real ENTSO-E SE3 Data."""
import pandas as pd
import numpy as np
from pathlib import Path

df_actual = pd.read_parquet("data/processed/real_se3_actual_load_6_1_a_2022_2025.parquet")
df_forecast = pd.read_parquet("data/processed/real_se3_day_ahead_forecast_6_1_b_2022_2025.parquet")

print("==================================================")
print("ACTUAL LOAD [6.1.A] OVERVIEW")
print("==================================================")
print("Total rows:", len(df_actual))
print("Timestamp range:", df_actual.index.min(), "->", df_actual.index.max())
print("Timezone:", df_actual.index.tz)
if "resolution" in df_actual.columns:
    print("Resolution distribution:\n", df_actual["resolution"].value_counts())

for yr in [2022, 2023, 2024, 2025]:
    sub = df_actual[df_actual.index.year == yr]
    res_dict = sub["resolution"].value_counts().to_dict() if "resolution" in sub.columns else {}
    print(f"Year {yr}: {len(sub)} rows, resolutions: {res_dict}")

print("\n==================================================")
print("FORECAST [6.1.B] OVERVIEW")
print("==================================================")
print("Total rows:", len(df_forecast))
print("Timestamp range:", df_forecast.index.min(), "->", df_forecast.index.max())
if "resolution" in df_forecast.columns:
    print("Resolution distribution:\n", df_forecast["resolution"].value_counts())

for yr in [2022, 2023, 2024, 2025]:
    sub = df_forecast[df_forecast.index.year == yr]
    res_dict = sub["resolution"].value_counts().to_dict() if "resolution" in sub.columns else {}
    print(f"Year {yr}: {len(sub)} rows, resolutions: {res_dict}")

print("\n==================================================")
print("2025 RESOLUTION TRANSITION INVESTIGATION")
print("==================================================")
sub_2025 = df_actual[df_actual.index.year == 2025]
if "resolution" in sub_2025.columns:
    p15 = sub_2025[sub_2025["resolution"] == "PT15M"]
    p60 = sub_2025[sub_2025["resolution"] == "PT60M"]
    if len(p60) > 0:
        print(f"PT60M in 2025: {len(p60)} rows, range: {p60.index.min()} -> {p60.index.max()}")
    if len(p15) > 0:
        print(f"PT15M in 2025: {len(p15)} rows, range: {p15.index.min()} -> {p15.index.max()}")
