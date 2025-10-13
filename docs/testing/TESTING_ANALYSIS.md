# Testing Analysis and Sample Data Requirements

## Executive Summary

This document analyzes the current test coverage, evaluates how existing sample data can be used to test integration functions, and identifies additional sample data sets needed for comprehensive testing.

## Testing Philosophy: Gaps Are Intentional

**Important**: The sample data contains gaps by design. These represent real-world scenarios:
- Home Assistant crashes and restarts
- System updates (may take 30+ minutes offline)
- Network connectivity issues
- Sensor failures or temporary unavailability

**Why this matters**: The integration uses cumulative energy counters specifically because they continue counting even when not being read. When sensor values return after a gap, the delta still accurately reflects energy flow during the outage. Testing with gaps ensures the integration handles these real-world scenarios correctly.

**Testing approach**: Use the existing gappy data to validate interpolation, gap detection, and counter-based calculations. This is more valuable than artificial "perfect" data without gaps.

## Current Test Coverage Analysis

### Well-Tested Modules (Unit Tests) ✓

1. **BEC (Battery Energy Cost)** - 49 tests
   - Initialization, SOC tracking, WACE calculations
   - Charge/discharge tracking
   - Historical data storage
   - Edge cases (overcharge, undercharge, reset)
   - **Gap**: No tests with real sample data

2. **Cost Strategy** - 28 tests
   - Price classification (cheap/medium/high)
   - Dynamic threshold calculation
   - High-cost window prediction
   - Battery reserve recommendations
   - EV charging optimization
   - **Uses synthetic price data only**

3. **Missing Data Handling** - 23 tests
   - Interpolation (linear, with gaps)
   - Data staleness detection
   - Counter reset handling
   - **Uses synthetic data only**

4. **Manual Forecast Physics** - 37 tests
   - Solar irradiance calculations
   - Temperature effects
   - Inverter efficiency
   - Array orientation
   - ⚠️ **Weather forecast data available** (Met.no format)

5. **Vehicle Manager** - 25 tests
   - Charge planning
   - Ready-by-time optimization
   - Power limit management
   - ✅ **Real EV sensor data now available**

6. **Physics Standalone** - 24 tests
   - GHI calculations
   - Cloud cover modeling
   - DHI/DNI decomposition
   - ⚠️ **Weather forecast available, but no actual measurements for validation**

7. **Config Flow** - 28 tests
   - Schema validation
   - Entity selectors
   - Options flow
   - **Adequate coverage**

8. **Baselines** - 13 tests
   - 48h baseline with time-of-day weighting
   - Daypart baseline calculation
   - **No tests with real consumption patterns**

9. **Battery Tracking** - 6 tests
   - Charge/discharge event tracking
   - **No tests with real battery sensor data**

### Modules Lacking Direct Tests ⚠️

1. **Price Provider** (`price_provider.py`)
   - Functions: `_enriched_spot()`, `get_hourly_prices()`
   - **Critical**: Handles fee calculations, tax, VAT
   - **No unit tests exist**
   - **Sample data available**: `nordpool_spot_price_today_tomorrow.yaml`, `historic_energy_*_price.csv`

2. **Forecast Provider** (`forecast_provider.py`)
   - Functions: Solar forecast fetching, caching, compensation
   - **Critical**: Main source of PV production forecasts
   - **Only 2 integration tests**
   - **Sample data available**: `historic_total_energy_from_pv.csv`

3. **Coordinator** (`coordinator.py`)
   - Functions: Data fetching, state management, update coordination
   - **Critical**: Central orchestrator for all data
   - **Tested indirectly through other tests**
   - **All sample data relevant**

4. **Helpers** (`helpers.py`)
   - Functions: Config parsing, JSON handling, defaults
   - **No dedicated tests**

5. **EV Dispatcher** (`ev_dispatcher.py`)
   - Functions: Charging strategy, power management
   - **No dedicated tests beyond vehicle manager**

6. **Adapters** (`adapters/`)
   - Huawei, Generic EVSE, Manual EV
   - **No dedicated tests**
   - ✅ **EV sensor data now available**: power, session energy, total energy


## Sample Data Quality Assessment

### Excellent Quality (Suitable for Validation) ✓

1. **historic_total_house_energy_consumption.csv**
   - 13,156 points over 167.91 hours
   - 30-second intervals
   - **No gaps** - perfect continuity
   - **Best for**: Baseline calculation validation, load pattern analysis

### Good Quality (Minor Gaps)

2. **historic_energy_spot_price.csv**
   - 163 points over 167 hours
   - Hourly intervals
   - 1 large gap (5 hours)
   - Suggested window: 2025-10-05 05:00 → 2025-10-11 21:00 (160h continuous)
   - **Good for**: Price classification, cost optimization tests

3. **historic_energy_full_price.csv**
   - 190 points over 167 hours
   - Hourly intervals
   - 2 large gaps
   - Best window: 2025-10-05 04:02 → 2025-10-09 08:00 (100h continuous)
   - **Good for**: Price enrichment validation

4. **historic_total_energy_supply_from_grid.csv**
   - 5,619 points over 167.91 hours
   - 30-second intervals
   - 5 large gaps
   - Best window: 2025-10-04 22:00 → 2025-10-07 02:12 (52h continuous)
   - **Good for**: Grid import tracking, cumulative meter handling

5. **historic_batteries_power_in_out.csv**
   - 16,194 points over 167.91 hours
   - 30-second intervals
   - 4 large gaps
   - Best window: 2025-10-04 22:00 → 2025-10-07 15:35 (65.6h continuous)
   - **Good for**: Battery power analysis, charge/discharge detection

### Fair Quality (Multiple Gaps)

6. **historic_batteries_SOC.csv**
   - 763 points over 167.91 hours
   - 5-minute intervals
   - 14 large gaps
   - Best window: 2025-10-04 22:00 → 2025-10-07 06:19 (56h continuous)
   - **Fair for**: SOC tracking validation (but expect interpolation)

7. **historic_total_energy_from_pv.csv**
   - 5,223 points over 163.22 hours
   - 30-second intervals
   - 14 large gaps (expected - night time)
   - Best window: 2025-10-10 05:37 → 2025-10-10 16:27 (10.8h continuous)
   - **Fair for**: PV generation validation (daytime only)

8. **historic_total_discharge_from_batteries.csv**
   - 2,552 points over 167.90 hours
   - 2-minute intervals
   - 19 large gaps
   - Best window: 2025-10-10 02:01 → 2025-10-10 22:18 (20.3h continuous)
   - **Fair for**: Battery discharge tracking

### Poor Quality (Many Gaps - Expected Behavior)

9. **historic_feed_in_to_grid_today.csv**
   - 863 points over 166.34 hours
   - 30-second intervals
   - 47 large gaps (expected - only updates during export)
   - Best window: 2025-10-10 06:11 → 2025-10-10 19:35 (13.4h continuous)
   - **Expected behavior**: Only records during grid export

10. **historic_total_feed_in_to_grid.csv**
    - 851 points over 166.34 hours
    - 30-second intervals
    - 44 large gaps
    - **Expected behavior**: Cumulative meter, only updates during export

11. **historic_total_charged_energy_to_batteries.csv**
    - 1,722 points over 166.34 hours
    - 2-minute intervals
    - 27 large gaps
    - **Expected behavior**: Only updates during charging

12. **historic_today_energy_supply_from_grid.csv**
    - 5,614 points over 167.91 hours
    - 30-second intervals
    - 5 large gaps
    - 6 non-monotonic segments ⚠️
    - **Note**: Non-monotonic indicates possible daily resets

13. **nordpool_spot_price_today_tomorrow-01.yaml** and **-02.yaml**
    - Structured price data with today/tomorrow split
    - -02 includes price spike (5.72 SEK/kWh peak on Oct 14, 18:45)
    - **Good for**: Price provider integration tests, spike scenario tests

14. **historic_EV_charging_power.csv**
    - 3,805 points over ~167 hours
    - Realistic gaps representing charging sessions
    - **Good for**: EV charging optimization, power tracking

15. **historic_EV_session_charged_energy.csv**
    - 5,654 points over ~167 hours
    - Session-based tracking with resets
    - **Good for**: Per-session energy accounting

16. **historic_EV_total_charged_energy.csv**
    - 4,798 points over ~167 hours
    - Cumulative energy counter
    - **Good for**: Long-term EV energy tracking

17. **forecast_weather_met.no-01.yaml**
    - Weather forecast data (Met.no format)
    - Hourly cloud coverage, temperature, precipitation
    - **Good for**: Solar forecast algorithm testing (processing, not accuracy validation)


## Recommended Priority 1 Tests (Can Be Implemented Now)

### Test Suite: `test_price_provider_with_data.py`
**Purpose**: Validate price enrichment calculations with real data
**Tests**: 3 tests covering enriched spot calculation, Nordpool parsing, gap handling
**Sample Data**: ✓ Available (`historic_energy_*_price.csv`, `nordpool_spot_price_today_tomorrow.yaml`)

### Test Suite: `test_coordinator_with_real_data.py`
**Purpose**: Integration tests with real sensor data
**Tests**: 5 tests covering cumulative meters, battery tracking, PV production, baselines, staleness detection
**Sample Data**: ✓ Available (all CSV files)

### Test Suite: `test_missing_data_real_scenarios.py`
**Purpose**: Validate interpolation with real gap patterns
**Tests**: 3 tests covering battery SOC gaps, price gaps, non-monotonic meters
**Sample Data**: ✓ Available

### Test Suite: `test_bec_real_battery_cycles.py`
**Purpose**: Validate BEC calculations with real charge/discharge cycles
**Tests**: 3 tests covering charge cycles, discharge cycles, full day cycles
**Sample Data**: ✓ Available

### Test Suite: `test_cost_strategy_real_prices.py`
**Purpose**: Test optimization algorithms with real price patterns
**Tests**: 3 tests covering dynamic thresholds, window detection, reserve calculations
**Sample Data**: ✓ Available

### Test Suite: `test_helpers_utilities.py`
**Purpose**: Test helper functions
**Tests**: 2 tests covering PV arrays JSON, config parsing
**Sample Data**: ✓ Can use synthetic data

**Total Priority 1**: 19 new tests using existing sample data


## Additional Sample Data Sets Needed

### Critical Gaps (High Priority)

1. **Historical Weather Data** (Oct 4-11, 2025) - ⚠️ **Partially Available**
   - ⚠️ Weather forecast available (Met.no format): `forecast_weather_met.no-01.yaml`
   - ❌ Historical actual measurements not available (HA doesn't log by default)
   - ❌ Solar irradiance (W/m²) not available
   - **Purpose**: Validate solar forecast accuracy (can test processing, not accuracy)
   - **Note**: Can use forecast data alongside actual PV production for validation

2. **EV/EVSE Sensor Data** (any 24-48h period) - ✅ **Available**
   - ✅ EV charging power (kW): `historic_EV_charging_power.csv`
   - ✅ EV session energy (kWh): `historic_EV_session_charged_energy.csv`
   - ✅ EV total energy (kWh): `historic_EV_total_charged_energy.csv`
   - ❌ EV SOC (%) not available
   - ❌ EVSE status/current not available
   - **Purpose**: Test EV dispatcher and EVSE adapters
   - **Impact**: Can now test charging optimization, energy tracking

3. **Grid Feed-in Tariff Data** (Oct 4-11, 2025) - ✅ **Documented**
   - ✅ Export compensation structure documented (E.ON Sweden, SE4 region)
   - ✅ 2025: Spot + 0.687 SEK/kWh (includes 0.60 SEK/kWh tax return)
   - ✅ 2026+: Spot + 0.087 SEK/kWh (tax return expires)
   - **Purpose**: Test export optimization
   - **Impact**: Can now implement export decision logic tests

### Nice to Have (Medium Priority)

4. **Winter Data Set** (Dec-Feb): Low solar, high consumption, different prices
5. **Summer Data Set** (Jun-Jul): High solar, low consumption, export scenarios
6. **Price Spike Event**: >5 SEK/kWh periods - ✅ **Available** (`nordpool_spot_price_today_tomorrow-02.yaml`, peak 5.72 SEK/kWh)
7. **Grid Outage Scenario**: Battery disconnect/reconnect events
8. **Battery Maintenance Event**: SOC reset, manual interventions
9. **Multi-Day Cloud Cover**: <20% expected solar for several days

### Low Priority (Optional)

10. **Multiple Battery Systems**: Data from installation with >1 battery
11. **Different Inverter Types**: Various models, efficiency curves
12. **Grid Frequency Events**: Frequency regulation activation

## Implementation Plan

### Phase 1: Foundation (Week 1) - Using Existing Data
1. Create `test_price_provider_with_data.py` - 3 tests
2. Create `test_coordinator_with_real_data.py` - 5 tests
3. Create `test_missing_data_real_scenarios.py` - 3 tests
4. Create `validate_sample_data.py` script

### Phase 2: Core Validation (Week 2) - Using Existing Data
5. Create `test_bec_real_battery_cycles.py` - 3 tests
6. Create `test_cost_strategy_real_prices.py` - 3 tests
7. Create `test_helpers_utilities.py` - 2 tests

### Phase 3: Advanced Testing (Week 3) - Now Possible with New Data
8. Create `test_forecast_provider_validation.py` - 2 tests (weather forecast available, can test processing)
9. Create `test_ev_dispatcher_with_data.py` - 3 tests (EV charging data now available)
10. Create `test_export_optimization.py` - 2 tests (feed-in tariff documented)
11. Create `test_price_spike_scenarios.py` - 2 tests (spike data available in nordpool-02)
12. Create `test_e2e_energy_management.py` - 3 tests
13. Document results and gaps

### Phase 4: Data Collection (Ongoing)
14. Collect seasonal variations (winter/summer data)
15. Add grid outage scenarios
16. Document edge cases and battery maintenance events
17. **Note**: EV sensor data ✅ Added, Weather forecast ✅ Added, Feed-in tariff ✅ Documented, Price spike ✅ Added

## Success Metrics

- **Test Coverage**: Increase from 236 to 300+ tests
- **Integration Coverage**: All major modules tested with real data
- **Data Quality**: All sample data validated and documented
- **Gap Coverage**: All gap scenarios tested
- **Edge Cases**: Documented and tested

## Conclusion

Current testing is strong on unit tests with synthetic data but weak on integration tests with real data. The existing sample data is sufficient to create **19+ new integration tests** covering critical functions like price enrichment, battery tracking, and baseline calculations. 

The main gaps are EV/EVSE data and historical weather data for solar forecast validation.

**Recommendation**: Implement Phase 1 and 2 immediately (19 tests) using existing sample data, then collect missing data sets for Phase 3 and 4.

