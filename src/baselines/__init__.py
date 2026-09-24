"""Baselines module for Project P4: Grid Load Forecasting.

Implements non-learned heuristic baselines:
- Persistence: hat{y}_{t+h} = y_t
- Daily Seasonal-Naive: hat{y}_{t+h} = y_{t+h-24}
- Weekly Seasonal-Naive: hat{y}_{t+h} = y_{t+h-168}
"""

from src.baselines.models import (
    PersistenceBaseline,
    DailySeasonalNaiveBaseline,
    WeeklySeasonalNaiveBaseline,
    BaselineMetrics,
    evaluate_baseline,
)

__all__ = [
    "PersistenceBaseline",
    "DailySeasonalNaiveBaseline",
    "WeeklySeasonalNaiveBaseline",
    "BaselineMetrics",
    "evaluate_baseline",
]
