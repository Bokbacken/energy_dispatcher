from __future__ import annotations
import time
from typing import List, Tuple
from .models import PriceSeries, PlanAction, Period

def _select_night_window(periods: List[Period], night_start: int = 22, night_end: int = 7) -> List[Period]:
    """
    Filter periods that fall within [night_start, next_day night_end).
    Assumes periods are local-time ISO converted already in your price sensors.
    For simplicity here, we accept all next 12h as candidate; core logic is price-sort.
    """
    return periods  # MVP: you can later filter by hour boundaries

def plan_night_charge_greedy(
    price_series: PriceSeries,
    soc_now: float,
    cap_kwh: float,
    target_soc: float,
    max_grid_charge_kw: float,
    eff: float,
) -> List[PlanAction]:
    """
    Greedy: sort candidate periods by ascending price and pick enough slots to reach target SoC.
    Uses 15-min resolution if provided.
    """
    slots = price_series.periods[:]
    if not slots:
        return []

    # slot duration in hours (assume uniform)
    dt_hours = max( (slots[0].end_ts - slots[0].start_ts) / 3600.0, 0.25)

    need_soc = max(target_soc - soc_now, 0.0) / 100.0
    need_kwh = need_soc * cap_kwh
    if need_kwh <= 0.0:
        return []

    # Sort by price ascending
    sorted_slots = sorted(slots, key=lambda p: p.price)
    plan: List[PlanAction] = []
    charged_kwh = 0.0

    per_slot_kwh = max_grid_charge_kw * dt_hours * eff  # delivered to battery accounting for efficiency
    for s in sorted_slots:
        if charged_kwh >= need_kwh:
            break
        plan.append(PlanAction(
            ts_start=s.start_ts,
            ts_end=s.end_ts,
            batt_kw= -max_grid_charge_kw,  # negative = charging
            ev_amps=None
        ))
        charged_kwh += per_slot_kwh

    # Sort actions by time for dispatcher
    plan.sort(key=lambda a: a.ts_start)
    return plan

def plan_day_discharge_simple(
    price_series: PriceSeries,
    soc_now: float,
    cap_kwh: float,
    soc_floor: float,
    batt_max_discharge_kw: float,
    bec_kr_per_kwh: float,
    margin: float,
) -> List[PlanAction]:
    """
    Simple discharge policy: discharge only when price > BEC + margin.
    """
    actions: List[PlanAction] = []
    slots = price_series.periods
    if not slots:
        return actions

    dt_hours = max((slots[0].end_ts - slots[0].start_ts) / 3600.0, 0.25)
    usable_kwh = max((soc_now - soc_floor)/100.0 * cap_kwh, 0.0)
    max_slots = int(usable_kwh / (batt_max_discharge_kw * dt_hours)) if batt_max_discharge_kw > 0 else 0

    candidates = [s for s in slots if s.price > (bec_kr_per_kwh + margin)]
    # Take most expensive first
    candidates.sort(key=lambda p: p.price, reverse=True)
    for s in candidates[:max_slots]:
        actions.append(PlanAction(
            ts_start=s.start_ts, ts_end=s.end_ts, batt_kw= +batt_max_discharge_kw
        ))
    actions.sort(key=lambda a: a.ts_start)
    return actions

def merge_plans(*plans: List[PlanAction]) -> List[PlanAction]:
    return sorted([a for p in plans for a in p], key=lambda x: x.ts_start)
