# Missing Data Handling

## Overview

The Energy Dispatcher integration handles missing or unavailable sensor data gracefully by implementing interpolation, extrapolation, and staleness detection. This ensures that temporary sensor unavailability doesn't cause incorrect calculations or loss of tracking.

## Key Features

### 1. Linear Interpolation

When historical data has gaps (e.g., a sensor was unavailable for a period), the system can interpolate values between known data points.

**How it works:**
- Detects gaps in hourly historical data
- For gaps within acceptable limits, calculates intermediate values using linear interpolation
- Preserves all originally logged values
- Only interpolates between consecutive known points

**Example:**
```
Original data:
  10:00 → 100 kWh
  13:00 → 115 kWh (missing 11:00 and 12:00)

After interpolation:
  10:00 → 100 kWh (original)
  11:00 → 105 kWh (interpolated)
  12:00 → 110 kWh (interpolated)
  13:00 → 115 kWh (original)
```

### 2. Gap Limits

Different components have different maximum acceptable gap sizes:

#### Baseline Calculation
- **Maximum gap: 8 hours**
- If gap exceeds 8 hours, those periods are excluded from calculation
- Prevents inaccurate baseline from long unavailable periods

#### BEC (Battery Energy Cost) Tracking
- **Maximum gap: 1 hour**
- If data is unavailable for > 1 hour, tracking resets
- Prevents incorrect charge/discharge deltas from accumulated errors

### 3. Staleness Detection

The system waits a reasonable time for data before assuming it's unavailable.

- **Wait time: 15 minutes**
- If a sensor has been unavailable for < 15 minutes, the system continues waiting
- After 15 minutes, the sensor is considered unavailable
- This prevents false alarms from temporary connectivity issues

### 4. Counter Reset Handling

Energy counters sometimes reset (e.g., daily counters at midnight):
- Interpolation is **not** performed across counter resets
- Negative deltas indicate a reset and are handled specially
- System uses the end value as approximation after reset

## Implementation Details

### Interpolation Function

```python
def _interpolate_energy_value(
    timestamp: datetime,
    prev_time: datetime,
    prev_value: float,
    next_time: datetime,
    next_value: float,
) -> Optional[float]:
    """
    Linearly interpolate energy counter value at a given timestamp.
    
    Returns None if:
    - Timestamp outside the range [prev_time, next_time]
    - Counter reset detected (next_value < prev_value)
    - Invalid time range (prev_time >= next_time)
    """
```

### Gap Filling Function

```python
def _fill_missing_hourly_data(
    time_index: Dict[datetime, float],
    max_gap_hours: float = 8.0
) -> Dict[datetime, float]:
    """
    Fill missing hourly data points using linear interpolation.
    
    - Only fills gaps up to max_gap_hours
    - Preserves all original values
    - Returns new dictionary with interpolated values added
    """
```

### Staleness Detection

```python
def _is_data_stale(
    last_update: Optional[datetime],
    max_age_minutes: int = 15
) -> bool:
    """
    Check if data is too old to be considered valid.
    
    Returns True if:
    - last_update is None
    - Age exceeds max_age_minutes
    """
```

## Use Cases

### Use Case 1: Temporary Sensor Unavailability

**Scenario:** House energy sensor goes offline for 3 hours due to network issue.

**Without interpolation:**
- Daypart baseline calculation would skip those hours
- Less accurate baseline due to missing data

**With interpolation:**
- Missing hours are filled using linear interpolation
- Baseline calculation uses complete dataset
- More accurate results

### Use Case 2: BEC Tracking During Outage

**Scenario:** Battery energy sensor unavailable for 90 minutes.

**Without gap detection:**
- Next reading would calculate incorrect delta
- WACE (Weighted Average Cost of Energy) would be wrong

**With gap detection:**
- After 1 hour, tracking resets
- Next reading starts fresh
- No incorrect deltas accumulated

### Use Case 3: Brief Connectivity Glitch

**Scenario:** Sensor unavailable for 5 minutes due to WiFi glitch.

**Without staleness detection:**
- System might immediately treat data as unavailable
- Unnecessary warnings and data loss

**With staleness detection:**
- System waits 15 minutes before giving up
- Brief glitches don't affect tracking
- More robust operation

## Configuration

The gap limits and staleness timeouts are built into the code with sensible defaults:

- **Baseline max gap:** 8 hours (hardcoded)
- **BEC max gap:** 1 hour (hardcoded)
- **Staleness timeout:** 15 minutes (hardcoded)

These values were chosen based on typical energy monitoring patterns:
- 15 minutes: Normal logging interval for energy systems
- 1 hour: Reasonable window for accurate battery charge/discharge tracking
- 8 hours: Balance between data recovery and preventing stale baseline

## Logging

The system logs information about missing data handling:

### Interpolation Messages
```
INFO: Daypart baseline: Interpolated 5 missing hourly data points (max gap: 8.0 hours)
```

### Gap Detection Messages
```
WARNING: BEC: Data gap of 65.2 minutes exceeds 1 hour limit. Resetting tracking to avoid incorrect deltas.
```

### Staleness Messages
```
DEBUG: BEC: Charged energy sensor sensor.battery_charged unavailable for > 15 minutes, treating as no data
```

## Benefits

### 1. Robustness
- Handles temporary sensor unavailability gracefully
- Prevents cascading errors from missing data
- Continues operation even with intermittent connectivity

### 2. Accuracy
- Interpolation provides better estimates than ignoring gaps
- Gap limits prevent using stale or incorrect data
- Staleness detection avoids false positives

### 3. Reliability
- BEC tracking protected from incorrect deltas
- Baseline calculation more complete
- Reduces "unknown" states in sensors

## Limitations

### Cannot Interpolate Across Counter Resets
- Daily energy counters that reset at midnight
- Counter overflows or manual resets
- These periods are excluded from interpolation

### Maximum Gap Limits
- Gaps larger than 8 hours (baseline) or 1 hour (BEC) are not filled
- Very long outages still result in missing data
- This is intentional to prevent using very stale estimates

### Linear Assumption
- Interpolation assumes constant energy consumption rate
- Actual consumption may vary
- Acceptable for gaps up to a few hours, less accurate for longer gaps

## Technical Notes

### Performance
- Interpolation is done in-memory on historical query results
- Minimal performance impact (< 1ms for typical 48-hour dataset)
- No additional database queries needed

### Thread Safety
- All time tracking uses Home Assistant's async executor
- No race conditions in update cycle
- Safe for concurrent sensor updates

### Storage
- Interpolated values are not stored
- Recalculated on each coordinator update
- No additional storage overhead

## Troubleshooting

### Baseline Shows Unusual Values After Outage

**Check:**
1. How long was the outage?
2. Was it > 8 hours (baseline max gap)?
3. Check logs for interpolation messages

**Solution:**
- If gap was too large, wait for new data to accumulate
- Baseline will normalize after 48 hours of good data

### BEC Tracking Reset Unexpectedly

**Check:**
1. Check logs for gap detection messages
2. Was sensor unavailable for > 1 hour?
3. Look for "Data gap exceeds 1 hour" warnings

**Solution:**
- Improve sensor reliability (better network, restart sensor)
- Gap detection is working as designed to prevent incorrect deltas

### Interpolated Values Don't Match Reality

**Check:**
1. Was consumption pattern unusual during the gap?
2. Large spikes or drops are not captured by linear interpolation

**Remember:**
- Interpolation assumes constant rate
- Cannot predict unusual consumption
- Trade-off between missing data and approximate data

## Future Enhancements

Possible improvements for future versions:

1. **Configurable gap limits:** Allow users to set custom limits via options
2. **Smart extrapolation:** Use recent trends when no future point available
3. **Non-linear interpolation:** Account for known patterns (e.g., time-of-day)
4. **Confidence intervals:** Indicate reliability of interpolated values
5. **Alternative strategies:** Median, exponential smoothing, etc.

## References

- See `coordinator.py` for implementation details
- See `test_missing_data_handling.py` for test coverage
- See `48h_baseline_feature.md` for baseline calculation overview
