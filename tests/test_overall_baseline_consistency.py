"""Unit tests for overall baseline consistency with daypart baselines."""
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


class TestOverallBaselineConsistency:
    """Test that overall baseline is consistent with daypart baselines."""
    
    @pytest.mark.asyncio
    async def test_overall_is_weighted_average_of_dayparts(self, coordinator, mock_hass):
        """Test that overall baseline equals weighted average of dayparts."""
        # Simulate the issue scenario: different consumption patterns by time of day
        # Night: 0.5 kWh/h, Day: 1.0 kWh/h, Evening: 1.5 kWh/h
        mock_time = datetime(2025, 10, 6, 12, 0, 0)
        
        house_states = []
        energy = 100.0
        
        # Create 48 hours of data with clear patterns
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
        
        # Mock the history fetch
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        # Call the baseline calculation
        result = await coordinator._calculate_48h_baseline()
        
        assert result is not None, "Baseline calculation should succeed"
        
        # Get the values
        overall = result.get("overall")
        night = result.get("night")
        day = result.get("day")
        evening = result.get("evening")
        
        assert overall is not None, "Overall baseline should be set"
        assert night is not None, "Night baseline should be set"
        assert day is not None, "Day baseline should be set"
        assert evening is not None, "Evening baseline should be set"
        
        # Calculate expected overall as weighted average
        # Each daypart is 8 hours in a 24-hour cycle
        expected_overall = (night * 8 + day * 8 + evening * 8) / 24
        
        # The overall should match the weighted average within a small tolerance
        tolerance = 0.01  # 10 Wh tolerance
        assert abs(overall - expected_overall) < tolerance, (
            f"Overall ({overall:.3f}) should equal weighted average of dayparts "
            f"({expected_overall:.3f}). Difference: {abs(overall - expected_overall):.3f}"
        )
        
        # Verify overall is between min and max dayparts
        min_daypart = min(night, day, evening)
        max_daypart = max(night, day, evening)
        assert min_daypart <= overall <= max_daypart, (
            f"Overall ({overall:.3f}) should be between min ({min_daypart:.3f}) "
            f"and max ({max_daypart:.3f}) daypart values"
        )
    
    @pytest.mark.asyncio
    async def test_overall_consistency_with_actual_issue_values(self, coordinator, mock_hass):
        """Test with values close to those reported in the issue."""
        # Simulate data that would produce values similar to the issue:
        # Night: ~767 W, Day: ~991 W, Evening: ~1206 W
        mock_time = datetime(2025, 10, 6, 12, 0, 0)
        
        house_states = []
        energy = 100.0
        
        # Create data that produces the reported pattern
        for hour_offset in range(48):
            timestamp = mock_time - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            if 0 <= hour_of_day < 8:  # Night - lower consumption
                energy += 0.767
            elif 8 <= hour_of_day < 16:  # Day - medium consumption
                energy += 0.991
            else:  # Evening - higher consumption
                energy += 1.206
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        result = await coordinator._calculate_48h_baseline()
        
        assert result is not None
        
        overall = result.get("overall")
        night = result.get("night")
        day = result.get("day")
        evening = result.get("evening")
        
        # Expected overall from dayparts
        expected_overall = (night * 8 + day * 8 + evening * 8) / 24
        
        # Key assertion: overall should NOT be higher than all dayparts
        # (which was the bug in the issue)
        assert not (overall > night and overall > day and overall > evening), (
            f"Overall ({overall:.3f}) should NOT be higher than all dayparts "
            f"(night: {night:.3f}, day: {day:.3f}, evening: {evening:.3f})"
        )
        
        # Overall should be consistent with weighted average
        tolerance = 0.01
        assert abs(overall - expected_overall) < tolerance, (
            f"Overall should equal weighted average. "
            f"Got {overall:.3f}, expected {expected_overall:.3f}"
        )
    
    @pytest.mark.asyncio
    async def test_overall_fallback_when_dayparts_disabled(self, coordinator, mock_hass):
        """Test that overall uses start/end delta when dayparts are disabled."""
        # Disable dayparts
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_use_dayparts"] = False
        
        mock_time = datetime(2025, 10, 6, 12, 0, 0)
        
        # Simple data: start at 100, end at 148 (48 kWh over 48 hours = 1 kWh/h)
        house_states = []
        
        start_state = MagicMock()
        start_state.state = "100.0"
        start_state.last_changed = mock_time - timedelta(hours=48)
        house_states.append(start_state)
        
        end_state = MagicMock()
        end_state.state = "148.0"
        end_state.last_changed = mock_time
        house_states.append(end_state)
        
        history_data = {
            "sensor.house_energy": house_states,
        }
        
        mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
        
        result = await coordinator._calculate_48h_baseline()
        
        assert result is not None
        
        overall = result.get("overall")
        
        # With dayparts disabled, overall should use simple start/end delta
        expected = 48.0 / 48  # 1.0 kWh/h
        assert abs(overall - expected) < 0.01, (
            f"With dayparts disabled, overall should use start/end delta. "
            f"Got {overall:.3f}, expected {expected:.3f}"
        )
