from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .forecast_provider import ForecastSolarProvider

async def async_setup_entry(hass, entry, async_add_entities):
    config = entry.data
    forecast_provider = ForecastSolarProvider(
        hass=hass,
        lat=config["fs_lat"],
        lon=config["fs_lon"],
        planes_json=config["fs_planes"],
        apikey=config.get("fs_apikey"),
        horizon_csv=config.get("fs_horizon"),
        weather_entity=config.get("weather_entity"),
        cloud_0_factor=config.get("cloud_0_factor", 250),
        cloud_100_factor=config.get("cloud_100_factor", 20),
    )
    async_add_entities([
        SolarForecastRawSensor(hass, forecast_provider),
        SolarForecastCompensatedSensor(hass, forecast_provider),
    ])

class SolarForecastRawSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_raw"

    def __init__(self, hass: HomeAssistant, forecast_provider: ForecastSolarProvider):
        self.hass = hass
        self._forecast_provider = forecast_provider
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )
        self._state = None
        self._attr_extra_state_attributes = {}

    @property
    def name(self):
        return "Solar Forecast (Raw)"

    async def async_update(self):
        raw, _ = await self._forecast_provider.async_fetch_watts()
        self._state = sum(point.watts for point in raw)
        self._attr_extra_state_attributes = {
            "forecast": [(point.time.isoformat(), point.watts) for point in raw]
        }

class SolarForecastCompensatedSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_compensated"

    def __init__(self, hass: HomeAssistant, forecast_provider: ForecastSolarProvider):
        self.hass = hass
        self._forecast_provider = forecast_provider
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "energy_dispatcher")},
            name="Energy Dispatcher",
            manufacturer="Bokbacken",
        )
        self._state = None
        self._attr_extra_state_attributes = {}

    @property
    def name(self):
        return "Solar Forecast (Cloud Compensated)"

    async def async_update(self):
        _, compensated = await self._forecast_provider.async_fetch_watts()
        self._state = sum(point.watts for point in compensated)
        self._attr_extra_state_attributes = {
            "forecast": [(point.time.isoformat(), point.watts) for point in compensated]
        }