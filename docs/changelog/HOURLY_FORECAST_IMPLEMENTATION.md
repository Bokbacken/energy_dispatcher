# Hourly Weather Forecast Implementation

## Problem Statement

The issue requested checking if we are requesting **hourly data** from the weather service when doing additional cloud compensation of the solar forecast. Previously, the system was using only the current weather state, which meant the same cloud coverage value was applied to all future time points in the forecast.

## Solution Implemented

### Overview
The implementation now requests **hourly forecast data** from Home Assistant weather services (e.g., Met.no, OpenWeatherMap) using the `weather.get_forecasts` service with `type: hourly`. This provides time-specific weather conditions for each forecast hour.

### Changes Made

#### 1. `forecast_provider.py` - Cloud Compensation for Forecast.Solar

**New Method: `_get_hourly_weather_forecast()`**
- Calls `weather.get_forecasts` service with parameters:
  - `entity_id`: The configured weather entity
  - `type`: "hourly"
- Returns a dictionary mapping datetime to weather data
- Handles ISO 8601 datetime parsing
- Includes comprehensive error handling

**Enhanced Method: `_apply_cloud_compensation()`**
- Requests hourly forecast data at the start
- If hourly data is available:
  - Finds the closest forecast time for each solar forecast point (within 2 hours)
  - Extracts cloud coverage from the hourly forecast entry
  - Applies time-specific compensation factor
  - Results in varying compensation throughout the day
- Falls back to current state if hourly forecast is unavailable:
  - Reads cloudiness from weather entity's current state
  - Applies uniform compensation to all points
  - Maintains backward compatibility

#### 2. `manual_forecast_engine.py` - Physics-Based Forecast

**New Method: `_get_hourly_weather_forecast()`**
- Same implementation as ForecastSolarProvider
- Retrieves hourly weather forecast from weather service

**Enhanced Method: `_get_weather_data(dt, hourly_forecast)`**
- Now accepts optional `hourly_forecast` parameter
- If hourly forecast is provided:
  - Finds the closest forecast time to the requested datetime
  - Extracts all weather attributes (cloud_cover, temperature, wind_speed, irradiance)
  - Returns time-specific weather data
- Falls back to current state if:
  - No hourly forecast provided
  - No matching forecast time found
  - Hourly forecast doesn't contain needed attributes

**Enhanced Method: `async_compute_forecast()`**
- Fetches hourly forecast once at the beginning
- Passes hourly forecast to all `_get_weather_data()` calls
- Logs whether hourly forecast is being used
- More efficient: single service call for entire forecast period

### Service Call Format

Both modules call the weather service with the exact format requested:

```python
response = await self.hass.services.async_call(
    "weather",
    "get_forecasts",
    {
        "entity_id": self.weather_entity,
        "type": "hourly",
    },
    blocking=True,
    return_response=True,
)
```

This matches the format shown in the problem statement for Met.no:
```yaml
action: weather.get_forecasts
data:
  type: hourly
target:
  device_id: 745003e09fd6b9b6c2a3046f65b04484
```

### Expected Response Format

The service returns data in this format (example from Met.no):

```yaml
weather.met_no:
  forecast:
    - condition: cloudy
      precipitation_probability: 0
      datetime: "2025-10-10T14:00:00+00:00"
      wind_bearing: 286.8
      cloud_coverage: 100
      uv_index: 0.6
      temperature: 14.5
      wind_gust_speed: 46.1
      wind_speed: 20.2
      precipitation: 0
      humidity: 88
    - condition: cloudy
      datetime: "2025-10-10T15:00:00+00:00"
      cloud_coverage: 100
      temperature: 14.2
      ...
```

## Benefits

1. **More Accurate Cloud Compensation**: Uses time-varying cloud coverage instead of assuming current conditions persist
2. **Better Manual Forecasts**: Physics calculations use hour-by-hour temperature, wind speed, and cloud cover
3. **Improved Solar Predictions**: Accounts for forecasted weather changes throughout the day
4. **Backward Compatible**: Automatically falls back to current state if hourly forecast is unavailable
5. **Efficient**: Single service call per forecast computation
6. **Flexible**: Works with any weather integration that supports hourly forecasts

## Testing

### Verification Performed
1. **Syntax Validation**: All files compile successfully
2. **Method Presence**: Verified both modules have `_get_hourly_weather_forecast()` method
3. **Service Call Format**: Confirmed correct service call with `type: hourly`
4. **Parameter Passing**: Verified `hourly_forecast` parameter is properly propagated

### Test Coverage
Created comprehensive unit tests in `tests/test_hourly_forecast_integration.py`:
- Test successful hourly forecast retrieval
- Test handling of missing weather entity
- Test cloud compensation with hourly data
- Test fallback to current state
- Test weather data extraction from hourly forecast
- Test with mock Met.no-style forecast data

## Documentation Updates

1. **`docs/manual_forecast.md`**:
   - Added note about hourly forecast usage
   - Explained automatic fallback to current state

2. **`docs/solar_forecast_improvement.md`**:
   - Updated "How It Works" section
   - Clarified hourly forecast data request
   - Mentioned supported weather services

## Compatibility

### Supported Weather Integrations
Any Home Assistant weather integration that supports the `weather.get_forecasts` service with `type: hourly`:
- Met.no ✓
- OpenWeatherMap ✓
- DarkSky ✓
- WeatherFlow Tempest ✓
- AccuWeather ✓
- And others that implement the standard weather service

### Backward Compatibility
- If weather service doesn't support hourly forecasts: Uses current state (existing behavior)
- If weather entity is not configured: Returns raw forecast (existing behavior)
- Existing configurations continue to work without changes

## Performance Considerations

- Hourly forecast is requested once per forecast computation
- No repeated service calls for each forecast point
- Efficient datetime matching with 2-hour window
- Debug logging available for troubleshooting

## Future Enhancements

Potential improvements for consideration:
1. Cache hourly forecast data with TTL to avoid repeated service calls
2. Support for sub-hourly interpolation (e.g., 15-minute forecasts)
3. Support for daily or twice-daily forecast types
4. Additional weather attributes (precipitation probability, humidity, pressure)
5. Configurable forecast time window for matching
