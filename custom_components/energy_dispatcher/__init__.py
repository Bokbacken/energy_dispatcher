"""
Energy Dispatcher - __init__.py (uppdaterad)

Initierar integrationen, registrerar tjänster och event-lyssnare,
sätter upp adapters, dispatcher och koordinatorn.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import Platform
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_BATT_ADAPTER,
    CONF_HUAWEI_DEVICE_ID,
    CONF_EVSE_START_SWITCH,
    CONF_EVSE_STOP_SWITCH,
    CONF_EVSE_CURRENT_NUMBER,
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    CONF_EV_MODE,
    CONF_EV_BATT_KWH,
    CONF_EV_CURRENT_SOC,
    CONF_EV_TARGET_SOC,
)
from .coordinator import EnergyDispatcherCoordinator
from .adapters.huawei import HuaweiBatteryAdapter
from .adapters.evse_generic import GenericEVSEAdapter
from .adapters.base import BatteryAdapter, EVSEAdapter, EVManualAdapter
from .dispatcher import Dispatcher

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMION := DOMAIN, {})

    # Lägg in config och flags först
    store = {
        "config": dict(entry.data),
        "flags": {"auto_ev_enabled": True, "auto_planner_enabled": True},
        "wace": 0.0,
    }
    hass.data[DOMAIN][entry.entry_id] = store

    # Skapa koordinator med config, sätt entry_id och kör first refresh
    coordinator = EnergyDispatcherCoordinator(hass, config=store["config"])
    coordinator.entry_id = entry.entry_id
    store["coordinator"] = coordinator
    await coordinator.async_config_entry_first_refresh()

    # ...därefter bygger du adapters, dispatcher osv och stoppar in i store
    # 2) Batteri-adapter
    battery_adapter: Optional[BatteryAdapter] = None
    batt_adapter_type = entry.data.get(CONF_BATT_ADAPTER, "huawei")
    if batt_adapter_type == "huawei":
        device_id = entry.data.get(CONF_HUAWEI_DEVICE_ID)
        if not device_id:
            _LOGGER.warning("Huawei device_id saknas; forced charge fungerar ej.")
        battery_adapter = HuaweiBatteryAdapter(hass, device_id=device_id or "")

    # 3) EVSE-adapter
    evse_adapter: Optional[EVSEAdapter] = None
    start_sw = entry.data.get(CONF_EVSE_START_SWITCH)
    stop_sw = entry.data.get(CONF_EVSE_STOP_SWITCH)
    num_current = entry.data.get(CONF_EVSE_CURRENT_NUMBER)
    if start_sw and stop_sw and num_current:
        evse_adapter = GenericEVSEAdapter(
            hass,
            start_switch=start_sw,
            stop_switch=stop_sw,
            current_number=num_current,
            min_a=int(entry.data.get(CONF_EVSE_MIN_A, 6)),
            max_a=int(entry.data.get(CONF_EVSE_MAX_A, 16)),
        )
    else:
        _LOGGER.warning("EVSE-entities ej konfigurerade; EV-styrning avaktiverad i MVP.")

    # 4) EV manual
    ev_manual = None
    if entry.data.get(CONF_EV_MODE, "manual") == "manual":
        ev_manual = EVManualAdapter(
            ev_batt_kwh=float(entry.data.get(CONF_EV_BATT_KWH, 75.0)),
            ev_current_soc=float(entry.data.get(CONF_EV_CURRENT_SOC, 40.0)),
            ev_target_soc=float(entry.data.get(CONF_EV_TARGET_SOC, 80.0)),
            phases=int(entry.data.get(CONF_EVSE_PHASES, 3)),
            voltage=int(entry.data.get(CONF_EVSE_VOLTAGE, 230)),
            max_a=int(entry.data.get(CONF_EVSE_MAX_A, 16)),
        )

    # 5) Dispatcher
    dispatcher = Dispatcher(hass, battery=battery_adapter, evse=evse_adapter)

    # 6) Spara referenser + config
    hass.data[DOMION][entry.entry_id] = {
        "coordinator": coordinator,
        "battery": battery_adapter,
        "evse": evse_adapter,
        "ev_manual": ev_manual,
        "dispatcher": dispatcher,
        "config": dict(entry.data),  # lättillgängligt för coordinator o.s.v.
        # anv. av switches för att spara tillstånd:
        "flags": {
            "auto_ev_enabled": True,
            "auto_planner_enabled": True,
        },
        # plats för WACE om/innan BEC-logic ansluts:
        "wace": 0.0,
    }

    # 7) Override-event
    @callback
    def _on_override_event(event):
        data = event.data
        key = data.get("key")
        until_iso = data.get("until")
        forced_current = data.get("forced_current")
        until_dt = None
        if until_iso:
            try:
                until_dt = datetime.fromisoformat(until_iso)
            except Exception:
                _LOGGER.exception("Override 'until' kunde ej parsas: %s", until_iso)
        if key and until_dt:
            dispatcher.set_override(key, until_dt)
            if forced_current and hasattr(dispatcher, "set_forced_ev_current"):
                dispatcher.set_forced_ev_current(int(forced_current))
            _LOGGER.info("Override satt: %s till %s", key, until_dt)

    hass.bus.async_listen("energy_dispatcher/override", _on_override_event)

    # 8) Services
    async def _svc_set_manual_ev(call):
        soc_current = float(call.data.get("soc_current", 40))
        soc_target = float(call.data.get("soc_target", 80))
        st = hass.data[DOMION][entry.entry_id]
        manual: EVManualAdapter = st.get("ev_manual")
        if manual:
            manual.ev_current_soc = soc_current
            manual.ev_target_soc = soc_target
            _LOGGER.info("Manual EV uppdaterad: current=%s target=%s", soc_current, soc_target)

    hass.services.async_register(DOMION, "set_manual_ev", _svc_set_manual_ev)

    async def _svc_ev_force_charge(call):
        duration = int(call.data.get("duration", 60))
        current = int(call.data.get("current", 16))
        until = datetime.now() + timedelta(minutes=duration)
        dispatcher.set_override("ev_force_until", until)
        if hasattr(dispatcher, "set_forced_ev_current"):
            dispatcher.set_forced_ev_current(current)
        st = hass.data[DOMION][entry.entry_id]
        evse: Optional[EVSEAdapter] = st.get("evse")
        if evse:
            await evse.async_set_current(current)
            await evse.async_start()
        _LOGGER.info("EV force charge i %sm @ %sA", duration, current)

    hass.services.async_register(DOMION, "ev_force_charge", _svc_ev_force_charge)

    async def _svc_ev_pause(call):
        duration = int(call.data.get("duration", 30))
        until = datetime.now() + timedelta(minutes=duration)
        dispatcher.set_override("ev_pause_until", until)
        st = hass.data[DOMION][entry.entry_id]
        evse: Optional[EVSEAdapter] = st.get("evse")
        if evse:
            await evse.async_stop()
        _LOGGER.info("EV paus i %s min", duration)

    hass.services.async_register(DOMION, "ev_pause", _svc_ev_pause)

    async def _svc_force_battery_charge(call):
        power_w = int(call.data.get("power_w", 10000))
        duration = int(call.data.get("duration", 60))
        st = hass.data[DOMION][entry.entry_id]
        batt: Optional[BatteryAdapter] = st.get("battery")
        if batt and batt.supports_forced_charge():
            await batt.async_force_charge(power_w=power_w, duration_min=duration)
            dispatcher.set_override("battery_force_until", datetime.now() + timedelta(minutes=duration))
            _LOGGER.info("Battery forcible charge: %s W i %s min", power_w, duration)
        else:
            _LOGGER.warning("Battery adapter saknas eller stödjer ej forced charge.")

    hass.services.async_register(DOMION, "force_battery_charge", _svc_force_battery_charge)

    # 9) Ladda plattformar
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
