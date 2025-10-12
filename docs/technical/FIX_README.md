# Fix for Forecast Source Selection Issues

## What Was Fixed

### Critical Bug: Forecast Engine Not Switching
**Problem**: Even when you changed the forecast source from "forecast.solar" to "manual_physics" (or vice versa) in the configuration, the sensors would continue to use the old forecast engine until you restarted Home Assistant.

**Root Cause**: The forecast sensors were creating the forecast provider once at startup and reusing it forever, never checking if the configuration changed.

**Fix**: Sensors now recreate the forecast provider with the current configuration every time they update. This means when you change the forecast source in the configuration, the sensors will immediately start using the new engine on their next update cycle.

### Config Flow Improvements
**Problem**: When the configuration form had validation errors (like an invalid latitude), it would reset to show forecast.solar fields even if you had selected manual_physics.

**Fix**: The form now remembers your selections and shows the correct fields when rebuilding after validation errors.

## How to Test the Fix

### Test 1: Verify Current Forecast Source
1. Check your Home Assistant logs at INFO level
2. Look for lines like:
   - `"Initializing manual physics forecast engine (weather_entity=weather.home)"` - means manual_physics is active
   - `"Using Forecast.Solar forecast engine (apikey=***)"` - means forecast.solar is active
3. Also look for DEBUG lines in sensor updates:
   - `"Using manual physics forecast engine"` - confirms manual is working
   - `"Using Forecast.Solar forecast engine"` - confirms forecast.solar is working

### Test 2: Switch from Forecast.Solar to Manual Physics
1. Open your Energy Dispatcher configuration
2. Current setting: `Forecast Source: forecast_solar`
3. Change to: `Forecast Source: manual_physics`
4. Configure a weather entity (required for manual physics)
5. Save the configuration
6. Wait 1-2 minutes for sensors to update
7. Check logs - you should see "Initializing manual physics forecast engine"
8. Check sensor attributes - `sensor.solar_forecast_raw` and `sensor.solar_forecast_compensated` should show forecast data
9. NEW: `sensor.weather_forecast_capabilities` should become available

### Test 3: Switch from Manual Physics to Forecast.Solar
1. Open your Energy Dispatcher configuration
2. Current setting: `Forecast Source: manual_physics`
3. Change to: `Forecast Source: forecast_solar`
4. Optionally add your Forecast.Solar API key
5. Save the configuration
6. Wait 1-2 minutes for sensors to update
7. Check logs - you should see "Using Forecast.Solar forecast engine"
8. Check sensor attributes - forecast data should now come from Forecast.Solar API
9. `sensor.weather_forecast_capabilities` should become unavailable

### Test 4: Config Flow Validation
1. Open configuration dialog
2. Select `Forecast Source: manual_physics`
3. Enter an invalid value for latitude (e.g., "abc")
4. Click Submit
5. Form should show error AND still show manual_physics fields (weather entity, manual step minutes, etc.)
6. Before this fix, it would show forecast.solar fields (API key, cloud factors)

## Known Limitation (Cannot Be Fixed)

**Issue**: When you change the "Forecast Source" dropdown in the configuration form from "forecast.solar" to "manual_physics" (or vice versa), the form fields don't update immediately to show the appropriate options for the selected source.

**Workaround**: After changing the forecast source:
1. Click "Submit" to save
2. Close the configuration dialog
3. Reopen the configuration dialog
4. Now you'll see the correct fields for your selected forecast source

**Why This Happens**: Home Assistant's configuration forms are static - they don't support dynamic field updates based on other field values. This is a platform limitation, not a bug in this integration.

**Alternative Solutions** (would require major refactoring):
- Use a multi-step flow (Step 1: Choose forecast source, Step 2: Configure chosen source)
- Show all fields at once (would be confusing)
- Migrate to Home Assistant's new UI-based config flows

## Diagnostic Logging

If you're still having issues, enable DEBUG logging for the integration:

```yaml
logger:
  default: info
  logs:
    custom_components.energy_dispatcher: debug
```

Then check your logs for:
- `"Initializing manual physics forecast engine"` - manual engine setup
- `"Using Forecast.Solar forecast engine"` - forecast.solar engine setup
- `"Using manual physics forecast engine"` - which engine is being used in sensor update
- `"Forecast source is 'manual_physics' but manual engine is not initialized"` - indicates a problem with manual engine initialization

## Need Help?

If the forecast engine is still not switching correctly after this fix:
1. Check the logs as described above
2. Verify your weather entity is correctly configured for manual_physics
3. Create a GitHub issue with:
   - Your configuration (redact API keys)
   - Relevant log entries
   - Steps to reproduce the issue

## Summary

The critical bug where sensors wouldn't pick up forecast source changes has been fixed. Sensors now dynamically read the configuration on every update. The config flow now properly handles validation errors. Enhanced logging makes it easy to diagnose which forecast engine is being used.

The only remaining limitation is the static form fields, which is a Home Assistant platform constraint and requires a workaround (save and reopen the config dialog after changing forecast source).
