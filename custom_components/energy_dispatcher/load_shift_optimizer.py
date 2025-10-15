"""Load shift optimizer for Energy Dispatcher.

This module identifies opportunities to shift flexible loads to cheaper time periods,
helping to minimize electricity costs while maintaining user convenience.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .models import PricePoint

_LOGGER = logging.getLogger(__name__)


class LoadShiftOptimizer:
    """
    Identifies and recommends load shifting opportunities.
    
    Analyzes current consumption patterns and price forecasts to suggest
    when flexible loads can be shifted to cheaper time periods.
    """

    def __init__(
        self,
        min_savings_threshold_sek: float = 0.5,
        min_flexible_load_w: float = 500.0,
    ):
        """
        Initialize the load shift optimizer.
        
        Args:
            min_savings_threshold_sek: Minimum price difference (SEK/kWh) to recommend a shift
            min_flexible_load_w: Minimum flexible load (W) to consider for shifting
        """
        self.min_savings_threshold = min_savings_threshold_sek
        self.min_flexible_load = min_flexible_load_w

    def recommend_load_shifts(
        self,
        current_time: datetime,
        baseline_load_w: float,
        current_consumption_w: float,
        prices: List[PricePoint],
        user_flexibility_hours: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Recommend load shifting opportunities.
        
        Strategy:
        1. Identify current flexible loads (consumption above baseline)
        2. Find cheaper time windows within flexibility period
        3. Calculate savings potential for each opportunity
        4. Prioritize by savings amount and user impact
        
        Args:
            current_time: Current timestamp
            baseline_load_w: Baseline always-on load in watts
            current_consumption_w: Current total consumption in watts
            prices: List of price points for the forecast period
            user_flexibility_hours: How many hours ahead user is willing to shift loads
            
        Returns:
            List of recommendations sorted by savings potential
        """
        recommendations = []
        
        # Identify flexible loads currently running
        flexible_load_w = current_consumption_w - baseline_load_w
        
        if flexible_load_w < self.min_flexible_load:
            _LOGGER.debug(
                "Flexible load %.0fW below threshold %.0fW, no shifts recommended",
                flexible_load_w,
                self.min_flexible_load,
            )
            return []
        
        # Get current price
        current_price = self._get_current_price(prices, current_time)
        if not current_price:
            _LOGGER.warning("No current price available for load shift analysis")
            return []
        
        # Get future prices within flexibility window
        future_prices = self._get_prices_in_window(
            prices, current_time, user_flexibility_hours
        )
        
        if not future_prices:
            _LOGGER.debug("No future prices available within flexibility window")
            return []
        
        # Calculate savings for each potential shift
        for future_price in future_prices:
            price_diff = (
                current_price.enriched_sek_per_kwh - future_price.enriched_sek_per_kwh
            )
            
            if price_diff >= self.min_savings_threshold:
                savings_per_hour = price_diff * (flexible_load_w / 1000.0)
                
                recommendations.append({
                    "shift_to": future_price.time,
                    "savings_per_hour_sek": round(savings_per_hour, 2),
                    "price_now": round(current_price.enriched_sek_per_kwh, 2),
                    "price_then": round(future_price.enriched_sek_per_kwh, 2),
                    "flexible_load_w": round(flexible_load_w, 0),
                    "user_impact": self._assess_user_impact(future_price.time),
                })
        
        # Sort by savings potential (highest first)
        recommendations.sort(key=lambda x: x["savings_per_hour_sek"], reverse=True)
        
        _LOGGER.debug(
            "Found %d load shift opportunities with flexible load %.0fW",
            len(recommendations),
            flexible_load_w,
        )
        
        return recommendations

    def _get_current_price(
        self, prices: List[PricePoint], current_time: datetime
    ) -> Optional[PricePoint]:
        """Get the price point for the current time."""
        for price in prices:
            # Price applies for the hour starting at price.time
            if price.time <= current_time < price.time + timedelta(hours=1):
                return price
        return None

    def _get_prices_in_window(
        self, prices: List[PricePoint], current_time: datetime, hours: int
    ) -> List[PricePoint]:
        """Get price points within the specified time window."""
        end_time = current_time + timedelta(hours=hours)
        return [
            p
            for p in prices
            if current_time < p.time <= end_time
        ]

    def _assess_user_impact(self, shift_time: datetime) -> str:
        """
        Assess user impact of shifting load to specified time.
        
        Night hours (0-6): Low impact
        Morning/evening (7-9, 17-22): Medium impact
        Daytime/late night (10-16, 23): Low impact
        """
        hour = shift_time.hour
        
        if hour in range(0, 7):  # Night
            return "low"
        elif hour in range(7, 10) or hour in range(17, 23):  # Peak hours
            return "medium"
        else:  # Midday
            return "low"
