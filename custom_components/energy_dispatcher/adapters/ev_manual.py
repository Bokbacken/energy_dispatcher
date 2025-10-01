from __future__ import annotations
from homeassistant.core import HomeAssistant

class ManualEVAdapter:
    """
    Manual EV SOC adapter: SOC and target provided via helpers.
    Charging is executed via a generic EVSE adapter (optional).
    """
    def __init__(self, hass: HomeAssistant, soc_entity: str, target_entity: str, evse: 'EVSEAdapter' | None = None):
        self.hass = hass
        self.soc_entity = soc_entity
        self.target_entity = target_entity
        self.evse = evse

    def get_soc(self) -> float:
        st = self.hass.states.get(self.soc_entity)
        try:
            return float(st.state) if st else 0.0
        except Exception:
            return 0.0

    def get_target_soc(self) -> float:
        st = self.hass.states.get(self.target_entity)
        try:
            return float(st.state) if st else 80.0
        except Exception:
            return 80.0

    async def start(self, amps: int | None = None):
        if self.evse:
            await self.evse.start(amps)

    async def stop(self):
        if self.evse:
            await self.evse.stop()
