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
| **B. Daily Seasonal-Naive** | $\hat{y}_{t+h} = y_{t+h-24}$ | **Direct**: $y_{t-23} \le t$ | **Direct**: $y_{t-18} \le t$ | **Direct**: $y_t \le t$ | **Recursive**: $y_t$ (repeating 24h cycle 7 times) <br>*Alternative*: $y_{T-24}$ (fixed 24h lag from origin $T-24$) |
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
| **168h** | Daily Seasonal-Naive | fixed_lag_24 | 26,093 | **509.12** | 714.27 | **5.36%** | -2.00 |
| **168h** | Weekly Seasonal-Naive | direct | 26,093 | **677.13** | 935.82 | **6.84%** | -13.34 |

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
| **2022** | **168h** | Daily Seasonal-Naive | 8,579 | 479.40 | 671.76 | 5.02% |
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
| **2023** | **168h** | Daily Seasonal-Naive | 8,748 | 498.80 | 697.58 | 5.31% |
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
| **2024** | **168h** | Daily Seasonal-Naive | 8,766 | 548.50 | 768.99 | 5.73% |
| **2024** | **168h** | Weekly Seasonal-Naive | 8,766 | 766.45 | 1076.17 | 7.67% |

---

## 5. Descriptive External Benchmark: ENTSO-E Day-Ahead Forecast [6.1.B]

The official ENTSO-E Day-ahead Total Load Forecast [6.1.B] is compared here as a **descriptive operational benchmark**.

### Operational Context & Alignment Nuance:
* **ENTSO-E [6.1.B]** is issued once daily at **10:00 CET on day $D-1$** for all 24 hours of day $D$.
* Its operational lead time ranges from **14 hours ahead** (for hour 00:00–01:00 D) to **38 hours ahead** (for hour 23:00–24:00 D).
* It does NOT observe intraday load changes on the afternoon or evening of day $D-1$.
* Consequently, a rolling 1-hour persistence model ($\hat{y}_{T} = y_{T-1}$) operates with a massive recency advantage (1 hour ahead vs 14–38 hours ahead).
* Conversely, Daily Seasonal-Naive ($y_{T-24}$) operates with a 24-hour lead time, providing a closer heuristic counterpart.

### Mutually Aligned Comparison ($N = 26,027$ hours):

| Forecasting System | Operational Lead Time | MAE (MW) | RMSE (MW) | MAPE (%) | Pearson $r$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ENTSO-E Day-ahead Forecast [6.1.B]** | **14–38 hours** (D-1 10:00 CET) | **238.00** | **308.71** | **2.55%** | **0.9890** |
| **Rolling Persistence ($h=1$)** | 1 hour | 230.44 | 317.15 | 2.46% | — |
| **Daily Seasonal-Naive ($h=24$)** | 24 hours | 509.27 | 714.57 | 5.36% | — |
| **Weekly Seasonal-Naive ($h=168$)** | 168 hours (1 week) | 677.03 | 935.73 | 6.84% | — |

**Core Analytical Insight:**
Against a comparable 24-hour heuristic ($y_{T-24}$, MAE $509.27$ MW), the official ENTSO-E Day-ahead forecast achieves **less than half the error** (MAE $238.00$ MW, $2.55$% MAPE). This demonstrates the profound value of weather forecasts and physical scheduling in operational grid planning.

---

## 6. Methodological Findings & Scope Confirmation

1. **Horizon Behavior:**
   - At $h=1$, Persistence is the strongest baseline (MAE $230.12$ MW, $2.46$% MAPE) due to extreme short-term inertia.
   - At $h=6$, Persistence degrades severely to MAE $1,022.97$ MW ($11.07$% MAPE) as the diurnal cycle shifts, while Daily Seasonal-Naive remains stable at MAE $509.12$ MW ($5.36$%).
   - At $h=24$, Persistence from origin $t$ is mathematically identical to Daily Seasonal-Naive ($y_t = y_{T-24}$), achieving MAE $509.12$ MW.
   - At $h=168$, Weekly Seasonal-Naive achieves MAE $677.13$ MW ($6.84$%).
2. **Scope Enforcement:**
   - **Zero learned models have been built.**
   - No GBDT, neural network, hyperparameter tuning, or extra datasets have been introduced.
   - All results strictly represent the empirical forecasting floor of Project P4.
