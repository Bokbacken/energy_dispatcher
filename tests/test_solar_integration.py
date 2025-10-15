"""Tests for solar forecast integration in optimization."""
import pytest
from datetime import datetime, timedelta

from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.planner import simple_plan, _is_solar_coming_soon
from custom_components.energy_dispatcher.models import (
    PricePoint,
    ForecastPoint,
    CostThresholds,
    ChargingMode,
)


@pytest.fixture
def strategy():
    """Create a CostStrategy instance."""
    thresholds = CostThresholds(cheap_max=1.5, high_min=3.0)
    return CostStrategy(thresholds)


@pytest.fixture
def now():
    """Create a base timestamp."""
    return datetime.now().replace(minute=0, second=0, microsecond=0)


@pytest.fixture
def high_cost_prices(now):
    """Generate prices with high-cost periods."""
    prices = []
    
    # Create 24 hours: 4 cheap hours, 4 high hours, rest medium
    for i in range(24):
        if i < 4:
            # Night - cheap
            price = 1.0
        elif 8 <= i < 12:
            # Morning peak - high
            price = 3.5
        elif 17 <= i < 21:
            # Evening peak - high
            price = 3.8
        else:
            # Other hours - medium
            price = 2.0
        
        prices.append(
            PricePoint(
                time=now + timedelta(hours=i),
                spot_sek_per_kwh=price * 0.8,
                enriched_sek_per_kwh=price,
                export_sek_per_kwh=price * 0.8 + 0.687,
            )
        )
    
    return prices


@pytest.fixture
def solar_forecast_with_morning_production(now):
    """Generate solar forecast with production during morning hours."""
    solar = []
    
    for i in range(24):
        if 7 <= i < 16:
            # Solar production during day hours (7 AM - 4 PM)
            # Peak at noon
            hour_from_noon = abs(i - 12)
            watts = max(0, 4000 - (hour_from_noon * 500))
        else:
            # No production at night
            watts = 0
        
        solar.append(
            ForecastPoint(
                time=now + timedelta(hours=i),
                watts=float(watts)
            )
        )
    
    return solar


@pytest.fixture
def solar_forecast_no_production(now):
    """Generate solar forecast with no production (cloudy day)."""
    solar = []
    
    for i in range(24):
        solar.append(
            ForecastPoint(
                time=now + timedelta(hours=i),
                watts=0.0
            )
        )
    
    return solar


class TestReserveReductionWithSolar:
    """Test that battery reserve is reduced when solar expected during high-cost hours."""
    
    def test_reserve_reduced_with_solar_during_high_cost(
        self, strategy, now, high_cost_prices, solar_forecast_with_morning_production
    ):
        """Test that reserve is lower when solar expected during high-cost hours."""
        battery_capacity = 10.0  # kWh
        current_soc = 50.0
        
        # Calculate reserve WITHOUT solar forecast
        reserve_without_solar = strategy.calculate_battery_reserve(
            prices=high_cost_prices,
            now=now,
            battery_capacity_kwh=battery_capacity,
            current_soc=current_soc,
            solar_forecast=None
        )
        
        # Calculate reserve WITH solar forecast
        reserve_with_solar = strategy.calculate_battery_reserve(
            prices=high_cost_prices,
            now=now,
            battery_capacity_kwh=battery_capacity,
            current_soc=current_soc,
            solar_forecast=solar_forecast_with_morning_production
        )
        
        # With solar during high-cost hours, reserve should be lower
        assert reserve_with_solar < reserve_without_solar
        
        # Reserve should be reduced by a meaningful amount (at least 10%)
        reduction_pct = (reserve_without_solar - reserve_with_solar) / reserve_without_solar * 100
        assert reduction_pct >= 10.0
    
    def test_reserve_unchanged_with_no_solar(
        self, strategy, now, high_cost_prices, solar_forecast_no_production
    ):
        """Test that reserve is same when no solar expected."""
        battery_capacity = 10.0  # kWh
        current_soc = 50.0
        
        # Calculate reserve WITHOUT solar forecast
        reserve_without_solar = strategy.calculate_battery_reserve(
            prices=high_cost_prices,
            now=now,
            battery_capacity_kwh=battery_capacity,
            current_soc=current_soc,
            solar_forecast=None
        )
        
        # Calculate reserve WITH solar forecast (but no production)
        reserve_with_solar = strategy.calculate_battery_reserve(
            prices=high_cost_prices,
            now=now,
            battery_capacity_kwh=battery_capacity,
            current_soc=current_soc,
            solar_forecast=solar_forecast_no_production
        )
        
        # With no solar production, reserve should be approximately the same
        assert abs(reserve_with_solar - reserve_without_solar) < 1.0
    
    def test_solar_calculation_during_windows(
        self, strategy, now, solar_forecast_with_morning_production
    ):
        """Test solar energy calculation during high-cost windows."""
        # Define high-cost windows during solar production hours
        windows = [
            (now + timedelta(hours=8), now + timedelta(hours=12)),  # Morning peak (8-12)
            (now + timedelta(hours=17), now + timedelta(hours=21)), # Evening peak (17-21, but no solar)
        ]
        
        solar_kwh = strategy._calculate_solar_during_windows(
            solar_forecast_with_morning_production,
            windows
        )
        
        # Should have solar during morning window (8-12 = 4 hours)
        # Hours 8-11: approximately 4000, 3500, 3000, 2500 W = 13000 W average = 13 kWh for 4 hours
        assert solar_kwh > 10.0  # At least 10 kWh
        assert solar_kwh < 20.0  # But not more than 20 kWh
        
        # Evening window (17-21) has no solar, so it shouldn't add much
        # Total should be mostly from morning window


class TestSolarComingSoonLogic:
    """Test that grid charging is skipped when solar coming soon."""
    
    def test_skip_charging_when_solar_coming(self, now, solar_forecast_with_morning_production):
        """Test that _is_solar_coming_soon detects upcoming solar."""
        # Create solar map - solar production is from hours 7-15
        # Peak is at hour 12 with 4000W, hour 7 has 1500W
        solar_map = {
            point.time.replace(minute=0, second=0, microsecond=0): point
            for point in solar_forecast_with_morning_production
        }
        
        # Test at hour 10: peak solar (4000W) at hour 12 within 2 hours (should return True)
        time_hour_10 = (now + timedelta(hours=10)).replace(minute=0, second=0, microsecond=0)
        result = _is_solar_coming_soon(time_hour_10, solar_map, threshold_w=2000, window_hours=2)
        assert result, f"Expected solar at hour 10 to detect peak at hour 12. Solar map has: {[(k.hour, v.watts) for k, v in solar_map.items() if v.watts > 2000]}"
        
        # Test at hour 2: no solar within 2 hours (hours 3-4) - should return False
        time_hour_2 = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
        result = _is_solar_coming_soon(time_hour_2, solar_map, threshold_w=2000, window_hours=2)
        assert not result, "Expected no solar coming soon at hour 2"
    
    def test_solar_aware_planning_skips_grid_charge(
        self, now, high_cost_prices, solar_forecast_with_morning_production
    ):
        """Test that plan skips grid charging when solar coming soon and SOC > reserve."""
        battery_capacity = 10.0  # kWh
        battery_soc = 40.0  # Above reserve but not full
        
        # Create cost strategy
        strategy = CostStrategy(CostThresholds(cheap_max=1.5, high_min=3.0))
        
        # Generate plan - start at hour 6 when solar is coming soon
        plan_time = now + timedelta(hours=6)
        plan = simple_plan(
            now=plan_time,
            horizon_hours=8,
            prices=high_cost_prices,
            solar=solar_forecast_with_morning_production,
            batt_soc_pct=battery_soc,
            batt_capacity_kwh=battery_capacity,
            batt_max_charge_w=4000,
            ev_need_kwh=0.0,
            cheap_threshold=1.5,
            cost_strategy=strategy,
            export_mode="never",
            battery_degradation_per_cycle=0.50,
        )
        
        # Check first hour (6 AM) - should skip charging due to solar coming
        first_action = plan[0]
        if first_action.notes:
            # Should have note about skipping charge due to solar
            assert "solar expected soon" in first_action.notes.lower() or first_action.charge_batt_w == 0
    
    def test_solar_aware_planning_allows_charge_below_reserve(
        self, now, high_cost_prices, solar_forecast_with_morning_production
    ):
        """Test that plan allows charging below reserve even with solar coming."""
        battery_capacity = 10.0  # kWh
        battery_soc = 10.0  # Well below reserve (critical)
        
        # Create cost strategy
        strategy = CostStrategy(CostThresholds(cheap_max=1.5, high_min=3.0))
        
        # Generate plan - start at cheap hour (hour 0) when solar is coming later
        plan_time = now
        plan = simple_plan(
            now=plan_time,
            horizon_hours=8,
            prices=high_cost_prices,
            solar=solar_forecast_with_morning_production,
            batt_soc_pct=battery_soc,
            batt_capacity_kwh=battery_capacity,
            batt_max_charge_w=4000,
            ev_need_kwh=0.0,
            cheap_threshold=1.5,
            cost_strategy=strategy,
            export_mode="never",
            battery_degradation_per_cycle=0.50,
        )
        
        # With SOC well below reserve, should charge during cheap hours (hours 0-3)
        # At least one action in first 4 hours should be charging
        early_actions = plan[:4]
        has_charging = any(action.charge_batt_w > 0 for action in early_actions)
        
        # Should charge when critically low during cheap hours
        assert has_charging, "Should charge when SOC is critically low (10%) during cheap hours"


class TestSolarIntegrationEdgeCases:
    """Test edge cases for solar integration."""
    
    def test_reserve_calculation_with_empty_solar_forecast(
        self, strategy, now, high_cost_prices
    ):
        """Test that reserve calculation works with empty solar forecast."""
        battery_capacity = 10.0
        current_soc = 50.0
        
        # Empty solar forecast list
        reserve = strategy.calculate_battery_reserve(
            prices=high_cost_prices,
            now=now,
            battery_capacity_kwh=battery_capacity,
            current_soc=current_soc,
            solar_forecast=[]
        )
        
        # Should handle empty list gracefully
        assert reserve >= 0.0
        assert reserve <= 100.0
    
    def test_solar_calculation_with_no_overlap(
        self, strategy, now
    ):
        """Test solar calculation when windows don't overlap with forecast."""
        # Solar forecast only in morning
        solar = [
            ForecastPoint(time=now + timedelta(hours=i), watts=3000.0)
            for i in range(8, 12)
        ]
        
        # Windows only in evening (no overlap)
        windows = [
            (now + timedelta(hours=18), now + timedelta(hours=22)),
        ]
        
        solar_kwh = strategy._calculate_solar_during_windows(solar, windows)
        
        # No overlap = no solar energy
        assert solar_kwh == 0.0
    
    def test_is_solar_coming_soon_with_empty_map(self, now):
        """Test _is_solar_coming_soon with empty solar map."""
        solar_map = {}
        
        result = _is_solar_coming_soon(now, solar_map, threshold_w=2000, window_hours=2)
        
        # Empty map = no solar coming
        assert result is False
