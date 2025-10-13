# Huawei Solar Reference Files

## Overview

This directory contains reference files from the [Huawei Solar Home Assistant Integration](https://github.com/wlcrs/huawei_solar) that were used to understand the available control functions for Huawei EMMA-based solar/battery systems.

## Files

### `services.py`
**Source:** Huawei Solar integration service handlers

**Purpose:** 
- Implementation reference for all Huawei Solar services
- Shows how to interact with the Huawei Solar API
- Documents register names and values
- Provides validation logic

**Key Contents:**
- Service handler implementations (forcible_charge, forcible_discharge, etc.)
- EMMA-specific service implementations
- Power control register mappings
- TOU period parsing logic
- Device validation functions

**Use:** Reference for understanding how to call Huawei Solar services from Energy Dispatcher adapters.

### `services.yaml`
**Source:** Huawei Solar integration service definitions

**Purpose:**
- Defines service schemas
- Documents required and optional parameters
- Specifies parameter types and ranges
- Provides UI selector configurations

**Key Contents:**
- Parameter definitions for all services
- Default values
- Min/max ranges
- Unit specifications (W, %, minutes, etc.)

**Use:** Reference for understanding parameter requirements and constraints when calling services.

### `strings.json`
**Source:** Huawei Solar integration UI translations

**Purpose:**
- UI strings and translations
- Entity names and descriptions
- Service descriptions
- Configuration options

**Key Contents:**
- Entity number controls (charging power, discharging power, etc.)
- Sensor names and descriptions
- Configuration flow strings

**Use:** Reference for understanding the meaning of various entities and parameters.

## How These Files Were Used

### Investigation Process

1. **Service Discovery**
   - Analyzed `services.py` to identify all available services
   - Documented EMMA-specific vs battery-specific services
   - Identified service parameters and constraints

2. **Parameter Understanding**
   - Used `services.yaml` to understand parameter types
   - Documented min/max values and units
   - Identified required vs optional parameters

3. **Entity Identification**
   - Used `strings.json` to understand entity purposes
   - Mapped entity names to your configuration
   - Identified useful sensors for integration

### Documentation Created

Based on these reference files, we created:

1. **`../huawei_emma_capabilities.md`**
   - Comprehensive documentation of all 13 control functions
   - Detailed parameter specifications
   - Code examples and recommendations
   - Integration patterns

2. **`../huawei_emma_quick_reference.md`**
   - Quick lookup tables
   - Common use case examples
   - Code snippets

3. **`../huawei_integration_summary.md`**
   - Integration strategy
   - Practical scenarios
   - Testing recommendations
   - Next steps

### Adapter Implementation

The reference files informed the implementation of:

**`custom_components/energy_dispatcher/adapters/huawei.py`:**
- `HuaweiBatteryAdapter` - Battery control methods
- `HuaweiEMMAAdapter` - Grid export control methods

## Key Insights from Reference Files

### 1. EMMA Architecture
From `services.py` lines 862-877:
```python
if has_battery:
    # When an EMMA is present, it is responsible for managing the battery.
    # No direct control of the battery is possible.
    if has_emma:
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TOU_PERIODS,
            partial(set_emma_tou_periods, hass),
            schema=EMMA_TOU_PERIODS_SCHEMA,
        )
```

**Insight:** EMMA controls battery; must use EMMA services, not direct battery services.

### 2. Power Control Registers
From `services.py` lines 505-516:
```python
POWER_CONTROL_REGISTERS = {
    "inverter": {
        "MODE_REGISTER": rn.ACTIVE_POWER_CONTROL_MODE,
        "POWER_WATT_REGISTER": rn.MAXIMUM_FEED_GRID_POWER_WATT,
        "POWER_PERCENT_REGISTER": rn.MAXIMUM_FEED_GRID_POWER_PERCENT,
    },
    "emma": {
        "MODE_REGISTER": rn.EMMA_POWER_CONTROL_MODE_AT_GRID_CONNECTION_POINT,
        "POWER_WATT_REGISTER": rn.EMMA_MAXIMUM_FEED_GRID_POWER_WATT,
        "POWER_PERCENT_REGISTER": rn.EMMA_MAXIMUM_FEED_GRID_POWER_PERCENT,
    },
}
```

**Insight:** EMMA has separate registers for grid control; need EMMA device ID for export control.

### 3. Duration Constraints
From `services.py` lines 384-386:
```python
duration = service_call.data[DATA_DURATION]
if duration > 1440:
    raise ValueError("Maximum duration is 1440 minutes")
```

**Insight:** 24-hour (1440 minute) maximum for time-based operations.

### 4. SOC Constraints
From `services.yaml` lines 52-59:
```yaml
target_soc:
  required: true
  default: 50
  selector:
    number:
      min: 12
      max: 100
      unit_of_measurement: "%"
```

**Insight:** Hardware minimum SOC is 12%, not configurable below this.

### 5. TOU Period Format
From `services.py` lines 257-273:
```python
HUAWEI_LUNA2000_TOU_PATTERN = r"([0-2]\d:\d\d-[0-2]\d:\d\d/[1-7]{0,7}/[+-]\n?){0,14}"

EMMA_TOU_PERIODS_SCHEMA = EMMA_DEVICE_SCHEMA.extend(
    {
        vol.Required(DATA_PERIODS): vol.All(
            cv.string,
            vol.Match(HUAWEI_LUNA2000_TOU_PATTERN),
        )
    }
)
```

**Insight:** TOU periods have strict format; max 14 periods; specific pattern required.

## Using These References

### When Implementing New Features

1. **Check `services.py`** for implementation details
   - How parameters are validated
   - What registers are set
   - Error handling patterns

2. **Check `services.yaml`** for parameter specs
   - Required vs optional
   - Min/max values
   - Default values
   - Units

3. **Check `strings.json`** for entity meanings
   - What each number entity controls
   - Sensor purposes
   - UI-friendly names

### Example: Understanding Forcible Charge

**From `services.yaml`:**
```yaml
forcible_charge:
  fields:
    device_id:
      required: true
    duration:
      required: true
      default: 60
      min: 1
      max: 1440
      unit_of_measurement: "minutes"
    power:
      required: true
      default: 1000
      selector: text
```

**From `services.py`:**
```python
async def forcible_charge(hass: HomeAssistant, service_call: ServiceCall) -> None:
    bridge, uc = get_battery_bridge(hass, service_call)
    power = await _validate_power_value(
        service_call.data[DATA_POWER], bridge, rn.STORAGE_MAXIMUM_CHARGE_POWER
    )
    
    await bridge.set(rn.STORAGE_FORCIBLE_CHARGE_POWER, power)
    await bridge.set(rn.STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD, duration)
    await bridge.set(rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_SETTING_MODE,
                     rv.StorageForcibleChargeDischargeTargetMode.TIME)
    await bridge.set(rn.STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE,
                     rv.StorageForcibleChargeDischarge.CHARGE)
```

**Learned:**
- Three required parameters: device_id, duration, power
- Duration is 1-1440 minutes
- Power is validated against STORAGE_MAXIMUM_CHARGE_POWER register
- Four registers are set to initiate charging
- Mode is set to TIME for duration-based control

## Limitations and Notes

### What These Files Don't Include

1. **Register Definitions**
   - Register names (rn.*) come from huawei_solar library
   - Register values (rv.*) come from huawei_solar library
   - Not included here; would need full library source

2. **Bridge Implementations**
   - HuaweiSolarBridge, HuaweiEMMABridge, HuaweiSUN2000Bridge
   - These are in the huawei_solar library
   - Handle actual Modbus communication

3. **Update Coordinators**
   - HuaweiSolarUpdateCoordinator implementation
   - Handles data refresh and coordination
   - Part of huawei_solar integration core

### Reference vs Implementation

These are **reference files only**, not part of Energy Dispatcher:
- ❌ Don't import these files in Energy Dispatcher code
- ❌ Don't modify these files (they're for reference)
- ✅ Use them to understand huawei_solar integration behavior
- ✅ Call huawei_solar services from Energy Dispatcher adapters
- ✅ Reference them when implementing new features

## Integration Architecture

```
┌─────────────────────────────────────┐
│   Energy Dispatcher Integration    │
├─────────────────────────────────────┤
│  ┌───────────────────────────────┐  │
│  │  HuaweiBatteryAdapter         │  │
│  │  HuaweiEMMAAdapter            │  │
│  └───────────────┬───────────────┘  │
│                  │ service calls     │
│                  ↓                   │
│  ┌───────────────────────────────┐  │
│  │  Home Assistant Service Layer │  │
│  └───────────────┬───────────────┘  │
└──────────────────┼───────────────────┘
                   │
                   ↓
┌─────────────────────────────────────┐
│   Huawei Solar Integration          │
├─────────────────────────────────────┤
│  ┌───────────────────────────────┐  │
│  │  services.py (this file)      │  │
│  │  - Service handlers           │  │
│  │  - Validation                 │  │
│  └───────────────┬───────────────┘  │
│                  │ bridge calls      │
│                  ↓                   │
│  ┌───────────────────────────────┐  │
│  │  HuaweiEMMABridge             │  │
│  │  HuaweiSUN2000Bridge          │  │
│  └───────────────┬───────────────┘  │
│                  │ modbus            │
└──────────────────┼───────────────────┘
                   │
                   ↓
┌─────────────────────────────────────┐
│   Physical Hardware                  │
├─────────────────────────────────────┤
│  ┌───────────────────────────────┐  │
│  │  EMMA Controller              │  │
│  │  - Battery management         │  │
│  │  - Grid connection control    │  │
│  └───────────────┬───────────────┘  │
│                  │                   │
│  ┌───────────────┴───────────────┐  │
│  │  LUNA2000 Battery (30 kWh)    │  │
│  │  - Charge/discharge           │  │
│  │  - SOC monitoring             │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Further Reading

### External Resources

- **Huawei Solar Integration:** https://github.com/wlcrs/huawei_solar
- **Huawei Solar Library:** https://github.com/wlcrs/huawei-solar-lib
- **Home Assistant Services:** https://www.home-assistant.io/docs/scripts/service-calls/

### Energy Dispatcher Documentation

- **Capabilities Reference:** `../huawei_emma_capabilities.md`
- **Quick Reference:** `../huawei_emma_quick_reference.md`
- **Integration Summary:** `../huawei_integration_summary.md`
- **Battery Cost Tracking:** `../battery_cost_tracking.md`

## Maintenance

### When Huawei Solar Integration Updates

If the huawei_solar integration is updated:

1. **Check for new services** in their services.py
2. **Check for changed parameters** in services.yaml
3. **Update our documentation** if new capabilities are available
4. **Test existing functionality** to ensure compatibility
5. **Update adapters** if API changes

### Version Information

These reference files were captured from:
- **Integration:** wlcrs/huawei_solar
- **Version:** Latest at time of analysis (2024)
- **Compatibility:** Home Assistant 2024.x

---

*These reference files were used to create comprehensive documentation for Huawei EMMA control capabilities in Energy Dispatcher.*
