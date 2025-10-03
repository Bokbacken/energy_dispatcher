from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([ResetBatteryCostButton(hass, entry.entry_id)])


class ResetBatteryCostButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id
        self._attr_name = "Reset Battery Energy Cost"
        self._attr_icon = "mdi:backup-restore"

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
