"""
Energy Dispatcher - config_flow.py
Konfigflöde (en-steg) + OptionsFlow med dynamiska defaults (kommer ihåg dina val).
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
    CONF_HOUSE_CONS_SENSOR,
    CONF_FS_USE,
    CONF_FS_APIKEY,
    CONF_FS_LAT,
    CONF_FS_LON,
    CONF_FS_PLANES,
    CONF_FS_HORIZON,
    CONF_PV_POWER_ENTITY,
    CONF_PV_ENERGY_TODAY_ENTITY,
    # Baseline
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
    CONF_FS_USE: True,
    CONF_PV_POWER_ENTITY: "",
    CONF_PV_ENERGY_TODAY_ENTITY: "",
    # Baseline defaults
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
}


def _schema_user(defaults: dict | None = None) -> vol.Schema:
    d = defaults or DEFAULTS
    return vol.Schema(
        {
            # Price configuration
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
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_PRICE_INCLUDE_FIXED, default=d.get(CONF_PRICE_INCLUDE_FIXED, False)): selector.BooleanSelector(),

            # Battery configuration
            vol.Required(CONF_BATT_CAP_KWH, default=d.get(CONF_BATT_CAP_KWH, 15.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, step=0.5, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_BATT_SOC_ENTITY, default=d.get(CONF_BATT_SOC_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_BATT_MAX_CHARGE_W, default=d.get(CONF_BATT_MAX_CHARGE_W, 4000)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=100, max=50000, step=100, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_BATT_MAX_DISCH_W, default=d.get(CONF_BATT_MAX_DISCH_W, 4000)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=100, max=50000, step=100, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_BATT_ADAPTER, default=d.get(CONF_BATT_ADAPTER, "huawei")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["huawei"], mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_HUAWEI_DEVICE_ID, default=d.get(CONF_HUAWEI_DEVICE_ID, "")): selector.TextSelector(),

            # Legacy house consumption sensor
            vol.Optional(CONF_HOUSE_CONS_SENSOR, default=d.get(CONF_HOUSE_CONS_SENSOR, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),

            # EV/EVSE configuration
            vol.Optional(CONF_EV_MODE, default=d.get(CONF_EV_MODE, "manual")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["manual"], mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_EV_BATT_KWH, default=d.get(CONF_EV_BATT_KWH, 75.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_EV_CURRENT_SOC, default=d.get(CONF_EV_CURRENT_SOC, 40.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_EV_TARGET_SOC, default=d.get(CONF_EV_TARGET_SOC, 80.0)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
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
                selector.NumberSelectorConfig(min=6, max=32, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_EVSE_MAX_A, default=d.get(CONF_EVSE_MAX_A, 16)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=6, max=32, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_EVSE_PHASES, default=d.get(CONF_EVSE_PHASES, 3)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=3, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_EVSE_VOLTAGE, default=d.get(CONF_EVSE_VOLTAGE, 230)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=180, max=250, step=1, mode=selector.NumberSelectorMode.BOX)
            ),

            # Forecast.Solar configuration
            vol.Optional(CONF_FS_USE, default=d.get(CONF_FS_USE, True)): selector.BooleanSelector(),
            vol.Optional(CONF_FS_APIKEY, default=d.get(CONF_FS_APIKEY, "")): selector.TextSelector(),
            vol.Optional(CONF_FS_LAT, default=d.get(CONF_FS_LAT, 56.6967208731)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-90, max=90, step=0.000001, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_FS_LON, default=d.get(CONF_FS_LON, 13.0196173488)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-180, max=180, step=0.000001, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_FS_PLANES, default=d.get(CONF_FS_PLANES, '[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]')): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            vol.Optional(CONF_FS_HORIZON, default=d.get(CONF_FS_HORIZON, "18,16,11,7,5,4,3,2,2,4,7,10")): selector.TextSelector(),

            # PV actual sensors
            vol.Optional(CONF_PV_POWER_ENTITY, default=d.get(CONF_PV_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_PV_ENERGY_TODAY_ENTITY, default=d.get(CONF_PV_ENERGY_TODAY_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),

            # Baseline and runtime configuration
            vol.Optional(CONF_RUNTIME_SOURCE, default=d.get(CONF_RUNTIME_SOURCE, "counter_kwh")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["counter_kwh", "power_w", "manual_dayparts"], mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_RUNTIME_COUNTER_ENTITY, default=d.get(CONF_RUNTIME_COUNTER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_RUNTIME_POWER_ENTITY, default=d.get(CONF_RUNTIME_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_LOAD_POWER_ENTITY, default=d.get(CONF_LOAD_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_BATT_POWER_ENTITY, default=d.get(CONF_BATT_POWER_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_GRID_IMPORT_TODAY_ENTITY, default=d.get(CONF_GRID_IMPORT_TODAY_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_RUNTIME_ALPHA, default=d.get(CONF_RUNTIME_ALPHA, 0.2)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1, step=0.01, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_RUNTIME_WINDOW_MIN, default=d.get(CONF_RUNTIME_WINDOW_MIN, 15)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=60, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_RUNTIME_EXCLUDE_EV, default=d.get(CONF_RUNTIME_EXCLUDE_EV, True)): selector.BooleanSelector(),
            vol.Optional(CONF_RUNTIME_EXCLUDE_BATT_GRID, default=d.get(CONF_RUNTIME_EXCLUDE_BATT_GRID, True)): selector.BooleanSelector(),
            vol.Optional(CONF_RUNTIME_SOC_FLOOR, default=d.get(CONF_RUNTIME_SOC_FLOOR, 10)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_RUNTIME_SOC_CEILING, default=d.get(CONF_RUNTIME_SOC_CEILING, 95)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                float(user_input.get(CONF_FS_LAT, 0))
                float(user_input.get(CONF_FS_LON, 0))
            except Exception:  # noqa: BLE001
                errors["base"] = "invalid_latlon"

            if not errors:
                return self.async_create_entry(title="Energy Dispatcher", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema_user(), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EnergyDispatcherOptionsFlowHandler(config_entry)


class EnergyDispatcherOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Dynamiska defaults från data + options
        current = {**self.config_entry.data, **(self.config_entry.options or {})}
        schema = _schema_user(current)
        return self.async_show_form(step_id="init", data_schema=schema)
