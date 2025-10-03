from datetime import datetime, timedelta
from typing import List
from .models import PlanAction, PricePoint, ForecastPoint

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
) -> List[PlanAction]:
    """
    Very simple heuristic:
    - Mark hours with price <= threshold as 'charge windows'
    - Prefer charging battery on cheap hours unless big solar next hour
    - Allocate EV charging to cheapest set of hours first until energy met
    """
    plan: List[PlanAction] = []
    price_map = {p.time.replace(minute=0, second=0, microsecond=0): p for p in prices}
    solar_map = {s.time.replace(minute=0, second=0, microsecond=0): s for s in solar}
    end = now + timedelta(hours=horizon_hours)
    cursor = now.replace(minute=0, second=0, microsecond=0)

    # Pick EV hours by lowest enriched price
    hourly_prices = []
    t = cursor
    while t < end:
        pp = price_map.get(t)
        if pp:
            hourly_prices.append((t, pp.enriched_sek_per_kwh))
        t += timedelta(hours=1)
    ev_hours_sorted = sorted(hourly_prices, key=lambda x: x[1])

    # naive EV allocation: first N cheapest hours
    ev_selected = set()
    ev_energy_remaining = ev_need_kwh
    ev_power_kw_assumed = 11.0  # example, will be adjusted by dispatcher EV adapter set_current
    for t, _ in ev_hours_sorted:
        if ev_energy_remaining <= 0:
            break
        ev_selected.add(t)
        ev_energy_remaining -= ev_power_kw_assumed

    # Build actions
    t = cursor
    while t < end:
        price = price_map.get(t)
        sol = solar_map.get(t)
        action = PlanAction(time=t)

        if t in ev_selected:
            # Dispatcher will start EV and set amps accordingly
            action.ev_charge_a = 16

        # Battery: charge on cheap hours unless high solar next hour (avoid double-charging)
        if price and price.enriched_sek_per_kwh <= cheap_threshold:
            next_sol = solar_map.get(t + timedelta(hours=1))
            if not next_sol or next_sol.watts < 500:  # small solar, top-up battery
                action.charge_batt_w = batt_max_charge_w

        plan.append(action)
        t += timedelta(hours=1)

    return plan
