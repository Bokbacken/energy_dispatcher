# AI Optimization Implementation Steps

**Purpose**: Step-by-step copy/paste instructions for implementing AI optimization features  
**Usage**: Copy one step at a time and paste to execute the implementation

---

## Step 1: Implement Core Appliance Scheduling (2 weeks)

### Context
Implement the appliance scheduling optimizer that suggests optimal times to run dishwasher, washing machine, and water heater based on price forecasts and solar production.

### Reference Documents
- Technical specs: `docs/ai_optimization_implementation_guide.md` (sections 1-2, lines 1-500)
- Code examples: `docs/ai_optimization_implementation_guide.md` (sensor implementations)
- Testing: `docs/ai_optimization_implementation_guide.md` (section 6, lines 900-1000)

### Implementation Tasks

1. **Create appliance_optimizer.py module** (8-12 hours)
   - Location: `custom_components/energy_dispatcher/appliance_optimizer.py`
   - Implement `ApplianceOptimizer` class with `optimize_schedule()` method
   - Input: appliance power (W), duration (h), time constraints, prices, solar forecast
   - Output: Dictionary with optimal_start_time, estimated_cost_sek, savings, reason
   - Algorithm: Iterate through valid time windows, calculate net cost (price - solar offset), select cheapest window

2. **Create appliance recommendation sensors** (6-8 hours)
   - Location: `custom_components/energy_dispatcher/sensor_optimization.py` (new file)
   - Implement 3 sensors: DishwasherOptimalTimeSensor, WashingMachineOptimalTimeSensor, WaterHeaterOptimalTimeSensor
   - Each sensor inherits from BaseEDSensor
   - Properties: native_value (ISO datetime), extra_state_attributes (cost, savings, reason, solar_available)
   - Device class: timestamp

3. **Add schedule_appliance service** (4-6 hours)
   - Location: `custom_components/energy_dispatcher/__init__.py` (service registration)
   - Service file: `custom_components/energy_dispatcher/services.yaml` (service definition)
   - Handler: `async_schedule_appliance()` function
   - Parameters: appliance (select), power_w (number), duration_hours (number), earliest_start (time), latest_end (time)
   - Action: Call optimizer, store recommendation, send notification

4. **Add configuration options** (2-3 hours)
   - Location: `custom_components/energy_dispatcher/config_flow.py` (options flow)
   - Add appliance power configuration: dishwasher_power_w, washing_machine_power_w, water_heater_power_w
   - Add enable_appliance_optimization boolean
   - Validation: Range 100-10000 W, step 50

5. **Add translations** (2-3 hours)
   - Location: `custom_components/energy_dispatcher/translations/en.json`
   - Location: `custom_components/energy_dispatcher/translations/sv.json`
   - Add entity names for 3 sensors
   - Add service descriptions and field labels
   - Add config option labels (see implementation guide lines 600-700)

6. **Write unit tests** (6-8 hours)
   - Location: `tests/test_appliance_optimizer.py`
   - Test optimize_schedule with various scenarios (cheap price, solar available, time constraints)
   - Test edge cases: no valid windows, solar vs grid cost comparison
   - Test sensor attribute calculations

7. **Integration with coordinator** (4-6 hours)
   - Location: `custom_components/energy_dispatcher/coordinator.py`
   - Import ApplianceOptimizer
   - In _async_update_data(), call optimizer for each appliance
   - Store recommendations in coordinator.data["appliance_recommendations"]
   - Update every 15 minutes (separate from main update interval)

8. **Create basic dashboard card** (2-3 hours)
   - Location: `docs/ai_optimization_dashboard_guide.md` (reference implementation)
   - Test YAML in personal HA instance
   - Document in getting_started.md

**Deliverables Checklist**:
- [ ] appliance_optimizer.py with ApplianceOptimizer class
- [ ] sensor_optimization.py with 3 appliance sensors
- [ ] schedule_appliance service in services.yaml
- [ ] Configuration options in config_flow.py
- [ ] Translations (EN + SV) in translations/*.json
- [ ] test_appliance_optimizer.py with 8+ tests
- [ ] Coordinator integration
- [ ] Basic dashboard example

**Estimated Effort**: 40-60 hours over 2 weeks

---

## Step 2: Implement Weather-Aware Solar Optimization (1 week)

### Context
Enhance solar forecasts by integrating weather data (cloud cover, temperature) to improve battery reserve calculations and planning accuracy.

### Reference Documents
- Strategy overview: `docs/cost_strategy_and_battery_optimization.md` (Weather-Aware Solar Optimization section)
- Technical specs: `docs/ai_optimization_implementation_guide.md` (weather optimizer section)

### Implementation Tasks

1. **Create weather_optimizer.py module** (6-8 hours)
   - Location: `custom_components/energy_dispatcher/weather_optimizer.py`
   - Implement `WeatherOptimizer` class with `adjust_solar_forecast_for_weather()` method
   - Input: base_solar_forecast, weather_forecast, historical_adjustment_factors
   - Cloud cover adjustments: Clear (100%), Partly cloudy (70-80%), Cloudy (40-60%), Overcast (20-30%)
   - Temperature adjustments: Panel efficiency reduction at high temps (0.4-0.5% per °C above 25°C)
   - Output: Adjusted solar forecast with confidence intervals

2. **Add weather entity configuration** (2-3 hours)
   - Location: `custom_components/energy_dispatcher/config_flow.py`
   - Add optional weather_entity (entity selector, domain: weather)
   - Add enable_weather_optimization boolean (default: True)

3. **Create weather-adjusted solar sensor** (3-4 hours)
   - Location: `custom_components/energy_dispatcher/sensor_optimization.py`
   - Implement WeatherAdjustedSolarForecastSensor
   - Attributes: base_forecast_kwh, weather_adjusted_kwh, confidence_level, limiting_factor
   - Unit: kWh

4. **Update battery reserve calculation** (4-6 hours)
   - Location: `custom_components/energy_dispatcher/cost_strategy.py` (modify calculate_battery_reserve)
   - If weather optimization enabled and forecast adjusted downward, increase reserve by 10-20%
   - Document reasoning in code comments

5. **Add translations** (1-2 hours)
   - Update translations/en.json and translations/sv.json
   - Add weather-adjusted solar sensor name
   - Add weather configuration labels

6. **Write tests** (4-6 hours)
   - Location: `tests/test_weather_optimizer.py`
   - Test cloud cover adjustments (clear, cloudy, overcast)
   - Test temperature effects
   - Test integration with battery reserve calculation

7. **Update dashboard** (2-3 hours)
   - Add weather-adjusted solar forecast card to dashboard guide
   - Show base vs adjusted comparison

**Deliverables Checklist**:
- [ ] weather_optimizer.py with WeatherOptimizer class
- [ ] Weather configuration options
- [ ] WeatherAdjustedSolarForecastSensor
- [ ] Updated battery reserve calculation
- [ ] Translations (EN + SV)
- [ ] test_weather_optimizer.py
- [ ] Dashboard documentation update

**Estimated Effort**: 20-30 hours over 1 week

---

## Step 3: Implement Export Profitability Analysis (1 week)

### Context
Add conservative export logic that defaults to "never export" but detects truly profitable opportunities when spot prices are exceptional.

### Reference Documents
- Strategy: `docs/cost_strategy_and_battery_optimization.md` (Export Profitability Analysis section)
- Implementation: `docs/ai_optimization_implementation_guide.md` (Export sensors and services)

### Implementation Tasks

1. **Create export_analyzer.py module** (6-8 hours)
   - Location: `custom_components/energy_dispatcher/export_analyzer.py`
   - Implement `ExportAnalyzer` class with `should_export_energy()` method
   - Input: spot_price, purchase_price, export_price, battery_soc, battery_capacity, degradation_cost, upcoming_high_cost_hours
   - Logic: Default False; True only if spot > 5 SEK/kWh AND (battery full OR no upcoming high-cost periods)
   - Calculate opportunity cost (value of storing vs selling)
   - Output: Dictionary with should_export, export_power_w, estimated_revenue, reason

2. **Create export opportunity sensors** (4-6 hours)
   - Location: `custom_components/energy_dispatcher/sensor_optimization.py`
   - Implement ExportOpportunityBinarySensor (on/off)
   - Implement ExportRevenueEstimateSensor (SEK)
   - Attributes: export_power_w, export_price, opportunity_cost, duration_estimate_h, reason

3. **Add set_export_mode service** (3-4 hours)
   - Location: `custom_components/energy_dispatcher/services.yaml`
   - Service: set_export_mode
   - Parameters: mode (select: never, excess_solar_only, peak_price_opportunistic), min_export_price (number)
   - Handler: Store mode in config, update export logic

4. **Add export configuration** (2-3 hours)
   - Location: `custom_components/energy_dispatcher/config_flow.py`
   - Add export_mode (select, default: "never")
   - Add min_export_price_sek_per_kwh (number, default: 3.0, range: 0-10)
   - Add battery_degradation_cost_per_cycle_sek (number, default: 0.50)

5. **Add translations** (1-2 hours)
   - Update translations for export sensors and service
   - Clear labels: "Export Opportunity", "Export Revenue Estimate"
   - Service descriptions in EN + SV

6. **Write tests** (4-6 hours)
   - Location: `tests/test_export_analyzer.py`
   - Test default "never export" behavior
   - Test high spot price trigger (>5 SEK/kWh)
   - Test battery full + excess solar scenario
   - Test opportunity cost calculation

7. **Integration and dashboard** (3-4 hours)
   - Integrate ExportAnalyzer into coordinator
   - Add export monitoring card to dashboard guide
   - Document conservative philosophy

**Deliverables Checklist**:
- [ ] export_analyzer.py with ExportAnalyzer class
- [ ] Export sensors (binary + revenue estimate)
- [ ] set_export_mode service
- [ ] Export configuration options
- [ ] Translations (EN + SV)
- [ ] test_export_analyzer.py
- [ ] Dashboard documentation

**Estimated Effort**: 20-30 hours over 1 week

---

## Step 4: Implement Load Shifting & Peak Shaving (2 weeks)

### Context
Add intelligent load shifting recommendations and peak shaving to minimize costs and demand charges.

### Reference Documents
- Strategy: `docs/cost_strategy_and_battery_optimization.md` (Load Shifting & Peak Shaving sections)
- Implementation: `docs/ai_optimization_implementation_guide.md` (load shift optimizer section)

### Implementation Tasks

1. **Create load_shift_optimizer.py module** (8-10 hours)
   - Location: `custom_components/energy_dispatcher/load_shift_optimizer.py`
   - Implement `LoadShiftOptimizer` class with `recommend_load_shifts()` method
   - Input: current_consumption, baseline_load, prices, flexible_categories, user_flexibility_hours
   - Identify flexible_load = current - baseline
   - Find cheaper windows within flexibility period
   - Calculate savings potential for each shift
   - Output: List of recommendations sorted by savings

2. **Create load shift sensors** (4-6 hours)
   - Location: `custom_components/energy_dispatcher/sensor_optimization.py`
   - Implement LoadShiftOpportunitySensor (text description)
   - Implement LoadShiftSavingsSensor (SEK)
   - Attributes: shift_to_time, savings_per_hour, price_now, price_then, affected_loads, user_impact

3. **Create peak_shaving.py module** (6-8 hours)
   - Location: `custom_components/energy_dispatcher/peak_shaving.py`
   - Implement `PeakShaving` class with `calculate_peak_shaving_action()` method
   - Input: current_grid_import, peak_threshold, battery_soc, battery_max_discharge, reserve_soc
   - Logic: If grid_import > threshold AND battery_soc > reserve, discharge to cap peak
   - Calculate available discharge duration
   - Output: Dictionary with discharge_battery, discharge_power_w, duration_estimate_h, reason

4. **Add peak shaving configuration** (2-3 hours)
   - Location: `custom_components/energy_dispatcher/config_flow.py`
   - Add enable_peak_shaving (boolean, default: False)
   - Add peak_threshold_w (number, default: 10000, range: 1000-50000)

5. **Integration with battery control** (6-8 hours)
   - Location: `custom_components/energy_dispatcher/coordinator.py`
   - Call PeakShaving.calculate_peak_shaving_action() in update cycle
   - Override battery discharge when peak shaving active
   - Log peak shaving events

6. **Add translations** (2-3 hours)
   - Update translations for load shift sensors
   - Add peak shaving configuration labels
   - Clear descriptions in EN + SV

7. **Write tests** (8-10 hours)
   - Location: `tests/test_load_shift_optimizer.py`
   - Location: `tests/test_peak_shaving.py`
   - Test load shift identification and savings calculation
   - Test peak detection and battery discharge logic
   - Test reserve protection

8. **Dashboard updates** (3-4 hours)
   - Add load shift opportunity card
   - Add peak shaving status indicator
   - Document in dashboard guide

**Deliverables Checklist**:
- [ ] load_shift_optimizer.py with LoadShiftOptimizer class
- [ ] Load shift sensors (opportunity + savings)
- [ ] peak_shaving.py with PeakShaving class
- [ ] Peak shaving configuration
- [ ] Battery control integration
- [ ] Translations (EN + SV)
- [ ] test_load_shift_optimizer.py and test_peak_shaving.py
- [ ] Dashboard documentation

**Estimated Effort**: 40-50 hours over 2 weeks

---

## Step 5: Implement Comfort-Aware Optimization (1 week)

### Context
Add user comfort preferences that filter and adjust recommendations based on convenience vs cost priorities.

### Reference Documents
- Strategy: `docs/cost_strategy_and_battery_optimization.md` (Comfort-Aware Optimization section)
- Implementation: `docs/ai_optimization_implementation_guide.md` (comfort manager section)

### Implementation Tasks

1. **Create comfort_manager.py module** (6-8 hours)
   - Location: `custom_components/energy_dispatcher/comfort_manager.py`
   - Implement `ComfortManager` class with `optimize_with_comfort_balance()` method
   - Input: optimization_recommendations, user_comfort_priority, current_conditions
   - Filtering logic:
     - cost_first: Accept all recommendations
     - balanced: Accept if savings/inconvenience_score > 2.0
     - comfort_first: Only low-impact recommendations, no inconvenient times
   - Output: Filtered list of recommendations

2. **Add comfort configuration** (3-4 hours)
   - Location: `custom_components/energy_dispatcher/config_flow.py`
   - Add comfort_priority (select: cost_first, balanced, comfort_first; default: balanced)
   - Add quiet_hours_start (time, default: 22:00)
   - Add quiet_hours_end (time, default: 07:00)
   - Add min_battery_peace_of_mind (number, %, default: 20)

3. **Apply comfort filtering** (4-6 hours)
   - Location: Modify all optimizer modules
   - Pass comfort_priority to each optimizer
   - Filter recommendations through ComfortManager before storing
   - Add "filtered_by_comfort" attribute to show what was filtered out

4. **Add override mechanisms** (4-6 hours)
   - Location: `custom_components/energy_dispatcher/services.yaml`
   - Enhance override_battery_mode service with expiration
   - Add override tracking in coordinator
   - Auto-reset overrides after expiration

5. **Add translations** (2-3 hours)
   - Update translations for comfort options
   - Add override service labels
   - Clear descriptions: "Cost First: Maximize savings", "Balanced: Balance cost and comfort", "Comfort First: Prioritize convenience"

6. **Write tests** (4-6 hours)
   - Location: `tests/test_comfort_manager.py`
   - Test filtering for each priority level
   - Test quiet hours enforcement
   - Test battery reserve peace-of-mind

7. **Dashboard controls** (3-4 hours)
   - Add comfort priority selector to dashboard
   - Add override buttons with duration pickers
   - Document override workflow

**Deliverables Checklist**:
- [ ] comfort_manager.py with ComfortManager class
- [ ] Comfort configuration options (priority, quiet hours, min battery)
- [ ] Comfort filtering in all optimizers
- [ ] Override mechanisms with expiration
- [ ] Translations (EN + SV)
- [ ] test_comfort_manager.py
- [ ] Dashboard controls

**Estimated Effort**: 20-30 hours over 1 week

---

## Step 6: Testing, Refinement & Documentation (2 weeks)

### Context
Comprehensive testing, performance optimization, bug fixes, and final documentation polish.

### Reference Documents
- Testing strategy: `docs/ai_optimization_implementation_guide.md` (section 6)
- Automation examples: `docs/ai_optimization_automation_examples.md` (all sections)
- Dashboard guide: `docs/ai_optimization_dashboard_guide.md` (all sections)

### Implementation Tasks

1. **Integration testing** (12-16 hours)
   - Location: `tests/test_optimization_coordinator.py`
   - Test full optimization cycle end-to-end
   - Test all optimizers working together
   - Test conflict resolution (e.g., EV charging vs appliance scheduling)
   - Test coordinator data flow
   - Test sensor updates
   - Mock price/solar/weather data

2. **Performance optimization** (8-10 hours)
   - Implement caching in optimization_coordinator.py (5-15 min TTL)
   - Measure and optimize slow operations
   - Add async processing where beneficial
   - Profile memory usage
   - Optimize update intervals (appliance: 1h, export: 5min, main: 15min)

3. **Real-world testing** (16-20 hours)
   - Test with actual HA instance and real data
   - Monitor for 3-5 days
   - Collect edge cases and bugs
   - Validate savings estimates
   - Test all dashboard cards
   - Test all automations

4. **Bug fixes and edge cases** (8-12 hours)
   - Fix issues discovered in real-world testing
   - Handle missing data gracefully (prices unavailable, weather unavailable)
   - Add error recovery
   - Improve logging for debugging

5. **Documentation polish** (8-10 hours)
   - Update README.md with AI optimization overview
   - Update getting_started.md with setup steps
   - Ensure all code examples in docs are tested
   - Add FAQ section to dashboard guide
   - Create video tutorial script (optional)

6. **Translation validation** (4-6 hours)
   - Verify all EN translations are clear
   - Verify all SV translations are accurate
   - Ensure consistency across all files
   - Test UI with both languages

7. **Create automation templates** (6-8 hours)
   - Test all 12 automations from automation_examples.md
   - Verify YAML syntax
   - Add comments and customization notes
   - Create blueprint versions for easy import

8. **Performance benchmarking** (4-6 hours)
   - Measure sensor update latency
   - Measure recommendation calculation time
   - Measure memory footprint
   - Document performance characteristics
   - Verify <5s sensor updates, <10s recommendations

9. **Final validation** (8-10 hours)
   - Run full test suite
   - Verify all 10+ sensors work
   - Verify all 3 services work
   - Test all configuration options
   - Test overrides and manual controls
   - Validate translations in UI
   - Test dashboard on mobile and desktop

10. **Release preparation** (4-6 hours)
    - Update CHANGELOG.md
    - Bump version in manifest.json
    - Update hacs.json if needed
    - Create release notes
    - Prepare announcement

**Deliverables Checklist**:
- [ ] Integration tests passing
- [ ] Performance optimized and benchmarked
- [ ] Real-world testing complete (3-5 days)
- [ ] All bugs fixed
- [ ] Documentation polished
- [ ] Translations validated (EN + SV)
- [ ] All 12 automations tested
- [ ] Performance meets targets
- [ ] Release notes prepared
- [ ] CHANGELOG updated

**Estimated Effort**: 40-50 hours over 2 weeks

---

## Usage Instructions

### For Each Step

1. **Copy the entire step** (from "## Step X" to the horizontal line before next step)
2. **Paste into chat** with instruction: "Implement this step completely following the reference documents and tasks listed"
3. **Wait for implementation** including code, tests, and documentation
4. **Review and test** the implementation
5. **Provide feedback** if changes needed
6. **Move to next step** once satisfied

### Expected Timeline

- **Week 1-2**: Step 1 (Appliance Scheduling)
- **Week 3**: Step 2 (Weather Integration)
- **Week 4**: Step 3 (Export Analysis)
- **Week 5-6**: Step 4 (Load Shifting & Peak Shaving)
- **Week 7**: Step 5 (Comfort Integration)
- **Week 8-9**: Step 6 (Testing & Refinement)

**Total: 6-9 weeks** as planned in the roadmap

---

## Notes

- Each step is designed to be self-contained and reference the comprehensive documentation
- Steps can be adjusted based on priorities (e.g., skip export if not needed)
- Testing is integrated into each step but Step 6 adds comprehensive integration testing
- All code changes follow Home Assistant best practices and the repository's i18n guidelines
- Translations (EN + SV) are included in every step

---

**Ready to start? Copy Step 1 and let's begin!** 🚀
