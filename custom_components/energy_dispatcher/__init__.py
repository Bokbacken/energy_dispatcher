from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import EnergyDispatcherCoordinator
from .ev_dispatcher import EVDispatcher

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    # Slå ihop data + options till aktuell konfig
    config: Dict[str, Any] = {**entry.data, **(entry.options or {})}

    coordinator = EnergyDispatcherCoordinator(hass)
    coordinator.entry_id = entry.entry_id

    dispatcher = EVDispatcher(
        hass=hass,
        cfg_lookup=lambda key, default=None: hass.data[DOMAIN][entry.entry_id]["config"].get(key, default),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "config": config,
        "flags": {"auto_ev_enabled": True},
        "coordinator": coordinator,
        "dispatcher": dispatcher,
        # WACE m.m. lagras här om du använder tjänsterna
        "wace": 0.0,
        "wace_tot_energy_kwh": 0.0,
        "wace_tot_cost_sek": 0.0,
    }

    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
    st["config"] = {**entry.data, **(entry.options or {})}
    # Refresh så koordinatorn får nya värden
    await st["coordinator"].async_request_refresh()
