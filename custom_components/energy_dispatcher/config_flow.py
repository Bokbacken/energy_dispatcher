"""
Energy Dispatcher - config_flow.py

Minimal konfigflöde (en-steg) för MVP.
Tar emot strängar för entity_ids och siffror för parametrar.
Du kan förbättra detta till fler steg och selectors senare.
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
    CONF_HOUSE_CONS_SENSOR,
    CONF_FS_USE,
    CONF_FS_APIKEY,
    CONF_FS_LAT,
    CONF_FS_LON,
    CONF_FS_PLANES,
    CONF_FS_HORIZON,
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
}


def _schema_user() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NORDPOOL_ENTITY): str,
            vol.Optional(CONF_PRICE_TAX, default=DEFAULTS[CONF_PRICE_TAX]): vol.Coerce(float),
            vol.Optional(CONF_PRICE_TRANSFER, default=DEFAULTS[CONF_PRICE_TRANSFER]): vol.Coerce(float),
            vol.Optional(CONF_PRICE_SURCHARGE, default=DEFAULTS[CONF_PRICE_SURCHARGE]): vol.Coerce(float),
            vol.Optional(CONF_PRICE_VAT, default=DEFAULTS[CONF_PRICE_VAT]): vol.Coerce(float),
            vol.Optional(CONF_PRICE_FIXED_MONTHLY, default=DEFAULTS[CONF_PRICE_FIXED_MONTHLY]): vol.Coerce(float),
            vol.Optional(CONF_PRICE_INCLUDE_FIXED, default=DEFAULTS[CONF_PRICE_INCLUDE_FIXED]): bool,
            vol.Required(CONF_BATT_CAP_KWH, default=DEFAULTS[CONF_BATT_CAP_KWH]): vol.Coerce(float),
            vol.Required(CONF_BATT_SOC_ENTITY): str,
            vol.Optional(CONF_BATT_MAX_CHARGE_W, default=DEFAULTS[CONF_BATT_MAX_CHARGE_W]): vol.Coerce(int),
            vol.Optional(CONF_BATT_MAX_DISCH_W, default=DEFAULTS[CONF_BATT_MAX_DISCH_W]): vol.Coerce(int),
            vol.Optional(CONF_BATT_ADAPTER, default=DEFAULTS[CONF_BATT_ADAPTER]): vol.In(["huawei"]),
            vol.Optional(CONF_HUAWEI_DEVICE_ID, default=""): str,
            vol.Optional(CONF_HOUSE_CONS_SENSOR, default=""): str,
            vol.Optional(CONF_EV_MODE, default=DEFAULTS[CONF_EV_MODE]): vol.In(["manual"]),
            vol.Optional(CONF_EV_BATT_KWH, default=DEFAULTS[CONF_EV_BATT_KWH]): vol.Coerce(float),
            vol.Optional(CONF_EV_CURRENT_SOC, default=DEFAULTS[CONF_EV_CURRENT_SOC]): vol.Coerce(float),
            vol.Optional(CONF_EV_TARGET_SOC, default=DEFAULTS[CONF_EV_TARGET_SOC]): vol.Coerce(float),
            vol.Optional(CONF_EVSE_START_SWITCH, default=""): str,
            vol.Optional(CONF_EVSE_STOP_SWITCH, default=""): str,
            vol.Optional(CONF_EVSE_CURRENT_NUMBER, default=""): str,
            vol.Optional(CONF_EVSE_MIN_A, default=DEFAULTS[CONF_EVSE_MIN_A]): vol.Coerce(int),
            vol.Optional(CONF_EVSE_MAX_A, default=DEFAULTS[CONF_EVSE_MAX_A]): vol.Coerce(int),
            vol.Optional(CONF_EVSE_PHASES, default=DEFAULTS[CONF_EVSE_PHASES]): vol.Coerce(int),
            vol.Optional(CONF_EVSE_VOLTAGE, default=DEFAULTS[CONF_EVSE_VOLTAGE]): vol.Coerce(int),
            vol.Optional(CONF_FS_USE, default=DEFAULTS[CONF_FS_USE]): bool,
            vol.Optional(CONF_FS_APIKEY, default=""): str,
            vol.Optional(CONF_FS_LAT, default=56.6967208731): vol.Coerce(float),
            vol.Optional(CONF_FS_LON, default=13.0196173488): vol.Coerce(float),
            # PLANES: för MVP: ange som JSON-sträng, ex: [{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]
            vol.Optional(CONF_FS_PLANES, default='[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]'): str,
            # Horizon CSV enligt Forecast.Solar: "18,16,11,7,5,4,3,2,2,4,7,10"
            vol.Optional(CONF_FS_HORIZON, default="18,16,11,7,5,4,3,2,2,4,7,10"): str,
        }
    )


class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Minimal validering
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

        # Visa samma schema som för user, med befintliga värden som default
        current = {**self.config_entry.data, **(self.config_entry.options or {})}
        schema = _schema_user()
        # OBS: Vi återanvänder schema men Home Assistant visar defaults från schema, ej current,
        # så en fullständig options-UI hade satt dynamiska defaults. För MVP räcker detta.
        return self.async_show_form(step_id="init", data_schema=schema)
