"""Generic adapter för EVSE-laddboxar (t.ex. Easee, Zaptec)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from homeassistant.core import HomeAssistant

from ..models import EVSettings, EVState
from .base import EVAdapterBase

_LOGGER = logging.getLogger(__name__)


class GenericEVSEAdapter(EVAdapterBase):
    """Antar att det finns switch för laddare och ev. entity för SOC."""

    async def async_get_state(self) -> EVState:
        soc = 0.5
        if self.settings.soc_sensor_entity_id:
            state = self.hass.states.get(self.settings.soc_sensor_entity_id)
            if state:
                try:
                    soc = float(state.state)
                    if soc > 1:
                        soc /= 100
                except ValueError:
                    soc = 0.5

        required_kwh = max(
            self.settings.capacity_kwh * (self.settings.default_target_soc - soc), 0
        )
        estimate_hours = required_kwh / ((self.settings.default_ampere * 230 / 1000) * self.settings.efficiency)

        now = datetime.now(UTC)
        return EVState(
            soc=soc,
            target_soc=self.settings.default_target_soc,
            required_kwh=required_kwh,
            estimated_charge_time=max(estimate_hours, 0),
            charger_available=True,
            last_update=now,
        )

    async def async_pause(self, duration_minutes: int | None = None) -> None:
        if self.settings.charger_pause_switch_entity_id:
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": self.settings.charger_pause_switch_entity_id},
                blocking=True,
            )
        elif self.settings.charger_switch_entity_id:
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self.settings.charger_switch_entity_id},
                blocking=True,
            )
        else:
            _LOGGER.warning("Ingen entitet att pausa laddning")

    async def async_resume(self) -> None:
        if self.settings.charger_pause_switch_entity_id:
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self.settings.charger_pause_switch_entity_id},
                blocking=True,
            )
        elif self.settings.charger_switch_entity_id:
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": self.settings.charger_switch_entity_id},
                blocking=True,
            )
        else:
            _LOGGER.warning("Ingen entitet att återuppta laddning")
