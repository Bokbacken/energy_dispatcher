from __future__ import annotations

import logging
import math
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

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
    - Auto EV v0 (setpoint i A + orsak + ETA)
    - Forecast vs Actual-delta (15m medel)
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
            "time_until_charge_ev_min": None,
            # Batteri (placeholder tills auto-batt implementeras)
            "time_until_charge_batt_min": None,
            "batt_charge_reason": "not_implemented",
            # Ekonomi
            "grid_vs_batt_delta_sek_per_kwh": None,
            # Forecast vs actual (15m)
            "solar_delta_15m_w": None,
            "solar_delta_15m_pct": None,
        }
        # Historik för delta-beräkning
        self._sf_history: List[Tuple[Any, float, float]] = []  # (ts, forecast_w, actual_w)

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
            self._update_grid_vs_batt_delta()
            self._update_solar_delta_15m()
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
            self.data["time_until_charge_ev_min"] = None
            _LOGGER.debug("Auto EV: paus override aktiv – ingen styrning.")
            return

        # Force-override: kör på given ström.
        if dispatcher.is_forced(now):
            amps = dispatcher.get_forced_ev_current() or int(self._get_cfg(CONF_EVSE_MIN_A, 6))
            await dispatcher.async_apply_ev_setpoint(amps)
            self.data["auto_ev_setpoint_a"] = amps
            self.data["auto_ev_reason"] = "override_force"
            self.data["time_until_charge_ev_min"] = 0
            _LOGGER.debug("Auto EV: force override %s A", amps)
            return

        if not self._get_flag("auto_ev_enabled", True):
            self.data["auto_ev_setpoint_a"] = 0
            self.data["auto_ev_reason"] = "auto_ev_off"
            self.data["time_until_charge_ev_min"] = None
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

        # Enkel beslutslogik
        reason = "idle"
        target_a = 0

        solar_a = w_to_amps(surplus_w)
        if solar_a >= min_a:
            target_a = max(min_a, min(max_a, solar_a))
            reason = "pv_surplus"
        elif price is not None and p25 is not None and price <= p25:
            target_a = min_a
            reason = "cheap_hour"
        else:
            target_a = 0
            reason = "expensive_or_no_need"

        # Säkerhet
        target_a = min(target_a, w_to_amps(max_w))
        await dispatcher.async_apply_ev_setpoint(target_a)

        self.data["auto_ev_setpoint_a"] = target_a
        self.data["auto_ev_reason"] = reason
        self.data["time_until_charge_ev_min"] = self._eta_until_next_charge(min_a, phases, voltage, p25)

        _LOGGER.debug(
            "Auto EV: setpoint=%s A, reason=%s (price=%s, p25=%s, pv_surplus_w=%s)",
            target_a, reason, price, p25, surplus_w
        )

    def _eta_until_next_charge(self, min_a: int, phases: int, voltage: int, cheap_threshold: Optional[float]):
        """
        Grov uppskattning av tid tills vi börjar ladda (minuter):
         - Nästa timme där enriched <= p25
         - Nästa tidpunkt med prognosticerat solöverskott som räcker för min_a
        """
        now = dt_util.now()
        # Om redan laddning: 0
        if int(self.data.get("auto_ev_setpoint_a") or 0) >= min_a:
            return 0

        # Kandidat 1: billig timme
        t1 = None
        if cheap_threshold is not None:
            for p in self.data.get("hourly_prices") or []:
                if p.time >= now and p.enriched_sek_per_kwh <= cheap_threshold:
                    t1 = p.time
                    break

        # Kandidat 2: solöverskott
        t2 = None
        solar_pts = self.data.get("solar_points") or []
        house_w = 0.0
        house_cons_entity = self._get_cfg(CONF_HOUSE_CONS_SENSOR, "")
        if house_cons_entity:
            st = self.hass.states.get(house_cons_entity)
            try:
                house_w = max(0.0, float(st.state) * 1000.0)
            except Exception:
                house_w = 0.0

        need_w = min_a * phases * voltage
        for sp in solar_pts:
            if sp.time >= now and (sp.watts - house_w) >= need_w:
                t2 = sp.time
                break

        candidates = [t for t in [t1, t2] if t is not None]
        if not candidates:
            return None
        eta = min(candidates)
        minutes = max(0, int((eta - now).total_seconds() // 60))
        return minutes

    # ---------- Ekonomi ----------
    def _update_grid_vs_batt_delta(self):
        store = self._get_store()
        wace = float(store.get("wace", 0.0))
        grid = self.data.get("current_enriched")
        if grid is None:
            self.data["grid_vs_batt_delta_sek_per_kwh"] = None
            return
        self.data["grid_vs_batt_delta_sek_per_kwh"] = round(grid - wace, 6)

    # ---------- Forecast vs Actual 15m ----------
    def _update_solar_delta_15m(self):
        now = dt_util.now()
        fc_w = self.data.get("solar_now_w") or 0.0
        pv_w = self.data.get("pv_now_w")
        if pv_w is None:
            pv_w = fc_w  # om ingen faktisk sensor, delta=0

        # Lägg till punkt och trimma äldre än 15 min
        self._sf_history.append((now, float(fc_w), float(pv_w)))
        cutoff = now - timedelta(minutes=15)
        self._sf_history = [e for e in self._sf_history if e[0] >= cutoff]

        if len(self._sf_history) < 2:
            self.data["solar_delta_15m_w"] = 0.0
            self.data["solar_delta_15m_pct"] = 0.0
            return

        deltas = [(pv - fc) for (_, fc, pv) in self._sf_history]
        avg_delta = sum(deltas) / len(deltas)

        # Procent relativt genomsnittlig forecast under perioden
        avg_fc = sum([fc for (_, fc, _) in self._sf_history]) / len(self._sf_history)
        pct = 0.0 if avg_fc == 0 else (avg_delta / avg_fc) * 100.0

        self.data["solar_delta_15m_w"] = round(avg_delta, 1)
        self.data["solar_delta_15m_pct"] = round(pct, 1)
