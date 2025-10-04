"""
Energy Dispatcher - config_flow.py
Enhanced configuration flow: clear descriptions, entity type hints, and help texts for easier setup.
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
            # Pricing
            vol.Required(CONF_NORDPOOL_ENTITY, default=d.get(CONF_NORDPOOL_ENTITY, "")): str,  # "Nordpool Price Sensor (SEK/kWh): Select the sensor or entity that provides spot price for electricity."
            vol.Optional(CONF_PRICE_TAX, default=d.get(CONF_PRICE_TAX, 0.0)): vol.Coerce(float),  # "Tax (SEK/kWh): Local electricity tax per kWh."
            vol.Optional(CONF_PRICE_TRANSFER, default=d.get(CONF_PRICE_TRANSFER, 0.0)): vol.Coerce(float),  # "Transfer Fee (SEK/kWh): Grid operator transfer cost per kWh."
            vol.Optional(CONF_PRICE_SURCHARGE, default=d.get(CONF_PRICE_SURCHARGE, 0.0)): vol.Coerce(float),  # "Surcharge (SEK/kWh): Any additional surcharges per kWh."
            vol.Optional(CONF_PRICE_VAT, default=d.get(CONF_PRICE_VAT, 0.25)): vol.Coerce(float),  # "VAT (%): Value Added Tax rate, e.g., 25."
            vol.Optional(CONF_PRICE_FIXED_MONTHLY, default=d.get(CONF_PRICE_FIXED_MONTHLY, 0.0)): vol.Coerce(float),  # "Fixed Monthly Fee (SEK): Fixed monthly cost for electricity."
            vol.Optional(CONF_PRICE_INCLUDE_FIXED, default=d.get(CONF_PRICE_INCLUDE_FIXED, False)): bool,  # "Include Fixed Monthly Fee: Whether to include fixed fee in cost calculations."

            # Battery
            vol.Required(CONF_BATT_CAP_KWH, default=d.get(CONF_BATT_CAP_KWH, 15.0)): vol.Coerce(float),  # "Battery Capacity (kWh): Total usable battery capacity. Use a sensor or enter manually."
            vol.Required(CONF_BATT_SOC_ENTITY, default=d.get(CONF_BATT_SOC_ENTITY, "")): str,  # "Battery SOC Sensor (%): Entity reporting battery state-of-charge (SOC) as a percentage (0–100%)."
            vol.Optional(CONF_BATT_MAX_CHARGE_W, default=d.get(CONF_BATT_MAX_CHARGE_W, 4000)): vol.Coerce(int),  # "Max Battery Charge Power (W): Maximum allowed charge power."
            vol.Optional(CONF_BATT_MAX_DISCH_W, default=d.get(CONF_BATT_MAX_DISCH_W, 4000)): vol.Coerce(int),  # "Max Battery Discharge Power (W): Maximum allowed discharge power."
            vol.Optional(CONF_BATT_ADAPTER, default=d.get(CONF_BATT_ADAPTER, "huawei")): vol.In(["huawei"]),  # "Battery Adapter Type: Current supported: Huawei."
            vol.Optional(CONF_HUAWEI_DEVICE_ID, default=d.get(CONF_HUAWEI_DEVICE_ID, "")): str,  # "Huawei Device ID: For Huawei battery adapter."

            # EV
            vol.Optional(CONF_EV_MODE, default=d.get(CONF_EV_MODE, "manual")): vol.In(["manual"]),  # "EV Mode: For now, only manual SOC is supported."
            vol.Optional(CONF_EV_BATT_KWH, default=d.get(CONF_EV_BATT_KWH, 75.0)): vol.Coerce(float),  # "EV Battery Capacity (kWh): Enter EV battery size."
            vol.Optional(CONF_EV_CURRENT_SOC, default=d.get(CONF_EV_CURRENT_SOC, 40.0)): vol.Coerce(float),  # "EV Current SOC (%): Current state-of-charge (manual or via sensor)."
            vol.Optional(CONF_EV_TARGET_SOC, default=d.get(CONF_EV_TARGET_SOC, 80.0)): vol.Coerce(float),  # "EV Target SOC (%): Desired SOC after charging (manual or via sensor)."
            vol.Optional(CONF_EVSE_START_SWITCH, default=d.get(CONF_EVSE_START_SWITCH, "")): str,  # "EV Charger Start Switch: Switch or button to start charging."
            vol.Optional(CONF_EVSE_STOP_SWITCH, default=d.get(CONF_EVSE_STOP_SWITCH, "")): str,  # "EV Charger Stop Switch: Switch or button to stop charging."
            vol.Optional(CONF_EVSE_CURRENT_NUMBER, default=d.get(CONF_EVSE_CURRENT_NUMBER, "")): str,  # "EV Charger Current Number (A): Number entity for charging current (amps)."
            vol.Optional(CONF_EVSE_MIN_A, default=d.get(CONF_EVSE_MIN_A, 6)): vol.Coerce(int),  # "EV Charger Min Current (A): Minimum allowed charging current."
            vol.Optional(CONF_EVSE_MAX_A, default=d.get(CONF_EVSE_MAX_A, 16)): vol.Coerce(int),  # "EV Charger Max Current (A): Maximum allowed charging current."
            vol.Optional(CONF_EVSE_PHASES, default=d.get(CONF_EVSE_PHASES, 3)): vol.Coerce(int),  # "EV Charger Phases: Number of charging phases (usually 1 or 3)."
            vol.Optional(CONF_EVSE_VOLTAGE, default=d.get(CONF_EVSE_VOLTAGE, 230)): vol.Coerce(int),  # "EV Charger Voltage (V): Voltage (typically 230V)."

            # Solar Forecast
            vol.Optional(CONF_FS_USE, default=d.get(CONF_FS_USE, True)): bool,  # "Enable Solar Forecast: Toggle to activate solar forecast calculations."
            vol.Optional(CONF_FS_APIKEY, default=d.get(CONF_FS_APIKEY, "")): str,  # "Forecast.Solar API Key: Required if using Forecast.Solar."
            vol.Optional(CONF_FS_LAT, default=d.get(CONF_FS_LAT, 56.6967208731)): vol.Coerce(float),  # "Latitude: Site latitude for solar calculations."
            vol.Optional(CONF_FS_LON, default=d.get(CONF_FS_LON, 13.0196173488)): vol.Coerce(float),  # "Longitude: Site longitude for solar calculations."
            vol.Optional(CONF_FS_PLANES, default=d.get(CONF_FS_PLANES, '[{"dec":45,"az":"W","kwp":9.43},{"dec":45,"az":"E","kwp":4.92}]')): str,  # "Solar Panel Orientation: JSON config for azimuth, declination, and power per plane."
            vol.Optional(CONF_FS_HORIZON, default=d.get(CONF_FS_HORIZON, "18,16,11,7,5,4,3,2,2,4,7,10")): str,  # "Horizon Profile: CSV string (degrees) for local horizon."

            # PV Actual
            vol.Optional(CONF_PV_POWER_ENTITY, default=d.get(CONF_PV_POWER_ENTITY, "")): str,  # "PV Power Sensor (W/kW/MW): Select sensor for real-time PV production. Unit must be specified."
            vol.Optional(CONF_PV_ENERGY_TODAY_ENTITY, default=d.get(CONF_PV_ENERGY_TODAY_ENTITY, "")): str,  # "PV Energy Today Sensor (Wh/kWh/MWh): Select sensor for total PV energy generated today. Unit must be specified."

            # House Consumption
            vol.Optional(CONF_HOUSE_CONS_SENSOR, default=d.get(CONF_HOUSE_CONS_SENSOR, "")): str,  # "House Consumption Sensor (W): Real-time sensor for home consumption."
            # Baseline
            vol.Optional(CONF_RUNTIME_SOURCE, default=d.get(CONF_RUNTIME_SOURCE, "counter_kwh")): vol.In(["counter_kwh", "power_w", "manual_dayparts"]),  # "Baseline Source: Choose method for baseline calculation."
            vol.Optional(CONF_RUNTIME_COUNTER_ENTITY, default=d.get(CONF_RUNTIME_COUNTER_ENTITY, "")): str,  # "House Consumption Counter (kWh): Sensor/entity for total home consumption."
            vol.Optional(CONF_RUNTIME_POWER_ENTITY, default=d.get(CONF_RUNTIME_POWER_ENTITY, "")): str,  # "House Consumption Power Sensor (W): Sensor/entity for real-time home consumption."
            vol.Optional(CONF_LOAD_POWER_ENTITY, default=d.get(CONF_LOAD_POWER_ENTITY, "")): str,  # "Load Power Sensor (W): Sensor/entity for real-time load power (optional, for exclusions)."
            vol.Optional(CONF_BATT_POWER_ENTITY, default=d.get(CONF_BATT_POWER_ENTITY, "")): str,  # "Battery Power Sensor (W): Sensor/entity for battery power flow (optional)."
            vol.Optional(CONF_GRID_IMPORT_TODAY_ENTITY, default=d.get(CONF_GRID_IMPORT_TODAY_ENTITY, "")): str,  # "Grid Import Today Sensor (kWh): Sensor/entity for total grid import today (optional)."
            vol.Optional(CONF_RUNTIME_ALPHA, default=d.get(CONF_RUNTIME_ALPHA, 0.2)): vol.Coerce(float),  # "Baseline Smoothing (α): Smoothing factor, 0 (no smoothing) to 1 (instant)."
            vol.Optional(CONF_RUNTIME_WINDOW_MIN, default=d.get(CONF_RUNTIME_WINDOW_MIN, 15)): vol.Coerce(int),  # "Baseline Window (min): Number of minutes for moving average window."
            vol.Optional(CONF_RUNTIME_EXCLUDE_EV, default=d.get(CONF_RUNTIME_EXCLUDE_EV, True)): bool,  # "Exclude EV Charging: Exclude EV charging periods from baseline calculation."
            vol.Optional(CONF_RUNTIME_EXCLUDE_BATT_GRID, default=d.get(CONF_RUNTIME_EXCLUDE_BATT_GRID, True)): bool,  # "Exclude Battery Grid Charging: Exclude battery grid charging periods from baseline calculation."
            vol.Optional(CONF_RUNTIME_SOC_FLOOR, default=d.get(CONF_RUNTIME_SOC_FLOOR, 10)): vol.Coerce(float),  # "SOC Floor (%): Minimum SOC for battery operation."
            vol.Optional(CONF_RUNTIME_SOC_CEILING, default=d.get(CONF_RUNTIME_SOC_CEILING, 95)): vol.Coerce(float),  # "SOC Ceiling (%): Maximum SOC for battery operation."
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

        # Dynamic defaults from config entry data + options
        current = {**self.config_entry.data, **(self.config_entry.options or {})}
        schema = _schema_user(current)
        return self.async_show_form(step_id="init", data_schema=schema)
