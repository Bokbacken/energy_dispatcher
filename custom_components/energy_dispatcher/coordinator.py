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
    CONF_PV_TOTAL_ENERGY_ENTITY,
    # EV/EVSE param
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    CONF_EVSE_START_SWITCH,
    CONF_EVSE_CURRENT_NUMBER,
    CONF_EVSE_TOTAL_ENERGY_SENSOR,
    CONF_EVSE_POWER_SENSOR,
    # Baseline
    CONF_RUNTIME_COUNTER_ENTITY,
    CONF_RUNTIME_EXCLUDE_EV,
    CONF_RUNTIME_EXCLUDE_BATT_GRID,
    CONF_RUNTIME_SOC_FLOOR,
    CONF_RUNTIME_SOC_CEILING,
    CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY,
    CONF_GRID_IMPORT_TODAY_ENTITY,
    CONF_RUNTIME_LOOKBACK_HOURS,
    CONF_RUNTIME_USE_DAYPARTS,
    CONF_LOAD_POWER_ENTITY,
    CONF_BATT_POWER_ENTITY,
    CONF_BATT_POWER_INVERT_SIGN,
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


def _fetch_history_for_multiple_entities(hass, start_time, end_time, entity_ids):
    """
    Wrapper function to fetch history for multiple entities.
    
    This is needed because in newer Home Assistant versions, 
    history.state_changes_during_period expects entity_id (singular) 
    as a string, not a list. This wrapper fetches each entity 
    individually and combines the results.
    
    Args:
        hass: Home Assistant instance
        start_time: Start datetime for history query
        end_time: End datetime for history query
        entity_ids: List of entity IDs to fetch history for
    
    Returns:
        Dict mapping entity_id to list of state objects
    """
    from homeassistant.components.recorder import history
    
    combined = {}
    for entity_id in entity_ids:
        # Fetch history for single entity
        result = history.state_changes_during_period(
            hass, start_time, end_time, entity_id
        )
        # Merge results
        if result:
            combined.update(result)
    
    return combined


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
        load_pw = self._read_watts(self._get_cfg(CONF_LOAD_POWER_ENTITY, ""))  # W
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
        Calculate baseline from last 48 hours using energy counter deltas.
        Returns dict with keys: overall, night, day, evening (all in kWh/h).
        Also includes 'failure_reason' key if calculation fails.
        Uses energy counters (kWh) to calculate consumption, excluding EV charging 
        and battery grid charging based on their respective energy counters.
        """
        lookback_hours = int(self._get_cfg(CONF_RUNTIME_LOOKBACK_HOURS, 48))
        use_dayparts = bool(self._get_cfg(CONF_RUNTIME_USE_DAYPARTS, True))
        
        # Get the required energy counter entities
        house_energy_ent = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
        if not house_energy_ent:
            _LOGGER.debug(
                "48h baseline: No house energy counter configured (runtime_counter_entity)"
            )
            return {
                "overall": None,
                "night": None,
                "day": None,
                "evening": None,
                "failure_reason": "No house energy counter configured (runtime_counter_entity)"
            }
        
        # Get optional energy counter entities for exclusions
        ev_energy_ent = self._get_cfg(CONF_EVSE_TOTAL_ENERGY_SENSOR, "")
        batt_energy_ent = self._get_cfg(CONF_BATT_TOTAL_CHARGED_ENERGY_ENTITY, "")
        pv_energy_ent = self._get_cfg(CONF_PV_TOTAL_ENERGY_ENTITY, "")
        
        exclude_ev = bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_EV, True))
        exclude_batt_grid = bool(self._get_cfg(CONF_RUNTIME_EXCLUDE_BATT_GRID, True))
            
        try:
            from homeassistant.components.recorder import history
            
            end = dt_util.now()
            start = end - timedelta(hours=lookback_hours)
            
            # Build list of entities to fetch
            entities_to_fetch = [house_energy_ent]
            if exclude_ev and ev_energy_ent:
                entities_to_fetch.append(ev_energy_ent)
            if exclude_batt_grid and batt_energy_ent:
                entities_to_fetch.append(batt_energy_ent)
            if exclude_batt_grid and pv_energy_ent:
                entities_to_fetch.append(pv_energy_ent)
            
            # Fetch all needed entities using wrapper function
            # (newer HA versions require entity_id as string, not list)
            # Use recorder's executor for database operations to avoid warnings
            from homeassistant.components.recorder import get_instance
            
            try:
                # Try to use the recorder's executor (preferred for database operations)
                recorder = get_instance(self.hass)
                all_hist = await recorder.async_add_executor_job(
                    _fetch_history_for_multiple_entities, self.hass, start, end, entities_to_fetch
                )
            except (KeyError, RuntimeError):
                # Fall back to hass executor if recorder not available (e.g., in tests)
                all_hist = await self.hass.async_add_executor_job(
                    _fetch_history_for_multiple_entities, self.hass, start, end, entities_to_fetch
                )
            
            house_states = all_hist.get(house_energy_ent, [])
            if not house_states or len(house_states) < 2:
                _LOGGER.warning(
                    "48h baseline: No historical data available for %s (need at least 2 data points, got %d). "
                    "Check: (1) Sensor exists and reports values, (2) Recorder is enabled, "
                    "(3) Recorder retention period >= %d hours",
                    house_energy_ent, len(house_states), lookback_hours
                )
                return {
                    "overall": None,
                    "night": None,
                    "day": None,
                    "evening": None,
                    "failure_reason": f"Insufficient historical data: {len(house_states)} data points (need 2+)"
                }
            
            # Get energy counter states for exclusions
            ev_states = all_hist.get(ev_energy_ent, []) if ev_energy_ent and exclude_ev else []
            batt_states = all_hist.get(batt_energy_ent, []) if batt_energy_ent and exclude_batt_grid else []
            pv_states = all_hist.get(pv_energy_ent, []) if pv_energy_ent and exclude_batt_grid else []
            
            # Get start and end energy values for house load
            house_start = _safe_float(house_states[0].state)
            house_end = _safe_float(house_states[-1].state)
            
            if house_start is None or house_end is None:
                _LOGGER.warning(
                    "48h baseline: Invalid house energy counter values for %s (start=%s, end=%s). "
                    "Check: Sensor reports numeric values (not 'unknown', 'unavailable')",
                    house_energy_ent, house_start, house_end
                )
                return {
                    "overall": None,
                    "night": None,
                    "day": None,
                    "evening": None,
                    "failure_reason": f"Invalid sensor values: start={house_start}, end={house_end}"
                }
            
            # Calculate total house energy consumed (handle counter resets)
            house_delta = house_end - house_start
            if house_delta < 0:
                # Counter reset detected, use only end value as approximation
                house_delta = house_end
            
            # Get energy deltas for exclusions
            ev_delta = 0.0
            if ev_states and len(ev_states) >= 2:
                ev_start = _safe_float(ev_states[0].state)
                ev_end = _safe_float(ev_states[-1].state)
                if ev_start is not None and ev_end is not None:
                    ev_delta = ev_end - ev_start
                    if ev_delta < 0:
                        ev_delta = ev_end  # Handle counter reset
            
            batt_delta = 0.0
            pv_delta = 0.0
            if batt_states and len(batt_states) >= 2:
                batt_start = _safe_float(batt_states[0].state)
                batt_end = _safe_float(batt_states[-1].state)
                if batt_start is not None and batt_end is not None:
                    batt_delta = batt_end - batt_start
                    if batt_delta < 0:
                        batt_delta = batt_end
            
            if pv_states and len(pv_states) >= 2:
                pv_start = _safe_float(pv_states[0].state)
                pv_end = _safe_float(pv_states[-1].state)
                if pv_start is not None and pv_end is not None:
                    pv_delta = pv_end - pv_start
                    if pv_delta < 0:
                        pv_delta = pv_end
            
            # Calculate net house consumption excluding EV and battery grid charging
            net_house_kwh = house_delta
            
            if exclude_ev and ev_delta > 0:
                net_house_kwh -= ev_delta
                _LOGGER.debug("Excluding EV energy: %.3f kWh", ev_delta)
            
            if exclude_batt_grid and batt_delta > 0:
                # Estimate battery grid charging (battery charged - PV generation)
                batt_grid_kwh = max(0.0, batt_delta - pv_delta)
                net_house_kwh -= batt_grid_kwh
                _LOGGER.debug("Excluding battery grid charging: %.3f kWh (batt: %.3f, pv: %.3f)", 
                             batt_grid_kwh, batt_delta, pv_delta)
            
            # Ensure we don't have negative consumption
            net_house_kwh = max(0.0, net_house_kwh)
            
            # Calculate average consumption rate (kWh/h)
            time_delta_h = lookback_hours
            avg_kwh_per_h = net_house_kwh / time_delta_h
            
            # Clip to reasonable range
            avg_kwh_per_h = max(0.05, min(5.0, avg_kwh_per_h))
            
            results = {
                "overall": avg_kwh_per_h,
                "night": None,
                "day": None,
                "evening": None,
            }
            
            # If dayparts are enabled, distribute evenly for now
            # (more sophisticated time-of-day distribution would require hourly data)
            if use_dayparts:
                results["night"] = avg_kwh_per_h
                results["day"] = avg_kwh_per_h
                results["evening"] = avg_kwh_per_h
            
            _LOGGER.debug(
                "48h baseline calculated: %.3f kWh/h (house: %.3f kWh, ev: %.3f kWh, batt_grid: ~%.3f kWh over %d hours)",
                avg_kwh_per_h, house_delta, ev_delta, 
                max(0.0, batt_delta - pv_delta) if exclude_batt_grid else 0.0,
                lookback_hours
            )
            
            return results
            
        except Exception as e:
            _LOGGER.warning("Failed to calculate 48h baseline: %s", e, exc_info=True)
            return {
                "overall": None,
                "night": None,
                "day": None,
                "evening": None,
                "failure_reason": f"Exception during calculation: {str(e)}"
            }

    async def _update_baseline_and_runtime(self):
        """
        Calculate house baseline (kWh/h) and Battery Runtime Estimate.
        Uses energy counters (kWh) with 48h lookback to calculate delta-based consumption.
        Excludes EV charging and battery grid charging based on their energy counters.
        """
        lookback_hours = int(self._get_cfg(CONF_RUNTIME_LOOKBACK_HOURS, 48))
        now = dt_util.now()

        visible_kwh_h: Optional[float] = None
        source_val = None

        # Calculate baseline using 48h energy counter deltas
        baseline_48h = await self._calculate_48h_baseline()
        if baseline_48h and baseline_48h.get("overall") is not None:
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
            
            # Get current house energy counter value for display
            house_energy_ent = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
            st = self.hass.states.get(house_energy_ent) if house_energy_ent else None
            source_val = _safe_float(st.state) if st else None
            
            baseline_w = None if visible_kwh_h is None else round(visible_kwh_h * 1000.0, 1)
            self.data["house_baseline_w"] = baseline_w
            self.data["baseline_method"] = "energy_counter_48h"
            self.data["baseline_source_value"] = source_val
            self.data["baseline_kwh_per_h"] = round(visible_kwh_h, 4) if visible_kwh_h else None
            self.data["baseline_exclusion_reason"] = ""  # Already excluded in 48h calc
            
            _LOGGER.debug(
                "Baseline: method=energy_counter_48h overall=%.3f kWh/h night=%.3f day=%.3f evening=%.3f",
                visible_kwh_h or 0,
                night_w or 0,
                day_w or 0,
                evening_w or 0,
            )
        else:
            # 48h calculation failed - set all to None with diagnostic message
            failure_reason = baseline_48h.get("failure_reason", "Unknown error") if baseline_48h else "No result returned"
            _LOGGER.warning(
                "48h baseline calculation failed: %s. Sensors will show 'unknown'. "
                "Check Home Assistant logs for detailed diagnostics.",
                failure_reason
            )
            
            # Get current house energy counter value for diagnostic display
            house_energy_ent = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
            st = self.hass.states.get(house_energy_ent) if house_energy_ent else None
            source_val = _safe_float(st.state) if st else None
            
            self.data["house_baseline_w"] = None
            self.data["baseline_method"] = "energy_counter_48h"
            self.data["baseline_source_value"] = source_val
            self.data["baseline_kwh_per_h"] = None
            self.data["baseline_exclusion_reason"] = failure_reason
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
