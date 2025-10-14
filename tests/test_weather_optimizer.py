"""Tests for weather-aware solar optimization."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from custom_components.energy_dispatcher.weather_optimizer import (
    WeatherOptimizer,
    WeatherPoint,
    AdjustedForecastPoint,
)
from custom_components.energy_dispatcher.models import ForecastPoint


@pytest.fixture
def hass_mock():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    return hass


@pytest.fixture
def optimizer(hass_mock):
    """Create a WeatherOptimizer instance."""
    return WeatherOptimizer(hass_mock)


@pytest.fixture
def base_forecast():
    """Create a base solar forecast."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    forecast = []
    
    # 24 hours of constant 3000W forecast
    for hour in range(24):
        forecast.append(
            ForecastPoint(
                time=now + timedelta(hours=hour),
                watts=3000.0,
            )
        )
    
    return forecast


@pytest.fixture
def weather_clear():
    """Create clear weather forecast."""
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
def weather_cloudy():
    """Create cloudy weather forecast."""
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
def weather_overcast():
    """Create overcast weather forecast."""
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


class TestCloudCoverAdjustments:
    """Test cloud cover adjustment calculations."""

    def test_clear_sky_no_adjustment(self, optimizer, base_forecast, weather_clear):
        """Test that clear sky (0-10% clouds) results in 100% of base forecast."""
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather_clear
        )
        
        assert len(adjusted) == len(base_forecast)
        
        # Check first point
        assert adjusted[0].base_watts == 3000.0
        assert adjusted[0].adjusted_watts == pytest.approx(3000.0, rel=0.01)
        assert adjusted[0].adjustment_factor == pytest.approx(1.0, rel=0.01)
        assert adjusted[0].confidence_level == "high"
        assert adjusted[0].limiting_factor == "clear"

    def test_partly_cloudy_adjustment(self, optimizer, base_forecast):
        """Test partly cloudy (11-50%) results in 70-80% of base forecast."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Test 30% cloud coverage (middle of partly cloudy range)
        weather = [
            WeatherPoint(
                time=now,
                cloud_coverage_pct=30.0,
                temperature_c=20.0,
            )
        ]
        forecast = [base_forecast[0]]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(forecast, weather)
        
        # At 30% clouds, should be in 70-80% range
        # Linear interpolation: 30% is halfway between 10% and 50%
        # Factor should be approximately 0.875 (87.5%)
        assert adjusted[0].adjusted_watts < 3000.0
        assert adjusted[0].adjusted_watts > 2100.0  # Above 70%
        assert adjusted[0].adjustment_factor < 1.0
        assert adjusted[0].adjustment_factor > 0.70
        assert adjusted[0].limiting_factor == "cloud_cover"

    def test_cloudy_adjustment(self, optimizer, base_forecast, weather_cloudy):
        """Test cloudy (51-80%) results in 40-60% of base forecast."""
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather_cloudy
        )
        
        # 65% cloud coverage should result in 40-60% range
        # At 65%: interpolates between 50% (at 80%) and 75% (at 50%)
        # Factor ~0.625, which is 62.5% - slightly above 60% but within range
        assert adjusted[0].adjusted_watts < 2000.0  # Below ~67%
        assert adjusted[0].adjusted_watts > 1200.0  # Above 40%
        assert adjusted[0].adjustment_factor < 0.70
        assert adjusted[0].adjustment_factor > 0.40
        assert adjusted[0].confidence_level == "medium"

    def test_overcast_adjustment(self, optimizer, base_forecast, weather_overcast):
        """Test overcast (81-100%) results in 20-30% of base forecast."""
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather_overcast
        )
        
        # 95% cloud coverage should result in 20-30% range
        # At 95%: interpolates from 50% (at 80%) to 25% (at 100%)
        # Factor ~0.3125, which is 31.25% - slightly above 30% but close
        assert adjusted[0].adjusted_watts < 1000.0  # Below ~33%
        assert adjusted[0].adjusted_watts > 600.0  # Above 20%
        assert adjusted[0].adjustment_factor < 0.35
        assert adjusted[0].adjustment_factor > 0.20


class TestTemperatureAdjustments:
    """Test temperature adjustment calculations."""

    def test_below_reference_temp_no_adjustment(self, optimizer, base_forecast):
        """Test that temperatures below 25°C don't reduce forecast."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        weather = [
            WeatherPoint(
                time=now,
                cloud_coverage_pct=5.0,  # Clear sky
                temperature_c=20.0,  # Below reference
            )
        ]
        forecast = [base_forecast[0]]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(forecast, weather)
        
        # Should be close to 100% (only clear sky factor)
        assert adjusted[0].adjusted_watts == pytest.approx(3000.0, rel=0.01)
        assert adjusted[0].adjustment_factor == pytest.approx(1.0, rel=0.01)

    def test_high_temperature_adjustment(self, optimizer, base_forecast):
        """Test that high temperatures reduce forecast by 0.4-0.5% per °C above 25°C."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Test at 35°C (10°C above reference)
        weather = [
            WeatherPoint(
                time=now,
                cloud_coverage_pct=5.0,  # Clear sky
                temperature_c=35.0,  # 10°C above reference
            )
        ]
        forecast = [base_forecast[0]]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(forecast, weather)
        
        # Expected: 10°C * 0.45% = 4.5% reduction -> 95.5% factor
        # With clear sky: 1.0 * 0.955 = 0.955
        expected_watts = 3000.0 * 0.955
        assert adjusted[0].adjusted_watts == pytest.approx(expected_watts, rel=0.01)
        assert adjusted[0].limiting_factor == "temperature"

    def test_extreme_temperature_clamping(self, optimizer, base_forecast):
        """Test that extreme temperatures are clamped to minimum 50% efficiency."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Test at 100°C (extreme, should clamp)
        weather = [
            WeatherPoint(
                time=now,
                cloud_coverage_pct=5.0,  # Clear sky
                temperature_c=100.0,
            )
        ]
        forecast = [base_forecast[0]]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(forecast, weather)
        
        # Should be clamped to at least 50% (1500W)
        assert adjusted[0].adjusted_watts >= 1500.0


class TestCombinedAdjustments:
    """Test combined cloud and temperature adjustments."""

    def test_cloudy_and_hot(self, optimizer, base_forecast):
        """Test combined adjustment for cloudy and hot conditions."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        weather = [
            WeatherPoint(
                time=now,
                cloud_coverage_pct=60.0,  # Cloudy
                temperature_c=35.0,  # Hot
            )
        ]
        forecast = [base_forecast[0]]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(forecast, weather)
        
        # Both factors should reduce forecast
        # At 60% clouds: interpolates between 50% (at 80%) and 75% (at 50%)
        # Cloud factor: ~0.6625 (for 60% clouds, 1/3 of way from 75% to 50%)
        # Temp factor: ~0.955 (for 10°C above reference)
        # Combined: ~0.633
        expected_watts = 3000.0 * 0.6375 * 0.955
        assert adjusted[0].adjusted_watts == pytest.approx(expected_watts, rel=0.08)
        assert adjusted[0].limiting_factor == "multiple"

    def test_clear_and_hot(self, optimizer, base_forecast):
        """Test adjustment for clear but hot conditions."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        weather = [
            WeatherPoint(
                time=now,
                cloud_coverage_pct=5.0,  # Clear
                temperature_c=32.0,  # Hot
            )
        ]
        forecast = [base_forecast[0]]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(forecast, weather)
        
        # Only temp adjustment: 7°C * 0.45% = 3.15% reduction
        expected_watts = 3000.0 * 0.9685
        assert adjusted[0].adjusted_watts == pytest.approx(expected_watts, rel=0.02)


class TestMissingData:
    """Test handling of missing weather data."""

    def test_no_weather_data(self, optimizer, base_forecast):
        """Test that missing weather data returns base forecast with low confidence."""
        adjusted = optimizer.adjust_solar_forecast_for_weather(base_forecast, [])
        
        assert len(adjusted) == len(base_forecast)
        assert adjusted[0].adjusted_watts == 3000.0
        assert adjusted[0].adjustment_factor == 1.0
        assert adjusted[0].confidence_level == "low"
        assert adjusted[0].limiting_factor == "no_weather_data"

    def test_partial_weather_data(self, optimizer, base_forecast):
        """Test handling of partial weather data (some hours missing)."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Only provide weather for first 12 hours
        weather = []
        for hour in range(12):
            weather.append(
                WeatherPoint(
                    time=now + timedelta(hours=hour),
                    cloud_coverage_pct=30.0,
                    temperature_c=20.0,
                )
            )
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather
        )
        
        # First 12 hours should have adjustments
        assert adjusted[0].adjustment_factor < 1.0
        assert adjusted[0].confidence_level in ["high", "medium"]
        
        # Last 12 hours should use base forecast
        assert adjusted[12].adjusted_watts == 3000.0
        assert adjusted[12].confidence_level == "low"


class TestAdjustmentSummary:
    """Test forecast adjustment summary calculations."""

    def test_summary_calculation(self, optimizer, base_forecast, weather_cloudy):
        """Test calculation of adjustment summary statistics."""
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather_cloudy
        )
        
        summary = optimizer.calculate_forecast_adjustment_summary(adjusted)
        
        assert "total_base_kwh" in summary
        assert "total_adjusted_kwh" in summary
        assert "avg_adjustment_factor" in summary
        assert "total_reduction_kwh" in summary
        assert "reduction_percentage" in summary
        
        # Base forecast should be higher than adjusted
        assert summary["total_base_kwh"] > summary["total_adjusted_kwh"]
        assert summary["total_reduction_kwh"] > 0
        assert summary["reduction_percentage"] > 0
        
        # For cloudy weather (40-60% of base), reduction should be 40-60%
        assert summary["reduction_percentage"] > 35
        assert summary["reduction_percentage"] < 65

    def test_summary_clear_weather(self, optimizer, base_forecast, weather_clear):
        """Test summary with clear weather (minimal adjustment)."""
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather_clear
        )
        
        summary = optimizer.calculate_forecast_adjustment_summary(adjusted)
        
        # Clear weather should result in minimal reduction
        assert summary["total_base_kwh"] == pytest.approx(
            summary["total_adjusted_kwh"], rel=0.01
        )
        assert summary["reduction_percentage"] == pytest.approx(0.0, abs=1.0)


class TestWeatherEntityExtraction:
    """Test extraction of weather data from Home Assistant entities."""

    def test_extract_weather_forecast(self, hass_mock, optimizer):
        """Test extraction of weather forecast from HA entity."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Mock weather entity state
        mock_state = Mock()
        mock_state.attributes = {
            "forecast": [
                {
                    "datetime": (now + timedelta(hours=i)).isoformat(),
                    "cloudiness": 30.0 + i * 2,
                    "temperature": 20.0 + i * 0.5,
                    "condition": "partly-cloudy",
                }
                for i in range(24)
            ]
        }
        hass_mock.states.get.return_value = mock_state
        
        weather_points = optimizer.extract_weather_forecast_from_entity(
            "weather.home", hours=24
        )
        
        assert len(weather_points) == 24
        assert weather_points[0].cloud_coverage_pct == 30.0
        assert weather_points[0].temperature_c == 20.0
        assert weather_points[5].cloud_coverage_pct == 40.0

    def test_extract_missing_entity(self, hass_mock, optimizer):
        """Test extraction when weather entity doesn't exist."""
        hass_mock.states.get.return_value = None
        
        weather_points = optimizer.extract_weather_forecast_from_entity(
            "weather.nonexistent", hours=24
        )
        
        assert len(weather_points) == 0


class TestBatteryReserveIntegration:
    """Test integration with battery reserve calculation."""

    def test_reserve_increase_on_downward_adjustment(self, optimizer):
        """Test that downward solar adjustment suggests reserve increase."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Base forecast: 3000W constant
        base_forecast = [
            ForecastPoint(time=now + timedelta(hours=i), watts=3000.0)
            for i in range(24)
        ]
        
        # Overcast weather: 20-30% of base
        weather = [
            WeatherPoint(
                time=now + timedelta(hours=i),
                cloud_coverage_pct=90.0,
                temperature_c=20.0,
            )
            for i in range(24)
        ]
        
        adjusted = optimizer.adjust_solar_forecast_for_weather(
            base_forecast, weather
        )
        summary = optimizer.calculate_forecast_adjustment_summary(adjusted)
        
        # Verify significant reduction
        assert summary["reduction_percentage"] > 60  # More than 60% reduction
        
        # This reduction should trigger 10-20% reserve increase in cost_strategy
        # That integration will be tested in cost_strategy tests
