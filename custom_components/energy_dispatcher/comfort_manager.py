"""
Comfort-Aware Optimization Manager for Energy Dispatcher.

Filters and adjusts optimization recommendations based on user comfort preferences.
Supports three priority levels:
- cost_first: Maximize savings, accept some inconvenience
- balanced: Seek savings without significant comfort impact
- comfort_first: Maintain comfort, optimize within those constraints
"""
from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)


class ComfortManager:
    """Manages comfort-aware filtering of optimization recommendations."""

    def __init__(
        self,
        comfort_priority: str = "balanced",
        quiet_hours_start: time | str = "22:00",
        quiet_hours_end: time | str = "07:00",
        min_battery_peace_of_mind: float = 20.0,
    ):
        """Initialize the ComfortManager.
        
        Args:
            comfort_priority: One of "cost_first", "balanced", "comfort_first"
            quiet_hours_start: Start time for quiet hours (no inconvenient operations)
            quiet_hours_end: End time for quiet hours
            min_battery_peace_of_mind: Minimum battery % to maintain for peace of mind
        """
        self.comfort_priority = comfort_priority
        
        # Parse quiet hours if strings
        if isinstance(quiet_hours_start, str):
            parts = quiet_hours_start.split(":")
            self.quiet_hours_start = time(int(parts[0]), int(parts[1]))
        else:
            self.quiet_hours_start = quiet_hours_start
            
        if isinstance(quiet_hours_end, str):
            parts = quiet_hours_end.split(":")
            self.quiet_hours_end = time(int(parts[0]), int(parts[1]))
        else:
            self.quiet_hours_end = quiet_hours_end
            
        self.min_battery_peace_of_mind = min_battery_peace_of_mind
        
        _LOGGER.debug(
            "ComfortManager initialized: priority=%s, quiet_hours=%s-%s, min_battery=%s%%",
            comfort_priority, self.quiet_hours_start, self.quiet_hours_end, min_battery_peace_of_mind
        )

    def is_in_quiet_hours(self, dt: datetime | None = None) -> bool:
        """Check if a given time is within quiet hours.
        
        Args:
            dt: Datetime to check. If None, uses current time.
            
        Returns:
            True if the time is within quiet hours.
        """
        if dt is None:
            from homeassistant.util import dt as dt_util
            dt = dt_util.now()
        
        check_time = dt.time()
        
        # Handle quiet hours that span midnight
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Normal case: 22:00 to 23:59 or 08:00 to 17:00
            return self.quiet_hours_start <= check_time <= self.quiet_hours_end
        else:
            # Spans midnight: 22:00 to 07:00
            return check_time >= self.quiet_hours_start or check_time <= self.quiet_hours_end

    def optimize_with_comfort_balance(
        self,
        optimization_recommendations: List[Dict[str, Any]],
        battery_soc: Optional[float] = None,
        current_conditions: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Filter and adjust recommendations based on comfort priority.
        
        Args:
            optimization_recommendations: List of optimization recommendations
            battery_soc: Current battery state of charge (%)
            current_conditions: Additional current conditions (temperature, etc.)
            
        Returns:
            Tuple of (filtered_recommendations, filtered_out_recommendations)
        """
        if not optimization_recommendations:
            return [], []
        
        if self.comfort_priority == "cost_first":
            # Accept all recommendations
            _LOGGER.debug("cost_first mode: accepting all %d recommendations", len(optimization_recommendations))
            return optimization_recommendations, []
        
        filtered_recommendations = []
        filtered_out = []
        
        for rec in optimization_recommendations:
            keep = True
            filter_reason = []
            
            if self.comfort_priority == "comfort_first":
                # Filter out aggressive recommendations
                user_impact = rec.get("user_impact", "medium")
                if user_impact != "low":
                    keep = False
                    filter_reason.append(f"user_impact={user_impact}")
                
                # Maintain higher battery reserve
                if battery_soc is not None and battery_soc < 70:
                    if rec.get("action") == "discharge":
                        keep = False
                        filter_reason.append(f"battery_soc_too_low={battery_soc:.1f}%")
                
                # Don't shift loads to inconvenient times (quiet hours)
                rec_time = rec.get("recommended_time")
                if rec_time:
                    if isinstance(rec_time, dict):
                        # Handle dict with 'hour' key
                        rec_hour = rec_time.get("hour", 12)
                        rec_dt = datetime.now().replace(hour=rec_hour, minute=0, second=0, microsecond=0)
                    elif isinstance(rec_time, datetime):
                        rec_dt = rec_time
                    else:
                        rec_dt = None
                    
                    if rec_dt and self.is_in_quiet_hours(rec_dt):
                        keep = False
                        filter_reason.append("in_quiet_hours")
                
            elif self.comfort_priority == "balanced":
                # Accept moderate inconvenience for significant savings
                savings_sek = rec.get("savings_sek", 0)
                inconvenience_score = rec.get("inconvenience_score", 1)
                
                # Avoid division by zero
                if inconvenience_score == 0:
                    inconvenience_score = 0.1
                
                savings_ratio = savings_sek / inconvenience_score
                
                if savings_ratio <= 2.0:
                    keep = False
                    filter_reason.append(f"savings_ratio={savings_ratio:.2f}<=2.0")
            
            # Apply minimum battery peace of mind threshold for all modes except cost_first
            if battery_soc is not None and rec.get("action") == "discharge":
                if battery_soc <= self.min_battery_peace_of_mind:
                    keep = False
                    filter_reason.append(f"battery_below_peace_of_mind={battery_soc:.1f}%<={self.min_battery_peace_of_mind}%")
            
            if keep:
                filtered_recommendations.append(rec)
            else:
                # Add filter reason to the recommendation
                rec_copy = rec.copy()
                rec_copy["filtered_by_comfort"] = ", ".join(filter_reason)
                filtered_out.append(rec_copy)
        
        _LOGGER.debug(
            "%s mode: kept %d/%d recommendations, filtered out %d",
            self.comfort_priority,
            len(filtered_recommendations),
            len(optimization_recommendations),
            len(filtered_out)
        )
        
        return filtered_recommendations, filtered_out

    def should_allow_operation(
        self,
        operation_type: str,
        battery_soc: Optional[float] = None,
        scheduled_time: Optional[datetime] = None,
    ) -> tuple[bool, str]:
        """Check if an operation should be allowed based on comfort settings.
        
        Args:
            operation_type: Type of operation (e.g., "discharge", "charge", "load_shift")
            battery_soc: Current battery state of charge (%)
            scheduled_time: When the operation is scheduled
            
        Returns:
            Tuple of (allowed, reason)
        """
        if self.comfort_priority == "cost_first":
            return True, "cost_first_mode"
        
        # Check battery peace of mind
        if battery_soc is not None and operation_type == "discharge":
            if battery_soc <= self.min_battery_peace_of_mind:
                return False, f"battery_below_peace_of_mind_{battery_soc:.1f}%"
        
        # Check quiet hours for comfort_first mode
        if self.comfort_priority == "comfort_first":
            if scheduled_time and self.is_in_quiet_hours(scheduled_time):
                if operation_type in ["load_shift", "discharge"]:
                    return False, "in_quiet_hours"
        
        return True, "allowed"
