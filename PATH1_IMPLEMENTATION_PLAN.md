# Path 1 Implementation Plan - Energy Dispatcher

**Date**: 2025-10-13  
**Current Version**: v0.8.30  
**Target Version**: v0.9.0 (deferred)

---

## 🎯 REVISED SCOPE (Updated 2025-10-13)

**Decision**: Focus on objectives 1-3 only. Defer objectives 4-5 pending live testing.

### What We're Doing Now:
1. ✅ **Documentation organization** (already complete)
2. ⏳ **Test infrastructure setup** (pytest.ini, CI/CD, requirements-test.txt)
3. ⏳ **Cost strategy integration** (coordinator, sensors, config UI, translations)

### What We're Deferring:
4. ⏸️ **Phase 1 roadmap items** (charger presets, config bundles, import/export)
5. ⏸️ **v0.9.0 release** (will prepare after live testing)

**Why**: Need to test cost strategy integration in production first. Will find important improvements during live testing before adding more features.

**Timeline**: 1-2 weeks for objectives 2-3

---

## Executive Summary

This document outlines the specific implementation plan for **Path 1: Complete Existing Work** as recommended in the technical evaluation documents. This path focuses on finishing what has been started before adding new features.

### Key Objectives - REVISED SCOPE
1. ✅ **Organize documentation** - Already done (docs in proper folders)
2. ⏳ **Set up test infrastructure** - Create pytest.ini, CI/CD, requirements-test.txt
3. ⏳ **Integrate Cost Strategy** - Wire existing cost_strategy.py into the coordinator
4. ⏸️ **Complete Phase 1 Roadmap** - **ON HOLD** - Add charger profiles, config bundles, import/export
5. ⏸️ **Release v0.9.0** - **ON HOLD** - Clean foundation for Phase 2

**Revised Scope**: Focus on objectives 1-3 only. Objectives 4-5 deferred pending live testing of cost strategy integration.

**Timeline**: 1-2 weeks for objectives 2-3  
**Effort**: Medium  
**Risk**: Low

---

## Current Status Review

### Documentation Organization ✅ COMPLETE

After reviewing the repository, the documentation is **already well-organized**:

```
/docs/
├── changelog/           ✅ Already exists with 23 fix summaries
│   ├── BASELINE_FIX_SUMMARY.md
│   ├── CONFIG_FLOW_FIX_v0.8.*.md
│   ├── BATTERY_COST_*.md
│   └── ... (20 more)
├── technical/           ✅ Already exists with evaluation docs
│   ├── COMPREHENSIVE_EVALUATION.md
│   ├── EVALUATION_README.md
│   ├── EVALUATION_SUMMARY.md
│   ├── RECOMMENDED_NEXT_STEPS.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── MISSING_DATA_HANDLING_SUMMARY.md
│   ├── DIAGNOSTIC_GUIDE.md
│   └── FIX_README.md
├── testing/             ✅ Already exists
│   ├── EXECUTIVE_SUMMARY.md
│   ├── README.md
│   ├── SAMPLE_DATA_NEEDS.md
│   └── TESTING_ANALYSIS.md
└── (25+ user-facing docs) ✅ Well organized
```

**Root directory**: Only contains README.md, CHANGELOG.md, QUICK_START.md, LICENSE ✅

**Conclusion**: Documentation organization is **already excellent** and follows the recommended structure. No action needed.

---

## Step 1: Test Infrastructure Setup

### Current State
- ✅ 92+ tests exist across 13 test files
- ✅ Tests are well-written and comprehensive
- ❌ No pytest.ini configuration
- ❌ No requirements-test.txt
- ❌ No CI/CD workflow (GitHub Actions)
- ❌ No testing documentation in README

### Tasks Required

#### 1.1 Create pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --tb=short -v --asyncio-mode=auto
asyncio_mode = auto
```

#### 1.2 Create requirements-test.txt
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-homeassistant-custom-component>=0.13.0
pytest-cov>=4.1.0
```

#### 1.3 Create .github/workflows/test.yml
```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: pytest tests/ --cov=custom_components/energy_dispatcher --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
```

#### 1.4 Update README.md
Add section on running tests:
```markdown
## Development

### Running Tests

```bash
pip install -r requirements-test.txt
pytest tests/
```

### Running with coverage

```bash
pytest tests/ --cov=custom_components/energy_dispatcher --cov-report=html
```
```

**Effort**: 1-2 hours  
**Impact**: High - Establishes proper testing workflow

---

## Step 2: Cost Strategy Integration Decision

### Current State

**Code Status**:
- ✅ `cost_strategy.py`: 301 lines, fully implemented
- ✅ 21 comprehensive unit tests (all passing)
- ✅ Models defined in `models.py` (CostThresholds, CostLevel, PricePoint)
- ❌ **NOT integrated into coordinator**
- ❌ **NO UI configuration**
- ❌ **NO sensors exposed**

**What Cost Strategy Provides**:
1. Dynamic cost classification (cheap/medium/high) based on thresholds
2. Battery reserve recommendations based on price forecasts
3. High-cost window prediction (when to discharge battery)
4. EV charging optimization (find cheapest hours)
5. Cost summary generation

### Recommendation: ✅ INTEGRATE IT

**Rationale**:
1. **High Value**: Provides intelligent battery management based on price
2. **Low Effort**: Code is already written and tested (2-3 days integration)
3. **User Benefit**: Immediate value - better battery cost optimization
4. **Respects Investment**: 301 lines of quality code shouldn't go to waste

### Integration Tasks

#### 2.1 Coordinator Integration
**File**: `custom_components/energy_dispatcher/coordinator.py`

Add to coordinator __init__:
```python
from .cost_strategy import CostStrategy

# In __init__
self._cost_strategy = CostStrategy()
```

Add to _async_update_data:
```python
# After price data is fetched
if prices and len(prices) > 0:
    # Classify current price
    current_price = prices[0].enriched_sek_per_kwh if prices else 0.0
    cost_level = self._cost_strategy.classify_price(current_price)
    
    # Calculate battery reserve recommendation
    battery_reserve = None
    if self._batt_cap_kwh and current_soc:
        battery_reserve = self._cost_strategy.calculate_battery_reserve(
            prices=prices,
            now=now,
            battery_capacity_kwh=self._batt_cap_kwh,
            current_soc=current_soc
        )
    
    # Predict high-cost windows
    high_cost_windows = self._cost_strategy.predict_high_cost_windows(
        prices=prices,
        now=now,
        horizon_hours=24
    )
    
    # Store in coordinator data
    data["cost_level"] = cost_level.value
    data["battery_reserve_recommendation"] = battery_reserve
    data["high_cost_windows"] = high_cost_windows
```

#### 2.2 Configuration Options
**File**: `custom_components/energy_dispatcher/config_flow.py`

Add constants:
```python
CONF_COST_CHEAP_THRESHOLD = "cost_cheap_threshold"
CONF_COST_HIGH_THRESHOLD = "cost_high_threshold"
CONF_COST_ENABLE = "cost_strategy_enable"
```

Add to schema:
```python
vol.Optional(CONF_COST_ENABLE, default=True): cv.boolean,
vol.Optional(CONF_COST_CHEAP_THRESHOLD, default=1.5): selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.0, max=10.0, step=0.01, unit_of_measurement="SEK/kWh"
    )
),
vol.Optional(CONF_COST_HIGH_THRESHOLD, default=3.0): selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.0, max=10.0, step=0.01, unit_of_measurement="SEK/kWh"
    )
),
```

#### 2.3 New Sensors
**File**: `custom_components/energy_dispatcher/sensor.py`

Add three new sensor classes:

1. **Cost Level Sensor** (cheap/medium/high)
2. **Battery Reserve Recommendation Sensor** (% of capacity)
3. **High Cost Window Sensor** (next high-cost period start time)

#### 2.4 Translations
**Files**: `translations/en.json`, `translations/sv.json`

Add keys for:
- Configuration labels (cost_cheap_threshold, cost_high_threshold)
- Sensor names and descriptions
- State values (cheap, medium, high)

**Effort**: 2-3 days  
**Impact**: High - Major new feature

---

## Step 3: Vehicle Manager Decision

### Current State

**Code Status**:
- ✅ `archive/vehicle_manager.py`: 225 lines
- ✅ 19 comprehensive tests
- ✅ Demo script exists
- ❌ Archived (not imported)
- ❌ Never integrated into UI

**What Vehicle Manager Provides**:
- Multi-vehicle tracking (multiple EVs)
- Per-vehicle charging sessions
- Charger-vehicle associations
- Vehicle presets (Tesla, Hyundai, etc.)

### Recommendation: ❌ REMOVE FOR NOW

**Rationale**:
1. **Low User Demand**: Most users have 1 EV
2. **High Integration Effort**: 3-4 days work
3. **Better to Focus**: Complete other Phase 1 items first
4. **Can Add Later**: If users request it, restore from git history

**Action**: 
- Remove `archive/vehicle_manager.py`
- Remove tests for vehicle manager
- Update documentation to remove multi-vehicle references
- Add note to roadmap: "Multi-vehicle support deferred to Phase 3"

**Effort**: 1 hour  
**Impact**: Low - Clarifies codebase, focuses effort

---

## Step 4: Phase 1 Roadmap Items

### PR-5: Pre-configured Charger Profiles

**Goal**: Provide preset configurations for common EVSE chargers

**Implementation**:

```python
# In config_flow.py
CHARGER_PRESETS = {
    "easee_home": {
        "name": "Easee Home",
        "max_current": 32,
        "min_current": 6,
        "phases": 3,
        "voltage": 230,
        "notes": "3-phase 32A (22 kW max)"
    },
    "wallbox_pulsar_plus": {
        "name": "Wallbox Pulsar Plus",
        "max_current": 32,
        "min_current": 6,
        "phases": 1,
        "voltage": 230,
        "notes": "1-phase 32A (7.4 kW max)"
    },
    "zaptec_go": {
        "name": "Zaptec Go",
        "max_current": 32,
        "min_current": 6,
        "phases": 3,
        "voltage": 230,
        "notes": "3-phase 32A (22 kW max)"
    },
    "generic_16a_3phase": {
        "name": "Generic 16A 3-Phase",
        "max_current": 16,
        "min_current": 6,
        "phases": 3,
        "voltage": 230,
        "notes": "Common EU installation"
    },
    "generic_32a_1phase": {
        "name": "Generic 32A 1-Phase",
        "max_current": 32,
        "min_current": 6,
        "phases": 1,
        "voltage": 230,
        "notes": "Common home charger"
    },
    "custom": {
        "name": "Custom Configuration",
        "max_current": None,  # User must specify
        "min_current": None,
        "phases": None,
        "voltage": None,
    }
}
```

Add a selection step in config flow:
```python
async def async_step_charger_preset(self, user_input=None):
    """Select charger preset or custom."""
    if user_input is not None:
        preset = CHARGER_PRESETS.get(user_input["preset"])
        if preset["max_current"]:
            # Auto-fill configuration
            return self.async_create_entry(...)
        else:
            # Go to custom configuration
            return await self.async_step_charger_custom()
    
    return self.async_show_form(
        step_id="charger_preset",
        data_schema=vol.Schema({
            vol.Required("preset", default="easee_home"): 
                vol.In(list(CHARGER_PRESETS.keys()))
        })
    )
```

**Effort**: 1-2 days  
**Impact**: Medium - Easier setup for common chargers

---

### PR-7: Configuration Bundles

**Goal**: Pre-configured settings for common scenarios

**Implementation**:

```python
CONFIG_BUNDLES = {
    "swedish_villa_15kwh_1ev": {
        "name": "Swedish Villa (15kWh battery, 1 EV)",
        "description": "Standard Swedish villa with solar, battery, and EV",
        "config": {
            "price_tax": 0.395,  # 39.5% VAT in Sweden
            "price_transfer": 0.50,  # Typical grid transfer fee
            "price_surcharge": 0.10,  # Typical surcharge
            "batt_cap_kwh": 15.0,
            "batt_max_charge_power": 5000,
            "batt_max_discharge_power": 5000,
            "ev_battery_capacity_kwh": 77.0,  # Tesla Model Y LR
            "evse_max_a": 16,
            "evse_phases": 3,
            "cost_cheap_threshold": 1.5,
            "cost_high_threshold": 3.0,
        }
    },
    "apartment_small_no_battery": {
        "name": "Apartment (No battery, small EV)",
        "description": "Apartment with solar and EV, no battery",
        "config": {
            "price_tax": 0.395,
            "price_transfer": 0.40,  # Lower apartment fee
            "batt_cap_kwh": 0,  # No battery
            "ev_battery_capacity_kwh": 40.0,  # Nissan Leaf
            "evse_max_a": 16,
            "evse_phases": 1,
        }
    },
    "large_home_30kwh_2ev": {
        "name": "Large Home (30kWh battery, 2 EVs)",
        "description": "Large house with big battery and multiple EVs",
        "config": {
            "price_tax": 0.395,
            "price_transfer": 0.55,  # Higher consumption bracket
            "batt_cap_kwh": 30.0,
            "batt_max_charge_power": 10000,
            "batt_max_discharge_power": 10000,
            "ev_battery_capacity_kwh": 77.0,
            "evse_max_a": 32,
            "evse_phases": 3,
        }
    }
}
```

Add bundle selection at start of config flow:
```python
async def async_step_bundle(self, user_input=None):
    """Select configuration bundle."""
    if user_input is not None:
        if user_input["bundle"] == "custom":
            return await self.async_step_user()
        else:
            bundle = CONFIG_BUNDLES[user_input["bundle"]]
            # Pre-fill with bundle config
            return await self.async_step_user(bundle["config"])
    
    return self.async_show_form(
        step_id="bundle",
        data_schema=vol.Schema({
            vol.Required("bundle", default="custom"): vol.In({
                "swedish_villa_15kwh_1ev": "Swedish Villa (15kWh + EV)",
                "apartment_small_no_battery": "Apartment (No battery + EV)",
                "large_home_30kwh_2ev": "Large Home (30kWh + EVs)",
                "custom": "Custom Configuration"
            })
        }),
        description_placeholders={
            "bundle_desc": "Choose a preset to auto-fill common settings"
        }
    )
```

**Effort**: 1 day  
**Impact**: Medium - Much faster initial setup

---

### PR-9: Configuration Import/Export

**Goal**: Allow users to backup, share, and migrate configurations

**Implementation**:

#### Add service (services.yaml):
```yaml
export_config:
  name: Export Configuration
  description: Export current configuration as JSON
  fields:
    entry_id:
      name: Config Entry ID
      description: The configuration entry to export
      required: true
      selector:
        text:

import_config:
  name: Import Configuration
  description: Import configuration from JSON
  fields:
    config_json:
      name: Configuration JSON
      description: Paste the exported JSON here
      required: true
      selector:
        text:
          multiline: true
```

#### Add service handlers (__init__.py):
```python
async def async_export_config(hass: HomeAssistant, call: ServiceCall):
    """Export configuration as JSON."""
    entry_id = call.data["entry_id"]
    entry = hass.config_entries.async_get_entry(entry_id)
    
    if not entry:
        raise ServiceValidationError("Configuration entry not found")
    
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "data": entry.data,
        "options": entry.options,
    }
    
    # Create persistent notification with JSON
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "Energy Dispatcher Configuration Export",
            "message": f"```json\n{json.dumps(export_data, indent=2)}\n```",
            "notification_id": f"energy_dispatcher_export_{entry_id}"
        }
    )

async def async_import_config(hass: HomeAssistant, call: ServiceCall):
    """Import configuration from JSON."""
    try:
        config_json = call.data["config_json"]
        config_data = json.loads(config_json)
        
        if config_data.get("version") != "1.0":
            raise ServiceValidationError("Unsupported configuration version")
        
        # Create new config entry
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=config_data["data"]
        )
        
    except json.JSONDecodeError:
        raise ServiceValidationError("Invalid JSON format")
```

#### Add to options flow:
Add "Export Configuration" button that calls the export service.

**Effort**: 2 days  
**Impact**: Medium - Useful for backup/migration

---

## Step 5: Release v0.9.0

### Tasks

1. **Update manifest.json**
   - Bump version to 0.9.0
   - Update description

2. **Update CHANGELOG.md**
```markdown
## [0.9.0] - 2025-XX-XX

### Added
- Cost-based battery optimization with configurable thresholds
- Battery reserve recommendations based on price forecasts
- High-cost window prediction
- Pre-configured charger profiles (Easee, Wallbox, Zaptec, Generic)
- Configuration bundles for common scenarios (Swedish Villa, Apartment, Large Home)
- Configuration import/export functionality
- Comprehensive test infrastructure with pytest and CI/CD

### Changed
- Improved test coverage and organization
- Enhanced documentation structure

### Removed
- Archived multi-vehicle manager code (can be restored if needed)

### Fixed
- Various minor bugs and improvements
```

3. **Update README.md**
   - Add "New in v0.9.0" section
   - Update feature list
   - Add CI/CD badges

4. **Documentation Updates**
   - Update configuration.md with new cost strategy options
   - Update getting_started.md with charger presets and bundles
   - Add cost_strategy_guide.md explaining the new feature

5. **Create GitHub Release**
   - Tag: v0.9.0
   - Release notes with changelog
   - Highlight major features

**Effort**: 1-2 days  
**Impact**: High - Milestone completion

---

## Timeline & Milestones - REVISED

### Week 1: Foundation & Setup (Days 1-5)
- [x] Day 1-2: Review and approve this plan
- [ ] Day 2-3: Set up test infrastructure (pytest.ini, CI/CD, requirements)
- [ ] Day 3-4: Make vehicle manager decision and clean up
- [ ] Day 4-5: Start cost strategy integration (coordinator changes)

**Milestone 1**: Test infrastructure complete, codebase cleaned up

### Week 2: Cost Strategy Integration (Days 6-10)
- [ ] Day 6-8: Complete cost strategy integration (coordinator, config flow)
- [ ] Day 9: Add sensors and configuration UI
- [ ] Day 10: Add translations (EN/SV) and test thoroughly

**Milestone 2**: Cost strategy fully integrated and ready for live testing

### DEFERRED - Pending Live Testing Results

The following milestones are deferred until cost strategy has been tested in production:

### ~~Week 3: Phase 1 Roadmap (Days 15-21)~~ **ON HOLD**
- ~~Day 15-16: Implement charger profiles (PR-5)~~
- ~~Day 17: Implement configuration bundles (PR-7)~~
- ~~Day 18-20: Implement import/export (PR-9)~~
- ~~Day 21: Test all Phase 1 features~~

**Reason**: Need live testing feedback on cost strategy before proceeding with additional features.

### ~~Week 4: Release (Days 22-28)~~ **ON HOLD**
- ~~Day 22-24: Documentation updates~~
- ~~Day 25: Final testing and bug fixes~~
- ~~Day 26-27: Prepare release notes and changelog~~
- ~~Day 28: Release v0.9.0~~

**Reason**: v0.9.0 release will be prepared after live testing validates cost strategy integration.

---

## Success Criteria - REVISED SCOPE

### Technical (Objectives 1-3)
- [x] Documentation already organized
- [ ] All 92+ existing tests pass
- [ ] New tests for cost strategy integration (10+ tests)
- [ ] CI/CD pipeline working on GitHub Actions
- [ ] Code coverage >= 70%
- [ ] No breaking changes to existing configurations

### Documentation (Objectives 1-3)
- [ ] Test infrastructure documented in README
- [ ] Cost strategy guide created
- [ ] Configuration docs updated for cost strategy
- [ ] Changelog entry for cost strategy integration

### Features (Objective 3 Only)
- [ ] Cost strategy integrated and working
- [ ] Cost classification (cheap/medium/high) functional
- [ ] Battery reserve recommendations working
- [ ] High-cost window prediction operational
- [ ] All cost strategy features have EN/SV translations
- [ ] Configuration UI for cost thresholds working

### DEFERRED Features (Objectives 4-5)
- ~~5 charger presets available~~ **ON HOLD**
- ~~3 configuration bundles available~~ **ON HOLD**
- ~~Import/export working~~ **ON HOLD**
- ~~v0.9.0 release~~ **ON HOLD**

---

## Risk Mitigation

### Risk 1: Breaking Existing Configurations
**Mitigation**: 
- Thoroughly test with existing config samples
- Make cost strategy optional (can be disabled)
- Version configuration schema
- Add migration logic if needed

### Risk 2: Integration Bugs
**Mitigation**:
- Comprehensive unit and integration tests
- Manual testing before release
- Beta period with early adopters
- Clear rollback plan

### Risk 3: Timeline Overrun
**Mitigation**:
- Focus on core features first
- Defer nice-to-haves if needed
- Prioritize ruthlessly
- Release early, iterate later

---

## Post Cost-Strategy Integration: Next Steps

After cost strategy integration and live testing, the following will be evaluated:

### Phase 1b: Complete Remaining Items (If Cost Strategy Works Well)
1. **PR-5**: Pre-configured charger profiles - 1-2 days
2. **PR-7**: Configuration bundles - 1 day
3. **PR-9**: Configuration import/export - 2 days
4. **Release v0.9.0** - 1-2 days

**Timeline**: 1-2 weeks after successful live testing

### Phase 2: Advanced Discovery (Future)
1. Device auto-discovery (PR-2) - 5-7 days
2. Smart entity detection (PR-8) - 3-4 days
3. Visual dashboard builder (PR-3) - 4-5 days

**Timeline**: 2-3 months after Phase 1b complete

---

## Decisions Made

Based on user feedback (comment #3333161760):

1. ✅ **Cost Strategy**: INTEGRATE IT - proceed with integration
2. ✅ **Vehicle Manager**: REMOVE FOR NOW - clean up archived code
3. ⏸️ **Charger Presets**: DEFERRED - wait for cost strategy live testing
4. ⏸️ **Config Bundles**: DEFERRED - wait for cost strategy live testing
5. ✅ **Timeline**: REVISED to 1-2 weeks for objectives 1-3 only
6. ✅ **Phase 1 Scope**: FOCUS ON OBJECTIVES 1-3 - defer 4-5 for now

**Rationale**: Need to test cost strategy integration live before adding more features. Won't get it right the first time, will find important improvements during testing.

---

## Appendix: Files to Modify

### Core Integration Files (7-10 files)
1. `custom_components/energy_dispatcher/coordinator.py` - Cost strategy integration
2. `custom_components/energy_dispatcher/config_flow.py` - New config options, presets, bundles
3. `custom_components/energy_dispatcher/sensor.py` - New cost sensors
4. `custom_components/energy_dispatcher/const.py` - New constants
5. `custom_components/energy_dispatcher/__init__.py` - Service handlers
6. `custom_components/energy_dispatcher/services.yaml` - Import/export services
7. `custom_components/energy_dispatcher/manifest.json` - Version bump

### Translation Files (2 files)
8. `custom_components/energy_dispatcher/translations/en.json` - English text
9. `custom_components/energy_dispatcher/translations/sv.json` - Swedish text

### Test Files (2-3 files)
10. `pytest.ini` - New file
11. `requirements-test.txt` - New file
12. `tests/test_cost_strategy_integration.py` - New file (integration tests)

### Documentation Files (5-8 files)
13. `README.md` - Update with new features, testing section
14. `CHANGELOG.md` - v0.9.0 entry
15. `docs/configuration.md` - Update with cost strategy options
16. `docs/getting_started.md` - Update with presets and bundles
17. `docs/cost_strategy_guide.md` - New file
18. `docs/charger_presets.md` - New file (optional)
19. `docs/configuration_bundles.md` - New file (optional)

### CI/CD Files (2 files)
20. `.github/workflows/test.yml` - New file
21. `.github/workflows/lint.yml` - New file (optional)

**Total Estimated Files**: 20-25 files to create/modify

---

## Conclusion

This plan provides a structured approach to completing Path 1 of the Energy Dispatcher roadmap. The focus is on:

1. **Completing existing work** (cost strategy integration)
2. **Establishing good practices** (test infrastructure, CI/CD)
3. **Delivering user value** (charger presets, config bundles, import/export)
4. **Building momentum** (v0.9.0 release sets stage for Phase 2)

The plan is **realistic**, **focused**, and **delivers tangible value** to users while cleaning up the codebase and establishing best practices for future development.

**Next Step**: Review this plan and provide feedback. Once approved, we'll begin implementation starting with Week 1 tasks.
