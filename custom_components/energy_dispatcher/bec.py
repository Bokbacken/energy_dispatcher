"""Battery Energy Cost (BEC) module for tracking weighted average cost of energy."""
import logging
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "energy_dispatcher_bec"
STORAGE_VERSION = 1


class BatteryEnergyCost:
    """
    Tracks battery state of charge (SOC), energy content, and weighted average
    cost of energy (WACE) in the battery.
    
    The WACE represents the average cost per kWh of energy currently stored in
    the battery, calculated using a weighted average of all charging events.
    
    Features:
    - Persistent storage across Home Assistant restarts
    - Manual SOC override capability
    - Manual cost reset capability
    - Automatic WACE calculation during charge/discharge
    - Comprehensive error handling and logging
    
    Attributes:
        capacity_kwh: Maximum battery capacity in kWh
        energy_kwh: Current energy content in battery (kWh)
        wace: Weighted average cost of energy in battery (SEK/kWh)
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
        
        _LOGGER.info(
            "BatteryEnergyCost initialized with capacity=%.2f kWh",
            self.capacity_kwh
        )

    async def async_load(self) -> bool:
        """
        Load persisted battery state from storage.
        
        Returns:
            True if data was loaded successfully, False otherwise
        """
        try:
            data = await self.store.async_load()
            if data:
                self.energy_kwh = float(data.get("energy_kwh", 0.0))
                self.wace = float(data.get("wace", 0.0))
                _LOGGER.info(
                    "Loaded battery state: energy=%.3f kWh, wace=%.3f SEK/kWh",
                    self.energy_kwh, self.wace
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
        Persist current battery state to storage.
        
        Returns:
            True if data was saved successfully, False otherwise
        """
        try:
            await self.store.async_save({
                "energy_kwh": self.energy_kwh,
                "wace": self.wace
            })
            _LOGGER.debug(
                "Saved battery state: energy=%.3f kWh, wace=%.3f SEK/kWh",
                self.energy_kwh, self.wace
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

    def on_charge(self, delta_kwh: float, cost_sek_per_kwh: float) -> None:
        """
        Record a charging event and update the weighted average cost.
        
        When energy is added to the battery, the WACE is recalculated as:
        WACE_new = (energy_old * WACE_old + delta * cost) / energy_new
        
        Args:
            delta_kwh: Amount of energy charged (kWh, must be > 0)
            cost_sek_per_kwh: Cost of the charged energy (SEK/kWh)
            
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
            
        _LOGGER.info(
            "Charge event: +%.3f kWh @ %.3f SEK/kWh | "
            "Energy: %.3f -> %.3f kWh | WACE: %.3f -> %.3f SEK/kWh",
            delta_kwh, cost_sek_per_kwh,
            old_energy, self.energy_kwh,
            old_wace, self.wace
        )

    def on_discharge(self, delta_kwh: float) -> None:
        """
        Record a discharging event.
        
        When energy is removed from the battery, the energy content is reduced
        but the WACE of the remaining energy is unchanged (FIFO assumption).
        
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
        """
        old_wace = self.wace
        self.wace = 0.0
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
