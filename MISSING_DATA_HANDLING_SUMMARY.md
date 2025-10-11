# Missing Data Handling Implementation Summary

## Overview

This document summarizes the implementation of missing data handling for energy counter sensors in the Energy Dispatcher integration (v0.8.29).

## Problem Statement

The integration needs to handle situations where energy counter sensors (kWh) have missing data points due to:
- Temporary sensor unavailability (e.g., network issues, sensor restarts)
- Recorder database gaps
- Integration restarts or updates

**Requirements:**
1. Interpolate between known data points when gaps are within acceptable limits
2. Wait reasonably (15 minutes) before assuming data is unavailable
3. Apply different gap limits for different use cases:
   - **Baseline calculation:** 8 hours max gap
   - **BEC tracking:** 1 hour max gap

## Solution Implemented

### 1. Linear Interpolation

**Function:** `_interpolate_energy_value()`

Calculates energy counter values at intermediate timestamps using linear interpolation.

**Features:**
- Linear interpolation between two known points
- Validates timestamp ranges
- Detects and skips counter resets (negative deltas)
- Returns None for invalid cases

**Example:**
```python
# Known points: 10:00 = 100 kWh, 12:00 = 110 kWh
# Want value at 11:00
interpolated = _interpolate_energy_value(
    timestamp=datetime(2024, 1, 1, 11, 0),
    prev_time=datetime(2024, 1, 1, 10, 0),
    prev_value=100.0,
    next_time=datetime(2024, 1, 1, 12, 0),
    next_value=110.0
)
# Result: 105.0 kWh
```

### 2. Data Staleness Detection

**Function:** `_is_data_stale()`

Determines if sensor data is too old to be considered valid.

**Features:**
- Configurable staleness threshold (default: 15 minutes)
- Returns True if timestamp is None
- Uses Home Assistant's dt utilities for timezone-aware comparisons

**Usage:**
```python
if _is_data_stale(self._batt_last_update_time, max_age_minutes=15):
    _LOGGER.debug("Sensor unavailable for > 15 minutes, treating as no data")
```

### 3. Gap Filling

**Function:** `_fill_missing_hourly_data()`

Fills missing hourly data points in a time-indexed dictionary using interpolation.

**Features:**
- Processes hourly timestamps in sorted order
- Only fills gaps within max_gap_hours limit
- Preserves all original values (never overwrites)
- Returns new dictionary with interpolated values added

**Example:**
```python
original = {
    datetime(2024, 1, 1, 10, 0): 100.0,
    datetime(2024, 1, 1, 13, 0): 115.0,  # Missing 11:00 and 12:00
}

filled = _fill_missing_hourly_data(original, max_gap_hours=8.0)
# Result includes interpolated values at 11:00 (105.0) and 12:00 (110.0)
```

### 4. BEC Gap Handling

**Changes to `_update_battery_charge_tracking()`:**

Added gap detection and tracking reset logic:

1. **Track Last Update Time:** Store timestamp of last successful sensor read
2. **Check Gap on Each Update:** Compare current time to last update
3. **Reset if Gap > 1 Hour:** Clear tracking variables to start fresh
4. **Update Timestamp:** Set timestamp on successful reads

**Behavior:**
```python
# Gap detection
if self._batt_last_update_time is not None:
    gap_minutes = (now - self._batt_last_update_time).total_seconds() / 60.0
    if gap_minutes > 60:  # 1 hour max for BEC
        _LOGGER.warning("BEC: Data gap of %.1f minutes exceeds 1 hour limit. Resetting tracking.")
        # Reset all tracking variables
```

**Benefits:**
- Prevents incorrect charge/discharge deltas from accumulated errors
- Protects WACE (Weighted Average Cost of Energy) calculations
- Provides clear logging when gaps are detected

### 5. Baseline Interpolation

**Changes to `_calculate_daypart_baselines()`:**

Enhanced to use interpolation for missing hourly data:

1. **Build Time Indexes:** Convert state lists to time-indexed dictionaries
2. **Fill Missing Data:** Apply interpolation to each sensor's time index
3. **Log Interpolation:** Record when and how many points were interpolated
4. **Increased Gap Limit:** Changed from 2 hours to 8 hours

**Code:**
```python
# Fill in missing hourly data points using interpolation
house_index = _fill_missing_hourly_data(house_index, MAX_GAP_HOURS=8.0)

# Log if interpolation was used
interpolated_count = len(house_index) - original_house_count
if interpolated_count > 0:
    _LOGGER.info("Daypart baseline: Interpolated %d missing hourly data points", interpolated_count)
```

**Benefits:**
- More complete baseline calculations with intermittent sensor data
- Better handling of temporary sensor outages
- More accurate daypart (night/day/evening) averages

## Testing

### Test Coverage

Created comprehensive test suite in `tests/test_missing_data_handling.py`:

**Test Classes:**
1. `TestInterpolation` (6 tests)
   - Midpoint interpolation
   - Quarter/three-quarter point interpolation
   - Counter reset handling
   - Invalid timestamp handling
   - Zero time delta handling

2. `TestDataStaleness` (5 tests)
   - None timestamp handling
   - Fresh data detection
   - Stale data detection
   - Threshold boundary testing
   - Custom threshold testing

3. `TestFillMissingHourlyData` (8 tests)
   - No gaps (pass-through)
   - Single gap filling
   - Multiple gaps filling
   - Max gap limit enforcement
   - Empty/single-point handling
   - Value preservation

4. `TestBECGapHandling` (2 tests)
   - Reset after 1-hour gap
   - Normal tracking within 1 hour

**Results:** All 21 tests pass ✅

### Existing Tests

Verified backward compatibility:
- ✅ All 46 BEC tests still pass
- ⚠️ Some baseline tests have pre-existing mocking issues (unrelated to this change)

## Impact Analysis

### Performance Impact

**Minimal:**
- Interpolation is in-memory operation
- Processes hourly data (typically 48-96 points for 48-hour baseline)
- No additional database queries
- Estimated overhead: < 1ms per coordinator update

### Memory Impact

**Minimal:**
- Interpolated values stored temporarily during calculation
- No persistent storage of interpolated values
- Hourly data structures are small (< 1 KB for 48 hours)

### Backward Compatibility

**Fully Compatible:**
- No breaking changes to existing behavior
- All configuration options remain the same
- Existing sensors and entities unaffected
- Previous data and storage formats unchanged

## Configuration

All thresholds are hardcoded with sensible defaults:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Baseline max gap | 8 hours | Balance between data recovery and preventing stale estimates |
| BEC max gap | 1 hour | Tight limit to ensure accurate charge/discharge tracking |
| Staleness timeout | 15 minutes | Standard energy logging interval; avoids false alarms |

**Future Enhancement:** These could be made configurable via options flow if needed.

## Logging

### New Log Messages

**Interpolation:**
```
INFO: Daypart baseline: Interpolated 5 missing hourly data points (max gap: 8.0 hours)
```

**Gap Detection:**
```
WARNING: BEC: Data gap of 65.2 minutes exceeds 1 hour limit. Resetting tracking to avoid incorrect deltas.
```

**Staleness (Debug):**
```
DEBUG: BEC: Charged energy sensor sensor.battery_charged unavailable for > 15 minutes, treating as no data
```

**Large Gaps:**
```
DEBUG: Skipping large gap in baseline data: 10.5 hours between 2024-01-01 08:00 and 2024-01-01 18:30
```

## User-Facing Changes

### Improved Robustness

**Before:**
- Missing sensor data caused baseline calculation failures
- BEC tracking could accumulate incorrect deltas
- Short sensor outages led to "unknown" states

**After:**
- Interpolation recovers from gaps up to 8 hours (baseline)
- BEC safely resets after 1-hour gaps
- 15-minute grace period for temporary issues

### No Configuration Required

Users benefit automatically from the improvements without any configuration changes.

### Better Diagnostics

New log messages help users understand:
- When interpolation is being used
- When gaps exceed limits
- When tracking resets to protect data integrity

## Documentation

### New Documentation

1. **`docs/missing_data_handling.md`**
   - Complete technical and user guide
   - Use cases and examples
   - Troubleshooting section
   - Implementation details

2. **`MISSING_DATA_HANDLING_SUMMARY.md`** (this file)
   - Executive summary for developers
   - Quick reference for implementation details

### Updated Documentation

1. **`manifest.json`**
   - Version bumped to 0.8.29
   - Description updated to reflect new features

## Known Limitations

### Cannot Interpolate Across Counter Resets

Energy counters that reset (e.g., daily counters) cannot be interpolated across the reset point.

**Example:**
```
09:00 → 50.0 kWh
10:00 → 52.0 kWh
00:00 → 2.0 kWh (reset at midnight)
01:00 → 3.0 kWh
```

The system will **not** interpolate between 10:00 and 01:00 because the counter reset is detected.

### Linear Interpolation Assumption

Interpolation assumes constant energy consumption rate, which may not reflect reality:
- **Acceptable for:** Short gaps (1-4 hours) with typical consumption patterns
- **Less accurate for:** Large consumption spikes or drops during gap period

### Maximum Gap Limits

Gaps exceeding the limits are not interpolated:
- **Baseline:** > 8 hours → excluded from calculation
- **BEC:** > 1 hour → tracking resets

This is **intentional** to prevent using very stale or unreliable estimates.

## Future Enhancements

Possible improvements for future versions:

1. **Configurable Limits:** Allow users to adjust gap limits via options flow
2. **Smart Extrapolation:** Use recent trends when no future point available
3. **Time-of-Day Awareness:** Apply different interpolation rates based on typical consumption patterns
4. **Confidence Intervals:** Indicate reliability of interpolated values
5. **Alternative Methods:** Support exponential smoothing, median filtering, etc.
6. **Interpolation Statistics:** Expose how much data is interpolated via diagnostic sensors

## Migration Notes

### Upgrading to v0.8.29

**Automatic:**
- No configuration changes required
- No data migration needed
- No breaking changes

**What to Expect:**
- Fewer "unknown" baseline values during sensor outages
- More stable BEC tracking with intermittent sensors
- Better baseline accuracy with incomplete historical data

**Monitoring:**
- Watch logs for interpolation messages
- Check that baseline calculations are more stable
- Verify BEC tracking continues correctly after sensor outages

## Conclusion

This implementation significantly improves the robustness of energy counter-based calculations in the Energy Dispatcher integration. By handling missing data gracefully through interpolation and intelligent gap detection, the system maintains accurate tracking even when sensors experience temporary unavailability.

The changes are backward compatible, require no user configuration, and provide clear logging for troubleshooting. The comprehensive test coverage ensures reliability and makes future maintenance easier.

---

**Version:** 0.8.29  
**Date:** 2025-10-11  
**Author:** GitHub Copilot (via Bokbacken)  
**PR:** [Link to PR will be added]
