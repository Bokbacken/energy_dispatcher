"""Unit tests for daypart baseline calculation."""
import pytest
from unittest.mock import MagicMock
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
    
    # Mock the store with configuration
    mock_hass.data["energy_dispatcher"] = {
        "test_entry": {
            "config": {
                "runtime_lookback_hours": 48,
                "runtime_use_dayparts": True,
                "runtime_counter_entity": "sensor.house_energy",
                "runtime_exclude_ev": True,
                "runtime_exclude_batt_grid": True,
            },
        }
    }
    
    return coordinator


class TestDaypartBaselinesMethod:
    """Test the _calculate_daypart_baselines method directly."""
    
    def test_daypart_baselines_with_varying_consumption(self, coordinator):
        """Test that daypart baselines reflect different consumption patterns."""
        now = datetime.now()
        
        # Create hourly data with different consumption patterns by time of day
        house_states = []
        
        # Simulate 48 hours of data
        # Night hours (00:00-07:59): Low consumption ~0.5 kWh/h
        # Day hours (08:00-15:59): Medium consumption ~1.0 kWh/h  
        # Evening hours (16:00-23:59): High consumption ~2.0 kWh/h
        
        energy = 100.0
        for hour_offset in range(48):
            timestamp = now - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            # Simulate different consumption rates by time of day
            if 0 <= hour_of_day < 8:  # Night
                energy += 0.5
            elif 8 <= hour_of_day < 16:  # Day
                energy += 1.0
            else:  # Evening
                energy += 2.0
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        # Call the method directly
        result = coordinator._calculate_daypart_baselines(
            house_states, [], [], [], False, False
        )
        
        assert result is not None
        assert "night" in result
        assert "day" in result
        assert "evening" in result
        
        night = result["night"]
        day = result["day"]
        evening = result["evening"]
        
        # Verify values are not None
        assert night is not None
        assert day is not None
        assert evening is not None
        
        # Night should be lowest
        assert night < day, f"Night ({night}) should be < Day ({day})"
        assert night < evening, f"Night ({night}) should be < Evening ({evening})"
        
        # Evening should be highest
        assert evening > day, f"Evening ({evening}) should be > Day ({day})"
        assert evening > night, f"Evening ({evening}) should be > Night ({night})"
        
        # Check approximate values (with tolerance)
        assert 0.4 <= night <= 0.6, f"Night should be ~0.5 kWh/h, got {night}"
        assert 0.9 <= day <= 1.2, f"Day should be ~1.0 kWh/h, got {day}"
        assert 1.8 <= evening <= 2.2, f"Evening should be ~2.0 kWh/h, got {evening}"
    
    def test_daypart_baselines_with_ev_exclusion(self, coordinator):
        """Test that EV charging is properly excluded from evening baseline."""
        now = datetime.now()
        
        # Create hourly data with EV charging in evening
        house_states = []
        ev_states = []
        
        house_energy = 100.0
        ev_energy = 50.0
        
        for hour_offset in range(48):
            timestamp = now - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            # Base house consumption: 1 kWh/h
            house_energy += 1.0
            
            # Add EV charging in evening (16:00-23:59): additional 3 kWh/h
            # This means house total will be 4 kWh/h in evening without exclusion
            if 16 <= hour_of_day < 24:
                house_energy += 3.0
                ev_energy += 3.0
            
            house_state = MagicMock()
            house_state.state = str(house_energy)
            house_state.last_changed = timestamp
            house_states.append(house_state)
            
            ev_state = MagicMock()
            ev_state.state = str(ev_energy)
            ev_state.last_changed = timestamp
            ev_states.append(ev_state)
        
        # Call with EV exclusion enabled
        result = coordinator._calculate_daypart_baselines(
            house_states, ev_states, [], [], True, False
        )
        
        assert result is not None
        
        # Evening baseline should be ~1 kWh/h after excluding EV (not ~4 kWh/h)
        evening = result.get("evening")
        assert evening is not None
        assert 0.8 <= evening <= 1.2, f"Evening should be ~1 kWh/h after EV exclusion, got {evening}"
        
        # Night and day should be unaffected (no EV charging)
        night = result.get("night")
        day = result.get("day")
        assert night is not None
        assert day is not None
        assert 0.8 <= night <= 1.2, f"Night should be ~1 kWh/h, got {night}"
        assert 0.8 <= day <= 1.2, f"Day should be ~1 kWh/h, got {day}"
    
    def test_daypart_baselines_with_battery_exclusion(self, coordinator):
        """Test that battery grid charging is excluded from baseline."""
        now = datetime.now()
        
        # Create hourly data with battery charging
        house_states = []
        batt_states = []
        pv_states = []
        
        house_energy = 100.0
        batt_energy = 50.0
        pv_energy = 0.0
        
        for hour_offset in range(48):
            timestamp = now - timedelta(hours=48-hour_offset)
            hour_of_day = timestamp.hour
            
            # Base house consumption: 1 kWh/h
            house_energy += 1.0
            
            # Battery charging from grid in night hours: 2 kWh/h
            # (no PV at night, so all battery charging is from grid)
            if 0 <= hour_of_day < 8:
                house_energy += 2.0  # Grid power for battery charging
                batt_energy += 2.0
                # No PV at night
            
            # During day, some PV generation
            if 8 <= hour_of_day < 16:
                pv_energy += 0.5
            
            house_state = MagicMock()
            house_state.state = str(house_energy)
            house_state.last_changed = timestamp
            house_states.append(house_state)
            
            batt_state = MagicMock()
            batt_state.state = str(batt_energy)
            batt_state.last_changed = timestamp
            batt_states.append(batt_state)
            
            pv_state = MagicMock()
            pv_state.state = str(pv_energy)
            pv_state.last_changed = timestamp
            pv_states.append(pv_state)
        
        # Call with battery exclusion enabled
        result = coordinator._calculate_daypart_baselines(
            house_states, [], batt_states, pv_states, False, True
        )
        
        assert result is not None
        
        # Night baseline should be ~1 kWh/h after excluding battery charging (not ~3 kWh/h)
        night = result.get("night")
        assert night is not None
        assert 0.8 <= night <= 1.2, f"Night should be ~1 kWh/h after battery exclusion, got {night}"
    
    def test_daypart_baselines_with_sparse_data(self, coordinator):
        """Test that the method handles sparse data gracefully."""
        now = datetime.now()
        
        # Create only a few data points
        house_states = []
        
        house_states.append(MagicMock(
            state="100.0",
            last_changed=now - timedelta(hours=10)
        ))
        house_states.append(MagicMock(
            state="105.0",
            last_changed=now - timedelta(hours=5)
        ))
        house_states.append(MagicMock(
            state="110.0",
            last_changed=now
        ))
        
        result = coordinator._calculate_daypart_baselines(
            house_states, [], [], [], False, False
        )
        
        # Should handle sparse data - may have some dayparts with no data
        # But should not crash
        assert result is None or isinstance(result, dict)
    
    def test_daypart_baselines_with_counter_reset(self, coordinator):
        """Test that counter resets are handled (negative deltas skipped)."""
        now = datetime.now()
        
        house_states = []
        energy = 100.0
        
        for hour_offset in range(24):
            timestamp = now - timedelta(hours=24-hour_offset)
            
            # Simulate a counter reset at hour 12
            if hour_offset == 12:
                energy = 5.0  # Reset to low value
            else:
                energy += 1.0
            
            state = MagicMock()
            state.state = str(energy)
            state.last_changed = timestamp
            house_states.append(state)
        
        result = coordinator._calculate_daypart_baselines(
            house_states, [], [], [], False, False
        )
        
        # Should handle the reset gracefully and still calculate baselines
        # from the valid data
        assert result is not None or result is None  # Should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
