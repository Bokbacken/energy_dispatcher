from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    st = hass.data[DOMAIN][entry.entry_id]
    flags = st["flags"]
    async_add_entities([
        AutoEVSwitch(hass, entry.entry_id, flags),
        AutoPlannerSwitch(hass, entry.entry_id, flags),
    ])


class BaseEDSwitch(SwitchEntity):
    def __init__(self, hass: HomeAssistant, entry_id: str, flags: dict):
        self.hass = hass
        self._entry_id = entry_id
        self._flags = flags

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, "energy_dispatcher")}}


class AutoEVSwitch(BaseEDSwitch):
    @property
    def name(self): return "Energy Dispatcher - Auto EV"

    @property
    def unique_id(self): return f"{DOMAIN}_switch_auto_ev_{self._entry_id}"

    @property
    def is_on(self) -> bool:
        return bool(self._flags.get("auto_ev_enabled", True))

    async def async_turn_on(self, **kwargs):
        self._flags["auto_ev_enabled"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._flags["auto_ev_enabled"] = False
        self.async_write_ha_state()


class AutoPlannerSwitch(BaseEDSwitch):
    @property
    def name(self): return "Energy Dispatcher - Auto Planner"

    @property
    def unique_id(self): return f"{DOMAIN}_switch_auto_planner_{self._entry_id}"

    @property
    def is_on(self) -> bool:
        return bool(self._flags.get("auto_planner_enabled", True))

    async def async_turn_on(self, **kwargs):
        self._flags["auto_planner_enabled"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._flags["auto_planner_enabled"] = False
        self.async_write_ha_state()
