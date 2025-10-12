# Diagnostic Guide for House Load Baseline Sensor

This guide helps you troubleshoot issues when the "House Load Baseline Now" sensor shows "unknown" or unexpected values.

## Understanding the Sensor Attributes

The "House Load Baseline Now" sensor has the following attributes that help with debugging:

### 1. `method`
Shows the calculation method being used. Should show `energy_counter_48h`.

### 2. `source_value`
Shows the current value of your house energy counter sensor. This helps verify:
- The sensor is accessible
- It's reporting numeric values (not "unknown" or "unavailable")
- The counter is incrementing over time

**Example values:**
- `1234.5` - Good! The sensor is working
- `null` or `Okänd` - The sensor is not configured or not accessible

### 3. `baseline_kwh_per_h`
Shows the calculated average consumption in kWh per hour over the lookback period (default 48 hours).

**Example values:**
- `0.8965` - Good! Baseline calculated successfully (~897W average load)
- `null` or `Okänd` - Calculation failed, check `exclusion_reason`

### 4. `exclusion_reason`
**NEW FEATURE**: This attribute now shows the specific reason why baseline calculation failed!

**Common failure reasons and solutions:**

#### "No house energy counter configured (runtime_counter_entity)"
**Problem:** The required energy counter sensor is not configured.

**Solution:** 
1. Go to Settings → Devices & Services → Energy Dispatcher
2. Click "Configure"
3. Set "House Energy Counter Sensor" (`runtime_counter_entity`) to a cumulative energy sensor (e.g., `sensor.house_total_energy`)

#### "Insufficient historical data: X data points (need 2+)"
**Problem:** The sensor doesn't have enough historical data in Home Assistant's Recorder database.

**Solution:**
1. Verify the sensor exists: Go to Developer Tools → States, search for your configured sensor
2. Check if the sensor is recording history:
   - Go to Developer Tools → Statistics
   - Search for your sensor
   - If not found, the sensor may not be recording to the database
3. Check Recorder retention settings:
   - Default is 10 days, which is sufficient
   - If you've customized `recorder` settings, ensure retention >= lookback period (default 48 hours)
4. Wait for data to accumulate (at least a few hours)

#### "Invalid sensor values: start=None, end=None" (or similar)
**Problem:** The sensor is reporting non-numeric values like "unknown", "unavailable", or invalid strings.

**Solution:**
1. Check sensor in Developer Tools → States
2. Verify it shows a numeric value (e.g., `1234.5`)
3. If showing "unknown" or "unavailable":
   - Check the integration providing the sensor
   - Restart the integration or Home Assistant
   - Check integration logs for errors
4. Ensure the sensor is a cumulative energy counter (always increasing), not a power sensor

#### "Exception during calculation: <error message>"
**Problem:** An unexpected error occurred during calculation.

**Solution:**
1. Check Home Assistant logs for the full error details:
   - Settings → System → Logs
   - Filter for "energy_dispatcher"
2. Report the issue on GitHub with the full error message

## Checking Home Assistant Logs

For more detailed diagnostic information, check the logs:

1. Go to Settings → System → Logs
2. Filter for "energy_dispatcher" 
3. Look for WARNING messages about baseline calculation

**Example log messages:**

```
WARNING: 48h baseline: No historical data available for sensor.house_energy 
(need at least 2 data points, got 0). Check: (1) Sensor exists and reports values, 
(2) Recorder is enabled, (3) Recorder retention period >= 48 hours
```

```
WARNING: 48h baseline: Invalid house energy counter values for sensor.house_energy 
(start=None, end=None). Check: Sensor reports numeric values (not 'unknown', 'unavailable')
```

## Verifying Your Configuration

### Step 1: Check sensor entity ID
1. Go to Settings → Devices & Services → Energy Dispatcher → Configure
2. Note the "House Energy Counter Sensor" value
3. Example: `sensor.house_total_energy`

### Step 2: Verify sensor exists and works
1. Go to Developer Tools → States
2. Search for your sensor (e.g., `sensor.house_total_energy`)
3. Verify:
   - ✅ Shows a numeric value
   - ✅ Unit is kWh (or similar energy unit)
   - ✅ Value increases over time (it's cumulative)
   - ❌ Not showing "unknown" or "unavailable"
   - ❌ Not a power sensor (W) - must be energy (kWh)

### Step 3: Check historical data
1. Go to Developer Tools → Statistics  
2. Search for your sensor
3. If listed: ✅ Sensor has historical data
4. If not listed: ❌ Sensor may not be recording to database

## Quick Troubleshooting Checklist

- [ ] House energy counter sensor is configured in Energy Dispatcher settings
- [ ] Sensor exists (found in Developer Tools → States)
- [ ] Sensor shows numeric value (not "unknown" or "unavailable")
- [ ] Sensor is cumulative energy in kWh (not instantaneous power in W)
- [ ] Sensor has historical data (check Developer Tools → Statistics)
- [ ] Home Assistant Recorder is enabled (default: yes)
- [ ] Waited at least 1-2 hours for data to accumulate
- [ ] Checked `exclusion_reason` attribute for specific failure reason
- [ ] Checked Home Assistant logs for WARNING messages

## Still Having Issues?

If you've checked everything above and still have issues:

1. Check the `exclusion_reason` attribute - it will tell you the specific problem
2. Check Home Assistant logs for detailed diagnostic messages
3. Open an issue on GitHub with:
   - The `exclusion_reason` value
   - Your sensor entity ID
   - Screenshot of sensor state from Developer Tools
   - Relevant log messages
   - Your configuration (Settings → Devices & Services → Energy Dispatcher)
