# Gate 0 Audit Report: ENTSO-E Dataset Provenance and Temporal Validity

![Gate 0 Decision](https://img.shields.io/badge/Gate%200%20Decision-AMBIGUOUS%20—%20DO%20NOT%20MODEL%20YET-orange?style=for-the-badge)

* **Date:** 2026-09-23
* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Geographic Scope:** Sweden Bidding Zone SE3 (`10Y1001A1001A46L`)
* **Temporal Scope:** 2022-01-01 00:00 UTC through 2025-12-31 23:00 UTC (4 complete calendar years)
* **Resolution:** Hourly (`PT60M`)
* **Primary Target:** Actual Total Load [6.1.A] (`docType=A65`, `processType=A16`)
* **External Benchmark:** Day-ahead Total Load Forecast [6.1.B] (`docType=A65`, `processType=A01`)

---

## 1. Executive Summary

| Sub-Audit Gate | Status | Key Evaluation Metric |
| :--- | :---: | :--- |
| **Gate 0.1 — Provenance** | **PASS** | Authoritative ENTSO-E specification, EU Reg 543/2013, MW units |
| **Gate 0.2 — Timezone & DST** | **PASS** | 8/8 DST transitions verified; canonical UTC vs Europe/Stockholm |
| **Gate 0.3 — Continuity** | **FAIL** | 37,154/35,064 physical hours, 56 missing |
| **Gate 0.4 — Artificial-Data** | **PASS** | Max flatline: 1h; Linear interp spans: 0 |
| **Gate 0.5 — Forecast Semantics** | **PASS** | Information cutoff: D-1 10:00 CET; anti-leakage verified |

### Overall Master Decision
> **AMBIGUOUS — DO NOT MODEL YET**

**Justification:**
Provenance, Timezone/DST (8/8 transitions), Artificial-Data (0 flatlines, 0 interpolation spans), and Forecast Semantics passed. However, Continuity audit failed strict 35,064 hourly expectation: found 56 missing hours (0.16% missingness across 2022-2024) and 37,154 rows due to a structural resolution shift to 15-minute MTU (PT15M) in December 2025. Modeling is strictly halted until resolution harmonization and missingness handling are approved.

---

## 2. Gate 0.1 — Provenance & Regulatory Findings

* **Data Platform:** ENTSO-E Transparency Platform
* **Legal Governance:** Regulation (EU) No 543/2013, Articles 6.1.a & 6.1.b
* **Bidding Zone:** Sweden SE3 (EIC: `10Y1001A1001A46L`)
* **Target Item:** Actual Total Load [6.1.A]
* **Resolution & Units:** PT60M | MW
* **Revision & Finalization Policy:**
  Under Regulation (EU) No 543/2013, Transmission System Operators (Svenska kraftnät for SE3) must publish initial Actual Total Load within H+1 hour post-operating period based on SCADA telemetry. Subsequent revisions occur as metered grid accounting data is reconciled during final market settlement.
* **Historical Stability Assessment:**
  For historical years 2022–2025 queried in 2026, the data has passed the standard market settlement window (typically finalized within 60–90 days). Values represent consolidated, final operational accounting.
* **Re-pull Requirements:**
  Zero re-pulls required for the 2022–2025 window once consolidated. For any newly elapsed month, an operational re-pull should occur 90 days post-delivery to capture settlement adjustments.

---

## 3. Gate 0.2 — Timezone & Daylight Saving Time (DST) Audit (HARD GATE)

* **Canonical Storage Timeline:** UTC (tz-aware UTC)
* **Local Reference Timezone:** Europe/Stockholm
* **Suitability for Forecasting Indexing:** SUITABLE: Canonical timeline is strictly continuous in UTC physical hours. Lag features (e.g. lag_24, lag_168) operate on uninterrupted physical intervals. Local calendar features (hour_of_day, day_of_week) can be derived via tz_convert('Europe/Stockholm') without disrupting the underlying time-delta continuity.

### Audit of All 8 Daylight Saving Time Transitions (2022–2025)

| Transition Date | Type | Expected UTC Hours | Actual UTC Hours | Expected Local Hours | Actual Local Hours | Duplicate UTC | Missing UTC | Result |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `2022-03-27` | spring_forward | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2022-10-30` | autumn_fallback | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |
| `2023-03-26` | spring_forward | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2023-10-29` | autumn_fallback | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |
| `2024-03-31` | spring_forward | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2024-10-27` | autumn_fallback | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |
| `2025-03-30` | spring_forward | 24 | 24 | 23 | 23 | 0 | 0 | **PASS** |
| `2025-10-26` | autumn_fallback | 24 | 24 | 25 | 25 | 0 | 0 | **PASS** |

---

## 4. Gate 0.3 — Timestamp Continuity & Monotonicity Audit

* **Total Expected Physical Hours:** 35,064 hours (including leap year 2024)
* **Total Actual Hours Inspected:** 37,154 hours
* **Strict Monotonic Increasing Index:** Yes
* **Total Missing Hours:** 56
* **Total Duplicate Timestamps:** 0
* **Abnormal UTC Day Count:** 84 days

### Annual Verification Summary

| Calendar Year | Expected Physical Hours | Actual Hours | Missing | Duplicates | Result |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **2022** | 8,760 | 8,747 | 13 | 0 | **FAIL** |
| **2023** | 8,760 | 8,748 | 12 | 0 | **FAIL** |
| **2024** | 8,784 | 8,766 | 18 | 0 | **FAIL** |
| **2025** | 8,760 | 10,893 | 13 | 0 | **FAIL** |

---

## 5. Gate 0.4 — Artificial-Data, Flatline, and Interpolation Audit

* **Consecutive Duplicate Count:** 0 (0.0000%)
* **Maximum Flatline Duration:** 1 consecutive hours
* **First Difference ($\Delta y_t$) Summary:**
  * Mean: 0.03 MW
  * Std: 303.05 MW
  * IQR: 299.00 MW
  * Zero-Change Rate ($\mathbb{P}(\Delta y = 0)$): 0.0000%
* **Second Difference ($\Delta^2 y_t$) Linear Interpolation Test:**
  * Detected deterministic linear interpolation spans: 0
  * Maximum linear interpolation duration: 0 hours
* **Autocorrelation Structure:**
  * Lag-1 (1 hour): 0.9888
  * Lag-24 (1 day): 0.9236
  * Lag-48 (2 days): 0.8572
  * Lag-168 (1 week): 0.8697

---

## 6. Gate 0.5 — Actual vs Forecast Semantics & Information Boundary

* **Governing Regulation:** Regulation (EU) No 543/2013, Article 6.1.b
* **Nord Pool Day-Ahead Gate Closure:** 12:00 CET / CEST on day D-1
* **Mandatory Forecast Publication Deadline:** 10:00 CET / CEST on day D-1 (two hours prior to gate closure)
* **Operational Lead Time:** 14 hours ahead (for delivery hour 00:00-01:00 D) to 38 hours ahead (for delivery hour 23:00-24:00 D)
* **Strict Anti-Leakage Boundary:**
  `D-1 10:00 CET (09:00 UTC winter / 08:00 UTC summer)`
* **Downstream Benchmark Rule:**
  STRICT ANTI-LEAKAGE REQUIREMENT: In any evaluation where our model is compared against the ENTSO-E Day-ahead Forecast [6.1.B], our model's feature set must contain ZERO information observed after D-1 10:00 CET. Using D-1 afternoon or evening actual load observations constitutes temporal data leakage and invalidates the benchmark comparison.

---

## 7. Final Master Decision

### Verdict: **AMBIGUOUS — DO NOT MODEL YET**

**Methodological Next Steps:**

1. Real ENTSO-E SE3 dataset has been successfully acquired, verified, and audited.
2. Provenance, Timezone/DST (8/8 transitions intact), Artificial-Data (0 flatlines, 0 interpolation spans), and Forecast Semantics all PASSED.
3. Continuity Ambiguity Identified:
   - 43 isolated single-hour missing gaps across 2022–2024 (0.16% missingness rate).
   - Structural transition to 15-minute resolution (PT15M, 2,864 rows) on 2025-12-01 23:00 UTC.
4. Methodological Rule Enforced: Modeling is strictly HALTED. Await user review and decision regarding (a) December 2025 hourly downsampling vs 2022–2024 study boundary, and (b) explicit imputation policy for isolated missing hours.
