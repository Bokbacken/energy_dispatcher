#!/usr/bin/env python3
"""
Sample Data Validation and Test Window Extraction Script

This script:
1. Loads all sample data from tests/fixtures/
2. Validates data quality (gaps, monotonicity, ranges)
3. Identifies best continuous windows for testing
4. Extracts perfect windows for test fixtures
5. Generates a detailed validation report

Usage:
    python tests/validate_sample_data.py
    python tests/validate_sample_data.py --extract-windows
    python tests/validate_sample_data.py --report-only
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reuse the data quality report infrastructure
from data_quality_report import (
    FIXTURES_DIR,
    SeriesStats,
    analyze_series,
    is_cumulative,
    load_csv_series,
    parse_timestamp,
)

PERFECT_WINDOWS_DIR = FIXTURES_DIR / "perfect_windows"
GAPPY_WINDOWS_DIR = FIXTURES_DIR / "gappy_windows"


@dataclass
class ValidationResult:
    """Result of validating a data file."""
    filename: str
    valid: bool
    stats: SeriesStats
    issues: List[str]
    recommendations: List[str]
    best_window: Optional[Tuple[datetime, datetime, float]]  # start, end, hours


def validate_price_data(stats: SeriesStats) -> Tuple[List[str], List[str]]:
    """Validate price data specifically."""
    issues = []
    recommendations = []
    
    # Check for reasonable price ranges (0.1 to 10 SEK/kWh)
    if stats.min_value is not None and stats.min_value < 0.0:
        issues.append(f"Negative prices detected: {stats.min_value:.3f} SEK/kWh")
    if stats.min_value is not None and stats.min_value < 0.1:
        recommendations.append(f"Very low price detected: {stats.min_value:.3f} SEK/kWh - verify this is correct")
    if stats.max_value is not None and stats.max_value > 10.0:
        recommendations.append(f"Very high price detected: {stats.max_value:.3f} SEK/kWh - good for spike testing")
    
    # Check for hourly intervals
    if stats.median_interval_seconds and stats.median_interval_seconds != 3600:
        issues.append(f"Expected hourly intervals, got {stats.median_interval_seconds}s median")
    
    return issues, recommendations


def validate_battery_soc(stats: SeriesStats) -> Tuple[List[str], List[str]]:
    """Validate battery SOC data."""
    issues = []
    recommendations = []
    
    # Check for valid SOC range (0-100%)
    if stats.min_value is not None and stats.min_value < 0:
        issues.append(f"Invalid SOC: {stats.min_value:.1f}% (below 0%)")
    if stats.max_value is not None and stats.max_value > 100:
        issues.append(f"Invalid SOC: {stats.max_value:.1f}% (above 100%)")
    
    # Check for reasonable variation
    if stats.min_value is not None and stats.max_value is not None:
        range_pct = stats.max_value - stats.min_value
        if range_pct < 10:
            recommendations.append(f"Limited SOC variation: {range_pct:.1f}% - may not show full charge/discharge cycles")
    
    return issues, recommendations


def validate_power_data(stats: SeriesStats) -> Tuple[List[str], List[str]]:
    """Validate power data (W or kW)."""
    issues = []
    recommendations = []
    
    # Check for extremely high values (>50kW suggests incorrect unit)
    if stats.max_value is not None and stats.max_value > 50000:
        recommendations.append(f"Very high power: {stats.max_value:.0f}W - verify units are correct")
    
    # Check for variation
    if stats.min_value is not None and stats.max_value is not None:
        if abs(stats.max_value - stats.min_value) < 10:
            recommendations.append("Very little power variation - may indicate inactive period")
    
    return issues, recommendations


def validate_cumulative_meter(stats: SeriesStats) -> Tuple[List[str], List[str]]:
    """Validate cumulative energy meter data."""
    issues = []
    recommendations = []
    
    # Check for non-monotonic behavior
    if stats.non_monotonic_count > 0:
        if stats.non_monotonic_count < 10:
            recommendations.append(f"{stats.non_monotonic_count} non-monotonic segments detected - may indicate daily resets")
        else:
            issues.append(f"{stats.non_monotonic_count} non-monotonic segments - data quality issue")
    
    # Check that values are increasing overall
    if stats.min_value is not None and stats.max_value is not None:
        if stats.max_value <= stats.min_value:
            issues.append("Cumulative meter not increasing - possible data quality issue")
    
    return issues, recommendations


def validate_data_file(path: Path) -> ValidationResult:
    """Validate a single data file and return results."""
    issues = []
    recommendations = []
    
    # Load and analyze
    times, values = load_csv_series(path)
    stats = analyze_series(path.name, times, values)
    
    # Basic validation
    if stats.count == 0:
        issues.append("No data points found")
        return ValidationResult(
            filename=path.name,
            valid=False,
            stats=stats,
            issues=issues,
            recommendations=recommendations,
            best_window=None
        )
    
    if stats.count < 10:
        recommendations.append(f"Very few data points: {stats.count}")
    
    # Type-specific validation
    name_lower = path.name.lower()
    
    if "price" in name_lower:
        type_issues, type_recs = validate_price_data(stats)
        issues.extend(type_issues)
        recommendations.extend(type_recs)
    elif "soc" in name_lower:
        type_issues, type_recs = validate_battery_soc(stats)
        issues.extend(type_issues)
        recommendations.extend(type_recs)
    elif "power" in name_lower:
        type_issues, type_recs = validate_power_data(stats)
        issues.extend(type_issues)
        recommendations.extend(type_recs)
    elif is_cumulative(path.name):
        type_issues, type_recs = validate_cumulative_meter(stats)
        issues.extend(type_issues)
        recommendations.extend(type_recs)
    
    # Gap analysis
    if len(stats.large_gaps) > 20:
        recommendations.append(f"{len(stats.large_gaps)} large gaps - expected for intermittent sensors (feed-in, charging)")
    elif len(stats.large_gaps) > 5:
        recommendations.append(f"{len(stats.large_gaps)} large gaps - may limit continuous testing windows")
    
    # Find best continuous window
    best_window = None
    if times and len(times) > 1:
        # Calculate gaps
        gap_threshold = max(3600.0, 3 * stats.median_interval_seconds) if stats.median_interval_seconds else 3600.0
        windows = []
        current_start = times[0]
        
        for i in range(len(times) - 1):
            gap = (times[i + 1] - times[i]).total_seconds()
            if gap >= gap_threshold:
                # End of window
                duration_h = (times[i] - current_start).total_seconds() / 3600
                if duration_h > 1.0:  # Only consider windows > 1 hour
                    windows.append((current_start, times[i], duration_h))
                current_start = times[i + 1]
        
        # Add final window
        duration_h = (times[-1] - current_start).total_seconds() / 3600
        if duration_h > 1.0:
            windows.append((current_start, times[-1], duration_h))
        
        if windows:
            best_window = max(windows, key=lambda w: w[2])
    
    # Overall validity
    valid = len(issues) == 0
    
    return ValidationResult(
        filename=path.name,
        valid=valid,
        stats=stats,
        issues=issues,
        recommendations=recommendations,
        best_window=best_window
    )


def extract_window(
    times: List[datetime],
    values: List[float],
    start: datetime,
    end: datetime,
    output_path: Path
):
    """Extract a time window and save to CSV."""
    # Find indices
    start_idx = None
    end_idx = None
    
    for i, t in enumerate(times):
        if start_idx is None and t >= start:
            start_idx = i
        if t <= end:
            end_idx = i
        else:
            break
    
    if start_idx is None or end_idx is None:
        print(f"Warning: Could not find window {start} to {end}")
        return
    
    # Write window
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'value'])
        for i in range(start_idx, end_idx + 1):
            writer.writerow([times[i].isoformat(), values[i]])
    
    print(f"Extracted {end_idx - start_idx + 1} points to {output_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Validate sample data and extract test windows")
    parser.add_argument('--extract-windows', action='store_true', help='Extract perfect windows for testing')
    parser.add_argument('--report-only', action='store_true', help='Only generate report, no extraction')
    args = parser.parse_args()
    
    print("=" * 80)
    print("SAMPLE DATA VALIDATION REPORT")
    print("=" * 80)
    print()
    
    # Load and validate all CSV files
    files = sorted([p for p in FIXTURES_DIR.glob("*.csv")])
    results: List[ValidationResult] = []
    
    for path in files:
        print(f"Validating {path.name}...")
        result = validate_data_file(path)
        results.append(result)
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    valid_count = sum(1 for r in results if r.valid)
    print(f"Files validated: {len(results)}")
    print(f"Valid files: {valid_count}")
    print(f"Files with issues: {len(results) - valid_count}")
    print()
    
    # Detailed results
    print("=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print()
    
    for result in results:
        print(f"📁 {result.filename}")
        print(f"   Status: {'✓ VALID' if result.valid else '⚠ ISSUES'}")
        print(f"   Points: {result.stats.count}")
        if result.stats.duration_hours:
            print(f"   Duration: {result.stats.duration_hours:.1f} hours")
        if result.stats.median_interval_seconds:
            print(f"   Interval: {result.stats.median_interval_seconds:.0f}s")
        
        if result.best_window:
            start, end, hours = result.best_window
            print(f"   Best window: {hours:.1f}h ({start} to {end})")
        
        if result.issues:
            print("   ⚠ Issues:")
            for issue in result.issues:
                print(f"      - {issue}")
        
        if result.recommendations:
            print("   💡 Recommendations:")
            for rec in result.recommendations:
                print(f"      - {rec}")
        
        print()
    
    # Test suitability
    print("=" * 80)
    print("TEST SUITABILITY")
    print("=" * 80)
    print()
    
    print("Excellent for testing (no gaps):")
    for result in results:
        if result.valid and len(result.stats.large_gaps) == 0:
            print(f"  ✓ {result.filename}")
    print()
    
    print("Good for testing (minor gaps):")
    for result in results:
        if result.valid and 0 < len(result.stats.large_gaps) <= 5:
            print(f"  ✓ {result.filename}")
    print()
    
    print("Fair for testing (multiple gaps):")
    for result in results:
        if result.valid and 5 < len(result.stats.large_gaps) <= 20:
            print(f"  ⚠ {result.filename}")
    print()
    
    # Extract windows if requested
    if args.extract_windows and not args.report_only:
        print("=" * 80)
        print("EXTRACTING PERFECT WINDOWS")
        print("=" * 80)
        print()
        
        PERFECT_WINDOWS_DIR.mkdir(exist_ok=True)
        GAPPY_WINDOWS_DIR.mkdir(exist_ok=True)
        
        for result in results:
            if result.best_window and result.best_window[2] > 12:  # > 12 hours
                times, values = load_csv_series(FIXTURES_DIR / result.filename)
                start, end, hours = result.best_window
                
                # Determine category
                if len(result.stats.large_gaps) == 0:
                    category = "perfect"
                    output_dir = PERFECT_WINDOWS_DIR
                else:
                    category = "gappy"
                    output_dir = GAPPY_WINDOWS_DIR
                
                output_name = f"{result.filename.replace('.csv', '')}_best_{hours:.0f}h.csv"
                output_path = output_dir / output_name
                
                extract_window(times, values, start, end, output_path)
        
        print()
        print(f"Extracted windows to:")
        print(f"  - {PERFECT_WINDOWS_DIR}")
        print(f"  - {GAPPY_WINDOWS_DIR}")
    
    print()
    print("=" * 80)
    print("Validation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
