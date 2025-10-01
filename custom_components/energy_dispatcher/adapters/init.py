"""
Adapters package for Energy Dispatcher.

This package contains brand- or interface-specific adapters that map the
core planner/dispatcher actions to actual Home Assistant services and entities.

Modules:
- base: abstract base classes and capability models
- huawei: Huawei SUN2000/LUNA battery adapter (via huawei_solar)
- evse_generic: Generic EVSE adapter (switch + number current control)
- ev_manual: Manual EV SOC adapter (helpers) + optional EVSE control
"""

from .base import BatteryAdapter, BatteryCapabilities  # re-export for convenience

__all__ = [
    "BatteryAdapter",
    "BatteryCapabilities",
]
