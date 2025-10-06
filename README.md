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
- **Solar Forecasting**: Dual-engine support (Forecast.Solar + Manual Physics-Based) with cloud compensation
- **Localization**: Full support for Swedish and English, including all config fields

## New: Manual PV Forecast Engine (Physics-Based) 🌤️☀️

Free, physics-based solar forecasting using your Home Assistant weather data! No API costs.

**Features:**
- **Tier-based weather adaptation**: Automatically uses best available data (DNI/DHI → GHI → Cloud cover)
- **Weather capability detection**: See exactly what data your weather provider supports
- **Industry-standard models**: Haurwitz, Kasten-Czeplak, Erbs, HDKR, PVWatts
- **Horizon blocking**: Full 12-point horizon support built-in
- **Temperature effects**: Accounts for panel temperature and wind cooling
- **Optional calibration**: Future per-plane calibration to tune accuracy

**When to use:**
- You want free forecasting without API costs
- Your weather provider has good irradiance or cloud data
- You want transparent, customizable calculations
- You're willing to spend time on initial setup

See [`docs/manual_forecast.md`](./docs/manual_forecast.md) for complete documentation.

**Cloud Compensation (Forecast.Solar):**
- Incorporates cloudiness from your selected weather entity
- User-configurable output factors for 0% and 100% cloud cover
- Exposes both raw and compensated solar forecast sensors

See [`docs/solar_forecast_improvement.md`](./docs/solar_forecast_improvement.md) for details.

## Installation

1. Copy the `energy_dispatcher` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Configure via the UI (Integrations > Add Energy Dispatcher).

## Quick Start

After installation:

1. **Configure the Integration**: Settings → Devices & Services → Add Integration → Energy Dispatcher
2. **Create Your Dashboard**: Follow the [Dashboard Setup Guide](./docs/dashboard_guide.md) for a step-by-step walkthrough
3. **Set Your Preferences**: Adjust EV target SOC and battery floor using the number entities
4. **Monitor & Control**: Use the dashboard to monitor optimization and override when needed

The [Dashboard Guide](./docs/dashboard_guide.md) explains:
- ✅ Where to enter different types of code (helpers, dashboards, automations, etc.)
- ✅ How to create a main control dashboard
- ✅ How to add EV and battery charge overrides
- ✅ How to visualize price forecasts and solar production
- ✅ Which cards to use and why

## Configuration

- Fill in all required fields in the config flow.
- For cloud compensation, select your weather entity and adjust the output factors as needed.
- See [Configuration Guide](./docs/configuration.md) for detailed information on each setting.

## Sensors

- `sensor.solar_forecast_raw`: Raw solar production forecast.
- `sensor.solar_forecast_compensated`: Cloud-compensated solar production forecast.

## Documentation

### Getting Started
- [Dashboard Setup Guide](./docs/dashboard_guide.md) ⭐ **START HERE** - Step-by-step dashboard creation
- [Configuration Guide](./docs/configuration.md) - Complete configuration reference

### Features & Setup
- [Multi-Vehicle and Multi-Charger Setup](./docs/multi_vehicle_setup.md) - Managing multiple EVs
- [Battery Cost Tracking](./docs/battery_cost_tracking.md) - Understanding battery economics
- [Manual PV Forecast (Physics-Based)](./docs/manual_forecast.md) - Free solar forecasting
- [Solar Forecast Improvement (Cloud Compensation)](./docs/solar_forecast_improvement.md) - Cloud-based adjustments

### Reference & Planning
- [Quick Reference](./docs/QUICK_REFERENCE.md) - Command cheat sheet
- [Future Improvements](./docs/future_improvements.md) - Planned usability enhancements
- [Changelog](./CHANGELOG.md) - Version history

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