# Battery Energy Cost Tracking Fix - v0.8.28

## Issue Summary

Battery charges were incorrectly classified as "solar" (free) when they should be "grid" (with cost) when the optional `load_power_entity` sensor was not configured. This led to the Battery Energy Cost sensor showing 0.0 SEK/kWh when the battery was actually charging from the grid at current grid prices.

## Problem Details

### Root Cause
In the `_update_battery_charge_tracking()` method in `coordinator.py`:

1. When `load_power_entity` is not configured, `load_power_w` defaults to 0.0
2. The PV surplus calculation becomes: `pv_surplus_w = max(0.0, pv_power_w - 0.0)` = full PV power
3. Battery charging is classified as "solar" whenever there's ANY PV production
4. This is incorrect because the house may be consuming most of the PV power, requiring the battery to charge from the grid

### User Impact
- **Battery Energy Cost sensor** shows 0.0 SEK/kWh instead of actual grid price
- **Battery vs Grid Price Delta** becomes incorrectly negative
- Users cannot make informed decisions about when to charge/discharge battery
- Cost tracking and optimization features become unreliable

### Affected Users
Users who:
- Have configured battery energy tracking sensors (`batt_energy_charged_today_entity`)
- Have NOT configured the optional `load_power_entity` sensor
- Are using systems like Huawei LUNA2000 where load sensor may not be readily available

## Solution Implemented

### Conservative Approach
When `load_power_entity` is not configured, the system now uses a conservative approach:

1. **With Load Sensor** (original behavior):
   - Calculate PV surplus: `pv_surplus_w = pv_power_w - load_power_w`
   - Classify as solar if: `pv_surplus_w >= charge_power_w * 0.8` (80% threshold)

2. **Without Load Sensor** (new conservative behavior):
   - Cannot calculate accurate PV surplus (unknown house load)
   - Classify as solar ONLY if: `pv_power_w >= charge_power_w * 2.0` (200% threshold)
   - This assumes some unknown house load exists

### Rationale for 2.0x Multiplier
- With no load sensor, we cannot know how much of the PV power is being consumed by the house
- A 2x multiplier provides safety margin for typical house loads
- Example: If battery charges at 4kW, PV must be at least 8kW to confidently classify as solar
- This prevents incorrectly classifying grid charging as free solar charging

### Implementation Details

**Changed Logic:**
```python
# Detect if load sensor is configured and available
load_power_entity = self._get_cfg(CONF_LOAD_POWER_ENTITY, "")
load_power_w_raw = self._read_watts(load_power_entity)
has_load_sensor = load_power_w_raw is not None
load_power_w = load_power_w_raw if has_load_sensor else 0.0

# Conservative classification based on sensor availability
if has_load_sensor:
    # Accurate calculation with load sensor
    pv_surplus_w = max(0.0, pv_power_w - load_power_w)
    is_solar = pv_surplus_w >= charge_power_w * 0.8
else:
    # Conservative approach without load sensor
    is_solar = pv_power_w >= charge_power_w * 2.0
```

**Enhanced Logging:**
```
Battery charged: 0.500 kWh from grid @ 2.500 SEK/kWh (PV: 5000.0 W, Load: 0.0 W [estimated], Charge: 4000.0 W)
```

The `[estimated]` marker indicates when load sensor is missing.

## Testing

### New Test Cases Added

1. **test_charge_without_load_sensor_grid**
   - Scenario: 5kW PV, 4kW battery charging, no load sensor
   - Expected: Classified as "grid" (5kW < 4kW * 2.0)
   - Result: ✅ Pass

2. **test_charge_without_load_sensor_solar**
   - Scenario: 10kW PV, 3kW battery charging, no load sensor
   - Expected: Classified as "solar" (10kW >= 3kW * 2.0)
   - Result: ✅ Pass

### Test Results
- ✅ All 13 battery tracking tests pass
- ✅ All 46 BEC (Battery Energy Cost) tests pass
- ✅ Backward compatibility maintained

## Documentation Updates

Updated `docs/configuration.md` to clarify:
- Load sensor is **highly recommended** for accurate battery cost tracking
- Impact of missing load sensor on cost classification
- Conservative behavior when sensor is not configured

## Recommendations for Users

### If You Experience This Issue
1. **Check your Battery Energy Cost sensor** - If it shows 0.0 SEK/kWh frequently, you may be affected
2. **Configure load_power_entity** if available from your inverter/energy meter
3. **Update to v0.8.28** to get the conservative fix

### Best Practice
For accurate battery energy cost tracking, configure:
- ✅ `batt_energy_charged_today_entity` (required for tracking)
- ✅ `batt_energy_discharged_today_entity` (required for tracking)
- ✅ `load_power_entity` (highly recommended for accuracy)
- ✅ `batt_power_entity` (recommended for better charge power estimation)

### Huawei LUNA2000 Users
Your system provides:
- ✅ `PV output power` → Use for `pv_power_entity`
- ✅ `Energy charged today` → Use for `batt_energy_charged_today_entity`
- ✅ `Energy discharged today` → Use for `batt_energy_discharged_today_entity`
- ✅ `Total energy consumption` → This is total house consumption, not instantaneous load
- ⚠️ Instantaneous house load may not be directly available

If your Huawei system doesn't expose instantaneous load power:
- The fix in v0.8.28 will use the conservative 2x multiplier
- Battery charging will be more frequently classified as "grid" (safer)
- Consider adding a separate power meter to measure house load for accuracy

## Migration

No action required. The fix is backward compatible:
- Systems with `load_power_entity` configured → No change in behavior
- Systems without `load_power_entity` → Automatic conservative classification

## Version Information

- **Fixed in**: v0.8.28
- **Previous version**: v0.8.27
- **Files changed**:
  - `custom_components/energy_dispatcher/coordinator.py`
  - `tests/test_battery_tracking.py`
  - `docs/configuration.md`
  - `custom_components/energy_dispatcher/manifest.json`

## Related Issues

This fix addresses user reports of:
- Battery Energy Cost often showing 0.0 SEK/kWh
- Incorrect classification of grid charging as solar charging
- Battery vs Grid Price Delta showing incorrect negative values
