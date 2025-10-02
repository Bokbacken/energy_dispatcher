"""Sensor-entity definitions."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_PLAN,
    ATTR_PRICE_SCHEDULE,
    ATTR_SOLAR_FORECAST,
    DOMAIN,
)
from .coordinator import EnergyDispatcherCoordinator
from .models import EnergyDispatcherData


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: EnergyDispatcherCoordinator = runtime.coordinator

    async_add_entities(
        [
            PlanSummarySensor(coordinator, entry.entry_id),
            PriceScheduleSensor(coordinator, entry.entry_id),
            SolarForecastSensor(coordinator, entry.entry_id),
            BatteryStatusSensor(coordinator, entry.entry_id),
            EVStatusSensor(coordinator, entry.entry_id),
        ]
    )


class BaseDispatcherSensor(CoordinatorEntity[EnergyDispatcherCoordinator], SensorEntity):
    """Bas-klass för sensorspecifika attribut."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnergyDispatcherCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self):
        config = self.coordinator.config
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": config.name,
            "manufacturer": "Energy Dispatcher",
            "model": "Virtual",
        }


class PlanSummarySensor(BaseDispatcherSensor):
    """Ger en översikt över planerade åtgärder."""

    _attr_name = "Plan summary"
    _attr_native_unit_of_measurement = None

    @property
    def unique_id(self) -> str:
        return f"{self._entry_id}_plan_summary"

    @property
    def native_value(self) -> str | None:
        plan = self.coordinator.data.plan if self.coordinator.data else None
        if not plan:
            return None
        return f"{len(plan.battery_actions)} batteri / {len(plan.ev_actions)} EV / {len(plan.household_actions)} hus"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "generated_at": data.plan.generated_at.isoformat(),
            "battery_actions": [
                {
                    "start": action.start.isoformat(),
                    "end": action.end.isoformat(),
                    "type": action.action_type,
                    "notes": action.notes,
                }
                for action in data.plan.battery_actions
            ],
            "ev_actions": [
                {
                    "start": action.start.isoformat(),
                    "end": action.end.isoformat(),
                    "type": action.action_type,
                    "notes": action.notes,
                }
                for action in data.plan.ev_actions
            ],
            "household_actions": [
                {
                    "start": action.start.isoformat(),
                    "end": action.end.isoformat(),
                    "type": action.action_type,
                    "notes": action.notes,
                }
                for action in data.plan.household_actions
            ],
        }


class PriceScheduleSensor(BaseDispatcherSensor):
    _attr_name = "Price schedule"

    @property
    def unique_id(self) -> str:
        return f"{self._entry_id}_price_schedule"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        now = datetime.now(UTC)
        current = next(
            (p for p in self.coordinator.data.price_points if p.start <= now < p.end),
            None,
        )
        return current.price if current else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "currency": self.coordinator.config.prices.currency,
            "prices": [
                {
                    "start": p.start.isoformat(),
                    "end": p.end.isoformat(),
                    "price": p.price,
                    "predicted": p.is_predicted,
                }
                for p in self.coordinator.data.price_points
            ],
        }


class SolarForecastSensor(BaseDispatcherSensor):
    _attr_name = "Solar forecast"

    @property
    def unique_id(self) -> str:
        return f"{self._entry_id}_solar_forecast"

    @property
    def native_value(self):
        if not self.coordinator.data or not self.coordinator.data.forecast_points:
            return None
        total_wh = self.coordinator.data.forecast_points[-1].cumulative_wh
        return round(total_wh / 1000, 2)

    @property
    def native_unit_of_measurement(self):
        return "kWh"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "forecast": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "watts": p.watts,
                    "watt_hours_period": p.watt_hours_period,
                    "cumulative_wh": p.cumulative_wh,
                }
                for p in self.coordinator.data.forecast_points
            ]
        }


class BatteryStatusSensor(BaseDispatcherSensor):
    _attr_name = "Battery status"

    @property
    def unique_id(self):
        return f"{self._entry_id}_battery"

    @property
    def native_value(self):
        if not self.coordinator.data or not self.coordinator.data.battery_state:
            return None
        return round(self.coordinator.data.battery_state.soc * 100, 1)

    @property
    def native_unit_of_measurement(self):
        return "%"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data or not self.coordinator.data.battery_state:
            return {}
        state = self.coordinator.data.battery_state
        return {
            "power_kw": state.power_kw,
            "price_per_kwh": state.price_per_kwh,
            "estimated_hours_remaining": state.estimated_hours_remaining,
            "last_update": state.last_update.isoformat(),
        }


class EVStatusSensor(BaseDispatcherSensor):
    _attr_name = "EV status"

    @property
    def unique_id(self):
        return f"{self._entry_id}_ev"

    @property
    def native_value(self):
        if not self.coordinator.data or not self.coordinator.data.ev_state:
            return None
        return round(self.coordinator.data.ev_state.soc * 100, 1)

    @property
    def native_unit_of_measurement(self):
        return "%"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data or not self.coordinator.data.ev_state:
            return {}
        ev = self.coordinator.data.ev_state
        return {
            "target_soc": ev.target_soc,
            "required_kwh": ev.required_kwh,
            "estimated_charge_time": ev.estimated_charge_time,
            "charger_available": ev.charger_available,
            "last_update": ev.last_update.isoformat(),
        }
