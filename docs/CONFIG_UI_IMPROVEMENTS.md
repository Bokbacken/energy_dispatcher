# Configuration UI Improvements - Visual Guide

This document shows how the configuration UI has been improved for Energy Dispatcher.

## Overview

The configuration flow has been enhanced with Home Assistant's modern selector system, providing:
- ✅ Entity dropdowns with autocomplete
- ✅ Range validation on numeric inputs
- ✅ Helpful descriptions for every field
- ✅ Type-safe entity selection (filtered by domain)

## Before vs After

### Entity Selection

#### ❌ Before
```yaml
# User had to manually type entity IDs
Field: "nordpool_entity"
Type: Plain text input
User types: "sensor.nordpool_kwh_se3_sek_3_10_025"
Problems:
  - Easy to make typos
  - No autocomplete
  - No validation if entity exists
  - Hard to discover available entities
```

#### ✅ After
```yaml
# User selects from dropdown with autocomplete
Field: "Nordpool Spot Price Sensor"
Type: Entity selector (filtered to 'sensor' domain)
Description: "Select your Nordpool spot price sensor (e.g., sensor.nordpool_kwh_se3_sek_3_10_025)"
Features:
  ✓ Dropdown shows all available sensors
  ✓ Autocomplete/search functionality
  ✓ Only shows valid sensor entities
  ✓ Entity state preview
```

### Numeric Inputs

#### ❌ Before
```yaml
Field: "batt_cap_kwh"
Type: Text input with vol.Coerce(float)
User could enter:
  - "abc" → Runtime error
  - "-5" → Invalid negative value
  - "1000" → Unrealistic value
No guidance on valid range
```

#### ✅ After
```yaml
Field: "Battery Capacity (kWh)"
Type: Number selector
Range: 1 - 100 kWh
Step: 0.5
Description: "Total usable capacity of your home battery in kWh"
Features:
  ✓ Prevents entering values outside range
  ✓ Shows +/- buttons for easy adjustment
  ✓ Clear min/max boundaries
  ✓ Appropriate step increment
```

### Boolean Options

#### ❌ Before
```yaml
Field: "fs_use"
Type: Plain boolean
No label or description
```

#### ✅ After
```yaml
Field: "Use Forecast.Solar"
Type: Toggle switch
Description: "Enable solar production forecasting using Forecast.Solar"
Features:
  ✓ Visual toggle switch
  ✓ Clear on/off state
  ✓ Helpful description
```

## Configuration Flow Sections

### 1. Price Configuration

**Fields with selectors:**
- `nordpool_entity` → EntitySelector (sensor)
- `price_tax` → NumberSelector (0-10 SEK/kWh, step 0.01)
- `price_transfer` → NumberSelector (0-10 SEK/kWh, step 0.01)
- `price_surcharge` → NumberSelector (0-10 SEK/kWh, step 0.01)
- `price_vat` → NumberSelector (0-1, step 0.01)
- `price_fixed_monthly` → NumberSelector (0-10000 SEK, step 1)
- `price_include_fixed` → BooleanSelector

**Each field includes:**
- Clear label with units
- Description of what it does
- Example values
- Valid range indication

### 2. Battery Configuration

**Fields with selectors:**
- `batt_cap_kwh` → NumberSelector (1-100 kWh, step 0.5)
- `batt_soc_entity` → EntitySelector (sensor)
- `batt_max_charge_w` → NumberSelector (100-50000 W, step 100)
- `batt_max_disch_w` → NumberSelector (100-50000 W, step 100)
- `batt_adapter` → SelectSelector (dropdown: ["huawei"])
- `huawei_device_id` → TextSelector

**Benefits:**
- Battery SOC sensor: Dropdown filtered to only show sensors
- Power limits: Number inputs with realistic ranges
- Adapter: Dropdown for future extensibility

### 3. EV & EVSE Configuration

**Fields with selectors:**
- `ev_mode` → SelectSelector (["manual"])
- `ev_batt_kwh` → NumberSelector (10-200 kWh, step 1)
- `ev_current_soc` → NumberSelector (0-100%, step 1)
- `ev_target_soc` → NumberSelector (0-100%, step 1)
- `evse_start_switch` → EntitySelector (switch)
- `evse_stop_switch` → EntitySelector (switch)
- `evse_current_number` → EntitySelector (number)
- `evse_min_a` → NumberSelector (6-32 A, step 1)
- `evse_max_a` → NumberSelector (6-32 A, step 1)
- `evse_phases` → NumberSelector (1-3, step 1)
- `evse_voltage` → NumberSelector (180-250 V, step 1)

**Benefits:**
- EVSE entities: Type-safe selection (switch for switches, number for current)
- Current limits: Validated to realistic charger ranges (6-32A)
- Percentage fields: Automatically limited to 0-100%

### 4. Solar Forecast Configuration

**Fields with selectors:**
- `fs_use` → BooleanSelector
- `fs_apikey` → TextSelector
- `fs_lat` → NumberSelector (-90 to 90, step 0.000001)
- `fs_lon` → NumberSelector (-180 to 180, step 0.000001)
- `fs_planes` → TextSelector (multiline for JSON)
- `fs_horizon` → TextSelector

**Benefits:**
- Latitude/Longitude: Precise decimal input with geographic range validation
- JSON configuration: Multiline text area for better readability
- Clear descriptions explain format and provide examples

### 5. Baseline Load Configuration

**Fields with selectors:**
- `runtime_source` → SelectSelector (["counter_kwh", "power_w", "manual_dayparts"])
- `runtime_counter_entity` → EntitySelector (sensor)
- `runtime_power_entity` → EntitySelector (sensor)
- `load_power_entity` → EntitySelector (sensor)
- `batt_power_entity` → EntitySelector (sensor)
- `grid_import_today_entity` → EntitySelector (sensor)
- `runtime_alpha` → NumberSelector (0-1, step 0.01)
- `runtime_window_min` → NumberSelector (5-60 min, step 1)
- `runtime_exclude_ev` → BooleanSelector
- `runtime_exclude_batt_grid` → BooleanSelector
- `runtime_soc_floor` → NumberSelector (0-100%, step 1)
- `runtime_soc_ceiling` → NumberSelector (0-100%, step 1)

**Benefits:**
- Method selection: Dropdown clearly shows available calculation methods
- All sensors: Type-safe entity selection
- Alpha factor: Range-limited to valid 0-1 values
- Exclusion options: Clear toggle switches

## Translation Structure

Each field now has two translations:

### Field Label (`data`)
```json
"batt_cap_kwh": "Battery Capacity (kWh)"
```
Short, clear label with units shown in UI

### Field Description (`data_description`)
```json
"batt_cap_kwh": "Total usable capacity of your home battery in kWh"
```
Detailed explanation shown as help text below field

## User Experience Flow

### Old Flow (Before)
1. User sees text input labeled `batt_cap_kwh`
2. User guesses what this means
3. User types "15" (hopes it's in kWh)
4. User submits → May get error if format wrong
5. User searches documentation or asks for help

### New Flow (After)
1. User sees "Battery Capacity (kWh)" with number spinner
2. Reads description: "Total usable capacity of your home battery in kWh"
3. Sees range: 1-100, current value: 15.0
4. Adjusts with +/- buttons or types directly
5. Cannot submit invalid value (validated at input time)
6. Confident setup, no errors

## Technical Implementation

### Selector Examples

```python
# Entity selector with domain filtering
vol.Required(CONF_NORDPOOL_ENTITY): selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)

# Number selector with validation
vol.Optional(CONF_BATT_CAP_KWH): selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=1, 
        max=100, 
        step=0.5, 
        mode=selector.NumberSelectorMode.BOX
    )
)

# Boolean selector for toggles
vol.Optional(CONF_FS_USE): selector.BooleanSelector()

# Select selector for dropdowns
vol.Optional(CONF_RUNTIME_SOURCE): selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=["counter_kwh", "power_w", "manual_dayparts"],
        mode=selector.SelectSelectorMode.DROPDOWN
    )
)

# Text selector with multiline for JSON
vol.Optional(CONF_FS_PLANES): selector.TextSelector(
    selector.TextSelectorConfig(multiline=True)
)
```

## Benefits Summary

### For Users
- **Easier**: Entity dropdowns with autocomplete vs manual typing
- **Safer**: Input validation prevents configuration errors
- **Clearer**: Every field has helpful description
- **Faster**: Less time figuring out what each setting means
- **Better**: Professional, modern UI consistent with Home Assistant

### For Support
- **Fewer errors**: Validation catches issues at input time
- **Fewer questions**: Descriptions answer most common questions
- **Better experience**: Users succeed on first try

### For Developers
- **Best practices**: Follows Home Assistant standards
- **Type safety**: Selectors enforce correct entity types
- **Maintainable**: Clear, well-documented code
- **Extensible**: Easy to add new fields with same pattern

## Related Documentation

- **[Configuration Guide](configuration.md)** - Complete setup instructions
- **[Changelog](CHANGELOG_CONFIG_IMPROVEMENTS.md)** - Detailed list of changes
- **[Home Assistant Selectors](https://www.home-assistant.io/docs/blueprint/selectors/)** - Official selector documentation
