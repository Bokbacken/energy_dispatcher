# Energy Dispatcher Documentation

Welcome to the Energy Dispatcher documentation! This guide helps you navigate the available documentation resources.

## 📚 Main Documentation

### Getting Started
- **[getting_started.md](getting_started.md)** - 10-minute quick start guide
- **[configuration.md](configuration.md)** - Comprehensive configuration reference (533 lines)
- **[dashboard_guide.md](dashboard_guide.md)** - Step-by-step dashboard creation

### Features & Guides
- **[battery_cost_tracking.md](battery_cost_tracking.md)** - Battery Energy Cost (BEC) tracking
- **[manual_forecast.md](manual_forecast.md)** - Physics-based solar forecasting
- **[missing_data_handling.md](missing_data_handling.md)** - Technical deep dive on data handling
- **[multi_vehicle_setup.md](multi_vehicle_setup.md)** - Multi-vehicle EV charging (archived feature)

### Reference & Planning
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - API and code examples
- **[future_improvements.md](future_improvements.md)** - Roadmap and planned features (830 lines)
- **[48h_baseline_feature.md](48h_baseline_feature.md)** - 48-hour baseline calculation feature
- **[solar_forecast_improvement.md](solar_forecast_improvement.md)** - Solar forecasting enhancements

### 🆕 Cost Strategy & Optimization
- **[cost_strategy_and_battery_optimization.md](cost_strategy_and_battery_optimization.md)** - **NEW**: Comprehensive guide to the cost strategy system, battery optimization, and integration roadmap

## 🔧 Technical Documentation

### Implementation & Architecture
Located in **[technical/](technical/)** folder:
- **[COMPREHENSIVE_EVALUATION.md](technical/COMPREHENSIVE_EVALUATION.md)** - Complete status evaluation and recommendations
- **[RECOMMENDED_NEXT_STEPS.md](technical/RECOMMENDED_NEXT_STEPS.md)** - 30-day action plan
- **[IMPLEMENTATION_SUMMARY.md](technical/IMPLEMENTATION_SUMMARY.md)** - Implementation details
- **[IMPROVEMENTS_SUMMARY.md](technical/IMPROVEMENTS_SUMMARY.md)** - Improvement tracking
- **[MISSING_DATA_HANDLING_SUMMARY.md](technical/MISSING_DATA_HANDLING_SUMMARY.md)** - Missing data handling technical details
- **[DIAGNOSTIC_GUIDE.md](technical/DIAGNOSTIC_GUIDE.md)** - Diagnostic features guide
- **[BEFORE_AFTER_EXAMPLE.md](technical/BEFORE_AFTER_EXAMPLE.md)** - Before/after comparisons
- **[EVALUATION_README.md](technical/EVALUATION_README.md)** - Evaluation documentation
- **[EVALUATION_SUMMARY.md](technical/EVALUATION_SUMMARY.md)** - Evaluation summary
- **[FIX_README.md](technical/FIX_README.md)** - Fix documentation

## 🐛 Changelog & Bugfixes

Located in **[changelog/](changelog/)** folder (21 files):
- Version-specific fix summaries (v0.8.24, v0.8.25, v0.8.28, etc.)
- Feature implementation summaries
- Bugfix documentation
- PR summaries

Key files:
- **[changelog/BATTERY_COST_FIX_v0.8.28.md](changelog/BATTERY_COST_FIX_v0.8.28.md)** - Battery cost tracking fix
- **[changelog/CONFIG_FLOW_FIX_v0.8.24.md](changelog/CONFIG_FLOW_FIX_v0.8.24.md)** - Config flow improvements
- **[changelog/CONFIG_FLOW_FIX_v0.8.25.md](changelog/CONFIG_FLOW_FIX_v0.8.25.md)** - Further config flow fixes
- **[changelog/HOURLY_FORECAST_IMPLEMENTATION.md](changelog/HOURLY_FORECAST_IMPLEMENTATION.md)** - Hourly forecast feature
- **[changelog/DIAGNOSTIC_FEATURE_SUMMARY.md](changelog/DIAGNOSTIC_FEATURE_SUMMARY.md)** - Diagnostic features

## 📖 Recommended Reading Paths

### For New Users
1. [getting_started.md](getting_started.md) - Start here!
2. [configuration.md](configuration.md) - Configure your setup
3. [dashboard_guide.md](dashboard_guide.md) - Create your dashboard

### For Advanced Users
1. [battery_cost_tracking.md](battery_cost_tracking.md) - Understand BEC
2. [manual_forecast.md](manual_forecast.md) - Configure solar forecasting
3. [cost_strategy_and_battery_optimization.md](cost_strategy_and_battery_optimization.md) - Learn about cost optimization (future feature)

### For Developers
1. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - API reference
2. [technical/COMPREHENSIVE_EVALUATION.md](technical/COMPREHENSIVE_EVALUATION.md) - Project status
3. [technical/RECOMMENDED_NEXT_STEPS.md](technical/RECOMMENDED_NEXT_STEPS.md) - Development roadmap
4. [cost_strategy_and_battery_optimization.md](cost_strategy_and_battery_optimization.md) - Integration guide

### For Troubleshooting
1. [missing_data_handling.md](missing_data_handling.md) - Data gap handling
2. [technical/DIAGNOSTIC_GUIDE.md](technical/DIAGNOSTIC_GUIDE.md) - Diagnostic features
3. [changelog/](changelog/) - Check version-specific fixes

## 🗂️ Documentation Organization

As of v0.8.31, documentation is organized as follows:

```
docs/
├── README.md                          ← You are here
├── getting_started.md                 ← Start here for new users
├── configuration.md                   ← Main configuration reference
├── dashboard_guide.md                 ← Dashboard setup
├── battery_cost_tracking.md           ← BEC feature
├── manual_forecast.md                 ← Solar forecasting
├── missing_data_handling.md           ← Data handling
├── multi_vehicle_setup.md             ← Multi-vehicle (archived)
├── cost_strategy_and_battery_optimization.md  ← NEW: Cost strategy guide
├── QUICK_REFERENCE.md                 ← API reference
├── future_improvements.md             ← Roadmap
├── 48h_baseline_feature.md            ← Baseline feature
├── solar_forecast_improvement.md      ← Solar improvements
├── CHANGELOG_CONFIG_IMPROVEMENTS.md   ← Config changelog
├── CONFIG_UI_IMPROVEMENTS.md          ← UI improvements
├── FUTURE_FORECAST_ENHANCEMENTS.md    ← Forecast enhancements
├── IMPLEMENTATION_SUMMARY.md          ← Implementation notes
├── missing_data_flow_diagram.md       ← Data flow diagram
├── changelog/                         ← 21 bugfix summaries
│   ├── BATTERY_COST_FIX_v0.8.28.md
│   ├── CONFIG_FLOW_FIX_v0.8.24.md
│   ├── CONFIG_FLOW_FIX_v0.8.25.md
│   ├── HOURLY_FORECAST_IMPLEMENTATION.md
│   └── ... (17 more files)
└── technical/                         ← 10 technical documents
    ├── COMPREHENSIVE_EVALUATION.md
    ├── RECOMMENDED_NEXT_STEPS.md
    ├── IMPLEMENTATION_SUMMARY.md
    ├── IMPROVEMENTS_SUMMARY.md
    ├── MISSING_DATA_HANDLING_SUMMARY.md
    ├── DIAGNOSTIC_GUIDE.md
    └── ... (4 more files)
```

## 📝 Contributing to Documentation

When adding new documentation:
- **User guides** → `docs/` (root level)
- **Bugfix summaries** → `docs/changelog/`
- **Technical deep dives** → `docs/technical/`

Keep the root directory clean with only essential files (README, CHANGELOG, LICENSE, QUICK_START).

## 🔗 External Links

- **GitHub Repository**: https://github.com/Bokbacken/energy_dispatcher
- **Issue Tracker**: https://github.com/Bokbacken/energy_dispatcher/issues
- **HACS**: [Energy Dispatcher on HACS](https://github.com/hacs/default)

---

**Last Updated**: 2025-10-12 (v0.8.31)
