"""Optimization sensors for Energy Dispatcher.

This module provides sensors for appliance scheduling recommendations,
showing optimal times to run household appliances based on electricity
prices and solar production forecasts.

Also provides weather-adjusted solar forecast sensor.
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import BaseEDSensor


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up optimization sensors from a config entry."""
    # Get coordinator from domain data
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    # Get config
    config = hass.data[DOMAIN][entry.entry_id]["config"]
    
    sensors = []
    
    # Add appliance optimization sensors if enabled
    if config.get("enable_appliance_optimization", False):
        sensors.extend([
            DishwasherOptimalTimeSensor(coordinator, entry.entry_id),
            WashingMachineOptimalTimeSensor(coordinator, entry.entry_id),
            WaterHeaterOptimalTimeSensor(coordinator, entry.entry_id),
        ])
    
    # Add weather-adjusted solar forecast sensor if weather optimization is enabled
    if config.get("enable_weather_optimization", True):
        sensors.append(
            WeatherAdjustedSolarForecastSensor(hass, entry, coordinator)
        )
    
    # Add export opportunity sensors if export mode is enabled
    export_mode = config.get("export_mode", "never")
    if export_mode != "never":
        sensors.extend([
            ExportOpportunityBinarySensor(coordinator, entry.entry_id),
            ExportRevenueEstimateSensor(coordinator, entry.entry_id),
        ])

    if sensors:
        async_add_entities(sensors, False)


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
        recommendations = self.coordinator.data.get("appliance_recommendations", {})
        recommendation = recommendations.get("dishwasher")
        if not recommendation:
            return None
        
        optimal_time = recommendation.get("optimal_start_time")
        if optimal_time:
            return optimal_time.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recommendation details."""
        recommendations = self.coordinator.data.get("appliance_recommendations", {})
        recommendation = recommendations.get("dishwasher")
        if not recommendation:
            return {}

        return {
            "estimated_cost_sek": round(recommendation.get("estimated_cost_sek", 0), 2),
            "cost_savings_vs_now_sek": round(recommendation.get("cost_savings_vs_now_sek", 0), 2),
            "reason": recommendation.get("reason", ""),
            "price_at_optimal_time": round(recommendation.get("price_at_optimal_time", 0), 2),
            "current_price": round(recommendation.get("current_price", 0), 2),
            "solar_available": recommendation.get("solar_available", False),
            "alternative_times": recommendation.get("alternative_times", []),
            "confidence": recommendation.get("confidence", "medium"),
        }

    @property
    def device_class(self) -> str:
        return "timestamp"


class WashingMachineOptimalTimeSensor(BaseEDSensor):
    """Sensor showing optimal time to run washing machine."""

    _attr_name = "Washing Machine Optimal Start Time"
    _attr_icon = "mdi:washing-machine"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_washing_machine_optimal_time_{self._entry_id}"

    @property
    def native_value(self) -> Optional[str]:
        """Return optimal start time as ISO datetime string."""
        recommendations = self.coordinator.data.get("appliance_recommendations", {})
        recommendation = recommendations.get("washing_machine")
        if not recommendation:
            return None
        
        optimal_time = recommendation.get("optimal_start_time")
        if optimal_time:
            return optimal_time.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recommendation details."""
        recommendations = self.coordinator.data.get("appliance_recommendations", {})
        recommendation = recommendations.get("washing_machine")
        if not recommendation:
            return {}

        return {
            "estimated_cost_sek": round(recommendation.get("estimated_cost_sek", 0), 2),
            "cost_savings_vs_now_sek": round(recommendation.get("cost_savings_vs_now_sek", 0), 2),
            "reason": recommendation.get("reason", ""),
            "price_at_optimal_time": round(recommendation.get("price_at_optimal_time", 0), 2),
            "current_price": round(recommendation.get("current_price", 0), 2),
            "solar_available": recommendation.get("solar_available", False),
            "alternative_times": recommendation.get("alternative_times", []),
            "confidence": recommendation.get("confidence", "medium"),
        }

    @property
    def device_class(self) -> str:
        return "timestamp"


class WaterHeaterOptimalTimeSensor(BaseEDSensor):
    """Sensor showing optimal time to heat water."""

    _attr_name = "Water Heater Optimal Time"
    _attr_icon = "mdi:water-boiler"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_water_heater_optimal_time_{self._entry_id}"

    @property
    def native_value(self) -> Optional[str]:
        """Return optimal start time as ISO datetime string."""
        recommendations = self.coordinator.data.get("appliance_recommendations", {})
        recommendation = recommendations.get("water_heater")
        if not recommendation:
            return None
        
        optimal_time = recommendation.get("optimal_start_time")
        if optimal_time:
            return optimal_time.isoformat()
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recommendation details."""
        recommendations = self.coordinator.data.get("appliance_recommendations", {})
        recommendation = recommendations.get("water_heater")
        if not recommendation:
            return {}

        return {
            "estimated_cost_sek": round(recommendation.get("estimated_cost_sek", 0), 2),
            "cost_savings_vs_now_sek": round(recommendation.get("cost_savings_vs_now_sek", 0), 2),
            "reason": recommendation.get("reason", ""),
            "price_at_optimal_time": round(recommendation.get("price_at_optimal_time", 0), 2),
            "current_price": round(recommendation.get("current_price", 0), 2),
            "solar_available": recommendation.get("solar_available", False),
            "alternative_times": recommendation.get("alternative_times", []),
            "confidence": recommendation.get("confidence", "medium"),
        }

    @property
    def device_class(self) -> str:
        return "timestamp"

    @property
    def device_class(self) -> str:
        return "timestamp"


class WeatherAdjustedSolarForecastSensor(BaseEDSensor):
    """Sensor showing weather-adjusted solar forecast."""

    _attr_name = "Weather Adjusted Solar Forecast"
    _attr_icon = "mdi:weather-partly-cloudy"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, entry, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator, entry.entry_id)
        self.hass = hass
        self._entry = entry
        self._state = None

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_weather_adjusted_solar_forecast_{self._entry_id}"

    @property
    def native_value(self) -> Optional[float]:
        """Return the weather-adjusted solar forecast for today in kWh."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return weather-adjusted forecast details."""
        weather_data = self.coordinator.data.get("weather_adjusted_solar", {})
        
        return {
            "base_forecast_kwh": weather_data.get("base_forecast_kwh", 0.0),
            "weather_adjusted_kwh": weather_data.get("weather_adjusted_kwh", 0.0),
            "confidence_level": weather_data.get("confidence_level", "unknown"),
            "limiting_factor": weather_data.get("limiting_factor", "unknown"),
            "avg_adjustment_factor": weather_data.get("avg_adjustment_factor", 1.0),
            "reduction_percentage": weather_data.get("reduction_percentage", 0.0),
            "forecast": weather_data.get("forecast_points", []),
        }

    async def async_update(self):
        """Update the sensor state."""
        # Get weather-adjusted data from coordinator
        weather_data = self.coordinator.data.get("weather_adjusted_solar", {})
        
        # Set state to the adjusted forecast in kWh
        self._state = weather_data.get("weather_adjusted_kwh", 0.0)


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
