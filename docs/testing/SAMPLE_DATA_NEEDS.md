# Additional Sample Data Sets Needed

This document provides a prioritized list of sample data sets needed to improve test coverage beyond what's currently available.

## Current Sample Data Coverage

✓ Battery SOC, power (7 days, multiple gaps)
✓ Grid import/export meters (7 days, various quality)
✓ PV generation (7 days, daytime only)
✓ House consumption (7 days, excellent quality - no gaps)
✓ Energy prices - spot and full (7 days, hourly)
✓ Nordpool price structure (YAML format)

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

**What we need**:
- Cloud cover percentage (0-100%)
- Ambient temperature (°C)
- Solar irradiance (W/m²) if available
- Hourly or better resolution
- Covering the same time period as existing sample data

**Purpose**:
- Validate solar forecast accuracy against actual weather
- Test cloud compensation algorithm effectiveness
- Correlate PV production with weather conditions

**How to obtain**:
- Historical weather API (e.g., OpenWeatherMap, Visual Crossing)
- Local weather station data
- Coordinate location: Should match PV system location

**Impact**: Enables `test_forecast_provider_validation.py` test suite (2 tests)

---

### 2. EV/EVSE Sensor Data (24-48 hours)

**What we need**:
- EV battery SOC (%)
- EVSE charging power (kW)
- EVSE status (charging/idle/error)
- EVSE current setting (A)
- EVSE cumulative energy delivered (kWh)
- EVSE start/stop commands (if available)
- 30-second to 1-minute intervals

**Purpose**:
- Test EV dispatcher charging optimization
- Validate EVSE adapter implementations (Huawei, Generic, Manual)
- Test EV charging cost optimization
- Validate ready-by-time calculations

**How to obtain**:
- Export from actual EV/EVSE installation
- Any EV charger with Home Assistant integration
- Prefer continuous 24h period with at least one full charge cycle

**Impact**: Enables testing of EV dispatcher and adapter modules (currently untested)

---

### 3. Grid Feed-in Tariff Data (Oct 4-11, 2025)

**What we need**:
- Export compensation rate (SEK/kWh)
- Time-of-use export rates if applicable
- Any special export incentives
- Hourly or constant rate

**Purpose**:
- Test export optimization logic
- Validate export decision making
- Calculate potential export revenue

**How to obtain**:
- User's electricity contract details
- Energy supplier's rate sheet
- For Oct 4-11, 2025 period specifically

**Impact**: Enables export optimization testing

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

- Period with prices >5 SEK/kWh
- Battery response during spike
- Consumption pattern changes
- **Purpose**: Extreme scenario handling
- **Duration**: At least 24 hours including spike

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
| ⭐⭐⭐ | Weather (Oct 4-11) | 7 days | Solar forecast validation | ❌ Missing |
| ⭐⭐⭐ | EV/EVSE sensors | 24-48h | EV dispatcher testing | ❌ Missing |
| ⭐⭐⭐ | Feed-in tariff | 7 days | Export optimization | ❌ Missing |
| ⭐⭐ | Winter data | 7 days | Seasonal variation | ❌ Missing |
| ⭐⭐ | Summer data | 7 days | Export scenarios | ❌ Missing |
| ⭐⭐ | Price spike | 24h+ | Extreme scenario | ❌ Missing |
| ⭐⭐ | Grid outage | Varies | Resilience testing | ❌ Missing |
| ⭐⭐ | Maintenance event | 24h+ | Manual overrides | ❌ Missing |
| ⭐⭐ | Cloudy period | 3-5 days | Low solar strategy | ❌ Missing |
| ⭐ | Multiple batteries | 7 days | Multi-battery support | ❌ Missing |
| ⭐ | Various inverters | 7 days | Adapter validation | ❌ Missing |
| ⭐ | Grid services | Varies | Future functionality | ❌ Missing |

Legend: ⭐⭐⭐ = Critical, ⭐⭐ = Nice to have, ⭐ = Optional

---

## Testing Impact

With current sample data (including its realistic gaps), we can implement **Phase 1 & 2** testing (19 new tests).

With the 3 critical missing data sets, we can implement **Phase 3** testing (5+ additional tests) and enable full validation of:
- Solar forecast accuracy
- EV charging optimization
- Export optimization

**Note**: The existing gappy data is already ideal for testing gap handling, interpolation, and cumulative counter calculations. No "perfect" data needed - gaps are a feature, not a bug.

Total potential: **300+ tests** (up from current 236)
