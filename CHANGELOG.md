# Changelog

## [Unreleased]
### Added
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
