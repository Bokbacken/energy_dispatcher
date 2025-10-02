"""Adapter för manuell EV-hantering (t.ex. leasingbil utan API)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..models import EVSettings, EVState
from .base import EVAdapterBase

_LOGGER = logging.getLogger(__name__)


class ManualEVAdapter(EVAdapterBase):
    """Bygger state från manuellt angivet SOC (lagras via helper)."""

    def __init__(self, hass, settings: EVSettings) -> None:
        super().__init__(hass, settings)
        self._manual_soc: float = settings.default_target_soc

    async def async_get_state(self) -> EVState:
        soc = self._manual_soc
        required_kwh = max(
            self.settings.capacity_kwh * (self.settings.default_target_soc - soc), 0
        )
        estimate_hours = required_kwh / ((self.settings.default_ampere * 230 / 1000) * self.settings.efficiency)
        now = datetime.now(UTC)

        return EVState(
            soc=soc,
            target_soc=self.settings.default_target_soc,
            required_kwh=required_kwh,
            estimated_charge_time=estimate_hours,
            charger_available=True,
            last_update=now,
        )

    async def async_set_manual_soc(self, soc: float) -> None:
        self._manual_soc = soc
        _LOGGER.info("Manuellt EV-SOC satt till %.2f", soc)

    async def async_pause(self, duration_minutes: int | None = None) -> None:
        _LOGGER.info("Manuell EV adapter: pause (duration=%s)", duration_minutes)

    async def async_resume(self) -> None:
        _LOGGER.info("Manuell EV adapter: resume")
