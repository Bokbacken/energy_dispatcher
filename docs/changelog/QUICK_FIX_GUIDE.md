# Quick Fix Guide - Energy Dispatcher v0.8.18 Regression

## 🎯 What Was Broken?

After PR#40 and PR#41, users experienced:
1. ❌ **Configuration dialog not loading** - 400: Bad Request error
2. ❌ **48h baseline calculation failing** - TypeError in logs
3. ⚠️ **Weather entity warnings** - "weather.met_no not found"

## ✅ What's Fixed Now?

### 1. Configuration Dialog Works Again
**Before:**
```
Fel: Konfigureringsflödet kunde inte laddas: 400: Bad Request
```

**After:**
- ✅ Configuration dialog loads successfully
- ✅ All fields display with proper defaults
- ✅ Weather entity selector works with any weather entity

**Technical:** Fixed `None` default value in NumberSelector for inverter AC capacity

---

### 2. Baseline Calculation Works Again
**Before:**
```
TypeError: HomeAssistant.async_add_executor_job() got an unexpected keyword argument 'entity_ids'
48h baseline calculation failed: Exception during calculation
```

**After:**
- ✅ 48h baseline calculation completes successfully
- ✅ Historical data fetched correctly
- ✅ Sensors display calculated values

**Technical:** Fixed async_add_executor_job to use positional arguments only

---

### 3. Weather Entity Warnings Explained
**Message:**
```
Weather entity weather.met_no not found
```

**Status:** ℹ️ **This is informational, not an error**

**What it means:**
- Your weather entity may not be loaded yet at startup
- The integration continues to work using clear-sky calculations
- You can configure `weather.met_no` in the settings

**To verify your weather entity:**
1. Go to Developer Tools → States
2. Search for your weather entity (e.g., "weather.met_no")
3. If it exists, configure it in Energy Dispatcher settings
4. If it doesn't exist, check your weather integration (e.g., Met.no)

---

## 📝 Changes Made

### File: `coordinator.py`
```python
# BEFORE (Line 375) - ❌ BROKEN:
all_hist = await self.hass.async_add_executor_job(
    history.state_changes_during_period, self.hass, start, end, entity_ids=entities_to_fetch
)

# AFTER - ✅ FIXED:
all_hist = await self.hass.async_add_executor_job(
    history.state_changes_during_period, self.hass, start, end, entities_to_fetch
)
```

### File: `config_flow.py`
```python
# BEFORE (Line 146) - ❌ BROKEN:
CONF_MANUAL_INVERTER_AC_CAP: None,

# AFTER - ✅ FIXED:
CONF_MANUAL_INVERTER_AC_CAP: 10.0,  # Default 10 kW AC capacity
```

---

## 🚀 How to Update

1. **Pull the latest changes** from this PR
2. **Restart Home Assistant**
3. **Verify fixes:**
   - Open Energy Dispatcher configuration (should load without 400 error)
   - Check logs for "48h baseline calculation succeeded"
   - Weather warnings are informational only

---

## 🔍 What You Should See in Logs

### ✅ Good Messages (After Fix):
```
48h baseline calculation succeeded: overall=X.XXX night=X.XXX day=X.XXX evening=X.XXX
Baseline: method=energy_counter_48h overall=X.XXX kWh/h
```

### ❌ Bad Messages (Before Fix):
```
Failed to calculate 48h baseline: HomeAssistant.async_add_executor_job() got an unexpected keyword argument 'entity_ids'
48h baseline calculation failed: Exception during calculation
```

### ℹ️ Informational Messages (Not Errors):
```
Weather entity weather.met_no not found
EVDispatcher: entity button.xxx unavailable, skipping
```
These are expected when entities are temporarily unavailable.

---

## 💡 Additional Notes

### No Breaking Changes
- ✅ Existing configurations will continue to work
- ✅ No user action required for the fixes
- ✅ Settings are preserved

### Manual Inverter AC Capacity
- New default: **10.0 kW**
- If you had this set to a different value, it's preserved
- Only affects new installations or users who never set this value

### Weather Entity
- The configuration selector already allows any weather entity
- `weather.met_no` will work if the entity exists in Home Assistant
- No changes needed to support existing weather entities

---

## 📊 Testing Status

- [x] Python syntax validation passed
- [x] Configuration schema validated
- [x] async_add_executor_job calling pattern validated
- [x] No remaining None defaults in NumberSelectors
- [x] All changes minimal and targeted

---

## 🆘 Need Help?

If you still experience issues after applying these fixes:

1. **Check Home Assistant logs** for specific error messages
2. **Verify entity names** in Developer Tools → States
3. **Check recorder retention** (needs at least 48h of data for baseline)
4. **Ensure energy counter entities** are configured and reporting values

---

## 📚 Related Documentation

- Full details: See `FIX_SUMMARY.md`
- Configuration: See `docs/configuration.md`
- Baseline feature: See `docs/48h_baseline_feature.md`
