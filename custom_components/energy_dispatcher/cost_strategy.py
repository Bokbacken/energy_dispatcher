"""Cost-based energy management strategy."""
from __future__ import annotations

import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from statistics import mean, stdev

from .models import PricePoint, CostThresholds, CostLevel

_LOGGER = logging.getLogger(__name__)


class CostStrategy:
    """
    Semi-intelligent cost-based energy management.
    
    Provides:
    - Dynamic cost classification (cheap/medium/high)
    - High-cost period prediction
    - Battery reserve recommendations
    - Charging window optimization
    """

    def __init__(self, thresholds: Optional[CostThresholds] = None):
        self.thresholds = thresholds or CostThresholds()
        self._price_history: List[PricePoint] = []
        
    def update_thresholds(self, cheap_max: Optional[float] = None, high_min: Optional[float] = None) -> None:
        """Update cost classification thresholds."""
        if cheap_max is not None:
            self.thresholds.cheap_max = cheap_max
        if high_min is not None:
            self.thresholds.high_min = high_min
        _LOGGER.info("Updated thresholds: cheap <= %.2f, high >= %.2f", 
                     self.thresholds.cheap_max, self.thresholds.high_min)
    
    def classify_price(self, price_sek_per_kwh: float) -> CostLevel:
        """Classify a price into cost level."""
        return self.thresholds.classify(price_sek_per_kwh)
    
    def update_price_history(self, prices: List[PricePoint]) -> None:
        """Update price history for analysis."""
        self._price_history = sorted(prices, key=lambda p: p.time)
    
    def get_dynamic_thresholds(self, prices: List[PricePoint]) -> CostThresholds:
        """
        Calculate dynamic thresholds based on price distribution.
        
        Uses 25th percentile for cheap and 75th percentile for high.
        """
        if not prices:
            return self.thresholds
        
        sorted_prices = sorted([p.enriched_sek_per_kwh for p in prices])
        n = len(sorted_prices)
        
        # 25th percentile (cheap threshold)
        p25_idx = int(n * 0.25)
        cheap_max = sorted_prices[p25_idx]
        
        # 75th percentile (high threshold)
        p75_idx = int(n * 0.75)
        high_min = sorted_prices[p75_idx]
        
        return CostThresholds(cheap_max=cheap_max, high_min=high_min)
    
    def predict_high_cost_windows(
        self,
        prices: List[PricePoint],
        now: datetime,
        horizon_hours: int = 24,
    ) -> List[tuple[datetime, datetime]]:
        """
        Predict high-cost time windows.
        
        Returns list of (start, end) datetime tuples for high-cost periods.
        """
        windows = []
        current_window_start = None
        
        end_time = now + timedelta(hours=horizon_hours)
        
        for price in prices:
            if price.time < now or price.time > end_time:
                continue
            
            level = self.classify_price(price.enriched_sek_per_kwh)
            
            if level == CostLevel.HIGH:
                if current_window_start is None:
                    current_window_start = price.time
            else:
                if current_window_start is not None:
                    windows.append((current_window_start, price.time))
                    current_window_start = None
        
        # Close any open window
        if current_window_start is not None:
            windows.append((current_window_start, end_time))
        
        return windows
    
    def calculate_battery_reserve(
        self,
        prices: List[PricePoint],
        now: datetime,
        battery_capacity_kwh: float,
        current_soc: float,
        horizon_hours: int = 24,
        weather_adjustment: Optional[Dict] = None,
        solar_forecast: Optional[List] = None,
    ) -> float:
        """
        Calculate recommended battery reserve level (SOC %).
        
        Reserves capacity for anticipated high-cost windows based on:
        - Duration of high-cost periods
        - Price differential
        - Current battery state
        - Weather-adjusted solar forecast (if available)
        - Solar production forecast during high-cost hours (if available)
        
        Solar Forecast Integration:
        When solar forecast is available, the reserve requirement is reduced by
        80% of expected solar production during high-cost hours. This conservative
        factor (0.8) accounts for forecast uncertainty and ensures adequate battery
        capacity remains available.
        
        Weather-Aware Adjustment:
        When weather optimization is enabled and solar forecast is adjusted downward
        (e.g., cloudy weather expected), the reserve is increased by 10-20% to
        compensate for reduced solar production. This ensures adequate battery
        capacity to cover load during high-cost periods when solar contribution
        is lower than normal.
        """
        high_cost_windows = self.predict_high_cost_windows(prices, now, horizon_hours)
        
        if not high_cost_windows:
            # No high-cost periods expected, no need to reserve
            return 0.0
        
        # Calculate total high-cost duration
        total_high_cost_hours = sum(
            (end - start).total_seconds() / 3600
            for start, end in high_cost_windows
        )
        
        # Estimate energy need during high-cost periods (assume 1 kW average load)
        # Reduced from 2 kW to be less conservative and allow better optimization
        estimated_load_kw = 1.0
        required_energy_kwh = total_high_cost_hours * estimated_load_kw
        
        # Solar forecast integration: reduce requirement by expected solar during high-cost hours
        if solar_forecast:
            solar_during_high_cost = self._calculate_solar_during_windows(
                solar_forecast, high_cost_windows
            )
            # Reduce requirement by 80% of expected solar (conservative factor)
            required_energy_kwh -= solar_during_high_cost * 0.8
            required_energy_kwh = max(0, required_energy_kwh)  # Can't be negative
            
            _LOGGER.debug(
                "Solar forecast integration: %.2f kWh expected during high-cost hours, "
                "reducing reserve requirement by %.2f kWh (80%% factor)",
                solar_during_high_cost,
                solar_during_high_cost * 0.8,
            )
        
        # Calculate required SOC to cover this
        required_soc = (required_energy_kwh / battery_capacity_kwh) * 100
        
        # Weather-aware adjustment: increase reserve if solar forecast is reduced
        if weather_adjustment:
            reduction_pct = weather_adjustment.get("reduction_percentage", 0.0)
            
            # If solar forecast is significantly reduced (>20%), increase reserve
            if reduction_pct > 20.0:
                # Scale the increase: 10-20% based on reduction severity
                # 20-40% reduction -> 10% increase
                # 40-60% reduction -> 15% increase
                # >60% reduction -> 20% increase
                if reduction_pct > 60:
                    increase_factor = 1.20
                elif reduction_pct > 40:
                    increase_factor = 1.15
                else:
                    increase_factor = 1.10
                
                required_soc = required_soc * increase_factor
                
                _LOGGER.debug(
                    "Weather-aware adjustment: solar forecast reduced by %.1f%%, "
                    "increasing battery reserve by %.0f%%",
                    reduction_pct,
                    (increase_factor - 1.0) * 100,
                )
        
        # Cap at 60% reserve (leave room for charging and better optimization)
        # Reduced from 80% to allow more aggressive charging during cheap hours
        reserve_soc = min(60.0, required_soc)
        
        _LOGGER.debug(
            "Battery reserve calculation: %.1f hours high-cost, %.1f kWh needed, %.1f%% SOC reserve",
            total_high_cost_hours,
            required_energy_kwh,
            reserve_soc,
        )
        
        return reserve_soc
    
    def _calculate_solar_during_windows(
        self,
        solar_forecast: List,
        windows: List[tuple[datetime, datetime]]
    ) -> float:
        """
        Calculate expected solar production during time windows.
        
        Args:
            solar_forecast: List of ForecastPoint objects with time and watts
            windows: List of (start, end) datetime tuples
        
        Returns:
            Total expected solar energy in kWh during the windows
        """
        total_solar_kwh = 0.0
        
        for start, end in windows:
            for point in solar_forecast:
                if start <= point.time < end:
                    # Convert watts to kWh (assuming 1 hour duration per point)
                    total_solar_kwh += point.watts / 1000.0
        
        return total_solar_kwh
    
    def should_charge_battery(
        self,
        current_price: float,
        current_soc: float,
        reserve_soc: float,
        solar_available_w: float = 0.0,
    ) -> bool:
        """
        Decide if battery should charge now.
        
        Considers:
        - Current price level
        - SOC vs reserve level
        - Solar availability
        """
        price_level = self.classify_price(current_price)
        
        # Always charge from excess solar (free energy)
        if solar_available_w > 500:
            return True
        
        # Don't charge if above reserve and not cheap
        if current_soc > reserve_soc and price_level != CostLevel.CHEAP:
            return False
        
        # Charge if below reserve and price is not high
        if current_soc < reserve_soc and price_level != CostLevel.HIGH:
            return True
        
        # Charge if price is cheap and not full
        if price_level == CostLevel.CHEAP and current_soc < 95.0:
            return True
        
        return False
    
    def should_discharge_battery(
        self,
        current_price: float,
        current_soc: float,
        reserve_soc: float,
        solar_deficit_w: float = 0.0,
    ) -> bool:
        """
        Decide if battery should discharge now.
        
        Considers:
        - Current price level
        - SOC vs reserve level
        - Solar deficit (negative = deficit)
        """
        price_level = self.classify_price(current_price)
        
        # Don't discharge if below reserve
        if current_soc <= reserve_soc:
            return False
        
        # Discharge if price is high and we have buffer above reserve
        if price_level == CostLevel.HIGH and current_soc > reserve_soc + 5:
            return True
        
        # Discharge if there's a solar deficit and we have spare capacity
        if solar_deficit_w < -1000 and current_soc > reserve_soc + 10:
            return True
        
        return False
    
    def optimize_ev_charging_windows(
        self,
        prices: List[PricePoint],
        now: datetime,
        required_energy_kwh: float,
        deadline: Optional[datetime] = None,
        charging_power_kw: float = 11.0,
    ) -> List[datetime]:
        """
        Optimize EV charging schedule.
        
        Returns list of hours when EV should charge to minimize cost
        while meeting deadline.
        """
        # Calculate hours needed
        hours_needed = required_energy_kwh / charging_power_kw if charging_power_kw > 0 else 0
        
        # If no energy needed, return empty list
        if hours_needed <= 0:
            return []
        
        # Filter prices from now until deadline
        if deadline:
            available_prices = [p for p in prices if now <= p.time < deadline]
        else:
            # Default 24 hour window
            end_time = now + timedelta(hours=24)
            available_prices = [p for p in prices if now <= p.time < end_time]
        
        if not available_prices:
            return []
        
        # Sort by price (cheapest first)
        sorted_prices = sorted(available_prices, key=lambda p: p.enriched_sek_per_kwh)
        
        # Select cheapest hours needed
        hours_to_select = min(int(hours_needed) + 1, len(sorted_prices))
        selected_hours = [p.time for p in sorted_prices[:hours_to_select]]
        
        # Sort chronologically for logging
        selected_hours.sort()
        
        if selected_hours:
            avg_price = mean([p.enriched_sek_per_kwh for p in sorted_prices[:hours_to_select]])
            _LOGGER.info(
                "Optimized EV charging: %d hours at avg %.2f SEK/kWh",
                len(selected_hours),
                avg_price,
            )
        
        return selected_hours
    
    def get_cost_summary(self, prices: List[PricePoint], now: datetime, horizon_hours: int = 24) -> Dict:
        """Get summary of cost classification for the horizon."""
        end_time = now + timedelta(hours=horizon_hours)
        relevant_prices = [p for p in prices if now <= p.time < end_time]
        
        if not relevant_prices:
            return {
                "total_hours": 0,
                "cheap_hours": 0,
                "medium_hours": 0,
                "high_hours": 0,
                "avg_price": 0.0,
                "min_price": 0.0,
                "max_price": 0.0,
            }
        
        cheap_count = sum(1 for p in relevant_prices if self.classify_price(p.enriched_sek_per_kwh) == CostLevel.CHEAP)
        high_count = sum(1 for p in relevant_prices if self.classify_price(p.enriched_sek_per_kwh) == CostLevel.HIGH)
        medium_count = len(relevant_prices) - cheap_count - high_count
        
        prices_values = [p.enriched_sek_per_kwh for p in relevant_prices]
        
        return {
            "total_hours": len(relevant_prices),
            "cheap_hours": cheap_count,
            "medium_hours": medium_count,
            "high_hours": high_count,
            "avg_price": mean(prices_values),
            "min_price": min(prices_values),
            "max_price": max(prices_values),
            "cheap_threshold": self.thresholds.cheap_max,
            "high_threshold": self.thresholds.high_min,
        }
