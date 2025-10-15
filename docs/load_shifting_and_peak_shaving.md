# Load Shifting and Peak Shaving Implementation

## Overview

This document describes the implementation of load shifting recommendations and peak shaving features in the Energy Dispatcher integration.

## Load Shifting

### Purpose
The load shifting optimizer identifies opportunities to shift flexible loads (consumption above baseline) to cheaper time periods, helping to minimize electricity costs.

### Configuration

**Enable Load Shifting**: `enable_load_shifting` (boolean, default: False)
- Activates the load shifting recommendation sensors

**Flexibility Window**: `load_shift_flexibility_hours` (hours, default: 6)
- How many hours ahead the system can suggest shifting loads
- Range: 1-24 hours

**Baseline Load**: `baseline_load_w` (watts, default: 300)
- Always-on baseline load in watts
- Loads above this are considered flexible and shiftable
- Range: 0-5000W

### Sensors

#### Load Shift Opportunity
**Entity ID**: `sensor.energy_dispatcher_load_shift_opportunity`

Shows the best load shifting opportunity with a text description like "Shift to 02:00".

**Attributes**:
- `shift_to_time`: ISO datetime of recommended shift time
- `savings_per_hour_sek`: Potential savings per hour in SEK
- `price_now`: Current electricity price (SEK/kWh)
- `price_then`: Price at recommended time (SEK/kWh)
- `flexible_load_w`: Current flexible load in watts
- `user_impact`: Impact assessment ("low" or "medium")
- `all_opportunities_count`: Total number of opportunities found

#### Load Shift Savings Potential
**Entity ID**: `sensor.energy_dispatcher_load_shift_savings`

Shows the potential savings from the best opportunity in SEK per hour.

**Attributes**:
- `best_opportunity_savings`: Savings from best opportunity (SEK/h)
- `total_potential_savings`: Sum of all opportunities (SEK/h)
- `opportunities_count`: Number of opportunities found
- `price_difference`: Price difference between now and best time (SEK/kWh)

### How It Works

1. **Identify Flexible Load**: Calculates current consumption minus baseline load
2. **Find Cheaper Windows**: Searches for cheaper price periods within the flexibility window
3. **Calculate Savings**: Computes potential savings for each shift opportunity
4. **Assess Impact**: Evaluates user impact based on time of day:
   - Night (0-6h): Low impact
   - Morning/Evening peaks (7-9h, 17-22h): Medium impact
   - Midday (10-16h): Low impact
5. **Sort by Savings**: Returns recommendations sorted by highest savings first

### Requirements

- Flexible load must be ≥ 500W to trigger recommendations
- Price difference must be ≥ 0.5 SEK/kWh to suggest a shift
- Requires configured `load_power_entity` sensor

---

## Peak Shaving

### Purpose
Peak shaving uses battery discharge to cap grid import power when it exceeds a threshold, helping to reduce demand charges and grid strain.

### Configuration

**Enable Peak Shaving**: `enable_peak_shaving` (boolean, default: False)
- Activates peak shaving functionality

**Peak Threshold**: `peak_threshold_w` (watts, default: 10000)
- Grid import power threshold that triggers battery discharge
- Range: 1000-50000W

### How It Works

1. **Monitor Grid Import**: Continuously monitors current grid import power
2. **Check Threshold**: Compares grid import against configured threshold
3. **Battery Availability**: Ensures battery SOC is above reserve level
4. **Calculate Discharge**: Determines discharge power needed to cap the peak
5. **Duration Check**: Verifies battery can sustain discharge for at least 30 minutes
6. **Execute**: Discharges battery to reduce grid import to threshold level

### Peak Shaving Action Data

The coordinator provides peak shaving action data in `coordinator.data["peak_shaving_action"]`:

```python
{
    "discharge_battery": bool,      # True if discharge is recommended
    "discharge_power_w": int,       # Discharge power in watts
    "duration_estimate_h": float,   # How long discharge can be sustained
    "peak_reduction_w": int,        # Amount of peak reduction in watts
    "reason": str,                  # Human-readable explanation
}
```

### Safety Features

- **Reserve Protection**: Will not discharge below battery reserve SOC (default: 20%)
- **Minimum Duration**: Requires at least 30 minutes of discharge capability
- **Minimum Power**: Only activates for excess ≥ 500W
- **Battery Limits**: Respects max discharge power configuration

### Requirements

- Requires configured `load_power_entity` sensor for grid import monitoring
- Requires battery SOC sensor
- Battery must have sufficient charge above reserve level

---

## Integration with Coordinator

Both features are integrated into the coordinator's update cycle:

1. **Load Shifting**: `_update_load_shift_recommendations()` - Called on each coordinator update
2. **Peak Shaving**: `_update_peak_shaving_status()` - Called on each coordinator update

The coordinator automatically:
- Checks if features are enabled in configuration
- Validates required sensor data is available
- Calls optimizers with current state
- Updates sensor values via coordinator data
- Logs warnings if optimization fails

---

## Testing

### Load Shift Optimizer Tests
**File**: `tests/test_load_shift_optimizer.py`

- 9 test cases covering:
  - Basic recommendation generation
  - Below-threshold filtering
  - Sorting by savings
  - Flexibility window constraints
  - User impact assessment
  - Savings calculation accuracy
  - Edge cases (no prices, no current price)
  - Minimum savings threshold

### Peak Shaving Tests
**File**: `tests/test_peak_shaving.py`

- 13 test cases covering:
  - Within threshold (no action)
  - Exceeding threshold (discharge)
  - Reserve SOC protection
  - Battery max discharge limits
  - Duration calculation
  - Insufficient duration handling
  - Minimum power threshold
  - Edge cases and result structure

All tests pass successfully.

---

## Example Usage

### Dashboard Card - Load Shifting
```yaml
type: entities
title: Load Shifting Opportunities
entities:
  - entity: sensor.energy_dispatcher_load_shift_opportunity
    name: Best Opportunity
  - entity: sensor.energy_dispatcher_load_shift_savings
    name: Potential Savings
    icon: mdi:piggy-bank
```

### Automation - Peak Shaving Alert
```yaml
automation:
  - alias: "Peak Shaving Active Alert"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('sensor.energy_dispatcher_coordinator', 
             'peak_shaving_action')['discharge_battery'] == true }}
    action:
      - service: notify.mobile_app
        data:
          message: >
            Peak shaving active: 
            {{ state_attr('sensor.energy_dispatcher_coordinator', 
               'peak_shaving_action')['reason'] }}
```

---

## Translation Support

Full translation support provided in English and Swedish:
- Configuration flow labels and descriptions
- Sensor entity names
- All user-facing text

---

## Future Enhancements

Potential improvements for future releases:
- Dashboard cards with visualization
- Automation templates for load shifting notifications
- Integration with specific appliance entities
- Historical savings tracking
- Peak shaving statistics and reporting
- Configurable user impact preferences
- Integration with demand response programs
