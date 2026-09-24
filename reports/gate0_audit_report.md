# Gate 0 Audit Report: ENTSO-E Dataset Provenance and Temporal Validity

![Gate 0 Decision](https://img.shields.io/badge/Gate%200%20Decision-PASS%20—%20HOURLY%20SE3%20ACTUAL%20TOTAL%20LOAD,%202022–2024-brightgreen?style=for-the-badge)

* **Date:** 2026-09-24
* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Geographic Scope:** Sweden Bidding Zone SE3 (`10Y1001A1001A46L`)
* **Core Temporal Scope (Option B):** 2022-01-01 00:00 UTC through 2024-12-31 23:00 UTC (3 complete calendar years, hourly `PT60M`)
* **Extension Scope:** 2025-01-01 00:00 UTC through 2025-12-31 23:00 UTC (documented separately due to Nordic 15-minute MTU transition)
* **Primary Target Series:** Actual Total Load [6.1.A] (`docType=A65`, `processType=A16`)
* **External Benchmark Series:** Day-ahead Total Load Forecast [6.1.B] (`docType=A65`, `processType=A01`)

---

## 1. Executive Summary & Review Scope Decision

Following external review and dataset audit, **Option B** is formally selected:
* The **core forecasting study** is strictly bounded to the 3-year homogeneous hourly period: **2022-01-01 00:00 UTC to 2024-12-31 23:00 UTC** ($N = 26,304$ physical hours).
* The **2025 dataset** is documented as a future extension, quarantined from the core study due to the structural transition from hourly (`PT60M`) to 15-minute (`PT15M`) Market Time Unit (MTU) on 2025-12-01 23:00 UTC.

### Sub-Audit Evaluation Summary (Core 2022–2024 Study)

| Sub-Audit Gate | Status | Key Evaluation Metric |
| :--- | :---: | :--- |
| **Gate 0.1 — Provenance** | **PASS** | Authoritative ENTSO-E specification, EU Reg 543/2013, MW units, verified EIC `10Y1001A1001A46L` |
| **Gate 0.2 — Timezone & DST** | **PASS** | 6/6 DST transitions intact (2022–2024); canonical UTC 24h physical days; Europe/Stockholm wall-clock shifts verified |
| **Gate 0.3 — Continuity** | **PASS** | 26,261 / 26,304 hours (99.84% complete); 43 isolated 1h gaps (0 adjacent); exactly 172 distinct affected rows |
| **Gate 0.4 — Artificial-Data** | **PASS** | No evidence of tested artificial-data signatures detected; 0 flatlines > 1h; 0 multi-step linear interpolations |
| **Gate 0.5 — Forecast Semantics** | **PASS** | D-1 10:00 CET information cutoff established; empirical baseline comparison: MAE 239.05 MW (2.56% MAPE) |

### Formal Master Status
> **PASS — HOURLY SE3 ACTUAL TOTAL LOAD, 2022–2024**
>
> **Mandatory Core Protocol Constraints:**
> * **Core Study Period:** 2022–2024 is the sole core study period ($N = 26,304$ physical hours).
> * **Extension Boundary:** December 2025 / the 15-minute resolution period is excluded from the core study and retained as a future extension.
> * **Target Preservation:** Missing actual targets remain un-imputed; no synthetic target values are ever generated.
> * **Causal Feature Handling:** Causal forward-fill is permitted **only for lag-feature construction** ($x_t^{\text{lag}}$).
> * **Evaluation Population:** Rows with missing actual targets are strictly excluded from training and evaluation.
> * **Zero Future Leakage:** No future information may be used in feature construction at any stage.


---

## 2. Gate 0.1 — Provenance & Regulatory Findings

* **Data Platform:** ENTSO-E Transparency Platform (`https://web-api.tp.entsoe.eu/api`)
* **Legal Governance:** Regulation (EU) No 543/2013, Articles 6.1.a & 6.1.b
* **Bidding Zone:** Sweden SE3 (EIC: `10Y1001A1001A46L`)
* **Target Item [6.1.A]:** Actual Total Load (`documentType=A65`, `processType=A16`)
* **Benchmark Item [6.1.B]:** Day-ahead Total Load Forecast (`documentType=A65`, `processType=A01`)
* **Resolution & Units:** Hourly (`PT60M`) | Megawatts (MW)
* **Revision & Finalization Policy:**
  Under Regulation (EU) No 543/2013, Svenska kraftnät (the Swedish TSO) publishes initial Actual Total Load within $H+1$ hour post-operating period based on SCADA telemetry. Final settlement reconciliation occurs 60–90 days post-delivery.
* **Historical Stability Assessment:**
  All historical data for 2022–2024 retrieved in 2026 is fully matured beyond the settlement window and represents finalized operational accounting.
* **Re-pull Requirements:**
  Zero re-pulls required for the 2022–2024 analysis window. SHA-256 checksums and raw XML responses are permanently archived in `data/raw/`.

---

## 3. Gate 0.2 — Timezone & Daylight Saving Time (DST) Integrity (HARD GATE)

* **Canonical Storage Timeline:** UTC (tz-aware `datetime64[ns, UTC]`)
* **Local Reference Timezone:** `Europe/Stockholm` (CET: UTC+1 in winter, CEST: UTC+2 in summer)
* **Suitability for Forecasting Indexing:** Fully suitable. The canonical UTC timeline maintains constant physical duration. Lag features ($y_{t-24}$, $y_{t-168}$) strictly represent 24 and 168 elapsed physical hours without clock distortions.

### Audit of DST Transitions (2022–2024 Core Scope)

| Transition Date | Type | Expected UTC Hours | Actual UTC Hours | Expected Local Hours | Actual Local Hours | Duplicate UTC | Missing UTC | Result |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `2022-03-27` | spring_forward (02:00 -> 03:00) | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2022-10-30` | autumn_fallback (03:00 -> 02:00) | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |
| `2023-03-26` | spring_forward (02:00 -> 03:00) | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2023-10-29` | autumn_fallback (03:00 -> 02:00) | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |
| `2024-03-31` | spring_forward (02:00 -> 03:00) | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2024-10-27` | autumn_fallback (03:00 -> 02:00) | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |

*(Note: 2025 transitions on `2025-03-30` and `2025-10-26` were also tested and physically verified intact in UTC).*

---

## 4. Gate 0.3 — Timestamp Continuity & Gap Forensic Analysis

### 4.1. Core Study Continuity (2022–2024)

* **Total Expected Physical Hours:** 26,304 hours ($8,760 + 8,760 + 8,784$)
* **Total Actual Observations:** 26,261 hours (99.837% completeness)
* **Total Missing Hours:** 43 hours (0.163% missingness)
* **Total Duplicate Timestamps:** 0 (zero duplicates)
* **Monotonicity:** Strictly monotonic increasing index
* **Annual Breakdown:**
  * **2022:** 8,747 observed / 8,760 expected (13 missing hours)
  * **2023:** 8,748 observed / 8,760 expected (12 missing hours)
  * **2024 (Leap Year):** 8,766 observed / 8,784 expected (18 missing hours)

### 4.2. Forensic Extraction of the 43 Missing Timestamps & Adjacency Check

Every single missing timestamp in the 2022–2024 dataset was extracted and audited against the Day-ahead Forecast series [6.1.B]:

| # | Missing Timestamp (UTC) | Year | Minimum Gap to Prev/Next Gap | Forecast Available [6.1.B]? | Forecast Value (MW) |
| :-: | :--- | :-: | :---: | :---: | :-: |
| 1 | `2022-02-07 01:00:00+00:00` | 2022 | > 30 days | **Yes** | 10,570.0 |
| 2 | `2022-03-21 00:00:00+00:00` | 2022 | > 40 days | **Yes** | 9,884.0 |
| 3 | `2022-03-28 23:00:00+00:00` | 2022 | 7 days 23h | **Yes** | 9,511.0 |
| 4 | `2022-04-07 00:00:00+00:00` | 2022 | 9 days 01h | **Yes** | 9,894.0 |
| 5 | `2022-04-15 19:00:00+00:00` | 2022 | 8 days 19h | **Yes** | 9,801.0 |
| 6 | `2022-05-09 18:00:00+00:00` | 2022 | 23 days 23h | **Yes** | 9,243.0 |
| 7 | `2022-05-10 01:00:00+00:00` | 2022 | **7 hours** (min gap) | **Yes** | 7,909.0 |
| 8 | `2022-06-15 11:00:00+00:00` | 2022 | 36 days 10h | **Yes** | 9,448.0 |
| 9 | `2022-07-02 18:00:00+00:00` | 2022 | 17 days 07h | **Yes** | 7,587.0 |
| 10 | `2022-09-14 08:00:00+00:00` | 2022 | > 70 days | **Yes** | 9,222.0 |
| 11 | `2022-10-24 14:00:00+00:00` | 2022 | > 40 days | **Yes** | 9,897.0 |
| 12 | `2022-11-13 12:00:00+00:00` | 2022 | 19 days 22h | **Yes** | 9,150.0 |
| 13 | `2022-12-14 12:00:00+00:00` | 2022 | 31 days 00h | **Yes** | 14,022.0 |
| 14 | `2023-01-14 23:00:00+00:00` | 2023 | 31 days 11h | **Yes** | 9,279.0 |
| 15 | `2023-02-16 09:00:00+00:00` | 2023 | 32 days 10h | **Yes** | 11,984.0 |
| 16 | `2023-03-27 01:00:00+00:00` | 2023 | 38 days 16h | **Yes** | 10,490.0 |
| 17 | `2023-04-24 18:00:00+00:00` | 2023 | 28 days 17h | **Yes** | 9,682.0 |
| 18 | `2023-07-17 03:00:00+00:00` | 2023 | > 80 days | **Yes** | 5,813.0 |
| 19 | `2023-08-23 07:00:00+00:00` | 2023 | 37 days 04h | **Yes** | 9,088.0 |
| 20 | `2023-08-25 01:00:00+00:00` | 2023 | 1 day 18h | **Yes** | 6,726.0 |
| 21 | `2023-09-17 10:00:00+00:00` | 2023 | 23 days 09h | **Yes** | 7,807.0 |
| 22 | `2023-09-23 02:00:00+00:00` | 2023 | 5 days 16h | **Yes** | 6,384.0 |
| 23 | `2023-11-16 03:00:00+00:00` | 2023 | > 50 days | **Yes** | 10,067.0 |
| 24 | `2023-11-17 09:00:00+00:00` | 2023 | 1 day 06h | **Yes** | 12,644.0 |
| 25 | `2023-12-19 10:00:00+00:00` | 2023 | 32 days 01h | **Yes** | 12,110.0 |
| 26 | `2024-01-07 03:00:00+00:00` | 2024 | 18 days 17h | **Yes** | 12,658.0 |
| 27 | `2024-02-02 11:00:00+00:00` | 2024 | 26 days 08h | **Yes** | 12,863.0 |
| 28 | `2024-03-02 15:00:00+00:00` | 2024 | 29 days 04h | **Yes** | 10,962.0 |
| 29 | `2024-03-08 13:00:00+00:00` | 2024 | 5 days 22h | **Yes** | 11,142.0 |
| 30 | `2024-04-26 16:00:00+00:00` | 2024 | > 45 days | **Yes** | 10,184.0 |
| 31 | `2024-04-27 00:00:00+00:00` | 2024 | 8 hours | **Yes** | 8,757.0 |
| 32 | `2024-05-16 02:00:00+00:00` | 2024 | 19 days 02h | **Yes** | 7,036.0 |
| 33 | `2024-05-19 03:00:00+00:00` | 2024 | 3 days 01h | **Yes** | 6,463.0 |
| 34 | `2024-05-29 08:00:00+00:00` | 2024 | 10 days 05h | **Yes** | 8,912.0 |
| 35 | `2024-06-01 16:00:00+00:00` | 2024 | 3 days 08h | **Yes** | 7,435.0 |
| 36 | `2024-06-11 16:00:00+00:00` | 2024 | 10 days 00h | **Yes** | 8,755.0 |
| 37 | `2024-07-14 16:00:00+00:00` | 2024 | > 30 days | **Yes** | 7,318.0 |
| 38 | `2024-07-18 17:00:00+00:00` | 2024 | 4 days 01h | **Yes** | 7,574.0 |
| 39 | `2024-07-24 10:00:00+00:00` | 2024 | 5 days 17h | **Yes** | 7,608.0 |
| 40 | `2024-09-23 16:00:00+00:00` | 2024 | > 60 days | **Yes** | 9,082.0 |
| 41 | `2024-10-10 10:00:00+00:00` | 2024 | 16 days 18h | **Yes** | 9,581.0 |
| 42 | `2024-11-06 08:00:00+00:00` | 2024 | 26 days 22h | **Yes** | 10,392.0 |
| 43 | `2024-12-16 00:00:00+00:00` | 2024 | 39 days 16h | **Yes** | 9,510.0 |

**Critical Findings from the Adjacency Audit:**
1. **Zero Adjacency:** There are strictly **0 adjacent missing hours**. Every single missing gap is an isolated, 1-hour telemetry loss.
2. **Minimum Separation:** The minimum temporal distance between any two missing hours is **7 hours** (between `2022-05-09 18:00Z` and `2022-05-10 01:00Z`).
3. **100% Benchmark Availability:** Exactly **43 of 43 (100.0%)** of the missing actual hours have valid, published Day-ahead Forecast values in [6.1.B].

---

### 4.3. Feature Lag Availability & Leakage-Safe Handling Policy

To determine whether imputation is necessary or desirable, we quantified the exact downstream impact of the 43 missing hours on lag feature creation ($y_{t-1}, y_{t-24}, y_{t-168}$) across the 26,136 post-warmup hours (excluding initial 168h warmup):

| Strategy | Methodology | Target $y_t$ Treatment | Features Retained | Dropped Rows | Leakage Risk | Operational Defensibility |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **Case 1: Complete-Case (No Imputation)** | Invalidate any row where target $y_t$ or any lag feature is NaN | Left raw (NaN) | 25,964 / 26,136 (99.34%) | **172 rows (0.66%)** | **Zero leakage** | High: Only real observed grid values are used for features and targets. 172 rows lost ($43 \times 4$). |
| **Case 2: Causal Feature FFill (Recommended)** | For feature construction only, forward-fill missing hour from $y_{t-1}$. Never impute target $y_t$. | Left raw (NaN) | 26,093 / 26,136 (99.84%) | **43 rows (0.16%)** | **Zero leakage** | Highest: $y_{t-1}$ is strictly historical (known at $t$). Model is never trained or evaluated on synthetic targets. |
| **Case 3: Linear Interpolation (REJECTED)** | Interpolate $y_t = (y_{t-1} + y_{t+1}) / 2$ | Imputed | 26,136 / 26,136 (100.0%) | 0 rows (0.00%) | **FATAL LEAKAGE** | Unacceptable: Uses future observation $y_{t+1}$ to construct feature at $t+1$, causing direct lookahead contamination. |

**Recommended Leakage-Safe Policy:**
We adopt **Case 2** (or Case 1). Causal forward-filling is applied exclusively to the feature calculation pipeline ($x_t^{\text{lag}}$) using strictly antecedent values ($y_{t-1}$), while the target column $y_t$ is preserved in its authentic, un-imputed state. Consequently, the model is strictly trained and evaluated against real empirical ground truth.

---

### 4.4. Authoritative 2025 Raw XML Reconciliation

To resolve the earlier arithmetic discrepancy ("8,760 expected / 13 missing / 8,029 PT60M"), a forensic audit was executed directly on the raw XML files (`actual_load_6_1_a_SE3_2025_*.xml` and `day_ahead_forecast_6_1_b_SE3_2025_*.xml`):

```
=== actual_load_6_1_a_SE3_2025_20260924T122850Z.xml ===
TimeSeries 0 (mRID=1):
  Period 0: 2025-01-01T00:00Z to 2025-12-01T23:00Z (resolution: PT60M)
            Expected points: 8,039 | Observed points: 8,029 | Missing: 10
  Period 1: 2025-12-01T23:00Z to 2026-01-01T00:00Z (resolution: PT15M)
            Expected points: 2,884 | Observed points: 2,864 | Missing: 20 (5h equivalent)
Total points in 2025 XML: 8,029 + 2,864 = 10,893 points.
```

**Resolution of Arithmetic Discrepancy:**
1. The calendar year 2025 contains exactly 8,760 physical hours ($8,039\text{ PT60M hours} + 721\text{ PT15M hours} = 8,760$).
2. The exact resolution transition timestamp is **`2025-12-01T23:00Z`** (midnight `2025-12-02 00:00:00` CET), representing the official go-live of the Nordic 15-minute MTU market regime.
3. The previous report of "13 missing" resulted from naively filtering 2025 by minute `:00`: across December's 721 hours, 718 had a `:00` reading (3 missing `:00` timestamps). Combining the 10 missing hours in Period 0 with 3 missing `:00` timestamps in December yielded $10 + 3 = 13$ missing top-of-hour readings.
4. In physical time, Period 0 has 10 missing hours and Period 1 has 20 missing quarter-hours (5 hours equivalent), totaling **15 physical hours of missing telemetry** in 2025.

---

## 5. Gate 0.4 — Artificial-Data, Flatline, and Interpolation Audit

### 5.1. Audit Findings Statement
> **Finding:** No evidence of the tested artificial-data signatures was detected under the implemented diagnostics and thresholds.

### 5.2. Quantitative Metrics (2022–2024 Core Dataset)

* **Total Observations Audited:** 26,261 hours
* **Consecutive Duplicate Count:** 0 out of 26,260 adjacent pairs (**0.0000%**)
* **Maximum Flatline Duration:** **1 consecutive hour** (threshold: $> 3$h warning, $> 6$h fail)
* **First Differences ($\Delta y_t = y_t - y_{t-1}$):**
  * Mean: $+0.03$ MW
  * Std: $303.05$ MW
  * Interquartile Range (IQR): $299.00$ MW (Q25: $-150.0$ MW, Q75: $+149.0$ MW)
  * Zero-Change Rate ($\mathbb{P}(\Delta y = 0)$): **0.0000%** (zero occurrences out of 26,260 steps)
* **Second Differences ($\Delta^2 y_t$) & Linear Interpolation Audit ($k \ge 3$ Specification):**
  * Spans of length $\ge 5$ points ($k \ge 3$ consecutive second-difference zeros): **0 spans**
  * Multi-step linear interpolation sequences (duration $\ge 4$ hours, $k \ge 2$ in $\Delta^2 y$): **0 spans**
  * Isolated 3-point sequences ($k = 1$ in $\Delta^2 y_t = 0$, 2 consecutive steps of identical integer change): 53 occurrences across 26,260 steps (**0.20%**), fully consistent with random integer quantization in 15,000 MW telemetry.
  * Maximum linear interpolation duration: **0 hours** of artificial smoothing.
* **Autocorrelation Structure:**
  * $\hat{\rho}(1)$ (1 hour): **0.9888** (smooth physical continuity)
  * $\hat{\rho}(24)$ (1 day): **0.9236** (strong diurnal periodicity)
  * $\hat{\rho}(48)$ (2 days): **0.8572** (recurrent daily cycle)
  * $\hat{\rho}(168)$ (1 week): **0.8697** (prominent weekly workweek/weekend rhythm)

### 5.3. Difference Histogram Diurnal Ramp Diagnostic

Inspection of the first difference distribution in `reports/figures/real_se3_gate0_differences.png` revealed an asymmetric positive tail ($> 500$ MW). An hourly diurnal breakdown in local `Europe/Stockholm` time confirmed this is the direct mathematical manifestation of the sharp morning industrial and commercial load ramp:

| Local Hour (Stockholm) | Mean $\Delta y$ (MW) | Std $\Delta y$ (MW) | Min $\Delta y$ (MW) | Max $\Delta y$ (MW) | Large Ramps ($> 500$ MW) | Steep Drops ($< -500$ MW) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **05:00** | $+233.84$ | $190.56$ | $-353.0$ | $+779.0$ | 75 | 0 |
| **06:00** | **$+649.49$** | $384.68$ | $-151.0$ | $+1,531.0$ | **703** | 0 |
| **07:00** | **$+636.16$** | $305.88$ | $-91.0$ | $+2,391.0$ | **728** | 0 |
| **08:00** | $+244.68$ | $159.93$ | $-413.0$ | $+1,050.0$ | 43 | 0 |
| ... | ... | ... | ... | ... | ... | ... |
| **21:00** | $-320.66$ | $168.90$ | $-1,416.0$ | $+625.0$ | 1 | 140 |
| **22:00** | **$-377.27$** | $156.24$ | $-851.0$ | $+125.0$ | 0 | **252** |
| **23:00** | **$-390.79$** | $138.49$ | $-1,363.0$ | $+423.0$ | 0 | **217** |

**Diurnal Physics Confirmation:**
* **83.83%** of all large positive ramps ($\Delta y > 500$ MW, 1,431 out of 1,707 occurrences) occur strictly between **06:00 and 08:00 local time**.
* In contrast, load decline in the evening is spread across a wider 5-hour window (20:00 to 01:00 local time), where hours 21:00–23:00 account for **81.09%** of steep drops ($\Delta y < -500$ MW).
* This fully explains the histogram shape as authentic grid physics rather than telemetry distortion.

---

## 6. Gate 0.5 — Actual vs Forecast Semantics & Information Boundary

### 6.1. Documented Forecast Semantics
* **Data Item:** Day-ahead Total Load Forecast [6.1.B]
* **Legal Basis:** Regulation (EU) No 543/2013, Article 6.1.b
* **Parameters:** `documentType=A65`, `processType=A01`, `outBiddingZone_Domain=10Y1001A1001A46L`
* **Nature of Series:** Day-ahead forecast generated by Svenska kraftnät covering all 24 hours of delivery day $D$.

### 6.2. Documented Publication & Information Boundary
* **Nord Pool Day-Ahead Gate Closure:** **12:00 CET / CEST on day $D-1$**
* **Mandatory Forecast Publication Deadline:** **10:00 CET / CEST on day $D-1$** (mandated $\ge 2$ hours prior to gate closure under Art 6.1.b)
* **Operational Lead Time:** 14 hours ahead (for delivery hour 00:00-01:00 of day $D$) to 38 hours ahead (for delivery hour 23:00-24:00 of day $D$).

### 6.3. Strict Anti-Leakage Cutoff Rule
To ensure an operationally defensible and non-leaking comparison against the ENTSO-E Day-ahead Forecast benchmark:
$$\text{Feature Information Cutoff: } T_{\text{cutoff}} = \text{Day } D-1 \text{ at 10:00 CET}$$
* Any internal model benchmarked against [6.1.B] must construct feature vectors strictly from data available before 10:00 CET on $D-1$ (09:00 UTC winter / 08:00 UTC summer).
* Utilizing actual load telemetry observed on the afternoon or evening of day $D-1$ (e.g. 12:00–23:00) represents illegal future information leakage that was unavailable when the TSO benchmark was published.

### 6.4. Descriptive Operational Benchmark Comparison (2022–2024 Aligned Data)

Across the 26,194 mutually available hours in the core 2022–2024 study:

| Metric | Complete 2022–2024 | Year 2022 ($N=8,721$) | Year 2023 ($N=8,728$) | Year 2024 ($N=8,745$) |
| :--- | :---: | :---: | :---: | :---: |
| **Aligned Hours ($N$)** | **26,194** | 8,721 | 8,728 | 8,745 |
| **Mean Absolute Error (MAE)** | **239.05 MW** | 241.31 MW | 236.12 MW | 239.74 MW |
| **Root Mean Squared Error (RMSE)** | **310.20 MW** | 313.44 MW | 306.91 MW | 310.22 MW |
| **Mean Absolute Percentage Error (MAPE)** | **2.56%** | 2.59% | 2.54% | 2.54% |
| **Mean Bias Error (Actual - Forecast)** | **$-10.82$ MW** | $-13.91$ MW | $-11.41$ MW | $-7.14$ MW |
| **Pearson Correlation ($r$)** | **0.9889** | 0.9885 | 0.9889 | 0.9896 |

**Interpretation:**
The official TSO Day-ahead forecast demonstrates exceptional baseline performance ($r = 0.9889$, MAPE $\approx 2.55\%$), providing a highly challenging, realistic operational benchmark for Project P4.

---

## 7. Master Decision & Action Plan

### Master Verdict: **PASS — HOURLY SE3 ACTUAL TOTAL LOAD, 2022–2024**

**Formal Gate 0 Approval & Protocol Requirements:**
1. **Core Study Period:** 2022-01-01 00:00 UTC through 2024-12-31 23:00 UTC is the sole core study period ($N = 26,304$ physical hours).
2. **Resolution Exclusion:** December 2025 and the 15-minute MTU resolution period are formally excluded from the core study and retained as a future extension.
3. **Target Integrity:** Missing actual targets remain un-imputed; no synthetic target values may be generated or evaluated.
4. **Causal Feature Handling:** Causal forward-fill is permitted **only for lag-feature construction** ($x_t^{\text{lag}}$).
5. **Evaluation Rule:** Rows with missing actual targets are strictly excluded from model training and evaluation.
6. **Anti-Leakage Principle:** No future information may be used in feature construction; all historical lag definitions must be strictly antecedent to the forecast origin.
7. **Empirical Sanity Check Confirmed:** Exactly 172 distinct post-warmup timestamps are affected under complete-case lag invalidation across the 43 isolated missing hours.

