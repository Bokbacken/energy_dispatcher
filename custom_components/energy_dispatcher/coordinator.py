from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_PRICE_TAX,
    CONF_PRICE_TRANSFER,
    CONF_PRICE_SURCHARGE,
    CONF_PRICE_VAT,
    CONF_PRICE_FIXED_MONTHLY,
    CONF_PRICE_INCLUDE_FIXED,
    CONF_BATT_CAP_KWH,
    CONF_BATT_SOC_ENTITY,
    CONF_HOUSE_CONS_SENSOR,
    CONF_FS_USE,
    CONF_FS_APIKEY,
    CONF_FS_LAT,
    CONF_FS_LON,
    CONF_FS_PLANES,
    CONF_FS_HORIZON,
    CONF_PV_POWER_ENTITY,
    CONF_PV_ENERGY_TODAY_ENTITY,
)
from .models import PricePoint
from .price_provider import PriceProvider, PriceFees
from .forecast_provider import ForecastSolarProvider

_LOGGER = logging.getLogger(__name__)


class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=300),
        )
        self.entry_id: Optional[str] = None
        self.data: Dict[str, Any] = {
            "hourly_prices": [],            # List[PricePoint]
            "current_enriched": None,       # float
            "battery_runtime_h": None,      # float
            "solar_points": [],             # List[ForecastPoint]
            "solar_now_w": None,            # float
            "solar_today_kwh": None,        # float
            "solar_tomorrow_kwh": None,     # float
            "pv_now_w": None,               # float (aktuell produktion)
            "pv_today_kwh": None,           # float (energi idag)
        }

    def _get_store(self) -> Dict[str, Any]:
        if not self.entry_id:
            return {}
        return self.hass.data.get(DOMAIN, {}).get(self.entry_id, {})

    def _get_cfg(self, key: str, default=None):
        store = self._get_store()
        cfg = store.get("config", {})
        return cfg.get(key, default)

    async def _async_update_data(self):
        try:
            await self._update_prices()
            await self._update_battery_runtime()
            await self._update_solar()
            await self._update_pv_actual()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Uppdatering misslyckades")
        return self.data

    async def _update_prices(self):
        nordpool_entity = self._get_cfg(CONF_NORDPOOL_ENTITY, "")
        if not nordpool_entity:
            self.data["hourly_prices"] = []
            self.data["current_enriched"] = None
            _LOGGER.debug("Ingen Nordpool-entity konfigurerad")
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
        _LOGGER.debug("Priser uppdaterade: %s rader, current_enriched=%s",
                      len(hourly), self.data["current_enriched"])

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

        val = None if runtime_h is None else round(runtime_h, 2)
        self.data["battery_runtime_h"] = val
        _LOGGER.debug("Battery runtime estimate: %s h (SOC=%s%%, cap=%s kWh, avg=%s kWh/h)",
                      val, soc, batt_cap, avg_kwh_per_h)

    def _trapz_kwh(self, points):
        if not points or len(points) < 2:
            return 0.0
        pts = sorted(points, key=lambda p: p.time)
        energy_wh = 0.0
        for a, b in zip(pts, pts[1:]):
            dt_h = (b.time - a.time).total_seconds() / 3600.0
            w_avg = (a.watts + b.watts) / 2.0
            energy_wh += w_avg * dt_h
        return round(energy_wh / 1000.0, 3)

    async def _update_solar(self):
        use = bool(self._get_cfg(CONF_FS_USE, True))
        if not use:
            self.data.update({
                "solar_points": [],
                "solar_now_w": None,
                "solar_today_kwh": None,
                "solar_tomorrow_kwh": None,
            })
            _LOGGER.debug("Forecast.Solar avstängt (fs_use=False)")
            return

        apikey = self._get_cfg(CONF_FS_APIKEY, "")
        lat = float(self._get_cfg(CONF_FS_LAT, 0.0))
        lon = float(self._get_cfg(CONF_FS_LON, 0.0))
        planes = self._get_cfg(CONF_FS_PLANES, "[]")
        horizon = self._get_cfg(CONF_FS_HORIZON, "")

        provider = ForecastSolarProvider(
            self.hass, lat=lat, lon=lon, planes_json=planes, apikey=apikey, horizon_csv=horizon
        )
        pts = await provider.async_fetch_watts()
        self.data["solar_points"] = pts

        now = dt_util.now().replace(second=0, microsecond=0)
        if pts:
            nearest = min(pts, key=lambda p: abs((p.time - now).total_seconds()))
            self.data["solar_now_w"] = round(nearest.watts, 1)
        else:
            self.data["solar_now_w"] = 0.0

        today = now.date()
        tomorrow = (now + timedelta(days=1)).date()
        today_pts = [p for p in pts if p.time.date() == today]
        tomo_pts = [p for p in pts if p.time.date() == tomorrow]

        self.data["solar_today_kwh"] = self._trapz_kwh(today_pts) if today_pts else 0.0
        self.data["solar_tomorrow_kwh"] = self._trapz_kwh(tomo_pts) if tomo_pts else 0.0

        _LOGGER.debug(
            "Forecast.Solar: points=%s, now=%s W, today=%s kWh, tomorrow=%s kWh",
            len(pts), self.data["solar_now_w"], self.data["solar_today_kwh"], self.data["solar_tomorrow_kwh"]
        )

    async def _update_pv_actual(self):
        """Läs faktiska produktionssensorer (om konfigurerade) och konvertera enheter."""
        pv_power_entity = self._get_cfg(CONF_PV_POWER_ENTITY, "")
        pv_energy_entity = self._get_cfg(CONF_PV_ENERGY_TODAY_ENTITY, "")

        # Effekt (W eller kW)
        pv_now = None
        if pv_power_entity:
            st = self.hass.states.get(pv_power_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                try:
                    val = float(st.state)
                    unit = str(st.attributes.get("unit_of_measurement", "")).lower()
                    if "kw" in unit and "mw" not in unit:
                        pv_now = round(val * 1000.0, 1)
                    elif "mw" in unit:
                        pv_now = round(val * 1_000_000.0, 1)
                    else:
                        pv_now = round(val, 1)  # antar W
                except Exception:
                    pv_now = None
        self.data["pv_now_w"] = pv_now

        # Energi idag (Wh eller kWh)
        pv_today = None
        if pv_energy_entity:
            st = self.hass.states.get(pv_energy_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                try:
                    val = float(st.state)
                    unit = str(st.attributes.get("unit_of_measurement", "")).lower()
                    if "wh" in unit and "kwh" not in unit and "mwh" not in unit:
                        pv_today = round(val / 1000.0, 3)  # Wh -> kWh
                    elif "mwh" in unit:
                        pv_today = round(val * 1000.0, 3)
                    else:
                        pv_today = round(val, 3)  # antar kWh
                except Exception:
                    pv_today = None
        self.data["pv_today_kwh"] = pv_today

        _LOGGER.debug("PV actual: now=%s W, today=%s kWh (power_entity=%s, energy_entity=%s)",
                      pv_now, pv_today, pv_power_entity, pv_energy_entity)
