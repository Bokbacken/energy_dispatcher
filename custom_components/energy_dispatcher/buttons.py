"""Buttons för manuella kommandon."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import ServiceCall
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SERVICE_FORCE_CHARGE, SERVICE_FORCE_DISCHARGE
from .coordinator import EnergyDispatcherCoordinator
from .dispatcher import ActionDispatcher


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: EnergyDispatcherCoordinator = runtime.coordinator
    dispatcher: ActionDispatcher = runtime.dispatcher

    async_add_entities(
        [
            ForceChargeButton(coordinator, dispatcher, entry.entry_id),
            ForceDischargeButton(coordinator, dispatcher, entry.entry_id),
        ]
    )


class BaseActionButton(CoordinatorEntity[EnergyDispatcherCoordinator], ButtonEntity):
    """Bas för knappar."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyDispatcherCoordinator,
        dispatcher: ActionDispatcher,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._dispatcher = dispatcher

    @property
    def device_info(self):
        config = self.coordinator.config
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": config.name,
            "manufacturer": "Energy Dispatcher",
        }


class ForceChargeButton(BaseActionButton):
    _attr_name = "Force battery charge"

    @property
    def unique_id(self):
        return f"{self._entry_id}_btn_force_charge"

    async def async_press(self):
        await self._dispatcher.async_force_battery_charge({"duration_minutes": 60})


class ForceDischargeButton(BaseActionButton):
    _attr_name = "Force battery discharge"

    @property
    def unique_id(self):
        return f"{self._entry_id}_btn_force_discharge"

    async def async_press(self):
        await self._dispatcher.async_force_battery_discharge({"duration_minutes": 60})
