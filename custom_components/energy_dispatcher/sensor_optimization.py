"""Optimization sensors for Energy Dispatcher.

This module provides sensors for appliance scheduling recommendations,
showing optimal times to run household appliances based on electricity
prices and solar production forecasts.

Also provides weather-adjusted solar forecast sensor.
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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
