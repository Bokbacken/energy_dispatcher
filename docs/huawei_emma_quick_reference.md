# Huawei EMMA Quick Reference

Quick reference for Huawei EMMA battery system control functions available in Energy Dispatcher.

## Your System Configuration

- **Battery:** Huawei LUNA2000, 30 kWh capacity
- **Max Charge:** 10 kW (10,000 W)
- **Max Discharge:** 10 kW (10,000 W)
- **Battery Device ID:** `5e572c76e307b4cc612e683a04bdb60a`
- **Controller:** EMMA (Energy Management and Monitoring Architecture)

## Quick Function Reference

### Battery Control

| Function | Service | Key Parameters | Duration/SOC |
|----------|---------|----------------|--------------|
| **Force Charge** | `forcible_charge` | power (W), duration (min) | Time-based, max 1440 min |
| **Force Charge to SOC** | `forcible_charge_soc` | power (W), target_soc (%) | SOC-based, 12-100% |
| **Force Discharge** | `forcible_discharge` | power (W), duration (min) | Time-based, max 1440 min |
| **Force Discharge to SOC** | `forcible_discharge_soc` | power (W), target_soc (%) | SOC-based, 12-100% |
| **Stop Force Operation** | `stop_forcible_charge` | device_id only | Immediate |

### Grid Export Control (EMMA)

| Function | Service | Effect |
|----------|---------|--------|
| **Zero Export** | `set_zero_power_grid_connection` | No grid export, excess curtailed/stored |
| **Limit Export (W)** | `set_maximum_feed_grid_power` | Limit export to specific wattage |
| **Limit Export (%)** | `set_maximum_feed_grid_power_percent` | Limit export to % of inverter capacity |
| **Unlimited Export** | `reset_maximum_feed_grid_power` | Remove all export restrictions |

### Time-of-Use Periods

| Function | Service | Parameters |
|----------|---------|------------|
| **Set TOU Periods** | `set_tou_periods` | Multi-line period definitions (max 14) |

## Code Examples

### Python (Adapter Methods)

```python
# Using HuaweiBatteryAdapter
battery = HuaweiBatteryAdapter(hass, "5e572c76e307b4cc612e683a04bdb60a")

# Charge at 8 kW for 2 hours
await battery.async_force_charge(power_w=8000, duration_min=120)

# Charge to 90% SOC at max power
await battery.async_force_charge_to_soc(power_w=10000, target_soc=90)

# Discharge at 5 kW for 1 hour
await battery.async_force_discharge(power_w=5000, duration_min=60)

# Stop any operation
await battery.async_cancel_force_charge()

# Using HuaweiEMMAAdapter (need EMMA device ID)
emma = HuaweiEMMAAdapter(hass, "your_emma_device_id")

# Prevent all export
await emma.async_set_zero_export()

# Limit export to 5 kW
await emma.async_set_export_limit_w(5000)

# Allow unlimited export
await emma.async_reset_export_limit()
```

### YAML (Service Calls)

```yaml
# Force charge
service: huawei_solar.forcible_charge
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
  power: 8000
  duration: 120

# Force discharge to SOC
service: huawei_solar.forcible_discharge_soc
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"
  power: 5000
  target_soc: 20

# Stop operation
service: huawei_solar.stop_forcible_charge
data:
  device_id: "5e572c76e307b4cc612e683a04bdb60a"

# Zero export mode
service: huawei_solar.set_zero_power_grid_connection
data:
  device_id: "your_emma_device_id"
```

## Common Use Cases for Energy Dispatcher

### 1. Charge Before Peak Hours (Night/Early Morning)
```python
# At 02:00 - cheap electricity
await battery.async_force_charge(power_w=8000, duration_min=180)  # Until 05:00
```

### 2. Discharge During Peak Hours (Evening)
```python
# At 17:00 - expensive electricity
await battery.async_force_discharge(power_w=7000, duration_min=240)  # Until 21:00
```

### 3. Prevent Export During Negative Prices
```python
# When price < 0
await emma.async_set_zero_export()

# When price returns to positive
await emma.async_reset_export_limit()
```

### 4. Ensure Battery Readiness
```python
# Before expensive period, ensure 90% SOC
await battery.async_force_charge_to_soc(power_w=10000, target_soc=90)
```

### 5. Return to Normal Operation
```python
# After planned operation
await battery.async_cancel_force_charge()
```

## TOU Period Format

```
HH:MM-HH:MM/DAYS/FLAG
```

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

Where:
- **Time:** 24-hour format (00:00-23:59)
- **Days:** 1=Mon, 2=Tue, ..., 7=Sun (combine for multiple days)
- **Flag:** `+` = charge period, `-` = discharge period

## Important Constraints

| Parameter | Minimum | Maximum | Notes |
|-----------|---------|---------|-------|
| **Power** | 0 W | 10,000 W | Your system max |
| **Duration** | 1 min | 1,440 min | 24 hours max |
| **SOC Target** | 12% | 100% | Hardware limit 12% |
| **TOU Periods** | 0 | 14 | Maximum periods |
| **Export Power** | -1,000 W | Unlimited | Negative = import limit |
| **Export Percent** | 0% | 100% | Of inverter capacity |

## Integration Workflow

```
Energy Dispatcher Planner
         ↓
    Price Analysis
         ↓
    Plan Generation
         ↓
  ┌──────┴──────┐
  ↓             ↓
Battery      EMMA
Adapter      Adapter
  ↓             ↓
Charge/      Export
Discharge    Control
  ↓             ↓
Huawei Solar Integration
         ↓
    EMMA Controller
         ↓
   Battery System
```

## Next Steps

1. **Find EMMA Device ID**
   - Settings → Devices & Services → Huawei Solar
   - Look for EMMA device, note its device ID

2. **Test Basic Operations**
   - Try force charge for short duration
   - Verify stop operation works
   - Test zero export mode

3. **Integrate with Planner**
   - Use adapters in coordinator
   - Schedule based on Nordpool prices
   - Monitor battery cost tracking

4. **Advanced Features**
   - Configure TOU periods based on price patterns
   - Implement dynamic export control
   - Optimize SOC targets

## Resources

- **Full Documentation:** `docs/huawei_emma_capabilities.md`
- **Reference Files:** `docs/huawei_solar_reference/`
- **Current Adapter:** `custom_components/energy_dispatcher/adapters/huawei.py`
- **Battery Cost Tracking:** `docs/battery_cost_tracking.md`

## Troubleshooting

**Problem:** Commands not working
- ✅ Verify device ID is correct
- ✅ Check huawei_solar integration is working
- ✅ Ensure elevated permissions enabled (installer mode)

**Problem:** Power limit exceeded
- ✅ Check max charge/discharge power (10,000 W)
- ✅ Reduce power_w parameter

**Problem:** SOC target rejected
- ✅ Ensure SOC between 12-100%
- ✅ Note: 12% is hardware minimum

**Problem:** Duration too long
- ✅ Maximum duration is 1,440 minutes (24 hours)
- ✅ For longer control, use TOU periods

---

*For detailed information, see `docs/huawei_emma_capabilities.md`*
