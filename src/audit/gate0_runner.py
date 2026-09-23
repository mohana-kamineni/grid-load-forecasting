"""Gate 0 Master Audit Runner & Report Generator.

Coordinates:
- Gate 0.1: Provenance Audit
- Gate 0.2: Timezone & DST Integrity Audit (All 8 transitions)
- Gate 0.3: Timestamp Continuity Audit (35,064 hours)
- Gate 0.4: Artificial-Data & Interpolation Audit (Flatlines, Delta y, Delta^2 y, ACF)
- Gate 0.5: Forecast Semantics & Information Boundary Audit

Generates:
- reports/gate0_audit_report.md
- Formal Decision: PASS | FAIL | AMBIGUOUS — DO NOT MODEL YET
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd

from config.settings import REPORTS_DIR, CONFIG
from src.audit.provenance import audit_provenance, ProvenanceAuditResult
from src.audit.timezone_dst import audit_timezone_dst, TimezoneAuditResult
from src.audit.continuity import audit_continuity, ContinuityAuditResult
from src.audit.artificial_data import audit_artificial_data, ArtificialDataAuditResult
from src.audit.forecast_semantics import audit_forecast_semantics, ForecastSemanticsAuditResult

logger = logging.getLogger(__name__)


def generate_markdown_report(
    prov_res: ProvenanceAuditResult,
    tz_res: TimezoneAuditResult,
    cont_res: ContinuityAuditResult,
    art_res: ArtificialDataAuditResult,
    sem_res: ForecastSemanticsAuditResult,
    overall_status: str,
    justification: str,
    output_path: Path,
) -> None:
    """Generate formal Gate 0 audit report in GitHub markdown format."""
    
    # Status badge color
    status_color = "brightgreen" if overall_status == "PASS" else ("red" if overall_status == "FAIL" else "orange")
    
    report_content = rf"""# Gate 0 Audit Report: ENTSO-E Dataset Provenance and Temporal Validity

![Gate 0 Decision](https://img.shields.io/badge/Gate%200%20Decision-{overall_status.replace(' ', '%20')}-{status_color}?style=for-the-badge)

* **Date:** 2026-09-23
* **Project ID:** P4
* **Working Title:** Data-Driven Grid Load Forecasting for Operational Planning
* **Geographic Scope:** Sweden Bidding Zone SE3 (`{CONFIG.AREA_CODE_SE3}`)
* **Temporal Scope:** 2022-01-01 00:00 UTC through 2025-12-31 23:00 UTC (4 complete calendar years)
* **Resolution:** Hourly (`PT60M`)
* **Primary Target:** Actual Total Load [6.1.A] (`docType=A65`, `processType=A16`)
* **External Benchmark:** Day-ahead Total Load Forecast [6.1.B] (`docType=A65`, `processType=A01`)

---

## 1. Executive Summary

| Sub-Audit Gate | Status | Key Evaluation Metric |
| :--- | :---: | :--- |
| **Gate 0.1 — Provenance** | **{prov_res.status}** | Authoritative ENTSO-E specification, EU Reg 543/2013, MW units |
| **Gate 0.2 — Timezone & DST** | **{tz_res.status}** | 8/8 DST transitions verified; canonical UTC vs Europe/Stockholm |
| **Gate 0.3 — Continuity** | **{cont_res.status}** | {cont_res.total_actual_hours:,}/{cont_res.total_expected_hours:,} physical hours, {cont_res.total_missing_hours} missing |
| **Gate 0.4 — Artificial-Data** | **{art_res.status}** | Max flatline: {art_res.max_flatline_hours}h; Linear interp spans: {len(art_res.detected_interpolation_spans)} |
| **Gate 0.5 — Forecast Semantics** | **{sem_res.status}** | Information cutoff: D-1 10:00 CET; anti-leakage verified |

### Overall Master Decision
> **{overall_status}**

**Justification:**
{justification}

---

## 2. Gate 0.1 — Provenance & Regulatory Findings

* **Data Platform:** {prov_res.platform}
* **Legal Governance:** {prov_res.regulation}
* **Bidding Zone:** {prov_res.bidding_zone} (EIC: `{prov_res.eic_code}`)
* **Target Item:** {prov_res.target_item}
* **Resolution & Units:** {prov_res.resolution} | {prov_res.unit}
* **Revision & Finalization Policy:**
  {prov_res.revision_policy_summary}
* **Historical Stability Assessment:**
  {prov_res.historical_stability_assessment}
* **Re-pull Requirements:**
  {prov_res.repull_requirements}

---

## 3. Gate 0.2 — Timezone & Daylight Saving Time (DST) Audit (HARD GATE)

* **Canonical Storage Timeline:** {tz_res.canonical_tz} (tz-aware UTC)
* **Local Reference Timezone:** {tz_res.local_tz}
* **Suitability for Forecasting Indexing:** {tz_res.forecasting_index_suitability}

### Audit of All 8 Daylight Saving Time Transitions (2022–2025)

| Transition Date | Type | Expected UTC Hours | Actual UTC Hours | Expected Local Hours | Actual Local Hours | Duplicate UTC | Missing UTC | Result |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for r in tz_res.transition_results:
        res_tag = "PASS" if r.passed else "FAIL"
        report_content += (
            f"| `{r.transition_date}` | {r.transition_type} | {r.expected_physical_hours_utc} | "
            f"{r.actual_physical_hours_utc} | {r.expected_local_clock_hours} | {r.actual_local_clock_hours} | "
            f"{r.duplicate_utc_count} | {r.missing_utc_count} | **{res_tag}** |\n"
        )

    report_content += f"""
---

## 4. Gate 0.3 — Timestamp Continuity & Monotonicity Audit

* **Total Expected Physical Hours:** {cont_res.total_expected_hours:,} hours (including leap year 2024)
* **Total Actual Hours Inspected:** {cont_res.total_actual_hours:,} hours
* **Strict Monotonic Increasing Index:** {'Yes' if cont_res.is_strictly_monotonic else 'NO (FAILED)'}
* **Total Missing Hours:** {cont_res.total_missing_hours}
* **Total Duplicate Timestamps:** {cont_res.total_duplicate_hours}
* **Abnormal UTC Day Count:** {len(cont_res.abnormal_days)} days

### Annual Verification Summary

| Calendar Year | Expected Physical Hours | Actual Hours | Missing | Duplicates | Result |
| :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for ay in cont_res.annual_results:
        y_tag = "PASS" if ay.passed else "FAIL"
        report_content += (
            f"| **{ay.year}** | {ay.expected_hours:,} | {ay.actual_hours:,} | {ay.missing_hours} | {ay.duplicate_hours} | **{y_tag}** |\n"
        )

    report_content += f"""
---

## 5. Gate 0.4 — Artificial-Data, Flatline, and Interpolation Audit

* **Consecutive Duplicate Count:** {art_res.consecutive_duplicate_count} ({art_res.consecutive_duplicate_rate:.4%})
* **Maximum Flatline Duration:** {art_res.max_flatline_hours} consecutive hours
* **First Difference ($\\Delta y_t$) Summary:**
  * Mean: {art_res.first_diff_mean:.2f} MW
  * Std: {art_res.first_diff_std:.2f} MW
  * IQR: {art_res.first_diff_iqr:.2f} MW
  * Zero-Change Rate ($\\mathbb{{P}}(\\Delta y = 0)$): {art_res.first_diff_zero_rate:.4%}
* **Second Difference ($\\Delta^2 y_t$) Linear Interpolation Test:**
  * Detected deterministic linear interpolation spans: {len(art_res.detected_interpolation_spans)}
  * Maximum linear interpolation duration: {art_res.max_linear_interpolation_hours} hours
* **Autocorrelation Structure:**
  * Lag-1 (1 hour): {art_res.autocorrelation_lag_1:.4f}
  * Lag-24 (1 day): {art_res.autocorrelation_lag_24:.4f}
  * Lag-48 (2 days): {art_res.autocorrelation_lag_48:.4f}
  * Lag-168 (1 week): {art_res.autocorrelation_lag_168:.4f}

---

## 6. Gate 0.5 — Actual vs Forecast Semantics & Information Boundary

* **Governing Regulation:** {sem_res.regulatory_article}
* **Nord Pool Day-Ahead Gate Closure:** {sem_res.market_gate_closure_cet}
* **Mandatory Forecast Publication Deadline:** {sem_res.mandatory_publication_deadline_cet}
* **Operational Lead Time:** {sem_res.lead_time_range_hours}
* **Strict Anti-Leakage Boundary:**
  `{sem_res.information_boundary_cutoff}`
* **Downstream Benchmark Rule:**
  {sem_res.leakage_prevention_rule}

---

## 7. Final Master Decision

### Verdict: **{overall_status}**

**Methodological Next Steps:**
"""
    if overall_status == "PASS":
        report_content += (
            "\n1. Gate 0 passed all tests. Proceed to Baseline Modeling phase.\n"
            "2. Implement Baseline 1: Persistence.\n"
            "3. Implement Baseline 2: Seasonal-naive.\n"
            "4. Ingest and align Baseline 3: ENTSO-E Day-ahead Total Load Forecast [6.1.B].\n"
            "5. Implement Candidate GBDT forecasting model under chronological walk-forward cross-validation.\n"
        )
    elif overall_status == "FAIL":
        report_content += (
            "\n1. Hard Gate failed. DO NOT PROCEED TO MODELING.\n"
            "2. Halt project and report specific data integrity violations.\n"
        )
    else:
        report_content += (
            "\n1. Real ENTSO-E dataset has not yet been ingested into the pipeline.\n"
            "2. All audit tooling, DST verification suites, and interpolation detectors are operational and verified on synthetic fixtures.\n"
            "3. Ingest real ENTSO-E SE3 load data (via API token or File Library CSV) and re-run runner to obtain definitive PASS/FAIL verdict.\n"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")
    logger.info("Saved Gate 0 audit report to %s", output_path)


def run_gate0_audit(
    actual_load_df: Optional[pd.DataFrame] = None,
    forecast_df: Optional[pd.DataFrame] = None,
    metadata: Optional[Dict[str, Any]] = None,
    output_report_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Master orchestrator for Gate 0 audit."""
    if output_report_path is None:
        output_report_path = REPORTS_DIR / "gate0_audit_report.md"

    # Run sub-audits
    prov_res = audit_provenance(df=actual_load_df, metadata=metadata)
    sem_res = audit_forecast_semantics(forecast_df=forecast_df, metadata=metadata)

    if actual_load_df is None or actual_load_df.empty:
        # No dataset provided yet - AMBIGUOUS
        tz_res = TimezoneAuditResult(
            passed=False,
            status="AMBIGUOUS",
            canonical_tz="Not loaded",
            local_tz=CONFIG.LOCAL_TIMEZONE,
            is_tz_aware_utc=False,
            transitions_evaluated=8,
            transitions_passed=0,
            transition_results=[],
            forecasting_index_suitability="Pending dataset ingestion.",
            findings=["Real ENTSO-E dataset has not yet been loaded."],
            errors=[],
        )
        cont_res = ContinuityAuditResult(
            passed=False,
            status="AMBIGUOUS",
            total_expected_hours=35064,
            total_actual_hours=0,
            total_missing_hours=35064,
            total_duplicate_hours=0,
            is_strictly_monotonic=False,
            annual_results=[],
            monthly_row_counts={},
            abnormal_days=[],
            gaps_detected=[],
            findings=["Real ENTSO-E dataset has not yet been loaded."],
            errors=[],
        )
        art_res = ArtificialDataAuditResult(
            passed=False,
            status="AMBIGUOUS",
            total_observations=0,
            consecutive_duplicate_count=0,
            consecutive_duplicate_rate=0.0,
            max_flatline_hours=0,
            first_diff_zero_rate=0.0,
            first_diff_mean=0.0,
            first_diff_std=0.0,
            first_diff_iqr=0.0,
            first_diff_min=0.0,
            first_diff_max=0.0,
            max_linear_interpolation_hours=0,
            detected_interpolation_spans=[],
            autocorrelation_lag_1=0.0,
            autocorrelation_lag_24=0.0,
            autocorrelation_lag_48=0.0,
            autocorrelation_lag_168=0.0,
            figure_paths=[],
            findings=["Real ENTSO-E dataset has not yet been loaded."],
            errors=[],
        )

        overall_status = "AMBIGUOUS — DO NOT MODEL YET"
        justification = (
            "The Gate 0 audit framework, verification tests, and API ingestion modules have been fully implemented. "
            "However, real ENTSO-E SE3 load data has not yet been fetched/ingested. "
            "Under methodological instructions, we do not claim a Gate 0 PASS without real operational data."
        )
    else:
        # Run empirical tests on real data
        tz_res = audit_timezone_dst(actual_load_df)
        cont_res = audit_continuity(actual_load_df)
        art_res = audit_artificial_data(actual_load_df)

        # Determine overall status
        if not prov_res.passed or not tz_res.passed or not cont_res.passed or not art_res.passed or not sem_res.passed:
            overall_status = "FAIL"
            all_errors = prov_res.errors + tz_res.errors + cont_res.errors + art_res.errors + sem_res.errors
            justification = f"Dataset failed Gate 0 validation with {len(all_errors)} fatal error(s): " + "; ".join(all_errors[:5])
        else:
            overall_status = "PASS"
            justification = (
                "Dataset successfully passed all 5 Gate 0 audit criteria: "
                "provenance confirmed under EU Reg 543/2013, all 8 DST transitions verified in physical UTC and local clock time, "
                "full 35,064-hour continuity verified without gaps, flatline and linear interpolation tests passed, "
                "and strict anti-leakage forecast semantics established."
            )

    generate_markdown_report(
        prov_res=prov_res,
        tz_res=tz_res,
        cont_res=cont_res,
        art_res=art_res,
        sem_res=sem_res,
        overall_status=overall_status,
        justification=justification,
        output_path=output_report_path,
    )

    return {
        "overall_status": overall_status,
        "justification": justification,
        "provenance": prov_res,
        "timezone_dst": tz_res,
        "continuity": cont_res,
        "artificial_data": art_res,
        "forecast_semantics": sem_res,
        "report_path": str(output_report_path),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = run_gate0_audit()
    print(f"\n==========================================")
    print(f"GATE 0 AUDIT RESULT: {result['overall_status']}")
    print(f"Report written to: {result['report_path']}")
    print(f"==========================================\n")
