from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import EnergyDispatcherCoordinator

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    coord: EnergyDispatcherCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        PlanLengthSensor(coord),
    ])

class PlanLengthSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Energy Dispatcher plan length"
    _attr_unique_id = "energy_dispatcher_plan_length"
    _attr_native_unit_of_measurement = "slots"

    def __init__(self, coord: EnergyDispatcherCoordinator):
        super().__init__(coord)
        self._attr_native_value = 0

    @property
    def native_value(self):
        return len(self.coordinator.plan)
