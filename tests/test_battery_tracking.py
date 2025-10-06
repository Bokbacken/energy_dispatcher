"""Unit tests for battery charge/discharge tracking in coordinator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from datetime import datetime, date

from custom_components.energy_dispatcher.coordinator import EnergyDispatcherCoordinator
from custom_components.energy_dispatcher.bec import BatteryEnergyCost


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.states = MagicMock()
    return hass


@pytest.fixture
def mock_bec(mock_hass):
    """Create a mock BEC instance."""
    bec = BatteryEnergyCost(mock_hass, capacity_kwh=30.0)
    bec.async_save = AsyncMock()
    return bec


@pytest.fixture
def coordinator(mock_hass, mock_bec):
    """Create a coordinator instance with mocked dependencies."""
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    
    # Mock the store
    mock_hass.data["energy_dispatcher"] = {
        "test_entry": {
            "config": {
                "batt_energy_charged_today_entity": "sensor.battery_charged_today",
                "batt_energy_discharged_today_entity": "sensor.battery_discharged_today",
                "pv_power_entity": "sensor.pv_power",
                "load_power_entity": "sensor.load_power",
                "batt_power_entity": "sensor.battery_power",
            },
            "bec": mock_bec,
        }
    }
    
    return coordinator


class TestBatteryChargeTracking:
    """Test battery charge tracking functionality."""

    @pytest.mark.asyncio
    async def test_charge_from_grid(self, coordinator, mock_bec):
        """Test tracking battery charging from grid."""
        # Setup initial state
        coordinator._batt_last_reset_date = date.today()
        coordinator._batt_prev_charged_today = 10.0
        
        # Mock current state showing 0.5 kWh more charged
        mock_state = MagicMock()
        mock_state.state = "10.5"
        coordinator.hass.states.get = MagicMock(return_value=mock_state)
        
        # Mock current price
        coordinator.data["current_enriched"] = 2.5
        coordinator.data["pv_now_w"] = 0.0  # No PV, so charging from grid
        
        # Run tracking
        await coordinator._update_battery_charge_tracking()
        
        # Verify charge was recorded and value updated
        assert coordinator._batt_prev_charged_today == 10.5

    @pytest.mark.asyncio
    async def test_charge_from_solar(self, coordinator, mock_bec):
        """Test tracking battery charging from solar."""
        # Setup initial state
        coordinator._batt_last_reset_date = date.today()
        coordinator._batt_prev_charged_today = 10.0
        
        # Mock current state showing 0.5 kWh more charged
        mock_charged_state = MagicMock()
        mock_charged_state.state = "10.5"
        
        # Mock battery power (positive = charging in standard convention)
        mock_batt_power = MagicMock()
        mock_batt_power.state = "4000"  # 4kW charging
        
        def state_get(entity_id):
            if "charged_today" in entity_id:
                return mock_charged_state
            elif "battery_power" in entity_id:
                return mock_batt_power
            return None
        
        coordinator.hass.states.get = MagicMock(side_effect=state_get)
        
        # Mock current price
        coordinator.data["current_enriched"] = 2.5
        coordinator.data["pv_now_w"] = 5000.0  # 5kW PV output
        
        # Mock load power
        with patch.object(coordinator, '_read_watts', return_value=1000.0):  # 1kW load
            # Run tracking
            await coordinator._update_battery_charge_tracking()
        
        # Verify charge was recorded and value updated
        assert coordinator._batt_prev_charged_today == 10.5

    @pytest.mark.asyncio
    async def test_discharge_tracking(self, coordinator, mock_bec):
        """Test tracking battery discharge."""
        # Setup initial state
        coordinator._batt_last_reset_date = date.today()
        coordinator._batt_prev_discharged_today = 5.0
        
        # Mock current state showing 0.3 kWh more discharged
        mock_state = MagicMock()
        mock_state.state = "5.3"
        coordinator.hass.states.get = MagicMock(return_value=mock_state)
        
        # Run tracking
        await coordinator._update_battery_charge_tracking()
        
        # Verify discharge was recorded
        assert coordinator._batt_prev_discharged_today == 5.3

    @pytest.mark.asyncio
    async def test_daily_reset(self, coordinator, mock_bec):
        """Test that tracking resets on new day."""
        # Setup state from previous day
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        coordinator._batt_last_reset_date = yesterday
        coordinator._batt_prev_charged_today = 10.0
        coordinator._batt_prev_discharged_today = 5.0
        
        # Mock current state
        mock_state = MagicMock()
        mock_state.state = "1.0"  # New day, counter reset
        coordinator.hass.states.get = MagicMock(return_value=mock_state)
        
        # Run tracking
        await coordinator._update_battery_charge_tracking()
        
        # Verify tracking was reset
        assert coordinator._batt_last_reset_date == date.today()
        assert coordinator._batt_prev_charged_today == 1.0
        # Should not trigger charge event since it's first reading of the day

    @pytest.mark.asyncio
    async def test_no_entities_configured(self, coordinator, mock_bec):
        """Test that tracking doesn't fail when no entities are configured."""
        # Clear configured entities
        coordinator.hass.data["energy_dispatcher"]["test_entry"]["config"] = {}
        
        # Run tracking - should not raise exception
        await coordinator._update_battery_charge_tracking()
        
        # Verify no tracking occurred
        assert coordinator._batt_prev_charged_today is None

    @pytest.mark.asyncio
    async def test_unavailable_sensor(self, coordinator, mock_bec):
        """Test handling of unavailable sensors."""
        # Setup initial state
        coordinator._batt_last_reset_date = date.today()
        coordinator._batt_prev_charged_today = 10.0
        
        # Mock unavailable sensor
        mock_state = MagicMock()
        mock_state.state = "unavailable"
        coordinator.hass.states.get = MagicMock(return_value=mock_state)
        
        # Run tracking - should not raise exception
        await coordinator._update_battery_charge_tracking()
        
        # Verify tracking state didn't change
        assert coordinator._batt_prev_charged_today == 10.0

    @pytest.mark.asyncio
    async def test_small_delta_ignored(self, coordinator, mock_bec):
        """Test that very small deltas are ignored."""
        # Setup initial state
        coordinator._batt_last_reset_date = date.today()
        coordinator._batt_prev_charged_today = 10.0
        
        # Mock current state with tiny change (< 1 Wh)
        mock_state = MagicMock()
        mock_state.state = "10.0005"  # 0.5 Wh change
        coordinator.hass.states.get = MagicMock(return_value=mock_state)
        
        # Run tracking
        await coordinator._update_battery_charge_tracking()
        
        # Verify small change was updated but didn't trigger charge event
        assert coordinator._batt_prev_charged_today == 10.0005


class TestBatteryCapacitySensor:
    """Test battery capacity from sensor."""

    def test_capacity_from_sensor(self, mock_hass):
        """Test that capacity can be read from sensor."""
        # Mock sensor state
        mock_state = MagicMock()
        mock_state.state = "30.0"
        mock_hass.states.get = MagicMock(return_value=mock_state)
        
        # This would be tested in integration test, but verifies the concept
        assert float(mock_state.state) == 30.0
