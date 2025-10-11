"""Unit tests for House Load Baseline Now using current daypart."""
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
    
    # Mock the store with 48h lookback configuration and dayparts enabled
    mock_hass.data["energy_dispatcher"] = {
        "test_entry": {
            "config": {
                "runtime_lookback_hours": 48,
                "runtime_use_dayparts": True,
                "runtime_counter_entity": "sensor.house_energy",
                "evse_total_energy_sensor": "",
                "batt_total_charged_energy_entity": "",
                "pv_total_energy_entity": "",
                "runtime_exclude_ev": True,
                "runtime_exclude_batt_grid": True,
            },
        }
    }
    
    # Initialize coordinator data
    coordinator.data = {}
    
    return coordinator


class TestBaselineNowUsesDaypart:
    """Test that House Load Baseline Now uses the current daypart baseline."""
    
    @pytest.mark.asyncio
    async def test_baseline_now_uses_night_during_night_hours(self, coordinator, mock_hass):
        """Test that baseline_now uses night baseline during night hours (0-7)."""
        # Mock time to be in night period (e.g., 3 AM)
        mock_time = datetime(2025, 10, 6, 3, 30, 0)
        
        # Create mock history data with different consumption patterns
        # Night: 0.5 kWh/h, Day: 1.0 kWh/h, Evening: 1.5 kWh/h
        house_states = []
        energy = 100.0
        
        # Simulate 48 hours of data with different patterns
        for hour_offset in range(48):
            timestamp = mock_time - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            # Different consumption by time of day
            if 0 <= hour_of_day < 8:  # Night
                energy += 0.5
            elif 8 <= hour_of_day < 16:  # Day
                energy += 1.0
            else:  # Evening (16-23)
                energy += 1.5
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        # Mock the recorder.get_instance to raise an exception, forcing fallback to hass.async_add_executor_job
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        # Mock dt_util.now() to return our test time
        with patch('homeassistant.util.dt.now', return_value=mock_time):
            # Mock state for source value
            mock_state = MagicMock()
            mock_state.state = str(energy)
            mock_hass.states.get.return_value = mock_state
            
            # Run the baseline calculation
            await coordinator._update_baseline_and_runtime()
        
        # Verify that baseline_now (house_baseline_w) uses the night baseline
        baseline_now_w = coordinator.data.get("house_baseline_w")
        baseline_night_w = coordinator.data.get("baseline_night_w")
        baseline_day_w = coordinator.data.get("baseline_day_w")
        baseline_evening_w = coordinator.data.get("baseline_evening_w")
        
        assert baseline_now_w is not None, "house_baseline_w should be set"
        assert baseline_night_w is not None, "baseline_night_w should be set"
        assert baseline_day_w is not None, "baseline_day_w should be set"
        assert baseline_evening_w is not None, "baseline_evening_w should be set"
        
        # The key assertion: baseline_now should match baseline_night (within rounding)
        assert baseline_now_w == baseline_night_w, \
            f"During night hours, baseline_now ({baseline_now_w}W) should match baseline_night ({baseline_night_w}W)"
        
        # Verify the daypart baselines are different (showing the pattern works)
        assert baseline_night_w < baseline_day_w < baseline_evening_w, \
            "Baselines should increase from night to day to evening"
    
    @pytest.mark.asyncio
    async def test_baseline_now_uses_day_during_day_hours(self, coordinator, mock_hass):
        """Test that baseline_now uses day baseline during day hours (8-15)."""
        # Mock time to be in day period (e.g., 11 AM)
        mock_time = datetime(2025, 10, 6, 11, 30, 0)
        
        # Create mock history data with different consumption patterns
        house_states = []
        energy = 100.0
        
        for hour_offset in range(48):
            timestamp = mock_time - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            if 0 <= hour_of_day < 8:  # Night
                energy += 0.5
            elif 8 <= hour_of_day < 16:  # Day
                energy += 1.0
            else:  # Evening
                energy += 1.5
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        with patch('homeassistant.util.dt.now', return_value=mock_time):
            mock_state = MagicMock()
            mock_state.state = str(energy)
            mock_hass.states.get.return_value = mock_state
            
            await coordinator._update_baseline_and_runtime()
        
        baseline_now_w = coordinator.data.get("house_baseline_w")
        baseline_day_w = coordinator.data.get("baseline_day_w")
        
        assert baseline_now_w == baseline_day_w, \
            f"During day hours, baseline_now ({baseline_now_w}W) should match baseline_day ({baseline_day_w}W)"
    
    @pytest.mark.asyncio
    async def test_baseline_now_uses_evening_during_evening_hours(self, coordinator, mock_hass):
        """Test that baseline_now uses evening baseline during evening hours (16-23)."""
        # Mock time to be in evening period (e.g., 8 PM)
        mock_time = datetime(2025, 10, 6, 20, 30, 0)
        
        # Create mock history data with different consumption patterns
        house_states = []
        energy = 100.0
        
        for hour_offset in range(48):
            timestamp = mock_time - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            if 0 <= hour_of_day < 8:  # Night
                energy += 0.5
            elif 8 <= hour_of_day < 16:  # Day
                energy += 1.0
            else:  # Evening
                energy += 1.5
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        with patch('homeassistant.util.dt.now', return_value=mock_time):
            mock_state = MagicMock()
            mock_state.state = str(energy)
            mock_hass.states.get.return_value = mock_state
            
            await coordinator._update_baseline_and_runtime()
        
        baseline_now_w = coordinator.data.get("house_baseline_w")
        baseline_evening_w = coordinator.data.get("baseline_evening_w")
        
        assert baseline_now_w == baseline_evening_w, \
            f"During evening hours, baseline_now ({baseline_now_w}W) should match baseline_evening ({baseline_evening_w}W)"
    
    @pytest.mark.asyncio
    async def test_baseline_now_fallback_to_overall_when_dayparts_disabled(self, coordinator, mock_hass):
        """Test that baseline_now uses overall baseline when dayparts are disabled."""
        # Disable dayparts
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_use_dayparts"] = False
        
        mock_time = datetime(2025, 10, 6, 11, 30, 0)
        
        # Create mock history data
        house_states = []
        energy = 100.0
        
        for hour_offset in range(48):
            timestamp = mock_time - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            if 0 <= hour_of_day < 8:
                energy += 0.5
            elif 8 <= hour_of_day < 16:
                energy += 1.0
            else:
                energy += 1.5
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        with patch('homeassistant.util.dt.now', return_value=mock_time):
            mock_state = MagicMock()
            mock_state.state = str(energy)
            mock_hass.states.get.return_value = mock_state
            
            await coordinator._update_baseline_and_runtime()
        
        baseline_now_w = coordinator.data.get("house_baseline_w")
        baseline_kwh_per_h = coordinator.data.get("baseline_kwh_per_h")
        
        # Should use overall average, not daypart specific
        # Overall average: (0.5*8 + 1.0*8 + 1.5*8) / 24 = 1.0 kWh/h
        assert baseline_now_w is not None
        assert baseline_kwh_per_h is not None
        
        # Calculate expected overall: 48h of pattern = 2*(8*0.5 + 8*1.0 + 8*1.5) = 2*24 = 48 kWh over 48h = 1.0 kWh/h
        expected_w = 1000.0  # 1.0 kWh/h = 1000 W
        
        # Allow for some tolerance in calculation
        assert abs(baseline_now_w - expected_w) < 50, \
            f"With dayparts disabled, baseline_now should use overall average (~{expected_w}W), got {baseline_now_w}W"
