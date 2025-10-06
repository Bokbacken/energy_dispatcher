# Energy Dispatcher - Dashboard Guide

This guide provides step-by-step instructions for creating a comprehensive Energy Dispatcher dashboard in Home Assistant. This dashboard is designed to be your primary control center, showing optimization progress, forecasts, and providing easy access to overrides and settings.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Where to Enter Different Code Types](#where-to-enter-different-code-types)
- [Step-by-Step Dashboard Creation](#step-by-step-dashboard-creation)
- [Main Dashboard Components](#main-dashboard-components)
- [Advanced Customization](#advanced-customization)
- [Troubleshooting](#troubleshooting)

## Overview

The main dashboard provides:
- **Quick Controls**: EV charge and battery charge overrides
- **Key Metrics**: Current prices, battery state, EV status
- **Forecasts**: Solar production and energy prices for today/tomorrow
- **Optimization Status**: Real-time view of what the system is doing
- **Point of Interest Values**: Showcase the integration's intelligence

## Prerequisites

Before creating your dashboard, ensure you have:
1. ✅ Energy Dispatcher integration installed and configured
2. ✅ At least one configuration cycle completed (sensors populated with data)
3. ✅ (Optional) HACS installed for custom cards like `apexcharts-card` and `mushroom-cards`

### Recommended HACS Cards

Install these from HACS → Frontend:
- **ApexCharts Card**: For beautiful, interactive graphs
- **Mushroom Cards**: For modern, touch-friendly controls
- **Button Card**: For custom action buttons
- **Multiple Entity Row**: For compact entity displays

To install: Go to **HACS** → **Frontend** → **Explore & Download Repositories** → Search for the card name

## Where to Enter Different Code Types

Understanding where to place different code snippets is crucial. Here's a quick reference:

| Code Type | Location | When to Use | Example |
|-----------|----------|-------------|---------|
| **Helpers** | Settings → Helpers → Create Helper | Manual input fields | Input number for manual EV SOC |
| **Dashboard Cards** | Dashboard → Edit → Add Card or Raw Config | Visual interface elements | ApexCharts, Entity cards |
| **Automations** | Settings → Automations → Create | Event-based actions | Auto-update EV SOC on plug-in |
| **Scripts** | Settings → Automations → Scripts | Reusable action sequences | Start optimal charging script |
| **configuration.yaml** | File Editor → configuration.yaml | Template sensors, global config | Custom template sensors |
| **Services** | Developer Tools → Services | Testing and debugging | Test service calls manually |

### Detailed Explanations

### 1. Helpers (Input Entities)

**Where**: Settings → Devices & Services → Helpers → Create Helper

**When to use**: Creating manual input fields for values not tracked by entities

**Example Use Cases**:
- Manual EV SOC input (if no API integration)
- Custom price thresholds
- Manual override flags

**How to create**:
1. Go to Settings → Devices & Services → Helpers
2. Click "+ CREATE HELPER"
3. Choose type (Input Number, Input Boolean, Input Text, etc.)
4. Configure name, icon, min/max values
5. Click "CREATE"

### 2. Dashboard YAML (Lovelace)

**Where**: Settings → Dashboards → [Your Dashboard] → Edit → Three Dots Menu → Raw Configuration Editor

**When to use**: Creating or editing dashboard cards and views

**Example Use Cases**:
- ApexCharts configuration
- Card layouts
- Entity cards
- Custom buttons

**How to enter**:
1. Go to your dashboard
2. Click the pencil icon (top right) to enter Edit mode
3. Click "+ ADD CARD" to add cards via UI, OR
4. Click "Three Dots Menu" → "Raw Configuration Editor" to paste YAML directly

### 3. configuration.yaml

**Where**: File editor or SSH access to `/config/configuration.yaml`

**When to use**: Creating automations, templates, sensors, or global configurations

**Example Use Cases**:
- Template sensors
- Automations
- Custom integrations
- Global settings

**How to enter**:
1. Go to Settings → Add-ons → File editor (install if needed)
2. Open `configuration.yaml`
3. Add your configuration under appropriate section
4. Click "SAVE"
5. Go to Developer Tools → YAML → Check Configuration
6. Click "Restart" to apply changes

**Important**: Always check configuration before restarting!

### 4. Automations

**Where**: Settings → Automations & Scenes → Create Automation

**When to use**: Creating automated actions based on triggers

**Example Use Cases**:
- Auto-update EV SOC when plugged in
- Send notifications when charging completes
- Adjust settings based on time or price

**How to create**:
1. Go to Settings → Automations & Scenes
2. Click "+ CREATE AUTOMATION"
3. Choose "Create new automation" or "Start with an empty automation"
4. Use UI to configure triggers, conditions, and actions, OR
5. Switch to YAML mode (Three Dots Menu → Edit in YAML) to paste code

### 5. Scripts

**Where**: Settings → Automations & Scenes → Scripts tab → Create Script

**When to use**: Creating reusable service call sequences

**Example Use Cases**:
- Start EV charging with specific settings
- Reset battery cost tracking
- Switch between charging modes

**How to create**:
1. Go to Settings → Automations & Scenes → Scripts tab
2. Click "+ ADD SCRIPT"
3. Configure using UI or YAML mode
4. Scripts can be called from dashboards or automations

## Step-by-Step Dashboard Creation

### Step 1: Create a New Dashboard

1. Go to **Settings** → **Dashboards**
2. Click **"+ ADD DASHBOARD"**
3. Choose **"New dashboard from scratch"**
4. Name it: "Energy Control Center"
5. Icon: `mdi:lightning-bolt`
6. Click **"CREATE"**

### Step 2: Add Title and Header Section

1. Click **"+ ADD CARD"**
2. Search for **"Markdown"**
3. Paste this content:

```yaml
type: markdown
content: |
  # ⚡ Energy Dispatcher Control Center
  Real-time energy optimization dashboard
```

### Step 3: Create Quick Controls Section

This section provides override buttons for manual control when needed.

#### Option A: Using UI (Easier for beginners)

1. Click **"+ ADD CARD"**
2. Search for **"Entities"**
3. Add these entities:
   - `switch.energy_dispatcher_auto_ev` (Auto EV control)
   - `switch.energy_dispatcher_auto_planner` (Auto Planner)
4. Set title: "System Controls"
5. Click "SAVE"

#### Option B: Using YAML (More control)

1. Click **"+ ADD CARD"** → **"Manual"** (at bottom)
2. Paste this YAML:

```yaml
type: entities
title: 🎮 Quick Controls
entities:
  - entity: switch.energy_dispatcher_auto_ev
    name: Auto EV Charging
    icon: mdi:car-electric
  - entity: switch.energy_dispatcher_auto_planner
    name: Auto Battery Planner
    icon: mdi:battery-charging
  - type: section
  - type: button
    name: Force EV Charge (1 hour)
    icon: mdi:flash
    tap_action:
      action: call-service
      service: energy_dispatcher.ev_force_charge
      data:
        duration: 60
        current: 16
  - type: button
    name: Pause EV Charge (30 min)
    icon: mdi:pause-circle
    tap_action:
      action: call-service
      service: energy_dispatcher.ev_pause
      data:
        duration: 30
  - type: button
    name: Force Battery Charge
    icon: mdi:battery-arrow-up
    tap_action:
      action: call-service
      service: energy_dispatcher.force_battery_charge
      data:
        power_w: 5000
        duration: 60
```

3. Click "SAVE"

### Step 4: Add Key Settings Panel

Display the most important settings for quick reference and adjustment.

1. Click **"+ ADD CARD"** → **"Entities"**
2. Add title: "⚙️ Essential Settings"
3. Add these entities:

```yaml
type: entities
title: ⚙️ Essential Settings
entities:
  - entity: number.energy_dispatcher_ev_aktuell_soc
    name: EV Current SOC
    icon: mdi:battery-charging-50
  - entity: number.energy_dispatcher_ev_mal_soc
    name: EV Target SOC
    icon: mdi:battery-charging-90
  - entity: number.energy_dispatcher_ev_batterikapacitet
    name: EV Battery Capacity
    icon: mdi:battery-high
  - type: section
    label: Battery Settings
  - entity: number.energy_dispatcher_hemmabatteri_kapacitet
    name: Home Battery Capacity
    icon: mdi:home-battery
  - entity: number.energy_dispatcher_hemmabatteri_soc_golv
    name: Battery SOC Floor
    icon: mdi:battery-low
```

### Step 5: Add Current Status Cards

Show real-time system status.

1. Click **"+ ADD CARD"** → **"Horizontal Stack"**
2. Add three **"Sensor"** cards inside:

```yaml
type: horizontal-stack
cards:
  - type: sensor
    entity: sensor.energy_dispatcher_enriched_power_price
    name: Current Price
    graph: line
    icon: mdi:cash
  - type: sensor
    entity: sensor.energy_dispatcher_battery_charging_state
    name: Battery Status
    icon: mdi:battery-charging
  - type: sensor
    entity: sensor.energy_dispatcher_ev_charging_session
    name: EV Session
    icon: mdi:car-electric
```

### Step 6: Add Price & Solar Forecast Graph

This is where ApexCharts shines! This graph shows today and tomorrow's forecast.

**Prerequisites**: Install `apexcharts-card` from HACS

1. Click **"+ ADD CARD"** → **"Custom: ApexCharts Card"** (or Manual)
2. Paste this configuration:

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
header:
  show: true
  title: 📊 Price & Solar Forecast (48h)
  show_states: true
  colorize_states: true
now:
  show: true
  label: Now
series:
  - entity: sensor.energy_dispatcher_enriched_power_price
    name: Electricity Price
    type: column
    color: '#FF6B6B'
    stroke_width: 2
    data_generator: |
      return entity.attributes.hourly.map((entry) => {
        return [new Date(entry.time).getTime(), entry.enriched];
      });
    show:
      in_header: true
      legend_value: false
  - entity: sensor.energy_dispatcher_solar_forecast_compensated
    name: Solar Forecast
    type: area
    color: '#FFA500'
    opacity: 0.3
    stroke_width: 2
    data_generator: |
      return entity.attributes.forecast.map((entry) => {
        return [new Date(entry[0]).getTime(), entry[1] / 1000];
      });
    show:
      in_header: true
      legend_value: false
  - entity: sensor.energy_dispatcher_solar_forecast_raw
    name: Solar Raw
    type: line
    color: '#FFD700'
    stroke_width: 1
    curve: smooth
    data_generator: |
      return entity.attributes.forecast.map((entry) => {
        return [new Date(entry[0]).getTime(), entry[1] / 1000];
      });
    show:
      in_header: false
      legend_value: false
yaxis:
  - id: price
    decimals: 2
    apex_config:
      title:
        text: 'Price (SEK/kWh)'
  - id: solar
    opposite: true
    decimals: 1
    apex_config:
      title:
        text: 'Solar (kW)'
```

**Note**: This graph shows:
- 🔴 Red bars: Electricity prices (left axis)
- 🟠 Orange area: Cloud-compensated solar forecast (right axis)
- 🟡 Yellow line: Raw solar forecast (right axis)
- ⚡ "Now" indicator: Current time marker

### Step 7: Add Point of Interest (POI) Values

Display key metrics that showcase the integration's intelligence.

1. Click **"+ ADD CARD"** → **"Glance"**
2. Configure:

```yaml
type: glance
title: 💡 Key Insights
columns: 3
entities:
  - entity: sensor.energy_dispatcher_solar_energy_forecast_today
    name: Solar Today
    icon: mdi:solar-power
  - entity: sensor.energy_dispatcher_solar_energy_forecast_tomorrow
    name: Solar Tomorrow
    icon: mdi:solar-power
  - entity: sensor.energy_dispatcher_battery_vs_grid_price_delta
    name: Battery vs Grid
    icon: mdi:scale-balance
  - entity: sensor.energy_dispatcher_battery_runtime
    name: Battery Runtime
    icon: mdi:timer
  - entity: sensor.energy_dispatcher_ev_time_until_charge
    name: EV Next Charge
    icon: mdi:clock-outline
  - entity: sensor.energy_dispatcher_battery_cost
    name: Battery Avg Cost
    icon: mdi:cash-check
```

### Step 8: Add Optimization Status

Show what the system is currently doing and why.

1. Click **"+ ADD CARD"** → **"Entities"**
2. Configure:

```yaml
type: entities
title: 🤖 Optimization Status
entities:
  - entity: sensor.energy_dispatcher_batt_charge_reason
    name: Battery Action Reason
    icon: mdi:information-outline
  - entity: sensor.energy_dispatcher_ev_charge_reason
    name: EV Charge Reason
    icon: mdi:information-outline
  - entity: sensor.energy_dispatcher_battery_power_flow
    name: Battery Power Flow
    icon: mdi:transmission-tower
  - entity: sensor.energy_dispatcher_batt_time_until_charge
    name: Battery Next Charge
    icon: mdi:clock-outline
```

### Step 9: Add Battery Energy Flow Graph

Visualize battery charging/discharging patterns.

```yaml
type: custom:apexcharts-card
graph_span: 24h
header:
  show: true
  title: 🔋 Battery Energy Flow (24h)
  show_states: true
now:
  show: true
  label: Now
series:
  - entity: sensor.energy_dispatcher_battery_power_flow
    name: Battery Power
    type: line
    color: '#4CAF50'
    stroke_width: 2
    curve: smooth
    show:
      in_header: true
yaxis:
  - id: power
    decimals: 2
    apex_config:
      title:
        text: 'Power (kW)'
```

### Step 10: Add EV Configuration Panel

Quick access to EV settings for multiple vehicles.

```yaml
type: entities
title: 🚗 Vehicle Settings
entities:
  - type: section
    label: Tesla Model Y
  - entity: number.energy_dispatcher_ev_aktuell_soc
    name: Current Charge
  - entity: number.energy_dispatcher_ev_mal_soc
    name: Target Charge
  - entity: number.energy_dispatcher_ev_batterikapacitet
    name: Battery Size
  - type: section
    label: Charger Settings
  - entity: number.energy_dispatcher_evse_max_a
    name: Max Current
  - entity: number.energy_dispatcher_evse_faser
    name: Phases
  - entity: number.energy_dispatcher_evse_spanning
    name: Voltage
```

## Main Dashboard Components

### Summary of What We Created

1. **Header**: Clear title and purpose
2. **Quick Controls**: Override switches and action buttons
3. **Essential Settings**: Most important configuration values
4. **Current Status**: Real-time system state
5. **Price & Solar Forecast**: 48-hour forecast visualization
6. **Key Insights**: POI values showcasing intelligence
7. **Optimization Status**: What the system is doing and why
8. **Battery Flow**: Energy movement visualization
9. **Vehicle Settings**: EV configuration panel

### Complete Dashboard YAML

If you prefer to create the entire dashboard at once, here's the complete configuration:

1. Go to your dashboard → Edit mode → Three Dots → Raw Configuration Editor
2. Paste the complete YAML below:

<details>
<summary>Click to expand complete dashboard YAML</summary>

```yaml
views:
  - title: Energy Control
    icon: mdi:lightning-bolt
    cards:
      # Header
      - type: markdown
        content: |
          # ⚡ Energy Dispatcher Control Center
          Real-time energy optimization dashboard

      # Quick Controls
      - type: entities
        title: 🎮 Quick Controls
        entities:
          - entity: switch.energy_dispatcher_auto_ev
            name: Auto EV Charging
            icon: mdi:car-electric
          - entity: switch.energy_dispatcher_auto_planner
            name: Auto Battery Planner
            icon: mdi:battery-charging
          - type: section
          - type: button
            name: Force EV Charge (1 hour)
            icon: mdi:flash
            tap_action:
              action: call-service
              service: energy_dispatcher.ev_force_charge
              data:
                duration: 60
                current: 16
          - type: button
            name: Pause EV Charge (30 min)
            icon: mdi:pause-circle
            tap_action:
              action: call-service
              service: energy_dispatcher.ev_pause
              data:
                duration: 30
          - type: button
            name: Force Battery Charge
            icon: mdi:battery-arrow-up
            tap_action:
              action: call-service
              service: energy_dispatcher.force_battery_charge
              data:
                power_w: 5000
                duration: 60

      # Current Status Cards
      - type: horizontal-stack
        cards:
          - type: sensor
            entity: sensor.energy_dispatcher_enriched_power_price
            name: Current Price
            graph: line
            icon: mdi:cash
          - type: sensor
            entity: sensor.energy_dispatcher_battery_charging_state
            name: Battery Status
            icon: mdi:battery-charging
          - type: sensor
            entity: sensor.energy_dispatcher_ev_charging_session
            name: EV Session
            icon: mdi:car-electric

      # Price & Solar Forecast Graph
      - type: custom:apexcharts-card
        graph_span: 48h
        span:
          start: day
        header:
          show: true
          title: 📊 Price & Solar Forecast (48h)
          show_states: true
          colorize_states: true
        now:
          show: true
          label: Now
        series:
          - entity: sensor.energy_dispatcher_enriched_power_price
            name: Electricity Price
            type: column
            color: '#FF6B6B'
            stroke_width: 2
            data_generator: |
              return entity.attributes.hourly.map((entry) => {
                return [new Date(entry.time).getTime(), entry.enriched];
              });
            show:
              in_header: true
              legend_value: false
          - entity: sensor.energy_dispatcher_solar_forecast_compensated
            name: Solar Forecast
            type: area
            color: '#FFA500'
            opacity: 0.3
            stroke_width: 2
            data_generator: |
              return entity.attributes.forecast.map((entry) => {
                return [new Date(entry[0]).getTime(), entry[1] / 1000];
              });
            show:
              in_header: true
              legend_value: false
        yaxis:
          - id: price
            decimals: 2
            apex_config:
              title:
                text: 'Price (SEK/kWh)'
          - id: solar
            opposite: true
            decimals: 1
            apex_config:
              title:
                text: 'Solar (kW)'

      # Key Insights
      - type: glance
        title: 💡 Key Insights
        columns: 3
        entities:
          - entity: sensor.energy_dispatcher_solar_energy_forecast_today
            name: Solar Today
            icon: mdi:solar-power
          - entity: sensor.energy_dispatcher_solar_energy_forecast_tomorrow
            name: Solar Tomorrow
            icon: mdi:solar-power
          - entity: sensor.energy_dispatcher_battery_vs_grid_price_delta
            name: Battery vs Grid
            icon: mdi:scale-balance
          - entity: sensor.energy_dispatcher_battery_runtime
            name: Battery Runtime
            icon: mdi:timer
          - entity: sensor.energy_dispatcher_ev_time_until_charge
            name: EV Next Charge
            icon: mdi:clock-outline
          - entity: sensor.energy_dispatcher_battery_cost
            name: Battery Avg Cost
            icon: mdi:cash-check

      # Optimization Status
      - type: entities
        title: 🤖 Optimization Status
        entities:
          - entity: sensor.energy_dispatcher_batt_charge_reason
            name: Battery Action Reason
            icon: mdi:information-outline
          - entity: sensor.energy_dispatcher_ev_charge_reason
            name: EV Charge Reason
            icon: mdi:information-outline
          - entity: sensor.energy_dispatcher_battery_power_flow
            name: Battery Power Flow
            icon: mdi:transmission-tower
          - entity: sensor.energy_dispatcher_batt_time_until_charge
            name: Battery Next Charge
            icon: mdi:clock-outline

      # Essential Settings
      - type: entities
        title: ⚙️ Essential Settings
        entities:
          - entity: number.energy_dispatcher_ev_aktuell_soc
            name: EV Current SOC
            icon: mdi:battery-charging-50
          - entity: number.energy_dispatcher_ev_mal_soc
            name: EV Target SOC
            icon: mdi:battery-charging-90
          - entity: number.energy_dispatcher_ev_batterikapacitet
            name: EV Battery Capacity
            icon: mdi:battery-high
          - type: section
            label: Battery Settings
          - entity: number.energy_dispatcher_hemmabatteri_kapacitet
            name: Home Battery Capacity
            icon: mdi:home-battery
          - entity: number.energy_dispatcher_hemmabatteri_soc_golv
            name: Battery SOC Floor
            icon: mdi:battery-low

      # Vehicle Settings
      - type: entities
        title: 🚗 Vehicle Settings
        entities:
          - type: section
            label: Charger Settings
          - entity: number.energy_dispatcher_evse_max_a
            name: Max Current
          - entity: number.energy_dispatcher_evse_faser
            name: Phases
          - entity: number.energy_dispatcher_evse_spanning
            name: Voltage
```

</details>

## Advanced Customization

### Adding Custom Helpers for Manual Override

Create helpers for additional manual controls:

1. Go to **Settings** → **Devices & Services** → **Helpers**
2. Click **"+ CREATE HELPER"**
3. Choose **"Number"**
4. Configure:
   - **Name**: "Manual Price Override"
   - **Icon**: `mdi:cash-edit`
   - **Min**: 0
   - **Max**: 10
   - **Step**: 0.1
   - **Unit**: SEK/kWh

### Creating an Automation for EV SOC Updates

Automatically update EV SOC when the car connects:

**Method 1: Via UI**
1. Go to **Settings** → **Automations & Scenes**
2. Click **"+ CREATE AUTOMATION"**
3. Configure trigger: State change of charger connection sensor
4. Configure action: Call service `energy_dispatcher.set_manual_ev`

**Method 2: Via configuration.yaml**

Add to your `configuration.yaml`:

```yaml
automation:
  - alias: "Update EV SOC on Connect"
    trigger:
      - platform: state
        entity_id: binary_sensor.wallbox_connected
        to: "on"
    action:
      - service: energy_dispatcher.set_manual_ev
        data:
          soc_current: "{{ states('input_number.manual_ev_soc') | float }}"
          soc_target: "{{ states('number.energy_dispatcher_ev_mal_soc') | float }}"
```

### Creating Scripts for Common Actions

Create a script to start optimal EV charging:

1. Go to **Settings** → **Automations & Scenes** → **Scripts**
2. Click **"+ ADD SCRIPT"**
3. Name: "Start Optimal EV Charge"
4. Add actions:

```yaml
sequence:
  - service: switch.turn_on
    target:
      entity_id: switch.energy_dispatcher_auto_ev
  - service: notify.mobile_app
    data:
      message: "EV charging optimization started"
      title: "Energy Dispatcher"
```

### Multiple Vehicle Dashboard

If you have multiple vehicles, you can create separate tabs or cards for each:

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      ## 🚗 Tesla Model Y
  - type: entities
    entities:
      - entity: number.energy_dispatcher_ev_aktuell_soc
        name: Current SOC
      - entity: number.energy_dispatcher_ev_mal_soc
        name: Target SOC
      - entity: sensor.energy_dispatcher_ev_time_until_charge
        name: Next Charge
  
  - type: markdown
    content: |
      ## 🚙 Hyundai Ioniq
  - type: entities
    entities:
      # Add second vehicle entities here when multi-vehicle support is fully implemented
```

## Troubleshooting

### Entities Not Showing

**Problem**: Entities don't appear in the dashboard

**Solutions**:
1. Check that Energy Dispatcher integration is loaded: **Settings** → **Devices & Services** → Look for "Energy Dispatcher"
2. Verify sensors have data: **Developer Tools** → **States** → Search for `energy_dispatcher`
3. Restart Home Assistant if entities were just created
4. Check entity names match exactly (case-sensitive)

**Entity Naming Pattern**: All Energy Dispatcher entities follow this pattern:
- Sensors: `sensor.energy_dispatcher_<description>` (e.g., `sensor.energy_dispatcher_enriched_power_price`)
- Numbers: `number.energy_dispatcher_<description>` (e.g., `number.energy_dispatcher_ev_aktuell_soc`)
- Switches: `switch.energy_dispatcher_<description>` (e.g., `switch.energy_dispatcher_auto_ev`)

To find all entities: Go to **Developer Tools** → **States** → Filter by `energy_dispatcher`

### ApexCharts Not Working

**Problem**: "Custom element doesn't exist: apexcharts-card"

**Solutions**:
1. Install apexcharts-card from HACS: **HACS** → **Frontend** → Search "ApexCharts"
2. Clear browser cache (Ctrl+F5 or Cmd+Shift+R)
3. Restart Home Assistant
4. Check that HACS is properly installed

### Graphs Show No Data

**Problem**: Graphs are empty or show "No data"

**Solutions**:
1. Verify sensor has `forecast` or `hourly` attributes: **Developer Tools** → **States** → Select sensor → Check attributes
2. Wait for at least one update cycle (5-10 minutes)
3. Check that `data_generator` matches your sensor's attribute structure
4. Review Home Assistant logs for errors: **Settings** → **System** → **Logs**

### Service Calls Not Working

**Problem**: Buttons don't trigger actions

**Solutions**:
1. Check service exists: **Developer Tools** → **Services** → Search for service name
2. Verify data format matches service requirements
3. Check Home Assistant logs for service call errors
4. Test service manually in Developer Tools first

### Sensors Show "Unavailable"

**Problem**: Sensors show as unavailable or unknown

**Solutions**:
1. Check integration configuration: **Settings** → **Devices & Services** → Energy Dispatcher → **CONFIGURE**
2. Verify required entities (Nordpool sensor, battery SOC, etc.) are available
3. Check that data sources (Forecast.Solar API, Nordpool, etc.) are responding
4. Review integration logs for specific errors

### Dashboard Layout Issues

**Problem**: Cards overlap or don't fit properly

**Solutions**:
1. Use **Horizontal Stack** or **Vertical Stack** cards to organize layout
2. Adjust card widths using `view_layout` property
3. Switch to mobile view to test responsive design
4. Use grid layout for more control: Set view to `type: panel` with masonry layout

## Next Steps

After creating your main dashboard:

1. **Test the Controls**: Try each button and switch to ensure they work
2. **Monitor for 24 Hours**: Watch the forecasts and optimization decisions
3. **Adjust Settings**: Fine-tune SOC targets, price thresholds, etc.
4. **Create Automations**: Set up automatic SOC updates and notifications
5. **Add More Views**: Create additional dashboard tabs for detailed analysis

## See Also

- [Configuration Guide](./configuration.md) - Detailed configuration options
- [Multi-Vehicle Setup](./multi_vehicle_setup.md) - Setting up multiple EVs
- [Battery Cost Tracking](./battery_cost_tracking.md) - Understanding battery economics
- [Future Improvements](./future_improvements.md) - Planned usability enhancements
- [Quick Reference](./QUICK_REFERENCE.md) - Quick command reference

## Looking Ahead

**Want less manual configuration?** See the [Future Improvements](./future_improvements.md) document for planned features that will:
- 🚀 Auto-generate dashboards with one click
- 🔍 Auto-discover compatible devices
- 🤖 Integrate directly with vehicle APIs (Tesla, VW ID, etc.)
- 🎨 Provide visual dashboard builder in the UI
- ⚡ Eliminate need for YAML knowledge

These improvements will make Energy Dispatcher even easier to use, but for now, this guide will help you create a powerful control dashboard.

## Feedback

This dashboard is designed for ease of use and understanding. If you have suggestions for improvements or find something unclear, please open an issue on [GitHub](https://github.com/Bokbacken/energy_dispatcher/issues).

**Want to contribute?** Check out the [Future Improvements](./future_improvements.md) document for areas where you can help make the integration more user-friendly!
