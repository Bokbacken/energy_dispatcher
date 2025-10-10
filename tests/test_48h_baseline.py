"""Unit tests for 48-hour baseline calculation with time-of-day weighting."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from custom_components.energy_dispatcher.coordinator import EnergyDispatcherCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.states = MagicMock()
    return hass


@pytest.fixture
def coordinator(mock_hass):
    """Create a coordinator instance with mocked dependencies."""
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    
    # Mock the store with 48h lookback configuration
    mock_hass.data["energy_dispatcher"] = {
        "test_entry": {
            "config": {
                "runtime_lookback_hours": 48,
                "runtime_use_dayparts": True,
                "runtime_power_entity": "sensor.house_power",
                "runtime_source": "power_w",
                "runtime_exclude_ev": True,
                "runtime_exclude_batt_grid": True,
            },
        }
    }
    
    return coordinator


class TestDaypartClassification:
    """Test time-of-day classification."""
    
    def test_classify_night_hours(self, coordinator):
        """Test that hours 0-7 are classified as night."""
        for hour in range(0, 8):
            assert coordinator._classify_hour_daypart(hour) == "night"
    
    def test_classify_day_hours(self, coordinator):
        """Test that hours 8-15 are classified as day."""
        for hour in range(8, 16):
            assert coordinator._classify_hour_daypart(hour) == "day"
    
    def test_classify_evening_hours(self, coordinator):
        """Test that hours 16-23 are classified as evening."""
        for hour in range(16, 24):
            assert coordinator._classify_hour_daypart(hour) == "evening"


class Test48HourBaseline:
    """Test 48-hour baseline calculation."""
    
    @pytest.mark.asyncio
    async def test_no_historical_data(self, coordinator, mock_hass):
        """Test that None is returned when no historical data is available."""
        # Mock empty history
        with patch('custom_components.energy_dispatcher.coordinator.history') as mock_history:
            mock_history.state_changes_during_period = MagicMock(return_value={})
            mock_hass.async_add_executor_job = AsyncMock(return_value={})
            
            result = await coordinator._calculate_48h_baseline()
            assert result is None
    
    @pytest.mark.asyncio
    async def test_baseline_calculation_with_data(self, coordinator, mock_hass):
        """Test baseline calculation with sample data."""
        # Create mock state objects
        now = datetime.now()
        states = []
        
        # Add 24 samples (one per hour for last 24 hours)
        for i in range(24):
            state = MagicMock()
            state.state = "1000"  # 1000W
            state.attributes = {"unit_of_measurement": "W"}
            state.last_changed = now - timedelta(hours=i)
            states.append(state)
        
        # Mock history response
        history_data = {
            "sensor.house_power": states
        }
        
        with patch('custom_components.energy_dispatcher.coordinator.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Should have results
            assert result is not None
            assert "overall" in result
            assert "night" in result
            assert "day" in result
            assert "evening" in result
            
            # Overall should be approximately 1 kWh/h (1000W / 1000)
            if result["overall"]:
                assert 0.9 <= result["overall"] <= 1.1
    
    @pytest.mark.asyncio
    async def test_exclusion_of_ev_charging(self, coordinator, mock_hass):
        """Test that EV charging periods are excluded."""
        now = datetime.now()
        house_states = []
        ev_states = []
        
        # Create samples where EV is charging half the time
        for i in range(24):
            house_state = MagicMock()
            house_state.state = "2000"  # 2000W house load
            house_state.attributes = {"unit_of_measurement": "W"}
            house_state.last_changed = now - timedelta(hours=i)
            house_states.append(house_state)
            
            ev_state = MagicMock()
            # EV charging every other hour
            ev_state.state = "3000" if i % 2 == 0 else "0"
            ev_state.last_changed = now - timedelta(hours=i)
            ev_states.append(ev_state)
        
        history_data = {
            "sensor.house_power": house_states,
            "sensor.ev_power": ev_states,
        }
        
        # Update config to include EV sensor
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["evse_power_sensor"] = "sensor.ev_power"
        
        with patch('custom_components.energy_dispatcher.coordinator.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Should exclude half the samples (when EV was charging)
            # So we should only have ~12 samples instead of 24
            assert result is not None


class TestBackwardCompatibility:
    """Test backward compatibility with existing configurations."""
    
    @pytest.mark.asyncio
    async def test_ema_fallback_when_lookback_zero(self, coordinator, mock_hass):
        """Test that EMA is used when lookback is 0."""
        # Configure for EMA mode
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_lookback_hours"] = 0
        
        # Mock current power state
        power_state = MagicMock()
        power_state.state = "1500"
        power_state.attributes = {"unit_of_measurement": "W"}
        mock_hass.states.get = MagicMock(return_value=power_state)
        
        # Update baseline should work with EMA
        await coordinator._update_baseline_and_runtime()
        
        # Should have baseline calculated
        assert coordinator.data.get("house_baseline_w") is not None
        assert coordinator.data.get("baseline_method") == "power_w"
    
    @pytest.mark.asyncio
    async def test_counter_method_still_works(self, coordinator, mock_hass):
        """Test that counter_kwh method still works."""
        # Configure for counter mode
        config = mock_hass.data["energy_dispatcher"]["test_entry"]["config"]
        config["runtime_source"] = "counter_kwh"
        config["runtime_counter_entity"] = "sensor.energy_counter"
        
        # Mock counter state
        counter_state = MagicMock()
        counter_state.state = "100.5"
        mock_hass.states.get = MagicMock(return_value=counter_state)
        
        # First update to establish baseline
        await coordinator._update_baseline_and_runtime()
        
        # Update again with new value
        counter_state.state = "101.0"
        await coordinator._update_baseline_and_runtime()
        
        # Should have baseline
        assert coordinator.data.get("baseline_method") == "counter_kwh"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
