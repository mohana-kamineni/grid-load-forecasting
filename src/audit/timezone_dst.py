"""Gate 0.2 — Timezone & Daylight Saving Time (DST) Integrity Audit (HARD GATE).

Verifies:
1. Canonical timeline is timezone-aware UTC.
2. Conversion to Europe/Stockholm behaves according to Swedish DST rules.
3. Rigorous audit of ALL 8 DST transitions across 2022–2025:
   - 2022-03-27 (spring-forward)
   - 2022-10-30 (autumn-fallback)
   - 2023-03-26 (spring-forward)
   - 2023-10-29 (autumn-fallback)
   - 2024-03-31 (spring-forward)
   - 2024-10-27 (autumn-fallback)
   - 2025-03-30 (spring-forward)
   - 2025-10-26 (autumn-fallback)
4. Asserts 24 physical hours in UTC for every transition day.
5. Confirms 23 wall-clock hours (spring) and 25 wall-clock hours (autumn) in local time.
6. Evaluates time index suitability for operational lag features.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import pandas as pd

from config.settings import CONFIG


@dataclass
class DSTTransitionResult:
    """Audit result for a single DST transition event."""
    transition_date: str
    transition_type: str  # spring_forward or autumn_fallback
    expected_physical_hours_utc: int
    actual_physical_hours_utc: int
    expected_local_clock_hours: int
    actual_local_clock_hours: int
    unique_utc_timestamps: int
    duplicate_utc_count: int
    missing_utc_count: int
    passed: bool
    details: str


@dataclass
class TimezoneAuditResult:
    """Overall result of Gate 0.2 Timezone & DST Audit."""
    passed: bool
    status: str  # PASS / FAIL / AMBIGUOUS
    canonical_tz: str
    local_tz: str
    is_tz_aware_utc: bool
    transitions_evaluated: int
    transitions_passed: int
    transition_results: List[DSTTransitionResult]
    forecasting_index_suitability: str
    findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def audit_timezone_dst(df: pd.DataFrame) -> TimezoneAuditResult:
    """Execute Gate 0.2 Timezone & DST integrity audit across all 8 transitions."""
    findings = []
    errors = []
    transition_results: List[DSTTransitionResult] = []

    # 1. Base Timezone Integrity
    if not isinstance(df.index, pd.DatetimeIndex):
        errors.append(f"DataFrame index is {type(df.index)}, expected pd.DatetimeIndex.")
        return TimezoneAuditResult(
            passed=False,
            status="FAIL",
            canonical_tz="Unknown",
            local_tz=CONFIG.LOCAL_TIMEZONE,
            is_tz_aware_utc=False,
            transitions_evaluated=0,
            transitions_passed=0,
            transition_results=[],
            forecasting_index_suitability="Unsuitable: Index is not a DatetimeIndex.",
            findings=findings,
            errors=errors,
        )

    tz = df.index.tz
    is_utc = tz is not None and str(tz).upper() in ("UTC", "DATETIME.TIMEZONE.UTC", "+00:00")
    if not is_utc:
        errors.append(f"Canonical index timezone is '{tz}', expected timezone-aware 'UTC'.")
        return TimezoneAuditResult(
            passed=False,
            status="FAIL",
            canonical_tz=str(tz) if tz is not None else "None",
            local_tz=CONFIG.LOCAL_TIMEZONE,
            is_tz_aware_utc=False,
            transitions_evaluated=len(CONFIG.DST_TRANSITIONS),
            transitions_passed=0,
            transition_results=[],
            forecasting_index_suitability="Unsuitable: Index is not timezone-aware UTC.",
            findings=findings,
            errors=errors,
        )

    findings.append("Canonical timeline verified as timezone-aware UTC.")

    # Convert to local Swedish time (Europe/Stockholm) for wall-clock inspection
    try:
        df_local = df.tz_convert(CONFIG.LOCAL_TIMEZONE)
        findings.append(f"Successfully converted series to local timezone: {CONFIG.LOCAL_TIMEZONE}")
    except Exception as e:
        errors.append(f"Failed to convert UTC index to {CONFIG.LOCAL_TIMEZONE}: {e}")
        df_local = None

    # 2. Inspect all 8 DST Transitions
    dst_configs = CONFIG.DST_TRANSITIONS
    transitions_passed_count = 0

    for date_str, trans_type, expected_clock_hours in dst_configs:
        # A transition date defines a 24-hour UTC window: [date 00:00 UTC, date 23:59:59 UTC]
        start_utc = pd.Timestamp(f"{date_str} 00:00:00", tz="UTC")
        end_utc = pd.Timestamp(f"{date_str} 23:59:59", tz="UTC")

        # Slice UTC
        slice_utc = df.loc[(df.index >= start_utc) & (df.index <= end_utc)]
        actual_physical_hours = len(slice_utc)
        unique_utc = slice_utc.index.nunique()
        duplicate_utc = actual_physical_hours - unique_utc
        
        # Check missing hours in UTC physical window
        expected_physical = 24
        missing_utc = max(0, expected_physical - unique_utc)

        # Slice Local Day
        actual_local_clock_hours = -1
        if df_local is not None:
            # Slicing by local calendar date
            local_slice = df_local.loc[date_str] if date_str in df_local.index else pd.DataFrame()
            actual_local_clock_hours = len(local_slice)

        # Check conditions
        trans_passed = True
        trans_issues = []

        if actual_physical_hours != expected_physical:
            trans_passed = False
            trans_issues.append(f"UTC physical hours = {actual_physical_hours} (expected {expected_physical})")

        if duplicate_utc > 0:
            trans_passed = False
            trans_issues.append(f"Duplicate UTC timestamps = {duplicate_utc}")

        if missing_utc > 0:
            trans_passed = False
            trans_issues.append(f"Missing UTC timestamps = {missing_utc}")

        if df_local is not None and actual_local_clock_hours != expected_clock_hours:
            trans_passed = False
            trans_issues.append(
                f"Local {CONFIG.LOCAL_TIMEZONE} clock hours = {actual_local_clock_hours} (expected {expected_clock_hours})"
            )

        if trans_passed:
            transitions_passed_count += 1
            details = f"PASSED: 24 physical UTC hours verified; local clock reflects {actual_local_clock_hours}h for {trans_type}."
        else:
            details = "FAILED: " + "; ".join(trans_issues)
            errors.append(f"DST Transition {date_str} ({trans_type}): {details}")

        transition_results.append(
            DSTTransitionResult(
                transition_date=date_str,
                transition_type=trans_type,
                expected_physical_hours_utc=expected_physical,
                actual_physical_hours_utc=actual_physical_hours,
                expected_local_clock_hours=expected_clock_hours,
                actual_local_clock_hours=actual_local_clock_hours,
                unique_utc_timestamps=unique_utc,
                duplicate_utc_count=duplicate_utc,
                missing_utc_count=missing_utc,
                passed=trans_passed,
                details=details,
            )
        )

    # 3. Time Index Suitability for Forecasting
    if len(errors) == 0:
        suitability = (
            "SUITABLE: Canonical timeline is strictly continuous in UTC physical hours. "
            "Lag features (e.g. lag_24, lag_168) operate on uninterrupted physical intervals. "
            "Local calendar features (hour_of_day, day_of_week) can be derived via tz_convert('Europe/Stockholm') "
            "without disrupting the underlying time-delta continuity."
        )
        passed = True
        status = "PASS"
        findings.append(f"All {len(dst_configs)} DST transitions passed validation.")
    else:
        suitability = "UNSUITABLE: Detected DST indexing corruption, missing hours, or duplicate timestamps."
        passed = False
        status = "FAIL"

    return TimezoneAuditResult(
        passed=passed,
        status=status,
        canonical_tz=str(df.index.tz) if df.index.tz else "None",
        local_tz=CONFIG.LOCAL_TIMEZONE,
        is_tz_aware_utc=is_utc,
        transitions_evaluated=len(dst_configs),
        transitions_passed=transitions_passed_count,
        transition_results=transition_results,
        forecasting_index_suitability=suitability,
        findings=findings,
        errors=errors,
    )
