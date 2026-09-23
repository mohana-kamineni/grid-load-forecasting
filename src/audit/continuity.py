"""Gate 0.3 — Timestamp Continuity & Monotonicity Audit.

Verifies:
1. Complete 4-year temporal scope: 2022-01-01 to 2025-12-31.
2. Total physical hours equal 35,064 (accounting for 2024 leap year).
3. Monotonic chronological ordering (no time travel or sorting errors).
4. Uniform 1-hour interval spacing (zero gaps, zero overlaps).
5. Breakdown by year and month.
6. Detection of days with abnormal row counts (<24 or >24 in UTC).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import pandas as pd

from config.settings import CONFIG


@dataclass
class AnnualContinuityResult:
    """Audit summary for a single calendar year."""
    year: int
    expected_hours: int
    actual_hours: int
    missing_hours: int
    duplicate_hours: int
    passed: bool


@dataclass
class ContinuityAuditResult:
    """Overall result of Gate 0.3 Continuity Audit."""
    passed: bool
    status: str  # PASS / FAIL / AMBIGUOUS
    total_expected_hours: int
    total_actual_hours: int
    total_missing_hours: int
    total_duplicate_hours: int
    is_strictly_monotonic: bool
    annual_results: List[AnnualContinuityResult]
    monthly_row_counts: Dict[str, Dict[str, int]]  # 'YYYY-MM': {'expected': X, 'actual': Y}
    abnormal_days: List[Dict[str, Any]]            # list of days with abnormal row counts
    gaps_detected: List[Dict[str, Any]]
    findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def audit_continuity(df: pd.DataFrame) -> ContinuityAuditResult:
    """Audit timestamp continuity across 2022-2025 hourly series."""
    findings = []
    errors = []

    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        errors.append("DataFrame is empty or does not have DatetimeIndex.")
        return ContinuityAuditResult(
            passed=False,
            status="FAIL",
            total_expected_hours=35064,
            total_actual_hours=len(df),
            total_missing_hours=35064,
            total_duplicate_hours=0,
            is_strictly_monotonic=False,
            annual_results=[],
            monthly_row_counts={},
            abnormal_days=[],
            gaps_detected=[],
            findings=findings,
            errors=errors,
        )

    # 1. Total Scope Verification
    total_expected = sum(CONFIG.EXPECTED_HOURS_BY_YEAR.values())
    total_actual = len(df)
    findings.append(f"Total rows inspected: {total_actual} (Expected: {total_expected})")

    # 2. Monotonicity & Duplicates
    is_monotonic = df.index.is_monotonic_increasing
    if not is_monotonic:
        errors.append("Timestamp index is NOT strictly monotonic increasing.")
    else:
        findings.append("Timestamp index is strictly monotonic increasing.")

    duplicate_count = df.index.duplicated().sum()
    if duplicate_count > 0:
        errors.append(f"Detected {duplicate_count} duplicate timestamps.")
    else:
        findings.append("Zero duplicate timestamps detected.")

    # 3. Check against ideal continuous hourly reference grid in UTC
    ideal_index = pd.date_range(
        start=CONFIG.START_DATE_UTC,
        end=CONFIG.END_DATE_UTC,
        freq="1h",
        tz="UTC",
    )
    
    missing_timestamps = ideal_index.difference(df.index)
    total_missing = len(missing_timestamps)
    
    extra_timestamps = df.index.difference(ideal_index)
    total_extra = len(extra_timestamps)

    if total_missing > 0:
        errors.append(f"Detected {total_missing} missing hours relative to the canonical reference grid.")
    else:
        findings.append("Zero missing hours relative to canonical 2022-2025 UTC grid.")

    if total_extra > 0:
        findings.append(f"Found {total_extra} timestamps outside standard 2022-2025 window.")

    # Detect contiguous gap ranges
    gaps_detected = []
    if total_missing > 0:
        # Group missing into spans
        gap_series = pd.Series(missing_timestamps)
        step = (gap_series != gap_series.shift(1) + pd.Timedelta(hours=1)).cumsum()
        for _, span in gap_series.groupby(step):
            gaps_detected.append({
                "gap_start": str(span.iloc[0]),
                "gap_end": str(span.iloc[-1]),
                "missing_hours": len(span),
            })

    # 4. Annual Breakdown
    annual_results: List[AnnualContinuityResult] = []
    for year, exp_h in CONFIG.EXPECTED_HOURS_BY_YEAR.items():
        year_mask = df.index.year == year
        year_df = df[year_mask]
        act_h = len(year_df)
        year_dups = year_df.index.duplicated().sum()
        
        # Missing in this year
        year_ideal = ideal_index[ideal_index.year == year]
        year_missing = len(year_ideal.difference(year_df.index))
        
        y_passed = (act_h == exp_h) and (year_dups == 0) and (year_missing == 0)
        if not y_passed:
            errors.append(f"Year {year} failed: actual={act_h} (expected={exp_h}), missing={year_missing}, dups={year_dups}")
        else:
            findings.append(f"Year {year} PASSED: {act_h}/{exp_h} physical hours.")

        annual_results.append(
            AnnualContinuityResult(
                year=year,
                expected_hours=exp_h,
                actual_hours=act_h,
                missing_hours=year_missing,
                duplicate_hours=year_dups,
                passed=y_passed,
            )
        )

    # 5. Monthly Breakdown
    monthly_row_counts = {}
    for period, group in df.groupby(df.index.tz_localize(None).to_period("M")):
        period_str = str(period)
        exp_m_hours = period.days_in_month * 24
        monthly_row_counts[period_str] = {
            "expected": exp_m_hours,
            "actual": len(group),
            "difference": len(group) - exp_m_hours,
        }

    # 6. Days with abnormal row counts in UTC (<24 or >24)
    abnormal_days = []
    for day, day_group in df.groupby(df.index.date):
        if len(day_group) != 24:
            abnormal_days.append({
                "date": str(day),
                "actual_hours": len(day_group),
                "expected_hours": 24,
            })
            errors.append(f"Date {day} has abnormal row count in UTC: {len(day_group)} hours (expected 24).")

    passed = len(errors) == 0
    status = "PASS" if passed else "FAIL"

    return ContinuityAuditResult(
        passed=passed,
        status=status,
        total_expected_hours=total_expected,
        total_actual_hours=total_actual,
        total_missing_hours=total_missing,
        total_duplicate_hours=duplicate_count,
        is_strictly_monotonic=is_monotonic,
        annual_results=annual_results,
        monthly_row_counts=monthly_row_counts,
        abnormal_days=abnormal_days,
        gaps_detected=gaps_detected,
        findings=findings,
        errors=errors,
    )
