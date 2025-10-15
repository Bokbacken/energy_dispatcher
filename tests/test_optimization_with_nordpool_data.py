"""Test optimization with real Nordpool price data."""
import pytest
from datetime import datetime
from decimal import Decimal
import yaml
from pathlib import Path

from custom_components.energy_dispatcher.models import PricePoint, ForecastPoint
from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.planner import simple_plan


@pytest.fixture
def nordpool_prices():
    """Load real Nordpool price data from docs/investigate."""
    docs_dir = Path(__file__).parent.parent / "docs" / "investigate"
    with open(docs_dir / "nordpool.yaml", "r") as f:
        data = yaml.safe_load(f)
    
    prices = []
    for entry in data.get("raw_today", []) + data.get("raw_tomorrow", []):
        start_time = datetime.fromisoformat(entry["start"])
        price = entry["value"]
        prices.append(PricePoint(
            time=start_time,
            spot_sek_per_kwh=price,
            enriched_sek_per_kwh=price
        ))
    
    return prices


@pytest.fixture
def solar_forecast(nordpool_prices):
    """Create minimal solar forecast (zeros for simplicity)."""
    return [ForecastPoint(time=p.time, watts=0) for p in nordpool_prices]


def test_dynamic_thresholds_calculation(nordpool_prices):
    """Test that dynamic thresholds are calculated correctly from price distribution."""
    cost_strategy = CostStrategy()
    dynamic_thresholds = cost_strategy.get_dynamic_thresholds(nordpool_prices)
    
    # Extract prices for percentile calculation
    all_prices = sorted([p.enriched_sek_per_kwh for p in nordpool_prices])
    p25_idx = int(len(all_prices) * 0.25)
    p75_idx = int(len(all_prices) * 0.75)
    expected_cheap = all_prices[p25_idx]
    expected_high = all_prices[p75_idx]
    
    assert abs(dynamic_thresholds.cheap_max - expected_cheap) < 0.01
    assert abs(dynamic_thresholds.high_min - expected_high) < 0.01
    
    # For the test data, verify reasonable thresholds
    assert 0.5 < dynamic_thresholds.cheap_max < 1.0  # Should be around 0.82
    assert 1.2 < dynamic_thresholds.high_min < 1.6   # Should be around 1.42


def test_battery_reserve_with_dynamic_thresholds(nordpool_prices):
    """Test battery reserve calculation with dynamic thresholds."""
    cost_strategy = CostStrategy()
    
    # Use dynamic thresholds
    dynamic_thresholds = cost_strategy.get_dynamic_thresholds(nordpool_prices)
    cost_strategy.update_thresholds(
        cheap_max=dynamic_thresholds.cheap_max,
        high_min=dynamic_thresholds.high_min
    )
    
    now = datetime.fromisoformat("2025-10-15T21:00:00+02:00")
    batt_capacity_kwh = 10.0
    current_soc = 61.0
    
    reserve_soc = cost_strategy.calculate_battery_reserve(
        nordpool_prices, now, batt_capacity_kwh, current_soc, 24
    )
    
    # With reduced conservatism (1 kW load, 60% cap), reserve should be reasonable
    assert 0 <= reserve_soc <= 60, f"Reserve {reserve_soc}% should be between 0-60%"
    
    # For the test data with ~4 hours of high-cost periods:
    # 4 hours * 1 kW = 4 kWh needed / 10 kWh capacity = 40%
    assert 30 <= reserve_soc <= 50, f"Reserve {reserve_soc}% should be around 40% for this data"


def test_optimization_with_dynamic_thresholds(nordpool_prices, solar_forecast):
    """Test that optimization with dynamic thresholds produces good results."""
    cost_strategy = CostStrategy()
    
    # Use dynamic thresholds
    dynamic_thresholds = cost_strategy.get_dynamic_thresholds(nordpool_prices)
    cost_strategy.update_thresholds(
        cheap_max=dynamic_thresholds.cheap_max,
        high_min=dynamic_thresholds.high_min
    )
    
    now = datetime.fromisoformat("2025-10-15T21:00:00+02:00")
    batt_soc_pct = 61.0
    batt_capacity_kwh = 10.0
    batt_max_charge_w = 10000
    ev_need_kwh = 0.0
    
    plan = simple_plan(
        now=now,
        horizon_hours=24,
        prices=nordpool_prices,
        solar=solar_forecast,
        batt_soc_pct=batt_soc_pct,
        batt_capacity_kwh=batt_capacity_kwh,
        batt_max_charge_w=batt_max_charge_w,
        ev_need_kwh=ev_need_kwh,
        cheap_threshold=dynamic_thresholds.cheap_max,
        cost_strategy=cost_strategy,
    )
    
    # Build price map for analysis
    price_map = {p.time.replace(minute=0, second=0, microsecond=0): p.enriched_sek_per_kwh for p in nordpool_prices}
    
    # Analyze charging actions
    charge_actions = [a for a in plan if a.charge_batt_w > 0]
    discharge_actions = [a for a in plan if a.discharge_batt_w > 0]
    
    assert len(charge_actions) > 0, "Should have some charging actions"
    assert len(discharge_actions) > 0, "Should have some discharging actions"
    
    # Calculate efficiency metrics
    charge_prices = [price_map.get(a.time, 0) for a in charge_actions]
    discharge_prices = [price_map.get(a.time, 0) for a in discharge_actions]
    
    cheap_charges = sum(1 for p in charge_prices if cost_strategy.classify_price(p).value == "cheap")
    high_discharges = sum(1 for p in discharge_prices if cost_strategy.classify_price(p).value == "high")
    
    charge_efficiency = (cheap_charges / len(charge_actions)) * 100 if charge_actions else 0
    discharge_efficiency = (high_discharges / len(discharge_actions)) * 100 if discharge_actions else 0
    overall_efficiency = (charge_efficiency + discharge_efficiency) / 2
    
    # With dynamic thresholds, efficiency should be at least FAIR (50%)
    assert overall_efficiency >= 50, f"Overall efficiency {overall_efficiency:.1f}% should be at least 50%"
    
    # Verify that average charging price is below average discharging price
    avg_charge = sum(charge_prices) / len(charge_prices)
    avg_discharge = sum(discharge_prices) / len(discharge_prices)
    
    assert avg_charge < avg_discharge, \
        f"Should charge at lower prices ({avg_charge:.3f}) than discharge ({avg_discharge:.3f})"


def test_static_vs_dynamic_thresholds_comparison(nordpool_prices, solar_forecast):
    """Compare optimization quality with static vs dynamic thresholds."""
    now = datetime.fromisoformat("2025-10-15T21:00:00+02:00")
    batt_soc_pct = 61.0
    batt_capacity_kwh = 10.0
    batt_max_charge_w = 10000
    ev_need_kwh = 0.0
    
    # Test with static thresholds (old behavior)
    cost_strategy_static = CostStrategy()
    cost_strategy_static.update_thresholds(cheap_max=1.5, high_min=3.0)
    
    plan_static = simple_plan(
        now=now,
        horizon_hours=24,
        prices=nordpool_prices,
        solar=solar_forecast,
        batt_soc_pct=batt_soc_pct,
        batt_capacity_kwh=batt_capacity_kwh,
        batt_max_charge_w=batt_max_charge_w,
        ev_need_kwh=ev_need_kwh,
        cheap_threshold=1.5,
        cost_strategy=cost_strategy_static,
    )
    
    # Test with dynamic thresholds (new behavior)
    cost_strategy_dynamic = CostStrategy()
    dynamic_thresholds = cost_strategy_dynamic.get_dynamic_thresholds(nordpool_prices)
    cost_strategy_dynamic.update_thresholds(
        cheap_max=dynamic_thresholds.cheap_max,
        high_min=dynamic_thresholds.high_min
    )
    
    plan_dynamic = simple_plan(
        now=now,
        horizon_hours=24,
        prices=nordpool_prices,
        solar=solar_forecast,
        batt_soc_pct=batt_soc_pct,
        batt_capacity_kwh=batt_capacity_kwh,
        batt_max_charge_w=batt_max_charge_w,
        ev_need_kwh=ev_need_kwh,
        cheap_threshold=dynamic_thresholds.cheap_max,
        cost_strategy=cost_strategy_dynamic,
    )
    
    # Count actions
    static_charges = sum(1 for a in plan_static if a.charge_batt_w > 0)
    static_discharges = sum(1 for a in plan_static if a.discharge_batt_w > 0)
    
    dynamic_charges = sum(1 for a in plan_dynamic if a.charge_batt_w > 0)
    dynamic_discharges = sum(1 for a in plan_dynamic if a.discharge_batt_w > 0)
    
    # Dynamic should produce more discharge actions (can identify more high-price periods)
    assert dynamic_discharges >= static_discharges, \
        f"Dynamic ({dynamic_discharges} discharges) should be >= static ({static_discharges})"
    
    # Dynamic should have better or equal activity
    total_dynamic = dynamic_charges + dynamic_discharges
    total_static = static_charges + static_discharges
    
    assert total_dynamic >= total_static, \
        f"Dynamic total actions ({total_dynamic}) should be >= static ({total_static})"
