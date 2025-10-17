from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([ResetBatteryCostButton(hass, entry.entry_id)])


class ResetBatteryCostButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "reset_battery_cost"
    _attr_icon = "mdi:backup-restore"
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_reset_battery_cost_{self._entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )

    async def async_press(self) -> None:
        await self._hass.services.async_call(
            DOMAIN,
            "battery_cost_reset",
            {},
            blocking=True,
        )
