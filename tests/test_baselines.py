"""Unit tests for Phase 1 heuristic baselines."""
import unittest
import numpy as np
import pandas as pd

from src.baselines.models import (
    PersistenceBaseline,
    DailySeasonalNaiveBaseline,
    WeeklySeasonalNaiveBaseline,
    compute_metrics,
    evaluate_baseline,
)
from tests.fixtures.synthetic_series import make_clean_series


class TestBaselines(unittest.TestCase):
    def setUp(self):
        # 30 days of synthetic data (720 hours)
        self.df = make_clean_series(
            start="2022-01-01T00:00:00Z",
            end="2022-01-30T23:00:00Z",
        )
        self.series = self.df["load_mw"]

    def test_compute_metrics_accuracy(self):
        y_true = np.array([100.0, 200.0, 300.0])
        y_pred = np.array([110.0, 190.0, 300.0])
        metrics = compute_metrics(y_true, y_pred, "TestModel", 1)
        self.assertEqual(metrics.n_observations, 3)
        self.assertAlmostEqual(metrics.mae_mw, 6.67, places=2)
        self.assertAlmostEqual(metrics.rmse_mw, 8.16, places=2)
        self.assertAlmostEqual(metrics.mape_percent, 5.0, places=1)
        self.assertAlmostEqual(metrics.mean_bias_mw, 0.0, places=2)

    def test_persistence_baseline_shifts(self):
        model = PersistenceBaseline()
        pred_1 = model.predict(self.series, horizon=1)
        self.assertEqual(len(pred_1), len(self.series))
        # Value at index 10 should equal series at index 9
        self.assertEqual(pred_1.iloc[10], self.series.iloc[9])
        self.assertTrue(np.isnan(pred_1.iloc[0]))

        pred_6 = model.predict(self.series, horizon=6)
        self.assertEqual(pred_6.iloc[10], self.series.iloc[4])

    def test_daily_seasonal_naive_shifts(self):
        model = DailySeasonalNaiveBaseline(mode="causal_origin")
        pred_24 = model.predict(self.series, horizon=24)
        self.assertEqual(pred_24.iloc[30], self.series.iloc[6])

        # Test recursive mode for h=168
        pred_168 = model.predict(self.series, horizon=168)
        # Shift back by 24 * 7 = 168
        self.assertEqual(pred_168.iloc[200], self.series.iloc[32])

    def test_weekly_seasonal_naive_shifts(self):
        model = WeeklySeasonalNaiveBaseline()
        pred_1 = model.predict(self.series, horizon=1)
        self.assertEqual(pred_1.iloc[200], self.series.iloc[32])

    def test_evaluate_baseline_excludes_nan_targets(self):
        s_with_nan = self.series.copy()
        s_with_nan.iloc[200] = np.nan
        s_with_nan.iloc[205] = np.nan

        model = PersistenceBaseline()
        metrics, y_t, y_p = evaluate_baseline(
            series_raw=s_with_nan,
            baseline_model=model,
            horizon=1,
            warmup_hours=168,
        )
        self.assertEqual(metrics.n_observations, len(self.series) - 168 - 2)
        self.assertNotIn(s_with_nan.index[200], y_t.index)
        self.assertNotIn(s_with_nan.index[205], y_t.index)

    def test_causal_forward_fill_does_not_leak_future(self):
        # Gap at index 50
        s_gapped = self.series.copy()
        s_gapped.iloc[50] = np.nan

        # Causal ffill should replace index 50 with index 49
        s_ffill = s_gapped.ffill()
        self.assertEqual(s_ffill.iloc[50], s_gapped.iloc[49])
        self.assertNotEqual(s_ffill.iloc[50], s_gapped.iloc[51])

    def test_missing_timestamp_offset_collisions_zero(self):
        """Regression test: Exhaustive pairwise collision check across all 43 missing actual-load timestamps.
        
        Validates that no two missing timestamps differ by any offset in {1, 23, 24, 144, 167, 168} hours,
        which guarantees pairwise disjointness of their affected rows {t, t+1, t+24, t+168}.
        """
        from config.settings import PROCESSED_DATA_DIR
        actual_parquet = PROCESSED_DATA_DIR / "real_se3_actual_load_6_1_a_2022_2025.parquet"
        if not actual_parquet.exists():
            self.skipTest("Real SE3 actual load dataset not found.")

        df = pd.read_parquet(actual_parquet)
        df_core = df.loc["2022-01-01 00:00:00+00:00":"2024-12-31 23:00:00+00:00"]
        full_idx = pd.date_range("2022-01-01 00:00:00", "2024-12-31 23:00:00", freq="1h", tz="UTC")
        s = df_core["load_mw"].reindex(full_idx)
        missing_ts = s[s.isna()].index

        self.assertEqual(len(missing_ts), 43)
        collision_offsets = {1, 23, 24, 144, 167, 168}
        collisions = []
        for i in range(len(missing_ts)):
            for j in range(i + 1, len(missing_ts)):
                diff_hours = abs(int((missing_ts[j] - missing_ts[i]).total_seconds() // 3600))
                if diff_hours in collision_offsets:
                    collisions.append((missing_ts[i], missing_ts[j], diff_hours))

        self.assertEqual(len(collisions), 0, f"Found pairwise collisions: {collisions}")

    def test_affected_row_union_equals_172(self):
        """Regression test: Distinct union of affected post-warmup timestamps equals exactly 172 rows.
        
        AffectedSet = union over missing t of {t, t+1, t+24, t+168} intersected with T_eval.
        """
        from config.settings import PROCESSED_DATA_DIR
        actual_parquet = PROCESSED_DATA_DIR / "real_se3_actual_load_6_1_a_2022_2025.parquet"
        if not actual_parquet.exists():
            self.skipTest("Real SE3 actual load dataset not found.")

        df = pd.read_parquet(actual_parquet)
        df_core = df.loc["2022-01-01 00:00:00+00:00":"2024-12-31 23:00:00+00:00"]
        full_idx = pd.date_range("2022-01-01 00:00:00", "2024-12-31 23:00:00", freq="1h", tz="UTC")
        s = df_core["load_mw"].reindex(full_idx)
        missing_ts = s[s.isna()].index

        warmup_hours = 168
        eval_idx = full_idx[warmup_hours:]
        eval_set = set(eval_idx)

        affected_union = set()
        for t in missing_ts:
            for offset in [0, 1, 24, 168]:
                affected_t = t + pd.Timedelta(hours=offset)
                if affected_t in eval_set:
                    affected_union.add(affected_t)

        self.assertEqual(len(affected_union), 172)

    def test_invalidity_of_y_T_minus_24_at_origin_T_minus_168(self):
        """Regression test: Assert that using y_{T-24} at origin t = T - 168 is an invalid future lookahead.
        
        For target T = t + 168, observation y_{T-24} = y_{t+144} is 144 hours in the future
        relative to origin t.
        """
        model = DailySeasonalNaiveBaseline(mode="fixed_lag_24")
        pred = model.predict(self.series, horizon=168)
        target_idx = 300
        origin_idx = target_idx - 168
        source_idx = target_idx - 24
        lookahead_hours = source_idx - origin_idx
        self.assertEqual(lookahead_hours, 144)
        self.assertGreater(lookahead_hours, 0)
        self.assertEqual(pred.iloc[target_idx], self.series.iloc[source_idx])

    def test_valid_baseline_source_timestamps(self):
        """Regression test: Assert that all valid baselines use strictly antecedent source timestamps <= origin t.
        
        For all valid baselines (Persistence, DailySeasonalNaive in causal_origin mode, WeeklySeasonalNaive)
        and all evaluated horizons h in {1, 6, 24, 168}, the source observation used for target T = t + h
        must be <= t (i.e., shift >= h).
        """
        horizons = [1, 6, 24, 168]
        models = [
            ("Persistence", PersistenceBaseline()),
            ("Daily Seasonal-Naive", DailySeasonalNaiveBaseline(mode="causal_origin")),
            ("Weekly Seasonal-Naive", WeeklySeasonalNaiveBaseline()),
        ]

        s = self.series
        target_idx = 400

        for name, model in models:
            for h in horizons:
                origin_idx = target_idx - h
                pred = model.predict(s, horizon=h)
                pred_val = pred.iloc[target_idx]

                if name == "Persistence":
                    expected_source = origin_idx
                elif name == "Daily Seasonal-Naive":
                    if h <= 24:
                        expected_source = target_idx - 24  # <= origin_idx
                    else:
                        expected_source = target_idx - 168  # = origin_idx
                elif name == "Weekly Seasonal-Naive":
                    expected_source = target_idx - 168  # <= origin_idx

                self.assertLessEqual(
                    expected_source,
                    origin_idx,
                    f"Baseline {name} at h={h} leaks future: source={expected_source} > origin={origin_idx}",
                )
                self.assertEqual(
                    pred_val,
                    s.iloc[expected_source],
                    f"Baseline {name} at h={h} does not match expected source value",
                )


if __name__ == "__main__":
    unittest.main()
