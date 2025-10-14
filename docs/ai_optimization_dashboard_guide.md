# AI Optimization Dashboard Guide

**Date**: 2025-10-14  
**Status**: Dashboard Setup Guide  
**Target Audience**: End Users

---

## Overview

This guide shows you how to create a comprehensive AI-like optimization dashboard for Energy Dispatcher. The dashboard displays intelligent recommendations for appliance scheduling, EV charging, battery management, and cost-saving opportunities.

**What You'll Create**:
- 🤖 AI Optimization Status Card
- 💡 Smart Appliance Recommendations
- 🔋 Battery & EV Optimization Controls
- 📊 Cost Savings Tracking
- ⚡ Export Opportunities Monitor
- 🎛️ Quick Action Buttons

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Dashboard Overview](#dashboard-overview)
3. [Step-by-Step Setup](#step-by-step-setup)
4. [Complete Dashboard YAML](#complete-dashboard-yaml)
5. [Automation Examples](#automation-examples)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- ✅ Energy Dispatcher integration installed with AI optimization features
- ✅ At least 24 hours of price data
- ✅ Battery configured and operational

### Recommended HACS Frontend Cards
Install these from HACS → Frontend for the best experience:

1. **ApexCharts Card** - Beautiful graphs and charts
2. **Mushroom Cards** - Modern, touch-friendly controls
3. **Button Card** - Custom action buttons
4. **Multiple Entity Row** - Compact entity displays
5. **Card Mod** - Advanced styling options
6. **Layout Card** - Better grid layouts

**Installation**: HACS → Frontend → Explore & Download Repositories → Search for card name

---

## Dashboard Overview

Your AI Optimization Dashboard will have these sections:

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 AI Energy Optimization                                      │
├─────────────────────────────────────────────────────────────────┤
│  Current Status:                                                │
│  • Price Level: CHEAP (1.20 SEK/kWh)                           │
│  • Battery Reserve: 40%                                         │
│  • Charging Recommended: Yes                                    │
│  • Next Action: Charge battery @ 13:00                         │
├─────────────────────────────────────────────────────────────────┤
│  💡 Smart Recommendations                                       │
├─────────────────────────────────────────────────────────────────┤
│  🍽️  Dishwasher:     13:00-15:00  Save 1.35 SEK               │
│  👕  Washing Machine: 02:00-04:00  Save 2.80 SEK               │
│  🚗  EV Charging:     01:00-05:00  Save 12.50 SEK              │
│  💧  Water Heater:    14:00-16:00  Save 3.20 SEK               │
├─────────────────────────────────────────────────────────────────┤
│  📊 Cost Optimization                                           │
├─────────────────────────────────────────────────────────────────┤
│  Today's Savings:     15.80 SEK                                │
│  This Month:          342.50 SEK                               │
│  Next Cheap Period:   13:00 (in 2 hours)                      │
├─────────────────────────────────────────────────────────────────┤
│  🔋 Quick Actions                                               │
├─────────────────────────────────────────────────────────────────┤
│  [Force Charge] [Start EV] [Export Mode] [Reset]              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Setup

### Step 1: Create New Dashboard

1. Go to **Settings** → **Dashboards**
2. Click **+ ADD DASHBOARD** (bottom right)
3. Fill in:
   - **Title**: "AI Energy Optimization"
   - **Icon**: `mdi:robot`
   - **Show in sidebar**: ✅ (checked)
4. Click **CREATE**

### Step 2: Add AI Optimization Status Card

1. Click **+ ADD CARD**
2. Select **Entities Card**
3. Click **Show Code Editor** (bottom left)
4. Paste this YAML:

```yaml
type: entities
title: 🤖 AI Optimization Status
icon: mdi:robot
entities:
  - entity: sensor.energy_dispatcher_cost_level
    name: Current Price Level
    icon: mdi:currency-eur
  - entity: sensor.energy_dispatcher_battery_reserve
    name: Battery Reserve Target
    icon: mdi:battery-50
    secondary_info: last-changed
  - entity: binary_sensor.energy_dispatcher_should_charge_battery
    name: Battery Charging Recommended
    icon: mdi:battery-charging
  - entity: binary_sensor.energy_dispatcher_should_discharge_battery
    name: Battery Discharging Recommended
    icon: mdi:battery-arrow-down
  - entity: sensor.energy_dispatcher_optimization_plan
    name: Next Recommended Action
    icon: mdi:calendar-clock
state_color: true
```

5. Click **SAVE**

**What this shows**:
- Current electricity price level (CHEAP/MEDIUM/HIGH)
- Recommended battery reserve percentage
- Whether to charge or discharge battery now
- Next scheduled optimization action

---

### Step 3: Add Smart Recommendations Card

This card shows optimal times to run appliances.

```yaml
type: entities
title: 💡 Smart Recommendations
icon: mdi:lightbulb-on
entities:
  - type: section
    label: Appliances
  - entity: sensor.energy_dispatcher_dishwasher_optimal_time
    name: 🍽️ Dishwasher
    icon: mdi:dishwasher
    secondary_info: last-changed
    tap_action:
      action: more-info
  - entity: sensor.energy_dispatcher_washing_machine_optimal_time
    name: 👕 Washing Machine
    icon: mdi:washing-machine
    secondary_info: last-changed
    tap_action:
      action: more-info
  - entity: sensor.energy_dispatcher_water_heater_optimal_time
    name: 💧 Water Heater
    icon: mdi:water-boiler
    secondary_info: last-changed
    tap_action:
      action: more-info
  
  - type: section
    label: Electric Vehicle
  - entity: sensor.energy_dispatcher_ev_charging_recommendation
    name: 🚗 EV Charging
    icon: mdi:car-electric
    secondary_info: last-changed
    tap_action:
      action: more-info
  
  - type: section
    label: Load Shifting
  - entity: sensor.energy_dispatcher_load_shift_opportunity
    name: ⚡ Best Load Shift
    icon: mdi:clock-time-four
  - entity: sensor.energy_dispatcher_load_shift_savings
    name: 💰 Potential Savings
    icon: mdi:piggy-bank
state_color: true
```

**What this shows**:
- Optimal time to run dishwasher with estimated savings
- Best window for washing machine
- When to heat water
- EV charging schedule recommendation
- Load shifting opportunities

**Tap any entity** to see detailed information including:
- Estimated cost
- Savings vs. running now
- Reasoning (e.g., "Solar peak + cheap price")
- Alternative time windows

---

### Step 4: Add Cost Optimization Card

Track your savings and upcoming opportunities.

```yaml
type: entities
title: 📊 Cost Optimization
icon: mdi:chart-line
entities:
  - type: section
    label: Savings
  - entity: sensor.energy_dispatcher_estimated_savings_today
    name: Today's Savings
    icon: mdi:piggy-bank
  - entity: sensor.energy_dispatcher_estimated_savings_month
    name: This Month
    icon: mdi:cash-multiple
  
  - type: section
    label: Price Windows
  - entity: sensor.energy_dispatcher_next_cheap_period
    name: Next Cheap Period
    icon: mdi:clock-outline
    secondary_info: last-changed
  - entity: sensor.energy_dispatcher_next_high_cost_period
    name: Next High Cost Period
    icon: mdi:alert-circle
    secondary_info: last-changed
  
  - type: section
    label: Export Opportunities
  - entity: binary_sensor.energy_dispatcher_export_opportunity
    name: Export Recommended
    icon: mdi:transmission-tower-export
  - entity: sensor.energy_dispatcher_export_revenue_estimate
    name: Estimated Revenue
    icon: mdi:cash-plus
state_color: true
```

**What this shows**:
- Real-time savings calculations
- Cumulative monthly savings
- Upcoming cheap/expensive periods
- Export opportunities (when profitable)
- Potential export revenue

---

### Step 5: Add Price & Optimization Chart

Beautiful chart showing 24-hour price forecast with optimization actions.

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: 24h Price & Optimization Plan
  show_states: true
  colorize_states: true
graph_span: 24h
span:
  start: day
all_series_config:
  stroke_width: 2
series:
  # Price bars
  - entity: sensor.nordpool_kwh_se3_sek_3_10_025
    name: Electricity Price
    type: column
    color: var(--primary-color)
    opacity: 0.3
    data_generator: |
      return entity.attributes.raw_today.concat(entity.attributes.raw_tomorrow || []).map((item) => {
        return [new Date(item.start), item.value];
      });
  
  # Cost level thresholds
  - entity: sensor.energy_dispatcher_cost_level
    name: Cheap Threshold
    type: line
    color: green
    stroke_width: 1
    curve: stepline
    show:
      in_header: false
    data_generator: |
      const threshold = entity.attributes.cheap_threshold || 1.5;
      const now = new Date();
      const start = new Date(now);
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setHours(48, 0, 0, 0);
      return [[start, threshold], [end, threshold]];
  
  - entity: sensor.energy_dispatcher_cost_level
    name: High Threshold
    type: line
    color: red
    stroke_width: 1
    curve: stepline
    show:
      in_header: false
    data_generator: |
      const threshold = entity.attributes.high_threshold || 3.0;
      const now = new Date();
      const start = new Date(now);
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setHours(48, 0, 0, 0);
      return [[start, threshold], [end, threshold]];
  
  # Battery actions overlay
  - entity: sensor.energy_dispatcher_optimization_plan
    name: Charge Battery
    type: line
    color: '#4CAF50'
    stroke_width: 3
    curve: stepline
    data_generator: |
      if (!entity.attributes.actions) return [];
      return entity.attributes.actions
        .filter(a => a.battery_action === 'charge')
        .map(a => [new Date(a.time), 0.5]);
  
  - entity: sensor.energy_dispatcher_optimization_plan
    name: Discharge Battery
    type: line
    color: '#FF5722'
    stroke_width: 3
    curve: stepline
    data_generator: |
      if (!entity.attributes.actions) return [];
      return entity.attributes.actions
        .filter(a => a.battery_action === 'discharge')
        .map(a => [new Date(a.time), 0.5]);
yaxis:
  - id: price
    decimals: 2
    apex_config:
      tickAmount: 5
      labels:
        formatter: |
          EVAL:function(value) {
            return value.toFixed(2) + ' SEK';
          }
```

**What this shows**:
- 24-hour price forecast as bars
- Cheap/high price thresholds as horizontal lines
- Planned battery charge periods (green)
- Planned battery discharge periods (red)
- Interactive - tap any point for details

---

### Step 5.5: Add Weather-Adjusted Solar Forecast Card

Display weather-adjusted solar forecast with comparison to base forecast.

```yaml
type: entities
title: ☀️ Weather-Adjusted Solar Forecast
state_color: true
entities:
  - entity: sensor.energy_dispatcher_weather_adjusted_solar_forecast
    name: Today's Forecast (Weather-Adjusted)
    icon: mdi:weather-partly-cloudy
  - type: attribute
    entity: sensor.energy_dispatcher_weather_adjusted_solar_forecast
    attribute: base_forecast_kwh
    name: Base Forecast (Clear Sky)
    icon: mdi:weather-sunny
  - type: attribute
    entity: sensor.energy_dispatcher_weather_adjusted_solar_forecast
    attribute: confidence_level
    name: Confidence Level
    icon: mdi:speedometer
  - type: attribute
    entity: sensor.energy_dispatcher_weather_adjusted_solar_forecast
    attribute: limiting_factor
    name: Limiting Factor
    icon: mdi:information-outline
  - type: attribute
    entity: sensor.energy_dispatcher_weather_adjusted_solar_forecast
    attribute: reduction_percentage
    name: Forecast Reduction
    icon: mdi:arrow-down-bold
    suffix: "%"
```

**Alternative: Visual Comparison Card**

Show base vs adjusted forecast side-by-side:

```yaml
type: custom:mushroom-template-card
primary: Solar Forecast (Weather-Adjusted)
secondary: >
  Base: {{ state_attr('sensor.energy_dispatcher_weather_adjusted_solar_forecast', 'base_forecast_kwh') | round(1) }} kWh
  | Adjusted: {{ states('sensor.energy_dispatcher_weather_adjusted_solar_forecast') | round(1) }} kWh
  | Reduction: {{ state_attr('sensor.energy_dispatcher_weather_adjusted_solar_forecast', 'reduction_percentage') | round(0) }}%
icon: >
  {% set factor = state_attr('sensor.energy_dispatcher_weather_adjusted_solar_forecast', 'limiting_factor') %}
  {% if factor == 'clear' %}
    mdi:weather-sunny
  {% elif factor == 'cloud_cover' %}
    mdi:weather-cloudy
  {% elif factor == 'temperature' %}
    mdi:thermometer-alert
  {% else %}
    mdi:weather-partly-cloudy
  {% endif %}
icon_color: >
  {% set conf = state_attr('sensor.energy_dispatcher_weather_adjusted_solar_forecast', 'confidence_level') %}
  {% if conf == 'high' %}
    green
  {% elif conf == 'medium' %}
    amber
  {% else %}
    red
  {% endif %}
tap_action:
  action: more-info
```

**What this shows**:
- Weather-adjusted solar forecast for today (kWh)
- Comparison with base forecast (clear sky scenario)
- Confidence level (high/medium/low) based on weather data availability
- Limiting factor (clear/cloud_cover/temperature/multiple)
- Percentage reduction from base forecast
- Icon changes based on conditions (sunny/cloudy/hot)
- Color indicates confidence (green=high, amber=medium, red=low)

**When the forecast is significantly reduced (>20%)**:
- Battery reserve is automatically increased by 10-20%
- Ensures adequate backup during poor solar conditions
- Helps avoid grid imports during expensive periods

---

### Step 6: Add Quick Action Buttons

Control overrides and manual actions easily.

```yaml
type: horizontal-stack
cards:
  # Force Charge Battery
  - type: button
    name: Force Charge
    icon: mdi:battery-charging
    icon_height: 40px
    tap_action:
      action: call-service
      service: energy_dispatcher.override_battery_mode
      data:
        mode: charge
        duration_minutes: 60
      confirmation:
        text: Force battery charging for 1 hour?
    hold_action:
      action: more-info
  
  # Start EV Charging
  - type: button
    name: Start EV
    icon: mdi:ev-station
    icon_height: 40px
    tap_action:
      action: call-service
      service: energy_dispatcher.start_ev_charging
      data:
        mode: optimal
      confirmation:
        text: Start EV charging in optimal mode?
  
  # Toggle Export Mode
  - type: button
    name: Export Mode
    icon: mdi:transmission-tower-export
    icon_height: 40px
    tap_action:
      action: call-service
      service: energy_dispatcher.set_export_mode
      data:
        mode: excess_solar_only
      confirmation:
        text: Enable export (excess solar only)?
  
  # Reset Optimizations
  - type: button
    name: Reset
    icon: mdi:restart
    icon_height: 40px
    tap_action:
      action: call-service
      service: energy_dispatcher.reset_optimizations
      confirmation:
        text: Reset all optimizations to defaults?
```

**What these do**:
- **Force Charge**: Override automatic control to charge battery for 1 hour
- **Start EV**: Begin EV charging in optimal (cost-minimizing) mode
- **Export Mode**: Enable energy export when conditions are profitable
- **Reset**: Clear all overrides and return to automatic optimization

---

### Step 7: Add Appliance Detail Cards (Optional)

For detailed information about each appliance recommendation.

```yaml
type: vertical-stack
cards:
  - type: markdown
    title: 🍽️ Dishwasher Details
    content: >
      **Optimal Time:** {{ states('sensor.energy_dispatcher_dishwasher_optimal_time') }}

      **Current Price:** {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'current_price') }} SEK/kWh

      **Price at Optimal Time:** {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'price_at_optimal_time') }} SEK/kWh

      **Estimated Cost:** {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'estimated_cost_sek') }} SEK

      **Savings vs. Now:** {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'cost_savings_vs_now_sek') }} SEK

      **Reason:** {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'reason') }}

      **Solar Available:** {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'solar_available') }}

  - type: button
    name: Schedule Dishwasher
    icon: mdi:dishwasher
    tap_action:
      action: call-service
      service: energy_dispatcher.schedule_appliance
      data:
        appliance: dishwasher
        power_w: 1800
        duration_hours: 2.0
```

**Repeat for other appliances** (washing machine, water heater, etc.)

---

## Complete Dashboard YAML

Here's the complete dashboard configuration combining all sections:

<details>
<summary>Click to expand complete YAML</summary>

```yaml
title: AI Energy Optimization
icon: mdi:robot
path: ai-optimization
badges: []
cards:
  # Row 1: AI Status and Recommendations
  - type: horizontal-stack
    cards:
      # AI Optimization Status
      - type: entities
        title: 🤖 AI Optimization Status
        icon: mdi:robot
        entities:
          - entity: sensor.energy_dispatcher_cost_level
            name: Current Price Level
            icon: mdi:currency-eur
          - entity: sensor.energy_dispatcher_battery_reserve
            name: Battery Reserve Target
            icon: mdi:battery-50
            secondary_info: last-changed
          - entity: binary_sensor.energy_dispatcher_should_charge_battery
            name: Battery Charging Recommended
            icon: mdi:battery-charging
          - entity: binary_sensor.energy_dispatcher_should_discharge_battery
            name: Battery Discharging Recommended
            icon: mdi:battery-arrow-down
          - entity: sensor.energy_dispatcher_optimization_plan
            name: Next Recommended Action
            icon: mdi:calendar-clock
        state_color: true
      
      # Smart Recommendations
      - type: entities
        title: 💡 Smart Recommendations
        icon: mdi:lightbulb-on
        entities:
          - type: section
            label: Appliances
          - entity: sensor.energy_dispatcher_dishwasher_optimal_time
            name: 🍽️ Dishwasher
            icon: mdi:dishwasher
            secondary_info: last-changed
          - entity: sensor.energy_dispatcher_washing_machine_optimal_time
            name: 👕 Washing Machine
            icon: mdi:washing-machine
            secondary_info: last-changed
          - type: section
            label: Electric Vehicle
          - entity: sensor.energy_dispatcher_ev_charging_recommendation
            name: 🚗 EV Charging
            icon: mdi:car-electric
            secondary_info: last-changed
          - type: section
            label: Load Shifting
          - entity: sensor.energy_dispatcher_load_shift_opportunity
            name: ⚡ Best Load Shift
            icon: mdi:clock-time-four
        state_color: true
  
  # Row 2: Cost Optimization
  - type: entities
    title: 📊 Cost Optimization
    icon: mdi:chart-line
    entities:
      - type: section
        label: Savings
      - entity: sensor.energy_dispatcher_estimated_savings_today
        name: Today's Savings
        icon: mdi:piggy-bank
      - entity: sensor.energy_dispatcher_estimated_savings_month
        name: This Month
        icon: mdi:cash-multiple
      - type: section
        label: Price Windows
      - entity: sensor.energy_dispatcher_next_cheap_period
        name: Next Cheap Period
        icon: mdi:clock-outline
      - entity: sensor.energy_dispatcher_next_high_cost_period
        name: Next High Cost Period
        icon: mdi:alert-circle
      - type: section
        label: Export Opportunities
      - entity: binary_sensor.energy_dispatcher_export_opportunity
        name: Export Recommended
        icon: mdi:transmission-tower-export
      - entity: sensor.energy_dispatcher_export_revenue_estimate
        name: Estimated Revenue
        icon: mdi:cash-plus
    state_color: true
  
  # Row 3: Price Chart
  - type: custom:apexcharts-card
    header:
      show: true
      title: 24h Price & Optimization Plan
      show_states: true
      colorize_states: true
    graph_span: 24h
    span:
      start: day
    series:
      - entity: sensor.nordpool_kwh_se3_sek_3_10_025
        name: Electricity Price
        type: column
        color: var(--primary-color)
        opacity: 0.3
        data_generator: |
          return entity.attributes.raw_today.concat(entity.attributes.raw_tomorrow || []).map((item) => {
            return [new Date(item.start), item.value];
          });
  
  # Row 4: Quick Actions
  - type: horizontal-stack
    cards:
      - type: button
        name: Force Charge
        icon: mdi:battery-charging
        icon_height: 40px
        tap_action:
          action: call-service
          service: energy_dispatcher.override_battery_mode
          data:
            mode: charge
            duration_minutes: 60
      
      - type: button
        name: Start EV
        icon: mdi:ev-station
        icon_height: 40px
        tap_action:
          action: call-service
          service: energy_dispatcher.start_ev_charging
          data:
            mode: optimal
      
      - type: button
        name: Export Mode
        icon: mdi:transmission-tower-export
        icon_height: 40px
        tap_action:
          action: call-service
          service: energy_dispatcher.set_export_mode
          data:
            mode: excess_solar_only
      
      - type: button
        name: Reset
        icon: mdi:restart
        icon_height: 40px
        tap_action:
          action: call-service
          service: energy_dispatcher.reset_optimizations
```

</details>

---

## Automation Examples

### 1. Notify When to Run Dishwasher

```yaml
alias: Notify Dishwasher Optimal Time
description: Send notification when it's a good time to run dishwasher
trigger:
  - platform: state
    entity_id: sensor.energy_dispatcher_dishwasher_optimal_time
condition:
  - condition: template
    value_template: >
      {{ (as_timestamp(now()) - as_timestamp(states('sensor.energy_dispatcher_dishwasher_optimal_time'))) | abs < 300 }}
action:
  - service: notify.mobile_app_your_phone
    data:
      title: 🍽️ Dishwasher Ready!
      message: >
        Great time to run the dishwasher now!
        Estimated cost: {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'estimated_cost_sek') }} SEK
        You'll save {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'cost_savings_vs_now_sek') }} SEK compared to your usual time.
      data:
        actions:
          - action: DISMISS
            title: Got it
```

### 2. Auto-Start EV Charging at Optimal Time

```yaml
alias: Auto Start EV Charging
description: Automatically start EV charging when optimal window begins
trigger:
  - platform: template
    value_template: >
      {% set optimal = states('sensor.energy_dispatcher_ev_charging_recommendation') %}
      {% set now = now().strftime('%H:%M') %}
      {{ optimal == now }}
condition:
  - condition: state
    entity_id: binary_sensor.ev_plugged_in
    state: 'on'
  - condition: state
    entity_id: input_boolean.ev_auto_charge_enabled
    state: 'on'
action:
  - service: switch.turn_on
    entity_id: switch.ev_charger_start
  - service: notify.mobile_app_your_phone
    data:
      title: 🚗 EV Charging Started
      message: >
        EV charging started automatically at optimal time.
        Estimated cost: {{ state_attr('sensor.energy_dispatcher_ev_charging_recommendation', 'estimated_cost_sek') }} SEK
```

### 3. Export Warning

```yaml
alias: Export Opportunity Alert
description: Notify when energy export is profitable
trigger:
  - platform: state
    entity_id: binary_sensor.energy_dispatcher_export_opportunity
    to: 'on'
condition:
  - condition: numeric_state
    entity_id: sensor.energy_dispatcher_export_revenue_estimate
    above: 5.0  # At least 5 SEK revenue
action:
  - service: notify.mobile_app_your_phone
    data:
      title: ⚡ Export Opportunity!
      message: >
        High spot price detected! Export energy now to earn {{ states('sensor.energy_dispatcher_export_revenue_estimate') }} SEK.
        Current price: {{ state_attr('binary_sensor.energy_dispatcher_export_opportunity', 'export_price_sek_per_kwh') }} SEK/kWh
      data:
        actions:
          - action: ENABLE_EXPORT
            title: Enable Export
          - action: DISMISS
            title: Dismiss
```

### 4. Daily Savings Summary

```yaml
alias: Daily Savings Summary
description: Send daily summary of cost savings
trigger:
  - platform: time
    at: '20:00:00'
action:
  - service: notify.mobile_app_your_phone
    data:
      title: 📊 Daily Energy Summary
      message: >
        Today's optimization savings: {{ states('sensor.energy_dispatcher_estimated_savings_today') }} SEK

        Breakdown:
        • Battery: {{ state_attr('sensor.energy_dispatcher_estimated_savings_today', 'battery_optimization_sek') }} SEK
        • EV Charging: {{ state_attr('sensor.energy_dispatcher_estimated_savings_today', 'ev_charging_optimization_sek') }} SEK
        • Appliances: {{ state_attr('sensor.energy_dispatcher_estimated_savings_today', 'appliance_scheduling_sek') }} SEK

        Month total: {{ states('sensor.energy_dispatcher_estimated_savings_month') }} SEK
```

---

## Troubleshooting

### Problem: Sensors Show "Unavailable"

**Solution**:
1. Check that Energy Dispatcher is properly configured
2. Verify you have at least 24 hours of price data
3. Restart Home Assistant: **Settings** → **System** → **Restart**
4. Check logs: **Settings** → **System** → **Logs** → Search for "energy_dispatcher"

### Problem: Recommendations Don't Update

**Solution**:
1. Check update interval in configuration (should update every 15 minutes)
2. Manually refresh: **Developer Tools** → **Services** → `homeassistant.update_entity`
3. Verify price sensor is updating correctly
4. Check solar forecast is available

### Problem: ApexCharts Card Not Working

**Solution**:
1. Ensure ApexCharts Card is installed via HACS
2. Clear browser cache: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
3. Check JavaScript console for errors: F12 → Console tab
4. Try simpler chart first without data_generator

### Problem: Buttons Don't Work

**Solution**:
1. Verify services exist: **Developer Tools** → **Services** → Search for "energy_dispatcher"
2. Test service manually in Developer Tools first
3. Check entity permissions and user role
4. Review automation/script logs for errors

### Problem: Savings Seem Inaccurate

**Solution**:
1. Verify baseline cost calculation is correct
2. Check that all sensors (battery, solar, consumption) are reporting correctly
3. Review calculation in sensor attributes for transparency
4. Compare with actual energy bill to calibrate

---

## Tips for Best Results

### 1. Customize for Your Needs

- **Remove unused appliances**: If you don't have a dishwasher, remove that card
- **Add custom appliances**: Use `energy_dispatcher.schedule_appliance` service for any device
- **Adjust notification times**: Set automations for times that work for you
- **Personalize thresholds**: Adjust cheap/high price thresholds in configuration

### 2. Learn the System

- **Monitor for a week**: Watch recommendations and see which ones work best
- **Check attribute details**: Tap sensors to see full reasoning
- **Track savings**: Compare estimated vs. actual savings over time
- **Provide feedback**: Use manual overrides when AI is wrong to teach preferences

### 3. Integrate with Existing Automations

- **Smart home integration**: Combine with other smart home automations
- **Voice control**: Use voice assistants to trigger overrides
- **Presence detection**: Adjust recommendations based on home/away status
- **Weather integration**: System already uses weather, but you can add manual adjustments

### 4. Advanced Optimization

- **Multiple vehicles**: Set up separate sensors for each EV
- **Time-of-use rates**: Configure if you have TOU pricing
- **Seasonal adjustments**: Modify thresholds seasonally (summer vs. winter)
- **Load profiles**: Fine-tune appliance power consumption values

---

## Next Steps

After setting up your dashboard:

1. ✅ **Test all buttons and controls**
2. ✅ **Monitor for 24 hours** to see recommendations in action
3. ✅ **Set up key automations** (at least dishwasher and EV notifications)
4. ✅ **Adjust thresholds** based on your energy prices
5. ✅ **Share feedback** to help improve the system

---

## Related Documentation

- [Cost Strategy and Battery Optimization Guide](cost_strategy_and_battery_optimization.md) - Deep dive into optimization logic
- [AI Optimization Implementation Guide](ai_optimization_implementation_guide.md) - For developers
- [Configuration Guide](configuration.md) - General configuration options
- [Dashboard Guide](dashboard_guide.md) - Original dashboard setup guide

---

**Questions or Issues?**

- 📚 Check documentation: `docs/` folder
- 💬 Community forum: [Home Assistant Community](https://community.home-assistant.io/)
- 🐛 Report bugs: GitHub Issues
- 💡 Feature requests: GitHub Discussions

---

**Enjoy your AI-powered energy optimization! 🤖⚡**
