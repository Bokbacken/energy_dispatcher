# 48-Hour Baseline with Time-of-Day Weighting

## Overview

This feature enhances the house load baseline calculation by using historical data from the last 48 hours instead of a simple exponential moving average (EMA). It provides more accurate and realistic battery runtime estimates by analyzing actual consumption patterns across different times of day.

## Key Features

### 1. Historical Data Analysis
- Analyzes power consumption data from the last 48 hours (configurable)
- Uses Home Assistant's Recorder database for historical lookback
- More realistic than EMA which can be too reactive to short-term changes

### 2. Time-of-Day Weighting
When enabled, calculates separate baselines for three distinct time periods:

- **Night** (00:00-07:59): Typically lowest consumption (sleep hours)
- **Day** (08:00-15:59): Daytime household activity
- **Evening** (16:00-23:59): Peak hours (cooking, entertainment, etc.)

This provides more accurate battery runtime estimates based on the current time of day.

### 3. Intelligent Exclusions
The system automatically excludes from baseline calculations:

- **EV Charging**: Removes periods when EV was charging (> 100W)
- **Battery Grid Charging**: Removes periods when battery was charging from grid (> 100W surplus beyond PV)

This ensures the baseline reflects only "normal" household consumption.

## Configuration

### Configuration Options

#### `runtime_lookback_hours`
- **Type**: Integer (0-168)
- **Default**: 48
- **Description**: Number of hours to look back for calculating baseline
- **Special**: Set to 0 to disable and use traditional EMA instead

#### `runtime_use_dayparts`
- **Type**: Boolean
- **Default**: True
- **Description**: Enable time-of-day specific baseline calculations
- **Effect**: Creates separate baselines for night/day/evening periods

### Backward Compatibility

The feature is designed to be fully backward compatible:

1. **Default Behavior**: New installations use 48-hour lookback by default
2. **Legacy Support**: Setting `runtime_lookback_hours: 0` reverts to EMA mode
3. **Counter Method**: The `counter_kwh` method continues to work as before
4. **Existing Configs**: Existing configurations work without changes

## New Sensors

### House Load Baseline Now
- **Entity**: `sensor.house_load_baseline_now`
- **Unit**: W (Watts)
- **Description**: Overall baseline (48h average or current time-of-day specific)
- **Attributes**:
  - `method`: Shows `power_w_48h` when using historical calculation
  - `baseline_kwh_per_h`: Baseline in kWh/h

### House Load Baseline Night
- **Entity**: `sensor.house_load_baseline_night`
- **Unit**: W (Watts)
- **Description**: Average consumption during night hours (00:00-07:59)
- **Available**: Only when `runtime_lookback_hours > 0`

### House Load Baseline Day
- **Entity**: `sensor.house_load_baseline_day`
- **Unit**: W (Watts)
- **Description**: Average consumption during day hours (08:00-15:59)
- **Available**: Only when `runtime_lookback_hours > 0`

### House Load Baseline Evening
- **Entity**: `sensor.house_load_baseline_evening`
- **Unit**: W (Watts)
- **Description**: Average consumption during evening hours (16:00-23:59)
- **Available**: Only when `runtime_lookback_hours > 0`

## Technical Implementation

### Data Flow

1. **Historical Fetch**: Queries Recorder for power sensor data over lookback period
2. **Sample Collection**: Collects all valid power readings with timestamps
3. **Exclusion Check**: For each sample, checks if EV or battery grid charging was active
4. **Time Classification**: Classifies each sample into night/day/evening based on hour
5. **Average Calculation**: Calculates average for each period and overall
6. **Clipping**: Ensures values are within reasonable range (0.05-5.0 kWh/h)

### Exclusion Logic

#### EV Charging Exclusion
```python
if ev_power > 100W:
    # Exclude this sample from baseline
```

#### Battery Grid Charging Exclusion
```python
if battery_power > 0:  # Charging
    pv_surplus = max(0, pv_power - house_load)
    grid_charge = max(0, battery_power - pv_surplus)
    if grid_charge > 100W:
        # Exclude this sample from baseline
```

### Fallback Mechanism

If historical calculation fails:
1. Logs debug message
2. Falls back to traditional EMA calculation
3. Ensures system continues to function

## Benefits

### More Accurate Runtime Estimates
- Battery runtime calculations based on actual consumption patterns
- Time-of-day awareness provides better estimates at different hours
- 48-hour window smooths out daily variations

### Better Decision Making
- More realistic understanding of house baseline
- Helps identify unusual consumption patterns
- Supports better battery and EV charging scheduling

### Excludes Controllable Loads
- Baseline reflects only "passive" household consumption
- EV and battery charging don't artificially inflate baseline
- More accurate for calculating what battery needs to cover

## Example Usage

### Typical Configuration
```yaml
runtime_source: power_w
runtime_power_entity: sensor.house_power
runtime_lookback_hours: 48
runtime_use_dayparts: true
runtime_exclude_ev: true
runtime_exclude_batt_grid: true
```

### Example Output
With this configuration, you might see:
- Overall baseline: 850W
- Night baseline: 450W
- Day baseline: 800W
- Evening baseline: 1200W

These values help the system:
1. Calculate battery runtime more accurately
2. Understand consumption patterns
3. Make better charging decisions

### Battery Runtime Precision

Battery runtime estimates are rounded to appropriate precision to avoid false accuracy:
- **>= 2 hours**: Rounded to 15-minute intervals (e.g., 5.75h, 3.25h, 2.50h)
- **< 2 hours**: Rounded to 5-minute intervals (e.g., 1.83h, 1.42h, 0.75h)

This provides a realistic estimate without suggesting more precision than the calculation can provide.

## Troubleshooting

### Baseline shows as "unavailable"
- Check that `runtime_power_entity` is configured
- Verify sensor has sufficient historical data (needs at least a few hours)
- Check Home Assistant logs for errors

### Historical calculation not working
- Ensure Recorder integration is enabled
- Verify power sensor is being recorded
- Check that lookback period doesn't exceed your retention period
- System will fall back to EMA if historical fetch fails

### Exclusions not working
- Verify EV and battery power sensors are configured
- Check sensor values are being reported correctly
- Ensure sign convention is correct (use `batt_power_invert_sign` if needed)

## Performance Considerations

- Historical queries run every 5 minutes (coordinator update interval)
- Queries are optimized to fetch only needed entities
- Results are cached between updates
- Minimal impact on system performance

## Future Enhancements

Potential future improvements:
- Configurable time period boundaries
- Custom weighting factors for different periods
- Integration with weather forecasts
- Machine learning for pattern recognition
- Seasonal adjustments
