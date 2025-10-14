# AI-Like Optimization Implementation Guide

**Date**: 2025-10-14  
**Status**: Implementation Guide  
**Target Audience**: Developers implementing advanced optimization features

---

## Overview

This guide provides practical implementation details for the advanced AI-like optimization strategies outlined in `cost_strategy_and_battery_optimization.md`. It includes code structures, sensor definitions, service APIs, and integration patterns.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [New Sensors to Implement](#new-sensors-to-implement)
3. [Services API Design](#services-api-design)
4. [Configuration Schema](#configuration-schema)
5. [Translation Keys](#translation-keys)
6. [Testing Strategy](#testing-strategy)
7. [Performance Considerations](#performance-considerations)

---

## Architecture Overview

### Module Structure

```
custom_components/energy_dispatcher/
├── cost_strategy.py              # Existing - base cost optimization
├── appliance_optimizer.py        # NEW - appliance scheduling logic
├── weather_optimizer.py          # NEW - weather-aware solar optimization
├── export_analyzer.py            # NEW - export profitability analysis
├── load_shift_optimizer.py       # NEW - load shifting recommendations
├── peak_shaving.py               # NEW - peak shaving logic
├── comfort_manager.py            # NEW - comfort-aware optimization
├── optimization_coordinator.py   # NEW - orchestrates all optimizers
└── sensor_optimization.py        # NEW - optimization sensors
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Coordinator (coordinator.py)                 │
│                                                                  │
│  Fetches: prices, weather, solar forecast, consumption data     │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│            Optimization Coordinator (NEW)                        │
│                                                                  │
│  - Receives all input data                                      │
│  - Calls specialized optimizers                                 │
│  - Aggregates recommendations                                   │
│  - Resolves conflicts between optimizers                        │
│  - Returns unified optimization plan                            │
└───────────────────────┬──────────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┬────────────┐
         │              │               │            │
         ▼              ▼               ▼            ▼
┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Appliance   │  │ Weather  │  │ Export   │  │ Load     │
│ Optimizer   │  │ Optimizer│  │ Analyzer │  │ Shift    │
└─────────────┘  └──────────┘  └──────────┘  └──────────┘
         │              │               │            │
         └──────────────┴───────────────┴────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Sensors (sensor_optimization.py)              │
│                                                                  │
│  Expose: recommendations, savings, timing, reasons              │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Sensors to Implement

### 1. Appliance Recommendation Sensors

#### Dishwasher Optimal Time Sensor
```python
class DishwasherOptimalTimeSensor(BaseEDSensor):
    """Sensor showing optimal time to run dishwasher."""
    
    _attr_name = "Dishwasher Optimal Start Time"
    _attr_icon = "mdi:dishwasher"
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_dishwasher_optimal_time_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[str]:
        """Return optimal start time as ISO datetime string."""
        recommendation = self.coordinator.data.get("appliance_recommendations", {}).get("dishwasher")
        if not recommendation:
            return None
        return recommendation.get("optimal_start_time").isoformat()
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recommendation details."""
        recommendation = self.coordinator.data.get("appliance_recommendations", {}).get("dishwasher")
        if not recommendation:
            return {}
        
        return {
            "estimated_cost_sek": round(recommendation.get("estimated_cost_sek", 0), 2),
            "cost_savings_vs_now_sek": round(recommendation.get("cost_savings_vs_now_sek", 0), 2),
            "reason": recommendation.get("reason", ""),
            "price_at_optimal_time": recommendation.get("price_at_optimal_time", 0),
            "current_price": recommendation.get("current_price", 0),
            "solar_available": recommendation.get("solar_available", False),
            "alternative_times": recommendation.get("alternative_times", []),
            "confidence": recommendation.get("confidence", "medium"),
        }
    
    @property
    def device_class(self) -> str:
        return "timestamp"
```

#### Washing Machine Optimal Time Sensor
```python
class WashingMachineOptimalTimeSensor(BaseEDSensor):
    """Sensor showing optimal time to run washing machine."""
    
    _attr_name = "Washing Machine Optimal Start Time"
    _attr_icon = "mdi:washing-machine"
    
    # Similar implementation to dishwasher sensor
    # ... (same structure as above)
```

#### Water Heater Optimal Time Sensor
```python
class WaterHeaterOptimalTimeSensor(BaseEDSensor):
    """Sensor showing optimal time to heat water."""
    
    _attr_name = "Water Heater Optimal Time"
    _attr_icon = "mdi:water-boiler"
    
    # Similar implementation
    # ... (same structure as above)
```

### 2. EV Charging Recommendation Sensor (Enhanced)

```python
class EVChargingRecommendationSensor(BaseEDSensor):
    """Enhanced EV charging recommendation sensor."""
    
    _attr_name = "EV Charging Recommendation"
    _attr_icon = "mdi:car-electric"
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_ev_charging_recommendation_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[str]:
        """Return recommended charging window start time."""
        recommendation = self.coordinator.data.get("ev_charging_recommendation")
        if not recommendation:
            return "No charging needed"
        
        optimal_windows = recommendation.get("optimal_windows", [])
        if not optimal_windows:
            return "No optimal window found"
        
        # Return first (best) window
        return optimal_windows[0].get("start_time").strftime("%Y-%m-%d %H:%M")
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed charging recommendation."""
        recommendation = self.coordinator.data.get("ev_charging_recommendation", {})
        
        return {
            "energy_needed_kwh": recommendation.get("energy_needed_kwh", 0),
            "hours_needed": recommendation.get("hours_needed", 0),
            "optimal_windows": recommendation.get("optimal_windows", []),
            "estimated_cost_sek": recommendation.get("estimated_cost_sek", 0),
            "cost_if_charge_now_sek": recommendation.get("cost_if_charge_now_sek", 0),
            "savings_sek": recommendation.get("savings_sek", 0),
            "deadline": recommendation.get("deadline"),
            "current_soc": recommendation.get("current_soc", 0),
            "target_soc": recommendation.get("target_soc", 80),
            "reason": recommendation.get("reason", ""),
            "solar_opportunity": recommendation.get("solar_opportunity", False),
        }
```

### 3. Export Opportunity Sensors

#### Export Opportunity Binary Sensor
```python
class ExportOpportunityBinarySensor(BinarySensorEntity, BaseEDSensor):
    """Binary sensor indicating export opportunity."""
    
    _attr_name = "Export Opportunity"
    _attr_icon = "mdi:transmission-tower-export"
    _attr_device_class = BinarySensorDeviceClass.POWER
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_export_opportunity_{self._entry_id}"
    
    @property
    def is_on(self) -> bool:
        """Return True if export is recommended."""
        export_data = self.coordinator.data.get("export_opportunity", {})
        return export_data.get("should_export", False)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return export opportunity details."""
        export_data = self.coordinator.data.get("export_opportunity", {})
        
        return {
            "export_power_w": export_data.get("export_power_w", 0),
            "estimated_revenue_per_kwh": export_data.get("estimated_revenue_per_kwh", 0),
            "export_price_sek_per_kwh": export_data.get("export_price_sek_per_kwh", 0),
            "opportunity_cost": export_data.get("opportunity_cost", 0),
            "reason": export_data.get("reason", ""),
            "battery_soc": export_data.get("battery_soc", 0),
            "solar_excess_w": export_data.get("solar_excess_w", 0),
            "duration_estimate_h": export_data.get("duration_estimate_h", 0),
        }
```

#### Export Revenue Estimate Sensor
```python
class ExportRevenueEstimateSensor(BaseEDSensor):
    """Sensor showing estimated export revenue."""
    
    _attr_name = "Export Revenue Estimate"
    _attr_icon = "mdi:cash-plus"
    _attr_native_unit_of_measurement = "SEK"
    _attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_export_revenue_estimate_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return estimated revenue for next export window."""
        export_data = self.coordinator.data.get("export_opportunity", {})
        if not export_data.get("should_export", False):
            return 0.0
        
        power_w = export_data.get("export_power_w", 0)
        price_per_kwh = export_data.get("estimated_revenue_per_kwh", 0)
        duration_h = export_data.get("duration_estimate_h", 0)
        
        revenue = (power_w / 1000) * price_per_kwh * duration_h
        return round(revenue, 2)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return revenue calculation details."""
        export_data = self.coordinator.data.get("export_opportunity", {})
        
        return {
            "export_power_kw": export_data.get("export_power_w", 0) / 1000,
            "price_per_kwh": export_data.get("estimated_revenue_per_kwh", 0),
            "duration_hours": export_data.get("duration_estimate_h", 0),
            "battery_degradation_cost": export_data.get("battery_degradation_cost", 0),
            "net_revenue": export_data.get("net_revenue", 0),
        }
```

### 4. Load Shifting Sensors

#### Load Shift Opportunity Sensor
```python
class LoadShiftOpportunitySensor(BaseEDSensor):
    """Sensor showing best load shifting opportunity."""
    
    _attr_name = "Load Shift Opportunity"
    _attr_icon = "mdi:clock-time-four"
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_load_shift_opportunity_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[str]:
        """Return description of best shift opportunity."""
        opportunities = self.coordinator.data.get("load_shift_opportunities", [])
        if not opportunities:
            return "No opportunities"
        
        best = opportunities[0]
        return f"Shift to {best['shift_to'].strftime('%H:%M')}"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return shift opportunity details."""
        opportunities = self.coordinator.data.get("load_shift_opportunities", [])
        if not opportunities:
            return {}
        
        best = opportunities[0]
        return {
            "shift_to_time": best.get("shift_to").isoformat(),
            "savings_per_hour_sek": best.get("savings_per_hour_sek", 0),
            "price_now": best.get("price_now", 0),
            "price_then": best.get("price_then", 0),
            "affected_loads": best.get("affected_loads", []),
            "user_impact": best.get("user_impact", "medium"),
            "all_opportunities": opportunities,
        }
```

#### Load Shift Savings Sensor
```python
class LoadShiftSavingsSensor(BaseEDSensor):
    """Sensor showing potential savings from load shifting."""
    
    _attr_name = "Load Shift Savings Potential"
    _attr_icon = "mdi:piggy-bank"
    _attr_native_unit_of_measurement = "SEK"
    _attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_load_shift_savings_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return potential savings from best opportunity."""
        opportunities = self.coordinator.data.get("load_shift_opportunities", [])
        if not opportunities:
            return 0.0
        
        # Sum all savings opportunities
        total_savings = sum(opp.get("savings_per_hour_sek", 0) for opp in opportunities)
        return round(total_savings, 2)
```

### 5. Cost Summary Sensors

#### Estimated Savings Today Sensor
```python
class EstimatedSavingsTodaySensor(BaseEDSensor):
    """Sensor showing estimated cost savings for today."""
    
    _attr_name = "Estimated Savings Today"
    _attr_icon = "mdi:piggy-bank"
    _attr_native_unit_of_measurement = "SEK"
    _attr_state_class = SensorStateClass.TOTAL
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_estimated_savings_today_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[float]:
        """Return estimated savings for today."""
        savings_data = self.coordinator.data.get("cost_savings", {})
        return round(savings_data.get("today_sek", 0), 2)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return savings breakdown."""
        savings_data = self.coordinator.data.get("cost_savings", {})
        
        return {
            "battery_optimization_sek": savings_data.get("battery_optimization_sek", 0),
            "ev_charging_optimization_sek": savings_data.get("ev_charging_optimization_sek", 0),
            "appliance_scheduling_sek": savings_data.get("appliance_scheduling_sek", 0),
            "peak_shaving_sek": savings_data.get("peak_shaving_sek", 0),
            "export_revenue_sek": savings_data.get("export_revenue_sek", 0),
            "baseline_cost_sek": savings_data.get("baseline_cost_sek", 0),
            "actual_cost_sek": savings_data.get("actual_cost_sek", 0),
            "savings_percentage": savings_data.get("savings_percentage", 0),
        }
```

#### Next Cheap Period Sensor
```python
class NextCheapPeriodSensor(BaseEDSensor):
    """Sensor showing when next cheap period begins."""
    
    _attr_name = "Next Cheap Period"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = "timestamp"
    
    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_next_cheap_period_{self._entry_id}"
    
    @property
    def native_value(self) -> Optional[datetime]:
        """Return start of next cheap period."""
        cost_windows = self.coordinator.data.get("cost_windows", {})
        next_cheap = cost_windows.get("next_cheap_start")
        return next_cheap
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return cheap period details."""
        cost_windows = self.coordinator.data.get("cost_windows", {})
        
        return {
            "start_time": cost_windows.get("next_cheap_start"),
            "end_time": cost_windows.get("next_cheap_end"),
            "duration_hours": cost_windows.get("next_cheap_duration_h", 0),
            "avg_price_sek_per_kwh": cost_windows.get("next_cheap_avg_price", 0),
            "recommended_actions": cost_windows.get("next_cheap_recommendations", []),
        }
```

---

## Services API Design

### 1. Override Battery Mode Service

```yaml
# services.yaml
override_battery_mode:
  name: Override Battery Mode
  description: Temporarily override automatic battery optimization
  fields:
    mode:
      name: Mode
      description: Battery operation mode to enforce
      required: true
      selector:
        select:
          options:
            - label: "Charge"
              value: "charge"
            - label: "Discharge"
              value: "discharge"
            - label: "Hold"
              value: "hold"
            - label: "Auto"
              value: "auto"
    duration_minutes:
      name: Duration
      description: How long to maintain override (minutes)
      required: false
      default: 60
      selector:
        number:
          min: 5
          max: 1440
          step: 5
          unit_of_measurement: "minutes"
    power_w:
      name: Power
      description: Power level for charge/discharge (W)
      required: false
      selector:
        number:
          min: 0
          max: 10000
          step: 100
          unit_of_measurement: "W"
```

Implementation:
```python
async def async_override_battery_mode(call: ServiceCall) -> None:
    """Handle override battery mode service call."""
    mode = call.data["mode"]
    duration_minutes = call.data.get("duration_minutes", 60)
    power_w = call.data.get("power_w")
    
    # Store override in coordinator
    coordinator.set_battery_override(
        mode=mode,
        duration_minutes=duration_minutes,
        power_w=power_w,
        expires_at=dt_util.now() + timedelta(minutes=duration_minutes)
    )
    
    _LOGGER.info(f"Battery mode override: {mode} for {duration_minutes} minutes")
    
    # Trigger update
    await coordinator.async_request_refresh()
```

### 2. Schedule Appliance Service

```yaml
schedule_appliance:
  name: Schedule Appliance
  description: Get optimal time to run an appliance
  fields:
    appliance:
      name: Appliance
      description: Type of appliance
      required: true
      selector:
        select:
          options:
            - label: "Dishwasher"
              value: "dishwasher"
            - label: "Washing Machine"
              value: "washing_machine"
            - label: "Dryer"
              value: "dryer"
            - label: "Water Heater"
              value: "water_heater"
    power_w:
      name: Power Consumption
      description: Appliance power consumption (W)
      required: true
      selector:
        number:
          min: 100
          max: 5000
          step: 50
          unit_of_measurement: "W"
    duration_hours:
      name: Duration
      description: How long appliance runs (hours)
      required: true
      selector:
        number:
          min: 0.25
          max: 12
          step: 0.25
          unit_of_measurement: "hours"
    earliest_start:
      name: Earliest Start Time
      description: Earliest acceptable start time
      required: false
      selector:
        time:
    latest_end:
      name: Latest End Time
      description: Latest acceptable completion time
      required: false
      selector:
        time:
```

Implementation:
```python
async def async_schedule_appliance(call: ServiceCall) -> None:
    """Handle appliance scheduling service call."""
    appliance = call.data["appliance"]
    power_w = call.data["power_w"]
    duration_hours = call.data["duration_hours"]
    earliest_start = call.data.get("earliest_start")
    latest_end = call.data.get("latest_end")
    
    # Get optimization
    from .appliance_optimizer import ApplianceOptimizer
    optimizer = ApplianceOptimizer(coordinator)
    
    recommendation = await optimizer.optimize_schedule(
        appliance_name=appliance,
        power_w=power_w,
        duration_hours=duration_hours,
        earliest_start=earliest_start,
        latest_end=latest_end
    )
    
    # Store recommendation
    coordinator.set_appliance_recommendation(appliance, recommendation)
    
    # Send notification
    await hass.services.async_call(
        "notify",
        "persistent_notification",
        {
            "title": f"{appliance.replace('_', ' ').title()} Schedule",
            "message": f"Optimal time: {recommendation['optimal_start_time'].strftime('%H:%M')}\n"
                      f"Estimated cost: {recommendation['estimated_cost_sek']:.2f} SEK\n"
                      f"Savings: {recommendation['cost_savings_vs_now_sek']:.2f} SEK\n"
                      f"Reason: {recommendation['reason']}",
        }
    )
```

### 3. Enable/Disable Export Service

```yaml
set_export_mode:
  name: Set Export Mode
  description: Configure energy export behavior
  fields:
    mode:
      name: Export Mode
      description: When to export energy to grid
      required: true
      selector:
        select:
          options:
            - label: "Never Export"
              value: "never"
            - label: "Excess Solar Only"
              value: "excess_solar_only"
            - label: "Peak Price Opportunistic"
              value: "peak_price_opportunistic"
            - label: "Always Optimize"
              value: "always_optimize"
    min_export_price:
      name: Minimum Export Price
      description: Minimum price to consider export (SEK/kWh)
      required: false
      default: 3.0
      selector:
        number:
          min: 0
          max: 10
          step: 0.1
          unit_of_measurement: "SEK/kWh"
```

---

## Configuration Schema

### New Configuration Options

Add to `config_flow.py` options flow:

```python
# In OptionsFlowHandler.async_step_optimization()
vol.Schema({
    # Appliance Scheduling
    vol.Optional("enable_appliance_optimization", default=True): cv.boolean,
    vol.Optional("dishwasher_power_w", default=1800): vol.All(
        vol.Coerce(int), vol.Range(min=100, max=5000)
    ),
    vol.Optional("washing_machine_power_w", default=2000): vol.All(
        vol.Coerce(int), vol.Range(min=100, max=5000)
    ),
    vol.Optional("water_heater_power_w", default=3000): vol.All(
        vol.Coerce(int), vol.Range(min=100, max=10000)
    ),
    
    # Export Settings
    vol.Optional("export_mode", default="never"): vol.In([
        "never", "excess_solar_only", "peak_price_opportunistic", "always_optimize"
    ]),
    vol.Optional("min_export_price_sek_per_kwh", default=3.0): vol.All(
        vol.Coerce(float), vol.Range(min=0.0, max=10.0)
    ),
    vol.Optional("battery_degradation_cost_per_cycle_sek", default=0.50): vol.All(
        vol.Coerce(float), vol.Range(min=0.0, max=5.0)
    ),
    
    # Peak Shaving
    vol.Optional("enable_peak_shaving", default=False): cv.boolean,
    vol.Optional("peak_threshold_w", default=10000): vol.All(
        vol.Coerce(int), vol.Range(min=1000, max=50000)
    ),
    
    # Comfort Settings
    vol.Optional("comfort_priority", default="balanced"): vol.In([
        "cost_first", "balanced", "comfort_first"
    ]),
    vol.Optional("quiet_hours_start", default="22:00"): cv.time,
    vol.Optional("quiet_hours_end", default="07:00"): cv.time,
    
    # Weather Integration
    vol.Optional("enable_weather_optimization", default=True): cv.boolean,
    vol.Optional("weather_entity", default=""): cv.entity_id,
})
```

---

## Translation Keys

### English Translation Structure (translations/en.json)

```json
{
  "entity": {
    "sensor": {
      "dishwasher_optimal_time": {
        "name": "Dishwasher Optimal Start Time"
      },
      "washing_machine_optimal_time": {
        "name": "Washing Machine Optimal Start Time"
      },
      "water_heater_optimal_time": {
        "name": "Water Heater Optimal Time"
      },
      "ev_charging_recommendation": {
        "name": "EV Charging Recommendation"
      },
      "export_revenue_estimate": {
        "name": "Export Revenue Estimate"
      },
      "load_shift_opportunity": {
        "name": "Load Shift Opportunity"
      },
      "load_shift_savings": {
        "name": "Load Shift Savings Potential"
      },
      "estimated_savings_today": {
        "name": "Estimated Savings Today"
      },
      "estimated_savings_month": {
        "name": "Estimated Savings This Month"
      },
      "next_cheap_period": {
        "name": "Next Cheap Period"
      },
      "next_high_cost_period": {
        "name": "Next High Cost Period"
      }
    },
    "binary_sensor": {
      "export_opportunity": {
        "name": "Export Opportunity"
      }
    }
  },
  "config": {
    "step": {
      "optimization": {
        "title": "Optimization Settings",
        "description": "Configure advanced AI-like optimization features",
        "data": {
          "enable_appliance_optimization": "Enable Appliance Scheduling",
          "dishwasher_power_w": "Dishwasher Power (W)",
          "washing_machine_power_w": "Washing Machine Power (W)",
          "water_heater_power_w": "Water Heater Power (W)",
          "export_mode": "Export Mode",
          "min_export_price_sek_per_kwh": "Minimum Export Price (SEK/kWh)",
          "battery_degradation_cost_per_cycle_sek": "Battery Degradation Cost per Cycle (SEK)",
          "enable_peak_shaving": "Enable Peak Shaving",
          "peak_threshold_w": "Peak Threshold (W)",
          "comfort_priority": "Comfort Priority",
          "quiet_hours_start": "Quiet Hours Start",
          "quiet_hours_end": "Quiet Hours End",
          "enable_weather_optimization": "Enable Weather-Based Optimization",
          "weather_entity": "Weather Entity"
        },
        "data_description": {
          "enable_appliance_optimization": "Suggest optimal times to run appliances",
          "export_mode": "Never: Don't export; Excess Solar: Export only when battery full; Peak Price: Export during price spikes; Always: Optimize for profit",
          "comfort_priority": "Cost First: Maximize savings; Balanced: Balance cost and comfort; Comfort First: Prioritize convenience"
        }
      }
    }
  },
  "services": {
    "override_battery_mode": {
      "name": "Override Battery Mode",
      "description": "Temporarily override automatic battery optimization",
      "fields": {
        "mode": {
          "name": "Mode",
          "description": "Battery operation mode"
        },
        "duration_minutes": {
          "name": "Duration",
          "description": "Override duration (minutes)"
        },
        "power_w": {
          "name": "Power",
          "description": "Power level (W)"
        }
      }
    },
    "schedule_appliance": {
      "name": "Schedule Appliance",
      "description": "Get optimal time to run an appliance",
      "fields": {
        "appliance": {
          "name": "Appliance",
          "description": "Type of appliance"
        },
        "power_w": {
          "name": "Power",
          "description": "Power consumption (W)"
        },
        "duration_hours": {
          "name": "Duration",
          "description": "Runtime (hours)"
        }
      }
    },
    "set_export_mode": {
      "name": "Set Export Mode",
      "description": "Configure energy export behavior",
      "fields": {
        "mode": {
          "name": "Mode",
          "description": "Export mode"
        },
        "min_export_price": {
          "name": "Minimum Price",
          "description": "Minimum export price (SEK/kWh)"
        }
      }
    }
  }
}
```

### Swedish Translation Structure (translations/sv.json)

```json
{
  "entity": {
    "sensor": {
      "dishwasher_optimal_time": {
        "name": "Diskmaskin Optimal Starttid"
      },
      "washing_machine_optimal_time": {
        "name": "Tvättmaskin Optimal Starttid"
      },
      "water_heater_optimal_time": {
        "name": "Varmvattenberedare Optimal Tid"
      },
      "ev_charging_recommendation": {
        "name": "EV Laddningsrekommendation"
      },
      "export_revenue_estimate": {
        "name": "Export Intäktsuppskattning"
      },
      "load_shift_opportunity": {
        "name": "Lastskiftningsmöjlighet"
      },
      "load_shift_savings": {
        "name": "Lastskiftning Besparingspotential"
      },
      "estimated_savings_today": {
        "name": "Uppskattade Besparingar Idag"
      },
      "estimated_savings_month": {
        "name": "Uppskattade Besparingar Denna Månad"
      },
      "next_cheap_period": {
        "name": "Nästa Billiga Period"
      },
      "next_high_cost_period": {
        "name": "Nästa Höga Kostnadsperiod"
      }
    },
    "binary_sensor": {
      "export_opportunity": {
        "name": "Exportmöjlighet"
      }
    }
  },
  "config": {
    "step": {
      "optimization": {
        "title": "Optimeringsinställningar",
        "description": "Konfigurera avancerade AI-liknande optimeringsfunktioner",
        "data": {
          "enable_appliance_optimization": "Aktivera Schemaläggning av Apparater",
          "dishwasher_power_w": "Diskmaskin Effekt (W)",
          "washing_machine_power_w": "Tvättmaskin Effekt (W)",
          "water_heater_power_w": "Varmvattenberedare Effekt (W)",
          "export_mode": "Exportläge",
          "min_export_price_sek_per_kwh": "Minsta Exportpris (SEK/kWh)",
          "battery_degradation_cost_per_cycle_sek": "Batteriförslitningskostnad per Cykel (SEK)",
          "enable_peak_shaving": "Aktivera Toppkapning",
          "peak_threshold_w": "Topptröskel (W)",
          "comfort_priority": "Komfortprioritet",
          "quiet_hours_start": "Tysta Timmar Start",
          "quiet_hours_end": "Tysta Timmar Slut",
          "enable_weather_optimization": "Aktivera Väderbaserad Optimering",
          "weather_entity": "Väderentitet"
        },
        "data_description": {
          "enable_appliance_optimization": "Föreslå optimala tider för att köra apparater",
          "export_mode": "Aldrig: Exportera inte; Överskott Sol: Exportera endast när batteriet är fullt; Toppris: Exportera under prisspike; Alltid: Optimera för vinst",
          "comfort_priority": "Kostnad Först: Maximera besparingar; Balanserad: Balansera kostnad och komfort; Komfort Först: Prioritera bekvämlighet"
        }
      }
    }
  },
  "services": {
    "override_battery_mode": {
      "name": "Åsidosätt Batteriläge",
      "description": "Tillfälligt åsidosätt automatisk batterioptimering",
      "fields": {
        "mode": {
          "name": "Läge",
          "description": "Batteridriftläge"
        },
        "duration_minutes": {
          "name": "Varaktighet",
          "description": "Åsidosättningens varaktighet (minuter)"
        },
        "power_w": {
          "name": "Effekt",
          "description": "Effektnivå (W)"
        }
      }
    },
    "schedule_appliance": {
      "name": "Schemalägg Apparat",
      "description": "Få optimal tid att köra en apparat",
      "fields": {
        "appliance": {
          "name": "Apparat",
          "description": "Typ av apparat"
        },
        "power_w": {
          "name": "Effekt",
          "description": "Effektförbrukning (W)"
        },
        "duration_hours": {
          "name": "Varaktighet",
          "description": "Körtid (timmar)"
        }
      }
    },
    "set_export_mode": {
      "name": "Ställ In Exportläge",
      "description": "Konfigurera energiexportbeteende",
      "fields": {
        "mode": {
          "name": "Läge",
          "description": "Exportläge"
        },
        "min_export_price": {
          "name": "Minimipris",
          "description": "Minsta exportpris (SEK/kWh)"
        }
      }
    }
  }
}
```

---

## Testing Strategy

### Unit Tests

Create `tests/test_appliance_optimizer.py`:
```python
"""Tests for appliance optimizer."""
import pytest
from datetime import datetime, timedelta
from custom_components.energy_dispatcher.appliance_optimizer import ApplianceOptimizer
from custom_components.energy_dispatcher.models import PricePoint, ForecastPoint

def test_optimize_dishwasher_schedule():
    """Test dishwasher optimization."""
    prices = [
        PricePoint(datetime(2025, 1, 1, h, 0), 1.0 + h * 0.1, 1.5 + h * 0.1)
        for h in range(24)
    ]
    solar = [
        ForecastPoint(datetime(2025, 1, 1, h, 0), max(0, 2000 * (1 - abs(h - 12) / 6)))
        for h in range(24)
    ]
    
    optimizer = ApplianceOptimizer()
    result = optimizer.optimize_schedule(
        appliance_name="dishwasher",
        power_w=1800,
        duration_hours=2.0,
        earliest_start=datetime(2025, 1, 1, 10, 0),
        latest_end=datetime(2025, 1, 1, 22, 0),
        prices=prices,
        solar_forecast=solar,
        battery_soc=50.0,
        battery_capacity_kwh=15.0,
    )
    
    assert result is not None
    assert "optimal_start_time" in result
    assert "estimated_cost_sek" in result
    assert result["estimated_cost_sek"] > 0
    assert result["optimal_start_time"].hour in range(10, 20)  # During allowed window
```

### Integration Tests

Create `tests/test_optimization_coordinator.py`:
```python
"""Tests for optimization coordinator."""
import pytest
from custom_components.energy_dispatcher.optimization_coordinator import OptimizationCoordinator

@pytest.mark.asyncio
async def test_full_optimization_cycle(hass, mock_coordinator):
    """Test complete optimization cycle."""
    opt_coordinator = OptimizationCoordinator(mock_coordinator)
    
    result = await opt_coordinator.compute_optimizations()
    
    assert result is not None
    assert "appliance_recommendations" in result
    assert "ev_charging_recommendation" in result
    assert "export_opportunity" in result
    assert "load_shift_opportunities" in result
    assert "cost_savings" in result
```

---

## Performance Considerations

### 1. Caching Strategy

```python
from functools import lru_cache
from datetime import timedelta

class OptimizationCoordinator:
    """Coordinator with caching for expensive operations."""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def get_cached_or_compute(self, key: str, compute_func, *args, **kwargs):
        """Get from cache or compute and cache result."""
        cache_entry = self._cache.get(key)
        now = dt_util.now()
        
        if cache_entry and (now - cache_entry["timestamp"]) < self._cache_ttl:
            return cache_entry["data"]
        
        # Compute new result
        result = compute_func(*args, **kwargs)
        
        # Cache it
        self._cache[key] = {
            "data": result,
            "timestamp": now
        }
        
        return result
```

### 2. Asynchronous Processing

```python
import asyncio

async def compute_all_optimizations(self):
    """Compute all optimizations concurrently."""
    tasks = [
        self.compute_appliance_schedules(),
        self.compute_ev_charging(),
        self.compute_export_opportunities(),
        self.compute_load_shifts(),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "appliance_recommendations": results[0] if not isinstance(results[0], Exception) else {},
        "ev_charging_recommendation": results[1] if not isinstance(results[1], Exception) else {},
        "export_opportunity": results[2] if not isinstance(results[2], Exception) else {},
        "load_shift_opportunities": results[3] if not isinstance(results[3], Exception) else [],
    }
```

### 3. Update Frequency

```python
# In coordinator
UPDATE_INTERVAL_OPTIMIZATION = timedelta(minutes=15)  # Less frequent than main updates
UPDATE_INTERVAL_APPLIANCE = timedelta(hours=1)        # Even less frequent for appliances
UPDATE_INTERVAL_EXPORT = timedelta(minutes=5)          # More frequent for export opportunities
```

---

## Next Steps

1. **Implement Core Modules**: Start with `appliance_optimizer.py` and basic sensors
2. **Add Configuration UI**: Extend config flow with new options
3. **Create Services**: Implement service handlers for overrides
4. **Add Translations**: Complete EN and SV translations
5. **Write Tests**: Comprehensive unit and integration tests
6. **Documentation**: Update user-facing docs with examples
7. **Dashboard Templates**: Create example dashboard cards
8. **Beta Testing**: Get feedback from real users

---

**This guide provides the foundation for implementing AI-like optimization features. Start with Phase 1 (Appliance Scheduling) and progressively add features based on user feedback and demand.**
