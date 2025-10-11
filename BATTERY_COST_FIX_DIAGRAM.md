# Battery Energy Cost Fix - Visual Explanation

## The Problem (Before v0.8.28)

```
Scenario: Morning sun, no load sensor configured

┌─────────────────────────────────────────────────┐
│  Solar Panels: 6 kW Production                  │
└────────────────┬────────────────────────────────┘
                 │
                 ├───────── 3 kW ────────┐
                 │                       │
                 │                       ▼
                 │              ┌──────────────────┐
                 │              │   House Load     │
                 │              │   (unknown)      │
                 │              └──────────────────┘
                 │
                 ├───────── 3 kW ────────┐
                 │                       │
                 └───────── 1 kW ────────┤
                                         ▼
                                ┌──────────────────┐
                Grid 1 kW ──►   │  Battery (4 kW)  │
                                └──────────────────┘

OLD CALCULATION (WRONG):
- PV Power: 6 kW
- Load Power: 0 (NOT CONFIGURED!)
- PV Surplus: 6 - 0 = 6 kW
- Battery Charge: 4 kW
- Check: 6 >= 4 * 0.8 = 3.2? YES
- Classification: SOLAR ❌
- Cost: 0.00 SEK/kWh ❌

REALITY:
- House is consuming 3 kW
- Only 3 kW available for battery
- Battery needs 4 kW
- 1 kW coming from GRID!
- Should cost: 2.50 SEK/kWh
```

## The Solution (After v0.8.28)

```
Same scenario with conservative classification

┌─────────────────────────────────────────────────┐
│  Solar Panels: 6 kW Production                  │
└────────────────┬────────────────────────────────┘
                 │
                 ├───────── 3 kW ────────┐
                 │                       │
                 │                       ▼
                 │              ┌──────────────────┐
                 │              │   House Load     │
                 │              │   (unknown)      │
                 │              └──────────────────┘
                 │
                 ├───────── 3 kW ────────┐
                 │                       │
                 └───────── 1 kW ────────┤
                                         ▼
                                ┌──────────────────┐
                Grid 1 kW ──►   │  Battery (4 kW)  │
                                └──────────────────┘

NEW CALCULATION (CONSERVATIVE):
- PV Power: 6 kW
- Load Power: unknown (NOT CONFIGURED)
- Battery Charge: 4 kW
- Check: 6 >= 4 * 2.0 = 8 kW? NO
- Classification: GRID ✅
- Cost: 2.50 SEK/kWh ✅

BENEFIT:
- Conservative approach
- Accounts for unknown house load
- Prevents false "free" classification
- More accurate cost tracking
```

## When Solar Classification Works (High PV)

```
Midday sun, high production

┌─────────────────────────────────────────────────┐
│  Solar Panels: 12 kW Production                 │
└────────────────┬────────────────────────────────┘
                 │
                 ├───────── 4 kW ────────┐
                 │                       │
                 │                       ▼
                 │              ┌──────────────────┐
                 │              │   House Load     │
                 │              │   (unknown)      │
                 │              └──────────────────┘
                 │
                 └───────── 8 kW ────────┐
                                         ▼
                                ┌──────────────────┐
                                │  Battery (5 kW)  │
                                └──────────────────┘
                                         │
                                         └───── 3 kW ──► Grid Export

NEW CALCULATION:
- PV Power: 12 kW
- Load Power: unknown (NOT CONFIGURED)
- Battery Charge: 5 kW
- Check: 12 >= 5 * 2.0 = 10 kW? YES ✅
- Classification: SOLAR ✅
- Cost: 0.00 SEK/kWh ✅

With 2x multiplier, we're confident:
- Even if house uses 4 kW
- Still 8 kW left for battery
- Battery only needs 5 kW
- Definitely solar charging!
```

## Classification Thresholds Comparison

```
Battery Charge Power: 4 kW

┌────────────────────────────────────────────────────────────┐
│                      PV POWER (kW)                         │
├────────────────────────────────────────────────────────────┤
│  0    2    4    6    8    10   12   14   16   18   20     │
│  ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤      │
│  │    │    │    │    │    │    │    │    │    │    │      │
│  └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘      │
│                      │         │                            │
│                      │         │                            │
│  OLD (0.8x): ───────▲         │                            │
│  Threshold: 4 * 0.8 = 3.2 kW  │                            │
│  (without load, assumes 0)    │                            │
│                                │                            │
│  NEW (2.0x): ──────────────────▲                           │
│  Threshold: 4 * 2.0 = 8 kW                                 │
│  (conservative, accounts for unknown load)                 │
│                                                             │
│  Classification:                                            │
│  ├─────────────┤ = GRID (with cost)                        │
│                ├──────────────────────────────────┤         │
│                = SOLAR (free)                               │
└────────────────────────────────────────────────────────────┘

OLD BEHAVIOR (0.8x):
- Solar if: PV >= 3.2 kW (TOO LENIENT without load sensor!)
- Many false solar classifications
- Underestimated battery cost

NEW BEHAVIOR (2.0x):
- Solar if: PV >= 8 kW (CONSERVATIVE)
- Safer classification
- Accurate battery cost tracking
```

## Real-World Impact

```
Daily Battery Charging Profile (Example User)

Time  │ PV   │ Batt │ OLD Class │ NEW Class │ OLD Cost │ NEW Cost
─────┼──────┼──────┼───────────┼───────────┼──────────┼──────────
06:00 │ 1kW  │ 2kW  │ GRID      │ GRID      │ 2.5 SEK  │ 2.5 SEK
08:00 │ 4kW  │ 3kW  │ SOLAR ❌  │ GRID ✅   │ 0.0 SEK  │ 2.5 SEK
10:00 │ 8kW  │ 4kW  │ SOLAR ❌  │ GRID ✅   │ 0.0 SEK  │ 2.5 SEK
12:00 │ 12kW │ 5kW  │ SOLAR ✅  │ SOLAR ✅  │ 0.0 SEK  │ 0.0 SEK
14:00 │ 10kW │ 5kW  │ SOLAR ✅  │ SOLAR ✅  │ 0.0 SEK  │ 0.0 SEK
16:00 │ 6kW  │ 3kW  │ SOLAR ❌  │ GRID ✅   │ 0.0 SEK  │ 2.5 SEK
18:00 │ 2kW  │ 2kW  │ GRID      │ GRID      │ 2.5 SEK  │ 2.5 SEK

Total Battery Charged: 24 kWh

OLD CALCULATION:
- Solar: 18 kWh @ 0.0 = 0.0 SEK
- Grid:   6 kWh @ 2.5 = 15.0 SEK
- Total: 15.0 SEK
- WACE: 0.625 SEK/kWh

NEW CALCULATION (CORRECT):
- Solar: 10 kWh @ 0.0 = 0.0 SEK
- Grid:  14 kWh @ 2.5 = 35.0 SEK
- Total: 35.0 SEK
- WACE: 1.458 SEK/kWh

DIFFERENCE:
- Cost difference: 20.0 SEK/day = 600 SEK/month
- User now sees ACCURATE battery cost!
- Better decisions about when to charge/discharge
```

## Recommendation

### Best Accuracy (Recommended)
```
┌─────────────────────────────────────────────┐
│  Configure ALL sensors:                     │
│  ✅ pv_power_entity                         │
│  ✅ load_power_entity ← KEY FOR ACCURACY!   │
│  ✅ batt_power_entity                       │
│  ✅ batt_energy_charged_today_entity        │
│  ✅ batt_energy_discharged_today_entity     │
└─────────────────────────────────────────────┘

Result: Uses 0.8x threshold with accurate PV surplus calculation
```

### Without Load Sensor (Conservative)
```
┌─────────────────────────────────────────────┐
│  If load sensor not available:              │
│  ✅ pv_power_entity                         │
│  ❌ load_power_entity (not configured)      │
│  ✅ batt_power_entity (recommended)         │
│  ✅ batt_energy_charged_today_entity        │
│  ✅ batt_energy_discharged_today_entity     │
└─────────────────────────────────────────────┘

Result: Uses 2.0x threshold for conservative (safe) classification
```

## Summary

**The Fix:**
- Detects when load sensor is missing
- Uses conservative 2.0x multiplier instead of 0.8x
- Prevents false "free solar" classifications
- Provides accurate battery energy cost tracking

**User Benefit:**
- Correct cost calculations
- Better decision making
- More reliable automation
- Realistic battery cost tracking

**Backward Compatible:**
- Systems with load sensor: No change
- Systems without load sensor: Conservative (safer)
