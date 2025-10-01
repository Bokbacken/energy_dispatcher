from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from .const import *
from .coordinator import EnergyDispatcherCoordinator
from .adapters.huawei import HuaweiBatteryAdapter
from .models import PriceSeries, Period

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "switch", "button"]

def _to_ts(hass: HomeAssistant, s: str) -> float:
    return hass.helpers.template.time.as_datetime(s).timestamp()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    cfg = dict(entry.data)

    # Build battery adapter
    brand = cfg.get(CONF_BATTERY_BRAND, "huawei")
    if brand == "huawei":
        batt = HuaweiBatteryAdapter(hass, cfg)
    else:
        _LOGGER.error("Battery brand '%s' not implemented yet", brand)
        return False

    def get_price_series():
        periods: list[Period] = []

        combined = cfg.get(CONF_PRICE_COMBINED_ENTITY) or ""
        today = cfg.get(CONF_PRICE_TODAY_ENTITY) or ""
        tomorrow = cfg.get(CONF_PRICE_TOMORROW_ENTITY) or ""

        def _to_ts_safe(v):
            try:
                return _to_ts(hass, v)
            except Exception:
                return None

        # Combined sensor path
        if combined:
            st = hass.states.get(combined)
            if not st:
                _LOGGER.warning("Combined price entity not found: %s", combined)
            else:
                raw_today = st.attributes.get("raw_today") or []
                raw_tomorrow = st.attributes.get("raw_tomorrow") or []
                rows = list(raw_today) + list(raw_tomorrow)
                for r in rows:
                    start_ts = _to_ts_safe(r.get("start"))
                    if start_ts is None:
                        continue
                    end_val = r.get("end")
                    end_ts = _to_ts_safe(end_val) if end_val else (start_ts + 3600.0)
                    price_val = r.get("price", r.get("value", None))
                    if price_val is None:
                        continue
                    try:
                        price = float(price_val)
                    except Exception:
                        continue
                    periods.append(Period(start_ts, end_ts, price))

        # Split sensors fallback
        def read_periods(entity_id: str):
            out = []
            if not entity_id:
                return out
            st2 = hass.states.get(entity_id)
            if st2 and isinstance(st2.attributes.get("data"), list):
                for p in st2.attributes["data"]:
                    start_ts = _to_ts_safe(p.get("start"))
                    end_ts = _to_ts_safe(p.get("end"))
                    try:
                        price = float(p.get("price"))
                    except Exception:
                        continue
                    if start_ts is None or end_ts is None:
                        continue
                    out.append(Period(start_ts, end_ts, price))
            return out

        if not periods:
            periods += read_periods(today)
            periods += read_periods(tomorrow)

        return PriceSeries(periods=periods)

    coordinator = EnergyDispatcherCoordinator(hass, get_price_series, batt, {
        "battery_capacity_kwh": cfg.get(CONF_BATTERY_CAPACITY_KWH, DEFAULT_BATTERY_CAPACITY_KWH),
        "battery_eff": cfg.get(CONF_BATTERY_EFF, DEFAULT_BATTERY_EFF),
        "morning_soc_target": cfg.get(CONF_MORNING_SOC_TARGET, DEFAULT_MORNING_SOC_TARGET),
        "soc_floor": cfg.get(CONF_SOC_FLOOR, DEFAULT_SOC_FLOOR),
        "max_grid_charge_kw": cfg.get(CONF_MAX_GRID_CHARGE_KW, DEFAULT_MAX_GRID_CHARGE_KW),
        "bec_margin": cfg.get(CONF_BEC_MARGIN, DEFAULT_BEC_MARGIN_KR_PER_KWH),
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

    # Forward platforms
    for platform in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, platform))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
