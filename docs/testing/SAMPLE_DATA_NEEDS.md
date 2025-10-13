# Additional Sample Data Sets Needed

This document provides a prioritized list of sample data sets needed to improve test coverage beyond what's currently available.

## Current Sample Data Coverage

✓ Battery SOC, power (7 days, multiple gaps)
✓ Grid import/export meters (7 days, various quality)
✓ PV generation (7 days, daytime only)
✓ House consumption (7 days, excellent quality - no gaps)
✓ Energy prices - spot and full (7 days, hourly)
✓ Nordpool price structure (YAML format, 2 files)
✓ Nordpool with price spike (tomorrow section reaches 5.72 SEK/kWh)
✓ EV charging power, session energy, total energy (multiple gaps, realistic)
✓ Weather forecast (Met.no format, forecast only - historical not available)

## Philosophy: Testing with Gaps is Intentional

**Important**: The existing sample data includes gaps by design. These gaps represent real-world scenarios:
- Home Assistant crashes and restarts
- System updates (may take 30+ minutes)
- Network connectivity issues
- Sensor failures or temporary unavailability

**Why this matters**: The integration uses cumulative energy counters specifically because they continue counting even when not being read. When values return, the delta still accurately reflects energy flow during the gap. Testing with gaps ensures the integration handles these real-world scenarios correctly.

**Testing approach**: Use the existing gappy data to validate interpolation, gap detection, and counter-based calculations. This is more valuable than artificial "perfect" data.

---

## Critical Missing Data (High Priority)

### 1. Historical Weather Data (Oct 4-11, 2025)

**Status**: ⚠️ **Partially Available** - Forecast only

**What we have**:
- ✅ Weather forecast (Met.no format) with cloud coverage, temperature, precipitation
- ✅ Hourly forecast data covering Oct 13-14, 2025

**What we still need**:
- ❌ Historical weather data (actual measurements)
- ❌ Solar irradiance measurements (W/m²)

**Why historical is missing**:
Home Assistant does not log historical weather data by default - only forecasts are available. Historical weather would require custom logging/recording setup, which was not in place during the sample data period.

**Purpose**:
- Validate solar forecast accuracy against actual weather
- Test cloud compensation algorithm effectiveness
- Correlate PV production with weather conditions

**Workaround**:
Use weather forecast data alongside actual PV production to validate forecast algorithms work with real-world forecast inputs.

**Impact**: Enables partial `test_forecast_provider_validation.py` test suite (can test forecast processing, but not accuracy validation against actual weather)

---

### 2. EV/EVSE Sensor Data (24-48 hours)

**Status**: ✅ **Available**

**What we have**:
- ✅ EV charging power (kW) - `historic_EV_charging_power.csv`
- ✅ EV session charged energy (kWh) - `historic_EV_session_charged_energy.csv`
- ✅ EV total charged energy (kWh) - `historic_EV_total_charged_energy.csv`
- ✅ Multiple charging sessions with realistic gaps
- ✅ Various power levels reflecting real-world charging patterns

**Purpose**:
- Test EV dispatcher charging optimization
- Validate EVSE adapter implementations (Huawei, Generic, Manual)
- Test EV charging cost optimization
- Validate ready-by-time calculations

**Note**: 
Data includes realistic gaps representing charging sessions starting/stopping. SOC data and current settings are not available but power and energy metrics cover the most critical test scenarios.

**Impact**: ✅ Enables testing of EV dispatcher and adapter modules

---

### 3. Grid Feed-in Tariff Data (Oct 4-11, 2025)

**Status**: ✅ **Documented** - Based on actual electricity contract (E.ON Sweden)

**Feed-in compensation structure** (all values in SEK/kWh):

1. **Grid utility compensation**: 0.067 SEK/kWh
   - Paid by grid operator (E.ON Energidistribution) for exported energy
   - Compensates for grid usage/stability benefits

2. **Energy purchase price**: Spot price + 0.02 SEK/kWh
   - Paid by energy supplier (E.ON Energilösningar)
   - Follows Nordpool spot price with 2 öre/kWh markup
   - Example from bill: 0.4819 SEK/kWh total (includes spot + 0.02 markup)

3. **Tax return** (temporary incentive): 0.60 SEK/kWh
   - Available through end of 2025
   - **Expires January 1, 2026** ⚠️
   - Significant impact on export economics

**Total feed-in compensation** (2025):
```
Total = Grid utility + Spot price + 0.02 + Tax return
      = 0.067 + Spot + 0.02 + 0.60
      = Spot + 0.687 SEK/kWh
```

**Total feed-in compensation** (2026 and beyond):
```
Total = Grid utility + Spot price + 0.02
      = 0.067 + Spot + 0.02
      = Spot + 0.087 SEK/kWh
```

**Contract details**:
- Supplier: E.ON (Sweden)
- Grid operator: E.ON Energidistribution
- Region: SE4 (Nordpool price area)
- No time-of-use variation (constant rates)
- No VAT on exported energy (0%)

**Purpose**:
- Test export optimization logic
- Validate export decision making
- Calculate potential export revenue
- Model impact of tax return expiration

**Implementation note**:
For testing, use spot price + 0.687 SEK/kWh for 2025 scenarios and spot price + 0.087 SEK/kWh for 2026+ scenarios. This represents the net feed-in compensation.

**Impact**: ✅ Enables comprehensive export optimization testing with real tariff structure

---

## Nice to Have (Medium Priority)

### 5. Winter Data Set (December-February)

- Low solar production (short days, low sun angle)
- High heating consumption
- Typically higher electricity prices
- Battery behavior in cold weather
- **Purpose**: Seasonal variation testing
- **Duration**: At least 7 days

### 6. Summer Data Set (June-July)

- High solar production (long days, high sun angle)
- Lower consumption (no heating)
- Potential export scenarios (excess solar)
- Battery behavior in warm weather
- **Purpose**: Summer behavior, export optimization
- **Duration**: At least 7 days

### 7. Price Spike Event

**Status**: ✅ **Available**

**What we have**:
- ✅ `nordpool_spot_price_today_tomorrow-02.yaml` contains price spike in tomorrow section
- ✅ Peak price: 5.722 SEK/kWh (October 14, 18:45)
- ✅ Extended high-price period: Multiple hours >4 SEK/kWh
- ✅ Full today/tomorrow data for context

**Spike characteristics**:
- Duration: ~3 hours above 4 SEK/kWh
- Peak: 5.722 SEK/kWh (October 14, 18:45)
- Context: Evening peak demand period (17:45-20:15)

**Purpose**: 
- Extreme scenario handling
- Peak price detection and classification
- Battery discharge strategy during spikes
- Export optimization during high prices (if enabled)

**Impact**: ✅ Enables price spike scenario testing

### 8. Grid Outage Scenario

- Battery disconnect and reconnect events
- Sensor unavailability periods
- Recovery behavior
- **Purpose**: Resilience testing
- **Duration**: At least the outage period + 6 hours

### 9. Battery Maintenance Event

- Manual SOC reset
- Manual WACE reset
- Manual mode interventions
- **Purpose**: Test manual override handling
- **Duration**: At least 24 hours

### 10. Multi-Day Cloudy Period

- Several consecutive days with minimal solar (<20% expected)
- Battery reserve strategy in action
- Grid dependency during low solar
- **Purpose**: Test battery management in poor solar conditions
- **Duration**: 3-5 consecutive cloudy days

---

## Low Priority (Optional / Future)

### 11. Multiple Battery Systems
- Installation with 2+ batteries
- Independent SOC tracking
- Coordinated charging/discharging

### 12. Different Inverter Types
- Data from various inverter models
- Different efficiency curves
- Different power curves

### 13. Grid Frequency Events
- Frequency regulation activation
- Battery grid services participation
- Grid stabilization events

---

## Data Collection Recommendations

### Format Requirements

All sensor data should be provided as CSV files with:
- Column 1: Timestamp (ISO 8601 format with timezone)
- Column 2: Value (numeric)
- Header row with column names
- UTF-8 encoding

Example:
```csv
timestamp,value
2025-10-04T22:00:00+00:00,45.5
2025-10-04T22:00:30+00:00,45.7
```

### Quality Guidelines

- **Timestamps**: Must be in consistent timezone
- **Gaps**: Document any known gaps and reasons
- **Units**: Clearly state units for each sensor
- **Sampling rate**: Consistent intervals preferred
- **Coverage**: Longer periods are better (minimum 24h, ideal 7 days)

### Privacy Considerations

- Remove or anonymize any personally identifiable information
- Location coordinates can be rounded to nearest 0.1 degree
- Energy values are fine to share as-is
- Consider aggregating if concerned about consumption patterns revealing occupancy

### Submission

Sample data can be added to:
- `tests/fixtures/` directory in the repository
- Separate branch for review before merging
- Include a README describing the data source, period, and any known issues

---

## Quick Reference

| Priority | Data Type | Min Duration | Purpose | Status |
|----------|-----------|--------------|---------|---------|
| ⭐⭐⭐ | Weather (Oct 4-11) | 7 days | Solar forecast validation | ⚠️ Forecast only |
| ⭐⭐⭐ | EV/EVSE sensors | 24-48h | EV dispatcher testing | ✅ Available |
| ⭐⭐⭐ | Feed-in tariff | 7 days | Export optimization | ✅ Documented |
| ⭐⭐ | Winter data | 7 days | Seasonal variation | ❌ Missing |
| ⭐⭐ | Summer data | 7 days | Export scenarios | ❌ Missing |
| ⭐⭐ | Price spike | 24h+ | Extreme scenario | ✅ Available |
| ⭐⭐ | Grid outage | Varies | Resilience testing | ❌ Missing |
| ⭐⭐ | Maintenance event | 24h+ | Manual overrides | ❌ Missing |
| ⭐⭐ | Cloudy period | 3-5 days | Low solar strategy | ❌ Missing |
| ⭐ | Multiple batteries | 7 days | Multi-battery support | ❌ Missing |
| ⭐ | Various inverters | 7 days | Adapter validation | ❌ Missing |
| ⭐ | Grid services | Varies | Future functionality | ❌ Missing |

Legend: ⭐⭐⭐ = Critical, ⭐⭐ = Nice to have, ⭐ = Optional

---

## Testing Impact

### Currently Available (Updated October 2025)

With current sample data we can now implement:
- ✅ **Phase 1 & 2** testing with realistic gaps (19 new tests)
- ✅ **Phase 3** testing - EV charging optimization (5+ tests)
- ✅ **Phase 3** testing - Export optimization with real tariff structure
- ✅ **Phase 3** testing - Price spike scenarios
- ⚠️ **Partial** - Solar forecast processing (can test with forecast data, but not accuracy validation)

**What's now testable**:
- ✅ EV charging optimization with realistic power/energy data
- ✅ Export decision making using documented feed-in tariff (spot + 0.687 SEK/kWh for 2025)
- ✅ Price spike detection and battery discharge strategy (5.72 SEK/kWh spike available)
- ✅ Weather forecast integration and processing
- ⚠️ Solar forecast algorithm (forecast processing yes, accuracy validation no)

**What's still missing**:
- ❌ Historical weather measurements for solar forecast accuracy validation
- ❌ Seasonal variation data (winter/summer)
- ❌ Grid outage scenarios
- ❌ Battery maintenance events
- ❌ Extended cloudy periods

**Note**: The existing gappy data is already ideal for testing gap handling, interpolation, and cumulative counter calculations. No "perfect" data needed - gaps are a feature, not a bug.

**Total potential**: **280+ tests** (up from current 236), with 3 critical data types now available
