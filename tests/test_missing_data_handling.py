"""Unit tests for missing data handling and interpolation."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.energy_dispatcher.coordinator import (
    _interpolate_energy_value,
    _is_data_stale,
    _fill_missing_hourly_data,
    EnergyDispatcherCoordinator,
)
from homeassistant.util import dt as dt_util


class TestInterpolation:
    """Test energy value interpolation."""
    
    def test_interpolate_midpoint(self):
        """Test interpolation at exact midpoint."""
        prev_time = datetime(2024, 1, 1, 10, 0)
        next_time = datetime(2024, 1, 1, 12, 0)
        mid_time = datetime(2024, 1, 1, 11, 0)
        
        result = _interpolate_energy_value(mid_time, prev_time, 100.0, next_time, 110.0)
        assert result == pytest.approx(105.0)
    
    def test_interpolate_quarter_point(self):
        """Test interpolation at 1/4 point."""
        prev_time = datetime(2024, 1, 1, 10, 0)
        next_time = datetime(2024, 1, 1, 14, 0)
        quarter_time = datetime(2024, 1, 1, 11, 0)
        
        result = _interpolate_energy_value(quarter_time, prev_time, 100.0, next_time, 120.0)
        assert result == pytest.approx(105.0)  # 100 + 0.25 * 20
    
    def test_interpolate_three_quarter_point(self):
        """Test interpolation at 3/4 point."""
        prev_time = datetime(2024, 1, 1, 10, 0)
        next_time = datetime(2024, 1, 1, 14, 0)
        three_quarter_time = datetime(2024, 1, 1, 13, 0)
        
        result = _interpolate_energy_value(three_quarter_time, prev_time, 100.0, next_time, 120.0)
        assert result == pytest.approx(115.0)  # 100 + 0.75 * 20
    
    def test_interpolate_counter_reset_returns_none(self):
        """Test that interpolation fails for counter resets."""
        prev_time = datetime(2024, 1, 1, 10, 0)
        next_time = datetime(2024, 1, 1, 12, 0)
        mid_time = datetime(2024, 1, 1, 11, 0)
        
        # Counter reset (next value < previous value)
        result = _interpolate_energy_value(mid_time, prev_time, 100.0, next_time, 50.0)
        assert result is None
    
    def test_interpolate_invalid_timestamp_returns_none(self):
        """Test that interpolation fails for timestamps outside range."""
        prev_time = datetime(2024, 1, 1, 10, 0)
        next_time = datetime(2024, 1, 1, 12, 0)
        
        # Before range
        before_time = datetime(2024, 1, 1, 9, 0)
        result = _interpolate_energy_value(before_time, prev_time, 100.0, next_time, 110.0)
        assert result is None
        
        # After range
        after_time = datetime(2024, 1, 1, 13, 0)
        result = _interpolate_energy_value(after_time, prev_time, 100.0, next_time, 110.0)
        assert result is None
    
    def test_interpolate_zero_time_delta_returns_none(self):
        """Test that interpolation fails when times are equal."""
        same_time = datetime(2024, 1, 1, 10, 0)
        target_time = datetime(2024, 1, 1, 10, 30)
        
        result = _interpolate_energy_value(target_time, same_time, 100.0, same_time, 110.0)
        assert result is None


class TestDataStaleness:
    """Test data staleness checking."""
    
    def test_none_is_stale(self):
        """Test that None timestamp is considered stale."""
        assert _is_data_stale(None) is True
    
    def test_fresh_data_not_stale(self):
        """Test that recent data is not stale."""
        now = dt_util.now()
        recent = now - timedelta(minutes=5)
        assert _is_data_stale(recent, max_age_minutes=15) is False
    
    def test_old_data_is_stale(self):
        """Test that old data is stale."""
        now = dt_util.now()
        old = now - timedelta(minutes=20)
        assert _is_data_stale(old, max_age_minutes=15) is True
    
    def test_exactly_at_threshold(self):
        """Test data exactly at threshold."""
        now = dt_util.now()
        at_threshold = now - timedelta(minutes=15)
        # Exactly at threshold should be stale (age > max_age)
        assert _is_data_stale(at_threshold, max_age_minutes=15) is True
        
        # Just under threshold should not be stale
        just_under = now - timedelta(minutes=14, seconds=59)
        assert _is_data_stale(just_under, max_age_minutes=15) is False
    
    def test_custom_threshold(self):
        """Test with custom staleness threshold."""
        now = dt_util.now()
        old = now - timedelta(minutes=65)
        
        # With 60 minute threshold, should be stale
        assert _is_data_stale(old, max_age_minutes=60) is True
        
        # With 70 minute threshold, should not be stale
        assert _is_data_stale(old, max_age_minutes=70) is False


class TestFillMissingHourlyData:
    """Test filling missing hourly data points."""
    
    def test_no_gaps_returns_same(self):
        """Test that continuous data is returned unchanged."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {
            base_time: 100.0,
            base_time + timedelta(hours=1): 105.0,
            base_time + timedelta(hours=2): 110.0,
        }
        
        result = _fill_missing_hourly_data(time_index)
        assert len(result) == 3
        assert result == time_index
    
    def test_fills_single_gap(self):
        """Test filling a single missing hour."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {
            base_time: 100.0,
            base_time + timedelta(hours=2): 110.0,  # Missing hour 11
        }
        
        result = _fill_missing_hourly_data(time_index)
        assert len(result) == 3
        
        # Check interpolated value
        mid_time = base_time + timedelta(hours=1)
        assert mid_time in result
        assert result[mid_time] == pytest.approx(105.0)
    
    def test_fills_multiple_gaps(self):
        """Test filling multiple missing hours."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {
            base_time: 100.0,
            base_time + timedelta(hours=4): 120.0,  # Missing hours 11, 12, 13
        }
        
        result = _fill_missing_hourly_data(time_index)
        assert len(result) == 5
        
        # Check interpolated values
        assert result[base_time + timedelta(hours=1)] == pytest.approx(105.0)
        assert result[base_time + timedelta(hours=2)] == pytest.approx(110.0)
        assert result[base_time + timedelta(hours=3)] == pytest.approx(115.0)
    
    def test_respects_max_gap_limit(self):
        """Test that gaps larger than max are not filled."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {
            base_time: 100.0,
            base_time + timedelta(hours=10): 150.0,  # 10-hour gap
        }
        
        # With default 8-hour max gap, should not fill
        result = _fill_missing_hourly_data(time_index, max_gap_hours=8.0)
        assert len(result) == 2  # No interpolation
        assert base_time in result
        assert base_time + timedelta(hours=10) in result
    
    def test_fills_within_max_gap(self):
        """Test that gaps within max are filled."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {
            base_time: 100.0,
            base_time + timedelta(hours=5): 125.0,  # 5-hour gap
        }
        
        # With 8-hour max gap, should fill
        result = _fill_missing_hourly_data(time_index, max_gap_hours=8.0)
        assert len(result) == 6  # 5 hours + 1 original end
        
        # Check all interpolated values exist
        for i in range(1, 5):
            assert base_time + timedelta(hours=i) in result
    
    def test_handles_empty_dict(self):
        """Test handling of empty input."""
        result = _fill_missing_hourly_data({})
        assert result == {}
    
    def test_handles_single_point(self):
        """Test handling of single data point."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {base_time: 100.0}
        
        result = _fill_missing_hourly_data(time_index)
        assert len(result) == 1
        assert result == time_index
    
    def test_preserves_existing_values(self):
        """Test that existing values are not modified."""
        base_time = datetime(2024, 1, 1, 10, 0)
        time_index = {
            base_time: 100.0,
            base_time + timedelta(hours=1): 103.0,  # Not exactly interpolated value
            base_time + timedelta(hours=2): 110.0,
        }
        
        result = _fill_missing_hourly_data(time_index)
        
        # Should preserve the original value at hour 1
        assert result[base_time + timedelta(hours=1)] == 103.0


class TestBECGapHandling:
    """Test BEC tracking with data gaps."""
    
    @pytest.mark.asyncio
    async def test_resets_tracking_after_1_hour_gap(self):
        """Test that BEC tracking resets after 1-hour gap."""
        # Create mock hass
        hass = MagicMock()
        hass.data = {}
        
        # Create coordinator
        coordinator = EnergyDispatcherCoordinator(hass)
        coordinator.entry_id = "test_entry"
        
        # Mock BEC in store
        mock_bec = MagicMock()
        hass.data["energy_dispatcher"] = {
            "test_entry": {
                "config": {
                    "batt_energy_charged_today_entity": "sensor.battery_charged",
                    "batt_energy_discharged_today_entity": "sensor.battery_discharged",
                },
                "bec": mock_bec,
            }
        }
        
        # Set up initial state
        now = dt_util.now()
        coordinator._batt_last_update_time = now - timedelta(minutes=65)  # 65 minutes ago
        coordinator._batt_prev_charged_today = 10.0
        
        # Mock sensors with new values
        charged_state = MagicMock()
        charged_state.state = "15.0"
        discharged_state = MagicMock()
        discharged_state.state = "5.0"
        
        hass.states.get = MagicMock(side_effect=lambda entity_id: {
            "sensor.battery_charged": charged_state,
            "sensor.battery_discharged": discharged_state,
        }.get(entity_id))
        
        # Run battery tracking
        await coordinator._update_battery_charge_tracking()
        
        # Should have reset tracking (prev_charged should be None initially after reset)
        # But then set to current value
        assert coordinator._batt_prev_charged_today == 15.0
        
        # Should not have called on_charge because tracking was reset
        mock_bec.on_charge.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_tracks_normally_within_1_hour(self):
        """Test that BEC tracking works normally within 1-hour window."""
        # Create mock hass
        hass = MagicMock()
        hass.data = {}
        
        # Create coordinator
        coordinator = EnergyDispatcherCoordinator(hass)
        coordinator.entry_id = "test_entry"
        
        # Mock BEC in store
        mock_bec = MagicMock()
        mock_bec.async_save = AsyncMock()
        hass.data["energy_dispatcher"] = {
            "test_entry": {
                "config": {
                    "batt_energy_charged_today_entity": "sensor.battery_charged",
                },
                "bec": mock_bec,
            }
        }
        
        # Set up initial state (30 minutes ago - within limit)
        now = dt_util.now()
        coordinator._batt_last_update_time = now - timedelta(minutes=30)
        coordinator._batt_prev_charged_today = 10.0
        coordinator._batt_last_reset_date = now.date()
        
        # Mock sensor with new value
        charged_state = MagicMock()
        charged_state.state = "15.0"
        
        hass.states.get = MagicMock(return_value=charged_state)
        
        # Mock current price
        coordinator.data["current_enriched"] = 2.5
        
        # Run battery tracking
        await coordinator._update_battery_charge_tracking()
        
        # Should have tracked the charge delta
        assert coordinator._batt_prev_charged_today == 15.0
        
        # Should have called on_charge with the delta
        mock_bec.on_charge.assert_called_once()
        call_args = mock_bec.on_charge.call_args[0]
        assert call_args[0] == pytest.approx(5.0)  # delta_charged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
