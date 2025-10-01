from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([
        SimpleSwitch("Energy Dispatcher Optimize Battery", "switch.energy_dispatcher_optimize_battery", True),
        SimpleSwitch("Energy Dispatcher Pause", "switch.energy_dispatcher_pause", False),
    ])

class SimpleSwitch(SwitchEntity):
    def __init__(self, name: str, unique_id: str, initial: bool):
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._is_on = initial

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._is_on = False
        self.async_write_ha_state()
