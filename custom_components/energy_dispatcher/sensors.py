from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    entities = [
        BatteryCostSensor(hass),
        EnrichedPriceSensor(hass),
        BatteryRuntimeSensor(hass),
    ]
    async_add_entities(entities, True)

class BaseEDSensor(SensorEntity):
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )

class BatteryCostSensor(BaseEDSensor):
    _attr_name = "Battery Energy Cost"
    _attr_unique_id = "energy_dispatcher_battery_cost"
    _attr_native_unit_of_measurement = "SEK/kWh"

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._state = 0.0

    async def async_update(self):
        # TODO: read from bec store or coordinator
        self._state = self.hass.data.get(DOMAIN, {}).get("wace", 0.0)

    @property
    def native_value(self):
        return self._state

class EnrichedPriceSensor(BaseEDSensor):
    _attr_name = "Enriched Power Price"
    _attr_unique_id = "energy_dispatcher_enriched_price"
    _attr_native_unit_of_measurement = "SEK/kWh"

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._state = None

    async def async_update(self):
        # TODO: compute from configured Nordpool + taxes
        pass

    @property
    def native_value(self):
        return self._state

class BatteryRuntimeSensor(BaseEDSensor):
    _attr_name = "Battery Runtime Estimate"
    _attr_unique_id = "energy_dispatcher_battery_runtime"
    _attr_native_unit_of_measurement = "h"

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._state = None

    async def async_update(self):
        # TODO: (SoC% * capacity_kWh) / house_avg_kWh_per_h
        pass

    @property
    def native_value(self):
        return self._state
