"""Tests for appliance optimizer."""
import pytest
from datetime import datetime, timedelta

from custom_components.energy_dispatcher.appliance_optimizer import ApplianceOptimizer
from custom_components.energy_dispatcher.models import PricePoint, ForecastPoint


@pytest.fixture
def optimizer():
    """Create an ApplianceOptimizer instance."""
    return ApplianceOptimizer()


@pytest.fixture
def sample_prices():
    """Generate 48 hours of sample price points."""
    base_time = datetime(2025, 1, 15, 0, 0, 0)
    prices = []
    
    # Create realistic price pattern over 48 hours
    # Night (00-06): cheap
    # Morning peak (07-09): high
    # Midday (10-15): medium
    # Evening peak (16-20): high
    # Night (21-23): cheap
    
    price_pattern = [
        # Day 1
        1.0, 0.9, 0.8, 0.8, 0.9, 1.0,  # 00-05 Night (cheap)
        1.2, 1.8, 2.5, 3.0,              # 06-09 Morning (high)
        2.2, 1.8, 1.5, 1.4, 1.5, 1.6,    # 10-15 Midday (medium)
        2.0, 2.8, 3.2, 3.5, 3.0,         # 16-20 Evening (high)
        2.0, 1.5, 1.2,                    # 21-23 Night (cheap)
        # Day 2
        1.0, 0.9, 0.8, 0.8, 0.9, 1.0,    # 00-05 Night (cheap)
        1.2, 1.8, 2.5, 3.0,              # 06-09 Morning (high)
        2.2, 1.8, 1.5, 1.4, 1.5, 1.6,    # 10-15 Midday (medium)
        2.0, 2.8, 3.2, 3.5, 3.0,         # 16-20 Evening (high)
        2.0, 1.5, 1.2,                    # 21-23 Night (cheap)
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
    """Generate 48 hours of sample solar forecast."""
    base_time = datetime(2025, 1, 15, 0, 0, 0)
    solar = []
    
    for hour in range(48):
        # Simple solar pattern: peak at 12:00, zero at night
        hour_of_day = hour % 24
        if 6 <= hour_of_day <= 18:
            # Parabolic curve peaking at noon
            watts = 2000 * (1 - abs(hour_of_day - 12) / 6) ** 2
        else:
            watts = 0
        
        solar.append(
            ForecastPoint(
                time=base_time + timedelta(hours=hour),
                watts=watts,
            )
        )
    
    return solar


class TestBasicOptimization:
    """Test basic optimization functionality."""

    def test_optimize_dishwasher_cheap_period(self, optimizer, sample_prices):
        """Test dishwasher optimization finds cheap period."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=base_time + timedelta(hours=8),
            latest_end=base_time + timedelta(hours=24),
        )
        
        assert result is not None
        assert "optimal_start_time" in result
        assert "estimated_cost_sek" in result
        assert result["estimated_cost_sek"] > 0
        
        # Should prefer cheap hours (late night or early morning or midday)
        optimal_hour = result["optimal_start_time"].hour
        # Between midnight and 5am, or midday hours (10-15), or late evening (22-23)
        assert optimal_hour < 6 or (10 <= optimal_hour <= 15) or optimal_hour >= 22

    def test_optimize_with_time_constraints(self, optimizer, sample_prices):
        """Test optimization respects time constraints."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        # Constrain to morning hours (expensive)
        earliest = base_time + timedelta(hours=7)
        latest = base_time + timedelta(hours=11)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=earliest,
            latest_end=latest,
        )
        
        # Should still find a time within constraints
        assert earliest <= result["optimal_start_time"] < latest - timedelta(hours=2)

    def test_optimize_washing_machine(self, optimizer, sample_prices):
        """Test washing machine optimization."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="washing_machine",
            power_w=2000,
            duration_hours=1.5,
            prices=sample_prices,
            earliest_start=base_time,
            latest_end=base_time + timedelta(hours=24),
        )
        
        assert result is not None
        assert result["estimated_cost_sek"] > 0
        # Should have savings vs running during peak hours
        assert "cost_savings_vs_now_sek" in result

    def test_optimize_water_heater(self, optimizer, sample_prices):
        """Test water heater optimization."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="water_heater",
            power_w=3000,
            duration_hours=3.0,
            prices=sample_prices,
            earliest_start=base_time,
            latest_end=base_time + timedelta(hours=24),
        )
        
        assert result is not None
        assert result["estimated_cost_sek"] > 0
        # Higher power appliance should show significant cost difference
        assert "cost_savings_vs_now_sek" in result


class TestSolarIntegration:
    """Test solar production integration."""

    def test_optimize_with_solar_forecast(self, optimizer, sample_prices, sample_solar):
        """Test optimization considers solar production."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            solar_forecast=sample_solar,
            earliest_start=base_time + timedelta(hours=8),
            latest_end=base_time + timedelta(hours=18),
        )
        
        assert result is not None
        
        # With solar available during day, might prefer midday
        optimal_hour = result["optimal_start_time"].hour
        # Should prefer solar hours (10-14) or cheap hours
        assert (10 <= optimal_hour <= 14) or optimal_hour < 6

    def test_solar_offset_reduces_cost(self, optimizer, sample_prices, sample_solar):
        """Test that solar production reduces estimated cost."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        # Optimize without solar
        result_no_solar = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=base_time + timedelta(hours=10),
            latest_end=base_time + timedelta(hours=14),
        )
        
        # Optimize with solar
        result_with_solar = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            solar_forecast=sample_solar,
            earliest_start=base_time + timedelta(hours=10),
            latest_end=base_time + timedelta(hours=14),
        )
        
        # Cost with solar should be lower or equal
        assert result_with_solar["estimated_cost_sek"] <= result_no_solar["estimated_cost_sek"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_prices_available(self, optimizer):
        """Test handling when no price data available."""
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=[],
        )
        
        assert result is not None
        assert result["confidence"] == "low"
        assert "No price data" in result["reason"]

    def test_no_valid_window(self, optimizer, sample_prices):
        """Test handling when no valid time window exists."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        # Impossible constraint: window too short
        earliest = base_time + timedelta(hours=10)
        latest = base_time + timedelta(hours=10, minutes=30)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=earliest,
            latest_end=latest,
        )
        
        assert result is not None
        assert "No valid time window" in result["reason"]

    def test_short_duration(self, optimizer, sample_prices):
        """Test optimization for short duration appliance."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="kettle",
            power_w=2000,
            duration_hours=0.25,  # 15 minutes
            prices=sample_prices,
        )
        
        assert result is not None
        assert result["estimated_cost_sek"] >= 0

    def test_long_duration(self, optimizer, sample_prices):
        """Test optimization for long duration appliance."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="water_heater",
            power_w=3000,
            duration_hours=6.0,
            prices=sample_prices,
            earliest_start=base_time,
            latest_end=base_time + timedelta(hours=36),
        )
        
        assert result is not None
        assert result["estimated_cost_sek"] > 0


class TestResultAttributes:
    """Test result attributes and formatting."""

    def test_result_has_all_required_fields(self, optimizer, sample_prices):
        """Test that result contains all required fields."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
        )
        
        required_fields = [
            "optimal_start_time",
            "estimated_cost_sek",
            "cost_savings_vs_now_sek",
            "reason",
            "price_at_optimal_time",
            "current_price",
            "solar_available",
            "alternative_times",
            "confidence",
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_alternative_times_provided(self, optimizer, sample_prices):
        """Test that alternative times are provided."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
        )
        
        assert "alternative_times" in result
        # Should have up to 3 alternatives
        assert len(result["alternative_times"]) <= 3

    def test_confidence_assessment(self, optimizer, sample_prices, sample_solar):
        """Test confidence level assessment."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        # With 48 hours of prices and solar -> high confidence
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            solar_forecast=sample_solar,
            earliest_start=base_time,
            latest_end=base_time + timedelta(hours=36),
        )
        
        assert result["confidence"] in ["low", "medium", "high"]
        # 48 hours of data should give high or medium confidence
        assert result["confidence"] in ["medium", "high"]

    def test_reason_is_descriptive(self, optimizer, sample_prices):
        """Test that reason is a non-empty string."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
        )
        
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


class TestCostCalculations:
    """Test cost calculation accuracy."""

    def test_cost_increases_with_power(self, optimizer, sample_prices):
        """Test that cost scales with power consumption."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result_1800w = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=base_time + timedelta(hours=10),
            latest_end=base_time + timedelta(hours=12),
        )
        
        result_3000w = optimizer.optimize_schedule(
            appliance_name="water_heater",
            power_w=3000,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=base_time + timedelta(hours=10),
            latest_end=base_time + timedelta(hours=12),
        )
        
        # Higher power should result in higher cost
        assert result_3000w["estimated_cost_sek"] > result_1800w["estimated_cost_sek"]

    def test_cost_increases_with_duration(self, optimizer, sample_prices):
        """Test that cost scales with duration."""
        base_time = datetime(2025, 1, 15, 0, 0, 0)
        
        result_1h = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=1.0,
            prices=sample_prices,
            earliest_start=base_time + timedelta(hours=10),
            latest_end=base_time + timedelta(hours=12),
        )
        
        result_3h = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=3.0,
            prices=sample_prices,
            earliest_start=base_time + timedelta(hours=10),
            latest_end=base_time + timedelta(hours=14),
        )
        
        # Longer duration should result in higher cost
        assert result_3h["estimated_cost_sek"] > result_1h["estimated_cost_sek"]

    def test_savings_calculation(self, optimizer, sample_prices):
        """Test that savings are calculated correctly."""
        base_time = datetime(2025, 1, 15, 8, 0, 0)  # Morning peak hour
        
        result = optimizer.optimize_schedule(
            appliance_name="dishwasher",
            power_w=1800,
            duration_hours=2.0,
            prices=sample_prices,
            earliest_start=base_time,
            latest_end=base_time + timedelta(hours=24),
        )
        
        # If current time is expensive, should show positive savings
        if result["current_price"] > 2.0:  # High price threshold
            assert result["cost_savings_vs_now_sek"] >= 0
