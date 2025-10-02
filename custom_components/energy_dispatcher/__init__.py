"""Init-fil för Energy Dispatcher-integrationen."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_PLAN,
    DOMAIN,
    NAME,
    PLATFORMS,
    SERVICE_FORCE_CHARGE,
    SERVICE_FORCE_DISCHARGE,
    SERVICE_OVERRIDE_PLAN,
    SERVICE_PAUSE_EV_CHARGING,
    SERVICE_RESUME_EV_CHARGING,
    SERVICE_SET_MANUAL_EV_SOC,
)
from .coordinator import EnergyDispatcherCoordinator
from .dispatcher import ActionDispatcher
from .models import EnergyDispatcherRuntimeData
from .planner import EnergyPlanner
from .bec import EnergyDispatcherStore, PriceAndCostHelper

_LOGGER = logging.getLogger(__name__)


async def async_setup(_: HomeAssistant, __: ConfigType) -> bool:
    """YAML-stöd behövs inte, returnera bara True."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initiera integrationen när en config entry skapas/hämtas."""
    hass.data.setdefault(DOMAIN, {})

    try:
        coordinator = EnergyDispatcherCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Energy Dispatcher kunde inte starta: {err}"
        ) from err

    planner = EnergyPlanner()
    store = EnergyDispatcherStore(hass, entry.entry_id)
    dispatcher = ActionDispatcher(hass, coordinator, planner)

    runtime = EnergyDispatcherRuntimeData(
        coordinator=coordinator,
        planner=planner,
        dispatcher=dispatcher,
        store=store,
        hass=hass,
    )
    hass.data[DOMAIN][entry.entry_id] = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass, runtime)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Avregistrera entiteter och tjänster vid borttagning."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime = hass.data[DOMAIN].pop(entry.entry_id)
        runtime.dispatcher.async_unregister_listeners()

    if not hass.data[DOMAIN]:
        _unregister_services(hass)

    return unload_ok


def _register_services(hass: HomeAssistant, runtime: EnergyDispatcherRuntimeData) -> None:
    """Registrera Home Assistant-tjänster."""

    async def _async_wrap(call, handler):
        await handler(call.data)

    if not hass.services.has_service(DOMAIN, SERVICE_FORCE_CHARGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_FORCE_CHARGE,
            lambda call: runtime.dispatcher.async_force_battery_charge(call.data),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_FORCE_DISCHARGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_FORCE_DISCHARGE,
            lambda call: runtime.dispatcher.async_force_battery_discharge(call.data),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE_EV_CHARGING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PAUSE_EV_CHARGING,
            lambda call: runtime.dispatcher.async_pause_ev_charging(call.data),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_EV_CHARGING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESUME_EV_CHARGING,
            lambda call: runtime.dispatcher.async_resume_ev_charging(call.data),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_MANUAL_EV_SOC):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_MANUAL_EV_SOC,
            lambda call: runtime.dispatcher.async_set_manual_ev_soc(call.data),
        )
    if not hass.services.has_service(DOMAIN, SERVICE_OVERRIDE_PLAN):
        hass.services.async_register(
            DOMAIN,
            SERVICE_OVERRIDE_PLAN,
            lambda call: runtime.dispatcher.async_override_plan(call.data),
        )


def _unregister_services(hass: HomeAssistant) -> None:
    """Avregistrera domänens tjänster."""
    for service in (
        SERVICE_FORCE_CHARGE,
        SERVICE_FORCE_DISCHARGE,
        SERVICE_PAUSE_EV_CHARGING,
        SERVICE_RESUME_EV_CHARGING,
        SERVICE_SET_MANUAL_EV_SOC,
        SERVICE_OVERRIDE_PLAN,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
