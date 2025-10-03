from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
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
    # Forecast.Solar-konfig
    CONF_FS_USE,
    CONF_FS_APIKEY,
    CONF_FS_LAT,
    CONF_FS_LON,
    CONF_FS_PLANES,
    CONF_FS_HORIZON,
    # PV actual
    CONF_PV_POWER_ENTITY,
    CONF_PV_ENERGY_TODAY_ENTITY,
    # EV/EVSE för beslutsparametrar
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
)
from .models import PricePoint
from .price_provider import PriceProvider, PriceFees
from .forecast_provider import ForecastSolarProvider

_LOGGER = logging.getLogger(__name__)


class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    """
    Samlar:
    - Timvisa priser (spot + enriched)
    - Aktuellt berikat pris
    - Batteriets uppskattade driftstid
    - Solprognos (nu, idag, imorgon)
    - Faktisk PV-produktion (nu, idag)
    - Enkel Auto EV v0 (setpoint i A + orsak)
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
            "solar_points": [],             # List[ForecastPoint]
            "solar_now_w": None,            # float
            "solar_today_kwh": None,        # float
            "solar_tomorrow_kwh": None,     # float
            "pv_now_w": None,               # float
            "pv_today_kwh": None,           # float
            # Auto EV status
            "cheap_threshold": None,        # SEK/kWh (P25)
            "auto_ev_setpoint_a": 0,
            "auto_ev_reason": "",
        }

    # ---------- helpers ----------
    def _get_store(self) -> Dict[str, Any]:
        if not self.entry_id:
            return {}
        return self.hass.data.get(DOMAIN, {}).get(self.entry_id, {})

    def _get_cfg(self, key: str, default=None):
        store = self._get_store()
        cfg = store.get("config", {})
        return cfg.get(key, default)

    def _get_flag(self, key: str, default=None):
        store = self._get_store()
        flags = store.get("flags", {})
        return flags.get(key, default)

    # ---------- update loop ----------
    async def _async_update_data(self):
        try:
            await self._update_prices()
            await self._update_battery_runtime()
            await self._update_solar()
            await self._update_pv_actual()
            await self._auto_ev_tick()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Uppdatering misslyckades")
        return self.data

    # ---------- prices ----------
    async def _update_prices(self):
        nordpool_entity = self._get_cfg(CONF_NORDPOOL_ENTITY, "")
        if not nordpool_entity:
            self.data["hourly_prices"] = []
            self.data["current_enriched"] = None
            self.data["cheap_threshold"] = None
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

        # P25-tröskel på kommande 24h (inkl. pågående timme)
        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        next24 = [p for p in hourly if 0 <= (p.time - now).total_seconds() < 24 * 3600]
        if next24:
            enriched = sorted([p.enriched_sek_per_kwh for p in next24])
            p25_idx = max(0, int(len(enriched) * 0.25) - 1)
            self.data["cheap_threshold"] = round(enriched[p25_idx], 4)
        else:
            self.data["cheap_threshold"] = None

        _LOGGER.debug(
            "Priser uppdaterade: %s rader, current_enriched=%s, p25=%s",
            len(hourly), self.data["current_enriched"], self.data["cheap_threshold"]
        )

    # ---------- battery runtime ----------
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
        _LOGGER.debug(
            "Battery runtime estimate: %s h (SOC=%s%%, cap=%s kWh, avg=%s kWh/h)",
            val, soc, batt_cap, avg_kwh_per_h
        )

    # ---------- solar forecast ----------
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

    # ---------- PV actual ----------
    async def _update_pv_actual(self):
        pv_power_entity = self._get_cfg(CONF_PV_POWER_ENTITY, "")
        pv_energy_entity = self._get_cfg(CONF_PV_ENERGY_TODAY_ENTITY, "")

        pv_now = None
        if pv_power_entity:
            st = self.hass.states.get(pv_power_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                try:
                    val = float(st.state)
                    unit = str(st.attributes.get("unit_of_measurement", "")).lower()
                    if "mw" in unit:
                        pv_now = round(val * 1_000_000.0, 1)
                    elif "kw" in unit:
                        pv_now = round(val * 1000.0, 1)
                    else:
                        pv_now = round(val, 1)  # antar W
                except Exception:
                    pv_now = None
        self.data["pv_now_w"] = pv_now

        pv_today = None
        if pv_energy_entity:
            st = self.hass.states.get(pv_energy_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                try:
                    val = float(st.state)
                    unit = str(st.attributes.get("unit_of_measurement", "")).lower()
                    if "mwh" in unit:
                        pv_today = round(val * 1000.0, 3)
                    elif "wh" in unit and "kwh" not in unit:
                        pv_today = round(val / 1000.0, 3)
                    else:
                        pv_today = round(val, 3)  # antar kWh
                except Exception:
                    pv_today = None
        self.data["pv_today_kwh"] = pv_today

        _LOGGER.debug(
            "PV actual: now=%s W, today=%s kWh (power_entity=%s, energy_entity=%s)",
            pv_now, pv_today, pv_power_entity, pv_energy_entity
        )

    # ---------- Auto EV tick ----------
    async def _auto_ev_tick(self):
        store = self._get_store()
        dispatcher = store.get("dispatcher")
        if not dispatcher:
            return

        now = dt_util.now()
        if dispatcher.is_paused(now):
            self.data["auto_ev_setpoint_a"] = 0
            self.data["auto_ev_reason"] = "override_pause"
            _LOGGER.debug("Auto EV: paus override aktiv – ingen styrning.")
            return

        # Force-override: kör på given ström.
        if dispatcher.is_forced(now):
            amps = dispatcher.get_forced_ev_current() or int(self._get_cfg(CONF_EVSE_MIN_A, 6))
            await dispatcher.async_apply_ev_setpoint(amps)
            self.data["auto_ev_setpoint_a"] = amps
            self.data["auto_ev_reason"] = "override_force"
            _LOGGER.debug("Auto EV: force override %s A", amps)
            return

        if not self._get_flag("auto_ev_enabled", True):
            self.data["auto_ev_setpoint_a"] = 0
            self.data["auto_ev_reason"] = "auto_ev_off"
            return

        # Parametrar
        phases = int(self._get_cfg(CONF_EVSE_PHASES, 3))
        voltage = int(self._get_cfg(CONF_EVSE_VOLTAGE, 230))
        min_a = int(self._get_cfg(CONF_EVSE_MIN_A, 6))
        max_a = int(self._get_cfg(CONF_EVSE_MAX_A, 16))
        max_w = phases * voltage * max_a

        price = self.data.get("current_enriched")
        p25 = self.data.get("cheap_threshold")

        # PV-överskott "nu": använd faktisk PV om tillgängligt, annars prognosen
        pv_now_w = self.data.get("pv_now_w")
        if pv_now_w is None:
            pv_now_w = self.data.get("solar_now_w") or 0.0
        house_cons_entity = self._get_cfg(CONF_HOUSE_CONS_SENSOR, "")
        surplus_w = pv_now_w
        if house_cons_entity:
            st = self.hass.states.get(house_cons_entity)
            try:
                avg_kwh_per_h = float(st.state)  # kWh/h ~ kW
                house_now_w = max(0.0, avg_kwh_per_h * 1000.0)
                surplus_w = max(0.0, pv_now_w - house_now_w)
            except Exception:
                pass

        def w_to_amps(w: float) -> int:
            return max(0, math.ceil(w / max(1, phases * voltage)))

        # Enkel mål-SOC-fallback mot 07:00
        # Om kWh som krävs inte ryms på >2h kvar, börja ladda oavsett pris.
        ev_manual = store.get("ev_manual")
        must_charge_now = False
        required_amps_for_target = 0
        try:
            if ev_manual and hasattr(ev_manual, "ev_batt_kwh"):
                current_soc = float(ev_manual.ev_current_soc)
                target_soc = float(ev_manual.ev_target_soc)
                batt_kwh = float(ev_manual.ev_batt_kwh)
                need_kwh = max(0.0, (target_soc - current_soc) / 100.0) * batt_kwh

                t_target = now.replace(hour=7, minute=0, second=0, microsecond=0)
                if t_target <= now:
                    t_target = t_target + timedelta(days=1)
                hrs_left = max(0.1, (t_target - now).total_seconds() / 3600.0)

                # Effekt som krävs för att nå mål (utan verkningsgradskorrigering)
                req_kw = need_kwh / hrs_left
                required_amps_for_target = w_to_amps(req_kw * 1000.0)
                # Om vi behöver nära max eller om det är <2 h kvar och vi har behov -> kör nu
                if need_kwh > 0 and (hrs_left <= 2.0 or required_amps_for_target >= max_a):
                    must_charge_now = True
        except Exception:
            pass

        # Beslutslogik
        reason = "idle"
        target_a = 0

        # 1) Om solöverskott finns, använd det
        solar_a = w_to_amps(surplus_w)
        if solar_a >= min_a:
            target_a = max(min_a, min(max_a, solar_a))
            reason = "pv_surplus"

        # 2) Annars om pris under P25-tröskel
        elif price is not None and p25 is not None and price <= p25:
            target_a = max(min_a, min(max_a, required_amps_for_target or min_a))
            reason = "cheap_hour"

        # 3) Fallback mot mål-SOC nära deadline
        elif must_charge_now and required_amps_for_target > 0:
            target_a = max(min_a, min(max_a, required_amps_for_target))
            reason = "deadline"

        # 4) Annars stoppa
        else:
            target_a = 0
            reason = "expensive_or_no_need"

        # Säkerhetsklipp baserat på max W
        target_a = min(target_a, w_to_amps(max_w))

        # Applicera
        await dispatcher.async_apply_ev_setpoint(target_a)

        self.data["auto_ev_setpoint_a"] = target_a
        self.data["auto_ev_reason"] = reason
        _LOGGER.debug(
            "Auto EV: setpoint=%s A, reason=%s (price=%s, p25=%s, pv_surplus_w=%s, reqA=%s)",
            target_a, reason, price, p25, surplus_w, required_amps_for_target
        )
