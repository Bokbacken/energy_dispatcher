from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .adapters.base import BatteryAdapter, EVSEAdapter

_LOGGER = logging.getLogger(__name__)


class Dispatcher:
    """
    Samlar anrop till EVSE/Batteri och hanterar enkla overrides.
    """

    def __init__(self, hass, battery: Optional[BatteryAdapter] = None, evse: Optional[EVSEAdapter] = None):
        self.hass = hass
        self._battery = battery
        self._evse = evse

        # Overrides
        self._overrides: dict[str, datetime] = {}
        self._forced_ev_current: Optional[int] = None

    # ===== Overrides =====
    def set_override(self, key: str, until: datetime):
        self._overrides[key] = until

    def clear_override(self, key: str):
        self._overrides.pop(key, None)

    def get_override_until(self, key: str) -> Optional[datetime]:
        return self._overrides.get(key)

    def is_paused(self, now: datetime) -> bool:
        u = self._overrides.get("ev_pause_until")
        return bool(u and u > now)

    def is_forced(self, now: datetime) -> bool:
        u = self._overrides.get("ev_force_until")
        return bool(u and u > now)

    def set_forced_ev_current(self, amps: Optional[int]):
        self._forced_ev_current = amps

    def get_forced_ev_current(self) -> Optional[int]:
        return self._forced_ev_current

    # ===== EVSE helpers =====
    async def async_ev_start(self):
        if self._evse:
            await self._evse.async_start()

    async def async_ev_stop(self):
        if self._evse:
            await self._evse.async_stop()

    async def async_ev_set_current(self, amps: int):
        if self._evse:
            await self._evse.async_set_current(amps)

    async def async_apply_ev_setpoint(self, amps: int):
        """
        amps <= 0 -> stoppa
        annars sätt current och starta.
        """
        if not self._evse:
            _LOGGER.debug("EVSE saknas - ingen setpoint att applicera")
            return
        if amps <= 0:
            _LOGGER.debug("EV setpoint: stop")
            await self._evse.async_stop()
            return
        _LOGGER.debug("EV setpoint: %s A (apply)", amps)
        await self._evse.async_set_current(amps)
        await self._evse.async_start()
