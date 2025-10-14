"""Tests for cost strategy."""
import pytest
from datetime import datetime, timedelta

from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.models import (
    PricePoint,
    CostThresholds,
    CostLevel,
)


@pytest.fixture
def strategy():
    """Create a CostStrategy instance."""
    thresholds = CostThresholds(cheap_max=1.5, high_min=3.0)
    return CostStrategy(thresholds)


@pytest.fixture
def sample_prices():
    """Generate sample price points."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    prices = []
    
    # Create 24 hours of varying prices
    price_pattern = [
        1.0, 1.2, 1.0, 0.8,  # Night (cheap)
        0.9, 1.1, 1.3, 2.0,  # Morning
        2.5, 3.5, 4.0, 3.8,  # Peak morning (high)
        2.2, 1.8, 1.5, 1.3,  # Midday
        1.4, 1.6, 2.8, 3.2,  # Evening
        3.5, 3.0, 2.0, 1.5,  # Night
    ]
    
    for i, price in enumerate(price_pattern):
        prices.append(
            PricePoint(
                time=now + timedelta(hours=i),
                spot_sek_per_kwh=price * 0.8,
                enriched_sek_per_kwh=price,
            )
        )
    
    return prices


class TestCostClassification:
    """Test cost classification functionality."""

    def test_classify_cheap(self, strategy):
        """Test cheap price classification."""
        level = strategy.classify_price(1.0)
        assert level == CostLevel.CHEAP

    def test_classify_medium(self, strategy):
        """Test medium price classification."""
        level = strategy.classify_price(2.0)
        assert level == CostLevel.MEDIUM

    def test_classify_high(self, strategy):
        """Test high price classification."""
        level = strategy.classify_price(3.5)
        assert level == CostLevel.HIGH

    def test_classify_boundary_cheap(self, strategy):
        """Test boundary at cheap threshold."""
        level = strategy.classify_price(1.5)
        assert level == CostLevel.CHEAP

    def test_classify_boundary_high(self, strategy):
        """Test boundary at high threshold."""
        level = strategy.classify_price(3.0)
        assert level == CostLevel.HIGH


class TestThresholds:
    """Test threshold management."""

    def test_update_thresholds(self, strategy):
        """Test updating thresholds."""
        strategy.update_thresholds(cheap_max=2.0, high_min=4.0)
        
        assert strategy.thresholds.cheap_max == 2.0
        assert strategy.thresholds.high_min == 4.0

    def test_dynamic_thresholds(self, strategy, sample_prices):
        """Test dynamic threshold calculation."""
        dynamic = strategy.get_dynamic_thresholds(sample_prices)
        
        # Check that thresholds are reasonable
        assert 0.0 < dynamic.cheap_max < dynamic.high_min
        assert dynamic.cheap_max < 2.0
        assert dynamic.high_min > 2.0


class TestHighCostWindows:
    """Test high-cost window prediction."""

    def test_predict_windows(self, strategy, sample_prices):
        """Test predicting high-cost windows."""
        now = sample_prices[0].time
        windows = strategy.predict_high_cost_windows(sample_prices, now, 24)
        
        # Should find at least one high-cost window
        assert len(windows) > 0
        
        # Windows should have start < end
        for start, end in windows:
            assert start < end

    def test_predict_windows_no_high_cost(self, strategy):
        """Test when no high-cost periods exist."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        cheap_prices = [
            PricePoint(now + timedelta(hours=i), 0.5, 1.0)
            for i in range(24)
        ]
        
        windows = strategy.predict_high_cost_windows(cheap_prices, now, 24)
        assert len(windows) == 0


class TestBatteryReserve:
    """Test battery reserve calculation."""

    def test_calculate_reserve(self, strategy, sample_prices):
        """Test battery reserve calculation."""
        now = sample_prices[0].time
        reserve = strategy.calculate_battery_reserve(
            sample_prices,
            now,
            battery_capacity_kwh=30.0,
            current_soc=50.0,
        )
        
        # Should recommend some reserve
        assert 0.0 <= reserve <= 80.0

    def test_reserve_no_high_cost(self, strategy):
        """Test reserve when no high-cost periods."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        cheap_prices = [
            PricePoint(now + timedelta(hours=i), 0.5, 1.0)
            for i in range(24)
        ]
        
        reserve = strategy.calculate_battery_reserve(
            cheap_prices,
            now,
            battery_capacity_kwh=30.0,
            current_soc=50.0,
        )
        
        # No reserve needed
        assert reserve == 0.0


class TestBatteryDecisions:
    """Test battery charge/discharge decisions."""

    def test_should_charge_cheap_price(self, strategy):
        """Test charging decision at cheap price."""
        should_charge = strategy.should_charge_battery(
            current_price=1.0,
            current_soc=50.0,
            reserve_soc=30.0,
        )
        assert should_charge is True

    def test_should_not_charge_high_price(self, strategy):
        """Test not charging at high price."""
        should_charge = strategy.should_charge_battery(
            current_price=3.5,
            current_soc=50.0,
            reserve_soc=30.0,
        )
        assert should_charge is False

    def test_should_charge_with_solar(self, strategy):
        """Test charging with available solar."""
        should_charge = strategy.should_charge_battery(
            current_price=3.5,  # Even at high price
            current_soc=50.0,
            reserve_soc=30.0,
            solar_available_w=1000.0,
        )
        assert should_charge is True

    def test_should_discharge_high_price(self, strategy):
        """Test discharging at high price."""
        should_discharge = strategy.should_discharge_battery(
            current_price=3.5,
            current_soc=50.0,
            reserve_soc=30.0,
        )
        assert should_discharge is True

    def test_should_not_discharge_below_reserve(self, strategy):
        """Test not discharging below reserve."""
        should_discharge = strategy.should_discharge_battery(
            current_price=3.5,
            current_soc=25.0,
            reserve_soc=30.0,
        )
        assert should_discharge is False


class TestEVOptimization:
    """Test EV charging optimization."""

    def test_optimize_charging_windows(self, strategy, sample_prices):
        """Test EV charging window optimization."""
        now = sample_prices[0].time
        
        hours = strategy.optimize_ev_charging_windows(
            sample_prices,
            now,
            required_energy_kwh=30.0,
            charging_power_kw=11.0,
        )
        
        # Should select about 3 hours (30/11)
        assert 2 <= len(hours) <= 4
        
        # Hours should be chronologically sorted
        for i in range(len(hours) - 1):
            assert hours[i] < hours[i + 1]

    def test_optimize_with_deadline(self, strategy, sample_prices):
        """Test optimization with deadline."""
        now = sample_prices[0].time
        deadline = now + timedelta(hours=6)
        
        hours = strategy.optimize_ev_charging_windows(
            sample_prices,
            now,
            required_energy_kwh=30.0,
            deadline=deadline,
            charging_power_kw=11.0,
        )
        
        # All selected hours should be before deadline
        for hour in hours:
            assert hour < deadline

    def test_optimize_no_energy_needed(self, strategy, sample_prices):
        """Test when no energy is needed."""
        now = sample_prices[0].time
        
        hours = strategy.optimize_ev_charging_windows(
            sample_prices,
            now,
            required_energy_kwh=0.0,
            charging_power_kw=11.0,
        )
        
        assert len(hours) == 0


class TestCostSummary:
    """Test cost summary generation."""

    def test_get_cost_summary(self, strategy, sample_prices):
        """Test generating cost summary."""
        now = sample_prices[0].time
        summary = strategy.get_cost_summary(sample_prices, now, 24)
        
        assert summary["total_hours"] == 24
        assert summary["cheap_hours"] > 0
        assert summary["medium_hours"] > 0
        assert summary["high_hours"] > 0
        assert summary["avg_price"] > 0
        assert summary["min_price"] < summary["max_price"]

    def test_summary_empty_prices(self, strategy):
        """Test summary with no prices."""
        now = datetime.now()
        summary = strategy.get_cost_summary([], now, 24)
        
        assert summary["total_hours"] == 0
        assert summary["cheap_hours"] == 0
        assert summary["avg_price"] == 0.0


class TestWeatherAwareReserve:
    """Test weather-aware battery reserve adjustments."""

    def test_reserve_without_weather_adjustment(self, strategy, sample_prices):
        """Test battery reserve calculation without weather adjustment."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Calculate reserve without weather adjustment
        reserve = strategy.calculate_battery_reserve(
            sample_prices, now, battery_capacity_kwh=30.0, current_soc=50.0
        )
        
        # Should be > 0 since we have high-cost periods
        assert reserve > 0

    def test_reserve_with_minor_weather_adjustment(self, strategy, sample_prices):
        """Test battery reserve with minor weather adjustment (<20% reduction)."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Minor reduction (15%) - should not increase reserve
        weather_adjustment = {
            "reduction_percentage": 15.0,
            "avg_adjustment_factor": 0.85,
        }
        
        reserve_with_weather = strategy.calculate_battery_reserve(
            sample_prices,
            now,
            battery_capacity_kwh=30.0,
            current_soc=50.0,
            weather_adjustment=weather_adjustment,
        )
        
        reserve_without_weather = strategy.calculate_battery_reserve(
            sample_prices, now, battery_capacity_kwh=30.0, current_soc=50.0
        )
        
        # Should be same (no increase for <20% reduction)
        assert reserve_with_weather == pytest.approx(reserve_without_weather, rel=0.01)

    def test_reserve_with_moderate_weather_adjustment(self, strategy, sample_prices):
        """Test battery reserve with moderate weather adjustment (20-40% reduction)."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Moderate reduction (30%) - should increase reserve by 10%
        weather_adjustment = {
            "reduction_percentage": 30.0,
            "avg_adjustment_factor": 0.70,
        }
        
        reserve_with_weather = strategy.calculate_battery_reserve(
            sample_prices,
            now,
            battery_capacity_kwh=30.0,
            current_soc=50.0,
            weather_adjustment=weather_adjustment,
        )
        
        reserve_without_weather = strategy.calculate_battery_reserve(
            sample_prices, now, battery_capacity_kwh=30.0, current_soc=50.0
        )
        
        # Should be increased by ~10%
        assert reserve_with_weather > reserve_without_weather
        assert reserve_with_weather == pytest.approx(
            reserve_without_weather * 1.10, rel=0.05
        )

    def test_reserve_with_severe_weather_adjustment(self, strategy, sample_prices):
        """Test battery reserve with severe weather adjustment (>60% reduction)."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Severe reduction (70%) - should increase reserve by 20%
        weather_adjustment = {
            "reduction_percentage": 70.0,
            "avg_adjustment_factor": 0.30,
        }
        
        reserve_with_weather = strategy.calculate_battery_reserve(
            sample_prices,
            now,
            battery_capacity_kwh=30.0,
            current_soc=50.0,
            weather_adjustment=weather_adjustment,
        )
        
        reserve_without_weather = strategy.calculate_battery_reserve(
            sample_prices, now, battery_capacity_kwh=30.0, current_soc=50.0
        )
        
        # Should be increased by ~20%
        assert reserve_with_weather > reserve_without_weather
        assert reserve_with_weather == pytest.approx(
            reserve_without_weather * 1.20, rel=0.05
        )
