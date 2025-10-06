from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PLATFORMS,
    STORE_MANUAL,
    STORE_ENTITIES,
    CONF_EV_CURRENT_SOC,
    CONF_EV_TARGET_SOC,
    CONF_EV_BATT_KWH,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    CONF_BATT_CAP_KWH,
    CONF_BATT_CAPACITY_ENTITY,
    M_EV_CURRENT_SOC,
    M_EV_TARGET_SOC,
    M_EV_BATT_KWH,
    M_EVSE_MAX_A,
    M_EVSE_PHASES,
    M_EVSE_VOLTAGE,
    M_HOME_BATT_CAP_KWH,
    M_HOME_BATT_SOC_FLOOR,
)
from .coordinator import EnergyDispatcherCoordinator
from .ev_dispatcher import EVDispatcher
from .bec import BatteryEnergyCost

_LOGGER = logging.getLogger(__name__)


async def _async_register_services(hass: HomeAssistant):
    """Register services for Energy Dispatcher."""
    
    # Only register once
    if hass.services.has_service(DOMAIN, "battery_cost_reset"):
        return

    async def handle_battery_cost_reset(call):
        """Handle battery cost reset service call."""
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if isinstance(data, dict) and "bec" in data:
                bec = data["bec"]
                bec.reset_cost()
                await bec.async_save()
                # Update legacy storage for backward compatibility
                data["wace"] = bec.wace
                data["wace_tot_energy_kwh"] = bec.energy_kwh
                data["wace_tot_cost_sek"] = bec.get_total_cost()
                _LOGGER.info("Battery cost reset for entry %s", entry_id)

    async def handle_battery_cost_set_soc(call):
        """Handle battery SOC set service call."""
        soc_percent = call.data.get("soc_percent")
        if soc_percent is None:
            _LOGGER.error("SOC percentage not provided")
            return
            
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if isinstance(data, dict) and "bec" in data:
                bec = data["bec"]
                bec.set_soc(soc_percent)
                await bec.async_save()
                # Update legacy storage for backward compatibility
                data["wace"] = bec.wace
                data["wace_tot_energy_kwh"] = bec.energy_kwh
                data["wace_tot_cost_sek"] = bec.get_total_cost()
                _LOGGER.info("Battery SOC set to %.1f%% for entry %s", soc_percent, entry_id)

    hass.services.async_register(
        DOMAIN,
        "battery_cost_reset",
        handle_battery_cost_reset
    )
    
    hass.services.async_register(
        DOMAIN,
        "battery_cost_set_soc",
        handle_battery_cost_set_soc
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    # Slå ihop data + options till aktuell konfig
    config: Dict[str, Any] = {**entry.data, **(entry.options or {})}

    coordinator = EnergyDispatcherCoordinator(hass)
    coordinator.entry_id = entry.entry_id

    cfg_lookup = lambda key, default=None: hass.data[DOMAIN][entry.entry_id]["config"].get(key, default)
    dispatcher = EVDispatcher(hass=hass, cfg_lookup=cfg_lookup, entry_id=entry.entry_id)

    # Initialize STORE_MANUAL with values from config if they exist
    # This ensures config_flow values are properly saved
    manual_store = {}
    if CONF_EV_CURRENT_SOC in config:
        manual_store[M_EV_CURRENT_SOC] = float(config[CONF_EV_CURRENT_SOC])
    if CONF_EV_TARGET_SOC in config:
        manual_store[M_EV_TARGET_SOC] = float(config[CONF_EV_TARGET_SOC])
    if CONF_EV_BATT_KWH in config:
        manual_store[M_EV_BATT_KWH] = float(config[CONF_EV_BATT_KWH])
    if CONF_EVSE_MAX_A in config:
        manual_store[M_EVSE_MAX_A] = float(config[CONF_EVSE_MAX_A])
    if CONF_EVSE_PHASES in config:
        manual_store[M_EVSE_PHASES] = float(config[CONF_EVSE_PHASES])
    if CONF_EVSE_VOLTAGE in config:
        manual_store[M_EVSE_VOLTAGE] = float(config[CONF_EVSE_VOLTAGE])
    if CONF_BATT_CAP_KWH in config:
        manual_store[M_HOME_BATT_CAP_KWH] = float(config[CONF_BATT_CAP_KWH])

    # Initialize Battery Energy Cost tracker
    # Try to get capacity from sensor first, fall back to manual config
    battery_capacity = config.get(CONF_BATT_CAP_KWH, 15.0)
    capacity_entity = config.get(CONF_BATT_CAPACITY_ENTITY, "")
    if capacity_entity:
        state = hass.states.get(capacity_entity)
        if state and state.state not in (None, "", "unknown", "unavailable"):
            try:
                sensor_capacity = float(state.state)
                if sensor_capacity > 0:
                    battery_capacity = sensor_capacity
                    _LOGGER.info("Using battery capacity from sensor %s: %.2f kWh", capacity_entity, battery_capacity)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid capacity value from sensor %s, using manual capacity", capacity_entity)
    
    bec = BatteryEnergyCost(hass, capacity_kwh=battery_capacity)
    await bec.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "config": config,
        "flags": {"auto_ev_enabled": True, "auto_planner_enabled": True},
        "coordinator": coordinator,
        "dispatcher": dispatcher,
        "bec": bec,
        STORE_MANUAL: manual_store,
        STORE_ENTITIES: {},
        # Legacy WACE storage (kept for backward compatibility)
        "wace": bec.wace,
        "wace_tot_energy_kwh": bec.energy_kwh,
        "wace_tot_cost_sek": bec.get_total_cost(),
    }

    await coordinator.async_config_entry_first_refresh()
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_register_services(hass)
    
    _LOGGER.info("Energy Dispatcher %s init complete", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    # Uppdatera sammanslagen konfig i store
    st = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **(entry.options or {})}
    st["config"] = config
    
    # Update STORE_MANUAL with new config values if they changed
    # But only if the value doesn't already exist (don't overwrite manual changes)
    manual_store = st.get(STORE_MANUAL, {})
    if CONF_EV_CURRENT_SOC in config and M_EV_CURRENT_SOC not in manual_store:
        manual_store[M_EV_CURRENT_SOC] = float(config[CONF_EV_CURRENT_SOC])
    if CONF_EV_TARGET_SOC in config and M_EV_TARGET_SOC not in manual_store:
        manual_store[M_EV_TARGET_SOC] = float(config[CONF_EV_TARGET_SOC])
    if CONF_EV_BATT_KWH in config and M_EV_BATT_KWH not in manual_store:
        manual_store[M_EV_BATT_KWH] = float(config[CONF_EV_BATT_KWH])
    if CONF_EVSE_MAX_A in config and M_EVSE_MAX_A not in manual_store:
        manual_store[M_EVSE_MAX_A] = float(config[CONF_EVSE_MAX_A])
    if CONF_EVSE_PHASES in config and M_EVSE_PHASES not in manual_store:
        manual_store[M_EVSE_PHASES] = float(config[CONF_EVSE_PHASES])
    if CONF_EVSE_VOLTAGE in config and M_EVSE_VOLTAGE not in manual_store:
        manual_store[M_EVSE_VOLTAGE] = float(config[CONF_EVSE_VOLTAGE])
    if CONF_BATT_CAP_KWH in config and M_HOME_BATT_CAP_KWH not in manual_store:
        manual_store[M_HOME_BATT_CAP_KWH] = float(config[CONF_BATT_CAP_KWH])
    
    # Refresh så koordinatorn får nya värden
    await st["coordinator"].async_request_refresh()
