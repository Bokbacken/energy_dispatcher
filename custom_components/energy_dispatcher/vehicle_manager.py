"""Manager for multiple vehicles and chargers."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant

from .models import (
    VehicleConfig,
    ChargerConfig,
    VehicleState,
    ChargingSession,
    ChargingMode,
)

_LOGGER = logging.getLogger(__name__)


class VehicleManager:
    """Manages multiple vehicles and their charging sessions."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._vehicles: Dict[str, VehicleConfig] = {}
        self._vehicle_states: Dict[str, VehicleState] = {}
        self._chargers: Dict[str, ChargerConfig] = {}
        self._sessions: Dict[str, ChargingSession] = {}
        
    def add_vehicle(self, config: VehicleConfig) -> None:
        """Add or update a vehicle configuration."""
        self._vehicles[config.id] = config
        if config.id not in self._vehicle_states:
            self._vehicle_states[config.id] = VehicleState(
                vehicle_id=config.id,
                current_soc=config.default_target_soc,
                target_soc=config.default_target_soc,
                charging_mode=ChargingMode.ECO,
            )
        _LOGGER.info("Added vehicle: %s (%s %s)", config.name, config.brand, config.model)
    
    def remove_vehicle(self, vehicle_id: str) -> None:
        """Remove a vehicle configuration."""
        self._vehicles.pop(vehicle_id, None)
        self._vehicle_states.pop(vehicle_id, None)
        _LOGGER.info("Removed vehicle: %s", vehicle_id)
    
    def get_vehicle(self, vehicle_id: str) -> Optional[VehicleConfig]:
        """Get vehicle configuration."""
        return self._vehicles.get(vehicle_id)
    
    def get_vehicles(self) -> List[VehicleConfig]:
        """Get all vehicle configurations."""
        return list(self._vehicles.values())
    
    def add_charger(self, config: ChargerConfig) -> None:
        """Add or update a charger configuration."""
        self._chargers[config.id] = config
        _LOGGER.info("Added charger: %s (%s %s)", config.name, config.brand, config.model)
    
    def remove_charger(self, charger_id: str) -> None:
        """Remove a charger configuration."""
        self._chargers.pop(charger_id, None)
        _LOGGER.info("Removed charger: %s", charger_id)
    
    def get_charger(self, charger_id: str) -> Optional[ChargerConfig]:
        """Get charger configuration."""
        return self._chargers.get(charger_id)
    
    def get_chargers(self) -> List[ChargerConfig]:
        """Get all charger configurations."""
        return list(self._chargers.values())
    
    def update_vehicle_state(
        self,
        vehicle_id: str,
        current_soc: Optional[float] = None,
        target_soc: Optional[float] = None,
        charging_mode: Optional[ChargingMode] = None,
        deadline: Optional[datetime] = None,
        is_connected: Optional[bool] = None,
        is_charging: Optional[bool] = None,
    ) -> None:
        """Update vehicle state."""
        if vehicle_id not in self._vehicle_states:
            _LOGGER.warning("Vehicle %s not found", vehicle_id)
            return
        
        state = self._vehicle_states[vehicle_id]
        if current_soc is not None:
            state.current_soc = max(0.0, min(100.0, current_soc))
        if target_soc is not None:
            state.target_soc = max(0.0, min(100.0, target_soc))
        if charging_mode is not None:
            state.charging_mode = charging_mode
        if deadline is not None:
            state.deadline = deadline
        if is_connected is not None:
            state.is_connected = is_connected
        if is_charging is not None:
            state.is_charging = is_charging
        state.last_update = datetime.now()
    
    def get_vehicle_state(self, vehicle_id: str) -> Optional[VehicleState]:
        """Get vehicle state."""
        return self._vehicle_states.get(vehicle_id)
    
    def start_charging_session(
        self,
        vehicle_id: str,
        charger_id: str,
        deadline: Optional[datetime] = None,
        mode: Optional[ChargingMode] = None,
    ) -> Optional[ChargingSession]:
        """Start a new charging session."""
        vehicle = self.get_vehicle(vehicle_id)
        charger = self.get_charger(charger_id)
        state = self.get_vehicle_state(vehicle_id)
        
        if not vehicle or not charger or not state:
            _LOGGER.error("Cannot start session: vehicle, charger, or state not found")
            return None
        
        # End any existing session for this vehicle
        self.end_charging_session(vehicle_id)
        
        session = ChargingSession(
            vehicle_id=vehicle_id,
            charger_id=charger_id,
            start_time=datetime.now(),
            start_soc=state.current_soc,
            target_soc=state.target_soc,
            deadline=deadline,
            mode=mode or state.charging_mode,
        )
        
        self._sessions[vehicle_id] = session
        state.is_charging = True
        
        _LOGGER.info(
            "Started charging session for %s: %.1f%% -> %.1f%%, mode=%s",
            vehicle.name,
            session.start_soc,
            session.target_soc,
            session.mode.value,
        )
        
        return session
    
    def end_charging_session(self, vehicle_id: str, energy_delivered: Optional[float] = None) -> Optional[ChargingSession]:
        """End an active charging session."""
        session = self._sessions.get(vehicle_id)
        if not session or not session.active:
            return None
        
        state = self.get_vehicle_state(vehicle_id)
        vehicle = self.get_vehicle(vehicle_id)
        
        session.end_time = datetime.now()
        session.active = False
        
        if state:
            session.end_soc = state.current_soc
            state.is_charging = False
        
        if energy_delivered is not None:
            session.energy_delivered = energy_delivered
        
        if vehicle and session.end_soc is not None:
            _LOGGER.info(
                "Ended charging session for %s: %.1f%% -> %.1f%%, delivered %.2f kWh",
                vehicle.name,
                session.start_soc,
                session.end_soc,
                session.energy_delivered or 0.0,
            )
        
        return session
    
    def get_active_session(self, vehicle_id: str) -> Optional[ChargingSession]:
        """Get active charging session for a vehicle."""
        session = self._sessions.get(vehicle_id)
        return session if session and session.active else None
    
    def get_all_active_sessions(self) -> List[ChargingSession]:
        """Get all active charging sessions."""
        return [s for s in self._sessions.values() if s.active]
    
    def calculate_required_energy(self, vehicle_id: str) -> float:
        """Calculate energy needed to reach target SOC."""
        vehicle = self.get_vehicle(vehicle_id)
        state = self.get_vehicle_state(vehicle_id)
        
        if not vehicle or not state:
            return 0.0
        
        soc_delta = max(0.0, state.target_soc - state.current_soc)
        return (soc_delta / 100.0) * vehicle.battery_kwh
    
    def calculate_charging_time(self, vehicle_id: str, amps: int) -> Optional[float]:
        """Calculate hours needed to charge at given amperage."""
        vehicle = self.get_vehicle(vehicle_id)
        required_kwh = self.calculate_required_energy(vehicle_id)
        
        if not vehicle or required_kwh <= 0:
            return 0.0
        
        # Power = Voltage * Current * Phases * Efficiency
        power_kw = (vehicle.voltage * amps * vehicle.phases * vehicle.charging_efficiency) / 1000.0
        
        if power_kw <= 0:
            return None
        
        return required_kwh / power_kw
    
    def get_vehicle_for_charger(self, charger_id: str) -> Optional[VehicleConfig]:
        """Get vehicle associated with a charger."""
        for vehicle in self._vehicles.values():
            if vehicle.charger_id == charger_id:
                return vehicle
        return None
    
    def associate_vehicle_charger(self, vehicle_id: str, charger_id: str) -> None:
        """Associate a vehicle with a charger."""
        vehicle = self.get_vehicle(vehicle_id)
        charger = self.get_charger(charger_id)
        
        if vehicle and charger:
            vehicle.charger_id = charger_id
            _LOGGER.info("Associated %s with charger %s", vehicle.name, charger.name)
        else:
            _LOGGER.error("Cannot associate: vehicle or charger not found")
