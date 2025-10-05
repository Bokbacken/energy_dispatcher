"""Battery Energy Cost (BEC) module for tracking weighted average cost of energy."""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "energy_dispatcher_bec"
STORAGE_VERSION = 2  # Incremented for historical data support


class BatteryEnergyCost:
    """
    Tracks battery state of charge (SOC), energy content, and weighted average
    cost of energy (WACE) in the battery with historical data storage.
    
    The WACE represents the average cost per kWh of energy currently stored in
    the battery, calculated using a weighted average of all charging events.
    
    Features:
    - Persistent storage across Home Assistant restarts
    - Historical time-series data for charging events (15-min intervals)
    - Manual SOC override capability
    - Manual cost reset capability
    - Automatic WACE calculation during charge/discharge
    - Comprehensive error handling and logging
    - Ability to recalculate WACE from historical data
    
    Attributes:
        capacity_kwh: Maximum battery capacity in kWh
        energy_kwh: Current energy content in battery (kWh)
        wace: Weighted average cost of energy in battery (SEK/kWh)
        charge_history: List of historical charging events with timestamps
    """

    def __init__(self, hass: HomeAssistant, capacity_kwh: float):
        """
        Initialize the Battery Energy Cost tracker.
        
        Args:
            hass: Home Assistant instance
            capacity_kwh: Maximum battery capacity in kWh (must be > 0)
            
        Raises:
            ValueError: If capacity_kwh is not positive
        """
        if capacity_kwh <= 0:
            raise ValueError(f"Battery capacity must be positive, got {capacity_kwh}")
            
        self.hass = hass
        self.capacity_kwh = float(capacity_kwh)
        self.store = Store(hass, STORAGE_VERSION, f".storage/{STORAGE_KEY}")
        self.energy_kwh = 0.0  # Estimated energy currently in battery
        self.wace = 0.0  # Weighted Average Cost of Energy (SEK/kWh)
        self.charge_history: List[Dict[str, Any]] = []  # Historical charging events
        
        _LOGGER.info(
            "BatteryEnergyCost initialized with capacity=%.2f kWh",
            self.capacity_kwh
        )

    async def async_load(self) -> bool:
        """
        Load persisted battery state from storage.
        Handles migration from version 1 to version 2.
        
        Returns:
            True if data was loaded successfully, False otherwise
        """
        try:
            data = await self.store.async_load()
            if data:
                # Load current state
                self.energy_kwh = float(data.get("energy_kwh", 0.0))
                self.wace = float(data.get("wace", 0.0))
                
                # Load historical data (version 2+)
                self.charge_history = data.get("charge_history", [])
                
                # If no history exists but we have energy/wace, create initial record
                # This handles migration from version 1
                if not self.charge_history and (self.energy_kwh > 0 or self.wace > 0):
                    _LOGGER.info("Migrating from storage version 1 to version 2")
                    # Create synthetic historical record for existing state
                    self.charge_history = [{
                        "timestamp": datetime.now().isoformat(),
                        "energy_kwh": self.energy_kwh,
                        "cost_sek_per_kwh": self.wace,
                        "soc_percent": self.get_soc(),
                        "source": "migration",
                        "event_type": "initial"
                    }]
                
                _LOGGER.info(
                    "Loaded battery state: energy=%.3f kWh, wace=%.3f SEK/kWh, history_records=%d",
                    self.energy_kwh, self.wace, len(self.charge_history)
                )
                return True
            else:
                _LOGGER.debug("No persisted battery state found, using defaults")
                return False
        except Exception as exc:
            _LOGGER.error("Failed to load battery state: %s", exc)
            return False

    async def async_save(self) -> bool:
        """
        Persist current battery state and historical data to storage.
        
        Returns:
            True if data was saved successfully, False otherwise
        """
        try:
            await self.store.async_save({
                "energy_kwh": self.energy_kwh,
                "wace": self.wace,
                "charge_history": self.charge_history
            })
            _LOGGER.debug(
                "Saved battery state: energy=%.3f kWh, wace=%.3f SEK/kWh, history_records=%d",
                self.energy_kwh, self.wace, len(self.charge_history)
            )
            return True
        except Exception as exc:
            _LOGGER.error("Failed to save battery state: %s", exc)
            return False

    def set_soc(self, soc_percent: float) -> None:
        """
        Manually set the battery state of charge (SOC).
        
        This method allows manual override of the battery's energy content based
        on a SOC percentage. The WACE is preserved during this operation.
        
        Args:
            soc_percent: State of charge as a percentage (0-100)
            
        Note:
            Values outside 0-100 are automatically clamped to valid range
        """
        # Clamp SOC to valid range
        soc_clamped = max(0.0, min(100.0, float(soc_percent)))
        old_energy = self.energy_kwh
        self.energy_kwh = (soc_clamped / 100.0) * self.capacity_kwh
        
        _LOGGER.info(
            "Manual SOC set: %.1f%% (%.3f kWh -> %.3f kWh), WACE unchanged at %.3f SEK/kWh",
            soc_clamped, old_energy, self.energy_kwh, self.wace
        )

    def on_charge(self, delta_kwh: float, cost_sek_per_kwh: float, source: str = "grid") -> None:
        """
        Record a charging event and update the weighted average cost.
        
        When energy is added to the battery, the WACE is recalculated as:
        WACE_new = (energy_old * WACE_old + delta * cost) / energy_new
        
        Historical data is stored for each charging event with timestamp,
        allowing recalculation of WACE at any time.
        
        Args:
            delta_kwh: Amount of energy charged (kWh, must be > 0)
            cost_sek_per_kwh: Cost of the charged energy (SEK/kWh)
            source: Source of energy ("grid" or "solar"), default "grid"
            
        Note:
            Non-positive delta_kwh values are ignored with a warning
        """
        if delta_kwh <= 0:
            _LOGGER.debug("Ignoring non-positive charge delta: %.3f kWh", delta_kwh)
            return
            
        old_energy = self.energy_kwh
        old_wace = self.wace
        
        # Calculate weighted average
        total_cost = self.energy_kwh * self.wace + delta_kwh * cost_sek_per_kwh
        self.energy_kwh += delta_kwh
        
        # Cap at capacity
        if self.energy_kwh > self.capacity_kwh:
            _LOGGER.warning(
                "Battery energy %.3f kWh exceeds capacity %.3f kWh, capping",
                self.energy_kwh, self.capacity_kwh
            )
            self.energy_kwh = self.capacity_kwh
        
        if self.energy_kwh > 0:
            self.wace = total_cost / self.energy_kwh
        
        # Store historical charging event
        event = {
            "timestamp": datetime.now().isoformat(),
            "energy_kwh": delta_kwh,
            "cost_sek_per_kwh": cost_sek_per_kwh,
            "soc_percent": self.get_soc(),
            "source": source,
            "event_type": "charge",
            "total_energy_after": self.energy_kwh,
            "wace_after": self.wace
        }
        self.charge_history.append(event)
        
        # Keep only last 30 days of history (2880 15-minute intervals)
        if len(self.charge_history) > 2880:
            self.charge_history = self.charge_history[-2880:]
            
        _LOGGER.info(
            "Charge event: +%.3f kWh @ %.3f SEK/kWh from %s | "
            "Energy: %.3f -> %.3f kWh | WACE: %.3f -> %.3f SEK/kWh",
            delta_kwh, cost_sek_per_kwh, source,
            old_energy, self.energy_kwh,
            old_wace, self.wace
        )

    def on_discharge(self, delta_kwh: float) -> None:
        """
        Record a discharging event.
        
        When energy is removed from the battery, the energy content is reduced
        but the WACE of the remaining energy is unchanged (FIFO assumption).
        
        Historical data is stored for tracking purposes.
        
        Args:
            delta_kwh: Amount of energy discharged (kWh, must be > 0)
            
        Note:
            Non-positive delta_kwh values are ignored with a warning
        """
        if delta_kwh <= 0:
            _LOGGER.debug("Ignoring non-positive discharge delta: %.3f kWh", delta_kwh)
            return
            
        old_energy = self.energy_kwh
        self.energy_kwh = max(0.0, self.energy_kwh - delta_kwh)
        
        # Store historical discharge event
        event = {
            "timestamp": datetime.now().isoformat(),
            "energy_kwh": -delta_kwh,  # Negative for discharge
            "cost_sek_per_kwh": 0.0,  # No cost for discharge
            "soc_percent": self.get_soc(),
            "source": "discharge",
            "event_type": "discharge",
            "total_energy_after": self.energy_kwh,
            "wace_after": self.wace
        }
        self.charge_history.append(event)
        
        # Keep only last 30 days of history
        if len(self.charge_history) > 2880:
            self.charge_history = self.charge_history[-2880:]
        
        _LOGGER.info(
            "Discharge event: -%.3f kWh | Energy: %.3f -> %.3f kWh | WACE unchanged at %.3f SEK/kWh",
            delta_kwh, old_energy, self.energy_kwh, self.wace
        )

    def reset_cost(self) -> None:
        """
        Reset the weighted average cost to zero.
        
        This manual override clears the cost tracking while preserving the
        current energy content. Useful when you want to restart cost tracking
        or after significant pricing changes.
        
        Historical data is preserved for auditing purposes.
        """
        old_wace = self.wace
        self.wace = 0.0
        
        # Store reset event in history
        event = {
            "timestamp": datetime.now().isoformat(),
            "energy_kwh": 0.0,
            "cost_sek_per_kwh": 0.0,
            "soc_percent": self.get_soc(),
            "source": "manual",
            "event_type": "reset_cost",
            "total_energy_after": self.energy_kwh,
            "wace_after": self.wace
        }
        self.charge_history.append(event)
        
        _LOGGER.info(
            "Manual cost reset: WACE %.3f -> 0.0 SEK/kWh (energy unchanged at %.3f kWh)",
            old_wace, self.energy_kwh
        )

    def get_soc(self) -> float:
        """
        Get the current state of charge as a percentage.
        
        Returns:
            Current SOC as percentage (0-100)
        """
        if self.capacity_kwh <= 0:
            return 0.0
        return (self.energy_kwh / self.capacity_kwh) * 100.0

    def get_total_cost(self) -> float:
        """
        Calculate the total cost of energy currently in the battery.
        
        Returns:
            Total cost in SEK
        """
        return self.energy_kwh * self.wace
    
    def recalculate_wace_from_history(self) -> bool:
        """
        Recalculate WACE from historical charging events.
        
        This method reconstructs the current WACE by replaying all charge
        events from history. Useful for verification or after data corrections.
        
        Returns:
            True if recalculation was successful, False if insufficient history
        """
        if not self.charge_history:
            _LOGGER.warning("Cannot recalculate WACE: no historical data available")
            return False
        
        # Start from zero
        temp_energy = 0.0
        temp_wace = 0.0
        
        # Replay all charge events
        for event in self.charge_history:
            if event.get("event_type") == "charge":
                delta_kwh = event.get("energy_kwh", 0.0)
                cost = event.get("cost_sek_per_kwh", 0.0)
                
                if delta_kwh > 0:
                    total_cost = temp_energy * temp_wace + delta_kwh * cost
                    temp_energy += delta_kwh
                    if temp_energy > 0:
                        temp_wace = total_cost / temp_energy
            
            elif event.get("event_type") == "discharge":
                delta_kwh = abs(event.get("energy_kwh", 0.0))
                temp_energy = max(0.0, temp_energy - delta_kwh)
            
            elif event.get("event_type") == "reset_cost":
                temp_wace = 0.0
        
        old_wace = self.wace
        self.wace = temp_wace
        self.energy_kwh = temp_energy
        
        _LOGGER.info(
            "Recalculated WACE from %d historical events: %.3f -> %.3f SEK/kWh",
            len(self.charge_history), old_wace, self.wace
        )
        return True
    
    def get_charge_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get historical charging events.
        
        Args:
            limit: Maximum number of recent events to return (None for all)
            
        Returns:
            List of historical event dictionaries
        """
        if limit is None:
            return self.charge_history.copy()
        return self.charge_history[-limit:] if limit > 0 else []
    
    def get_history_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics from historical data.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.charge_history:
            return {
                "total_events": 0,
                "charge_events": 0,
                "discharge_events": 0,
                "total_charged_kwh": 0.0,
                "total_discharged_kwh": 0.0,
                "avg_charge_cost": 0.0,
                "oldest_event": None,
                "newest_event": None
            }
        
        charge_events = [e for e in self.charge_history if e.get("event_type") == "charge"]
        discharge_events = [e for e in self.charge_history if e.get("event_type") == "discharge"]
        
        total_charged = sum(e.get("energy_kwh", 0.0) for e in charge_events)
        total_discharged = sum(abs(e.get("energy_kwh", 0.0)) for e in discharge_events)
        
        # Calculate average charge cost
        charged_costs = [e.get("cost_sek_per_kwh", 0.0) * e.get("energy_kwh", 0.0) for e in charge_events]
        avg_cost = sum(charged_costs) / total_charged if total_charged > 0 else 0.0
        
        return {
            "total_events": len(self.charge_history),
            "charge_events": len(charge_events),
            "discharge_events": len(discharge_events),
            "total_charged_kwh": total_charged,
            "total_discharged_kwh": total_discharged,
            "avg_charge_cost": avg_cost,
            "oldest_event": self.charge_history[0].get("timestamp") if self.charge_history else None,
            "newest_event": self.charge_history[-1].get("timestamp") if self.charge_history else None
        }
