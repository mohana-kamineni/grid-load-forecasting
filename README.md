# Project P4: Data-Driven Grid Load Forecasting for Operational Planning

[![Status: Complete — Evaluated & Frozen](https://img.shields.io/badge/Status-Complete%20—%20Evaluated%20%26%20Frozen-brightgreen.svg)](#)
[![Data Source: ENTSO-E](https://img.shields.io/badge/Data%20Source-ENTSO--E%20Transparency%20Platform-blue.svg)](https://transparency.entsoe.eu/)
[![Geographic Scope: Sweden SE3](https://img.shields.io/badge/Bidding%20Zone-Sweden%20SE3-green.svg)](#)
[![Tests: 63 Passing](https://img.shields.io/badge/Tests-63%2F63%20Passing-brightgreen.svg)](#)

## 1. Project Identity & Research Question

* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Direction:** Operational excellence / data-driven decision support (aligned with industrial applied research frameworks).
* **Research Focus:** Real-world, operationally grounded electricity demand forecasting under verified physical and regulatory constraints.

### Core Research Question
> **How accurately can short-term electricity demand in the Swedish SE3 bidding zone be forecast from historical load patterns, and how does forecast performance change across prediction horizons and operating conditions?**

The primary research objective is to establish the empirical usefulness and limitations of historical-load and calendar information across operational horizons—not merely to optimize metrics on an arbitrary benchmark.

---

## 2. Methodological Foundation: Gate 0 Temporal Audit

Prior to baseline or model development, the dataset underwent an exhaustive forensic audit (**Gate 0: Provenance and Temporal Validity Audit**):

1. **Gate 0.1 — Provenance & Regulatory Status:** Verified official ENTSO-E Transparency Platform data under EU Regulation 543/2013 (Articles 6.1.a & 6.1.b) for Sweden bidding zone SE3 (`10Y1001A1001A46L`).
2. **Gate 0.2 — Timezone & DST Integrity (HARD GATE):** Evaluated in canonical UTC with Europe/Stockholm reference. All 8 Daylight Saving Time transitions across 2022–2025 verified intact (24 physical UTC hours per day; 23 wall-clock hours in spring, 25 in autumn).
3. **Gate 0.3 — Timestamp Continuity & Gap Analysis:** 
   - Core study scope formally restricted to **Option B: 2022-01-01 00:00 UTC through 2024-12-31 23:00 UTC** ($N = 26,304$ physical hours). The 2025 dataset is quarantined and documented as a future extension due to the Nordic 15-minute MTU market resolution transition on 2025-12-01 23:00 UTC.
   - Identified exactly 43 missing actual-load hours across 2022–2024 (99.837% completeness). Zero adjacent missing hours (minimum gap: 7 hours).
   - An exhaustive pairwise difference check across all $\binom{43}{2} = 903$ pairs of missing actual-load timestamps for difference offsets in $\{1, 23, 24, 144, 167, 168\}$ hours yielded **0 pairwise collisions**, mathematically proving that the affected sets $\{t, t+1, t+24, t+168\}$ are mutually pairwise disjoint and confirming the exact union size of **172 distinct post-warmup timestamps**.
4. **Gate 0.4 — Artificial-Data & Interpolation Audit:** Detected zero flatlines $> 1$ hour (0.0000% duplicate rate); zero multi-step linear interpolations ($k \ge 2$, $k \ge 3$). Asymmetric positive tail in first differences confirmed as authentic diurnal ramp physics (83.83% of $>500$ MW ramps occur at 06:00–08:00 local time).
5. **Gate 0.5 — Information Boundary & Operational Benchmark:** Documented the D-1 10:00 CET regulatory publication deadline for the ENTSO-E Day-ahead Forecast [6.1.B], enforcing that benchmark comparisons respect operational lead-time differences.

---

## 3. Dataset Specification

| Parameter | Specification | Official Reference / Code |
| :--- | :--- | :--- |
| **Authoritative Source** | ENTSO-E Transparency Platform | Regulation (EU) No 543/2013 |
| **Bidding Zone** | Sweden SE3 (Stockholm / Southern Central) | EIC: `10Y1001A1001A46L` (`SE_3`) |
| **Target Series** | Actual Total Load [6.1.A] | `documentType=A65`, `processType=A16` |
| **External Benchmark** | Day-ahead Total Load Forecast [6.1.B] | `documentType=A65`, `processType=A01` |
| **Core Temporal Scope** | 2022-01-01 00:00 UTC to 2024-12-31 23:00 UTC | 3 Complete Calendar Years (26,304 hours) |
| **Temporal Resolution** | Hourly | `PT60M` |
| **Physical Units** | Megawatts | `MW` |

---

## 4. Experimental Design & Frozen Protocol

### Chronological Splitting
Evaluation strictly follows non-overlapping chronological partitions with zero random splitting:
* **Train:** 2022-01-01 00:00 UTC → 2023-12-31 23:00 UTC (168h warmup applied)
* **Validation:** 2024-01-01 00:00 UTC → 2024-06-30 23:00 UTC
* **Final Test:** 2024-07-01 00:00 UTC → 2024-12-31 23:00 UTC (**Evaluated blind, exactly once**)

**Partition Rule:** For every evaluated pair $(t, t+h)$, both forecast origin $t$ and target $t+h$ must belong strictly to the partition.

### Target & Feature Handling Rules
* **Target Integrity:** Ground-truth targets ($y_{t+h}$) are **never imputed**. Rows with missing targets are strictly excluded from training and evaluation.
* **Causal Feature Forward-Fill:** Forward-filling missing load observations is permitted strictly for lag-feature generation ($x_t^{\text{lag}}$) using antecedent values ($y \le t$).
* **Zero Future Lookahead:** Every observed-load feature satisfies $\text{source\_timestamp} \le t$.

### Model Formulation
Four independent direct forecasting models ($X_t \to y_{t+h}$) for horizons $h \in \{1, 6, 24, 168\}$ hours using `sklearn.ensemble.HistGradientBoostingRegressor` with strictly frozen hyperparameters:
* `loss="squared_error"`, `learning_rate=0.05`, `max_iter=150`, `max_leaf_nodes=31`, `min_samples_leaf=20`, `l2_regularization=1.0`, `random_state=42`, `early_stopping=False`.

### Frozen 21-Feature Set
* **10 Historical Load Lags:** `lag_0` ($y_t$), `lag_1`, `lag_2`, `lag_3`, `lag_6`, `lag_12`, `lag_24`, `lag_48`, `lag_72`, `lag_168`.
* **5 Rolling Statistics:** `rolling_mean_6h`, `rolling_mean_24h`, `rolling_mean_168h`, `rolling_std_24h`, `rolling_std_168h` (all ending strictly at origin $t$).
* **5 Target Calendar Features:** `hour_of_day`, `day_of_week`, `day_of_month`, `month`, `is_weekend` (evaluated at target $t+h$).
* **1 Holiday Feature:** `is_public_holiday` (Swedish statutory holidays plus de facto reduced-activity days, evaluated at target $t+h$).

---

## 5. Empirical Results

### 5.1. Final Blind Test Evaluation (2024 H2 Out-of-Sample)
Evaluated on strictly identical origin sets (`set(gbdt_origins) == set(baseline_origins)`):

| Horizon | Evaluated $N$ | GBDT MAE (MW) | GBDT RMSE (MW) | GBDT MAPE (%) | GBDT Bias (MW) | Best Baseline Model | Best Baseline MAE | Diff vs Best (MW) | % Improvement |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: |
| **1h** | 4,408 | **101.27** | 134.69 | **1.15%** | -0.22 | Persistence | 231.94 | **-130.67** | **+56.34%** |
| **6h** | 4,403 | **275.56** | 361.72 | **3.07%** | -18.90 | Daily Seasonal-Naive | 488.13 | **-212.57** | **+43.55%** |
| **24h** | 4,385 | **334.92** | 469.22 | **3.64%** | -36.53 | Daily Seasonal-Naive | 488.25 | **-153.33** | **+31.40%** |
| **168h** | 4,241 | **559.74** | 779.27 | **6.01%** | -176.51 | Weekly Seasonal-Naive | 604.48 | **-44.74** | **+7.40%** |

### 5.2. Operational Day-Ahead Benchmark Comparison (2024 H2, $h=24$, $N=4,376$)

| Forecasting System | Operational Lead Time | MAE (MW) | RMSE (MW) | MAPE (%) | Mean Bias (MW) | Pearson $r$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTSO-E Day-ahead Forecast [6.1.B]** | **14–38 hours** (D-1 10:00 CET) | **230.79** | **299.73** | **2.55%** | **+41.43** | **0.9874** |
| **GBDT ($h=24$)** | 24 hours | 334.92 | 469.22 | 3.64% | -36.53 | — |
| **Daily Seasonal-Naive ($h=24$)** | 24 hours | 488.25 | 687.88 | 5.39% | +18.68 | — |

*(Note: The ENTSO-E forecast is an external operational benchmark issued under a documented D-1 10:00 CET information boundary, corresponding to 14–38 hours of lead time, rather than a simple hourly autoregressive baseline).*

### 5.3. H1 Validation vs. H2 Test Comparison

| Horizon | H1 Val $N$ | H1 Val GBDT MAE | H2 Test $N$ | H2 Test GBDT MAE | Absolute Change | H1 % Impr vs Baseline | H2 % Impr vs Baseline |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1h** | 4,356 | 116.80 MW | 4,408 | 101.27 MW | -15.53 MW | +50.69% | +56.34% |
| **6h** | 4,351 | 367.32 MW | 4,403 | 275.56 MW | -91.76 MW | +39.65% | +43.55% |
| **24h** | 4,333 | 499.08 MW | 4,385 | 334.92 MW | -164.16 MW | +18.18% | +31.40% |
| **168h** | 4,190 | 733.48 MW | 4,241 | 559.74 MW | -173.74 MW | +17.78% | +7.40% |

### 5.4. Core Empirical Findings
1. **Consistent Baseline Outperformance:** A historical-load-only GBDT consistently outperformed persistence and seasonal-naive baselines on both validation and unseen test data, with the strongest gains at short horizons ($-56.34\%$ MAE at $1\text{h}$, $-43.55\%$ at $6\text{h}$, $-31.40\%$ at $24\text{h}$) and substantially smaller gains at one-week lead time ($-7.40\%$ at $168\text{h}$).
2. **Lead-Time Horizon Dynamics:** The smaller improvement at 168h is consistent with the model relying strictly on historical load and calendar information during sustained seasonal changes; without exogenous information such as future weather, the model may lag persistent changes that are not represented in historical load patterns.
3. **Operational Relevance:** The ENTSO-E Day-ahead Forecast [6.1.B] achieves MAE 230.79 MW (2.55% MAPE, $r=0.9874$) at 14–38h lead time, providing an external operational reference point that illustrates what is achievable under a day-ahead information regime.

---

## 6. Repository Structure

```
p4-grid-load-forecasting/
├── config/
│   ├── __init__.py
│   └── settings.py               # Paths, parameters, EIC codes, frozen settings
├── data/
│   ├── raw/                      # Pristine raw XML responses from ENTSO-E API
│   ├── processed/                # Canonical hourly series (UTC parquet & CSV)
│   └── metadata/                 # Query manifests, timestamps, file sizes
├── docs/
│   ├── gate0_spec.md             # Gate 0 mathematical and regulatory criteria
│   └── entsoe_access_guide.md    # API registration and access guide
├── reports/
│   ├── figures/                  # Gate 0 diagnostic plots (ACF, differences)
│   ├── gate0_audit_report.md     # Gate 0 provenance & temporal audit report
│   ├── baseline_evaluation_report.md  # Phase 1 baseline evaluation report
│   ├── gbdt_validation_report.md      # Phase 2 validation & diagnostics report
│   └── gbdt_test_evaluation_report.md # Phase 2 blind test evaluation report
├── src/
│   ├── audit/                    # Gate 0 audit engine (provenance, DST, continuity)
│   ├── baselines/                # Non-learned baselines (Persistence, S-Naive)
│   ├── data/                     # Ingestion, client, XML parser
│   ├── features/                 # Frozen 21-feature pipeline & Swedish calendar
│   └── models/                   # Frozen GBDT engine & evaluation runners
├── tests/                        # 63 unit, regression, and fault-injection tests
├── LICENSE                       # MIT License
├── requirements.txt              # Environment dependencies
├── walkthrough.md                # Comprehensive end-to-end walkthrough
└── README.md
```

---

## 7. Getting Started & Reproducibility

### Prerequisites
* Python 3.10+
* ENTSO-E API Security Token (only required if re-downloading raw telemetry via API; processed Parquet datasets are included in the repository for out-of-the-box reproducibility)

### Installation
```bash
pip install -r requirements.txt
```

### Run Test Suite
```bash
pytest tests/ -v
```
All 63 automated tests verify feature causality, missing-target accounting, DST transitions, linear interpolation detection, and baseline shifts.

### Inspect Reports
* Gate 0 Audit: [`reports/gate0_audit_report.md`](reports/gate0_audit_report.md)
* Baseline Evaluation: [`reports/baseline_evaluation_report.md`](reports/baseline_evaluation_report.md)
* GBDT Validation Diagnostics: [`reports/gbdt_validation_report.md`](reports/gbdt_validation_report.md)
* Final Blind Test Evaluation: [`reports/gbdt_test_evaluation_report.md`](reports/gbdt_test_evaluation_report.md)

---

## 8. Methodological Readiness & Integrity Statement

* **Mathematical & Temporal Rigor:** **STRONG** — Gate 0 verified temporal continuity, resolved the 2025 resolution transition, proved 172 distinct affected rows with zero pairwise collisions across 903 pairs, and eliminated future lookahead.
* **Engineering & Code Quality:** **RESEARCH-GRADE / REPRODUCIBLE** — Fully modular pipeline with 63 automated unit and regression tests passing.
* **Credential Hygiene:** **THOROUGH** — Zero credentials logged, committed, or manifested.
* **Empirical Integrity:** **METHODOLOGICALLY SOUND** — Pre-commitment pre-recorded; single blind test run; frozen results reported without cherry-picking or post-hoc adjustments.

---

## 9. License & Data Terms

* **Code & Documentation:** The original source code, documentation, and analysis scripts in this repository are licensed under the [MIT License](LICENSE).
* **Third-Party / ENTSO-E Data:** Electricity load and forecast data included or retrieved by this project originate from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) under Regulation (EU) No 543/2013 and remain subject to ENTSO-E's terms of use and data policies. The MIT license applies strictly to the project's original software and documentation, not to third-party data.
