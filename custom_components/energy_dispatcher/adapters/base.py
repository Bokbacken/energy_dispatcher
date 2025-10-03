from abc import ABC, abstractmethod
from typing import Optional
from homeassistant.core import HomeAssistant

class BatteryAdapter(ABC):
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    @abstractmethod
    def supports_forced_charge(self) -> bool:
        ...

    @abstractmethod
    async def async_force_charge(self, power_w: int, duration_min: int) -> None:
        ...

    @abstractmethod
    async def async_cancel_force_charge(self) -> None:
        ...

    async def async_set_target_soc(self, percent: int) -> None:
        # Optional override
        return

class EVSEAdapter(ABC):
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    @abstractmethod
    async def async_start(self) -> None:
        ...

    @abstractmethod
    async def async_stop(self) -> None:
        ...

    @abstractmethod
    async def async_set_current(self, amps: int) -> None:
        ...

class EVManualAdapter:
    """
    Stores manual EV info and provides estimated energy/time to target.
    """
    def __init__(self, ev_batt_kwh: float, ev_current_soc: float, ev_target_soc: float,
                 phases: int = 3, voltage: int = 230, max_a: int = 16):
        self.ev_batt_kwh = ev_batt_kwh
        self.ev_current_soc = ev_current_soc
        self.ev_target_soc = ev_target_soc
        self.phases = phases
        self.voltage = voltage
        self.max_a = max_a

    def energy_needed_kwh(self) -> float:
        delta = max(0.0, self.ev_target_soc - self.ev_current_soc) / 100.0
        return delta * self.ev_batt_kwh

    def power_kw_at(self, amps: int) -> float:
        # Simple 3-phase power estimate: P = V * I * phases / 1000
        return self.voltage * amps * self.phases / 1000.0

    def hours_needed(self, amps: int) -> Optional[float]:
        p = self.power_kw_at(amps)
        if p <= 0:
            return None
        return self.energy_needed_kwh() / p
