"""Integration tests for BEC module with Home Assistant."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.energy_dispatcher.bec import BatteryEnergyCost


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance with services."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = AsyncMock()
    return hass


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    @pytest.mark.asyncio
    async def test_initialization_and_persistence(self, mock_hass):
        """Test that BEC initializes and persists correctly."""
        # Create BEC instance
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        
        # Simulate storage
        storage = {}
        
        async def mock_save(data):
            storage.update(data)
            
        async def mock_load():
            return storage if storage else None
            
        bec.store.async_save = mock_save
        bec.store.async_load = mock_load
        
        # Perform operations
        bec.on_charge(5.0, 2.0)
        bec.on_charge(5.0, 3.0)
        
        # Save
        await bec.async_save()
        
        # Verify storage
        assert storage["energy_kwh"] == 10.0
        assert storage["wace"] == pytest.approx(2.5)
        
        # Create new instance and load
        new_bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        new_bec.store.async_load = mock_load
        await new_bec.async_load()
        
        # Verify state was restored
        assert new_bec.energy_kwh == 10.0
        assert new_bec.wace == pytest.approx(2.5)
        assert new_bec.get_soc() == pytest.approx(66.67, rel=0.01)

    @pytest.mark.asyncio
    async def test_service_call_reset_cost(self, mock_hass):
        """Test battery cost reset service behavior."""
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        
        # Charge battery
        bec.on_charge(10.0, 2.5)
        assert bec.wace == 2.5
        assert bec.energy_kwh == 10.0
        
        # Reset cost (simulating service call)
        bec.reset_cost()
        
        # Verify
        assert bec.wace == 0.0
        assert bec.energy_kwh == 10.0  # Energy preserved

    @pytest.mark.asyncio
    async def test_service_call_set_soc(self, mock_hass):
        """Test manual SOC override service behavior."""
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        
        # Set initial state
        bec.on_charge(5.0, 2.0)
        original_wace = bec.wace
        
        # Manually set SOC (simulating service call)
        bec.set_soc(80.0)
        
        # Verify
        assert bec.get_soc() == 80.0
        assert bec.energy_kwh == 12.0
        assert bec.wace == original_wace  # Cost preserved

    @pytest.mark.asyncio
    async def test_sensor_data_flow(self, mock_hass):
        """Test that sensor can read BEC data correctly."""
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        
        # Simulate charging
        bec.on_charge(7.5, 2.0)
        
        # Verify sensor would read correct values
        assert bec.wace == 2.0
        assert bec.energy_kwh == 7.5
        assert bec.get_soc() == 50.0
        assert bec.get_total_cost() == 15.0  # 7.5 kWh * 2.0 SEK/kWh

    @pytest.mark.asyncio
    async def test_realistic_daily_cycle_with_persistence(self, mock_hass):
        """Test a realistic daily cycle with saves."""
        # Simulate storage
        storage = {}
        
        async def mock_save(data):
            storage.update(data)
            
        async def mock_load():
            return storage if storage else None
        
        # Morning: Start from previous day's state
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        bec.store.async_save = mock_save
        bec.store.async_load = mock_load
        
        # Load previous state (30% charged @ 1.5 SEK/kWh)
        storage["energy_kwh"] = 4.5
        storage["wace"] = 1.5
        await bec.async_load()
        
        # Morning: Charge from grid (expensive)
        bec.on_charge(5.5, 3.0)  # Now at 66.67%
        await bec.async_save()
        
        # Midday: Charge from solar (cheap)
        bec.on_charge(5.0, 0.5)  # Now at 100%
        await bec.async_save()
        
        # Calculate expected WACE: (4.5*1.5 + 5.5*3.0 + 5.0*0.5) / 15 = 25.75 / 15 ≈ 1.7167
        assert bec.get_soc() == 100.0
        assert bec.wace == pytest.approx(1.7167, rel=0.001)
        
        # Evening: Discharge
        bec.on_discharge(10.0)  # Down to 33.33%
        await bec.async_save()
        
        # Verify final state
        assert bec.get_soc() == pytest.approx(33.33, rel=0.01)
        assert bec.energy_kwh == 5.0
        assert bec.wace == pytest.approx(1.7167, rel=0.001)  # WACE unchanged

    @pytest.mark.asyncio
    async def test_manual_override_workflow_with_save(self, mock_hass):
        """Test manual override and cost reset workflow."""
        storage = {}
        
        async def mock_save(data):
            storage.update(data)
            
        async def mock_load():
            return storage if storage else None
        
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        bec.store.async_save = mock_save
        bec.store.async_load = mock_load
        
        # Initial charge
        bec.on_charge(5.0, 2.0)
        await bec.async_save()
        
        # User notices SOC is wrong, manually overrides
        bec.set_soc(60.0)  # Set to 60% = 9 kWh
        await bec.async_save()
        
        assert bec.energy_kwh == 9.0
        assert bec.wace == 2.0  # Cost preserved
        
        # User wants to reset cost tracking
        bec.reset_cost()
        await bec.async_save()
        
        assert bec.wace == 0.0
        assert bec.energy_kwh == 9.0
        
        # Continue with fresh cost tracking
        bec.on_charge(6.0, 1.5)
        await bec.async_save()
        
        # WACE should only consider new charge
        # (9*0 + 6*1.5) / 15 = 0.6
        assert bec.wace == pytest.approx(0.6)
        assert bec.get_soc() == 100.0
