from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from ..models import Metrics

@dataclass
class BatteryCapabilities:
    can_force_charge_from_grid: bool = True
    can_force_discharge_to_load: bool = True
    can_write_TOU_schedule: bool = False
    max_charge_kw: float = 5.0
    max_discharge_kw: float = 5.0
    min_soc: float = 10.0
    max_soc: float = 90.0

class BatteryAdapter:
    async def get_soc(self) -> float:
        raise NotImplementedError

    async def get_power_limits(self) -> tuple[float, float]:
        raise NotImplementedError

    async def get_metrics(self) -> Metrics:
        return Metrics()

    async def force_charge(self, minutes: int, power_kw: float) -> None:
        raise NotImplementedError

    async def stop_charge(self) -> None:
        pass

    async def force_discharge(self, minutes: int, power_kw: float) -> None:
        raise NotImplementedError

    async def stop_discharge(self) -> None:
        pass
