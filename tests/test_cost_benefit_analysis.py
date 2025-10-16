"""Tests for cost-benefit analysis in optimization planning."""
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


class TestArbitrageProfitCalculation:
    """Test arbitrage profit calculation."""
    
    def test_profitable_arbitrage(self, strategy):
        """Test profitable arbitrage scenario."""
        # Buy at 1.0 SEK/kWh, discharge at 4.0 SEK/kWh (avoided import cost)
        # For 5 kWh with 10 kWh battery (0.5 cycle)
        # Degradation: 0.50 SEK per cycle → 0.25 SEK for 0.5 cycle
        # Cost avoided: 4.0 × 5 × 0.9 = 18.0 SEK
        # Cost: 1.0 × 5 = 5.0 SEK
        # Net: 18.0 - 5.0 - 0.25 = 12.75 SEK
        
        profit = strategy.calculate_arbitrage_profit(
            buy_price=1.0,
            discharge_value=4.0,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        assert profit > 0
        assert abs(profit - 12.75) < 0.01
    
    def test_unprofitable_arbitrage(self, strategy):
        """Test unprofitable arbitrage scenario."""
        # Buy at 2.0 SEK/kWh, discharge at 2.1 SEK/kWh
        # Small price difference, degradation makes it unprofitable
        # For 5 kWh with 10 kWh battery (0.5 cycle)
        # Degradation: 0.50 SEK per cycle → 0.25 SEK for 0.5 cycle
        # Cost avoided: 2.1 × 5 × 0.9 = 9.45 SEK
        # Cost: 2.0 × 5 = 10.0 SEK
        # Net: 9.45 - 10.0 - 0.25 = -0.8 SEK (loss)
        
        profit = strategy.calculate_arbitrage_profit(
            buy_price=2.0,
            discharge_value=2.1,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        assert profit < 0
    
    def test_break_even_arbitrage(self, strategy):
        """Test break-even arbitrage scenario."""
        # Calculate what discharge value would give near-zero profit
        # With degradation 0.50 SEK/cycle and 10 kWh battery
        # For 5 kWh (0.5 cycle), degradation = 0.25 SEK
        # To break even: cost_avoided = cost + degradation
        # discharge_value × 5 × 0.9 = 2.0 × 5 + 0.25
        # discharge_value × 4.5 = 10.25
        # discharge_value = 2.278 SEK/kWh
        
        profit = strategy.calculate_arbitrage_profit(
            buy_price=2.0,
            discharge_value=2.278,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        # Should be close to zero (within rounding)
        assert abs(profit) < 0.02
    
    def test_efficiency_impact(self, strategy):
        """Test that efficiency factor impacts profit calculation."""
        # Same scenario with different efficiencies
        
        profit_90 = strategy.calculate_arbitrage_profit(
            buy_price=1.0,
            discharge_value=3.0,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        profit_80 = strategy.calculate_arbitrage_profit(
            buy_price=1.0,
            discharge_value=3.0,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            efficiency=0.8
        )
        
        # Lower efficiency should result in lower profit
        assert profit_90 > profit_80
        # Difference should be: (3.0 × 5 × 0.9) - (3.0 × 5 × 0.8) = 1.5 SEK
        assert abs((profit_90 - profit_80) - 1.5) < 0.01


class TestArbitrageProfitabilityCheck:
    """Test arbitrage profitability decision."""
    
    def test_profitable_passes_threshold(self, strategy):
        """Test that profitable arbitrage passes threshold check."""
        # Large price difference, should be profitable
        is_profitable = strategy.is_arbitrage_profitable(
            buy_price=1.0,
            discharge_value=4.0,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            min_profit_threshold=0.10
        )
        
        assert is_profitable is True
    
    def test_unprofitable_fails_threshold(self, strategy):
        """Test that unprofitable arbitrage fails threshold check."""
        # Small price difference, won't pass 0.10 SEK threshold
        is_profitable = strategy.is_arbitrage_profitable(
            buy_price=2.0,
            discharge_value=2.05,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            min_profit_threshold=0.10
        )
        
        assert is_profitable is False
    
    def test_threshold_sensitivity(self, strategy):
        """Test that threshold affects profitability decision."""
        # Scenario with small profit (~0.20 SEK)
        # Buy at 2.0, sell at 2.15 with 5 kWh
        # Cost avoided: 2.15 × 5 × 0.9 = 9.675
        # Cost: 2.0 × 5 = 10.0
        # Degradation: 0.50 × 0.5 = 0.25
        # Profit: 9.675 - 10.0 - 0.25 = -0.575 (actually negative!)
        # Let's try 2.25:
        # Cost avoided: 2.25 × 5 × 0.9 = 10.125
        # Cost: 2.0 × 5 = 10.0
        # Degradation: 0.50 × 0.5 = 0.25
        # Profit: 10.125 - 10.0 - 0.25 = -0.125 (still negative!)
        # Need higher sell price. Try 2.35:
        # Cost avoided: 2.35 × 5 × 0.9 = 10.575
        # Cost: 2.0 × 5 = 10.0
        # Degradation: 0.50 × 0.5 = 0.25
        # Profit: 10.575 - 10.0 - 0.25 = 0.325 SEK
        # This should pass 0.10 and 0.20 threshold but fail 0.40
        
        passes_low_threshold = strategy.is_arbitrage_profitable(
            buy_price=2.0,
            discharge_value=2.35,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            min_profit_threshold=0.10
        )
        
        passes_medium_threshold = strategy.is_arbitrage_profitable(
            buy_price=2.0,
            discharge_value=2.35,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            min_profit_threshold=0.20
        )
        
        passes_high_threshold = strategy.is_arbitrage_profitable(
            buy_price=2.0,
            discharge_value=2.35,
            energy_kwh=5.0,
            degradation_cost_per_cycle=0.50,
            battery_capacity_kwh=10.0,
            min_profit_threshold=0.40
        )
        
        assert passes_low_threshold is True
        assert passes_medium_threshold is True
        assert passes_high_threshold is False


class TestDegradationCostProration:
    """Test degradation cost prorated by cycle fraction."""
    
    def test_half_cycle_degradation(self, strategy):
        """Test that 0.5 cycle uses half the degradation cost."""
        # For 5 kWh in 10 kWh battery (0.5 cycle)
        profit = strategy.calculate_arbitrage_profit(
            buy_price=1.0,
            discharge_value=3.0,
            energy_kwh=5.0,
            degradation_cost_per_cycle=1.0,  # Use 1.0 for easy calculation
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        # Expected: revenue (3.0 × 5 × 0.9 = 13.5) - cost (1.0 × 5 = 5.0) - degradation (1.0 × 0.5 = 0.5)
        # = 13.5 - 5.0 - 0.5 = 8.0
        assert abs(profit - 8.0) < 0.01
    
    def test_full_cycle_degradation(self, strategy):
        """Test that full cycle uses full degradation cost."""
        # For 10 kWh in 10 kWh battery (1.0 cycle)
        profit = strategy.calculate_arbitrage_profit(
            buy_price=1.0,
            discharge_value=3.0,
            energy_kwh=10.0,
            degradation_cost_per_cycle=1.0,
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        # Expected: revenue (3.0 × 10 × 0.9 = 27.0) - cost (1.0 × 10 = 10.0) - degradation (1.0 × 1.0 = 1.0)
        # = 27.0 - 10.0 - 1.0 = 16.0
        assert abs(profit - 16.0) < 0.01
    
    def test_quarter_cycle_degradation(self, strategy):
        """Test that 0.25 cycle uses quarter degradation cost."""
        # For 2.5 kWh in 10 kWh battery (0.25 cycle)
        profit = strategy.calculate_arbitrage_profit(
            buy_price=1.0,
            discharge_value=3.0,
            energy_kwh=2.5,
            degradation_cost_per_cycle=1.0,
            battery_capacity_kwh=10.0,
            efficiency=0.9
        )
        
        # Expected: revenue (3.0 × 2.5 × 0.9 = 6.75) - cost (1.0 × 2.5 = 2.5) - degradation (1.0 × 0.25 = 0.25)
        # = 6.75 - 2.5 - 0.25 = 4.0
        assert abs(profit - 4.0) < 0.01
