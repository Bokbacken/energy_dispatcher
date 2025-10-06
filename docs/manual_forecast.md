# Manual PV Forecast Engine (Physics-Based)

## Overview

The Manual PV Forecast Engine provides a free, physics-based alternative to Forecast.Solar for generating solar power forecasts. It uses publicly available weather data combined with your solar installation parameters to calculate expected power output.

## Key Features

- **No API costs**: Works with any Home Assistant weather integration
- **Physics-based modeling**: Uses established solar radiation and PV performance models
- **Adaptive to data availability**: Automatically selects best calculation path based on available weather data
- **Transparent calculations**: All formulas and assumptions are documented
- **Optional calibration**: Can be tuned to match your specific system characteristics

## When to Use Manual Forecast

**Choose Manual (Physics) if:**
- You want to avoid paid API subscriptions
- Your weather provider has good irradiance or cloud cover data
- You want full control over the forecast model
- You're willing to spend time on initial calibration

**Stick with Forecast.Solar if:**
- You want plug-and-play simplicity
- You have an API key with horizon support
- You don't have reliable weather data
- You prefer externally validated forecasts

## Configuration

### Basic Setup

1. **Enable Solar Forecasting** (`fs_use`): `True`
2. **Forecast Source** (`forecast_source`): Select `manual_physics`
3. **Weather Entity** (`weather_entity`): Select your weather integration
4. **Location** (`fs_lat`, `fs_lon`): Your installation coordinates
5. **Solar Arrays** (`fs_planes`): JSON array of your panels (same format as Forecast.Solar)
6. **Horizon** (`fs_horizon`): CSV with 12 altitude values

### Advanced Settings

#### Time Step (`manual_step_minutes`)
- **Options**: 15, 30, or 60 minutes
- **Default**: 15 minutes
- **Recommendation**: Use 15 for best accuracy, 30 for reduced computation

#### Diffuse Sky View Factor (`manual_diffuse_sky_view_factor`)
- **Range**: 0.7 to 1.0
- **Default**: 0.95
- **Description**: Fraction of diffuse sky radiation received (accounts for horizon blocking)
- **Recommendation**: Leave at 0.95 unless you have significant horizon obstruction

#### Temperature Coefficient (`manual_temp_coeff_pct_per_c`)
- **Range**: -0.2 to -0.5 %/°C
- **Default**: -0.38 %/°C
- **Description**: How much panel efficiency decreases per degree Celsius above 25°C
- **Recommendation**: Check your panel datasheet; typical silicon modules are -0.35 to -0.45 %/°C

#### Inverter AC Cap (`manual_inverter_ac_kw_cap`)
- **Type**: Float (kW) or None
- **Default**: None
- **Description**: Maximum AC output of your inverter system
- **Recommendation**: Set if your inverter is smaller than total DC capacity

#### Calibration (`manual_calibration_enabled`)
- **Type**: Boolean
- **Default**: False
- **Description**: Enable automatic per-plane calibration (future feature)
- **Recommendation**: Leave disabled for now

## Weather Data Tiers

The engine automatically detects available weather data and uses the best path:

### Tier 1: Irradiance Data (Excellent)
**Best case**: Weather provider includes irradiance measurements
- **Direct + Diffuse**: `direct_normal_irradiance` (DNI) + `diffuse_horizontal_irradiance` (DHI)
- **Global**: `global_horizontal_irradiance` (GHI) or `shortwave_radiation`
- **Accuracy**: Highest, typically within 10-15% on clear days

### Tier 2: Cloud Cover (Good)
**Fallback**: Weather provider has `cloud_cover` percentage
- Uses Kasten-Czeplak model to estimate GHI from cloud cover
- Then decomposes to DNI/DHI using Erbs correlation
- **Accuracy**: Good, typically within 15-25%

### Tier 3: Clear Sky (Limited)
**Last resort**: No irradiance or cloud data available
- Uses Haurwitz clear-sky model
- **Accuracy**: Poor on cloudy days, overestimates significantly

### Checking Your Weather Capabilities

After enabling manual forecast with a weather entity, check the sensor:
```
sensor.weather_forecast_capabilities
```

This will show detected fields like:
- `Excellent: DNI, DHI, Temp, Wind`
- `Good: Cloud, Temp, Wind`
- `Limited: Temp, Wind`

## Supported Weather Integrations

### Excellent (Tier 1)
- **Met.no** (Norway): Provides GHI estimation in some regions
- **OpenWeatherMap** (with solar data): Provides radiation values
- **Custom weather stations**: If they expose irradiance sensors

### Good (Tier 2)
- **Met.no**: Provides detailed cloud cover
- **OpenWeatherMap**: Provides cloud cover percentage
- **DarkSky**: Provides cloud cover
- **Weatherflow Tempest**: Provides solar radiation sensor data

### Limited (Tier 3)
- Any weather integration without irradiance or cloud data

## Physics Models Used

### Abbreviations
- **GHI**: Global Horizontal Irradiance (W/m²)
- **DNI**: Direct Normal Irradiance (W/m²) - direct beam from the sun
- **DHI**: Diffuse Horizontal Irradiance (W/m²) - scattered sky radiation
- **POA**: Plane-of-Array - irradiance on tilted panel surface
- **STC**: Standard Test Conditions (1000 W/m², 25°C cell temp)
- **NOCT**: Nominal Operating Cell Temperature
- **HDKR**: Hay-Davies-Klucher-Reindl transposition model
- **SVF**: Sky View Factor - fraction of sky hemisphere visible

### Calculation Pipeline

1. **Solar Position** (Sun altitude and azimuth)
   - Simplified solar position algorithm
   - Accounts for equation of time and declination

2. **Clear-Sky Irradiance** (if needed)
   - **Haurwitz model**: Simple, robust clear-sky GHI
   - Formula: `GHI_cs = 1098 × cos(zenith) × exp(-0.059/cos(zenith))`

3. **Cloud Mapping** (if no direct irradiance)
   - **Kasten-Czeplak model**: Maps cloud cover to GHI fraction
   - Formula: `GHI = GHI_cs × (1 - 0.75 × C^3.4)`
   - Where C is cloud fraction (0-1)

4. **GHI Decomposition** (if only GHI available)
   - **Erbs correlation**: Splits GHI into beam and diffuse
   - Based on clearness index kt = GHI / (DNI_extra × cos(zenith))
   - Piecewise polynomial function for diffuse fraction

5. **Horizon Blocking**
   - Direct beam blocked when sun altitude < horizon altitude at that azimuth
   - Linear interpolation between 12 horizon points (every 30°)
   - Diffuse reduced by sky-view factor

6. **Transposition to POA**
   - **HDKR model**: Converts horizontal irradiance to tilted plane
   - Accounts for:
     - Direct beam component (AOI cosine effect)
     - Circumsolar diffuse (anisotropic)
     - Isotropic diffuse
     - Ground-reflected component (20% albedo)

7. **Cell Temperature**
   - Simplified PVsyst-like model
   - Based on NOCT (45°C at 800 W/m²)
   - Includes basic wind cooling effect

8. **DC Power**
   - **PVWatts model**: Industry-standard simple model
   - `Pdc = Pdc0 × (POA/1000) × [1 + γ × (Tcell - 25)]`
   - Where γ is temperature coefficient

9. **AC Power**
   - Nominal inverter efficiency (96%)
   - Optional clipping at inverter AC limit

10. **Calibration** (optional)
    - Per-plane scalar multipliers
    - Learned from historical forecast vs. actual data

## Example Configuration

```json
{
  "fs_use": true,
  "forecast_source": "manual_physics",
  "weather_entity": "weather.home",
  "fs_lat": 56.6967,
  "fs_lon": 13.0196,
  "fs_planes": "[{\"dec\":45,\"az\":\"W\",\"kwp\":9.43},{\"dec\":45,\"az\":\"E\",\"kwp\":4.92}]",
  "fs_horizon": "18,16,11,7,5,4,3,2,2,4,7,10",
  "manual_step_minutes": 15,
  "manual_diffuse_sky_view_factor": 0.95,
  "manual_temp_coeff_pct_per_c": -0.38,
  "manual_inverter_ac_kw_cap": 10.0,
  "manual_calibration_enabled": false
}
```

## Sensors

When using manual forecast, the following sensors are available:

### `sensor.solar_forecast_raw`
- **Type**: Energy (kWh)
- **Description**: Today's total forecasted energy
- **Attributes**: 
  - `forecast`: Array of (time, watts) pairs

### `sensor.solar_forecast_compensated`
- **Type**: Energy (kWh)
- **Description**: Same as raw for manual mode (physics already accounts for conditions)
- **Attributes**:
  - `forecast`: Array of (time, watts) pairs
  - `weather_entity`: Source weather entity

### `sensor.weather_forecast_capabilities`
- **Type**: String
- **Description**: Detected weather data capabilities
- **State Examples**:
  - `"Excellent: DNI, DHI, Temp, Wind"`
  - `"Good: Cloud, Temp, Wind"`
- **Attributes**:
  - `tier`: 1, 2, or 3
  - `has_dni`, `has_dhi`, `has_ghi`: Boolean flags
  - `has_cloud_cover`, `has_temperature`, `has_wind_speed`: Boolean flags

## Calibration (Future)

The calibration feature will allow the system to learn correction factors by comparing forecasts to actual production. This helps account for:
- Panel degradation
- Soiling and snow
- Actual vs. rated inverter efficiency
- Site-specific microclimate effects
- Shading not captured in horizon data

*Note: Calibration is currently disabled and will be implemented in a future update.*

## Troubleshooting

### Forecast is Always Zero
- Check weather entity has valid state
- Verify latitude/longitude are correct
- Ensure planes JSON is valid
- Check horizon CSV has 12 values

### Forecast Too High
- Verify temperature coefficient is negative
- Check inverter AC cap is set if applicable
- Confirm panel kWp ratings are correct
- Weather data may be overly optimistic

### Forecast Too Low
- Check for horizon blocking issues
- Verify diffuse sky-view factor (may need to increase)
- Weather data may be too conservative
- Temperature coefficient may be too aggressive

### "Limited" Weather Capabilities
- Your weather provider doesn't expose irradiance or cloud data
- Consider switching weather integrations
- Manual forecast will use clear-sky model (inaccurate on cloudy days)

## Comparison: Manual vs. Forecast.Solar

| Feature | Manual (Physics) | Forecast.Solar |
|---------|------------------|----------------|
| Cost | Free | Free (limited) / Paid |
| Setup Complexity | Medium | Easy |
| Data Requirements | Weather integration | Internet access |
| Accuracy (clear sky) | 90-95% | 90-95% |
| Accuracy (cloudy) | 70-85% (with good weather data) | 85-90% |
| Horizon Support | Built-in (12 points) | Yes (paid plans) |
| Real-time Adaptation | Yes (weather updates) | No (fixed forecast) |
| Offline Capability | No (needs weather) | No (needs API) |
| Customization | High | Low |
| Calibration | Yes (future) | No (user-level) |

## Best Practices

1. **Start with Forecast.Solar**: Get a baseline to compare against
2. **Verify Weather Data**: Check that your weather integration provides good data
3. **Compare Forecasts**: Run both engines in parallel for a week
4. **Calibrate Over Time**: Once calibration is available, let it learn for 2-4 weeks
5. **Monitor Accuracy**: Use the actual PV sensors to track forecast vs. reality
6. **Seasonal Adjustments**: Forecasts may need tuning between summer and winter

## References

- Haurwitz, B. (1945). "Insolation in Relation to Cloudiness and Cloud Density"
- Kasten, F. and Czeplak, G. (1980). "Solar and terrestrial radiation dependent on the amount and type of cloud"
- Erbs, D. G., et al. (1982). "Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation"
- Perez, R., et al. (1990). "Modeling daylight availability and irradiance components from direct and global irradiance"
- Hay, J. E. and Davies, J. A. (1980). "Calculation of the solar radiation incident on an inclined surface"
- King, D. L., et al. (2004). "PVWatts Version 3 User's Manual" (NREL)

## Future Enhancements

- **Full pvlib Integration**: Optional "Advanced" mode using pvlib for users who want maximum accuracy
- **Perez Transposition**: More accurate than HDKR for circumsolar effects
- **Linke Turbidity**: Better clear-sky modeling with atmospheric turbidity
- **Snow Detection**: Automatic snow coverage detection and modeling
- **Soiling Model**: Gradual efficiency loss between cleaning events
- **Multi-Inverter**: Better handling of systems with multiple inverters
- **Machine Learning**: Neural network calibration for complex shading patterns
