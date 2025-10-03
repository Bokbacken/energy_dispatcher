import math
from homeassistant.helpers.storage import Store

STORAGE_KEY = "energy_dispatcher_bec"
STORAGE_VERSION = 1

class BatteryEnergyCost:
    """
    Tracks average cost (WACE) of energy in the battery.
    Persisted across restarts.
    """
    def __init__(self, hass, capacity_kwh: float):
        self.hass = hass
        self.capacity_kwh = capacity_kwh
        self.store = Store(hass, STORAGE_VERSION, f".storage/{STORAGE_KEY}")
        self.energy_kwh = 0.0     # Estimated energy currently in battery
        self.wace = 0.0           # SEK/kWh

    async def async_load(self):
        data = await self.store.async_load()
        if data:
            self.energy_kwh = data.get("energy_kwh", 0.0)
            self.wace = data.get("wace", 0.0)

    async def async_save(self):
        await self.store.async_save({"energy_kwh": self.energy_kwh, "wace": self.wace})

    def set_soc(self, soc_percent: float):
        self.energy_kwh = max(0.0, min(1.0, soc_percent / 100.0)) * self.capacity_kwh

    def on_charge(self, delta_kwh: float, cost_sek_per_kwh: float):
        if delta_kwh <= 0:
            return
        total_cost = self.energy_kwh * self.wace + delta_kwh * cost_sek_per_kwh
        self.energy_kwh += delta_kwh
        if self.energy_kwh > 0:
            self.wace = total_cost / self.energy_kwh

    def on_discharge(self, delta_kwh: float):
        if delta_kwh <= 0:
            return
        self.energy_kwh = max(0.0, self.energy_kwh - delta_kwh)
        # WACE unchanged for remaining energy
