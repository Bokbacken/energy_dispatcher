"""Unit tests for ComfortManager."""
import pytest
from datetime import datetime, time
from custom_components.energy_dispatcher.comfort_manager import ComfortManager


class TestComfortManagerInit:
    """Test ComfortManager initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        manager = ComfortManager()
        assert manager.comfort_priority == "balanced"
        assert manager.quiet_hours_start == time(22, 0)
        assert manager.quiet_hours_end == time(7, 0)
        assert manager.min_battery_peace_of_mind == 20.0

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        manager = ComfortManager(
            comfort_priority="comfort_first",
            quiet_hours_start="23:30",
            quiet_hours_end="06:00",
            min_battery_peace_of_mind=30.0,
        )
        assert manager.comfort_priority == "comfort_first"
        assert manager.quiet_hours_start == time(23, 30)
        assert manager.quiet_hours_end == time(6, 0)
        assert manager.min_battery_peace_of_mind == 30.0

    def test_init_with_time_objects(self):
        """Test initialization with time objects."""
        start = time(21, 0)
        end = time(8, 0)
        manager = ComfortManager(
            quiet_hours_start=start,
            quiet_hours_end=end,
        )
        assert manager.quiet_hours_start == start
        assert manager.quiet_hours_end == end


class TestQuietHours:
    """Test quiet hours functionality."""

    def test_is_in_quiet_hours_normal_range(self):
        """Test quiet hours check for normal time range (08:00-17:00)."""
        manager = ComfortManager(
            quiet_hours_start="08:00",
            quiet_hours_end="17:00"
        )
        
        # Inside quiet hours
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 10, 0)) is True
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 8, 0)) is True
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 17, 0)) is True
        
        # Outside quiet hours
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 7, 59)) is False
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 17, 1)) is False
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 23, 0)) is False

    def test_is_in_quiet_hours_spans_midnight(self):
        """Test quiet hours check when range spans midnight (22:00-07:00)."""
        manager = ComfortManager(
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        
        # Inside quiet hours (evening)
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 22, 0)) is True
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 23, 30)) is True
        
        # Inside quiet hours (morning)
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 0, 0)) is True
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 6, 30)) is True
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 7, 0)) is True
        
        # Outside quiet hours
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 7, 1)) is False
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 12, 0)) is False
        assert manager.is_in_quiet_hours(datetime(2024, 1, 1, 21, 59)) is False


class TestCostFirstMode:
    """Test cost_first priority mode."""

    def test_cost_first_accepts_all_recommendations(self):
        """Test that cost_first mode accepts all recommendations."""
        manager = ComfortManager(comfort_priority="cost_first")
        
        recommendations = [
            {"action": "discharge", "user_impact": "high", "savings_sek": 1.0, "inconvenience_score": 10},
            {"action": "discharge", "user_impact": "medium", "savings_sek": 5.0, "inconvenience_score": 5},
            {"action": "charge", "user_impact": "low", "savings_sek": 10.0, "inconvenience_score": 1},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=10.0
        )
        
        assert len(filtered) == 3
        assert len(filtered_out) == 0

    def test_cost_first_ignores_battery_peace_of_mind(self):
        """Test that cost_first mode ignores battery peace of mind threshold."""
        manager = ComfortManager(
            comfort_priority="cost_first",
            min_battery_peace_of_mind=50.0
        )
        
        recommendations = [
            {"action": "discharge", "savings_sek": 10.0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=10.0  # Well below peace of mind threshold
        )
        
        # Should not filter even though battery is low
        assert len(filtered) == 1
        assert len(filtered_out) == 0


class TestBalancedMode:
    """Test balanced priority mode."""

    def test_balanced_filters_by_savings_ratio(self):
        """Test that balanced mode filters by savings/inconvenience ratio."""
        manager = ComfortManager(comfort_priority="balanced")
        
        recommendations = [
            {"action": "charge", "savings_sek": 10.0, "inconvenience_score": 2.0},  # Ratio 5.0 > 2.0 ✓
            {"action": "discharge", "savings_sek": 5.0, "inconvenience_score": 5.0},  # Ratio 1.0 <= 2.0 ✗
            {"action": "charge", "savings_sek": 8.0, "inconvenience_score": 3.0},  # Ratio 2.67 > 2.0 ✓
            {"action": "discharge", "savings_sek": 2.0, "inconvenience_score": 1.0},  # Ratio 2.0 <= 2.0 ✗
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=50.0
        )
        
        assert len(filtered) == 2
        assert len(filtered_out) == 2
        assert filtered[0]["savings_sek"] == 10.0
        assert filtered[1]["savings_sek"] == 8.0

    def test_balanced_respects_battery_peace_of_mind(self):
        """Test that balanced mode respects battery peace of mind threshold."""
        manager = ComfortManager(
            comfort_priority="balanced",
            min_battery_peace_of_mind=30.0
        )
        
        recommendations = [
            {"action": "discharge", "savings_sek": 100.0, "inconvenience_score": 10.0},  # High ratio
            {"action": "charge", "savings_sek": 50.0, "inconvenience_score": 10.0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=25.0  # Below peace of mind threshold
        )
        
        # Discharge should be filtered, charge should pass
        assert len(filtered) == 1
        assert len(filtered_out) == 1
        assert filtered[0]["action"] == "charge"
        assert filtered_out[0]["action"] == "discharge"
        assert "battery_below_peace_of_mind" in filtered_out[0]["filtered_by_comfort"]


class TestComfortFirstMode:
    """Test comfort_first priority mode."""

    def test_comfort_first_filters_by_user_impact(self):
        """Test that comfort_first mode only accepts low impact recommendations."""
        manager = ComfortManager(comfort_priority="comfort_first")
        
        recommendations = [
            {"action": "charge", "user_impact": "low", "savings_sek": 5.0},
            {"action": "discharge", "user_impact": "medium", "savings_sek": 10.0},
            {"action": "charge", "user_impact": "high", "savings_sek": 15.0},
            {"action": "discharge", "user_impact": "low", "savings_sek": 3.0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=80.0
        )
        
        assert len(filtered) == 2
        assert all(rec["user_impact"] == "low" for rec in filtered)
        assert len(filtered_out) == 2

    def test_comfort_first_filters_discharge_when_soc_low(self):
        """Test that comfort_first filters discharge when battery SOC < 70%."""
        manager = ComfortManager(comfort_priority="comfort_first")
        
        recommendations = [
            {"action": "discharge", "user_impact": "low", "savings_sek": 10.0},
            {"action": "charge", "user_impact": "low", "savings_sek": 5.0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=60.0  # Below 70%
        )
        
        assert len(filtered) == 1
        assert filtered[0]["action"] == "charge"
        assert len(filtered_out) == 1
        assert filtered_out[0]["action"] == "discharge"
        assert "battery_soc_too_low" in filtered_out[0]["filtered_by_comfort"]

    def test_comfort_first_allows_discharge_when_soc_high(self):
        """Test that comfort_first allows discharge when battery SOC >= 70%."""
        manager = ComfortManager(comfort_priority="comfort_first")
        
        recommendations = [
            {"action": "discharge", "user_impact": "low", "savings_sek": 10.0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=75.0  # Above 70%
        )
        
        assert len(filtered) == 1
        assert len(filtered_out) == 0

    def test_comfort_first_filters_quiet_hours(self):
        """Test that comfort_first filters recommendations during quiet hours."""
        manager = ComfortManager(
            comfort_priority="comfort_first",
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        
        recommendations = [
            {
                "action": "discharge",
                "user_impact": "low",
                "recommended_time": datetime(2024, 1, 1, 23, 0),  # During quiet hours
                "savings_sek": 10.0
            },
            {
                "action": "charge",
                "user_impact": "low",
                "recommended_time": datetime(2024, 1, 1, 10, 0),  # Outside quiet hours
                "savings_sek": 5.0
            },
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=80.0
        )
        
        assert len(filtered) == 1
        assert filtered[0]["recommended_time"].hour == 10
        assert len(filtered_out) == 1
        assert "in_quiet_hours" in filtered_out[0]["filtered_by_comfort"]

    def test_comfort_first_handles_dict_recommended_time(self):
        """Test that comfort_first handles dict format for recommended_time."""
        manager = ComfortManager(
            comfort_priority="comfort_first",
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        
        recommendations = [
            {
                "action": "discharge",
                "user_impact": "low",
                "recommended_time": {"hour": 23},  # During quiet hours
                "savings_sek": 10.0
            },
            {
                "action": "charge",
                "user_impact": "low",
                "recommended_time": {"hour": 10},  # Outside quiet hours
                "savings_sek": 5.0
            },
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=80.0
        )
        
        assert len(filtered) == 1
        assert len(filtered_out) == 1
        assert "in_quiet_hours" in filtered_out[0]["filtered_by_comfort"]


class TestShouldAllowOperation:
    """Test should_allow_operation method."""

    def test_cost_first_allows_all_operations(self):
        """Test that cost_first allows all operations."""
        manager = ComfortManager(comfort_priority="cost_first")
        
        allowed, reason = manager.should_allow_operation(
            "discharge",
            battery_soc=10.0,
            scheduled_time=datetime(2024, 1, 1, 23, 0)
        )
        
        assert allowed is True
        assert reason == "cost_first_mode"

    def test_balanced_checks_battery_peace_of_mind(self):
        """Test that balanced mode checks battery peace of mind."""
        manager = ComfortManager(
            comfort_priority="balanced",
            min_battery_peace_of_mind=30.0
        )
        
        # Below threshold
        allowed, reason = manager.should_allow_operation(
            "discharge",
            battery_soc=25.0
        )
        assert allowed is False
        assert "battery_below_peace_of_mind" in reason
        
        # Above threshold
        allowed, reason = manager.should_allow_operation(
            "discharge",
            battery_soc=35.0
        )
        assert allowed is True
        assert reason == "allowed"

    def test_comfort_first_checks_quiet_hours(self):
        """Test that comfort_first checks quiet hours for operations."""
        manager = ComfortManager(
            comfort_priority="comfort_first",
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        
        # During quiet hours
        allowed, reason = manager.should_allow_operation(
            "discharge",
            scheduled_time=datetime(2024, 1, 1, 23, 0)
        )
        assert allowed is False
        assert reason == "in_quiet_hours"
        
        # Outside quiet hours
        allowed, reason = manager.should_allow_operation(
            "discharge",
            scheduled_time=datetime(2024, 1, 1, 10, 0)
        )
        assert allowed is True
        assert reason == "allowed"

    def test_comfort_first_allows_charge_during_quiet_hours(self):
        """Test that comfort_first allows charging during quiet hours."""
        manager = ComfortManager(
            comfort_priority="comfort_first",
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        
        # Charging during quiet hours should be allowed
        allowed, reason = manager.should_allow_operation(
            "charge",
            scheduled_time=datetime(2024, 1, 1, 23, 0)
        )
        assert allowed is True
        assert reason == "allowed"


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_recommendations_list(self):
        """Test handling of empty recommendations list."""
        manager = ComfortManager()
        
        filtered, filtered_out = manager.optimize_with_comfort_balance([])
        
        assert filtered == []
        assert filtered_out == []

    def test_none_battery_soc(self):
        """Test handling when battery_soc is None."""
        manager = ComfortManager(comfort_priority="balanced")
        
        recommendations = [
            {"action": "discharge", "savings_sek": 10.0, "inconvenience_score": 2.0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=None
        )
        
        # Should still work without battery_soc
        assert len(filtered) == 1

    def test_zero_inconvenience_score(self):
        """Test handling of zero inconvenience_score (division by zero)."""
        manager = ComfortManager(comfort_priority="balanced")
        
        recommendations = [
            {"action": "charge", "savings_sek": 5.0, "inconvenience_score": 0},
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=50.0
        )
        
        # Should handle gracefully (converts 0 to 0.1)
        # Ratio becomes 5.0 / 0.1 = 50.0 > 2.0, so should pass
        assert len(filtered) == 1

    def test_missing_user_impact_defaults_to_medium(self):
        """Test that missing user_impact defaults to 'medium'."""
        manager = ComfortManager(comfort_priority="comfort_first")
        
        recommendations = [
            {"action": "charge"},  # No user_impact specified
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=80.0
        )
        
        # Should be filtered (defaults to medium, which is not low)
        assert len(filtered) == 0
        assert len(filtered_out) == 1

    def test_recommendation_without_recommended_time(self):
        """Test handling of recommendation without recommended_time."""
        manager = ComfortManager(comfort_priority="comfort_first")
        
        recommendations = [
            {"action": "charge", "user_impact": "low"},  # No recommended_time
        ]
        
        filtered, filtered_out = manager.optimize_with_comfort_balance(
            recommendations,
            battery_soc=80.0
        )
        
        # Should pass (no quiet hours check without time)
        assert len(filtered) == 1
