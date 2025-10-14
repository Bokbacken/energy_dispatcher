"""Weather-Aware Solar Optimization.

This module adjusts solar forecasts based on weather conditions (cloud cover,
temperature) to improve battery reserve calculations and planning accuracy.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

from homeassistant.core import HomeAssistant

from .models import ForecastPoint

_LOGGER = logging.getLogger(__name__)


@dataclass
class WeatherPoint:
    """Weather data point for a specific time."""
    time: datetime
    cloud_coverage_pct: Optional[float] = None  # 0-100%
    temperature_c: Optional[float] = None  # Celsius
    condition: Optional[str] = None  # Weather condition string


@dataclass
class AdjustedForecastPoint:
    """Solar forecast point with weather adjustments."""
    time: datetime
    base_watts: float
    adjusted_watts: float
    adjustment_factor: float
    confidence_level: str  # "high", "medium", "low"
    limiting_factor: str  # "clear", "cloud_cover", "temperature", "multiple"


class WeatherOptimizer:
    """
    Adjusts solar forecasts based on weather conditions.
    
    Cloud cover adjustments:
    - Clear (0-10%): 100% of base forecast
    - Partly cloudy (11-50%): 70-80% of base forecast
    - Cloudy (51-80%): 40-60% of base forecast
    - Overcast (81-100%): 20-30% of base forecast
    
    Temperature adjustments:
    - Panel efficiency reduction: 0.4-0.5% per °C above 25°C
    - Below 25°C: No adjustment (baseline efficiency)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        temp_coeff_pct_per_c: float = -0.45,  # -0.4 to -0.5% per °C
        reference_temp_c: float = 25.0,
    ):
        """
        Initialize WeatherOptimizer.
        
        Args:
            hass: Home Assistant instance
            temp_coeff_pct_per_c: Temperature coefficient (% per °C above reference)
            reference_temp_c: Reference temperature for panel efficiency (°C)
        """
        self.hass = hass
        self.temp_coeff = temp_coeff_pct_per_c / 100.0  # Convert to decimal
        self.reference_temp = reference_temp_c

    def adjust_solar_forecast_for_weather(
        self,
        base_solar_forecast: List[ForecastPoint],
        weather_forecast: List[WeatherPoint],
        historical_adjustment_factors: Optional[Dict[str, float]] = None,
    ) -> List[AdjustedForecastPoint]:
        """
        Adjust solar forecast based on weather conditions.
        
        Args:
            base_solar_forecast: Base solar production forecast
            weather_forecast: Weather forecast data points
            historical_adjustment_factors: Optional historical calibration factors
            
        Returns:
            List of adjusted forecast points with confidence intervals
        """
        if not base_solar_forecast:
            return []
        
        # Create weather lookup by time (rounded to hour for matching)
        weather_by_hour: Dict[datetime, WeatherPoint] = {}
        for wp in weather_forecast:
            hour_key = wp.time.replace(minute=0, second=0, microsecond=0)
            weather_by_hour[hour_key] = wp
        
        adjusted_points = []
        
        for forecast_point in base_solar_forecast:
            # Match weather data by hour
            hour_key = forecast_point.time.replace(minute=0, second=0, microsecond=0)
            weather = weather_by_hour.get(hour_key)
            
            if weather is None:
                # No weather data, use base forecast with low confidence
                adjusted_points.append(
                    AdjustedForecastPoint(
                        time=forecast_point.time,
                        base_watts=forecast_point.watts,
                        adjusted_watts=forecast_point.watts,
                        adjustment_factor=1.0,
                        confidence_level="low",
                        limiting_factor="no_weather_data",
                    )
                )
                continue
            
            # Calculate adjustments
            cloud_factor, cloud_confidence = self._calculate_cloud_adjustment(
                weather.cloud_coverage_pct
            )
            temp_factor = self._calculate_temperature_adjustment(
                weather.temperature_c
            )
            
            # Combine factors
            combined_factor = cloud_factor * temp_factor
            
            # Apply historical calibration if available
            if historical_adjustment_factors:
                condition_key = self._get_condition_key(weather.cloud_coverage_pct)
                historical_factor = historical_adjustment_factors.get(condition_key, 1.0)
                combined_factor *= historical_factor
            
            # Calculate adjusted watts
            adjusted_watts = forecast_point.watts * combined_factor
            
            # Determine limiting factor and confidence
            limiting_factor = self._determine_limiting_factor(
                weather.cloud_coverage_pct, weather.temperature_c
            )
            confidence = self._determine_confidence(
                weather.cloud_coverage_pct, cloud_confidence
            )
            
            adjusted_points.append(
                AdjustedForecastPoint(
                    time=forecast_point.time,
                    base_watts=forecast_point.watts,
                    adjusted_watts=adjusted_watts,
                    adjustment_factor=combined_factor,
                    confidence_level=confidence,
                    limiting_factor=limiting_factor,
                )
            )
        
        _LOGGER.debug(
            "Adjusted %d forecast points with weather data",
            len(adjusted_points)
        )
        
        return adjusted_points

    def _calculate_cloud_adjustment(
        self, cloud_coverage_pct: Optional[float]
    ) -> Tuple[float, str]:
        """
        Calculate cloud cover adjustment factor.
        
        Returns:
            Tuple of (adjustment_factor, confidence_level)
        """
        if cloud_coverage_pct is None:
            return 1.0, "low"
        
        # Clamp to valid range
        cloud_pct = max(0.0, min(100.0, cloud_coverage_pct))
        
        if cloud_pct <= 10:
            # Clear sky: 100% of base forecast
            return 1.0, "high"
        elif cloud_pct <= 50:
            # Partly cloudy: 70-80% linear interpolation
            # At 10%: 1.0, at 50%: 0.75 (midpoint of 70-80%)
            factor = 1.0 - (cloud_pct - 10) / 40 * 0.25
            return factor, "high"
        elif cloud_pct <= 80:
            # Cloudy: 40-60% linear interpolation
            # At 50%: 0.75, at 80%: 0.50 (midpoint of 40-60%)
            factor = 0.75 - (cloud_pct - 50) / 30 * 0.25
            return factor, "medium"
        else:
            # Overcast: 20-30% linear interpolation
            # At 80%: 0.50, at 100%: 0.25 (midpoint of 20-30%)
            factor = 0.50 - (cloud_pct - 80) / 20 * 0.25
            return factor, "medium"

    def _calculate_temperature_adjustment(
        self, temperature_c: Optional[float]
    ) -> float:
        """
        Calculate temperature adjustment factor.
        
        Solar panels lose efficiency at high temperatures.
        Returns adjustment factor (1.0 = no adjustment, <1.0 = reduced efficiency).
        """
        if temperature_c is None:
            return 1.0
        
        # Only adjust for temperatures above reference
        if temperature_c <= self.reference_temp:
            return 1.0
        
        # Calculate efficiency loss
        temp_diff = temperature_c - self.reference_temp
        efficiency_loss = temp_diff * self.temp_coeff  # Negative value
        
        # Convert to factor (e.g., -2% loss = 0.98 factor)
        factor = 1.0 + efficiency_loss
        
        # Clamp to reasonable range (don't go below 0.5)
        return max(0.5, factor)

    def _determine_limiting_factor(
        self, cloud_coverage_pct: Optional[float], temperature_c: Optional[float]
    ) -> str:
        """Determine the primary limiting factor for solar production."""
        factors = []
        
        if cloud_coverage_pct is not None and cloud_coverage_pct > 10:
            factors.append("cloud_cover")
        
        if temperature_c is not None and temperature_c > self.reference_temp + 5:
            factors.append("temperature")
        
        if not factors:
            return "clear"
        elif len(factors) == 1:
            return factors[0]
        else:
            return "multiple"

    def _determine_confidence(
        self, cloud_coverage_pct: Optional[float], cloud_confidence: str
    ) -> str:
        """Determine overall confidence level for the adjustment."""
        if cloud_coverage_pct is None:
            return "low"
        
        # High confidence when weather data is available and cloud confidence is high
        if cloud_confidence == "high":
            return "high"
        elif cloud_confidence == "medium":
            return "medium"
        else:
            return "low"

    def _get_condition_key(self, cloud_coverage_pct: Optional[float]) -> str:
        """Get condition key for historical lookup."""
        if cloud_coverage_pct is None:
            return "unknown"
        
        if cloud_coverage_pct <= 10:
            return "clear"
        elif cloud_coverage_pct <= 50:
            return "partly_cloudy"
        elif cloud_coverage_pct <= 80:
            return "cloudy"
        else:
            return "overcast"

    def extract_weather_forecast_from_entity(
        self, weather_entity_id: str, hours: int = 24
    ) -> List[WeatherPoint]:
        """
        Extract weather forecast from Home Assistant weather entity.
        
        Args:
            weather_entity_id: Entity ID of weather integration
            hours: Number of hours to extract
            
        Returns:
            List of WeatherPoint objects
        """
        if not weather_entity_id:
            return []
        
        state = self.hass.states.get(weather_entity_id)
        if not state:
            _LOGGER.warning("Weather entity %s not found", weather_entity_id)
            return []
        
        weather_points = []
        
        # Try to get forecast attribute
        forecast_data = state.attributes.get("forecast", [])
        
        for entry in forecast_data[:hours]:
            # Extract time
            time_str = entry.get("datetime")
            if not time_str:
                continue
            
            try:
                # Parse datetime
                if isinstance(time_str, str):
                    time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                else:
                    time = time_str
                
                # Extract cloud coverage (various attribute names)
                cloud_pct = None
                for key in ["cloudiness", "cloud_coverage", "cloud_cover", "cloud"]:
                    if key in entry:
                        try:
                            cloud_pct = float(entry[key])
                            break
                        except (ValueError, TypeError):
                            continue
                
                # Extract temperature
                temp_c = entry.get("temperature")
                if temp_c is not None:
                    try:
                        temp_c = float(temp_c)
                    except (ValueError, TypeError):
                        temp_c = None
                
                # Extract condition
                condition = entry.get("condition")
                
                weather_points.append(
                    WeatherPoint(
                        time=time,
                        cloud_coverage_pct=cloud_pct,
                        temperature_c=temp_c,
                        condition=condition,
                    )
                )
            except (ValueError, AttributeError) as e:
                _LOGGER.debug("Failed to parse weather entry: %s", e)
                continue
        
        _LOGGER.debug(
            "Extracted %d weather points from %s",
            len(weather_points),
            weather_entity_id
        )
        
        return weather_points

    def calculate_forecast_adjustment_summary(
        self, adjusted_forecast: List[AdjustedForecastPoint]
    ) -> Dict[str, float]:
        """
        Calculate summary statistics for forecast adjustments.
        
        Returns:
            Dictionary with adjustment statistics
        """
        if not adjusted_forecast:
            return {
                "total_base_kwh": 0.0,
                "total_adjusted_kwh": 0.0,
                "avg_adjustment_factor": 1.0,
                "total_reduction_kwh": 0.0,
                "reduction_percentage": 0.0,
            }
        
        total_base_wh = 0.0
        total_adjusted_wh = 0.0
        
        # Calculate energy totals (trapezoidal integration)
        for i in range(len(adjusted_forecast) - 1):
            p1 = adjusted_forecast[i]
            p2 = adjusted_forecast[i + 1]
            hours = (p2.time - p1.time).total_seconds() / 3600.0
            
            # Average power over interval
            avg_base_w = (p1.base_watts + p2.base_watts) / 2.0
            avg_adjusted_w = (p1.adjusted_watts + p2.adjusted_watts) / 2.0
            
            total_base_wh += avg_base_w * hours
            total_adjusted_wh += avg_adjusted_w * hours
        
        total_base_kwh = total_base_wh / 1000.0
        total_adjusted_kwh = total_adjusted_wh / 1000.0
        total_reduction_kwh = total_base_kwh - total_adjusted_kwh
        
        reduction_pct = 0.0
        if total_base_kwh > 0:
            reduction_pct = (total_reduction_kwh / total_base_kwh) * 100.0
        
        avg_factor = total_adjusted_kwh / total_base_kwh if total_base_kwh > 0 else 1.0
        
        return {
            "total_base_kwh": round(total_base_kwh, 2),
            "total_adjusted_kwh": round(total_adjusted_kwh, 2),
            "avg_adjustment_factor": round(avg_factor, 3),
            "total_reduction_kwh": round(total_reduction_kwh, 2),
            "reduction_percentage": round(reduction_pct, 1),
        }
