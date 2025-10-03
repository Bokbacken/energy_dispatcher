from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class Plane:
    dec: int
    az: int
    kwp: float

@dataclass
class ForecastPoint:
    time: datetime
    watts: float

@dataclass
class PricePoint:
    time: datetime
    spot_sek_per_kwh: float
    enriched_sek_per_kwh: float

@dataclass
class PlanAction:
    time: datetime
    charge_batt_w: int = 0
    discharge_batt_w: int = 0
    ev_charge_a: Optional[int] = None
    notes: Optional[str] = None
