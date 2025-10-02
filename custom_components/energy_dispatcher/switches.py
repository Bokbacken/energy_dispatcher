"""Switch-entity för att toggla auto-dispatch."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLE_AUTO_DISPATCH, DOMAIN
from .coordinator import EnergyDispatcherCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: EnergyDispatcherCoordinator = runtime.coordinator
    async_add_entities(
        [AutoDispatchSwitch(coordinator, entry.entry_id)],
        update_before_add=True,
    )


class AutoDispatchSwitch(CoordinatorEntity[EnergyDispatcherCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Auto dispatch"

    def __init__(self, coordinator: EnergyDispatcherCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_auto_dispatch"

    @property
    def is_on(self):
        return self.coordinator.config.auto_dispatch

    async def async_turn_on(self, **kwargs):
        await self._set_auto_dispatch(True)

    async def async_turn_off(self, **kwargs):
        await self._set_auto_dispatch(False)

    async def _set_auto_dispatch(self, value: bool):
        # Uppdatera options
        options = dict(self.coordinator.entry.options)
        options[CONF_ENABLE_AUTO_DISPATCH] = value
        self.coordinator.hass.config_entries.async_update_entry(
            self.coordinator.entry, options=options
        )
        await self.coordinator.async_request_refresh()
