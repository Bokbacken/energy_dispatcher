# Appliance Scheduling Implementation

## Overview
This document summarizes the implementation of the appliance scheduling feature for Energy Dispatcher, which suggests optimal times to run household appliances based on electricity prices and solar production forecasts.

## Implementation Date
2025-10-14

## Files Created

### Core Module
- **`custom_components/energy_dispatcher/appliance_optimizer.py`** (413 lines)
  - `ApplianceOptimizer` class with `optimize_schedule()` method
  - Finds optimal time windows for running appliances
  - Considers electricity prices, solar production, time constraints
  - Returns detailed recommendations with cost savings

### Sensors
- **`custom_components/energy_dispatcher/sensor_optimization.py`** (186 lines)
  - `DishwasherOptimalTimeSensor` - Shows optimal time to run dishwasher
  - `WashingMachineOptimalTimeSensor` - Shows optimal time to run washing machine
  - `WaterHeaterOptimalTimeSensor` - Shows optimal time to heat water
  - Each sensor provides:
    - Optimal start time (timestamp device class)
    - Estimated cost and savings
    - Reason for recommendation
    - Solar availability indicator
    - Alternative time suggestions
    - Confidence level

### Tests
- **`tests/test_appliance_optimizer.py`** (428 lines)
  - 17 comprehensive unit tests
  - Test coverage:
    - Basic optimization scenarios
    - Time constraint handling
    - Solar production integration
    - Edge cases (no data, invalid windows)
    - Cost calculations and scaling
    - Result attributes validation

## Files Modified

### Configuration
- **`custom_components/energy_dispatcher/const.py`**
  - Added 4 new configuration constants:
    - `CONF_ENABLE_APPLIANCE_OPTIMIZATION`
    - `CONF_DISHWASHER_POWER_W`
    - `CONF_WASHING_MACHINE_POWER_W`
    - `CONF_WATER_HEATER_POWER_W`

- **`custom_components/energy_dispatcher/config_flow.py`**
  - Added appliance optimization options to schema:
    - Enable/disable toggle (defaults to False)
    - Power consumption inputs for each appliance
    - Validation: 100-10000W range, 50W step

### Services
- **`custom_components/energy_dispatcher/services.yaml`**
  - Added `schedule_appliance` service definition:
    - Appliance type selector (dishwasher, washing_machine, water_heater)
    - Power consumption (100-10000W)
    - Duration (0.25-12 hours)
    - Optional time constraints (earliest_start, latest_end)

- **`custom_components/energy_dispatcher/__init__.py`**
  - Added `handle_schedule_appliance` service handler
  - Calls optimizer with current price and solar data
  - Stores recommendation in coordinator
  - Sends notification to user with results

### Coordinator Integration
- **`custom_components/energy_dispatcher/coordinator.py`**
  - Added `_update_appliance_recommendations()` method
  - Runs automatically every update cycle if enabled
  - Optimizes all three appliances using configured power values
  - Stores results in `coordinator.data["appliance_recommendations"]`

### Sensor Setup
- **`custom_components/energy_dispatcher/sensor.py`**
  - Conditionally adds appliance sensors when optimization is enabled
  - Imports sensors from `sensor_optimization.py`

### Translations
- **`custom_components/energy_dispatcher/translations/en.json`**
  - Added config field labels and descriptions
  - Added entity names for 3 sensors
  - Added service description and field labels

- **`custom_components/energy_dispatcher/translations/sv.json`**
  - Swedish translations for all new strings
  - Entity names, service descriptions, config fields

## Features

### Automatic Recommendations
When enabled in configuration, the system automatically:
- Analyzes next 24-36 hours of price forecasts
- Considers solar production forecasts if available
- Updates recommendations every coordinator cycle
- Exposes 3 sensors showing optimal times

### On-Demand Optimization
Users can call the `schedule_appliance` service to:
- Get recommendations for any appliance
- Specify custom power consumption and duration
- Set time constraints (earliest start, latest end)
- Receive notification with detailed results

### Smart Algorithm
The optimizer:
1. Finds all valid time windows based on constraints
2. Calculates net cost for each window (grid cost - solar offset)
3. Selects window with lowest cost
4. Compares to cost of running now
5. Provides savings estimate and reasoning

### Cost Awareness
- Accounts for time-varying electricity prices
- Offsets cost with solar production when available
- Shows savings vs running immediately
- Ranks alternative time windows

## Configuration Example

```yaml
# configuration.yaml (via UI)
energy_dispatcher:
  enable_appliance_optimization: true
  dishwasher_power_w: 1800
  washing_machine_power_w: 2000
  water_heater_power_w: 3000
```

## Service Usage Example

```yaml
# Call service to get recommendation
service: energy_dispatcher.schedule_appliance
data:
  appliance: dishwasher
  power_w: 1800
  duration_hours: 2
  earliest_start: "18:00"
  latest_end: "07:00"
```

## Sensor Attributes

Each optimization sensor provides:
- **State**: Optimal start time (ISO datetime)
- **Attributes**:
  - `estimated_cost_sek`: Expected cost in SEK
  - `cost_savings_vs_now_sek`: Savings compared to running now
  - `reason`: Human-readable explanation
  - `price_at_optimal_time`: Price (SEK/kWh) at optimal time
  - `current_price`: Current electricity price (SEK/kWh)
  - `solar_available`: Boolean indicating solar availability
  - `alternative_times`: List of up to 3 other good times
  - `confidence`: Confidence level (low/medium/high)

## Testing

All 17 unit tests pass:
- Basic optimization scenarios ✓
- Time constraint handling ✓
- Solar integration ✓
- Edge case handling ✓
- Cost calculations ✓
- Result validation ✓

No existing tests were broken by the implementation.

## Future Enhancements

Potential improvements for future versions:
1. Add more appliance types (dryer, pool pump, etc.)
2. Support for variable-rate tariffs (Tibber dynamic pricing)
3. Weather-aware optimization (postpone if rain expected)
4. Integration with smart home automation
5. Learning from user patterns
6. Multi-appliance coordination

## Documentation References

- Technical specification: `docs/ai_optimization_implementation_guide.md`
- Implementation plan: `docs/IMPLEMENTATION_STEPS.md`
- This implementation: Lines 1-500 from implementation guide

## Notes

- Sensors only created when `enable_appliance_optimization` is true
- Default appliance durations: dishwasher 2h, washing machine 1.5h, water heater 3h
- Optimization runs every coordinator update cycle (typically 5-15 minutes)
- Service can be called at any time for on-demand recommendations
- All user-facing strings are translated to EN and SV
