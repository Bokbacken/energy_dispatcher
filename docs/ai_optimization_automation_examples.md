# AI Optimization Automation Examples

**Date**: 2025-10-14  
**Status**: Automation Template Library  
**Target Audience**: End Users

---

## Overview

This document provides ready-to-use automation examples for Energy Dispatcher's AI optimization features. Copy and paste these directly into your Home Assistant automations, then customize to your needs.

---

## Table of Contents

1. [Appliance Scheduling Automations](#appliance-scheduling-automations)
2. [EV Charging Automations](#ev-charging-automations)
3. [Battery Management Automations](#battery-management-automations)
4. [Export Management Automations](#export-management-automations)
5. [Notification Automations](#notification-automations)
6. [Cost Tracking Automations](#cost-tracking-automations)
7. [Helper Scripts](#helper-scripts)

---

## Appliance Scheduling Automations

### 1. Smart Dishwasher Notification

Notifies you when it's an optimal time to run the dishwasher.

```yaml
alias: Smart Dishwasher Alert
description: Notify when dishwasher should be run for optimal cost
trigger:
  # Trigger when optimal time is within next 15 minutes
  - platform: template
    value_template: >
      {% set optimal_time = states('sensor.energy_dispatcher_dishwasher_optimal_time') %}
      {% if optimal_time not in ['unknown', 'unavailable'] %}
        {% set optimal = as_timestamp(optimal_time) %}
        {% set now = as_timestamp(now()) %}
        {{ (optimal - now) <= 900 and (optimal - now) > 0 }}
      {% else %}
        false
      {% endif %}
condition:
  # Only notify during awake hours
  - condition: time
    after: '07:00:00'
    before: '22:00:00'
  # Don't notify if already notified recently
  - condition: template
    value_template: >
      {{ (as_timestamp(now()) - as_timestamp(state_attr('automation.smart_dishwasher_alert', 'last_triggered') | default(0))) > 3600 }}
action:
  - service: notify.mobile_app_your_phone
    data:
      title: 🍽️ Time to Run Dishwasher!
      message: >
        Optimal time is NOW. 
        Cost: {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'estimated_cost_sek') | round(2) }} SEK
        Save: {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'cost_savings_vs_now_sek') | round(2) }} SEK
        Reason: {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'reason') }}
      data:
        tag: dishwasher_alert
        group: appliance_scheduling
        actions:
          - action: SNOOZE_DISHWASHER
            title: Remind in 1h
          - action: DISMISS
            title: Dismiss
mode: single
```

### 2. Auto-Schedule Washing Machine

Automatically calculates and displays the best time to do laundry when you indicate you have a load ready.

```yaml
alias: Auto-Schedule Washing Machine
description: Calculate optimal washing machine time when load is ready
trigger:
  # Trigger when helper boolean is turned on
  - platform: state
    entity_id: input_boolean.laundry_ready
    to: 'on'
action:
  # Call the scheduling service
  - service: energy_dispatcher.schedule_appliance
    data:
      appliance: washing_machine
      power_w: 2000
      duration_hours: 1.5
      earliest_start: '{{ now().replace(hour=7, minute=0, second=0) }}'
      latest_end: '{{ now().replace(hour=22, minute=0, second=0) }}'
  
  # Wait for recommendation to update
  - delay:
      seconds: 5
  
  # Send notification with result
  - service: notify.mobile_app_your_phone
    data:
      title: 👕 Washing Machine Schedule Ready
      message: >
        Best time to start: {{ states('sensor.energy_dispatcher_washing_machine_optimal_time') }}
        
        Cost: {{ state_attr('sensor.energy_dispatcher_washing_machine_optimal_time', 'estimated_cost_sek') | round(2) }} SEK
        
        Savings: {{ state_attr('sensor.energy_dispatcher_washing_machine_optimal_time', 'cost_savings_vs_now_sek') | round(2) }} SEK
        
        {{ state_attr('sensor.energy_dispatcher_washing_machine_optimal_time', 'reason') }}
      data:
        actions:
          - action: START_WASHING_NOW
            title: Start Now Anyway
          - action: SET_REMINDER
            title: Remind Me
          - action: DISMISS
            title: OK
  
  # Turn off the ready indicator
  - service: input_boolean.turn_off
    entity_id: input_boolean.laundry_ready
mode: single
```

**Required Helper**: Create `input_boolean.laundry_ready` in Settings → Helpers

### 3. Smart Water Heater Control

Automatically heats water during optimal (cheap) periods while ensuring hot water availability.

```yaml
alias: Smart Water Heater Control
description: Heat water at optimal times while maintaining availability
trigger:
  # Check every 15 minutes
  - platform: time_pattern
    minutes: '/15'
condition: []
action:
  - choose:
      # SCENARIO 1: Optimal time to heat - turn on
      - conditions:
          - condition: template
            value_template: >
              {% set optimal_time = states('sensor.energy_dispatcher_water_heater_optimal_time') %}
              {% if optimal_time not in ['unknown', 'unavailable'] %}
                {% set optimal = as_timestamp(optimal_time) %}
                {% set now = as_timestamp(now()) %}
                {{ (optimal - now) <= 1800 and (optimal - now) >= -1800 }}
              {% else %}
                false
              {% endif %}
          - condition: numeric_state
            entity_id: sensor.water_heater_temperature
            below: 55  # Below target temperature
        sequence:
          - service: switch.turn_on
            entity_id: switch.water_heater
          - service: notify.persistent_notification
            data:
              title: 💧 Water Heater On
              message: Heating water at optimal time ({{ states('sensor.energy_dispatcher_cost_level') }} price)
      
      # SCENARIO 2: Water too cold and it's not a HIGH price period - emergency heat
      - conditions:
          - condition: numeric_state
            entity_id: sensor.water_heater_temperature
            below: 45  # Below minimum acceptable
          - condition: template
            value_template: >
              {{ states('sensor.energy_dispatcher_cost_level') != 'HIGH' }}
        sequence:
          - service: switch.turn_on
            entity_id: switch.water_heater
          - service: notify.mobile_app_your_phone
            data:
              title: ⚠️ Water Heater Emergency On
              message: Water temperature low ({{ states('sensor.water_heater_temperature') }}°C), heating now despite not being optimal time
      
      # SCENARIO 3: Water hot enough - turn off
      - conditions:
          - condition: numeric_state
            entity_id: sensor.water_heater_temperature
            above: 60  # Above target
        sequence:
          - service: switch.turn_off
            entity_id: switch.water_heater
mode: single
```

**Required Sensors**: 
- `sensor.water_heater_temperature` (your water temp sensor)
- `switch.water_heater` (your water heater control switch)

---

## EV Charging Automations

### 4. Smart EV Charging with Deadline

Charges EV at optimal times while ensuring it's ready when you need it.

```yaml
alias: Smart EV Charging
description: Charge EV at optimal times with ready-by deadline
trigger:
  # When EV is plugged in
  - platform: state
    entity_id: binary_sensor.ev_plugged_in
    to: 'on'
  
  # Also check every 30 minutes while plugged in
  - platform: time_pattern
    minutes: '/30'
condition:
  # EV must be plugged in
  - condition: state
    entity_id: binary_sensor.ev_plugged_in
    state: 'on'
  
  # Auto-charge must be enabled
  - condition: state
    entity_id: input_boolean.ev_auto_charge_enabled
    state: 'on'
  
  # SOC below target
  - condition: template
    value_template: >
      {{ states('sensor.ev_battery_soc') | float < states('input_number.ev_target_soc') | float }}
action:
  # Get EV charging recommendation
  - variables:
      current_soc: "{{ states('sensor.ev_battery_soc') | float }}"
      target_soc: "{{ states('input_number.ev_target_soc') | float }}"
      battery_kwh: 75.0  # Adjust for your EV
      energy_needed: "{{ ((target_soc - current_soc) / 100) * battery_kwh }}"
      deadline: "{{ state_attr('input_datetime.ev_ready_by_time', 'timestamp') }}"
  
  # Check if we should charge now
  - choose:
      # CONDITION 1: We're in an optimal charging window
      - conditions:
          - condition: template
            value_template: >
              {% set rec = state_attr('sensor.energy_dispatcher_ev_charging_recommendation', 'optimal_windows') %}
              {% if rec %}
                {% for window in rec %}
                  {% if as_timestamp(window.start_time) <= as_timestamp(now()) <= as_timestamp(window.end_time) %}
                    true
                  {% endif %}
                {% endfor %}
              {% else %}
                false
              {% endif %}
        sequence:
          - service: switch.turn_on
            entity_id: switch.ev_charger_start
          - service: notify.mobile_app_your_phone
            data:
              title: 🚗 EV Charging Started
              message: >
                Charging at optimal time!
                Cost: {{ state_attr('sensor.energy_dispatcher_ev_charging_recommendation', 'estimated_cost_sek') | round(2) }} SEK
                Target: {{ target_soc }}%
                Ready by: {{ states('input_datetime.ev_ready_by_time') }}
      
      # CONDITION 2: Deadline approaching and not enough charge
      - conditions:
          - condition: template
            value_template: >
              {% set hours_until_deadline = (as_timestamp(deadline) - as_timestamp(now())) / 3600 %}
              {% set hours_needed = energy_needed / 11.0 %}
              {{ hours_until_deadline < (hours_needed * 1.2) }}
        sequence:
          - service: switch.turn_on
            entity_id: switch.ev_charger_start
          - service: notify.mobile_app_your_phone
            data:
              title: ⚠️ EV Deadline Charging
              message: >
                Starting EV charge now to meet deadline.
                {{ energy_needed | round(1) }} kWh needed by {{ states('input_datetime.ev_ready_by_time') }}
    
    # DEFAULT: Don't charge yet, waiting for better price
    default:
      - service: switch.turn_off
        entity_id: switch.ev_charger_start
mode: restart
```

**Required Helpers**:
- `input_boolean.ev_auto_charge_enabled` (boolean)
- `input_number.ev_target_soc` (number, 50-100%)
- `input_datetime.ev_ready_by_time` (datetime)

### 5. EV Charging Complete Notification

Notifies when EV charging is complete.

```yaml
alias: EV Charging Complete
description: Notify when EV reaches target SOC
trigger:
  - platform: template
    value_template: >
      {{ states('sensor.ev_battery_soc') | float >= states('input_number.ev_target_soc') | float }}
condition:
  - condition: state
    entity_id: binary_sensor.ev_plugged_in
    state: 'on'
  - condition: state
    entity_id: switch.ev_charger_start
    state: 'on'
action:
  # Stop charging
  - service: switch.turn_off
    entity_id: switch.ev_charger_start
  
  # Calculate and notify
  - variables:
      final_cost: "{{ state_attr('sensor.energy_dispatcher_ev_charging_recommendation', 'estimated_cost_sek') | round(2) }}"
      savings: "{{ state_attr('sensor.energy_dispatcher_ev_charging_recommendation', 'savings_sek') | round(2) }}"
  
  - service: notify.mobile_app_your_phone
    data:
      title: ✅ EV Charging Complete
      message: >
        Your EV is ready! 🚗✨
        
        Final SOC: {{ states('sensor.ev_battery_soc') }}%
        Charge cost: {{ final_cost }} SEK
        Saved: {{ savings }} SEK vs. immediate charging
        
        {{ state_attr('sensor.energy_dispatcher_ev_charging_recommendation', 'reason') }}
      data:
        tag: ev_charging_complete
        actions:
          - action: VIEW_EV
            title: View Details
mode: single
```

---

## Battery Management Automations

### 6. Automatic Battery Reserve Management

Dynamically adjusts battery reserve based on upcoming high-cost periods.

```yaml
alias: Dynamic Battery Reserve
description: Adjust battery reserve target based on upcoming price forecast
trigger:
  # Update every hour
  - platform: time_pattern
    hours: '/1'
  
  # Also when cost level changes
  - platform: state
    entity_id: sensor.energy_dispatcher_cost_level
condition: []
action:
  - variables:
      recommended_reserve: "{{ states('sensor.energy_dispatcher_battery_reserve') | float }}"
      current_soc: "{{ states('sensor.battery_soc') | float }}"
      should_charge: "{{ states('binary_sensor.energy_dispatcher_should_charge_battery') }}"
      should_discharge: "{{ states('binary_sensor.energy_dispatcher_should_discharge_battery') }}"
  
  - choose:
      # HIGH reserve recommended and we're below it - charge if not high price
      - conditions:
          - condition: template
            value_template: "{{ current_soc < recommended_reserve }}"
          - condition: template
            value_template: "{{ should_charge == 'on' }}"
        sequence:
          - service: notify.persistent_notification
            data:
              title: 🔋 Battery Below Reserve
              message: >
                Battery at {{ current_soc }}%, reserve target is {{ recommended_reserve }}%.
                Charging recommended to prepare for upcoming high-cost period.
          
          # You could add actual battery charge command here if you have control
      
      # We're above reserve and discharge recommended
      - conditions:
          - condition: template
            value_template: "{{ current_soc > recommended_reserve + 10 }}"
          - condition: template
            value_template: "{{ should_discharge == 'on' }}"
        sequence:
          - service: notify.persistent_notification
            data:
              title: 🔋 Battery Discharge Opportunity
              message: >
                Battery at {{ current_soc }}%, above reserve ({{ recommended_reserve }}%).
                High price period - consider using battery power.
mode: single
```

### 7. Battery Override Timer

Automatically cancels battery mode overrides after specified duration.

```yaml
alias: Battery Override Auto-Cancel
description: Reset battery mode after override expires
trigger:
  # Check every 5 minutes
  - platform: time_pattern
    minutes: '/5'
condition:
  # There is an active override
  - condition: template
    value_template: >
      {{ state_attr('sensor.energy_dispatcher_battery_mode', 'override_active') == true }}
  
  # Override has expired
  - condition: template
    value_template: >
      {% set expires = state_attr('sensor.energy_dispatcher_battery_mode', 'override_expires_at') %}
      {{ expires and as_timestamp(expires) <= as_timestamp(now()) }}
action:
  - service: energy_dispatcher.override_battery_mode
    data:
      mode: auto
  
  - service: notify.mobile_app_your_phone
    data:
      title: 🔋 Battery Override Ended
      message: Battery mode returned to automatic optimization
mode: single
```

---

## Export Management Automations

### 8. Export Opportunity Alert

Alerts when energy export is highly profitable.

```yaml
alias: High-Value Export Alert
description: Notify when export opportunity exceeds threshold
trigger:
  - platform: state
    entity_id: binary_sensor.energy_dispatcher_export_opportunity
    to: 'on'
condition:
  # Revenue must be significant
  - condition: numeric_state
    entity_id: sensor.energy_dispatcher_export_revenue_estimate
    above: 10.0  # At least 10 SEK potential
  
  # Battery must be sufficiently charged
  - condition: numeric_state
    entity_id: sensor.battery_soc
    above: 80
action:
  - service: notify.mobile_app_your_phone
    data:
      title: 💰 Export Opportunity!
      message: >
        HIGH spot price detected: {{ state_attr('binary_sensor.energy_dispatcher_export_opportunity', 'export_price_sek_per_kwh') | round(2) }} SEK/kWh
        
        Potential revenue: {{ states('sensor.energy_dispatcher_export_revenue_estimate') }} SEK
        
        Duration: {{ state_attr('binary_sensor.energy_dispatcher_export_opportunity', 'duration_estimate_h') | round(1) }} hours
        
        Battery: {{ states('sensor.battery_soc') }}%
        
        {{ state_attr('binary_sensor.energy_dispatcher_export_opportunity', 'reason') }}
      data:
        tag: export_opportunity
        group: energy_optimization
        actions:
          - action: ENABLE_EXPORT
            title: Enable Export
          - action: DISMISS
            title: Not Now
mode: single
```

### 9. Auto-Enable Export (Conservative)

Automatically enables export only during exceptional circumstances.

```yaml
alias: Auto-Enable Export (Conservative)
description: Enable export only when conditions are highly favorable
trigger:
  - platform: state
    entity_id: binary_sensor.energy_dispatcher_export_opportunity
    to: 'on'
condition:
  # Very high revenue potential
  - condition: numeric_state
    entity_id: sensor.energy_dispatcher_export_revenue_estimate
    above: 20.0
  
  # Battery nearly full
  - condition: numeric_state
    entity_id: sensor.battery_soc
    above: 95
  
  # Solar producing excess
  - condition: numeric_state
    entity_id: sensor.solar_power
    above: 1000
  
  # No high-cost periods expected soon
  - condition: template
    value_template: >
      {% set next_high = states('sensor.energy_dispatcher_next_high_cost_period') %}
      {{ next_high == 'unknown' or (as_timestamp(next_high) - as_timestamp(now())) > 14400 }}
action:
  # Enable export
  - service: energy_dispatcher.set_export_mode
    data:
      mode: peak_price_opportunistic
  
  # Notify
  - service: notify.mobile_app_your_phone
    data:
      title: ⚡ Auto-Export Enabled
      message: >
        Export automatically enabled due to exceptional conditions:
        • Price: {{ state_attr('binary_sensor.energy_dispatcher_export_opportunity', 'export_price_sek_per_kwh') | round(2) }} SEK/kWh
        • Revenue: {{ states('sensor.energy_dispatcher_export_revenue_estimate') }} SEK
        • Battery: {{ states('sensor.battery_soc') }}%
      data:
        actions:
          - action: DISABLE_EXPORT
            title: Disable Export
  
  # Auto-disable after duration
  - delay:
      hours: >
        {{ state_attr('binary_sensor.energy_dispatcher_export_opportunity', 'duration_estimate_h') | float }}
  
  - service: energy_dispatcher.set_export_mode
    data:
      mode: never
  
  - service: notify.persistent_notification
    data:
      title: Export Disabled
      message: Auto-export period ended, returned to normal operation
mode: single
```

---

## Notification Automations

### 10. Daily Optimization Summary

Sends a daily summary of AI optimization performance.

```yaml
alias: Daily Optimization Summary
description: Daily report of energy optimization and savings
trigger:
  - platform: time
    at: '20:00:00'
condition: []
action:
  - variables:
      today_savings: "{{ states('sensor.energy_dispatcher_estimated_savings_today') | float }}"
      month_savings: "{{ states('sensor.energy_dispatcher_estimated_savings_month') | float }}"
      battery_savings: "{{ state_attr('sensor.energy_dispatcher_estimated_savings_today', 'battery_optimization_sek') | float }}"
      ev_savings: "{{ state_attr('sensor.energy_dispatcher_estimated_savings_today', 'ev_charging_optimization_sek') | float }}"
      appliance_savings: "{{ state_attr('sensor.energy_dispatcher_estimated_savings_today', 'appliance_scheduling_sek') | float }}"
  
  - service: notify.mobile_app_your_phone
    data:
      title: 📊 Daily Energy Summary
      message: >
        ### Today's AI Optimization Results
        
        **Total Savings**: {{ today_savings | round(2) }} SEK
        
        **Breakdown**:
        • Battery: {{ battery_savings | round(2) }} SEK
        • EV Charging: {{ ev_savings | round(2) }} SEK
        • Appliances: {{ appliance_savings | round(2) }} SEK
        
        **Month Total**: {{ month_savings | round(2) }} SEK
        
        **Current Status**:
        • Price Level: {{ states('sensor.energy_dispatcher_cost_level') }}
        • Battery: {{ states('sensor.battery_soc') }}%
        • Next Cheap Period: {{ as_timestamp(states('sensor.energy_dispatcher_next_cheap_period')) | timestamp_custom('%H:%M') }}
      data:
        tag: daily_summary
        actions:
          - action: VIEW_DASHBOARD
            title: View Dashboard
mode: single
```

### 11. Price Alert - Upcoming High Cost Period

Warns when a high-cost period is approaching.

```yaml
alias: High Cost Period Warning
description: Alert 30 minutes before high-cost period begins
trigger:
  - platform: template
    value_template: >
      {% set next_high = states('sensor.energy_dispatcher_next_high_cost_period') %}
      {% if next_high not in ['unknown', 'unavailable'] %}
        {% set time_until = (as_timestamp(next_high) - as_timestamp(now())) / 60 %}
        {{ time_until <= 30 and time_until > 25 }}
      {% else %}
        false
      {% endif %}
condition: []
action:
  - service: notify.mobile_app_your_phone
    data:
      title: ⚠️ High Cost Period Approaching
      message: >
        High electricity prices starting in 30 minutes!
        
        Start time: {{ as_timestamp(states('sensor.energy_dispatcher_next_high_cost_period')) | timestamp_custom('%H:%M') }}
        
        Duration: {{ state_attr('sensor.energy_dispatcher_next_high_cost_period', 'duration_hours') }} hours
        
        Avg price: {{ state_attr('sensor.energy_dispatcher_next_high_cost_period', 'avg_price_sek_per_kwh') | round(2) }} SEK/kWh
        
        **Recommendations**:
        • Ensure battery is charged ({{ states('sensor.battery_soc') }}%)
        • Avoid running high-power appliances
        • Use battery power if possible
      data:
        tag: high_cost_warning
        priority: high
        actions:
          - action: VIEW_FORECAST
            title: View Forecast
mode: single
```

---

## Cost Tracking Automations

### 12. Monthly Savings Report

Sends detailed monthly optimization report.

```yaml
alias: Monthly Optimization Report
description: Detailed monthly savings and performance report
trigger:
  - platform: time
    at: '08:00:00'
condition:
  # First day of month
  - condition: template
    value_template: "{{ now().day == 1 }}"
action:
  - variables:
      last_month_savings: "{{ states('sensor.energy_dispatcher_estimated_savings_month') | float }}"
      savings_percentage: "{{ state_attr('sensor.energy_dispatcher_estimated_savings_month', 'savings_percentage') | float }}"
  
  - service: notify.mobile_app_your_phone
    data:
      title: 📈 Monthly Energy Report
      message: >
        ## {{ (now() - timedelta(days=1)).strftime('%B %Y') }} Optimization Summary
        
        ### Total Savings: {{ last_month_savings | round(2) }} SEK
        
        **Savings Rate**: {{ savings_percentage | round(1) }}% of baseline cost
        
        **Category Breakdown**:
        • Battery Optimization: {{ state_attr('sensor.energy_dispatcher_estimated_savings_month', 'battery_optimization_sek') | round(2) }} SEK
        • EV Charging: {{ state_attr('sensor.energy_dispatcher_estimated_savings_month', 'ev_charging_optimization_sek') | round(2) }} SEK
        • Appliance Scheduling: {{ state_attr('sensor.energy_dispatcher_estimated_savings_month', 'appliance_scheduling_sek') | round(2) }} SEK
        • Peak Shaving: {{ state_attr('sensor.energy_dispatcher_estimated_savings_month', 'peak_shaving_sek') | round(2) }} SEK
        • Export Revenue: {{ state_attr('sensor.energy_dispatcher_estimated_savings_month', 'export_revenue_sek') | round(2) }} SEK
        
        **Projected Annual Savings**: {{ (last_month_savings * 12) | round(2) }} SEK
        
        Keep optimizing! 🎯
      data:
        tag: monthly_report
        actions:
          - action: VIEW_DETAILS
            title: View Details
mode: single
```

---

## Helper Scripts

### Script: Emergency Battery Charge

```yaml
emergency_battery_charge:
  alias: Emergency Battery Charge
  description: Force battery to charge immediately regardless of price
  sequence:
    - service: energy_dispatcher.override_battery_mode
      data:
        mode: charge
        duration_minutes: 120
        power_w: 5000
    
    - service: notify.mobile_app_your_phone
      data:
        title: 🔋 Emergency Charge Started
        message: Battery charging at max power for 2 hours
  mode: single
  icon: mdi:battery-alert
```

### Script: Optimize All Appliances

```yaml
optimize_all_appliances:
  alias: Optimize All Appliances
  description: Recalculate optimal times for all appliances
  sequence:
    # Dishwasher
    - service: energy_dispatcher.schedule_appliance
      data:
        appliance: dishwasher
        power_w: 1800
        duration_hours: 2.0
    
    # Washing machine
    - service: energy_dispatcher.schedule_appliance
      data:
        appliance: washing_machine
        power_w: 2000
        duration_hours: 1.5
    
    # Water heater
    - service: energy_dispatcher.schedule_appliance
      data:
        appliance: water_heater
        power_w: 3000
        duration_hours: 2.0
    
    - delay:
        seconds: 5
    
    - service: notify.mobile_app_your_phone
      data:
        title: ✅ Appliances Optimized
        message: All appliance schedules updated with latest price forecasts
  mode: single
  icon: mdi:calendar-refresh
```

### Script: Reset All Optimizations

```yaml
reset_all_optimizations:
  alias: Reset All Optimizations
  description: Clear all overrides and return to full auto mode
  sequence:
    - service: energy_dispatcher.reset_optimizations
    
    - service: energy_dispatcher.override_battery_mode
      data:
        mode: auto
    
    - service: energy_dispatcher.set_export_mode
      data:
        mode: never
    
    - service: notify.persistent_notification
      data:
        title: 🔄 Optimizations Reset
        message: All overrides cleared, system returned to automatic optimization mode
  mode: single
  icon: mdi:restart
```

---

## Tips for Customization

### 1. Adjust Notification Thresholds

Modify conditions to match your preferences:
```yaml
# Example: Only notify for savings > 5 SEK
- condition: numeric_state
  entity_id: sensor.energy_dispatcher_dishwasher_optimal_time
  value_template: "{{ state.attributes.cost_savings_vs_now_sek }}"
  above: 5.0
```

### 2. Customize Notification Times

Change when notifications are sent:
```yaml
# Example: Only during waking hours
- condition: time
  after: '07:00:00'
  before: '22:00:00'
  weekday:
    - mon
    - tue
    - wed
    - thu
    - fri
```

### 3. Add Presence Detection

Only notify when home:
```yaml
- condition: state
  entity_id: person.your_name
  state: home
```

### 4. Integrate with Voice Assistants

Add to Google/Alexa:
```yaml
# In configuration.yaml
google_assistant:
  entity_config:
    script.emergency_battery_charge:
      expose: true
      name: Emergency Battery Charge
```

---

## Testing Your Automations

### 1. Test Services Manually

**Developer Tools** → **Services**:
```yaml
service: energy_dispatcher.schedule_appliance
data:
  appliance: dishwasher
  power_w: 1800
  duration_hours: 2.0
```

### 2. Test Triggers

**Developer Tools** → **Template**:
```yaml
{% set optimal_time = states('sensor.energy_dispatcher_dishwasher_optimal_time') %}
{{ (as_timestamp(optimal_time) - as_timestamp(now())) / 60 }} minutes until optimal
```

### 3. Check Automation Logs

**Settings** → **System** → **Logs** → Filter by automation name

---

## Troubleshooting

**Problem**: Automation not triggering  
**Solution**: Check condition constraints, verify entity states

**Problem**: Notifications not received  
**Solution**: Check mobile app permissions, test notify service manually

**Problem**: Service calls failing  
**Solution**: Verify service exists, check required parameters

---

## Next Steps

1. ✅ Copy automations you want to use
2. ✅ Customize notification preferences
3. ✅ Test each automation individually
4. ✅ Monitor for a few days
5. ✅ Fine-tune thresholds and timing
6. ✅ Share your improvements!

---

**Related Documentation**:
- [AI Optimization Dashboard Guide](ai_optimization_dashboard_guide.md)
- [Cost Strategy and Battery Optimization](cost_strategy_and_battery_optimization.md)
- [Configuration Guide](configuration.md)

**Happy Automating! 🤖**
