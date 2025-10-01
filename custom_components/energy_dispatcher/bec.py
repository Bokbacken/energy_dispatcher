from __future__ import annotations
from dataclasses import dataclass

@dataclass
class BECState:
    bec_kr_per_kwh: float = 0.0

def update_bec_weighted(current_bec: float, energy_now_kwh: float, delta_e_kwh: float, slot_cost_kr_per_kwh: float) -> float:
    """
    Weighted-average update of Battery Effective Cost (kr/kWh).
    """
    if delta_e_kwh <= 0.0:
        return current_bec
    return (current_bec * energy_now_kwh + slot_cost_kr_per_kwh * delta_e_kwh) / (energy_now_kwh + delta_e_kwh)
