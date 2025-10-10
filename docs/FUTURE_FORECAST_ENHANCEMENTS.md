# Future Forecast Enhancements - Investigation and Implementation Plan

## Overview

This document outlines potential enhancements to the solar forecasting system by incorporating additional weather parameters and implementing comprehensive logging for forecast accuracy analysis and machine learning improvements.

## Goals

1. **Enhanced Forecast Accuracy**: Incorporate additional weather parameters beyond cloud coverage
2. **Data Collection for Learning**: Log all relevant parameters for historical analysis
3. **Forecast Validation**: Enable comparison between predictions and actual production
4. **Parameter Discovery**: Identify and document available weather data from various services

## Current State

### Currently Logged/Used Parameters
- **Cloud Coverage** (0-100%): Primary factor for cloud compensation
- **Temperature** (°C): Used in manual physics forecast for cell temperature calculations
- **Wind Speed** (m/s): Used for cooling effect on panel temperature
- **GHI/DNI/DHI** (W/m²): Solar irradiance components (when available)

### Current Limitations
- Historical data points (before "now") don't get cloud compensation from hourly forecast
- Limited weather parameters used in compensation calculations
- No systematic logging for forecast vs actual comparison
- No structured data collection for ML/optimization

## Proposed Logging System

### Parameters to Log

#### Solar Forecast Data
1. **Raw Forecast** (W)
   - Uncompensated forecast from Forecast.Solar or manual physics
   - Timestamp and power value
   
2. **Compensated Forecast** (W)
   - Cloud-compensated forecast
   - Applied compensation factor
   
3. **Actual Production** (W)
   - Real-time solar production from sensors
   - Timestamp-aligned with forecasts

#### Weather Parameters (Current and Forecast)

**Tier 1: Currently Available**
- **Cloud Coverage** (%)
  - Current state
  - Hourly forecast values
  - Source: Met.no, OpenWeatherMap, DarkSky, AccuWeather
  
- **Temperature** (°C)
  - Ambient temperature
  - Affects panel efficiency
  - Source: All major weather services
  
- **Wind Speed** (m/s)
  - Panel cooling effect
  - Source: All major weather services

**Tier 2: Commonly Available**
- **UV Index** (0-11+)
  - Direct measure of UV radiation
  - Strong correlation with solar production
  - Source: Met.no, OpenWeatherMap, AccuWeather, WeatherBit
  
- **Visibility/Sight Distance** (km)
  - Atmospheric clarity indicator
  - Affects irradiance transmission
  - Source: Met.no, OpenWeatherMap, NOAA
  
- **Humidity** (%)
  - Affects atmospheric transmission
  - Can indicate haze/moisture
  - Source: All major weather services
  
- **Atmospheric Pressure** (hPa/mbar)
  - Air density affects light scattering
  - Source: All major weather services
  
- **Precipitation** (mm/h)
  - Rain reduces production dramatically
  - Source: All major weather services
  
- **Precipitation Probability** (%)
  - Risk assessment for production drops
  - Source: Most weather services

**Tier 3: Specialized Parameters**
- **Aerosol Optical Depth (AOD)**
  - Atmospheric particulate measurement
  - Directly affects irradiance
  - Source: NASA AERONET, Copernicus, specialized APIs
  
- **Linke Turbidity**
  - Atmospheric turbidity coefficient
  - Standard parameter in solar calculations
  - Source: SoDa, PVGIS, specialized solar APIs
  
- **Total Column Ozone** (DU)
  - Affects UV/visible light transmission
  - Source: NASA, NOAA, Copernicus
  
- **Solar Radiation Forecast** (W/m²)
  - Direct GHI/DNI/DHI forecasts
  - Source: SolarAnywhere, Solcast, Meteotest
  
- **Cloud Type Classification**
  - Low/medium/high clouds affect differently
  - Source: Advanced weather services (NOAA, ECMWF)
  
- **Snow Cover** (binary or depth)
  - Ground albedo effect + panel coverage
  - Source: Weather services, satellite data

## Weather Service Capabilities

### Free/Open Services

#### Met.no (Norway)
**Available Now:**
- Cloud coverage (%)
- Temperature, wind speed
- Humidity, pressure
- Precipitation, precipitation probability
- UV index (in some regions)

**Forecast Type:** Hourly up to 48-72 hours

**API:** Free, no key required
**Documentation:** https://api.met.no/

#### OpenWeatherMap
**Available:**
- Cloud coverage (%)
- Temperature, wind speed
- Humidity, pressure
- Precipitation, precipitation probability
- UV index
- Visibility
- Optional: Solar radiation data (paid tier)

**Forecast Type:** Hourly up to 48 hours

**API:** Free tier available (60 calls/min)
**Documentation:** https://openweathermap.org/api

#### WeatherBit
**Available:**
- Cloud coverage (%)
- Temperature, wind speed
- Humidity, pressure
- UV index
- Visibility
- Solar radiation (GHI, DNI - paid tier)

**Forecast Type:** Hourly up to 48 hours

**API:** Free tier available
**Documentation:** https://www.weatherbit.io/api

### Paid/Premium Services

#### Solcast
**Specialization:** Solar-specific forecasts
**Available:**
- GHI, DNI, DHI forecasts
- Cloud opacity
- Aerosol optical depth
- Precipitable water
- Solar production forecasts

**Forecast Type:** 30-minute resolution, 7 days
**Cost:** Paid service, hobbyist tier available
**Documentation:** https://solcast.com/

#### SolarAnywhere
**Specialization:** Professional solar forecasting
**Available:**
- Complete irradiance components
- Aerosol data
- Site-specific forecasts

**Cost:** Professional/enterprise pricing

#### Visual Crossing Weather
**Available:**
- Comprehensive weather data
- UV index
- Solar radiation
- Visibility
- Cloud cover

**Forecast Type:** Hourly up to 15 days
**Cost:** Free tier available
**Documentation:** https://www.visualcrossing.com/

### Satellite Data Sources

#### NASA POWER (Prediction Of Worldwide Energy Resources)
**Available:**
- Historical solar radiation data
- Climatological averages
- Free access

**Documentation:** https://power.larc.nasa.gov/

#### Copernicus Atmosphere Monitoring Service (CAMS)
**Available:**
- Aerosol optical depth
- Total column ozone
- Atmospheric composition
- Solar radiation forecasts

**Cost:** Free for research/non-commercial
**Documentation:** https://atmosphere.copernicus.eu/

## Proposed Implementation

### Phase 1: Enhanced Logging System

#### 1.1 Data Structure

```python
@dataclass
class ForecastLogEntry:
    """Comprehensive forecast log entry for analysis."""
    timestamp: datetime
    
    # Forecast data
    raw_forecast_watts: float
    compensated_forecast_watts: float
    compensation_factor: float
    
    # Actual production (if available)
    actual_production_watts: Optional[float]
    
    # Weather parameters used
    cloud_coverage_pct: Optional[float]
    temperature_c: Optional[float]
    wind_speed_ms: Optional[float]
    uv_index: Optional[float]
    visibility_km: Optional[float]
    humidity_pct: Optional[float]
    pressure_hpa: Optional[float]
    precipitation_mm: Optional[float]
    
    # Advanced parameters (when available)
    ghi_wm2: Optional[float]
    dni_wm2: Optional[float]
    dhi_wm2: Optional[float]
    aod: Optional[float]
    
    # Metadata
    forecast_source: str  # "forecast_solar" or "manual_physics"
    weather_source: str  # "met.no", "openweathermap", etc.
    data_tier: int  # 1, 2, or 3 based on available data
```

#### 1.2 Storage Implementation

```python
class ForecastLogger:
    """Logger for forecast data and weather parameters."""
    
    def __init__(self, hass, storage_path: str, retention_days: int = 30):
        self.hass = hass
        self.storage_path = storage_path
        self.retention_days = retention_days
        
    async def log_forecast_point(self, entry: ForecastLogEntry):
        """Log a single forecast point with all available parameters."""
        # Store to persistent storage
        # Format: CSV or JSON for easy analysis
        pass
        
    async def get_historical_data(
        self, 
        start: datetime, 
        end: datetime
    ) -> List[ForecastLogEntry]:
        """Retrieve historical logged data for analysis."""
        pass
        
    async def cleanup_old_data(self):
        """Remove data older than retention_days."""
        pass
```

#### 1.3 Integration Points

**Location 1: forecast_provider.py - async_fetch_watts()**
```python
# After computing raw and compensated forecasts
for point in raw:
    log_entry = ForecastLogEntry(
        timestamp=point.time,
        raw_forecast_watts=point.watts,
        compensated_forecast_watts=compensated_point.watts,
        compensation_factor=factor,
        # ... extract weather parameters
    )
    await forecast_logger.log_forecast_point(log_entry)
```

**Location 2: Actual production sensor**
```python
# When actual production is recorded
await forecast_logger.update_actual_production(
    timestamp=now,
    actual_watts=sensor_value
)
```

### Phase 2: Weather Parameter Expansion

#### 2.1 Enhanced Weather Data Fetching

```python
class EnhancedWeatherProvider:
    """Fetch extended weather parameters from multiple sources."""
    
    async def get_extended_forecast(
        self, 
        entity_id: str
    ) -> Dict[datetime, ExtendedWeatherData]:
        """Get all available weather parameters."""
        
        # Base parameters from HA weather entity
        base_data = await self._get_ha_weather_forecast(entity_id)
        
        # Optionally supplement with additional sources
        if self.use_additional_sources:
            uv_data = await self._get_uv_index()
            visibility_data = await self._get_visibility()
            # etc.
            
        return merged_data
```

#### 2.2 UV Index Integration

Most weather services provide UV index in their hourly forecasts. Add to weather data extraction:

```python
# In _get_weather_data() method
if "uv_index" in forecast_entry:
    data["uv_index"] = float(forecast_entry["uv_index"])
```

#### 2.3 Visibility/Sight Distance

Available in Met.no and OpenWeatherMap:

```python
if "visibility" in forecast_entry:
    # Usually in meters, convert to km
    data["visibility_km"] = float(forecast_entry["visibility"]) / 1000.0
```

### Phase 3: Analysis and Visualization Support

#### 3.1 Export Functionality

```python
class ForecastAnalyzer:
    """Tools for analyzing forecast accuracy."""
    
    async def export_comparison_data(
        self,
        start_date: date,
        end_date: date,
        format: str = "csv"
    ) -> str:
        """
        Export data for external analysis.
        
        Columns:
        - timestamp
        - raw_forecast_watts
        - compensated_forecast_watts
        - actual_production_watts
        - forecast_error_watts
        - forecast_error_pct
        - cloud_coverage_pct
        - temperature_c
        - uv_index
        - visibility_km
        - ... (all logged parameters)
        """
        pass
        
    async def calculate_accuracy_metrics(
        self,
        date: date
    ) -> Dict[str, float]:
        """
        Calculate forecast accuracy metrics.
        
        Returns:
        - mae: Mean Absolute Error
        - rmse: Root Mean Square Error
        - mape: Mean Absolute Percentage Error
        - r2: R-squared score
        """
        pass
```

#### 3.2 Home Assistant Sensors

Create new sensors for visualization:

```python
# sensor.solar_forecast_accuracy
# State: R² score or MAPE for last 7 days
# Attributes: Detailed accuracy metrics

# sensor.solar_forecast_logger
# State: Number of logged entries
# Attributes: Storage size, oldest entry, newest entry

# sensor.weather_parameters_availability
# State: Number of available parameters
# Attributes: List of available parameters and sources
```

### Phase 4: Advanced Parameter Integration (Optional)

#### 4.1 Aerosol Optical Depth (AOD)

**Source:** Copernicus CAMS or NASA AERONET

```python
async def get_aod_forecast(lat: float, lon: float) -> float:
    """Get aerosol optical depth from CAMS."""
    # API call to Copernicus CAMS
    # Returns AOD at 550nm typically
    pass
```

**Impact:** AOD directly affects clear-sky irradiance. Can improve Tier 3 forecasts significantly.

#### 4.2 Linke Turbidity

**Source:** SoDa service, climatological databases

```python
def get_linke_turbidity(lat: float, lon: float, month: int) -> float:
    """Get typical Linke turbidity for location and time."""
    # Use climatological database
    # Or query SoDa service
    pass
```

**Impact:** Better clear-sky modeling in manual physics engine.

## Implementation Priority

### High Priority (Phase 1)
1. ✅ Basic forecast logging structure
2. ✅ Log raw forecast, compensated forecast, actual production
3. ✅ Log cloud coverage, temperature, wind speed
4. ✅ CSV/JSON export for analysis
5. ✅ Data retention management

### Medium Priority (Phase 2)
1. ⬜ UV index integration (easy - already in many services)
2. ⬜ Visibility/sight distance logging
3. ⬜ Humidity and pressure logging
4. ⬜ Precipitation data logging
5. ⬜ Enhanced weather parameter extraction

### Low Priority (Phase 3)
1. ⬜ Accuracy metric calculations
2. ⬜ Analysis sensors
3. ⬜ Visualization helpers
4. ⬜ Dashboard integration

### Future/Advanced (Phase 4)
1. ⬜ Aerosol optical depth integration
2. ⬜ Linke turbidity data
3. ⬜ Cloud type classification
4. ⬜ Machine learning optimization
5. ⬜ Integration with specialized solar APIs (Solcast, SolarAnywhere)

## Data Format Specification

### CSV Log Format

```csv
timestamp,raw_forecast_w,compensated_forecast_w,actual_production_w,compensation_factor,cloud_coverage_pct,temperature_c,wind_speed_ms,uv_index,visibility_km,humidity_pct,pressure_hpa,precipitation_mm,forecast_source,weather_source,data_tier
2025-10-10T14:00:00+02:00,1500.0,1200.0,1150.0,0.80,75,14.5,5.2,3.5,10.0,85,1013.2,0.0,forecast_solar,met.no,2
2025-10-10T15:00:00+02:00,1450.0,1305.0,1280.0,0.90,50,15.2,4.8,4.0,15.0,80,1013.5,0.0,forecast_solar,met.no,2
```

### JSON Log Format

```json
{
  "entries": [
    {
      "timestamp": "2025-10-10T14:00:00+02:00",
      "forecast": {
        "raw_watts": 1500.0,
        "compensated_watts": 1200.0,
        "compensation_factor": 0.80,
        "source": "forecast_solar"
      },
      "actual": {
        "production_watts": 1150.0
      },
      "weather": {
        "source": "met.no",
        "cloud_coverage_pct": 75,
        "temperature_c": 14.5,
        "wind_speed_ms": 5.2,
        "uv_index": 3.5,
        "visibility_km": 10.0,
        "humidity_pct": 85,
        "pressure_hpa": 1013.2,
        "precipitation_mm": 0.0
      },
      "metadata": {
        "data_tier": 2
      }
    }
  ]
}
```

## Testing Strategy

### Unit Tests
- Test logger creation and storage
- Test data retrieval and filtering
- Test export functionality
- Test cleanup/retention

### Integration Tests
- Test logging during forecast computation
- Test actual production updates
- Test multi-source weather data aggregation

### Performance Tests
- Storage size with 30 days of 15-minute data
- Query performance for large date ranges
- Impact on forecast computation time

## Configuration Options

```yaml
# configuration.yaml additions
energy_dispatcher:
  forecast_logging:
    enabled: true
    retention_days: 30
    storage_path: "forecast_logs/"
    log_interval_minutes: 15  # Align with forecast steps
    parameters:
      - cloud_coverage
      - temperature
      - wind_speed
      - uv_index
      - visibility
      - humidity
      - pressure
      - precipitation
```

## Benefits

1. **Forecast Improvement**: Identify which weather parameters most affect accuracy
2. **System Optimization**: Tune compensation factors based on historical data
3. **Debugging**: Understand why forecasts were inaccurate
4. **Machine Learning**: Collect training data for ML-based optimization
5. **User Insights**: Show users how weather affects their solar production
6. **Service Comparison**: Compare accuracy of different weather services

## Next Steps

1. Create GitHub issue for Phase 1 implementation
2. Design database schema for forecast logs
3. Implement basic logging infrastructure
4. Add UV index and visibility extraction (low-hanging fruit)
5. Create export/analysis utilities
6. Document findings for ML optimization (future PR)

## References

- [Met.no API Documentation](https://api.met.no/)
- [OpenWeatherMap API](https://openweathermap.org/api)
- [Copernicus CAMS](https://atmosphere.copernicus.eu/)
- [NASA POWER](https://power.larc.nasa.gov/)
- [Solcast API](https://solcast.com/)
- [pvlib-python](https://pvlib-python.readthedocs.io/) - Reference for solar calculations
- [SoDa Service](http://www.soda-pro.com/) - Solar radiation data

## Conclusion

This enhancement plan provides a roadmap for:
1. Comprehensive data logging for analysis
2. Integration of additional weather parameters
3. Tools for forecast accuracy evaluation
4. Foundation for future ML-based optimization

The phased approach ensures incremental value delivery while maintaining system stability and backward compatibility.
