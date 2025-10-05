# Changelog

## [Unreleased]
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
