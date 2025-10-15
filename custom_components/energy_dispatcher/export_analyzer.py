"""Export profitability analyzer for Energy Dispatcher.

This module provides conservative export logic that defaults to "never export"
but detects truly profitable opportunities when spot prices are exceptional.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class ExportAnalyzer:
    """Analyze export profitability and recommend export decisions."""

    def __init__(
        self,
        export_mode: str = "never",
        min_export_price_sek_per_kwh: float = 3.0,
        battery_degradation_cost_per_cycle_sek: float = 0.50,
    ):
        """Initialize the export analyzer.
        
        Args:
            export_mode: Export mode setting ("never", "excess_solar_only", "peak_price_opportunistic")
            min_export_price_sek_per_kwh: Minimum price threshold for export consideration
            battery_degradation_cost_per_cycle_sek: Cost of battery degradation per cycle
        """
        self.export_mode = export_mode
        self.min_export_price = min_export_price_sek_per_kwh
        self.degradation_cost = battery_degradation_cost_per_cycle_sek
        _LOGGER.debug(
            "ExportAnalyzer initialized: mode=%s, min_price=%.2f, degradation=%.2f",
            export_mode, min_export_price_sek_per_kwh, battery_degradation_cost_per_cycle_sek
        )

    def should_export_energy(
        self,
        spot_price: float,
        purchase_price: float,
        export_price: float,
        battery_soc: float,
        battery_capacity_kwh: float,
        upcoming_high_cost_hours: int = 0,
        solar_excess_w: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Determine if exporting energy is worthwhile.
        
        Key principles:
        1. Default: DON'T EXPORT (selling price usually too low)
        2. Export only if:
           - Spot price is exceptionally high (e.g., >5 SEK/kWh)
           - Battery is full and solar still producing
           - No high-cost periods expected soon (no need to store)
           - Export price - battery degradation > threshold
        
        Args:
            spot_price: Current spot electricity price (SEK/kWh)
            purchase_price: Current purchase price including all fees (SEK/kWh)
            export_price: Price we get for exporting (SEK/kWh)
            battery_soc: Battery state of charge (0-100%)
            battery_capacity_kwh: Total battery capacity in kWh
            upcoming_high_cost_hours: Number of high-cost hours expected soon
            solar_excess_w: Excess solar power in watts (optional)
        
        Returns:
            Dictionary with export recommendation:
            {
                "should_export": bool,
                "export_power_w": int,
                "estimated_revenue_per_kwh": float,
                "export_price_sek_per_kwh": float,
                "opportunity_cost": float,
                "reason": str,
                "battery_soc": float,
                "solar_excess_w": float,
                "duration_estimate_h": float,
                "battery_degradation_cost": float,
                "net_revenue": float,
            }
        """
        # Default response structure
        default_response = {
            "should_export": False,
            "export_power_w": 0,
            "estimated_revenue_per_kwh": 0.0,
            "export_price_sek_per_kwh": export_price,
            "opportunity_cost": 0.0,
            "reason": "",
            "battery_soc": battery_soc,
            "solar_excess_w": solar_excess_w or 0.0,
            "duration_estimate_h": 0.0,
            "battery_degradation_cost": self.degradation_cost,
            "net_revenue": 0.0,
        }

        # Mode: never - always return False
        if self.export_mode == "never":
            default_response["reason"] = "Export disabled (mode: never)"
            _LOGGER.debug("Export disabled by mode: never")
            return default_response

        # Check if export price is too low
        if export_price < 2.0:
            default_response["reason"] = f"Export price too low ({export_price:.2f} < 2.00 SEK/kWh)"
            _LOGGER.debug("Export price too low: %.2f SEK/kWh", export_price)
            return default_response

        # Mode: excess_solar_only - only export when battery is full and solar excess exists
        if self.export_mode == "excess_solar_only":
            if battery_soc >= 95 and solar_excess_w and solar_excess_w > 1000:
                # Battery full, excess solar - export to avoid waste
                duration_h = 1.0  # Estimate 1 hour of export
                revenue = (solar_excess_w / 1000) * export_price * duration_h
                net_revenue = revenue - self.degradation_cost
                
                response = default_response.copy()
                response.update({
                    "should_export": True,
                    "export_power_w": int(solar_excess_w),
                    "estimated_revenue_per_kwh": export_price,
                    "opportunity_cost": 0.0,  # Would be wasted otherwise
                    "reason": f"Battery full ({battery_soc:.0f}%), excess solar {solar_excess_w:.0f}W would be wasted",
                    "duration_estimate_h": duration_h,
                    "net_revenue": round(net_revenue, 2),
                })
                _LOGGER.info(
                    "Export recommended (excess solar): SOC=%.1f%%, excess=%.0fW, export_price=%.2f",
                    battery_soc, solar_excess_w, export_price
                )
                return response
            else:
                default_response["reason"] = "No excess solar or battery not full (mode: excess_solar_only)"
                return default_response

        # Mode: peak_price_opportunistic - export during exceptionally high prices
        if self.export_mode == "peak_price_opportunistic":
            # Check if spot price is exceptionally high (>5 SEK/kWh)
            if export_price > 5.0 and battery_soc > 80:
                # High price and sufficient battery - opportunistic export
                max_export_power = 5000  # Max export rate in watts
                duration_h = 1.0  # Estimate 1 hour of high prices
                revenue = (max_export_power / 1000) * export_price * duration_h
                
                # Calculate opportunity cost: value of storing vs selling
                # If upcoming high cost hours, storing is valuable
                if upcoming_high_cost_hours > 0:
                    opportunity_cost = (max_export_power / 1000) * purchase_price * duration_h
                else:
                    opportunity_cost = 0.0
                
                net_revenue = revenue - self.degradation_cost - opportunity_cost
                
                # Only export if net revenue is positive
                if net_revenue > 0:
                    response = default_response.copy()
                    response.update({
                        "should_export": True,
                        "export_power_w": max_export_power,
                        "estimated_revenue_per_kwh": export_price,
                        "opportunity_cost": round(opportunity_cost, 2),
                        "reason": f"Exceptionally high export price ({export_price:.2f} SEK/kWh)",
                        "duration_estimate_h": duration_h,
                        "net_revenue": round(net_revenue, 2),
                    })
                    _LOGGER.info(
                        "Export recommended (high price): SOC=%.1f%%, export_price=%.2f, net_revenue=%.2f",
                        battery_soc, export_price, net_revenue
                    )
                    return response
                else:
                    default_response["reason"] = (
                        f"High export price ({export_price:.2f} SEK/kWh) but opportunity cost too high"
                    )
                    return default_response
            
            # Also check for excess solar scenario in this mode
            if battery_soc >= 95 and solar_excess_w and solar_excess_w > 1000:
                duration_h = 1.0
                revenue = (solar_excess_w / 1000) * export_price * duration_h
                net_revenue = revenue - self.degradation_cost
                
                response = default_response.copy()
                response.update({
                    "should_export": True,
                    "export_power_w": int(solar_excess_w),
                    "estimated_revenue_per_kwh": export_price,
                    "opportunity_cost": 0.0,
                    "reason": f"Battery full ({battery_soc:.0f}%), excess solar {solar_excess_w:.0f}W",
                    "duration_estimate_h": duration_h,
                    "net_revenue": round(net_revenue, 2),
                })
                _LOGGER.info(
                    "Export recommended (excess solar): SOC=%.1f%%, excess=%.0fW",
                    battery_soc, solar_excess_w
                )
                return response
            
            # Check if price meets minimum threshold
            if export_price >= self.min_export_price and battery_soc > 80:
                default_response["reason"] = (
                    f"Price {export_price:.2f} meets minimum {self.min_export_price:.2f} but not exceptional enough"
                )
                return default_response
            
            default_response["reason"] = (
                f"Export price {export_price:.2f} below threshold or battery SOC {battery_soc:.0f}% too low"
            )
            return default_response

        # Unknown mode - default to not exporting
        default_response["reason"] = f"Unknown export mode: {self.export_mode}"
        _LOGGER.warning("Unknown export mode: %s", self.export_mode)
        return default_response

    def update_settings(
        self,
        export_mode: Optional[str] = None,
        min_export_price_sek_per_kwh: Optional[float] = None,
        battery_degradation_cost_per_cycle_sek: Optional[float] = None,
    ) -> None:
        """Update analyzer settings.
        
        Args:
            export_mode: New export mode (if provided)
            min_export_price_sek_per_kwh: New minimum export price (if provided)
            battery_degradation_cost_per_cycle_sek: New degradation cost (if provided)
        """
        if export_mode is not None:
            self.export_mode = export_mode
            _LOGGER.info("Export mode updated to: %s", export_mode)
        
        if min_export_price_sek_per_kwh is not None:
            self.min_export_price = min_export_price_sek_per_kwh
            _LOGGER.info("Minimum export price updated to: %.2f SEK/kWh", min_export_price_sek_per_kwh)
        
        if battery_degradation_cost_per_cycle_sek is not None:
            self.degradation_cost = battery_degradation_cost_per_cycle_sek
            _LOGGER.info("Battery degradation cost updated to: %.2f SEK", battery_degradation_cost_per_cycle_sek)
