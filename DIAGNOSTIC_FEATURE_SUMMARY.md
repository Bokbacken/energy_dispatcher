# Diagnostic Feature Summary

## Problem
When the 48-hour baseline calculation failed, the "House Load Baseline Now" sensor would show "unknown" for the main value, and its attributes would show:
- `method`: `energy_counter_48h`
- `source_value`: `Okänd` (Unknown)
- `baseline_kwh_per_h`: `Okänd` (Unknown)  
- `exclusion_reason`: (empty)

This provided no information about **why** the calculation failed, making it very difficult to troubleshoot.

## Solution
Enhanced the diagnostic capabilities of the baseline calculation to provide clear, actionable failure reasons:

### 1. Failure Reason Tracking
Modified `_calculate_48h_baseline()` to return a dictionary that always includes a `failure_reason` key when calculation fails. Instead of returning `None`, it now returns:

```python
{
    "overall": None,
    "night": None,
    "day": None,
    "evening": None,
    "failure_reason": "Specific diagnostic message explaining why it failed"
}
```

### 2. Specific Diagnostic Messages
Added four distinct failure reasons with actionable guidance:

1. **"No house energy counter configured (runtime_counter_entity)"**
   - When: No energy counter sensor is configured in settings
   - Action: Configure the runtime_counter_entity setting

2. **"Insufficient historical data: X data points (need 2+)"**
   - When: Sensor has less than 2 historical data points
   - Action: Check if sensor exists, is recording, and wait for data to accumulate

3. **"Invalid sensor values: start=X, end=Y"**
   - When: Sensor reports non-numeric values like "unknown" or "unavailable"
   - Action: Check sensor state and integration providing the sensor

4. **"Exception during calculation: <error message>"**
   - When: Unexpected error occurs
   - Action: Check logs for full stack trace

### 3. Enhanced Logging
Upgraded diagnostic logging from DEBUG to WARNING level for failures, with specific checks to perform:

**Before:**
```python
_LOGGER.debug("No historical data available for baseline calculation (need at least 2 data points)")
```

**After:**
```python
_LOGGER.warning(
    "48h baseline: No historical data available for %s (need at least 2 data points, got %d). "
    "Check: (1) Sensor exists and reports values, (2) Recorder is enabled, "
    "(3) Recorder retention period >= %d hours",
    house_energy_ent, len(house_states), lookback_hours
)
```

### 4. Source Value Display
Modified `_update_baseline_and_runtime()` to always fetch and display the current energy counter value, even when calculation fails. This helps users verify:
- The sensor is accessible
- It's reporting numeric values
- The counter is incrementing

**Before failure:**
- `source_value`: `None` (no information)

**After failure:**
- `source_value`: `1234.5` (current counter value, helps verify sensor works)

### 5. Attribute Display
The `exclusion_reason` attribute (previously always empty) now displays the failure reason when calculation fails, making it immediately visible in the UI:

**When successful:**
- `exclusion_reason`: "" (empty, no issues)

**When failed:**
- `exclusion_reason`: "Insufficient historical data: 0 data points (need 2+)"

## User Impact

### Before
User sees attributes showing "Okänd" (Unknown) with no indication of what's wrong:
```
method: energy_counter_48h
source_value: Okänd
baseline_kwh_per_h: Okänd
exclusion_reason: (empty)
```

User must:
1. Enable debug logging
2. Restart Home Assistant
3. Wait for next update cycle
4. Search through debug logs
5. Try to interpret technical log messages

### After
User immediately sees the problem in the sensor attributes:
```
method: energy_counter_48h
source_value: 1234.5 (shows current counter value)
baseline_kwh_per_h: Okänd
exclusion_reason: Insufficient historical data: 0 data points (need 2+)
```

User can:
1. See the failure reason directly in the UI
2. Know exactly what to check (historical data)
3. Verify sensor is working (source_value shows current counter)
4. Consult DIAGNOSTIC_GUIDE.md for specific solutions

## Technical Changes

### Files Modified
1. **`custom_components/energy_dispatcher/coordinator.py`**
   - `_calculate_48h_baseline()`: Added failure_reason to return dict
   - `_update_baseline_and_runtime()`: Updated to use and store failure reason
   - Enhanced logging with specific diagnostic messages

2. **`CHANGELOG.md`**
   - Documented new diagnostic features

3. **`tests/test_48h_baseline.py`**
   - Updated existing tests to expect dict with failure_reason instead of None
   - Added new test for missing configuration
   - Added new test for invalid sensor values

### Files Added
1. **`DIAGNOSTIC_GUIDE.md`**
   - Complete user guide for troubleshooting
   - Explanation of each attribute
   - Common failure reasons and solutions
   - Step-by-step verification procedures

2. **`DIAGNOSTIC_FEATURE_SUMMARY.md`**
   - This file - technical summary of changes

## Benefits

1. **Self-Service Troubleshooting**: Users can diagnose and fix issues without developer assistance
2. **Faster Problem Resolution**: Immediate visibility of failure reason reduces time to resolution
3. **Better User Experience**: Clear, actionable error messages instead of generic "unknown"
4. **Easier Support**: Support requests can include specific failure reasons
5. **Reduced Log Noise**: Users don't need to enable debug logging for basic troubleshooting

## Backward Compatibility

✅ **Fully backward compatible**
- Existing working installations continue to work normally
- When calculation succeeds, `exclusion_reason` is empty (same as before)
- Only difference is when calculation fails - now shows helpful diagnostic instead of empty string
- No configuration changes required
- No breaking changes to sensor structure or attributes

## Testing

Added comprehensive tests covering:
- Missing configuration (no counter entity configured)
- No historical data (empty history from Recorder)
- Invalid sensor values (unknown/unavailable states)
- Successful calculation (unchanged behavior)

All tests verify that failure_reason is properly set and contains expected diagnostic message.
