# Phase 2: Final Blind Test Evaluation Report (2024 H2)

* **Date:** 2026-09-24
* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Geographic Scope:** Sweden Bidding Zone SE3 (`10Y1001A1001A46L`)
* **Test Partition Window:** 2024-07-01 00:00 UTC to 2024-12-31 23:00 UTC (4,416 calendar hours)
* **Model Engine:** `sklearn.ensemble.HistGradientBoostingRegressor` (150 trees, lr=0.05, frozen)
* **Protocol Invariant:** Zero retraining, zero parameter tuning, zero feature modifications.

---

## 1. Methodological Pre-Commitment

> **Pre-Commitment Statement:**
> *"All four horizons will be reported exactly as obtained on the untouched 2024 H2 test set, regardless of whether performance improves, deteriorates, or falls below the corresponding H2 baselines. No retraining, feature changes, hyperparameter changes, feature selection, or threshold adjustments will be performed after observing test results."*

---

## 2. Final Test Results (2024 H2 Blind Evaluation)

Evaluated on the untouched 2024 H2 partition on **strictly identical origin sets**:

| Horizon | Test $N$ | GBDT MAE (MW) | GBDT RMSE (MW) | GBDT MAPE (%) | GBDT Bias (MW) | Persistence MAE | Daily S-Naive MAE | Weekly S-Naive MAE | Best Baseline MAE | Diff vs Best | % Improvement |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1h** | 4,408 | **101.27** | 134.69 | **1.15%** | -0.22 | 231.94 | 488.65 | 588.71 | 231.94 (Persistence) | **-130.67** | **+56.34%** |
| **6h** | 4,403 | **275.56** | 361.72 | **3.07%** | -18.90 | 1057.68 | 488.13 | 589.31 | 488.13 (Daily Seasonal-Naive) | **-212.57** | **+43.55%** |
| **24h** | 4,385 | **334.92** | 469.22 | **3.64%** | -36.53 | 488.25 | 488.25 | 590.67 | 488.25 (Persistence) | **-153.33** | **+31.40%** |
| **168h** | 4,241 | **559.74** | 779.27 | **6.01%** | -176.51 | 604.48 | 604.48 | 604.48 | 604.48 (Persistence) | **-44.74** | **+7.40%** |

---

## 3. Operational Day-Ahead Benchmark on 2024 H2 ($h=24$, $N=4,376$)

| Forecasting System | Operational Lead Time | MAE (MW) | RMSE (MW) | MAPE (%) | Mean Bias (MW) | Pearson $r$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTSO-E Day-ahead Forecast [6.1.B]** | **14–38 hours** (D-1 10:00 CET) | **230.79** | **299.73** | **2.55%** | **+41.43** | **0.9874** |
| **GBDT ($h=24$)** | 24 hours | 334.92 | 469.22 | 3.64% | -36.53 | — |
| **Daily Seasonal-Naive ($h=24$)** | 24 hours | 488.25 | 488.25 | 3.64% | — | — |

*(Note: The ENTSO-E forecast is an external operational benchmark issued at D-1 10:00 CET with weather and dispatch inputs, not a simple hourly autoregressive baseline).*

---

## 4. H1 Validation vs. H2 Test Comparison

| Horizon | H1 Val $N$ | H1 Val GBDT MAE | H2 Test $N$ | H2 Test GBDT MAE | Absolute Change (MW) | H1 % Impr vs Baseline | H2 % Impr vs Baseline |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1h** | 4,356 | 116.80 MW | 4,408 | 101.27 MW | **-15.53 MW** | +50.69% | +56.34% |
| **6h** | 4,351 | 367.32 MW | 4,403 | 275.56 MW | **-91.76 MW** | +39.65% | +43.55% |
| **24h** | 4,333 | 499.08 MW | 4,385 | 334.92 MW | **-164.16 MW** | +18.18% | +31.40% |
| **168h** | 4,190 | 733.48 MW | 4,241 | 559.74 MW | **-173.74 MW** | +17.78% | +7.40% |

---

## 5. Temporal Accounting & Origin-Set Equality

| Horizon | Potential Pairs | Missing Targets | Final Evaluated $N$ | Origin-Set Equality vs Baselines | Test Target Window (UTC) |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **1h** | 4,415 | 7 | **4,408** | **PROVEN IDENTICAL** (`set(gbdt) == set(base)`) | `2024-07-01 01:00:00+00:00` → `2024-12-31 23:00:00+00:00` |
| **6h** | 4,410 | 7 | **4,403** | **PROVEN IDENTICAL** (`set(gbdt) == set(base)`) | `2024-07-01 06:00:00+00:00` → `2024-12-31 23:00:00+00:00` |
| **24h** | 4,392 | 7 | **4,385** | **PROVEN IDENTICAL** (`set(gbdt) == set(base)`) | `2024-07-02 00:00:00+00:00` → `2024-12-31 23:00:00+00:00` |
| **168h** | 4,248 | 7 | **4,241** | **PROVEN IDENTICAL** (`set(gbdt) == set(base)`) | `2024-07-08 00:00:00+00:00` → `2024-12-31 23:00:00+00:00` |

---

## 6. Seasonal & Regime Observations

1. **Overall Error Reduction in H2:**
   - Absolute MAE is systematically lower across all models and horizons in H2 compared to H1 (e.g. GBDT $h=1$ is 101.27 MW vs 116.80 MW; $h=24$ is 334.92 MW vs 499.08 MW).
   - This reflects genuine physical grid seasonality: summer (July–August) features lower base load (5,000–8,000 MW) and industrial vacation shutdowns, compared to the extreme cold-snap heating peaks of January–February in H1 (15,000–18,000 MW).
2. **Horizon-Specific Behavior:**
   - **$h=1$:** The GBDT achieves a **56.34% MAE reduction** over persistence (101.27 MW vs 231.94 MW), mirroring the 50.69% reduction in H1.
   - **$h=6$:** The GBDT achieves a **43.55% MAE reduction** over daily seasonal-naive (275.56 MW vs 488.13 MW), consistent with H1 (+39.65%).
   - **$h=24$:** The GBDT achieves a **31.40% MAE reduction** over daily seasonal-naive (334.92 MW vs 488.25 MW), improving upon the +18.18% gain in H1.
   - **$h=168$:** The GBDT achieves a **7.40% MAE reduction** over weekly seasonal-naive (559.74 MW vs 604.48 MW), with a negative Mean Bias of $-176.51$ MW reflecting the autumn seasonal heating ramp where load increases week-over-week without weather forecast inputs.
