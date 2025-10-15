"""Tests for load shift optimizer."""
import pytest
from datetime import datetime, timedelta

from custom_components.energy_dispatcher.load_shift_optimizer import LoadShiftOptimizer
from custom_components.energy_dispatcher.models import PricePoint


@pytest.fixture
def optimizer():
    """Create a LoadShiftOptimizer instance."""
    return LoadShiftOptimizer(
        min_savings_threshold_sek=0.5,
        min_flexible_load_w=500.0,
    )


@pytest.fixture
def sample_prices():
    """Generate sample price points with variation."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    prices = []
    
    # Create 12 hours of varying prices
    price_pattern = [
        3.0, 3.2, 2.8, 1.5,  # Current + next 3 hours (expensive now, cheap later)
        1.2, 1.0, 1.3, 1.8,  # Hours 4-7 (cheap period)
        2.0, 2.2, 2.5, 2.3,  # Hours 8-11 (moderate)
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


class TestLoadShiftRecommendations:
    """Test load shift recommendation functionality."""

    def test_recommend_shifts_basic(self, optimizer, sample_prices):
        """Test basic load shift recommendation."""
        now = sample_prices[0].time
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=2000.0,  # 1700W flexible load
            prices=sample_prices,
            user_flexibility_hours=6,
        )
        
        assert len(recommendations) > 0
        assert recommendations[0]["savings_per_hour_sek"] > 0
        assert recommendations[0]["price_now"] > recommendations[0]["price_then"]

    def test_no_recommendations_below_threshold(self, optimizer, sample_prices):
        """Test no recommendations when flexible load is too low."""
        now = sample_prices[0].time
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=600.0,  # Only 300W flexible, below 500W threshold
            prices=sample_prices,
            user_flexibility_hours=6,
        )
        
        assert len(recommendations) == 0

    def test_recommendations_sorted_by_savings(self, optimizer, sample_prices):
        """Test recommendations are sorted by savings potential."""
        now = sample_prices[0].time
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=2000.0,
            prices=sample_prices,
            user_flexibility_hours=8,
        )
        
        if len(recommendations) > 1:
            # Verify descending order by savings
            for i in range(len(recommendations) - 1):
                assert (
                    recommendations[i]["savings_per_hour_sek"]
                    >= recommendations[i + 1]["savings_per_hour_sek"]
                )

    def test_flexibility_window_respected(self, optimizer, sample_prices):
        """Test that recommendations stay within flexibility window."""
        now = sample_prices[0].time
        flexibility_hours = 4
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=2000.0,
            prices=sample_prices,
            user_flexibility_hours=flexibility_hours,
        )
        
        end_time = now + timedelta(hours=flexibility_hours)
        for rec in recommendations:
            assert rec["shift_to"] > now
            assert rec["shift_to"] <= end_time

    def test_user_impact_assessment(self, optimizer):
        """Test user impact assessment for different times."""
        # Night hours (0-6) should be low impact
        night_time = datetime(2025, 1, 1, 3, 0)
        assert optimizer._assess_user_impact(night_time) == "low"
        
        # Morning peak (7-9) should be medium impact
        morning_time = datetime(2025, 1, 1, 8, 0)
        assert optimizer._assess_user_impact(morning_time) == "medium"
        
        # Midday (10-16) should be low impact
        midday_time = datetime(2025, 1, 1, 12, 0)
        assert optimizer._assess_user_impact(midday_time) == "low"
        
        # Evening peak (17-22) should be medium impact
        evening_time = datetime(2025, 1, 1, 19, 0)
        assert optimizer._assess_user_impact(evening_time) == "medium"

    def test_savings_calculation(self, optimizer, sample_prices):
        """Test that savings are calculated correctly."""
        now = sample_prices[0].time
        flexible_load_w = 1700.0
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=300.0 + flexible_load_w,
            prices=sample_prices,
            user_flexibility_hours=6,
        )
        
        # Check first recommendation (should be to hour with lowest price)
        best = recommendations[0]
        price_diff = best["price_now"] - best["price_then"]
        expected_savings = price_diff * (flexible_load_w / 1000.0)
        
        # Allow small rounding differences
        assert abs(best["savings_per_hour_sek"] - expected_savings) < 0.01

    def test_no_current_price(self, optimizer):
        """Test handling when current price is not available."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Create prices that don't include current time
        future_prices = [
            PricePoint(
                time=now + timedelta(hours=i),
                spot_sek_per_kwh=2.0,
                enriched_sek_per_kwh=2.5,
            )
            for i in range(5, 10)  # Prices start 5 hours in future
        ]
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=2000.0,
            prices=future_prices,
            user_flexibility_hours=6,
        )
        
        assert len(recommendations) == 0

    def test_no_future_prices(self, optimizer):
        """Test handling when no future prices are available."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Only current price, no future
        prices = [
            PricePoint(
                time=now,
                spot_sek_per_kwh=2.0,
                enriched_sek_per_kwh=2.5,
            )
        ]
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=2000.0,
            prices=prices,
            user_flexibility_hours=6,
        )
        
        assert len(recommendations) == 0

    def test_minimum_savings_threshold(self, optimizer):
        """Test that small price differences are not recommended."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Create prices with small differences (below 0.5 SEK/kWh threshold)
        prices = [
            PricePoint(
                time=now + timedelta(hours=i),
                spot_sek_per_kwh=2.0 - i * 0.1,
                enriched_sek_per_kwh=2.5 - i * 0.1,
            )
            for i in range(6)
        ]
        
        recommendations = optimizer.recommend_load_shifts(
            current_time=now,
            baseline_load_w=300.0,
            current_consumption_w=2000.0,
            prices=prices,
            user_flexibility_hours=6,
        )
        
        # Should be no or few recommendations due to small price differences
        for rec in recommendations:
            price_diff = rec["price_now"] - rec["price_then"]
            assert price_diff >= optimizer.min_savings_threshold
