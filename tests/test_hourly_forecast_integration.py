"""Test hourly weather forecast integration."""
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from homeassistant.util import dt as dt_util
    from custom_components.energy_dispatcher.forecast_provider import ForecastSolarProvider
    from custom_components.energy_dispatcher.manual_forecast_engine import ManualForecastEngine
    from custom_components.energy_dispatcher.models import ForecastPoint
    HAS_HA = True
except ImportError:
    HAS_HA = False
    pytest.skip("Home Assistant not installed, skipping integration tests", allow_module_level=True)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states.get = Mock(return_value=None)
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_hourly_forecast():
    """Create mock hourly forecast data."""
    now = datetime.now(dt_util.DEFAULT_TIME_ZONE)
    forecast = []
    for i in range(24):
        dt = now + timedelta(hours=i)
        forecast.append({
            "datetime": dt.isoformat(),
            "cloud_coverage": 50 + i * 2,  # Gradually increasing cloud cover
            "temperature": 15 + i * 0.5,
            "wind_speed": 5 + i * 0.2,
        })
    return forecast


class TestForecastProviderHourlyWeather:
    """Test ForecastSolarProvider with hourly weather data."""
    
    @pytest.mark.asyncio
    async def test_get_hourly_weather_forecast_success(self, mock_hass, mock_hourly_forecast):
        """Test successful retrieval of hourly weather forecast."""
        # Setup mock response
        weather_entity = "weather.home"
        mock_hass.services.async_call = AsyncMock(return_value={
            weather_entity: {
                "forecast": mock_hourly_forecast
            }
        })
        
        # Create provider
        provider = ForecastSolarProvider(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=weather_entity,
        )
        
        # Get hourly forecast
        forecast = await provider._get_hourly_weather_forecast()
        
        # Verify service was called
        mock_hass.services.async_call.assert_called_once_with(
            "weather",
            "get_forecasts",
            {"entity_id": weather_entity, "type": "hourly"},
            blocking=True,
            return_response=True,
        )
        
        # Verify forecast data
        assert len(forecast) == 24
        for dt, data in forecast.items():
            assert "cloud_coverage" in data
            assert isinstance(dt, datetime)
    
    @pytest.mark.asyncio
    async def test_get_hourly_weather_forecast_no_entity(self, mock_hass):
        """Test when no weather entity is configured."""
        provider = ForecastSolarProvider(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=None,
        )
        
        forecast = await provider._get_hourly_weather_forecast()
        
        # Should return empty dict
        assert forecast == {}
        # Service should not be called
        mock_hass.services.async_call.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_apply_cloud_compensation_with_hourly_forecast(self, mock_hass, mock_hourly_forecast):
        """Test cloud compensation using hourly forecast data."""
        weather_entity = "weather.home"
        mock_hass.services.async_call = AsyncMock(return_value={
            weather_entity: {
                "forecast": mock_hourly_forecast
            }
        })
        
        provider = ForecastSolarProvider(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=weather_entity,
            cloud_0_factor=250,
            cloud_100_factor=20,
        )
        
        # Create raw forecast points
        now = datetime.now(dt_util.DEFAULT_TIME_ZONE)
        raw_points = [
            ForecastPoint(time=now + timedelta(hours=i), watts=1000.0)
            for i in range(24)
        ]
        
        # Apply compensation
        compensated = await provider._apply_cloud_compensation(raw_points)
        
        # Verify compensation was applied
        assert len(compensated) == 24
        # Different points should have different compensation based on hourly cloud cover
        # (cloud cover increases in mock data, so watts should decrease)
        assert compensated[0].watts > compensated[-1].watts
    
    @pytest.mark.asyncio
    async def test_apply_cloud_compensation_fallback_to_current_state(self, mock_hass):
        """Test fallback to current state when hourly forecast is unavailable."""
        weather_entity = "weather.home"
        
        # Mock empty/failed hourly forecast
        mock_hass.services.async_call = AsyncMock(return_value={})
        
        # Mock current state
        mock_state = Mock()
        mock_state.attributes = {"cloud_coverage": 75}
        mock_hass.states.get = Mock(return_value=mock_state)
        
        provider = ForecastSolarProvider(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=weather_entity,
            cloud_0_factor=250,
            cloud_100_factor=20,
        )
        
        # Create raw forecast points
        now = datetime.now(dt_util.DEFAULT_TIME_ZONE)
        raw_points = [
            ForecastPoint(time=now + timedelta(hours=i), watts=1000.0)
            for i in range(5)
        ]
        
        # Apply compensation
        compensated = await provider._apply_cloud_compensation(raw_points)
        
        # Verify compensation was applied using current state
        assert len(compensated) == 5
        # All points should have same compensation (from current state)
        for i in range(1, 5):
            assert abs(compensated[i].watts - compensated[0].watts) < 0.01


class TestManualForecastEngineHourlyWeather:
    """Test ManualForecastEngine with hourly weather data."""
    
    @pytest.mark.asyncio
    async def test_get_hourly_weather_forecast_success(self, mock_hass, mock_hourly_forecast):
        """Test successful retrieval of hourly weather forecast in manual engine."""
        weather_entity = "weather.home"
        mock_hass.services.async_call = AsyncMock(return_value={
            weather_entity: {
                "forecast": mock_hourly_forecast
            }
        })
        
        engine = ManualForecastEngine(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=weather_entity,
        )
        
        forecast = await engine._get_hourly_weather_forecast()
        
        # Verify service was called
        mock_hass.services.async_call.assert_called_once()
        
        # Verify forecast data
        assert len(forecast) == 24
    
    @pytest.mark.asyncio
    async def test_get_weather_data_with_hourly_forecast(self, mock_hass, mock_hourly_forecast):
        """Test getting weather data with hourly forecast."""
        weather_entity = "weather.home"
        
        engine = ManualForecastEngine(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=weather_entity,
        )
        
        # Build hourly forecast dict
        now = datetime.now(dt_util.DEFAULT_TIME_ZONE)
        hourly_forecast = {}
        for i in range(24):
            dt = now + timedelta(hours=i)
            hourly_forecast[dt] = {
                "cloud_coverage": 50 + i * 2,
                "temperature": 15 + i * 0.5,
                "wind_speed": 5 + i * 0.2,
            }
        
        # Get weather data for a specific time
        target_time = now + timedelta(hours=5)
        weather_data = engine._get_weather_data(target_time, hourly_forecast)
        
        # Verify we got data from the forecast
        assert weather_data["cloud_cover"] is not None
        assert weather_data["temperature"] is not None
        assert weather_data["wind_speed"] is not None
        # Should be close to hour 5 values
        assert 55 <= weather_data["cloud_cover"] <= 65
    
    @pytest.mark.asyncio
    async def test_get_weather_data_fallback_to_current_state(self, mock_hass):
        """Test fallback to current state when hourly forecast is not provided."""
        weather_entity = "weather.home"
        
        # Mock current state
        mock_state = Mock()
        mock_state.attributes = {
            "cloud_coverage": 75,
            "temperature": 20,
            "wind_speed": 5,
        }
        mock_hass.states.get = Mock(return_value=mock_state)
        
        engine = ManualForecastEngine(
            hass=mock_hass,
            lat=56.7,
            lon=13.0,
            planes_json='[{"dec": 45, "az": 180, "kwp": 5.0}]',
            weather_entity=weather_entity,
        )
        
        # Get weather data without hourly forecast
        now = datetime.now(dt_util.DEFAULT_TIME_ZONE)
        weather_data = engine._get_weather_data(now, hourly_forecast=None)
        
        # Verify we got data from current state
        assert weather_data["cloud_cover"] == 75
        assert weather_data["temperature"] == 20
        assert weather_data["wind_speed"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
