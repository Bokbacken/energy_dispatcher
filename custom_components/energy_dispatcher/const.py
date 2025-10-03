from homeassistant.const import Platform

DOMAIN = "energy_dispatcher"

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]

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

# Husförbrukning
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

# Forecast.Solar
CONF_FS_USE = "fs_use"
CONF_FS_APIKEY = "fs_apikey"
CONF_FS_LAT = "fs_lat"
CONF_FS_LON = "fs_lon"
CONF_FS_PLANES = "fs_planes"
CONF_FS_HORIZON = "fs_horizon"

# NYTT: faktiska produktionssensorer (frivilliga)
CONF_PV_POWER_ENTITY = "pv_power_entity"               # t.ex. sensor.inverter_pv_power (W eller kW)
CONF_PV_ENERGY_TODAY_ENTITY = "pv_energy_today_entity" # t.ex. sensor.pv_energy_today (Wh eller kWh)
