# Huawei EMMA Integration Summary

## Overview

This document summarizes the investigation of Huawei Solar integration files and the available control functions for your Huawei LUNA2000 battery system with EMMA controller.

## Documentation Structure

We've created three complementary documents:

1. **`huawei_emma_capabilities.md`** - Comprehensive reference
   - All 13 available control functions
   - Detailed parameters and constraints
   - Code examples and recommendations
   - Integration patterns with Energy Dispatcher
   - ~700 lines of detailed documentation

2. **`huawei_emma_quick_reference.md`** - Quick lookup guide
   - Function tables and summaries
   - Common use case examples
   - Code snippets ready to use
   - Troubleshooting tips

3. **`huawei_solar_reference/`** - Original reference files
   - `services.py` - Service implementations from Huawei Solar integration
   - `services.yaml` - Service definitions
   - `strings.json` - UI translations

## Key Findings

### 1. EMMA Architecture

When EMMA is present (as in your setup):
- ✅ EMMA is the central energy management controller
- ✅ All battery control must go through EMMA services
- ✅ No direct battery register access
- ✅ EMMA manages coordination between solar, battery, grid, and load

### 2. Available Control Functions

**Battery Control (5 services):**
- `forcible_charge` - Time-based forced charging
- `forcible_charge_soc` - SOC-target forced charging
- `forcible_discharge` - Time-based forced discharging
- `forcible_discharge_soc` - SOC-target forced discharging
- `stop_forcible_charge` - Stop any forced operation

**Grid Export Control (4 services):**
- `reset_maximum_feed_grid_power` - Unlimited export
- `set_zero_power_grid_connection` - No export (zero export mode)
- `set_maximum_feed_grid_power` - Limit export by watts
- `set_maximum_feed_grid_power_percent` - Limit export by percentage

**TOU Configuration (1 service):**
- `set_tou_periods` - Configure up to 14 time-of-use periods

### 3. Example System Specifications

Example configuration:
```yaml
Battery Capacity: 30 kWh
Max Charge Power: 10,000 W (10 kW)
Max Discharge Power: 10,000 W (10 kW)
SOC Floor: 5% (hardware minimum: 12%)
SOC Ceiling: 100%
```

**Available sensors:**
- Battery Energy Charged Today: `sensor.luna2000_energy_charged_today`
- Battery Energy Discharged Today: `sensor.luna2000_energy_discharged_today`
- Battery Capacity: `sensor.luna2000_rated_ess_capacity`
- Battery SOC: State of capacity EMMA
- PV Power: PV output power EMMA
- Grid Import Today: Supply from grid today EMMA

## Code Enhancements

### Enhanced HuaweiBatteryAdapter

**Before:** Only supported forced charging
```python
class HuaweiBatteryAdapter(BatteryAdapter):
    async def async_force_charge(self, power_w, duration_min)
    async def async_cancel_force_charge(self)  # Was no-op
```

**After:** Full battery control capabilities
```python
class HuaweiBatteryAdapter(BatteryAdapter):
    # Time-based control
    async def async_force_charge(self, power_w, duration_min)
    async def async_force_discharge(self, power_w, duration_min)
    
    # SOC-based control
    async def async_force_charge_to_soc(self, power_w, target_soc)
    async def async_force_discharge_to_soc(self, power_w, target_soc)
    
    # Operation control
    async def async_cancel_force_charge()  # Now properly stops operations
```

### New HuaweiEMMAAdapter

**Purpose:** Control grid export behavior

```python
class HuaweiEMMAAdapter:
    # Export control
    async def async_set_zero_export()
    async def async_set_export_limit_w(power_w)
    async def async_set_export_limit_percent(percentage)
    async def async_reset_export_limit()
    
    # TOU configuration
    async def async_set_tou_periods(periods)
```

## Integration with Energy Dispatcher

### Current Usage

Energy Dispatcher currently uses `HuaweiBatteryAdapter` for:
- Forced charging during cheap electricity hours
- Integration with battery cost tracking (BEC module)
- Automatic detection of battery capacity and SOC

### Recommended Enhancements

#### 1. Price-Based Battery Control

```python
# In coordinator or planner
async def optimize_battery_for_prices(self):
    """Optimize battery based on Nordpool prices."""
    battery = HuaweiBatteryAdapter(self.hass, self.battery_device_id)
    
    # Get upcoming prices
    cheap_hours = self.get_cheap_hours(threshold=0.50)  # SEK/kWh
    expensive_hours = self.get_expensive_hours(threshold=1.50)  # SEK/kWh
    
    # Schedule charging during cheap hours
    if current_hour in cheap_hours:
        await battery.async_force_charge(power_w=8000, duration_min=60)
    
    # Schedule discharging during expensive hours
    elif current_hour in expensive_hours:
        await battery.async_force_discharge(power_w=7000, duration_min=60)
    
    # Return to automatic mode otherwise
    else:
        await battery.async_cancel_force_charge()
```

#### 2. Export Control for Negative Prices

```python
# In coordinator
async def handle_negative_prices(self):
    """Prevent export during negative price periods."""
    emma = HuaweiEMMAAdapter(self.hass, self.emma_device_id)
    
    current_price = self.get_current_price()
    
    if current_price < 0:
        # Prevent export when prices are negative
        await emma.async_set_zero_export()
    else:
        # Allow normal export when prices recover
        await emma.async_reset_export_limit()
```

#### 3. SOC-Based Pre-Charging

```python
# Before expensive period
async def prepare_for_peak_hours(self):
    """Ensure battery is charged before expensive period."""
    battery = HuaweiBatteryAdapter(self.hass, self.battery_device_id)
    
    # Check if expensive period is upcoming
    next_expensive = self.get_next_expensive_period()
    time_until = next_expensive - now()
    
    if time_until < timedelta(hours=2):
        # Charge to 90% before expensive period
        await battery.async_force_charge_to_soc(
            power_w=10000,  # Max power
            target_soc=90
        )
```

#### 4. Dynamic TOU Configuration

```python
# Weekly TOU setup based on historical price patterns
async def configure_tou_from_price_patterns(self):
    """Configure TOU periods based on typical price patterns."""
    emma = HuaweiEMMAAdapter(self.hass, self.emma_device_id)
    
    # Analyze historical Nordpool prices
    patterns = self.analyze_price_patterns()
    
    # Build TOU period string
    periods = []
    for pattern in patterns:
        start = pattern['start_time']
        end = pattern['end_time']
        days = "1234567"  # All days
        flag = "+" if pattern['mode'] == 'charge' else "-"
        periods.append(f"{start}-{end}/{days}/{flag}")
    
    periods_str = "\n".join(periods)
    await emma.async_set_tou_periods(periods_str)
```

## Practical Usage Scenarios

### Scenario 1: Daily Price Optimization

**Goal:** Minimize electricity cost using battery

**Strategy:**
1. **Night (00:00-06:00):** Charge battery during low prices
2. **Morning (06:00-09:00):** Use battery for morning consumption
3. **Day (09:00-17:00):** Let solar charge battery
4. **Evening (17:00-21:00):** Discharge battery during peak prices
5. **Late evening (21:00-24:00):** Charge if prices drop

**Implementation:**
```python
# Energy Dispatcher coordinator
async def daily_optimization_cycle(self):
    hour = datetime.now().hour
    price = self.get_current_price()
    
    battery = HuaweiBatteryAdapter(self.hass, self.battery_device_id)
    
    # Night charging (00:00-06:00)
    if 0 <= hour < 6 and price < 0.50:
        await battery.async_force_charge(power_w=8000, duration_min=60)
    
    # Evening peak discharge (17:00-21:00)
    elif 17 <= hour < 21 and price > 1.00:
        await battery.async_force_discharge(power_w=7000, duration_min=60)
    
    # Normal operation
    else:
        await battery.async_cancel_force_charge()
```

### Scenario 2: Negative Price Handling

**Goal:** Avoid exporting during negative prices

**Strategy:**
- Monitor Nordpool prices continuously
- Enable zero export mode when price goes negative
- Restore normal operation when price recovers

**Implementation:**
```python
async def handle_export_based_on_price(self):
    emma = HuaweiEMMAAdapter(self.hass, self.emma_device_id)
    price = self.get_current_price()
    
    if price < 0:
        # Negative price - prevent export
        await emma.async_set_zero_export()
        _LOGGER.info(f"Zero export enabled (price: {price} SEK/kWh)")
    
    elif price < 0.20:
        # Very low price - limit export to 50%
        await emma.async_set_export_limit_percent(50)
        _LOGGER.info(f"Export limited to 50% (price: {price} SEK/kWh)")
    
    else:
        # Normal price - unlimited export
        await emma.async_reset_export_limit()
        _LOGGER.info(f"Normal export (price: {price} SEK/kWh)")
```

### Scenario 3: Weekend vs Weekday Patterns

**Goal:** Different strategies for weekday/weekend

**TOU Configuration:**
```python
async def configure_weekly_tou(self):
    emma = HuaweiEMMAAdapter(self.hass, self.emma_device_id)
    
    # Weekday pattern (more consumption during day)
    # Weekend pattern (more evening consumption)
    periods = """
00:00-06:00/12345/+
06:00-09:00/12345/-
17:00-22:00/12345/-
22:00-24:00/12345/+
00:00-08:00/67/+
08:00-12:00/67/-
18:00-23:00/67/-
23:00-24:00/67/+
"""
    await emma.async_set_tou_periods(periods.strip())
```

## Integration Checklist

To fully utilize these capabilities in Energy Dispatcher:

### Phase 1: Basic Integration (Current)
- [x] HuaweiBatteryAdapter with forced charging
- [x] Battery cost tracking (BEC module)
- [x] Automatic sensor configuration
- [x] Device ID from config

### Phase 2: Enhanced Battery Control
- [ ] Implement forced discharge in coordinator
- [ ] Add SOC-based control logic
- [ ] Create proper stop/cancel logic
- [ ] Test with actual system

### Phase 3: EMMA Grid Control
- [ ] Add EMMA device ID to config flow
- [ ] Implement export control based on prices
- [ ] Add zero export mode for negative prices
- [ ] Test export limit functionality

### Phase 4: TOU Integration
- [ ] Create TOU period generator from price data
- [ ] Add TOU configuration to options
- [ ] Allow manual TOU period editing
- [ ] Automatic TOU updates based on price patterns

### Phase 5: Advanced Optimization
- [ ] Predictive charging based on forecast
- [ ] Multi-day optimization algorithms
- [ ] Integration with EV charging schedules
- [ ] Dashboard visualization of plans

## Testing Recommendations

### 1. Start Small
```python
# Test basic charge operation
await battery.async_force_charge(power_w=1000, duration_min=5)
await asyncio.sleep(300)  # Wait 5 minutes
await battery.async_cancel_force_charge()
```

### 2. Monitor Effects
- Watch battery SOC sensor
- Check power flow sensors
- Verify grid import/export behavior
- Monitor cost tracking

### 3. Validate Constraints
- Test power limit enforcement (max 10,000 W)
- Test SOC limits (12-100%)
- Test duration limits (1-1440 min)
- Verify proper stop behavior

### 4. Integration Testing
- Test with actual Nordpool prices
- Verify cost calculations
- Check BEC module tracking
- Validate dashboard displays

## Safety Considerations

### 1. Power Limits
- ✅ Never exceed 10 kW charge/discharge
- ✅ Validate power values before sending commands
- ✅ Handle errors gracefully

### 2. SOC Protection
- ✅ Respect 12% minimum SOC (hardware limit)
- ✅ Don't discharge below configured floor
- ✅ Monitor SOC during operations

### 3. Duration Management
- ✅ Set reasonable durations
- ✅ Always have stop/cancel capability
- ✅ Monitor for stuck operations

### 4. Error Handling
- ✅ Catch service call exceptions
- ✅ Log all control actions
- ✅ Provide user notifications
- ✅ Fall back to safe defaults

## Next Steps

### Immediate Actions

1. **Find EMMA Device ID**
   ```
   Settings → Devices & Services → Huawei Solar → EMMA device
   ```

2. **Test Basic Functions**
   - Test force charge (low power, short duration)
   - Test stop operation
   - Verify battery responds correctly

3. **Review Current Integration**
   - Check how coordinator uses battery adapter
   - Identify where discharge could be added
   - Plan export control integration

### Short-term Goals

1. **Enhance Adapter Usage**
   - Add discharge to optimization logic
   - Implement proper cancel/stop
   - Add SOC-based methods

2. **Add Export Control**
   - Integrate EMMA adapter
   - Add negative price handling
   - Configure export limits

3. **Improve Documentation**
   - Add user guide for setup
   - Document configuration options
   - Create troubleshooting guide

### Long-term Vision

1. **Full Automation**
   - Automatic TOU configuration
   - Self-learning price patterns
   - Predictive optimization

2. **Advanced Features**
   - Multi-day planning
   - Weather integration
   - Demand response

3. **User Experience**
   - Visual plan editor
   - Real-time optimization display
   - Cost savings reports

## Conclusion

Your Huawei LUNA2000 system with EMMA controller provides powerful capabilities for energy optimization:

✅ **13 control functions** available through huawei_solar integration
✅ **Time-based and SOC-based** battery control
✅ **Grid export management** for price optimization
✅ **TOU configuration** for automated daily patterns
✅ **Full integration** with Energy Dispatcher possible

The enhanced adapters (`HuaweiBatteryAdapter` and `HuaweiEMMAAdapter`) provide a clean interface to these capabilities, ready for integration into your Energy Dispatcher coordinator and planner.

**Key Benefits:**
- Minimize electricity costs using battery strategically
- Avoid costs during negative price periods
- Automate battery charging during cheap hours
- Discharge during expensive peak hours
- Full visibility through battery cost tracking

All the tools are now in place to build a sophisticated price-responsive energy management system! 🔋⚡

## References

- **Full Capabilities:** `docs/huawei_emma_capabilities.md`
- **Quick Reference:** `docs/huawei_emma_quick_reference.md`
- **Reference Code:** `docs/huawei_solar_reference/services.py`
- **Battery Adapter:** `custom_components/energy_dispatcher/adapters/huawei.py`
- **Cost Tracking:** `docs/battery_cost_tracking.md`
