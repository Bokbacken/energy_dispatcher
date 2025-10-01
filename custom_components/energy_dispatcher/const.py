DOMAIN = "energy_dispatcher"

# Update cadence (15 min slots)
DISPATCH_INTERVAL_SECONDS = 15 * 60
PLAN_REFRESH_SECONDS = 15 * 60

# Defaults
DEFAULT_SOC_FLOOR = 25.0
DEFAULT_MORNING_SOC_TARGET = 65.0
DEFAULT_MAX_GRID_CHARGE_KW = 8.0
DEFAULT_BATTERY_CAPACITY_KWH = 30.0
DEFAULT_BATTERY_EFF = 0.92
DEFAULT_BEC_MARGIN_KR_PER_KWH = 0.10
DEFAULT_PRICE_LOW_PERCENTILE = 25.0

CONF_BATTERY_BRAND = "battery_brand"
CONF_BATTERY_SOC_ENTITY = "battery_soc_entity"
CONF_PV_POWER_ENTITY = "pv_power_entity"
CONF_HOUSE_LOAD_ENTITY = "house_load_entity"
CONF_PRICE_TODAY_ENTITY = "price_today_entity"
CONF_PRICE_TOMORROW_ENTITY = "price_tomorrow_entity"
CONF_IMPORT_LIMIT_KW = "import_limit_kw"

CONF_SOC_FLOOR = "soc_floor"
CONF_MORNING_SOC_TARGET = "morning_soc_target"
CONF_MAX_GRID_CHARGE_KW = "max_grid_charge_kw"
CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
CONF_BATTERY_EFF = "battery_eff"
CONF_BEC_MARGIN = "bec_margin"
CONF_PRICE_LOW_PERCENTILE = "price_low_percentile"

CONF_HUAWEI_DEVICE_ID = "huawei_device_id"

# EV config
CONF_EV_MODE = "ev_mode"  # "none" | "evse" | "manual"
CONF_EVSE_SWITCH = "evse_switch"
CONF_EVSE_CURRENT_NUMBER = "evse_current_number"
CONF_EV_MAX_AMPS = "ev_max_amps"
CONF_EV_PHASES = "ev_phases"
CONF_EV_VOLTAGE = "ev_voltage"
CONF_EV_MANUAL_SOC = "ev_manual_soc_helper"
CONF_EV_TARGET = "ev_target_helper"

EV_MODE_NONE = "none"
EV_MODE_EVSE = "evse"
EV_MODE_MANUAL = "manual"

# Entity names
SENSOR_BEC = "sensor.energy_dispatcher_bec"
SENSOR_RUNTIME = "sensor.energy_dispatcher_battery_runtime"
SENSOR_NEXT_CHEAP = "sensor.energy_dispatcher_next_cheap_window"
SWITCH_OPT_BATT = "switch.energy_dispatcher_optimize_battery"
SWITCH_OPT_EV = "switch.energy_dispatcher_optimize_ev"
BUTTON_FORCE_30 = "button.energy_dispatcher_force_batt_charge_30m"
BUTTON_FORCE_60 = "button.energy_dispatcher_force_batt_charge_60m"
BUTTON_FORCE_120 = "button.energy_dispatcher_force_batt_charge_120m"
SWITCH_PAUSE = "switch.energy_dispatcher_pause"

SERVICE_FORCE_CHARGE = "force_batt_charge"
SERVICE_STOP_CHARGE = "stop_batt_charge"
