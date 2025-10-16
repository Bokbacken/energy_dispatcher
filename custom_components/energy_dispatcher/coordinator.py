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
    CONF_EXPORT_GRID_UTILITY,
    CONF_EXPORT_ENERGY_SURCHARGE,
    CONF_EXPORT_TAX_RETURN,
    CONF_BATT_CAP_KWH,
    CONF_BATT_SOC_ENTITY,
    CONF_BATT_MAX_CHARGE_W,
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
    CONF_LOAD_POWER_ENTITY,
    CONF_BATT_POWER_ENTITY,
    CONF_BATT_POWER_INVERT_SIGN,
    # Cost strategy
    CONF_USE_DYNAMIC_COST_THRESHOLDS,
    CONF_COST_CHEAP_THRESHOLD,
    CONF_COST_HIGH_THRESHOLD,
    # Export profitability
    CONF_EXPORT_MODE,
    CONF_MIN_EXPORT_PRICE_SEK_PER_KWH,
    CONF_BATTERY_DEGRADATION_COST_PER_CYCLE_SEK,
    CONF_MIN_ARBITRAGE_PROFIT_SEK_PER_KWH,
    # Weather optimization
    CONF_WEATHER_ENTITY,
    CONF_ENABLE_WEATHER_OPTIMIZATION,
)
from .models import PricePoint, ChargingMode
from .price_provider import PriceProvider, PriceFees
from .forecast_provider import ForecastSolarProvider
from .cost_strategy import CostStrategy
from .planner import simple_plan
from .export_analyzer import ExportAnalyzer
from .weather_optimizer import WeatherOptimizer

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


def _interpolate_energy_value(
    timestamp: datetime,
    prev_time: datetime,
    prev_value: float,
    next_time: datetime,
    next_value: float,
) -> Optional[float]:
    """
    Linearly interpolate energy counter value at a given timestamp.
    
    Args:
        timestamp: The timestamp to interpolate for
        prev_time: Timestamp of previous known value
        prev_value: Previous known energy value (kWh)
        next_time: Timestamp of next known value
        next_value: Next known energy value (kWh)
    
    Returns:
        Interpolated energy value (kWh), or None if interpolation not possible
    """
    if prev_time >= next_time or timestamp < prev_time or timestamp > next_time:
        return None
    
    # Handle counter reset (negative delta)
    if next_value < prev_value:
        # Can't reliably interpolate across a counter reset
        return None
    
    # Linear interpolation
    time_fraction = (timestamp - prev_time).total_seconds() / (next_time - prev_time).total_seconds()
    interpolated = prev_value + time_fraction * (next_value - prev_value)
    return interpolated


def _is_data_stale(last_update: Optional[datetime], max_age_minutes: int = 15) -> bool:
    """
    Check if data is too old to be considered valid.
    
    Args:
        last_update: Timestamp of last data update
        max_age_minutes: Maximum age in minutes before data is considered stale
    
    Returns:
        True if data is stale or last_update is None, False otherwise
    """
    if last_update is None:
        return True
    
    now = dt_util.now()
    age = (now - last_update).total_seconds() / 60.0
    return age > max_age_minutes


def _fill_missing_hourly_data(
    time_index: Dict[datetime, float],
    max_gap_hours: float = 8.0
) -> Dict[datetime, float]:
    """
    Fill missing hourly data points using linear interpolation.
    
    For gaps up to max_gap_hours, interpolates values between known points.
    For gaps larger than max_gap_hours, leaves them empty (no interpolation).
    
    Args:
        time_index: Dictionary mapping hour timestamps to energy values (kWh)
        max_gap_hours: Maximum gap size to interpolate (default 8 hours)
    
    Returns:
        New dictionary with interpolated values added
    """
    if not time_index or len(time_index) < 2:
        return time_index.copy()
    
    filled = time_index.copy()
    sorted_times = sorted(time_index.keys())
    
    # Iterate through consecutive pairs
    for i in range(len(sorted_times) - 1):
        start_time = sorted_times[i]
        end_time = sorted_times[i + 1]
        start_val = time_index[start_time]
        end_val = time_index[end_time]
        
        # Calculate gap in hours
        gap_hours = (end_time - start_time).total_seconds() / 3600.0
        
        # Only interpolate if gap is within acceptable limits
        if gap_hours <= max_gap_hours and gap_hours > 1.0:
            # Generate hourly timestamps between start and end
            current = start_time + timedelta(hours=1)
            while current < end_time:
                if current not in filled:
                    # Interpolate value at this timestamp
                    interpolated = _interpolate_energy_value(
                        current, start_time, start_val, end_time, end_val
                    )
                    if interpolated is not None:
                        filled[current] = interpolated
                current += timedelta(hours=1)
    
    return filled


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
            "current_export": None,
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
            # Cost strategy
            "cost_level": None,  # "cheap", "medium", or "high"
            "battery_reserve_recommendation": None,  # Recommended SOC% to maintain
            "high_cost_windows": [],  # List of (start, end) tuples for high-cost periods
            "cost_summary": {},  # Summary of cost classification
            # Optimization plan
            "optimization_plan": [],  # List of PlanAction objects with hourly recommendations
            "optimization_plan_status": None,  # Diagnostic info: why plan is empty or status
            # Export opportunity
            "export_opportunity": {},  # Export profitability analysis
        }

        # Cost strategy instance
        self._cost_strategy = CostStrategy()
        
        # Weather optimizer instance
        self._weather_optimizer = WeatherOptimizer(hass)
        
        # Export analyzer instance
        self.export_analyzer: Optional[ExportAnalyzer] = None
        
        # Historik för baseline (counter_kwh)
        self._baseline_prev_counter: Optional[Tuple[float, Any]] = None  # (kWh, ts)
        self._sf_history: List[Tuple[Any, float, float]] = []  # (ts, forecast_w, actual_w)
        
        # Battery charge/discharge tracking
        self._batt_prev_charged_today: Optional[float] = None  # kWh charged today (previous value)
        self._batt_prev_discharged_today: Optional[float] = None  # kWh discharged today (previous value)
        self._batt_last_reset_date: Optional[Any] = None  # Track daily reset
        self._batt_last_update_time: Optional[datetime] = None  # Track last successful BEC update
        
        # Energy delta tracking for accurate solar vs grid classification
        self._prev_pv_energy_today: Optional[float] = None  # kWh PV today (previous value)
        self._prev_house_energy: Optional[float] = None  # kWh house total (previous value)
        self._prev_grid_import_today: Optional[float] = None  # kWh grid import today (previous value)
        
        # Battery override tracking
        self._battery_override: Optional[Dict[str, Any]] = None  # {"mode": str, "power_w": int, "expires_at": datetime}

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

    def set_battery_override(
        self,
        mode: str,
        duration_minutes: int,
        power_w: Optional[int] = None
    ) -> None:
        """Set battery override mode with expiration."""
        expires_at = dt_util.now() + timedelta(minutes=duration_minutes)
        self._battery_override = {
            "mode": mode,
            "power_w": power_w,
            "expires_at": expires_at,
        }
        _LOGGER.info(
            "Battery override set: mode=%s, power_w=%s, expires_at=%s",
            mode, power_w, expires_at
        )

    def get_battery_override(self) -> Optional[Dict[str, Any]]:
        """Get current battery override if still valid."""
        if self._battery_override is None:
            return None
        
        # Check if expired
        if dt_util.now() >= self._battery_override["expires_at"]:
            _LOGGER.info("Battery override expired, clearing")
            self._battery_override = None
            return None
        
        return self._battery_override

    def clear_battery_override(self) -> None:
        """Clear battery override."""
        if self._battery_override is not None:
            _LOGGER.info("Battery override cleared")
        self._battery_override = None

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
            await self._update_optimization_plan()
            await self._update_appliance_recommendations()
            await self._update_export_analysis()
            await self._update_load_shift_recommendations()
            await self._update_peak_shaving_status()
            
            # Update battery override status
            override = self.get_battery_override()
            if override:
                self.data["battery_override"] = {
                    "active": True,
                    "mode": override["mode"],
                    "power_w": override["power_w"],
                    "expires_at": override["expires_at"].isoformat(),
                }
            else:
                self.data["battery_override"] = {"active": False}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Uppdatering misslyckades")
        return self.data

    def _calculate_export_price(self, spot_price: float, current_year: int) -> float:
        """Calculate export price based on year and configured contract parameters.
        
        Export price formula:
        - Grid utility (nätnytta): Configured value (default 0.067 SEK/kWh)
        - Energy surcharge (påslag): Configured value (default 0.02 SEK/kWh)
        - Tax return (skattereduktion): Configured value (default 0.60 SEK/kWh for 2025)
        
        Note: Tax return typically expires after 2025 in Sweden. User should set to 0 for 2026+.
        
        Args:
            spot_price: Nordpool spot price in SEK/kWh
            current_year: Current year (can be used by user to determine tax return)
            
        Returns:
            Export price in SEK/kWh
        """
        grid_utility = _safe_float(self._get_cfg(CONF_EXPORT_GRID_UTILITY, 0.067), 0.067)
        energy_surcharge = _safe_float(self._get_cfg(CONF_EXPORT_ENERGY_SURCHARGE, 0.02), 0.02)
        tax_return = _safe_float(self._get_cfg(CONF_EXPORT_TAX_RETURN, 0.60), 0.60)
        
        export_price = spot_price + grid_utility + energy_surcharge + tax_return
        return export_price
    
    def _get_current_export_price(self, hourly: List[PricePoint]) -> Optional[float]:
        """Get the current export price from hourly data.
        
        Similar to get_current_enriched, returns the export price for the current hour.
        
        Args:
            hourly: List of PricePoint objects with export prices
            
        Returns:
            Current export price in SEK/kWh, or None if no data available
        """
        if not hourly:
            return None
        now = dt_util.now().replace(minute=0, second=0, microsecond=0)
        # Get the most recent hour <= now, otherwise the first future hour
        past = [p for p in hourly if p.time <= now]
        if past:
            return past[-1].export_sek_per_kwh
        return hourly[0].export_sek_per_kwh

    # ---------- prices ----------
    async def _update_prices(self):
        nordpool_entity = self._get_cfg(CONF_NORDPOOL_ENTITY, "")
        if not nordpool_entity:
            self.data["hourly_prices"] = []
            self.data["current_enriched"] = None
            self.data["current_export"] = None
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
        
        # Calculate export prices for each hour
        now = dt_util.now()
        for price_point in hourly:
            export_price = self._calculate_export_price(
                price_point.spot_sek_per_kwh,
                current_year=price_point.time.year
            )
            price_point.export_sek_per_kwh = export_price
        
        self.data["hourly_prices"] = hourly
        self.data["current_enriched"] = provider.get_current_enriched(hourly)
        
        # Calculate current export price
        self.data["current_export"] = self._get_current_export_price(hourly)

        # P25-tröskel 24h framåt
        now = now.replace(minute=0, second=0, microsecond=0)
        next24 = [p for p in hourly if 0 <= (p.time - now).total_seconds() < 24 * 3600]
        if next24:
            enriched = sorted([p.enriched_sek_per_kwh for p in next24])
            p25_idx = max(0, int(len(enriched) * 0.25) - 1)
            self.data["cheap_threshold"] = round(enriched[p25_idx], 4)
        else:
            self.data["cheap_threshold"] = None
        
        # Update cost strategy analysis
        await self._update_cost_strategy(hourly)

    # ---------- cost strategy ----------
    async def _update_cost_strategy(self, hourly_prices: List[PricePoint]):
        """Update cost strategy analysis based on current price data."""
        if not hourly_prices:
            self.data["cost_level"] = None
            self.data["battery_reserve_recommendation"] = None
            self.data["high_cost_windows"] = []
            self.data["cost_summary"] = {}
            return
        
        # Update cost strategy thresholds from configuration
        use_dynamic = self._get_cfg(CONF_USE_DYNAMIC_COST_THRESHOLDS, True)
        
        if use_dynamic:
            # Use dynamic thresholds based on price distribution (25th/75th percentiles)
            dynamic_thresholds = self._cost_strategy.get_dynamic_thresholds(hourly_prices)
            cheap_threshold = dynamic_thresholds.cheap_max
            high_threshold = dynamic_thresholds.high_min
            _LOGGER.debug(
                "Using dynamic cost thresholds: cheap <= %.3f, high >= %.3f SEK/kWh",
                cheap_threshold, high_threshold
            )
        else:
            # Use static thresholds from configuration
            cheap_threshold = _safe_float(self._get_cfg(CONF_COST_CHEAP_THRESHOLD, 1.5), 1.5)
            high_threshold = _safe_float(self._get_cfg(CONF_COST_HIGH_THRESHOLD, 3.0), 3.0)
            _LOGGER.debug(
                "Using static cost thresholds: cheap <= %.3f, high >= %.3f SEK/kWh",
                cheap_threshold, high_threshold
            )
        
        self._cost_strategy.update_thresholds(cheap_max=cheap_threshold, high_min=high_threshold)
        
        now = dt_util.now()
        
        # Get current price
        current_price = self.data.get("current_enriched")
        if current_price is None:
            self.data["cost_level"] = None
        else:
            # Classify current price
            cost_level = self._cost_strategy.classify_price(current_price)
            self.data["cost_level"] = cost_level.value
        
        # Calculate battery reserve recommendation if we have battery info
        battery_reserve = None
        batt_cap_kwh = _safe_float(self._get_cfg(CONF_BATT_CAP_KWH))
        batt_soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
        current_soc = None
        if batt_soc_entity:
            current_soc = self._read_float(batt_soc_entity)
        
        if batt_cap_kwh and current_soc is not None:
            try:
                # Get solar forecast for reserve calculation
                solar_points = self.data.get("solar_points", [])
                
                # Calculate weather adjustment if weather optimization is enabled
                weather_adjustment = None
                enable_weather_opt = self._get_cfg(CONF_ENABLE_WEATHER_OPTIMIZATION, False)
                weather_entity = self._get_cfg(CONF_WEATHER_ENTITY, "")
                
                if enable_weather_opt and weather_entity and solar_points:
                    try:
                        # Get weather forecast
                        weather_forecast = self._weather_optimizer.extract_weather_forecast_from_entity(
                            weather_entity_id=weather_entity,
                            hours=24
                        )
                        
                        if weather_forecast:
                            # Adjust solar forecast based on weather
                            adjusted_forecast = self._weather_optimizer.adjust_solar_forecast_for_weather(
                                base_solar_forecast=solar_points,
                                weather_forecast=weather_forecast
                            )
                            
                            # Calculate adjustment summary
                            weather_adjustment = self._weather_optimizer.calculate_forecast_adjustment_summary(
                                adjusted_forecast
                            )
                            
                            # Store for diagnostics
                            self.data["weather_adjustment_summary"] = weather_adjustment
                            
                            # Log the adjustment
                            if weather_adjustment.get("reduction_percentage", 0) > 0:
                                _LOGGER.info(
                                    "Weather adjustment: Solar forecast reduced by %.1f%% "
                                    "(%.2f kWh -> %.2f kWh) due to weather conditions",
                                    weather_adjustment["reduction_percentage"],
                                    weather_adjustment["total_base_kwh"],
                                    weather_adjustment["total_adjusted_kwh"]
                                )
                            else:
                                _LOGGER.debug(
                                    "Weather adjustment calculated: %.2f kWh (no reduction)",
                                    weather_adjustment["total_adjusted_kwh"]
                                )
                    except Exception as e:
                        _LOGGER.debug("Failed to calculate weather adjustment: %s", e)
                        weather_adjustment = None
                
                battery_reserve = self._cost_strategy.calculate_battery_reserve(
                    prices=hourly_prices,
                    now=now,
                    battery_capacity_kwh=batt_cap_kwh,
                    current_soc=current_soc,
                    solar_forecast=solar_points,
                    weather_adjustment=weather_adjustment
                )
                
                # Log the reserve calculation with weather context
                if weather_adjustment and weather_adjustment.get("reduction_percentage", 0) > 20:
                    _LOGGER.info(
                        "Battery reserve calculated: %.1f%% SOC (weather-adjusted due to %.1f%% solar reduction)",
                        battery_reserve if battery_reserve else 0,
                        weather_adjustment["reduction_percentage"]
                    )
            except Exception as e:
                _LOGGER.debug("Failed to calculate battery reserve: %s", e)
                battery_reserve = None
        
        self.data["battery_reserve_recommendation"] = battery_reserve
        
        # Predict high-cost windows
        try:
            high_cost_windows = self._cost_strategy.predict_high_cost_windows(
                prices=hourly_prices,
                now=now,
                horizon_hours=24
            )
            self.data["high_cost_windows"] = high_cost_windows
        except Exception as e:
            _LOGGER.debug("Failed to predict high-cost windows: %s", e)
            self.data["high_cost_windows"] = []
        
        # Generate cost summary
        try:
            cost_summary = self._cost_strategy.get_cost_summary(
                prices=hourly_prices,
                now=now,
                horizon_hours=24
            )
            self.data["cost_summary"] = cost_summary
        except Exception as e:
            _LOGGER.debug("Failed to generate cost summary: %s", e)
            self.data["cost_summary"] = {}

    # ---------- appliance optimization ----------
    async def _update_appliance_recommendations(self):
        """Generate appliance scheduling recommendations."""
        from .appliance_optimizer import ApplianceOptimizer
        from .const import (
            CONF_ENABLE_APPLIANCE_OPTIMIZATION,
            CONF_DISHWASHER_POWER_W,
            CONF_WASHING_MACHINE_POWER_W,
            CONF_WATER_HEATER_POWER_W,
        )
        
        # Check if appliance optimization is enabled
        if not bool(self._get_cfg(CONF_ENABLE_APPLIANCE_OPTIMIZATION, False)):
            self.data["appliance_recommendations"] = {}
            return
        
        # Check if we have necessary data
        hourly_prices = self.data.get("hourly_prices", [])
        if not hourly_prices:
            self.data["appliance_recommendations"] = {}
            return
        
        try:
            optimizer = ApplianceOptimizer()
            
            # Get solar forecast if available
            solar_forecast = self.data.get("solar_points", None)
            
            # Get battery state if available
            batt_soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
            battery_soc = self._read_float(batt_soc_entity) if batt_soc_entity else None
            battery_capacity_kwh = _safe_float(self._get_cfg(CONF_BATT_CAP_KWH))
            
            # Optimize for each configured appliance
            recommendations = {}
            
            appliances = {
                "dishwasher": {
                    "power_w": int(self._get_cfg(CONF_DISHWASHER_POWER_W, 1800)),
                    "duration_hours": 2.0,
                },
                "washing_machine": {
                    "power_w": int(self._get_cfg(CONF_WASHING_MACHINE_POWER_W, 2000)),
                    "duration_hours": 1.5,
                },
                "water_heater": {
                    "power_w": int(self._get_cfg(CONF_WATER_HEATER_POWER_W, 3000)),
                    "duration_hours": 3.0,
                },
            }
            
            for appliance_name, config in appliances.items():
                try:
                    recommendation = optimizer.optimize_schedule(
                        appliance_name=appliance_name,
                        power_w=config["power_w"],
                        duration_hours=config["duration_hours"],
                        prices=hourly_prices,
                        solar_forecast=solar_forecast,
                        battery_soc=battery_soc,
                        battery_capacity_kwh=battery_capacity_kwh,
                    )
                    
                    # Add user_impact and inconvenience_score for comfort filtering
                    # Estimate user_impact based on optimal time
                    optimal_time = recommendation.get("optimal_start_time")
                    if optimal_time:
                        hour = optimal_time.hour
                        # High impact during evening hours (18-23), low during night/morning
                        if 18 <= hour <= 23:
                            recommendation["user_impact"] = "high"
                            recommendation["inconvenience_score"] = 3.0
                        elif 7 <= hour <= 17:
                            recommendation["user_impact"] = "medium"
                            recommendation["inconvenience_score"] = 2.0
                        else:
                            recommendation["user_impact"] = "low"
                            recommendation["inconvenience_score"] = 1.0
                    else:
                        recommendation["user_impact"] = "medium"
                        recommendation["inconvenience_score"] = 2.0
                    
                    recommendation["recommended_time"] = optimal_time
                    recommendation["savings_sek"] = recommendation.get("cost_savings_vs_now_sek", 0)
                    recommendation["appliance_name"] = appliance_name
                    
                    recommendations[appliance_name] = recommendation
                except Exception as e:
                    _LOGGER.debug("Failed to optimize %s: %s", appliance_name, e)
            
            # Apply comfort filtering
            from .comfort_manager import ComfortManager
            from .const import (
                CONF_COMFORT_PRIORITY,
                CONF_QUIET_HOURS_START,
                CONF_QUIET_HOURS_END,
                CONF_MIN_BATTERY_PEACE_OF_MIND,
            )
            
            comfort_manager = ComfortManager(
                comfort_priority=self._get_cfg(CONF_COMFORT_PRIORITY, "balanced"),
                quiet_hours_start=self._get_cfg(CONF_QUIET_HOURS_START, "22:00"),
                quiet_hours_end=self._get_cfg(CONF_QUIET_HOURS_END, "07:00"),
                min_battery_peace_of_mind=float(self._get_cfg(CONF_MIN_BATTERY_PEACE_OF_MIND, 20)),
            )
            
            # Convert recommendations dict to list for filtering
            rec_list = list(recommendations.values())
            filtered_recs, filtered_out = comfort_manager.optimize_with_comfort_balance(
                rec_list,
                battery_soc=battery_soc,
            )
            
            # Store both filtered and filtered_out recommendations
            self.data["appliance_recommendations"] = recommendations
            if filtered_out:
                self.data["appliance_recommendations_filtered_by_comfort"] = {
                    rec.get("appliance_name", "unknown"): rec 
                    for rec in filtered_out
                }
            _LOGGER.debug(
                "Generated appliance recommendations for %d appliances",
                len(recommendations)
            )
            
        except Exception as e:
            _LOGGER.warning("Failed to generate appliance recommendations: %s", e)
            self.data["appliance_recommendations"] = {}

    async def _update_export_analysis(self):
        """Analyze export profitability opportunities."""
        # Initialize export analyzer if not already done
        if self.export_analyzer is None:
            export_mode = self._get_cfg(CONF_EXPORT_MODE, "never")
            min_export_price = _safe_float(self._get_cfg(CONF_MIN_EXPORT_PRICE_SEK_PER_KWH, 3.0), 3.0)
            degradation_cost = _safe_float(self._get_cfg(CONF_BATTERY_DEGRADATION_COST_PER_CYCLE_SEK, 0.50), 0.50)
            
            self.export_analyzer = ExportAnalyzer(
                export_mode=export_mode,
                min_export_price_sek_per_kwh=min_export_price,
                battery_degradation_cost_per_cycle_sek=degradation_cost,
            )
            _LOGGER.info("Export analyzer initialized: mode=%s, min_price=%.2f, degradation=%.2f",
                        export_mode, min_export_price, degradation_cost)
        
        # Get export mode from config - if "never", skip analysis
        export_mode = self._get_cfg(CONF_EXPORT_MODE, "never")
        if export_mode == "never":
            self.data["export_opportunity"] = {
                "should_export": False,
                "reason": "Export disabled (mode: never)",
                "export_power_w": 0,
                "estimated_revenue_per_kwh": 0.0,
                "export_price_sek_per_kwh": 0.0,
                "opportunity_cost": 0.0,
                "battery_soc": 0.0,
                "solar_excess_w": 0.0,
                "duration_estimate_h": 0.0,
                "battery_degradation_cost": 0.0,
                "net_revenue": 0.0,
            }
            return
        
        # Get current price data
        current_price = self.data.get("current_enriched")
        if not current_price:
            self.data["export_opportunity"] = {
                "should_export": False,
                "reason": "No price data available",
                "export_power_w": 0,
                "estimated_revenue_per_kwh": 0.0,
                "export_price_sek_per_kwh": 0.0,
                "opportunity_cost": 0.0,
                "battery_soc": 0.0,
                "solar_excess_w": 0.0,
                "duration_estimate_h": 0.0,
                "battery_degradation_cost": 0.0,
                "net_revenue": 0.0,
            }
            return
        
        # Get battery state
        batt_soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
        battery_soc = self._read_float(batt_soc_entity) if batt_soc_entity else 0.0
        if battery_soc is None:
            battery_soc = 0.0
        
        battery_capacity_kwh = _safe_float(self._get_cfg(CONF_BATT_CAP_KWH), 15.0)
        
        # Get solar excess (if battery full and solar producing)
        pv_now_w = self.data.get("pv_now_w", 0.0) or 0.0
        house_baseline_w = self.data.get("house_baseline_w", 0.0) or 0.0
        
        # Estimate solar excess (simplified - actual excess would need battery power flow)
        solar_excess_w = max(0.0, pv_now_w - house_baseline_w)
        
        # Count upcoming high-cost hours (next 6 hours)
        high_cost_windows = self.data.get("high_cost_windows", [])
        now = dt_util.now()
        upcoming_high_cost_hours = 0
        for start, end in high_cost_windows:
            # Check if window is in the next 6 hours
            if start <= now + timedelta(hours=6):
                duration_hours = (end - start).total_seconds() / 3600
                upcoming_high_cost_hours += int(duration_hours)
        
        # Use current price as both spot and purchase price
        # In a real system, export price might be different (usually lower)
        # For now, assume export price = spot price (conservative)
        spot_price = current_price
        purchase_price = current_price
        export_price = spot_price  # Conservative: assume same as spot
        
        # Analyze export opportunity
        try:
            result = self.export_analyzer.should_export_energy(
                spot_price=spot_price,
                purchase_price=purchase_price,
                export_price=export_price,
                battery_soc=battery_soc,
                battery_capacity_kwh=battery_capacity_kwh,
                upcoming_high_cost_hours=upcoming_high_cost_hours,
                solar_excess_w=solar_excess_w,
            )
            
            self.data["export_opportunity"] = result
            
            if result["should_export"]:
                _LOGGER.debug(
                    "Export opportunity detected: power=%dW, revenue=%.2f SEK/kWh, reason=%s",
                    result["export_power_w"],
                    result["estimated_revenue_per_kwh"],
                    result["reason"]
                )
        
        except Exception as e:
            _LOGGER.warning("Failed to analyze export opportunity: %s", e)
            self.data["export_opportunity"] = {
                "should_export": False,
                "reason": f"Analysis error: {str(e)}",
                "export_power_w": 0,
                "estimated_revenue_per_kwh": 0.0,
                "export_price_sek_per_kwh": 0.0,
                "opportunity_cost": 0.0,
                "battery_soc": battery_soc,
                "solar_excess_w": solar_excess_w,
                "duration_estimate_h": 0.0,
                "battery_degradation_cost": 0.0,
                "net_revenue": 0.0,
            }

    async def _update_load_shift_recommendations(self):
        """Generate load shifting recommendations."""
        from .load_shift_optimizer import LoadShiftOptimizer
        from .const import (
            CONF_ENABLE_LOAD_SHIFTING,
            CONF_LOAD_SHIFT_FLEXIBILITY_HOURS,
            CONF_BASELINE_LOAD_W,
        )
        
        # Check if load shifting is enabled
        if not bool(self._get_cfg(CONF_ENABLE_LOAD_SHIFTING, False)):
            self.data["load_shift_opportunities"] = []
            return
        
        # Check if we have necessary data
        hourly_prices = self.data.get("hourly_prices", [])
        if not hourly_prices:
            self.data["load_shift_opportunities"] = []
            return
        
        # Get current load from sensors
        load_power_entity = self._get_cfg(CONF_LOAD_POWER_ENTITY, "")
        current_consumption_w = self._read_float(load_power_entity) if load_power_entity else None
        
        if current_consumption_w is None or current_consumption_w <= 0:
            self.data["load_shift_opportunities"] = []
            return
        
        try:
            optimizer = LoadShiftOptimizer()
            
            baseline_load_w = float(self._get_cfg(CONF_BASELINE_LOAD_W, 300))
            flexibility_hours = int(self._get_cfg(CONF_LOAD_SHIFT_FLEXIBILITY_HOURS, 6))
            
            recommendations = optimizer.recommend_load_shifts(
                current_time=dt_util.now(),
                baseline_load_w=baseline_load_w,
                current_consumption_w=current_consumption_w,
                prices=hourly_prices,
                user_flexibility_hours=flexibility_hours,
            )
            
            # Add required fields for comfort filtering
            for rec in recommendations:
                rec["action"] = "load_shift"
                # Load shifting is typically medium impact
                rec["user_impact"] = rec.get("user_impact", "medium")
                rec["inconvenience_score"] = rec.get("inconvenience_score", 2.0)
                rec["savings_sek"] = rec.get("savings_per_hour_sek", 0)
            
            # Apply comfort filtering
            from .comfort_manager import ComfortManager
            from .const import (
                CONF_COMFORT_PRIORITY,
                CONF_QUIET_HOURS_START,
                CONF_QUIET_HOURS_END,
                CONF_MIN_BATTERY_PEACE_OF_MIND,
            )
            
            comfort_manager = ComfortManager(
                comfort_priority=self._get_cfg(CONF_COMFORT_PRIORITY, "balanced"),
                quiet_hours_start=self._get_cfg(CONF_QUIET_HOURS_START, "22:00"),
                quiet_hours_end=self._get_cfg(CONF_QUIET_HOURS_END, "07:00"),
                min_battery_peace_of_mind=float(self._get_cfg(CONF_MIN_BATTERY_PEACE_OF_MIND, 20)),
            )
            
            batt_soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
            battery_soc = self._read_float(batt_soc_entity) if batt_soc_entity else None
            
            filtered_recs, filtered_out = comfort_manager.optimize_with_comfort_balance(
                recommendations,
                battery_soc=battery_soc,
            )
            
            self.data["load_shift_opportunities"] = filtered_recs
            if filtered_out:
                self.data["load_shift_opportunities_filtered_by_comfort"] = filtered_out
            
            if recommendations:
                _LOGGER.debug(
                    "Found %d load shift opportunities, best savings: %.2f SEK/h",
                    len(recommendations),
                    recommendations[0].get("savings_per_hour_sek", 0),
                )
        except Exception as e:
            _LOGGER.warning("Failed to generate load shift recommendations: %s", e)
            self.data["load_shift_opportunities"] = []

    async def _update_peak_shaving_status(self):
        """Update peak shaving status and recommendations."""
        from .peak_shaving import PeakShaving
        from .const import (
            CONF_ENABLE_PEAK_SHAVING,
            CONF_PEAK_THRESHOLD_W,
        )
        
        # Check if peak shaving is enabled
        if not bool(self._get_cfg(CONF_ENABLE_PEAK_SHAVING, False)):
            self.data["peak_shaving_action"] = {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": "Peak shaving disabled",
            }
            return
        
        # Get grid import power
        load_power_entity = self._get_cfg(CONF_LOAD_POWER_ENTITY, "")
        grid_import_w = self._read_float(load_power_entity) if load_power_entity else None
        
        if grid_import_w is None:
            self.data["peak_shaving_action"] = {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": "No grid import data available",
            }
            return
        
        # Get battery state
        batt_soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
        battery_soc = self._read_float(batt_soc_entity) if batt_soc_entity else 0.0
        if battery_soc is None:
            battery_soc = 0.0
        
        battery_capacity_kwh = _safe_float(self._get_cfg(CONF_BATT_CAP_KWH), 15.0)
        battery_max_discharge_w = int(self._get_cfg(CONF_BATT_MAX_DISCH_W, 4000))
        
        # Get reserve SOC from cost strategy or use default
        battery_reserve_soc = 20.0  # Default reserve
        
        # Get peak threshold
        peak_threshold_w = float(self._get_cfg(CONF_PEAK_THRESHOLD_W, 10000))
        
        try:
            peak_shaver = PeakShaving()
            
            action = peak_shaver.calculate_peak_shaving_action(
                current_grid_import_w=grid_import_w,
                peak_threshold_w=peak_threshold_w,
                battery_soc=battery_soc,
                battery_max_discharge_w=battery_max_discharge_w,
                battery_reserve_soc=battery_reserve_soc,
                battery_capacity_kwh=battery_capacity_kwh,
                solar_production_w=0.0,  # Solar is already factored into grid_import_w
            )
            
            # Check if comfort settings allow peak shaving discharge
            if action.get("discharge_battery", False):
                from .comfort_manager import ComfortManager
                from .const import (
                    CONF_COMFORT_PRIORITY,
                    CONF_QUIET_HOURS_START,
                    CONF_QUIET_HOURS_END,
                    CONF_MIN_BATTERY_PEACE_OF_MIND,
                )
                
                comfort_manager = ComfortManager(
                    comfort_priority=self._get_cfg(CONF_COMFORT_PRIORITY, "balanced"),
                    quiet_hours_start=self._get_cfg(CONF_QUIET_HOURS_START, "22:00"),
                    quiet_hours_end=self._get_cfg(CONF_QUIET_HOURS_END, "07:00"),
                    min_battery_peace_of_mind=float(self._get_cfg(CONF_MIN_BATTERY_PEACE_OF_MIND, 20)),
                )
                
                allowed, reason = comfort_manager.should_allow_operation(
                    "discharge",
                    battery_soc=battery_soc,
                    scheduled_time=dt_util.now(),
                )
                
                if not allowed:
                    action["discharge_battery"] = False
                    action["discharge_power_w"] = 0
                    action["reason"] = f"Peak shaving blocked by comfort settings: {reason}"
                    action["filtered_by_comfort"] = reason
            
            self.data["peak_shaving_action"] = action
            
            if action.get("discharge_battery", False):
                _LOGGER.info(
                    "Peak shaving active: %s",
                    action.get("reason", ""),
                )
        except Exception as e:
            _LOGGER.warning("Failed to calculate peak shaving action: %s", e)
            self.data["peak_shaving_action"] = {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": f"Error: {e}",
            }

    # ---------- optimization plan ----------
    async def _update_optimization_plan(self):
        """Generate optimization plan using planner module."""
        # Check if we have necessary data
        hourly_prices = self.data.get("hourly_prices", [])
        if not hourly_prices:
            self.data["optimization_plan"] = []
            self.data["optimization_plan_status"] = "missing_price_data"
            _LOGGER.warning(
                "Optimization plan unavailable: No price data. "
                "Check that nordpool_entity is configured and providing hourly prices."
            )
            return
        
        try:
            # Get current battery state
            batt_soc_entity = self._get_cfg(CONF_BATT_SOC_ENTITY, "")
            if not batt_soc_entity:
                self.data["optimization_plan"] = []
                self.data["optimization_plan_status"] = "missing_battery_soc_entity"
                _LOGGER.warning(
                    "Optimization plan unavailable: Battery SOC entity not configured. "
                    "Configure 'Battery SOC Sensor' in integration settings."
                )
                return
            
            batt_soc_pct = self._read_float(batt_soc_entity)
            if batt_soc_pct is None:
                self.data["optimization_plan"] = []
                self.data["optimization_plan_status"] = "battery_soc_unavailable"
                _LOGGER.warning(
                    "Optimization plan unavailable: Battery SOC sensor '%s' is not available or not reporting a valid value. "
                    "Check sensor state in Developer Tools → States.",
                    batt_soc_entity
                )
                return
            
            # Get battery capacity
            batt_capacity_kwh = _safe_float(self._get_cfg(CONF_BATT_CAP_KWH), 15.0)
            if batt_capacity_kwh is None or batt_capacity_kwh <= 0:
                self.data["optimization_plan"] = []
                self.data["optimization_plan_status"] = "invalid_battery_capacity"
                _LOGGER.warning(
                    "Optimization plan unavailable: Invalid battery capacity (%s kWh). "
                    "Configure 'Battery Capacity (kWh)' in integration settings.",
                    batt_capacity_kwh
                )
                return
            
            # Get battery power limits
            batt_max_charge_w = int(self._get_cfg(CONF_BATT_MAX_CHARGE_W, 4000))
            
            # Get solar forecast data
            solar_points = self.data.get("solar_points", [])
            
            # Get EV needs (simplified - using configured target)
            # In future, this could be calculated from current vs target SOC
            ev_need_kwh = 0.0  # Default to no EV charging needed
            
            # Get cost thresholds
            cheap_threshold = _safe_float(self._get_cfg(CONF_COST_CHEAP_THRESHOLD, 1.5), 1.5)
            
            # Get export mode and degradation cost
            export_mode = self._get_cfg(CONF_EXPORT_MODE, "never")
            degradation_cost = _safe_float(
                self._get_cfg(CONF_BATTERY_DEGRADATION_COST_PER_CYCLE_SEK, 0.50), 
                0.50
            )
            
            min_arbitrage_profit = _safe_float(
                self._get_cfg(CONF_MIN_ARBITRAGE_PROFIT_SEK_PER_KWH, 0.10),
                0.10
            )
            
            # Generate plan
            now = dt_util.now()
            plan = simple_plan(
                now=now,
                horizon_hours=24,
                prices=hourly_prices,
                solar=solar_points,
                batt_soc_pct=batt_soc_pct,
                batt_capacity_kwh=batt_capacity_kwh,
                batt_max_charge_w=batt_max_charge_w,
                ev_need_kwh=ev_need_kwh,
                cheap_threshold=cheap_threshold,
                ev_deadline=None,
                ev_mode=ChargingMode.ECO,
                cost_strategy=self._cost_strategy,
                export_mode=export_mode,
                battery_degradation_per_cycle=degradation_cost,
                min_arbitrage_profit=min_arbitrage_profit,
            )
            
            self.data["optimization_plan"] = plan
            self.data["optimization_plan_status"] = "ok"
            _LOGGER.debug("Generated optimization plan with %d actions", len(plan))
            
        except Exception as e:
            _LOGGER.warning("Failed to generate optimization plan: %s", e, exc_info=True)
            self.data["optimization_plan"] = []
            self.data["optimization_plan_status"] = f"error: {str(e)}"

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

    def _calculate_battery_grid_charging(self, batt_states, pv_states) -> float:
        """
        Calculate battery grid charging by identifying periods where battery charged
        but no solar generation was present (forced grid charging).
        
        Args:
            batt_states: List of battery charged energy counter states
            pv_states: List of PV generation energy counter states
            
        Returns:
            Total kWh of battery grid charging (charging without solar)
        """
        from collections import defaultdict
        
        # Build hourly aggregates
        hourly_batt_charge = defaultdict(float)
        hourly_pv_gen = defaultdict(float)
        
        # Aggregate battery charging by hour
        for i in range(len(batt_states) - 1):
            val_start = _safe_float(batt_states[i].state)
            val_end = _safe_float(batt_states[i + 1].state)
            
            if val_start is None or val_end is None:
                continue
            
            ts_start = batt_states[i].last_changed
            hour_start = ts_start.replace(minute=0, second=0, microsecond=0)
            
            charge_delta = val_end - val_start
            if charge_delta > 0:  # Only count charging (ignore counter resets)
                hourly_batt_charge[hour_start] += charge_delta
        
        # Aggregate PV generation by hour
        for i in range(len(pv_states) - 1):
            val_start = _safe_float(pv_states[i].state)
            val_end = _safe_float(pv_states[i + 1].state)
            
            if val_start is None or val_end is None:
                continue
            
            ts_start = pv_states[i].last_changed
            hour_start = ts_start.replace(minute=0, second=0, microsecond=0)
            
            pv_delta = val_end - val_start
            if pv_delta > 0:  # Only count generation (ignore counter resets)
                hourly_pv_gen[hour_start] += pv_delta
        
        # Calculate grid charging: battery charging when no solar is present
        # Use a small threshold (0.01 kWh) to account for negligible nighttime solar readings
        grid_charge_total = 0.0
        PV_THRESHOLD = 0.01  # kWh - ignore very small PV values (sensor noise at night)
        
        for hour_ts, batt_charge in hourly_batt_charge.items():
            pv_gen = hourly_pv_gen.get(hour_ts, 0.0)
            
            # If battery is charging but PV is negligible, it's grid charging
            if batt_charge > 0.0 and pv_gen < PV_THRESHOLD:
                grid_charge_total += batt_charge
        
        _LOGGER.debug(
            "Battery grid charging analysis: %.3f kWh charged during periods with no solar",
            grid_charge_total
        )
        
        return grid_charge_total



    async def _calculate_48h_baseline(self) -> Optional[Dict[str, Optional[float]]]:
        """
        Calculate baseline from last 48 hours using energy counter deltas.
        Returns dict with key 'overall' containing kWh/h value.
        Also includes 'failure_reason' key if calculation fails.
        Uses energy counters (kWh) to calculate consumption, excluding EV charging 
        and battery grid charging based on their respective energy counters.
        """
        lookback_hours = int(self._get_cfg(CONF_RUNTIME_LOOKBACK_HOURS, 48))
        
        # Get the required energy counter entities
        house_energy_ent = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
        if not house_energy_ent:
            _LOGGER.debug(
                "48h baseline: No house energy counter configured (runtime_counter_entity)"
            )
            return {
                "overall": None,
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
            
            if exclude_batt_grid and batt_states and pv_states:
                # Calculate battery grid charging by identifying periods where battery charged
                # but no solar was available (i.e., forced grid charging at night)
                batt_grid_kwh = self._calculate_battery_grid_charging(
                    batt_states, pv_states
                )
                net_house_kwh -= batt_grid_kwh
                _LOGGER.debug("Excluding battery grid charging: %.3f kWh (from time-based analysis)", 
                             batt_grid_kwh)
            
            # Ensure we don't have negative consumption
            net_house_kwh = max(0.0, net_house_kwh)
            
            # Calculate average consumption rate (kWh/h)
            time_delta_h = lookback_hours
            avg_kwh_per_h = net_house_kwh / time_delta_h
            
            # Clip to reasonable range
            avg_kwh_per_h = max(0.05, min(5.0, avg_kwh_per_h))
            
            results = {
                "overall": avg_kwh_per_h,
            }
            
            # Calculate batt_grid_kwh for logging
            batt_grid_kwh_log = 0.0
            if exclude_batt_grid and batt_states and pv_states:
                batt_grid_kwh_log = self._calculate_battery_grid_charging(batt_states, pv_states)
            
            _LOGGER.debug(
                "48h baseline calculated: overall=%.3f kWh/h "
                "(house: %.3f kWh, ev: %.3f kWh, batt_grid: %.3f kWh over %d hours)",
                avg_kwh_per_h,
                house_delta, ev_delta, 
                batt_grid_kwh_log,
                lookback_hours
            )
            
            return results
            
        except Exception as e:
            _LOGGER.warning("Failed to calculate 48h baseline: %s", e, exc_info=True)
            return {
                "overall": None,
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
                "48h baseline calculation succeeded: overall=%s",
                baseline_48h.get("overall"),
            )
            
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
                "Baseline: method=energy_counter_48h overall=%.3f kWh/h",
                visible_kwh_h or 0,
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
        Uses energy deltas (kWh) for accurate solar vs grid classification.
        Calls bec.on_charge() when battery charges and bec.on_discharge() when it discharges.
        
        Handles missing data:
        - If data is unavailable for > 1 hour, resets tracking to avoid incorrect deltas
        - Waits up to 15 minutes for data before assuming sensor is unavailable
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
            self._prev_pv_energy_today = None
            self._prev_house_energy = None
            self._prev_grid_import_today = None
            self._batt_last_update_time = None
            self._batt_last_reset_date = current_date
            _LOGGER.debug("Battery tracking reset for new day: %s", current_date)
        
        # Get configured entities
        charged_entity = self._get_cfg(CONF_BATT_ENERGY_CHARGED_TODAY_ENTITY, "")
        discharged_entity = self._get_cfg(CONF_BATT_ENERGY_DISCHARGED_TODAY_ENTITY, "")
        
        if not charged_entity and not discharged_entity:
            # No tracking entities configured
            return
        
        # Check if previous data is too old (> 1 hour for BEC)
        # This prevents incorrect deltas when sensors were unavailable
        if self._batt_last_update_time is not None:
            gap_minutes = (now - self._batt_last_update_time).total_seconds() / 60.0
            if gap_minutes > 60:  # 1 hour max gap for BEC
                _LOGGER.warning(
                    "BEC: Data gap of %.1f minutes exceeds 1 hour limit. "
                    "Resetting tracking to avoid incorrect deltas.",
                    gap_minutes
                )
                # Reset tracking to start fresh
                self._batt_prev_charged_today = None
                self._batt_prev_discharged_today = None
                self._prev_pv_energy_today = None
                self._prev_house_energy = None
                self._prev_grid_import_today = None
                self._batt_last_update_time = None
        
        # Get current price for charging cost calculation (the only reliable direct cost value)
        current_price = self.data.get("current_enriched", 0.0) or 0.0
        
        # Get energy sensors for delta-based calculation
        pv_energy_entity = self._get_cfg(CONF_PV_ENERGY_TODAY_ENTITY, "")
        house_energy_entity = self._get_cfg(CONF_RUNTIME_COUNTER_ENTITY, "")
        grid_import_entity = self._get_cfg(CONF_GRID_IMPORT_TODAY_ENTITY, "")
        
        # Read current energy values
        pv_energy_today = None
        if pv_energy_entity:
            st = self.hass.states.get(pv_energy_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                pv_energy_today = _safe_float(st.state)
        
        house_energy = None
        if house_energy_entity:
            st = self.hass.states.get(house_energy_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                house_energy = _safe_float(st.state)
        
        grid_import_today = None
        if grid_import_entity:
            st = self.hass.states.get(grid_import_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                grid_import_today = _safe_float(st.state)
        
        # Track if we got valid data in this update cycle
        got_valid_data = False
        
        # Track charging
        if charged_entity:
            st = self.hass.states.get(charged_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                charged_today = _safe_float(st.state)
                if charged_today is not None:
                    got_valid_data = True
                    if self._batt_prev_charged_today is not None:
                        delta_charged = charged_today - self._batt_prev_charged_today
                        if delta_charged > 0.001:  # At least 1 Wh change
                            # Determine if charging from grid or solar using energy deltas
                            # This is the safest method - comparing kWh to kWh over the same period
                            source = "grid"  # Default to grid (conservative)
                            
                            # Calculate energy deltas over the same time period
                            delta_pv = 0.0
                            if pv_energy_today is not None and self._prev_pv_energy_today is not None:
                                delta_pv = max(0.0, pv_energy_today - self._prev_pv_energy_today)
                            
                            delta_grid_import = 0.0
                            if grid_import_today is not None and self._prev_grid_import_today is not None:
                                delta_grid_import = max(0.0, grid_import_today - self._prev_grid_import_today)
                            
                            # Determine source based on energy deltas
                            if delta_pv > 0:
                                # We have PV production in this period
                                # If PV delta >= battery charge delta, it's definitely solar
                                if delta_pv >= delta_charged * 0.95:  # 95% threshold for measurement tolerances
                                    source = "solar"
                                # If we have grid import data, use it for verification
                                elif delta_grid_import > 0:
                                    # Grid was imported, so likely grid charging
                                    source = "grid"
                                else:
                                    # No grid import, PV available but less than battery charge
                                    # This could be mixed solar/grid - be conservative
                                    source = "grid"
                            
                            if source == "solar":
                                cost = 0.0  # Solar is free
                            else:
                                cost = current_price  # Use enriched price (the only reliable direct cost)
                            
                            _LOGGER.info(
                                "Battery charged: %.3f kWh from %s @ %.3f SEK/kWh (PV delta: %.3f kWh, Grid import: %.3f kWh)",
                                delta_charged, source, cost, delta_pv, delta_grid_import
                            )
                            bec.on_charge(delta_charged, cost, source)
                            await bec.async_save()
                    
                    self._batt_prev_charged_today = charged_today
            else:
                # Data unavailable - check if we should wait or reset
                if _is_data_stale(self._batt_last_update_time, max_age_minutes=15):
                    _LOGGER.debug(
                        "BEC: Charged energy sensor %s unavailable for > 15 minutes, treating as no data",
                        charged_entity
                    )
        
        # Track discharging
        if discharged_entity:
            st = self.hass.states.get(discharged_entity)
            if st and st.state not in (None, "", "unknown", "unavailable"):
                discharged_today = _safe_float(st.state)
                if discharged_today is not None:
                    got_valid_data = True
                    if self._batt_prev_discharged_today is not None:
                        delta_discharged = discharged_today - self._batt_prev_discharged_today
                        if delta_discharged > 0.001:  # At least 1 Wh change
                            _LOGGER.info("Battery discharged: %.3f kWh", delta_discharged)
                            bec.on_discharge(delta_discharged)
                            await bec.async_save()
                    
                    self._batt_prev_discharged_today = discharged_today
            else:
                # Data unavailable - check if we should wait or reset
                if _is_data_stale(self._batt_last_update_time, max_age_minutes=15):
                    _LOGGER.debug(
                        "BEC: Discharged energy sensor %s unavailable for > 15 minutes, treating as no data",
                        discharged_entity
                    )
        
        # Update last update timestamp if we got any valid data
        if got_valid_data:
            self._batt_last_update_time = now
        
        # Update previous energy values for next iteration
        if pv_energy_today is not None:
            self._prev_pv_energy_today = pv_energy_today
        if house_energy is not None:
            self._prev_house_energy = house_energy
        if grid_import_today is not None:
            self._prev_grid_import_today = grid_import_today

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
