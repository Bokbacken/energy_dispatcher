"""
Planner module for optimizing battery and EV charging schedules.

This module provides cost-based optimization suggestions for:
- Battery charging/discharging timing
- EV charging schedule optimization
- Reserve capacity management for high-cost periods
"""
from datetime import datetime, timedelta
from typing import List, Optional

from .models import PlanAction, PricePoint, ForecastPoint, ChargingMode, CostThresholds
from .cost_strategy import CostStrategy, CostLevel

def simple_plan(
    now: datetime,
    horizon_hours: int,
    prices: List[PricePoint],
    solar: List[ForecastPoint],
    batt_soc_pct: float,
    batt_capacity_kwh: float,
    batt_max_charge_w: int,
    ev_need_kwh: float,
    cheap_threshold: float,
    ev_deadline: Optional[datetime] = None,
    ev_mode: ChargingMode = ChargingMode.ECO,
    cost_strategy: Optional[CostStrategy] = None,
) -> List[PlanAction]:
    """
    Enhanced heuristic with cost strategy:
    - Uses cost classification (cheap/medium/high) for decisions
    - Reserves battery capacity for high-cost windows
    - Optimizes EV charging for deadline and cost
    - Prevents premature battery depletion
    """
    # Initialize cost strategy if not provided
    if cost_strategy is None:
        cost_strategy = CostStrategy(CostThresholds(cheap_max=cheap_threshold, high_min=cheap_threshold * 2))
    
    plan: List[PlanAction] = []
    price_map = {p.time.replace(minute=0, second=0, microsecond=0): p for p in prices}
    solar_map = {s.time.replace(minute=0, second=0, microsecond=0): s for s in solar}
    end = now + timedelta(hours=horizon_hours)
    cursor = now.replace(minute=0, second=0, microsecond=0)

    # Calculate battery reserve for high-cost windows
    reserve_soc = cost_strategy.calculate_battery_reserve(
        prices, now, batt_capacity_kwh, batt_soc_pct, horizon_hours
    )
    
    # Optimize EV charging windows based on mode
    ev_selected = set()
    if ev_need_kwh > 0:
        if ev_mode == ChargingMode.ASAP:
            # Charge ASAP: select all hours from now until charged
            ev_power_kw = 11.0
            hours_needed = int(ev_need_kwh / ev_power_kw) + 1
            t = cursor
            for _ in range(hours_needed):
                if t < end:
                    ev_selected.add(t)
                    t += timedelta(hours=1)
        elif ev_mode == ChargingMode.DEADLINE and ev_deadline:
            # Meet deadline: use cost optimization within deadline window
            ev_hours = cost_strategy.optimize_ev_charging_windows(
                prices, now, ev_need_kwh, ev_deadline
            )
            ev_selected = set(ev_hours)
        else:
            # ECO or COST_SAVER: optimize for cheapest hours
            ev_hours = cost_strategy.optimize_ev_charging_windows(
                prices, now, ev_need_kwh, ev_deadline or (now + timedelta(hours=24))
            )
            ev_selected = set(ev_hours)

    # Build actions
    current_batt_soc = batt_soc_pct
    t = cursor
    while t < end:
        price = price_map.get(t)
        sol = solar_map.get(t)
        action = PlanAction(time=t)

        if t in ev_selected:
            # Dispatcher will start EV and set amps accordingly
            action.ev_charge_a = 16

        # Battery management with cost strategy
        if price:
            price_level = cost_strategy.classify_price(price.enriched_sek_per_kwh)
            solar_w = sol.watts if sol else 0
            
            # Check if we should charge battery
            should_charge = cost_strategy.should_charge_battery(
                price.enriched_sek_per_kwh,
                current_batt_soc,
                reserve_soc,
                solar_w
            )
            
            # Check if we should discharge battery
            should_discharge = cost_strategy.should_discharge_battery(
                price.enriched_sek_per_kwh,
                current_batt_soc,
                reserve_soc,
                -solar_w if solar_w < 0 else 0
            )
            
            if should_charge and current_batt_soc < 95.0:
                action.charge_batt_w = batt_max_charge_w
                # Estimate SOC increase
                charge_kwh = batt_max_charge_w / 1000.0
                soc_increase = (charge_kwh / batt_capacity_kwh) * 100
                current_batt_soc = min(100.0, current_batt_soc + soc_increase)
                action.notes = f"Charge (price: {price_level.value}, SOC: {current_batt_soc:.0f}%)"
            elif should_discharge and current_batt_soc > reserve_soc:
                action.discharge_batt_w = batt_max_charge_w
                # Estimate SOC decrease
                discharge_kwh = batt_max_charge_w / 1000.0
                soc_decrease = (discharge_kwh / batt_capacity_kwh) * 100
                current_batt_soc = max(0.0, current_batt_soc - soc_decrease)
                action.notes = f"Discharge (price: {price_level.value}, reserve: {reserve_soc:.0f}%)"

        plan.append(action)
        t += timedelta(hours=1)

    return plan
