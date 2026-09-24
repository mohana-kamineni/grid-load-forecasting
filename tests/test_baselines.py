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


if __name__ == "__main__":
    unittest.main()
