"""Test optimization plan diagnostic features."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch

from custom_components.energy_dispatcher.coordinator import EnergyDispatcherCoordinator
from custom_components.energy_dispatcher.models import PricePoint


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    hass.data = {}
    return hass


@pytest.fixture
def basic_config():
    """Create basic configuration data."""
    return {
        "nordpool_entity": "sensor.nordpool_kwh_se3_sek_3_10_025",
        "price_tax": 0.395,
        "price_transfer": 0.50,
        "price_surcharge": 0.10,
        "price_vat": 0.25,
        "batt_cap_kwh": 15.0,
        "batt_soc_entity": "sensor.battery_soc",
        "batt_max_charge_w": 4000,
        "cost_cheap_threshold": 1.5,
        "cost_high_threshold": 3.0,
    }


@pytest.mark.asyncio
async def test_optimization_plan_missing_price_data(mock_hass, basic_config):
    """Test that diagnostic status is set when price data is missing."""
    # Setup mock hass data structure
    mock_hass.data = {"energy_dispatcher": {"test_entry": {"config": basic_config}}}
    
    # Create coordinator with basic config
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    coordinator._config = basic_config
    
    # Ensure no price data
    coordinator.data["hourly_prices"] = []
    
    # Run plan update
    await coordinator._update_optimization_plan()
    
    # Verify diagnostic status
    assert coordinator.data["optimization_plan"] == []
    assert coordinator.data["optimization_plan_status"] == "missing_price_data"


@pytest.mark.asyncio
async def test_optimization_plan_missing_battery_soc_entity(mock_hass, basic_config):
    """Test that diagnostic status is set when battery SOC entity is missing."""
    # Create coordinator with config missing battery SOC entity
    config = basic_config.copy()
    config["batt_soc_entity"] = ""
    
    # Setup mock hass data structure
    mock_hass.data = {"energy_dispatcher": {"test_entry": {"config": config}}}
    
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    coordinator._config = config
    
    # Add price data
    base_time = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    coordinator.data["hourly_prices"] = [
        PricePoint(time=base_time + timedelta(hours=i), spot_sek_per_kwh=1.0, enriched_sek_per_kwh=2.0)
        for i in range(24)
    ]
    
    # Run plan update
    await coordinator._update_optimization_plan()
    
    # Verify diagnostic status
    assert coordinator.data["optimization_plan"] == []
    assert coordinator.data["optimization_plan_status"] == "missing_battery_soc_entity"


@pytest.mark.asyncio
async def test_optimization_plan_battery_soc_unavailable(mock_hass, basic_config):
    """Test that diagnostic status is set when battery SOC sensor is unavailable."""
    # Setup mock hass data structure
    mock_hass.data = {"energy_dispatcher": {"test_entry": {"config": basic_config}}}
    
    # Create coordinator
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    coordinator._config = basic_config
    
    # Add price data
    base_time = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    coordinator.data["hourly_prices"] = [
        PricePoint(time=base_time + timedelta(hours=i), spot_sek_per_kwh=1.0, enriched_sek_per_kwh=2.0)
        for i in range(24)
    ]
    
    # Mock battery SOC sensor as unavailable
    mock_state = Mock()
    mock_state.state = "unavailable"
    mock_hass.states.get.return_value = mock_state
    
    # Run plan update
    await coordinator._update_optimization_plan()
    
    # Verify diagnostic status
    assert coordinator.data["optimization_plan"] == []
    assert coordinator.data["optimization_plan_status"] == "battery_soc_unavailable"


@pytest.mark.asyncio
async def test_optimization_plan_invalid_battery_capacity(mock_hass, basic_config):
    """Test that diagnostic status is set when battery capacity is invalid."""
    # Create coordinator with invalid battery capacity
    config = basic_config.copy()
    config["batt_cap_kwh"] = 0
    
    # Setup mock hass data structure
    mock_hass.data = {"energy_dispatcher": {"test_entry": {"config": config}}}
    
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    coordinator._config = config
    
    # Add price data
    base_time = datetime(2025, 1, 15, 0, 0, 0)
    coordinator.data["hourly_prices"] = [
        PricePoint(time=base_time + timedelta(hours=i), spot_sek_per_kwh=1.0, enriched_sek_per_kwh=2.0)
        for i in range(24)
    ]
    
    # Mock battery SOC sensor as available
    mock_state = Mock()
    mock_state.state = "50.0"
    mock_hass.states.get.return_value = mock_state
    
    # Run plan update
    await coordinator._update_optimization_plan()
    
    # Verify diagnostic status
    assert coordinator.data["optimization_plan"] == []
    assert coordinator.data["optimization_plan_status"] == "invalid_battery_capacity"


@pytest.mark.asyncio
async def test_optimization_plan_success(mock_hass, basic_config):
    """Test that plan is generated successfully with valid configuration."""
    # Setup mock hass data structure
    mock_hass.data = {"energy_dispatcher": {"test_entry": {"config": basic_config}}}
    
    # Create coordinator
    coordinator = EnergyDispatcherCoordinator(mock_hass)
    coordinator.entry_id = "test_entry"
    coordinator._config = basic_config
    
    # Add price data
    base_time = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    coordinator.data["hourly_prices"] = [
        PricePoint(time=base_time + timedelta(hours=i), spot_sek_per_kwh=1.0, enriched_sek_per_kwh=2.0)
        for i in range(24)
    ]
    coordinator.data["solar_points"] = []
    
    # Mock battery SOC sensor as available
    mock_state = Mock()
    mock_state.state = "50.0"
    mock_hass.states.get.return_value = mock_state
    
    # Run plan update
    await coordinator._update_optimization_plan()
    
    # Verify plan was generated
    assert len(coordinator.data["optimization_plan"]) > 0
    assert coordinator.data["optimization_plan_status"] == "ok"
