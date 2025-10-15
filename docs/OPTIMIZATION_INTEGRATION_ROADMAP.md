# Optimization Integration Roadmap

**Date**: 2025-10-15  
**Status**: Implementation Plan  
**Target**: Merge separate optimization components into unified system

---

## Executive Summary

This document provides a **step-by-step implementation plan** to integrate currently separate optimization components (export analysis, solar forecasting, weather adjustments, battery reserve) into a unified optimization system. Each step is designed as an independent PR that can be implemented and tested separately.

**Current State**: Optimization components exist as separate modules
- `planner.py` - Battery and EV optimization (24h planning)
- `export_analyzer.py` - Export profitability analysis (real-time)
- `weather_optimizer.py` - Weather-aware solar adjustments
- `cost_strategy.py` - Cost thresholds and battery reserve
- Solar forecast - Read but not used in planning

**Goal State**: Unified optimization system that considers all factors in a single 24-hour plan

---

## Implementation Strategy

### Approach: Incremental Integration (Recommended)

Break the work into 4 manageable PRs, each adding one major capability:

1. **PR #1: Export Mode Integration** - Add export opportunities to optimization planning
2. **PR #2: Solar Forecast Integration** - Use solar forecast to improve battery decisions
3. **PR #3: Cost-Benefit Analysis** - Factor in battery degradation and profitability
4. **PR #4: Weather-Aware Planning** - Integrate weather adjustments into reserve calculation

**Why Incremental?**
- ✅ Each PR is testable independently
- ✅ Lower risk of breaking existing functionality
- ✅ Easier to review and validate
- ✅ Can be deployed progressively
- ✅ Provides value at each step

---

## PR #1: Export Mode Integration

### Goal
Integrate export mode configuration into the optimization planning so the 24-hour plan includes export decisions based on profitability.

### Current Gap
- Export mode exists (`never`, `excess_solar_only`, `peak_price_opportunistic`)
- `ExportAnalyzer` makes real-time decisions
- Optimization plan (`simple_plan`) doesn't consider export mode
- No discharge-to-export actions in 24h plan

### Changes Required

#### 1.1 Update `models.py`
Add export price to `PricePoint`:
```python
@dataclass
class PricePoint:
    time: datetime
    spot_sek_per_kwh: float
    enriched_sek_per_kwh: float
    export_sek_per_kwh: float = 0.0  # NEW: Export price for this hour
```

#### 1.2 Update `coordinator.py`
Calculate export prices when building hourly prices:
```python
# In _compute_cost_analysis(), after enriched price calculation
for price_point in hourly_prices:
    # Calculate export price based on contract
    export_price = self._calculate_export_price(
        price_point.spot_sek_per_kwh,
        current_year=now.year
    )
    price_point.export_sek_per_kwh = export_price

# Add helper method
def _calculate_export_price(self, spot_price: float, current_year: int) -> float:
    """Calculate export price based on year and contract."""
    grid_utility = 0.067  # nätnytta
    energy_surcharge = 0.02  # påslag
    tax_return = 0.60 if current_year <= 2025 else 0.0  # expires 2026
    return spot_price + grid_utility + energy_surcharge + tax_return
```

#### 1.3 Update `planner.py`
Add export mode parameter and export decision logic:
```python
def simple_plan(
    now: datetime,
    horizon_hours: int,
    prices: List[PricePoint],
    solar: List[ForecastPoint],
    batt_soc_pct: float,
    batt_capacity_kwh: float,
    batt_max_charge_w: int,
    ev_need_kwh: float,
    cheap_threshold: float,
    ev_deadline: Optional[datetime] = None,
    ev_mode: ChargingMode = ChargingMode.ECO,
    cost_strategy: Optional[CostStrategy] = None,
    export_mode: str = "never",  # NEW
    battery_degradation_per_cycle: float = 0.50,  # NEW
) -> List[PlanAction]:
    # ... existing code ...
    
    # NEW: After discharge decision
    if export_mode != "never" and price:
        should_export = self._should_export_to_grid(
            price=price,
            current_soc=current_batt_soc,
            reserve_soc=reserve_soc,
            solar_w=solar_w,
            export_mode=export_mode,
            degradation_cost=battery_degradation_per_cycle
        )
        
        if should_export:
            action.discharge_batt_w = batt_max_charge_w
            # ... update SOC simulation
            action.notes = f"Export (price: {price.export_sek_per_kwh:.2f} SEK/kWh)"

def _should_export_to_grid(
    self,
    price: PricePoint,
    current_soc: float,
    reserve_soc: float,
    solar_w: float,
    export_mode: str,
    degradation_cost: float
) -> bool:
    """Determine if exporting to grid is profitable."""
    
    # Mode: never
    if export_mode == "never":
        return False
    
    # Mode: excess_solar_only
    if export_mode == "excess_solar_only":
        if current_soc >= 95 and solar_w > 1000:
            return True
        return False
    
    # Mode: peak_price_opportunistic
    if export_mode == "peak_price_opportunistic":
        # Check if export is profitable
        profit_per_kwh = price.export_sek_per_kwh - (degradation_cost / 10.0)  # assuming 10 kWh battery
        
        # Export if:
        # 1. Profitable after degradation
        # 2. Battery above reserve + buffer
        # 3. Export price significantly above purchase price
        if (profit_per_kwh > 0 and 
            current_soc > reserve_soc + 10 and
            price.export_sek_per_kwh > price.enriched_sek_per_kwh * 0.7):
            return True
        
        # Also export if battery full and solar excess
        if current_soc >= 95 and solar_w > 1000:
            return True
    
    return False
```

#### 1.4 Update `coordinator.py` (planner call)
Pass export mode to planner:
```python
export_mode = self._get_cfg(CONF_EXPORT_MODE, "never")
degradation_cost = _safe_float(
    self._get_cfg(CONF_BATTERY_DEGRADATION_COST_PER_CYCLE_SEK, 0.50), 
    0.50
)

plan = simple_plan(
    now=now,
    horizon_hours=24,
    prices=hourly_prices,
    solar=solar_points,
    batt_soc_pct=batt_soc_pct,
    batt_capacity_kwh=batt_capacity_kwh,
    batt_max_charge_w=batt_max_charge_w,
    ev_need_kwh=ev_need_kwh,
    cheap_threshold=cheap_threshold,
    ev_deadline=None,
    ev_mode=ChargingMode.ECO,
    cost_strategy=self._cost_strategy,
    export_mode=export_mode,  # NEW
    battery_degradation_per_cycle=degradation_cost,  # NEW
)
```

#### 1.5 Add Tests
Create `tests/test_export_integration.py`:
```python
def test_export_mode_never():
    """Test that no export happens when mode is never."""
    # ... test implementation

def test_export_mode_excess_solar_only():
    """Test export only when battery full and solar excess."""
    # ... test implementation

def test_export_mode_peak_price_opportunistic():
    """Test export during profitable high prices."""
    # ... test implementation

def test_export_price_calculation():
    """Test export price formula for 2025 and 2026."""
    # ... test implementation
```

#### 1.6 Update Documentation
Update `OPTIMIZATION_RULES_AND_DECISIONS.md`:
- Remove "export mode NOT integrated" from gaps
- Add export decision rules to Rule 4
- Add export price calculation section
- Update examples

### Copy-Paste PR Instructions for PR #1

```
@copilot Please implement PR #1 from docs/OPTIMIZATION_INTEGRATION_ROADMAP.md

Title: Integrate export mode into optimization planning

Changes:
1. Add export_sek_per_kwh field to PricePoint model in models.py
2. Add _calculate_export_price() method to coordinator.py
3. Calculate export prices in _compute_cost_analysis() in coordinator.py
4. Add export_mode and battery_degradation_per_cycle parameters to simple_plan() in planner.py
5. Add _should_export_to_grid() method to planner.py
6. Integrate export decision into battery discharge logic in planner.py
7. Pass export_mode and degradation_cost to simple_plan() call in coordinator.py
8. Create tests/test_export_integration.py with 4 test cases
9. Update OPTIMIZATION_RULES_AND_DECISIONS.md to document export integration

Test data: Use E.ON SE4 contract parameters (grid utility 0.067, surcharge 0.02, tax return 0.60 for 2025)
```

### Success Criteria
- ✅ Export mode configuration affects optimization plan
- ✅ 24-hour plan includes export actions when profitable
- ✅ Export decisions respect battery reserve
- ✅ Export price calculated correctly for 2025 vs 2026
- ✅ All existing tests still pass
- ✅ New tests validate export integration

### Expected Benefits
- Export opportunities visible in 24-hour plan
- Better revenue estimation for users
- Coordinated battery discharge decisions
- Clear profitability analysis

---

## PR #2: Solar Forecast Integration

### Goal
Use solar forecast data to improve battery charging decisions and reduce unnecessary reserve requirements.

### Current Gap
- Solar forecast is read but not used in planning
- No "wait for solar" logic
- Reserve calculation doesn't account for expected solar during high-cost hours
- No anticipation of solar production

### Changes Required

#### 2.1 Update `cost_strategy.py`
Enhance `calculate_battery_reserve()` to account for solar:
```python
def calculate_battery_reserve(
    self,
    prices: List[PricePoint],
    now: datetime,
    battery_capacity_kwh: float,
    current_soc: float,
    horizon_hours: int = 24,
    weather_adjustment: Optional[Dict] = None,
    solar_forecast: Optional[List[ForecastPoint]] = None,  # NEW
) -> float:
    """Calculate battery reserve with solar forecast consideration."""
    
    high_cost_windows = self.predict_high_cost_windows(prices, now, horizon_hours)
    
    if not high_cost_windows:
        return 0.0
    
    total_high_cost_hours = sum(
        (end - start).total_seconds() / 3600
        for start, end in high_cost_windows
    )
    
    estimated_load_kw = 1.0
    required_energy_kwh = total_high_cost_hours * estimated_load_kw
    
    # NEW: Reduce requirement by expected solar during high-cost hours
    if solar_forecast:
        solar_during_high_cost = self._calculate_solar_during_windows(
            solar_forecast, high_cost_windows
        )
        # Reduce requirement by 80% of expected solar (conservative)
        required_energy_kwh -= solar_during_high_cost * 0.8
        required_energy_kwh = max(0, required_energy_kwh)  # Can't be negative
    
    required_soc = (required_energy_kwh / battery_capacity_kwh) * 100
    
    # ... existing weather adjustment code ...
    
    reserve_soc = min(60.0, required_soc)
    return reserve_soc

def _calculate_solar_during_windows(
    self,
    solar_forecast: List[ForecastPoint],
    windows: List[tuple[datetime, datetime]]
) -> float:
    """Calculate expected solar production during time windows."""
    total_solar_kwh = 0.0
    
    for start, end in windows:
        for point in solar_forecast:
            if start <= point.time < end:
                # Convert watts to kWh (assuming 1 hour duration)
                total_solar_kwh += point.watts / 1000.0
    
    return total_solar_kwh
```

#### 2.2 Update `planner.py`
Add solar-aware charging logic:
```python
def simple_plan(...):
    # ... existing code ...
    
    # Build actions
    current_batt_soc = batt_soc_pct
    t = cursor
    while t < end:
        price = price_map.get(t)
        sol = solar_map.get(t)
        action = PlanAction(time=t)
        
        # NEW: Check if solar coming soon
        solar_coming_soon = self._is_solar_coming_soon(
            t, solar_map, threshold_w=2000, window_hours=2
        )
        
        # Battery management with cost strategy
        if price:
            solar_w = sol.watts if sol else 0
            
            # Check if we should charge battery
            should_charge = cost_strategy.should_charge_battery(
                price.enriched_sek_per_kwh,
                current_batt_soc,
                reserve_soc,
                solar_w
            )
            
            # NEW: Skip grid charging if significant solar expected soon
            if should_charge and solar_coming_soon and current_batt_soc > reserve_soc:
                should_charge = False
                action.notes = f"Skip charge (solar expected soon)"
            
            # ... rest of charging/discharging logic ...

def _is_solar_coming_soon(
    self,
    current_time: datetime,
    solar_map: dict,
    threshold_w: float,
    window_hours: int
) -> bool:
    """Check if significant solar production is expected within window."""
    for hour in range(1, window_hours + 1):
        future_time = current_time + timedelta(hours=hour)
        solar_point = solar_map.get(future_time)
        if solar_point and solar_point.watts > threshold_w:
            return True
    return False
```

#### 2.3 Update `coordinator.py`
Pass solar forecast to reserve calculation:
```python
reserve_soc = self._cost_strategy.calculate_battery_reserve(
    hourly_prices,
    now,
    batt_cap_kwh,
    current_soc,
    24,
    weather_adjustment=weather_data,  # existing
    solar_forecast=solar_points,  # NEW
)
```

#### 2.4 Add Tests
Create `tests/test_solar_integration.py`:
```python
def test_reserve_reduced_with_solar_forecast():
    """Test that reserve is lower when solar expected during high-cost hours."""
    # ... test implementation

def test_skip_charging_when_solar_coming():
    """Test that grid charging skipped if solar coming soon."""
    # ... test implementation

def test_solar_calculation_during_windows():
    """Test solar energy calculation during high-cost windows."""
    # ... test implementation
```

### Copy-Paste PR Instructions for PR #2

```
@copilot Please implement PR #2 from docs/OPTIMIZATION_INTEGRATION_ROADMAP.md

Title: Integrate solar forecast into optimization planning

Changes:
1. Add solar_forecast parameter to calculate_battery_reserve() in cost_strategy.py
2. Add _calculate_solar_during_windows() method to cost_strategy.py
3. Reduce reserve requirement by expected solar during high-cost hours
4. Add _is_solar_coming_soon() helper method to planner.py
5. Add solar-aware charging logic to skip grid charging if solar coming soon
6. Pass solar_points to calculate_battery_reserve() in coordinator.py
7. Create tests/test_solar_integration.py with 3 test cases
8. Update OPTIMIZATION_RULES_AND_DECISIONS.md to document solar integration

Use conservative 80% factor when reducing reserve by solar forecast.
```

### Success Criteria
- ✅ Battery reserve reduced when solar expected during high-cost hours
- ✅ Grid charging skipped when solar coming within 2 hours
- ✅ Reserve calculation accounts for solar production
- ✅ Tests validate solar integration
- ✅ All existing tests still pass

### Expected Benefits
- Lower battery reserve requirements
- Less grid charging needed
- Better utilization of solar forecast
- More efficient battery usage

---

## PR #3: Cost-Benefit Analysis

### Goal
Factor in battery degradation costs and profitability thresholds to avoid unprofitable charge/discharge cycles.

### Current Gap
- Battery degradation cost configured but not used in planning
- No cost-benefit analysis for arbitrage opportunities
- Small price differences trigger full charge/discharge cycles
- No profitability threshold

### Changes Required

#### 3.1 Update `cost_strategy.py`
Add cost-benefit analysis methods:
```python
def calculate_arbitrage_profit(
    self,
    buy_price: float,
    sell_price: float,
    energy_kwh: float,
    degradation_cost_per_cycle: float,
    battery_capacity_kwh: float,
    efficiency: float = 0.9
) -> float:
    """Calculate net profit from buy-low-sell-high arbitrage."""
    
    # Revenue from selling
    revenue = sell_price * energy_kwh * efficiency
    
    # Cost of buying
    cost = buy_price * energy_kwh
    
    # Degradation cost (prorated by cycle fraction)
    cycle_fraction = energy_kwh / battery_capacity_kwh
    degradation = degradation_cost_per_cycle * cycle_fraction
    
    # Net profit
    net_profit = revenue - cost - degradation
    return net_profit

def is_arbitrage_profitable(
    self,
    buy_price: float,
    sell_price: float,
    energy_kwh: float,
    degradation_cost_per_cycle: float,
    battery_capacity_kwh: float,
    min_profit_threshold: float = 0.10,  # Minimum 10 öre profit
) -> bool:
    """Check if arbitrage opportunity is profitable."""
    
    profit = self.calculate_arbitrage_profit(
        buy_price,
        sell_price,
        energy_kwh,
        degradation_cost_per_cycle,
        battery_capacity_kwh
    )
    
    return profit >= min_profit_threshold
```

#### 3.2 Update `planner.py`
Add profitability checks:
```python
def simple_plan(
    # ... existing parameters ...
    min_arbitrage_profit: float = 0.10,  # NEW: Minimum 10 öre/kWh profit
) -> List[PlanAction]:
    
    # ... existing code ...
    
    # Before charging decision
    if should_charge:
        # NEW: Check if charging is profitable
        # Find next likely discharge opportunity
        next_discharge_price = self._find_next_high_price(
            t, price_map, cost_strategy, horizon_hours=12
        )
        
        if next_discharge_price:
            is_profitable = cost_strategy.is_arbitrage_profitable(
                buy_price=price.enriched_sek_per_kwh,
                sell_price=next_discharge_price,
                energy_kwh=batt_max_charge_w / 1000.0,
                degradation_cost_per_cycle=battery_degradation_per_cycle,
                battery_capacity_kwh=batt_capacity_kwh,
                min_profit_threshold=min_arbitrage_profit
            )
            
            if not is_profitable and current_batt_soc > reserve_soc:
                should_charge = False
                action.notes = f"Skip charge (insufficient arbitrage profit)"

def _find_next_high_price(
    self,
    current_time: datetime,
    price_map: dict,
    cost_strategy: CostStrategy,
    horizon_hours: int
) -> Optional[float]:
    """Find the next high price within horizon for arbitrage calculation."""
    for hour in range(1, horizon_hours + 1):
        future_time = current_time + timedelta(hours=hour)
        future_price = price_map.get(future_time)
        if future_price:
            level = cost_strategy.classify_price(future_price.enriched_sek_per_kwh)
            if level == CostLevel.HIGH:
                return future_price.enriched_sek_per_kwh
    return None
```

#### 3.3 Add Configuration
Add to `const.py` and `config_flow.py`:
```python
# const.py
CONF_MIN_ARBITRAGE_PROFIT_SEK_PER_KWH = "min_arbitrage_profit_sek_per_kwh"

# config_flow.py DEFAULT_OPTIONS
CONF_MIN_ARBITRAGE_PROFIT_SEK_PER_KWH: 0.10,  # 10 öre minimum profit
```

#### 3.4 Add Tests
Create `tests/test_cost_benefit_analysis.py`:
```python
def test_arbitrage_profit_calculation():
    """Test net profit calculation including degradation."""
    # ... test implementation

def test_unprofitable_arbitrage_skipped():
    """Test that small price differences don't trigger charging."""
    # ... test implementation

def test_profitable_arbitrage_executed():
    """Test that large price differences trigger charging."""
    # ... test implementation
```

### Copy-Paste PR Instructions for PR #3

```
@copilot Please implement PR #3 from docs/OPTIMIZATION_INTEGRATION_ROADMAP.md

Title: Add cost-benefit analysis to optimization planning

Changes:
1. Add calculate_arbitrage_profit() method to cost_strategy.py
2. Add is_arbitrage_profitable() method to cost_strategy.py
3. Add min_arbitrage_profit parameter to simple_plan() in planner.py
4. Add _find_next_high_price() helper method to planner.py
5. Add profitability check before charging decisions in planner.py
6. Add CONF_MIN_ARBITRAGE_PROFIT_SEK_PER_KWH to const.py
7. Add configuration option to config_flow.py (default 0.10 SEK/kWh)
8. Add translations for new option (EN/SV)
9. Create tests/test_cost_benefit_analysis.py with 3 test cases
10. Update OPTIMIZATION_RULES_AND_DECISIONS.md to document cost-benefit analysis

Use 90% efficiency factor and consider degradation cost prorated by cycle fraction.
```

### Success Criteria
- ✅ Unprofitable arbitrage opportunities skipped
- ✅ Battery degradation factored into decisions
- ✅ Configurable profit threshold
- ✅ Tests validate cost-benefit logic
- ✅ All existing tests still pass

### Expected Benefits
- Fewer unnecessary charge/discharge cycles
- Extended battery lifespan
- Only profitable arbitrage executed
- Configurable profitability threshold

---

## PR #4: Weather-Aware Planning

### Goal
Integrate weather-adjusted solar forecast into battery reserve calculation to account for reduced solar production during cloudy periods.

### Current Gap
- Weather optimization exists but not connected to planning
- Weather-adjusted solar forecast calculated separately
- Reserve calculation doesn't use weather adjustments
- No adaptation to weather conditions

### Changes Required

#### 4.1 Update `coordinator.py`
Pass weather adjustment to reserve calculation:
```python
# After weather optimization calculation
weather_adjustment = None
if self._get_cfg(CONF_ENABLE_WEATHER_OPTIMIZATION, True):
    weather_data = self.data.get("weather_adjusted_solar", {})
    if weather_data:
        weather_adjustment = {
            "reduction_percentage": weather_data.get("reduction_percentage", 0.0),
            "confidence_level": weather_data.get("confidence_level", "unknown"),
            "limiting_factor": weather_data.get("limiting_factor", "unknown")
        }

# Use in reserve calculation
reserve_soc = self._cost_strategy.calculate_battery_reserve(
    hourly_prices,
    now,
    batt_cap_kwh,
    current_soc,
    24,
    weather_adjustment=weather_adjustment,  # Already exists, ensure it's passed
    solar_forecast=solar_points,
)
```

#### 4.2 Update `cost_strategy.py`
Ensure weather adjustment is properly used (already exists but verify):
```python
# In calculate_battery_reserve()
# Weather-aware adjustment: increase reserve if solar forecast is reduced
if weather_adjustment:
    reduction_pct = weather_adjustment.get("reduction_percentage", 0.0)
    
    # If solar forecast is significantly reduced (>20%), increase reserve
    if reduction_pct > 20.0:
        if reduction_pct > 60:
            increase_factor = 1.20
        elif reduction_pct > 40:
            increase_factor = 1.15
        else:
            increase_factor = 1.10
        
        required_soc = required_soc * increase_factor
        
        _LOGGER.debug(
            "Weather-aware adjustment: solar forecast reduced by %.1f%%, "
            "increasing battery reserve by %.0f%%",
            reduction_pct,
            (increase_factor - 1.0) * 100,
        )
```

#### 4.3 Add Tests
Create `tests/test_weather_integration.py`:
```python
def test_reserve_increased_with_cloudy_weather():
    """Test that reserve increases when weather reduces solar forecast."""
    # ... test implementation

def test_weather_adjustment_at_different_levels():
    """Test reserve increase at 20%, 40%, and 60% reduction levels."""
    # ... test implementation

def test_weather_integration_disabled():
    """Test that weather adjustment not applied when optimization disabled."""
    # ... test implementation
```

### Copy-Paste PR Instructions for PR #4

```
@copilot Please implement PR #4 from docs/OPTIMIZATION_INTEGRATION_ROADMAP.md

Title: Integrate weather-aware adjustments into optimization planning

Changes:
1. Ensure weather_adjustment is passed to calculate_battery_reserve() in coordinator.py
2. Verify weather adjustment logic in cost_strategy.py is working correctly
3. Add logging for weather adjustments in coordinator.py
4. Create tests/test_weather_integration.py with 3 test cases
5. Update OPTIMIZATION_RULES_AND_DECISIONS.md to document weather integration

Weather adjustment already exists in code but verify integration path is complete.
```

### Success Criteria
- ✅ Battery reserve increases when weather forecast shows clouds
- ✅ Reserve adjustment scaled by severity (10-20% increase)
- ✅ Weather optimization can be disabled
- ✅ Tests validate weather integration
- ✅ All existing tests still pass

### Expected Benefits
- Better reserve during cloudy weather
- Adapts to weather conditions
- Reduces risk of running out during high-cost hours
- More reliable optimization

---

## Summary Table

| PR # | Title | Key Benefit | Complexity | Risk |
|------|-------|-------------|------------|------|
| #1 | Export Mode Integration | Export revenue in 24h plan | Medium | Low |
| #2 | Solar Forecast Integration | Lower reserve, less grid charging | Medium | Low |
| #3 | Cost-Benefit Analysis | Avoid unprofitable cycles | Low | Very Low |
| #4 | Weather-Aware Planning | Better cloudy-day reserve | Low | Very Low |

**Recommended Order**: PR #1 → PR #3 → PR #2 → PR #4

**Why This Order?**
1. PR #1 provides immediate user value (export planning)
2. PR #3 is low-risk and improves efficiency
3. PR #2 builds on foundation from PR #1 and #3
4. PR #4 is final refinement with minimal changes

---

## Testing Strategy

### For Each PR

1. **Unit Tests**: Test new functions in isolation
2. **Integration Tests**: Test with real Nordpool data
3. **Regression Tests**: Ensure existing tests still pass
4. **Manual Testing**: Verify optimization plan attributes

### Combined Testing (After All PRs)

Create `tests/test_unified_optimization.py`:
```python
def test_all_features_together():
    """Test optimization with all features enabled."""
    # - Export mode: peak_price_opportunistic
    # - Solar forecast: Active
    # - Cost-benefit: Enabled
    # - Weather: Cloudy forecast
    # Verify plan is optimal and all features work together

def test_feature_independence():
    """Test that disabling any feature doesn't break others."""
    # Test all combinations of enabled/disabled features

def test_contract_specific_optimization():
    """Test optimization for E.ON SE4 contract."""
    # Use actual contract parameters
    # Verify profitability calculations
    # Check export decisions
```

---

## Validation Checklist

After all PRs are implemented, verify:

- [ ] Export mode affects optimization plan
- [ ] Export decisions respect battery reserve
- [ ] Solar forecast reduces reserve requirements
- [ ] Grid charging skipped when solar coming
- [ ] Unprofitable arbitrage opportunities skipped
- [ ] Battery degradation factored into decisions
- [ ] Weather forecast increases reserve when needed
- [ ] All 4 new test suites pass
- [ ] All existing tests pass
- [ ] Documentation updated
- [ ] Performance acceptable (< 1s for plan generation)
- [ ] Configuration options exposed in UI
- [ ] Translations complete (EN/SV)

---

## Rollback Plan

If issues arise with any PR:

1. **Immediate**: Disable problematic feature via configuration
2. **Short-term**: Revert PR and investigate
3. **Long-term**: Fix issue and re-deploy

Each PR should include a config option to disable the new feature:
- PR #1: `export_mode = "never"` (already exists)
- PR #2: `use_solar_forecast_in_planning = False` (new)
- PR #3: `enable_cost_benefit_analysis = False` (new)
- PR #4: `enable_weather_optimization = False` (already exists)

---

## Documentation Updates

After all PRs, update:

1. **OPTIMIZATION_RULES_AND_DECISIONS.md**:
   - Remove all items from "What is NOT implemented" section
   - Add new rules to decision logic sections
   - Update examples with unified optimization

2. **OPTIMIZATION_FIX_SUMMARY.md**:
   - Add "Integration Complete" section
   - Update metrics with new capabilities

3. **README** (if exists):
   - Update feature list
   - Add unified optimization description

4. **config_precision.md**:
   - Document new configuration options
   - Add recommended settings

---

## Expected Timeline

With incremental PRs:
- PR #1: 2-4 hours implementation + 1-2 hours testing
- PR #2: 2-3 hours implementation + 1-2 hours testing
- PR #3: 1-2 hours implementation + 1 hour testing
- PR #4: 1 hour implementation + 1 hour testing
- Combined testing: 2 hours
- Documentation: 2 hours

**Total**: 10-15 hours spread across 4 PRs

---

## Success Metrics

After complete integration, measure:

1. **Efficiency**: Should remain ≥75% or improve
2. **Coverage**: % of hours with optimal actions
3. **Profitability**: Net savings vs baseline
4. **Reliability**: Test pass rate and error frequency
5. **Performance**: Plan generation time
6. **User satisfaction**: Feedback and adoption rate

---

## Next Steps

1. **Review this roadmap** with team/users
2. **Approve approach** (incremental vs all-at-once)
3. **Start with PR #1** using copy-paste instructions above
4. **Iterate through PRs** in recommended order
5. **Perform combined testing** after all PRs
6. **Update documentation** with final state
7. **Collect user feedback** on integrated system

---

**Document Status**: Complete implementation roadmap  
**Ready for**: Implementation via copy-paste PR instructions  
**Maintenance**: Update after each PR completion
