"""Hjälpfunktioner (delas mellan moduler)."""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict, Tuple

from homeassistant.const import CONF_NAME

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
)


def default_pv_arrays_json() -> str:
    """Standardexempel för PV-arraylista."""
    example = [
        {
            "label": "Tak väst",
            "tilt": 35,
            "azimuth": "W",
            "peak_power_kwp": 4.92,
        },
        {
            "label": "Tak öst",
            "tilt": 45,
            "azimuth": "E",
            "peak_power_kwp": 4.51,
        },
    ]
    return json.dumps(example, indent=2)


def get_default_horizon_string() -> str:
    return "18,16,11,7,5,4,3,2,2,4,7,10"


def parse_config_entry_from_flow_data(flow_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Dela upp konfiguration i data (statisk) + options (dynamisk)."""
    config = {
        CONF_NAME: flow_data[CONF_NAME],
        CONF_FORECAST_API_KEY: flow_data[CONF_FORECAST_API_KEY],
        CONF_FORECAST_LAT: flow_data[CONF_FORECAST_LAT],
        CONF_FORECAST_LON: flow_data[CONF_FORECAST_LON],
        CONF_FORECAST_HORIZON: flow_data.get(CONF_FORECAST_HORIZON),
        CONF_PV_ARRAYS: flow_data[CONF_PV_ARRAYS],
        CONF_PRICE_AREA: flow_data[CONF_PRICE_AREA],
        CONF_PRICE_CURRENCY: flow_data[CONF_PRICE_CURRENCY],
        CONF_PRICE_API_TOKEN: flow_data.get(CONF_PRICE_API_TOKEN),
    }

    if CONF_BATTERY_SETTINGS in flow_data:
        config[CONF_BATTERY_SETTINGS] = flow_data[CONF_BATTERY_SETTINGS]
    if CONF_EV_SETTINGS in flow_data:
        config[CONF_EV_SETTINGS] = flow_data[CONF_EV_SETTINGS]
    config["house_settings"] = flow_data["house_settings"]

    options = {
        CONF_ENABLE_AUTO_DISPATCH: flow_data.get(CONF_ENABLE_AUTO_DISPATCH, True),
        CONF_SCAN_INTERVAL: flow_data.get(CONF_SCAN_INTERVAL, 300),
        CONF_PRICE_SENSOR: flow_data.get(CONF_PRICE_SENSOR),
    }
    return config, options
