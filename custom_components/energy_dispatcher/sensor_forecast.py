from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

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
        forecast_source=config.get("forecast_source", "forecast_solar"),
        manual_step_minutes=config.get("manual_step_minutes", 15),
        manual_diffuse_svf=config.get("manual_diffuse_sky_view_factor"),
        manual_temp_coeff=config.get("manual_temp_coeff_pct_per_c", -0.38),
        manual_inverter_ac_cap=config.get("manual_inverter_ac_kw_cap"),
        manual_calibration_enabled=config.get("manual_calibration_enabled", False),
    )
    
    entities = [
        SolarForecastRawSensor(hass, forecast_provider),
        SolarForecastCompensatedSensor(hass, forecast_provider),
    ]
    
    # Add weather capability sensor if manual physics is enabled
    if config.get("forecast_source") == "manual_physics":
        entities.append(WeatherCapabilitySensor(hass, forecast_provider))
    
    async_add_entities(entities)

class SolarForecastRawSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_raw"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"
    _attr_icon = "mdi:solar-power"

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

    @property
    def state(self):
        return self._state
    
    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        raw, _ = await self._forecast_provider.async_fetch_watts()
        
        # Calculate today's total energy in kWh using trapezoidal integration
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        
        today_points = [p for p in raw if today_start <= p.time < tomorrow_start]
        
        # Trapezoidal integration: sum of (watts[i] + watts[i+1]) / 2 * hours
        total_wh = 0.0
        for i in range(len(today_points) - 1):
            p1, p2 = today_points[i], today_points[i + 1]
            hours = (p2.time - p1.time).total_seconds() / 3600.0
            avg_watts = (p1.watts + p2.watts) / 2.0
            total_wh += avg_watts * hours
        
        self._state = round(total_wh / 1000.0, 2) if total_wh > 0 else 0.0
        
        self._attr_extra_state_attributes = {
            "forecast": [(point.time.isoformat(), point.watts) for point in raw]
        }

class SolarForecastCompensatedSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_compensated"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "measurement"
    _attr_icon = "mdi:solar-power"

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

    @property
    def state(self):
        return self._state
    
    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        _, compensated = await self._forecast_provider.async_fetch_watts()
        
        # Calculate today's total energy in kWh using trapezoidal integration
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        
        today_points = [p for p in compensated if today_start <= p.time < tomorrow_start]
        
        # Trapezoidal integration: sum of (watts[i] + watts[i+1]) / 2 * hours
        total_wh = 0.0
        for i in range(len(today_points) - 1):
            p1, p2 = today_points[i], today_points[i + 1]
            hours = (p2.time - p1.time).total_seconds() / 3600.0
            avg_watts = (p1.watts + p2.watts) / 2.0
            total_wh += avg_watts * hours
        
        self._state = round(total_wh / 1000.0, 2) if total_wh > 0 else 0.0
        
        # Get cloudiness from weather entity for debugging
        cloudiness = None
        weather_entity = self._forecast_provider.weather_entity
        if weather_entity:
            state = self.hass.states.get(weather_entity)
            if state:
                attrs = state.attributes
                for key in ["cloudiness", "cloud_coverage", "cloud_cover", "cloud"]:
                    if key in attrs:
                        try:
                            cloudiness = float(attrs[key])
                            break
                        except (ValueError, TypeError):
                            continue
        
        self._attr_extra_state_attributes = {
            "forecast": [(point.time.isoformat(), point.watts) for point in compensated],
            "cloud_coverage": cloudiness,
            "weather_entity": weather_entity if weather_entity else None
        }


class WeatherCapabilitySensor(SensorEntity):
    """Sensor showing detected weather capabilities for manual forecast."""
    
    _attr_has_entity_name = True
    _attr_unique_id = "solar_forecast_weather_capabilities"
    _attr_icon = "mdi:weather-partly-cloudy"
    
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
        return "Weather Forecast Capabilities"
    
    @property
    def state(self):
        return self._state
    
    @property
    def native_value(self):
        return self._state
    
    async def async_update(self):
        """Update weather capabilities."""
        if self._forecast_provider.manual_engine:
            caps = self._forecast_provider.manual_engine.weather_caps
            self._state = caps.get_description()
            
            # Detailed attributes
            self._attr_extra_state_attributes = {
                "tier": caps.get_tier(),
                "has_dni": caps.has_dni,
                "has_dhi": caps.has_dhi,
                "has_ghi": caps.has_ghi,
                "has_shortwave_radiation": caps.has_shortwave_radiation,
                "has_cloud_cover": caps.has_cloud_cover,
                "has_temperature": caps.has_temperature,
                "has_wind_speed": caps.has_wind_speed,
                "has_relative_humidity": caps.has_relative_humidity,
                "has_pressure": caps.has_pressure,
                "weather_entity": self._forecast_provider.weather_entity,
            }
        else:
            self._state = "Manual forecast not enabled"
            self._attr_extra_state_attributes = {}