"""Unit tests for Battery Energy Cost (BEC) module."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.energy_dispatcher.bec import BatteryEnergyCost


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    return hass


@pytest.fixture
def bec(mock_hass):
    """Create a BatteryEnergyCost instance with default capacity."""
    return BatteryEnergyCost(mock_hass, capacity_kwh=15.0)


class TestInitialization:
    """Test BatteryEnergyCost initialization."""

    def test_init_valid_capacity(self, mock_hass):
        """Test initialization with valid capacity."""
        bec = BatteryEnergyCost(mock_hass, capacity_kwh=15.0)
        assert bec.capacity_kwh == 15.0
        assert bec.energy_kwh == 0.0
        assert bec.wace == 0.0

    def test_init_invalid_capacity_zero(self, mock_hass):
        """Test initialization with zero capacity raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            BatteryEnergyCost(mock_hass, capacity_kwh=0.0)

    def test_init_invalid_capacity_negative(self, mock_hass):
        """Test initialization with negative capacity raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            BatteryEnergyCost(mock_hass, capacity_kwh=-5.0)


class TestSOCSetting:
    """Test manual SOC setting functionality."""

    def test_set_soc_valid(self, bec):
        """Test setting SOC with valid percentage."""
        bec.set_soc(50.0)
        assert bec.energy_kwh == 7.5  # 50% of 15 kWh
        assert bec.get_soc() == 50.0

    def test_set_soc_zero(self, bec):
        """Test setting SOC to 0%."""
        bec.set_soc(0.0)
        assert bec.energy_kwh == 0.0
        assert bec.get_soc() == 0.0

    def test_set_soc_full(self, bec):
        """Test setting SOC to 100%."""
        bec.set_soc(100.0)
        assert bec.energy_kwh == 15.0
        assert bec.get_soc() == 100.0

    def test_set_soc_clamped_high(self, bec):
        """Test SOC values above 100% are clamped."""
        bec.set_soc(150.0)
        assert bec.energy_kwh == 15.0  # Clamped to 100%
        assert bec.get_soc() == 100.0

    def test_set_soc_clamped_low(self, bec):
        """Test SOC values below 0% are clamped."""
        bec.set_soc(-10.0)
        assert bec.energy_kwh == 0.0  # Clamped to 0%
        assert bec.get_soc() == 0.0

    def test_set_soc_preserves_wace(self, bec):
        """Test that manual SOC setting preserves WACE."""
        bec.wace = 2.5
        bec.set_soc(50.0)
        assert bec.wace == 2.5  # WACE unchanged


class TestCharging:
    """Test battery charging functionality."""

    def test_charge_from_empty(self, bec):
        """Test charging from empty battery."""
        bec.on_charge(5.0, 2.0)  # 5 kWh at 2 SEK/kWh
        assert bec.energy_kwh == 5.0
        assert bec.wace == 2.0

    def test_charge_multiple_events_same_cost(self, bec):
        """Test multiple charging events at same cost."""
        bec.on_charge(5.0, 2.0)
        bec.on_charge(5.0, 2.0)
        assert bec.energy_kwh == 10.0
        assert bec.wace == 2.0

    def test_charge_multiple_events_different_cost(self, bec):
        """Test multiple charging events at different costs."""
        bec.on_charge(5.0, 1.0)  # 5 kWh @ 1 SEK/kWh = 5 SEK
        bec.on_charge(5.0, 3.0)  # 5 kWh @ 3 SEK/kWh = 15 SEK
        # Total: 10 kWh, 20 SEK -> WACE = 2.0 SEK/kWh
        assert bec.energy_kwh == 10.0
        assert bec.wace == pytest.approx(2.0)

    def test_charge_weighted_average(self, bec):
        """Test weighted average calculation."""
        bec.on_charge(3.0, 1.5)  # 3 kWh @ 1.5 SEK/kWh = 4.5 SEK
        bec.on_charge(7.0, 2.5)  # 7 kWh @ 2.5 SEK/kWh = 17.5 SEK
        # Total: 10 kWh, 22 SEK -> WACE = 2.2 SEK/kWh
        assert bec.energy_kwh == 10.0
        assert bec.wace == pytest.approx(2.2)

    def test_charge_exceeds_capacity(self, bec):
        """Test charging beyond battery capacity."""
        bec.on_charge(20.0, 2.0)  # More than 15 kWh capacity
        assert bec.energy_kwh == 15.0  # Capped at capacity

    def test_charge_zero_delta(self, bec):
        """Test charging with zero delta is ignored."""
        bec.on_charge(0.0, 2.0)
        assert bec.energy_kwh == 0.0
        assert bec.wace == 0.0

    def test_charge_negative_delta(self, bec):
        """Test charging with negative delta is ignored."""
        bec.on_charge(-5.0, 2.0)
        assert bec.energy_kwh == 0.0
        assert bec.wace == 0.0


class TestDischarging:
    """Test battery discharging functionality."""

    def test_discharge_partial(self, bec):
        """Test partial discharge."""
        bec.on_charge(10.0, 2.0)
        bec.on_discharge(3.0)
        assert bec.energy_kwh == 7.0
        assert bec.wace == 2.0  # WACE unchanged

    def test_discharge_full(self, bec):
        """Test complete discharge."""
        bec.on_charge(10.0, 2.0)
        bec.on_discharge(10.0)
        assert bec.energy_kwh == 0.0
        assert bec.wace == 2.0  # WACE preserved

    def test_discharge_more_than_available(self, bec):
        """Test discharging more than available energy."""
        bec.on_charge(5.0, 2.0)
        bec.on_discharge(10.0)
        assert bec.energy_kwh == 0.0  # Cannot go negative
        assert bec.wace == 2.0

    def test_discharge_zero_delta(self, bec):
        """Test discharging with zero delta is ignored."""
        bec.on_charge(10.0, 2.0)
        bec.on_discharge(0.0)
        assert bec.energy_kwh == 10.0

    def test_discharge_negative_delta(self, bec):
        """Test discharging with negative delta is ignored."""
        bec.on_charge(10.0, 2.0)
        bec.on_discharge(-5.0)
        assert bec.energy_kwh == 10.0


class TestCostReset:
    """Test manual cost reset functionality."""

    def test_reset_cost_with_energy(self, bec):
        """Test resetting cost when battery has energy."""
        bec.on_charge(10.0, 2.5)
        bec.reset_cost()
        assert bec.wace == 0.0
        assert bec.energy_kwh == 10.0  # Energy unchanged

    def test_reset_cost_empty_battery(self, bec):
        """Test resetting cost when battery is empty."""
        bec.reset_cost()
        assert bec.wace == 0.0
        assert bec.energy_kwh == 0.0


class TestGetters:
    """Test getter methods."""

    def test_get_soc_empty(self, bec):
        """Test getting SOC when battery is empty."""
        assert bec.get_soc() == 0.0

    def test_get_soc_half(self, bec):
        """Test getting SOC when battery is half full."""
        bec.energy_kwh = 7.5
        assert bec.get_soc() == 50.0

    def test_get_soc_full(self, bec):
        """Test getting SOC when battery is full."""
        bec.energy_kwh = 15.0
        assert bec.get_soc() == 100.0

    def test_get_total_cost_zero(self, bec):
        """Test getting total cost when empty."""
        assert bec.get_total_cost() == 0.0

    def test_get_total_cost_with_energy(self, bec):
        """Test getting total cost with energy."""
        bec.on_charge(10.0, 2.0)  # 10 kWh @ 2 SEK/kWh = 20 SEK
        assert bec.get_total_cost() == pytest.approx(20.0)

    def test_get_total_cost_after_discharge(self, bec):
        """Test getting total cost after discharge."""
        bec.on_charge(10.0, 2.0)  # 10 kWh @ 2 SEK/kWh = 20 SEK
        bec.on_discharge(5.0)  # 5 kWh remaining @ 2 SEK/kWh = 10 SEK
        assert bec.get_total_cost() == pytest.approx(10.0)


class TestPersistence:
    """Test persistence functionality."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, bec):
        """Test saving and loading state."""
        # Set some state
        bec.on_charge(8.0, 2.5)
        
        # Mock the store
        saved_data = None
        
        async def mock_save(data):
            nonlocal saved_data
            saved_data = data
            
        async def mock_load():
            return saved_data
            
        bec.store.async_save = mock_save
        bec.store.async_load = mock_load
        
        # Save state
        result = await bec.async_save()
        assert result is True
        assert saved_data["energy_kwh"] == 8.0
        assert saved_data["wace"] == 2.5
        
        # Create new instance and load
        new_bec = BatteryEnergyCost(bec.hass, capacity_kwh=15.0)
        new_bec.store.async_load = mock_load
        result = await new_bec.async_load()
        assert result is True
        assert new_bec.energy_kwh == 8.0
        assert new_bec.wace == 2.5

    @pytest.mark.asyncio
    async def test_load_no_data(self, bec):
        """Test loading when no data exists."""
        async def mock_load():
            return None
            
        bec.store.async_load = mock_load
        result = await bec.async_load()
        assert result is False
        assert bec.energy_kwh == 0.0
        assert bec.wace == 0.0

    @pytest.mark.asyncio
    async def test_save_error_handling(self, bec):
        """Test error handling during save."""
        async def mock_save_error(data):
            raise Exception("Storage error")
            
        bec.store.async_save = mock_save_error
        result = await bec.async_save()
        assert result is False

    @pytest.mark.asyncio
    async def test_load_error_handling(self, bec):
        """Test error handling during load."""
        async def mock_load_error():
            raise Exception("Storage error")
            
        bec.store.async_load = mock_load_error
        result = await bec.async_load()
        assert result is False


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_daily_cycle(self, bec):
        """Test a typical daily charge/discharge cycle."""
        # Morning: charge from grid (expensive)
        bec.on_charge(5.0, 3.0)
        assert bec.get_soc() == pytest.approx(33.33, rel=0.01)
        
        # Midday: charge from solar (cheap)
        bec.on_charge(10.0, 0.5)
        assert bec.get_soc() == 100.0
        # WACE should be weighted: (5*3 + 10*0.5) / 15 = 20/15 = 1.333
        assert bec.wace == pytest.approx(1.333, rel=0.01)
        
        # Evening: discharge
        bec.on_discharge(10.0)
        assert bec.get_soc() == pytest.approx(33.33, rel=0.01)
        assert bec.wace == pytest.approx(1.333, rel=0.01)  # WACE unchanged
        
        # Night: charge from grid (medium cost)
        bec.on_charge(10.0, 2.0)
        # Now: 5 kWh @ 1.333 + 10 kWh @ 2.0 = 6.665 + 20 = 26.665 / 15 = 1.777
        assert bec.wace == pytest.approx(1.777, rel=0.01)

    def test_manual_override_workflow(self, bec):
        """Test manual SOC override and cost reset workflow."""
        # Charge some energy
        bec.on_charge(5.0, 2.0)
        
        # Manual SOC override (e.g., user input)
        bec.set_soc(80.0)
        assert bec.energy_kwh == 12.0  # 80% of 15 kWh
        assert bec.wace == 2.0  # Cost preserved
        
        # Reset cost
        bec.reset_cost()
        assert bec.wace == 0.0
        assert bec.energy_kwh == 12.0  # Energy preserved
        
        # Continue tracking with fresh cost
        bec.on_charge(3.0, 1.5)
        assert bec.energy_kwh == 15.0
        # WACE only considers new charge: 1.5 SEK/kWh
        # (12*0 + 3*1.5) / 15 = 0.3
        assert bec.wace == pytest.approx(0.3)
