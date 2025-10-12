# Energy Dispatcher - Configuration Improvements Summary

This document summarizes the improvements made to fix the House Baseline issue and enhance the configuration flow.

## Issues Addressed

### 1. ✅ Fixed "'set' object has no attribute 'lower'" Error

**Problem:** The `_calculate_48h_baseline()` method was creating a set of entity IDs and passing it to Home Assistant's `history.state_changes_during_period()` API, which expects a list.

**Solution:** Changed `entities_to_fetch` from a set to a list in `coordinator.py` line 362.

```python
# Before (line 362):
entities_to_fetch = {house_energy_ent}

# After:
entities_to_fetch = [house_energy_ent]
```

**Impact:** The baseline calculation now works correctly without throwing exceptions.

---

### 2. ✅ Added Unit Specifications to Configuration

**Problem:** Configuration fields did not clearly indicate what units should be used (W, kW, kWh, etc.), leading to confusion.

**Solution:** Updated `translations/en.json` to include units in all relevant field labels and descriptions.

**Fields Updated:**
- **Power sensors:** Added (W) or (W or kW) indicators
- **Energy sensors:** Added (kWh) or (kWh or Wh) indicators  
- **Current sensors:** Added (A) for Amperes
- **Voltage sensors:** Added (V) for Volts
- **Percentage sensors:** Added (%)
- **Capacity fields:** Added (kWh) for battery and EV capacity

**New Fields Added:**
- `evse_power_sensor`: "EVSE Charging Power Sensor (W or kW)"
- `evse_energy_sensor`: "EVSE Session Energy Sensor (kWh or Wh)"
- `evse_total_energy_sensor`: "EVSE Total Energy Counter (kWh)"
- `pv_total_energy_entity`: "PV Total Energy Counter (kWh)"
- `batt_capacity_entity`: "Battery Capacity Sensor (kWh)"
- `batt_total_charged_energy_entity`: "Battery Total Charged Energy Counter (kWh)"
- `runtime_counter_entity`: Updated to "House Energy Counter (kWh)"

**Impact:** Users now know exactly what units each sensor should report.

---

### 3. ✅ Implemented Entity Selectors with Domain Filtering

**Problem:** Users had to manually type entity IDs, making configuration error-prone and difficult.

**Solution:** Replaced string validators with Home Assistant's modern selector system in `config_flow.py`.

#### Selector Types Implemented:

##### EntitySelector (with domain filtering)
Used for all entity/sensor fields to provide dropdown pickers:

```python
# Example: Battery SOC Sensor
vol.Required(CONF_BATT_SOC_ENTITY, default=d.get(CONF_BATT_SOC_ENTITY, "")): selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
),
```

**Entity selectors by domain:**
- `domain="sensor"`: All energy, power, capacity sensors
- `domain="switch"`: EVSE start/stop switches  
- `domain="number"`: EVSE current control
- `domain="weather"`: Weather entity for forecasting

##### NumberSelector (with validation)
Used for numeric fields with min/max ranges and units:

```python
# Example: Battery Capacity
vol.Required(CONF_BATT_CAP_KWH, default=d.get(CONF_BATT_CAP_KWH, 15.0)): selector.NumberSelector(
    selector.NumberSelectorConfig(min=1, max=100, step=0.5, unit_of_measurement="kWh", mode=selector.NumberSelectorMode.BOX)
),
```

**Number fields configured:**
- Battery capacity: 1-100 kWh, step 0.5
- Battery charge/discharge power: 100-20000 W, step 100
- EV battery capacity: 10-200 kWh, step 0.5
- EV SOC: 0-100%, step 1
- EVSE current: 6-32 A, step 1
- EVSE voltage: 110-240 V, step 1
- EVSE phases: 1 or 3 (step 2)
- Runtime lookback: 12-168 hours, step 1
- SOC floor/ceiling: 0-100%, step 1
- Latitude: -90 to 90, step 0.0001
- Longitude: -180 to 180, step 0.0001
- Price fields with appropriate ranges

##### BooleanSelector
Used for all boolean toggles:
- `fs_use`: Enable Solar Forecasting
- `price_include_fixed`: Include Fixed Fee
- `runtime_use_dayparts`: Use Time-of-Day Weighting
- `runtime_exclude_ev`: Exclude EV Charging from Baseline
- `runtime_exclude_batt_grid`: Exclude Battery Grid Charging
- `manual_calibration_enabled`: Enable Manual Calibration
- `auto_create_dashboard`: Auto-create Dashboard

##### SelectSelector
Used for dropdown choices:
- Battery adapter: ["huawei"]
- EV mode: ["manual"]
- Forecast source: ["forecast_solar", "manual_physics"]

##### TextSelector
Used for free-form text and JSON:
- API keys
- Device IDs
- Solar panel configuration JSON (multiline)
- Horizon values (comma-separated)

**Impact:** 
- Dramatically improved user experience
- Prevents invalid entity selections
- Enforces valid value ranges
- Shows units directly in the UI
- Provides autocomplete for entities
- Reduces configuration errors

---

## Files Modified

1. **`custom_components/energy_dispatcher/coordinator.py`**
   - Fixed set-to-list conversion for entity fetching (1 line changed)

2. **`custom_components/energy_dispatcher/config_flow.py`**
   - Added selector imports
   - Replaced 58 field validators with appropriate selectors
   - 155 lines added, 58 lines modified

3. **`custom_components/energy_dispatcher/translations/en.json`**
   - Added 13 new field labels with units
   - Updated 15 existing field labels to include units
   - Added detailed descriptions for 10 energy counter fields
   - 40 lines added, 13 lines modified

---

## Testing

All existing tests pass:
- ✅ 15 config flow tests
- ✅ 3 baseline classification tests
- ✅ Syntax validation for Python files
- ✅ JSON validation for translation files

---

## Benefits

### For Users:
1. **No more baseline calculation errors** - The set object exception is fixed
2. **Clear unit indicators** - Know exactly what units each sensor should report
3. **Entity pickers with autocomplete** - No more typing entity IDs manually
4. **Value validation** - Can't enter out-of-range values
5. **Better discoverability** - Can browse available entities by type
6. **Reduced errors** - Domain filtering ensures only valid entities are selectable

### For Developers:
1. **Follows Home Assistant best practices** - Uses modern selector system
2. **Type-safe configuration** - Selectors enforce proper types
3. **Maintainable code** - Clear separation of concerns
4. **Better UX consistency** - Matches other Home Assistant integrations
5. **Extensible** - Easy to add new fields with proper validation

---

## Usage Examples

### Before (Old String-based Config):
```yaml
# User had to manually type entity IDs (error-prone)
runtime_counter_entity: "sensor.house_energy"  # Hope this is right!
batt_cap_kwh: 15.0  # Is this in kWh or Wh?
evse_min_a: 6  # What unit?
```

### After (Selector-based Config with UI):
- **Entity fields:** Dropdown with all available sensors filtered by domain
- **Number fields:** +/- buttons with min/max enforcement and unit display
- **Boolean fields:** Toggle switches
- **Select fields:** Dropdown menus with valid options

Users see:
- "House Energy Counter (kWh)" with dropdown of all sensors
- "Battery Capacity (kWh)" with number input showing range 1-100 kWh
- "EVSE Minimum Current (A)" with number input showing range 6-32 A

---

## Documentation Updates Needed

The following documentation should be updated to reflect these changes:
1. `docs/configuration.md` - Update field descriptions to mention selectors
2. `docs/getting_started.md` - Update setup instructions with new UI
3. `README.md` - Add note about improved configuration UI

---

## Parameters Used in Baseline Calculation

Based on the problem statement requirement to specify what parameters are used in the baseline method:

### Parameters Used in `_calculate_48h_baseline()`:

1. **`runtime_counter_entity`** (House Energy Counter - kWh)
   - **Required:** Yes
   - **Type:** Energy counter sensor (cumulative kWh)
   - **Purpose:** Main sensor for calculating house baseline consumption
   - **Usage:** Fetches 48h history to calculate delta-based consumption

2. **`runtime_lookback_hours`** (Historical Lookback Period - hours)
   - **Default:** 48
   - **Range:** 12-168 hours
   - **Purpose:** How many hours of history to analyze

3. **`runtime_use_dayparts`** (Use Time-of-Day Weighting)
   - **Default:** True
   - **Purpose:** Calculate separate baselines for night/day/evening

4. **`runtime_exclude_ev`** (Exclude EV Charging from Baseline)
   - **Default:** True
   - **Purpose:** Remove EV charging from baseline calculation
   - **Requires:** `evse_total_energy_sensor` to be configured

5. **`evse_total_energy_sensor`** (EVSE Total Energy Counter - kWh)
   - **Optional:** Only needed if `runtime_exclude_ev` is True
   - **Type:** Energy counter sensor (cumulative kWh)
   - **Purpose:** Track EV charging to exclude from baseline

6. **`runtime_exclude_batt_grid`** (Exclude Battery Grid Charging)
   - **Default:** True
   - **Purpose:** Remove battery grid charging from baseline
   - **Requires:** `batt_total_charged_energy_entity` and optionally `pv_total_energy_entity`

7. **`batt_total_charged_energy_entity`** (Battery Total Charged Energy Counter - kWh)
   - **Optional:** Only needed if `runtime_exclude_batt_grid` is True
   - **Type:** Energy counter sensor (cumulative kWh)
   - **Purpose:** Track battery charging to exclude from baseline

8. **`pv_total_energy_entity`** (PV Total Energy Counter - kWh)
   - **Optional:** Only needed if `runtime_exclude_batt_grid` is True
   - **Type:** Energy counter sensor (cumulative kWh)
   - **Purpose:** Track solar generation to determine if battery was charged from grid or solar

---

## Future Improvements

Potential enhancements for future releases:
1. Add device class filtering to entity selectors (e.g., only show energy sensors)
2. Add validation warnings for misconfigured sensors
3. Implement dynamic field visibility based on other selections
4. Add Swedish translations with units
5. Create visual configuration guide with screenshots
