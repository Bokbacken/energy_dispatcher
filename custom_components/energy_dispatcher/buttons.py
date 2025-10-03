from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timedelta
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([
        ForceEV60Button(hass),
        PauseEV30Button(hass),
        ForceBatt60Button(hass),
    ])

class BaseEDButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, "energy_dispatcher")}}

class ForceEV60Button(BaseEDButton):
    @property
    def name(self): return "EV Force Charge 60m"
    @property
    def unique_id(self): return "ed_btn_ev_force_60"

    async def async_press(self):
        until = datetime.now() + timedelta(minutes=60)
        self.hass.bus.async_fire("energy_dispatcher/override", {"key": "ev_force_until", "until": until.isoformat()})

class PauseEV30Button(BaseEDButton):
    @property
    def name(self): return "EV Pause 30m"
    @property
    def unique_id(self): return "ed_btn_ev_pause_30"

    async def async_press(self):
        until = datetime.now() + timedelta(minutes=30)
        self.hass.bus.async_fire("energy_dispatcher/override", {"key": "ev_pause_until", "until": until.isoformat()})

class ForceBatt60Button(BaseEDButton):
    @property
    def name(self): return "Battery Force Charge 60m"
    @property
    def unique_id(self): return "ed_btn_batt_force_60"

    async def async_press(self):
        until = datetime.now() + timedelta(minutes=60)
        self.hass.bus.async_fire("energy_dispatcher/override", {"key": "battery_force_until", "until": until.isoformat()})
