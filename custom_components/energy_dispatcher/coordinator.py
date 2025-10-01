from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PLAN_REFRESH_SECONDS
from .models import PriceSeries, Period

logger = logging.getLogger(__name__)


@dataclass
class PlanSlot:
    start_ts: float
    end_ts: float
    action: str  # "charge", "discharge", "idle"
    power_kw: float


class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        get_price_series: Callable[[], PriceSeries],
        batt,
        params: dict,
    ):
        super().__init__(
            hass,
            logger=logger,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=PLAN_REFRESH_SECONDS),
        )
        self.hass = hass
        self.get_price_series = get_price_series
        self.batt = batt
        self.params = params

        # Lazy import to avoid config_flow-time import issues
        from .planner import Planner  # type: ignore
        from .dispatcher import Dispatcher  # type: ignore

        self._planner = Planner(params=self.params)
        self._dispatcher = Dispatcher(hass=self.hass, batt=self.batt, params=self.params)

        self._last_plan: List[PlanSlot] = []
        self._last_plan_generated_utc: datetime | None = None

    @property
    def last_plan(self) -> List[PlanSlot]:
        return self._last_plan

    @property
    def last_plan_generated_utc(self) -> datetime | None:
        return self._last_plan_generated_utc

    async def _async_update_data(self):
        await self._refresh_plan_if_needed()

    async def async_config_entry_first_refresh(self):
        await self._refresh_plan(force=True)

    async def _refresh_plan_if_needed(self):
        if self._last_plan_generated_utc is None:
            await self._refresh_plan(force=True)
            return
        if (datetime.utcnow() - self._last_plan_generated_utc).total_seconds() >= PLAN_REFRESH_SECONDS:
            await self._refresh_plan(force=True)

    async def _refresh_plan(self, force: bool = False):
        try:
            price_series: PriceSeries = self.get_price_series()
        except Exception as e:
            logger.warning("Energy Dispatcher: Failed to read price series: %s", e)
            return

        if not price_series or not price_series.periods:
            logger.warning("Energy Dispatcher: No price periods available; skipping plan refresh")
            return

        try:
            plan = self._planner.build_plan(price_series)
        except Exception as e:
            logger.exception("Energy Dispatcher: Planner failed: %s", e)
            return

        slots: List[PlanSlot] = []
        for p in plan:
            if not isinstance(p, Period):
                continue
            action = getattr(p, "action", "idle")
            power_kw = float(getattr(p, "power_kw", 0.0))
            slots.append(PlanSlot(start_ts=p.start_ts, end_ts=p.end_ts, action=action, power_kw=power_kw))

        self._last_plan = slots
        self._last_plan_generated_utc = datetime.utcnow()
        logger.debug("Energy Dispatcher: Plan updated with %d slots", len(self._last_plan))

    async def async_tick_dispatch(self):
        await self._refresh_plan_if_needed()
        if not self._last_plan:
            return

        now_ts = datetime.utcnow().timestamp()

        current = None
        for s in self._last_plan:
            if s.start_ts <= now_ts < s.end_ts:
                current = s
                break

        if current is None:
            await self._dispatcher.idle()
            return

        action = (current.action or "idle").lower()
        power_kw = max(0.0, float(current.power_kw or 0.0))

        try:
            if action == "charge":
                await self._dispatcher.charge(power_kw)
            elif action == "discharge":
                await self._dispatcher.discharge(power_kw)
            else:
                await self._dispatcher.idle()
        except Exception as e:
            logger.warning("Energy Dispatcher: dispatch error on action=%s power=%.2f: %s", action, power_kw, e)
