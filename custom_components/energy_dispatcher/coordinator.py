from __future__ import annotations
import time
from datetime import timedelta
from typing import Optional, List
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, PLAN_REFRESH_SECONDS, DISPATCH_INTERVAL_SECONDS
from .models import PriceSeries, Period, PlanAction
from .planner import plan_night_charge_greedy, plan_day_discharge_simple, merge_plans
from .dispatcher import dispatch_now

class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    """
    Coordinates planning and dispatching.
    Expects external code (setup) to provide:
      - get_price_series(): PriceSeries (48h)
      - batt_adapter
      - config options (targets, limits, etc.)
    """
    def __init__(self, hass: HomeAssistant, get_price_series, batt_adapter, cfg: dict):
        super().__init__(hass, logger=hass.helpers.logger.logging.getLogger(__name__),
                         name=f"{DOMAIN}_coordinator", update_interval=timedelta(seconds=PLAN_REFRESH_SECONDS))
        self.get_price_series = get_price_series
        self.batt = batt_adapter
        self.cfg = cfg
        self._plan: List[PlanAction] = []

    @property
    def plan(self) -> List[PlanAction]:
        return self._plan

    async def _async_update_data(self):
        # Build a new plan every interval
        prices: PriceSeries = await self.hass.async_add_executor_job(self.get_price_series)
        soc_now = await self.batt.get_soc()
        night = plan_night_charge_greedy(
            price_series=prices,
            soc_now=soc_now,
            cap_kwh=self.cfg["battery_capacity_kwh"],
            target_soc=self.cfg["morning_soc_target"],
            max_grid_charge_kw=self.cfg["max_grid_charge_kw"],
            eff=self.cfg["battery_eff"],
        )
        discharge = plan_day_discharge_simple(
            price_series=prices,
            soc_now=soc_now,
            cap_kwh=self.cfg["battery_capacity_kwh"],
            soc_floor=self.cfg["soc_floor"],
            batt_max_discharge_kw=self.cfg.get("max_discharge_kw", self.cfg["max_grid_charge_kw"]),
            bec_kr_per_kwh=self.cfg.get("bec_kr_per_kwh", 0.0),
            margin=self.cfg.get("bec_margin", 0.10),
        )
        self._plan = merge_plans(night, discharge)
        return self._plan

    async def async_tick_dispatch(self):
        now_ts = time.time()
        await dispatch_now(self.hass, now_ts, self._plan, self.batt)
