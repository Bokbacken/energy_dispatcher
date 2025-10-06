# Fixes Summary: Forecast Source Selection Issues

## Problem Statement
The user reported two main issues:
1. The forecast engine doesn't switch correctly between `forecast_solar` and `manual_physics` - always getting forecast.solar data even when manual_physics is selected
2. The config flow doesn't dynamically update parameter fields when changing the forecast source dropdown - user has to save and reopen to see the correct fields

## Root Causes Identified

### Critical Issue: Sensors Not Updating Configuration
**Location**: `custom_components/energy_dispatcher/sensor_forecast.py`

The sensors were creating a single `ForecastSolarProvider` instance at setup time and reusing it for all updates. When the user changed the configuration (e.g., switching from `forecast_solar` to `manual_physics`), the sensors continued using the old provider with the old `forecast_source` setting.

**Impact**: Even though the coordinator would pick up the new config, the forecast sensors would still show data from the old engine until Home Assistant was restarted or the integration was reloaded.

### Config Flow Schema Not Rebuilding on Validation Errors
**Location**: `custom_components/energy_dispatcher/config_flow.py`

When the config flow form had validation errors, it would rebuild the form using the DEFAULTS dictionary instead of the user's current selections. This meant if a user selected `manual_physics` but had a validation error (e.g., invalid lat/lon), the form would rebuild showing `forecast_solar` fields instead of `manual_physics` fields.

### Home Assistant Form Limitations (Cannot be Fixed)
Home Assistant's voluptuous-based forms are static and do not support dynamic field updates based on other field values. When a user changes the forecast_source dropdown from `forecast_solar` to `manual_physics` within the form, the fields do not update until the form is saved and reopened.

**This is expected behavior** and would require either:
- A multi-step flow (separate steps for selecting forecast source and configuring it)
- Showing all fields at once (which would be confusing)
- Using Home Assistant's new UI-based config flows (requires significant refactoring)

## Fixes Applied

### 1. Dynamic Forecast Provider Creation in Sensors
**Files Changed**: `sensor_forecast.py`

**Changes**:
- Modified all sensor classes (`SolarForecastRawSensor`, `SolarForecastCompensatedSensor`, `WeatherCapabilitySensor`) to store the config entry instead of a fixed forecast provider
- Added `_get_forecast_provider()` method to each sensor that creates a new `ForecastSolarProvider` with the current configuration
- Each sensor now calls `_get_forecast_provider()` in `async_update()` to get a fresh provider with the latest config
- Made `WeatherCapabilitySensor` conditionally available based on `forecast_source` setting

**Impact**: Sensors now immediately pick up configuration changes without requiring a restart or reload.

### 2. Config Flow Schema Rebuilding
**Files Changed**: `config_flow.py`

**Changes**:
- Updated `async_step_user()` to pass `user_input` as defaults to `_schema_user()` when rebuilding the form after validation errors
- Updated `EnergyDispatcherOptionsFlowHandler.async_step_init()` to:
  - Add validation for lat/lon (matching the main config flow)
  - Pass `user_input` as defaults when rebuilding after validation errors
  - Properly handle the case where there are no errors (use current config)

**Impact**: When validation errors occur, the form now shows the fields matching the user's current forecast_source selection.

### 3. Enhanced Logging for Diagnostics
**Files Changed**: `forecast_provider.py`

**Changes**:
- Added INFO-level log when initializing manual physics engine (shows weather_entity)
- Added INFO-level log when using Forecast.Solar engine (shows if apikey is present)
- Added DEBUG-level log in `async_fetch_watts()` to show which engine is being used
- Added WARNING-level log when `forecast_source` is `manual_physics` but `manual_engine` is None (indicates initialization failure)

**Impact**: Users and developers can now easily diagnose which forecast engine is being used by checking the logs.

## Remaining Limitations

### Dynamic Form Updates
The config flow form fields do not update dynamically when changing the forecast_source dropdown within the same form submission. Users must:
1. Select the forecast source
2. Save the configuration
3. Reopen the configuration dialog
4. See the fields appropriate for the selected forecast source

This is a limitation of Home Assistant's static form schema and cannot be easily fixed without significant refactoring to use multi-step flows or the new UI-based config flows.

### Performance Consideration
Creating a new `ForecastSolarProvider` (and potentially `ManualForecastEngine`) on every sensor update could have a small performance impact. However:
- The `ForecastSolarProvider` constructor is lightweight
- The `ManualForecastEngine` constructor just parses JSON and detects weather capabilities once
- The actual forecast calculation (`async_fetch_watts()`) already implements caching to avoid redundant API calls or calculations
- Sensor updates typically happen every few minutes, not every second

If performance becomes an issue, we could add instance-level caching where the sensor checks if the config has changed before recreating the provider.

## Testing Recommendations

1. **Manual Test - Switch from Forecast.Solar to Manual Physics**:
   - Configure integration with `forecast_source: forecast_solar`
   - Verify sensors show forecast.solar data (check logs)
   - Change config to `forecast_source: manual_physics` with a valid weather entity
   - Wait for next sensor update (or restart integration)
   - Verify sensors now show manual physics data (check logs for "Initializing manual physics forecast engine")

2. **Manual Test - Switch from Manual Physics to Forecast.Solar**:
   - Configure integration with `forecast_source: manual_physics`
   - Verify sensors show manual physics data
   - Change config to `forecast_source: forecast_solar` with API key
   - Wait for next sensor update (or restart integration)
   - Verify sensors now show forecast.solar data (check logs for "Using Forecast.Solar forecast engine")

3. **Manual Test - Config Flow Validation Errors**:
   - Open config dialog
   - Select `forecast_source: manual_physics`
   - Enter invalid latitude (e.g., "abc")
   - Submit form
   - Verify form shows validation error AND still shows manual_physics fields

4. **Manual Test - Weather Capability Sensor**:
   - Configure with `forecast_source: manual_physics`
   - Verify `sensor.weather_forecast_capabilities` is available
   - Change to `forecast_source: forecast_solar`
   - Verify `sensor.weather_forecast_capabilities` becomes unavailable

## Conclusion

The critical bug (sensors not updating when config changes) has been fixed. The config flow now properly rebuilds forms with user selections on validation errors. Enhanced logging will help diagnose any remaining issues.

The limitation around dynamic form updates is a known Home Assistant constraint and would require significant refactoring to address. However, this is a minor UX inconvenience, not a functionality issue.
