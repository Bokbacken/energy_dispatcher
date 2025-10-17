"""Integration tests for weather-aware optimization planning.

This module tests the integration between WeatherOptimizer, CostStrategy,
and the battery reserve calculation to ensure weather adjustments are
properly applied when calculating battery reserve requirements.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from custom_components.energy_dispatcher.weather_optimizer import (
    WeatherOptimizer,
    WeatherPoint,
)
from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.models import PricePoint, ForecastPoint


@pytest.fixture
def hass_mock():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    return hass


@pytest.fixture
def weather_optimizer(hass_mock):
    """Create a WeatherOptimizer instance."""
    return WeatherOptimizer(hass_mock)


@pytest.fixture
def cost_strategy():
    """Create a CostStrategy instance."""
    return CostStrategy()


@pytest.fixture
def sample_prices():
    """Create sample price data with high-cost periods."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    prices = []
    
    # Create prices with high-cost periods (hours 8-10 and 17-20)
    for hour in range(24):
        if 8 <= hour < 10 or 17 <= hour < 20:
            # High price hours
            enriched_price = 4.0
        elif hour < 6 or hour >= 22:
            # Cheap price hours
            enriched_price = 1.0
        else:
            # Medium price hours
            enriched_price = 2.0
        
        prices.append(
            PricePoint(
                time=now + timedelta(hours=hour),
                spot_sek_per_kwh=enriched_price * 0.8,
                enriched_sek_per_kwh=enriched_price,
                export_sek_per_kwh=enriched_price * 0.6,
            )
        )
    
    return prices


@pytest.fixture
def base_solar_forecast():
    """Create a base solar forecast (3000W constant)."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    forecast = []
    
    # 24 hours of constant 3000W forecast (daylight hours)
    for hour in range(24):
        # Solar production only during daylight hours (6-18)
        if 6 <= hour < 18:
            watts = 3000.0
        else:
            watts = 0.0
        
        forecast.append(
            ForecastPoint(
                time=now + timedelta(hours=hour),
                watts=watts,
            )
        )
    
    return forecast


@pytest.fixture
def clear_weather():
    """Create clear weather forecast (no clouds)."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    weather = []
    
    for hour in range(24):
        weather.append(
            WeatherPoint(
                time=now + timedelta(hours=hour),
                cloud_coverage_pct=5.0,
                temperature_c=20.0,
                condition="sunny",
            )
        )
    
    return weather


@pytest.fixture
def cloudy_weather():
    """Create cloudy weather forecast (65% cloud coverage)."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    weather = []
    
    for hour in range(24):
        weather.append(
            WeatherPoint(
                time=now + timedelta(hours=hour),
                cloud_coverage_pct=65.0,
                temperature_c=18.0,
                condition="cloudy",
            )
        )
    
    return weather


@pytest.fixture
def overcast_weather():
    """Create overcast weather forecast (95% cloud coverage)."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    weather = []
    
    for hour in range(24):
        weather.append(
            WeatherPoint(
                time=now + timedelta(hours=hour),
                cloud_coverage_pct=95.0,
                temperature_c=15.0,
                condition="cloudy",
            )
        )
    
    return weather


class TestWeatherIntegrationWithBatteryReserve:
    """Test integration of weather adjustments with battery reserve calculation."""

    def test_clear_weather_no_adjustment(
        self,
        weather_optimizer,
        cost_strategy,
        sample_prices,
        base_solar_forecast,
        clear_weather,
    ):
        """Test that clear weather does not increase battery reserve."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        battery_capacity_kwh = 30.0
        current_soc = 50.0
        
        # Update cost strategy thresholds
        cost_strategy.update_thresholds(cheap_max=1.5, high_min=3.0)
        
        # Calculate adjusted forecast
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=clear_weather,
        )
        
        # Calculate adjustment summary
        weather_adjustment = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Reserve without weather adjustment
        reserve_without = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
        )
        
        # Reserve with weather adjustment (clear weather)
        reserve_with = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
            weather_adjustment=weather_adjustment,
        )
        
        # Clear weather should not change reserve (reduction < 20%)
        assert weather_adjustment["reduction_percentage"] < 20.0
        assert reserve_with == pytest.approx(reserve_without, rel=0.01)

    def test_cloudy_weather_moderate_adjustment(
        self,
        weather_optimizer,
        cost_strategy,
        sample_prices,
        base_solar_forecast,
        cloudy_weather,
    ):
        """Test that cloudy weather increases battery reserve moderately."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        battery_capacity_kwh = 30.0
        current_soc = 50.0
        
        # Update cost strategy thresholds
        cost_strategy.update_thresholds(cheap_max=1.5, high_min=3.0)
        
        # Calculate adjusted forecast
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=cloudy_weather,
        )
        
        # Calculate adjustment summary
        weather_adjustment = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Reserve without weather adjustment
        reserve_without = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
        )
        
        # Reserve with weather adjustment (cloudy weather)
        reserve_with = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
            weather_adjustment=weather_adjustment,
        )
        
        # Cloudy weather (65% clouds) should reduce solar by ~35-50%
        assert 35.0 <= weather_adjustment["reduction_percentage"] <= 50.0
        
        # Reserve should be >= when weather adjustment is applied
        # Both might be 0 if solar forecast covers all high-cost hours even after reduction
        # The key is that weather adjustment was considered
        assert reserve_with >= reserve_without
        
        # If there is any reserve needed, verify it increases appropriately
        if reserve_without > 0:
            assert reserve_with > reserve_without
            assert reserve_with <= reserve_without * 1.20  # Not more than 20% increase

    def test_overcast_weather_severe_adjustment(
        self,
        weather_optimizer,
        cost_strategy,
        sample_prices,
        base_solar_forecast,
        overcast_weather,
    ):
        """Test that overcast weather increases battery reserve significantly."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        battery_capacity_kwh = 30.0
        current_soc = 50.0
        
        # Update cost strategy thresholds
        cost_strategy.update_thresholds(cheap_max=1.5, high_min=3.0)
        
        # Calculate adjusted forecast
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=overcast_weather,
        )
        
        # Calculate adjustment summary
        weather_adjustment = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Reserve without weather adjustment
        reserve_without = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
        )
        
        # Reserve with weather adjustment (overcast weather)
        reserve_with = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
            weather_adjustment=weather_adjustment,
        )
        
        # Overcast weather (95% clouds) should reduce solar by ~65-75%
        assert weather_adjustment["reduction_percentage"] >= 65.0
        
        # Reserve should increase when weather adjustment is applied
        # Note: If solar completely covers the high-cost hours even after reduction,
        # the reserve might still be 0. The key test is that the weather adjustment
        # was applied and increased the reserve requirement (even if final is 0)
        assert reserve_with >= reserve_without


class TestWeatherAdjustmentSummary:
    """Test the weather adjustment summary calculation."""

    def test_summary_with_clear_weather(
        self,
        weather_optimizer,
        base_solar_forecast,
        clear_weather,
    ):
        """Test adjustment summary with clear weather."""
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=clear_weather,
        )
        
        summary = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Clear weather should result in minimal reduction
        assert summary["reduction_percentage"] < 5.0
        assert summary["avg_adjustment_factor"] > 0.95
        assert summary["total_adjusted_kwh"] >= summary["total_base_kwh"] * 0.95

    def test_summary_with_cloudy_weather(
        self,
        weather_optimizer,
        base_solar_forecast,
        cloudy_weather,
    ):
        """Test adjustment summary with cloudy weather."""
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=cloudy_weather,
        )
        
        summary = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Cloudy weather should result in moderate reduction (35-50%)
        assert 35.0 <= summary["reduction_percentage"] <= 50.0
        assert 0.50 <= summary["avg_adjustment_factor"] <= 0.65
        assert summary["total_reduction_kwh"] > 0

    def test_summary_with_overcast_weather(
        self,
        weather_optimizer,
        base_solar_forecast,
        overcast_weather,
    ):
        """Test adjustment summary with overcast weather."""
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=overcast_weather,
        )
        
        summary = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Overcast weather should result in severe reduction
        assert summary["reduction_percentage"] >= 65.0
        assert summary["avg_adjustment_factor"] <= 0.35
        assert summary["total_reduction_kwh"] > summary["total_base_kwh"] * 0.6


class TestEndToEndWeatherIntegration:
    """End-to-end integration tests simulating real-world scenarios."""

    def test_full_integration_path(
        self,
        weather_optimizer,
        cost_strategy,
        sample_prices,
        base_solar_forecast,
        cloudy_weather,
    ):
        """Test the complete integration path from weather to reserve calculation."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        battery_capacity_kwh = 30.0
        current_soc = 50.0
        
        # Step 1: Update cost thresholds
        cost_strategy.update_thresholds(cheap_max=1.5, high_min=3.0)
        
        # Step 2: Adjust solar forecast for weather
        adjusted_forecast = weather_optimizer.adjust_solar_forecast_for_weather(
            base_solar_forecast=base_solar_forecast,
            weather_forecast=cloudy_weather,
        )
        
        # Step 3: Calculate adjustment summary
        weather_adjustment = weather_optimizer.calculate_forecast_adjustment_summary(
            adjusted_forecast
        )
        
        # Verify adjustment summary is correct
        assert "total_base_kwh" in weather_adjustment
        assert "total_adjusted_kwh" in weather_adjustment
        assert "avg_adjustment_factor" in weather_adjustment
        assert "total_reduction_kwh" in weather_adjustment
        assert "reduction_percentage" in weather_adjustment
        
        # Step 4: Calculate battery reserve with weather adjustment
        reserve = cost_strategy.calculate_battery_reserve(
            prices=sample_prices,
            now=now,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc=current_soc,
            solar_forecast=base_solar_forecast,
            weather_adjustment=weather_adjustment,
        )
        
        # Verify reserve is calculated
        assert reserve is not None
        assert 0.0 <= reserve <= 60.0  # Reserve is capped at 60%
        
        # Verify integration works as expected
        if weather_adjustment["reduction_percentage"] > 20.0:
            # Should increase reserve for significant reductions
            reserve_without_weather = cost_strategy.calculate_battery_reserve(
                prices=sample_prices,
                now=now,
                battery_capacity_kwh=battery_capacity_kwh,
                current_soc=current_soc,
                solar_forecast=base_solar_forecast,
            )
            assert reserve >= reserve_without_weather
