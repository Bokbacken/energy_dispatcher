# Multi-Vehicle and Multi-Charger Setup Guide

This guide explains how to set up and use multiple electric vehicles and chargers with Energy Dispatcher.

## Features

- **Multiple Vehicles**: Manage charging for multiple EVs with different specifications
- **Multiple Chargers**: Support for different charger types and capabilities
- **Vehicle Presets**: Quick setup for popular EV models
- **Charging Modes**: ASAP, Eco, Deadline, Cost Saver
- **Deadline Support**: Schedule charging to complete by a specific time
- **Cost Optimization**: Intelligent cost-based charging strategy
- **Battery Reserve**: Preserve home battery for high-cost periods

## Vehicle Presets

### Tesla Model Y Long Range 2022

Pre-configured settings:
- **Battery Capacity**: 75 kWh
- **Max Charge Current**: 16A
- **Phases**: 3-phase
- **Voltage**: 230V
- **Default Target SOC**: 80%
- **Charging Efficiency**: 92%
- **API Integration**: Manual (no API)

Typical charging time from 20% to 80% at 16A:
- Power: 230V × 16A × 3 phases × 0.92 = 10.2 kW
- Energy needed: 75 kWh × 60% = 45 kWh
- Time: 45 kWh / 10.2 kW ≈ 4.4 hours

### Hyundai Ioniq Electric 2019

Pre-configured settings:
- **Battery Capacity**: 28 kWh
- **Max Charge Current**: 16A
- **Phases**: 1-phase
- **Voltage**: 230V
- **Default Target SOC**: 100%
- **Charging Efficiency**: 88%
- **API Integration**: Manual (no API)

Typical charging time from 20% to 100% at 16A:
- Power: 230V × 16A × 1 phase × 0.88 = 3.2 kW
- Energy needed: 28 kWh × 80% = 22.4 kWh
- Time: 22.4 kWh / 3.2 kW ≈ 7 hours

## Charger Presets

### Generic 3-Phase 16A Charger

Suitable for:
- Tesla Model Y, Model 3, Model S, Model X
- Most European EVs with 3-phase support
- Maximum power: ~11 kW

Settings:
- **Min Current**: 6A
- **Max Current**: 16A
- **Phases**: 3
- **Voltage**: 230V

### Generic 1-Phase 16A Charger

Suitable for:
- Hyundai Ioniq Electric
- Nissan Leaf
- Older EVs or single-phase installations
- Maximum power: ~3.7 kW

Settings:
- **Min Current**: 6A
- **Max Current**: 16A
- **Phases**: 1
- **Voltage**: 230V

## Charging Modes

### ASAP (As Soon As Possible)

Charge immediately regardless of cost.

**Use when**:
- You need the car urgently
- Emergency charging
- SOC is critically low

**Example**:
```yaml
mode: ASAP
current_soc: 15%
target_soc: 80%
# Will start charging immediately at maximum available power
```

### Eco (Optimize for Solar/Cheap Energy)

Charge using solar power and cheapest grid hours.

**Use when**:
- You have time to charge
- Solar forecast is good
- No urgent deadline

**Example**:
```yaml
mode: Eco
current_soc: 40%
target_soc: 80%
# Will wait for solar production or cheap grid hours
```

### Deadline

Ensure charging completes by a specific time.

**Use when**:
- You need the car ready by a certain time
- Morning commute preparation
- Planned trip

**Example**:
```yaml
mode: Deadline
current_soc: 30%
target_soc: 80%
deadline: "2024-01-15 08:00:00"
# Will optimize charging within deadline window
```

### Cost Saver

Minimize charging cost even if slower.

**Use when**:
- Cost is the priority
- You have ample time
- Price spread is significant

**Example**:
```yaml
mode: Cost Saver
current_soc: 50%
target_soc: 90%
# Will only charge during cheapest hours
```

## Cost Strategy

### Energy Cost Classification

Prices are classified into three levels:

- **Cheap**: ≤ 1.5 SEK/kWh (configurable)
- **Medium**: 1.5 - 3.0 SEK/kWh
- **High**: ≥ 3.0 SEK/kWh (configurable)

### Battery Reserve Strategy

The system calculates a battery reserve level based on:

1. **Predicted High-Cost Windows**: Identifies upcoming expensive hours
2. **Duration of High-Cost Periods**: Longer periods need more reserve
3. **Price Differential**: Higher prices justify more reserve
4. **Current Battery State**: Adjusts based on available capacity

**Example**:
```
Current time: 22:00
High-cost window: 06:00-09:00 (3 hours)
Average high-cost price: 3.5 SEK/kWh
Estimated load: 2 kW

Reserve calculation:
- Energy needed: 3 hours × 2 kW = 6 kWh
- Battery capacity: 15 kWh
- Reserve SOC: (6 / 15) × 100 = 40%

System will maintain at least 40% SOC for the morning peak.
```

### Smart Charging Decisions

**Battery Charging**:
- ✅ Charge during cheap hours below 95% SOC
- ✅ Always charge from excess solar (free energy)
- ✅ Charge if below reserve level and not expensive
- ❌ Don't charge during high-cost hours above reserve

**Battery Discharging**:
- ✅ Discharge during high-cost hours if above reserve + buffer
- ✅ Discharge to cover solar deficit if spare capacity
- ❌ Never discharge below reserve level

**EV Charging**:
- Optimizes for cheapest hours within deadline
- Considers solar availability
- Meets deadline requirements
- Alerts if deadline cannot be met

## Configuration Examples

### Example 1: Two Vehicles, One 3-Phase Charger

**Scenario**: Tesla Model Y and Hyundai Ioniq sharing one charger

```python
# Add vehicles
tesla = VehicleConfig.tesla_model_y_lr_2022()
tesla.name = "Family Tesla"
vehicle_manager.add_vehicle(tesla)

ioniq = VehicleConfig.hyundai_ioniq_electric_2019()
ioniq.name = "Commuter Ioniq"
vehicle_manager.add_vehicle(ioniq)

# Add charger
charger = ChargerConfig.generic_3phase_16a()
charger.name = "Home Charger"
charger.start_switch = "switch.wallbox_start"
charger.stop_switch = "switch.wallbox_stop"
charger.current_number = "number.wallbox_current"
charger.power_sensor = "sensor.wallbox_power"
vehicle_manager.add_charger(charger)

# Associate vehicles (one at a time)
vehicle_manager.associate_vehicle_charger(tesla.id, charger.id)
```

**Usage**:
- Charge Tesla overnight for morning commute (Deadline mode, 08:00)
- Charge Ioniq during day with solar (Eco mode)
- Manually switch which car is connected

### Example 2: One Vehicle, Manual SOC Updates

**Scenario**: Tesla Model Y without API integration

```python
# Setup vehicle
tesla = VehicleConfig.tesla_model_y_lr_2022()
vehicle_manager.add_vehicle(tesla)

# Update SOC manually when connecting
vehicle_manager.update_vehicle_state(
    tesla.id,
    current_soc=45.0,  # Read from car display
    target_soc=80.0,
    charging_mode=ChargingMode.DEADLINE,
    deadline=datetime.now() + timedelta(hours=10)
)

# System will optimize charging
session = vehicle_manager.start_charging_session(
    tesla.id,
    charger_id="home_charger"
)
```

### Example 3: Cost Thresholds Customization

**Scenario**: Adjust cost classification for your area

```python
from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.models import CostThresholds

# Custom thresholds for your electricity market
thresholds = CostThresholds(
    cheap_max=1.2,  # Lower threshold for cheap
    high_min=2.5    # Lower threshold for high
)

strategy = CostStrategy(thresholds)

# Or use dynamic thresholds based on actual prices
dynamic = strategy.get_dynamic_thresholds(price_history)
strategy.thresholds = dynamic
```

## Session Tracking

### Starting a Session

```python
session = vehicle_manager.start_charging_session(
    vehicle_id="tesla_model_y_lr",
    charger_id="home_charger",
    deadline=datetime(2024, 1, 15, 8, 0),
    mode=ChargingMode.DEADLINE
)

print(f"Session started: {session.start_soc}% -> {session.target_soc}%")
print(f"Deadline: {session.deadline}")
```

### Monitoring a Session

```python
active_session = vehicle_manager.get_active_session("tesla_model_y_lr")

if active_session:
    print(f"Charging: {active_session.start_soc}% -> current")
    print(f"Mode: {active_session.mode.value}")
    if active_session.deadline:
        remaining = active_session.deadline - datetime.now()
        print(f"Time remaining: {remaining}")
```

### Ending a Session

```python
# Update final SOC
vehicle_manager.update_vehicle_state("tesla_model_y_lr", current_soc=80.0)

# End session with energy delivered
session = vehicle_manager.end_charging_session(
    "tesla_model_y_lr",
    energy_delivered=30.5  # kWh
)

print(f"Charged {session.energy_delivered} kWh")
print(f"Final SOC: {session.end_soc}%")
```

## Integration with Home Assistant

### Entities Created

For each vehicle:
- `number.ev_{vehicle_id}_current_soc`: Current state of charge
- `number.ev_{vehicle_id}_target_soc`: Target state of charge
- `select.ev_{vehicle_id}_charging_mode`: Charging mode selector
- `sensor.ev_{vehicle_id}_charging_status`: Current status
- `sensor.ev_{vehicle_id}_energy_needed`: Energy to target

For cost strategy:
- `sensor.energy_cost_level`: Current cost classification
- `sensor.battery_reserve_soc`: Recommended reserve level
- `sensor.next_cheap_hour`: Next cheap charging window
- `sensor.high_cost_windows`: Predicted expensive periods

### Services

#### Set Vehicle SOC
```yaml
service: energy_dispatcher.set_vehicle_soc
data:
  vehicle_id: tesla_model_y_lr
  soc: 65.0
```

#### Set Charging Mode
```yaml
service: energy_dispatcher.set_charging_mode
data:
  vehicle_id: tesla_model_y_lr
  mode: deadline
  deadline: "2024-01-15 08:00:00"
```

#### Start Charging Session
```yaml
service: energy_dispatcher.start_charging
data:
  vehicle_id: tesla_model_y_lr
  charger_id: home_charger
  mode: eco
```

#### Update Cost Thresholds
```yaml
service: energy_dispatcher.update_cost_thresholds
data:
  cheap_max: 1.5
  high_min: 3.0
```

## Troubleshooting

### Deadline Cannot Be Met

**Symptom**: Warning that charging won't complete by deadline

**Causes**:
- Insufficient time for energy needed
- Limited charging power
- SOC too low

**Solutions**:
1. Switch to ASAP mode to start immediately
2. Increase target charging current
3. Adjust deadline or reduce target SOC
4. Check charger and vehicle are properly connected

### Battery Depletes Before High-Cost Window

**Symptom**: Battery empty during expensive hours

**Causes**:
- Reserve calculation incorrect
- Unexpected high load
- Reserve too low

**Solutions**:
1. Manually increase reserve SOC
2. Check cost thresholds are appropriate
3. Verify price forecast data
4. Adjust load estimation in strategy

### Vehicle Not Charging During Cheap Hours

**Symptom**: EV not charging when expected

**Causes**:
- SOC already at target
- Charger not available
- Mode set to manual/paused
- Entity communication issues

**Solutions**:
1. Check current SOC vs target SOC
2. Verify charger entities are available
3. Check charging mode setting
4. Review automation logs

## Best Practices

1. **Update SOC Regularly**: For vehicles without API, update SOC when connecting
2. **Set Realistic Deadlines**: Allow buffer time for charging
3. **Monitor Costs**: Review cost classification periodically
4. **Adjust Thresholds**: Customize for your electricity rates
5. **Use Eco Mode**: When time permits, for cost savings
6. **Reserve Strategy**: Trust the battery reserve logic for peak hours
7. **Session Logging**: Review completed sessions to optimize strategy

## Future Enhancements

Planned features:
- API integration for Tesla, Volkswagen ID, Hyundai/Kia
- Automatic SOC detection via integrations
- Machine learning for load prediction
- Multi-charger scheduling optimization
- Vehicle-to-grid (V2G) support
- Smart grid integration
- Mobile app notifications

## See Also

- [Configuration Guide](./configuration.md)
- [Battery Cost Tracking](./battery_cost_tracking.md)
- [Energy Dispatcher README](../README.md)
