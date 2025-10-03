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
    # EV/EVSE param
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    CONF_EVSE_START_SWITCH,
    CONF_EVSE_CURRENT_NUMBER,
    # Baseline
    CONF_RUNTIME_SOURCE,
    CONF_RUNTIME_COUNTER_ENTITY,
    CONF_RUNTIME_POWER_ENTITY,
    CONF_RUNTIME_ALPHA,
    CONF_RUNTIME_WINDOW_MIN,
    CONF_RUNTIME_EXCLUDE_EV,
    CONF_RUNTIME_EXCLUDE_BATT_GRID,
    CONF_RUNTIME_SOC_FLOOR,
    CONF_RUNTIME_SOC_CEILING,
    CONF_LOAD_POWER_ENTITY,
    CONF_BATT_POWER_ENTITY,
    CONF_GRID_IMPORT_TODAY_ENTITY,
)
from .models import PricePoint
from .price_provider import PriceProvider, PriceFees
from .forecast_provider import ForecastSolarProvider

_LOGGER = logging.getLogger(__name__)


class EnergyDispatcherCoordinator(DataUpdateCoordinator):
    """
    Samlar:
    - Priser (spot + enriched)
    - Aktuellt berikat pris
    - Huslast-baseline (W) och runtime-estimat
    - Solprognos + faktisk PV
    - Auto EV v0 + ETA
    - Ekonomi (grid vs batt)
    - Forecast vs Actual-delta (15m)
    """

    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=300),
        )
        self.entry_id: Optional[str] = None
        self.data: Dict[str, Any] = {
            "hourly_prices": [],
            "current_enriched": None,
            # Baseline
            "house_baseline_w": None,
            "baseline_method": None,
            "baseline_source_value": None,
            "baseline_kwh_per_h": None,
            "baseline_exclusion_reason": "",
            # Runtime + batteri
            "battery_runtime_h": None,
            # Sol
            "solar_points": [],
            "solar_now_w": None,
            "solar_today_kwh": None,
            "solar_tomorrow_kwh": None,
            # PV actual
            "pv_now_w": None,
            "pv_today_kwh": None,
            # Auto EV status
            "cheap_threshold": None,
            "auto_ev_setpoint_a": 0,
            "auto_ev_reason": "",
            "time_until_charge_ev_min": None,
            # Batteri placeholder
            "time_until_charge_batt_min": None,
            "batt_charge_reason": "not_implemented",
            # Ekonomi
            "grid_vs_batt_delta_sek_per_kwh": None,
            # Forecast vs actual (15m)
            "solar_delta_15m_w": None,
            "solar_delta_15m_pct": None,
        }

        # Historik/EMA för baseline (counter_kwh/power_w)
        self._baseline_prev_counter: Optional[Tuple[float, Any]] = None  # (kWh, ts)
        self._baseline_ema_kwh_per_h: Optional[float] = None
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
            await self._update_baseline_and_runtime()
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

        # P25-tröskel 24h framåt
        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        next24 = [p for p in hourly if 0 <= (p.time - now).total_seconds() < 24 * 3600]
        if next24:
            enriched = sorted([p.enriched_sek_per_kwh for p in next24])
            p25_idx = max(0, int(len(enriched) * 0.25) - 1)
            self.data["cheap_threshold"] = round(enriched[p25_idx], 4)
        else:
            self.data["cheap_threshold"] = None

    # ---------- baseline + runtime ----------
    def _read_float(self, entity_id: str) -> Optional[float]:
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in (None, "", "unknown", "unavailable"):
            return None
        try:
            return float(str(st.state).replace(",", "."))
        except Exception:
            return None

    def _is_ev_charging(self) -> bool:
        if not bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_EV, True)):
            return False
        start_sw = self._get_cfg(CONF_EVSE_START_SWITCH, "")
        num_current = self._get_cfg(CONF_EVSE_CURRENT_NUMBER, "")
        if start_sw:
            st = self.hass.states.get(start_sw)
            is_on = (st and str(st.state).lower() == "on")
        else:
            is_on = False
        amps = 0.0
        if num_current:
            try:
                amps = float(self.hass.states.get(num_current).state)
            except Exception:
                amps = 0.0
        min_a = int(self._get_cfg(CONF_EVSE_MIN_A, 6))
        return bool(is_on and amps >= min_a)

    def _is_batt_charging_from_grid(self) -> bool:
        if not bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_BATT_GRID, True)):
            return False
        batt_pw = self._read_float(self._get_cfg(CONF_BATT_POWER_ENTITY, ""))
        load_pw = self._read_float(self._get_cfg(CONF_LOAD_POWER_ENTITY, ""))
        pv_pw = self._read_float(self._get_cfg(CONF_PV_POWER_ENTITY, ""))
        if batt_pw is None or load_pw is None or pv_pw is None:
            return False
        batt_charge_w = max(0.0, -batt_pw)  # negativt = laddning
        pv_surplus_w = max(0.0, pv_pw - load_pw)
        grid_charge_w = max(0.0, batt_charge_w - pv_surplus_w)
        return grid_charge_w > 100.0

    async def _update_baseline_and_runtime(self):
        """
        Beräkna husets baseline (kWh/h) och Battery Runtime Estimate.
        - counter_kwh: derivata på kWh-räknare (t.ex. Consumption today)
        - power_w: W-sensor till kWh/h
        - manual_dayparts: ej implementerad än (placeholder)
        Exkluderar datapunkter vid EV-laddning och forcerad batteriladdning från grid.
        """
        method = self._get_cfg(CONF_RUNTIME_SOURCE, "counter_kwh")
        alpha = float(self._get_cfg(CONF_RUNTIME_ALPHA, 0.2))
        now = dt_util.now()

        excluded_reason = ""
        sample_kwh_per_h: Optional[float] = None
        source_val = None

        if method == "counter_kwh":
            ent = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
            kwh = self._read_float(ent)
            source_val = kwh
            if kwh is not None:
                prev = self._baseline_prev_counter
                self._baseline_prev_counter = (kwh, now)
                if prev:
                    prev_kwh, prev_ts = prev
                    dt_h = max(0.0, (now - prev_ts).total_seconds() / 3600.0)
                    delta = kwh - prev_kwh
                    # hantera dygnsreset/negativa hopp
                    if dt_h > 0 and delta >= 0:
                        sample_kwh_per_h = delta / dt_h

        elif method == "power_w":
            ent = self._get_cfg(CONF_RUNTIME_POWER_ENTITY, "")
            w = self._read_float(ent)
            source_val = w
            if w is not None and w >= 0:
                sample_kwh_per_h = w / 1000.0

        else:
            # manual_dayparts (placeholder)
            sample_kwh_per_h = None

        # Exkludera datapunkt för inlärning när EV eller grid-laddning pågår
        if sample_kwh_per_h is not None:
            if self._is_ev_charging():
                excluded_reason = "ev_charging"
                sample_for_ema = None
            elif self._is_batt_charging_from_grid():
                excluded_reason = "batt_grid_charge"
                sample_for_ema = None
            else:
                sample_for_ema = sample_kwh_per_h
        else:
            sample_for_ema = None

        # Klipp orimliga värden (0.05..5 kWh/h)
        if sample_for_ema is not None:
            sample_for_ema = max(0.05, min(5.0, sample_for_ema))

        # EMA
        if sample_for_ema is not None:
            if self._baseline_ema_kwh_per_h is None:
                self._baseline_ema_kwh_per_h = sample_for_ema
            else:
                self._baseline_ema_kwh_per_h = (alpha * sample_for_ema) + ((1 - alpha) * self._baseline_ema_kwh_per_h)

        # Publicera baseline data
        baseline_kwh_h = self._baseline_ema_kwh_per_h
        baseline_w = None if baseline_kwh_h is None else round(baseline_kwh_h * 1000.0, 1)
        self.data["house_baseline_w"] = baseline_w
        self.data["baseline_method"] = method
        self.data["baseline_source_value"] = source_val
        self.data["baseline_kwh_per_h"] = None if baseline_kwh_h is None else round(baseline_kwh_h, 4)
        self.data["baseline_exclusion_reason"] = excluded_reason

        # Battery runtime
        batt_cap = float(self._get_cfg(CONF_BATT_CAP_KWH, 0.0))
        soc_ent = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
        soc_state = self._read_float(soc_ent)
        soc_floor = float(self._get_cfg(CONF_RUNTIME_SOC_FLOOR, 10))
        soc_ceil = float(self._get_cfg(CONF_RUNTIME_SOC_CEILING, 95))

        if batt_cap and soc_state is not None and baseline_kwh_h and baseline_kwh_h > 0:
            span = max(1.0, soc_ceil - soc_floor)
            usable = max(0.0, min(1.0, (soc_state - soc_floor) / span))
            energy_kwh = usable * batt_cap
            runtime_h = round(energy_kwh / baseline_kwh_h, 2) if baseline_kwh_h > 0 else None
        else:
            runtime_h = None

        self.data["battery_runtime_h"] = runtime_h
        _LOGGER.debug(
            "Baseline: method=%s sample=%.4f kWh/h ema=%.4f kWh/h excl=%s | Runtime=%s h",
            method,
            -1.0 if sample_kwh_per_h is None else sample_kwh_per_h,
            -1.0 if self._baseline_ema_kwh_per_h is None else self._baseline_ema_kwh_per_h,
            excluded_reason or "none",
            runtime_h,
        )

    # ---------- solar ----------
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

    # ---------- Auto EV tick (oförändrad logik v0) ----------
    async def _auto_ev_tick(self):
        store = self._get_store()
        dispatcher = store.get("dispatcher")
        if not dispatcher:
            return

        now = dt_util.now()
        if hasattr(dispatcher, "is_paused") and dispatcher.is_paused(now):
            self.data["auto_ev_setpoint_a"] = 0
            self.data["auto_ev_reason"] = "override_pause"
            self.data["time_until_charge_ev_min"] = None
            return

        if hasattr(dispatcher, "is_forced") and dispatcher.is_forced(now):
            amps = dispatcher.get_forced_ev_current() or int(self._get_cfg(CONF_EVSE_MIN_A, 6))
            await dispatcher.async_apply_ev_setpoint(amps)
            self.data["auto_ev_setpoint_a"] = amps
            self.data["auto_ev_reason"] = "override_force"
            self.data["time_until_charge_ev_min"] = 0
            return

        if not self._get_flag("auto_ev_enabled", True):
            self.data["auto_ev_setpoint_a"] = 0
            self.data["auto_ev_reason"] = "auto_ev_off"
            self.data["time_until_charge_ev_min"] = None
            return

        phases = int(self._get_cfg(CONF_EVSE_PHASES, 3))
        voltage = int(self._get_cfg(CONF_EVSE_VOLTAGE, 230))
        min_a = int(self._get_cfg(CONF_EVSE_MIN_A, 6))
        max_a = int(self._get_cfg(CONF_EVSE_MAX_A, 16))
        max_w = phases * voltage * max_a

        price = self.data.get("current_enriched")
        p25 = self.data.get("cheap_threshold")

        pv_now_w = self.data.get("pv_now_w")
        if pv_now_w is None:
            pv_now_w = self.data.get("solar_now_w") or 0.0

        house_w = float(self.data.get("house_baseline_w") or 0.0)
        surplus_w = max(0.0, pv_now_w - house_w)

        def w_to_amps(w: float) -> int:
            return max(0, math.ceil(w / max(1, phases * voltage)))

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

        target_a = min(target_a, w_to_amps(max_w))
        await dispatcher.async_apply_ev_setpoint(target_a)

        self.data["auto_ev_setpoint_a"] = target_a
        self.data["auto_ev_reason"] = reason
        self.data["time_until_charge_ev_min"] = self._eta_until_next_charge(min_a, phases, voltage, p25, house_w)

    def _eta_until_next_charge(self, min_a: int, phases: int, voltage: int, cheap_threshold: Optional[float], house_w: float):
        now = dt_util.now()
        if int(self.data.get("auto_ev_setpoint_a") or 0) >= min_a:
            return 0

        # Billig timme
        t1 = None
        if cheap_threshold is not None:
            for p in self.data.get("hourly_prices") or []:
                if p.time >= now and p.enriched_sek_per_kwh <= cheap_threshold:
                    t1 = p.time
                    break

        # Solöverskott
        need_w = min_a * phases * voltage
        t2 = None
        for sp in self.data.get("solar_points") or []:
            if sp.time >= now and (sp.watts - house_w) >= need_w:
                t2 = sp.time
                break

        candidates = [t for t in [t1, t2] if t is not None]
        if not candidates:
            return None
        eta = min(candidates)
        return max(0, int((eta - now).total_seconds() // 60))

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
            pv_w = fc_w

        self._sf_history.append((now, float(fc_w), float(pv_w)))
        cutoff = now - timedelta(minutes=15)
        self._sf_history = [e for e in self._sf_history if e[0] >= cutoff]

        if len(self._sf_history) < 2:
            self.data["solar_delta_15m_w"] = 0.0
            self.data["solar_delta_15m_pct"] = 0.0
            return

        deltas = [(pv - fc) for (_, fc, pv) in self._sf_history]
        avg_delta = sum(deltas) / len(deltas)
        avg_fc = sum([fc for (_, fc, _) in self._sf_history]) / len(self._sf_history)
        pct = 0.0 if avg_fc == 0 else (avg_delta / avg_fc) * 100.0

        self.data["solar_delta_15m_w"] = round(avg_delta, 1)
        self.data["solar_delta_15m_pct"] = round(pct, 1)
