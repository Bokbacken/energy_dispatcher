# Changelog

## [Unreleased]
### Added
- **Enhanced Diagnostic Logging**: Added comprehensive logging for 48h baseline calculation to help troubleshoot issues
  - Logs when 48h calculation succeeds with all daypart values
  - Logs when falling back to EMA mode with helpful guidance
  - Logs when power entity is not configured
  - Logs when entering EMA fallback mode for debugging

### Fixed
- **48h Baseline Daypart Sensors**: Fixed bug where daypart sensors (Night/Day/Evening) showed "unknown" instead of values
  - Root cause: Falsy check (`if night_w`) treated 0 as False instead of checking for None
  - Fix: Changed to explicit None check (`if night_w is not None`)
  - Impact: Even 0W baselines now display correctly instead of showing "unknown"

### Changed
- **Configuration Cleanup**: Removed deprecated EMA parameters from configuration UI
  - Removed `runtime_alpha` (EMA Smoothing Factor 0-1) from config flow
  - Removed `runtime_window_min` (Calculation Windows minutes) from config flow
  - These parameters are kept in code for backward compatibility (EMA fallback mode)
  - Existing configurations will continue to work without changes

### Removed
- **Code Cleanup**: Archived unused files to `archive/` directory
  - `planner.py`: simple_plan() function was never imported or used
  - `vehicle_manager.py`: VehicleManager class was never imported or used
  - Files can be restored from archive if needed in the future

### Added
- **Automated Dashboard Setup Assistance**: New users now receive a helpful welcome notification
  - Persistent notification appears after integration setup with dashboard guidance
  - Provides direct link to comprehensive Dashboard Setup Guide
  - Lists available entity patterns for easy dashboard creation
  - Can be disabled by setting `auto_create_dashboard: false` in configuration
  - Graceful error handling ensures setup never fails due to notification issues
  - Implements PR-1 from Future Improvements roadmap

- **Manual PV Forecast Engine (Physics-Based)**: Free alternative to Forecast.Solar using weather data
  - Physics-based solar power forecasting using Home Assistant weather integrations
  - No API costs or external dependencies beyond weather data
  - Tier-based adaptation: DNI/DHI (best) → GHI → Cloud cover → Clear-sky (fallback)
  - Weather capability detection sensor showing available data fields
  - Industry-standard models:
    - **Haurwitz**: Simple clear-sky GHI calculation
    - **Kasten-Czeplak**: Cloud cover to GHI mapping
    - **Erbs**: GHI decomposition to DNI/DHI
    - **HDKR**: Plane-of-array transposition with anisotropic diffuse
    - **PVWatts**: DC and AC power calculation with temperature effects
  - Built-in horizon blocking with 12-point interpolation
  - Cell temperature modeling with wind cooling effects
  - Optional per-plane calibration (framework ready, implementation pending)
  - Configurable settings:
    - Time step: 15, 30, or 60 minutes
    - Diffuse sky-view factor: 0.7-1.0
    - Temperature coefficient: customizable per installation
    - System-level inverter AC cap
  - New sensor: `sensor.weather_forecast_capabilities` showing detected weather data
  - Comprehensive unit tests for all physics calculations (17 tests passing)
  - Complete documentation in `docs/manual_forecast.md`

### Fixed
- **Configuration Flow Error**: Fixed remaining 500 Internal Server Error edge cases in weather entity enumeration (PR #19 follow-up)
  - Root cause: `_available_weather_entities()` function had insufficient error handling even after `hasattr()` check was added
  - Impact: Could still cause AttributeError or TypeError when:
    - `hass.states` exists but is None
    - `hass.states.async_all()` method doesn't exist
    - `hass.states.async_all()` raises exceptions during execution
  - Solution: Wrapped the entire entity enumeration logic in try-except block to catch AttributeError and TypeError
  - Added comprehensive test coverage for all edge cases (5 new tests)
  - This fully resolves the configuration flow errors reported in PR #19

- **Options Flow Handler Error**: Fixed 500 Internal Server Error by modernizing to Home Assistant 2025.12+ pattern
  - Root cause: The `async_get_options_flow` method was passing `config_entry` to the constructor, but `EnergyDispatcherOptionsFlowHandler` didn't accept it (TypeError)
  - Impact: Users got 500 Internal Server Error when trying to modify integration settings
  - Previous attempt: Version 0.7.7 had an `__init__` method (deprecated pattern scheduled for removal in 2025.12), which was removed in 0.7.8
  - Solution: Use modern Home Assistant pattern where `config_entry` is automatically available as a property from the `OptionsFlow` base class
  - Changed `EnergyDispatcherOptionsFlowHandler(config_entry)` to `EnergyDispatcherOptionsFlowHandler()` in `async_get_options_flow`
  - This is the proper long-term solution that aligns with Home Assistant's architecture and avoids deprecated code patterns

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
