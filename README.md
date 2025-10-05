# Energy Dispatcher for Home Assistant

Smart energy management for Home Assistant users, supporting dynamic price, battery, EV, and solar optimization.

## Features

- **Multi-Vehicle Support**: Manage charging for multiple EVs with different specifications
- **Vehicle Presets**: Quick setup for Tesla Model Y LR, Hyundai Ioniq Electric, and more
- **Charging Modes**: ASAP, Eco, Deadline, and Cost Saver optimization
- **Cost Strategy**: Semi-intelligent energy cost classification and battery reserve management
- **Nordpool Price Integration**: Use real-time spot prices for smarter dispatch
- **Battery Scheduling**: Automatic and manual battery management with high-cost window anticipation
- **EV Charging Optimization**: Schedule and control EV charging sessions with deadline support
- **Solar Forecasting**: Now with cloud compensation—see below!
- **Localization**: Full support for Swedish and English, including all config fields

## New in v0.7.0: Solar Forecast Cloud Compensation

- Incorporates cloudiness from your selected weather entity.
- User-configurable output factors for 0% and 100% cloud cover.
- Exposes both raw and compensated solar forecast sensors for direct comparison.
- Supports easy graphing and testing in Home Assistant dashboards.

See [`docs/solar_forecast_improvement.md`](./docs/solar_forecast_improvement.md) for details.

## Installation

1. Copy the `energy_dispatcher` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Configure via the UI (Integrations > Add Energy Dispatcher).

## Configuration

- Fill in all required fields in the config flow.
- For cloud compensation, select your weather entity and adjust the output factors as needed.

## Sensors

- `sensor.solar_forecast_raw`: Raw solar production forecast.
- `sensor.solar_forecast_compensated`: Cloud-compensated solar production forecast.

## Documentation

- [Multi-Vehicle and Multi-Charger Setup](./docs/multi_vehicle_setup.md) ⭐ NEW
- [Configuration Guide](./docs/configuration.md)
- [Battery Cost Tracking](./docs/battery_cost_tracking.md)
- [Solar Forecast Improvement](./docs/solar_forecast_improvement.md)
- [Changelog](./CHANGELOG.md)

## Quick Start Examples

### Example 1: Tesla Model Y with Deadline Charging

```yaml
# Set up vehicle
vehicle_id: tesla_model_y_lr
current_soc: 40%
target_soc: 80%
charging_mode: deadline
deadline: tomorrow 08:00

# System will optimize charging to:
# - Meet the 08:00 deadline
# - Use cheapest electricity hours
# - Leverage solar if available
# - Preserve home battery for peak hours
```

### Example 2: Cost-Optimized Charging

```yaml
# Hyundai Ioniq with flexible timing
vehicle_id: hyundai_ioniq_electric
current_soc: 50%
target_soc: 100%
charging_mode: cost_saver

# System will:
# - Only charge during cheapest hours
# - Maximize solar usage
# - Take as long as needed for lowest cost
```

See [Multi-Vehicle Setup Guide](./docs/multi_vehicle_setup.md) for detailed examples.

## License

MIT

## Support

Open issues or feature requests on [GitHub Issues](https://github.com/Bokbacken/energy_dispatcher/issues).