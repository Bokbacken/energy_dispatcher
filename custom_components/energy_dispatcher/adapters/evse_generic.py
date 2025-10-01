from __future__ import annotations
from homeassistant.core import HomeAssistant

class EVSEAdapter:
    """
    Generic EVSE adapter using a switch (start/stop) and a number (max current).
    """
    def __init__(self, hass: HomeAssistant, switch_entity: str, number_entity: str, max_amps: int = 16):
        self.hass = hass
        self.switch = switch_entity
        self.number = number_entity
        self.max_amps = max_amps

    async def start(self, amps: int | None = None):
        if amps is not None and self.number:
            await self.hass.services.async_call(
                "number", "set_value",
                {"entity_id": self.number, "value": int(min(amps, self.max_amps))},
                blocking=False
            )
        await self.hass.services.async_call(
            "switch", "turn_on",
            {"entity_id": self.switch},
            blocking=False
        )

    async def stop(self):
        await self.hass.services.async_call(
            "switch", "turn_off",
            {"entity_id": self.switch},
            blocking=False
        )
