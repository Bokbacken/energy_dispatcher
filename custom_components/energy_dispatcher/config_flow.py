from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    # Defaults
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_BATTERY_EFF,
    DEFAULT_MORNING_SOC_TARGET,
    DEFAULT_SOC_FLOOR,
    DEFAULT_MAX_GRID_CHARGE_KW,
    DEFAULT_BEC_MARGIN_KR_PER_KWH,
    DEFAULT_PRICE_LOW_PERCENTILE,
    # Keys
    CONF_BATTERY_BRAND,
    CONF_BATTERY_SOC_ENTITY,
    CONF_PV_POWER_ENTITY,
    CONF_HOUSE_LOAD_ENTITY,
    CONF_HUAWEI_DEVICE_ID,
    CONF_PRICE_TODAY_ENTITY,
    CONF_PRICE_TOMORROW_ENTITY,
    CONF_PRICE_COMBINED_ENTITY,
)

BATTERY_BRANDS = ["huawei", "generic"]


def _as_float(v: Any) -> float:
    """
    Robust float-converter:
    - Accepterar str med komma eller punkt som decimal
    - Trimmar whitespace
    """
    if isinstance(v, str):
        v = v.replace(",", ".").strip()
    return float(v)


class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    _data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Bas-steg: välj batteribrand, entities och (helst) combined price-sensor.
        """
        if user_input is not None:
            # Spara och gå vidare till detaljer
            self._data = dict(user_input)
            return await self.async_step_details()

        schema = vol.Schema(
            {
                vol.Required(CONF_BATTERY_BRAND, default="huawei"): vol.In(BATTERY_BRANDS),
                vol.Required(CONF_BATTERY_SOC_ENTITY): str,
                # Pris-sensorer: helst combined, men stödjer även split
                vol.Optional(CONF_PRICE_COMBINED_ENTITY, default=""): str,
                vol.Optional(CONF_PRICE_TODAY_ENTITY, default=""): str,
                vol.Optional(CONF_PRICE_TOMORROW_ENTITY, default=""): str,
                # Övriga (frivilliga)
                vol.Optional(CONF_PV_POWER_ENTITY, default=""): str,
                vol.Optional(CONF_HOUSE_LOAD_ENTITY, default=""): str,
                vol.Optional(CONF_HUAWEI_DEVICE_ID, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_details(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Detalj-steg: mål, gränser och parametrar. Alla coerces till float, med stöd för komma.
        """
        if user_input is not None:
            data = {**self._data, **user_input}
            return self.async_create_entry(title="Energy Dispatcher", data=data)

        schema = vol.Schema(
            {
                vol.Required("battery_capacity_kwh", default=DEFAULT_BATTERY_CAPACITY_KWH): vol.Coerce(_as_float),
                vol.Required("battery_eff", default=DEFAULT_BATTERY_EFF): vol.All(
                    vol.Coerce(_as_float), vol.Range(min=0.80, max=0.99)
                ),
                vol.Required("morning_soc_target", default=DEFAULT_MORNING_SOC_TARGET): vol.All(
                    vol.Coerce(_as_float), vol.Range(min=0, max=100)
                ),
                vol.Required("soc_floor", default=DEFAULT_SOC_FLOOR): vol.All(
                    vol.Coerce(_as_float), vol.Range(min=0, max=100)
                ),
                vol.Required("max_grid_charge_kw", default=DEFAULT_MAX_GRID_CHARGE_KW): vol.All(
                    vol.Coerce(_as_float), vol.Range(min=0)
                ),
                vol.Required("bec_margin", default=DEFAULT_BEC_MARGIN_KR_PER_KWH): vol.Coerce(_as_float),
                vol.Required("price_low_percentile", default=DEFAULT_PRICE_LOW_PERCENTILE): vol.All(
                    vol.Coerce(_as_float), vol.Range(min=0, max=100)
                ),
            }
        )
        return self.async_show_form(step_id="details", data_schema=schema)


class EnergyDispatcherOptionsFlowHandler(config_entries.OptionsFlow):
    """
    Enkel options-flow för att undvika 'Invalid handler specified' när man klickar 'Konfigurera'.
    Här kan vi i framtiden lägga in samma schema som i details om du vill ändra parametrar efteråt.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            # Spara options (vi lämnar tomt nu)
            return self.async_create_entry(title="", data={})

        # Tom form – du kan lägga in fält här vid behov
        schema = vol.Schema({})
        return self.async_show_form(step_id="init", data_schema=schema)


async def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> EnergyDispatcherOptionsFlowHandler:
    return EnergyDispatcherOptionsFlowHandler(config_entry)
