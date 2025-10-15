from homeassistant.const import Platform

DOMAIN = "energy_dispatcher"

# Dashboard configuration
CONF_AUTO_CREATE_DASHBOARD = "auto_create_dashboard"

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
CONF_BATT_MAX_CHARGE_POWER_ENTITY = "batt_max_charge_power_entity"  # Sensor for max charge power (W)
CONF_BATT_MAX_DISCH_POWER_ENTITY = "batt_max_disch_power_entity"  # Sensor for max discharge power (W)
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
CONF_PV_TOTAL_ENERGY_ENTITY = "pv_total_energy_entity" # Total kWh Solar generation counter

# Batteri total energy
CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY = "batt_total_charged_energy_entity"  # Total kWh battery charging counter

# Huslast-baseline (simplified to only use energy counters)
CONF_RUNTIME_COUNTER_ENTITY = "runtime_counter_entity"  # Total kWh House Load counter
# Legacy EMA parameters (kept for backward compatibility, not exposed in UI)
CONF_RUNTIME_ALPHA = "runtime_alpha"  # EMA smoothing factor (0-1) - only used when lookback_hours=0
CONF_RUNTIME_WINDOW_MIN = "runtime_window_min"  # Calculation window (minutes) - only used in bootstrap
CONF_RUNTIME_EXCLUDE_EV = "runtime_exclude_ev"
CONF_RUNTIME_EXCLUDE_BATT_GRID = "runtime_exclude_batt_grid"
CONF_RUNTIME_SOC_FLOOR = "runtime_soc_floor"
CONF_RUNTIME_SOC_CEILING = "runtime_soc_ceiling"

# Cost strategy
CONF_USE_DYNAMIC_COST_THRESHOLDS = "use_dynamic_cost_thresholds"  # bool
CONF_COST_CHEAP_THRESHOLD = "cost_cheap_threshold"  # SEK/kWh
CONF_COST_HIGH_THRESHOLD = "cost_high_threshold"    # SEK/kWh

# Appliance optimization
CONF_ENABLE_APPLIANCE_OPTIMIZATION = "enable_appliance_optimization"
CONF_DISHWASHER_POWER_W = "dishwasher_power_w"
CONF_WASHING_MACHINE_POWER_W = "washing_machine_power_w"
CONF_WATER_HEATER_POWER_W = "water_heater_power_w"

# Weather-aware optimization
CONF_ENABLE_WEATHER_OPTIMIZATION = "enable_weather_optimization"

# Export profitability settings
CONF_EXPORT_MODE = "export_mode"  # never, excess_solar_only, peak_price_opportunistic
CONF_MIN_EXPORT_PRICE_SEK_PER_KWH = "min_export_price_sek_per_kwh"  # SEK/kWh
CONF_BATTERY_DEGRADATION_COST_PER_CYCLE_SEK = "battery_degradation_cost_per_cycle_sek"  # SEK

# Load shifting optimization
CONF_ENABLE_LOAD_SHIFTING = "enable_load_shifting"  # Boolean
CONF_LOAD_SHIFT_FLEXIBILITY_HOURS = "load_shift_flexibility_hours"  # Hours (default: 6)
CONF_BASELINE_LOAD_W = "baseline_load_w"  # Watts (default: 300)

# Peak shaving
CONF_ENABLE_PEAK_SHAVING = "enable_peak_shaving"  # Boolean
CONF_PEAK_THRESHOLD_W = "peak_threshold_w"  # Watts (default: 10000)

# Comfort-aware optimization
CONF_COMFORT_PRIORITY = "comfort_priority"  # cost_first, balanced, comfort_first
CONF_QUIET_HOURS_START = "quiet_hours_start"  # time (default: 22:00)
CONF_QUIET_HOURS_END = "quiet_hours_end"  # time (default: 07:00)
CONF_MIN_BATTERY_PEACE_OF_MIND = "min_battery_peace_of_mind"  # % (default: 20)

# 48-hour historical baseline
CONF_RUNTIME_LOOKBACK_HOURS = "runtime_lookback_hours"  # Default 48
# Legacy config (no longer used, kept for backwards compatibility)
CONF_RUNTIME_USE_DAYPARTS = "runtime_use_dayparts"  # Deprecated: time-of-day weighting removed

# Kontextsensors för exkludering
CONF_LOAD_POWER_ENTITY = "load_power_entity"  # W
CONF_BATT_POWER_ENTITY = "batt_power_entity"  # W (+ ladd, - urladd)
CONF_BATT_POWER_INVERT_SIGN = "batt_power_invert_sign"  # Invert sign convention (for Huawei-style sensors)
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
