# Optimization Rules and Decision Logic

**Date**: 2025-10-15  
**Status**: Current Implementation Documentation  
**Target Audience**: Users and Developers

---

## Executive Summary

This document explains **exactly how the Energy Dispatcher makes optimization decisions** for battery charging/discharging and EV charging. Understanding these rules helps you:

1. **Save money** by knowing when the system charges/discharges
2. **Refine settings** to match your electricity contract and preferences
3. **Identify gaps** in the current implementation that could be improved

---

## 🎯 Current Implementation Status

### ✅ What IS Implemented in Optimization Plan

The optimization plan (`simple_plan` in `planner.py`) currently considers:

1. **Dynamic Cost Thresholds** (NEW - enabled by default)
   - Automatically calculates cheap/high price thresholds from price distribution
   - Uses 25th percentile for "cheap" threshold
   - Uses 75th percentile for "high" threshold
   - Can be disabled to use static thresholds (1.5/3.0 SEK/kWh)

2. **Battery Charging Decisions**
   - Charges during CHEAP hours when SOC < 95%
   - Charges when below reserve and price is not HIGH
   - Charges when excess solar available (>500W)

3. **Battery Discharging Decisions**
   - Discharges during HIGH price hours when SOC > reserve + 5%
   - Discharges when solar deficit and SOC > reserve + 10%

4. **Battery Reserve Calculation**
   - Calculates reserve based on predicted high-cost hours
   - Assumes 1 kW average load (reduced from 2 kW for better optimization)
   - Caps reserve at 60% (reduced from 80% for more aggressive optimization)
   - Formula: `reserve = (high_cost_hours × 1 kW) / battery_capacity_kwh × 100%`

5. **EV Charging Optimization**
   - ECO mode: Charges during cheapest hours within 24h window
   - DEADLINE mode: Charges during cheapest hours before deadline
   - ASAP mode: Charges immediately

### ⚠️ What is NOT Implemented in Optimization Plan

The optimization plan currently does **NOT** consider:

1. **Export Mode** - Export settings are NOT used in planning
2. **Export Opportunities** - No discharge-to-export decisions
3. **Purchase Price vs Export Price** - No arbitrage calculations in planning
4. **Battery Degradation Costs** - Not factored into charge/discharge decisions
5. **Solar Forecast** - Solar values are read but not actively used for optimization
6. **Weather Adjustments** - Weather-aware battery reserve exists but not used in planning

### 🔍 Export Analysis (Separate Module)

Export decisions are handled separately by `ExportAnalyzer` (not integrated into optimization plan):

**Export Modes**:
1. **never** (default) - No export, ever
2. **excess_solar_only** - Export only when battery full (≥95%) and solar excess >1000W
3. **peak_price_opportunistic** - Export during exceptional prices (>5 SEK/kWh) with SOC >80%

**Export Analysis Rules** (when mode is not "never"):
- Export price must be ≥2.0 SEK/kWh minimum
- Battery degradation cost (default: 0.50 SEK/cycle) is considered
- Opportunity cost calculated if high-cost hours are upcoming
- Net revenue must be positive to export

**Current Gap**: Export analyzer exists but is **not called by the optimization planner**. It's used separately for real-time export decisions but doesn't influence the 24-hour optimization plan.

---

## 📊 Your Electricity Contract (E.ON Sweden SE4)

Based on your bill, here's your price structure:

### Purchase Price (Buying Electricity)

**Components** (per kWh):
1. Spot price: Variable (e.g., 0.4153 SEK/kWh from bill)
2. Grid transfer: 0.2456 SEK/kWh (24.56 öre)
3. Energy tax: 0.4390 SEK/kWh (43.90 öre)
4. Variable costs: 0.0442 SEK/kWh (4.42 öre)
5. Fixed surcharge: 0.0600 SEK/kWh (6.00 öre)
6. VAT: 25% on above subtotal

**Formula**:
```
purchase_price = (spot + 0.2456 + 0.4390 + 0.0442 + 0.0600) × 1.25
                = (spot + 0.7888) × 1.25
                = spot × 1.25 + 0.986 SEK/kWh
```

**Example** (spot = 0.4153 SEK/kWh):
- Subtotal: 0.4153 + 0.7888 = 1.2041 SEK/kWh
- With VAT: 1.2041 × 1.25 = 1.505 SEK/kWh ✓ (matches your 51.95 öre avg/kWh when accounting for monthly fees)

### Export Price (Selling Electricity)

**Components** (per kWh) in 2025:
1. Grid utility (nätnytta): 0.067 SEK/kWh (6.70 öre) - deducted as negative
2. Energy purchase: spot + 0.02 SEK/kWh (48.19 öre includes 2 öre påslag)
3. Tax return (2025 only): 0.60 SEK/kWh

**Formula 2025**:
```
export_price_2025 = spot + 0.067 + 0.02 + 0.60
                  = spot + 0.687 SEK/kWh
```

**Formula 2026+** (tax return expires):
```
export_price_2026 = spot + 0.067 + 0.02
                  = spot + 0.087 SEK/kWh
```

**Example** (spot = 0.4153 SEK/kWh):
- 2025 export: 0.4153 + 0.687 = 1.102 SEK/kWh
- 2026 export: 0.4153 + 0.087 = 0.502 SEK/kWh

**No VAT on exported energy** (0% moms)

### Profitability Analysis

For exporting to be profitable, **export price must exceed purchase price**:

**2025** (with tax return):
```
export_profitable = (spot + 0.687) > (spot × 1.25 + 0.986)
                  = 0.687 > spot × 0.25 + 0.986
                  = spot < (0.687 - 0.986) / 0.25
                  = spot < -1.196 (NEVER!)
```
❌ **Export is NEVER profitable in 2025** when considering full purchase price!

However, if you consider only the **marginal cost** (avoiding the spot price part):
```
export_profit_2025 = (spot + 0.687) - (0.2456 + 0.4390 + 0.0442 + 0.0600) × 1.25
                   = spot + 0.687 - 0.936
                   = spot - 0.249
```
✅ **Marginally profitable when spot > 0.249 SEK/kWh** (but ignores battery degradation)

**2026** (without tax return):
```
export_profit_2026 = (spot + 0.087) - (0.936)
                   = spot - 0.849
```
✅ **Marginally profitable when spot > 0.849 SEK/kWh** (rare in SE4)

**Battery Degradation Impact**:
- Battery cycle cost: ~0.50 SEK per full cycle (configurable)
- For 10 kWh battery: 0.05 SEK/kWh degradation cost
- Reduces profitability threshold further

---

## 🔧 Optimization Decision Rules (Current Implementation)

### Rule 1: Price Classification

**When**: Every hour  
**What**: Classify current hour's price into CHEAP, MEDIUM, or HIGH

**Dynamic Thresholds** (enabled by default):
```python
cheap_threshold = P25 of all prices in horizon  # 25th percentile
high_threshold = P75 of all prices in horizon   # 75th percentile

if price <= cheap_threshold:
    level = CHEAP
elif price >= high_threshold:
    level = HIGH
else:
    level = MEDIUM
```

**Static Thresholds** (when dynamic disabled):
```python
cheap_threshold = 1.5 SEK/kWh  # configurable
high_threshold = 3.0 SEK/kWh   # configurable
```

### Rule 2: Battery Reserve Calculation

**When**: At start of optimization planning  
**What**: Calculate minimum SOC to maintain for high-cost hours

**Algorithm**:
```python
# Step 1: Find high-cost windows
high_cost_windows = find_windows_where_price >= high_threshold

# Step 2: Calculate total high-cost duration
total_hours = sum(window_durations)

# Step 3: Estimate energy need
estimated_load = 1.0 kW  # conservative average
required_energy = total_hours × estimated_load

# Step 4: Convert to SOC percentage
required_soc = (required_energy / battery_capacity) × 100

# Step 5: Apply cap
reserve_soc = min(60%, required_soc)
```

**Example** (4 hours high-cost, 10 kWh battery):
```
required_energy = 4 hours × 1 kW = 4 kWh
required_soc = (4 / 10) × 100 = 40%
reserve_soc = min(60%, 40%) = 40%
```

### Rule 3: Battery Charging Decision

**When**: Every hour in planning horizon  
**What**: Decide if battery should charge

**Conditions for Charging**:
```python
should_charge = (
    # Condition 1: Always charge from excess solar (free energy)
    (solar_available_w > 500) OR
    
    # Condition 2: Charge if below reserve and price not HIGH
    (current_soc < reserve_soc AND price_level != HIGH) OR
    
    # Condition 3: Charge if price is CHEAP and not full
    (price_level == CHEAP AND current_soc < 95%)
)

# Additional constraint
if should_charge AND current_soc < 95%:
    action = CHARGE
```

**Charge Power**: Uses configured `batt_max_charge_w` (typically 10,000W)

### Rule 4: Battery Discharging Decision

**When**: Every hour in planning horizon  
**What**: Decide if battery should discharge

**Conditions for Discharging**:
```python
# Never discharge if below reserve
if current_soc <= reserve_soc:
    should_discharge = False

# Discharge if price is HIGH and buffer above reserve
elif price_level == HIGH AND current_soc > reserve_soc + 5%:
    should_discharge = True

# Discharge if solar deficit and spare capacity
elif solar_deficit_w < -1000 AND current_soc > reserve_soc + 10%:
    should_discharge = True

else:
    should_discharge = False
```

**Discharge Power**: Uses configured `batt_max_disch_w` (typically 10,000W)

### Rule 5: SOC Simulation

**When**: After each charge/discharge decision  
**What**: Update estimated SOC for next hour

**Algorithm**:
```python
if charging:
    charge_kwh = batt_max_charge_w / 1000.0  # Convert W to kW
    soc_increase = (charge_kwh / batt_capacity_kwh) × 100
    current_soc = min(100%, current_soc + soc_increase)

if discharging:
    discharge_kwh = batt_max_disch_w / 1000.0
    soc_decrease = (discharge_kwh / batt_capacity_kwh) × 100
    current_soc = max(0%, current_soc - soc_decrease)
```

**Note**: This is a simplified simulation. Actual SOC changes depend on house load, solar production, and battery efficiency.

### Rule 6: EV Charging Decision

**When**: At start of optimization planning  
**What**: Select optimal hours for EV charging

**Algorithms by Mode**:

**ECO Mode** (default):
```python
# Step 1: Calculate hours needed
hours_needed = ev_need_kwh / charging_power_kw

# Step 2: Get prices within 24h window
available_prices = prices[now : now + 24h]

# Step 3: Sort by price (cheapest first)
sorted_prices = sort(available_prices, key=price)

# Step 4: Select cheapest hours
selected_hours = sorted_prices[:hours_needed]
```

**DEADLINE Mode**:
```python
# Step 1: Calculate hours needed
hours_needed = ev_need_kwh / charging_power_kw

# Step 2: Get prices until deadline
available_prices = prices[now : deadline]

# Step 3: Sort by price and select cheapest
selected_hours = cheapest_n_hours(available_prices, hours_needed)
```

**ASAP Mode**:
```python
# Charge continuously from now until charged
selected_hours = [now, now+1h, now+2h, ..., now+hours_needed]
```

---

## 🚫 What the Optimization Does NOT Consider

### 1. Export Mode Setting

**Current Status**: `export_mode` configuration exists but is **NOT used in optimization planning**.

**What This Means**:
- If you set `export_mode` to "excess_solar_only" or "peak_price_opportunistic", the optimization plan will NOT include any export/discharge decisions based on export profitability
- Export decisions happen separately in real-time via `ExportAnalyzer`
- The 24-hour optimization plan only considers battery discharge for avoiding import costs, not for export revenue

**Gap**: Optimization should consider export opportunities when planning battery discharge, especially in your case where:
- Export price (2025): spot + 0.687 SEK/kWh
- Marginal export profit: spot - 0.249 SEK/kWh
- Could be profitable during high spot price hours (>0.25 SEK/kWh)

### 2. Purchase vs Export Price Comparison

**Current Status**: Planner only uses purchase price for decisions, never compares to export price.

**What This Means**:
- Battery discharge decisions are based solely on avoiding purchase costs
- No consideration of "buy low, sell high" arbitrage opportunities
- No optimization for: charge when purchase < export threshold, discharge when export > purchase + costs

**Gap**: For your contract, optimal strategy should be:
```python
if export_price > purchase_price + battery_degradation + margin:
    # Could be profitable to discharge to export
    # But only if no high-cost hours upcoming (opportunity cost)
    should_consider_export = True
```

### 3. Solar Forecast Integration

**Current Status**: Solar watts are read but not used for planning decisions.

**What This Means**:
- No anticipation of solar production in planning
- No "charge before solar arrives" or "save battery, solar coming" logic
- Solar only considered as instantaneous value for "charge from excess solar" rule

**Gap**: Optimization should use solar forecast to:
- Reduce reserve requirement if solar expected during high-cost hours
- Avoid charging from grid if solar coming soon
- Plan to charge battery before cloudy periods

### 4. Weather-Aware Reserve

**Current Status**: Weather-adjusted reserve exists in `cost_strategy.py` but is **NOT passed to reserve calculation**.

**What This Means**:
- If weather forecast shows clouds, reserve should increase
- Currently not implemented in the optimization flow
- Weather optimization exists as a separate feature

### 5. Battery Degradation Costs

**Current Status**: Degradation cost configured (default 0.50 SEK/cycle) but **NOT used in planning**.

**What This Means**:
- No cost-benefit analysis for charge/discharge cycles
- No "skip small arbitrage opportunities if degradation cost exceeds benefit"
- Degradation only considered in `ExportAnalyzer`, not in optimization plan

**Gap**: Should add degradation cost to decision logic:
```python
charge_benefit = price_high - price_cheap
discharge_cost = battery_degradation_per_kwh

if charge_benefit > discharge_cost + margin:
    perform_arbitrage = True
```

---

## 💡 Improvement Suggestions

### Priority 1: Integrate Export Mode into Optimization

**What**: Make optimization plan aware of export mode and opportunities

**How**:
1. Pass `export_mode` to `simple_plan()` function
2. Add export price calculation to price points
3. Modify discharge rule to consider export profitability:
```python
if export_mode != "never":
    export_price = calculate_export_price(spot_price)
    purchase_price = calculate_purchase_price(spot_price)
    
    if export_price > purchase_price + battery_degradation:
        # Profitable to export
        # But check if reserve needed for upcoming high costs
        if current_soc > reserve_soc + safe_margin:
            should_discharge_to_export = True
```

### Priority 2: Add Purchase vs Export Price Comparison

**What**: Include full price comparison in optimization decisions

**How**:
1. Calculate both purchase and export prices for each hour
2. Add "enriched_export_price" to PricePoint model
3. Use price differential in discharge decisions:
```python
if export_price > purchase_price × threshold_factor:
    # Significant arbitrage opportunity
    consider_export = True
```

### Priority 3: Integrate Solar Forecast

**What**: Use solar forecast to improve planning

**How**:
1. Pass solar forecast to reserve calculation
2. Reduce reserve if solar expected during high-cost hours:
```python
if solar_forecast_during_high_cost > threshold:
    reserve_soc = reserve_soc × reduction_factor
```
3. Add "wait for solar" logic to charging decisions:
```python
if solar_coming_within_1h > house_load:
    skip_grid_charge = True
```

### Priority 4: Add Degradation Cost Analysis

**What**: Factor battery degradation into charge/discharge decisions

**How**:
1. Pass degradation cost to planner
2. Calculate cost/benefit for each charge/discharge:
```python
arbitrage_profit = (price_high - price_low) × energy_kwh
degradation_cost = battery_degradation_per_kwh × energy_kwh

if arbitrage_profit > degradation_cost × safety_margin:
    perform_cycle = True
```

### Priority 5: Weather-Aware Reserve

**What**: Adjust battery reserve based on weather forecast

**How**:
1. Pass weather adjustment to planner
2. Increase reserve when solar forecast reduced:
```python
if weather_reduces_solar_by > 20%:
    reserve_soc = reserve_soc × (1 + reduction_factor)
```

### Priority 6: Export Price Configuration

**What**: Allow users to configure export price formula

**How**:
Add configuration options:
- `export_grid_utility_sek_per_kwh`: Default 0.067 (nätnytta)
- `export_energy_surcharge_sek_per_kwh`: Default 0.02 (påslag)
- `export_tax_return_sek_per_kwh`: Default 0.60 (2025), 0.00 (2026+)
- `export_formula`: "spot + grid_utility + surcharge + tax_return"

---

## 📈 Expected Improvements for Your Setup

### Current Behavior (Default Settings)

With dynamic thresholds and your typical SE4 prices (0.40-2.00 SEK/kWh):

1. **Cheap threshold**: ~0.80 SEK/kWh (P25)
2. **High threshold**: ~1.40 SEK/kWh (P75)
3. **Charges**: During hours with spot <0.80
4. **Discharges**: During hours with spot >1.40
5. **Ignores**: Export opportunities (mode = "never")

### With Export Integration (Proposed)

If export mode = "excess_solar_only":

1. Same charge/discharge as above for import avoidance
2. **Plus**: Discharge to export when:
   - Battery full (≥95%) AND solar excess >1000W
   - Export price = spot + 0.687 (2025)
   - Always profitable since avoiding waste

If export mode = "peak_price_opportunistic":

1. Same as above
2. **Plus**: Discharge to export when:
   - Spot > 0.85 SEK/kWh (export marginally profitable)
   - Battery SOC > reserve + 10% (safe buffer)
   - No high-cost hours upcoming (no opportunity cost)
   - Net revenue > battery degradation cost

**Example Scenario**:
- Spot price: 1.50 SEK/kWh (high)
- Export price: 1.50 + 0.687 = 2.187 SEK/kWh
- Purchase price: 1.50 × 1.25 + 0.986 = 2.861 SEK/kWh
- Marginal export: 2.187 - 0.936 = 1.251 SEK/kWh
- Arbitrage opportunity: Save 2.861 by not importing OR earn 1.251 by exporting

**Potential Savings**:
- Current: Saves 2.861 SEK/kWh by discharging (avoiding import)
- With export: Could earn additional revenue during battery-full + solar-excess periods
- Estimated: 5-10% improvement in annual savings for your setup

---

## 🎓 Understanding the Tradeoffs

### Why Export is Cautious by Default

**Reason 1: Export Price Usually Lower Than Purchase**
- Your 2025 export: spot + 0.687 SEK/kWh
- Your 2025 purchase: spot × 1.25 + 0.986 SEK/kWh
- Difference: Purchase is ~0.3-0.5 SEK/kWh higher
- **Conclusion**: Usually better to avoid buying than to sell

**Reason 2: Battery Degradation**
- Each charge/discharge cycle costs ~0.05 SEK/kWh
- Small arbitrage profits eaten by degradation
- Only worth exporting for significant price differences

**Reason 3: Opportunity Cost**
- Discharging battery for export means less available for later
- If high-cost period coming, stored energy is valuable
- Export only makes sense when battery full or no upcoming needs

**Reason 4: 2026 Cliff**
- Export becomes much less attractive after 2025
- Tax return expires: export drops from spot+0.687 to spot+0.087
- Integration should account for this change

### Why Reserve Calculation is Conservative

**Reason 1: Uncertainty in Load**
- Actual house load varies: 0.5-3 kW typical
- Assume 1 kW average as reasonable middle ground
- Too low → risk running out during expensive hours
- Too high → miss cheap charging opportunities

**Reason 2: Solar Uncertainty**
- Solar forecast may be wrong (weather changes)
- Without weather integration, assume worst case
- Better to have too much than too little

**Reason 3: Price Volatility**
- Prices can spike unexpectedly
- Reserve provides buffer for unplanned events
- 60% cap balances safety and optimization

---

## 🔍 How to Monitor and Tune

### Check Your Optimization Plan

1. Go to **Developer Tools → States**
2. Find `sensor.energy_dispatcher_optimization_plan`
3. View attributes:
   - `actions`: List of hourly decisions
   - `charge_hours`: Number of charge hours
   - `discharge_hours`: Number of discharge hours
   - `description`: Summary

### Monitor Cost Levels

1. Check `sensor.energy_dispatcher_cost_level`
2. Values: "cheap", "medium", "high"
3. Corresponds to current hour's classification

### Review Battery Reserve

1. Check coordinator data for `battery_reserve_recommendation`
2. Shows calculated reserve SOC percentage
3. High reserve = many expensive hours expected

### Analyze Actual Performance

1. Track actual vs planned:
   - Did battery charge when plan said to charge?
   - Did battery discharge when plan said to discharge?
   - What was actual SOC vs predicted SOC?
2. Compare costs:
   - Hours charged × charge price = charge cost
   - Hours discharged × discharge price = savings
   - Net savings = savings - charge cost - degradation

### Tune Configuration

**If you see charging during expensive hours**:
- Check if dynamic thresholds are enabled
- Verify Nordpool sensor is working
- Check if reserve calculation is too high

**If you see idle during cheap hours**:
- Battery may be full
- Reserve may be met
- Check SOC level during those hours

**If you see no discharge during expensive hours**:
- Check if SOC is above reserve + 5%
- Verify price meets high threshold
- Check if export mode is affecting decisions

---

## 📝 Summary

**Current Optimization Plan**:
- ✅ Uses dynamic cost thresholds (improved accuracy)
- ✅ Charges during cheap hours
- ✅ Discharges during high hours (import avoidance only)
- ✅ Maintains battery reserve for expensive periods
- ✅ Optimizes EV charging timing
- ⚠️ Does NOT consider export mode
- ⚠️ Does NOT compare purchase vs export prices
- ⚠️ Does NOT use solar forecast for planning
- ⚠️ Does NOT factor in battery degradation costs

**Your E.ON SE4 Contract**:
- Purchase: spot × 1.25 + 0.986 SEK/kWh
- Export 2025: spot + 0.687 SEK/kWh
- Export 2026+: spot + 0.087 SEK/kWh
- Export marginally profitable at spot >0.25 SEK/kWh (2025)

**Recommendations**:
1. Keep dynamic thresholds enabled (default)
2. Use "excess_solar_only" export mode for your setup
3. Monitor optimization plan attributes to understand decisions
4. Consider export integration improvements (Priority 1-2 above)
5. Plan for 2026 when export becomes less attractive

**Questions or Issues?**:
- Check `docs/troubleshooting_optimization_plan.md`
- Review `docs/cost_strategy_and_battery_optimization.md` for technical details
- Open GitHub issue for feature requests or bugs

---

**Document Status**: Complete and accurate as of 2025-10-15  
**Next Update**: After export integration implementation
