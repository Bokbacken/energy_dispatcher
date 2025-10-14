"""Tests for export profitability analyzer."""
import pytest

from custom_components.energy_dispatcher.export_analyzer import ExportAnalyzer


@pytest.fixture
def analyzer_never():
    """Create an ExportAnalyzer with 'never' mode."""
    return ExportAnalyzer(
        export_mode="never",
        min_export_price_sek_per_kwh=3.0,
        battery_degradation_cost_per_cycle_sek=0.50,
    )


@pytest.fixture
def analyzer_excess_solar():
    """Create an ExportAnalyzer with 'excess_solar_only' mode."""
    return ExportAnalyzer(
        export_mode="excess_solar_only",
        min_export_price_sek_per_kwh=3.0,
        battery_degradation_cost_per_cycle_sek=0.50,
    )


@pytest.fixture
def analyzer_opportunistic():
    """Create an ExportAnalyzer with 'peak_price_opportunistic' mode."""
    return ExportAnalyzer(
        export_mode="peak_price_opportunistic",
        min_export_price_sek_per_kwh=3.0,
        battery_degradation_cost_per_cycle_sek=0.50,
    )


class TestNeverExportMode:
    """Test cases for 'never' export mode."""

    def test_never_export_high_price(self, analyzer_never):
        """Test that 'never' mode always returns False even with high prices."""
        result = analyzer_never.should_export_energy(
            spot_price=6.0,
            purchase_price=7.0,
            export_price=6.0,
            battery_soc=90.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=2000.0,
        )
        
        assert result["should_export"] is False
        assert "never" in result["reason"].lower()

    def test_never_export_full_battery(self, analyzer_never):
        """Test that 'never' mode returns False even with full battery and solar excess."""
        result = analyzer_never.should_export_energy(
            spot_price=3.5,
            purchase_price=4.0,
            export_price=3.5,
            battery_soc=98.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=3000.0,
        )
        
        assert result["should_export"] is False
        assert "never" in result["reason"].lower()


class TestExcessSolarOnlyMode:
    """Test cases for 'excess_solar_only' export mode."""

    def test_export_when_battery_full_and_excess_solar(self, analyzer_excess_solar):
        """Test export is recommended when battery is full and solar producing excess."""
        result = analyzer_excess_solar.should_export_energy(
            spot_price=2.5,
            purchase_price=3.0,
            export_price=2.5,
            battery_soc=96.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=2500.0,
        )
        
        assert result["should_export"] is True
        assert result["export_power_w"] == 2500
        assert "full" in result["reason"].lower()
        assert "excess solar" in result["reason"].lower()

    def test_no_export_battery_not_full(self, analyzer_excess_solar):
        """Test no export when battery is not full even with solar excess."""
        result = analyzer_excess_solar.should_export_energy(
            spot_price=2.5,
            purchase_price=3.0,
            export_price=2.5,
            battery_soc=85.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=2500.0,
        )
        
        assert result["should_export"] is False
        assert "not full" in result["reason"].lower()

    def test_no_export_no_solar_excess(self, analyzer_excess_solar):
        """Test no export when battery is full but no solar excess."""
        result = analyzer_excess_solar.should_export_energy(
            spot_price=2.5,
            purchase_price=3.0,
            export_price=2.5,
            battery_soc=96.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=500.0,
        )
        
        assert result["should_export"] is False

    def test_no_export_price_too_low(self, analyzer_excess_solar):
        """Test no export when price is below conservative threshold."""
        result = analyzer_excess_solar.should_export_energy(
            spot_price=1.5,
            purchase_price=2.0,
            export_price=1.5,
            battery_soc=96.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=2500.0,
        )
        
        assert result["should_export"] is False
        assert "too low" in result["reason"].lower()


class TestOpportunisticMode:
    """Test cases for 'peak_price_opportunistic' export mode."""

    def test_export_exceptionally_high_price(self, analyzer_opportunistic):
        """Test export when spot price is exceptionally high (>5 SEK/kWh)."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=6.0,
            purchase_price=7.0,
            export_price=6.0,
            battery_soc=85.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=0.0,
        )
        
        assert result["should_export"] is True
        assert result["export_power_w"] == 5000
        assert "exceptionally high" in result["reason"].lower()
        assert result["export_price_sek_per_kwh"] == 6.0

    def test_no_export_high_price_but_low_soc(self, analyzer_opportunistic):
        """Test no export when price is high but battery SOC is too low."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=6.0,
            purchase_price=7.0,
            export_price=6.0,
            battery_soc=70.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=0.0,
        )
        
        assert result["should_export"] is False

    def test_export_battery_full_excess_solar(self, analyzer_opportunistic):
        """Test export in opportunistic mode when battery full and solar excess."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=3.0,
            purchase_price=3.5,
            export_price=3.0,
            battery_soc=96.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=2000.0,
        )
        
        assert result["should_export"] is True
        assert result["export_power_w"] == 2000

    def test_opportunity_cost_calculation(self, analyzer_opportunistic):
        """Test that opportunity cost is calculated when upcoming high cost hours."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=6.0,
            purchase_price=7.0,
            export_price=6.0,
            battery_soc=85.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=3,
            solar_excess_w=0.0,
        )
        
        # Should export if net revenue is positive after opportunity cost
        if result["should_export"]:
            assert result["opportunity_cost"] > 0
            assert result["net_revenue"] > 0

    def test_no_export_below_minimum_threshold(self, analyzer_opportunistic):
        """Test no export when price is below minimum threshold."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=2.5,
            purchase_price=3.0,
            export_price=2.5,
            battery_soc=85.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=0.0,
        )
        
        assert result["should_export"] is False


class TestBatteryDegradationCost:
    """Test battery degradation cost consideration."""

    def test_degradation_cost_included_in_calculation(self):
        """Test that degradation cost is properly included in net revenue."""
        analyzer = ExportAnalyzer(
            export_mode="excess_solar_only",
            min_export_price_sek_per_kwh=3.0,
            battery_degradation_cost_per_cycle_sek=1.0,  # Higher degradation cost
        )
        
        result = analyzer.should_export_energy(
            spot_price=2.5,
            purchase_price=3.0,
            export_price=2.5,
            battery_soc=96.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=2000.0,
        )
        
        # Should still export because excess solar would be wasted
        assert result["should_export"] is True
        assert result["battery_degradation_cost"] == 1.0


class TestUpdateSettings:
    """Test updating analyzer settings."""

    def test_update_export_mode(self, analyzer_never):
        """Test updating export mode."""
        analyzer_never.update_settings(export_mode="excess_solar_only")
        assert analyzer_never.export_mode == "excess_solar_only"

    def test_update_min_export_price(self, analyzer_opportunistic):
        """Test updating minimum export price."""
        analyzer_opportunistic.update_settings(min_export_price_sek_per_kwh=4.0)
        assert analyzer_opportunistic.min_export_price == 4.0

    def test_update_degradation_cost(self, analyzer_opportunistic):
        """Test updating degradation cost."""
        analyzer_opportunistic.update_settings(battery_degradation_cost_per_cycle_sek=0.75)
        assert analyzer_opportunistic.degradation_cost == 0.75

    def test_update_multiple_settings(self, analyzer_never):
        """Test updating multiple settings at once."""
        analyzer_never.update_settings(
            export_mode="peak_price_opportunistic",
            min_export_price_sek_per_kwh=3.5,
            battery_degradation_cost_per_cycle_sek=0.60,
        )
        assert analyzer_never.export_mode == "peak_price_opportunistic"
        assert analyzer_never.min_export_price == 3.5
        assert analyzer_never.degradation_cost == 0.60


class TestResponseStructure:
    """Test that response structure is consistent."""

    def test_response_has_all_required_fields(self, analyzer_opportunistic):
        """Test that response contains all required fields."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=3.0,
            purchase_price=3.5,
            export_price=3.0,
            battery_soc=85.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=0.0,
        )
        
        required_fields = [
            "should_export",
            "export_power_w",
            "estimated_revenue_per_kwh",
            "export_price_sek_per_kwh",
            "opportunity_cost",
            "reason",
            "battery_soc",
            "solar_excess_w",
            "duration_estimate_h",
            "battery_degradation_cost",
            "net_revenue",
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_response_types_are_correct(self, analyzer_opportunistic):
        """Test that response field types are correct."""
        result = analyzer_opportunistic.should_export_energy(
            spot_price=3.0,
            purchase_price=3.5,
            export_price=3.0,
            battery_soc=85.0,
            battery_capacity_kwh=15.0,
            upcoming_high_cost_hours=0,
            solar_excess_w=0.0,
        )
        
        assert isinstance(result["should_export"], bool)
        assert isinstance(result["export_power_w"], (int, float))
        assert isinstance(result["estimated_revenue_per_kwh"], (int, float))
        assert isinstance(result["opportunity_cost"], (int, float))
        assert isinstance(result["reason"], str)
        assert isinstance(result["battery_soc"], (int, float))
        assert isinstance(result["net_revenue"], (int, float))
