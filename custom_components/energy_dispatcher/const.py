DOMAIN = "energy_dispatcher"
PLATFORMS = ["sensor", "switch", "button"]

CONF_NORDPOOL_ENTITY = "nordpool_entity"
CONF_PRICE_TAX = "price_tax"           # kr/kWh
CONF_PRICE_TRANSFER = "price_transfer" # kr/kWh
CONF_PRICE_SURCHARGE = "price_surcharge"  # kr/kWh (alt %: se TODO)
CONF_PRICE_VAT = "price_vat"           # 0.25 e.g.
CONF_PRICE_FIXED_MONTHLY = "price_fixed_monthly"  # kr/mån
CONF_PRICE_INCLUDE_FIXED = "price_include_fixed"

CONF_HOUSE_CONS_SENSOR = "house_avg_consumption_entity"  # kWh/h

# Forecast.solar
CONF_FS_USE = "fs_use"
CONF_FS_APIKEY = "fs_apikey"
CONF_FS_LAT = "fs_lat"
CONF_FS_LON = "fs_lon"
CONF_FS_PLANES = "fs_planes"  # list of dicts: {dec, az, kwp}
CONF_FS_HORIZON = "fs_horizon"  # optional CSV numbers

# Battery
CONF_BATT_CAP_KWH = "batt_capacity_kwh"
CONF_BATT_SOC_ENTITY = "batt_soc_entity"
CONF_BATT_MAX_CHARGE_W = "batt_max_charge_w"
CONF_BATT_MAX_DISCH_W = "batt_max_discharge_w"
CONF_BATT_ADAPTER = "batt_adapter"
CONF_HUAWEI_DEVICE_ID = "huawei_device_id"

# EV/EVSE
CONF_EV_MODE = "ev_mode"  # "manual" | "integration"
CONF_EV_TARGET_SOC = "ev_target_soc"
CONF_EV_CURRENT_SOC = "ev_current_soc"
CONF_EV_BATT_KWH = "ev_batt_kwh"
CONF_EV_DEADLINE = "ev_deadline"  # e.g. "07:00"
CONF_EVSE_START_SWITCH = "evse_start_switch"
CONF_EVSE_STOP_SWITCH = "evse_stop_switch"
CONF_EVSE_CURRENT_NUMBER = "evse_current_number"
CONF_EVSE_MIN_A = "evse_min_a"
CONF_EVSE_MAX_A = "evse_max_a"
CONF_EVSE_PHASES = "evse_phases"
CONF_EVSE_VOLTAGE = "evse_voltage"

# Coordinator intervals (seconds)
DEFAULT_UPDATE_INTERVAL = 300

ATTR_PLAN = "plan"
