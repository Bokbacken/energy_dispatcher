# Battery Pause Mode with Dynamic Power Limits

**Date**: 2025-10-13  
**Feature**: Battery Pause Mode using Dynamic Power Limit Sensors  
**Status**: Configuration Added

---

## Overview

Energy Dispatcher now supports dynamic battery power limits through sensor configuration. This enables advanced control scenarios including "pause mode" where the battery can be temporarily disabled from charging or discharging.

## What is Pause Mode?

Pause mode allows you to temporarily stop battery charging or discharging without completely disconnecting the battery or modifying hardware settings. This is achieved by setting the maximum charge/discharge power limits to 0 W.

### Use Cases

**1. Save Energy for Higher Price Periods**
- Battery is full and spot price is very low
- No need to discharge - save the energy for when prices are higher
- Set discharge power to 0 W to pause discharging

**2. Avoid Charging During Moderate Prices**
- Battery has sufficient charge for peak periods
- Current price is moderate - not cheap enough to justify charging
- Set charge power to 0 W to pause charging

**3. Grid Stability or Maintenance**
- Temporarily disable battery operation during grid instability
- Set both charge and discharge to 0 W for full pause

**4. Preserve Backup Reserve**
- Need to maintain battery charge for potential outages
- Disable discharging while still allowing solar charging
- Set discharge power to 0 W

---

## Configuration

### Step 1: Identify Your Battery Power Limit Sensors

For **Huawei LUNA2000** systems, these sensors are typically exposed by the `huawei_solar` integration:

- **Max Charge Power**: `sensor.battery_1_maximum_charge_power` or similar
- **Max Discharge Power**: `sensor.battery_1_maximum_discharge_power` or similar

**Finding Your Sensors:**
1. Go to **Settings → Devices & Services**
2. Find your **Huawei Solar** integration
3. Click on your battery device
4. Look for sensors containing "maximum charge power" or "maximum discharge power"
5. Note the entity IDs

### Step 2: Configure in Energy Dispatcher

1. Go to **Settings → Devices & Services**
2. Find **Energy Dispatcher** integration
3. Click **Configure**
4. In the Battery Configuration section, add:
   - **Max Charge Power Sensor (W)**: Select your charge power limit sensor
   - **Max Discharge Power Sensor (W)**: Select your discharge power limit sensor
5. Save configuration

### Step 3: Verify Configuration

The sensors will now be used to dynamically read the battery's maximum charge and discharge power limits. When these sensors report:
- **Normal value** (e.g., 10000 W): Battery operates normally within that limit
- **0 W**: Battery charging/discharging is paused
- **Reduced value** (e.g., 5000 W): Battery operates with reduced power

---

## How to Implement Pause Mode

### Method 1: Using Huawei Solar Services (Recommended)

The `huawei_solar` integration doesn't directly expose a service to set these registers, but they can be managed through register writes if your integration supports it.

### Method 2: Using Automations with Number Entities

If your Huawei Solar integration exposes writable number entities for these power limits:

**Pause Charging Automation:**
```yaml
automation:
  - alias: "Pause Battery Charging - Low Price Period"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nordpool_kwh_se3_sek_3_10_025
        below: 0.50  # Below 0.50 SEK/kWh
    condition:
      - condition: numeric_state
        entity_id: sensor.battery_state_of_capacity
        above: 90  # Battery > 90%
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_1_maximum_charge_power
        data:
          value: 0  # Pause charging
```

**Resume Charging Automation:**
```yaml
automation:
  - alias: "Resume Battery Charging"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nordpool_kwh_se3_sek_3_10_025
        above: 0.50
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_1_maximum_charge_power
        data:
          value: 10000  # Resume with max power
```

**Pause Discharging During Low Prices:**
```yaml
automation:
  - alias: "Pause Battery Discharging - Save for Peak"
    trigger:
      - platform: numeric_state
        entity_id: sensor.battery_state_of_capacity
        above: 85
      - platform: time
        at: "02:00:00"  # During night low prices
    condition:
      - condition: numeric_state
        entity_id: sensor.nordpool_kwh_se3_sek_3_10_025
        below: 1.00  # Low price period
    action:
      - service: number.set_value
        target:
          entity_id: number.battery_1_maximum_discharge_power
        data:
          value: 0  # Pause discharging
```

### Method 3: Using Node-RED or Advanced Automations

For more complex scenarios, use Node-RED or Home Assistant scripts to:
1. Monitor electricity prices
2. Check battery SOC
3. Calculate optimal pause/resume times
4. Adjust power limits dynamically

---

## Integration with Energy Dispatcher

Once configured, Energy Dispatcher will:

1. **Monitor Dynamic Limits**: Read current values from the configured sensors
2. **Use in Calculations**: Factor these limits into optimization algorithms
3. **Respect Pause State**: When limits are 0 W, the planner knows battery is paused
4. **Dashboard Display**: Show current limits in diagnostic sensors (future enhancement)

**Future Enhancements** (not yet implemented):
- Automatic pause/resume based on price thresholds
- Integration with cost strategy for intelligent pause decisions
- Dashboard cards showing pause state and reasons
- Service calls to control pause mode directly from Energy Dispatcher

---

## Best Practices

### 1. Monitor Battery Temperature
- Don't pause charging/discharging for extended periods in extreme temperatures
- Battery thermal management may require some charge/discharge cycling

### 2. Avoid Long Pause Periods
- Batteries benefit from regular cycling
- Don't pause for more than 24-48 hours continuously
- Consider allowing small trickle charge/discharge

### 3. Set Appropriate Resume Conditions
- Define clear conditions for when to resume normal operation
- Include SOC thresholds, price triggers, and time-based conditions
- Avoid flip-flopping between pause and resume

### 4. Test Thoroughly
- Test pause mode during different conditions
- Verify battery responds correctly to power limit changes
- Monitor for any error states or warnings from the battery system

### 5. Backup Power Considerations
- If using battery for backup power, ensure discharge isn't paused during outages
- Set up automation to resume discharge when grid fails
- Test backup functionality with pause mode active

---

## Example Scenario: Full Day Optimization

**Morning (06:00-09:00)**: Peak prices
- Discharge allowed (limit: 10000 W)
- Charging paused (limit: 0 W)
- Use battery to avoid expensive grid imports

**Daytime (09:00-16:00)**: Low prices, high solar production
- Discharge paused (limit: 0 W) - save energy
- Charging allowed (limit: 10000 W) - charge from cheap grid or solar
- Build up battery reserve for evening peak

**Evening (17:00-22:00)**: Peak prices again
- Discharge allowed (limit: 10000 W)
- Charging paused (limit: 0 W)
- Use stored energy to offset expensive grid power

**Night (22:00-06:00)**: Low prices
- Charging allowed (limit: 10000 W)
- Discharge paused (limit: 0 W) - save for morning peak
- Top up battery from cheap night electricity

**Automation Logic:**
```yaml
input_number:
  price_discharge_threshold:
    name: "Price threshold for discharging"
    min: 0
    max: 5
    step: 0.1
    initial: 2.0
    unit_of_measurement: "SEK/kWh"

automation:
  - alias: "Dynamic Battery Control"
    trigger:
      - platform: state
        entity_id: sensor.nordpool_kwh_se3_sek_3_10_025
      - platform: time_pattern
        minutes: "/5"  # Check every 5 minutes
    action:
      - choose:
          # High price - allow discharge, pause charge
          - conditions:
              - condition: numeric_state
                entity_id: sensor.nordpool_kwh_se3_sek_3_10_025
                above: input_number.price_discharge_threshold
            sequence:
              - service: number.set_value
                target:
                  entity_id: number.battery_1_maximum_discharge_power
                data:
                  value: 10000
              - service: number.set_value
                target:
                  entity_id: number.battery_1_maximum_charge_power
                data:
                  value: 0
          
          # Low price - pause discharge, allow charge
          - conditions:
              - condition: numeric_state
                entity_id: sensor.nordpool_kwh_se3_sek_3_10_025
                below: 1.0
            sequence:
              - service: number.set_value
                target:
                  entity_id: number.battery_1_maximum_discharge_power
                data:
                  value: 0
              - service: number.set_value
                target:
                  entity_id: number.battery_1_maximum_charge_power
                data:
                  value: 10000
          
          # Medium price - normal operation
        default:
          - service: number.set_value
            target:
              entity_id: number.battery_1_maximum_discharge_power
            data:
              value: 10000
          - service: number.set_value
            target:
              entity_id: number.battery_1_maximum_charge_power
            data:
              value: 10000
```

---

## Troubleshooting

### Battery Not Responding to Pause Commands
- **Check sensor entity**: Verify the correct sensor is configured
- **Check entity type**: Ensure sensor is writable (number entity) if trying to control it
- **Huawei integration**: Verify `huawei_solar` integration is up to date
- **Device ID**: Confirm correct device ID is configured in Energy Dispatcher

### Unexpected Battery Behavior
- **Check current limits**: View the sensor values in Developer Tools → States
- **Review automations**: Disable automations temporarily to isolate issue
- **Check logs**: Look for errors in Home Assistant logs related to battery or Huawei Solar
- **Battery firmware**: Ensure battery firmware is up to date

### Power Limits Not Updating
- **Integration restart**: Restart the Huawei Solar integration
- **Configuration reload**: Reload Energy Dispatcher configuration
- **Check EMMA**: Verify EMMA controller is online and responding

---

## Safety Notes

⚠️ **Important Considerations:**

1. **Battery Management System (BMS)**: The battery's internal BMS always has final control. Even if you set limits to 0, the BMS may override this for safety.

2. **Thermal Management**: Batteries may need to charge/discharge for thermal management regardless of your settings.

3. **Backup Power**: If using battery for backup power, ensure your pause logic includes emergency overrides.

4. **Warranty**: Check if modifying battery control parameters affects your warranty.

5. **Grid Connection**: Ensure compliance with local grid connection requirements when pausing battery operation.

---

## Related Documentation

- [Huawei EMMA Capabilities](huawei_emma_capabilities.md) - Full technical reference
- [Configuration Guide](configuration.md) - General configuration instructions
- [Cost Strategy Guide](cost_strategy_and_battery_optimization.md) - Battery optimization algorithms
- [Huawei Integration Summary](huawei_integration_summary.md) - Overview of Huawei features

---

## Summary

Battery pause mode provides fine-grained control over battery charging and discharging by using dynamic power limit sensors. This enables:

✅ **Cost Optimization**: Save energy for high-price periods  
✅ **Grid Integration**: Respond to grid conditions and requirements  
✅ **Battery Longevity**: Reduce unnecessary cycling  
✅ **Flexible Control**: Implement complex automation strategies  
✅ **Safety**: Temporary battery disable without hardware changes

Configure the sensors in Energy Dispatcher and use Home Assistant automations to implement intelligent pause/resume strategies based on your specific needs and electricity pricing patterns.
