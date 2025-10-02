"""Konstanter och nycklar som används i Energy Dispatcher."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "energy_dispatcher"
NAME: Final = "Energy Dispatcher"

PLATFORMS: Final[list[Platform]] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

# Standardintervall för uppdateringar om inget annat anges i options.
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)

# Konfigurationsnycklar (config_flow, config entry data/options).
CONF_FORECAST_API_KEY: Final = "forecast_api_key"
CONF_FORECAST_LAT: Final = "forecast_lat"
CONF_FORECAST_LON: Final = "forecast_lon"
CONF_FORECAST_HORIZON: Final = "forecast_horizon"
CONF_PV_ARRAYS: Final = "pv_arrays"

CONF_PRICE_AREA: Final = "price_area"
CONF_PRICE_CURRENCY: Final = "price_currency"
CONF_PRICE_API_TOKEN: Final = "price_api_token"
CONF_PRICE_SENSOR: Final = "price_sensor_entity_id"

CONF_BATTERY_SETTINGS: Final = "battery_settings"
CONF_EV_SETTINGS: Final = "ev_settings"
CONF_HOUSE_SETTINGS: Final = "house_settings"

CONF_ENABLE_AUTO_DISPATCH: Final = "enable_auto_dispatch"
CONF_SCAN_INTERVAL: Final = "scan_interval_seconds"

# Attributnycklar.
ATTR_PLAN: Final = "plan"
ATTR_SOLAR_FORECAST: Final = "solar_forecast"
ATTR_PRICE_SCHEDULE: Final = "price_schedule"
ATTR_BATTERY_STATE: Final = "battery_state"
ATTR_EV_STATE: Final = "ev_state"
ATTR_HOUSE_STATE: Final = "house_state"
ATTR_GENERATION_TIMESTAMP: Final = "generated_at"

# Service-namn.
SERVICE_FORCE_CHARGE: Final = "force_charge_battery"
SERVICE_FORCE_DISCHARGE: Final = "force_discharge_battery"
SERVICE_PAUSE_EV_CHARGING: Final = "pause_ev_charging"
SERVICE_RESUME_EV_CHARGING: Final = "resume_ev_charging"
SERVICE_SET_MANUAL_EV_SOC: Final = "set_manual_ev_soc"
SERVICE_OVERRIDE_PLAN: Final = "override_plan"

# Hemsnickrade konstanter för adapter-typer.
BATTERY_ADAPTER_HUAWEI: Final = "huawei"
BATTERY_ADAPTER_ENTITY: Final = "entity"

EV_ADAPTER_MANUAL: Final = "manual"
EV_ADAPTER_GENERIC_EVSE: Final = "generic_evse"

# Metadata för storage.
STORAGE_VERSION: Final = 1
STORAGE_KEY_TEMPLATE: Final = "energy_dispatcher_{entry_id}"

# Övriga gränsvärden.
MIN_SOC_DEFAULT: Final = 0.1
MAX_SOC_DEFAULT: Final = 0.95
DEFAULT_EV_TARGET_SOC: Final = 0.8

# Planner-konstanter.
LOW_PRICE_THRESHOLD_FACTOR: Final = 0.85
HIGH_PRICE_THRESHOLD_FACTOR: Final = 1.15
