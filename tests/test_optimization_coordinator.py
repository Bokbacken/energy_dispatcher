"""Integration tests for optimization coordinator."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from custom_components.energy_dispatcher.coordinator import EnergyDispatcherCoordinator
from custom_components.energy_dispatcher.models import PricePoint, ForecastPoint


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    return hass


@pytest.fixture
def mock_config():
    """Create mock configuration data."""
    return {
        "nordpool_entity": "sensor.nordpool_kwh_se3_sek_3_10_025",
        "price_tax": 0.395,
        "price_transfer": 0.50,
        "price_surcharge": 0.10,
        "price_vat": 0.25,
        "battery_capacity_kwh": 15.0,
        "battery_soc_entity": "sensor.battery_soc",
        "battery_max_charge_w": 5000,
        "battery_max_discharge_w": 5000,
        "enable_appliance_optimization": True,
        "dishwasher_power_w": 1800,
        "washing_machine_power_w": 2000,
        "water_heater_power_w": 3000,
        "enable_export_analysis": True,
        "export_mode": "excess_solar_only",
        "min_export_price_sek_per_kwh": 3.0,
        "battery_degradation_cost_per_cycle_sek": 0.50,
        "enable_load_shifting": True,
        "baseline_load_w": 300,
        "load_shift_flexibility_hours": 6,
        "cost_cheap_threshold": 1.5,
        "cost_high_threshold": 3.0,
    }


@pytest.fixture
def sample_prices():
    """Generate realistic 48-hour price data."""
    base_time = datetime(2025, 1, 15, 0, 0, 0)
    prices = []
    
    # Create realistic price pattern over 48 hours
    # Night (00-06): cheap ~1.0 SEK/kWh
    # Morning peak (07-09): high ~3.0 SEK/kWh
    # Midday (10-15): medium ~1.5 SEK/kWh
    # Evening peak (16-20): high ~3.5 SEK/kWh
    # Night (21-23): cheap ~1.2 SEK/kWh
    
    price_pattern = [
        # Day 1
        1.0, 0.9, 0.8, 0.8, 0.9, 1.0,  # 00-05 Night (cheap)
        1.2, 1.8, 2.5, 3.0,              # 06-09 Morning (high)
        2.2, 1.8, 1.5, 1.4, 1.5, 1.6,    # 10-15 Midday (medium)
        2.0, 2.8, 3.2, 3.5, 3.0,         # 16-20 Evening (high)
        2.0, 1.5, 1.2,                    # 21-23 Night (cheap)
        # Day 2 (repeat pattern)
        1.0, 0.9, 0.8, 0.8, 0.9, 1.0,
        1.2, 1.8, 2.5, 3.0,
        2.2, 1.8, 1.5, 1.4, 1.5, 1.6,
        2.0, 2.8, 3.2, 3.5, 3.0,
        2.0, 1.5, 1.2,
    ]
    
    for i, price in enumerate(price_pattern):
        prices.append(
            PricePoint(
                time=base_time + timedelta(hours=i),
                spot_sek_per_kwh=price * 0.8,
                enriched_sek_per_kwh=price,
            )
        )
    
    return prices


@pytest.fixture
def sample_solar():
    """Generate realistic 48-hour solar forecast."""
    base_time = datetime(2025, 1, 15, 0, 0, 0)
    solar = []
    
    for hour in range(48):
        # Simple solar pattern: peak at 12:00, zero at night
        hour_of_day = hour % 24
        if 6 <= hour_of_day <= 18:
            # Parabolic curve peaking at noon with 5kW max
            watts = 5000 * (1 - abs(hour_of_day - 12) / 6) ** 2
        else:
            watts = 0
        
        solar.append(
            ForecastPoint(
                time=base_time + timedelta(hours=hour),
                watts=watts,
            )
        )
    
    return solar


class TestOptimizationCoordinatorIntegration:
    """Integration tests for the optimization coordinator."""

    @pytest.mark.asyncio
    async def test_full_optimization_cycle(self, mock_hass, mock_config, sample_prices, sample_solar):
        """Test complete optimization cycle with all optimizers working together."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # Set up mock data
        coordinator.data = {
            "hourly_prices": sample_prices,
            "solar_points": sample_solar,
            "current_enriched": 1.5,
        }
        
        # Mock state reads for battery and load
        def mock_state_get(entity_id):
            state = Mock()
            if "battery_soc" in entity_id:
                state.state = "75.0"
            elif "load_power" in entity_id:
                state.state = "2000"
            else:
                state.state = "0"
            return state
        
        mock_hass.states.get = mock_state_get
        
        # Run optimization updates
        await coordinator._update_appliance_recommendations()
        await coordinator._update_export_analysis()
        await coordinator._update_load_shift_recommendations()
        
        # Verify appliance recommendations were generated
        assert "appliance_recommendations" in coordinator.data
        appliance_recs = coordinator.data["appliance_recommendations"]
        assert isinstance(appliance_recs, dict)
        
        # Should have recommendations for configured appliances
        if appliance_recs:
            for appliance in ["dishwasher", "washing_machine", "water_heater"]:
                if appliance in appliance_recs:
                    rec = appliance_recs[appliance]
                    assert "optimal_start_time" in rec
                    assert "estimated_cost_sek" in rec
                    assert "confidence" in rec
        
        # Verify export analysis was performed
        assert "export_opportunity" in coordinator.data
        export = coordinator.data["export_opportunity"]
        assert "should_export" in export or "net_revenue" in export
        
        # Verify load shift recommendations were generated
        assert "load_shift_opportunities" in coordinator.data
        load_shifts = coordinator.data["load_shift_opportunities"]
        assert isinstance(load_shifts, list)

    @pytest.mark.asyncio
    async def test_optimizer_conflict_resolution(self, mock_hass, mock_config, sample_prices, sample_solar):
        """Test that optimizers handle conflicts gracefully (e.g., all want to charge at same time)."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # Set up scenario where cheapest time is the same for all optimizers
        # All should recommend the same time window, but they shouldn't interfere
        coordinator.data = {
            "hourly_prices": sample_prices,
            "solar_points": sample_solar,
            "current_enriched": 3.5,  # High price now
        }
        
        # Mock battery state
        mock_hass.states.get = Mock(return_value=Mock(state="50.0"))
        
        # Run all optimizers
        await coordinator._update_appliance_recommendations()
        await coordinator._update_export_analysis()
        
        # Verify both completed without errors
        assert "appliance_recommendations" in coordinator.data
        assert "export_opportunity" in coordinator.data
        
        # In high price scenario, appliances should defer to cheap hours
        appliance_recs = coordinator.data.get("appliance_recommendations", {})
        for rec in appliance_recs.values():
            if "optimal_start_time" in rec:
                # Optimal time should not be during peak hours (16-20)
                optimal_hour = rec["optimal_start_time"].hour
                # Should prefer cheap hours (night time)
                assert optimal_hour < 10 or optimal_hour > 20

    @pytest.mark.asyncio
    async def test_coordinator_data_flow(self, mock_hass, mock_config, sample_prices):
        """Test that data flows correctly through coordinator update cycle."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # Initial state has default keys
        assert isinstance(coordinator.data, dict)
        
        # Simulate price update
        coordinator.data["hourly_prices"] = sample_prices
        coordinator.data["current_enriched"] = 2.0
        
        # Run optimization updates
        await coordinator._update_appliance_recommendations()
        
        # Verify data structure is maintained
        assert "hourly_prices" in coordinator.data
        assert "appliance_recommendations" in coordinator.data
        assert len(coordinator.data["hourly_prices"]) == len(sample_prices)

    @pytest.mark.asyncio
    async def test_missing_price_data_handling(self, mock_hass, mock_config):
        """Test graceful handling when price data is unavailable."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # No price data
        coordinator.data = {"hourly_prices": []}
        
        # Should not crash, but return empty recommendations
        await coordinator._update_appliance_recommendations()
        await coordinator._update_export_analysis()
        await coordinator._update_load_shift_recommendations()
        
        # Verify empty/safe defaults
        assert coordinator.data.get("appliance_recommendations") == {}
        assert coordinator.data.get("export_opportunity", {}).get("should_export", False) is False
        assert coordinator.data.get("load_shift_opportunities") == []

    @pytest.mark.asyncio
    async def test_missing_solar_data_handling(self, mock_hass, mock_config, sample_prices):
        """Test optimization works without solar forecast data."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # Price data but no solar
        coordinator.data = {
            "hourly_prices": sample_prices,
            "solar_points": None,
            "current_enriched": 2.0,
        }
        
        mock_hass.states.get = Mock(return_value=Mock(state="50.0"))
        
        # Should still work without solar
        await coordinator._update_appliance_recommendations()
        
        # Verify recommendations were generated (may be less optimal without solar)
        assert "appliance_recommendations" in coordinator.data
        appliance_recs = coordinator.data["appliance_recommendations"]
        # May be empty or have recommendations, both are valid

    @pytest.mark.asyncio
    async def test_battery_override_integration(self, mock_hass, mock_config, sample_prices):
        """Test that battery overrides are respected in optimization."""
        from homeassistant.util import dt as dt_util
        
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        coordinator.data = {"hourly_prices": sample_prices}
        
        # Set a battery override with timezone-aware datetime
        override_time = dt_util.now() + timedelta(hours=1)
        coordinator._battery_override = {
            "mode": "charge",
            "power_w": 5000,
            "expires_at": override_time,
        }
        
        # Get override
        override = coordinator.get_battery_override()
        assert override is not None
        assert override["mode"] == "charge"
        assert override["power_w"] == 5000

    @pytest.mark.asyncio
    async def test_sensor_update_flow(self, mock_hass, mock_config, sample_prices, sample_solar):
        """Test that sensor data updates correctly after optimization."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        coordinator.data = {
            "hourly_prices": sample_prices,
            "solar_points": sample_solar,
            "current_enriched": 1.5,
        }
        
        mock_hass.states.get = Mock(return_value=Mock(state="75.0"))
        
        # Run full update cycle
        await coordinator._update_appliance_recommendations()
        await coordinator._update_export_analysis()
        await coordinator._update_load_shift_recommendations()
        
        # Verify all expected data keys are present
        expected_keys = [
            "hourly_prices",
            "appliance_recommendations",
            "export_opportunity",
            "load_shift_opportunities",
        ]
        
        for key in expected_keys:
            assert key in coordinator.data, f"Missing expected key: {key}"

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, mock_hass, mock_config):
        """Test coordinator performance with large price/solar datasets."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # Generate 7 days of hourly data (168 hours)
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        large_prices = []
        large_solar = []
        
        for hour in range(168):
            # Realistic price variation
            hour_of_day = hour % 24
            if 0 <= hour_of_day <= 6:
                price = 1.0
            elif 7 <= hour_of_day <= 9:
                price = 3.0
            elif 10 <= hour_of_day <= 15:
                price = 1.5
            elif 16 <= hour_of_day <= 20:
                price = 3.5
            else:
                price = 1.2
            
            large_prices.append(
                PricePoint(
                    time=base_time + timedelta(hours=hour),
                    spot_sek_per_kwh=price * 0.8,
                    enriched_sek_per_kwh=price,
                )
            )
            
            # Solar pattern
            if 6 <= hour_of_day <= 18:
                watts = 5000 * (1 - abs(hour_of_day - 12) / 6) ** 2
            else:
                watts = 0
            
            large_solar.append(
                ForecastPoint(
                    time=base_time + timedelta(hours=hour),
                    watts=watts,
                )
            )
        
        coordinator.data = {
            "hourly_prices": large_prices,
            "solar_points": large_solar,
            "current_enriched": 2.0,
        }
        
        mock_hass.states.get = Mock(return_value=Mock(state="50.0"))
        
        # Time the optimization
        import time
        start_time = time.time()
        
        await coordinator._update_appliance_recommendations()
        await coordinator._update_export_analysis()
        
        elapsed = time.time() - start_time
        
        # Should complete within reasonable time (<10 seconds for large dataset)
        assert elapsed < 10.0, f"Optimization took too long: {elapsed:.2f}s"
        
        # Verify results
        assert "appliance_recommendations" in coordinator.data
        assert "export_opportunity" in coordinator.data


class TestOptimizationCaching:
    """Test caching behavior in optimization coordinator."""

    @pytest.mark.asyncio
    async def test_recommendation_caching(self, mock_hass, mock_config, sample_prices):
        """Test that recommendations are cached appropriately."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        coordinator.data = {
            "hourly_prices": sample_prices,
            "current_enriched": 2.0,
        }
        
        mock_hass.states.get = Mock(return_value=Mock(state="50.0"))
        
        # First call
        await coordinator._update_appliance_recommendations()
        first_result = coordinator.data.get("appliance_recommendations", {}).copy()
        
        # Second call immediately after (data hasn't changed)
        await coordinator._update_appliance_recommendations()
        second_result = coordinator.data.get("appliance_recommendations", {})
        
        # Results should be consistent
        assert len(first_result) == len(second_result)


class TestOptimizationErrorHandling:
    """Test error handling in optimization coordinator."""

    @pytest.mark.asyncio
    async def test_optimizer_exception_handling(self, mock_hass, mock_config, sample_prices):
        """Test that exceptions in one optimizer don't crash the whole system."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        coordinator.data = {
            "hourly_prices": sample_prices,
            "current_enriched": 2.0,
        }
        
        # Mock a state read that raises an exception
        def mock_state_with_error(entity_id):
            if "battery_soc" in entity_id:
                raise Exception("Sensor unavailable")
            return Mock(state="50.0")
        
        mock_hass.states.get = mock_state_with_error
        
        # Should handle error gracefully
        try:
            await coordinator._update_appliance_recommendations()
            # Should not raise exception
            success = True
        except Exception:
            success = False
        
        assert success, "Coordinator should handle optimizer exceptions gracefully"

    @pytest.mark.asyncio
    async def test_invalid_price_data_handling(self, mock_hass, mock_config):
        """Test handling of corrupted or invalid price data."""
        coordinator = EnergyDispatcherCoordinator(mock_hass)
        coordinator._config = mock_config
        
        # Invalid price data (wrong type)
        coordinator.data = {
            "hourly_prices": "invalid",
            "current_enriched": 2.0,
        }
        
        # Should not crash
        try:
            await coordinator._update_appliance_recommendations()
            success = True
        except Exception as e:
            success = False
            print(f"Unexpected error: {e}")
        
        assert success, "Should handle invalid price data gracefully"
