# House Load Baseline Fix - Version 0.8.27

## Summary
Fixed two critical issues with the House Load Baseline calculation:
1. All daypart sensors (Night, Day, Evening) were showing the same value
2. Exclusion settings for EV charging and Battery grid charging appeared to have no effect

## What Changed

### Before
- The baseline calculation simply assigned the overall 48-hour average to all dayparts
- This meant Night, Day, and Evening baselines were identical
- Users couldn't see the actual consumption patterns throughout the day

### After
- The baseline calculation now processes hourly data to calculate separate averages for each daypart:
  - **Night** (00:00-07:59): Typically lower consumption
  - **Day** (08:00-15:59): Medium consumption
  - **Evening** (16:00-23:59): Usually higher consumption (more activity, cooking, etc.)
- EV charging and battery grid charging exclusions now work correctly on a per-hour basis

## Technical Details

### New Calculation Method
The `_calculate_daypart_baselines()` method:
1. Builds hourly indexes from historical energy counter data
2. Calculates consumption for each consecutive hour pair
3. Applies EV and battery exclusions on a per-hour basis
4. Groups hours by daypart classification
5. Calculates average consumption rate for each daypart

### Exclusions
- **EV Charging Exclusion**: Subtracts EV energy counter delta from house consumption for each hour
- **Battery Grid Charging Exclusion**: Estimates grid charging as (battery charged - PV generated) and subtracts it from house consumption

## Example Results

Using real sample data (138 hours):

| Daypart | Without Exclusions | With Exclusions | Reduction |
|---------|-------------------|-----------------|-----------|
| Night   | 1.099 kWh/h       | 1.097 kWh/h     | 0.2%      |
| Day     | 1.000 kWh/h       | 0.913 kWh/h     | 8.8%      |
| Evening | 1.972 kWh/h       | 1.208 kWh/h     | 38.7%     |
| Overall | 1.333 kWh/h       | 1.068 kWh/h     | 19.9%     |

**Key Observations:**
- Evening consumption is significantly higher (1.972 kWh/h vs 1.099 kWh/h for night)
- Exclusions have the biggest impact in the evening (38.7% reduction)
- This makes sense as battery charging and EV charging typically occur in the evening

## Sensors Affected

The following sensors now show accurate, differentiated values:
- `sensor.energy_dispatcher_baseline_night_w` - Night baseline (00:00-07:59)
- `sensor.energy_dispatcher_baseline_day_w` - Day baseline (08:00-15:59)
- `sensor.energy_dispatcher_baseline_evening_w` - Evening baseline (16:00-23:59)
- `sensor.energy_dispatcher_house_baseline_w` - Overall average baseline (Now)

## Configuration

No configuration changes are required. The fix automatically applies when:
- `runtime_use_dayparts` is enabled (default: true)
- `runtime_counter_entity` is configured
- At least 48 hours of historical data is available

### Exclusion Settings
To enable exclusions, configure:
- `runtime_exclude_ev: true` + `evse_total_energy_sensor` (for EV exclusion)
- `runtime_exclude_batt_grid: true` + `batt_total_charged_energy_entity` + `pv_total_energy_entity` (for battery exclusion)

## Compatibility

- No breaking changes
- Existing configurations continue to work
- Falls back to overall average if daypart calculation fails (e.g., insufficient hourly data)

## Testing

- 5 new unit tests covering daypart calculations
- All existing passing tests continue to pass
- Validated with real sample data (138 hours of actual sensor data)

## Version
- **Previous**: 0.8.26
- **Current**: 0.8.27
