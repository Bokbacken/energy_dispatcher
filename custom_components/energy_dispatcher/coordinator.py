from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, List

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    # Baseline/Runtime
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
    # EV/EVSE (för enklare EV-exkludering om ingen direkt EV-power finns)
    CONF_EVSE_CURRENT_NUMBER,
    CONF_EVSE_PHASES,
    CONF_EVSE_VOLTAGE,
    # PV (för pv_now_w om användaren pekat ut faktisk produktion)
    CONF_PV_POWER_ENTITY,
    # Batteri SOC entitet (används av sensorer)
    CONF_BATT_SOC_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


def _safe_float(v: Any, default: Optional[float] = None) -> Optional[float]:
    """Best effort: parse value to float, handling None, 'unknown', 'unavailable' and decimal commas."""
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            f = float(v)
            if math.isnan(f):
                return default
            return f
        s = str(v).strip()
        if s in ("unknown", "unavailable", "", "None"):
            return default
        s = s.replace(",", ".")
        f = float(s)
        if math.isnan(f):
            return default
        return f
    except Exception:
        return default


def _as_watts(value: Any, unit: Optional[str]) -> Optional[float]:
    """Convert to Watts if possible. If unit is 'kW', multiply by 1000; if 'W' or unknown, return as-is."""
    val = _safe_float(value)
    if val is None:
        return None
    if unit:
        u = str(unit).lower()
        if u == "kw":
            return val * 1000.0
        if u in ("w", "watt"):
            return val
    # If we don't know the unit, return the numeric value (assumed W).
    return val


@dataclass
class _RuntimeSample:
    ts: datetime
    value_w: float


class EnergyDispatcherCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Central coordinator for Energy Dispatcher.

    0.5.4 highlights in this file:
    - Robust baseline computation with graceful degradation of excludes (EV/Battery).
    - Power (W) is recommended/default source; Counter (kWh) supported with simple derivative.
    - Bootstrap baseline from Recorder history on cold start to avoid 'unknown'.
    - Tolerant parsing (kW→W, decimal commas).
    - Diagnostics in self.data['diag_status'] and ['diag_attrs'].
    """

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Energy Dispatcher Coordinator",
            update_interval=timedelta(seconds=30),
        )
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id

        # Runtime baseline state
        self._runtime_samples: List[_RuntimeSample] = []
        self._baseline_w: Optional[float] = None
        self._baseline_ready: bool = False
        self._bootstrap_done: bool = False

        # For counter_kwh derivative
        self._prev_counter: Optional[float] = None
        self._prev_counter_ts: Optional[datetime] = None

        # Data dict published to sensors/platforms
        self.data: Dict[str, Any] = {}

    # ---------- Config helpers ----------

    def _cfg(self, key: str, default: Any = None) -> Any:
        """Read config from options, fallback to data."""
        if key in self.entry.options:
            return self.entry.options.get(key, default)
        return self.entry.data.get(key, default)

    # Backwards-compat alias used by some sensors
    def _get_cfg(self, key: str, default: Any = None) -> Any:
        return self._cfg(key, default)

    # ---------- Entity helpers ----------

    def _state(self, entity_id: Optional[str]) -> Optional[State]:
        if not entity_id:
            return None
        try:
            return self.hass.states.get(entity_id)
        except Exception:
            return None

    def _num_state(self, entity_id: Optional[str]) -> Optional[float]:
        st = self._state(entity_id)
        if not st:
            return None
        return _safe_float(st.state)

    def _watts_from_entity(self, entity_id: Optional[str]) -> Optional[float]:
        st = self._state(entity_id)
        if not st:
            return None
        unit = st.attributes.get("unit_of_measurement")
        return _as_watts(st.state, unit)

    # ---------- Public methods ----------

    async def async_initialize(self) -> None:
        """Call once from __init__.py after creating the coordinator."""
        # First refresh
        await self.async_config_entry_first_refresh()

    # ---------- Update loop ----------

    async def _async_update_data(self) -> Dict[str, Any]:
        """Main periodic update. Compute baseline and other live diagnostics."""
        try:
            now = dt_util.utcnow()

            # 1) Resolve runtime source and inputs
            src = str(self._cfg(CONF_RUNTIME_SOURCE, "power_w"))
            alpha = float(self._cfg(CONF_RUNTIME_ALPHA, 0.4))
            window_min = int(self._cfg(CONF_RUNTIME_WINDOW_MIN, 10))
            exclude_ev = bool(self._cfg(CONF_RUNTIME_EXCLUDE_EV, False))
            exclude_batt = bool(self._cfg(CONF_RUNTIME_EXCLUDE_BATT_GRID, False))

            # Inputs for power_w
            power_ent = self._cfg(CONF_RUNTIME_POWER_ENTITY) or self._cfg(CONF_LOAD_POWER_ENTITY) or self._cfg("house_cons_sensor")
            load_w: Optional[float] = None

            # Inputs for counter_kwh
            counter_ent = self._cfg(CONF_RUNTIME_COUNTER_ENTITY)

            # EV exclude heuristics inputs
            evse_current_number = self._cfg(CONF_EVSE_CURRENT_NUMBER)
            evse_phases = _safe_float(self._cfg(CONF_EVSE_PHASES, 3)) or 3.0
            evse_voltage = _safe_float(self._cfg(CONF_EVSE_VOLTAGE, 230)) or 230.0

            # Battery exclude inputs
            batt_power_ent = self._cfg(CONF_BATT_POWER_ENTITY)
            grid_import_today_ent = self._cfg(CONF_GRID_IMPORT_TODAY_ENTITY)

            # 2) Acquire sample value (house load) depending on source
            sample_w: Optional[float] = None
            reasons: List[str] = []

            if src == "power_w":
                load_w = self._watts_from_entity(power_ent)
                if load_w is None:
                    reasons.append("load_w_none")
            elif src == "counter_kwh":
                # Derive power from energy counter
                sample_w = await self._derive_w_from_counter(counter_ent, now, reasons)
            else:
                # manual_dayparts or unknown → currently not implemented baseline here
                reasons.append(f"runtime_source_unsupported:{src}")

            # If power_w, sample is load_w minus excludes (apply below)
            if src == "power_w" and load_w is not None:
                sample_w = load_w

            # 3) Compute excludes robustly (errors degrade to 0 W)
            ev_excl_w = 0.0
            if exclude_ev:
                ev_excl_w = self._estimate_ev_power_w(evse_current_number, evse_phases, evse_voltage)

            batt_excl_w = 0.0
            if exclude_batt:
                batt_excl_w = self._estimate_batt_grid_charge_w(batt_power_ent, grid_import_today_ent)

            if sample_w is not None:
                sample_w = max(0.0, sample_w - ev_excl_w - batt_excl_w)

            # 4) Bootstrap baseline from Recorder history if we still don't have a sample
            if not self._bootstrap_done and (sample_w is None):
                boot = await self._bootstrap_from_history(power_ent, window_min)
                if boot is not None:
                    self._baseline_w = boot
                    self._baseline_ready = True
                    self._bootstrap_done = True
                    sample_w = boot
                    reasons.append("bootstrapped")

            # 5) EMA smoothing + windowing
            if sample_w is not None:
                self._runtime_samples.append(_RuntimeSample(now, sample_w))
                cutoff = now - timedelta(minutes=window_min if window_min > 0 else 1)
                self._runtime_samples = [s for s in self._runtime_samples if s.ts >= cutoff]

                if self._baseline_w is None:
                    self._baseline_w = sample_w
                else:
                    a = max(0.0, min(1.0, alpha))
                    self._baseline_w = a * sample_w + (1.0 - a) * self._baseline_w

                # Consider baseline ready when we have at least one sample (fast start)
                self._baseline_ready = len(self._runtime_samples) >= 1

            # 6) Publish diagnostics
            diag_status = "ok" if self._baseline_ready else "pending"
            diag_attrs = {
                "source": src,
                "ready": self._baseline_ready,
                "sample_count": len(self._runtime_samples),
                "last_sample_w": sample_w,
                "baseline_w": self._baseline_w,
                "alpha": alpha,
                "window_min": window_min,
                "ev_exclude_w": ev_excl_w if exclude_ev else 0.0,
                "batt_exclude_w": batt_excl_w if exclude_batt else 0.0,
                "reasons": reasons,
            }

            # 7) Also publish PV now (if user has actual PV sensor configured)
            pv_now_w = self._watts_from_entity(self._cfg(CONF_PV_POWER_ENTITY))

            # 8) Expose values to the integration
            self.data["house_baseline_w"] = self._baseline_w if self._baseline_ready else None
            self.data["pv_now_w"] = pv_now_w  # can be None
            # solar_now_w left as-is if some forecast provider populates it elsewhere; otherwise leave None
            self.data.setdefault("solar_now_w", None)

            self.data["diag_status"] = diag_status
            self.data["diag_attrs"] = diag_attrs

            return self.data

        except Exception as exc:
            raise UpdateFailed(f"Coordinator update failed: {exc}") from exc

    # ---------- Helper routines ----------

    async def _derive_w_from_counter(self, counter_entity: Optional[str], now: datetime, reasons: List[str]) -> Optional[float]:
        """Simple derivative from an energy counter (kWh)."""
        if not counter_entity:
            reasons.append("no_counter_entity")
            return None

        st = self._state(counter_entity)
        if not st:
            reasons.append("counter_state_none")
            return None

        cur = _safe_float(st.state)
        if cur is None:
            reasons.append("counter_not_numeric")
            return None

        if self._prev_counter is None or self._prev_counter_ts is None:
            self._prev_counter = cur
            self._prev_counter_ts = now
            reasons.append("counter_first_sample")
            return None

        dt = (now - self._prev_counter_ts).total_seconds()
        if dt <= 0:
            reasons.append("counter_dt_zero")
            return None

        delta_kwh = cur - self._prev_counter
        # Guard against midnattshopp/återställning
        if delta_kwh < -0.001:
            # reset – treat as first sample again
            self._prev_counter = cur
            self._prev_counter_ts = now
            reasons.append("counter_reset_detected")
            return None

        self._prev_counter = cur
        self._prev_counter_ts = now

        # W = kWh * 3600_000 / s
        w = (delta_kwh * 3_600_000.0) / dt
        if w < 0:
            reasons.append("counter_negative_derivative")
            return None
        return w

    def _estimate_ev_power_w(self, current_number_entity: Optional[str], phases: float, voltage: float) -> float:
        """Estimate EV charging power from EVSE current, if available. Gracefully degrade to 0."""
        try:
            cur_a = self._num_state(current_number_entity)
            if cur_a is None or cur_a <= 0:
                return 0.0
            ph = max(1.0, float(phases or 1.0))
            volt = max(100.0, float(voltage or 230.0))
            return max(0.0, ph * volt * float(cur_a))
        except Exception:
            return 0.0

    def _estimate_batt_grid_charge_w(self, batt_power_entity: Optional[str], grid_import_today_entity: Optional[str]) -> float:
        """Estimate power to exclude when battery is charging from grid. Conservative: any positive battery charge is excluded."""
        try:
            st = self._state(batt_power_entity)
            if not st:
                return 0.0
            unit = st.attributes.get("unit_of_measurement")
            batt_w = _as_watts(st.state, unit)
            if batt_w is None:
                return 0.0
            # Positive → charging. We conservatively exclude full positive charging power.
            if batt_w > 0:
                return batt_w
            return 0.0
        except Exception:
            return 0.0

    async def _bootstrap_from_history(self, power_entity: Optional[str], window_min: int) -> Optional[float]:
        """Try to build an initial baseline from Recorder history."""
        if not power_entity or window_min <= 0:
            return None
        try:
            # Import inside function to avoid hard dependency for users without recorder
            from homeassistant.components.recorder import history

            end = dt_util.utcnow()
            start = end - timedelta(minutes=window_min)
            hist = await self.hass.async_add_executor_job(
                history.state_changes_during_period,
                self.hass,
                start,
                end,
                {power_entity},
            )
            samples = []
            for s in hist.get(power_entity, []):
                unit = s.attributes.get("unit_of_measurement")
                w = _as_watts(s.state, unit)
                if w is not None and not math.isnan(w):
                    samples.append(w)
            if not samples:
                return None
            return sum(samples) / len(samples)
        except Exception as e:
            _LOGGER.debug("Bootstrap from history failed: %s", e)
            return None

    # ---------- Convenience for sensors ----------

    @property
    def batt_soc_entity(self) -> Optional[str]:
        return self._cfg(CONF_BATT_SOC_ENTITY)

    # ---------- Debug helpers ----------

    def dump_diag(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "data": self.data,
            "samples": len(self._runtime_samples),
            "baseline": self._baseline_w,
            "ready": self._baseline_ready,
        }
