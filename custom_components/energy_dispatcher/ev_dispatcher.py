from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Optional

from homeassistant.core import HomeAssistant

from .const import (
    CONF_EVSE_START_SWITCH,
    CONF_EVSE_STOP_SWITCH,
    CONF_EVSE_CURRENT_NUMBER,
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
)

_LOGGER = logging.getLogger(__name__)


class EVDispatcher:
    """
    EV-kontroller som kan:
      - trycka button/script eller slå på/av switch/input_boolean
      - sätta laddström via number.set_value
      - hantera overrides: pause/force och "forced current"

    Koordinatorn anropar:
      - is_paused(now), is_forced(now)
      - get_forced_ev_current()
      - async_apply_ev_setpoint(amps)
    """

    def __init__(self, hass: HomeAssistant, cfg_lookup: Callable[[str, Optional[object]], object]):
        self.hass = hass
        self._cfg = cfg_lookup

        # Overrides
        self._overrides: dict[str, datetime] = {}
        self._forced_ev_current: Optional[int] = None

    # ==== Overrides ====
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

    # ==== Helpers ====
    def _available(self, entity_id: str) -> bool:
        if not entity_id:
            return False
        st = self.hass.states.get(entity_id)
        return bool(st and str(st.state).lower() != "unavailable")

    async def _press_or_turn(self, entity_id: str, on: bool):
        if not entity_id:
            return
        if not self._available(entity_id):
            _LOGGER.warning("EVDispatcher: entity %s unavailable, skipping", entity_id)
            return

        domain = entity_id.split(".")[0]
        if domain == "button":
            await self.hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
            _LOGGER.debug("EVDispatcher: button.press %s", entity_id)
            return

        if domain in ("switch", "input_boolean"):
            service = "turn_on" if on else "turn_off"
            await self.hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)
            _LOGGER.debug("EVDispatcher: %s.%s %s", domain, service, entity_id)
            return

        if domain == "script":
            await self.hass.services.async_call("script", "turn_on", {"entity_id": entity_id}, blocking=True)
            _LOGGER.debug("EVDispatcher: script.turn_on %s", entity_id)
            return

        # fallback via homeassistant.turn_on/off för andra domäner som stöder det
        service = "turn_on" if on else "turn_off"
        await self.hass.services.async_call("homeassistant", service, {"entity_id": entity_id}, blocking=True)
        _LOGGER.debug("EVDispatcher: homeassistant.%s %s", service, entity_id)

    async def _set_current(self, amps: int):
        num_ent = self._cfg(CONF_EVSE_CURRENT_NUMBER, "")
        if not num_ent:
            return
        if not self._available(num_ent):
            _LOGGER.warning("EVDispatcher: current number %s unavailable, skipping", num_ent)
            return
        try:
            await self.hass.services.async_call(
                "number", "set_value", {"entity_id": num_ent, "value": float(amps)}, blocking=True
            )
            _LOGGER.debug("EVDispatcher: number.set_value %s = %s A", num_ent, amps)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("EVDispatcher: failed to set current to %s A", amps)

    # ==== Publikt API ====
    async def async_apply_ev_setpoint(self, amps: int):
        min_a = int(self._cfg(CONF_EVSE_MIN_A, 6))
        max_a = int(self._cfg(CONF_EVSE_MAX_A, 16))
        amps = max(0, min(max_a, int(amps)))

        start_ent = self._cfg(CONF_EVSE_START_SWITCH, "")
        stop_ent = self._cfg(CONF_EVSE_STOP_SWITCH, "")

        if amps >= min_a:
            # Sätt ström först, tryck sedan start
            await self._set_current(amps)
            await self._press_or_turn(start_ent, on=True)
        else:
            # Stanna laddning
            await self._press_or_turn(stop_ent or start_ent, on=False)
