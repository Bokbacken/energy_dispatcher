from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([
        ForceEV60Button(hass, entry.entry_id),
        PauseEV30Button(hass, entry.entry_id),
        ForceBatt60Button(hass, entry.entry_id),
    ])


class BaseEDButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self.hass = hass
        self._entry_id = entry_id

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, "energy_dispatcher")}}

    @property
    def should_poll(self) -> bool:
        return False


class ForceEV60Button(BaseEDButton):
    @property
    def name(self): return "EV Force Charge 60m"

    @property
    def unique_id(self): return f"{DOMAIN}_btn_ev_force_60_{self._entry_id}"

    async def async_press(self):
        until = datetime.now() + timedelta(minutes=60)
        self.hass.bus.async_fire("energy_dispatcher/override", {"key": "ev_force_until", "until": until.isoformat(), "forced_current": 16})


class PauseEV30Button(BaseEDButton):
    @property
    def name(self): return "EV Pause 30m"

    @property
    def unique_id(self): return f"{DOMAIN}_btn_ev_pause_30_{self._entry_id}"

    async def async_press(self):
        until = datetime.now() + timedelta(minutes=30)
        self.hass.bus.async_fire("energy_dispatcher/override", {"key": "ev_pause_until", "until": until.isoformat()})


class ForceBatt60Button(BaseEDButton):
    @property
    def name(self): return "Battery Force Charge 60m"

    @property
    def unique_id(self): return f"{DOMAIN}_btn_batt_force_60_{self._entry_id}"

    async def async_press(self):
        # Skicka direkt service-anrop så vi sätter rätt power/duration
        await self.hass.services.async_call(
            DOMAIN,
            "force_battery_charge",
            {"power_w": 10000, "duration": 60},
            blocking=False,
        )
