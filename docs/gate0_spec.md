# Gate 0 Specification: Dataset Provenance & Temporal Validity Audit

This document defines the mathematical, logical, and regulatory criteria for **Gate 0** of Project P4.

---

## 1. Overview and Decision Framework

The dataset must undergo an exhaustive audit across five dimensions before any forecasting model is developed or trained.

The master audit outputs exactly one decision:
* **PASS:** All five sub-audits pass all critical tests. Dataset is suitable for model development.
* **FAIL:** At least one hard gate fails (e.g., unexplained gaps, systematic artificial interpolation, unresolvable DST corruption, missing target series). The dataset is rejected.
* **AMBIGUOUS — DO NOT MODEL YET:** Data contains anomalies that require clarification from TSO documentation, API provider inquiries, or manual verification before proceeding.

---

## 2. Gate 0.1 — Provenance Audit

### Purpose
Establish the legal, physical, and technical origin of the series to ensure strict reproducibility.

### Specifications
* **Platform:** ENTSO-E Transparency Platform (Regulation EU No 543/2013).
* **Bidding Zone:** Sweden SE3 (`10Y1001A1001A46L`).
* **Target Data Item:** Actual Total Load [6.1.A] (`documentType=A65`, `processType=A16`).
* **External Benchmark Item:** Day-ahead Total Load Forecast [6.1.B] (`documentType=A65`, `processType=A01`).
* **Units:** Megawatts (MW).
* **Temporal Resolution:** Hourly (`PT60M`).
* **Revision Status:**
  - Initial publication occurs within $H+1$ hour post-delivery based on SCADA telemetry.
  - Final settlement reconciliation occurs weeks to months later.
  - Historical periods (2022–2025) are expected to be finalized, but retrieval timestamp, API version, and raw file checksums must be persistently logged.

---

## 3. Gate 0.2 — Timezone & Daylight Saving Time (DST) Integrity (HARD GATE)

### Purpose
Verify that temporal indexing is mathematically continuous, tz-aware, and unambiguous across seasonal clock adjustments.

### Timeline Standard
* **Canonical Storage:** Coordinated Universal Time (UTC, tz-aware).
* **Local Reference:** `Europe/Stockholm` (CET: UTC+1 in winter, CEST: UTC+2 in summer).

### Audit of All 8 DST Transitions (2022–2025)
For each of the following 8 transition dates:
1. **2022 Spring-Forward:** 2022-03-27 (clock jumps 02:00 -> 03:00 local)
2. **2022 Autumn-Fallback:** 2022-10-30 (clock jumps 03:00 -> 02:00 local)
3. **2023 Spring-Forward:** 2023-03-26 (clock jumps 02:00 -> 03:00 local)
4. **2023 Autumn-Fallback:** 2023-10-29 (clock jumps 03:00 -> 02:00 local)
5. **2024 Spring-Forward:** 2024-03-31 (clock jumps 02:00 -> 03:00 local)
6. **2024 Autumn-Fallback:** 2024-10-27 (clock jumps 03:00 -> 02:00 local)
7. **2025 Spring-Forward:** 2025-03-30 (clock jumps 02:00 -> 03:00 local)
8. **2025 Autumn-Fallback:** 2025-10-26 (clock jumps 03:00 -> 02:00 local)

### Validation Checks
* **Expected Physical Hours:** In canonical UTC, every transition day has exactly 24 physical hours.
* **Local Display Representation:** In `Europe/Stockholm`, spring days must contain 23 wall-clock hours; autumn days must contain 25 wall-clock hours.
* **Duplicates & Gaps:** Zero duplicate timestamps in UTC; zero missing UTC hours.
* **Index Suitability:** Lag features (e.g. $y_{t-24}$, $y_{t-168}$) must be explicitly defined in physical time elapsed (24 physical hours, 168 physical hours).

---

## 4. Gate 0.3 — Timestamp Continuity Audit

### Purpose
Ensure no unhandled missing values, inverted timestamps, or irregular intervals exist across the entire 4-year evaluation window.

### Validation Parameters
* **Total Expected Physical Hours:**
  $$\text{Total Hours} = (365 \times 3 + 366) \times 24 = (1095 + 366) \times 24 = 1461 \times 24 = 35,064\text{ hours}$$
  - 2022: 8,760 hours
  - 2023: 8,760 hours
  - 2024 (Leap Year): 8,784 hours
  - 2025: 8,760 hours
* **Continuity Assertions:**
  - $\Delta t_i = t_i - t_{i-1} = 1\text{ hour}$ for all $i \in \{1, \dots, N-1\}$.
  - Strictly monotonic: $t_i > t_{i-1}$.
  - Zero duplicate timestamps.
  - Zero unrecorded gaps. Missing values must be detected, quantified, and explained before any filling strategy is contemplated.

---

## 5. Gate 0.4 — Artificial-Data & Interpolation Audit

### Purpose
Directly detect synthetic smoothing, forward filling, or deterministic linear interpolation (the failure mode that disqualified the previous industrial dataset).

### Mathematical Metrics

#### 1. Flatline & Repeated Value Rate
Let $y_t$ denote the load at hour $t$.
* **Consecutive Zero-Change Rate:**
  $$\rho_0 = \frac{1}{N-1} \sum_{t=1}^{N-1} \mathbb{I}(y_t = y_{t-1})$$
* **Max Flatline Duration:**
  $$L_{\max} = \max \{ k : y_t = y_{t+1} = \dots = y_{t+k-1} \}$$
  *Threshold:* For large-scale bidding zone total load, continuous flatlines exceeding 3 consecutive identical hours are flagged for manual verification; flatlines $> 6$ hours fail the audit unless substantiated by grid outage events.

#### 2. First Differences
$$\Delta y_t = y_t - y_{t-1}$$
* Proportion of zero first differences: $\mathbb{P}(\Delta y_t = 0)$.
* Outlier detection: $|\Delta y_t| > 3 \times \text{IQR}(\Delta y)$.

#### 3. Second Differences & Linear Interpolation Signature
Linear interpolation generates continuous segments where the rate of change is constant:
$$\Delta^2 y_t = \Delta y_t - \Delta y_{t-1} = y_t - 2y_{t-1} + y_{t-2}$$
* In natural grid demand, $\Delta^2 y_t = 0$ occurs only transiently at inflection points.
* If a sequence of length $k \ge 3$ satisfies:
  $$\Delta^2 y_t = 0 \quad \text{and} \quad \Delta y_t \ne 0$$
  this constitutes a mathematical signature of deterministic linear interpolation between missing telemetry points.

#### 4. Autocorrelation Structure
Sample autocorrelation function:
$$\hat{\rho}(k) = \frac{\sum_{t=1}^{N-k} (y_t - \bar{y})(y_{t+k} - \bar{y})}{\sum_{t=1}^N (y_t - \bar{y})^2}$$
* Evaluated at lag 1 (smoothness), lag 24 (daily cycle), lag 168 (weekly cycle).
* Must exhibit physical load dynamics (diurnal peak/trough, weekend drop) without artificial periodicity or clipping.

---

## 6. Gate 0.5 — Actual vs Forecast Semantics Audit

### Purpose
Establish the temporal information boundary to eliminate data leakage when benchmarking against the ENTSO-E Day-ahead Total Load Forecast [6.1.B].

### Regulatory Boundaries (Regulation EU No 543/2013)
* **Market Gate Closure:** Nord Pool day-ahead spot market gates close at **12:00 CET / CEST on day $D-1$**.
* **Publication Deadline:** Article 6.1.b mandates publication no later than 2 hours before gate closure (**10:00 CET/CEST on $D-1$**), or 12:00 CET/CEST if no separate gate closure.
* **Forecast Range:** Delivered for the 24 hours of delivery day $D$ (from 00:00 to 24:00 CET).
* **Anti-Leakage Principle:**
  When comparing an internal model to [6.1.B], the internal model's feature set must contain **no information observed after 10:00 CET on $D-1$**. Intraday actuals from $D-1$ afternoon/evening cannot be used in a fair day-ahead benchmark comparison.
