from __future__ import annotations

import logging
import math
from datetime import timedelta, datetime
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
    CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY,
    CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY,
    CONF_BATT_CAPACITY_ENTITY,
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
    CONF_RUNTIME_EXCLUDE_EV,
    CONF_RUNTIME_EXCLUDE_BATT_GRID,
    CONF_RUNTIME_SOC_FLOOR,
    CONF_RUNTIME_SOC_CEILING,
    CONF_LOAD_POWER_ENTITY,
    CONF_BATT_POWER_ENTITY,
    CONF_BATT_POWER_INVERT_SIGN,
    CONF_GRID_IMPORT_TODAY_ENTITY,
    CONF_RUNTIME_LOOKBACK_HOURS,
    CONF_RUNTIME_USE_DAYPARTS,
)
from .models import PricePoint
from .price_provider import PriceProvider, PriceFees
from .forecast_provider import ForecastSolarProvider

_LOGGER = logging.getLogger(__name__)


def _safe_float(v: Any, default: Optional[float] = None) -> Optional[float]:
    """Tolerant parse till float. Hanterar None, unknown/unavailable och decimal‑komma."""
    if v is None:
        return default
    try:
        if isinstance(v, (int, float)):
            f = float(v)
            if math.isnan(f):
                return default
            return f
        s = str(v).strip()
        if s in ("", "unknown", "unavailable", "None", "nan"):
            return default
        s = s.replace(",", ".")
        f = float(s)
        if math.isnan(f):
            return default
        return f
    except Exception:
        return default


def _as_watts(value: Any, unit: Optional[str]) -> Optional[float]:
    """Konvertera till W om möjligt. kW→W, MW→W. Saknas unit -> anta W."""
    val = _safe_float(value)
    if val is None:
        return None
    u = (unit or "").lower()
    if u == "kw":
        return val * 1000.0
    if u == "mw":
        return val * 1_000_000.0
    # "w", "watt" eller okänt → returnera som är (antar W)
    return val


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

    0.5.4 patchar baseline:
    - Robust exkluderingar (EV/batteri) → inga "unknown"
    - Bootstrap från Recorder-historik vid omstart (power_w)
    - Tolerant parsing och kW/MW→W
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
            # Daypart baselines (night/day/evening)
            "baseline_night_w": None,
            "baseline_day_w": None,
            "baseline_evening_w": None,
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

        # Historik för baseline (counter_kwh)
        self._baseline_prev_counter: Optional[Tuple[float, Any]] = None  # (kWh, ts)
        self._sf_history: List[Tuple[Any, float, float]] = []  # (ts, forecast_w, actual_w)
        
        # Battery charge/discharge tracking
        self._batt_prev_charged_today: Optional[float] = None  # kWh charged today (previous value)
        self._batt_prev_discharged_today: Optional[float] = None  # kWh discharged today (previous value)
        self._batt_last_reset_date: Optional[Any] = None  # Track daily reset

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

    def _read_float(self, entity_id: str) -> Optional[float]:
        """Legacy: läs numeriskt värde utan att titta på enhet."""
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in (None, "", "unknown", "unavailable"):
            return None
        return _safe_float(st.state)

    def _read_watts(self, entity_id: str) -> Optional[float]:
        """Läs effekt i W, med automatisk konvertering kW/MW→W."""
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in (None, "", "unknown", "unavailable"):
            return None
        unit = st.attributes.get("unit_of_measurement")
        return _as_watts(st.state, unit)
    
    def _read_battery_power_normalized(self) -> Optional[float]:
        """Read battery power normalized to standard convention (positive=charging)."""
        batt_power_w = self._read_float(self._get_cfg(CONF_BATT_POWER_ENTITY, ""))
        if batt_power_w is None:
            return None
        
        # Apply sign inversion if configured (for Huawei-style sensors)
        invert_sign = self._get_cfg(CONF_BATT_POWER_INVERT_SIGN, False)
        if invert_sign:
            batt_power_w = -batt_power_w
        
        return batt_power_w

    # ---------- update loop ----------
    async def _async_update_data(self):
        try:
            await self._update_prices()
            await self._update_baseline_and_runtime()
            await self._update_solar()
            await self._update_pv_actual()
            await self._update_battery_charge_tracking()
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
    def _is_ev_charging(self) -> bool:
        # Om vi har ström-siffran, använd den som primär indikator
        if not bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_EV, True)):
            return False
        num_current = self._get_cfg(CONF_EVSE_CURRENT_NUMBER, "")
        amps = 0.0
        if num_current:
            st = self.hass.states.get(num_current)
            amps = _safe_float(st.state, 0.0) if st and st.state not in ("unknown", "unavailable", None, "") else 0.0
        min_a = int(self._get_cfg(CONF_EVSE_MIN_A, 6))
        if amps and amps >= min_a:
            return True

        # Fallback: bara om start-entity är en switch/input_boolean och står ON
        start_sw = self._get_cfg(CONF_EVSE_START_SWITCH, "")
        if start_sw and start_sw.split(".")[0] in ("switch", "input_boolean"):
            st = self.hass.states.get(start_sw)
            return bool(st and str(st.state).lower() == "on")

        return False

    def _is_batt_charging_from_grid(self) -> bool:
        """Konservativ heuristik: om batterisensorn visar laddning och PV-överskott inte täcker, anta grid."""
        if not bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_BATT_GRID, True)):
            return False

        batt_pw = self._read_battery_power_normalized()
        load_pw = self._read_watts(self._get_cfg(CONF_LOAD_POWER_ENTITY, "")) or self._read_watts(self._get_cfg(CONF_RUNTIME_POWER_ENTITY, ""))  # W
        pv_pw = self._read_watts(self._get_cfg(CONF_PV_POWER_ENTITY, ""))

        if batt_pw is None or load_pw is None or pv_pw is None:
            # Saknas data ⇒ var försiktig: returnera False (låt inte exkludering döda baseline)
            return False

        # Standard convention: positive = charging, negative = discharging
        batt_charge_w = max(0.0, batt_pw)
        pv_surplus_w = max(0.0, pv_pw - load_pw)
        grid_charge_w = max(0.0, batt_charge_w - pv_surplus_w)
        return grid_charge_w > 100.0



    def _classify_hour_daypart(self, hour: int) -> str:
        """Classify hour into daypart: night (0-7), day (8-15), evening (16-23)."""
        if 0 <= hour < 8:
            return "night"
        elif 8 <= hour < 16:
            return "day"
        else:
            return "evening"

    async def _calculate_48h_baseline(self) -> Optional[Dict[str, Optional[float]]]:
        """
        Calculate baseline from last 48 hours with time-of-day weighting.
        Returns dict with keys: overall, night, day, evening (all in kWh/h).
        Excludes EV charging and battery grid charging periods.
        """
        lookback_hours = int(self._get_cfg(CONF_RUNTIME_LOOKBACK_HOURS, 48))
        use_dayparts = bool(self._get_cfg(CONF_RUNTIME_USE_DAYPARTS, True))
        
        # Get the power entity
        ent = self._get_cfg(CONF_RUNTIME_POWER_ENTITY, "") or self._get_cfg(CONF_LOAD_POWER_ENTITY, "") or self._get_cfg(CONF_HOUSE_CONS_SENSOR, "")
        if not ent:
            _LOGGER.debug(
                "48h baseline: No power entity configured (runtime_power_entity, load_power_entity, or house_cons_sensor)"
            )
            return None
            
        try:
            from homeassistant.components.recorder import history
            
            end = dt_util.now()
            start = end - timedelta(hours=lookback_hours)
            
            # Fetch historical data for house load
            hist = await self.hass.async_add_executor_job(
                history.state_changes_during_period, self.hass, start, end, {ent}
            )
            states = hist.get(ent, [])
            
            if not states:
                _LOGGER.debug("No historical data available for baseline calculation")
                return None
            
            # Also fetch EV charging and battery power data for exclusions
            ev_power_ent = self._get_cfg(CONF_EVSE_POWER_SENSOR, "")
            batt_power_ent = self._get_cfg(CONF_BATT_POWER_ENTITY, "")
            pv_power_ent = self._get_cfg(CONF_PV_POWER_ENTITY, "")
            
            entities_to_fetch = {ent}
            if ev_power_ent:
                entities_to_fetch.add(ev_power_ent)
            if batt_power_ent:
                entities_to_fetch.add(batt_power_ent)
            if pv_power_ent:
                entities_to_fetch.add(pv_power_ent)
            
            # Fetch all needed entities in one call
            all_hist = await self.hass.async_add_executor_job(
                history.state_changes_during_period, self.hass, start, end, entities_to_fetch
            )
            
            # Build dictionaries by timestamp for easier lookup
            ev_states_by_time = {}
            batt_states_by_time = {}
            pv_states_by_time = {}
            
            if ev_power_ent:
                for s in all_hist.get(ev_power_ent, []):
                    ev_states_by_time[s.last_changed] = s
            
            if batt_power_ent:
                for s in all_hist.get(batt_power_ent, []):
                    batt_states_by_time[s.last_changed] = s
            
            if pv_power_ent:
                for s in all_hist.get(pv_power_ent, []):
                    pv_states_by_time[s.last_changed] = s
            
            # Collect samples by daypart
            daypart_samples = {
                "night": [],
                "day": [],
                "evening": [],
            }
            
            exclude_ev = bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_EV, True))
            exclude_batt_grid = bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_BATT_GRID, True))
            
            for state in states:
                # Parse house load power
                w = _as_watts(state.state, state.attributes.get("unit_of_measurement"))
                if w is None or math.isnan(w) or w < 0:
                    continue
                
                timestamp = state.last_changed
                hour = timestamp.hour
                daypart = self._classify_hour_daypart(hour)
                
                # Check if we should exclude this sample
                should_exclude = False
                
                # Check EV charging exclusion
                if exclude_ev and ev_power_ent:
                    # Find closest EV power state
                    ev_state = self._find_closest_state(ev_states_by_time, timestamp)
                    if ev_state:
                        ev_power = _safe_float(ev_state.state)
                        if ev_power and ev_power > 100:  # EV charging if > 100W
                            should_exclude = True
                
                # Check battery grid charging exclusion
                if not should_exclude and exclude_batt_grid and batt_power_ent:
                    batt_state = self._find_closest_state(batt_states_by_time, timestamp)
                    pv_state = self._find_closest_state(pv_states_by_time, timestamp) if pv_power_ent else None
                    
                    if batt_state:
                        batt_power = _safe_float(batt_state.state)
                        pv_power = _safe_float(pv_state.state) if pv_state else 0.0
                        
                        # Apply sign inversion if configured
                        invert_sign = self._get_cfg(CONF_BATT_POWER_INVERT_SIGN, False)
                        if invert_sign and batt_power is not None:
                            batt_power = -batt_power
                        
                        if batt_power and batt_power > 0:  # Battery charging
                            # Check if it's from grid (PV doesn't cover it)
                            pv_surplus = max(0.0, (pv_power or 0.0) - w)
                            grid_charge = max(0.0, batt_power - pv_surplus)
                            if grid_charge > 100:  # Charging from grid if > 100W
                                should_exclude = True
                
                if not should_exclude:
                    kwh_per_h = w / 1000.0
                    daypart_samples[daypart].append(kwh_per_h)
            
            # Calculate averages for each daypart
            results = {
                "night": None,
                "day": None,
                "evening": None,
                "overall": None,
            }
            
            all_samples = []
            for daypart in ["night", "day", "evening"]:
                samples = daypart_samples[daypart]
                if samples:
                    avg = sum(samples) / len(samples)
                    results[daypart] = max(0.05, min(5.0, avg))  # Clip to reasonable range
                    all_samples.extend(samples)
                    _LOGGER.debug(
                        "48h baseline %s: %.3f kWh/h from %d samples",
                        daypart, results[daypart], len(samples)
                    )
            
            # Calculate overall average
            if all_samples:
                overall_avg = sum(all_samples) / len(all_samples)
                results["overall"] = max(0.05, min(5.0, overall_avg))
                _LOGGER.debug(
                    "48h baseline overall: %.3f kWh/h from %d total samples",
                    results["overall"], len(all_samples)
                )
            
            return results
            
        except Exception as e:
            _LOGGER.warning("Failed to calculate 48h baseline: %s", e, exc_info=True)
            return None
    
    def _find_closest_state(self, states_by_time: Dict, target_time: datetime, max_delta_seconds: int = 300) -> Optional[Any]:
        """Find the state closest to target_time within max_delta_seconds."""
        if not states_by_time:
            return None
        
        closest_state = None
        closest_delta = float('inf')
        
        for state_time, state in states_by_time.items():
            delta = abs((state_time - target_time).total_seconds())
            if delta < closest_delta and delta <= max_delta_seconds:
                closest_delta = delta
                closest_state = state
        
        return closest_state

    async def _update_baseline_and_runtime(self):
        """
        Beräkna husets baseline (kWh/h) och Battery Runtime Estimate.
        - counter_kwh: derivata på kWh-räknare (t.ex. Consumption today)
        - power_w: 48h historical baseline with time-of-day weighting (no EMA fallback)
        - manual_dayparts: ej implementerad än (placeholder)
        Exkluderar datapunkter vid EV-laddning och forcerad batteriladdning från grid.
        """
        method = self._get_cfg(CONF_RUNTIME_SOURCE, "counter_kwh")
        lookback_hours = int(self._get_cfg(CONF_RUNTIME_LOOKBACK_HOURS, 48))
        now = dt_util.now()

        visible_kwh_h: Optional[float] = None
        source_val = None

        # power_w method: Use ONLY 48h historical calculation (no EMA fallback)
        if method == "power_w":
            baseline_48h = await self._calculate_48h_baseline()
            if baseline_48h:
                # Use 48h historical baseline
                visible_kwh_h = baseline_48h.get("overall")
                _LOGGER.debug(
                    "48h baseline calculation succeeded: overall=%s night=%s day=%s evening=%s",
                    baseline_48h.get("overall"),
                    baseline_48h.get("night"),
                    baseline_48h.get("day"),
                    baseline_48h.get("evening"),
                )
                
                # Store daypart baselines
                night_w = baseline_48h.get("night")
                day_w = baseline_48h.get("day")
                evening_w = baseline_48h.get("evening")
                
                self.data["baseline_night_w"] = round(night_w * 1000.0, 1) if night_w is not None else None
                self.data["baseline_day_w"] = round(day_w * 1000.0, 1) if day_w is not None else None
                self.data["baseline_evening_w"] = round(evening_w * 1000.0, 1) if evening_w is not None else None
                
                # Get current sensor value for display
                ent = self._get_cfg(CONF_RUNTIME_POWER_ENTITY, "") or self._get_cfg(CONF_LOAD_POWER_ENTITY, "") or self._get_cfg(CONF_HOUSE_CONS_SENSOR, "")
                st = self.hass.states.get(ent) if ent else None
                source_val = _as_watts(st.state, st.attributes.get("unit_of_measurement")) if st else None
                
                baseline_w = None if visible_kwh_h is None else round(visible_kwh_h * 1000.0, 1)
                self.data["house_baseline_w"] = baseline_w
                self.data["baseline_method"] = f"{method}_48h"
                self.data["baseline_source_value"] = source_val
                self.data["baseline_kwh_per_h"] = round(visible_kwh_h, 4) if visible_kwh_h else None
                self.data["baseline_exclusion_reason"] = ""  # Already excluded in 48h calc
                
                _LOGGER.debug(
                    "Baseline: method=%s_48h overall=%.3f kWh/h night=%.3f day=%.3f evening=%.3f",
                    method,
                    visible_kwh_h or 0,
                    night_w or 0,
                    day_w or 0,
                    evening_w or 0,
                )
            else:
                # 48h calculation failed - set all to None with diagnostic message
                _LOGGER.warning(
                    "48h baseline calculation failed. Sensors will show 'unknown'. "
                    "Check: (1) runtime_power_entity is configured, "
                    "(2) sensor has historical data in Recorder, "
                    "(3) Recorder retention period is sufficient."
                )
                self.data["house_baseline_w"] = None
                self.data["baseline_method"] = f"{method}_48h"
                self.data["baseline_source_value"] = None
                self.data["baseline_kwh_per_h"] = None
                self.data["baseline_exclusion_reason"] = ""
                self.data["baseline_night_w"] = None
                self.data["baseline_day_w"] = None
                self.data["baseline_evening_w"] = None
                visible_kwh_h = None
        
        # counter_kwh method: Use counter-based calculation
        elif method == "counter_kwh":
            ent = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
            st = self.hass.states.get(ent) if ent else None
            kwh = _safe_float(st.state) if st else None
            source_val = kwh
            
            sample_kwh_per_h: Optional[float] = None
            if kwh is not None:
                prev = self._baseline_prev_counter
                self._baseline_prev_counter = (kwh, now)
                if prev:
                    prev_kwh, prev_ts = prev
                    dt_h = max(0.0, (now - prev_ts).total_seconds() / 3600.0)
                    delta = kwh - prev_kwh
                    # hantera dygnsreset/negativa hopp
                    if dt_h > 0 and delta >= -0.0005:
                        # Om negativ litet hopp → nolla till 0
                        delta = max(0.0, delta)
                        sample_kwh_per_h = delta / dt_h
            
            # Fönster/klippning
            if sample_kwh_per_h is not None:
                sample_kwh_per_h = max(0.05, min(5.0, sample_kwh_per_h))
                visible_kwh_h = sample_kwh_per_h
            else:
                visible_kwh_h = None
            
            baseline_w = None if visible_kwh_h is None else round(visible_kwh_h * 1000.0, 1)
            self.data["house_baseline_w"] = baseline_w
            self.data["baseline_method"] = method
            self.data["baseline_source_value"] = source_val
            self.data["baseline_kwh_per_h"] = round(visible_kwh_h, 4) if visible_kwh_h else None
            self.data["baseline_exclusion_reason"] = ""
            
            # counter_kwh method doesn't support dayparts
            self.data["baseline_night_w"] = None
            self.data["baseline_day_w"] = None
            self.data["baseline_evening_w"] = None
            
            _LOGGER.debug(
                "Baseline: method=%s sample=%.4f kWh/h",
                method,
                visible_kwh_h or 0,
            )
        
        else:
            # Unknown method - set all to None
            _LOGGER.warning("Unknown baseline method: %s", method)
            self.data["house_baseline_w"] = None
            self.data["baseline_method"] = method
            self.data["baseline_source_value"] = None
            self.data["baseline_kwh_per_h"] = None
            self.data["baseline_exclusion_reason"] = ""
            self.data["baseline_night_w"] = None
            self.data["baseline_day_w"] = None
            self.data["baseline_evening_w"] = None
            visible_kwh_h = None

        # Battery runtime (using final visible_kwh_h regardless of method)
        batt_cap = float(self._get_cfg(CONF_BATT_CAP_KWH, 0.0))
        soc_ent = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
        soc_state = self._read_float(soc_ent)
        soc_floor = float(self._get_cfg(CONF_RUNTIME_SOC_FLOOR, 10))
        soc_ceil = float(self._get_cfg(CONF_RUNTIME_SOC_CEILING, 95))

        if batt_cap and soc_state is not None and visible_kwh_h and visible_kwh_h > 0:
            span = max(1.0, soc_ceil - soc_floor)
            usable = max(0.0, min(1.0, (soc_state - soc_floor) / span))
            energy_kwh = usable * batt_cap
            raw_runtime_h = energy_kwh / visible_kwh_h if visible_kwh_h > 0 else None
            
            # Round to appropriate precision: 15-min intervals for >= 2h, 5-min for < 2h
            if raw_runtime_h is not None:
                if raw_runtime_h >= 2.0:
                    # Round to nearest 15 minutes (0.25 hours)
                    runtime_h = round(raw_runtime_h * 4) / 4
                else:
                    # Round to nearest 5 minutes (1/12 hours)
                    runtime_h = round(raw_runtime_h * 12) / 12
            else:
                runtime_h = None
        else:
            runtime_h = None

        self.data["battery_runtime_h"] = runtime_h
        _LOGGER.debug("Battery runtime: %s h", runtime_h)

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
        
        # Get forecast source and manual settings (new in this PR)
        forecast_source = self._get_cfg("forecast_source", "forecast_solar")
        weather_entity = self._get_cfg("weather_entity", "")
        
        provider = ForecastSolarProvider(
            self.hass,
            lat=lat,
            lon=lon,
            planes_json=planes,
            apikey=apikey,
            horizon_csv=horizon,
            weather_entity=weather_entity,
            forecast_source=forecast_source,
            manual_step_minutes=self._get_cfg("manual_step_minutes", 15),
            manual_diffuse_svf=self._get_cfg("manual_diffuse_sky_view_factor"),
            manual_temp_coeff=self._get_cfg("manual_temp_coeff_pct_per_c", -0.38),
            manual_inverter_ac_cap=self._get_cfg("manual_inverter_ac_kw_cap"),
            manual_calibration_enabled=self._get_cfg("manual_calibration_enabled", False),
        )
        pts, _ = await provider.async_fetch_watts()
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
                pv_now = _as_watts(st.state, str(st.attributes.get("unit_of_measurement", "")).lower())
                pv_now = None if pv_now is None else round(pv_now, 1)
        self.data["pv_now_w"] = pv_now

        pv_today = None
        if pv_energy_entity:
            st = self.hass.states.get(pv_energy_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                try:
                    val = _safe_float(st.state)
                    unit = str(st.attributes.get("unit_of_measurement", "")).lower()
                    if val is not None:
                        if "mwh" in unit:
                            pv_today = round(val * 1000.0, 3)
                        elif "wh" in unit and "kwh" not in unit:
                            pv_today = round(val / 1000.0, 3)
                        else:
                            pv_today = round(val, 3)  # antar kWh
                except Exception:
                    pv_today = None
        self.data["pv_today_kwh"] = pv_today

    # ---------- Battery charge/discharge tracking ----------
    async def _update_battery_charge_tracking(self):
        """
        Track battery charge/discharge events using daily energy counters.
        Calls bec.on_charge() when battery charges and bec.on_discharge() when it discharges.
        """
        store = self._get_store()
        bec = store.get("bec")
        if not bec:
            return
        
        # Get current date
        now = dt_util.now()
        current_date = now.date()
        
        # Check if we need to reset tracking (new day)
        if self._batt_last_reset_date != current_date:
            self._batt_prev_charged_today = None
            self._batt_prev_discharged_today = None
            self._batt_last_reset_date = current_date
            _LOGGER.debug("Battery tracking reset for new day: %s", current_date)
        
        # Get configured entities
        charged_entity = self._get_cfg(CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY, "")
        discharged_entity = self._get_cfg(CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY, "")
        
        if not charged_entity and not discharged_entity:
            # No tracking entities configured
            return
        
        # Get current price for charging cost calculation
        current_price = self.data.get("current_enriched", 0.0) or 0.0
        
        # Get PV power to determine if charging from solar or grid
        pv_power_w = self.data.get("pv_now_w", 0.0) or 0.0
        load_power_w = self._read_watts(self._get_cfg(CONF_LOAD_POWER_ENTITY, "")) or 0.0
        batt_power_w = self._read_battery_power_normalized()
        
        # Track charging
        if charged_entity:
            st = self.hass.states.get(charged_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                charged_today = _safe_float(st.state)
                if charged_today is not None:
                    if self._batt_prev_charged_today is not None:
                        delta_charged = charged_today - self._batt_prev_charged_today
                        if delta_charged > 0.001:  # At least 1 Wh change
                            # Determine if charging from grid or solar
                            # If PV surplus exceeds charging power, it's solar, otherwise grid
                            pv_surplus_w = max(0.0, pv_power_w - load_power_w)
                            # Estimate charge power (if batt_power_w available)
                            if batt_power_w is not None:
                                # Standard convention: positive means charging
                                charge_power_w = max(0.0, batt_power_w)
                            else:
                                # Estimate from delta over 5 minutes (300s update interval)
                                charge_power_w = (delta_charged * 1000.0) / (300.0 / 3600.0)  # Convert to W
                            
                            # Determine source and cost
                            if pv_surplus_w >= charge_power_w * 0.8:  # 80% threshold for solar
                                source = "solar"
                                cost = 0.0  # Solar is free
                            else:
                                source = "grid"
                                cost = current_price
                            
                            _LOGGER.info(
                                "Battery charged: %.3f kWh from %s @ %.3f SEK/kWh (PV: %.1f W, Load: %.1f W, Charge: %.1f W)",
                                delta_charged, source, cost, pv_power_w, load_power_w, charge_power_w
                            )
                            bec.on_charge(delta_charged, cost, source)
                            await bec.async_save()
                    
                    self._batt_prev_charged_today = charged_today
        
        # Track discharging
        if discharged_entity:
            st = self.hass.states.get(discharged_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                discharged_today = _safe_float(st.state)
                if discharged_today is not None:
                    if self._batt_prev_discharged_today is not None:
                        delta_discharged = discharged_today - self._batt_prev_discharged_today
                        if delta_discharged > 0.001:  # At least 1 Wh change
                            _LOGGER.info("Battery discharged: %.3f kWh", delta_discharged)
                            bec.on_discharge(delta_discharged)
                            await bec.async_save()
                    
                    self._batt_prev_discharged_today = discharged_today

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
