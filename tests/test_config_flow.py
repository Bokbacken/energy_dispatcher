"""Unit tests for config_flow module."""
import pytest
from unittest.mock import MagicMock

from custom_components.energy_dispatcher.config_flow import _available_weather_entities


class MockState:
    """Mock Home Assistant state object."""
    
    def __init__(self, entity_id, attributes):
        self.entity_id = entity_id
        self.attributes = attributes


class MockStates:
    """Mock Home Assistant states manager."""
    
    def __init__(self, weather_states=None):
        self._weather_states = weather_states or []
    
    def async_all(self, domain):
        """Return all states for a given domain."""
        if domain == "weather":
            return self._weather_states
        return []


@pytest.fixture
def mock_hass_with_states():
    """Create a mock Home Assistant instance with states attribute."""
    hass = MagicMock()
    hass.states = MockStates()
    return hass


@pytest.fixture
def mock_hass_without_states():
    """Create a mock Home Assistant instance without states attribute."""
    hass = MagicMock(spec=[])  # spec=[] ensures no attributes
    # Explicitly delete states if it exists
    if hasattr(hass, 'states'):
        delattr(hass, 'states')
    return hass


class TestAvailableWeatherEntities:
    """Test _available_weather_entities function."""

    def test_hass_is_none(self):
        """Test that None hass returns empty list."""
        result = _available_weather_entities(None)
        assert result == []

    def test_hass_without_states_attribute(self, mock_hass_without_states):
        """Test that hass without states attribute returns empty list without error."""
        result = _available_weather_entities(mock_hass_without_states)
        assert result == []

    def test_hass_with_empty_weather_list(self, mock_hass_with_states):
        """Test that hass with no weather entities returns empty list."""
        mock_hass_with_states.states = MockStates([])
        result = _available_weather_entities(mock_hass_with_states)
        assert result == []

    def test_hass_with_weather_entity_cloudiness(self, mock_hass_with_states):
        """Test weather entity with cloudiness attribute is detected."""
        weather_states = [
            MockState("weather.home", {"cloudiness": 50, "temperature": 20})
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert len(result) == 1
        assert "weather.home" in result

    def test_hass_with_weather_entity_cloud_coverage(self, mock_hass_with_states):
        """Test weather entity with cloud_coverage attribute is detected."""
        weather_states = [
            MockState("weather.forecast", {"cloud_coverage": 75})
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert len(result) == 1
        assert "weather.forecast" in result

    def test_hass_with_weather_entity_cloud_cover(self, mock_hass_with_states):
        """Test weather entity with cloud_cover attribute is detected."""
        weather_states = [
            MockState("weather.openweather", {"cloud_cover": 25})
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert len(result) == 1
        assert "weather.openweather" in result

    def test_hass_with_weather_entity_cloud(self, mock_hass_with_states):
        """Test weather entity with cloud attribute is detected."""
        weather_states = [
            MockState("weather.met", {"cloud": 60})
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert len(result) == 1
        assert "weather.met" in result

    def test_hass_filters_weather_without_cloud_data(self, mock_hass_with_states):
        """Test that weather entities without cloud attributes are filtered out."""
        weather_states = [
            MockState("weather.home", {"cloudiness": 50}),
            MockState("weather.no_cloud", {"temperature": 20, "humidity": 70}),
            MockState("weather.forecast", {"cloud_coverage": 75}),
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert len(result) == 2
        assert "weather.home" in result
        assert "weather.forecast" in result
        assert "weather.no_cloud" not in result

    def test_hass_with_multiple_cloud_attributes(self, mock_hass_with_states):
        """Test weather entity with multiple cloud attributes."""
        weather_states = [
            MockState("weather.complex", {
                "cloudiness": 50,
                "cloud_coverage": 50,
                "temperature": 20
            })
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert len(result) == 1
        assert "weather.complex" in result

    def test_hass_with_empty_attributes(self, mock_hass_with_states):
        """Test weather entity with no attributes."""
        weather_states = [
            MockState("weather.empty", {})
        ]
        mock_hass_with_states.states = MockStates(weather_states)
        result = _available_weather_entities(mock_hass_with_states)
        assert result == []
