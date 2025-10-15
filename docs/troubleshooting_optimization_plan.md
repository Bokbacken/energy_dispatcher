# Troubleshooting: Optimization Plan Sensor

This guide helps you diagnose and fix issues when the **Optimization Plan** sensor shows "No plan available".

## 🔍 Understanding the Sensor

The **Optimization Plan** sensor (`sensor.energy_dispatcher_optimization_plan`) provides:
- **State**: Summary of next recommended action (e.g., "Charge battery @ 02:00")
- **Attributes**: Detailed hourly plan with battery charge/discharge and EV charging recommendations
- **Diagnostics**: Information about why the plan is unavailable (if applicable)

## 🩺 Quick Diagnostic Check

The sensor includes diagnostic attributes that tell you exactly what's wrong. To view them:

1. Go to **Developer Tools** → **States**
2. Search for `sensor.energy_dispatcher_optimization_plan`
3. Look at the **Attributes** section

### Diagnostic Attributes

The sensor exposes these diagnostic attributes:

- **`status`**: Current state of plan generation
  - `ok` - Plan generated successfully
  - `missing_price_data` - No hourly price data available
  - `missing_battery_soc_entity` - Battery SOC sensor not configured
  - `battery_soc_unavailable` - Battery SOC sensor not reporting valid values
  - `invalid_battery_capacity` - Battery capacity invalid or not configured
  - `error: <message>` - An unexpected error occurred

- **`help`**: Human-readable explanation of the problem
- **`check`**: Where to go in Home Assistant to fix the issue

## 🔧 Common Issues and Solutions

### Issue 1: "No price data available"

**Diagnostic Status**: `missing_price_data`

**What it means**: The integration cannot get hourly price data from your Nordpool sensor.

**How to fix**:

1. **Check Nordpool Integration**:
   - Go to **Settings** → **Devices & Services**
   - Find your Nordpool integration
   - Verify it's showing prices (not "unavailable")

2. **Verify Nordpool Sensor Configuration**:
   - Go to **Settings** → **Devices & Services** → **Energy Dispatcher** → **Configure**
   - Check "Nordpool Spot Price Sensor" is set to the correct entity
   - Common entity names: `sensor.nordpool_kwh_se3_sek_3_10_025`

3. **Check Sensor State**:
   - Go to **Developer Tools** → **States**
   - Search for your Nordpool sensor
   - Verify:
     - ✅ Shows a numeric price value
     - ✅ Has `raw_today` and `raw_tomorrow` attributes with hourly data
     - ❌ Not showing "unknown" or "unavailable"

**Still not working?**
- Wait for the next Nordpool price update (usually happens around 13:00 CET)
- Restart Home Assistant to force a refresh
- Check Nordpool integration logs for errors

---

### Issue 2: "Battery SOC entity not configured"

**Diagnostic Status**: `missing_battery_soc_entity`

**What it means**: The integration needs to know your battery's state of charge (SOC) to generate a plan.

**How to fix**:

1. Go to **Settings** → **Devices & Services** → **Energy Dispatcher** → **Configure**
2. Set **"Battery State of Charge Sensor (%)"** to your battery SOC sensor
3. Common sensor names:
   - `sensor.battery_soc`
   - `sensor.battery_state_of_charge`
   - `sensor.powerwall_charge` (Tesla Powerwall)
   - `sensor.luna2000_battery_state_of_charge` (Huawei)

**Don't have a battery?**
- The optimization plan feature requires a battery to provide recommendations
- Other features of Energy Dispatcher will still work (price monitoring, solar forecasting)

---

### Issue 3: "Battery SOC sensor not reporting valid value"

**Diagnostic Status**: `battery_soc_unavailable`

**What it means**: The battery SOC sensor exists but is returning "unavailable", "unknown", or an invalid value.

**How to fix**:

1. **Check Sensor State**:
   - Go to **Developer Tools** → **States**
   - Search for your battery SOC sensor
   - Verify:
     - ✅ Shows a numeric value (e.g., `65.5`)
     - ✅ Unit is `%` (percent)
     - ❌ Not showing "unknown" or "unavailable"

2. **Check Battery Integration**:
   - Go to **Settings** → **Devices & Services**
   - Find your battery integration (e.g., Tesla, Huawei, etc.)
   - Verify it's connected and responding
   - Check for error messages

3. **Common Causes**:
   - Battery integration not configured correctly
   - Communication issue with battery (check network/connection)
   - Battery in maintenance or offline mode
   - Incorrect sensor entity ID configured in Energy Dispatcher

4. **Temporary Fix**:
   - If your battery integration is temporarily down, the plan won't generate
   - Once the sensor starts reporting valid values again, the plan will resume

---

### Issue 4: "Battery capacity not configured or invalid"

**Diagnostic Status**: `invalid_battery_capacity`

**What it means**: The battery capacity is set to 0, negative, or not configured.

**How to fix**:

1. Go to **Settings** → **Devices & Services** → **Energy Dispatcher** → **Configure**
2. Set **"Battery Capacity (kWh)"** to your battery's actual capacity
3. Examples:
   - Tesla Powerwall 2: `13.5` kWh (usable capacity)
   - Huawei LUNA2000-10: `10.0` kWh
   - LG Chem RESU 10H: `9.3` kWh

**Note**: Use the **usable** capacity, not the total capacity. Most batteries reserve 10-20% for longevity.

---

### Issue 5: "An error occurred generating the plan"

**Diagnostic Status**: `error: <error message>`

**What it means**: An unexpected error occurred during plan generation.

**How to fix**:

1. **Check Home Assistant Logs**:
   - Go to **Settings** → **System** → **Logs**
   - Filter for `energy_dispatcher`
   - Look for WARNING or ERROR messages about "optimization plan"

2. **Common Error Messages**:

   - **"can't compare offset-naive and offset-aware datetimes"**
     - This is an internal datetime handling issue
     - Usually self-corrects on next update cycle
     - If persistent, restart Home Assistant

   - **"name 'CONF_...' is not defined"**
     - Missing configuration value
     - Report as a bug on GitHub with full error message

3. **Report the Issue**:
   - If the error persists or you don't understand it
   - Open an issue on GitHub: https://github.com/Bokbacken/energy_dispatcher/issues
   - Include:
     - Full error message from logs
     - `status` attribute value
     - Your configuration (anonymize personal details)

---

## ✅ Verification Checklist

Use this checklist to verify your setup is correct:

- [ ] Nordpool integration installed and working
- [ ] Nordpool sensor configured in Energy Dispatcher settings
- [ ] Nordpool sensor showing current price (not "unavailable")
- [ ] Battery SOC sensor configured in Energy Dispatcher settings
- [ ] Battery SOC sensor showing valid percentage (e.g., 65%)
- [ ] Battery capacity configured (e.g., 15.0 kWh)
- [ ] Battery integration connected and responding
- [ ] Waited at least 5 minutes after configuration for first plan generation
- [ ] Checked sensor attributes for `status: ok`

## 🎯 Expected Behavior When Working

When everything is configured correctly:

**Sensor State**:
- Shows next action, e.g., "Charge battery @ 02:00"
- Or "No actions recommended" if battery strategy doesn't suggest any actions
- Updates every 5 minutes

**Sensor Attributes**:
- `status: ok`
- `plan_count: 24` (number of hourly slots in the plan)
- `actions: [...]` (array of hourly actions)
- `charge_hours: <number>` (how many hours to charge)
- `discharge_hours: <number>` (how many hours to discharge)

**Dashboard View**:
```yaml
type: entities
entities:
  - entity: sensor.energy_dispatcher_optimization_plan
    name: Next Recommended Action
```

## 🔄 Update Frequency

The optimization plan updates every **5 minutes** (default coordinator update interval).

If you make configuration changes:
1. Changes are applied immediately
2. Next update cycle (within 5 minutes) will use new settings
3. You can force an update by restarting Home Assistant (not required)

## 📚 Related Documentation

- [Configuration Guide](./configuration.md) - Detailed explanation of all settings
- [Dashboard Setup Guide](./dashboard_guide.md) - How to visualize the optimization plan
- [Diagnostic Guide for Baseline Sensor](./technical/DIAGNOSTIC_GUIDE.md) - Similar troubleshooting for house load baseline

## 🆘 Still Need Help?

If you've followed all the steps above and still have issues:

1. **Check Recent Issues**: https://github.com/Bokbacken/energy_dispatcher/issues
2. **Open a New Issue**: Include:
   - Description of the problem
   - Value of `status` attribute
   - Screenshot of sensor attributes
   - Relevant log messages
   - Your configuration (anonymize personal details)
3. **Community Support**: Join the discussion in GitHub issues
