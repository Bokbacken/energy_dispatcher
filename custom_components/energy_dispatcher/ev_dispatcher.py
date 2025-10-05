from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Optional

from homeassistant.core import HomeAssistant

from .const import (
    CONF_EVSE_START_SWITCH,
    CONF_EVSE_STOP_SWITCH,
    CONF_EVSE_CURRENT_NUMBER,
    CONF_EVSE_MIN_A,
    CONF_EVSE_MAX_A,
    CONF_EVSE_POWER_SENSOR,
    CONF_EVSE_ENERGY_SENSOR,
    CONF_EVSE_TOTAL_ENERGY_SENSOR,
    CONF_EV_BATT_KWH,
    DOMAIN,
    STORE_MANUAL,
    M_EV_CURRENT_SOC,
    M_EV_TARGET_SOC,
    M_EV_BATT_KWH,
)

_LOGGER = logging.getLogger(__name__)


class EVDispatcher:
    """
    EV-kontroller som kan:
      - trycka button/script eller slå på/av switch/input_boolean
      - sätta laddström via number.set_value
      - hantera overrides: pause/force och "forced current"

    Koordinatorn anropar:
      - is_paused(now), is_forced(now)
      - get_forced_ev_current()
      - async_apply_ev_setpoint(amps)
    """

    def __init__(self, hass: HomeAssistant, cfg_lookup: Callable[[str, Optional[object]], object], entry_id: str):
        self.hass = hass
        self._cfg = cfg_lookup
        self._entry_id = entry_id

        # Overrides
        self._overrides: dict[str, datetime] = {}
        self._forced_ev_current: Optional[int] = None
        
        # Charging session tracking
        self._charging_session_active: bool = False
        self._session_start_soc: Optional[float] = None
        self._session_start_energy: Optional[float] = None  # From total energy counter
        self._session_target_soc: Optional[float] = None

    # ==== Overrides ====
    def set_override(self, key: str, until: datetime):
        self._overrides[key] = until

    def clear_override(self, key: str):
        self._overrides.pop(key, None)

    def get_override_until(self, key: str) -> Optional[datetime]:
        return self._overrides.get(key)

    def is_paused(self, now: datetime) -> bool:
        u = self._overrides.get("ev_pause_until")
        return bool(u and u > now)

    def is_forced(self, now: datetime) -> bool:
        u = self._overrides.get("ev_force_until")
        return bool(u and u > now)

    def set_forced_ev_current(self, amps: Optional[int]):
        self._forced_ev_current = amps

    def get_forced_ev_current(self) -> Optional[int]:
        return self._forced_ev_current

    # ==== Helpers ====
    def _available(self, entity_id: str) -> bool:
        if not entity_id:
            return False
        st = self.hass.states.get(entity_id)
        return bool(st and str(st.state).lower() != "unavailable")

    async def _press_or_turn(self, entity_id: str, on: bool):
        if not entity_id:
            return
        if not self._available(entity_id):
            _LOGGER.warning("EVDispatcher: entity %s unavailable, skipping", entity_id)
            return

        domain = entity_id.split(".")[0]
        if domain == "button":
            await self.hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
            _LOGGER.debug("EVDispatcher: button.press %s", entity_id)
            return

        if domain in ("switch", "input_boolean"):
            service = "turn_on" if on else "turn_off"
            await self.hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)
            _LOGGER.debug("EVDispatcher: %s.%s %s", domain, service, entity_id)
            return

        if domain == "script":
            await self.hass.services.async_call("script", "turn_on", {"entity_id": entity_id}, blocking=True)
            _LOGGER.debug("EVDispatcher: script.turn_on %s", entity_id)
            return

        # fallback via homeassistant.turn_on/off för andra domäner som stöder det
        service = "turn_on" if on else "turn_off"
        await self.hass.services.async_call("homeassistant", service, {"entity_id": entity_id}, blocking=True)
        _LOGGER.debug("EVDispatcher: homeassistant.%s %s", service, entity_id)

    async def _set_current(self, amps: int):
        num_ent = self._cfg(CONF_EVSE_CURRENT_NUMBER, "")
        if not num_ent:
            return
        if not self._available(num_ent):
            _LOGGER.warning("EVDispatcher: current number %s unavailable, skipping", num_ent)
            return
        try:
            await self.hass.services.async_call(
                "number", "set_value", {"entity_id": num_ent, "value": float(amps)}, blocking=True
            )
            _LOGGER.debug("EVDispatcher: number.set_value %s = %s A", num_ent, amps)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("EVDispatcher: failed to set current to %s A", amps)

    def _read_sensor_float(self, entity_id: str) -> Optional[float]:
        """Read a float value from a sensor, handling common units."""
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in ("unknown", "unavailable", None, ""):
            return None
        try:
            value = float(st.state)
            unit = st.attributes.get("unit_of_measurement", "").lower()
            
            # Convert W to kW if needed
            if "power" in entity_id.lower() and unit == "w":
                value = value / 1000.0
            # Convert Wh to kWh if needed
            elif "energy" in entity_id.lower() and unit == "wh":
                value = value / 1000.0
                
            return value
        except (ValueError, TypeError):
            return None

    def _is_charging(self) -> bool:
        """Check if EV is currently charging based on current sensor or start switch state."""
        # Check current sensor first
        num_current = self._cfg(CONF_EVSE_CURRENT_NUMBER, "")
        if num_current:
            st = self.hass.states.get(num_current)
            if st and st.state not in ("unknown", "unavailable", None, ""):
                try:
                    amps = float(st.state)
                    min_a = int(self._cfg(CONF_EVSE_MIN_A, 6))
                    if amps >= min_a:
                        return True
                except (ValueError, TypeError):
                    pass
        
        # Fallback: check if start switch/button is in "on" state (for switches/input_boolean)
        start_ent = self._cfg(CONF_EVSE_START_SWITCH, "")
        if start_ent and start_ent.split(".")[0] in ("switch", "input_boolean"):
            st = self.hass.states.get(start_ent)
            if st and str(st.state).lower() == "on":
                return True
        
        return False

    def _start_charging_session(self):
        """Start tracking a charging session."""
        # Get current SOC from STORE_MANUAL
        store = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        manual = store.get(STORE_MANUAL, {})
        
        current_soc = manual.get(M_EV_CURRENT_SOC)
        target_soc = manual.get(M_EV_TARGET_SOC)
        
        if current_soc is not None and target_soc is not None:
            self._charging_session_active = True
            self._session_start_soc = float(current_soc)
            self._session_target_soc = float(target_soc)
            
            # Read initial energy counter if available
            total_energy_sensor = self._cfg(CONF_EVSE_TOTAL_ENERGY_SENSOR, "")
            if total_energy_sensor:
                self._session_start_energy = self._read_sensor_float(total_energy_sensor)
            
            _LOGGER.info(
                "EVDispatcher: Started charging session - SOC: %.1f%% → %.1f%%, Start energy: %s kWh",
                self._session_start_soc,
                self._session_target_soc,
                self._session_start_energy if self._session_start_energy is not None else "N/A"
            )
    
    def _check_charging_complete(self) -> bool:
        """Check if charging is complete and update SOC if so."""
        if not self._charging_session_active:
            return False
        
        # Get charging power
        power_sensor = self._cfg(CONF_EVSE_POWER_SENSOR, "")
        charging_power = self._read_sensor_float(power_sensor) if power_sensor else None
        
        # Check if power is near zero (< 0.5 kW)
        if charging_power is not None and charging_power < 0.5:
            # Calculate charged energy and estimate new SOC
            store = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
            manual = store.get(STORE_MANUAL, {})
            battery_kwh = manual.get(M_EV_BATT_KWH, 75.0)
            
            energy_charged = None
            
            # Try to get energy charged from session energy sensor
            energy_sensor = self._cfg(CONF_EVSE_ENERGY_SENSOR, "")
            if energy_sensor:
                energy_charged = self._read_sensor_float(energy_sensor)
            
            # Or calculate from total energy counter difference
            if energy_charged is None:
                total_energy_sensor = self._cfg(CONF_EVSE_TOTAL_ENERGY_SENSOR, "")
                if total_energy_sensor and self._session_start_energy is not None:
                    current_total = self._read_sensor_float(total_energy_sensor)
                    if current_total is not None:
                        energy_charged = current_total - self._session_start_energy
            
            if energy_charged is not None and energy_charged > 0:
                # Calculate new SOC
                soc_increase = (energy_charged / battery_kwh) * 100.0
                new_soc = min(100.0, self._session_start_soc + soc_increase)
                
                # Update STORE_MANUAL with new SOC
                manual[M_EV_CURRENT_SOC] = new_soc
                
                _LOGGER.info(
                    "EVDispatcher: Charging complete! Charged %.2f kWh, SOC: %.1f%% → %.1f%%",
                    energy_charged,
                    self._session_start_soc,
                    new_soc
                )
                
                # Fire event for UI notification
                self.hass.bus.async_fire(
                    "energy_dispatcher.charging_complete",
                    {
                        "entry_id": self._entry_id,
                        "start_soc": self._session_start_soc,
                        "end_soc": new_soc,
                        "energy_charged_kwh": energy_charged,
                        "target_soc": self._session_target_soc,
                    }
                )
                
                # End session
                self._charging_session_active = False
                self._session_start_soc = None
                self._session_start_energy = None
                self._session_target_soc = None
                
                return True
        
        return False

    # ==== Publikt API ====
    async def async_apply_ev_setpoint(self, amps: int):
        min_a = int(self._cfg(CONF_EVSE_MIN_A, 6))
        max_a = int(self._cfg(CONF_EVSE_MAX_A, 16))
        amps = max(0, min(max_a, int(amps)))

        start_ent = self._cfg(CONF_EVSE_START_SWITCH, "")
        stop_ent = self._cfg(CONF_EVSE_STOP_SWITCH, "")
        
        was_charging = self._is_charging()

        if amps >= min_a:
            # Sätt ström först, tryck sedan start (men bara om inte redan laddar)
            await self._set_current(amps)
            if not was_charging:
                await self._press_or_turn(start_ent, on=True)
                # Start tracking charging session
                self._start_charging_session()
            else:
                _LOGGER.debug("EVDispatcher: already charging, skipping start button")
        else:
            # Stanna laddning (men bara om laddar för tillfället)
            if was_charging:
                await self._press_or_turn(stop_ent or start_ent, on=False)
            else:
                _LOGGER.debug("EVDispatcher: already stopped, skipping stop button")
        
        # Check if charging is complete (updates SOC automatically)
        if self._charging_session_active:
            self._check_charging_complete()
    
    def get_charging_session_info(self) -> dict:
        """Get current charging session information."""
        return {
            "active": self._charging_session_active,
            "start_soc": self._session_start_soc,
            "target_soc": self._session_target_soc,
            "start_energy": self._session_start_energy,
        }
