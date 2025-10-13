# Testing Documentation

This directory contains comprehensive testing documentation and analysis for the Energy Dispatcher integration.

## Documents

### [TESTING_ANALYSIS.md](TESTING_ANALYSIS.md)
**Comprehensive testing coverage analysis**

Complete breakdown of current test coverage (236 tests across 9 modules), sample data quality assessment, and detailed recommendations for new tests.

**Key sections**:
- Current test coverage by module
- Sample data quality ratings (Excellent/Good/Fair/Poor)
- 19 recommended Priority 1 tests (can be implemented now)
- Implementation roadmap (Phase 1-4)
- Success metrics

**Quick stats**:
- 236 existing tests (well-tested: BEC, Cost Strategy, Missing Data, Physics)
- 13 sample data files (7-day period, Oct 4-11, 2025)
- 19 new tests ready to implement with existing data
- Target: 300+ total tests

---

### [SAMPLE_DATA_NEEDS.md](SAMPLE_DATA_NEEDS.md)
**Prioritized list of additional sample data sets needed**

Detailed requirements for additional data collection to enable comprehensive testing beyond what's currently available.

**Critical missing data** (high priority):
1. Historical weather data (Oct 4-11, 2025) - for solar forecast validation
2. EV/EVSE sensor data (24-48h, with realistic gaps) - for EV dispatcher testing
3. Grid feed-in tariff data - for export optimization

**Note**: Gaps in existing data are intentional and valuable. The integration uses cumulative energy counters that continue counting during gaps (HA crashes, updates, network issues), so testing with gaps validates real-world scenarios.

**Nice to have** (medium priority):
- Winter/summer data sets
- Price spike events
- Grid outages
- Battery maintenance events

**Quick reference table** showing all 13 needed data sets with priorities (⭐⭐⭐ = Critical, ⭐⭐ = Nice to have, ⭐ = Optional)

---

## Tools

### [validate_sample_data.py](../../tests/validate_sample_data.py)
**Sample data validation and quality assessment script**

Python script that validates all CSV sample data files, identifies quality issues, and extracts perfect windows for testing.

**Features**:
- Validates data quality (gaps, monotonicity, ranges)
- Type-specific validation (prices, SOC, power, meters)
- Identifies best continuous windows for testing
- Can extract perfect windows to separate fixtures
- Generates detailed validation report

**Usage**:
```bash
# Basic validation report
python tests/validate_sample_data.py --report-only

# Full validation with window extraction
python tests/validate_sample_data.py --extract-windows
```

**Output example**:
```
Files validated: 12
Valid files: 10
Files with issues: 2

Excellent for testing (no gaps):
  ✓ historic_total_house_energy_consumption.csv

Good for testing (minor gaps):
  ✓ historic_batteries_power_in_out.csv
  ✓ historic_today_energy_supply_from_grid.csv
  ✓ historic_total_energy_supply_from_grid.csv
```

---

## Example Test Implementation

### [test_price_provider_with_data.py](../../tests/test_price_provider_with_data.py)
**Integration tests for price provider using real sample data**

Demonstrates how to create integration tests that use real sample data from `tests/fixtures/`.

**Test classes**:
1. `TestEnrichedSpotCalculation` - Validates fee calculations
2. `TestPriceProviderRealData` - Tests with historical CSV data
3. `TestNordpoolParsing` - Tests YAML parsing
4. `TestPriceGapHandling` - Tests gap detection and windowing

**Key techniques**:
- Loading CSV sample data
- Loading YAML sample data
- Validating against real measurements
- Statistical analysis (min/max/avg)
- Gap detection and continuous window identification
- Tolerance-based validation (±10%)

**Run the tests**:
```bash
pytest tests/test_price_provider_with_data.py -v -s
```

---

## Testing Strategy

### Current Approach

**Unit Tests** ✓ Strong coverage
- Synthetic data
- Isolated function testing
- Fast execution
- Good for algorithm validation

**Gap**: Integration tests with real data

### New Approach (Being Implemented)

**Integration Tests** 🚧 In progress
- Real sample data from fixtures
- Multi-sensor coordination
- Data quality validation
- Real-world scenario testing

### Test Pyramid

```
        /\
       /  \      E2E Tests (few, slow)
      /____\     ├─ Full week simulation
     /      \    └─ Peak shaving scenarios
    /        \   
   /__________\  Integration Tests (more, medium speed)
  /            \ ├─ Price provider with data
 /   Unit Tests \ ├─ Coordinator with real sensors
/________________\ ├─ BEC with real cycles
                   ├─ Missing data scenarios
                   └─ Cost strategy with real prices
                   
                   Unit Tests (many, fast)
                   ├─ BEC (49 tests)
                   ├─ Cost Strategy (28 tests)
                   ├─ Missing Data (23 tests)
                   ├─ Manual Forecast (37 tests)
                   └─ ... (total 236 tests)
```

---

## Implementation Roadmap

### ✅ Completed
- [x] Testing analysis document
- [x] Sample data needs document
- [x] Sample data validation script
- [x] Example integration test (price provider)

### 🚧 Phase 1 (In Progress) - Foundation with Existing Data
- [x] `test_price_provider_with_data.py` - 11 tests
- [ ] `test_coordinator_with_real_data.py` - 5 tests
- [ ] `test_missing_data_real_scenarios.py` - 3 tests

**Target**: 19 new tests (current: 11)

### 📋 Phase 2 - Core Validation with Existing Data
- [ ] `test_bec_real_battery_cycles.py` - 3 tests
- [ ] `test_cost_strategy_real_prices.py` - 3 tests
- [ ] `test_helpers_utilities.py` - 2 tests

**Target**: 8 new tests

### 📋 Phase 3 - Advanced Testing (Requires New Data)
- [ ] Collect missing data (weather, EV with realistic gaps, tariffs)
- [ ] `test_forecast_provider_validation.py` - 2 tests
- [ ] `test_e2e_energy_management.py` - 3 tests
- [ ] Document results and gaps

**Target**: 5 new tests

### 📋 Phase 4 - Ongoing Data Collection
- [ ] Seasonal variations (winter, summer)
- [ ] Edge cases (price spikes, outages, maintenance)
- [ ] Multi-installation data (various setups)

**Target**: Complete coverage

---

## Best Practices

### Writing Integration Tests with Sample Data

1. **Load data systematically**
   ```python
   from tests.data_quality_report import parse_timestamp
   
   def load_csv(filename):
       with open(FIXTURES_DIR / filename) as f:
           reader = csv.DictReader(f)
           for row in reader:
               ts = parse_timestamp(row['timestamp'])
               val = float(row['value'])
               yield ts, val
   ```

2. **Use continuous windows**
   - Refer to validation script output for best windows
   - Document which window you're using
   - Handle gaps explicitly

3. **Statistical validation**
   - Don't expect exact matches
   - Use tolerance bands (e.g., ±10%)
   - Calculate and report metrics (MAE, RMSE, %)

4. **Print useful diagnostics**
   - Use `pytest -s` to see prints
   - Report ranges, averages, gaps
   - Help future debugging

5. **Document data assumptions**
   - Which time period
   - Expected sensor behavior
   - Known gaps or issues

### Sample Data Format

All sample data in `tests/fixtures/` should follow this format:

```csv
timestamp,value
2025-10-04T22:00:00+00:00,45.5
2025-10-04T22:00:30+00:00,45.7
```

- ISO 8601 timestamps with timezone
- Numeric values
- Header row required
- UTF-8 encoding

---

## Contributing

### Adding New Tests

1. Review `TESTING_ANALYSIS.md` for gaps
2. Check if sample data is available
3. Use existing tests as templates
4. Run validation script first
5. Document which data window you use
6. Include statistical validation
7. Update this README with progress

### Adding New Sample Data

1. Review `SAMPLE_DATA_NEEDS.md` for priorities
2. Follow CSV format requirements
3. Add to `tests/fixtures/`
4. Run validation script
5. Document in PR description
6. Update sample data report

### Running All Tests

```bash
# All tests
pytest tests/ -v

# Integration tests only
pytest tests/test_*_with_data.py -v

# With coverage
pytest tests/ --cov=custom_components.energy_dispatcher --cov-report=html
```

---

## Questions?

See [TESTING_ANALYSIS.md](TESTING_ANALYSIS.md) for detailed analysis or ask in GitHub issues.
