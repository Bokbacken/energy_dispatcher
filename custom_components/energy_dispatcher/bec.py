"""Beräkningar för kostnader och storage (Battery Energy Cost)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, time
from typing import Any, Dict, Optional

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage
from homeassistant.util import slugify

from .const import (
    ATTR_BATTERY_STATE,
    ATTR_HOUSE_STATE,
    ATTR_PRICE_SCHEDULE,
    CONF_ENABLE_AUTO_DISPATCH,
    CONF_EV_SETTINGS,
    STORAGE_KEY_TEMPLATE,
    STORAGE_VERSION,
)
from .models import (
    BatteryState,
    EnergyDispatcherConfig,
    EVSettings,
    HouseSettings,
    PricePoint,
    SolarForecastPoint,
    HouseState,
)

_LOGGER = logging.getLogger(__name__)


class PriceAndCostHelper:
    """Hjälper till att beräkna kostnader, thresholds och last."""

    def __init__(self, config: EnergyDispatcherConfig) -> None:
        self.config = config

    def get_price_statistics(self, prices: list[PricePoint]) -> dict[str, float]:
        values = [p.price for p in prices]
        average = sum(values) / len(values)
        low = min(values)
        high = max(values)
        return {"average": average, "low": low, "high": high}

    def estimate_ev_block_kwh(self, price_point: PricePoint, ev: EVSettings) -> float:
        """Grovt anta hur mycket bilen hinner ladda under en period."""
        duration_hours = (price_point.end - price_point.start).total_seconds() / 3600
        kw = (ev.max_ampere * 230) / 1000  # enfas
        return duration_hours * kw * ev.efficiency

    def get_departure_time(self, ev: EVSettings | None) -> Optional[datetime]:
        if not ev or not ev.manual_departure_time:
            return None
        today = datetime.now().astimezone()
        dep_hour, dep_min = [int(x) for x in ev.manual_departure_time.split(":")]
        return today.replace(hour=dep_hour, minute=dep_min, second=0, microsecond=0)

    async def async_get_house_state(self, hass: HomeAssistant, entry) -> HouseState:
        """Plocka olika sensorvärden."""
        now = datetime.now().astimezone()

        avg = None
        temp = None
        overrides = {}

        house = entry.data["house_settings"]
        avg_entity = house.get("avg_consumption_sensor")
        if avg_entity:
            state = hass.states.get(avg_entity)
            if state:
                avg = float(state.state)

        temp_entity = house.get("temperature_sensor")
        if temp_entity:
            state = hass.states.get(temp_entity)
            if state:
                try:
                    temp = float(state.state)
                except ValueError:
                    temp = None

        return HouseState(
            avg_consumption_kw=avg,
            temperature_c=temp,
            projected_adjusted_kw=avg,
            last_update=now,
            overrides_active=overrides,
        )


class EnergyDispatcherStore:
    """Lokal storage för overrides och historik."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store = storage.Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(entry_id=entry_id)
        )

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        if data is None:
            data = {"overrides": []}
        return data

    async def async_save_override(self, override: dict[str, Any]) -> None:
        data = await self.async_load()
        data["overrides"].append(
            {
                "created": datetime.now().isoformat(),
                "override": override,
            }
        )
        await self._store.async_save(data)

    async def async_clear_overrides(self) -> None:
        await self._store.async_save({"overrides": []})
