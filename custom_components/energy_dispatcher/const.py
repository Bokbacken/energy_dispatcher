from homeassistant.const import Platform

DOMAIN = "energy_dispatcher"

# Viktigt: PLATFORMS inkluderar NUMBER och SELECT i 0.5.4
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]

# Prisrelaterat
CONF_NORDPOOL_ENTITY = "nordpool_entity"
CONF_PRICE_TAX = "price_tax"
CONF_PRICE_TRANSFER = "price_transfer"
CONF_PRICE_SURCHARGE = "price_surcharge"
CONF_PRICE_VAT = "price_vat"
CONF_PRICE_FIXED_MONTHLY = "price_fixed_monthly"
CONF_PRICE_INCLUDE_FIXED = "price_include_fixed"

# Batteri
CONF_BATT_CAP_KWH = "batt_cap_kwh"
CONF_BATT_SOC_ENTITY = "batt_soc_entity"
CONF_BATT_MAX_CHARGE_W = "batt_max_charge_w"
CONF_BATT_MAX_DISCH_W = "batt_max_disch_w"
CONF_BATT_ADAPTER = "batt_adapter"
CONF_HUAWEI_DEVICE_ID = "huawei_device_id"
CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY = "batt_energy_charged_today_entity"  # kWh charged today
CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY = "batt_energy_discharged_today_entity"  # kWh discharged today
CONF_BATT_CAPACITY_ENTITY = "batt_capacity_entity"  # Rated ESS capacity sensor (optional)

# Legacy house consumption (fallback)
CONF_HOUSE_CONS_SENSOR = "house_cons_sensor"

# EV / EVSE
CONF_EV_MODE = "ev_mode"
CONF_EV_BATT_KWH = "ev_batt_kwh"
CONF_EV_CURRENT_SOC = "ev_current_soc"
CONF_EV_TARGET_SOC = "ev_target_soc"

CONF_EVSE_START_SWITCH = "evse_start_switch"
CONF_EVSE_STOP_SWITCH = "evse_stop_switch"
CONF_EVSE_CURRENT_NUMBER = "evse_current_number"
CONF_EVSE_MIN_A = "evse_min_a"
CONF_EVSE_MAX_A = "evse_max_a"
CONF_EVSE_PHASES = "evse_phases"
CONF_EVSE_VOLTAGE = "evse_voltage"
CONF_EVSE_POWER_SENSOR = "evse_power_sensor"  # Charging power in kW or W
CONF_EVSE_ENERGY_SENSOR = "evse_energy_sensor"  # Energy charged this session in kWh or Wh
CONF_EVSE_TOTAL_ENERGY_SENSOR = "evse_total_energy_sensor"  # Total energy counter in kWh

# Forecast.Solar
CONF_FS_USE = "fs_use"
CONF_FS_APIKEY = "fs_apikey"
CONF_FS_LAT = "fs_lat"
CONF_FS_LON = "fs_lon"
CONF_FS_PLANES = "fs_planes"
CONF_FS_HORIZON = "fs_horizon"

# Forecast source selection
CONF_FORECAST_SOURCE = "forecast_source"  # "forecast_solar" or "manual_physics"

# Weather entity for manual forecast
CONF_WEATHER_ENTITY = "weather_entity"
CONF_CLOUD_0_FACTOR = "cloud_0_factor"
CONF_CLOUD_100_FACTOR = "cloud_100_factor"

# Manual forecast settings
CONF_MANUAL_STEP_MINUTES = "manual_step_minutes"
CONF_MANUAL_DIFFUSE_SKY_VIEW_FACTOR = "manual_diffuse_sky_view_factor"
CONF_MANUAL_TEMP_COEFF = "manual_temp_coeff_pct_per_c"
CONF_MANUAL_INVERTER_AC_CAP = "manual_inverter_ac_kw_cap"
CONF_MANUAL_CALIBRATION_ENABLED = "manual_calibration_enabled"

# PV actual (frivilligt)
CONF_PV_POWER_ENTITY = "pv_power_entity"               # W/kW/MW
CONF_PV_ENERGY_TODAY_ENTITY = "pv_energy_today_entity" # Wh/kWh/MWh

# Huslast-baseline
CONF_RUNTIME_SOURCE = "runtime_source"  # power_w | counter_kwh | manual_dayparts
CONF_RUNTIME_COUNTER_ENTITY = "runtime_counter_entity"
CONF_RUNTIME_POWER_ENTITY = "runtime_power_entity"
CONF_RUNTIME_ALPHA = "runtime_alpha"
CONF_RUNTIME_WINDOW_MIN = "runtime_window_min"
CONF_RUNTIME_EXCLUDE_EV = "runtime_exclude_ev"
CONF_RUNTIME_EXCLUDE_BATT_GRID = "runtime_exclude_batt_grid"
CONF_RUNTIME_SOC_FLOOR = "runtime_soc_floor"
CONF_RUNTIME_SOC_CEILING = "runtime_soc_ceiling"

# Kontextsensors för exkludering
CONF_LOAD_POWER_ENTITY = "load_power_entity"  # W
CONF_BATT_POWER_ENTITY = "batt_power_entity"  # W (+ ladd, - urladd)
CONF_GRID_IMPORT_TODAY_ENTITY = "grid_import_today_entity"  # kWh (frivillig)

# Internt store
STORE_ENTITIES = "entities"  # {"number_ev_target_soc": "number.xxx", ...}
STORE_MANUAL = "manual"      # manuella värden för EV/batteri/EVSE

# Nycklar i STORE_MANUAL (uppdateras av Number/Select)
M_EV_BATT_KWH = "ev_batt_kwh"
M_EV_CURRENT_SOC = "ev_current_soc"
M_EV_TARGET_SOC = "ev_target_soc"
M_HOME_BATT_CAP_KWH = "home_batt_cap_kwh"
M_HOME_BATT_SOC_FLOOR = "home_batt_soc_floor"
M_EVSE_MAX_A = "evse_max_a"
M_EVSE_PHASES = "evse_phases"
M_EVSE_VOLTAGE = "evse_voltage"

# Events
EVENT_ACTION = "energy_dispatcher.action"
