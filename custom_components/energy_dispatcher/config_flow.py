"""
Energy Dispatcher - config_flow.py
Multilingual config flow with translation keys for labels and descriptions.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_PRICE_TAX,
    CONF_PRICE_TRANSFER,
    CONF_PRICE_SURCHARGE,
    CONF_PRICE_VAT,
    CONF_PRICE_FIXED_MONTHLY,
    CONF_PRICE_INCLUDE_FIXED,
    CONF_BATT_CAP_KWH,
    CONF_BATT_SOC_ENTITY,
    CONF_BATT_MAX_CHARGE_W,
    CONF_BATT_MAX_DISCH_W,
    CONF_BATT_ADAPTER,
    CONF_HUAWEI_DEVICE_ID,
    CONF_EV_MODE,
    CONF_EV_TARGET_SOC,
    CONF_EV_CURRENT_SOC,
    CONF_EV_BATT_KWH,
    CONF_EVSE_START_SWITCH,
    CONF_EVSE_STOP_SWITCH,
    CONF_EVSE_CURRENT_NUMBER,
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    CONF_EVSE_POWER_SENSOR,
    CONF_EVSE_ENERGY_SENSOR,
    CONF_EVSE_TOTAL_ENERGY_SENSOR,
    CONF_HOUSE_CONS_SENSOR,
    CONF_FS_USE,
    CONF_FS_APIKEY,
    CONF_FS_LAT,
    CONF_FS_LON,
    CONF_FS_PLANES,
    CONF_FS_HORIZON,
    CONF_PV_POWER_ENTITY,
    CONF_PV_ENERGY_TODAY_ENTITY,
    CONF_RUNTIME_SOURCE,
    CONF_RUNTIME_COUNTER_ENTITY,
    CONF_RUNTIME_POWER_ENTITY,
    CONF_RUNTIME_ALPHA,
    CONF_RUNTIME_WINDOW_MIN,
    CONF_RUNTIME_EXCLUDE_EV,
    CONF_RUNTIME_EXCLUDE_BATT_GRID,
    CONF_RUNTIME_SOC_FLOOR,
    CONF_RUNTIME_SOC_CEILING,
    CONF_LOAD_POWER_ENTITY,
    CONF_BATT_POWER_ENTITY,
    CONF_GRID_IMPORT_TODAY_ENTITY,
)

# New additions for weather/cloud compensation
CONF_WEATHER_ENTITY = "weather_entity"
CONF_CLOUD_0 = "cloud_0_factor"
CONF_CLOUD_100 = "cloud_100_factor"

def _available_weather_entities(hass):
    entities = []
    for state in getattr(hass, "states", []).async_all("weather") if hass else []:
        attrs = state.attributes
        if (
            "cloudiness" in attrs
            or "cloud_coverage" in attrs
            or "cloud_cover" in attrs
            or "cloud" in attrs
        ):
            entities.append(state.entity_id)
    return entities

DEFAULTS = {
    CONF_PRICE_VAT: 0.25,
    CONF_PRICE_TAX: 0.0,
    CONF_PRICE_TRANSFER: 0.0,
    CONF_PRICE_SURCHARGE: 0.0,
    CONF_PRICE_FIXED_MONTHLY: 0.0,
    CONF_PRICE_INCLUDE_FIXED: False,
    CONF_BATT_CAP_KWH: 15.0,
    CONF_BATT_MAX_CHARGE_W: 4000,
    CONF_BATT_MAX_DISCH_W: 4000,
    CONF_BATT_ADAPTER: "huawei",
    CONF_EV_MODE: "manual",
    CONF_EV_TARGET_SOC: 80.0,
    CONF_EV_CURRENT_SOC: 40.0,
    CONF_EV_BATT_KWH: 75.0,
    CONF_EVSE_MIN_A: 6,
    CONF_EVSE_MAX_A: 16,
    CONF_EVSE_PHASES: 3,
    CONF_EVSE_VOLTAGE: 230,
    CONF_EVSE_POWER_SENSOR: "",
    CONF_EVSE_ENERGY_SENSOR: "",
    CONF_EVSE_TOTAL_ENERGY_SENSOR: "",
    CONF_FS_USE: True,
    CONF_PV_POWER_ENTITY: "",
    CONF_PV_ENERGY_TODAY_ENTITY: "",
    CONF_RUNTIME_SOURCE: "counter_kwh",
    CONF_RUNTIME_COUNTER_ENTITY: "",
    CONF_RUNTIME_POWER_ENTITY: "",
    CONF_RUNTIME_ALPHA: 0.2,
    CONF_RUNTIME_WINDOW_MIN: 15,
    CONF_RUNTIME_EXCLUDE_EV: True,
    CONF_RUNTIME_EXCLUDE_BATT_GRID: True,
    CONF_RUNTIME_SOC_FLOOR: 10,
    CONF_RUNTIME_SOC_CEILING: 95,
    CONF_LOAD_POWER_ENTITY: "",
    CONF_BATT_POWER_ENTITY: "",
    CONF_GRID_IMPORT_TODAY_ENTITY: "",
    CONF_WEATHER_ENTITY: "",
    CONF_CLOUD_0: 250,
    CONF_CLOUD_100: 20,
}

def _schema_user(defaults: dict | None = None, hass=None) -> vol.Schema:
    d = defaults or DEFAULTS
    weather_entities = _available_weather_entities(hass) if hass else []
    weather_select = vol.In(weather_entities) if weather_entities else str

    return vol.Schema(
        {
            vol.Required(CONF_NORDPOOL_ENTITY, default=d.get(CONF_NORDPOOL_ENTITY, "")): str,
            vol.Optional(CONF_PRICE_TAX, default=d.get(CONF_PRICE_TAX, 0.0)): vol.Coerce(float),
            vol.Optional(CONF_PRICE_TRANSFER, default=d.get(CONF_PRICE_TRANSFER, 0.0)): vol.Coerce(float),
            vol.Optional(CONF_PRICE_SURCHARGE, default=d.get(CONF_PRICE_SURCHARGE, 0.0)): vol.Coerce(float),
            vol.Optional(CONF_PRICE_VAT, default=d.get(CONF_PRICE_VAT, 0.25)): vol.Coerce(float),
            vol.Optional(CONF_PRICE_FIXED_MONTHLY, default=d.get(CONF_PRICE_FIXED_MONTHLY, 0.0)): vol.Coerce(float),
            vol.Optional(CONF_PRICE_INCLUDE_FIXED, default=d.get(CONF_PRICE_INCLUDE_FIXED, False)): bool,

            vol.Required(CONF_BATT_CAP_KWH, default=d.get(CONF_BATT_CAP_KWH, 15.0)): vol.Coerce(float),
            vol.Required(CONF_BATT_SOC_ENTITY, default=d.get(CONF_BATT_SOC_ENTITY, "")): str,
            vol.Optional(CONF_BATT_MAX_CHARGE_W, default=d.get(CONF_BATT_MAX_CHARGE_W, 4000)): vol.Coerce(int),
            vol.Optional(CONF_BATT_MAX_DISCH_W, default=d.get(CONF_BATT_MAX_DISCH_W, 4000)): vol.Coerce(int),
            vol.Optional(CONF_BATT_ADAPTER, default=d.get(CONF_BATT_ADAPTER, "huawei")): vol.In(["huawei"]),
            vol.Optional(CONF_HUAWEI_DEVICE_ID, default=d.get(CONF_HUAWEI_DEVICE_ID, "")): str,

            vol.Optional(CONF_EV_MODE, default=d.get(CONF_EV_MODE, "manual")): vol.In(["manual"]),
            vol.Optional(CONF_EV_BATT_KWH, default=d.get(CONF_EV_BATT_KWH, 75.0)): vol.Coerce(float),
            vol.Optional(CONF_EV_CURRENT_SOC, default=d.get(CONF_EV_CURRENT_SOC, 40.0)): vol.Coerce(float),
            vol.Optional(CONF_EV_TARGET_SOC, default=d.get(CONF_EV_TARGET_SOC, 80.0)): vol.Coerce(float),
            vol.Optional(CONF_EVSE_START_SWITCH, default=d.get(CONF_EVSE_START_SWITCH, "")): str,
            vol.Optional(CONF_EVSE_STOP_SWITCH, default=d.get(CONF_EVSE_STOP_SWITCH, "")): str,
            vol.Optional(CONF_EVSE_CURRENT_NUMBER, default=d.get(CONF_EVSE_CURRENT_NUMBER, "")): str,
            vol.Optional(CONF_EVSE_MIN_A, default=d.get(CONF_EVSE_MIN_A, 6)): vol.Coerce(int),
            vol.Optional(CONF_EVSE_MAX_A, default=d.get(CONF_EVSE_MAX_A, 16)): vol.Coerce(int),
            vol.Optional(CONF_EVSE_PHASES, default=d.get(CONF_EVSE_PHASES, 3)): vol.Coerce(int),
            vol.Optional(CONF_EVSE_VOLTAGE, default=d.get(CONF_EVSE_VOLTAGE, 230)): vol.Coerce(int),
            vol.Optional(CONF_EVSE_POWER_SENSOR, default=d.get(CONF_EVSE_POWER_SENSOR, "")): str,
            vol.Optional(CONF_EVSE_ENERGY_SENSOR, default=d.get(CONF_EVSE_ENERGY_SENSOR, "")): str,
            vol.Optional(CONF_EVSE_TOTAL_ENERGY_SENSOR, default=d.get(CONF_EVSE_TOTAL_ENERGY_SENSOR, "")): str,

            vol.Optional(CONF_FS_USE, default=d.get(CONF_FS_USE, True)): bool,
            vol.Optional(CONF_FS_APIKEY, default=d.get(CONF_FS_APIKEY, "")): str,
            vol.Optional(CONF_FS_LAT, default=d.get(CONF_FS_LAT, 56.6967208731)): vol.Coerce(float),
            vol.Optional(CONF_FS_LON, default=d.get(CONF_FS_LON, 13.0196173488)): vol.Coerce(float),
            vol.Optional(CONF_FS_PLANES, default=d.get(CONF_FS_PLANES, '[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]')): str,
            vol.Optional(CONF_FS_HORIZON, default=d.get(CONF_FS_HORIZON, "18,16,11,7,5,4,3,2,2,4,7,10")): str,

            vol.Optional(CONF_WEATHER_ENTITY, default=d.get(CONF_WEATHER_ENTITY, "")): weather_select,
            vol.Optional(CONF_CLOUD_0, default=d.get(CONF_CLOUD_0, 250)): vol.All(vol.Coerce(int), vol.Range(min=0, max=500)),
            vol.Optional(CONF_CLOUD_100, default=d.get(CONF_CLOUD_100, 20)): vol.All(vol.Coerce(int), vol.Range(min=0, max=500)),

            vol.Optional(CONF_PV_POWER_ENTITY, default=d.get(CONF_PV_POWER_ENTITY, "")): str,
            vol.Optional(CONF_PV_ENERGY_TODAY_ENTITY, default=d.get(CONF_PV_ENERGY_TODAY_ENTITY, "")): str,

            vol.Optional(CONF_HOUSE_CONS_SENSOR, default=d.get(CONF_HOUSE_CONS_SENSOR, "")): str,
            vol.Optional(CONF_RUNTIME_SOURCE, default=d.get(CONF_RUNTIME_SOURCE, "counter_kwh")): vol.In(["counter_kwh", "power_w", "manual_dayparts"]),
            vol.Optional(CONF_RUNTIME_COUNTER_ENTITY, default=d.get(CONF_RUNTIME_COUNTER_ENTITY, "")): str,
            vol.Optional(CONF_RUNTIME_POWER_ENTITY, default=d.get(CONF_RUNTIME_POWER_ENTITY, "")): str,
            vol.Optional(CONF_LOAD_POWER_ENTITY, default=d.get(CONF_LOAD_POWER_ENTITY, "")): str,
            vol.Optional(CONF_BATT_POWER_ENTITY, default=d.get(CONF_BATT_POWER_ENTITY, "")): str,
            vol.Optional(CONF_GRID_IMPORT_TODAY_ENTITY, default=d.get(CONF_GRID_IMPORT_TODAY_ENTITY, "")): str,
            vol.Optional(CONF_RUNTIME_ALPHA, default=d.get(CONF_RUNTIME_ALPHA, 0.2)): vol.Coerce(float),
            vol.Optional(CONF_RUNTIME_WINDOW_MIN, default=d.get(CONF_RUNTIME_WINDOW_MIN, 15)): vol.Coerce(int),
            vol.Optional(CONF_RUNTIME_EXCLUDE_EV, default=d.get(CONF_RUNTIME_EXCLUDE_EV, True)): bool,
            vol.Optional(CONF_RUNTIME_EXCLUDE_BATT_GRID, default=d.get(CONF_RUNTIME_EXCLUDE_BATT_GRID, True)): bool,
            vol.Optional(CONF_RUNTIME_SOC_FLOOR, default=d.get(CONF_RUNTIME_SOC_FLOOR, 10)): vol.Coerce(float),
            vol.Optional(CONF_RUNTIME_SOC_CEILING, default=d.get(CONF_RUNTIME_SOC_CEILING, 95)): vol.Coerce(float),
        }
    )

# Translation key structure for Home Assistant config flows:
# "component.energy_dispatcher.config.<field>.label"
# "component.energy_dispatcher.config.<field>.description"

class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        hass = getattr(self, "hass", None)

        if user_input is not None:
            try:
                float(user_input.get(CONF_FS_LAT, 0))
                float(user_input.get(CONF_FS_LON, 0))
            except Exception:  # noqa: BLE001
                errors["base"] = "invalid_latlon"

            if not errors:
                return self.async_create_entry(title="Energy Dispatcher", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema_user(hass=hass),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EnergyDispatcherOptionsFlowHandler(config_entry)

class EnergyDispatcherOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = {**self.config_entry.data, **(self.config_entry.options or {})}
        schema = _schema_user(current, hass=self.hass)
        return self.async_show_form(step_id="init", data_schema=schema)