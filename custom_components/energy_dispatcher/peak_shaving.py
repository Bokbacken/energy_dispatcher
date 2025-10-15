"""Peak shaving logic for Energy Dispatcher.

This module implements peak shaving strategies to minimize peak power consumption
and reduce demand charges by intelligently discharging the battery when grid
import exceeds thresholds.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)


class PeakShaving:
    """
    Implements peak shaving logic to cap grid import power.
    
    Uses battery discharge to reduce peak grid imports, helping to minimize
    demand charges and reduce strain on the grid.
    """

    def __init__(
        self,
        min_shaving_duration_h: float = 0.5,
        min_shaving_power_w: float = 500.0,
    ):
        """
        Initialize peak shaving.
        
        Args:
            min_shaving_duration_h: Minimum duration battery can sustain discharge
            min_shaving_power_w: Minimum power worth shaving
        """
        self.min_duration = min_shaving_duration_h
        self.min_power = min_shaving_power_w

    def calculate_peak_shaving_action(
        self,
        current_grid_import_w: float,
        peak_threshold_w: float,
        battery_soc: float,
        battery_max_discharge_w: int,
        battery_reserve_soc: float,
        battery_capacity_kwh: float,
        solar_production_w: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Determine battery discharge needed to shave peaks.
        
        Strategy:
        1. Monitor grid import power
        2. If approaching or exceeding peak threshold, discharge battery
        3. Maintain reserve SOC for essential needs
        4. Prioritize solar usage first
        
        Args:
            current_grid_import_w: Current grid import power (W)
            peak_threshold_w: Peak power threshold to avoid exceeding (W)
            battery_soc: Current battery state of charge (%)
            battery_max_discharge_w: Maximum battery discharge power (W)
            battery_reserve_soc: Reserve SOC to maintain (%)
            battery_capacity_kwh: Total battery capacity (kWh)
            solar_production_w: Current solar production (W)
            
        Returns:
            Dictionary with discharge recommendation and details
        """
        # Calculate net demand after solar
        # Note: If solar is already offsetting grid import, it's included in grid reading
        net_demand_w = current_grid_import_w
        
        # Check if peak threshold exceeded
        if net_demand_w <= peak_threshold_w:
            return {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": "Within peak threshold",
            }
        
        # Check battery availability
        if battery_soc <= battery_reserve_soc:
            return {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": "Battery at reserve level, cannot shave peak",
            }
        
        # Calculate excess above threshold
        excess_w = net_demand_w - peak_threshold_w
        
        # Minimum power check
        if excess_w < self.min_power:
            return {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": f"Excess {excess_w:.0f}W below minimum {self.min_power:.0f}W",
            }
        
        # Calculate discharge power (limit to battery capability)
        discharge_w = min(excess_w, battery_max_discharge_w)
        
        # Calculate available battery energy above reserve
        available_battery_kwh = (
            (battery_soc - battery_reserve_soc) / 100.0
        ) * battery_capacity_kwh
        
        # Calculate discharge duration
        max_discharge_duration_h = available_battery_kwh / (discharge_w / 1000.0)
        
        # Check minimum duration
        if max_discharge_duration_h < self.min_duration:
            return {
                "discharge_battery": False,
                "discharge_power_w": 0,
                "duration_estimate_h": 0.0,
                "peak_reduction_w": 0,
                "reason": (
                    f"Insufficient battery capacity for meaningful peak shaving "
                    f"(can sustain only {max_discharge_duration_h:.1f}h)"
                ),
            }
        
        _LOGGER.info(
            "Peak shaving active: discharging %.0fW to cap grid import at %.0fW "
            "(current: %.0fW, can sustain %.1fh)",
            discharge_w,
            peak_threshold_w,
            net_demand_w,
            max_discharge_duration_h,
        )
        
        return {
            "discharge_battery": True,
            "discharge_power_w": int(discharge_w),
            "duration_estimate_h": round(max_discharge_duration_h, 2),
            "peak_reduction_w": int(discharge_w),
            "reason": (
                f"Shaving {discharge_w:.0f}W peak, can maintain for "
                f"{max_discharge_duration_h:.1f}h"
            ),
        }
