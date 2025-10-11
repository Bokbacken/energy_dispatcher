# Battery Energy Cost - Energy Delta Based Calculation

## Overview

This document describes the improved battery energy cost calculation that uses **energy deltas (kWh)** instead of instantaneous power (W) measurements. This approach is more accurate, reliable, and safer for determining whether battery charging is from solar or grid.

## Problem with Power-Based Approach (Previous Method)

The previous implementation used instantaneous power measurements:
- PV power (W)
- House load power (W)  
- Battery charging power (W)

**Issues:**
1. **Measurement timing**: Power readings can be taken at slightly different times
2. **Load sensor dependency**: Required optional `load_power_entity` to be configured
3. **Estimation errors**: Power spikes or dips could cause misclassification
4. **Conservative thresholds needed**: Without load sensor, had to use 2x multiplier to be safe

## Energy Delta Approach (New Method)

The new implementation uses **accumulated energy deltas (kWh)** over the same time period:

```python
# Compare energy deltas over the same 5-minute interval
delta_pv_energy = pv_energy_today_now - pv_energy_today_prev
delta_battery_charged = battery_charged_today_now - battery_charged_today_prev
delta_grid_import = grid_import_today_now - grid_import_today_prev

# Simple, reliable logic:
if delta_pv_energy >= delta_battery_charged * 0.95:
    source = "solar"  # PV energy covered the battery charge
else:
    source = "grid"   # Not enough PV, must be from grid
```

## Advantages

### 1. **Direct Energy Comparison**
- Compares apples-to-apples: kWh to kWh
- No need to estimate or extrapolate
- More accurate representation of actual energy flow

### 2. **Time-Synchronized Measurements**
- All sensors reset at midnight
- Deltas calculated from same "today" counters
- Measurements are inherently synchronized over the update interval

### 3. **No Load Sensor Required**
- PV delta tells us how much solar was generated
- Battery delta tells us how much was charged
- If PV ≥ battery charge, it's solar - simple!
- Load consumption is implicitly accounted for in the delta

### 4. **Grid Import Verification**
- When available, `grid_import_today` provides additional confirmation
- If grid was imported during charging, definitely from grid

### 5. **Measurement Tolerance**
- Uses 95% threshold (0.95) to account for sensor measurement accuracy
- More lenient than power-based 80% threshold
- Accounts for rounding errors in energy counters

## Required Sensors

### Essential
- `batt_energy_charged_today_entity` - Battery energy charged today (kWh) - **Required**
- `batt_energy_discharged_today_entity` - Battery energy discharged today (kWh) - **Required**

### Recommended for Accurate Classification
- `pv_energy_today_entity` - PV energy generated today (kWh) - **Highly recommended**
  - Without this, all charges default to "grid" (conservative)

### Optional for Additional Verification
- `grid_import_today_entity` - Grid energy imported today (kWh) - Optional
  - Provides additional confirmation when available

## Examples

### Example 1: Clear Solar Charging
```
Time: 12:00 - 12:05 (5-minute update interval)

Previous values (12:00):
- Battery charged today: 10.0 kWh
- PV energy today: 8.0 kWh

Current values (12:05):
- Battery charged today: 10.5 kWh  → delta = 0.5 kWh
- PV energy today: 8.6 kWh         → delta = 0.6 kWh

Classification:
- PV delta (0.6) >= Battery delta (0.5) * 0.95 = 0.475? YES
- Result: SOLAR charging @ 0.00 SEK/kWh ✅
```

### Example 2: Grid Charging (Insufficient PV)
```
Time: 18:00 - 18:05 (evening, low sun)

Previous values (18:00):
- Battery charged today: 12.0 kWh
- PV energy today: 15.0 kWh

Current values (18:05):
- Battery charged today: 12.5 kWh  → delta = 0.5 kWh
- PV energy today: 15.2 kWh        → delta = 0.2 kWh

Classification:
- PV delta (0.2) >= Battery delta (0.5) * 0.95 = 0.475? NO
- Result: GRID charging @ 2.50 SEK/kWh ✅
```

### Example 3: Without PV Energy Sensor
```
Previous values:
- Battery charged today: 10.0 kWh
- PV energy today: not configured

Current values:
- Battery charged today: 10.5 kWh  → delta = 0.5 kWh
- PV energy today: not available

Classification:
- No PV energy data available
- Result: GRID charging @ 2.50 SEK/kWh (conservative default) ✅
```

### Example 4: With Grid Import Verification
```
Time: 16:00 - 16:05 (cloudy day)

Previous values (16:00):
- Battery charged today: 8.0 kWh
- PV energy today: 12.0 kWh
- Grid import today: 3.0 kWh

Current values (16:05):
- Battery charged today: 8.5 kWh   → delta = 0.5 kWh
- PV energy today: 12.3 kWh        → delta = 0.3 kWh
- Grid import today: 3.2 kWh       → delta = 0.2 kWh

Classification:
- PV delta (0.3) < Battery delta (0.5) * 0.95? YES, insufficient
- Grid import delta > 0? YES, grid was used
- Result: GRID charging @ 2.50 SEK/kWh ✅
```

## Implementation Details

### Data Tracking
```python
# Added to coordinator __init__:
self._prev_pv_energy_today: Optional[float] = None
self._prev_house_energy: Optional[float] = None
self._prev_grid_import_today: Optional[float] = None
```

### Daily Reset
```python
# Reset at midnight:
if self._batt_last_reset_date != current_date:
    self._batt_prev_charged_today = None
    self._batt_prev_discharged_today = None
    self._prev_pv_energy_today = None
    self._prev_house_energy = None
    self._prev_grid_import_today = None
```

### Classification Logic
```python
# Calculate deltas
delta_charged = charged_today - self._batt_prev_charged_today
delta_pv = pv_energy_today - self._prev_pv_energy_today
delta_grid_import = grid_import_today - self._prev_grid_import_today

# Determine source
source = "grid"  # Default conservative

if delta_pv > 0:
    # PV production available
    if delta_pv >= delta_charged * 0.95:
        source = "solar"  # PV covers charge
    elif delta_grid_import > 0:
        source = "grid"  # Grid was imported
    else:
        source = "grid"  # Be conservative

# Use enriched price for grid charging
cost = 0.0 if source == "solar" else current_enriched_price
```

## Comparison: Old vs New

### Old Power-Based Method
```
Scenario: Battery charging 4 kW, PV producing 6 kW

Without load sensor:
- Assumed load = 0 W
- PV surplus = 6 kW
- Check: 6 kW >= 4 kW * 2.0? NO
- Result: GRID (too conservative)

With load sensor (3 kW):
- PV surplus = 6 - 3 = 3 kW
- Check: 3 kW >= 4 kW * 0.8? NO
- Result: GRID ❌ (wrong if battery charged at 3 kW from solar)
```

### New Energy-Delta Method
```
Scenario: Same 5-minute period

Measured deltas:
- Battery charged: 0.33 kWh (4 kW avg × 5 min)
- PV generated: 0.50 kWh (6 kW avg × 5 min)
- Check: 0.50 >= 0.33 * 0.95? YES
- Result: SOLAR ✅ (correct!)

No load sensor needed - PV delta tells the whole story!
```

## Migration Path

### For Users with Power Sensors Only
If you only have:
- `pv_power_entity` (W)
- `batt_power_entity` (W)
- `load_power_entity` (W)

**You need to add:**
- `pv_energy_today_entity` (kWh) - Check your PV inverter
- Keep existing sensors for other features

### For Huawei LUNA2000 Users
You already have all needed sensors:
- ✅ `Energy charged today EMMA` → `batt_energy_charged_today_entity`
- ✅ `Energy discharged today EMMA` → `batt_energy_discharged_today_entity`  
- ✅ `PV yield today EMMA` → `pv_energy_today_entity`
- ✅ `Supply from grid today EMMA` → `grid_import_today_entity` (optional)

**No additional configuration needed!**

## Logging

Enhanced logging shows energy deltas instead of power:

```
Battery charged: 0.500 kWh from solar @ 0.000 SEK/kWh (PV delta: 0.600 kWh, Grid import: 0.000 kWh)
Battery charged: 0.500 kWh from grid @ 2.500 SEK/kWh (PV delta: 0.200 kWh, Grid import: 0.400 kWh)
```

## Summary

The energy-delta approach:
- ✅ **More accurate**: Direct energy comparison, no estimation
- ✅ **More reliable**: Synchronized measurements from daily counters
- ✅ **Simpler**: No complex power-based heuristics
- ✅ **No load sensor required**: PV delta tells the complete story
- ✅ **Uses enriched price**: The only direct, reliable cost value
- ✅ **Better for users**: Most systems have energy counters

This is the **safest and most accurate method** for battery cost tracking!
