# Energy Dispatcher - Configuration Guide

This guide provides detailed instructions on how to configure Energy Dispatcher for optimal battery and EV charging management.

## Table of Contents
- [Initial Setup](#initial-setup)
- [Price Configuration](#price-configuration)
- [Battery Configuration](#battery-configuration)
- [EV & EVSE Configuration](#ev--evse-configuration)
- [Solar Forecast Configuration](#solar-forecast-configuration)
- [Baseline Load Configuration](#baseline-load-configuration)
- [Advanced Options](#advanced-options)

## Initial Setup

1. Navigate to **Settings** → **Devices & Services** in Home Assistant
2. Click **Add Integration**
3. Search for and select **Energy Dispatcher**
4. Follow the configuration flow described below

## Price Configuration

Energy Dispatcher enriches your spot prices with additional fees and taxes to calculate the true cost of electricity.

### Required Settings

#### Nordpool Spot Price Sensor
- **Field**: `nordpool_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Select your Nordpool sensor that provides hourly spot prices
- **Example**: `sensor.nordpool_kwh_se3_sek_3_10_025`
- **Note**: The sensor should report prices in SEK/kWh

### Optional Price Components

#### Energy Tax
- **Field**: `price_tax`
- **Type**: Number (0-10 SEK/kWh)
- **Default**: 0.0
- **Description**: Government energy tax per kWh
- **Example**: `0.395` (typical Swedish energy tax)

#### Grid Transfer Fee
- **Field**: `price_transfer`
- **Type**: Number (0-10 SEK/kWh)
- **Default**: 0.0
- **Description**: Cost for transmitting electricity through the grid
- **Example**: `0.50` (varies by region and grid operator)

#### Supplier Surcharge
- **Field**: `price_surcharge`
- **Type**: Number (0-10 SEK/kWh)
- **Default**: 0.0
- **Description**: Additional markup from your electricity supplier
- **Example**: `0.05`

#### VAT Rate
- **Field**: `price_vat`
- **Type**: Number (0-1)
- **Default**: 0.25
- **Description**: Value Added Tax rate as decimal
- **Example**: `0.25` for 25% VAT

#### Fixed Monthly Fee
- **Field**: `price_fixed_monthly`
- **Type**: Number (0-10000 SEK)
- **Default**: 0.0
- **Description**: Fixed monthly cost from your electricity contract
- **Example**: `75` SEK per month

#### Include Fixed Fee in Hourly Price
- **Field**: `price_include_fixed`
- **Type**: Boolean
- **Default**: False
- **Description**: When enabled, distributes the fixed monthly fee across all hours of the month
- **Use Case**: Enable this if you want to see the total cost per kWh including fixed costs

### Price Calculation Formula

The enriched price is calculated as:
```
enriched_price = (spot_price + tax + transfer + surcharge) × (1 + vat)

If include_fixed:
    enriched_price += (fixed_monthly / 730)  # Assuming ~730 hours per month
```

## Battery Configuration

Configure your home battery system for optimal charge/discharge scheduling.

### Required Settings

#### Battery Capacity
- **Field**: `batt_cap_kwh`
- **Type**: Number (1-100 kWh)
- **Default**: 15.0
- **Description**: Total usable capacity of your battery system
- **Example**: `15.0` for a 15 kWh battery
- **Note**: Use the usable capacity, not the total installed capacity

#### Battery State of Charge Sensor
- **Field**: `batt_soc_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Sensor reporting current battery charge level as percentage
- **Example**: `sensor.battery_state_of_capacity`
- **Requirements**: Must report values 0-100 representing percentage

### Optional Battery Settings

#### Maximum Charge Power
- **Field**: `batt_max_charge_w`
- **Type**: Number (100-50000 W)
- **Default**: 4000
- **Description**: Maximum power at which the battery can be charged
- **Example**: `5000` for a 5kW system

#### Maximum Discharge Power
- **Field**: `batt_max_disch_w`
- **Type**: Number (100-50000 W)
- **Default**: 4000
- **Description**: Maximum power at which the battery can discharge
- **Example**: `5000` for a 5kW system

#### Battery Adapter
- **Field**: `batt_adapter`
- **Type**: Select dropdown
- **Default**: `huawei`
- **Options**: Currently only "huawei" is supported
- **Description**: Adapter type for controlling your battery system

#### Huawei Device ID
- **Field**: `huawei_device_id`
- **Type**: Text
- **Default**: Empty
- **Description**: Device ID for Huawei LUNA2000 systems
- **Example**: `1` or your specific device ID
- **Note**: Required when using Huawei adapter for force charge functionality

#### Battery Capacity Sensor (Alternative)
- **Field**: `batt_capacity_entity`
- **Type**: Entity selector (sensor domain)
- **Default**: Empty (uses manual capacity)
- **Description**: Sensor reporting battery rated capacity (alternative to manual capacity)
- **Example**: `sensor.rated_ess_capacity`
- **Requirements**: Must report capacity in kWh
- **Note**: When configured, this sensor value will override the manual `batt_cap_kwh` setting

#### Battery Energy Charged Today Sensor
- **Field**: `batt_energy_charged_today_entity`
- **Type**: Entity selector (sensor domain)
- **Default**: Empty
- **Description**: Sensor reporting total energy charged to battery today
- **Example**: `sensor.energy_charged_today`
- **Requirements**: Must report energy in kWh, resets daily
- **Purpose**: Enables automatic cost tracking by calling `bec.on_charge()` when battery charges
- **Note**: This sensor is required for automatic battery cost tracking

#### Battery Energy Discharged Today Sensor
- **Field**: `batt_energy_discharged_today_entity`
- **Type**: Entity selector (sensor domain)
- **Default**: Empty
- **Description**: Sensor reporting total energy discharged from battery today
- **Example**: `sensor.energy_discharged_today`
- **Requirements**: Must report energy in kWh, resets daily
- **Purpose**: Enables automatic discharge tracking by calling `bec.on_discharge()` when battery discharges
- **Note**: This sensor is required for automatic battery cost tracking

### Battery Runtime Settings

#### SOC Floor
- **Field**: `runtime_soc_floor`
- **Type**: Number (0-100 %)
- **Default**: 10
- **Description**: Minimum battery SOC to consider for runtime calculations
- **Purpose**: Protects battery by not draining below this level

#### SOC Ceiling
- **Field**: `runtime_soc_ceiling`
- **Type**: Number (0-100 %)
- **Default**: 95
- **Description**: Maximum battery SOC to consider for runtime calculations
- **Purpose**: Protects battery by not charging above this level

## EV & EVSE Configuration

Configure electric vehicle charging parameters and EVSE (Electric Vehicle Supply Equipment) control.

### EV Battery Settings

#### EV Mode
- **Field**: `ev_mode`
- **Type**: Select dropdown
- **Default**: `manual`
- **Options**: Currently only "manual" is supported
- **Description**: EV charging control mode

#### EV Battery Capacity
- **Field**: `ev_batt_kwh`
- **Type**: Number (10-200 kWh)
- **Default**: 75.0
- **Description**: Total battery capacity of your electric vehicle
- **Example**: `82` for a Tesla Model 3 Long Range

#### EV Current State of Charge
- **Field**: `ev_current_soc`
- **Type**: Number (0-100 %)
- **Default**: 40.0
- **Description**: Current charge level of your EV battery
- **Note**: This can be adjusted via number entities after initial setup

#### EV Target State of Charge
- **Field**: `ev_target_soc`
- **Type**: Number (0-100 %)
- **Default**: 80.0
- **Description**: Desired charge level for your EV
- **Note**: This can be adjusted via number entities after initial setup

### EVSE Control Settings

#### EVSE Start Switch
- **Field**: `evse_start_switch`
- **Type**: Entity selector (switch domain)
- **Description**: Switch entity to start EV charging
- **Example**: `switch.charger_charging`

#### EVSE Stop Switch
- **Field**: `evse_stop_switch`
- **Type**: Entity selector (switch domain)
- **Description**: Switch entity to stop EV charging
- **Example**: `switch.charger_pause_charging`

#### EVSE Current Control
- **Field**: `evse_current_number`
- **Type**: Entity selector (number domain)
- **Description**: Number entity to set charging current in Amperes
- **Example**: `number.charger_max_charging_current`

#### EVSE Minimum Current
- **Field**: `evse_min_a`
- **Type**: Number (6-32 A)
- **Default**: 6
- **Description**: Minimum charging current supported by your EVSE
- **Note**: Most chargers have a minimum of 6A

#### EVSE Maximum Current
- **Field**: `evse_max_a`
- **Type**: Number (6-32 A)
- **Default**: 16
- **Description**: Maximum charging current supported by your EVSE
- **Example**: `16` for a 3.7kW charger, `32` for a 7.4kW or 22kW charger

#### EVSE Phases
- **Field**: `evse_phases`
- **Type**: Number (1-3)
- **Default**: 3
- **Description**: Number of phases available for charging
- **Note**: 3-phase provides 3x the power of single-phase at the same current

#### EVSE Voltage
- **Field**: `evse_voltage`
- **Type**: Number (180-250 V)
- **Default**: 230
- **Description**: Line voltage at your location
- **Example**: `230` (standard in Europe), `120` (US single-phase)

### Charging Power Calculation

The charging power is calculated as:
```
Single-phase: Power (kW) = Voltage × Current / 1000
Three-phase: Power (kW) = √3 × Voltage × Current / 1000

Example (3-phase, 230V, 16A):
Power = 1.732 × 230 × 16 / 1000 = 6.4 kW
```

## Solar Forecast Configuration

Enable solar production forecasting using the Forecast.Solar service.

**Note**: Energy Dispatcher implements intelligent caching to avoid excessive API calls. Forecast data is cached for 30 minutes and reused across all components, reducing API requests from ~250+/hour to ~2/hour. This ensures compliance with Forecast.Solar's rate limits while maintaining accurate predictions.

### Basic Settings

#### Use Forecast.Solar
- **Field**: `fs_use`
- **Type**: Boolean
- **Default**: True
- **Description**: Enable or disable solar forecasting
- **Note**: Disable if you don't have solar panels

#### API Key (Optional)
- **Field**: `fs_apikey`
- **Type**: Text
- **Default**: Empty
- **Description**: API key for enhanced Forecast.Solar features
- **Note**: Public API is available without a key, but has rate limits
- **Get one at**: https://forecast.solar/

### Location Settings

#### Latitude
- **Field**: `fs_lat`
- **Type**: Number (-90 to 90)
- **Default**: 56.6967208731
- **Description**: Latitude of your solar installation
- **How to find**: Use Google Maps, right-click your location, and copy the first number

#### Longitude
- **Field**: `fs_lon`
- **Type**: Number (-180 to 180)
- **Default**: 13.0196173488
- **Description**: Longitude of your solar installation
- **How to find**: Use Google Maps, right-click your location, and copy the second number

### Solar Panel Configuration

#### Solar Panel Arrays
- **Field**: `fs_planes`
- **Type**: Multi-line text (JSON)
- **Default**: `[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]`
- **Description**: JSON array describing your solar panel arrays
- **Format**:
  ```json
  [
    {
      "dec": 45,      // Declination (tilt angle from horizontal, 0-90°)
      "az": "W",      // Azimuth (direction: N, NE, E, SE, S, SW, W, NW or degrees)
      "kwp": 9.43     // Peak power in kWp
    },
    {
      "dec": 45,
      "az": "E",
      "kwp": 4.92
    }
  ]
  ```
- **Example configurations**:
  ```json
  // Simple south-facing array
  [{"dec": 30, "az": "S", "kwp": 6.0}]
  
  // East-West split
  [{"dec": 15, "az": 90, "kwp": 5.0}, {"dec": 15, "az": 270, "kwp": 5.0}]
  ```

#### Horizon Profile
- **Field**: `fs_horizon`
- **Type**: Text (comma-separated)
- **Default**: `18,16,11,7,5,4,3,2,2,4,7,10`
- **Description**: Horizon angles for shading calculations (12 values for each 30° azimuth segment starting from north)
- **Format**: 12 comma-separated numbers representing elevation angles in degrees
- **Use case**: Important if you have shading from buildings, trees, or terrain
- **Default horizon**: Use `0,0,0,0,0,0,0,0,0,0,0,0` for flat, unobstructed horizon

### Actual PV Production Sensors (Optional)

#### PV Current Power Sensor
- **Field**: `pv_power_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Sensor reporting current solar power production
- **Units**: Should report in W, kW, or MW
- **Example**: `sensor.solar_power`
- **Purpose**: Used for comparing forecast vs actual production

#### PV Energy Today Sensor
- **Field**: `pv_energy_today_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Sensor reporting total solar energy produced today
- **Units**: Should report in Wh, kWh, or MWh
- **Example**: `sensor.solar_energy_today`
- **Purpose**: Used for daily production tracking

## Baseline Load Configuration

Configure how Energy Dispatcher calculates your house's baseline electricity consumption.

### Calculation Method

#### Runtime Source
- **Field**: `runtime_source`
- **Type**: Select dropdown
- **Default**: `counter_kwh`
- **Options**:
  - `counter_kwh`: Use an energy counter sensor
  - `power_w`: Use a power sensor with EMA smoothing
  - `manual_dayparts`: Manually define consumption patterns (not yet fully implemented)
- **Description**: Method for determining baseline house consumption

### Counter-Based Method Settings

#### Energy Counter Sensor
- **Field**: `runtime_counter_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Energy counter that tracks consumption
- **Example**: `sensor.house_energy_total`
- **Required for**: `counter_kwh` method

### Power-Based Method Settings

#### Power Sensor
- **Field**: `runtime_power_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Real-time power consumption sensor in Watts
- **Example**: `sensor.house_power`
- **Required for**: `power_w` method

#### Historical Lookback Period
- **Field**: `runtime_lookback_hours`
- **Type**: Number (0-168 hours)
- **Default**: 48
- **Description**: Number of hours to look back for calculating baseline from historical data
- **Note**: Set to 0 to disable historical calculation and use EMA instead
- **Recommendation**: 48 hours provides a good balance between responsiveness and stability

#### Use Time-of-Day Weighting
- **Field**: `runtime_use_dayparts`
- **Type**: Boolean
- **Default**: True
- **Description**: When enabled, calculates separate baselines for different times of day
- **Time periods**:
  - **Night** (00:00-07:59): Typical sleep hours with minimal activity
  - **Day** (08:00-15:59): Daytime hours with normal household activity
  - **Evening** (16:00-23:59): Peak hours with cooking, entertainment, etc.
- **Purpose**: Provides more accurate battery runtime estimates based on time of day

#### EMA Smoothing Factor (Alpha)
- **Field**: `runtime_alpha`
- **Type**: Number (0-1)
- **Default**: 0.2
- **Description**: Exponential moving average smoothing factor (used when lookback is 0)
- **Lower values** (e.g., 0.1): More smoothing, slower response to changes
- **Higher values** (e.g., 0.5): Less smoothing, faster response to changes

#### Calculation Window
- **Field**: `runtime_window_min`
- **Type**: Number (5-60 minutes)
- **Default**: 15
- **Description**: Time window for baseline calculations (used for bootstrap)
- **Recommendation**: 15 minutes aligns with typical smart meter intervals

### Exclusion Settings

These settings help calculate the "true" baseline by excluding non-constant loads:

#### Exclude EV Charging
- **Field**: `runtime_exclude_ev`
- **Type**: Boolean
- **Default**: True
- **Description**: Exclude EV charging power from baseline calculation
- **Purpose**: EV charging is controlled separately and shouldn't inflate baseline

#### Exclude Battery Grid Charging
- **Field**: `runtime_exclude_batt_grid`
- **Type**: Boolean
- **Default**: True
- **Description**: Exclude battery charging from grid in baseline calculation
- **Purpose**: Battery charging is controlled separately

### Context Sensors for Exclusion

#### House Load Power Sensor
- **Field**: `load_power_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Total house load power for exclusion calculations and accurate battery cost tracking
- **Example**: `sensor.house_load_power`
- **Importance**: While optional, this sensor is **highly recommended** for accurate battery energy cost tracking. Without it, the system cannot accurately determine when battery charging is from solar vs grid, which may result in incorrect cost calculations
- **Impact if missing**: Battery charges will be conservatively classified as "grid" (with cost) unless PV production is at least 2x the battery charging power

#### Battery Power Sensor
- **Field**: `batt_power_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Battery power sensor
- **Example**: `sensor.battery_power`
- **Default convention**: Positive = charging, negative = discharging
- **Note**: If your sensor shows negative values when battery is charging, enable the "Invert Battery Power Sign" option below

#### Invert Battery Power Sign
- **Field**: `batt_power_invert_sign`
- **Type**: Boolean (checkbox)
- **Default**: `False` (disabled)
- **Description**: Enable this option if your battery power sensor uses Huawei/inverted convention (negative=charging, positive=discharging)
- **How to check**: Look at your battery power sensor when the battery is actively charging:
  - If it shows **negative values** (e.g., -1000 W) → Enable this option
  - If it shows **positive values** (e.g., +1000 W) → Leave this disabled (default)
- **Systems that may need this**: Some Huawei LUNA2000 inverters and older battery management systems

#### Grid Import Today Sensor
- **Field**: `grid_import_today_entity`
- **Type**: Entity selector (sensor domain)
- **Description**: Daily grid import for monitoring
- **Example**: `sensor.grid_import_today`
- **Units**: Should report in kWh

## Advanced Options

### Updating Configuration

After initial setup, you can modify any configuration option:

1. Go to **Settings** → **Devices & Services**
2. Find **Energy Dispatcher**
3. Click **Configure**
4. Modify any settings as needed
5. Click **Submit**

All settings maintain their previous values by default, so you only need to change what you want to update.

### Manual Control via Number Entities

Energy Dispatcher creates several number entities for manual control:

- **EV Battery Capacity**: Adjust EV battery size
- **EV Current SOC**: Set current EV charge level
- **EV Target SOC**: Set desired EV charge level
- **Home Battery Capacity**: Adjust home battery size
- **Home Battery SOC Floor**: Set minimum battery level
- **EVSE Max Current**: Adjust maximum charging current
- **EVSE Phases**: Change number of charging phases
- **EVSE Voltage**: Adjust voltage setting

These entities allow you to quickly adjust parameters without reconfiguring the integration.

### Services

Energy Dispatcher provides several services for manual override:

#### Force EV Charge
Service: `energy_dispatcher.ev_force_charge`
```yaml
service: energy_dispatcher.ev_force_charge
data:
  duration: 60  # minutes
  current: 16   # amperes
```

#### Pause EV Charging
Service: `energy_dispatcher.ev_pause`
```yaml
service: energy_dispatcher.ev_pause
data:
  duration: 30  # minutes
```

#### Force Battery Charge
Service: `energy_dispatcher.force_battery_charge`
```yaml
service: energy_dispatcher.force_battery_charge
data:
  power_w: 5000   # watts
  duration: 60    # minutes
```

#### Create Dashboard Notification
Service: `energy_dispatcher.create_dashboard_notification`

Manually create or recreate the dashboard setup notification. Useful if you dismissed the original notification or want to see the setup instructions again.

```yaml
service: energy_dispatcher.create_dashboard_notification
```

**Use case:** You deleted the hub and re-added it, or you dismissed the notification and want to see the dashboard setup instructions again.

## Available Sensors

Energy Dispatcher provides several sensors for monitoring your energy system:

### Baseline Load Sensors

#### House Load Baseline Now
- **Entity**: `sensor.house_load_baseline_now`
- **Unit**: W (Watts)
- **Description**: Current house baseline power consumption
- **Behavior**: 
  - When dayparts are enabled (`runtime_use_dayparts: true`): Shows the baseline for the current time of day (night/day/evening)
  - When dayparts are disabled: Shows the overall 48-hour average
  - Falls back to overall average if current daypart baseline is unavailable
- **Attributes**:
  - `method`: Calculation method (counter_kwh, power_w, or power_w_48h)
  - `source_value`: Raw value from source sensor
  - `baseline_kwh_per_h`: Baseline in kWh/h
  - `exclusion_reason`: Reason if current sample is excluded (ev_charging, batt_grid_charge)

#### House Load Baseline Night
- **Entity**: `sensor.house_load_baseline_night`
- **Unit**: W (Watts)
- **Description**: Average house load during night hours (00:00-07:59)
- **Note**: Only available when using 48-hour historical baseline (runtime_lookback_hours > 0)
- **Purpose**: Provides accurate baseline for battery runtime calculations during night

#### House Load Baseline Day
- **Entity**: `sensor.house_load_baseline_day`
- **Unit**: W (Watts)
- **Description**: Average house load during day hours (08:00-15:59)
- **Note**: Only available when using 48-hour historical baseline (runtime_lookback_hours > 0)
- **Purpose**: Provides accurate baseline for battery runtime calculations during day

#### House Load Baseline Evening
- **Entity**: `sensor.house_load_baseline_evening`
- **Unit**: W (Watts)
- **Description**: Average house load during evening hours (16:00-23:59)
- **Note**: Only available when using 48-hour historical baseline (runtime_lookback_hours > 0)
- **Purpose**: Provides accurate baseline for battery runtime calculations during evening

### Other Sensors

See the main [README.md](../README.md) for a complete list of all available sensors including:
- Battery runtime and cost tracking
- Solar production and forecast
- EV charging status
- Price information

## Troubleshooting

### Common Issues

1. **Invalid latitude/longitude error**
   - Ensure latitude is between -90 and 90
   - Ensure longitude is between -180 and 180
   - Use decimal format (e.g., 56.123456)

2. **Entity not found**
   - Verify the entity exists in **Developer Tools** → **States**
   - Check that the entity domain matches (sensor, switch, number)
   - Ensure the entity is available (not "unavailable" or "unknown")

3. **Battery not responding**
   - Verify battery adapter is correctly set
   - For Huawei: Ensure device_id is correct
   - Check that battery entities are reporting valid states

4. **Solar forecast not updating**
   - Note: Forecast data is cached for 30 minutes to comply with API rate limits
   - Verify Forecast.Solar API is accessible
   - Check that latitude/longitude are correct
   - Ensure plane configuration JSON is valid
   - Verify API key if using enhanced features
   - Check Home Assistant logs for "Forecast.Solar" messages to see cache status

5. **Baseline calculation seems wrong**
   - Check exclusion settings match your setup
   - Verify context sensors are reporting correct values
   - Adjust EMA alpha for different smoothing
   - Consider switching between counter_kwh and power_w methods

6. **500 Internal Server Error when re-entering configuration**
   - This issue was fixed in version 0.8.1 and further improved in the latest version
   - If you encounter this error, update to the latest version
   - The error occurred when trying to modify settings after initial setup
   - Root causes: 
     - Options flow was not properly passing Home Assistant instance (fixed in v0.8.1)
     - Weather entity enumeration had improper error handling (fixed in latest)
   - Solution: Update the integration to get the fixes

## Support

For additional help:
- GitHub Issues: https://github.com/Bokbacken/energy_dispatcher/issues
- Home Assistant Community: Tag your post with "energy_dispatcher"

## See Also

- [README.md](../README.md) - Main documentation and features overview
- [Home Assistant Integration Documentation](https://www.home-assistant.io/integrations/)
- [Forecast.Solar API Documentation](https://doc.forecast.solar/)
