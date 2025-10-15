# Energy Dispatcher: Where We Are Now

**Current Version**: 0.10.1  
**Last Updated**: 2025-10-15  
**Status**: Production Ready with Advanced Features

---

## Executive Summary

Energy Dispatcher has evolved into a comprehensive intelligent energy management system for Home Assistant. This document provides a clear overview of what's **actually working now** versus what's planned for the future.

### 🎯 Core Purpose
Minimize electricity costs by intelligently managing:
- Battery charging/discharging based on spot prices
- EV charging optimization
- Solar production forecasting
- Energy export decisions
- Appliance scheduling recommendations

---

## ✅ What's Working Now (v0.10.1)

### 1. 🔋 Battery Management & Cost Optimization

**Status**: ✅ **FULLY WORKING**

#### Battery Cost Tracking (BEC Module)
- **Tracks weighted average cost of energy (WACE)** stored in battery
- **Historical tracking**: 30 days of charge/discharge events (15-min intervals)
- **Source tracking**: Distinguishes grid vs solar charging
- **Automatic cost calculation** during charge/discharge
- **Persistent storage** across Home Assistant restarts (Storage Version 2)
- **Manual controls**:
  - `battery_cost_reset` service: Reset WACE to zero
  - `battery_cost_set_soc` service: Manually set battery SOC
  - Reset button entity available in UI

**Sensors**:
- `sensor.energy_dispatcher_battery_cost`: Shows WACE and SOC with historical statistics
- `sensor.energy_dispatcher_battery_vs_grid_delta`: Compares battery cost vs current grid price

#### Cost Strategy
- **Dynamic price classification**: Cheap/Medium/High based on percentiles (25th/75th)
- **High-cost window prediction**: 24-hour ahead forecast
- **Battery reserve calculation**: Prevents premature depletion before expensive periods
- **Smart charge/discharge decisions** based on price and solar availability

**Sensors**:
- `sensor.energy_dispatcher_cost_level`: Current price classification
- `sensor.energy_dispatcher_battery_reserve`: Recommended reserve percentage
- `sensor.energy_dispatcher_next_high_cost_window`: When next expensive period starts

**How it works**:
1. Classifies hourly prices into cheap/medium/high tiers
2. Predicts high-cost windows in next 24 hours
3. Calculates battery reserve needed to cover high-cost periods
4. Recommends charging during cheap hours, holding/discharging during expensive hours

### 2. 🚗 EV Charging Optimization

**Status**: ✅ **FULLY WORKING**

#### Multi-Vehicle Support
- **Multiple EVs** with different specifications
- **Vehicle presets**: Tesla Model Y LR 2022, Hyundai Ioniq Electric 2019
- **Per-vehicle state tracking**: SOC, target, mode, deadline
- **Charging session management**: start/end tracking, energy delivered
- **Vehicle-charger association** management

#### Charging Modes
- **ASAP Mode**: Immediate charging for urgent needs
- **Eco Mode**: Optimize for solar and cheap grid hours
- **Deadline Mode**: Meet specific completion time requirements
- **Cost Saver Mode**: Minimize cost with flexible timing

**Sensors**:
- `sensor.energy_dispatcher_ev_time_until_charge`: Countdown to next charge window
- `sensor.energy_dispatcher_ev_charge_reason`: Explanation of charging decision
- `sensor.energy_dispatcher_ev_charging_session`: Current session details

**Services**:
- `energy_dispatcher.set_manual_ev`: Update EV SOC and target
- `energy_dispatcher.ev_force_charge`: Force charge for specified duration/current
- `energy_dispatcher.ev_pause`: Pause charging for specified duration

**Adapters**:
- ✅ Generic EVSE adapter (manual control)
- ✅ Huawei EMMA adapter
- 🔌 Extensible adapter pattern for future chargers

### 3. ☀️ Solar Forecasting

**Status**: ✅ **FULLY WORKING** (Two Engines Available)

#### Option 1: Forecast.Solar Integration (External API)
- **Cloud compensation feature**: Adjusts forecast based on weather
- **User-configurable factors** for 0% and 100% cloud cover
- **Two sensors exposed**:
  - `sensor.solar_forecast_raw`: Unmodified API forecast
  - `sensor.solar_forecast_compensated`: Weather-adjusted forecast
- **Attributes include**: cloud coverage, weather entity, adjustment factors

**Configuration**:
- Select weather entity for cloud data
- Set output factors for clear/cloudy conditions
- Configure location (defaults to Home Assistant home)
- Optional API key for enhanced features

#### Option 2: Manual PV Forecast Engine (Physics-Based)
- **Free alternative** using Home Assistant weather data
- **No API costs** or external dependencies
- **Tier-based weather adaptation**: DNI/DHI → GHI → Cloud cover
- **Industry-standard models**:
  - Haurwitz: Clear-sky GHI calculation
  - Kasten-Czeplak: Cloud cover to GHI mapping
  - Erbs: GHI decomposition to DNI/DHI
  - HDKR: Plane-of-array transposition
  - PVWatts: DC/AC power with temperature effects
- **Built-in horizon blocking**: 12-point interpolation
- **Cell temperature modeling** with wind cooling
- **Configurable settings**: time step, sky-view factor, temperature coefficient

**Sensors**:
- `sensor.weather_forecast_capabilities`: Shows available weather data fields
- `sensor.solar_power_now`: Current solar production
- `sensor.solar_energy_today`: Today's total production
- `sensor.solar_energy_tomorrow`: Tomorrow's forecast
- `sensor.solar_delta_15m`: 15-minute production delta

**When to use which**:
- **Forecast.Solar**: Easy setup, accurate for most cases, requires API
- **Manual Engine**: Free, customizable, requires weather integration with good data

### 4. 📊 Appliance Scheduling Recommendations

**Status**: ✅ **WORKING** (Requires Configuration)

#### Supported Appliances
- Dishwasher
- Washing machine
- Water heater
- Custom appliances (configurable)

**Intelligence**:
- Analyzes 24-hour price forecast
- Considers solar production windows
- Accounts for user time constraints
- Calculates cost savings vs immediate use
- Provides multiple alternative times
- Confidence levels for recommendations

**Sensors** (when enabled):
- `sensor.energy_dispatcher_dishwasher_optimal_time`
- `sensor.energy_dispatcher_washing_machine_optimal_time`
- `sensor.energy_dispatcher_water_heater_optimal_time`

**Attributes include**:
- `estimated_cost_sek`: Cost at optimal time
- `cost_savings_vs_now_sek`: How much you save
- `reason`: Human-readable explanation
- `price_at_optimal_time`: Price (SEK/kWh)
- `solar_available`: Whether solar will be available
- `alternative_times`: Other good options
- `confidence`: Recommendation confidence level

**Service**:
- `energy_dispatcher.schedule_appliance`: Get optimal time for any appliance with custom power/duration

### 5. 💰 Export Profitability Analysis

**Status**: ✅ **WORKING** (Conservative by Default)

#### Export Modes
- **never**: Don't export (default - selling price typically too low)
- **excess_solar_only**: Only export when battery full + excess solar
- **peak_price_opportunistic**: Export during exceptionally high prices

**Analysis includes**:
- Battery degradation cost calculation
- Opportunity cost analysis
- Revenue estimation
- Duration estimates

**Sensors** (when export mode enabled):
- `binary_sensor.energy_dispatcher_export_opportunity`: Whether to export now
- `sensor.energy_dispatcher_export_revenue_estimate`: Estimated revenue

**Service**:
- `energy_dispatcher.set_export_mode`: Configure export behavior and minimum price

**How it works**:
1. Monitors current electricity prices
2. Calculates net revenue after degradation costs
3. Checks battery SOC and solar excess
4. Only recommends export when clearly profitable
5. Automatically disables after export window

### 6. 📈 Load Shifting & Peak Shaving

**Status**: ✅ **WORKING** (Requires Configuration)

#### Load Shifting
**Purpose**: Identifies opportunities to shift flexible loads to cheaper periods

**Configuration**:
- `enable_load_shifting`: Enable/disable feature
- `load_shift_flexibility_hours`: How far ahead to suggest (1-24h)
- `baseline_load_w`: Always-on baseline (loads above this are shiftable)

**Sensors**:
- `sensor.energy_dispatcher_load_shift_opportunity`: Best shift opportunity
- `sensor.energy_dispatcher_load_shift_savings`: Potential savings

**Requirements**:
- Flexible load ≥ 500W
- Price difference ≥ 0.5 SEK/kWh
- Configured load power sensor

#### Peak Shaving
**Purpose**: Uses battery to cap grid import during peak demand

**Configuration**:
- `enable_peak_shaving`: Enable/disable feature
- `peak_threshold_w`: Grid import threshold (1000-50000W)

**How it works**:
1. Monitors grid import power
2. When threshold exceeded, discharges battery to cap the peak
3. Respects battery reserve levels
4. Requires minimum 30-minute discharge capability

### 7. 🏠 Baseline Load Tracking

**Status**: ✅ **WORKING** (48-hour Historical Method)

#### 48-Hour Baseline Calculation
- **Uses historical data** from last 48 hours for realistic baselines
- **Daypart sensors**: Night/Day/Evening consumption patterns
- **Power or energy method**: Supports both power_w and counter_kwh approaches
- **Enhanced diagnostics**: Clear failure reasons in sensor attributes
- **Exclusion options**: Can exclude EV and battery grid charging

**Sensors**:
- `sensor.energy_dispatcher_house_baseline`: Overall baseline
- Daypart-specific sensors when available
- `sensor.energy_dispatcher_battery_runtime`: Estimated runtime

**Diagnostic Features**:
- `exclusion_reason` attribute explains calculation failures
- Shows source values even when calculation fails
- Detailed logging for troubleshooting

### 8. 🔄 Runtime Integration Features

**Status**: ✅ **WORKING**

#### Adapter System
- **Base adapter interface** for hardware abstraction
- **Huawei EMMA adapter**: Full integration with Huawei solar/battery systems
- **Generic EVSE adapter**: Manual EV charger control
- **Extensible pattern**: Easy to add new hardware adapters

#### Services Available
- `energy_dispatcher.force_battery_charge`: Charge battery at specified power
- `energy_dispatcher.override_battery_mode`: Temporary manual control
- `energy_dispatcher.create_dashboard_notification`: Setup assistance

#### Entities for Control
- **Number entities**: EV target SOC, battery floor settings
- **Select entities**: EV charging mode, target presets
- **Switch entities**: Feature toggles
- **Button entities**: Battery cost reset

### 9. 📱 Dashboard & User Experience

**Status**: ✅ **DOCUMENTED & WORKING**

#### Welcome Notification (v0.8.7+)
- **Automatic setup assistance** on first install
- **Direct link** to dashboard setup guide
- **Entity patterns** for easy dashboard creation
- **Can be disabled** via configuration

#### Available Documentation
- ✅ [Getting Started Guide](./docs/getting_started.md): 10-minute quick start
- ✅ [Dashboard Setup Guide](./docs/dashboard_guide.md): Step-by-step dashboard creation
- ✅ [AI Optimization Dashboard Guide](./docs/ai_optimization_dashboard_guide.md): Advanced dashboard
- ✅ [Configuration Guide](./docs/configuration.md): Complete reference
- ✅ [Battery Cost Tracking](./docs/battery_cost_tracking.md): BEC module details
- ✅ [Multi-Vehicle Setup](./docs/multi_vehicle_setup.md): EV management
- ✅ [Manual PV Forecast](./docs/manual_forecast.md): Physics-based forecasting
- ✅ [Solar Forecast Improvement](./docs/solar_forecast_improvement.md): Cloud compensation
- ✅ [Load Shifting & Peak Shaving](./docs/load_shifting_and_peak_shaving.md): Feature guide

### 10. 🌐 Internationalization

**Status**: ✅ **WORKING** (English + Swedish)

- **Full translations** for EN and SV
- **All config fields** localized
- **Sensor names** and descriptions in both languages
- **Service descriptions** translated
- **Error messages** in both languages

**Translation Coverage**:
- EN: 374 lines (complete)
- SV: 262 lines (core features complete, some sensor translations pending)

---

## 🎯 What Actually Makes Suggestions Now

### YES - Spot Price Can Make Actual Suggestions ✅

The integration **actively makes intelligent suggestions** based on spot prices:

1. **Battery Charging/Discharging**
   - Analyzes 24h price forecast
   - Recommends charging during cheap hours
   - Suggests holding/discharging during expensive hours
   - Provides specific times via `sensor.energy_dispatcher_next_high_cost_window`

2. **EV Charging Windows**
   - Calculates optimal charging schedule based on:
     - Current SOC and target
     - Deadline requirements (if set)
     - Price forecast
     - Solar availability
   - Shows countdown via `sensor.energy_dispatcher_ev_time_until_charge`
   - Explains decision via `sensor.energy_dispatcher_ev_charge_reason`

3. **Appliance Scheduling**
   - When enabled, provides specific start times for:
     - Dishwasher
     - Washing machine
     - Water heater
   - Shows cost savings vs immediate use
   - Provides alternative times if primary isn't convenient

4. **Load Shifting**
   - When enabled and conditions met:
     - Identifies current flexible loads
     - Finds cheaper time windows
     - Calculates potential savings
     - Shows "Shift to HH:MM" recommendations

5. **Export Opportunities**
   - When export mode enabled:
     - Monitors for profitable export windows
     - Calculates revenue vs degradation cost
     - Provides binary yes/no recommendation
     - Shows estimated revenue

### YES - Solar Forecast with Weather Compensation ✅

**Two ways to use solar forecasting**:

1. **Forecast.Solar with Cloud Compensation**:
   - Base forecast from Forecast.Solar API
   - Adjusts for cloud cover from weather entity
   - Provides both raw and compensated sensors
   - Used in battery/EV planning decisions

2. **Manual Physics-Based Engine**:
   - Free alternative using weather data
   - Considers cloud cover, temperature, wind
   - Built-in horizon blocking
   - More customizable but requires setup

**Integration with Decisions**:
- ✅ Battery charging decisions consider solar forecast
- ✅ EV charging optimizer uses solar availability
- ✅ Appliance recommendations factor in solar windows
- ✅ Export analysis considers excess solar production

### YES - Automatic Battery Control ✅

**Battery can be automatically controlled**:

1. **Charge Decisions**:
   - During cheap price periods (below cheap threshold)
   - When high-cost window predicted within 24h
   - When solar forecast shows insufficient production
   - Calculates required reserve percentage

2. **Discharge Decisions**:
   - During high-cost periods (above high threshold)
   - When spot price exceeds battery WACE
   - For peak shaving when grid import exceeds threshold
   - For export when profitable (if mode enabled)

3. **Hold Decisions**:
   - During medium-cost periods
   - When battery needed for upcoming high-cost window
   - When reserve target reached

**Control Methods**:
- Via `energy_dispatcher.force_battery_charge` service
- Via `energy_dispatcher.override_battery_mode` service
- Through hardware adapters (Huawei EMMA, etc.)
- Manual overrides always available

**Sensors Showing Status**:
- `sensor.energy_dispatcher_battery_charging_state`: Current action
- `sensor.energy_dispatcher_battery_power_flow`: Power direction and amount
- `sensor.energy_dispatcher_batt_time_until_charge`: Countdown to next charge
- `sensor.energy_dispatcher_batt_charge_reason`: Explanation of decision

---

## 📊 Creating a Monitoring & Override Dashboard

### Essential Cards for Your Dashboard

Here's what you should include for complete monitoring and control:

#### 1. 🤖 Status Overview Card
```yaml
type: entities
title: Energy Dispatcher Status
entities:
  - entity: sensor.energy_dispatcher_cost_level
    name: Current Price Level
  - entity: sensor.energy_dispatcher_battery_reserve
    name: Battery Reserve Target
  - entity: sensor.energy_dispatcher_optimization_plan
    name: Next Action
state_color: true
```

#### 2. 🔋 Battery Control & Monitoring
```yaml
type: entities
title: Battery Management
entities:
  - entity: sensor.energy_dispatcher_battery_cost
    name: Battery Energy Cost
  - entity: sensor.energy_dispatcher_battery_charging_state
    name: Charging State
  - entity: sensor.energy_dispatcher_battery_power_flow
    name: Power Flow
  - entity: sensor.energy_dispatcher_batt_time_until_charge
    name: Time Until Charge
  - entity: sensor.energy_dispatcher_batt_charge_reason
    name: Charge Reason
  - type: button
    name: Force Charge Now
    tap_action:
      action: call-service
      service: energy_dispatcher.force_battery_charge
      service_data:
        power_w: 5000
        duration: 60
  - type: button
    name: Override to Hold
    tap_action:
      action: call-service
      service: energy_dispatcher.override_battery_mode
      service_data:
        mode: hold
        duration_minutes: 120
```

#### 3. 🚗 EV Charging Control
```yaml
type: entities
title: EV Charging
entities:
  - entity: sensor.energy_dispatcher_ev_time_until_charge
    name: Next Charge Window
  - entity: sensor.energy_dispatcher_ev_charge_reason
    name: Charge Reason
  - entity: sensor.energy_dispatcher_ev_charging_session
    name: Current Session
  - entity: number.energy_dispatcher_ev_target_soc
    name: Target SOC
  - entity: select.energy_dispatcher_ev_mode
    name: Charging Mode
  - type: button
    name: Force Charge Now
    tap_action:
      action: call-service
      service: energy_dispatcher.ev_force_charge
      service_data:
        duration: 60
        current: 16
```

#### 4. 💡 Cost-Saving Suggestions
```yaml
type: entities
title: Smart Recommendations
entities:
  - entity: sensor.energy_dispatcher_dishwasher_optimal_time
    name: Dishwasher
  - entity: sensor.energy_dispatcher_washing_machine_optimal_time
    name: Washing Machine
  - entity: sensor.energy_dispatcher_water_heater_optimal_time
    name: Water Heater
  - entity: sensor.energy_dispatcher_load_shift_opportunity
    name: Load Shift
  - entity: binary_sensor.energy_dispatcher_export_opportunity
    name: Export Now?
```

#### 5. ☀️ Solar Production & Forecast
```yaml
type: entities
title: Solar Production
entities:
  - entity: sensor.solar_power_now
    name: Current Production
  - entity: sensor.solar_energy_today
    name: Today's Total
  - entity: sensor.solar_energy_tomorrow
    name: Tomorrow's Forecast
  - entity: sensor.solar_forecast_raw
    name: Raw Forecast
  - entity: sensor.solar_forecast_compensated
    name: Weather-Adjusted Forecast
```

#### 6. 📈 Price & Cost Tracking
```yaml
type: custom:apexcharts-card
header:
  title: Electricity Prices (24h)
  show: true
series:
  - entity: sensor.nordpool_kwh_se3_sek_3_10_025
    name: Spot Price
    stroke_width: 2
    type: line
    color: blue
  - entity: sensor.energy_dispatcher_cost_level
    name: Cost Level
    type: column
    color: orange
```

#### 7. 🎛️ Quick Action Panel
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
    name: Force Export
    icon: mdi:transmission-tower-export
    tap_action:
      action: call-service
      service: energy_dispatcher.set_export_mode
      service_data:
        mode: peak_price_opportunistic
  - type: button
    name: EV ASAP
    icon: mdi:car-electric
    tap_action:
      action: call-service
      service: energy_dispatcher.set_manual_ev
      service_data:
        soc_target: 80
```

### Complete Dashboard YAML

See the comprehensive dashboard guide at:
- 📖 [Dashboard Setup Guide](./docs/dashboard_guide.md)
- 📖 [AI Optimization Dashboard Guide](./docs/ai_optimization_dashboard_guide.md)

These guides include:
- Copy-paste ready YAML
- ApexCharts configurations
- Custom card recommendations
- Troubleshooting tips
- Automation examples

---

## 🧪 Testing & Quality

### Test Coverage (v0.10.1)
- **Total tests**: 361 tests
- **Integration tests**: 11 tests for optimization coordinator
- **Automation validation**: 16 tests for YAML examples
- **Translation validation**: 18 tests for EN/SV quality
- **Unit tests**: Full coverage for all modules

### Quality Assurance
- ✅ All automation templates validated
- ✅ YAML syntax verification
- ✅ Translation consistency checks
- ✅ Performance testing (handles 168 hours of data)
- ✅ Error handling and graceful degradation
- ✅ Backward compatibility maintained

---

## 🚫 What's NOT Yet Implemented

### Planned but Not Yet Working

1. **AI-Style Learning**
   - No machine learning models yet
   - No pattern recognition from historical usage
   - No adaptive threshold learning
   - ➡️ Currently uses rule-based optimization (still very effective)

2. **Comfort-Aware Optimization**
   - Framework designed but not fully implemented
   - No quiet hours enforcement
   - No comfort priority levels
   - ➡️ You can still manually configure constraints

3. **Advanced Weather Integration**
   - Basic cloud compensation works
   - Full weather prediction integration not complete
   - No precipitation-based adjustments
   - ➡️ Manual forecast engine provides good alternative

4. **Demand Response Integration**
   - No utility demand response program integration
   - No grid flexibility market participation
   - ➡️ Peak shaving provides similar benefits

5. **Multi-Home Coordination**
   - Single home/location only
   - No fleet management
   - ➡️ Can run multiple instances if needed

### Partially Implemented

1. **Appliance Optimization**
   - ✅ Recommendations working
   - ❌ Automatic scheduling not implemented
   - ➡️ You need to create automations to act on recommendations

2. **Load Shifting**
   - ✅ Opportunity identification working
   - ❌ Automatic load control not implemented
   - ➡️ You need to act on recommendations manually or via automation

3. **Export Management**
   - ✅ Profitability analysis working
   - ❌ Automatic export triggering depends on hardware adapter
   - ➡️ Huawei EMMA adapter supports automatic control

---

## 📚 How to Get Started

### For New Users

1. **Install the Integration**
   - Add Energy Dispatcher via HACS or manual installation
   - Configure via UI: Settings → Integrations → Add Energy Dispatcher

2. **Essential Configuration**
   - Nordpool price sensor
   - Battery SOC sensor
   - Battery capacity
   - Location (defaults to HA home)

3. **Optional but Recommended**
   - Solar forecast configuration (Forecast.Solar or Manual)
   - Weather entity for cloud compensation
   - EV charging setup (if applicable)
   - Export mode configuration

4. **Create Your Dashboard**
   - Follow [Dashboard Setup Guide](./docs/dashboard_guide.md)
   - Start with essential cards, add more as needed
   - Use [AI Optimization Dashboard](./docs/ai_optimization_dashboard_guide.md) for advanced features

5. **Set Up Automations**
   - See [Automation Examples](./docs/ai_optimization_automation_examples.md)
   - Start with battery charging automation
   - Add EV charging optimization
   - Include notification automations

### For Existing Users

- Check [CHANGELOG.md](./CHANGELOG.md) for what's new
- Review new sensor entities in Developer Tools → States
- Update your dashboard with new cards
- Explore new services in Developer Tools → Services
- Consider enabling new features like load shifting or export optimization

---

## 🔮 Future Development

See [Future Improvements](./docs/future_improvements.md) for detailed roadmap.

### Near-Term Priorities
1. Complete appliance automation implementation
2. Enhanced comfort-aware features
3. Additional hardware adapters
4. Advanced weather integration
5. User preference learning

### Long-Term Vision
1. Machine learning integration
2. Community pattern sharing
3. Utility program integration
4. Multi-home coordination
5. Enhanced predictive capabilities

---

## 💬 Support & Community

- **Issues**: [GitHub Issues](https://github.com/Bokbacken/energy_dispatcher/issues)
- **Documentation**: [docs/](./docs/) directory
- **Quick Start**: [Getting Started Guide](./docs/getting_started.md)
- **Dashboard Help**: [Dashboard Guide](./docs/dashboard_guide.md)

---

## 📄 License

MIT License - See [LICENSE](./LICENSE) file

---

**Last Updated**: 2025-10-15  
**Current Version**: 0.10.1  
**Status**: Production ready with comprehensive feature set
