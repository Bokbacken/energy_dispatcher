# Missing Data Handling Flow Diagrams

## 1. Baseline Calculation with Interpolation

```
┌─────────────────────────────────────────────────────────────┐
│ Coordinator Update (every 5 minutes)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ _calculate_48h_baseline()                                   │
│ - Fetch 48h historical data from Recorder                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Build Time Indexes                                          │
│ - Convert state lists to hour-indexed dictionaries          │
│ - One index per sensor (house, EV, battery, PV)             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Example: House Energy Index (BEFORE interpolation)          │
│                                                              │
│  10:00 → 100.0 kWh  ✓ (logged)                              │
│  11:00 → ❌ MISSING                                          │
│  12:00 → ❌ MISSING                                          │
│  13:00 → 115.0 kWh  ✓ (logged)                              │
│  14:00 → ❌ MISSING                                          │
│  15:00 → ❌ MISSING                                          │
│  16:00 → ❌ MISSING                                          │
│  17:00 → ❌ MISSING                                          │
│  18:00 → 135.0 kWh  ✓ (logged)                              │
│  19:00 → 140.0 kWh  ✓ (logged)                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ _fill_missing_hourly_data()                                 │
│ - Check gap between each consecutive pair                   │
│ - If gap ≤ 8 hours: interpolate missing points              │
│ - If gap > 8 hours: skip (log warning)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Interpolation Logic (10:00 → 13:00 gap)                     │
│                                                              │
│  Gap = 3 hours ≤ 8 hours ✓ OK to interpolate                │
│                                                              │
│  11:00 = 100 + (1/3) × (115 - 100) = 105.0 kWh              │
│  12:00 = 100 + (2/3) × (115 - 100) = 110.0 kWh              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Interpolation Logic (13:00 → 18:00 gap)                     │
│                                                              │
│  Gap = 5 hours ≤ 8 hours ✓ OK to interpolate                │
│                                                              │
│  14:00 = 115 + (1/5) × (135 - 115) = 119.0 kWh              │
│  15:00 = 115 + (2/5) × (135 - 115) = 123.0 kWh              │
│  16:00 = 115 + (3/5) × (135 - 115) = 127.0 kWh              │
│  17:00 = 115 + (4/5) × (135 - 115) = 131.0 kWh              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Example: House Energy Index (AFTER interpolation)           │
│                                                              │
│  10:00 → 100.0 kWh  ✓ (logged)                              │
│  11:00 → 105.0 kWh  📈 (interpolated)                       │
│  12:00 → 110.0 kWh  📈 (interpolated)                       │
│  13:00 → 115.0 kWh  ✓ (logged)                              │
│  14:00 → 119.0 kWh  📈 (interpolated)                       │
│  15:00 → 123.0 kWh  📈 (interpolated)                       │
│  16:00 → 127.0 kWh  📈 (interpolated)                       │
│  17:00 → 131.0 kWh  📈 (interpolated)                       │
│  18:00 → 135.0 kWh  ✓ (logged)                              │
│  19:00 → 140.0 kWh  ✓ (logged)                              │
│                                                              │
│  Total: 10 points (4 logged + 6 interpolated)               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Calculate Daypart Baselines                                 │
│ - Use filled indexes for all sensors                        │
│ - Calculate consumption for each hour pair                  │
│ - Group by daypart (night/day/evening)                      │
│ - Calculate averages                                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Return Baseline Results                                     │
│ - overall: 1.2 kWh/h                                        │
│ - night: 0.8 kWh/h                                          │
│ - day: 1.0 kWh/h                                            │
│ - evening: 1.6 kWh/h                                        │
└─────────────────────────────────────────────────────────────┘
```

## 2. BEC Tracking with Gap Detection

```
┌─────────────────────────────────────────────────────────────┐
│ Coordinator Update (every 5 minutes)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ _update_battery_charge_tracking()                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                    ┌───────┴───────┐
                    │               │
                    ▼               ▼
        ┌───────────────┐   ┌──────────────┐
        │  First Run?   │   │  New Day?    │
        │  (no timestamp│   │              │
        │   stored)     │   │              │
        └───────┬───────┘   └──────┬───────┘
                │ Yes                │ Yes
                ▼                    ▼
        Initialize tracking    Reset tracking
        └───────┬───────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│ Check for Large Gap                                         │
│                                                              │
│  gap_minutes = now - _batt_last_update_time                 │
│                                                              │
│  if gap_minutes > 60:  # 1 hour limit                       │
│      LOG: "Data gap of {gap} minutes exceeds 1 hour limit"  │
│      Reset tracking to avoid incorrect deltas               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Read Current Sensor Values                                  │
│ - Battery charged today                                     │
│ - Battery discharged today                                  │
│ - PV energy today                                           │
│ - Grid import today                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                    ┌───────┴───────┐
                    │ Sensor        │
                    │ Available?    │
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │ Yes           │               │ No
            ▼               ▼               ▼
    ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
    │ Have         │ │  Calculate  │ │ Check        │
    │ Previous?    │ │  Delta      │ │ Staleness    │
    └──────┬───────┘ └──────┬──────┘ └──────┬───────┘
           │ Yes            │               │
           ▼                ▼               ▼
    ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
    │ Calculate    │ │ Delta > 1Wh?│ │ > 15 min?    │
    │ Delta        │ └──────┬──────┘ └──────┬───────┘
    └──────┬───────┘        │ Yes           │ Yes
           │                ▼               ▼
           │         ┌─────────────┐ ┌──────────────┐
           │         │ Classify    │ │ LOG: Sensor  │
           │         │ Source      │ │ unavailable  │
           │         │ (grid/solar)│ │ for > 15 min │
           │         └──────┬──────┘ └──────────────┘
           │                │
           │                ▼
           │         ┌─────────────┐
           │         │ Call BEC    │
           │         │ on_charge() │
           │         │ or          │
           │         │ on_discharge│
           │         └──────┬──────┘
           │                │
           └────────────────┴──────────────┐
                                           │
                                           ▼
                            ┌──────────────────────┐
                            │ Update Timestamp     │
                            │ _batt_last_update_   │
                            │ time = now           │
                            └──────────────────────┘
```

## 3. Staleness Detection Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Sensor State Change                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                    ┌───────┴───────┐
                    │ Sensor State? │
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Valid    │    │ unknown  │    │ unavail  │
    │ numeric  │    │          │    │          │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         ▼               └───────┬───────┘
┌────────────────┐              │
│ Process Value  │              ▼
│ Update         │    ┌──────────────────┐
│ timestamp      │    │ _is_data_stale() │
└────────────────┘    │                  │
                      │ Check:           │
                      │ last_update_time │
                      └────────┬─────────┘
                               │
                       ┌───────┴────────┐
                       │                │
                       ▼                ▼
              ┌─────────────┐  ┌────────────┐
              │ Age ≤ 15min │  │ Age > 15min│
              └─────┬───────┘  └─────┬──────┘
                    │                │
                    ▼                ▼
            ┌──────────────┐  ┌──────────────┐
            │ Wait for     │  │ Treat as     │
            │ data         │  │ no data      │
            │ (next cycle) │  │ available    │
            └──────────────┘  └──────────────┘
```

## 4. Gap Scenarios

### Scenario A: Small Gap (Acceptable)

```
Timeline: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

10:00  ✓ 100 kWh
       │
       ├─ Gap: 2 hours
       │  Action: Interpolate
       │
11:00  📈 105 kWh (interpolated)
12:00  📈 110 kWh (interpolated)
       │
13:00  ✓ 115 kWh

Result: Baseline calculation uses all data points
```

### Scenario B: Large Gap (Exceeds Limit)

```
Timeline: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

10:00  ✓ 100 kWh
       │
       ├─ Gap: 10 hours (> 8 hour limit)
       │  Action: Skip this period
       │
20:00  ✓ 150 kWh

Result: Baseline calculation excludes this period
Log: "Skipping large gap: 10.0 hours between..."
```

### Scenario C: Counter Reset

```
Timeline: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

22:00  ✓ 95 kWh
23:00  ✓ 98 kWh
       │
       ├─ Counter reset at midnight
       │  98 → 2 (negative delta)
       │  Action: Do NOT interpolate
       │
00:00  ✓ 2 kWh (reset)
01:00  ✓ 5 kWh

Result: Uses reset value directly, no interpolation
```

### Scenario D: BEC Gap Detection

```
Timeline: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         (5-minute updates)

10:00  ✓ charged: 10.0 kWh
10:05  ✓ charged: 10.2 kWh → delta: 0.2 kWh ✓
10:10  ✓ charged: 10.5 kWh → delta: 0.3 kWh ✓
       │
       ├─ Sensor offline for 65 minutes
       │
11:15  ❌ sensor unavailable (gap > 1 hour)
       │  Action: Reset tracking
       │  Log: "Data gap of 65.0 minutes exceeds 1 hour limit"
       │
11:20  ✓ charged: 15.0 kWh
       │  Action: Start fresh (no delta calculated)
       │
11:25  ✓ charged: 15.3 kWh → delta: 0.3 kWh ✓

Result: BEC tracking protected from incorrect 4.5 kWh delta
```

## 5. Decision Tree

```
                  Start: New Sensor Reading
                            │
                            ▼
                    ┌───────────────┐
                    │ Sensor value  │
                    │   valid?      │
                    └───────┬───────┘
                            │
                ┌───────────┼───────────┐
                │ Yes                   │ No
                ▼                       ▼
        ┌──────────────┐      ┌────────────────┐
        │ Store value  │      │ Check staleness│
        │ Update time  │      └────────┬───────┘
        └──────┬───────┘               │
               │           ┌────────────┼──────────┐
               ▼           │ < 15 min            │ > 15 min
        ┌──────────────┐  ▼                      ▼
        │ Calculate    │ ┌────────────┐   ┌──────────────┐
        │ gap from     │ │ Wait/Retry │   │ Treat as     │
        │ last update  │ └────────────┘   │ unavailable  │
        └──────┬───────┘                  └──────────────┘
               │
               ▼
        ┌──────────────┐
        │ Gap check:   │
        │ Baseline: 8h │
        │ BEC: 1h      │
        └──────┬───────┘
               │
    ┌──────────┼──────────┐
    │ Within             │ Exceeds
    │ limit              │ limit
    ▼                    ▼
┌────────────┐    ┌──────────────┐
│ Process    │    │ Reset/Skip   │
│ normally   │    │ Log warning  │
│ Interpolate│    │              │
│ if needed  │    │              │
└────────────┘    └──────────────┘
```

## Legend

- ✓ = Logged data point
- ❌ = Missing data
- 📈 = Interpolated value
- ━━━ = Timeline
- │ = Relationship
- ▼ = Flow direction
