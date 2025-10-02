"""Enkel planeringslogik (kan byggas ut)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from typing import Iterable, Optional

from .bec import PriceAndCostHelper
from .const import (
    HIGH_PRICE_THRESHOLD_FACTOR,
    LOW_PRICE_THRESHOLD_FACTOR,
)
from .models import (
    BatteryState,
    EnergyDispatcherConfig,
    EnergyPlan,
    EnergyPlanAction,
    EVState,
    HouseState,
    PricePoint,
    SolarForecastPoint,
)

_LOGGER = logging.getLogger(__name__)


class EnergyPlanner:
    """Planerar prioriterad energianvändning."""

    def build_plan(
        self,
        config: EnergyDispatcherConfig,
        forecast: Iterable[SolarForecastPoint],
        price_points: list[PricePoint],
        battery_state: BatteryState | None,
        ev_state: EVState | None,
        house_state: HouseState,
        price_helper: PriceAndCostHelper,
    ) -> EnergyPlan:
        """Bygg en plan baserat på känd data."""
        plan = EnergyPlan(
            generated_at=datetime.now(UTC),
            horizon_hours=48,
        )

        price_stats = price_helper.get_price_statistics(price_points)
        low_threshold = price_stats["average"] * LOW_PRICE_THRESHOLD_FACTOR
        high_threshold = price_stats["average"] * HIGH_PRICE_THRESHOLD_FACTOR

        if battery_state and battery_state.price_per_kwh:
            _LOGGER.debug("Battery price per kWh: %s", battery_state.price_per_kwh)

        # Batteri: ladda vid lågpris, håll reserv vid högpris.
        if battery_state:
            for point in price_points:
                if point.price <= low_threshold and battery_state.soc < config.battery.max_soc:
                    action = EnergyPlanAction(
                        action_type="charge_battery",
                        start=point.start,
                        end=point.end,
                        target_value=config.battery.max_soc,
                        notes=f"Lågt pris ({point.price:.2f} {config.prices.currency}/kWh)",
                    )
                    plan.battery_actions.append(action)
                elif point.price >= high_threshold and battery_state.soc > config.battery.min_soc:
                    action = EnergyPlanAction(
                        action_type="reserve_battery",
                        start=point.start,
                        end=point.end,
                        target_value=config.battery.min_soc,
                        notes=f"Högt pris ({point.price:.2f}) - behåll laddning",
                    )
                    plan.battery_actions.append(action)

        # EV: planera laddning så att den är klar före departure.
        if ev_state:
            ready_time = price_helper.get_departure_time(config.ev)
            if ready_time:
                # Hitta billigaste block innan ready_time
                sorted_prices = sorted(
                    [p for p in price_points if p.end <= ready_time],
                    key=lambda p: p.price,
                )
                remaining_kwh = max(ev_state.required_kwh, 0)
                for block in sorted_prices:
                    if remaining_kwh <= 0:
                        break
                    action = EnergyPlanAction(
                        action_type="charge_ev",
                        start=block.start,
                        end=block.end,
                        target_value=config.ev.default_ampere,
                        notes=f"Ladda EV (mål {ev_state.target_soc*100:.0f}%)",
                        metadata={
                            "price": block.price,
                            "kwh_block_est": price_helper.estimate_ev_block_kwh(block, config.ev),
                        },
                    )
                    remaining_kwh -= action.metadata["kwh_block_est"]
                    plan.ev_actions.append(action)

        # Hushållslaster: föreslå att flytta tunga laster till soliga/lågpris timmar.
        forecast_map = {p.timestamp: p for p in forecast}
        for action in list(plan.battery_actions):
            # Om solprognos är hög under samma period, markera synergi.
            solar = forecast_map.get(action.start)
            if solar and solar.watts > 1000:
                action.notes += " (hög solproduktion)"

        # Exempel: föreslå diskmaskin under lågpris.
        if house_state and price_points:
            cheapest = min(price_points, key=lambda p: p.price)
            plan.household_actions.append(
                EnergyPlanAction(
                    action_type="suggest_shift_load",
                    start=cheapest.start,
                    end=cheapest.end,
                    notes=f"Kör tunga laster (t.ex. diskmaskin) {cheapest.start}",
                    metadata={
                        "price": cheapest.price,
                        "reason": "Lägsta pris kommande dygn",
                    },
                )
            )

        return plan
