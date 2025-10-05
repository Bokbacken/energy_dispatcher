# Changelog

## [Unreleased]
### Fixed
- **Configuration Flow Error**: Fixed additional 500 Internal Server Error edge case in weather entity enumeration
  - Root cause: `_available_weather_entities()` function had improper error handling when `hass.states` attribute doesn't exist
  - Impact: Could cause AttributeError when trying to call `async_all()` on an empty list
  - Solution: Added proper existence check using `hasattr()` before accessing `hass.states`
  - This complements the fix in v0.8.1 and handles edge cases during testing or unusual runtime conditions

## [0.8.1] - 2025-10-05
### Fixed
- **Configuration Flow Error**: Fixed 500 Internal Server Error when re-entering configuration options
  - Root cause: Options flow handler was not passing the Home Assistant instance to the schema builder
  - Impact: Users could not modify integration settings after initial setup
  - Solution: Options flow now properly passes `self.hass` to `_schema_user()` for correct entity enumeration
  - This was a minimal one-line fix ensuring backward compatibility
### Added
- **Multi-Vehicle and Multi-Charger Support**: Enhanced EV charging management
  - Support for multiple electric vehicles with different specifications
  - Vehicle presets for Tesla Model Y LR 2022 and Hyundai Ioniq Electric 2019
  - Multiple charger configurations with adapter pattern for future expansion
  - Per-vehicle state tracking (SOC, target, mode, deadline)
  - Charging session management with start/end tracking
  - Energy delivered calculation per session
  - Vehicle-charger association management
  - Charging time and energy requirement calculations

- **Advanced Charging Modes**: Flexible charging optimization strategies
  - **ASAP Mode**: Immediate charging for urgent needs
  - **Eco Mode**: Optimize for solar and cheap grid hours
  - **Deadline Mode**: Meet specific completion time requirements
  - **Cost Saver Mode**: Minimize cost with flexible timing

- **Cost Strategy Module**: Semi-intelligent energy management
  - Energy cost classification (cheap/medium/high) with configurable thresholds
  - Dynamic threshold calculation based on price distribution
  - High-cost window prediction for next 24 hours
  - Battery reserve calculation to prevent premature depletion
  - Smart charge/discharge decisions based on price and solar
  - EV charging window optimization with deadline awareness
  - Cost summary with statistics for visualization

- **Enhanced Planning**: Deadline-aware and cost-optimized charging
  - Integration with cost strategy for battery management
  - Battery reserve logic prevents depletion before high-cost periods
  - Deadline support for EV charging sessions
  - Mode-based optimization (ASAP, Eco, Deadline, Cost Saver)
  - Notes in plan actions for transparency

- **Comprehensive Documentation**:
  - `docs/multi_vehicle_setup.md`: Complete setup guide with examples
  - `examples/multi_vehicle_config.yaml`: Example configurations and automations
  - Vehicle preset specifications and charging calculations
  - Cost strategy explanation and best practices
  - Troubleshooting guide and automation examples

- **Testing**: Full test coverage for new features
  - 19 tests for vehicle manager (all passing)
  - 21 tests for cost strategy (all passing)
  - Vehicle presets validation
  - Charging session lifecycle tests
  - Cost classification and optimization tests

- **Battery Energy Cost (BEC) Module**: Comprehensive battery cost and state management
  - Tracks weighted average cost of energy (WACE) in battery
  - **Historical data storage**: Records every charge/discharge event with timestamp (15-min intervals)
  - **Data retention**: Keeps 30 days of historical data (2,880 events)
  - **Event tracking**: Distinguishes between grid and solar charging sources
  - **WACE recalculation**: Ability to recalculate from historical data
  - **History summary**: Aggregate statistics in sensor attributes
  - Automatic cost calculation during charge/discharge events
  - Persistent storage across Home Assistant restarts (Storage Version 2)
  - **Automatic migration** from Storage Version 1 to Version 2
  - Manual SOC override via `battery_cost_set_soc` service
  - Manual cost reset via `battery_cost_reset` service and button
  - Enhanced sensor with SOC, total cost, and historical statistics attributes
  - Full test coverage with 52 unit and integration tests (46 unit + 6 integration)
  - Comprehensive documentation in `docs/battery_cost_tracking.md`

### Fixed
- Solar forecast sensors now correctly display today's total energy in kWh instead of incorrectly summing all forecast points (which caused values >200000)
- Cloud-compensated sensor now exposes `cloud_coverage` and `weather_entity` attributes for debugging
- Added proper unit of measurement (kWh), device class (energy), and state class (measurement) to forecast sensors

## [0.7.0] - 2025-10-04
### Added
- Solar forecast now supports cloud compensation via weather entity, with user-configurable factors.
- Both raw and compensated solar forecasts exposed as sensors for comparison and graphing.
- Swedish and English translation files are fully populated for all config fields.
- New documentation: `docs/solar_forecast_improvement.md` describes the new solar features.

### Changed
- Config flow updated to use translation keys for all labels and descriptions.

### Fixed
- Various minor documentation and localization improvements.

---

Older changelogs omitted for brevity.
