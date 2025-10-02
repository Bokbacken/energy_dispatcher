"""Bas-klasser för batteri- och EV-adaptrar."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant

from ..models import BatterySettings, BatteryState, EVSettings, EVState

_LOGGER = logging.getLogger(__name__)


class BatteryAdapterBase(ABC):
    """Abstrakt bas för batteriadaptrar."""

    def __init__(self, hass: HomeAssistant, settings: BatterySettings) -> None:
        self.hass = hass
        self.settings = settings

    @abstractmethod
    async def async_get_state(self) -> BatteryState:
        ...

    async def async_force_charge(
        self, duration_minutes: int, ampere: float | None = None
    ) -> None:
        _LOGGER.warning("Force charge ej implementerat för adapter %s", type(self))

    async def async_force_discharge(self, duration_minutes: int) -> None:
        _LOGGER.warning("Force discharge ej implementerat för adapter %s", type(self))

    @classmethod
    def from_entity(cls, hass: HomeAssistant, settings: BatterySettings):
        """Fallback adapter som läser stat från angivna sensorer."""
        return EntityBatteryAdapter(hass, settings)


class EntityBatteryAdapter(BatteryAdapterBase):
    """Simple batteriadapter vare sig det finns generella entiteter."""

    async def async_get_state(self) -> BatteryState:
        soc_state = self.hass.states.get(self.settings.soc_sensor_entity_id)
        if not soc_state:
            raise RuntimeError("SOC-sensor saknas")
        soc = float(soc_state.state) / 100 if float(soc_state.state) > 1 else float(soc_state.state)

        power_state = None
        if self.settings.power_sensor_entity_id:
            state = self.hass.states.get(self.settings.power_sensor_entity_id)
            if state:
                try:
                    power_state = float(state.state)
                except ValueError:
                    power_state = None

        now = datetime.now(UTC)
        return BatteryState(
            soc=soc,
            power_kw=power_state,
            estimated_hours_remaining=None,
            price_per_kwh=None,
            last_update=now,
        )


class EVAdapterBase(ABC):
    """Bas-klass för EV-laddningsadapter."""

    def __init__(self, hass: HomeAssistant, settings: EVSettings) -> None:
        self.hass = hass
        self.settings = settings

    @abstractmethod
    async def async_get_state(self) -> EVState:
        ...

    async def async_pause(self, duration_minutes: int | None = None) -> None:
        _LOGGER.warning("Pause ej implementerat i adapter %s", type(self))

    async def async_resume(self) -> None:
        _LOGGER.warning("Resume ej implementerat i adapter %s", type(self))

    async def async_set_manual_soc(self, soc: float) -> None:
        _LOGGER.debug("Manual SOC satt via adapter %s: %.2f", type(self), soc)
