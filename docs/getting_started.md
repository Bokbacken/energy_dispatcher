# Getting Started with Energy Dispatcher

Welcome! This guide will help you get Energy Dispatcher up and running in the shortest time possible.

## 🎯 Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Energy Dispatcher Flow                                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. INSTALL      → Copy files & restart                      │
│                                                               │
│  2. CONFIGURE    → Set prices, battery, EV, solar            │
│                                                               │
│  3. DASHBOARD    → Create visual control center              │
│                                                               │
│  4. OPTIMIZE     → Let it run and monitor                    │
│                                                               │
│  5. CUSTOMIZE    → Adjust based on your needs                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Time Investment**: 10-15 minutes for basic setup  
**Skill Level**: Beginner-friendly (no coding required for basic use)  
**Reward**: Automated energy cost optimization 24/7

## 🚀 Quick Start (10 Minutes)

### Step 1: Install the Integration (2 minutes)

1. **Copy Files**: Place the `energy_dispatcher` folder in `/config/custom_components/`
2. **Restart**: Restart Home Assistant
3. **Verify**: Check that Home Assistant restarted successfully

### Step 2: Configure the Integration (5 minutes)

1. Go to **Settings** → **Devices & Services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"Energy Dispatcher"**
4. Fill in the required information:

> 🆕 **New in v0.8.7+**: After configuration, you'll receive a helpful welcome notification with dashboard setup guidance!

#### Essential Configuration

**Prices** (Required):
- Select your Nordpool sensor
- Enter energy tax: `0.395` SEK/kWh (typical Swedish value)
- Enter grid transfer: `0.50` SEK/kWh (typical, check your contract)
- VAT: `0.25` (25%)

**Battery** (If you have one):
- Capacity: e.g., `15.0` kWh
- SOC sensor: Select your battery state of charge sensor
- Max charge power: e.g., `5000` W
- Max discharge power: e.g., `5000` W

**EV Charging** (If you have an EV):
- Battery capacity: e.g., `75.0` kWh for Tesla Model Y
- Current SOC: e.g., `40` %
- Target SOC: e.g., `80` %
- Charger max current: e.g., `16` A
- Phases: `3` (or `1` for single-phase)
- Voltage: `230` V

**Solar** (If you have solar panels):
- Latitude: Your location
- Longitude: Your location
- Solar panels: Use the example JSON and modify for your setup
- Weather entity: Select your weather integration

5. Click **"SUBMIT"**
6. Integration is now configured! ✅

### Step 3: Create Your Dashboard (3 minutes)

**Option A: Copy Complete Dashboard** (Fastest)

1. Create a new dashboard:
   - Settings → Dashboards → "+ ADD DASHBOARD"
   - Name: "Energy Control Center"
   - Icon: `mdi:lightning-bolt`

2. Enter edit mode and paste the complete YAML:
   - Click pencil icon (Edit)
   - Three dots menu → "Raw Configuration Editor"
   - Paste the complete dashboard YAML from [Dashboard Guide - Complete YAML](./dashboard_guide.md#complete-dashboard-yaml)
   - Click "SAVE"

3. Done! You now have a working dashboard 🎉

**Option B: Build Step-by-Step** (More control)

Follow the detailed [Dashboard Setup Guide](./dashboard_guide.md) to build your dashboard card by card.

### Step 4: Set Your Preferences (1 minute)

Adjust these values on your dashboard:

- **EV Current SOC**: Set to your actual EV charge level
- **EV Target SOC**: Set to desired charge level (typically 80%)
- **Battery SOC Floor**: Set to minimum battery level (typically 10-20%)

### Step 5: Monitor & Enjoy! (Ongoing)

Watch your dashboard for:
- Current electricity price
- Solar forecast for today/tomorrow
- Battery and EV optimization status
- Upcoming charge/discharge decisions

## 📚 What You Get

After completing these steps, you'll have:

✅ **Automated Optimization**
- Battery charges during cheap hours
- EV charges optimally before your target time
- Solar production maximized
- Costs minimized automatically

✅ **Visual Dashboard**
- 48-hour price and solar forecast
- Real-time system status
- Quick override controls
- Key insights and metrics

✅ **Smart Control**
- Override buttons for manual control
- Auto-mode for hands-off operation
- Detailed reasons for every action
- Cost tracking and savings

## 🎯 Next Steps

### Customize Your Setup

**For Basic Users**:
- Adjust EV target SOC daily based on your needs
- Use override buttons when you need immediate charging
- Monitor the "Key Insights" for savings

**For Advanced Users**:
- Create automations to update EV SOC when plugged in ([examples](./dashboard_guide.md#creating-an-automation-for-ev-soc-updates))
- Add custom sensors for additional metrics
- Set up notifications for charging completion
- Fine-tune price thresholds based on your electricity contract

### Understand the Integration

📖 **Recommended Reading Order**:

1. **[Dashboard Guide](./dashboard_guide.md)** ⭐ **YOU ARE HERE**
   - Complete dashboard setup
   - Where to enter different code types
   - Troubleshooting common issues

2. **[Configuration Guide](./configuration.md)**
   - Detailed explanation of every setting
   - Advanced configuration options
   - Understanding the calculations

3. **[Quick Reference](./QUICK_REFERENCE.md)**
   - Command cheat sheet
   - Common operations
   - Quick tips

4. **[Multi-Vehicle Setup](./multi_vehicle_setup.md)**
   - Managing 2+ electric vehicles
   - Charger scheduling
   - Cost strategies

5. **[Battery Cost Tracking](./battery_cost_tracking.md)**
   - Understanding battery economics
   - Tracking energy costs
   - Maximizing savings

### Common Scenarios

#### Scenario 1: Morning Commute
**Situation**: Need car ready by 8 AM tomorrow

**Steps**:
1. Set EV Current SOC to actual level (e.g., 40%)
2. Set EV Target SOC to desired level (e.g., 80%)
3. System automatically charges during cheapest hours before 8 AM

**Result**: Car ready, costs minimized ✅

#### Scenario 2: Emergency Charge
**Situation**: Need car charged ASAP, regardless of price

**Steps**:
1. Click "Force EV Charge (1 hour)" button on dashboard
2. System starts charging immediately at maximum power

**Result**: Car charges right away ⚡

#### Scenario 3: High Price Period
**Situation**: Electricity is expensive, want to use battery

**Steps**:
1. System automatically detects high price
2. Battery discharges to power home
3. Grid import reduced during expensive hours

**Result**: Automatic cost savings 💰

#### Scenario 4: Sunny Day
**Situation**: Solar production high, want to use for charging

**Steps**:
1. System automatically prioritizes solar
2. EV charges when solar production is high
3. Excess solar charges battery

**Result**: Maximized free energy use ☀️

#### Scenario 5: Export Profitability (Advanced)
**Situation**: Exceptionally high electricity prices, want to export energy

**Prerequisites**:
- Export mode configured in integration settings
- Battery with sufficient charge
- High spot prices (>5 SEK/kWh)

**Steps**:
1. Configure export mode via Settings → Devices & Services → Energy Dispatcher → Configure
2. Choose export mode:
   - **Never Export** (Default): Conservative, never sells to grid
   - **Excess Solar Only**: Export when battery full and solar producing excess
   - **Peak Price Opportunistic**: Also export during exceptional prices (>5 SEK/kWh)
3. Set minimum export price (default: 3.0 SEK/kWh)
4. System automatically analyzes export opportunities

**Result**: Additional revenue during peak prices 💰

**Dashboard Monitoring**:
- **Export Opportunity** sensor shows when export is recommended
- **Export Revenue Estimate** shows potential earnings
- Monitor reason in sensor attributes

**Conservative Philosophy**:
Export is intentionally conservative - defaults to "never export" because:
- Export prices are usually lower than import prices
- Battery degradation has a cost
- Stored energy is valuable for future high-cost periods

Only exports when:
- Battery is full and solar would be wasted
- Prices are exceptionally high (>5 SEK/kWh)
- Net revenue is clearly positive after all costs

## 🔧 Configuration Tips

### Price Settings

**Swedish Users** (typical values):
```yaml
Energy Tax: 0.395 SEK/kWh
Grid Transfer: 0.50 SEK/kWh (check your contract)
Supplier Surcharge: 0.05 SEK/kWh
VAT: 0.25 (25%)
Fixed Monthly: 75 SEK (optional)
```

**Other Countries**:
Adjust values based on your electricity contract and local regulations.

### Battery Settings

**Recommended SOC Floor**:
- `10%` - Minimum to protect battery health
- `20%` - More conservative, better for battery longevity
- `30%` - Very conservative, ensures reserve for emergencies

**Max Power Settings**:
- Use actual inverter limits
- Leave some margin (e.g., if max is 5000W, set to 4500W)
- Consider your battery's C-rating

### EV Settings

**Target SOC Recommendations**:
- Daily driving: `80%` (best for battery health)
- Long trips: `90-100%`
- Weekend only: `60-70%`

**Charger Current**:
- Use maximum safe current for your installation
- Common values: 6A, 10A, 13A, 16A, 32A
- Consider your electrical panel capacity

### Solar Settings

**For Best Results**:
- Use actual panel specifications
- Enter accurate tilt and azimuth
- Configure horizon profile if buildings/trees block sun
- Enable weather entity for cloud compensation

## ❓ FAQ

### Q: The dashboard shows "Unavailable" for some sensors
**A**: Wait 5-10 minutes for the first update cycle to complete. If still unavailable, check that all required integrations (Nordpool, battery, etc.) are working.

### Q: EV isn't charging even though price is low
**A**: Check that:
- Auto EV switch is ON
- Current SOC is below Target SOC
- Charger entities are configured correctly
- EVSE control switches are working

### Q: Battery isn't discharging during high prices
**A**: Check that:
- Battery SOC is above SOC Floor
- Max discharge power is set correctly
- Battery adapter (e.g., Huawei) is configured
- Auto Planner switch is ON

### Q: Solar forecast shows zero
**A**: Check that:
- Latitude/longitude are correct
- Panel configuration is valid JSON
- Forecast.Solar API is responding (check logs)
- Time of day (night = zero solar is expected!)

### Q: Dashboard graphs are empty
**A**: 
- Install ApexCharts from HACS
- Clear browser cache (Ctrl+F5)
- Check that sensors have `forecast` or `hourly` attributes
- Wait for one full update cycle

### Q: Can I have multiple vehicles?
**A**: Yes! The integration supports multiple EVs. See [Multi-Vehicle Setup](./multi_vehicle_setup.md) for details. Full multi-vehicle UI is coming in a future update (see [Future Improvements](./future_improvements.md)).

### Q: How much will this save me?
**A**: Savings vary based on:
- Electricity price variation in your area
- Battery size
- Solar production
- Usage patterns

Typical users report 20-40% reduction in electricity costs with good price variation and solar production.

## 🆘 Getting Help

### Check Logs First

1. Go to **Settings** → **System** → **Logs**
2. Search for `energy_dispatcher`
3. Look for errors or warnings
4. Check timestamp of errors

### Common Log Errors

**"Entity not found"**: Check entity names in configuration
**"API error"**: Check internet connection and API keys
**"Invalid JSON"**: Check solar panel configuration JSON syntax
**"Service call failed"**: Check that target device is online

### Community Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/Bokbacken/energy_dispatcher/issues)
- **GitHub Discussions**: [Ask questions and share tips](https://github.com/Bokbacken/energy_dispatcher/discussions)
- **Home Assistant Forum**: Search for "Energy Dispatcher"

### Before Asking for Help

Please provide:
1. Home Assistant version
2. Energy Dispatcher version
3. Your configuration (remove sensitive info)
4. Relevant log entries
5. What you expected vs. what happened

## 🎉 Success!

You're now ready to enjoy optimized energy management! 

**Remember**:
- Monitor the dashboard for the first few days
- Adjust settings based on your actual usage
- Use override buttons when needed
- Trust the system to optimize over time

**Want to go further?**
- Read the [Dashboard Guide](./dashboard_guide.md) for customization options
- Check [Future Improvements](./future_improvements.md) to see what's coming
- Contribute to the project on [GitHub](https://github.com/Bokbacken/energy_dispatcher)

Happy optimizing! ⚡🔋☀️
