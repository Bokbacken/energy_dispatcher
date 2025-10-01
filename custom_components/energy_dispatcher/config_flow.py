from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_BATTERY_EFF,
    DEFAULT_MORNING_SOC_TARGET,
    DEFAULT_SOC_FLOOR,
    DEFAULT_MAX_GRID_CHARGE_KW,
    DEFAULT_BEC_MARGIN_KR_PER_KWH,
    DEFAULT_PRICE_LOW_PERCENTILE,
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


class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Save and move to details
            self._data = dict(user_input)
            return await self.async_step_details()

        schema = vol.Schema(
            {
                vol.Required("battery_capacity_kwh", default=DEFAULT_BATTERY_CAPACITY_KWH): vol.Coerce(float),
                vol.Required("battery_eff", default=DEFAULT_BATTERY_EFF): vol.All(vol.Coerce(float), vol.Range(min=0.80, max=0.99)),
                vol.Required("morning_soc_target", default=DEFAULT_MORNING_SOC_TARGET): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                vol.Required("soc_floor", default=DEFAULT_SOC_FLOOR): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                vol.Required("max_grid_charge_kw", default=DEFAULT_MAX_GRID_CHARGE_KW): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Required("bec_margin", default=DEFAULT_BEC_MARGIN_KR_PER_KWH): vol.Coerce(float),
                vol.Required("price_low_percentile", default=DEFAULT_PRICE_LOW_PERCENTILE): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            }
        ) 
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_details(self, user_input=None):
        if user_input is not None:
            data = {**getattr(self, "_data", {}), **user_input}
            return self.async_create_entry(title="Energy Dispatcher", data=data)

        schema = vol.Schema(
            {
                vol.Required("battery_capacity_kwh", default=DEFAULT_BATTERY_CAPACITY_KWH): float,
                vol.Required("battery_eff", default=DEFAULT_BATTERY_EFF): float,
                vol.Required("morning_soc_target", default=DEFAULT_MORNING_SOC_TARGET): float,
                vol.Required("soc_floor", default=DEFAULT_SOC_FLOOR): float,
                vol.Required("max_grid_charge_kw", default=DEFAULT_MAX_GRID_CHARGE_KW): float,
                vol.Required("bec_margin", default=DEFAULT_BEC_MARGIN_KR_PER_KWH): float,
                vol.Required("price_low_percentile", default=DEFAULT_PRICE_LOW_PERCENTILE): float,
            }
        )
        return self.async_show_form(step_id="details", data_schema=schema)
