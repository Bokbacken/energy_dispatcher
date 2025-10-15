# Quick Dashboard Reference for Energy Dispatcher v0.10.1

**TL;DR**: Copy-paste YAML snippets to create your monitoring and control dashboard.

---

## 🎯 Essential Dashboard Cards

### 1. Status Overview (Must Have)

```yaml
type: entities
title: 🤖 Energy Dispatcher Status
entities:
  - entity: sensor.energy_dispatcher_cost_level
    name: Price Level
    icon: mdi:currency-eur
  - entity: sensor.energy_dispatcher_battery_reserve
    name: Battery Reserve Target
    icon: mdi:battery-50
  - entity: sensor.energy_dispatcher_next_high_cost_window
    name: Next Expensive Period
    icon: mdi:clock-alert
state_color: true
```

**What it shows**: Current price classification, recommended battery reserve, when next expensive period starts.

---

### 2. Battery Control & Monitoring

```yaml
type: entities
title: 🔋 Battery Management
entities:
  - entity: sensor.energy_dispatcher_battery_cost
    name: Energy Cost (WACE)
  - entity: sensor.energy_dispatcher_battery_vs_grid_delta
    name: vs Current Grid Price
  - entity: sensor.energy_dispatcher_battery_charging_state
    name: Current Action
  - entity: sensor.energy_dispatcher_battery_power_flow
    name: Power Flow
  - entity: sensor.energy_dispatcher_batt_time_until_charge
    name: Next Charge Window
  - type: divider
  - type: button
    name: Force Charge (5kW for 1h)
    icon: mdi:battery-charging-high
    tap_action:
      action: call-service
      service: energy_dispatcher.force_battery_charge
      service_data:
        power_w: 5000
        duration: 60
  - type: button
    name: Hold Battery (2h)
    icon: mdi:pause-circle
    tap_action:
      action: call-service
      service: energy_dispatcher.override_battery_mode
      service_data:
        mode: hold
        duration_minutes: 120
  - type: button
    name: Auto Mode
    icon: mdi:auto-fix
    tap_action:
      action: call-service
      service: energy_dispatcher.override_battery_mode
      service_data:
        mode: auto
```

**Actions available**:
- Force charging at specified power/duration
- Override to hold/charge/discharge/auto modes
- Reset battery energy cost
- Manual SOC adjustment

---

### 3. EV Charging Control

```yaml
type: entities
title: 🚗 EV Charging
entities:
  - entity: sensor.energy_dispatcher_ev_time_until_charge
    name: Next Charge Window
  - entity: sensor.energy_dispatcher_ev_charge_reason
    name: Why Charging/Not Charging
  - entity: sensor.energy_dispatcher_ev_charging_session
    name: Current Session
  - entity: number.energy_dispatcher_ev_target_soc
    name: Target SOC
  - entity: select.energy_dispatcher_ev_mode
    name: Charging Mode
  - type: divider
  - type: button
    name: Force Charge (16A, 1h)
    icon: mdi:car-electric
    tap_action:
      action: call-service
      service: energy_dispatcher.ev_force_charge
      service_data:
        duration: 60
        current: 16
  - type: button
    name: Pause Charging (30min)
    icon: mdi:pause
    tap_action:
      action: call-service
      service: energy_dispatcher.ev_pause
      service_data:
        duration: 30
```

**Modes available**: ASAP, Eco, Deadline, Cost Saver

---

### 4. Smart Recommendations (When Enabled)

```yaml
type: entities
title: 💡 Cost-Saving Suggestions
icon: mdi:lightbulb-on
entities:
  - entity: sensor.energy_dispatcher_dishwasher_optimal_time
    name: 🍽️ Dishwasher
    secondary_info: attribute
    attribute: cost_savings_vs_now_sek
  - entity: sensor.energy_dispatcher_washing_machine_optimal_time
    name: 👕 Washing Machine
    secondary_info: attribute
    attribute: cost_savings_vs_now_sek
  - entity: sensor.energy_dispatcher_water_heater_optimal_time
    name: 💧 Water Heater
    secondary_info: attribute
    attribute: cost_savings_vs_now_sek
  - type: divider
  - entity: sensor.energy_dispatcher_load_shift_opportunity
    name: ⚡ Load Shift
  - entity: sensor.energy_dispatcher_load_shift_savings
    name: Potential Savings
  - type: divider
  - entity: binary_sensor.energy_dispatcher_export_opportunity
    name: 💰 Export Now?
  - entity: sensor.energy_dispatcher_export_revenue_estimate
    name: Estimated Revenue
state_color: true
```

**Note**: These sensors only appear when features are enabled in configuration.

---

### 5. Solar Production & Forecast

```yaml
type: entities
title: ☀️ Solar Production
entities:
  - entity: sensor.solar_power_now
    name: Current Production
    icon: mdi:solar-power
  - entity: sensor.solar_energy_today
    name: Today's Total
  - entity: sensor.solar_energy_tomorrow
    name: Tomorrow's Forecast
  - type: divider
  - entity: sensor.solar_forecast_raw
    name: Raw Forecast
  - entity: sensor.solar_forecast_compensated
    name: Weather-Adjusted
  - entity: sensor.weather_forecast_capabilities
    name: Weather Data Available
```

---

### 6. Price Graph (ApexCharts)

**Requires HACS: ApexCharts Card**

```yaml
type: custom:apexcharts-card
header:
  title: 📊 Electricity Prices (24h)
  show: true
graph_span: 24h
span:
  start: day
now:
  show: true
  label: Now
series:
  - entity: sensor.nordpool_kwh_se3_sek_3_10_025
    name: Total Price
    stroke_width: 2
    type: line
    color: '#2196F3'
    show:
      legend_value: false
  - entity: sensor.energy_dispatcher_cost_level
    name: Level
    type: column
    color: '#FF9800'
    transform: |
      return x === 'CHEAP' ? 0.5 : (x === 'MEDIUM' ? 1 : 1.5);
```

**Alternative without ApexCharts**:
```yaml
type: history-graph
title: Electricity Prices
hours_to_show: 24
entities:
  - entity: sensor.nordpool_kwh_se3_sek_3_10_025
  - entity: sensor.energy_dispatcher_cost_level
```

---

## 🎛️ Quick Action Panel

Horizontal button strip for common actions:

```yaml
type: horizontal-stack
cards:
  - type: button
    name: Reset Battery Cost
    icon: mdi:battery-sync
    tap_action:
      action: call-service
      service: energy_dispatcher.battery_cost_reset
  - type: button
    name: Force Charge
    icon: mdi:battery-charging-high
    tap_action:
      action: call-service
      service: energy_dispatcher.force_battery_charge
      service_data:
        power_w: 5000
        duration: 60
  - type: button
    name: EV Charge Now
    icon: mdi:car-electric
    tap_action:
      action: call-service
      service: energy_dispatcher.ev_force_charge
      service_data:
        duration: 60
        current: 16
  - type: button
    name: Enable Export
    icon: mdi:transmission-tower-export
    tap_action:
      action: call-service
      service: energy_dispatcher.set_export_mode
      service_data:
        mode: peak_price_opportunistic
        min_export_price: 3.0
```

---

## 🔔 Useful Automations

### 1. Notify When Appliance Optimal Time

```yaml
automation:
  - alias: "Energy: Dishwasher Optimal Time"
    trigger:
      - platform: state
        entity_id: sensor.energy_dispatcher_dishwasher_optimal_time
    condition:
      - condition: template
        value_template: >
          {{ (as_timestamp(now()) - as_timestamp(trigger.to_state.state)) | abs < 300 }}
    action:
      - service: notify.mobile_app
        data:
          title: "💡 Dishwasher Ready"
          message: >
            Optimal time to run dishwasher is now!
            Save {{ state_attr('sensor.energy_dispatcher_dishwasher_optimal_time', 'cost_savings_vs_now_sek') }} SEK
```

### 2. Auto-Charge Battery During Cheap Hours

```yaml
automation:
  - alias: "Energy: Auto Charge Battery When Cheap"
    trigger:
      - platform: state
        entity_id: sensor.energy_dispatcher_cost_level
        to: 'CHEAP'
    condition:
      - condition: numeric_state
        entity_id: sensor.battery_soc
        below: 80
    action:
      - service: energy_dispatcher.force_battery_charge
        data:
          power_w: 5000
          duration: 120
```

### 3. Alert High Cost Period Coming

```yaml
automation:
  - alias: "Energy: Alert High Cost Period"
    trigger:
      - platform: state
        entity_id: sensor.energy_dispatcher_next_high_cost_window
    condition:
      - condition: template
        value_template: >
          {{ (as_timestamp(states('sensor.energy_dispatcher_next_high_cost_window')) - as_timestamp(now())) < 3600 }}
    action:
      - service: notify.mobile_app
        data:
          title: "⚡ High Price Alert"
          message: >
            Expensive electricity in less than 1 hour.
            Current reserve: {{ states('sensor.energy_dispatcher_battery_reserve') }}%
```

---

## 📍 Where to Add This Code

### For Dashboard Cards

1. Go to **Home Assistant** → **Dashboards**
2. Click **⋮** (three dots) → **Edit Dashboard**
3. Click **+ ADD CARD**
4. Click **Show Code Editor** (bottom left)
5. Paste the YAML
6. Click **SAVE**

### For Automations

1. Go to **Settings** → **Automations & Scenes**
2. Click **+ CREATE AUTOMATION**
3. Click **⋮** (three dots) → **Edit in YAML**
4. Paste the YAML
5. Click **SAVE**

### For Manual YAML Files

Add to your configuration:
- Dashboard YAML: `ui-lovelace.yaml` or via UI editor
- Automations: `automations.yaml`
- Scripts: `scripts.yaml`

---

## 🎨 Recommended HACS Cards

For the best dashboard experience, install these from HACS:

1. **ApexCharts Card** - Beautiful price graphs
2. **Mushroom Cards** - Modern entity cards
3. **Button Card** - Customizable action buttons
4. **Multiple Entity Row** - Compact displays
5. **Card Mod** - Advanced styling

**Installation**: HACS → Frontend → Explore & Download Repositories

---

## 🔧 Common Customizations

### Change Price Thresholds

```yaml
# Via Developer Tools → Services
service: energy_dispatcher.set_cost_thresholds
data:
  cheap_max: 1.0  # SEK/kWh
  high_min: 2.5   # SEK/kWh
```

### Adjust Battery Reserve

Use the number entity directly or:
```yaml
service: number.set_value
target:
  entity_id: number.energy_dispatcher_battery_floor
data:
  value: 30  # Percent
```

### Set EV Charging Mode

```yaml
service: select.select_option
target:
  entity_id: select.energy_dispatcher_ev_mode
data:
  option: "Cost Saver"
# Options: ASAP, Eco, Deadline, Cost Saver
```

---

## 📚 Full Documentation

For complete details, see:
- 📖 [WHERE_WE_ARE_NOW.md](./WHERE_WE_ARE_NOW.md) - Complete feature overview
- 📖 [Dashboard Setup Guide](./docs/dashboard_guide.md) - Comprehensive tutorial
- 📖 [AI Optimization Dashboard](./docs/ai_optimization_dashboard_guide.md) - Advanced features
- 📖 [Getting Started Guide](./docs/getting_started.md) - 10-minute quick start
- 📖 [Configuration Guide](./docs/configuration.md) - All settings explained

---

## 🆘 Troubleshooting

### Sensors Showing "Unknown"
- Check that source sensors (Nordpool, battery SOC) are working
- Wait 5-10 minutes for first data update
- Check entity IDs match your configuration

### Recommendations Not Appearing
- Ensure features are enabled in integration options
- Check that required sensors are configured (price, solar, load)
- Verify minimum thresholds are met (load ≥ 500W for shifting)

### Automations Not Triggering
- Check conditions are met (price level, SOC, time)
- Verify entity IDs are correct
- Test manually via Developer Tools → Services

### Dashboard Cards Not Working
- Install required HACS cards if using custom cards
- Check YAML syntax (use YAML validator)
- Verify entity IDs exist in Developer Tools → States

---

**Version**: 0.10.1  
**Last Updated**: 2025-10-15  
**Quick Help**: See [Getting Started Guide](./docs/getting_started.md)
