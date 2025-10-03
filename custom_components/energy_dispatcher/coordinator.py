from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_NORDPOOL_ENTITY, CONF_PRICE_TAX, CONF_PRICE_TRANSFER, CONF_PRICE_SURCHARGE, CONF_PRICE_VAT, CONF_PRICE_FIXED_MONTHLY, CONF_PRICE_INCLUDE_FIXED, CONF_BATT_CAP_KWH, CONF_BATT_SOC_ENTITY, CONF_HOUSE_CONS_SENSOR
from .models import PricePoint
from .price_provider import PriceProvider, PriceFees

_LOGGER = logging.getLogger(__name__)


class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    """
    Hämtar och sammanställer:
    - Timvisa priser (spot + enriched)
    - Aktuellt berikat pris (just nu)
    - Batteriets driftstid (h) givet husets snittförbrukning
    - (Plats för WACE m.m. i framtida uppdateringar)
    """

    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=300),
        )
        self.entry_id: Optional[str] = None  # sätts i __init__.py
        self.data: Dict[str, Any] = {
            "hourly_prices": [],            # List[PricePoint]
            "current_enriched": None,       # float
            "battery_runtime_h": None,      # float
        }

    def _get_cfg(self, key: str, default=None):
        if not self.entry_id:
            return default
        store = self.hass.data.get(DOMAIN, {}).get(self.entry_id, {})
        cfg = store.get("config", {})
        return cfg.get(key, default)

    def _get_flag(self, key: str, default=None):
        if not self.entry_id:
            return default
        store = self.hass.data.get(DOMAIN, {}).get(self.entry_id, {})
        flags = store.get("flags", {})
        return flags.get(key, default)

    async def _async_update_data(self):
        try:
            await self._update_prices()
            await self._update_battery_runtime()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Uppdatering misslyckades")
        return self.data

    async def _update_prices(self):
        nordpool_entity = self._get_cfg(CONF_NORDPOOL_ENTITY, "")
        if not nordpool_entity:
            self.data["hourly_prices"] = []
            self.data["current_enriched"] = None
            return

        fees = PriceFees(
            tax=float(self._get_cfg(CONF_PRICE_TAX, 0.0)),
            transfer=float(self._get_cfg(CONF_PRICE_TRANSFER, 0.0)),
            surcharge=float(self._get_cfg(CONF_PRICE_SURCHARGE, 0.0)),
            vat=float(self._get_cfg(CONF_PRICE_VAT, 0.25)),
            fixed_monthly=float(self._get_cfg(CONF_PRICE_FIXED_MONTHLY, 0.0)),
            include_fixed=bool(self._get_cfg(CONF_PRICE_INCLUDE_FIXED, False)),
        )

        provider = PriceProvider(self.hass, nordpool_entity=nordpool_entity, fees=fees)
        hourly: List[PricePoint] = provider.get_hourly_prices()
        self.data["hourly_prices"] = hourly
        self.data["current_enriched"] = provider.get_current_enriched(hourly)

    async def _update_battery_runtime(self):
        batt_cap = float(self._get_cfg(CONF_BATT_CAP_KWH, 0.0))
        soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
        house_cons_entity = self._get_cfg(CONF_HOUSE_CONS_SENSOR, "")

        if not batt_cap or not soc_entity:
            self.data["battery_runtime_h"] = None
            return

        soc_state = self.hass.states.get(soc_entity)
        try:
            soc = float(soc_state.state)  # %
        except Exception:
            soc = None

        if soc is None:
            self.data["battery_runtime_h"] = None
            return

        energy_kwh = max(0.0, min(1.0, soc / 100.0)) * batt_cap

        avg_kwh_per_h = None
        if house_cons_entity:
            cons_state = self.hass.states.get(house_cons_entity)
            try:
                avg_kwh_per_h = float(cons_state.state)
            except Exception:
                avg_kwh_per_h = None

        if avg_kwh_per_h and avg_kwh_per_h > 0:
            runtime_h = energy_kwh / avg_kwh_per_h
        else:
            runtime_h = None

        self.data["battery_runtime_h"] = None if runtime_h is None else round(runtime_h, 2)
