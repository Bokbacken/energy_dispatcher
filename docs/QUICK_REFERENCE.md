# Multi-Vehicle Quick Reference

A concise reference for the multi-vehicle and cost strategy features.

## Vehicle Presets

### Tesla Model Y Long Range 2022
```python
VehicleConfig.tesla_model_y_lr_2022()
# Battery: 75 kWh
# Phases: 3-phase, 16A max
# Efficiency: 92%
# Charge time 40%→80%: ~3 hours
```

### Hyundai Ioniq Electric 2019
```python
VehicleConfig.hyundai_ioniq_electric_2019()
# Battery: 28 kWh  
# Phases: 1-phase, 16A max
# Efficiency: 88%
# Charge time 30%→100%: ~6 hours
```

## Charger Presets

### 3-Phase Charger
```python
ChargerConfig.generic_3phase_16a()
# 6-16A, 3-phase, 230V
# Max power: ~11 kW
```

### 1-Phase Charger
```python
ChargerConfig.generic_1phase_16a()
# 6-16A, 1-phase, 230V
# Max power: ~3.7 kW
```

## Charging Modes

| Mode | When to Use | Behavior |
|------|-------------|----------|
| `ASAP` | Emergency, urgent | Charge immediately |
| `Eco` | Flexible timing | Wait for solar/cheap |
| `Deadline` | Specific time | Meet deadline |
| `Cost Saver` | Cost priority | Cheapest hours only |

## Cost Classification

| Level | Threshold | Color | Action |
|-------|-----------|-------|--------|
| Cheap | ≤ 1.5 SEK/kWh | 🟢 Green | Charge battery & EV |
| Medium | 1.5-3.0 SEK/kWh | 🟡 Yellow | Hold or optimize |
| High | ≥ 3.0 SEK/kWh | 🔴 Red | Discharge battery |

## Common Operations

### Add Vehicle
```python
manager = VehicleManager(hass)
tesla = VehicleConfig.tesla_model_y_lr_2022()
manager.add_vehicle(tesla)
```

### Update SOC
```python
manager.update_vehicle_state(
    "tesla_model_y_lr",
    current_soc=45.0,
    target_soc=80.0
)
```

### Start Charging
```python
session = manager.start_charging_session(
    "tesla_model_y_lr",
    "home_charger",
    mode=ChargingMode.DEADLINE,
    deadline=datetime(2024, 1, 15, 8, 0)
)
```

### Get Required Energy
```python
kwh = manager.calculate_required_energy("tesla_model_y_lr")
# Returns: 26.25 kWh for 40%→80% on 75 kWh battery
```

### Get Charging Time
```python
hours = manager.calculate_charging_time("tesla_model_y_lr", 16)
# Returns: ~2.6 hours at 16A
```

### End Charging
```python
session = manager.end_charging_session(
    "tesla_model_y_lr",
    energy_delivered=26.5
)
```

## Cost Strategy

### Create Strategy
```python
from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.models import CostThresholds

thresholds = CostThresholds(cheap_max=1.5, high_min=3.0)
strategy = CostStrategy(thresholds)
```

### Classify Price
```python
level = strategy.classify_price(2.5)
# Returns: CostLevel.MEDIUM
```

### Calculate Reserve
```python
reserve = strategy.calculate_battery_reserve(
    prices, 
    now, 
    battery_capacity_kwh=15.0,
    current_soc=50.0
)
# Returns: 40.0 (40% reserve recommended)
```

### Should Charge Battery?
```python
should_charge = strategy.should_charge_battery(
    current_price=1.2,
    current_soc=60.0,
    reserve_soc=40.0,
    solar_available_w=500.0
)
# Returns: True (cheap price OR solar available)
```

### Should Discharge Battery?
```python
should_discharge = strategy.should_discharge_battery(
    current_price=3.5,
    current_soc=65.0,
    reserve_soc=40.0
)
# Returns: True (high price AND above reserve)
```

### Optimize EV Charging
```python
hours = strategy.optimize_ev_charging_windows(
    prices,
    now,
    required_energy_kwh=30.0,
    deadline=datetime(2024, 1, 15, 8, 0),
    charging_power_kw=11.0
)
# Returns: [00:00, 01:00, 02:00] (3 cheapest hours)
```

### Get Cost Summary
```python
summary = strategy.get_cost_summary(prices, now, 24)
# Returns:
# {
#   'total_hours': 24,
#   'cheap_hours': 11,
#   'medium_hours': 7,
#   'high_hours': 6,
#   'avg_price': 2.05,
#   'min_price': 0.80,
#   'max_price': 4.00
# }
```

## Typical Scenarios

### Morning Commute
```python
# Tesla ready by 08:00
manager.update_vehicle_state(
    "tesla_model_y_lr",
    current_soc=40.0,
    target_soc=80.0,
    charging_mode=ChargingMode.DEADLINE,
    deadline=datetime.now() + timedelta(hours=10)
)
session = manager.start_charging_session("tesla_model_y_lr", "home_charger")
# → Charges during cheapest hours before deadline
```

### Solar Charging
```python
# Ioniq during daytime
manager.update_vehicle_state(
    "hyundai_ioniq_electric",
    current_soc=60.0,
    target_soc=100.0,
    charging_mode=ChargingMode.ECO
)
session = manager.start_charging_session("hyundai_ioniq_electric", "home_charger")
# → Prioritizes solar hours, uses cheap grid as backup
```

### Emergency Charge
```python
# Tesla needs charge ASAP
manager.update_vehicle_state(
    "tesla_model_y_lr",
    current_soc=15.0,
    target_soc=50.0,
    charging_mode=ChargingMode.ASAP
)
session = manager.start_charging_session("tesla_model_y_lr", "home_charger")
# → Starts charging immediately at max power
```

### Cost Minimization
```python
# Ioniq overnight, cost is priority
manager.update_vehicle_state(
    "hyundai_ioniq_electric",
    current_soc=40.0,
    target_soc=100.0,
    charging_mode=ChargingMode.COST_SAVER
)
session = manager.start_charging_session("hyundai_ioniq_electric", "home_charger")
# → Only charges during absolute cheapest hours
```

## Calculations

### Power (3-Phase)
```
P (kW) = V × I × phases × efficiency / 1000
Example: 230V × 16A × 3 × 0.92 / 1000 = 10.2 kW
```

### Power (1-Phase)
```
P (kW) = V × I × 1 × efficiency / 1000
Example: 230V × 16A × 1 × 0.88 / 1000 = 3.2 kW
```

### Energy Required
```
E (kWh) = battery_kwh × (target_soc - current_soc) / 100
Example: 75 kWh × (80% - 40%) / 100 = 30 kWh
```

### Charging Time
```
T (hours) = required_kwh / power_kw
Example: 30 kWh / 10.2 kW = 2.94 hours ≈ 3 hours
```

### Battery Reserve
```
Reserve (%) = (high_cost_hours × avg_load_kw / battery_kwh) × 100
Example: (3h × 2kW / 15kWh) × 100 = 40%
```

## Automation Examples

### Update SOC on Connect
```yaml
automation:
  - alias: "Update Tesla SOC"
    trigger:
      platform: state
      entity_id: sensor.wallbox_connected
      to: "connected"
    action:
      service: energy_dispatcher.set_vehicle_soc
      data:
        vehicle_id: "tesla_model_y_lr"
        soc: "{{ states('input_number.tesla_manual_soc') }}"
```

### Set Morning Deadline
```yaml
automation:
  - alias: "Tesla Morning Deadline"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      service: energy_dispatcher.set_charging_mode
      data:
        vehicle_id: "tesla_model_y_lr"
        mode: "deadline"
        deadline: "{{ (now() + timedelta(hours=10)).isoformat() }}"
```

### Notify on Completion
```yaml
automation:
  - alias: "Charging Complete"
    trigger:
      platform: event
      event_type: energy_dispatcher.charging_complete
    action:
      service: notify.mobile_app
      data:
        message: "{{ trigger.event.data.vehicle_name }} charged to {{ trigger.event.data.end_soc }}%"
```

## Tips

1. **Update SOC regularly** for vehicles without API
2. **Set realistic deadlines** with buffer time
3. **Use Eco mode** when time flexible
4. **Trust battery reserve** for peak hours
5. **Monitor cost classification** to verify thresholds
6. **Review completed sessions** to optimize strategy

## See Also

- [Multi-Vehicle Setup Guide](./multi_vehicle_setup.md) - Full documentation
- [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) - Technical details
- [Example Config](../examples/multi_vehicle_config.yaml) - YAML examples
- [Demo Script](../examples/vehicle_manager_demo.py) - Working code
