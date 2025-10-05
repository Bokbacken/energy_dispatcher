# Energy Dispatcher for Home Assistant

Smart energy management for Home Assistant users, supporting dynamic price, battery, EV, and solar optimization.

## Features

- **Nordpool Price Integration**: Use real-time spot prices for smarter dispatch.
- **Battery Scheduling**: Automatic and manual battery management.
- **EV Charging Optimization**: Schedule and control EV charging sessions.
- **Solar Forecasting**: Now with cloud compensation—see below!
- **Localization**: Full support for Swedish and English, including all config fields.

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

- [Battery Cost Tracking](./docs/battery_cost_tracking.md)
- [Solar Forecast Improvement](./docs/solar_forecast_improvement.md)
- [Changelog](./CHANGELOG.md)

## License

MIT

## Support

Open issues or feature requests on [GitHub Issues](https://github.com/Bokbacken/energy_dispatcher/issues).