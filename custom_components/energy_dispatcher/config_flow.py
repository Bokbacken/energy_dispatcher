"""Config flow för Energy Dispatcher."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    CONF_BATTERY_SETTINGS,
    CONF_ENABLE_AUTO_DISPATCH,
    CONF_EV_SETTINGS,
    CONF_FORECAST_API_KEY,
    CONF_FORECAST_HORIZON,
    CONF_FORECAST_LAT,
    CONF_FORECAST_LON,
    CONF_PV_ARRAYS,
    CONF_PRICE_API_TOKEN,
    CONF_PRICE_AREA,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_SENSOR,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from .helpers import (
    default_pv_arrays_json,
    get_default_horizon_string,
    parse_config_entry_from_flow_data,
)

STEP_GENERAL = "general"
STEP_PV = "pv"
STEP_PRICE = "price"
STEP_BATTERY = "battery"
STEP_EV = "ev"
STEP_HOUSE = "house"
STEP_OPTIONS = "options"


class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfigurationsflöde."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None):
        """Första steget."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_pv()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Energy Dispatcher"): str,
                vol.Required(CONF_FORECAST_API_KEY): str,
                vol.Required(CONF_FORECAST_LAT, default=56.6967): vol.Coerce(float),
                vol.Required(CONF_FORECAST_LON, default=13.0196): vol.Coerce(float),
                vol.Optional(
                    CONF_FORECAST_HORIZON,
                    default=get_default_horizon_string(),
                ): str,
            }
        )
        return self.async_show_form(step_id=STEP_GENERAL, data_schema=schema)

    async def async_step_pv(self, user_input: Mapping[str, Any] | None = None):
        """Steg: PV-konfiguration."""
        if user_input is not None:
            try:
                json.loads(user_input[CONF_PV_ARRAYS])
            except json.JSONDecodeError as err:
                return self.async_show_form(
                    step_id=STEP_PV,
                    data_schema=self._pv_schema(),
                    errors={"base": f"json_error: {err}"},
                )
            self._data.update(user_input)
            return await self.async_step_price()

        return self.async_show_form(
            step_id=STEP_PV,
            data_schema=self._pv_schema(),
            description_placeholders={
                "pv_example": default_pv_arrays_json(),
            },
        )

    async def async_step_price(self, user_input: Mapping[str, Any] | None = None):
        """Steg: prisdata."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery()

        schema = vol.Schema(
            {
                vol.Required(CONF_PRICE_AREA, default="SE3"): str,
                vol.Required(CONF_PRICE_CURRENCY, default="SEK"): str,
                vol.Optional(CONF_PRICE_API_TOKEN): str,
                vol.Optional(CONF_PRICE_SENSOR): str,
            }
        )
        return self.async_show_form(step_id=STEP_PRICE, data_schema=schema)

    async def async_step_battery(self, user_input: Mapping[str, Any] | None = None):
        """Steg: batteri."""
        if user_input is not None:
            if user_input.get("has_battery"):
                self._data[CONF_BATTERY_SETTINGS] = {
                    "adapter_type": user_input["adapter_type"],
                    "capacity_kwh": user_input["capacity_kwh"],
                    "min_soc": user_input["min_soc"],
                    "max_soc": user_input["max_soc"],
                    "soc_sensor_entity_id": user_input["soc_sensor_entity_id"],
                    "power_sensor_entity_id": user_input.get("power_sensor_entity_id"),
                    "grid_import_sensor_entity_id": user_input.get(
                        "grid_import_sensor_entity_id"
                    ),
                    "force_charge_entity_id": user_input.get(
                        "force_charge_entity_id"
                    ),
                    "force_discharge_entity_id": user_input.get(
                        "force_discharge_entity_id"
                    ),
                    "charge_mode_select_entity_id": user_input.get(
                        "charge_mode_select_entity_id"
                    ),
                    "charge_current_number_entity_id": user_input.get(
                        "charge_current_number_entity_id"
                    ),
                    "supports_force_charge": user_input.get(
                        "supports_force_charge", False
                    ),
                    "supports_force_discharge": user_input.get(
                        "supports_force_discharge", False
                    ),
                    "power_sign_invert": user_input.get("power_sign_invert", False),
                }
            return await self.async_step_ev()

        return self.async_show_form(
            step_id=STEP_BATTERY,
            data_schema=self._battery_schema(),
        )

    async def async_step_ev(self, user_input: Mapping[str, Any] | None = None):
        """Steg: elbil."""
        if user_input is not None:
            if user_input.get("has_ev"):
                self._data[CONF_EV_SETTINGS] = {
                    "adapter_type": user_input["adapter_type"],
                    "capacity_kwh": user_input["capacity_kwh"],
                    "default_target_soc": user_input["default_target_soc"],
                    "min_ampere": user_input["min_ampere"],
                    "max_ampere": user_input["max_ampere"],
                    "default_ampere": user_input["default_ampere"],
                    "soc_sensor_entity_id": user_input.get("soc_sensor_entity_id"),
                    "charger_switch_entity_id": user_input.get(
                        "charger_switch_entity_id"
                    ),
                    "charger_pause_switch_entity_id": user_input.get(
                        "charger_pause_switch_entity_id"
                    ),
                    "current_number_entity_id": user_input.get(
                        "current_number_entity_id"
                    ),
                    "manual_departure_time": user_input.get("manual_departure_time"),
                    "manual_ready_by_time": user_input.get("manual_ready_by_time"),
                    "efficiency": user_input.get("efficiency", 0.9),
                    "allow_manual_soc_entry": user_input.get(
                        "allow_manual_soc_entry", True
                    ),
                }
            return await self.async_step_house()

        return self.async_show_form(
            step_id=STEP_EV,
            data_schema=self._ev_schema(),
        )

    async def async_step_house(self, user_input: Mapping[str, Any] | None = None):
        """Steg: hus / laster."""
        if user_input is not None:
            self._data["house_settings"] = {
                "avg_consumption_sensor": user_input.get("avg_consumption_sensor"),
                "temperature_sensor": user_input.get("temperature_sensor"),
                "base_load_kw": user_input.get("base_load_kw"),
                "hvac_load_sensor": user_input.get("hvac_load_sensor"),
                "dishwasher_load_kw": user_input.get("dishwasher_load_kw"),
                "washer_load_kw": user_input.get("washer_load_kw"),
                "dryer_load_kw": user_input.get("dryer_load_kw"),
                "extra_manual_entities": [
                    e.strip()
                    for e in user_input.get("extra_manual_entities", "").split(",")
                    if e.strip()
                ],
            }
            return await self.async_step_options()

        schema = vol.Schema(
            {
                vol.Optional("avg_consumption_sensor"): str,
                vol.Optional("temperature_sensor"): str,
                vol.Optional("base_load_kw", default=0.5): vol.Coerce(float),
                vol.Optional("hvac_load_sensor"): str,
                vol.Optional("dishwasher_load_kw", default=1.5): vol.Coerce(float),
                vol.Optional("washer_load_kw", default=2.0): vol.Coerce(float),
                vol.Optional("dryer_load_kw", default=2.2): vol.Coerce(float),
                vol.Optional("extra_manual_entities"): str,
            }
        )
        return self.async_show_form(step_id=STEP_HOUSE, data_schema=schema)

    async def async_step_options(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Sista steget innan konfiguration sparas."""
        if user_input is not None:
            self._data[CONF_ENABLE_AUTO_DISPATCH] = user_input[
                CONF_ENABLE_AUTO_DISPATCH
            ]
            self._data[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
            return self._create_entry()

        schema = vol.Schema(
            {
                vol.Optional(CONF_ENABLE_AUTO_DISPATCH, default=True): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=300): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=3600)
                ),
            }
        )
        return self.async_show_form(step_id=STEP_OPTIONS, data_schema=schema)

    def _create_entry(self) -> config_entries.FlowResult:
        """Skapa config entry."""
        config_data, options = parse_config_entry_from_flow_data(self._data)
        return self.async_create_entry(
            title=self._data.get(CONF_NAME, "Energy Dispatcher"),
            data=config_data,
            options=options,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return EnergyDispatcherOptionsFlow(config_entry)

    # ----------------- Scheman -----------------
    @staticmethod
    def _pv_schema() -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_PV_ARRAYS,
                    default=default_pv_arrays_json(),
                ): str,
            }
        )

    @staticmethod
    def _battery_schema() -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("has_battery", default=True): bool,
                vol.Optional("adapter_type", default="huawei"): vol.In(
                    ["huawei", "entity"]
                ),
                vol.Optional("capacity_kwh", default=10.0): vol.Coerce(float),
                vol.Optional("min_soc", default=0.1): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=0.9)
                ),
                vol.Optional("max_soc", default=0.95): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=1.0)
                ),
                vol.Optional("soc_sensor_entity_id"): str,
                vol.Optional("power_sensor_entity_id"): str,
                vol.Optional("grid_import_sensor_entity_id"): str,
                vol.Optional("force_charge_entity_id"): str,
                vol.Optional("force_discharge_entity_id"): str,
                vol.Optional("charge_mode_select_entity_id"): str,
                vol.Optional("charge_current_number_entity_id"): str,
                vol.Optional("supports_force_charge", default=True): bool,
                vol.Optional("supports_force_discharge", default=False): bool,
                vol.Optional("power_sign_invert", default=False): bool,
            }
        )

    @staticmethod
    def _ev_schema() -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("has_ev", default=True): bool,
                vol.Optional("adapter_type", default="generic_evse"): vol.In(
                    ["generic_evse", "manual"]
                ),
                vol.Optional("capacity_kwh", default=75.0): vol.All(
                    vol.Coerce(float), vol.Range(min=10, max=150)
                ),
                vol.Optional("default_target_soc", default=0.8): vol.All(
                    vol.Coerce(float), vol.Range(min=0.3, max=1.0)
                ),
                vol.Optional("min_ampere", default=6): vol.Coerce(float),
                vol.Optional("max_ampere", default=16): vol.Coerce(float),
                vol.Optional("default_ampere", default=16): vol.Coerce(float),
                vol.Optional("soc_sensor_entity_id"): str,
                vol.Optional("charger_switch_entity_id"): str,
                vol.Optional("charger_pause_switch_entity_id"): str,
                vol.Optional("current_number_entity_id"): str,
                vol.Optional("manual_departure_time", default="07:00"): str,
                vol.Optional("manual_ready_by_time", default="06:30"): str,
                vol.Optional("efficiency", default=0.9): vol.All(
                    vol.Coerce(float), vol.Range(min=0.6, max=1.0)
                ),
                vol.Optional("allow_manual_soc_entry", default=True): bool,
            }
        )


class EnergyDispatcherOptionsFlow(config_entries.OptionsFlow):
    """Optionshantering (efter installation)."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_AUTO_DISPATCH,
                    default=self.entry.options.get(CONF_ENABLE_AUTO_DISPATCH, True),
                ): bool,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.entry.options.get(CONF_SCAN_INTERVAL, 300),
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                vol.Optional(
                    CONF_PRICE_SENSOR,
                    default=self.entry.options.get(CONF_PRICE_SENSOR),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
