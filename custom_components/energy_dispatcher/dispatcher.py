from __future__ import annotations
import time
from typing import List
from homeassistant.core import HomeAssistant
from .models import PlanAction

SLOT_TOLERANCE_SEC = 60  # trigger within +/- 1 min

async def dispatch_now(hass: HomeAssistant, now_ts: float, plan: List[PlanAction], batt_adapter) -> None:
    """
    Execute actions for the current 15-min slot. Idempotent per-slot behavior:
    - if action matches current slot window, (re)issue force charge/discharge
    """
    for a in plan:
        if (a.ts_start - SLOT_TOLERANCE_SEC) <= now_ts <= (a.ts_start + SLOT_TOLERANCE_SEC):
            if a.batt_kw < 0:
                minutes = int(round((a.ts_end - a.ts_start) / 60.0))
                await batt_adapter.force_charge(minutes=minutes, power_kw=abs(a.batt_kw))
            elif a.batt_kw > 0:
                minutes = int(round((a.ts_end - a.ts_start) / 60.0))
                await batt_adapter.force_discharge(minutes=minutes, power_kw=a.batt_kw)
