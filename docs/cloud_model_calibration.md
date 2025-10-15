# Cloud Model Calibration Guide

## Overview

The manual forecast engine uses a cloud transmission model to estimate how much solar irradiance reaches the ground based on cloud cover percentage from weather forecasts.

## Current Model (v0.10.5+)

**Formula**: `GHI = GHI_clear × (0.15 + 0.85 × (1 - C)^1.8)`

Where:
- `GHI_clear` = Clear-sky irradiance (from Haurwitz model)
- `C` = Cloud cover fraction (0-1)
- Power factor = 1.8
- Minimum transmission = 15%

### Transmission Values

| Cloud Cover | Transmission | Notes |
|-------------|--------------|-------|
| 0% | 100% | Clear sky |
| 25% | 66% | Partly cloudy |
| 50% | 39% | Half cloudy |
| 75% | 22% | Mostly cloudy |
| 85% | 18% | Heavy overcast |
| 100% | 15% | Complete overcast |

## Model History

### Version 0.10.4 and Earlier (Original Kasten-Czeplak)

**Formula**: `GHI = GHI_clear × (1 - 0.75 × C^3.4)`

**Problem**: This model was too optimistic, giving:
- 50% cloud → 93% transmission (unrealistic)
- 85% cloud → 57% transmission (too high for heavy overcast)
- Result: Forecasts were 4-6× higher than Forecast.Solar API

**Why it failed**: The Kasten-Czeplak formula is designed for satellite measurements of instantaneous irradiance, not weather forecasts which tend to overestimate cloud cover.

### Version 0.10.5+ (Current Balanced Model)

**Formula**: `GHI = GHI_clear × (0.15 + 0.85 × (1 - C)^1.8)`

**Improvements**:
- More realistic transmission across all cloud levels
- Guaranteed minimum 15% (accounts for diffuse skylight)
- Smooth monotonic decrease with cloud cover
- Better match to Forecast.Solar and actual PV production

**Validation**: For October test data (84-99% cloud):
- Old model: 8.57 kWh total
- New model: 1.95 kWh total
- Ratio: 4.4× reduction (aligns with user report of 4-6× too high)

## Comparing with Forecast.Solar

### Expected Accuracy

When properly calibrated, the manual forecast should be within:
- **±20% on average** compared to Forecast.Solar
- **±50% for individual hours** (weather forecasts have inherent uncertainty)

### Known Limitations

1. **Clear Sky Model**: Uses simplified Haurwitz model
   - May overestimate on hazy days
   - No atmospheric correction for elevation, aerosols, water vapor

2. **Weather Forecast Quality**: Depends on your weather provider
   - Some providers overestimate cloud cover
   - Hourly forecasts more accurate than current state extrapolation

3. **Panel Configuration**: Simplified transposition
   - Full POA calculation uses HDKR model
   - May differ from Forecast.Solar's proprietary model

### Calibration Process

If you find systematic differences between manual forecast and Forecast.Solar:

1. **Collect comparison data** over at least 1 week in varying weather
2. **Calculate average ratio**: `Manual / Forecast.Solar`
3. **Check if ratio is consistent** or varies by cloud level

**If manual is consistently higher** (e.g., 1.5-2.0×):
- Weather provider may underestimate cloud cover
- Clear-sky model may be too optimistic
- Consider adjusting minimum transmission down (e.g., 10% instead of 15%)

**If manual is consistently lower** (e.g., 0.5-0.7×):
- Weather provider may overestimate cloud cover
- Cloud model may be too pessimistic
- Consider adjusting power factor down (e.g., 1.5 instead of 1.8)

## Testing with Fixture Data

The test suite includes `test_forecast_solar_comparison.py` which compares manual calculations with Forecast.Solar data when available.

To add your own comparison data:
1. Export Forecast.Solar data to `tests/fixtures/forecast.solar.csv`
2. Run: `pytest tests/test_forecast_solar_comparison.py -v -s`
3. Review the ratio statistics and adjust if needed

### CSV Format

Expected columns:
- `datetime` or `timestamp`: ISO format (YYYY-MM-DD HH:MM:SS)
- `watts` or `power`: Instantaneous power in watts

Example:
```csv
datetime,watts
2025-10-14 06:00:00,25
2025-10-14 07:00:00,350
2025-10-14 08:00:00,425
```

## Advanced: Formula Tuning

If you need to tune the cloud model, the key parameters are in `manual_forecast_engine.py`:

```python
def cloud_to_ghi(ghi_clear: float, cloud_fraction: float) -> float:
    C = max(0.0, min(1.0, cloud_fraction))
    
    # TUNABLE PARAMETERS:
    min_transmission = 0.15  # Minimum at 100% cloud (0.10-0.20 typical)
    max_transmission = 0.85  # = 1.0 - min_transmission
    power_factor = 1.8       # Shape of curve (1.5-2.5 typical)
    
    ghi = ghi_clear * (min_transmission + max_transmission * ((1.0 - C) ** power_factor))
    return max(0.0, ghi)
```

**Parameter Effects**:
- **min_transmission**: Higher = more light at 100% cloud (typical: 0.10-0.20)
- **power_factor**: Lower = more light at all cloud levels (typical: 1.5-2.5)
  - 1.5 = more optimistic (higher transmission)
  - 2.0 = more pessimistic (lower transmission)
  - 1.8 = balanced (current default)

## References

- Kasten, F., & Czeplak, G. (1980). Solar and terrestrial radiation dependent on the amount and type of cloud.
- Erbs, D. G., et al. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation.
- Hay, J. E., & Davies, J. A. (1980). Calculation of the solar radiation incident on an inclined surface.
