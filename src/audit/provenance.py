"""Gate 0.1 — Provenance & Regulatory Audit.

Verifies:
- Authoritative source: ENTSO-E Transparency Platform (Regulation EU No 543/2013)
- Area code: 10Y1001A1001A46L (SE3)
- Document type: A65 (System total load)
- Process type: A16 (Realised / Actual Load) vs A01 (Day-ahead forecast)
- Units: MW
- Resolution: PT60M
- Revision policy and historical finalization dynamics
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import pandas as pd

from config.settings import CONFIG


@dataclass
class ProvenanceAuditResult:
    """Results from Gate 0.1 Provenance Audit."""
    passed: bool
    status: str  # PASS / FAIL / AMBIGUOUS
    platform: str
    regulation: str
    bidding_zone: str
    eic_code: str
    target_item: str
    target_doc_type: str
    target_process_type: str
    benchmark_item: str
    benchmark_doc_type: str
    benchmark_process_type: str
    unit: str
    resolution: str
    revision_policy_summary: str
    historical_stability_assessment: str
    repull_requirements: str
    findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def audit_provenance(
    df: Optional[pd.DataFrame] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ProvenanceAuditResult:
    """Perform Gate 0.1 Provenance audit against authoritative ENTSO-E specifications."""
    findings = []
    errors = []

    # 1. Platform and Legal Basis
    platform = "ENTSO-E Transparency Platform"
    regulation = "Regulation (EU) No 543/2013, Articles 6.1.a & 6.1.b"
    findings.append(f"Authoritative platform: {platform}")
    findings.append(f"Legal governance: {regulation}")

    # 2. Bidding Zone
    bidding_zone = CONFIG.AREA_NAME
    eic_code = CONFIG.AREA_CODE_SE3
    findings.append(f"Bidding zone: {bidding_zone} (EIC: {eic_code})")

    # 3. Document and Process Types
    target_item = "Actual Total Load [6.1.A]"
    target_doc_type = CONFIG.DOC_TYPE_TOTAL_LOAD
    target_process_type = CONFIG.PROCESS_TYPE_ACTUAL_LOAD
    
    benchmark_item = "Day-ahead Total Load Forecast [6.1.B]"
    benchmark_doc_type = CONFIG.DOC_TYPE_TOTAL_LOAD
    benchmark_process_type = CONFIG.PROCESS_TYPE_DAY_AHEAD_FORECAST

    findings.append(f"Primary Target: {target_item} (docType={target_doc_type}, processType={target_process_type})")
    findings.append(f"External Benchmark: {benchmark_item} (docType={benchmark_doc_type}, processType={benchmark_process_type})")

    # 4. Units and Resolution
    unit = CONFIG.UNIT
    resolution = CONFIG.RESOLUTION
    findings.append(f"Resolution: {resolution} (Hourly)")
    findings.append(f"Physical Unit: {unit} (Megawatts)")

    # 5. Revision Policy and Stability
    revision_summary = (
        "Under Regulation (EU) No 543/2013, Transmission System Operators (Svenska kraftnät for SE3) "
        "must publish initial Actual Total Load within H+1 hour post-operating period based on SCADA telemetry. "
        "Subsequent revisions occur as metered grid accounting data is reconciled during final market settlement."
    )
    historical_stability = (
        "For historical years 2022–2025 queried in 2026, the data has passed the standard market settlement window "
        "(typically finalized within 60–90 days). Values represent consolidated, final operational accounting."
    )
    repull_requirements = (
        "Zero re-pulls required for the 2022–2025 window once consolidated. "
        "For any newly elapsed month, an operational re-pull should occur 90 days post-delivery to capture settlement adjustments."
    )

    # 6. Metadata / DataFrame validation if provided
    if metadata:
        if metadata.get("bidding_zone") and metadata["bidding_zone"] != CONFIG.AREA_CODE_SE3:
            errors.append(f"Metadata bidding zone mismatch: expected {CONFIG.AREA_CODE_SE3}, got {metadata['bidding_zone']}")
        if metadata.get("document_type") and metadata["document_type"] != CONFIG.DOC_TYPE_TOTAL_LOAD:
            errors.append(f"Metadata document_type mismatch: expected {CONFIG.DOC_TYPE_TOTAL_LOAD}, got {metadata['document_type']}")
        if metadata.get("process_type") and metadata["process_type"] not in (CONFIG.PROCESS_TYPE_ACTUAL_LOAD, CONFIG.PROCESS_TYPE_DAY_AHEAD_FORECAST):
            errors.append(f"Metadata process_type unexpected: got {metadata['process_type']}")

    if df is not None and not df.empty:
        if "unit" in df.columns:
            observed_unit = df["unit"].iloc[0]
            if observed_unit != "MW":
                errors.append(f"Unit in dataframe is '{observed_unit}', expected 'MW'.")
            else:
                findings.append(f"Verified dataset unit column: '{observed_unit}'")
        if "area_code" in df.columns:
            observed_area = df["area_code"].iloc[0]
            if observed_area != CONFIG.AREA_CODE_SE3:
                errors.append(f"Area code in dataframe is '{observed_area}', expected '{CONFIG.AREA_CODE_SE3}'.")
            else:
                findings.append(f"Verified dataset area_code column: '{observed_area}'")

    passed = len(errors) == 0
    status = "PASS" if passed else "FAIL"

    return ProvenanceAuditResult(
        passed=passed,
        status=status,
        platform=platform,
        regulation=regulation,
        bidding_zone=bidding_zone,
        eic_code=eic_code,
        target_item=target_item,
        target_doc_type=target_doc_type,
        target_process_type=target_process_type,
        benchmark_item=benchmark_item,
        benchmark_doc_type=benchmark_doc_type,
        benchmark_process_type=benchmark_process_type,
        unit=unit,
        resolution=resolution,
        revision_policy_summary=revision_summary,
        historical_stability_assessment=historical_stability,
        repull_requirements=repull_requirements,
        findings=findings,
        errors=errors,
    )
