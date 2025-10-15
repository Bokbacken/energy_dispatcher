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
                "runtime_counter_entity": "sensor.house_energy",
                "evse_total_energy_sensor": "sensor.ev_energy",
                "batt_total_charged_energy_entity": "sensor.battery_charged_energy",
                "pv_total_energy_entity": "sensor.pv_total_energy",
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
    async def test_no_counter_configured(self, coordinator, mock_hass):
        """Test diagnostic reason when no energy counter is configured."""
        # Remove counter entity from config
        mock_hass.data["energy_dispatcher"]["test_entry"]["config"]["runtime_counter_entity"] = ""
        
        result = await coordinator._calculate_48h_baseline()
        assert result is not None
        assert result.get("overall") is None
        assert result.get("failure_reason") == "No house energy counter configured (runtime_counter_entity)"
    
    @pytest.mark.asyncio
    async def test_no_historical_data(self, coordinator, mock_hass):
        """Test that diagnostic reason is returned when no historical data is available."""
        # Mock empty history
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value={})
            
            result = await coordinator._calculate_48h_baseline()
            assert result is not None
            assert result.get("overall") is None
            assert result.get("failure_reason") == "Insufficient historical data: 0 data points (need 2+)"
    
    @pytest.mark.asyncio
    async def test_invalid_sensor_values(self, coordinator, mock_hass):
        """Test diagnostic reason when sensor values are invalid (unknown/unavailable)."""
        now = datetime.now()
        
        # House energy counter with invalid values
        house_states = []
        start_state = MagicMock()
        start_state.state = "unknown"
        start_state.last_changed = now - timedelta(hours=48)
        house_states.append(start_state)
        
        end_state = MagicMock()
        end_state.state = "unavailable"
        end_state.last_changed = now
        house_states.append(end_state)
        
        history_data = {
            "sensor.house_energy": house_states
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            assert result is not None
            assert result.get("overall") is None
            assert "Invalid sensor values" in result.get("failure_reason", "")
    
    @pytest.mark.asyncio
    async def test_baseline_calculation_with_data(self, coordinator, mock_hass):
        """Test baseline calculation with energy counter data."""
        # Create mock state objects for energy counters
        now = datetime.now()
        
        # House energy counter: start at 100 kWh, end at 148 kWh (48 kWh consumed over 48h = 1 kWh/h)
        house_states = []
        start_state = MagicMock()
        start_state.state = "100.0"
        start_state.last_changed = now - timedelta(hours=48)
        house_states.append(start_state)
        
        end_state = MagicMock()
        end_state.state = "148.0"
        end_state.last_changed = now
        house_states.append(end_state)
        
        # Mock history response
        history_data = {
            "sensor.house_energy": house_states
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Should have results
            assert result is not None
            assert "overall" in result
            assert "night" in result
            assert "day" in result
            assert "evening" in result
            
            # Overall should be approximately 1 kWh/h (48 kWh / 48 hours)
            if result["overall"]:
                assert 0.9 <= result["overall"] <= 1.1
    
    @pytest.mark.asyncio
    async def test_exclusion_of_ev_charging(self, coordinator, mock_hass):
        """Test that EV charging energy is excluded from baseline."""
        now = datetime.now()
        
        # House energy counter: 100 kWh -> 158 kWh (58 kWh consumed over 48h)
        house_states = []
        house_start = MagicMock()
        house_start.state = "100.0"
        house_start.last_changed = now - timedelta(hours=48)
        house_states.append(house_start)
        
        house_end = MagicMock()
        house_end.state = "158.0"
        house_end.last_changed = now
        house_states.append(house_end)
        
        # EV energy counter: 50 kWh -> 60 kWh (10 kWh charged)
        ev_states = []
        ev_start = MagicMock()
        ev_start.state = "50.0"
        ev_start.last_changed = now - timedelta(hours=48)
        ev_states.append(ev_start)
        
        ev_end = MagicMock()
        ev_end.state = "60.0"
        ev_end.last_changed = now
        ev_states.append(ev_end)
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.ev_energy": ev_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Should exclude EV charging: (58 - 10) / 48 = 1 kWh/h
            assert result is not None
            if result["overall"]:
                assert 0.9 <= result["overall"] <= 1.1


class TestDaypartCalculation:
    """Test daypart-specific baseline calculation."""
    
    @pytest.mark.asyncio
    async def test_daypart_baselines_differ(self, coordinator, mock_hass):
        """Test that daypart baselines show different values based on time of day."""
        now = datetime.now()
        
        # Create hourly data with different consumption patterns by time of day
        house_states = []
        
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
        
        history_data = {
            "sensor.house_energy": house_states
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            assert result is not None
            assert result.get("night") is not None
            assert result.get("day") is not None
            assert result.get("evening") is not None
            
            # Verify that the values are different
            night = result["night"]
            day = result["day"]
            evening = result["evening"]
            
            # Night should be lowest
            assert night < day
            assert night < evening
            
            # Evening should be highest
            assert evening > day
            assert evening > night
            
            # Check approximate values (with tolerance for calculation)
            assert 0.4 <= night <= 0.6  # ~0.5 kWh/h
            assert 0.9 <= day <= 1.1    # ~1.0 kWh/h
            assert 1.8 <= evening <= 2.2  # ~2.0 kWh/h
    
    @pytest.mark.asyncio
    async def test_daypart_exclusions_work(self, coordinator, mock_hass):
        """Test that EV and battery exclusions affect daypart baselines."""
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
            
            # EV charging in evening (16:00-23:59): 3 kWh/h
            # House counter includes EV consumption
            if 16 <= hour_of_day < 24:
                ev_energy += 3.0
                house_energy += 3.0  # EV consumption is part of house total
            
            house_state = MagicMock()
            house_state.state = str(house_energy)
            house_state.last_changed = timestamp
            house_states.append(house_state)
            
            ev_state = MagicMock()
            ev_state.state = str(ev_energy)
            ev_state.last_changed = timestamp
            ev_states.append(ev_state)
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.ev_energy": ev_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            assert result is not None
            
            # Without EV charging, evening would show ~4 kWh/h
            # With EV exclusion, evening should show ~1 kWh/h
            evening = result.get("evening")
            assert evening is not None
            assert 0.8 <= evening <= 1.2  # Should be close to 1 kWh/h after exclusion
            
            # Night and day should not be affected (no EV charging)
            night = result.get("night")
            day = result.get("day")
            assert night is not None
            assert day is not None
            assert 0.8 <= night <= 1.2
            assert 0.8 <= day <= 1.2


class TestEnergyCounterBaseline:
    """Test energy counter-based baseline calculation."""
    
    @pytest.mark.asyncio
    async def test_baseline_with_counter_reset(self, coordinator, mock_hass):
        """Test that counter resets are handled correctly."""
        now = datetime.now()
        
        # House energy counter with reset: 500 kWh -> 10 kWh (counter reset at midnight)
        house_states = []
        house_start = MagicMock()
        house_start.state = "500.0"
        house_start.last_changed = now - timedelta(hours=48)
        house_states.append(house_start)
        
        house_end = MagicMock()
        house_end.state = "10.0"  # Counter reset
        house_end.last_changed = now
        house_states.append(house_end)
        
        history_data = {
            "sensor.house_energy": house_states
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Should use end value as approximation: 10 / 48 ≈ 0.21 kWh/h
            assert result is not None
            if result["overall"]:
                assert 0.15 <= result["overall"] <= 0.25
    
    @pytest.mark.asyncio
    async def test_baseline_with_battery_exclusion(self, coordinator, mock_hass):
        """Test that battery grid charging is excluded."""
        now = datetime.now()
        
        # House: 100 -> 170 kWh (70 kWh)
        house_states = [
            MagicMock(state="100.0", last_changed=now - timedelta(hours=48)),
            MagicMock(state="170.0", last_changed=now)
        ]
        
        # Battery charged: 20 -> 40 kWh (20 kWh charged)
        batt_states = [
            MagicMock(state="20.0", last_changed=now - timedelta(hours=48)),
            MagicMock(state="40.0", last_changed=now)
        ]
        
        # PV generated: 0 -> 10 kWh (10 kWh from solar)
        pv_states = [
            MagicMock(state="0.0", last_changed=now - timedelta(hours=48)),
            MagicMock(state="10.0", last_changed=now)
        ]
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.battery_charged_energy": batt_states,
            "sensor.pv_total_energy": pv_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Should exclude battery grid charging: (70 - (20 - 10)) / 48 = 60 / 48 = 1.25 kWh/h
            assert result is not None
            if result["overall"]:
                assert 1.2 <= result["overall"] <= 1.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
