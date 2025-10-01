from __future__ import annotations
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from .const import *
from .coordinator import EnergyDispatcherCoordinator
from .adapters.huawei import HuaweiBatteryAdapter
from .models import PriceSeries, Period

def _to_ts(hass: HomeAssistant, s: str) -> float:
    # robust: handles ISO with timezone
    return hass.helpers.template.time.as_datetime(s).timestamp()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    cfg = dict(entry.data)

    # Build battery adapter
    if cfg[CONF_BATTERY_BRAND] == "huawei":
        batt = HuaweiBatteryAdapter(hass, cfg)
    else:
        raise NotImplementedError("Generic battery not implemented yet")

    def get_price_series():
        """
        Supports either:
          - combined sensor with attributes.raw_today + attributes.raw_tomorrow, or
          - split sensors (today/tomorrow) each with attributes.data [{start, end, price}]
        """
        periods: list[Period] = []

        combined = cfg.get(CONF_PRICE_COMBINED_ENTITY) or ""
        today = cfg.get(CONF_PRICE_TODAY_ENTITY) or ""
        tomorrow = cfg.get(CONF_PRICE_TOMORROW_ENTITY) or ""

        if combined:
            st = hass.states.get(combined)
            if st:
                raw_today = st.attributes.get("raw_today") or []
                raw_tomorrow = st.attributes.get("raw_tomorrow") or []
                rows = list(raw_today) + list(raw_tomorrow)
                for r in rows:
                    try:
                        start_ts = _to_ts(hass, r["start"])
                        # Assume 60-min resolution if end not provided; fallback +3600s
                        end_ts = _to_ts(hass, r["end"]) if "end" in r else (start_ts + 3600.0)
                        price = float(r.get("price", r.get("value", 0.0)))
                        periods.append(Period(start_ts, end_ts, price))
                    except Exception:
                        continue)

        # Fallback/also support split sensors
        def read_periods(entity_id: str):
            st = hass.states.get(entity_id)
            out = []
            if st and isinstance(st.attributes.get("data"), list):
                for p in st.attributes["data"]:
                    try:
                        start_ts = _to_ts(hass, p["start"])
                        end_ts = _to_ts(hass, p["end"])
                        price = float(p["price"])
                        out.append(Period(start_ts, end_ts, price))
                    except Exception:
                        continue
            return out

        if not periods and today:
            periods += read_periods(today)
        if not periods and tomorrow:
            periods += read_periods(tomorrow)

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
