"""Appliance scheduling optimizer for Energy Dispatcher.

This module provides optimization logic for scheduling household appliances
(dishwasher, washing machine, water heater) based on:
- Electricity price forecasts
- Solar production forecasts
- Time constraints
- Battery state

The optimizer aims to minimize cost by scheduling appliances during cheap
periods or when solar production is high.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.util import dt as dt_util

from .models import PricePoint, ForecastPoint

_LOGGER = logging.getLogger(__name__)


class ApplianceOptimizer:
    """Optimizer for household appliance scheduling."""

    def optimize_schedule(
        self,
        appliance_name: str,
        power_w: float,
        duration_hours: float,
        prices: List[PricePoint],
        solar_forecast: Optional[List[ForecastPoint]] = None,
        earliest_start: Optional[datetime] = None,
        latest_end: Optional[datetime] = None,
        battery_soc: Optional[float] = None,
        battery_capacity_kwh: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Find optimal time to run an appliance.

        Args:
            appliance_name: Name of appliance (for logging/reporting)
            power_w: Appliance power consumption in watts
            duration_hours: Runtime duration in hours
            prices: List of price points (at least 24 hours recommended)
            solar_forecast: Optional solar production forecast
            earliest_start: Optional earliest acceptable start time
            latest_end: Optional latest acceptable end time
            battery_soc: Optional current battery state of charge (%)
            battery_capacity_kwh: Optional battery capacity in kWh

        Returns:
            Dictionary with:
                - optimal_start_time: Best time to start (datetime)
                - estimated_cost_sek: Cost estimate (SEK)
                - cost_savings_vs_now_sek: Savings vs running now (SEK)
                - reason: Explanation for the recommendation
                - price_at_optimal_time: Price at optimal time (SEK/kWh)
                - current_price: Current electricity price (SEK/kWh)
                - solar_available: Whether solar power is available at optimal time
                - alternative_times: List of other good times
                - confidence: Confidence level (low/medium/high)
        """
        if not prices:
            _LOGGER.warning("No price data available for %s optimization", appliance_name)
            return self._no_data_result()

        now = dt_util.now()
        
        # Ensure earliest_start and latest_end are timezone-aware if now is
        if now.tzinfo:
            if earliest_start and not earliest_start.tzinfo:
                earliest_start = earliest_start.replace(tzinfo=now.tzinfo)
            if latest_end and not latest_end.tzinfo:
                latest_end = latest_end.replace(tzinfo=now.tzinfo)
        else:
            # Make everything naive for consistency
            if earliest_start and earliest_start.tzinfo:
                earliest_start = earliest_start.replace(tzinfo=None)
            if latest_end and latest_end.tzinfo:
                latest_end = latest_end.replace(tzinfo=None)
        
        # Default time constraints: today from now until end of tomorrow
        if earliest_start is None:
            earliest_start = now
        if latest_end is None:
            latest_end = now + timedelta(hours=36)

        # Calculate energy consumption
        energy_kwh = (power_w / 1000.0) * duration_hours

        # Find all valid time windows
        valid_windows = self._find_valid_windows(
            prices=prices,
            earliest_start=earliest_start,
            latest_end=latest_end,
            duration_hours=duration_hours,
        )

        if not valid_windows:
            _LOGGER.warning(
                "No valid time windows found for %s between %s and %s",
                appliance_name,
                earliest_start,
                latest_end,
            )
            return self._no_window_result(earliest_start, latest_end)

        # Score each window
        scored_windows = []
        for window_start, window_prices in valid_windows:
            score = self._score_window(
                window_start=window_start,
                window_prices=window_prices,
                duration_hours=duration_hours,
                energy_kwh=energy_kwh,
                solar_forecast=solar_forecast,
            )
            scored_windows.append((window_start, score))

        # Sort by score (lower is better - represents cost)
        scored_windows.sort(key=lambda x: x[1]["total_cost_sek"])

        # Best window
        best_start, best_score = scored_windows[0]
        
        # Calculate cost if run now
        now_cost = self._calculate_cost_if_now(
            now=now,
            duration_hours=duration_hours,
            energy_kwh=energy_kwh,
            prices=prices,
            solar_forecast=solar_forecast,
        )

        # Build result
        result = {
            "optimal_start_time": best_start,
            "estimated_cost_sek": round(best_score["total_cost_sek"], 2),
            "cost_savings_vs_now_sek": round(now_cost - best_score["total_cost_sek"], 2),
            "reason": self._generate_reason(best_score, now, best_start),
            "price_at_optimal_time": round(best_score["avg_price_sek_per_kwh"], 2),
            "current_price": self._get_current_price(now, prices),
            "solar_available": best_score["solar_offset_kwh"] > 0,
            "alternative_times": self._format_alternatives(scored_windows[1:4]),
            "confidence": self._assess_confidence(prices, solar_forecast),
        }

        _LOGGER.info(
            "%s optimization: Start at %s, cost %.2f SEK, savings %.2f SEK",
            appliance_name.title(),
            best_start.strftime("%Y-%m-%d %H:%M"),
            result["estimated_cost_sek"],
            result["cost_savings_vs_now_sek"],
        )

        return result

    def _find_valid_windows(
        self,
        prices: List[PricePoint],
        earliest_start: datetime,
        latest_end: datetime,
        duration_hours: float,
    ) -> List[tuple[datetime, List[PricePoint]]]:
        """Find all valid time windows where appliance can run."""
        valid_windows = []
        duration_td = timedelta(hours=duration_hours)

        # Create a dict for quick price lookup (remove timezone for comparison)
        price_dict = {}
        for p in prices:
            key = p.time.replace(tzinfo=None) if p.time.tzinfo else p.time
            price_dict[key] = p

        # Normalize datetimes for comparison
        earliest = earliest_start.replace(tzinfo=None) if earliest_start.tzinfo else earliest_start
        latest = latest_end.replace(tzinfo=None) if latest_end.tzinfo else latest_end

        # Try each hour as potential start
        current = earliest.replace(minute=0, second=0, microsecond=0)
        while current <= latest - duration_td:
            # Check if we have prices for the entire window
            window_end = current + duration_td
            
            # Collect prices for this window
            window_prices = []
            check_time = current
            has_all_prices = True
            
            while check_time < window_end:
                if check_time in price_dict:
                    window_prices.append(price_dict[check_time])
                else:
                    has_all_prices = False
                    break
                check_time += timedelta(hours=1)

            if has_all_prices and window_prices:
                valid_windows.append((current, window_prices))

            current += timedelta(hours=1)

        return valid_windows

    def _score_window(
        self,
        window_start: datetime,
        window_prices: List[PricePoint],
        duration_hours: float,
        energy_kwh: float,
        solar_forecast: Optional[List[ForecastPoint]] = None,
    ) -> Dict[str, Any]:
        """Score a time window based on cost and solar availability."""
        # Calculate average price for window
        avg_price = sum(p.enriched_sek_per_kwh for p in window_prices) / len(window_prices)

        # Check solar availability
        solar_offset_kwh = 0.0
        if solar_forecast:
            solar_dict = {}
            for f in solar_forecast:
                key = f.time.replace(tzinfo=None) if f.time.tzinfo else f.time
                solar_dict[key] = f
            
            window_start_naive = window_start.replace(tzinfo=None) if window_start.tzinfo else window_start
            window_end = window_start_naive + timedelta(hours=duration_hours)
            
            check_time = window_start_naive
            total_solar_w = 0
            count = 0
            while check_time < window_end:
                if check_time in solar_dict:
                    total_solar_w += solar_dict[check_time].watts
                    count += 1
                check_time += timedelta(hours=1)
            
            if count > 0:
                avg_solar_w = total_solar_w / count
                # Estimate how much solar can offset (simplified)
                solar_offset_kwh = min(energy_kwh, (avg_solar_w / 1000.0) * duration_hours)

        # Calculate net cost (grid cost after solar offset)
        grid_energy_kwh = max(0, energy_kwh - solar_offset_kwh)
        total_cost_sek = grid_energy_kwh * avg_price

        return {
            "total_cost_sek": total_cost_sek,
            "avg_price_sek_per_kwh": avg_price,
            "solar_offset_kwh": solar_offset_kwh,
            "grid_energy_kwh": grid_energy_kwh,
        }

    def _calculate_cost_if_now(
        self,
        now: datetime,
        duration_hours: float,
        energy_kwh: float,
        prices: List[PricePoint],
        solar_forecast: Optional[List[ForecastPoint]] = None,
    ) -> float:
        """Calculate cost if appliance were run starting now."""
        # Find prices for the window starting now
        now_hour = now.replace(minute=0, second=0, microsecond=0, tzinfo=None)
        window_end = now_hour + timedelta(hours=duration_hours)
        
        price_dict = {}
        for p in prices:
            key = p.time.replace(tzinfo=None) if p.time.tzinfo else p.time
            price_dict[key] = p
        
        window_prices = []
        check_time = now_hour
        while check_time < window_end:
            if check_time in price_dict:
                window_prices.append(price_dict[check_time])
            check_time += timedelta(hours=1)

        if not window_prices:
            # No price data available, use current price as estimate
            current_price = self._get_current_price(now, prices)
            return energy_kwh * current_price

        # Score the window starting now
        score = self._score_window(
            window_start=now_hour,
            window_prices=window_prices,
            duration_hours=duration_hours,
            energy_kwh=energy_kwh,
            solar_forecast=solar_forecast,
        )
        
        return score["total_cost_sek"]

    def _get_current_price(self, now: datetime, prices: List[PricePoint]) -> float:
        """Get current electricity price."""
        now_hour = now.replace(minute=0, second=0, microsecond=0, tzinfo=None)
        
        for price in prices:
            price_time = price.time.replace(tzinfo=None) if price.time.tzinfo else price.time
            if price_time == now_hour:
                return price.enriched_sek_per_kwh
        
        # Fallback: return average price
        if prices:
            return sum(p.enriched_sek_per_kwh for p in prices) / len(prices)
        
        return 0.0

    def _generate_reason(
        self, 
        score: Dict[str, Any], 
        now: datetime, 
        optimal_start: datetime
    ) -> str:
        """Generate human-readable reason for the recommendation."""
        if score["solar_offset_kwh"] > 0.5:
            return "Solar production available during this time"
        
        # Ensure both datetimes are comparable (remove timezone info if needed)
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        optimal_naive = optimal_start.replace(tzinfo=None) if optimal_start.tzinfo else optimal_start
        time_diff = (optimal_naive - now_naive).total_seconds() / 3600
        
        if time_diff < 1:
            return "Best time to run is right now"
        elif time_diff < 4:
            return f"Low electricity price in {int(time_diff)} hours"
        elif optimal_start.hour < 6:
            return "Cheapest during night hours"
        elif 11 <= optimal_start.hour <= 15:
            return "Optimal during midday hours"
        else:
            return "Low electricity price period"

    def _format_alternatives(
        self, 
        alternatives: List[tuple[datetime, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Format alternative time windows."""
        result = []
        for start_time, score in alternatives[:3]:  # Max 3 alternatives
            result.append({
                "start_time": start_time.isoformat(),
                "estimated_cost_sek": round(score["total_cost_sek"], 2),
                "solar_available": score["solar_offset_kwh"] > 0,
            })
        return result

    def _assess_confidence(
        self,
        prices: List[PricePoint],
        solar_forecast: Optional[List[ForecastPoint]] = None,
    ) -> str:
        """Assess confidence level in the recommendation."""
        # High confidence: 24+ hours of price data, solar forecast available
        # Medium confidence: 24+ hours of price data, no solar
        # Low confidence: < 24 hours of price data
        
        if len(prices) >= 24:
            if solar_forecast and len(solar_forecast) >= 24:
                return "high"
            return "medium"
        return "low"

    def _no_data_result(self) -> Dict[str, Any]:
        """Return result when no data available."""
        now = dt_util.now()
        return {
            "optimal_start_time": now,
            "estimated_cost_sek": 0.0,
            "cost_savings_vs_now_sek": 0.0,
            "reason": "No price data available",
            "price_at_optimal_time": 0.0,
            "current_price": 0.0,
            "solar_available": False,
            "alternative_times": [],
            "confidence": "low",
        }

    def _no_window_result(
        self, 
        earliest_start: datetime, 
        latest_end: datetime
    ) -> Dict[str, Any]:
        """Return result when no valid window found."""
        return {
            "optimal_start_time": earliest_start,
            "estimated_cost_sek": 0.0,
            "cost_savings_vs_now_sek": 0.0,
            "reason": f"No valid time window between {earliest_start.strftime('%H:%M')} and {latest_end.strftime('%H:%M')}",
            "price_at_optimal_time": 0.0,
            "current_price": 0.0,
            "solar_available": False,
            "alternative_times": [],
            "confidence": "low",
        }
