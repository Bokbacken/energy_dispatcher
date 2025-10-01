from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class Period:
    start_ts: float  # epoch seconds
    end_ts: float
    price: float     # currency/kWh

@dataclass
class PlanAction:
    ts_start: float
    ts_end: float
    batt_kw: float  # +discharge, -charge, 0 idle
    ev_amps: Optional[int] = None

@dataclass
class PriceSeries:
    periods: List[Period]  # must be contiguous 15-min or 60-min steps

@dataclass
class Metrics:
    p_batt_w: Optional[float] = None
    p_pv_w: Optional[float] = None
    p_load_w: Optional[float] = None
    p_import_w: Optional[float] = None
    p_export_w: Optional[float] = None
