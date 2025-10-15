"""Tests for peak shaving logic."""
import pytest

from custom_components.energy_dispatcher.peak_shaving import PeakShaving


@pytest.fixture
def peak_shaver():
    """Create a PeakShaving instance."""
    return PeakShaving(
        min_shaving_duration_h=0.5,
        min_shaving_power_w=500.0,
    )


class TestPeakShavingAction:
    """Test peak shaving action calculation."""

    def test_no_action_within_threshold(self, peak_shaver):
        """Test no action when within peak threshold."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=8000.0,
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is False
        assert result["discharge_power_w"] == 0
        assert "Within peak threshold" in result["reason"]

    def test_discharge_when_exceeding_threshold(self, peak_shaver):
        """Test battery discharge when exceeding peak threshold."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is True
        assert result["discharge_power_w"] == 2000  # Excess: 12000 - 10000
        assert result["peak_reduction_w"] == 2000
        assert result["duration_estimate_h"] > 0

    def test_no_action_at_reserve_soc(self, peak_shaver):
        """Test no discharge when battery is at reserve level."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=20.0,  # At reserve level
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is False
        assert "at reserve level" in result["reason"]

    def test_no_action_below_reserve_soc(self, peak_shaver):
        """Test no discharge when battery is below reserve level."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=15.0,  # Below reserve
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is False
        assert "at reserve level" in result["reason"]

    def test_discharge_limited_by_battery_max(self, peak_shaver):
        """Test discharge is limited by battery max discharge power."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=20000.0,
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=3000,  # Lower than excess
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is True
        # Should be limited to battery max, not full excess (10000W)
        assert result["discharge_power_w"] == 3000

    def test_duration_calculation(self, peak_shaver):
        """Test discharge duration calculation."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        # Available energy: (60% - 20%) * 15kWh = 6kWh
        # Discharge power: 2000W = 2kW
        # Duration: 6kWh / 2kW = 3 hours
        assert result["discharge_battery"] is True
        assert result["duration_estimate_h"] == pytest.approx(3.0, rel=0.01)

    def test_insufficient_duration(self, peak_shaver):
        """Test no action when discharge duration too short."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=21.0,  # Just above reserve
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        # Available energy: (21% - 20%) * 15kWh = 0.15kWh
        # Discharge power: 2000W
        # Duration: 0.15kWh / 2kW = 0.075h < 0.5h threshold
        assert result["discharge_battery"] is False
        assert "Insufficient battery capacity" in result["reason"]

    def test_minimum_power_threshold(self, peak_shaver):
        """Test no action when excess is below minimum power threshold."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=10200.0,  # Only 200W excess
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is False
        assert "below minimum" in result["reason"]

    def test_exact_threshold_match(self, peak_shaver):
        """Test no action when exactly at threshold."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=10000.0,  # Exactly at threshold
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is False

    def test_large_excess(self, peak_shaver):
        """Test handling of very large excess."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=25000.0,
            peak_threshold_w=10000.0,
            battery_soc=80.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        assert result["discharge_battery"] is True
        # Discharge limited by battery max (5000W), not full excess (15000W)
        assert result["discharge_power_w"] == 5000

    def test_high_soc_long_duration(self, peak_shaver):
        """Test long duration with high SOC."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=90.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        # Available energy: (90% - 20%) * 15kWh = 10.5kWh
        # Discharge power: 2000W = 2kW
        # Duration: 10.5kWh / 2kW = 5.25 hours
        assert result["discharge_battery"] is True
        assert result["duration_estimate_h"] == pytest.approx(5.25, rel=0.01)

    def test_minimum_soc_margin(self, peak_shaver):
        """Test with very small SOC margin above reserve."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=25.0,  # 5% above reserve
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        # Available energy: (25% - 20%) * 15kWh = 0.75kWh
        # Discharge power: 2000W = 2kW
        # Duration: 0.75kWh / 2kW = 0.375h < 0.5h threshold
        assert result["discharge_battery"] is False

    def test_result_structure(self, peak_shaver):
        """Test that result dictionary has all required keys."""
        result = peak_shaver.calculate_peak_shaving_action(
            current_grid_import_w=12000.0,
            peak_threshold_w=10000.0,
            battery_soc=60.0,
            battery_max_discharge_w=5000,
            battery_reserve_soc=20.0,
            battery_capacity_kwh=15.0,
            solar_production_w=0.0,
        )
        
        # Verify all expected keys are present
        assert "discharge_battery" in result
        assert "discharge_power_w" in result
        assert "duration_estimate_h" in result
        assert "peak_reduction_w" in result
        assert "reason" in result
        
        # Verify types
        assert isinstance(result["discharge_battery"], bool)
        assert isinstance(result["discharge_power_w"], int)
        assert isinstance(result["duration_estimate_h"], (int, float))
        assert isinstance(result["peak_reduction_w"], int)
        assert isinstance(result["reason"], str)
