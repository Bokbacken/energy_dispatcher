# Simplified 48-Hour Baseline Using Energy Counters

## Overview

This feature calculates house load baseline using energy counter deltas over the last 48 hours. It provides more accurate and fail-safe battery runtime estimates by using cumulative energy readings (kWh) instead of instantaneous power samples.

## Key Features

### 1. Energy Counter-Based Calculation
- Uses energy counters (kWh) with delta values over 48 hours (configurable)
- Missing data points don't matter - only start and end values are needed
- More robust than power-based sampling which requires continuous data
- Simple and reliable approach

### 2. Time-of-Day Weighting (Optional)
When enabled, provides separate baseline estimates for three distinct time periods:

- **Night** (00:00-07:59): Typically lowest consumption (sleep hours)
- **Day** (08:00-15:59): Daytime household activity
- **Evening** (16:00-23:59): Peak hours (cooking, entertainment, etc.)

Note: Currently distributes the overall average evenly across time periods.

### 3. Intelligent Exclusions via Energy Counters
The system automatically excludes consumption from controllable loads:

- **EV Charging**: Subtracts energy charged to EV (from EV energy counter)
- **Battery Grid Charging**: Subtracts battery charging from grid (battery charged - PV generated)

This ensures the baseline reflects only "normal" household consumption.

## Configuration

### Required Configuration

#### `runtime_counter_entity`
- **Type**: Entity ID
- **Required**: Yes
- **Description**: Total house load energy counter (kWh)
- **Example**: `sensor.house_total_energy`

### Optional Configuration

#### `evse_total_energy_sensor`
- **Type**: Entity ID
- **Optional**: Yes
- **Description**: Total EV charging energy counter (kWh)
- **Example**: `sensor.ev_total_energy`
- **Used For**: Excluding EV charging from baseline

#### `batt_total_charged_energy_entity`
- **Type**: Entity ID
- **Optional**: Yes
- **Description**: Total battery charged energy counter (kWh)
- **Example**: `sensor.battery_total_charged`
- **Used For**: Excluding battery grid charging from baseline

#### `pv_total_energy_entity`
- **Type**: Entity ID
- **Optional**: Yes
- **Description**: Total PV generation energy counter (kWh)
- **Example**: `sensor.pv_total_generation`
- **Used For**: Calculating battery charging from PV vs grid

### Calculation Options

#### `runtime_lookback_hours`
- **Type**: Integer (1-168)
- **Default**: 48
- **Description**: Number of hours to look back for calculating baseline
- **Note**: Larger values smooth out variations but reduce responsiveness

#### `runtime_use_dayparts`
- **Type**: Boolean
- **Default**: True
- **Description**: Enable time-of-day specific baseline estimates
- **Effect**: Provides separate estimates for night/day/evening periods

#### `runtime_exclude_ev`
- **Type**: Boolean
- **Default**: True
- **Description**: Exclude EV charging energy from baseline
- **Requires**: `evse_total_energy_sensor` to be configured

#### `runtime_exclude_batt_grid`
- **Type**: Boolean
- **Default**: True
- **Description**: Exclude battery grid charging energy from baseline
- **Requires**: `batt_total_charged_energy_entity` and `pv_total_energy_entity` to be configured

## New Sensors

### House Load Baseline Now
- **Entity**: `sensor.house_load_baseline_now`
- **Unit**: W (Watts)
- **Description**: Current time-of-day baseline calculated from energy counter deltas
- **Behavior**:
  - When dayparts enabled (`runtime_use_dayparts: true`): Shows baseline for current time period (night/day/evening)
  - When dayparts disabled: Shows overall 48-hour average
  - Falls back to overall if current daypart unavailable
- **Attributes**:
  - `method`: Shows `energy_counter_48h` for the simplified calculation
  - `baseline_kwh_per_h`: Baseline in kWh/h
  - `source_value`: Current house energy counter value (kWh)

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

1. **Historical Fetch**: Queries Recorder for energy counter values at start and end of lookback period
2. **Delta Calculation**: Calculates energy consumed: `end_value - start_value`
3. **Counter Reset Handling**: If delta is negative (counter reset), uses end value as approximation
4. **Exclusion Calculation**: Subtracts EV and battery grid charging energy from total
5. **Average Calculation**: Divides net consumption by lookback hours to get kWh/h
6. **Clipping**: Ensures values are within reasonable range (0.05-5.0 kWh/h)

### Calculation Formula

```python
# Get energy counter deltas
house_delta = house_end - house_start
ev_delta = ev_end - ev_start (if configured)
batt_delta = batt_end - batt_start (if configured)
pv_delta = pv_end - pv_start (if configured)

# Calculate net house consumption
net_house_kwh = house_delta
if exclude_ev:
    net_house_kwh -= ev_delta
if exclude_batt_grid:
    batt_grid_kwh = max(0, batt_delta - pv_delta)
    net_house_kwh -= batt_grid_kwh

# Calculate average rate
baseline_kwh_per_h = net_house_kwh / lookback_hours
```

### Exclusion Logic

#### EV Charging Exclusion
```python
# Subtract total EV energy charged over the period
net_consumption -= ev_total_energy_delta
```

#### Battery Grid Charging Exclusion
```python
# Estimate grid charging: battery charged minus PV generated
battery_grid_charge = max(0, battery_charged - pv_generated)
net_consumption -= battery_grid_charge
```

### Robustness Features

- **Missing Data**: Only needs 2 data points (start and end), not continuous sampling
- **Counter Resets**: Automatically handles daily/monthly counter resets
- **No EMA Fallback**: Simple calculation always works if counters exist
- **Fail-Safe**: Returns None if insufficient data, system continues operating

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
runtime_counter_entity: sensor.house_total_energy
evse_total_energy_sensor: sensor.ev_total_energy
batt_total_charged_energy_entity: sensor.battery_total_charged
pv_total_energy_entity: sensor.pv_total_generation
runtime_lookback_hours: 48
runtime_use_dayparts: true
runtime_exclude_ev: true
runtime_exclude_batt_grid: true
```

### Example Calculation
Given these counter values over 48 hours:
- House energy: 1000 kWh → 1058 kWh (58 kWh consumed)
- EV energy: 500 kWh → 510 kWh (10 kWh charged)
- Battery charged: 200 kWh → 210 kWh (10 kWh charged)
- PV generated: 300 kWh → 305 kWh (5 kWh generated)

Calculation:
```
Net house = 58 kWh (total house consumption)
          - 10 kWh (EV charging)
          - 5 kWh (battery grid charging: 10 charged - 5 from PV)
          = 43 kWh over 48 hours
          = 0.896 kWh/h average
          ≈ 896W baseline
```

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

### Baseline shows as "unknown"
- Check that `runtime_counter_entity` is configured
- Verify energy counter sensor exists and is reporting values
- Check that sensor has at least 2 historical data points (start and end of period)
- Check Home Assistant logs for detailed error messages

### Historical calculation not working
- Ensure Recorder integration is enabled
- Verify energy counter sensor is being recorded (check recorder configuration)
- Check that lookback period doesn't exceed your recorder retention period
- Verify counter values are numeric (not "unknown" or "unavailable")

### Exclusions not working correctly
- Verify optional energy counter sensors are configured correctly
- Check that EV and battery energy sensors are cumulative counters (always increasing)
- Verify PV generation sensor is also a cumulative counter
- Check sensor units are in kWh (not Wh or MWh)

### Counter reset issues
- System automatically handles counter resets by using end value
- If resets happen frequently, baseline may be less accurate
- Consider using counters that don't reset, or use longer lookback periods

## Performance Considerations

- Historical queries run every 5 minutes (coordinator update interval)
- Only fetches 2 data points per sensor (start and end of period)
- Very lightweight compared to power-based sampling
- Minimal impact on system performance and database

## Advantages Over Power-Based Sampling

1. **Robustness**: Missing data points don't affect calculation
2. **Simplicity**: Only needs start and end values
3. **Accuracy**: Uses actual energy consumed, not estimated from power
4. **Efficiency**: Minimal database queries
5. **Reliability**: No dependency on continuous power sensor readings

## Migration from Power-Based Method

If you were previously using `runtime_source: power_w`:
1. Configure `runtime_counter_entity` with your house energy counter
2. Optionally configure EV, battery, and PV energy counters for exclusions
3. The system will automatically use the new energy counter method
4. Remove `runtime_power_entity`, `load_power_entity`, and `batt_power_entity` (no longer used)
