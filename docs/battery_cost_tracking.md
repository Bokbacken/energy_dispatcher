# Battery Cost Tracking (BEC Module)

## Overview

The Battery Energy Cost (BEC) module tracks the weighted average cost of energy (WACE) stored in your home battery. This helps you understand the true cost of the energy currently in your battery and make informed decisions about when to charge and discharge.

## Features

### Automatic Cost Tracking
- **Weighted Average Cost of Energy (WACE)**: Automatically calculates the average cost per kWh based on all charging events
- **Historical Data Storage**: Records every charging/discharging event with timestamp (15-minute intervals)
- **Persistent Storage**: State and historical data saved across Home Assistant restarts
- **Real-time Updates**: Updates automatically as battery charges and discharges
- **Data Retention**: Keeps 30 days of historical data (2,880 15-minute intervals)

### Manual Overrides
- **Manual SOC Setting**: Override the battery state of charge if sensor readings are incorrect
- **Cost Reset**: Reset cost tracking to start fresh (useful after pricing changes)
- **WACE Recalculation**: Ability to recalculate WACE from historical data

### Historical Data
- **Event Tracking**: Records every charge, discharge, and manual override
- **Source Tracking**: Distinguishes between grid and solar charging
- **Timestamp Records**: Each event includes ISO timestamp for precise tracking
- **History Summary**: Provides aggregate statistics (total charged, discharged, events)

## Configuration

### Automatic Charge/Discharge Tracking

Energy Dispatcher can automatically track battery charging and discharging using daily energy sensors. This eliminates the need for manual tracking and ensures accurate cost calculations.

#### Required Sensors

To enable automatic tracking, configure these sensor entities in the integration settings:

1. **Battery Energy Charged Today** (`batt_energy_charged_today_entity`)
   - Reports daily energy charged to battery (kWh)
   - Must reset to 0 at midnight
   - Example: `sensor.energy_charged_today`

2. **Battery Energy Discharged Today** (`batt_energy_discharged_today_entity`)
   - Reports daily energy discharged from battery (kWh)
   - Must reset to 0 at midnight
   - Example: `sensor.energy_discharged_today`

#### Optional: Automatic Capacity Detection

You can optionally configure a sensor that reports your battery's rated capacity:

- **Battery Capacity Sensor** (`batt_capacity_entity`)
  - Reports battery rated capacity (kWh)
  - Example: `sensor.rated_ess_capacity`
  - When configured, overrides the manual capacity setting
  - Useful for systems where capacity is dynamically reported

#### How Automatic Tracking Works

1. **Every 5 minutes** (coordinator update interval), the system reads the daily energy counters
2. **Calculates deltas** by comparing current values with previous readings
3. **Determines energy source**:
   - If PV surplus covers charging power → cost is 0 (solar)
   - Otherwise → uses current electricity price (grid)
4. **Calls BEC methods**:
   - `bec.on_charge(delta_kwh, cost, source)` for charging
   - `bec.on_discharge(delta_kwh)` for discharging
5. **Daily reset**: Automatically handles sensor resets at midnight

#### Example EMMA/Huawei Sensors

For Huawei LUNA2000 systems (EMMA), use these sensors:

```yaml
batt_energy_charged_today_entity: sensor.luna2000_energy_charged_today
batt_energy_discharged_today_entity: sensor.luna2000_energy_discharged_today
batt_capacity_entity: sensor.luna2000_rated_ess_capacity
```

## How It Works

### Charging
When energy is added to the battery, the WACE is recalculated using a weighted average:

```
WACE_new = (energy_old × WACE_old + energy_charged × cost_charged) / energy_new
```

**Example:**
- Battery has 5 kWh at 2.0 SEK/kWh (total cost: 10 SEK)
- Charge 5 kWh at 3.0 SEK/kWh (cost: 15 SEK)
- New WACE: (10 + 15) / 10 = 2.5 SEK/kWh

### Discharging
When energy is removed from the battery, the energy content decreases but the WACE remains unchanged for the remaining energy (FIFO assumption).

**Example:**
- Battery has 10 kWh at 2.5 SEK/kWh
- Discharge 5 kWh
- Remaining: 5 kWh at 2.5 SEK/kWh

## Services

### battery_cost_reset
Reset the weighted average cost to zero while preserving energy content.

**Use case:** You want to start fresh cost tracking or there's been a significant pricing change.

```yaml
service: energy_dispatcher.battery_cost_reset
```

### battery_cost_set_soc
Manually set the battery state of charge (SOC) percentage.

**Use case:** Your SOC sensor is incorrect and you want to manually correct it.

```yaml
service: energy_dispatcher.battery_cost_set_soc
data:
  soc_percent: 50  # Set battery to 50%
```

**Note:** This preserves the WACE - only the energy content is adjusted.

### create_dashboard_notification
Manually create or recreate the dashboard setup notification with instructions and links.

**Use case:** You dismissed the original notification or want to see the dashboard setup instructions again.

```yaml
service: energy_dispatcher.create_dashboard_notification
```

**Note:** This is helpful if you deleted and re-added the integration, or simply want to reference the setup guide again.

## Entities

### Sensor: Battery Energy Cost
- **Entity ID**: `sensor.battery_energy_cost`
- **Value**: Current WACE in SEK/kWh
- **Description**: Shows the weighted average cost of energy currently stored in the battery
- **Attributes**:
  - `total_energy_kwh`: Current energy content (kWh)
  - `total_cost_sek`: Total cost of energy in battery (SEK)
  - `battery_soc_percent`: Current state of charge (%)
  - `battery_capacity_kwh`: Battery capacity (kWh)
  - `history_events`: Total number of historical events
  - `history_charge_events`: Number of charging events recorded
  - `history_discharge_events`: Number of discharge events recorded
  - `history_total_charged_kwh`: Total energy charged (last 30 days)
  - `history_total_discharged_kwh`: Total energy discharged (last 30 days)
  - `history_oldest_event`: Timestamp of oldest event in history
  - `history_newest_event`: Timestamp of newest event in history

### Sensor: Battery Charging State
- **Entity ID**: `sensor.battery_charging_state`
- **Value**: Current battery state: `charging`, `discharging`, or `idle`
- **Description**: Shows the current charging/discharging state of the battery
- **Attributes**:
  - `battery_power_w`: Current battery power (W)
- **Note**: Uses a 50W threshold to determine state

### Sensor: Battery Power Flow
- **Entity ID**: `sensor.battery_power_flow`
- **Value**: Current power flow in Watts
- **Description**: Shows battery power flow (positive = charging, negative = discharging)
- **Device Class**: `power`
- **State Class**: `measurement`
- **Attributes**:
  - `battery_soc_percent`: Current state of charge (%)
  - `battery_energy_kwh`: Current energy content (kWh)
  - `battery_capacity_kwh`: Battery capacity (kWh)
- **Note**: Uses standard convention (positive=charging, negative=discharging)

### Button: Reset Battery Energy Cost
- **Entity ID**: `button.reset_battery_energy_cost`
- **Action**: Calls `battery_cost_reset` service when pressed

## Automation Examples

### Alert When Battery Cost is High
```yaml
automation:
  - alias: "Alert High Battery Cost"
    trigger:
      - platform: numeric_state
        entity_id: sensor.battery_energy_cost
        above: 3.0  # SEK/kWh
    action:
      - service: notify.mobile_app
        data:
          message: "Battery energy cost is high: {{ states('sensor.battery_energy_cost') }} SEK/kWh"
```

### Reset Cost Monthly
```yaml
automation:
  - alias: "Reset Battery Cost Monthly"
    trigger:
      - platform: time
        at: "00:00:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 1 }}"
    action:
      - service: energy_dispatcher.battery_cost_reset
```

### Notify When Battery Is Charging
```yaml
automation:
  - alias: "Notify Battery Charging"
    trigger:
      - platform: state
        entity_id: sensor.battery_charging_state
        to: "charging"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Battery is now charging at {{ states('sensor.battery_power_flow') | round(0) }}W.
            Current cost: {{ states('sensor.battery_energy_cost') }} SEK/kWh
```

## Dashboard Cards

### Simple Cost Display
```yaml
type: entities
entities:
  - entity: sensor.battery_energy_cost
  - type: button
    name: Reset Cost
    tap_action:
      action: call-service
      service: energy_dispatcher.battery_cost_reset
```

### Detailed Cost Card
```yaml
type: custom:mushroom-template-card
primary: "Battery: {{ states('sensor.battery_energy_cost') }} SEK/kWh"
secondary: |
  Energy: {{ state_attr('sensor.battery_energy_cost', 'total_energy_kwh') | round(1) }} kWh
  Cost: {{ state_attr('sensor.battery_energy_cost', 'total_cost_sek') | round(2) }} SEK
  SOC: {{ state_attr('sensor.battery_energy_cost', 'battery_soc_percent') | round(0) }}%
icon: mdi:battery-heart-variant
icon_color: |
  {% set cost = states('sensor.battery_energy_cost') | float %}
  {% if cost < 1.5 %}green
  {% elif cost < 2.5 %}yellow
  {% else %}red
  {% endif %}
```

## Typical Usage Scenarios

### Scenario 1: Daily Cycle with Mixed Sources
1. **Morning (00:00-06:00)**: Charge 5 kWh from cheap night tariff (1.0 SEK/kWh)
   - WACE: 1.0 SEK/kWh
2. **Midday (12:00-14:00)**: Charge 10 kWh from free solar
   - WACE: (5×1.0 + 10×0.0) / 15 = 0.33 SEK/kWh
3. **Evening (18:00-22:00)**: Discharge 12 kWh
   - WACE unchanged: 0.33 SEK/kWh

### Scenario 2: Manual Override
Your SOC sensor shows 40% but you know it's actually at 50%:
```yaml
service: energy_dispatcher.battery_cost_set_soc
data:
  soc_percent: 50
```

### Scenario 3: Cost Reset
New tariff starts, want to track costs separately:
```yaml
service: energy_dispatcher.battery_cost_reset
```

## Technical Details

### Storage
State is persisted to `.storage/energy_dispatcher_bec` (Storage Version 2) and includes:
- `energy_kwh`: Current energy content
- `wace`: Weighted average cost of energy
- `charge_history`: Array of historical events (last 30 days)

Each historical event contains:
- `timestamp`: ISO 8601 timestamp
- `energy_kwh`: Energy amount (positive for charge, negative for discharge)
- `cost_sek_per_kwh`: Cost per kWh (0 for discharge)
- `soc_percent`: Battery SOC after event
- `source`: Energy source ("grid", "solar", "discharge", "manual")
- `event_type`: Type of event ("charge", "discharge", "reset_cost", "initial")
- `total_energy_after`: Total battery energy after event
- `wace_after`: WACE after event

### Storage Migration
The module automatically migrates from Storage Version 1 (no history) to Version 2:
- Existing `energy_kwh` and `wace` values are preserved
- A synthetic initial event is created for historical context
- All future events are properly tracked

### Error Handling
- Negative charge/discharge deltas are ignored
- SOC values are clamped to 0-100%
- Capacity exceeded warnings are logged
- Storage failures are logged and return False

### Logging
All state changes are logged at INFO level for audit purposes:
```
INFO: Charge event: +5.0 kWh @ 2.0 SEK/kWh | Energy: 5.0 -> 10.0 kWh | WACE: 1.5 -> 1.75 SEK/kWh
INFO: Manual SOC set: 50.0% (7.5 kWh -> 7.5 kWh), WACE unchanged at 1.75 SEK/kWh
INFO: Manual cost reset: WACE 1.75 -> 0.0 SEK/kWh (energy unchanged at 7.5 kWh)
```

## FAQ

**Q: What happens if I manually set SOC?**  
A: The energy content is updated based on the new SOC percentage, but the WACE is preserved. This is useful when your SOC sensor is incorrect.

**Q: When should I reset the cost?**  
A: Reset cost when you want to start fresh tracking, such as at the beginning of a billing period or after significant tariff changes.

**Q: Why does WACE stay the same after discharging?**  
A: We use a FIFO (First-In-First-Out) assumption - the remaining energy retains its weighted average cost. This is the most accurate representation for cost tracking.

**Q: Can I have different WACE for different battery sections?**  
A: No, WACE represents the average cost of all energy in the battery. For detailed tracking of individual charging events, you would need additional custom automation.

**Q: What if battery capacity changes?**  
A: The capacity is set during initialization. If your battery capacity changes, you'll need to reconfigure the integration.

## See Also
- [Energy Dispatcher README](../README.md)
- [Services Documentation](../custom_components/energy_dispatcher/services.yaml)
