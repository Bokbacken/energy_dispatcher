"""Optimization sensors for Energy Dispatcher.

This module provides sensors for appliance scheduling recommendations,
showing optimal times to run household appliances based on electricity
prices and solar production forecasts.
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import BaseEDSensor


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up optimization sensors from a config entry."""
    # Get coordinator from domain data
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    # Check if appliance optimization is enabled
    config = hass.data[DOMAIN][entry.entry_id]["config"]
    if not config.get("enable_appliance_optimization", False):
        # Optimization not enabled, skip sensor creation
        return

    sensors = [
        DishwasherOptimalTimeSensor(coordinator, entry.entry_id),
        WashingMachineOptimalTimeSensor(coordinator, entry.entry_id),
        WaterHeaterOptimalTimeSensor(coordinator, entry.entry_id),
    ]

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
