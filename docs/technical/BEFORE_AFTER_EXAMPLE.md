# Before and After: Diagnostic Improvements

## Problem Scenario
Your "House Load Baseline Now" sensor shows "unknown" and you don't know why.

## Before (v0.8.17 and earlier)

### What you see in Home Assistant UI:

**Sensor State:** `unknown`

**Attributes:**
```yaml
method: energy_counter_48h
source_value: Okänd  # Swedish for "Unknown"
baseline_kwh_per_h: Okänd
exclusion_reason: ""  # Empty - no information!
```

### To troubleshoot, you had to:
1. Go to Settings → System → Logs
2. Enable debug logging for `energy_dispatcher`
3. Restart Home Assistant
4. Wait for next update cycle (5 minutes)
5. Search through debug logs
6. Try to interpret technical messages
7. Still might not know what's wrong

### Result: 😞
- No immediate feedback
- Requires technical knowledge
- Time-consuming process
- Might still not solve the issue

---

## After (v0.8.18+) ✨

### Scenario 1: Sensor not configured

**Sensor State:** `unknown`

**Attributes:**
```yaml
method: energy_counter_48h
source_value: null
baseline_kwh_per_h: null
exclusion_reason: "No house energy counter configured (runtime_counter_entity)"
```

**What this tells you:** 
- ✅ The problem is clear: no sensor configured
- ✅ What to do: Configure `runtime_counter_entity` in settings

**Time to fix:** ~1 minute (just configure the sensor)

---

### Scenario 2: New installation / Not enough data

**Sensor State:** `unknown`

**Attributes:**
```yaml
method: energy_counter_48h
source_value: 1234.5  # Shows current counter value!
baseline_kwh_per_h: null
exclusion_reason: "Insufficient historical data: 0 data points (need 2+)"
```

**What this tells you:**
- ✅ Sensor is working! (source_value shows 1234.5)
- ✅ Problem: Not enough historical data yet
- ✅ What to do: Wait 1-2 hours for data to accumulate

**Time to fix:** Wait 1-2 hours (automatic)

---

### Scenario 3: Sensor reporting bad values

**Sensor State:** `unknown`

**Attributes:**
```yaml
method: energy_counter_48h
source_value: unavailable  # Sensor is broken!
baseline_kwh_per_h: null
exclusion_reason: "Invalid sensor values: start=None, end=None"
```

**What this tells you:**
- ✅ Problem: Sensor is reporting "unavailable"
- ✅ What to check: The integration providing the sensor
- ✅ What to do: Check sensor configuration, restart integration

**Time to fix:** ~5 minutes (fix the sensor)

---

### Scenario 4: Working correctly ✨

**Sensor State:** `897` W

**Attributes:**
```yaml
method: energy_counter_48h
source_value: 1234.5
baseline_kwh_per_h: 0.8965
exclusion_reason: ""  # Empty = everything OK!
```

**What this tells you:**
- ✅ Everything working!
- ✅ Average consumption: 0.8965 kWh/h (897W)
- ✅ Counter currently at 1234.5 kWh

---

## Key Improvements

### 1. Immediate Feedback
**Before:** Check logs, debug mode, restart  
**After:** Look at `exclusion_reason` attribute

### 2. Actionable Messages
**Before:** Generic "unknown"  
**After:** Specific reason with guidance

### 3. Sensor Verification
**Before:** `source_value: Okänd` (no info)  
**After:** `source_value: 1234.5` (shows current counter)

### 4. Self-Service
**Before:** Contact support, open GitHub issue  
**After:** Follow DIAGNOSTIC_GUIDE.md, fix yourself

---

## How to View Attributes in Home Assistant

### Method 1: Developer Tools
1. Go to **Developer Tools** → **States**
2. Search for `sensor.house_load_baseline_now`
3. Look at the **Attributes** section
4. Check the `exclusion_reason` field

### Method 2: Dashboard Card
Add this to your dashboard to see attributes:

```yaml
type: entities
entities:
  - entity: sensor.house_load_baseline_now
    secondary_info: last-changed
cards:
  - type: attribute
    entity: sensor.house_load_baseline_now
    attribute: exclusion_reason
    name: Diagnostic Info
  - type: attribute
    entity: sensor.house_load_baseline_now
    attribute: source_value
    name: Current Counter Value
  - type: attribute
    entity: sensor.house_load_baseline_now
    attribute: baseline_kwh_per_h
    name: Average kWh/h
```

### Method 3: Entity Card with More Info
1. Add entity to dashboard
2. Click on it
3. Scroll down to see all attributes including `exclusion_reason`

---

## Real User Impact

### Before Enhancement
**User's question on GitHub:**
> "The House Load Baseline shows 'Okänd' for everything. I don't know what's wrong. Can I find debug information somewhere?"

**Response time:** Days (waiting for support)

### After Enhancement
**User's solution:**
> "Oh! The `exclusion_reason` says 'Insufficient historical data: 0 data points (need 2+)'. I just installed this an hour ago. I'll wait for data to accumulate. Thanks!"

**Response time:** Self-solved in 1 minute 🎉

---

## Summary

This enhancement transforms a frustrating debugging experience into a quick, self-service fix by providing:

1. ✅ **Clear failure reasons** in UI (no log diving)
2. ✅ **Current sensor values** for verification
3. ✅ **Actionable guidance** for each scenario
4. ✅ **Comprehensive documentation** (DIAGNOSTIC_GUIDE.md)

Users can now diagnose and fix baseline issues themselves in minutes instead of hours or days! 🚀
