# Project P4: Data-Driven Grid Load Forecasting for Operational Planning

[![Status: Gate 0 In-Progress](https://img.shields.io/badge/Status-Gate%200%20Audit%20In--Progress-yellow.svg)](#)
[![Data Source: ENTSO-E](https://img.shields.io/badge/Data%20Source-ENTSO--E%20Transparency%20Platform-blue.svg)](https://transparency.entsoe.eu/)
[![Geographic Scope: Sweden SE3](https://img.shields.io/badge/Bidding%20Zone-Sweden%20SE3-green.svg)](#)

## 1. Project Identity & Thesis Framing

* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Direction:** Operational-excellence / data-driven decision-support (aligned with industrial thesis frameworks such as the Alleima thesis).
* **Research Focus:** Real-world, operationally grounded electricity demand forecasting rather than a generic machine-learning demonstration.

### Thesis Context
Industrial and utility organizations generate vast streams of operational telemetry, yet connecting fine-grained data to actionable decision-making (dispatching, scheduling, capacity reservation, and reserve procurement) remains a systematic bottleneck. This project explores how empirical forecasting methodologies support operational planning under real physical and regulatory constraints.

### Core Research Question
> **How accurately can short-term electricity demand in the Swedish SE3 bidding zone be forecast from historical load patterns, and how does forecast performance change across prediction horizons and operating conditions?**

The goal is to understand **forecast usefulness** across operational horizons—not merely to chase arbitrary metric optimization. A null result showing that simple baselines or ENTSO-E's existing operational forecast outperform a machine learning model is completely valid and will be reported transparently.

---

## 2. Methodological Rule: The Gate 0 Temporal Audit

This project incorporates the critical lesson from earlier industrial time-series investigations: **Never trust the apparent temporal structure of a dataset simply because it is labeled as time series.**

Before any forecasting models (statistical, tree-based, or neural) are built or trained, the dataset must pass **Gate 0: Provenance and Temporal Validity Audit**:
1. **Gate 0.1 — Provenance:** Authoritative source, EIC code, units, resolution, revision dynamics, and historical finalization under EU Regulation 543/2013.
2. **Gate 0.2 — Timezone & DST Integrity (HARD GATE):** Analysis of UTC representations vs local CET/CEST and rigorous verification of all 8 Daylight Saving Time transitions across 2022–2025.
3. **Gate 0.3 — Timestamp Continuity:** Verification of the 35,064 physical hours across 2022–2025 (including leap year 2024), detecting gaps, duplicates, and abnormal counts.
4. **Gate 0.4 — Artificial-Data & Interpolation Audit:** Quantitative checks for repeated values, flatlines, first differences ($\Delta y$), second differences ($\Delta^2 y$) to detect deterministic linear interpolation, and autocorrelation structure.
5. **Gate 0.5 — Actual vs Forecast Semantics:** Information boundary analysis verifying the D-1 10:00/12:00 CET publication gate closure to prevent data leakage in external benchmark evaluations.

---

## 3. Dataset Specification

| Parameter | Specification | Official Reference / Code |
| :--- | :--- | :--- |
| **Authoritative Source** | ENTSO-E Transparency Platform | Regulation (EU) No 543/2013 |
| **Bidding Zone** | Sweden SE3 (Stockholm / Southern Central) | EIC: `10Y1001A1001A46L` (`SE_3`) |
| **Primary Target** | Actual Total Load [6.1.A] | `documentType=A65`, `processType=A16` |
| **External Benchmark** | Day-ahead Total Load Forecast [6.1.B] | `documentType=A65`, `processType=A01` |
| **Temporal Scope** | 2022-01-01 00:00 UTC to 2025-12-31 23:00 UTC | 4 Complete Calendar Years (35,064 hours) |
| **Temporal Resolution** | Hourly | `PT60M` |
| **Physical Units** | Megawatts | `MW` |

---

## 4. Planned Benchmarks & Horizons (Post Gate 0)

Once Gate 0 formally passes, evaluation will follow strict chronological splits:
* **Baseline 1:** Persistence ($y_{t+h} = y_t$)
* **Baseline 2:** Seasonal-naive ($y_{t+h} = y_{t+h-168}$ or $y_{t+h-24}$)
* **Baseline 3:** ENTSO-E Operational Day-Ahead Forecast [6.1.B]
* **Candidate Model:** Gradient-boosted decision trees (GBDT) / interpretable statistical models.

Target Horizons: 1-hour, 6-hour, 12-hour, 24-hour, and 48-hour operational horizons.

---

## 5. Repository Structure

```
p4-grid-load-forecasting/
├── config/
│   └── settings.py              # Configuration & environment variables
├── data/
│   ├── raw/                     # Pristine raw downloads / API responses
│   ├── processed/               # Cleaned hourly series (UTC canonical)
│   └── metadata/                # Retrieval timestamps, API query records
├── docs/
│   ├── gate0_spec.md            # Gate 0 mathematical & logical criteria
│   └── entsoe_access_guide.md   # ENTSO-E registration and token guide
├── reports/
│   ├── figures/                 # Diagnostic audit figures (ACF, differences)
│   └── gate0_audit_report.md    # Formal audit report
├── src/
│   ├── data/
│   │   ├── client.py            # ENTSO-E Transparency REST API client
│   │   └── ingest.py            # Raw data ingestion & validation
│   └── audit/
│       ├── provenance.py         # Gate 0.1 provenance auditor
│       ├── timezone_dst.py       # Gate 0.2 DST & timezone auditor
│       ├── continuity.py         # Gate 0.3 timestamp continuity auditor
│       ├── artificial_data.py    # Gate 0.4 interpolation & flatline auditor
│       ├── forecast_semantics.py # Gate 0.5 information boundary auditor
│       └── gate0_runner.py       # Master audit orchestrator
└── tests/                       # Unit tests & fault-injection fixtures
```

---

## 6. Getting Started

### Prerequisites
* Python 3.10+
* ENTSO-E API Security Token (see [ENTSO-E Access Guide](docs/entsoe_access_guide.md))

### Installation
```bash
pip install -r requirements.txt
```

### Configure Credentials
Copy `.env.example` to `.env` and add your ENTSO-E security token:
```bash
cp .env.example .env
```

### Run Tests
```bash
pytest tests/ -v
```

### Run Gate 0 Audit
```bash
python -m src.audit.gate0_runner
```
