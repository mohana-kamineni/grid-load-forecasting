# Phase 2: Conservative GBDT Validation Evaluation Report

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
| **1h** | 4,356 | **116.80** | 166.72 | **1.16%** | +4.03 | 236.88 | 609.06 | 946.52 | 236.88 (Persistence) | **-120.08** | **+50.69%** |
| **6h** | 4,351 | **367.32** | 500.16 | **3.56%** | +34.88 | 1019.34 | 608.66 | 946.89 | 608.66 (Daily Seasonal-Naive) | **-241.34** | **+39.65%** |
| **24h** | 4,333 | **499.08** | 699.65 | **4.70%** | +55.79 | 609.98 | 609.98 | 948.06 | 609.98 (Persistence) | **-110.90** | **+18.18%** |
| **168h** | 4,190 | **733.48** | 984.66 | **7.21%** | +45.62 | 892.08 | 892.08 | 892.08 | 892.08 (Persistence) | **-158.60** | **+17.78%** |

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
| **Train (2022–2023)** | **1h** | 17,351 | 25 | **17,326** | $17351 - 25 = 17326$ |
| **Validation (2024 H1)** | **1h** | 4,367 | 11 | **4,356** | $4367 - 11 = 4356$ |
| **Train (2022–2023)** | **6h** | 17,346 | 25 | **17,321** | $17346 - 25 = 17321$ |
| **Validation (2024 H1)** | **6h** | 4,362 | 11 | **4,351** | $4362 - 11 = 4351$ |
| **Train (2022–2023)** | **24h** | 17,328 | 25 | **17,303** | $17328 - 25 = 17303$ |
| **Validation (2024 H1)** | **24h** | 4,344 | 11 | **4,333** | $4344 - 11 = 4333$ |
| **Train (2022–2023)** | **168h** | 17,184 | 25 | **17,159** | $17184 - 25 = 17159$ |
| **Validation (2024 H1)** | **168h** | 4,200 | 10 | **4,190** | $4200 - 10 = 4190$ |

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
