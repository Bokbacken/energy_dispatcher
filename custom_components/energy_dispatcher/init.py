from __future__ import annotations
import time, json
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from .const import *
from .coordinator import EnergyDispatcherCoordinator
from .adapters.huawei import HuaweiBatteryAdapter
from .models import PriceSeries, Period

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    cfg = dict(entry.data)

    # Build battery adapter
    if cfg[CONF_BATTERY_BRAND] == "huawei":
        batt = HuaweiBatteryAdapter(hass, cfg)
    else:
        raise NotImplementedError("Generic battery not implemented yet")

    def get_price_series():
        """
        Read price sensors attributes 'data' which should be a list of {start, end, price} ISO strings.
        Merge today+tomorrow into a single list and convert to epoch seconds.
        """
        def read_periods(entity_id: str):
            st = hass.states.get(entity_id)
            data = []
            if st and isinstance(st.attributes.get("data"), list):
                for p in st.attributes["data"]:
                    try:
                        start_ts = hass.helpers.template.time.as_datetime(p["start"]).timestamp()
                        end_ts = hass.helpers.template.time.as_datetime(p["end"]).timestamp()
                        price = float(p["price"])
                        data.append(Period(start_ts, end_ts, price))
                    except Exception:
                        continue
            return data
        periods = read_periods(cfg[CONF_PRICE_TODAY_ENTITY]) + read_periods(cfg[CONF_PRICE_TOMORROW_ENTITY])
        return PriceSeries(periods=periods)

    coordinator = EnergyDispatcherCoordinator(hass, get_price_series, batt, {
        "battery_capacity_kwh": cfg[CONF_BATTERY_CAPACITY_KWH],
        "battery_eff": cfg[CONF_BATTERY_EFF],
        "morning_soc_target": cfg[CONF_MORNING_SOC_TARGET],
        "soc_floor": cfg[CONF_SOC_FLOOR],
        "max_grid_charge_kw": cfg[CONF_MAX_GRID_CHARGE_KW],
        "bec_margin": cfg[CONF_BEC_MARGIN],
    })
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "batt": batt,
    }

    # Register services
    async def _svc_force(call):
        minutes = int(call.data.get("minutes", 15))
        power_kw = float(call.data.get("power_kw", 6.0))
        await batt.force_charge(minutes, power_kw)

    async def _svc_stop(call):
        await batt.stop_charge()

    hass.services.async_register(DOMAIN, SERVICE_FORCE_CHARGE, _svc_force)
    hass.services.async_register(DOMAIN, SERVICE_STOP_CHARGE, _svc_stop)

    # Periodic dispatch tick every minute
    async def _tick(now):
        await coordinator.async_tick_dispatch()
    async_track_time_interval(hass, _tick, timedelta(seconds=60))

    hass.config_entries.async_setup_platforms(entry, ["sensor", "switch", "button"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload = await hass.config_entries.async_unload_platforms(entry, ["sensor", "switch", "button"])
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload
