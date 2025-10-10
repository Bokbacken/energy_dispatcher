"""
Energy Dispatcher - config_flow.py
Multilingual config flow with translation keys for labels and descriptions.
"""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY,
    CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY,
    CONF_BATT_CAPACITY_ENTITY,
    CONF_BATT_POWER_INVERT_SIGN,
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
    CONF_PV_TOTAL_ENERGY_ENTITY,
    CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY,
    CONF_RUNTIME_COUNTER_ENTITY,
    CONF_RUNTIME_EXCLUDE_EV,
    CONF_RUNTIME_EXCLUDE_BATT_GRID,
    CONF_RUNTIME_SOC_FLOOR,
    CONF_RUNTIME_SOC_CEILING,
    CONF_RUNTIME_LOOKBACK_HOURS,
    CONF_RUNTIME_USE_DAYPARTS,
    CONF_GRID_IMPORT_TODAY_ENTITY,
    CONF_AUTO_CREATE_DASHBOARD,
)

# Forecast source and weather/cloud compensation
CONF_FORECAST_SOURCE = "forecast_source"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_CLOUD_0 = "cloud_0_factor"
CONF_CLOUD_100 = "cloud_100_factor"

# Manual forecast settings
CONF_MANUAL_STEP_MINUTES = "manual_step_minutes"
CONF_MANUAL_DIFFUSE_SKY_VIEW_FACTOR = "manual_diffuse_sky_view_factor"
CONF_MANUAL_TEMP_COEFF = "manual_temp_coeff_pct_per_c"
CONF_MANUAL_INVERTER_AC_CAP = "manual_inverter_ac_kw_cap"
CONF_MANUAL_CALIBRATION_ENABLED = "manual_calibration_enabled"

def _available_weather_entities(hass):
    entities = []
    if hass and hasattr(hass, "states"):
        try:
            for state in hass.states.async_all("weather"):
                attrs = state.attributes
                if (
                    "cloudiness" in attrs
                    or "cloud_coverage" in attrs
                    or "cloud_cover" in attrs
                    or "cloud" in attrs
                ):
                    entities.append(state.entity_id)
        except (AttributeError, TypeError):
            # Handle cases where:
            # - hass.states is None
            # - hass.states.async_all doesn't exist
            # - hass.states.async_all raises an error
            pass
    return entities

DEFAULTS = {
    CONF_PRICE_VAT: 0.25,
    CONF_PRICE_TAX: 0.0,
    CONF_PRICE_TRANSFER: 0.0,
    CONF_PRICE_SURCHARGE: 0.0,
    CONF_PRICE_FIXED_MONTHLY: 0.0,
    CONF_PRICE_INCLUDE_FIXED: False,
    CONF_BATT_CAP_KWH: 15.0,
    CONF_BATT_CAPACITY_ENTITY: "",
    CONF_BATT_MAX_CHARGE_W: 4000,
    CONF_BATT_MAX_DISCH_W: 4000,
    CONF_BATT_ADAPTER: "huawei",
    CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY: "",
    CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY: "",
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
    CONF_PV_TOTAL_ENERGY_ENTITY: "",
    CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY: "",
    CONF_RUNTIME_COUNTER_ENTITY: "",
    CONF_RUNTIME_EXCLUDE_EV: True,
    CONF_RUNTIME_EXCLUDE_BATT_GRID: True,
    CONF_RUNTIME_SOC_FLOOR: 10,
    CONF_RUNTIME_SOC_CEILING: 95,
    CONF_RUNTIME_LOOKBACK_HOURS: 48,
    CONF_RUNTIME_USE_DAYPARTS: True,
    CONF_GRID_IMPORT_TODAY_ENTITY: "",
    CONF_FORECAST_SOURCE: "forecast_solar",
    CONF_WEATHER_ENTITY: "",
    CONF_CLOUD_0: 250,
    CONF_CLOUD_100: 20,
    CONF_MANUAL_STEP_MINUTES: 15,
    CONF_MANUAL_DIFFUSE_SKY_VIEW_FACTOR: 0.95,
    CONF_MANUAL_TEMP_COEFF: -0.38,
    CONF_MANUAL_INVERTER_AC_CAP: None,
    CONF_MANUAL_CALIBRATION_ENABLED: False,
    CONF_AUTO_CREATE_DASHBOARD: True,
}

def _schema_user(defaults: dict | None = None, hass=None) -> vol.Schema:
    d = defaults or DEFAULTS
    weather_entities = _available_weather_entities(hass) if hass else []
    weather_select = vol.In(weather_entities) if weather_entities else str

    # Build schema with all fields visible regardless of forecast source selection
    schema_dict = {
        vol.Required(CONF_NORDPOOL_ENTITY, default=d.get(CONF_NORDPOOL_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_PRICE_TAX, default=d.get(CONF_PRICE_TAX, 0.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PRICE_TRANSFER, default=d.get(CONF_PRICE_TRANSFER, 0.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PRICE_SURCHARGE, default=d.get(CONF_PRICE_SURCHARGE, 0.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PRICE_VAT, default=d.get(CONF_PRICE_VAT, 0.25)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=1, step=0.01, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PRICE_FIXED_MONTHLY, default=d.get(CONF_PRICE_FIXED_MONTHLY, 0.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=1000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PRICE_INCLUDE_FIXED, default=d.get(CONF_PRICE_INCLUDE_FIXED, False)): selector.BooleanSelector(),

        vol.Required(CONF_BATT_CAP_KWH, default=d.get(CONF_BATT_CAP_KWH, 15.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=100, step=0.5, unit_of_measurement="kWh", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_BATT_CAPACITY_ENTITY, default=d.get(CONF_BATT_CAPACITY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_BATT_SOC_ENTITY, default=d.get(CONF_BATT_SOC_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_BATT_MAX_CHARGE_W, default=d.get(CONF_BATT_MAX_CHARGE_W, 4000)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=100, max=20000, step=100, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_BATT_MAX_DISCH_W, default=d.get(CONF_BATT_MAX_DISCH_W, 4000)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=100, max=20000, step=100, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_BATT_ADAPTER, default=d.get(CONF_BATT_ADAPTER, "huawei")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["huawei"], mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_HUAWEI_DEVICE_ID, default=d.get(CONF_HUAWEI_DEVICE_ID, "")): selector.TextSelector(),
        vol.Optional(CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY, default=d.get(CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY, default=d.get(CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),

        vol.Optional(CONF_EV_MODE, default=d.get(CONF_EV_MODE, "manual")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["manual"], mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_EV_BATT_KWH, default=d.get(CONF_EV_BATT_KWH, 75.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=10, max=200, step=0.5, unit_of_measurement="kWh", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EV_CURRENT_SOC, default=d.get(CONF_EV_CURRENT_SOC, 40.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EV_TARGET_SOC, default=d.get(CONF_EV_TARGET_SOC, 80.0)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EVSE_START_SWITCH, default=d.get(CONF_EVSE_START_SWITCH, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="switch")
        ),
        vol.Optional(CONF_EVSE_STOP_SWITCH, default=d.get(CONF_EVSE_STOP_SWITCH, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="switch")
        ),
        vol.Optional(CONF_EVSE_CURRENT_NUMBER, default=d.get(CONF_EVSE_CURRENT_NUMBER, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="number")
        ),
        vol.Optional(CONF_EVSE_MIN_A, default=d.get(CONF_EVSE_MIN_A, 6)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=6, max=32, step=1, unit_of_measurement="A", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EVSE_MAX_A, default=d.get(CONF_EVSE_MAX_A, 16)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=6, max=32, step=1, unit_of_measurement="A", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EVSE_PHASES, default=d.get(CONF_EVSE_PHASES, 3)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=3, step=2, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EVSE_VOLTAGE, default=d.get(CONF_EVSE_VOLTAGE, 230)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=110, max=240, step=1, unit_of_measurement="V", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_EVSE_POWER_SENSOR, default=d.get(CONF_EVSE_POWER_SENSOR, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_EVSE_ENERGY_SENSOR, default=d.get(CONF_EVSE_ENERGY_SENSOR, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_EVSE_TOTAL_ENERGY_SENSOR, default=d.get(CONF_EVSE_TOTAL_ENERGY_SENSOR, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),

        # Solar forecasting fields - all visible regardless of source selection
        vol.Optional(CONF_FS_USE, default=d.get(CONF_FS_USE, True)): selector.BooleanSelector(),
        vol.Optional(CONF_FORECAST_SOURCE, default=d.get(CONF_FORECAST_SOURCE, "forecast_solar")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["forecast_solar", "manual_physics"], mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_FS_LAT, default=d.get(CONF_FS_LAT, 56.6967208731)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-90, max=90, step=0.0001, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_FS_LON, default=d.get(CONF_FS_LON, 13.0196173488)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-180, max=180, step=0.0001, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_FS_PLANES, default=d.get(CONF_FS_PLANES, '[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]')): selector.TextSelector(
            selector.TextSelectorConfig(multiline=True)
        ),
        vol.Optional(CONF_FS_HORIZON, default=d.get(CONF_FS_HORIZON, "18,16,11,7,5,4,3,2,2,4,7,10")): selector.TextSelector(),
        
        # Forecast.solar specific fields (always visible)
        vol.Optional(CONF_FS_APIKEY, default=d.get(CONF_FS_APIKEY, "")): selector.TextSelector(),
        vol.Optional(CONF_WEATHER_ENTITY, default=d.get(CONF_WEATHER_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="weather")
        ),
        vol.Optional(CONF_CLOUD_0, default=d.get(CONF_CLOUD_0, 250)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=500, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_CLOUD_100, default=d.get(CONF_CLOUD_100, 20)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=500, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        
        # Manual physics specific fields (always visible)
        vol.Optional(CONF_MANUAL_STEP_MINUTES, default=d.get(CONF_MANUAL_STEP_MINUTES, 15)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=15, max=60, step=15, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_MANUAL_DIFFUSE_SKY_VIEW_FACTOR, default=d.get(CONF_MANUAL_DIFFUSE_SKY_VIEW_FACTOR, 0.95)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.7, max=1.0, step=0.01, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_MANUAL_TEMP_COEFF, default=d.get(CONF_MANUAL_TEMP_COEFF, -0.38)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-1.0, max=0.0, step=0.01, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_MANUAL_INVERTER_AC_CAP, default=d.get(CONF_MANUAL_INVERTER_AC_CAP, None)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=100, step=0.1, unit_of_measurement="kW", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_MANUAL_CALIBRATION_ENABLED, default=d.get(CONF_MANUAL_CALIBRATION_ENABLED, False)): selector.BooleanSelector(),

        vol.Optional(CONF_PV_POWER_ENTITY, default=d.get(CONF_PV_POWER_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_PV_ENERGY_TODAY_ENTITY, default=d.get(CONF_PV_ENERGY_TODAY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_PV_TOTAL_ENERGY_ENTITY, default=d.get(CONF_PV_TOTAL_ENERGY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),

        vol.Optional(CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY, default=d.get(CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        
        vol.Optional(CONF_RUNTIME_COUNTER_ENTITY, default=d.get(CONF_RUNTIME_COUNTER_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_GRID_IMPORT_TODAY_ENTITY, default=d.get(CONF_GRID_IMPORT_TODAY_ENTITY, "")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_RUNTIME_LOOKBACK_HOURS, default=d.get(CONF_RUNTIME_LOOKBACK_HOURS, 48)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=12, max=168, step=1, unit_of_measurement="hours", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_RUNTIME_USE_DAYPARTS, default=d.get(CONF_RUNTIME_USE_DAYPARTS, True)): selector.BooleanSelector(),
        vol.Optional(CONF_RUNTIME_EXCLUDE_EV, default=d.get(CONF_RUNTIME_EXCLUDE_EV, True)): selector.BooleanSelector(),
        vol.Optional(CONF_RUNTIME_EXCLUDE_BATT_GRID, default=d.get(CONF_RUNTIME_EXCLUDE_BATT_GRID, True)): selector.BooleanSelector(),
        vol.Optional(CONF_RUNTIME_SOC_FLOOR, default=d.get(CONF_RUNTIME_SOC_FLOOR, 10)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_RUNTIME_SOC_CEILING, default=d.get(CONF_RUNTIME_SOC_CEILING, 95)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
        
        vol.Optional(CONF_AUTO_CREATE_DASHBOARD, default=d.get(CONF_AUTO_CREATE_DASHBOARD, True)): selector.BooleanSelector(),
    }

    return vol.Schema(schema_dict)

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

        # If there are errors or first time, use user_input if available to rebuild schema
        # This ensures the form shows the correct fields based on user's current selections
        defaults = user_input if user_input is not None else None
        return self.async_show_form(
            step_id="user",
            data_schema=_schema_user(defaults=defaults, hass=hass),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EnergyDispatcherOptionsFlowHandler()

class EnergyDispatcherOptionsFlowHandler(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            # Validate input
            try:
                float(user_input.get(CONF_FS_LAT, 0))
                float(user_input.get(CONF_FS_LON, 0))
            except Exception:  # noqa: BLE001
                errors["base"] = "invalid_latlon"
            
            if not errors:
                return self.async_create_entry(title="", data=user_input)
        
        # Use user_input if validation failed, otherwise use current config
        # This ensures the form shows the correct fields based on user's current selections
        if user_input is not None:
            defaults = user_input
        else:
            defaults = {**self.config_entry.data, **(self.config_entry.options or {})}
        
        schema = _schema_user(defaults, hass=self.hass)
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)