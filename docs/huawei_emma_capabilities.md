# Huawei EMMA Solar/Battery System Capabilities

## Overview

This document describes the available control functions for Huawei solar/battery systems with EMMA (Energy Management and Monitoring Architecture) based on the Huawei Solar Home Assistant integration.

**Your Setup:**
- **System:** Huawei LUNA2000 battery with EMMA controller
- **Battery Capacity:** 30 kWh
- **Max Charge/Discharge Power:** 10 kW (10,000 W)
- **Device ID:** `5e572c76e307b4cc612e683a04bdb60a`
- **Integration:** `huawei_solar` (Home Assistant)

When EMMA is present, it acts as the central energy management controller. The EMMA is responsible for managing the battery, and no direct control of the battery hardware is possible - all battery control must go through EMMA services.

---

## Available Control Functions

The Huawei Solar integration provides the following services for EMMA-based systems:

### 1. Battery Charge/Discharge Control

#### 1.1 Forcible Charge (Time-based)
**Service:** `huawei_solar.forcible_charge`

Forces the battery to charge from the grid at a specified power level for a specific duration.

**Parameters:**
- `device_id` (required): The battery device ID
- `power` (required): Charge power in watts (W)
  - Must be ≤ max charge power (in your case: 10,000 W)
  - Specified as integer or string
- `duration` (required): Duration in minutes
  - Range: 1-1440 minutes (up to 24 hours)

**Example:**
```yaml
service: huawei_solar.forcible_charge
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
  power: 5000  # 5 kW
  duration: 120  # 2 hours
```

**How it works:**
- Sets the battery to charge mode at the specified power
- Charges for the specified duration
- Automatically stops after the duration expires
- Mode: `TIME` (time-based control)

---

#### 1.2 Forcible Charge (SOC-based)
**Service:** `huawei_solar.forcible_charge_soc`

Forces the battery to charge from the grid until a target State of Charge (SOC) is reached.

**Parameters:**
- `device_id` (required): The battery device ID
- `power` (required): Charge power in watts (W)
- `target_soc` (required): Target SOC percentage
  - Range: 12-100%

**Example:**
```yaml
service: huawei_solar.forcible_charge_soc
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
  power: 8000  # 8 kW
  target_soc: 90  # Charge to 90%
```

**How it works:**
- Sets the battery to charge mode at the specified power
- Charges until the target SOC is reached
- Automatically stops when SOC target is met
- Mode: `SOC` (SOC-based control)

---

#### 1.3 Forcible Discharge (Time-based)
**Service:** `huawei_solar.forcible_discharge`

Forces the battery to discharge at a specified power level for a specific duration.

**Parameters:**
- `device_id` (required): The battery device ID
- `power` (required): Discharge power in watts (W)
  - Must be ≤ max discharge power (in your case: 10,000 W)
- `duration` (required): Duration in minutes
  - Range: 1-1440 minutes

**Example:**
```yaml
service: huawei_solar.forcible_discharge
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
  power: 3000  # 3 kW
  duration: 60  # 1 hour
```

**Use cases:**
- Export energy to grid during high-price hours
- Reduce peak load from grid
- Emergency backup preparation

---

#### 1.4 Forcible Discharge (SOC-based)
**Service:** `huawei_solar.forcible_discharge_soc`

Forces the battery to discharge until a target SOC is reached.

**Parameters:**
- `device_id` (required): The battery device ID
- `power` (required): Discharge power in watts (W)
- `target_soc` (required): Target SOC percentage
  - Range: 12-100%

**Example:**
```yaml
service: huawei_solar.forcible_discharge_soc
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
  power: 5000  # 5 kW
  target_soc: 20  # Discharge to 20%
```

---

#### 1.5 Stop Forcible Charge/Discharge
**Service:** `huawei_solar.stop_forcible_charge`

Stops any active forcible charge or discharge operation and returns the battery to automatic mode.

**Parameters:**
- `device_id` (required): The battery device ID

**Example:**
```yaml
service: huawei_solar.stop_forcible_charge
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
```

**What it does:**
- Stops any ongoing forcible charge/discharge
- Resets discharge power to 0
- Resets period to 0
- Returns to normal battery operation mode

---

### 2. Grid Connection Power Control (EMMA)

When EMMA is present, it manages the grid connection point. These services control how much power can be fed to the grid.

#### 2.1 Reset Maximum Feed Grid Power
**Service:** `huawei_solar.reset_maximum_feed_grid_power`

Sets the grid connection to unlimited mode - no restriction on grid export.

**Parameters:**
- `device_id` (required): The EMMA device ID

**Example:**
```yaml
service: huawei_solar.reset_maximum_feed_grid_power
data:
  device_id: "your_emma_device_id"
```

**What it does:**
- Sets mode to `UNLIMITED`
- Removes all power export restrictions
- Sets power limits to 0 (meaning no limit)

---

#### 2.2 Set Zero Power Grid Connection
**Service:** `huawei_solar.set_zero_power_grid_connection`

Prevents any power export to the grid (zero export mode).

**Parameters:**
- `device_id` (required): The EMMA device ID

**Example:**
```yaml
service: huawei_solar.set_zero_power_grid_connection
data:
  device_id: "your_emma_device_id"
```

**What it does:**
- Sets mode to `ZERO_POWER_GRID_CONNECTION`
- System will not export any power to grid
- Excess solar will charge battery or be curtailed
- Useful in areas with no feed-in compensation or negative prices

---

#### 2.3 Set Maximum Feed Grid Power (Watts)
**Service:** `huawei_solar.set_maximum_feed_grid_power`

Limits grid export to a specific wattage.

**Parameters:**
- `device_id` (required): The EMMA device ID
- `power` (required): Maximum power in watts (W)
  - Can be negative (for import limit)
  - Must be ≥ -1000 W

**Example:**
```yaml
service: huawei_solar.set_maximum_feed_grid_power
data:
  device_id: "your_emma_device_id"
  power: 5000  # Limit export to 5 kW
```

**Use cases:**
- Comply with grid operator export limits
- Prevent grid overload during high production
- Control export during negative price periods

---

#### 2.4 Set Maximum Feed Grid Power (Percentage)
**Service:** `huawei_solar.set_maximum_feed_grid_power_percent`

Limits grid export to a percentage of inverter capacity.

**Parameters:**
- `device_id` (required): The EMMA device ID
- `power_percentage` (required): Maximum export as percentage
  - Range: 0-100%

**Example:**
```yaml
service: huawei_solar.set_maximum_feed_grid_power_percent
data:
  device_id: "your_emma_device_id"
  power_percentage: 50  # 50% of inverter capacity
```

**Note:** With 10 kW inverter capacity, 50% = 5 kW export limit.

---

### 3. Time-of-Use (TOU) Period Configuration

TOU periods allow you to define time-based rules for battery charge/discharge behavior.

#### 3.1 Set TOU Periods (EMMA)
**Service:** `huawei_solar.set_tou_periods`

Configures Time-of-Use periods for the EMMA-controlled battery.

**Parameters:**
- `device_id` (required): The EMMA device ID
- `periods` (required): Multi-line string defining TOU periods

**Period Format:**
```
HH:MM-HH:MM/DAYS/FLAG
```

Where:
- `HH:MM-HH:MM`: Time range (24-hour format)
- `DAYS`: Days of week (1=Monday, 7=Sunday)
  - Can combine multiple days: `1234567` = all days
  - Can be subset: `12345` = weekdays only
- `FLAG`: `+` for charge, `-` for discharge

**Example:**
```yaml
service: huawei_solar.set_tou_periods
data:
  device_id: "your_emma_device_id"
  periods: |
    00:00-06:00/1234567/+
    06:00-17:00/1234567/-
    17:00-21:00/1234567/-
    21:00-24:00/1234567/+
```

**What this example does:**
- **00:00-06:00 (all days):** Charge period - battery will charge from grid if needed
- **06:00-17:00 (all days):** Discharge period - battery can discharge
- **17:00-21:00 (all days):** Discharge period - cover evening peak
- **21:00-24:00 (all days):** Charge period - charge during low prices

**Limitations:**
- Maximum 14 periods
- Must follow pattern exactly
- Times must be valid (00:00-23:59)

**Use cases for Energy Dispatcher:**
- Define cheap charging windows based on Nordpool prices
- Set discharge periods during expensive hours
- Optimize battery usage with time-based strategies

---

## Integration Registers (Read/Write)

The EMMA controller exposes various registers that can be read or written. Here are the key ones:

### Battery Control Registers
- `STORAGE_FORCIBLE_CHARGE_POWER`: Charge power (W)
- `STORAGE_FORCIBLE_DISCHARGE_POWER`: Discharge power (W)
- `STORAGE_FORCED_CHARGING_AND_DISCHARGING_PERIOD`: Duration (minutes)
- `STORAGE_FORCIBLE_CHARGE_DISCHARGE_SOC`: Target SOC (%)
- `STORAGE_FORCIBLE_CHARGE_DISCHARGE_SETTING_MODE`: Mode (TIME or SOC)
- `STORAGE_FORCIBLE_CHARGE_DISCHARGE_WRITE`: Command (CHARGE, DISCHARGE, STOP)
- `STORAGE_MAXIMUM_CHARGE_POWER`: Max charge power limit (W)
- `STORAGE_MAXIMUM_DISCHARGE_POWER`: Max discharge power limit (W)

### EMMA Power Control Registers
- `EMMA_POWER_CONTROL_MODE_AT_GRID_CONNECTION_POINT`: Power control mode
- `EMMA_MAXIMUM_FEED_GRID_POWER_WATT`: Max export power (W)
- `EMMA_MAXIMUM_FEED_GRID_POWER_PERCENT`: Max export percentage (%)
- `EMMA_TOU_PERIODS`: Time-of-use periods configuration

### Power Control Modes
- `UNLIMITED`: No restriction on export
- `ZERO_POWER_GRID_CONNECTION`: No export to grid
- `POWER_LIMITED_GRID_CONNECTION_WATT`: Export limited by wattage
- `POWER_LIMITED_GRID_CONNECTION_PERCENT`: Export limited by percentage

---

## Current Energy Dispatcher Integration

### What's Already Implemented

The `HuaweiBatteryAdapter` currently implements:

```python
class HuaweiBatteryAdapter(BatteryAdapter):
    def supports_forced_charge(self) -> bool:
        return True

    async def async_force_charge(self, power_w: int, duration_min: int) -> None:
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_charge",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "duration": duration_min,
            },
            blocking=False,
        )

    async def async_cancel_force_charge(self) -> None:
        # Currently no-op
        return
```

### What's Missing / Could Be Enhanced

1. **Cancel Force Charge:**
   - Currently a no-op
   - Should call `stop_forcible_charge` service

2. **Forced Discharge:**
   - Not implemented in adapter
   - Could add methods for discharge control

3. **SOC-based Control:**
   - Not exposed in adapter
   - Could add `async_force_charge_to_soc()` method

4. **Grid Export Control:**
   - Not implemented in adapter
   - Could add methods to control export limits

5. **TOU Period Management:**
   - Not implemented in adapter
   - Could add methods to configure TOU periods dynamically

---

## Recommendations for Energy Dispatcher Integration

### 1. Enhanced Battery Adapter

Extend `HuaweiBatteryAdapter` with additional capabilities:

```python
class HuaweiBatteryAdapter(BatteryAdapter):
    # ... existing code ...
    
    async def async_cancel_force_charge(self) -> None:
        """Stop any forcible charge/discharge operation."""
        await self.hass.services.async_call(
            "huawei_solar",
            "stop_forcible_charge",
            {"device_id": self._device_id},
            blocking=False,
        )
    
    async def async_force_discharge(self, power_w: int, duration_min: int) -> None:
        """Force battery discharge for a specific duration."""
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_discharge",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "duration": duration_min,
            },
            blocking=False,
        )
    
    async def async_force_charge_to_soc(self, power_w: int, target_soc: int) -> None:
        """Force battery charge to a target SOC."""
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_charge_soc",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "target_soc": target_soc,
            },
            blocking=False,
        )
    
    async def async_force_discharge_to_soc(self, power_w: int, target_soc: int) -> None:
        """Force battery discharge to a target SOC."""
        await self.hass.services.async_call(
            "huawei_solar",
            "forcible_discharge_soc",
            {
                "device_id": self._device_id,
                "power": str(power_w),
                "target_soc": target_soc,
            },
            blocking=False,
        )
```

### 2. Grid Export Control

Add a separate adapter or extend existing one for grid control:

```python
class HuaweiEMMAAdapter:
    """Adapter for EMMA-specific grid control functions."""
    
    def __init__(self, hass: HomeAssistant, emma_device_id: str):
        self.hass = hass
        self._emma_device_id = emma_device_id
    
    async def async_set_zero_export(self) -> None:
        """Disable all grid export."""
        await self.hass.services.async_call(
            "huawei_solar",
            "set_zero_power_grid_connection",
            {"device_id": self._emma_device_id},
            blocking=False,
        )
    
    async def async_set_export_limit_w(self, power_w: int) -> None:
        """Set maximum grid export in watts."""
        await self.hass.services.async_call(
            "huawei_solar",
            "set_maximum_feed_grid_power",
            {
                "device_id": self._emma_device_id,
                "power": power_w,
            },
            blocking=False,
        )
    
    async def async_reset_export_limit(self) -> None:
        """Remove all export restrictions."""
        await self.hass.services.async_call(
            "huawei_solar",
            "reset_maximum_feed_grid_power",
            {"device_id": self._emma_device_id},
            blocking=False,
        )
```

### 3. TOU Period Configuration

For advanced Energy Dispatcher integration with TOU:

```python
async def async_set_tou_periods_from_plan(
    hass: HomeAssistant,
    emma_device_id: str,
    plan: list[dict]
) -> None:
    """
    Convert Energy Dispatcher plan to Huawei TOU periods.
    
    plan format: [
        {"start": "00:00", "end": "06:00", "mode": "charge", "days": [1,2,3,4,5,6,7]},
        {"start": "17:00", "end": "21:00", "mode": "discharge", "days": [1,2,3,4,5,6,7]},
    ]
    """
    periods = []
    for period in plan:
        days_str = "".join(str(d) for d in period["days"])
        flag = "+" if period["mode"] == "charge" else "-"
        periods.append(f"{period['start']}-{period['end']}/{days_str}/{flag}")
    
    periods_str = "\n".join(periods)
    
    await hass.services.async_call(
        "huawei_solar",
        "set_tou_periods",
        {
            "device_id": emma_device_id,
            "periods": periods_str,
        },
        blocking=False,
    )
```

### 4. Integration with Energy Dispatcher Planner

The planner could use these capabilities:

**Pre-peak hours (cheap electricity):**
- Use `forcible_charge` or `forcible_charge_soc` to charge battery
- Ensure battery has enough energy for expensive periods

**Peak hours (expensive electricity):**
- Use `forcible_discharge` to discharge battery and avoid grid import
- Could use `set_zero_power_grid_connection` to prevent any export during negative prices

**Normal hours:**
- Use `stop_forcible_charge` to return to automatic operation
- Use `reset_maximum_feed_grid_power` to allow normal export

**Export management:**
- During negative prices: `set_zero_power_grid_connection`
- During normal times: `reset_maximum_feed_grid_power` or set specific limit
- During high export prices: allow unlimited export

---

## Important Constraints and Considerations

### 1. Power Limits
- **Your max charge power:** 10,000 W (10 kW)
- **Your max discharge power:** 10,000 W (10 kW)
- Always validate power values don't exceed these limits
- The integration will reject commands exceeding limits

### 2. Duration Limits
- **Maximum duration:** 1,440 minutes (24 hours)
- Plan your charge/discharge windows accordingly
- For longer control periods, use TOU periods instead

### 3. SOC Limits
- **Minimum SOC:** 12% (hard limit in Huawei system)
- **Your configured floor:** 5% (but 12% is hardware minimum)
- **Your configured ceiling:** 100%
- **Backup power SOC:** Can be configured separately

### 4. EMMA Control Priority
- When EMMA is present, it has full control over the battery
- Cannot directly access battery registers
- All commands must go through EMMA services
- EMMA coordinates between solar, battery, grid, and load

### 5. Forcible Charge/Discharge Behavior
- Overrides normal battery operation
- Will charge from grid even if solar is available
- Remember to stop forcible operations when done
- System returns to automatic mode after stop

### 6. Grid Export Considerations
- Zero export mode may curtail excess solar
- Battery should be available to absorb excess
- Consider your grid operator requirements
- Respect any contractual export limits

### 7. TOU Period Interactions
- TOU periods work alongside forcible charge/discharge
- Forcible commands override TOU periods
- Maximum 14 TOU periods can be configured
- TOU periods persist until changed or system restart

---

## Usage Examples for Energy Dispatcher

### Example 1: Charge Before Peak Hours

```python
# At 02:00 - charge battery for morning peak
await adapter.async_force_charge(
    power_w=8000,  # 8 kW charging
    duration_min=180  # 3 hours (until 05:00)
)
```

### Example 2: Discharge During Peak Hours

```python
# At 17:00 - discharge during evening peak
await adapter.async_force_discharge(
    power_w=5000,  # 5 kW discharge
    duration_min=120  # 2 hours (until 19:00)
)
```

### Example 3: Prevent Export During Negative Prices

```python
# When price goes negative
await emma_adapter.async_set_zero_export()

# When price returns to normal
await emma_adapter.async_reset_export_limit()
```

### Example 4: SOC-based Optimization

```python
# Ensure battery is at 90% before expensive period
await adapter.async_force_charge_to_soc(
    power_w=10000,  # Max power
    target_soc=90
)

# Later, discharge to 20% during peak
await adapter.async_force_discharge_to_soc(
    power_w=8000,
    target_soc=20
)
```

### Example 5: Stop All Operations

```python
# Return to automatic mode
await adapter.async_cancel_force_charge()
```

---

## Configuration Notes

### Device IDs

You'll need two device IDs for full control:

1. **Battery Device ID:** `5e572c76e307b4cc612e683a04bdb60a` (already configured)
   - Used for: forcible_charge, forcible_discharge, stop_forcible_charge
   
2. **EMMA Device ID:** (need to identify in your HA instance)
   - Used for: grid export control, TOU periods
   - Found in: Developer Tools → Services → huawei_solar domain → device picker

### Finding Your EMMA Device ID

In Home Assistant:
1. Go to **Settings → Devices & Services**
2. Find **Huawei Solar** integration
3. Look for device named "EMMA" or similar
4. Click on it to get the device ID from the URL or device info

---

## Summary

The Huawei EMMA system provides comprehensive control over:

✅ **Battery Charging/Discharging**
- Time-based and SOC-based control
- Forcible charge/discharge commands
- Stop/cancel operations

✅ **Grid Export Management**
- Zero export mode
- Power-limited export (W or %)
- Unlimited export mode

✅ **Time-of-Use Optimization**
- Define up to 14 TOU periods
- Charge/discharge based on time and day
- Automated battery behavior

**Key for Energy Dispatcher:**
- Use forcible charge during cheap electricity hours
- Use forcible discharge during expensive hours
- Control grid export during negative price periods
- Integrate with price forecasts for optimal battery scheduling
- Ensure operations are stopped when returning to automatic mode

This gives Energy Dispatcher powerful tools to minimize electricity costs and optimize battery usage based on Nordpool spot prices! 🔋⚡
