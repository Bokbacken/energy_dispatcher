"""
Energy Dispatcher - __init__.py

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
    # Grundstruktur i hass.data
    hass.data.setdefault(DOMAIN, {})
    store = hass.data[DOMAIN].setdefault(
        entry.entry_id,
        {
            "config": {**entry.data, **entry.options},
            "flags": {"auto_ev_enabled": True, "auto_planner_enabled": True},
            # Battery Energy Cost (WACE)
            "wace": 0.0,
            "wace_tot_energy_kwh": 0.0,
            "wace_tot_cost_sek": 0.0,
        },
    )

    # Uppdatera config automatiskt när options ändras
    async def _update_listener(hass: HomeAssistant, updated_entry: ConfigEntry):
        st = hass.data[DOMAIN].get(updated_entry.entry_id)
        if st is not None:
            st["config"] = {**updated_entry.data, **updated_entry.options}
            coord = st.get("coordinator")
            if coord:
                await coord.async_request_refresh()

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    # Koordinator
    coordinator = EnergyDispatcherCoordinator(hass)
    coordinator.entry_id = entry.entry_id
    store["coordinator"] = coordinator
    await coordinator.async_config_entry_first_refresh()

    # Batteri-adapter (Huawei i MVP)
    battery_adapter: Optional[BatteryAdapter] = None
    batt_adapter_type = store["config"].get(CONF_BATT_ADAPTER, "huawei")
    if batt_adapter_type == "huawei":
        device_id = store["config"].get(CONF_HUAWEI_DEVICE_ID)
        if not device_id:
            _LOGGER.warning("Huawei device_id saknas; forced charge fungerar ej.")
        battery_adapter = HuaweiBatteryAdapter(hass, device_id=device_id or "")

    # EVSE-adapter (generisk: start/stop-switch + current number)
    evse_adapter: Optional[EVSEAdapter] = None
    start_sw = store["config"].get(CONF_EVSE_START_SWITCH)
    stop_sw = store["config"].get(CONF_EVSE_STOP_SWITCH)
    num_current = store["config"].get(CONF_EVSE_CURRENT_NUMBER)
    if start_sw and stop_sw and num_current:
        evse_adapter = GenericEVSEAdapter(
            hass,
            start_switch=start_sw,
            stop_switch=stop_sw,
            current_number=num_current,
            min_a=int(store["config"].get(CONF_EVSE_MIN_A, 6)),
            max_a=int(store["config"].get(CONF_EVSE_MAX_A, 16)),
        )
    else:
        _LOGGER.info("EVSE-entities ej konfigurerade; EV-styrning avaktiverad i MVP.")

    # EV manual
    ev_manual = None
    if store["config"].get(CONF_EV_MODE, "manual") == "manual":
        ev_manual = EVManualAdapter(
            ev_batt_kwh=float(store["config"].get(CONF_EV_BATT_KWH, 75.0)),
            ev_current_soc=float(store["config"].get(CONF_EV_CURRENT_SOC, 40.0)),
            ev_target_soc=float(store["config"].get(CONF_EV_TARGET_SOC, 80.0)),
            phases=int(store["config"].get(CONF_EVSE_PHASES, 3)),
            voltage=int(store["config"].get(CONF_EVSE_VOLTAGE, 230)),
            max_a=int(store["config"].get(CONF_EVSE_MAX_A, 16)),
        )

    # Dispatcher
    dispatcher = Dispatcher(hass, battery=battery_adapter, evse=evse_adapter)

    # Uppdatera store
    store.update(
        {
            "battery": battery_adapter,
            "evse": evse_adapter,
            "ev_manual": ev_manual,
            "dispatcher": dispatcher,
        }
    )

    # Override-event
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
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Override 'until' kunde ej parsas: %s", until_iso)
        if key and until_dt:
            dispatcher.set_override(key, until_dt)
            if forced_current and hasattr(dispatcher, "set_forced_ev_current"):
                dispatcher.set_forced_ev_current(int(forced_current))
            _LOGGER.info("Override satt: %s till %s", key, until_dt)

    hass.bus.async_listen("energy_dispatcher/override", _on_override_event)

    # Services
    async def _svc_set_manual_ev(call):
        soc_current = float(call.data.get("soc_current", 40))
        soc_target = float(call.data.get("soc_target", 80))
        st = hass.data[DOMAIN][entry.entry_id]
        manual: EVManualAdapter = st.get("ev_manual")
        if manual:
            manual.ev_current_soc = soc_current
            manual.ev_target_soc = soc_target
            _LOGGER.info("Manual EV uppdaterad: current=%s target=%s", soc_current, soc_target)

    hass.services.async_register(DOMAIN, "set_manual_ev", _svc_set_manual_ev)

    async def _svc_ev_force_charge(call):
        duration = int(call.data.get("duration", 60))
        current = int(call.data.get("current", 16))
        until = datetime.now() + timedelta(minutes=duration)
        dispatcher.set_override("ev_force_until", until)
        if hasattr(dispatcher, "set_forced_ev_current"):
            dispatcher.set_forced_ev_current(current)
        st = hass.data[DOMAIN][entry.entry_id]
        evse: Optional[EVSEAdapter] = st.get("evse")
        if evse:
            await evse.async_set_current(current)
            await evse.async_start()
        _LOGGER.info("EV force charge i %sm @ %sA", duration, current)

    hass.services.async_register(DOMAIN, "ev_force_charge", _svc_ev_force_charge)

    async def _svc_ev_pause(call):
        duration = int(call.data.get("duration", 30))
        until = datetime.now() + timedelta(minutes=duration)
        dispatcher.set_override("ev_pause_until", until)
        st = hass.data[DOMAIN][entry.entry_id]
        evse: Optional[EVSEAdapter] = st.get("evse")
        if evse:
            await evse.async_stop()
        _LOGGER.info("EV paus i %s min", duration)

    hass.services.async_register(DOMAIN, "ev_pause", _svc_ev_pause)

    async def _svc_force_battery_charge(call):
        power_w = int(call.data.get("power_w", 10000))
        duration = int(call.data.get("duration", 60))
        st = hass.data[DOMAIN][entry.entry_id]
        batt: Optional[BatteryAdapter] = st.get("battery")
        if batt and batt.supports_forced_charge():
            await batt.async_force_charge(power_w=power_w, duration_min=duration)
            dispatcher.set_override("battery_force_until", datetime.now() + timedelta(minutes=duration))
            _LOGGER.info("Battery forcible charge: %s W i %s min", power_w, duration)
        else:
            _LOGGER.warning("Battery adapter saknas eller stödjer ej forced charge.")

    hass.services.async_register(DOMAIN, "force_battery_charge", _svc_force_battery_charge)

    # Battery Energy Cost (manuellt tills vi har auto)
    async def _svc_battery_cost_reset(call):
        st = hass.data[DOMAIN][entry.entry_id]
        st["wace"] = 0.0
        st["wace_tot_energy_kwh"] = 0.0
        st["wace_tot_cost_sek"] = 0.0
        _LOGGER.info("Battery Energy Cost återställd.")
        await coordinator.async_request_refresh()

    async def _svc_battery_cost_add(call):
        """
        Parametrar:
          - energy_kwh: float (krävs)
          - price_sek_per_kwh: float (valfritt)
          - total_cost_sek: float (valfritt om price saknas)
        """
        st = hass.data[DOMAIN][entry.entry_id]
        energy_kwh = float(call.data.get("energy_kwh", 0.0))
        price = call.data.get("price_sek_per_kwh")
        total_cost = call.data.get("total_cost_sek")

        if energy_kwh <= 0.0:
            _LOGGER.warning("battery_cost_add: energy_kwh måste vara > 0")
            return

        if price is None and total_cost is None:
            _LOGGER.warning("battery_cost_add: ange price_sek_per_kwh eller total_cost_sek")
            return

        if total_cost is None:
            total_cost = float(price) * energy_kwh
        else:
            total_cost = float(total_cost)

        st["wace_tot_energy_kwh"] = float(st.get("wace_tot_energy_kwh", 0.0)) + energy_kwh
        st["wace_tot_cost_sek"] = float(st.get("wace_tot_cost_sek", 0.0)) + total_cost
        if st["wace_tot_energy_kwh"] > 0:
            st["wace"] = round(st["wace_tot_cost_sek"] / st["wace_tot_energy_kwh"], 6)
        _LOGGER.info(
            "Battery Energy Cost uppdaterad: +%.3f kWh, +%.2f SEK ⇒ WACE=%.4f (E=%.3f kWh, C=%.2f SEK)",
            energy_kwh, total_cost, st["wace"], st["wace_tot_energy_kwh"], st["wace_tot_cost_sek"]
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "battery_cost_reset", _svc_battery_cost_reset)
    hass.services.async_register(DOMAIN, "battery_cost_add", _svc_battery_cost_add)

    # Ladda plattformar
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
