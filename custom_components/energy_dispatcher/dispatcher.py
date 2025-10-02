"""Utför planerade åtgärder och manuella overrides."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
)
from .models import EnergyPlan
from .bec import EnergyDispatcherStore
from .planner import EnergyPlanner
from .coordinator import EnergyDispatcherCoordinator

_LOGGER = logging.getLogger(__name__)


class ActionDispatcher:
    """Ansvarar för att köra plan/overrides via adaptrar."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EnergyDispatcherCoordinator,
        planner: EnergyPlanner,
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.planner = planner
        self._cancel_callbacks: list[Any] = []

    def async_unregister_listeners(self) -> None:
        for cancel in self._cancel_callbacks:
            cancel()

    async def async_force_battery_charge(self, data: Dict[str, Any]) -> None:
        adapter = self.coordinator._battery_adapter
        if not adapter:
            _LOGGER.warning("Ingen batteriadapter definierad")
            return
        duration = data.get("duration_minutes", 60)
        ampere = data.get("ampere", None)
        await adapter.async_force_charge(duration_minutes=duration, ampere=ampere)

    async def async_force_battery_discharge(self, data: Dict[str, Any]) -> None:
        adapter = self.coordinator._battery_adapter
        if not adapter:
            return
        duration = data.get("duration_minutes", 60)
        await adapter.async_force_discharge(duration_minutes=duration)

    async def async_pause_ev_charging(self, data: Dict[str, Any]) -> None:
        adapter = self.coordinator._ev_adapter
        if not adapter:
            return
        duration = data.get("duration_minutes", None)
        await adapter.async_pause(duration_minutes=duration)

    async def async_resume_ev_charging(self, data: Dict[str, Any]) -> None:
        adapter = self.coordinator._ev_adapter
        if not adapter:
            return
        await adapter.async_resume()

    async def async_set_manual_ev_soc(self, data: Dict[str, Any]) -> None:
        adapter = self.coordinator._ev_adapter
        if not adapter:
            return
        soc = float(data["soc"])
        await adapter.async_set_manual_soc(soc)

    async def async_override_plan(self, data: Dict[str, Any]) -> None:
        """Spara manuell override i storage och trigga ny plan."""
        store = EnergyDispatcherStore(self.hass, self.coordinator.entry.entry_id)
        await store.async_save_override(data)
        await self.coordinator.async_request_refresh()
