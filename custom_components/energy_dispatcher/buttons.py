from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    batt = hass.data[DOMAIN][entry.entry_id]["batt"]
    async_add_entities([
        ForceChargeButton("Force charge 30m", "button.energy_dispatcher_force_batt_charge_30m", batt, 30),
        ForceChargeButton("Force charge 60m", "button.energy_dispatcher_force_batt_charge_60m", batt, 60),
        ForceChargeButton("Force charge 120m", "button.energy_dispatcher_force_batt_charge_120m", batt, 120),
    ])

class ForceChargeButton(ButtonEntity):
    def __init__(self, name: str, unique_id: str, batt_adapter, minutes: int):
        self._attr_name = name
        self._attr_unique_id = unique_id
        self.batt = batt_adapter
        self.minutes = minutes

    async def async_press(self) -> None:
        await self.batt.force_charge(self.minutes, power_kw=6.0)  # default 6 kW, can be made configurable
