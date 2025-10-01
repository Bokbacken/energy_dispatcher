from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import *

BATTERY_BRANDS = ["huawei", "generic"]

class EnergyDispatcherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return await self.async_step_details(user_input)

        schema = vol.Schema({
            vol.Required(CONF_BATTERY_BRAND, default="huawei"): vol.In(BATTERY_BRANDS),
            vol.Required(CONF_BATTERY_SOC_ENTITY): str,
            vol.Required(CONF_PRICE_TODAY_ENTITY): str,     # expects attribute data: [ {start, end, price} ]
            vol.Required(CONF_PRICE_TOMORROW_ENTITY): str,  # same as above (can be empty before publish)
            vol.Optional(CONF_PV_POWER_ENTITY, default=""): str,
            vol.Optional(CONF_HOUSE_LOAD_ENTITY, default=""): str,
            vol.Optional(CONF_HUAWEI_DEVICE_ID, default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_details(self, base):
        self.base = base
        schema = vol.Schema({
            vol.Required(CONF_BATTERY_CAPACITY_KWH, default=DEFAULT_BATTERY_CAPACITY_KWH): float,
            vol.Required(CONF_BATTERY_EFF, default=DEFAULT_BATTERY_EFF): float,
            vol.Required(CONF_MORNING_SOC_TARGET, default=DEFAULT_MORNING_SOC_TARGET): float,
            vol.Required(CONF_SOC_FLOOR, default=DEFAULT_SOC_FLOOR): float,
            vol.Required(CONF_MAX_GRID_CHARGE_KW, default=DEFAULT_MAX_GRID_CHARGE_KW): float,
            vol.Required(CONF_BEC_MARGIN, default=DEFAULT_BEC_MARGIN_KR_PER_KWH): float,
            vol.Required(CONF_PRICE_LOW_PERCENTILE, default=DEFAULT_PRICE_LOW_PERCENTILE): float,
        })
        return self.async_show_form(step_id="details", data_schema=schema)

    async def async_step_details_submit(self, user_input):
        data = {**self.base, **user_input}
        return self.async_create_entry(title="Energy Dispatcher", data=data)

    async def async_step_details(self, user_input=None):
        if user_input is not None:
            return await self.async_step_details_submit(user_input)
        schema = vol.Schema({
            vol.Required(CONF_BATTERY_CAPACITY_KWH, default=DEFAULT_BATTERY_CAPACITY_KWH): float,
            vol.Required(CONF_BATTERY_EFF, default=DEFAULT_BATTERY_EFF): float,
            vol.Required(CONF_MORNING_SOC_TARGET, default=DEFAULT_MORNING_SOC_TARGET): float,
            vol.Required(CONF_SOC_FLOOR, default=DEFAULT_SOC_FLOOR): float,
            vol.Required(CONF_MAX_GRID_CHARGE_KW, default=DEFAULT_MAX_GRID_CHARGE_KW): float,
            vol.Required(CONF_BEC_MARGIN, default=DEFAULT_BEC_MARGIN_KR_PER_KWH): float,
            vol.Required(CONF_PRICE_LOW_PERCENTILE, default=DEFAULT_PRICE_LOW_PERCENTILE): float,
        })
        return self.async_show_form(step_id="details", data_schema=schema)
