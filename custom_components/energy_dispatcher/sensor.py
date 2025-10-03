from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    st = hass.data[DOMAIN][entry.entry_id]
    coordinator = st["coordinator"]

    entities = [
        EnrichedPriceSensor(coordinator, entry.entry_id),
        BatteryRuntimeSensor(coordinator, entry.entry_id),
        BatteryCostSensor(coordinator, entry.entry_id),
        SolarPowerNowSensor(coordinator, entry.entry_id),
        SolarEnergyTodaySensor(coordinator, entry.entry_id),
        SolarEnergyTomorrowSensor(coordinator, entry.entry_id),
        PVPowerNowSensor(coordinator, entry.entry_id),
        PVEnergyTodaySensor(coordinator, entry.entry_id),
    ]
    async_add_entities(entities)


class BaseEDSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )


class EnrichedPriceSensor(BaseEDSensor):
    _attr_name = "Enriched Power Price"
    _attr_native_unit_of_measurement = "SEK/kWh"
    _attr_icon = "mdi:currency-usd"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_enriched_price_{self._entry_id}"

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data.get("current_enriched")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        hourly = self.coordinator.data.get("hourly_prices") or []
        out = [
            {
                "time": p.time.isoformat(),
                "spot": p.spot_sek_per_kwh,
                "enriched": p.enriched_sek_per_kwh,
            }
            for p in hourly
        ]
        return {"hourly": out}


class BatteryRuntimeSensor(BaseEDSensor):
    _attr_name = "Battery Runtime Estimate"
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:clock-outline"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_battery_runtime_{self._entry_id}"

    @property
    def native_value(self) -> Optional[float]:
        return self.coordinator.data.get("battery_runtime_h")


class BatteryCostSensor(BaseEDSensor):
    _attr_name = "Battery Energy Cost"
    _attr_native_unit_of_measurement = "SEK/kWh"
    _attr_icon = "mdi:battery-heart-variant"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_battery_cost_{self._entry_id}"

    @property
    def native_value(self) -> float:
        store = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        return float(store.get("wace", 0.0))


class SolarPowerNowSensor(BaseEDSensor):
    _attr_name = "Solar Power Forecast Now"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_now_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_now_w")

    @property
    def extra_state_attributes(self):
        pts = self.coordinator.data.get("solar_points") or []
        return {"points": [{"time": p.time.isoformat(), "watts": p.watts} for p in pts[:96]]}


class SolarEnergyTodaySensor(BaseEDSensor):
    _attr_name = "Solar Energy Forecast Today"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_today_kwh_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_today_kwh")


class SolarEnergyTomorrowSensor(BaseEDSensor):
    _attr_name = "Solar Energy Forecast Tomorrow"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_solar_tomorrow_kwh_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("solar_tomorrow_kwh")


class PVPowerNowSensor(BaseEDSensor):
    _attr_name = "Solar Production Now"
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "power"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_pv_now_w_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("pv_now_w")


class PVEnergyTodaySensor(BaseEDSensor):
    _attr_name = "Solar Production Today"
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:solar-power"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_pv_today_kwh_{self._entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data.get("pv_today_kwh")
