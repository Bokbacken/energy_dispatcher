from __future__ import annotations
from typing import Optional
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, STORE_ENTITIES, STORE_MANUAL, M_EV_TARGET_SOC, EVENT_ACTION

OPTIONS = ["Custom", "80%", "100%"]

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([EVTargetPresetSelect(entry.entry_id)])

class EVTargetPresetSelect(SelectEntity):
    should_poll = False
    def __init__(self, entry_id: str):
        self._entry_id = entry_id
        self._current = "Custom"

    async def async_added_to_hass(self) -> None:
        st = self.hass.data[DOMAIN][self._entry_id]
        target = float(st.get(STORE_MANUAL, {}).get(M_EV_TARGET_SOC, 80.0))
        self._current = "80%" if round(target) == 80 else ("100%" if round(target) == 100 else "Custom")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, "energy_dispatcher")}, name="Energy Dispatcher", manufacturer="Bokbacken")

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_select_ev_target_preset_{self._entry_id}"

    @property
    def name(self) -> str:
        return "EV Mål SOC – Snabbval"

    @property
    def options(self):
        return OPTIONS

    @property
    def current_option(self) -> Optional[str]:
        return self._current

    async def async_select_option(self, option: str) -> None:
        self._current = option
        st = self.hass.data[DOMAIN][self._entry_id]
        ent_id = st.get(STORE_ENTITIES, {}).get("number_ev_target_soc")
        if option in ("80%", "100%"):
            value = 80.0 if option == "80%" else 100.0
            st.setdefault(STORE_MANUAL, {})[M_EV_TARGET_SOC] = value
            if ent_id:
                await self.hass.services.async_call("number", "set_value", {"entity_id": ent_id, "value": value}, blocking=False)
            self.hass.bus.async_fire(EVENT_ACTION, {"entry_id": self._entry_id, "entity_id": self.entity_id, "key": "ev_target_preset", "value": option})
            await self.hass.services.async_call(
                "logbook", "log",
                {"name": "Energy Dispatcher", "message": f"EV mål SOC preset → {option}", "domain": "energy_dispatcher"},
                blocking=False
            )
        self.async_write_ha_state()
