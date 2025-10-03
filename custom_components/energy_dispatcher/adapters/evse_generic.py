from .base import EVSEAdapter
from homeassistant.core import HomeAssistant

class GenericEVSEAdapter(EVSEAdapter):
    def __init__(self, hass: HomeAssistant, start_switch: str, stop_switch: str, current_number: str,
                 min_a: int = 6, max_a: int = 16):
        super().__init__(hass)
        self._start = start_switch
        self._stop = stop_switch
        self._number = current_number
        self._min_a = min_a
        self._max_a = max_a

    async def async_start(self) -> None:
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self._start}, blocking=False)

    async def async_stop(self) -> None:
        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self._stop}, blocking=False)

    async def async_set_current(self, amps: int) -> None:
        amps = max(self._min_a, min(self._max_a, int(amps)))
        await self.hass.services.async_call("number", "set_value", {"entity_id": self._number, "value": amps}, blocking=False)
