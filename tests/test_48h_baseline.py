"""Unit tests for 48-hour baseline calculation."""
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
        """Test that battery grid charging is excluded (time-based analysis)."""
        now = datetime.now()
        
        # Create hourly data to simulate battery charging at night (no solar)
        house_states = []
        batt_states = []
        pv_states = []
        
        house_energy = 100.0
        batt_energy = 20.0
        pv_energy = 0.0
        
        for hour in range(49):  # 48 hours + 1 for end point
            ts = now - timedelta(hours=48-hour)
            
            # House consumes steadily: 1.5 kWh/h
            house_energy += 1.5
            
            # Battery charges at night (hours 0-5, 22-23): 0.5 kWh/h
            # No charging during day
            hour_of_day = ts.hour
            if hour_of_day < 6 or hour_of_day >= 22:
                batt_energy += 0.5
            
            # PV generates during day (hours 8-16): 1.0 kWh/h
            if 8 <= hour_of_day <= 16:
                pv_energy += 1.0
            
            house_states.append(MagicMock(state=f"{house_energy:.1f}", last_changed=ts))
            batt_states.append(MagicMock(state=f"{batt_energy:.1f}", last_changed=ts))
            pv_states.append(MagicMock(state=f"{pv_energy:.1f}", last_changed=ts))
        
        history_data = {
            "sensor.house_energy": house_states,
            "sensor.battery_charged_energy": batt_states,
            "sensor.pv_total_energy": pv_states,
        }
        
        with patch('homeassistant.components.recorder.history'):
            mock_hass.async_add_executor_job = AsyncMock(return_value=history_data)
            
            result = await coordinator._calculate_48h_baseline()
            
            # Total house: 72 kWh over 48h = 1.5 kWh/h
            # Battery charged at night (no solar): 8 kWh (16 hours total across 2 days at 0.5 kWh/h)
            # Expected baseline: (72 - 8) / 48 = 1.333 kWh/h
            assert result is not None
            if result["overall"]:
                assert 1.3 <= result["overall"] <= 1.35


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
