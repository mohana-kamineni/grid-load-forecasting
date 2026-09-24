# Phase 1: Baseline Forecasting Models Evaluation Report

* **Date:** 2026-09-24
* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Geographic Scope:** Sweden Bidding Zone SE3 (`10Y1001A1001A46L`)
* **Core Study Period:** 2022-01-01 00:00 UTC through 2024-12-31 23:00 UTC
* **Post-Warmup Evaluation Window:** 2022-01-08 00:00 UTC to 2024-12-31 23:00 UTC (26,136 physical hours)
* **Evaluated Observations ($N$):** 26,093 hours (43 missing actual target hours strictly excluded)
* **Forecasting Floor Status:** Established. **Zero learned models built.**

---

## 1. Executive Summary & Evaluation Protocol

This report establishes the **empirical forecasting floor** for Sweden SE3 hourly load forecasting across horizons $h \in [1, 6, 24, 168]$ hours.

### Protocol Invariants Enforced:
1. **Target Integrity:** True targets ($y_{t+h}$) are un-imputed; missing actuals are strictly excluded from evaluation ($N = 26,093$).
2. **Causal Information Boundary:** At forecast origin $t$, only observations $\le t$ are accessible.
3. **Causal Feature Handling:** Causal forward-fill is permitted strictly for historical lag feature generation.
4. **No Future Lookahead:** No future actual observations are utilized in any baseline.
5. **Zero Learned Models:** No GBDT, neural network, linear regression, or parameter optimization has been performed.

---

## 2. Direct vs. Recursive Horizon Specification

| Baseline Model | Mathematical Formula | Horizon $h=1$ | Horizon $h=6$ | Horizon $h=24$ | Horizon $h=168$ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **A. Persistence** | $\hat{y}_{t+h} = y_t$ | **Direct / Recursive (Identical)**: $y_t$ | **Direct / Recursive (Identical)**: $y_t$ | **Direct / Recursive (Identical)**: $y_t$ | **Direct / Recursive (Identical)**: $y_t$ |
| **B. Daily Seasonal-Naive** | $\hat{y}_{t+h} = y_{t+h-24}$ | **Direct**: $y_{t-23} \le t$ | **Direct**: $y_{t-18} \le t$ | **Direct**: $y_t \le t$ | **Recursive**: $y_t$ (repeating 24h cycle 7 times) |
| **C. Weekly Seasonal-Naive** | $\hat{y}_{t+h} = y_{t+h-168}$ | **Direct**: $y_{t-167} \le t$ | **Direct**: $y_{t-162} \le t$ | **Direct**: $y_{t-144} \le t$ | **Direct**: $y_t \le t$ |

---

## 3. Overall Baseline Performance (2022–2024 Core Scope)

Evaluation across all $N = 26,093$ valid target hours in the 3-year study:

| Horizon ($h$) | Baseline Model | Forecast Mode | Evaluated $N$ | MAE (MW) | RMSE (MW) | MAPE (%) | Mean Bias (MW) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1h** | Persistence | direct/recursive (identical) | 26,093 | **230.12** | 316.85 | **2.46%** | -0.06 |
| **1h** | Daily Seasonal-Naive | causal_origin | 26,093 | **509.12** | 714.27 | **5.36%** | -2.00 |
| **1h** | Weekly Seasonal-Naive | direct | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |
| **6h** | Persistence | direct/recursive (identical) | 26,093 | **1022.97** | 1274.45 | **11.07%** | -0.40 |
| **6h** | Daily Seasonal-Naive | causal_origin | 26,093 | **509.12** | 714.27 | **5.36%** | -2.00 |
| **6h** | Weekly Seasonal-Naive | direct | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |
| **24h** | Persistence | direct/recursive (identical) | 26,093 | **509.12** | 714.27 | **5.36%** | -2.00 |
| **24h** | Daily Seasonal-Naive | causal_origin | 26,093 | **509.12** | 714.27 | **5.36%** | -2.00 |
| **24h** | Weekly Seasonal-Naive | direct | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |
| **168h** | Persistence | direct/recursive (identical) | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |
| **168h** | Daily Seasonal-Naive | causal_origin | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |
| **168h** | Weekly Seasonal-Naive | direct | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |

> [!NOTE]
> **Diagnostic Reference for Horizon h=168:**
> **Reference only — not a valid 168-hour-ahead forecast. Uses y[T−24], which is available only 24 hours before the target and therefore represents a much shorter information horizon. Shown solely to illustrate the effect of forecast lead time.**
> * Fixed lag $y_{T-24}$ at target $T$: MAE = **509.12 MW**, RMSE = 714.27 MW, MAPE = **5.36%** ($N = 26,093$). This reference is excluded from the valid 168-hour baseline floor.

---

## 4. Annual Performance Breakdown (2022, 2023, 2024)

Stability of baseline error across individual calendar years:

| Year | Horizon ($h$) | Baseline Model | Evaluated $N$ | MAE (MW) | RMSE (MW) | MAPE (%) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **2022** | **1h** | Persistence | 8,579 | 228.47 | 313.82 | 2.43% |
| **2022** | **1h** | Daily Seasonal-Naive | 8,579 | 479.40 | 671.76 | 5.02% |
| **2022** | **1h** | Weekly Seasonal-Naive | 8,579 | 587.88 | 833.26 | 5.96% |
| **2022** | **6h** | Persistence | 8,579 | 1013.97 | 1268.02 | 10.92% |
| **2022** | **6h** | Daily Seasonal-Naive | 8,579 | 479.40 | 671.76 | 5.02% |
| **2022** | **6h** | Weekly Seasonal-Naive | 8,579 | 587.88 | 833.26 | 5.96% |
| **2022** | **24h** | Persistence | 8,579 | 479.40 | 671.76 | 5.02% |
| **2022** | **24h** | Daily Seasonal-Naive | 8,579 | 479.40 | 671.76 | 5.02% |
| **2022** | **24h** | Weekly Seasonal-Naive | 8,579 | 587.88 | 833.26 | 5.96% |
| **2022** | **168h** | Persistence | 8,579 | 587.88 | 833.26 | 5.96% |
| **2022** | **168h** | Daily Seasonal-Naive | 8,579 | 587.88 | 833.26 | 5.96% |
| **2022** | **168h** | Weekly Seasonal-Naive | 8,579 | 587.88 | 833.26 | 5.96% |
| **2023** | **1h** | Persistence | 8,748 | 227.50 | 316.23 | 2.44% |
| **2023** | **1h** | Daily Seasonal-Naive | 8,748 | 498.80 | 697.58 | 5.31% |
| **2023** | **1h** | Weekly Seasonal-Naive | 8,748 | 675.17 | 877.89 | 6.88% |
| **2023** | **6h** | Persistence | 8,748 | 1016.29 | 1269.00 | 11.04% |
| **2023** | **6h** | Daily Seasonal-Naive | 8,748 | 498.80 | 697.58 | 5.31% |
| **2023** | **6h** | Weekly Seasonal-Naive | 8,748 | 675.17 | 877.89 | 6.88% |
| **2023** | **24h** | Persistence | 8,748 | 498.80 | 697.58 | 5.31% |
| **2023** | **24h** | Daily Seasonal-Naive | 8,748 | 498.80 | 697.58 | 5.31% |
| **2023** | **24h** | Weekly Seasonal-Naive | 8,748 | 675.17 | 877.89 | 6.88% |
| **2023** | **168h** | Persistence | 8,748 | 675.17 | 877.89 | 6.88% |
| **2023** | **168h** | Daily Seasonal-Naive | 8,748 | 675.17 | 877.89 | 6.88% |
| **2023** | **168h** | Weekly Seasonal-Naive | 8,748 | 675.17 | 877.89 | 6.88% |
| **2024** | **1h** | Persistence | 8,766 | 234.35 | 320.40 | 2.50% |
| **2024** | **1h** | Daily Seasonal-Naive | 8,766 | 548.50 | 768.99 | 5.73% |
| **2024** | **1h** | Weekly Seasonal-Naive | 8,766 | 766.45 | 1076.17 | 7.67% |
| **2024** | **6h** | Persistence | 8,766 | 1038.43 | 1286.10 | 11.24% |
| **2024** | **6h** | Daily Seasonal-Naive | 8,766 | 548.50 | 768.99 | 5.73% |
| **2024** | **6h** | Weekly Seasonal-Naive | 8,766 | 766.45 | 1076.17 | 7.67% |
| **2024** | **24h** | Persistence | 8,766 | 548.50 | 768.99 | 5.73% |
| **2024** | **24h** | Daily Seasonal-Naive | 8,766 | 548.50 | 768.99 | 5.73% |
| **2024** | **24h** | Weekly Seasonal-Naive | 8,766 | 766.45 | 1076.17 | 7.67% |
| **2024** | **168h** | Persistence | 8,766 | 766.45 | 1076.17 | 7.67% |
| **2024** | **168h** | Daily Seasonal-Naive | 8,766 | 766.45 | 1076.17 | 7.67% |
| **2024** | **168h** | Weekly Seasonal-Naive | 8,766 | 766.45 | 1076.17 | 7.67% |

---

## 5. Descriptive External Benchmark: ENTSO-E Day-Ahead Forecast [6.1.B]

The official ENTSO-E Day-ahead Total Load Forecast [6.1.B] is compared here as a **descriptive operational benchmark**.

### 5.1. Lead-Time-Comparable Benchmark (24-Hour Horizon)
Where information availability and forecast horizons are more comparable:

| Forecasting System | Operational Lead Time | MAE (MW) | RMSE (MW) | MAPE (%) | Pearson $r$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ENTSO-E Day-ahead Forecast [6.1.B]** | **14–38 hours** (D-1 10:00 CET) | **238.00** | **308.71** | **2.55%** | **0.9890** |
| **Daily Seasonal-Naive ($h=24$)** | 24 hours | 509.27 | 714.57 | 5.36% | — |

### 5.2. Other Heuristic Horizons (For Descriptive Context Only)

| Forecasting System | Operational Lead Time | MAE (MW) | RMSE (MW) | MAPE (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Rolling Persistence ($h=1$)** | 1 hour | 230.44 | 317.15 | 2.46% |
| **Weekly Seasonal-Naive ($h=168$)** | 168 hours (1 week) | 677.03 | 935.73 | 6.84% |

> [!IMPORTANT]
> **Important:** The 1-hour persistence result and the ENTSO-E day-ahead forecast are evaluated at substantially different forecast lead times and are therefore not an apples-to-apples performance comparison. The ENTSO-E forecast has a documented D−1 information boundary, corresponding to approximately 14–38 hours of lead time for the delivery day. The h=1 persistence result is shown for descriptive context only.

---

## 6. Methodological Findings & Scope Confirmation

> **The baseline experiments establish empirical reference points for subsequent learned models. The 24-hour daily seasonal-naive result provides a lead-time-relevant heuristic reference, while the ENTSO-E day-ahead forecast provides an external operational benchmark where information availability and evaluation populations are aligned.**

### Detailed Observations:
1. **Short-Term Inertia:** At $h=1$, Persistence achieves MAE 230.12 MW (2.46% MAPE) due to extreme short-term grid inertia.
2. **Diurnal Shift:** By $h=6$, Persistence degrades severely to MAE 1,022.97 MW (11.07% MAPE) as the diurnal load cycle changes, whereas Daily Seasonal-Naive remains stable at MAE 509.12 MW (5.36%).
3. **Horizon Equivalences:** At $h=24$, 24-step persistence from origin $t$ is mathematically identical to daily seasonal-naive ($y_t = y_{T-24}$, MAE 509.12 MW). At $h=168$, 168-step persistence from origin $t$ is mathematically identical to weekly seasonal-naive ($y_t = y_{T-168}$, MAE 677.13 MW).
4. **Scope Enforcement:**
   - **Zero learned models have been built.**
   - No GBDT, neural network, hyperparameter tuning, or extra datasets have been introduced.
   - All results strictly represent the empirical reference floor of Project P4.
