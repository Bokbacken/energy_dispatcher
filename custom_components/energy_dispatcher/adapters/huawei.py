"""Huawei Luna2000 adapter (exempel)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant

from ..models import BatterySettings, BatteryState
from .base import BatteryAdapterBase

_LOGGER = logging.getLogger(__name__)


class HuaweiLunaBatteryAdapter(BatteryAdapterBase):
    """Adapter som använder entiteter från Huawei Solar integrationen."""

    def __init__(self, hass: HomeAssistant, settings: BatterySettings) -> None:
        super().__init__(hass, settings)

    async def async_get_state(self) -> BatteryState:
        soc_entity = self.settings.soc_sensor_entity_id
        soc_state = self.hass.states.get(soc_entity)
        if not soc_state:
            raise RuntimeError(f"Hittar inte SOC-entity {soc_entity}")

        soc = float(soc_state.state)
        if soc > 1:
            soc /= 100

        power_kw = None
        if self.settings.power_sensor_entity_id:
            power_state = self.hass.states.get(self.settings.power_sensor_entity_id)
            if power_state:
                try:
                    power_kw = float(power_state.state)
                except ValueError:
                    power_kw = None
            if power_kw is not None and self.settings.power_sign_invert:
                power_kw = -power_kw

        now = datetime.now(UTC)
        return BatteryState(
            soc=soc,
            power_kw=power_kw,
            estimated_hours_remaining=None,
            price_per_kwh=None,
            last_update=now,
        )

    async def async_force_charge(
        self, duration_minutes: int, ampere: float | None = None
    ) -> None:
        if not self.settings.force_charge_entity_id:
            _LOGGER.warning("Ingen force charge entity definierad")
            return
        service_data = {"entity_id": self.settings.force_charge_entity_id}
        await self.hass.services.async_call(
            "switch",
            "turn_on",
            service_data,
            blocking=True,
        )

    async def async_force_discharge(self, duration_minutes: int) -> None:
        if not self.settings.force_discharge_entity_id:
            _LOGGER.warning("Ingen force discharge entity definierad")
            return
        await self.hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": self.settings.force_discharge_entity_id},
            blocking=True,
        )
