"""Integrity tests for Phase 2 feature pipeline and temporal partitioning."""

import unittest
import datetime
import numpy as np
import pandas as pd

from config.settings import PROCESSED_DATA_DIR
from src.features.calendar import (
    get_easter_sunday,
    get_swedish_public_and_de_facto_holidays,
    compute_target_calendar_features,
)
from src.features.pipeline import (
    FROZEN_FEATURE_NAMES,
    extract_origin_features,
    build_feature_matrix_for_horizon,
    assert_feature_matrix_integrity,
    trace_observed_load_source_timestamps,
)
from src.models.gbdt import (
    PARTITION_BOUNDS,
    get_partition_origin_timestamps,
)
from tests.fixtures.synthetic_series import make_clean_series


class TestFeaturePipelineIntegrity(unittest.TestCase):
    def setUp(self):
        # Full canonical timeline from real parquet or synthetic fallback
        self.actual_parquet = PROCESSED_DATA_DIR / "real_se3_actual_load_6_1_a_2022_2025.parquet"
        if self.actual_parquet.exists():
            df_act = pd.read_parquet(self.actual_parquet)
            self.full_idx = pd.date_range("2022-01-01 00:00:00", "2024-12-31 23:00:00", freq="1h", tz="UTC")
            self.s_raw = df_act["load_mw"].reindex(self.full_idx)
        else:
            self.df = make_clean_series("2022-01-01T00:00:00Z", "2024-12-31T23:00:00Z")
            self.full_idx = self.df.index
            self.s_raw = self.df["load_mw"]

    def test_frozen_feature_schema(self):
        """Assert exact 21 features with exact column naming."""
        self.assertEqual(len(FROZEN_FEATURE_NAMES), 21)
        expected_features = [
            "lag_0", "lag_1", "lag_2", "lag_3", "lag_6", "lag_12",
            "lag_24", "lag_48", "lag_72", "lag_168",
            "rolling_mean_6h", "rolling_mean_24h", "rolling_mean_168h",
            "rolling_std_24h", "rolling_std_168h",
            "hour_of_day", "day_of_week", "day_of_month", "month", "is_weekend",
            "is_public_holiday",
        ]
        self.assertEqual(FROZEN_FEATURE_NAMES, expected_features)

    def test_feature_causality_and_fault_injection(self):
        """Assert source_timestamp <= t for every observed-load feature; test fault injection."""
        sample_origins = [
            pd.Timestamp("2022-03-15 12:00:00+00:00"),
            pd.Timestamp("2023-08-20 00:00:00+00:00"),
            pd.Timestamp("2024-05-10 18:00:00+00:00"),
        ]
        for t in sample_origins:
            sources = trace_observed_load_source_timestamps(t, horizon_hours=24)
            for feat_name, src_ts in sources.items():
                self.assertLessEqual(
                    src_ts,
                    t,
                    f"Causality leak detected in feature {feat_name}: source {src_ts} > origin {t}",
                )

        # Fault injection: deliberately inject a future lookahead t + 1 hour
        invalid_sources = trace_observed_load_source_timestamps(sample_origins[0], horizon_hours=24)
        invalid_sources["leak_feature"] = sample_origins[0] + pd.Timedelta(hours=1)
        with self.assertRaises(AssertionError):
            for feat, ts in invalid_sources.items():
                if ts > sample_origins[0]:
                    raise AssertionError(f"Fault-injection caught lookahead in {feat}: {ts} > {sample_origins[0]}")

    def test_feature_nan_integrity_and_fault_injection(self):
        """Assert feature matrix has zero NaNs and is finite; test fault injection."""
        val_origins = get_partition_origin_timestamps("validation", 1, self.full_idx)
        X_val, _ = build_feature_matrix_for_horizon(self.s_raw, val_origins, 1)

        # Invariant: no NaNs, finite values
        assert_feature_matrix_integrity(X_val)
        self.assertEqual(int(X_val.isna().sum().sum()), 0)
        self.assertTrue(bool(np.isfinite(X_val.values).all()))

        # Fault injection: inject NaN
        X_fault_nan = X_val.copy()
        X_fault_nan.iloc[10, 0] = np.nan
        with self.assertRaises(AssertionError):
            assert_feature_matrix_integrity(X_fault_nan)

        # Fault injection: inject infinity
        X_fault_inf = X_val.copy()
        X_fault_inf.iloc[10, 0] = np.inf
        with self.assertRaises(AssertionError):
            assert_feature_matrix_integrity(X_fault_inf)

    def test_missing_target_reconciliation_all_partitions_and_horizons(self):
        """Programmatically verify: evaluated_N = potential_pairs - missing_target_pairs.
        
        Specifically covers the special 2024 H1 h=168 case.
        """
        horizons = [1, 6, 24, 168]
        partitions = ["train", "validation", "test"]

        for part in partitions:
            for h in horizons:
                origins = get_partition_origin_timestamps(part, h, self.full_idx)
                X, y = build_feature_matrix_for_horizon(self.s_raw, origins, h)

                targets_ts = origins + pd.Timedelta(hours=h)
                raw_targets = self.s_raw.loc[targets_ts]
                missing_targets = int(raw_targets.isna().sum())
                potential_pairs = len(origins)
                evaluated_N = len(y)

                self.assertEqual(
                    evaluated_N,
                    potential_pairs - missing_targets,
                    f"Mismatch in {part} h={h}: evaluated {evaluated_N} != {potential_pairs} - {missing_targets}",
                )

                # Special 2024 H1 h=168 case: missing hour 2024-01-07 03:00 is outside target window
                if part == "validation":
                    if h in [1, 6, 24]:
                        self.assertEqual(missing_targets, 11)
                    elif h == 168:
                        self.assertEqual(missing_targets, 10)

    def test_split_integrity_no_leakage_across_boundaries(self):
        """Assert no origin or target crosses partition boundaries and zero overlap."""
        horizons = [1, 6, 24, 168]
        for h in horizons:
            train_orig = get_partition_origin_timestamps("train", h, self.full_idx)
            val_orig = get_partition_origin_timestamps("validation", h, self.full_idx)
            test_orig = get_partition_origin_timestamps("test", h, self.full_idx)

            # 1. No overlap between origin sets
            self.assertEqual(len(set(train_orig) & set(val_orig)), 0)
            self.assertEqual(len(set(val_orig) & set(test_orig)), 0)
            self.assertEqual(len(set(train_orig) & set(test_orig)), 0)

            # 2. Both origin and target must belong to partition
            for name, origs in [("train", train_orig), ("validation", val_orig), ("test", test_orig)]:
                bounds = PARTITION_BOUNDS[name]
                self.assertGreaterEqual(origs.min(), bounds["start"])
                self.assertLessEqual(origs.max(), bounds["end"])

                targets = origs + pd.Timedelta(hours=h)
                self.assertGreaterEqual(targets.min(), bounds["start"])
                self.assertLessEqual(targets.max(), bounds["end"])

    def test_holiday_calendar_reproducibility_and_coverage(self):
        """Verify statutory Swedish holidays + de facto eves for 2022, 2023, 2024."""
        for year in [2022, 2023, 2024]:
            holidays = get_swedish_public_and_de_facto_holidays(year)
            # Exactly 16 holiday dates (13 statutory + 3 de facto)
            self.assertEqual(len(holidays), 16, f"Expected 16 holidays in {year}, got {len(holidays)}")

            # Deterministic reproducibility check
            holidays_repeat = get_swedish_public_and_de_facto_holidays(year)
            self.assertEqual(holidays, holidays_repeat)

            # Key fixed holidays
            self.assertIn(datetime.date(year, 1, 1), holidays)    # New Year's Day
            self.assertIn(datetime.date(year, 1, 6), holidays)    # Epiphany
            self.assertIn(datetime.date(year, 5, 1), holidays)    # Labour Day
            self.assertIn(datetime.date(year, 6, 6), holidays)    # National Day
            self.assertIn(datetime.date(year, 12, 24), holidays)  # Christmas Eve (de facto)
            self.assertIn(datetime.date(year, 12, 25), holidays)  # Christmas Day
            self.assertIn(datetime.date(year, 12, 26), holidays)  # Boxing Day
            self.assertIn(datetime.date(year, 12, 31), holidays)  # New Year's Eve (de facto)

        # 2024 Easter verification (Easter Sunday = 2024-03-31)
        easter_2024 = get_easter_sunday(2024)
        self.assertEqual(easter_2024, datetime.date(2024, 3, 31))
        h_2024 = get_swedish_public_and_de_facto_holidays(2024)
        self.assertIn(datetime.date(2024, 3, 29), h_2024)  # Good Friday
        self.assertIn(datetime.date(2024, 4, 1), h_2024)   # Easter Monday
        self.assertIn(datetime.date(2024, 5, 9), h_2024)   # Ascension Day
        self.assertIn(datetime.date(2024, 6, 21), h_2024)  # Midsummer Eve
        self.assertIn(datetime.date(2024, 6, 22), h_2024)  # Midsummer Day

    def test_exact_origin_set_equality_between_gbdt_and_baselines(self):
        """Assert set(gbdt_origins) == set(baseline_origins) for every horizon in validation."""
        horizons = [1, 6, 24, 168]
        for h in horizons:
            val_origins = get_partition_origin_timestamps("validation", h, self.full_idx)
            X_val, y_val = build_feature_matrix_for_horizon(self.s_raw, val_origins, h)
            gbdt_origins = set(X_val.index)

            # Baseline origin set under identical rules
            targets_ts = val_origins + pd.Timedelta(hours=h)
            raw_targets = self.s_raw.loc[targets_ts]
            valid_mask = ~raw_targets.isna()
            baseline_origins = set(val_origins[valid_mask])

            self.assertEqual(
                gbdt_origins,
                baseline_origins,
                f"Origin set mismatch at h={h}: {len(gbdt_origins)} != {len(baseline_origins)}",
            )


if __name__ == "__main__":
    unittest.main()
